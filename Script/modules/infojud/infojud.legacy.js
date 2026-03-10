
(function () {
    'use strict';

    const URL_ATUAL = window.location.href;
    const URL_BASE_CNPJ = 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI=';
    const URL_BASE_CPF = 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp?NI=';

    const wait = (ms) => new Promise(r => setTimeout(r, ms));
    const normalizar = (txt) => (txt || '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/\s+/g, ' ').trim();
    const apenasNumeros = (txt) => (txt || '').replace(/\D/g, '');

    // --- FUZZY ---
    function similaridade(s1, s2) {
        s1 = s1.toUpperCase(); s2 = s2.toUpperCase();
        if (s1 === s2) return 1.0;
        if ((s1 === 'JARDIM' && s2 === 'JD') || (s1 === 'JD' && s2 === 'JARDIM')) return 0.95;
        if ((s1 === 'PARQUE' && s2 === 'PQ') || (s1 === 'PQ' && s2 === 'PARQUE')) return 0.95;
        if ((s1 === 'VILA' && s2 === 'VL') || (s1 === 'VL' && s2 === 'VILA')) return 0.95;
        if ((s1 === 'AVENIDA' && s2 === 'AV') || (s1 === 'AV' && s2 === 'AVENIDA')) return 0.95;
        if ((s1 === 'RUA' && s2 === 'R') || (s1 === 'R' && s2 === 'RUA')) return 0.95;

        const costs = [];
        for (let i = 0; i <= s1.length; i++) {
            let lastValue = i;
            for (let j = 0; j <= s2.length; j++) {
                if (i === 0) costs[j] = j;
                else if (j > 0) {
                    let newValue = costs[j - 1];
                    if (s1.charAt(i - 1) !== s2.charAt(j - 1)) newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                    costs[j - 1] = lastValue;
                    lastValue = newValue;
                }
            }
            if (i > 0) costs[s2.length] = lastValue;
        }
        const longer = Math.max(s1.length, s2.length);
        return (longer - costs[s2.length]) / parseFloat(longer);
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
                console.log(`[GOD] Match Fuzzy encontrado. Removendo trecho...`);
                const trechoEncontrado = palavrasComp.slice(i, i + palavrasBairro.length).join('.*?');
                const regexRemove = new RegExp(trechoEncontrado + '.*?(\\s|$)', 'i');
                return complemento.replace(regexRemove, '').trim().replace(/^[-, \.\s]+/, '');
            }
        }
        return complemento;
    }

    // =================================================================================
    // PARTE 1: PJE
    // =================================================================================
    if (URL_ATUAL.includes('pje.trt2.jus.br') && URL_ATUAL.includes('/comunicacoesprocessuais/minutas')) {
        console.log('[GOD] Modo PJe Ativo (v17.0)');

        let filaDocs = [];
        let atual = 0;
        let rodando = false;
        let ultimoProcessado = '';
        let MODO_EXECUCAO = '';
        let dadosRelatorio = [];

        // --- BOTOES ---
        function criarBotoes() {
            if (document.getElementById('god-btn-container')) return;

            const container = document.createElement('div');
            container.id = 'god-btn-container';
            container.style.cssText = 'position:fixed;top:100px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:5px;';
            const styleBtn = 'padding:10px 20px;color:white;font-weight:bold;cursor:pointer;border-radius:4px;box-shadow:0 3px 6px rgba(0,0,0,0.3);font-size:14px;border:none;';

            const btnDireto = document.createElement('button');
            btnDireto.textContent = 'Infojud Direto';
            btnDireto.style.cssText = styleBtn + 'background:#0288d1;';
            btnDireto.onclick = () => iniciarFluxo('DIRETO');

            const btnCorrecao = document.createElement('button');
            btnCorrecao.textContent = 'Infojud Correção';
            btnCorrecao.style.cssText = styleBtn + 'background:#004d40;';
            btnCorrecao.onclick = () => iniciarFluxo('COMPLETO');

            container.appendChild(btnDireto);
            container.appendChild(btnCorrecao);
            document.body.appendChild(container);
        }

        criarBotoes();
        window.addEventListener('load', criarBotoes);
        setTimeout(criarBotoes, 2000);

        function iniciarFluxo(modo) {
            MODO_EXECUCAO = modo;
            const spans = Array.from(document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
            filaDocs = [];
            dadosRelatorio = [];
            const vistos = new Set();
            spans.forEach(s => {
                let txt = s.textContent.trim();
                if (/\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/.test(txt)) {
                    let num = txt.replace(/\D/g, '');
                    if (!vistos.has(num)) {
                        vistos.add(num);
                        filaDocs.push(num);
                    }
                }
            });

            if (!filaDocs.length) return alert('Nenhum documento encontrado!');

            const oldR = document.getElementById('god-relatorio-panel');
            if (oldR) oldR.remove();

            rodando = true;
            atual = 0;
            ultimoProcessado = '';
            GM_setValue('GOD_STATUS', 'STANDBY');

            console.log(`[GOD] Iniciando Modo: ${MODO_EXECUCAO}`);
            monitorarSinais();
            processarProximo();
        }

        function processarProximo() {
            if (atual >= filaDocs.length) {
                console.log('[GOD] Ciclo finalizado!');
                salvarGeralFinal();
                exibirRelatorioFinal();
                rodando = false;
                return;
            }

            const doc = filaDocs[atual];
            const linha = encontrarLinhaPorDoc(doc);
            if (linha) {
                linha.style.backgroundColor = '#fff9c4';
                linha.scrollIntoView({ block: 'center', behavior: 'smooth' });
            }

            if (doc.length === 11) {
                GM_setValue('GOD_TIPO_ORIGEM', 'CPF_DIRETO');
                GM_openInTab(URL_BASE_CPF + doc, { active: true, insert: true });
            } else {
                GM_setValue('GOD_TIPO_ORIGEM', 'CNPJ_NORMAL');
                GM_openInTab(URL_BASE_CNPJ + doc, { active: true, insert: true });
            }
        }

        function encontrarLinhaPorDoc(docNumerico) {
            const spans = Array.from(document.querySelectorAll('span.pec-formatacao-padrao-dados-parte'));
            for (let s of spans) {
                if (s.textContent.replace(/\D/g, '') === docNumerico) {
                    return s.closest('tr');
                }
            }
            return null;
        }

        function monitorarSinais() {
            if (!rodando) return;
            const status = GM_getValue('GOD_STATUS', '');

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
            // d = {cep: "12345678", rua: "RUA X", numero: "123", ...}
            console.log('[GOD] Verificando se endereço já existe na tabela...');

            // Localiza a tabela pelo atributo "nametabela" ou pela classe
            const tabela = document.querySelector('pje-data-table[nametabela="Endereços do destinatário no sistema"] table') ||
                document.querySelector('table[name="Endereços do destinatário no sistema"]');

            if (!tabela) { console.log('[GOD] Tabela de endereços não encontrada.'); return false; }

            const linhas = Array.from(tabela.querySelectorAll('tbody tr'));

            for (let tr of linhas) {
                const colunas = tr.querySelectorAll('td');
                if (colunas.length < 5) continue; // Precisa ter colunas suficientes

                // Índices baseados no HTML fornecido (assumindo ordem: Botão, CEP, Logradouro, Número, Bairro...)
                // 1: CEP, 2: Logradouro, 3: Número
                const cepTabela = apenasNumeros(colunas[1].textContent);
                const ruaTabela = normalizar(colunas[2].textContent);
                const numTabela = normalizar(colunas[3].textContent);

                const cepNovo = d.cep;
                const ruaNova = normalizar(d.rua || d.endRaw); // Fallback se d.rua vier vazio
                const numNovo = normalizar(d.numero);

                // Critérios de Match
                const matchCep = cepTabela === cepNovo;
                const matchNum = numTabela === numNovo || (numNovo === 'SN' && numTabela === 'S/N');

                // Fuzzy para Rua (Logradouro)
                const simRua = similaridade(ruaTabela, ruaNova);
                const matchRua = simRua > 0.8 || ruaTabela.includes(ruaNova) || ruaNova.includes(ruaTabela);

                if (matchCep && matchNum && matchRua) {
                    console.log(`[GOD] ENDEREÇO JÁ EXISTE! Usando linha da tabela. (Sim: ${simRua.toFixed(2)})`);

                    // Clica na seta (fa-arrow-up) da primeira coluna
                    const btnSeta = colunas[0].querySelector('.fa-arrow-up');
                    if (btnSeta) {
                        (btnSeta.closest('button') || btnSeta).click();
                        return true; // Sucesso, endereço selecionado
                    }
                }
            }
            console.log('[GOD] Endereço não encontrado na tabela. Cadastrando novo...');
            return false;
        }

        async function aplicarLogicaMaster() {
            try {
                const docAtual = filaDocs[atual];
                const linha = encontrarLinhaPorDoc(docAtual);
                if (!linha) throw new Error(`Linha não encontrada`);

                const btnEnvelope = linha.querySelector('.fa-envelope');
                if (!btnEnvelope) throw new Error('Envelope sumiu');

                const d = JSON.parse(GM_getValue('GOD_DADOS_CAPTURA', '{}'));

                // --- RELATÓRIO ---
                const nomes = (d.nome || '').split(' ');
                const nomeFmt = nomes.length > 1 ? `${nomes[0]} ${nomes[1]}` : nomes[0];
                const linhaRel = `(${nomeFmt}) - (${d.cep}) - (${d.rua || ''} ${d.numero || 'S/N'}) - (${d.complemento || ''})`;
                dadosRelatorio.push(linhaRel.replace(/\s+/g, ' '));

                btnEnvelope.click();
                await esperarModal('mat-dialog-container');
                await wait(1500); // Espera tabela carregar

                // --- CHECK DE DUPLICIDADE ---
                const jaExiste = await verificarExistenciaNaTabela(d);

                if (jaExiste) {
                    // Se já existe, ele clicou na seta. O modal deve fechar ou atualizar.
                    // Geralmente ao clicar na seta o endereço é vinculado e o modal pode fechar ou precisar de "Salvar"
                    // Vamos assumir que precisa Salvar para confirmar a seleção, ou apenas fechar.
                    // Por garantia, tentamos clicar em Salvar Modal se ele ainda estiver aberto.

                    await wait(1000);
                    const btnSalvar = document.querySelector('.botao-salvar') || document.querySelector('button[mattooltip="Salva as alterações"]');
                    if (btnSalvar && document.body.contains(btnSalvar)) btnSalvar.click();

                } else {
                    // --- FLUXO DE CADASTRO NOVO (Se não existe) ---

                    // Preenche CEP
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
                    if (inputBairro && inputBairro.value) {
                        complFinal = limparBairroFuzzy(complFinal, inputBairro.value);
                    }

                    let n = document.querySelector('#inputNumero');
                    let c = document.querySelector('#inputComplemento');
                    if (n) { n.value = d.numero || ''; n.dispatchEvent(new Event('input', { bubbles: true })); }
                    if (c) { c.value = complFinal; c.dispatchEvent(new Event('input', { bubbles: true })); }

                    await wait(500);

                    // Salva Modal (Novo Cadastro)
                    const btnSalvar = document.querySelector('.botao-salvar') || document.querySelector('button[mattooltip="Salva as alterações"]');
                    if (btnSalvar) btnSalvar.click();
                }

                // --- PÓS MODAL (Comum) ---
                await wait(1500);

                // Fecha Modal se ainda aberto
                const btnFechar = document.querySelector('.fa-window-close') || document.querySelector('.btn-fechar');
                if (btnFechar && document.querySelector('mat-dialog-container')) btnFechar.click();

                for (let i = 0; i < 30; i++) {
                    if (!document.querySelector('mat-dialog-container')) break;
                    await wait(300);
                }
                await wait(500);

                // --- FLUXO DIVIDIDO ---
                if (MODO_EXECUCAO === 'COMPLETO') {
                    // MODO COMPLETO: Troca de Destinatário + Edição

                    // Rua Alvo para troca (recuperada do objeto, pois o inputLogradouro já foi fechado)
                    let ruaAlvo = normalizar(d.rua || d.endRaw).split(',')[0].trim();

                    if (ruaAlvo) {
                        const icones = Array.from(document.querySelectorAll('.pec-icone-verde-endereco-tabela-destinatarios'));
                        const alvo = icones.find(icone => normalizar(icone.getAttribute('aria-label') || '').includes(ruaAlvo));
                        if (alvo) {
                            const tr = alvo.closest('tr');
                            const btnEdit = tr.querySelector('.fa-edit');
                            if (btnEdit) {
                                (btnEdit.closest('button') || btnEdit).click();
                                await wait(800);
                            }
                        }
                    }

                    // Edita Minuta
                    console.log('[GOD] Completo: Editando minuta...');
                    const btnConfec = document.querySelector('button[aria-label="Confeccionar ato"]');
                    if (btnConfec) {
                        btnConfec.click();

                        let editorCarregou = false;
                        for (let i = 0; i < 50; i++) {
                            if (document.querySelector('.ck-editor__editable')) { editorCarregou = true; break; }
                            await wait(200);
                        }

                        if (editorCarregou) {
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
                } else {
                    console.log('[GOD] Modo Direto: Fim do ciclo.');
                }

                linha.style.backgroundColor = '#c8e6c9';
                atual++;
                setTimeout(processarProximo, 800);

            } catch (e) {
                console.error('[GOD] Erro:', e);
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
    }

    // =================================================================================
    // PARTE 2: INFOJUD CNPJ
    // =================================================================================
    else if (URL_ATUAL.includes('detalheNICNPJ.asp')) {
        if (document.body.innerText.includes('Nenhum registro') || document.body.innerText.includes('Erro')) {
            GM_setValue('GOD_STATUS', 'PULAR_' + Date.now());
            /* mantendo aba aberta por solicitação do usuário:
            setTimeout(() => window.close(), 1000);
            */
            return;
        }
        setTimeout(() => {
            const tds = Array.from(document.querySelectorAll('td'));
            const labelCpf = tds.find(td => td.textContent.includes('CPF do responsável'));
            const cpf = labelCpf ? labelCpf.nextElementSibling?.textContent.replace(/\D/g, '') : null;
            if (cpf && cpf.length === 11) {
                GM_openInTab(URL_BASE_CPF + cpf, { active: true, insert: true });
                /* mantendo aba aberta por solicitação do usuário:
                setTimeout(() => window.close(), 500);
                */
            } else {
                GM_setValue('GOD_STATUS', 'PULAR_' + Date.now());
                /* mantendo aba aberta por solicitação do usuário:
                setTimeout(() => window.close(), 500);
                */
            }
        }, 800);
    }

    // =================================================================================
    // PARTE 3: INFOJUD CPF (CAPTURA OTIMIZADA)
    // =================================================================================
    else if (URL_ATUAL.includes('detalheNICPF.asp')) {
        setTimeout(() => {
            try {
                let d = {};
                let c = Array.from(document.querySelectorAll('td.azulEsquerdaNeg'));
                c.forEach(t => {
                    let l = t.textContent.trim().replace(':', '');
                    let v = t.nextElementSibling?.textContent.trim() || '';
                    v = v.replace(/[\n\r]+/g, ' ').replace(/\s+/g, ' ').trim();

                    if (l === 'Nome Completo') d.nomeCompleto = v;
                    if (l === 'CEP') d.cepRaw = v;
                    if (l === 'Endereço') d.endRaw = v;
                });

                if (d.cepRaw) {
                    d.nome = d.nomeCompleto ? d.nomeCompleto.trim() : '';
                    let cep = d.cepRaw.replace(/\D/g, '');
                    if (cep.length === 7) cep = '0' + cep;
                    d.cep = cep;

                    // Parse Endereço para Relatório e Match
                    let endLimpo = d.endRaw;
                    let tokens = endLimpo.split(' ');
                    let numeroIdx = -1;

                    for (let i = 0; i < tokens.length; i++) {
                        if (/^\d+$/.test(tokens[i])) { numeroIdx = i; break; }
                    }

                    if (numeroIdx > -1) {
                        d.numero = tokens[numeroIdx];
                        d.rua = tokens.slice(0, numeroIdx).join(' '); // Rua sem número

                        let resto = tokens.slice(numeroIdx + 1).join(' ');
                        if (resto.startsWith('-')) resto = resto.substring(1).trim();

                        const tipoOrigem = GM_getValue('GOD_TIPO_ORIGEM', 'CNPJ_NORMAL');
                        if (tipoOrigem === 'CPF_DIRETO') {
                            d.complemento = resto;
                        } else {
                            d.complemento = resto + ' N/P ' + d.nome;
                        }
                    } else {
                        d.numero = 'S/N';
                        d.rua = endLimpo;
                        d.complemento = d.nome;
                    }

                    GM_setValue('GOD_DADOS_CAPTURA', JSON.stringify(d));
                    GM_setValue('GOD_STATUS', 'DADOS_PRONTOS_' + Date.now());

                    document.body.innerHTML = '<h1 style="color:green;text-align:center">DADOS OK!</h1>';
                    /* mantendo aba aberta por solicitação do usuário:
                    setTimeout(() => window.close(), 500);
                    */
                } else {
                    throw new Error('Dados incompletos');
                }
            } catch (e) {
                console.error(e);
                GM_setValue('GOD_STATUS', 'PULAR_' + Date.now());
                /* mantendo aba aberta por solicitação do usuário:
                setTimeout(() => window.close(), 1000);
                */
            }
        }, 1000);
    }

    function esperarModal(classe) {
        return new Promise((resolve, reject) => {
            let k = 0;
            const i = setInterval(() => {
                if (document.querySelector(classe)) { clearInterval(i); resolve(); }
                k++; if (k > 50) { clearInterval(i); reject('Timeout Modal'); }
            }, 200);
        });
    }
})();