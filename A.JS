// ==UserScript==
// @name         MaisPJe - Atalhos Avançados (F6, F7...)
// @namespace    http://tampermonkey.net/
// @version      2.8
// @description  Atalhos para funções do sistema incluindo Limpeza GIGS (F6) e atalhos customizados de hover
// @author       Você
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @match        https://pje.trt2.jus.br/pjekz/processo/*/comunicacoesprocessuais/minutas*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    const CHANNEL_NAME = 'maispje_expediente_worker';
    const channel = new BroadcastChannel(CHANNEL_NAME);

    const isWorkerTab = /\/comunicacoesprocessuais\/minutas/.test(window.location.href)
                        && new URLSearchParams(window.location.search).get('maispje_worker') === '1';

    const isMainTab = /\/detalhe/.test(window.location.href);

    if (isWorkerTab) {
        console.log('[WORKER] Flag detectada. Aguardando página carregar...');
        window.addEventListener('load', () => {
            setTimeout(() => {
                console.log('[WORKER] Página carregada. Iniciando fluxo...');
                runWorker();
            }, 2000);
        });
        return;
    }

    if (isMainTab) {
        console.log('[MAISPJE_ATALHOS] Modo principal ativado.');
        initMain();
    }

    // ─── MODO PRINCIPAL ───────────────────────────────────────────────────────────

    function initMain() {
        document.addEventListener('keydown', function (e) {
            if (e.key === 'F6') {
                e.preventDefault();
                showToast('F6: Iniciando limpeza...', '#ff9800');
                runCleanup();
            }
            else if (e.key === 'F7') {
                e.preventDefault();
                showToast('F7: Abrindo aba de expediente...', '#673ab7');
                runExpedienteFlow();
            }
        });

        channel.addEventListener('message', async (event) => {
            if (event.data?.type === 'WORKER_DONE') {
                console.log('[MAIN] Worker concluiu. Limpeza + hover...');
                showToast('F7: Expediente concluído. Limpando...', '#ff9800');
                await runCleanupAsync();
                showToast('F7: Movimentar -> ag pz-', '#673ab7');
                await hoverAndClickTarget('#maisPJe_bt_detalhes_movimentar', 'ag pz-');
            }
            if (event.data?.type === 'WORKER_ERROR') {
                showToast(`F7 Worker erro: ${event.data.message}`, '#f44336');
            }
        });
    }

    async function runExpedienteFlow() {
        const match = window.location.href.match(/\/processo\/([^/]+)\/detalhe/);
        if (!match) {
            showToast('F7: Não foi possível extrair ID do processo!', '#f44336');
            return;
        }
        const processId = match[1];
        // Flag ?maispje_worker=1 garante que só esta abertura ativa o worker
        const workerUrl = `https://pje.trt2.jus.br/pjekz/processo/${processId}/comunicacoesprocessuais/minutas?maispje_worker=1`;
        console.log(`[F7] Abrindo aba worker: ${workerUrl}`);
        window.open(workerUrl, '_blank');
        showToast('F7: Aba aberta. Aguardando worker...', '#2196f3');
    }

    // ─── MODO WORKER ──────────────────────────────────────────────────────────────

    async function runWorker() {
        const wait = (ms) => new Promise(r => setTimeout(r, ms));

        try {
            // ── ETAPA 1: SALVAR ──────────────────────────────────────────────────
            showToast('Worker: Buscando botão Salvar...', '#2196f3');
            console.log('[WORKER] Buscando btnSalvarExpedientes...');

            const btnSalvar = await esperarBotaoPorAttrName('btnSalvarExpedientes', 15000);
            if (!btnSalvar) {
                console.warn('[WORKER] Botão Salvar não encontrado. Botões na página:');
                document.querySelectorAll('button').forEach(b =>
                    console.warn(`  → name="${b.getAttribute('name')}" attr.name="${b.getAttribute('attr.name')}" texto="${b.textContent.trim().substring(0, 60)}"`)
                );
                notificarErro('Timeout — botão Salvar não apareceu');
                return;
            }

            console.log('[WORKER] ✅ Salvar encontrado:', btnSalvar.outerHTML.substring(0, 120));

            if (btnSalvar.disabled) {
                console.warn('[WORKER] Salvar está disabled. Aguardando habilitar...');
                const ativo = await esperarBotaoHabilitado('btnSalvarExpedientes', 5000);
                if (!ativo) { notificarErro('Botão Salvar permaneceu desabilitado'); return; }
            }

            showToast('Worker: Salvando...', '#2196f3');
            btnSalvar.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            console.log('[WORKER] Click Salvar disparado.');

            await wait(2000);

            // ── ETAPA 2: ASSINAR ─────────────────────────────────────────────────
            showToast('Worker: Buscando botão Assinar...', '#2196f3');
            console.log('[WORKER] Buscando btnFinalizarExpedientes...');

            const btnAssinar = await esperarBotaoPorAttrName('btnFinalizarExpedientes', 15000);
            if (!btnAssinar) {
                console.warn('[WORKER] Botão Assinar não encontrado. Botões na página:');
                document.querySelectorAll('button').forEach(b =>
                    console.warn(`  → name="${b.getAttribute('name')}" attr.name="${b.getAttribute('attr.name')}" texto="${b.textContent.trim().substring(0, 60)}"`)
                );
                notificarErro('Timeout — botão Assinar não apareceu');
                return;
            }

            console.log('[WORKER] ✅ Assinar encontrado:', btnAssinar.outerHTML.substring(0, 120));
            showToast('Worker: Assinando...', '#2196f3');
            btnAssinar.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            console.log('[WORKER] Click Assinar disparado.');

            await wait(3000);

            // ── ETAPA 3: NOTIFICAR E FECHAR ──────────────────────────────────────
            console.log('[WORKER] ✅ Concluído. Notificando aba principal...');
            showToast('Worker: Concluído! Fechando...', '#4caf50');
            channel.postMessage({ type: 'WORKER_DONE' });

            await wait(400);
            window.close();

        } catch (err) {
            console.error('[WORKER] Erro inesperado:', err);
            notificarErro(err.message || 'Erro desconhecido');
        }
    }

    function notificarErro(message) {
        showToast(`Worker erro: ${message}`, '#f44336');
        channel.postMessage({ type: 'WORKER_ERROR', message });
    }

    // ─── HELPERS DE BOTÃO ─────────────────────────────────────────────────────────

    function esperarBotaoPorAttrName(attrNameValue, timeout = 15000) {
        return new Promise((resolve) => {
            const start = Date.now();
            const interval = setInterval(() => {
                const btn = encontrarBotaoPorAttrName(attrNameValue);
                if (btn) { clearInterval(interval); resolve(btn); }
                if (Date.now() - start > timeout) { clearInterval(interval); resolve(null); }
            }, 300);
        });
    }

    function esperarBotaoHabilitado(attrNameValue, timeout = 5000) {
        return new Promise((resolve) => {
            const start = Date.now();
            const interval = setInterval(() => {
                const btn = encontrarBotaoPorAttrName(attrNameValue);
                if (btn && !btn.disabled) { clearInterval(interval); resolve(btn); }
                if (Date.now() - start > timeout) { clearInterval(interval); resolve(null); }
            }, 300);
        });
    }

    function encontrarBotaoPorAttrName(attrNameValue) {
        let btn = document.querySelector(`button[name="${attrNameValue}"]`);
        if (btn) return btn;
        for (let b of document.querySelectorAll('button')) {
            if (b.getAttribute('name') === attrNameValue ||
                b.getAttribute('attr.name') === attrNameValue) return b;
            const wrapper = b.querySelector('span.mat-button-wrapper');
            if (wrapper) {
                const txt = wrapper.textContent.trim().toLowerCase();
                if (attrNameValue === 'btnSalvarExpedientes'    && txt === 'salvar')        return b;
                if (attrNameValue === 'btnFinalizarExpedientes' && txt.includes('assinar')) return b;
            }
        }
        return null;
    }

    // ─── FUNÇÕES ORIGINAIS ────────────────────────────────────────────────────────

    function playSound() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sine'; osc.frequency.value = 880;
            gain.gain.setValueAtTime(0.1, ctx.currentTime);
            osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.1);
        } catch (e) { console.error('Audio falhou', e); }
    }

    async function hoverAndClickTarget(menuSelector, buttonLabel) {
        const wait = (ms) => new Promise(r => setTimeout(r, ms));
        const triggerEl = document.querySelector(menuSelector);
        if (!triggerEl) { showToast(`Menu não encontrado! (${menuSelector})`, '#f44336'); return; }
        const opts = { bubbles: true, cancelable: true, view: window };
        triggerEl.dispatchEvent(new MouseEvent('mouseover',  opts));
        triggerEl.dispatchEvent(new MouseEvent('mouseenter', opts));
        triggerEl.dispatchEvent(new MouseEvent('mousemove',  opts));
        const container = await esperarElemento('maispjecontaineraa', 3000);
        if (!container) { showToast('Timeout: Menu MaisPJe não abriu!', '#f44336'); return; }
        await wait(250);
        const labelLower = buttonLabel.toLowerCase();
        const alvo = Array.from(container.querySelectorAll('button, div, span, a')).find(el => {
            const name  = (el.getAttribute('name') || '').toLowerCase();
            const texto = (el.textContent || '').toLowerCase();
            return texto.trim() === labelLower || name === labelLower || texto.includes(labelLower);
        });
        if (alvo) {
            alvo.style.border = '2px solid red'; alvo.style.boxShadow = '0 0 10px red';
            await wait(150);
            alvo.querySelector('.mat-button-wrapper')?.click();
            alvo.click();
            showToast(`Ação disparada: ${buttonLabel}`, '#4caf50');
        } else {
            showToast(`Botão não encontrado: ${buttonLabel}`, '#f44336');
        }
    }

    function esperarElemento(selector, timeout = 3000) {
        return new Promise((resolve) => {
            const start = Date.now();
            const interval = setInterval(() => {
                const el = document.querySelector(selector);
                if (el && el.offsetParent !== null) { clearInterval(interval); resolve(el); }
                if (Date.now() - start > timeout)   { clearInterval(interval); resolve(null); }
            }, 100);
        });
    }

    function showToast(text, color) {
        const t = document.createElement('div');
        t.textContent = text;
        t.style.cssText = `position:fixed;top:15px;right:15px;background:${color};color:#fff;padding:12px;z-index:999999;border-radius:4px;font-weight:bold;box-shadow:0 3px 6px rgba(0,0,0,0.4);font-family:sans-serif;`;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 4000);
    }

    function runCleanupAsync() {
        return new Promise((done) => {
            (async () => {
                let removed = 0;
                const sleep = (ms) => new Promise(r => setTimeout(r, ms));
                let hasMore = true;
                while (hasMore) {
                    hasMore = false;
                    for (let row of document.querySelectorAll('pje-gigs-atividades table tbody tr')) {
                        try {
                            if (row.style.display === 'none') continue;
                            const desc = row.querySelector('td .descricao')?.textContent.trim();
                            if (!desc) continue;
                            const prazo = row.querySelector('pje-gigs-alerta-prazo .prazo');
                            if (!prazo) continue;
                            if (prazo.querySelector('i.fa-clock.far.success')) continue;
                            const isVencida  = prazo.querySelector('i.danger.fa-clock.far');
                            const isSemPrazo = prazo.querySelector('i.fa.fa-pen.atividade-sem-prazo');
                            const hasXsOrSilas = desc.toLowerCase().includes('xs') || desc.toLowerCase().includes('silas');
                            const hasDomE      = desc.includes('Dom.E');
                            if (!((isVencida && hasXsOrSilas) || (isSemPrazo && (hasXsOrSilas || hasDomE)))) continue;
                            const btnExcluir = row.querySelector('button[mattooltip="Excluir Atividade"]');
                            if (!btnExcluir) continue;
                            btnExcluir.click(); await sleep(800);
                            let btnSim = null;
                            for (let b of document.querySelectorAll('button[color="primary"]')) {
                                if (b.querySelector('span.mat-button-wrapper')?.textContent.trim() === 'Sim') { btnSim = b; break; }
                            }
                            if (!btnSim) {
                                for (let b of document.querySelectorAll('button')) {
                                    if (b.textContent.includes('Sim')) { btnSim = b; break; }
                                }
                            }
                            if (btnSim) { btnSim.click(); removed++; await sleep(1000); hasMore = true; break; }
                        } catch (err) { console.error('[CLEANUP]', err); }
                    }
                }
                if (removed > 0) { playSound(); showToast(`Limpeza: ${removed} removidos!`, '#4caf50'); }
                else { showToast('Nenhuma atividade para limpar.', '#2196f3'); }
                done();
            })();
        });
    }

    function runCleanup() { runCleanupAsync(); }

})();
