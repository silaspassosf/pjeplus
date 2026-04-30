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
                const temRecJudicial = (recChkPrincipal && recChkPrincipal.checked) || recJudicialUnica;
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

            // Principais
            const jaUsadas = new Set();
            document.querySelectorAll('#resp-principais-dinamico-container .chk-principal:checked').forEach(chk => jaUsadas.add(chk.dataset.nome));

            // Extras
            document.querySelectorAll('#resp-extras-reclamadas-container .resp-extra-box').forEach(box => {
                if (box.dataset.nome) jaUsadas.add(box.dataset.nome);
            });

            // Update selAddPrincipal
            const selAddPrincipal = document.getElementById('sel-add-principal');
            if (selAddPrincipal) {
                const cur = selAddPrincipal.value || '';
                selAddPrincipal.innerHTML = '<option value="">Adicionar devedora principal...</option>';
                todasReclamadas.forEach(rec => {
                    if (!jaUsadas.has(rec) || rec === cur) {
                        const o = document.createElement('option'); o.value = rec; o.textContent = rec; selAddPrincipal.appendChild(o);
                    }
                });
            }
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

        // ── TASKS 1-3: Boxes de reclamadas extras (2ª reclamada em diante) ──────────

        function criarBoxReclamadaExtra(nome, idx) {
            let container = document.getElementById('resp-extras-reclamadas-container');
            if (!container) return;
            if (container.querySelector(`.resp-extra-box[data-nome="${CSS.escape(nome)}"]`)) return;

            const box = document.createElement('div');
            box.className = 'resp-extra-box';
            box.dataset.nome = nome;
            box.dataset.idx = String(idx);
            box.id = `resp-extra-box-${idx}`;
            box.innerHTML = `
                <fieldset style="border:1px solid #cbd5e1;border-radius:4px;padding:8px;margin-bottom:6px;background:#f8fafc">
                    <legend style="background:#6b7280;color:#fff;padding:2px 6px;border-radius:3px;font-size:12px;font-weight:bold">${nome}</legend>
                    <div class="row" style="margin-bottom:4px">
                        <label style="font-size:12px"><input type="radio" name="rad-resp-extra-${idx}" value="subsidiaria" checked> Subsidiária</label>
                        <label style="font-size:12px;margin-left:12px"><input type="radio" name="rad-resp-extra-${idx}" value="solidaria"> Solidária</label>
                    </div>
                    <div id="resp-extra-periodo-opts-${idx}" class="row" style="margin-bottom:4px">
                        <label style="font-size:12px"><input type="radio" name="rad-resp-extra-periodo-${idx}" value="integral" checked> Período Integral</label>
                        <label style="font-size:12px;margin-left:12px"><input type="radio" name="rad-resp-extra-periodo-${idx}" value="diverso"> Período Diverso</label>
                    </div>
                    <div id="resp-extra-diverso-area-${idx}" class="hidden">
                        <div class="row">
                            <button type="button" id="btn-extra-carregar-${idx}" class="btn-action" style="font-size:11px;padding:4px 8px">📎 Carregar Planilha</button>
                            <input type="file" id="inp-extra-pdf-${idx}" accept="application/pdf" style="display:none">
                        </div>
                        <div id="resp-extra-resumo-${idx}" style="font-size:11px;color:#555;margin-top:4px"></div>
                    </div>
                </fieldset>`;
            container.appendChild(box);

            box.querySelectorAll(`input[name="rad-resp-extra-${idx}"]`).forEach(radio => {
                radio.addEventListener('change', () => {
                    const isSolidaria = document.querySelector(`input[name="rad-resp-extra-${idx}"]:checked`)?.value === 'solidaria';
                    const periodoOpts = document.getElementById(`resp-extra-periodo-opts-${idx}`);
                    const diversoArea = document.getElementById(`resp-extra-diverso-area-${idx}`);
                    if (periodoOpts) periodoOpts.classList.toggle('hidden', isSolidaria);
                    if (isSolidaria && diversoArea) diversoArea.classList.add('hidden');
                    queueOverlayDraftSave();
                });
            });

            box.querySelectorAll(`input[name="rad-resp-extra-periodo-${idx}"]`).forEach(radio => {
                radio.addEventListener('change', () => {
                    const isDiverso = document.querySelector(`input[name="rad-resp-extra-periodo-${idx}"]:checked`)?.value === 'diverso';
                    const diversoArea = document.getElementById(`resp-extra-diverso-area-${idx}`);
                    if (diversoArea) diversoArea.classList.toggle('hidden', !isDiverso);
                    queueOverlayDraftSave();
                });
            });

            const btnCarregar = document.getElementById(`btn-extra-carregar-${idx}`);
            const inpPdf = document.getElementById(`inp-extra-pdf-${idx}`);
            if (btnCarregar && inpPdf) {
                btnCarregar.addEventListener('click', () => inpPdf.click());
                inpPdf.addEventListener('change', async (e) => {
                    const file = e.target.files[0];
                    if (!file) return;
                    const originalText = btnCarregar.textContent;
                    try {
                        btnCarregar.textContent = '⏳ Processando...';
                        btnCarregar.disabled = true;
                        await carregarPDFJSSeNecessario();
                        const dados = await processarPlanilhaPDF(file);
                        if (dados) {
                            const planilhaId = dados.id || dados.idPlanilha || `extra-${idx}-${Date.now()}`;
                            const existente = window.hcalcState.planilhasDisponiveis.find(p => p.id === planilhaId);
                            if (!existente) {
                                window.hcalcState.planilhasDisponiveis.push({ id: planilhaId, label: nome, dados });
                            } else {
                                existente.dados = dados;
                            }
                            box.dataset.idPlanilha = planilhaId;
                            box.dataset.periodoCalculo = dados.periodoCalculo || '';
                            const resumo = document.getElementById(`resp-extra-resumo-${idx}`);
                            if (resumo) {
                                resumo.innerHTML = `<strong>ID:</strong> ${planilhaId} &nbsp; <strong>Período:</strong> ${dados.periodoCalculo || '—'}`;
                            }
                            btnCarregar.textContent = '✅ Planilha Carregada';
                            queueOverlayDraftSave();
                        }
                    } catch (err) {
                        console.warn('hcalc resp-extra carregar planilha falhou', err);
                        btnCarregar.textContent = '⚠️ Erro — Tentar novamente';
                    } finally {
                        btnCarregar.disabled = false;
                        inpPdf.value = '';
                    }
                });
            }
        }

        function inicializarBoxesReclamadasExtras(passivo) {
            if (!Array.isArray(passivo) || passivo.length <= 1) return;
            passivo.slice(1).forEach((parte, i) => {
                criarBoxReclamadaExtra(parte.nome, i + 1);
            });
        }

        // ── Fim Tasks 1-3 ────────────────────────────────────────────────────────────

        function initEventHandlers() {
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

            // Ensure UI reflects current checkbox states immediately
            try { aplicarEstiloRecuperacaoJudicial(); } catch (e) { /* ignore */ }

            return {
                addPrincipal
            };
        }

        const exposedApi = initEventHandlers();

        return {
            initEventHandlers,
            aplicarEstiloRecuperacaoJudicial,
            atualizarDropdownsPlanilhas,
            addPrincipal: exposedApi.addPrincipal,
            inicializarBoxesReclamadasExtras,
            criarBoxReclamadaExtra
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
            const periodoCompleto = window.hcalcState.planilhaExtracaoData?.periodoCalculo || '';
            
            // Principais
            let principaisSelecionadas = Array.from(document.querySelectorAll('#resp-principais-dinamico-container .principal-item')).map(item => {
                const nome = item.dataset.nome;
                const recChk = item.querySelector('.chk-principal-rec');
                return { nome: nome, recJud: !!(recChk && recChk.checked) };
            }).filter(p => p.nome);

            const principaisParciais = [];
            const subsidiariasComPeriodo = [];
            const extraSubsIntegrais = [];

            // Ler boxes de reclamadas extras
            Array.from(document.querySelectorAll('#resp-extras-reclamadas-container .resp-extra-box')).forEach((box) => {
                const nome = box.dataset.nome;
                if (!nome) return;
                const idx = box.dataset.idx;
                const tipo = document.querySelector(`input[name="rad-resp-extra-${idx}"]:checked`)?.value || 'subsidiaria';
                if (tipo === 'solidaria') {
                    if (!principaisSelecionadas.some(p => p.nome === nome)) {
                        principaisSelecionadas.push({ nome, recJud: false });
                    }
                } else {
                    const periodo = document.querySelector(`input[name="rad-resp-extra-periodo-${idx}"]:checked`)?.value || 'integral';
                    if (periodo === 'diverso') {
                        const idPlanilha = box.dataset.idPlanilha || `SemID-extra-${idx}`;
                        const periodoTexto = box.dataset.periodoCalculo || '';
                        if (!subsidiariasComPeriodo.some(s => s.nome === nome)) {
                            subsidiariasComPeriodo.push({ nome, periodo: periodoTexto, idPlanilha, usarMesmaPlanilha: false });
                        }
                    } else {
                        if (!extraSubsIntegrais.includes(nome)) extraSubsIntegrais.push(nome);
                    }
                }
            });

            const nomesPrincipaisUnicos = Array.from(new Set(principaisSelecionadas.map(p => p.nome).filter(n => n)));
            const principalsSet = new Set(nomesPrincipaisUnicos);
            const subsComPeriodoSet = new Set(subsidiariasComPeriodo.map(s => s.nome));
            
            // Subsidiarias integrais
            const subsidiariasIntegrais = extraSubsIntegrais.filter(nome => nome && !principalsSet.has(nome) && !subsComPeriodoSet.has(nome));

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
                paragrafos.push(`<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">São devedoras solidárias por período parcial do contrato: ${txtSolDiv}.</p>`);
            }

            if (subsInt.length > 0) {
                const txtSubsInt = formatarLista(subsInt);
                paragrafos.push(`<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">São devedoras subsidiárias pelo período integral do contrato: ${txtSubsInt}.</p>`);
            }

            if (subsDiv.length > 0) {
                const txtSubsDiv = formatarLista(subsDiv.map(s => s.nome || s));
                paragrafos.push(`<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">São devedoras subsidiárias por período parcial do contrato: ${txtSubsDiv}.</p>`);
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
                subsIntComRecJud: [] // O novo design de extra box não tem Recuperação Judicial per-item
            };
        }

        // RETORNO DA API DE TEXTO QUE HAVIA SIDO APAGADO:
        return {
            gerarTextoResponsabilidades
        };
    }

    window.hcalcOverlayResponsabilidades = { createController, createTextApi };
})();