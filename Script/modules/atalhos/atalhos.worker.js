(function () {
    'use strict';

    // Executado APENAS na aba worker (?maispje_worker=1)
    // Responsabilidade única: salvar + finalizar expediente e avisar a aba principal.

    async function runWorker() {
        const channel = new BroadcastChannel('maispje_expediente_worker');

        // Registra fechamento para quando a função terminar
        const cleanup = () => { try { channel.close(); } catch (e) { } };

        try {
            showToast('Worker: Aguardando página...', '#4caf50');

            // Salvar expedientes
            const btnSalvar = await waitElementVisible(
                'button[name="btnSalvarExpedientes"]', 15000) ||
                Array.from(document.querySelectorAll('button'))
                    .find(b => b.querySelector('.mat-button-wrapper')
                        ?.textContent.trim() === 'salvar');

            if (btnSalvar) {
                if (!btnSalvar.disabled) btnSalvar.click();
                await sleep(2000);
            }

            // Finalizar / Assinar
            const btnFinalizar = await waitElementVisible(
                'button[name="btnFinalizarExpedientes"]', 10000) ||
                Array.from(document.querySelectorAll('button'))
                    .find(b => (b.querySelector('.mat-button-wrapper')
                        ?.textContent || '').toLowerCase().includes('assinar'));

            if (btnFinalizar && !btnFinalizar.disabled) {
                btnFinalizar.click();
                await sleep(1500);
            }

            showToast('Worker: Concluído! Fechando...', '#4caf50');
            channel.postMessage({ type: 'WORKER_DONE' });
        } catch (e) {
            console.error('[WORKER]', e);
            channel.postMessage({ type: 'WORKER_ERROR', message: e.message || 'Erro desconhecido' });
            showToast(`Worker erro: ${e.message}`, '#f44336');
        } finally {
            await sleep(400);
            cleanup();
            setTimeout(() => window.close(), 500);
        }
    }

    // Exports
    window.runWorker = runWorker;
})();