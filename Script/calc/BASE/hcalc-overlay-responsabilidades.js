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

        }

        // Definidas no escopo do controller para serem acessíveis externamente (Drafts)
        function addPrincipal(nome) {
            const principaisContainer = document.getElementById('resp-principais-dinamico-container');
            if (!nome || !principaisContainer) return;
            // avoid duplicates (check both dataset.nome and option value just in case)
            if (principaisContainer.querySelector(`.principal-item[data-nome="${CSS.escape(nome)}"]`)) return;
            const div = document.createElement('div');
            div.className = 'principal-item';
            div.dataset.nome = nome;
            div.style.display = 'flex';
            div.style.alignItems = 'center';
            div.style.gap = '8px';
            
            const isFirst = principaisContainer.children.length === 0;
            const removeStyle = isFirst ? 'display:none;' : 'background:#d32f2f;padding:4px 8px;';

            const todasReclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [nome];
            const optionsHtml = todasReclamadas.map(r => `<option value="${r}" ${r === nome ? 'selected' : ''}>${r}</option>`).join('');

            div.innerHTML = `<label style="flex:1; display:flex; gap:8px; align-items:center;">
                <input type="checkbox" class="chk-principal hidden" data-nome="${nome}" checked style="display:none;"> 
                <select class="sel-principal-dinamico" style="flex:1; padding:4px; max-width:400px;">
                    ${optionsHtml}
                </select>
            </label>
            <label style="font-size:11px;"><input type="checkbox" class="chk-principal-rec"> Rec. Judicial/Falência</label>
            <button type="button" class="btn-remove-principal btn-action" style="${removeStyle}">Remover</button>`;
            principaisContainer.appendChild(div);

            const sel = div.querySelector('.sel-principal-dinamico');
            const chk = div.querySelector('.chk-principal');
            sel.addEventListener('change', (e) => {
                const novoNome = e.target.value;
                div.dataset.nome = novoNome;
                chk.dataset.nome = novoNome;
                atualizarDropdownsPlanilhas();
                queueOverlayDraftSave();
            });

            // Se for o primeiro item, marcar automaticamente como principal
            try {
                if (chk && isFirst) {
                    chk.checked = true;
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

            const todas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const realIdx = todas.indexOf(nome) + 1;
            const prefixo = realIdx > 0 ? `${realIdx}ª ` : '';
            const nomeComPrefixo = `${prefixo}${nome}`;

            const box = document.createElement('div');
            box.className = 'resp-extra-box';
            box.dataset.nome = nome;
            box.dataset.idx = String(idx);
            box.id = `resp-extra-box-${idx}`;
            box.innerHTML = `
                <div style="border:1px solid #cbd5e1;border-radius:4px;padding:8px;margin-bottom:6px;background:#f8fafc">
                    <div style="display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px;">
                        <input type="text" value="${nomeComPrefixo}" disabled title="${nomeComPrefixo}" style="flex:1; padding:4px; border:1px solid #ccc; border-radius:4px; background:#e9ecef; color:#495057; font-size:12px; cursor:not-allowed;">
                        <div style="display:flex; gap:12px; align-items:center; margin-left:auto;">
                            <label style="font-size:11px;margin:0;"><input type="radio" name="rad-resp-extra-${idx}" value="subsidiaria" checked> Subsidiária</label>
                            <label style="font-size:11px;margin:0;"><input type="radio" name="rad-resp-extra-${idx}" value="solidaria"> Solidária</label>
                        </div>
                    </div>
                    <div id="resp-extra-periodo-opts-${idx}" style="display:flex; gap:12px; align-items:center; margin-bottom:4px;">
                        <label style="font-size:11px;margin:0;"><input type="checkbox" id="chk-resp-extra-integral-${idx}" checked> Período Integral</label>
                        <label style="font-size:11px;margin:0;"><input type="checkbox" id="chk-resp-extra-diverso-${idx}"> Período Diverso</label>
                    </div>
                    <div id="resp-extra-diverso-area-${idx}" class="hidden" style="margin-top:6px;">
                        <div class="row" style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">
                            <button type="button" id="btn-extra-carregar-${idx}" class="btn-action" style="font-size:11px;padding:4px 8px">📎 Carregar Planilha</button>
                            <input type="file" id="inp-extra-pdf-${idx}" accept="application/pdf" style="display:none">
                            <input type="text" id="inp-extra-uid-${idx}" placeholder="UID"
                                style="font-size:11px;padding:4px 6px;border:1px solid #ccc;border-radius:4px;width:120px;"
                                title="Cole o idUnicoDocumento da planilha para carregar via API">
                            <button type="button" id="btn-extra-uid-${idx}" class="btn-action"
                                style="font-size:11px;padding:4px 8px">API &#x21D2;</button>
                        </div>
                        <div id="resp-extra-resumo-${idx}" style="font-size:11px;color:#555;margin-top:4px"></div>
                    </div>
                </div>`;
            container.appendChild(box);

            const chkIntegral = box.querySelector(`#chk-resp-extra-integral-${idx}`);
            const chkDiverso = box.querySelector(`#chk-resp-extra-diverso-${idx}`);
            const diversoArea = box.querySelector(`#resp-extra-diverso-area-${idx}`);

            chkIntegral.addEventListener('change', () => {
                if (chkIntegral.checked) {
                    chkDiverso.checked = false;
                    diversoArea.classList.add('hidden');
                } else if (!chkDiverso.checked) {
                    chkIntegral.checked = true;
                }
                queueOverlayDraftSave();
            });

            chkDiverso.addEventListener('change', () => {
                if (chkDiverso.checked) {
                    chkIntegral.checked = false;
                    diversoArea.classList.remove('hidden');
                } else if (!chkIntegral.checked) {
                    chkDiverso.checked = true;
                }
                queueOverlayDraftSave();
            });

            box.querySelectorAll(`input[name="rad-resp-extra-${idx}"]`).forEach(radio => {
                radio.addEventListener('change', () => {
                    const isSolidaria = document.querySelector(`input[name="rad-resp-extra-${idx}"]:checked`)?.value === 'solidaria';
                    const periodoOpts = document.getElementById(`resp-extra-periodo-opts-${idx}`);
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

            // Handler API ⇒ para extra reclamada
            const btnExtraUid = document.getElementById(`btn-extra-uid-${idx}`);
            const inpExtraUid = document.getElementById(`inp-extra-uid-${idx}`);
            if (btnExtraUid && inpExtraUid) {
                btnExtraUid.addEventListener('click', async () => {
                    const uid = inpExtraUid.value.trim();
                    if (!uid) { alert('Informe o UID da planilha.'); return; }
                    const m = location.pathname.match(/\/processo\/(\d+)/);
                    if (!m) { alert('ID do processo não encontrado na URL.'); return; }
                    const idProcesso = m[1];
                    const getCookie = (name) => {
                        const c = document.cookie.split(';').map(s => s.trim())
                            .find(s => s.toLowerCase().startsWith(name.toLowerCase() + '='));
                        return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
                    };
                    const xsrf = getCookie('XSRF-TOKEN');
                    const headers = { 'Accept': '*/*', 'X-Grau-Instancia': '1' };
                    if (xsrf) headers['X-XSRF-TOKEN'] = xsrf;
                    btnExtraUid.disabled = true;
                    btnExtraUid.textContent = '⏳';
                    try {
                        const url = `${location.origin}/pje-comum-api/api/processos/id/${idProcesso}/documentos/id/${uid}/conteudo`;
                        const resp = await fetch(url, { method: 'GET', credentials: 'include', headers });
                        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                        const buffer = await resp.arrayBuffer();
                        if (!buffer || buffer.byteLength < 100) throw new Error('Resposta vazia');
                        await carregarPDFJSSeNecessario();
                        const fakeFile = new File([buffer], `Documento_${uid}.pdf`, { type: 'application/pdf' });
                        const dados = await processarPlanilhaPDF(fakeFile);
                        if (!dados || !dados.sucesso) throw new Error(dados && dados.erro ? dados.erro : 'Falha na extração');
                        const planilhaId = dados.id || dados.idPlanilha || `extra-${idx}-api`;
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
                            resumo.innerHTML = `<strong>ID:</strong> ${planilhaId} &nbsp; <strong>Período:</strong> ${dados.periodoCalculo || '—'} (API)`;
                        }
                        if (btnCarregar) btnCarregar.textContent = '✅ Planilha Carregada (API)';
                        btnExtraUid.textContent = '✓';
                        inpExtraUid.value = '';
                        queueOverlayDraftSave();
                        setTimeout(() => { btnExtraUid.textContent = 'API ⇒'; btnExtraUid.disabled = false; }, 2000);
                    } catch (e) {
                        console.warn('hcalc resp-extra uid falhou:', e.message);
                        alert('Erro ao carregar via API: ' + e.message);
                        btnExtraUid.textContent = 'API ⇒';
                        btnExtraUid.disabled = false;
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
            const btnAddPrincipal = document.getElementById('btn-add-principal');
            if (btnAddPrincipal) {
                btnAddPrincipal.onclick = (e) => {
                    e.preventDefault();
                    const curNames = Array.from(document.querySelectorAll('.sel-principal-dinamico')).map(s => s.value);
                    const todas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
                    const next = todas.find(n => !curNames.includes(n)) || todas[0] || 'Nova Devedora';
                    addPrincipal(next);
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
                    const chkDiverso = document.getElementById(`chk-resp-extra-diverso-${idx}`);
                    const periodo = chkDiverso && chkDiverso.checked ? 'diverso' : 'integral';
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