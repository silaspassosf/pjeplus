// pdf.compress.js — Módulo PJeTools: Ajustar PDF v2.0.0
// Comprime PDF via rasterização canvas+JPEG (mesma técnica do ilovepdf)
// e divide em partes de até 9,5 MB para envio no PJe
(function () {
    'use strict';

    const MOD_NAME  = 'AjustarPDF';
    const MAX_BYTES = 9.5 * 1024 * 1024;   // 9,5 MB por parte

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
        const el  = document.getElementById('pjepdf-status');
        const sub2 = document.getElementById('pjepdf-substatus');
        if (el)   el.textContent  = msg  ?? '';
        if (sub2) sub2.textContent = sub ?? '';
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
    // Conversão dataURL → Uint8Array
    // ──────────────────────────────────────────────
    function _dataUrlToBytes(dataUrl) {
        const base64 = dataUrl.split(',')[1];
        const binary = atob(base64);
        const bytes  = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        return bytes;
    }

    // ──────────────────────────────────────────────
    // Núcleo: renderiza páginas via pdf.js → JPEG → pdf-lib
    // ──────────────────────────────────────────────

    /**
     * Rasteriza o PDF em um novo PDF com imagens JPEG comprimidas.
     * @param {Uint8Array} pdfBytes  — bytes do PDF original
     * @param {number}     dpi       — resolução de renderização (72 = 1:1)
     * @param {number}     quality   — qualidade JPEG (0.0–1.0)
     * @param {number}     pctStart  — % inicial da barra de progresso
     * @param {number}     pctEnd    — % final da barra de progresso
     * @returns {Promise<Uint8Array>}
     */
    async function _rasterizar(pdfBytes, dpi, quality, pctStart = 10, pctEnd = 90) {
        if (typeof pdfjsLib === 'undefined') throw new Error('pdf.js não carregado (pdfjsLib indefinido)');
        if (typeof PDFLib === 'undefined')   throw new Error('pdf-lib não carregado (PDFLib indefinido)');

        // Configura worker do pdf.js (CDN, mesma versão do @require)
        pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';

        const loadingTask = pdfjsLib.getDocument({ data: pdfBytes.slice() });
        const srcPdf      = await loadingTask.promise;
        const totalPages  = srcPdf.numPages;

        const { PDFDocument } = PDFLib;
        const newDoc = await PDFDocument.create();
        const scale  = dpi / 72;

        for (let i = 1; i <= totalPages; i++) {
            const pct = pctStart + ((i - 1) / totalPages) * (pctEnd - pctStart);
            _setStatus(
                `Comprimindo página ${i}/${totalPages}...`,
                `DPI: ${dpi}  Qualidade JPEG: ${Math.round(quality * 100)}%`,
                pct
            );

            const page     = await srcPdf.getPage(i);
            const viewport = page.getViewport({ scale });

            const canvas = document.createElement('canvas');
            canvas.width  = Math.round(viewport.width);
            canvas.height = Math.round(viewport.height);

            const ctx = canvas.getContext('2d');
            // Fundo branco (PDFs transparentes ficam pretos sem isso)
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            await page.render({ canvasContext: ctx, viewport }).promise;

            const dataUrl   = canvas.toDataURL('image/jpeg', quality);
            const jpegBytes = _dataUrlToBytes(dataUrl);

            const img     = await newDoc.embedJpg(jpegBytes);
            const pdfPage = newDoc.addPage([canvas.width, canvas.height]);
            pdfPage.drawImage(img, { x: 0, y: 0, width: canvas.width, height: canvas.height });

            // Liberar memória
            canvas.width = canvas.height = 0;
            page.cleanup();
        }

        return await newDoc.save({ useObjectStreams: true });
    }

    /**
     * Comprime o PDF tentando vários níveis de qualidade em cascata.
     * Retorna o melhor resultado (menor tamanho que ainda ≤ MAX_BYTES,
     * ou o menor possível se nenhum couber).
     */
    async function _comprimirPdf(originalBytes) {
        let melhorBytes  = null;
        let melhorLabel  = '';

        for (let i = 0; i < QUALITY_LEVELS.length; i++) {
            const { dpi, quality, label } = QUALITY_LEVELS[i];
            const pctStart = 10 + i * 14;
            const pctEnd   = pctStart + 13;

            _setStatus(`Tentando: ${label}`, `Nível ${i + 1}/${QUALITY_LEVELS.length}`, pctStart);

            const result = await _rasterizar(originalBytes, dpi, quality, pctStart, pctEnd);
            _log(`${label}: ${(result.length / 1024 / 1024).toFixed(2)} MB`);

            // Sempre guarda o mais recente (que é o menor, pois níveis pioram progressivamente)
            melhorBytes = result;
            melhorLabel = label;

            if (result.length <= MAX_BYTES) break;  // já cabe — para aqui
        }

        return { bytes: melhorBytes, label: melhorLabel };
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

        _setStatus(`Dividindo em partes (${totalPages} págs.)...`, '', 92);

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
                92 + Math.round(((pageIdx + melhorCount) / totalPages) * 7)
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
                _setStatus(`Ainda ${compressedMB.toFixed(2)} MB após compressão. Dividindo...`, '', 91);
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
    _log('Módulo carregado (v2.0.0) — compressão via canvas+JPEG.');
})();
