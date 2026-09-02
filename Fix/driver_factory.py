# -*- coding: utf-8 -*-
"""Fix.driver_factory — Fábricas de driver Selenium para o PJePlus.

Extraído de Fix/core.py (SEÇÃO 7) para isolar a infraestrutura de browser
do código de negócio. Todo o restante do projeto importa daqui, *ou* de
Fix.core (que re-exporta tudo abaixo por compatibilidade).

Quando pw.py está ativo, pjeplay.compat substitui selenium.* pelo backend
Playwright antes de qualquer import — então criar_driver_PC() aqui já
entrega um PWDriver transparentemente, sem nenhuma mudança neste módulo.

Referência canônica de criação de driver: este arquivo.
O Play/pjeplay/launcher.py é implementação interna do shim — não importar
de fora de pjeplay.
"""

import os

from selenium import webdriver
from .log import logger
from Fix import espera

# ====================================================================
# CONSTANTES DE CAMINHOS
# ====================================================================

# GECKODRIVER_PATH
GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), 'geckodriver.exe')

if not os.path.exists(GECKODRIVER_PATH):
    logger.warning(f'AVISO: Geckodriver não encontrado em {GECKODRIVER_PATH}')
else:
    logger.info(f'Geckodriver encontrado: {GECKODRIVER_PATH}')

# Caminhos conhecidos do binario Firefox usado por PC/SISB_PC.
FIREFOX_BINARY_PADRAO = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
FIREFOX_BINARY_PADRAO_ALT = r"C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe"

# Perfis SISBAJUD
SISB_PROFILE_PC = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'
SISB_PROFILE_NOTEBOOK = r'C:\Users\Silas\AppData\Local\Mozilla\Firefox\Profiles\arrn673i.Sisb'


# ====================================================================
# HELPERS INTERNOS
# ====================================================================

def _aplicar_preferencias(options, preferencias):
    """Aplica preferencias no Firefox mantendo a ordem declarada."""
    for chave, valor in preferencias:
        options.set_preference(chave, valor)


def _configurar_driver_pos_criacao(driver, headless=False):
    """Padroniza passos pos-criacao do driver Firefox."""
    driver.implicitly_wait(10)
    if not headless:
        driver.maximize_window()
    else:
        driver.set_window_size(1920, 1080)
        driver._headless = True
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")


def _criar_driver_firefox(options, headless=False):
    """Cria instancia Firefox com service padrao do projeto."""
    from selenium.webdriver.firefox.service import Service
    
    # Guarda defensiva: detecta se o shim pjeplay foi inicializado corretamente.
    # Se Options nao tem 'capabilities', e a forma esperada do pjeplay.compat,
    # entao Selenium real foi carregado antes de pjeplay.iniciar() — estado misto.
    if hasattr(options.__class__, 'capabilities') and not hasattr(options, 'capabilities'):
        logger.error(
            "ERRO em _criar_driver_firefox: Estado misto detectado — "
            "Selenium real importado antes de pjeplay.iniciar(). "
            "Ensure pjeplay.iniciar() runs BEFORE any Fix/* imports."
        )
        return None
    
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    _configurar_driver_pos_criacao(driver, headless=headless)
    return driver


def _resolver_binario_firefox_padrao():
    """
    Resolve o binario Firefox valido entre os caminhos conhecidos.
    Causa raiz do InvalidArgumentException ("binary is not a Firefox
    executable"): _montar_options_pc/criar_driver_sisb_pc fixavam
    FIREFOX_BINARY_PADRAO sem checar existencia (diferente de criar_driver_VT,
    que ja faz fallback). Se o caminho mudar/nao existir na maquina, o
    geckodriver falha na largada. Aqui testamos os caminhos conhecidos antes
    de configurar options.binary_location.
    """
    for caminho in (FIREFOX_BINARY_PADRAO, FIREFOX_BINARY_PADRAO_ALT):
        if os.path.exists(caminho):
            return caminho
    logger.error(
        "Nenhum binario Firefox encontrado nos caminhos conhecidos: %s | %s",
        FIREFOX_BINARY_PADRAO, FIREFOX_BINARY_PADRAO_ALT,
    )
    return None


