(function () {
    'use strict';

    function normalizarDataApi(dataStr) {
        if (!dataStr) return '';
        const m = dataStr.match(/(\d{4})-(\d{2})-(\d{2})/);
        if (m) return `${m[3]}/${m[2]}/${m[1].slice(2)}`;
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

        if (typeof showToast === 'function') {
            showToast('Dados salvos', '#28a745', 3000);
        }
    };

    // ── LÓGICA DO SIMBA (na página simba-novo.redejt) ──
    if (window.location.href.includes('simba-novo.redejt/simba/php/Simba.php')) {
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
                    alert('Botão "Nova Cooperação" não encontrado.');
                    btn.textContent = '🦁 Criar Ordem';
                    btn.disabled = false;
                    return;
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

                // Função auxiliar para definir valor e disparar eventos
                const setVal = (id, val) => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.value = val;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('blur', { bubbles: true }));
                    }
                };

                setVal('telefone_contato', '1137388145');
                setVal('nome_caso', numProcesso);
                setVal('numero_processo', numProcesso);
                setVal('juiz_relator', 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA');
                setVal('vara_tribunal', '3A VARA DO TRABALHO DA ZONA SUL DE SAO PAULO');
                setVal('data_ini_afastamento', dataExecucao);
                setVal('data_fim_afastamento', dataFimAfastamento);

                // 4. Clicar em Avançar
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

        document.body.appendChild(btn);
    }
})();
