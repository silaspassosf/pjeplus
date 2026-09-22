"""
SISB Core - JavaScript helpers
"""


def criar_js_otimizado() -> str:
    """
    JavaScript otimizado consolidado para todas as operacoes SISBAJUD.
    """
    return """
    // ===== JAVASCRIPT OTIMIZADO CONSOLIDADO =====

    // Configuracoes globais
    const CONFIG = {
        timeout: 5000,
        retryDelay: 500,
        maxRetries: 3
    };

    // Sistema de observacao de mutacoes para elementos dinamicos
    class ElementObserver {
        constructor() {
            this.observers = new Map();
        }

        observe(selector, callback, timeout = CONFIG.timeout) {
            return new Promise((resolve, reject) => {
                const element = document.querySelector(selector);
                if (element) {
                    resolve(element);
                    return;
                }

                const observer = new MutationObserver((mutations) => {
                    const element = document.querySelector(selector);
                    if (element) {
                        observer.disconnect();
                        resolve(element);
                    }
                });

                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });

                setTimeout(() => {
                    observer.disconnect();
                    reject(new Error(`Elemento nao encontrado: ${selector}`));
                }, timeout);
            });
        }

        disconnectAll() {
            this.observers.forEach(observer => observer.disconnect());
            this.observers.clear();
        }
    }

    const elementObserver = new ElementObserver();

    // Funcoes utilitarias consolidadas
    function esperarElemento(seletor, timeout = CONFIG.timeout) {
        return elementObserver.observe(seletor, null, timeout);
    }

    function esperarElementos(seletor, timeout = CONFIG.timeout) {
        return new Promise((resolve) => {
            const elements = document.querySelectorAll(seletor);
            if (elements.length > 0) {
                resolve(Array.from(elements));
                return;
            }

            const observer = new MutationObserver(() => {
                const elements = document.querySelectorAll(seletor);
                if (elements.length > 0) {
                    observer.disconnect();
                    resolve(Array.from(elements));
                }
            });

            observer.observe(document.body, { childList: true, subtree: true });
            setTimeout(() => {
                observer.disconnect();
                resolve([]);
            }, timeout);
        });
    }

    async function esperarOpcoes(seletor, timeout = 3000) {
        return new Promise((resolve) => {
            const elements = document.querySelectorAll(seletor);
            if (elements.length > 0) {
                resolve(elements);
                return;
            }

            const observer = new MutationObserver(() => {
                const elements = document.querySelectorAll(seletor);
                if (elements.length > 0) {
                    observer.disconnect();
                    resolve(elements);
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            setTimeout(() => {
                observer.disconnect();
                resolve([]);
            }, timeout);
        });
    }

    function triggerEvent(elemento, tipo) {
        if ('createEvent' in document) {
            const evento = document.createEvent('HTMLEvents');
            evento.initEvent(tipo, false, true);
            elemento.dispatchEvent(evento);
        }
    }

    function safeClick(elemento) {
        try {
            elemento.scrollIntoView({ behavior: 'smooth', block: 'center' });
            elemento.click();
            return true;
        } catch (e) {
            try {
                elemento.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                return true;
            } catch (e2) {
                return false;
            }
        }
    }

    function preencherCampo(seletor, valor, timeout = CONFIG.timeout) {
        return new Promise(async (resolve) => {
            try {
                const elemento = await esperarElemento(seletor, timeout);
                if (!elemento) {
                    resolve({ sucesso: false, erro: 'Campo nao encontrado' });
                    return;
                }

                elemento.focus();
                elemento.value = '';
                elemento.value = valor;
                triggerEvent(elemento, 'input');
                triggerEvent(elemento, 'change');
                elemento.blur();

                resolve({ sucesso: true });
            } catch (e) {
                resolve({ sucesso: false, erro: e.message });
            }
        });
    }

    function clicarBotao(seletor, timeout = CONFIG.timeout) {
        return new Promise(async (resolve) => {
            try {
                const elemento = await esperarElemento(seletor, timeout);
                if (!elemento) {
                    resolve({ sucesso: false, erro: 'Botao nao encontrado' });
                    return;
                }

                const sucesso = safeClick(elemento);
                resolve({ sucesso });
            } catch (e) {
                resolve({ sucesso: false, erro: e.message });
            }
        });
    }

    const Logger = {
        log: [],
        add: function(msg) { this.log.push(msg); },
        clear: function() { this.log = []; },
        get: function() { return this.log; }
    };

    window.SISBAJUD = {
        esperarElemento,
        esperarElementos,
        esperarOpcoes,
        triggerEvent,
        safeClick,
        preencherCampo,
        clicarBotao,
        Logger,
        CONFIG
    };
    """


def mutation_observer_script():
    """JavaScript para MutationObserver otimizado."""
    return """
    class MutationObserverManager {
        constructor() {
            this.observers = new Map();
            this.timeouts = new Map();
        }

        observe(selector, callback, options = {}) {
            const config = {
                timeout: 10000,
                checkInterval: 100,
                ...options
            };

            return new Promise((resolve, reject) => {
                const element = document.querySelector(selector);
                if (element) {
                    resolve(element);
                    return;
                }

                const observer = new MutationObserver((mutations) => {
                    const element = document.querySelector(selector);
                    if (element) {
                        observer.disconnect();
                        resolve(element);
                    }
                });

                observer.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: ['style', 'class']
                });

                const timeoutId = setTimeout(() => {
                    observer.disconnect();
                    reject(new Error(`Elemento nao encontrado: ${selector}`));
                }, config.timeout);

                this.observers.set(selector, observer);
                this.timeouts.set(selector, timeoutId);
            });
        }

        disconnect(selector) {
            const observer = this.observers.get(selector);
            if (observer) {
                observer.disconnect();
                this.observers.delete(selector);
            }

            const timeoutId = this.timeouts.get(selector);
            if (timeoutId) {
                clearTimeout(timeoutId);
                this.timeouts.delete(selector);
            }
        }

        disconnectAll() {
            this.observers.forEach(observer => observer.disconnect());
            this.observers.clear();

            this.timeouts.forEach(timeoutId => clearTimeout(timeoutId));
            this.timeouts.clear();
        }
    }

    window.MutationObserverManager = new MutationObserverManager();
    """


