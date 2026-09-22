"""Traducao de localizadores Selenium (By.*) e teclas (Keys.*) para Playwright.

O projeto usa By.CSS_SELECTOR em ~500 pontos e By.XPATH em ~117 — os demais
sao residuais. A traducao acontece uma unica vez, aqui.
"""
import json

from .errors import InvalidSelectorException


class By:
    ID = "id"
    XPATH = "xpath"
    LINK_TEXT = "link text"
    PARTIAL_LINK_TEXT = "partial link text"
    NAME = "name"
    TAG_NAME = "tag name"
    CLASS_NAME = "class name"
    CSS_SELECTOR = "css selector"


def _k(offset):
    """Codepoint da area privada usado pelo WebDriver para teclas especiais."""
    return chr(0xE000 + offset)


class Keys:
    """Mesmos codepoints do WebDriver — o codigo de negocio compara literais."""
    NULL = _k(0x00)
    CANCEL = _k(0x01)
    HELP = _k(0x02)
    BACKSPACE = _k(0x03)
    BACK_SPACE = BACKSPACE
    TAB = _k(0x04)
    CLEAR = _k(0x05)
    RETURN = _k(0x06)
    ENTER = _k(0x07)
    SHIFT = _k(0x08)
    LEFT_SHIFT = SHIFT
    CONTROL = _k(0x09)
    LEFT_CONTROL = CONTROL
    ALT = _k(0x0A)
    LEFT_ALT = ALT
    PAUSE = _k(0x0B)
    ESCAPE = _k(0x0C)
    SPACE = _k(0x0D)
    PAGE_UP = _k(0x0E)
    PAGE_DOWN = _k(0x0F)
    END = _k(0x10)
    HOME = _k(0x11)
    LEFT = _k(0x12)
    ARROW_LEFT = LEFT
    UP = _k(0x13)
    ARROW_UP = UP
    RIGHT = _k(0x14)
    ARROW_RIGHT = RIGHT
    DOWN = _k(0x15)
    ARROW_DOWN = DOWN
    INSERT = _k(0x16)
    DELETE = _k(0x17)
    SEMICOLON = _k(0x18)
    EQUALS = _k(0x19)
    NUMPAD0 = _k(0x1A)
    NUMPAD1 = _k(0x1B)
    NUMPAD2 = _k(0x1C)
    NUMPAD3 = _k(0x1D)
    NUMPAD4 = _k(0x1E)
    NUMPAD5 = _k(0x1F)
    NUMPAD6 = _k(0x20)
    NUMPAD7 = _k(0x21)
    NUMPAD8 = _k(0x22)
    NUMPAD9 = _k(0x23)
    MULTIPLY = _k(0x24)
    ADD = _k(0x25)
    SEPARATOR = _k(0x26)
    SUBTRACT = _k(0x27)
    DECIMAL = _k(0x28)
    DIVIDE = _k(0x29)
    F1 = _k(0x31)
    F2 = _k(0x32)
    F3 = _k(0x33)
    F4 = _k(0x34)
    F5 = _k(0x35)
    F6 = _k(0x36)
    F7 = _k(0x37)
    F8 = _k(0x38)
    F9 = _k(0x39)
    F10 = _k(0x3A)
    F11 = _k(0x3B)
    F12 = _k(0x3C)
    META = _k(0x3D)
    COMMAND = META


# Codepoint WebDriver -> nome de tecla Playwright (page.keyboard.press)
TECLAS_PW = {
    Keys.BACKSPACE: "Backspace",
    Keys.TAB: "Tab",
    Keys.CLEAR: "Delete",
    Keys.RETURN: "Enter",
    Keys.ENTER: "Enter",
    Keys.SHIFT: "Shift",
    Keys.CONTROL: "Control",
    Keys.ALT: "Alt",
    Keys.PAUSE: "Pause",
    Keys.ESCAPE: "Escape",
    Keys.SPACE: "Space",
    Keys.PAGE_UP: "PageUp",
    Keys.PAGE_DOWN: "PageDown",
    Keys.END: "End",
    Keys.HOME: "Home",
    Keys.LEFT: "ArrowLeft",
    Keys.UP: "ArrowUp",
    Keys.RIGHT: "ArrowRight",
    Keys.DOWN: "ArrowDown",
    Keys.INSERT: "Insert",
    Keys.DELETE: "Delete",
    Keys.SEMICOLON: "Semicolon",
    Keys.EQUALS: "Equal",
    Keys.MULTIPLY: "NumpadMultiply",
    Keys.ADD: "NumpadAdd",
    Keys.SUBTRACT: "NumpadSubtract",
    Keys.DECIMAL: "NumpadDecimal",
    Keys.DIVIDE: "NumpadDivide",
    Keys.META: "Meta",
    **{getattr(Keys, f"NUMPAD{i}"): f"Numpad{i}" for i in range(10)},
    **{getattr(Keys, f"F{i}"): f"F{i}" for i in range(1, 13)},
}

_MIN_ESPECIAL = _k(0x00)
_MAX_ESPECIAL = _k(0x3D)


def traduzir(by, valor):
    """Retorna o seletor no dialeto Playwright para o par (by, valor)."""
    if by in (By.CSS_SELECTOR, None):
        return valor
    if by == By.XPATH:
        return f"xpath={valor}"
    if by == By.ID:
        return f"[id={json.dumps(valor)}]"
    if by == By.NAME:
        return f"[name={json.dumps(valor)}]"
    if by == By.CLASS_NAME:
        return f"[class~={json.dumps(valor)}]"
    if by == By.TAG_NAME:
        return valor
    if by == By.LINK_TEXT:
        return f"a:text-is({json.dumps(valor)})"
    if by == By.PARTIAL_LINK_TEXT:
        return f"a:has-text({json.dumps(valor)})"
    raise InvalidSelectorException(f"Localizador nao suportado: {by!r}")


def dividir_teclas(texto):
    """Fatia uma sequencia de send_keys em blocos ('texto', str) / ('tecla', nome).

    send_keys('abc' + Keys.ENTER) vira [('texto', 'abc'), ('tecla', 'Enter')].
    """
    blocos = []
    buffer = []
    for ch in str(texto):
        if not (_MIN_ESPECIAL <= ch <= _MAX_ESPECIAL):
            buffer.append(ch)
            continue
        if buffer:
            blocos.append(("texto", "".join(buffer)))
            buffer = []
        nome = TECLAS_PW.get(ch)
        if nome:
            blocos.append(("tecla", nome))
    if buffer:
        blocos.append(("texto", "".join(buffer)))
    return blocos
