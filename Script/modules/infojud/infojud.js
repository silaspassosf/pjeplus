// Módulo Infojud Pro - Integrado ao PJeTools
(function () {
    'use strict';

    // ── APIs de storage: usa GM_setValue/getValue reais (cross-origin no TM)
    // Fallback para localStorage apenas se GM não disponível (contexto fora do TM)
    const _gmSet = (typeof GM_setValue !== 'undefined')
        ? (k, v) => GM_setValue(k, String(v))
        : (k, v) => localStorage.setItem(k, String(v));

    const _gmGet = (typeof GM_getValue !== 'undefined')
        ? (k, d = null) => { const v = GM_getValue(k, d); return v !== null && v !== undefined ? v : d; }
        : (k, d = null) => { const v = localStorage.getItem(k); return v !== null ? v : d; };

    // GM_openInTab abre com foco e mantém referência; fallback para window.open
    const _gmOpenTab = (typeof GM_openInTab !== 'undefined')
        ? (url, opts) => GM_openInTab(url, opts)
        : (url, _opts) => window.open(url, '_blank');
    // ────────────────────────────────────────────────────────────────

    // contexto de execução real da página (unsafeWindow quando disponível)
    const _win = (typeof unsafeWindow !== 'undefined') ? unsafeWindow : window;
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

    function parseEndereco(endRaw) {
        const result = { rua: '', numero: 'S/N', complemento: '', raw: endRaw || '' };
        if (!endRaw) return result;
        const tokens = endRaw.replace(/\s+/g, ' ').trim().split(' ');
        const numeroIdx = tokens.findIndex(t => /^\d+$/.test(t));
        if (numeroIdx > -1) {
            result.rua = tokens.slice(0, numeroIdx).join(' ');
            result.numero = tokens[numeroIdx];
            let resto = tokens.slice(numeroIdx + 1).join(' ');
            if (resto.startsWith('-')) resto = resto.substring(1).trim();
            result.complemento = resto;
        } else {
            result.rua = endRaw.trim();
        }
        return result;
    }

    function formatarEnderecoRelatorio(end) {
        const parts = [];
        if (end.rua) parts.push(normalizar(end.rua));
        if (end.numero) parts.push(normalizar(end.numero));
        if (end.complemento) parts.push(normalizar(end.complemento));
        if (end.cep) parts.push(end.cep);
        return parts.filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
    }

    function formatarDocumento(doc) {
        const apenas = apenasNumeros(doc || '');
        if (apenas.length === 14) return `${apenas.slice(0,2)}.${apenas.slice(2,5)}.${apenas.slice(5,8)}/${apenas.slice(8,12)}-${apenas.slice(12)}`;
        if (apenas.length === 11) return `${apenas.slice(0,3)}.${apenas.slice(3,6)}.${apenas.slice(6,9)}-${apenas.slice(9)}`;
        return doc || '';
    }

    function montarRelatorio(d) {
        const linhas = [];
        if (d.empresaNome) {
            linhas.push(`Empresa: ${d.empresaNome}`);
            if (d.empresaEnderecoRaw || d.empresaCep) {
                const empresaEnd = d.empresaEndereco || parseEndereco(d.empresaEnderecoRaw || '');
                empresaEnd.cep = d.empresaCep || empresaEnd.cep || '';
                const textoEmpresa = formatarEnderecoRelatorio(empresaEnd);
                if (textoEmpresa) linhas.push(`Endereço: ${textoEmpresa}`);
            }
            if (d.nome) {
                linhas.push(`Sócio desta empresa: ${d.nome}${d.cpf ? ` (${formatarDocumento(d.cpf)})` : ''}`);
                const socioEnd = { rua: d.rua, numero: d.numero, complemento: d.complemento, cep: d.cep };
                const textoSocio = formatarEnderecoRelatorio(socioEnd);
                if (textoSocio) linhas.push(`Endereço: ${textoSocio}`);
            }
        } else {
            if (d.nome) linhas.push(`Nome: ${d.nome}`);
            if (d.cpf) linhas.push(`CPF: ${formatarDocumento(d.cpf)}`);
            const endereco = { rua: d.rua, numero: d.numero, complemento: d.complemento, cep: d.cep };
            const texto = formatarEnderecoRelatorio(endereco);
            if (texto) linhas.push(`Endereço: ${texto}`);
        }
        return linhas.join('\n');
    }

    function extrairDadosCNPJPage() {
        const d = { empresaNome: '', empresaCep: '', empresaEnderecoRaw: '', empresaEndereco: null, cpfResponsavel: '' };
        document.querySelectorAll('td.azulEsquerdaNeg').forEach(td => {
            const label = (td.textContent || '').replace(/:/g, '').trim().toUpperCase();
            const valor = (td.nextElementSibling?.textContent || '').replace(/\s+/g, ' ').trim();
            if (label.includes('CPF DO RESPONSÁVEL')) d.cpfResponsavel = apenasNumeros(valor);
            if (label.includes('NOME EMPRESARIAL') || label.includes('RAZÃO SOCIAL') || label.includes('RAZAO SOCIAL')) d.empresaNome = valor;
            if (label === 'CEP') d.empresaCep = apenasNumeros(valor);
            if (label === 'ENDEREÇO') {
                d.empresaEnderecoRaw = valor;
                d.empresaEndereco = parseEndereco(valor);
            }
        });
        return d;
    }

    function extrairDadosCPFPage() {
        const d = { nome: '', cpf: '', cepRaw: '', endRaw: '', cep: '', rua: '', numero: '', complemento: '' };
        document.querySelectorAll('td.azulEsquerdaNeg').forEach(td => {
            const label = (td.textContent || '').replace(/:/g, '').trim().toUpperCase();
            const valor = (td.nextElementSibling?.textContent || '').replace(/\s+/g, ' ').trim();
            if (label === 'NOME COMPLETO') d.nome = valor;
            if (label === 'CPF') d.cpf = apenasNumeros(valor);
            if (label === 'CEP') d.cepRaw = valor;
            if (label === 'ENDEREÇO') d.endRaw = valor;
        });
        if (d.cepRaw) {
            d.cep = apenasNumeros(d.cepRaw);
            if (d.cep.length === 7) d.cep = '0' + d.cep;
        }
        if (d.endRaw) {
            const addr = parseEndereco(d.endRaw);
            d.rua = addr.rua;
            d.numero = addr.numero;
            d.complemento = addr.complemento;
        }
        return d;
    }

    // =================================================================================
    // PARTE 1: EXPOSIÇÃO PARA O PJE TOOLS (O Orquestrador chama esta função)
    // =================================================================================
    // FIX #1: registrar no contexto real da página para que o orquestrador (unsafeWindow) ache
    _win.runInfojudWorker = function() {
        // FIX #2: ler a URL no momento da chamada (SPA pode ter navegado desde o carregamento)
        const URL_ATUAL_LOCAL = window.location.href;
        if (!(URL_ATUAL_LOCAL.includes('pje.trt2.jus.br') || URL_ATUAL_LOCAL.includes('pje1g.trt2.jus.br'))) return;
        if (!URL_ATUAL_LOCAL.includes('/minutas')) return;

        console.log('[Infojud] Worker orquestrado pelo PJeTools com sucesso.');

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
            
            const btnDados = document.createElement('button');
            btnDados.textContent = 'Infojud Dados'; btnDados.style.cssText = btnStyle + 'background:#6a1b9a;';
            btnDados.onclick = () => iniciarTrabalho('DADOS');

            const btnD = document.createElement('button');
            btnD.textContent = 'Infojud Direto'; btnD.style.cssText = btnStyle + 'background:#0288d1;';
            btnD.onclick = () => iniciarTrabalho('DIRETO');

            const btnC = document.createElement('button');
            btnC.textContent = 'Infojud Correção'; btnC.style.cssText = btnStyle + 'background:#004d40;';
            btnC.onclick = () => iniciarTrabalho('COMPLETO');

            container.appendChild(btnDados);
            container.appendChild(btnD);
            container.appendChild(btnC);
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

        async function processarProximo() {
            // marca que esta aba PJe está pronta para recebimento de foco
            _gmSet('GOD_PJE_PRONTA', '1');
            if (atual >= filaDocs.length) {
                mostrarNotificacao("Ciclo Infojud Finalizado!", '#28a745', true);
                if (MODO_EXECUCAO !== 'DADOS') salvarGeralFinal();
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

            // Jitter para evitar requests sequenciais rápidos (mitiga bloqueio da Receita)
            const jitter = 800 + Math.floor(Math.random() * 1200); // 800ms - 2000ms
            await wait(jitter);

            if (doc.length === 11) {
                _gmSet('GOD_TIPO_ORIGEM', 'CPF_DIRETO');
                _gmOpenTab(URL_BASE_CPF + doc, { active: false, insert: true });
            } else {
                _gmSet('GOD_TIPO_ORIGEM', 'CNPJ_NORMAL');
                _gmOpenTab(URL_BASE_CNPJ + doc, { active: false, insert: true });
            }

            // marca timestamp da última abertura para o watchdog
            try { window.__ultimaAberturaAba = Date.now(); } catch (e) {}
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
            const status = _gmGet('GOD_STATUS', '') || '';
            const agora = Date.now();

            // Watchdog: se passou muito tempo desde a última abertura de aba sem resposta, pula
            if (!window.__ultimaAberturaAba) window.__ultimaAberturaAba = 0;
            if (status === 'STANDBY' && window.__ultimaAberturaAba && (agora - window.__ultimaAberturaAba) > 30000) {
                console.warn('[Infojud] Watchdog: timeout aguardando e-CAC. Pulando.');
                _gmSet('GOD_STATUS', 'PULAR_' + agora);
                window.__ultimaAberturaAba = agora;
            }

            if (status.startsWith('DADOS_PRONTOS_')) {
                const id = status.split('_')[2];
                if (id !== ultimoProcessado) {
                    ultimoProcessado = id;
                    // limpa sinal imediatamente para evitar reentrância
                    _gmSet('GOD_STATUS', 'PROCESSANDO');
                    try { window.focus(); } catch (e) {}
                    setTimeout(() => aplicarLogicaMaster(), 300);
                }
            } else if (status.startsWith('PULAR_')) {
                const id = status.split('_')[1];
                if (id !== ultimoProcessado) {
                    ultimoProcessado = id;
                    try { window.focus(); } catch (e) {}
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
                dadosRelatorio.push(montarRelatorio(d));

                if (MODO_EXECUCAO === 'DADOS') {
                    linha.style.backgroundColor = '#c8e6c9';
                    atual++;
                    setTimeout(processarProximo, 800);
                    return;
                }

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
                position: fixed; top: 190px; right: 20px;
                background: white; border: 2px solid #004d40;
                padding: 10px; z-index: 10000;
                width: 520px; max-height: 420px;
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
            contentDiv.textContent = dadosRelatorio.join('\n\n---\n\n');
           
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

        // Desenha os botões na tela quando o orquestrador mandar rodar
        criarBotoesInfojud();
    };

    // =================================================================================
    // PARTE 2: AUTO-EXECUÇÃO RECEITA FEDERAL (e-CAC)
    // O orquestrador não monitora essas rotas ativamente para comandos,
    // então a lógica roda automaticamente aqui.
    // =================================================================================
    if (URL_ATUAL.includes('detalheNICNPJ.asp') || URL_ATUAL.includes('detalheNICPF.asp')) {
        console.log('[Infojud] Módulo ativo na aba e-CAC:', URL_ATUAL);
    }

    if (URL_ATUAL.includes('detalheNICNPJ.asp')) {
        if (document.body.innerText.includes('Nenhum registro') || document.body.innerText.includes('Erro')) {
            _gmSet('GOD_STATUS', 'PULAR_' + Date.now());
            mostrarNotificacao('Falha: Nenhum registro. Aguarde ou feche manualmente.', '#dc3545', true);
            // tenta devolver foco ao PJe para que ele prossiga
            try { if (window.opener && !window.opener.closed) window.opener.focus(); } catch (e) {}
            return;
        }
        setTimeout(() => {
            const cnpjDados = extrairDadosCNPJPage();
            const cpf = cnpjDados.cpfResponsavel || '';
            if (cnpjDados.empresaNome) {
                _gmSet('GOD_DADOS_CAPTURA', JSON.stringify(cnpjDados));
            }
            if (cpf && cpf.length === 11) {
                mostrarNotificacao('CNPJ Direcionando para CPF...', '#0288d1');
                _gmOpenTab(URL_BASE_CPF + cpf, { active: false, insert: true });
            } else {
                _gmSet('GOD_STATUS', 'PULAR_' + Date.now());
                mostrarNotificacao('Nenhum CPF Elegível Encontrado.', '#ffc107', true);
                try { if (window.opener && !window.opener.closed) window.opener.focus(); } catch (e) {}
            }
        }, 800);
    } 
    else if (URL_ATUAL.includes('detalheNICPF.asp')) {
        setTimeout(() => {
            try {
                const base = JSON.parse(_gmGet('GOD_DADOS_CAPTURA', '{}')) || {};
                const cpfDados = extrairDadosCPFPage();
                const merged = Object.assign({}, base, cpfDados, {
                    tipoOrigem: _gmGet('GOD_TIPO_ORIGEM', 'CNPJ_NORMAL')
                });

                if (merged.cep) {
                    _gmSet('GOD_DADOS_CAPTURA', JSON.stringify(merged));
                    _gmSet('GOD_STATUS', 'DADOS_PRONTOS_' + Date.now());
                    mostrarNotificacao('DADOS OK! Retornando ao PJe...', '#28a745', true);
                    _devolverFocoPJe();
                } else {
                    throw new Error('Dados incompletos');
                }
            } catch (e) {
                console.error(e);
                _gmSet('GOD_STATUS', 'PULAR_' + Date.now());
                mostrarNotificacao('Erro na Leitura da Receita. Pulando no PJe.', '#dc3545', true);
                _devolverFocoPJe();
            }
        }, 1000);
    }

    // ── Auxiliar: percorre cadeia de openers até encontrar a aba PJe e foca nela
    function _devolverFocoPJe() {
        try {
            if (window.opener && !window.opener.closed) {
                const op = window.opener;
                try {
                    if (op.location && op.location.href && (op.location.href.includes('pje.trt2.jus.br') || op.location.href.includes('pje1g.trt2.jus.br'))) {
                        op.focus(); return;
                    }
                } catch (e) { /* cross-origin may block reading location */ }

                if (op.opener && !op.opener.closed) {
                    try {
                        const pje = op.opener;
                        if (pje.location && pje.location.href && (pje.location.href.includes('pje.trt2.jus.br') || pje.location.href.includes('pje1g.trt2.jus.br'))) {
                            pje.focus(); return;
                        }
                    } catch (e) { /* ignore */ }
                }

                // fallback: focus opener
                try { op.focus(); } catch (e) {}
            }
        } catch (e) { /* ignore */ }
    }

})();