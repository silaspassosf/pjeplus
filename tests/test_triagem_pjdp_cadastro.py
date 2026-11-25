# -*- coding: utf-8 -*-
"""Deteccao de PJDP com cadastro incorreto no polo passivo (fluxo bianca/triagem).

Cenario: a API geral do RPA informa o polo passivo com o campo `pjdp`
(marcador de procuradoria). Quando a parte e' um ente publico mas o cadastro
no PJe esta errado, o campo vem falso/ausente e o processo passa pelo filtro
como PJ privada. A funcao `_detectar_pjdp_cadastro_incorreto` faz uma varredura
por regex no NOME para levantar esses casos como ALERTA.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bianca.triagem.regras import (  # noqa: E402
    _checar_partes,
    _detectar_pjdp_api,
    _detectar_pjdp_cadastro_incorreto,
)


def _capa(*partes):
    """Monta capa_dados no formato da API: (nome, pjdp)."""
    return {'reclamados': [{'nome': n, 'cpfcnpj': '', 'pjdp': p} for n, p in partes]}


class TestPjdpCadastroIncorreto(unittest.TestCase):
    def test_ente_publico_sem_marcador_alerta(self):
        for nome in (
            'MUNICIPIO DE SAO PAULO',
            'ESTADO DE SAO PAULO',
            'FUNDACAO CASA',
            'SECRETARIA DE SAUDE DO ESTADO',
            'SECRETARIA MUNICIPAL DE EDUCACAO',
            'PREFEITURA DE SANTO ANDRE',
            'AUTARQUIA MUNICIPAL DE TRANSPORTES',
            'FAZENDA PUBLICA MUNICIPAL',
            'UNIAO FEDERAL',
        ):
            with self.subTest(nome=nome):
                self.assertEqual(
                    _detectar_pjdp_cadastro_incorreto(_capa((nome, False))), [nome])

    def test_ente_publico_com_marcador_nao_alerta(self):
        for nome in ('MUNICIPIO DE SAO PAULO', 'FUNDACAO CASA', 'ESTADO DE SAO PAULO'):
            with self.subTest(nome=nome):
                self.assertEqual(
                    _detectar_pjdp_cadastro_incorreto(_capa((nome, True))), [])

    def test_pj_privada_nao_alerta(self):
        for nome in (
            'PADARIA DO MUNICIPIO LTDA',
            'COMERCIO DE MUNICIPIOS LTDA',
            'ESTADO MAIOR CONSULTORIA LTDA',
            'SECRETARIA EXECUTIVA SERVICOS ME',
        ):
            with self.subTest(nome=nome):
                self.assertEqual(
                    _detectar_pjdp_cadastro_incorreto(_capa((nome, False))), [])

    def test_fundacao_match_amplo_por_spec(self):
        # "fundacao ..." e' match amplo por decisao de produto: fundacoes
        # privadas (ex.: Fundacao Bradesco) tambem caem no alerta. O alerta e'
        # informativo, entao o falso positivo e' revisado por humano.
        self.assertEqual(
            _detectar_pjdp_cadastro_incorreto(_capa(('FUNDACAO BRADESCO', False))),
            ['FUNDACAO BRADESCO'])

    def test_sem_dados_de_api_nao_alerta(self):
        self.assertEqual(_detectar_pjdp_cadastro_incorreto({}), [])
        self.assertEqual(_detectar_pjdp_cadastro_incorreto({'reclamados': []}), [])

    def test_misto_so_o_suspeito_entra(self):
        capa = _capa(
            ('JOSE DA SILVA', False),
            ('MUNICIPIO DE SAO PAULO', False),
            ('EMPRESA X LTDA', False),
        )
        self.assertEqual(
            _detectar_pjdp_cadastro_incorreto(capa), ['MUNICIPIO DE SAO PAULO'])

    def test_deteccao_pjdp_api_nao_regride(self):
        self.assertEqual(
            _detectar_pjdp_api(_capa(('MUNICIPIO DE SAO PAULO', True))),
            (True, 'MUNICIPIO DE SAO PAULO'))
        self.assertEqual(
            _detectar_pjdp_api(_capa(('MUNICIPIO DE SAO PAULO', False))),
            (False, ''))

    def test_checar_partes_emite_alerta(self):
        texto = 'RECLAMANTE: JOSE DA SILVA\nRECLAMADO: MUNICIPIO DE SAO PAULO\n'
        linhas = _checar_partes(texto, _capa(('MUNICIPIO DE SAO PAULO', False)))

        self.assertTrue(any(
            'Possivel PJDP (procuradoria) com cadastro incorreto - '
            'MUNICIPIO DE SAO PAULO' in l for l in linhas), linhas)
        # Havendo ALERTA, a linha de OK nao deve ser emitida.
        self.assertFalse(any(l.startswith('B3_PARTES: OK') for l in linhas), linhas)

    def test_checar_partes_cadastro_correto_sem_alerta(self):
        texto = 'RECLAMANTE: JOSE DA SILVA\nRECLAMADO: MUNICIPIO DE SAO PAULO\n'
        linhas = _checar_partes(texto, _capa(('MUNICIPIO DE SAO PAULO', True)))

        self.assertFalse(any('cadastro incorreto' in l for l in linhas), linhas)


if __name__ == '__main__':
    unittest.main(verbosity=2)