def _montar_options_pc(headless=False):
    """Monta options para driver PC."""
    from selenium.webdriver.firefox.options import Options
    options = Options()

    if headless:
        options.add_argument('-headless')

    prefs_anti_automacao = [
        ("dom.webdriver.enabled", False),
        ('useAutomationExtension', False),
    ]
    prefs_pc_base = [
        ("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"),
        ("browser.cache.disk.enable", True),
        ("browser.cache.memory.enable", True),
        ("browser.cache.offline.enable", True),
        ("network.http.use-cache", True),
        ("dom.webnotifications.enabled", False),
        ("media.volume_scale", "0.0"),
    ]
    prefs_download_headless = [
        ("browser.download.folderList", 2),
        ("browser.download.manager.showWhenStarting", False),
        ("browser.download.dir", os.path.join(os.path.dirname(__file__), "..", "downloads")),
        (
            "browser.helperApps.neverAsk.saveToDisk",
            "application/pdf,application/octet-stream,application/zip,"
            "application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("pdfjs.disabled", True),
    ]
    prefs_anti_throttling = [
        ("dom.min_background_timeout_value", 0),
        ("dom.timeout.throttling_delay", 0),
        ("dom.timeout.budget_throttling_max_delay", 0),
        ("page.load.animation.disabled", True),
        ("dom.disable_window_move_resize", False),
    ]

    _aplicar_preferencias(options, prefs_anti_automacao)
    _aplicar_preferencias(options, prefs_pc_base)
    if headless:
        _aplicar_preferencias(options, prefs_download_headless)
    _aplicar_preferencias(options, prefs_anti_throttling)

    binario = _resolver_binario_firefox_padrao()
    if binario:
        options.binary_location = binario
    return options


def _montar_options_vt(
    headless=False,
    firefox_bin=None,
    usar_perfil_vt=False,
    vt_profile_pje=None,
    vt_profile_pje_alt=None,
    modo_fallback=False,
):
    """Monta options VT (normal ou fallback) sem duplicar blocos de preferencias."""
    from selenium.webdriver.firefox.options import Options
    options = Options()

    if headless:
        options.add_argument('-headless')
        if not modo_fallback:
            options.add_argument('--width=1920')
            options.add_argument('--height=1200')

    options.add_argument('-no-remote')
    options.add_argument('-new-instance')

    if firefox_bin:
        options.binary_location = firefox_bin

    if usar_perfil_vt and not modo_fallback:
        if vt_profile_pje and os.path.exists(vt_profile_pje):
            options.profile = vt_profile_pje
            logger.debug("[DRIVER_VT] Usando perfil: %s", vt_profile_pje)
        elif vt_profile_pje_alt and os.path.exists(vt_profile_pje_alt):
            options.profile = vt_profile_pje_alt
            logger.debug("[DRIVER_VT] Usando perfil alternativo: %s", vt_profile_pje_alt)

    prefs_anti_automacao = [
        ("dom.webdriver.enabled", False),
        ('useAutomationExtension', False),
    ]
    prefs_extensoes = [
        ("extensions.update.enabled", False),
        ("extensions.update.autoUpdateDefault", False),
        ("xpinstall.enabled", False),
    ]
    prefs_performance_base = [
        ("browser.sessionstore.max_tabs_undo", 0),
        ("browser.sessionstore.max_windows_undo", 0),
        ("browser.cache.disk.enable", False),
        ("browser.cache.memory.enable", False),
        ("browser.shell.checkDefaultBrowser", False),
        ("browser.safebrowsing.malware.enabled", False),
        ("browser.safebrowsing.phishing.enabled", False),
        ("browser.safebrowsing.downloads.enabled", False),
    ]
    prefs_anti_throttling = [
        ("dom.min_background_timeout_value", 0),
        ("dom.timeout.throttling_delay", 0),
        ("dom.timeout.budget_throttling_max_delay", 0),
    ]

    _aplicar_preferencias(options, prefs_anti_automacao)
    _aplicar_preferencias(options, prefs_extensoes)
    _aplicar_preferencias(options, prefs_performance_base)
    _aplicar_preferencias(options, prefs_anti_throttling)

    if modo_fallback:
        prefs_fallback = [
            ("browser.startup.homepage", "about:blank"),
            ("startup.homepage_welcome_url", "about:blank"),
            ("startup.homepage_welcome_url.additional", "about:blank"),
            ("browser.startup.firstrunSkipsHomepage", True),
            ("browser.startup.page", 0),
            ("browser.tabs.drawInTitlebar", True),
            ("browser.privatebrowsing.autostart", False),
            ("toolkit.cosmeticAnimations.enabled", False),
            ("alerts.useSystemBackend", False),
            ("datareporting.healthreport.uploadEnabled", False),
            ("datareporting.policy.dataSubmissionEnabled", False),
            ("toolkit.telemetry.enabled", False),
            ("toolkit.startup.max_pinned_tabs", 0),
            ("dom.disable_beforeunload", True),
            ("browser.sessionstore.resuming_notification.delayed", False),
        ]
        _aplicar_preferencias(options, prefs_fallback)
    else:
        if headless:
            prefs_headless = [
                ("browser.cache.disk.enable", True),
                ("browser.cache.memory.enable", True),
                ("ui.prefersReducedMotion", 1),
                ("browser.tabs.animate", False),
                ("toolkit.cosmeticAnimations.enabled", False),
            ]
        else:
            prefs_headless = [
                ("browser.cache.disk.enable", False),
                ("browser.cache.memory.enable", False),
            ]

        prefs_performance_geral = [
            ("browser.sessionstore.max_tabs_undo", 0),
            ("browser.sessionstore.max_windows_undo", 0),
            ("browser.shell.checkDefaultBrowser", False),
            ("browser.safebrowsing.malware.enabled", False),
            ("browser.safebrowsing.phishing.enabled", False),
            ("browser.safebrowsing.downloads.enabled", False),
            ("browser.startup.homepage", "about:blank"),
            ("startup.homepage_welcome_url", "about:blank"),
            ("browser.startup.page", 0),
            ("datareporting.healthreport.uploadEnabled", False),
            ("datareporting.policy.dataSubmissionEnabled", False),
            ("toolkit.telemetry.enabled", False),
        ]

        _aplicar_preferencias(options, prefs_headless)
        _aplicar_preferencias(options, prefs_performance_geral)

    return options


# ====================================================================
# com_retry — utilitário de retry (usado pelas fábricas)
# ====================================================================

def com_retry(func, max_tentativas=3, backoff_base=2, log=False, *args, **kwargs):
    """
    Executa função com retry e backoff exponencial.
    Padrão repetitivo consolidado: for tentativa + try/except + sleep.

    Args:
        func: Função a executar
        max_tentativas: Número máximo de tentativas
        backoff_base: Base para cálculo exponencial (2^tentativa)
        log: Ativa logging
        *args, **kwargs: Argumentos para a função

    Returns:
        Resultado da função se sucesso, None se todas tentativas falharam
    """
    import time

    for tentativa in range(max_tentativas):
        try:
            resultado = func(*args, **kwargs)
            if resultado or resultado == 0:  # Permite 0 como resultado válido
                if log:
                    logger.debug("com_retry: sucesso na tentativa %d", tentativa + 1)
                return resultado
        except Exception as e:
            if log:
                logger.warning("com_retry tentativa %d/%d: %s", tentativa + 1, max_tentativas, e)

            if tentativa < max_tentativas - 1:
                delay = backoff_base ** tentativa
                if log:
                    logger.debug("com_retry: aguardando %.1fs antes da próxima tentativa", delay)
                time.sleep(delay)

    if log:
        logger.error("com_retry: todas as %d tentativas falharam", max_tentativas)
    return None


# ====================================================================
# FÁBRICAS PÚBLICAS — única referência canônica de criação de driver
# ====================================================================

def criar_driver_PC(headless=False):
    """
    Cria driver Firefox para PC (padrao).
    Firefox Developer Edition com configuracoes otimizadas.
    """
    try:
        options = _montar_options_pc(headless=headless)
        # WebDriverException "Process unexpectedly closed with status 0" e
        # transiente (AV/handshake do processo Firefox recem-lancado) e some
        # numa nova tentativa; com_retry ja e o padrao de retry do projeto.
        driver = com_retry(
            _criar_driver_firefox, max_tentativas=2, backoff_base=2, log=True,
            options=options, headless=headless,
        )
        if driver is None:
            logger.error("ERRO em criar_driver_PC: driver nao criado apos retries")
            return None
        logger.info("driver criado: PC")
        return driver
    except Exception as e:
        logger.error("ERRO em criar_driver_PC: %s: %s", type(e).__name__, e)
        return None


def criar_driver_VT(headless=False):
    """
    Cria driver Firefox para VT (maquina especifica).
    Usa perfis e configuracoes VT com otimizacoes de startup.
    """
    FIREFOX_BINARY = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
    FIREFOX_BINARY_ALT = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    VT_PROFILE_PJE = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
    VT_PROFILE_PJE_ALT = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'

    if not os.path.exists(GECKODRIVER_PATH):
        logger.error("ERRO em criar_driver_VT: geckodriver nao encontrado em %s", GECKODRIVER_PATH)
        return None

    firefox_bin = None
    for bin_path in [FIREFOX_BINARY, FIREFOX_BINARY_ALT]:
        if os.path.exists(bin_path):
            firefox_bin = bin_path
            break
    if not firefox_bin:
        logger.error("ERRO em criar_driver_VT: nenhum binario Firefox encontrado")
        return None

    logger.info("criar_driver_VT: usando binario: %s", firefox_bin)

    try:
        USAR_PERFIL_VT = False
        options = _montar_options_vt(
            headless=headless,
            firefox_bin=firefox_bin,
            usar_perfil_vt=USAR_PERFIL_VT,
            vt_profile_pje=VT_PROFILE_PJE,
            vt_profile_pje_alt=VT_PROFILE_PJE_ALT,
            modo_fallback=False,
        )

        logger.debug("criar_driver_VT: criando instancia Firefox...")
        import time as _t
        t0 = _t.time()
        driver = _criar_driver_firefox(options, headless=headless)
        logger.debug("criar_driver_VT: configurando driver... (launch %.1fs)", _t.time() - t0)
        logger.info("driver criado: VT")
        return driver

    except Exception as e:
        logger.warning("criar_driver_VT: erro com configuracoes otimizadas: %s - tentando fallback...", e)

        try:
            options = _montar_options_vt(
                headless=headless,
                firefox_bin=firefox_bin,
                usar_perfil_vt=False,
                vt_profile_pje=VT_PROFILE_PJE,
                vt_profile_pje_alt=VT_PROFILE_PJE_ALT,
                modo_fallback=True,
            )

            import time as _t
            t0 = _t.time()
            driver = _criar_driver_firefox(options, headless=headless)
            logger.debug("criar_driver_VT: configurando driver... (fallback launch %.1fs)", _t.time() - t0)
            logger.info("driver criado: VT (fallback)")
            return driver

        except Exception as e2:
            logger.error("ERRO em criar_driver_VT: %s: %s", type(e2).__name__, e2)
            return None


# Aliases lowercase para compatibilidade com x.py e f.py
criar_driver_pc = criar_driver_PC
criar_driver_vt = criar_driver_VT


def criar_driver_notebook(headless=False):
    """Driver Notebook - Firefox Developer Edition"""
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service

    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'

    USE_USER_PROFILE_NOTEBOOK = False
    if USE_USER_PROFILE_NOTEBOOK:
        options.profile = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'

    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    logger.info("driver criado: NOTEBOOK")
    return driver


def criar_driver_sisb_pc(headless=False):
    """Driver SISBAJUD - PC (Firefox Developer Edition com configurações robustas)"""
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

    options = Options()
    if headless:
        options.add_argument('--headless')

    binario = _resolver_binario_firefox_padrao()
    if binario:
        options.binary_location = binario

    options.set_preference("browser.startup.homepage", "about:blank")
    options.set_preference("startup.homepage_welcome_url", "about:blank")
    options.set_preference("startup.homepage_welcome_url.additional", "about:blank")
    options.set_preference("browser.startup.page", 0)
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.http.use-cache", False)
    options.set_preference("browser.safebrowsing.enabled", False)
    options.set_preference("browser.safebrowsing.malware.enabled", False)
    options.set_preference("datareporting.healthreport.uploadEnabled", False)
    options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
    options.set_preference("toolkit.telemetry.enabled", False)

    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    try:
        if os.path.exists(SISB_PROFILE_PC):
            profile = FirefoxProfile(SISB_PROFILE_PC)
            options.profile = profile
            logger.debug("[DRIVER_SISB_PC] Usando perfil: %s", SISB_PROFILE_PC)
        else:
            logger.warning("[DRIVER_SISB_PC] Perfil nao encontrado: %s, usando perfil temporario", SISB_PROFILE_PC)
    except Exception as e:
        logger.warning("[DRIVER_SISB_PC] Erro ao carregar perfil: %s, usando perfil temporario", e)

    service = Service(executable_path=GECKODRIVER_PATH)

    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)
        logger.info("driver criado: SISB_PC")
        return driver
    except Exception as e:
        logger.warning("criar_driver_sisb_pc: erro ao criar driver: %s - tentando fallback...", e)
        try:
            options_fallback = Options()
            if headless:
                options_fallback.add_argument('--headless')
            if binario:
                options_fallback.binary_location = binario
            driver = webdriver.Firefox(service=service, options=options_fallback)
            driver.implicitly_wait(10)
            logger.info("driver criado: SISB_PC (fallback)")
            return driver
        except Exception as e2:
            logger.error("ERRO em criar_driver_sisb_pc: %s: %s", type(e2).__name__, e2)
            return None


