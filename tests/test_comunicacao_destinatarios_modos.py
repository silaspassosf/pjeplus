"""Testes unitários para modos 'primeiro' e 'terceiros' em selecionar_destinatarios."""

import unittest
from unittest.mock import MagicMock, patch
from atos.comunicacao_destinatarios import selecionar_destinatarios


class TestComunicacaoDestinatariosModos(unittest.TestCase):

    def setUp(self):
        self.driver = MagicMock()
        self.page = MagicMock()
        self.driver.page = self.page

    @patch('atos.comunicacao_destinatarios.wait_for_clickable')
    @patch('atos.comunicacao_destinatarios._clicar_e_aguardar_spinner')
    def test_terceiros_com_terceiros_disponiveis(self, mock_spinner, mock_wait):
        """Polo passivo 1x adicionado e terceiros adicionados quando botão habilitado."""
        btn_pp = MagicMock()
        mock_wait.return_value = btn_pp

        btn_terceiro = MagicMock()
        btn_terceiro._js.return_value = False  # is_disabled = False

        with patch('atos.comunicacao_destinatarios.espera.elemento', return_value=btn_terceiro):
            logs = []
            res = selecionar_destinatarios(self.driver, destinatarios='terceiros', log=logs.append)

            self.assertTrue(res.sucesso)
            self.assertEqual(res.status, 'geral')
            self.assertTrue(res.detalhes['polo_passivo'])
            self.assertTrue(res.detalhes['terceiros'])
            mock_spinner.assert_any_call(self.driver, btn_pp)
            mock_spinner.assert_any_call(self.driver, btn_terceiro)

    @patch('atos.comunicacao_destinatarios.wait_for_clickable')
    @patch('atos.comunicacao_destinatarios._clicar_e_aguardar_spinner')
    def test_terceiros_sem_terceiros_nao_falha(self, mock_spinner, mock_wait):
        """Quando não há terceiros (botão desabilitado), salva apenas com polo passivo sem falhar."""
        btn_pp = MagicMock()
        mock_wait.return_value = btn_pp

        btn_terceiro = MagicMock()
        btn_terceiro._js.return_value = True  # is_disabled = True

        with patch('atos.comunicacao_destinatarios.espera.elemento', return_value=btn_terceiro):
            logs = []
            res = selecionar_destinatarios(self.driver, destinatarios='terceiros', log=logs.append)

            self.assertTrue(res.sucesso)
            self.assertEqual(res.status, 'geral')
            self.assertTrue(res.detalhes['polo_passivo'])
            self.assertFalse(res.detalhes['terceiros'])
            mock_spinner.assert_called_once_with(self.driver, btn_pp)
            self.assertTrue(any('sem terceiros no processo' in m for m in logs))

    @patch('atos.comunicacao_destinatarios.aguardar_renderizacao_nativa', return_value=True)
    def test_primeiro_destinatario_sucesso(self, mock_render):
        """Modo primeiro expande polo passivo e clica no primeiro destinatário."""
        # Mock do JS do page.evaluate: expansão e clique
        self.page.evaluate.side_effect = [
            {'ok': True, 'clicou': True},   # expansão do header
            {'ok': True, 'seletor': 'button.icone-clicavel'},  # clique no 1º botão
        ]

        with patch('atos.comunicacao_destinatarios.espera.elemento', return_value=None), \
             patch('atos.comunicacao_destinatarios.espera.assentar'):
            logs = []
            res = selecionar_destinatarios(self.driver, destinatarios='primeiro', log=logs.append)

            self.assertTrue(res.sucesso)
            self.assertEqual(res.status, 'ok')
            self.assertEqual(res.detalhes['count'], 1)
            self.assertTrue(any('Primeira seta (primeiro destinatário) clicada' in m for m in logs))


if __name__ == '__main__':
    unittest.main()
