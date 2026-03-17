"""
SISB Utils - Funções auxiliares consolidadas para SISBAJUD
Refatoração do s.py seguindo padrões do projeto PjePlus
"""

import time
import re
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# Constantes consolidadas
SISBAJUD_URLS = {
    'base': 'https://sisbajud.cnj.jus.br',
    'login': 'https://sisbajud.cnj.jus.br/login',
    'teimosinha': 'https://sisbajud.cnj.jus.br/teimosinha',
    'minuta_cadastrar': 'https://sisbajud.cnj.jus.br/sisbajudweb/pages/minuta/cadastrar'
}

TIMEOUTS = {
    'elemento_padrao': 10,
    'elemento_rapido': 5,
    'elemento_lento': 20,
    'pagina_carregar': 30,
    'script_executar': 15
}

SELECTORS = {
    'input_juiz': 'input[placeholder*="Juiz"]',
    'input_processo': 'input[placeholder="Número do Processo"]',
    'input_cpf': 'input[placeholder*="CPF"]',
    'input_nome_autor': 'input[placeholder="Nome do autor/exequente da ação"]',
    'botao_consultar': 'button.mat-fab.mat-primary',
    'botao_salvar': 'button.mat-fab.mat-primary mat-icon.fa-save',
    'tabela_ordens': 'table.mat-table',
    'cabecalho_tabela': 'th.cdk-column-sequencial'
}

def criar_js_otimizado() -> str:
    """
    JavaScript otimizado consolidado para todas as operações SISBAJUD.
    Substitui múltiplas funções de JavaScript espalhadas pelo código.

    Returns:
        str: Código JavaScript consolidado
    """
    return """
    // ===== JAVASCRIPT OTIMIZADO CONSOLIDADO =====

    // Configurações globais
    const CONFIG = {
        timeout: 5000,
        retryDelay: 500,
        maxRetries: 3
    };

    // Sistema de observação de mutações para elementos dinâmicos
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
                    reject(new Error(`Elemento não encontrado: ${selector}`));
                }, timeout);
            });
        }

        disconnectAll() {
            this.observers.forEach(observer => observer.disconnect());
            this.observers.clear();
        }
    }

    const elementObserver = new ElementObserver();

    // Funções utilitárias consolidadas
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
                    resolve({ sucesso: false, erro: 'Campo não encontrado' });
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
                    resolve({ sucesso: false, erro: 'Botão não encontrado' });
                    return;
                }

                const sucesso = safeClick(elemento);
                resolve({ sucesso });
            } catch (e) {
                resolve({ sucesso: false, erro: e.message });
            }
        });
    }

    // Sistema de logging consolidado
    const Logger = {
        log: [],
        add: function(msg) { this.log.push(msg); },
        clear: function() { this.log = []; },
        get: function() { return this.log; }
    };

    // Exportar funções globais
    window.SISBAJUD = {
        esperarElemento,
        esperarElementos,
        triggerEvent,
        safeClick,
        preencherCampo,
        clicarBotao,
        Logger,
        CONFIG
    };
    """

def safe_click(driver, elemento, descricao="elemento", timeout=10):
    """
    Clique seguro com fallback para JavaScript.
    Consolidado de múltiplas implementações similares no código.

    Args:
        driver: WebDriver instance
        elemento: Elemento a clicar
        descricao: Descrição para logging
        timeout: Timeout para operações

    Returns:
        bool: True se conseguiu clicar
    """
    try:
        # Scroll suave para o elemento
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elemento)
        time.sleep(0.5)

        # Verificar se elemento está visível e habilitado
        if not elemento.is_displayed():
            print(f"[SISBAJUD] Elemento não visível: {descricao}")
            return False

        if not elemento.is_enabled():
            print(f"[SISBAJUD] Elemento desabilitado: {descricao}")
            return False

        # Tentar clique normal
        elemento.click()
        return True

    except Exception as e:
        try:
            # Fallback: JavaScript click
            driver.execute_script("arguments[0].click();", elemento)
            return True
        except Exception as e2:
            print(f"[SISBAJUD] Falha no clique seguro ({descricao}): {e} / {e2}")
            return False

