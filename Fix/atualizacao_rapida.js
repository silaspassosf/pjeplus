/* Réplica da "Atualização Rápida" do +PJe (gigs-plugin.js, ramo
 * `atualizacaorapida`, ~L24076-24396) para execução autônoma via Playwright.
 *
 * Diferenças deliberadas em relação ao +PJe:
 *   - SEM caixa de confirmação de data: a data de liquidação vem em cfg.data
 *     (o orquestrador injeta a data atual). O +PJe perguntava ao usuário.
 *   - SEM caixa de seleção de cálculo: cfg.idCalculo (número da listagem) ou
 *     cálculo único. Ambiguidade => falha controlada, nunca escolha arbitrária.
 *   - Roda numa aba própria do PJeCalc; ao confirmar "Sucesso!" fecha a aba.
 *   - Sobrevive à navegação do PJeCalc: cada fase é marcada no sessionStorage
 *     ANTES de agir; se o contexto for destruído por um redirecionamento JSF/SSO,
 *     o Python lê o espelho e resubmete o motor (como o +PJe re-roda por carga de
 *     página com tempAR:passoN). A retomada só ocorre se o espelho provar que
 *     nada foi liquidado/enviado ainda.
 *   - cfg.somenteBusca=true (modo de teste/inspeção): abre o cálculo, confere o
 *     CNJ no painel de dados e PARA — não liquida nem envia.
 *
 * Contrato: executado via page.evaluate(JS, cfg). Resolve para
 *   { ok: true,  numeroProcesso, numeroCalculo, data }
 *   { ok: false, erro, fase, posEnvio }   // posEnvio=true => NÃO reenviar
 *
 * cfg = { numeroProcesso, data (dd/mm/aaaa), idCalculo (string|null),
 *         selecionarMaisRecente (bool — modo automático do fluxo teimosinha:
 *         com vários cálculos, atualiza o de maior número, o mais recente) }
 */
