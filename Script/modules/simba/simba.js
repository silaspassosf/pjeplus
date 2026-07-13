(function () {
    'use strict';

    function normalizarDataApi(dataStr) {
        if (!dataStr) return '';
        const m = dataStr.match(/(\d{4})-(\d{2})-(\d{2})/);
        if (m) return `${m[3]}/${m[2]}/${m[1]}`;
        return dataStr;
    }

    function headersApi() {
        const xsrf = (window.__pjeApi && window.__pjeApi.xsrf) ? window.__pjeApi.xsrf() : '';
        const h = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Grau-Instancia': '1',
        };
        if (xsrf) h['X-XSRF-TOKEN'] = xsrf;
        return h;
    }

    window.executarSimba = async function() {
        if (typeof showToast === 'function') {
            showToast('Extraindo dados para Simba...', '#ff9800', 3000);
        }

        const btnGuardar = document.getElementById('maisPJe_bt_detalhes_guardarDados');
        if (btnGuardar) {
            btnGuardar.click();
        } else {
            console.warn('[Simba] Botão Guardar Dados não encontrado no DOM.');
        }

        // Tentar obter o número do processo pelo título ou DOM
        let numProcesso = '';
        const matchProc = document.title.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
        if (matchProc) {
            numProcesso = matchProc[0];
        } else {
            const elProc = document.querySelector('.texto-numero-processo');
            if (elProc) {
                const m2 = elProc.textContent.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
                if (m2) numProcesso = m2[0];
            }
        }

        if (numProcesso && typeof GM_setValue !== 'undefined') {
            GM_setValue('simba_last_processo', numProcesso);
        } else if (numProcesso) {
            localStorage.setItem('simba_last_processo', numProcesso);
        }

        const idProcesso = (window.__pjeApi && window.__pjeApi.idProcesso) ? window.__pjeApi.idProcesso() : null;
        
        // --- DEBUG STORAGE PARA O USUÁRIO ---
        console.log('--- DEBUG: DADOS DO MAISPJE NO LOCALSTORAGE ---');
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            const numLimpo = numProcesso ? numProcesso.replace(/\D/g, '') : 'xxxxxxxxxx';
            if (key.includes('maisPJe') || (idProcesso && key.includes(idProcesso)) || key.includes(numLimpo) || key.includes('partes') || key.includes('processo')) {
                try {
                    const val = localStorage.getItem(key);
                    // Mostrar apenas os primeiros 300 caracteres para evitar poluir demais, ou JSON parsed
                    try {
                        console.log(`[Key: ${key}]`, JSON.parse(val));
                    } catch (e) {
                        console.log(`[Key: ${key}]`, val.substring(0, 300));
                    }
                } catch (e) {}
            }
        }
        console.log('------------------------------------------------');
        if (idProcesso) {
            try {
                const params = new URLSearchParams({
                    buscarMovimentos: 'true',
                    buscarDocumentos: 'false',
                    somenteDocumentosAssinados: 'false',
                });
                const url = location.origin
                    + '/pje-comum-api/api/processos/id/' + idProcesso
                    + '/timeline?' + params.toString();

                const resp = await fetch(url, { method: 'GET', credentials: 'include', headers: headersApi() });
                if (resp.ok) {
                    const itens = await resp.json();
                    const movimentoExec = itens.find(item => item.titulo && item.titulo.includes('Iniciada a execução'));
                    if (movimentoExec) {
                        const dataExecucao = normalizarDataApi(movimentoExec.data || movimentoExec.atualizadoEm || '');
                        if (typeof GM_setValue !== 'undefined') {
                            GM_setValue('simba_last_data_execucao', dataExecucao);
                        } else {
                            localStorage.setItem('simba_last_data_execucao', dataExecucao);
                        }
                        console.log(`[Simba] Data da Iniciada a execução salva: ${dataExecucao}`);
                    } else {
                        console.log('[Simba] Movimento "Iniciada a execução" não encontrado.');
                    }
                }
            } catch (e) {
                console.error('[Simba] Erro ao buscar movimentos da execução:', e);
            }
        } else {
            console.warn('[Simba] ID do processo não encontrado para buscar a data de início da execução.');
        }

        // --- BUSCA POLO PASSIVO VIA API ---
        if (idProcesso) {
            try {
                console.log(`[Simba] Buscando polo passivo para o processo ID ${idProcesso}...`);
                const urlPartes = location.origin + '/pje-comum-api/api/processos/id/' + idProcesso + '/partes';
                const respPartes = await fetch(urlPartes, { method: 'GET', credentials: 'include', headers: headersApi() });
                if (respPartes.ok) {
                    const partes = await respPartes.json();
                    console.log('[Simba] RAW payload da API de partes:', partes);
                    
                    let reclamados = [];

                    // Extrair PASSIVO
                    if (partes.PASSIVO && Array.isArray(partes.PASSIVO)) {
                        console.log(`[Simba] Verificando ${partes.PASSIVO.length} partes no PASSIVO...`);
                        partes.PASSIVO.forEach(p => {
                            console.log('[Simba] Analisando parte PASSIVO:', p);
                            if (p.nome && p.documento) {
                                reclamados.push({ nome: p.nome, documento: p.documento });
                                console.log(`[Simba] Adicionado PASSIVO: ${p.nome} - ${p.documento}`);
                            }
                        });
                    } else {
                        console.log('[Simba] Array PASSIVO não encontrado ou não é array:', partes.PASSIVO);
                    }
                    
                    // Extrair TERCEIROS (Sócios, etc)
                    if (partes.TERCEIROS && Array.isArray(partes.TERCEIROS)) {
                        console.log(`[Simba] Verificando ${partes.TERCEIROS.length} partes em TERCEIROS...`);
                        partes.TERCEIROS.forEach(p => {
                            console.log('[Simba] Analisando parte TERCEIROS:', p);
                            if (p.nome && p.documento) {
                                reclamados.push({ nome: p.nome, documento: p.documento });
                                console.log(`[Simba] Adicionado TERCEIRO: ${p.nome} - ${p.documento}`);
                            }
                        });
                    }

                    if (reclamados.length > 0) {
                        console.log(`[Simba] Encontrados ${reclamados.length} investigados/reclamados:`, reclamados);
                        const reclamadosStr = JSON.stringify(reclamados);
                        console.log('[Simba] Salvando no GM_setValue simba_reclamados:', reclamadosStr);
                        if (typeof GM_setValue !== 'undefined') {
                            GM_setValue('simba_reclamados', reclamadosStr);
                            GM_setValue('simba_reclamados_index', 0); // Reseta o índice
                            console.log('[Simba] Dados salvos com sucesso via GM_setValue.');
                        } else {
                            localStorage.setItem('simba_reclamados', reclamadosStr);
                            localStorage.setItem('simba_reclamados_index', 0);
                            console.log('[Simba] Dados salvos com sucesso via localStorage.');
                        }
                    } else {
                        console.warn('[Simba] Polo passivo não retornou CPFs/CNPJs válidos.');
                    }
                } else {
                    console.error('[Simba] Falha ao buscar partes do processo. Status:', respPartes.status);
                }
            } catch (e) {
                console.error('[Simba] Erro na requisição do polo passivo:', e);
            }
        }

        if (typeof showToast === 'function') {
            showToast('Dados salvos', '#28a745', 3000);
        }
    };

    // ── LÓGICA DO SIMBA (na página simba-novo.redejt) ──
    if (window.location.href.includes('simba/php/')) {
        criarBotaoOrdemSimba();
    }

    function criarBotaoOrdemSimba() {
        if (document.getElementById('btnSimbaCriarOrdem')) return;

        const btn = document.createElement('button');
        btn.id = 'btnSimbaCriarOrdem';
        btn.textContent = '🦁 Criar Ordem';
        btn.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:999999;
            padding:10px 15px;background-color:#ff9800;color:white;border:none;
            border-radius:4px;font-weight:bold;cursor:pointer;box-shadow:0 2px 5px rgba(0,0,0,0.3);`;
        
        btn.onclick = async function() {
            btn.textContent = 'Processando...';
            btn.disabled = true;
            
            try {
                // 1. Clicar no botão "Nova Cooperação"
                const btnIncluir = document.getElementById('incluir');
                if (btnIncluir) {
                    btnIncluir.click();
                } else {
                    console.log('Botão "Nova Cooperação" não encontrado, prosseguindo...');
                }

                // 2. Aguardar a tab ficar ativa
                await new Promise(resolve => {
                    const checkTab = setInterval(() => {
                        const tab = document.getElementById('tab_container_tab0');
                        if (tab && tab.classList.contains('activeTab')) {
                            clearInterval(checkTab);
                            resolve();
                        }
                    }, 500);
                });

                // 3. Preencher a tab
                // Obter dados do GM_getValue (ou localStorage como fallback)
                let numProcesso = '';
                let dataExecucao = '';
                if (typeof GM_getValue !== 'undefined') {
                    numProcesso = GM_getValue('simba_last_processo', '');
                    dataExecucao = GM_getValue('simba_last_data_execucao', '');
                } else {
                    numProcesso = localStorage.getItem('simba_last_processo') || '';
                    dataExecucao = localStorage.getItem('simba_last_data_execucao') || '';
                }

                // Data de fim do afastamento: último dia do mês anterior ao atual
                const now = new Date();
                now.setDate(0); // Último dia do mês anterior
                const dd = String(now.getDate()).padStart(2, '0');
                const mm = String(now.getMonth() + 1).padStart(2, '0');
                const yyyy = now.getFullYear();
                const dataFimAfastamento = `${dd}/${mm}/${yyyy}`;

                // Função auxiliar para definir valor simulando digitação
                const setVal = async (id, val) => {
                    const el = document.getElementById(id);
                    if (el && val) {
                        console.log(`[Simba] Iniciando preenchimento de "${id}" com o valor: "${val}"...`);
                        el.focus();
                        await new Promise(r => setTimeout(r, 100)); // Aguarda o campo receber foco real
                        
                        el.value = '';
                        for (let i = 0; i < val.length; i++) {
                            el.value += val[i];
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            await new Promise(r => setTimeout(r, 20));
                        }
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        await new Promise(r => setTimeout(r, 50));
                        
                        if (typeof el.onblur === 'function') {
                            console.log(`[Simba] Chamando onblur nativo de "${id}"...`);
                            el.onblur();
                        } else {
                            el.blur();
                        }
                        
                        // Aguarda processamento de onblur
                        await new Promise(r => setTimeout(r, 300));
                        console.log(`[Simba] Preenchimento de "${id}" finalizado. Valor que ficou na tela: "${el.value}"`);
                    } else if (!el) {
                        console.warn(`[Simba] AVISO: Campo "${id}" não foi encontrado na página!`);
                    } else if (!val) {
                        console.warn(`[Simba] AVISO: Valor para o campo "${id}" está vazio!`);
                    }
                };

                if (!dataExecucao) {
                    alert('[Simba] Atenção: Data da "Iniciada a execução" não foi capturada no PJe! O campo ficará vazio.');
                }

                await setVal('telefone_contato', '1137388145');
                await setVal('nome_caso', numProcesso);
                await setVal('numero_processo', numProcesso);
                await setVal('juiz_relator', 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA');
                await setVal('vara_tribunal', '3A VARA DO TRABALHO DA ZONA SUL DE SAO PAULO');
                await setVal('data_ini_afastamento', dataExecucao);
                await setVal('data_fim_afastamento', dataFimAfastamento);

                console.log('[Simba] Todos os campos preenchidos. Aguardando antes de avançar...');
                // Aguarda 1.5 segundos para garantir que o onblur de todos os campos processou
                await new Promise(r => setTimeout(r, 1500));

                // Reseta o índice de reclamados ao iniciar uma nova ordem e ativa automação
                if (typeof GM_setValue !== 'undefined') {
                    GM_setValue('simba_reclamados_index', 0);
                    GM_setValue('simba_automacao_ativa', true);
                } else {
                    localStorage.setItem('simba_reclamados_index', 0);
                    localStorage.setItem('simba_automacao_ativa', 'true');
                }

                console.log('[Simba] Clicando em Avançar...');
                // 4. Clicar em Avançar
                const btnAvancar = document.getElementById('avancar_formulario');
                if (btnAvancar) {
                    btnAvancar.click();
                    // O clique no Avançar recarrega a página. A automação continuará após o reload.
                } else {
                    alert('Botão "Avançar" não encontrado.');
                }
            } catch (error) {
                console.error('[Simba] Erro ao criar ordem:', error);
                alert('Ocorreu um erro ao criar a ordem. Verifique o console.');
            }
            
            btn.textContent = '🦁 Criar Ordem';
            btn.disabled = false;
        };

        // Injeta o botão "Criar Ordem" (ex: breadcrumb superior)
        const header = document.querySelector('.titulo_funcionalidade') || document.body;
        header.appendChild(btn);
    }
    
    // =========================================================================
    // RETOMADA DA AUTOMAÇÃO (Pós-Reload)
    // =========================================================================
    async function resumeAutomacaoSimba() {
        if (!window.location.href.includes('simba/php/')) return;
        
        let automacaoAtiva = false;
        let reclamadosStr = '[]';
        let idx = 0;
        
        if (typeof GM_getValue !== 'undefined') {
            automacaoAtiva = GM_getValue('simba_automacao_ativa', false);
            reclamadosStr = GM_getValue('simba_reclamados', '[]');
            idx = GM_getValue('simba_reclamados_index', 0);
        } else {
            automacaoAtiva = localStorage.getItem('simba_automacao_ativa') === 'true';
            reclamadosStr = localStorage.getItem('simba_reclamados') || '[]';
            idx = parseInt(localStorage.getItem('simba_reclamados_index') || '0', 10);
        }
        
        if (!automacaoAtiva) return;
        
        // Verifica se estamos na aba de Investigados
        const tab1 = document.getElementById('tab_container_tab1');
        if (!tab1 || !tab1.classList.contains('activeTab')) {
            // Ainda não estamos na aba certa, pode estar carregando.
            return;
        }
        
        // Evita rodar duplicado
        if (window.simbaAutomacaoRodando) return;
        window.simbaAutomacaoRodando = true;
        
        console.log('[Simba] Retomando automação na aba Investigados (Pós-Reload)...');
        
        const reclamados = JSON.parse(reclamadosStr);
        if (!reclamados || reclamados.length === 0) {
            console.warn('[Simba] Automação ativa, mas nenhum reclamado encontrado na memória.');
            return;
        }
        
        let dataExecucao = '';
        if (typeof GM_getValue !== 'undefined') dataExecucao = GM_getValue('simba_last_data_execucao', '');
        else dataExecucao = localStorage.getItem('simba_last_data_execucao') || '';
        
        const now = new Date();
        const dd = String(now.getDate()).padStart(2, '0');
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const yyyy = now.getFullYear();
        const dataFimAfastamento = `${dd}/${mm}/${yyyy}`;

        // Função local setVal (reuso)
        const setValAsync = async (id, val) => {
            const el = document.getElementById(id);
            if (el && val) {
                console.log(`[Simba] Preenchendo "${id}" com: "${val}"...`);
                el.focus();
                await new Promise(res => setTimeout(res, 100));
                el.value = '';
                for (let i = 0; i < val.length; i++) {
                    el.value += val[i];
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    await new Promise(res => setTimeout(res, 20));
                }
                el.dispatchEvent(new Event('change', { bubbles: true }));
                await new Promise(res => setTimeout(res, 50));
                if (typeof el.onblur === 'function') el.onblur();
                else el.blur();
                await new Promise(res => setTimeout(res, 300));
            }
        };

        // Laço principal (AJAX)
        for (let i = idx; i < reclamados.length; i++) {
            const r = reclamados[i];
            console.log(`[Simba] [AUTOMAÇÃO] Preenchendo reclamado ${i + 1}/${reclamados.length}:`, r);
            
            // Aguarda o formulário estar pronto (botão salvar visível)
            await new Promise(resolve => {
                const checkBtn = setInterval(() => {
                    if (document.getElementById('botao_grava_investigado')) {
                        clearInterval(checkBtn);
                        resolve();
                    }
                }, 500);
            });
            
            const docLimpo = r.documento.replace(/\D/g, '');
            await setValAsync('cpf_cnpj_investigado', docLimpo);
            await setValAsync('nome_investigado', r.nome);
            await setValAsync('data_ini_afastamento_investigado', dataExecucao);
            await setValAsync('data_fim_afastamento_investigado', dataFimAfastamento);
            
            const getNumRows = () => document.querySelectorAll('table.paginacao_corpo tbody tr').length;
            const initialRows = getNumRows();
            
            console.log(`[Simba] Clicando em Salvar Investigado (${i + 1}/${reclamados.length})...`);
            const btnGravar = document.getElementById('botao_grava_investigado');
            if (btnGravar) btnGravar.click();
            
            // Aguarda a nova linha surgir na tabela após o AJAX
            console.log('[Simba] Aguardando confirmação (nova linha na tabela)...');
            let waitCycles = 0;
            while (getNumRows() <= initialRows && waitCycles < 20) { // Timeout de 10s
                await new Promise(res => setTimeout(res, 500));
                waitCycles++;
            }
            
            if (getNumRows() > initialRows) {
                console.log('[Simba] Reclamado adicionado com sucesso na tabela!');
                await new Promise(res => setTimeout(res, 500)); // Pequena pausa extra por segurança
            } else {
                console.warn('[Simba] Tempo limite atingido. A tabela não atualizou (erro de validação?). Indo para o próximo...');
            }
            
            // Salva o progresso
            if (typeof GM_setValue !== 'undefined') GM_setValue('simba_reclamados_index', i + 1);
            else localStorage.setItem('simba_reclamados_index', i + 1);
        }
        
        // Finalizou todos
        console.log('[Simba] Todos os reclamados já foram inseridos! Finalizando automação.');
        if (typeof GM_setValue !== 'undefined') GM_setValue('simba_automacao_ativa', false);
        else localStorage.setItem('simba_automacao_ativa', 'false');
        alert(`✅ Automação concluída com sucesso! Todos os ${reclamados.length} reclamados foram inseridos.`);
    }
    
    // Inicia verificador de retomada a cada 2s
    setInterval(resumeAutomacaoSimba, 2000);

    // =========================================================================
    // EXECUÇÃO BCB (Requisição de Extratos Cadastro)
    // =========================================================================
    
    window.executarSimbaBcb = async function() {
        console.log('[Simba BCB] Iniciando preenchimento automático do formulário BCB...');
        
        if (typeof showToast === 'function') {
            showToast('Preenchendo formulário BCB...', '#ff9800', 3000);
        }

        // ── Helper: Clicar e aguardar renderização ──
        const clickAndWait = async (sel, desc, delayMs = 400) => {
            const el = document.querySelector(sel);
            if (!el) {
                console.warn(`[Simba BCB] Elemento não encontrado: ${desc} (${sel})`);
                return false;
            }
            el.click();
            console.log(`[Simba BCB] Clicado: ${desc}`);
            await new Promise(r => setTimeout(r, delayMs));
            return true;
        };

        // ── Helper: Preencher campo text/input ──
        const preencherCampo = async (sel, valor, desc, delayMs = 300) => {
            const el = document.querySelector(sel);
            if (!el) {
                console.warn(`[Simba BCB] Campo não encontrado: ${desc} (${sel})`);
                return false;
            }
            el.focus();
            await new Promise(r => setTimeout(r, 100));
            el.value = valor;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.blur();
            console.log(`[Simba BCB] Preenchido: ${desc} = "${valor}"`);
            await new Promise(r => setTimeout(r, delayMs));
            return true;
        };

        // ── Helper: Selecionar opção em dropdown ──
        const selecionarOpcao = async (sel, textoOpcao, desc, delayMs = 400) => {
            const el = document.querySelector(sel);
            if (!el) {
                console.warn(`[Simba BCB] Dropdown não encontrado: ${desc} (${sel})`);
                return false;
            }
            el.click();
            console.log(`[Simba BCB] Dropdown aberto: ${desc}`);
            await new Promise(r => setTimeout(r, delayMs));
            
            // Procura a opção com o texto
            const opcoes = document.querySelectorAll(`${sel} option`);
            for (const opt of opcoes) {
                if (opt.textContent.includes(textoOpcao)) {
                    opt.selected = true;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log(`[Simba BCB] Selecionado: ${desc} = "${textoOpcao}"`);
                    await new Promise(r => setTimeout(r, delayMs));
                    return true;
                }
            }
            console.warn(`[Simba BCB] Opção não encontrada: ${textoOpcao} em ${desc}`);
            return false;
        };

        // ── Helper: Selecionar checkbox/radio ──
        const selecionarCheckbox = async (sel, desc, delayMs = 300) => {
            const el = document.querySelector(sel);
            if (!el) {
                console.warn(`[Simba BCB] Checkbox/Radio não encontrado: ${desc} (${sel})`);
                return false;
            }
            if (!el.checked) {
                el.click();
                el.dispatchEvent(new Event('change', { bubbles: true }));
                console.log(`[Simba BCB] Marcado: ${desc}`);
                await new Promise(r => setTimeout(r, delayMs));
            }
            return true;
        };

        try {
            // 1. Obter dados salvos do processo
            let numProcesso = '';
            let email = '';
            let telefone = '';
            let vara = '3ª VARA DO TRABALHO DA ZONA SUL DE SÃO PAULO';
            let juiz = 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA';

            if (typeof GM_getValue !== 'undefined') {
                numProcesso = GM_getValue('simba_last_processo', '');
                email = GM_getValue('simba_bcb_email', 'nao-informado@pje.trt2.jus.br');
                telefone = GM_getValue('simba_bcb_telefone', '1137388145');
            } else {
                numProcesso = localStorage.getItem('simba_last_processo') || '';
                email = localStorage.getItem('simba_bcb_email') || 'nao-informado@pje.trt2.jus.br';
                telefone = localStorage.getItem('simba_bcb_telefone') || '1137388145';
            }

            if (!numProcesso) {
                alert('[Simba BCB] Atenção: Número do processo não encontrado. O campo ficará vazio.');
            }

            console.log(`[Simba BCB] Dados carregados: processo=${numProcesso}, email=${email}, telefone=${telefone}`);

            // 2. Preencher Vara (dropdown custom Angular)
            // Campo: input.form-control.saj-input-select-form-input.ng-pristine
            await clickAndWait('input.form-control.saj-input-select-form-input.ng-pristine', 'Campo de Vara', 400);
            
            // Esperar o dropdown abrir e procurar a opção
            await new Promise(r => setTimeout(r, 500));
            const opcaoVara = document.querySelector('div.saj-input-select-body-options-value');
            if (opcaoVara) {
                opcaoVara.click();
                console.log('[Simba BCB] Selecionada vara padrão');
                await new Promise(r => setTimeout(r, 400));
            }

            // 3. Preencher Juiz (select normal)
            await selecionarOpcao('select.form-control.ng-untouched.ng-pristine', juiz, 'Juiz', 400);

            // 4. Preencher Código do Processo
            await preencherCampo('#codigoProcesso', numProcesso, 'Código do Processo', 300);

            // 5. Preencher Prazo (usar 30 dias padrão)
            await preencherCampo('#prazo', '30', 'Prazo', 300);

            // 6. Selecionar Extractos
            // Opções: Mercantil (1), Movimentação (2), Aplicações Financeiras (3), Cartão de Crédito (4)
            await selecionarCheckbox('input[name="defaultExampleRadios"]#1', 'Extrato Mercantil', 300);
            await selecionarCheckbox('input[name="defaultExampleRadios"]#2', 'Extrato de movimentação', 300);
            await selecionarCheckbox('#3.form-check-input', 'Extrato de aplicações financeiras', 300);
            await selecionarCheckbox('#4.form-check-input', 'Fatura de cartão de crédito', 300);

            // 7. Preencher Email
            await preencherCampo('#email', email, 'Email', 300);

            // 8. Preencher Telefone
            await preencherCampo('#telefone', telefone, 'Telefone', 300);

            console.log('[Simba BCB] Todos os campos preenchidos! Aguardando confirmação...');
            await new Promise(r => setTimeout(r, 1000));

            if (typeof showToast === 'function') {
                showToast('Formulário BCB preenchido com sucesso!', '#28a745', 3000);
            }

        } catch (error) {
            console.error('[Simba BCB] Erro ao preencher formulário:', error);
            if (typeof showToast === 'function') {
                showToast('Erro ao preencher formulário BCB', '#dc3545', 3000);
            }
        }
    };

})();
