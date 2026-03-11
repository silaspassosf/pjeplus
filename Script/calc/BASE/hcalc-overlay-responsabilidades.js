(function () {
    'use strict';

    function createController(deps) {
        const {
            $,
            queueOverlayDraftSave,
            carregarPDFJSSeNecessario,
            processarPlanilhaPDF
        } = deps;

        function aplicarEstiloRecuperacaoJudicial() {
            // Ler quais reclamadas principais estão com RJ marcada
            const rjMap = new Map();
            document.querySelectorAll('#resp-principais-dinamico-container .resp-item').forEach(item => {
                const isRj = item.querySelector('.chk-rec-judicial-item')?.checked;
                rjMap.set(item.dataset.nome, isRj);
            });

            document.querySelectorAll('.intimacao-row').forEach(row => {
                const checkbox = row.querySelector('.chk-parte-principal');
                if (checkbox && checkbox.checked) {
                    const nomeStr = checkbox.dataset.nome;
                    const temRecJudicial = rjMap.get(nomeStr) || false;

                    const nomeDiv = row.querySelector('div[title]');
                    if (nomeDiv) {
                        if (temRecJudicial) {
                            nomeDiv.style.textDecoration = 'line-through';
                            nomeDiv.style.color = '#999';
                            nomeDiv.title = `${nomeStr} (Em Recuperação Judicial/Falência - sem intimação para pagamento)`;
                        } else {
                            nomeDiv.style.textDecoration = 'none';
                            nomeDiv.style.color = '#333';
                            nomeDiv.title = nomeStr;
                        }
                    }
                }
            });
        }

        function atualizarDropdownsReclamadas() {
            // compat wrapper for older callers
            atualizarDropdownsPlanilhas();
        }

        function registrarPlanilhaDisponivel(id, label, dados) {
            if (!window.hcalcState.planilhasDisponiveis) window.hcalcState.planilhasDisponiveis = [];
            window.hcalcState.planilhasDisponiveis =
                window.hcalcState.planilhasDisponiveis.filter(p => p.id !== id);
            window.hcalcState.planilhasDisponiveis.push({ id, label, dados });
            atualizarDropdownsPlanilhas();
        }

        function atualizarDropdownsPlanilhas() {
            const todasReclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];

            // Principals are now in the dynamic container + timeline checkboxes
            const principaisSet = new Set();
            document.querySelectorAll('.chk-parte-principal:checked').forEach(chk => principaisSet.add(chk.dataset.nome));
            document.querySelectorAll('#resp-principais-dinamico-container .resp-item').forEach(item => principaisSet.add(item.dataset.nome));

            // Integral Subsidiaries
            const subsidiariasIntegraisSelecionadas = new Set();
            document.querySelectorAll('#resp-subsidiarias-integral-dinamico-container .resp-item').forEach(item => subsidiariasIntegraisSelecionadas.add(item.dataset.nome));

            // Diverse Periods
            const diversasSelecionadas = new Set();
            document.querySelectorAll('#resp-diversos-container .periodo-reclamada').forEach(sel => {
                if (sel && sel.selectedOptions) {
                    Array.from(sel.selectedOptions).forEach(opt => { if (opt.value) diversasSelecionadas.add(opt.value); });
                } else if (sel && sel.value) {
                    diversasSelecionadas.add(sel.value);
                }
            });

            const jaUsadas = new Set([...principaisSet, ...subsidiariasIntegraisSelecionadas, ...diversasSelecionadas]);

            // Function to rebuild a single select element
            const rebuildSelect = (selectEl, defaultOptionText, excludedSet) => {
                if (!selectEl) return;
                const current = selectEl.value;
                selectEl.innerHTML = `<option value="">${defaultOptionText}</option>`;
                todasReclamadas.forEach(rec => {
                    if (!excludedSet.has(rec) || current === rec) {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        if (current === rec) opt.selected = true;
                        selectEl.appendChild(opt);
                    }
                });
            };

            // Rebuild the "add" dropdowns
            rebuildSelect($('sel-add-principal'), 'Adicionar devedora principal...', jaUsadas);
            rebuildSelect($('sel-add-subs-int'), 'Adicionar subsidiária integral...', jaUsadas);

            // Rebuild "diversas" multiselects
            document.querySelectorAll('#resp-diversos-container .periodo-reclamada').forEach(select => {
                const currentSelected = Array.from(select.selectedOptions).map(o => o.value);
                select.innerHTML = '';
                todasReclamadas.forEach(rec => {
                    const opt = document.createElement('option');
                    opt.value = rec;
                    opt.textContent = rec;
                    if (currentSelected.includes(rec)) opt.selected = true;
                    // Disable instead of hide for multi-selects to keep visibility consistent
                    if (!opt.selected && jaUsadas.has(rec)) opt.disabled = true;
                    select.appendChild(opt);
                });
            });
        }

        function adicionarItemLista(containerId, nome, isPrincipal = false) {
            const container = $(containerId);
            if (!container) return;

            // Check if already exists
            const existing = Array.from(container.querySelectorAll('.resp-item')).find(el => el.dataset.nome === nome);
            if (existing) return;

            const div = document.createElement('div');
            div.className = 'resp-item row';
            div.dataset.nome = nome;
            div.style.cssText = 'display:flex; align-items:center; justify-content:space-between; padding:6px; background:#f9fafb; border:1px solid #e5e7eb; border-radius:4px;';

            const txtColor = isPrincipal ? '#b45309' : '#0284c7';

            let extraHtml = '';
            if (isPrincipal) {
                // For principals, add "Recuperação Judicial" checkbox specific to this company
                extraHtml = `<label style="font-size:11px; margin-left:10px; display:flex; align-items:center; gap:4px; color:#6b7280; white-space:nowrap;"><input type="checkbox" class="chk-rec-judicial-item" data-nome="${nome}"> Rec. Jud/Falência</label>`;
            }

            div.innerHTML = `
                <div style="display:flex; align-items:center; flex:1; overflow:hidden;">
                    <span style="font-weight:600; font-size:12px; color:${txtColor}; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="${nome}">${nome}</span>
                    ${extraHtml}
                </div>
                <button type="button" class="btn-action btn-remover-item" style="background:#ef4444; padding:2px 6px; font-size:10px; margin-left:8px;">❌ Rem</button>
            `;

            div.querySelector('.btn-remover-item').onclick = () => {
                div.remove();
                atualizarDropdownsPlanilhas();
                if (typeof queueOverlayDraftSave === 'function') queueOverlayDraftSave();
            };

            const chkRj = div.querySelector('.chk-rec-judicial-item');
            if (chkRj) {
                chkRj.addEventListener('change', () => {
                    aplicarEstiloRecuperacaoJudicial();
                    if (typeof queueOverlayDraftSave === 'function') queueOverlayDraftSave();
                });
            }

            container.appendChild(div);
            atualizarDropdownsPlanilhas();
        }

        function adicionarLinhaPeridoDiverso() {
            const container = $('resp-diversos-container');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const principalIntegral = $('resp-devedora-principal')?.value || '';
            const idx = container.children.length;
            const rowId = `periodo-diverso-${idx}`;
            const numeroDevedora = idx + 2;

            const div = document.createElement('div');
            div.id = rowId;
            div.className = 'row';
            div.style.marginBottom = '15px';
            div.style.padding = '12px';
            div.style.backgroundColor = '#f5f5f5';
            div.style.borderRadius = '4px';

            const jaUsadas = new Set();
            document.querySelectorAll('.chk-parte-principal:checked').forEach(chk => jaUsadas.add(chk.dataset.nome));
            document.querySelectorAll('#resp-principais-dinamico-container .resp-item').forEach(item => jaUsadas.add(item.dataset.nome));
            document.querySelectorAll('#resp-subsidiarias-integral-dinamico-container .resp-item').forEach(item => jaUsadas.add(item.dataset.nome));

            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                if (select && select.selectedOptions) Array.from(select.selectedOptions).forEach(o => { if (o.value) jaUsadas.add(o.value); });
                else if (select && select.value) jaUsadas.add(select.value);
            });

            let selectOptions = '<option value="">Selecione a reclamada...</option>';
            reclamadas.forEach(rec => {
                if (!jaUsadas.has(rec)) {
                    selectOptions += `<option value="${rec}">${rec}</option>`;
                }
            });

            div.innerHTML = `
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Devedoras (selecione todas que pertencem a este período)</label>
                    <select multiple size="4" class="periodo-reclamada" data-idx="${idx}" style="width: 100%; padding: 8px;">
                        ${selectOptions}
                    </select>
                </div>
                    
                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <label>Período (vazio = integral)</label>
                        <input type="text" class="periodo-periodo" data-idx="${idx}" placeholder="Deixe vazio para período integral" style="width: 100%; padding: 8px;">
                    </div>
                    <div style="flex: 1;">
                        <label>ID Cálculo Separado</label>
                        <input type="text" class="periodo-id" data-idx="${idx}" placeholder="ID #XXXX" style="width: 100%; padding: 8px;">
                    </div>
                </div>
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold; font-size: 12px;">Planilha desta Devedora</label>
                    <div style="display: flex; gap: 8px; align-items: center; margin-top: 4px;">
                        <select class="periodo-planilha-select" data-idx="${idx}"
                                style="flex: 1; padding: 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="principal">📋 Mesma planilha principal</option>
                        </select>
                        <button type="button" class="btn-carregar-planilha-extra btn-action"
                                data-idx="${idx}"
                                style="font-size: 11px; padding: 6px 10px; white-space: nowrap; background: #7c3aed;">
                            📄 Carregar Nova
                        </button>
                        <input type="file" class="input-planilha-extra-pdf" data-idx="${idx}"
                               accept=".pdf" style="display: none;">
                    </div>
                </div>
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
                    <label><input type="checkbox" class="periodo-total" data-idx="${idx}"> Período Total</label>
                    <button type="button" class="btn-remover-periodo btn-action" data-idx="${idx}" data-row-id="${rowId}" style="padding: 8px; margin-left: auto; background: #d32f2f;">Remover</button>
                </div>
            `;
            container.appendChild(div);

            const btnRemover = div.querySelector(`.btn-remover-periodo[data-idx="${idx}"]`);
            btnRemover.onclick = () => {
                document.getElementById(rowId).remove();
                atualizarDropdownsReclamadas();
                queueOverlayDraftSave();
            };

            const periodoInput = div.querySelector(`.periodo-periodo[data-idx="${idx}"]`);
            const idInput = div.querySelector(`.periodo-id[data-idx="${idx}"]`);

            if (window.hcalcState.planilhaExtracaoData) {
                const pd = window.hcalcState.planilhaExtracaoData;
                if (periodoInput && pd.periodoCalculo) periodoInput.value = pd.periodoCalculo;
                if (idInput && pd.idPlanilha) idInput.value = pd.idPlanilha;
            }

            const selectReclamada = div.querySelector(`.periodo-reclamada[data-idx="${idx}"]`);
            selectReclamada.onchange = () => {
                atualizarDropdownsReclamadas();
            };

            const selectPlanilha = div.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`);
            atualizarDropdownsPlanilhas();

            selectPlanilha.onchange = (e) => {
                const val = e.target.value;
                const pd = val === 'principal'
                    ? window.hcalcState.planilhaExtracaoData
                    : (window.hcalcState.planilhasDisponiveis || []).find(p => p.id === val)?.dados;
                if (!pd) return;
                if (pd.idPlanilha && idInput) idInput.value = pd.idPlanilha;
                if (pd.periodoCalculo && periodoInput) periodoInput.value = pd.periodoCalculo;
            };

            const btnCarregar = div.querySelector(`.btn-carregar-planilha-extra[data-idx="${idx}"]`);
            const inputExtra = div.querySelector(`.input-planilha-extra-pdf[data-idx="${idx}"]`);

            btnCarregar.onclick = () => inputExtra.click();

            inputExtra.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                inputExtra.value = '';

                const originalText = btnCarregar.textContent;
                btnCarregar.textContent = '⏳...';
                btnCarregar.disabled = true;

                try {
                    const loaded = await carregarPDFJSSeNecessario();
                    if (!loaded) throw new Error('PDF.js não disponível');

                    const dados = await processarPlanilhaPDF(file);
                    if (!dados.sucesso) throw new Error(dados.erro || 'Erro desconhecido');

                    if (dados.idPlanilha && idInput) idInput.value = dados.idPlanilha;
                    if (dados.periodoCalculo && periodoInput) periodoInput.value = dados.periodoCalculo;

                    const extraId = `extra_${idx}`;
                    const extraLabel = `${dados.idPlanilha || 'Extra'} (Dev.${idx + 2})`;
                    registrarPlanilhaDisponivel(extraId, extraLabel, dados);

                    selectPlanilha.value = extraId;

                    btnCarregar.textContent = '✓ Analisada';
                    btnCarregar.style.background = '#10b981';
                    btnCarregar.disabled = false;
                    queueOverlayDraftSave();
                } catch (err) {
                    alert('Erro ao processar planilha: ' + err.message);
                    btnCarregar.textContent = originalText;
                    btnCarregar.disabled = false;
                }
            };
        }

        function initEventHandlers() {
            const respSubs = document.getElementById('resp-subsidiarias');
            const respSol = document.getElementById('resp-solidarias');

            const updateRespOptions = () => {
                const isSubs = respSubs && respSubs.checked;
                // Mostrar opcoes adicionais para subsidiarias
                $('resp-sub-opcoes').classList.toggle('hidden', !isSubs);

                // Atualizar visibilidade dos depósitos principais
                window.hcalcState.depositosRecursais.forEach(d => {
                    if (!d.removed && typeof window.hcalcAtualizarVisibilidadeDepositoPrincipal === 'function') {
                        window.hcalcAtualizarVisibilidadeDepositoPrincipal(d.idx);
                    }
                });
            };

            const radRespIntegral = $('resp-integral');
            const radRespDiversos = $('resp-diversos');

            const handleRadiosRespTipo = () => {
                const fieldset = $('resp-diversos-fieldset');
                if (radRespDiversos && radRespDiversos.checked) {
                    fieldset.classList.remove('hidden');

                    // Auto-add first reclamada as principal if none exists
                    const containerPrincipais = $('resp-principais-dinamico-container');
                    if (containerPrincipais && containerPrincipais.children.length === 0) {
                        const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
                        if (reclamadas.length > 0) {
                            adicionarItemLista('resp-principais-dinamico-container', reclamadas[0], true);
                        }
                    }
                } else {
                    fieldset.classList.add('hidden');
                }
            };

            if (radRespIntegral) radRespIntegral.addEventListener('change', handleRadiosRespTipo);
            if (radRespDiversos) radRespDiversos.addEventListener('change', handleRadiosRespTipo);

            if ($('btn-add-principal')) {
                $('btn-add-principal').onclick = () => {
                    const sel = $('sel-add-principal');
                    if (sel.value) {
                        adicionarItemLista('resp-principais-dinamico-container', sel.value, true);
                        sel.value = '';
                    }
                };
            }

            if ($('btn-add-subs-int')) {
                $('btn-add-subs-int').onclick = () => {
                    const sel = $('sel-add-subs-int');
                    if (sel.value) {
                        adicionarItemLista('resp-subsidiarias-integral-dinamico-container', sel.value, false);
                        sel.value = '';
                    }
                };
            }

            if ($('chk-nao-ha-subs-int')) {
                $('chk-nao-ha-subs-int').onchange = (e) => {
                    const checked = e.target.checked;
                    const divAdd = $('div-add-subs-int');
                    if (divAdd) {
                        divAdd.style.opacity = checked ? '0.5' : '1';
                        divAdd.style.pointerEvents = checked ? 'none' : 'auto';
                    }
                    if (checked) {
                        $('resp-subsidiarias-integral-dinamico-container').innerHTML = '';
                        atualizarDropdownsPlanilhas();
                    }
                };
            }

            $('btn-adicionar-periodo').onclick = (e) => {
                e.preventDefault();
                adicionarLinhaPeridoDiverso();
                queueOverlayDraftSave();
            };
        }

        return {
            initEventHandlers,
            aplicarEstiloRecuperacaoJudicial,
            atualizarDropdownsPlanilhas,
            adicionarLinhaPeridoDiverso
        };
    }

    function createTextApi(deps) {
        const { $, bold } = deps;

        function formatarLista(nomes) {
            if (nomes.length === 0) return '';
            if (nomes.length === 1) return bold(nomes[0]);
            if (nomes.length === 2) return `${bold(nomes[0])} e ${bold(nomes[1])}`;
            const ultimos = nomes.slice(-2);
            const anteriores = nomes.slice(0, -2);
            return `${anteriores.map(n => bold(n)).join(', ')}, ${bold(ultimos[0])} e ${bold(ultimos[1])}`;
        }

        function gerarTextoResponsabilidades() {
            const linhasPeriodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]'));
            if (linhasPeriodos.length === 0) return null;

            const isDiversos = document.getElementById('resp-diversos')?.checked;

            const periodoCompleto = window.hcalcState.planilhaExtracaoData?.periodoCalculo || '';
            const principaisSelecionadas = Array.from(document.querySelectorAll('.chk-parte-principal:checked')).map(chk => chk.dataset.nome).filter(Boolean);
            const principaisParciais = [];
            const subsidiariasComPeriodo = [];

            // Adicionar principais adicionais do bloco dinamico
            if (isDiversos) {
                document.querySelectorAll('#resp-principais-dinamico-container .resp-item').forEach(item => {
                    const nome = item.dataset.nome;
                    if (!principaisSelecionadas.includes(nome)) principaisSelecionadas.push(nome);
                });
            }

            linhasPeriodos.forEach((linha) => {
                const idx = linha.id.replace('periodo-diverso-', '');
                const selectEl = document.querySelector(`.periodo-reclamada[data-idx="${idx}"]`);
                const nomesRec = selectEl ? Array.from(selectEl.selectedOptions).map(o => o.value).filter(Boolean) : [];
                const periodoTexto = document.querySelector(`.periodo-periodo[data-idx="${idx}"]`)?.value || '';
                const idPlanilhaManual = document.querySelector(`.periodo-id[data-idx="${idx}"]`)?.value || '';

                const planilhaSel = document.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`)?.value || 'principal';
                const usarMesmaPlanilha = planilhaSel === 'principal';
                const idPlanilhaFinal = usarMesmaPlanilha ? '' : (planilhaSel || idPlanilhaManual);
                const periodoTotalCheckbox = document.querySelector(`.periodo-total[data-idx="${idx}"]`);
                let isPeriodoIntegral = !periodoTexto || periodoTexto === periodoCompleto;
                if (periodoTotalCheckbox && periodoTotalCheckbox.checked) isPeriodoIntegral = true;
                if (!usarMesmaPlanilha) isPeriodoIntegral = false;

                nomesRec.forEach((nomeRec) => {
                    if (nomeRec && !isPeriodoIntegral) {
                        subsidiariasComPeriodo.push({ nome: nomeRec, periodo: periodoTexto, idPlanilha: idPlanilhaFinal, usarMesmaPlanilha });
                    }
                });
            });

            const todasReclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const principaisNomes = new Set([...principaisSelecionadas]);
            const subsidiariasComPeriodoNomes = new Set(subsidiariasComPeriodo.map(s => s.nome));

            let subsidiariasIntegrais = [];

            if (isDiversos) {
                const naoHaSubsInt = document.getElementById('chk-nao-ha-subs-int')?.checked;
                if (!naoHaSubsInt) {
                    // Extract from the integral dynamic block
                    document.querySelectorAll('#resp-subsidiarias-integral-dinamico-container .resp-item').forEach(item => {
                        subsidiariasIntegrais.push(item.dataset.nome);
                    });
                }
            } else {
                // Modo "Todas pelo período integral": todas as reclamadas menos as principais são subsidiárias integrais
                subsidiariasIntegrais = todasReclamadas.filter(nome => !principaisNomes.has(nome));
            }

            const nomesPrincipaisUnicos = Array.from(new Set(principaisSelecionadas.filter(n => n)));
            const txtPrincipais = formatarLista(nomesPrincipaisUnicos);

            const subsInt = subsidiariasIntegrais || [];
            const subsDiv = subsidiariasComPeriodo || [];

            const paragrafos = [];

            if (nomesPrincipaisUnicos.length > 0) {
                paragrafos.push(`<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">São devedoras principais/solidárias: ${txtPrincipais}. Portanto, apenas estas respondem pelo montante neste ato.</p>`);
            }

            if (subsInt.length > 0) {
                const txtSubsInt = formatarLista(subsInt);
                paragrafos.push(`<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">São devedoras subsidiárias pelo período integral do contrato: ${txtSubsInt}.</p>`);
            }

            if (subsDiv.length > 0) {
                const txtSubsDiv = formatarLista(subsDiv.map(s => s.nome || s));
                paragrafos.push(`<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">São devedoras subsidiárias por período parcial do contrato: ${txtSubsDiv} — serão tratadas em item próprio a seguir.</p>`);
            }

            const textoIntro = paragrafos.join('');

            return {
                textoIntro,
                principalIntegral: nomesPrincipaisUnicos[0] || '',
                principaisParciais,
                subsidiariasIntegrais,
                subsidiariasComPeriodo,
                todasPrincipais: [
                    ...nomesPrincipaisUnicos.map(n => ({ nome: n, periodo: 'integral', idPlanilha: '' })),
                    ...principaisParciais
                ]
            };
        }

        return {
            formatarLista,
            gerarTextoResponsabilidades
        };
    }

    window.hcalcOverlayResponsabilidades = { createController, createTextApi };
})();