'use strict';

// ── Pgto ─────────────────────────────────────────────────────────
window.executarPgto = async function () {
    const docs = await lerTimelineCompleta();
    const filtrados = filtrarDocs(docs);
    const alvaras = filtrados
        .filter(d => d.tipo.toLowerCase() === 'alvarás' && d.data)
        .map(a => ({ data: a.data, link: resolverLink(a)?.getAttribute('href') || '#' }));
    localStorage.setItem('pjeplus_alvaras', JSON.stringify(alvaras));

    const match = window.location.href.match(/\/processo\/(\d+)\//);
    if (match) {
        window.open(
            `https://pje.trt2.jus.br/pjekz/pagamento/${match[1]}/cadastro`, '_blank');
    }
}
