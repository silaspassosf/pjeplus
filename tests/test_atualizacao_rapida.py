# -*- coding: utf-8 -*-
"""Testes offline da Atualização Rápida (réplica autônoma do +PJe).

Sem rede e sem browser: o driver Playwright é simulado. Cobre o contrato do
motor (data atual automática, sucesso só após "Sucesso!", ambiguidade sem
id_calculo, falha pós-envio sem reenvio) e a integração no orquestrador
(fluxo K, retry externo desligado para pos_envio).

Roda com:  python -m unittest tests.test_atualizacao_rapida
"""
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Backend Playwright no lugar do selenium ANTES de importar Fix.* (regra P9).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "play"))
import pjeplay  # noqa: E402
pjeplay.iniciar(raiz_projeto=os.path.join(os.path.dirname(__file__), ".."),
                nativo=False, silencioso=True)

from Fix import atualizacao_rapida as ar  # noqa: E402


def _import_x():
    """Importa o orquestrador neutralizando escritas de import-time legadas.

    `Mandado/entrada_api.py` grava um `log.py` de diagnóstico no import (bloco
    legado). Em sandbox esse write pode ser negado; aqui ele é irrelevante para
    o teste, então `builtins.open` em modo escrita viro no-op durante o import.
    """
    import builtins
    real_open = builtins.open

    def _open(file, mode="r", *a, **k):
        if isinstance(mode, str) and any(c in mode for c in "wax+"):
            return MagicMock()
        return real_open(file, mode, *a, **k)

    with patch.object(builtins, "open", _open):
        import x
    return x

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CNJ = "1001190-87.2024.5.02.0000"


def _driver(resultado_js=None, exc_eval=None):
    """Driver fake com page/context; a aba nova devolve `resultado_js`."""
    aba = MagicMock()
    aba.is_closed.return_value = False
    if exc_eval is not None:
        aba.evaluate.side_effect = exc_eval
    else:
        aba.evaluate.return_value = resultado_js
    context = MagicMock()
    context.new_page.return_value = aba
    page = MagicMock()
    page.evaluate.return_value = f"Processo {CNJ} — detalhe"
    driver = MagicMock()
    driver.page = page
    driver.context = context
    driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/6334837/detalhe"
    return driver, aba