async (cfg) => {
    const CNJ_RE = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;
    const MARCADOR = 'MAISPJE: ATUALIZAÇÃO RÁPIDA';
    const TETO_PASSO = 30000;      // teto por etapa (como o +PJe: 30s)
    const TETO_PAGINA = 12000;     // busca por paginação de cálculos

    const estado = { fase: 'inicio', posEnvio: false };
    const falhar = (erro) => ({ ok: false, erro: String(erro), fase: estado.fase, posEnvio: estado.posEnvio });

    // ── Espelho de progresso no sessionStorage ───────────────────────────────
    // O PJeCalc navega (rediraw JSF/SSO) e isso derruba o contexto do evaluate.
    // O +PJe sobrevive porque guarda o passo no storage e re-roda por carga de
    // página (tempAR:passoN). Aqui registramos a fase ANTES de qualquer ação com
    // efeito; o Python lê o espelho após um contexto destruído e só retoma se a
    // fase provar que nada foi liquidado/enviado ainda. sessionStorage sobrevive
    // à navegação da mesma aba (e é limpo quando a aba fecha).
    const CHAVE_MIR = '__pjeplusAR';
    const CHAVE_LIMPO = '__pjeplusAR_limpo';
    const CHAVE_CALC = '__pjeplusAR_calc';
    const marcar = (fase) => { try { sessionStorage.setItem(CHAVE_MIR, fase); } catch (e) {} };
    const lerMem = (k) => { try { return sessionStorage.getItem(k) || ''; } catch (e) { return ''; } };
    const gravarMem = (k, v) => { try { sessionStorage.setItem(k, String(v || '')); } catch (e) {} };
    marcar('inicio');

    // Espera observável (MutationObserver + polling curto), nunca pausa cega.
    function aguardar(teste, teto = TETO_PASSO, intervalo = 200) {
        return new Promise((resolve) => {
            const inicio = Date.now();
            let observer = null;
            let timer = null;
            const concluir = (valor) => {
                if (observer) { try { observer.disconnect(); } catch (e) {} }
                if (timer) clearTimeout(timer);
                resolve(valor);
            };
            const verificar = () => {
                let valor = null;
                try { valor = teste(); } catch (e) { valor = null; }
                if (valor) { concluir(valor); return true; }
                if (Date.now() - inicio >= teto) { concluir(null); return true; }
                return false;
            };
            if (verificar()) return;
            try {
                observer = new MutationObserver(() => { verificar(); });
                observer.observe(document.documentElement,
                    { childList: true, subtree: true, attributes: true, characterData: true });
            } catch (e) {}
            const passo = () => { if (!verificar()) timer = setTimeout(passo, intervalo); };
            timer = setTimeout(passo, intervalo);
        });
    }

    const titulo = () => (document.querySelector('div[id="barraTitulo"]')?.textContent || '').trim();

    // Preenche campo JSF/RichFaces disparando os eventos que o servidor observa.
    function preencher(el, valor) {
        if (!el) throw new Error('Campo não encontrado para preenchimento.');
        const proto = el instanceof HTMLTextAreaElement
            ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(el, valor);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        if (typeof el.onchange === 'function') { try { el.onchange(); } catch (e) {} }
    }

    const clicar = (el) => { if (!el) throw new Error('Controle não encontrado para clique.'); el.click(); };

    const linkAbrir = () => Array.from(document.querySelectorAll('a.linkSelecionar[title="Abrir"]'));

    // Número do cálculo na célula da listagem (coluna 2, como o +PJe).
    function numeroDaLinha(link) {
        try {
            const celulas = link.parentElement.parentElement.childNodes;
            return (celulas[2]?.innerText || '').trim();
        } catch (e) { return ''; }
    }

    // Lê o CNJ da tela atual: tenta panelDadosCalculo (presente em Liquidar Atualização
    // e cálculos internos) e, em cálculo externo (calculo-externo.jsf), monta dos inputs.
    function lerCnjDaTela() {
        const painel = document.querySelector('span[id="formulario:panelDadosCalculo"]');
        const mPainel = ((painel?.textContent || '').match(CNJ_RE) || [])[0];
        if (mPainel) return mPainel;

        const g = (sufixo) => {
            const el = document.querySelector('input[id="formulario:' + sufixo + '"]')
                || document.querySelector('input[id$=":' + sufixo + '"]');
            return (el && el.value ? el.value : '').trim();
        };
        const num = g('numero');
        const dig = g('digito');
        const ano = g('ano');
        const just = g('justica') || '5';
        const reg = g('regiao');
        const vara = g('vara');
        if (num && dig && ano && reg && vara) {
            const montado = `${num.padStart(7, '0')}-${dig.padStart(2, '0')}.${ano}.${just}.${reg.padStart(2, '0')}.${vara.padStart(4, '0')}`;
            if (CNJ_RE.test(montado)) return montado;
        }
        return null;
    }

    try {
        const numeroProcesso = String(cfg.numeroProcesso || '').trim();
        const data = String(cfg.data || '').trim();
        const idCalculo = cfg.idCalculo == null ? null : String(cfg.idCalculo).trim();
        if (!CNJ_RE.test(numeroProcesso)) return falhar('Número CNJ inválido: ' + numeroProcesso);
        if (!/^\d{2}\/\d{2}\/\d{4}$/.test(data)) return falhar('Data de liquidação inválida: ' + data);
        const partes = numeroProcesso.match(/^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$/);
        if (!partes) return falhar('Número CNJ fora do padrão: ' + numeroProcesso);

        // ── 0. Limpar memória do PJe-Calc (equivalente ao avjt-limpar-memoria) ─
        // Se havia um cálculo aberto de execução anterior na sessão JSF, clica
        // `.menuImageClose` antes de buscar o novo processo para evitar o bug
        // de exibir o último cálculo aberto.
        if (lerMem(CHAVE_LIMPO) !== numeroProcesso) {
            gravarMem(CHAVE_LIMPO, numeroProcesso);
            gravarMem(CHAVE_CALC, '');
            const btnFecharAnterior = document.querySelector('li#li_operacoes_fechar a')
                || document.querySelector('a.menuImageClose')
                || document.querySelector('.menuImageClose');
            if (btnFecharAnterior) {
                estado.fase = 'limpar-memoria'; marcar('limpar-memoria');
                clicar(btnFecharAnterior);
                await aguardar(() => !document.querySelector('.menuImageClose') && document.querySelector('[title="Buscar Cálculo"]'), 12000);
            }
        }

        let numeroCalculo = lerMem(CHAVE_CALC);
        const titInicial = titulo();
        const jaEmEnviar = titInicial.includes('Enviar para o PJe') && !!numeroCalculo;
        const jaEmLiquidar = titInicial.includes('Liquidar Atualização') && !!numeroCalculo;
        const jaEmDados = titInicial.includes('Dados do Cálculo') && !!numeroCalculo;

        if (!jaEmEnviar && !jaEmLiquidar && !jaEmDados) {
            // ── 1. Buscar processo no PJeCalc ───────────────────────────────
            estado.fase = 'busca-processo'; marcar('busca-processo');
            if (!document.querySelector('input[id*="numeroProcessoBusca"]')) {
                const campoBuscarCalc = await aguardar(() => document.querySelector('[title="Buscar Cálculo"]'));
                if (campoBuscarCalc) clicar(campoBuscarCalc);
            }
            const campos = [
                ['numeroProcessoBusca', partes[1]],
                ['digitoProcessoBusca', partes[2]],
                ['anoProcessoBusca', partes[3]],
                ['justicaBusca', partes[4]],
                ['regiaoBusca', partes[5]],
                ['varaProcessoBusca', partes[6]],
            ];
            for (const [nome, valor] of campos) {
                const input = await aguardar(() => document.querySelector('input[id*="' + nome + '"]'));
                if (!input) return falhar('Campo de busca não carregou: ' + nome);
                preencher(input, valor);
            }
            const setor = document.querySelector('input[id*="formulario:setor"]');
            if (setor && (setor.checked || setor.hasAttribute('checked'))) clicar(setor);
            const btBuscar = await aguardar(() => document.querySelector('input[id*="formulario:buscar"]'));
            if (!btBuscar) return falhar('Botão de busca do processo não encontrado.');
            clicar(btBuscar);

            // ── 2. Resultado da busca: sem cálculo / lista ──────────────────
            estado.fase = 'lista-calculos'; marcar('lista-calculos');
            const resultado = await aguardar(() => {
                const livre = document.querySelector('span.box-msg-livre');
                if (livre && /Não existem resultados/i.test(livre.textContent || '')) return { semCalculo: true };
                const links = linkAbrir();
                if (links.length) return { links };
                return null;
            });
            if (!resultado) return falhar('A busca do PJeCalc não retornou resultados.');
            if (resultado.semCalculo) return falhar('Processo sem cálculo registrado no PJeCalc.');

            // ── 3. Selecionar o cálculo (único, por número, mais recente, ou ambiguidade) ─
            estado.fase = 'selecao-calculo'; marcar('selecao-calculo');
            let alvo = null;
            const links = resultado.links;
            const maisRecente = !!cfg.selecionarMaisRecente;
            if (idCalculo != null && idCalculo !== '') {
                const inputNum = await aguardar(() => document.querySelector('input[id*="numeroCalculoBusca"]'));
                if (!inputNum) return falhar('Campo de número do cálculo não encontrado.');
                preencher(inputNum, idCalculo);
                const btBuscar2 = await aguardar(() => document.querySelector('input[id*="formulario:buscar"]'));
                if (btBuscar2) clicar(btBuscar2);
                const filtrado = await aguardar(() => {
                    const ls = linkAbrir().filter((l) => numeroDaLinha(l) === idCalculo);
                    if (ls.length === 1) return ls[0];
                    const livre = document.querySelector('span.box-msg-livre');
                    if (livre && /Não existem resultados/i.test(livre.textContent || '')) return { vazio: true };
                    return null;
                });
                if (!filtrado || filtrado.vazio) return falhar('Cálculo ' + idCalculo + ' não localizado na listagem.');
                alvo = filtrado;
                numeroCalculo = idCalculo;
            } else if (links.length === 1) {
                alvo = links[0];
                numeroCalculo = numeroDaLinha(alvo);
            } else if (maisRecente) {
                const vistos = new Map();
                let guarda = 0;
                while (guarda++ < 50) {
                    for (const l of linkAbrir()) {
                        const n = numeroDaLinha(l);
                        if (n && !vistos.has(n)) vistos.set(n, l);
                    }
                    const prox = document.querySelector('img[title="Próximo"]');
                    if (!prox || /desabilitado/i.test(prox.alt || '')) break;
                    clicar(prox.parentElement);
                    await aguardar(() => null, 900);
                }
                const numeros = [];
                vistos.forEach((_, k) => { numeros.push(String(k)); });
                if (!numeros.length) return falhar('Nenhum número de cálculo legível na listagem.');
                const numerico = numeros.every((n) => /^\d+$/.test(n));
                let escolhido = numeros[0];
                if (numerico) {
                    for (let i = 1; i < numeros.length; i++) {
                        if (BigInt(numeros[i]) > BigInt(escolhido)) escolhido = numeros[i];
                    }
                } else {
                    numeros.sort();
                    escolhido = numeros[numeros.length - 1];
                }
                const inputNum = await aguardar(() => document.querySelector('input[id*="numeroCalculoBusca"]'));
                if (!inputNum) return falhar('Campo de número do cálculo não encontrado.');
                preencher(inputNum, escolhido);
                const btBuscar3 = await aguardar(() => document.querySelector('input[id*="formulario:buscar"]'));
                if (btBuscar3) clicar(btBuscar3);
                const filtrado2 = await aguardar(() => {
                    const ls = linkAbrir().filter((l) => numeroDaLinha(l) === escolhido);
                    if (ls.length === 1) return ls[0];
                    return null;
                });
                if (!filtrado2) return falhar('Cálculo mais recente (' + escolhido + ') não relocalizado na listagem.');
                alvo = filtrado2;
                numeroCalculo = escolhido;
            } else {
                const vistos = new Set();
                const candidatos = [];
                let guarda = 0;
                while (guarda++ < 50) {
                    for (const l of linkAbrir()) {
                        const n = numeroDaLinha(l);
                        if (n && !vistos.has(n)) { vistos.add(n); candidatos.push(n); }
                    }
                    const prox = document.querySelector('img[title="Próximo"]');
                    if (!prox || /desabilitado/i.test(prox.alt || '')) break;
                    clicar(prox.parentElement);
                    await aguardar(() => null, 900);
                }
                return falhar('Múltiplos cálculos (' + candidatos.join(', ') +
                    '); informe id_calculo para escolher. Nenhuma atualização foi enviada.');
            }

            // ── 4. Abrir o cálculo ──────────────────────────────────────────
            gravarMem(CHAVE_CALC, numeroCalculo);
            estado.fase = 'abrir-calculo'; marcar('abrir-calculo');
            clicar(alvo);
            const dadosCalc = await aguardar(() => titulo().includes('Cálculo > Dados do Cálculo') ? true : null);
            if (!dadosCalc) return falhar('A tela de dados do cálculo não abriu.');
        }

        if (!jaEmEnviar && !jaEmLiquidar) {
            // Modo somente_busca (teste f.ar): confirma o processo e PARA — nada é liquidado nem enviado.
            if (cfg.somenteBusca) {
                const cnjCalc = lerCnjDaTela();
                if (cnjCalc !== numeroProcesso) {
                    return falhar('O cálculo aberto pertence a outro processo (' +
                        (cnjCalc || '?') + '); busca cancelada.');
                }
                try { document.querySelector('li#li_operacoes_fechar a, a.menuImageClose, .menuImageClose')?.click(); } catch (e) {}
                return { ok: true, somenteBusca: true, numeroProcesso, numeroCalculo, data: '' };
            }

            // ── 5. Menu "Liquidar Atualização" ──────────────────────────────
            estado.fase = 'menu-liquidar'; marcar('menu-liquidar');
            const menuLiquidar = await aguardar(() =>
                document.querySelector('li#li_operacoes_liquidar_pagamento a')
                || Array.from(document.querySelectorAll('li a'))
                    .find((a) => (a.textContent || '').includes('Liquidar Atualização'))
                || null);
            if (!menuLiquidar) return falhar('Opção "Liquidar Atualização" não apareceu.');
            clicar(menuLiquidar);
            const telaLiquidar = await aguardar(() => titulo().includes('Atualização > Liquidar Atualização') ? true : null);
            if (!telaLiquidar) return falhar('A tela de liquidação da atualização não abriu.');
        }

        if (!jaEmEnviar) {
            // ── 6. Conferir processo, observação, data e liquidar ───────────
            estado.fase = 'liquidar'; marcar('liquidar');
            const cnjAberto = lerCnjDaTela();
            if (cnjAberto !== numeroProcesso) {
                return falhar('O cálculo aberto pertence a outro processo (' + (cnjAberto || '?') +
                    '); liquidação cancelada.');
            }
            const obs = await aguardar(() => document.querySelector('textarea[id="formulario:comentarios"]'));
            if (obs && !(obs.value || '').includes(MARCADOR)) {
                preencher(obs, (obs.value || '') + '\n' + MARCADOR);
            }
            const barraTituloEl = document.querySelector('div[id="barraTitulo"]');
            const frameAtualizacao = (barraTituloEl && barraTituloEl.parentElement &&
                barraTituloEl.parentElement.parentElement) || null;
            const noFrame = (sel) => frameAtualizacao
                ? frameAtualizacao.querySelector(sel)
                : document.querySelector(sel);
            const inputData = await aguardar(() => noFrame('input[id="formulario:dataDeLiquidacaoInputDate"]'));
            if (!inputData) return falhar('Campo de data de liquidação não carregou.');
            preencher(inputData, data);
            const btLiquidar = await aguardar(() => noFrame('input[id="formulario:liquidar"]'));
            if (!btLiquidar) return falhar('Botão liquidar não encontrado.');
            clicar(btLiquidar);
            const aviso = await aguardar(() => {
                const el = document.querySelector('div[id="divMensagem"]');
                return (el && (el.textContent || '').trim()) ? el : null;
            });
            if (!aviso) return falhar('O PJeCalc não confirmou o resultado da liquidação.');
            if (!(aviso.textContent || '').includes('Operação realizada com sucesso.')) {
                return falhar('Liquidação não confirmada: ' + (aviso.textContent || '').trim());
            }

            // ── 7. Ir para "Enviar para o PJe" ──────────────────────────────
            estado.fase = 'enviar-tela'; marcar('enviar-tela');
            const menuEnviar = await aguardar(() => document.querySelector('li[id="li_operacoes_validar_atualizacao"] a'));
            if (!menuEnviar) return falhar('Opção "Enviar para o PJe" não apareceu após liquidar.');
            clicar(menuEnviar);
            const telaEnviar = await aguardar(() => titulo().includes('Enviar para o PJe') ? true : null);
            if (!telaEnviar) return falhar('A tela "Enviar para o PJe" não abriu.');
        }

        estado.fase = 'consolidar'; marcar('consolidar');
        const consolidar = await aguardar(() =>
            document.querySelector('input[value="Consolidar Dados"]')
            || document.querySelector('input[id="formulario:validar"]'), 8000);
        if (consolidar) clicar(consolidar);
        const pronto = await aguardar(() =>
            Array.from(document.querySelectorAll('span.rich-messages-label'))
                .find((el) => (el.textContent || '').includes('Os dados estão prontos para serem enviados para o PJe')) || null);
        if (!pronto) return falhar('O PJeCalc não concluiu a consolidação dos dados.');

        // A partir daqui o envio é irreversível: qualquer falha é pós-envio.
        estado.fase = 'enviar'; marcar('enviar');
        estado.posEnvio = true;
        const btEnviar = await aguardar(() => document.querySelector('input[value="Enviar para o PJe"]'));
        if (!btEnviar) return falhar('Botão "Enviar para o PJe" não encontrado.');
        clicar(btEnviar);
        const popup = await aguardar(() => document.querySelector('input[id="popup_ok"]')
            || Array.from(document.querySelectorAll('h2')).find((h) => (h.textContent || '').includes('Sucesso!'))
            || null);
        if (!popup) return falhar('O PJe não confirmou o envio (resultado desconhecido — não reenviar).');
        if (popup.matches && popup.matches('input[id="popup_ok"]')) clicar(popup);

        // ── 8. Confirmar "Sucesso!" e encerrar ──────────────────────────────
        estado.fase = 'sucesso'; marcar('sucesso');
        const sucesso = await aguardar(() =>
            Array.from(document.querySelectorAll('h2')).find((h) => (h.textContent || '').includes('Sucesso!')) || null);
        if (!sucesso) return falhar('O envio ao PJe não confirmou sucesso (não reenviar).');

        try { document.querySelector('li#li_operacoes_fechar a, a.menuImageClose, .menuImageClose')?.click(); } catch (e) {}
        try { window.close(); } catch (e) {}
        return { ok: true, numeroProcesso, numeroCalculo, data };
    } catch (e) {
        return falhar((e && e.message) ? e.message : e);
    }
}