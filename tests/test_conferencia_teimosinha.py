"""Testes de SISB/conferencia_teimosinha.py — conferência das séries e definição do fluxo.

Cobre a paridade com a conferência real (`_filtrar_series` + bloco `tipo_fluxo` e
`_calcular_estrategia_bloqueio` do `SISB/core.py`): mesmos seletores/data-label, mesma
normalização de texto, mesma regra de data, mesmos filtros e as três saídas de fluxo —
NEGATIVO, DESBLOQUEIO e POSITIVO (TRANSFERIR_TUDO / TRANSFERIR_PARCIAL).

Roda com:  python -m unittest tests.test_conferencia_teimosinha
"""

import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from SISB import conferencia_teimosinha as ct

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


# ───────────────────────────── página falsa ─────────────────────────────


class Loc:
    def __init__(self, itens=None):
        self._itens = list(itens or [])

    @property
    def first(self):
        return Loc(self._itens[:1])

    def count(self):
        return len(self._itens)

    def nth(self, indice):
        return self._itens[indice]

    def is_visible(self):
        return True

    def click(self, timeout=None):
        return None

    def fill(self, valor):
        return None

    def press(self, tecla):
        return None

    def evaluate(self, script):
        return []


class Pagina:
    """Página falsa: `evaluate` devolve o que o JS de extração devolveria."""

    def __init__(self, brutos):
        self.brutos = brutos
        self.consultados = []

    def evaluate(self, script):
        self.script = script
        return self.brutos

    def locator(self, seletor):
        self.consultados.append(seletor)
        return Loc([])


def _driver(brutos, url=ct.URL_TEIMOSINHA):
    d = MagicMock()
    d.page = Pagina(brutos)
    d.current_url = url
    d.get = MagicMock()
    return d


def _bruto(id_serie='1', protocolo='2026/0001', acao='1001439-72.2023.5.02.0703',
           bloquear='R$ 1.000,00', bloqueado='R$ 0,00',
           # data recente: dentro do prazo padrão de 30 dias usado por conferir_fluxo
           data='01 DE NOVEMBRO DE 2026', situacao='Encerrada', linha_index=0):
    return {
        'linha_index': linha_index,
        'tem_id': bool(id_serie),
        'id_serie': id_serie,
        'protocolo': protocolo,
        'acao': acao,
        'valor_bloquear_text': bloquear,
        'valor_bloqueado_text': bloqueado,
        'data_conclusao_text': data,
        'situacao': situacao,
    }


def _patches(aparece=True):
    return [
        patch.object(ct.espera, 'ate_aparecer', return_value=aparece),
        patch.object(ct.espera, 'ate_texto', return_value=False),
        patch.object(ct.espera, 'assentar'),
        patch.object(ct, 'aguardar_renderizacao_nativa', return_value=True),
    ]


class Base(unittest.TestCase):
    def setUp(self):
        for p in _patches():
            self.addCleanup(p.stop)
            p.start()

    def _fluxo(self, brutos, dados_processo=None, data_limite=None):
        return ct.conferir_fluxo(_driver(brutos), None, dados_processo=dados_processo,
                                 data_limite=data_limite, log=False)


# ───────────────────────────── paridade de extração ─────────────────────────────


class TestParidadeExtracao(Base):
    def test_usa_os_mesmos_seletores_do_codigo_real(self):
        self.assertIn('table.mat-table', ct.SEL_LINHAS)
        self.assertIn('tr.mat-row', ct.SEL_LINHAS)
        for pedaco in ("td[data-label=", 'cdk-column-sequencial', 'cdk-column-dataProgramada',
                       'cdk-column-valorBloqueado', 'cdk-column-dataFim', 'textContent'):
            self.assertIn(pedaco, ct.JS_LER_SERIES)

    def test_extrai_os_mesmos_campos(self):
        serie = ct.ler_series(_driver([_bruto(bloqueado='R$ 1.234,56',
                                              data='10 DE SETEMBRO DE 2026')]), log=False)[0]

        self.assertEqual(serie['id_serie'], '1')
        self.assertEqual(serie['protocolo'], '2026/0001')
        self.assertEqual(serie['acao'], '1001439-72.2023.5.02.0703')
        self.assertEqual(serie['valor_bloqueado'], 1234.56)
        self.assertEqual(serie['valor_bloquear'], 1000.0)
        self.assertEqual(serie['data_conclusao'], datetime(2026, 9, 10))
        self.assertTrue(serie['encerrada'])

    def test_linha_sem_celula_sequencial_vira_apenas_indice(self):
        bruto = _bruto(id_serie='', situacao='', data='')
        serie = ct.ler_series(_driver([bruto]), log=False)[0]

        self.assertEqual(set(serie), {'linha_index', 'valor_bloqueado', 'valor_bloquear',
                                      'data_conclusao', 'encerrada'})
        self.assertEqual(ct.filtrar_validas([serie], log=False), [])

    def test_tabela_ausente_devolve_lista_vazia(self):
        self.assertEqual(ct.ler_series(_driver(None), log=False), [])

    def test_falha_na_leitura_nao_levanta(self):
        d = _driver([])
        d.page.evaluate = MagicMock(side_effect=RuntimeError('boom'))
        self.assertEqual(ct.ler_series(d, log=False), [])


