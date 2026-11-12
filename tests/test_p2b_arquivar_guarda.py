"""Guarda do arquivamento P2B (regra `_mov_arquivar_se_sem_prazo`).

Regressão do log de 12/11: a regra do art. 924 casou 13 vezes e as 13 foram
puladas com o mesmo `Prazo: xs1`. O `xs1` é a atividade-gatilho do próprio P2B
(`testar_gigs_xs1` filtra por `xs1`), logo a guarda se auto-bloqueava e
`mov_arquivar` nunca era executado.

Regra correta: arquiva SÓ quando a única atividade GIGS é `xs1`; qualquer outra
atividade ou comentário bloqueia (a guarda é de existência, não de prazo).

Roda com:  python -m unittest tests.test_p2b_arquivar_guarda
"""
import types
import unittest
from unittest.mock import MagicMock, patch

from Prazo import p2b_documentos as doc
from Prazo import p2b_gateway as gw


class Linha:
    """Linha fake do painel GIGS."""

    def __init__(self, texto, tem_prazo=False):
        self.text = texto
        self._tem = tem_prazo
        self._desc = texto


def _elemento(_alvo, seletor, teto=0):
    if 'alerta-prazo' in seletor:
        return MagicMock() if getattr(_alvo, '_tem', False) else None
    if 'descricao' in seletor:
        return types.SimpleNamespace(text=getattr(_alvo, '_desc', ''))
    return None


def _painel(linhas):
    return patch.object(doc.espera, 'elementos', return_value=linhas), \
        patch.object(doc.espera, 'elemento', side_effect=_elemento)


class TestGuardaPainel(unittest.TestCase):

    def _roda(self, linhas):
        p_linhas, p_elem = _painel(linhas)
        with p_linhas, p_elem:
            return doc._gigs_com_prazo_pendente(MagicMock())

    def test_xs1_com_prazo_nao_bloqueia(self):
        self.assertFalse(self._roda([Linha('Prazo: xs1', tem_prazo=True)]))

    def test_duas_xs1_liberam(self):
        self.assertFalse(self._roda([
            Linha('Prazo: xs1', tem_prazo=True),
            Linha('xs1', tem_prazo=True),
        ]))

    def test_xs1_junto_de_prazo_real_bloqueia(self):
        self.assertTrue(self._roda([
            Linha('Prazo: xs1', tem_prazo=True),
            Linha('Prazo: 15 dias - parte', tem_prazo=True),
        ]))

    def test_outra_atividade_sem_prazo_bloqueia(self):
        """Regra é de existência: qualquer outra atividade bloqueia."""
        self.assertTrue(self._roda([Linha('xs carta', tem_prazo=False)]))

    def test_comentario_bloqueia(self):
        self.assertTrue(self._roda([
            Linha('Prazo: xs1', tem_prazo=True),
            Linha('Comentário: aguardando comprovante', tem_prazo=False),
        ]))

    def test_painel_vazio_cai_na_api(self):
        p_linhas, p_elem = _painel([])
        with p_linhas, p_elem, \
             patch.object(doc, '_gigs_com_prazo_pendente_api', return_value=True) as api:
            self.assertTrue(doc._gigs_com_prazo_pendente(MagicMock()))
        api.assert_called_once()


class TestGuardaApi(unittest.TestCase):

    def _roda(self, atividades):
        client = MagicMock()
        client.atividades_gigs.return_value = atividades
        with patch('Fix.navegacao_espera.extrair_id_processo', return_value='123'), \
             patch.object(gw, '_criar_api_client', return_value=client):
            return doc._gigs_com_prazo_pendente_api(MagicMock())

    def test_xs1_com_data_prazo_nao_bloqueia(self):
        self.assertFalse(self._roda([
            {'tipoAtividade': {'descricao': 'xs1'}, 'dataPrazo': '2026-12-01',
             'statusAtividade': 'PENDENTE'},
        ]))

    def test_prazo_real_pendente_bloqueia(self):
        self.assertTrue(self._roda([
            {'tipoAtividade': {'descricao': 'xs1'}, 'dataPrazo': '2026-12-01',
             'statusAtividade': 'PENDENTE'},
            {'tipoAtividade': {'descricao': 'Prazo parte'}, 'dataPrazo': '2026-12-05',
             'statusAtividade': 'PENDENTE'},
        ]))

    def test_prazo_concluido_tambem_bloqueia(self):
        """Existência basta: atividade concluída diferente de xs1 ainda bloqueia."""
        self.assertTrue(self._roda([
            {'tipoAtividade': {'descricao': 'Prazo parte'}, 'dataPrazo': '2026-12-05',
             'statusAtividade': 'CONCLUIDA'},
        ]))

    def test_comentario_bloqueia(self):
        self.assertTrue(self._roda([
            {'tipoAtividade': {'descricao': 'Comentário'}, 'dataPrazo': None,
             'statusAtividade': 'PENDENTE'},
        ]))

    def test_xs1_por_observacao_tambem_e_ignorado(self):
        self.assertFalse(self._roda([
            {'tipoAtividade': {'descricao': 'Atividade'}, 'observacao': 'xs1',
             'dataPrazo': '2026-12-01', 'statusAtividade': 'PENDENTE'},
        ]))


class TestRegraArquivar(unittest.TestCase):
    """Com a guarda liberada, mov_arquivar TEM de ser chamado."""

    def test_arquiva_quando_so_xs1(self):
        p_linhas, p_elem = _painel([Linha('Prazo: xs1', tem_prazo=True)])
        mov = MagicMock(return_value=True)
        with p_linhas, p_elem, \
             patch.object(doc, '_lazy_import', return_value={'mov_arquivar': mov}):
            ok = doc._mov_arquivar_se_sem_prazo(MagicMock())

        self.assertTrue(ok)
        mov.assert_called_once()

    def test_pula_sem_chamar_mov_arquivar_com_outra_atividade(self):
        p_linhas, p_elem = _painel([Linha('Comentário: aguardando', tem_prazo=False)])
        mov = MagicMock(return_value=True)
        with p_linhas, p_elem, \
             patch.object(doc, '_lazy_import', return_value={'mov_arquivar': mov}):
            ok = doc._mov_arquivar_se_sem_prazo(MagicMock())

        self.assertTrue(ok)
        mov.assert_not_called()


if __name__ == '__main__':
    unittest.main()
