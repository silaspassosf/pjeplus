'use strict';

// ── UI: Botões e Painéis ─────────────────────────────────────────

function criarBotoesInfojud() {
    document.getElementById('god-btns')?.remove();
    const container = document.createElement('div');
    container.id = 'god-btns';
    container.style.cssText = `position:fixed;top:100px;right:20px;z-index:9999;` +
        `display:flex;flex-direction:column;gap:5px;`;
    const styleBtn = 'padding:10px 20px;color:white;font-weight:bold;cursor:pointer;' +
        'border-radius:4px;box-shadow:0 3px 6px rgba(0,0,0,.3);font-size:14px;border:none;';
    const btnD = document.createElement('button');
    btnD.textContent = 'Infojud Direto';
    btnD.style.cssText = styleBtn + 'background:#0288d1;';
    btnD.onclick = () => iniciarFluxoInfojud('DIRETO');
    const btnC = document.createElement('button');
    btnC.textContent = 'Infojud Correção';
    btnC.style.cssText = styleBtn + 'background:#004d40;';
    btnC.onclick = () => iniciarFluxoInfojud('COMPLETO');
    container.appendChild(btnD);
    container.appendChild(btnC);
    document.body.appendChild(container);
    PJeState.registry.add(() => container.remove());
}

function exibirRelatorioFinalInfojud() {
    playBeep();
    const painel = document.createElement('div');
    painel.id = 'god-relatorio-panel';
    painel.style.cssText = `position:fixed;bottom:80px;left:20px;background:white;` +
        `border:2px solid #004d40;padding:10px;z-index:10000;width:600px;` +
        `max-height:400px;overflow-y:auto;box-shadow:0 5px 20px rgba(0,0,0,.4);` +
        `border-radius:6px;font-family:'Segoe UI',sans-serif;font-size:12px;`;
    const cab = document.createElement('div');
    cab.innerHTML = `<strong>RELATÓRIO INFOJUD</strong>` +
        `<span style="float:right;cursor:pointer;font-weight:bold" ` +
        `onclick="this.closest('#god-relatorio-panel').remove()">[X]</span>`;
    cab.style.borderBottom = '1px solid #ccc';
    cab.style.marginBottom = '10px';
    painel.appendChild(cab);

    const content = document.createElement('div');
    content.textContent = `${PJeState.infojud.fila.length} documento(s) processado(s).`;
    painel.appendChild(content);
    document.body.appendChild(painel);
    showToast(`✅ Infojud concluído: ${PJeState.infojud.fila.length} doc(s)`, '#4caf50', 6000);
}
