import unittest
from unittest.mock import MagicMock, patch

from atos.movimentos_navegacao import (
    _normalizar_texto,
    _normalizar_tarefa,
    clicar_botao_por_texto,
    movimentar_analise,
    navegar_para_tarefa,
)
from atos.movimentos_fluxo import movimentar_inteligente


class TestMovimentosNavegacao(unittest.TestCase):

    def test_normalizacao_texto_e_tarefa(self):
        # Acentos e quebras de linha removidos
        self.assertEqual(
            _normalizar_texto("Responsável do Processo\nSem Responsável\nTarefa:\nCumprimento de Providências"),
            "responsavel do processo sem responsavel tarefa: cumprimento de providencias"
        )
        self.assertEqual(
            _normalizar_tarefa("Preparar Expedientes e Comunicações"),
            "comunicacoes e expedientes"
        )
        self.assertEqual(
            _normalizar_tarefa("Aguardando Cumprimento de Acordo"),
            "controle de acordo"
        )

    def test_clicar_botao_por_texto_via_js(self):
        driver = MagicMock()
        mock_exec = MagicMock(return_value=True)
        setattr(driver, 'execute_script', mock_exec)

        sucesso = clicar_botao_por_texto(driver, "Análise")
        self.assertTrue(sucesso)
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        self.assertEqual(args[1], {'texto': 'Análise', 'tag': 'button'})

    def test_movimentar_analise_conclusao(self):
        driver = MagicMock()
        mock_exec = MagicMock(return_value=True)
        setattr(driver, 'execute_script', mock_exec)

        with patch('atos.movimentos_navegacao.esperar_transicao_tarefa', return_value=True):
            sucesso = movimentar_analise(driver, "Conclusão ao Magistrado")
            self.assertTrue(sucesso)
            # Deve ter clicado no botão 'cancelar Conclusao'
            call_args = mock_exec.call_args[0]
            self.assertEqual(call_args[1]['texto'], 'cancelar Conclusao')

    def test_movimentar_analise_cumprimento_providencias(self):
        driver = MagicMock()
        mock_exec = MagicMock(return_value=True)
        setattr(driver, 'execute_script', mock_exec)

        with patch('atos.movimentos_navegacao.esperar_transicao_tarefa', return_value=True):
            sucesso = movimentar_analise(driver, "Cumprimento de Providências")
            self.assertTrue(sucesso)
            # Deve ter clicado no botão default 'analise'
            call_args = mock_exec.call_args[0]
            self.assertEqual(call_args[1]['texto'], 'analise')

    def test_movimentar_inteligente_cumprimento_para_aguardando_prazo(self):
        driver = MagicMock()
        
        # Simula: 1ª chamada está em Cumprimento de Providências.
        # Transiciona para Análise, e 2ª chamada está em Análise e clica Aguardando Prazo.
        tarefas = [
            "Responsável do Processo\nSem Responsável\nTarefa:\nCumprimento de Providências",
            "Análise"
        ]
        
        with patch('atos.movimentos_fluxo.abrir_tarefa_por_api', return_value=True), \
             patch('atos.movimentos_fluxo._tarefa_atual_via_api', return_value=None), \
             patch('atos.movimentos_fluxo._obter_tarefa_atual_robusta', side_effect=tarefas), \
             patch('atos.movimentos_navegacao.clicar_botao_por_texto', return_value=True), \
             patch('atos.movimentos_navegacao.esperar_transicao_tarefa', return_value=True):

            ok = movimentar_inteligente(driver, "Aguardando Prazo")
            self.assertTrue(ok)


if __name__ == '__main__':
    unittest.main()
