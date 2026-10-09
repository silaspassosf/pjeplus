# -*- coding: utf-8 -*-
"""Testes de Caracterização — Regras Puras e Contratos de Negócio.

Cobre os três fluxos principais:
  1. PEC: Classificação por RuleRegistry (determinar_regra), cálculo de prazos e datas e-Carta.
  2. Mandado: Classificação de anexos, regras SISBAJUD da certidão de devolução, termos de timeline.
  3. P2B: Roteamento de início de execução por API, parsing de GIGS, regex geral e regras de timeline.

Estes testes travam o comportamento funcional antes e depois de qualquer refatoração.
"""
import os
import sys
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock

# Garantir raiz no sys.path
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


class TestCaracterizacaoPEC(unittest.TestCase):
    """Caracterização de regras e decisões puras do fluxo PEC."""

    def test_determinar_regra_carta(self):
        from PEC.regras_execucao import determinar_regra
        match = determinar_regra("cumprir xs carta urgente")
        self.assertIsNotNone(match)
        _, bucket, acao = match
        self.assertEqual(bucket, "carta")
        self.assertTrue(callable(acao))

    def test_determinar_regra_comunicacoes_ord_sum(self):
        from PEC.regras_execucao import determinar_regra
        for obs in ["xs ord", "c.ord", "notificar xs ord"]:
            match = determinar_regra(obs)
            self.assertIsNotNone(match, f"Falha ao casar '{obs}'")
            self.assertEqual(match[1], "comunicacoes")

        for obs in ["xs sum", "c.sum", "notificar xs sum"]:
            match = determinar_regra(obs)
            self.assertIsNotNone(match, f"Falha ao casar '{obs}'")
            self.assertEqual(match[1], "comunicacoes")

    def test_determinar_regra_sobrestamento(self):
        from PEC.regras_execucao import determinar_regra
        match = determinar_regra("sobrestamento vencido")
        self.assertIsNotNone(match)
        self.assertEqual(match[1], "sobrestamento")

        match_sob = determinar_regra("xs sob 30")
        self.assertIsNotNone(match_sob)
        self.assertEqual(match_sob[1], "xs_sob")

    def test_determinar_regra_sisbajud(self):
        from PEC.regras_execucao import determinar_regra
        match_t2 = determinar_regra("rodar teimosinha no processo")
        self.assertIsNotNone(match_t2)
        self.assertEqual(match_t2[1], "sisbajud_teimosinha")

        match_res = determinar_regra("sisbajud resultado verificar")
        self.assertIsNotNone(match_res)
        self.assertEqual(match_res[1], "sisbajud_resultado")

    def test_determinar_regra_sigilo_e_chip(self):
        from PEC.regras_execucao import determinar_regra, BUCKET_ORDEM
        self.assertEqual(BUCKET_ORDEM[0], "xs_sigilo")
        match_sigilo = determinar_regra("xs sigilo documentos")
        self.assertIsNotNone(match_sigilo)
        self.assertEqual(match_sigilo[1], "xs_sigilo")

        match_chip = determinar_regra("sob chip etiqueta")
        self.assertIsNotNone(match_chip)
        self.assertEqual(match_chip[1], "xs_sob")

    def test_calculo_dias_uteis_ecarta(self):
        from PEC.runtime_pec import _parse_data_ecarta, _somar_dias_uteis
        dt = _parse_data_ecarta("15/05/2025")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.year, 2025)

        # Somar 5 dias úteis a partir de uma quarta-feira (14/05/2025) usando date
        dt_qua = date(2025, 5, 14)
        prazo_5 = _somar_dias_uteis(dt_qua, 5)
        self.assertIsNotNone(prazo_5)
        self.assertEqual(prazo_5.weekday(), 2)  # Quarta-feira seguinte (pula fds)

    def test_selecionar_modelo_gigs_imports(self):
        import PEC.anexos.anexos_juntador_metodos as metodos
        self.assertTrue(hasattr(metodos, 'time'))
        self.assertIsNotNone(metodos.time)


