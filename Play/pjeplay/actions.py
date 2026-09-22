"""ActionChains e Select compativeis com Selenium, sobre Playwright."""
import time

from .element import PWElement
from .errors import NoSuchElementException, UnexpectedTagNameException
from .locators import dividir_teclas


class ActionChains:
    """Fila de acoes executada em perform(), como no Selenium."""

    def __init__(self, driver, duration=250):
        self._driver = driver
        self._fila = []
        self._duracao = duration

    # -- infraestrutura ---------------------------------------------------

    def _enfileirar(self, fn):
        self._fila.append(fn)
        return self

    @property
    def _mouse(self):
        return self._driver.page.mouse

    @property
    def _teclado(self):
        return self._driver.page.keyboard

    def _centro(self, elemento):
        caixa = elemento._handle.bounding_box()
        if not caixa:
            raise NoSuchElementException("Elemento sem caixa delimitadora")
        return caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2

    # -- movimento --------------------------------------------------------

    def move_to_element(self, elemento):
        return self._enfileirar(lambda: elemento._handle.hover())

    def move_to_element_with_offset(self, elemento, dx, dy):
        def _acao():
            x, y = self._centro(elemento)
            self._mouse.move(x + dx, y + dy)
        return self._enfileirar(_acao)

    def move_by_offset(self, dx, dy):
        return self._enfileirar(lambda: self._mouse.move(dx, dy))

    def scroll_to_element(self, elemento):
        return self._enfileirar(lambda: elemento._handle.scroll_into_view_if_needed())

    # -- cliques ----------------------------------------------------------

    def click(self, elemento=None):
        if elemento is not None:
            return self._enfileirar(lambda: elemento._handle.click())
        return self._enfileirar(lambda: self._mouse.down() or self._mouse.up())

    def double_click(self, elemento=None):
        if elemento is not None:
            return self._enfileirar(lambda: elemento._handle.dblclick())
        return self._enfileirar(lambda: self._mouse.dblclick(0, 0))

    def context_click(self, elemento=None):
        if elemento is not None:
            return self._enfileirar(lambda: elemento._handle.click(button="right"))
        return self._enfileirar(lambda: self._mouse.down(button="right"))

    def click_and_hold(self, elemento=None):
        def _acao():
            if elemento is not None:
                elemento._handle.hover()
            self._mouse.down()
        return self._enfileirar(_acao)

    def release(self, elemento=None):
        def _acao():
            if elemento is not None:
                elemento._handle.hover()
            self._mouse.up()
        return self._enfileirar(_acao)

    def drag_and_drop(self, origem, destino):
        def _acao():
            origem._handle.hover()
            self._mouse.down()
            destino._handle.hover()
            self._mouse.up()
        return self._enfileirar(_acao)

    def drag_and_drop_by_offset(self, origem, dx, dy):
        def _acao():
            x, y = self._centro(origem)
            origem._handle.hover()
            self._mouse.down()
            self._mouse.move(x + dx, y + dy)
            self._mouse.up()
        return self._enfileirar(_acao)

    # -- teclado ----------------------------------------------------------

    def send_keys(self, *valores):
        texto = "".join(str(v) for v in valores)

        def _acao():
            for tipo, dado in dividir_teclas(texto):
                if tipo == "texto":
                    self._teclado.type(dado)
                else:
                    self._teclado.press(dado)
        return self._enfileirar(_acao)

    def send_keys_to_element(self, elemento, *valores):
        return self._enfileirar(lambda: elemento.send_keys(*valores))

    def key_down(self, tecla, elemento=None):
        nome = self._nome_tecla(tecla)

        def _acao():
            if elemento is not None:
                elemento._handle.focus()
            self._teclado.down(nome)
        return self._enfileirar(_acao)

    def key_up(self, tecla, elemento=None):
        nome = self._nome_tecla(tecla)
        return self._enfileirar(lambda: self._teclado.up(nome))

    @staticmethod
    def _nome_tecla(tecla):
        blocos = dividir_teclas(str(tecla))
        for tipo, dado in blocos:
            if tipo == "tecla":
                return dado
        return str(tecla)

    def pause(self, segundos):
        return self._enfileirar(lambda: time.sleep(float(segundos)))

    # -- execucao ---------------------------------------------------------

    def perform(self):
        for acao in self._fila:
            acao()
        self._fila.clear()

    def reset_actions(self):
        self._fila.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.perform()
        return False


class Select:
    """Fachada do Select do Selenium para elementos <select> nativos."""

    def __init__(self, elemento):
        if not isinstance(elemento, PWElement):
            raise UnexpectedTagNameException("Select espera um elemento")
        if elemento.tag_name != "select":
            raise UnexpectedTagNameException(
                f"Select so funciona em <select>, recebido <{elemento.tag_name}>"
            )
        self._el = elemento
        self.is_multiple = bool(elemento.get_attribute("multiple"))

    @property
    def options(self):
        return self._el.find_elements("css selector", "option")

    @property
    def all_selected_options(self):
        return [o for o in self.options if o.is_selected()]

    @property
    def first_selected_option(self):
        for opcao in self.options:
            if opcao.is_selected():
                return opcao
        raise NoSuchElementException("Nenhuma opcao selecionada")

    def select_by_visible_text(self, texto):
        self._el._handle.select_option(label=texto)

    def select_by_value(self, valor):
        self._el._handle.select_option(value=valor)

    def select_by_index(self, indice):
        self._el._handle.select_option(index=int(indice))

    def deselect_all(self):
        self._el._handle.select_option([])

    def deselect_by_value(self, valor):
        restantes = [
            o.get_attribute("value")
            for o in self.all_selected_options
            if o.get_attribute("value") != valor
        ]
        self._el._handle.select_option(value=restantes)

    def deselect_by_index(self, indice):
        restantes = [
            o.get_attribute("value")
            for i, o in enumerate(self.options)
            if o.is_selected() and i != int(indice)
        ]
        self._el._handle.select_option(value=restantes)

    def deselect_by_visible_text(self, texto):
        restantes = [
            o.get_attribute("value")
            for o in self.all_selected_options
            if o.text != texto
        ]
        self._el._handle.select_option(value=restantes)
