"""Fabricas de driver Playwright — IMPLEMENTAÇÃO INTERNA DO SHIM.

Este módulo é a implementação real do backend Playwright quando pw.py está
ativo. Ele NÃO deve ser importado diretamente de fora do pacote pjeplay.

Com o shim ativo (pjeplay.iniciar()), qualquer chamada a
`Fix.core.criar_driver_PC` já retorna um PWDriver transparentemente.
Portanto, código de negócio deve sempre importar de Fix.core ou
Fix.driver_factory — nunca daqui.

As preferencias replicam `_montar_options_pc`, `criar_driver_sisb_pc` e
`criar_driver_sisb_vt` do projeto Selenium. Nao ha geckodriver: o Playwright
usa o Firefox proprio (`playwright install firefox`).
"""
import logging
import os

from playwright.sync_api import sync_playwright
from .driver import PWDriver

logger = logging.getLogger("pjeplay")

_pw_instancia = None  # singleton: sync_playwright nao e reentrante

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS = os.path.join(RAIZ, "downloads")

UA_PJE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) "
          "Gecko/20100101 Firefox/91.0")

TIPOS_DOWNLOAD_DIRETO = (
    "application/pdf,application/octet-stream,application/zip,"
    "application/msword,"
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

# Espelha prefs_anti_automacao + prefs_pc_base + prefs_anti_throttling.
PREFS_BASE = {
    "dom.webdriver.enabled": False,
    "useAutomationExtension": False,
    "general.useragent.override": UA_PJE,
    "dom.webnotifications.enabled": False,
    "media.volume_scale": "0.0",
    "dom.min_background_timeout_value": 0,
    "dom.timeout.throttling_delay": 0,
    "dom.timeout.budget_throttling_max_delay": 0,
    "page.load.animation.disabled": True,
    "dom.disable_window_move_resize": False,
}

PREFS_CACHE_LIGADO = {
    "browser.cache.disk.enable": True,
    "browser.cache.memory.enable": True,
    "browser.cache.offline.enable": True,
    "network.http.use-cache": True,
}

# Espelha o bloco anti-cache/telemetria dos drivers SISBAJUD.
PREFS_SISB = {
    "browser.startup.homepage": "about:blank",
    "startup.homepage_welcome_url": "about:blank",
    "startup.homepage_welcome_url.additional": "about:blank",
    "browser.startup.page": 0,
    "browser.cache.disk.enable": False,
    "browser.cache.memory.enable": False,
    "browser.cache.offline.enable": False,
    "network.http.use-cache": False,
    "browser.safebrowsing.enabled": False,
    "browser.safebrowsing.malware.enabled": False,
    "datareporting.healthreport.uploadEnabled": False,
    "datareporting.policy.dataSubmissionEnabled": False,
    "toolkit.telemetry.enabled": False,
}

PREFS_DOWNLOAD = {
    "browser.download.folderList": 2,
    "browser.download.manager.showWhenStarting": False,
    "browser.download.dir": DOWNLOADS,
    "browser.helperApps.neverAsk.saveToDisk": TIPOS_DOWNLOAD_DIRETO,
    "pdfjs.disabled": True,
}

# Ganho de velocidade opcional: o PJe nao depende de imagens/fontes para
# nenhum fluxo automatizado, e elas dominam o trafego das telas de timeline.
RECURSOS_DESCARTAVEIS = ("image", "font", "media")


def _bloquear_recursos(context):
    context.route(
        "**/*",
        lambda rota: rota.abort()
        if rota.request.resource_type in RECURSOS_DESCARTAVEIS
        else rota.continue_(),
    )


def criar_driver(headless=False, perfil=None, prefs_extra=None, cache=True,
                 bloquear_midia=False, viewport=(1920, 1080),
                 espera_navegacao="domcontentloaded", implicito=10):
    """Cria um PWDriver Firefox. Base de todas as fabricas nomeadas.

    perfil: diretorio de perfil persistente (sessao/certificados do PJe).
    bloquear_midia: aborta imagens/fontes/midia — mais rapido, sem efeito
    sobre os fluxos automatizados.
    """
    global _pw_instancia

    prefs = dict(PREFS_BASE)
    prefs.update(PREFS_CACHE_LIGADO if cache else {})
    prefs.update(PREFS_DOWNLOAD)
    prefs.update(prefs_extra or {})

    os.makedirs(DOWNLOADS, exist_ok=True)

    # sync_playwright nao e reentrante: falha se chamado com outro driver
    # ativo (ex: PJe + SISB). Reusa a instancia existente.
    if _pw_instancia is None:
        _pw_instancia = sync_playwright().start()
    pw = _pw_instancia
    largura, altura = viewport

    try:
        if perfil:
            context = pw.firefox.launch_persistent_context(
                perfil,
                headless=headless,
                firefox_user_prefs=prefs,
                downloads_path=DOWNLOADS,
                accept_downloads=True,
                viewport={"width": largura, "height": altura},
                user_agent=UA_PJE,
            )
            browser = context.browser
            pagina = context.pages[0] if context.pages else context.new_page()
        else:
            browser = pw.firefox.launch(
                headless=headless,
                firefox_user_prefs=prefs,
                downloads_path=DOWNLOADS,
            )
            context = browser.new_context(
                viewport={"width": largura, "height": altura},
                user_agent=UA_PJE,
                accept_downloads=True,
            )
            pagina = context.new_page()
    except Exception as e:
        logger.error("criar_driver: falha ao iniciar Firefox Playwright: %s", e)
        return None

    if bloquear_midia:
        _bloquear_recursos(context)

    driver = PWDriver(pw, browser, context, pagina, headless=headless,
                      espera_navegacao=espera_navegacao)
    driver.implicitly_wait(implicito)
    from .api_resiliencia import registrar_driver
    registrar_driver(driver)
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# -- fabricas com os nomes usados pelo shim (NAO importar de fora de pjeplay) --

def criar_driver_PC(headless=False, **kwargs):
    driver = criar_driver(headless=headless, **kwargs)
    if driver:
        logger.info("driver criado: PC (playwright)")
    return driver


def criar_driver_VT(headless=False, **kwargs):
    driver = criar_driver(headless=headless, **kwargs)
    if driver:
        logger.info("driver criado: VT (playwright)")
    return driver


def criar_driver_notebook(headless=False, **kwargs):
    driver = criar_driver(headless=headless, **kwargs)
    if driver:
        logger.info("driver criado: NOTEBOOK (playwright)")
    return driver


def criar_driver_sisb_pc(headless=False, **kwargs):
    kwargs.setdefault("prefs_extra", PREFS_SISB)
    kwargs.setdefault("cache", False)
    driver = criar_driver(headless=headless, **kwargs)
    if driver:
        logger.info("driver criado: SISB PC (playwright)")
    return driver


def criar_driver_sisb_vt(headless=False, **kwargs):
    kwargs.setdefault("prefs_extra", PREFS_SISB)
    kwargs.setdefault("cache", False)
    driver = criar_driver(headless=headless, **kwargs)
    if driver:
        logger.info("driver criado: SISB VT (playwright)")
    return driver


criar_driver_pc = criar_driver_PC
criar_driver_vt = criar_driver_VT
driver_pc = criar_driver_PC


def finalizar_driver(driver, log=True):
    """Encerra o driver de forma segura (equivale a Fix.core.finalizar_driver)."""
    global _pw_instancia
    if driver is None:
        return True
    try:
        driver.quit()
        if _pw_instancia is not None:
            _pw_instancia.stop()
            _pw_instancia = None
        if log:
            logger.info("driver finalizado")
        return True
    except Exception as e:
        logger.warning("finalizar_driver: %s", e)
        return False
