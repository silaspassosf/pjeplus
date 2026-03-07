(function () {
    'use strict';

    async function aplicarVisibilidadeSigilosos() {
        try {
            console.log('[V] Iniciando visibilidade (TODOS os anexos do primeiro documento)...');

            const itens = Array.from(document.querySelectorAll('li.tl-item-container'));
            if (!itens.length) {
                alert('⚠️ Nenhum item na timeline');
                return;
            }

            let totalProcessados = 0;
            let encontrouPrimeiro = false;

            // Processar apenas o PRIMEIRO documento com anexos
            for (const item of itens) {
                if (encontrouPrimeiro) break;

                const anexosComp = item.querySelector('pje-timeline-anexos');
                if (!anexosComp) continue;

                const toggle = anexosComp.querySelector('div[name="mostrarOuOcultarAnexos"]');
                if (!toggle) continue;

                const jaExpandido = toggle.getAttribute('aria-pressed') === 'true';

                if (!jaExpandido) {
                    console.log('[V] Expandindo anexos...');
                    toggle.click();
                    await sleep(600);
                }

                await sleep(200);
                const anexoLinks = anexosComp.querySelectorAll('a.tl-documento[id^="anexo_"]');

                if (!anexoLinks.length) continue;

                console.log(`[V] Encontrados ${anexoLinks.length} anexos - processando TODOS...`);
                encontrouPrimeiro = true;

                // Processar TODOS os anexos do primeiro documento
                for (const anexo of anexoLinks) {
                    try {
                        const textoAnexo = (anexo.textContent || anexo.innerText || '').trim();
                        console.log(`[V] Processando anexo ${totalProcessados + 1}: ${textoAnexo}`);

                        // 1. Procurar ícone + do anexo
                        const iconePlus = anexo.querySelector('i.fa-plus, [class*="plus"], button[title*="Visibilidade"]') ||
                            anexo.parentElement?.querySelector('i.fa-plus, [class*="plus"]');

                        if (!iconePlus) {
                            console.log(`[V] ⚠️ Ícone + não encontrado para: ${textoAnexo}`);
                            continue;
                        }

                        const elemClicavel = iconePlus.closest('button') || iconePlus;
                        elemClicavel.click();
                        await sleep(1500);

                        // 2. Aguardar modal de visibilidade
                        let modal = null;
                        for (let t = 0; t < 30; t++) {
                            const mods = document.querySelectorAll('.cdk-overlay-container .mat-dialog-container');
                            for (const m of mods) {
                                const html = m.innerHTML || '';
                                if (html.includes('Visibilidade') && (html.includes('partes') || html.includes('Atribuir'))) {
                                    modal = m;
                                    break;
                                }
                            }
                            if (modal) break;
                            await sleep(200);
                        }

                        if (!modal) {
                            console.log(`[V] ⚠️ Modal não encontrado para: ${textoAnexo}`);
                            document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                            await sleep(800);
                            continue;
                        }

                        console.log('[V] Modal encontrado - processando...');
                        await sleep(600);

                        // 3. Clicar "Marcar Todas"
                        try {
                            let marcarTodasBtn = null;
                            const iconeMarcarTodas = modal.querySelector('i.fa-check.marcar-todas');
                            if (iconeMarcarTodas) {
                                marcarTodasBtn = iconeMarcarTodas.closest('button, div[role="button"]') || iconeMarcarTodas;
                            }
                            if (!marcarTodasBtn) {
                                marcarTodasBtn = modal.querySelector('.marcar-todas');
                            }
                            if (!marcarTodasBtn) {
                                const botaoIcone = modal.querySelector('i.fa-check.botao-icone-titulo-coluna');
                                if (botaoIcone) {
                                    marcarTodasBtn = botaoIcone.closest('button, div[role="button"]') || botaoIcone;
                                }
                            }
                            if (marcarTodasBtn) {
                                console.log('[V] Clicando "Marcar Todas"...');
                                if (marcarTodasBtn.tagName === 'BUTTON' || marcarTodasBtn.getAttribute('role') === 'button') {
                                    marcarTodasBtn.click();
                                } else {
                                    const parentBtn = marcarTodasBtn.closest('button');
                                    if (parentBtn) {
                                        parentBtn.click();
                                    } else {
                                        marcarTodasBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                    }
                                }
                                await sleep(400);
                            }
                        } catch (e) {
                            console.log('[V] Erro ao buscar "Marcar Todas":', e.message);
                        }

                        // 4. Clicar botão Salvar
                        await sleep(300);
                        const btnSalvar = Array.from(modal.querySelectorAll('button'))
                            .find(b => (b.textContent || '').trim().toLowerCase().includes('salvar'));

                        if (!btnSalvar) {
                            console.log('[V] ⚠️ Botão Salvar não encontrado');
                            document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                            await sleep(800);
                            continue;
                        }

                        console.log('[V] Clicando Salvar...');
                        btnSalvar.click();
                        await sleep(1500);

                        console.log('[V] ✅ Anexo processado');
                        totalProcessados++;

                        document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                        await sleep(500);

                    } catch (e) {
                        console.error('[V] Erro ao processar anexo:', e.message);
                        try {
                            document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                        } catch (e2) { }
                        await sleep(800);
                    }
                }
            }

            if (totalProcessados > 0) {
                console.log(`[V] ✅ Concluído! ${totalProcessados} anexo(s) processado(s) com visibilidade`);
            } else {
                console.log('[V] ⚠️ Nenhum anexo encontrado para processar');
            }

        } catch (e) {
            console.error('[V] Erro:', e);
        }
    }

    async function aplicarVisibilidadeSigilosamente() {
        showToast('🔐 Iniciando visibilidade...', '#d9534f');
        try {
            const itens = Array.from(document.querySelectorAll('li.tl-item-container'));
            if (!itens.length) { alert('⚠ Nenhum item na timeline'); return; }

            let total = 0;
            let achouPrimeiro = false;

            for (const item of itens) {
                if (achouPrimeiro) break;
                const anexosComp = item.querySelector('pje-timeline-anexos');
                if (!anexosComp) continue;

                const toggle = anexosComp.querySelector('div[name="mostrarOuOcultarAnexos"]');
                if (!toggle) continue;

                const jaExpandido = toggle.getAttribute('aria-pressed') === 'true';
                if (!jaExpandido) {
                    toggle.click();
                    await sleep(600);
                }
                await sleep(200);
                const links = anexosComp.querySelectorAll('a.tl-documento[id^="anexo_"]');
                if (!links.length) continue;
                achouPrimeiro = true;

                for (const anexo of links) {
                    try {
                        const icone = anexo.querySelector('i.fa-plus, [class*="plus"]') ||
                            anexo.parentElement?.querySelector('i.fa-plus, [class*="plus"]');
                        if (!icone) continue;
                        (icone.closest('button') || icone).click();
                        await sleep(1500);

                        // Aguardar modal de visibilidade
                        let modal = null;
                        for (let t = 0; t < 30; t++) {
                            for (const m of document.querySelectorAll(
                                '.cdk-overlay-container .mat-dialog-container')) {
                                if (m.innerHTML.includes('Visibilidade') &&
                                    (m.innerHTML.includes('partes') || m.innerHTML.includes('Atribuir'))) {
                                    modal = m; break;
                                }
                            }
                            if (modal) break;
                            await sleep(200);
                        }
                        if (!modal) {
                            document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                            await sleep(800); continue;
                        }

                        // Marcar Todas
                        const marcarSels = [
                            'i.fa-check.marcar-todas', '.marcar-todas',
                            'i.fa-check.botao-icone-titulo-coluna',
                        ];
                        let btnMarcar = null;
                        for (const s of marcarSels) {
                            const ic = modal.querySelector(s);
                            if (ic) { btnMarcar = ic.closest('button, div[role="button"]') || ic; break; }
                        }
                        if (btnMarcar) { btnMarcar.click(); await sleep(400); }

                        // Salvar
                        const btnSalvar = Array.from(modal.querySelectorAll('button'))
                            .find(b => (b.textContent || '').trim().toLowerCase().includes('salvar'));
                        if (btnSalvar) { btnSalvar.click(); await sleep(1500); total++; }
                        else {
                            document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                            await sleep(800);
                        }
                    } catch (e) {
                        document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
                        await sleep(800);
                    }
                }
            }
            showToast(`✅ Visibilidade: ${total} anexo(s) processado(s)`, '#28a745', 5000);
        } catch (e) {
            showToast(`❌ Erro: ${e.message}`, '#dc3545');
        }
    }

    // Exports
    window.aplicarVisibilidadeSigilosamente = aplicarVisibilidadeSigilosamente;
    window.aplicarVisibilidadeSigilosos = aplicarVisibilidadeSigilosos;
})();