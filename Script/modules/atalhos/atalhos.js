'use strict';

window.CHANNEL_NAME = 'maispje_expediente_worker';

// ─── DETECÇÃO DE MODO ────────────────────────────────────────────
const isWorkerTab = /\/comunicacoesprocessuais\/minutas/.test(window.location.href)
    && new URLSearchParams(window.location.search).get('maispje_worker') === '1';

const isMainTab = /\/detalhe/.test(window.location.href);

const isPainelGlobal = /\/painel\/global\//.test(window.location.href);

// ─── INICIALIZAÇÃO ───────────────────────────────────────────────
window.initAtalhos = function () {
    if (isWorkerTab) {
        console.log('[WORKER] Flag detectada. Aguardando página carregar...');
        window.addEventListener('load', () => {
            setTimeout(() => {
                console.log('[WORKER] Página carregada. Iniciando fluxo...');
                window.runWorker();
            }, 2000);
        });
        return;
    }

    if (isMainTab) {
        console.log('[MAISPJE_ATALHOS] Modo principal ativado.');
        initMain();
    }

    if (isPainelGlobal) {
        console.log('[MAISPJE_ATALHOS] Painel Global detectado.');
        if (typeof injetarBotaoLivresPainelGlobal === 'function') {
            injetarBotaoLivresPainelGlobal();
        }
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
    // Prefer registry-based binding. Se não existir, usar fallback direto no channel/document.
    if (reg && typeof reg.on === 'function') {
        reg.on(channel, 'message', async event => {
            if (event.data?.type === 'WORKER_DONE') {
                console.log('[MAIN] Worker concluiu. Limpeza + hover...');
                showToast('F7: Expediente concluído. Limpando...', '#ff9800');
                await startCleanupIfNeeded();
                showToast('F7: Movimentar -> ag pz-', '#673ab7');
                await hoverAndClickTarget('#maisPJe_bt_detalhes_movimentar', 'ag pz-');
            }
            if (event.data?.type === 'WORKER_ERROR') {
                showToast(`F7 Worker erro: ${event.data.message}`, '#f44336');
            }
        });
    } else {
        // Fallback direto: some environments (scripts) não expõem o registry
        channel.addEventListener('message', async (event) => {
            const data = event.data || {};
            if (data.type === 'WORKER_DONE') {
                console.log('[MAIN][FALLBACK] Worker concluiu. Limpeza + hover...');
                showToast('F7: Expediente concluído. Limpando...', '#ff9800');
                await startCleanupIfNeeded();
                showToast('F7: Movimentar -> ag pz-', '#673ab7');
                await hoverAndClickTarget('#maisPJe_bt_detalhes_movimentar', 'ag pz-');
            }
            if (data.type === 'WORKER_ERROR') {
                showToast(`F7 Worker erro: ${data.message}`, '#f44336');
            }
        });

        // Fallback para teclas (document) caso registry.on não esteja presente
        document.addEventListener('keydown', async e => {
            if (e.key === 'F6') {
                e.preventDefault();
                showToast('F6: Iniciando limpeza...', '#ff9800');
                await startCleanupIfNeeded();
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
                showToast('F8: Iniciando arquivamento (varrendo tabela da página)...', '#607d8b');
                try {
                    let linhas = buscarLinhasDoTipo();
                    if (!linhas || linhas.length === 0) {
                        showToast('F8: Nenhuma linha com "Escolher/Tipo" encontrada na página.', '#f44336');
                        return;
                    }
                    for (let i = 0; i < linhas.length; i++) {
                        const row = linhas[i];
                        const resumo = (row.textContent || '').trim().split('\n').map(s => s.trim()).filter(Boolean).slice(0,2).join(' | ');
                        showToast(`F8: Processando linha ${i+1}/${linhas.length}: ${resumo}`, '#607d8b');
                        await processRowArquivamento(row);
                        await sleep(800);
                    }
                    showToast('F8: Arquivamento em todas as linhas concluído.', '#4caf50');
                } catch (err) {
                    console.error('[F8] Erro:', err);
                    showToast(`F8 erro: ${err.message || err}`, '#f44336');
                }
            }
        });
    }

    // Teclas F6 / F7
    reg.on(document, 'keydown', async e => {
            if (e.key === 'F6') {
            e.preventDefault();
            showToast('F6: Iniciando limpeza...', '#ff9800');
            await startCleanupIfNeeded();
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
            showToast('F8: Iniciando arquivamento (varrendo tabela da página)...', '#607d8b');
            try {
                // Buscar todas as linhas com a coluna Tarefa que apresentam ação "Escolher"/"Tipo"
                let linhas = buscarLinhasDoTipo();
                if (!linhas || linhas.length === 0) {
                    showToast('F8: Nenhuma linha com "Escolher/Tipo" encontrada na página.', '#f44336');
                    return;
                }

                // Processar sequencialmente cada linha encontrada
                for (let i = 0; i < linhas.length; i++) {
                    const row = linhas[i];
                    const resumo = (row.textContent || '').trim().split('\n').map(s => s.trim()).filter(Boolean).slice(0,2).join(' | ');
                    showToast(`F8: Processando linha ${i+1}/${linhas.length}: ${resumo}`, '#607d8b');
                    await processRowArquivamento(row);
                    await sleep(800);
                }

                showToast('F8: Arquivamento em todas as linhas concluído.', '#4caf50');
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

// Retorna todas as linhas da tabela de atividades cuja coluna de tarefa tem ação 'Escolher' ou 'Tipo'
function buscarLinhasDoTipo() {
    try {
        const rows = Array.from(document.querySelectorAll('pje-gigs-atividades table tbody tr'));
        const out = [];
        for (const row of rows) {
            if (row.style.display === 'none') continue;
            // procurar botão/elemento que represente a ação 'Escolher' ou 'Tipo'
            const escolher = row.querySelector('button[title*="Escolher"], button[mattooltip*="Escolher"], .escolher-tipo, a[title*="Escolher"]');
            if (escolher) out.push(row);
            else {
                // heurística: coluna tarefa contendo texto 'Escolher' ou 'Tipo'
                const txt = (row.textContent || '').toLowerCase();
                if (txt.includes('escolher') || txt.includes('tipo')) out.push(row);
            }
        }
        return out;
    } catch (e) {
        return [];
    }
}

// Executa o fluxo de arquivamento para a linha fornecida: abre, clica arquivar, assina e fecha
async function processRowArquivamento(row) {
    // localizar botão 'Escolher' preferencialmente
    let escolherBtn = row.querySelector('button[title*="Escolher"], button[mattooltip*="Escolher"], .escolher-tipo, a[title*="Escolher"]');
    if (!escolherBtn) {
        escolherBtn = Array.from(row.querySelectorAll('button, a, span')).find(el => {
            const t = (el.textContent || '').trim().toLowerCase();
            return t === 'escolher' || t.includes('escolher') || t.includes('tipo');
        });
    }
    if (!escolherBtn) { showToast('F8: botão Escolher não encontrado na linha.', '#f44336'); return; }

    // abrir nova aba/controlar janela
    let newWin = null;
    const href = escolherBtn.href || escolherBtn.getAttribute('data-href') || escolherBtn.getAttribute('href');
    if (href) {
        newWin = window.open(href, '_blank');
    } else {
        escolherBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        await sleep(300);
        const link = row.querySelector('a[target="_blank"], a');
        if (link && link.href) newWin = window.open(link.href, '_blank');
    }

    if (!newWin) { showToast('F8: Não foi possível abrir nova aba para arquivamento.', '#f44336'); return; }

    // aguardar carregamento (mesmo-origin quando possível)
    for (let i = 0; i < 40; i++) {
        try {
            if (newWin.document && (newWin.document.readyState === 'complete' || newWin.document.readyState === 'interactive')) break;
        } catch (e) { /* cross-origin */ }
        await sleep(200);
    }

    try { newWin.focus(); } catch (e) { }

    // clicar ícone arquivar
    const icone = await esperarElementoInWindow(newWin, 'i.fas.fa-archive.icone-app', 8000);
    if (!icone) { showToast('F8: Ícone de arquivar não encontrado na aba.', '#f44336'); try { newWin.close(); } catch (e) {} return; }
    try { icone.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); } catch (e) { icone.click(); }
    await sleep(1000);

    // clicar Assinar
    const btnAssinar = await esperarElementoInWindow(newWin, 'button span.mat-button-wrapper', 8000);
    let assinarBtn = null;
    if (btnAssinar) {
        assinarBtn = Array.from(newWin.document.querySelectorAll('button')).find(b => b.textContent.trim().toLowerCase().includes('assinar'));
    }
    if (!assinarBtn) { showToast('F8: Botão Assinar não encontrado na aba.', '#f44336'); try { newWin.close(); } catch (e) {} return; }
    try { assinarBtn.click(); } catch (e) { assinarBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); }
    showToast('F8: Arquivamento iniciado e Assinar clicado.', '#4caf50');

    // fechar aba após ação
    await sleep(800);
    try { newWin.close(); } catch (e) { }
}

// ─── LER TABELA DIRETAMENTE DA PÁGINA (GIGS → RELATÓRIOS → ATIVIDADES) ───
async function lerTabelaDaPagina() {
    try {
        const rows = Array.from(document.querySelectorAll('pje-gigs-atividades table tbody tr'));
        const results = [];
        for (const row of rows) {
            if (row.style.display === 'none') continue;
            const text = (row.textContent || '').trim();
            if (!text) continue;
            // Tentar extrair um identificador de processo semelhante às linhas de tabela.txt
            // Procurar por sequência de dígitos e caracteres comuns (.-/)
            const m = text.match(/[0-9\.\-\/]{5,}/);
            if (m && m[0]) {
                results.push(m[0].trim());
            } else {
                // fallback: usar primeira célula textual da linha
                const firstCell = row.querySelector('td');
                if (firstCell && firstCell.textContent.trim()) results.push(firstCell.textContent.trim());
            }
        }
        return results;
    } catch (e) {
        return [];
    }
}

// ─── MODO WORKER ─────────────────────────────────────────────────
window.runWorker = async function () {
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
async function runCleanup() {
    const runner = new AsyncRunner();
    await runner.run(async (signal) => {
        let actionsDone = 0;
        let hasMore = true;

        // Etapa 1: Limpar responsáveis (Silas Passos) sem excluir a linha
        while (hasMore && !signal.aborted) {
            hasMore = false;
            for (const row of document.querySelectorAll('pje-gigs-atividades table tbody tr')) {
                if (signal.aborted) break;
                if (row.style.display === 'none') continue;

                const inputResp = row.querySelector('input[mattooltip="Inserir/Alterar responsável"]');
                if (!inputResp) continue;

                const val = (inputResp.value || '').toLowerCase();
                const aria = (inputResp.getAttribute('aria-label') || '').toLowerCase();

                if (val.includes('silas passos') || aria.includes('silas passos')) {
                    inputResp.click();
                    await sleep(300);

                    inputResp.value = '';
                    inputResp.dispatchEvent(new Event('input', { bubbles: true }));
                    inputResp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Backspace', bubbles: true }));
                    await sleep(400);

                    let responsavelLimpo = false;
                    for (const opt of document.querySelectorAll('mat-option')) {
                        if (opt.textContent.includes('SEM RESPONSÁVEL')) {
                            opt.click();
                            await sleep(500);
                            responsavelLimpo = true;
                            actionsDone++;
                            break;
                        }
                    }

                    if (responsavelLimpo) {
                        hasMore = true;
                        break; // Reinicia o loop pois o DOM pode ter sido atualizado
                    }
                }
            }
        }

        // Etapa 2: Deletar itens próprios (xs, silas, Dom.E) com prazo vencido/sem prazo
        hasMore = true;
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

                btnExcluir.click();
                await sleep(800);

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

                if (btnSim) {
                    btnSim.click();
                    actionsDone++;
                    await sleep(1000);
                    hasMore = true;
                    break; // Reinicia o loop após excluir
                }
            }
        }

        if (actionsDone > 0) {
            playSound();
            showToast(`Limpeza: ${actionsDone} ações concluídas!`, '#4caf50');
        } else {
            showToast('Nenhuma atividade para limpar.', '#2196f3');
        }
    });
}

// Ensure cleanup runs exclusively and callers can await shared promise
function startCleanupIfNeeded() {
    if (!PJeState.atalhos) PJeState.atalhos = {};
    if (PJeState.atalhos._cleanupPromise) return PJeState.atalhos._cleanupPromise;
    PJeState.atalhos._cleanupPromise = (async () => {
        try {
            await runCleanup();
        } finally {
            PJeState.atalhos._cleanupPromise = null;
        }
    })();
    return PJeState.atalhos._cleanupPromise;
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

// Compatibilidade: assinatura antiga (selector do gatilho, label do alvo).
// Agora só delega para o motor genérico — a implementação é uma só.
async function hoverAndClickTarget(menuSelector, buttonLabel) {
    const triggerEl = document.querySelector(menuSelector);
    if (!triggerEl) { showToast(`Menu não encontrado! (${menuSelector})`, '#f44336'); return; }

    // O motor espera um alias de ícone ("movimentar", "concluso"...). Aceita
    // tanto o id completo (#maisPJe_bt_detalhes_movimentar) quanto o sufixo.
    const icone = menuSelector
        .replace(/^#maisPJe_bt_detalhes_/, '')
        .replace(/^#/, '');

    const r = await acionarMaisPJe(icone, buttonLabel);
    if (r && r.ok) showToast(`Ação disparada: ${buttonLabel}`, '#4caf50');
}

// ─── MOTOR GENÉRICO: BOTÕES DA MAIS PJE ─────────────────────────
//
// Aciona qualquer botão da barra "Detalhes" da extensão maisPJe fazendo
// hover no ícone certo e clicando no botão pedido.
//
//   const alvo = await maisPJe.hover('concluso').clicar('parcela');
//
// O hover SEMPRE é um dos botões de #maisPJe_bt_detalhes_base (os "ícones"):
//   concluso, movimentar, guardarDados, gigs, anexarDocumentos, bndt,
//   abrirCalculos, intimacaoEExpediente, Expedientes, Lembretes, pagamento,
//   retificarAutuacao, DomicilioEletronico
//
// `clicar` aceita:
//   - o nome/id/aria-label do próprio ícone ("movimentar", "Pagamento")
//   - o texto de um item do menu que abre no hover ("parcela", "ag pz-")
//
// O casamento segue o mesmo critério da extensão (gigs-plugin.js:4112):
// aria-label exato, id, ou o texto do elemento. Depois cai para "contém",
// que é o que permite achar "parcela" dentro de "Parcelas".

const MAISPJE_BASE = '#maisPJe_bt_detalhes_base';

// showToast vem de core/utils.js; se por algum motivo não estiver lá, cai
// para console — o motor não pode quebrar por causa de aviso.
function _maisPjeAviso(msg, cor) {
    if (typeof showToast === 'function') { showToast(msg, cor); }
    else { console.log('[maisPje]', msg); }
}

// Aliases curtos -> sufixo do id em #maisPJe_bt_detalhes_<sufixo>.
const MAISPJE_ICONES = {
    concluso: 'concluso',
    movimentar: 'movimentar',
    movimento: 'movimentar',
    guardar: 'guardarDados',
    guardarDados: 'guardarDados',
    gigs: 'gigs',
    anexar: 'anexarDocumentos',
    anexarDocumentos: 'anexarDocumentos',
    bndt: 'bndt',
    calculos: 'abrirCalculos',
    abrirCalculos: 'abrirCalculos',
    intimacao: 'intimacaoEExpediente',
    intimacaoEExpediente: 'intimacaoEExpediente',
    expedientes: 'Expedientes',
    lembretes: 'Lembretes',
    pagamento: 'pagamento',
    retificar: 'retificarAutuacao',
    retificarAutuacao: 'retificarAutuacao',
    domicilio: 'DomicilioEletronico',
    DomicilioEletronico: 'DomicilioEletronico'
};

function _maisPjeDispatcher() {
    // Tenta MouseEvent com `view`; se falhar, repete sem `view`; por último
    // tenta .click(). Alguns ambientes rejeitam a construção com view.
    return function (el, type, opts) {
        try { el.dispatchEvent(new MouseEvent(type, opts || {})); return true; }
        catch (e) {
            try {
                const safeOpts = Object.assign({}, opts || {});
                if ('view' in safeOpts) delete safeOpts.view;
                el.dispatchEvent(new MouseEvent(type, safeOpts));
                return true;
            } catch (e2) { try { el.click(); return true; } catch (e3) { } }
        }
        return false;
    };
}

// Resolve o ícone: aceita alias ("concluso"), id completo ou o aria-label.
function _maisPjeIcone(nome) {
    const base = document.querySelector(MAISPJE_BASE);
    if (!base) return null;

    const sufixo = MAISPJE_ICONES[nome] || nome;

    return base.querySelector('#maisPJe_bt_detalhes_' + sufixo)
        || base.querySelector('button[aria-label="' + String(nome).replace(/"/g, '\\"') + '"]')
        // último caso: o ícone cujo aria-label começa pelo nome (sem o " ▼")
        || Array.from(base.querySelectorAll('button[aria-label]')).find(b => {
            const rotulo = (b.getAttribute('aria-label') || '').toLowerCase();
            return rotulo && !rotulo.includes('expandir') && rotulo.includes(String(nome).toLowerCase());
        })
        || null;
}

// Faz o hover em um ícone da barra. Devolve o container do menu que abriu,
// ou null se não abriu (aí o alvo pode ser o próprio ícone).
async function _maisPjeHover(icone) {
    const safeDispatch = _maisPjeDispatcher();
    const opts = { bubbles: true, cancelable: true, view: window };

    // A extensão não limpa o menu do hover anterior: ele fica no DOM com os
    // botões do ícone antigo. Se não removermos, a busca acha o botão do menu
    // velho e o clique sai no lugar errado (foi observado: hover em concluso
    // e o menu do anexar ainda na tela com "Siscon").
    const menuVelho = document.querySelector('maispjecontaineraa');
    if (menuVelho) menuVelho.remove();

    // ORDEM E CONJUNTO IDÊNTICOS AO ORIGINAL (atalhos.js:662-664).
    //
    // A extensão (gigs-plugin.js:4613) faz:
    //     base.onmouseover = ev => { if (ev.target.id) elementoAtivo = ev.target.id }
    // e o botão faz onmouseenter → sleep(500) → if (elementoAtivo == this.id).
    // Ou seja: o mouseover tem de chegar ao base ANTES do mouseenter do
    // botão. Disparar no ícone com bubbles:true sobe até o base levando
    // event.target = ícone (que tem id) — exatamente o que ela espera.
    //
    // Não intercalar esperas: o mouseleave do botão zera elementoAtivo, e
    // qualquer coisa entre o mouseover e o mouseenter pode deixá-lo vazio.
    safeDispatch(icone, 'mouseover',  opts);
    safeDispatch(icone, 'mouseenter', opts);
    safeDispatch(icone, 'mousemove',  opts);

    return await esperarElemento('maispjecontaineraa', 3000);
}

// Espera o ALVO aparecer — não o container.
//
// O container pode já estar na tela de um hover anterior (montado com outro
// conjunto de botões) e NÃO é limpo pela extensão. Esperar só por ele
// devolveria um menu obsoleto, e é por isso que a remoção prévia (em
// _maisPjeHover) existe. Aqui a condição de parada é o próprio botão existir.
async function _maisPjeEsperarAlvo(nome, timeout) {
    const fim = Date.now() + (timeout || 3000);
    while (Date.now() < fim) {
        const container = document.querySelector('maispjecontaineraa');
        if (container) {
            const noMenu = _maisPjeAcharAlvo(nome, container);
            if (noMenu) return { alvo: noMenu, container, origem: 'menu' };
        }
        // Sem menu: pode ser um ícone da própria barra (hover A, clique B).
        // Restrinjo à barra — varrer o documento inteiro encontrava botões
        // de menus antigos e dava falso positivo.
        const naBarra = _maisPjeAcharAlvo(nome, document.querySelector(MAISPJE_BASE) || null);
        if (naBarra) return { alvo: naBarra, container, origem: 'barra' };
        await new Promise(r => setTimeout(r, 100));
    }
    return { alvo: null, container: document.querySelector('maispjecontaineraa') };
}

// Procura o alvo pelo nome dentro do container (ou do documento, se o
// container não abriu). Mesmo critério da extensão, mais o "contém".
//
// IMPORTANTE: devolve sempre o BOTÃO, nunca um filho dele. Os botões da
// extensão são montados como
//     <button id=N name="Siscon"><span class="mat-button-wrapper">Siscon</span></button>
// e o onclick vive no <button>. Se a busca por texto devolvesse o <span>,
// clicar nele não aciona nada — foi o que acontecia com "Siscon".
function _maisPjeAcharAlvo(nome, container) {
    const alvo = String(nome).trim();
    const alvoLower = alvo.toLowerCase();
    const escopo = container || document;

    // Só elementos que podem RECEBER o clique. Sem 'li' nem 'i'.
    const candidatos = Array.from(escopo.querySelectorAll('button, a, div, span'));

    // 1) nome exato: aria-label, name ou id
    const exato = candidatos.find(el => {
        const rotulo = (el.getAttribute('aria-label') || '').toLowerCase();
        const name = (el.getAttribute('name') || '').toLowerCase();
        const id = (el.id || '').toLowerCase();
        return rotulo === alvoLower || name === alvoLower || id.endsWith(alvoLower);
    });
    if (exato) return exato;

    // 2) texto exato (o elemento folha, para não pegar um ancestral)
    const porTexto = candidatos.find(el =>
        (el.textContent || '').trim().toLowerCase() === alvoLower && el.children.length === 0);
    if (porTexto) return porTexto;

    // 3) contém, preferindo o elemento mais interno
    const contem = candidatos.filter(el =>
        (el.textContent || '').toLowerCase().includes(alvoLower));
    if (contem.length) {
        return contem.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length)[0];
    }
    return null;
}

// Sobe do elemento achado até o <button>/<a> que de fato tem o handler.
// O onclick da extensão está no botão; o texto está no span interno.
function _maisPjeBotaoDe(el) {
    if (!el) return null;
    if (el.closest) {
        const bt = el.closest('button, a');
        if (bt) return bt;
    }
    return el;
}

// Clica de fato — mesma sequência do original (atalhos.js:677-678):
//   alvo.querySelector('.mat-button-wrapper')?.click();
//   alvo.click();
function _maisPjeClicar(el) {
    const botao = _maisPjeBotaoDe(el);
    let clicou = false;
    const wrapper = botao.querySelector && botao.querySelector('.mat-button-wrapper');
    if (wrapper) { try { wrapper.click(); clicou = true; } catch (e) { } }
    try { botao.click(); clicou = true; } catch (e) { }
    return clicou;
}

/**
 * Motor genérico dos botões da maisPJe.
 *
 *   await maisPje.hover('concluso').clicar('parcela')
 *   await maisPje.hover('movimentar').clicar('ag pz-')
 *   await maisPje.clicar('Pagamento')          // sem hover explícito
 *
 * Retorna { ok, icone, alvo, container }.
 */
function maisPjeHover(icone, opcoes) {
    const opts = opcoes || {};
    const api = {
        /** Clica em `nome`, que pode estar no menu aberto ou ser o próprio ícone. */
        async clicar(nome) {
            const iconeEl = _maisPjeIcone(icone);
            if (!iconeEl) {
                const msg = `maisPje: ícone "${icone}" não encontrado`;
                if (opts.silencioso !== true) _maisPjeAviso(msg, '#f44336');
                return { ok: false, erro: msg, icone };
            }

            await _maisPjeHover(iconeEl);

            // O menu do Anexar demora ~500ms para montar os botões depois do
            // hover, então esperamos o ALVO, não o container.
            const { alvo, container } = await _maisPjeEsperarAlvo(nome, opts.timeoutAlvo || 4000);

            if (!alvo) {
                const msg = `maisPje: botão "${nome}" não apareceu após hover em "${icone}"`;
                if (opts.silencioso !== true) _maisPjeAviso(msg, '#f44336');
                return { ok: false, erro: msg, icone, container };
            }

            // Destaque visual rápido, para dar para ver por onde passou.
            // Vai no BOTÃO (onde está o handler), não no span interno.
            const botao = _maisPjeBotaoDe(alvo);
            const estiloAnterior = botao.style.cssText;
            botao.style.border = '2px solid red';
            botao.style.boxShadow = '0 0 10px red';
            await new Promise(r => setTimeout(r, 150));

            _maisPjeClicar(alvo);
            botao.style.cssText = estiloAnterior;

            if (opts.silencioso !== true) {
                _maisPjeAviso(`maisPje: ${icone} ➜ ${nome}`, '#4caf50');
            }
            return { ok: true, icone, alvo: botao, container };
        }
    };
    return api;
}

/**
 * Atalho: hover no ícone e clique no alvo.
 *   await acionarMaisPJe('concluso', 'parcela');
 */
async function acionarMaisPJe(icone, alvo, opcoes) {
    return await maisPjeHover(icone, opcoes).clicar(alvo);
}

window.maisPje = {
    hover: maisPjeHover,
    acionar: acionarMaisPJe,
    icones: MAISPJE_ICONES,
    selectorBase: MAISPJE_BASE
};



// ─── PAINEL GLOBAL: SELEÇÃO LIVRES + ATIVIDADE XS1 (FLUXO PRAZO) ──

/**
 * Varre a tabela de processos (tr.cdk-drag) e seleciona os processos livres:
 * - Sem prazo (td:nth-child(9) time vazio ou ausente)
 * - Sem comentário (sem i.fa-comment)
 * - Sem campo de texto preenchido (sem input[matinput] com valor)
 * - Sem lupa de pesquisa na coluna 3 (sem td:nth-child(3) i.fa-search)
 * 
 * Marca visualmente a linha com #ffccd2 e clica no checkbox caso desmarcado.
 * Retorna a quantidade de processos selecionados.
 */
function selecionarProcessosLivres() {
    try {
        const linhas = document.querySelectorAll('tr.cdk-drag');
        let selecionados = 0;

        linhas.forEach(function (linha) {
            const prazo = linha.querySelector('td:nth-child(9) time');
            const prazoVazio = !prazo || !prazo.textContent.trim();
            const hasComment = linha.querySelector('i.fa-comment') !== null;
            const inputField = linha.querySelector('input[matinput]');
            const campoPreenchido = inputField && inputField.value.trim();
            const temLupa = linha.querySelector('td:nth-child(3) i.fa-search') !== null;

            if (prazoVazio && !hasComment && !campoPreenchido && !temLupa) {
                const chkInput = linha.querySelector('mat-checkbox input[type="checkbox"]');
                const matCheckbox = linha.querySelector('mat-checkbox');
                const jaMarcado = (chkInput && chkInput.checked) || (matCheckbox && matCheckbox.classList.contains('mat-checkbox-checked'));

                if (!jaMarcado) {
                    if (chkInput) {
                        chkInput.click();
                    } else if (matCheckbox) {
                        matCheckbox.click();
                    }
                }
                linha.style.backgroundColor = '#ffccd2';
                selecionados++;
            }
        });

        return selecionados;
    } catch (e) {
        console.error('[LIVRES_XS1] Erro ao selecionar processos livres:', e);
        return -1;
    }
}

/**
 * Executa o fluxo completo idêntico ao ciclo de Prazo/loop_orquestrador:
 * 1. Seleciona processos livres
 * 2. Clica no botão tag verde de ações em lote
 * 3. Clica na opção "Atividade" do menu
 * 4. Preenche observação com "xs1"
/**
 * Helper para setar valor nativo em inputs/textareas e disparar eventos Angular
 */
function setNativeInputValue(element, value) {
    if (!element) return;
    const proto = element instanceof HTMLTextAreaElement
        ? window.HTMLTextAreaElement.prototype
        : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
    if (setter) {
        setter.call(element, value);
    } else {
        element.value = value;
    }
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    element.dispatchEvent(new Event('blur', { bubbles: true }));
}

/**
 * Seleciona a opção "Prazo" no mat-autocomplete do campo tipoAtividade
 */
async function selecionarTipoAtividadePrazo(modalContainer, wait) {
    const inputTipo = modalContainer.querySelector('input[formcontrolname="tipoAtividade"]') ||
                      document.querySelector('input[formcontrolname="tipoAtividade"]') ||
                      modalContainer.querySelector('input[data-placeholder*="Tipo de Atividade"]');
    if (!inputTipo) {
        console.warn('[LIVRES_XS1] Campo tipoAtividade não encontrado no modal.');
        return false;
    }

    inputTipo.focus();
    inputTipo.click();
    await wait(200);

    const buscarOpcaoPrazo = () => {
        const options = Array.from(document.querySelectorAll('mat-option, .mat-option, [role="option"]'));
        return options.find(opt => {
            const txt = (opt.textContent || '').trim().toLowerCase();
            return txt === 'prazo' || txt.includes('prazo');
        });
    };

    let optionPrazo = buscarOpcaoPrazo();
    if (!optionPrazo) {
        setNativeInputValue(inputTipo, 'Prazo');
        inputTipo.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
        await wait(300);

        for (let t = 0; t < 25; t++) {
            optionPrazo = buscarOpcaoPrazo();
            if (optionPrazo) break;
            await wait(150);
        }
    }

    if (optionPrazo) {
        if (typeof optionPrazo.scrollIntoView === 'function') {
            optionPrazo.scrollIntoView({ block: 'nearest' });
        }
        optionPrazo.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        optionPrazo.click();
        console.log('[LIVRES_XS1] Opção "Prazo" selecionada no autocomplete.');
        await wait(300);
        return true;
    } else {
        console.warn('[LIVRES_XS1] Opção "Prazo" não encontrada no autocomplete.');
        return false;
    }
}

/**
 * Preenche o campo Dias Úteis (Prazo -1)
 */
async function preencherPrazoDias(modalContainer, valor, wait) {
    const inputDias = modalContainer.querySelector('input[formcontrolname="dias"]') ||
                      modalContainer.querySelector('input[data-placeholder*="Dias Úteis"]') ||
                      modalContainer.querySelector('input[formcontrolname="prazo"]') ||
                      document.querySelector('input[formcontrolname="dias"]');
    if (inputDias) {
        inputDias.focus();
        setNativeInputValue(inputDias, String(valor));
        console.log(`[LIVRES_XS1] Campo dias preenchido com: ${valor}`);
        await wait(200);
        return true;
    }
    console.warn('[LIVRES_XS1] Campo dias/prazo não encontrado.');
    return false;
}

/**
 * Preenche o campo de Observação (ex: "xs1")
 */
async function preencherObservacao(modalContainer, valor, wait) {
    const textareaObs = modalContainer.querySelector('textarea[formcontrolname="observacao"]') ||
                        modalContainer.querySelector('textarea[data-placeholder="Observação"]') ||
                        document.querySelector('textarea[formcontrolname="observacao"]') ||
                        modalContainer.querySelector('textarea');
    if (textareaObs) {
        textareaObs.focus();
        setNativeInputValue(textareaObs, valor);
        console.log(`[LIVRES_XS1] Campo observação preenchido com: ${valor}`);
        await wait(200);
        return true;
    }
    console.warn('[LIVRES_XS1] Campo observação não encontrado.');
    return false;
}

/**
 * Clica no botão Salvar do modal
 */
async function clicarBotaoSalvar(modalContainer, wait) {
    let btnSalvar = modalContainer.querySelector('button[data-cy="salvar"]') ||
                    modalContainer.querySelector('button[color="primary"][type="submit"]');
    if (!btnSalvar) {
        const botoes = Array.from(modalContainer.querySelectorAll('button'));
        btnSalvar = botoes.find(b => {
            const txt = (b.textContent || '').trim().toLowerCase();
            return txt === 'salvar' || txt.includes('salvar');
        });
    }
    if (!btnSalvar) {
        console.error('[LIVRES_XS1] Botão Salvar não encontrado no modal.');
        return false;
    }

    if (btnSalvar.disabled) {
        console.warn('[LIVRES_XS1] Botão Salvar desabilitado, aguardando validação...');
        await wait(500);
    }

    btnSalvar.click();
    console.log('[LIVRES_XS1] Botão Salvar clicado.');
    return true;
}

/**
 * Executa o fluxo completo do botão "Livres (xs1)":
 * 1. Seleciona os processos livres
 * 2. Clica no botão de tag de ações em lote
 * 3. Seleciona "Atividade"
 * 4. Seleciona Tipo de Atividade = "Prazo" via autocomplete
 * 5. Preenche Dias Úteis com -1
 * 6. Preenche Observação com "xs1"
 * 7. Clica em "Salvar"
 */
async function executarLivresXs1() {
    const notify = (msg, cor, dur) => {
        if (typeof showToast === 'function') {
            showToast(msg, cor, dur);
        } else {
            console.log(`[LIVRES_XS1] ${msg}`);
        }
    };
    const wait = (ms) => typeof sleep === 'function' ? sleep(ms) : new Promise(r => setTimeout(r, ms));

    try {
        notify('Buscando processos livres na tabela...', '#2196f3', 2000);
        await wait(300);

        const selecionados = selecionarProcessosLivres();
        console.log(`[LIVRES_XS1] Total de livres selecionados: ${selecionados}`);

        if (selecionados === 0) {
            notify('Nenhum processo livre encontrado na página.', '#ff9800', 4000);
            return;
        }
        if (selecionados < 0) {
            notify('Erro ao inspecionar a tabela de processos.', '#f44336', 4000);
            return;
        }

        notify(`${selecionados} processo(s) selecionado(s). Abrindo atividade...`, '#2196f3', 2500);
        await wait(600);

        // 1. Localizar botão tag verde
        let tagVerde = document.querySelector('i.fa.fa-tag.icone.texto-verde') ||
                       document.querySelector('i.fa-tag.texto-verde') ||
                       document.querySelector('button i.fa-tag')?.closest('button') ||
                       document.querySelector('i.fa-tag');

        if (!tagVerde) {
            const icones = Array.from(document.querySelectorAll('i')).filter(i => i.className && i.className.includes('fa-tag'));
            if (icones.length > 0) tagVerde = icones[0];
        }

        if (!tagVerde) {
            notify('Erro: Botão de Tag (Atividade em lote) não encontrado!', '#f44336', 5000);
            console.error('[LIVRES_XS1] Botão tag verde não encontrado no DOM.');
            return;
        }

        const btnTag = tagVerde.closest('button') || tagVerde;
        btnTag.click();
        console.log('[LIVRES_XS1] Botão tag clicado.');
        await wait(600);

        // 2. Localizar item "Atividade" no menu suspenso
        let btnAtividade = null;
        for (let tent = 0; tent < 20; tent++) {
            const itensMenu = document.querySelectorAll('.mat-menu-panel button, button.mat-menu-item, div[role="menu"] button');
            for (const b of itensMenu) {
                const txt = (b.textContent || '').trim().toLowerCase();
                if (txt.includes('atividade')) {
                    btnAtividade = b;
                    break;
                }
            }
            if (btnAtividade) break;
            await wait(200);
        }

        if (!btnAtividade) {
            notify('Erro: Item "Atividade" não encontrado no menu!', '#f44336', 5000);
            console.error('[LIVRES_XS1] Opção Atividade não localizada no menu.');
            return;
        }

        btnAtividade.click();
        console.log('[LIVRES_XS1] Item Atividade clicado. Aguardando modal...');
        await wait(800);

        // 3. Aguardar modal/formulário de cadastro de atividades
        let modalContainer = null;
        for (let tent = 0; tent < 30; tent++) {
            modalContainer = document.querySelector('pje-gigs-cadastro-atividades') ||
                             document.querySelector('mat-dialog-container form') ||
                             document.querySelector('mat-dialog-container') ||
                             document.querySelector("textarea[formcontrolname='observacao']")?.closest('.mat-dialog-container');
            if (modalContainer && modalContainer.offsetParent !== null) break;
            await wait(200);
        }

        if (!modalContainer) {
            notify('Erro: Formulário de atividade não apareceu!', '#f44336', 5000);
            console.error('[LIVRES_XS1] Modal de atividade não encontrado.');
            return;
        }

        notify('Configurando Tipo de Atividade = "Prazo"...', '#2196f3', 2000);
        // 4. Selecionar tipo de atividade = "Prazo" via autocomplete
        await selecionarTipoAtividadePrazo(modalContainer, wait);

        // 5. Preencher Dias Úteis = -1
        await preencherPrazoDias(modalContainer, -1, wait);

        // 6. Preencher Observação = "xs1"
        await preencherObservacao(modalContainer, 'xs1', wait);

        await wait(300);

        // 7. Clicar no botão Salvar
        const salvou = await clicarBotaoSalvar(modalContainer, wait);
        if (!salvou) {
            notify('Erro: Não foi possível acionar o botão Salvar!', '#f44336', 5000);
            return;
        }

        if (typeof playSound === 'function') {
            try { playSound(); } catch (e) {}
        }
        notify(`✅ ${selecionados} processo(s) livre(s) marcado(s) com atividade xs1 (Prazo: -1)!`, '#4caf50', 6000);

    } catch (err) {
        console.error('[LIVRES_XS1] Erro na execução:', err);
        notify(`Erro ao processar: ${err.message || err}`, '#f44336', 6000);
    }
}

/**
 * Injeta o botão "Livres (xs1)" no Painel Global KZ
 * (ex: https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos)
 */
function injetarBotaoLivresPainelGlobal() {
    const isGlobal = /\/painel\/global\/(?:14|\d+|todos)\/lista-processos/.test(window.location.href) ||
                     window.location.href.includes('/pjekz/painel/global/');
    if (!isGlobal) {
        const btnAntigo = document.getElementById('pjetools-btn-livres-xs1');
        if (btnAntigo) btnAntigo.remove();
        return;
    }

    if (document.getElementById('pjetools-btn-livres-xs1')) return;

    const btn = document.createElement('button');
    btn.id = 'pjetools-btn-livres-xs1';
    btn.type = 'button';
    btn.innerHTML = '<span style="margin-right:6px;font-size:14px;">⚡</span><span>Livres (xs1)</span>';
    btn.title = 'Selecionar processos livres e aplicar atividade xs1 (Fluxo PRAZO)';
    btn.style.cssText = `
        position: fixed;
        top: 65px;
        right: 25px;
        z-index: 99999;
        background: linear-gradient(135deg, #1b5e20, #2e7d32);
        color: #ffffff;
        border: 2px solid #a5d6a7;
        border-radius: 20px;
        padding: 7px 16px;
        font-size: 13px;
        font-weight: bold;
        font-family: Roboto, "Helvetica Neue", sans-serif;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        transition: all 0.2s ease-in-out;
        user-select: none;
        display: flex;
        align-items: center;
    `;

    btn.addEventListener('mouseenter', () => {
        btn.style.transform = 'scale(1.05)';
        btn.style.boxShadow = '0 6px 16px rgba(0,0,0,0.35)';
        btn.style.background = 'linear-gradient(135deg, #2e7d32, #388e3c)';
    });
    btn.addEventListener('mouseleave', () => {
        btn.style.transform = 'scale(1)';
        btn.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
        btn.style.background = 'linear-gradient(135deg, #1b5e20, #2e7d32)';
    });

    btn.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (btn.disabled) return;

        btn.disabled = true;
        const htmlOriginal = btn.innerHTML;
        btn.innerHTML = '<span style="margin-right:6px;">⏳</span><span>Executando...</span>';
        btn.style.opacity = '0.85';

        try {
            await executarLivresXs1();
        } finally {
            btn.innerHTML = htmlOriginal;
            btn.style.opacity = '1';
            btn.disabled = false;
        }
    });

    document.body.appendChild(btn);
    console.log('[ATALHOS] Botão "Livres (xs1)" inserido no Painel Global.');
}

/**
 * Monitora navegação SPA e mutações no DOM para manter o botão presente
 * apenas nas rotas do painel global de processos.
 */
function iniciarMonitorPainelGlobal() {
    if (window.__pjeAtalhosMonitorIniciado) return;
    window.__pjeAtalhosMonitorIniciado = true;

    // Tentativa imediata
    setTimeout(injetarBotaoLivresPainelGlobal, 1000);

    // Observa mutações de rota ou renderização assíncrona do Angular
    const observer = new MutationObserver(() => {
        injetarBotaoLivresPainelGlobal();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Observa navegação SPA via histórico
    window.addEventListener('popstate', () => {
        setTimeout(injetarBotaoLivresPainelGlobal, 500);
    });
    window.addEventListener('hashchange', () => {
        setTimeout(injetarBotaoLivresPainelGlobal, 500);
    });
}

// Inicializa o monitor no carregamento do arquivo
iniciarMonitorPainelGlobal();

// Exposição pública de APIs
window.selecionarProcessosLivres = selecionarProcessosLivres;
window.executarLivresXs1 = executarLivresXs1;
window.injetarBotaoLivresPainelGlobal = injetarBotaoLivresPainelGlobal;

