console.log('[PJeT][sisbpje] Módulo carregado.');
(function () {
    'use strict';

    // Estado global para acumular ordens e valores
    window._sisbajudState = window._sisbajudState || {
        qtdExtraida: 0,
        protocolos: new Set(),
        documentosExtraidos: new Set(),
        bloqueios: {} // formato: { "Nome da Parte": 123.45 }
    };

    function detectarDocIdAtivoSisbajud() {
        // 1. Título do cabeçalho do documento ativo no viewer do PJe
        var titulosCabecalho = document.querySelectorAll(
            'pje-cabecalho-documento mat-card-title, .cabecalho-conteudo .mat-card-title, mat-card-title, .mat-card-title'
        );
        for (var i = 0; i < titulosCabecalho.length; i++) {
            var txt = (titulosCabecalho[i].textContent || '').trim();
            var m = txt.match(/Id\s+([A-Za-z0-9]+)\s*[-–—]/i);
            if (m) return { id: m[1].trim(), origem: 'mat-card-title' };
        }

        // 2. Item selecionado/destacado na timeline
        var highlighted = document.querySelector('li.tl-item-container[style*="rgb(255, 247, 214)"]')
            || document.querySelector('li.tl-item-container.pjetools-destaque')
            || document.querySelector('li.tl-item-container.active')
            || document.querySelector('li.tl-item-container[class*="selecionado"]');
        if (highlighted) {
            var link = highlighted.querySelector('a.tl-documento:not([target="_blank"])');
            if (link) {
                var ml = link.textContent.trim().match(/\s-\s([A-Za-z0-9]+)$/);
                if (ml) return { id: ml[1].trim(), origem: 'timeline-highlighted' };
            }
        }

        // 3. Parâmetro na URL (ex: ?documentoId=...)
        var params = new URLSearchParams(window.location.search);
        var porUrl = params.get('documentoId') || params.get('docId');
        if (porUrl) return { id: porUrl.trim(), origem: 'url' };

        // 4. Span com 'Número do documento:'
        var spans = document.querySelectorAll('span');
        for (var j = 0; j < spans.length; j++) {
            if (spans[j].innerText && spans[j].innerText.includes('Número do documento:')) {
                var ms = spans[j].innerText.match(/Número do documento:\s*(\d+)/i);
                if (ms) return { id: ms[1].trim(), origem: 'span-numero' };
            }
        }
        return null;
    }

    function detectarIdDocumentoTituloSisbajud() {
        var det = detectarDocIdAtivoSisbajud();
        return det ? det.id : null;
    }

    // Usa carregarPlanilhaPorUidBotao (hcalc-overlay.js) por importação:
    // extrai a planilha via API sem digitação — o Id curto é lido automaticamente
    // do mat-card-title "Id xxxxx - ..." do documento ativo.
    window.extrairPlanilhaPorSpanSisbajud = async function () {
        if (typeof window.carregarPlanilhaPorUidBotao !== 'function') {
            console.error('[sisbpje] window.carregarPlanilhaPorUidBotao indisponível — verifique se hcalc-overlay.js (hcalc.user.js) está carregado antes deste módulo.');
            return false;
        }
        try {
            var idDoc = (typeof window.hcalcDetectarIdDocumento === 'function')
                ? window.hcalcDetectarIdDocumento()
                : detectarIdDocumentoTituloSisbajud();
            console.log('[sisbpje] Id do documento detectado no título:', idDoc);
            if (!idDoc) {
                console.error('[sisbpje] Nenhum mat-card-title "Id xxxxx - ..." encontrado na página.');
                return false;
            }
            const dados = await window.carregarPlanilhaPorUidBotao(idDoc);
            console.log('[sisbpje] Planilha extraída via API:', dados);
            return dados;
        } catch (e) {
            console.error('[sisbpje] Falha ao extrair planilha via API:', e.message);
            return false;
        }
    };

    window.extrairResumoSisbajud = async function (opts) {
        console.log('[extrairResumoSisbajud] Iniciando extração...');
        opts = opts || {};

        const det = detectarDocIdAtivoSisbajud();
        if (!det || !det.id) {
            console.error('[extrairResumoSisbajud] Id do documento não detectado (mat-card-title, timeline ou span).');
            return false;
        }
        const docId = det.id;
        console.log('[extrairResumoSisbajud] Id do documento detectado:', docId, '(' + det.origem + ')');

        // Proteção contra extração consecutiva acidental do mesmo documento
        if (window._sisbajudState.documentosExtraidos && window._sisbajudState.documentosExtraidos.has(docId)) {
            console.warn('[extrairResumoSisbajud] Documento ' + docId + ' já foi extraído anteriormente nesta sessão.');
            if (typeof window.alert === 'function') {
                alert('Atenção: O documento Id ' + docId + ' já foi extraído nesta sessão.\nSelecione outro documento na timeline antes de clicar em "Extrair próxima".');
            }
            return false;
        }

        let res;
        try {
            if (typeof window.pjeExtrairApi !== 'function') {
                throw new Error('window.pjeExtrairApi não está disponível');
            }
            res = await window.pjeExtrairApi(docId, opts);
            console.log('[extrairResumoSisbajud] Resultado bruto da API:', res);
        } catch (e) {
            console.error('[extrairResumoSisbajud] Erro na chamada da API:', e);
            return false;
        }
        if (!res || !res.sucesso) {
            console.error('[extrairResumoSisbajud] API retornou falha:', res);
            return false;
        }
        const textoDocumento = String(res.conteudo_bruto || res.conteudo || '').trim();
        if (!textoDocumento) {
            console.error('[extrairResumoSisbajud] API retornou sucesso, mas sem texto.', res);
            return false;
        }
        console.log('[extrairResumoSisbajud] Texto bruto recebido:', textoDocumento);
        const textoFlat = textoDocumento
            .replace(/\r\n|\r|\n/g, ' ')
            .replace(/\s{2,}/g, ' ')
            .trim();
        console.log('[extrairResumoSisbajud] Texto planificado:', textoFlat);
        let protocolo = '';
        const protocoloMatch = textoFlat.match(/Número do protocolo\s*:\s*(\d+)/i) ||
            textoFlat.match(/protocolo\s*[:#]?\s*(\d{10,20})/i) ||
            textoFlat.match(/\b(\d{14,16})\b/);
        if (protocoloMatch) {
            protocolo = protocoloMatch[1] || protocoloMatch[0];
            window._sisbajudState.protocolos.add(protocolo);
        }
        // Regex do standalone, preservada
        const blockRegex = /(?:\d{11}|\d{14}):\s*(.{3,100}?)\s*\|?\s*R\$\s*([\d\.,]+)/gmi;
        let match;
        let encontrouBloco = false;
        while ((match = blockRegex.exec(textoFlat)) !== null) {
            encontrouBloco = true;
            const nome = match[1]
                .trim()
                .replace(/\s+/g, ' ');
            const valorStr = match[2].trim();
            if (valorStr === '0' || valorStr === '0,00' || valorStr === '0.00') {
                continue;
            }
            const valorNum = parseFloat(valorStr.replace(/\./g, '').replace(',', '.'));
            if (!Number.isNaN(valorNum)) {
                window._sisbajudState.bloqueios[nome] = (window._sisbajudState.bloqueios[nome] || 0) + valorNum;
            }
        }
        if (!encontrouBloco) {
            console.warn('[extrairResumoSisbajud] Nenhum bloco de valor reconhecido.');
            console.warn('[extrairResumoSisbajud] Regex utilizada:', blockRegex);
            console.warn('[extrairResumoSisbajud] Texto analisado:', textoFlat);
        }
        window._sisbajudState.qtdExtraida++;
        window._sisbajudState.documentosExtraidos = window._sisbajudState.documentosExtraidos || new Set();
        window._sisbajudState.documentosExtraidos.add(docId);
        console.log('[extrairResumoSisbajud] Ordem processada:', protocolo, window._sisbajudState);
        return true;
    };

    function copyToClipboardHtml(content) {
        var container = document.createElement('div');
        container.innerHTML = content;
        container.style.position = 'absolute';
        container.style.left = '-9999px';
        document.body.appendChild(container);
        
        var range = document.createRange();
        range.selectNodeContents(container);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        
        try {
            var success = document.execCommand('copy');
            document.body.removeChild(container);
            selection.removeAllRanges();
            return success;
        } catch (err) {
            if (document.body.contains(container)) document.body.removeChild(container);
            return false;
        }
    }

    window.executarSisbajudPJe = async function () {
        // Indicador de loading na UI oficial por uns instantes
        var btnAcaoOficial = document.getElementById('btnSisbajud');
        if (btnAcaoOficial) {
            btnAcaoOficial.innerText = 'Extraindo...';
            btnAcaoOficial.style.backgroundColor = '#f39c12';
        }
        
        try {
            var ok = await window.extrairResumoSisbajud();
            if (ok) {
                var st = window._sisbajudState;
                if (btnAcaoOficial) {
                    btnAcaoOficial.innerText = '💸 Sisbajud';
                    btnAcaoOficial.style.backgroundColor = '#1e88e5';
                }
                
                var containerEx = document.getElementById('sisbajud-botoes-extras');
                if (!containerEx) {
                    containerEx = document.createElement('div');
                    containerEx.id = 'sisbajud-botoes-extras';
                    containerEx.style.cssText = 'position:fixed;bottom:170px;right:230px;z-index:99999;display:flex;flex-direction:column;gap:5px;';
                    document.body.appendChild(containerEx);
                    
                    var btnExtrairProx = document.createElement('button');
                    btnExtrairProx.id = 'btnSisbajudExtrairProx';
                    btnExtrairProx.innerText = 'Extrair próxima';
                    btnExtrairProx.title = 'Extrai o documento desta tela e acumula na memória';
                    btnExtrairProx.style.cssText = 'padding:10px 15px;background:#f39c12;color:#fff;border:2px solid #333;border-radius:6px;cursor:pointer;font-weight:bold;font-size:12px;box-shadow:0 8px 32px rgba(0,0,0,.25);transition:opacity .2s;';
                    
                    var btnFinalizar = document.createElement('button');
                    btnFinalizar.id = 'btnSisbajudFinalizar';
                    btnFinalizar.innerText = '✅ Finalizar (' + st.qtdExtraida + ')';
                    btnFinalizar.title = 'Copiar resumo consolidado para área de transferência';
                    btnFinalizar.style.cssText = 'padding:10px 15px;background:#27ae60;color:#fff;border:2px solid #333;border-radius:6px;cursor:pointer;font-weight:bold;font-size:12px;box-shadow:0 8px 32px rgba(0,0,0,.25);transition:opacity .2s;';
                    
                    btnExtrairProx.addEventListener('click', async function() {
                        btnExtrairProx.disabled = true;
                        btnExtrairProx.innerText = 'Extraindo...';
                        try {
                            var ok = await window.extrairResumoSisbajud();
                            var _s = window._sisbajudState;
                            if (ok) {
                                btnExtrairProx.innerText = 'Extrair próxima';
                                btnFinalizar.innerText = '✅ Finalizar (' + _s.qtdExtraida + ')';
                            } else {
                                btnExtrairProx.innerText = 'Falhou (tente novamente)';
                                setTimeout(function() {
                                    btnExtrairProx.innerText = 'Extrair próxima';
                                }, 2500);
                            }
                        } catch (err) {
                            console.error('[Sisbajud] Erro no clique de Extrair próxima:', err);
                            btnExtrairProx.innerText = 'Erro';
                            setTimeout(function() {
                                btnExtrairProx.innerText = 'Extrair próxima';
                            }, 2000);
                        } finally {
                            btnExtrairProx.disabled = false;
                        }
                    });
                    
                    btnFinalizar.addEventListener('click', function() {
                        var _st = window._sisbajudState;
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
                        saida += "<p " + pJustifyImp + ">(total de bloqueios esperado na conta judicial, sem considerar atualizações = R$ <strong>" + totalFormatado + "</strong>)</p>";

                        // Limpa linhas vazias antes e depois do texto
                        saida = saida
                            .replace(/^(\s|<br\s*\/?>|&nbsp;|<p[^>]*>\s*<\/p>)+/i, '')
                            .replace(/(\s|<br\s*\/?>|&nbsp;|<p[^>]*>\s*<\/p>)+$/i, '');

                        var okCopy = copyToClipboardHtml(saida);
                        if (okCopy) {
                            btnFinalizar.innerText = 'Copiado!';
                            window._sisbajudState.qtdExtraida = 0;
                            window._sisbajudState.protocolos = new Set();
                            window._sisbajudState.bloqueios = {};
                            if (window._sisbajudState.documentosExtraidos) {
                                window._sisbajudState.documentosExtraidos.clear();
                            }
                            setTimeout(function() {
                                containerEx.remove();
                            }, 2000);
                        } else {
                            alert('Falha ao copiar html. Verifique o console.');
                            console.log(saida);
                        }
                    });
                    
                    containerEx.appendChild(btnExtrairProx);
                    containerEx.appendChild(btnFinalizar);
                } else {
                    // Já existe
                    var btnFin = document.getElementById('btnSisbajudFinalizar');
                    if (btnFin) btnFin.innerText = '✅ Finalizar (' + window._sisbajudState.qtdExtraida + ')';
                }
            } else {
                if (btnAcaoOficial) {
                    btnAcaoOficial.innerText = 'Falhou';
                    setTimeout(function(){ btnAcaoOficial.innerText = '💸 Sisbajud'; btnAcaoOficial.style.backgroundColor = '#1e88e5'; }, 2000);
                }
            }
        } catch (e) {
            console.error('[Sisbajud] Erro no executarSisbajudPJe:', e);
            if (btnAcaoOficial) {
                btnAcaoOficial.innerText = 'Erro';
                setTimeout(function(){ btnAcaoOficial.innerText = '💸 Sisbajud'; btnAcaoOficial.style.backgroundColor = '#1e88e5'; }, 2000);
            }
        }
    };

})();
