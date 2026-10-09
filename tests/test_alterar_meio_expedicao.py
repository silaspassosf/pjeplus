"""Testes unitários para alterar_meio_expedicao."""

import unittest
from unittest.mock import MagicMock, patch
from atos.comunicacao_finalizacao import alterar_meio_expedicao


class TestAlterarMeioExpedicao(unittest.TestCase):

    def setUp(self):
        self.driver = MagicMock()
        self.page = MagicMock()
        self.driver.page = self.page

    @patch('atos.comunicacao_finalizacao.aguardar_renderizacao_nativa', return_value=True)
    @patch('atos.comunicacao_finalizacao.esperar_elemento', return_value=True)
    @patch('atos.comunicacao_finalizacao.safe_click_no_scroll')
    def test_altera_diario_eletronico_para_correio(self, mock_click, mock_esperar, mock_aguardar):
        """Linha com 'Diário Eletrônico' deve ser identificada e alterada para Correio."""
        # Mock da linha com _js retornando 'Diário Eletrônico'
        linha_diario = MagicMock()
        linha_diario._js.return_value = 'Diário Eletrônico'

        # Mock das opções do dropdown
        opcao_edital = MagicMock()
        opcao_edital.text = 'Edital'
        opcao_correio = MagicMock()
        opcao_correio.text = 'Correios'

        dropdown_mock = MagicMock()

        def mock_elementos(drv, sel, teto=2):
            if 'mat-option' in sel:
                return [opcao_edital, opcao_correio]
            if 'tbody.cdk-drop-list tr.cdk-drag' in sel:
                return [linha_diario]
            return []

        def mock_elemento(drv, sel, teto=2, **kwargs):
            if 'mat-select' in sel:
                return dropdown_mock
            return None

        with patch('atos.comunicacao_finalizacao.espera.elementos', side_effect=mock_elementos), \
             patch('atos.comunicacao_finalizacao.espera.elemento', side_effect=mock_elemento), \
             patch('atos.comunicacao_finalizacao.espera.ate_js', return_value=True):
            logs = []
            sucesso = alterar_meio_expedicao(self.driver, debug=True, log=logs.append)

            self.assertTrue(sucesso)
            # Verifica que dropdown foi clicado
            mock_click.assert_any_call(self.driver, dropdown_mock)
            # Verifica que a opção 'Correios' foi clicada
            mock_click.assert_any_call(self.driver, opcao_correio)
            # Verifica log
            self.assertTrue(any('Diário Eletrônico' in m for m in logs))
            self.assertTrue(any('Alterados: 1' in m for m in logs))

    @patch('atos.comunicacao_finalizacao.aguardar_renderizacao_nativa', return_value=True)
    @patch('atos.comunicacao_finalizacao.safe_click_no_scroll')
    def test_pula_linha_ja_em_correios(self, mock_click, mock_aguardar):
        """Linha já em 'Correios' não deve ser alterada."""
        linha_correio = MagicMock()
        linha_correio._js.return_value = 'Correios'

        def mock_elementos(drv, sel, teto=2):
            if 'tbody.cdk-drop-list tr.cdk-drag' in sel:
                return [linha_correio]
            return []

        with patch('atos.comunicacao_finalizacao.espera.elementos', side_effect=mock_elementos), \
             patch('atos.comunicacao_finalizacao.espera.ate_js', return_value=True):
            logs = []
            sucesso = alterar_meio_expedicao(self.driver, debug=True, log=logs.append)

            self.assertTrue(sucesso)
            # Nenhum clique deve ter ocorrido
            mock_click.assert_not_called()
            self.assertTrue(any('Alterados: 0' in m for m in logs))
            self.assertTrue(any('Não precisavam: 1' in m for m in logs))

    @patch('atos.comunicacao_finalizacao.aguardar_renderizacao_nativa', return_value=True)
    @patch('atos.comunicacao_finalizacao.esperar_elemento', return_value=True)
    @patch('atos.comunicacao_finalizacao.safe_click_no_scroll')
    def test_altera_domicilio_eletronico(self, mock_click, mock_esperar, mock_aguardar):
        """Linha com 'Domicílio Eletrônico' continua sendo alterada para Correio."""
        linha_dom = MagicMock()
        linha_dom._js.return_value = 'Domicílio Eletrônico'

        opcao_correio = MagicMock()
        opcao_correio.text = 'Correio'
        dropdown_mock = MagicMock()

        def mock_elementos(drv, sel, teto=2):
            if 'mat-option' in sel:
                return [opcao_correio]
            if 'tbody.cdk-drop-list tr.cdk-drag' in sel:
                return [linha_dom]
            return []

        def mock_elemento(drv, sel, teto=2, **kwargs):
            if 'mat-select' in sel:
                return dropdown_mock
            return None

        with patch('atos.comunicacao_finalizacao.espera.elementos', side_effect=mock_elementos), \
             patch('atos.comunicacao_finalizacao.espera.elemento', side_effect=mock_elemento), \
             patch('atos.comunicacao_finalizacao.espera.ate_js', return_value=True):
            logs = []
            sucesso = alterar_meio_expedicao(self.driver, debug=True, log=logs.append)

            self.assertTrue(sucesso)
            mock_click.assert_any_call(self.driver, opcao_correio)
            self.assertTrue(any('Alterados: 1' in m for m in logs))

    @patch('atos.comunicacao_finalizacao.vincular_primeiro_endereco_valido')
    @patch('atos.comunicacao_finalizacao.aguardar_renderizacao_nativa', return_value=True)
    @patch('atos.comunicacao_finalizacao.esperar_elemento', return_value=True)
    @patch('atos.comunicacao_finalizacao.safe_click_no_scroll')
    def test_alterar_meio_expedicao_chama_vincular_endereco(self, mock_click, mock_esperar, mock_aguardar, mock_vincular):
        """Ao alterar para Correio, vincular_primeiro_endereco_valido deve ser chamado para a linha."""
        linha_diario = MagicMock()
        linha_diario._js.return_value = 'Diário Eletrônico'

        opcao_correio = MagicMock()
        opcao_correio.text = 'Correios'
        dropdown_mock = MagicMock()

        def mock_elementos(drv, sel, teto=2):
            if 'mat-option' in sel:
                return [opcao_correio]
            if 'tbody.cdk-drop-list tr.cdk-drag' in sel:
                return [linha_diario]
            return []

        def mock_elemento(drv, sel, teto=2, **kwargs):
            if 'mat-select' in sel:
                return dropdown_mock
            return None

        with patch('atos.comunicacao_finalizacao.espera.elementos', side_effect=mock_elementos), \
             patch('atos.comunicacao_finalizacao.espera.elemento', side_effect=mock_elemento), \
             patch('atos.comunicacao_finalizacao.espera.ate_js', return_value=True):
            logs = []
            sucesso = alterar_meio_expedicao(self.driver, debug=True, log=logs.append)

            self.assertTrue(sucesso)
            mock_vincular.assert_called_once_with(self.driver, linha=linha_diario, idx=1, debug=True, log=unittest.mock.ANY)

    @patch('atos.comunicacao_finalizacao.aguardar_renderizacao_nativa', return_value=True)
    def test_vincular_primeiro_endereco_valido_via_js(self, mock_aguardar):
        """vincular_primeiro_endereco_valido deve clicar envelope, selecionar primeira seta e fechar modal via evaluate."""
        from atos.comunicacao_finalizacao import vincular_primeiro_endereco_valido

        # Mock das 3 chamadas JS evaluate: envelope, seta, fechar modal
        self.page.evaluate.side_effect = [
            {'ok': True},  # envelope
            {'ok': True, 'seletor': 'button[aria-label="Selecionar endereço"]'},  # seta
            {'ok': True, 'fechado_via': 'a[mattooltip="Fechar"]'},  # fechar
        ]

        modal_mock = MagicMock()
        with patch('atos.comunicacao_finalizacao.espera.elemento', return_value=modal_mock), \
             patch('atos.comunicacao_finalizacao.espera.assentar'):
            logs = []
            resultado = vincular_primeiro_endereco_valido(self.driver, idx=1, debug=True, log=logs.append)

            self.assertTrue(resultado)
            self.assertEqual(self.page.evaluate.call_count, 3)
            self.assertTrue(any('Primeira seta para cima selecionada' in m for m in logs))
            self.assertTrue(any('Diálogo de endereços fechado' in m for m in logs))

    @patch('atos.comunicacao_finalizacao.aguardar_renderizacao_nativa', return_value=True)
    @patch('atos.comunicacao_finalizacao.safe_click_no_scroll')
    def test_vincular_primeiro_endereco_valido_fallback_locators(self, mock_click, mock_aguardar):
        """vincular_primeiro_endereco_valido deve usar fallback para locators quando evaluate falhar/retornar False."""
        from atos.comunicacao_finalizacao import vincular_primeiro_endereco_valido

        # evaluate falha ou retorna ok: False
        self.page.evaluate.side_effect = [
            {'ok': False},
            {'ok': False},
            {'ok': False},
        ]

        btn_env_mock = MagicMock()
        modal_mock = MagicMock()
        btn_seta_mock = MagicMock()
        btn_fechar_mock = MagicMock()

        def mock_elemento(drv, sel, teto=2, **kwargs):
            if 'fa-envelope' in sel or 'coluna-endereco' in sel:
                return btn_env_mock
            if 'pje-pec-dialogo-endereco' in sel or 'mat-dialog-container' in sel:
                if 'Selecionar endereço' in sel or 'fa-arrow-up' in sel:
                    return btn_seta_mock
                if 'Fechar' in sel or 'window-close' in sel:
                    return btn_fechar_mock
                return modal_mock
            return None

        with patch('atos.comunicacao_finalizacao.espera.elemento', side_effect=mock_elemento), \
             patch('atos.comunicacao_finalizacao.espera.assentar'):
            logs = []
            resultado = vincular_primeiro_endereco_valido(self.driver, idx=1, debug=True, log=logs.append)

            self.assertTrue(resultado)
            # safe_click_no_scroll deve ter sido chamado para envelope, seta e fechar
            mock_click.assert_any_call(self.driver, btn_env_mock)
            mock_click.assert_any_call(self.driver, btn_seta_mock)
            mock_click.assert_any_call(self.driver, btn_fechar_mock)


if __name__ == '__main__':
    unittest.main()
