"""PWDriver — fachada WebDriver sobre Playwright.

O codigo de negocio do PJePlus fala WebDriver em ~1500 pontos
(execute_script, find_element(s), switch_to, window_handles, current_url...).
PWDriver implementa exatamente essa superficie sobre uma Page do Playwright,
o que permite rodar os modulos atuais — sem fork, sem editar arquivo algum.
"""
import time

from . import script as ponte
from .element import PWElement
from .errors import (
    NoAlertPresentException,
    NoSuchElementException,
    NoSuchFrameException,
    NoSuchWindowException,
    traduzir,
)
from .locators import By, traduzir as traduzir_seletor


class Alert:
    """Fachada do Alert do Selenium sobre um Dialog do Playwright."""

    def __init__(self, dialogo, driver):
        self._dialogo = dialogo
        self._driver = driver

    @property
    def text(self):
        return self._dialogo.message

    def accept(self):
        self._dialogo.accept()
        self._driver._dialogo_pendente = None

    def dismiss(self):
        self._dialogo.dismiss()
        self._driver._dialogo_pendente = None

    def send_keys(self, texto):
        self._dialogo.accept(texto)
        self._driver._dialogo_pendente = None


class SwitchTo:
    def __init__(self, driver):
        self._driver = driver

    @property
    def alert(self):
        driver = self._driver
        if driver._dialogo_pendente is None:
            driver.pulsar()  # despacha o evento de dialogo, se houver
        if driver._dialogo_pendente is None:
            raise NoAlertPresentException("Nenhum alerta presente")
        return Alert(driver._dialogo_pendente, driver)

    @property
    def active_element(self):
        handle = self._driver._ctx.evaluate_handle("() => document.activeElement")
        return PWElement(handle, self._driver.page)

    def window(self, handle):
        self._driver._ativar_janela(handle)

    def new_window(self, tipo="tab"):
        nova = self._driver._context.new_page()
        self._driver._registrar_pagina(nova)
        self._driver._pagina = nova
        self._driver._frame = None

    def default_content(self):
        self._driver._frame = None

    def parent_frame(self):
        frame = self._driver._frame
        self._driver._frame = frame.parent_frame if frame is not None else None

    def frame(self, referencia):
        self._driver._frame = self._driver._resolver_frame(referencia)


class Timeouts:
    def __init__(self, driver):
        self._driver = driver

    @property
    def implicit_wait(self):
        return self._driver._implicito

    @implicit_wait.setter
    def implicit_wait(self, valor):
        self._driver._implicito = float(valor)

    @property
    def page_load(self):
        return self._driver._timeout_pagina

    @page_load.setter
    def page_load(self, valor):
        self._driver._timeout_pagina = float(valor)

    @property
    def script(self):
        return self._driver._timeout_script

    @script.setter
    def script(self, valor):
        self._driver._timeout_script = float(valor)


