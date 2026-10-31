# -*- coding: utf-8 -*-
"""
tests/test_dom_lembrete.py -- Testes unitários para a extração de IDs de Notificação
e geração do conteúdo do lembrete no fluxo DOM (Domicílio Eletrônico).
"""

import unittest
from unittest.mock import MagicMock, patch

from bianca.dom_engine import (
    _checar_empresas_e_ids_api,
    _montar_conteudo_lembrete_dom,
)


class TestDomLembreteIdNotificacao(unittest.TestCase):
    """Garante que _checar_empresas_e_ids_api prioriza a Notificação individual

    sobre a Intimação/Despacho genérico compartilhado por várias partes.
    """

    def test_prioriza_notificacao_sobre_intimacao_generica(self):
        id_processo = "8885568"
        mock_driver = MagicMock()

        # Expedientes retornados pela API: a Intimação genérica (486923683) vem PRIMEIRO no array,
        # seguida pelas Notificações específicas (481290565, etc).
        expedientes_falsos = [
            # 0. Genéricos (Intimação compartilhada)
            {
                "id": 100,
                "nomePessoaParte": "M CASSAB COMERCIO E INDUSTRIA LTDA",
                "idDocumento": 486923683,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 101,
                "nomePessoaParte": "ASCENDANT COMERCIO DE VEICULOS LTDA",
                "idDocumento": 486923683,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 102,
                "nomePessoaParte": "CONDOMINIO SHOPPING JARDIM SUL",
                "idDocumento": 486923683,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            # 1. Específicos (Notificação individual para cada parte)
            {
                "id": 200,
                "nomePessoaParte": "SP MARKET ADMINISTRACAO E SERVICOS LTDA.",
                "idDocumento": 481290573,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 201,
                "nomePessoaParte": "BANCO CSF S/A",
                "idDocumento": 481290569,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 202,
                "nomePessoaParte": "ASCENDANT COMERCIO DE VEICULOS LTDA",
                "idDocumento": 481290570,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 203,
                "nomePessoaParte": "CONDOMINIO SHOPPING JARDIM SUL",
                "idDocumento": 481290566,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 204,
                "nomePessoaParte": "M CASSAB COMERCIO E INDUSTRIA LTDA",
                "idDocumento": 481290565,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
        ]

        documentos_mock = {
            486923683: {"id": 486923683, "titulo": "Intimação", "idUnicoDocumento": "7432019"},
            481290573: {"id": 481290573, "titulo": "Notificação", "idUnicoDocumento": "8201597"},
            481290569: {"id": 481290569, "titulo": "Notificação", "idUnicoDocumento": "030869f"},
            481290570: {"id": 481290570, "titulo": "Notificação", "idUnicoDocumento": "46fa065"},
            481290566: {"id": 481290566, "titulo": "Notificação", "idUnicoDocumento": "a011ede"},
            481290565: {"id": 481290565, "titulo": "Notificação", "idUnicoDocumento": "512224b"},
        }

        mock_client = MagicMock()
        mock_client.expedientes_processo.return_value = expedientes_falsos
        mock_client.documento_por_id.side_effect = lambda pid, doc_id: documentos_mock.get(doc_id)

        with patch("Fix.variaveis.session_from_driver", return_value=(MagicMock(), "https://base")), \
             patch("Fix.variaveis.PjeApiClient", return_value=mock_client), \
             patch("bianca.dom_engine._pjdp_do_passivo_api", return_value=[]):

            resultado = _checar_empresas_e_ids_api(id_processo, mock_driver)

        # Mapear resultado por empresa
        mapa = {d["empresa"]: d["id_unico_documento"] for d in resultado}

        # Verificação rigorosa: nenhuma deve receber o id 7432019 (Intimação genérica)
        self.assertNotIn("7432019", mapa.values(), "O ID genérico 7432019 não deve ser atribuído quando houver Notificação individual")

        # Cada empresa deve receber o ID exato da sua respectiva Notificação
        self.assertEqual(mapa["M CASSAB COMERCIO E INDUSTRIA LTDA"], "512224b")
        self.assertEqual(mapa["ASCENDANT COMERCIO DE VEICULOS LTDA"], "46fa065")
        self.assertEqual(mapa["CONDOMINIO SHOPPING JARDIM SUL"], "a011ede")
        self.assertEqual(mapa["SP MARKET ADMINISTRACAO E SERVICOS LTDA."], "8201597")
        self.assertEqual(mapa["BANCO CSF S/A"], "030869f")

    def test_montar_conteudo_lembrete_dom(self):
        destinatarios = [
            {"empresa": "M CASSAB", "id_unico_documento": "512224b"},
            {"empresa": "BANCO CSF", "id_unico_documento": "030869f"},
        ]
        conteudo = _montar_conteudo_lembrete_dom(destinatarios)
        self.assertEqual(
            conteudo,
            "Renovado por correio para (M CASSAB - 512224b), (BANCO CSF - 030869f)"
        )
        self.assertTrue(len(conteudo) <= 200)

    def test_montar_conteudo_lembrete_dom_truncamento_200(self):
        # Gera lista longa para testar limite do PJe
        destinatarios = [
            {"empresa": f"EMPRESA MUITO LONGA DE TESTE NUMERO {i} LTDA", "id_unico_documento": f"uid{i}abc"}
            for i in range(15)
        ]
        conteudo = _montar_conteudo_lembrete_dom(destinatarios)
        self.assertTrue(len(conteudo) <= 200)
        self.assertTrue(conteudo.startswith("Renovado por correio para "))

    @patch("bianca.dom_engine.has_dom_eletronico_reminder", return_value=False)
    @patch("bianca.dom_engine._checar_empresas_e_ids_api")
    @patch("bianca.dom_engine.criar_gigs")
    @patch("bianca.dom_engine.criar_comentario", return_value=True)
    @patch("bianca.dom_engine.criar_lembrete_posit", return_value=True)
    @patch("bianca.dom_engine.def_chip", return_value=True)
    @patch("bianca.dom_engine._verificar_acesso_negado")
    @patch("bianca.dom_engine._obter_abas", side_effect=[['aba1'], ['aba1', 'aba2']])
    @patch("bianca.dom_engine.pec_arordv", return_value=True)
    def test_callback_bucket2_executa_comentario_e_lembrete_sem_gigs(
        self,
        mock_pec,
        mock_abas,
        mock_acesso,
        mock_chip,
        mock_lembrete,
        mock_coment,
        mock_gigs,
        mock_checar_api,
        mock_verif_lembrete,
    ):
        """Verifica se callback_bucket2 executa apenas Comentário + Lembrete DomElet (sem GIGS)."""
        from bianca.dom_engine import ListaDestinatariosDOM, callback_bucket2

        mock_driver = MagicMock()
        mock_driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/8885568/detalhe"
        mock_driver._numero_processo_lista = "1000123-45.2026.5.02.0001"

        destinatarios_mock = ListaDestinatariosDOM([
            {"empresa": "BANCO CSF", "id_unico_documento": "030869f"},
        ])
        destinatarios_mock.pjdp_detectado = []
        mock_checar_api.return_value = destinatarios_mock

        processo_info = {"dataAudiencia": "2026-11-02 09:00:00"}  # segunda-feira

        with patch("bianca.dom_engine._dia_semana_audiencia", return_value=0):
            res = callback_bucket2(mock_driver, tipo_processo="ATOrd", processo_info=processo_info)

        self.assertTrue(res)
        # GIGS NÃO deve ser criado
        mock_gigs.assert_not_called()
        # Comentário deve ser criado
        mock_coment.assert_called_once_with(mock_driver, "DOM", log=True)
        # Lembrete Post-it DomElet deve ser criado
        mock_lembrete.assert_called_once_with(
            mock_driver,
            "DomElet",
            "Renovado por correio para (BANCO CSF - 030869f)",
            debug=True,
        )
        self.assertEqual(mock_chip.call_count, 2)
        mock_pec.assert_called_once()


if __name__ == "__main__":
    unittest.main()

