"""
tests/test_seletores_catalogo.py - Testes unitários do catálogo centralizado de seletores.
"""

import unittest
from unittest.mock import MagicMock, patch
from Fix.seletores_catalogo import CatalogoSeletores, SeletorRegistro


class TestSeletoresCatalogo(unittest.TestCase):

    def setUp(self):
        self.cat = CatalogoSeletores()

    def test_registro_e_consulta_basica(self):
        reg = self.cat.obter("abrir_menu_tarefa", contexto="mandado")
        self.assertIsNotNone(reg)
        self.assertEqual(reg.seletor_principal, "#botao-menu")
        self.assertIn('button#botao-menu', reg.fallbacks)

    def test_fallback_para_contexto_geral(self):
        reg = self.cat.obter("confirmar_dialogo_sim", contexto="mandado")
        self.assertIsNotNone(reg)
        self.assertIn("mat-dialog-container", reg.seletor_principal)

    def test_acao_nao_cadastrada_retorna_none(self):
        mock_driver = MagicMock()
        resultado = self.cat.executar_busca(mock_driver, "acao_totalmente_inexistente")
        self.assertIsNone(resultado)

    def test_vencedor_encerra_imediatamente_ao_sucesso(self):
        reg = SeletorRegistro(
            acao="teste_acao",
            seletor_principal="#principal",
            fallbacks=["#fallback_1", "#fallback_2"],
            contexto="teste",
            seletor_vencedor="#fallback_1",
            quantidade_sucessos=5,
        )
        self.cat.registrar(reg)

        mock_driver = MagicMock()
        chamadas_espera = []

        def mock_espera_elemento(driver, sel, teto=1, visivel=False):
            chamadas_espera.append(sel)
            if sel == "#fallback_1":
                el = MagicMock()
                el.tag_name = "button"
                return el
            return None

        with patch("Fix.espera.elemento", side_effect=mock_espera_elemento):
            res = self.cat.executar_busca(mock_driver, "teste_acao", contexto="teste")
            self.assertIsNotNone(res)
            # Garante que testou SOMENTE o vencedor e encerrou
            self.assertEqual(chamadas_espera, ["#fallback_1"])
            self.assertEqual(reg.quantidade_sucessos, 6)
            self.assertEqual(reg.seletor_vencedor, "#fallback_1")

    def test_vencedor_falha_invalida_e_acha_novo_vencedor(self):
        reg = SeletorRegistro(
            acao="teste_mutacao",
            seletor_principal="#principal",
            fallbacks=["#fallback_1", "#fallback_2"],
            contexto="teste",
            seletor_vencedor="#principal",
        )
        self.cat.registrar(reg)

        mock_driver = MagicMock()
        chamadas_espera = []

        def mock_espera_elemento(driver, sel, teto=1, visivel=False):
            chamadas_espera.append(sel)
            if sel == "#principal":
                return None  # Vencedor falhou (DOM mudou)
            if sel == "#fallback_1":
                el = MagicMock()
                el.tag_name = "div"
                return el  # Fallback 1 tem sucesso!
            return None

        with patch("Fix.espera.elemento", side_effect=mock_espera_elemento):
            res = self.cat.executar_busca(mock_driver, "teste_mutacao", contexto="teste")
            self.assertIsNotNone(res)
            # Testou o vencedor (#principal), falhou, tentou a cadeia e parou no primeiro sucesso (#fallback_1)
            # NÃO deve ter tentado #fallback_2
            self.assertEqual(chamadas_espera, ["#principal", "#fallback_1"])
            # Novo vencedor registrado
            self.assertEqual(reg.seletor_vencedor, "#fallback_1")
            self.assertEqual(reg.quantidade_falhas, 1)

    def test_todos_falham_retorna_none(self):
        reg = SeletorRegistro(
            acao="teste_tudo_falha",
            seletor_principal="#principal",
            fallbacks=["#fallback_1"],
            contexto="teste",
        )
        self.cat.registrar(reg)

        mock_driver = MagicMock()
        with patch("Fix.espera.elemento", return_value=None):
            res = self.cat.executar_busca(mock_driver, "teste_tudo_falha", contexto="teste")
            self.assertIsNone(res)


if __name__ == '__main__':
    unittest.main()
