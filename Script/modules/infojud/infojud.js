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
    try { _win.__infojudModuleLoaded = true; } catch (e) {}
    console.log('[Infojud] module loaded and registered on window');
    const URL_ATUAL = window.location.href;
    const URL_BASE_CNPJ = 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI=';
    const URL_BASE_CPF = 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp?NI=';

    // API pública para outros módulos abrirem uma consulta Infojud.
    _win.consultarInfojud = function (numero) {
        const documento = apenasNumeros(numero);
        if (documento.length !== 11 && documento.length !== 14) {
            throw new Error('Informe um CPF com 11 números ou CNPJ com 14 números.');
        }
        const base = documento.length === 11 ? URL_BASE_CPF : URL_BASE_CNPJ;
        const url = base + encodeURIComponent(documento);
        _gmOpenTab(url, { active: true, insert: true });
        return url;
    };

    // Saída em formato de minuta para o painel AUD:
    // NOME, CPF nº XXX.XXX.XXX-XX, residente no endereço: AV X 72 BAIRRO, CEP XXXXXXXX - CIDADE/UF.
    function textoMinutaAud(d) {
        if (d.empresaNome) return montarRelatorio(d);
        const endereco = [d.rua, d.numero, d.complemento].filter(Boolean).join(' ').trim();
        const local = [d.municipio, d.uf].filter(Boolean).join('/');
        const partes = [d.nome, 'CPF nº ' + formatarDocumento(d.cpf), 'residente no endereço: ' + endereco];
        let texto = partes.filter(Boolean).join(', ');
        if (d.cep) texto += ', CEP ' + d.cep;
        if (local) texto += ' - ' + local;
        return texto + '.';
    }

    _win.consultarInfojudComRetorno = function (numero) {        const documento = apenasNumeros(numero);
        if (documento.length !== 11 && documento.length !== 14) {
            return Promise.reject(new Error('Informe um CPF com 11 números ou CNPJ com 14 números.'));
        }
        const chave = 'GOD_AUD_' + Date.now();
        _gmSet('GOD_STATUS', 'STANDBY');
        _gmSet('GOD_DADOS_CAPTURA', '{}');
        _gmSet('GOD_TIPO_ORIGEM', documento.length === 11 ? 'CPF_DIRETO' : 'CNPJ_NORMAL');
        const url = (documento.length === 11 ? URL_BASE_CPF : URL_BASE_CNPJ) + encodeURIComponent(documento);
        console.log('[Infojud AUD] Abrindo consulta em segundo plano:', url);
        const aba = _gmOpenTab(url, { active: false, insert: true });
        return new Promise((resolve, reject) => {
            const inicio = Date.now();
            const fecharAba = () => {
                if (aba && typeof aba.close === 'function') {
                    try { aba.close(); } catch (e) {}
                }
            };
            const timer = setInterval(() => {
                const status = _gmGet('GOD_STATUS', '') || '';
                if (status.startsWith('DADOS_PRONTOS_')) {
                    clearInterval(timer);
                    try {
                        const dados = JSON.parse(_gmGet('GOD_DADOS_CAPTURA', '{}') || '{}');
                        console.log('[Infojud AUD] Dados recebidos da Receita:', dados);
                        resolve({ texto: textoMinutaAud(dados), dados: dados, chave: chave });
                    } catch (e) { reject(new Error('Dados Infojud inválidos: ' + e.message)); }
                    fecharAba();
                } else if (status.startsWith('PULAR_')) {
                    clearInterval(timer);
                    console.warn('[Infojud AUD] Receita sinalizou falha:', status);
                    reject(new Error('A Receita não retornou dados para o documento.'));
                    fecharAba();
                } else if (Date.now() - inicio > 60000) {
                    clearInterval(timer);
                    console.warn('[Infojud AUD] Timeout aguardando retorno:', status || 'sem status');
                    reject(new Error('Tempo esgotado aguardando a consulta Infojud.'));
                    fecharAba();
                }
            }, 400);
        });
    };

    const wait = (ms) => new Promise(r => setTimeout(r, ms));
    const normalizar = (txt) => (txt || '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/\s+/g, ' ').trim();
    const apenasNumeros = (txt) => (txt || '').replace(/\D/g, '');

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[c]));
    }

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
        if (!end) return '';
        const parts = [];
        if (end.rua) parts.push(end.rua);
        if (end.numero && end.numero !== 'S/N') parts.push(end.numero);
        else if (end.numero === 'S/N') parts.push('S/N');
        if (end.complemento) parts.push(end.complemento);
        if (end.bairro) parts.push(end.bairro);
        let txt = parts.filter(Boolean).join(', ').trim();
        const cidUf = [end.municipio, end.uf].filter(Boolean).join('/');
        if (cidUf) txt += (txt ? ' - ' : '') + cidUf;
        if (end.cep) {
            const numCep = apenasNumeros(end.cep);
            const cepFmt = numCep.length === 8 ? `${numCep.slice(0, 5)}-${numCep.slice(5)}` : end.cep;
            txt += (txt ? ' - CEP: ' : 'CEP: ') + cepFmt;
        }
        return txt || end.raw || '';
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
            if (d.cnpj) linhas.push(`CNPJ: ${formatarDocumento(d.cnpj)}`);
            if (d.empresaEnderecoRaw || d.empresaCep) {
                const empresaEnd = d.empresaEndereco || parseEndereco(d.empresaEnderecoRaw || '');
                empresaEnd.cep = d.empresaCep || empresaEnd.cep || '';
                const textoEmpresa = formatarEnderecoRelatorio(empresaEnd);
                if (textoEmpresa) linhas.push(`Endereço: ${textoEmpresa}`);
            }
            if (d.nome) {
                linhas.push(`Sócio desta empresa: ${d.nome}${d.cpf ? ` (${formatarDocumento(d.cpf)})` : ''}`);
                const socioEnd = { rua: d.rua, numero: d.numero, complemento: d.complemento, bairro: d.bairro, municipio: d.municipio, uf: d.uf, cep: d.cep };
                const textoSocio = formatarEnderecoRelatorio(socioEnd);
                if (textoSocio) linhas.push(`Endereço: ${textoSocio}`);
            }
        } else {
            if (d.nome) linhas.push(`Nome: ${d.nome}`);
            if (d.cpf) linhas.push(`CPF: ${formatarDocumento(d.cpf)}`);
            const endereco = { rua: d.rua, numero: d.numero, complemento: d.complemento, bairro: d.bairro, municipio: d.municipio, uf: d.uf, cep: d.cep };
            const texto = formatarEnderecoRelatorio(endereco);
            if (texto) linhas.push(`Endereço: ${texto}`);
        }
        return linhas.join('\n');
    }

    function extrairDadosCNPJPage() {
        const d = { empresaNome: '', empresaCep: '', empresaEnderecoRaw: '', empresaEndereco: null, cpfResponsavel: '', cnpj: '', logradouro: '', complemento: '', bairro: '', municipio: '', uf: '' };
        document.querySelectorAll('td.azulEsquerdaNeg').forEach(td => {
            const rawLabel = (td.textContent || '').replace(/:/g, '').trim();
            const label = rawLabel.toUpperCase();
            const valor = (td.nextElementSibling?.textContent || '').replace(/\s+/g, ' ').trim();
            if (label.includes('CPF') && label.includes('RESP')) d.cpfResponsavel = apenasNumeros(valor);
            if (label === 'CNPJ' || label.includes('CNPJ')) d.cnpj = apenasNumeros(valor);
            if (label.includes('NOME EMPRESARIAL') || label.includes('NOME FANTASIA') || label.includes('RAZÃO SOCIAL') || label.includes('RAZAO SOCIAL')) {
                // preferir Nome Empresarial (razão social)
                if (!d.empresaNome || label.includes('EMPRESARIAL') || label.includes('RAZ')) d.empresaNome = valor;
            }
            if (label === 'CEP' || label.includes('CEP')) d.empresaCep = apenasNumeros(valor);
            if (label === 'ENDEREÇO' || label.includes('LOGRADOURO') || label.includes('RUA') || label.includes('AVENIDA') || label.includes('AV')) {
                d.empresaEnderecoRaw = valor;
                d.empresaEndereco = parseEndereco(valor);
                d.logradouro = d.empresaEndereco.rua || '';
                d.complemento = d.empresaEndereco.complemento || '';
            }
            if (label.includes('COMPLEMENTO')) d.complemento = valor;
            if (label.includes('BAIRRO')) d.bairro = valor;
            if (label.includes('MUNICIP') || label.includes('MUNICI')) d.municipio = valor;
            if (label === 'UF') d.uf = valor;
        });

        // If endereco pieces available but empresaEndereco empty, try to assemble
        if (!d.empresaEndereco && (d.logradouro || d.complemento || d.bairro)) {
            const assembled = `${d.logradouro || ''} ${d.complemento || ''}`.trim();
            d.empresaEnderecoRaw = assembled;
            d.empresaEndereco = parseEndereco(assembled);
        }

        return d;
    }

    function extrairDadosCPFPage() {
        const d = { nome: '', cpf: '', cepRaw: '', endRaw: '', cep: '', rua: '', numero: '', complemento: '', bairro: '', municipio: '', uf: '' };
        document.querySelectorAll('td.azulEsquerdaNeg').forEach(td => {
            const rawLabel = (td.textContent || '').replace(/:/g, '').trim();
            const label = rawLabel.toUpperCase();
            const valor = (td.nextElementSibling?.textContent || '').replace(/\s+/g, ' ').trim();
            if (label.includes('NOME') && label.includes('COMPLETO')) d.nome = valor;
            if (label === 'CPF' || label.includes('CPF')) d.cpf = apenasNumeros(valor);
            if (label === 'CEP' || label.includes('CEP')) d.cepRaw = valor;
            if (label === 'ENDEREÇO' || label.includes('LOGRADOURO') || label.includes('RUA') || label.includes('AV')) d.endRaw = valor;
            if (label.includes('COMPLEMENTO')) d.complemento = valor;
            if (label.includes('BAIRRO')) d.bairro = valor;
            if (label.includes('MUNICIP') || label.includes('MUNICI')) d.municipio = valor;
            if (label === 'UF') d.uf = valor;
        });

        if (d.cepRaw) {
            d.cep = apenasNumeros(d.cepRaw);
            if (d.cep.length === 7) d.cep = '0' + d.cep;
        }
        if (d.endRaw) {
            const addr = parseEndereco(d.endRaw);
            d.rua = addr.rua;
            d.numero = addr.numero;
            d.complemento = addr.complemento || d.complemento;
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
        let dadosRelatorioKeys = new Set();

        function criarBotoesInfojud() {
            if (document.getElementById('god-btn-wrapper')) return;

            // Tentar inserir próximo ao botão de lixeira (quando disponível na tela)
            const alvo = document.querySelector('div.pec-item-botoes-ato-agrupado');
            const wrapper = document.createElement('div');
            wrapper.id = 'god-btn-wrapper';
            wrapper.style.cssText = 'display:flex;flex-direction:row;gap:8px;align-items:center;';

            const btnStyle = 'padding:8px 14px;color:white;font-weight:700;cursor:pointer;border-radius:6px;border:none;box-shadow:0 2px 6px rgba(0,0,0,0.18);font-size:13px;';

            // Botão inicial (apenas este aparece no carregamento)
            const btnExtrair = document.createElement('button');
            btnExtrair.id = 'god-btn-extrair';
            btnExtrair.textContent = 'Extrair Infojud';
            btnExtrair.style.cssText = btnStyle + 'background:#d32f2f;';
            btnExtrair.onclick = () => iniciarTrabalho('DADOS');
            wrapper.appendChild(btnExtrair);

            if (alvo && alvo.parentElement) {
                // inserir após o container de botões do ato agrupado, com um pequeno espaçamento
                alvo.parentElement.insertBefore(wrapper, alvo.nextSibling);
                wrapper.style.marginLeft = '8px';
            } else {
                // fallback: container fixo no canto superior direito
                wrapper.style.position = 'fixed';
                wrapper.style.top = '100px';
                wrapper.style.right = '20px';
                wrapper.style.zIndex = '9999';
                document.body.appendChild(wrapper);
            }
        }

        function iniciarTrabalho(modo) {
            MODO_EXECUCAO = modo;
            const spans = Array.from(document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
            filaDocs = [...new Set(spans.map(s => apenasNumeros(s.textContent)).filter(n => n.length === 11 || n.length === 14))];
            
            if (!filaDocs.length) return alert('Nenhum documento encontrado na página!');
            
            const oldR = document.getElementById('god-relatorio-panel');
            if(oldR) oldR.remove();

            rodando = true; atual = 0; ultimoProcessado = ''; dadosRelatorio = []; dadosRelatorioKeys = new Set();
            _gmSet('GOD_STATUS', 'STANDBY');
            
            mostrarNotificacao(`Iniciando Modo: ${MODO_EXECUCAO}`, '#0288d1');
            if (MODO_EXECUCAO === 'DADOS') monitorarSinais();
            processarProximo();
        }

        async function processarProximo() {
            // marca que esta aba PJe está pronta para recebimento de foco
            _gmSet('GOD_PJE_PRONTA', '1');
            if (atual >= filaDocs.length) {
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

            if (MODO_EXECUCAO === 'DADOS') {
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
            } else {
                // DIRETO / COMPLETO: usa cache gerado pelo modo DADOS, sem tocar no e-CAC
                const cached = _gmGet('GOD_DADOS_' + doc, null);
                if (cached) {
                    setTimeout(() => aplicarLogicaMaster(), 300);
                } else {
                    mostrarNotificacao('Sem dados para ' + doc + '. Execute "Extrair Infojud" primeiro.', '#f57c00');
                    const linhaSem = encontrarLinhaPorDoc(doc);
                    if (linhaSem) linhaSem.style.backgroundColor = '#ffccbc';
                    atual++;
                    setTimeout(processarProximo, 1000);
                }
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
                    // DADOS lê de CAPTURA (fresh da sessão); DIRETO/COMPLETO lê do cache por-doc
                    const d = JSON.parse(
                        MODO_EXECUCAO === 'DADOS'
                            ? (_gmGet('GOD_DADOS_CAPTURA', '{}') || '{}')
                            : (_gmGet('GOD_DADOS_' + docAtual, '{}') || '{}')
                    );
                    console.log('[Infojud] dados lidos', docAtual, d, 'MODO', MODO_EXECUCAO);

                    if (MODO_EXECUCAO === 'DADOS') {
                        const buscaDoc = docAtual || filaDocs[atual] || '';
                        const tipoOrigem = (d && d.tipoOrigem) ? d.tipoOrigem : (buscaDoc && buscaDoc.length === 11 ? 'CPF_DIRETO' : 'CNPJ_NORMAL');

                        if (tipoOrigem === 'CPF_DIRETO') {
                            const pf = {
                                nome: d.nome || '',
                                cpf: d.cpf || buscaDoc,
                                rua: d.rua || '',
                                numero: d.numero || '',
                                complemento: d.complemento || '',
                                cep: d.cep || ''
                            };
                            if (!dadosRelatorioKeys.has(buscaDoc)) {
                                dadosRelatorioKeys.add(buscaDoc);
                                dadosRelatorio.push(montarRelatorio(pf));
                            }
                        } else {
                            const empresaEntry = {
                                empresaNome: d.empresaNome || '',
                                empresaEnderecoRaw: d.empresaEnderecoRaw || '',
                                empresaEndereco: d.empresaEndereco || null,
                                empresaCep: d.empresaCep || '',
                                nome: d.nome || d.cpfResponsavel || '',
                                cpf: d.cpf || d.cpfResponsavel || '',
                                rua: d.rua || '',
                                numero: d.numero || '',
                                complemento: d.complemento || '',
                                cep: d.cep || ''
                            };
                            if (!dadosRelatorioKeys.has(buscaDoc)) {
                                dadosRelatorioKeys.add(buscaDoc);
                                dadosRelatorio.push(montarRelatorio(empresaEntry));
                            }
                        }

                        // salvar por-doc para que DIRETO/COMPLETO reutilizem sem ir ao e-CAC
                        try { _gmSet('GOD_DADOS_' + buscaDoc, JSON.stringify(d)); } catch (e) {}
                        const l = encontrarLinhaPorDoc(buscaDoc);
                        if (l) l.style.backgroundColor = '#c8e6c9';
                        atual++;
                        setTimeout(processarProximo, 800);
                        return;
                    }

                    const linha = encontrarLinhaPorDoc(docAtual);
                    if (!linha) throw new Error(`Linha não encontrada`);

                    const btnEnvelope = linha.querySelector('.fa-envelope');
                    if (!btnEnvelope) throw new Error('Envelope sumiu');

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

                    // quando é endereço de sócio (CNPJ com nome do responsável), anexar "N/P {nome}" ao complemento
                    if (d.empresaNome && d.nome) {
                        const sufixo = 'N/P ' + d.nome;
                        complFinal = complFinal ? complFinal + ' ' + sufixo : sufixo;
                    }

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

                // --- TROCA DE ENDEREÇO NA TABELA PRINCIPAL (Para ambos MODO DIRETO e COMPLETO) ---
                let endAlvoRaw = d.rua || d.endRaw || d.logradouro || d.empresaEnderecoRaw || '';
                let ruaAlvo = normalizar(endAlvoRaw).split(',')[0].trim();
                if (ruaAlvo) {
                    const icones = Array.from(document.querySelectorAll('.pec-icone-verde-endereco-tabela-destinatarios'));
                    const alvo = icones.find(icone => normalizar(icone.getAttribute('aria-label') || '').includes(ruaAlvo));
                    if (alvo) {
                        const tr = alvo.closest('tr');
                        const btnEdit = tr.querySelector('.fa-edit');
                        if (btnEdit) { (btnEdit.closest('button') || btnEdit).click(); await wait(800); }
                    }
                }

                if (MODO_EXECUCAO === 'COMPLETO') {
                    const btnConfec = document.querySelector('button[aria-label="Confeccionar ato"]');
                    if (btnConfec) {
                        console.log('[Infojud] Abrindo minuta (Confeccionar ato)...');
                        btnConfec.click();

                        let editor = null;
                        let ckInstance = null;
                        let html = '';

                        // Polling defensivo aguardando editor estar presente E com o template/conteúdo carregado
                        for (let i = 0; i < 50; i++) {
                            await wait(200);
                            editor = document.querySelector('.ck-editor__editable[contenteditable="true"], .ck-editor__editable, [contenteditable="true"]');
                            if (editor) {
                                ckInstance = editor.ckeditorInstance 
                                    || editor.closest('.ck-editor')?.ckeditorInstance 
                                    || Array.from(document.querySelectorAll('.ck-editor__editable, [contenteditable="true"]')).find(x => x.ckeditorInstance)?.ckeditorInstance
                                    || (window.CKEDITOR?.instances ? Object.values(window.CKEDITOR.instances)[0] : null);

                                html = ckInstance && typeof ckInstance.getData === 'function' ? ckInstance.getData() : (editor.innerHTML || '');
                                if (html && (/DESTINAT[ÁA]RIO/i.test(html) || /endere[çc]o/i.test(html) || /\bcep\s*:?/i.test(html) || html.trim().length > 80)) {
                                    break;
                                }
                            }
                        }

                        if (editor) {
                            await wait(300);
                            if (!html) {
                                html = ckInstance && typeof ckInstance.getData === 'function' ? ckInstance.getData() : (editor.innerHTML || '');
                            }

                            const variavelPJe = '#{processo.comunicacaoProcessual.enderecoDestinatario}';

                            let novoHtml = null;

                            // 1. Estratégia Principal: Parágrafo imediatamente abaixo de DESTINATÁRIO
                            const patDestNext = /((?:<p[^>]*>|<div[^>]*>)[\s\S]*?DESTINAT[ÁA]RIO[\s\S]*?(?:<\/p>|<\/div>)\s*(?:<p[^>]*>|<div[^>]*>))([\s\S]*?)(<\/p>|<\/div>)/i;

                            if (patDestNext.test(html)) {
                                console.log('[Infojud] Localizado parágrafo abaixo de DESTINATÁRIO. Substituindo pela variável...');
                                novoHtml = html.replace(patDestNext, (match, prefix, pContent, closing) => {
                                    const hasStrong = /<strong\b/i.test(pContent);
                                    const hasB = /<b\b(?!r)/i.test(pContent);

                                    let val = '';
                                    if (/ENDERE[ÇC]O/i.test(pContent)) {
                                        val = `ENDEREÇO: ${variavelPJe}`;
                                    } else {
                                        // Substitui toda a linha de CEP ou endereço antigo diretamente pela variável
                                        val = variavelPJe;
                                    }

                                    let finalContent = val;
                                    if (hasStrong) {
                                        finalContent = `<strong>${val}</strong>`;
                                    } else if (hasB) {
                                        finalContent = `<b>${val}</b>`;
                                    }
                                    return `${prefix}${finalContent}${closing}`;
                                });
                            } else {
                                // 2. Fallbacks caso não esteja em parágrafo isolado logo após DESTINATÁRIO
                                const regexEndereco = /((?:<(?:strong|b)[^>]*>)?\s*ENDERE[ÇC]O(?:\s+DO\s+DESTINAT[ÁA]RIO)?(?:\s*<\/(?:strong|b)>)?\s*:\s*(?:<\/(?:strong|b)>)?)(?:\s|&nbsp;|<br\s*\/?>)*(?:(?!<\/(?:p|div|td|li)>|<br\s*\/?>)[\s\S])*?(?=(?:<\/(?:strong|b)>)?\s*(?:<\/(?:p|div|td|li)>|<br\s*\/?>|$))/gi;
                                const regexCepInicio = /((?:<p[^>]*>|<div[^>]*>|<br\s*\/?>|^)(?:\s|&nbsp;)*(?:<(?:strong|b)[^>]*>)?\s*CEP(?:\s*<\/(?:strong|b)>)?\s*:?\s*(?:<\/(?:strong|b)>)?)(?:\s|&nbsp;|<br\s*\/?>)*(?:(?!<\/(?:p|div|td|li)>|<br\s*\/?>)[\s\S])*?(?=(?:<\/(?:strong|b)>)?\s*(?:<\/(?:p|div|td|li)>|<br\s*\/?>|$))/gi;

                                if (regexEndereco.test(html)) {
                                    console.log('[Infojud] Fallback: Rótulo ENDEREÇO: encontrado. Substituindo no editor...');
                                    novoHtml = html.replace(regexEndereco, (match, p1) => {
                                        let prefixo = p1.trim();
                                        if (/<strong\b/i.test(prefixo) && !/<\/strong\b/i.test(prefixo)) prefixo += '</strong>';
                                        else if (/<b\b(?!r)/i.test(prefixo) && !/<\/b\b/i.test(prefixo)) prefixo += '</b>';
                                        return `${prefixo} ${variavelPJe}`;
                                    });
                                } else if (regexCepInicio.test(html)) {
                                    console.log('[Infojud] Fallback: Linha com CEP: no início encontrada. Substituindo...');
                                    novoHtml = html.replace(regexCepInicio, (match, p1) => {
                                        let prefixo = p1.trim();
                                        if (/<strong\b/i.test(prefixo) && !/<\/strong\b/i.test(prefixo)) prefixo += '</strong>';
                                        else if (/<b\b(?!r)/i.test(prefixo) && !/<\/b\b/i.test(prefixo)) prefixo += '</b>';
                                        return `${prefixo} ${variavelPJe}`;
                                    });
                                } else {
                                    console.warn('[Infojud] Nem parágrafo de destinatário nem rótulos de endereço/CEP localizados. Trecho:', html.substring(0, 300));
                                }
                            }

                            if (novoHtml) {
                                console.log('[Infojud] Inserindo variável de endereço no editor...');
                                if (ckInstance && typeof ckInstance.setData === 'function') {
                                    ckInstance.setData(novoHtml);
                                } else {
                                    editor.focus();
                                    editor.innerHTML = novoHtml;
                                    editor.dispatchEvent(new Event('input', { bubbles: true }));
                                    editor.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                                await wait(600);
                            }

                            // Finalizar minuta (pena)
                            const btnPena = document.querySelector('button[aria-label="Finalizar minuta"]') || document.querySelector('.fa-pen-nib')?.closest('button');
                            if (btnPena) {
                                console.log('[Infojud] Finalizando minuta...');
                                btnPena.click();
                                for (let j = 0; j < 30; j++) {
                                    await wait(200);
                                    if (!document.querySelector('.ck-editor__editable') && !document.querySelector('button[aria-label="Finalizar minuta"]')) {
                                        break;
                                    }
                                }
                            }
                            await wait(600);
                        } else {
                            console.warn('[Infojud] Editor não foi detectado após clicar em Confeccionar ato.');
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
            renderizarPainelRelatorio(dadosRelatorio, {
                isMinutas: true,
                onDireto: () => iniciarTrabalho('DIRETO'),
                onCorrecao: () => iniciarTrabalho('COMPLETO')
            });
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
    // COMPONENTE COMPARTILHADO: RELATÓRIO FINAL DE ENDEREÇOS
    // ── Formatação de Certidão de Juntada INFOJUD ─────────────────────────────
    function formatarEnderecoCertidao(d) {
        const partesLogr = [];
        if (d.rua) partesLogr.push(normalizar(d.rua));
        if (d.numero && d.numero !== 'S/N') partesLogr.push(normalizar(d.numero));
        else if (d.numero === 'S/N') partesLogr.push('S/N');
        if (d.complemento) partesLogr.push(normalizar(d.complemento));
        if (d.bairro) partesLogr.push(normalizar(d.bairro));

        let endereco = partesLogr.filter(Boolean).join(', ');
        const cidadeUf = [normalizar(d.municipio), normalizar(d.uf)].filter(Boolean).join('/');
        if (cidadeUf) endereco += (endereco ? ' - ' : '') + cidadeUf;
        if (d.cep) {
            const numCep = apenasNumeros(d.cep);
            const cepFmt = numCep.length === 8 ? `${numCep.slice(0, 5)}-${numCep.slice(5)}` : d.cep;
            endereco += (endereco ? ' - CEP: ' : 'CEP: ') + cepFmt;
        }
        return endereco.trim() || 'Endereço não informado';
    }

    function formatarEnderecoCertidaoEmpresa(d) {
        if (d.empresaEnderecoRaw) {
            let end = d.empresaEnderecoRaw.trim();
            if (d.empresaCep) {
                const numCep = apenasNumeros(d.empresaCep);
                const cepFmt = numCep.length === 8 ? `${numCep.slice(0, 5)}-${numCep.slice(5)}` : d.empresaCep;
                if (!end.includes(cepFmt) && !end.includes(numCep)) {
                    end += ' - CEP: ' + cepFmt;
                }
            }
            return end;
        }
        return formatarEnderecoCertidao(d);
    }

    function extrairItensDeBlocoTexto(b) {
        const lines = String(b).split('\n').map(l => l.trim()).filter(Boolean);
        const itens = [];

        if (lines.some(l => l.startsWith('Empresa:'))) {
            const empNome = (lines.find(l => l.startsWith('Empresa:')) || '').replace(/^Empresa:\s*/, '').trim();
            const allEnd = lines.filter(l => l.startsWith('Endereço:'));
            const empEnd = allEnd.length > 0 ? allEnd[0].replace(/^Endereço:\s*/, '').trim() : '';
            const cnpjLine = lines.find(l => l.startsWith('CNPJ:'));
            const cnpj = cnpjLine ? cnpjLine.replace(/^CNPJ:\s*/, '').trim() : '';

            itens.push({
                identificacao: `${empNome}${cnpj ? ` - CNPJ ${cnpj}` : ''}`,
                endereco: empEnd
            });

            const socioLine = lines.find(l => l.startsWith('Sócio desta empresa:'));
            if (socioLine) {
                const socioRaw = socioLine.replace(/^Sócio desta empresa:\s*/, '').trim();
                const socioEnd = allEnd.length > 1 ? allEnd[1].replace(/^Endereço:\s*/, '').trim() : '';
                itens.push({
                    identificacao: `Sócio: ${socioRaw}`,
                    endereco: socioEnd
                });
            }
        } else {
            const nome = (lines.find(l => l.startsWith('Nome:')) || lines.find(l => l.startsWith('PESSOA FÍSICA:')) || '').replace(/^(Nome|PESSOA FÍSICA):\s*/, '').trim();
            const cpf = (lines.find(l => l.startsWith('CPF:')) || '').replace(/^CPF:\s*/, '').trim();
            const end = (lines.find(l => l.startsWith('Endereço:')) || '').replace(/^Endereço:\s*/, '').trim();

            itens.push({
                identificacao: `${nome}${cpf ? ` - CPF ${cpf}` : ''}`,
                endereco: end
            });
        }
        return itens;
    }

    function construirHtmlCertidao(itens) {
        const styleTitulo = 'font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:center;text-indent:4.5cm;';
        const styleCorpo = 'font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify;text-indent:4.5cm;';

        let inner = `<p style="${styleTitulo}" class="corpo"><strong>JUNTADA - pesquisa INFOJUD</strong></p>`;
        inner += `<p class="corpo" style="${styleCorpo}">Nessa data, procedo à juntada de pesquisa INFOJUD de endereços:</p>`;

        for (const item of (itens || [])) {
            inner += `<p class="corpo" style="${styleCorpo}">${escapeHtml(item.identificacao)}</p>`;
            inner += `<p class="corpo" style="${styleCorpo}">${escapeHtml(item.endereco)}<br><br><br data-cke-filler="true"></p>`;
        }

        inner += `<p class="corpo" style="${styleCorpo}"><br data-cke-filler="true"></p>`;

        return `<div _ngcontent-epf-c262="" aria-label="Conteúdo principal. Alt+F10 para acessar a barra de tarefas" class="area-conteudo ck ck-content ck-editor__editable ck-rounded-corners ck-editor__editable_inline ck-blurred" lang="pt-br" dir="ltr" role="textbox" contenteditable="true">${inner}</div>`;
    }

    function construirTextoCertidao(itens) {
        let txt = 'JUNTADA - pesquisa INFOJUD\n\n';
        txt += 'Nessa data, procedo à juntada de pesquisa INFOJUD de endereços:\n\n';
        for (const item of (itens || [])) {
            txt += `${item.identificacao}\n${item.endereco}\n\n`;
        }
        return txt.trim();
    }

    async function copiarCertidaoParaClipboard(html, plainText) {
        let copiado = false;
        if (navigator.clipboard && window.ClipboardItem) {
            try {
                const blobHtml = new Blob([html], { type: 'text/html' });
                const blobText = new Blob([plainText], { type: 'text/plain' });
                await navigator.clipboard.write([
                    new ClipboardItem({
                        'text/html': blobHtml,
                        'text/plain': blobText
                    })
                ]);
                copiado = true;
            } catch (e) {
                console.warn('[Infojud] Falha ClipboardItem write:', e);
            }
        }
        if (!copiado) {
            try {
                const listener = (evt) => {
                    evt.clipboardData.setData('text/html', html);
                    evt.clipboardData.setData('text/plain', plainText);
                    evt.preventDefault();
                };
                document.addEventListener('copy', listener);
                document.execCommand('copy');
                document.removeEventListener('copy', listener);
                copiado = true;
            } catch (e2) {
                console.warn('[Infojud] Falha execCommand copy:', e2);
            }
        }
        if (!copiado && typeof GM_setClipboard === 'function') {
            try {
                GM_setClipboard(html, 'html');
                copiado = true;
            } catch (e3) {
                GM_setClipboard(plainText, 'text');
                copiado = true;
            }
        }
        return copiado;
    }

    function tentarInserirNoCKEditor(html) {
        try {
            const editorEl = document.querySelector('.ck-editor__editable[contenteditable="true"], .ck-editor__editable, [contenteditable="true"]');
            if (!editorEl) return false;

            const ck = editorEl.ckeditorInstance
                || editorEl.closest('.ck-editor')?.ckeditorInstance
                || Array.from(document.querySelectorAll('.ck-editor__editable, [contenteditable="true"]')).find(x => x.ckeditorInstance)?.ckeditorInstance;

            if (ck) {
                let htmlParaInserir = html;
                if (html.includes('<div') && html.includes('</div>')) {
                    const match = html.match(/<div[^>]*>([\s\S]*?)<\/div>/i);
                    if (match && match[1]) {
                        htmlParaInserir = match[1];
                    }
                }

                if (typeof ck.setData === 'function') {
                    const atual = (ck.getData() || '').trim();
                    if (!atual || atual === '<p>&nbsp;</p>' || atual === '<p></p>') {
                        ck.setData(htmlParaInserir);
                        return true;
                    }
                }
                if (ck.model && typeof ck.model.change === 'function') {
                    const viewFragment = ck.data.processor.toView(htmlParaInserir);
                    const modelFragment = ck.data.toModel(viewFragment);
                    ck.model.insertContent(modelFragment);
                    return true;
                }
            }
        } catch (e) {
            console.warn('[Infojud] Não foi possível inserir direto no editor:', e);
        }
        return false;
    }

    // =================================================================================
    function renderizarPainelRelatorio(dadosRelatorio, opts = {}) {
        document.getElementById('god-relatorio-panel')?.remove();

        const painel = document.createElement('div');
        painel.id = 'god-relatorio-panel';
        painel.style.cssText = 'position:fixed;right:20px;top:150px;width:500px;max-width:92vw;background:#fff;border:2px solid #004d40;border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,0.4);font-family:"Segoe UI",sans-serif;z-index:10000;';

        // ── Cabeçalho (drag + collapse + copiar + fechar)
        const cab = document.createElement('div');
        cab.style.cssText = 'display:flex;justify-content:space-between;align-items:center;background:#004d40;color:#fff;padding:9px 14px;border-radius:8px 8px 0 0;cursor:grab;user-select:none;';

        const titulo = document.createElement('span');
        titulo.textContent = 'RELATÓRIO DE ENDEREÇOS';
        titulo.style.cssText = 'font-size:14px;font-weight:800;letter-spacing:.5px;cursor:pointer;';

        const ctrls = document.createElement('span');
        ctrls.style.cssText = 'display:flex;gap:8px;align-items:center;font-size:13px;font-weight:700;';

        const btnCopiar = document.createElement('span');
        btnCopiar.textContent = '📋';
        btnCopiar.title = 'Copiar todos os endereços';
        btnCopiar.style.cursor = 'pointer';
        btnCopiar.onclick = () => {
            const textoCompleto = (dadosRelatorio || []).join('\n\n---\n\n');
            if (typeof GM_setClipboard === 'function') {
                GM_setClipboard(textoCompleto);
            } else if (navigator.clipboard) {
                navigator.clipboard.writeText(textoCompleto);
            }
            mostrarNotificacao('Endereços copiados!', '#28a745');
        };

        const btnToggle = document.createElement('span');
        btnToggle.textContent = '▲';
        btnToggle.title = 'Minimizar / Expandir';
        btnToggle.style.cursor = 'pointer';

        const btnX = document.createElement('span');
        btnX.textContent = '✕';
        btnX.title = 'Fechar';
        btnX.style.cursor = 'pointer';
        btnX.onclick = () => painel.remove();

        ctrls.appendChild(btnCopiar);
        ctrls.appendChild(btnToggle);
        ctrls.appendChild(btnX);
        cab.appendChild(titulo);
        cab.appendChild(ctrls);
        painel.appendChild(cab);

        // ── Corpo
        const corpo = document.createElement('div');
        corpo.style.cssText = 'padding:12px 14px;max-height:440px;overflow-y:auto;user-select:text;';

        const blocks = (dadosRelatorio || []).slice();
        if (blocks.length === 0) {
            corpo.innerHTML = '<div style="padding:15px;text-align:center;color:#666;font-size:13px;">Nenhum endereço encontrado para os documentos pesquisados.</div>';
        } else {
            const S = { // estilos inline reutilizados
                empresa:  'font-size:15px;font-weight:800;color:#01579b;margin-bottom:3px;',
                endEmp:   'font-size:14px;color:#1a237e;margin-bottom:4px;padding-left:2px;',
                socio:    'font-size:14px;font-weight:700;color:#1a237e;margin-top:6px;margin-bottom:2px;padding:3px 8px;background:#e8eaf6;border-left:4px solid #3949ab;border-radius:0 4px 4px 0;',
                endSocio: 'font-size:14px;color:#283593;margin-bottom:2px;padding-left:12px;',
                cpfSocio: 'font-size:13px;color:#444;padding-left:12px;margin-bottom:2px;',
                pf:       'font-size:15px;font-weight:800;color:#4a148c;margin-bottom:3px;',
                cpfPf:    'font-size:14px;color:#444;margin-bottom:3px;',
                endPf:    'font-size:14px;color:#333;margin-bottom:2px;',
            };

            const htmlBlocks = blocks.map(b => {
                const lines = String(b).split('\n');
                let ctx = '';
                const parts = lines.map(l => {
                    if (l.startsWith('Empresa:')) {
                        ctx = 'empresa';
                        return `<div style="${S.empresa}">${escapeHtml(l)}</div>`;
                    }
                    if (l.startsWith('Sócio desta empresa:')) {
                        ctx = 'socio';
                        const val = l.replace(/^Sócio desta empresa:\s*/, '');
                        return `<div style="${S.socio}">Sócio: ${escapeHtml(val)}</div>`;
                    }
                    if (l.startsWith('Nome:')) {
                        ctx = 'pf';
                        const val = l.replace(/^Nome:\s*/, '');
                        return `<div style="${S.pf}">PESSOA FÍSICA: ${escapeHtml(val)}</div>`;
                    }
                    if (l.startsWith('CPF:')) {
                        return `<div style="${ctx === 'socio' ? S.cpfSocio : S.cpfPf}">${escapeHtml(l)}</div>`;
                    }
                    if (l.startsWith('Endereço:')) {
                        const val = l.replace(/^Endereço:\s*/, '');
                        if (ctx === 'socio') return `<div style="${S.endSocio}">Endereço: ${escapeHtml(val)}</div>`;
                        if (ctx === 'empresa') return `<div style="${S.endEmp}">Endereço: ${escapeHtml(val)}</div>`;
                        return `<div style="${S.endPf}">Endereço: ${escapeHtml(val)}</div>`;
                    }
                    return `<div style="font-size:14px;color:#333;">${escapeHtml(l)}</div>`;
                });
                return `<div style="padding:10px 10px 8px;border-radius:6px;background:#f5f5f5;border:1px solid #ddd;margin-bottom:10px;">${parts.join('')}</div>`;
            });
            corpo.innerHTML = htmlBlocks.join('');
        }

        painel.appendChild(corpo);

        // ── Rodapé com botão único: Gerar e Copiar Certidão
        const rodape = document.createElement('div');
        rodape.style.cssText = 'padding:10px 14px;background:#f1f8e9;border-top:1px solid #c8e6c9;border-radius:0 0 8px 8px;display:flex;justify-content:flex-end;align-items:center;';

        const btnGerarCertRodape = document.createElement('button');
        btnGerarCertRodape.textContent = '📜 Gerar e Copiar Certidão';
        btnGerarCertRodape.title = 'Gera e copia a certidão padronizada de pesquisa INFOJUD para colar no modelo';
        btnGerarCertRodape.style.cssText = `
            background: #2e7d32; color: #fff; border: none; border-radius: 4px;
            padding: 8px 16px; font-size: 13px; font-weight: 700; cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15); transition: background 0.15s, transform 0.05s;
        `;
        btnGerarCertRodape.onmouseenter = () => {
            if (!btnGerarCertRodape.dataset.copiado) btnGerarCertRodape.style.background = '#1b5e20';
        };
        btnGerarCertRodape.onmouseleave = () => {
            if (!btnGerarCertRodape.dataset.copiado) btnGerarCertRodape.style.background = '#2e7d32';
        };

        let timerFeedbackBtn = null;
        const acaoGerarCertidao = async () => {
            let itens = [];
            if (opts.itensCertidao && opts.itensCertidao.length) {
                itens = opts.itensCertidao;
            } else {
                for (const b of blocks) {
                    itens.push(...extrairItensDeBlocoTexto(b));
                }
            }

            if (!itens.length) {
                mostrarNotificacao('Nenhum dado de endereço para gerar certidão.', '#ff9800');
                return;
            }

            const htmlCertidao = construirHtmlCertidao(itens);
            const textoCertidao = construirTextoCertidao(itens);

            await copiarCertidaoParaClipboard(htmlCertidao, textoCertidao);
            tentarInserirNoCKEditor(htmlCertidao);

            btnGerarCertRodape.dataset.copiado = 'true';
            btnGerarCertRodape.textContent = 'certidão copiada, basta colar no modelo';
            btnGerarCertRodape.style.background = '#1b5e20';

            mostrarNotificacao('✅ Certidão copiada, basta colar no modelo', '#2e7d32');

            if (timerFeedbackBtn) clearTimeout(timerFeedbackBtn);
            timerFeedbackBtn = setTimeout(() => {
                delete btnGerarCertRodape.dataset.copiado;
                btnGerarCertRodape.textContent = '📜 Gerar e Copiar Certidão';
                btnGerarCertRodape.style.background = '#2e7d32';
            }, 6000);
        };

        btnGerarCertRodape.onclick = acaoGerarCertidao;
        rodape.appendChild(btnGerarCertRodape);
        painel.appendChild(rodape);

        document.body.appendChild(painel);

        // ── Collapse
        let recolhido = false;
        const toggleCorpo = () => {
            recolhido = !recolhido;
            corpo.style.display = recolhido ? 'none' : '';
            rodape.style.display = recolhido ? 'none' : 'flex';
            btnToggle.textContent = recolhido ? '▼' : '▲';
        };
        btnToggle.onclick = toggleCorpo;
        titulo.onclick = toggleCorpo;

        // ── Drag
        let dragging = false, ox = 0, oy = 0;
        cab.addEventListener('mousedown', e => {
            if (e.target === btnToggle || e.target === btnX || e.target === btnCopiar) return;
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

        // ── Botões no wrapper (apenas no ambiente de minutas)
        if (opts.isMinutas && (opts.onDireto || opts.onCorrecao)) {
            const wrapper = document.getElementById('god-btn-wrapper');
            const btnStyle = 'padding:8px 14px;color:white;font-weight:700;cursor:pointer;border-radius:6px;border:none;box-shadow:0 2px 6px rgba(0,0,0,0.18);font-size:13px;';
            const mkBtn = (txt, cb) => { const b = document.createElement('button'); b.textContent = txt; b.style.cssText = btnStyle + 'background:#0288d1;'; b.onclick = cb; return b; };
            if (wrapper) {
                wrapper.innerHTML = '';
                if (opts.onDireto) wrapper.appendChild(mkBtn('Infojud Direto', opts.onDireto));
                if (opts.onCorrecao) wrapper.appendChild(mkBtn('Infojud Correção', opts.onCorrecao));
            } else {
                const fallback = document.createElement('div');
                fallback.id = 'god-btn-wrapper';
                fallback.style.cssText = 'position:fixed;top:100px;right:20px;display:flex;gap:8px;z-index:9999;';
                if (opts.onDireto) fallback.appendChild(mkBtn('Infojud Direto', opts.onDireto));
                if (opts.onCorrecao) fallback.appendChild(mkBtn('Infojud Correção', opts.onCorrecao));
                document.body.appendChild(fallback);
            }
        }
    }

    // =================================================================================
    // PARTE 1.5: EXECUÇÃO NA ROTA /DETALHE (Via API de Partes + Dialog de Seleção)
    // =================================================================================

    function _xsrf() {
        const c = document.cookie.split(';').map(s => s.trim())
            .find(s => s.toLowerCase().startsWith('xsrf-token='));
        return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
    }

    function _headers() {
        const h = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Grau-Instancia': '1',
        };
        const x = _xsrf();
        if (x) h['X-XSRF-TOKEN'] = x;
        return h;
    }

    function _obterIdProcesso() {
        const m = window.location.pathname.match(/\/processo\/(\d+)/) ||
                  window.location.search.match(/processo=(\d+)/i);
        return m ? m[1] : null;
    }

    async function _fetchPartesProcesso(idProc) {
        const url = `${window.location.origin}/pje-comum-api/api/processos/id/${idProc}/partes`;
        const resp = await fetch(url, {
            method: 'GET',
            credentials: 'include',
            headers: _headers(),
        });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}: Falha ao buscar partes do processo`);
        }
        return await resp.json();
    }

    function _extrairPartesParaDialog(raw) {
        const parseItem = (p, polo) => {
            const nome = (p.nome || '').trim();
            const docBruto = (p.documento || p.documentoPrincipal || p.pessoaFisica?.numeroDocumento || p.pessoaJuridica?.numeroDocumento || '').trim();
            const docLimpo = apenasNumeros(docBruto);
            const valido = (docLimpo.length === 11 || docLimpo.length === 14);
            const tipo = docLimpo.length === 14 ? 'CNPJ' : (docLimpo.length === 11 ? 'CPF' : 'OUTRO');
            return {
                id: p.id || p.idPessoa || Math.random().toString(36).slice(2),
                nome: nome,
                documento: docLimpo,
                documentoFormatado: formatarDocumento(docLimpo) || docBruto || '(sem documento)',
                valido: valido,
                polo: polo,
                tipoPessoa: tipo
            };
        };

        const passivo = (raw && raw.PASSIVO ? raw.PASSIVO : []).map(p => parseItem(p, 'PASSIVO'));
        const ativo = (raw && raw.ATIVO ? raw.ATIVO : []).map(p => parseItem(p, 'ATIVO'));
        const outros = (raw && raw.TERCEIROS ? raw.TERCEIROS : []).map(p => parseItem(p, 'TERCEIROS'));

        return { passivo, ativo, outros };
    }

    function _removerDuplicados(lista) {
        const vistos = new Set();
        return (lista || []).filter(item => {
            const key = item.documento ? item.documento : (item.nome || '').toUpperCase();
            if (vistos.has(key)) return false;
            vistos.add(key);
            return true;
        });
    }

    function abrirDialogSelecaoPartes(grupos, onConfirm) {
        document.getElementById('pjetools-infojud-modal-backdrop')?.remove();

        const backdrop = document.createElement('div');
        backdrop.id = 'pjetools-infojud-modal-backdrop';
        backdrop.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.55); z-index: 100000;
            display: flex; align-items: center; justify-content: center;
            backdrop-filter: blur(2px); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        `;

        const modal = document.createElement('div');
        modal.id = 'pjetools-infojud-modal';
        modal.style.cssText = `
            width: 580px; max-width: 95vw; max-height: 85vh;
            background: #ffffff; border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
            display: flex; flex-direction: column; overflow: hidden;
        `;

        // ── Cabeçalho
        const header = document.createElement('div');
        header.style.cssText = `
            background: linear-gradient(135deg, #004d40, #00695c);
            color: #ffffff; padding: 14px 18px;
            display: flex; align-items: center; justify-content: space-between;
            user-select: none;
        `;
        const headerTitle = document.createElement('div');
        headerTitle.innerHTML = '<span style="font-size:16px;font-weight:700;">🏛️ Infojud — Selecionar Partes</span>';

        const btnFechar = document.createElement('button');
        btnFechar.innerHTML = '✕';
        btnFechar.title = 'Fechar';
        btnFechar.style.cssText = `
            background: transparent; border: none; color: #fff;
            font-size: 18px; cursor: pointer; padding: 0 6px; line-height: 1;
            opacity: 0.85; transition: opacity 0.15s;
        `;
        btnFechar.onmouseenter = () => btnFechar.style.opacity = '1';
        btnFechar.onmouseleave = () => btnFechar.style.opacity = '0.85';
        btnFechar.onclick = () => backdrop.remove();

        header.appendChild(headerTitle);
        header.appendChild(btnFechar);
        modal.appendChild(header);

        // ── Barra de Ações Rápidas
        const actionBar = document.createElement('div');
        actionBar.style.cssText = `
            background: #f8f9fa; border-bottom: 1px solid #e9ecef;
            padding: 8px 16px; display: flex; align-items: center;
            justify-content: space-between; flex-wrap: wrap; gap: 8px; font-size: 12px;
        `;
        const subTitle = document.createElement('span');
        subTitle.textContent = 'Marque quem deseja pesquisar:';
        subTitle.style.cssText = 'color: #495057; font-weight: 600;';

        const pillContainer = document.createElement('div');
        pillContainer.style.cssText = 'display: flex; gap: 6px;';

        const criarPill = (txt, onClick) => {
            const b = document.createElement('button');
            b.type = 'button';
            b.textContent = txt;
            b.style.cssText = `
                background: #ffffff; border: 1px solid #ced4da;
                border-radius: 12px; padding: 3px 10px; font-size: 11px;
                cursor: pointer; font-weight: 600; color: #495057;
                transition: all 0.15s;
            `;
            b.onmouseenter = () => { b.style.background = '#e9ecef'; b.style.borderColor = '#adb5bd'; };
            b.onmouseleave = () => { b.style.background = '#ffffff'; b.style.borderColor = '#ced4da'; };
            b.onclick = onClick;
            return b;
        };

        const pillPassivo = criarPill('Apenas Polo Passivo', () => setSelecao('PASSIVO'));
        const pillTodos = criarPill('Todos', () => setSelecao('TODOS'));
        const pillNenhum = criarPill('Nenhum', () => setSelecao('NENHUM'));
        pillContainer.appendChild(pillPassivo);
        pillContainer.appendChild(pillTodos);
        pillContainer.appendChild(pillNenhum);

        actionBar.appendChild(subTitle);
        actionBar.appendChild(pillContainer);
        modal.appendChild(actionBar);

        // ── Corpo da Lista (Scrollable)
        const body = document.createElement('div');
        body.style.cssText = `
            padding: 14px 18px; overflow-y: auto; flex: 1;
            display: flex; flex-direction: column; gap: 12px;
            max-height: 55vh;
        `;

        const checkboxes = [];

        function renderizarSecao(titulo, partes, corPolo) {
            if (!partes || !partes.length) return;

            const secao = document.createElement('div');
            secao.style.cssText = 'display: flex; flex-direction: column; gap: 6px;';

            const secHeader = document.createElement('div');
            secHeader.style.cssText = `
                font-size: 11px; font-weight: 700; color: ${corPolo};
                text-transform: uppercase; letter-spacing: 0.5px;
                padding-bottom: 2px; border-bottom: 1px solid #e0e0e0;
                display: flex; justify-content: space-between;
            `;
            secHeader.innerHTML = `<span>${titulo}</span><span style="color:#888;">${partes.length} parte(s)</span>`;
            secao.appendChild(secHeader);

            partes.forEach(p => {
                const row = document.createElement('label');
                row.style.cssText = `
                    display: flex; align-items: center; gap: 10px;
                    padding: 8px 10px; border: 1px solid #dee2e6;
                    border-radius: 6px; background: #fff;
                    cursor: ${p.valido ? 'pointer' : 'not-allowed'};
                    opacity: ${p.valido ? '1' : '0.6'};
                    transition: background 0.15s, border-color 0.15s;
                    user-select: none; margin: 0;
                `;

                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = p.documento;
                cb.disabled = !p.valido;
                cb.dataset.polo = p.polo;
                cb.style.cssText = 'width: 16px; height: 16px; cursor: inherit; margin: 0;';

                // Pré-seleciona quem tem documento válido no polo passivo
                if (p.valido && p.polo === 'PASSIVO') {
                    cb.checked = true;
                    row.style.background = '#e0f2f1';
                    row.style.borderColor = '#80cbc4';
                }

                cb.onchange = () => {
                    atualizarEstiloRow(row, cb.checked);
                    atualizarContador();
                };

                const infoBox = document.createElement('div');
                infoBox.style.cssText = 'flex: 1; display: flex; flex-direction: column; gap: 2px;';

                const nomeRow = document.createElement('div');
                nomeRow.style.cssText = 'font-size: 13px; font-weight: 600; color: #212529; line-height: 1.3;';
                nomeRow.textContent = p.nome || '(sem nome cadastrado)';

                const metaRow = document.createElement('div');
                metaRow.style.cssText = 'display: flex; align-items: center; gap: 6px; font-size: 11px;';

                let badgeTipo = '';
                if (p.tipoPessoa === 'CNPJ') {
                    badgeTipo = '<span style="background:#fff3e0;color:#e65100;font-weight:700;padding:1px 5px;border-radius:3px;">CNPJ</span>';
                } else if (p.tipoPessoa === 'CPF') {
                    badgeTipo = '<span style="background:#e3f2fd;color:#0d47a1;font-weight:700;padding:1px 5px;border-radius:3px;">CPF</span>';
                } else {
                    badgeTipo = '<span style="background:#f5f5f5;color:#616161;font-weight:700;padding:1px 5px;border-radius:3px;">SEM DOC</span>';
                }

                const docSpan = document.createElement('span');
                docSpan.style.cssText = 'font-family: monospace; color: #495057; font-weight: 500;';
                docSpan.textContent = p.documentoFormatado;

                metaRow.innerHTML = badgeTipo;
                metaRow.appendChild(docSpan);

                infoBox.appendChild(nomeRow);
                infoBox.appendChild(metaRow);

                row.appendChild(cb);
                row.appendChild(infoBox);
                secao.appendChild(row);

                checkboxes.push({ cb, row, parte: p });
            });

            body.appendChild(secao);
        }

        renderizarSecao('Polo Passivo (Réus / Executados)', grupos.passivo, '#c62828');
        renderizarSecao('Polo Ativo (Autores / Exequentes)', grupos.ativo, '#1565c0');
        renderizarSecao('Outros / Terceiros', grupos.outros, '#6a1b9a');

        modal.appendChild(body);

        function atualizarEstiloRow(row, checked) {
            if (checked) {
                row.style.background = '#e0f2f1';
                row.style.borderColor = '#80cbc4';
            } else {
                row.style.background = '#ffffff';
                row.style.borderColor = '#dee2e6';
            }
        }

        function setSelecao(modo) {
            checkboxes.forEach(({ cb, row, parte }) => {
                if (!parte.valido) return;
                if (modo === 'TODOS') cb.checked = true;
                else if (modo === 'NENHUM') cb.checked = false;
                else if (modo === 'PASSIVO') cb.checked = (parte.polo === 'PASSIVO');
                atualizarEstiloRow(row, cb.checked);
            });
            atualizarContador();
        }

        // ── Rodapé
        const footer = document.createElement('div');
        footer.style.cssText = `
            background: #fafafa; border-top: 1px solid #e9ecef;
            padding: 12px 18px; display: flex; align-items: center;
            justify-content: space-between; user-select: none;
        `;

        const contador = document.createElement('span');
        contador.id = 'infojud-dialog-contador';
        contador.style.cssText = 'font-size: 13px; color: #495057; font-weight: 600;';

        const btnContainer = document.createElement('div');
        btnContainer.style.cssText = 'display: flex; gap: 8px;';

        const btnCancelar = document.createElement('button');
        btnCancelar.type = 'button';
        btnCancelar.textContent = 'Cancelar';
        btnCancelar.style.cssText = `
            padding: 8px 14px; background: #e9ecef; color: #495057;
            border: none; border-radius: 5px; font-weight: 600;
            font-size: 13px; cursor: pointer; transition: background 0.15s;
        `;
        btnCancelar.onmouseenter = () => btnCancelar.style.background = '#dee2e6';
        btnCancelar.onmouseleave = () => btnCancelar.style.background = '#e9ecef';
        btnCancelar.onclick = () => backdrop.remove();

        const btnOk = document.createElement('button');
        btnOk.type = 'button';
        btnOk.id = 'infojud-dialog-btn-ok';
        btnOk.textContent = '🔍 Pesquisar';
        btnOk.style.cssText = `
            padding: 8px 18px; background: #004d40; color: #ffffff;
            border: none; border-radius: 5px; font-weight: 700;
            font-size: 13px; cursor: pointer; transition: background 0.15s, opacity 0.15s;
            box-shadow: 0 2px 6px rgba(0,77,64,0.3);
        `;
        btnOk.onmouseenter = () => { if (!btnOk.disabled) btnOk.style.background = '#00695c'; };
        btnOk.onmouseleave = () => { if (!btnOk.disabled) btnOk.style.background = '#004d40'; };

        btnOk.onclick = () => {
            const selecionados = checkboxes
                .filter(({ cb }) => cb.checked)
                .map(({ parte }) => parte);

            if (!selecionados.length) {
                alert('Selecione pelo menos uma parte com CPF ou CNPJ para pesquisar.');
                return;
            }

            backdrop.remove();
            if (typeof onConfirm === 'function') {
                onConfirm(selecionados);
            }
        };

        btnContainer.appendChild(btnCancelar);
        btnContainer.appendChild(btnOk);
        footer.appendChild(contador);
        footer.appendChild(btnContainer);
        modal.appendChild(footer);

        backdrop.appendChild(modal);
        document.body.appendChild(backdrop);

        function atualizarContador() {
            const count = checkboxes.filter(({ cb }) => cb.checked).length;
            contador.textContent = `${count} parte(s) selecionada(s)`;
            btnOk.disabled = (count === 0);
            btnOk.style.opacity = (count === 0) ? '0.5' : '1';
            btnOk.style.cursor = (count === 0) ? 'not-allowed' : 'pointer';
        }

        atualizarContador();

        // Fechar com Esc ou clique no backdrop
        const onKeyDown = (e) => {
            if (e.key === 'Escape') {
                backdrop.remove();
                document.removeEventListener('keydown', onKeyDown);
            }
        };
        document.addEventListener('keydown', onKeyDown);
        backdrop.onclick = (e) => {
            if (e.target === backdrop) {
                backdrop.remove();
                document.removeEventListener('keydown', onKeyDown);
            }
        };
    }

    function consultarDocInfojud(doc, nome) {
        return new Promise((resolve) => {
            const docNumerico = apenasNumeros(doc);
            if (docNumerico.length !== 11 && docNumerico.length !== 14) {
                resolve({ sucesso: false, erro: 'Documento inválido' });
                return;
            }

            const tipoOrigem = docNumerico.length === 11 ? 'CPF_DIRETO' : 'CNPJ_NORMAL';
            const url = (docNumerico.length === 11 ? URL_BASE_CPF : URL_BASE_CNPJ) + encodeURIComponent(docNumerico);

            const agora = Date.now();
            _gmSet('GOD_STATUS', 'STANDBY_' + agora);
            _gmSet('GOD_DADOS_CAPTURA', '{}');
            _gmSet('GOD_TIPO_ORIGEM', tipoOrigem);

            console.log('[Infojud Detalhe] Abrindo consulta em segundo plano:', url, 'para:', nome || docNumerico);
            const tabAba = _gmOpenTab(url, { active: false, insert: true });

            const fecharAba = () => {
                if (tabAba && typeof tabAba.close === 'function') {
                    try { tabAba.close(); } catch (e) {}
                }
            };

            const timer = setInterval(() => {
                const status = _gmGet('GOD_STATUS', '') || '';
                const decorrido = Date.now() - agora;

                if (status.startsWith('DADOS_PRONTOS_')) {
                    const ts = parseInt(status.split('_')[2] || '0', 10);
                    if (ts >= (agora - 1000)) {
                        clearInterval(timer);
                        fecharAba();
                        try {
                            const raw = _gmGet('GOD_DADOS_CAPTURA', '{}') || '{}';
                            const dados = JSON.parse(raw);
                            try { _gmSet('GOD_DADOS_' + docNumerico, JSON.stringify(dados)); } catch (e) {}
                            resolve({ sucesso: true, dados: dados });
                        } catch (e) {
                            resolve({ sucesso: false, erro: 'Erro ao interpretar resposta da Receita' });
                        }
                    }
                } else if (status.startsWith('PULAR_')) {
                    const ts = parseInt(status.split('_')[1] || '0', 10);
                    if (ts >= (agora - 1000)) {
                        clearInterval(timer);
                        fecharAba();
                        resolve({ sucesso: false, erro: 'Receita sinalizou sem dados ou erro' });
                    }
                } else if (decorrido > 35000) {
                    clearInterval(timer);
                    fecharAba();
                    console.warn('[Infojud Detalhe] Watchdog: timeout aguardando Receita para doc:', docNumerico);
                    resolve({ sucesso: false, erro: 'Tempo limite esgotado' });
                }
            }, 400);
        });
    }

    async function executarPesquisaInfojudPartes(partesSelecionadas) {
        if (!partesSelecionadas || !partesSelecionadas.length) {
            mostrarNotificacao('Nenhuma parte selecionada para consulta.', '#dc3545');
            return;
        }

        document.getElementById('god-relatorio-panel')?.remove();

        const dadosRelatorio = [];
        const itensCertidao = [];
        const dadosRelatorioKeys = new Set();
        const total = partesSelecionadas.length;

        mostrarNotificacao(`Iniciando pesquisa Infojud para ${total} parte(s)...`, '#0288d1');

        for (let i = 0; i < total; i++) {
            const parte = partesSelecionadas[i];
            const doc = apenasNumeros(parte.documento);
            const nome = parte.nome || '';

            mostrarNotificacao(`Infojud (${i + 1}/${total}): Consultando ${nome || formatarDocumento(doc)}...`, '#0288d1', true);

            if (i > 0) {
                const jitter = 1000 + Math.floor(Math.random() * 1200);
                await wait(jitter);
            }

            const res = await consultarDocInfojud(doc, nome);
            const docKey = doc;

            if (res.sucesso && res.dados) {
                const d = res.dados;
                if (!dadosRelatorioKeys.has(docKey)) {
                    dadosRelatorioKeys.add(docKey);
                    if (doc.length === 11) {
                        const pf = {
                            nome: d.nome || nome || '',
                            cpf: d.cpf || doc,
                            rua: d.rua || '',
                            numero: d.numero || '',
                            complemento: d.complemento || '',
                            bairro: d.bairro || '',
                            municipio: d.municipio || '',
                            uf: d.uf || '',
                            cep: d.cep || ''
                        };
                        dadosRelatorio.push(montarRelatorio(pf));
                        itensCertidao.push({
                            nome: pf.nome,
                            documento: formatarDocumento(pf.cpf),
                            tipoDoc: 'CPF',
                            identificacao: `${(pf.nome || 'Parte').trim()} - CPF ${formatarDocumento(pf.cpf)}`,
                            endereco: formatarEnderecoCertidao(pf)
                        });
                    } else {
                        const empresaEntry = {
                            empresaNome: d.empresaNome || nome || '',
                            cnpj: d.cnpj || doc,
                            empresaEnderecoRaw: d.empresaEnderecoRaw || '',
                            empresaEndereco: d.empresaEndereco || null,
                            empresaCep: d.empresaCep || '',
                            nome: d.nome || d.cpfResponsavel || '',
                            cpf: d.cpf || d.cpfResponsavel || '',
                            rua: d.rua || '',
                            numero: d.numero || '',
                            complemento: d.complemento || '',
                            bairro: d.bairro || '',
                            municipio: d.municipio || '',
                            uf: d.uf || '',
                            cep: d.cep || ''
                        };
                        dadosRelatorio.push(montarRelatorio(empresaEntry));
                        itensCertidao.push({
                            nome: empresaEntry.empresaNome,
                            documento: formatarDocumento(empresaEntry.cnpj),
                            tipoDoc: 'CNPJ',
                            identificacao: `${(empresaEntry.empresaNome || 'Empresa').trim()} - CNPJ ${formatarDocumento(empresaEntry.cnpj)}`,
                            endereco: formatarEnderecoCertidaoEmpresa(empresaEntry)
                        });
                        if (d.nome && d.cpf) {
                            itensCertidao.push({
                                nome: d.nome,
                                documento: formatarDocumento(d.cpf),
                                tipoDoc: 'CPF',
                                identificacao: `${d.nome.trim()} (sócio) - CPF ${formatarDocumento(d.cpf)}`,
                                endereco: formatarEnderecoCertidao(d)
                            });
                        }
                    }
                }
            } else {
                if (!dadosRelatorioKeys.has(docKey)) {
                    dadosRelatorioKeys.add(docKey);
                    if (doc.length === 11) {
                        const pfNome = nome || 'Pessoa Física';
                        dadosRelatorio.push(`Nome: ${pfNome}\nCPF: ${formatarDocumento(doc)}\nEndereço: (Não localizado ou sem retorno na Receita Federal)`);
                        itensCertidao.push({
                            nome: pfNome,
                            documento: formatarDocumento(doc),
                            tipoDoc: 'CPF',
                            identificacao: `${pfNome.trim()} - CPF ${formatarDocumento(doc)}`,
                            endereco: 'Endereço não localizado na pesquisa INFOJUD'
                        });
                    } else {
                        const pjNome = nome || 'Pessoa Jurídica';
                        dadosRelatorio.push(`Empresa: ${pjNome}\nCNPJ: ${formatarDocumento(doc)}\nEndereço: (Não localizado ou sem retorno na Receita Federal)`);
                        itensCertidao.push({
                            nome: pjNome,
                            documento: formatarDocumento(doc),
                            tipoDoc: 'CNPJ',
                            identificacao: `${pjNome.trim()} - CNPJ ${formatarDocumento(doc)}`,
                            endereco: 'Endereço não localizado na pesquisa INFOJUD'
                        });
                    }
                }
            }
        }

        mostrarNotificacao(`Pesquisa Infojud finalizada! (${total} partes processadas)`, '#28a745', false);
        renderizarPainelRelatorio(dadosRelatorio, { isMinutas: false, itensCertidao: itensCertidao });
    }

    async function executarInfojudDetalhe() {
        const idProc = _obterIdProcesso();
        if (!idProc) {
            mostrarNotificacao('Abra os detalhes de um processo para consultar o Infojud.', '#dc3545');
            return;
        }

        mostrarNotificacao('Buscando partes do processo...', '#0288d1', true);

        let raw;
        try {
            raw = await _fetchPartesProcesso(idProc);
        } catch (e) {
            console.error('[Infojud Detalhe] Falha ao consultar partes:', e);
            mostrarNotificacao('Erro ao buscar partes: ' + e.message, '#dc3545');
            return;
        }

        const grupos = _extrairPartesParaDialog(raw);
        grupos.passivo = _removerDuplicados(grupos.passivo);
        grupos.ativo = _removerDuplicados(grupos.ativo);
        grupos.outros = _removerDuplicados(grupos.outros);

        const totalPartes = grupos.passivo.length + grupos.ativo.length + grupos.outros.length;
        if (totalPartes === 0) {
            mostrarNotificacao('Nenhuma parte encontrada no processo.', '#ff9800');
            return;
        }

        abrirDialogSelecaoPartes(grupos, async (selecionados) => {
            await executarPesquisaInfojudPartes(selecionados);
        });
    }

    // Exportação para o contexto global / PJeTools
    _win.executarInfojudDetalhe = window.executarInfojudDetalhe = executarInfojudDetalhe;
    _win.consultarDocInfojud = window.consultarDocInfojud = consultarDocInfojud;
    _win.renderizarPainelRelatorio = window.renderizarPainelRelatorio = renderizarPainelRelatorio;
    _win.abrirDialogSelecaoPartes = window.abrirDialogSelecaoPartes = abrirDialogSelecaoPartes;

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
            mostrarNotificacao('Falha: Nenhum registro. Fechando aba...', '#dc3545', false);
            try { if (window.opener && !window.opener.closed) window.opener.focus(); } catch (e) {}
            setTimeout(() => { try { window.close(); } catch (e) {} }, 400);
            return;
        }
        setTimeout(() => {
            const cnpjDados = extrairDadosCNPJPage();
            const cpf = cnpjDados.cpfResponsavel || '';
            if (cnpjDados.empresaNome) {
                _gmSet('GOD_DADOS_CAPTURA', JSON.stringify(cnpjDados));
            }
            if (cpf && cpf.length === 11) {
                mostrarNotificacao('CNPJ Direcionando para CPF...', '#0288d1', false);
                _gmOpenTab(URL_BASE_CPF + cpf, { active: false, insert: true });
                setTimeout(() => { try { window.close(); } catch (e) {} }, 500);
            } else if (cnpjDados.empresaNome && (cnpjDados.empresaEnderecoRaw || cnpjDados.empresaCep)) {
                _gmSet('GOD_STATUS', 'DADOS_PRONTOS_' + Date.now());
                mostrarNotificacao('DADOS CNPJ OK! Retornando ao PJe...', '#28a745', false);
                _devolverFocoPJe();
                setTimeout(() => { try { window.close(); } catch (e) {} }, 400);
            } else {
                _gmSet('GOD_STATUS', 'PULAR_' + Date.now());
                mostrarNotificacao('Nenhum dado ou CPF elegível encontrado. Fechando...', '#ffc107', false);
                try { if (window.opener && !window.opener.closed) window.opener.focus(); } catch (e) {}
                setTimeout(() => { try { window.close(); } catch (e) {} }, 400);
            }
        }, 800);
    } 
    else if (URL_ATUAL.includes('detalheNICPF.asp')) {
        setTimeout(() => {
            try {
                const rawCaptura = _gmGet('GOD_DADOS_CAPTURA', '{}') || '{}';
                const base = JSON.parse(rawCaptura.trim() || '{}') || {};
                const cpfDados = extrairDadosCPFPage();
                const merged = Object.assign({}, base, cpfDados, {
                    tipoOrigem: _gmGet('GOD_TIPO_ORIGEM', 'CNPJ_NORMAL')
                });

                if (merged.cep || merged.rua || merged.endRaw) {
                    _gmSet('GOD_DADOS_CAPTURA', JSON.stringify(merged));
                    _gmSet('GOD_STATUS', 'DADOS_PRONTOS_' + Date.now());
                    console.log('[Infojud Receita] Dados extraídos e enviados ao AUD:', merged);
                    mostrarNotificacao('DADOS OK! Retornando ao PJe...', '#28a745', false);
                    _devolverFocoPJe();
                    setTimeout(() => { try { window.close(); } catch (e) {} }, 400);
                } else {
                    throw new Error('Dados incompletos');
                }
            } catch (e) {
                console.error(e);
                _gmSet('GOD_STATUS', 'PULAR_' + Date.now());
                mostrarNotificacao('Erro na Leitura da Receita. Fechando...', '#dc3545', false);
                _devolverFocoPJe();
                setTimeout(() => { try { window.close(); } catch (e) {} }, 400);
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