class TestMotor(unittest.TestCase):
    def test_sucesso_usa_data_atual_e_fecha_aba(self):
        ok_js = {"ok": True, "numeroProcesso": CNJ, "numeroCalculo": "123",
                 "data": datetime.now().strftime("%d/%m/%Y")}
        driver, aba = _driver(resultado_js=ok_js)
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            ok = ar.executar_atualizacao_rapida(driver, CNJ)
        self.assertTrue(ok)
        # data atual injetada no cfg, sem confirmação
        cfg = aba.evaluate.call_args.args[1]
        self.assertEqual(cfg["data"], datetime.now().strftime("%d/%m/%Y"))
        self.assertEqual(cfg["numeroProcesso"], CNJ)
        self.assertIsNone(cfg["idCalculo"])
        aba.goto.assert_called_once()
        self.assertIn("/pjecalc/pages/principal.jsf", aba.goto.call_args.args[0])
        aba.close.assert_called_once()  # aba própria fechada ao terminar

    def test_data_explicita_respeitada(self):
        driver, aba = _driver(resultado_js={"ok": True, "numeroProcesso": CNJ,
                                            "numeroCalculo": "1", "data": "01/02/2025"})
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            ar.executar_atualizacao_rapida(driver, CNJ, data="01/02/2025")
        self.assertEqual(aba.evaluate.call_args.args[1]["data"], "01/02/2025")

    def test_id_calculo_repassado(self):
        driver, aba = _driver(resultado_js={"ok": True, "numeroProcesso": CNJ,
                                            "numeroCalculo": "7", "data": "01/01/2025"})
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            ar.executar_atualizacao_rapida(driver, CNJ, id_calculo="7")
        self.assertEqual(aba.evaluate.call_args.args[1]["idCalculo"], "7")

    def test_cnj_lido_da_pagina_quando_omitido(self):
        driver, aba = _driver(resultado_js={"ok": True, "numeroProcesso": CNJ,
                                            "numeroCalculo": "1", "data": "01/01/2025"})
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            ok = ar.executar_atualizacao_rapida(driver, None)
        self.assertTrue(ok)
        self.assertEqual(aba.evaluate.call_args.args[1]["numeroProcesso"], CNJ)

    def test_cnj_invalido_falha_sem_abrir_aba(self):
        driver, aba = _driver(resultado_js={"ok": True})
        driver.page.evaluate.return_value = "sem numero aqui"
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            with self.assertRaises(ar.AtualizacaoRapidaErro):
                ar.executar_atualizacao_rapida(driver, None)
        driver.context.new_page.assert_not_called()

    def test_data_invalida_falha(self):
        driver, _ = _driver(resultado_js={"ok": True})
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            with self.assertRaises(ar.AtualizacaoRapidaErro):
                ar.executar_atualizacao_rapida(driver, CNJ, data="2025-01-01")

    def test_falha_pre_envio_nao_pos_envio(self):
        driver, aba = _driver(resultado_js={"ok": False, "erro": "Processo sem cálculo registrado no PJeCalc.",
                                            "fase": "lista-calculos", "posEnvio": False})
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            with self.assertRaises(ar.AtualizacaoRapidaErro) as ctx:
                ar.executar_atualizacao_rapida(driver, CNJ)
        self.assertFalse(ctx.exception.pos_envio)
        aba.close.assert_called_once()

    def test_falha_pos_envio_marcada(self):
        driver, _ = _driver(resultado_js={"ok": False, "erro": "O envio ao PJe não confirmou sucesso (não reenviar).",
                                          "fase": "sucesso", "posEnvio": True})
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            with self.assertRaises(ar.AtualizacaoRapidaErro) as ctx:
                ar.executar_atualizacao_rapida(driver, CNJ)
        self.assertTrue(ctx.exception.pos_envio)

    def test_timeout_transporte_e_pos_envio(self):
        driver, aba = _driver(exc_eval=TimeoutError("evaluate timeout"))
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            with self.assertRaises(ar.AtualizacaoRapidaErro) as ctx:
                ar.executar_atualizacao_rapida(driver, CNJ)
        self.assertTrue(ctx.exception.pos_envio)  # estado desconhecido => não reenviar
        aba.close.assert_called_once()

    def test_retoma_apos_contexto_destruido_pre_efeito(self):
        """Regressão (log 22:59:56): PJeCalc navega no 1º segundo e derruba o
        contexto. Se o espelho mostra fase sem efeito (liquidar/enviar), o motor
        reassenta e reexecuta em vez de falhar o fluxo inteiro."""
        exc = RuntimeError("Page.evaluate: Execution context was destroyed, "
                           "most likely because of a navigation.")
        ok = {"ok": True, "numeroProcesso": CNJ, "numeroCalculo": "123",
              "data": "17/11/2026"}
        driver, aba = _driver(resultado_js=None)
        aba.evaluate.side_effect = [exc, "lista-calculos", ok]  # js → espelho → reexec
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            res = ar.executar_atualizacao_rapida_detalhada(driver, CNJ)
        self.assertTrue(res.sucesso)
        self.assertEqual(res.fase, "sucesso")
        self.assertEqual(aba.evaluate.call_count, 3)

    def test_nao_retoma_apos_liquidar_iniciado(self):
        """Espelho em 'liquidar' ou posterior = estado desconhecido: NÃO reexecuta
        (poderia duplicar a liquidação/envio). Marca pos_envio."""
        exc = RuntimeError("Page.evaluate: Execution context was destroyed, "
                           "most likely because of a navigation.")
        driver, aba = _driver(resultado_js=None)
        aba.evaluate.side_effect = [exc, "liquidar"]  # js → espelho('liquidar')
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            with self.assertRaises(ar.AtualizacaoRapidaErro) as ctx:
                ar.executar_atualizacao_rapida(driver, CNJ)
        self.assertTrue(ctx.exception.pos_envio)
        self.assertEqual(aba.evaluate.call_count, 2)  # 1 js + 1 espelho; sem reexecução

    def test_somente_busca_nao_liquida_nem_envia(self):
        """Modo de inspeção (f.py 'ar'): abre o cálculo, confere CNJ e para.
        Repassa somenteBusca no cfg e devolve fase 'somente-busca'."""
        driver, aba = _driver(resultado_js={"ok": True, "somenteBusca": True,
                                            "numeroProcesso": CNJ, "numeroCalculo": "7"})
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            res = ar.executar_atualizacao_rapida_detalhada(driver, CNJ, somente_busca=True)
        self.assertTrue(res.sucesso)
        self.assertEqual(res.fase, "somente-busca")
        self.assertEqual(res.numero_calculo, "7")
        self.assertTrue(aba.evaluate.call_args.args[1]["somenteBusca"])

    def test_somente_busca_default_off(self):
        driver, aba = _driver(resultado_js={"ok": True, "numeroProcesso": CNJ,
                                            "numeroCalculo": "1", "data": "01/01/2025"})
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            ar.executar_atualizacao_rapida(driver, CNJ)
        self.assertFalse(aba.evaluate.call_args.args[1]["somenteBusca"])

    def test_evaluate_sem_kwarg_timeout(self):
        """Regressão: Page.evaluate() não aceita timeout= (TypeError no log real)."""
        driver, aba = _driver(resultado_js={"ok": True, "numeroProcesso": CNJ,
                                           "numeroCalculo": "1", "data": "01/01/2025"})
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            ar.executar_atualizacao_rapida(driver, CNJ)
        # teto vai por set_default_timeout, nunca como kwarg do evaluate
        aba.set_default_timeout.assert_called_once_with(ar._TETO_EVAL_MS)
        self.assertNotIn("timeout", aba.evaluate.call_args.kwargs)

    def test_falha_ao_abrir_nao_e_pos_envio(self):
        """Regressão: erro antes de abrir/navegar não pode bloquear como pós-envio."""
        driver, aba = _driver(resultado_js={"ok": True})
        aba.goto.side_effect = RuntimeError("net::ERR_ABORTED")
        with patch.object(ar, "carregar_js", return_value="async (cfg) => ({})"):
            with self.assertRaises(ar.AtualizacaoRapidaErro) as ctx:
                ar.executar_atualizacao_rapida(driver, CNJ)
        self.assertFalse(ctx.exception.pos_envio)
        self.assertEqual(ctx.exception.fase, "abrir-pjecalc")
        aba.evaluate.assert_not_called()
        aba.close.assert_called_once()

    def test_js_carregado_do_disco(self):
        js = ar.carregar_js(ar._JS_NOME, pasta=ar._PASTA_JS)
        self.assertIn("Liquidar Atualização", js)
        self.assertIn("MAISPJE: ATUALIZAÇÃO RÁPIDA", js)
        self.assertIn("Sucesso!", js)


