# -*- coding: utf-8 -*-
"""Testes unitários da tarefa pós-xs1 CPcumprir (Prazo/p2b_cpcumprir.py)."""

from unittest.mock import MagicMock, patch

import pytest


def test_ato_cp1_importavel():
    """Garante que ato_cp1 em atos/wrappers_ato.py importa sem erro de sintaxe."""
    from atos.wrappers_ato import ato_cp1

    assert callable(ato_cp1)


def test_buscar_processos_por_tarefa_pagina_e_normaliza():
    """PjeApiClient.buscar_processos_por_tarefa pagina e filtra com normalização de acento/caixa."""
    from Fix.variaveis import PjeApiClient

    client = PjeApiClient(MagicMock(), "pje.trt2.jus.br")
    respostas = [
        {
            "ok": True,
            "status": 200,
            "data": {
                "qtdPaginas": 2,
                "resultado": [
                    {"id": 101, "numero": "0000101-11.2026.5.02.0001", "tarefa": "Iniciar Execução"},
                    {"id": 102, "numero": "0000102-11.2026.5.02.0002", "tarefa": "Análise"},
                ],
            },
            "error": None,
        },
        {
            "ok": True,
            "status": 200,
            "data": {
                "qtdPaginas": 2,
                "resultado": [
                    {"id": 103, "numero": "0000103-11.2026.5.02.0003", "nomeTarefa": "  iniciar execucao "},
                    {"id": 104, "numero": "0000104-11.2026.5.02.0004", "tarefa": {"nome": "INICIAR EXECUÇÃO"}},
                ],
            },
            "error": None,
        },
    ]

    with patch.object(client, "gateway_patch", side_effect=respostas) as mock_patch:
        encontrados, diag = client.buscar_processos_por_tarefa(
            "Iniciar Execução", tamanho_pagina=2, retornar_diagnostico=True
        )

    assert [p["id"] for p in encontrados] == [101, 103, 104]
    assert mock_patch.call_count == 2
    assert mock_patch.call_args_list[0].args[0] == "/pje-comum-api/api/agrupamentotarefas/10/processos"
    assert mock_patch.call_args_list[0].kwargs["json_data"]["juizoDigital"] is None
    assert diag["ok"] is True
    assert diag["total_varrido"] == 4


def test_listar_processos_fallback_browser_fetch_quando_gateway_falha():
    from Prazo.p2b_cpcumprir import listar_processos_iniciar_execucao

    driver = MagicMock()
    driver.current_url = "https://pje.trt2.jus.br/pjekz/gigs/meu-painel"
    driver.page.evaluate.return_value = {
        "ok": True,
        "status": 200,
        "paginas": 1,
        "path": "/pje-comum-api/api/agrupamentotarefas/10/processos",
        "resultado": [
            {"id": 201, "numero": "0000201-11.2026.5.02.0001", "tarefa": "Iniciar Execução"},
            {"id": 202, "numero": "0000202-11.2026.5.02.0002", "tarefa": "Triagem Inicial"},
        ],
    }

    fake_client = MagicMock()
    fake_client.buscar_processos_por_tarefa.return_value = (
        [],
        {"ok": False, "status": 403, "erro": {"message": "forbidden"}, "path": "/pje-comum-api/api/agrupamentotarefas/10/processos"},
    )

    with patch("Prazo.p2b_cpcumprir._criar_api_client", return_value=fake_client):
        res = listar_processos_iniciar_execucao(driver)

    assert [p["id"] for p in res] == [201]
    driver.page.evaluate.assert_called_once()


def test_buscar_processos_por_tarefa_401_dispara_permission_error():
    from Fix.variaveis import PjeApiClient

    client = PjeApiClient(MagicMock(), "pje.trt2.jus.br")
    with patch.object(
        client,
        "gateway_patch",
        return_value={"ok": False, "status": 401, "data": None, "error": {"message": "401"}},
    ):
        with pytest.raises(PermissionError, match="sessao_expirada_401"):
            client.buscar_processos_por_tarefa("Iniciar Execução")


