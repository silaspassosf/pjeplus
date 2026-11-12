"""Invariantes do clique na aba "Intimações" (pós-Salvar da minuta).

Histórico (11/11): os 5 seletores localizavam a aba, mas só
`pje-editor-lateral div[role="tab"][aria-posinset="1"]` foi provado para o
clique; o que matava o fluxo era a CONFIRMAÇÃO mentirosa e o atalho de
"já estava ativa", que pulava o clique. Regra fixada em 13:05: o clique é
SEMPRE feito; a confirmação usa label ativo + painel no mesmo mat-tab-group.

Depois veio o problema da ATRIBUIÇÃO: se alguém clica manualmente durante a
execução, o painel aparece e a confirmação passa mesmo com o clique da
automação tendo falhado — o log mentia. Por isso o estado é lido ANTES do
clique e o sucesso só é chamado de "transição observada pelo clique" quando o
estado realmente mudou.

Roda com:  python -m unittest tests.test_ato_aba_intimacoes
"""
import unittest
from unittest.mock import ANY, MagicMock, patch

from atos import judicial_fluxo as jf

S1, S2 = jf.SELETORES_ABA_INTIMACOES[0], jf.SELETORES_ABA_INTIMACOES[1]

INATIVA = {'existe': True, 'ativa': False, 'painel': False, 'ativa_texto': 'modelos'}
ATIVA = {'existe': True, 'ativa': True, 'painel': True, 'ativa_texto': 'intimações'}


def _buscar(mapa):
    def _fn(_driver, seletor, timeout=0):
        return mapa.get(seletor)
    return _fn


def _labels(mapa):
    def _fn(_driver, seletor, elemento=None):
        return mapa.get(seletor, '')
    return _fn


def _ate_uma_vez(_driver, condicao, teto=0):
    return bool(condicao(_driver))


def _patches(**extra):
    base = dict(
        esperar_elemento=patch.object(jf, 'esperar_elemento', side_effect=_buscar({S1: MagicMock()})),
        texto=patch.object(jf, '_texto_aba', side_effect=_labels({S1: 'intimações'})),
        clique=patch.object(jf, 'safe_click_no_scroll'),
        confirmacao=patch.object(jf, '_aba_intimacoes_ativa', return_value=True),
        assentar=patch.object(jf.espera, 'assentar'),
        armar=patch.object(jf, '_armar_clique_aba', return_value=False),
    )
    base.update(extra)
    return base


