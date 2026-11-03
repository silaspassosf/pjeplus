"""Testes das correções de tempo/refresh no fluxo CLS.

Cobre dois problemas observados no log de 01/11/2026 (fluxo D):

  1. `NAVEGAR_CONCLUSAO` levava 13.6s porque a tarefa "Triagem Inicial" caía no
     ramo `else` e passava por `navegar_para_tarefa` (movimentar_analise +
     espera de transição) antes de procurar um botão que já estava na tela.

  2. `escolher_tipo_conclusao` esperava `document.readyState === 'complete'`
     logo após o clique, prendendo o passo durante toda a navegação para
     /minutar -- era o "refresh" visto antes de escolher o tipo.

Roda com:  python -m unittest tests.test_cls_navegacao_rapida
"""
import sys
import unittest
from unittest.mock import MagicMock, patch

from atos import judicial_navegacao as nav

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def _driver():
    d = MagicMock()
    d.current_url = 'https://pje.trt2.jus.br/pjekz/tarefa/123'
    d.pje_tarefa_atual = 'Triagem Inicial'
    return d


class TestNavegarParaConclusaoDireto(unittest.TestCase):
    """Item 1: tarefa não-'aguardando prazo' tenta o botão ANTES de rotear."""

    def test_triagem_inicial_nao_roteia_por_analise(self):
        """Se o botão de conclusão já está na tela, não passa por Análise."""
        d = _driver()
        botao = MagicMock()

        with patch.object(nav, 'navegar_para_tarefa') as rotear, \
             patch.object(nav, 'aguardar_renderizacao_nativa', return_value=True), \
             patch.object(nav.espera, 'elemento', return_value=botao), \
             patch.object(nav.espera, 'elementos', return_value=[]), \
             patch.object(nav, 'limpar_overlays'), \
             patch.object(nav, 'safe_click_no_scroll', return_value=True), \
             patch.object(nav.espera, 'ate_aparecer', return_value=True):
            ok = nav.navegar_para_conclusao(d)

        self.assertTrue(ok)
        rotear.assert_not_called()

    def test_roteia_quando_botao_nao_esta_na_tela(self):
        """Sem o botão direto, o roteamento por Análise continua acontecendo."""
        d = _driver()
        d.pje_tarefa_atual = 'Cumprimento de Providencias'
        botao = MagicMock()
        chamadas = {'n': 0}

        def elemento(_driver, _sel, teto=2):
            chamadas['n'] += 1
            # 1ª busca (teto=6) devolve None; depois do roteamento acha o botão.
            return None if chamadas['n'] == 1 else botao

        with patch.object(nav, 'navegar_para_tarefa', return_value=True) as rotear, \
             patch.object(nav, 'aguardar_renderizacao_nativa', return_value=True), \
             patch.object(nav.espera, 'elemento', side_effect=elemento), \
             patch.object(nav.espera, 'elementos', return_value=[]), \
             patch.object(nav, 'limpar_overlays'), \
             patch.object(nav, 'safe_click_no_scroll', return_value=True), \
             patch.object(nav.espera, 'ate_aparecer', return_value=True):
            ok = nav.navegar_para_conclusao(d)

        self.assertTrue(ok)
        rotear.assert_called_once()

    def test_nao_limpa_overlays_depois_do_clique(self):
        """O Escape pós-clique (que causava o 'refresh') não deve mais ocorrer."""
        d = _driver()
        botao = MagicMock()
        overlays = []

        with patch.object(nav, 'navegar_para_tarefa'), \
             patch.object(nav, 'aguardar_renderizacao_nativa', return_value=True), \
             patch.object(nav.espera, 'elemento', return_value=botao), \
             patch.object(nav.espera, 'elementos', return_value=[]), \
             patch.object(nav, 'limpar_overlays', side_effect=lambda _d: overlays.append(1)), \
             patch.object(nav, 'safe_click_no_scroll', return_value=True), \
             patch.object(nav.espera, 'ate_aparecer', return_value=True):
            nav.navegar_para_conclusao(d)

        # Só a limpeza ANTES do clique (para o clique não ser engolido).
        self.assertEqual(len(overlays), 1, 'limpar_overlays só deve rodar antes do clique')


class TestEscolherTipoSemTravar(unittest.TestCase):
    """Item 2: não esperar readyState após clicar no tipo de conclusão."""

    def test_nao_espera_readyState_depois_do_clique(self):
        d = _driver()
        d.page.evaluate.return_value = True   # o JS achou e clicou no botão
        avaliado = []

        def ate_js(_driver, expressao, teto=2.0):
            avaliado.append(expressao)
            return True

        with patch.object(nav.espera, 'ate_js', side_effect=ate_js), \
             patch.object(nav.espera, 'assentar', return_value=None):
            ok = nav.escolher_tipo_conclusao(d, 'Despacho')

        self.assertTrue(ok)
        travadas = [e for e in avaliado if 'readyState' in str(e)]
        self.assertEqual(travadas, [], 'não deve esperar readyState após o clique')


if __name__ == '__main__':
    unittest.main()
