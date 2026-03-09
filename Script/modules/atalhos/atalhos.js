'use strict';

window.CHANNEL_NAME = 'maispje_expediente_worker';

// ─── DETECÇÃO DE MODO ────────────────────────────────────────────
const isWorkerTab = /\/comunicacoesprocessuais\/minutas/.test(window.location.href)
    && new URLSearchParams(window.location.search).get('maispje_worker') === '1';

const isMainTab = /\/detalhe/.test(window.location.href);

// ─── INICIALIZAÇÃO ───────────────────────────────────────────────
window.initAtalhos = function () {
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
}

function initMain() {
    const reg = PJeState.atalhos.registry;

    // Garante channel único (fechar anterior se existir)
    if (PJeState.atalhos.channel) {
        try { PJeState.atalhos.channel.close(); } catch (e) { }
    }
    const channel = new BroadcastChannel(CHANNEL_NAME);
    PJeState.atalhos.channel = channel;
    reg.channel(channel);

    // Escutar resposta do worker
    reg.on(channel, 'message', async event => {
        if (event.data?.type === 'WORKER_DONE') {
            console.log('[MAIN] Worker concluiu. Limpeza + hover...');
            showToast('F7: Expediente concluído. Limpando...', '#ff9800');
            await runCleanup();
            showToast('F7: Movimentar -> ag pz-', '#673ab7');
            await hoverAndClickTarget('#maisPJe_bt_detalhes_movimentar', 'ag pz-');
        }
        if (event.data?.type === 'WORKER_ERROR') {
            showToast(`F7 Worker erro: ${event.data.message}`, '#f44336');
        }
    });

    // Teclas F6 / F7
    reg.on(document, 'keydown', async e => {
        if (e.key === 'F6') {
            e.preventDefault();
            showToast('F6: Iniciando limpeza...', '#ff9800');
            await runCleanup();
        } else if (e.key === 'F7') {
            e.preventDefault();
            showToast('F7: Abrindo aba de expediente...', '#673ab7');
            await runExpedienteFlow();
        } else if (e.key === 'F8') {
            e.preventDefault();
            const allowedF8 = /https:\/\/pje\.trt2\.jus\.br\/pjekz\/gigs\/relatorios\/atividades/.test(window.location.href);
            if (!allowedF8) {
                showToast('F8: atalho disponível apenas em Gigs → Relatórios → Atividades.', '#f44336');
                return;
            }
            showToast('F8: Iniciando arquivamento (ler tabela)...', '#607d8b');
            try {
                const tabela = await lerTabelaTxt();
                if (!tabela || tabela.length === 0) {
                    showToast('F8: tabela.txt vazia ou não encontrada.', '#f44336');
                    return;
                }
                const processoId = tabela[0];
                showToast(`F8: Processando ${processoId}`, '#607d8b');
                await performArquivamentoFlow(processoId);
            } catch (err) {
                console.error('[F8] Erro:', err);
                showToast(`F8 erro: ${err.message || err}`, '#f44336');
            }
        }
    });
}

// ─── ATALHO F8 / ARQUIVAMENTO ───────────────────────────────────
async function lerTabelaTxt() {
    const candidates = [
        `${location.origin}/tabela.txt`,
        `${location.pathname.replace(/\/.*/, '')}/tabela.txt`,
        './tabela.txt',
        '/tabela.txt'
    ];
    for (const url of candidates) {
        try {
            const res = await fetch(url, { cache: 'no-store' });
            if (!res.ok) continue;
            const text = await res.text();
            const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
            if (lines.length) return lines;
        } catch (e) { /* tentar próximo */ }
    }
    // fallback: tentar ler de um elemento na página (se existir)
    const el = document.getElementById('tabela-txt-content');
    if (el) return el.textContent.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    return [];
}

function esperarElementoInWindow(win, selector, timeout = 5000) {
    return new Promise((resolve) => {
        const start = Date.now();
        const iv = setInterval(() => {
            try {
                if (!win || win.closed) { clearInterval(iv); resolve(null); return; }
                const el = win.document.querySelector(selector);
                if (el && el.offsetParent !== null) { clearInterval(iv); resolve(el); return; }
            } catch (e) {
                // cross-origin or not ready
            }
            if (Date.now() - start > timeout) { clearInterval(iv); resolve(null); }
        }, 200);
    });
}

