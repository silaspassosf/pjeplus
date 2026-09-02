"""PWElement — fachada WebElement sobre um ElementHandle do Playwright.

Mantem a semantica do Selenium (resolucao ansiosa, staleness, get_attribute
misturando propriedade e atributo) porque o codigo de negocio depende dela.
"""
from .errors import NoSuchElementException, traduzir
from .locators import By, dividir_teclas, traduzir as traduzir_seletor

# Replica o comportamento do atom getAttribute do Selenium: propriedade quando
# ela existe e e mais fiel (value, href, innerHTML), atributo caso contrario.
_JS_ATRIBUTO = """
(el, nome) => {
  const BOOL = ['checked','selected','disabled','readonly','multiple','required',
                'hidden','open','autofocus','async','defer','ismap','loop',
                'novalidate','reversed','scoped','seamless'];
  const baixo = nome.toLowerCase();
  if (BOOL.includes(baixo)) {
    const prop = el[nome] !== undefined ? el[nome] : el[baixo];
    return prop ? 'true' : null;
  }
  if (baixo === 'value' && 'value' in el) {
    return el.value === null || el.value === undefined ? null : String(el.value);
  }
  if (baixo === 'href' || baixo === 'src') {
    return el[baixo] !== undefined ? String(el[baixo]) : el.getAttribute(nome);
  }
  if (['innerhtml','outerhtml','textcontent','innertext'].includes(baixo)) {
    const mapa = {innerhtml:'innerHTML', outerhtml:'outerHTML',
                  textcontent:'textContent', innertext:'innerText'};
    return el[mapa[baixo]];
  }
  const attr = el.getAttribute(nome);
  if (attr !== null) return attr;
  const prop = el[nome];
  if (prop === undefined || prop === null) return null;
  if (typeof prop === 'object' || typeof prop === 'function') return null;
  return String(prop);
}
"""


class PWElement:
    """Objeto com a mesma superficie do WebElement do Selenium."""

    __slots__ = ("_handle", "_page")

    def __init__(self, handle, page=None):
        self._handle = handle
        self._page = page

    # -- infraestrutura ---------------------------------------------------

    @property
    def page(self):
        if self._page is None:
            self._page = self._handle.owner_frame().page
        return self._page

    def _js(self, expressao, *args):
        try:
            return self._handle.evaluate(expressao, *args)
        except Exception as e:
            raise traduzir(e) from e

    def __repr__(self):
        return f"<PWElement {self._handle}>"

    def __eq__(self, outro):
        return isinstance(outro, PWElement) and self._handle == outro._handle

    def __hash__(self):
        return hash(id(self._handle))

    # -- leitura ----------------------------------------------------------

    @property
    def text(self):
        try:
            return self._handle.inner_text()
        except Exception as e:
            raise traduzir(e) from e

    @property
    def tag_name(self):
        return self._js("el => el.tagName.toLowerCase()")

    def get_attribute(self, nome):
        return self._js(_JS_ATRIBUTO, nome)

    def get_dom_attribute(self, nome):
        try:
            return self._handle.get_attribute(nome)
        except Exception as e:
            raise traduzir(e) from e

    def get_property(self, nome):
        return self._js("(el, n) => el[n]", nome)

    def value_of_css_property(self, nome):
        return self._js("(el, n) => getComputedStyle(el).getPropertyValue(n)", nome)

    def is_displayed(self):
        try:
            return self._handle.is_visible()
        except Exception:
            return False

    def is_enabled(self):
        try:
            return self._handle.is_enabled()
        except Exception:
            return False

    def is_selected(self):
        # Vale para <option> (selected) e para checkbox/radio (checked).
        return bool(self._js(
            "el => el.selected !== undefined ? !!el.selected : !!el.checked"))

    @property
    def rect(self):
        caixa = self._handle.bounding_box() or {}
        return {
            "x": caixa.get("x", 0), "y": caixa.get("y", 0),
            "width": caixa.get("width", 0), "height": caixa.get("height", 0),
        }

    @property
    def location(self):
        r = self.rect
        return {"x": r["x"], "y": r["y"]}

    @property
    def size(self):
        r = self.rect
        return {"width": r["width"], "height": r["height"]}

    @property
    def location_once_scrolled_into_view(self):
        self.scroll_into_view()
        return self.location

    @property
    def shadow_root(self):
        raiz = self._handle.evaluate_handle("el => el.shadowRoot")
        return PWElement(raiz, self._page)

    # -- acao -------------------------------------------------------------

    def click(self):
        # JS-first: nao depende de actionability (visible/enabled/STABLE) do
        # Playwright. O gate de estabilidade usa rAF e aba/janela inativa no
        # Firefox nao dispara rAF — com a janela ao fundo o clique nativo
        # travava 30s ("waiting for element to be stable"). O el.click() via
        # evaluate dispara os handlers igual ao padrao Selenium
        # (execute_script("arguments[0].click()")). Fallback nativo com
        # force=True (pula actionability) se o evaluate falhar.
        try:
            self._js("el => el.click()")
            return
        except Exception:
            pass
        try:
            self._handle.click(force=True, timeout=10000)
        except Exception as e:
            raise traduzir(e) from e

    def clear(self):
        try:
            self._handle.fill("")
        except Exception as e:
            raise traduzir(e) from e

    def send_keys(self, *valores):
        texto = "".join(str(v) for v in valores)
        teclado = self.page.keyboard
        try:
            # Gate curto de estabilidade: elemento em modal Angular pode ficar
            # instante por segundos (preview carregando) e o default de 30s do
            # Playwright trava o fluxo. Fallback JS se nao estabilizar rapido.
            try:
                self._handle.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                self._js("el => el.scrollIntoView({block: 'center'})")
            self._handle.focus()
            for tipo, dado in dividir_teclas(texto):
                if tipo == "texto":
                    teclado.type(dado)
                else:
                    teclado.press(dado)
        except Exception as e:
            raise traduzir(e) from e

    def submit(self):
        self._js("el => { const f = el.form || el.closest('form'); if (f) f.requestSubmit ? f.requestSubmit() : f.submit(); }")

    def scroll_into_view(self):
        try:
            self._handle.scroll_into_view_if_needed()
            return True
        except Exception:
            return False

    def screenshot_as_png(self):
        return self._handle.screenshot()

    def screenshot(self, caminho):
        self._handle.screenshot(path=caminho)
        return True

    # -- busca aninhada ---------------------------------------------------

    def find_element(self, by=By.CSS_SELECTOR, value=None):
        seletor = traduzir_seletor(by, value)
        try:
            achado = self._handle.query_selector(seletor)
        except Exception as e:
            raise traduzir(e, seletor) from e
        if achado is None:
            raise NoSuchElementException(f"Elemento nao encontrado: {seletor}")
        return PWElement(achado, self._page)

    def find_elements(self, by=By.CSS_SELECTOR, value=None):
        seletor = traduzir_seletor(by, value)
        try:
            return [PWElement(h, self._page) for h in self._handle.query_selector_all(seletor)]
        except Exception:
            return []
