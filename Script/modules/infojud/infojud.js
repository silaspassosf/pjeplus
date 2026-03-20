// Refatorado: Infojud + UI discreta + exposicao para Loader
(function () {
    'use strict';

    // ── Shim de GM APIs para execução via loader (page context) ──────
    const _gmSet    = (k, v) => localStorage.setItem(k, String(v));
    const _gmGet    = (k, d = null) => { const v = localStorage.getItem(k); return v !== null ? v : d; };
    const _gmOpenTab = (url, _opts) => window.open(url, '_blank');
    // ────────────────────────────────────────────────────────────────
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
        // Somente injetar botões na aba '/minutas'
        if (!URL_ATUAL.includes('/minutas')) return;
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
        _gmSet('GOD_STATUS', 'STANDBY');
        processarFila();
    }

    function processarFila() {
        if (atual >= filaDocs.length) { 
            mostrarNotificacao("Ciclo Infojud Concluído!"); 
            rodando = false; return; 
        }
        const doc = filaDocs[atual];
        const url = doc.length === 11 ? URL_BASE_CPF + doc : URL_BASE_CNPJ + doc;
        _gmSet('GOD_TIPO_ORIGEM', doc.length === 11 ? 'CPF_DIRETO' : 'CNPJ_NORMAL');
        _gmOpenTab(url, { active: true, insert: true });
        // Lógica de monitoramento de sinais do GM_getValue continua aqui...
    }

    // =================================================================================
    // MÓDULO RECEITA (e-CAC): EXTRAÇÃO DE DADOS
    // =================================================================================
    if (URL_ATUAL.includes('detalheNICNPJ.asp')) {
        setTimeout(() => {
            const label = Array.from(document.querySelectorAll('td')).find(td => td.textContent.includes('CPF do responsável'));
            if (label) _gmOpenTab(URL_BASE_CPF + apenasNumeros(label.nextElementSibling.textContent), { active: true });
            else _gmSet('GOD_STATUS', 'PULAR_' + Date.now());
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

                    _gmSet('GOD_DADOS_CAPTURA', JSON.stringify(d));
                    _gmSet('GOD_STATUS', 'DADOS_PRONTOS_' + Date.now());
                    
                    mostrarNotificacao("DADOS CARREGADOS!"); 
                    console.log("[Infojud] Extração concluída. Aba mantida aberta conforme solicitado.");
                    // window.close() REMOVIDO PARA MANTER ABA ABERTA
                }
            } catch (e) { console.error("Erro na extração:", e); }
        }, 1000);
    }

    // =================================================================================
    // INTEGRAÇÃO: EXPOSIÇÃO PARA O LOADER (Módulo PJe completo)
    // =================================================================================
    if (URL_ATUAL.includes('pje.trt2.jus.br')) {
        window.runInfojudWorker = function runInfojudWorker() {
            console.log('[GOD] runInfojudWorker inicializado.');

            // Variáveis locais/estado (reutilizam as globais onde aplicável)
            let filaDocsLocal = [];
            let atualLocal = 0;
            let rodandoLocal = false;
            let ultimoProcessadoLocal = '';
            let MODO_EXECUCAO_LOCAL = '';
            let dadosRelatorioLocal = [];

            function criarBotoesWrapper() {
                if (document.getElementById('god-btn-container')) return;
                criarBotoesInfojud();
            }

            function iniciarFluxoLocal(modo) {
                MODO_EXECUCAO_LOCAL = modo;
                const spans = Array.from(document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
                filaDocsLocal = [];
                dadosRelatorioLocal = [];
                const vistos = new Set();
                spans.forEach(s => {
                    let txt = s.textContent.trim();
                    if (/\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/.test(txt)) {
                        let num = txt.replace(/\D/g, '');
                        if (!vistos.has(num)) { vistos.add(num); filaDocsLocal.push(num); }
                    }
                });

                if (!filaDocsLocal.length) return alert('Nenhum documento encontrado!');

                const oldR = document.getElementById('god-relatorio-panel');
                if (oldR) oldR.remove();

                rodandoLocal = true; atualLocal = 0; ultimoProcessadoLocal = '';
                _gmSet('GOD_STATUS', 'STANDBY');

                console.log(`[GOD] Iniciando Modo: ${MODO_EXECUCAO_LOCAL}`);
                monitorarSinaisLocal();
                processarProximoLocal();
            }

            function processarProximoLocal() {
                if (atualLocal >= filaDocsLocal.length) {
                    console.log('[GOD] Ciclo finalizado!');
                    salvarGeralFinalLocal();
                    exibirRelatorioFinalLocal();
                    rodandoLocal = false; return;
                }

                const doc = filaDocsLocal[atualLocal];
                const linha = encontrarLinhaPorDocLocal(doc);
                if (linha) { linha.style.backgroundColor = '#fff9c4'; linha.scrollIntoView({ block: 'center', behavior: 'smooth' }); }

                if (doc.length === 11) {
                    _gmSet('GOD_TIPO_ORIGEM', 'CPF_DIRETO');
                    _gmOpenTab(URL_BASE_CPF + doc, { active: true, insert: true });
                } else {
                    _gmSet('GOD_TIPO_ORIGEM', 'CNPJ_NORMAL');
                    _gmOpenTab(URL_BASE_CNPJ + doc, { active: true, insert: true });
                }
            }

            function encontrarLinhaPorDocLocal(docNumerico) {
                const spans = Array.from(document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
                for (let s of spans) {
                    if (s.textContent.replace(/\D/g, '') === docNumerico) return s.closest('tr');
                }
                return null;
            }

            function monitorarSinaisLocal() {
                if (!rodandoLocal) return;
                const status = _gmGet('GOD_STATUS', '');

                if (status.startsWith('DADOS_PRONTOS_')) {
                    const id = status.split('_')[2];
                    if (id !== ultimoProcessadoLocal) { ultimoProcessadoLocal = id; aplicarLogicaMasterLocal(); }
                } else if (status.startsWith('PULAR_')) {
                    const id = status.split('_')[1];
                    if (id !== ultimoProcessadoLocal) {
                        ultimoProcessadoLocal = id;
                        const linha = encontrarLinhaPorDocLocal(filaDocsLocal[atualLocal]);
                        if (linha) linha.style.backgroundColor = '#ffccbc';
                        atualLocal++; setTimeout(processarProximoLocal, 1000);
                    }
                }
                setTimeout(monitorarSinaisLocal, 500);
            }

            async function verificarExistenciaNaTabelaLocal(d) {
                const tabela = document.querySelector('pje-data-table[nametabela="Endereços do destinatário no sistema"] table') ||
                    document.querySelector('table[name="Endereços do destinatário no sistema"]');
                if (!tabela) { console.log('[GOD] Tabela de endereços não encontrada.'); return false; }
                const linhas = Array.from(tabela.querySelectorAll('tbody tr'));

                for (let tr of linhas) {
                    const colunas = tr.querySelectorAll('td'); if (colunas.length < 5) continue;
                    const cepTabela = apenasNumeros(colunas[1].textContent);
                    const ruaTabela = normalizar(colunas[2].textContent);
                    const numTabela = normalizar(colunas[3].textContent);

                    const cepNovo = d.cep; const ruaNova = normalizar(d.rua || d.endRaw); const numNovo = normalizar(d.numero);
                    const matchCep = cepTabela === cepNovo; const matchNum = numTabela === numNovo || (numNovo === 'SN' && numTabela === 'S/N');
                    const simRua = similaridade(ruaTabela, ruaNova); const matchRua = simRua > 0.8 || ruaTabela.includes(ruaNova) || ruaNova.includes(ruaTabela);

                    if (matchCep && matchNum && matchRua) {
                        console.log(`[GOD] ENDEREÇO JÁ EXISTE! Usando linha da tabela. (Sim: ${simRua.toFixed(2)})`);
                        const btnSeta = colunas[0].querySelector('.fa-arrow-up');
                        if (btnSeta) { (btnSeta.closest('button') || btnSeta).click(); return true; }
                    }
                }
                console.log('[GOD] Endereço não encontrado na tabela. Cadastrando novo...'); return false;
            }

            async function aplicarLogicaMasterLocal() {
                try {
                    const docAtual = filaDocsLocal[atualLocal];
                    const linha = encontrarLinhaPorDocLocal(docAtual); if (!linha) throw new Error('Linha não encontrada');
                    const btnEnvelope = linha.querySelector('.fa-envelope'); if (!btnEnvelope) throw new Error('Envelope sumiu');

                    const d = JSON.parse(_gmGet('GOD_DADOS_CAPTURA', '{}'));
                    const nomes = (d.nome || '').split(' '); const nomeFmt = nomes.length > 1 ? `${nomes[0]} ${nomes[1]}` : nomes[0];
                    const linhaRel = `(${nomeFmt}) - (${d.cep}) - (${d.rua || ''} ${d.numero || 'S/N'}) - (${d.complemento || ''})`;
                    dadosRelatorioLocal.push(linhaRel.replace(/\s+/g, ' '));

                    btnEnvelope.click(); await esperarModalLocal('mat-dialog-container'); await wait(1500);

                    const jaExiste = await verificarExistenciaNaTabelaLocal(d);
                    if (jaExiste) {
                        await wait(1000);
                        const btnSalvar = document.querySelector('.botao-salvar') || document.querySelector('button[mattooltip="Salva as alterações"]');
                        if (btnSalvar && document.body.contains(btnSalvar)) btnSalvar.click();
                    } else {
                        let cep = document.querySelector('#inputCep');
                        if (cep) {
                            const cVal = d.cep; cep.value = ''; cep.click(); cep.focus();
                            for (let i = 0; i < cVal.length; i++) { await wait(50); cep.value += cVal[i]; cep.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true })); cep.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: cVal[i] })); cep.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true })); }
                        }
                        await wait(1500);
                        let cepFmt = d.cep.substring(0, 5) + '-' + d.cep.substring(5);
                        let opt = Array.from(document.querySelectorAll('mat-option')).find(o => o.textContent.includes(cepFmt)); if (opt) opt.click();
                        await wait(2000);
                        let complFinal = d.complemento || ''; const inputBairro = document.querySelector('#inputBairro'); if (inputBairro && inputBairro.value) complFinal = limparBairroFuzzy(complFinal, inputBairro.value);
                        let n = document.querySelector('#inputNumero'); let c = document.querySelector('#inputComplemento'); if (n) { n.value = d.numero || ''; n.dispatchEvent(new Event('input', { bubbles: true })); } if (c) { c.value = complFinal; c.dispatchEvent(new Event('input', { bubbles: true })); }
                        await wait(500);
                        const btnSalvar = document.querySelector('.botao-salvar') || document.querySelector('button[mattooltip="Salva as alterações"]'); if (btnSalvar) btnSalvar.click();
                    }

                    await wait(1500);
                    const btnFechar = document.querySelector('.fa-window-close') || document.querySelector('.btn-fechar'); if (btnFechar && document.querySelector('mat-dialog-container')) btnFechar.click();
                    for (let i = 0; i < 30; i++) { if (!document.querySelector('mat-dialog-container')) break; await wait(300); }
                    await wait(500);

                    if (MODO_EXECUCAO_LOCAL === 'COMPLETO') {
                        let ruaAlvo = normalizar(d.rua || d.endRaw).split(',')[0].trim();
                        if (ruaAlvo) {
                            const icones = Array.from(document.querySelectorAll('.pec-icone-verde-endereco-tabela-destinatarios'));
                            const alvo = icones.find(icone => normalizar(icone.getAttribute('aria-label') || '').includes(ruaAlvo));
                            if (alvo) { const tr = alvo.closest('tr'); const btnEdit = tr.querySelector('.fa-edit'); if (btnEdit) { (btnEdit.closest('button') || btnEdit).click(); await wait(800); } }
                        }

                        console.log('[GOD] Completo: Editando minuta...');
                        const btnConfec = document.querySelector('button[aria-label="Confeccionar ato"]');
                        if (btnConfec) {
                            btnConfec.click();
                            let editorCarregou = false; for (let i = 0; i < 50; i++) { if (document.querySelector('.ck-editor__editable')) { editorCarregou = true; break; } await wait(200); }
                            if (editorCarregou) {
                                await wait(500);
                                const editor = document.querySelector('.ck-editor__editable');
                                let ckInstance = editor.ckeditorInstance || (editor.closest('.ck-editor') ? editor.closest('.ck-editor').ckeditorInstance : null);
                                const variavelPJe = '#{processo.comunicacaoProcessual.enderecoDestinatario}';
                                let html = ckInstance ? ckInstance.getData() : editor.innerHTML;
                                const regex = /(<strong>\s*ENDEREÇO:\s*)([\s\S]*?)(<\/strong>)/gi;
                                if (regex.test(html)) { const novoHtml = html.replace(regex, `$1${variavelPJe}$3`); if (ckInstance) ckInstance.setData(novoHtml); else { editor.innerHTML = novoHtml; editor.dispatchEvent(new InputEvent('input', { bubbles: true })); } }
                                await wait(500);
                                const btnPena = document.querySelector('button[aria-label="Finalizar minuta"]') || document.querySelector('.fa-pen-nib')?.closest('button'); if (btnPena) btnPena.click(); await wait(1000);
                            }
                        }
                    } else { console.log('[GOD] Modo Direto: Fim do ciclo.'); }

                    linha.style.backgroundColor = '#c8e6c9'; atualLocal++; setTimeout(processarProximoLocal, 800);
                } catch (e) {
                    console.error('[GOD] Erro:', e);
                    const l = encontrarLinhaPorDocLocal(filaDocsLocal[atualLocal]); if (l) l.style.backgroundColor = '#ef5350'; atualLocal++; setTimeout(processarProximoLocal, 1500);
                }
            }

            async function salvarGeralFinalLocal() { const btn = document.querySelector('button[aria-label="Salva os expedientes"]'); if (btn && !btn.disabled) btn.click(); }

            function exibirRelatorioFinalLocal() {
                const painel = document.createElement('div'); painel.id = 'god-relatorio-panel'; painel.style.cssText = `position: fixed; bottom: 80px; left: 20px; background: white; border: 2px solid #004d40; padding: 10px; z-index: 10000; width: 600px; max-height: 400px; overflow-y: auto; box-shadow: 0 5px 20px rgba(0,0,0,0.4); border-radius: 6px; font-family: 'Segoe UI', sans-serif; font-size: 12px;`;
                const cabecalho = document.createElement('div'); cabecalho.innerHTML = '<strong>RELATÓRIO DE ENDEREÇOS</strong> <span style="float:right;cursor:pointer;font-weight:bold" onclick="this.parentElement.parentElement.remove()">[X]</span>'; cabecalho.style.borderBottom = '1px solid #ccc'; cabecalho.style.marginBottom = '10px'; painel.appendChild(cabecalho);
                const contentDiv = document.createElement('div'); contentDiv.style.cssText = `width: 100%; white-space: pre-wrap; word-break: break-all; user-select: text; border: 1px solid #ddd; padding: 8px; background: #f9f9f9; font-family: monospace; font-size: 11px; color: #333;`;
                contentDiv.textContent = dadosRelatorioLocal.join('\n'); painel.appendChild(contentDiv); document.body.appendChild(painel);
            }

            function esperarModalLocal(classe) {
                return new Promise((resolve, reject) => {
                    let k = 0; const i = setInterval(() => { if (document.querySelector(classe)) { clearInterval(i); resolve(); } k++; if (k > 50) { clearInterval(i); reject('Timeout Modal'); } }, 200);
                });
            }

            // expõe handlers de UI
            // Substitui os botões para utilizar o fluxo local quando clicados
            criarBotoesWrapper();
            const btnContainer = document.getElementById('god-btn-container');
            if (btnContainer) {
                const btns = btnContainer.querySelectorAll('button');
                if (btns[0]) btns[0].onclick = () => iniciarFluxoLocal('DIRETO');
                if (btns[1]) btns[1].onclick = () => iniciarFluxoLocal('COMPLETO');
            }

            // Auto-reativar se os botões não surgirem
            window.addEventListener('load', criarBotoesWrapper);
        };

        // Auto-execução de segurança caso o loader demore
        setTimeout(() => { if (!document.getElementById('god-btn-container')) window.runInfojudWorker(); }, 4000);
    }

})();
