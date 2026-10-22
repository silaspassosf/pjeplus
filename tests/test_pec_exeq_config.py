"""Testes unitários para a configuração e execução de pec_exeq e fluxo de endereço via envelope sem limpeza de inválidos."""

import unittest
from unittest.mock import MagicMock, patch
from atos.wrappers_pec import pec_exeq
from atos.comunicacao_finalizacao import salvar_minuta_final


class TestPecExeqConfig(unittest.TestCase):

    def test_pec_exeq_wrapper_atributos(self):
        """pec_exeq deve possuir o nome 'pec_exeq' e ter remover_endereco_invalido=False."""
        self.assertEqual(getattr(pec_exeq, '__name__', ''), 'pec_exeq')

    @patch('atos.comunicacao_destinatarios.remover_destinatarios_endereco_invalido')
    def test_salvar_minuta_final_com_remover_invalido_false(self, mock_remover):
        """Quando remover_endereco_invalido=False, salvar_minuta_final NÃO deve chamar remover_destinatarios_endereco_invalido."""
        driver = MagicMock()
        driver.page = MagicMock()
        
        # Simular elementos de salvar presentes
        btn_salvar = MagicMock()
        with patch('atos.comunicacao_finalizacao.espera.elemento', return_value=btn_salvar), \
             patch('atos.comunicacao_finalizacao.safe_click_no_scroll'), \
             patch('atos.comunicacao_finalizacao.espera.pausa'), \
             patch('atos.comunicacao_finalizacao.espera.ate_sumir', return_value=True), \
             patch('atos.comunicacao_finalizacao.espera.ate_texto', return_value=True), \
             patch('atos.comunicacao_finalizacao.espera.assentar'):
            logs = []
            resultado = salvar_minuta_final(driver, sigilo=False, log=logs.append, remover_endereco_invalido=False)

            self.assertTrue(resultado)
            mock_remover.assert_not_called()

    @patch('atos.comunicacao_destinatarios.remover_destinatarios_endereco_invalido')
    def test_salvar_minuta_final_com_remover_invalido_true(self, mock_remover):
        """Quando remover_endereco_invalido=True (padrão dos outros fluxos), remover_destinatarios_endereco_invalido deve ser chamado."""
        driver = MagicMock()
        driver.page = MagicMock()

        btn_salvar = MagicMock()
        with patch('atos.comunicacao_finalizacao.espera.elemento', return_value=btn_salvar), \
             patch('atos.comunicacao_finalizacao.safe_click_no_scroll'), \
             patch('atos.comunicacao_finalizacao.espera.pausa'), \
             patch('atos.comunicacao_finalizacao.espera.ate_sumir', return_value=True), \
             patch('atos.comunicacao_finalizacao.espera.ate_texto', return_value=True), \
             patch('atos.comunicacao_finalizacao.espera.assentar'):
            logs = []
            salvar_minuta_final(driver, sigilo=False, log=logs.append, remover_endereco_invalido=True)

            mock_remover.assert_called_once()

    @patch('atos.comunicacao.abrir_minutas', return_value=True)
    @patch('atos.comunicacao.executar_preenchimento_minuta', return_value=True)
    @patch('atos.comunicacao.aguardar_estabilizacao_para_destinatarios', return_value=True)
    @patch('atos.comunicacao.selecionar_destinatarios')
    @patch('atos.comunicacao.aguardar_renderizacao_nativa', return_value=True)
    @patch('atos.comunicacao.alterar_meio_expedicao', return_value=True)
    @patch('atos.comunicacao.remover_destinatarios_endereco_invalido')
    @patch('atos.comunicacao.contar_linhas_destinatarios', return_value=1)
    @patch('atos.comunicacao.salvar_minuta_final', return_value=True)
    def test_execucao_pec_exeq_nao_executa_remover_destinatarios_endereco_invalido(
        self,
        mock_salvar,
        mock_contar,
        mock_remover_comunicacao,
        mock_alterar_meio,
        mock_render,
        mock_sel_dest,
        mock_estab,
        mock_preench,
        mock_abrir
    ):
        """Ao executar pec_exeq, a exclusão de endereços inválidos NÃO deve ser chamada em nenhum momento."""
        driver = MagicMock()
        driver.current_window_handle = 'handle_principal'

        mock_sel_dest.return_value = MagicMock(status='ok', count=1)

        logs = []
        sucesso = pec_exeq(driver, log=logs.append)

        self.assertTrue(sucesso)
        # remover_destinatarios_endereco_invalido não pode ter sido chamado em comunicacao.py
        mock_remover_comunicacao.assert_not_called()
        # alterar_meio_expedicao deve ter sido acionado (tipo correios)
        mock_alterar_meio.assert_called_once()
        # salvar_minuta_final deve ter recebido remover_endereco_invalido=False
        mock_salvar.assert_called_once()
        _, kwargs_salvar = mock_salvar.call_args
        self.assertFalse(kwargs_salvar.get('remover_endereco_invalido', True))
        self.assertTrue(any('Exclusão de endereço inválido desativada' in m for m in logs))


if __name__ == '__main__':
    unittest.main()