class TestIntegracaoOrquestrador(unittest.TestCase):
    def test_fluxo_k_registrado(self):
        x = _import_x()
        self.assertIn("K", x.FLOW_HANDLERS)
        self.assertIs(x.FLOW_HANDLERS["K"], x.executar_atualizacao_rapida_fluxo)

    def test_handler_sucesso(self):
        x = _import_x()
        driver = MagicMock()
        with patch.dict(os.environ, {"PJEPLUS_AR_PROCESSO": CNJ}, clear=False), \
             patch("Fix.atualizacao_rapida.executar_atualizacao_rapida", return_value=True):
            res = x.executar_atualizacao_rapida_fluxo(driver)
        self.assertTrue(res["sucesso"])
        self.assertFalse(res.get("pos_envio"))

    def test_handler_falha_pos_envio(self):
        x = _import_x()
        driver = MagicMock()
        erro = ar.AtualizacaoRapidaErro("envio desconhecido", fase="sucesso", pos_envio=True)
        with patch.dict(os.environ, {"PJEPLUS_AR_PROCESSO": CNJ}, clear=False), \
             patch("Fix.atualizacao_rapida.executar_atualizacao_rapida", side_effect=erro):
            res = x.executar_atualizacao_rapida_fluxo(driver)
        self.assertFalse(res["sucesso"])
        self.assertTrue(res["pos_envio"])

    def test_retry_externo_desligado_para_pos_envio(self):
        x = _import_x()
        driver = MagicMock()
        resultado = {"sucesso": False, "tempo": 0.1, "pos_envio": True}
        with patch.object(x, "FLOW_HANDLERS", {"K": lambda d: resultado}), \
             patch.object(x, "login_cpf") as login_cpf, \
             patch.object(x, "login_manual") as login_manual:
            res = x._executar_um_fluxo(driver, "K", x.DriverType.PC_HEADLESS)
        self.assertFalse(res["sucesso"])
        login_cpf.assert_not_called()   # não reloga/reexecuta após envio
        login_manual.assert_not_called()

    def test_retry_externo_ativo_para_falha_comum(self):
        x = _import_x()
        driver = MagicMock()
        resultado = {"sucesso": False, "tempo": 0.1, "pos_envio": False}
        with patch.object(x, "FLOW_HANDLERS", {"K": lambda d: resultado}), \
             patch.object(x, "login_cpf", return_value=False) as login_cpf, \
             patch.object(x, "_aguardar_sessao_ativa", return_value=False), \
             patch.object(x, "_aguardar_login_manual", return_value=False):
            x._executar_um_fluxo(driver, "K", x.DriverType.PC_HEADLESS)
        login_cpf.assert_called_once()  # falha pré-envio ainda tenta relogin


