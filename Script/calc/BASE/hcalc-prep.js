(function () {
    'use strict';
    const HCALC_DEBUG = false;
    const dbg = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err = (...args) => console.error('[hcalc]', ...args);

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
                && hasAnexoNoItem(item)) {
                const tipoRec = tipoDoc.includes('revista') ? 'RR' : 'RO';
                const depositante = nomePassivoDoItem(item);

                // Permitir recursos que não mostram o ícone de polo passivo
                // quando já foi detectado pelo menos um acórdão na timeline.
                // Nesse caso aceitamos itens cujo nome de parte (normalizado)
                // corresponde a alguma parte do passivo detectado.
                const poloPassivo = isPoloPassivoNoItem(item);
                const acordaoVisto = resultado.acordaos && resultado.acordaos.length > 0;
                let accept = poloPassivo;
                if (!accept && acordaoVisto) {
                    const passivoNames = (window.hcalcPartesData?.passivo || []).map(p => normalizeText(p.nome || ''));
                    const nomeNorm = normalizeText(depositante || '');
                    if (nomeNorm && passivoNames.includes(nomeNorm)) accept = true;
                }

                if (accept) {
                    resultado.recursosPassivo.push({ ...base, tipoRec, depositante, _itemRef: item });
                    return;
                }
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
            try { safeDispatch(previewLink, 'click', { bubbles: true, cancelable: true }); }
            catch (_) { try { previewLink.click(); } catch (_2) { } }
        }
    }

    // Dispatch seguro local para este arquivo (evita erro quando UIEventInit.view é problemático)
    function safeDispatch(el, type, opts) {
        try { el.dispatchEvent(new MouseEvent(type, opts || {})); return true; }
        catch (e) {
            try { const safeOpts = Object.assign({}, opts || {}); if ('view' in safeOpts) delete safeOpts.view; el.dispatchEvent(new MouseEvent(type, safeOpts)); return true; }
            catch (e2) { try { el.click(); return true; } catch (e3) {} try { const ev = document.createEvent('MouseEvents'); ev.initMouseEvent(type, !!(opts && opts.bubbles), !!(opts && opts.cancelable), window, 0,0,0,0,0,false,false,false,false,0,null); el.dispatchEvent(ev); return true; } catch (e4) {} }
        }
        return false;
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
        // Exceções absolutas: se tiver essas palavras, é anexo comum
        if (/jurisprudência|jurisprudencia|sentença|sentenca|isenção|isencao/.test(t)) return { tipo: 'Anexo', ordem: 4 };

        // PRIORIDADE: Preferir identificar Depósito recursal antes de classificar como Custas.
        // Alguns anexos mencionam ambas palavras; considerando a importância do depósito recursal
        // para o fluxo, priorizamos sua detecção.
        if (/depósito|deposito|preparo/.test(t)) return { tipo: 'Depósito', ordem: 1 };
        // GRU/Custas ficam em seguida
        if (/gru|custas/.test(t)) return { tipo: 'Custas', ordem: 2 };
        // PRIORIDADE 3: Garantia
        if (/garantia|seguro|susep|apólice|apolice/.test(t)) return { tipo: 'Garantia', ordem: 3 };
        // PRIORIDADE 4: Outros anexos
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
                try { safeDispatch(toggle, 'click', { bubbles: true }); } catch (e) { }
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
                // Log de depuração para auxiliar identificação de anexos (visível no console)
                try {
                    console.log('[prep] anexos extraídos:', anexos.map(a => ({ id: a.id, tipo: a.tipo, texto: a.texto ? a.texto.slice(0,80) : '' })));
                } catch (e) { /* ignore */ }
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
    async function buscarPartesEdital(editaisItems, passivo, abortSignal) {
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

            // #region agent log
            fetch('http://127.0.0.1:7803/ingest/28b8f51b-bfb8-4f41-93f6-1611c83e87d0', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Debug-Session-Id': '6b8a26'
                },
                body: JSON.stringify({
                    sessionId: '6b8a26',
                    runId: 'pre-fix',
                    hypothesisId: 'H1',
                    location: 'hcalc-prep.js:611',
                    message: 'buscarPartesEdital antes de lerHtmlOriginal',
                    data: { hasAbortSignal: !!abortSignal, editaisCount: editaisItems.length },
                    timestamp: Date.now()
                })
            }).catch(() => { });
            // #endregion agent log

            const resHtml = await lerHtmlOriginal(6000, abortSignal);
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
                // Excluir itens cuja classificação de anexos indicou 'Custas'
                const excluded = [];
                const recs = (timeline.recursosPassivo || []).filter(r => {
                    const anexos = r.anexos || [];
                    const isCustas = anexos.some(a => (a.tipo || '').toLowerCase() === 'custas');
                    if (isCustas) excluded.push({ texto: r.texto, anexos });
                    return !isCustas;
                });

                // Debug: listar recursos excluídos por serem 'Custas' (visível quando HCALC_DEBUG=true)
                if (excluded.length > 0) {
                    excluded.forEach(ex => dbg('prep: exclui recurso como Custas:', ex.texto, ex.anexos.map(a => a.tipo)));
                }

                prepResult.depositos = recs.map(r => ({
                    tipo: r.tipoRec,
                    texto: r.texto,
                    href: r.href,
                    data: r.data,
                    depositante: r.depositante || '',
                    anexos: r.anexos || []
                }));

                // Ordenar depósitos por data (mais antigos primeiro)
                function _dateToTs(dstr) {
                    if (!dstr) return 0;
                    const parts = dstr.split('/');
                    if (parts.length < 3) return 0;
                    const dia = parseInt(parts[0], 10);
                    const mes = parseInt(parts[1], 10) - 1;
                    const ano = parseInt(parts[2], 10);
                    return new Date(ano, mes, dia).getTime();
                }
                prepResult.depositos.sort((a, b) => _dateToTs(a.data) - _dateToTs(b.data));
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

                // #region agent log
                fetch('http://127.0.0.1:7803/ingest/28b8f51b-bfb8-4f41-93f6-1611c83e87d0', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Debug-Session-Id': '6b8a26'
                    },
                    body: JSON.stringify({
                        sessionId: '6b8a26',
                        runId: 'pre-fix',
                        hypothesisId: 'H1',
                        location: 'hcalc-prep.js:791',
                        message: 'executarPrep chamando buscarPartesEdital',
                        data: {
                            editaisCount: timeline.editais.length,
                            passivoCount: passivoArray.length,
                            hasAbortController: !!window.hcalcState.abortController
                        },
                        timestamp: Date.now()
                    })
                }).catch(() => { });
                // #endregion agent log

                prepResult.partesIntimadasEdital = await buscarPartesEdital(timeline.editais, passivoArray, signal);
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

    window.executarPrep = executarPrep;
    window.destacarElementoNaTimeline = destacarElementoNaTimeline;
    window.encontrarItemTimeline = encontrarItemTimeline;
    window.expandirAnexos = expandirAnexos;
})();
