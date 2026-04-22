(function () {
    'use strict';
    const HCALC_DEBUG = false;
    const dbg = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err = (...args) => console.error('[hcalc]', ...args);

    // PDF.js carregado via @require no userscript header
    function carregarPDFJSSeNecessario() {
        if (window.hcalcState.pdfjsLoaded) return true;

        if (!window.pdfjsLib) {
            console.error('[HCalc] pdfjsLib não encontrado. Verifique o @require.');
            return false;
        }

        window.pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';

        window.hcalcState.pdfjsLoaded = true;
        console.log('[HCalc] PDF.js worker configurado (lazy).');
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
    // EXTRAÇÃO DE PLANILHA - CORE
    // ==========================================

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

            // Extrair texto iterando páginas até encontrar o marcador padrão
            const LIMITE_MARCADOR = /Crit[ée]rio de C[aá]lculo e Fundamenta[çc][aã]o Legal/i;
            let textoCompleto = '';
            let textosBrutos = [];

            // Varre todas as páginas (ou até encontrar o marcador) - alguns PDFs têm a seção padrão em páginas posteriores
            const paginasTextos = [];
            let marcadorEncontrado = false;
            for (let p = 1; p <= pdf.numPages; p++) {
                try {
                    page = await pdf.getPage(p);
                    const textContent = await page.getTextContent();
                    const textosPagina = textContent.items.map(item => item.str.trim());
                    const textoPagina = textosPagina.filter(str => str !== "").join(' ');

                    paginasTextos.push(textoPagina);
                    textosBrutos = textosBrutos.concat(textosPagina);

                    // Verificar marcador nesta página
                    if (textoPagina.search(LIMITE_MARCADOR) !== -1) {
                        // Concatena tudo até o ponto do marcador na página atual
                        const pos = textoPagina.search(LIMITE_MARCADOR);
                        const prefixo = textoPagina.substring(0, pos);
                        textoCompleto = paginasTextos.slice(0, -1).join(' ') + ' ' + prefixo;
                        marcadorEncontrado = true;
                        dbg('[HCalc] Marcador encontrado na página', p);
                        break;
                    }
                } catch (err) {
                    console.warn('[HCalc] Erro ao ler página', p, err && err.message);
                }
            }

            if (!marcadorEncontrado) {
                // Se não encontrou o marcador, usa o texto concatenado das primeiras 2 páginas (fallback)
                textoCompleto = paginasTextos.slice(0, Math.min(2, paginasTextos.length)).join(' ');
                textosBrutos = textosBrutos.slice(0, Math.min(textosBrutos.length, paginasTextos.length * 200));
                dbg('[HCalc] Marcador não encontrado; usando concat das primeiras 2 páginas como fallback');
            }

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
            // Honorários: tentar extrair preferencialmente da seção entre os marcadores
            const markerStarts = [
                /Descri[cç][aã]o de D[eé]bitos do Reclamado por Credor/i,
                /Descri[cç][aã]o de D[eé]bitos do Reclamante/i,
                /Descri[cç][aã]o de D[eé]bitos do Reclamad[oa]/i
            ];
            const markerEnds = [
                /Total Devido pelo Reclamado/i,
                /Total Devido pelo Reclamante/i,
                /Total Devido pelo Reclamad[oa]/i
            ];

            const regexHonAutor_variants = [
                /HONOR[AÁ]RIOS\s+L[IÍ]QUIDOS\s+PARA\s+PATRONO\s+DO\s+RECLAMANTE\s+([\d.,]+)/i,
                /HONOR[AÁ]RIOS\s+ADVOCAT[IÁ]CIOS.*?RECLAMANTE[\s\S]*?R\$\s*([\d.,]+)/i,
                /HONOR[AÁ]RIOS.*?RECLAMANTE[\s\S]*?R\$\s*([\d.,]+)/i
            ];

            const regexHonReu_variants = [
                /HONOR[AÁ]RIOS\s+L[IÍ]QUIDOS\s+PARA\s+PATRONO\s+DA\s+RECLAMADA\s+([\d.,]+)/i,
                /HONOR[AÁ]RIOS\s+ADVOCAT[IÁ]CIOS.*?RECLAMADA[\s\S]*?R\$\s*([\d.,]+)/i,
                /HONOR[AÁ]RIOS.*?RECLAMADA[\s\S]*?R\$\s*([\d.,]+)/i,
                /HONOR[AÁ]RIOS.*?PELA\s+RECLAMADA[\s\S]*?R\$\s*([\d.,]+)/i
            ];

            const regexHonPerito = /HONORÁRIOS LÍQUIDOS PARA\s+(?!PATRONO DO RECLAMANTE)(.+?)\s+([\d.,]{3,})/i;

            // Extrair trecho entre os marcadores para cada tipo separadamente
            function extractSectionFor(text, starts, ends) {
                try {
                    let best = { s: -1, e: -1, span: Infinity };
                    starts.forEach((sx) => {
                        ends.forEach((ex) => {
                            const sIdx = text.search(sx);
                            const eIdx = text.search(ex);
                            if (sIdx !== -1 && eIdx !== -1 && eIdx > sIdx) {
                                const span = eIdx - sIdx;
                                if (span < best.span) best = { s: sIdx, e: eIdx, span };
                            }
                        });
                    });
                    if (best.s !== -1 && best.e !== -1) return text.substring(best.s, best.e);
                } catch (e) { dbg('[hcalc] extractSectionFor failed', e); }
                return null;
            }

            // Section for HONORÁRIOS do AUTOR: especificamente between Reclamado markers
            const markerStartAutor = /Descri[cç][aã]o de D[eé]bitos do Reclamado por Credor/i;
            const markerEndAutor = /Total Devido pelo Reclamado/i;
            const honraSectionAutor = extractSectionFor(textoCompleto, [markerStartAutor], [markerEndAutor]) || textoCompleto;

            // Section for HONORÁRIOS da RECLAMADA: specifically below 'Descrição de Débitos do Reclamante'
            const markerStartReclamada = /Descri[cç][aã]o de D[eé]bitos do Reclamante/i;
            const markerEndReclamada = /Total Devido pelo Reclamante/i;
            const honraSectionReu = extractSectionFor(textoCompleto, [markerStartReclamada], [markerEndReclamada]) || textoCompleto;

            dbg('[hcalc] honraSectionAutor length=', honraSectionAutor.length, 'honraSectionReu length=', honraSectionReu.length);

            function findFirstMatch(text, variants) {
                for (const rx of variants) {
                    const m = text.match(rx);
                    if (m && m[1]) return m[1];
                }
                return '';
            }
            const regexPeriodo = /(\d{2}[\/]?\d{2}[\/]?\d{4})\s+a\s+(\d{2}[\/]?\d{2}[\/]?\d{4})/;
            const regexIRPF = /IRPF\s+DEVIDO\s+PELO\s+RECLAMANTE\s+([\d.,]+)/i;

            // Extração
            const verbas = (textoCompleto.match(regexVerbas) || [])[1] || "";
            const fgts = (textoCompleto.match(regexFGTS) || [])[1] || "";
            const inssTotal = (textoCompleto.match(regexINSSTotal) || [])[1] || "";
            const inssAutor = (textoCompleto.match(regexINSSAutor) || [])[1] || "";
            const custas = (textoCompleto.match(regexCustas) || [])[1] || "";
            // Tentar extrair honorários do autor e da reclamada primeiro dentro de suas seções dedicadas,
            // depois no texto completo como fallback.
            let honAutor = findFirstMatch(honraSectionAutor, regexHonAutor_variants) || findFirstMatch(textoCompleto, regexHonAutor_variants) || "";
            let honReu = findFirstMatch(honraSectionReu, regexHonReu_variants) || findFirstMatch(textoCompleto, regexHonReu_variants) || "";

            dbg('[hcalc] extracted honAutor=', honAutor, 'honReu=', honReu);

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
                    // DEFAULT (legado): tratar como honorário do advogado autor salvo se já extraído
                    console.log(`hcalc: "${peritoNome}" → DEFAULT: honorário advogado autor (legado)`);
                    if (!honAutor) {
                        honAutor = peritoValor;
                    } else {
                        console.log('hcalc: honAutor já definido; não sobrescrevendo com peritoValor (legado)');
                    }
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

            // FGTS depositado não será mais testado nem verificado. É sempre devido.
            let fgtsDepositado = false;

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
                honReu,
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
        // Extrai ID do nome do arquivo se possível
        let idNomeArquivo = "";
        const matchNome = file.name.match(/Documento_([a-zA-Z0-9]+)\.pdf/i);
        if (matchNome) idNomeArquivo = matchNome[1];

        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = async (e) => {
                const arrayBuffer = e.target.result;
                // setTimeout libera UI (evita travamento)
                setTimeout(async () => {
                    try {
                        const dados = await extrairDadosPlanilha(arrayBuffer, idNomeArquivo);
                        resolve(dados);
                    } catch (error) {
                        reject(error);
                    }
                }, 50);
            };
            reader.onerror = reject;
            reader.readAsArrayBuffer(file);
        });
    }


    window.normalizarNomeParaComparacao = normalizarNomeParaComparacao;
    window.carregarPDFJSSeNecessario = carregarPDFJSSeNecessario;
    window.processarPlanilhaPDF = processarPlanilhaPDF;
})();