class TestIntegracaoTeimosinha(unittest.TestCase):
    """Elo PEC teimosinha: gap >3 meses → atualização → valor via API → minuta."""

    def _dados(self, data_divida, valor="R$ 1.000,00"):
        return {"numero": [CNJ], "id": "6334837",
                "divida": {"valor": valor, "data": data_divida}}

    def test_calculo_antigo_limiar(self):
        from datetime import timedelta
        antigo = (datetime.now() - timedelta(days=100)).strftime("%d/%m/%Y")
        hoje = datetime.now().strftime("%d/%m/%Y")
        self.assertTrue(ar.calculo_antigo(antigo))
        self.assertFalse(ar.calculo_antigo(hoje))
        self.assertFalse(ar.calculo_antigo(""))           # ausência = ramo sem_calculo
        self.assertFalse(ar.calculo_antigo("xorriso"))    # ilegível = False, não crash

    def test_nao_antigo_nao_executa_nada(self):
        driver = MagicMock()
        dados = self._dados(datetime.now().strftime("%d/%m/%Y"))
        with patch.object(ar, "executar_atualizacao_rapida_detalhada") as motor:
            res = ar.atualizar_calculo_se_antigo(driver, dados)
        self.assertIsNone(res)
        motor.assert_not_called()

    def test_antigo_atualiza_e_repuxa_valor(self):
        driver = MagicMock()
        dados = self._dados("01/01/2020")
        nova_divida = {"valor": "R$ 9.999,00", "data": datetime.now().strftime("%d/%m/%Y")}

        def motor_fake(_d, _n, **kw):
            self.assertTrue(kw.get("selecionar_mais_recente"))
            return ar.ResultadoAtualizacao(sucesso=True, numero_processo=CNJ,
                                           numero_calculo="77", data=nova_divida["data"])

        with patch.object(ar, "executar_atualizacao_rapida_detalhada", side_effect=motor_fake) as motor, \
             patch.object(ar, "_divida_mais_recente_api", return_value=dict(nova_divida)), \
             patch("Fix.espera.ate", side_effect=lambda _d, cond, **kw: cond(None)):
            res = ar.atualizar_calculo_se_antigo(driver, dados)
        self.assertEqual(res, "calculo_antigo")
        motor.assert_called_once()
        self.assertEqual(dados["divida"], nova_divida)  # mutado in-place p/ minuta

    def test_antigo_motor_falha_pos_envio_propaga(self):
        driver = MagicMock()
        dados = self._dados("01/01/2020")
        with patch.object(ar, "executar_atualizacao_rapida_detalhada",
                          side_effect=ar.AtualizacaoRapidaErro("envio?", pos_envio=True)):
            with self.assertRaises(ar.AtualizacaoRapidaErro):
                ar.atualizar_calculo_se_antigo(driver, dados)
        self.assertEqual(dados["divida"]["valor"], "R$ 1.000,00")  # dívida intacta

    def test_antigo_api_nao_reflete_mantem_divida(self):
        driver = MagicMock()
        dados = self._dados("01/01/2020")
        with patch.object(ar, "executar_atualizacao_rapida_detalhada",
                          return_value=ar.ResultadoAtualizacao(sucesso=True, numero_calculo="77")), \
             patch("Fix.espera.ate", return_value=None):  # API nunca reflete no teto
            res = ar.atualizar_calculo_se_antigo(driver, dados)
        self.assertEqual(res, "calculo_antigo")
        self.assertEqual(dados["divida"]["valor"], "R$ 1.000,00")  # NÃO vira valor novo falso

    def test_sisb_ponte_sucesso_limpa_pendencia(self):
        sisb = _import_sisb_core()
        dados = self._dados("01/01/2020")
        nova = {"valor": "R$ 9.999,00", "data": datetime.now().strftime("%d/%m/%Y")}

        def motor(_dp, _dados, log=True):
            dados["divida"] = nova
            return "calculo_antigo"

        with patch("Fix.atualizacao_rapida.atualizar_calculo_se_antigo", side_effect=motor):
            pendencia, valor = sisb._atualizar_calculo_antigo(MagicMock(), dados, "R$ 1.000,00")
        self.assertIsNone(pendencia)              # GIGS sem sufixo CALC
        self.assertEqual(valor, "R$ 9.999,00")    # minuta usa valor novo

    def test_sisb_ponte_falha_mantem_calc(self):
        sisb = _import_sisb_core()
        dados = self._dados("01/01/2020")
        with patch("Fix.atualizacao_rapida.atualizar_calculo_se_antigo",
                   side_effect=ar.AtualizacaoRapidaErro("falha", pos_envio=False)):
            pendencia, valor = sisb._atualizar_calculo_antigo(MagicMock(), dados, "R$ 1.000,00")
        self.assertEqual(pendencia, "calculo_antigo")  # GIGS 'xs resultado CALC' segue
        self.assertEqual(valor, "R$ 1.000,00")


