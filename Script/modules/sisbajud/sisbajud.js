'use strict';

// ── Injeção autônoma no SISBAJUD ─────────────────────────────────
if (window.location.href.includes('sisbajud.cnj.jus.br')) {

    // ── Acumulador SISBAJUD ─────────────────────────────────────────
    window._sisbAccum = { executados: {}, protocolos: [] };
    window._sisbTimerId = null;
    window.SISB_TIMEOUT = 15000;

    window._resetSisbAccum = function () {
        _sisbAccum = { executados: {}, protocolos: [] };
        _sisbTimerId = null;
    }

    window._acumularDados = function (executados, protocolo) {
        Object.assign(_sisbAccum.executados, executados);
        if (!_sisbAccum.protocolos.includes(protocolo))
            _sisbAccum.protocolos.push(protocolo);
        if (_sisbTimerId) clearTimeout(_sisbTimerId);
        _sisbTimerId = setTimeout(_resetSisbAccum, SISB_TIMEOUT);
    }

    // Registra o timer no CleanupRegistry
    if (window.PJeState && window.PJeState.registry) {
        window.PJeState.registry.add(() => {
            if (_sisbTimerId) clearTimeout(_sisbTimerId);
            _resetSisbAccum();
        });
    }

    async function extrairRelatorioSISB() {
        for (let t = 0; t < 25; t++) {
            const modal = document.querySelector('.cdk-overlay-container .mat-dialog-container');
            if (!modal) { await sleep(600); continue; }
            const txt = modal.innerText || modal.textContent || '';
            if (!txt.includes('protocolo') && !txt.includes('Protocolo')) {
                await sleep(600); continue;
            }
            const matchProto = modal.innerHTML.match(/Número do protocolo:\s*(\d+)/i);
            const protocolo = matchProto ? matchProto[1] : 'N/A';

            const executados = {};
            const padrao = /(\d+):\s*(.+?)\s+R\$\s*([\d.,]+)/g;
            let m;
            while ((m = padrao.exec(modal.innerHTML)) !== null) {
                executados[m[2].trim()] = m[3].trim();
            }
            _acumularDados(executados, protocolo);
            return { protocolo, executados };
        }
        return null;
    }

    window._formatValorSISB = function (v) {
        const n = parseFloat(v.replace(/[^\d,]/g, '').replace(',', '.'));
        return Number.isFinite(n)
            ? n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
            : v;
    }

    window._gerarRelatorioHTML = function () {
        const pS = 'style="margin:0;padding:0;text-indent:4.5cm;line-height:1.5;"';
        let html = `<p ${pS}><strong>BLOQUEIOS TRANSFERIDOS - SISBAJUD</strong></p>`;
        Object.entries(_sisbAccum.executados).forEach(([nome, valor]) => {
            const lbl = _sisbAccum.protocolos.length > 1 ? 'Protocolos' : 'Protocolo';
            html += `<p ${pS}>- ${nome}: Ordens com bloqueios transferidos` +
                ` [${lbl}: ${_sisbAccum.protocolos.join(', ')}]` +
                ` - Total: ${_formatValorSISB(valor)}</p>`;
        });
        return html;
    }

    window._copiarHTMLFormatado = function () {
        const html = _gerarRelatorioHTML();
        const div = document.createElement('div');
        div.innerHTML = html;
        document.body.appendChild(div);
        try {
            const sel = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(div);
            sel.removeAllRanges(); sel.addRange(range);
            document.execCommand('copy');
            sel.removeAllRanges();
        } finally {
            document.body.removeChild(div);
        }
    }

    async function extrairRelatorioEAlertar() {
        const btn = document.getElementById('pjetools-btn-sisb');
        btn.textContent = '⏳ Extraindo...';
        btn.style.background = '#e6a8d7';
        btn.disabled = true;

        try {
            const resultado = await extrairRelatorioSISB();
            if (resultado) {
                await sleep(300);
                _copiarHTMLFormatado();
                alert(`✅ Relatório copiado!\n\nProtocolo: ${resultado.protocolo}\n` +
                    `Executados: ${Object.keys(_sisbAccum.executados).length}`);
            } else {
                alert('⚠ Nenhum modal de detalhamento do SISBAJUD foi encontrado aberto na tela.');
            }
        } catch (e) {
            alert(`❌ Erro: ${e.message}`);
        } finally {
            btn.textContent = '🏦 Extrair SISBAJUD';
            btn.style.background = '#6f42c1';
            btn.disabled = false;
        }
    }

    function injetarBotaoSisb() {
        if (document.getElementById('pjetools-btn-sisb')) return;
        const btn = document.createElement('button');
        btn.id = 'pjetools-btn-sisb';
        btn.textContent = '🏦 Extrair SISBAJUD';
        btn.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:999999;` +
            `background:#6f42c1;color:#fff;border:none;border-radius:4px;` +
            `padding:12px 20px;font-weight:bold;font-size:14px;cursor:pointer;` +
            `box-shadow:0 4px 12px rgba(0,0,0,.3);transition:transform 0.2s;`;

        btn.onmouseover = () => btn.style.transform = 'scale(1.05)';
        btn.onmouseout = () => btn.style.transform = 'scale(1)';
        btn.onclick = extrairRelatorioEAlertar;
        document.body.appendChild(btn);
    }

    // Tentar injetar algumas vezes pois as páginas podem ser lentas
    setTimeout(injetarBotaoSisb, 2000);
    setTimeout(injetarBotaoSisb, 5000);
}
