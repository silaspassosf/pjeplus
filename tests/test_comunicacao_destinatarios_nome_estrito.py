import unittest
from unittest.mock import MagicMock
from atos.comunicacao_destinatarios import (
    casar_nome_destinatario,
    extrair_primeiro_nome_e_sobrenome,
    selecionar_destinatario_por_documento,
    _extrair_reus_mencionados_no_texto,
)


class TestComunicacaoDestinatariosNomeEstrito(unittest.TestCase):

    def test_extrair_primeiro_nome_e_sobrenome(self):
        p, s = extrair_primeiro_nome_e_sobrenome('BRUNO DOS SANTOS GOMES MIRANDA')
        self.assertEqual(p, 'bruno')
        self.assertEqual(s, 'santos')

        p2, s2 = extrair_primeiro_nome_e_sobrenome('NARLISON ROGERIO MAGALHAES GOMES')
        self.assertEqual(p2, 'narlison')
        self.assertEqual(s2, 'rogerio')

        p3, s3 = extrair_primeiro_nome_e_sobrenome('CJS ALIMENTOS EIRELI')
        self.assertEqual(p3, 'cjs')
        self.assertEqual(s3, 'alimentos')

        p4, s4 = extrair_primeiro_nome_e_sobrenome('BRUNO')
        self.assertEqual(p4, 'bruno')
        self.assertIsNone(s4)

    def test_casar_nome_destinatario_bruno_vs_narlison(self):
        """Valida que alvo Bruno NUNCA casa com Narlison, mesmo com sobrenomes/advogados coincidentes."""
        alvo = 'BRUNO DOS SANTOS GOMES MIRANDA'

        # Linha do Narlison pura
        self.assertFalse(casar_nome_destinatario(alvo, 'NARLISON ROGERIO MAGALHAES GOMES'))

        # Linha do Narlison com advogado Joel Miranda de Freitas (colisão de Gomes + Miranda)
        linha_narlison_com_adv = 'NARLISON ROGERIO MAGALHAES GOMES Advogado: JOEL MIRANDA DE FREITAS OAB SP'
        self.assertFalse(casar_nome_destinatario(alvo, linha_narlison_com_adv))

        # Reclamado prefixo Narlison
        self.assertFalse(casar_nome_destinatario(alvo, 'RECLAMADO: NARLISON ROGERIO MAGALHAES GOMES'))

    def test_casar_nome_destinatario_bruno_casamentos_validos(self):
        """Valida que o alvo Bruno casa com variações legítimas de primeiro nome + sobrenome."""
        alvo = 'BRUNO DOS SANTOS GOMES MIRANDA'

        # Match exato completo
        self.assertTrue(casar_nome_destinatario(alvo, 'BRUNO DOS SANTOS GOMES MIRANDA'))

        # Bruno com primeiro sobrenome com preposição
        self.assertTrue(casar_nome_destinatario(alvo, 'BRUNO DOS SANTOS'))

        # Bruno com primeiro sobrenome sem preposição
        self.assertTrue(casar_nome_destinatario(alvo, 'BRUNO SANTOS'))

        # Prefixo PJe Reclamado
        self.assertTrue(casar_nome_destinatario(alvo, 'RECLAMADO: BRUNO DOS SANTOS GOMES MIRANDA'))

    def test_casar_nome_destinatario_rejeita_outro_sobrenome(self):
        """Valida que mesmo primeiro nome mas sobrenome diferente é rejeitado."""
        alvo = 'BRUNO DOS SANTOS GOMES MIRANDA'

        # Bruno Oliveira (outro sobrenome)
        self.assertFalse(casar_nome_destinatario(alvo, 'BRUNO OLIVEIRA'))

        # Bruno Gomes (pulou o Santos)
        self.assertFalse(casar_nome_destinatario(alvo, 'BRUNO GOMES'))

    def test_casar_nome_destinatario_pessoa_juridica(self):
        empresa = 'CJS ALIMENTOS EIRELI'
        self.assertTrue(casar_nome_destinatario(empresa, 'CJS ALIMENTOS EIRELI'))
        self.assertTrue(casar_nome_destinatario(empresa, 'CJS ALIMENTOS'))
        self.assertFalse(casar_nome_destinatario(empresa, 'CJS TRANSPORTES'))

    def test_selecionar_destinatario_cenario_processo_real(self):
        """Simula o cenário do processo 1001130-46 onde Narlison vem antes de Bruno na lista.
        
        Garante que ao buscar Bruno, a linha do Bruno é clicada e a linha do Narlison é ignorada.
        """
        driver = MagicMock()

        # Mock das linhas simulando elementos do PJe
        linha_cjs = MagicMock()
        linha_cjs.text = 'CJS ALIMENTOS EIRELI'
        linha_cjs._js.return_value = 'CJS ALIMENTOS EIRELI'

        linha_rr = MagicMock()
        linha_rr.text = 'RR PADARIA LTDA'
        linha_rr._js.return_value = 'RR PADARIA LTDA'

        linha_victor = MagicMock()
        linha_victor.text = 'VICTOR MANOEL CARAMES GARCIA GONCALVES'
        linha_victor._js.return_value = 'VICTOR MANOEL CARAMES GARCIA GONCALVES'

        linha_narlison = MagicMock()
        linha_narlison.text = 'NARLISON ROGERIO MAGALHAES GOMES Advogado: JOEL MIRANDA DE FREITAS'
        linha_narlison._js.return_value = 'NARLISON ROGERIO MAGALHAES GOMES'

        linha_bruno = MagicMock()
        linha_bruno.text = 'BRUNO DOS SANTOS GOMES MIRANDA'
        linha_bruno._js.return_value = 'BRUNO DOS SANTOS GOMES MIRANDA'

        linhas = [linha_cjs, linha_rr, linha_victor, linha_narlison, linha_bruno]

        with unittest.mock.patch('Fix.espera.elementos', return_value=linhas), \
             unittest.mock.patch('atos.comunicacao_destinatarios.aguardar_renderizacao_nativa', return_value=True), \
             unittest.mock.patch('atos.comunicacao_destinatarios._clicar_btn_acrescentar', return_value=True) as mock_click:

            dest_info = {
                'nome': 'BRUNO DOS SANTOS GOMES MIRANDA',
                'nome_oficial': 'BRUNO DOS SANTOS GOMES MIRANDA',
                'documento': '501.377.928-67',
            }

            res = selecionar_destinatario_por_documento(driver, dest_info)
            self.assertEqual(res.get('status'), 'ok')

            # O clique DEVE ter sido na linha do Bruno (linha_bruno), NUNCA na linha do Narlison
            mock_click.assert_called_once()
            args, _ = mock_click.call_args
            linha_clicada = args[1]
            self.assertEqual(linha_clicada, linha_bruno)
            self.assertNotEqual(linha_clicada, linha_narlison)

    def test_extrair_reus_mencionados_no_texto_sem_falso_positivo(self):
        """Valida que menções isoladas de sobrenomes não selecionam réus indevidos."""
        texto_decisao = (
            "Vistos etc. Defiro a desconsideracao da personalidade juridica da empresa "
            "e determino a inclusao do suscitado BRUNO DOS SANTOS GOMES MIRANDA, CPF 501.377.928-67. "
            "Intimem-se por mandado os suscitados sem advogado."
        )
        reus = [
            {'nome': 'CJS ALIMENTOS EIRELI', 'cpfcnpj': '26.571.742/0001-60'},
            {'nome': 'NARLISON ROGERIO MAGALHAES GOMES', 'cpfcnpj': '377.279.758-00'},
            {'nome': 'BRUNO DOS SANTOS GOMES MIRANDA', 'cpfcnpj': '501.377.928-67'},
        ]

        encontrados = _extrair_reus_mencionados_no_texto(texto_decisao, reus)
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0]['nome_oficial'], 'BRUNO DOS SANTOS GOMES MIRANDA')


if __name__ == '__main__':
    unittest.main()
