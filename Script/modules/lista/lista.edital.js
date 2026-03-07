(function () {
    'use strict';

    async function executarEdital() {
        const docs = await lerTimelineCompleta();
        const editais = docs.filter(d => d.tipo === 'Edital').sort(byDataDesc);
        const saida = editais.map(e => ({ ...e, _label: 'Edital' }));

        renderTabela('listaDocsEditalSimples', '📣 Relatório de Editais', '#28a745',
            saida, async (doc) => {
                const elem = resolverElemento(doc);
                if (elem) {
                    elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    elem.classList.add('pjetools-destaque-edital');
                    setTimeout(() => elem?.classList.remove('pjetools-destaque-edital'), 3000);
                }
            });
    }

    // Exports
    window.executarEdital = executarEdital;
})();