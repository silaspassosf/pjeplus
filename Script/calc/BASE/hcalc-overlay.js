(function () {
    'use strict';
    const HCALC_DEBUG = true;
    const dbg = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err = (...args) => console.error('[hcalc]', ...args);
    // Proxies para dependencias de hcalc-core.js e hcalc-pdf.js
    const normalizarNomeParaComparacao = n => window.normalizarNomeParaComparacao(n);
    const carregarPDFJSSeNecessario = () => window.carregarPDFJSSeNecessario();
    const processarPlanilhaPDF = (...a) => window.processarPlanilhaPDF(...a);
    const executarPrep = (...a) => window.executarPrep(...a);
    const destacarElementoNaTimeline = (...a) => window.destacarElementoNaTimeline(...a);
    const encontrarItemTimeline = (href) => window.encontrarItemTimeline && window.encontrarItemTimeline(href);
    const expandirAnexos = (item) => window.expandirAnexos && window.expandirAnexos(item);
    const overlayDraftApi = window.hcalcOverlayDraft;
    // Função pública para forçar limpeza de rascunho/estado e permitir carregar nova planilha
    window.hcalcForceClearAndLoadNew = function () {
        try {
            const m = window.location.pathname.match(/processo\/([^/]+)/i);
            const pid = m ? m[1] : null;
            if (pid) {
                const key = `hcalc-overlay-draft:${pid}`;
                localStorage.removeItem(key);
                dbg('[hcalc] removed draft key', key);
            } else {
                Object.keys(localStorage).filter(k => k.startsWith('hcalc-overlay-draft:')).forEach(k => {
                    localStorage.removeItem(k);
                    dbg('[hcalc] removed draft key (no pid)', k);
                });
            }
        } catch (e) { dbg('[hcalc] force clear localStorage failed', e); }

        try {
            if (window.hcalcState) {
                if (typeof window.hcalcState.resetPrep === 'function') {
                    window.hcalcState.resetPrep();
                } else {
                    window.hcalcState = {};
                }
            } else {
                window.hcalcState = {};
            }
            dbg('[hcalc] window.hcalcState cleared');
        } catch (e) { dbg('[hcalc] clearing window.hcalcState failed', e); }

        try { if (typeof window.hcalcDispose === 'function') { window.hcalcDispose(); dbg('[hcalc] called hcalcDispose()'); } } catch (e) { dbg('[hcalc] dispose call failed', e); }

        try { document.querySelectorAll('.hcalc-overlay, [data-hcalc-root], #hcalc-overlay, #homologacao-overlay').forEach(el => el.remove()); } catch (e) { /* ignore */ }
        try { document.querySelectorAll('input[type=file]').forEach(f => { try { f.value = ''; } catch (e) { } }); } catch (e) { /* ignore */ }

        if (typeof window.hcalcInitBotao === 'function') {
            try { window.hcalcInitBotao(); dbg('[hcalc] hcalcInitBotao() re-called'); } catch (e) { dbg('[hcalc] hcalcInitBotao call failed', e); }
        } else {
            dbg('[hcalc] hcalcInitBotao not available to re-init button');
        }
    };
    // ==========================================
    function initializeBotao() {
        if (window.__hcalcBotaoInitialized) {
            dbg('initializeBotao ignorado: botão já inicializado.');
            return;
        }
        dbg('initializeBotao iniciado (FASE A - leve).');
        window.__hcalcBotaoInitialized = true;

        // CSS mínimo — apenas o botão (~200 bytes)
        if (!document.getElementById('hcalc-btn-style')) {
            const s = document.createElement('style');
            s.id = 'hcalc-btn-style';
            s.innerText = `
        #hcalc-floating-wrap {
            position: fixed; bottom: 20px; right: 20px; z-index: 99999;
            display: flex; flex-direction: column; gap: 6px; align-items: stretch;
        }
        #btn-abrir-homologacao {
            background: #00509e; color: white; border: none; border-radius: 6px;
            padding: 10px 18px; font-size: 13px; font-weight: bold; cursor: pointer;
            box-shadow: 0 3px 5px rgba(0,0,0,0.3); width: 100%;
        }
        #btn-abrir-homologacao:hover { background: #003d7a; }`;
            document.head.appendChild(s);
        }

        // Injeta container + botão + input file (sem overlay)
        document.body.insertAdjacentHTML(
            'beforeend',
            `
            <div id="hcalc-floating-wrap">
                <button id="btn-abrir-homologacao" type="button">
                    \uD83D\uDCC4 Carregar Planilha
                </button>
                <div id="hcalc-uid-row" style="display:flex;gap:4px;margin-top:6px;">
                    <input id="input-planilha-uid" type="text" placeholder="UID da planilha"
                        style="flex:1;font-size:11px;padding:4px 6px;border:1px solid #ccc;border-radius:4px;min-width:0;"
                        title="Cole aqui o idUnicoDocumento da planilha (documentoId da URL)">
                    <button id="btn-planilha-uid" type="button"
                        style="font-size:11px;padding:4px 8px;border:none;border-radius:4px;background:#374151;color:#fff;cursor:pointer;white-space:nowrap;">
                        API &#x21D2;
                    </button>
                </div>
            </div>
            <input
                id="input-planilha-pdf"
                type="file"
                accept="application/pdf"
                style="display:none"
            />
            `
        );

        const btn = document.getElementById('btn-abrir-homologacao');

        if (overlayDraftApi) {
            const restored = overlayDraftApi.restoreStateOnly(warn);
            let rawDraft = (typeof overlayDraftApi.loadRaw === 'function') ? overlayDraftApi.loadRaw(warn) : null;
            dbg('overlayDraft restoreStateOnly ->', restored, 'planilhaCarregada=', window.hcalcState && window.hcalcState.planilhaCarregada, 'rawDraft=', !!rawDraft);
            // fallback: verificar apenas o rascunho do processo atual (isolamento por processo)
            if (!rawDraft) {
                try {
                    const match = window.location.pathname.match(/processo\/([^/]+)/i);
                    const processoId = match ? match[1] : null;
                    if (processoId) {
                        const key = `hcalc-overlay-draft:${processoId}`;
                        try {
                            const val = JSON.parse(localStorage.getItem(key));
                            if (val && val.state) {
                                rawDraft = val;
                                dbg('[hcalc] fallback: found rawDraft for current process key=', key);
                            }
                        } catch (e) { /* ignore parse errors */ }
                    }
                } catch (e) { dbg('[hcalc] fallback localStorage search failed', e); }
            }
            dbg('overlayDraft after fallback rawDraft=', !!rawDraft);

            // Se o restore direto indicou planilha carregada, ajusta para restaurar com destaque
            if (restored && window.hcalcState && window.hcalcState.planilhaCarregada) {
                btn.textContent = '🔁 Restaurar dados anteriores — planilha já lida';
                btn.title = 'Restaurar dados anteriores extraídos da última planilha (já carregada)';
                btn.style.background = '#f59e0b';
                btn.style.color = '#000';
            }

            // Função utilitária para criar/remover botão de limpar rascunho do processo atual
            function ensureClearDraftButton(shouldShow, planilhaCarregadaFlag) {
                let limpar = document.getElementById('btn-limpar-rascunho');
                if (shouldShow) {
                    if (!limpar) {
                        limpar = document.createElement('button');
                        limpar.id = 'btn-limpar-rascunho';
                        limpar.type = 'button';
                        limpar.textContent = '🧹 Limpar dados';
                        limpar.style.background = '#ef4444';
                        limpar.style.color = '#fff';
                        limpar.style.border = 'none';
                        // reduzir largura horizontal do botão vermelho: menos padding e não esticar
                        limpar.style.padding = '6px 8px';
                        limpar.style.alignSelf = 'flex-end';
                        limpar.style.borderRadius = '6px';
                        limpar.style.cursor = 'pointer';
                        limpar.style.fontSize = '12px';
                        limpar.style.fontWeight = 'bold';
                        limpar.style.boxShadow = '0 3px 5px rgba(0,0,0,0.3)';
                        document.getElementById('hcalc-floating-wrap').appendChild(limpar);

                        limpar.addEventListener('click', (e) => {
                            e.preventDefault();
                            if (confirm('Tem certeza que deseja limpar todos os dados salvos deste processo?')) {
                                try {
                                    // Prefer clearRaw on the module or the global helper that always exists
                                    if (overlayDraftApi && typeof overlayDraftApi.clearRaw === 'function') {
                                        overlayDraftApi.clearRaw();
                                    } else if (typeof window.hcalcClearOverlayDraft === 'function') {
                                        window.hcalcClearOverlayDraft();
                                    }
                                } catch (err) { console.warn('[hcalc] falha ao limpar rascunho', err); }
                                try { if (window.hcalcState && typeof window.hcalcState.resetPrep === 'function') window.hcalcState.resetPrep(); } catch (err) { console.warn('[hcalc] resetPrep falhou', err); }

                                // Recarregar a página para garantir a limpeza completa da memória e interface
                                window.location.reload();
                            }
                        });
                    }
                    // atualizar texto do botão principal se planilha carregada
                    if (planilhaCarregadaFlag) {
                        btn.textContent = '🔁 Restaurar dados anteriores — planilha já lida';
                        btn.title = 'Restaurar dados anteriores extraídos da última planilha (já carregada)';
                        btn.style.background = '#f59e0b';
                        btn.style.color = '#000';
                    } else {
                        btn.title = 'Rascunho encontrado (sem planilha carregada)';
                    }
                } else {
                    if (limpar) {
                        try { limpar.remove(); } catch (e) { /* ignore */ }
                    }
                    // reset title if needed
                    btn.title = btn.title && btn.title.indexOf('Rascunho') === 0 ? '' : btn.title;
                }
            }

            // Se houver rascunho salvo (mesmo que restoreStateOnly=false), exibe botão de limpar/recuperar
            if (rawDraft && rawDraft.state) {
                ensureClearDraftButton(true, !!rawDraft.state.planilhaCarregada);
            }

            // Escuta eventos de alteração de rascunho (salvar/limpar) para atualizar botão dinamicamente
            window.addEventListener('hcalc:draft:changed', (ev) => {
                try {
                    const match = window.location.pathname.match(/processo\/([^/]+)/i);
                    const processoId = match ? match[1] : null;
                    if (!processoId) return;
                    const key = `hcalc-overlay-draft:${processoId}`;
                    if (ev.detail && ev.detail.key === key) {
                        if (ev.detail.action === 'save') {
                            // show button
                            const raw = overlayDraftApi.loadRaw && overlayDraftApi.loadRaw(warn);
                            ensureClearDraftButton(!!raw && !!raw.state, raw && raw.state && !!raw.state.planilhaCarregada);
                        } else if (ev.detail.action === 'clear') {
                            // hide button
                            ensureClearDraftButton(false);
                        }
                    }
                } catch (e) { dbg('[hcalc] draft change handler failed', e); }
            });

            // Extra fallback: checar diretamente localStorage para o rascunho do processo atual
            try {
                const m = window.location.pathname.match(/processo\/([^/]+)/i);
                const pid = m ? m[1] : null;
                if (pid) {
                    const directKey = `hcalc-overlay-draft:${pid}`;
                    const rawStr = localStorage.getItem(directKey);
                    if (rawStr) {
                        try {
                            const parsed = JSON.parse(rawStr);
                            ensureClearDraftButton(!!parsed && !!parsed.state, parsed && parsed.state && !!parsed.state.planilhaCarregada);
                            dbg('[hcalc] direct localStorage fallback enabled clear button for key=', directKey);
                        } catch (e) { dbg('[hcalc] direct localStorage parse failed', e); }
                    }
                }
            } catch (e) { dbg('[hcalc] direct localStorage fallback error', e); }
        }

        // Handler do botão API ⇒ (registrado aqui para funcionar sem abrir o overlay)
        // uid = idUnicoDocumento (7-char hex). Resolve para id numérico via
        // GET /documentos?idUnicoDocumento={uid} (retorna documento único com campo "id").
        async function carregarPlanilhaPorUidBotao(uid) {
            uid = (uid || '').trim();
            if (!uid) throw new Error('UID vazio');
            const m = location.pathname.match(/\/processo\/(\d+)/);
            if (!m) throw new Error('ID do processo não encontrado na URL');
            const idProcesso = m[1];
            const getCookie = (name) => {
                const c = document.cookie.split(';').map(s => s.trim())
                    .find(s => s.toLowerCase().startsWith(name.toLowerCase() + '='));
                return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
            };
            const xsrf = getCookie('XSRF-TOKEN');
            const baseHeaders = { 'Accept': 'application/json', 'X-Grau-Instancia': '1' };
            if (xsrf) baseHeaders['X-XSRF-TOKEN'] = xsrf;

            // 1. Resolver idUnicoDocumento → id numérico
            const docUrl = `${location.origin}/pje-comum-api/api/processos/id/${idProcesso}/documentos?` +
                new URLSearchParams({ idUnicoDocumento: uid });
            const docResp = await fetch(docUrl, { method: 'GET', credentials: 'include', headers: baseHeaders });
            if (!docResp.ok) throw new Error(`HTTP ${docResp.status} ao resolver uid=${uid}`);
            const docData = await docResp.json();
            // resposta pode ser array ou objeto único
            const docItem = Array.isArray(docData) ? docData[0] : docData;
            const idDoc = docItem && docItem.id;
            if (!idDoc) throw new Error(`idUnicoDocumento "${uid}" não encontrado`);

            // 2. Buscar conteúdo pelo id numérico
            const pdfHeaders = { 'Accept': '*/*', 'X-Grau-Instancia': '1' };
            if (xsrf) pdfHeaders['X-XSRF-TOKEN'] = xsrf;
            const url = `${location.origin}/pje-comum-api/api/processos/id/${idProcesso}/documentos/id/${idDoc}/conteudo`;
            const resp = await fetch(url, { method: 'GET', credentials: 'include', headers: pdfHeaders });
            if (!resp.ok) throw new Error(`HTTP ${resp.status} ao buscar conteúdo (idDoc=${idDoc})`);
            const buffer = await resp.arrayBuffer();
            if (!buffer || buffer.byteLength < 100) throw new Error('Resposta vazia para idDoc=' + idDoc);
            const loaded = await window.carregarPDFJSSeNecessario();
            if (!loaded) throw new Error('PDF.js não disponível');
            const fakeFile = new File([buffer], `Documento_${uid}.pdf`, { type: 'application/pdf' });
            return window.processarPlanilhaPDF(fakeFile);
        }
        const btnUidEarly = document.getElementById('btn-planilha-uid');
        const inputUidEarly = document.getElementById('input-planilha-uid');
        if (btnUidEarly && inputUidEarly) {
            btnUidEarly.addEventListener('click', async () => {
                const uid = inputUidEarly.value.trim();
                if (!uid) { alert('Informe o UID da planilha.'); return; }
                const btnMain = document.getElementById('btn-abrir-homologacao');
                btnUidEarly.disabled = true;
                btnUidEarly.textContent = '⏳';
                if (btnMain) { btnMain.textContent = '⏳ Buscando...'; btnMain.disabled = true; }
                try {
                    const dados = await carregarPlanilhaPorUidBotao(uid);
                    if (!dados || !dados.sucesso) throw new Error(dados && dados.erro ? dados.erro : 'Falha na extração');
                    window.hcalcState.planilhaExtracaoData = dados;
                    window.hcalcState.planilhaCarregada = true;
                    if (window.hcalcAtualizarResumoPlanilha) window.hcalcAtualizarResumoPlanilha(dados);
                    if (window.hcalcAtualizarDropdownsPlanilhas) window.hcalcAtualizarDropdownsPlanilhas();
                    if (btnMain) { btnMain.textContent = '✓ Dados Extraídos (API)'; btnMain.style.background = '#10b981'; btnMain.disabled = false; }
                    btnUidEarly.textContent = '✓';
                    inputUidEarly.value = '';
                    setTimeout(() => {
                        if (btnMain) { btnMain.textContent = 'Gerar Homologação'; btnMain.style.background = '#00509e'; }
                        btnUidEarly.textContent = 'API ⇒';
                        btnUidEarly.disabled = false;
                    }, 2000);
                } catch (e) {
                    console.error('[HCalc] carregarPlanilhaPorUid falhou:', e.message);
                    alert('Erro ao carregar via API: ' + e.message);
                    btnUidEarly.textContent = 'API ⇒';
                    btnUidEarly.disabled = false;
                    if (btnMain) { btnMain.textContent = '📄 Carregar Planilha'; btnMain.disabled = false; }
                }
            });
        }

        // Handler do botão — inicializa overlay lazy na primeira vez
        btn.onclick = async () => {
            if (!window.__hcalcOverlayInitialized) {
                dbg('Primeiro clique: carregando overlay completo (lazy init)...');
                initializeOverlay();
                // initializeOverlay substitui btn.onclick com o handler completo
            }

            // FASE 1: ainda não há planilha carregada
            if (!window.hcalcState.planilhaCarregada) {
                dbg('FASE 1: abrindo file picker.');
                document.getElementById('input-planilha-pdf').click();
                return;
            }

            // FASE 3: overlay já inicializado e planilha carregada
            btn.click();
        };
        dbg('Botão flutuante injetado (lazy init ativo).');
    }


    function initializeOverlay() {
        if (window.__hcalcOverlayInitialized) {
            dbg('initializeOverlay ignorado: overlay ja inicializado.');
            return;
        }
        dbg('initializeOverlay iniciado.');
        window.__hcalcOverlayInitialized = true;

        // ==========================================
        // 1. ESTILOS DO OVERLAY E BOTÃO (v1.9 - UI Compacta)
        // ==========================================
        const styles = `
        #homologacao-overlay {
            display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: transparent; z-index: 100000; justify-content: flex-end; align-items: flex-start;
            font-family: Arial, sans-serif; pointer-events: none;
        }

        #homologacao-modal {
            background: #fff; width: 630px; max-width: 630px; height: 100vh; max-height: 100vh; overflow-y: auto;
            border-radius: 0; box-shadow: -4px 0 20px rgba(0,0,0,0.25); padding: 10px; margin: 0;
            display: flex; flex-direction: column; gap: 5px; color: #333; pointer-events: all;
        }

        .modal-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 6px; margin-bottom: 3px; }
        .modal-header h2 { margin: 0; color: #00509e; font-size: 15px; }
        .btn-close { background: #cc0000; color: white; border: none; padding: 3px 10px; cursor: pointer; border-radius: 3px; font-weight: bold; font-size: 11px; }

        fieldset { border: 1px solid #ddd; border-radius: 4px; padding: 6px; margin-bottom: 4px; background: #fff; }
        legend { background: #00509e; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; font-weight: bold; }

        .row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; align-items: center; }
        .col { display: flex; flex-direction: column; flex: 1; min-width: 140px; }

        label { font-size: 11px; font-weight: bold; margin-bottom: 3px; color: #555; }
        input[type="text"], input[type="date"] { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 13px; }
        textarea { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 12px; resize: vertical; font-family: Arial, sans-serif; }
        select { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 13px; }

        .hidden { display: none !important; }
        /* Destaque para o campo atual da coleta */
        .highlight { border: 2px solid #ff9800 !important; background: #fffde7 !important; box-shadow: 0 0 6px rgba(255,152,0,0.4); }

        /* Badges para partes detectadas (v1.9) */
        .partes-badges { display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0; }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            white-space: nowrap;
        }
        .badge-blue { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
        .badge-gray { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }
        .badge-green { background: #d1fae5; color: #047857; border: 1px solid #a7f3d0; }

        .btn-action { background: #28a745; color: white; border: none; padding: 8px 12px; border-radius: 3px; cursor: pointer; font-weight: bold; font-size: 13px; }
        .btn-action:hover { background: #218838; }
        .btn-gravar { background: #00509e; width: 100%; padding: 12px; font-size: 16px; margin-top: 10px; }

        /* Compactar espaçamento interno para caber na tela */
        #homologacao-modal fieldset { padding: 8px 10px; margin-bottom: 6px; }
        #homologacao-modal .row { margin-bottom: 6px; gap: 8px; }
        #homologacao-modal input[type=text],
        #homologacao-modal input[type=date],
        #homologacao-modal select,
        #homologacao-modal textarea { padding: 5px 7px; font-size: 12px; }
        #homologacao-modal label { font-size: 11px; margin-bottom: 2px; }
        #homologacao-modal legend { font-size: 12px; padding: 3px 8px; }
        #homologacao-modal .btn-gravar { padding: 10px; font-size: 15px; margin-top: 10px; }

        /* Estilos do Card de Resumo da Planilha (FASE 1) */
        #resumo-extracao-card {
            width: 260px;
            background: #f8f9fa;
            border: 2px solid #10b981;
            border-radius: 8px;
            padding: 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            pointer-events: all;
            align-self: flex-start;
            margin-right: 8px;
            overflow: hidden;
            flex-shrink: 0;
        }
        #resumo-extracao-card h4 {
            margin: 0;
            padding: 12px 14px;
            border-bottom: 1px solid #10b981;
            cursor: pointer;
            user-select: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
            color: #fff;
            background: #10b981;
        }
        #resumo-extracao-card h4:hover { background: #059669; }
        #resumo-body {
            padding: 10px 12px;
            display: none;
        }
        #resumo-conteudo { display: flex; flex-direction: column; gap: 6px; }
        .resumo-item {
            padding: 4px 6px;
            background: white;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
            font-size: 12px;
        }
        .resumo-item strong { color: #ea580c; }
        #btn-reload-planilha {
            margin-top: 8px;
            width: 100%;
            padding: 6px 10px;
            font-size: 11px;
            border-radius: 4px;
            border: 1px solid #f97316;
            background: #fff;
            color: #f97316;
            cursor: pointer;
        }
        #btn-reload-planilha:hover { background: #fff7ed; }
        #btn-force-clear-overlay {
            width: 100%;
            padding: 8px 10px;
            font-size: 12px;
            border-radius: 4px;
            border: none;
            background: #ef4444;
            color: #fff;
            cursor: pointer;
        }
        #btn-force-clear-overlay:hover { background: #dc2626; }
        #btn-reload-planilha:hover { background: #10b981; color: white; }

        /* Recursos com anexos — integrado de rec.js v1.0 */
        .rec-recurso-card {
            padding: 8px 10px; margin-bottom: 6px;
            border: 1px solid #e5e7eb; border-radius: 5px;
            background: white; cursor: pointer; transition: all 0.2s;
        }
        .rec-recurso-card:hover { background: #f0f9ff; border-color: #3b82f6; }
        .rec-tipo-badge {
            display: inline-block; padding: 1px 7px; border-radius: 3px;
            font-size: 10px; font-weight: 700; color: white;
            background: #3b82f6; margin-right: 6px;
        }
        .rec-anexos-lista { margin-top: 6px; padding-top: 5px; border-top: 1px solid #e5e7eb; display: none; }
        .rec-recurso-card.expandido .rec-anexos-lista { display: block; }
        .rec-anexo-item {
            display: flex; align-items: center; gap: 6px;
            padding: 3px 4px; border-radius: 3px; cursor: pointer;
            font-size: 11px; transition: background 0.15s;
        }
        .rec-anexo-item:hover { background: #f3f4f6; }
        .rec-anexo-badge {
            padding: 1px 5px; border-radius: 2px;
            font-size: 10px; font-weight: 600; color: white; white-space: nowrap;
        }
        .rec-anexo-id {
            font-size: 10px; background: #f3f4f6;
            padding: 1px 4px; border-radius: 2px;
            font-family: monospace; color: #374151; user-select: all;
        }
        .rec-seta-toggle { font-size: 10px; color: #9ca3af; margin-left: auto; }
    `;
        if (!document.getElementById('hcalc-overlay-style')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'hcalc-overlay-style';
            styleSheet.innerText = styles;
            document.head.appendChild(styleSheet);
        }

        // ==========================================
        // 2. HTML DO OVERLAY (ESTRUTURA)
        // ==========================================
        const htmlModal = `
    <div id="homologacao-overlay">
        <!-- Card de Resumo da Planilha Extraída (à esquerda) -->
        <div id="resumo-extracao-card" style="display:none">
            <h4 id="resumo-toggle">
                <span>📋 Planilha Carregada</span>
                <span id="resumo-seta">▶</span>
            </h4>
            <div id="resumo-body">
                <div id="resumo-conteudo"></div>
                <button id="btn-reload-planilha" type="button">🔄 Recarregar PDF</button>
            </div>
        </div>
       
        <div id="homologacao-modal">
            <div class="modal-header">
                <h2>Assistente de Homologação</h2>
                <div>
                    <button class="btn-close" id="btn-fechar">X Fechar</button>
                </div>
            </div>



            <!-- SEÇÃO 1 e 2: BASE E PARTE -->
            <fieldset>
                <legend>Cálculo Base e Autoria</legend>
                <div class="row">
                    <div class="col">
                        <label>Origem do Cálculo</label>
                        <select id="calc-origem">
                            <option value="pjecalc" selected>PJeCalc</option>
                            <option value="outros">Outros</option>
                        </select>
                    </div>
                    <div class="col" id="col-pjc">
                        <label><input type="checkbox" id="calc-pjc" checked> Acompanha arquivo .PJC?</label>
                    </div>
                    <div class="col">
                        <label>Autor do Cálculo</label>
                        <select id="calc-autor">
                            <option value="autor" selected>Reclamante (Autor)</option>
                            <option value="reclamada">Reclamada</option>
                            <option value="perito">Perito</option>
                        </select>
                    </div>
                    <div class="col hidden" id="col-esclarecimentos">
                        <label><input type="checkbox" id="calc-esclarecimentos" checked> Esclarecimentos do Perito?</label>
                        <input type="text" id="calc-peca-perito" placeholder="Id da Peça">
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 3: ATUALIZAÇÃO -->
            <fieldset>
                <legend>Atualização</legend>
                <div class="row">
                    <div class="col">
                        <label>Índice de Atualização</label>
                        <select id="calc-indice">
                            <option value="adc58" selected>SELIC / IPCA-E (ADC 58)</option>
                            <option value="tr">TR / IPCA-E (Casos Antigos)</option>
                        </select>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 5: DADOS COPIADOS DA PLANILHA (ÚNICO FIELDSET) -->
            <fieldset>
                <legend>Dados Copiados da Planilha</legend>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">1) Identificação, Datas, Principal e FGTS</label>
                    <div class="row">
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Id da Planilha</label>
                            <input type="text" id="val-id" class="coleta-input" placeholder="Id #XXXX">
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Data da Atualização</label>
                            <input type="text" id="val-data" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col" style="flex: 1;">
                            <label>Crédito Principal (ou Total)</label>
                            <input type="text" id="val-credito" class="coleta-input" placeholder="R$ Crédito Principal">
                        </div>
                    </div>
                    <div class="row row-fgts-block" style="align-items: flex-start; margin-top: 6px;">
                        <div class="col" style="flex: 0 0 140px;">
                            <label style="font-size: 11px; font-weight: bold; margin-bottom: 3px; color: #555; display: block;">FGTS</label>
                            <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px; height: 28px;">
                                <input type="checkbox" id="calc-fgts" checked> Apurado separado?
                            </label>
                            <div id="row-fgts-valor" style="margin-top: 6px;">
                                <label style="font-size: 11px; font-weight: bold; margin-bottom: 3px; color: #555; display: block;">Valor FGTS Separado</label>
                                <input type="text" id="val-fgts" class="coleta-input" placeholder="R$ FGTS" style="width: 140px; box-sizing: border-box;">
                            </div>
                        </div>
                        <div class="col" id="fgts-opcoes" style="flex: 1; padding-top: 17px;">
                            <div style="display: flex; align-items: center; gap: 15px; height: 28px; flex-wrap: wrap;">
                                <div id="fgts-radios" style="display: flex; align-items: center; gap: 8px;">
                                    <label style="font-size: 11px; font-weight: bold; margin: 0; color: #555;">Situação:</label>
                                    <label style="display: flex; align-items: center; gap: 4px; margin: 0; font-size: 12px;"><input type="radio" name="fgts-tipo" value="devido" checked> Devido</label>
                                </div>
                                <div style="width: 1px; height: 16px; background: #ccc;"></div>
                                <label style="display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px;">
                                    <input type="checkbox" id="calc-fgts-alvara"> Dispensa imotivada? (Alvará)
                                </label>
                            </div>
                        </div>
                    </div>
                    <div class="row hidden" id="col-juros-val">
                        <div class="col">
                            <label>Juros</label>
                            <input type="text" id="val-juros" placeholder="R$ Juros">
                        </div>
                        <div class="col">
                            <label>Data de Ingresso</label>
                            <input type="date" id="data-ingresso">
                        </div>
                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">2) INSS (Autor e Reclamada) e IR</label>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col">
                            <label>INSS - Desconto (Reclamante)</label>
                            <input type="text" id="val-inss-rec" class="coleta-input" placeholder="R$ INSS Reclamante (Desconto)">
                        </div>
                        <div class="col">
                            <label>INSS - Total da Empresa (Reclamada)</label>
                            <input type="text" id="val-inss-total" class="coleta-input" placeholder="R$ INSS Total / Reclamada">
                        </div>
                    </div>
                    <div class="row" style="margin-top: 5px;">
                        <div class="col">
                            <label><input type="checkbox" id="ignorar-inss"> Não há INSS</label>
                            <small style="color: #666; display: block;">*INSS Reclamada = Subtração automática se PJeCalc marcado.</small>
                        </div>
                        <div class="col">
                            <label>Imposto de Renda</label>
                            <select id="irpf-tipo" style="margin-bottom: 5px; width: 100%;">
                                <option value="isento" selected>Não há</option>
                                <option value="informar">Informar Valores</option>
                            </select>
                            <div id="irpf-campos" class="hidden" style="display:flex; gap: 5px;">
                                <input type="text" id="val-irpf-base" placeholder="Base (R$)" style="flex:1;">
                                <input type="text" id="val-irpf-meses" placeholder="Meses" style="flex:1;">
                            </div>
                        </div>
                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">3) Honorários Advocatícios</label>
                    <div class="row" style="margin-bottom: 0; align-items: flex-start;">

                        <!-- Coluna AUTOR -->
                        <div class="col" style="flex: 1; min-width: 160px;">
                            <label>Honorários Adv Autor</label>
                            <input type="text" id="val-hon-autor" class="coleta-input highlight" placeholder="R$ Honorários Autor">
                            <label style="font-size: 11px; margin-top: 4px; display: block;">
                                <input type="checkbox" id="ignorar-hon-autor"> Não há honorários autor
                            </label>
                        </div>

                        <!-- Coluna RÉU -->
                        <div class="col" style="flex: 1; min-width: 160px;">
                            <label>
                                <input type="checkbox" id="chk-hon-reu" style="margin-right: 5px;">Não há Honorários Adv Réu
                            </label>
                            <div id="hon-reu-campos" class="hidden" style="margin-top: 6px;">
                                <label style="font-size: 11px; display: block; margin-bottom: 6px;">
                                    <input type="checkbox" id="chk-hon-reu-suspensiva" checked> Condição Suspensiva
                                </label>
                                <div style="display: flex; gap: 8px; flex-direction: column; margin-bottom: 6px;">
                                    <label style="font-size: 11px;">
                                        <input type="radio" name="rad-hon-reu-tipo" value="percentual" checked> Percentual
                                    </label>
                                    <label style="font-size: 11px;">
                                        <input type="radio" name="rad-hon-reu-tipo" value="valor"> Valor Informado
                                    </label>
                                </div>
                                <div id="hon-reu-perc-campo" style="margin-bottom: 4px;">
                                    <input type="text" id="val-hon-reu-perc" class="coleta-input" value="5%" placeholder="%" style="width: 80px;">
                                </div>
                                <div id="hon-reu-valor-campo" class="hidden" style="margin-bottom: 4px;">
                                    <input type="text" id="val-hon-reu" class="coleta-input" placeholder="R$ Honorários Réu" style="width: 140px;">
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">4) Custas</label>
                    <div class="row" style="margin-bottom: 5px;">
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Valor</label>
                            <input type="text" id="val-custas" class="coleta-input" placeholder="R$ Custas">
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Status</label>
                            <select id="custas-status">
                                <option value="devidas" selected>Devidas</option>
                                <option value="pagas">Já Pagas</option>
                            </select>
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Origem</label>
                            <select id="custas-origem">
                                <option value="sentenca" selected>Sentença</option>
                                <option value="planilha">Planilha</option>
                                <option value="acordao">Acórdão</option>
                            </select>
                        </div>
                    </div>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col" id="custas-data-col" style="flex: 1;">
                            <label>Data Custas <small style="color: #666;">(vazio = mesma planilha)</small></label>
                            <input type="text" id="custas-data-origem" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col hidden" id="custas-acordao-col" style="flex: 1;">
                            <label>Acórdão</label>
                            <select id="custas-acordao-select">
                                <option value="">Selecione o acórdão</option>
                            </select>
                        </div>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 6: DECISÕES E HONORÁRIOS PERICIAIS -->
            <fieldset style="border:none; padding:0; margin: 15px 0 5px 0;">
                <legend>Decisões</legend>
            </fieldset>
            <fieldset style="border: none; padding: 0 0 8px 0; margin: 0 0 8px 0;">
                <div id="link-sentenca-acordao-container"></div>
            </fieldset>

            <!-- SEÇÃO 7B: HONORÁRIOS PERICIAIS (auto-esconde se não detectar perito) -->
            <fieldset id="fieldset-pericia-conh" class="hidden">
                <legend>Honorários Periciais <span id="link-sentenca-container"></span></legend>
                <div class="row">
                    <div class="col">
                        <label><input type="checkbox" id="chk-perito-conh"> Honorários Periciais (Conhecimento)</label>
                        <div id="perito-conh-campos" class="hidden" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-nome" placeholder="Nome do Perito">
                            <select id="perito-tipo-pag">
                                <option value="reclamada" selected>Pago pela Reclamada (Valor)</option>
                                <option value="trt">Pago pelo TRT (Autor Sucumbente)</option>
                            </select>
                            <input type="text" id="val-perito-valor" placeholder="R$ Valor ou ID TRT">
                            <input type="text" id="val-perito-data" placeholder="Data da Sentença">
                        </div>
                    </div>
                </div>
                <div class="row hidden" id="row-perito-contabil">
                    <div class="col">
                        <label>Honorários Periciais (Contábil - Rogério)</label>
                        <div id="perito-contabil-campos" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-contabil-valor" placeholder="Valor dos honorários contábeis">
                        </div>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 7: RESPONSABILIDADE -->
            <fieldset style="border:none; padding:0; margin: 15px 0 5px 0;">
                <legend>Responsabilidade</legend>
            </fieldset>

            <!-- CONFERÊNCIA DE ACÓRDÃO (novo card) -->
            <fieldset style="border:none; padding: 0 0 8px 0; margin: 0 0 8px 0;">
                <div id="conferencia-acordao-container" class="hidden">
                    <label style="font-weight:bold; color:#5b21b6;">Conferência Pós-Acórdão:</label>
                    <div id="conferencia-acordao-body" style="margin-top:6px; font-size:12px; color:#374151"></div>
                </div>
            </fieldset>
            <fieldset id="resp-principais-fieldset" style="border: 1px solid #cbd5e1; border-radius: 4px; padding: 8px; margin-bottom: 10px;">
                <div class="row" style="margin-bottom: 0;">
                    <div class="col">
                        <label style="font-weight: bold; color: #00509e; font-size: 13px;">A) Devedora Principal</label>
                        <small style="color:#666; display:block; margin-bottom:6px;">A primeira da lista é a Devedora Principal (automática).</small>
                        <div id="resp-principais-dinamico-container" style="margin-top:6px; padding:0; display:flex; flex-direction:column; gap:6px;"></div>
                        <div style="margin-top: 8px; display: flex; align-items: center; gap: 6px;">
                            <button type="button" class="btn-action" id="btn-add-principal" style="padding: 4px 12px; font-size: 11px;">+ Adicionar principal</button>
                        </div>
                        <small id="resp-principais-note" style="color:#666; display:block; margin-top:6px;">Marque Rec. Judicial/Falência por empresa na lista acima.</small>
                    </div>
                </div>
            </fieldset>

            <div id="resp-extras-header-container" class="hidden" style="margin-top: 15px; margin-bottom: 5px;">
                <label style="font-weight: bold; color: #00509e; font-size: 13px;">B) Demais Reclamadas</label>
            </div>
            <div id="resp-extras-reclamadas-container"></div>

            <!-- Custas já foram movidas para o card 4 acima -->

            <!-- SEÇÃO 8: DEPÓSITOS -->
            <fieldset id="fieldset-deposito">
                <legend>Depósitos</legend>
                <div class="row">
                    <label id="label-chk-deposito"><input type="checkbox" id="chk-deposito"> Há Depósito Recursal?</label>
                    <label style="margin-left: 20px;"><input type="checkbox" id="chk-pag-antecipado"> Pagamento Antecipado</label>
                </div>

                <!-- CONTAINER DE DEPÓSITOS RECURSAIS (dinâmico) -->
                <div id="deposito-campos" class="hidden">
                    <div id="depositos-container"></div>
                    <button type="button" id="btn-add-deposito" class="btn-action" style="margin-top: 8px; padding: 4px 12px; font-size: 11px;">+ Adicionar Depósito Recursal</button>
                </div>

                <!-- CONTAINER DE PAGAMENTOS ANTECIPADOS (dinâmico) -->
                <div id="pag-antecipado-campos" class="hidden">
                    <div id="pagamentos-container"></div>
                    <button type="button" id="btn-add-pagamento" class="btn-action" style="margin-top: 8px; padding: 4px 12px; font-size: 11px;">+ Adicionar Pagamento</button>
                </div>
            </fieldset>

            <!-- SEÇÃO 9: INTIMAÇÕES -->
            <fieldset id="fieldset-intimacoes">
                <legend>Intimações</legend>
                <div id="lista-intimacoes-container">
                    <small style="color:#666; font-style:italic;">Aguardando leitura das partes...</small>
                </div>
                <div id="links-editais-container" class="hidden" style="margin-top: 10px; border-top: 1px dashed #ccc; padding-top: 10px;">
                    <label style="font-weight:bold; font-size:12px; color:#5b21b6;">Editais Detectados na Timeline:</label>
                    <div id="links-editais-lista"></div>
                </div>
            </fieldset>

            <button class="btn-action btn-gravar" id="btn-gravar">GRAVAR DECISÃO (Copiar p/ PJe)</button>
        </div>
    </div>
    `;
        // Check robusto: Remover overlay antigo se existir (previne duplicação)
        const existingOverlay = document.getElementById('homologacao-overlay');
        if (existingOverlay) {
            dbg('Overlay já existe, removendo versão antiga antes de recriar');
            existingOverlay.remove();
        }

        // Inserir HTML limpo
        document.body.insertAdjacentHTML('beforeend', htmlModal);
        dbg('Overlay HTML inserido no DOM.');

        // Heurística leve: tentar detectar Id de planilha em anchors/codes visíveis
        try {
            if (!window.hcalcState) window.hcalcState = {};
            if (!window.hcalcState.planilhaExtracaoData) {
                const rx = /Documento_([A-Za-z0-9]+)\.pdf/i;
                const candidates = Array.from(document.querySelectorAll('a, code, span'));
                for (const el of candidates) {
                    try {
                        const txt = (el.textContent || el.innerText || '') + ' ' + (el.getAttribute && el.getAttribute('title') || '');
                        const m = txt.match(rx);
                        if (m) {
                            window.hcalcState.planilhaExtracaoData = { idPlanilha: m[1], sucesso: true };
                            window.hcalcState.planilhaCarregada = true;
                            dbg('[hcalc] detectIdFromPage -> found planilha id=', m[1]);
                            // Atualizar resumo visual se API disponível
                            if (typeof window.hcalcAtualizarResumoPlanilha === 'function') {
                                window.hcalcAtualizarResumoPlanilha(window.hcalcState.planilhaExtracaoData);
                            }
                            // Atualizar botão visual se presente
                            const b = document.getElementById('btn-abrir-homologacao');
                            if (b) { b.textContent = '✓ Dados Extraídos'; b.style.background = '#10b981'; }
                            break;
                        }
                    } catch (e) { /* ignore per-item */ }
                }
            }
        } catch (e) { dbg('[hcalc] detectIdFromPage failed', e); }

        // Registrar listener do botão de limpeza forçada
        try {
            const btnForce = document.getElementById('btn-force-clear-overlay');
            if (btnForce) {
                btnForce.addEventListener('click', (ev) => {
                    ev.preventDefault();
                    if (confirm('Limpar rascunho e carregar nova planilha? Esta ação removerá o rascunho salvo para este processo.')) {
                        try {
                            if (typeof window.hcalcForceClearAndLoadNew === 'function') {
                                window.hcalcForceClearAndLoadNew();
                            } else {
                                dbg('[hcalc] hcalcForceClearAndLoadNew não disponível');
                            }
                        } catch (e) { dbg('[hcalc] erro ao executar forceClear', e); }
                    }
                });
                dbg('[hcalc] btn-force-clear-overlay listener registrado');
            }
        } catch (e) { dbg('[hcalc] falha ao registrar listener btn-force-clear-overlay', e); }

        // Toggle colapso/expansão do card de resumo
        const resumoToggle = document.getElementById('resumo-toggle');
        const resumoBody = document.getElementById('resumo-body');
        const resumoSeta = document.getElementById('resumo-seta');
        if (resumoToggle && resumoBody) {
            resumoToggle.addEventListener('click', () => {
                const aberto = resumoBody.style.display !== 'none';
                resumoBody.style.display = aberto ? 'none' : 'block';
                if (resumoSeta) resumoSeta.textContent = aberto ? '▶' : '▼';
            });
        }

        if (!document.getElementById('homologacao-overlay')) {
            err('Falha apos insercao: homologacao-overlay nao encontrado.');
            return;
        }

        // ==========================================
        // Bind no input file (FASE 4 do MD) - será definido abaixo após declaração de funções
        // ==========================================

        // ==========================================
        // 3. LÓGICA DE INTERFACE E EVENTOS (TOGGLES)
        // ==========================================
        const $ = (id) => document.getElementById(id);
        const modalEl = $('homologacao-modal');
        dbg('Binding de eventos iniciado.');

        // Dispatch seguro: tenta MouseEvent com opções, se falhar remove `view` ou cai para `el.click()`
        function safeDispatch(el, type, opts) {
            try { el.dispatchEvent(new MouseEvent(type, opts || {})); return true; }
            catch (e) {
                try { const safeOpts = Object.assign({}, opts || {}); if ('view' in safeOpts) delete safeOpts.view; el.dispatchEvent(new MouseEvent(type, safeOpts)); return true; }
                catch (e2) { try { el.click(); return true; } catch (e3) {} try { const ev = document.createEvent('MouseEvents'); ev.initMouseEvent(type, !!(opts && opts.bubbles), !!(opts && opts.cancelable), window, 0,0,0,0,0,false,false,false,false,0,null); el.dispatchEvent(ev); return true; } catch (e4) {} }
            }
            return false;
        }

        function atualizarResumoPlanilha(dados) {
            const resumoCard = $('resumo-extracao-card');
            const resumoConteudo = $('resumo-conteudo');
            if (!resumoCard || !resumoConteudo || !dados) return;

            resumoCard.style.display = 'block';
            resumoConteudo.innerHTML = `
                <div class="resumo-item"><strong>ID:</strong> ${dados.idPlanilha || 'N/A'}</div>
                <div class="resumo-item"><strong>Crédito:</strong> R$ ${dados.verbas || '0,00'}</div>
                ${dados.fgts ? `<div class="resumo-item"><strong>FGTS:</strong> R$ ${dados.fgts}</div>` : ''}
                <div class="resumo-item"><strong>INSS Total:</strong> R$ ${dados.inssTotal || '0,00'}</div>
                <div class="resumo-item"><strong>INSS Rec:</strong> R$ ${dados.inssAutor || '0,00'}</div>
                ${dados.custas ? `<div class="resumo-item"><strong>Custas:</strong> R$ ${dados.custas}</div>` : ''}
                <div class="resumo-item"><strong>Data:</strong> ${dados.dataAtualizacao || 'N/A'}</div>
                ${dados.periodoCalculo ? `<div class="resumo-item"><strong>Período:</strong> ${dados.periodoCalculo}</div>` : ''}
                ${dados.irpfIsento === false ? `<div class="resumo-item" style="color:#b45309"><strong>IRPF:</strong> Tributável</div>` : ''}
            `;
        }

        window.hcalcAtualizarResumoPlanilha = atualizarResumoPlanilha;
        window.hcalcAtualizarDropdownsPlanilhas = () => {
            if (responsabilidadesController && typeof responsabilidadesController.atualizarDropdownsPlanilhas === 'function') {
                responsabilidadesController.atualizarDropdownsPlanilhas();
            }
        };
        const draftController = overlayDraftApi.createController({
            $, modalEl, warn, atualizarResumoPlanilha, adicionarLinhaPeridoDiverso,
            adicionarDepositoRecursal, adicionarPagamentoAntecipado,
            aplicarEstiloRecuperacaoJudicial, atualizarDropdownsPlanilhas,
            updateHighlight
        });
        const queueOverlayDraftSave = draftController.queueSave;
        const restoreOverlayDraft = draftController.restore;
        const depositosController = window.hcalcOverlayDepositos.createController({
            $, queueOverlayDraftSave
        });
        const responsabilidadesController = window.hcalcOverlayResponsabilidades.createController({
            $,
            queueOverlayDraftSave,
            carregarPDFJSSeNecessario,
            processarPlanilhaPDF
        });
        
        draftController.setResponsabilidadesApi({
            addPrincipal: responsabilidadesController.addPrincipal,
            addSubsInt: responsabilidadesController.addSubsInt,
            addSolInt: responsabilidadesController.addSolInt,
            criarBoxReclamadaExtra: responsabilidadesController.criarBoxReclamadaExtra
        });

        const responsabilidadesTextoApi = window.hcalcOverlayResponsabilidades.createTextApi({
            $,
            bold
        });

        // Atualiza marcações quando a condição "Devedora Única" muda
        window.addEventListener('hcalc:devedora-unica-changed', (ev) => {
            try {
                const unica = ev && ev.detail && ev.detail.unica;
                const note = document.getElementById('resp-principais-note');
                if (note) {
                    note.textContent = unica ? 'Devedora Única detectada — opções subsidiárias/solidárias desabilitadas.' : 'Marque Rec. Judicial/Falência por empresa na lista acima.';
                }

                // Atualizar títulos de depósitos existentes e aplicar visibilidade/lock
                try {
                    const deps = window.hcalcState?.depositosRecursais || [];
                    deps.forEach(d => {
                        try {
                            const title = document.getElementById(`dep-title-${d.idx}`);
                            if (title) {
                                const reclamadasNow = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
                                title.textContent = `Depósito Recursal #${d.idx + 1}` + (reclamadasNow.length === 1 ? ' (Única)' : '');
                            }
                            if (typeof window.hcalcAtualizarVisibilidadeDepositoPrincipal === 'function') {
                                window.hcalcAtualizarVisibilidadeDepositoPrincipal(d.idx);
                            }
                        } catch (inner) { /* ignore per-dep */ }
                    });
                } catch (ex) { /* ignore */ }

                // Mostrar/ocultar resumo 'Devedora Única' e sincronizar checkbox Rec. Judicial
                try {
                    let respFieldset = null;
                    const candidate = document.getElementById('resp-subsidiarias') || document.getElementById('resp-solidarias') || document.getElementById('resp-principais-fieldset');
                    if (candidate) respFieldset = candidate.closest('fieldset');
                    if (!respFieldset) {
                        Array.from(document.querySelectorAll('fieldset')).forEach(f => {
                            const lg = f.querySelector('legend');
                            if (lg && /Responsabilidade/i.test(lg.textContent)) respFieldset = f;
                        });
                    }

                    const existingSummary = document.getElementById('resp-unica-summary');
                    if (unica) {
                        // criar/atualizar summary
                        const nome = window.hcalcPartesData?.passivo?.[0]?.nome || '(reclamada)';
                        if (!existingSummary) {
                            const s = document.createElement('div');
                            s.id = 'resp-unica-summary';
                            s.style.cssText = 'padding:8px;margin-bottom:8px;background:#f8fafc;border:1px solid #cbd5e1;border-radius:6px;';
                            const containerRef = document.getElementById('resp-principais-fieldset');
                            if (containerRef && containerRef.parentElement) containerRef.parentElement.insertBefore(s, containerRef);
                        }
                        const sum = document.getElementById('resp-unica-summary');
                        if (sum) {
                            const recChecked = document.getElementById('resp-rec-judicial-unica')?.checked ? 'checked' : '';
                            sum.innerHTML = `<strong style="color:#b45309;">Devedora Única:</strong> <span style="margin-left:8px;font-weight:600">${nome}</span> <label style="margin-left:12px;font-size:12px"><input type="checkbox" id="resp-unica-summary-rec" ${recChecked}> Rec. Judicial/Falência</label>`;
                            const chk = document.getElementById('resp-unica-summary-rec');
                            if (chk) {
                                chk.onchange = (e) => {
                                    const target = document.getElementById('resp-rec-judicial-unica');
                                    if (target) { target.checked = e.target.checked; target.dispatchEvent(new Event('change', { bubbles: true })); }
                                };
                            }
                        }
                        if (respFieldset) respFieldset.classList.add('hidden');

                        // Garantir selects de depósitos travados/selecionados
                        try {
                            const nome = window.hcalcPartesData?.passivo?.[0]?.nome;
                            if (nome) {
                                Array.from(document.querySelectorAll('[id^="dep-depositante-"]')).forEach(s => { try { s.value = nome; s.disabled = true; } catch(e){} });
                            }
                        } catch (e) { /* ignore */ }
                    } else {
                        if (existingSummary) existingSummary.remove();
                        if (respFieldset) respFieldset.classList.remove('hidden');
                        // reabilitar selects de depósitos
                        Array.from(document.querySelectorAll('[id^="dep-depositante-"]')).forEach(s => { try { s.disabled = false; } catch(e){} });
                    }
                } catch (e) { /* ignore */ }

            } catch (e) { /* ignore */ }
        });

        // ==========================================
        const partesController = window.hcalcOverlayPartes.createController({
            $,
            normalizarNomeParaComparacao,
            aplicarEstiloRecuperacaoJudicial
        });
        const isNomeRogerio = partesController.isNomeRogerio;
        partesController.scheduleRefreshDetectedPartes();

        // Aguarda os dados das partes carregarem para atualizar dropdowns e injetar a Principal
        window.addEventListener('hcalc:partes-refreshed', () => {
            try {
                const passivo = window.hcalcPartesData?.passivo || [];

                // 1. Atualiza os dropdowns vazios agora que temos os dados
                if (responsabilidadesController && typeof responsabilidadesController.atualizarDropdownsPlanilhas === 'function') {
                    responsabilidadesController.atualizarDropdownsPlanilhas();
                }

                // 2. Injeta a primeira reclamada como Principal automaticamente
                if (passivo.length > 0 && responsabilidadesController && typeof responsabilidadesController.addPrincipal === 'function') {
                    const container = document.getElementById('resp-principais-dinamico-container');
                    const draftIsRestoring = overlayDraftApi && typeof overlayDraftApi.isRestoring === 'function' ? overlayDraftApi.isRestoring() : false;

                    // Só injeta se estiver vazio e não estiver restaurando um rascunho
                    if (container && container.children.length === 0 && !draftIsRestoring) {
                        responsabilidadesController.addPrincipal(passivo[0].nome);
                    }
                    if (passivo.length > 1 && !draftIsRestoring && typeof responsabilidadesController.inicializarBoxesReclamadasExtras === 'function') {
                        responsabilidadesController.inicializarBoxesReclamadasExtras(passivo);
                    }
                }

                // Se o checkbox de depósitos já estiver marcado (ex.: prep marcou antes das partes chegarem),
                // garantir que os depósitos sejam preenchidos agora que as partes estão disponíveis.
                try {
                    const chkDep = document.getElementById('chk-deposito');
                    if (chkDep && chkDep.checked && typeof preencherDepositosAutomaticos === 'function') {
                        preencherDepositosAutomaticos();
                    }
                } catch (e) { /* ignore */ }
            } catch (e) { console.error('[hcalc] Erro no auto-add principal:', e); }
        });

        // ==========================================
        // FASE 1: Sistema de Fases do Botão
        // ==========================================
        $('btn-abrir-homologacao').onclick = async () => {
            const btn = $('btn-abrir-homologacao');

            dbg('btn-abrir-homologacao clicked - intent: restaurar rascunho (sem abrir seletor)');

            // Valida se o sistema tem dados extraídos ou um rascunho salvo antes de prosseguir
            const raw = overlayDraftApi && typeof overlayDraftApi.loadRaw === 'function' ? overlayDraftApi.loadRaw(warn) : null;
            const hasDraft = raw && raw.state;
            const hasPlanilha = window.hcalcState && window.hcalcState.planilhaCarregada;

            if (!hasDraft && !hasPlanilha) {
                try { document.getElementById('input-planilha-pdf').click(); } catch (e) { alert('Nenhum rascunho salvo encontrado. Carregue a planilha primeiro (pelo botão de carregar planilha).'); }
                return;
            }
            
            // ATENÇÃO: O script agora segue a execução para forçar o executarPrep() a extrair recursos e Links,
            // e o draft será restaurado adequadamente depois que a UI estiver montada.

            dbg('FASE 3: Clique em Gerar Homologação');
            try {
                const peritosConh = window.hcalcPeritosConhecimentoDetectados || [];
                const partesData = window.hcalcPartesData || {};
                const prep = await executarPrep(partesData, peritosConh);

                window.hcalcLastPrepResult = prep;
                console.log('[INICIALIZAÇÃO] executarPrep retornou prep:', {
                    depositosCount: Array.isArray(prep?.depositos) ? prep.depositos.length : 0,
                    depositosSample: (prep?.depositos || []).slice(0,5)
                });
                window.hcalcPrepResult = prep;

                window.hcalcTimelineData = {
                    sentenca: prep.sentenca.data ? { data: prep.sentenca.data, href: prep.sentenca.href } : null,
                    acordaos: prep.acordaos,
                    editais: prep.editais
                };

                const labelDeposito = $('label-chk-deposito');
                if (labelDeposito) {
                    // Riscar apenas se não houver acórdão E também não houver depósito válido encontrado
                    labelDeposito.style.textDecoration = (prep.acordaos.length === 0 && prep.depositos.length === 0) ? 'line-through' : 'none';
                }

                const linkSentencaContainer = $('link-sentenca-container');
                if (linkSentencaContainer) {
                    linkSentencaContainer.innerHTML = '';
                    if (prep.sentenca.data) {
                        const info = [];
                        if (prep.sentenca.custas) info.push(`Custas: R$${prep.sentenca.custas}`);
                        if (prep.sentenca.responsabilidade) info.push(`Resp: ${prep.sentenca.responsabilidade}`);
                        if (prep.pericia.peritosComAjJt.length > 0) {
                            info.push(`Hon.Periciais: ${prep.pericia.peritosComAjJt.length} AJ-JT detectado(s)`);
                        } else if (prep.sentenca.honorariosPericiais.length > 0) {
                            info.push(`Hon.Periciais: ${prep.sentenca.honorariosPericiais.map(h => 'R$' + h.valor + (h.trt ? ' (TRT)' : '')).join(', ')}`);
                        }

                        linkSentencaContainer.innerHTML = `<span style="font-size:12px; color:#16a34a;">Sentença: ${prep.sentenca.data}${info.length ? ' | ' + info.join(' | ') : ''}</span>`;
                    }
                }

                const linkSentencaAcordaoContainer = $('link-sentenca-acordao-container');
                if (linkSentencaAcordaoContainer) {
                    linkSentencaAcordaoContainer.innerHTML = '';

                    if (prep.sentenca.href) {
                        const sentencaLink = document.createElement('a');
                        sentencaLink.href = '#';
                        sentencaLink.innerHTML = `<i class="fas fa-crosshairs"></i> Sentença${prep.sentenca.data ? ' - ' + prep.sentenca.data : ''}`;
                        sentencaLink.style.cssText = 'display:block; color:#16a34a; font-size:12px; margin-bottom:5px; text-decoration:none; font-weight:600; cursor:pointer;';
                        sentencaLink.addEventListener('click', (e) => {
                            e.preventDefault();
                            destacarElementoNaTimeline(prep.sentenca.href);
                        });
                        linkSentencaAcordaoContainer.appendChild(sentencaLink);
                    }

                    if (prep.acordaos.length > 0) {
                        prep.acordaos.forEach((acordao, i) => {
                            if (acordao.href) {
                                const lbl = prep.acordaos.length > 1 ? `Acórdão ${i + 1}` : 'Acórdão';
                                const a = document.createElement('a');
                                a.href = '#';
                                a.innerHTML = `<i class="fas fa-crosshairs"></i> ${lbl}${acordao.data ? ' - ' + acordao.data : ''}`;
                                a.style.cssText = 'display:block; color:#00509e; font-size:12px; margin-top:5px; text-decoration:none; cursor:pointer;';
                                a.addEventListener('click', (e) => {
                                    e.preventDefault();
                                    destacarElementoNaTimeline(acordao.href);
                                });
                                linkSentencaAcordaoContainer.appendChild(a);
                            }
                        });

                        // RECURSOS COM ANEXOS (integrado de rec.js v1.0)
                        if (prep.depositos.length > 0) {
                            const recDiv = document.createElement('div');
                            recDiv.style.cssText = 'margin-top:8px; padding:6px; background:#fffde7; border:1px solid #fbbf24; border-radius:4px;';
                            recDiv.innerHTML = `<strong style="font-size:11px;color:#92400e">📎 Recursos das Reclamadas (${prep.depositos.length})</strong>`;

                            prep.depositos.forEach((dep, depIdx) => {
                                const card = document.createElement('div');
                                card.className = 'rec-recurso-card';
                                card.dataset.href = dep.href || '';

                                const corBadge = { 'Depósito': '#10b981', 'Garantia': '#f59e0b', 'Custas': '#ef4444', 'Anexo': '#6b7280' };

                                let anexosHtml = '';
                                if (dep.anexos && dep.anexos.length > 0) {
                                    anexosHtml = `<div class="rec-anexos-lista">` +
                                        dep.anexos.map((ax, axIdx) =>
                                            `<div class="rec-anexo-item" data-dep-idx="${depIdx}" data-ax-idx="${axIdx}">
                                            <span class="rec-anexo-badge" style="background:${corBadge[ax.tipo] || '#6b7280'}">${ax.tipo}</span>
                                            <code class="rec-anexo-id">${ax.id || 'sem id'}</code>
                                            <span style="font-size:10px;color:#6b7280;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:120px" title="${ax.texto}">${ax.texto.substring(0, 40)}</span>
                                        </div>`
                                        ).join('') +
                                        `</div>`;
                                }

                                card.innerHTML = `
                                <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
                                    <span class="rec-tipo-badge">${dep.tipo || 'RO'}</span>
                                    <span style="font-size:11px;color:#92400e;font-weight:600;flex:1">${dep.depositante || 'Parte não identificada'}</span>
                                    ${dep.polo ? `<span style="font-size:9px;background:${dep.polo === 'PASSIVO' ? '#dc2626' : '#2563eb'};color:#fff;padding:1px 4px;border-radius:3px;margin-left:4px;font-weight:600">${dep.polo}</span>` : ''}
                                    <span style="font-size:10px;color:#6b7280">${dep.data || 'sem data'}</span>
                                    ${dep.anexos && dep.anexos.length > 0 ? `<span class="rec-seta-toggle">▶ ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}</span>` : ''}
                                </div>
                                ${anexosHtml}`;

                                card.addEventListener('click', e => {
                                    const axItem = e.target.closest('.rec-anexo-item');
                                    if (axItem) {
                                        e.stopPropagation();
                                        const axIdx = parseInt(axItem.dataset.axIdx, 10);
                                        const ax = dep.anexos[axIdx];
                                        if (!ax) return;

                                        // 1. Destacar o recurso na timeline
                                        if (dep.href) try { destacarElementoNaTimeline(dep.href); } catch (e2) { console.error('[hcalc]', e2); }

                                        // 2. Re-encontrar e clicar no anexo (evita referência stale do Angular)
                                        setTimeout(async () => {
                                            try {
                                                const item = encontrarItemTimeline(dep.href);
                                                if (item) {
                                                    await expandirAnexos(item);
                                                    const links = item.querySelectorAll('a.tl-documento[id^="anexo_"]');
                                                    let alvo = null;
                                                    if (ax.id) {
                                                        alvo = Array.from(links).find(l => l.textContent.includes(ax.id));
                                                    }
                                                    alvo = alvo || links[axIdx] || links[0];
                                                    if (alvo) safeDispatch(alvo, 'click', { bubbles: true, cancelable: true });
                                                } else if (ax.elemento && ax.elemento.isConnected) {
                                                    safeDispatch(ax.elemento, 'click', { bubbles: true, cancelable: true });
                                                }
                                            } catch (e3) { console.error('[hcalc] Erro ao clicar no anexo:', e3); }
                                        }, 600);
                                        return;
                                    }

                                    card.classList.toggle('expandido');
                                    const seta = card.querySelector('.rec-seta-toggle');
                                    if (seta) seta.textContent = card.classList.contains('expandido')
                                        ? `\u25bc ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}`
                                        : `\u25b6 ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}`;
                                    if (dep.href) try { destacarElementoNaTimeline(dep.href); } catch (e2) { console.error('[hcalc]', e2); }
                                });

                                recDiv.appendChild(card);
                            });

                            linkSentencaAcordaoContainer.appendChild(recDiv);
                        }
                    } else {
                        // Aviso quando não há acórdão
                        const avisoDiv = document.createElement('div');
                        avisoDiv.style.cssText = 'margin-top:8px; padding:8px; background:#fef2f2; border:1px solid #ef4444; border-radius:4px;';
                        avisoDiv.innerHTML = `<span style="font-size:12px; color:#dc2626; font-weight:600;">⚠ Não há Acórdão</span>`;
                        linkSentencaAcordaoContainer.appendChild(avisoDiv);
                    }
                }

                // Preencher card de Conferência de Acórdão
                try {
                    const conf = prep.conferenciaAcordao || null;
                    const confContainer = $('conferencia-acordao-container');
                    const confBody = $('conferencia-acordao-body');
                    if (conf && confBody && confContainer) {
                        confContainer.classList.remove('hidden');
                        const lines = [];
                        lines.push(`<div><strong>Status:</strong> ${conf.ok ? '✅ OK' : '❌ Não OK'}</div>`);
                        if (conf.despacho) {
                            lines.push(`<div><strong>Despacho:</strong> ${conf.despacho.data ? conf.despacho.data : ''} ${conf.despacho.uid ? ' (uid: ' + conf.despacho.uid + ')' : ''}</div>`);
                        }
                        if (conf.analise) {
                            const a = conf.analise;
                            lines.push(`<div style="margin-top:6px"><strong>Análise:</strong></div>`);
                            lines.push(`<div>Sentença mantida: ${a.mantidaSentenca ? '✅' : '❌'}</div>`);
                            lines.push(`<div>Exclusão de reclamadas: ${Array.isArray(a.exclusaoReclamadas) && a.exclusaoReclamadas.length ? a.exclusaoReclamadas.join(', ') : 'nenhuma'}</div>`);
                            lines.push(`<div>Rearbitramento de custas: ${a.rearbitramentoCustas ? '✅' : '❌'}</div>`);
                            lines.push(`<div>CTPS anotação: ${a.ctpsAnotacao ? '✅' : '❌'}</div>`);
                            lines.push(`<div>FGTS depósito: ${a.fgtsDeposito ? '✅' : '❌'}</div>`);
                        }
                        confBody.innerHTML = lines.join('');
                    } else if (confContainer && confBody) {
                        confContainer.classList.add('hidden');
                        confBody.innerHTML = '';
                    }
                } catch (e) { console.warn('[hcalc] falha ao preencher conferenciaAcordao:', e); }

                // Preencher custas automaticamente (planilha vs sentença)
                if (window.hcalcState.planilhaExtracaoData?.custas && $('val-custas')) {
                    const custasPlanilha = window.hcalcState.planilhaExtracaoData.custas;
                    const custasSentenca = prep.sentenca?.custas || '';
                    $('val-custas').value = custasPlanilha;

                    const valorPlanilha = parseMoney(custasPlanilha || '0');
                    const valorSentenca = parseMoney(custasSentenca || '0');
                    const temCustasSentenca = !!custasSentenca;
                    const custasDiferentes = temCustasSentenca && Math.abs(valorPlanilha - valorSentenca) > 0.0001;
                    const origemPlanilha = !temCustasSentenca || custasDiferentes;

                    if ($('custas-origem')) {
                        $('custas-origem').value = origemPlanilha ? 'planilha' : 'sentenca';
                        $('custas-origem').dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // Regra: diferentes da sentença => data da planilha; iguais => data da sentença
                    if (origemPlanilha) {
                        if (window.hcalcState.planilhaExtracaoData.dataAtualizacao && $('custas-data-origem')) {
                            $('custas-data-origem').value = window.hcalcState.planilhaExtracaoData.dataAtualizacao;
                        }
                    } else if (prep.sentenca.data && $('custas-data-origem')) {
                        $('custas-data-origem').value = prep.sentenca.data;
                    }
                } else if (prep.sentenca.custas && $('val-custas')) {
                    $('val-custas').value = prep.sentenca.custas;
                    if ($('custas-origem')) {
                        $('custas-origem').value = 'sentenca';
                        $('custas-origem').dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    // Data das custas = data da sentença (apenas se não há planilha)
                    if (prep.sentenca.data && $('custas-data-origem')) {
                        $('custas-data-origem').value = prep.sentenca.data;
                    }
                }

                // Se tem recurso da reclamada ou depósitos detectados → custas já pagas
                if ((prep.recursosPassivo && prep.recursosPassivo.length > 0) || (prep.depositos && prep.depositos.length > 0)) {
                    const custasStatusEl = $('custas-status');
                    if (custasStatusEl) {
                        custasStatusEl.value = 'pagas';
                        console.log('[hcalc] Recurso/depósito detectado! Custas marcadas como pagas.');
                    }
                }

                // Depósito recursal: visível se tem acórdãos OU se encontrou depósitos válidos
                const fieldsetDeposito = $('fieldset-deposito');
                if (prep.acordaos.length === 0 && prep.depositos.length === 0) {
                    if (fieldsetDeposito) fieldsetDeposito.classList.add('hidden');
                } else {
                    if (fieldsetDeposito) fieldsetDeposito.classList.remove('hidden');
                }

                // Povoar select de acórdãos se existirem
                const custasAcordaoSelect = $('custas-acordao-select');
                if (custasAcordaoSelect && prep.acordaos.length > 0) {
                    custasAcordaoSelect.innerHTML = '<option value="">Selecione o acórdão</option>';
                    prep.acordaos.forEach((acordao, i) => {
                        const opt = document.createElement('option');
                        opt.value = i;
                        opt.textContent = `Acórdão ${i + 1}${acordao.data ? ' - ' + acordao.data : ''}`;
                        opt.dataset.data = acordao.data || '';
                        opt.dataset.id = acordao.id || '';
                        custasAcordaoSelect.appendChild(opt);
                    });
                }

                // Editais — exibir como texto informativo (sem links clicáveis)
                const editaisContainer = $('links-editais-container');
                const editaisLista = $('links-editais-lista');
                if (editaisContainer && editaisLista) {
                    editaisLista.innerHTML = '';
                    if (prep.editais.length > 0) {
                        editaisContainer.classList.remove('hidden');
                        editaisLista.innerHTML = prep.editais.map((e, i) =>
                            `<span style="display:inline-block; margin-right:10px; color:#374151; font-size:12px;">` +
                            `Edital ${i + 1}${e.data ? ' (' + e.data + ')' : ''}` +
                            `</span>`
                        ).join('');
                    } else {
                        editaisContainer.classList.add('hidden');
                    }
                }

                // ==========================================
                // REGRAS AUTO-PREENCHIMENTO (prep sobrepõe defaults)
                // ==========================================

                // REGRA 1: Depósito recursal — disparar evento onChange para unificar fluxo
                // CORREÇÃO 2: Usar dispatchEvent em vez de manipulação direta do DOM
                if (prep.depositos.length > 0) {
                    console.log('[INICIALIZAÇÃO] Detectados', prep.depositos.length, 'recursos com depósito/garantia');

                    const chkDep = $('chk-deposito');
                    if (chkDep) {
                        chkDep.checked = true;
                        // Disparar onChange sintético — aciona visibilidade E preencherDepositosAutomaticos
                        // de forma unificada, eliminando dessincronização
                        chkDep.dispatchEvent(new Event('change', { bubbles: true }));
                        console.log('[INICIALIZAÇÃO] Evento change disparado');
                    }
                }

                // REGRA 2: Perito conhecimento + TRT / AJ-JT match
                const peritoTipoEl = $('perito-tipo-pag');
                const peritoValorEl = $('val-perito-valor');
                const peritoDataEl = $('val-perito-data');
                if (prep.pericia.peritosComAjJt.length > 0) {
                    // Perito casou com AJ-JT — pago pelo TRT
                    const match = prep.pericia.peritosComAjJt[0];
                    if (peritoTipoEl) peritoTipoEl.value = 'trt';
                    if (peritoValorEl) peritoValorEl.value = match.idAjJt || '';
                } else if (prep.sentenca.honorariosPericiais.length > 0 && (!(window.hcalcPeritosConhecimentoDetectados || []).length)) {
                    // Honorários periciais na sentença (casos antigos onde o perito
                    // não aparece na busca de partes). Preenche campos e marca a
                    // seção de perícia para permitir edição manual adicional.
                    const hon = prep.sentenca.honorariosPericiais[0];
                    if (hon.trt && peritoTipoEl) {
                        peritoTipoEl.value = 'trt';
                    }
                    // Sempre preencher valor se detectado
                    if (peritoValorEl && !peritoValorEl.value) {
                        peritoValorEl.value = 'R$' + hon.valor;
                    }

                    // Marcar a checkbox e expor campos de perícia de conhecimento
                    const chkPeritoConh = $('chk-perito-conh');
                    if (chkPeritoConh) {
                        chkPeritoConh.checked = true;
                        chkPeritoConh.dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // Preencher o campo de nomes com um marcador informando
                    // que foi detectado na sentença; o usuário pode editar
                    // ou acrescentar nomes manualmente separados por '|'.
                    const peritoNomeEl = $('val-perito-nome');
                    const etiqueta = prep.sentenca.honorariosPericiais
                        .map(h => (h.nome ? h.nome : 'Detectado em sentença — revisar'))
                        .join(' | ');
                    if (peritoNomeEl && !peritoNomeEl.value) {
                        peritoNomeEl.value = etiqueta;
                    }

                    // Atualiza a variável detectada global para que o gerador
                    // de decisão utilize esse nome automaticamente.
                    try {
                        window.hcalcPeritosConhecimentoDetectados = etiqueta.split('|').map(s => s.trim()).filter(Boolean);
                    } catch (e) {
                        console.warn('[hcalc] falha ao setar peritos detectados:', e);
                    }
                }
                // Data da sentença no campo de data do perito
                if (prep.sentenca.data && peritoDataEl && !peritoDataEl.value) {
                    peritoDataEl.value = prep.sentenca.data;
                }

                // REGRA 3 e 4: Responsabilidade (subsidiária / solidária)
                const respTipoEl = $('resp-tipo');
                const respSubOpcoes = $('resp-sub-opcoes');
                const passivo = window.hcalcPartesData?.passivo || [];
                if (prep.sentenca.responsabilidade && respTipoEl) {
                    if (prep.sentenca.responsabilidade === 'subsidiaria') {
                        respTipoEl.value = 'subsidiarias';
                        if (respSubOpcoes) respSubOpcoes.classList.remove('hidden');
                    } else if (prep.sentenca.responsabilidade === 'solidaria') {
                        respTipoEl.value = 'solidarias';
                        if (respSubOpcoes) respSubOpcoes.classList.add('hidden');
                    }
                } else if (passivo.length <= 1 && respTipoEl) {
                    respTipoEl.value = 'unica';
                    if (respSubOpcoes) respSubOpcoes.classList.add('hidden');
                }

                // REGRA 5: Custas
                // Sempre padrão = sentença (usuário pode mudar para acórdão se necessário)
                const custasStatusEl = $('custas-status');
                const custasOrigemEl = $('custas-origem');
                if (prep.sentenca.custas) {
                    // ATENÇÃO: Não sobrepõe se planilha já preencheu custas
                    if ($('val-custas') && !window.hcalcState.planilhaExtracaoData?.custas) {
                        $('val-custas').value = prep.sentenca.custas;
                    }
                    // Sempre usa sentença como padrão, salvo se houver recurso da reclamada
                        if (custasStatusEl) {
                            if ((prep.recursosPassivo && prep.recursosPassivo.length > 0) || (prep.depositos && prep.depositos.length > 0)) {
                                custasStatusEl.value = 'pagas';
                            } else {
                                custasStatusEl.value = 'devidas';
                            }
                        }
                    if (custasOrigemEl) custasOrigemEl.value = 'sentenca';
                    // ATENÇÃO: Não sobrepõe data se planilha já preencheu
                    if ($('custas-data-origem') && prep.sentenca.data && !window.hcalcState.planilhaExtracaoData?.custas) {
                        $('custas-data-origem').value = prep.sentenca.data;
                    }
                }

                // REGRA 6: hsusp → Honorários Adv. Réu com condição suspensiva
                const chkHonReu = $('chk-hon-reu');
                const honReuCampos = $('hon-reu-campos');
                if (prep.sentenca.hsusp) {
                // Desmarcar "Não há" e forçar suspensiva quando sentença tem condição suspensiva
                if (chkHonReu) chkHonReu.checked = false;
                if (honReuCampos) honReuCampos.classList.remove('hidden');

                const radSusp = document.querySelector('input[name="rad-hon-reu"][value="suspensiva"]');
                if (radSusp) radSusp.checked = true;
            }
            // else: manter default do HTML (chk-hon-reu desmarcado = campos visíveis)
                // ==========================================
                // PREENCHER COM DADOS DA PLANILHA (PRIORIDADE)
                // ==========================================
                if (window.hcalcState.planilhaExtracaoData) {
                    const dados = window.hcalcState.planilhaExtracaoData;
                    dbg('Preenchendo campos do overlay com planilhaExtracaoData:', dados);

                    if (dados.idPlanilha && $('val-id')) $('val-id').value = dados.idPlanilha;
                    if (dados.verbas && $('val-credito')) $('val-credito').value = dados.verbas;

                    // FGTS: preencher valor + ajustar checkbox
                    if ($('val-fgts') && $('calc-fgts')) {
                        const temFgts = dados.fgts && dados.fgts !== '0,00' && dados.fgts !== '0';

                        if (temFgts) {
                            $('val-fgts').value = dados.fgts;
                            $('calc-fgts').checked = true;
                        } else {
                            // Sem FGTS detectado → desmarcar checkbox (que vem marcado por padrão)
                            $('calc-fgts').checked = false;
                        }
                        $('calc-fgts').dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // INSS: preencher valores + ajustar checkbox se não há nenhum
                    if (dados.inssTotal && $('val-inss-total')) $('val-inss-total').value = dados.inssTotal;
                    if (dados.inssAutor && $('val-inss-rec')) $('val-inss-rec').value = dados.inssAutor;

                    // Verificar se não há INSS nenhum
                    const semInssTotal = !dados.inssTotal || dados.inssTotal === '0,00' || dados.inssTotal === '0';
                    const semInssAutor = !dados.inssAutor || dados.inssAutor === '0,00' || dados.inssAutor === '0';

                    if (semInssTotal && semInssAutor && $('ignorar-inss')) {
                        $('ignorar-inss').checked = true;
                        $('ignorar-inss').dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // Custas: comparar planilha x sentença para definir origem/data
                    if (dados.custas && $('val-custas')) {
                        $('val-custas').value = dados.custas;
                        const custasSentenca = window.hcalcPrepResult?.sentenca?.custas || '';
                        const dataSentenca = window.hcalcPrepResult?.sentenca?.data || '';
                        const valorPlanilha = parseMoney(dados.custas || '0');
                        const valorSentenca = parseMoney(custasSentenca || '0');
                        const temCustasSentenca = !!custasSentenca;
                        const custasDiferentes = temCustasSentenca && Math.abs(valorPlanilha - valorSentenca) > 0.0001;
                        const origemPlanilha = !temCustasSentenca || custasDiferentes;

                        if ($('custas-origem')) {
                            $('custas-origem').value = origemPlanilha ? 'planilha' : 'sentenca';
                            $('custas-origem').dispatchEvent(new Event('change', { bubbles: true }));
                        }

                        if (origemPlanilha) {
                            if (dados.dataAtualizacao && $('custas-data-origem')) {
                                $('custas-data-origem').value = dados.dataAtualizacao;
                            }
                        } else if (dataSentenca && $('custas-data-origem')) {
                            $('custas-data-origem').value = dataSentenca;
                        }
                    }

                    if (dados.dataAtualizacao && $('val-data')) $('val-data').value = dados.dataAtualizacao;
                    if (dados.honAutor && $('val-hon-autor')) $('val-hon-autor').value = dados.honAutor;

                    // Honorários da reclamada: preencher valor + marcar checkbox automaticamente
                    if (dados.honReu && $('val-hon-reu')) {
                        $('val-hon-reu').value = dados.honReu;

                        // Marcar radio "com valor" se existir
                        const radComValor = document.querySelector('input[name="hon-reu-tipo"][value="valor"]');
                        if (radComValor) {
                            radComValor.checked = true;
                            radComValor.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }

                    // Aplicar IRPF se tributável
                    if (dados.irpfIsento === false) {
                        const irpfTipoEl = document.getElementById('irpf-tipo');
                        if (irpfTipoEl && irpfTipoEl.options.length > 1) {
                            irpfTipoEl.value = irpfTipoEl.options[1].value; // primeiro != 'isento'
                            irpfTipoEl.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }

                    // Auto-selecionar origem como PJeCalc
                    if ($('calc-origem')) $('calc-origem').value = 'pjecalc';
                }

                // Mostrar card colapsado se planilha foi carregada (Fase 3)
                const resumoCard = $('resumo-extracao-card');
                if (resumoCard && window.hcalcState.planilhaExtracaoData) {
                    resumoCard.style.display = 'block';
                    // Preencher conteúdo do card
                    const dados = window.hcalcState.planilhaExtracaoData;
                    const resumoConteudo = $('resumo-conteudo');
                    if (resumoConteudo) {
                        resumoConteudo.innerHTML = `
                            <div class="resumo-item"><strong>ID:</strong> ${dados.idPlanilha || 'N/A'}</div>
                            <div class="resumo-item"><strong>Crédito:</strong> R$ ${dados.verbas || '0,00'}</div>
                            ${dados.fgts ? `<div class="resumo-item"><strong>FGTS:</strong> R$ ${dados.fgts}</div>` : ''}
                            <div class="resumo-item"><strong>INSS Total:</strong> R$ ${dados.inssTotal || '0,00'}</div>
                            <div class="resumo-item"><strong>INSS Rec:</strong> R$ ${dados.inssAutor || '0,00'}</div>
                            ${dados.custas ? `<div class="resumo-item"><strong>Custas:</strong> R$ ${dados.custas}</div>` : ''}
                            <div class="resumo-item"><strong>Data:</strong> ${dados.dataAtualizacao || 'N/A'}</div>
                            ${dados.periodoCalculo ? `<div class="resumo-item"><strong>Período:</strong> ${dados.periodoCalculo}</div>` : ''}
                            ${dados.irpfIsento === false ? `<div class="resumo-item" style="color:#b45309"><strong>IRPF:</strong> Tributável</div>` : ''}
                        `;
                    }
                }

                restoreOverlayDraft();
                $('homologacao-overlay').style.display = 'flex';
                dbg('Overlay exibido para o usuario.');

                updateHighlight();
            } catch (e) {
                err('Erro no handler do botao Gerar Homologacao:', e);
                alert('Erro ao abrir assistente. Verifique o console (F12).');
                return;
            }
        };

        // ==========================================
        // FASE 2: Handler do Input File (Carregar Planilha) - UNIFICADO
        // ==========================================
        const fileInput = document.getElementById('input-planilha-pdf');
        if (fileInput && !fileInput._hcalcBound) {
            fileInput._hcalcBound = true;
            fileInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                const btn = $('btn-abrir-homologacao');
                btn.textContent = '⏳ Processando...';
                btn.disabled = true;

                try {
                    // Configurar PDF.js (primeira vez)
                    const loaded = await carregarPDFJSSeNecessario();
                    if (!loaded) {
                        throw new Error('PDF.js não disponível');
                    }

                    // Processar planilha
                    const dados = await processarPlanilhaPDF(file);

                    if (dados.sucesso) {
                        // Salvar no state
                        window.hcalcState.planilhaExtracaoData = dados;
                        window.hcalcState.planilhaCarregada = true;
                        dbg('Planilha processada e salva em state:', dados);

                        // Atualizar card/resumo
                        if (window.hcalcAtualizarResumoPlanilha) {
                            window.hcalcAtualizarResumoPlanilha(dados);
                        }

                        // Atualizar dropdowns de linhas extras com a planilha principal recém-carregada
                        atualizarDropdownsPlanilhas();

                        // Atualizar botão
                        btn.textContent = '✓ Dados Extraídos';
                        btn.style.background = '#10b981';
                        btn.disabled = false;

                        // Limpar o rascunho em FASE 2 para impedir que campos vazios do DOM sejam salvos e sobreponham a Fase 3
                        if (window.hcalcClearOverlayDraft) {
                            window.hcalcClearOverlayDraft();
                        }

                        dbg('Planilha extraída:', dados);

                        // Feedback visual momentâneo
                        setTimeout(() => {
                            btn.textContent = 'Gerar Homologação';
                            btn.style.background = '#00509e';
                        }, 2000);
                    } else {
                        throw new Error(dados.erro || 'Erro desconhecido');
                    }
                } catch (error) {
                    console.error('[HCalc] Erro ao processar PDF:', error.message);
                    alert('Erro ao processar PDF: ' + error.message);
                    btn.textContent = '📄 Carregar Planilha';
                    btn.disabled = false;
                    window.hcalcState.planilhaCarregada = false;
                }
            });
        }

        $('btn-reload-planilha').onclick = () => {
            const inputFile = $('input-planilha-pdf');
            inputFile.click();
        };

        $('btn-fechar').onclick = (e) => {
            e.preventDefault();  // Previne scroll indesejado
            const modal = $('homologacao-modal');
            const overlay = $('homologacao-overlay');
            modal.style.opacity = '1';
            modal.style.pointerEvents = 'all';
            modal.dataset.ghost = 'false';
            overlay.style.display = 'none';
            overlay.style.pointerEvents = 'none';
            // LIMPAR REFERÊNCIAS DOM: v1.8 usa método centralizado
            window.hcalcState.resetPrep();
            console.log('[hcalc] Estado resetado via hcalcState.resetPrep()');
        };
        $('homologacao-overlay').onclick = (e) => {
            if (e.target.id === 'homologacao-overlay') {
                // Não fecha — torna transparente e "fantasma"
                const modal = $('homologacao-modal');
                const overlay = $('homologacao-overlay');
                const isGhost = modal.dataset.ghost === 'true';
                if (isGhost) {
                    // Segundo clique fora: volta ao normal
                    modal.style.opacity = '1';
                    modal.style.pointerEvents = 'all';
                    overlay.style.pointerEvents = 'none';
                    modal.dataset.ghost = 'false';
                } else {
                    // Primeiro clique fora: vira fantasma
                    modal.style.opacity = '0.25';
                    modal.style.transition = 'opacity 0.3s';
                    modal.style.pointerEvents = 'none';
                    // Mantém overlay transparente para detectar clique de retorno
                    overlay.style.pointerEvents = 'all';
                    modal.dataset.ghost = 'true';
                }
            }
        };

        $('calc-origem').onchange = (e) => { $('col-pjc').classList.toggle('hidden', e.target.value !== 'pjecalc'); };
        $('calc-autor').onchange = (e) => { $('col-esclarecimentos').classList.toggle('hidden', e.target.value !== 'perito'); };
        $('calc-esclarecimentos').onchange = (e) => { $('calc-peca-perito').classList.toggle('hidden', !e.target.checked); };

        $('calc-fgts').onchange = (e) => {
            const isChecked = e.target.checked;
            $('fgts-opcoes').classList.toggle('hidden', !isChecked);
            $('row-fgts-valor').classList.toggle('hidden', !isChecked);
            updateHighlight();

            try {
                // Se FGTS separado e marcado como 'depositado', exibir modal bloqueante
                if (isChecked) {
                    const fgtsTipo = document.querySelector('input[name="fgts-tipo"]:checked')?.value || 'devido';
                    if (fgtsTipo === 'depositado') {
                        if (document.getElementById('maisPje_fgts_modal_overlay')) return;
                        const overlay = document.createElement('div');
                        overlay.id = 'maisPje_fgts_modal_overlay';
                        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.45);z-index:2147483647;display:flex;align-items:center;justify-content:center;';

                        const box = document.createElement('div');
                        box.id = 'maisPje_fgts_modal_box';
                        box.style.cssText = 'background:#ffffff;padding:18px;border-radius:8px;max-width:620px;color:#222;box-shadow:0 12px 32px rgba(0,0,0,0.35);font-family:sans-serif;line-height:1.35;';

                        const title = document.createElement('div');
                        title.style.cssText = 'font-weight:700;margin-bottom:8px;font-size:15px;color:#333';
                        title.textContent = 'Atenção';

                        const msg = document.createElement('div');
                        msg.style.cssText = 'margin-bottom:14px;font-size:13px;color:#333';
                        msg.textContent = 'Se depositado, o valor deve estar diretamente lançado na planilha geral, e não contabilizado no valor bruto devido ao reclamante.';

                        const actions = document.createElement('div');
                        actions.style.cssText = 'text-align:right;';
                        const ok = document.createElement('button');
                        ok.id = 'maisPje_fgts_modal_ok';
                        ok.textContent = 'OK';
                        ok.style.cssText = 'padding:8px 14px;background:#007bff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600';

                        actions.appendChild(ok);
                        box.appendChild(title);
                        box.appendChild(msg);
                        box.appendChild(actions);
                        overlay.appendChild(box);
                        document.body.appendChild(overlay);

                        ok.addEventListener('click', () => overlay.remove());
                    }
                }
            } catch (ex) { console.warn('maisPJe: erro ao mostrar modal FGTS (BASE)', ex); }
        };
        // Adicionar listener para mudanças no tipo de FGTS (ex.: usuário marca 'depositado' depois)
        try {
            document.querySelectorAll('input[name="fgts-tipo"]').forEach(r => {
                r.addEventListener('change', (ev) => {
                    try {
                        const val = ev.target.value;
                        if (val === 'depositado' && $('calc-fgts') && $('calc-fgts').checked) {
                            // Reusar código do modal definido acima
                            if (document.getElementById('maisPje_fgts_modal_overlay')) return;
                            const overlay = document.createElement('div');
                            overlay.id = 'maisPje_fgts_modal_overlay';
                            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.45);z-index:2147483647;display:flex;align-items:center;justify-content:center;';

                            const box = document.createElement('div');
                            box.id = 'maisPje_fgts_modal_box';
                            box.style.cssText = 'background:#ffffff;padding:18px;border-radius:8px;max-width:620px;color:#222;box-shadow:0 12px 32px rgba(0,0,0,0.35);font-family:sans-serif;line-height:1.35;';

                            const title = document.createElement('div');
                            title.style.cssText = 'font-weight:700;margin-bottom:8px;font-size:15px;color:#333';
                            title.textContent = 'Atenção';

                            const msg = document.createElement('div');
                            msg.style.cssText = 'margin-bottom:14px;font-size:13px;color:#333';
                            msg.textContent = 'Se depositado, o valor deve estar diretamente lançado na planilha geral, e não contabilizado no valor bruto devido ao reclamante.';

                            const actions = document.createElement('div');
                            actions.style.cssText = 'text-align:right;';
                            const ok = document.createElement('button');
                            ok.id = 'maisPje_fgts_modal_ok';
                            ok.textContent = 'OK';
                            ok.style.cssText = 'padding:8px 14px;background:#007bff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600';

                            actions.appendChild(ok);
                            box.appendChild(title);
                            box.appendChild(msg);
                            box.appendChild(actions);
                            overlay.appendChild(box);
                            document.body.appendChild(overlay);

                            ok.addEventListener('click', () => overlay.remove());
                        }
                    } catch (ex) { console.warn('maisPJe: erro no fgts-tipo change handler', ex); }
                });
            });
        } catch (e) { /* ignore */ }
        $('calc-indice').onchange = (e) => { $('col-juros-val').classList.toggle('hidden', e.target.value !== 'tr'); };
        $('ignorar-hon-autor').onchange = (e) => { $('val-hon-autor').classList.toggle('hidden', e.target.checked); updateHighlight(); };
        $('ignorar-inss').onchange = (e) => {
            $('val-inss-rec').classList.toggle('hidden', e.target.checked);
            $('val-inss-total').classList.toggle('hidden', e.target.checked);
            updateHighlight();
        };
        $('irpf-tipo').onchange = (e) => { $('irpf-campos').classList.toggle('hidden', e.target.value === 'isento'); };

        responsabilidadesController.initEventHandlers();

        // Garantir visibilidade correta dos fieldsets integrais: ambos PAI e FILHO devem estar marcados
        function enforceIntegralVisibility() {
            try {
                if ($('resp-subsidiarias-integral-fieldset')) {
                    const isSubAtiva = $('resp-subsidiarias') && $('resp-subsidiarias').checked;
                    const isSubIntAtiva = $('resp-sub-integral') && $('resp-sub-integral').checked;
                    $('resp-subsidiarias-integral-fieldset').classList.toggle('hidden', !(isSubAtiva && isSubIntAtiva));
                }

                if ($('resp-solidarias-integral-fieldset')) {
                    const isSolAtiva = $('resp-solidarias') && $('resp-solidarias').checked;
                    const isSolIntAtiva = $('resp-sol-integral') && $('resp-sol-integral').checked;
                    $('resp-solidarias-integral-fieldset').classList.toggle('hidden', !(isSolAtiva && isSolIntAtiva));
                }
            } catch (e) { /* ignore */ }
        }

        // Escutar mudanças relevantes para manter sincronização (pais e filhos)
        ['resp-subsidiarias','resp-sub-integral','resp-solidarias','resp-sol-integral'].forEach(id => {
            const el = $(id);
            if (el) el.addEventListener('change', enforceIntegralVisibility);
        });

        // Estado inicial
        enforceIntegralVisibility();

        function aplicarEstiloRecuperacaoJudicial() {
            return responsabilidadesController.aplicarEstiloRecuperacaoJudicial();
        }

        function atualizarDropdownsPlanilhas() {
            return responsabilidadesController.atualizarDropdownsPlanilhas();
        }

        function adicionarLinhaPeridoDiverso() {
            return responsabilidadesController.adicionarLinhaPeridoDiverso();
        }

        $('chk-hon-reu').onchange = (e) => {
            // Lógica invertida: marcado = "Não há" = esconde campos
            $('hon-reu-campos').classList.toggle('hidden', e.target.checked);
        };

        // Controlar exibição de campo percentual vs valor
        document.querySelectorAll('input[name="rad-hon-reu-tipo"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const isPercentual = e.target.value === 'percentual';
                $('hon-reu-perc-campo').classList.toggle('hidden', !isPercentual);
                $('hon-reu-valor-campo').classList.toggle('hidden', isPercentual);
            });
        });

        $('chk-perito-conh').onchange = (e) => { $('perito-conh-campos').classList.toggle('hidden', !e.target.checked); };

        // CORREÇÃO 4: Event listener simplificado - guard interno em preencherDepositosAutomaticos
        $('chk-deposito').onchange = (e) => {
            // Toggle visibilidade
            $('deposito-campos').classList.toggle('hidden', !e.target.checked);

            // Preencher automaticamente se marcado (safe: tem guard para jaTemCampos)
            if (e.target.checked) {
                preencherDepositosAutomaticos();
            }
        };

        $('chk-pag-antecipado').onchange = (e) => {
            $('pag-antecipado-campos').classList.toggle('hidden', !e.target.checked);
            if (e.target.checked && window.hcalcState.pagamentosAntecipados.length === 0) {
                adicionarPagamentoAntecipado(); // Adiciona primeiro pagamento automaticamente
            }
        };

        // Event listeners para radios de tipo de liberação
        document.querySelectorAll('input[name="lib-tipo"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const valor = e.target.value;
                $('lib-remanescente-campos').classList.toggle('hidden', valor !== 'remanescente');
                $('lib-devolucao-campos').classList.toggle('hidden', valor !== 'devolucao');
            });
        });

        document.getElementsByName('rad-intimacao').forEach((rad) => {
            rad.onchange = (e) => { $('intimacao-mandado-campos').classList.toggle('hidden', e.target.value === 'diario'); };
        });

        // ==========================================
        // ==========================================
        // FUNÇÕES DE GERENCIAMENTO DE MÚLTIPLOS DEPÓSITOS
        // ==========================================

        function preencherDepositosAutomaticos() {
            return depositosController.preencherDepositosAutomaticos();
        }

        function adicionarDepositoRecursal() {
            return depositosController.adicionarDepositoRecursal();
        }

        function atualizarVisibilidadeDepositoPrincipal(idx) {
            return depositosController.atualizarVisibilidadeDepositoPrincipal(idx);
        }

        function adicionarPagamentoAntecipado() {
            return depositosController.adicionarPagamentoAntecipado();
        }

        window.hcalcAtualizarVisibilidadeDepositoPrincipal = atualizarVisibilidadeDepositoPrincipal;

        // Bind dos botões de adicionar
        $('btn-add-deposito').onclick = adicionarDepositoRecursal;
        $('btn-add-pagamento').onclick = adicionarPagamentoAntecipado;

        // Máscara de data DD/MM/YYYY para campos de data
        const aplicarMascaraData = (input) => {
            input.addEventListener('input', (e) => {
                let valor = e.target.value.replace(/\D/g, ''); // Remove não-dígitos
                if (valor.length >= 2) {
                    valor = valor.slice(0, 2) + '/' + valor.slice(2);
                }
                if (valor.length >= 5) {
                    valor = valor.slice(0, 5) + '/' + valor.slice(5);
                }
                e.target.value = valor.slice(0, 10); // Limita a DD/MM/YYYY
            });
        };

        // Aplicar máscara aos campos de data
        ['val-data', 'custas-data-origem', 'val-perito-data'].forEach(id => {
            const campo = $(id);
            if (campo) aplicarMascaraData(campo);
        });

        // Toggle origem custas: Sentença vs Acórdão
        $('custas-origem').onchange = (e) => {
            const isAcordao = e.target.value === 'acordao';
            $('custas-data-col').classList.toggle('hidden', isAcordao);
            $('custas-acordao-col').classList.toggle('hidden', !isAcordao);
        };

        const ordemCopiaLabels = {
            'val-id': '1) Id da Planilha',
            'val-data': '1) Data da Atualização',
            'val-credito': '1) Crédito Principal',
            'val-fgts': '1) FGTS Separado',
            'val-inss-rec': '2) INSS - Desconto Reclamante',
            'val-inss-total': '2) INSS - Total Empresa',
            'val-hon-autor': '3) Honorários do Autor',
            'val-custas': '4) Custas'
        };

        window.hcalcPeritosDetectados = [];
        window.hcalcPeritosConhecimentoDetectados = [];


        function atualizarStatusProximoCampo(nextInputId = null) {
            // Função simplificada - status removido da interface
            // Mantida para compatibilidade com código existente
        }

        // Timeline functions moved to prep.js
        // readTimelineBasic / extractDataFromTimelineItem / getTimelineItems
        // now handled by window.executarPrep()

        // ==========================================
        // 4. LÓGICA DE NAVEGAÇÃO "COLETA INTELIGENTE"
        // ==========================================
        const orderSequence = [
            'val-id', 'val-data', 'val-credito', 'val-fgts',
            'val-inss-rec', 'val-inss-total', 'val-hon-autor', 'val-custas'
        ];

        function updateHighlight(currentId = null) {
            orderSequence.forEach((id) => $(id).classList.remove('highlight'));
            const visibleInputs = orderSequence.filter((id) => !$(id).classList.contains('hidden'));
            if (visibleInputs.length === 0) return;
            let nextIndex = 0;
            if (currentId) {
                const currentIndex = visibleInputs.indexOf(currentId);
                if (currentIndex !== -1 && currentIndex < visibleInputs.length - 1) {
                    nextIndex = currentIndex + 1;
                } else if (currentIndex === visibleInputs.length - 1) {
                    return;
                }
            }
            const nextInputId = visibleInputs[nextIndex];
            $(nextInputId).classList.add('highlight');
            $(nextInputId).focus();
            atualizarStatusProximoCampo(nextInputId);
        }

        orderSequence.forEach((id) => {
            const el = $(id);
            el.addEventListener('paste', () => {
                setTimeout(() => {
                    el.value = el.value.trim();
                    updateHighlight(id);
                }, 10);
            });
            el.addEventListener('focus', () => {
                orderSequence.forEach((i) => $(i).classList.remove('highlight'));
                el.classList.add('highlight');
            });
        });

        // ==========================================
        // 5. FUNÇÕES AUXILIARES DE CÁLCULO E TEXTO
        function parseMoney(str) {
            if (!str) return 0;
            str = str.replace(/[R$\s]/g, '').replace(/\./g, '').replace(',', '.');
            const num = parseFloat(str);
            return isNaN(num) ? 0 : num;
        }

        function formatMoney(num) {
            return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }).replace(/\s/g, '');
        }

        function normalizeMoneyInput(val) {
            if (!val || val === '[VALOR]') return val;
            const parsed = parseMoney(val);
            if (parsed === 0 && !/^\s*0/.test(val)) return val;
            return formatMoney(parsed);
        }

        function bold(text) { return `<strong>${text}</strong>`; }
        function u(text) { return `<u>${text}</u>`; }

        const decisaoController = window.hcalcOverlayDecisao.createController({
            $,
            dbg,
            logError: err,
            parseMoney,
            formatMoney,
            normalizeMoneyInput,
            bold,
            u,
            isNomeRogerio,
            responsabilidadesTextoApi
        });

        // ==========================================
        // 6. GERADOR DE DECISÃO HTML (O CORE)
        // ==========================================
        $('btn-gravar').onclick = decisaoController.handleGravar;

        dbg('initializeOverlay finalizado com sucesso.');
    }

    // Expor API pública para o userscript loader
    window.hcalcInitBotao = initializeBotao;
})();
