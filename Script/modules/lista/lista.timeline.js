'use strict';

window.CACHE_TTL = 5 * 60 * 1000; // 5 minutos

// Meses PT para número
window.MESES_PT = {
    jan: '01', fev: '02', mar: '03', abr: '04', mai: '05', jun: '06',
    jul: '07', ago: '08', set: '09', out: '10', nov: '11', dez: '12',
};

window.extrairData = function (item) {
    let el = null;
    let prev = item.previousElementSibling;
    while (prev) {
        el = prev.querySelector('.tl-data[name="dataItemTimeline"]') ||
            prev.querySelector('.tl-data');
        if (el) break;
        prev = prev.previousElementSibling;
    }
    if (!el) el = item.querySelector('.tl-data[name="dataItemTimeline"]') ||
        item.querySelector('.tl-data');
    const txt = el?.textContent.trim() || '';

    // dd/mm/yyyy
    const m1 = txt.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
    if (m1) return m1[1];

    // "20 out. 2025"
    const m2 = txt.match(/(\d{1,2})\s+(\w{3})\.\s+(\d{4})/);
    if (m2) {
        const mes = MESES_PT[m2[2].toLowerCase()];
        if (mes) return `${m2[1].padStart(2, '0')}/${mes}/${m2[3].slice(-2)}`;
    }
    return '';
}

window.extrairUid = function (link) {
    const m = link.textContent.trim().match(/\s-\s([A-Za-z0-9]+)$/);
    return m ? m[1] : null;
}

window.classificarItem = function (low, tipoTexto, titulo) {
    if (low.includes('devolução de ordem')) return 'Certidão devolução pesquisa';
    if (low.includes('certidão de oficial') || low.includes('oficial de justiça'))
        return 'Certidão de oficial de justiça';
    if ((low.includes('mandado de pagamento') && (low.includes('alvará'))))
        return 'Alvarás';
    if ((tipoTexto === 'certidão' || tipoTexto === 'documento diverso') &&
        (titulo.includes('alvará'))) return 'Alvarás';
    if (tipoTexto === 'alvará' || tipoTexto === 'alvara') return 'Alvarás';
    if (low.includes('juntada de alvará')) return 'Alvarás';
    if (low.includes('sobrestamento')) return 'Decisão (Sobrestamento)';
    if (low.includes('serasa') || low.includes('apjur') ||
        low.includes('carta ação') || low.includes('carta acao')) return 'SerasaAntigo';
    if (low.includes('edital')) return 'Edital';
    return null;
}

window.lerTimelineCompleta = async function () {
    const state = PJeState.lista;
    const agora = Date.now();
    if (state.docs && (agora - state.readAt) < CACHE_TTL) return state.docs;

    const seletores = [
        'li.tl-item-container',
        '.tl-data .tl-item-container',
        '.timeline-item',
    ];
    let itens = [];
    for (const s of seletores) {
        itens = document.querySelectorAll(s);
        if (itens.length) break;
    }

    const documentos = [];

    for (let i = 0; i < itens.length; i++) {
        const item = itens[i];
        const textLink = item.querySelector('a.tl-documento:not([target])');
        if (!textLink) continue;
        const iconLink = item.querySelector('a.tl-documento[target="_blank"]');
        if (!iconLink) continue;

        const spans = textLink.querySelectorAll('span');
        if (spans.length < 4) continue;

        const tipoTexto = spans[2].textContent.trim().toLowerCase();
        const titulo = spans[3].textContent.trim().toLowerCase();
        const texto = textLink.textContent.trim();
        const low = texto.toLowerCase();
        const tipo = classificarItem(low, tipoTexto, titulo);
        if (!tipo) continue;

        // ID: usar UID do texto ou fallback index
        const id = extrairUid(textLink) || `doc${i}`;

        // IMPORTANTE: guardar apenas o ID do elemento, não a referência DOM
        // A referência será re-resolvida no momento do uso (evita memory leak)
        documentos.push({
            tipo, texto, id, tipoTexto,
            elementoId: item.id || null,
            elementoSel: item.id ? `#${CSS.escape(item.id)}` : null,
            linkId: iconLink.id || null,
            data: extrairData(item),
            isAnexo: false,
        });

        // Buscar anexos Serasa/CNIB apenas para certidões
        const isCertAlvo = (tipo === 'Certidão devolução pesquisa' ||
            tipo === 'Certidão de oficial de justiça');
        if (isCertAlvo) {
            const anexosRoot = item.querySelector('pje-timeline-anexos');
            let anexoLinks = anexosRoot
                ? anexosRoot.querySelectorAll('a.tl-documento[id^="anexo_"]') : [];

            // Expandir se necessário
            if (!anexoLinks.length) {
                const toggle = item.querySelector(
                    'pje-timeline-anexos div[name="mostrarOuOcultarAnexos"]');
                if (toggle) {
                    try { toggle.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
                    catch (e) { }
                    await sleep(350);
                    anexoLinks = item.querySelectorAll('a.tl-documento[id^="anexo_"]');
                }
            }

            Array.from(anexoLinks).forEach(anexo => {
                const t = (anexo.textContent || '').toLowerCase();
                const tipoAnexo = /serasa|serasajud/.test(t) ? 'Serasa'
                    : /cnib|indisp/.test(t) ? 'CNIB'
                        : null;
                if (!tipoAnexo) return;
                documentos.push({
                    tipo: tipoAnexo, texto: anexo.textContent.trim(),
                    id: anexo.id || `anexo_${id}_${tipoAnexo}`,
                    elementoId: anexo.id || null,
                    elementoSel: anexo.id ? `a[id="${anexo.id}"]` : null,
                    linkId: anexo.id || null,
                    data: extrairData(item),
                    isAnexo: true, parentId: id,
                });
            });
        }
    }

    state.docs = documentos;
    state.readAt = agora;
    return documentos;
}

window.invalidarCacheTimeline = function () {
    PJeState.lista.docs = null;
    PJeState.lista.readAt = 0;
}

// Helper para re-resolver elemento pelo ID/seletor salvo
window.resolverElemento = function (doc) {
    if (doc.elementoSel) return document.querySelector(doc.elementoSel);
    if (doc.elementoId) return document.getElementById(doc.elementoId);
    return null;
}

window.resolverLink = function (doc) {
    if (doc.linkId) return document.getElementById(doc.linkId) ||
        document.querySelector(`a[id="${doc.linkId}"]`);
    return null;
}