def criar_driver_sisb_vt(headless=False):
    """
    Driver SISBAJUD - VT (temporario, sem perfil fixo).
    Segue a logica do criar_driver_PC: auto-detecta o binario Firefox
    entre os caminhos conhecidos e nao exige perfil especifico da maquina.
    """
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service

    FIREFOX_BINARY = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
    FIREFOX_BINARY_ALT = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'

    options = Options()
    if headless:
        options.add_argument('--headless')

    firefox_bin = None
    for bin_path in [FIREFOX_BINARY, FIREFOX_BINARY_ALT]:
        if os.path.exists(bin_path):
            firefox_bin = bin_path
            break
    if firefox_bin:
        options.binary_location = firefox_bin
        logger.debug("[DRIVER_SISB_VT] Usando binario: %s", firefox_bin)
    else:
        logger.warning("[DRIVER_SISB_VT] Nenhum binario Firefox conhecido encontrado, usando padrao do sistema")

    # Perfil sempre temporario (novo a cada execucao) - nao depende de maquina especifica
    options.set_preference("browser.startup.homepage", "about:blank")
    options.set_preference("startup.homepage_welcome_url", "about:blank")
    options.set_preference("startup.homepage_welcome_url.additional", "about:blank")
    options.set_preference("browser.startup.page", 0)
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.http.use-cache", False)
    options.set_preference("browser.safebrowsing.enabled", False)
    options.set_preference("browser.safebrowsing.malware.enabled", False)
    options.set_preference("datareporting.healthreport.uploadEnabled", False)
    options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
    options.set_preference("toolkit.telemetry.enabled", False)

    # ===== ANTI-THROTTLING: Evitar lentidao quando janela esta em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    service = Service(executable_path=GECKODRIVER_PATH)

    try:
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)
        logger.info("driver criado: SISB_VT (temporario)")
        return driver
    except Exception as e:
        logger.error("ERRO em criar_driver_sisb_vt: %s: %s", type(e).__name__, e)
        return None


