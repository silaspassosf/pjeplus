'use strict';

// ── Pgto ─────────────────────────────────────────────────────────
window.executarPgto = async function () {
    const btnMovimentos = document.getElementById('exibirMovimentos');
    if (btnMovimentos && btnMovimentos.getAttribute('aria-label') === 'Exibir movimentos.') {
        btnMovimentos.click();
        await sleep(1500);
    }

    // Usar docs cacheados se possível, porém sem ignorar movimentos. 
    // Como precisamos ler os movimentos DOM diretamente:
    const docs = await lerTimelineCompleta();
    const filtrados = filtrarDocs(docs);
    const alvaras = filtrados.filter(d => (d.tipo || '').toLowerCase() === 'alvarás' && d.data);

    if (alvaras.length === 0) {
        alert('Nenhum Alvará encontrado na timeline.');
        return;
    }

    const saidaPgto = [];
    const elements = Array.from(document.querySelectorAll('li.tl-item-container, .timeline-item'));

    for (const alv of alvaras) {
        let registrado = false;
        const elemAlv = resolverElemento(alv);
        if (elemAlv) {
            const idx = elements.indexOf(elemAlv);
            if (idx !== -1) {
                // Procurar nos itens ACIMA (newer, portanto idx menores)
                // Vamos checar os 15 itens mais recentes acima deste alvara (2 dias de margem costuma ser poucos itens)
                for (let i = idx - 1; i >= Math.max(0, idx - 15); i--) {
                    const txt = elements[i].textContent || '';
                    if (txt.includes('Efetuado o pagamento de')) {
                        registrado = true;
                        break;
                    }
                    // Opcionalmente podemos parar se acharmos outro documento com data muito maior, mas manter o range de 15 é seguro.
                }
            }
        }

        saidaPgto.push({
            ...alv,
            _label: registrado ? '🟢 Alvará Registrado' : '🔴 Alvará Pendente',
            registrado: registrado
        });
    }

    // Reutilizar o painel do lista.check.js (renderTabela)
    renderTabela('listaDocsPgto', '💸 Controle de Alvarás', '#9c27b0', saidaPgto, async (doc) => {
        const el = resolverElemento(doc);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('pjetools-destaque');
            setTimeout(() => el?.classList.remove('pjetools-destaque'), 3000);
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
}
