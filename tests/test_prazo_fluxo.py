"""Testes unitários do fluxo Prazo simplificado (7 etapas sequenciais com barreiras)."""
import Prazo.loop_orquestrador as lo


class _FakeElement:
    def __init__(self, text="", attrs=None):
        self.text = text
        self._attrs = dict(attrs or {})

    def get_attribute(self, nome):
        return self._attrs.get(nome)


class _FakeDriver:
    def __init__(self):
        self.current_url = ""
        self.eventos = []

    def get(self, url):
        self.current_url = url
        self.eventos.append(("get", url))


def _patch_ambiente(monkeypatch, estado_por_painel, *, selecoes_por_chamada=None, xs_ok=True):
    """Configura mocks mínimos e observáveis das barreiras Playwright do orquestrador."""
    estado = {
        "painel": None,
        "paginacao": "",
        "filtro_100": False,
        "vazio": False,
        "selecoes": list(selecoes_por_chamada or []),
        "eventos": [],
    }

    def _carregar_painel(url):
        if "painel/global/14" in url:
            chave = "vencidos"
        elif "painel/global/6" in url:
            chave = "cumprimento"
        else:
            chave = "outro"
        cfg = estado_por_painel[chave]
        estado["painel"] = chave
        estado["vazio"] = bool(cfg.get("vazio_inicial", False))
        estado["paginacao"] = cfg.get("paginacao_inicial", "1 - 20 de 40")
        estado["filtro_100"] = bool(cfg.get("filtro_100_inicial", False))

    class _DriverObservavel(_FakeDriver):
        def get(self, url):
            super().get(url)
            estado["eventos"].append(("get", url))
            _carregar_painel(url)

    def _ate(drv, condicao, teto=10, intervalo=0.05):
        return condicao(drv)

    def _ate_url(drv, trecho, teto=10):
        return trecho in (drv.current_url or "")

    def _ate_sumir(drv, seletor, teto=2.0):
        return True

    def _ate_aparecer(drv, seletor, teto=2.0):
        if seletor == "tr.cdk-drag":
            return not estado["vazio"]
        return True

    def _ate_js(drv, expressao, teto=2.0):
        return True

    def _elemento(drv, seletor, teto=10, visivel=True):
        if seletor == lo._XPATH_LISTA_VAZIA:
            return _FakeElement("Não há processos neste tema") if estado["vazio"] else None
        if seletor == "span.total-registros":
            return _FakeElement(estado["paginacao"]) if estado["paginacao"] else None
        if seletor in ("tr.cdk-drag", "tbody tr.tr-class"):
            return None if estado["vazio"] else _FakeElement("row")
        if seletor == lo._SEL_SPINNERS:
            return None
        if seletor == lo._XPATH_FILTRO_100_ATIVO:
            return _FakeElement("100") if estado["filtro_100"] else None
        if seletor in ('button[aria-label="Próximo"]', 'mat-paginator button[aria-label="Próxima página"]'):
            cfg = estado_por_painel[estado["painel"]]
            prox = cfg.get("proximas_paginas", [])
            if prox:
                return _FakeElement("next", attrs={"aria-disabled": "false"})
            return _FakeElement("next", attrs={"disabled": "true"})
        if seletor == "i.fa.fa-tag.icone.texto-verde":
            return _FakeElement("tag")
        return _FakeElement(seletor)

    def _elementos(drv, seletor, teto=10):
        if seletor == "button.mat-menu-item":
            return [_FakeElement("Outra"), _FakeElement("Atividade")]
        if "mat-raised-button" in seletor:
            return [_FakeElement("Cancelar"), _FakeElement("Salvar")]
        return []

    def _buscar(drv, chave, seletores, **kwargs):
        return _FakeElement(chave)

    def _filtrofases(drv, fases_alvo=None):
        estado["eventos"].append(("filtrofases", list(fases_alvo or [])))
        cfg = estado_por_painel[estado["painel"]]
        if cfg.get("vazio_pos_fases"):
            estado["vazio"] = True
            estado["paginacao"] = "0 de 0"
        elif "paginacao_pos_fases" in cfg:
            estado["paginacao"] = cfg["paginacao_pos_fases"]
        return cfg.get("filtrofases_ok", True)

    def _aplicar_100(drv):
        estado["eventos"].append(("aplicar_filtro_100", estado["painel"]))
        estado["filtro_100"] = True
        cfg = estado_por_painel[estado["painel"]]
        if "paginacao_pos_100" in cfg:
            estado["paginacao"] = cfg["paginacao_pos_100"]
        return cfg.get("filtro100_ok", True)

    def _executar_js(drv, script, *args):
        if "querySelectorAll('tr.cdk-drag').length" in script:
            return max(1, lo._ler_esperado_na_pagina(drv))
        qtd = estado["selecoes"].pop(0) if estado["selecoes"] else 0
        estado["eventos"].append(("selecionar_livres", estado["painel"], estado["paginacao"], qtd))
        return qtd

    def _preencher(drv, seletor, valor):
        estado["eventos"].append(("preencher", seletor, valor))
        return True

    def _clicar(drv, el):
        if getattr(el, "text", "") == "next":
            cfg = estado_por_painel[estado["painel"]]
            prox = cfg.get("proximas_paginas", [])
            if prox:
                nova = prox.pop(0)
                estado["paginacao"] = nova
                estado["eventos"].append(("proxima_pagina", estado["painel"], nova))
        elif getattr(el, "text", "") in ("Salvar", "btn_salvar_pai"):
            estado["eventos"].append(("salvar_xs1", estado["painel"], estado["paginacao"]))
            return xs_ok
        return True

    monkeypatch.setattr(lo.espera, "ate", _ate)
    monkeypatch.setattr(lo.espera, "ate_url", _ate_url)
    monkeypatch.setattr(lo.espera, "ate_sumir", _ate_sumir)
    monkeypatch.setattr(lo.espera, "ate_aparecer", _ate_aparecer)
    monkeypatch.setattr(lo.espera, "ate_js", _ate_js)
    monkeypatch.setattr(lo.espera, "assentar", lambda drv, teto=1.0, motivo="": True)
    monkeypatch.setattr(lo.espera, "pausa", lambda drv, seg=0.1, motivo="": True)
    monkeypatch.setattr(lo.espera, "elemento", _elemento)
    monkeypatch.setattr(lo.espera, "elementos", _elementos)
    monkeypatch.setattr(lo, "buscar", _buscar)
    monkeypatch.setattr(lo, "filtrofases", _filtrofases)
    monkeypatch.setattr(lo, "aplicar_filtro_100", _aplicar_100)
    monkeypatch.setattr(lo, "_executar_js", _executar_js)
    monkeypatch.setattr(lo, "preencher_campo", _preencher)
    monkeypatch.setattr(lo, "safe_click_no_scroll", _clicar)
    monkeypatch.setattr(lo, "safe_click", _clicar)

    return _DriverObservavel(), estado


