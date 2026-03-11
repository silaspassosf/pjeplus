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
            const temRecJudicial = $('resp-rec-judicial')?.checked || false;

            document.querySelectorAll('.intimacao-row').forEach(row => {
                const checkbox = row.querySelector('.chk-parte-principal');
                if (checkbox && checkbox.checked) {
                    const nomeDiv = row.querySelector('div[title]');
                    if (nomeDiv) {
                        if (temRecJudicial) {
                            nomeDiv.style.textDecoration = 'line-through';
                            nomeDiv.style.color = '#999';
                            nomeDiv.title = `${checkbox.dataset.nome} (Em Recuperação Judicial/Falência - sem intimação para pagamento)`;
                        } else {
                            nomeDiv.style.textDecoration = 'none';
                            nomeDiv.style.color = '#333';
                            nomeDiv.title = checkbox.dataset.nome;
                        }
                    }
                }
            });
        }

        function registrarPlanilhaDisponivel(id, label, dados) {
            if (!window.hcalcState.planilhasDisponiveis) window.hcalcState.planilhasDisponiveis = [];
            window.hcalcState.planilhasDisponiveis =
                window.hcalcState.planilhasDisponiveis.filter(p => p.id !== id);
            window.hcalcState.planilhasDisponiveis.push({ id, label, dados });
            atualizarDropdownsPlanilhas();
        }

        function atualizarDropdownsPlanilhas() {
            const extras = window.hcalcState.planilhasDisponiveis || [];
            document.querySelectorAll('.periodo-planilha-select').forEach(sel => {
                const currentVal = sel.value;
                Array.from(sel.options).filter(o => o.value !== 'principal').forEach(o => o.remove());
                extras.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = `📊 ${p.label}`;
                    sel.appendChild(opt);
                });
                if (Array.from(sel.options).some(o => o.value === currentVal)) sel.value = currentVal;
            });
        }

        function atualizarDropdownsReclamadas() {
            const todasReclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const principalIntegral = $('resp-devedora-principal')?.value || '';

            const jaUsadas = new Set([principalIntegral]);
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                if (select.value) jaUsadas.add(select.value);
            });

            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                const valorAtual = select.value;

                select.innerHTML = '<option value="">Selecione a reclamada...</option>';
                todasReclamadas.forEach(rec => {
                    if (!jaUsadas.has(rec) || rec === valorAtual) {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        if (rec === valorAtual) opt.selected = true;
                        select.appendChild(opt);
                    }
                });
            });
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

            const jaUsadas = new Set([principalIntegral]);
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                if (select.value) jaUsadas.add(select.value);
            });

            let selectOptions = '<option value="">Selecione a reclamada...</option>';
            reclamadas.forEach(rec => {
                if (!jaUsadas.has(rec)) {
                    selectOptions += `<option value="${rec}">${rec}</option>`;
                }
            });

            div.innerHTML = `
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Devedora #${numeroDevedora}</label>
                    <select class="periodo-reclamada" data-idx="${idx}" style="width: 100%; padding: 8px;">
                        ${selectOptions}
                    </select>
                </div>
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Tipo de Responsabilidade</label>
                    <div style="display: flex; gap: 15px;">
                        <label><input type="radio" name="periodo-tipo-${idx}" class="periodo-tipo" data-idx="${idx}" value="subsidiaria" checked> Subsidiária</label>
                        <label><input type="radio" name="periodo-tipo-${idx}" class="periodo-tipo" data-idx="${idx}" value="principal"> Principal (Período Parcial)</label>
                    </div>
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

            if (respSubs) respSubs.addEventListener('change', updateRespOptions);
            if (respSol) respSol.addEventListener('change', updateRespOptions);

            $('resp-diversos').onchange = (e) => {
                const fieldset = $('resp-diversos-fieldset');
                const container = $('resp-diversos-container');
                const selectPrincipal = $('resp-devedora-principal');
                const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];

                if (e.target.checked) {
                    fieldset.classList.remove('hidden');

                    selectPrincipal.innerHTML = '';
                    reclamadas.forEach((rec, idx) => {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        if (idx === 0) opt.selected = true;
                        selectPrincipal.appendChild(opt);
                    });

                    if (container.children.length === 0) {
                        adicionarLinhaPeridoDiverso();
                    }
                } else {
                    fieldset.classList.add('hidden');
                    container.innerHTML = '';
                }
            };

            $('resp-devedora-principal').onchange = () => {
                atualizarDropdownsReclamadas();
            };

            $('resp-rec-judicial').onchange = () => {
                aplicarEstiloRecuperacaoJudicial();
            };

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

            const principalSelecionada = $('resp-devedora-principal')?.value || '1';
            const periodoCompleto = window.hcalcState.planilhaExtracaoData?.periodoCalculo || '';
            const principaisParciais = [];
            const subsidiariasComPeriodo = [];

            linhasPeriodos.forEach((linha) => {
                const idx = linha.id.replace('periodo-diverso-', '');
                const nomeRec = document.querySelector(`.periodo-reclamada[data-idx="${idx}"]`)?.value || '';
                const periodoTexto = document.querySelector(`.periodo-periodo[data-idx="${idx}"]`)?.value || '';
                const idPlanilhaManual = document.querySelector(`.periodo-id[data-idx="${idx}"]`)?.value || '';
                const tipoRadio = document.querySelector(`input[name="periodo-tipo-${idx}"]:checked`)?.value || 'principal';

                const planilhaSel = document.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`)?.value || 'principal';
                const usarMesmaPlanilha = planilhaSel === 'principal';
                const idPlanilhaFinal = usarMesmaPlanilha ? '' : (planilhaSel || idPlanilhaManual);
                const periodoTotalCheckbox = document.querySelector(`.periodo-total[data-idx="${idx}"]`);
                let isPeriodoIntegral = !periodoTexto || periodoTexto === periodoCompleto;
                // If user explicitly marked 'Período Total', treat as integral
                if (periodoTotalCheckbox && periodoTotalCheckbox.checked) isPeriodoIntegral = true;
                // If the selected planilha is an extra planilha (not 'principal'), consider it a diverso period
                if (!usarMesmaPlanilha) isPeriodoIntegral = false;

                if (nomeRec && !isPeriodoIntegral) {
                    if (tipoRadio === 'principal') {
                        principaisParciais.push({ nome: nomeRec, periodo: periodoTexto, idPlanilha: idPlanilhaFinal, usarMesmaPlanilha });
                    } else {
                        subsidiariasComPeriodo.push({ nome: nomeRec, periodo: periodoTexto, idPlanilha: idPlanilhaFinal, usarMesmaPlanilha });
                    }
                }
            });

            const principaisNomes = new Set([principalSelecionada, ...principaisParciais.map(p => p.nome)]);
            const subsidiariasComPeriodoNomes = new Set(subsidiariasComPeriodo.map(s => s.nome));
            const todasReclamadas = Array.from(document.querySelectorAll('.chk-parte-principal'))
                .map(chk => chk.getAttribute('data-nome'))
                .filter(n => n);

            const subsidiariasIntegrais = todasReclamadas.filter(nome =>
                !principaisNomes.has(nome) && !subsidiariasComPeriodoNomes.has(nome)
            );

            const nomesPrincipais = [principalSelecionada, ...principaisParciais.map(p => p.nome)];
            const nomesPrincipaisUnicos = Array.from(new Set(nomesPrincipais.filter(n => n)));
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
                principalIntegral: principalSelecionada,
                principaisParciais,
                subsidiariasIntegrais,
                subsidiariasComPeriodo,
                todasPrincipais: [
                    { nome: principalSelecionada, periodo: 'integral', idPlanilha: '' },
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