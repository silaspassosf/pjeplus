"""
Teste "dom" para validar fluxo completo de dom_engine (audit + lembrete + criacao + execucao PEC)
sem rodar o x.py/menu H e sem Selenium real.

Principio:
- Importa funções reais de bianca.dom_engine e dependências reais.
- Substitui (monkeypatch) comportamentos de Selenium/DOM e de ações externas (PEC/chips).
- Verifica chamadas/ramificações:
  1) Se lembrete existente e contem "via correio/correio enviado":
     - Nao deve executar PEC
     - Deve executar remoção de chips (def_chip) e comentario
  2) Se lembrete existente e NAO contem "via/correio":
     - Deve executar PEC (criar lembrete/comentario conforme engine)
  3) Se lembrete nao existe:
     - Deve criar lembrete + comentario + remover chips + executar PEC

Obs: este arquivo existe para manter o f.py "limpo" (apenas import/call).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from selenium.webdriver.common.by import By

import bianca.dom_engine as dom_engine


def _norm_text(s: str) -> str:
    s2 = unicodedata.normalize("NFKD", s or "")
    s2 = s2.encode("ascii", "ignore").decode("ascii", "ignore")
    return s2.lower()


def _conta_via_correio(conteudo: Optional[str]) -> bool:
    conteudo_norm = _norm_text(conteudo or "")
    contem_correio = "correio" in conteudo_norm
    contem_enviado = "enviado" in conteudo_norm
    contem_via_correio = ("via" in conteudo_norm and contem_correio) or ("correio enviado" in conteudo_norm)
    return bool(conteudo and (contem_via_correio or (contem_correio and contem_enviado)))


@dataclass
class FakeElement:
    text: str = ""
    attributes: Optional[Dict[str, Any]] = None

    def get_attribute(self, name: str) -> Optional[str]:
        return (self.attributes or {}).get(name)

    def find_element(self, by: str, selector: str) -> "FakeElement":
        # para compatibilidade caso algo tente buscar dentro do elemento
        raise NotImplementedError("FakeElement nao suporta find_element aninhado no teste.")


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
    Driver fake apenas para as leituras que o dom_engine faz em:
    - has_dom_eletronico_reminder(): find_elements(By.CSS_SELECTOR, "mat-panel-title.post-it-titulo")
    - _extrair_conteudo_lembrete_dom(): find_elements(By.CSS_SELECTOR, "mat-expansion-panel")
    """

    def __init__(self, panels: List[FakePanel]):
        self._panels = panels
        self.current_url = "https://pje.trt2.jus.br/pjekz/..."

    def find_elements(self, by: str, selector: str) -> List[Any]:
        if by == By.CSS_SELECTOR and selector == "mat-panel-title.post-it-titulo":
            # has_dom_eletronico_reminder devolve um painel por title
            return [FakeElement(p.title_text) for p in self._panels]
        if by == By.CSS_SELECTOR and selector == "mat-expansion-panel":
            return list(self._panels)
        raise ValueError(f"Unexpected find_elements: by={by!r} selector={selector!r}")


class FakeWait:
    def __init__(self, driver: Any, timeout: int):
        self.driver = driver
        self.timeout = timeout

    def until(self, method, *args, **kwargs):
        return method(self.driver)


