// pdf.compress.js — Módulo PJeTools: Ajustar PDF v2.1.0
// Comprime PDF via rasterização canvas+JPEG (mesma técnica do ilovepdf)
// e divide em partes de até 9,5 MB para envio no PJe
// v2.1.0: parse único do doc-fonte, amostragem por nível (1 pass real),
// encode async sem base64, cap de área de canvas e barra monotônica
(function () {
    'use strict';

    const MOD_NAME  = 'AjustarPDF';
    const MAX_BYTES = 9.5 * 1024 * 1024;   // 9,5 MB por parte
    // Cap de área de canvas (px²): o Firefox limita a área total de um canvas
    // (~16,7 MP) e scans grandes estouram o limite — deixamos margem.
    // 12_000_000 usa numeric separator (ES2021) — alvo é Firefox moderno;
    // equivalente a 12000000 (12 milhões de pixels = 12 MP).
    const MAX_CANVAS_AREA = 12_000_000;

    // Níveis de qualidade tentados em cascata (DPI × qualidade JPEG)
    // Mais alto = melhor qualidade, menos compressão
    const QUALITY_LEVELS = [
        { dpi: 150, quality: 0.82, label: 'Alta (150 DPI / Q82)' },
        { dpi: 130, quality: 0.72, label: 'Média-Alta (130 DPI / Q72)' },
        { dpi: 110, quality: 0.62, label: 'Média (110 DPI / Q62)' },
        { dpi: 96,  quality: 0.52, label: 'Baixa (96 DPI / Q52)' },
        { dpi: 80,  quality: 0.42, label: 'Mínima (80 DPI / Q42)' },
    ];

    // ──────────────────────────────────────────────
    // Helpers UI
    // ──────────────────────────────────────────────
    function _log(msg) { console.log(`[${MOD_NAME}] ${msg}`); }

    function _modalCSS() {
        return `
        #pjepdf-overlay {
            position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:2147483640;
            display:flex;align-items:center;justify-content:center;
            font-family:'Segoe UI',sans-serif;
        }
        #pjepdf-box {
            background:#fff;border-radius:10px;padding:28px 32px;min-width:340px;max-width:520px;
            box-shadow:0 12px 40px rgba(0,0,0,.35);position:relative;
        }
        #pjepdf-box h2 {
            margin:0 0 16px;font-size:16px;color:#212529;
            border-bottom:2px solid #007bff;padding-bottom:8px;
        }
        #pjepdf-status {
            font-size:13px;color:#495057;margin-bottom:8px;min-height:20px;word-break:break-word;
        }
        #pjepdf-substatus {
            font-size:11px;color:#868e96;margin-bottom:10px;min-height:16px;
        }
        #pjepdf-progress-bar {
            height:8px;border-radius:4px;background:#e9ecef;overflow:hidden;margin-bottom:14px;
        }
        #pjepdf-progress-inner {
            height:100%;border-radius:4px;background:#007bff;
            width:0%;transition:width .25s ease;
        }
        #pjepdf-links { display:flex;flex-direction:column;gap:8px;margin-bottom:14px; }
        .pjepdf-link-btn {
            display:flex;align-items:center;gap:8px;padding:8px 14px;
            background:#007bff;color:#fff;border-radius:6px;text-decoration:none;
            font-size:13px;font-weight:600;transition:background .2s;
        }
        .pjepdf-link-btn:hover { background:#0056b3;color:#fff; }
        .pjepdf-link-btn .sz { font-weight:400;opacity:.85;font-size:11px;margin-left:auto; }
        #pjepdf-close {
            position:absolute;top:12px;right:14px;background:none;border:none;
            font-size:20px;cursor:pointer;color:#666;line-height:1;
        }
        #pjepdf-close:hover { color:#dc3545; }
        #pjepdf-info-box {
            background:#f8f9fa;border:1px solid #dee2e6;border-radius:6px;
            padding:10px 14px;font-size:12px;color:#495057;margin-bottom:14px;
            line-height:1.6;
        }
        `;
    }

    function _criarModal() {
        document.getElementById('pjepdf-overlay')?.remove();
        document.getElementById('pjepdf-css')?.remove();
        const style = document.createElement('style');
        style.id = 'pjepdf-css';
        style.textContent = _modalCSS();
        document.head.appendChild(style);

        const overlay = document.createElement('div');
        overlay.id = 'pjepdf-overlay';
        overlay.innerHTML = `
            <div id="pjepdf-box">
                <button id="pjepdf-close" title="Fechar">✕</button>
                <h2>📎 Ajustar PDF</h2>
                <div id="pjepdf-status">Selecione um arquivo PDF...</div>
                <div id="pjepdf-substatus"></div>
                <div id="pjepdf-progress-bar"><div id="pjepdf-progress-inner"></div></div>
                <div id="pjepdf-info-box" style="display:none"></div>
                <div id="pjepdf-links"></div>
            </div>
        `;
        document.body.appendChild(overlay);

        document.getElementById('pjepdf-close').onclick = () => overlay.remove();
        overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });

        return overlay;
    }

    function _setStatus(msg, sub, pct) {
        const el    = document.getElementById('pjepdf-status');
        const subEl = document.getElementById('pjepdf-substatus');
        if (el)    el.textContent    = msg ?? '';
        if (subEl) subEl.textContent = sub ?? '';
        if (pct !== undefined) {
            const bar = document.getElementById('pjepdf-progress-inner');
            if (bar) bar.style.width = Math.min(100, Math.max(0, pct)) + '%';
        }
        _log(msg + (sub ? ' | ' + sub : ''));
    }

    function _setInfo(html) {
        const box = document.getElementById('pjepdf-info-box');
        if (!box) return;
        box.style.display = html ? '' : 'none';
        box.innerHTML = html;
    }

    function _addDownloadLink(blob, filename, label) {
        const url  = URL.createObjectURL(blob);
        const size = (blob.size / (1024 * 1024)).toFixed(2) + ' MB';
        const container = document.getElementById('pjepdf-links');
        if (!container) return;
        const a = document.createElement('a');
        a.className = 'pjepdf-link-btn';
        a.href      = url;
        a.download  = filename;
        a.innerHTML = `📄 ${label} <span class="sz">${size}</span>`;
        container.appendChild(a);
    }

    // ──────────────────────────────────────────────
    // Encode JPEG async (sem round-trip base64)
    // ──────────────────────────────────────────────
    // `convertToBlob` é o caminho rápido (OffscreenCanvas); fallback para o
    // `toBlob` clássico de HTMLCanvasElement. Ambos async, sem base64.
    function _canvasParaJpegBytes(canvas, quality) {
        return new Promise((resolve, reject) => {
            const toBlobFn = typeof canvas.convertToBlob === 'function'
                ? opts => canvas.convertToBlob(opts)
                : (typeof canvas.toBlob === 'function'
                    ? opts => new Promise((res, rej) => canvas.toBlob(b => b ? res(b) : rej(new Error('toBlob retornou null')), opts.type, opts.quality))
                    : null);
            if (!toBlobFn) { reject(new Error('Canvas não suporta convertToBlob nem toBlob')); return; }
            toBlobFn({ type: 'image/jpeg', quality })
                .then(blob => blob.arrayBuffer())
                .then(buf => resolve(new Uint8Array(buf)))
                .catch(reject);
        });
    }

    // Cede ciclo ao event loop para o modal repintar entre páginas
    function _yieldUI() {
        return new Promise(r => requestAnimationFrame(() => r()));
    }

    /**
     * Pass completo de rasterização: renderiza TODAS as páginas do doc-fonte
     * (pdf.js JÁ carregado por _comprimirPdf — NÃO re-parseia) em JPEG e
     * monta o PDF final via pdf-lib.
     * @param {Object} srcPdf     — doc pdf.js já carregado (getDocument feito em _comprimirPdf)
     * @param {number} totalPages — nº de páginas do doc-fonte
     * @param {number} dpi        — resolução de render (72 = 1:1)
     * @param {number} quality    — qualidade JPEG (0.0–1.0)
     * @param {number} pctStart   — início da banda de progresso (%)
     * @param {number} pctEnd     — fim da banda de progresso (%)
     * @param {Object} opts       — { levelLabel, estimativaMB, t0, paginasAmostradas }
     * @returns {Promise<Uint8Array>} PDF montado (newDoc.save)
     */
    async function _rasterizar(srcPdf, totalPages, dpi, quality, pctStart, pctEnd, opts) {
        const { levelLabel = '', estimativaMB = '', t0 = performance.now(), paginasAmostradas = 0 } = opts || {};

        if (typeof PDFLib === 'undefined') throw new Error('pdf-lib não carregado (PDFLib indefinido)');
        const { PDFDocument } = PDFLib;

        const newDoc = await PDFDocument.create();
        let concluidas = paginasAmostradas;   // amostragem já conta como trabalho feito
        let lastPct    = pctStart;            // garante barra monotônica

        for (let i = 1; i <= totalPages; i++) {
            // ── Render da página (cap 12 MP + fundo branco + cleanup internos) ──
            const { bytes, w, h } = await _renderPaginaJpeg(srcPdf, i, dpi, quality);

            // ── Montagem do PDF final (padrão v2.0.0: página do tamanho do canvas) ──
            const img  = await newDoc.embedJpg(bytes);
            const page = newDoc.addPage([w, h]);
            page.drawImage(img, { x: 0, y: 0, width: w, height: h });

            // ── Telemetria (monotônica, banda pctStart→pctEnd) ──
            concluidas++;
            const elapsed   = (performance.now() - t0) / 1000;
            const pps       = elapsed > 0 ? concluidas / elapsed : 0;
            const restantes = totalPages - i;
            const etaSeg    = pps > 0 ? Math.round(restantes / pps) : null;
            const pct       = Math.max(lastPct, pctStart + ((i - 1) / totalPages) * (pctEnd - pctStart));
            lastPct         = pct;

            _setStatus(
                `Comprimindo página ${i}/${totalPages}`,
                `Nível ${levelLabel} · Estimativa ~${estimativaMB} MB · ` +
                `${pps.toFixed(1)} págs/s · ETA ~${etaSeg === null ? '—' : etaSeg + 's'}`,
                pct
            );

            // ── Cede o event loop para o modal repintar (Importante 1) ──
            await _yieldUI();
        }

        return await newDoc.save({ useObjectStreams: true });
    }

    // ──────────────────────────────────────────────
    // Núcleo: renderiza páginas via pdf.js → JPEG → pdf-lib
    // ──────────────────────────────────────────────

    /**
     * Renderiza UMA página do doc-fonte em JPEG (Uint8Array).
     * Reutilizada pela amostragem e pelo pass completo.
     * @param {Object} srcPdf   — doc pdf.js JÁ carregado
     * @param {number} pageNum  — página 1-based
     * @param {number} dpi      — resolução (72 = 1:1)
     * @param {number} quality  — qualidade JPEG (0.0–1.0)
     * @returns {Promise<{bytes: Uint8Array, w: number, h: number}>}
     */
    async function _renderPaginaJpeg(srcPdf, pageNum, dpi, quality) {
        const page = await srcPdf.getPage(pageNum);
        const scale = dpi / 72;
        let viewport = page.getViewport({ scale });

        // Cap de área: o Firefox limita a área total de um canvas (~16,7 MP);
        // scans grandes estouram o limite e falham — reduzimos a escala.
        if (viewport.width * viewport.height > MAX_CANVAS_AREA) {
            const areaOriginal = viewport.width * viewport.height;
            const novoScale    = scale * Math.sqrt(MAX_CANVAS_AREA / areaOriginal);
            viewport = page.getViewport({ scale: novoScale });
            _log(`Pág. ${pageNum}: cap de canvas (${(areaOriginal / 1e6).toFixed(1)} MP → ${(MAX_CANVAS_AREA / 1e6).toFixed(1)} MP)`);
        }

        const canvas = document.createElement('canvas');
        canvas.width  = Math.round(viewport.width);
        canvas.height = Math.round(viewport.height);

        const ctx = canvas.getContext('2d');
        // Fundo branco (PDFs transparentes ficam pretos sem isso)
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        await page.render({ canvasContext: ctx, viewport }).promise;

        const bytes = await _canvasParaJpegBytes(canvas, quality);

        // Liberar memória
        canvas.width = canvas.height = 0;
        page.cleanup();

        return { bytes, w: Math.round(viewport.width), h: Math.round(viewport.height) };
    }

    /**
     * Comprime o PDF com parse ÚNICO do doc-fonte:
     *  1) FASE AMOSTRAGEM (0–8%): até 2 páginas de amostra por nível → estimativa de tamanho
     *  2) FASE COMPRESSÃO (8–88%): UM pass completo no nível escolhido
     *  3) Caso raro (amostragem imprecisa): tenta nível pior SEM resetar a barra
     * @param {Uint8Array} originalBytes — bytes do PDF original
     * @returns {Promise<{bytes: Uint8Array, label: string}>}
     */
    async function _comprimirPdf(originalBytes) {
        if (typeof pdfjsLib === 'undefined') throw new Error('pdf.js não carregado (pdfjsLib indefinido)');

        // Configura worker do pdf.js (CDN, mesma versão do @require)
        pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';

        // .slice() protege o buffer original de transferências do worker
        const loadingTask = pdfjsLib.getDocument({ data: originalBytes.slice() });
        let srcPdf = null;

        try {
            srcPdf      = await loadingTask.promise;
            const totalPages = srcPdf.numPages;
            const t0         = performance.now();

            // ── FASE 1: AMOSTRAGEM (barra 0–8%) ──────────────
            // Até 2 páginas de amostra (1ª e a do meio) por nível para
            // estimar o tamanho total sem renders completos.
            const idxAmostras = totalPages === 1 ? [1] : [1, Math.max(2, Math.ceil(totalPages / 2))];
            const estimativas = [];   // { bytesPorPag, estimativaMB }

            for (let i = 0; i < QUALITY_LEVELS.length; i++) {
                const { dpi, quality, label } = QUALITY_LEVELS[i];
                const pct = (i / QUALITY_LEVELS.length) * 8;

                _setStatus(
                    `Analisando: ${label}`,
                    `Amostragem ${i + 1}/${QUALITY_LEVELS.length} · ${idxAmostras.length} pág. de amostra`,
                    pct
                );

                let soma = 0;
                for (const nPg of idxAmostras) {
                    const { bytes } = await _renderPaginaJpeg(srcPdf, nPg, dpi, quality);
                    soma += bytes.length;
                }
                const bytesPorPag  = soma / idxAmostras.length;
                const estimativaMB = (bytesPorPag * totalPages) / 1024 / 1024;
                estimativas.push({ bytesPorPag, estimativaMB });
                _log(`${label}: amostra ${(bytesPorPag / 1024).toFixed(0)} KB/pág → estimativa total ~${estimativaMB.toFixed(2)} MB`);
            }

            // Escolhe o primeiro nível (do mais alto ao mais baixo) que couber.
            // Se nenhum couber, usa o último (mais comprimido) — o split resolve.
            let nivelIdx = QUALITY_LEVELS.length - 1;
            for (let i = 0; i < QUALITY_LEVELS.length; i++) {
                if (estimativas[i].estimativaMB * 1024 * 1024 <= MAX_BYTES) { nivelIdx = i; break; }
            }

            // ── FASE 2: COMPRESSÃO (barra 8–88%) — UM ÚNICO pass ──
            // O pass escolhido preenche 8→88%. Retries (caso raro de
            // amostragem imprecisa) avançam dentro da banda fina 88→89%,
            // garantindo barra MONOTÔNICA sem invadir a faixa do split (89%+).
            let melhorBytes = null;
            let melhorLabel = '';
            let pctAtual    = 8;

            while (nivelIdx < QUALITY_LEVELS.length) {
                const { dpi, quality, label } = QUALITY_LEVELS[nivelIdx];
                const estimativaMB = estimativas[nivelIdx].estimativaMB.toFixed(2);

                const primeiroTry = (pctAtual === 8);
                const pctFim      = primeiroTry ? 88 : pctAtual + (89 - pctAtual) / (QUALITY_LEVELS.length - nivelIdx);

                _setStatus(`Comprimindo: ${label}`, `Estimativa ~${estimativaMB} MB`, pctAtual);

                const result = await _rasterizar(
                    srcPdf, totalPages, dpi, quality, pctAtual, pctFim,
                    { levelLabel: label, estimativaMB, t0, paginasAmostradas: idxAmostras.length }
                );
                _log(`${label}: ${(result.length / 1024 / 1024).toFixed(2)} MB`);
                pctAtual = pctFim;

                melhorBytes = result;
                melhorLabel = label;

                // Amostragem imprecisa: ainda grande → tenta o próximo nível
                // pior SEM resetar a barra (mantém monotonicidade).
                if (result.length <= MAX_BYTES) break;
                _log(`${label} excedeu MAX_BYTES (${(result.length / 1024 / 1024).toFixed(2)} MB) — tentando nível pior sem reiniciar`);
                nivelIdx++;
            }

            return { bytes: melhorBytes, label: melhorLabel };

        } finally {
            // Libera o doc pdf.js (worker + memória) em qualquer saída do fluxo
            try { if (srcPdf) await srcPdf.destroy(); } catch (_) { /* noop */ }
            try { await loadingTask.destroy(); } catch (_) { /* noop */ }
        }
    }

    // ──────────────────────────────────────────────
    // Divisão em partes (pdf-lib, API correta)
    // ──────────────────────────────────────────────
    async function _dividirPdf(sourceBytes, maxBytes) {
        const { PDFDocument } = PDFLib;
        const sourceDoc  = await PDFDocument.load(sourceBytes, { ignoreEncryption: true });
        const totalPages = sourceDoc.getPageCount();
        const partes     = [];
        let   pageIdx    = 0;

        _setStatus(`Dividindo em partes (${totalPages} págs.)...`, '', 89);

        while (pageIdx < totalPages) {
            let lo = 1, hi = totalPages - pageIdx;
            let melhorBytes = null, melhorCount = 0;

            while (lo <= hi) {
                const mid   = Math.floor((lo + hi) / 2);
                const cpIdx = Array.from({ length: mid }, (_, k) => pageIdx + k);
                const chunk = await PDFDocument.create();
                const pages = await chunk.copyPages(sourceDoc, cpIdx);  // ✅ API correta
                pages.forEach(p => chunk.addPage(p));
                const bytes = await chunk.save({ useObjectStreams: true });

                if (bytes.length <= maxBytes) {
                    melhorBytes = bytes;
                    melhorCount = mid;
                    lo = mid + 1;
                } else {
                    hi = mid - 1;
                }
            }

            // Fallback: página muito grande sozinha
            if (!melhorBytes) {
                const chunk = await PDFDocument.create();
                const [p]   = await chunk.copyPages(sourceDoc, [pageIdx]);
                chunk.addPage(p);
                melhorBytes = await chunk.save({ useObjectStreams: true });
                melhorCount = 1;
                _log(`Aviso: pág. ${pageIdx + 1} sozinha → ${(melhorBytes.length / 1024 / 1024).toFixed(2)} MB`);
            }

            partes.push(melhorBytes);
            _setStatus(
                `Parte ${partes.length}: ${(melhorBytes.length / 1024 / 1024).toFixed(2)} MB (${melhorCount} págs.)`,
                '',
                89 + Math.round(((pageIdx + melhorCount) / totalPages) * 6)   // faixa 89–95%
            );
            pageIdx += melhorCount;
        }

        return partes;
    }

    // ──────────────────────────────────────────────
    // Ponto de entrada
    // ──────────────────────────────────────────────
    async function executarAjustarPDF() {
        _criarModal();

        const input = document.createElement('input');
        input.type   = 'file';
        input.accept = 'application/pdf,.pdf';
        input.style.display = 'none';
        document.body.appendChild(input);

        input.onchange = async () => {
            const file = input.files[0];
            input.remove();
            if (!file) { _setStatus('Nenhum arquivo selecionado.', '', 0); return; }

            const originalBytes = new Uint8Array(await file.arrayBuffer());
            const originalMB    = file.size / 1024 / 1024;
            const baseName      = file.name.replace(/\.pdf$/i, '');

            _setStatus(`Lendo "${file.name}" (${originalMB.toFixed(2)} MB)...`, '', 5);

            try {
                // ── 1. Comprimir ───────────────────────────
                const { bytes: compressedBytes, label: usedLevel } = await _comprimirPdf(originalBytes);
                const compressedMB = compressedBytes.length / 1024 / 1024;
                const reducao      = Math.round((1 - compressedBytes.length / originalBytes.length) * 100);

                _setInfo(
                    `<strong>Original:</strong> ${originalMB.toFixed(2)} MB &nbsp;→&nbsp; ` +
                    `<strong>Comprimido:</strong> ${compressedMB.toFixed(2)} MB ` +
                    `<strong style="color:${reducao > 0 ? '#28a745' : '#dc3545'}">(${reducao > 0 ? '-' : '+'}${Math.abs(reducao)}%)</strong><br>` +
                    `<small>Nível usado: ${usedLevel}</small>`
                );

                // ── 2. Cabe em um arquivo? ─────────────────
                if (compressedBytes.length <= MAX_BYTES) {
                    _setStatus('✅ Compressão concluída! Arquivo dentro do limite.', '', 100);
                    const blob = new Blob([compressedBytes], { type: 'application/pdf' });
                    _addDownloadLink(blob, `${baseName}_comprimido.pdf`, `${baseName}_comprimido.pdf`);
                    return;
                }

                // ── 3. Ainda grande: dividir ───────────────
                _setStatus(`Ainda ${compressedMB.toFixed(2)} MB após compressão. Dividindo...`, '', 88);
                const partes = await _dividirPdf(compressedBytes, MAX_BYTES);

                _setStatus(`✅ Dividido em ${partes.length} parte(s). Clique para baixar:`, '', 100);
                partes.forEach((partBytes, i) => {
                    const blob  = new Blob([partBytes], { type: 'application/pdf' });
                    const fname = `${baseName}_parte${String(i + 1).padStart(2, '0')}.pdf`;
                    _addDownloadLink(blob, fname, fname);
                });

            } catch (err) {
                _setStatus(`❌ Erro: ${err.message}`, '', 0);
                console.error(`[${MOD_NAME}]`, err);
            }
        };

        input.click();
    }

    window.executarAjustarPDF = executarAjustarPDF;
    _log('Módulo carregado (v2.1.0) — compressão via canvas+JPEG (parse único + amostragem).');
})();
