// ==UserScript==
// @name         0-Temper Robusto
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Automação robusta para PJe - Sistema de vínculos sequenciais baseado em fluxos.py
// @author       You
// @match        https://*.pje.jus.br/*
// @match        https://pje*.trt*.jus.br/*
// @match        https://pje*.tjsp.jus.br/*
// @match        https://pje*.tjrj.jus.br/*
// @match        https://pje*.tjmg.jus.br/*
// @match        https://pje*.tjrs.jus.br/*
// @match        https://pje*.tjpr.jus.br/*
// @match        https://pje*.tjsc.jus.br/*
// @match        https://pje*.tjgo.jus.br/*
// @match        https://pje*.tjba.jus.br/*
// @match        https://pje*.tjpe.jus.br/*
// @match        https://pje*.tjce.jus.br/*
// @match        https://pje*.tjpb.jus.br/*
// @match        https://pje*.tjal.jus.br/*
// @match        https://pje*.tjse.jus.br/*
// @match        https://pje*.tjrn.jus.br/*
// @match        https://pje*.tjpi.jus.br/*
// @match        https://pje*.tjma.jus.br/*
// @match        https://pje*.tjmt.jus.br/*
// @match        https://pje*.tjms.jus.br/*
// @match        https://pje*.tjdf.jus.br/*
// @match        https://pje*.tjro.jus.br/*
// @match        https://pje*.tjac.jus.br/*
// @match        https://pje*.tjap.jus.br/*
// @match        https://pje*.tjam.jus.br/*
// @match        https://pje*.tjrr.jus.br/*
// @match        https://pje*.tjto.jus.br/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    // Sistema de armazenamento global dos vínculos (equivalente ao browser storage do Python)
    if (!window.vinculoStorage) {
        window.vinculoStorage = {
            tempBt: [],                    // Equivalente ao tempBt do JS
            tempAAEspecial: [],           // Equivalente ao tempAAEspecial do JS
            AALote: '',                   // Equivalente ao AALote do JS
            processandoVinculos: false,   // Flag para controle de processamento
            filaExecucao: [],            // Fila para processamento sequencial
            maxTentativas: 3,            // Máximo de tentativas por ação
            delayEntreAcoes: 1500        // Delay padrão entre ações
        };
    }

    // Remove qualquer instância anterior da interface
    var old = document.getElementById('maisPjeBox');
    if (old) old.remove();

    // ====== SISTEMA DE VÍNCULOS SEQUENCIAIS (baseado em fluxos.py) ======

    /**
     * Armazena um vínculo para processamento (equivalente a storage_vinculo)
     */
    window.storageVinculo = function(param) {
        console.log('[VINCULO] storage_vinculo(' + param + ')');
        
        // Processa vínculos em cadeia usando conferirVinculoEspecial
        var paramProcessado = window.conferirVinculoEspecial(param);
        
        // Armazena o vínculo processado no storage global
        window.vinculoStorage.tempBt = ['vinculo', paramProcessado];
        
        return paramProcessado;
    };

    /**
     * Confere e processa vínculos especiais em sequência (equivalente a conferir_vinculo_especial)
     */
    window.conferirVinculoEspecial = function(aaVinculo) {
        if (typeof aaVinculo === 'undefined') aaVinculo = 'Nenhum';
        
        console.log('[VINCULO] conferirVinculoEspecial(' + aaVinculo + ')');
        
        var tempAAEspecial = window.vinculoStorage.tempAAEspecial;
        
        // Se tempAAEspecial está vazio ou é 'Nenhum', usa o vínculo atual
        if (!tempAAEspecial || tempAAEspecial === 'Nenhum' || 
            (Array.isArray(tempAAEspecial) && tempAAEspecial.length === 0)) {
            var aaVinculoFinal = aaVinculo;
        } else {
            var aaVinculoFinal = tempAAEspecial;
        }
        
        // Processa vínculos múltiplos como array
        if (typeof aaVinculoFinal === 'string' && aaVinculoFinal.indexOf(',') > -1) {
            tempAAEspecial = aaVinculoFinal.split(',').map(function(v) { return v.trim(); });
        } else if (Array.isArray(aaVinculoFinal)) {
            tempAAEspecial = aaVinculoFinal.slice();
        } else {
            tempAAEspecial = aaVinculoFinal !== 'Nenhum' ? [aaVinculoFinal] : [];
        }
        
        // Remove o primeiro item da lista (próximo a executar)
        if (tempAAEspecial.length > 0) {
            var proximoVinculo = tempAAEspecial.shift();
            
            console.log('[VINCULO] Próximo vínculo: ' + proximoVinculo);
            console.log('[VINCULO] AAEspecial remanescente: ' + JSON.stringify(tempAAEspecial));
            
            // Atualiza o storage com os vínculos remanescentes
            window.vinculoStorage.tempAAEspecial = tempAAEspecial;
            
            return proximoVinculo;
        }
        
        return 'Nenhum';
    };

    /**
     * Monitora fim de execução e processa próximos vínculos (equivalente a monitor_fim)
     */
    window.monitorFim = function(param) {
        if (!param) {
            param = window.vinculoStorage.tempAAEspecial;
            if (Array.isArray(param)) {
                param = param.length > 0 ? param.join(',') : 'Nenhum';
            }
        }
        
        console.log('[VINCULO] monitorFim(' + param + ')');
        
        if (param && param !== 'Nenhum') {
            // Adiciona vínculo à fila de processamento
            window.adicionarVinculoFila(param);
        } else {
            // Verifica se é execução em lote
            var aaLote = window.vinculoStorage.AALote;
            if (aaLote) {
                console.log('[VINCULO] Finalizando execução em lote: ' + aaLote);
                window.vinculoStorage.AALote = '';
            }
            console.log('[VINCULO] Fim da cadeia de vínculos.');
        }
    };

    /**
     * Adiciona vínculo à fila de processamento
     */
    window.adicionarVinculoFila = function(vinculo) {
        console.log('[FILA] Adicionando à fila: ' + vinculo);
        window.vinculoStorage.filaExecucao.push(vinculo);
        
        // Inicia processamento se não estiver ativo
        if (!window.vinculoStorage.processandoVinculos) {
            window.processarFilaVinculos();
        }
    };

    /**
     * Processa fila de vínculos sequencialmente (equivalente a processar_fila_vinculos)
     */
    window.processarFilaVinculos = function() {
        if (window.vinculoStorage.processandoVinculos) {
            console.log('[FILA] Processamento já ativo, aguardando...');
            return;
        }
        
        if (window.vinculoStorage.filaExecucao.length === 0) {
            console.log('[FILA] Fila vazia.');
            return;
        }
        
        window.vinculoStorage.processandoVinculos = true;
        console.log('[FILA] Iniciando processamento da fila de vínculos.');
        
        function processarProximo() {
            if (window.vinculoStorage.filaExecucao.length === 0) {
                window.vinculoStorage.processandoVinculos = false;
                console.log('[FILA] Processamento da fila finalizado.');
                return;
            }
            
            var vinculoStr = window.vinculoStorage.filaExecucao.shift();
            
            if (!vinculoStr || vinculoStr.toLowerCase() === 'nenhum') {
                console.log('[FILA] Vínculo "Nenhum" ou vazio, continuando...');
                setTimeout(processarProximo, 500);
                return;
            }

            console.log('[FILA] Processando vínculo: ' + vinculoStr);

            var vinculoProcessado = window.storageVinculo(vinculoStr);
            
            if (!vinculoProcessado || vinculoProcessado.toLowerCase() === 'nenhum') {
                console.log('[FILA] Vínculo retornou "Nenhum", continuando...');
                setTimeout(processarProximo, 500);
                return;
            }

            // Extrair tipo e nome do botão
            var tipoVinculo = '';
            var nomeBotaoVinculo = vinculoProcessado;
            
            if (vinculoProcessado.indexOf('|') > -1) {
                var partes = vinculoProcessado.split('|');
                tipoVinculo = partes[0].trim();
                nomeBotaoVinculo = partes[1].trim();
            }

            console.log('[FILA] Extraído - Tipo: "' + tipoVinculo + '", Botão: "' + nomeBotaoVinculo + '"');

            // Criar configuração para execução
            var configVinculo = {
                nm_botao: nomeBotaoVinculo,
                tipo: tipoVinculo,
                vinculo: 'Nenhum'
            };

            // Mapear tipo para função de execução (baseado no mapeamento do fluxos.py)
            var funcaoExecucao = window.obterFuncaoExecucao(tipoVinculo);

            if (funcaoExecucao) {
                console.log('[FILA] Executando vínculo: ' + nomeBotaoVinculo);
                try {
                    funcaoExecucao(configVinculo);
                    setTimeout(processarProximo, window.vinculoStorage.delayEntreAcoes);
                } catch (e) {
                    console.error('[FILA][ERRO] Erro ao executar vínculo:', e);
                    setTimeout(processarProximo, 1000);
                }
            } else {
                console.warn('[FILA] Tipo de vínculo não reconhecido: ' + tipoVinculo);
                setTimeout(processarProximo, 500);
            }
        }
        
        // Iniciar processamento com delay inicial
        setTimeout(processarProximo, 1000);
    };

    /**
     * Mapeia tipo de vínculo para função de execução (baseado no fluxos.py)
     */
    window.obterFuncaoExecucao = function(tipo) {
        var tipoLower = tipo.toLowerCase();
        
        // Mapeamento baseado na estrutura do fluxos.py
        if (tipoLower.indexOf('despacho') > -1 || 
            tipoLower.indexOf('homologação') > -1 || 
            tipoLower.indexOf('sobrest') > -1 || 
            tipoLower.indexOf('extinção') > -1 || 
            tipoLower.indexOf('bacen') > -1 || 
            tipoLower.indexOf('idpj') > -1) {
            return window.fluxoDespacho;
        }
        
        if (tipoLower.indexOf('intimação') > -1 || 
            tipoLower.indexOf('mandado') > -1 || 
            tipoLower.indexOf('notificação') > -1 || 
            tipoLower.indexOf('edital') > -1 || 
            tipoLower.indexOf('comunicação') > -1) {
            return window.fluxoComunicacao;
        }
        
        if (tipoLower.indexOf('anexar') > -1) {
            return window.fluxoAnexar;
        }
        
        if (tipoLower.indexOf('autogigs') > -1 || 
            tipoLower.indexOf('prazo') > -1 || 
            tipoLower.indexOf('comentario') > -1 || 
            tipoLower.indexOf('lembrete') > -1 || 
            tipoLower.indexOf('gigs') > -1) {
            return window.fluxoGigs;
        }
        
        return null;
    };

    /**
     * Obtém vínculos descendentes com prevenção de loops infinitos
     */
    window.obterVinculosDescendentes = function(aaPai, vinculoAtual) {
        console.log('[VINCULO] obterVinculosDescendentes(' + aaPai + ', ' + vinculoAtual + ')');
        
        if (!vinculoAtual || vinculoAtual.indexOf('Nenhum') > -1) {
            return 'Nenhum';
        }
        
        // Sistema de prevenção de loops infinitos
        if (!window.vinculoStorage.botoesProcessados) {
            window.vinculoStorage.botoesProcessados = new Set();
        }
        
        var chaveVinculo = aaPai + '|' + vinculoAtual;
        if (window.vinculoStorage.botoesProcessados.has(chaveVinculo)) {
            console.warn('[VINCULO] Loop detectado para: ' + chaveVinculo + ', interrompendo.');
            return 'Nenhum';
        }
        
        window.vinculoStorage.botoesProcessados.add(chaveVinculo);
        
        return vinculoAtual;
    };

    // ====== FLUXOS DE AUTOMAÇÃO ROBUSTOS ======

    /**
     * Fluxo de Despacho com tratamento robusto de erros (baseado em fluxos.py)
     */
    window.fluxoDespacho = function(config) {
        console.log('[DESPACHO] Iniciando fluxo:', config);
        
        var tentativas = 0;
        var maxTentativas = window.vinculoStorage.maxTentativas;
        
        function executarDespacho() {
            tentativas++;
            console.log('[DESPACHO] Tentativa ' + tentativas + '/' + maxTentativas);
            
            try {
                // 1. Verificar se já está na página do editor
                if (window.location.href.indexOf('/editor/') > -1 || 
                    document.querySelector('pje-editor-lateral') || 
                    document.querySelector('button[aria-label="Salvar"]') ||
                    document.querySelector('input[aria-label="Filtro"]')) {
                    console.log('[DESPACHO] Já na página do editor.');
                    setTimeout(executarPreenchimento, 800);
                    return;
                }
                
                // 2. Buscar e clicar na tarefa do processo
                var seletoresTarefa = [
                    'button[mattooltip="Abre a tarefa do processo"]',
                    'a[mattooltip="Abre a tarefa do processo"]',
                    'button[aria-label*="tarefa"]',
                    'a[aria-label*="tarefa"]'
                ];
                
                var tarefaBtn = null;
                for (var i = 0; i < seletoresTarefa.length; i++) {
                    tarefaBtn = document.querySelector(seletoresTarefa[i]);
                    if (tarefaBtn) break;
                }
                
                // Busca alternativa por texto
                if (!tarefaBtn) {
                    tarefaBtn = Array.from(document.querySelectorAll('button, a')).find(function(btn) {
                        var texto = (btn.textContent || '').toLowerCase();
                        return texto.includes('cumprimento') || texto.includes('tarefa');
                    });
                }
                
                if (tarefaBtn) {
                    console.log('[DESPACHO] Clicando na tarefa do processo.');
                    
                    if (tarefaBtn.tagName === 'A') {
                        // Para links, navegar na mesma aba
                        tarefaBtn.removeAttribute('target');
                        window.location.href = tarefaBtn.href;
                    } else {
                        tarefaBtn.click();
                    }
                    
                    // Aguardar carregamento
                    setTimeout(function() {
                        executarFluxoEditor();
                    }, 2000);
                } else {
                    console.warn('[DESPACHO] Tarefa não encontrada. Tentativa ' + tentativas);
                    if (tentativas < maxTentativas) {
                        setTimeout(executarDespacho, 2000);
                    } else {
                        console.error('[DESPACHO] Falha após ' + maxTentativas + ' tentativas.');
                        finalizarDespacho();
                    }
                }
                
            } catch (e) {
                console.error('[DESPACHO][ERRO] Erro na execução:', e);
                if (tentativas < maxTentativas) {
                    setTimeout(executarDespacho, 2000);
                } else {
                    finalizarDespacho();
                }
            }
        }
        
        function executarFluxoEditor() {
            try {
                console.log('[DESPACHO] Executando fluxo no editor.');
                
                // Sequência de cliques: Análise -> Conclusão
                var sequenciaSteps = [
                    {
                        nome: 'Análise',
                        seletores: [
                            'button[title*="Análise"]',
                            'mat-tab[aria-label*="Análise"]',
                            'button:contains("Análise")'
                        ]
                    },
                    {
                        nome: 'Conclusão',
                        seletores: [
                            'button[title*="Conclusão"]',
                            'mat-tab[aria-label*="Conclusão"]',
                            'button:contains("Conclusão")'
                        ]
                    }
                ];
                
                function executarStep(stepIndex) {
                    if (stepIndex >= sequenciaSteps.length) {
                        setTimeout(executarPreenchimento, 1000);
                        return;
                    }
                    
                    var step = sequenciaSteps[stepIndex];
                    var elemento = null;
                    
                    // Procurar elemento pelos seletores
                    for (var i = 0; i < step.seletores.length; i++) {
                        elemento = document.querySelector(step.seletores[i]);
                        if (elemento && elemento.offsetParent !== null) break;
                    }
                    
                    if (elemento) {
                        console.log('[DESPACHO] Executando: ' + step.nome);
                        elemento.click();
                        setTimeout(function() {
                            executarStep(stepIndex + 1);
                        }, 1200);
                    } else {
                        console.warn('[DESPACHO] ' + step.nome + ' não encontrado, prosseguindo.');
                        executarStep(stepIndex + 1);
                    }
                }
                
                executarStep(0);
                
            } catch (e) {
                console.error('[DESPACHO][ERRO] Erro no fluxo do editor:', e);
                setTimeout(executarPreenchimento, 1000);
            }
        }
        
        function executarPreenchimento() {
            try {
                console.log('[DESPACHO] Iniciando preenchimento.');
                
                // Aguardar elementos do editor
                var checkEditor = setInterval(function() {
                    if (document.querySelector('input[aria-label="Filtro"]') || 
                        document.querySelector('button[aria-label="Salvar"]')) {
                        clearInterval(checkEditor);
                        preencherFormulario();
                    }
                }, 500);
                
                setTimeout(function() {
                    clearInterval(checkEditor);
                    preencherFormulario();
                }, 8000);
                
            } catch (e) {
                console.error('[DESPACHO][ERRO] Erro no preenchimento:', e);
                finalizarDespacho();
            }
        }
        
        function preencherFormulario() {
            try {
                console.log('[DESPACHO] Preenchendo formulário.');
                
                // 1. Selecionar tipo "Despacho"
                setTimeout(function() {
                    var btnDespacho = Array.from(document.querySelectorAll('button')).find(function(btn) {
                        return btn.textContent.trim() === 'Despacho';
                    });
                    if (btnDespacho) {
                        btnDespacho.click();
                        console.log('[DESPACHO] Tipo "Despacho" selecionado.');
                    }
                }, 500);
                
                // 2. Preencher modelo se especificado
                if (config.modelo) {
                    setTimeout(function() {
                        var campoFiltro = document.querySelector('input[aria-label="Filtro"]');
                        if (campoFiltro) {
                            campoFiltro.focus();
                            campoFiltro.value = '';
                            campoFiltro.value = config.modelo;
                            campoFiltro.dispatchEvent(new Event('input', { bubbles: true }));
                            console.log('[DESPACHO] Modelo preenchido: ' + config.modelo);
                        }
                    }, 1000);
                }
                
                // 3. Finalizar após preenchimento
                setTimeout(finalizarDespacho, 2000);
                
            } catch (e) {
                console.error('[DESPACHO][ERRO] Erro ao preencher formulário:', e);
                finalizarDespacho();
            }
        }
        
        function finalizarDespacho() {
            console.log('[DESPACHO] Fluxo finalizado.');
            
            // Processar vínculos subsequentes
            var vinculo = config.vinculo || 'Nenhum';
            if (vinculo && vinculo !== 'Nenhum') {
                console.log('[DESPACHO] Processando vínculo: ' + vinculo);
                var vinculosProcessados = window.obterVinculosDescendentes(config.nm_botao, vinculo);
                setTimeout(function() {
                    window.monitorFim(vinculosProcessados);
                }, 1500);
            } else {
                window.monitorFim('Nenhum');
            }
        }
        
        // Iniciar execução
        executarDespacho();
    };

    /**
     * Fluxo de Comunicação robusto
     */
    window.fluxoComunicacao = function(config) {
        console.log('[COMUNICACAO] Iniciando fluxo:', config);
        
        try {
            // Implementação básica - pode ser expandida
            console.log('[COMUNICACAO] Processando: ' + config.nm_botao);
            
            // Processar vínculos
            setTimeout(function() {
                var vinculo = config.vinculo || 'Nenhum';
                if (vinculo !== 'Nenhum') {
                    var vinculosProcessados = window.obterVinculosDescendentes(config.nm_botao, vinculo);
                    window.monitorFim(vinculosProcessados);
                } else {
                    window.monitorFim('Nenhum');
                }
            }, 1000);
            
        } catch (e) {
            console.error('[COMUNICACAO][ERRO]:', e);
            window.monitorFim('Nenhum');
        }
    };

    /**
     * Fluxo de GIGS robusto
     */
    window.fluxoGigs = function(config) {
        console.log('[GIGS] Iniciando fluxo:', config);
        
        try {
            // Verificar se GIGS está aberto
            var gigsAberto = document.querySelector('pje-gigs-ficha-processo');
            
            if (!gigsAberto) {
                // Abrir GIGS
                var btnGigs = document.querySelector('button[aria-label="GIGS"]') ||
                             document.querySelector('button[title*="GIGS"]');
                if (btnGigs) {
                    btnGigs.click();
                    console.log('[GIGS] Abrindo GIGS.');
                    setTimeout(function() { executarAcaoGigs(); }, 1500);
                } else {
                    console.warn('[GIGS] Botão GIGS não encontrado.');
                    finalizarGigs();
                }
            } else {
                executarAcaoGigs();
            }
            
        } catch (e) {
            console.error('[GIGS][ERRO]:', e);
            finalizarGigs();
        }
        
        function executarAcaoGigs() {
            try {
                console.log('[GIGS] Executando ação: ' + config.nm_botao);
                
                // Implementação específica baseada no tipo
                var tipo = (config.tipo || '').toLowerCase();
                
                if (tipo.indexOf('prazo') > -1) {
                    // Lógica para prazo
                    console.log('[GIGS] Processando prazo.');
                } else if (tipo.indexOf('comentario') > -1) {
                    // Lógica para comentário
                    console.log('[GIGS] Processando comentário.');
                } else if (tipo.indexOf('lembrete') > -1) {
                    // Lógica para lembrete
                    console.log('[GIGS] Processando lembrete.');
                }
                
                setTimeout(finalizarGigs, 1500);
                
            } catch (e) {
                console.error('[GIGS][ERRO] Erro na execução:', e);
                finalizarGigs();
            }
        }
        
        function finalizarGigs() {
            console.log('[GIGS] Fluxo finalizado.');
            
            // Processar vínculos
            var vinculo = config.vinculo || 'Nenhum';
            if (vinculo !== 'Nenhum') {
                var vinculosProcessados = window.obterVinculosDescendentes(config.nm_botao, vinculo);
                setTimeout(function() {
                    window.monitorFim(vinculosProcessados);
                }, 1000);
            } else {
                window.monitorFim('Nenhum');
            }
        }
    };

    /**
     * Fluxo de Anexar robusto
     */
    window.fluxoAnexar = function(config) {
        console.log('[ANEXAR] Iniciando fluxo:', config);
        
        try {
            // Implementação básica
            console.log('[ANEXAR] Processando: ' + config.nm_botao);
            
            setTimeout(function() {
                var vinculo = config.vinculo || 'Nenhum';
                if (vinculo !== 'Nenhum') {
                    var vinculosProcessados = window.obterVinculosDescendentes(config.nm_botao, vinculo);
                    window.monitorFim(vinculosProcessados);
                } else {
                    window.monitorFim('Nenhum');
                }
            }, 1000);
            
        } catch (e) {
            console.error('[ANEXAR][ERRO]:', e);
            window.monitorFim('Nenhum');
        }
    };

    // ====== CONFIGURAÇÃO DE BOTÕES (baseada em botoes_maispje.json) ======

    var dados = {
        aaDespacho: [
            { nm_botao: 'Despacho Simples', tipo: 'despacho', cor: '#28a745', modelo: 'despacho_simples' },
            { nm_botao: 'Homologação', tipo: 'homologação', cor: '#17a2b8', modelo: 'homologacao' },
            { nm_botao: 'Extinção', tipo: 'extinção', cor: '#dc3545', modelo: 'extincao' }
        ],
        aaAutogigs: [
            { nm_botao: 'Prazo 15 dias', tipo: 'autogigs|prazo', cor: '#ffc107' },
            { nm_botao: 'Comentário', tipo: 'autogigs|comentario', cor: '#6c757d' },
            { nm_botao: 'Lembrete', tipo: 'autogigs|lembrete', cor: '#fd7e14' }
        ],
        aaAnexar: [
            { nm_botao: 'Anexar Documento', tipo: 'anexar', cor: '#6f42c1' }
        ],
        aaComunicacao: [
            { nm_botao: 'Intimação', tipo: 'intimação', cor: '#20c997' },
            { nm_botao: 'Mandado', tipo: 'mandado', cor: '#e83e8c' }
        ]
    };

    // ====== INTERFACE DO USUÁRIO ======    function criarInterface() {
        console.log('[UI] Iniciando criação da interface...');
        
        try {
            // Verificar se já existe
            if (document.getElementById('maisPjeBox')) {
                console.log('[UI] Interface já existe, removendo anterior...');
                document.getElementById('maisPjeBox').remove();
            }
            
            console.log('[UI] Criando container principal...');
            
            // Criar container principal
            var container = document.createElement('div');
            container.id = 'maisPjeBox';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                width: 320px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                z-index: 10000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
            `;
            
            console.log('[UI] Container criado, ID:', container.id);

            // Cabeçalho
            var header = document.createElement('div');
            header.style.cssText = `
                background: rgba(255,255,255,0.1);
                padding: 15px 20px;
                border-radius: 12px 12px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            `;

            var titulo = document.createElement('h3');
            titulo.textContent = 'PJe+ Robusto';
            titulo.style.cssText = `
                margin: 0;
                color: #fff;
                font-size: 18px;
                font-weight: 600;
                text-shadow: 0 1px 3px rgba(0,0,0,0.3);
            `;

            var btnFechar = document.createElement('button');
            btnFechar.innerHTML = '×';
            btnFechar.style.cssText = `
                background: rgba(255,255,255,0.2);
                border: none;
                color: #fff;
                font-size: 20px;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
            `;
            btnFechar.onclick = function() { container.remove(); };

            header.appendChild(titulo);
            header.appendChild(btnFechar);

            // Área de botões
            var botoesArea = document.createElement('div');
            botoesArea.style.cssText = `
                padding: 20px;
                max-height: 400px;
                overflow-y: auto;
            `;

            // Botão voltar
            var voltar = document.createElement('button');
            voltar.textContent = '← Voltar';
            voltar.style.cssText = `
                background: rgba(255,255,255,0.2);
                color: #fff;
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                margin-bottom: 15px;
                cursor: pointer;
                font-size: 14px;
                display: none;
                transition: all 0.2s;
            `;
            voltar.onclick = exibirGrupos;

            container.appendChild(header);
            container.appendChild(voltar);
            container.appendChild(botoesArea);
            document.body.appendChild(container);

            // Grupos de botões
            var grupos = [
                { nome: 'Despachos', chave: 'aaDespacho' },
                { nome: 'AutoGIGS', chave: 'aaAutogigs' },
                { nome: 'Anexar', chave: 'aaAnexar' },
                { nome: 'Comunicação', chave: 'aaComunicacao' }
            ];

            function exibirGrupos() {
                botoesArea.innerHTML = '';
                botoesArea.style.cssText = 'padding:20px;display:flex;flex-direction:column;gap:12px';
                voltar.style.display = 'none';
                
                grupos.forEach(function(grupo) {
                    var btn = document.createElement('button');
                    btn.textContent = grupo.nome;
                    btn.style.cssText = `
                        background: rgba(255,255,255,0.2);
                        color: #fff;
                        border: none;
                        border-radius: 8px;
                        padding: 15px 20px;
                        font-size: 16px;
                        font-weight: 500;
                        cursor: pointer;
                        transition: all 0.2s;
                        backdrop-filter: blur(5px);
                    `;
                    btn.onmouseover = function() { 
                        this.style.background = 'rgba(255,255,255,0.3)';
                        this.style.transform = 'translateY(-1px)';
                    };
                    btn.onmouseout = function() { 
                        this.style.background = 'rgba(255,255,255,0.2)';
                        this.style.transform = 'translateY(0)';
                    };
                    btn.onclick = function() { exibirBotoesGrupo(grupo); };
                    botoesArea.appendChild(btn);
                });
            }

            function exibirBotoesGrupo(grupo) {
                botoesArea.innerHTML = '';
                botoesArea.style.cssText = 'padding:20px;display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-start';
                voltar.style.display = 'block';
                
                var lista = dados[grupo.chave] || [];
                lista.forEach(function(btnConfig) {
                    var btn = document.createElement('button');
                    btn.textContent = btnConfig.nm_botao;
                    
                    var fontSize = btnConfig.nm_botao.length > 12 ? '12px' : '13px';
                    var padding = btnConfig.nm_botao.length > 15 ? '8px 10px' : '10px 12px';
                    
                    btn.style.cssText = `
                        background: ${btnConfig.cor};
                        color: #fff;
                        border: none;
                        border-radius: 6px;
                        padding: ${padding};
                        font-size: ${fontSize};
                        font-weight: 500;
                        cursor: pointer;
                        white-space: nowrap;
                        transition: all 0.2s;
                        flex: 0 0 auto;
                        min-width: 60px;
                        max-width: 140px;
                        text-align: center;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                    `;
                    
                    btn.onmouseover = function() { 
                        this.style.transform = 'scale(1.05)';
                        this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
                    };
                    btn.onmouseout = function() { 
                        this.style.transform = 'scale(1)';
                        this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
                    };
                    
                    btn.onclick = function() {
                        console.log('[UI] Executando:', btnConfig.nm_botao);
                        
                        // Executar função baseada no grupo
                        if (grupo.chave === 'aaDespacho') {
                            window.fluxoDespacho(btnConfig);
                        } else if (grupo.chave === 'aaAutogigs') {
                            window.fluxoGigs(btnConfig);
                        } else if (grupo.chave === 'aaAnexar') {
                            window.fluxoAnexar(btnConfig);
                        } else if (grupo.chave === 'aaComunicacao') {
                            window.fluxoComunicacao(btnConfig);
                        }
                    };
                    
                    botoesArea.appendChild(btn);
                });
            }

            exibirGrupos();

        } catch (e) {
            console.error('[UI][ERRO] Erro ao criar interface:', e);
        }
    }    // ====== INICIALIZAÇÃO ROBUSTA ======

    function inicializar() {
        console.log('[INIT] Iniciando PJe+ Robusto - readyState:', document.readyState);
        console.log('[INIT] URL atual:', window.location.href);
        
        var tentativas = 0;
        var maxTentativas = 10;
        
        function tentarCriarInterface() {
            tentativas++;
            console.log('[INIT] Tentativa', tentativas, 'de', maxTentativas);
            
            if (document.body && document.readyState !== 'loading') {
                console.log('[INIT] DOM pronto, criando interface...');
                try {
                    criarInterface();
                    console.log('[INIT] Interface criada com sucesso!');
                } catch (e) {
                    console.error('[INIT] Erro ao criar interface:', e);
                    if (tentativas < maxTentativas) {
                        setTimeout(tentarCriarInterface, 2000);
                    }
                }
            } else if (tentativas < maxTentativas) {
                console.log('[INIT] DOM não está pronto, tentando novamente em 1000ms');
                setTimeout(tentarCriarInterface, 1000);
            } else {
                console.error('[INIT] Falha ao criar interface após', maxTentativas, 'tentativas');
            }
        }
        
        // Múltiplas estratégias de inicialização
        if (document.readyState === 'loading') {
            console.log('[INIT] Aguardando DOMContentLoaded...');
            document.addEventListener('DOMContentLoaded', tentarCriarInterface);
        } else {
            console.log('[INIT] DOM já carregado, tentando imediatamente...');
            setTimeout(tentarCriarInterface, 100);
        }
        
        // Tentativa adicional após carregamento completo
        if (document.readyState !== 'complete') {
            window.addEventListener('load', function() {
                console.log('[INIT] Window load event - tentativa adicional...');
                setTimeout(tentarCriarInterface, 500);
            });
        }
        
        // Observador de mutações para detectar quando o body estiver disponível
        if (!document.body) {
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList' && document.body) {
                        console.log('[INIT] Body detectado via MutationObserver');
                        observer.disconnect();
                        setTimeout(tentarCriarInterface, 500);
                    }
                });
            });
            observer.observe(document.documentElement, { childList: true, subtree: true });
        }
    }

    inicializar();
    
    // Atalho de emergência: Ctrl+Shift+T para forçar criação da interface
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.shiftKey && e.key === 'T') {
            console.log('[EMERGENCIA] Atalho Ctrl+Shift+T pressionado - forçando criação da interface');
            e.preventDefault();
            
            // Remove qualquer instância anterior
            var old = document.getElementById('maisPjeBox');
            if (old) {
                old.remove();
                console.log('[EMERGENCIA] Interface anterior removida');
            }
            
            // Força criação
            setTimeout(function() {
                try {
                    criarInterface();
                    console.log('[EMERGENCIA] Interface criada via atalho!');
                } catch (e) {
                    console.error('[EMERGENCIA] Erro ao criar interface via atalho:', e);
                }
            }, 100);
        }
    });

})();