class TestCaracterizacaoMandado(unittest.TestCase):
    """Caracterização de regras e decisões puras do fluxo Mandado."""

    def test_identificar_tipo_anexo(self):
        from Mandado.anexos_argos import _identificar_tipo_anexo
        self.assertEqual(_identificar_tipo_anexo("DECLARACAO INFOJUD 2024"), "infojud")
        self.assertEqual(_identificar_tipo_anexo("Comprovante DOI Receita"), "doi")
        self.assertEqual(_identificar_tipo_anexo("Copia IRPF 2023"), "irpf")
        self.assertEqual(_identificar_tipo_anexo("DEC123456789"), "DEC9")
        self.assertIsNone(_identificar_tipo_anexo("peticao simples de juntada"))

    def test_processar_sisbajud_positivo_negativo(self):
        from Mandado.anexos_argos import processar_sisbajud

        # Texto sem marcador deve levantar ValueError
        with self.assertRaises(ValueError):
            processar_sisbajud("Texto qualquer sem o marcador esperado")

        # Texto com marcador e bloqueio positivo
        texto_positivo = (
            "DETERMINAÇÕES NORMATIVAS E LEGAIS\n"
            "1. EMPRESA REU LTDA\n"
            "CNPJ: 11.222.333/0001-44\n"
            "Bloqueio de valores\n"
            "SISBAJUD Positivo\n"
            "Saldo transferido: R$ 1.500,50\n"
        )
        res, motivo, executados = processar_sisbajud(texto_positivo, log=False)
        self.assertEqual(res, "positivo")
        self.assertTrue(len(executados) >= 1)
        self.assertEqual(executados[0]["nome"], "EMPRESA REU LTDA")

        # Texto com marcador e bloqueio negativo
        texto_negativo = (
            "DETERMINAÇÕES NORMATIVAS E LEGAIS\n"
            "1. EMPRESA REU LTDA\n"
            "CNPJ: 11.222.333/0001-44\n"
            "Bloqueio de valores\n"
            "SISBAJUD Negativo\n"
            "Saldo encontrado: R$ 0,00\n"
        )
        res_neg, motivo_neg, _ = processar_sisbajud(texto_negativo, log=False)
        self.assertEqual(res_neg, "negativo")

    def test_termos_timeline_mandado(self):
        from Mandado.entrada_api import _TERMOS_ARGOS, _TERMOS_OUTROS
        self.assertIn("argos", _TERMOS_ARGOS)
        self.assertIn("pesquisa patrimonial", _TERMOS_ARGOS)
        self.assertIn("certidao de oficial de justica", _TERMOS_OUTROS)

    def test_extrair_nome_destinatario_certidao(self):
        from Mandado.apoio_fluxos import _extrair_nome_destinatario_certidao
        texto_real_1000397 = (
            "PODER JUDICIÁRIO JUSTIÇA DO TRABALHO\n"
            "ATOrd 1000397-80.2026.5.02.0703\n"
            "DESTINATÁRIO: ABN MONTAGENS ELETRICAS LTDA - ME\n"
            "CERTIFICO que dirigi-me ao endereço e procedi a citação..."
        )
        nome = _extrair_nome_destinatario_certidao(texto_real_1000397)
        self.assertEqual(nome, "ABN MONTAGENS ELETRICAS LTDA - ME")

        texto_sem_dois_pontos = "DESTINATARIO CICERO FARIAS SILVA\nCertifico..."
        nome2 = _extrair_nome_destinatario_certidao(texto_sem_dois_pontos)
        self.assertEqual(nome2, "CICERO FARIAS SILVA")

        self.assertIsNone(_extrair_nome_destinatario_certidao(None))
        self.assertIsNone(_extrair_nome_destinatario_certidao("Texto sem destinatario"))

    def test_arquivar_mandado_positivo_registra_gigs_sem_prazo(self):
        from unittest.mock import patch, MagicMock
        from Mandado.apoio_fluxos import arquivar_mandado_positivo_reconhecido

        driver_mock = MagicMock()
        texto_certidao = "DESTINATÁRIO: EMPRESA TESTE LTDA\nCertifico..."

        with patch("Mandado.apoio_fluxos._extrair_texto_certidao_oficial_via_api", return_value=texto_certidao), \
             patch("Mandado.apoio_fluxos._criar_gigs_xs1_uma_vez") as mock_xs1, \
             patch("Fix.extracao.criar_gigs", return_value=True) as mock_criar_gigs, \
             patch("Mandado.apoio_fluxos._apagar_mandado_do_escaninho", return_value=True) as mock_apagar:

            res = arquivar_mandado_positivo_reconhecido(
                driver=driver_mock,
                numero_processo="1000397-80.2026.5.02.0703",
                escaninho_handle="h1",
                log=False,
            )

            self.assertTrue(res)
            mock_xs1.assert_called_once_with(driver_mock, "1000397-80.2026.5.02.0703", False)
            mock_criar_gigs.assert_called_once_with(
                driver_mock,
                "",
                "",
                "EMPRESA TESTE LTDA - já alterado endereço na autuação.",
                log=False,
            )
            mock_apagar.assert_called_once_with(driver_mock, "1000397-80.2026.5.02.0703", "h1", False)



