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
    def _analise_livres_stub(drv, *, tag="[PRAZO][ANALISE_LIVRES]"):
        estado["eventos"].append(("analise_livres", estado["painel"]))
        return {
            "ok": True,
            "total_livres": 0,
            "movidos_aguardando_prazo": [],
            "gigs_xs1_criadas": [],
            "falhas_movimento": [],
            "falhas_gigs": [],
            "sem_status_transicao": [],
            "diagnostico": {},
        }

    monkeypatch.setattr(lo, "safe_click_no_scroll", _clicar)
    monkeypatch.setattr(lo, "safe_click", _clicar)
    monkeypatch.setattr(lo, "ciclo_analise_livres", _analise_livres_stub)

    return _DriverObservavel(), estado


def test_ciclo0_e_ciclo3_dom_executam_em_ordem_exata(monkeypatch):
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

    assert lo.ciclo0(driver) is True
    assert lo.ciclo3(driver) is True

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

    assert lo.ciclo0(driver) is True
    assert lo.ciclo3(driver) is True
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

    assert lo.ciclo3(driver) is True
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

    assert lo.ciclo0(driver) is True
    assert lo.ciclo3(driver) is True
    tipos = [ev[0] for ev in estado["eventos"]]
    assert "salvar_xs1" not in tipos
    assert tipos.count("selecionar_livres") == 2


def test_falha_em_prazos_vencidos_dom_retorna_false(monkeypatch):
    driver, estado = _patch_ambiente(
        monkeypatch,
        {
            "vencidos": {"paginacao_inicial": "1 - 20 de 30", "filtrofases_ok": False},
            "cumprimento": {"paginacao_inicial": "1 - 20 de 30"},
        },
        selecoes_por_chamada=[],
    )

    assert lo.ciclo0(driver) is False
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


def test_filtro_100_nao_finalizado_bloqueia_disparo_de_xs1(monkeypatch):
    """Regressão: se filtro 100 não atualizar a paginação (>20), xs1 não pode ser disparado."""
    driver, estado = _patch_ambiente(
        monkeypatch,
        {
            "vencidos": {
                "paginacao_inicial": "1 - 20 de 60",
                "paginacao_pos_fases": "1 - 20 de 60",
                "paginacao_pos_100": "1 - 20 de 60",  # não atualizou para 1 - 60 de 60
            },
            "cumprimento": {"vazio_inicial": True},
        },
        selecoes_por_chamada=[5],
    )

    assert lo.ciclo0(driver) is False
    tipos = [ev[0] for ev in estado["eventos"]]
    assert "aplicar_filtro_100" in tipos
    assert "selecionar_livres" not in tipos
    assert "salvar_xs1" not in tipos


def test_xs1_so_dispara_apos_tabela_100_terminar_renderizacao_e_spinner_sumir(monkeypatch):
    """Regressão: seleção e xs1 aguardam spinner sumir e todas as 60 linhas renderizarem."""
    driver, estado = _patch_ambiente(
        monkeypatch,
        {
            "vencidos": {
                "paginacao_inicial": "1 - 20 de 60",
                "paginacao_pos_fases": "1 - 20 de 60",
                "paginacao_pos_100": "1 - 60 de 60",
            },
            "cumprimento": {"vazio_inicial": True},
        },
        selecoes_por_chamada=[3],
    )

    # Simula 2 ciclos de carregamento: 1º com spinner e 20 linhas, 2º sem spinner e 40 linhas, 3º pronto com 60 linhas
    fases_dom = [
        {"spinner": True, "linhas": 20},
        {"spinner": False, "linhas": 40},
        {"spinner": False, "linhas": 60},
    ]
    idx_dom = {"i": 0}
    orig_elemento = lo.espera.elemento
    orig_exec_js = lo._executar_js

    def _ate_iterativo(drv, condicao, teto=10, intervalo=0.05):
        for _ in range(10):
            res = condicao(drv)
            if res:
                return res
            if idx_dom["i"] < len(fases_dom) - 1:
                idx_dom["i"] += 1
        return False

    def _elemento_com_spinner(drv, seletor, teto=10, visivel=True):
        if seletor == lo._SEL_SPINNERS and estado["filtro_100"]:
            return _FakeElement("spin") if fases_dom[idx_dom["i"]]["spinner"] else None
        return orig_elemento(drv, seletor, teto=teto, visivel=visivel)

    def _exec_js_linhas(drv, script, *args):
        if "querySelectorAll('tr.cdk-drag').length" in script and estado["filtro_100"]:
            return fases_dom[idx_dom["i"]]["linhas"]
        return orig_exec_js(drv, script, *args)

    monkeypatch.setattr(lo.espera, "ate", _ate_iterativo)
    monkeypatch.setattr(lo.espera, "elemento", _elemento_com_spinner)
    monkeypatch.setattr(lo, "_executar_js", _exec_js_linhas)

    assert lo.ciclo0(driver) is True
    assert idx_dom["i"] == 2
    assert any(ev[0] == "salvar_xs1" for ev in estado["eventos"])


