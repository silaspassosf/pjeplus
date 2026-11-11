import unittest
from unittest.mock import MagicMock, patch

from atos import judicial_navegacao as nav
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
    def test_navegar_para_conclusao_clique_direto_prazos_vencidos(self, mock_render):
        """Em "Prazos Vencidos" o botão NÃO tem aria-label.

        O DOM real é `nav.container-botoes > button > span.mat-button-wrapper >
        div.texto-botao-app`. A primeira tentativa tem de ser o texto dentro
        desse container — buscar aria-label primeiro custava 6s fixos
        (NAVEGAR_CONCLUSAO saía em ~7,1s em todas as execuções).
        """
        driver = MagicMock()
        driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/123/tarefa/456"
        driver.pje_tarefa_atual = "prazos vencidos"

        with patch.object(nav, 'esperar_elemento', return_value=MagicMock()) as por_texto, \
             patch.object(nav, 'safe_click_no_scroll') as clicar, \
             patch.object(nav.espera, 'elemento') as por_aria, \
             patch.object(nav.espera, 'ate_aparecer', return_value=True), \
             patch.object(nav, 'navegar_para_tarefa') as rotear:
            sucesso = navegar_para_conclusao(driver)

        self.assertTrue(sucesso)
        # 1ª tentativa: texto dentro do container real da barra de transição.
        por_texto.assert_any_call(
            driver, 'nav.container-botoes button',
            texto='Conclusão ao magistrado', timeout=6)
        # O aria-label é só reserva: num acerto de primeira não pode rodar.
        por_aria.assert_not_called()
        clicar.assert_called_once()
        rotear.assert_not_called()

    @patch('atos.judicial_navegacao.aguardar_renderizacao_nativa', return_value=True)
    def test_navegar_para_conclusao_via_analise_quando_direto_falha(self, mock_render):
        driver = MagicMock()
        driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/123/tarefa/456"
        driver.pje_tarefa_atual = "Cumprimento de Providencias"

        # 1ª busca (container) falha, aria-label falha e o `button` amplo
        # também; depois do Análise, o container acha o botão.
        with patch.object(nav, 'esperar_elemento',
                          side_effect=[None, None, MagicMock()]) as por_texto, \
             patch.object(nav, 'safe_click_no_scroll'), \
             patch.object(nav.espera, 'elemento', return_value=None), \
             patch.object(nav.espera, 'ate_aparecer', return_value=True), \
             patch.object(nav, 'navegar_para_tarefa', return_value=True) as rotear:
            sucesso = navegar_para_conclusao(driver)

        self.assertTrue(sucesso)
        rotear.assert_called_once()
        self.assertEqual(por_texto.call_count, 3)


if __name__ == '__main__':
    unittest.main()
