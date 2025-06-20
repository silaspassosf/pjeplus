// ==UserScript==
// @name         Triagem Petição Inicial Trabalhista - Zona Sul SP
// @namespace    http://tampermonkey.net/
// @version      3.2
// @description  Análise automatizada de petição inicial trabalhista para competência territorial e valor da causa
// @author       Assistente
// @match        https://pje.trt2.jus.br/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    
    // Carrega PDF.js
    function loadPdfJs(callback) {
        if (window.pdfjsLib) return callback();
        let script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        script.onload = callback;
        document.head.appendChild(script);
    }

    let textoExtraidoGlobal = '';

    function createUI() {
        console.log('Criando interface...');
        
        let existing = document.getElementById('trg-peticao-root');
        if (existing) existing.remove();
        
        let selectors = [
            'i.fa.fa-plus-circle.icone-acoes-cadastro',
            'i.fa-plus-circle.icone-acoes-cadastro', 
            'i.icone-acoes-cadastro',
            'i.fa.fa-plus-circle',
            '[class*="icone-acoes-cadastro"]'
        ];
        
        let acaoIcon = null;
        for (let selector of selectors) {
            acaoIcon = document.querySelector(selector);
            if (acaoIcon) {
                console.log('Icone encontrado:', selector);
                break;
            }
        }
        
        let root = document.createElement('div');
        root.id = 'trg-peticao-root';
        
        if (acaoIcon) {
            root.style = 'position:absolute;right:100%;top:0;margin-right:20px;z-index:10000;background:#1e3a8a !important;color:white;border:2px solid #1e40af;border-radius:8px;padding:16px;box-shadow:0 4px 16px rgba(0,0,0,0.18);font-family:Segoe UI,Arial,sans-serif;max-width:400px;min-width:350px;box-sizing:border-box;pointer-events:auto;';
            
            let parentElement = acaoIcon.parentElement;
            if (getComputedStyle(parentElement).position === 'static') {
                parentElement.style.position = 'relative';
            }
            
            parentElement.appendChild(root);
            console.log('Interface inserida a esquerda do icone');
        } else {
            root.style = 'position:fixed;top:30px;right:30px;z-index:99999;background:#1e3a8a !important;color:white;border:2px solid #1e40af;border-radius:8px;padding:16px;box-shadow:0 4px 16px rgba(0,0,0,0.18);font-family:Segoe UI,Arial,sans-serif;max-width:420px;box-sizing:border-box;pointer-events:auto;';
            document.body.appendChild(root);
            console.log('Interface em posicao fixa (fallback)');
        }
        
        root.innerHTML = `
            <div style="background:#1e3a8a !important;border-radius:8px;padding:16px;box-sizing:border-box;">
                <b style="font-size:18px;color:white;display:block;margin-bottom:5px;">Triagem Petição Inicial - Zona Sul SP</b>
                <button id="trg-close" style="background:#dc2626;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;float:right;margin-top:-30px;">Fechar</button>
                <div style="clear:both;margin-top:10px;"></div>
                <div id="trg-status" style="margin:10px 0 12px 0;color:#e5e7eb;">Aguardando upload do PDF...</div>
                <input type="file" id="trg-file" accept="application/pdf" style="margin-bottom:10px;width:100%;padding:8px;border-radius:4px;border:1px solid #3b82f6;background:white;color:black;box-sizing:border-box;">
                <button id="trg-save-txt" style="display:none;margin-bottom:8px;background:#3b82f6;color:white;border:none;padding:8px 12px;border-radius:4px;cursor:pointer;width:100%;box-sizing:border-box;">Salvar texto extraído (.txt)</button>
                <div id="trg-progress" style="margin:8px 0 8px 0;font-size:13px;color:#bfdbfe;"></div>
                <div id="trg-table" style="color:white;background:#1e3a8a !important;"></div>
            </div>
        `;
        
        document.getElementById('trg-close').onclick = function() { root.remove(); };
        
        document.getElementById('trg-file').onchange = async function() {
            let file = this.files[0];
            if (!file) return;
            
            let status = document.getElementById('trg-status');
            let progress = document.getElementById('trg-progress');
            let btnSaveTxt = document.getElementById('trg-save-txt');
            
            status.textContent = 'Extraindo o PDF...';
            progress.textContent = '';
            btnSaveTxt.style.display = 'none';
            
            try {
                let texto = await extrairTextoPDF(file, (pg, total) => {
                    progress.textContent = `Extraindo página ${pg} de ${total}...`;
                });
                
                textoExtraidoGlobal = texto;
                status.textContent = 'PDF extraído. Analisando...';
                progress.textContent = '';
                
                let alertas = [];
                for (let a of analises) {
                    let result = a.func(texto);
                    if (result) {
                        alertas.push({nome: a.nome, result});
                    }
                }
                
                status.textContent = 'Análise completa.';
                mostrarTabelaAlertas(alertas);
                
                btnSaveTxt.style.display = 'block';
                btnSaveTxt.onclick = function() {
                    const blob = new Blob([textoExtraidoGlobal], {type: 'text/plain'});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'texto_extraido_peticao.txt';
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(() => {
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                    }, 100);
                };
                
            } catch (e) {
                status.textContent = 'Erro ao extrair/analisar o PDF: ' + e.message;
                console.error('Erro:', e);
            }
        };
        
        console.log('Interface criada com sucesso!');
    }

    function tryCreateInterface() {
        if (document.getElementById('trg-peticao-root')) return true;
        
        let selectors = [
            'i.fa.fa-plus-circle.icone-acoes-cadastro',
            'i.fa-plus-circle.icone-acoes-cadastro',
            'i.icone-acoes-cadastro',
            'i.fa.fa-plus-circle'
        ];
        
        for (let selector of selectors) {
            if (document.querySelector(selector)) {
                console.log('Icone encontrado, criando interface...');
                createUI();
                return true;
            }
        }
        return false;
    }

    function normalizarCEP(cep) {
        return cep.replace(/[^0-9]/g, '');
    }

    function validarCEP(cep) {
        const n = parseInt(cep, 10);
        if (cep.length !== 8 || isNaN(n)) return false;
        const faixas = [
            [4307000, 4314999], [4316000, 4477999], [4603000, 4620999],
            [4624000, 4703999], [4708000, 4967999], [5640000, 5642999],
            [5657000, 5665999], [5692000, 5692999], [5703000, 5743999],
            [5745000, 5750999], [5752000, 5895999]
        ];
        return faixas.some(([ini, fim]) => n >= ini && n <= fim);
    }

    async function extrairTextoPDF(file, onProgress) {
        return new Promise((resolve, reject) => {
            let reader = new FileReader();
            reader.onload = async function() {
                try {
                    let pdf = await window.pdfjsLib.getDocument({data: new Uint8Array(reader.result)}).promise;
                    let texto = '';
                    for (let i = 1; i <= pdf.numPages; i++) {
                        let page = await pdf.getPage(i);
                        let content = await page.getTextContent();
                        texto += content.items.map(item => item.str).join(' ') + '\n';
                        if (onProgress) onProgress(i, pdf.numPages);
                    }
                    resolve(texto);
                } catch (e) {
                    reject(e);
                }
            };
            reader.onerror = reject;
            reader.readAsArrayBuffer(file);
        });
    }

    function analisarCompetenciaTerritorial(texto) {
        let ceps_do_reclamante = [];
        let contextos_reclamante = [
            /reclamante[\s\S]{0,300}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
            /residente[\s\S]{0,100}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
            /domiciliad[ao][\s\S]{0,100}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
            /RESIDENTE E DOMICILIADA[\s\S]{0,100}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi,
            /OUTORGANTE[\s\S]{0,200}?CEP:?\s*(\d{5}\s?\d{3})/gi
        ];
        
        for (let regex of contextos_reclamante) {
            let match;
            while ((match = regex.exec(texto)) !== null) {
                let cep = normalizarCEP(match[1]);
                ceps_do_reclamante.push(cep);
            }
        }
        
        ceps_do_reclamante = [...new Set(ceps_do_reclamante)];
        
        let ceps_prioritarios = [];
        let contexto_ceps = [];
        
        let matchCNPJ = texto.match(/CNPJ[\s\S]{0,200}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi);
        if (matchCNPJ) {
            for (let m of matchCNPJ) {
                let ceps = [...m.matchAll(/(\d{5}\s?-?\s?\d{3})/g)].map(c => normalizarCEP(c[1]));
                if (ceps.length) {
                    ceps_prioritarios.push(...ceps);
                    contexto_ceps.push({cep: ceps.join(','), contexto: 'CNPJ: ' + m.trim().slice(0, 120)});
                }
            }
        }
        
        let matchSede = texto.match(/com sede[\s\S]{0,200}?CEP:?\s*(\d{5}\s?-?\s?\d{3})/gi);
        if (matchSede) {
            for (let m of matchSede) {
                let ceps = [...m.matchAll(/(\d{5}\s?-?\s?\d{3})/g)].map(c => normalizarCEP(c[1]));
                if (ceps.length) {
                    ceps_prioritarios.push(...ceps);
                    contexto_ceps.push({cep: ceps.join(','), contexto: 'com sede: ' + m.trim().slice(0, 120)});
                }
            }
        }
        
        ceps_prioritarios = [...new Set(ceps_prioritarios)];
        
        let todos_ceps = [...texto.matchAll(/\b\d{5}\s?-?\s?\d{3}\b/g)].map(m => normalizarCEP(m[0]));
        let ceps_finais = ceps_prioritarios.length > 0 ? ceps_prioritarios : todos_ceps.filter(cep => !ceps_do_reclamante.includes(cep));
        
        let detalhe = '';
        if (ceps_finais.length) {
            detalhe += 'CEPs considerados: ' + ceps_finais.join(', ') + '\n';
            if (contexto_ceps.length) {
                detalhe += 'Contextos encontrados:\n';
                contexto_ceps.forEach(obj => {
                    detalhe += `- ${obj.cep}: ${obj.contexto}\n`;
                });
            }
        }
        if (ceps_do_reclamante.length) {
            detalhe += 'CEPs ignorados (reclamante): ' + ceps_do_reclamante.join(', ') + '\n';
        }
        
        let alerta = null, trecho = '';
        if (ceps_finais.length === 0) {
            alerta = 'Não há indicação clara do local da prestação dos serviços (CEP não encontrado ou apenas do reclamante).';
        } else {
            let valido = ceps_finais.some(cep => validarCEP(cep));
            if (!valido) {
                alerta = 'O(s) CEP(s) encontrado(s) não estão dentro da jurisdição da Zona Sul de São Paulo.';
                trecho = ceps_finais.join(', ');
            } else {
                alerta = 'CEP(s) dentro da jurisdição da Zona Sul de São Paulo.';
                trecho = ceps_finais.join(', ');
            }
        }
        
        return {alerta: alerta || 'Análise de CEP concluída.', trecho, detalhe};
    }

    function analisarValorCausa(texto) {
        let valorCapa = (texto.match(/valor da causa[^\d]{0,20}([\d\.,]+)/i) || [])[1];
        let pedidos = [...texto.matchAll(/R\$\s?([\d\.]+,[\d]{2})/g)].map(m => parseFloat(m[1].replace(/\./g, '').replace(',', '.')));
        let soma = pedidos.reduce((a, b) => a + b, 0);
        
        let valorTotal = null;
        let regexTotal = /(pedido[s]?|dos pedidos|dos PEDIDOS)[\s\S]{0,400}?(total (apurado|geral|final|dos pedidos|requerido|devidos|valores totais|R\$)[\s\S]{0,40}?([\d\.]+,[\d]{2}))/i;
        let matchTotal = texto.match(regexTotal);
        if (matchTotal) {
            let matchValor = matchTotal[0].match(/R\$\s?([\d\.]+,[\d]{2})/);
            if (matchValor) valorTotal = parseFloat(matchValor[1].replace(/\./g, '').replace(',', '.'));
        }
        
        let detalhe = '';
        if (valorCapa) detalhe += `Valor da causa (capa): R$ ${valorCapa}\n`;
        if (pedidos.length > 0) detalhe += `Valores discriminados: ${pedidos.length} itens, soma: R$ ${soma.toFixed(2)}\n`;
        if (valorTotal) detalhe += `Valor total ao final: R$ ${valorTotal.toFixed(2)}\n`;
        
        let alerta = null, trecho = '';
        if (!valorCapa && !valorTotal) {
            alerta = 'Valor da causa não informado na capa nem valor total ao final da petição.';
        } else if (pedidos.length > 0 && valorTotal && Math.abs(soma - valorTotal) > 10) {
            alerta = 'Divergência significativa entre a soma dos pedidos e o valor total ao final da petição (> R$ 10,00).';
            trecho = `Valor total ao final: R$ ${valorTotal.toFixed(2)}, Soma dos pedidos: R$ ${soma.toFixed(2)}`;
        } else {
            alerta = 'Valores verificados - sem divergências significativas.';
            if (valorCapa && valorTotal) {
                trecho = `Valor da capa: R$ ${valorCapa}, Valor total: R$ ${valorTotal.toFixed(2)}`;
            } else if (valorCapa) {
                trecho = `Valor da causa: R$ ${valorCapa}`;
            }
        }
        
        return {alerta: alerta || 'Análise de valores concluída.', trecho, detalhe};
    }

    const analises = [
        {nome: 'Competência Territorial (CEP)', func: analisarCompetenciaTerritorial},
        {nome: 'Valor da Causa', func: analisarValorCausa}
    ];

    function mostrarTabelaAlertas(alertas) {
        let html = `<table style="width:100%;border-collapse:collapse;font-size:14px;margin-top:10px;background:#1e3a8a !important;">
            <tr style="background:#1e40af !important;color:white;">
                <th style="color:white;padding:8px;border:1px solid #3b82f6;">Item</th>
                <th style="color:white;padding:8px;border:1px solid #3b82f6;">Alerta</th>
                <th style="color:white;padding:8px;border:1px solid #3b82f6;">Trecho relevante</th>
            </tr>`;
        for (let a of alertas) {
            html += `<tr style="background:#1e3a8a !important;color:white;">
                <td style="color:white;padding:6px;border:1px solid #3b82f6;">${a.nome}</td>
                <td style="color:white;padding:6px;border:1px solid #3b82f6;">${a.result.alerta}</td>
                <td style="color:white;padding:6px;max-width:200px;word-wrap:break-word;border:1px solid #3b82f6;">${a.result.trecho || ''}</td>
            </tr>`;
            if (a.result.detalhe) {
                html += `<tr style="background:#1e40af !important;color:white;">
                    <td colspan="3" style="color:#bfdbfe;padding:6px;font-size:12px;white-space:pre-wrap;border:1px solid #3b82f6;">${a.result.detalhe}</td>
                </tr>`;
            }
        }
        html += `</table>`;
        document.getElementById('trg-table').innerHTML = html;
    }

    // Execução principal com aguardo de carregamento
    function iniciar() {
        console.log('Iniciando deteccao...');
        
        if (!tryCreateInterface()) {
            let tentativas = 0;
            let observer = new MutationObserver(() => {
                tentativas++;
                if (tryCreateInterface()) {
                    console.log('Interface criada apos mudanca DOM');
                    observer.disconnect();
                } else if (tentativas > 100) {
                    observer.disconnect();
                    console.log('Muitas tentativas. Use Ctrl+Shift+T para ativar');
                }
            });
            
            observer.observe(document.body, { childList: true, subtree: true });
            
            // Verificação periódica como backup
            let verificacoes = 0;
            let intervalo = setInterval(() => {
                verificacoes++;
                if (tryCreateInterface()) {
                    console.log('Interface criada via verificacao periodica');
                    clearInterval(intervalo);
                } else if (verificacoes > 20) {
                    clearInterval(intervalo);
                }
            }, 3000);
        }
        
        // Ativação manual
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.shiftKey && e.key === 'T') {
                console.log('Ativacao manual');
                createUI();
            }
        });
    }
    
    // Aguarda carregamento completo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => loadPdfJs(iniciar), 2000);
        });
    } else {
        setTimeout(() => loadPdfJs(iniciar), 1000);
    }

})();