def test_loop_prazo_4_etapas_100_porcento_api(monkeypatch):
    """Fluxo Prazo completo via API: Vencidos→Análise, Análise não-livres→Cumprimento, Análise livres→Ag.Prazo/xs1, Cumprimento livres→xs1."""
    import Fix.variaveis as fv
    import api.filtro_analise as fa

    eventos = []

    class _ClientFake:
        def listar_agrupamento_processos(self, id_agrup, *, fases=None, id_tarefa=None, **kw):
            eventos.append(("listar", id_agrup, list(fases) if fases else None, id_tarefa))
            if id_agrup == fa.ID_AGRUPAMENTO_PRAZOS_VENCIDOS:
                return [{"id": 10, "numeroProcesso": "0000010", "idTarefa": 511, "faseProcessual": "Execução"}]
            if id_agrup == fa.ID_AGRUPAMENTO_ANALISE:
                return [
                    {"id": 20, "numeroProcesso": "0000020", "idTarefa": 500, "faseProcessual": "Execução", "temComentario": True, "idOrgaoJulgador": 187},
                    {"id": 21, "numeroProcesso": "0000021", "idTarefa": 500, "faseProcessual": "Liquidação", "idOrgaoJulgador": 187},
                    {"id": 22, "numeroProcesso": "0000022", "idTarefa": 500, "faseProcessual": "Execução", "idOrgaoJulgador": 187},
                    {"id": 23, "numeroProcesso": "0000023", "idTarefa": 500, "faseProcessual": "Execução", "isPeticaoNaoApreciada": True, "idOrgaoJulgador": 187},
                    {"id": 24, "numeroProcesso": "0000024", "idTarefa": 500, "faseProcessual": "Execução", "dataPrazoFinal": "2026-11-27", "idOrgaoJulgador": 187},
                ]
            if id_agrup == fa.ID_AGRUPAMENTO_CUMPRIMENTO:
                return [
                    {"id": 30, "numeroProcesso": "0000030", "idTarefa": 491, "faseProcessual": "Execução", "idOrgaoJulgador": 187},
                    {"id": 31, "numeroProcesso": "0000031", "idTarefa": 491, "faseProcessual": "Conhecimento", "dataPrazoFinal": "2026-12-01", "idOrgaoJulgador": 187},
                ]
            return []

        def tipos_atividades_gigs_lote(self, ids, **kw):
            return {24: ["Prazo"]} if 24 in ids else {}

        def atividades_gigs(self, pid):
            if str(pid) == "24":
                return [{"id": 999, "observacao": "xs1"}]
            return []

        def transicoes_tarefa(self, pid, tid, **kw):
            return [{"nomeTransicaoDestino": "Aguardando prazo", "transicaoDisponivel": pid == 21}]

        def movimentar_tarefa_lote_api(self, pid, tid, destino, **kw):
            eventos.append(("movimentar", pid, tid, destino))
            return {"ok": True, "id_tarefa_destino": 500, "nome_tarefa_destino": destino}

        def criar_atividade_gigs_api(self, pid, obs, *, dias=-1, id_oj=None, **kw):
            eventos.append(("gigs", pid, dias, obs, id_oj))
            return {"ok": True, "id": 9000 + pid, "dataPrazo": "2026-11-27"}

    monkeypatch.setattr(fv, "cliente_para", lambda drv, grau=1: _ClientFake())
    monkeypatch.setattr(fa, "_buscar_ids_escaninho_nao_apreciados", lambda client, **kw: set())

    res = lo.loop_prazo(_FakeDriver())
    assert res.sucesso is True
    assert res.status == "OK"
    assert res.detalhes["prazos_vencidos"]["movidos"] == ["0000010"]
    assert res.detalhes["analise_nao_livres"]["movidos"] == ["0000020"]
    assert res.detalhes["analise_livres"]["movidos_aguardando_prazo"] == ["0000021"]
    assert res.detalhes["analise_livres"]["gigs_xs1_criadas"] == ["0000022"]
    assert res.detalhes["cumprimento_providencias"]["gigs_xs1_criadas"] == ["0000030"]
    # Processo 23 (doc não apreciado) e Processo 24 (apenas GIGS xs1) não podem ter sido movidos nem recebido GIGS
    assert all(ev[1] not in (23, 24) for ev in eventos if ev[0] in ("movimentar", "gigs"))
    assert ("movimentar", 10, 511, "Análise") in eventos
    assert ("movimentar", 20, 500, "Cumprimento de providências") in eventos
    assert ("movimentar", 21, 500, "Aguardando prazo") in eventos
    assert ("gigs", 22, -1, "xs1", 187) in eventos
    assert ("gigs", 30, -1, "xs1", 187) in eventos


