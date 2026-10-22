# -*- coding: utf-8 -*-
"""Testes unitários para busca de Notificação na fase de Conhecimento na função de carta."""

import unittest
from unittest.mock import MagicMock, patch

from PEC.carta_execucao import (
    _eh_documento_alvo,
    _eh_fase_conhecimento,
    _obter_fase_processo,
    _processar_item,
)


class TestPECCartaNotificacao(unittest.TestCase):

    def test_eh_documento_alvo_intimacao(self):
        """Intimação deve ser aceita independentemente de buscar_notificacao ser True ou False."""
        self.assertTrue(_eh_documento_alvo("Intimação(Intimação) - 95d7f08", buscar_notificacao=False))
        self.assertTrue(_eh_documento_alvo("Intimação(Intimação) - 95d7f08", buscar_notificacao=True))
        self.assertTrue(_eh_documento_alvo("Intimacao - 95d7f08", buscar_notificacao=False))

    def test_eh_documento_alvo_notificacao(self):
        """Notificação só deve ser aceita se buscar_notificacao for True (fase de conhecimento)."""
        self.assertFalse(_eh_documento_alvo("Notificação(Notificação Inicial) - ff81647", buscar_notificacao=False))
        self.assertTrue(_eh_documento_alvo("Notificação(Notificação Inicial) - ff81647", buscar_notificacao=True))
        self.assertTrue(_eh_documento_alvo("Notificação(Notificação) - ff81647", buscar_notificacao=True))
        self.assertTrue(_eh_documento_alvo("Notificacao - ff81647", buscar_notificacao=True))

    def test_eh_documento_alvo_outros_tipos(self):
        """Outros tipos documentais não devem ser aceitos."""
        self.assertFalse(_eh_documento_alvo("Despacho - 12345", buscar_notificacao=True))
        self.assertFalse(_eh_documento_alvo("Sentença - 12345", buscar_notificacao=True))
        self.assertFalse(_eh_documento_alvo("Petição - 12345", buscar_notificacao=True))
        self.assertFalse(_eh_documento_alvo("", buscar_notificacao=True))

    @patch("PEC.carta_execucao._obter_fase_processo")
    def test_eh_fase_conhecimento(self, mock_fase):
        """Verifica detecção da fase de conhecimento."""
        mock_fase.return_value = "Conhecimento"
        self.assertTrue(_eh_fase_conhecimento(MagicMock()))

        mock_fase.return_value = "CONHECIMENTO"
        self.assertTrue(_eh_fase_conhecimento(MagicMock()))

        mock_fase.return_value = "Fase de Conhecimento"
        self.assertTrue(_eh_fase_conhecimento(MagicMock()))

        mock_fase.return_value = "Execução"
        self.assertFalse(_eh_fase_conhecimento(MagicMock()))

        mock_fase.return_value = "Liquidação"
        self.assertFalse(_eh_fase_conhecimento(MagicMock()))

        mock_fase.return_value = ""
        self.assertFalse(_eh_fase_conhecimento(MagicMock()))

    @patch("Fix.core.extrair_id_processo", return_value="123456")
    @patch("Fix.variaveis.cliente_para")
    def test_obter_fase_processo_api(self, mock_cliente_para, mock_extrair_id):
        """Chamada de API retorna labelFaseProcessual corretamente."""
        mock_client = MagicMock()
        mock_client.processo_por_id.return_value = {"labelFaseProcessual": "Conhecimento"}
        mock_cliente_para.return_value = mock_client

        fase = _obter_fase_processo(MagicMock(), log=False)
        self.assertEqual(fase, "Conhecimento")
        mock_client.processo_por_id.assert_called_once_with("123456")

    @patch("PEC.carta_execucao._sub_elemento")
    def test_processar_item_ignora_notificacao_quando_fora_conhecimento(self, mock_sub):
        """Item Notificação deve ser ignorado quando buscar_notificacao for False."""
        mock_link = MagicMock()
        mock_link.text_content.return_value = "Notificação(Notificação Inicial) - abc1234"
        mock_sub.return_value = mock_link

        resultado = _processar_item(MagicMock(), MagicMock(), "teste", log=False, buscar_notificacao=False)
        self.assertIsNone(resultado)


if __name__ == "__main__":
    unittest.main()
