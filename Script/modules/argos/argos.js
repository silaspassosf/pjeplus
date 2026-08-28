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
    const FINALIZAR_KEY = 'pjetools_argos_finalizar';

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

    // Fetch igual ao ApiWrapper do maispje (APIS/): SÓ Content-Type, sem X-XSRF-TOKEN/X-Grau-Instancia.
    async function _getValorDetalhado(url) {
        try {
            const r = await fetch(url, { method: 'GET', headers: { 'Content-Type': 'application/json' } });
            const txt = await r.text();
            console.log('[Argos] API status', r.status, url, '→', (txt || '').slice(0, 500));
            if (!r.ok) return null;
            try { return JSON.parse(txt); } catch (e) { console.warn('[Argos] resposta não-JSON:', (txt || '').slice(0, 200)); return null; }
        } catch (e) {
            console.warn('[Argos] fetch exceção:', e.message, url);
            return null;
        }
    }

    async function _obterValorExecucao() {
        const id = _idProcesso();
        if (!id) return null;

        // 1) GIGS — valor da execução (mesmo endpoint do maispje)
        const dados = await _getValorDetalhado(window.location.origin + '/pje-gigs-api/api/execucao/processo/' + id);
        const vGigs = dados && (dados.valor ?? dados.valorExecucao ?? dados.total);
        console.log('[Argos] valor da execução (GIGS):', vGigs, '| data:', dados && dados.data);
        const nGigs = _valorParaNumero(vGigs);
        if (nGigs > 0) return nGigs;

        // 2) PJeCalc — últimos cálculos (MESMOS params do ApiWrapper calculosProcesso do APIS/)
        const qs = new URLSearchParams({
            idProcesso: id,
            pagina: '1',
            tamanhoPagina: '10',
            ordenacaoCrescente: 'true',
            mostrarCalculosHomologados: 'true',
            incluirCalculosHomologados: 'true'
        });
        const calc = await _getValorDetalhado(window.location.origin + '/pje-comum-api/api/calculos/processo?' + qs.toString());
        const resultado = calc && Array.isArray(calc.resultado) ? calc.resultado : [];
        if (resultado.length) {
            let ultimo = resultado[0];
            let maior = new Date(1900, 1, 1).getTime();
            for (const c of resultado) {
                const dt = new Date(c.dataHoraImportacao).getTime();
                if (Number.isFinite(dt) && dt > maior) { maior = dt; ultimo = c; }
            }
            const v = ultimo && (ultimo.total ?? ultimo.valor ?? ultimo.valorExecucao);
            console.log('[Argos] valor (fallback PJeCalc):', v);
            const n = _valorParaNumero(v);
            if (n > 0) return n;
        } else {
            console.warn('[Argos] PJeCalc sem resultado (resultado vazio)');
        }
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
                const t = normalize(o.textContent); // normalizeText devolve MAIÚSCULAS
                if (!t.includes('POLO ATIVO')) return false;
                return (alvoDoc && t.includes(alvoDoc)) || (alvoNome && t.includes(alvoNome));
            });
            if (!opt) opt = opts.find(o => normalize(o.textContent).includes('POLO ATIVO'));
            if (opt) {
                try { opt.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
                return opt;
            }
            await sleep(150);
        }
        console.warn('[Argos] opção do polo ativo não encontrada. mat-options no DOM:', Array.from(document.querySelectorAll('mat-option')).map(function (o) {
            return normalize(o.textContent).slice(0, 60);
        }));
        return null;
    }

    // Clique robusto numa mat-option (Angular Material registra mousedown/click)
    function _clicarOpcao(opt) {
        try { opt.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
        // NÃO usar `view: window`: no sandbox do Tampermonkey isso lança
        // "MouseEvent constructor: 'view' member ... does not implement interface Window",
        // abortando o try antes de chegar no opt.click().
        const evOpts = { bubbles: true, cancelable: true };
        try {
            opt.dispatchEvent(new MouseEvent('mousedown', evOpts));
            opt.dispatchEvent(new MouseEvent('mouseup', evOpts));
            opt.dispatchEvent(new MouseEvent('click', evOpts));
        } catch (e) {
            console.warn('[Argos] falha ao disparar MouseEvent:', e.message);
        }
        try {
            if (typeof opt.click === 'function') opt.click();
        } catch (e) {
            console.warn('[Argos] falha no opt.click():', e.message);
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
    //  - considera APENAS linhas do polo PASSIVO (ATIVO e TERCEIROS são
    //    sempre ignorados — nunca marcados e fora da regra CPF/CNPJ);
    //  - entre as PASSIVO, marca o grupo líder do MESMO tipo de documento
    //    (CNPJ/CPF) — cobre os 3 casos pedidos:
    //      * só CNPJ           -> marca todos;
    //      * começa com CPF    -> marca só os CPF (líder);
    //      * CNPJ, CPF, CNPJ   -> marca só os primeiros CNPJ.
    // Retorna as linhas que devem ser marcadas.
    function _decidirSelecaoExecutados(linhas) {
        const executados = (linhas || []).filter(function (l) {
            return normalize(l.polo).includes('PASSIVO');
        });
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

    // Marca um mat-checkbox por texto do label dentro de um escopo (seletor CSS).
    // Usado nos convênios, na dialog de finalização e na dialog de visibilidade/sigilo.
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

    // Marca um convênio na dialog "Convênios" (SISBAJUD, RENAJUD, CNIB, SERASAJUD,
    // ARISP, INFOJUD e sub-opções DIRPF, DECRED, DOI, DIMOB). Ordem importa: o
    // INFOJUD deve ser marcado por último, pois revela as sub-opções.
    async function _marcarConvenio(nome, timeout) {
        return _marcarCheckboxPorLabel('app-escolher-convenios, .convenios', nome, timeout);
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

        // 7. Aguardar o clique manual em "Prosseguir" e o carregar da dialog de
        //    convênios (mat-stepper passo 1 -> app-escolher-convenios)
        console.log('[Argos] aguardando clique manual em "Prosseguir"...');
        showToast('Argos: clique em "Prosseguir" para continuar', '#6f42c1', 6000);
        const convenios = await waitElementVisible('app-escolher-convenios, .convenios', 60000);
        if (!convenios) {
            console.warn('[Argos] dialog de convênios não carregou');
            showToast('Argos: dialog de convênios não carregou', '#dc3545', 5000);
            return;
        }
        console.log('[Argos] dialog de convênios carregada');
        await sleep(500);

        // 8. Marcar convênios conforme a regra (flag cpf):
        //    cpf=true  -> SISBAJUD, RENAJUD, CNIB, SERASAJUD, ARISP, INFOJUD, DIRPF, DECRED, DOI, DIMOB
        //    cpf=false -> igual, MENOS o DIRPF
        const temCpf = window.PjeArgos && window.PjeArgos.temCpfSelecionado
            ? window.PjeArgos.temCpfSelecionado()
            : false;
        const ordem = temCpf
            ? ['SISBAJUD', 'RENAJUD', 'CNIB', 'SERASAJUD', 'ARISP', 'INFOJUD', 'DIRPF', 'DECRED', 'DOI', 'DIMOB']
            : ['SISBAJUD', 'RENAJUD', 'CNIB', 'SERASAJUD', 'ARISP', 'INFOJUD', 'DECRED', 'DOI', 'DIMOB'];
        console.log('[Argos] marcando convênios (flag cpf=' + temCpf + '):', ordem.join(', '));
        let marcados = 0;
        for (const nome of ordem) {
            if (await _marcarConvenio(nome, 10000)) {
                marcados++;
                await sleep(250);
            } else {
                console.warn('[Argos] convênio não marcado:', nome);
            }
        }
        showToast('Argos: ' + marcados + ' convênio(s) marcado(s)', marcados ? '#28a745' : '#dc3545', 4000);
        console.log('[Argos] fluxo de convênios concluído');

        // 9. Aguardar clique manual em "Encaminhar ordem de pesquisa" e a dialog
        //    "Finalizar expedição de ordem de pesquisa(s)"
        console.log('[Argos] aguardando clique manual em "Encaminhar ordem de pesquisa"...');
        showToast('Argos: clique em "Encaminhar ordem de pesquisa" para continuar', '#6f42c1', 6000);
        const confirma = await waitElementVisible('app-confirmacao-criacao-ordem, .paragrafo-detalhamento', 60000);
        if (!confirma) {
            console.warn('[Argos] dialog de confirmação da ordem não abriu');
            showToast('Argos: dialog de confirmação da ordem não abriu', '#dc3545', 5000);
            return;
        }
        console.log('[Argos] dialog "Finalizar expedição de ordem de pesquisa(s)" aberta');
        await sleep(500);

        // 9.1 Marcar "Atribuir sigilo aos documentos juntados" (mat-checkbox-27 no probe)
        const sigiloOk = await _marcarCheckboxPorLabel('app-confirmacao-criacao-ordem', 'Atribuir sigilo aos documentos juntados', 8000);
        console.log('[Argos] "Atribuir sigilo aos documentos juntados" marcado?', sigiloOk);

        // 9.2 Confirmar
        if (!(await _clicarTexto('button', 'confirmar', 10000))) {
            console.warn('[Argos] botão "Confirmar" não encontrado');
            showToast('Argos: botão "Confirmar" não encontrado', '#dc3545', 5000);
            return;
        }
        console.log('[Argos] "Confirmar" clicado');

        // 9.3 Aguardar snackbar de sucesso e fechar
        const snack = await _aguardarElementoPorTexto('simple-snack-bar', 'ordem de pesquisa(s) criada com sucesso', 20000);
        if (snack) {
            const fechar = snack.querySelector('.mat-simple-snackbar-action button, button');
            if (fechar) fechar.click();
            console.log('[Argos] snackbar de sucesso reconhecida — fechando');
            await sleep(600);
        } else {
            console.warn('[Argos] snackbar de sucesso não apareceu');
        }

        // 9.4 Fechar a aba ARGOS (a finalização no /detalhe segue via window.closed)
        console.log('[Argos] fluxo concluído — fechando aba ARGOS');
        try { window.close(); } catch (e) { console.warn('[Argos] falha ao fechar aba:', e.message); }
    }

    // Prompt nativo para o usuário informar o valor da execução quando a API
    // não detectar. Funciona no sandbox do Tampermonkey (window.prompt).
    function _promptValor() {
        try {
            if (typeof window.prompt === 'function') {
                return window.prompt('Informar valor sem virgula ou ponto', '');
            }
            if (typeof unsafeWindow !== 'undefined' && unsafeWindow.prompt) {
                return unsafeWindow.prompt('Informar valor sem virgula ou ponto', '');
            }
        } catch (e) {
            console.warn('[Argos] prompt indisponível:', e);
        }
        return null;
    }

    // Aguarda (sem clicar) um elemento cujo texto normalizado contém textoNorm
    async function _aguardarElementoPorTexto(tag, textoNorm, timeout) {
        timeout = timeout || 10000;
        const alvo = normalize(textoNorm);
        const inicio = Date.now();
        while (Date.now() - inicio < timeout) {
            const els = Array.from(document.querySelectorAll(tag));
            const el = els.find(e => normalize(e.textContent).includes(alvo));
            if (el) return el;
            await sleep(150);
        }
        return null;
    }

    // Aguarda a aba ARGOS (aberta via window.open) ser fechada pelo fluxo
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

    // Abre a dialog "Visibilidade de Sigilo de Documento" do documento mais recente
    // (primeiro item da timeline, que é DESC) e retorna true se a dialog abriu
    async function _abrirSigiloDocumentoMaisRecente(timeout) {
        timeout = timeout || 20000;
        const inicio = Date.now();
        while (Date.now() - inicio < timeout) {
            const primeiroItem = document.querySelector('li.tl-item-container');
            const base = primeiroItem || document;
            const alvo = base.querySelector('[id^="doc_"], [mattooltip*="Visibilidade"], [title*="Visibilidade"], i.fa-eye, .icone-visibilidade');
            if (alvo) {
                try { alvo.scrollIntoView({ block: 'nearest' }); } catch (e) { /* ignore */ }
                const elem = alvo.closest('button') || alvo;
                try { elem.click(); } catch (e) { /* ignore */ }
                const dialog = await waitElementVisible('pje-doc-visibilidade-sigilo', 6000);
                if (dialog) return true;
            }
            await sleep(200);
        }
        return false;
    }

    // Finalização no /detalhe após o fluxo ARGOS (roda no boot, após o F5):
    // 1) estabiliza, 2) "+ mais recente", 3) visibilidade/sigilo do doc mais
    // recente marcando o polo ativo e salvando, 4) limpa GIGS ARGOS/convênios.
    async function _fluxoFinalizacaoDetalhe(dados) {
        console.log('[Argos] finalização no /detalhe iniciada');
        showToast('Argos: finalização no processo — aguarde', '#6f42c1', 5000);

        // 1. estabilizar a página após o F5
        const timeline = await waitElementVisible('li.tl-item-container, [id^="doc_"]', 30000);
        if (!timeline) {
            console.warn('[Argos] timeline do processo não carregou');
            showToast('Argos: timeline do processo não carregou', '#dc3545', 5000);
            return;
        }
        await sleep(1000);
        // "+ mais recente" (toggle/filtro) se existir
        await _clicarTexto('button, a, mat-button-toggle, .mat-button-toggle', 'mais recente', 5000);

        // 2. abrir visibilidade/sigilo do documento mais recente
        const dialogOk = await _abrirSigiloDocumentoMaisRecente(20000);
        if (!dialogOk) {
            console.warn('[Argos] dialog de visibilidade não abriu');
            showToast('Argos: dialog de visibilidade/sigilo não abriu', '#ff9800', 5000);
            return;
        }
        await sleep(600);

        // 3. marcar o polo ativo na dialog e salvar
        const ativoNome = dados && dados.ativo && dados.ativo[0] ? dados.ativo[0].nome : null;
        if (ativoNome) {
            const marcado = await _marcarCheckboxPorLabel('pje-doc-visibilidade-sigilo', ativoNome, 10000);
            console.log('[Argos] polo ativo marcado na dialog de visibilidade?', marcado);
        } else {
            console.warn('[Argos] polo ativo não disponível para marcar na dialog');
        }
        if (await _clicarTexto('button', 'salvar', 10000)) {
            console.log('[Argos] "Salvar" clicado na dialog de visibilidade');
        }
        await sleep(800);

        // 4. limpeza GIGS (ARGOS/convênios) se a página tiver atividades GIGS
        if (document.querySelector('pje-gigs-atividades')) {
            await _limparGigsArgos();
        } else {
            console.log('[Argos] sem pje-gigs-atividades nesta página — rode window.limparGigsArgos() na página do GIGS');
        }

        // limpa o flag de finalização
        try { sessionStorage.removeItem(FINALIZAR_KEY); } catch (e) { /* ignore */ }
        console.log('[Argos] finalização no /detalhe concluída');
        showToast('Argos: finalização concluída', '#28a745', 4000);
    }

    // Limpa atividades GIGS cuja descrição contenha ARGOS ou convênio(s),
    // vencidas ou não — seguindo o padrão do bookmarklet GIGS_CLEANUP.
    // Usar na página de atividades do GIGS (onde existe pje-gigs-atividades).
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
                    console.warn('[Argos] GIGS limpeza erro:', e.message);
                }
            }
        }
        console.log('[Argos] GIGS limpeza concluída — removidas:', removidas);
        showToast('Argos: ' + removidas + ' atividade(s) GIGS removida(s)', removidas ? '#28a745' : '#dc3545', 4000);
        return removidas;
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
            // Se o valor não foi detectado, pede para o usuário informar antes de abrir o ARGOS
            let valorFinal = (valor && valor > 0) ? valor : null;
            if (!valorFinal) {
                const entrada = _promptValor();
                if (entrada !== null && String(entrada).trim() !== '') {
                    valorFinal = _valorParaNumero(entrada);
                    console.log('[Argos] valor informado manualmente:', entrada, '→', valorFinal);
                    showToast('Argos: valor informado manualmente', '#6f42c1', 3000);
                } else {
                    console.warn('[Argos] valor não informado manualmente — segue sem valor');
                }
            }
            const dados = { numero, valor: valorFinal, ativo: partes.ativo, passivo: partes.passivo };
            try { sessionStorage.setItem(KEY, JSON.stringify(dados)); } catch (e) { console.warn('[Argos] sessionStorage indisponível:', e); }
            const url = window.location.origin + '/argos/home-servidor/processos/' + numero;
            console.log('[Argos] abrindo:', url);
            const win = window.open(url, '_blank');
            if (!win) {
                console.warn('[Argos] popup bloqueado?');
                showToast('Argos: popup bloqueado — permita popups para pje.trt2.jus.br', '#dc3545', 5000);
                return;
            }

            // Aguarda a aba ARGOS concluir o fluxo (inclui os cliques manuais em
            // "Prosseguir" e "Encaminhar ordem de pesquisa") e fechar; então
            // finaliza no /detalhe.
            await _aguardarAbaFechar(win, 15 * 60 * 1000);
            console.log('[Argos] aba ARGOS fechada — iniciando finalização no /detalhe');
            try {
                sessionStorage.setItem(FINALIZAR_KEY, JSON.stringify({
                    numero: numero,
                    ativo: partes.ativo,
                    passivo: partes.passivo,
                    valor: valorFinal
                }));
            } catch (e) { console.warn('[Argos] sessionStorage indisponível p/ finalização:', e); }
            // F5 para a página ver o documento juntado (a finalização roda no boot)
            window.location.reload();
        } catch (e) {
            console.error('[Argos] erro ao obter dados:', e);
            showToast('Argos: erro ao obter dados — ' + e.message, '#dc3545', 5000);
        }
    };

    window.limparGigsArgos = _limparGigsArgos;

    // API pública do módulo
    window.PjeArgos = {
        executar: window.executarArgos,
        fluxo: executarFluxoArgos,
        _decidirSelecao: _decidirSelecaoExecutados, // helper de teste/debug
        temCpfSelecionado: function () {
            try { return sessionStorage.getItem(FLAG_CPF_KEY) === '1'; } catch (e) { return false; }
        },
        limparGigs: _limparGigsArgos,
    };

    // ── Boot: na página /argos, executa o fluxo se houver dados pendentes;
    //    no /detalhe, roda a finalização se o fluxo Argos a deixou pendente ──
    async function _boot() {
        // Finalização no /detalhe após fluxo ARGOS (flag persiste pelo F5)
        if (/\/processo\/\d+\/detalhe/.test(window.location.href)) {
            let finalRaw = null;
            try { finalRaw = sessionStorage.getItem(FINALIZAR_KEY); } catch (e) { /* ignore */ }
            if (finalRaw) {
                let finalDados;
                try { finalDados = JSON.parse(finalRaw); } catch (e) { /* ignore */ }
                await _fluxoFinalizacaoDetalhe(finalDados || {});
            }
            return;
        }
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