def test_ciclo_analise_livres_legado_despacha_acoes(monkeypatch):
    """Compatibilidade: ciclo_analise_livres continua funcionando se chamado isoladamente."""
    from unittest.mock import MagicMock
    import Fix.variaveis as fv
    import api.filtro_analise as fa

    p_disp = fa.ProcessoAnaliseFiltrado(
        id_processo=101,
        numero_processo="0000101-00.2026.5.02.0703",
        fase_processual="Execução",
        id_tarefa=500,
        tarefa="Análise",
        aguardando_prazo_disponivel=True,
        estado_aguardando_prazo="disponivel",
    )
    p_indisp = fa.ProcessoAnaliseFiltrado(
        id_processo=202,
        numero_processo="0000202-00.2026.5.02.0703",
        fase_processual="Liquidação",
        id_tarefa=500,
        tarefa="Análise",
        aguardando_prazo_disponivel=False,
        estado_aguardando_prazo="indisponivel",
    )

    fake_client = MagicMock()
    fake_client.transitar_tarefa_processo.return_value = {
        "ok": True,
        "id_tarefa_destino": 510,
        "nome_tarefa_destino": "Aguardando prazo",
    }
    chamadas_gigs = []

    monkeypatch.setattr(fv, "cliente_para", lambda drv, grau=1: fake_client)
    monkeypatch.setattr(
        fa,
        "filtrar_processos_analise_livres",
        lambda client, **kwargs: ([p_disp, p_indisp], {"ok": True}),
    )
    monkeypatch.setattr(
        lo,
        "_criar_gigs_1_xs1_no_processo",
        lambda drv, pid, num, tag: (chamadas_gigs.append((pid, num)), True)[1],
    )

    res = lo.ciclo_analise_livres(_FakeDriver())
    assert res["ok"] is True
    assert res["movidos_aguardando_prazo"] == ["0000101-00.2026.5.02.0703"]
    assert res["gigs_xs1_criadas"] == ["0000202-00.2026.5.02.0703"]
    fake_client.transitar_tarefa_processo.assert_called_once_with(
        101, 500, "Aguardando prazo", verificar_bloqueio=True
    )
    assert chamadas_gigs == [(202, "0000202-00.2026.5.02.0703")]