def _import_sisb_core():
    import builtins
    real_open = builtins.open

    def _open(file, mode="r", *a, **k):
        if isinstance(mode, str) and any(c in mode for c in "wax+"):
            return MagicMock()
        return real_open(file, mode, *a, **k)

    with patch.object(builtins, "open", _open):
        import SISB.core as sisb_core
    return sisb_core


def _import_com_open_mascarado(caminho_modulo):
    """Importa módulo neutralizando escritas de import-time legadas (sandbox)."""
    import builtins
    import importlib
    real_open = builtins.open

    def _open(file, mode="r", *a, **k):
        if isinstance(mode, str) and any(c in mode for c in "wax+"):
            return MagicMock()
        return real_open(file, mode, *a, **k)

    with patch.object(builtins, "open", _open):
        return importlib.import_module(caminho_modulo)


class _DriverAbas:
    """Driver mínimo que só troca a aba corrente (sem Playwright)."""

    def __init__(self):
        self.atual = "handle-detalhe"

    @property
    def current_window_handle(self):
        return self.atual


class TestJuntadaFoco(unittest.TestCase):
    """Regressão do log 22:59:44 — a limpeza dupla fechava a aba /detalhe e o
    fluxo terminava preso em /documento/anexar."""

    def test_com_navegacao_nao_deixa_o_geral_fechar_abas(self):
        base = _import_com_open_mascarado("atos.anexos.anexos_juntador_base")
        driver = _DriverAbas()
        juntador = MagicMock()

        def _abrir():
            driver.atual = "handle-anexar"   # passo 1 troca de aba
            return True

        juntador._abrir_interface_anexacao.side_effect = _abrir
        with patch.object(base, "create_juntador", return_value=juntador), \
             patch.object(base, "wrapper_juntada_geral", return_value=True) as geral, \
             patch("Fix.abas.forcar_fechamento_abas_extras") as fechar:
            base.wrapper_juntada_com_navegacao(driver, debug=False)
        # o wrapper interno não pode fechar abas: a "original" dele seria a /anexar
        self.assertFalse(geral.call_args.kwargs["fechar_aba_apos"])
        # e a limpeza única tem de preservar a aba /detalhe de verdade
        fechar.assert_called_once()
        self.assertEqual(fechar.call_args.args[0], driver)
        self.assertEqual(fechar.call_args.args[1], "handle-detalhe")

    def test_geral_continua_fechando_quando_chamado_direto(self):
        base = _import_com_open_mascarado("atos.anexos.anexos_juntador_base")
        driver = _DriverAbas()
        juntador = MagicMock()
        juntador.executar_juntada.return_value = True
        with patch.object(base, "create_juntador", return_value=juntador), \
             patch("Fix.abas.forcar_fechamento_abas_extras") as fechar:
            ok = base.wrapper_juntada_geral(driver, debug=False)
        self.assertTrue(ok)
        fechar.assert_called_once()   # comportamento próprio preservado


