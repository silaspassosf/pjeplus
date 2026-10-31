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

    def test_determinar_regra_notificacao_v(self):
        from PEC.regras_execucao import determinar_regra
        from atos import wrappers_pec as w

        # XS ordv -> pec_ordv (troca de modelo para arvord)
        match = determinar_regra("XS ordv")
        self.assertIsNotNone(match)
        self.assertEqual(match[1], "comunicacoes")
        self.assertTrue(w.pec_ordv.trocar_modelo)
        self.assertEqual(w.pec_ordv.modelo_troca_correios, 'arvord')

        # xs sumv -> pec_sumv (troca de modelo para arvsum)
        match = determinar_regra("xs sumv")
        self.assertIsNotNone(match)
        self.assertEqual(match[1], "comunicacoes")
        self.assertTrue(w.pec_sumv.trocar_modelo)
        self.assertEqual(w.pec_sumv.modelo_troca_correios, 'arvsum')

        # xs ordva -> pec_arordv (direto sem hífen no wrapper)
        match = determinar_regra("xs ordva")
        self.assertIsNotNone(match)
        self.assertEqual(match[1], "comunicacoes")
        self.assertEqual(w.pec_arordv.modelo_nome, 'arvord')

        # xs sumva -> pec_arsumv (direto sem hífen no wrapper)
        match = determinar_regra("xs sumva")
        self.assertIsNotNone(match)
        self.assertEqual(match[1], "comunicacoes")
        self.assertEqual(w.pec_arsumv.modelo_nome, 'arvsum')

        # Garantir ausência de aliases
        self.assertFalse(hasattr(w, 'pec_ar_ordv'))
        self.assertFalse(hasattr(w, 'pec_ar_sumv'))

    def test_determinar_regra_pec_id_e_mddid_removido(self):
        from PEC.regras_execucao import determinar_regra
        # mddid deve ter sido removido das regras
        self.assertIsNone(determinar_regra("xs mddid"))
        self.assertIsNone(determinar_regra("mdd id"))
        self.assertIsNone(determinar_regra("mddid"))

        # pec id deve casar no bucket comunicacoes
        for obs in ["xs pec id", "pec id", "pecid", "xs pecid", "xs pec id >silas"]:
            match = determinar_regra(obs)
            self.assertIsNotNone(match, f"Falha ao casar '{obs}'")
            self.assertEqual(match[1], "comunicacoes")

        # pec idpj não deve ser consumido pela regra de pec id
        match_idpj = determinar_regra("xs pec idpj")
        self.assertIsNotNone(match_idpj)
        self.assertEqual(match_idpj[1], "comunicacoes")
        self.assertIn("idpj", match_idpj[0].pattern)

    def test_determinar_regra_pagto_desp(self):
        from PEC.regras_execucao import determinar_regra
        for obs in [
            "pagto desp",
            "xs pagto desp",
            "pgto desp",
            "xs pgto desp",
            "desp pagto",
            "xs desp pagto",
            "pagto despacho",
            "despacho pagto",
            "cumprir pagto desp urgente"
        ]:
            match = determinar_regra(obs)
            self.assertIsNotNone(match, f"Falha ao casar '{obs}'")
            self.assertEqual(match[1], "outros")
            self.assertTrue(callable(match[2]))

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

    def test_determinar_regra_xs_pesq_e_xs_pesquisa(self):
        from PEC.regras_execucao import determinar_regra
        # Aceita estritamente 'xs pesq' ou 'xs pesquisa'
        match_pesq = determinar_regra("xs pesq")
        self.assertIsNotNone(match_pesq)
        self.assertEqual(match_pesq[1], "outros")

        match_pesquisa = determinar_regra("xs pesquisa")
        self.assertIsNotNone(match_pesquisa)
        self.assertEqual(match_pesquisa[1], "outros")

        # Não aceita sem o prefixo 'xs'
        self.assertIsNone(determinar_regra("pesq"))
        self.assertIsNone(determinar_regra("pesquisa"))

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
                "Mandado positivo (EMPRESA TESTE LTDA) - já alterado endereço na autuação.",
                log=False,
            )
            mock_apagar.assert_called_once_with(driver_mock, "1000397-80.2026.5.02.0703", "h1", False)

    def test_classificar_certidao_oficial_negativo_padroes(self):
        from Mandado.apoio_fluxos import _classificar_certidao_oficial

        # Caso real do processo 1001090-35.2024.5.02.0703
        texto_real = (
            "CERTIDÃO NEGATIVA\n"
            "Certifico e dou fé que compareci ao endereço... "
            "Esta afirmou que a empresa não estava instalada naquele centro comercial. "
            "Por todo o exposto, DEIXO DE REALIZAR A PENHORA e submeto a certidão."
        )
        self.assertEqual(_classificar_certidao_oficial(texto_real), "negativo")

        # Teste com padrões individuais
        self.assertEqual(_classificar_certidao_oficial("deixo de realizar a diligencia"), "negativo")
        self.assertEqual(_classificar_certidao_oficial("empresa nao esta instalada no local"), "negativo")
        self.assertEqual(_classificar_certidao_oficial("pessoa desconhecida no local"), "negativo")
        self.assertEqual(_classificar_certidao_oficial("certidao de intimacao negativa"), "negativo")

    def test_classificar_certidao_oficial_positivo_padroes(self):
        from Mandado.apoio_fluxos import _classificar_certidao_oficial, _extrair_nome_destinatario_certidao

        texto_exemplo = (
            "CERTIDÃO DE DEVOLUÇÃO DE MANDADO\n\n"
            "ID do mandado: 84f3bd5\n\n"
            "Destinatário: FABIO BRITO DE ALMEIDA\n\n"
            "Certifico e dou fé que, no dia 16/10/2026 às 7:50h, me dirigi à Rua dos Buritis, nº 925, apto 2153, "
            "São Paulo, onde CITEI, o destinatário, FABIO BRITO DE ALMEIDA, que de tudo ficou ciente e recebeu o mandado. "
            "Diante do exposto, devolvo o presente mandado e submeto à apreciação de V. Exa"
        )
        self.assertEqual(_classificar_certidao_oficial(texto_exemplo), "positivo")
        self.assertEqual(_extrair_nome_destinatario_certidao(texto_exemplo), "FABIO BRITO DE ALMEIDA")

        # Testar cada novo padrão positivo individualmente
        self.assertEqual(_classificar_certidao_oficial("... onde citei o reclamado ..."), "positivo")
        self.assertEqual(_classificar_certidao_oficial("... onde intimei o reclamado ..."), "positivo")
        self.assertEqual(_classificar_certidao_oficial("... ocasião em que citei a executada ..."), "positivo")
        self.assertEqual(_classificar_certidao_oficial("... ato contínuo, citei o sócio ..."), "positivo")
        self.assertEqual(_classificar_certidao_oficial("... ali, citei a ré ..."), "positivo")
        self.assertEqual(_classificar_certidao_oficial("... que ficou ciente dos termos ..."), "positivo")
        self.assertEqual(_classificar_certidao_oficial("... recebeu o mandado em mãos ..."), "positivo")




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
    def test_p2b_admito_parcelamento_prevalencia_sobre_iniciar_exec(self):
        """Valida que 'admito o parcelamento' cai no grupo 'xs saldo' e tem prevalência sobre iniciar_exec."""
        from Prazo.p2b_documentos import _definir_regras_processamento
        from Prazo.p2b_regras_execucao import gerar_regex_geral

        regras = _definir_regras_processamento()

        # Texto que contém tanto 'admito o parcelamento' quanto termos do grupo iniciar_exec ('sob pena de bloqueio', 'comprovar o pagamento')
        texto = (
            "Vistos etc. Admito o parcelamento do débito exequendo nos termos do art. 916 do CPC. "
            "Deverá a reclamada comprovar o pagamento das parcelas subsequentes, sob pena de bloqueio."
        )

        regra_casada = None
        for trechos, tipo_acao in regras:
            for trecho in trechos:
                padrao = trecho if hasattr(trecho, 'search') else gerar_regex_geral(trecho)
                if padrao.search(texto):
                    regra_casada = tipo_acao
                    break
            if regra_casada:
                break

        self.assertIsNotNone(regra_casada)
        self.assertEqual(regra_casada, ("criar_gigs[1//xs saldo]",))

    def test_p2b_regra_arquivar_devendo_diligenciar_cartorio(self):
        """Valida que o trecho 'devendo diligenciar junto ao cartório' aciona a ação mov_arquivar."""
        from Prazo.p2b_documentos import _definir_regras_processamento
        from Prazo.p2b_regras_execucao import gerar_regex_geral
        from Fix.utils import normalizar_texto

        regras = _definir_regras_processamento()
        texto = normalizar_texto(
            "Intime-se o autor, devendo diligenciar junto ao cartório para levantamento da certidão. "
            "Cumpridas as determinações, arquivem-se."
        )

        regra_casada = None
        for trechos, tipo_acao in regras:
            for trecho in trechos:
                padrao = trecho if hasattr(trecho, 'search') else gerar_regex_geral(trecho)
                if padrao.search(texto):
                    regra_casada = tipo_acao
                    break
            if regra_casada:
                break

        self.assertIsNotNone(regra_casada)
        # O callable deve ser mov_arquivar
        acao = regra_casada[0]
        self.assertEqual(getattr(acao, '__name__', str(acao)), 'mov_arquivar')

    def test_p2b_regra_iniciar_exec_comprovar_recolhimento_sob_pena_execucao(self):
        """Valida que intimação com comprovação de recolhimento sob pena de execução dispara _inicar_exec."""
        from Prazo.p2b_documentos import _definir_regras_processamento
        from Prazo.p2b_regras_execucao import gerar_regex_geral
        from Fix.utils import normalizar_texto

        regras = _definir_regras_processamento()
        texto = normalizar_texto(
            "Vistos, etc. Vencido o prazo estipulado para pagamento do acordo e ausente manifestação "
            "da parte reclamante em sentido contrário, presumo quitado o seu crédito. "
            "Intime-se a reclamada para, em 2 (dois) dias, comprovar o recolhimento das custas e o "
            "pagamento dos honorários periciais, conforme determinado em ID #id:41d8e6d, sob pena de execução. "
            "Cumprido, registrem-se os valores pagos e tornem conclusos para extinção do feito."
        )

        regra_casada = None
        for trechos, tipo_acao in regras:
            for trecho in trechos:
                padrao = trecho if hasattr(trecho, 'search') else gerar_regex_geral(trecho)
                if padrao.search(texto):
                    regra_casada = tipo_acao
                    break
            if regra_casada:
                break

        self.assertIsNotNone(regra_casada)
        acao = regra_casada[0]
        self.assertEqual(getattr(acao, '__name__', str(acao)), 'inicar_exec')

    def test_p2b_eh_despacho_2_dias_execucao_casos(self):
        """Valida que _eh_despacho_2_dias_execucao detecta apenas despachos de 2 dias/48h com execução."""
        from Prazo.p2b_gateway import _eh_despacho_2_dias_execucao

        texto_real = (
            "Vistos, etc. Vencido o prazo estipulado para pagamento do acordo e ausente manifestação "
            "da parte reclamante em sentido contrário, presumo quitado o seu crédito. "
            "Intime-se a reclamada para, em 2 (dois) dias, comprovar o recolhimento das custas e o "
            "pagamento dos honorários periciais, conforme determinado em ID #id:41d8e6d, sob pena de execução. "
            "Cumprido, registrem-se os valores pagos e tornem conclusos para extinção do feito."
        )
        self.assertTrue(_eh_despacho_2_dias_execucao(texto_real))

        texto_48h = (
            "Intime-se a executada para, no prazo de 48 horas, comprovar o recolhimento sob pena de execução."
        )
        self.assertTrue(_eh_despacho_2_dias_execucao(texto_48h))

        texto_48h_extenso = (
            "Intime-se para que em 48 (quarenta e oito) horas realize o pagamento das custas, sob pena de prosseguimento da execução."
        )
        self.assertTrue(_eh_despacho_2_dias_execucao(texto_48h_extenso))

        # Casos negativos:
        # Prazo de 5 ou 8 dias
        self.assertFalse(_eh_despacho_2_dias_execucao(
            "Intime-se a reclamada para, em 5 dias, comprovar o recolhimento sob pena de execução."
        ))
        self.assertFalse(_eh_despacho_2_dias_execucao(
            "Intime-se a reclamada para, em 8 dias, comprovar o recolhimento sob pena de execução."
        ))
        # Prazo de 2 dias mas sem cominação de execução
        self.assertFalse(_eh_despacho_2_dias_execucao(
            "Intime-se o perito para que em 2 dias apresente os esclarecimentos periciais."
        ))
        # Prazo de 48h genérico
        self.assertFalse(_eh_despacho_2_dias_execucao(
            "Intime-se o reclamante para que em 48 horas informe o endereço atualizado."
        ))

    def test_p2b_extrair_documento_relevante_excecao_2_dias(self):
        """Valida que extrair_documento_relevante abre exceção para despacho de 2 dias/48h sob pena de execução."""
        from unittest.mock import MagicMock, patch
        from Prazo.p2b_gateway import extrair_documento_relevante

        driver = MagicMock()
        driver.current_url = 'https://pje.trt2.jus.br/pjekz/processo/5023436/detalhe/'

        mock_sess = MagicMock()
        mock_resp_timeline = MagicMock()
        mock_resp_timeline.status_code = 200
        mock_resp_timeline.json.return_value = [
            {
                'tipo': 'Despacho',
                'id': 1234,
                'dataJuntada': '2026-10-15T07:38:15.011603',
                'titulo': 'Despacho'
            }
        ]

        mock_resp_conteudo = MagicMock()
        mock_resp_conteudo.status_code = 200
        mock_resp_conteudo.content = b'%PDF-1.4 mock content'

        def get_side_effect(url, **kwargs):
            if 'timeline' in url:
                return mock_resp_timeline
            return mock_resp_conteudo

        mock_sess.get.side_effect = get_side_effect

        texto_2d = (
            "Vistos, etc. Vencido o prazo estipulado para pagamento do acordo, presumo quitado. "
            "Intime-se a reclamada para, em 2 (dois) dias, comprovar o recolhimento das custas sob pena de execução."
        )
        texto_comum = (
            "Vistos, etc. Intime-se a reclamada para manifestar sobre os calculos no prazo de 8 dias."
        )

        # Caso 1: Despacho de 2 dias com 5 dias de idade -> DEVE PROCESSAR (sucesso = True)
        with patch('Prazo.p2b_gateway.session_from_driver', return_value=(mock_sess, 'pje.trt2.jus.br')), \
             patch('Mandado.apoio_fluxos._extrair_texto_pdf_bytes', return_value=texto_2d):
            res1 = extrair_documento_relevante(driver)
            self.assertTrue(res1.get('sucesso'))
            self.assertEqual(res1.get('conteudo'), texto_2d)

        # Caso 2: Despacho comum com 5 dias de idade -> DEVE PULAR (decisao_recente_menos_5_dias)
        with patch('Prazo.p2b_gateway.session_from_driver', return_value=(mock_sess, 'pje.trt2.jus.br')), \
             patch('Mandado.apoio_fluxos._extrair_texto_pdf_bytes', return_value=texto_comum):
            res2 = extrair_documento_relevante(driver)
            self.assertFalse(res2.get('sucesso'))
            self.assertEqual(res2.get('erro'), 'decisao_recente_menos_5_dias')


if __name__ == "__main__":
    unittest.main()




