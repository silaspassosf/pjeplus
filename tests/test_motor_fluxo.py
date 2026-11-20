"""Testes unitários do motor geral parametrizável Fix/motor_fluxo.py."""

from unittest.mock import MagicMock, patch

from Fix.motor_fluxo import (
    FluxoSpec,
    eh_erro_critico_driver,
    executar_fluxo_lote,
    extrair_id_numero,
)
from utilitarios_processamento import resultado_falha, resultado_ok


def test_extrair_id_numero_formatos_heterogeneos():
    assert extrair_id_numero({"processo": {"id": 10, "numero": "0001"}}) == (10, "0001")
    assert extrair_id_numero({"idProcesso": 22, "numeroProcesso": "0002"}) == (22, "0002")
    assert extrair_id_numero({"id": 33, "numero": "0003"}) == (33, "0003")


def test_eh_erro_critico_driver():
    assert eh_erro_critico_driver(RuntimeError("Target closed: page has been closed")) is True
    assert eh_erro_critico_driver(RuntimeError("RESTART_PEC: sessao"), extras=("RESTART_PEC",)) is True
    assert eh_erro_critico_driver(ValueError("campo vazio")) is False


def test_executar_fluxo_lote_skip_sucesso_falha_e_persistencia():
    driver = MagicMock()
    executados = []
    persistidos = []

    itens = [
        {"id": 1, "numero": "P1", "chave": "P1"},
        {"id": 2, "numero": "P2", "chave": "P2"},
        {"id": 3, "numero": "P3", "chave": "P3"},
    ]

    def _exec(_drv, item):
        executados.append(item["numero"])
        return item["numero"] != "P3"

    spec = FluxoSpec(
        nome="teste",
        executar=_exec,
        should_skip=lambda it: it["numero"] == "P1",
        open_item_fn=lambda _d, _it: resultado_ok(),
        persist_result=lambda it, res: persistidos.append((it["numero"], res["ok"])),
        fechar_abas_ao_final=False,
    )

    out = executar_fluxo_lote(driver, itens, spec)
    assert out["total"] == 3
    assert out["pulados"] == 1
    assert out["processados"] == 1
    assert out["erro"] == 1
    assert out["sucesso"] is False
    assert executados == ["P2", "P3"]
    assert persistidos == [("P2", True), ("P3", False)]


def test_executar_fluxo_lote_para_em_erro_critico():
    driver = MagicMock()
    vistos = []

    class _SessaoExpirada(Exception):
        pass

    def _exec(_drv, item):
        vistos.append(item["numero"])
        if item["numero"] == "P1":
            raise _SessaoExpirada("401")
        return True

    spec = FluxoSpec(
        nome="teste_crit",
        executar=_exec,
        should_skip=lambda _it: False,
        open_item_fn=lambda _d, _it: resultado_ok(),
        persist_result=lambda _it, _res: None,
        on_critical_exception=lambda exc: isinstance(exc, _SessaoExpirada),
        fechar_abas_ao_final=False,
    )

    itens = [{"id": 1, "numero": "P1"}, {"id": 2, "numero": "P2"}]
    out = executar_fluxo_lote(driver, itens, spec)
    assert out["critical_stop"] is True
    assert vistos == ["P1"]


def test_executar_fluxo_lote_usa_abrir_detalhe_padrao():
    driver = MagicMock()
    abertos = []

    def _fake_abrir(_drv, url, **_kw):
        abertos.append(url)
        return resultado_ok()

    spec = FluxoSpec(
        nome="p2b_sim",
        executar=lambda _d, _it: True,
        should_skip=lambda _it: False,
        persist_result=lambda _it, _res: None,
        fechar_abas_ao_final=False,
    )

    with patch("Fix.motor_fluxo.abrir_detalhe_processo", side_effect=_fake_abrir):
        out = executar_fluxo_lote(driver, [{"id": 999, "numero": "CNJ-999"}], spec)

    assert out["sucesso"] is True
    assert out["processados"] == 1
    assert abertos == ["https://pje.trt2.jus.br/pjekz/processo/999/detalhe"]