class TestSubstMarcadorEditor(unittest.TestCase):
    """Regressão do log 23:00:44: script rodava com o CKEditor ainda inicializando
    e caía em 'Nenhum método funcionou'."""

    def _montar(self, respostas_script):
        helpers = _import_com_open_mascarado("atos.anexos.anexos_juntador_helpers")
        editable = MagicMock()
        fila = list(respostas_script)
        chamadas = {'principal': 0}

        def _js(_d, script, *_a):
            if "=== USANDO LÓGICA ROBUSTA" in script:      # script principal primeiro
                chamadas['principal'] += 1
                return fila.pop(0) if fila else {"sucesso": True, "metodo": "x"}
            if "ckeditorInstance" in script and "closest" in script:
                return True                                  # sonda de prontidão
            if "return arguments[0].innerHTML" in script:
                return '<p>texto do modelo sem marcador</p>'
            return None

        with patch.object(helpers, "_executar_js", side_effect=_js), \
             patch("Fix.espera.assentar", return_value=True), \
             patch("Fix.espera.elemento", return_value=editable):
            ok = helpers.substituir_marcador_por_conteudo(
                MagicMock(), conteudo_customizado="<p>relatorio</p>", debug=False)
        return ok, chamadas

    def test_retenta_uma_vez_quando_nenhum_metodo(self):
        ok, chamadas = self._montar([
            {"sucesso": False, "erro": "Nenhum método funcionou"},
            {"sucesso": True, "metodo": "ckeditor_api"},
        ])
        self.assertTrue(ok)
        self.assertEqual(chamadas["principal"], 2)   # reexecutou uma vez

    def test_sucesso_direto_nao_retenta(self):
        ok, chamadas = self._montar([{"sucesso": True, "metodo": "ckeditor_api"}])
        self.assertTrue(ok)
        self.assertEqual(chamadas["principal"], 1)


