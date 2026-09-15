'use strict';

// ── Portado de Script/modules/lista/lista.pgto.js ───────────────
// Sem GM_*, sem @require externos — expõe window.executarPgto

window.executarPgto = async function () {
    const log = window.PJeLogger || {
        pgto:    (...a) => console.log('[PJeT::PGTO]', ...a),
        warn:    (c, ...a) => console.warn(`[PJeT::${c}]`, ...a),
        error:   (c, m, e) => console.error(`[PJeT::${c} ERRO] ${m}:`, e),
        success: (c, ...a) => console.log(`[PJeT::${c}] ✅`, ...a),
    };

    log.pgto('Iniciando conferência de alvarás e pagamentos...');
    try {
        const btnMovimentos = document.getElementById('exibirMovimentos');
        if (btnMovimentos && btnMovimentos.getAttribute('aria-label') === 'Exibir movimentos.') {
            log.pgto('Expandindo movimentos na timeline...');
            btnMovimentos.click();
            await sleep(1500);
        }

        const docs = await lerTimelineCompleta();
        if (!docs || !docs.length) {
            log.warn('PGTO', 'Timeline retornou vazia ao buscar alvarás.');
            showToast('Nenhum documento encontrado na timeline', '#f57f17', 3500);
            return;
        }

        const filtrados = filtrarDocs(docs);
        const alvaras = filtrados.filter(d => (d.tipo || '').toLowerCase() === 'alvarás' && d.data);

        log.pgto(`Total de alvarás identificados: ${alvaras.length}`);

        if (alvaras.length === 0) {
            log.warn('PGTO', 'Nenhum alvará com data encontrado.');
            showToast('Nenhum Alvará encontrado na timeline do processo.', '#6c757d', 3500);
            return;
        }

        const saidaPgto = [];
        const elements = Array.from(document.querySelectorAll('li.tl-item-container, .timeline-item'));
        log.pgto(`Cruzando ${alvaras.length} alvará(s) com ${elements.length} itens do DOM da timeline...`);

        let registradosCount = 0;
        let pendentesCount = 0;

        for (const alv of alvaras) {
            let registrado = false;
            const elemAlv = resolverElemento(alv) || encontrarElementoPorUid(alv.id);
            if (elemAlv) {
                const idx = elements.indexOf(elemAlv);
                if (idx !== -1) {
                    // Procurar nos itens ACIMA (mais recentes, portanto idx menor)
                    // Checa até 15 itens mais recentes acima deste alvará
                    for (let i = idx - 1; i >= Math.max(0, idx - 15); i--) {
                        const txt = elements[i].textContent || '';
                        if (txt.includes('Efetuado o pagamento de')) {
                            registrado = true;
                            break;
                        }
                    }
                }
            } else {
                log.warn('PGTO', `Elemento do alvará não localizado no DOM: ${alv.id}`);
            }

            if (registrado) registradosCount++;
            else pendentesCount++;

            saidaPgto.push({
                ...alv,
                _label: registrado ? '🟢 Alvará Registrado' : '🔴 Alvará Pendente',
                registrado: registrado
            });
        }

        log.pgto(`Resultado da conferência: ${registradosCount} registrado(s), ${pendentesCount} pendente(s).`);

        // Reutilizar o painel do lista.check.js (renderTabela)
        renderTabela('listaDocsPgto', '💸 Controle de Alvarás', '#9c27b0', saidaPgto, async (doc) => {
            log.pgto(`Destacando alvará no DOM: ${doc.id} (${doc._label})`);
            const el = resolverElemento(doc) || encontrarElementoPorUid(doc.id);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                el.classList.add('pjetools-destaque');
                setTimeout(() => el?.classList.remove('pjetools-destaque'), 3000);
            } else {
                log.warn('PGTO', `Elemento do alvará não encontrado no DOM: ${doc.id}`);
            }
        });

        // Colorir as linhas da tabela criada
        const tbl = document.getElementById('listaDocsPgto_tbl');
        if (tbl) {
            const tbody = tbl.querySelector('tbody');
            if (tbody) {
                Array.from(tbody.querySelectorAll('tr')).forEach((tr, i) => {
                    const docRef = saidaPgto[i];
                    if (docRef.registrado) {
                        tr.style.backgroundColor = '#e8f5e9'; // verde claro
                    } else {
                        tr.style.backgroundColor = '#ffebee'; // vermelho claro
                    }
                });
            }
        }

        log.success('PGTO', `Tabela de Controle de Alvarás exibida com sucesso (${saidaPgto.length} itens).`);
    } catch (err) {
        log.error('PGTO', 'Falha ao processar conferência de alvarás', err);
    }
};