def simulate_human_movement(driver, elemento):
    """
    Simula movimento humano antes de interagir com elemento.
    Previne detecção de automação.

    Args:
        driver: WebDriver instance
        elemento: Elemento alvo
    """
    try:
        # Pequena pausa antes do movimento
        time.sleep(0.2)

        # Scroll para o elemento
        driver.execute_script("""
            arguments[0].scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                inline: 'center'
            });
        """, elemento)

        # Pausa para simular leitura
        time.sleep(0.3)

    except Exception as e:
        print(f"[SISBAJUD] Erro no movimento humano: {e}")

def aguardar_elemento(driver, seletor, timeout=TIMEOUTS['elemento_padrao']):
    """
    Aguardar elemento com timeout padronizado.
    Consolidado de múltiplas implementações WebDriverWait.

    Args:
        driver: WebDriver instance
        seletor: Seletor CSS
        timeout: Timeout em segundos

    Returns:
        WebElement or None: Elemento encontrado ou None
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
        )
    except TimeoutException:
        print(f"[SISBAJUD] Timeout aguardando elemento: {seletor}")
        return None
    except Exception as e:
        print(f"[SISBAJUD] Erro aguardando elemento {seletor}: {e}")
        return None

def aguardar_e_clicar(driver, seletor, timeout=TIMEOUTS['elemento_padrao']):
    """
    Aguardar elemento e clicar com tratamento de erros consolidado.

    Args:
        driver: WebDriver instance
        seletor: Seletor CSS
        timeout: Timeout em segundos

    Returns:
        bool: True se conseguiu clicar
    """
    elemento = aguardar_elemento(driver, seletor, timeout)
    if not elemento:
        return False

    return safe_click(driver, elemento, f"seletor: {seletor}")

def escolher_opcao_sisbajud(driver, seletor_input, valor, timeout=TIMEOUTS['elemento_padrao']):
    """
    Escolher opção em dropdown do SISBAJUD.
    Consolidado de múltiplas implementações similares.

    Args:
        driver: WebDriver instance
        seletor_input: Seletor do campo input
        valor: Valor a selecionar
        timeout: Timeout em segundos

    Returns:
        bool: True se conseguiu selecionar
    """
    try:
        # Aguardar campo input
        input_element = aguardar_elemento(driver, seletor_input, timeout)
        if not input_element:
            return False

        # Preencher valor
        input_element.clear()
        input_element.send_keys(valor)
        time.sleep(1)  # Aguardar dropdown aparecer

        # Aguardar e clicar na opção
        opcao_seletor = f'span.mat-option-text:contains("{valor}")'
        return aguardar_e_clicar(driver, opcao_seletor, 5)

    except Exception as e:
        print(f"[SISBAJUD] Erro ao escolher opção {valor}: {e}")
        return False

def extrair_protocolo(driver):
    """
    Extrair protocolo da URL atual.
    Consolidado de múltiplas implementações similares.

    Args:
        driver: WebDriver instance

    Returns:
        str or None: Protocolo extraído ou None
    """
    try:
        url = driver.current_url
        match = re.search(r'/(\d{10,})/', url)
        return match.group(1) if match else None
    except Exception as e:
        print(f"[SISBAJUD] Erro ao extrair protocolo: {e}")
        return None

def validar_numero_processo(numero):
    """
    Validar formato do número do processo.

    Args:
        numero: Número do processo (string ou list)

    Returns:
        str or None: Número validado ou None
    """
    if isinstance(numero, list) and len(numero) > 0:
        numero = numero[0]
    elif not isinstance(numero, str) or not numero.strip():
        return None

    numero = numero.strip()

    # Validar formato básico (números-três números.números.números.números-números)
    if not re.match(r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$', numero):
        return None

    return numero

def formatar_valor_monetario(valor_str):
    """
    Formatar valor monetário brasileiro para float.
    Consolidado de múltiplas implementações similares.

    Args:
        valor_str: String com valor (ex: "R$ 1.234,56")

    Returns:
        float: Valor formatado ou 0.0 se erro
    """
    try:
        # Remover texto e símbolos
        valor_limpo = valor_str.replace('R$', '').replace('\u00a0', '').replace('&nbsp;', '').strip()

        # Converter formato brasileiro para americano
        valor_limpo = valor_limpo.replace('.', '').replace(',', '.')

        return float(valor_limpo)
    except (ValueError, AttributeError):
        return 0.0

def calcular_data_limite(dias_atras=15):
    """
    Calcular data limite para filtros (hoje - dias_atras).

    Args:
        dias_atras: Dias para subtrair da data atual

    Returns:
        datetime: Data limite calculada
    """
    return datetime.now() - timedelta(days=dias_atras)

def criar_timestamp():
    """
    Criar timestamp formatado para logging.

    Returns:
        str: Timestamp no formato [HH:MM:SS]
    """
    return datetime.now().strftime("[%H:%M:%S]")

def log_sisbajud(mensagem, nivel="INFO"):
    """
    Logging padronizado para SISBAJUD.

    Args:
        mensagem: Mensagem a logar
        nivel: Nível do log (INFO, ERROR, WARNING, etc.)
    """
    timestamp = criar_timestamp()
    print(f"[SISBAJUD]{timestamp} [{nivel}] {mensagem}")

def registrar_erro_minuta(numero_processo, erro, contexto, continuar=False):
    """
    Registrar erro de minuta de forma padronizada.

    Args:
        numero_processo: Número do processo
        erro: Exceção ou mensagem de erro
        contexto: Contexto onde ocorreu o erro
        continuar: Se deve continuar processamento
    """
    mensagem = f"Erro em {contexto}: {str(erro)}"
    log_sisbajud(mensagem, "ERROR")

    if not continuar:
        log_sisbajud(f"Interrompendo processamento do processo {numero_processo}", "ERROR")
        raise erro

# ===== FUNÇÕES CONSOLIDADAS AVANÇADAS =====

def mutation_observer_script():
    """
    JavaScript para MutationObserver otimizado.
    Substitui polling por observação eficiente de mudanças no DOM.

    Returns:
        str: Código JavaScript do MutationObserver
    """
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

                observer.observe(document.body, {{
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: ['style', 'class']
                }});

                // Timeout fallback
                const timeoutId = setTimeout(() => {
                    observer.disconnect();
                    reject(new Error(`Elemento não encontrado: ${selector}`));
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

    // Instância global
    window.MutationObserverManager = new MutationObserverManager();
    """

