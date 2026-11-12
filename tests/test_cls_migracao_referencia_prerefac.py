"""Testes da migração de tela no CLS, alinhados ao pre-refac / gigs-plugin.

Cobre as duas correções do item 1 do log de 12/11 (fluxos P2B e Mandado),
que falhavam por não esperar a tela migrar:

  1. `escolher_tipo_conclusao`: quando o botão do tipo ainda não renderizou
     (tela migrando), o fallback de polling JS (mesma função do pre-refac /
     despacho_engine) precisa achar e clicar o botão em vez de estourar.

  2. `aguardar_transicao_minutar`: o DOM de minutar é o sinal PRIMÁRIO
     (pje-arvore-modelo-documento), a URL é só fallback — o inverso (URL
     primeiro) estourava o teto quando o Angular demorava a montar a tela.

Roda com:  python -m unittest tests.test_cls_migracao_referencia_prerefac
"""
import unittest
from unittest.mock import ANY, MagicMock, patch

from atos import judicial_navegacao as nav


def _driver(url='https://pje.trt2.jus.br/pjekz/tarefa/123'):
    d = MagicMock()
    d.current_url = url
    return d


class TestEscolherTipoFallback(unittest.TestCase):
    """Item 1a: o fallback de polling JS substitui o teto estourado."""

    def test_fallback_clica_quando_esperar_elemento_nao_acha(self):
        d = _driver()

        def ate(_driver, condicao, teto=10):
            # Avalia o predicado uma vez, como o polling faria.
            return bool(condicao(_driver))

        with patch.object(nav, 'esperar_elemento', side_effect=[None, None]), \
             patch.object(nav, 'safe_click_no_scroll') as clicar, \
             patch.object(nav.espera, 'ate', side_effect=ate):
            d.page.evaluate.return_value = True
            ok = nav.escolher_tipo_conclusao(d, 'Despacho')

        self.assertTrue(ok)
        # O clique sai do JS do fallback, não do safe_click_no_scroll.
        clicar.assert_not_called()
        self.assertTrue(d.page.evaluate.called)
        # O script do fallback precisa usar o conjunto canônico do
        # despacho_engine/pre-refac (container de tipo + dependência + amplo).
        script = d.page.evaluate.call_args[0][0]
        self.assertIn('pje-concluso-tarefa-botao', script)
        self.assertIn('pje-conclusao-dependencia', script)
        self.assertEqual(d.page.evaluate.call_args[0][1], 'Despacho')

    def test_sem_botao_nem_fallback_retorna_false(self):
        d = _driver()

        with patch.object(nav, 'esperar_elemento', side_effect=[None, None]), \
             patch.object(nav, 'safe_click_no_scroll'), \
             patch.object(nav.espera, 'ate', return_value=False), \
             patch.object(nav, '_dump_botoes_conclusao'):
            d.page.evaluate.return_value = False
            ok = nav.escolher_tipo_conclusao(d, 'Despacho')

        self.assertFalse(ok)

    def test_happy_path_nao_entra_no_fallback(self):
        d = _driver()

        with patch.object(nav, 'esperar_elemento', return_value=MagicMock()), \
             patch.object(nav, 'safe_click_no_scroll') as clicar, \
             patch.object(nav.espera, 'ate') as ate:
            ok = nav.escolher_tipo_conclusao(d, 'Despacho')

        self.assertTrue(ok)
        clicar.assert_called_once()
        ate.assert_not_called()


class TestTransicaoMinutarOrdemSinais(unittest.TestCase):
    """Item 1b: DOM primário, URL só como fallback."""

    def test_dom_renderizado_nao_consulta_url(self):
        d = _driver()

        with patch.object(nav, 'aguardar_renderizacao_nativa', return_value=True) as dom, \
             patch.object(nav, 'esperar_url_conter') as url, \
             patch.object(nav.espera, 'ate_sumir', return_value=True), \
             patch.object(nav.espera, 'assentar'):
            ok = nav.aguardar_transicao_minutar(d)

        self.assertTrue(ok)
        dom.assert_called_once()
        url.assert_not_called()
        # O sinal primário tem de ser o DOM exclusivo de minutar.
        self.assertIn('pje-arvore-modelo-documento', dom.call_args[0][1])

    def test_url_e_fallback_quando_dom_falha(self):
        d = _driver()

        with patch.object(nav, 'aguardar_renderizacao_nativa', return_value=False), \
             patch.object(nav, 'esperar_url_conter', return_value=True) as url, \
             patch.object(nav.espera, 'ate_sumir', return_value=True), \
             patch.object(nav.espera, 'assentar'):
            ok = nav.aguardar_transicao_minutar(d)

        self.assertTrue(ok)
        url.assert_called_once_with(d, '/minutar', timeout=ANY)

    def test_falha_quando_dom_e_url_nao_vem(self):
        d = _driver()

        with patch.object(nav, 'aguardar_renderizacao_nativa', return_value=False), \
             patch.object(nav, 'esperar_url_conter', return_value=False), \
             patch.object(nav, '_dump_botoes_conclusao'):
            ok = nav.aguardar_transicao_minutar(d)

        self.assertFalse(ok)

    def test_atalho_quando_url_ja_e_minutar(self):
        d = _driver('https://pje.trt2.jus.br/pjekz/tarefa/1/minutar')

        with patch.object(nav, 'aguardar_renderizacao_nativa') as dom:
            ok = nav.aguardar_transicao_minutar(d)

        self.assertTrue(ok)
        dom.assert_not_called()


if __name__ == '__main__':
    unittest.main()