def test_executar_cpcumprir_lista_vazia():
    from Prazo.p2b_cpcumprir import executar_cpcumprir

    driver = MagicMock()
    with patch("Prazo.p2b_cpcumprir.listar_processos_iniciar_execucao", return_value=[]):
        res = executar_cpcumprir(driver)

    assert res == {"sucesso": True, "total": 0, "processados": 0, "falhas": []}


def test_executar_cpcumprir_sequencia_completa():
    """Valida a ordem exata: abrir tarefa -> clicar Iniciar execução -> fechar aba -> /detalhe -> criar_gigs -> ato_cp1."""
    from Prazo import p2b_cpcumprir as mod

    eventos = []

    class FakeBtn:
        def get_attribute(self, name):
            return "" if name == "class" else None

        def is_enabled(self):
            return True

    class FakeSwitch:
        def __init__(self, drv):
            self._drv = drv

        def window(self, handle):
            eventos.append(("switch_window", handle))
            self._drv.current_window_handle = handle

    class FakeDriver:
        def __init__(self):
            self.current_window_handle = "aba_detalhe"
            self.current_url = "https://pje.trt2.jus.br/pjekz/processo/999/detalhe"
            self.switch_to = FakeSwitch(self)

        def get(self, url):
            eventos.append(("get", url))
            self.current_url = url

    driver = FakeDriver()
    fake_client = MagicMock()
    fake_client.trt_host = "pje.trt2.jus.br"
    fake_client.gateway_get.return_value = {
        "ok": True,
        "status": 200,
        "data": [{"idTarefa": 555, "nomeTarefa": "Iniciar Execução"}],
        "error": None,
    }

    def fake_abrir_nova_aba(drv, url, timeout=15):
        eventos.append(("abrir_nova_aba", url))
        drv.current_window_handle = "aba_tarefa"
        drv.current_url = url
        return "aba_tarefa"

    def fake_safe_click(drv, el):
        eventos.append(("clicar_iniciar_execucao", drv.current_window_handle))
        return True

    def fake_fechar_extras(drv, principal=None):
        eventos.append(("fechar_aba_tarefa", principal))
        drv.current_window_handle = principal

    def fake_criar_gigs(drv, dias_uteis=None, responsavel=None, observacao=None, **kwargs):
        eventos.append(("criar_gigs", dias_uteis, responsavel, observacao, drv.current_window_handle))
        return True

    def fake_ato_cp1(drv):
        eventos.append(("ato_cp1", drv.current_window_handle))
        return (True, False)

    def fake_lote(drv, itens, spec):
        assert len(itens) == 1
        r = spec.executar(drv, itens[0])
        assert r["ok"] is True
        return {
            "sucesso": True,
            "processados": 1,
            "falhas": [],
            "critical_stop": False,
            "critical_reason": None,
        }

    with (
        patch("Prazo.p2b_cpcumprir.listar_processos_iniciar_execucao", return_value=[{"id": 999, "numero": "1000999-10.2026.5.02.0703"}]),
        patch("Prazo.p2b_cpcumprir._criar_api_client", return_value=fake_client),
        patch("Prazo.p2b_cpcumprir.abrir_url_nova_aba", side_effect=fake_abrir_nova_aba),
        patch("Prazo.p2b_cpcumprir.garantir_carregamento_pagina", return_value=True),
        patch("Prazo.p2b_cpcumprir.aguardar_renderizacao_nativa", return_value=True),
        patch("Prazo.p2b_cpcumprir.espera.elemento", return_value=FakeBtn()),
        patch("Prazo.p2b_cpcumprir.espera.ate_sumir", return_value=True),
        patch("Prazo.p2b_cpcumprir.espera.assentar", return_value=None),
        patch("Prazo.p2b_cpcumprir.safe_click_no_scroll", side_effect=fake_safe_click),
        patch("Prazo.p2b_cpcumprir.fechar_abas_extras", side_effect=fake_fechar_extras),
        patch("Prazo.p2b_cpcumprir.url_processo_detalhe", side_effect=lambda pid: f"https://pje.trt2.jus.br/pjekz/processo/{pid}/detalhe"),
        patch("Fix.extracao.criar_gigs", side_effect=fake_criar_gigs),
        patch("atos.wrappers_ato.ato_cp1", side_effect=fake_ato_cp1),
        patch("Prazo.p2b_cpcumprir.executar_fluxo_lote", side_effect=fake_lote),
    ):
        res = mod.executar_cpcumprir(driver)

    assert res["sucesso"] is True
    assert res["total"] == 1
    assert res["processados"] == 1
    assert eventos == [
        ("abrir_nova_aba", "https://pje.trt2.jus.br/pjekz/processo/999/tarefa/555"),
        ("clicar_iniciar_execucao", "aba_tarefa"),
        ("fechar_aba_tarefa", "aba_detalhe"),
        ("get", "https://pje.trt2.jus.br/pjekz/processo/999/detalhe"),
        ("criar_gigs", "1", "", "xs1", "aba_detalhe"),
        ("criar_gigs", "1", "", "xs pec cp", "aba_detalhe"),
        ("ato_cp1", "aba_detalhe"),
    ]


