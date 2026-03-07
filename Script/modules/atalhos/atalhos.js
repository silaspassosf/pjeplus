'use strict';

const CHANNEL_NAME = 'maispje_expediente_worker';

function initAtalhos() {
    const reg = PJeState.atalhos.registry;

    // Garante channel único (fechar anterior se existir)
    if (PJeState.atalhos.channel) {
        try { PJeState.atalhos.channel.close(); } catch(e) {}
    }
    const channel = new BroadcastChannel(CHANNEL_NAME);
    PJeState.atalhos.channel = channel;
    reg.channel(channel);

    // Escutar resposta do worker
    reg.on(channel, 'message', async event => {
        if (event.data?.type === 'WORKER_DONE') {
            showToast('F7: Expediente concluído. Limpando...', '#ff9800');
            await runCleanup();
            await sleep(500);
            await hoverAndClickTarget('pje-gigs', 'Inativar atividades');
        }
        if (event.data?.type === 'WORKER_ERROR') {
            showToast(`Worker erro: ${event.data.message}`, '#f44336');
        }
    });

    // Teclas F6 / F7
    reg.on(document, 'keydown', async e => {
        if (e.key === 'F6') {
            e.preventDefault();
            showToast('F6: Iniciando limpeza GIGS...', '#ff9800');
            await runCleanup();
        } else if (e.key === 'F7') {
            e.preventDefault();
            showToast('F7: Abrindo aba de expediente...', '#673ab7');
            await runExpedienteFlow(channel);
        }
    });
}

// ── GIGS cleanup ─────────────────────────────────────────────────
async function runCleanup() {
    const runner = new AsyncRunner();  // runner local, não persiste
    await runner.run(async (signal) => {
        let removed = 0;
        let hasMore = true;
        while (hasMore && !signal.aborted) {
            hasMore = false;
            for (const row of document.querySelectorAll(
                'pje-gigs-atividades table tbody tr')) {
                if (signal.aborted) break;
                if (row.style.display === 'none') continue;
                const desc = row.querySelector('td .descricao')?.textContent.trim();
                if (!desc) continue;
                const prazo = row.querySelector('pje-gigs-alerta-prazo .prazo');
                if (!prazo) continue;
                if (prazo.querySelector('i.fa-clock.far.success')) continue;
                const isVencida  = prazo.querySelector('i.danger.fa-clock.far');
                const isSemPrazo = prazo.querySelector('i.fa.fa-pen.atividade-sem-prazo');
                const descL = desc.toLowerCase();
                const hasXsSilas = descL.includes('xs') || descL.includes('silas');
                const hasDomE    = desc.includes('Dom.E');
                if (!((isVencida && hasXsSilas) ||
                      (isSemPrazo && (hasXsSilas || hasDomE)))) continue;
                const btnEx = row.querySelector('button[mattooltip="Excluir Atividade"]');
                if (!btnEx) continue;
                btnEx.click(); await sleep(800);
                let btnSim = null;
                for (const b of document.querySelectorAll('button[color="primary"]')) {
                    if (b.querySelector('span.mat-button-wrapper')?.textContent.trim() === 'Sim') {
                        btnSim = b; break;
                    }
                }
                if (btnSim) { btnSim.click(); await sleep(600); removed++; hasMore = true; break; }
            }
        }
        showToast(`✅ GIGS: ${removed} atividade(s) removida(s)`, '#4caf50', 5000);
    });
}

// ── Expediente flow ──────────────────────────────────────────────
async function runExpedienteFlow(channel) {
    const url = window.location.href
        .replace(/\/detalhe.*/, '/comunicacoesprocessuais/minutas?maispje_worker=1');
    window.open(url, '_blank');
}

async function hoverAndClickTarget(menuSelector, buttonLabel) {
    const triggerEl = document.querySelector(menuSelector);
    if (!triggerEl) {
        showToast(`Menu não encontrado! (${menuSelector})`, '#f44336');
        return;
    }
    hoverAndDispatch(triggerEl);
    const container = await waitElement('maispjecontaineraa', 3000);
    if (!container) { showToast('Timeout: Menu MaisPJe não abriu!', '#f44336'); return; }
    await sleep(250);
    const labelL = buttonLabel.toLowerCase();
    const alvo = Array.from(container.querySelectorAll('button, div, span, a'))
        .find(el => {
            const txt = (el.textContent || '').toLowerCase().trim();
            return txt === labelL || txt.includes(labelL);
        });
    if (alvo) {
        alvo.style.border = '2px solid red';
        await sleep(150);
        (alvo.querySelector('.mat-button-wrapper') || alvo).click();
        showToast(`Ação disparada: ${buttonLabel}`, '#4caf50');
    } else {
        showToast(`Botão não encontrado: ${buttonLabel}`, '#f44336');
    }
}