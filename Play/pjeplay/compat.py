"""Instala o backend Playwright no lugar do pacote `selenium`.

Registra modulos compativeis em `sys.modules` antes de qualquer `import Fix...`.
A partir dai todo o projeto — Fix/, atos/, PEC/, Prazo/, Mandado/, SISB/,
Peticao/, Triagem/, bianca/ — roda sobre Playwright sem uma linha editada.
E por isso que nao existe fork: as atualizacoes do projeto valem automaticamente.
"""
import logging
import sys
import types

from . import errors, launcher, waits
from .actions import ActionChains, Select
from .driver import PWDriver
from .element import PWElement
from .locators import By, Keys

logger = logging.getLogger("pjeplay")

_INSTALADO = False


class Options:
    """Coletor de preferencias no formato do FirefoxOptions do Selenium.

    Nao configura nada por si: e lido por `Firefox()` e convertido em
    parametros do Playwright.
    """

    def __init__(self):
        self._prefs = {}
        self._args = []
        self.binary_location = None
        self.profile = None
        self.headless = False

    def set_preference(self, chave, valor):
        self._prefs[chave] = valor

    def add_argument(self, arg):
        self._args.append(arg)
        if str(arg).lstrip("-").lower() == "headless":
            self.headless = True

    def add_experimental_option(self, *_a, **_kw):
        return None

    def set_capability(self, *_a, **_kw):
        return None

    @property
    def preferences(self):
        return dict(self._prefs)

    @property
    def arguments(self):
        return list(self._args)


class Service:
    def __init__(self, executable_path=None, port=0, service_args=None,
                 log_path=None, log_output=None, env=None, **kwargs):
        self.path = executable_path

    def start(self):
        return None

    def stop(self):
        return None


class FirefoxProfile:
    def __init__(self, profile_directory=None):
        self.path = profile_directory
        self._prefs = {}

    def set_preference(self, chave, valor):
        self._prefs[chave] = valor

    def update_preferences(self):
        return None


def Firefox(options=None, service=None, **kwargs):
    """Substitui `webdriver.Firefox(...)`, devolvendo um PWDriver.

    Traduz as options montadas por `Fix/core.py` para o launcher Playwright,
    de modo que `criar_driver_PC()` e afins continuem funcionando como estao.
    """
    opts = options or Options()
    perfil = getattr(opts, "profile", None)
    if isinstance(perfil, FirefoxProfile):
        perfil = perfil.path
    prefs = opts.preferences if hasattr(opts, "preferences") else {}
    cache = prefs.get("browser.cache.disk.enable", True)
    return launcher.criar_driver(
        headless=bool(getattr(opts, "headless", False)),
        perfil=perfil,
        prefs_extra=prefs,
        cache=bool(cache),
    )


Chrome = Firefox
Edge = Firefox
Remote = Firefox


def _modulo(nome, **conteudo):
    mod = types.ModuleType(nome)
    for chave, valor in conteudo.items():
        setattr(mod, chave, valor)
    sys.modules[nome] = mod
    return mod


def _montar_modulos():
    excecoes = {n: getattr(errors, n) for n in dir(errors)
                if isinstance(getattr(errors, n), type)
                and issubclass(getattr(errors, n), Exception)}

    ec = _modulo("selenium.webdriver.support.expected_conditions",
                 **{n: getattr(waits, n) for n in dir(waits)
                    if not n.startswith("_") and callable(getattr(waits, n))})

    raiz = _modulo("selenium", __version__="pjeplay", __path__=[])
    _modulo("selenium.common", exceptions=None, __path__=[])
    comum = _modulo("selenium.common.exceptions", **excecoes)
    sys.modules["selenium.common"].exceptions = comum

    wd = _modulo(
        "selenium.webdriver",
        Firefox=Firefox, Chrome=Chrome, Edge=Edge, Remote=Remote,
        FirefoxOptions=Options, ChromeOptions=Options,
        FirefoxProfile=FirefoxProfile, FirefoxService=Service,
        ActionChains=ActionChains, Keys=Keys, By=By,
        __path__=[],
    )
    raiz.webdriver = wd
    raiz.common = sys.modules["selenium.common"]

    _modulo("selenium.webdriver.common", __path__=[])
    _modulo("selenium.webdriver.common.by", By=By)
    _modulo("selenium.webdriver.common.keys", Keys=Keys)
    _modulo("selenium.webdriver.common.action_chains", ActionChains=ActionChains)
    _modulo("selenium.webdriver.common.desired_capabilities",
            DesiredCapabilities=types.SimpleNamespace(FIREFOX={}, CHROME={}))
    _modulo("selenium.webdriver.common.options", ArgOptions=Options)

    _modulo("selenium.webdriver.support", __path__=[], expected_conditions=ec)
    _modulo("selenium.webdriver.support.ui",
            WebDriverWait=waits.WebDriverWait, Select=Select)
    _modulo("selenium.webdriver.support.wait", WebDriverWait=waits.WebDriverWait)
    _modulo("selenium.webdriver.support.select", Select=Select)

    _modulo("selenium.webdriver.remote", __path__=[])
    _modulo("selenium.webdriver.remote.webdriver", WebDriver=PWDriver)
    _modulo("selenium.webdriver.remote.webelement", WebElement=PWElement)

    _modulo("selenium.webdriver.firefox", __path__=[])
    _modulo("selenium.webdriver.firefox.options", Options=Options)
    _modulo("selenium.webdriver.firefox.service", Service=Service)
    _modulo("selenium.webdriver.firefox.firefox_profile",
            FirefoxProfile=FirefoxProfile)
    _modulo("selenium.webdriver.firefox.webdriver", WebDriver=PWDriver)

    _modulo("selenium.webdriver.chrome", __path__=[])
    _modulo("selenium.webdriver.chrome.options", Options=Options)
    _modulo("selenium.webdriver.chrome.service", Service=Service)


def instalar(silencioso=False):
    """Aponta `selenium` para o backend Playwright. Idempotente."""
    global _INSTALADO
    if _INSTALADO:
        return True

    ja_carregados = [m for m in sys.modules
                     if m == "Fix" or m.startswith("Fix.")]
    if ja_carregados and not silencioso:
        logger.warning(
            "pjeplay.instalar() chamado apos %d modulos Fix ja importados; "
            "eles seguirao no Selenium real. Instale antes de qualquer import.",
            len(ja_carregados),
        )

    for nome in [m for m in sys.modules if m == "selenium" or m.startswith("selenium.")]:
        del sys.modules[nome]

    _montar_modulos()
    _INSTALADO = True
    if not silencioso:
        logger.info("pjeplay: backend Playwright instalado no lugar do selenium")
    return True
