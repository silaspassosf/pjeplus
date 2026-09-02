(function () {
    'use strict';

    // Estado global para acumular ordens e valores
    window._sisbajudState = window._sisbajudState || {
        qtdExtraida: 0,
        protocolos: new Set(),
        bloqueios: {} // formato: { "Nome da Parte": 123.45 }
    };

    function encontrarDocIdSisbajud() {
        var spans = document.querySelectorAll('span');
        for (var i = 0; i < spans.length; i++) {
            if (spans[i].innerText && spans[i].innerText.includes('Número do documento:')) {
                var match = spans[i].innerText.match(/Número do documento:\s*(\d+)/i);
                if (match) return match[1];
            }
        }
        return null;
    }

    // Mesma detecção do hcalc-overlay.js: o Id curto (alafanumérico, ex.: 0015c20)
    // vem do título do documento ativo — <mat-card-title>Id 0015c20 - calculo ...</mat-card-title>.
    function detectarIdDocumentoTituloSisbajud() {
        var titulos = document.querySelectorAll('mat-card-title, .mat-card-title');
        for (var i = 0; i < titulos.length; i++) {
            var txt = (titulos[i].textContent || '').trim();
            var m = txt.match(/Id\s+([A-Za-z0-9]+)\s*[-–—]/i);
            if (m) return m[1].trim();
        }
        return null;
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
        // Preferência: Id curto alfanumérico do documento ativo (mat-card-title "Id xxxxx - ..."),
        // mesmo padrão aceito por pjeExtrairApi/carregarPlanilhaPorUidBotao.
        const idCurto = detectarIdDocumentoTituloSisbajud();
        const docId = idCurto || encontrarDocIdSisbajud();
        if (!docId) {
            console.error('[extrairResumoSisbajud] Id do documento não detectado (mat-card-title ou span).');
            return false;
        }
        console.log('[extrairResumoSisbajud] Id do documento detectado:', docId, idCurto ? '(curto, via mat-card-title)' : '(longo, via span)');
        let res;
        try {
            if (typeof window.pjeExtrairApi !== 'function') {
                throw new Error('window.pjeExtrairApi não está disponível');
            }
            // A chamada permanece igual à funcional:
            // o número extraído do span é passado diretamente.
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
                    
                    btnExtrairProx.addEventListener('click', function() {
                        btnExtrairProx.innerText = 'Extraindo...';
                        window.executarSisbajudPJe().then(function() {
                            var _s = window._sisbajudState;
                            btnExtrairProx.innerText = 'Extrair próxima';
                            btnFinalizar.innerText = '✅ Finalizar (' + _s.qtdExtraida + ')';
                        });
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
                        saida += "<p " + pJustifyImp + ">(total de bloqueios esperado na conta judicial, sem considerar atualizações = R$ <strong>" + totalFormatado + "</strong>)<br><br><br data-cke-filler=\"true\"></p>";
                        
                        var okCopy = copyToClipboardHtml(saida);
                        if (okCopy) {
                            btnFinalizar.innerText = 'Copiado!';
                            window._sisbajudState.qtdExtraida = 0;
                            window._sisbajudState.protocolos = new Set();
                            window._sisbajudState.bloqueios = {};
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
