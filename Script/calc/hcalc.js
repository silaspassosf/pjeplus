// ==UserScript==
// @name         Homologação de Cálculos
// @namespace    http://tampermonkey.net/
// @version      1.10.6
// @description  Pagamento antecipado substitui intimações, adiciona texto de manifestação
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
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
    let lastUrl = location.href;
    new MutationObserver(() => {
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
    }).observe(document, { subtree: true, childList: true });

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
        const tipoDiv = container.querySelector('div[name="tipoItemTimeline"]');
        return tipoDiv?.getAttribute('aria-label')?.trim() || '';
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
                resultado.recursosPassivo.push({ ...base, tipoRec, depositante });
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
                depositante: r.depositante || ''
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
    <button id="btn-abrir-homologacao">Gerar Homologação</button>
    <div id="homologacao-overlay">
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
                        <div class="col hidden" id="col-fgts-val" style="flex: 0 0 140px;">
                            <label>FGTS Separado</label>
                            <input type="text" id="val-fgts" class="coleta-input" placeholder="R$ FGTS">
                        </div>
                    </div>
                    <div class="row">
                        <div class="col">
                            <label><input type="checkbox" id="calc-fgts"> FGTS apurado separado?</label>
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
                    <div class="row" style="margin-bottom: 0;">
                        <div class="col" style="flex: 0 0 220px;">
                            <label>Honorários Adv Autor</label>
                            <input type="text" id="val-hon-autor" class="coleta-input highlight" placeholder="R$ Honorários Autor">
                        </div>
                        <div class="col" style="flex: 1;">
                            <label><input type="checkbox" id="chk-hon-reu" checked style="margin-right: 5px;">Não há Honorários Adv Réu</label>
                            <div id="hon-reu-campos" class="hidden" style="margin-top: 6px;">
                                <input type="text" id="val-hon-reu" class="coleta-input" placeholder="R$ Honorários Réu" style="margin-bottom: 4px;">
                                <div style="display: flex; gap: 8px; flex-direction: column;">
                                    <label style="font-size: 11px;"><input type="radio" name="rad-hon-reu" value="suspensiva" checked> Condição Suspensiva</label>
                                    <label style="font-size: 11px;"><input type="radio" name="rad-hon-reu" value="percentual"> Percentual: <input type="text" id="val-hon-reu-perc" value="5%" style="width: 50px; margin-left: 5px;"></label>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="row">
                        <label style="font-size: 11px;"><input type="checkbox" id="ignorar-hon-autor"> Não há honorários autor</label>
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
                    <div id="link-acordao-container" style="margin-top: 4px;"></div>
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
                    <label>Preencha período, planilha e escolha se é período total para cada reclamada subsidiária:</label>
                </div>
                <div id="resp-diversos-container"></div>
                <button type="button" class="btn-action" id="btn-adicionar-periodo" style="margin-top: 10px;">+ Adicionar Reclamada Subsidiária</button>
            </fieldset>

            <!-- DETECÇÃO INICIAL (movido para depois de Custas) -->
            <fieldset>
                <legend>Detectados</legend>
                <div class="row">
                    <div class="col">
                        <label>Reclamadas</label>
                        <div id="det-reclamadas" class="partes-badges" style="min-height: 24px; padding: 3px; border: 1px solid #ddd; border-radius: 3px; background: #fafafa;"></div>
                    </div>
                    <div class="col">
                        <label>Peritos</label>
                        <div id="det-peritos" class="partes-badges" style="min-height: 24px; padding: 3px; border: 1px solid #ddd; border-radius: 3px; background: #fafafa;"></div>
                    </div>
                </div>
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

            <!-- Custas já foram movidas para o card 4 acima -->

            <!-- SEÇÃO 8: DEPÓSITO RECURSAL -->
            <fieldset id="fieldset-deposito">
                <legend>Depósito Recursal</legend>
                <div class="row">
                    <label><input type="checkbox" id="chk-deposito"> Há Depósito Recursal?</label>
                    <label style="margin-left: 20px;"><input type="checkbox" id="chk-pag-antecipado"> Pagamento Antecipado</label>
                </div>
                <div id="pag-antecipado-campos" class="hidden">
                    <div class="row">
                        <input type="text" id="pag-antecipado-id" placeholder="ID do Depósito">
                    </div>
                    <div class="row">
                        <label><input type="radio" name="lib-tipo" value="nenhum" checked> Padrão (extinção)</label>
                        <label style="margin-left: 15px;"><input type="radio" name="lib-tipo" value="remanescente"> Com Remanescente</label>
                        <label style="margin-left: 15px;"><input type="radio" name="lib-tipo" value="devolucao"> Com Devolução</label>
                    </div>
                    <div id="lib-remanescente-campos" class="hidden">
                        <div class="row">
                            <input type="text" id="lib-rem-valor" placeholder="Valor Remanescente (ex: 1.234,56)">
                            <input type="text" id="lib-rem-titulo" placeholder="Título (ex: custas processuais)">
                        </div>
                    </div>
                    <div id="lib-devolucao-campos" class="hidden">
                        <div class="row">
                            <input type="text" id="lib-dev-valor" placeholder="Valor Devolução (ex: 1.234,56)">
                        </div>
                    </div>
                </div>
                <div id="deposito-campos" class="hidden">
                    <div class="row">
                        <select id="dep-tipo">
                            <option value="bb" selected>Banco do Brasil</option>
                            <option value="sif">CEF (SIF)</option>
                            <option value="garantia">Seguro Garantia</option>
                        </select>
                        <input type="text" id="dep-depositante" placeholder="Depositante (Reclamada)">
                        <input type="text" id="dep-id" placeholder="ID da Guia">
                    </div>
                    <div class="row">
                        <label><input type="checkbox" id="dep-principal" checked> Depositado pela Devedora Principal?</label>
                    </div>
                    <div class="row" id="dep-liberacao-row">
                        <label><input type="radio" name="rad-dep-lib" value="reclamante" checked> Liberação simples (Reclamante)</label>
                        <label style="margin-left: 10px;"><input type="radio" name="rad-dep-lib" value="detalhada"> Liberação detalhada (Crédito, INSS, Hon.)</label>
                    </div>
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

        if (!document.getElementById('btn-abrir-homologacao') || !document.getElementById('homologacao-overlay')) {
            err('Falha apos insercao: elementos principais do overlay nao encontrados.');
            return;
        }

        // ==========================================
        // 3. LÓGICA DE INTERFACE E EVENTOS (TOGGLES)
        // ==========================================
        const $ = (id) => document.getElementById(id);
        dbg('Binding de eventos iniciado.');
        $('btn-abrir-homologacao').onclick = async () => {
            dbg('Clique em Gerar Homologacao detectado.');
            try {
                // Executar prep.js: varredura + extração da sentença + AJ-JT
                const peritosConh = window.hcalcPeritosConhecimentoDetectados || [];
                const partesData = window.hcalcPartesData || {};
                const prep = await executarPrep(partesData, peritosConh);

            // Retrocompat: manter window.hcalcTimelineData para construirSecaoIntimacoes
            window.hcalcTimelineData = {
                sentenca: prep.sentenca.data ? { data: prep.sentenca.data, href: null } : null,
                acordaos: prep.acordaos,
                editais: prep.editais
            };

            // Link sentença
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

            // Preencher custas automaticamente se extraídas
            if (prep.sentenca.custas && $('val-custas')) {
                $('val-custas').value = prep.sentenca.custas;
            }

            // Depósito recursal: visível se tem acórdãos
            const fieldsetDeposito = $('fieldset-deposito');
            const linkAcordaoContainer = $('link-acordao-container');
            if (linkAcordaoContainer) linkAcordaoContainer.innerHTML = '';

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

            if (prep.acordaos.length === 0) {
                if (fieldsetDeposito) fieldsetDeposito.classList.add('hidden');
            } else {
                if (fieldsetDeposito) fieldsetDeposito.classList.remove('hidden');
                if (linkAcordaoContainer) {
                    prep.acordaos.forEach((acordao, i) => {
                        if (acordao.href) {
                            const lbl = prep.acordaos.length > 1 ? `Acórdão ${i + 1}` : `Acórdão`;
                            const a = document.createElement('a');
                            a.href = acordao.href;
                            a.target = "_blank";
                            a.innerHTML = `<i class="fas fa-external-link-alt"></i> ${lbl}`;
                            a.style.cssText = "display:block; color:#00509e; font-size:12px; margin-top:5px; text-decoration:none;";
                            linkAcordaoContainer.appendChild(a);
                        }
                    });
                    // RO/RR com depósito recursal
                    if (prep.depositos.length > 0) {
                        const depDiv = document.createElement('div');
                        depDiv.style.cssText = 'margin-top:8px; padding:6px; background:#fffde7; border:1px solid #fbbf24; border-radius:4px;';
                        depDiv.innerHTML = `<strong style="font-size:11px; color:#92400e;">📎 Depósitos Recursais (${prep.depositos.length}):</strong>`;
                        prep.depositos.forEach(dep => {
                            if (dep.href) {
                                const a = document.createElement('a');
                                a.href = dep.href;
                                a.target = '_blank';
                                a.innerHTML = `<i class="fas fa-external-link-alt"></i> ${dep.tipo} - ${dep.data || 'sem data'}`;
                                a.style.cssText = 'display:block; color:#92400e; font-size:11px; margin-top:3px; text-decoration:none;';
                                depDiv.appendChild(a);
                            }
                        });
                        linkAcordaoContainer.appendChild(depDiv);
                    }
                }
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

            // REGRA 1: Depósito recursal — depositante da RO/RR polo passivo
            if (prep.depositos.length > 0) {
                const chkDep = $('chk-deposito');
                const depCampos = $('deposito-campos');
                const depDepositante = $('dep-depositante');
                if (chkDep) { chkDep.checked = true; }
                if (depCampos) { depCampos.classList.remove('hidden'); }
                // Usar o nome do primeiro depositante encontrado
                if (depDepositante && prep.depositos[0].depositante) {
                    depDepositante.value = prep.depositos[0].depositante;
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
                if ($('val-custas')) $('val-custas').value = prep.sentenca.custas;
                // Sempre usa sentença como padrão
                if (custasStatusEl) custasStatusEl.value = 'devidas';
                if (custasOrigemEl) custasOrigemEl.value = 'sentenca';
                if ($('custas-data-origem') && prep.sentenca.data) {
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


                $('homologacao-overlay').style.display = 'flex';
                dbg('Overlay exibido para o usuario.');
                try {
                    const txt = await navigator.clipboard.readText();
                    if (txt && txt.trim().length > 0) {
                        $('val-id').value = txt.trim();
                    }
                } catch (e) { console.warn('Clipboard ignorado ou bloqueado', e); }
                updateHighlight();
            } catch (e) {
                err('Erro no handler do botao Gerar Homologacao:', e);
                alert('Erro ao abrir assistente. Verifique o console (F12).');
                return;
                }
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
            $('col-fgts-val').classList.toggle('hidden', !e.target.checked);
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

        $('resp-tipo').onchange = (e) => { $('resp-sub-opcoes').classList.toggle('hidden', e.target.value !== 'subsidiarias'); };

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

        $('btn-adicionar-periodo').onclick = (e) => {
            e.preventDefault();
            adicionarLinhaPeridoDiverso();
        };

        function adicionarLinhaPeridoDiverso() {
            const container = $('resp-diversos-container');
            const reclamadas = window.hcalcPartesData?.passivo?.map(r => r.nome) || [];
            const idx = container.children.length;
            const rowId = `periodo-diverso-${idx}`;

            const div = document.createElement('div');
            div.id = rowId;
            div.className = 'row';
            div.style.marginBottom = '15px';
            div.style.padding = '12px';
            div.style.backgroundColor = '#f5f5f5';
            div.style.borderRadius = '4px';

            let selectOptions = '<option value="">Selecione a reclamada...</option>';
            reclamadas.forEach(rec => {
                selectOptions += `<option value="${rec}">${rec}</option>`;
            });

            div.innerHTML = `
                <div style="margin-bottom: 10px;">
                    <label style="font-weight: bold;">Reclamada Subsidiária ${idx + 1}</label>
                    <select class="periodo-reclamada" data-idx="${idx}" style="width: 100%; padding: 8px;">
                        ${selectOptions}
                    </select>
                </div>
                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <label>Período</label>
                        <input type="text" class="periodo-periodo" data-idx="${idx}" placeholder="Ex: 01/01/2020 a 31/12/2020" style="width: 100%; padding: 8px;">
                    </div>
                    <div style="flex: 1;">
                        <label>ID Cálculo Separado</label>
                        <input type="text" class="periodo-id" data-idx="${idx}" placeholder="ID #XXXX" style="width: 100%; padding: 8px;">
                    </div>
                </div>
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
                    <label><input type="checkbox" class="periodo-total" data-idx="${idx}"> Período Total</label>
                    <button type="button" class="btn-action" style="padding: 8px; margin-left: auto; background: #d32f2f;" onclick="document.getElementById('${rowId}').remove();">Remover</button>
                </div>
            `;
            container.appendChild(div);
        }

        $('chk-hon-reu').onchange = (e) => {
            // Lógica invertida: marcado = "Não há" = esconde campos
            $('hon-reu-campos').classList.toggle('hidden', e.target.checked);
        };
        $('chk-perito-conh').onchange = (e) => { $('perito-conh-campos').classList.toggle('hidden', !e.target.checked); };

        $('chk-deposito').onchange = (e) => { $('deposito-campos').classList.toggle('hidden', !e.target.checked); };
        $('dep-tipo').onchange = (e) => { $('dep-liberacao-row').classList.toggle('hidden', e.target.value === 'garantia'); };
        $('dep-principal').onchange = (e) => { $('dep-liberacao-row').classList.toggle('hidden', !e.target.checked); };
        $('chk-pag-antecipado').onchange = (e) => { $('pag-antecipado-campos').classList.toggle('hidden', !e.target.checked); };

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

        const detReclamadasEl = $('det-reclamadas');
        const detPeritosEl = $('det-peritos');

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

                divRow.innerHTML = `
                    <div style="flex: 1; font-size: 13px; font-weight: bold; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 10px;" title="${parte.nome}">
                        ${parte.nome}
                    </div>
                    <div style="flex-shrink: 0;">
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
            if (!detReclamadasEl || !detPeritosEl) { return; }
            const partes = await derivePartesData();

            // Armazenar globalmente para uso em geração de textos
            window.hcalcPartesData = partes;

            const reclamadas = (partes?.passivo || []).map(p => p.nome).filter(Boolean);
            const peritos = ordenarComRogerioPrimeiro(extractPeritos(partes));
            const advogadosMap = extractAdvogadosPorReclamada(partes);
            const statusAdvMap = extractStatusAdvogadoPorReclamada(partes);

            window.hcalcStatusAdvogados = statusAdvMap;

            const reclamadasComStatus = (partes?.passivo || []).map((parte) => {
                const nome = parte?.nome || '';
                if (!nome) { return null; }
                const comAdv = statusAdvMap[nome] === true;
                return { nome, comAdv };
            }).filter(Boolean);

            const qtdComAdv = reclamadas.filter((nome) => statusAdvMap[nome] === true).length;
            const qtdSemAdv = reclamadas.length - qtdComAdv;

            // Log para debug
            console.log('hcalc: advogados por reclamada', advogadosMap);
            console.log('hcalc: status advogado por reclamada', statusAdvMap);

            // BADGES: Reclamadas
            if (reclamadasComStatus.length) {
                detReclamadasEl.innerHTML = reclamadasComStatus.map(r =>
                    `<span class="badge ${r.comAdv ? 'badge-blue' : 'badge-gray'}" title="${r.comAdv ? 'Com advogado' : 'Sem advogado'}">${r.nome}</span>`
                ).join('');
            } else {
                detReclamadasEl.innerHTML = '<span style="font-size: 11px; color: #999; font-style: italic;">Nenhuma reclamada detectada</span>';
            }

            // BADGES: Peritos
            if (peritos.length) {
                detPeritosEl.innerHTML = peritos.map(p =>
                    `<span class="badge badge-green">${p}</span>`
                ).join('');
            } else {
                detPeritosEl.innerHTML = '<span style="font-size: 11px; color: #999; font-style: italic;">Não há perícias</span>';
            }

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

        refreshDetectedPartes();

        // ==========================================
        // 4. LÓGICA DE NAVEGAÇÃO "COLETA INTELIGENTE"
        // ==========================================
        const orderSequence = [
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

                if (isFgtsSep) {
                    introTxt += `fixando o crédito do autor em ${bold(vCredito)} relativo ao principal, e ${bold(vFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(vData)}. `;
                } else {
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
                    const rdHonReu = document.querySelector('input[name="rad-hon-reu"]:checked').value;
                    if (rdHonReu === 'suspensiva') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, diante da gratuidade deferida.</p>`;
                    } else {
                        const p = $('val-hon-reu-perc').value;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}.</p>`;
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

                if ($('chk-deposito').checked) {
                    const tDep = $('dep-tipo').value;
                    const dNome = $('dep-depositante').value || '[RECLAMADA]';
                    const dId = $('dep-id').value || '[ID]';
                    let isPrin = $('dep-principal').checked;

                    const passivoDetectado = (window.hcalcPartesData?.passivo || []).map((p) => p?.nome).filter(Boolean);
                    const primeiraReclamada = passivoDetectado[0] || '';
                    const tipoRespAtual = $('resp-tipo')?.value || 'unica';
                    const isDepositoJudicial = tDep !== 'garantia';

                    let criterioLiberacaoDeposito = 'manual';
                    let depositanteResolvida = dNome;

                    if (passivoDetectado.length === 1) {
                        depositanteResolvida = passivoDetectado[0];
                        isPrin = true;
                        criterioLiberacaoDeposito = 'reclamada-unica';
                    } else if (tipoRespAtual === 'subsidiarias' && primeiraReclamada) {
                        depositanteResolvida = primeiraReclamada;
                        isPrin = true;
                        criterioLiberacaoDeposito = 'subsidiaria-principal';
                    } else if (tipoRespAtual === 'solidarias') {
                        depositanteResolvida = depositanteResolvida || primeiraReclamada || '[RECLAMADA]';
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
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Há depósito recursal da devedora ${naturezaDevedora} (${depositanteResolvida} - Id ${bold(dId)}) via ${bancoTxt}.</p>`;
                    if (!isDepositoJudicial) {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Tratando-se de seguro garantia, não há liberação imediata de valores nesta oportunidade.</p>`;
                    } else {
                        const modoSelecionado = (document.querySelector('input[name="rad-dep-lib"]:checked')?.value === 'detalhada')
                            ? 'detalhada'
                            : 'direta';

                        const depositosLiberaveis = deveLiberarDeposito
                            ? [{ depositante: depositanteResolvida, id: dId, banco: bancoTxt, modo: modoSelecionado }]
                            : [];

                        const formatarLista = (itens) => {
                            if (!itens || itens.length === 0) { return ''; }
                            if (itens.length === 1) { return itens[0]; }
                            if (itens.length === 2) { return `${itens[0]} e ${itens[1]}`; }
                            return `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
                        };

                        const montarListaDepositos = (deps) => {
                            const itens = deps.map((d) => `${d.depositante} #${bold(d.id)}`);
                            return formatarLista(itens);
                        };

                        const montarListaBancos = (deps) => {
                            const unicos = [...new Set(deps.map((d) => d.banco))];
                            return formatarLista(unicos);
                        };

                        const depsDiretos = depositosLiberaveis.filter((d) => d.modo === 'direta');
                        const depsDetalhados = depositosLiberaveis.filter((d) => d.modo === 'detalhada');

                        if (depsDiretos.length > 0) {
                            houveDepositoDireto = true;
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Libere-se o depósito recursal em favor do reclamante. Após, apure-se o remanescente devido.</p>`;
                        }

                        if (depsDetalhados.length > 0) {
                            const listaDeps = montarListaDepositos(depsDetalhados);
                            const listaBancos = montarListaBancos(depsDetalhados);

                            // Usar função unificada de liberação detalhada
                            houveLibecaoDetalhada = true;
                            gerarLiberacaoDetalhada({
                                depositoInfo: `o depósito recursal (${listaDeps} via ${listaBancos})`
                            });
                        }

                        if (!deveLiberarDeposito) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Por ora, não há liberação automática do depósito recursal informado.</p>`;
                        }
                    }
                }

                // PAGAMENTO ANTECIPADO - Substitui intimações completamente
                const isPagamentoAntecipado = $('chk-pag-antecipado').checked;
                if (isPagamentoAntecipado) {
                    const idPagAntecipado = $('pag-antecipado-id').value || '[ID]';
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Realizado depósito pela reclamada, #${bold(idPagAntecipado)}.</p>`;

                    // Usar função unificada de liberação detalhada
                    houveLibecaoDetalhada = true;
                    let proximoNum = gerarLiberacaoDetalhada({});

                    // Verificar tipo de liberação
                    const tipoLib = document.querySelector('input[name="lib-tipo"]:checked')?.value || 'nenhum';

                    if (tipoLib === 'devolucao') {
                        // Adicionar item de devolução
                        const valDev = $('lib-dev-valor').value || '[VALOR]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">${proximoNum}) Devolva-se à reclamada o valor pago a maior, no montante de ${bold('R$ ' + valDev)}, expedindo-se o competente alvará.</p>`;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestação das partes.</p>`;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Após, tornem conclusos para extinção da execução.</p>`;
                    } else if (tipoLib === 'remanescente') {
                        // Adicionar intimação de remanescente
                        const valRem = $('lib-rem-valor').value || '[VALOR]';
                        const tituloRem = $('lib-rem-titulo').value || '[TÍTULO]';
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Sem prejuízo, fica a reclamada intimada a pagar o valor remanescente de ${bold('R$ ' + valRem)} devidos a título de ${bold(tituloRem)}, em 15 dias, sob pena de execução.</p>`;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Cientes as partes.</p>`;
                    } else {
                        // Padrão (nenhum)
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Concede-se 05 dias para manifestações. Silentes, cumpra-se e, após, tornem conclusos para extinção da execução.</p>`;
                    }
                } else {
                    // INTIMAÇÕES (apenas se NÃO houver pagamento antecipado)
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

                    if (elsOpcoes.length > 0) {
                        elsOpcoes.forEach((sel) => {
                            const nome = sel.getAttribute('data-nome');
                            const v = sel.value;
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

            const linhasPeriodos = Array.from(document.querySelectorAll('#resp-diversos-container [id^="periodo-diverso-"]'));
            const usarDuplicacao = $('resp-diversos').checked && linhasPeriodos.length > 0;

            if (usarDuplicacao && passivoTotal > 1) {
                const principalSelecionada = $('resp-devedora-principal')?.value || '1';
                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A ${bold(principalSelecionada)} é devedora principal, as demais são subsidiárias.</p>`;

                text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>A - A devedora principal, ${bold(principalSelecionada)}, deverá ainda:</strong></p>`;
                appendBaseAteAntesPericiais({ idCalculo: idPlanilha, usarPlaceholder: false });

                linhasPeriodos.forEach((linha, i) => {
                    const idx = linha.id.replace('periodo-diverso-', '');
                    const nomeSub = document.querySelector(`.periodo-reclamada[data-idx="${idx}"]`)?.value || `[RECLAMADA ${i + 1}]`;
                    const idSub = document.querySelector(`.periodo-id[data-idx="${idx}"]`)?.value || `[ID ${i + 1}]`;
                    text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;"><strong>${String.fromCharCode(66 + i)} - Já em relação à reclamada subsidiária ${bold(nomeSub)}:</strong></p>`;
                    appendBaseAteAntesPericiais({ idCalculo: idSub, usarPlaceholder: true });
                });

                appendDisposicoesFinais();
            } else {
                let introTxt = '';
                if (isPerito && peritoEsclareceu) {
                    introTxt += `As impugnações apresentadas já foram objeto de esclarecimentos pelo Sr. Perito sob o #${bold(pecaPerito)}, nada havendo a ser reparado no laudo. Portanto, HOMOLOGO os cálculos do expert (#${bold(idPlanilha)}), `;
                } else {
                    introTxt += `Tendo em vista a concordância das partes, HOMOLOGO os cálculos apresentados pelo(a) ${u(autoria)} (#${bold(idPlanilha)}), `;
                }
                if (isFgtsSep) {
                    introTxt += `fixando o crédito do autor em ${bold('R$' + valCredito)} relativo ao principal, e ${bold('R$' + valFgts)} relativo ao ${bold('FGTS')} a ser recolhido em conta vinculada, atualizados para ${bold(valData)}. `;
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
                if (passivoTotal > 1) {
                    if ($('resp-tipo').value === 'solidarias') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Declaro que as reclamadas respondem de forma solidária pela presente execução.</p>`;
                    } else if ($('resp-tipo').value === 'subsidiarias') {
                        if ($('resp-integral').checked) {
                            text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">A primeira reclamada é devedora principal, as demais são subsidiárias pelo período integral do contrato, portanto, os valores neste momento são devidos apenas pela primeira.</p>`;
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
                    const rdHonReu = document.querySelector('input[name="rad-hon-reu"]:checked').value;
                    if (rdHonReu === 'suspensiva') {
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios pela reclamante sob condição suspensiva, diante da gratuidade deferida.</p>`;
                    } else {
                        const p = $('val-hon-reu-perc').value;
                        text += `<p style="text-align:justify; text-indent: 4.5cm; font-size:12pt;">Honorários advocatícios sucumbenciais em favor da reclamada na ordem de ${bold(p)}.</p>`;
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