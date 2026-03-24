// Módulo Infojud Pro - Integrado ao PJeTools
(function () {
    'use strict';

    // ── Compatibilidade de contexto para GM APIs ──────
    const _gmSet = (k, v) => localStorage.setItem(k, String(v));
    const _gmGet = (k, d = null) => { const v = localStorage.getItem(k); return v !== null ? v : d; };
    const _gmOpenTab = (url, _opts) => window.open(url, '_blank');
    // ────────────────────────────────────────────────────────────────

    const URL_ATUAL = window.location.href;
    const URL_BASE_CNPJ = 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI=';
    const URL_BASE_CPF = 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp?NI=';

    const wait = (ms) => new Promise(r => setTimeout(r, ms));
    const normalizar = (txt) => (txt || '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/\s+/g, ' ').trim();
    const apenasNumeros = (txt) => (txt || '').replace(/\D/g, '');

    function mostrarNotificacao(msg, cor = '#28a745', persistente = false) {
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
        container.style.opacity = '1';
        container.textContent = msg;

        if (!persistente) {
            setTimeout(() => { 
                container.style.opacity = '0'; 
                setTimeout(() => container.remove(), 500); 
            }, 3000);
        }
    }

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

    function limparBairroFuzzy(complemento, bairroPJe) {
        if (!bairroPJe || !complemento) return complemento;
        const palavrasBairro = normalizar(bairroPJe).split(' ');
        const palavrasComp = normalizar(complemento).split(/[\s,\.-]+/);
        for (let i = 0; i <= palavrasComp.length - palavrasBairro.length; i++) {
            let matchCount = 0;
            for (let j = 0; j < palavrasBairro.length; j++) {
                if (similaridade(palavrasComp[i + j], palavrasBairro[j]) > 0.8) matchCount++;
            }
            if (matchCount / palavrasBairro.length > 0.7) {
                const trechoEncontrado = palavrasComp.slice(i, i + palavrasBairro.length).join('.*?');
                const regexRemove = new RegExp(trechoEncontrado + '.*?(\\s|$)', 'i');
                return complemento.replace(regexRemove, '').trim().replace(/^[-, \.\s]+/, '');
            }
        }
        return complemento;
    }

    // =================================================================================
    // PARTE 1: EXPOSIÇÃO PARA O PJE TOOLS (Módulo PJe)
    // =================================================================================
    window.runInfojudWorker = function() {
        if (!URL_ATUAL.includes('pje.trt2.jus.br') || !URL_ATUAL.includes('/minutas')) return;
        
        console.log('[Infojud] runInfojudWorker orquestrado pelo PJeTools.');

        let filaDocs = [];
        let atual = 0;
        let rodando = false;
        let ultimoProcessado = '';
        let MODO_EXECUCAO = '';
        let dadosRelatorio = [];

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
        }

        function iniciarTrabalho(modo) {
            MODO_EXECUCAO = modo;
            const spans = Array.from(document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
            filaDocs = [...new Set(spans.map(s => apenasNumeros(s.textContent)).filter(n => n.length === 11 || n.length === 14))];
            
            if (!filaDocs.length) return alert('Nenhum documento encontrado na página!');
            
            const oldR = document.getElementById('god-relatorio-panel');
            if(oldR) oldR.remove();

            rodando = true; atual = 0; ultimoProcessado = ''; dadosRelatorio = [];
            _gmSet('GOD_STATUS', 'STANDBY');
            
            mostrarNotificacao(`Iniciando Modo: ${MODO_EXECUCAO}`, '#0288d1');
            monitorarSinais();
            processarProximo();
        }

        function processarProximo() {
            if (atual >= filaDocs.length) {
                mostrarNotificacao("Ciclo Infojud Finalizado!", '#28a745', true);
                salvarGeralFinal();
                exibirRelatorioFinal();
                rodando = false; 
                return;
            }

            const doc = filaDocs[atual];
            const linha = encontrarLinhaPorDoc(doc);
            if (linha) {
                linha.style.backgroundColor = '#fff9c4';
                linha.scrollIntoView({block: 'center', behavior: 'smooth'});
            }

            if (doc.length === 11) {
                _gmSet('GOD_TIPO_ORIGEM', 'CPF_DIRETO');
                _gmOpenTab(URL_BASE_CPF + doc, { active: true, insert: true });
            } else {
                _gmSet('GOD_TIPO_ORIGEM', 'CNPJ_NORMAL');
                _gmOpenTab(URL_BASE_CNPJ + doc, { active: true, insert: true });
            }
        }

        function encontrarLinhaPorDoc(docNumerico) {
            const spans = Array.from(document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
            for (let s of spans) {
                if (s.textContent.replace(/\D/g, '') === docNumerico) return s.closest('tr');
            }
            return null;
        }

        function monitorarSinais() {
            if (!rodando) return;
            const status = _gmGet('GOD_STATUS', '');

            if (status.startsWith('DADOS_PRONTOS_')) {
                const id = status.split('_')[2];
                if (id !== ultimoProcessado) {
                    ultimoProcessado = id;
                    aplicarLogicaMaster();
                }
            } else if (status.startsWith('PULAR_')) {
                const id = status.split('_')[1];
                if (id !== ultimoProcessado) {
                    ultimoProcessado = id;
                    const linha = encontrarLinhaPorDoc(filaDocs[atual]);
                    if (linha) linha.style.backgroundColor = '#ffccbc';
                    atual++;
                    setTimeout(processarProximo, 1000);
                }
            }
            setTimeout(monitorarSinais, 500);
        }

        async function verificarExistenciaNaTabela(d) {
            const tabela = document.querySelector('pje-data-table[nametabela="Endereços do destinatário no sistema"] table') ||
                           document.querySelector('table[name="Endereços do destinatário no sistema"]');
            if (!tabela) return false;

            const linhas = Array.from(tabela.querySelectorAll('tbody tr'));
            for (let tr of linhas) {
                const colunas = tr.querySelectorAll('td');
                if (colunas.length < 5) continue;

                const cepTabela = apenasNumeros(colunas[1].textContent);
                const ruaTabela = normalizar(colunas[2].textContent);
                const numTabela = normalizar(colunas[3].textContent);

                const cepNovo = d.cep;
                const ruaNova = normalizar(d.rua || d.endRaw);
                const numNovo = normalizar(d.numero);

                const matchCep = cepTabela === cepNovo;
                const matchNum = numTabela === numNovo || (numNovo === 'SN' && numTabela === 'S/N');
                const simRua = similaridade(ruaTabela, ruaNova);
                const matchRua = simRua > 0.8 || ruaTabela.includes(ruaNova) || ruaNova.includes(ruaTabela);

                if (matchCep && matchNum && matchRua) {
                    const btnSeta = colunas[0].querySelector('.fa-arrow-up');
                    if (btnSeta) {
                        (btnSeta.closest('button') || btnSeta).click();
                        return true;
                    }
                }
            }
            return false;
        }

        async function aplicarLogicaMaster() {
            try {
                const docAtual = filaDocs[atual];
                const linha = encontrarLinhaPorDoc(docAtual);
                if (!linha) throw new Error(`Linha não encontrada`);

                const btnEnvelope = linha.querySelector('.fa-envelope');
                if (!btnEnvelope) throw new Error('Envelope sumiu');

                const d = JSON.parse(_gmGet('GOD_DADOS_CAPTURA', '{}'));
                const nomes = (d.nome || '').split(' ');
                const nomeFmt = nomes.length > 1 ? `${nomes[0]} ${nomes[1]}` : nomes[0];
                dadosRelatorio.push(`(${nomeFmt}) - (${d.cep}) - (${d.rua || ''} ${d.numero || 'S/N'}) - (${d.complemento || ''})`.replace(/\s+/g, ' '));

                btnEnvelope.click();
                await esperarModal('mat-dialog-container');
                await wait(1500); 

                const jaExiste = await verificarExistenciaNaTabela(d);

                if (jaExiste) {
                    await wait(1000);
                    const btnSalvar = document.querySelector('.botao-salvar') || document.querySelector('button[mattooltip="Salva as alterações"]');
                    if (btnSalvar && document.body.contains(btnSalvar)) btnSalvar.click();
                } else {
                    let cep = document.querySelector('#inputCep');
                    if (cep) {
                        const cVal = d.cep;
                        cep.value = ''; cep.click(); cep.focus();
                        for (let i = 0; i < cVal.length; i++) {
                            await wait(50);
                            cep.value += cVal[i];
                            cep.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
                            cep.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: cVal[i] }));
                            cep.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                        }
                    }

                    await wait(1500);
                    let cepFmt = d.cep.substring(0, 5) + '-' + d.cep.substring(5);
                    let opt = Array.from(document.querySelectorAll('mat-option')).find(o => o.textContent.includes(cepFmt));
                    if (opt) opt.click();

                    await wait(2000);
                    let complFinal = d.complemento || '';
                    const inputBairro = document.querySelector('#inputBairro');
                    if (inputBairro && inputBairro.value) complFinal = limparBairroFuzzy(complFinal, inputBairro.value);

                    let n = document.querySelector('#inputNumero');
                    let c = document.querySelector('#inputComplemento');
                    if (n) { n.value = d.numero || ''; n.dispatchEvent(new Event('input', { bubbles: true })); }
                    if (c) { c.value = complFinal; c.dispatchEvent(new Event('input', { bubbles: true })); }

                    await wait(500);
                    const btnSalvar = document.querySelector('.botao-salvar') || document.querySelector('button[mattooltip="Salva as alterações"]');
                    if (btnSalvar) btnSalvar.click();
                }
               
                await wait(1500);
                const btnFechar = document.querySelector('.fa-window-close') || document.querySelector('.btn-fechar');
                if (btnFechar && document.querySelector('mat-dialog-container')) btnFechar.click();

                for(let i=0; i<30; i++) {
                    if(!document.querySelector('mat-dialog-container')) break;
                    await wait(300);
                }
                await wait(500);

                if (MODO_EXECUCAO === 'COMPLETO') {
                    let ruaAlvo = normalizar(d.rua || d.endRaw).split(',')[0].trim();
                    if (ruaAlvo) {
                        const icones = Array.from(document.querySelectorAll('.pec-icone-verde-endereco-tabela-destinatarios'));
                        const alvo = icones.find(icone => normalizar(icone.getAttribute('aria-label') || '').includes(ruaAlvo));
                        if (alvo) {
                            const tr = alvo.closest('tr');
                            const btnEdit = tr.querySelector('.fa-edit');
                            if (btnEdit) { (btnEdit.closest('button') || btnEdit).click(); await wait(800); }
                        }
                    }

                    const btnConfec = document.querySelector('button[aria-label="Confeccionar ato"]');
                    if (btnConfec) {
                        btnConfec.click();
                        let editorCarregou = false;
                        for(let i=0; i<50; i++) {
                            if(document.querySelector('.ck-editor__editable')) { editorCarregou = true; break; }
                            await wait(200);
                        }

                        if(editorCarregou) {
                            await wait(500);
                            const editor = document.querySelector('.ck-editor__editable');
                            let ckInstance = editor.ckeditorInstance || (editor.closest('.ck-editor') ? editor.closest('.ck-editor').ckeditorInstance : null);
                            const variavelPJe = '#{processo.comunicacaoProcessual.enderecoDestinatario}';
                            let html = ckInstance ? ckInstance.getData() : editor.innerHTML;
                           
                            const regex = /(<strong>\s*ENDEREÇO:\s*)([\s\S]*?)(<\/strong>)/gi;
                            if (regex.test(html)) {
                                const novoHtml = html.replace(regex, `$1${variavelPJe}$3`);
                                if (ckInstance) ckInstance.setData(novoHtml);
                                else { editor.innerHTML = novoHtml; editor.dispatchEvent(new InputEvent('input', { bubbles: true })); }
                            }
                            await wait(500);

                            const btnPena = document.querySelector('button[aria-label="Finalizar minuta"]') || document.querySelector('.fa-pen-nib')?.closest('button');
                            if (btnPena) btnPena.click();
                            await wait(1000);
                        }
                    }
                }

                linha.style.backgroundColor = '#c8e6c9';
                atual++;
                setTimeout(processarProximo, 800);

            } catch (e) {
                console.error('[Infojud Error]', e);
                const l = encontrarLinhaPorDoc(filaDocs[atual]);
                if (l) l.style.backgroundColor = '#ef5350';
                atual++;
                setTimeout(processarProximo, 1500);
            }
        }

        async function salvarGeralFinal() {
            const btn = document.querySelector('button[aria-label="Salva os expedientes"]');
            if (btn && !btn.disabled) btn.click();
        }

        function exibirRelatorioFinal() {
            const painel = document.createElement('div');
            painel.id = 'god-relatorio-panel';
            painel.style.cssText = `
                position: fixed; bottom: 80px; left: 20px;
                background: white; border: 2px solid #004d40;
                padding: 10px; z-index: 10000;
                width: 600px; max-height: 400px;
                overflow-y: auto; box-shadow: 0 5px 20px rgba(0,0,0,0.4);
                border-radius: 6px; font-family: 'Segoe UI', sans-serif; font-size: 12px;
            `;

            const cabecalho = document.createElement('div');
            cabecalho.innerHTML = '<strong>RELATÓRIO DE ENDEREÇOS</strong> <span style="float:right;cursor:pointer;font-weight:bold" onclick="this.parentElement.parentElement.remove()">[X]</span>';
            cabecalho.style.borderBottom = '1px solid #ccc';
            cabecalho.style.marginBottom = '10px';
            painel.appendChild(cabecalho);

            const contentDiv = document.createElement('div');
            contentDiv.style.cssText = `
                width: 100%; white-space: pre-wrap; word-break: break-all;
                user-select: text; border: 1px solid #ddd; padding: 8px; background: #f9f9f9;
                font-family: monospace; font-size: 11px; color: #333;
            `;
            contentDiv.textContent = dadosRelatorio.join('\n');
           
            painel.appendChild(contentDiv);
            document.body.appendChild(painel);
        }

        function esperarModal(classe) {
            return new Promise((resolve, reject) => {
                let k = 0;
                const i = setInterval(() => {
                    if (document.querySelector(classe)) { clearInterval(i); resolve(); }
                    k++; if(k > 50) { clearInterval(i); reject('Timeout Modal'); }
                }, 200);
            });
        }

        // Auto-inicializa a UI da Worker
        criarBotoesInfojud();
    };

    // =================================================================================
    // PARTE 2: AUTO-EXECUÇÃO RECEITA FEDERAL (e-CAC)
    // =================================================================================
    if (URL_ATUAL.includes('detalheNICNPJ.asp')) {
        if (document.body.innerText.includes('Nenhum registro') || document.body.innerText.includes('Erro')) {
            _gmSet('GOD_STATUS', 'PULAR_' + Date.now());
            mostrarNotificacao('Falha: Nenhum registro. Aguarde ou feche manualmente.', '#dc3545', true);
            return;
        }
        setTimeout(() => {
            const tds = Array.from(document.querySelectorAll('td'));
            const labelCpf = tds.find(td => td.textContent.includes('CPF do responsável'));
            const cpf = labelCpf ? apenasNumeros(labelCpf.nextElementSibling?.textContent) : null;
            if (cpf && cpf.length === 11) {
                mostrarNotificacao('CNPJ Direcionando para CPF...', '#0288d1');
                _gmOpenTab(URL_BASE_CPF + cpf, { active: true, insert: true });
            } else {
                _gmSet('GOD_STATUS', 'PULAR_' + Date.now());
                mostrarNotificacao('Nenhum CPF Elegível Encontrado.', '#ffc107', true);
            }
        }, 800);
    } 
    else if (URL_ATUAL.includes('detalheNICPF.asp')) {
        setTimeout(() => {
            try {
                let d = { nomeCompleto: '', cepRaw: '', endRaw: '' };
                document.querySelectorAll('td.azulEsquerdaNeg').forEach(t => {
                    let l = t.textContent.trim().replace(':', '');
                    let v = t.nextElementSibling?.textContent.trim() || '';
                    v = v.replace(/[\n\r]+/g, ' ').replace(/\s+/g, ' ').trim();
                   
                    if (l === 'Nome Completo') d.nomeCompleto = v;
                    if (l === 'CEP') d.cepRaw = v;
                    if (l === 'Endereço') d.endRaw = v;
                });

                if (d.cepRaw) {
                    d.nome = d.nomeCompleto ? d.nomeCompleto.trim() : '';
                    let cep = apenasNumeros(d.cepRaw);
                    if (cep.length === 7) cep = '0' + cep;
                    d.cep = cep;

                    let endLimpo = d.endRaw;
                    let tokens = endLimpo.split(' ');
                    let numeroIdx = -1;

                    for (let i = 0; i < tokens.length; i++) {
                        if (/^\d+$/.test(tokens[i])) { numeroIdx = i; break; }
                    }

                    if (numeroIdx > -1) {
                        d.numero = tokens[numeroIdx];
                        d.rua = tokens.slice(0, numeroIdx).join(' ');
                        let resto = tokens.slice(numeroIdx + 1).join(' ');
                        if(resto.startsWith('-')) resto = resto.substring(1).trim();
                       
                        const tipoOrigem = _gmGet('GOD_TIPO_ORIGEM', 'CNPJ_NORMAL');
                        d.complemento = tipoOrigem === 'CPF_DIRETO' ? resto : resto + ' N/P ' + d.nome;
                    } else {
                        d.numero = 'S/N';
                        d.rua = endLimpo;
                        d.complemento = d.nome;
                    }

                    _gmSet('GOD_DADOS_CAPTURA', JSON.stringify(d));
                    _gmSet('GOD_STATUS', 'DADOS_PRONTOS_' + Date.now());

                    mostrarNotificacao('DADOS OK! Retorne ao PJe (Aba continuará aberta)', '#28a745', true);
                } else {
                    throw new Error('Dados incompletos');
                }
            } catch (e) {
                console.error(e);
                _gmSet('GOD_STATUS', 'PULAR_' + Date.now());
                mostrarNotificacao('Erro na Leitura da Receita. Pulando no PJe.', '#dc3545', true);
            }
        }, 1000);
    }

})();