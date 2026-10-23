"""Regressões da rodada real de mandado (23/10/2026).

1. intimação de 30 dias não era fechada: a tabela de Expedientes mudou de
   layout e o índice fixo cells[8]/cells[10] deixava de casar. A coluna agora
   é descoberta pelo cabeçalho.
2. veredito SISBAJUD invertido: a seção 'Bloqueio de valores' vazava para o
   bloco ARISP seguinte ('arisp consulta positivo') e o 'positivo' vencia.
   O veredito declarado pelo SISBAJUD passou a ter precedência, e a seção é
   cortada em 'pesquisa patrimonial'.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Fix.espera as espera
import Mandado.entrada_api as api
from Mandado.anexos_argos import processar_sisbajud


class TestColunasExpedientes(unittest.TestCase):
    class Th:
        def __init__(self, t):
            self.text = t

    def _driver(self, cabecalhos):
        class D:
            pass
        d = D()
        d.cabecalhos = cabecalhos
        return d

    def setUp(self):
        self._orig = espera.elementos

    def tearDown(self):
        espera.elementos = self._orig

    def _patch(self, cabecalhos):
        def fake(driver, seletor, teto=10):
            if "thead" in seletor:
                return [self.Th(c) for c in driver.cabecalhos]
            return []
        espera.elementos = fake

    def test_layout_11_colunas(self):
        cab = ["0", "1", "2", "3", "4", "5", "6", "7", "Prazo", "9", "Fechado"]
        self._patch(cab)
        self.assertEqual(api._colunas_expedientes(self._driver(cab)), (8, 10))

    def test_layout_9_colunas_movido(self):
        """Caso que o índice fixo 8/10 NÃO encontrava."""
        cab = ["Tipo", "Descrição", "Órgão", "Data", "Prazo", "Hora", "X", "Situação", "Y"]
        self._patch(cab)
        self.assertEqual(api._colunas_expedientes(self._driver(cab)), (4, 7))

    def test_sem_cabecalho_devolve_none(self):
        self._patch([])
        self.assertEqual(api._colunas_expedientes(self._driver([])), (None, None))


class TestSelecaoPrazo30(unittest.TestCase):
    """Replica a escolha da linha conforme fechar_intimacao."""

    @staticmethod
    def escolher(textos, idx_p, idx_f):
        if idx_p is not None and idx_p < len(textos):
            prazo = textos[idx_p]
            fechado = textos[idx_f].lower() if (idx_f is not None and idx_f < len(textos)) else ""
        else:
            prazo = next((t for t in textos if t == "30"), "")
            fechado = "sim" if any(t.lower() == "sim" for t in textos) else ""
        return prazo == "30" and fechado != "sim"

    def test_prazo_30_aberto_seleciona(self):
        textos = ["Intimação", "Art. 84", "TRT", "01/10", "30", "10:00", "x", "Não", "y"]
        self.assertTrue(self.escolher(textos, 4, 7))

    def test_prazo_30_fechado_nao_seleciona(self):
        textos = ["Intimação", "Art. 84", "TRT", "01/10", "30", "10:00", "x", "Sim", "y"]
        self.assertFalse(self.escolher(textos, 4, 7))

    def test_outro_prazo_nao_seleciona(self):
        textos = ["Intimação", "Art. 84", "TRT", "01/10", "5", "10:00", "x", "Não", "y"]
        self.assertFalse(self.escolher(textos, 4, 7))

    def test_fallback_sem_cabecalho(self):
        textos = ["Intimação", "Art. 84", "TRT", "01/10", "30", "10:00", "x", "Não", "y"]
        self.assertTrue(self.escolher(textos, None, None))


class TestSisbajudVeredito(unittest.TestCase):
    def _certidao(self, secao_bloqueio, secao_seguinte="pesquisa patrimonial\narisp consulta negativo"):
        return (
            "PROCESSO\n"
            "determinacoes normativas e legais\n"
            "determinacao 1\n"
            "determinacao 2\n"
            "Bloqueio de valores\n"
            f"{secao_bloqueio}\n"
            f"{secao_seguinte}\n"
            "certifico finalmente\n"
        )

    def test_negativo_com_arisp_positivo_nao_vira_positivo(self):
        """Regressão exata: 'sisbajud negativo' + 'arisp consulta positivo'."""
        texto = self._certidao(
            "sisbajud negativo\nvalor total bloqueado: r$ 0,00",
            "pesquisa patrimonial\narisp consulta positivo",
        )
        veredito, motivo, _ = processar_sisbajud(texto, log=False)
        self.assertEqual(veredito, "negativo", motivo)

    def test_positivo_declarado(self):
        texto = self._certidao("sisbajud positivo\nvalor total bloqueado: r$ 1.500,00")
        veredito, motivo, _ = processar_sisbajud(texto, log=False)
        self.assertEqual(veredito, "positivo", motivo)

    def test_valor_maior_que_zero_e_positivo(self):
        texto = self._certidao("sisbajud negativo\nvalor total bloqueado: r$ 250,00")
        veredito, _, _ = processar_sisbajud(texto, log=False)
        self.assertEqual(veredito, "positivo")

    def test_sem_bloqueio_de_valores_e_negativo(self):
        texto = (
            "determinacoes normativas e legais\n"
            "determinacao 1\n"
            "certifico finalmente\n"
        )
        veredito, motivo, _ = processar_sisbajud(texto, log=False)
        self.assertEqual(veredito, "negativo")
        self.assertIn("não encontrado", motivo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
