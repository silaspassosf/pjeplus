// ==UserScript==
// @name         PJeTools Argos
// @namespace    http://tampermonkey.net/
// @description  Botão Argos na lista check: abre "Nova Pesquisa" no ARGOS preenchida a partir do processo PJe (polo ativo, polo passivo e valor da execução via API)
// @author       Silas
// ==/UserScript==
'use strict';

(function () {
    const KEY = 'pjetools_argos_dados';
    const FLAG_CPF_KEY = 'pjetools_argos_tem_cpf';

    // ── Primitivas (fallback caso core/utils.js não tenha carregado) ──────
    const sleep = window.sleep || (ms => new Promise(r => setTimeout(r, ms)));
    const showToast = window.showToast || function (texto, cor, dur) {
        console.log('[Argos]', texto);
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
    const parseMoney = window.parseMoney || function (s) {
        if (!s) return 0;
        const n = parseFloat(String(s).replace(/R\$\s*/g, '').replace(/\./g, '').replace(',', '.').trim());
        return Number.isFinite(n) ? n : 0;
    };

    // ── API helpers (mesmo padrão do hcalc-prep) ───────────────────────────
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

    // Número do processo no padrão CNJ (nnnnnnn-nn.nnnn.5.02.nnnn) — do título ou do DOM
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

    // Polo ativo + passivo via /partes (mesmo endpoint do hcalc-prep)
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

    function _valorParaNumero(v) {
        if (v === null || v === undefined) return 0;
        if (typeof v === 'number') return Number.isFinite(v) ? v : 0;
        const s = String(v).trim().replace(/R\$\s*/g, '');
        if (!s) return 0;
        // ponto como decimal (ex.: "241561.65") sem vírgula -> número direto
        if (!s.includes(',') && /^\d+(\.\d+)?$/.test(s)) return parseFloat(s) || 0;
        // senão, formatação pt-BR (ex.: "241.561,65")
        return parseMoney(s);
    }

    async function _obterValorExecucao() {
        const id = _idProcesso();
        if (!id) return null;
        // Fonte correta do valor da execução: GIGS
        try {
            const dados = await _getJson(window.location.origin + '/pje-gigs-api/api/execucao/processo/' + id);
            const v = dados && dados.valor;
            console.log('[Argos] valor da execução (GIGS):', v, '| data:', dados && dados.data);
            const n = _valorParaNumero(v);
            if (n > 0) return n;
        } catch (e) {
            console.warn('[Argos] API GIGS execução falhou:', e.message);
        }
        // fallback PJeCalc — último cálculo do processo (mesmo do gigs-plugin SISBAJUD)
        try {
            const calc = await _getJson(window.location.origin + '/pje-comum-api/api/calculos/processo?idProcesso=' + id);
            const resultado = calc && Array.isArray(calc.resultado) ? calc.resultado : [];
            if (resultado.length) {
                let ultimo = resultado[0];
                let maior = new Date(1900, 1, 1).getTime();
                for (const c of resultado) {
                    const dt = new Date(c.dataHoraImportacao).getTime();
                    if (Number.isFinite(dt) && dt > maior) { maior = dt; ultimo = c; }
                }
                const v = ultimo && ultimo.total;
                console.log('[Argos] valor (fallback PJeCalc):', v);
                const n = _valorParaNumero(v);
                if (n > 0) return n;
            }
        } catch (e) { /* fallback indisponível */ }
        return null;
    }

    // ── Helpers de interação (SPA Angular) ─────────────────────────────────

    // Clica no primeiro elemento de `tag` cujo texto normalizado contém `textoNorm`
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

    // Digita dígito por dígito (máscara de moeda processa) — "digitado, não colado"
    async function _digitarMoeda(input, digitos) {
        const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        input.focus();
        await sleep(80);
        set.call(input, '');
        input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward' }));
        await sleep(40);
        for (const ch of digitos) {
            input.dispatchEvent(new KeyboardEvent('keydown', { key: ch, bubbles: true, cancelable: true }));
            input.dispatchEvent(new KeyboardEvent('keypress', { key: ch, bubbles: true, cancelable: true, charCode: ch.charCodeAt(0) }));
            input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: ch }));
            input.dispatchEvent(new KeyboardEvent('keyup', { key: ch, bubbles: true }));
            await sleep(30);
        }
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function _tipoDoc(doc) {
        const d = String(doc || '').replace(/\D/g, '');
        if (d.length === 11) return 'CPF';
        if (d.length === 14) return 'CNPJ';
        return null;
    }

    // ── Fluxo no ARGOS ─────────────────────────────────────────────────────

    // Aguarda o dropdown do autocomplete e devolve a mat-option do POLO ATIVO
    async function _aguardarOpcaoAtivo(ativo, timeout) {
        timeout = timeout || 8000;
        const alvoNome = normalize(ativo.nome);
        const alvoDoc = String(ativo.documento || '').replace(/\D/g, '');
        const inicio = Date.now();
        while (Date.now() - inicio < timeout) {
            const opts = Array.from(document.querySelectorAll('mat-option'));
            let opt = opts.find(function (o) {
                const t = normalize(o.textContent);
                if (!t.includes('polo ativo')) return false;
                return (alvoDoc && t.includes(alvoDoc)) || (alvoNome && t.includes(alvoNome));
            });
            if (!opt) opt = opts.find(o => normalize(o.textContent).includes('polo ativo'));
            if (opt) {
                try { opt.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
                return opt;
            }
            await sleep(150);
        }
        return null;
    }

    // Clique robusto numa mat-option (Angular Material registra mousedown/click)
    function _clicarOpcao(opt) {
        try { opt.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
        try {
            opt.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
            opt.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
            opt.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
            if (typeof opt.click === 'function') opt.click();
        } catch (e) {
            console.warn('[Argos] falha ao clicar na opção:', e.message);
        }
    }

    // Confirma que o campo foi preenchido com o polo ativo após o clique
    async function _confirmarPoloAtivoPreenchido(input, ativo, timeout) {
        timeout = timeout || 6000;
        const alvoNome = normalize(ativo.nome);
        const alvoDoc = String(ativo.documento || '').replace(/\D/g, '');
        const inicio = Date.now();
        while (Date.now() - inicio < timeout) {
            const valor = normalize(input.value || '');
            if (valor && ((alvoDoc && valor.includes(alvoDoc)) || (alvoNome && valor.includes(alvoNome)))) {
                console.log('[Argos] campo polo ativo preenchido:', input.value);
                return true;
            }
            await sleep(150);
        }
        console.warn('[Argos] polo ativo NÃO confirmado no campo. Valor atual:', input.value);
        return false;
    }

    // Decisão pura de seleção de executados (testável):
    //  - ignora linhas do polo ATIVO;
    //  - entre as demais, marca o grupo líder do MESMO tipo de documento
    //    (CNPJ/CPF) — cobre os 3 casos pedidos:
    //      * só CNPJ           -> marca todos;
    //      * começa com CPF    -> marca só os CPF (líder);
    //      * CNPJ, CPF, CNPJ   -> marca só os primeiros CNPJ.
    // Retorna as linhas que devem ser marcadas.
    function _decidirSelecaoExecutados(linhas) {
        const executados = (linhas || []).filter(l => !normalize(l.polo).includes('ATIVO'));
        const tipados = executados.map(function (l) {
            return { l, tipo: _tipoDoc(l.doc) };
        }).filter(x => x.tipo);
        if (!tipados.length) return [];
        const primeiroTipo = tipados[0].tipo;
        const selecionados = [];
        for (const t of tipados) {
            if (t.tipo !== primeiroTipo) break;
            selecionados.push(t.l);
        }
        return selecionados;
    }

    // Seleção de executados: aplica _decidirSelecaoExecutados e marca os checkboxes
    async function _selecionarExecutados(timeout) {
        timeout = timeout || 12000;
        const tab = await waitElementVisible(
            '.executados app-tabela-executados table, mat-dialog-container table',
            timeout
        );
        if (!tab) {
            showToast('Argos: tabela de executados não encontrada', '#dc3545', 5000);
            return;
        }
        // Linhas: data-cy^="executado-" (padrão) ou cdk-row com coluna Polo
        const rows = Array.from(tab.querySelectorAll('tr[data-cy^="executado-"], tr.cdk-row')).filter(function (row) {
            const poloEl = row.querySelector('td.mat-column-polo label') || row.querySelectorAll('td')[3];
            return !!poloEl;
        });
        const linhas = rows.map(function (row) {
            const docEl = row.querySelector('td.mat-column-documento label') || row.querySelectorAll('td')[1];
            const nomeEl = row.querySelector('td.mat-column-nome label') || row.querySelectorAll('td')[2];
            const poloEl = row.querySelector('td.mat-column-polo label') || row.querySelectorAll('td')[3];
            const cbInput = row.querySelector('input[type="checkbox"]');
            return {
                row,
                cbInput,
                doc: docEl ? docEl.textContent.trim() : '',
                nome: nomeEl ? nomeEl.textContent.trim() : '',
                polo: normalize(poloEl ? poloEl.textContent : ''),
            };
        });
        console.log('[Argos] linhas de executados lidas:', linhas.length);

        const selecionados = _decidirSelecaoExecutados(linhas);
        if (!selecionados.length) {
            showToast('Argos: nenhum executado com CPF/CNPJ na tabela', '#dc3545', 5000);
            return;
        }
        let marcados = 0;
        for (const l of selecionados) {
            // Clique no input nativo (#checkbox-N-input, confirmado por probe)
            const cb = l.cbInput;
            if (cb) {
                if (cb.checked) continue;
                try { cb.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
                cb.click();
                marcados++;
                await sleep(120);
                continue;
            }
            // fallback: clicar no mat-checkbox
            const mcb = l.row.querySelector('mat-checkbox');
            if (!mcb) continue;
            const inp = mcb.querySelector('input[type="checkbox"]');
            if (inp && inp.checked) continue;
            try { mcb.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
            mcb.click();
            marcados++;
            await sleep(120);
        }

        // Flag p/ a próxima página: ao menos um CPF entre os executados selecionados
        const temCpf = selecionados.some(function (l) { return _tipoDoc(l.doc) === 'CPF'; });
        try { sessionStorage.setItem(FLAG_CPF_KEY, temCpf ? '1' : '0'); } catch (e) { /* ignore */ }
        if (window.PjeArgos) window.PjeArgos.temCpf = temCpf;
        console.log('[Argos] selecionouCpf =', temCpf, '| selecionados:', selecionados.map(function (l) {
            return l.nome + ' (' + (_tipoDoc(l.doc) || '?') + ')';
        }));

        showToast('Argos: ' + marcados + ' executado(s) selecionado(s)', marcados ? '#28a745' : '#dc3545', 4000);
    }

    async function executarFluxoArgos(dados) {
        console.log('[Argos] fluxo iniciado — dados:', JSON.stringify(dados));
        showToast('Argos: iniciando fluxo de "Nova Pesquisa"...', '#6f42c1', 3000);

        // 1. "Ordens em cumprimento"
        if (!(await _clicarTexto('mat-panel-title', 'ordens em cumprimento', 20000))) {
            console.warn('[Argos] painel "Ordens em cumprimento" não encontrado');
            showToast('Argos: painel "Ordens em cumprimento" não encontrado', '#dc3545', 5000);
            return;
        }
        console.log('[Argos] painel "Ordens em cumprimento" clicado');
        await sleep(700); // deixa o painel expandir

        // 2. "Nova ordem"
        if (!(await _clicarTexto('button', 'nova ordem', 15000))) {
            console.warn('[Argos] botão "Nova ordem" não encontrado');
            showToast('Argos: botão "Nova ordem" não encontrado', '#dc3545', 5000);
            return;
        }
        console.log('[Argos] botão "Nova ordem" clicado');
        await sleep(900); // deixa o diálogo abrir

        // 3. Diálogo "Nova Pesquisa" (mat-dialog-container confirmado por probe)
        const h = await waitElementVisible(
            'mat-dialog-container[role="dialog"], h1.titulo-nova-ordem',
            12000
        );
        if (!h) {
            console.warn('[Argos] diálogo "Nova Pesquisa" não abriu');
            showToast('Argos: diálogo "Nova Pesquisa" não abriu', '#dc3545', 5000);
            return;
        }
        console.log('[Argos] diálogo "Nova Pesquisa" aberto');
        await sleep(500);

        // 4. Valor da execução (apenas números, digitado)
        if (dados.valor && dados.valor > 0) {
            const inValor = await waitElementVisible(
                'input[data-cy="input-valor-execucao"], input[aria-label="Digite o valor da execução"]',
                8000
            );
            if (inValor) {
                const centavos = String(Math.round(dados.valor * 100));
                console.log('[Argos] digitando valor da execução:', dados.valor, '→ dígitos:', centavos);
                await _digitarMoeda(inValor, centavos);
                console.log('[Argos] valor digitado — campo agora:', JSON.stringify(inValor.value));
            } else {
                console.warn('[Argos] input de valor da execução não encontrado');
            }
        } else {
            console.warn('[Argos] valor da execução não detectado (dados.valor =', dados.valor, ')');
            showToast('Argos: valor da execução não detectado — preencher manualmente', '#ff9800', 4000);
        }

        // 5. Selecionar o POLO ATIVO: clicar no campo abre o dropdown (sem digitar);
        //    clicar na linha (Polo ATIVO) e CONFIRMAR que o campo foi preenchido
        let poloAtivoOk = false;
        const ativo = dados.ativo && dados.ativo[0];
        if (ativo) {
            const inDoc = await waitElementVisible('input[aria-label="Digite o documento ou o nome"], input[data-placeholder="Digite o documento ou o nome"]', 8000);
            if (inDoc) {
                for (let tentativa = 0; tentativa < 2 && !poloAtivoOk; tentativa++) {
                    inDoc.click();
                    console.log('[Argos] campo "documento ou nome" clicado (tentativa ' + (tentativa + 1) + ')');
                    const opt = await _aguardarOpcaoAtivo(ativo, 8000);
                    if (opt) {
                        console.log('[Argos] opção do polo ativo encontrada:', opt.textContent.trim().slice(0, 80));
                        _clicarOpcao(opt);
                        poloAtivoOk = await _confirmarPoloAtivoPreenchido(inDoc, ativo, 6000);
                        console.log('[Argos] polo ativo confirmado?', poloAtivoOk);
                    } else {
                        console.warn('[Argos] opção do polo ativo não encontrada no dropdown (tentativa ' + (tentativa + 1) + ')');
                        showToast('Argos: opção do polo ativo não encontrada no dropdown', '#ff9800', 4000);
                        break;
                    }
                }
                if (!poloAtivoOk) {
                    showToast('Argos: não foi possível confirmar o polo ativo no campo', '#dc3545', 5000);
                }
            } else {
                console.warn('[Argos] campo "documento ou nome" não encontrado');
            }
        } else {
            console.warn('[Argos] polo ativo não identificado (dados.ativo =', JSON.stringify(dados.ativo), ')');
            showToast('Argos: polo ativo não identificado', '#ff9800', 4000);
        }

        // 6. Selecionar executados — só após confirmar o polo ativo preenchido
        if (poloAtivoOk) {
            console.log('[Argos] iniciando seleção de executados');
            await _selecionarExecutados(12000);
        } else {
            console.warn('[Argos] executados NÃO selecionados (polo ativo não confirmado)');
        }
    }

    // ── Botão (na página /detalhe) ─────────────────────────────────────────
    window.executarArgos = async function () {
        try {
            // reseta flag de execução anterior (a próxima página re-definirá)
            try { sessionStorage.removeItem(FLAG_CPF_KEY); } catch (e) { /* ignore */ }
            const numero = _numeroProcesso();
            if (!numero) {
                showToast('Argos: número do processo não encontrado nesta página', '#dc3545', 4000);
                return;
            }
            console.log('[Argos] processo:', numero);
            const partes = await _fetchPartes();
            console.log('[Argos] partes via API:', JSON.stringify(partes));
            const valor = await _obterValorExecucao();
            console.log('[Argos] valor da execução final:', valor);
            const dados = { numero, valor, ativo: partes.ativo, passivo: partes.passivo };
            try { sessionStorage.setItem(KEY, JSON.stringify(dados)); } catch (e) { console.warn('[Argos] sessionStorage indisponível:', e); }
            const url = window.location.origin + '/argos/home-servidor/processos/' + numero;
            console.log('[Argos] abrindo:', url);
            window.open(url, '_blank');
        } catch (e) {
            console.error('[Argos] erro ao obter dados:', e);
            showToast('Argos: erro ao obter dados — ' + e.message, '#dc3545', 5000);
        }
    };

    // API pública do módulo
    window.PjeArgos = {
        executar: window.executarArgos,
        fluxo: executarFluxoArgos,
        _decidirSelecao: _decidirSelecaoExecutados, // helper de teste/debug
        temCpfSelecionado: function () {
            try { return sessionStorage.getItem(FLAG_CPF_KEY) === '1'; } catch (e) { return false; }
        },
    };

    // ── Boot: na página /argos, executa o fluxo se houver dados pendentes ──
    async function _boot() {
        if (!/\/argos\//.test(window.location.href)) return;
        let raw = null;
        try { raw = sessionStorage.getItem(KEY); } catch (e) { /* ignore */ }
        if (!raw) { console.log('[Argos] página /argos sem dados pendentes'); return; }
        try { sessionStorage.removeItem(KEY); } catch (e) { /* ignore */ }
        let dados;
        try { dados = JSON.parse(raw); } catch (e) { console.error('[Argos] dados inválidos no sessionStorage'); return; }
        console.log('[Argos] dados recebidos na página /argos:', dados);
        await waitElementVisible('mat-panel-title, .mat-expansion-panel', 20000);
        await executarFluxoArgos(dados);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { _boot(); });
    } else {
        _boot();
    }
})();
