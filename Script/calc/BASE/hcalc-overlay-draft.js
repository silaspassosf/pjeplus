(function () {
    'use strict';

    function getOverlayDraftKey() {
        const match = window.location.pathname.match(/processo\/([^/]+)/i);
        const processoId = match ? match[1] : window.location.pathname;
        return `hcalc-overlay-draft:${processoId}`;
    }

    function loadRaw(warnFn = console.warn) {
        try {
            const raw = window.localStorage.getItem(getOverlayDraftKey());
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            warnFn('[hcalc]', 'Falha ao carregar rascunho do overlay:', e);
            return null;
        }
    }

    function saveRaw(draft, warnFn = console.warn) {
        try {
            // Evitar crescimento ilimitado: manter no máximo 2 rascunhos por diferentes processos.
            const prefix = 'hcalc-overlay-draft:';
            const currentKey = getOverlayDraftKey();

            try {
                // Coletar chaves existentes com o prefixo
                const existing = [];
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (key && key.indexOf(prefix) === 0) {
                        try {
                            const val = JSON.parse(localStorage.getItem(key));
                            existing.push({ key, savedAt: val && val.savedAt ? new Date(val.savedAt).getTime() : 0 });
                        } catch (e) {
                            // parse error: treat as oldest
                            existing.push({ key, savedAt: 0 });
                        }
                    }
                }

                // If currentKey is new and we already have 2 or more different process drafts,
                // remove the oldest until only 1 remains (so after adding current there will be at most 2).
                const hasCurrent = existing.some(e => e.key === currentKey);
                if (!hasCurrent && existing.length >= 2) {
                    existing.sort((a, b) => a.savedAt - b.savedAt);
                    const toRemove = existing.length - 1; // remove enough to keep room for current
                    for (let j = 0; j < toRemove; j++) {
                        try { localStorage.removeItem(existing[j].key); } catch (e) { /* ignore */ }
                    }
                }
            } catch (e) {
                // If anything fails during eviction, continue to attempt save
                warnFn('[hcalc]', 'Eviction check failed:', e);
            }

            window.localStorage.setItem(currentKey, JSON.stringify(draft));
            try {
                window.dispatchEvent(new CustomEvent('hcalc:draft:changed', { detail: { key: currentKey, action: 'save' } }));
            } catch (e) { /* ignore */ }
        } catch (e) {
            warnFn('[hcalc]', 'Falha ao salvar rascunho do overlay:', e);
        }
    }

    function clearRaw(warnFn = console.warn) {
        try {
            const key = getOverlayDraftKey();
            window.localStorage.removeItem(key);
            try {
                window.dispatchEvent(new CustomEvent('hcalc:draft:changed', { detail: { key, action: 'clear' } }));
            } catch (e) { /* ignore */ }
        } catch (e) {
            warnFn('[hcalc]', 'Falha ao limpar rascunho do overlay:', e);
        }
    }

    function restoreStateOnly(warnFn = console.warn) {
        const draft = loadRaw(warnFn);
        if (!draft?.state || !window.hcalcState) return false;

        window.hcalcState.planilhaExtracaoData = draft.state.planilhaExtracaoData || null;
        window.hcalcState.planilhaCarregada = !!draft.state.planilhaCarregada;
        window.hcalcState.planilhasDisponiveis = draft.state.planilhasDisponiveis || [];
        try {
            console.log('[hcalc][draft] restoreStateOnly: planilhaCarregada=', !!window.hcalcState.planilhaCarregada, 'planilhaExtracaoData=', window.hcalcState.planilhaExtracaoData);
            if (window.hcalcAtualizarResumoPlanilha && window.hcalcState.planilhaExtracaoData) {
                try { window.hcalcAtualizarResumoPlanilha(window.hcalcState.planilhaExtracaoData); } catch (e) { console.warn('[hcalc][draft] atualizarResumoPlanilha falhou', e); }
            }
        } catch (e) {}
        return !!window.hcalcState.planilhaCarregada;
    }

    function createController(deps) {
        const {
            $, modalEl, warn, atualizarResumoPlanilha, adicionarLinhaPeridoDiverso,
            adicionarDepositoRecursal, adicionarPagamentoAntecipado,
            aplicarEstiloRecuperacaoJudicial, atualizarDropdownsPlanilhas,
            updateHighlight
        } = deps;

        let saveDraftTimer = null;
        let restoringDraft = false;

        function queueSave() {
            if (restoringDraft) return;
            clearTimeout(saveDraftTimer);
            saveDraftTimer = setTimeout(save, 150);
        }

        function save() {
            const modal = $('homologacao-modal');
            if (!modal) return;

            const staticFields = {};
            modal.querySelectorAll('input[id], select[id], textarea[id]').forEach((el) => {
                if (!el.id || el.type === 'file' || /^dep-|^pag-|^lib-rem-|^lib-dev-/.test(el.id)) return;
                if (el.type === 'checkbox') {
                    staticFields[el.id] = { type: 'checkbox', checked: el.checked };
                } else if (el.type !== 'radio') {
                    staticFields[el.id] = { type: el.type || el.tagName.toLowerCase(), value: el.value };
                }
            });

            const namedRadios = {};
            modal.querySelectorAll('input[type="radio"][name]:checked').forEach((radio) => {
                namedRadios[radio.name] = radio.value;
            });

            const periodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]')).map((linha) => {
                const idx = linha.id.replace('periodo-diverso-', '');
                return {
                    reclamada: document.querySelector(`.periodo-reclamada[data-idx="${idx}"]`)?.value || '',
                    tipo: 'subsidiaria',
                    periodo: document.querySelector(`.periodo-periodo[data-idx="${idx}"]`)?.value || '',
                    idCalculo: document.querySelector(`.periodo-id[data-idx="${idx}"]`)?.value || '',
                    planilha: document.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`)?.value || 'principal'
                };
            });

            const depositos = window.hcalcState.depositosRecursais
                .filter((dep) => !dep.removed && $(`deposito-item-${dep.idx}`))
                .map((dep) => ({
                    tipo: $(`dep-tipo-${dep.idx}`)?.value || 'bb',
                    depositante: $(`dep-depositante-${dep.idx}`)?.value || '',
                    idGuia: $(`dep-id-${dep.idx}`)?.value || '',
                    principal: !!$(`dep-principal-${dep.idx}`)?.checked,
                    liberacao: document.querySelector(`input[name="rad-dep-lib-${dep.idx}"]:checked`)?.value || 'reclamante'
                }));

            const pagamentos = window.hcalcState.pagamentosAntecipados
                .filter((pag) => !pag.removed && $(`pagamento-item-${pag.idx}`))
                .map((pag) => ({
                    idDeposito: $(`pag-id-${pag.idx}`)?.value || '',
                    tipoLib: document.querySelector(`input[name="lib-tipo-${pag.idx}"]:checked`)?.value || 'nenhum',
                    remValor: $(`lib-rem-valor-${pag.idx}`)?.value || '',
                    remTitulo: $(`lib-rem-titulo-${pag.idx}`)?.value || '',
                    devValor: $(`lib-dev-valor-${pag.idx}`)?.value || ''
                }));

            const intimacoes = Array.from(document.querySelectorAll('.intimacao-row')).map((row) => ({
                nome: row.querySelector('.chk-parte-principal')?.dataset?.nome || '',
                principal: !!row.querySelector('.chk-parte-principal')?.checked,
                modo: row.querySelector('.sel-modo-intimacao')?.value || 'diario'
            }));

            saveRaw({
                version: 1,
                savedAt: new Date().toISOString(),
                state: {
                    planilhaExtracaoData: window.hcalcState.planilhaExtracaoData,
                    planilhaCarregada: window.hcalcState.planilhaCarregada,
                    planilhasDisponiveis: window.hcalcState.planilhasDisponiveis || []
                },
                staticFields,
                namedRadios,
                periodosEnabled: !!$('resp-diversos')?.checked,
                principalResponsavel: $('resp-devedora-principal')?.value || '',
                periodos,
                depositosEnabled: !!$('chk-deposito')?.checked,
                depositos,
                pagamentosEnabled: !!$('chk-pag-antecipado')?.checked,
                pagamentos,
                intimacoes
            }, warn);
        }

        function restore() {
            const draft = loadRaw(warn);
            if (!draft) return false;

            restoringDraft = true;
            try {
                if (draft.state?.planilhaExtracaoData) {
                    window.hcalcState.planilhaExtracaoData = draft.state.planilhaExtracaoData;
                    window.hcalcState.planilhaCarregada = !!draft.state.planilhaCarregada;
                    window.hcalcState.planilhasDisponiveis = draft.state.planilhasDisponiveis || [];
                    atualizarResumoPlanilha(draft.state.planilhaExtracaoData);
                }

                Object.entries(draft.staticFields || {}).forEach(([id, cfg]) => {
                    const el = $(id);
                    if (!el) return;
                    if (cfg.type === 'checkbox') el.checked = !!cfg.checked;
                    else el.value = cfg.value ?? '';
                });

                ['resp-tipo', 'calc-fgts', 'ignorar-inss', 'irpf-tipo', 'chk-hon-reu', 'chk-perito-conh', 'custas-origem'].forEach((id) => {
                    const el = $(id);
                    if (el) el.dispatchEvent(new Event('change', { bubbles: true }));
                });

                if ($('resp-diversos')) {
                    $('resp-diversos').checked = !!draft.periodosEnabled;
                    $('resp-diversos').dispatchEvent(new Event('change', { bubbles: true }));
                }

                if (draft.periodosEnabled && $('resp-devedora-principal')) {
                    $('resp-devedora-principal').value = draft.principalResponsavel || $('resp-devedora-principal').value;
                    $('resp-devedora-principal').dispatchEvent(new Event('change', { bubbles: true }));

                    const container = $('resp-diversos-container');
                    if (container) container.innerHTML = '';
                    (draft.periodos || []).forEach(() => adicionarLinhaPeridoDiverso());

                    (draft.periodos || []).forEach((periodo, idx) => {
                        const selRec = document.querySelector(`.periodo-reclamada[data-idx="${idx}"]`);
                        const inpPeriodo = document.querySelector(`.periodo-periodo[data-idx="${idx}"]`);
                        const inpId = document.querySelector(`.periodo-id[data-idx="${idx}"]`);
                        const selPlanilha = document.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`);

                        if (selRec && periodo.reclamada) {
                            if (!Array.from(selRec.options).some((opt) => opt.value === periodo.reclamada)) {
                                const opt = document.createElement('option');
                                opt.value = periodo.reclamada;
                                opt.textContent = periodo.reclamada;
                                selRec.appendChild(opt);
                            }
                            selRec.value = periodo.reclamada;
                        }
                        if (inpPeriodo) inpPeriodo.value = periodo.periodo || '';
                        if (inpId) inpId.value = periodo.idCalculo || '';
                        if (selPlanilha) selPlanilha.value = periodo.planilha || 'principal';
                    });
                }

                if ($('chk-deposito')) {
                    $('chk-deposito').checked = !!draft.depositosEnabled;
                    $('deposito-campos')?.classList.toggle('hidden', !draft.depositosEnabled);
                }
                if (draft.depositosEnabled) {
                    $('depositos-container').innerHTML = '';
                    window.hcalcState.depositosRecursais = [];
                    window.hcalcState.nextDepositoIdx = 0;
                    (draft.depositos || []).forEach((dep) => {
                        adicionarDepositoRecursal();
                        const idx = window.hcalcState.nextDepositoIdx - 1;
                        if ($(`dep-tipo-${idx}`)) $(`dep-tipo-${idx}`).value = dep.tipo || 'bb';
                        if ($(`dep-depositante-${idx}`)) $(`dep-depositante-${idx}`).value = dep.depositante || '';
                        if ($(`dep-id-${idx}`)) $(`dep-id-${idx}`).value = dep.idGuia || '';
                        if ($(`dep-principal-${idx}`)) $(`dep-principal-${idx}`).checked = dep.principal !== false;
                        const radio = document.querySelector(`input[name="rad-dep-lib-${idx}"][value="${dep.liberacao || 'reclamante'}"]`);
                        if (radio) radio.checked = true;
                        if ($(`dep-tipo-${idx}`)) $(`dep-tipo-${idx}`).dispatchEvent(new Event('change', { bubbles: true }));
                        if ($(`dep-principal-${idx}`)) $(`dep-principal-${idx}`).dispatchEvent(new Event('change', { bubbles: true }));
                    });
                }

                if ($('chk-pag-antecipado')) {
                    $('chk-pag-antecipado').checked = !!draft.pagamentosEnabled;
                    $('pag-antecipado-campos')?.classList.toggle('hidden', !draft.pagamentosEnabled);
                }
                if (draft.pagamentosEnabled) {
                    $('pagamentos-container').innerHTML = '';
                    window.hcalcState.pagamentosAntecipados = [];
                    window.hcalcState.nextPagamentoIdx = 0;
                    (draft.pagamentos || []).forEach((pag) => {
                        adicionarPagamentoAntecipado();
                        const idx = window.hcalcState.nextPagamentoIdx - 1;
                        if ($(`pag-id-${idx}`)) $(`pag-id-${idx}`).value = pag.idDeposito || '';
                        const radio = document.querySelector(`input[name="lib-tipo-${idx}"][value="${pag.tipoLib || 'nenhum'}"]`);
                        if (radio) {
                            radio.checked = true;
                            radio.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        if ($(`lib-rem-valor-${idx}`)) $(`lib-rem-valor-${idx}`).value = pag.remValor || '';
                        if ($(`lib-rem-titulo-${idx}`)) $(`lib-rem-titulo-${idx}`).value = pag.remTitulo || '';
                        if ($(`lib-dev-valor-${idx}`)) $(`lib-dev-valor-${idx}`).value = pag.devValor || '';
                    });
                }

                Object.entries(draft.namedRadios || {}).forEach(([name, value]) => {
                    const radio = document.querySelector(`input[type="radio"][name="${name}"][value="${value}"]`);
                    if (radio) radio.checked = true;
                });

                (draft.intimacoes || []).forEach((item) => {
                    const chk = document.querySelector(`.chk-parte-principal[data-nome="${item.nome}"]`);
                    const sel = document.querySelector(`.sel-modo-intimacao[data-nome="${item.nome}"]`);
                    if (chk) chk.checked = !!item.principal;
                    if (sel) sel.value = item.modo || 'diario';
                });

                aplicarEstiloRecuperacaoJudicial();
                atualizarDropdownsPlanilhas();
                updateHighlight();
                return true;
            } finally {
                restoringDraft = false;
            }
        }

        if (modalEl && !modalEl.dataset.draftBound) {
            modalEl.dataset.draftBound = 'true';
            modalEl.addEventListener('change', () => queueSave(), true);
            modalEl.addEventListener('input', () => queueSave(), true);
        }

        return {
            queueSave,
            save,
            restore,
            clear: () => clearRaw(warn),
            isRestoring: () => restoringDraft
        };
    }

    window.hcalcOverlayDraft = {
        loadRaw,
        saveRaw,
        clearRaw,
        restoreStateOnly,
        createController
    };

    window.hcalcClearOverlayDraft = () => clearRaw(console.warn);
})();