def rate_limiting_manager():
    """
    Gerenciador de rate limiting para evitar detecção de automação.

    Returns:
        str: Código JavaScript para rate limiting
    """
    return """
    class RateLimiter {
        constructor() {
            this.actions = [];
            this.maxActionsPerMinute = 30;
            this.cooldownMs = 2000; // 2 segundos entre ações pesadas
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

            // Limpar ações antigas
            this.actions = this.actions.filter(time => time > oneMinuteAgo);

            if (this.actions.length >= this.maxActionsPerMinute) {
                const waitTime = 60000 - (now - this.actions[0]);
                console.log(`Rate limit atingido. Aguardando ${waitTime/1000}s...`);
                await new Promise(resolve => setTimeout(resolve, waitTime));
                return this.checkRateLimit(); // Recursão para verificar novamente
            }

            this.actions.push(now);
        }

        async executeWithRateLimit(action) {
            await this.checkRateLimit();
            await this.throttle();

            try {
                return await action();
            } catch (error) {
                console.error('Erro na ação com rate limiting:', error);
                throw error;
            }
        }
    }

    // Instância global
    window.RateLimiter = new RateLimiter();
    """

def advanced_dom_manipulator():
    """
    Manipulador avançado de DOM com estratégias anti-detecção.

    Returns:
        str: Código JavaScript para manipulação avançada de DOM
    """
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
            // Abrir dropdown
            await this.clickHuman(selectElement);

            // Aguardar opções
            await new Promise(resolve => setTimeout(resolve, 500));

            // Encontrar e clicar na opção
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

    // Instância global
    window.DOMManipulator = new DOMManipulator();
    """

def consolidated_js_framework():
    """
    Framework JavaScript consolidado com todas as funcionalidades.

    Returns:
        str: Framework JavaScript completo
    """
    return f"""
    {mutation_observer_script()}

    {rate_limiting_manager()}

    {advanced_dom_manipulator()}

    // Framework consolidado SISBAJUD
    window.SISBAJUD_Framework = {{
        init: function() {{
            console.log('SISBAJUD Framework inicializado');
            return true;
        }},

        // Método unificado para operações seguras
        executeSafe: async function(operation, options = {{}}) {{
            const config = {{
                useRateLimit: true,
                useHumanBehavior: true,
                ...options
            }};

            const action = async () => {{
                if (config.useHumanBehavior) {{
                    // Adicionar comportamento humano
                    await new Promise(resolve => setTimeout(resolve,
                        100 + Math.random() * 200));
                }
                return await operation();
            }};

            if (config.useRateLimit) {{
                return await window.RateLimiter.executeWithRateLimit(action);
            }} else {{
                return await action();
            }}
        }},

        // Cleanup
        cleanup: function() {{
            if (window.MutationObserverManager) {{
                window.MutationObserverManager.disconnectAll();
            }}
            console.log('SISBAJUD Framework limpo');
        }}
    }};

    // Inicialização automática
    window.SISBAJUD_Framework.init();
    """

def aplicar_rate_limiting(driver, acao):
    """
    Aplica rate limiting a uma ação do Selenium.

    Args:
        driver: WebDriver instance
        acao: Função a ser executada com rate limiting

    Returns:
        Resultado da ação
    """
    # Injetar rate limiter se não estiver presente
    driver.execute_script(rate_limiting_manager())

    # Executar ação com rate limiting
    script = """
    return window.RateLimiter.executeWithRateLimit(async () => {
        // Ação será definida dinamicamente
        return await arguments[0]();
    });
    """

    return driver.execute_script(script, acao)

def detectar_captcha(driver):
    """
    Detecta presença de CAPTCHA na página.

    Args:
        driver: WebDriver instance

    Returns:
        bool: True se CAPTCHA detectado
    """
    try:
        indicadores_captcha = [
            'recaptcha',
            'captcha',
            'verify human',
            'robot',
            'automated'
        ]

        page_text = driver.find_element(By.TAG_NAME, 'body').text.lower()

        for indicador in indicadores_captcha:
            if indicador in page_text:
                return True

        # Verificar elementos específicos
        captcha_selectors = [
            '.recaptcha',
            '#recaptcha',
            '[class*="captcha"]',
            '[id*="captcha"]'
        ]

        for selector in captcha_selectors:
            try:
                driver.find_element(By.CSS_SELECTOR, selector)
                return True
            except:
                continue

        return False

    except Exception:
        return False

def anti_detection_measures(driver):
    """
    Aplica medidas anti-detecção de automação.

    Args:
        driver: WebDriver instance
    """
    try:
        # Definir propriedades navigator para parecer navegador real
        driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });

        // Simular plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer' },
                { name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' }
            ],
        });

        // Simular languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['pt-BR', 'pt', 'en-US', 'en'],
        });
        """)

        # Adicionar headers HTTP simulados
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    except Exception as e:
        log_sisbajud(f"Erro ao aplicar medidas anti-detecção: {e}", "WARNING")

def smart_wait(driver, condition, timeout=TIMEOUTS['elemento_padrao'], interval=0.5):
    """
    Espera inteligente com detecção de CAPTCHA e erros.

    Args:
        driver: WebDriver instance
        condition: Função de condição
        timeout: Timeout máximo
        interval: Intervalo entre verificações

    Returns:
        WebElement or None: Elemento encontrado ou None
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # Verificar CAPTCHA
            if detectar_captcha(driver):
                log_sisbajud("CAPTCHA detectado! Aguardando intervenção manual...", "WARNING")
                time.sleep(30)  # Aguardar intervenção
                continue

            result = condition()
            if result:
                return result

        except Exception as e:
            log_sisbajud(f"Erro durante smart_wait: {e}", "WARNING")

        time.sleep(interval)

    return None