class TestProvaDoClique(unittest.TestCase):
    """Painel montado prova UM clique — não que foi o deste código.

    O contador de eventos no label existe para atribuir: 0 eventos = o clique
    da automação não alcançou a aba e o painel (se aparecer) é alheio.
    """

    def test_clique_que_chega_ao_label_segue_para_confirmacao(self):
        p = _patches(
            estado=patch.object(jf, '_estado_aba', return_value=INATIVA),
            armar=patch.object(jf, '_armar_clique_aba', return_value=True),
            ler=patch.object(jf, '_ler_clique_aba', return_value=1),
        )
        with p['esperar_elemento'], p['texto'], p['clique'], p['confirmacao'] as conf, \
             p['assentar'], p['estado'], p['armar'], p['ler']:
            ok = jf._ativar_aba_intimacoes(MagicMock())

        self.assertTrue(ok)
        conf.assert_called_once()

    def test_zero_eventos_retenta_em_vez_de_aceitar_painel_alheio(self):
        p = _patches(
            estado=patch.object(jf, '_estado_aba', return_value=INATIVA),
            armar=patch.object(jf, '_armar_clique_aba', return_value=True),
            ler=patch.object(jf, '_ler_clique_aba', side_effect=[0, 1]),
        )
        with p['esperar_elemento'], p['texto'], p['clique'] as clicar, \
             p['confirmacao'] as conf, p['assentar'], p['estado'], p['armar'], p['ler']:
            ok = jf._ativar_aba_intimacoes(MagicMock())

        self.assertTrue(ok)
        self.assertEqual(clicar.call_count, 2)
        # Na 1ª (0 eventos) não chegou a confirmar; confirmou só na 2ª.
        conf.assert_called_once()

    def test_ultima_tentativa_com_zero_eventos_ainda_aceita(self):
        p = _patches(
            estado=patch.object(jf, '_estado_aba', return_value=INATIVA),
            armar=patch.object(jf, '_armar_clique_aba', return_value=True),
            ler=patch.object(jf, '_ler_clique_aba', return_value=0),
        )
        with p['esperar_elemento'], p['texto'], p['clique'] as clicar, \
             p['confirmacao'], p['assentar'], p['estado'], p['armar'], p['ler']:
            ok = jf._ativar_aba_intimacoes(MagicMock())

        self.assertTrue(ok)
        self.assertEqual(clicar.call_count, jf.TENTATIVAS_ABA_INTIMACOES)

    def test_armamento_acontece_antes_do_clique(self):
        ordem = []
        p = _patches(
            estado=patch.object(jf, '_estado_aba', return_value=INATIVA),
            armar=patch.object(
                jf, '_armar_clique_aba',
                side_effect=lambda *a: ordem.append('armar') or True),
            ler=patch.object(jf, '_ler_clique_aba', return_value=1),
            clique=patch.object(
                jf, 'safe_click_no_scroll',
                side_effect=lambda *a: ordem.append('clique')),
        )
        with p['esperar_elemento'], p['texto'], p['clique'], p['confirmacao'], \
             p['assentar'], p['estado'], p['armar'], p['ler']:
            jf._ativar_aba_intimacoes(MagicMock())

        self.assertEqual(ordem, ['armar', 'clique'])



class TestCliqueAbaIntimacoes(unittest.TestCase):

    def test_clique_sempre_mesmo_com_aba_ja_confirmada(self):
        """Não pode existir atalho: clica mesmo que a confirmação passe."""
        p = _patches(estado=patch.object(jf, '_estado_aba', return_value=ATIVA))
        with p['esperar_elemento'], p['texto'], p['clique'] as clicar, \
             p['confirmacao'], p['assentar'], p['estado']:
            ok = jf._ativar_aba_intimacoes(MagicMock())

        self.assertTrue(ok)
        clicar.assert_called_once()

    def test_pula_candidato_cujo_label_nao_e_intimacoes(self):
        """Drift de posinset: candidato 1 aponta p/ outra aba, usa o 2."""
        errado, certo = MagicMock(), MagicMock()
        p = _patches(
            esperar_elemento=patch.object(
                jf, 'esperar_elemento', side_effect=_buscar({S1: errado, S2: certo})),
            texto=patch.object(
                jf, '_texto_aba', side_effect=_labels({S1: 'modelos', S2: 'intimações'})),
            estado=patch.object(jf, '_estado_aba', return_value=INATIVA),
        )
        with p['esperar_elemento'], p['texto'], p['clique'] as clicar, \
             p['confirmacao'], p['assentar'], p['estado']:
            ok = jf._ativar_aba_intimacoes(MagicMock())

        self.assertTrue(ok)
        clicar.assert_called_once_with(ANY, certo)

    def test_estado_e_lido_antes_do_clique_no_seletor_resolvido(self):
        """Atribuição: o estado pré-clique tem de ser capturado no alvo certo."""
        ordem = []
        el = MagicMock()
        p = _patches(
            esperar_elemento=patch.object(jf, 'esperar_elemento', side_effect=_buscar({S1: el})),
            estado=patch.object(
                jf, '_estado_aba',
                side_effect=lambda *a, **k: ordem.append('estado') or INATIVA),
            clique=patch.object(
                jf, 'safe_click_no_scroll',
                side_effect=lambda *a, **k: ordem.append('clique')),
        )
        with p['esperar_elemento'], p['texto'], p['clique'], \
             p['confirmacao'], p['assentar'], p['estado'] as estado:
            jf._ativar_aba_intimacoes(MagicMock())

        self.assertEqual(ordem[0], 'estado')
        self.assertEqual(estado.call_args_list[0][0][1], S1)
        self.assertIs(estado.call_args_list[0][0][2], el)

    def test_primeiro_candidato_e_o_provado_por_posicao(self):
        self.assertEqual(S1, 'pje-editor-lateral div[role="tab"][aria-posinset="1"]')
        self.assertEqual(len(jf.SELETORES_ABA_INTIMACOES), 5)

    def test_retry_reclica_quando_painel_nao_monta(self):
        """Painel demora a montar: o retry precisa clicar de novo, não desistir."""
        p = _patches(
            estado=patch.object(jf, '_estado_aba', return_value=INATIVA),
            confirmacao=patch.object(jf, '_aba_intimacoes_ativa', side_effect=[False, True]),
        )
        with p['esperar_elemento'], p['texto'], p['clique'] as clicar, \
             p['confirmacao'], p['assentar'], p['estado']:
            ok = jf._ativar_aba_intimacoes(MagicMock())

        self.assertTrue(ok)
        self.assertEqual(clicar.call_count, 2)

    def test_desiste_apos_o_teto_de_tentativas(self):
        p = _patches(
            estado=patch.object(jf, '_estado_aba', return_value=INATIVA),
            confirmacao=patch.object(jf, '_aba_intimacoes_ativa', return_value=False),
        )
        with p['esperar_elemento'], p['texto'], p['clique'] as clicar, \
             p['confirmacao'], p['assentar'], p['estado']:
            ok = jf._ativar_aba_intimacoes(MagicMock())

        self.assertFalse(ok)
        self.assertEqual(clicar.call_count, jf.TENTATIVAS_ABA_INTIMACOES)

    def test_nenhum_candidato_nao_clica_e_esgota(self):
        p = _patches(
            esperar_elemento=patch.object(jf, 'esperar_elemento', side_effect=_buscar({})),
            texto=patch.object(jf, '_texto_aba', side_effect=_labels({})),
        )
        with p['esperar_elemento'], p['texto'], p['clique'] as clicar, \
             p['confirmacao'] as conf, p['assentar']:
            ok = jf._ativar_aba_intimacoes(MagicMock())

        self.assertFalse(ok)
        clicar.assert_not_called()
        conf.assert_not_called()