def rate_limiting_manager():
    """Gerenciador de rate limiting para evitar deteccao de automacao."""
    return """
    class RateLimiter {
        constructor() {
            this.actions = [];
            this.maxActionsPerMinute = 30;
            this.cooldownMs = 2000;
            this.lastActionTime = 0;
        }

        async throttle() {
            const now = Date.now();
            const timeSinceLastAction = now - this.lastActionTime;

            if (timeSinceLastAction < this.cooldownMs) {
                const waitTime = this.cooldownMs - timeSinceLastAction;
                await new Promise(resolve => setTimeout(resolve, waitTime));
            }

            this.lastActionTime = Date.now();
        }

        async checkRateLimit() {
            const now = Date.now();
            const oneMinuteAgo = now - 60000;

            this.actions = this.actions.filter(time => time > oneMinuteAgo);

            if (this.actions.length >= this.maxActionsPerMinute) {
                const waitTime = 60000 - (now - this.actions[0]);
                console.log(`Rate limit atingido. Aguardando ${waitTime/1000}s...`);
                await new Promise(resolve => setTimeout(resolve, waitTime));
                return this.checkRateLimit();
            }

            this.actions.push(now);
        }

        async executeWithRateLimit(action) {
            await this.checkRateLimit();
            await this.throttle();

            try {
                return await action();
            } catch (error) {
                console.error('Erro na acao com rate limiting:', error);
                throw error;
            }
        }
    }

    window.RateLimiter = new RateLimiter();
    """


def advanced_dom_manipulator():
    """Manipulador avancado de DOM com estrategias anti-deteccao."""
    return """
    class DOMManipulator {
        constructor() {
            this.eventTypes = ['input', 'change', 'blur', 'focus'];
            this.humanDelays = {
                typing: { min: 50, max: 150 },
                clicking: { min: 100, max: 300 },
                navigation: { min: 500, max: 1500 }
            };
        }

        async typeHuman(element, text) {
            for (let i = 0; i < text.length; i++) {
                element.value += text[i];
                element.dispatchEvent(new Event('input', { bubbles: true }));

                const delay = this.humanDelays.typing.min +
                    Math.random() * (this.humanDelays.typing.max - this.humanDelays.typing.min);
                await new Promise(resolve => setTimeout(resolve, delay));
            }

            element.dispatchEvent(new Event('change', { bubbles: true }));
            element.blur();
        }

        async clickHuman(element) {
            const delay = this.humanDelays.clicking.min +
                Math.random() * (this.humanDelays.clicking.max - this.humanDelays.clicking.min);
            await new Promise(resolve => setTimeout(resolve, delay));

            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            await new Promise(resolve => setTimeout(resolve, 200));

            element.click();
        }

        async selectOption(selectElement, optionText) {
            await this.clickHuman(selectElement);
            await new Promise(resolve => setTimeout(resolve, 500));

            const options = document.querySelectorAll('mat-option[role="option"]');
            for (let option of options) {
                if (option.textContent.trim().toLowerCase().includes(optionText.toLowerCase())) {
                    await this.clickHuman(option);
                    return true;
                }
            }

            return false;
        }

        async waitForStability(element, timeout = 5000) {
            return new Promise((resolve) => {
                let lastState = element.outerHTML;
                let stableCount = 0;
                const requiredStable = 3;

                const checkStability = () => {
                    const currentState = element.outerHTML;
                    if (currentState === lastState) {
                        stableCount++;
                        if (stableCount >= requiredStable) {
                            resolve(true);
                            return;
                        }
                    } else {
                        stableCount = 0;
                        lastState = currentState;
                    }

                    setTimeout(checkStability, 200);
                };

                setTimeout(() => resolve(false), timeout);
                checkStability();
            });
        }
    }

    window.DOMManipulator = new DOMManipulator();
    """


def consolidated_js_framework():
    """Framework JavaScript consolidado com todas as funcionalidades."""
    js_parts = [
        mutation_observer_script(),
        rate_limiting_manager(),
        advanced_dom_manipulator(),
        """
        window.SISBAJUD_Framework = {
            init: function() {
                console.log('SISBAJUD Framework inicializado');
                return true;
            },

            executeSafe: async function(operation, options = {}) {
                const config = {
                    useRateLimit: true,
                    useHumanBehavior: true,
                    ...options
                };

                const action = async () => {
                    if (config.useHumanBehavior) {
                        await new Promise(resolve => setTimeout(resolve,
                            100 + Math.random() * 200));
                    }
                    return await operation();
                };

                if (config.useRateLimit) {
                    return await window.RateLimiter.executeWithRateLimit(action);
                }
                return await action();
            },

            cleanup: function() {
                if (window.MutationObserverManager) {
                    window.MutationObserverManager.disconnectAll();
                }
                console.log('SISBAJUD Framework limpo');
            }
        };

        window.SISBAJUD_Framework.init();
        """
    ]

    return "\n".join(js_parts)