async function performArquivamentoFlow(processoId) {
    // localizar linha com processoId
    const row = Array.from(document.querySelectorAll('tr')).find(r => r.textContent.includes(processoId));
    if (!row) { showToast('Linha do processo não encontrada na página.', '#f44336'); return; }

    // tentar encontrar botão 'Escolher' na coluna tarefa
    let escolherBtn = row.querySelector('button[title*="Escolher"], button[mattooltip*="Escolher"], a[title*="Escolher"], .escolher-tipo');
    if (!escolherBtn) {
        // procurar qualquer botão/anchor na mesma linha com texto 'Escolher' ou 'Tipo'
        escolherBtn = Array.from(row.querySelectorAll('button, a, span')).find(el => {
            const t = (el.textContent || '').trim().toLowerCase();
            return t === 'escolher' || t.includes('escolher') || t.includes('tipo');
        });
    }
    if (!escolherBtn) { showToast('Botão de escolher tipo não encontrado na linha.', '#f44336'); return; }

    // se for anchor com href, abrir via window.open para ter controle
    let newWin = null;
    const href = escolherBtn.href || escolherBtn.getAttribute('data-href') || escolherBtn.getAttribute('href');
    if (href) {
        newWin = window.open(href, '_blank');
    } else {
        // dispatch click e tentar capturar última janela aberta
        const before = Array.from(window.open ? [] : []);
        escolherBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        // tentativa: procurar janela recentemente aberta (same-origin behavior may allow)
        // esperar e try to get a handle via window.open with current target if a link exists inside
        await sleep(300);
        // fallback: se a clicar não retornou, tentar encontrar link dentro do row
        const link = row.querySelector('a[target="_blank"], a');
        if (link && link.href) newWin = window.open(link.href, '_blank');
    }

    if (!newWin) { showToast('Não foi possível abrir nova aba (controle). Tente abrir manualmente.', '#f44336'); return; }

    // aguardar carga (mesmo-origin)
    for (let i = 0; i < 40; i++) {
        try {
            if (newWin.document && (newWin.document.readyState === 'complete' || newWin.document.readyState === 'interactive')) break;
        } catch (e) { /* cross-origin */ }
        await sleep(200);
    }

    // foco na nova aba
    try { newWin.focus(); } catch (e) { }

    // clicar ícone de arquivo
    const icone = await esperarElementoInWindow(newWin, 'i.fas.fa-archive.icone-app', 8000);
    if (!icone) { showToast('Ícone de arquivar não encontrado na aba.', '#f44336'); return; }
    try {
        icone.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    } catch (e) { icone.click(); }
    await sleep(1000);

    // clicar no botão 'Assinar'
    const btnAssinar = await esperarElementoInWindow(newWin, 'button span.mat-button-wrapper', 8000);
    let assinarBtn = null;
    if (btnAssinar) {
        assinarBtn = Array.from(newWin.document.querySelectorAll('button')).find(b => b.textContent.trim().toLowerCase().includes('assinar'));
    }
    if (!assinarBtn) {
        showToast('Botão Assinar não encontrado na aba.', '#f44336');
        return;
    }
    try { assinarBtn.click(); } catch (e) { assinarBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); }
    showToast('F8: Arquivamento iniciado e Assinar clicado.', '#4caf50');
}

