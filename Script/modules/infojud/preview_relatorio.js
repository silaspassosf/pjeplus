// Cole no console do browser para previsualizar o painel de relatório
// Dados de exemplo: 4 empresas com sócio + 3 PFs → testa paginação (2 páginas)
(function () {
    document.getElementById('god-relatorio-panel')?.remove();

    const dadosRelatorio = [
        [
            'Empresa: BANCO SANTANDER (BRASIL) S.A.',
            'Endereço: AVENIDA PRES JUSCELINO KUBITSCHEK , 2041 04543011',
            'Sócio desta empresa: REGINALDO ANTONIO RIBEIRO (091.440.778-31)',
            'Endereço: R TUIM 230 APTO 151 VILA UBERABINHA 04514100',
        ].join('\n'),
        [
            'Empresa: PETROBRAS DISTRIBUIDORA S.A.',
            'Endereço: RUA GENERAL CANABARRO 500 MARACANA 20270021',
            'Sócio desta empresa: ANA PAULA FERREIRA SOUZA (234.567.890-12)',
            'Endereço: AV ATLANTICA 1800 APTO 304 COPACABANA 22021001',
        ].join('\n'),
        [
            'Empresa: MAGAZINE LUIZA S.A.',
            'Endereço: RUA VOLUNTARIOS DA PATRIA 1200 SANTANA 02402000',
            'Sócio desta empresa: FREDERICO TRAJANO INÁCIO RODRIGUES (345.678.901-23)',
            'Endereço: AL SANTOS 1234 CONJ 81 CERQUEIRA CESAR 01419100',
        ].join('\n'),
        [
            'Empresa: ITAU UNIBANCO S.A.',
            'Endereço: PRACA ALFREDO EGYDIO DE SOUZA ARANHA 100 JABAQUARA 04344902',
            'Sócio desta empresa: CANDIDO BRACHER NETO (456.789.012-34)',
            'Endereço: R IGUATEMI 151 SALA 2801 ITAIM BIBI 01451011',
        ].join('\n'),
        [
            'Nome: MARCUS LORENTE',
            'CPF: 184.839.448-98',
            'Endereço: R FIACAO DA SAUDE 00104 AP1408 VILA DA SAUDE 04144020',
        ].join('\n'),
        [
            'Nome: FERNANDA CRISTINA OLIVEIRA',
            'CPF: 567.890.123-45',
            'Endereço: R BELA CINTRA 877 APTO 52 CONSOLACAO 01415001',
        ].join('\n'),
        [
            'Nome: ROBERTO CARLOS NEVES',
            'CPF: 678.901.234-56',
            'Endereço: AV BRIGADEIRO LUIZ ANTONIO 3142 AP 71 JARDIM PAULISTA 01402002',
        ].join('\n'),
    ];

    // ── Posicionamento dinâmico: cobre toolbar (top=0), limita no fundo da linha Prazo/Ato
    function getPos() {
        let top = 0, right = 20, maxH = Math.round(window.innerHeight * 0.9);
        // Right: encosta à esquerda do ícone de acessibilidade
        const icon = document.querySelector('.fa-universal-access');
        if (icon) {
            const r = icon.getBoundingClientRect();
            right = Math.round(window.innerWidth - r.left + 6);
        }
        // MaxH: bottom da <tr> que contém "Prazo" e "Ato" (linha de cabeçalho da tabela)
        for (const row of document.querySelectorAll('tr,thead tr')) {
            const txt = row.textContent || '';
            if (txt.includes('Prazo') && txt.includes('Ato')) {
                const r = row.getBoundingClientRect();
                if (r.bottom > 50) { maxH = Math.round(r.bottom); break; }
            }
        }
        return { top, right, maxH };
    }
    const pos = getPos();

    const CARDS_PER_PAGE = 4;
    let currentPage = 0;
    const totalPages = Math.ceil(dadosRelatorio.length / CARDS_PER_PAGE);

    const painel = document.createElement('div');
    painel.id = 'god-relatorio-panel';
    painel.style.cssText = `position:fixed;right:${pos.right}px;top:${pos.top}px;width:528px;background:#fff;border:2px solid #004d40;border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,0.4);font-family:"Segoe UI",sans-serif;z-index:10000;height:${pos.maxH}px;display:flex;flex-direction:column;`;

    const cab = document.createElement('div');
    cab.style.cssText = 'display:flex;justify-content:space-between;align-items:center;background:#004d40;color:#fff;padding:7px 12px;cursor:grab;flex-shrink:0;';

    const titulo = document.createElement('span');
    titulo.textContent = 'RELATÓRIO DE ENDEREÇOS';
    titulo.style.cssText = 'font-size:13px;font-weight:800;letter-spacing:.5px;cursor:pointer;';

    const ctrls = document.createElement('span');
    ctrls.style.cssText = 'display:flex;gap:10px;align-items:center;font-size:13px;font-weight:700;';

    const btnToggle = document.createElement('span');
    btnToggle.textContent = '▲';
    btnToggle.style.cursor = 'pointer';

    const btnX = document.createElement('span');
    btnX.textContent = '✕';
    btnX.style.cursor = 'pointer';
    btnX.onclick = () => painel.remove();

    ctrls.appendChild(btnToggle);
    ctrls.appendChild(btnX);
    cab.appendChild(titulo);
    cab.appendChild(ctrls);
    painel.appendChild(cab);

    // ── Corpo (flex-grow, sem scroll — paginação controla o volume)
    const corpo = document.createElement('div');
    corpo.style.cssText = 'padding:7px 10px 4px;overflow-y:auto;user-select:text;flex:1;';
    painel.appendChild(corpo);

    // ── Barra de paginação
    const paginacao = document.createElement('div');
    paginacao.style.cssText = 'display:flex;justify-content:center;align-items:center;gap:8px;padding:4px 10px 6px;border-top:1px solid #ddd;flex-shrink:0;';

    const btnPrev = document.createElement('button');
    btnPrev.textContent = '◀ Anterior';
    btnPrev.style.cssText = 'border:none;background:#004d40;color:#fff;border-radius:4px;padding:3px 9px;cursor:pointer;font-size:11px;font-weight:700;';
    btnPrev.onclick = () => { if (currentPage > 0) { currentPage--; renderPage(); } };

    const pageInfo = document.createElement('span');
    pageInfo.style.cssText = 'font-size:11px;font-weight:700;color:#333;min-width:44px;text-align:center;';

    const btnNext = document.createElement('button');
    btnNext.textContent = 'Próxima ▶';
    btnNext.style.cssText = 'border:none;background:#004d40;color:#fff;border-radius:4px;padding:3px 9px;cursor:pointer;font-size:11px;font-weight:700;';
    btnNext.onclick = () => { if (currentPage < totalPages - 1) { currentPage++; renderPage(); } };

    paginacao.appendChild(btnPrev); paginacao.appendChild(pageInfo); paginacao.appendChild(btnNext);
    painel.appendChild(paginacao);
    document.body.appendChild(painel);

    // ── Helpers de render
    function escapeHtml(s) { return String(s).replace(/[&<>"]+/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

    const nw = 'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    const S = {
        empEnd:   'font-size:11.5px;font-weight:800;color:#01579b;white-space:nowrap;overflow:visible;',   // empresa+endço numa linha
        socio:    `font-size:11px;font-weight:700;color:#1a237e;margin-top:3px;margin-bottom:1px;padding:2px 6px;background:#e8eaf6;border-left:3px solid #3949ab;border-radius:0 3px 3px 0;${nw}`,
        endSocio: 'font-size:11px;color:#283593;padding-left:10px;white-space:nowrap;overflow:visible;',
        pf:       `font-size:12px;font-weight:800;color:#4a148c;${nw}`,
        endPf:    'font-size:11px;color:#333;margin-top:1px;white-space:nowrap;overflow:visible;',
    };

    function renderBlock(b) {
        const lines = String(b).split('\n').filter(l => l.trim());
        let ctx = '', i = 0;
        const parts = [];
        while (i < lines.length) {
            const l = lines[i];
            if (l.startsWith('Empresa:')) {
                ctx = 'empresa';
                const nomeEmp = l.replace(/^Empresa:\s*/, '');
                // Consome endereço da empresa → flex: endereço tem prioridade, empresa trunca
                let endPart = '';
                if (i + 1 < lines.length && lines[i + 1].startsWith('Endereço:')) {
                    const endVal = lines[i + 1].replace(/^Endereço:\s*/, '');
                    endPart = `<span style="flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:11px;font-weight:400;color:#1a237e;"> · ${escapeHtml(endVal)}</span>`;
                    i++;
                }
                parts.push(`<div style="display:flex;overflow:hidden;align-items:baseline;margin-bottom:2px;"><span style="flex:0 2 auto;min-width:0;max-width:42%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:11.5px;font-weight:800;color:#01579b;">${escapeHtml(nomeEmp)}</span>${endPart}</div>`);
                i++; continue;
            }
            if (l.startsWith('Sócio desta empresa:')) {
                ctx = 'socio';
                const val = l.replace(/^Sócio desta empresa:\s*/, '');
                parts.push(`<div style="${S.socio}">Sócio: ${escapeHtml(val)}</div>`);
                i++; continue;
            }
            if (l.startsWith('Nome:')) {
                ctx = 'pf';
                const nome = l.replace(/^Nome:\s*/, '');
                let cpfSpan = '';
                if (i + 1 < lines.length && lines[i + 1].startsWith('CPF:')) {
                    const cpfVal = lines[i + 1].replace(/^CPF:\s*/, '');
                    cpfSpan = ` &nbsp;<span style="font-weight:600;color:#6a1b9a;font-size:10.5px;">CPF: ${escapeHtml(cpfVal)}</span>`;
                    i++;
                }
                parts.push(`<div style="${S.pf}">PESSOA FÍSICA: ${escapeHtml(nome)}${cpfSpan}</div>`);
                i++; continue;
            }
            if (l.startsWith('CPF:')) {
                parts.push(`<div style="font-size:10.5px;color:#555;padding-left:10px;${nw}">${escapeHtml(l)}</div>`);
                i++; continue;
            }
            if (l.startsWith('Endereço:')) {
                const val = l.replace(/^Endereço:\s*/, '');
                const st = ctx === 'socio' ? S.endSocio : S.endPf;
                parts.push(`<div data-fit="1" style="${st}">Endereço: ${escapeHtml(val)}</div>`);
                i++; continue;
            }
            parts.push(`<div style="font-size:11px;color:#333;${nw}">${escapeHtml(l)}</div>`);
            i++;
        }
        return `<div style="padding:4px 6px 3px;border-radius:5px;background:#f5f5f5;border:1px solid #ddd;margin-bottom:4px;">${parts.join('')}</div>`;
    }

    function fitTexts() {
        corpo.querySelectorAll('[data-fit]').forEach(el => {
            let fs = 11.5;
            el.style.fontSize = fs + 'px';
            const avail = (el.parentElement ? el.parentElement.offsetWidth : corpo.offsetWidth) - 14;
            while (el.scrollWidth > avail && fs > 7) {
                fs = Math.round((fs - 0.25) * 100) / 100;
                el.style.fontSize = fs + 'px';
            }
        });
    }

    function renderPage() {
        const slice = dadosRelatorio.slice(currentPage * CARDS_PER_PAGE, (currentPage + 1) * CARDS_PER_PAGE);
        corpo.innerHTML = slice.map(renderBlock).join('');
        fitTexts();
        const multi = totalPages > 1;
        paginacao.style.display = multi ? 'flex' : 'none';
        if (multi) {
            pageInfo.textContent = `${currentPage + 1} / ${totalPages}`;
            btnPrev.style.opacity = currentPage === 0 ? '0.35' : '1';
            btnPrev.disabled = currentPage === 0;
            btnNext.style.opacity = currentPage >= totalPages - 1 ? '0.35' : '1';
            btnNext.disabled = currentPage >= totalPages - 1;
        }
    }
    renderPage();

    // ── Collapse
    let recolhido = false;
    const toggleCorpo = () => {
        recolhido = !recolhido;
        corpo.style.display    = recolhido ? 'none' : '';
        paginacao.style.display = recolhido ? 'none' : (totalPages > 1 ? 'flex' : 'none');
        btnToggle.textContent  = recolhido ? '▼' : '▲';
    };
    btnToggle.onclick = toggleCorpo;
    titulo.onclick = toggleCorpo;

    // Drag
    let dragging = false, ox = 0, oy = 0;
    cab.addEventListener('mousedown', e => {
        if (e.target === btnToggle || e.target === btnX) return;
        dragging = true;
        const r = painel.getBoundingClientRect();
        ox = e.clientX - r.left; oy = e.clientY - r.top;
        cab.style.cursor = 'grabbing';
        e.preventDefault();
    });
    document.addEventListener('mousemove', e => {
        if (!dragging) return;
        painel.style.left = (e.clientX - ox) + 'px';
        painel.style.top  = (e.clientY - oy) + 'px';
        painel.style.right = 'auto';
    });
    document.addEventListener('mouseup', () => { dragging = false; cab.style.cursor = 'grab'; });
})();