class PWDriver:
    """WebDriver-compativel. `driver.page` expoe a Page Playwright crua."""

    def __init__(self, playwright, browser, context, pagina, headless=False,
                 espera_navegacao="domcontentloaded"):
        self._pw = playwright
        self._browser = browser
        self._context = context
        self._pagina = pagina
        self._frame = None
        self._handles = {}
        self._proximo_handle = 0
        self._implicito = 0.0
        self._timeout_pagina = 30.0
        self._timeout_script = 30.0
        self._dialogo_pendente = None
        self._encerrado = False
        self.headless = headless
        self.espera_navegacao = espera_navegacao
        # "accept" | "dismiss" | None (None = guarda para switch_to.alert)
        self.auto_dialogo = "accept"
        self.ultimo_dialogo = None
        # find_elements fiel ao Selenium aguarda o implicito quando vazio.
        # Desligar acelera varreduras que toleram lista vazia.
        self.implicito_em_find_elements = True

        self._context.on("page", self._registrar_pagina)
        self._registrar_pagina(pagina)

    # -- ciclo de vida de paginas ----------------------------------------

    def _registrar_pagina(self, pagina):
        if any(p is pagina for p in self._handles.values()):
            return
        self._proximo_handle += 1
        self._handles[f"pw-window-{self._proximo_handle}"] = pagina
        pagina.on("dialog", self._ao_abrir_dialogo)
        pagina.on("close", lambda p=pagina: self._ao_fechar_pagina(p))

    def _ao_fechar_pagina(self, pagina):
        for handle, alvo in list(self._handles.items()):
            if alvo is pagina:
                self._handles.pop(handle, None)
        if self._pagina is pagina:
            vivas = [p for p in self._handles.values() if not p.is_closed()]
            self._pagina = vivas[0] if vivas else None
            self._frame = None

    def _ao_abrir_dialogo(self, dialogo):
        self.ultimo_dialogo = dialogo.message
        # Um dialogo nao respondido congela a pagina inteira no Playwright.
        # O PJe nunca consome alertas, entao o padrao e aceitar — quem precisar
        # do fluxo Selenium (switch_to.alert) troca auto_dialogo para None.
        if dialogo.type == "beforeunload" or self.auto_dialogo:
            (dialogo.accept if self.auto_dialogo != "dismiss" else dialogo.dismiss)()
            return
        self._dialogo_pendente = dialogo

    def pulsar(self, segundos=0.05):
        """Cede tempo ao loop de eventos do Playwright durante polls Python.

        A API sync so despacha eventos (dialog, page, close) dentro de uma
        chamada ao servidor; um `time.sleep` puro deixaria eventos represados.
        """
        try:
            self.page.wait_for_timeout(int(segundos * 1000))
        except Exception:
            time.sleep(segundos)

    def _ativar_janela(self, handle):
        pagina = self._handles.get(handle)
        if pagina is None or pagina.is_closed():
            raise NoSuchWindowException(f"Janela inexistente: {handle}")
        self._pagina = pagina
        self._frame = None
        pagina.bring_to_front()

    def _resolver_frame(self, referencia):
        if isinstance(referencia, PWElement):
            frame = referencia._handle.content_frame()
        elif isinstance(referencia, int):
            iframes = self.page.query_selector_all("iframe, frame")
            if referencia >= len(iframes):
                raise NoSuchFrameException(f"Frame indice {referencia} inexistente")
            frame = iframes[referencia].content_frame()
        else:
            frame = next(
                (f for f in self.page.frames if f.name == referencia), None
            )
            if frame is None:
                alvo = self.page.query_selector(
                    f'iframe#{referencia}, iframe[name="{referencia}"], '
                    f'frame#{referencia}, frame[name="{referencia}"]'
                )
                frame = alvo.content_frame() if alvo else None
        if frame is None:
            raise NoSuchFrameException(f"Frame nao encontrado: {referencia!r}")
        return frame

    # -- acessores --------------------------------------------------------

    @property
    def page(self):
        """Page Playwright ativa (escape hatch para codigo novo)."""
        if self._pagina is None or self._pagina.is_closed():
            vivas = [p for p in self._handles.values() if not p.is_closed()]
            if not vivas:
                raise NoSuchWindowException("Nenhuma janela aberta")
            self._pagina = vivas[0]
        return self._pagina

    @property
    def _ctx(self):
        """Contexto de busca corrente: a Page ou o frame selecionado."""
        return self._frame if self._frame is not None else self.page

    @property
    def context(self):
        return self._context

    @property
    def playwright(self):
        return self._pw

    @property
    def current_url(self):
        return self.page.url

    @property
    def title(self):
        return self.page.title()

    @property
    def page_source(self):
        return self.page.content()

    @property
    def name(self):
        return "firefox"

    @property
    def session_id(self):
        return f"pjeplay-{id(self):x}"

    @property
    def capabilities(self):
        return {"browserName": "firefox", "pjeplay": True, "headless": self.headless}

    @property
    def switch_to(self):
        return SwitchTo(self)

    @property
    def timeouts(self):
        return Timeouts(self)

    @property
    def window_handles(self):
        return [h for h, p in self._handles.items() if not p.is_closed()]

    @property
    def current_window_handle(self):
        atual = self.page
        for handle, pagina in self._handles.items():
            if pagina is atual:
                return handle
        raise NoSuchWindowException("Janela atual nao registrada")

    # -- navegacao --------------------------------------------------------

    def get(self, url):
        try:
            self.page.goto(
                url,
                wait_until=self.espera_navegacao,
                timeout=int(self._timeout_pagina * 1000),
            )
        except Exception as e:
            raise traduzir(e) from e
        self._frame = None

    def refresh(self):
        self.page.reload(wait_until=self.espera_navegacao,
                         timeout=int(self._timeout_pagina * 1000))
        self._frame = None

    def back(self):
        self.page.go_back(wait_until=self.espera_navegacao)
        self._frame = None

    def forward(self):
        self.page.go_forward(wait_until=self.espera_navegacao)
        self._frame = None

    # -- busca ------------------------------------------------------------

    def find_element(self, by=By.CSS_SELECTOR, value=None):
        seletor = traduzir_seletor(by, value)
        ctx = self._ctx
        try:
            if self._implicito > 0:
                achado = ctx.wait_for_selector(
                    seletor, state="attached", timeout=int(self._implicito * 1000)
                )
            else:
                achado = ctx.query_selector(seletor)
        except Exception as e:
            erro = traduzir(e, seletor)
            if type(erro).__name__ == "TimeoutException":
                raise NoSuchElementException(f"Elemento nao encontrado: {seletor}") from e
            raise erro from e
        if achado is None:
            raise NoSuchElementException(f"Elemento nao encontrado: {seletor}")
        return PWElement(achado, self.page)

    def find_elements(self, by=By.CSS_SELECTOR, value=None):
        seletor = traduzir_seletor(by, value)
        ctx = self._ctx
        try:
            achados = ctx.query_selector_all(seletor)
            if not achados and self._implicito > 0 and self.implicito_em_find_elements:
                try:
                    ctx.wait_for_selector(
                        seletor, state="attached",
                        timeout=int(self._implicito * 1000),
                    )
                    achados = ctx.query_selector_all(seletor)
                except Exception:
                    achados = []
        except Exception:
            return []
        return [PWElement(h, self.page) for h in achados]

    def find_elements_by_xpath(self, xpath):
        return self.find_elements(By.XPATH, xpath)

    def find_element_by_css_selector(self, seletor):
        return self.find_element(By.CSS_SELECTOR, seletor)

    # -- scripts ----------------------------------------------------------

    def execute_script(self, script, *args):
        return ponte.executar(self._ctx, script, args, assincrono=False)

    def execute_async_script(self, script, *args):
        # O callback do script controla a conclusao; o teto e o script timeout.
        self.page.set_default_timeout(int(self._timeout_script * 1000))
        return ponte.executar(self._ctx, script, args, assincrono=True)

    def execute_cdp_cmd(self, *args, **kwargs):
        """Firefox/Playwright nao expoe CDP; mantido como no-op de compatibilidade."""
        return {}

    # -- timeouts ---------------------------------------------------------

    def implicitly_wait(self, segundos):
        self._implicito = float(segundos)

    def set_script_timeout(self, segundos):
        self._timeout_script = float(segundos)

    def set_page_load_timeout(self, segundos):
        self._timeout_pagina = float(segundos)

    # -- janela -----------------------------------------------------------

    def maximize_window(self):
        self.set_window_size(1920, 1080)

    def minimize_window(self):
        return None

    def fullscreen_window(self):
        self.set_window_size(1920, 1080)

    def set_window_size(self, largura, altura, windowHandle="current"):
        self.page.set_viewport_size({"width": int(largura), "height": int(altura)})

    def get_window_size(self, windowHandle="current"):
        vp = self.page.viewport_size or {"width": 1920, "height": 1080}
        return {"width": vp["width"], "height": vp["height"]}

    def set_window_position(self, x, y, windowHandle="current"):
        return {"x": x, "y": y}

    def get_window_position(self, windowHandle="current"):
        return {"x": 0, "y": 0}

    def save_screenshot(self, caminho):
        try:
            self.page.screenshot(path=caminho, full_page=False)
            return True
        except Exception:
            return False

    get_screenshot_as_file = save_screenshot

    def get_screenshot_as_png(self):
        return self.page.screenshot()

    # -- cookies ----------------------------------------------------------

    def get_cookies(self):
        saida = []
        for c in self._context.cookies():
            item = {
                "name": c.get("name"), "value": c.get("value"),
                "domain": c.get("domain"), "path": c.get("path", "/"),
                "secure": c.get("secure", False),
                "httpOnly": c.get("httpOnly", False),
            }
            expira = c.get("expires", -1)
            if expira and expira > 0:
                item["expiry"] = int(expira)
            if c.get("sameSite"):
                item["sameSite"] = c["sameSite"]
            saida.append(item)
        return saida

    def get_cookie(self, nome):
        return next((c for c in self.get_cookies() if c["name"] == nome), None)

    def add_cookie(self, cookie):
        item = dict(cookie)
        if "expiry" in item:
            item["expires"] = float(item.pop("expiry"))
        item.setdefault("path", "/")
        if not item.get("domain") and not item.get("url"):
            item["url"] = self.current_url
        self._context.add_cookies([item])

    def delete_cookie(self, nome):
        restantes = [c for c in self._context.cookies() if c.get("name") != nome]
        self._context.clear_cookies()
        if restantes:
            self._context.add_cookies(restantes)

    def delete_all_cookies(self):
        self._context.clear_cookies()

    # -- encerramento -----------------------------------------------------

    def close(self):
        try:
            atual = self._pagina
            if atual is not None and not atual.is_closed():
                atual.close()
        except Exception:
            pass

    def quit(self):
        if self._encerrado:
            return
        self._encerrado = True
        # Fecha apenas browser e context — o _pw e compartilhado
        # via singleton em launcher.py e nao pode ser parado aqui
        # (mataria outros drivers ativos, ex: PJe + SISB).
        for fechar in (
            lambda: self._context.close(),
            lambda: self._browser.close(),
        ):
            try:
                fechar()
            except Exception:
                pass
        self._handles.clear()
        self._pagina = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.quit()
        return False


def aguardar(condicao, timeout=10, intervalo=0.05):
    """Poll generico usado pelos compatibilizadores (WebDriverWait/EC)."""
    limite = time.monotonic() + float(timeout)
    while True:
        resultado = condicao()
        if resultado:
            return resultado
        if time.monotonic() >= limite:
            return False
        time.sleep(intervalo)