// ─── MODO WORKER ─────────────────────────────────────────────────
async function runWorker() {
    const channel = new BroadcastChannel(CHANNEL_NAME);

    try {
        // ── ETAPA 1: SALVAR ──────────────────────────────────────
        showToast('Worker: Buscando botão Salvar...', '#2196f3');
        console.log('[WORKER] Buscando btnSalvarExpedientes...');

        const btnSalvar = await esperarBotaoPorAttrName('btnSalvarExpedientes', 15000);
        if (!btnSalvar) {
            console.warn('[WORKER] Botão Salvar não encontrado. Botões na página:');
            document.querySelectorAll('button').forEach(b =>
                console.warn(`  → name="${b.getAttribute('name')}" attr.name="${b.getAttribute('attr.name')}" texto="${b.textContent.trim().substring(0, 60)}"`)
            );
            notificarErro(channel, 'Timeout — botão Salvar não apareceu');
            return;
        }

        console.log('[WORKER] ✅ Salvar encontrado:', btnSalvar.outerHTML.substring(0, 120));

        if (btnSalvar.disabled) {
            console.warn('[WORKER] Salvar está disabled. Aguardando habilitar...');
            const ativo = await esperarBotaoHabilitado('btnSalvarExpedientes', 5000);
            if (!ativo) { notificarErro(channel, 'Botão Salvar permaneceu desabilitado'); return; }
        }

        showToast('Worker: Salvando...', '#2196f3');
        btnSalvar.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        console.log('[WORKER] Click Salvar disparado.');

        await sleep(2000);

        // ── ETAPA 2: ASSINAR ─────────────────────────────────────
        showToast('Worker: Buscando botão Assinar...', '#2196f3');
        console.log('[WORKER] Buscando btnFinalizarExpedientes...');

        const btnAssinar = await esperarBotaoPorAttrName('btnFinalizarExpedientes', 15000);
        if (!btnAssinar) {
            console.warn('[WORKER] Botão Assinar não encontrado. Botões na página:');
            document.querySelectorAll('button').forEach(b =>
                console.warn(`  → name="${b.getAttribute('name')}" attr.name="${b.getAttribute('attr.name')}" texto="${b.textContent.trim().substring(0, 60)}"`)
            );
            notificarErro(channel, 'Timeout — botão Assinar não apareceu');
            return;
        }

        console.log('[WORKER] ✅ Assinar encontrado:', btnAssinar.outerHTML.substring(0, 120));
        showToast('Worker: Assinando...', '#2196f3');
        btnAssinar.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        console.log('[WORKER] Click Assinar disparado.');

        await sleep(3000);

        // ── ETAPA 3: NOTIFICAR E FECHAR ──────────────────────────
        console.log('[WORKER] ✅ Concluído. Notificando aba principal...');
        showToast('Worker: Concluído! Fechando...', '#4caf50');
        channel.postMessage({ type: 'WORKER_DONE' });

        await sleep(400);
        window.close();

    } catch (err) {
        console.error('[WORKER] Erro inesperado:', err);
        notificarErro(channel, err.message || 'Erro desconhecido');
    }
}

function notificarErro(channel, message) {
    showToast(`Worker erro: ${message}`, '#f44336');
    channel.postMessage({ type: 'WORKER_ERROR', message });
}

// ─── HELPERS DE BOTÃO ────────────────────────────────────────────
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
            if (attrNameValue === 'btnSalvarExpedientes' && txt === 'salvar') return b;
            if (attrNameValue === 'btnFinalizarExpedientes' && txt.includes('assinar')) return b;
        }
    }
    return null;
}

// ─── FUNÇÕES AUXILIARES ──────────────────────────────────────────
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

function esperarElemento(selector, timeout = 3000) {
    return new Promise((resolve) => {
        const start = Date.now();
        const interval = setInterval(() => {
            const el = document.querySelector(selector);
            if (el && el.offsetParent !== null) { clearInterval(interval); resolve(el); }
            if (Date.now() - start > timeout) { clearInterval(interval); resolve(null); }
        }, 100);
    });
}

// ─── GIGS CLEANUP ────────────────────────────────────────────────
async function limparResponsavel(row) {
    const inputResp = row.querySelector('input[mattooltip="Inserir/Alterar responsável"]');
    if (!inputResp) return;

    const val = (inputResp.value || '').toLowerCase();
    const aria = (inputResp.getAttribute('aria-label') || '').toLowerCase();

    if (val.includes('silas passos') || aria.includes('silas passos')) {
        inputResp.click();
        await sleep(300);

        inputResp.value = '';
        inputResp.dispatchEvent(new Event('input', { bubbles: true }));
        inputResp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Backspace', bubbles: true }));
        await sleep(300);

        for (const opt of document.querySelectorAll('mat-option')) {
            if (opt.textContent.includes('SEM RESPONSÁVEL')) {
                opt.click();
                await sleep(400);
                break;
            }
        }
    }
}