class TestConfirmacaoAbaIntimacoes(unittest.TestCase):
    """A confirmação exige DOIS sinais: label ativo e painel no mesmo group."""

    def _confirma(self, estado):
        with patch.object(jf, '_estado_aba', return_value=estado), \
             patch.object(jf.espera, 'ate', side_effect=_ate_uma_vez):
            return jf._aba_intimacoes_ativa(MagicMock(), S1, teto=0)

    def test_ativa_com_painel_confirma(self):
        self.assertTrue(self._confirma({'ativa': True, 'painel': True}))

    def test_ativa_sem_painel_nao_confirma(self):
        self.assertFalse(self._confirma({'ativa': True, 'painel': False}))

    def test_painel_sem_ativa_nao_confirma(self):
        self.assertFalse(self._confirma({'ativa': False, 'painel': True}))

    def test_js_do_estado_exige_os_dois_sinais(self):
        js = jf._JS_ESTADO_ABA
        self.assertIn('mat-tab-label-active', js)
        self.assertIn("aria-selected') === 'true'", js)
        self.assertIn("closest('mat-tab-group')", js)
        self.assertIn('pje-intimacao-automatica .controle-intimacao-pai', js)

    def test_avalia_o_seletor_recebido(self):
        with patch.object(jf, '_estado_aba', return_value={'ativa': False}) as estado, \
             patch.object(jf.espera, 'ate', side_effect=_ate_uma_vez):
            jf._aba_intimacoes_ativa(MagicMock(), S2, teto=0)

        self.assertEqual(estado.call_args[0][1], S2)

    def test_nao_usa_sinais_que_mentem(self):
        self.assertNotIn('mat-tab-body-active', jf._JS_ESTADO_ABA)


if __name__ == '__main__':
    unittest.main()