def test_loop_prazo_executa_7_etapas_em_ordem_exata(monkeypatch):
    driver, estado = _patch_ambiente(
        monkeypatch,
        {
            "vencidos": {
                "paginacao_inicial": "1 - 20 de 60",
                "paginacao_pos_fases": "1 - 20 de 35",
                "paginacao_pos_100": "1 - 35 de 35",
            },
            "cumprimento": {
                "paginacao_inicial": "1 - 20 de 45",
                "paginacao_pos_100": "1 - 45 de 45",
            },
        },
        selecoes_por_chamada=[4, 3],
    )

    res = lo.loop_prazo(driver)

    assert res.sucesso is True
    assert res.status == "OK"
    assert res.detalhes["prazos_vencidos"] is True
    assert res.detalhes["cumprimento_providencias"] is True

    marcos = [
        ev for ev in estado["eventos"]
        if ev[0] in ("get", "filtrofases", "aplicar_filtro_100", "selecionar_livres", "salvar_xs1")
    ]
    assert marcos == [
        ("get", lo.URL_PAINEL_PRAZOS_VENCIDOS),
        ("filtrofases", ["liquidação", "execução"]),
        ("aplicar_filtro_100", "vencidos"),
        ("selecionar_livres", "vencidos", "1 - 35 de 35", 4),
        ("salvar_xs1", "vencidos", "1 - 35 de 35"),
        ("get", lo.URL_PAINEL_CUMPRIMENTO),
        ("aplicar_filtro_100", "cumprimento"),
        ("selecionar_livres", "cumprimento", "1 - 45 de 45", 3),
        ("salvar_xs1", "cumprimento", "1 - 45 de 45"),
    ]
    preenchimentos = [ev for ev in estado["eventos"] if ev[0] == "preencher"]
    assert any(v == "-1" for _, _, v in preenchimentos)
    assert any(v == "xs1" for _, _, v in preenchimentos)