class TestNavegacaoSisbajud(unittest.TestCase):
    """Regressão do log real: página correta já aberta, mas preenchimento falhava
    com 'Execution context was destroyed' por renavegação da SPA/Callback OIDC."""

    def test_cadastro_ja_aberto_nao_renavega(self):
        sisb = _import_sisb_core()
        driver = MagicMock()
        driver.current_url = "https://sisbajud.cnj.jus.br/minuta/cadastrar"
        with patch.object(sisb, "_aguardar_cadastro_renderizado", return_value=True), \
             patch.object(sisb, "_exec_js", return_value={"ok": True}):
            ok = sisb._abrir_cadastro_minuta(driver, "1ª minuta", log=False)
        self.assertTrue(ok)
        driver.get.assert_not_called()

    def test_cadastro_consumido_renavega(self):
        """URL igual mas formulário já preenchido (sobra da 1ª) => renavega."""
        sisb = _import_sisb_core()
        driver = MagicMock()
        driver.current_url = "https://sisbajud.cnj.jus.br/minuta/cadastrar"
        with patch.object(sisb, "_aguardar_cadastro_renderizado", return_value=True), \
             patch.object(sisb, "_exec_js", return_value={"ok": False, "preenchido": True}), \
             patch("Fix.espera.assentar", return_value=True):
            ok = sisb._abrir_cadastro_minuta(driver, "2ª minuta", log=False)
        self.assertTrue(ok)
        driver.get.assert_called_once()

    def test_forcar_novo_sempre_renavega(self):
        sisb = _import_sisb_core()
        driver = MagicMock()
        driver.current_url = "https://sisbajud.cnj.jus.br/minuta/cadastrar"
        with patch.object(sisb, "_aguardar_cadastro_renderizado", return_value=True), \
             patch("Fix.espera.assentar", return_value=True):
            ok = sisb._abrir_cadastro_minuta(driver, "2ª minuta", log=False, forcar_novo=True)
        self.assertTrue(ok)
        driver.get.assert_called_once()

    def test_cadastro_fora_da_rota_navega(self):
        sisb = _import_sisb_core()
        driver = MagicMock()
        driver.current_url = "https://sisbajud.cnj.jus.br/teimosinha"
        with patch.object(sisb, "_aguardar_cadastro_renderizado", return_value=True), \
             patch("Fix.espera.assentar", return_value=True):
            ok = sisb._abrir_cadastro_minuta(driver, "1ª minuta", log=False)
        self.assertTrue(ok)
        driver.get.assert_called_once()

    def _rodar_sonda(self, sisb, estados):
        """Executa _aguardar_cadastro_renderizado ciclando os estados da sonda."""
        driver = MagicMock()
        passos = {'i': 0}

        def _script(_d, _s):
            valor = estados[passos['i'] % len(estados)]
            passos['i'] += 1
            return valor

        def _ate(_d, cond, teto=0, intervalo=0):
            for _ in range(12):
                if cond(_d):
                    return True
            return False

        with patch.object(sisb, "_exec_js", side_effect=_script), \
             patch("Fix.espera.ate", side_effect=_ate):
            return sisb._aguardar_cadastro_renderizado(driver, teto=1)

    def test_carregando_nao_conta_como_pronto(self):
        sisb = _import_sisb_core()
        ok = self._rodar_sonda(sisb, [
            {"pronto": False, "motivo": "carregando", "url": "u#state=1"},
            {"pronto": False, "motivo": "carregando", "url": "u#state=1"},
            {"pronto": True, "motivo": "ok", "url": "u#state=1"},
            {"pronto": True, "motivo": "ok", "url": "u#state=1"},
        ])
        self.assertTrue(ok)

    def test_carregando_ate_o_teto_nao_fica_pronto(self):
        sisb = _import_sisb_core()
        ok = self._rodar_sonda(sisb, [{"pronto": False, "motivo": "carregando", "url": "u"}])
        self.assertFalse(ok)

    def test_exige_url_estavel_entre_amostras(self):
        """URL mudando (SPA ainda navegando) não conta como pronta."""
        sisb = _import_sisb_core()
        ok = self._rodar_sonda(sisb, [
            {"pronto": True, "motivo": "ok", "url": "a"},
            {"pronto": True, "motivo": "ok", "url": "b"},
            {"pronto": True, "motivo": "ok", "url": "c"},
        ])
        self.assertFalse(ok)

    def test_preenchimento_retenta_apos_contexto_destruido(self):
        from SISB.processamento import minutas_campos as mc
        driver = MagicMock()
        driver.execute_async_script.side_effect = [
            RuntimeError("Page.evaluate_handle: Execution context was destroyed, "
                         "most likely because of a navigation."),
            {"sucesso": True, "log": [], "data_final": "18/12/2026"},
        ]
        with patch.object(mc, "_exec_js", return_value=["1. Preenchendo Juiz..."]), \
             patch("Fix.espera.assentar", return_value=True), \
             patch("Fix.espera.ate_habilitar", return_value=True):
            res = mc._executar_campos_resiliente(driver, "script")
        self.assertTrue(res["sucesso"])
        self.assertEqual(driver.execute_async_script.call_count, 2)

    def test_falha_loga_passo_exato(self):
        """Diagnóstico: o progresso em window é lido mesmo quando a avaliação morre."""
        from SISB.processamento import minutas_campos as mc
        driver = MagicMock()
        driver.execute_async_script.side_effect = ValueError("erro de script")
        scripts = []

        def _js(_d, script):
            scripts.append(script)
            if "__pjeplusCamposLog" in script and "slice(-15)" in script:
                return ["0. Script iniciado", "2. Preenchendo Vara..."]
            return {"url": "https://sisbajud.cnj.jus.br/minuta/cadastrar", "cadastro": True}

        with patch.object(mc, "_exec_js", side_effect=_js):
            with self.assertRaises(ValueError):
                mc._executar_campos_resiliente(driver, "script")
        self.assertEqual(driver.execute_async_script.call_count, 1)
        self.assertTrue(any("__pjeplusCamposLog" in s for s in scripts))


if __name__ == "__main__":
    unittest.main()