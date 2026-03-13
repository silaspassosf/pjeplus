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
            const passivo = window.hcalcPartesData?.passivo?.length || 0;
            const recJudicialUnica = passivo === 1 && document.getElementById('resp-rec-judicial-unica')?.checked;
            document.querySelectorAll('.intimacao-row').forEach(row => {
                const checkbox = row.querySelector('.chk-parte-principal');
                const nomeDiv = row.querySelector('div[title]');
                if (!checkbox || !nomeDiv) return;
                const nome = checkbox.dataset.nome;
                const recChkPrincipal = document.querySelector(`#resp-principais-dinamico-container .principal-item[data-nome="${CSS.escape(nome)}"] .chk-principal-rec`);
                const recChkSubsInt = document.querySelector(`#resp-subsidiarias-integral-dinamico-container .subs-item[data-nome="${CSS.escape(nome)}"] .chk-subs-int-rec`);
                const temRecJudicial = (recChkPrincipal && recChkPrincipal.checked) || (recChkSubsInt && recChkSubsInt.checked) || recJudicialUnica;
                if (temRecJudicial) {
                    nomeDiv.style.textDecoration = 'line-through';
                    nomeDiv.style.color = '#999';
                    nomeDiv.title = `${nome} (Em Recuperação Judicial/Falência - sem intimação para pagamento)`;
                } else {
                    nomeDiv.style.textDecoration = 'none';
                    nomeDiv.style.color = '#333';
                    nomeDiv.title = nome;
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

            // Principais podem vir do bloco de principais dinâmico (não ler checkboxes de Intimações)
            const principaisSet = new Set();
            document.querySelectorAll('#resp-principais-dinamico-container .chk-principal:checked').forEach(chk => principaisSet.add(chk.dataset.nome));

            // Subsidiarias integrais marcadas também contam como usadas (não aparecerão nas listas)
            const subsidiariasIntegraisSelecionadas = new Set();
            document.querySelectorAll('#resp-subsidiarias-integral-dinamico-container .chk-subs-int:checked').forEach(chk => subsidiariasIntegraisSelecionadas.add(chk.dataset.nome));

            // Reclamadas já escolhidas nos blocos diversos (lendo a nova lista de divs)
            const jaUsadas = new Set([...principaisSet, ...subsidiariasIntegraisSelecionadas]);
            document.querySelectorAll('.periodo-reclamadas-list .reclamada-item').forEach(item => {
                if (item.dataset.nome) jaUsadas.add(item.dataset.nome);
            });

            // Atualiza os dropdowns de Quick Add (.periodo-reclamada-select)
            document.querySelectorAll('.periodo-reclamada-select').forEach(select => {
                select.innerHTML = '<option value="">Selecione a reclamada...</option>';
                todasReclamadas.forEach(rec => {
                    if (!jaUsadas.has(rec)) {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        select.appendChild(opt);
                    }
                });
            });

            // Also update quick-add selects for principais and subsidiarias integrais
            const selAddPrincipal = document.getElementById('sel-add-principal');
            const selAddSubsInt = document.getElementById('sel-add-subs-int');
            const used = new Set(jaUsadas);

            if (selAddPrincipal) {
                const cur = selAddPrincipal.value || '';
                selAddPrincipal.innerHTML = '<option value="">Adicionar devedora principal...</option>';
                todasReclamadas.forEach(rec => {
                    if (!used.has(rec) || rec === cur) {
                        const o = document.createElement('option'); o.value = rec; o.textContent = rec; selAddPrincipal.appendChild(o);
                    }
                });
            }

            if (selAddSubsInt) {
                const cur2 = selAddSubsInt.value || '';
                selAddSubsInt.innerHTML = '<option value="">Adicionar subsidiária integral...</option>';
                todasReclamadas.forEach(rec => {
                    if (!used.has(rec) || rec === cur2) {
                        const o = document.createElement('option'); o.value = rec; o.textContent = rec; selAddSubsInt.appendChild(o);
                    }
                });
            }
        }

        function adicionarLinhaPeridoDiverso(tipo = 'sub') {
            const isSol = tipo === 'sol';
            const containerId = isSol ? 'resp-sol-diversos-container' : 'resp-sub-diversos-container';
            const container = $(containerId);
            if (!container) return;

            const idx = Date.now(); // use timestamp as unique ID to prevent clashes
            const rowId = `periodo-diverso-${tipo}-${idx}`;
            
            const div = document.createElement('div');
            div.id = rowId;
            div.className = `periodo-linha periodo-${tipo}`;
            div.style.padding = '8px';
            div.style.border = '1px solid #e5e7eb';
            div.style.borderRadius = '5px';
            div.style.background = '#fff';

            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const jaUsadas = new Set();
            // Marcar como usadas as reclamadas marcadas como principais e solidárias integrais
            document.querySelectorAll('#resp-principais-dinamico-container .chk-principal:checked').forEach(chk => jaUsadas.add(chk.dataset.nome));
            document.querySelectorAll('#resp-solidarias-integral-dinamico-container .chk-sol-int:checked').forEach(chk => jaUsadas.add(chk.dataset.nome));
            document.querySelectorAll('#resp-subsidiarias-integral-dinamico-container .chk-subs-int:checked').forEach(chk => jaUsadas.add(chk.dataset.nome));
            
            // Marcar as já escolhidas em outros periodos
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

            const lblReclamada = isSol ? 'Reclamadas Solidárias' : 'Reclamadas Subsidiárias';

            const num = container.querySelectorAll('.periodo-linha').length + 1;

            div.innerHTML = `
                <div style="display: flex; align-items: center; margin-bottom: 10px; gap: 8px;">
                    <span class="periodo-title" style="font-weight: bold; font-size: 13px; color: ${isSol ? '#d97706' : '#334155'};">Período Diverso #${num}</span>
                    <button type="button" class="btn-carregar-planilha-extra btn-action" data-idx="${idx}" style="font-size: 11px; padding: 4px 10px; background: #0ea5e9;">📄 Carregar planilha do período</button>
                    <input type="file" class="input-planilha-extra-pdf" data-idx="${idx}" accept=".pdf" style="display: none;">
                    <button type="button" class="btn-remover-periodo" data-idx="${idx}" data-row-id="${rowId}" style="margin-left: auto; background: transparent; border: none; color: #ef4444; font-weight: bold; cursor: pointer; font-size: 14px;" title="Remover Período">✖</button>
                </div>
                
                <div style="display: flex; gap: 10px; margin-bottom: 12px; background: #f9fafb; padding: 8px; border: 1px solid #e5e7eb; border-radius: 4px;">
                    <div style="flex: 1;">
                        <label style="font-size: 11px; color: #6b7280; margin-bottom: 2px; display: block;">ID da Planilha</label>
                        <input type="text" class="periodo-id" data-idx="${idx}" placeholder="Automático ao analisar PDF" style="width: 100%; border: none; background: transparent; font-weight: bold; color: #111827; padding: 0;" readonly>
                    </div>
                    <div style="flex: 1;">
                        <label style="font-size: 11px; color: #6b7280; margin-bottom: 2px; display: block;">Período Apurado</label>
                        <input type="text" class="periodo-periodo" data-idx="${idx}" placeholder="Automático ao analisar PDF" style="width: 100%; border: none; background: transparent; font-weight: bold; color: #111827; padding: 0;" readonly>
                    </div>
                </div>

                <div style="margin-bottom: 4px;">
                    <div class="periodo-reclamadas-list" data-idx="${idx}" style="display:flex; flex-direction:column; gap:4px; margin-bottom:6px;"></div>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <select class="periodo-reclamada-select" data-idx="${idx}" style="flex: 1; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px;">
                            <option value="">Selecione a reclamada...</option>
                        </select>
                        <button type="button" class="btn-add-reclamada-periodo btn-action" data-idx="${idx}" style="padding: 6px 12px; font-size: 12px; background: #10b981;">Adicionar reclamada neste período</button>
                    </div>
                </div>
            `;
            container.appendChild(div);

            const btnRemover = div.querySelector(`.btn-remover-periodo[data-idx="${idx}"]`);
            btnRemover.onclick = () => {
                document.getElementById(rowId).remove();
                // Renumerar planilhas
                container.querySelectorAll('.periodo-linha').forEach((linha, i) => {
                    linha.querySelector('.periodo-title').textContent = `Período Diverso #${i + 1}`;
                });
                atualizarDropdownsPlanilhas();
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
                queueOverlayDraftSave();
            };

            const selectPlanilha = div.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`);
            atualizarDropdownsPlanilhas();

            // Lista visual de reclamadas para este período e botão de adicionar
            const listContainer = div.querySelector(`.periodo-reclamadas-list[data-idx="${idx}"]`);
            const selectReclamada = div.querySelector(`.periodo-reclamada-select[data-idx="${idx}"]`);
            if (selectReclamada) selectReclamada.innerHTML = `${selectOptions}`;
            const btnAddReclamada = div.querySelector(`.btn-add-reclamada-periodo[data-idx="${idx}"]`);
            if (btnAddReclamada) {
                btnAddReclamada.onclick = () => {
                    const nome = selectReclamada.value;
                    if (!nome) return;
                    // avoid duplicates in this period
                    if (Array.from(listContainer.querySelectorAll('.reclamada-item')).some(it => it.dataset.nome === nome)) return;
                    const item = document.createElement('div');
                    item.className = 'reclamada-item';
                    item.dataset.nome = nome;
                    item.style.display = 'flex';
                    item.style.justifyContent = 'space-between';
                    item.style.alignItems = 'center';
                    item.style.padding = '4px 6px';
                    item.style.borderRadius = '4px';
                    item.innerHTML = `<span>${nome}</span><button type="button" class="btn-remove-reclamada" style="background:transparent;border:none;color:#ef4444;font-weight:bold;cursor:pointer;">✖</button>`;
                    listContainer.appendChild(item);
                    const rem = item.querySelector('.btn-remove-reclamada');
                    rem.onclick = () => { item.remove(); atualizarDropdownsReclamadas(); queueOverlayDraftSave(); };
                    atualizarDropdownsReclamadas();
                    queueOverlayDraftSave();
                };
            }

            selectPlanilha.onchange = (e) => {
                const val = e.target.value;
                const pd = val === 'principal'
                    ? window.hcalcState.planilhaExtracaoData
                    : (window.hcalcState.planilhasDisponiveis || []).find(p => p.id === val)?.dados;
                if (!pd) return;
                if (pd.idPlanilha && idInput) idInput.value = pd.idPlanilha;
                if (pd.periodoCalculo && periodoInput) periodoInput.value = pd.periodoCalculo;
                queueOverlayDraftSave();
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
                    const extraLabel = `${dados.idPlanilha || 'Extra'} (${isSol ? 'Sol' : 'Sub'})`;
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

        // Definidas no escopo do controller para serem acessíveis externamente (Drafts)
        function addPrincipal(nome) {
            const principaisContainer = document.getElementById('resp-principais-dinamico-container');
            if (!nome || !principaisContainer) return;
            // avoid duplicates
            if (principaisContainer.querySelector(`.principal-item[data-nome="${CSS.escape(nome)}"]`)) return;
            const div = document.createElement('div');
            div.className = 'principal-item';
            div.dataset.nome = nome;
            div.style.display = 'flex';
            div.style.alignItems = 'center';
            div.style.gap = '8px';
            
            const isFirst = principaisContainer.children.length === 0;
            const removeStyle = isFirst ? 'display:none;' : 'background:#d32f2f;padding:4px 8px;';

            div.innerHTML = `<label style="flex:1; display:flex; gap:8px; align-items:center;"><input type="checkbox" class="chk-principal" data-nome="${nome}"> <span>${nome}</span></label><label style="font-size:11px;"><input type="checkbox" class="chk-principal-rec"> Rec. Judicial/Falência</label><button type="button" class="btn-remove-principal btn-action" style="${removeStyle}">Remover</button>`;
            principaisContainer.appendChild(div);
            // Se for o primeiro item, marcar automaticamente como principal
            try {
                const chk = div.querySelector('.chk-principal');
                if (chk && isFirst) {
                    chk.checked = true;
                    // garantir que dropdowns e estilos reflitam a seleção
                    if (typeof atualizarDropdownsPlanilhas === 'function') atualizarDropdownsPlanilhas();
                }
            } catch (e) { /* ignore */ }
            const removeBtn = div.querySelector('.btn-remove-principal');
            removeBtn.onclick = () => { div.remove(); atualizarDropdownsPlanilhas(); queueOverlayDraftSave(); };
            // update dropdowns
            atualizarDropdownsPlanilhas();
            queueOverlayDraftSave();
        }

        function addSubsInt(nome) {
            const subsIntContainer = document.getElementById('resp-subsidiarias-integral-dinamico-container');
            if (!nome || !subsIntContainer) return;
            if (subsIntContainer.querySelector(`.subs-item[data-nome="${CSS.escape(nome)}"]`)) return;
            const div = document.createElement('div');
            div.className = 'subs-item';
            div.dataset.nome = nome;
            div.style.display = 'flex';
            div.style.alignItems = 'center';
            div.style.gap = '8px';
            div.innerHTML = `<label style="flex:1; display:flex; gap:8px; align-items:center;"><input type="checkbox" class="chk-subs-int" data-nome="${nome}"> <span>${nome}</span><span class="subs-principal-badge" style="display:none;font-size:10px;color:#b45309;margin-left:4px;">Principal</span></label><label style="font-size:11px;"><input type="checkbox" class="chk-subs-int-rec"> Rec. Judicial/Falência</label><button type="button" class="btn-remove-subs btn-action" style="background:#d32f2f;padding:4px 8px;">Remover</button>`;
            subsIntContainer.appendChild(div);
            const removeBtn = div.querySelector('.btn-remove-subs');
            removeBtn.onclick = () => { 
                div.remove(); 
                // Função local para atualizar os badges
                const container = document.getElementById('resp-subsidiarias-integral-dinamico-container');
                if (container) {
                    container.querySelectorAll('.subs-item').forEach((el, i) => {
                        const badge = el.querySelector('.subs-principal-badge');
                        if (badge) badge.style.display = i === 0 ? '' : 'none';
                    });
                }
                atualizarDropdownsPlanilhas(); 
                queueOverlayDraftSave(); 
            };
            
            // Atualizar os badges diretamente após adicionar
            subsIntContainer.querySelectorAll('.subs-item').forEach((el, i) => {
                const badge = el.querySelector('.subs-principal-badge');
                if (badge) badge.style.display = i === 0 ? '' : 'none';
            });
            
            atualizarDropdownsPlanilhas();
            queueOverlayDraftSave();
        }

        function addSolInt(nome) {
            const container = document.getElementById('resp-solidarias-integral-dinamico-container');
            if (!nome || !container) return;
            if (container.querySelector(`.sol-item[data-nome="${CSS.escape(nome)}"]`)) return;
            const div = document.createElement('div');
            div.className = 'sol-item';
            div.dataset.nome = nome;
            div.style.display = 'flex';
            div.style.alignItems = 'center';
            div.style.gap = '8px';
            div.innerHTML = `<label style="flex:1; display:flex; gap:8px; align-items:center;"><input type="checkbox" class="chk-sol-int" data-nome="${nome}"> <span>${nome}</span></label><label style="font-size:11px;"><input type="checkbox" class="chk-sol-int-rec"> Rec. Judicial/Falência</label><button type="button" class="btn-remove-sol btn-action" style="background:#d32f2f;padding:4px 8px;">Remover</button>`;
            container.appendChild(div);
            const removeBtn = div.querySelector('.btn-remove-sol');
            removeBtn.onclick = () => { div.remove(); atualizarDropdownsPlanilhas(); queueOverlayDraftSave(); };
            atualizarDropdownsPlanilhas();
            queueOverlayDraftSave();
        }

        function initEventHandlers() {
            const respSubs = document.getElementById('resp-subsidiarias');
            const respSol = document.getElementById('resp-solidarias');

            const radSubInt = document.getElementById('resp-sub-integral');
            const radSubDiv = document.getElementById('resp-sub-diversos');
            const radSolInt = document.getElementById('resp-sol-integral');
            const radSolDiv = document.getElementById('resp-sol-diversos');

            const updateVisibility = () => {
                const isSubs = respSubs && respSubs.checked;
                const isSol = respSol && respSol.checked;

                const subDiv = radSubDiv && radSubDiv.checked;
                const solDiv = radSolDiv && radSolDiv.checked;

                const subInt = radSubInt && radSubInt.checked;
                const solInt = radSolInt && radSolInt.checked;

                // Sub-options appear if main checkbox is checked
                const subOpcoes = document.getElementById('resp-sub-opcoes');
                if (subOpcoes) subOpcoes.classList.toggle('hidden', !isSubs);

                const solOpcoes = document.getElementById('resp-sol-opcoes');
                if (solOpcoes) solOpcoes.classList.toggle('hidden', !isSol);

                // Lower UI blocks
                const fsSubInt = document.getElementById('resp-subsidiarias-integral-fieldset');
                if (fsSubInt) fsSubInt.classList.toggle('hidden', !(isSubs && subInt));

                const fsSubDiv = document.getElementById('resp-subsidiarias-diversos-fieldset');
                if (fsSubDiv) fsSubDiv.classList.toggle('hidden', !(isSubs && subDiv));
                
                const fsSolInt = document.getElementById('resp-solidarias-integral-fieldset');
                if (fsSolInt) fsSolInt.classList.toggle('hidden', !(isSol && solInt));

                const fsSolDiv = document.getElementById('resp-solidarias-diversos-fieldset');
                if (fsSolDiv) fsSolDiv.classList.toggle('hidden', !(isSol && solDiv));

                // When an area is hidden, clear its dynamic container so values don't remain hidden
                const subsIntDyn = document.getElementById('resp-subsidiarias-integral-dinamico-container');
                if (!(isSubs && subInt) && subsIntDyn) subsIntDyn.innerHTML = '';
                const solIntDyn = document.getElementById('resp-solidarias-integral-dinamico-container');
                if (!(isSol && solInt) && solIntDyn) solIntDyn.innerHTML = '';

                // Auto-add first row if empty and newly shown
                const subContainer = document.getElementById('resp-sub-diversos-container');
                if (isSubs && subDiv && subContainer && subContainer.children.length === 0) {
                    adicionarLinhaPeridoDiverso('sub');
                }
                const solContainer = document.getElementById('resp-sol-diversos-container');
                if (isSol && solDiv && solContainer && solContainer.children.length === 0) {
                    adicionarLinhaPeridoDiverso('sol');
                }

                // Clean up hidden containers so their values don't leak into generation text
                if (!(isSubs && subDiv) && subContainer) subContainer.innerHTML = '';
                if (!(isSol && solDiv) && solContainer) solContainer.innerHTML = '';

                // Call existing depósitos update
                if (window.hcalcState && window.hcalcState.depositosRecursais) {
                    window.hcalcState.depositosRecursais.forEach(d => {
                        if (!d.removed && typeof window.hcalcAtualizarVisibilidadeDepositoPrincipal === 'function') {
                            window.hcalcAtualizarVisibilidadeDepositoPrincipal(d.idx);
                        }
                    });
                }

                queueOverlayDraftSave();
            };

            if (respSubs) respSubs.addEventListener('change', updateVisibility);
            if (respSol) respSol.addEventListener('change', updateVisibility);
            if (radSubInt) radSubInt.addEventListener('change', updateVisibility);
            if (radSubDiv) radSubDiv.addEventListener('change', updateVisibility);
            if (radSolInt) radSolInt.addEventListener('change', updateVisibility);
            if (radSolDiv) radSolDiv.addEventListener('change', updateVisibility);
            
            const btnAddSub = document.getElementById('btn-adicionar-periodo-sub');
            if (btnAddSub) btnAddSub.onclick = (e) => { e.preventDefault(); adicionarLinhaPeridoDiverso('sub'); queueOverlayDraftSave(); };

            const btnAddSol = document.getElementById('btn-adicionar-periodo-sol');
            if (btnAddSol) btnAddSol.onclick = (e) => { e.preventDefault(); adicionarLinhaPeridoDiverso('sol'); queueOverlayDraftSave(); };

            // Rec. Judicial/Falência por principal (item 1): aplicar estilo nas intimações ao mudar
            const containerPrincipais = document.getElementById('resp-principais-dinamico-container');
            if (containerPrincipais) {
                containerPrincipais.addEventListener('change', (e) => {
                    if (e.target.classList.contains('chk-principal-rec')) {
                        aplicarEstiloRecuperacaoJudicial();
                        queueOverlayDraftSave();
                    }
                });
            }
            
            const recJudUnicaEl = document.getElementById('resp-rec-judicial-unica');
            if (recJudUnicaEl) recJudUnicaEl.addEventListener('change', () => { aplicarEstiloRecuperacaoJudicial(); queueOverlayDraftSave(); });

            // --- Principais quick-add
            const selAddPrincipal = document.getElementById('sel-add-principal');
            const btnAddPrincipal = document.getElementById('btn-add-principal');
            if (btnAddPrincipal && selAddPrincipal) {
                btnAddPrincipal.onclick = (e) => {
                    e.preventDefault();
                    const nome = selAddPrincipal.value;
                    if (nome) addPrincipal(nome);
                };
            }

            // Auto-add first reclamada if none exist
            try {
                const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
                if (reclamadas.length && containerPrincipais && containerPrincipais.children.length === 0) {
                    addPrincipal(reclamadas[0]);
                }
            } catch (e) { /* ignore */ }

            // --- Subsidiárias integrais quick-add
            const selAddSubsInt = document.getElementById('sel-add-subs-int');
            const btnAddSubsInt = document.getElementById('btn-add-subs-int');
            if (btnAddSubsInt && selAddSubsInt) {
                btnAddSubsInt.onclick = (e) => { e.preventDefault(); const nome = selAddSubsInt.value; if (nome) addSubsInt(nome); };
            }

            const chkNaoHaSubsInt = document.getElementById('chk-nao-ha-subs-int');
            if (chkNaoHaSubsInt) {
                chkNaoHaSubsInt.onchange = (e) => {
                    const hide = e.target.checked;
                    document.getElementById('resp-subsidiarias-integral-dinamico-container').classList.toggle('hidden', hide);
                    document.getElementById('div-add-subs-int').classList.toggle('hidden', hide);
                    queueOverlayDraftSave();
                };
            }
            const subsIntContainer = document.getElementById('resp-subsidiarias-integral-dinamico-container');
            if (subsIntContainer) {
                subsIntContainer.addEventListener('change', (e) => {
                    if (e.target.classList.contains('chk-subs-int-rec')) {
                        aplicarEstiloRecuperacaoJudicial();
                        queueOverlayDraftSave();
                    }
                });
            }

            // --- Solidárias integrais quick-add
            const selAddSolInt = document.getElementById('sel-add-sol-int');
            const btnAddSolInt = document.getElementById('btn-add-sol-int');
            if (btnAddSolInt && selAddSolInt) {
                btnAddSolInt.onclick = (e) => { e.preventDefault(); const nome = selAddSolInt.value; if (nome) addSolInt(nome); };
            }

            const chkNaoHaSolInt = document.getElementById('chk-nao-ha-sol-int');
            if (chkNaoHaSolInt) {
                chkNaoHaSolInt.onchange = (e) => {
                    const hide = e.target.checked;
                    document.getElementById('resp-solidarias-integral-dinamico-container').classList.toggle('hidden', hide);
                    document.getElementById('div-add-sol-int').classList.toggle('hidden', hide);
                    queueOverlayDraftSave();
                };
            }
            const solIntContainer = document.getElementById('resp-solidarias-integral-dinamico-container');
            if (solIntContainer) {
                solIntContainer.addEventListener('change', (e) => {
                    if (e.target.classList.contains('chk-sol-int-rec')) {
                        aplicarEstiloRecuperacaoJudicial();
                        queueOverlayDraftSave();
                    }
                });
            }
            
            // Ensure UI reflects current checkbox states immediately
            try { updateVisibility(); aplicarEstiloRecuperacaoJudicial(); } catch (e) { /* ignore */ }

            return {
                addPrincipal,
                addSubsInt,
                addSolInt
            };
        }

        const exposedApi = initEventHandlers();

        return {
            initEventHandlers,
            aplicarEstiloRecuperacaoJudicial,
            atualizarDropdownsPlanilhas,
            adicionarLinhaPeridoDiverso,
            addPrincipal: exposedApi.addPrincipal,
            addSubsInt: exposedApi.addSubsInt,
            addSolInt: exposedApi.addSolInt
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
            const linhasSol = Array.from(document.querySelectorAll('#resp-sol-diversos-container [id^="periodo-diverso-sol-"]'));
            const linhasSub = Array.from(document.querySelectorAll('#resp-sub-diversos-container [id^="periodo-diverso-sub-"]'));

            const periodoCompleto = window.hcalcState.planilhaExtracaoData?.periodoCalculo || '';
            
            // Principais
            let principaisSelecionadas = Array.from(document.querySelectorAll('#resp-principais-dinamico-container .principal-item')).map(item => {
                const nome = item.dataset.nome;
                const recChk = item.querySelector('.chk-principal-rec');
                return { nome: nome, recJud: !!(recChk && recChk.checked) };
            }).filter(p => p.nome);

            // Solidarias Integrais act as Principals
            Array.from(document.querySelectorAll('#resp-solidarias-integral-dinamico-container .sol-item')).forEach(item => {
                const nome = item.dataset.nome;
                if (!nome) return;
                const recChk = item.querySelector('.chk-sol-int-rec');
                // Only push if not already explicitly in Principais
                if (!principaisSelecionadas.some(p => p.nome === nome)) {
                    principaisSelecionadas.push({ nome, recJud: !!(recChk && recChk.checked) });
                }
            });

            const principaisParciais = [];
            const subsidiariasComPeriodo = [];

            const processarLinhas = (linhas, arrayDestino, isPrincipalParcial) => {
                linhas.forEach((linha) => {
                    const itensLista = linha.querySelectorAll('.periodo-reclamadas-list .reclamada-item');
                    const nomesRec = Array.from(itensLista).map(item => item.dataset.nome).filter(Boolean);
                    
                    const periodoTexto = linha.querySelector(`.periodo-periodo`)?.value || '';
                    const idPlanilhaManual = linha.querySelector(`.periodo-id`)?.value || '';
                    const idPlanilhaFinal = idPlanilhaManual || `SemID-${Math.random().toString(36).substring(2, 7)}`;

                    // Planilha diversa é sempre uma planilha separada
                    const usarMesmaPlanilha = false; 

                    // Salva cada empresa listada no array destino
                    nomesRec.forEach((nomeRec) => {
                        if (nomeRec) {
                            arrayDestino.push({ 
                                nome: nomeRec, 
                                periodo: periodoTexto, 
                                idPlanilha: idPlanilhaFinal, 
                                usarMesmaPlanilha: usarMesmaPlanilha 
                            });
                        }
                    });
                });
            };

            processarLinhas(linhasSol, principaisParciais, true);
            processarLinhas(linhasSub, subsidiariasComPeriodo, false);

            const nomesPrincipaisUnicos = Array.from(new Set(principaisSelecionadas.map(p => p.nome).filter(n => n)));
            const principalsSet = new Set(nomesPrincipaisUnicos);
            const subsComPeriodoSet = new Set(subsidiariasComPeriodo.map(s => s.nome));
            
            // Subsidiarias integrais
            const subsIntFromDom = Array.from(document.querySelectorAll('#resp-subsidiarias-integral-dinamico-container .subs-item')).map(el => el.dataset.nome);
            const subsidiariasIntegrais = subsIntFromDom.filter(nome => nome && !principalsSet.has(nome) && !subsComPeriodoSet.has(nome));

            const txtPrincipais = formatarLista(nomesPrincipaisUnicos);
            const subsInt = subsidiariasIntegrais || [];
            const subsDiv = subsidiariasComPeriodo || [];
            const solDiv = principaisParciais || [];

            const paragrafos = [];

            if (nomesPrincipaisUnicos.length > 0) {
                paragrafos.push(`<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">São devedoras principais/solidárias: ${txtPrincipais}. Portanto, apenas estas respondem pelo montante neste ato.</p>`);
            }

            if (solDiv.length > 0) {
                const txtSolDiv = formatarLista(solDiv.map(s => s.nome || s));
                paragrafos.push(`<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">São devedoras solidárias por período parcial do contrato: ${txtSolDiv} — serão tratadas em item próprio a seguir.</p>`);
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
                principaisParciais: solDiv,
                subsidiariasIntegrais: subsInt,
                subsidiariasComPeriodo: subsDiv,
                todasPrincipais: [
                    // Adiciona flag usarMesmaPlanilha para evitar que a principal receba R$XXX no texto
                    ...nomesPrincipaisUnicos.map(n => ({ nome: n, periodo: 'integral', idPlanilha: '', usarMesmaPlanilha: true })),
                    ...solDiv
                ],
                principaisComRecJud: principaisSelecionadas.filter(p => p.recJud).map(p => p.nome),
                subsIntComRecJud: Array.from(document.querySelectorAll('#resp-subsidiarias-integral-dinamico-container .subs-item .chk-subs-int-rec:checked')).map(chk => chk.closest('.subs-item')?.dataset?.nome).filter(Boolean)
            };
        }

        // RETORNO DA API DE TEXTO QUE HAVIA SIDO APAGADO:
        return {
            gerarTextoResponsabilidades
        };
    }

    window.hcalcOverlayResponsabilidades = { createController, createTextApi };
})();