def test_painel_vazio_encerra_cedo_sem_filtro_100_nem_xs1(monkeypatch):
    driver, estado = _patch_ambiente(
        monkeypatch,
        {
            "vencidos": {"paginacao_inicial": "1 - 20 de 15", "vazio_pos_fases": True},
            "cumprimento": {"vazio_inicial": True, "paginacao_inicial": "0 de 0"},
        },
        selecoes_por_chamada=[],
    )

    res = lo.loop_prazo(driver)

    assert res.sucesso is True
    tipos = [ev[0] for ev in estado["eventos"]]
    assert "aplicar_filtro_100" not in tipos
    assert "selecionar_livres" not in tipos
    assert "salvar_xs1" not in tipos
    assert tipos == ["get", "filtrofases", "get"]


def test_multipagina_aplica_xs1_por_pagina_com_barreira_de_paginacao(monkeypatch):
    driver, estado = _patch_ambiente(
        monkeypatch,
        {
            "vencidos": {"vazio_inicial": True},
            "cumprimento": {
                "paginacao_inicial": "1 - 20 de 140",
                "paginacao_pos_100": "1 - 100 de 140",
                "proximas_paginas": ["101 - 140 de 140"],
            },
        },
        selecoes_por_chamada=[5, 2],
    )

    res = lo.loop_prazo(driver)

    assert res.sucesso is True
    acoes_cumprimento = [
        ev for ev in estado["eventos"]
        if ev[0] in ("selecionar_livres", "salvar_xs1", "proxima_pagina")
    ]
    assert acoes_cumprimento == [
        ("selecionar_livres", "cumprimento", "1 - 100 de 140", 5),
        ("salvar_xs1", "cumprimento", "1 - 100 de 140"),
        ("proxima_pagina", "cumprimento", "101 - 140 de 140"),
        ("selecionar_livres", "cumprimento", "101 - 140 de 140", 2),
        ("salvar_xs1", "cumprimento", "101 - 140 de 140"),
    ]


def test_zero_livres_pula_criacao_xs1(monkeypatch):
    driver, estado = _patch_ambiente(
        monkeypatch,
        {
            "vencidos": {"paginacao_inicial": "1 - 10 de 10", "filtro_100_inicial": True},
            "cumprimento": {"paginacao_inicial": "1 - 8 de 8", "filtro_100_inicial": True},
        },
        selecoes_por_chamada=[0, 0],
    )

    res = lo.loop_prazo(driver)

    assert res.sucesso is True
    tipos = [ev[0] for ev in estado["eventos"]]
    assert "salvar_xs1" not in tipos
    assert tipos.count("selecionar_livres") == 2


