import unittest
from unittest.mock import MagicMock, patch

from atos.judicial_navegacao import (
    _localizar_botao_navegacao,
    navegar_para_conclusao,
)


class TestJudicialNavegacao(unittest.TestCase):

    def test_navegar_para_conclusao_ja_em_conclusao(self):
        driver = MagicMock()
        driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/123/tarefa/456/conclusao"
        self.assertTrue(navegar_para_conclusao(driver))

    def test_navegar_para_conclusao_ja_em_minutar(self):
        driver = MagicMock()
        driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/123/tarefa/456/minutar"
        self.assertTrue(navegar_para_conclusao(driver))

    @patch('atos.judicial_navegacao.aguardar_renderizacao_nativa', return_value=True)
    @patch('atos.judicial_navegacao.clicar_botao_por_texto')
    def test_navegar_para_conclusao_clique_direto_prazos_vencidos(self, mock_clique, mock_render):
        driver = MagicMock()
        driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/123/tarefa/456"
        driver.pje_tarefa_atual = "prazos vencidos"

        # Clique direto em "conclusao ao magistrado" tem sucesso
        mock_clique.return_value = True

        sucesso = navegar_para_conclusao(driver)
        self.assertTrue(sucesso)
        # Verifica se tentou clique direto em conclusao ao magistrado
        mock_clique.assert_any_call(driver, 'conclusao ao magistrado', timeout=3, debug=True)

    @patch('atos.judicial_navegacao.aguardar_renderizacao_nativa', return_value=True)
    @patch('atos.judicial_navegacao.limpar_overlays')
    @patch('atos.judicial_navegacao.movimentar_analise', return_value=True)
    @patch('atos.judicial_navegacao.clicar_botao_por_texto')
    def test_navegar_para_conclusao_via_analise_quando_direto_falha(self, mock_clique, mock_mov, mock_overlays, mock_render):
        driver = MagicMock()
        driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/123/tarefa/456"
        driver.pje_tarefa_atual = "aguardando prazo"

        # 1ª e 2ª chamadas (diretas: 'conclusao ao magistrado' e 'conclusao') falham (False)
        # 3ª chamada (após Análise: 'conclusao ao magistrado') tem sucesso (True)
        mock_clique.side_effect = [False, False, True]

        with patch('atos.judicial_navegacao._localizar_botao_navegacao', return_value=None):
            sucesso = navegar_para_conclusao(driver)
            self.assertTrue(sucesso)
            mock_mov.assert_called_once_with(driver, "aguardando prazo", debug=True)


if __name__ == '__main__':
    unittest.main()
