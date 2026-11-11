"""`Fix.utils.padrao_texto` — normalização canônica aplicada ao matching.

O texto que vem do DOM está como o PJe renderizou (acentuado, com quebras de
linha). `normalizar_texto` só normaliza o lado Python, então o casamento por
texto precisa de um padrão que cubra os dois lados.
"""
import unittest

from Fix.utils import normalizar_texto, padrao_texto


class TestPadraoTexto(unittest.TestCase):

    def test_ignora_acento_nos_dois_sentidos(self):
        self.assertTrue(padrao_texto('Suspensao').search('Suspensão'))
        self.assertTrue(padrao_texto('Suspensão').search('Suspensao'))
        self.assertTrue(padrao_texto('decisao').search('Decisão'))
        self.assertTrue(padrao_texto('intimacoes').search('Intimações'))
        self.assertTrue(padrao_texto('acao').search('Ação'))

    def test_ignora_caixa(self):
        self.assertTrue(padrao_texto('DESPACHO').search('Despacho'))
        self.assertTrue(padrao_texto('despacho').search('DESPACHO'))

    def test_ignora_quebra_de_linha_e_espaco_extra(self):
        self.assertTrue(
            padrao_texto('Conclusão ao magistrado').search('Conclusão ao\n   Magistrado'))

    def test_continua_sendo_substring(self):
        # Mesmo contrato do `has_text` antigo: casa em qualquer posição.
        self.assertTrue(
            padrao_texto('Despacho').search('Despacho de mero expediente'))
        self.assertFalse(padrao_texto('Despacho').search('Despachante'))

    def test_escapa_metacaracteres_de_regex(self):
        padrao = padrao_texto('a.b (c)')
        self.assertTrue(padrao.search('a.b (c)'))
        self.assertFalse(padrao.search('axb (c)'))

    def test_texto_vazio_devolve_none(self):
        # None = "não há o que casar", o chamador cai na comparação literal.
        self.assertIsNone(padrao_texto(''))
        self.assertIsNone(padrao_texto('   '))
        self.assertIsNone(padrao_texto(None))

    def test_consistente_com_normalizar_texto(self):
        # O padrão é derivado da fonte canônica: o que ela normaliza, ele casa.
        for bruto in ('Suspensão', 'Intimações', 'Ação', 'Decisão'):
            self.assertTrue(
                padrao_texto(normalizar_texto(bruto)).search(bruto), bruto)


if __name__ == '__main__':
    unittest.main()