# ───────────────────────────── filtro (igual ao real) ─────────────────────────────


class TestFiltro(Base):
    def test_mantem_apenas_encerradas(self):
        series = ct.ler_series(_driver([
            _bruto(id_serie='1', situacao='Encerrada'),
            _bruto(id_serie='2', situacao='Em andamento', linha_index=1),
        ]), log=False)

        self.assertEqual([s['id_serie'] for s in ct.filtrar_validas(series, log=False)], ['1'])

    def test_descarta_serie_fora_do_prazo(self):
        series = ct.ler_series(_driver([
            _bruto(id_serie='antiga', data='10 DE JANEIRO DE 2026'),
            _bruto(id_serie='recente', data='01 DE NOVEMBRO DE 2026', linha_index=1),
        ]), log=False)

        validas = ct.filtrar_validas(series, datetime(2026, 10, 9), log=False)
        self.assertEqual([s['id_serie'] for s in validas], ['recente'])

    def test_data_em_outro_formato_e_descartada_como_no_real(self):
        series = ct.ler_series(_driver([
            _bruto(id_serie='barra', data='10/09/2026'),
            _bruto(id_serie='curta', data='10 SET 2026', linha_index=1),
        ]), log=False)

        self.assertEqual(ct.filtrar_validas(series, log=False), [])

    def test_formato_da_serie_valida_e_o_do_core(self):
        validas = self._fluxo([_bruto(bloqueado='R$ 900,00')])['series_validas']
        esperado = {'id_serie', 'protocolo', 'acao', 'data_conclusao', 'data_conclusao_text',
                    'situacao', 'valor_bloqueado', 'valor_bloquear', 'valor_bloqueado_text',
                    'valor_bloquear_text', 'linha_index'}
        self.assertEqual(set(validas[0]), esperado)

    def test_valor_ausente_vira_zero(self):
        validas = self._fluxo([_bruto(bloqueado='', bloquear='')])['series_validas']
        self.assertEqual(validas[0]['valor_bloqueado'], 0.0)
        self.assertEqual(validas[0]['valor_bloquear'], 0.0)


# ───────────────────────────── fluxo ─────────────────────────────


class TestFluxo(Base):
    def test_negativo_quando_nada_foi_bloqueado(self):
        fluxo = self._fluxo([_bruto(bloqueado='R$ 0,00', bloquear='R$ 5.000,00')])

        self.assertEqual(fluxo['tipo_fluxo'], 'NEGATIVO')
        self.assertIsNone(fluxo['estrategia'])

    def test_negativo_sem_series(self):
        fluxo = self._fluxo([])
        self.assertEqual(fluxo['tipo_fluxo'], 'NEGATIVO')
        self.assertEqual(fluxo['total_bloqueado'], 0.0)

    def test_desbloqueio_quando_bloqueio_irrisorio(self):
        fluxo = self._fluxo([_bruto(bloqueado='R$ 50,00', bloquear='R$ 5.000,00')])

        self.assertEqual(fluxo['tipo_fluxo'], 'DESBLOQUEIO')
        self.assertIsNone(fluxo['estrategia'])

    def test_bloqueio_irrisorio_com_pouco_a_bloquear_e_positivo(self):
        fluxo = self._fluxo([_bruto(bloqueado='R$ 50,00', bloquear='R$ 500,00')])
        self.assertEqual(fluxo['tipo_fluxo'], 'POSITIVO')

    def test_positivo_transferir_tudo_quando_cabe_na_execucao(self):
        fluxo = self._fluxo([_bruto(bloqueado='R$ 800,00')],
                            dados_processo={'divida': {'valor': 'R$ 1.003,00'}})

        self.assertEqual(fluxo['tipo_fluxo'], 'POSITIVO')
        self.assertEqual(fluxo['estrategia']['tipo'], 'TRANSFERIR_TUDO')
        self.assertIsNone(fluxo['series_ordenadas'])

    def test_positivo_transferir_parcial_ordena_series(self):
        fluxo = self._fluxo([
            _bruto(id_serie='menor', bloqueado='R$ 1.000,00'),
            _bruto(id_serie='maior', bloqueado='R$ 4.000,00', linha_index=1),
        ], dados_processo={'divida': {'valor': 'R$ 1.003,00'}})

        self.assertEqual(fluxo['estrategia']['tipo'], 'TRANSFERIR_PARCIAL')
        self.assertEqual([s['id_serie'] for s in fluxo['series_ordenadas']], ['maior', 'menor'])

    def test_usa_valor_de_execucao_padrao_sem_dados(self):
        fluxo = self._fluxo([_bruto(bloqueado='R$ 500,00')])
        self.assertEqual(fluxo['estrategia']['valor_execucao'], ct.VALOR_EXECUCAO_FALLBACK)

    def test_soma_series_multiplas(self):
        fluxo = self._fluxo([
            _bruto(id_serie='1', bloqueado='R$ 300,00', bloquear='R$ 300,00'),
            _bruto(id_serie='2', bloqueado='R$ 400,00', bloquear='R$ 900,00', linha_index=1),
        ])

        self.assertEqual(fluxo['total_bloqueado'], 700.0)
        self.assertEqual(fluxo['total_bloquear'], 1200.0)
        self.assertEqual(fluxo['tipo_fluxo'], 'POSITIVO')


