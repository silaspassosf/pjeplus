// ==UserScript==
// @name         PJe Argos — Teste Finalização (standalone)
// @namespace    pjeplus.argos.teste
// @version      1.1
// @description  Teste isolado da finalização pós-F5 do módulo Argos: fecha a aba ativa (/argos), dá F5 no /detalhe e executa visibilidade + limpeza GIGS. Funções copiadas verbatim de Script/modules/argos/argos.js.
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe
// @match        https://pje.trt2.jus.br/argos/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_deleteValue
// @grant        window.close
// @grant        unsafeWindow
// @run-at       document-end
// ==/UserScript==
(function () {
    'use strict';

    // Chave própria p/ não colidir com o módulo real (pjetools_argos_fluxo)
    const FLUXO_KEY = 'pjetools_argos_teste_fluxo';

    // ── Primitivas (iguais ao argos.js) ───────────────────────────────────
    const sleep = window.sleep || (ms => new Promise(r => setTimeout(r, ms)));
    const showToast = window.showToast || function (texto, cor, dur) {
        console.log('[ArgosTeste]', texto);
    };
    const waitElementVisible = window.waitElementVisible || (async function (sel, timeout) {
        timeout = timeout || 8000;
        const inicio = Date.now();
        while (Date.now() - inicio < timeout) {
            const el = document.querySelector(sel);
            if (el) return el;
            await sleep(100);
        }
        return null;
    });
    const normalize = window.normalizeText || function (s) {
        return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().trim();
    };

    // ── Persistência entre reloads (checkpoint, igual ao argos.js) ────────
    function _gmSet(key, val) {
        const s = (typeof val === 'string') ? val : JSON.stringify(val);
        try { if (typeof GM_setValue === 'function') { GM_setValue(key, s); return; } } catch (e) { /* ignore */ }
        try { sessionStorage.setItem(key, s); } catch (e2) { /* ignore */ }
    }
    function _gmGet(key) {
        let raw = null;
        try { if (typeof GM_getValue === 'function') raw = GM_getValue(key, null); } catch (e) { /* ignore */ }
        if (raw === null || raw === undefined) {
            try { raw = sessionStorage.getItem(key); } catch (e2) { /* ignore */ }
        }
        if (raw === null || raw === undefined) return null;
        if (typeof raw === 'object') return raw;
        try { return JSON.parse(raw); } catch (e) { return raw; }
    }
    function _gmDel(key) {
        try { if (typeof GM_deleteValue === 'function') { GM_deleteValue(key); return; } } catch (e) { /* ignore */ }
        try { sessionStorage.removeItem(key); } catch (e2) { /* ignore */ }
    }

    // ── API helpers (iguais ao argos.js) ──────────────────────────────────
    function _xsrf() {
        const c = document.cookie.split(';').map(s => s.trim())
            .find(s => s.toLowerCase().startsWith('xsrf-token='));
        return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
    }
    function _headers() {
        const h = { 'Accept': 'application/json', 'Content-Type': 'application/json', 'X-Grau-Instancia': '1' };
        const x = _xsrf();
        if (x) h['X-XSRF-TOKEN'] = x;
        return h;
    }
    function _idProcesso() {
        const m = window.location.pathname.match(/\/processo\/(\d+)/);
        return m ? m[1] : null;
    }
    async function _getJson(url) {
        const r = await fetch(url, { method: 'GET', credentials: 'include', headers: _headers() });
        if (!r.ok) throw new Error('HTTP ' + r.status + ': ' + url);
        return r.json();
    }
    async function _fetchPartes() {
        const id = _idProcesso();
        if (!id) return { ativo: [], passivo: [] };
        const raw = await _getJson(window.location.origin + '/pje-comum-api/api/processos/id/' + id + '/partes');
        const shape = function (lista) {
            return (lista || []).map(function (p) {
                return { nome: (p.nome || '').trim(), documento: (p.documento || '').trim() };
            });
        };
        return { ativo: shape(raw.ATIVO), passivo: shape(raw.PASSIVO), outros: shape(raw.TERCEIROS) };
    }

    // Número CNJ do processo (igual ao argos.js)
    function _numeroProcesso() {
        const re = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;
        let m = document.title.match(re);
        if (m) return m[0];
        const el = document.querySelector('.texto-numero-processo');
        if (el) {
            m = (el.textContent || '').match(re);
            if (m) return m[0];
        }
        return null;
    }

    // Aguarda a aba ARGOS ser fechada (igual ao argos.js)
    async function _aguardarAbaFechar(win, timeout) {
        timeout = timeout || 15 * 60 * 1000;
        const inicio = Date.now();
        while (Date.now() - inicio < timeout) {
            try {
                if (!win || win.closed) return true;
            } catch (e) { return true; }
            await sleep(1000);
        }
        return false;
    }

    // ── Interação (iguais ao argos.js) ────────────────────────────────────
    async function _clicarTexto(tag, textoNorm, timeout) {
        timeout = timeout || 10000;
        const alvo = normalize(textoNorm);
        const inicio = Date.now();
        while (Date.now() - inicio < timeout) {
            const els = Array.from(document.querySelectorAll(tag));
            const el = els.find(e => normalize(e.textContent).includes(alvo));
            if (el) {
                try { el.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
                el.click();
                return true;
            }
            await sleep(150);
        }
        return false;
    }

    async function _marcarCheckboxPorLabel(scopeSel, nome, timeout) {
        timeout = timeout || 10000;
        const alvo = normalize(nome);
        const inicio = Date.now();
        while (Date.now() - inicio < timeout) {
            const escopo = document.querySelector(scopeSel);
            if (escopo) {
                const cb = Array.from(escopo.querySelectorAll('mat-checkbox'))
                    .find(function (el) {
                        const lbl = el.querySelector('.mat-checkbox-label');
                        const txt = normalize(lbl ? lbl.textContent : '');
                        return txt.includes(alvo);
                    });
                if (cb) {
                    const input = cb.querySelector('input[type="checkbox"]');
                    if (input) {
                        if (input.checked) return true;
                        try { input.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
                        input.click();
                        await sleep(250);
                        return !!input.checked;
                    }
                }
            }
            await sleep(150);
        }
        return false;
    }

    // Marca o polo ativo na dialog "Visibilidade de Sigilo de Documento".
    // O checkbox tem aria-label="Selecionar {NOME}" (o label visual fica vazio);
    // fallback: linha da tabela cuja coluna Nome (3ª td) contém o nome.
    async function _marcarPoloAtivoDialog(ativoNome, timeout) {
        timeout = timeout || 10000;
        const alvo = normalize(ativoNome);
        const inicio = Date.now();
        while (Date.now() - inicio < timeout) {
            const escopo = document.querySelector('pje-doc-visibilidade-sigilo');
            if (escopo) {
                let cb = Array.from(escopo.querySelectorAll('mat-checkbox[aria-label^="Selecionar"]'))
                    .find(function (el) {
                        return normalize(el.getAttribute('aria-label')).includes(alvo);
                    });
                if (!cb) {
                    const rows = escopo.querySelectorAll('table.t-class tbody tr, pje-doc-visibilidade-sigilo-table tbody tr');
                    for (const row of Array.from(rows)) {
                        const nomeEl = row.querySelectorAll('td')[2];
                        if (nomeEl && normalize(nomeEl.textContent).includes(alvo)) {
                            cb = row.querySelector('mat-checkbox');
                            if (cb) break;
                        }
                    }
                }
                if (cb) {
                    const input = cb.querySelector('input[type="checkbox"]');
                    if (input) {
                        if (input.checked) {
                            console.log('[ArgosTeste] [dialog] polo ativo já marcado:', normalize(cb.getAttribute('aria-label') || ''));
                            return true;
                        }
                        try { input.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
                        input.click();
                        await sleep(300);
                        console.log('[ArgosTeste] [dialog] clicou checkbox:', normalize(cb.getAttribute('aria-label') || ''), '| agora checked:', input.checked);
                        return !!input.checked;
                    }
                }
            }
            await sleep(150);
        }
        console.warn('[ArgosTeste] [dialog] checkbox do polo ativo não encontrado. aria-labels na dialog:',
            Array.from(document.querySelectorAll('pje-doc-visibilidade-sigilo mat-checkbox[aria-label^="Selecionar"]')).map(function (el) {
                return normalize(el.getAttribute('aria-label')).slice(0, 50);
            }));
        return false;
    }

    // Abre a dialog "Visibilidade de Sigilo de Documento" do documento mais recente
    async function _abrirSigiloDocumentoMaisRecente(timeout) {
        timeout = timeout || 20000;
        // FIX: o clique correto é no botão button[name="Visibilidade para Sigilo"]
        // (ícone fa-plus). O [id^="doc_"] é o mat-card do título — NÃO abre a dialog.
        const SEL = 'button[name="Visibilidade para Sigilo"], button[aria-label^="Visibilidade para Sigilo"], button[mattooltip^="Visibilidade para Sigilo"]';
        const inicio = Date.now();
        let tentativas = 0;
        while (Date.now() - inicio < timeout) {
            tentativas++;
            const itens = document.querySelectorAll('li.tl-item-container');
            const primeiroItem = itens[0] || null;
            let alvo = primeiroItem ? primeiroItem.querySelector(SEL) : null;
            if (!alvo) alvo = document.querySelector(SEL);
            if (tentativas === 1 || tentativas % 5 === 0) {
                console.log('[ArgosTeste] [sigilo] tentativa', tentativas,
                    '| tl-item-container:', itens.length,
                    '| botão sigilo:', alvo ? (alvo.name || alvo.id) : 'null',
                    '| dialog visibilidade:', document.querySelectorAll('pje-doc-visibilidade-sigilo').length);
            }
            if (alvo) {
                try { alvo.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
                const elem = alvo.closest('button') || alvo;
                // espera curta p/ garantir o handler Angular pronto
                await sleep(150);
                console.log('[ArgosTeste] [sigilo] clicando em:', elem.name || elem.id, '| texto:', normalize(elem.textContent).slice(0, 40));
                try { elem.click(); } catch (e) { console.warn('[ArgosTeste] [sigilo] falha no click:', e.message); }
                const dialog = await waitElementVisible('pje-doc-visibilidade-sigilo', 8000);
                if (dialog) {
                    console.log('[ArgosTeste] [sigilo] dialog de visibilidade ABRIU');
                    return true;
                }
                console.warn('[ArgosTeste] [sigilo] clicou mas dialog não apareceu. Dialogs abertos:',
                    Array.from(document.querySelectorAll('.cdk-overlay-container .mat-dialog-container')).map(function (d) {
                        return normalize(d.textContent).slice(0, 50);
                    }));
            }
            await sleep(300);
        }
        console.warn('[ArgosTeste] [sigilo] esgotou o tempo. tl-item-container:', document.querySelectorAll('li.tl-item-container').length,
            '| botões sigilo:', document.querySelectorAll('button[name="Visibilidade para Sigilo"]').length);
        return false;
    }

    // Fluxo de finalização no /detalhe (visibilidade + limpeza GIGS)
    async function _fluxoFinalizacaoDetalhe(dados) {
        console.log('[ArgosTeste] === finalização no /detalhe iniciada ===');
        showToast('ArgosTeste: finalização no processo — aguarde', '#6f42c1', 5000);

        const alvoSel = 'li.tl-item-container, [id^="doc_"], app-processo-detalhe, pje-timeline, #documento';
        const timeline = await waitElementVisible(alvoSel, 30000);
        console.log('[ArgosTeste] [fluxo] timeline?', !!timeline, '| readyState:', document.readyState,
            '| tl-item-container:', document.querySelectorAll('li.tl-item-container').length,
            '| [id^=doc_]:', document.querySelectorAll('[id^="doc_"]').length,
            '| app-processo-detalhe:', document.querySelectorAll('app-processo-detalhe').length,
            '| #documento:', document.querySelectorAll('#documento').length);
        if (!timeline) {
            console.warn('[ArgosTeste] timeline do processo não carregou');
            showToast('ArgosTeste: timeline do processo não carregou', '#dc3545', 5000);
            return;
        }
        await sleep(800);
        const clicouRecente = await _clicarTexto('button, a, mat-button-toggle, .mat-button-toggle', 'mais recente', 2500);
        console.log('[ArgosTeste] [fluxo] clique "+ mais recente"?', clicouRecente);
        await sleep(300);

        const dialogOk = await _abrirSigiloDocumentoMaisRecente(20000);
        console.log('[ArgosTeste] [fluxo] dialog de visibilidade abriu?', dialogOk);
        if (!dialogOk) {
            console.warn('[ArgosTeste] dialog de visibilidade não abriu');
            showToast('ArgosTeste: dialog de visibilidade/sigilo não abriu', '#ff9800', 5000);
            return;
        }
        // aguarda a tabela da dialog renderizar antes de marcar
        await waitElementVisible('pje-doc-visibilidade-sigilo-table, table.t-class', 8000);
        await sleep(800);

        const ativoNome = dados && dados.ativo && dados.ativo[0] ? dados.ativo[0].nome : null;
        console.log('[ArgosTeste] [fluxo] polo ativo alvo:', ativoNome);
        let marcado = false;
        if (ativoNome) {
            marcado = await _marcarPoloAtivoDialog(ativoNome, 10000);
            console.log('[ArgosTeste] [fluxo] polo ativo marcado na dialog de visibilidade?', marcado);
        } else {
            console.warn('[ArgosTeste] polo ativo não disponível para marcar na dialog');
        }
        if (marcado) {
            await sleep(400);
            const clicouSalvar = await _clicarTexto('button', 'salvar', 10000);
            console.log('[ArgosTeste] [fluxo] "Salvar" clicado?', clicouSalvar);
        } else {
            console.warn('[ArgosTeste] [fluxo] polo ativo NÃO marcado — não clicou em Salvar');
        }
        await sleep(800);

        if (document.querySelector('pje-gigs-atividades')) {
            await _limparGigsArgos();
        } else {
            console.log('[ArgosTeste] sem pje-gigs-atividades nesta página — rode a limpeza na página do GIGS');
        }

        _gmDel(FLUXO_KEY);
        console.log('[ArgosTeste] finalização no /detalhe concluída');
        showToast('ArgosTeste: finalização concluída', '#28a745', 4000);
    }

    // Limpa atividades GIGS cuja descrição contenha ARGOS ou convênio(s), vencidas ou não
    async function _limparGigsArgos() {
        let removidas = 0;
        const clicarSim = async function () {
            await sleep(800);
            for (const b of document.querySelectorAll('button[color="primary"]')) {
                const s = b.querySelector('span.mat-button-wrapper');
                if (s && s.textContent.trim() === 'Sim') { b.click(); await sleep(1000); return true; }
            }
            return false;
        };
        let temMais = true;
        while (temMais) {
            temMais = false;
            const rows = Array.from(document.querySelectorAll('pje-gigs-atividades table tbody tr'));
            for (const row of rows) {
                try {
                    if (row.style.display === 'none') continue;
                    const descEl = row.querySelector('td .descricao');
                    if (!descEl) continue;
                    const desc = descEl.textContent.trim().toLowerCase();
                    const ehAlvo = desc.includes('argos') || desc.includes('convênio') || desc.includes('convenio');
                    if (!ehAlvo) continue;
                    const btnEx = row.querySelector('button[mattooltip="Excluir Atividade"]');
                    if (!btnEx) continue;
                    btnEx.click();
                    if (await clicarSim()) {
                        removidas++;
                        temMais = true;
                        break;
                    }
                } catch (e) {
                    console.warn('[ArgosTeste] GIGS limpeza erro:', e.message);
                }
            }
        }
        console.log('[ArgosTeste] GIGS limpeza concluída — removidas:', removidas);
        showToast('ArgosTeste: ' + removidas + ' atividade(s) GIGS removida(s)', removidas ? '#28a745' : '#dc3545', 4000);
        return removidas;
    }

    // Worker pós-F5: aguarda estabilização e executa a finalização
    async function _iniciarWorkerFinalizacao(dados) {
        console.log('[ArgosTeste] worker de finalização disparado após o F5');
        try {
            let tent = 0;
            while (document.readyState !== 'complete' && tent < 200) {
                await sleep(250);
                tent++;
            }
            await sleep(800);
            const alvoSel = 'li.tl-item-container, [id^="doc_"], app-processo-detalhe, pje-timeline, #documento';
            const inicio = Date.now();
            let pronto = null;
            while (Date.now() - inicio < 60000) {
                pronto = document.querySelector(alvoSel);
                if (pronto) break;
                await sleep(400);
            }
            if (!pronto) {
                console.warn('[ArgosTeste] worker: página do processo não estabilizou em 60s');
                showToast('ArgosTeste: página não estabilizou — finalização não executada', '#dc3545', 5000);
                return;
            }
            console.log('[ArgosTeste] worker: página estabilizada — executando finalização');
            await _fluxoFinalizacaoDetalhe(dados);
        } catch (e) {
            console.error('[ArgosTeste] worker de finalização erro:', e);
            showToast('ArgosTeste: erro na finalização — ' + e.message, '#dc3545', 5000);
        }
    }

    // ── UI ─────────────────────────────────────────────────────────────────
    function criarBotao(texto, fn, cor) {
        const btn = document.createElement('button');
        btn.textContent = texto;
        btn.style.cssText = 'position:fixed;bottom:16px;right:16px;z-index:2147483647;' +
            'padding:10px 16px;border:none;border-radius:20px;font:600 13px monospace;' +
            'background:' + (cor || '#6f42c1') + ';color:#fff;box-shadow:0 4px 16px rgba(0,0,0,.4);cursor:pointer;';
        btn.onclick = fn;
        document.body.appendChild(btn);
        return btn;
    }

    const isDetalhe = /\/processo\/\d+\/detalhe/.test(window.location.href);
    const isArgos = /\/argos\//.test(window.location.href);

    // Boot: no /detalhe, retoma a finalização se houver checkpoint (pós-F5)
    function _boot() {
        if (isDetalhe) {
            const fluxo = _gmGet(FLUXO_KEY);
            if (fluxo && fluxo.etapa === 'finalizar' &&
                Date.now() - (fluxo.ts || 0) < 30 * 60 * 1000 &&
                (!fluxo.path || fluxo.path === window.location.pathname)) {
                console.log('[ArgosTeste] checkpoint de finalização encontrado — retomando após o reload');
                _iniciarWorkerFinalizacao(fluxo.dados || {});
            } else if (fluxo) {
                _gmDel(FLUXO_KEY);
            }
        }
    }

    if (isDetalhe) {
        // Sequência idêntica ao argos.js: abre a aba ARGOS, aguarda ela ser
        // fechada (botão "Fechar aba ativa" na aba /argos), grava checkpoint e
        // dá F5; após o reload o boot retoma visibilidade + limpeza.
        criarBotao('🧪 Testar Sequência', async function (e) {
            e.preventDefault();
            e.stopPropagation();
            try {
                const numero = _numeroProcesso();
                if (!numero) {
                    alert('Número do processo não encontrado nesta página');
                    return;
                }
                console.log('[ArgosTeste] processo:', numero);
                const partes = await _fetchPartes();
                console.log('[ArgosTeste] partes via API:', JSON.stringify(partes));

                // 1) abre a aba ARGOS (igual ao executarArgos)
                const url = window.location.origin + '/argos/home-servidor/processos/' + numero;
                console.log('[ArgosTeste] abrindo aba ARGOS:', url);
                const win = window.open(url, '_blank');
                if (!win) {
                    console.warn('[ArgosTeste] popup bloqueado?');
                    alert('Popup bloqueado — permita popups para pje.trt2.jus.br');
                    return;
                }

                // 2) aguarda a aba ARGOS ser fechada (fecha a aba ativa)
                await _aguardarAbaFechar(win, 15 * 60 * 1000);
                console.log('[ArgosTeste] aba ARGOS fechada — gravando checkpoint e dando F5');

                // 3) checkpoint persistente + F5 (a finalização retoma no boot)
                _gmSet(FLUXO_KEY, {
                    etapa: 'finalizar',
                    dados: { numero: numero, ativo: partes.ativo, passivo: partes.passivo, valor: null },
                    path: window.location.pathname,
                    ts: Date.now()
                });
                console.log('[ArgosTeste] checkpoint gravado — F5 em /detalhe');
                window.location.reload();
            } catch (err) {
                console.error('[ArgosTeste] erro:', err);
                alert('Erro: ' + err.message);
            }
        }, '#0d6efd');
    } else if (isArgos) {
        // Reproduz o argos.js: após detectar a finalização, a aba se fecha sozinha
        console.log('[ArgosTeste] aba ARGOS aberta — fechando automaticamente em 1s (igual argos.js)');
        setTimeout(function () {
            console.log('[ArgosTeste] fechando aba ativa (automático)');
            try { window.close(); } catch (err) { console.warn('[ArgosTeste] falha ao fechar aba:', err); }
        }, 1000);
        // botão manual como fallback
        criarBotao('🧪 Fechar aba ativa', function (e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[ArgosTeste] fechando aba ativa (manual)');
            try { window.close(); } catch (err) { console.warn('[ArgosTeste] falha ao fechar aba:', err); }
        }, '#dc3545');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _boot);
    } else {
        _boot();
    }
})();