def criar_driver_sisb_notebook(headless=False):
    """Driver SISBAJUD - Notebook"""
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service

    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
    options.profile = SISB_PROFILE_NOTEBOOK

    # ===== ANTI-THROTTLING: Evitar lentidão quando janela está em background =====
    options.set_preference("dom.min_background_timeout_value", 0)
    options.set_preference("dom.timeout.throttling_delay", 0)
    options.set_preference("dom.timeout.budget_throttling_max_delay", 0)

    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(options=options, service=service)
    driver.implicitly_wait(10)
    logger.info("driver criado: SISB_NOTEBOOK")
    return driver


def finalizar_driver(driver, log=True):
    """Finaliza o driver de forma segura, aguardando operações pendentes."""
    try:
        # Fecha todas as janelas exceto a principal
        if len(driver.window_handles) > 1:
            janela_principal = driver.window_handles[0]
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(janela_principal)

        # Pequeno delay para operações pendentes (mantido pois não há condição
        # observável para esperar — operações internas do Selenium/Geckodriver)
        espera.assentar(driver, 0.5)

        # Fecha o driver
        driver.quit()

        if log:
            logger.debug("[DRIVER] Driver finalizado com sucesso")
        return True
    except Exception as e:
        if log:
            logger.warning("[DRIVER] Erro ao finalizar driver: %s", e)
        return False
