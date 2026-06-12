"""
Isolated DOM Eletrônico "lembrete" detection test (sem rodar x.py / sem API demorada).

O objetivo é validar que:
- has_dom_eletronico_reminder() detecta o painel "Dom Eletronico"
- _extrair_conteudo_lembrete_dom() retorna o texto correto
- a decisão "via correio / correio enviado" (match robusto) funciona para variações

Este teste usa um driver/fake-element minimalista para imitar Selenium.
Execute: python test_dom_lembrete_detection_isolated.py
"""

from dataclasses import dataclass
from typing import List, Optional, Any

from selenium.webdriver.common.by import By

# Importa alvo
from bianca.dom_engine import has_dom_eletronico_reminder, _extrair_conteudo_lembrete_dom


def _norm_text(s: str) -> str:
    import unicodedata

    s2 = unicodedata.normalize("NFKD", s or "")
    s2 = s2.encode("ascii", "ignore").decode("ascii", "ignore")
    return s2.lower()


def _contem_via_correio(conteudo: Optional[str]) -> bool:
    conteudo_norm = _norm_text(conteudo or "")
    contem_correio = "correio" in conteudo_norm
    contem_enviado = "enviado" in conteudo_norm
    contem_via_correio = ("via" in conteudo_norm and contem_correio) or (
        "correio enviado" in conteudo_norm
    )
    return bool(conteudo and (contem_via_correio or (contem_correio and contem_enviado)))


@dataclass
class FakeElement:
    text: str

    def find_element(self, by: str, selector: str) -> "FakeElement":
        raise NotImplementedError("Use FakePanel for nested lookups.")


@dataclass
class FakePanel:
    title_text: str
    description_text: str

    def find_element(self, by: str, selector: str) -> FakeElement:
        if selector == "mat-panel-title.post-it-titulo":
            return FakeElement(self.title_text)
        if selector == "mat-panel-description":
            return FakeElement(self.description_text)
        raise ValueError(f"Unexpected selector in FakePanel: {selector!r}")


class FakeDriver:
    """
    Apenas o suficiente para as funções do dom_engine dependerem:
    - find_elements(css, "mat-panel-title.post-it-titulo") para has_dom_eletronico_reminder
    - find_elements(css, "mat-expansion-panel") para _extrair_conteudo_lembrete_dom
    - current_url não é necessário neste teste
    """

    def __init__(self, panels: List[FakePanel]):
        self._panels = panels

    def find_elements(self, by: str, selector: str) -> List[Any]:
        if by == By.CSS_SELECTOR and selector == "mat-panel-title.post-it-titulo":
            return [FakeElement(p.title_text) for p in self._panels]
        if by == By.CSS_SELECTOR and selector == "mat-expansion-panel":
            return list(self._panels)
        raise ValueError(f"Unexpected find_elements: by={by!r} selector={selector!r}")


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def assert_eq(a: Any, b: Any, msg: str) -> None:
    if a != b:
        raise AssertionError(f"{msg}\nExpected: {b!r}\nGot: {a!r}")


def run_case(case_name: str, title_text: str, desc_text: Optional[str], expect_has: bool, expect_via: bool):
    driver = FakeDriver(panels=[FakePanel(title_text=title_text, description_text=desc_text or "")])

    has = has_dom_eletronico_reminder(driver)
    assert_eq(has, expect_has, f"[{case_name}] has_dom_eletronico_reminder mismatch")

    conteudo = _extrair_conteudo_lembrete_dom(driver)
    assert_eq(conteudo, desc_text, f"[{case_name}] _extrair_conteudo_lembrete_dom mismatch")

    via = _contem_via_correio(conteudo)
    assert_eq(via, expect_via, f"[{case_name}] via_correio decision mismatch")


def main():
    # 1) Correio + enviado (ordem e frases esperadas)
    run_case(
        "via_correio_com_via",
        title_text="Dom Eletronico",
        desc_text="Ciencia negativa Domicilio: via Correio enviado",
        expect_has=True,
        expect_via=True,
    )

    # 2) "Correio enviado" (sem "via")
    run_case(
        "correio_enviado_sem_via",
        title_text="DomicEletr - post-it",
        desc_text="Ciencia negativa Domicilio: correio enviado",
        expect_has=True,
        expect_via=True,
    )

    # 3) Não é correio enviado (deve pular)
    run_case(
        "lembrete_sem_correio",
        title_text="DomElet",
        desc_text="Ciencia negativa Domicilio: sem correio aqui",
        expect_has=True,
        expect_via=False,
    )

    # 4) Painel não existe
    driver = FakeDriver(panels=[FakePanel(title_text="Outro Painel", description_text="correio enviado")])
    has = has_dom_eletronico_reminder(driver)
    assert_eq(has, False, "[painel_inexistente] has_dom_eletronico_reminder should be False")

    conteudo = _extrair_conteudo_lembrete_dom(driver)
    assert_eq(conteudo, None, "[painel_inexistente] _extrair_conteudo_lembrete_dom should be None")

    print("OK - isolated lembrete detection tests passed.")


if __name__ == "__main__":
    main()
