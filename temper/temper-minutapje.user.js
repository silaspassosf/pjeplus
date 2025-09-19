// ==UserScript==
// @name         MinutaPJE (Versão Anti-Conflito)
// @namespace    http://tampermonkey.net/
// @version      1.1
// @description  Automatização de minuta PJE baseada na função ato_judicial - Versão com proteção contra conflitos com maisPJe
// @author       PjePlus
// @match        *://*/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    // === SISTEMA DE PROTEÇÃO CONTRA CONFLITOS ===

    // Flag global para indicar quando o MinutaPJE está executando
    window.MinutaPJE_executando = false;

    // Contador de cliques para evitar múltiplos cliques
    let clickCounter = {};

    // Sistema de debounce para cliques
    function debounceClick(seletor, callback, delay = 1000) {
        const agora = Date.now();
        const ultimo = clickCounter[seletor] || 0;

        if (agora - ultimo > delay) {
            clickCounter[seletor] = agora;
            return callback();
        } else {
            console.log(`[MinutaPJE] Clique em ${seletor} ignorado por debounce (${agora - ultimo}ms)`);
            return Promise.resolve(false);
        }
    }

    // Função para detectar conflitos com maisPJe
    function detectarMaisPJe() {
        // Verifica se a extensão maisPJe está ativa
        if (window.preferencias && window.preferencias.extensaoAtiva) {
            console.log('[MinutaPJE] ⚠️ Extensão maisPJe detectada e ativa');
            return true;
        }

        // Verifica elementos típicos do maisPJe
        const elementosMaisPJe = document.querySelectorAll('[id*="maisPje"], [class*="maisPje"]');
        if (elementosMaisPJe.length > 0) {
            console.log('[MinutaPJE] ⚠️ Elementos maisPJe detectados no DOM');
            return true;
        }

        return false;
    }

    // Função melhorada para clicar em botões com proteção anti-conflito
    async function clicarBotaoSeguro(seletor, timeout = 5000) {
        return debounceClick(seletor, async () => {

            // Marca que MinutaPJE está executando
            window.MinutaPJE_executando = true;

            try {
                const elemento = await waitForElement(seletor, timeout);

                if (!elemento) {
                    console.warn(`[MinutaPJE] Elemento não encontrado: ${seletor}`);
                    return false;
                }

                // Verifica se o elemento está sendo usado por outra extensão
                if (elemento.dataset.maisPjeProcessando) {
                    console.log(`[MinutaPJE] Elemento ${seletor} sendo processado por maisPJe, aguardando...`);
                    await sleep(2000);
                }

                // Marca o elemento como sendo processado pelo MinutaPJE
                elemento.dataset.minutaPjeProcessando = 'true';

                console.log(`[MinutaPJE] Clicando seguro em: ${seletor}`);
                elemento.click();

                await sleep(500);

                // Remove a marca após o clique
                delete elemento.dataset.minutaPjeProcessando;

                return true;

            } catch (error) {
                console.error(`[MinutaPJE] Erro ao clicar em ${seletor}:`, error);
                return false;
            } finally {
                // Libera a flag após um tempo
                setTimeout(() => {
                    window.MinutaPJE_executando = false;
                }, 3000);
            }
        });
    }

    // Criar interface do botão principal
    function criarInterface() {
        console.log('[MinutaPJE] Função criarInterface() executada');

        // Verificar se já existe - proteção dupla
        const botaoExistente = document.getElementById('minutapje-btn');
        if (botaoExistente) {
            console.log('[MinutaPJE] Botão já existe - não criando novamente');
            return;
        }

        // Criar botão simples
        const btnMinuta = document.createElement('button');
        btnMinuta.id = 'minutapje-btn';
        btnMinuta.textContent = 'Minuta';
        btnMinuta.style.cssText = `
            position: fixed;
            top: 50%;
            right: 20px;
            transform: translateY(-50%);
            z-index: 99999;
            padding: 15px 25px;
            background: #2196F3;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            transition: background 0.3s;
            font-family: Arial, sans-serif;
        `;
        btnMinuta.onmouseover = () => btnMinuta.style.background = '#1976D2';
        btnMinuta.onmouseout = () => btnMinuta.style.background = '#2196F3';

        btnMinuta.onclick = () => {
            console.log('[MinutaPJE] Botão clicado!');
            executarMinuta();
        };

        document.body.appendChild(btnMinuta);
        console.log('[MinutaPJE] Botão adicionado ao DOM');
    }

    // Sistema de regras baseado no conteúdo da fundamentação
    const REGRAS_FUNDAMENTACAO = [
        {
            trigger: "promover a execução",
            descricao: "Regra para execução - promover execução",
            params: {
                pec: false,
                sigilo: false,
                prazo: 5,
                primeiroDestinatario: true,
                movimento: null, // null = não configurar movimento
                assinar: true
            }
        }
        // Outras regras serão adicionadas aqui
    ];

    // Função para analisar fundamentação e determinar parâmetros
    function analisarFundamentacao() {
        try {
            // Tenta diferentes seletores para encontrar a fundamentação
            let fundamentacao = null;

            // Seletor 1: O que o usuário forneceu
            fundamentacao = document.querySelector('div[aria-label*="Fundamentação"] .ck-content');

            if (!fundamentacao) {
                // Seletor 2: Mais específico baseado no exemplo do usuário
                fundamentacao = document.querySelector('div[aria-label="Fundamentação. Alt+F10 para acessar a barra de tarefas"]');
            }

            if (!fundamentacao) {
                // Seletor 3: Classe específica do editor
                fundamentacao = document.querySelector('.area-conteudo.ck.ck-content.ck-editor__editable');
            }

            if (!fundamentacao) {
                // Seletor 4: Qualquer div com ck-content
                fundamentacao = document.querySelector('div.ck-content[contenteditable="true"]');
            }

            if (!fundamentacao) {
                console.warn('[MinutaPJE] Elemento de fundamentação não encontrado com nenhum seletor');
                console.log('[MinutaPJE] Tentando buscar qualquer elemento editável...');

                // Debug: lista todos os elementos editáveis
                const editaveis = document.querySelectorAll('[contenteditable="true"]');
                console.log(`[MinutaPJE] Encontrados ${editaveis.length} elementos editáveis`);

                if (editaveis.length > 0) {
                    fundamentacao = editaveis[0]; // Usa o primeiro encontrado
                    console.log('[MinutaPJE] Usando primeiro elemento editável encontrado');
                }
            }

            if (!fundamentacao) {
                return null;
            }

            const textoFundamentacao = fundamentacao.textContent.toLowerCase();
            console.log('[MinutaPJE] Texto da fundamentação encontrado:', textoFundamentacao.substring(0, 200) + '...');

            // Procura por regras que correspondem ao texto
            for (const regra of REGRAS_FUNDAMENTACAO) {
                if (textoFundamentacao.includes(regra.trigger.toLowerCase())) {
                    console.log(`[MinutaPJE] Regra encontrada: ${regra.descricao}`);
                    console.log('[MinutaPJE] Parâmetros da regra:', regra.params);
                    return regra.params;
                }
            }

            console.warn('[MinutaPJE] Nenhuma regra correspondente encontrada na fundamentação');
            return null;

        } catch (error) {
            console.error('[MinutaPJE] Erro ao analisar fundamentação:', error);
            return null;
        }
    }

    // Função principal de execução da minuta (MODIFICADA COM PROTEÇÃO)
    async function executarMinuta() {
        try {
            console.log('[MinutaPJE] Iniciando execução da minuta...');

            // Verifica conflitos antes de começar
            if (detectarMaisPJe()) {
                criarLogExecucao('⚠️ maisPJe detectado - usando modo compatibilidade', 'warning');
            }

            // Analisa fundamentação para determinar parâmetros
            let params = analisarFundamentacao();

            if (!params) {
                // Fallback para parâmetros padrão se não encontrar regra
                console.log('[MinutaPJE] Usando parâmetros padrão');
                params = {
                    pec: false,
                    sigilo: false,
                    prazo: 11,
                    primeiroDestinatario: true,
                    movimento: 'bloqueio',
                    assinar: false
                };
            }

            console.log('[MinutaPJE] Parâmetros finais:', params);

            // Log inicial
            criarLogExecucao('Iniciando execução da minuta...');

            // Etapa 1: Configurar sigilo
            criarLogExecucao('Etapa 1: Configurando sigilo...');
            await configurarSigilo(params.sigilo);

            // Etapa 2: Configurar PEC
            criarLogExecucao('Etapa 2: Configurando PEC...');
            await configurarPEC(params.pec);

            // Etapa 3: Configurar prazo (se especificado)
            if (params.prazo) {
                criarLogExecucao('Etapa 3: Configurando prazo...');
                await configurarPrazo(params.prazo, params.primeiroDestinatario);
            } else {
                criarLogExecucao('Etapa 3: Prazo não especificado, pulando...');
            }

            // Etapa 4: Configurar movimento (se especificado)
            if (params.movimento) {
                criarLogExecucao('Etapa 4: Configurando movimento...');
                await configurarMovimento(params.movimento);
            } else {
                criarLogExecucao('Etapa 4: Movimento não especificado, pulando...');
            }

            // Etapa 5: Assinar (se solicitado)
            if (params.assinar) {
                criarLogExecucao('Etapa 5: Enviando para assinatura...');
                await enviarParaAssinatura();
            } else {
                criarLogExecucao('Etapa 5: Assinatura não solicitada, pulando...');
            }

            criarLogExecucao('✅ Minuta executada com sucesso!', 'success');

        } catch (error) {
            console.error('[MinutaPJE] Erro:', error);
            criarLogExecucao(`❌ Erro: ${error.message}`, 'error');
        }
    }

    // Função para configurar sigilo
    async function configurarSigilo(ativar) {
        try {
            const toggles = document.querySelectorAll('mat-slide-toggle');
            let sigiloToggle = null;

            for (const toggle of toggles) {
                if (toggle.textContent.toLowerCase().includes('sigilo')) {
                    sigiloToggle = toggle;
                    break;
                }
            }

            if (!sigiloToggle) {
                console.warn('[MinutaPJE] Toggle de sigilo não encontrado');
                return false;
            }

            const sigiloInput = sigiloToggle.querySelector('input[type="checkbox"], input.mat-slide-toggle-input');
            const checked = sigiloInput?.getAttribute('aria-checked') === 'true';

            if ((ativar && !checked) || (!ativar && checked)) {
                const label = sigiloToggle.querySelector('label.mat-slide-toggle-label');
                if (label) {
                    label.click();
                    await sleep(500);
                }
            }

            return true;
        } catch (error) {
            console.error('[MinutaPJE] Erro ao configurar sigilo:', error);
            return false;
        }
    }

    // Função para configurar PEC
    async function configurarPEC(marcar) {
        try {
            let pecCheckbox = null;
            let pecInput = null;

            // Tenta diferentes seletores
            try {
                pecCheckbox = document.querySelector('mat-checkbox[aria-label="Enviar para PEC"]');
                pecInput = pecCheckbox?.querySelector('input[type="checkbox"]');
            } catch (e) {
                try {
                    pecCheckbox = document.querySelector('div.checkbox-pec mat-checkbox');
                    pecInput = pecCheckbox?.querySelector('input[type="checkbox"]');
                } catch (e2) {
                    pecInput = document.querySelector('input[type="checkbox"][aria-label="Enviar para PEC"]');
                    pecCheckbox = pecInput?.closest('mat-checkbox');
                }
            }

            if (!pecCheckbox || !pecInput) {
                console.warn('[MinutaPJE] Checkbox PEC não encontrado');
                return false;
            }

            // Verifica estado atual
            const checked = pecInput.getAttribute('aria-checked') === 'true' ||
                pecInput.checked ||
                pecCheckbox.classList.contains('mat-checkbox-checked');

            // Clica se necessário mudar estado
            if ((marcar && !checked) || (!marcar && checked)) {
                const label = pecCheckbox.querySelector('label.mat-checkbox-layout');
                if (label) {
                    label.click();
                } else {
                    pecCheckbox.click();
                }
                await sleep(300);
            }

            return true;
        } catch (error) {
            console.error('[MinutaPJE] Erro ao configurar PEC:', error);
            return false;
        }
    }

    // Função para configurar prazo (MODIFICADA COM PROTEÇÃO)
    async function configurarPrazo(prazo, apenasUm) {
        try {
            console.log(`[MinutaPJE] Configurando prazo: ${prazo} dias, apenas primeiro: ${apenasUm}`);

            // Procura pela tabela de destinatários
            const linhas = document.querySelectorAll('table.t-class tr.ng-star-inserted');

            if (linhas.length === 0) {
                console.warn('[MinutaPJE] Nenhuma linha de destinatário encontrada!');
                return false;
            }

            let ativos = [];

            // Identifica destinatários ativos
            for (const tr of linhas) {
                try {
                    const checkbox = tr.querySelector('input[type="checkbox"][aria-label="Intimar parte"]');
                    const nomeElem = tr.querySelector('.destinario');

                    if (checkbox && nomeElem) {
                        const nome = nomeElem.textContent.trim().toUpperCase();

                        // Se já está marcado, adiciona à lista de ativos
                        if (checkbox.getAttribute('aria-checked') === 'true' || checkbox.checked) {
                            ativos.push({ tr, checkbox, nome });
                            console.log(`[MinutaPJE] Destinatário ativo encontrado: ${nome}`);
                        }
                    }
                } catch (e) {
                    console.warn('[MinutaPJE] Erro ao processar linha de destinatário:', e);
                }
            }

            if (ativos.length === 0) {
                console.warn('[MinutaPJE] Nenhum destinatário ativo encontrado!');
                return false;
            }

            // Se apenas primeiro destinatário, desmarca os outros
            if (apenasUm && ativos.length > 1) {
                console.log('[MinutaPJE] Desmarcando destinatários extras, mantendo apenas o primeiro...');

                for (let i = 1; i < ativos.length; i++) {
                    try {
                        const { checkbox, nome } = ativos[i];
                        checkbox.click();
                        console.log(`[MinutaPJE] Checkbox do destinatário ${i + 1} (${nome}) desmarcado.`);
                        await sleep(200);
                    } catch (e) {
                        console.warn(`[MinutaPJE] Erro ao desmarcar checkbox ${i + 1}:`, e);
                    }
                }

                // Mantém apenas o primeiro na lista
                ativos = [ativos[0]];
            }

            // Preenche prazos dos destinatários ativos
            for (const { tr, nome } of ativos) {
                try {
                    const inputPrazo = tr.querySelector('mat-form-field.prazo input[type="text"].mat-input-element');

                    if (inputPrazo) {
                        // Limpa o campo primeiro
                        inputPrazo.focus();
                        inputPrazo.select();
                        inputPrazo.value = '';

                        // Preenche com o novo prazo
                        inputPrazo.value = prazo.toString();

                        // Dispara eventos
                        ['input', 'change', 'blur'].forEach(eventType => {
                            const event = new Event(eventType, { bubbles: true });
                            inputPrazo.dispatchEvent(event);
                        });

                        console.log(`[MinutaPJE] Prazo ${prazo} preenchido para destinatário: ${nome}`);
                        await sleep(200);
                    } else {
                        console.warn(`[MinutaPJE] Campo de prazo não encontrado para: ${nome}`);
                    }
                } catch (e) {
                    console.warn(`[MinutaPJE] Erro ao preencher prazo para ${nome}:`, e);
                }
            }

            // Clica em Gravar após preencher os prazos (USANDO FUNÇÃO SEGURA)
            await sleep(500);
            console.log('[MinutaPJE] Procurando botão Gravar...');

            const btnGravar = await waitForElement(
                "button[.//span[normalize-space(text())='Gravar'] and contains(@class, 'mat-raised-button')]",
                5000,
                true // xpath
            );

            if (btnGravar) {
                console.log('[MinutaPJE] Clicando em Gravar com proteção...');
                await clicarBotaoSeguro('button[aria-label="Salvar"]', 5000);
                await sleep(1000);
            } else {
                console.warn('[MinutaPJE] Botão Gravar não encontrado');
            }

            return true;
        } catch (error) {
            console.error('[MinutaPJE] Erro ao configurar prazo:', error);
            return false;
        }
    }

    // Função para configurar movimento (MODIFICADA COM PROTEÇÃO)
    async function configurarMovimento(movimento) {
        try {
            // Ativa aba Movimentos
            const abas = document.querySelectorAll('.mat-tab-label');
            let abaMovimentos = null;

            for (const aba of abas) {
                if (aba.textContent.toLowerCase().includes('movimento')) {
                    abaMovimentos = aba;
                    break;
                }
            }

            if (abaMovimentos && abaMovimentos.getAttribute('aria-selected') !== 'true') {
                abaMovimentos.click();
                await sleep(800);
            }

            // Busca checkbox do movimento
            const checkboxes = document.querySelectorAll('mat-checkbox.movimento');
            let movimentoEncontrado = false;

            const movimentoNorm = movimento.toLowerCase().trim();

            for (const checkbox of checkboxes) {
                const label = checkbox.querySelector('label .mat-checkbox-label');
                if (label) {
                    const labelText = label.textContent.toLowerCase().trim();

                    if (labelText.includes(movimentoNorm) ||
                        (movimentoNorm === 'frustrada' && labelText.includes('execução frustrada'))) {

                        const input = checkbox.querySelector('input[type="checkbox"]');
                        if (input && !input.checked) {
                            const innerContainer = checkbox.querySelector('.mat-checkbox-inner-container');
                            if (innerContainer) {
                                innerContainer.click();
                            } else {
                                input.click();
                            }
                            movimentoEncontrado = true;
                            break;
                        }
                    }
                }
            }

            if (!movimentoEncontrado) {
                console.warn(`[MinutaPJE] Movimento "${movimento}" não encontrado`);
                return false;
            }

            await sleep(500);

            // Clica em Gravar movimentos (USANDO FUNÇÃO SEGURA)
            const btnGravarMov = await waitForElement(
                "button[aria-label='Gravar os movimentos a serem lançados']",
                5000
            );

            if (btnGravarMov) {
                await clicarBotaoSeguro("button[aria-label='Gravar os movimentos a serem lançados']", 5000);
                await sleep(1000);

                // Confirma no diálogo
                const btnSim = await waitForElement(
                    "button[contains(@class, 'mat-button') and contains(@class, 'mat-primary') and .//span[text()='Sim']]",
                    5000,
                    true // xpath
                );

                if (btnSim) {
                    btnSim.click();
                    await sleep(1000);

                    // Salvar final (USANDO FUNÇÃO SEGURA)
                    const sucesso = await clicarBotaoSeguro("button[aria-label='Salvar'][color='primary']", 5000);
                    if (sucesso) {
                        await sleep(1000);
                    }
                }
            }

            return true;
        } catch (error) {
            console.error('[MinutaPJE] Erro ao configurar movimento:', error);
            return false;
        }
    }

    // Função para enviar para assinatura (MODIFICADA COM PROTEÇÃO)
    async function enviarParaAssinatura() {
        try {
            await sleep(3000); // Aguarda 3s após salvamento

            const sucesso = await clicarBotaoSeguro('button.mat-fab[aria-label="Enviar para assinatura"]', 10000);

            if (sucesso) {
                await sleep(1000);
                return true;
            } else {
                console.warn('[MinutaPJE] Botão de assinatura não encontrado');
                return false;
            }
        } catch (error) {
            console.error('[MinutaPJE] Erro ao enviar para assinatura:', error);
            return false;
        }
    }

    // Funções auxiliares
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function waitForElement(selector, timeout = 5000, isXPath = false) {
        return new Promise((resolve) => {
            const startTime = Date.now();

            const checkElement = () => {
                let element;

                if (isXPath) {
                    const result = document.evaluate(
                        selector,
                        document,
                        null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                        null
                    );
                    element = result.singleNodeValue;
                } else {
                    element = document.querySelector(selector);
                }

                if (element) {
                    resolve(element);
                } else if (Date.now() - startTime < timeout) {
                    setTimeout(checkElement, 100);
                } else {
                    resolve(null);
                }
            };

            checkElement();
        });
    }

    function criarLogExecucao(mensagem, tipo = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        let cor = '#2196F3'; // azul padrão

        switch (tipo) {
            case 'success': cor = '#4CAF50'; break;
            case 'error': cor = '#f44336'; break;
            case 'warning': cor = '#FF9800'; break;
        }

        console.log(`[MinutaPJE] ${timestamp} - ${mensagem}`);

        // Criar toast notification
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${cor};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 11000;
            font-family: Arial, sans-serif;
            font-size: 14px;
            max-width: 400px;
            word-wrap: break-word;
            transition: opacity 0.3s;
        `;
        toast.textContent = `${timestamp} - ${mensagem}`;

        document.body.appendChild(toast);

        // Remove toast após 4 segundos
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    // === INICIALIZAÇÃO COM PROTEÇÃO ===
    console.log('[MinutaPJE] Script iniciado!');
    console.log('[MinutaPJE] URL atual:', window.location.href);
    console.log('[MinutaPJE] Document ready state:', document.readyState);

    // Verificar se é página de minutar
    if (!window.location.href.includes('minutar')) {
        console.log('[MinutaPJE] Não é página de minutar, saindo...');
        return;
    }

    console.log('[MinutaPJE] É página de minutar, continuando...');

    // Flag para garantir que o botão seja criado apenas uma vez
    let botaoJaCriado = false;

    // Função única de criação da interface
    const criarInterfaceUnica = () => {
        if (botaoJaCriado) {
            console.log('[MinutaPJE] Botão já foi criado anteriormente, ignorando...');
            return;
        }

        if (!document.body) {
            console.log('[MinutaPJE] Body não existe ainda, tentando novamente em 500ms...');
            setTimeout(criarInterfaceUnica, 500);
            return;
        }

        console.log('[MinutaPJE] Criando interface única...');
        criarInterface();
        botaoJaCriado = true;
        console.log('[MinutaPJE] ✅ Interface criada com sucesso - não será recriada');
    };

    // Criar interface apenas uma vez após aguardar o DOM carregar
    setTimeout(criarInterfaceUnica, 2000); // Aguarda 2 segundos antes de criar

})();