class TestCaracterizacaoP2B(unittest.TestCase):
    """Caracterização de regras e decisões puras do fluxo P2B."""

    def test_parse_gigs_param(self):
        from Prazo.p2b_regras_execucao import parse_gigs_param
        dias, resp, obs = parse_gigs_param("1/Ana Lucia/Argos")
        self.assertEqual(dias, "1")
        self.assertEqual(resp, "Ana Lucia")
        self.assertEqual(obs, "Argos")

        d2, r2, o2 = parse_gigs_param("5//xs sigilo")
        self.assertEqual(d2, "5")
        self.assertEqual(r2, "")
        self.assertEqual(o2, "xs sigilo")

    def test_gerar_regex_geral(self):
        from Prazo.p2b_regras_execucao import gerar_regex_geral
        from Fix.utils import normalizar_texto
        padrao = gerar_regex_geral("iniciar execucao")
        self.assertIsNotNone(padrao.search("iniciar - execucao"))
        self.assertIsNotNone(padrao.search(normalizar_texto("INICIAR   EXECUÇÃO")))

    def test_decidir_rota_iniciar_exec_mock(self):
        from Prazo.p2b_gateway import decidir_rota_iniciar_exec

        mock_client = MagicMock()

        # Cenário 1: Fase já em execução -> rota 'pesquisas'
        mock_client.processo_por_id.return_value = {"labelFaseProcessual": "Execução"}
        rota = decidir_rota_iniciar_exec(mock_client, "12345")
        self.assertEqual(rota, "pesquisas")

        # Cenário 2: Fase liquidação sem movimento 50047 -> rota 'pesqliq'
        mock_client.processo_por_id.return_value = {"labelFaseProcessual": "Liquidação"}
        mock_client.timeline.return_value = [{"codEvento": 123}]  # sem 50047
        rota = decidir_rota_iniciar_exec(mock_client, "12345")
        self.assertEqual(rota, "pesqliq")

        # Cenário 3: Fase liquidação homologada (com 50047) COM obrigações -> 'executar_pesquisas'
        mock_client.timeline.return_value = [{"codEvento": 50047}]
        mock_client.obrigacoes_pagar.return_value = [{"id": 1, "valor": 500.0}]
        rota = decidir_rota_iniciar_exec(mock_client, "12345")
        self.assertEqual(rota, "executar_pesquisas")

        # Cenário 4: Fase liquidação homologada (com 50047) SEM obrigações -> 'mock_pesquisas'
        mock_client.obrigacoes_pagar.return_value = []
        rota = decidir_rota_iniciar_exec(mock_client, "12345")
        self.assertEqual(rota, "mock_pesquisas")

    def test_decidir_ato_despacho_argos(self):
        from Mandado.regras import decidir_ato_despacho_argos
        self.assertEqual(decidir_ato_despacho_argos("positivo", False), "ato_bloq")
        self.assertEqual(decidir_ato_despacho_argos("positivo", True), "ato_bloq")
        self.assertEqual(decidir_ato_despacho_argos("negativo", True), "ato_termoS")
        self.assertEqual(decidir_ato_despacho_argos("negativo", False), "ato_meios")
        self.assertEqual(decidir_ato_despacho_argos("outro", False), "ato_meios")

    def test_mandado_anterior_penhora_helper(self):
        from Mandado.apoio_fluxos import _mandado_contem_penhora
        # Casos positivos
        doc1 = {"tipo": "Mandado de Penhora", "descricao": "(Mandado de Penhora e avaliação de veículo placa FAV5939)"}
        self.assertTrue(_mandado_contem_penhora(doc1))

        doc2 = {"tipo": "Mandado", "titulo": "Mandado de Penhora e Avaliação"}
        self.assertTrue(_mandado_contem_penhora(doc2))

        doc3 = {"tipo": "Mandado", "descricao": "cumprimento de penhora de bens"}
        self.assertTrue(_mandado_contem_penhora(doc3))

        # Casos negativos
        doc4 = {"tipo": "Mandado", "titulo": "Mandado de Notificação", "descricao": "notificação da reclamada"}
        self.assertFalse(_mandado_contem_penhora(doc4))

        doc5 = {"tipo": "Certidão", "descricao": "certidão de devolução"}
        self.assertFalse(_mandado_contem_penhora(doc5))

    def test_fix_espera_ate(self):
        from Fix import espera
        self.assertTrue(hasattr(espera, 'ate'))
        chamadas = []
        def cond(driver):
            chamadas.append(1)
            return len(chamadas) >= 2
        res = espera.ate(None, cond, teto=2, intervalo=0.01)
        self.assertTrue(res)
        self.assertGreaterEqual(len(chamadas), 2)


if __name__ == "__main__":
    unittest.main()
