'use strict';

window.CSS_PAINEL = `
.pjetools-destaque        { outline:3px solid #007bff!important; background:#e7f3ff!important; transition:.3s; }
.pjetools-destaque-edital { outline:3px solid #28a745!important; background:#e8f5e8!important; transition:.3s; }
#pjetools-painel button:hover { opacity:.85; }
`;

window.criarPainel = function (botoes) {
    document.getElementById('pjetools-painel')?.remove();
    addStyles(CSS_PAINEL, 'pjetools-styles');

    const painel = document.createElement('div');
    painel.id = 'pjetools-painel';
    painel.style.cssText = `position:fixed;bottom:170px;right:20px;z-index:99999;` +
        `background:#fff;border:2px solid #333;border-radius:8px;` +
        `box-shadow:0 8px 32px rgba(0,0,0,.25);padding:10px 12px;font-family:sans-serif;` +
        `min-width:190px;user-select:none;`;

    const titulo = document.createElement('div');
    titulo.textContent = 'PJeTools v1.0';
    titulo.style.cssText = `font-weight:bold;margin-bottom:8px;color:#333;font-size:12px;` +
        `text-align:center;border-bottom:1px solid #ddd;padding-bottom:6px;`;
    painel.appendChild(titulo);

    const grid = document.createElement('div');
    grid.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:6px;';

    botoes.forEach(btn => {
        const b = document.createElement('button');
        b.id = btn.id;
        b.textContent = btn.texto;
        b.title = btn.titulo || '';
        b.style.cssText = `padding:7px 6px;background:${btn.bg};color:#fff;border:none;` +
            `border-radius:4px;cursor:pointer;font-weight:bold;font-size:11px;` +
            `transition:opacity .15s;`;
        b.onclick = btn.fn;
        if (btn.full) b.style.gridColumn = '1 / -1';
        grid.appendChild(b);
    });

    painel.appendChild(grid);

    // Botão limpar cache
    const limparBtn = document.createElement('button');
    limparBtn.textContent = '🔄 Limpar Cache';
    limparBtn.style.cssText = `margin-top:8px;width:100%;padding:5px;background:#6c757d;` +
        `color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:10px;`;
    limparBtn.onclick = () => {
        invalidarCacheTimeline();
        showToast('Cache da timeline limpo', '#6c757d', 2000);
    };
    painel.appendChild(limparBtn);

    // Arrastar
    _tornaPainelArrastavel(painel);

    document.body.appendChild(painel);
    PJeState.registry.add(() => painel.remove());
}

window._tornaPainelArrastavel = function (el) {
    let ox = 0, oy = 0, drag = false;
    const onDown = e => {
        if (e.target.tagName === 'BUTTON') return;
        drag = true; ox = e.clientX - el.offsetLeft; oy = e.clientY - el.offsetTop;
        e.preventDefault();
    };
    const onMove = e => {
        if (!drag) return;
        el.style.left = (e.clientX - ox) + 'px';
        el.style.top = (e.clientY - oy) + 'px';
        el.style.right = 'auto'; el.style.bottom = 'auto';
    };
    const onUp = () => { drag = false; };
    el.addEventListener('mousedown', onDown);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    // Limpeza quando painel for removido
    PJeState.registry.add(() => {
        el.removeEventListener('mousedown', onDown);
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    });
}

window.inicializarPainel = function () {
    criarPainel([
        { id: 'btnCheck', texto: '🔎 Check', bg: '#007bff', fn: executarCheck, titulo: 'Relatório de Medidas' },
        { id: 'btnEdital', texto: '📣 Edital', bg: '#28a745', fn: executarEdital, titulo: 'Relatório de Editais' },
        { id: 'btnPgto', texto: '💳 Pgto', bg: '#ff6600', fn: executarPgto, titulo: 'Abrir página de pagamento' }
    ]);
}

