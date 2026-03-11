// ==UserScript==
// @name         Homologação de Cálculos
// @namespace    http://tampermonkey.net/
// @version      1.16.0
// @description  Refatoração subsidiárias: Principais (Integrais/Parciais) + Verdadeiras Subsidiárias
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @require      https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js
// @connect      cdnjs.cloudflare.com
// @run-at       document-idle
// @grant        unsafeWindow
// ==/UserScript==


(function () {
    'use strict';

    // FILTRO ANTI-IFRAME: Impede execução em iframes (PDF viewer, etc)
    if (window.self !== window.top) {
        return;
    }

    // Marcador de execução
    document.documentElement.setAttribute('data-hcalc-boot', '1');

    // DEBUG: false em produção para reduzir I/O do console
    const HCALC_DEBUG = false;
    const dbg = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err = (...args) => console.error('[hcalc]', ...args);
    if (HCALC_DEBUG) dbg('Script carregado em:', window.location.href);

    if (!window.__hcalcGlobalErrorHooksInstalled) {
        window.__hcalcGlobalErrorHooksInstalled = true;
        window.addEventListener('error', (event) => {
            err('Erro global capturado:', event?.message, event?.filename, event?.lineno, event?.colno, event?.error);
        });
        window.addEventListener('unhandledrejection', (event) => {
            err('Promise rejeitada sem tratamento:', event?.reason);
        });
    }

    // ==========================================
    // ESTADO CENTRAL HCALC
    // ==========================================
    // Centraliza todas as variáveis de estado do script
    // Permite dispose() completo para evitar vazamentos de memória
    if (!window.hcalcState) {
        window.hcalcState = {
            // Cache de partes (limitado a 5 entradas)
            calcPartesCache: {},

            // Flags de execução
            prepRunning: false,

            // Resultados do prep
            prepResult: null,
            timelineData: null,

            // Dados detectados
            peritosConhecimento: [],
            partesData: null,

            // AbortController para cancelamento de operações
            abortController: null,

            // FASE 1: Dados da planilha PJe-Calc (extração PDF)
            planilhaExtracaoData: null,  // {verbas, fgts, inss, data, id, ...}
            planilhaCarregada: false,
            pdfjsLoaded: false,

            // FASE 2: Múltiplos depósitos
            depositosRecursais: [],  // [{idx, tipo, depositante, id, isPrincipal, liberacao}]
            pagamentosAntecipados: [],  // [{idx, id, tipoLib, remValor, remTitulo, devValor}]
            nextDepositoIdx: 0,
            nextPagamentoIdx: 0,

            // FASE 3: Planilhas extras para períodos diversos
            planilhasDisponiveis: [],  // [{id, label, dados}]

            // Método de limpeza completa
            dispose() {
                dbg('Executando dispose() - limpando estado hcalc');

                // Abortar operações em andamento
                if (this.abortController) {
                    this.abortController.abort();
                    this.abortController = null;
                }

                this.calcPartesCache = {};
                this.prepRunning = false;
                this.prepResult = null;
                this.timelineData = null;
                this.peritosConhecimento = [];
                this.partesData = null;
                this.planilhaExtracaoData = null;
                this.planilhaCarregada = false;
                this.planilhasDisponiveis = [];
                this.depositosRecursais = [];
                this.pagamentosAntecipados = [];
                this.nextDepositoIdx = 0;
                this.nextPagamentoIdx = 0;
                dbg('Estado hcalc limpo');
            },

            // Método de reset parcial (mantém cache)
            resetPrep() {
                // Abortar prep em andamento
                if (this.abortController) {
                    this.abortController.abort();
                    this.abortController = null;
                }

                this.prepResult = null;
                this.timelineData = null;
                this.prepRunning = false;
                this.planilhaExtracaoData = null;
                this.planilhaCarregada = false;
            }
        };
    }

    // Aliases de retrocompatibilidade (apontam para hcalcState)
    // Permite que código existente continue funcionando sem modificação
    Object.defineProperty(window, 'calcPartesCache', {
        get() { return window.hcalcState.calcPartesCache; },
        set(val) { window.hcalcState.calcPartesCache = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPrepRunning', {
        get() { return window.hcalcState.prepRunning; },
        set(val) { window.hcalcState.prepRunning = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPrepResult', {
        get() { return window.hcalcState.prepResult; },
        set(val) { window.hcalcState.prepResult = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcTimelineData', {
        get() { return window.hcalcState.timelineData; },
        set(val) { window.hcalcState.timelineData = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPeritosConhecimentoDetectados', {
        get() { return window.hcalcState.peritosConhecimento; },
        set(val) { window.hcalcState.peritosConhecimento = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPartesData', {
        get() { return window.hcalcState.partesData; },
        set(val) { window.hcalcState.partesData = val; },
        configurable: true
    });

    // ==========================================
    // MONITOR DE NAVEGAÇÃO SPA
    // ==========================================
    // Detecta mudança de URL no PJe (SPA) e limpa estado automaticamente
    // Previne vazamento de memória ao trocar de processo sem fechar overlay
    // OTIMIZAÇÃO: History API hooks ao invés de MutationObserver pesado
    let lastUrl = location.href;

    function handleSpaNavigation() {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            dbg('Navegação SPA detectada, limpando estado...');

            // Dispose completo
            if (window.hcalcState) {
                window.hcalcState.dispose();
            }

            // Ocultar overlay se estiver aberto
            const overlay = document.getElementById('homologacao-overlay');
            if (overlay) overlay.style.display = 'none';
        }
    }

    // Intercepta pushState (navegação programática Angular)
    const _pushState = history.pushState.bind(history);
    history.pushState = function (...args) {
        _pushState(...args);
        handleSpaNavigation();
    };

    // Intercepta popstate (botão voltar/avançar)
    window.addEventListener('popstate', handleSpaNavigation);

    // ==========================================
    // EXTRAÇÃO DE PLANILHA PJE-CALC (FASE 1)
    // ==========================================
    // PDF.js carregado via @require (só executa se abrir página PJe)
    // Worker configurado sob demanda (primeira vez que processar PDF)

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

    // prep.js — Preparação pré-overlay para hcalc.js
    // Varre timeline, extrai dados da sentença, cruza peritos com AJ-JT, monta depósitos.
    // Uso: const result = await window.executarPrep(partesData, peritosConhecimento);

    // (IIFE removida para escopo único)

    // ==========================================
    // UTILIDADES
    // ==========================================
    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    function normalizeText(str) {
        return (str || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    }

    // Normaliza data de "17 nov. 2025" para "17/11/2025"
    function normalizarDataTimeline(dataStr) {
        if (!dataStr) return '';
        const meses = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
            'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
        };
        // Padrão: "17 nov. 2025" ou "17 nov 2025"
        const match = dataStr.match(/(\d{1,2})\s+(\w{3})\.?\s+(\d{4})/);
        if (match) {
            const dia = match[1].padStart(2, '0');
            const mes = meses[match[2].toLowerCase()] || '00';
            const ano = match[3];
            return `${dia}/${mes}/${ano}`;
        }
        return dataStr; // Retorna original se não reconhecer
    }

    // Destaca um elemento na timeline (usado por links de recursos)
    function destacarElementoNaTimeline(href) {
        try {
            // Tentar encontrar o elemento pelo href
            const link = document.querySelector(`a[href="${href}"]`);
            if (!link) {
                console.warn('[hcalc] Elemento não encontrado na timeline:', href);
                return;
            }

            // Encontrar o container do item na timeline
            let container = link.closest('li.tl-item-container') ||
                link.closest('.tl-item-container') ||
                link.closest('.timeline-item');

            if (!container) {
                console.warn('[hcalc] Container do item não encontrado');
                return;
            }

            // Scroll suave até o elemento
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Salvar estilo original
            const originalBorder = container.style.border;
            const originalBackground = container.style.background;
            const originalTransition = container.style.transition;

            // Aplicar destaque
            container.style.transition = 'all 0.3s ease';
            container.style.border = '2px solid #fbbf24';
            container.style.background = '#fffbeb';

            // Remover destaque após 3 segundos
            setTimeout(() => {
                container.style.transition = 'all 0.5s ease';
                container.style.border = originalBorder;
                container.style.background = originalBackground;

                // Restaurar transition original após animação
                setTimeout(() => {
                    container.style.transition = originalTransition;
                }, 500);
            }, 3000);

            console.log('[hcalc] Elemento destacado na timeline:', href);
        } catch (error) {
            console.error('[hcalc] Erro ao destacar elemento:', error);
        }
    }

    // ==========================================
    // TIMELINE: VARREDURA ÚNICA
    // ==========================================
    function getTimelineItems() {
        const selectors = ['li.tl-item-container', '.tl-data .tl-item-container', '.timeline-item'];
        for (const sel of selectors) {
            const items = Array.from(document.querySelectorAll(sel));
            if (items.length > 0) return items;
        }
        return [];
    }

    function extractDataFromItem(item) {
        let el = null;
        let prev = item.previousElementSibling;
        while (prev) {
            el = prev.querySelector('.tl-data[name="dataItemTimeline"]') || prev.querySelector('.tl-data');
            if (el) break;
            prev = prev.previousElementSibling;
        }
        if (!el) el = item.querySelector('.tl-data[name="dataItemTimeline"]') || item.querySelector('.tl-data');
        const dataOriginal = (el?.textContent || '').trim();
        return normalizarDataTimeline(dataOriginal);
    }

    function tipoDocumentoDoItem(item) {
        const link = item.querySelector('a.tl-documento[target="_blank"]');
        if (!link) return '';
        const ariaLabel = link.getAttribute('aria-label') || '';
        const m = ariaLabel.match(/Tipo do documento:\s*([^.]+)/i);
        return m ? normalizeText(m[1].trim()) : '';
    }

    function tituloDocumentoDoItem(item) {
        const link = item.querySelector('a.tl-documento[target="_blank"]');
        if (!link) return '';
        const ariaLabel = link.getAttribute('aria-label') || '';
        const m = ariaLabel.match(/Título:\s*\(([^)]+)\)/i);
        return m ? normalizeText(m[1].trim()) : '';
    }

    function hasAnexoNoItem(item) {
        if (!item) return false;
        const sels = [
            'div[name="mostrarOuOcultarAnexos"]',
            'pje-timeline-anexos div[name="areaAnexos"]',
            '.fa-paperclip'
        ];
        return sels.some(s => item.querySelector(s));
    }

    function isPoloPassivoNoItem(item) {
        if (!item) return false;
        const container = item.closest('li.tl-item-container') || item;
        return !!container.querySelector('.icone-polo-passivo, [class*="polo-passivo"]');
    }

    // Extrai o nome da parte do polo passivo a partir do aria-label do div tipoItemTimeline
    // Ex: aria-label="VIBRASIL INDUSTRIA DE ARTEFATOS DE BORRACHA LTDA"
    function nomePassivoDoItem(item) {
        if (!item) return '';
        const container = item.closest('li.tl-item-container') || item;

        // ESTRATÉGIA PRINCIPAL: aria-label do ícone do polo
        const seletores = [
            'div[name="tipoItemTimeline"][aria-label]',
            '[name="tipoItemTimeline"][aria-label]',
            'div.tl-icon[aria-label]',
            '[role="img"][aria-label]'
        ];

        for (const sel of seletores) {
            const elemento = container.querySelector(sel);
            if (elemento) {
                const ariaLabel = elemento.getAttribute('aria-label')?.trim();
                if (ariaLabel && ariaLabel.length > 3) {
                    if (!ariaLabel.toLowerCase().includes('advogado') &&
                        !ariaLabel.toLowerCase().includes('tipo do documento')) {
                        return ariaLabel;
                    }
                }
            }
        }

        // FALLBACK rec.js v1.0: extrair do texto do documento
        const textoDoc = textoDoItem(item);
        const matchEmpresa = textoDoc.match(/^([^-:\n]+)/);
        if (matchEmpresa && matchEmpresa[1].trim().length > 10) {
            const nomeExtraido = matchEmpresa[1].trim();
            if (!/^(recurso|ordinário|revista|ro|rr|documento)$/i.test(nomeExtraido)) {
                return nomeExtraido;
            }
        }

        return 'Reclamada não identificada';
    }

    function hrefDoItem(item) {
        const link = item.querySelector('a.tl-documento[target="_blank"]');
        return link?.href || null;
    }

    function textoDoItem(item) {
        const previewLink = item.querySelector('a.tl-documento[role="button"]:not([target])')
            || item.querySelector('a.tl-documento:not([target])');
        return (previewLink?.textContent || item.textContent || '').replace(/\s+/g, ' ').trim();
    }

    function idDocumentoDoItem(item) {
        // Extrai ID do formato: <span class="ng-star-inserted"> - 44709e4</span>
        const previewLink = item.querySelector('a.tl-documento[role="button"]:not([target])')
            || item.querySelector('a.tl-documento:not([target])');
        if (!previewLink) return null;

        const spans = previewLink.querySelectorAll('span.ng-star-inserted');
        for (let i = spans.length - 1; i >= 0; i--) {
            const texto = spans[i].textContent.trim();
            const match = texto.match(/^\s*-\s*([a-f0-9]{7})$/i);
            if (match) return match[1];
        }
        return null;
    }

    // Varredura única: classifica todos os items da timeline
    function varrerTimeline() {
        const items = getTimelineItems();
        const resultado = {
            sentencas: [],
            acordaos: [],
            editais: [],
            recursosPassivo: [],  // RO/RR + polo passivo + anexo
            honAjJt: []
        };

        items.forEach((item, idx) => {
            const texto = textoDoItem(item);
            const textoNorm = normalizeText(texto);
            const tipoDoc = tipoDocumentoDoItem(item);
            const tituloDoc = tituloDocumentoDoItem(item);
            const data = extractDataFromItem(item);
            const href = hrefDoItem(item);

            // BASE: Apenas dados essenciais (SEM element: item para evitar vazamento DOM)
            const base = {
                idx,
                texto: texto.substring(0, 300), // Limitar tamanho do texto
                data,
                href
            };

            // Sentença
            if (textoNorm.includes('sentenca') || textoNorm.includes('sentença')) {
                resultado.sentencas.push({ ...base, tipo: 'sentenca' });
                return;
            }

            // Acórdão - CAPTURA ID
            if (textoNorm.includes('acordao') && !textoNorm.includes('intima')) {
                const idDoc = idDocumentoDoItem(item);
                resultado.acordaos.push({ ...base, id: idDoc, tipo: 'acordao' });
                return;
            }

            // Recurso Ordinário / Recurso de Revista (polo passivo + anexo)
            if ((tipoDoc === 'recurso ordinario' || tipoDoc === 'recurso de revista'
                || tipoDoc.includes('recurso ordinario') || tipoDoc.includes('recurso de revista'))
                && isPoloPassivoNoItem(item) && hasAnexoNoItem(item)) {
                const tipoRec = tipoDoc.includes('revista') ? 'RR' : 'RO';
                const depositante = nomePassivoDoItem(item);
                resultado.recursosPassivo.push({ ...base, tipoRec, depositante, _itemRef: item });
                return;
            }

            // Honorários Periciais AJ-JT - CAPTURA ID
            if (/peric[ia]*.*aj[\s-]*jt/i.test(tituloDoc) || /peric[ia]*.*aj[\s-]*jt/i.test(texto)) {
                const idDoc = idDocumentoDoItem(item);
                resultado.honAjJt.push({ ...base, id: idDoc, tipo: 'hon_ajjt' });
                return;
            }

            // Edital
            if (textoNorm.includes('edital')) {
                resultado.editais.push({ ...base, tipo: 'edital' });
            }
        });

        // Sentença alvo = mais antiga (última no array, pois timeline é desc)
        return resultado;
    }

    // ==========================================
    // EXTRAÇÃO VIA HTML ORIGINAL
    // ==========================================

    // Abre o documento inline (clica no preview link)
    function abrirDocumentoInline(item) {
        const previewLink = item.querySelector('a.tl-documento[accesskey="v"]:not([target])')
            || item.querySelector('a.tl-documento[role="button"]:not([target])')
            || item.querySelector('a.tl-documento:not([target])');
        if (previewLink) {
            try { previewLink.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); }
            catch (_) { try { previewLink.click(); } catch (_2) { } }
        }
    }

    // Recaptura elemento da timeline pelo href (evita guardar referências DOM)
    function encontrarItemTimeline(href) {
        if (!href) return null;
        const items = getTimelineItems();
        for (const item of items) {
            const link = item.querySelector('a.tl-documento[target="_blank"]');
            if (link && link.href === href) return item;
        }
        return null;
    }

    // ========== INTEGRADO DE rec.js v1.0 ==========

    // Classificação por tipo de anexo
    function classificarAnexo(textoAnexo) {
        const t = textoAnexo.toLowerCase();
        if (/depósito|deposito|preparo/.test(t)) return { tipo: 'Depósito', ordem: 1 };
        if (/garantia|seguro|susep/.test(t)) return { tipo: 'Garantia', ordem: 2 };
        if (/gru|custas/.test(t)) return { tipo: 'Custas', ordem: 3 };
        return { tipo: 'Anexo', ordem: 4 };
    }

    // Expande anexos e retorna lista estruturada
    async function extrairAnexosDoItem(item) {
        const anexos = [];
        try {
            const anexosRoot = item.querySelector('pje-timeline-anexos');
            if (!anexosRoot) return anexos;

            const toggle = anexosRoot.querySelector('div[name="mostrarOuOcultarAnexos"]');
            let anexoLinks = anexosRoot.querySelectorAll('a.tl-documento[id^="anexo_"]');

            if ((!anexoLinks || anexoLinks.length === 0) && toggle) {
                try { toggle.dispatchEvent(new MouseEvent('click', { bubbles: true })); } catch (e) { }
                await sleep(350);
                anexoLinks = anexosRoot.querySelectorAll('a.tl-documento[id^="anexo_"]');
            }

            if (anexoLinks && anexoLinks.length) {
                Array.from(anexoLinks).forEach(anexo => {
                    const texto = (anexo.textContent || '').trim();
                    let id = '';
                    const match = texto.match(/\s-\s([a-f0-9]{7})\s*$/i);
                    if (match) {
                        id = match[1];
                    } else {
                        id = anexo.id || anexo.getAttribute('id') || '';
                    }
                    const { tipo, ordem } = classificarAnexo(texto);
                    anexos.push({ texto, id, tipo, ordem, elemento: anexo });
                });
                anexos.sort((a, b) => a.ordem - b.ordem);
            }
        } catch (error) {
            err('Erro ao extrair anexos:', error);
        }
        return anexos;
    }

    // Expande o toggle de anexos se não estiver expandido
    async function expandirAnexos(container) {
        try {
            const anexosRoot = container.querySelector('pje-timeline-anexos');
            if (!anexosRoot) return false;

            const toggle = anexosRoot.querySelector('div[name="mostrarOuOcultarAnexos"]');
            if (!toggle) return false;

            const jaExpandido = toggle.getAttribute('aria-pressed') === 'true';
            if (jaExpandido) return true;

            toggle.click();
            await sleep(400);
            return true;
        } catch (error) {
            err('Erro ao expandir anexos:', error);
            return false;
        }
    }

    // Destaca elemento na timeline (recebe href, localiza e aplica visual)
    function destacarElementoNaTimeline(href) {
        const container = encontrarItemTimeline(href);
        if (!container) {
            warn('Elemento não encontrado para href:', href);
            return;
        }
        try {
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });

            const originalBorder = container.style.border;
            const originalBackground = container.style.background;
            const originalTransition = container.style.transition;

            container.style.transition = 'all 0.3s ease';
            container.style.border = '2px solid #fbbf24';
            container.style.background = '#fffbeb';

            // Expandir anexos após scroll completar
            setTimeout(async () => { await expandirAnexos(container); }, 500);

            // Remover destaque após 3s
            setTimeout(() => {
                container.style.transition = 'all 0.5s ease';
                container.style.border = originalBorder;
                container.style.background = originalBackground;
                setTimeout(() => { container.style.transition = originalTransition; }, 500);
            }, 3000);
        } catch (error) {
            err('Erro ao destacar elemento:', error);
        }
    }

    // Abre documento inline via href (recaptura elemento dinamicamente)
    function abrirDocumentoInlineViaHref(href) {
        const item = encontrarItemTimeline(href);
        if (!item) return false;
        abrirDocumentoInline(item);
        return true;
    }

    // Clica em "Visualizar HTML original" e lê #previewModeloDocumento
    async function lerHtmlOriginal(timeoutMs = 5000, abortSignal = null) {
        const started = Date.now();

        // 1. Espera o botão aparecer (com suporte a cancelamento)
        let htmlBtn = null;
        while ((Date.now() - started) < timeoutMs) {
            if (abortSignal?.aborted) {
                console.log('[hcalc] lerHtmlOriginal cancelado (aborted)');
                return null;
            }
            htmlBtn = document.querySelector('button[aria-label="Visualizar HTML original"]');
            if (htmlBtn) break;
            await sleep(150); // Reduzido de 200ms para 150ms
        }
        if (!htmlBtn) return null;

        htmlBtn.click();

        // 2. Espera o conteúdo carregar (com suporte a cancelamento)
        let previewEl = null;
        const started2 = Date.now();
        while ((Date.now() - started2) < timeoutMs) {
            if (abortSignal?.aborted) {
                console.log('[hcalc] lerHtmlOriginal cancelado (aborted)');
                return null;
            }
            previewEl = document.getElementById('previewModeloDocumento');
            if (previewEl && (previewEl.innerText || '').trim().length > 200) break;
            await sleep(150); // Reduzido de 200ms para 150ms
        }

        const texto = (previewEl?.innerText || '').trim();
        const html = (previewEl?.innerHTML || '').trim();
        return texto.length > 200 ? { texto, html } : null;
    }

    // Fecha o modal/viewer atual (se houver)
    function fecharViewer() {
        // Tenta fechar o modal de preview
        const closeBtns = document.querySelectorAll(
            'button[aria-label="Fechar"], .mat-dialog-close, mat-dialog-container button.close, .cdk-overlay-backdrop'
        );
        closeBtns.forEach(b => { try { b.click(); } catch (_) { } });
    }

    // ==========================================
    // EXTRAÇÃO DE DADOS DA SENTENÇA
    // ==========================================
    function extrairDadosSentenca(texto) {
        const result = {
            custas: null,
            hsusp: false,
            trteng: false,
            trtmed: false,
            responsabilidade: null,   // 'subsidiaria' | 'solidaria' | null
            honorariosPericiais: []    // { valor, trt }
        };

        // Custas: padrão amplo com flexibilidade para "mínimo", "máximo", "total", etc.
        // Aceita: "no importe [mínimo/máximo/total] de R$ X, calculadas sobre"
        // ou "Custas, pela Reclamada, no importe de R$ 300,00"
        // ou "Custas de R$ 200,00"
        const custasMatch = texto.match(
            /no\s+importe\s+(?:m[ií]nim[oa]\s+|m[áa]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+),?\s*calculadas\s+sobre/i
        ) || texto.match(
            /[Cc]ustas[^,]*,\s*(?:pela\s+)?[Rr]eclamad[ao][^,]*,\s*no\s+importe\s+(?:m[ií]nim[oa]\s+|m[áa]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+)/i
        ) || texto.match(
            /[Cc]ustas[^,]*de\s+R\$\s*([\d.,]+)/i
        );
        if (custasMatch) {
            // Remove vírgulas/pontos extras no final
            result.custas = custasMatch[1].replace(/[.,]+$/, '');
        }

        // Condição suspensiva
        result.hsusp = /obriga[cç][aã]o\s+ficar[aá]\s+sob\s+condi[cç][aã]o\s+suspensiva/i.test(texto);

        // Perícia TRT engenharia
        result.trteng = /honor[aá]rios\s+periciais\s+t[eé]cnicos.*pagos\s+pelo\s+Tribunal/i.test(texto)
            || /pagos\s+pelo\s+Tribunal\s+Regional.*periciais\s+t[eé]cnicos/i.test(texto);

        // Perícia TRT médica
        result.trtmed = /honor[aá]rios\s+periciais\s+m[eé]dicos.*pagos\s+pelo\s+Tribunal/i.test(texto)
            || /pagos\s+pelo\s+Tribunal\s+Regional.*periciais\s+m[eé]dicos/i.test(texto);

        // Responsabilidade
        if (/condenar\s+(de\s+forma\s+)?subsidi[aá]ri/i.test(texto)) {
            result.responsabilidade = 'subsidiaria';
        } else if (/condenar\s+(de\s+forma\s+)?solid[aá]ri/i.test(texto)) {
            result.responsabilidade = 'solidaria';
        }

        // Honorários periciais: buscar todos os trechos com valor + se é TRT
        // Padrão: "honorários periciais ... em R$ 800,00 ... pagos pelo Tribunal"
        const regexHon = /honor[aá]rios\s+periciais[^.]*?R\$\s*([\d.,]+)[^.]*?\./gi;
        let match;
        while ((match = regexHon.exec(texto)) !== null) {
            const trecho = match[0];
            const valor = match[1];
            const trt = /pagos?\s+pelo\s+Tribunal/i.test(trecho)
                || /Tribunal\s+Regional/i.test(trecho)
                || /TRT/i.test(trecho);
            result.honorariosPericiais.push({ valor, trt });
        }

        return result;
    }

    // ==========================================
    // CRUZAMENTO AJ-JT × PERITOS
    // ==========================================
    async function buscarAjJtPeritos(honAjJtItems, peritosConhecimento) {
        const resultados = []; // { nome, trt: true, idAjJt }

        // Set de peritos já encontrados — evita abrir mais docs desnecessários
        const peritosEncontrados = new Set();

        for (const ajjt of honAjJtItems) {
            // Se todos os peritos já foram encontrados, para
            if (peritosEncontrados.size >= peritosConhecimento.length) break;

            // Abre documento via href (recaptura elemento dinamicamente)
            if (!abrirDocumentoInlineViaHref(ajjt.href)) {
                console.warn('[prep] Falha ao abrir AJ-JT:', ajjt.href);
                continue;
            }
            await sleep(600);

            // Lê HTML original
            const resHtml = await lerHtmlOriginal(5000);
            fecharViewer();
            await sleep(300);

            if (!resHtml || !resHtml.texto) continue;

            const textoNorm = normalizeText(resHtml.texto);

            // Procura cada perito de conhecimento no texto
            for (const perito of peritosConhecimento) {
                if (peritosEncontrados.has(perito)) continue;

                const peritoNorm = normalizeText(perito);
                // Match parcial: primeiro nome + último nome
                const partes = peritoNorm.split(/\s+/).filter(Boolean);
                const primeiroNome = partes[0] || '';
                const ultimoNome = partes.length > 1 ? partes[partes.length - 1] : '';

                const found = textoNorm.includes(peritoNorm)
                    || (primeiroNome && ultimoNome && textoNorm.includes(primeiroNome) && textoNorm.includes(ultimoNome));

                if (found) {
                    // Usar ID já extraído da timeline
                    const idAjJt = ajjt.id || ajjt.texto;

                    resultados.push({ nome: perito, trt: true, idAjJt });
                    peritosEncontrados.add(perito);
                }
            }
        }

        return resultados;
    }

    // ==========================================
    // NOTIFICAÇÕES EDITAL
    // ==========================================
    async function buscarPartesEdital(editaisItems, passivo) {
        // Regra maior: se há apenas uma reclamada e há edital, é ela.
        if (passivo.length === 1) {
            return [passivo[0].nome];
        }

        const intimadas = new Set();
        const reclamadas = passivo.map(p => ({ nome: p.nome, nomNorm: normalizeText(p.nome) }));

        for (const edital of editaisItems) {
            if (intimadas.size >= passivo.length) break;

            // Abre edital via href (recaptura elemento dinamicamente)
            if (!abrirDocumentoInlineViaHref(edital.href)) {
                console.warn('[prep] Falha ao abrir edital:', edital.href);
                continue;
            }
            await sleep(600);

            const resHtml = await lerHtmlOriginal(6000, signal, signal);
            fecharViewer();
            await sleep(300);

            if (!resHtml || !resHtml.html) continue;

            const html = resHtml.html;

            const matchComeco = html.match(/<strong[^>]*>\s*EDITAL\s+D.*?<\/strong>/i);
            const matchFim = html.match(/<strong[^>]*>\s*\(http:\/\/pje\.trtsp\.jus\.br\/documentos\)\s*<\/strong>/i);

            let textoAlvo = '';

            if (matchComeco && matchFim && matchFim.index > matchComeco.index) {
                const blocoHtml = html.substring(matchComeco.index, matchFim.index + matchFim[0].length);
                const div = document.createElement('div');
                div.innerHTML = blocoHtml;
                textoAlvo = normalizeText(div.innerText || div.textContent || '');
            } else if (matchComeco) {
                const blocoHtml = html.substring(matchComeco.index, matchComeco.index + 1000);
                const div = document.createElement('div');
                div.innerHTML = blocoHtml;
                textoAlvo = normalizeText(div.innerText || div.textContent || '');
            } else {
                textoAlvo = normalizeText(resHtml.texto);
            }

            for (const r of reclamadas) {
                if (intimadas.has(r.nome)) continue;
                if (textoAlvo.includes(r.nomNorm)) {
                    intimadas.add(r.nome);
                }
            }
        }
        return Array.from(intimadas);
    }

    // ==========================================
    // ORQUESTRADOR PRINCIPAL
    // ==========================================
    async function executarPrep(partesData, peritosConhecimento) {
        // FLAG ANTI-EXECUÇÃO-DUPLA: Previne loops de polling acumulando timers
        if (window.hcalcPrepRunning) {
            console.log('[prep.js] ⚠️ Prep já em execução, ignorando chamada duplicada');
            return;
        }

        // Abortar prep anterior se existir
        if (window.hcalcState.abortController) {
            dbg('[prep] Abortando execução anterior antes de iniciar nova');
            window.hcalcState.abortController.abort();
        }

        // Criar novo AbortController para esta execução
        window.hcalcState.abortController = new AbortController();
        const signal = window.hcalcState.abortController.signal;

        window.hcalcPrepRunning = true;

        try {
            console.log('[prep.js] Iniciando preparação pré-overlay...');
            const partesSafe = partesData && typeof partesData === 'object' ? partesData : {};

            // Resultado padrão
            const prepResult = {
                sentenca: {
                    data: null,
                    href: null,
                    custas: null,
                    hsusp: false,
                    responsabilidade: null,
                    honorariosPericiais: []
                },
                pericia: {
                    trteng: false,
                    trtmed: false,
                    peritosComAjJt: []
                },
                acordaos: [],
                depositos: [],
                editais: [],
                partesIntimadasEdital: []
            };

            // ── ETAPA 1: Varrer timeline (síncrona) ──
            const timeline = varrerTimeline();
            console.log('[prep.js] Timeline varrida:', {
                sentencas: timeline.sentencas.length,
                acordaos: timeline.acordaos.length,
                editais: timeline.editais.length,
                recursosPassivo: timeline.recursosPassivo.length,
                honAjJt: timeline.honAjJt.length
            });

            // ── ETAPA 1.5: Enriquecer recursos com anexos (integrado rec.js) ──
            if (timeline.recursosPassivo.length > 0) {
                dbg('prep', 'Extraindo anexos de', timeline.recursosPassivo.length, 'recursos...');
                for (const rec of timeline.recursosPassivo) {
                    if (rec._itemRef) {
                        rec.anexos = await extrairAnexosDoItem(rec._itemRef);
                        delete rec._itemRef;
                    } else {
                        rec.anexos = [];
                    }
                }
                dbg('prep', 'Anexos extraídos');
            }
            // Garantir limpeza de _itemRef mesmo se não processou
            timeline.recursosPassivo.forEach(r => { delete r._itemRef; });

            // Mapear acórdãos e editais para resultado
            prepResult.acordaos = timeline.acordaos.map(a => ({ data: a.data, href: a.href, id: a.id }));
            prepResult.editais = timeline.editais.map(e => ({ data: e.data, href: e.href }));

            // Depósitos recursais = recursos passivo (só se tem acórdão)
            if (timeline.acordaos.length > 0) {
                prepResult.depositos = timeline.recursosPassivo.map(r => ({
                    tipo: r.tipoRec,
                    texto: r.texto,
                    href: r.href,
                    data: r.data,
                    depositante: r.depositante || '',
                    anexos: r.anexos || []
                }));
            }

            // ── ETAPA 2: AJ-JT — só se tem perito de conhecimento ──
            // ORDEM INVERTIDA: AJ-JT antes de sentença para manter sentença selecionada
            const peritosConh = Array.isArray(peritosConhecimento) ? peritosConhecimento.filter(Boolean) : [];

            if (peritosConh.length > 0 && timeline.honAjJt.length > 0) {
                console.log('[prep.js] Buscando AJ-JT para peritos:', peritosConh);
                prepResult.pericia.peritosComAjJt = await buscarAjJtPeritos(timeline.honAjJt, peritosConh);
                console.log('[prep.js] AJ-JT encontrados:', prepResult.pericia.peritosComAjJt);
            } else if (peritosConh.length > 0) {
                console.log('[prep.js] Peritos de conhecimento detectados mas nenhum AJ-JT na timeline.');
            }

            // ── ETAPA 3: Sentença — abrir e extrair tudo ──
            // MOVIDO PARA DEPOIS DE AJ-JT para ficar selecionada por último
            const sentencaAlvo = timeline.sentencas.length > 0
                ? timeline.sentencas[timeline.sentencas.length - 1]  // mais antiga (última no array)
                : null;

            if (sentencaAlvo) {
                prepResult.sentenca.data = sentencaAlvo.data;
                prepResult.sentenca.href = sentencaAlvo.href;

                // Abrir documento via href (recaptura elemento dinamicamente)
                if (!abrirDocumentoInlineViaHref(sentencaAlvo.href)) {
                    console.warn('[prep] Falha ao abrir sentença:', sentencaAlvo.href);
                } else {
                    await sleep(600);

                    // Ler HTML original
                    const resSent = await lerHtmlOriginal(6000, signal);
                    fecharViewer();
                    await sleep(300);

                    if (resSent && resSent.texto) {
                        const textoSentenca = resSent.texto;
                        console.log('[prep.js] Sentença lida:', textoSentenca.length, 'chars');

                        const dados = extrairDadosSentenca(textoSentenca);
                        prepResult.sentenca.custas = dados.custas;
                        prepResult.sentenca.hsusp = dados.hsusp;
                        prepResult.sentenca.responsabilidade = dados.responsabilidade;
                        prepResult.sentenca.honorariosPericiais = dados.honorariosPericiais;
                        prepResult.pericia.trteng = dados.trteng;
                        prepResult.pericia.trtmed = dados.trtmed;
                    } else {
                        console.warn('[prep.js] Falha ao ler sentença via HTML original.');
                    }
                }
            } else {
                console.warn('[prep.js] Nenhuma sentença encontrada na timeline.');
            }

            // ── ETAPA 4: EDITAL — extrair partes intimadas ──
            const passivoArray = Array.isArray(partesSafe.passivo) ? partesSafe.passivo : [];
            if (timeline.editais.length > 0 && passivoArray.length > 0) {
                console.log('[prep.js] Buscando partes intimadas nos editais...');
                prepResult.partesIntimadasEdital = await buscarPartesEdital(timeline.editais, passivoArray);
                console.log('[prep.js] Partes intimadas por edital:', prepResult.partesIntimadasEdital);
            }

            console.log('[prep.js] Preparação concluída:', prepResult);

            // Disponibilizar globalmente
            window.hcalcPrepResult = prepResult;

            // Liberar flag de execução
            window.hcalcPrepRunning = false;

            return prepResult;

        } catch (error) {
            console.error('[prep.js] Erro durante preparação:', error);
            // Garantir que flag seja liberada mesmo em caso de erro
            window.hcalcPrepRunning = false;
            throw error;
        }
    }

    // Expor prep no escopo global para integração/depuração.
    const prepGlobalObj = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;
    prepGlobalObj.executarPrep = executarPrep;
    if (prepGlobalObj !== window) {
        window.executarPrep = executarPrep;
    }

    // Fim prep (agora global no escopo do arquivo)


    function initializeOverlay() {
        if (window.__hcalcOverlayInitialized) {
            dbg('initializeOverlay ignorado: overlay ja inicializado.');
            return;
        }
        dbg('initializeOverlay iniciado.');
        window.__hcalcOverlayInitialized = true;

        // ==========================================
        // 1. ESTILOS DO OVERLAY E BOTÃO (v1.9 - UI Compacta)
        // ==========================================
        const styles = `
        #btn-abrir-homologacao {
            position: fixed; bottom: 20px; right: 20px; z-index: 99999;
            background: #00509e; color: white; border: none; border-radius: 6px;
            padding: 10px 18px; font-size: 13px; font-weight: bold; cursor: pointer;
            box-shadow: 0 3px 5px rgba(0,0,0,0.3);
        }
        #btn-abrir-homologacao:hover { background: #003d7a; }

        #homologacao-overlay {
            display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: transparent; z-index: 100000; justify-content: flex-end; align-items: flex-start;
            font-family: Arial, sans-serif; pointer-events: none;
        }

        #homologacao-modal {
            background: #fff; width: 630px; max-width: 630px; height: 100vh; max-height: 100vh; overflow-y: auto;
            border-radius: 0; box-shadow: -4px 0 20px rgba(0,0,0,0.25); padding: 10px; margin: 0;
            display: flex; flex-direction: column; gap: 5px; color: #333; pointer-events: all;
        }

        .modal-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 6px; margin-bottom: 3px; }
        .modal-header h2 { margin: 0; color: #00509e; font-size: 15px; }
        .btn-close { background: #cc0000; color: white; border: none; padding: 3px 10px; cursor: pointer; border-radius: 3px; font-weight: bold; font-size: 11px; }

        fieldset { border: 1px solid #ddd; border-radius: 4px; padding: 6px; margin-bottom: 4px; background: #fff; }
        legend { background: #00509e; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; font-weight: bold; }

        .row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; align-items: center; }
        .col { display: flex; flex-direction: column; flex: 1; min-width: 140px; }

        label { font-size: 11px; font-weight: bold; margin-bottom: 3px; color: #555; }
        input[type="text"], input[type="date"] { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 13px; }
        textarea { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 12px; resize: vertical; font-family: Arial, sans-serif; }
        select { padding: 6px; border: 1px solid #aaa; border-radius: 3px; font-size: 13px; }

        .hidden { display: none !important; }
        /* Destaque para o campo atual da coleta */
        .highlight { border: 2px solid #ff9800 !important; background: #fffde7 !important; box-shadow: 0 0 6px rgba(255,152,0,0.4); }

        /* Badges para partes detectadas (v1.9) */
        .partes-badges { display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0; }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            white-space: nowrap;
        }
        .badge-blue { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
        .badge-gray { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }
        .badge-green { background: #d1fae5; color: #047857; border: 1px solid #a7f3d0; }

        .btn-action { background: #28a745; color: white; border: none; padding: 8px 12px; border-radius: 3px; cursor: pointer; font-weight: bold; font-size: 13px; }
        .btn-action:hover { background: #218838; }
        .btn-gravar { background: #00509e; width: 100%; padding: 12px; font-size: 16px; margin-top: 10px; }

        /* Compactar espaçamento interno para caber na tela */
        #homologacao-modal fieldset { padding: 8px 10px; margin-bottom: 6px; }
        #homologacao-modal .row { margin-bottom: 6px; gap: 8px; }
        #homologacao-modal input[type=text],
        #homologacao-modal input[type=date],
        #homologacao-modal select,
        #homologacao-modal textarea { padding: 5px 7px; font-size: 12px; }
        #homologacao-modal label { font-size: 11px; margin-bottom: 2px; }
        #homologacao-modal legend { font-size: 12px; padding: 3px 8px; }
        #homologacao-modal .btn-gravar { padding: 10px; font-size: 15px; margin-top: 10px; }

        /* Estilos do Card de Resumo da Planilha (FASE 1) */
        #resumo-extracao-card {
            width: 260px;
            background: #f8f9fa;
            border: 2px solid #10b981;
            border-radius: 8px;
            padding: 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            pointer-events: all;
            align-self: flex-start;
            margin-right: 8px;
            overflow: hidden;
            flex-shrink: 0;
        }
        #resumo-extracao-card h4 {
            margin: 0;
            padding: 10px 12px;
            border-bottom: 1px solid #10b981;
            cursor: pointer;
            user-select: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: #16a34a;
            background: #f0fdf4;
        }
        #resumo-extracao-card h4:hover { background: #dcfce7; }
        #resumo-body {
            padding: 10px 12px;
            display: none;
        }
        #resumo-conteudo { display: flex; flex-direction: column; gap: 6px; }
        .resumo-item {
            padding: 4px 6px;
            background: white;
            border-radius: 4px;
            border: 1px solid #e5e7eb;
            font-size: 12px;
        }
        .resumo-item strong { color: #16a34a; }
        #btn-reload-planilha {
            margin-top: 8px;
            width: 100%;
            padding: 5px 10px;
            font-size: 11px;
            border-radius: 4px;
            border: 1px solid #10b981;
            background: #fff;
            color: #10b981;
            cursor: pointer;
        }
        #btn-reload-planilha:hover { background: #10b981; color: white; }

        /* Recursos com anexos — integrado de rec.js v1.0 */
        .rec-recurso-card {
            padding: 8px 10px; margin-bottom: 6px;
            border: 1px solid #e5e7eb; border-radius: 5px;
            background: white; cursor: pointer; transition: all 0.2s;
        }
        .rec-recurso-card:hover { background: #f0f9ff; border-color: #3b82f6; }
        .rec-tipo-badge {
            display: inline-block; padding: 1px 7px; border-radius: 3px;
            font-size: 10px; font-weight: 700; color: white;
            background: #3b82f6; margin-right: 6px;
        }
        .rec-anexos-lista { margin-top: 6px; padding-top: 5px; border-top: 1px solid #e5e7eb; display: none; }
        .rec-recurso-card.expandido .rec-anexos-lista { display: block; }
        .rec-anexo-item {
            display: flex; align-items: center; gap: 6px;
            padding: 3px 4px; border-radius: 3px; cursor: pointer;
            font-size: 11px; transition: background 0.15s;
        }
        .rec-anexo-item:hover { background: #f3f4f6; }
        .rec-anexo-badge {
            padding: 1px 5px; border-radius: 2px;
            font-size: 10px; font-weight: 600; color: white; white-space: nowrap;
        }
        .rec-anexo-id {
            font-size: 10px; background: #f3f4f6;
            padding: 1px 4px; border-radius: 2px;
            font-family: monospace; color: #374151; user-select: all;
        }
        .rec-seta-toggle { font-size: 10px; color: #9ca3af; margin-left: auto; }
    `;
        if (!document.getElementById('hcalc-overlay-style')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'hcalc-overlay-style';
            styleSheet.innerText = styles;
            document.head.appendChild(styleSheet);
        }

        // ==========================================
        // 2. HTML DO OVERLAY (ESTRUTURA)
        // ==========================================
        const htmlModal = `
    <button id="btn-abrir-homologacao">📄 Carregar Planilha</button>
    <input type="file" id="input-planilha-pdf" accept=".pdf" style="display: none;">
    <div id="homologacao-overlay">
        <!-- Card de Resumo da Planilha Extraída (à esquerda) -->
        <div id="resumo-extracao-card" style="display:none">
            <h4 id="resumo-toggle">
                <span>📋 Planilha Carregada</span>
                <span id="resumo-seta">▶</span>
            </h4>
            <div id="resumo-body">
                <div id="resumo-conteudo"></div>
                <button id="btn-reload-planilha">🔄 Recarregar PDF</button>
            </div>
        </div>
       
        <div id="homologacao-modal">
            <div class="modal-header">
                <h2>Assistente de Homologação</h2>
                <button class="btn-close" id="btn-fechar">X Fechar</button>
            </div>



            <!-- SEÇÃO 1 e 2: BASE E PARTE -->
            <fieldset>
                <legend>Cálculo Base e Autoria</legend>
                <div class="row">
                    <div class="col">
                        <label>Origem do Cálculo</label>
                        <select id="calc-origem">
                            <option value="pjecalc" selected>PJeCalc</option>
                            <option value="outros">Outros</option>
                        </select>
                    </div>
                    <div class="col" id="col-pjc">
                        <label><input type="checkbox" id="calc-pjc" checked> Acompanha arquivo .PJC?</label>
                    </div>
                    <div class="col">
                        <label>Autor do Cálculo</label>
                        <select id="calc-autor">
                            <option value="autor" selected>Reclamante (Autor)</option>
                            <option value="reclamada">Reclamada</option>
                            <option value="perito">Perito</option>
                        </select>
                    </div>
                    <div class="col hidden" id="col-esclarecimentos">
                        <label><input type="checkbox" id="calc-esclarecimentos" checked> Esclarecimentos do Perito?</label>
                        <input type="text" id="calc-peca-perito" placeholder="Id da Peça">
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 3: ATUALIZAÇÃO -->
            <fieldset>
                <legend>Atualização</legend>
                <div class="row">
                    <div class="col">
                        <label>Índice de Atualização</label>
                        <select id="calc-indice">
                            <option value="adc58" selected>SELIC / IPCA-E (ADC 58)</option>
                            <option value="tr">TR / IPCA-E (Casos Antigos)</option>
                        </select>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 5: DADOS COPIADOS DA PLANILHA (ÚNICO FIELDSET) -->
            <fieldset>
                <legend>Dados Copiados da Planilha</legend>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">1) Identificação, Datas, Principal e FGTS</label>
                    <div class="row">
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Id da Planilha</label>
                            <input type="text" id="val-id" class="coleta-input" placeholder="Id #XXXX">
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Data da Atualização</label>
                            <input type="text" id="val-data" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col" style="flex: 1;">
                            <label>Crédito Principal (ou Total)</label>
                            <input type="text" id="val-credito" class="coleta-input" placeholder="R$ Crédito Principal">
                        </div>
                    </div>
                    <div class="row" style="align-items: center; gap: 10px; margin-bottom: 5px;">
                        <div class="col" style="flex: 0 0 auto;">
                            <label><input type="checkbox" id="calc-fgts" checked> FGTS apurado separado?</label>
                        </div>
                        <div class="col" id="fgts-radios" style="flex: 0 0 auto; display: flex; gap: 12px;">
                            <label style="margin: 0;"><input type="radio" name="fgts-tipo" value="devido" checked> Devido</label>
                            <label style="margin: 0;"><input type="radio" name="fgts-tipo" value="depositado"> Depositado</label>
                        </div>
                    </div>
                    <div class="row" id="row-fgts-valor">
                        <div class="col" id="col-fgts-val" style="flex: 0 0 auto;">
                            <label style="font-size: 11px; margin-bottom: 2px;">Valor FGTS Separado</label>
                            <input type="text" id="val-fgts" class="coleta-input" placeholder="R$ FGTS" style="width: 140px;">
                        </div>
                    </div>
                    <div class="row hidden" id="col-juros-val">
                        <div class="col">
                            <label>Juros</label>
                            <input type="text" id="val-juros" placeholder="R$ Juros">
                        </div>
                        <div class="col">
                            <label>Data de Ingresso</label>
                            <input type="date" id="data-ingresso">
                        </div>
                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">2) INSS (Autor e Reclamada) e IR</label>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col">
                            <label>INSS - Desconto (Reclamante)</label>
                            <input type="text" id="val-inss-rec" class="coleta-input" placeholder="R$ INSS Reclamante (Desconto)">
                        </div>
                        <div class="col">
                            <label>INSS - Total da Empresa (Reclamada)</label>
                            <input type="text" id="val-inss-total" class="coleta-input" placeholder="R$ INSS Total / Reclamada">
                        </div>
                    </div>
                    <div class="row" style="margin-top: 5px;">
                        <div class="col">
                            <label><input type="checkbox" id="ignorar-inss"> Não há INSS</label>
                            <small style="color: #666; display: block;">*INSS Reclamada = Subtração automática se PJeCalc marcado.</small>
                        </div>
                        <div class="col">
                            <label>Imposto de Renda</label>
                            <select id="irpf-tipo" style="margin-bottom: 5px; width: 100%;">
                                <option value="isento" selected>Não há</option>
                                <option value="informar">Informar Valores</option>
                            </select>
                            <div id="irpf-campos" class="hidden" style="display:flex; gap: 5px;">
                                <input type="text" id="val-irpf-base" placeholder="Base (R$)" style="flex:1;">
                                <input type="text" id="val-irpf-meses" placeholder="Meses" style="flex:1;">
                            </div>
                        </div>
                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; margin-bottom: 6px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">3) Honorários Advocatícios</label>
                    <div class="row" style="margin-bottom: 0; align-items: flex-start;">

                        <!-- Coluna AUTOR -->
                        <div class="col" style="flex: 1; min-width: 160px;">
                            <label>Honorários Adv Autor</label>
                            <input type="text" id="val-hon-autor" class="coleta-input highlight" placeholder="R$ Honorários Autor">
                            <label style="font-size: 11px; margin-top: 4px; display: block;">
                                <input type="checkbox" id="ignorar-hon-autor"> Não há honorários autor
                            </label>
                        </div>

                        <!-- Coluna RÉU -->
                        <div class="col" style="flex: 1; min-width: 160px;">
                            <label>
                                <input type="checkbox" id="chk-hon-reu" checked style="margin-right: 5px;">Não há Honorários Adv Réu
                            </label>
                            <div id="hon-reu-campos" class="hidden" style="margin-top: 6px;">
                                <label style="font-size: 11px; display: block; margin-bottom: 6px;">
                                    <input type="checkbox" id="chk-hon-reu-suspensiva" checked> Condição Suspensiva
                                </label>
                                <div style="display: flex; gap: 8px; flex-direction: column; margin-bottom: 6px;">
                                    <label style="font-size: 11px;">
                                        <input type="radio" name="rad-hon-reu-tipo" value="percentual" checked> Percentual
                                    </label>
                                    <label style="font-size: 11px;">
                                        <input type="radio" name="rad-hon-reu-tipo" value="valor"> Valor Informado
                                    </label>
                                </div>
                                <div id="hon-reu-perc-campo" style="margin-bottom: 4px;">
                                    <input type="text" id="val-hon-reu-perc" class="coleta-input" value="5%" placeholder="%" style="width: 80px;">
                                </div>
                                <div id="hon-reu-valor-campo" class="hidden" style="margin-bottom: 4px;">
                                    <input type="text" id="val-hon-reu" class="coleta-input" placeholder="R$ Honorários Réu" style="width: 140px;">
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

                <div style="padding: 8px; border: 1px dashed #d9d9d9; border-radius: 4px; background: #fff;">
                    <label style="display:block; margin-bottom: 5px; color:#00509e; font-size: 12px;">4) Custas</label>
                    <div class="row" style="margin-bottom: 5px;">
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Valor</label>
                            <input type="text" id="val-custas" class="coleta-input" placeholder="R$ Custas">
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Status</label>
                            <select id="custas-status">
                                <option value="devidas" selected>Devidas</option>
                                <option value="pagas">Já Pagas</option>
                            </select>
                        </div>
                        <div class="col" style="flex: 0 0 140px;">
                            <label>Origem</label>
                            <select id="custas-origem">
                                <option value="sentenca" selected>Sentença</option>
                                <option value="acordao">Acórdão</option>
                            </select>
                        </div>
                    </div>
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col" id="custas-data-col" style="flex: 1;">
                            <label>Data Custas <small style="color: #666;">(vazio = mesma planilha)</small></label>
                            <input type="text" id="custas-data-origem" class="coleta-input" placeholder="DD/MM/AAAA">
                        </div>
                        <div class="col hidden" id="custas-acordao-col" style="flex: 1;">
                            <label>Acórdão</label>
                            <select id="custas-acordao-select">
                                <option value="">Selecione o acórdão</option>
                            </select>
                        </div>
                    </div>
                </div>
            </fieldset>

            <!-- SEÇÃO 6: RESPONSABILIDADE -->
            <fieldset>
                <legend>Responsabilidade</legend>
                <div class="row">
                    <select id="resp-tipo">
                        <option value="unica">Reclamada Única</option>
                        <option value="solidarias">Devedoras Solidárias</option>
                        <option value="subsidiarias" selected>Devedoras Subsidiárias</option>
                    </select>
                </div>
                <div id="resp-sub-opcoes" class="row">
                    <label><input type="checkbox" id="resp-integral" checked> Responde pelo período total</label>
                    <label style="margin-left: 15px;"><input type="checkbox" id="resp-diversos"> Períodos Diversos (Gera estrutura para preencher)</label>
                </div>
            </fieldset>

            <!-- SEÇÃO 6.1: PERÍODOS DIVERSOS (Dinâmico) -->
            <fieldset id="resp-diversos-fieldset" class="hidden">
                <legend>Períodos Diversos - Cálculos Separados por Reclamada</legend>
                <div class="row" style="margin-bottom: 15px;">
                    <div class="col">
                        <label style="font-weight: bold;">Devedora Principal</label>
                        <select id="resp-devedora-principal" style="width: 100%; padding: 8px;">
                            <option value="">Selecione a devedora principal...</option>
                        </select>
                        <small style="color: #666; display: block; margin-top: 5px;">*Padrão: primeira reclamada</small>
                    </div>
                </div>
                <div class="row" style="margin-bottom: 15px; font-size: 13px; color: #555;">
                    <label>Preencha período, planilha e tipo (Principal/Subsidiária) para cada reclamada com responsabilidade diversa:</label>
                </div>
                <div id="resp-diversos-container"></div>
                <button type="button" class="btn-action" id="btn-adicionar-periodo" style="margin-top: 10px;">+ Adicionar Período Diverso</button>
            </fieldset>

            <!-- Links de Sentença e Acórdão -->
            <fieldset style="border: none; padding: 8px 0; margin: 8px 0;">
                <div id="link-sentenca-acordao-container"></div>
            </fieldset>

            <!-- SEÇÃO 7B: HONORÁRIOS PERICIAIS (auto-esconde se não detectar perito) -->
            <fieldset id="fieldset-pericia-conh" class="hidden">
                <legend>Honorários Periciais <span id="link-sentenca-container"></span></legend>
                <div class="row">
                    <div class="col">
                        <label><input type="checkbox" id="chk-perito-conh"> Honorários Periciais (Conhecimento)</label>
                        <div id="perito-conh-campos" class="hidden" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-nome" placeholder="Nome do Perito">
                            <select id="perito-tipo-pag">
                                <option value="reclamada" selected>Pago pela Reclamada (Valor)</option>
                                <option value="trt">Pago pelo TRT (Autor Sucumbente)</option>
                            </select>
                            <input type="text" id="val-perito-valor" placeholder="R$ Valor ou ID TRT">
                            <input type="text" id="val-perito-data" placeholder="Data da Sentença">
                        </div>
                    </div>
                </div>
                <div class="row hidden" id="row-perito-contabil">
                    <div class="col">
                        <label>Honorários Periciais (Contábil - Rogério)</label>
                        <div id="perito-contabil-campos" style="margin-top: 5px; display: flex; gap: 10px;">
                            <input type="text" id="val-perito-contabil-valor" placeholder="Valor dos honorários contábeis">
                        </div>
                    </div>
                </div>
            </fieldset>

            <!-- Custas já foram movidas para o card 4 acima -->

            <!-- SEÇÃO 8: DEPÓSITOS -->
            <fieldset id="fieldset-deposito">
                <legend>Depósitos</legend>
                <div class="row">
                    <label id="label-chk-deposito"><input type="checkbox" id="chk-deposito"> Há Depósito Recursal?</label>
                    <label style="margin-left: 20px;"><input type="checkbox" id="chk-pag-antecipado"> Pagamento Antecipado</label>
                </div>

                <!-- CONTAINER DE DEPÓSITOS RECURSAIS (dinâmico) -->
                <div id="deposito-campos" class="hidden">
                    <div id="depositos-container"></div>
                    <button type="button" id="btn-add-deposito" class="btn-action" style="margin-top: 8px; padding: 4px 12px; font-size: 11px;">+ Adicionar Depósito Recursal</button>
                </div>

                <!-- CONTAINER DE PAGAMENTOS ANTECIPADOS (dinâmico) -->
                <div id="pag-antecipado-campos" class="hidden">
                    <div id="pagamentos-container"></div>
                    <button type="button" id="btn-add-pagamento" class="btn-action" style="margin-top: 8px; padding: 4px 12px; font-size: 11px;">+ Adicionar Pagamento</button>
                </div>
            </fieldset>

            <!-- SEÇÃO 9: INTIMAÇÕES -->
            <fieldset id="fieldset-intimacoes">
                <legend>Intimações</legend>
                <div id="lista-intimacoes-container">
                    <small style="color:#666; font-style:italic;">Aguardando leitura das partes...</small>
                </div>
                <div id="links-editais-container" class="hidden" style="margin-top: 10px; border-top: 1px dashed #ccc; padding-top: 10px;">
                    <label style="font-weight:bold; font-size:12px; color:#5b21b6;">Editais Detectados na Timeline:</label>
                    <div id="links-editais-lista"></div>
                </div>
            </fieldset>

            <button class="btn-action btn-gravar" id="btn-gravar">GRAVAR DECISÃO (Copiar p/ PJe)</button>
        </div>
    </div>
    `;
        // Check robusto: Remover overlay antigo se existir (previne duplicação)
        const existingOverlay = document.getElementById('homologacao-overlay');
        const existingBtn = document.getElementById('btn-abrir-homologacao');

        if (existingOverlay || existingBtn) {
            dbg('Overlay já existe, removendo versão antiga antes de recriar');
            existingOverlay?.remove();
            existingBtn?.remove();
        }

        // Inserir HTML limpo
        document.body.insertAdjacentHTML('beforeend', htmlModal);
        dbg('Overlay HTML inserido no DOM.');

        // Toggle colapso/expansão do card de resumo
        const resumoToggle = document.getElementById('resumo-toggle');
        const resumoBody = document.getElementById('resumo-body');
        const resumoSeta = document.getElementById('resumo-seta');
        if (resumoToggle && resumoBody) {
            resumoToggle.addEventListener('click', () => {
                const aberto = resumoBody.style.display !== 'none';
                resumoBody.style.display = aberto ? 'none' : 'block';
                if (resumoSeta) resumoSeta.textContent = aberto ? '▶' : '▼';
            });
        }

        if (!document.getElementById('btn-abrir-homologacao') || !document.getElementById('homologacao-overlay')) {
            err('Falha apos insercao: elementos principais do overlay nao encontrados.');
            return;
        }

        // ==========================================
        // 3. LÓGICA DE INTERFACE E EVENTOS (TOGGLES)
        // ==========================================
        const $ = (id) => document.getElementById(id);
        dbg('Binding de eventos iniciado.');

        // ==========================================
        // FASE 1: Sistema de Fases do Botão
        // ==========================================
        $('btn-abrir-homologacao').onclick = async () => {
            const btn = $('btn-abrir-homologacao');
            const inputFile = $('input-planilha-pdf');

            // FASE 1: Carregar Planilha (estado inicial)
            if (!window.hcalcState.planilhaCarregada) {
                dbg('FASE 1: Clique em Carregar Planilha');
                inputFile.click(); // Abre file picker
                return;
            }

            // FASE 3: Gerar Homologação (após planilha carregada)
            dbg('FASE 3: Clique em Gerar Homologação');
            try {
                // Executar prep.js: varredura + extração da sentença + AJ-JT
                const peritosConh = window.hcalcPeritosConhecimentoDetectados || [];
                const partesData = window.hcalcPartesData || {};
                const prep = await executarPrep(partesData, peritosConh);

                // CORREÇÃO 1: Salvar globalmente para preencherDepositosAutomaticos
                window.hcalcLastPrepResult = prep;

                // Retrocompat: manter window.hcalcTimelineData para construirSecaoIntimacoes
                window.hcalcTimelineData = {
                    sentenca: prep.sentenca.data ? { data: prep.sentenca.data, href: prep.sentenca.href } : null,
                    acordaos: prep.acordaos,
                    editais: prep.editais
                };

                // Strikethrough no label de depósito recursal se não há acórdão
                const labelDeposito = $('label-chk-deposito');
                if (labelDeposito) {
                    labelDeposito.style.textDecoration = prep.acordaos.length === 0 ? 'line-through' : 'none';
                }

                // Link sentença (info inline no card de custas)
                const linkSentencaContainer = $('link-sentenca-container');
                if (linkSentencaContainer) {
                    linkSentencaContainer.innerHTML = '';
                    if (prep.sentenca.data) {
                        const info = [];
                        if (prep.sentenca.custas) info.push(`Custas: R$${prep.sentenca.custas}`);
                        if (prep.sentenca.responsabilidade) info.push(`Resp: ${prep.sentenca.responsabilidade}`);

                        // Honorários periciais: prioriza AJ-JT, só mostra sentença se não tiver AJ-JT
                        if (prep.pericia.peritosComAjJt.length > 0) {
                            info.push(`Hon.Periciais: ${prep.pericia.peritosComAjJt.length} AJ-JT detectado(s)`);
                        } else if (prep.sentenca.honorariosPericiais.length > 0) {
                            info.push(`Hon.Periciais: ${prep.sentenca.honorariosPericiais.map(h => 'R$' + h.valor + (h.trt ? ' (TRT)' : '')).join(', ')}`);
                        }

                        linkSentencaContainer.innerHTML = `<span style="font-size:12px; color:#16a34a;">✔ Sentença: ${prep.sentenca.data}${info.length ? ' | ' + info.join(' | ') : ''}</span>`;
                    }
                }

                // Links clicáveis de Sentença e Acórdão (fieldset separado)
                const linkSentencaAcordaoContainer = $('link-sentenca-acordao-container');
                if (linkSentencaAcordaoContainer) {
                    linkSentencaAcordaoContainer.innerHTML = '';

                    // Link da Sentença (clicável)
                    if (prep.sentenca.href) {
                        const sentencaLink = document.createElement('a');
                        sentencaLink.href = prep.sentenca.href;
                        sentencaLink.target = '_blank';
                        sentencaLink.innerHTML = `<i class="fas fa-external-link-alt"></i> Sentença${prep.sentenca.data ? ' - ' + prep.sentenca.data : ''}`;
                        sentencaLink.style.cssText = 'display:block; color:#16a34a; font-size:12px; margin-bottom:5px; text-decoration:none; font-weight:600;';
                        linkSentencaAcordaoContainer.appendChild(sentencaLink);
                    }

                    // Links de Acórdãos
                    if (prep.acordaos.length > 0) {
                        prep.acordaos.forEach((acordao, i) => {
                            if (acordao.href) {
                                const lbl = prep.acordaos.length > 1 ? `Acórdão ${i + 1}` : `Acórdão`;
                                const a = document.createElement('a');
                                a.href = acordao.href;
                                a.target = "_blank";
                                a.innerHTML = `<i class="fas fa-external-link-alt"></i> ${lbl}${acordao.data ? ' - ' + acordao.data : ''}`;
                                a.style.cssText = "display:block; color:#00509e; font-size:12px; margin-top:5px; text-decoration:none;";
                                linkSentencaAcordaoContainer.appendChild(a);
                            }
                        });

                        // RECURSOS COM ANEXOS (integrado de rec.js v1.0)
                        if (prep.depositos.length > 0) {
                            const recDiv = document.createElement('div');
                            recDiv.style.cssText = 'margin-top:8px; padding:6px; background:#fffde7; border:1px solid #fbbf24; border-radius:4px;';
                            recDiv.innerHTML = `<strong style="font-size:11px;color:#92400e">📎 Recursos das Reclamadas (${prep.depositos.length})</strong>`;

                            prep.depositos.forEach((dep, depIdx) => {
                                const card = document.createElement('div');
                                card.className = 'rec-recurso-card';
                                card.dataset.href = dep.href || '';

                                const corBadge = { 'Depósito': '#10b981', 'Garantia': '#f59e0b', 'Custas': '#ef4444', 'Anexo': '#6b7280' };

                                let anexosHtml = '';
                                if (dep.anexos && dep.anexos.length > 0) {
                                    anexosHtml = `<div class="rec-anexos-lista">` +
                                        dep.anexos.map((ax, axIdx) =>
                                            `<div class="rec-anexo-item" data-dep-idx="${depIdx}" data-ax-idx="${axIdx}">
                                            <span class="rec-anexo-badge" style="background:${corBadge[ax.tipo] || '#6b7280'}">${ax.tipo}</span>
                                            <code class="rec-anexo-id">${ax.id || 'sem id'}</code>
                                            <span style="font-size:10px;color:#6b7280;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:120px" title="${ax.texto}">${ax.texto.substring(0, 40)}</span>
                                        </div>`
                                        ).join('') +
                                        `</div>`;
                                }

                                card.innerHTML = `
                                <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
                                    <span class="rec-tipo-badge">${dep.tipo || 'RO'}</span>
                                    <span style="font-size:11px;color:#92400e;font-weight:600;flex:1">${dep.depositante || 'Parte não identificada'}</span>
                                    <span style="font-size:10px;color:#6b7280">${dep.data || 'sem data'}</span>
                                    ${dep.anexos && dep.anexos.length > 0 ? `<span class="rec-seta-toggle">▶ ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}</span>` : ''}
                                </div>
                                ${anexosHtml}`;

                                card.addEventListener('click', e => {
                                    const axItem = e.target.closest('.rec-anexo-item');
                                    if (axItem) {
                                        e.stopPropagation();
                                        const axIdx = parseInt(axItem.dataset.axIdx, 10);
                                        const ax = dep.anexos[axIdx];
                                        if (ax && ax.elemento) {
                                            const closeBtns = document.querySelectorAll('button[aria-label="Fechar"], .mat-dialog-close, button.ui-dialog-titlebar-close');
                                            closeBtns.forEach(b => { try { b.click(); } catch (e) { } });
                                            setTimeout(() => {
                                                try { ax.elemento.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
                                                catch (err) { err('Erro ao clicar no anexo:', err); }
                                            }, 300);
                                        }
                                        return;
                                    }

                                    card.classList.toggle('expandido');
                                    const seta = card.querySelector('.rec-seta-toggle');
                                    if (seta) seta.textContent = card.classList.contains('expandido')
                                        ? `▼ ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}`
                                        : `▶ ${dep.anexos.length} anexo${dep.anexos.length > 1 ? 's' : ''}`;
                                    if (dep.href) destacarElementoNaTimeline(dep.href);
                                });

                                recDiv.appendChild(card);
                            });

                            linkSentencaAcordaoContainer.appendChild(recDiv);
                        }
                    } else {
                        // Aviso quando não há acórdão
                        const avisoDiv = document.createElement('div');
                        avisoDiv.style.cssText = 'margin-top:8px; padding:8px; background:#fef2f2; border:1px solid #ef4444; border-radius:4px;';
                        avisoDiv.innerHTML = `<span style="font-size:12px; color:#dc2626; font-weight:600;">⚠ Não há Acórdão</span>`;
                        linkSentencaAcordaoContainer.appendChild(avisoDiv);
                    }
                }

                // Preencher custas automaticamente - PRIORIZA PLANILHA
                if (window.hcalcState.planilhaExtracaoData?.custas && $('val-custas')) {
                    $('val-custas').value = window.hcalcState.planilhaExtracaoData.custas;
                    // Data das custas = data de liquidação da planilha (prevalece sobre sentença)
                    if (window.hcalcState.planilhaExtracaoData.dataAtualizacao && $('custas-data-origem')) {
                        $('custas-data-origem').value = window.hcalcState.planilhaExtracaoData.dataAtualizacao;
                    }
                } else if (prep.sentenca.custas && $('val-custas')) {
                    $('val-custas').value = prep.sentenca.custas;
                    // Data das custas = data da sentença (apenas se não há planilha)
                    if (prep.sentenca.data && $('custas-data-origem')) {
                        $('custas-data-origem').value = prep.sentenca.data;
                    }
                }

                // Depósito recursal: visível se tem acórdãos
                const fieldsetDeposito = $('fieldset-deposito');
                if (prep.acordaos.length === 0) {
                    if (fieldsetDeposito) fieldsetDeposito.classList.add('hidden');
                } else {
                    if (fieldsetDeposito) fieldsetDeposito.classList.remove('hidden');
                }

                // Povoar select de acórdãos se existirem
                const custasAcordaoSelect = $('custas-acordao-select');
                if (custasAcordaoSelect && prep.acordaos.length > 0) {
                    custasAcordaoSelect.innerHTML = '<option value="">Selecione o acórdão</option>';
                    prep.acordaos.forEach((acordao, i) => {
                        const opt = document.createElement('option');
                        opt.value = i;
                        opt.textContent = `Acórdão ${i + 1}${acordao.data ? ' - ' + acordao.data : ''}`;
                        opt.dataset.data = acordao.data || '';
                        opt.dataset.id = acordao.id || '';
                        custasAcordaoSelect.appendChild(opt);
                    });
                }

                // Editais
                const editaisContainer = $('links-editais-container');
                const editaisLista = $('links-editais-lista');
                if (editaisContainer && editaisLista) {
                    editaisLista.innerHTML = '';
                    if (prep.editais.length > 0) {
                        editaisContainer.classList.remove('hidden');
                        prep.editais.forEach((edital, i) => {
                            if (edital.href) {
                                const btn = document.createElement('a');
                                btn.href = edital.href;
                                btn.target = "_blank";
                                btn.innerHTML = `<i class="fas fa-external-link-alt"></i> Edital ${i + 1}`;
                                btn.style.cssText = "display:inline-block; margin-right:10px; color:#00509e; font-size:12px; text-decoration:none;";
                                editaisLista.appendChild(btn);
                            }
                        });
                    } else {
                        editaisContainer.classList.add('hidden');
                    }
                }

                // ==========================================
                // REGRAS AUTO-PREENCHIMENTO (prep sobrepõe defaults)
                // ==========================================

                // REGRA 1: Depósito recursal — disparar evento onChange para unificar fluxo
                // CORREÇÃO 2: Usar dispatchEvent em vez de manipulação direta do DOM
                if (prep.depositos.length > 0) {
                    console.log('[INICIALIZAÇÃO] Detectados', prep.depositos.length, 'recursos com depósito/garantia');

                    const chkDep = $('chk-deposito');
                    if (chkDep) {
                        chkDep.checked = true;
                        // Disparar onChange sintético — aciona visibilidade E preencherDepositosAutomaticos
                        // de forma unificada, eliminando dessincronização
                        chkDep.dispatchEvent(new Event('change', { bubbles: true }));
                        console.log('[INICIALIZAÇÃO] Evento change disparado');
                    }
                }

                // REGRA 2: Perito conhecimento + TRT / AJ-JT match
                const peritoTipoEl = $('perito-tipo-pag');
                const peritoValorEl = $('val-perito-valor');
                const peritoDataEl = $('val-perito-data');
                if (prep.pericia.peritosComAjJt.length > 0) {
                    // Perito casou com AJ-JT — pago pelo TRT
                    const match = prep.pericia.peritosComAjJt[0];
                    if (peritoTipoEl) peritoTipoEl.value = 'trt';
                    if (peritoValorEl) peritoValorEl.value = match.idAjJt || '';
                } else if (prep.sentenca.honorariosPericiais.length > 0) {
                    // Honorários periciais na sentença
                    const hon = prep.sentenca.honorariosPericiais[0];
                    if (hon.trt && peritoTipoEl) {
                        peritoTipoEl.value = 'trt';
                    }
                    // Sempre preencher valor se detectado
                    if (peritoValorEl && !peritoValorEl.value) {
                        peritoValorEl.value = 'R$' + hon.valor;
                    }
                }
                // Data da sentença no campo de data do perito
                if (prep.sentenca.data && peritoDataEl && !peritoDataEl.value) {
                    peritoDataEl.value = prep.sentenca.data;
                }

                // REGRA 3 e 4: Responsabilidade (subsidiária / solidária)
                const respTipoEl = $('resp-tipo');
                const respSubOpcoes = $('resp-sub-opcoes');
                const passivo = window.hcalcPartesData?.passivo || [];
                if (prep.sentenca.responsabilidade && respTipoEl) {
                    if (prep.sentenca.responsabilidade === 'subsidiaria') {
                        respTipoEl.value = 'subsidiarias';
                        if (respSubOpcoes) respSubOpcoes.classList.remove('hidden');
                    } else if (prep.sentenca.responsabilidade === 'solidaria') {
                        respTipoEl.value = 'solidarias';
                        if (respSubOpcoes) respSubOpcoes.classList.add('hidden');
                    }
                } else if (passivo.length <= 1 && respTipoEl) {
                    respTipoEl.value = 'unica';
                    if (respSubOpcoes) respSubOpcoes.classList.add('hidden');
                }

                // REGRA 5: Custas
                // Sempre padrão = sentença (usuário pode mudar para acórdão se necessário)
                const custasStatusEl = $('custas-status');
                const custasOrigemEl = $('custas-origem');
                if (prep.sentenca.custas) {
                    // ATENÇÃO: Não sobrepõe se planilha já preencheu custas
                    if ($('val-custas') && !window.hcalcState.planilhaExtracaoData?.custas) {
                        $('val-custas').value = prep.sentenca.custas;
                    }
                    // Sempre usa sentença como padrão
                    if (custasStatusEl) custasStatusEl.value = 'devidas';
                    if (custasOrigemEl) custasOrigemEl.value = 'sentenca';
                    // ATENÇÃO: Não sobrepõe data se planilha já preencheu
                    if ($('custas-data-origem') && prep.sentenca.data && !window.hcalcState.planilhaExtracaoData?.custas) {
                        $('custas-data-origem').value = prep.sentenca.data;
                    }
                }

                // REGRA 6: hsusp → Honorários Adv. Réu com condição suspensiva
                const chkHonReu = $('chk-hon-reu');
                const honReuCampos = $('hon-reu-campos');
                if (prep.sentenca.hsusp) {
                    // Lógica invertida: desmarcar "Não há" para mostrar campos
                    if (chkHonReu) chkHonReu.checked = false;
                    if (honReuCampos) honReuCampos.classList.remove('hidden');

                    const radSusp = document.querySelector('input[name="rad-hon-reu"][value="suspensiva"]');
                    if (radSusp) radSusp.checked = true;
                } else {
                    // Estado padrão: checkbox marcado, campos ocultos
                    if (chkHonReu) chkHonReu.checked = true;
                    if (honReuCampos) honReuCampos.classList.add('hidden');
                }

                // ==========================================
                // PREENCHER COM DADOS DA PLANILHA (PRIORIDADE)
                // ==========================================
                if (window.hcalcState.planilhaExtracaoData) {
                    const dados = window.hcalcState.planilhaExtracaoData;

                    if (dados.idPlanilha && $('val-id')) $('val-id').value = dados.idPlanilha;
                    if (dados.verbas && $('val-credito')) $('val-credito').value = dados.verbas;

                    // FGTS: preencher valor + ajustar checkbox + marcar status depositado conforme extração
                    if ($('val-fgts') && $('calc-fgts')) {
                        const temFgts = dados.fgts && dados.fgts !== '0,00' && dados.fgts !== '0';

                        if (temFgts) {
                            $('val-fgts').value = dados.fgts;
                            $('calc-fgts').checked = true;

                            // Marcar radio button correto (depositado ou devido)
                            if (dados.fgtsDepositado) {
                                const radDepositado = document.querySelector('input[name="fgts-tipo"][value="depositado"]');
                                if (radDepositado) radDepositado.checked = true;
                            } else {
                                const radDevido = document.querySelector('input[name="fgts-tipo"][value="devido"]');
                                if (radDevido) radDevido.checked = true;
                            }
                        } else {
                            // Sem FGTS detectado → desmarcar checkbox (que vem marcado por padrão)
                            $('calc-fgts').checked = false;
                        }
                        $('calc-fgts').dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // INSS: preencher valores + ajustar checkbox se não há nenhum
                    if (dados.inssTotal && $('val-inss-total')) $('val-inss-total').value = dados.inssTotal;
                    if (dados.inssAutor && $('val-inss-rec')) $('val-inss-rec').value = dados.inssAutor;

                    // Verificar se não há INSS nenhum
                    const semInssTotal = !dados.inssTotal || dados.inssTotal === '0,00' || dados.inssTotal === '0';
                    const semInssAutor = !dados.inssAutor || dados.inssAutor === '0,00' || dados.inssAutor === '0';

                    if (semInssTotal && semInssAutor && $('ignorar-inss')) {
                        $('ignorar-inss').checked = true;
                        $('ignorar-inss').dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // Custas: valor e data da planilha (prevalece sobre sentença)
                    if (dados.custas && $('val-custas')) {
                        $('val-custas').value = dados.custas;
                        // Data das custas = data de liquidação da planilha
                        if (dados.dataAtualizacao && $('custas-data-origem')) {
                            $('custas-data-origem').value = dados.dataAtualizacao;
                        }
                    }

                    if (dados.dataAtualizacao && $('val-data')) $('val-data').value = dados.dataAtualizacao;
                    if (dados.honAutor && $('val-hon-autor')) $('val-hon-autor').value = dados.honAutor;

                    // Aplicar IRPF se tributável
                    if (dados.irpfIsento === false) {
                        const irpfTipoEl = document.getElementById('irpf-tipo');
                        if (irpfTipoEl && irpfTipoEl.options.length > 1) {
                            irpfTipoEl.value = irpfTipoEl.options[1].value; // primeiro != 'isento'
                            irpfTipoEl.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }

                    // Auto-selecionar origem como PJeCalc
                    if ($('calc-origem')) $('calc-origem').value = 'pjecalc';
                }

                // Mostrar card colapsado se planilha foi carregada (Fase 3)
                const resumoCard = $('resumo-extracao-card');
                if (resumoCard && window.hcalcState.planilhaExtracaoData) {
                    resumoCard.style.display = 'block';
                    // Preencher conteúdo do card
                    const dados = window.hcalcState.planilhaExtracaoData;
                    const resumoConteudo = $('resumo-conteudo');
                    if (resumoConteudo) {
                        resumoConteudo.innerHTML = `
                            <div class="resumo-item"><strong>ID:</strong> ${dados.idPlanilha || 'N/A'}</div>
                            <div class="resumo-item"><strong>Crédito:</strong> R$ ${dados.verbas || '0,00'}</div>
                            ${dados.fgts ? `<div class="resumo-item"><strong>FGTS:</strong> R$ ${dados.fgts}</div>` : ''}
                            <div class="resumo-item"><strong>INSS Total:</strong> R$ ${dados.inssTotal || '0,00'}</div>
                            <div class="resumo-item"><strong>INSS Rec:</strong> R$ ${dados.inssAutor || '0,00'}</div>
                            ${dados.custas ? `<div class="resumo-item"><strong>Custas:</strong> R$ ${dados.custas}</div>` : ''}
                            <div class="resumo-item"><strong>Data:</strong> ${dados.dataAtualizacao || 'N/A'}</div>
                            ${dados.periodoCalculo ? `<div class="resumo-item"><strong>Período:</strong> ${dados.periodoCalculo}</div>` : ''}
                            ${dados.irpfIsento === false ? `<div class="resumo-item" style="color:#b45309"><strong>IRPF:</strong> Tributável</div>` : ''}
                        `;
                    }
                }

                $('homologacao-overlay').style.display = 'flex';
                dbg('Overlay exibido para o usuario.');

                // Fallback: tentar clipboard se não tem ID da planilha
                if (!window.hcalcState.planilhaExtracaoData?.idPlanilha) {
                    try {
                        const txt = await navigator.clipboard.readText();
                        if (txt && txt.trim().length > 0) {
                            $('val-id').value = txt.trim();
                        }
                    } catch (e) { console.warn('Clipboard ignorado ou bloqueado', e); }
                }

                updateHighlight();
            } catch (e) {
                err('Erro no handler do botao Gerar Homologacao:', e);
                alert('Erro ao abrir assistente. Verifique o console (F12).');
                return;
            }
        };

        // ==========================================
        // FASE 2: Handler do Input File (Carregar Planilha)
        // ==========================================
        $('input-planilha-pdf').onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const btn = $('btn-abrir-homologacao');
            btn.textContent = '⏳ Processando...';
            btn.disabled = true;

            try {
                // Configurar PDF.js (primeira vez)
                const loaded = carregarPDFJSSeNecessario();
                if (!loaded) {
                    throw new Error('PDF.js não disponível');
                }

                // Processar planilha
                const dados = await processarPlanilhaPDF(file);

                if (dados.sucesso) {
                    // Salvar no state
                    window.hcalcState.planilhaExtracaoData = dados;
                    window.hcalcState.planilhaCarregada = true;

                    // Atualizar dropdowns de linhas extras com a planilha principal recém-carregada
                    atualizarDropdownsPlanilhas();

                    // Atualizar botão
                    btn.textContent = '✓ Dados Extraídos';
                    btn.style.background = '#10b981';
                    btn.disabled = false;

                    dbg('Planilha extraída:', dados);

                    // Feedback visual momentâneo
                    setTimeout(() => {
                        btn.textContent = 'Gerar Homologação';
                        btn.style.background = '#00509e';
                    }, 2000);
                } else {
                    throw new Error(dados.erro || 'Erro desconhecido');
                }
            } catch (error) {
                console.error('[HCalc] Erro ao processar PDF:', error.message);
                alert('Erro ao processar PDF: ' + error.message);
                btn.textContent = '📄 Carregar Planilha';
                btn.disabled = false;
            }
        };

        // Handler do botão Reload (recarregar planilha)
        $('btn-reload-planilha').onclick = () => {
            const inputFile = $('input-planilha-pdf');
            inputFile.click();
        };

        $('btn-fechar').onclick = (e) => {
            e.preventDefault();  // Previne scroll indesejado
            const modal = $('homologacao-modal');
            const overlay = $('homologacao-overlay');
            modal.style.opacity = '1';
            modal.style.pointerEvents = 'all';
            modal.dataset.ghost = 'false';
            overlay.style.display = 'none';
            overlay.style.pointerEvents = 'none';
            // LIMPAR REFERÊNCIAS DOM: v1.8 usa método centralizado
            window.hcalcState.resetPrep();
            console.log('[hcalc] Estado resetado via hcalcState.resetPrep()');
        };
        $('homologacao-overlay').onclick = (e) => {
            if (e.target.id === 'homologacao-overlay') {
                // Não fecha — torna transparente e "fantasma"
                const modal = $('homologacao-modal');
                const overlay = $('homologacao-overlay');
                const isGhost = modal.dataset.ghost === 'true';
                if (isGhost) {
                    // Segundo clique fora: volta ao normal
                    modal.style.opacity = '1';
                    modal.style.pointerEvents = 'all';
                    overlay.style.pointerEvents = 'none';
                    modal.dataset.ghost = 'false';
                } else {
                    // Primeiro clique fora: vira fantasma
                    modal.style.opacity = '0.25';
                    modal.style.transition = 'opacity 0.3s';
                    modal.style.pointerEvents = 'none';
                    // Mantém overlay transparente para detectar clique de retorno
                    overlay.style.pointerEvents = 'all';
                    modal.dataset.ghost = 'true';
                }
            }
        };

        $('calc-origem').onchange = (e) => { $('col-pjc').classList.toggle('hidden', e.target.value !== 'pjecalc'); };
        $('calc-autor').onchange = (e) => { $('col-esclarecimentos').classList.toggle('hidden', e.target.value !== 'perito'); };
        $('calc-esclarecimentos').onchange = (e) => { $('calc-peca-perito').classList.toggle('hidden', !e.target.checked); };

        $('calc-fgts').onchange = (e) => {
            const isChecked = e.target.checked;
            $('fgts-radios').classList.toggle('hidden', !isChecked);
            $('row-fgts-valor').classList.toggle('hidden', !isChecked);
            updateHighlight();
        };
        $('calc-indice').onchange = (e) => { $('col-juros-val').classList.toggle('hidden', e.target.value !== 'tr'); };
        $('ignorar-hon-autor').onchange = (e) => { $('val-hon-autor').classList.toggle('hidden', e.target.checked); updateHighlight(); };
        $('ignorar-inss').onchange = (e) => {
            $('val-inss-rec').classList.toggle('hidden', e.target.checked);
            $('val-inss-total').classList.toggle('hidden', e.target.checked);
            updateHighlight();
        };
        $('irpf-tipo').onchange = (e) => { $('irpf-campos').classList.toggle('hidden', e.target.value === 'isento'); };

        $('resp-tipo').onchange = (e) => {
            $('resp-sub-opcoes').classList.toggle('hidden', e.target.value !== 'subsidiarias');

            // Atualizar visibilidade de checkboxes "Depositado pela Principal" em todos os depósitos
            window.hcalcState.depositosRecursais.forEach(d => {
                if (!d.removed) {
                    atualizarVisibilidadeDepositoPrincipal(d.idx);
                }
            });
        };

        // Lógica para Períodos Diversos
        $('resp-diversos').onchange = (e) => {
            const fieldset = $('resp-diversos-fieldset');
            const container = $('resp-diversos-container');
            const selectPrincipal = $('resp-devedora-principal');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];

            if (e.target.checked) {
                fieldset.classList.remove('hidden');

                // Preencher dropdown de Devedora Principal
                selectPrincipal.innerHTML = '';
                reclamadas.forEach((rec, idx) => {
                    const opt = document.createElement('option');
                    opt.value = rec;
                    opt.textContent = rec;
                    if (idx === 0) opt.selected = true; // Primeira como padrão
                    selectPrincipal.appendChild(opt);
                });

                // Verifique se já existe um formulário, senão crie um
                if (container.children.length === 0) {
                    adicionarLinhaPeridoDiverso();
                }
            } else {
                fieldset.classList.add('hidden');
                container.innerHTML = '';
            }
        };

        // Atualizar listas quando principal mudar
        $('resp-devedora-principal').onchange = (e) => {
            // Atualizar todos os dropdowns de reclamadas (centralizado)
            atualizarDropdownsReclamadas();
        };

        $('btn-adicionar-periodo').onclick = (e) => {
            e.preventDefault();
            adicionarLinhaPeridoDiverso();
        };

        // ─── PLANILHAS EXTRAS: REGISTRO E SINCRONIZAÇÃO ───────────────────────────
        function registrarPlanilhaDisponivel(id, label, dados) {
            if (!window.hcalcState.planilhasDisponiveis) window.hcalcState.planilhasDisponiveis = [];
            // Substitui entrada com mesmo id (re-upload da mesma linha)
            window.hcalcState.planilhasDisponiveis =
                window.hcalcState.planilhasDisponiveis.filter(p => p.id !== id);
            window.hcalcState.planilhasDisponiveis.push({ id, label, dados });
            atualizarDropdownsPlanilhas();
        }

        function atualizarDropdownsPlanilhas() {
            const extras = window.hcalcState.planilhasDisponiveis || [];
            document.querySelectorAll('.periodo-planilha-select').forEach(sel => {
                const currentVal = sel.value;
                // Remove todas as opções extras (mantém apenas 'principal')
                Array.from(sel.options).filter(o => o.value !== 'principal').forEach(o => o.remove());
                // Re-adiciona as disponíveis
                extras.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = `📊 ${p.label}`;
                    sel.appendChild(opt);
                });
                // Restaura seleção anterior se ainda válida
                if (Array.from(sel.options).some(o => o.value === currentVal)) sel.value = currentVal;
            });
        }

        function atualizarDropdownsReclamadas() {
            const todasReclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const principalIntegral = $('resp-devedora-principal')?.value || '';

            // Coletar todas as reclamadas já selecionadas em linhas existentes
            const jaUsadas = new Set([principalIntegral]);
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                if (select.value) jaUsadas.add(select.value);
            });

            // Atualizar cada dropdown
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                const valorAtual = select.value;

                // Reconstruir opções excluindo as já usadas (exceto a própria seleção)
                select.innerHTML = '<option value="">Selecione a reclamada...</option>';
                todasReclamadas.forEach(rec => {
                    if (!jaUsadas.has(rec) || rec === valorAtual) {
                        const opt = document.createElement('option');
                        opt.value = rec;
                        opt.textContent = rec;
                        if (rec === valorAtual) opt.selected = true;
                        select.appendChild(opt);
                    }
                });
            });
        }

        function adicionarLinhaPeridoDiverso() {
            const container = $('resp-diversos-container');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const principalIntegral = $('resp-devedora-principal')?.value || '';
            const idx = container.children.length;
            const rowId = `periodo-diverso-${idx}`;
            const numeroDevedora = idx + 2; // #1 é a principal, então começa do #2

            const div = document.createElement('div');
            div.id = rowId;
            div.className = 'row';
            div.style.marginBottom = '15px';
            div.style.padding = '12px';
            div.style.backgroundColor = '#f5f5f5';
            div.style.borderRadius = '4px';

            // Filtrar: remover a principal integral E as já selecionadas em outras linhas
            const jaUsadas = new Set([principalIntegral]);
            document.querySelectorAll('.periodo-reclamada').forEach(select => {
                if (select.value) jaUsadas.add(select.value);
            });

            let selectOptions = '<option value="">Selecione a reclamada...</option>';
            reclamadas.forEach(rec => {
                if (!jaUsadas.has(rec)) {
                    selectOptions += `<option value="${rec}">${rec}</option>`;
                }
            });

            div.innerHTML = `
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Devedora #${numeroDevedora}</label>
                    <select class="periodo-reclamada" data-idx="${idx}" style="width: 100%; padding: 8px;">
                        ${selectOptions}
                    </select>
                </div>
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Tipo de Responsabilidade</label>
                    <div style="display: flex; gap: 15px;">
                        <label><input type="radio" name="periodo-tipo-${idx}" class="periodo-tipo" data-idx="${idx}" value="subsidiaria" checked> Subsidiária</label>
                        <label><input type="radio" name="periodo-tipo-${idx}" class="periodo-tipo" data-idx="${idx}" value="principal"> Principal (Período Parcial)</label>
                    </div>
                </div>
                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <label>Período (vazio = integral)</label>
                        <input type="text" class="periodo-periodo" data-idx="${idx}" placeholder="Deixe vazio para período integral" style="width: 100%; padding: 8px;">
                    </div>
                    <div style="flex: 1;">
                        <label>ID Cálculo Separado</label>
                        <input type="text" class="periodo-id" data-idx="${idx}" placeholder="ID #XXXX" style="width: 100%; padding: 8px;">
                    </div>
                </div>
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold; font-size: 12px;">Planilha desta Devedora</label>
                    <div style="display: flex; gap: 8px; align-items: center; margin-top: 4px;">
                        <select class="periodo-planilha-select" data-idx="${idx}"
                                style="flex: 1; padding: 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="principal">📋 Mesma planilha principal</option>
                        </select>
                        <button type="button" class="btn-carregar-planilha-extra btn-action"
                                data-idx="${idx}"
                                style="font-size: 11px; padding: 6px 10px; white-space: nowrap; background: #7c3aed;">
                            📄 Carregar Nova
                        </button>
                        <input type="file" class="input-planilha-extra-pdf" data-idx="${idx}"
                               accept=".pdf" style="display: none;">
                    </div>
                </div>
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
                    <label><input type="checkbox" class="periodo-total" data-idx="${idx}"> Período Total</label>
                    <button type="button" class="btn-remover-periodo btn-action" data-idx="${idx}" data-row-id="${rowId}" style="padding: 8px; margin-left: auto; background: #d32f2f;">Remover</button>
                </div>
            `;
            container.appendChild(div);

            // ─── BOTÃO REMOVER: atualizar dropdowns após remoção ──────────────────────
            const btnRemover = div.querySelector(`.btn-remover-periodo[data-idx="${idx}"]`);
            btnRemover.onclick = () => {
                document.getElementById(rowId).remove();
                atualizarDropdownsReclamadas(); // Liberar reclamada de volta
            };

            // ─── AUTO-PREENCHER CAMPOS com planilha principal (padrão) ────────────────
            const periodoInput = div.querySelector(`.periodo-periodo[data-idx="${idx}"]`);
            const idInput = div.querySelector(`.periodo-id[data-idx="${idx}"]`);

            if (window.hcalcState.planilhaExtracaoData) {
                const pd = window.hcalcState.planilhaExtracaoData;
                if (periodoInput && pd.periodoCalculo) periodoInput.value = pd.periodoCalculo;
                if (idInput && pd.idPlanilha) idInput.value = pd.idPlanilha;
            }

            // ─── SELECT RECLAMADA: atualizar dropdowns quando selecionada ─────────────
            const selectReclamada = div.querySelector(`.periodo-reclamada[data-idx="${idx}"]`);
            selectReclamada.onchange = () => {
                // Atualizar todos os dropdowns para refletir nova seleção
                atualizarDropdownsReclamadas();
            };

            // ─── SELECT: trocar planilha ──────────────────────────────────────────────
            const selectPlanilha = div.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`);

            // Injetar planilhas já disponíveis neste dropdown
            atualizarDropdownsPlanilhas();

            selectPlanilha.onchange = (e) => {
                const val = e.target.value;
                const pd = val === 'principal'
                    ? window.hcalcState.planilhaExtracaoData
                    : (window.hcalcState.planilhasDisponiveis || []).find(p => p.id === val)?.dados;
                if (!pd) return;
                if (pd.idPlanilha && idInput) idInput.value = pd.idPlanilha;
                if (pd.periodoCalculo && periodoInput) periodoInput.value = pd.periodoCalculo;
            };

            // ─── BOTÃO CARREGAR NOVA PLANILHA ─────────────────────────────────────────
            const btnCarregar = div.querySelector(`.btn-carregar-planilha-extra[data-idx="${idx}"]`);
            const inputExtra = div.querySelector(`.input-planilha-extra-pdf[data-idx="${idx}"]`);

            btnCarregar.onclick = () => inputExtra.click();

            inputExtra.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                inputExtra.value = '';  // reset — permite re-upload do mesmo arquivo

                const originalText = btnCarregar.textContent;
                btnCarregar.textContent = '⏳...';
                btnCarregar.disabled = true;

                try {
                    const loaded = carregarPDFJSSeNecessario();
                    if (!loaded) throw new Error('PDF.js não disponível');

                    const dados = await processarPlanilhaPDF(file);
                    if (!dados.sucesso) throw new Error(dados.erro || 'Erro desconhecido');

                    // Preencher campos da linha com dados extraídos
                    if (dados.idPlanilha && idInput) idInput.value = dados.idPlanilha;
                    if (dados.periodoCalculo && periodoInput) periodoInput.value = dados.periodoCalculo;

                    // Registrar como planilha disponível para as demais linhas
                    const extraId = `extra_${idx}`;
                    const extraLabel = `${dados.idPlanilha || 'Extra'} (Dev.${idx + 2})`;
                    registrarPlanilhaDisponivel(extraId, extraLabel, dados);

                    // Selecionar esta planilha no dropdown desta linha
                    selectPlanilha.value = extraId;

                    // Feedback visual
                    btnCarregar.textContent = '✓ Analisada';
                    btnCarregar.style.background = '#10b981';
                    btnCarregar.disabled = false;

                } catch (err) {
                    alert('Erro ao processar planilha: ' + err.message);
                    btnCarregar.textContent = originalText;
                    btnCarregar.disabled = false;
                }
            };
        }

        $('chk-hon-reu').onchange = (e) => {
            // Lógica invertida: marcado = "Não há" = esconde campos
            $('hon-reu-campos').classList.toggle('hidden', e.target.checked);
        };

        // Controlar exibição de campo percentual vs valor
        document.querySelectorAll('input[name="rad-hon-reu-tipo"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const isPercentual = e.target.value === 'percentual';
                $('hon-reu-perc-campo').classList.toggle('hidden', !isPercentual);
                $('hon-reu-valor-campo').classList.toggle('hidden', isPercentual);
            });
        });

        $('chk-perito-conh').onchange = (e) => { $('perito-conh-campos').classList.toggle('hidden', !e.target.checked); };

        // CORREÇÃO 4: Event listener simplificado - guard interno em preencherDepositosAutomaticos
        $('chk-deposito').onchange = (e) => {
            // Toggle visibilidade
            $('deposito-campos').classList.toggle('hidden', !e.target.checked);

            // Preencher automaticamente se marcado (safe: tem guard para jaTemCampos)
            if (e.target.checked) {
                preencherDepositosAutomaticos();
            }
        };

        $('chk-pag-antecipado').onchange = (e) => {
            $('pag-antecipado-campos').classList.toggle('hidden', !e.target.checked);
            if (e.target.checked && window.hcalcState.pagamentosAntecipados.length === 0) {
                adicionarPagamentoAntecipado(); // Adiciona primeiro pagamento automaticamente
            }
        };

        // Event listeners para radios de tipo de liberação
        document.querySelectorAll('input[name="lib-tipo"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const valor = e.target.value;
                $('lib-remanescente-campos').classList.toggle('hidden', valor !== 'remanescente');
                $('lib-devolucao-campos').classList.toggle('hidden', valor !== 'devolucao');
            });
        });

        document.getElementsByName('rad-intimacao').forEach((rad) => {
            rad.onchange = (e) => { $('intimacao-mandado-campos').classList.toggle('hidden', e.target.value === 'diario'); };
        });

        // ==========================================
        // ==========================================
        // FUNÇÕES DE GERENCIAMENTO DE MÚLTIPLOS DEPÓSITOS
        // ==========================================

        // Preenche depósitos automaticamente com recursos detectados (Depósito/Garantia)
        function preencherDepositosAutomaticos() {
            const prep = window.hcalcLastPrepResult;
            if (!prep || !prep.depositos || prep.depositos.length === 0) {
                console.log('[AUTO-DEPOSITOS] Sem dados de prep');
                return;
            }

            const container = $('depositos-container');
            if (!container) {
                console.error('[AUTO-DEPOSITOS] Container não encontrado!');
                return;
            }

            // Se já tem campos, não limpar (permite adicionar manualmente)
            const jaTemCampos = container.children.length > 0;
            if (jaTemCampos) {
                console.log('[AUTO-DEPOSITOS] Container já possui campos, pulando');
                return;
            }

            // Limpar depósitos existentes apenas se estiver vazio
            container.innerHTML = '';
            window.hcalcState.nextDepositoIdx = 0;
            window.hcalcState.depositosRecursais = [];

            console.log('[AUTO-DEPOSITOS] Iniciando preenchimento com', prep.depositos.length, 'recursos');

            // Preencher com TODOS os depósitos/garantias dos recursos detectados
            for (const deposito of prep.depositos) {
                // Filtrar anexos de tipo Depósito ou Garantia
                const anexosRelevantes = (deposito.anexos || []).filter(ax =>
                    ax.tipo === 'Depósito' || ax.tipo === 'Garantia'
                );

                // CORREÇÃO 3: Fallback para recursos sem anexos expandidos
                if (anexosRelevantes.length > 0) {
                    for (const anexo of anexosRelevantes) {
                        adicionarDepositoRecursal();
                        const idx = window.hcalcState.nextDepositoIdx - 1;

                        const tipoSelect = $(`dep-tipo-${idx}`);
                        const depositanteSelect = $(`dep-depositante-${idx}`);
                        const idInput = $(`dep-id-${idx}`);

                        if (tipoSelect) {
                            tipoSelect.value = anexo.tipo === 'Depósito' ? 'bb' : 'garantia';
                            tipoSelect.dispatchEvent(new Event('change', { bubbles: true }));
                        }

                        if (depositanteSelect) {
                            depositanteSelect.value = deposito.depositante;
                        }

                        if (idInput) {
                            idInput.value = anexo.id || '';
                        }
                    }
                    console.log('[AUTO-DEPOSITOS]', anexosRelevantes.length, 'depósito(s) de', deposito.depositante);
                } else {
                    // FALLBACK: Recurso detectado mas sem anexos expandidos
                    console.warn('[AUTO-DEPOSITOS] Recurso sem anexos para', deposito.depositante, '— criando linha sem ID');
                    adicionarDepositoRecursal();
                    const idx = window.hcalcState.nextDepositoIdx - 1;
                    const depositanteSelect = $(`dep-depositante-${idx}`);
                    if (depositanteSelect) {
                        depositanteSelect.value = deposito.depositante || '';
                    }
                }
            }
        }

        function adicionarDepositoRecursal() {
            const idx = window.hcalcState.nextDepositoIdx++;
            const container = $('depositos-container');

            // Buscar TODAS as reclamadas do processo (não só as com recursos)
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];

            const depositoDiv = document.createElement('div');
            depositoDiv.id = `deposito-item-${idx}`;
            depositoDiv.className = 'deposito-item';
            depositoDiv.style.cssText = 'border: 1px solid #ddd; padding: 8px; margin-bottom: 8px; border-radius: 4px; background: #f9f9f9;';

            // Construir opções do select de depositante com TODAS as reclamadas do processo
            let optionsHtml = '<option value="">-- Selecione Reclamada --</option>';
            for (const nome of reclamadas) {
                optionsHtml += `<option value="${nome}">${nome}</option>`;
            }

            depositoDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="font-size: 11px; color: #666;">Depósito Recursal #${idx + 1}</strong>
                    <button type="button" id="btn-remover-dep-${idx}" style="padding: 2px 8px; font-size: 10px; color: #dc2626; background: #fee; border: 1px solid #fca; border-radius: 3px; cursor: pointer;">✕ Remover</button>
                </div>
                <div class="row">
                    <select id="dep-tipo-${idx}" data-dep-idx="${idx}">
                        <option value="bb" selected>Banco do Brasil</option>
                        <option value="sif">CEF (SIF)</option>
                        <option value="garantia">Seguro Garantia</option>
                    </select>
                    <select id="dep-depositante-${idx}" data-dep-idx="${idx}">
                        ${optionsHtml}
                    </select>
                    <input type="text" id="dep-id-${idx}" placeholder="ID da Guia" data-dep-idx="${idx}">
                </div>
                <div class="row" id="dep-principal-row-${idx}">
                    <label><input type="checkbox" id="dep-principal-${idx}" checked data-dep-idx="${idx}"> Depositado pela Devedora Principal?</label>
                </div>
                <div class="row hidden" id="dep-solidaria-info-${idx}" style="font-size: 11px; color: #059669; font-style: italic;">
                    ✓ Devedoras solidárias: qualquer depósito pode ser liberado
                </div>
                <div class="row" id="dep-liberacao-row-${idx}">
                    <label><input type="radio" name="rad-dep-lib-${idx}" value="reclamante" checked data-dep-idx="${idx}"> Liberação simples (Reclamante)</label>
                    <label style="margin-left: 10px;"><input type="radio" name="rad-dep-lib-${idx}" value="detalhada" data-dep-idx="${idx}"> Liberação detalhada (Crédito, INSS, Hon.)</label>
                </div>
            `;

            container.appendChild(depositoDiv);

            // Event listeners para este depósito específico
            const tipoEl = $(`dep-tipo-${idx}`);
            const principalEl = $(`dep-principal-${idx}`);
            const liberacaoRow = $(`dep-liberacao-row-${idx}`);

            tipoEl.onchange = (e) => {
                liberacaoRow.classList.toggle('hidden', e.target.value === 'garantia');
            };

            principalEl.onchange = (e) => {
                liberacaoRow.classList.toggle('hidden', !e.target.checked);
            };

            // Atualizar visibilidade inicial baseado em tipo de responsabilidade
            atualizarVisibilidadeDepositoPrincipal(idx);

            // Event listener para botão remover (evita problema sandbox TamperMonkey)
            const btnRemoverDep = depositoDiv.querySelector(`#btn-remover-dep-${idx}`);
            if (btnRemoverDep) {
                btnRemoverDep.addEventListener('click', () => {
                    depositoDiv.remove();
                    const dep = window.hcalcState.depositosRecursais.find(d => d.idx === idx);
                    if (dep) dep.removed = true;
                });
            }

            // Armazenar referência no estado
            window.hcalcState.depositosRecursais.push({ idx, removed: false });
        }

        function atualizarVisibilidadeDepositoPrincipal(idx) {
            const tipoResp = $('resp-tipo')?.value || 'unica';
            const isSolidaria = tipoResp === 'solidarias';

            const principalRow = $(`dep-principal-row-${idx}`);
            const solidariaInfo = $(`dep-solidaria-info-${idx}`);
            const principalChk = $(`dep-principal-${idx}`);

            if (principalRow && solidariaInfo) {
                if (isSolidaria) {
                    // Ocultar checkbox, mostrar info, forçar checked
                    principalRow.classList.add('hidden');
                    solidariaInfo.classList.remove('hidden');
                    if (principalChk) principalChk.checked = true;
                } else {
                    // Mostrar checkbox, ocultar info
                    principalRow.classList.remove('hidden');
                    solidariaInfo.classList.add('hidden');
                }
            }
        }

        function adicionarPagamentoAntecipado() {
            const idx = window.hcalcState.nextPagamentoIdx++;
            const container = $('pagamentos-container');

            const pagamentoDiv = document.createElement('div');
            pagamentoDiv.id = `pagamento-item-${idx}`;
            pagamentoDiv.className = 'pagamento-item';
            pagamentoDiv.style.cssText = 'border: 1px solid #ddd; padding: 8px; margin-bottom: 8px; border-radius: 4px; background: #f9f9f9;';

            pagamentoDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="font-size: 11px; color: #666;">Pagamento Antecipado #${idx + 1}</strong>
                    <button type="button" id="btn-remover-pag-${idx}" style="padding: 2px 8px; font-size: 10px; color: #dc2626; background: #fee; border: 1px solid #fca; border-radius: 3px; cursor: pointer;">✕ Remover</button>
                </div>
                <div class="row">
                    <input type="text" id="pag-id-${idx}" placeholder="ID do Depósito" data-pag-idx="${idx}">
                </div>
                <div class="row">
                    <label><input type="radio" name="lib-tipo-${idx}" value="nenhum" checked data-pag-idx="${idx}"> Padrão (extinção)</label>
                    <label style="margin-left: 15px;"><input type="radio" name="lib-tipo-${idx}" value="remanescente" data-pag-idx="${idx}"> Com Remanescente</label>
                    <label style="margin-left: 15px;"><input type="radio" name="lib-tipo-${idx}" value="devolucao" data-pag-idx="${idx}"> Com Devolução</label>
                </div>
                <div id="lib-remanescente-campos-${idx}" class="hidden">
                    <div class="row">
                        <input type="text" id="lib-rem-valor-${idx}" placeholder="Valor Remanescente (ex: 1.234,56)" data-pag-idx="${idx}">
                        <input type="text" id="lib-rem-titulo-${idx}" placeholder="Título (ex: custas processuais)" data-pag-idx="${idx}">
                    </div>
                </div>
                <div id="lib-devolucao-campos-${idx}" class="hidden">
                    <div class="row">
                        <input type="text" id="lib-dev-valor-${idx}" placeholder="Valor Devolução (ex: 1.234,56)" data-pag-idx="${idx}">
                    </div>
                </div>
            `;

            container.appendChild(pagamentoDiv);

            // Event listeners para os radios deste pagamento
            document.querySelectorAll(`input[name="lib-tipo-${idx}"]`).forEach(radio => {
                radio.addEventListener('change', (e) => {
                    const valor = e.target.value;
                    $(`lib-remanescente-campos-${idx}`).classList.toggle('hidden', valor !== 'remanescente');
                    $(`lib-devolucao-campos-${idx}`).classList.toggle('hidden', valor !== 'devolucao');
                });
            });

            // Event listener para botão remover (evita problema sandbox TamperMonkey)
            const btnRemoverPag = pagamentoDiv.querySelector(`#btn-remover-pag-${idx}`);
            if (btnRemoverPag) {
                btnRemoverPag.addEventListener('click', () => {
                    pagamentoDiv.remove();
                    const pag = window.hcalcState.pagamentosAntecipados.find(p => p.idx === idx);
                    if (pag) pag.removed = true;
                });
            }

            // Armazenar referência no estado
            window.hcalcState.pagamentosAntecipados.push({ idx, removed: false });
        }

        // Bind dos botões de adicionar
        $('btn-add-deposito').onclick = adicionarDepositoRecursal;
        $('btn-add-pagamento').onclick = adicionarPagamentoAntecipado;

        // Máscara de data DD/MM/YYYY para campos de data
        const aplicarMascaraData = (input) => {
            input.addEventListener('input', (e) => {
                let valor = e.target.value.replace(/\D/g, ''); // Remove não-dígitos
                if (valor.length >= 2) {
                    valor = valor.slice(0, 2) + '/' + valor.slice(2);
                }
                if (valor.length >= 5) {
                    valor = valor.slice(0, 5) + '/' + valor.slice(5);
                }
                e.target.value = valor.slice(0, 10); // Limita a DD/MM/YYYY
            });
        };

        // Aplicar máscara aos campos de data
        ['val-data', 'custas-data-origem', 'val-perito-data'].forEach(id => {
            const campo = $(id);
            if (campo) aplicarMascaraData(campo);
        });

        // Toggle origem custas: Sentença vs Acórdão
        $('custas-origem').onchange = (e) => {
            const isAcordao = e.target.value === 'acordao';
            $('custas-data-col').classList.toggle('hidden', isAcordao);
            $('custas-acordao-col').classList.toggle('hidden', !isAcordao);
        };

        const ordemCopiaLabels = {
            'val-id': '1) Id da Planilha',
            'val-data': '1) Data da Atualização',
            'val-credito': '1) Crédito Principal',
            'val-fgts': '1) FGTS Separado',
            'val-inss-rec': '2) INSS - Desconto Reclamante',
            'val-inss-total': '2) INSS - Total Empresa',
            'val-hon-autor': '3) Honorários do Autor',
            'val-custas': '4) Custas'
        };

        window.hcalcPeritosDetectados = [];
        window.hcalcPeritosConhecimentoDetectados = [];

        function isNomeRogerio(nome) {
            return /rogerio|rogério/i.test(nome || '');
        }

        function aplicarRegrasPeritosDetectados(peritosDetectados) {
            const nomes = Array.isArray(peritosDetectados) ? peritosDetectados.filter(Boolean) : [];
            const temRogerio = nomes.some((nome) => isNomeRogerio(nome));
            const peritosConhecimento = nomes.filter((nome) => !isNomeRogerio(nome));

            window.hcalcPeritosDetectados = nomes;
            window.hcalcPeritosConhecimentoDetectados = peritosConhecimento;

            const origemEl = $('calc-origem');
            const pjcEl = $('calc-pjc');
            const autorEl = $('calc-autor');
            const colEsclarecimentosEl = $('col-esclarecimentos');
            const rowPeritoContabilEl = $('row-perito-contabil');
            const chkPeritoConhEl = $('chk-perito-conh');
            const peritoConhCamposEl = $('perito-conh-campos');
            const valPeritoNomeEl = $('val-perito-nome');
            const valPeritoContabilValorEl = $('val-perito-contabil-valor');

            if (temRogerio) {
                origemEl.value = 'pjecalc';
                origemEl.disabled = true;
                pjcEl.checked = true;
                pjcEl.disabled = true;
                autorEl.value = 'perito';
                autorEl.disabled = true;
                colEsclarecimentosEl.classList.remove('hidden');
                rowPeritoContabilEl.classList.remove('hidden');
            } else {
                origemEl.disabled = false;
                pjcEl.disabled = false;
                autorEl.disabled = false;
                rowPeritoContabilEl.classList.add('hidden');
                if (valPeritoContabilValorEl) {
                    valPeritoContabilValorEl.value = '';
                }
            }

            // Controlar visibilidade do fieldset de perícia conhecimento
            const fieldsetPericiaConh = $('fieldset-pericia-conh');
            if (peritosConhecimento.length > 0) {
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.remove('hidden');
                chkPeritoConhEl.checked = true;
                peritoConhCamposEl.classList.remove('hidden');
                valPeritoNomeEl.value = peritosConhecimento.join(' | ');
            } else {
                // Esconder card de perícia se não há perito de conhecimento
                if (fieldsetPericiaConh) fieldsetPericiaConh.classList.add('hidden');
            }
        }

        function atualizarStatusProximoCampo(nextInputId = null) {
            // Função simplificada - status removido da interface
            // Mantida para compatibilidade com código existente
        }

        // Timeline functions moved to prep.js
        // readTimelineBasic / extractDataFromTimelineItem / getTimelineItems
        // now handled by window.executarPrep()

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
                divRow.style.cssText = "display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; padding: 6px; background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px;";

                // Checkbox para marcar como principal (primeira é marcada por padrão)
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
        }

        async function refreshDetectedPartes() {
            const partes = await derivePartesData();

            // Armazenar globalmente para uso em geração de textos
            window.hcalcPartesData = partes;

            const reclamadas = (partes?.passivo || []).map(p => p.nome).filter(Boolean);
            const peritos = ordenarComRogerioPrimeiro(extractPeritos(partes));
            const advogadosMap = extractAdvogadosPorReclamada(partes);
            const statusAdvMap = extractStatusAdvogadoPorReclamada(partes);
            const advogadosAutor = extractAdvogadosDoAutor(partes);

            window.hcalcStatusAdvogados = statusAdvMap;
            window.hcalcAdvogadosAutor = advogadosAutor; // Cache global para validação de honorários
            window.hcalcPeritosDetectados = peritos; // Cache global para validação de honorários

            // Log para debug
            console.log('hcalc: advogados por reclamada', advogadosMap);
            console.log('hcalc: status advogado por reclamada', statusAdvMap);
            console.log(`[hcalc] Detecção atualizada: ${reclamadas.length} reclamada(s), ${peritos.length} perito(s)`);

            aplicarRegrasPeritosDetectados(peritos);

            // Log de debug
            console.log(`[hcalc] Detecção atualizada: ${reclamadas.length} reclamada(s), ${peritos.length} perito(s)`);

            // LÓGICA DE RESPONSABILIDADE DINÂMICA
            const respFieldset = document.querySelector('fieldset #resp-tipo')?.closest('fieldset');
            if (reclamadas.length <= 1 && respFieldset) {
                respFieldset.classList.add('hidden');
            } else if (reclamadas.length > 1 && respFieldset) {
                respFieldset.classList.remove('hidden');
            }

            // AUTO-PREENCHER DEPOSITANTE COM RECLAMADA EXTRAIDA
            const depDepositante = $('dep-depositante');
            if (depDepositante && reclamadas.length > 0) {
                if (reclamadas.length === 1) {
                    // Só 1 reclamada: preencher e travar
                    depDepositante.value = reclamadas[0];
                    depDepositante.disabled = true;
                } else {
                    // 2+ reclamadas: transformar em dropdown
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

            // CONSTRUIR SEÇÃO DE INTIMAÇÕES
            construirSecaoIntimacoes();
        }

        function getProcessIdFromUrl() {
            const match = window.location.href.match(/\/processo\/(\d+)/);
            return match ? match[1] : null;
        }

        function shapePartesPayload(dados) {
            const buildRecord = (parte, tipo, idx, total) => {
                let nome = parte.nome.trim();
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

            const ativo = (dados?.ATIVO || []).map((parte, idx) => buildRecord(parte, 'AUTOR', idx, dados.ATIVO.length));
            const passivo = (dados?.PASSIVO || []).map((parte, idx) => buildRecord(parte, 'RÉU', idx, dados.PASSIVO.length));
            const outros = (dados?.TERCEIROS || []).map((parte, idx) => buildRecord(parte, parte.tipo || 'TERCEIRO', idx, dados.TERCEIROS.length));

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
                // Armazenar no cache
                const PROCESS_CACHE = window.calcPartesCache || {};
                PROCESS_CACHE[idProcesso] = partes;
                window.calcPartesCache = PROCESS_CACHE;

                // LIMITAR CACHE: Manter apenas últimas 5 entradas para prevenir crescimento ilimitado
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
            // Inicializar cache se não existir
            if (!window.calcPartesCache) {
                window.calcPartesCache = {};
            }
            const cache = window.calcPartesCache;
            const processId = getProcessIdFromUrl();

            // 1. Tentar cache primeiro
            if (processId && cache[processId]) {
                console.log('hcalc: usando dados do cache', cache[processId]);
                return cache[processId];
            }

            // 2. Tentar buscar via API
            if (processId) {
                const apiData = await fetchPartesViaApi();
                if (apiData) {
                    return apiData;
                }
            }

            // 3. Fallback: buscar qualquer cache disponível
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

            // 4. Último recurso: parsear DOM
            console.warn('hcalc: usando parseamento do DOM (pode ser impreciso)');
            return parsePartesFromDom();
        }

        function parsePartesFromDom() {
            const rows = document.querySelectorAll('div[class*="bloco-participante"] tbody tr');
            const data = { ativo: [], passivo: [], outros: [] };
            rows.forEach((row) => {
                const text = row.innerText || '';
                const value = text.split('\n').map((l) => l.trim()).find(Boolean) || text.trim();
                if (!value) { return; }
                if (/reclamante|exequente|autor/i.test(text)) {
                    data.ativo.push({ nome: value });
                } else if (/reclamado|réu|executado/i.test(text)) {
                    data.passivo.push({ nome: value });
                } else {
                    data.outros.push({ nome: value, tipo: 'OUTRO' });
                }
            });
            return data;
        }

        function extractPeritos(partes) {
            const outros = partes?.outros || [];
            // Filtrar por tipo 'PERITO' ou qualquer variação no nome/tipo
            return outros.filter((part) => {
                const tipo = (part.tipo || '').toUpperCase();
                const nome = (part.nome || '').toUpperCase();
                return tipo.includes('PERITO') || nome.includes('PERITO');
            }).map((part) => part.nome);
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

        // ==========================================
        // FUNÇÕES DE EXTRAÇÃO DE REPRESENTANTES
        // ==========================================
        window.hcalcPartesData = null; // Cache global de partes para uso em geração de textos

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

        function verificarSeNomeEAdvogadoAutor(nomeParaVerificar, advogadosAutor) {
            if (!nomeParaVerificar || !advogadosAutor || advogadosAutor.length === 0) {
                return false;
            }
            const nomeNorm = normalizarNomeParaComparacao(nomeParaVerificar);
            return advogadosAutor.some(adv => {
                const match = adv.nomeNormalizado === nomeNorm ||
                    nomeNorm.includes(adv.nomeNormalizado) ||
                    adv.nomeNormalizado.includes(nomeNorm);
                if (match) {
                    console.log(`hcalc: match encontrado - "${nomeParaVerificar}" = advogado autor "${adv.nome}"`);
                }
                return match;
            });
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

        function temAdvogado(nomeReclamada, advogadosMap) {
            if (!advogadosMap || !nomeReclamada) { return false; }
            const reps = advogadosMap[nomeReclamada] || [];
            return reps.length > 0;
        }

        function obterReclamadasSemAdvogado(partes, advogadosMap) {
            if (!partes?.passivo) { return []; }
            return partes.passivo.filter(rec => !temAdvogado(rec.nome, advogadosMap)).map(rec => rec.nome);
        }

        function obterReclamadasComAdvogado(partes, advogadosMap) {
            if (!partes?.passivo) { return []; }
            return partes.passivo.filter(rec => temAdvogado(rec.nome, advogadosMap)).map(rec => rec.nome);
        }

        // OTIMIZAÇÃO: adiar refresh até browser estar ocioso (não compete com carregamento)
        if (typeof requestIdleCallback === 'function') {
            requestIdleCallback(() => refreshDetectedPartes(), { timeout: 3000 });
        } else {
            setTimeout(refreshDetectedPartes, 1500); // fallback para browsers sem rIC
        }

        // ==========================================
        // 4. LÓGICA DE NAVEGAÇÃO "COLETA INTELIGENTE"
        // ==========================================
        var orderSequence = [
            'val-id', 'val-data', 'val-credito', 'val-fgts',
            'val-inss-rec', 'val-inss-total', 'val-hon-autor', 'val-custas'
        ];

        function updateHighlight(currentId = null) {
            orderSequence.forEach((id) => $(id).classList.remove('highlight'));
            const visibleInputs = orderSequence.filter((id) => !$(id).classList.contains('hidden'));
            if (visibleInputs.length === 0) return;
            let nextIndex = 0;
            if (currentId) {
                const currentIndex = visibleInputs.indexOf(currentId);
                if (currentIndex !== -1 && currentIndex < visibleInputs.length - 1) {
                    nextIndex = currentIndex + 1;
                } else if (currentIndex === visibleInputs.length - 1) {
                    return;
                }
            }
            const nextInputId = visibleInputs[nextIndex];
            $(nextInputId).classList.add('highlight');
            $(nextInputId).focus();
            atualizarStatusProximoCampo(nextInputId);
        }

        orderSequence.forEach((id) => {
            const el = $(id);
            el.addEventListener('paste', () => {
                setTimeout(() => {
                    el.value = el.value.trim();
                    updateHighlight(id);
                }, 10);
            });
            el.addEventListener('focus', () => {
                orderSequence.forEach((i) => $(i).classList.remove('highlight'));
                el.classList.add('highlight');
            });
        });

        // ==========================================
        // 5. FUNÇÕES AUXILIARES DE CÁLCULO E TEXTO
        function parseMoney(str) {
            if (!str) return 0;
            str = str.replace(/[R$\s]/g, '').replace(/\./g, '').replace(',', '.');
            const num = parseFloat(str);
            return isNaN(num) ? 0 : num;
        }

        function formatMoney(num) {
            return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }).replace(/\s/g, '');
        }

        function normalizeMoneyInput(val) {
            if (!val || val === '[VALOR]') return val;
            const parsed = parseMoney(val);
            if (parsed === 0 && !/^\s*0/.test(val)) return val;
            return formatMoney(parsed);
        }

        function bold(text) { return `<strong>${text}</strong>`; }
        function u(text) { return `<u>${text}</u>`; }

        // ==========================================
        // 6. GERADOR DE DECISÃO HTML (O CORE)
        // ==========================================
        $('btn-gravar').onclick = () => {
            dbg('Clique em Gravar Decisao detectado.');
            let text = `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Vistos.</p>`;
            let houveDepositoDireto = false;
            let houveLibecaoDetalhada = false;
            const passivoTotal = (window.hcalcPartesData?.passivo || []).length;

            const autoria = $('calc-autor').options[$('calc-autor').selectedIndex].text;
            const idPlanilha = $('val-id').value || '[ID DA PLANILHA]';
            const valData = $('val-data').value || '[DATA]';
            const valCredito = $('val-credito').value || '[VALOR]';
            const valFgts = $('val-fgts').value || '[VALOR FGTS]';
            const isPerito = $('calc-autor').value === 'perito';
            const peritoEsclareceu = $('calc-esclarecimentos').checked;
            const pecaPerito = $('calc-peca-perito').value || '[ID PEÇA]';
            const indice = $('calc-indice').value;
            const isFgtsSep = $('calc-fgts').checked;
            const ignorarInss = $('ignorar-inss').checked;

            const xxx = () => u(bold('XXX'));

            const appendBaseAteAntesPericiais = ({
                idCalculo,
                usarPlaceholder = false,
                reclamadaLabel = ''
            }) => {
                let introTxt = '';
                const vCredito = usarPlaceholder ? 'R$XXX' : `R$${valCredito}`;
                const vFgts = usarPlaceholder ? 'R$XXX' : `R$${valFgts}`;
                const vData = usarPlaceholder ? 'XXX' : valData;

                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugnações apresentadas já foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os cálculos do expert (#${bold(idCalculo)}), `;
                } else {
                    introTxt += `Tendo em vista a concordância das partes, HOMOLOGO os cálculos apresentados pelo(a) ${u(autoria)} (#${bold(idCalculo)}), `;
                }

                // Verificar se FGTS foi depositado (para evitar contradição)
                const fgtsTipo = isFgtsSep ? (document.querySelector('input[name="fgts-tipo"]:checked')?.value || 'devido') : 'devido';
                const fgtsJaDepositado = fgtsTipo === 'depositado';

                if (isFgtsSep && !fgtsJaDepositado) {
                    // FGTS devido (a ser recolhido)
                    introTxt += `fixando o crédito do autor em ${bold(vCredito)} relativo ao principal, e ${bold(vFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(vData)}. `;
                } else if (isFgtsSep && fgtsJaDepositado) {
                    // FGTS depositado (não menciona "a ser recolhido")
                    introTxt += `fixando o crédito do autor em ${bold(vCredito)}, atualizado para ${bold(vData)}. `;
                } else {
                    // Sem FGTS separado
                    introTxt += `fixando o crédito em ${bold(vCredito)}, referente ao valor principal, atualizado para ${bold(vData)}. `;
                }

                if (indice === 'adc58') {
                    if (isFgtsSep) {
                        introTxt += `A atualização foi feita na forma da Lei 14.905/2024 e da decisão da SDI-1 do C. TST (IPCA-E até a distribuição; taxa Selic até 29/08/2024, e IPCA + juros de mora a partir de 30/08/2024).`;
                    } else {
                        introTxt += `A correção monetária foi realizada pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento, pela taxa SELIC (ADC 58).`;
                    }
                } else {
                    const valJuros = usarPlaceholder ? 'XXX' : ($('val-juros').value || '[JUROS]');
                    const dtIngresso = usarPlaceholder ? 'XXX' : ($('data-ingresso').value || '[DATA INGRESSO]');
                    introTxt += `Atualizáveis pela TR/IPCA-E, conforme sentença. Juros legais de ${bold('R$' + valJuros)} a partir de ${bold(dtIngresso)}.`;
                }

                if (reclamadaLabel) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${reclamadaLabel}</strong></p>`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;

                // 2º parágrafo: FGTS depositado (com valor)
                if (isFgtsSep && fgtsJaDepositado) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><u>O FGTS devido, ${bold(vFgts)}, já foi depositado, portanto deduzido.</u></p>`;
                }

                if (!usarPlaceholder && $('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a ausência do arquivo de origem, <u>deverá a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }

                if (usarPlaceholder) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${xxx()}, para ${xxx()}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada, ainda, deverá pagar o valor de sua cota-parte no INSS, a saber, ${xxx()}, para ${xxx()}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${xxx()} para ${xxx()}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${xxx()}, para ${xxx()}.</p>`;
                    if ($('chk-hon-reu').checked) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                    } else {
                        const rdHonReu = document.querySelector('input[name="rad-hon-reu"]:checked').value;
                        if (rdHonReu === 'suspensiva') {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${xxx()}.</p>`;
                        }
                    }
                    return;
                }

                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do crédito, não há contribuições previdenciárias devidas.</p>`;
                } else {
                    const valInssRecStr = $('val-inss-rec').value || '0';
                    const valInssTotalStr = $('val-inss-total').value || '0';
                    const valInssRec = parseMoney(valInssRecStr);
                    const valInssTotal = parseMoney(valInssTotalStr);
                    let valInssReclamadaStr = valInssTotalStr;
                    if ($('calc-origem').value === 'pjecalc') {
                        const recResult = valInssTotal - valInssRec;
                        valInssReclamadaStr = formatMoney(recResult);
                    }
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada deverá pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}.</p>`;
                }

                if ($('irpf-tipo').value === 'isento') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não há deduções fiscais cabíveis.</p>`;
                } else {
                    const vBase = $('val-irpf-base').value || '[VALOR]';
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tributáveis (${bold('R$' + vBase)}), pelo período de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }

                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }

                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                } else {
                    const tipoHonReu = document.querySelector('input[name="rad-hon-reu-tipo"]:checked').value;
                    const temSuspensiva = $('chk-hon-reu-suspensiva').checked;

                    if (tipoHonReu === 'percentual') {
                        const p = $('val-hon-reu-perc').value;
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, na ordem de ${bold(p)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}, a serem descontados do crédito do autor.</p>`;
                        }
                    } else {
                        const vHonR = normalizeMoneyInput($('val-hon-reu').value || '[VALOR]');
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, no importe de ${bold(vHonR)}, para ${bold(valData)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada, no importe de ${bold(vHonR)}, para ${bold(valData)}, a serem descontados do crédito do autor.</p>`;
                        }
                    }
                }
            };

            // Função unificada para liberação detalhada (depósito recursal ou pagamento antecipado)
            const gerarLiberacaoDetalhada = (contexto) => {
                const { prefixo = '', depositoInfo = '' } = contexto;

                // Linha inicial com referência à planilha
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Passo à liberação de valores conforme planilha #${bold(idPlanilha)}:</p>`;

                let numLiberacao = 1;

                // 1) Crédito do reclamante
                if (depositoInfo) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante ${depositoInfo}, no valor de ${bold('R$' + valCredito)}, expedindo-se alvará eletrônico.</p>`;
                } else {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao reclamante seu crédito, no valor de ${bold('R$' + valCredito)}, expedindo-se alvará eletrônico.</p>`;
                }
                numLiberacao++;

                // 2) INSS (se não ignorado)
                if (!ignorarInss) {
                    const valInssRec = normalizeMoneyInput($('val-inss-rec').value || '0,00');
                    const valInssTotal = normalizeMoneyInput($('val-inss-total').value || '0,00');

                    // Calcular INSS patronal
                    const isPjeCalc = $('calc-pjc').checked;
                    let inssEmpregado = valInssRec; // parte empregado - sempre valor do reclamante
                    let inssPatronal = valInssTotal; // parte patronal/reclamada

                    // Se é PJC: patronal = total - empregado
                    if (isPjeCalc && valInssTotal && valInssRec) {
                        const totalNum = parseMoney(valInssTotal);
                        const recNum = parseMoney(valInssRec);
                        const patronalNum = totalNum - recNum;
                        inssPatronal = formatMoney(patronalNum);
                    }
                    // Se não é PJC: usa direto o valInssTotal

                    const totalInss = valInssTotal;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Proceda a Secretaria à transferência de valores ao órgão competente, via Siscondj, sendo: ${bold('R$ ' + inssEmpregado)} referente às contribuições previdenciárias parte empregado e ${bold('R$ ' + inssPatronal)} no que concernem às contribuições patronais (total de ${bold('R$ ' + totalInss)}).</p>`;
                    numLiberacao++;
                }

                // 3) Honorários periciais (se houver)
                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';

                // Perito contábil (Rogério) - se houver
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(peritoContabilDetectado)} seus honorários, no valor de ${bold('R$' + vContabil)}.</p>`;
                    numLiberacao++;
                }

                // Peritos de conhecimento - se houver
                const peritosConhecimentoDetectados = window.hcalcPeritosConhecimentoDetectados || [];
                const nomesInputConhecimento = ($('val-perito-nome').value || '')
                    .split(/\||,|;|\n/g)
                    .map((n) => n.trim())
                    .filter(Boolean);
                const nomesConhecimento = peritosConhecimentoDetectados.length
                    ? peritosConhecimentoDetectados
                    : nomesInputConhecimento;

                const valorPeritoConh = $('val-perito-valor')?.value || '';
                const tipoPagPericia = $('perito-tipo-pag')?.value || 'reclamada';

                if ($('chk-perito-conh').checked && nomesConhecimento.length > 0 && valorPeritoConh) {
                    nomesConhecimento.forEach((nomePerito) => {
                        if (tipoPagPericia !== 'trt') {
                            const vP = normalizeMoneyInput(valorPeritoConh);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao perito ${bold(nomePerito)} seus honorários, no valor de ${bold('R$' + vP)}.</p>`;
                            numLiberacao++;
                        }
                    });
                }

                // 4) Honorários do advogado do autor (se não ignorado)
                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${numLiberacao}) Libere-se ao patrono da parte autora seus honorários, no valor de ${bold('R$' + vHonA)}.</p>`;
                    numLiberacao++;
                }

                // Retornar o número da próxima liberação (para devolução)
                return numLiberacao;
            };

            const appendDisposicoesFinais = () => {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>Disposições finais:</strong></p>`;

                // CONTÁBIL PRIMEIRO (Rogério)
                const peritoContabilDetectado = (window.hcalcPeritosDetectados || []).find((nome) => isNomeRogerio(nome));
                const valorPeritoContabil = $('val-perito-contabil-valor')?.value || '';
                if (peritoContabilDetectado && valorPeritoContabil) {
                    const vContabil = normalizeMoneyInput(valorPeritoContabil);
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários contábeis em favor de ${bold(peritoContabilDetectado)}, ora arbitrados em ${bold(vContabil)}.</p>`;
                }

                // CONHECIMENTO DEPOIS
                const peritosConhecimentoDetectados = window.hcalcPeritosConhecimentoDetectados || [];
                const nomesInputConhecimento = ($('val-perito-nome').value || '')
                    .split(/\||,|;|\n/g)
                    .map((n) => n.trim())
                    .filter(Boolean);
                const nomesConhecimento = peritosConhecimentoDetectados.length
                    ? peritosConhecimentoDetectados
                    : nomesInputConhecimento;

                if ($('chk-perito-conh').checked && nomesConhecimento.length > 0) {
                    const vP = $('val-perito-valor').value || '[VALOR/ID]';
                    const dtP = $('val-perito-data').value || $('val-data').value || '[DATA]';
                    const tipoPagPericia = $('perito-tipo-pag').value;

                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários periciais da fase de conhecimento assim estabelecidos:</p>`;

                    nomesConhecimento.forEach((nomePerito) => {
                        if (tipoPagPericia === 'trt') {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagos pelo TRT, considerando a sucumbência do autor no objeto da perícia (#${bold(vP)}).</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- Em favor de ${bold(nomePerito)}, pagamento de ${bold('R$' + vP)} pela reclamada, para ${bold(dtP)}.</p>`;
                        }
                    });
                }

                if ($('custas-status').value === 'pagas') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas pagas em razão de recurso.</p>`;
                } else {
                    const valC = $('val-custas').value || '[VALOR]';
                    const origemCustas = $('custas-origem').value;

                    if (valC && valC !== '0,00' && valC !== '0') {
                        if (origemCustas === 'acordao') {
                            // Custas por acórdão (inclui ID do acórdão no texto)
                            const acordaoIdx = $('custas-acordao-select').value;
                            const acordaoSel = $('custas-acordao-select').selectedOptions[0];
                            const dataAcordao = acordaoSel?.dataset?.data || '[DATA ACÓRDÃO]';
                            const idAcordao = acordaoSel?.dataset?.id || '';
                            const idTexto = idAcordao ? ` #${bold(idAcordao)}` : '';
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas definidas em acórdão${idTexto}, pela reclamada, no valor de ${bold('R$' + valC)} para ${bold(dataAcordao)}.</p>`;
                        } else {
                            // Custas por sentença (padrão)
                            const dataCustas = $('custas-data-origem').value || valData;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Custas de ${bold('R$' + valC)} pela reclamada, para ${bold(dataCustas)}.</p>`;
                        }
                    }
                }

                // ==========================================
                // DEPÓSITOS RECURSAIS (múltiplos)
                // ==========================================
                if ($('chk-deposito').checked) {
                    const passivoDetectado = (window.hcalcPartesData?.passivo || []).map((p) => p?.nome).filter(Boolean);
                    const primeiraReclamada = passivoDetectado[0] || '';
                    const tipoRespAtual = $('resp-tipo')?.value || 'unica';

                    // Coletar todos os depósitos válidos (não removidos)
                    const depositosValidos = window.hcalcState.depositosRecursais
                        .filter(d => !d.removed)
                        .map(d => {
                            const idx = d.idx;
                            const tDep = $(`dep-tipo-${idx}`)?.value || 'bb';
                            const dNome = $(`dep-depositante-${idx}`)?.value || '[RECLAMADA]';
                            const dId = $(`dep-id-${idx}`)?.value || '[ID]';
                            let isPrin = $(`dep-principal-${idx}`)?.checked ?? true;
                            const liberacao = document.querySelector(`input[name="rad-dep-lib-${idx}"]:checked`)?.value || 'reclamante';

                            const isDepositoJudicial = tDep !== 'garantia';
                            let criterioLiberacaoDeposito = 'manual';
                            let depositanteResolvida = dNome;

                            // Auto-resolver depositante baseado em partes detectadas
                            if (passivoDetectado.length === 1) {
                                depositanteResolvida = passivoDetectado[0];
                                isPrin = true;
                                criterioLiberacaoDeposito = 'reclamada-unica';
                            } else if (tipoRespAtual === 'subsidiarias' && primeiraReclamada && isPrin) {
                                depositanteResolvida = primeiraReclamada;
                                criterioLiberacaoDeposito = 'subsidiaria-principal';
                            } else if (tipoRespAtual === 'solidarias') {
                                // Solidárias: qualquer depósito pode ser liberado
                                depositanteResolvida = depositanteResolvida || primeiraReclamada || '[RECLAMADA]';
                                isPrin = true; // Forçar como principal (todas são principais em solidária)
                                criterioLiberacaoDeposito = 'solidaria';
                            }

                            const deveLiberarDeposito = isDepositoJudicial && (
                                criterioLiberacaoDeposito === 'reclamada-unica' ||
                                criterioLiberacaoDeposito === 'subsidiaria-principal' ||
                                criterioLiberacaoDeposito === 'solidaria' ||
                                (criterioLiberacaoDeposito === 'manual' && isPrin)
                            );

                            const naturezaDevedora = criterioLiberacaoDeposito === 'solidaria'
                                ? 'solidária'
                                : (isPrin ? 'principal' : 'subsidiária');

                            const bancoTxt = tDep === 'bb' ? 'Banco do Brasil' : (tDep === 'sif' ? 'Caixa Econômica Federal (SIF)' : 'seguro garantia regular');

                            return {
                                idx, tDep, depositanteResolvida, dId, isPrin, liberacao,
                                isDepositoJudicial, naturezaDevedora, bancoTxt, deveLiberarDeposito
                            };
                        });

                    if (depositosValidos.length === 0) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Há depósito recursal. (Configure os dados)</p>`;
                    } else {
                        // Agrupar depósitos por depositante + tipo
                        const grupos = {};
                        depositosValidos.forEach(dep => {
                            const chave = `${dep.depositanteResolvida}|${dep.naturezaDevedora}|${dep.bancoTxt}`;
                            if (!grupos[chave]) {
                                grupos[chave] = {
                                    depositante: dep.depositanteResolvida,
                                    natureza: dep.naturezaDevedora,
                                    banco: dep.bancoTxt,
                                    depositos: [],
                                    todosGarantia: true,
                                    todosLiberacaoDireta: true
                                };
                            }
                            grupos[chave].depositos.push(dep);
                            if (dep.isDepositoJudicial) grupos[chave].todosGarantia = false;
                            if (dep.liberacao !== 'reclamante') grupos[chave].todosLiberacaoDireta = false;
                        });

                        const formatarLista = (itens) => {
                            if (!itens || itens.length === 0) { return ''; }
                            if (itens.length === 1) { return itens[0]; }
                            if (itens.length === 2) { return `${itens[0]} e ${itens[1]}`; }
                            return `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
                        };

                        // Gerar texto para cada grupo
                        Object.values(grupos).forEach(grupo => {
                            const ids = grupo.depositos.map(d => `${bold(d.dId)}`);
                            const idsTexto = ids.length > 1 ? `(Ids ${formatarLista(ids)})` : `(Id ${ids[0]})`;

                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Há depósito${grupo.depositos.length > 1 ? 's' : ''} recursal${grupo.depositos.length > 1 ? 'is' : ''} da devedora ${grupo.natureza} (${grupo.depositante} ${idsTexto}) via ${grupo.banco}.</p>`;

                            if (grupo.todosGarantia) {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Tratando-se de seguro garantia, não há liberação imediata de valores nesta oportunidade.</p>`;
                            } else {
                                // Processar liberações
                                const depsLiberaveis = grupo.depositos.filter(d => d.deveLiberarDeposito && d.isDepositoJudicial);

                                if (depsLiberaveis.length > 0) {
                                    const depsDiretos = depsLiberaveis.filter(d => d.liberacao === 'reclamante');
                                    const depsDetalhados = depsLiberaveis.filter(d => d.liberacao === 'detalhada');

                                    if (depsDiretos.length > 0) {
                                        houveDepositoDireto = true;
                                        const txtPlural = depsDiretos.length > 1 ? 'os depósitos recursais' : 'o depósito recursal';
                                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Libere-se ${txtPlural} em favor do reclamante. Após, apure-se o remanescente devido.</p>`;
                                    }

                                    if (depsDetalhados.length > 0) {
                                        const idsDetalhados = depsDetalhados.map(d => `${grupo.depositante} #${bold(d.dId)}`);
                                        const listaDeps = formatarLista(idsDetalhados);

                                        houveLibecaoDetalhada = true;
                                        gerarLiberacaoDetalhada({
                                            depositoInfo: `o${depsDetalhados.length > 1 ? 's' : ''} depósito${depsDetalhados.length > 1 ? 's' : ''} recursal${depsDetalhados.length > 1 ? 'is' : ''} (${listaDeps} via ${grupo.banco})`
                                        });
                                    }
                                } else {
                                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Por ora, não há liberação automática do${grupo.depositos.length > 1 ? 's' : ''} depósito${grupo.depositos.length > 1 ? 's' : ''} recursal${grupo.depositos.length > 1 ? 'is' : ''} informado${grupo.depositos.length > 1 ? 's' : ''}.</p>`;
                                }
                            }
                        });
                    }
                }

                // ==========================================
                // PAGAMENTOS ANTECIPADOS (múltiplos)
                // ==========================================
                const isPagamentoAntecipado = $('chk-pag-antecipado').checked;
                if (isPagamentoAntecipado) {
                    const pagamentosValidos = window.hcalcState.pagamentosAntecipados
                        .filter(p => !p.removed)
                        .map(p => {
                            const idx = p.idx;
                            return {
                                idx,
                                id: $(`pag-id-${idx}`)?.value || '[ID]',
                                tipoLib: document.querySelector(`input[name="lib-tipo-${idx}"]:checked`)?.value || 'nenhum',
                                remValor: $(`lib-rem-valor-${idx}`)?.value || '',
                                remTitulo: $(`lib-rem-titulo-${idx}`)?.value || '',
                                devValor: $(`lib-dev-valor-${idx}`)?.value || ''
                            };
                        });

                    if (pagamentosValidos.length === 0) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado depósito pela reclamada. (Configure os dados)</p>`;
                    } else {
                        pagamentosValidos.forEach(pag => {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado depósito pela reclamada, #${bold(pag.id)}.</p>`;

                            houveLibecaoDetalhada = true;
                            let proximoNum = gerarLiberacaoDetalhada({});

                            if (pag.tipoLib === 'devolucao') {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${proximoNum}) Devolva-se à reclamada o valor pago a maior, no montante de ${bold('R$ ' + (pag.devValor || '[VALOR]'))}, expedindo-se o competente alvará.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestação das partes.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após, tornem conclusos para extinção da execução.</p>`;
                            } else if (pag.tipoLib === 'remanescente') {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sem prejuízo, fica a reclamada intimada a pagar o valor remanescente de ${bold('R$ ' + (pag.remValor || '[VALOR]'))} devidos a título de ${bold(pag.remTitulo || '[TÍTULO]')}, em 15 dias, sob pena de execução.</p>`;
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Cientes as partes.</p>`;
                            } else {
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestações. Silentes, cumpra-se e, após, tornem conclusos para extinção da execução.</p>`;
                            }
                        });
                    }
                }

                // INTIMAÇÕES (apenas se NÃO houver pagamento antecipado)
                if (!isPagamentoAntecipado) {
                    const formatarListaPartes = (nomes) => {
                        if (!nomes || nomes.length === 0) { return ''; }
                        if (nomes.length === 1) { return nomes[0]; }
                        if (nomes.length === 2) { return `${nomes[0]} e ${nomes[1]}`; }
                        return `${nomes.slice(0, -1).join(', ')} e ${nomes[nomes.length - 1]}`;
                    };

                    const elsOpcoes = document.querySelectorAll('.sel-modo-intimacao');
                    const grpDiario = [];
                    const grpMandado = [];
                    const grpEdital = [];

                    // Verificar se é responsabilidade subsidiária
                    const isSubsidiaria = $('resp-tipo')?.value === 'subsidiarias';

                    // Obter lista de principais (marcadas como principal)
                    const principaisSet = new Set();
                    if (isSubsidiaria) {
                        document.querySelectorAll('.chk-parte-principal:checked').forEach(chk => {
                            principaisSet.add(chk.getAttribute('data-nome'));
                        });
                    }

                    if (elsOpcoes.length > 0) {
                        elsOpcoes.forEach((sel) => {
                            const nome = sel.getAttribute('data-nome');
                            const v = sel.value;

                            // FILTRO: Se subsidiária, intima apenas principais
                            if (isSubsidiaria && !principaisSet.has(nome)) {
                                return; // Pula subsidiárias
                            }

                            if (v === 'diario') grpDiario.push(nome);
                            else if (v === 'mandado') grpMandado.push(nome);
                            else if (v === 'edital') grpEdital.push(nome);
                        });
                    } else {
                        const valManual = $('sel-intimacao-manual')?.value || 'diario';
                        const nomeManual = $('int-nome-parte-manual')?.value || '[RECLAMADA]';
                        if (valManual === 'diario') grpDiario.push(nomeManual);
                        else if (valManual === 'mandado') grpMandado.push(nomeManual);
                        else if (valManual === 'edital') grpEdital.push(nomeManual);
                    }

                    if (grpDiario.length > 0) {
                        const alvoComAdv = formatarListaPartes(grpDiario);
                        const verboComAdv = grpDiario.length > 1 ? 'Intimem-se as reclamadas' : 'Intime-se a reclamada';
                        const patronoTxt = grpDiario.length > 1 ? 'seus patronos' : 'seu patrono';
                        const tipoValores = houveDepositoDireto ? 'valores remanescentes' : 'valores acima indicados';

                        if (houveDepositoDireto) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após referida atualização, ${verboComAdv} ${bold(alvoComAdv)}, na pessoa de ${patronoTxt}, para que pague(m) os ${tipoValores} em 15 dias, na forma do art. 523, caput, do CPC, sob pena de penhora.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboComAdv} ${bold(alvoComAdv)}, na pessoa de ${patronoTxt}, para que pague(m) os ${tipoValores} em 15 dias, na forma do art. 523, caput, do CPC, sob pena de penhora.</p>`;
                        }
                    }

                    if (grpMandado.length > 0) {
                        const alvoMand = formatarListaPartes(grpMandado);
                        const verboMand = grpMandado.length > 1 ? 'Intimem-se as reclamadas' : 'Intime-se a reclamada';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboMand} ${bold(alvoMand)} para pagamento dos valores acima em 48 (quarenta e oito) horas, sob pena de penhora, expedindo-se o competente ${bold("mandado")}.</p>`;
                    }

                    if (grpEdital.length > 0) {
                        const alvoEdit = formatarListaPartes(grpEdital);
                        const verboEdit = grpEdital.length > 1 ? 'Citem-se as reclamadas' : 'Cite-se a reclamada';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${verboEdit} ${bold(alvoEdit)}, por ${bold("edital")}, para pagamento dos valores acima em 48 (quarenta e oito) horas, sob pena de penhora.</p>`;
                    }
                }
            };

            // ==========================================
            // GERAÇÃO DE TEXTO - RESPONSABILIDADES
            // ==========================================
            function gerarTextoResponsabilidades() {
                const formatarLista = (nomes) => {
                    if (nomes.length === 0) return '';
                    if (nomes.length === 1) return bold(nomes[0]);
                    if (nomes.length === 2) return `${bold(nomes[0])} e ${bold(nomes[1])}`;
                    const ultimos = nomes.slice(-2);
                    const anteriores = nomes.slice(0, -2);
                    return `${anteriores.map(n => bold(n)).join(', ')}, ${bold(ultimos[0])} e ${bold(ultimos[1])}`;
                };

                const linhasPeriodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]'));
                if (linhasPeriodos.length === 0) return null;

                const principalSelecionada = $('resp-devedora-principal')?.value || '1';
                const periodoCompleto = window.hcalcState.planilhaExtracaoData?.periodoCalculo || '';
                const principaisParciais = [];
                const subsidiariasComPeriodo = [];

                linhasPeriodos.forEach((linha) => {
                    const idx = linha.id.replace('periodo-diverso-', '');
                    const nomeRec = document.querySelector(`.periodo-reclamada[data-idx="${idx}"]`)?.value || '';
                    const periodoTexto = document.querySelector(`.periodo-periodo[data-idx="${idx}"]`)?.value || '';
                    const idPlanilha = document.querySelector(`.periodo-id[data-idx="${idx}"]`)?.value || '';
                    const tipoRadio = document.querySelector(`input[name="periodo-tipo-${idx}"]:checked`)?.value || 'principal';

                    // NOVO: detectar se usa mesma planilha da principal
                    const planilhaSel = document.querySelector(`.periodo-planilha-select[data-idx="${idx}"]`)?.value || 'principal';
                    const usarMesmaPlanilha = planilhaSel === 'principal';

                    // Período vazio ou igual ao período completo = integral
                    const isPeriodoIntegral = !periodoTexto || periodoTexto === periodoCompleto;

                    if (nomeRec && !isPeriodoIntegral) {
                        if (tipoRadio === 'principal') {
                            principaisParciais.push({ nome: nomeRec, periodo: periodoTexto, idPlanilha: idPlanilha || '', usarMesmaPlanilha });
                        } else {
                            subsidiariasComPeriodo.push({ nome: nomeRec, periodo: periodoTexto, idPlanilha: idPlanilha || '', usarMesmaPlanilha });
                        }
                    }
                });

                // Identificar subsidiárias integrais (reclamadas que NÃO são principais e NÃO estão em períodos)
                const principaisNomes = new Set([principalSelecionada, ...principaisParciais.map(p => p.nome)]);
                const subsidiariasComPeriodoNomes = new Set(subsidiariasComPeriodo.map(s => s.nome));
                const todasReclamadas = Array.from(document.querySelectorAll('.chk-parte-principal'))
                    .map(chk => chk.getAttribute('data-nome'))
                    .filter(n => n);

                const subsidiariasIntegrais = todasReclamadas.filter(nome =>
                    !principaisNomes.has(nome) && !subsidiariasComPeriodoNomes.has(nome)
                );

                let textoIntro = '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sobre a responsabilidade pelo crédito, tem-se o seguinte:</p>';
                textoIntro += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>1 - Devedoras Principais:</strong></p>';
                textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${bold(principalSelecionada)} é devedora principal pelo período integral do contrato.</p>`;

                principaisParciais.forEach(prin => {
                    textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${bold(prin.nome)} também é principal, mas pelo período parcial de ${prin.periodo}.</p>`;
                });

                const todasSubsidiarias = [...subsidiariasIntegrais, ...subsidiariasComPeriodo];
                if (todasSubsidiarias.length > 0) {
                    textoIntro += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>2 - Devedoras Subsidiárias:</strong></p>';

                    // Subsidiárias integrais (agrupadas)
                    if (subsidiariasIntegrais.length > 0) {
                        const listaFormatada = formatarLista(subsidiariasIntegrais);
                        const verbo = subsidiariasIntegrais.length === 1 ? 'é responsável subsidiária' : 'são responsáveis subsidiárias';
                        textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${listaFormatada} ${verbo} pelo período integral do contrato.</p>`;
                    }

                    // Subsidiárias com período específico (individuais)
                    subsidiariasComPeriodo.forEach(sub => {
                        textoIntro += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">- ${bold(sub.nome)} é responsável subsidiária pelo período de ${sub.periodo}.</p>`;
                    });
                }

                textoIntro += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após isso, passo às homologações específicas:</p>';

                return {
                    textoIntro,
                    principalIntegral: principalSelecionada,
                    principaisParciais,
                    subsidiarias: todasSubsidiarias,
                    subsidiariasIntegrais,
                    subsidiariasComPeriodo,
                    todasPrincipais: [
                        { nome: principalSelecionada, periodo: 'integral', idPlanilha: '' },
                        ...principaisParciais
                    ]
                };
            }

            const linhasPeriodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]'));
            const usarDuplicacao = $('resp-diversos').checked && linhasPeriodos.length > 0;

            if (usarDuplicacao && passivoTotal > 1) {
                const dadosResp = gerarTextoResponsabilidades();

                if (dadosResp) {
                    const { textoIntro, todasPrincipais, subsidiariasIntegrais, subsidiariasComPeriodo } = dadosResp;
                    const principalIntegral = todasPrincipais[0];

                    text += textoIntro;

                    text += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>1 - Devedoras Principais:</strong></p>';

                    todasPrincipais.forEach((prin, i) => {
                        const letra = String.fromCharCode(97 + i);
                        const labelPrin = prin.periodo === 'integral'
                            ? `${bold(prin.nome)} (Período Integral)`
                            : `${bold(prin.nome)} (${prin.periodo})`;

                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${letra}) Reclamada ${labelPrin}:</strong></p>`;

                        const idParaUsar = prin.periodo === 'integral'
                            ? idPlanilha
                            : (prin.usarMesmaPlanilha || !prin.idPlanilha ? idPlanilha : prin.idPlanilha);

                        // placeholder=false se usa mesma planilha (valores já estão no form principal)
                        // placeholder=true  se tem período parcial mas sem planilha própria nem principal
                        const usarPlaceholder = prin.periodo !== 'integral' && !prin.usarMesmaPlanilha && !prin.idPlanilha;

                        appendBaseAteAntesPericiais({
                            idCalculo: idParaUsar,
                            usarPlaceholder: usarPlaceholder,
                            reclamadaLabel: ''
                        });
                    });

                    const totalSubsidiarias = subsidiariasIntegrais.length + subsidiariasComPeriodo.length;
                    if (totalSubsidiarias > 0) {
                        text += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>2 - Devedoras Subsidiárias:</strong></p>';
                        text += '<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">(Respondem apenas em caso de insuficiência patrimonial das principais)</p>';

                        let letraIdx = 0;

                        // Subsidiárias integrais (agrupadas)
                        subsidiariasIntegrais.forEach((nomeSub) => {
                            const letra = String.fromCharCode(97 + letraIdx);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${letra}) Reclamada ${bold(nomeSub)}:</p>`;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><em>Subsidiária pelo período integral do contrato, com os mesmos valores definidos para a devedora principal <strong>${principalIntegral.nome}</strong>, conforme planilha <strong>${idPlanilha}</strong>.</em></p>`;
                            letraIdx++;
                        });

                        // Subsidiárias com período específico
                        subsidiariasComPeriodo.forEach((sub) => {
                            const letra = String.fromCharCode(97 + letraIdx);
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${letra}) Reclamada ${bold(sub.nome)}</strong></p>`;

                            if (sub.usarMesmaPlanilha) {
                                // ── CASO 1: mesma planilha da principal → texto simplificado ──
                                const nomePrincipal = principalIntegral;
                                const idPrincipalUsar = idPlanilha; // val-id.value — planilha principal
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">
                                    <em>Subsidiária pelo período de <strong>${sub.periodo}</strong>.
                                    Os valores são os mesmos definidos para a devedora principal
                                    <strong>${nomePrincipal}</strong>, conforme planilha <strong>${idPrincipalUsar}</strong>,
                                    não sendo necessária homologação em separado.</em></p>`;
                            } else {
                                // ── CASO 2: planilha própria carregada ou sem planilha ──
                                const idSubPlanilha = sub.idPlanilha || idPlanilha;
                                const comPlaceholder = !sub.idPlanilha; // sem planilha própria = placeholder
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">
                                    <em>Subsidiária pelo período de <strong>${sub.periodo}</strong>.</em></p>`;
                                appendBaseAteAntesPericiais({
                                    idCalculo: idSubPlanilha,
                                    usarPlaceholder: comPlaceholder,
                                    reclamadaLabel: sub.nome
                                });
                            }
                            letraIdx++;
                        });
                    }
                }

                appendDisposicoesFinais();
            } else {
                let introTxt = '';
                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugnações apresentadas já foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os cálculos do expert (#${bold(idPlanilha)}), `;
                } else {
                    introTxt += `Tendo em vista a concordância das partes, HOMOLOGO os cálculos apresentados pelo(a) ${u(autoria)} (#${bold(idPlanilha)}), `;
                }

                // Verificar se FGTS foi depositado (para evitar contradição)
                const fgtsTipo = isFgtsSep ? (document.querySelector('input[name="fgts-tipo"]:checked')?.value || 'devido') : 'devido';
                const fgtsJaDepositado = fgtsTipo === 'depositado';

                if (isFgtsSep && !fgtsJaDepositado) {
                    // FGTS devido (a ser recolhido)
                    introTxt += `fixando o crédito do autor em ${bold('R$' + valCredito)} relativo ao principal, e ${bold('R$' + valFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(valData)}. `;
                } else if (isFgtsSep && fgtsJaDepositado) {
                    // FGTS depositado (não menciona "a ser recolhido")
                    introTxt += `fixando o crédito do autor em ${bold('R$' + valCredito)}, atualizado para ${bold(valData)}. `;
                } else {
                    introTxt += `fixando o crédito em ${bold('R$' + valCredito)}, referente ao valor principal, atualizado para ${bold(valData)}. `;
                }
                if (indice === 'adc58') {
                    if (isFgtsSep) {
                        introTxt += `A atualização foi feita na forma da Lei 14.905/2024 e da decisão da SDI-1 do C. TST (IPCA-E até a distribuição; taxa Selic até 29/08/2024, e IPCA + juros de mora a partir de 30/08/2024).`;
                    } else {
                        introTxt += `A correção monetária foi realizada pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento, pela taxa SELIC (ADC 58).`;
                    }
                } else {
                    const valJuros = $('val-juros').value || '[JUROS]';
                    const dtIngresso = $('data-ingresso').value || '[DATA INGRESSO]';
                    introTxt += `Atualizáveis pela TR/IPCA-E, conforme sentença. Juros legais de ${bold('R$' + valJuros)} a partir de ${bold(dtIngresso)}.`;
                }
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${introTxt}</p>`;

                // 2º parágrafo: FGTS depositado (com valor)
                if (isFgtsSep && fgtsJaDepositado) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><u>O FGTS devido, ${bold('R$' + valFgts)}, já foi depositado, portanto deduzido.</u></p>`;
                }

                if (passivoTotal > 1) {
                    if ($('resp-tipo').value === 'solidarias') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Declaro que as reclamadas respondem de forma solidária pela presente execução.</p>`;
                    } else if ($('resp-tipo').value === 'subsidiarias') {
                        if ($('resp-integral').checked) {
                            // Obter lista de principais e subsidiárias
                            const principais = [];
                            const subsidiarias = [];

                            document.querySelectorAll('.chk-parte-principal').forEach(chk => {
                                const nome = chk.getAttribute('data-nome');
                                if (chk.checked) {
                                    principais.push(nome);
                                } else {
                                    subsidiarias.push(nome);
                                }
                            });

                            // Texto específico nomeando principais e subsidiárias
                            if (principais.length > 0 && subsidiarias.length > 0) {
                                const formatarLista = (nomes) => {
                                    if (nomes.length === 1) return bold(nomes[0]);
                                    if (nomes.length === 2) return `${bold(nomes[0])} e ${bold(nomes[1])}`;
                                    return nomes.slice(0, -1).map(n => bold(n)).join(', ') + ' e ' + bold(nomes[nomes.length - 1]);
                                };

                                const txtPrincipais = formatarLista(principais);
                                const txtSubsidiarias = formatarLista(subsidiarias);
                                const verboPrin = principais.length > 1 ? 'são devedoras principais' : 'é devedora principal';
                                const verboSub = subsidiarias.length > 1 ? 'são subsidiárias' : 'é subsidiária';

                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${txtPrincipais} ${verboPrin}, ${txtSubsidiarias} ${verboSub} pelo período integral do contrato, portanto, os valores neste momento são devidos apenas pelas principais.</p>`;
                            } else {
                                // Fallback se não houver checkboxes marcados
                                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A primeira reclamada é devedora principal, as demais são subsidiárias pelo período integral do contrato, portanto, os valores neste momento são devidos apenas pela primeira.</p>`;
                            }
                        }
                    }
                }
                if ($('calc-origem').value === 'pjecalc' && !$('calc-pjc').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Considerando a ausência do arquivo de origem, <u>deverá a parte apresentar novamente a planilha ora homologada, acompanhada obrigatoriamente do respectivo arquivo ${bold('.PJC')} no prazo de 05 dias</u>.</p>`;
                }
                if (ignorarInss) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Pela natureza do crédito, não há contribuições previdenciárias devidas.</p>`;
                } else {
                    const valInssRecStr = $('val-inss-rec').value || '0';
                    const valInssTotalStr = $('val-inss-total').value || '0';
                    const valInssRec = parseMoney(valInssRecStr);
                    const valInssTotal = parseMoney(valInssTotalStr);
                    let valInssReclamadaStr = valInssTotalStr;
                    if ($('calc-origem').value === 'pjecalc') {
                        const recResult = valInssTotal - valInssRec;
                        valInssReclamadaStr = formatMoney(recResult);
                    }
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A reclamada deverá pagar o valor de sua cota-parte no INSS, a saber, ${bold(valInssReclamadaStr)}, para ${bold(valData)}.</p>`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Desde já, ficam autorizados os descontos previdenciários (cota do reclamante) ora fixados em ${bold('R$' + valInssRecStr)}, para ${bold(valData)}.</p>`;
                }
                if ($('irpf-tipo').value === 'isento') {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não há deduções fiscais cabíveis.</p>`;
                } else {
                    const vBase = $('val-irpf-base').value || '[VALOR]';
                    if ($('calc-origem').value === 'pjecalc') {
                        const vMes = $('val-irpf-meses').value || '[X]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Ficam autorizados os descontos fiscais, calculados sobre as verbas tributáveis (${bold('R$' + vBase)}), pelo período de ${bold(vMes + ' meses')}.</p>`;
                    } else {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Para as deduções fiscais de Imposto de Renda, fixadas em ${bold('R$' + vBase)} para ${bold(valData)}, observem-se a Súmula 368 do TST e IN RFB 1500/2014.</p>`;
                    }
                }
                if (!$('ignorar-hon-autor').checked) {
                    const vHonA = normalizeMoneyInput($('val-hon-autor').value || '[VALOR]');
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais pela reclamada, no importe de ${bold(vHonA)}, para ${bold(valData)}.</p>`;
                }
                if ($('chk-hon-reu').checked) {
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Não foram arbitrados honorários ao advogado do réu.</p>`;
                } else {
                    const tipoHonReu = document.querySelector('input[name="rad-hon-reu-tipo"]:checked').value;
                    const temSuspensiva = $('chk-hon-reu-suspensiva').checked;

                    if (tipoHonReu === 'percentual') {
                        const p = $('val-hon-reu-perc').value;
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, na ordem de ${bold(p)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}, a serem descontados do crédito do autor.</p>`;
                        }
                    } else {
                        const vHonR = normalizeMoneyInput($('val-hon-reu').value || '[VALOR]');
                        if (temSuspensiva) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, no importe de ${bold(vHonR)}, para ${bold(valData)}, diante da gratuidade deferida.</p>`;
                        } else {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada, no importe de ${bold(vHonR)}, para ${bold(valData)}, a serem descontados do crédito do autor.</p>`;
                        }
                    }
                }
                appendDisposicoesFinais();
            }

            // Linha final - OMITIR se houver liberação detalhada (depósito recursal ou pagamento antecipado)
            if (!houveLibecaoDetalhada) {
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${u('Ficam as partes cientes de que qualquer questionamento acerca desta decisão, salvo erro material, será apreciado após a garantia do juízo.')}</p>`;
            }
            const blob = new Blob([text], { type: 'text/html' });
            const clipboardItem = new window.ClipboardItem({ 'text/html': blob });
            navigator.clipboard.write([clipboardItem]).then(() => {
                alert('Decisão copiada com sucesso! Vá ao editor do PJe e cole (Ctrl+V).');
                $('homologacao-overlay').style.display = 'none';
                dbg('Decisao copiada para area de transferencia com sucesso.');
            }).catch((err) => {
                alert('Erro ao copiar. O navegador pode ter bloqueado.');
                console.error(err);
                err('Falha ao copiar decisao para clipboard:', err);
            });
        };

        dbg('initializeOverlay finalizado com sucesso.');
    }

    if (document.readyState === 'loading') {
        dbg('Documento em loading, aguardando DOMContentLoaded para iniciar overlay.');
        document.addEventListener('DOMContentLoaded', () => {
            try {
                initializeOverlay();
            } catch (e) {
                err('Erro ao iniciar overlay no DOMContentLoaded:', e);
            }
        }, { once: true });
    } else {
        dbg('Documento ja pronto, iniciando overlay imediatamente.');
        try {
            initializeOverlay();
        } catch (e) {
            err('Erro ao iniciar overlay imediatamente:', e);
        }
    }
})();