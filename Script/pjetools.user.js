// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      2.1.62-inline
// @description  Suite de ferramentas para PJe
// @author       Silas
// ── PJe (cobre todas as rotas com um único match)
// @match        https://pje.trt2.jus.br/*
// @match        https://pje1g.trt2.jus.br/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
// ── Externos (domínios distintos mantidos individuais)
// @match        https://sisbajud.cnj.jus.br/*
// @match        https://sisbajud.pdpj.jus.br/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
// @match        https://simba-novo.redejt/*
// @match        https://www3.bcb.gov.br/saj/requisicao-extratos-cadastro*
// ── Único require: o loader (bumpar só ele ao adicionar módulos)
// (loader injetado inline — remove dependência externa)
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_openInTab
// @grant        window.close
// @grant        unsafeWindow
// @run-at       document-idle
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/utils.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/state.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/extrair.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.check.js?v=2.1.37
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.edital.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.pgto.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.worker.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/ui/painel.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/infojud/infojud.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/core.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/relatorios.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/sisbajud.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/debito/registrar_debito.js
// ==/UserScript==

// ════════════════════════════════════════════════════════════════════════════════════════
// ═══ SIMBA.JS INLINE (v2.1.62) ═══════════════════════════════════════════════════════
// ════════════════════════════════════════════════════════════════════════════════════════
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

        let numProcesso = '';
        const matchProc = document.title.match(/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/);
        if (matchProc) {
            numProcesso = matchProc[0];
        } else {
            const elProc = document.querySelector('.texto-numero-processo');
            if (elProc) {
                const m2 = elProc.textContent.match(/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/);
                if (m2) numProcesso = m2[0];
            }
        }

        if (numProcesso && typeof GM_setValue !== 'undefined') {
            GM_setValue('simba_last_processo', numProcesso);
        } else if (numProcesso) {
            localStorage.setItem('simba_last_processo', numProcesso);
        }

        const idProcesso = (window.__pjeApi && window.__pjeApi.idProcesso) ? window.__pjeApi.idProcesso() : null;
        
        console.log('--- DEBUG: DADOS DO MAISPJE NO LOCALSTORAGE ---');
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            const numLimpo = numProcesso ? numProcesso.replace(/\D/g, '') : 'xxxxxxxxxx';
            if (key.includes('maisPJe') || (idProcesso && key.includes(idProcesso)) || key.includes(numLimpo) || key.includes('partes') || key.includes('processo')) {
                try {
                    const val = localStorage.getItem(key);
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

        if (idProcesso) {
            try {
                console.log(`[Simba] Buscando polo passivo para o processo ID ${idProcesso}...`);
                const urlPartes = location.origin + '/pje-comum-api/api/processos/id/' + idProcesso + '/partes';
                const respPartes = await fetch(urlPartes, { method: 'GET', credentials: 'include', headers: headersApi() });
                if (respPartes.ok) {
                    const partes = await respPartes.json();
                    console.log('[Simba] RAW payload da API de partes:', partes);
                    
                    let reclamados = [];

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
                            GM_setValue('simba_reclamados_index', 0);
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
                const btnIncluir = document.getElementById('incluir');
                if (btnIncluir) {
                    btnIncluir.click();
                } else {
                    console.log('Botão "Nova Cooperação" não encontrado, prosseguindo...');
                }

                await new Promise(resolve => {
                    const checkTab = setInterval(() => {
                        const tab = document.getElementById('tab_container_tab0');
                        if (tab && tab.classList.contains('activeTab')) {
                            clearInterval(checkTab);
                            resolve();
                        }
                    }, 500);
                });

                let numProcesso = '';
                let dataExecucao = '';
                if (typeof GM_getValue !== 'undefined') {
                    numProcesso = GM_getValue('simba_last_processo', '');
                    dataExecucao = GM_getValue('simba_last_data_execucao', '');
                } else {
                    numProcesso = localStorage.getItem('simba_last_processo') || '';
                    dataExecucao = localStorage.getItem('simba_last_data_execucao') || '';
                }

                const now = new Date();
                now.setDate(0);
                const dd = String(now.getDate()).padStart(2, '0');
                const mm = String(now.getMonth() + 1).padStart(2, '0');
                const yyyy = now.getFullYear();
                const dataFimAfastamento = `${dd}/${mm}/${yyyy}`;

                const setVal = async (id, val) => {
                    const el = document.getElementById(id);
                    if (el && val) {
                        console.log(`[Simba] Iniciando preenchimento de "${id}" com o valor: "${val}"...`);
                        el.focus();
                        await new Promise(r => setTimeout(r, 100));
                        
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
                await new Promise(r => setTimeout(r, 1500));

                if (typeof GM_setValue !== 'undefined') {
                    GM_setValue('simba_reclamados_index', 0);
                    GM_setValue('simba_automacao_ativa', true);
                } else {
                    localStorage.setItem('simba_reclamados_index', 0);
                    localStorage.setItem('simba_automacao_ativa', 'true');
                }

                console.log('[Simba] Clicando em Avançar...');
                const btnAvancar = document.getElementById('avancar_formulario');
                if (btnAvancar) {
                    btnAvancar.click();
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

        const header = document.querySelector('.titulo_funcionalidade') || document.body;
        header.appendChild(btn);
    }
    
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
        
        const tab1 = document.getElementById('tab_container_tab1');
        if (!tab1 || !tab1.classList.contains('activeTab')) {
            return;
        }
        
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

        for (let i = idx; i < reclamados.length; i++) {
            const r = reclamados[i];
            console.log(`[Simba] [AUTOMAÇÃO] Preenchendo reclamado ${i + 1}/${reclamados.length}:`, r);
            
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
            
            console.log('[Simba] Aguardando confirmação (nova linha na tabela)...');
            let waitCycles = 0;
            while (getNumRows() <= initialRows && waitCycles < 20) {
                await new Promise(res => setTimeout(res, 500));
                waitCycles++;
            }
            
            if (getNumRows() > initialRows) {
                console.log('[Simba] Reclamado adicionado com sucesso na tabela!');
                await new Promise(res => setTimeout(res, 500));
            } else {
                console.warn('[Simba] Tempo limite atingido. A tabela não atualizou (erro de validação?). Indo para o próximo...');
            }
            
            if (typeof GM_setValue !== 'undefined') GM_setValue('simba_reclamados_index', i + 1);
            else localStorage.setItem('simba_reclamados_index', i + 1);
        }
        
        console.log('[Simba] Todos os reclamados já foram inseridos! Finalizando automação.');
        if (typeof GM_setValue !== 'undefined') GM_setValue('simba_automacao_ativa', false);
        else localStorage.setItem('simba_automacao_ativa', 'false');
        alert(`✅ Automação concluída com sucesso! Todos os ${reclamados.length} reclamados foram inseridos.`);
    }
    
    setInterval(resumeAutomacaoSimba, 2000);

    window.executarSimbaBcbParte1 = async function() {
        console.log('[Simba BCB P1] Iniciando preenchimento da primeira página...');
        
        if (typeof showToast === 'function') {
            showToast('Preenchendo primeira página BCB...', '#ff9800', 3000);
        }

        const clickAndWait = async (sel, desc, delayMs = 400) => {
            const el = document.querySelector(sel);
            if (!el) {
                console.warn(`[Simba BCB P1] Elemento não encontrado: ${desc} (${sel})`);
                return false;
            }
            el.click();
            console.log(`[Simba BCB P1] Clicado: ${desc}`);
            await new Promise(r => setTimeout(r, delayMs));
            return true;
        };

        const preencherCampo = async (sel, valor, desc, delayMs = 300) => {
            const el = document.querySelector(sel);
            if (!el) {
                console.warn(`[Simba BCB P1] Campo não encontrado: ${desc} (${sel})`);
                return false;
            }
            el.focus();
            await new Promise(r => setTimeout(r, 100));
            el.value = valor;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.blur();
            console.log(`[Simba BCB P1] Preenchido: ${desc} = "${valor}"`);
            await new Promise(r => setTimeout(r, delayMs));
            return true;
        };

        const selecionarOpcao = async (sel, textoOpcao, desc, delayMs = 400) => {
            const el = document.querySelector(sel);
            if (!el) {
                console.warn(`[Simba BCB P1] Dropdown não encontrado: ${desc} (${sel})`);
                return false;
            }
            el.click();
            console.log(`[Simba BCB P1] Dropdown aberto: ${desc}`);
            await new Promise(r => setTimeout(r, delayMs));
            
            const opcoes = document.querySelectorAll(`${sel} option`);
            for (const opt of opcoes) {
                if (opt.textContent.includes(textoOpcao)) {
                    opt.selected = true;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log(`[Simba BCB P1] Selecionado: ${desc} = "${textoOpcao}"`);
                    await new Promise(r => setTimeout(r, delayMs));
                    return true;
                }
            }
            console.warn(`[Simba BCB P1] Opção não encontrada: ${textoOpcao} em ${desc}`);
            return false;
        };

        const selecionarCheckbox = async (sel, desc, delayMs = 300) => {
            const el = document.querySelector(sel);
            if (!el) {
                console.warn(`[Simba BCB P1] Checkbox/Radio não encontrado: ${desc} (${sel})`);
                return false;
            }
            if (!el.checked) {
                el.click();
                el.dispatchEvent(new Event('change', { bubbles: true }));
                console.log(`[Simba BCB P1] Marcado: ${desc}`);
                await new Promise(r => setTimeout(r, delayMs));
            }
            return true;
        };

        try {
            let numProcesso = '';
            let email = '';
            let telefone = '';
            let dataInicio = '';
            let dataFim = '';
            let vara = '3ª VARA DO TRABALHO DA ZONA SUL DE SÃO PAULO';
            let juiz = 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA';

            if (typeof GM_setValue !== 'undefined') {
                numProcesso = GM_getValue('simba_last_processo', '');
                email = GM_getValue('simba_bcb_email', 'vtsps03@trt2.jus.br');
                telefone = GM_getValue('simba_bcb_telefone', '(11)3738-8145');
                dataInicio = GM_getValue('simba_last_data_execucao', '');
                dataFim = GM_getValue('simba_bcb_data_fim', '');
            } else {
                numProcesso = localStorage.getItem('simba_last_processo') || '';
                email = localStorage.getItem('simba_bcb_email') || 'vtsps03@trt2.jus.br';
                telefone = localStorage.getItem('simba_bcb_telefone') || '(11)3738-8145';
                dataInicio = localStorage.getItem('simba_last_data_execucao') || '';
                dataFim = localStorage.getItem('simba_bcb_data_fim') || '';
            }

            if (!dataFim) {
                const now = new Date();
                now.setDate(0);
                const dd = String(now.getDate()).padStart(2, '0');
                const mm = String(now.getMonth() + 1).padStart(2, '0');
                const yyyy = now.getFullYear();
                dataFim = `${dd}/${mm}/${yyyy}`;
                
                if (typeof GM_setValue !== 'undefined') {
                    GM_setValue('simba_bcb_data_fim', dataFim);
                } else {
                    localStorage.setItem('simba_bcb_data_fim', dataFim);
                }
            }

            if (!numProcesso) {
                alert('[Simba BCB P1] Atenção: Número do processo não encontrado. O campo ficará vazio.');
            }

            console.log(`[Simba BCB P1] Dados carregados: processo=${numProcesso}, email=${email}, telefone=${telefone}, dataInicio=${dataInicio}, dataFim=${dataFim}`);

            const inputVara = document.querySelector('input.form-control.saj-input-select-form-input');
            if (inputVara) {
                inputVara.focus();
                await new Promise(r => setTimeout(r, 100));
                inputVara.value = '3ª VA';
                inputVara.dispatchEvent(new Event('input', { bubbles: true }));
                console.log('[Simba BCB P1] Digitado "3ª VA" no campo de Vara');
                await new Promise(r => setTimeout(r, 500));
                
                const opcaoVara = document.querySelector('div.saj-input-select-body-options-value');
                if (opcaoVara && opcaoVara.textContent.includes('3ª VARA DO TRABALHO DA ZONA SUL DE SÃO PAULO')) {
                    opcaoVara.click();
                    console.log('[Simba BCB P1] Selecionada: 3ª VARA DO TRABALHO DA ZONA SUL DE SÃO PAULO');
                    await new Promise(r => setTimeout(r, 400));
                } else {
                    console.warn('[Simba BCB P1] Opção de vara não encontrada');
                }
            } else {
                console.warn('[Simba BCB P1] Campo de Vara não encontrado');
            }

            await selecionarOpcao('select.form-control.ng-untouched.ng-pristine', juiz, 'Juiz', 400);

            await preencherCampo('#codigoProcesso', numProcesso, 'Código do Processo', 300);

            await preencherCampo('#prazo', '60', 'Prazo', 300);

            await selecionarCheckbox('input[name="defaultExampleRadios"]#2', 'Extrato de movimentação', 300);
            await selecionarCheckbox('input[name="defaultExampleRadios"]#3', 'Extrato de aplicações financeiras', 300);
            await selecionarCheckbox('input[name="defaultExampleRadios"]#4', 'Fatura de cartão de crédito', 300);

            await preencherCampo('#email', email, 'Email', 300);

            await preencherCampo('#telefone', telefone, 'Telefone', 300);

            console.log('[Simba BCB P1] Primeira página preenchida com sucesso!');
            
            if (typeof GM_setValue !== 'undefined') {
                GM_setValue('simba_bcb_parte1_concluida', true);
            } else {
                localStorage.setItem('simba_bcb_parte1_concluida', 'true');
            }
            
            if (typeof showToast === 'function') {
                showToast('Primeira página preenchida! Clique novamente para adicionar investigados.', '#28a745', 4000);
            }

        } catch (error) {
            console.error('[Simba BCB P1] Erro ao preencher formulário:', error);
            if (typeof showToast === 'function') {
                showToast('Erro ao preencher primeira página BCB', '#dc3545', 3000);
            }
        }
    };

    window.executarSimbaBcbParte2 = async function() {
        console.log('[Simba BCB P2] Iniciando adição de investigados...');
        
        if (typeof showToast === 'function') {
            showToast('Adicionando investigados...', '#ff9800', 3000);
        }

        try {
            let dataInicio = '';
            let dataFim = '';
            
            if (typeof GM_getValue !== 'undefined') {
                dataInicio = GM_getValue('simba_last_data_execucao', '');
                dataFim = GM_getValue('simba_bcb_data_fim', '');
            } else {
                dataInicio = localStorage.getItem('simba_last_data_execucao') || '';
                dataFim = localStorage.getItem('simba_bcb_data_fim') || '';
            }
            
            let reclamadosStr = '[]';
            if (typeof GM_getValue !== 'undefined') {
                reclamadosStr = GM_getValue('simba_reclamados', '[]');
            } else {
                reclamadosStr = localStorage.getItem('simba_reclamados') || '[]';
            }
            
            let reclamados = JSON.parse(reclamadosStr);
            if (!reclamados || reclamados.length === 0) {
                console.warn('[Simba BCB P2] Nenhum reclamado encontrado para adicionar.');
                if (typeof showToast === 'function') {
                    showToast('Nenhum investigado para adicionar.', '#ffc107', 3000);
                }
                return;
            }

            console.log(`[Simba BCB P2] Adicionando ${reclamados.length} investigados...`);

            for (let i = 0; i < reclamados.length; i++) {
                const r = reclamados[i];
                const docLimpo = r.documento.replace(/\D/g, '');
                
                console.log(`[Simba BCB P2] Processando investigado ${i + 1}/${reclamados.length}: ${r.nome} (${docLimpo})...`);
                
                const btnAdicionar = document.querySelector('button.btn.btn-primary');
                if (btnAdicionar && btnAdicionar.textContent.includes('Adicionar Investigado')) {
                    btnAdicionar.click();
                    console.log(`[Simba BCB P2] Clicado botão Adicionar Investigado para item ${i + 1}`);
                    await new Promise(r => setTimeout(r, 500));
                } else {
                    console.warn('[Simba BCB P2] Botão Adicionar Investigado não encontrado');
                }
                
                const inputItem = document.querySelector('input[formcontrolname="item"]');
                if (inputItem) {
                    inputItem.focus();
                    await new Promise(r => setTimeout(r, 100));
                    inputItem.value = docLimpo;
                    inputItem.dispatchEvent(new Event('input', { bubbles: true }));
                    inputItem.dispatchEvent(new Event('change', { bubbles: true }));
                    inputItem.blur();
                    console.log(`[Simba BCB P2] Preenchido CPF/CNPJ: ${docLimpo}`);
                    await new Promise(r => setTimeout(r, 300));
                } else {
                    console.warn('[Simba BCB P2] Campo de CPF/CNPJ não encontrado');
                }

                const inputDataInicio = document.querySelector('input[formcontrolname="dataInicio"]');
                if (inputDataInicio && dataInicio) {
                    inputDataInicio.focus();
                    await new Promise(r => setTimeout(r, 100));
                    inputDataInicio.value = dataInicio;
                    inputDataInicio.dispatchEvent(new Event('input', { bubbles: true }));
                    inputDataInicio.dispatchEvent(new Event('change', { bubbles: true }));
                    inputDataInicio.blur();
                    console.log(`[Simba BCB P2] Preenchida Data Início: ${dataInicio}`);
                    await new Promise(r => setTimeout(r, 300));
                }

                const inputDataFim = document.querySelector('input[formcontrolname="dataFim"]');
                if (inputDataFim && dataFim) {
                    inputDataFim.focus();
                    await new Promise(r => setTimeout(r, 100));
                    inputDataFim.value = dataFim;
                    inputDataFim.dispatchEvent(new Event('input', { bubbles: true }));
                    inputDataFim.dispatchEvent(new Event('change', { bubbles: true }));
                    inputDataFim.blur();
                    console.log(`[Simba BCB P2] Preenchida Data Fim: ${dataFim}`);
                    await new Promise(r => setTimeout(r, 300));
                }

                await new Promise(r => setTimeout(r, 400));
            }

            console.log('[Simba BCB P2] Todos os investigados preenchidos!');
            
            if (typeof GM_setValue !== 'undefined') {
                GM_setValue('simba_bcb_parte1_concluida', false);
            } else {
                localStorage.setItem('simba_bcb_parte1_concluida', 'false');
            }
            
            if (typeof showToast === 'function') {
                showToast(`✅ ${reclamados.length} investigados adicionados!`, '#28a745', 3000);
            }

        } catch (error) {
            console.error('[Simba BCB P2] Erro ao adicionar investigados:', error);
            if (typeof showToast === 'function') {
                showToast('Erro ao adicionar investigados', '#dc3545', 3000);
            }
        }
    };

    window.executarSimbaBcb = async function() {
        let parte1Concluida = false;
        
        if (typeof GM_getValue !== 'undefined') {
            parte1Concluida = GM_getValue('simba_bcb_parte1_concluida', false);
        } else {
            parte1Concluida = localStorage.getItem('simba_bcb_parte1_concluida') === 'true';
        }
        
        if (parte1Concluida) {
            console.log('[Simba BCB] Detectada Parte 1 concluída, executando Parte 2...');
            await window.executarSimbaBcbParte2();
        } else {
            console.log('[Simba BCB] Executando Parte 1...');
            await window.executarSimbaBcbParte1();
        }
    };

})();
// ════════════════════════════════════════════════════════════════════════════════════════

(async function () {
    'use strict';
    console.log('[Loader] PJe Tools Pro v2.1.62 loaded');
    if (window.self !== window.top) return;

    // W = window real da página (unsafeWindow quando disponível)
    const W = (typeof unsafeWindow !== 'undefined') ? unsafeWindow : window;

    const url = window.location.href;

    const isReceita  = url.includes('cav.receita.fazenda.gov.br');
    const isSisbajud = url.includes('sisbajud.cnj.jus.br') || url.includes('sisbajud.pdpj.jus.br');
    const isPjeDomain = url.includes('pje.trt2.jus.br') || url.includes('pje1g.trt2.jus.br');
    const isBcb = url.includes('bcb.gov.br/saj/requisicao-extratos-cadastro');

    // (No match da Receita, content scripts já estão via @require em header)
    if (isSisbajud) return;

    // ── Lógica BCB (terceira execução Simba) ──
    if (isBcb) {
        console.log('[Loader] Detectada URL do BCB, carregando Simba BCB...');
        setTimeout(() => {
            if (!document.getElementById('btnSimbaBcbExtratos')) {
                const btn = document.createElement('button');
                btn.id = 'btnSimbaBcbExtratos';
                btn.textContent = '🦁 Preencher BCB';
                btn.title = 'Preencher automaticamente o formulário de requisição de extratos do BCB';
                btn.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:999999999;
                    padding:10px 15px;background-color:#ff6600;color:white;border:none;
                    border-radius:4px;font-weight:bold;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,0.3);
                    font-size:14px;text-shadow:0 1px 2px rgba(0,0,0,0.3);`;
                
                btn.onclick = async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    btn.disabled = true;
                    btn.textContent = 'Processando...';
                    try {
                        await window.executarSimbaBcb?.();
                    } catch (err) {
                        console.error('[Loader BCB] Erro:', err);
                        alert('Erro ao preencher formulário BCB: ' + err.message);
                    }
                    btn.textContent = '🦁 Preencher BCB';
                    btn.disabled = false;
                };
                
                document.body.appendChild(btn);
                console.log('[Loader] Botão BCB criado com sucesso');
            }
        }, 800);
        return;
    }

    // ── Roteamento (roda depois de todos os @require carregados)
    if (isPjeDomain || isReceita) {

        // Se for Receita Federal (e-CAC), não roteamos aqui — o módulo carregado via @require
        // já executa sua Parte 2 quando a aba do e-CAC abre. Permitimos que o módulo aja.
        if (isReceita) return;
        // Dynamic loader removed: all modules must be provided via @require in the userscript header.

        // ── Roteamento (só roda DEPOIS de tudo carregado)
        const isMinutas  = url.includes('/comunicacoesprocessuais/minutas');
        const isDetalhe  = /\/processo\/\d+\/detalhe/.test(url);
        const isObrigacao = url.includes('/obrigacao-pagar/');

        if (isMinutas) {
            // FIX #3: usar flag em memória por sessão para evitar persistência entre navegações SPA
            if (window.__infojudWorkerRodando) return;
            window.__infojudWorkerRodando = true;
            console.log('[Loader] Iniciando Worker Infojud...');

            setTimeout(() => {
                if (W.runInfojudWorker) {
                    W.runInfojudWorker();
                } else {
                    console.error('[Loader] runInfojudWorker não encontrado no window! Verifique o @require do infojud.js.');
                }
                // liberar para próximas navegações SPA
                window.__infojudWorkerRodando = false;
            }, 1500);
            return;
        }

        if (isObrigacao) {
            setTimeout(() => {
                try {
                    if (/\/obrigacao-pagar\/\d+\/cadastro/.test(url)) {
                        window.PjeRegistrarDebito?.onCadastro();
                    } else if (/\/obrigacao-pagar\/\d+\/inclusao/.test(url)) {
                        window.PjeRegistrarDebito?.onInclusao();
                    }
                } catch (e) { console.error('[Loader] erro ao iniciar PjeRegistrarDebito:', e); }
            }, 1500);
            return;
        }

        if (!isDetalhe) return;

        // ── Detalhe: registrar SPA monitor uma vez e inicializar
        if (!window.__pjeToolsLoaded) {
            window.__pjeToolsLoaded = true;

            window.monitorarSPA && window.monitorarSPA(() => {
                window.PJeState && window.PJeState.dispose();
                setTimeout(() => {
                    if (/\/processo\/\d+\/detalhe/.test(window.location.href)) {
                        bootDetalhe();
                    }
                }, 300);
            });
        }

        bootDetalhe();

        function bootDetalhe() {
            if (!/\/processo\/\d+\/detalhe/.test(window.location.href)) return;
            // FIX: módulos registrados via @require expõem suas funções no sandbox `window`,
            // portanto chamamos `window.*` aqui em vez de `W` (unsafeWindow).
            if (!window.PJeState || window.PJeState._iniciado) return;
            window.PJeState._iniciado = true;
            window.inicializarPainel && window.inicializarPainel();
            window.initAtalhos && window.initAtalhos();
        }
    }
})();
