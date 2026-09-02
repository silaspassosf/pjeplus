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

    window.extrairResumoSisbajud = async function (opts) {
        console.log('[extrairResumoSisbajud] Iniciando extração...');

        var res = null;
        var docId = encontrarDocIdSisbajud();

        if (docId) {
            console.log('[extrairResumoSisbajud] Número do documento detectado no span:', docId, '- Tentando via API...');
            if (window.pjeExtrairApi) {
                res = await window.pjeExtrairApi(docId, opts);
            }
        }

        // Fallback para DOM
        if (!res || !res.sucesso) {
            console.log('[extrairResumoSisbajud] Fallback para extração por DOM...');
            if (window.pjeExtrair) {
                res = await window.pjeExtrair(opts);
            }
        }

        if (!res || !res.sucesso) {
            console.error('[extrairResumoSisbajud] Falha na extração:', res);
            alert('Falha ao tentar ler o conteúdo do documento.');
            return false;
        }

        var textoDocumento = res.conteudo || res.conteudo_bruto;

        // Remove quebras de linha
        var textoFlat = textoDocumento.replace(/\n|\r/g, ' ').replace(/\s{2,}/g, ' ');

        var protocolo = '';
        var protocoloMatch = textoFlat.match(/Número do protocolo:\s*(\d+)/i) ||
            textoFlat.match(/(\d{14,16})/);
        if (protocoloMatch) protocolo = protocoloMatch[1] || protocoloMatch[0];

        // Regex
        var blockRegex = /(?:\d{11}|\d{14}):\s*(.{3,100}?)\s*\|?\s*R\$\s*([\d\.,]+)/gmi;
        var match;

        while ((match = blockRegex.exec(textoFlat)) !== null) {
            var nome = match[1].trim();
            var valorStr = match[2].trim();

            if (valorStr !== '0,00' && valorStr !== '0.00' && valorStr !== '0') {
                var valorNum = parseFloat(valorStr.replace(/\./g, '').replace(',', '.'));
                if (!isNaN(valorNum)) {
                    window._sisbajudState.bloqueios[nome] = (window._sisbajudState.bloqueios[nome] || 0) + valorNum;
                }
            }
        }

        if (protocolo) window._sisbajudState.protocolos.add(protocolo);
        window._sisbajudState.qtdExtraida++;

        console.log('[extrairResumoSisbajud] Ordem ' + protocolo + ' processada e valores acumulados.');
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
                    if (btnFin) btnFin.innerText = '✅ Finalizar (' + st.qtdExtraida + ')';
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
