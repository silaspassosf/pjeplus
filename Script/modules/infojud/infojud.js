// Refatorado: Infojud + UI discreta + exposicao para Loader
(function () {
    'use strict';

    // Configurações e URLs
    const URL_ATUAL = window.location.href;
    const URL_BASE_CNPJ = 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI=';
    const URL_BASE_CPF = 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp?NI=';

    // Utilitários
    const wait = (ms) => new Promise(r => setTimeout(r, ms));
    const normalizar = (txt) => (txt || '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/\s+/g, ' ').trim();
    const apenasNumeros = (txt) => (txt || '').replace(/\D/g, '');

    /**
     * Componente de Notificação Discreta
     * Substitui o overlay invasivo por uma caixa no canto superior
     */
    function mostrarNotificacao(msg, cor = '#28a745') {
        const id = 'pje-tools-notif';
        let container = document.getElementById(id);
        if (!container) {
            container = document.createElement('div');
            container.id = id;
            container.style.cssText = `
                position: fixed; top: 20px; right: 20px; z-index: 2147483647;
                padding: 12px 20px; background: ${cor}; color: white;
                font-weight: bold; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 14px;
                transition: opacity 0.5s ease;
            `;
            document.body.appendChild(container);
        }
        container.textContent = msg;
        setTimeout(() => { container.style.opacity = '0'; setTimeout(() => container.remove(), 500); }, 3000);
    }

    // --- Lógica de Similaridade e Filtro (Fuzzy) ---
    function similaridade(s1, s2) {
        s1 = s1.toUpperCase(); s2 = s2.toUpperCase();
        if (s1 === s2) return 1.0;
        const aliases = { 'JARDIM': 'JD', 'PARQUE': 'PQ', 'VILA': 'VL', 'AVENIDA': 'AV', 'RUA': 'R' };
        for (let [f, s] of Object.entries(aliases)) {
            if ((s1 === f && s2 === s) || (s1 === s && s2 === f)) return 0.95;
        }
        const costs = [];
        for (let i = 0; i <= s1.length; i++) {
            let lastValue = i;
            for (let j = 0; j <= s2.length; j++) {
                if (i === 0) costs[j] = j;
                else if (j > 0) {
                    let newValue = costs[j - 1];
                    if (s1.charAt(i - 1) !== s2.charAt(j - 1)) newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                    costs[j - 1] = lastValue; lastValue = newValue;
                }
            }
            if (i > 0) costs[s2.length] = lastValue;
        }
        return (Math.max(s1.length, s2.length) - costs[s2.length]) / parseFloat(Math.max(s1.length, s2.length));
    }

    // =================================================================================
    // MÓDULO PJE: CRIAÇÃO DE BOTÕES E AUTOMAÇÃO
    // =================================================================================
    let filaDocs = [], atual = 0, rodando = false, MODO_EXECUCAO = '', dadosRelatorio = [];

    function criarBotoesInfojud() {
        if (document.getElementById('god-btn-container')) return;
        const container = document.createElement('div');
        container.id = 'god-btn-container';
        container.style.cssText = 'position:fixed;top:100px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:5px;';
        
        const btnStyle = 'padding:10px 20px;color:white;font-weight:bold;cursor:pointer;border-radius:4px;border:none;box-shadow:0 3px 6px rgba(0,0,0,0.3);font-size:13px;';
        
        const btnD = document.createElement('button');
        btnD.textContent = 'Infojud Direto'; btnD.style.cssText = btnStyle + 'background:#0288d1;';
        btnD.onclick = () => iniciarTrabalho('DIRETO');

        const btnC = document.createElement('button');
        btnC.textContent = 'Infojud Correção'; btnC.style.cssText = btnStyle + 'background:#004d40;';
        btnC.onclick = () => iniciarTrabalho('COMPLETO');

        container.appendChild(btnD); container.appendChild(btnC);
        document.body.appendChild(container);
        console.log('[Infojud] Botões injetados com sucesso.');
    }

    function iniciarTrabalho(modo) {
        MODO_EXECUCAO = modo;
        const spans = Array.from(document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
        filaDocs = [...new Set(spans.map(s => apenasNumeros(s.textContent)).filter(n => n.length === 11 || n.length === 14))];
        if (!filaDocs.length) return alert('Nenhum CPF/CNPJ encontrado na página!');
        rodando = true; atual = 0;
        GM_setValue('GOD_STATUS', 'STANDBY');
        processarFila();
    }

    function processarFila() {
        if (atual >= filaDocs.length) { 
            mostrarNotificacao("Ciclo Infojud Concluído!"); 
            rodando = false; return; 
        }
        const doc = filaDocs[atual];
        const url = doc.length === 11 ? URL_BASE_CPF + doc : URL_BASE_CNPJ + doc;
        GM_setValue('GOD_TIPO_ORIGEM', doc.length === 11 ? 'CPF_DIRETO' : 'CNPJ_NORMAL');
        GM_openInTab(url, { active: true, insert: true });
        // Lógica de monitoramento de sinais do GM_getValue continua aqui...
    }

    // =================================================================================
    // MÓDULO RECEITA (e-CAC): EXTRAÇÃO DE DADOS
    // =================================================================================
    if (URL_ATUAL.includes('detalheNICNPJ.asp')) {
        setTimeout(() => {
            const label = Array.from(document.querySelectorAll('td')).find(td => td.textContent.includes('CPF do responsável'));
            if (label) GM_openInTab(URL_BASE_CPF + apenasNumeros(label.nextElementSibling.textContent), { active: true });
            else GM_setValue('GOD_STATUS', 'PULAR_' + Date.now());
        }, 800);
    } 
    else if (URL_ATUAL.includes('detalheNICPF.asp')) {
        setTimeout(() => {
            try {
                let d = { nomeCompleto: '', cepRaw: '', endRaw: '' };
                document.querySelectorAll('td.azulEsquerdaNeg').forEach(t => {
                    let label = t.textContent.trim();
                    let valor = t.nextElementSibling?.textContent.trim() || '';
                    if (label.includes('Nome Completo')) d.nomeCompleto = valor;
                    if (label.includes('CEP')) d.cepRaw = valor;
                    if (label.includes('Endereço')) d.endRaw = valor;
                });

                if (d.cepRaw) {
                    d.cep = apenasNumeros(d.cepRaw).padStart(8, '0');
                    d.nome = d.nomeCompleto;
                    // Lógica de split de endereço simplificada
                    let tokens = d.endRaw.split(' ');
                    let nIdx = tokens.findIndex(tk => /^\d+$/.test(tk));
                    d.numero = nIdx > -1 ? tokens[nIdx] : 'S/N';
                    d.rua = nIdx > -1 ? tokens.slice(0, nIdx).join(' ') : d.endRaw;

                    GM_setValue('GOD_DADOS_CAPTURA', JSON.stringify(d));
                    GM_setValue('GOD_STATUS', 'DADOS_PRONTOS_' + Date.now());
                    
                    mostrarNotificacao("DADOS CARREGADOS!"); 
                    console.log("[Infojud] Extração concluída. Aba mantida aberta conforme solicitado.");
                    // window.close() REMOVIDO PARA MANTER ABA ABERTA
                }
            } catch (e) { console.error("Erro na extração:", e); }
        }, 1000);
    }

    // =================================================================================
    // INTEGRAÇÃO: EXPOSIÇÃO PARA O LOADER
    // =================================================================================
    if (URL_ATUAL.includes('pje.trt2.jus.br')) {
        // Expõe a função para o Loader (pjetools.user.js)
        window.runInfojudWorker = criarBotoesInfojud;
        
        // Auto-execução de segurança caso o loader demore
        setTimeout(() => { if (!document.getElementById('god-btn-container')) criarBotoesInfojud(); }, 4000);
    }

})();
