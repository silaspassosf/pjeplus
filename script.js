// ==UserScript==
// @name         Triagem Petição Inicial Trabalhista - Zona Sul SP
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Análise automática de petição inicial trabalhista (PDF) conforme roteiro do TRT2 Zona Sul SP, sem IA, com interface de acompanhamento e tabela de alertas editável.
// @author       GPT-4
// @match        *://*/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Carrega pdf.js se necessário
    function loadPdfJs(callback) {
        if (window.pdfjsLib) return callback();
        let script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        script.onload = callback;
        document.head.appendChild(script);
    }

    let textoExtraidoGlobal = '';

    // Cria interface principal
    function createUI() {
        if (document.getElementById('trg-peticao-root')) return;
        let root = document.createElement('div');
        root.id = 'trg-peticao-root';
        root.style = 'position:fixed;top:30px;right:30px;z-index:99999;background:#fff;border:2px solid #333;border-radius:8px;padding:24px 20px 16px 20px;box-shadow:0 4px 16px rgba(0,0,0,0.18);font-family:Segoe UI,Arial,sans-serif;max-width:420px;min-width:340px;';
        root.innerHTML = `
            <b style="font-size:18px;">Triagem Petição Inicial - Zona Sul SP</b>
            <div id="trg-status" style="margin:10px 0 12px 0;color:#444;">Aguardando upload do PDF...</div>
            <input type="file" id="trg-file" accept="application/pdf" style="margin-bottom:10px;">
            <button id="trg-save-txt" style="display:none;margin-bottom:8px;">Salvar texto extraído (.txt)</button>
            <div id="trg-progress" style="margin:8px 0 8px 0;font-size:13px;color:#2e7d32;"></div>
            <div id="trg-table"></div>
        `;
        document.body.appendChild(root);
    }

    // Utilitário: normaliza CEP
    function normalizarCEP(cep) {
        return cep.replace(/[^0-9]/g, '');
    }

    // Utilitário: valida CEP nos intervalos
    function validarCEP(cep) {
        const n = parseInt(cep, 10);
        if (cep.length !== 8 || isNaN(n)) return false;
        const faixas = [
            [4307000, 4314999],
            [4316000, 4477999],
            [4603000, 4620999],
            [4624000, 4703999],
            [4708000, 4967999],
            [5640000, 5642999],
            [5657000, 5665999],
            [5692000, 5692999],
            [5703000, 5743999],
            [5745000, 5750999],
            [5752000, 5895999]
        ];
        return faixas.some(([ini, fim]) => n >= ini && n <= fim);
    }

    // Função para extrair texto do PDF
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

    // Funções de análise (cada item retorna {alerta, trecho, detalhe})
    function analisarCompetenciaTerritorial(texto) {
        // Busca bloco do local da prestação dos serviços
        let bloco = '';
        let matchBloco = texto.match(/(local da prestação[\s\S]{0,200}?cep[\s\S]{0,30}?\d{5}-?\d{3})/i)
            || texto.match(/prestação de serviços[\s\S]{0,200}?cep[\s\S]{0,30}?\d{5}-?\d{3}/i)
            || texto.match(/laborou[\s\S]{0,200}?cep[\s\S]{0,30}?\d{5}-?\d{3}/i)
            || texto.match(/trabalhou[\s\S]{0,200}?cep[\s\S]{0,30}?\d{5}-?\d{3}/i);
        if (matchBloco) bloco = matchBloco[0];
        // Se não encontrar bloco típico, busca frases com "prestação" e endereço
        if (!bloco) {
            let matchAlt = texto.match(/(prestação[\s\S]{0,100}?em[\s\S]{0,100}?cep[\s\S]{0,30}?\d{5}-?\d{3})/i);
            if (matchAlt) bloco = matchAlt[0];
        }
        // Extrai CEP do bloco prioritário
        let ceps = bloco ? [...bloco.matchAll(/\b\d{5}-?\d{3}\b/g)].map(m => normalizarCEP(m[0])) : [];
        // Se não encontrou, busca CEP em frases que associam endereço à prestação
        if (ceps.length === 0) {
            let match2 = texto.match(/(prestou serviços[\s\S]{0,100}?cep[\s\S]{0,30}?\d{5}-?\d{3})/i);
            if (match2) ceps = [...match2[0].matchAll(/\b\d{5}-?\d{3}\b/g)].map(m => normalizarCEP(m[0]));
        }
        // Se ainda não encontrou, busca CEPs em frases de endereço da reclamada, mas só se afirmar que o trabalho foi prestado ali
        if (ceps.length === 0) {
            let match3 = texto.match(/endereço[\s\S]{0,100}?reclamad[ao][\s\S]{0,100}?cep[\s\S]{0,30}?\d{5}-?\d{3}/i);
            if (match3 && /prestou|laborou|trabalhou/i.test(match3[0])) {
                ceps = [...match3[0].matchAll(/\b\d{5}-?\d{3}\b/g)].map(m => normalizarCEP(m[0]));
            }
        }
        // Se ainda não encontrou, busca todos os CEPs do texto (último recurso)
        if (ceps.length === 0) {
            ceps = [...texto.matchAll(/\b\d{5}-?\d{3}\b/g)].map(m => normalizarCEP(m[0]));
        }
        let alerta = null, trecho = '', detalhe = '';
        if (ceps.length === 0) {
            alerta = '🔔 Não há indicação clara do local da prestação dos serviços (CEP não encontrado).';
        } else {
            // Valida cada CEP
            let valido = ceps.some(cep => validarCEP(cep));
            if (!valido) {
                alerta = '🔔 O(s) CEP(s) encontrado(s) não estão dentro da jurisdição da Zona Sul de São Paulo.';
                trecho = ceps.join(', ');
            } else {
                // Se encontrou CEP válido, mas só de endereço da reclamada sem afirmar que o trabalho foi prestado ali
                if (bloco && /reclamad[ao]/i.test(bloco) && !/prestou|laborou|trabalhou/i.test(bloco)) {
                    alerta = '🔔 A petição apenas menciona o endereço da reclamada sem afirmar que o trabalho foi prestado ali.';
                    trecho = bloco;
                }
            }
            // Checa formato
            for (let cep of ceps) {
                if (cep.length !== 8) {
                    alerta = '🔔 O CEP está mal formatado, ilegível ou com menos de 8 dígitos.';
                    trecho = cep;
                    break;
                }
            }
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarRitoProcessual(texto) {
        // Busca valor da causa e rito na capa
        let valorCausa = (texto.match(/valor da causa[^\d]{0,20}([\d\.,]+)/i) || [])[1];
        let rito = (texto.match(/rito[^\w]{0,10}(ordin[aá]rio|sumar[ií]ssimo|al[cç]ada)/i) || [])[1];
        let alerta = null, trecho = '', detalhe = '';
        if (!valorCausa || !rito) return null;
        let valor = parseFloat(valorCausa.replace(/\./g, '').replace(',', '.'));
        let sm = 1518.00;
        let ritoCorreto = '';
        if (valor <= 2 * sm) ritoCorreto = 'alçada';
        else if (valor <= 40 * sm) ritoCorreto = 'sumaríssimo';
        else ritoCorreto = 'ordinário';
        // Verifica PJ de direito público
        let pjPublico = /munic[ií]pio|autarquia|funda[çc][aã]o p[úu]blica|uni[aã]o|estado/i.test(texto);
        if (pjPublico && ritoCorreto !== 'ordinário') {
            alerta = '🔔 ALERTA: Polo passivo com PJ de direito público exige rito ordinário.';
            trecho = 'Rito declarado: ' + rito + '.';
        } else if (ritoCorreto && rito && ritoCorreto !== rito.toLowerCase()) {
            alerta = `🔔 ALERTA: incompatibilidade entre o valor da causa e o rito informado.`;
            trecho = `Valor da causa: R$ ${valorCausa}, Rito declarado: ${rito}, Rito correto: ${ritoCorreto}`;
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarPartes(texto) {
        // Extrai blocos de partes
        let partes = [];
        let matchReclamante = texto.match(/reclamante:([^\n]+?)(cpf|rg|identidade|n[úu]mero|advogado|\-|\d{3}\.\d{3}\.\d{3}-\d{2})/i);
        let matchReclamada = texto.match(/reclamad[ao]:([^\n]+?)(cnpj|cpf|endere[çc]o|\-|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2})/i);
        if (matchReclamante) partes.push({tipo:'reclamante', texto:matchReclamante[0]});
        if (matchReclamada) partes.push({tipo:'reclamada', texto:matchReclamada[0]});
        let alerta = null, trecho = '', detalhe = '';
        // Qualificação mínima
        for (let p of partes) {
            if (!/cpf|cnpj|endere[çc]o/i.test(p.texto)) {
                alerta = '🔔 Parte sem qualificação mínima (nome, CPF/CNPJ ou endereço).';
                trecho = p.texto;
            }
        }
        // Parte na capa mas não em fatos/pedidos
        if (matchReclamada && !/fato|pedido|pleiteia|requer|narra/i.test(texto.substr(texto.indexOf(matchReclamada[0]), 500))) {
            alerta = '🔔 Parte consta na capa mas não é mencionada nos fatos ou pedidos.';
            trecho = matchReclamada[0];
        }
        // Duplicidade
        if (/filial/i.test(texto) && /matriz/i.test(texto) && !/v[íi]nculo|relação/i.test(texto)) {
            alerta = '🔔 Matriz e filial tratadas como entidades distintas sem explicação.';
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarSegredoJustica(texto) {
        let pedido = texto.match(/segredo de justi[çc]a/i);
        if (!pedido) return null;
        let final = /dos pedidos|requerimentos/i.test(texto.substr(texto.length-800));
        let justificativa = /interesse p[úu]blico|filia[çc][aã]o|guarda|intimidade|sigilo|dados protegidos|art.?189/i.test(texto);
        let alerta = null, trecho = '', detalhe = '';
        if (!justificativa) {
            alerta = '🔔 Pedido de segredo de justiça sem justificativa compatível.';
            trecho = pedido[0];
        } else if (!final) {
            alerta = '🔔 Pedido de segredo de justiça ausente da parte final da petição.';
            trecho = pedido[0];
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarCNPJReclamadas(texto) {
        let cnpjs = [...texto.matchAll(/\b\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}\b|\b\d{14}\b/g)].map(m => m[0]);
        let alerta = null, trecho = '', detalhe = '';
        if (cnpjs.length === 0) {
            alerta = '🔔 Reclamada(s) sem CNPJ informado.';
        } else {
            for (let cnpj of cnpjs) {
                let num = cnpj.replace(/\D/g, '');
                if (num.length !== 14) {
                    alerta = '🔔 CNPJ incompleto ou mal formatado.';
                    trecho = cnpj;
                    break;
                }
                if (/\/0002-/.test(cnpj) && !/matriz|v[íi]nculo|relação/i.test(texto)) {
                    alerta = '🔔 CNPJ de filial sem referência à matriz.';
                    trecho = cnpj;
                }
            }
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarPedidosUrgentes(texto) {
        let blocoPedidos = texto.match(/dos pedidos[\s\S]{0,800}/i);
        let menTutela = /tutela de urg[êe]ncia|tutela cautelar|tutela da evid[êe]ncia|pedido liminar|antecipação de tutela/i.test(texto);
        let objeto = /reintegra[çc][aã]o|bloqueio|libera[çc][aã]o|urg[êe]ncia/i.test(texto);
        let causa = /fato|perigo|probabilidade|risco|dano|amea[çc]a/i.test(texto);
        let fundamentacao = /art.?300|art.?303|art.?305|art.?311|probabilidade do direito|perigo de dano|resultado útil/i.test(texto);
        let pedidoFinal = blocoPedidos && /tutela|liminar/i.test(blocoPedidos[0]);
        let alerta = null, trecho = '', detalhe = '';
        if (menTutela && (!objeto || !causa || !fundamentacao || !pedidoFinal)) {
            alerta = '🔔 Tutela provisória mencionada sem objeto claro, causa de pedir específica, fundamentação jurídica e/ou pedido formal na parte final.';
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarJuizoDigital(texto) {
        let adesao = /ju[ií]zo 100% digital|atos processuais.*digital|audi[eê]ncia.*digital/i.test(texto);
        let confusao = /processo eletr[oô]nico/i.test(texto) && !adesao;
        let alerta = null, trecho = '', detalhe = '';
        if (confusao) {
            alerta = '🔔 Petição menciona apenas processo eletrônico, sem requerimento de atos exclusivamente digitais.';
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarValorCausa(texto) {
        let valorCapa = (texto.match(/valor da causa[^\d]{0,20}([\d\.,]+)/i) || [])[1];
        let pedidos = [...texto.matchAll(/R\$\s?([\d\.]+,[\d]{2})/g)].map(m => parseFloat(m[1].replace(/\./g, '').replace(',', '.')));
        let soma = pedidos.reduce((a, b) => a + b, 0);
        let alerta = null, trecho = '', detalhe = '';
        if (!valorCapa) {
            alerta = '🔔 Valor da causa não informado na capa.';
        } else if (pedidos.length > 0 && Math.abs(soma - parseFloat(valorCapa.replace(/\./g, '').replace(',', '.'))) > 10) {
            alerta = '🔔 Divergência significativa entre a soma dos pedidos e o valor da capa (> R$ 10,00).';
            trecho = `Valor da capa: R$ ${valorCapa}, Soma dos pedidos: R$ ${soma.toFixed(2)}`;
        } else if (pedidos.length === 0) {
            alerta = '🔔 Valor total indicado, mas não há discriminação dos valores dos pedidos.';
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarPessoasFisicasPassivo(texto) {
        let pessoas = [...texto.matchAll(/reclamad[ao]:?\s*([A-ZÁ-Úa-zá-ú\s]+)[^\n]*cpf:?\s*([\d\.\-]+)/gi)];
        let alerta = null, trecho = '', detalhe = '';
        for (let p of pessoas) {
            let nome = p[1], cpf = p[2];
            let qualif = new RegExp(nome + '[\s\S]{0,100}endere[çc]o', 'i').test(texto);
            let fundamenta = /desconsidera[çc][aã]o|sucess[aã]o|responsabilidade pessoal|empregador/i.test(texto);
            let causa = new RegExp(nome + '[\s\S]{0,200}(fato|v[íi]nculo|pedido)', 'i').test(texto);
            let pedido = new RegExp('pedido[\s\S]{0,200}' + nome, 'i').test(texto);
            if (!qualif || !fundamenta || !causa || !pedido) {
                alerta = '🔔 Pessoa física no polo passivo sem fundamentação, causa de pedir, pedido ou qualificação mínima.';
                trecho = nome;
                break;
            }
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarOutrosProcessos(texto) {
        let men = /processo anterior|ação idêntica|acordo não homologado|desist[êe]ncia|arquivamento|litispend[êe]ncia|coisa julgada|conex[aã]o/i.test(texto);
        if (men) {
            return {alerta: '🔔 Possível litispendência, coisa julgada ou conexão processual.', trecho: '', detalhe: ''};
        }
        return null;
    }

    function analisarResponsabilidadeSubsidiariaSolidaria(texto) {
        let sub = /responsabilidade subsidi[áa]ria/i.test(texto);
        let sol = /responsabilidade solid[áa]ria/i.test(texto);
        let alerta = null, trecho = '', detalhe = '';
        if (sub && sol && !/fundamenta[çc][aã]o distinta|grupo econ[oô]mico|terceiriza[çc][aã]o|confus[aã]o patrimonial/i.test(texto)) {
            alerta = '🔔 Pedido simultâneo de responsabilidade subsidiária e solidária sem fundamentações distintas.';
        } else if ((sub || sol) && !/fundamenta[çc][aã]o|fato|pedido/i.test(texto)) {
            alerta = '🔔 Pedido de responsabilidade sem fundamentação jurídica ou fática.';
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarEnderecoReclamante(texto) {
        let match = texto.match(/reclamante[\s\S]{0,100}endere[çc]o[\s\S]{0,100}(\b\d{5}-?\d{3}\b)/i);
        let cidade = texto.match(/reclamante[\s\S]{0,100}cidade:?\s*([A-Za-zÀ-ú ]+)/i);
        let virtual = /audi[eê]ncia virtual|audi[eê]ncia h[ií]brida/i.test(texto);
        let alerta = null, trecho = '', detalhe = '';
        if (cidade && !/s[ãa]o paulo/i.test(cidade[1]) && !virtual) {
            alerta = '🔔 Reclamante reside fora de São Paulo/SP e não há pedido de audiência virtual.';
            trecho = cidade[1];
        } else if (cidade && /s[ãa]o paulo/i.test(cidade[1]) && virtual) {
            alerta = '🔔 Pedido de audiência virtual/híbrida sem justificativa, sendo o reclamante domiciliado em São Paulo/SP.';
            trecho = cidade[1];
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    function analisarProcuracao(texto) {
        let menProc = /procura[çc][aã]o/i.test(texto);
        let assinada = /assinado digitalmente|assinatura eletr[oô]nica/i.test(texto);
        let advogado = texto.match(/advogado:?\s*([A-ZÁ-Úa-zá-ú\s]+)\s*-?\s*oab:?\s*([A-Z]{2}\d+)/i);
        let outorgado = texto.match(/outorgad[ao][\s\S]{0,100}oab:?\s*([A-Z]{2}\d+)/i);
        let alerta = null, trecho = '', detalhe = '';
        if (!menProc) {
            alerta = '🔔 Não há procuração anexa.';
        } else if (!assinada) {
            alerta = '🔔 Procuração sem assinatura digital/eletrônica.';
        } else if (advogado && outorgado && advogado[2] !== outorgado[1]) {
            alerta = '🔔 Advogado signatário não consta na procuração.';
        }
        return alerta ? {alerta, trecho, detalhe} : null;
    }

    // Mapeamento dos itens de análise
    const analises = [
        {nome: 'Competência Territorial (CEP)', func: analisarCompetenciaTerritorial},
        {nome: 'Rito Processual', func: analisarRitoProcessual},
        {nome: 'Partes', func: analisarPartes},
        {nome: 'Segredo de Justiça', func: analisarSegredoJustica},
        {nome: 'CNPJ das Reclamadas', func: analisarCNPJReclamadas},
        {nome: 'Pedidos Urgentes', func: analisarPedidosUrgentes},
        {nome: 'Juízo 100% Digital', func: analisarJuizoDigital},
        {nome: 'Valor da Causa', func: analisarValorCausa},
        {nome: 'Pessoas Físicas no Polo Passivo', func: analisarPessoasFisicasPassivo},
        {nome: 'Outros Processos entre as Partes', func: analisarOutrosProcessos},
        {nome: 'Responsabilidade Subsidiária/Solidária', func: analisarResponsabilidadeSubsidiariaSolidaria},
        {nome: 'Endereço da Parte Reclamante', func: analisarEnderecoReclamante},
        {nome: 'Procuração', func: analisarProcuracao},
    ];

    // Cria tabela editável de alertas
    function mostrarTabelaAlertas(alertas) {
        let html = `<table border="1" style="width:100%;border-collapse:collapse;font-size:14px;">
            <tr style="background:#eee;">
                <th>Item</th>
                <th>Alerta</th>
                <th>Trecho relevante</th>
                <th>Editar Observação</th>
            </tr>`;
        for (let a of alertas) {
            html += `<tr>
                <td>${a.nome}</td>
                <td>${a.result.alerta}</td>
                <td style="max-width:180px;overflow-x:auto;">${a.result.trecho || ''}</td>
                <td contenteditable="true" style="background:#fffbe7;"></td>
            </tr>`;
        }
        html += `</table>
        <div style="margin-top:8px;font-size:13px;color:#444;">Você pode editar as observações antes de copiar ou salvar.</div>`;
        document.getElementById('trg-table').innerHTML = html;
        // Remove controles de IA (OpenAI)
        let iaDiv = document.getElementById('trg-openai-result');
        if (iaDiv) iaDiv.remove();
        let iaBtn = document.getElementById('trg-openai-review');
        if (iaBtn) iaBtn.remove();
        let iaKey = document.getElementById('trg-openai-key');
        if (iaKey) iaKey.remove();
        let iaSave = document.getElementById('trg-openai-save');
        if (iaSave) iaSave.remove();
        let iaStatus = document.getElementById('trg-openai-status');
        if (iaStatus) iaStatus.remove();
        let iaImprove = document.getElementById('trg-openai-improve');
        if (iaImprove) iaImprove.remove();
        let iaImproveResult = document.getElementById('trg-openai-improve-result');
        if (iaImproveResult) iaImproveResult.remove();
    }

    // Execução principal
    loadPdfJs(() => {
        createUI();
        let fileInput = document.getElementById('trg-file');
        let status = document.getElementById('trg-status');
        let progress = document.getElementById('trg-progress');
        let btnSaveTxt = document.getElementById('trg-save-txt');
        fileInput.onchange = async function() {
            let file = fileInput.files[0];
            if (!file) return;
            status.textContent = 'Extraindo o PDF...';
            progress.textContent = '';
            btnSaveTxt.style.display = 'none';
            try {
                let texto = await extrairTextoPDF(file, (pg, total) => {
                    progress.textContent = `Extraindo página ${pg} de ${total}...`;
                });
                textoExtraidoGlobal = texto; // Salva o texto extraído globalmente
                status.textContent = 'PDF extraído. Analisando itens...';
                progress.textContent = '';
                // Executa cada análise
                let alertas = [];
                for (let a of analises) {
                    let result = a.func(texto);
                    if (result) alertas.push({nome: a.nome, result});
                }
                status.textContent = 'Compilando respostas...';
                setTimeout(() => {
                    status.textContent = 'Análise completa.';
                    mostrarTabelaAlertas(alertas);
                    btnSaveTxt.style.display = '';
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
                }, 800);
            } catch (e) {
                status.textContent = 'Erro ao extrair/analisar o PDF: ' + e;
            }
        };
    });
})();