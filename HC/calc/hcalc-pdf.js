(function () {
    'use strict';
    const HCALC_DEBUG = false;
    const dbg = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err = (...args) => console.error('[hcalc]', ...args);
    // ==========================================
    // EXTRAÇÃO DE PLANILHA PJE-CALC (FASE 1)
    // ==========================================
    // PDF.js carregado via @require (só executa se abrir página PJe)
    // Worker configurado sob demanda (primeira vez que processar PDF)

    function carregarPDFJSSeNecessario() {
        // Estratégia 3: PDF.js carrega dentro do Worker via importScripts.
        // Main thread não precisa do pdfjsLib — sempre retorna true.
        return true;
    }

    // ==========================================
    // VALIDAÇÃO DE DADOS EXTRAÍDOS (FASE 2)
    // ==========================================

    // Função utilitária para normalizar nomes (comparação de peritos/advogados)
    function normalizarNomeParaComparacao(nome) {
        if (!nome) return '';
        // Remove acentos, pontos, transforma em maiúsculas para comparação
        return nome.normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[.]/g, '')
            .toUpperCase()
            .trim();
    }

    function validarValor(valor) {
        if (!valor || valor === '0,00') return false;
        // Formato válido: 1.234,56 ou 123,45 ou 1,23
        const regex = /^\d{1,3}(\.\d{3})*,\d{2}$/;
        return regex.test(valor);
    }

    function validarData(data) {
        if (!data) return false;
        const match = data.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        if (!match) return false;

        const dia = parseInt(match[1]);
        const mes = parseInt(match[2]);
        const ano = parseInt(match[3]);

        // Validações básicas
        if (mes < 1 || mes > 12) return false;
        if (dia < 1 || dia > 31) return false;
        if (ano < 2020 || ano > 2030) return false; // Range razoável para planilhas

        return true;
    }

    function calcularQualidadeExtracao(dados) {
        const campos = [
            { nome: 'idPlanilha', label: 'ID', validar: (v) => v && v.length > 3 },
            { nome: 'verbas', label: 'Crédito', validar: validarValor },
            { nome: 'fgts', label: 'FGTS', validar: (v) => !v || v === '0,00' || validarValor(v) }, // Opcional
            { nome: 'inssTotal', label: 'INSS Total', validar: validarValor },
            { nome: 'inssAutor', label: 'INSS Rec', validar: (v) => !v || v === '0,00' || validarValor(v) }, // Opcional
            { nome: 'custas', label: 'Custas', validar: (v) => !v || v === '0,00' || validarValor(v) }, // Opcional
            { nome: 'dataAtualizacao', label: 'Data', validar: validarData }
        ];

        let extraidos = 0;
        let validos = 0;
        const faltando = [];
        const invalidos = [];

        campos.forEach(campo => {
            const valor = dados[campo.nome];
            const temValor = valor && valor !== '' && valor !== '0,00';

            if (temValor) {
                extraidos++;
                if (campo.validar(valor)) {
                    validos++;
                } else {
                    invalidos.push({ campo: campo.label, valor });
                }
            } else if (campo.nome === 'verbas' || campo.nome === 'idPlanilha' || campo.nome === 'dataAtualizacao') {
                // Campos obrigatórios
                faltando.push(campo.label);
            }
        });

        return {
            percentual: Math.round((validos / campos.length) * 100),
            extraidos,
            validos,
            total: campos.length,
            faltando,
            invalidos
        };
    }

    function validarDadosExtraidos(dados) {
        // Validar formatos
        if (dados.verbas && !validarValor(dados.verbas)) {
            warn('Valor de crédito com formato suspeito:', dados.verbas);
            dados._avisoCredito = true;
        }

        if (dados.fgts && dados.fgts !== '0,00' && !validarValor(dados.fgts)) {
            warn('Valor de FGTS com formato suspeito:', dados.fgts);
            dados._avisoFgts = true;
        }

        if (dados.dataAtualizacao && !validarData(dados.dataAtualizacao)) {
            warn('Data extraída inválida:', dados.dataAtualizacao);
            dados._avisoData = true;
        }

        return dados;
    }

    // ==========================================
    // ESTRATÉGIA 3: WEB WORKER PDF
    // PDF.js roda em Worker isolado — zero bloqueio no thread principal.
    // ==========================================

    function criarPdfWorkerBlob() {
        const workerCode = `
// Load worker code FIRST — registers PDFWorkerMessageHandler inline.
// This prevents PDF.js from trying to create a nested Worker (fails in extensions)
// or falling back to "fake worker" mode (needs document, unavailable in Worker).
importScripts('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js');
importScripts('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js');

// Worker code inline is detected — no workerSrc needed
pdfjsLib.GlobalWorkerOptions.workerSrc = '';

function normalizarNome(nome) {
    if (!nome) return '';
    return nome.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').replace(/[.]/g, '').toUpperCase().trim();
}

async function extrair(arrayBuffer, idNomeArquivo, peritosConhecidos) {
    var pdf = null; var page = null;
    try {
        var task = pdfjsLib.getDocument({ data: arrayBuffer });
        pdf = await task.promise;
        page = await pdf.getPage(1);
        var tc = await page.getTextContent();
        var txt = tc.items.map(function(i) { return i.str.trim(); }).filter(function(s) { return s !== ''; }).join(' ');

        var regexVerbas    = /VERBAS\\s+([\\d.,]+)/i;
        var regexFGTS      = /VERBAS\\s+[\\d.,]+\\s+FGTS\\s+([\\d.,]+)/i;
        var regexDepFGTS   = /DEP[OÓ]SITO FGTS\\s*[.,]?\\s*([\\d.,]+)/i;
        var regexINSSTotal = /CONTRIBUIÇÃO SOCIAL SOBRE SALÁRIOS DEVIDOS\\s+([\\d.,]+)/i;
        var regexINSSAutor = /DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL\\s+(?:\\(\\s*)?([\\d.,]+)(?:\\s*\\))?/i;
        var regexCustas    = /CUSTAS JUDICIAIS DEVIDAS PELO RECLAMADO\\s+([\\d.,]+)/i;
        var regexData      = /(?:Data\\s+Liquida[çc][ãa]o\\s*[:\\-]?\\s*(\\d{2}\\/\\d{2}\\/\\d{4}))|(?:(\\d{2}\\/\\d{2}\\/\\d{4})\\s*Data\\s+Liquida[çc][ãa]o)/i;
        var regexDataFB    = /([0-3][0-9]\\/[0-1][0-9]\\/20[2-9][0-9])\\s+[A-ZÀ-Ÿ\\s]+Data\\s+Liquida[çc][ãa]o/i;
        var regexIdAssin   = /Documento assinado eletronicamente[\\s\\S]*?-\\s*([a-zA-Z0-9]+)(?:\\s|$)/i;
        var regexHonAutor  = /HONORÁRIOS LÍQUIDOS PARA PATRONO DO RECLAMANTE\\s+([\\d.,]+)/i;
        var regexHonPerito = /HONORÁRIOS LÍQUIDOS PARA\\s+(?!PATRONO DO RECLAMANTE)(.+?)\\s+([\\d.,]{3,})/i;
        var regexPeriodo   = /(\\d{2}[/]?\\d{2}[/]?\\d{4})\\s+a\\s+(\\d{2}[/]?\\d{2}[/]?\\d{4})/;
        var regexIRPF      = /IRPF\\s+DEVIDO\\s+PELO\\s+RECLAMANTE\\s+([\\d.,]+)/i;

        var verbas    = (txt.match(regexVerbas)    || [])[1] || '';
        var fgts      = (txt.match(regexFGTS)      || [])[1] || '';
        var inssTotal = (txt.match(regexINSSTotal)  || [])[1] || '';
        var inssAutor = (txt.match(regexINSSAutor)  || [])[1] || '';
        var custas    = (txt.match(regexCustas)     || [])[1] || '';
        var honAutor  = (txt.match(regexHonAutor)   || [])[1] || '';
        var mPerito   = txt.match(regexHonPerito);
        var peritoNome  = mPerito ? mPerito[1].trim() : '';
        var peritoValor = mPerito ? mPerito[2] : '';

        if (peritoNome && peritoValor && peritosConhecidos && peritosConhecidos.length) {
            var ehPerito = peritosConhecidos.some(function(p) {
                return normalizarNome(p).includes(normalizarNome(peritoNome)) ||
                       normalizarNome(peritoNome).includes(normalizarNome(p));
            });
            if (!ehPerito) { honAutor = peritoValor; peritoNome = ''; peritoValor = ''; }
        }

        var dataAtualizacao = (txt.match(regexData) || [])[1] || (txt.match(regexData) || [])[2];
        if (!dataAtualizacao) { var fb = txt.match(regexDataFB); if (fb) dataAtualizacao = fb[1]; }

        var idPlanilha = idNomeArquivo || (txt.match(regexIdAssin) || [])[1] || '';
        var pm = txt.match(regexPeriodo);
        var periodoCalculo = null;
        if (pm) {
            var fmt = function(s) { return s.indexOf('/') !== -1 ? s : s.substr(0,2)+'/'+s.substr(2,2)+'/'+s.substr(4,4); };
            periodoCalculo = fmt(pm[1]) + ' a ' + fmt(pm[2]);
        }
        var irpfM = txt.match(regexIRPF);
        var irpfIsento = !irpfM || parseFloat(irpfM[1].replace(/\\./g,'').replace(',','.')) === 0;
        var fgtsDepositado = false;
        if (fgts) { var mDep = txt.match(regexDepFGTS); if (mDep && mDep[1]) fgtsDepositado = fgts.replace(/[\\.,]/g,'') === mDep[1].replace(/[\\.,]/g,''); }

        return { sucesso: true, verbas, fgts, fgtsDepositado, inssTotal, inssAutor, custas,
                 dataAtualizacao, idPlanilha, honAutor, peritoNome, peritoValor, periodoCalculo, irpfIsento };
    } catch(e) {
        return { sucesso: false, erro: e.message };
    } finally {
        try { if (page) page.cleanup(); } catch(e) {}
        try { if (pdf) await pdf.destroy(); } catch(e) {}
    }
}

self.onmessage = async function(e) {
    var d = e.data;
    var resultado = await extrair(d.arrayBuffer, d.idNomeArquivo, d.peritosConhecidos);
    self.postMessage(resultado);
};
`;
        const blob = new Blob([workerCode], { type: 'application/javascript' });
        return URL.createObjectURL(blob);
    }

    // Placeholder para compatibilidade com hcalc-overlay.js
    async function extrairDadosPlanilha(arrayBuffer, idNomeArquivo = '') {
        let loadingTask = null;
        let pdf = null;
        let page = null;

        try {
            if (!window.pdfjsLib) {
                throw new Error('PDF.js não está carregado');
            }

            loadingTask = window.pdfjsLib.getDocument({ data: arrayBuffer });
            pdf = await loadingTask.promise;
            page = await pdf.getPage(1);
            const textContent = await page.getTextContent();

            const textosBrutos = textContent.items.map(item => item.str.trim());
            const textoCompleto = textosBrutos.filter(str => str !== "").join(' ');

            // Regex otimizadas (copiadas de ext.js v4.2)
            const regexVerbas = /VERBAS\s+([\d.,]+)/i;
            const regexFGTS = /VERBAS\s+[\d.,]+\s+FGTS\s+([\d.,]+)/i;
            const regexDepositoFGTS = /DEP[OÓ]SITO FGTS\s*[\.,]?\s*([\d\.,]+)/i;
            const regexINSSTotal = /CONTRIBUIÇÃO SOCIAL SOBRE SALÁRIOS DEVIDOS\s+([\d.,]+)/i;
            const regexINSSAutor = /DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL\s+(?:\(\s*)?([\d.,]+)(?:\s*\))?/i;
            const regexCustas = /CUSTAS JUDICIAIS DEVIDAS PELO RECLAMADO\s+([\d.,]+)/i;
            const regexData = /(?:Data\s+Liquida[çc][ãa]o\s*[:\-]?\s*(\d{2}\/\d{2}\/\d{4}))|(?:(\d{2}\/\d{2}\/\d{4})\s*Data\s+Liquida[çc][ãa]o)/i;
            const regexDataFallback = /([0-3][0-9]\/[0-1][0-9]\/20[2-9][0-9])\s+[A-ZÀ-Ÿ\s]+Data\s+Liquida[çc][ãa]o/i;
            const regexIdAssinatura = /Documento assinado eletronicamente[\s\S]*?-\s*([a-zA-Z0-9]+)(?:\s|$)/i;
            const regexHonAutor = /HONORÁRIOS LÍQUIDOS PARA PATRONO DO RECLAMANTE\s+([\d.,]+)/i;
            const regexHonPerito = /HONORÁRIOS LÍQUIDOS PARA\s+(?!PATRONO DO RECLAMANTE)(.+?)\s+([\d.,]{3,})/i;
            const regexPeriodo = /(\d{2}[\/]?\d{2}[\/]?\d{4})\s+a\s+(\d{2}[\/]?\d{2}[\/]?\d{4})/;
            const regexIRPF = /IRPF\s+DEVIDO\s+PELO\s+RECLAMANTE\s+([\d.,]+)/i;

            // Extração
            const verbas = (textoCompleto.match(regexVerbas) || [])[1] || "";
            const fgts = (textoCompleto.match(regexFGTS) || [])[1] || "";
            const inssTotal = (textoCompleto.match(regexINSSTotal) || [])[1] || "";
            const inssAutor = (textoCompleto.match(regexINSSAutor) || [])[1] || "";
            const custas = (textoCompleto.match(regexCustas) || [])[1] || "";
            let honAutor = (textoCompleto.match(regexHonAutor) || [])[1] || "";

            const matchPerito = textoCompleto.match(regexHonPerito);
            let peritoNome = matchPerito ? matchPerito[1].trim() : "";
            let peritoValor = matchPerito ? matchPerito[2] : "";

            // VALIDAÇÃO: Verificar se "honorário para..." é perito ou advogado autor
            // REGRA: Default = honorário advogado autor
            //        Só registra como perito se nome bater com perito detectado
            // PREVALÊNCIA: Valor da planilha prevalece sobre valor da sentença (mais atualizado)
            if (peritoNome && peritoValor) {
                const peritosConhecidos = window.hcalcPeritosDetectados || [];

                // Verificar se nome bate com perito já detectado no processo
                const ehPerito = peritosConhecidos.some(p =>
                    normalizarNomeParaComparacao(p).includes(normalizarNomeParaComparacao(peritoNome)) ||
                    normalizarNomeParaComparacao(peritoNome).includes(normalizarNomeParaComparacao(p))
                );

                if (ehPerito) {
                    // Nome bate com perito detectado → honorário pericial
                    console.log(`hcalc: "${peritoNome}" confirmado como PERITO (match detectado)`);
                    // Mantém peritoNome e peritoValor
                } else {
                    // DEFAULT: Qualquer outro caso = honorário advogado autor
                    console.log(`hcalc: "${peritoNome}" → DEFAULT: honorário advogado autor`);
                    // Transferir para honorários do autor
                    honAutor = peritoValor;
                    peritoNome = "";
                    peritoValor = "";
                }
            }

            let dataAtualizacao = (textoCompleto.match(regexData) || [])[1] ||
                (textoCompleto.match(regexData) || [])[2];
            if (!dataAtualizacao) {
                const fallback = textoCompleto.match(regexDataFallback);
                if (fallback) dataAtualizacao = fallback[1];
            }

            const idPlanilha = idNomeArquivo || (textoCompleto.match(regexIdAssinatura) || [])[1] || "";

            // Extrair período do cálculo
            const periodoMatch = textoCompleto.match(regexPeriodo);
            let periodoCalculo = null;
            if (periodoMatch) {
                const fmt = s => s.includes('/') ? s : `${s.substr(0, 2)}/${s.substr(2, 2)}/${s.substr(4, 4)}`;
                periodoCalculo = `${fmt(periodoMatch[1])} a ${fmt(periodoMatch[2])}`;
            }

            // Extrair IRPF e determinar se é tributável
            const irpfMatch = textoCompleto.match(regexIRPF);
            const irpfIsento = !irpfMatch || parseFloat(
                irpfMatch[1].replace(/\./g, '').replace(',', '.')
            ) === 0;

            // Detectar se FGTS foi depositado (comparando valores)
            let fgtsDepositado = false;
            if (fgts) {
                const matchDepositoFGTS = textoCompleto.match(regexDepositoFGTS);
                if (matchDepositoFGTS && matchDepositoFGTS[1]) {
                    // Normalizar valores para comparação (remover pontos/vírgulas)
                    const valorFgts = fgts.replace(/[\.,]/g, '');
                    const valorDeposito = matchDepositoFGTS[1].replace(/[\.,]/g, '');

                    if (valorFgts === valorDeposito) {
                        fgtsDepositado = true;
                        console.log(`hcalc: FGTS identificado como DEPOSITADO (valor: ${fgts})`);
                    }
                }
            }

            const dadosBrutos = {
                verbas,
                fgts,
                fgtsDepositado,
                inssTotal,
                inssAutor,
                custas,
                dataAtualizacao,
                idPlanilha,
                honAutor,
                peritoNome,
                peritoValor,
                periodoCalculo,
                irpfIsento,
                sucesso: true
            };

            // Aplicar validação (Fase 2)
            const dadosValidados = validarDadosExtraidos(dadosBrutos);
            const qualidade = calcularQualidadeExtracao(dadosValidados);

            console.log(`[HCalc] Extração concluída - Qualidade: ${qualidade.percentual}% (${qualidade.validos}/${qualidade.total} válidos)`);
            if (qualidade.faltando.length > 0) {
                warn('Campos não extraídos:', qualidade.faltando.join(', '));
            }
            if (qualidade.invalidos.length > 0) {
                warn('Campos com formato suspeito:', qualidade.invalidos.map(i => `${i.campo}: ${i.valor}`).join(', '));
            }

            return dadosValidados;

        } catch (error) {
            console.error('[HCalc] Erro na extração:', error.message);
            return { sucesso: false, erro: error.message };
        } finally {
            // Limpeza de memória (previne leak)
            if (page) {
                try { page.cleanup(); } catch (e) { }
            }
            if (pdf) {
                try { await pdf.destroy(); } catch (e) { }
            }
            if (loadingTask && typeof loadingTask.destroy === 'function') {
                try { await loadingTask.destroy(); } catch (e) { }
            }
        }
    }

    async function processarPlanilhaPDF(file) {
        let idNomeArquivo = '';
        const matchNome = file.name.match(/Documento_([a-zA-Z0-9]+)\.pdf/i);
        if (matchNome) idNomeArquivo = matchNome[1];

        // Transfere ArrayBuffer para Worker (zero-copy)
        const arrayBuffer = await file.arrayBuffer();
        const peritosConhecidos = window.hcalcPeritosDetectados || [];

        return new Promise((resolve, reject) => {
            if (!window.hcalcState._pdfWorkerUrl) {
                window.hcalcState._pdfWorkerUrl = criarPdfWorkerBlob();
            }
            const worker = new Worker(window.hcalcState._pdfWorkerUrl);
            worker.onmessage = (e) => {
                worker.terminate();
                const dados = e.data;
                if (!dados.sucesso) { resolve(dados); return; }
                const dadosValidados = validarDadosExtraidos(dados);
                const qualidade = calcularQualidadeExtracao(dadosValidados);
                console.log('[HCalc Worker] Qualidade: ' + qualidade.percentual + '% (' + qualidade.validos + '/' + qualidade.total + ' válidos)');
                if (qualidade.faltando.length > 0) warn('Campos não extraídos:', qualidade.faltando.join(', '));
                if (qualidade.invalidos.length > 0) warn('Campos suspeitos:', qualidade.invalidos.map(i => i.campo + ': ' + i.valor).join(', '));
                resolve(dadosValidados);
            };
            worker.onerror = (e) => {
                console.error('[HCalc Worker] Erro no worker:', e.message, e);
                worker.terminate();
                reject(new Error(e.message));
            };
            worker.postMessage({ arrayBuffer, idNomeArquivo, peritosConhecidos }, [arrayBuffer]);
        });
    }

    // Expor para hcalc-overlay.js
    window.normalizarNomeParaComparacao = normalizarNomeParaComparacao;
    window.carregarPDFJSSeNecessario = carregarPDFJSSeNecessario;
    window.processarPlanilhaPDF = processarPlanilhaPDF;
})();
