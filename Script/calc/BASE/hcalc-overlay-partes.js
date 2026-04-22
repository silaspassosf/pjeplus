(function () {
    'use strict';

    function createController(deps) {
        const {
            $,
            normalizarNomeParaComparacao,
            aplicarEstiloRecuperacaoJudicial
        } = deps;

        window.hcalcPartesData = null;

        function isNomeRogerio(nome) {
            return /rogerio|rogério/i.test(nome || '');
        }

        function aplicarRegrasPeritosDetectados(peritosDetectados) {
            const nomes = Array.isArray(peritosDetectados) ? peritosDetectados.filter(Boolean) : [];
            const temRogerio = nomes.some((nome) => isNomeRogerio(nome));
            const peritosConhecimento = nomes.filter((nome) => !isNomeRogerio(nome));

            window.hcalcPeritosDetectados = nomes;
            window.hcalcPeritosConhecimentoDetectados = peritosConhecimento;

            console.log('[hcalc] aplicarRegrasPeritosDetectados: nomes=', nomes, 'temRogerio=', temRogerio, 'peritosConhecimento=', peritosConhecimento);

            const origemEl = $('calc-origem');
            const pjcEl = $('calc-pjc');
            const autorEl = $('calc-autor');
            const colEsclarecimentosEl = $('col-esclarecimentos');
            const rowPeritoContabilEl = $('row-perito-contabil');
            const chkPeritoConhEl = $('chk-perito-conh');
            const peritoConhCamposEl = $('perito-conh-campos');
            const valPeritoNomeEl = $('val-perito-nome');
            const valPeritoContabilValorEl = $('val-perito-contabil-valor');
            const fieldsetPericiaConh = $('fieldset-pericia-conh');

            console.log('[hcalc] Elementos encontrados: rowPeritoContabilEl=', rowPeritoContabilEl, 'fieldsetPericiaConh=', fieldsetPericiaConh);

            if (temRogerio) {
                console.log('[hcalc] Rogério detectado! Mostrando row-perito-contabil...');
                origemEl.value = 'pjecalc';
                origemEl.disabled = true;
                pjcEl.checked = true;
                pjcEl.disabled = true;
                autorEl.value = 'perito';
                autorEl.disabled = true;
                colEsclarecimentosEl.classList.remove('hidden');

                if (fieldsetPericiaConh) {
                    fieldsetPericiaConh.classList.remove('hidden');
                }

                if (rowPeritoContabilEl) {
                    rowPeritoContabilEl.classList.remove('hidden');
                    console.log('[hcalc] ✓ Classe hidden removida de row-perito-contabil');
                } else {
                    console.error('[hcalc] ✗ Elemento row-perito-contabil NÃO ENCONTRADO!');
                }

                if (peritosConhecimento.length === 0 && chkPeritoConhEl) {
                    chkPeritoConhEl.parentElement.parentElement.classList.add('hidden');
                }
            } else {
                origemEl.disabled = false;
                pjcEl.disabled = false;
                autorEl.disabled = false;
                rowPeritoContabilEl.classList.add('hidden');
                if (valPeritoContabilValorEl) {
                    valPeritoContabilValorEl.value = '';
                }
                colEsclarecimentosEl.classList.add('hidden');
            }

            if (peritosConhecimento.length > 0) {
                console.log('[hcalc] Perítos de conhecimento detectados:', peritosConhecimento);
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.remove('hidden');
                chkPeritoConhEl.checked = true;
                peritoConhCamposEl.classList.remove('hidden');
                valPeritoNomeEl.value = peritosConhecimento.join(' | ');
                console.log('[hcalc] ✓ Seção de conhecimento mostrada com peritos:', peritosConhecimento);
            } else if (!temRogerio) {
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.add('hidden');
            }
        }

        function construirSecaoIntimacoes() {
            const container = $('lista-intimacoes-container');
            if (!container) return;

            const passivo = window.hcalcPartesData?.passivo || [];
            const advMap = window.hcalcStatusAdvogados || {};
            const partesIntimadasEdital = window.hcalcPrepResult?.partesIntimadasEdital || [];

            container.innerHTML = '';

            if (passivo.length === 0) {
                container.innerHTML = `
                    <div style="margin-bottom: 5px;">
                        <input type="text" id="int-nome-parte-manual" placeholder="Nome da Reclamada" style="width: 100%; padding: 6px; box-sizing: border-box; margin-bottom: 5px;">
                        <select id="sel-intimacao-manual" style="width: 100%; padding: 4px;">
                            <option value="diario">Diário (Advogado - Art. 523)</option>
                            <option value="mandado">Mandado (Art. 880 - 48h)</option>
                            <option value="edital">Edital (Art. 880 - 48h)</option>
                        </select>
                    </div>`;
                return;
            }

            passivo.forEach((parte, idx) => {
                const temAdvogado = advMap[parte.nome] === true;
                let modoDefault = 'mandado';

                if (temAdvogado) modoDefault = 'diario';
                else if (partesIntimadasEdital.includes(parte.nome)) modoDefault = 'edital';

                const divRow = document.createElement('div');
                divRow.className = 'intimacao-row';
                divRow.style.cssText = 'display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; padding: 6px; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px;';

                const isPrimeiraPorPadrao = idx === 0;

                divRow.innerHTML = `
                    <div style="flex: 1; font-size: 13px; font-weight: bold; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 10px;" title="${parte.nome}">
                        ${parte.nome}
                    </div>
                    <div style="flex-shrink: 0; display: flex; align-items: center; gap: 8px;">
                        <label style="font-size: 11px; margin: 0; display: flex; align-items: center; gap: 3px; color: #666;">
                            <input type="checkbox" class="chk-parte-principal" data-nome="${parte.nome}" ${isPrimeiraPorPadrao ? 'checked' : ''}>
                            Principal
                        </label>
                        <select class="sel-modo-intimacao" data-nome="${parte.nome}" style="padding: 4px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="diario" ${modoDefault === 'diario' ? 'selected' : ''}>Diário (Advogado - Art 523)</option>
                            <option value="mandado" ${modoDefault === 'mandado' ? 'selected' : ''}>Mandado (Art 880 - 48h)</option>
                            <option value="edital" ${modoDefault === 'edital' ? 'selected' : ''}>Edital (Art 880 - 48h)</option>
                            <option value="ignorar">Não Intimar</option>
                        </select>
                    </div>
                `;
                container.appendChild(divRow);
            });

            setTimeout(() => aplicarEstiloRecuperacaoJudicial(), 50);

            container.querySelectorAll('.chk-parte-principal').forEach(chk => {
                chk.addEventListener('change', () => {
                    aplicarEstiloRecuperacaoJudicial();
                });
            });
        }

        async function refreshDetectedPartes() {
            const partes = await derivePartesData();

            window.hcalcPartesData = partes;

            const reclamadas = (partes?.passivo || []).map(p => p.nome).filter(Boolean);
            const peritos = ordenarComRogerioPrimeiro(extractPeritos(partes));
            const advogadosMap = extractAdvogadosPorReclamada(partes);
            const statusAdvMap = extractStatusAdvogadoPorReclamada(partes);
            const advogadosAutor = extractAdvogadosDoAutor(partes);

            window.hcalcStatusAdvogados = statusAdvMap;
            window.hcalcAdvogadosAutor = advogadosAutor;
            window.hcalcPeritosDetectados = peritos;

            console.log('hcalc: advogados por reclamada', advogadosMap);
            console.log('hcalc: status advogado por reclamada', statusAdvMap);
            console.log(`[hcalc] Detecção atualizada: ${reclamadas.length} reclamada(s), ${peritos.length} perito(s)`);

            aplicarRegrasPeritosDetectados(peritos);

            // Localiza o fieldset de Responsabilidade de forma robusta e oculta quando houver
            // apenas 1 reclamada (Devedora Única)
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
                if (respFieldset) {
                    if (reclamadas.length <= 1) respFieldset.classList.add('hidden');
                    else respFieldset.classList.remove('hidden');
                }
            } catch (e) { /* ignore */ }

            const recJudUnicaRow = $('resp-rec-judicial-unica-row');
            if (recJudUnicaRow) recJudUnicaRow.classList.toggle('hidden', reclamadas.length !== 1);

            // Se houver apenas 1 reclamada, travar como Devedora Única: marcar flag, esconder/opcionais
            try {
                const respUnicaFlag = $('resp-unica-flag');
                const chkSubs = $('resp-subsidiarias');
                const chkSol = $('resp-solidarias');
                const subOpcoes = $('resp-sub-opcoes');
                const solOpcoes = $('resp-sol-opcoes');
                const subsFieldset = $('resp-subsidiarias-integral-fieldset');
                const solFieldset = $('resp-solidarias-integral-fieldset');

                if (reclamadas.length === 1) {
                    if (respUnicaFlag) respUnicaFlag.value = 'true';
                    if (chkSubs) { chkSubs.checked = false; chkSubs.disabled = true; }
                    if (chkSol) { chkSol.checked = false; chkSol.disabled = true; }
                    if (subOpcoes) subOpcoes.classList.add('hidden');
                    if (solOpcoes) solOpcoes.classList.add('hidden');
                    if (subsFieldset) subsFieldset.classList.add('hidden');
                    if (solFieldset) solFieldset.classList.add('hidden');
                } else {
                    if (respUnicaFlag) respUnicaFlag.value = 'false';
                    if (chkSubs) { chkSubs.disabled = false; }
                    if (chkSol) { chkSol.disabled = false; }
                    if (subOpcoes) subOpcoes.classList.remove('hidden');
                    if (solOpcoes) solOpcoes.classList.remove('hidden');
                    if (subsFieldset) subsFieldset.classList.remove('hidden');
                    if (solFieldset) solFieldset.classList.remove('hidden');
                }
            } catch (e) { /* ignore */ }

            // Notificar outras seções que o estado "Devedora Única" mudou
            try { window.dispatchEvent(new CustomEvent('hcalc:devedora-unica-changed', { detail: { unica: reclamadas.length === 1 } })); } catch (e) { /* ignore */ }

            const depDepositante = $('dep-depositante');
            if (depDepositante && reclamadas.length > 0) {
                if (reclamadas.length === 1) {
                    depDepositante.value = reclamadas[0];
                    depDepositante.disabled = true;
                } else {
                    const selectEl = document.createElement('select');
                    selectEl.id = 'dep-depositante';
                    selectEl.style.cssText = depDepositante.style.cssText || 'padding: 8px; border: 1px solid #aaa; border-radius: 4px; font-size: 14px;';
                    reclamadas.forEach((rec, idx) => {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        if (idx === 0) opt.selected = true;
                        selectEl.appendChild(opt);
                    });
                    depDepositante.replaceWith(selectEl);
                }
            }

            construirSecaoIntimacoes();

            // sinaliza que as partes foram atualizadas para que outras seções possam reagir
            try { window.dispatchEvent(new CustomEvent('hcalc:partes-refreshed')); } catch (e) { console.error('[hcalc] dispatch partes-refreshed falhou', e); }
        }

        function getProcessIdFromUrl() {
            const match = window.location.href.match(/\/processo\/(\d+)/);
            return match ? match[1] : null;
        }

        function shapePartesPayload(dados) {
            const formatTelefones = (pessoaFisica) => {
                if (!pessoaFisica) { return 'desconhecido'; }
                const numbers = [];
                if (pessoaFisica.dddCelular && pessoaFisica.numeroCelular) {
                    numbers.push(`(${pessoaFisica.dddCelular}) ${pessoaFisica.numeroCelular}`);
                }
                if (pessoaFisica.dddResidencial && pessoaFisica.numeroResidencial) {
                    numbers.push(`(${pessoaFisica.dddResidencial}) ${pessoaFisica.numeroResidencial}`);
                }
                if (pessoaFisica.dddComercial && pessoaFisica.numeroComercial) {
                    numbers.push(`(${pessoaFisica.dddComercial}) ${pessoaFisica.numeroComercial}`);
                }
                return numbers.join(' | ') || 'desconhecido';
            };

            const buildRecord = (parte, tipo) => {
                const nome = parte.nome.trim();
                return {
                    nome,
                    cpfcnpj: parte.documento || 'desconhecido',
                    tipo,
                    telefone: formatTelefones(parte.pessoaFisica),
                    representantes: (parte.representantes || []).map(rep => ({
                        nome: rep.nome.trim(),
                        cpfcnpj: rep.documento || 'desconhecido',
                        oab: rep.numeroOab || '',
                        tipo: rep.tipo
                    }))
                };
            };

            const ativo = (dados?.ATIVO || []).map((parte) => buildRecord(parte, 'AUTOR'));
            const passivo = (dados?.PASSIVO || []).map((parte) => buildRecord(parte, 'RÉU'));
            const outros = (dados?.TERCEIROS || []).map((parte) => buildRecord(parte, parte.tipo || 'TERCEIRO'));

            return { ativo, passivo, outros };
        }

        async function fetchPartesViaApi() {
            const trtHost = window.location.host;
            const baseUrl = `https://${trtHost}`;
            const idProcesso = getProcessIdFromUrl();
            if (!idProcesso) {
                console.warn('hcalc: idProcesso não detectado na URL.');
                return null;
            }
            const url = `${baseUrl}/pje-comum-api/api/processos/id/${idProcesso}/partes`;
            try {
                const response = await fetch(url, { credentials: 'include' });
                if (!response.ok) {
                    throw new Error(`API retornou ${response.status}`);
                }
                const json = await response.json();
                const partes = shapePartesPayload(json);
                const processCache = window.calcPartesCache || {};
                processCache[idProcesso] = partes;
                window.calcPartesCache = processCache;

                const keys = Object.keys(window.calcPartesCache);
                if (keys.length > 5) {
                    delete window.calcPartesCache[keys[0]];
                    console.log('hcalc: cache limitado a 5 entradas, removida mais antiga');
                }

                console.log('hcalc: partes extraídas via API', partes);
                return partes;
            } catch (error) {
                console.error('hcalc: falha ao buscar partes via API', error);
                return null;
            }
        }

        async function derivePartesData() {
            if (!window.calcPartesCache) {
                window.calcPartesCache = {};
            }
            const cache = window.calcPartesCache;
            const processId = getProcessIdFromUrl();

            if (processId && cache[processId]) {
                console.log('hcalc: usando dados do cache', cache[processId]);
                return cache[processId];
            }

            if (processId) {
                const apiData = await fetchPartesViaApi();
                if (apiData) {
                    return apiData;
                }
            }

            const fallbackKey = processId ? Object.keys(cache).find((key) => key.includes(processId)) : null;
            if (fallbackKey) {
                console.log('hcalc: usando cache alternativo', cache[fallbackKey]);
                return cache[fallbackKey];
            }

            const cachedValues = Object.values(cache);
            if (cachedValues.length > 0) {
                console.log('hcalc: usando primeiro cache disponível', cachedValues[0]);
                return cachedValues[0];
            }

            console.warn('hcalc: usando parseamento do DOM (pode ser impreciso)');
            return parsePartesFromDom();
        }

        function parsePartesFromDom() {
            const rows = document.querySelectorAll('div[class*="bloco-participante"] tbody tr');
            const data = { ativo: [], passivo: [], outros: [] };
            rows.forEach((row) => {
                const text = row.innerText || '';
                const value = text.split('\n').map((line) => line.trim()).find(Boolean) || text.trim();
                if (!value) { return; }
                if (/reclamante|exequente|autor/i.test(text)) {
                    data.ativo.push({ nome: value });
                } else if (/reclamado|réu|executado/i.test(text)) {
                    data.passivo.push({ nome: value });
                } else {
                    let tipo = 'OUTRO';
                    if (/perito/i.test(text) || /perito/i.test(value)) {
                        tipo = 'PERITO';
                    }
                    data.outros.push({ nome: value, tipo });
                }
            });
            console.log('[hcalc] parsePartesFromDom: detectou', data);
            return data;
        }

        function extractPeritos(partes) {
            const outros = partes?.outros || [];
            console.log('[hcalc] extractPeritos: outros=', outros);
            const peritosEncontrados = outros.filter((part) => {
                const tipo = (part.tipo || '').toUpperCase();
                const nome = (part.nome || '').toUpperCase();
                return tipo.includes('PERITO') || nome.includes('PERITO');
            }).map((part) => part.nome);
            console.log('[hcalc] extractPeritos: peritos encontrados=', peritosEncontrados);
            return peritosEncontrados;
        }

        function ordenarComRogerioPrimeiro(nomes) {
            if (!Array.isArray(nomes) || nomes.length === 0) { return []; }
            const rogerio = [];
            const demais = [];
            nomes.forEach((nome) => {
                if (/rogerio/i.test(nome || '')) {
                    rogerio.push(nome);
                } else {
                    demais.push(nome);
                }
            });
            return [...rogerio, ...demais];
        }

        function extractAdvogadosPorReclamada(partes) {
            const map = {};
            if (!partes?.passivo) { return map; }
            partes.passivo.forEach((reclamada) => {
                const reps = reclamada.representantes || [];
                const advogados = reps.filter(rep => {
                    const tipo = (rep.tipo || '').toUpperCase();
                    return tipo.includes('ADVOGADO') || tipo.includes('OAB');
                }).map(rep => ({
                    nome: rep.nome,
                    oab: rep.oab || ''
                }));
                map[reclamada.nome] = advogados;
            });
            return map;
        }

        function extractAdvogadosDoAutor(partes) {
            const advogados = [];
            if (!partes?.ativo) { return advogados; }
            partes.ativo.forEach((reclamante) => {
                const reps = reclamante.representantes || [];
                const advs = reps.filter(rep => {
                    const tipo = (rep.tipo || '').toUpperCase();
                    return tipo.includes('ADVOGADO') || tipo.includes('OAB');
                }).map(rep => ({
                    nome: rep.nome,
                    oab: rep.oab || '',
                    nomeNormalizado: normalizarNomeParaComparacao(rep.nome)
                }));
                advogados.push(...advs);
            });
            console.log('hcalc: advogados do autor extraídos:', advogados);
            return advogados;
        }

        function extractStatusAdvogadoPorReclamada(partes) {
            const map = {};
            if (!partes?.passivo) { return map; }

            partes.passivo.forEach((reclamada) => {
                const reps = Array.isArray(reclamada.representantes) ? reclamada.representantes : [];
                const temRepresentante = reps.length > 0;

                const temIndicadorAdv = reps.some((rep) => {
                    const tipo = (rep?.tipo || '').toUpperCase();
                    const oab = (rep?.oab || rep?.numeroOab || '').toString().trim();
                    return tipo.includes('ADVOGADO') || tipo.includes('OAB') || oab !== '';
                });

                map[reclamada.nome] = temRepresentante || temIndicadorAdv;
            });

            return map;
        }

        function scheduleRefreshDetectedPartes() {
            if (typeof requestIdleCallback === 'function') {
                requestIdleCallback(() => refreshDetectedPartes(), { timeout: 3000 });
            } else {
                setTimeout(refreshDetectedPartes, 1500);
            }
        }

        return {
            isNomeRogerio,
            scheduleRefreshDetectedPartes
        };
    }

    window.hcalcOverlayPartes = { createController };
})();