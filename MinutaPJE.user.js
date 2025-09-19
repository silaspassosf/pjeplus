// ==UserScript==
// @name         MinutaPJE
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Automatização de minuta PJE baseada na função ato_judicial
// @author       PjePlus
// @match        *://*/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    // Criar interface do botão principal
    function criarInterface() {
        console.log('[MinutaPJE] Função criarInterface() executada');

        // Verificar se já existe
        if (document.getElementById('minutapje-btn')) {
            console.log('[MinutaPJE] Botão já existe, removendo...');
            document.getElementById('minutapje-btn').remove();
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

        // Verificar se foi realmente adicionado
        setTimeout(() => {
            const btnCheck = document.getElementById('minutapje-btn');
            if (btnCheck) {
                console.log('[MinutaPJE] ✅ Botão confirmado no DOM');
            } else {
                console.error('[MinutaPJE] ❌ Botão não encontrado no DOM após criação');
            }
        }, 100);
    }    // Sistema de regras baseado no conteúdo da fundamentação
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
        },
        {
            trigger: "apesar de devidamente intimado",
            descricao: "Regra para intimação não cumprida",
            params: {
                pec: false,
                sigilo: true,
                prazo: 30,
                primeiroDestinatario: true,
                movimento: "bloqueio",
                assinar: true
            }
        },
        {
            trigger: "para pagamento da parcela pendente",
            descricao: "Regra para pagamento de parcela pendente",
            params: {
                pec: false,
                sigilo: false,
                prazo: 10,
                primeiroDestinatario: false,
                movimento: null, // null = não configurar movimento
                assinar: true
            }
        },
        {
            trigger: "valores vencido e pendente",
            descricao: "Regra para valores vencidos e pendentes",
            params: {
                pec: false,
                sigilo: false,
                prazo: 11,
                primeiroDestinatario: false,
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

    // Função principal de execução da minuta
    async function executarMinuta() {
        try {
            console.log('[MinutaPJE] Iniciando execução da minuta...');

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
            } console.log('[MinutaPJE] Parâmetros finais:', params);

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

    // Função para configurar prazo
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

            // Clica em Gravar após preencher os prazos
            await sleep(500);
            console.log('[MinutaPJE] Procurando botão Gravar...');

            // Tenta diferentes seletores para o botão Gravar
            let btnGravar = null;

            // Seletor 1: Baseado no HTML fornecido pelo usuário
            btnGravar = await waitForElement(
                'button[mat-raised-button][color="primary"][type="submit"][aria-label="Gravar a intimação/notificação"]',
                3000
            );

            if (!btnGravar) {
                // Seletor 2: Por classe específica
                btnGravar = await waitForElement(
                    'button.botao-salvar.mat-raised-button.mat-primary',
                    3000
                );
            }

            if (!btnGravar) {
                // Seletor 3: Por texto do botão
                btnGravar = await waitForElement(
                    'button[mat-raised-button] span:contains("Gravar")',
                    3000
                );
            }

            if (!btnGravar) {
                // Seletor 4: XPath mais genérico
                btnGravar = await waitForElement(
                    "//button[contains(@class, 'mat-raised-button') and contains(@class, 'mat-primary') and .//span[normalize-space(text())='Gravar']]",
                    3000,
                    true // xpath
                );
            }

            if (btnGravar) {
                console.log('[MinutaPJE] Botão Gravar encontrado, clicando...');
                btnGravar.click();
                await sleep(1000);
            } else {
                console.warn('[MinutaPJE] Botão Gravar não encontrado com nenhum seletor');

                // Debug: lista todos os botões encontrados
                const botoes = document.querySelectorAll('button[mat-raised-button]');
                console.log(`[MinutaPJE] Encontrados ${botoes.length} botões mat-raised-button`);

                for (let i = 0; i < botoes.length; i++) {
                    const botao = botoes[i];
                    console.log(`[MinutaPJE] Botão ${i}: ${botao.textContent.trim()} - Classes: ${botao.className}`);
                }
            }

            return true;
        } catch (error) {
            console.error('[MinutaPJE] Erro ao configurar prazo:', error);
            return false;
        }
    }

    // Função para configurar movimento
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

            // Clica em Gravar movimentos
            const btnGravarMov = await waitForElement(
                "button[aria-label='Gravar os movimentos a serem lançados']",
                5000
            );

            if (btnGravarMov) {
                btnGravarMov.click();
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

                    // Salvar final
                    const btnSalvarFinal = await waitForElement(
                        "button[aria-label='Salvar'][color='primary']",
                        5000
                    );

                    if (btnSalvarFinal) {
                        btnSalvarFinal.click();
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

    // Função para enviar para assinatura
    async function enviarParaAssinatura() {
        try {
            await sleep(3000); // Aguarda 3s após salvamento

            const btnAssinar = await waitForElement(
                'button.mat-fab[aria-label="Enviar para assinatura"]',
                10000
            );

            if (btnAssinar) {
                btnAssinar.click();
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
                } else if (selector.includes(':contains(')) {
                    // Implementação simples de :contains() para JavaScript
                    const [baseSelector, containsText] = selector.split(':contains(');
                    const text = containsText.replace(')', '').replace(/['"]/g, '');
                    const elements = document.querySelectorAll(baseSelector);

                    for (const el of elements) {
                        if (el.textContent.includes(text)) {
                            element = el;
                            break;
                        }
                    }
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
        const cor = tipo === 'success' ? '#4CAF50' : tipo === 'error' ? '#f44336' : '#2196F3';

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

    // Inicialização mais robusta
    console.log('[MinutaPJE] Script iniciado!');
    console.log('[MinutaPJE] URL atual:', window.location.href);
    console.log('[MinutaPJE] Document ready state:', document.readyState);

    // Verificar se é página de minutar
    if (!window.location.href.includes('minutar')) {
        console.log('[MinutaPJE] Não é página de minutar, saindo...');
        return;
    }

    console.log('[MinutaPJE] É página de minutar, continuando...');

    // Criar interface imediatamente
    const criarInterfaceImediata = () => {
        console.log('[MinutaPJE] Criando interface imediata...');

        if (!document.body) {
            console.log('[MinutaPJE] Body não existe ainda, tentando novamente em 100ms...');
            setTimeout(criarInterfaceImediata, 100);
            return;
        }

        criarInterface();
    };

    // Tentar criar interface várias vezes
    criarInterfaceImediata();
    setTimeout(criarInterfaceImediata, 1000);
    setTimeout(criarInterfaceImediata, 3000);
    setTimeout(criarInterfaceImediata, 5000);

})();
