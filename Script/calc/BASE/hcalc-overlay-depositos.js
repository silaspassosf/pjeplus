(function () {
    'use strict';

    function createController(deps) {
        const { $, queueOverlayDraftSave } = deps;

        function preencherDepositosAutomaticos() {
            const prep = window.hcalcLastPrepResult;
            if (!prep || !prep.depositos || prep.depositos.length === 0) {
                console.log('[AUTO-DEPOSITOS] Sem dados de prep', { prepPresent: !!prep, depositosLength: prep?.depositos?.length });
                return;
            }

            const container = $('depositos-container');
            if (!container) {
                console.error('[AUTO-DEPOSITOS] Container não encontrado!');
                return;
            }

            const jaTemCampos = container.children.length > 0;
            if (jaTemCampos) {
                console.log('[AUTO-DEPOSITOS] Container já possui campos, pulando');
                return;
            }

            container.innerHTML = '';
            window.hcalcState.nextDepositoIdx = 0;
            window.hcalcState.depositosRecursais = [];

            console.log('[AUTO-DEPOSITOS] Iniciando preenchimento com', prep.depositos.length, 'recursos', { depositos: prep.depositos });

            for (const deposito of prep.depositos) {
                console.log('[AUTO-DEPOSITOS] processamento de recurso encontrado:', deposito);
                
                // 1. Filtra os anexos: aceita apenas Depósito ou Garantia (NUNCA Custas)
                const anexosValidos = (deposito.anexos || []).filter(ax => 
                    ax.tipo === 'Depósito' || ax.tipo === 'Garantia'
                );

                let anexoEscolhido = null;

                if (anexosValidos.length > 0) {
                    // 2. Regras de Preferência (Tie-breaker)
                    // Preferência 1: Depósito com nome específico da guia
                    const depositoPreferencial = anexosValidos.find(ax => 
                        ax.tipo === 'Depósito' && 
                        /(guia de dep[oó]sito recursal|guia de dep[oó]sito judicial)/i.test(ax.texto || '')
                    );
                    
                    // Preferência 2: Qualquer outro Depósito
                    const qualquerDeposito = anexosValidos.find(ax => ax.tipo === 'Depósito');
                    
                    // Preferência 3: Seguro Garantia
                    const garantia = anexosValidos.find(ax => ax.tipo === 'Garantia');

                    anexoEscolhido = depositoPreferencial || qualquerDeposito || garantia;
                }

                // 3. Cria EXATAMENTE UMA linha para este recurso
                adicionarDepositoRecursal();
                const idx = window.hcalcState.nextDepositoIdx - 1;

                // Preenche o nome da reclamada (sempre preenche, mesmo se não achar anexo válido)
                const depositanteSelect = $(`dep-depositante-${idx}`);
                if (depositanteSelect) {
                    depositanteSelect.value = deposito.depositante || '';
                }

                // 4. Se encontrou um anexo campeão, preenche os dados dele
                if (anexoEscolhido) {
                    const tipoSelect = $(`dep-tipo-${idx}`);
                    const idInput = $(`dep-id-${idx}`);

                    if (tipoSelect) {
                        tipoSelect.value = anexoEscolhido.tipo === 'Depósito' ? 'bb' : 'garantia';
                        tipoSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    if (idInput) {
                        idInput.value = anexoEscolhido.id || '';
                    }
                    console.log('[AUTO-DEPOSITOS] 1 anexo consolidado escolhido:', anexoEscolhido);
                } else {
                    console.warn('[AUTO-DEPOSITOS] Recurso sem anexos válidos (Depósito/Garantia) para', deposito.depositante, '— criada linha apenas com o nome');
                }
            }
        }

        function adicionarDepositoRecursal() {
            const idx = window.hcalcState.nextDepositoIdx++;
            const container = $('depositos-container');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];

            console.log('[AUTO-DEPOSITOS] adicionarDepositoRecursal called, idx will be', idx, 'reclamadas:', reclamadas);

            const depositoDiv = document.createElement('div');
            depositoDiv.id = `deposito-item-${idx}`;
            depositoDiv.className = 'deposito-item';
            depositoDiv.style.cssText = 'border: 1px solid #ddd; padding: 8px; margin-bottom: 8px; border-radius: 4px; background: #f9f9f9;';

            let optionsHtml = '<option value="">-- Selecione Reclamada --</option>';
            for (const nome of reclamadas) {
                optionsHtml += `<option value="${nome}">${nome}</option>`;
            }

            depositoDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong id="dep-title-${idx}" style="font-size: 11px; color: #666;">Depósito Recursal #${idx + 1}</strong>
                    <button type="button" id="btn-remover-dep-${idx}" style="padding: 2px 8px; font-size: 10px; color: #dc2626; background: #fee; border: 1px solid #fca; border-radius: 3px; cursor: pointer;">✕ Remover</button>
                </div>
                <div class="row">
                    <select id="dep-tipo-${idx}" data-dep-idx="${idx}">
                        <option value="bb" selected>Banco do Brasil</option>
                        <option value="sif">CEF (SIF)</option>
                        <option value="garantia">Seguro Garantia</option>
                    </select>
                    <select id="dep-depositante-${idx}" data-dep-idx="${idx}">
                        ${optionsHtml}
                    </select>
                    <input type="text" id="dep-id-${idx}" placeholder="ID da Guia" data-dep-idx="${idx}">
                </div>
                <div class="row" id="dep-principal-row-${idx}">
                    <label><input type="checkbox" id="dep-principal-${idx}" checked data-dep-idx="${idx}"> Depositado pela Devedora Principal?</label>
                </div>
                <div class="row hidden" id="dep-solidaria-info-${idx}" style="font-size: 11px; color: #059669; font-style: italic;">
                    ✓ Devedoras solidárias: qualquer depósito pode ser liberado
                </div>
                <div class="row" id="dep-liberacao-row-${idx}">
                    <label><input type="radio" name="rad-dep-lib-${idx}" value="reclamante" checked data-dep-idx="${idx}"> Liberação simples (Reclamante)</label>
                    <label style="margin-left: 10px;"><input type="radio" name="rad-dep-lib-${idx}" value="detalhada" data-dep-idx="${idx}"> Liberação detalhada (Crédito, INSS, Hon.)</label>
                </div>
            `;

            container.appendChild(depositoDiv);

            // Se houver apenas uma reclamadas detectada, indicar no título que é a "Única"
            try {
                const titleEl = document.getElementById(`dep-title-${idx}`);
                const reclamadasNow = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
                if (titleEl) titleEl.textContent = `Depósito Recursal #${idx + 1}` + (reclamadasNow.length === 1 ? ' (Única)' : '');
            } catch (e) { /* ignore */ }

            const tipoEl = $(`dep-tipo-${idx}`);
            const principalEl = $(`dep-principal-${idx}`);
            const liberacaoRow = $(`dep-liberacao-row-${idx}`);

            tipoEl.onchange = (e) => {
                liberacaoRow.classList.toggle('hidden', e.target.value === 'garantia');
            };

            principalEl.onchange = (e) => {
                liberacaoRow.classList.toggle('hidden', !e.target.checked);
            };

            atualizarVisibilidadeDepositoPrincipal(idx);

            const btnRemoverDep = depositoDiv.querySelector(`#btn-remover-dep-${idx}`);
            if (btnRemoverDep) {
                btnRemoverDep.addEventListener('click', () => {
                    depositoDiv.remove();
                    const dep = window.hcalcState.depositosRecursais.find(d => d.idx === idx);
                    if (dep) dep.removed = true;
                    queueOverlayDraftSave();
                });
            }

            window.hcalcState.depositosRecursais.push({ idx, removed: false });
            queueOverlayDraftSave();
        }

        function atualizarVisibilidadeDepositoPrincipal(idx) {
            const isSolidaria = document.getElementById('resp-solidarias')?.checked || false;
            const isUnica = document.getElementById('resp-unica-flag')?.value === 'true';

            const principalRow = $(`dep-principal-row-${idx}`);
            const solidariaInfo = $(`dep-solidaria-info-${idx}`);
            const principalChk = $(`dep-principal-${idx}`);

            if (!principalRow || !solidariaInfo) return;

            // Devedora Única tem precedência: esconder escolha e travar como principal
            if (isUnica) {
                principalRow.classList.add('hidden');
                solidariaInfo.classList.remove('hidden');
                if (principalChk) { principalChk.checked = true; principalChk.disabled = true; }
                return;
            }

            // Caso contrário, comportamento normal com base na marcação de solidárias
            if (isSolidaria) {
                principalRow.classList.add('hidden');
                solidariaInfo.classList.remove('hidden');
                if (principalChk) { principalChk.checked = true; principalChk.disabled = false; }
            } else {
                principalRow.classList.remove('hidden');
                solidariaInfo.classList.add('hidden');
                if (principalChk) principalChk.disabled = false;
            }
        }

        function adicionarPagamentoAntecipado() {
            const idx = window.hcalcState.nextPagamentoIdx++;
            const container = $('pagamentos-container');

            const pagamentoDiv = document.createElement('div');
            pagamentoDiv.id = `pagamento-item-${idx}`;
            pagamentoDiv.className = 'pagamento-item';
            pagamentoDiv.style.cssText = 'border: 1px solid #ddd; padding: 8px; margin-bottom: 8px; border-radius: 4px; background: #f9f9f9;';

            pagamentoDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="font-size: 11px; color: #666;">Pagamento Antecipado #${idx + 1}</strong>
                    <button type="button" id="btn-remover-pag-${idx}" style="padding: 2px 8px; font-size: 10px; color: #dc2626; background: #fee; border: 1px solid #fca; border-radius: 3px; cursor: pointer;">✕ Remover</button>
                </div>
                <div class="row">
                    <input type="text" id="pag-id-${idx}" placeholder="ID do Depósito" data-pag-idx="${idx}">
                </div>
                <div class="row">
                    <label><input type="radio" name="lib-tipo-${idx}" value="nenhum" checked data-pag-idx="${idx}"> Padrão (extinção)</label>
                    <label style="margin-left: 15px;"><input type="radio" name="lib-tipo-${idx}" value="remanescente" data-pag-idx="${idx}"> Com Remanescente</label>
                    <label style="margin-left: 15px;"><input type="radio" name="lib-tipo-${idx}" value="devolucao" data-pag-idx="${idx}"> Com Devolução</label>
                </div>
                <div id="lib-remanescente-campos-${idx}" class="hidden">
                    <div class="row">
                        <input type="text" id="lib-rem-valor-${idx}" placeholder="Valor Remanescente (ex: 1.234,56)" data-pag-idx="${idx}">
                        <input type="text" id="lib-rem-titulo-${idx}" placeholder="Título (ex: custas processuais)" data-pag-idx="${idx}">
                    </div>
                </div>
                <div id="lib-devolucao-campos-${idx}" class="hidden">
                    <div class="row">
                        <input type="text" id="lib-dev-valor-${idx}" placeholder="Valor Devolução (ex: 1.234,56)" data-pag-idx="${idx}">
                    </div>
                </div>
            `;

            container.appendChild(pagamentoDiv);

            document.querySelectorAll(`input[name="lib-tipo-${idx}"]`).forEach(radio => {
                radio.addEventListener('change', (e) => {
                    const valor = e.target.value;
                    $(`lib-remanescente-campos-${idx}`).classList.toggle('hidden', valor !== 'remanescente');
                    $(`lib-devolucao-campos-${idx}`).classList.toggle('hidden', valor !== 'devolucao');
                });
            });

            const btnRemoverPag = pagamentoDiv.querySelector(`#btn-remover-pag-${idx}`);
            if (btnRemoverPag) {
                btnRemoverPag.addEventListener('click', () => {
                    pagamentoDiv.remove();
                    const pag = window.hcalcState.pagamentosAntecipados.find(p => p.idx === idx);
                    if (pag) pag.removed = true;
                    queueOverlayDraftSave();
                });
            }

            window.hcalcState.pagamentosAntecipados.push({ idx, removed: false });
            queueOverlayDraftSave();
        }

        return {
            preencherDepositosAutomaticos,
            adicionarDepositoRecursal,
            atualizarVisibilidadeDepositoPrincipal,
            adicionarPagamentoAntecipado
        };
    }

    window.hcalcOverlayDepositos = { createController };
})();