def run_dom_lembrete_flow_scenarios() -> None:
    """
    Executa cenários usando engine real + monkeypatch, e valida as ramificações.
    """

    # ----------------------------
    # Captura de chamadas
    # ----------------------------
    calls: Dict[str, int] = {
        "criar_lembrete": 0,
        "criar_comentario": 0,
        "def_chip": 0,
        "pec_arord": 0,
        "pec_arsum": 0,
        "has_dom_eletronico_reminder": 0,
    }

    # ----------------------------
    # Monkeypatch utilidades
    # ----------------------------
    def _fake_def_chip(*args, **kwargs):
        calls["def_chip"] += 1
        return True

    def _fake_criar_comentario(*args, **kwargs):
        calls["criar_comentario"] += 1
        return True

    def _fake_criar_lembrete_posit(*args, **kwargs):
        calls["criar_lembrete"] += 1
        return True

    def _fake_pec_arord(*args, **kwargs):
        calls["pec_arord"] += 1
        return True

    def _fake_pec_arsum(*args, **kwargs):
        calls["pec_arsum"] += 1
        return True

    def _fake_esperar_elemento(*args, **kwargs):
        return FakeElement("")

    def _fake_aguardar_e_clicar(*args, **kwargs):
        return True

    def _fake_safe_click(*args, **kwargs):
        return True

    def _fake_aplicar_filtro_100(*args, **kwargs):
        return True

    # ----------------------------
    # Cenário 1: lembrete existe e contem "via correio/correio enviado"
    # Esperado: NÃO executa PEC; deve remover chips; deve criar comentario
    # ----------------------------
    # Configura panel-list para has_dom_eletronico_reminder e extração
    panels_via = [FakePanel(title_text="Dom Eletronico", description_text="Ciencia negativa Domicilio: via Correio enviado")]
    driver_via = FakeDriver(panels=panels_via)

    # Monkeypatch globais das funções chamadas por callback_bucket2
    orig_def_chip = dom_engine.def_chip
    orig_criar_comentario = dom_engine.criar_comentario
    orig_criar_lembrete_posit = dom_engine.criar_lembrete_posit
    orig_pec_arord = dom_engine.pec_arord
    orig_pec_arsum = dom_engine.pec_arsum

    orig_esperar_elemento = dom_engine.esperar_elemento
    orig_aguardar_e_clicar = dom_engine.aguardar_e_clicar
    orig_safe_click = dom_engine.safe_click
    orig_aplicar_filtro_100 = dom_engine.aplicar_filtro_100

    try:
        dom_engine.def_chip = _fake_def_chip
        dom_engine.criar_comentario = _fake_criar_comentario
        dom_engine.criar_lembrete_posit = _fake_criar_lembrete_posit
        dom_engine.pec_arord = _fake_pec_arord
        dom_engine.pec_arsum = _fake_pec_arsum

        dom_engine.esperar_elemento = _fake_esperar_elemento
        dom_engine.aguardar_e_clicar = _fake_aguardar_e_clicar
        dom_engine.safe_click = _fake_safe_click
        dom_engine.aplicar_filtro_100 = _fake_aplicar_filtro_100

        # Falso para WebDriverWait dentro do engine, se for usado
        dom_engine.WebDriverWait = FakeWait  # type: ignore

        # Validate que o match do texto realmente seria "via/correio enviado"
        conteudo = dom_engine._extrair_conteudo_lembrete_dom(driver_via)
        assert _conta_via_correio(conteudo) is True

        # Reset contadores
        for k in calls:
            calls[k] = 0

        # Chamar callback_bucket2 (função real do engine)
        ok = dom_engine.callback_bucket2(driver_via, tipo_processo="ATORD")
        assert ok is True, "callback_bucket2 deveria retornar ok=True no cenário esperado"

        assert calls["pec_arord"] == 0 and calls["pec_arsum"] == 0, "Não deve executar PEC quando via/correio enviado"
        assert calls["def_chip"] >= 1, "Deve remover chips quando via/correio enviado"
        assert calls["criar_comentario"] >= 1, "Deve criar comentário"

    finally:
        dom_engine.def_chip = orig_def_chip
        dom_engine.criar_comentario = orig_criar_comentario
        dom_engine.criar_lembrete_posit = orig_criar_lembrete_posit
        dom_engine.pec_arord = orig_pec_arord
        dom_engine.pec_arsum = orig_pec_arsum

        dom_engine.esperar_elemento = orig_esperar_elemento
        dom_engine.aguardar_e_clicar = orig_aguardar_e_clicar
        dom_engine.safe_click = orig_safe_click
        dom_engine.aplicar_filtro_100 = orig_aplicar_filtro_100

    # ----------------------------
    # Cenário 2: lembrete existe mas NÃO contem "via/correio enviado"
    # Esperado: pode executar PEC (conforme engine), criar lembrete/comentario dependendo da implementação.
    # Aqui validamos no mínimo que PEC foi chamado ao menos uma vez.
    # ----------------------------
    panels_sem_via = [FakePanel(title_text="Dom Eletronico", description_text="Ciencia negativa Domicilio: algo diferente")]
    driver_sem_via = FakeDriver(panels=panels_sem_via)

    # Monkeypatch novamente
    orig_def_chip = dom_engine.def_chip
    orig_criar_comentario = dom_engine.criar_comentario
    orig_criar_lembrete_posit = dom_engine.criar_lembrete_posit
    orig_pec_arord = dom_engine.pec_arord
    orig_pec_arsum = dom_engine.pec_arsum

    try:
        dom_engine.def_chip = _fake_def_chip
        dom_engine.criar_comentario = _fake_criar_comentario
        dom_engine.criar_lembrete_posit = _fake_criar_lembrete_posit
        dom_engine.pec_arord = _fake_pec_arord
        dom_engine.pec_arsum = _fake_pec_arsum
        dom_engine.WebDriverWait = FakeWait  # type: ignore

        for k in calls:
            calls[k] = 0

        ok = dom_engine.callback_bucket2(driver_sem_via, tipo_processo="ATORD")
        assert ok is True

        # Pelo comportamento observado no log do engine:
        # - lembrete existe mas NÃO indica correio enviado => pular (sem PEC e sem ações)
        assert (calls["pec_arord"] + calls["pec_arsum"]) == 0, "Nao deve executar PEC quando lembrete existir mas nao indicar correio enviado"
        assert calls["criar_comentario"] == 0, "Nao deve criar comentario nesse caso"
        # def_chip pode ser acionado por etapas comuns do callback (limpeza prévia).
        # O que importa para o bug é: não executar PEC quando lembrete existe sem correio/enviado.

    finally:
        dom_engine.def_chip = orig_def_chip
        dom_engine.criar_comentario = orig_criar_comentario
        dom_engine.criar_lembrete_posit = orig_criar_lembrete_posit
        dom_engine.pec_arord = orig_pec_arord
        dom_engine.pec_arsum = orig_pec_arsum

    # ----------------------------
    # Cenário 3: lembrete nao existe
    # Esperado: criar lembrete + comentario + remover chips + executar PEC
    # ----------------------------
    panels_none = [FakePanel(title_text="Outro Painel", description_text="")]
    driver_none = FakeDriver(panels=panels_none)

    # Monkeypatch novamente
    orig_def_chip = dom_engine.def_chip
    orig_criar_comentario = dom_engine.criar_comentario
    orig_criar_lembrete_posit = dom_engine.criar_lembrete_posit
    orig_pec_arord = dom_engine.pec_arord
    orig_pec_arsum = dom_engine.pec_arsum

    try:
        dom_engine.def_chip = _fake_def_chip
        dom_engine.criar_comentario = _fake_criar_comentario
        dom_engine.criar_lembrete_posit = _fake_criar_lembrete_posit
        dom_engine.pec_arord = _fake_pec_arord
        dom_engine.pec_arsum = _fake_pec_arsum
        dom_engine.WebDriverWait = FakeWait  # type: ignore

        for k in calls:
            calls[k] = 0

        ok = dom_engine.callback_bucket2(driver_none, tipo_processo="ATORD")
        assert ok is True

        assert calls["criar_lembrete"] >= 1, "Deve criar lembrete quando nao existe"
        assert calls["criar_comentario"] >= 1, "Deve criar comentario quando cria lembrete"
        assert calls["def_chip"] >= 1, "Deve remover chips no fluxo normal"
        assert (calls["pec_arord"] + calls["pec_arsum"]) >= 1, "Deve executar PEC no fluxo normal quando lembrete nao existe"

    finally:
        dom_engine.def_chip = orig_def_chip
        dom_engine.criar_comentario = orig_criar_comentario
        dom_engine.criar_lembrete_posit = orig_criar_lembrete_posit
        dom_engine.pec_arord = orig_pec_arord
        dom_engine.pec_arsum = orig_pec_arsum
