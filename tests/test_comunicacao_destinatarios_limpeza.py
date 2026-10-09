"""Testes unitários para exclusão de destinatários com endereço inválido na tabela de expedientes."""

import unittest
from unittest.mock import MagicMock
from atos.comunicacao_destinatarios import (
    remover_destinatarios_endereco_invalido,
    contar_linhas_destinatarios,
)


class TestComunicacaoDestinatariosLimpeza(unittest.TestCase):

    def setUp(self):
        self.driver = MagicMock()
        self.page = MagicMock()
        self.driver.page = self.page

    def test_sem_icone_vermelho_nao_remove(self):
        # Quando não há ícones vermelhos, evaluate retorna encontrado=False
        self.page.evaluate.return_value = {'encontrado': False}
        removidos = remover_destinatarios_endereco_invalido(self.driver)
        self.assertEqual(removidos, 0)
        self.page.evaluate.assert_called_once()

    def test_um_icone_vermelho_remove_com_sucesso(self):
        # Primeira chamada encontra e exclui; segunda chamada não encontra mais
        self.page.evaluate.side_effect = [
            {'encontrado': True, 'excluido': True, 'nome': 'PARTE TESTE', 'endereco': 'AV BRASIL'},
            {'encontrado': False},
        ]
        logs = []
        removidos = remover_destinatarios_endereco_invalido(self.driver, log=logs.append)
        self.assertEqual(removidos, 1)
        self.assertEqual(self.page.evaluate.call_count, 2)
        self.assertTrue(any('PARTE TESTE' in m for m in logs))

    def test_multiplos_icones_vermelhos_remove_todos(self):
        # Duas linhas inválidas removidas sequencialmente
        self.page.evaluate.side_effect = [
            {'encontrado': True, 'excluido': True, 'nome': 'PARTE 1', 'endereco': 'END 1'},
            {'encontrado': True, 'excluido': True, 'nome': 'PARTE 2', 'endereco': 'END 2'},
            {'encontrado': False},
        ]
        removidos = remover_destinatarios_endereco_invalido(self.driver)
        self.assertEqual(removidos, 2)
        self.assertEqual(self.page.evaluate.call_count, 3)

    def test_falha_ao_clicar_botao_excluir_interrompe_loop(self):
        # Encontra ícone vermelho mas botão não é achado/clicável
        self.page.evaluate.return_value = {
            'encontrado': True,
            'excluido': False,
            'erro': 'btn_excluir_nao_encontrado',
        }
        logs = []
        removidos = remover_destinatarios_endereco_invalido(self.driver, log=logs.append)
        self.assertEqual(removidos, 0)
        self.page.evaluate.assert_called_once()
        self.assertTrue(any('WARN' in m for m in logs))

    def test_contar_linhas_destinatarios(self):
        self.page.evaluate.return_value = 3
        contagem = contar_linhas_destinatarios(self.driver)
        self.assertEqual(contagem, 3)

        self.page.evaluate.return_value = 0
        contagem_zero = contar_linhas_destinatarios(self.driver)
        self.assertEqual(contagem_zero, 0)


if __name__ == '__main__':
    unittest.main()