# ───────────────────────────── conferir / condução tranquila ─────────────────────────────


class TestConferir(Base):
    def test_conferir_com_numero_digita_e_consulta(self):
        d = _driver([_bruto(bloqueado='R$ 900,00')])
        fluxo = ct.conferir_fluxo(d, '1001439-72.2023.5.02.0703', log=False)

        self.assertEqual(fluxo['tipo_fluxo'], 'POSITIVO')
        self.assertIn(ct.SEL_CAMPO, d.page.consultados)

    def test_conferir_sem_numero_nao_digita(self):
        d = _driver([_bruto(bloqueado='R$ 900,00')])
        ct.conferir_fluxo(d, None, log=False)

        self.assertNotIn(ct.SEL_CAMPO, d.page.consultados)

    def test_numero_vazio_nao_navega(self):
        d = _driver([])
        self.assertEqual(ct.conferir(d, '   ', log=False), [])
        d.get.assert_not_called()

    def test_pagina_que_nao_abre_tenta_duas_vezes_e_nao_levanta(self):
        d = _driver([])
        for p in _patches(aparece=False):
            self.addCleanup(p.stop)
            p.start()

        self.assertEqual(ct.conferir(d, '1001439-72.2023.5.02.0703', log=False), [])
        self.assertEqual(d.get.call_count, 2)

    def test_excecao_no_dom_nao_levanta(self):
        d = _driver([_bruto()])
        with patch.object(ct, 'ler_series', side_effect=RuntimeError('boom')):
            self.assertEqual(ct.conferir(d, '1001439-72.2023.5.02.0703', log=False), [])

    def test_tem_teimosinha_responde_booleano(self):
        self.assertTrue(ct.tem_teimosinha(_driver([_bruto()]), '1001439-72.2023.5.02.0703'))
        self.assertFalse(ct.tem_teimosinha(_driver([]), '1001439-72.2023.5.02.0703'))

    def test_lote_devolve_fluxo_por_numero(self):
        numeros = ['1001439-72.2023.5.02.0703', '1000910-53.2023.5.02.0703', '']
        dados = ct.conferir_lote(_driver([_bruto(bloqueado='R$ 900,00')]), numeros, log=False)

        self.assertEqual(set(dados), set(numeros[:2]))
        self.assertEqual(dados['1001439-72.2023.5.02.0703']['tipo_fluxo'], 'POSITIVO')


# ───────────────────────────── utilidades ─────────────────────────────


class TestUtilidades(unittest.TestCase):
    def test_valor_formatos(self):
        self.assertEqual(ct._valor('R$ 1.234,56'), 1234.56)
        self.assertEqual(ct._valor('R$ 10,00'), 10.0)
        self.assertEqual(ct._valor(''), 0.0)
        self.assertEqual(ct._valor('sem valor'), 0.0)

    def test_data_formato_real(self):
        self.assertEqual(ct._data('10 DE SETEMBRO DE 2026'), datetime(2026, 9, 10))
        self.assertEqual(ct._data('01 DE NOVEMBRO DE 2026'), datetime(2026, 11, 1))

    def test_data_recusa_formatos_que_o_real_recusa(self):
        self.assertIsNone(ct._data(''))
        self.assertIsNone(ct._data('10/09/2026'))
        self.assertIsNone(ct._data('10 SET 2026'))
        self.assertIsNone(ct._data('10 DE XXXX DE 2026'))

    def test_resumo_de_fluxo_e_de_series(self):
        fluxo = {'tipo_fluxo': 'POSITIVO', 'total_bloqueado': 700.0,
                 'total_bloquear': 1200.0, 'series_validas': [{'id_serie': '1'}],
                 'estrategia': {'tipo': 'TRANSFERIR_TUDO'}}
        self.assertEqual(ct.resumo(fluxo), {'tipo_fluxo': 'POSITIVO', 'series': 1,
                                            'valor_bloqueado': 700.0,
                                            'valor_bloquear': 1200.0,
                                            'estrategia': 'TRANSFERIR_TUDO'})
        self.assertEqual(ct.resumo([{'valor_bloqueado': 10.0, 'valor_bloquear': 20.0}]),
                         {'series': 1, 'valor_bloqueado': 10.0, 'valor_bloquear': 20.0})


if __name__ == '__main__':
    unittest.main()
