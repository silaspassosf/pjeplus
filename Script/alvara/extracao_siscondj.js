// Script/alvara/extracao_siscondj.js — extração de dados dentro do SISCONDJ (fase 2).
//
// Responsabilidade: ler a tela/API do SISCONDJ e devolver dados estruturados
// para a minuta e preenchimento. Roda SOMENTE quando a aba ativa é do SISCONDJ.

(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    // ─────────────────────────────────────────────────────────────────
    // CONFIG — seletores e endpoints do SISCONDJ
    // ─────────────────────────────────────────────────────────────────
    const CONFIG = {
        dominios: [
            'siscondj',
            'alvaraeletronico',
            'portaltrtsp'
        ],
        seletores: {
            numeroProcesso: '#numeroProcesso',
            btnBuscar: '#bt_buscar',
            tabelaContas: '#table_contas',
            btnEmitirMandato: '#bt_emitir_mandato'
        },
        endpoints: {}
    };

    function ehSiscondj() {
        const host = (window.location.hostname || '').toLowerCase();
        const href = (window.location.href || '').toLowerCase();
        return CONFIG.dominios.some(d => host.includes(d) || href.includes(d));
    }

    function logSiscondj(...args) {
        console.log('[PjeAlvara][siscondj]', ...args);
    }

    function parseMoeda(str) {
        if (!str) return 0;
        const limpo = String(str).replace(/[^\d,\.-]/g, '').replace(/\./g, '').replace(',', '.');
        const num = parseFloat(limpo);
        return isNaN(num) ? 0 : num;
    }

    // ─────────────────────────────────────────────────────────────────
    // LEITURA POR DOM
    // ─────────────────────────────────────────────────────────────────
    function valorDoCampo(seletor) {
        const el = document.querySelector(seletor);
        return el ? String(el.value || el.innerText || '').trim() : '';
    }

    function lerTela() {
        const dados = {};
        for (const [chave, seletor] of Object.entries(CONFIG.seletores)) {
            const valor = valorDoCampo(seletor);
            if (valor) dados[chave] = valor;
        }
        return dados;
    }

    function lerContasJudiciais() {
        const tabela = document.getElementById('table_contas') || document.querySelector('table.relatorio');
        if (!tabela) return [];

        const linhas = Array.from(tabela.querySelectorAll('tr[id^="linhaConta_"]'));
        return linhas.map(tr => {
            const idMatch = tr.id.match(/linhaConta_(\d+)/);
            const contaId = idMatch ? idMatch[1] : '';
            const tdSaldo = tr.querySelector('[id^="td_saldo_corrigido_conta_"]');
            const saldoTexto = (tdSaldo?.innerText || '').trim();
            const carregando = !!tr.querySelector('img.rotate');

            return {
                id: contaId,
                linhaEl: tr,
                saldoTexto,
                saldoValor: parseMoeda(saldoTexto),
                carregando
            };
        });
    }

    function lerParcelasConta(contaId) {
        const subTabela = contaId ? document.getElementById('contaId_' + contaId) : document.querySelector('tr.subtabela');
        if (!subTabela) return [];

        const linhasParcelas = Array.from(subTabela.querySelectorAll('tr[id^="linhaParcela_"]'));
        return linhasParcelas.map(tr => {
            const tdSaldo = tr.querySelector('[id^="td_saldo_parcela_saldo_"]');
            const saldoTexto = (tdSaldo?.innerText || '').trim();
            const chk = tr.querySelector('input[name="parcelasSelecionadas"], input[id^="parcelasSelecionadas_"], input[type="checkbox"]');

            return {
                linhaEl: tr,
                saldoTexto,
                saldoValor: parseMoeda(saldoTexto),
                checkboxEl: chk,
                marcado: chk ? chk.checked : false
            };
        });
    }

    // ─────────────────────────────────────────────────────────────────
    // CAMADA DE API — consulta do saldo sem sair da página do PJe (/detalhe)
    //
    // O Alvará roda em alvaraeletronico.trt2.jus.br e o PJe em pje.trt2.jus.br.
    // O fetch cross-origin é barrado por CORS (o servidor não manda
    // Access-Control-Allow-Origin) e a sessão do Alvará é httpOnly, então não
    // há header para montar à mão. GM_xmlhttpRequest ignora CORS e envia os
    // cookies do domínio de destino — por isso exige @grant no header do
    // pjetools.user.js junto com @connect.
    //
    // Fluxo confirmado em teste real:
    //   POST /pages/movimentacao/conta/buscar   (só o numeroProcesso importa)
    //     -> HTML com tr[id^=linhaConta_] e a tabela de parcelas
    //   GET  /pages/relatorios/extrato/conta/obterSaldo/{idConta}/parcelas/{n}/3
    //     -> Valor Disponível de cada parcela; termina em {emptyList:true}
    //
    // ATENÇÃO ao que é o quê (conferido contra a tela):
    //   td_saldo_conta_*          = VALOR DEPOSITADO acumulado  (NÃO é o saldo)
    //   td_saldo_corrigido_conta_ = VALOR DISPONÍVEL da conta    (é o saldo)
    //   td[5] parcela             = Valor Depositado da parcela
    //   td[8] parcela             = Valor Disponível da parcela  (é o saldo)
    // ─────────────────────────────────────────────────────────────────
    const HOST_ALVARA = 'https://alvaraeletronico.trt2.jus.br';
    const URL_BUSCAR = HOST_ALVARA + '/portaltrtsp/pages/movimentacao/conta/buscar';
    const URL_PARCELAS = HOST_ALVARA + '/portaltrtsp/pages/relatorios/extrato/conta/obterSaldo';
    // Saldo da conta inteira (sem /parcelas/). Mesma rota que o site usa.
    const URL_SALDO_CONTA = URL_PARCELAS;
    const MAX_PAGINAS_PARCELAS = 60;
    
    function temGMXHR() {
        return typeof GM_xmlhttpRequest === 'function';
    }

    // Wrapper de GM_xmlhttpRequest em Promise.
    function requisitar(opcoes) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest(Object.assign({}, opcoes, {
                onload: r => resolve(r),
                onerror: e => reject(new Error('falha de rede: ' + (e && e.error ? e.error : 'desconhecida'))),
                ontimeout: () => reject(new Error('timeout'))
            }));
        });
    }

    // Busca as contas de um processo. Devolve o HTML cru + o documento parseado.
    async function buscarContas(numeroProcesso) {
        if (!temGMXHR()) {
            throw new Error('GM_xmlhttpRequest indisponível — falta @grant no pje_tools.user.js');
        }
        if (!numeroProcesso) throw new Error('número do processo vazio');

        // Os campos de id vão vazios de propósito: o servidor resolve pelo
        // número. Mandar valores de outro processo é o que produz resultado
        // errado (foi observado em teste).
        const corpo = 'contaSelecionada=&exibirTJSP=false'
            + '&numeroProcesso=' + encodeURIComponent(String(numeroProcesso).trim())
            + '&idProcesso=&numeroConta=';

        const r = await requisitar({
            method: 'POST',
            url: URL_BUSCAR,
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            data: corpo,
            timeout: 45000
        });

        if (r.status !== 200) throw new Error('POST /buscar devolveu HTTP ' + r.status);

        const doc = new DOMParser().parseFromString(r.responseText, 'text/html');

        // Login expirado devolve a tela sem a tabela de contas.
        if (!doc.getElementById('form_movimentacao_conta') && !doc.getElementById('table_contas')) {
            throw new Error('resposta sem o formulário de contas — sessão do Alvará expirada?');
        }

        return { html: r.responseText, doc };
    }

    // Busca o saldo de UMA conta — endpoint da conta, não das parcelas.
    //
    // É o mesmo que o site chama em carregarContasAjax (av.md:3076):
    //     GET /pages/relatorios/extrato/conta/obterSaldo/{idConta}
    // e devolve valorSaldoCorrigido / valorSaldoCorrigidoFormatado, que é o
    // "Valor Disponível" da conta. Uma requisição, sem olhar parcela alguma.
    //
    // Devolve null se não der para ler (código de erro, resposta ruim).
    async function saldoContaApi(idConta) {
        const r = await requisitar({
            method: 'GET',
            url: URL_SALDO_CONTA + '/' + idConta + '?_=' + Date.now(),
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            timeout: 30000
        });
        if (r.status !== 200) return null;

        let json;
        try { json = JSON.parse(r.responseText); } catch (e) { return null; }
        if (!json || String(json.codigoRetorno) !== '0') return null;

        const texto = json.valorSaldoCorrigidoFormatado;
        const valor = typeof json.valorSaldoCorrigido === 'number'
            ? json.valorSaldoCorrigido
            : parseMoeda(texto);

        return {
            texto: texto || formatarBRL(valor),
            valor: valor,
            agendadoTexto: json.valorCapitalAgendadoFormatado || '',
            bloqueadoTexto: json.valorCapitalBloqueadoFormatado || '',
            depositadoTexto: json.valorDepositoOriginalFormatado || ''
        };
    }

    // Busca uma página de parcelas. Devolve { dados, fim }.
    async function umaPaginaParcelas(idConta, pagina) {
        const r = await requisitar({
            method: 'GET',
            url: URL_PARCELAS + '/' + idConta + '/parcelas/' + pagina + '/3?_=' + Date.now(),
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            timeout: 30000
        });
        if (r.status !== 200) return { dados: [], fim: true };

        let json;
        try { json = JSON.parse(r.responseText); } catch (e) { return { dados: [], fim: true }; }
        if (!json) return { dados: [], fim: true };
        if (json.emptyList !== undefined) return { dados: [], fim: true };

        const arr = Array.isArray(json) ? json : [json];
        return { dados: arr, fim: arr.length === 0 };
    }

    // Parcelas de uma conta, paginando até vir {emptyList:true}.
    // Chamada apenas para contas que têm saldo — nas demais não há o que
    // expandir, e o HTML já basta.
    async function parcelasContaApi(idConta) {
        const todas = [];
        for (let pagina = 0; pagina < MAX_PAGINAS_PARCELAS; pagina++) {
            const res = await umaPaginaParcelas(idConta, pagina);
            if (res.fim) break;
            todas.push(...res.dados);
        }
        return todas;
    }

    // Extrai, do HTML do POST, a lista de contas com seus depósitos.
    // Data e depositante só existem aqui — a API devolve apenas valores.
    function extrairContasDoHtml(doc) {
        const contas = [];

        doc.querySelectorAll('tr[id^="linhaConta_"]').forEach(tr => {
            const m = tr.id.match(/linhaConta_(\d+)/);
            if (!m) return;
            const idConta = m[1];

            // Número da conta: segunda coluna (a primeira é o ícone).
            const numeroConta = (tr.querySelector('td:nth-child(2)')?.textContent || '').trim();
            const status = (tr.querySelector('td[id^="td_status"]')?.textContent || '').trim();

            // ATENÇÃO: td_saldo_conta_ é o DEPOSITADO total, não o saldo.
            const depositadoTxt = (tr.querySelector('td[id^="td_saldo_conta_"]')?.textContent || '').trim();

            // td_saldo_corrigido_conta_ é o VALOR DISPONÍVEL. Ele vem de dois
            // jeitos (av.md:3056):
            //   - com o valor já dentro          -> não precisa consultar nada
            //   - com um <img> ("Atualizar")     -> o servidor pede consulta
            const tdDisp = tr.querySelector('td[id^="td_saldo_corrigido_conta_"]');
            const temImg = !!(tdDisp && tdDisp.querySelector('img'));
            const disponivelTxt = tdDisp ? (tdDisp.textContent || '').trim() : '';

            // Parcelas: cada <tr id="linhaParcela_{idConta}_{idParcela}">
            //
            // As células de valor são localizadas pelo ID, não pelo índice: o
            // parse do HTML desalinha as colunas (a linha perde o <td> do
            // ícone e o restante escorrega), então tds[5] pode não ser o
            // depositado. O id é estável; o índice não é.
            const parcelas = [];
            doc.querySelectorAll('tr[id^="linhaParcela_' + idConta + '_"]').forEach(lp => {
                const mp = lp.id.match(/linhaParcela_\d+_(\d+)/);
                if (!mp) return;
                const tds = lp.querySelectorAll('td');
                if (tds.length < 6) return;

                const txt = sel => (lp.querySelector(sel)?.textContent || '').trim();

                parcelas.push({
                    idParcela: mp[1],
                    numero: (tds[1].textContent || '').trim(),
                    data: (tds[2].textContent || '').trim(),
                    depositante: (tds[3].textContent || '').trim(),
                    cpfCnpj: (tds[4].textContent || '').trim(),
                    depositadoTexto: txt('td[id^="td_saldo_parcela_depositado_"]'),
                    // Vazio no HTML: o site preenche via AJAX depois. A API é
                    // a única fonte desse valor.
                    disponivelTexto: txt('td[id^="td_saldo_parcela_saldo_"]')
                });
            });

            contas.push({
                idConta,
                numeroConta,
                status,
                depositadoTexto: depositadoTxt,
                disponivelTexto: disponivelTxt,
                // true só quando a célula veio preenchida com valor — se veio
                // com <img>, o saldo tem de ser consultado.
                temValorNoHtml: !temImg && parseMoeda(disponivelTxt) > 0,
                parcelas
            });
        });

        return contas;
    }

    // Junta HTML + API.
    //
    // O VALOR DISPONÍVEL DA CONTA, em três situações (av.md:3056):
    //
    //   1. A célula td_saldo_corrigido_conta_* já vem com o valor no HTML.
    //      Nesse caso o site não faz requisição nenhuma — e nós também não.
    //
    //   2. A célula vem com <img> (ícone "Atualizar"). É o servidor dizendo
    //      "consulte na hora". Aí o site chama
    //          GET .../extrato/conta/obterSaldo/{idConta}
    //      que devolve o saldo da CONTA em uma única requisição, sem
    //      parcela alguma. É esse caminho que usamos.
    //
    //   3. Se esse endpoint falhar, aí sim caímos nas parcelas.
    //
    // As parcelas servem só para a discriminação dos depósitos na saída —
    // nunca para descobrir se há saldo.
    async function saldosCompletos(numeroProcesso) {
        const t0 = performance.now();
        const { doc } = await buscarContas(numeroProcesso);
        const contas = extrairContasDoHtml(doc);

        contas.forEach(c => {
            c.depositadoValor = parseMoeda(c.depositadoTexto);
        });

        logSiscondj('contas:', contas.length,
            '| POST em', Math.round(performance.now() - t0) + 'ms');

        for (const conta of contas) {
            await completarConta(conta);
        }

        logSiscondj('consulta concluída em', Math.round(performance.now() - t0) + 'ms');
        return contas;
    }

    // tol = meio centavo: os valores têm 2 casas, diferença real é ≥ 1 centavo.
    const TOLERANCIA = 0.005;

    // Completar UMA conta.
    //
    // 1. Se o HTML já trouxe o Valor Disponível preenchido (sem <img>),
    //    usa esse valor. Nenhuma requisição.
    // 2. Se a célula veio com <img> ("Atualizar"), chama
    //    obterSaldo/{idConta} — UMA requisição que devolve o saldo da conta.
    //    Sem parcela alguma.
    // 3. Só se esse endpoint falhar é que descemos para as parcelas, de trás
    //    para a frente, parando quando a soma para de crescer.
    //
    // As parcelas, quando consultadas, servem só para a discriminação dos
    // depósitos na saída — nunca para descobrir se há saldo.
    async function completarConta(conta) {
        const n = conta.parcelas.length;
        const totalPaginas = Math.ceil(n / 3);

        let origemSaldo = 'html';
        let valorSaldo = 0;

        // 1. O HTML já tem o valor? Então é isso e pronto.
        const doHtml = parseMoeda(conta.disponivelTexto);
        if (conta.temValorNoHtml && doHtml > 0) {
            valorSaldo = doHtml;
        } else {
            // 2. Endpoint do saldo da conta: uma requisição.
            const api = await saldoContaApi(conta.idConta);
            if (api) {
                valorSaldo = api.valor;
                origemSaldo = 'api-conta';
                conta.saldoApiTexto = api.texto;
            } else {
                // 3. Plano B: parcelas, de trás para a frente.
                logSiscondj('conta', conta.numeroConta,
                    '— obterSaldo falhou, caindo para as parcelas');
                valorSaldo = await saldoPorParcelas(conta, totalPaginas);
                origemSaldo = 'api-parcelas';
            }
        }

        conta.totalDisponivelValor = valorSaldo;
        conta.totalDisponivelTexto = formatarBRL(valorSaldo);
        conta.origemSaldo = origemSaldo;
        conta.totalPaginas = totalPaginas;
        conta.expandida = true;

        logSiscondj('conta', conta.numeroConta,
            '— disponível', conta.totalDisponivelTexto,
            '| origem', origemSaldo,
            '| depositado', conta.depositadoTexto);
    }

    // Plano B: soma o saldo percorrendo as parcelas de trás para a frente,
    // parando na primeira página que não acrescenta nada.
    async function saldoPorParcelas(conta, totalPaginas) {
        let paginasLidas = 0;

        for (let k = totalPaginas - 1; k >= 0; k--) {
            const res = await umaPaginaParcelas(conta.idConta, k);
            if (res.fim) continue;
            paginasLidas++;

            const anterior = conta.parcelas.reduce((s, p) => s + (p.disponivelValor || 0), 0);

            for (const reg of res.dados) {
                if (!reg) continue;
                const idx = conta.parcelas.findIndex(p => String(p.idParcela) === String(reg.idParcela));
                if (idx < 0) continue;
                const p = conta.parcelas[idx];
                const texto = reg.valorSaldoCorrigidoFormatado;
                if (!texto) continue;
                p.disponivelTexto = texto;
                p.disponivelValor = parseMoeda(texto);
                p.fonte = 'api';
            }

            const acumulado = conta.parcelas.reduce((s, p) => s + (p.disponivelValor || 0), 0);
            if (acumulado > 0 && acumulado <= anterior + TOLERANCIA) break;
        }

        conta.paginasLidas = paginasLidas;
        return conta.parcelas.reduce((s, p) => s + (p.disponivelValor || 0), 0);
    }

    function formatarBRL(n) {
        try {
            return Number(n).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        } catch (e) {
            return 'R$ ' + (Number(n) || 0).toFixed(2).replace('.', ',');
        }
    }

    // Monta o HTML de saída — mesmo formato do botão "Extrair saldo"
    // (Script/alvara/saldo_extracao.js), que é a referência do projeto.
    function montarSaidaHtml(contas) {
        const hoje = new Date();
        const dataConferencia = String(hoje.getDate()).padStart(2, '0') + '/'
            + String(hoje.getMonth() + 1).padStart(2, '0') + '/' + hoje.getFullYear();

        const pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"';

        // Só contas com valor disponível > 0 entram na saída.
        const comSaldo = contas.filter(c => (c.totalDisponivelValor || 0) > 0);
        if (!comSaldo.length) return null;

        let html = '<p ' + pStyle + '>Data da conferência: ' + dataConferencia + '</p>';

        comSaldo.forEach((conta, index) => {
            html += '<p ' + pStyle + '>Conta judicial: ' + conta.numeroConta + '</p>';
            html += '<p ' + pStyle + '>Total disponível: ' + formatarBRL(conta.totalDisponivelValor) + '</p>';

            const depositos = conta.parcelas.filter(p => p.disponivelValor > 0 && p.data && p.depositante);
            if (depositos.length) {
                html += '<p ' + pStyle + '>Discriminação de depósitos disponíveis:</p>';
                depositos.forEach(d => {
                    html += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:1cm;text-align:justify !important;text-indent:4.5cm;">'
                        + '• ' + d.data + ' - ' + d.depositante + ' - ' + formatarBRL(d.disponivelValor) + '</p>';
                });
            } else {
                html += '<p ' + pStyle + '>(Consultar parcelas individuais - expandir detalhes na tela)</p>';
            }

            if (index < comSaldo.length - 1) {
                html += '<p ' + pStyle + '><br data-cke-filler="true"></p>';
            }
        });

        return html;
    }

    // ─────────────────────────────────────────────────────────────────
    // NÚMERO DO PROCESSO
    //
    // A tela /detalhe do PJe NÃO traz o número na URL (só /processo/{id}).
    // Mesmas fontes usadas pelo Argos (Script/modules/argos/argos.js:85):
    // título da aba, .texto-numero-processo e, por último, a URL.
    // ─────────────────────────────────────────────────────────────────
    const RE_CNJ = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;

    function numeroProcessoDaPagina(doc) {
        const d = doc || document;

        const doTitulo = String(d.title || '').match(RE_CNJ);
        if (doTitulo) return doTitulo[0];

        const el = d.querySelector('.texto-numero-processo');
        if (el) {
            const m = String(el.textContent || '').match(RE_CNJ);
            if (m) return m[0];
        }

        // Fallbacks: campo de formulário e a própria URL.
        const campo = d.querySelector('#numeroProcesso');
        if (campo && campo.value && RE_CNJ.test(campo.value)) {
            return String(campo.value).match(RE_CNJ)[0];
        }

        const doHref = String((window.location && window.location.href) || '').match(RE_CNJ);
        if (doHref) return doHref[0];

        return null;
    }

    // ─────────────────────────────────────────────────────────────────
    // ORQUESTRADOR DE EXTRAÇÃO
    // ─────────────────────────────────────────────────────────────────
    async function extrairDadosSiscondj() {
        if (!ehSiscondj()) {
            return {
                sucesso: false,
                erro: 'aba atual nao e do SISCONDJ',
                origem: 'siscondj'
            };
        }

        const tela = lerTela();
        const contas = lerContasJudiciais();
        const sucesso = Object.keys(tela).length > 0 || contas.length > 0;

        logSiscondj('extracao concluida — contas encontradas:', contas.length);

        return {
            sucesso,
            tela,
            contas,
            origem: 'siscondj'
        };
    }

    // Consulta externa (pelo módulo AUD)
    async function consultarDocumento(documento) {
        if (!Alv.siscon || typeof Alv.siscon.consultarDocumento !== 'function') {
            throw new Error('Módulo de consulta SISCON não disponível.');
        }
        return Alv.siscon.consultarDocumento(documento);
    }

    // Copia HTML para o clipboard.
    //
    // execCommand('copy') exige gesto do usuário, e o fluxo aqui é assíncrono
    // (await na rede) — o navegador perde o vínculo e nega a cópia, o que
    // acontecia de fato. GM_setClipboard não tem essa exigência, então é o
    // caminho principal; execCommand fica como reserva. Mesmo padrão do
    // infojud.js:1011.
    function copiarHtml(html) {
        if (!html) return false;

        if (typeof GM_setClipboard === 'function') {
            try {
                GM_setClipboard(html, 'html');
                return true;
            } catch (e) {
                try {
                    const puro = document.createElement('div');
                    puro.innerHTML = html;
                    GM_setClipboard(puro.innerText, 'text');
                    return true;
                } catch (e2) {
                    logSiscondj('GM_setClipboard falhou:', e2);
                }
            }
        }

        // Reserva: seleção + execCommand (só funciona dentro do gesto).
        const div = document.createElement('div');
        div.innerHTML = html;
        div.style.cssText = 'position:absolute;left:-9999px;';
        document.body.appendChild(div);

        const range = document.createRange();
        range.selectNodeContents(div);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);

        let ok = false;
        try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
        if (document.body.contains(div)) document.body.removeChild(div);
        sel.removeAllRanges();
        return ok;
    }

    // Ação do botão no painel (roda na tela /detalhe do PJe).
    // Devolve { copiado: bool, semSaldo: bool, contas }.
    async function copiarSaldoProcesso(numeroProcesso) {
        const contas = await saldosCompletos(numeroProcesso);
        const html = montarSaidaHtml(contas);

        if (!html) {
            logSiscondj('nenhuma conta com saldo disponível');
            return { copiado: false, semSaldo: true, contas };
        }

        const ok = copiarHtml(html);
        logSiscondj('saída copiada:', ok, '| contas com saldo:', contas.filter(c => c.totalDisponivelValor > 0).length);
        return { copiado: ok, semSaldo: false, contas };
    }

    Alv.siscondj = Alv.siscondj || {};
    Object.assign(Alv.siscondj, {
        CONFIG,
        ehSiscondj,
        logSiscondj,
        parseMoeda,
        formatarBRL,
        valorDoCampo,
        lerTela,
        lerContasJudiciais,
        lerParcelasConta,
        extrairDadosSiscondj,
        consultarDocumento,
        numeroProcessoDaPagina,
        // camada de API
        temGMXHR,
        buscarContas,
        parcelasContaApi,
        extrairContasDoHtml,
        saldosCompletos,
        montarSaidaHtml,
        copiarSaldoProcesso
    });
})();