async function runCleanup() {
    const runner = new AsyncRunner();
    await runner.run(async (signal) => {
        let removed = 0;
        let hasMore = true;
        while (hasMore && !signal.aborted) {
            hasMore = false;
            for (const row of document.querySelectorAll('pje-gigs-atividades table tbody tr')) {
                if (signal.aborted) break;
                if (row.style.display === 'none') continue;
                const desc = row.querySelector('td .descricao')?.textContent.trim();
                if (!desc) continue;
                const prazo = row.querySelector('pje-gigs-alerta-prazo .prazo');
                if (!prazo) continue;
                if (prazo.querySelector('i.fa-clock.far.success')) continue;
                const isVencida = prazo.querySelector('i.danger.fa-clock.far');
                const isSemPrazo = prazo.querySelector('i.fa.fa-pen.atividade-sem-prazo');
                const hasXsOrSilas = desc.toLowerCase().includes('xs') || desc.toLowerCase().includes('silas');
                const hasDomE = desc.includes('Dom.E');
                if (!((isVencida && hasXsOrSilas) || (isSemPrazo && (hasXsOrSilas || hasDomE)))) continue;
                const btnExcluir = row.querySelector('button[mattooltip="Excluir Atividade"]');
                if (!btnExcluir) continue;

                await limparResponsavel(row);

                btnExcluir.click(); await sleep(800);
                let btnSim = null;
                for (let b of document.querySelectorAll('button[color="primary"]')) {
                    if (b.querySelector('span.mat-button-wrapper')?.textContent.trim() === 'Sim') {
                        btnSim = b; break;
                    }
                }
                if (!btnSim) {
                    for (let b of document.querySelectorAll('button')) {
                        if (b.textContent.includes('Sim')) { btnSim = b; break; }
                    }
                }
                if (btnSim) { btnSim.click(); removed++; await sleep(1000); hasMore = true; break; }
            }
        }
        if (removed > 0) {
            playSound();
            showToast(`Limpeza: ${removed} removidos!`, '#4caf50');
        } else {
            showToast('Nenhuma atividade para limpar.', '#2196f3');
        }
    });
}

// ─── EXPEDIENTE FLOW ─────────────────────────────────────────────
async function runExpedienteFlow() {
    const match = window.location.href.match(/\/processo\/([^/]+)\/detalhe/);
    if (!match) {
        showToast('F7: Não foi possível extrair ID do processo!', '#f44336');
        return;
    }
    const processId = match[1];
    const workerUrl = `https://pje.trt2.jus.br/pjekz/processo/${processId}/comunicacoesprocessuais/minutas?maispje_worker=1`;
    console.log(`[F7] Abrindo aba worker: ${workerUrl}`);
    window.open(workerUrl, '_blank');
    showToast('F7: Aba aberta. Aguardando worker...', '#2196f3');
}

async function hoverAndClickTarget(menuSelector, buttonLabel) {
    const triggerEl = document.querySelector(menuSelector);
    if (!triggerEl) {
        showToast(`Menu não encontrado! (${menuSelector})`, '#f44336');
        return;
    }
    const opts = { bubbles: true, cancelable: true, view: window };
    triggerEl.dispatchEvent(new MouseEvent('mouseover', opts));
    triggerEl.dispatchEvent(new MouseEvent('mouseenter', opts));
    triggerEl.dispatchEvent(new MouseEvent('mousemove', opts));
    const container = await esperarElemento('maispjecontaineraa', 3000);
    if (!container) {
        showToast('Timeout: Menu MaisPJe não abriu!', '#f44336');
        return;
    }
    await sleep(250);
    const labelLower = buttonLabel.toLowerCase();
    const alvo = Array.from(container.querySelectorAll('button, div, span, a')).find(el => {
        const name = (el.getAttribute('name') || '').toLowerCase();
        const texto = (el.textContent || '').toLowerCase();
        return texto.trim() === labelLower || name === labelLower || texto.includes(labelLower);
    });
    if (alvo) {
        alvo.style.border = '2px solid red';
        alvo.style.boxShadow = '0 0 10px red';
        await sleep(150);
        alvo.querySelector('.mat-button-wrapper')?.click();
        alvo.click();
        showToast(`Ação disparada: ${buttonLabel}`, '#4caf50');
    } else {
        showToast(`Botão não encontrado: ${buttonLabel}`, '#f44336');
    }
}

