// ==UserScript==
// @name         TESTE — Saldo Alvará (isolado)
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  Teste isolado da consulta de saldo do Alvará Eletrônico. Injeta um painel com botão "Buscar saldo" no PJe. Não depende do pjetools.
// @author       Silas
// @match        https://pje.trt2.jus.br/*
// @match        https://pje1g.trt2.jus.br/*
// @grant        GM_xmlhttpRequest
// @connect      alvaraeletronico.trt2.jus.br
// @connect      siscondj.trt2.jus.br
// @run-at       document-idle
// ==/UserScript==

(function () {
    'use strict';

    const HOST_ALVARA = 'https://alvaraeletronico.trt2.jus.br';
    const URL_BUSCAR = HOST_ALVARA + '/portaltrtsp/pages/movimentacao/conta/buscar';
    const URL_PARCELAS = HOST_ALVARA + '/portaltrtsp/pages/relatorios/extrato/conta/obterSaldo';
    const MAX_PAGINAS = 60;
    const RE_CNJ = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;

    let painel, saida, btn;

    function log(...a) { console.log('%c[SALDO-TESTE]', 'color:#1a7f37;font-weight:bold', ...a); }

    function escrever(txt, cor) {
        const p = document.createElement('div');
        p.textContent = txt;
        p.style.cssText = 'padding:3px 0;border-bottom:1px solid #eee;' + (cor ? 'color:' + cor + ';' : '');
        saida.appendChild(p);
        saida.scrollTop = saida.scrollHeight;
    }

    function escreverDetalhe(txt) {
        const p = document.createElement('div');
        p.textContent = '   ' + txt;
        p.style.cssText = 'padding:2px 0 2px 12px;color:#555;font-size:11px;';
        saida.appendChild(p);
        saida.scrollTop = saida.scrollHeight;
    }

    // ── Número do processo: mesmo padrão do Argos/Simba/Sisbajud ──
    function numeroProcessoDaPagina() {
        const doTitulo = String(document.title || '').match(RE_CNJ);
        if (doTitulo) return doTitulo[0];
        const el = document.querySelector('.texto-numero-processo');
        if (el) {
            const m = String(el.textContent || '').match(RE_CNJ);
            if (m) return m[0];
        }
        const doHref = String(location.href).match(RE_CNJ);
        return doHref ? doHref[0] : null;
    }

    function requisitar(opcoes) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest(Object.assign({}, opcoes, {
                onload: resolve,
                onerror: e => reject(new Error('erro de rede: ' + (e && e.error || '?'))),
                ontimeout: () => reject(new Error('timeout'))
            }));
        });
    }

    // ── ETAPA 1: POST /buscar ──
    async function buscar(numeroProcesso) {
        const t0 = performance.now();
        const corpo = 'contaSelecionada=&exibirTJSP=false'
            + '&numeroProcesso=' + encodeURIComponent(numeroProcesso)
            + '&idProcesso=&numeroConta=';

        escrever('1) POST ' + URL_BUSCAR.replace(HOST_ALVARA, ''), '#1e88e5');
        escreverDetalhe('payload: ' + corpo);

        const r = await requisitar({
            method: 'POST',
            url: URL_BUSCAR,
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            data: corpo,
            timeout: 45000
        });

        const ms = Math.round(performance.now() - t0);
        escreverDetalhe('status ' + r.status + ' em ' + ms + 'ms | ' + r.responseText.length + ' chars');

        if (r.status !== 200) {
            escrever('FALHA: HTTP ' + r.status, '#c0392b');
            return null;
        }

        const doc = new DOMParser().parseFromString(r.responseText, 'text/html');

        const temForm = !!doc.getElementById('form_movimentacao_conta');
        const temTabela = !!doc.getElementById('table_contas');
        const procNaTela = doc.getElementById('numeroProcesso') ? doc.getElementById('numeroProcesso').value : '(sem campo)';

        escreverDetalhe('form_movimentacao_conta: ' + temForm);
        escreverDetalhe('table_contas: ' + temTabela);
        escreverDetalhe('numeroProcesso devolvido: ' + procNaTela);

        const linhas = doc.querySelectorAll('tr[id^="linhaConta_"]');
        escrever('   contas na pagina: ' + linhas.length, linhas.length ? '#27ae60' : '#c0392b');

        // PROVA: o HTML cru que o GM_xmlhttpRequest recebeu. Se a célula do
        // valor disponível existe lá e o parse a devolve vazia, o problema é
        // do parse; se não existe no cru, o problema é do servidor.
        const cruasCorr = (r.responseText.match(/id="td_saldo_corrigido_conta_[^"]*"/g) || []).length;
        const cruasDep = (r.responseText.match(/id="td_saldo_conta_[^"]*"/g) || []).length;
        escreverDetalhe('HTML cru: ' + cruasCorr + 'x td_saldo_corrigido_conta_ | ' + cruasDep + 'x td_saldo_conta_');
        const mCru = r.responseText.match(/<td[^>]*id="td_saldo_corrigido_conta_[^"]*"[^>]*>([\s\S]*?)<\/td>/);
        escreverDetalhe('HTML cru, conteudo da celula: ' + (mCru ? JSON.stringify(mCru[1].replace(/\s+/g, ' ').trim()) : '(celula nao encontrada no cru)'));

        if (!linhas.length) {
            // Diagnóstico: o que voltou?
            const temLogin = /login|senha|cpf/i.test(r.responseText.slice(0, 3000));
            if (temLogin) {
                escrever('SESSAO NAO COMPARTILHADA com o Alvara (veio tela de login)', '#c0392b');
            } else if (!temTabela) {
                escrever('resposta sem table_contas — processo nao encontrado ou sessao expirada', '#c0392b');
            }
            const amostra = doc.body ? doc.body.textContent.replace(/\s+/g, ' ').trim().slice(0, 300) : '';
            escreverDetalhe('inicio do texto: ' + amostra);
            return null;
        }

        const contas = [];
        linhas.forEach(tr => {
            const m = tr.id.match(/linhaConta_(\d+)/);
            if (!m) return;
            const idConta = m[1];
            const tdDep = tr.querySelector('td[id^="td_saldo_conta_"]');
            const tdCorr = tr.querySelector('td[id^="td_saldo_corrigido_conta_"]');
            const tdStatus = tr.querySelector('td[id^="td_status"]');

            const temImg = !!(tdCorr && tdCorr.querySelector('img'));
            const conta = {
                idConta,
                numeroConta: (tr.querySelector('td:nth-child(2)')?.textContent || '').trim(),
                depositadoTexto: tdDep ? tdDep.textContent.trim() : null,
                disponivelTexto: tdCorr ? tdCorr.textContent.trim() : null,
                temValorNoHtml: !temImg && brl(tdCorr ? tdCorr.textContent : '') > 0,
                status: tdStatus ? tdStatus.textContent.trim() : ''
            };

            escrever('   conta ' + conta.numeroConta + ' (id ' + idConta + ')');
            escreverDetalhe('depositado: ' + JSON.stringify(conta.depositadoTexto));
            escreverDetalhe('disponivel: ' + JSON.stringify(conta.disponivelTexto)
                + ' | celula tem <img>: ' + temImg
                + ' | valor utilizavel no HTML: ' + conta.temValorNoHtml);
            escreverDetalhe('   [tds da linha] ' + Array.from(tr.querySelectorAll('td')).map((td, i) =>
                i + ':' + (td.id || '-') + '=' + JSON.stringify(td.textContent.replace(/\s+/g, ' ').trim())).join(' | '));

            // Parcelas do HTML — celulas de valor localizadas por id, porque o
            // parse desalinha as colunas e tds[8] vira outra coisa.
            conta.parcelas = [];
            doc.querySelectorAll('tr[id^="linhaParcela_' + idConta + '_"]').forEach(lp => {
                const mp = lp.id.match(/linhaParcela_\d+_(\d+)/);
                if (!mp) return;
                const tds = lp.querySelectorAll('td');
                const txt = sel => (lp.querySelector(sel)?.textContent || '').trim();
                conta.parcelas.push({
                    idParcela: mp[1],
                    numero: (tds[1]?.textContent || '').trim(),
                    data: (tds[2]?.textContent || '').trim(),
                    depositante: (tds[3]?.textContent || '').trim(),
                    depositadoTexto: txt('td[id^="td_saldo_parcela_depositado_"]'),
                    disponivelTexto: txt('td[id^="td_saldo_parcela_saldo_"]')
                });
            });
            escreverDetalhe('parcelas no HTML: ' + conta.parcelas.length);
            escreverDetalhe('parcelas com saldo no HTML: '
                + conta.parcelas.filter(p => brl(p.disponivelTexto) > 0).length
                + ' (o esperado e 0: o site preenche via AJAX)');

            contas.push(conta);
        });

        return contas;
    }

    // ── ETAPA 2: parcelas via API ──
    // Uma página só — devolve { dados, fim }. Usada quando se sabe de antemão
    // quanto falta somar e dá para parar antes do fim.
    async function umaPagina(idConta, pagina) {
        const t0 = performance.now();
        const r = await requisitar({
            method: 'GET',
            url: URL_PARCELAS + '/' + idConta + '/parcelas/' + pagina + '/3?_=' + Date.now(),
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            timeout: 30000
        });
        const ms = Math.round(performance.now() - t0);
        if (r.status !== 200) { escreverDetalhe('pagina ' + pagina + ': HTTP ' + r.status); return { dados: [], fim: true }; }

        let json;
        try { json = JSON.parse(r.responseText); } catch (e) { escreverDetalhe('pagina ' + pagina + ': JSON invalido'); return { dados: [], fim: true }; }
        if (!json) return { dados: [], fim: true };
        if (json.emptyList !== undefined) { escreverDetalhe('pagina ' + pagina + ': emptyList (fim)'); return { dados: [], fim: true }; }

        const arr = Array.isArray(json) ? json : [json];
        escreverDetalhe('pagina ' + pagina + ': ' + arr.length + ' parcela(s) em ' + ms + 'ms');

        // PROVA: o que REALMENTE veio. Sem isso a gente fica adivinhando se o
        // array contem parcelas ou alguma outra coisa.
        if (arr.length) {
            escreverDetalhe('pagina ' + pagina + ' chaves: ' + JSON.stringify(Object.keys(arr[0])));
            escreverDetalhe('pagina ' + pagina + ' item0: ' + JSON.stringify(arr[0]));
        } else {
            escreverDetalhe('pagina ' + pagina + ' corpo cru: ' + r.responseText.slice(0, 300));
        }

        return { dados: arr, fim: arr.length === 0 };
    }

    async function parcelasApi(idConta) {
        const todas = [];
        for (let pagina = 0; pagina < MAX_PAGINAS; pagina++) {
            const res = await umaPagina(idConta, pagina);
            if (res.fim) break;
            todas.push(...res.dados);
        }
        return todas;
    }

    function brl(txt) {
        if (!txt) return 0;
        const n = String(txt).replace(/[^\d,.-]/g, '').replace(/\./g, '').replace(',', '.');
        const v = parseFloat(n);
        return isNaN(v) ? 0 : v;
    }

    function fmt(n) {
        return Number(n).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    // ── FLUXO COMPLETO ──
    async function executar() {
        saida.innerHTML = '';
        btn.disabled = true;
        btn.textContent = 'Consultando...';

        const t0 = performance.now();
        try {
            const num = numeroProcessoDaPagina();
            escrever('processo na pagina: ' + (num || 'NAO ENCONTRADO'), num ? '#27ae60' : '#c0392b');
            if (!num) return;

            const contas = await buscar(num);
            if (!contas) return;

            // Etapa 2: saldo da CONTA, uma requisicao so.
            // Mesmo endpoint que o site usa em carregarContasAjax:
            //   GET .../extrato/conta/obterSaldo/{idConta}
            // Devolve valorSaldoCorrigidoFormatado, sem tocar em parcela.
            escrever('');
            escrever('2) GET obterSaldo/{idConta} — saldo da conta, uma requisicao',
                '#1e88e5');

            for (const conta of contas) {
                if (conta.temValorNoHtml) {
                    escrever('   conta ' + conta.numeroConta
                        + ': valor ja estava no HTML (' + conta.disponivelTexto
                        + ') — nenhuma requisicao', '#27ae60');
                    continue;
                }

                const t1 = performance.now();
                const r = await requisitar({
                    method: 'GET',
                    url: URL_PARCELAS + '/' + conta.idConta + '?_=' + Date.now(),
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    timeout: 30000
                });
                const ms1 = Math.round(performance.now() - t1);

                escreverDetalhe('url: ' + URL_PARCELAS.replace(HOST_ALVARA, '') + '/'
                    + conta.idConta);
                escreverDetalhe('status ' + r.status + ' em ' + ms1 + 'ms');
                escreverDetalhe('corpo: ' + r.responseText.slice(0, 400));

                let j = null;
                try { j = JSON.parse(r.responseText); } catch (e) { /* noop */ }
                if (!j) {
                    escrever('   conta ' + conta.numeroConta + ': resposta nao e JSON', '#c0392b');
                    continue;
                }

                const tipoCod = typeof j.codigoRetorno;
                const ok = String(j.codigoRetorno) === '0';
                escreverDetalhe('codigoRetorno: ' + JSON.stringify(j.codigoRetorno)
                    + ' (' + tipoCod + ')');

                if (!ok) {
                    escrever('   conta ' + conta.numeroConta + ': codigoRetorno '
                        + JSON.stringify(j.codigoRetorno) + ' | msg: '
                        + (j.msgUsuario || j.msgTecnica || '(vazia)'), '#c0392b');
                    continue;
                }

                const valor = typeof j.valorSaldoCorrigido === 'number'
                    ? j.valorSaldoCorrigido
                    : brl(j.valorSaldoCorrigidoFormatado);

                escreverDetalhe('valorSaldoCorrigidoFormatado: '
                    + JSON.stringify(j.valorSaldoCorrigidoFormatado));
                escreverDetalhe('valorCapitalAgendadoFormatado: '
                    + JSON.stringify(j.valorCapitalAgendadoFormatado));
                escreverDetalhe('valorCapitalBloqueadoFormatado: '
                    + JSON.stringify(j.valorCapitalBloqueadoFormatado));

                escrever('   SALDO DA CONTA ' + conta.numeroConta + ': ' + fmt(valor)
                    + ' em ' + ms1 + 'ms — nenhuma parcela lida',
                    valor > 0 ? '#27ae60' : '#c0392b');
            }

            escrever('');
            escrever('tempo total: ' + Math.round(performance.now() - t0) + 'ms', '#1e88e5');
        } catch (e) {
            escrever('ERRO: ' + (e && e.message ? e.message : e), '#c0392b');
            console.error('[SALDO-TESTE]', e);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Buscar saldo';
        }
    }

    // ── PAINEL ──
    function montarPainel() {
        if (document.getElementById('saldo-teste-painel')) return;
        if (!document.body) { setTimeout(montarPainel, 500); return; }

        painel = document.createElement('div');
        painel.id = 'saldo-teste-painel';
        painel.style.cssText = 'position:fixed;bottom:20px;right:20px;width:480px;max-height:70vh;' +
            'background:#fff;border:2px solid #1a7f37;border-radius:6px;z-index:2147483647;' +
            'font-family:monospace;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.3);display:flex;flex-direction:column;';

        const topo = document.createElement('div');
        topo.style.cssText = 'background:#1a7f37;color:#fff;padding:6px 10px;font-weight:bold;' +
            'display:flex;justify-content:space-between;align-items:center;';
        topo.textContent = 'TESTE — Saldo Alvará';

        const fechar = document.createElement('button');
        fechar.textContent = '✕';
        fechar.style.cssText = 'background:transparent;border:none;color:#fff;font-size:14px;cursor:pointer;';
        fechar.onclick = () => painel.remove();
        topo.appendChild(fechar);

        btn = document.createElement('button');
        btn.textContent = 'Buscar saldo';
        btn.style.cssText = 'margin:8px;padding:8px;background:#1a7f37;color:#fff;border:none;' +
            'border-radius:4px;font-weight:bold;cursor:pointer;font-size:13px;';
        btn.onclick = executar;

        saida = document.createElement('div');
        saida.style.cssText = 'flex:1;overflow-y:auto;padding:0 10px 10px;';

        painel.appendChild(topo);
        painel.appendChild(btn);
        painel.appendChild(saida);
        document.body.appendChild(painel);

        log('painel montado. Processo detectado:', numeroProcessoDaPagina());
    }

    montarPainel();
    let tentativas = 0;
    const timer = setInterval(() => {
        tentativas++;
        if (document.getElementById('saldo-teste-painel') || tentativas > 10) clearInterval(timer);
        else montarPainel();
    }, 800);
})();
