(function () {
    'use strict';
    const HCALC_DEBUG = false;
    const dbg = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err = (...args) => console.error('[hcalc]', ...args);
    if (HCALC_DEBUG) dbg('Script carregado em:', window.location.href);

    if (!window.__hcalcGlobalErrorHooksInstalled) {
        window.__hcalcGlobalErrorHooksInstalled = true;
        window.addEventListener('error', (event) => {
            err('Erro global capturado:', event?.message, event?.filename, event?.lineno, event?.colno, event?.error);
        });
        window.addEventListener('unhandledrejection', (event) => {
            err('Promise rejeitada sem tratamento:', event?.reason);
        });
    }

    // ==========================================
    // ESTADO CENTRAL HCALC
    // ==========================================
    // Centraliza todas as variáveis de estado do script
    // Permite dispose() completo para evitar vazamentos de memória
    if (!window.hcalcState) {
        window.hcalcState = {
            // Cache de partes (limitado a 5 entradas)
            calcPartesCache: {},

            // Flags de execução
            prepRunning: false,

            // Resultados do prep
            prepResult: null,
            timelineData: null,

            // Dados detectados
            peritosConhecimento: [],
            partesData: null,

            // AbortController para cancelamento de operações
            abortController: null,

            // FASE 1: Dados da planilha PJe-Calc (extração PDF)
            planilhaExtracaoData: null,  // {verbas, fgts, inss, data, id, ...}
            planilhaCarregada: false,
            pdfjsLoaded: false,

            // FASE 2: Múltiplos depósitos
            depositosRecursais: [],  // [{idx, tipo, depositante, id, isPrincipal, liberacao}]
            pagamentosAntecipados: [],  // [{idx, id, tipoLib, remValor, remTitulo, devValor}]
            nextDepositoIdx: 0,
            nextPagamentoIdx: 0,

            // FASE 3: Planilhas extras para períodos diversos
            planilhasDisponiveis: [],  // [{id, label, dados}]

            // Método de limpeza completa
            dispose() {
                dbg('Executando dispose() - limpando estado hcalc');

                // Abortar operações em andamento
                if (this.abortController) {
                    this.abortController.abort();
                    this.abortController = null;
                }

                this.calcPartesCache = {};
                this.prepRunning = false;
                this.prepResult = null;
                this.timelineData = null;
                this.peritosConhecimento = [];
                this.partesData = null;
                this.planilhaExtracaoData = null;
                this.planilhaCarregada = false;
                this.planilhasDisponiveis = [];
                this.depositosRecursais = [];
                this.pagamentosAntecipados = [];
                this.nextDepositoIdx = 0;
                this.nextPagamentoIdx = 0;
                if (this._pdfWorkerUrl) {
                    URL.revokeObjectURL(this._pdfWorkerUrl);
                    this._pdfWorkerUrl = null;
                }
                dbg('Estado hcalc limpo');
            },

            // Método de reset parcial (mantém cache)
            resetPrep() {
                // Abortar prep em andamento
                if (this.abortController) {
                    this.abortController.abort();
                    this.abortController = null;
                }

                this.prepResult = null;
                this.timelineData = null;
                this.prepRunning = false;
                this.planilhaExtracaoData = null;
                this.planilhaCarregada = false;
            }
        };
    }

    // Aliases de retrocompatibilidade (apontam para hcalcState)
    // Permite que código existente continue funcionando sem modificação
    Object.defineProperty(window, 'calcPartesCache', {
        get() { return window.hcalcState.calcPartesCache; },
        set(val) { window.hcalcState.calcPartesCache = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPrepRunning', {
        get() { return window.hcalcState.prepRunning; },
        set(val) { window.hcalcState.prepRunning = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPrepResult', {
        get() { return window.hcalcState.prepResult; },
        set(val) { window.hcalcState.prepResult = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcTimelineData', {
        get() { return window.hcalcState.timelineData; },
        set(val) { window.hcalcState.timelineData = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPeritosConhecimentoDetectados', {
        get() { return window.hcalcState.peritosConhecimento; },
        set(val) { window.hcalcState.peritosConhecimento = val; },
        configurable: true
    });
    Object.defineProperty(window, 'hcalcPartesData', {
        get() { return window.hcalcState.partesData; },
        set(val) { window.hcalcState.partesData = val; },
        configurable: true
    });

    // Sequência de ordem de campos (disponível globalmente para módulos que gerenciam foco)
    if (!window.hcalcOrderSequence) {
        window.hcalcOrderSequence = [
            'val-id', 'val-data', 'val-credito', 'val-fgts',
            'val-inss-rec', 'val-inss-total', 'val-hon-autor', 'val-custas'
        ];
    }

    // ==========================================
    // MONITOR DE NAVEGAÇÃO SPA
    // ==========================================
    // Detecta mudança de URL no PJe (SPA) e limpa estado automaticamente
    // Previne vazamento de memória ao trocar de processo sem fechar overlay
    // OTIMIZAÇÃO: History API hooks ao invés de MutationObserver pesado
    let lastUrl = location.href;

    function handleSpaNavigation() {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            dbg('Navegação SPA detectada, limpando estado...');

            // Dispose completo
            if (window.hcalcState) {
                window.hcalcState.dispose();
            }

            // Ocultar overlay se estiver aberto
            const overlay = document.getElementById('homologacao-overlay');
            if (overlay) overlay.style.display = 'none';
        }
    }

    // Intercepta pushState (navegação programática Angular)
    const _pushState = history.pushState.bind(history);
    history.pushState = function (...args) {
        _pushState(...args);
        handleSpaNavigation();
    };

    // Intercepta popstate (botão voltar/avançar)
    window.addEventListener('popstate', handleSpaNavigation);
})();
