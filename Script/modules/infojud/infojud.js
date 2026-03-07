'use strict';

const URL_BASE_CPF  = 'https://pje.trt2.jus.br/infojud-frontend/pages/consulta-cpf/';
const URL_BASE_CNPJ = 'https://pje.trt2.jus.br/infojud-frontend/pages/consulta-cnpj/';
const GOD_KEY_STATUS = 'GOD_STATUS';
const GOD_KEY_TIPO   = 'GOD_TIPO_ORIGEM';

function iniciarFluxoInfojud(modo) {
    const state = PJeState.infojud;

    if (state.runner.running) {
        alert('Infojud já está rodando. Aguarde ou recarregue a página.');
        return;
    }

    // Coletar CPF/CNPJ da tela
    const spans = Array.from(
        document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
    const vistos = new Set();
    state.fila = [];
    state.dados = [];
    state.atual = 0;
    state.modo = modo;

    spans.forEach(s => {
        const txt = s.textContent.trim();
        if (/\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/.test(txt)) {
            const num = txt.replace(/\D/g,'');
            if (!vistos.has(num)) { vistos.add(num); state.fila.push(num); }
        }
    });

    if (!state.fila.length) { alert('Nenhum CPF/CNPJ encontrado na tela!'); return; }

    // Remover relatório anterior
    document.getElementById('god-relatorio-panel')?.remove();

    GM_setValue(GOD_KEY_STATUS, 'STANDBY');
    showToast(`Infojud ${modo}: ${state.fila.length} doc(s)`, '#0288d1');
    criarBotoesInfojud();
    monitorarSinaisInfojud();
    processarProximoInfojud();
}

function processarProximoInfojud() {
    const state = PJeState.infojud;
    if (state.atual >= state.fila.length) {
        console.log('[GOD] Ciclo finalizado');
        exibirRelatorioFinalInfojud();
        return;
    }

    const doc = state.fila[state.atual];
    highlightLinha(doc);

    if (doc.length === 11) {
        GM_setValue(GOD_KEY_TIPO, 'CPF_DIRETO');
        GM_openInTab(URL_BASE_CPF + doc, { active: true, insert: true });
    } else {
        GM_setValue(GOD_KEY_TIPO, 'CNPJ_DIRETO');
        GM_openInTab(URL_BASE_CNPJ + doc, { active: true, insert: true });
    }
}

function highlightLinha(doc) {
    document.querySelectorAll('span.pec-formatacao-padrao-dados-parte').forEach(s => {
        if (s.textContent.replace(/\D/g,'') === doc) {
            const tr = s.closest('tr');
            if (tr) tr.style.backgroundColor = '#fff9c4';
        }
    });
}

let _godPollId = null;
function monitorarSinaisInfojud() {
    if (_godPollId) clearInterval(_godPollId);
    _godPollId = setInterval(() => {
        const status = GM_getValue(GOD_KEY_STATUS);
        if (status === 'STANDBY') return;
        const state = PJeState.infojud;
        if (status === 'DONE' || status === 'ERROR') {
            clearInterval(_godPollId);
            _godPollId = null;
            const linha = state.fila[state.atual];
            const tr = document.querySelector(`span.pec-formatacao-padrao-dados-parte`)
                ?.closest('tr');
            if (tr) tr.style.backgroundColor = status === 'DONE' ? '#c8e6c9' : '#ef9a9a';
            state.atual++;
            GM_setValue(GOD_KEY_STATUS, 'STANDBY');
            setTimeout(() => {
                monitorarSinaisInfojud();
                processarProximoInfojud();
            }, 800);
        }
    }, 1000);
    // Registrar limpeza no registry
    PJeState.registry.add(() => {
        if (_godPollId) { clearInterval(_godPollId); _godPollId = null; }
    });
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