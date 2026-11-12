"""Clique em "Selecionar polo ativo" (apenas_primeiro=True).

Regressão: a função trocou o clique nativo por ID (JS) por uma busca com gate de
visibilidade + `safe_click` silencioso, e ainda logava "clique realizado" mesmo
sem elemento. No processo 1001901 (P2B, 12/11) o ato foi até o fim com os
destinatários não selecionados e o log dizendo sucesso.

A confirmação aqui é o EFEITO (alguma linha marcada), não o disparo do clique.

Roda com:  python -m unittest tests.test_prazos_polo_ativo
"""
import unittest
from unittest.mock import ANY, MagicMock, patch

from atos import judicial_utils as ju


class TestClicarPoloAtivo(unittest.TestCase):

    def test_clique_por_js_marca_linha(self):
        with patch.object(ju, '_executar_js', return_value=True) as js, \
             patch.object(ju, 'safe_click_no_scroll') as safe, \
             patch.object(ju.espera, 'ate_aparecer'), \
             patch.object(ju.espera, 'ate_js', return_value=True), \
             patch.object(ju.espera, 'assentar'):
            ok = ju._clicar_polo_ativo(MagicMock())

        self.assertTrue(ok)
        js.assert_called_once()
        safe.assert_not_called()

    def test_js_sem_botao_cai_no_elemento_sem_gate_de_visibilidade(self):
        btn = MagicMock()
        with patch.object(ju, '_executar_js', return_value=False), \
             patch.object(ju, 'safe_click_no_scroll', return_value=True) as safe, \
             patch.object(ju.espera, 'ate_aparecer'), \
             patch.object(ju.espera, 'elemento', return_value=btn) as elem, \
             patch.object(ju.espera, 'ate_js', return_value=True), \
             patch.object(ju.espera, 'assentar'):
            ok = ju._clicar_polo_ativo(MagicMock())

        self.assertTrue(ok)
        self.assertFalse(elem.call_args.kwargs.get('visivel', True))
        safe.assert_called_once()

    def test_retenta_quando_nada_e_marcado(self):
        """Clique disparado sem marcar linha não é sucesso."""
        with patch.object(ju, '_executar_js', return_value=True), \
             patch.object(ju, 'safe_click_no_scroll'), \
             patch.object(ju.espera, 'ate_aparecer'), \
             patch.object(ju.espera, 'ate_js', side_effect=[False, True]), \
             patch.object(ju.espera, 'assentar'):
            ok = ju._clicar_polo_ativo(MagicMock())

        self.assertTrue(ok)

    def test_desiste_apos_as_tentativas(self):
        with patch.object(ju, '_executar_js', return_value=True) as js, \
             patch.object(ju, 'safe_click_no_scroll'), \
             patch.object(ju.espera, 'ate_aparecer'), \
             patch.object(ju.espera, 'ate_js', return_value=False), \
             patch.object(ju.espera, 'assentar'):
            ok = ju._clicar_polo_ativo(MagicMock(), tentativas=2)

        self.assertFalse(ok)
        self.assertEqual(js.call_count, 2)

    def test_botao_inexistente_devolve_false(self):
        with patch.object(ju, '_executar_js', return_value=False), \
             patch.object(ju, 'safe_click_no_scroll') as safe, \
             patch.object(ju.espera, 'ate_aparecer'), \
             patch.object(ju.espera, 'elemento', return_value=None), \
             patch.object(ju.espera, 'ate_js', return_value=True), \
             patch.object(ju.espera, 'assentar'):
            ok = ju._clicar_polo_ativo(MagicMock(), tentativas=1)

        self.assertFalse(ok)
        safe.assert_not_called()

    def test_js_usa_o_id_do_botao(self):
        with patch.object(ju, '_executar_js', return_value=True) as js, \
             patch.object(ju.espera, 'ate_aparecer'), \
             patch.object(ju.espera, 'ate_js', return_value=True), \
             patch.object(ju.espera, 'assentar'):
            ju._clicar_polo_ativo(MagicMock(), tentativas=1)

        self.assertIn('getElementById(\'selecionar-polo-ativo\')', js.call_args[0][1])


class TestIntegracaoApenasPrimeiro(unittest.TestCase):

    def test_apenas_primeiro_delega_para_o_clique_do_polo(self):
        with patch.object(ju.espera, 'ate_js', return_value=True), \
             patch.object(ju, '_aguardar_painel_destinatarios_assentar'), \
             patch.object(ju, '_clicar_polo_ativo', return_value=False) as polo, \
             patch.object(ju, '_executar_js',
                          return_value={'marcadas': 1, 'preenchidos': 1}), \
             patch.object(ju.espera, 'assentar'):
            ok = ju.preencher_prazos_destinatarios(MagicMock(), 5, apenas_primeiro=True)

        self.assertTrue(ok)
        polo.assert_called_once_with(ANY)

    def test_sem_apenas_primeiro_nao_clica_no_polo(self):
        with patch.object(ju.espera, 'ate_js', return_value=True), \
             patch.object(ju, '_aguardar_painel_destinatarios_assentar'), \
             patch.object(ju, '_clicar_polo_ativo') as polo, \
             patch.object(ju.espera, 'ate_habilitar', return_value=False), \
             patch.object(ju, '_executar_js',
                          return_value={'marcadas': 0, 'preenchidos': 0}), \
             patch.object(ju.espera, 'assentar'):
            ju.preencher_prazos_destinatarios(MagicMock(), 5, apenas_primeiro=False)

        polo.assert_not_called()


if __name__ == '__main__':
    unittest.main()
