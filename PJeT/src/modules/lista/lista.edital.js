'use strict';

// ── Portado de Script/modules/lista/lista.edital.js ─────────────
// Sem GM_*, sem @require externos — expõe window.executarEdital

window.executarEdital = async function () {
    const log = window.PJeLogger || {
        edital:  (...a) => console.log('[PJeT::EDITAL]', ...a),
        warn:    (c, ...a) => console.warn(`[PJeT::${c}]`, ...a),
        error:   (c, m, e) => console.error(`[PJeT::${c} ERRO] ${m}:`, e),
        success: (c, ...a) => console.log(`[PJeT::${c}] ✅`, ...a),
    };

    log.edital('Iniciando relatório de editais...');
    try {
        const docs = await lerTimelineCompleta();
        if (!docs || !docs.length) {
            log.warn('EDITAL', 'Timeline retornou vazia.');
            showToast('Nenhum documento encontrado na timeline', '#f57f17', 3500);
            return;
        }

        const editais = docs.filter(d => d.tipo === 'Edital').sort(byDataDesc);
        log.edital(`Total de editais encontrados: ${editais.length}`);

        if (editais.length === 0) {
            showToast('Nenhum edital encontrado no processo.', '#6c757d', 3500);
            return;
        }

        const saida = editais.map(e => ({ ...e, _label: 'Edital' }));

        renderTabela('listaDocsEditalSimples', '📣 Relatório de Editais', '#28a745',
            saida, async (doc) => {
                log.edital(`Destacando edital no DOM: ${doc.id}`);
                const elem = resolverElemento(doc) || encontrarElementoPorUid(doc.id);
                if (elem) {
                    elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    elem.classList.add('pjetools-destaque-edital');
                    setTimeout(() => elem?.classList.remove('pjetools-destaque-edital'), 3000);
                } else {
                    log.warn('EDITAL', `Elemento do edital não encontrado no DOM: ${doc.id}`);
                }
            });

        log.success('EDITAL', `Tabela com ${saida.length} edital(is) renderizada com sucesso.`);
    } catch (err) {
        log.error('EDITAL', 'Falha ao processar relatório de editais', err);
    }
};
