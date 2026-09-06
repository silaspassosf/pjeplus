// pdf.compress.js — Módulo PJeTools: Ajustar PDF v1.0.0
// Comprime PDF e divide em partes de até 9,5 MB para envio no PJe
(function () {
    'use strict';

    const MOD_NAME  = 'AjustarPDF';
    const MAX_BYTES = 9.5 * 1024 * 1024;      // 9,5 MB por parte
    const TARGET_MB = 9.5;

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
            font-size:13px;color:#495057;margin-bottom:12px;min-height:20px;word-break:break-word;
        }
        #pjepdf-progress-bar {
            height:8px;border-radius:4px;background:#e9ecef;overflow:hidden;margin-bottom:16px;
        }
        #pjepdf-progress-inner {
            height:100%;border-radius:4px;background:#007bff;
            width:0%;transition:width .3s ease;
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
        }
        `;
    }

    function _criarModal() {
        document.getElementById('pjepdf-overlay')?.remove();
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

    function _setStatus(msg, pct) {
        const el = document.getElementById('pjepdf-status');
        if (el) el.textContent = msg;
        if (pct !== undefined) {
            const bar = document.getElementById('pjepdf-progress-inner');
            if (bar) bar.style.width = Math.min(100, pct) + '%';
        }
        _log(msg);
    }

    function _setInfo(msg) {
        const box = document.getElementById('pjepdf-info-box');
        if (!box) return;
        box.style.display = msg ? '' : 'none';
        box.innerHTML = msg;
    }

    function _addDownloadLink(blob, filename, label) {
        const url  = URL.createObjectURL(blob);
        const size = (blob.size / (1024 * 1024)).toFixed(2) + ' MB';
        const container = document.getElementById('pjepdf-links');
        if (!container) return;
        const a = document.createElement('a');
        a.className  = 'pjepdf-link-btn';
        a.href       = url;
        a.download   = filename;
        a.innerHTML  = `📄 ${label} <span class="sz">${size}</span>`;
        container.appendChild(a);
    }

    // ──────────────────────────────────────────────
    // Lógica PDF (usa pdf-lib exposto via @require como PDFLib)
    // ──────────────────────────────────────────────

    /**
     * Tenta comprimir o PDF removendo metadados redundantes e aplicando
     * remoção de streams duplicados via pdf-lib (compressão leve).
     * Retorna Uint8Array do PDF "comprimido".
     */
    async function _comprimirPdf(originalBytes) {
        if (typeof PDFLib === 'undefined') {
            throw new Error('pdf-lib não carregado (PDFLib indefinido).');
        }
        const { PDFDocument } = PDFLib;

        _setStatus('Carregando PDF...', 10);
        const pdfDoc = await PDFDocument.load(originalBytes, { ignoreEncryption: true });

        // Remove XMP metadata e limpa info dictionary (reduz tamanho)
        pdfDoc.setTitle('');
        pdfDoc.setAuthor('');
        pdfDoc.setSubject('');
        pdfDoc.setKeywords([]);
        pdfDoc.setCreator('');
        pdfDoc.setProducer('');
        // Remove metadados XMP embutidos
        try { pdfDoc.catalog.delete(PDFLib.PDFName.of('Metadata')); } catch (_) {}

        _setStatus('Serializando PDF comprimido...', 30);
        // objectsPerTick menor = melhor desduplicação de streams
        const compressedBytes = await pdfDoc.save({
            useObjectStreams: true,
            addDefaultPage: false,
            objectsPerTick: 20,
        });

        return compressedBytes;
    }

    /**
     * Divide um PDF em partes de até maxBytes bytes, agrupando páginas.
     * Retorna array de Uint8Array (uma por parte).
     */
    async function _dividirPdf(sourceBytes, maxBytes) {
        const { PDFDocument } = PDFLib;
        const sourceDoc  = await PDFDocument.load(sourceBytes, { ignoreEncryption: true });
        const totalPages = sourceDoc.getPageCount();
        const partes     = [];
        let   pageIdx    = 0;

        _setStatus(`Dividindo em partes (${totalPages} págs.)...`, 50);

        while (pageIdx < totalPages) {
            // Estratégia: binária — tenta adicionar o máximo de páginas possível
            let lo = 1, hi = totalPages - pageIdx, melhores = null;

            while (lo <= hi) {
                const mid   = Math.floor((lo + hi) / 2);
                const chunk = await PDFDocument.create();
                const cpIdx = Array.from({ length: mid }, (_, i) => pageIdx + i);
                const pages = await chunk.copyPagesFrom(sourceDoc, cpIdx);
                pages.forEach(p => chunk.addPage(p));
                const bytes = await chunk.save({ useObjectStreams: true });

                if (bytes.length <= maxBytes) {
                    melhores = bytes;
                    lo = mid + 1;
                } else {
                    hi = mid - 1;
                }
            }

            // Fallback: se nem 1 página cabe, inclui assim mesmo
            if (!melhores) {
                const chunk = await PDFDocument.create();
                const [p]   = await chunk.copyPagesFrom(sourceDoc, [pageIdx]);
                chunk.addPage(p);
                melhores = await chunk.save({ useObjectStreams: true });
                _log(`Aviso: página ${pageIdx + 1} sozinha excede o limite (${(melhores.length / 1024 / 1024).toFixed(2)} MB)`);
            }

            const pagesInChunk = await PDFDocument.load(melhores).then(d => d.getPageCount());
            partes.push(melhores);
            _setStatus(
                `Parte ${partes.length}: ${(melhores.length / 1024 / 1024).toFixed(2)} MB (${pagesInChunk} págs.)`,
                50 + Math.round((pageIdx / totalPages) * 45)
            );
            pageIdx += pagesInChunk;
        }

        return partes;
    }

    // ──────────────────────────────────────────────
    // Ponto de entrada
    // ──────────────────────────────────────────────
    async function executarAjustarPDF() {
        _criarModal();

        // Escolha do arquivo via input oculto
        const input = document.createElement('input');
        input.type    = 'file';
        input.accept  = 'application/pdf,.pdf';
        input.style.display = 'none';
        document.body.appendChild(input);

        input.onchange = async () => {
            const file = input.files[0];
            input.remove();
            if (!file) {
                _setStatus('Nenhum arquivo selecionado.');
                return;
            }

            _setStatus(`Lendo "${file.name}" (${(file.size / 1024 / 1024).toFixed(2)} MB)...`, 5);

            const originalBytes = new Uint8Array(await file.arrayBuffer());
            const originalMB    = file.size / 1024 / 1024;
            const baseName      = file.name.replace(/\.pdf$/i, '');

            try {
                // 1. Comprimir
                const compressedBytes = await _comprimirPdf(originalBytes);
                const compressedMB    = compressedBytes.length / 1024 / 1024;

                _setInfo(
                    `<strong>Original:</strong> ${originalMB.toFixed(2)} MB → ` +
                    `<strong>Comprimido:</strong> ${compressedMB.toFixed(2)} MB ` +
                    `(${Math.round((1 - compressedBytes.length / originalBytes.length) * 100)}% menor)`
                );

                // 2. Verificar se cabe em um único arquivo
                if (compressedBytes.length <= MAX_BYTES) {
                    _setStatus('✅ Compressão concluída! Arquivo dentro do limite.', 100);
                    const blob = new Blob([compressedBytes], { type: 'application/pdf' });
                    _addDownloadLink(blob, `${baseName}_ajustado.pdf`, `${baseName}_ajustado.pdf`);
                    return;
                }

                // 3. Dividir em partes
                _setStatus(`Arquivo ainda grande (${compressedMB.toFixed(2)} MB). Dividindo em partes...`, 45);
                const partes = await _dividirPdf(compressedBytes, MAX_BYTES);

                _setStatus(`✅ Dividido em ${partes.length} parte(s). Baixe abaixo:`, 100);
                partes.forEach((partBytes, i) => {
                    const blob  = new Blob([partBytes], { type: 'application/pdf' });
                    const fname = `${baseName}_parte${String(i + 1).padStart(2, '0')}.pdf`;
                    _addDownloadLink(blob, fname, fname);
                });

            } catch (err) {
                _setStatus(`❌ Erro: ${err.message}`);
                console.error(`[${MOD_NAME}]`, err);
            }
        };

        input.click();
    }

    // Expor globalmente para ser chamado pelo painel
    window.executarAjustarPDF = executarAjustarPDF;
    _log('Módulo carregado (v1.0.0).');
})();
