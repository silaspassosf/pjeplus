'use strict';

window.URL_BASE_CPF = 'https://pje.trt2.jus.br/infojud-frontend/pages/consulta-cpf/';
window.URL_BASE_CNPJ = 'https://pje.trt2.jus.br/infojud-frontend/pages/consulta-cnpj/';
window.GOD_KEY_STATUS = 'GOD_STATUS';
window.GOD_KEY_TIPO = 'GOD_TIPO_ORIGEM';

window.iniciarFluxoInfojud = function(modo) {
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
            const num = txt.replace(/\D/g, '');
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

window.processarProximoInfojud = function() {
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

window.highlightLinha = function(doc) {
    document.querySelectorAll('span.pec-formatacao-padrao-dados-parte').forEach(s => {
        if (s.textContent.replace(/\D/g, '') === doc) {
            const tr = s.closest('tr');
            if (tr) tr.style.backgroundColor = '#fff9c4';
        }
    });
}

window._godPollId = null;
window.monitorarSinaisInfojud = function() {
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

// UI functions (criarBotoesInfojud, exibirRelatorioFinalInfojud) are in infojud.ui.js

