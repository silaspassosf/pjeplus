'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — Módulo Detalhes e Desdobramento
// Consolidação de 1ª e 2ª ordem (agendada) e extração de desdobramento
// Requer: core.js (SisbCore)
// ═══════════════════════════════════════════════════════════════════

(function() {
    if (window.location.href.indexOf('sisbajud.cnj.jus.br') === -1 && window.location.href.indexOf('sisbajud.pdpj.jus.br') === -1) return;

    const C = window.SisbCore;

    window._sisbajudDesdobrarState = {
        qtdExtraida: 0,
        protocolos: new Set(),
        bloqueios: {}
    };

    function getCleanText(selector) {
        const element = document.querySelector(selector);
        if (element) { return element.textContent.trim(); }
        return null;
    }

    function getValueByLabel(labelText) {
        const cleanTarget = labelText.replace(/[:\s]+/g, ' ').trim().toLowerCase();

        // Tentativa 1: classe .sisbajud-label
        const labels = Array.from(document.querySelectorAll('.sisbajud-label'));
        const targetLabel = labels.find(label => {
            const txt = (label.textContent || '').replace(/[:\s]+/g, ' ').trim().toLowerCase();
            return txt.includes(cleanTarget);
        });
        if (targetLabel) {
            const parentDiv = targetLabel.closest('.col-md-3') || targetLabel.parentElement;
            const valueElement = (parentDiv && parentDiv.querySelector('.sisbajud-label-valor'))
                || targetLabel.parentElement.querySelector('.sisbajud-label-valor')
                || targetLabel.nextElementSibling;
            if (valueElement) { return valueElement.textContent.trim(); }
        }

        // Tentativa 2: qualquer elemento label/span/strong contendo o texto
        const allSpans = Array.from(document.querySelectorAll('label, span, strong, dt, div'));
        for (let i = 0; i < allSpans.length; i++) {
            const el = allSpans[i];
            const txt = (el.textContent || '').replace(/[:\s]+/g, ' ').trim().toLowerCase();
            if (txt === cleanTarget || (txt.startsWith(cleanTarget) && txt.length < cleanTarget.length + 5)) {
                const nextVal = el.nextElementSibling || (el.parentElement && el.parentElement.querySelector('.sisbajud-label-valor'));
                if (nextVal) return nextVal.textContent.trim();
            }
        }
        return null;
    }

    function extrairNomesExecutados() {
        const executados = [];
        const rowsExecutados = document.querySelectorAll('tr.element-row');
        rowsExecutados.forEach(row => {
            const nomeElement = row.querySelector('.col-reu-dados-nome-pessoa');
            const documentoElement = row.querySelector('.col-reu-dados a');
            if (nomeElement && documentoElement) {
                const nome = nomeElement.textContent.trim();
                const documento = documentoElement.textContent.trim();
                executados.push(`${nome} - [${documento}]`);
            }
        });
        return executados;
    }

    function montarHtmlExtracao(numeroProcesso, protocolosStr, repeticaoProgramada, limiteRepeticao, valorBloqueio, executados) {
        const pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"';
        let resultado = `<p ${pStyle}><strong>Dados da Teimosinha protocolada:</strong></p>`;
        resultado += `<p ${pStyle}>Número do processo: <strong>${numeroProcesso || 'Não encontrado'}</strong></p>`;
        resultado += `<p ${pStyle}>Número do protocolo: <strong>${protocolosStr || 'Não encontrado'}</strong></p>`;
        resultado += `<p ${pStyle}>Repetição programada? <strong>${repeticaoProgramada || 'Não encontrado'}</strong></p>`;
        resultado += `<p ${pStyle}>Limite da repetição: <strong>${limiteRepeticao || 'Não encontrado'}</strong></p>`;
        resultado += `<p ${pStyle}>Valor do bloqueio: <strong>${valorBloqueio ? valorBloqueio.split('\n')[0] : 'Não encontrado'}</strong></p>`;
        resultado += `<p ${pStyle}><strong>Partes alvo do bloqueio:</strong></p>`;

        if (executados && executados.length > 0) {
            executados.forEach(executado => {
                resultado += `<p ${pStyle}><strong>${executado}</strong></p>`;
            });
        } else {
            resultado += `<p ${pStyle}><strong>Nenhum executado encontrado</strong></p>`;
        }

        resultado += `<p ${pStyle}>Notas:</p>`;
        resultado += `<p ${pStyle}>-Por padrão é consultado CNPJ raiz.</p>`;
        resultado += `<p ${pStyle}>-Eventuais partes faltantes se referem a CPF ou CNPJ sem relacionamento bancário.</p>`;
        return resultado;
    }

    function extrairNumeroProcesso() {
        const porLabel = getValueByLabel('Número do Processo')
                      || getValueByLabel('Número do processo')
                      || getValueByLabel('Nº do Processo')
                      || getValueByLabel('Processo');
        if (porLabel) {
            const m = porLabel.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
            if (m) return m[0];
            const digits = porLabel.replace(/\D/g, '');
            if (digits.length === 20) return porLabel.trim();
        }

        try {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                const m = node.nodeValue && node.nodeValue.match(/\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b/);
                if (m) return m[0];
            }
        } catch(e) {}

        const inp = document.querySelector('input[placeholder*="Processo"], input[formcontrolname*="processo"]');
        if (inp && inp.value) {
            const m = inp.value.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
            if (m) return m[0];
            return inp.value.trim();
        }

        return porLabel ? porLabel.trim() : null;
    }

    function extrairNumeroProtocolo() {
        const porLabel = getValueByLabel('Número do Protocolo')
                      || getValueByLabel('Número do protocolo')
                      || getValueByLabel('Protocolo')
                      || getValueByLabel('Número da Ordem')
                      || getValueByLabel('Número da ordem')
                      || getValueByLabel('Ordem');
        if (porLabel) {
            const m = porLabel.match(/\d{8,25}/);
            if (m) return m[0];
        }

        const elProto = document.querySelector('.col-protocolo, [data-label*="protocolo"], [data-label*="Protocolo"]');
        if (elProto && elProto.textContent) {
            const m = elProto.textContent.match(/\d{8,25}/);
            if (m) return m[0];
        }

        try {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                const text = node.nodeValue || '';
                const m = text.match(/(?:[Pp]rotocolo|[Nn]úmero da [Oo]rdem)[\s:]+(\d{8,25})/);
                if (m) return m[1];
            }
        } catch(e) {}

        return porLabel ? porLabel.replace(/\D/g, '') : null;
    }

    function obterMapaDetalhar() {
        let raw = C.lerEstado('sisb_detalhar_state');
        if (!raw) return {};
        if (raw.processoNorm && !raw[raw.processoNorm]) {
            const mapa = {};
            if (!raw.timestamp || Date.now() - raw.timestamp < 24 * 60 * 60 * 1000) {
                mapa[raw.processoNorm] = raw;
            }
            return mapa;
        }
        const agora = Date.now();
        const mapaLimpo = {};
        for (const k in raw) {
            if (raw[k] && (!raw[k].timestamp || agora - raw[k].timestamp < 24 * 60 * 60 * 1000)) {
                mapaLimpo[k] = raw[k];
            }
        }
        return mapaLimpo;
    }

    function salvarMapaDetalhar(mapa) {
        C.salvarEstado('sisb_detalhar_state', mapa);
    }

    function obterOrdensProcessadas() {
        return C.lerEstado('sisb_ordens_processadas') || {};
    }

    function marcarOrdemProcessada(procNorm, protocolo) {
        const proc = obterOrdensProcessadas();
        proc[`${procNorm}_${protocolo}`] = Date.now();
        C.salvarEstado('sisb_ordens_processadas', proc);
    }

    function ordemJaProcessada(procNorm, protocolo) {
        const proc = obterOrdensProcessadas();
        return !!proc[`${procNorm}_${protocolo}`];
    }

    function extrairOrdemDetalharAuto() {
        const numeroProcesso = extrairNumeroProcesso();
        const numeroProtocolo = extrairNumeroProtocolo();

        if (!numeroProcesso || !numeroProtocolo) return;

        const procNorm = numeroProcesso.replace(/\D/g, '');

        // Não reprocessar ordem que já foi extraída
        if (ordemJaProcessada(procNorm, numeroProtocolo)) {
            return;
        }

        // Se havia um protocolo esperado definido na lista de ordens, verifica se bate
        const protoEsperado = C.lerEstado('sisb_protocolo_esperado');
        if (protoEsperado && protoEsperado !== numeroProtocolo) {
            console.log('[SisbDetalhes] Protocolo atual (' + numeroProtocolo + ') diferente do esperado (' + protoEsperado + '). Aguardando tela correta...');
            return;
        }

        if (window._sisbUltimoProtocoloProcessado === numeroProtocolo) return;

        if (window._sisbUltimoProtocolo !== numeroProtocolo) {
            window._sisbDetalharPronto = 0;
            window._sisbUltimoProtocolo = numeroProtocolo;
        }

        if (!window._sisbDetalharPronto) {
            window._sisbDetalharPronto = Date.now();
            return;
        }
        if (Date.now() - window._sisbDetalharPronto < 1000) {
            return;
        }

        const mapa = obterMapaDetalhar();
        const st = mapa[procNorm];

        // SEGUNDA ORDEM DO MESMO PROCESSO (detectou nova extração com outro protocolo):
        if (st && st.protocolo1 && st.protocolo1 !== numeroProtocolo) {
            const protocolosStr = st.protocolo1 + ', ' + numeroProtocolo;

            let textoFinal = st.primeiroTextoHtml || '';
            if (textoFinal && /(?:Número do(?:s)? protocolo(?:s)?:\s*<strong>)(.*?)(<\/strong>)/i.test(textoFinal)) {
                textoFinal = textoFinal.replace(
                    /(Número do(?:s)? protocolo(?:s)?:\s*<strong>)(.*?)(<\/strong>)/i,
                    `Número dos protocolos: <strong>${protocolosStr}</strong>`
                );
            } else {
                const repeticaoProgramada = getValueByLabel('Repetição programada?') || getValueByLabel('Repetição programada') || st.repeticaoProgramada || '';
                const limiteRepeticao = getValueByLabel('Data limite da repetição') || st.limiteRepeticao || '';
                const valorBloqueio = getCleanText('td[data-label="valorBloquear:"]') || getCleanText('td[data-label*="valorBloquear"]') || getCleanText('td.cdk-column-valorBloquear') || st.valorBloqueio || '';
                const executados = extrairNomesExecutados();
                textoFinal = montarHtmlExtracao(
                    st.processo || numeroProcesso,
                    protocolosStr,
                    repeticaoProgramada,
                    limiteRepeticao,
                    valorBloqueio,
                    executados.length ? executados : (st.executados || [])
                );
            }

            if (C.copyToClipboardHtml(textoFinal)) {
                C.mostrarToast('2 ordens consolidadas e copiadas! Protocolos: ' + protocolosStr, 'ok');
                window._sisbUltimoProtocoloProcessado = numeroProtocolo;
                marcarOrdemProcessada(procNorm, st.protocolo1);
                marcarOrdemProcessada(procNorm, numeroProtocolo);
                C.salvarEstado('sisb_protocolo_esperado', null);
                delete mapa[procNorm];
                salvarMapaDetalhar(mapa);
            } else {
                C.mostrarToast('Falha ao copiar html consolidado', 'erro');
            }
        }
        // AINDA É A PRIMEIRA ORDEM DO MESMO PROCESSO:
        else if (st && st.protocolo1 === numeroProtocolo) {
            window._sisbUltimoProtocoloProcessado = numeroProtocolo;
            marcarOrdemProcessada(procNorm, numeroProtocolo);
            C.salvarEstado('sisb_protocolo_esperado', null);
        }
        // PRIMEIRA ORDEM (NOVO PROCESSO):
        else {
            const repeticaoProgramada = getValueByLabel('Repetição programada?') || getValueByLabel('Repetição programada') || '';
            const limiteRepeticao = getValueByLabel('Data limite da repetição') || '';
            const valorBloqueio = getCleanText('td[data-label="valorBloquear:"]') || getCleanText('td[data-label*="valorBloquear"]') || getCleanText('td.cdk-column-valorBloquear') || '';
            const executados = extrairNomesExecutados();

            const textoBase = montarHtmlExtracao(numeroProcesso, numeroProtocolo, repeticaoProgramada, limiteRepeticao, valorBloqueio, executados);

            mapa[procNorm] = {
                processo: numeroProcesso,
                processoNorm: procNorm,
                protocolo1: numeroProtocolo,
                primeiroTextoHtml: textoBase,
                repeticaoProgramada: repeticaoProgramada,
                limiteRepeticao: limiteRepeticao,
                valorBloqueio: valorBloqueio,
                executados: executados,
                timestamp: Date.now()
            };

            salvarMapaDetalhar(mapa);
            window._sisbUltimoProtocoloProcessado = numeroProtocolo;
            marcarOrdemProcessada(procNorm, numeroProtocolo);
            C.salvarEstado('sisb_protocolo_esperado', null);

            C.mostrarToast('1ª ordem guardada (' + numeroProtocolo + '). Aguardando 2ª ordem...', 'aviso');
        }
    }

    function extrairDesdobrarHtml() {
        var panels = document.querySelectorAll('mat-expansion-panel');
        if (!panels || panels.length === 0) return false;

        var encontrouAlgum = false;
        panels.forEach(function(panel) {
            var inputVal = panel.querySelector('input[formcontrolname="valorDesbloqueio"]');
            if (!inputVal) return;

            var valNum = parseFloat(inputVal.value.replace(/\./g, '').replace(',', '.'));
            if (isNaN(valNum) || valNum <= 0) return;

            var nomePessoaEl = panel.querySelector('.col-reu-dados-nome-pessoa');
            var docEl = panel.querySelector('.col-reu-dados a');
            var nomeCompleto = '';

            if (nomePessoaEl && docEl) {
                nomeCompleto = nomePessoaEl.textContent.trim() + ' [' + docEl.textContent.trim() + ']';
            } else if (nomePessoaEl) {
                nomeCompleto = nomePessoaEl.textContent.trim();
            } else {
                nomeCompleto = 'Desconhecido';
            }

            if (!window._sisbajudDesdobrarState.bloqueios[nomeCompleto]) {
                window._sisbajudDesdobrarState.bloqueios[nomeCompleto] = 0;
            }
            window._sisbajudDesdobrarState.bloqueios[nomeCompleto] += valNum;
            encontrouAlgum = true;
        });

        if (encontrouAlgum) {
            window._sisbajudDesdobrarState.qtdExtraida++;
            var proto = extrairNumeroProtocolo();
            if (proto) window._sisbajudDesdobrarState.protocolos.add(proto);
            C.mostrarToast('Dados extraídos (' + window._sisbajudDesdobrarState.qtdExtraida + ')', 'ok');
            return true;
        } else {
            C.mostrarToast('Nenhum valor válido para extrair', 'aviso');
            return false;
        }
    }

    function injetarBotoesDesdobrar() {
        if (document.getElementById('btn-sisb-desdobrar-extrair')) return;

        var container = document.getElementById('pjetools-sisb-desdobrar-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'pjetools-sisb-desdobrar-container';
            container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;display:flex;flex-direction:column;gap:8px;';
            document.body.appendChild(container);
        }

        var btnExtrair = C.criarBotao('btn-sisb-desdobrar-extrair', '📄 Extrair dados', '#1e88e5', async function() {
            btnExtrair.textContent = 'Extraindo...';
            btnExtrair.style.background = '#f39c12';

            await C.sleep(300);

            var ok = extrairDesdobrarHtml();
            if (ok) {
                btnExtrair.style.display = 'none';

                var btnProx = document.getElementById('btn-sisb-desdobrar-prox');
                if (!btnProx) {
                    btnProx = C.criarBotao('btn-sisb-desdobrar-prox', 'Extrair próxima', '#f39c12', async function() {
                        btnProx.textContent = 'Extraindo...';
                        await C.sleep(300);
                        extrairDesdobrarHtml();
                        btnProx.textContent = 'Extrair próxima';
                        var btnFin = document.getElementById('btn-sisb-desdobrar-fin');
                        if (btnFin) btnFin.textContent = '✅ Finalizar (' + window._sisbajudDesdobrarState.qtdExtraida + ')';
                    });
                    container.appendChild(btnProx);
                } else {
                    btnProx.style.display = 'block';
                }

                var btnFin = document.getElementById('btn-sisb-desdobrar-fin');
                if (!btnFin) {
                    btnFin = C.criarBotao('btn-sisb-desdobrar-fin', '✅ Finalizar (' + window._sisbajudDesdobrarState.qtdExtraida + ')', '#27ae60', function() {
                        var _st = window._sisbajudDesdobrarState;
                        var protocolosStr = Array.from(_st.protocolos).join(', ');
                        var pJustifyImp = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"';

                        var saida = "";
                        saida += "<p " + pJustifyImp + ">Ordens com bloqueio: <strong>" + (protocolosStr || "Nenhuma") + "</strong></p>";
                        saida += "<p " + pJustifyImp + ">Discriminação de partes e respectivos valores totais<u> já transferidos à conta do juízo</u>:</p>";

                        var somaTotal = 0;
                        for (var nome in _st.bloqueios) {
                            var num = _st.bloqueios[nome];
                            somaTotal += num;
                            var valFormatado = num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                            saida += "<p " + pJustifyImp + ">-" + nome + " - R$ " + valFormatado + "</p>";
                        }

                        var totalFormatado = somaTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        saida += "<p " + pJustifyImp + ">(total de bloqueios esperado na conta judicial, sem considerar atualizações = R$ <strong>" + totalFormatado + "</strong>)<br><br><br data-cke-filler=\"true\"></p>";

                        var okCopy = C.copyToClipboardHtml(saida);
                        if (okCopy) {
                            btnFin.textContent = 'Copiado!';
                            window._sisbajudDesdobrarState.qtdExtraida = 0;
                            window._sisbajudDesdobrarState.protocolos = new Set();
                            window._sisbajudDesdobrarState.bloqueios = {};
                            setTimeout(function() {
                                btnFin.style.display = 'none';
                                btnProx.style.display = 'none';
                                btnExtrair.textContent = '📄 Extrair dados';
                                btnExtrair.style.background = '#1e88e5';
                                btnExtrair.style.display = 'block';
                            }, 2000);
                        } else {
                            alert('Falha ao copiar html.');
                        }
                    });
                    container.appendChild(btnFin);
                } else {
                    btnFin.style.display = 'block';
                    btnFin.textContent = '✅ Finalizar (' + window._sisbajudDesdobrarState.qtdExtraida + ')';
                }
            } else {
                btnExtrair.textContent = 'Falhou (tente denovo)';
                setTimeout(function(){
                    btnExtrair.textContent = '📄 Extrair dados';
                    btnExtrair.style.background = '#1e88e5';
                }, 2000);
            }
        });

        container.appendChild(btnExtrair);
    }

    window.SisbDetalhes = {
        getCleanText: getCleanText,
        getValueByLabel: getValueByLabel,
        extrairNomesExecutados: extrairNomesExecutados,
        montarHtmlExtracao: montarHtmlExtracao,
        extrairNumeroProcesso: extrairNumeroProcesso,
        extrairNumeroProtocolo: extrairNumeroProtocolo,
        obterMapaDetalhar: obterMapaDetalhar,
        salvarMapaDetalhar: salvarMapaDetalhar,
        obterOrdensProcessadas: obterOrdensProcessadas,
        marcarOrdemProcessada: marcarOrdemProcessada,
        ordemJaProcessada: ordemJaProcessada,
        extrairOrdemDetalharAuto: extrairOrdemDetalharAuto,
        extrairDesdobrarHtml: extrairDesdobrarHtml,
        injetarBotoesDesdobrar: injetarBotoesDesdobrar
    };

})();