def test_cpcumprir_falha_iniciar_execucao_fecha_aba_e_nao_roda_passo3():
    from Prazo import p2b_cpcumprir as mod

    driver = MagicMock()
    driver.current_window_handle = "aba_detalhe"
    fake_client = MagicMock()
    fake_client.trt_host = "pje.trt2.jus.br"
    fake_client.gateway_get.return_value = {
        "ok": True,
        "status": 200,
        "data": [{"idTarefa": 777}],
        "error": None,
    }

    with (
        patch("Prazo.p2b_cpcumprir._criar_api_client", return_value=fake_client),
        patch("Prazo.p2b_cpcumprir.abrir_url_nova_aba", return_value="aba_tarefa"),
        patch("Prazo.p2b_cpcumprir.garantir_carregamento_pagina", return_value=True),
        patch("Prazo.p2b_cpcumprir.aguardar_renderizacao_nativa", return_value=False),
        patch("Prazo.p2b_cpcumprir.espera.elemento", return_value=None),
        patch("atos.movimentos_navegacao.clicar_botao_por_texto", return_value=False),
        patch("Prazo.p2b_cpcumprir.fechar_abas_extras") as mock_fechar,
        patch("Fix.extracao.criar_gigs") as mock_gigs,
        patch("atos.wrappers_ato.ato_cp1") as mock_ato,
    ):
        res = mod._executar_processo_cpcumprir(driver, {"id": 888, "numero": "1000888-10.2026.5.02.0703"})

    assert res["ok"] is False
    assert res["erro"] == "falha_iniciar_execucao"
    mock_fechar.assert_called_once_with(driver, "aba_detalhe")
    mock_gigs.assert_not_called()
    mock_ato.assert_not_called()


def test_executar_p2b_chama_cpcumprir_apos_xs1():
    """Em x.executar_p2b, CPcumprir roda imediatamente após finalizar o xs1."""
    import x

    ordem = []

    def fake_xs1(drv, tamanho_pagina=100, max_processos=0):
        ordem.append("xs1")
        return {"sucesso": True, "total": 0, "processados": 0, "falhas": [], "critical_stop": False}

    def fake_cp(drv, tamanho_pagina=100, max_processos=0):
        ordem.append("cpcumprir")
        return {"sucesso": True, "total": 2, "processados": 2, "falhas": [], "critical_stop": False}

    driver = MagicMock()
    with (
        patch.object(x, "testar_gigs_sem_prazo", return_value=[]),
        patch.object(x, "processar_gigs_sem_prazo_p2b", side_effect=fake_xs1),
        patch("Prazo.p2b_cpcumprir.executar_cpcumprir", side_effect=fake_cp),
    ):
        res = x.executar_p2b(driver, motor_api=False)

    assert ordem == ["xs1", "cpcumprir"]
    assert res["sucesso"] is True
    assert res["detalhes"]["cpcumprir"]["processados"] == 2
