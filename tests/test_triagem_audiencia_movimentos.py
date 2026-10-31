# -*- coding: utf-8 -*-
"""
Testes unitários para classificação de audiência via movimentos da timeline (bianca/triagem).
Regra dos 3 casos:
  (a) Distribuição e NÃO tem audiência -> SEM AUDIÊNCIA, fluxo de sempre
  (b) Distribuição + audiência em horário muito próximo -> TEM AUDIÊNCIA, fluxo de sempre
  (c) Tem audiência, mas marcação veio mais tarde que a distribuição -> SEM AUDIÊNCIA mas pula marcação
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from bianca.triagem.api import (
    classificar_audiencia_movimentos,
    parse_data_hora_movimento,
    enriquecer_processo,
)
from bianca.triagem.acoes import _tem_audiencia_marcada


class TestTriagemAudienciaMovimentos(unittest.TestCase):

    def test_parse_data_hora_movimento(self):
        dt1 = parse_data_hora_movimento("2026-10-26T15:34:07.746Z")
        self.assertIsNotNone(dt1)
        self.assertEqual(dt1.year, 2026)
        self.assertEqual(dt1.month, 10)
        self.assertEqual(dt1.day, 26)
        self.assertEqual(dt1.hour, 15)
        self.assertEqual(dt1.minute, 34)
        self.assertEqual(dt1.second, 7)

        dt2 = parse_data_hora_movimento("2026-10-26T15:34:05")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.second, 5)

        self.assertIsNone(parse_data_hora_movimento(None))
        self.assertIsNone(parse_data_hora_movimento(""))

    def test_caso_b_distribuicao_com_audiencia_mesmo_horario(self):
        # Dados reais do HTML fornecido pelo usuário (diferença de 1.845s)
        movimentos = [
            {
                "id": 476906367,
                "tipo": "Movimento",
                "titulo": "Audiência una (rito sumaríssimo) designada (11/12/2026 09:20 Sala Principal - 3ª Vara do Trabalho de São Paulo - Zona Sul)",
                "data": "2026-10-26T15:34:07.746Z",
            },
            {
                "id": 476906363,
                "tipo": "Movimento",
                "titulo": "Distribuído por sorteio",
                "codEvento": 26,
                "data": "2026-10-26T15:34:05.901Z",
            },
        ]
        status, det = classificar_audiencia_movimentos(movimentos)
        self.assertEqual(status, "TEM_AUDIENCIA")
        self.assertLessEqual(det["delta_segundos"], 180)

    def test_caso_a_distribuicao_sem_audiencia(self):
        movimentos = [
            {
                "id": 476906363,
                "tipo": "Movimento",
                "titulo": "Distribuído por sorteio",
                "codEvento": 26,
                "data": "2026-10-26T15:34:05.901Z",
            },
            {
                "id": 476906360,
                "tipo": "Movimento",
                "titulo": "Juntada de Petição Inicial",
                "data": "2026-10-26T15:33:09.418Z",
            },
        ]
        status, det = classificar_audiencia_movimentos(movimentos)
        self.assertEqual(status, "SEM_AUDIENCIA")
        self.assertIsNone(det["mov_aud"])

    def test_caso_c_audiencia_tardia_posterior_a_distribuicao(self):
        # Audiência marcada horas depois ou no dia seguinte
        movimentos = [
            {
                "id": 476909999,
                "tipo": "Movimento",
                "titulo": "Audiência una designada (15/12/2026 10:00)",
                "data": "2026-10-26T17:15:00.000Z",  # ~1h40 depois da distribuição
            },
            {
                "id": 476906363,
                "tipo": "Movimento",
                "titulo": "Distribuído por sorteio",
                "codEvento": 26,
                "data": "2026-10-26T15:34:05.901Z",
            },
        ]
        status, det = classificar_audiencia_movimentos(movimentos)
        self.assertEqual(status, "AUDIENCIA_TARDIA")
        self.assertGreater(det["delta_segundos"], 180)

    def test_enriquecer_processo_com_os_3_casos(self):
        item_base = {
            "id": "9019073",
            "numeroProcesso": "1000123-45.2026.5.02.0003",
            "classeJudicial": "ATSUM",
            "juizoDigital": False,
        }

        # Caso a: sem audiência -> bucket A, pular_marcar_aud = False
        client_a = MagicMock()
        client_a.timeline.return_value = [
            {"titulo": "Distribuído por sorteio", "codEvento": 26, "data": "2026-10-26T15:34:05.000Z"}
        ]
        res_a = enriquecer_processo(item_base, client_a)
        self.assertEqual(res_a["bucket"], "A")
        self.assertFalse(res_a["tem_audiencia"])
        self.assertFalse(res_a["pular_marcar_aud"])
        self.assertEqual(res_a["status_audiencia"], "SEM_AUDIENCIA")

        # Caso b: com audiência na autuação -> bucket C (ou B se 100% digital), pular_marcar_aud = False
        client_b = MagicMock()
        client_b.timeline.return_value = [
            {"titulo": "Distribuído por sorteio", "codEvento": 26, "data": "2026-10-26T15:34:05.000Z"},
            {"titulo": "Audiência una designada", "data": "2026-10-26T15:34:07.000Z"},
        ]
        res_b = enriquecer_processo(item_base, client_b)
        self.assertEqual(res_b["bucket"], "C")
        self.assertTrue(res_b["tem_audiencia"])
        self.assertFalse(res_b["pular_marcar_aud"])
        self.assertEqual(res_b["status_audiencia"], "TEM_AUDIENCIA")

        # Caso c: audiência tardia -> bucket A, tem_audiencia = False, pular_marcar_aud = True
        client_c = MagicMock()
        client_c.timeline.return_value = [
            {"titulo": "Distribuído por sorteio", "codEvento": 26, "data": "2026-10-26T15:34:05.000Z"},
            {"titulo": "Audiência una designada", "data": "2026-10-26T18:00:00.000Z"},
        ]
        res_c = enriquecer_processo(item_base, client_c)
        self.assertEqual(res_c["bucket"], "A")
        self.assertFalse(res_c["tem_audiencia"])
        self.assertTrue(res_c["pular_marcar_aud"])
        self.assertEqual(res_c["status_audiencia"], "AUDIENCIA_TARDIA")

    def test_tem_audiencia_marcada_acoes(self):
        from unittest.mock import patch

        driver_mock = MagicMock()
        driver_mock.current_url = "https://pje.trt2.jus.br/pjekz/processo/9019073/detalhe"

        # Caso b: com audiência na autuação -> retorna True
        proc_b = {"id_processo": "9019073"}
        with patch("Fix.variaveis.session_from_driver", return_value=(MagicMock(), "https://pje.trt2.jus.br")), \
             patch("Fix.variaveis.PjeApiClient.timeline", return_value=[
                 {"titulo": "Distribuído por sorteio", "codEvento": 26, "data": "2026-10-26T15:34:05.000Z"},
                 {"titulo": "Audiência una designada", "data": "2026-10-26T15:34:07.000Z"},
             ]):
            tem_aud_b = _tem_audiencia_marcada(driver_mock, proc_b)
            self.assertTrue(tem_aud_b)
            self.assertTrue(proc_b["tem_audiencia"])
            self.assertFalse(proc_b["pular_marcar_aud"])

        # Caso c: audiência tardia -> retorna False e seta pular_marcar_aud = True
        proc_c = {"id_processo": "9019073"}
        with patch("Fix.variaveis.session_from_driver", return_value=(MagicMock(), "https://pje.trt2.jus.br")), \
             patch("Fix.variaveis.PjeApiClient.timeline", return_value=[
                 {"titulo": "Distribuído por sorteio", "codEvento": 26, "data": "2026-10-26T15:34:05.000Z"},
                 {"titulo": "Audiência una designada", "data": "2026-10-26T18:00:00.000Z"},
             ]):
            tem_aud_c = _tem_audiencia_marcada(driver_mock, proc_c)
            self.assertFalse(tem_aud_c)
            self.assertFalse(proc_c["tem_audiencia"])
            self.assertTrue(proc_c["pular_marcar_aud"])

        # Caso a: sem audiência -> retorna False e pular_marcar_aud = False
        proc_a = {"id_processo": "9019073"}
        with patch("Fix.variaveis.session_from_driver", return_value=(MagicMock(), "https://pje.trt2.jus.br")), \
             patch("Fix.variaveis.PjeApiClient.timeline", return_value=[
                 {"titulo": "Distribuído por sorteio", "codEvento": 26, "data": "2026-10-26T15:34:05.000Z"},
             ]):
            tem_aud_a = _tem_audiencia_marcada(driver_mock, proc_a)
            self.assertFalse(tem_aud_a)
            self.assertFalse(proc_a["tem_audiencia"])
            self.assertFalse(proc_a["pular_marcar_aud"])

    def test_usa_padrao_novo_dias_semana(self):
        from bianca.triagem.acoes import _usa_padrao_novo

        # Segunda (02/11/2026), Terça (03/11/2026), Sexta (06/11/2026) -> True
        self.assertTrue(_usa_padrao_novo({"data_audiencia": "2026-11-02T10:00:00"}, "1002098"))
        self.assertTrue(_usa_padrao_novo({"dataProximaAudiencia": "2026-11-03"}, "1002098"))
        self.assertTrue(_usa_padrao_novo({"data_audiencia": "06/11/2026"}, "1002098"))

        # Quarta (04/11/2026), Quinta (05/11/2026) -> False
        self.assertFalse(_usa_padrao_novo({"data_audiencia": "2026-11-04T10:00:00"}, "1002098"))
        self.assertFalse(_usa_padrao_novo({"dataProximaAudiencia": "2026-11-05"}, "1002098"))

    def test_acao_bucket_c_seg_ter_sex_faz_despacho_e_citacao_sem_pec(self):
        from unittest.mock import patch
        from bianca.triagem.acoes import acao_bucket_c

        driver_mock = MagicMock()
        proc_info = {
            "numero": "1002098-76.2026.5.02.0703",
            "tipo": "ATSUM",
            "tem_audiencia": True,
            "data_audiencia": "2026-11-03T09:30:00",  # Terça-feira (1 in 0, 1, 4)
        }

        with patch("bianca.triagem.acoes._tem_audiencia_marcada", return_value=True), \
             patch("bianca.triagem.acoes.def_citacao", return_value={
                 "sucesso": True,
                 "gigs_obs": ["xs sumv"],
                 "pec_wrappers": ["pec_sum"],
             }) as mock_citacao, \
             patch("bianca.triagem.acoes.criar_gigs") as mock_gigs, \
             patch("atos.wrappers_ato.ato_vpp", return_value=True) as mock_vpp, \
             patch("atos.wrappers_pec.pec_sum") as mock_pec_sum, \
             patch("atos.wrappers_mov.mov_aud") as mock_mov:

            ok, status = acao_bucket_c(driver_mock, "1002098-76.2026.5.02.0703", proc_info)

            self.assertTrue(ok)
            self.assertEqual(status, "Direto (seg/ter/sex) - despachado (ato_vpp)?")
            mock_citacao.assert_called_once()
            mock_gigs.assert_called_once_with(driver_mock, "1", "Bianca", "xs sumv")
            mock_vpp.assert_called_once_with(driver_mock, debug=True)
            mock_pec_sum.assert_not_called()
            mock_mov.assert_not_called()

    def test_acao_bucket_c_qua_qui_faz_pec_direto(self):
        from unittest.mock import patch
        from bianca.triagem.acoes import acao_bucket_c

        driver_mock = MagicMock()
        proc_info = {
            "numero": "1002099-00.2026.5.02.0703",
            "tipo": "ATSUM",
            "tem_audiencia": True,
            "data_audiencia": "2026-11-04T09:30:00",  # Quarta-feira (dia 2)
        }

        with patch("bianca.triagem.acoes._tem_audiencia_marcada", return_value=True), \
             patch("bianca.triagem.acoes.def_citacao", return_value={
                 "sucesso": True,
                 "gigs_obs": ["xs sum"],
                 "pec_wrappers": ["pec_sum"],
             }) as mock_citacao, \
             patch("bianca.triagem.acoes.criar_gigs") as mock_gigs, \
             patch("atos.wrappers_ato.ato_vpp") as mock_vpp, \
             patch("atos.wrappers_pec.pec_sum", return_value=True) as mock_pec_sum, \
             patch("atos.wrappers_mov.mov_aud", return_value=True) as mock_mov:

            ok, status = acao_bucket_c(driver_mock, "1002099-00.2026.5.02.0703", proc_info)

            self.assertTrue(ok)
            self.assertEqual(status, "Direto - citado?")
            mock_citacao.assert_called_once()
            mock_vpp.assert_not_called()
            mock_gigs.assert_not_called()
            mock_pec_sum.assert_called_once_with(driver_mock, debug=True)
            mock_mov.assert_called_once_with(driver_mock, debug=True)


if __name__ == "__main__":
    unittest.main()