def test_falha_em_prazos_vencidos_aborta_antes_de_cumprimento(monkeypatch):
    driver, estado = _patch_ambiente(
        monkeypatch,
        {
            "vencidos": {"paginacao_inicial": "1 - 20 de 30", "filtrofases_ok": False},
            "cumprimento": {"paginacao_inicial": "1 - 20 de 30"},
        },
        selecoes_por_chamada=[],
    )

    res = lo.loop_prazo(driver)

    assert res.sucesso is False
    assert res.status == "FALHA"
    assert res.detalhes["prazos_vencidos"] is False
    assert res.detalhes["cumprimento_providencias"] is False
    urls = [ev[1] for ev in estado["eventos"] if ev[0] == "get"]
    assert urls == [lo.URL_PAINEL_PRAZOS_VENCIDOS]


def test_espera_elemento_nao_herda_implicito_de_pwdriver():
    """Regressão: espera.elemento(..., teto=0.0) deve desativar implicito_em_find_elements."""
    from Fix import espera

    estados_observados = []

    class _DriverComImplicito:
        def __init__(self):
            self.implicito_em_find_elements = True

        def find_elements(self, by, seletor):
            estados_observados.append(self.implicito_em_find_elements)
            return []

    drv = _DriverComImplicito()
    achado = espera.elemento(drv, "//span[contains(text(), 'Não há processos neste tema')]", teto=0.0)

    assert achado is None
    assert estados_observados == [False]
    assert drv.implicito_em_find_elements is True


def test_filtrofases_usa_seletores_validos_e_clica_filtrar(monkeypatch):
    """Regressão: filtrofases deve usar aria-label de fase e CSS puro para Filtrar."""
    import Fix.filtros_painel as fp

    seletores_espera = []
    cliques = []

    class _FakeBtn:
        def __init__(self, nome):
            self.nome = nome

    class _DriverFiltro:
        def execute_script(self, script, *args):
            if ".filter(function(t)" in script or "mat-option" in script and not args:
                return ["conhecimento", "liquidação", "execução"]
            return len(args[0]) if args else 2

    monkeypatch.setattr(
        fp,
        "aguardar_e_clicar",
        lambda d, sel, timeout=10, usar_js=True: (seletores_espera.append(sel), True)[1],
    )
    monkeypatch.setattr(fp, "aguardar_renderizacao_nativa", lambda d, *a, **kw: True)
    monkeypatch.setattr(fp, "_fechar_dropdown_ou_esc", lambda d: True)
    monkeypatch.setattr(fp, "_aguardar_loader_painel", lambda d, timeout=10: True)

    def _elemento(d, sel, teto=2, visivel=True):
        seletores_espera.append(sel)
        assert not (", //" in sel), f"Seletor mistura CSS e XPath: {sel}"
        if "button[aria-label='Filtrar']" in sel:
            return _FakeBtn("filtrar")
        return None

    monkeypatch.setattr(fp.espera, "elemento", _elemento)
    monkeypatch.setattr(fp, "safe_click_no_scroll", lambda d, el: (cliques.append(el.nome), True)[1])

    assert fp.filtrofases(_DriverFiltro(), fases_alvo=["liquidação", "execução"]) is True
    assert any('mat-select[aria-label*="Fase processual"]' in s for s in seletores_espera)
    assert cliques == ["filtrar"]


def test_login_cpf_reutiliza_cookies_salvos_em_driver_novo(monkeypatch):
    """Regressão: driver recém-criado (sem cookies em memória) deve tentar verificar_e_aplicar_cookies."""
    import Fix.sessao as sessao

    chamadas = []

    class _DriverNovo:
        def get_cookies(self):
            return []

        def delete_all_cookies(self):
            chamadas.append("delete_all_cookies")

    monkeypatch.setattr(sessao, "verificar_e_aplicar_cookies", lambda d: (chamadas.append("verificar_cookies"), True)[1])
    monkeypatch.setattr(sessao, "salvar_cookies_sessao", lambda d, **kw: chamadas.append("salvar_cookies"))

    assert sessao.login_cpf(_DriverNovo()) is True
    assert chamadas == ["verificar_cookies", "salvar_cookies"]


