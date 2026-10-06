"""Testes unitários para o módulo de movimento judicial (atos e complementos)."""

import unittest
from unittest.mock import MagicMock
from Fix.facade_publica import (
    executar_movimento_judicial,
    selecionar_movimento_dois_estagios,
    selecionar_movimento_auto,
)


class TestMovimentoJudicial(unittest.TestCase):

    def setUp(self):
        self.driver = MagicMock()
        self.page = MagicMock()
        self.driver.page = self.page

    def test_movimento_vazio_ou_nenhum_retorna_true(self):
        self.assertTrue(executar_movimento_judicial(self.driver, None))
        self.assertTrue(executar_movimento_judicial(self.driver, ""))
        self.assertTrue(executar_movimento_judicial(self.driver, "nenhum"))
        self.assertTrue(executar_movimento_judicial(self.driver, "false"))
        self.assertEqual(self.page.evaluate.call_count, 0)

    def test_executar_movimento_multi_estagios_sucesso(self):
        self.page.evaluate.return_value = {
            'sucesso': True,
            'movimento': '219 / incidente de desco / polo ativo',
        }
        res = executar_movimento_judicial(self.driver, '219 / incidente de desco / polo ativo')
        self.assertTrue(res)
        self.page.evaluate.assert_called_once()
        args = self.page.evaluate.call_args[0]
        self.assertEqual(args[1], '219 / incidente de desco / polo ativo')

    def test_executar_movimento_falha_retorna_false(self):
        self.page.evaluate.return_value = {
            'sucesso': False,
            'erro': 'Opção do dropdown não encontrada: polo ativo',
        }
        res = executar_movimento_judicial(self.driver, '219 / incidente de desco / polo ativo')
        self.assertFalse(res)

    def test_delegacao_selecionar_movimento_dois_estagios(self):
        self.page.evaluate.return_value = {'sucesso': True}
        res = selecionar_movimento_dois_estagios(self.driver, '219 / incidente de desco / polo ativo')
        self.assertTrue(res)

    def test_delegacao_selecionar_movimento_auto(self):
        self.page.evaluate.return_value = {'sucesso': True}
        res = selecionar_movimento_auto(self.driver, 'frustrada')
        self.assertTrue(res)


if __name__ == '__main__':
    unittest.main()