def test_inicar_exec_fallback_para_ato_pesqliq_quando_iniciar_execucao_indisponivel(monkeypatch):
    """Regressão: se credito_mock falha e botão 'Iniciar execução' não existe (fase em Liquidação), usa ato_pesqliq."""
    import Prazo.p2b_gateway as gw
    import Fix.core as core

    atos_chamados = []

    monkeypatch.setattr(
        gw,
        "_lazy_import",
        lambda: {
            "criar_gigs": lambda *a, **kw: True,
            "ato_pesquisas": lambda *a, **kw: (atos_chamados.append("ato_pesquisas"), (True, True))[1],
            "ato_pesqliq": lambda *a, **kw: (atos_chamados.append("ato_pesqliq"), (True, True))[1],
        },
    )
    monkeypatch.setattr(gw.espera, "ate_sumir", lambda *a, **kw: True)
    monkeypatch.setattr(core, "extrair_id_processo", lambda d: "7329484")
    monkeypatch.setattr(gw, "cliente_para", lambda d: object())
    monkeypatch.setattr(gw, "decidir_rota_iniciar_exec", lambda c, pid: "mock_pesquisas")
    monkeypatch.setattr(gw, "registrar_credito_mock_0_01", lambda d, pid: False)
    monkeypatch.setattr(gw, "_abrir_tarefa_e_tentar_iniciar_execucao", lambda d, timeout=10: False)
    monkeypatch.setattr(gw, "_abrir_tarefa", lambda d, timeout=10: True)

    res = gw.inicar_exec(_FakeDriver())
    assert res == (True, True)
    assert atos_chamados == ["ato_pesqliq"]


def test_inicar_exec_cria_gigs_pjdp_quando_passivo_tem_procuradoria_ou_nome_ente_publico(monkeypatch):
    """Se polo passivo tem PJDP (procuradoria ou cadastro incorreto), cria GIGS apenas com observacao."""
    import Prazo.p2b_gateway as gw
    import Fix.core as core

    casos = [
        ([{"nome": "MUNICIPIO DE SAO PAULO", "procuradoria": True}], True),
        ([{"nome": "ESTADO DE SAO PAULO", "procuradoria": False}], True),
        ([{"nome": "EMPRESA PRIVADA LTDA", "procuradoria": False}], False),
    ]

    for passivo, espera_gigs_pjdp in casos:
        gigs_chamadas = []

        class _ClientFake:
            def partes(self, pid):
                return {"ATIVO": [{"nome": "AUTOR"}], "PASSIVO": passivo}

        monkeypatch.setattr(
            gw,
            "_lazy_import",
            lambda: {
                "criar_gigs": lambda *a, **kw: (gigs_chamadas.append((a[1:], kw)), True)[1],
                "ato_pesquisas": lambda *a, **kw: (True, True),
                "ato_pesqliq": lambda *a, **kw: (True, True),
            },
        )
        monkeypatch.setattr(gw.espera, "ate_sumir", lambda *a, **kw: True)
        monkeypatch.setattr(core, "extrair_id_processo", lambda d: "7329484")
        monkeypatch.setattr(gw, "cliente_para", lambda d: _ClientFake())
        monkeypatch.setattr(gw, "decidir_rota_iniciar_exec", lambda c, pid: "pesquisas")
        monkeypatch.setattr(gw, "_abrir_tarefa", lambda d, timeout=10: True)

        res = gw.inicar_exec(_FakeDriver())
        assert res == (True, True)

        chamadas_pjdp = [
            (args, kw)
            for args, kw in gigs_chamadas
            if kw.get("observacao") == "PJDP no polo passivo, verificar"
        ]
        if espera_gigs_pjdp:
            assert chamadas_pjdp == [((), {"observacao": "PJDP no polo passivo, verificar"})]
        else:
            assert chamadas_pjdp == []
