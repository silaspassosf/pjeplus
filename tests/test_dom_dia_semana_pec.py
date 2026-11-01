# -*- coding: utf-8 -*-
"""
tests/test_dom_dia_semana_pec.py -- Regressao: o PEC do fluxo DOM deve ser
escolhido pelo dia da semana da audiencia.

Regra (mesma da triagem, bianca/triagem/acoes.py::_usa_padrao_novo):
    audiencia em segunda, terca ou sexta -> pec_arordv / pec_arsumv (AR-Ordv/AR-Sumv)
    audiencia em quarta ou quinta        -> pec_arord  / pec_arsum  (AR-Or/AR-Su)

O bug corrigido: o fluxo DOM montava `processo_info` apenas com
`{"id": ..., "numeroProcesso": ...}`, sem a data da audiencia. O
`dt#audiencias` nao existe na aba de detalhes, entao `_dia_semana_audiencia`
devolvia None e todo processo caia no PEC padrao (AR-Or/AR-Su),
independente do dia.
"""

import unittest
from unittest.mock import MagicMock, patch

from bianca.dom_engine import (
    ListaDestinatariosDOM,
    _resolver_dia_audiencia,
    callback_bucket2,
)


def _destinatarios():
    lst = ListaDestinatariosDOM([
        {"empresa": "BANCO CSF", "id_unico_documento": "030869f"},
    ])
    lst.pjdp_detectado = []
    return lst


def _driver():
    drv = MagicMock()
    drv.current_url = "https://pje.trt2.jus.br/pjekz/processo/8885568/detalhe"
    drv._numero_processo_lista = "1000123-45.2026.5.02.0001"
    return drv


def _executar_callback(data_api, tipo="ATSum"):
    """Executa callback_bucket2 com a data vinda apenas da API.

    processo_info e' exatamente o que processar_processo_dom monta:
    {"id": ..., "numeroProcesso": ...}, sem nenhuma data de audiencia.

    Returns:
        (sucesso, dict com o wrapper de PEC chamado)
    """
    processo_info = {"id": "8885568", "numeroProcesso": "8885568"}

    # Antes da PEC: 1 aba; depois (nova aba aberta pela PEC): 2 abas.
    with patch("bianca.dom_engine._checar_empresas_e_ids_api", return_value=_destinatarios()), \
         patch("bianca.dom_engine.has_dom_eletronico_reminder", return_value=False), \
         patch("bianca.dom_engine.def_chip", return_value=True), \
         patch("bianca.dom_engine.criar_comentario", return_value=True), \
         patch("bianca.dom_engine.criar_lembrete_posit", return_value=True), \
         patch("bianca.dom_engine._verificar_acesso_negado", return_value=None), \
         patch("bianca.dom_engine._obter_abas", side_effect=[["a"], ["a", "b"]]), \
         patch("bianca.dom_engine._data_audiencia_api", return_value=data_api), \
         patch("bianca.dom_engine.pec_arsumv", return_value=True) as pec_arsumv, \
         patch("bianca.dom_engine.pec_arordv", return_value=True) as pec_arordv, \
         patch("bianca.dom_engine.pec_arsum", return_value=True) as pec_arsum, \
         patch("bianca.dom_engine.pec_arord", return_value=True) as pec_arord:
        ok = callback_bucket2(_driver(), tipo_processo=tipo, processo_info=processo_info)

    return ok, {
        "arsumv": pec_arsumv.called, "arordv": pec_arordv.called,
        "arsum": pec_arsum.called, "arord": pec_arord.called,
    }


class TestResolverDiaAudiencia(unittest.TestCase):
    """As camadas de resolucao da data da audiencia."""

    def test_usa_data_do_processo_info(self):
        # 2026-11-05 e quinta-feira
        self.assertEqual(
            _resolver_dia_audiencia(None, {"dataProximaAudiencia": "2026-11-05"}),
            3,
        )

    def test_fallback_api_quando_processo_info_nao_tem_data(self):
        """processo_info do DOM tem so id/numero: precisa cair na API."""
        with patch(
            "bianca.dom_engine._data_audiencia_api",
            return_value="2026-11-06T09:00:00",  # sexta-feira
        ) as mock_api:
            dia = _resolver_dia_audiencia(None, {"id": "8885568", "numeroProcesso": "1000123"})

        self.assertEqual(dia, 4)
        mock_api.assert_called_once()

    def test_retorna_none_quando_api_tambem_falha(self):
        with patch("bianca.dom_engine._data_audiencia_api", return_value=None):
            self.assertIsNone(_resolver_dia_audiencia(None, {"id": "8885568"}))


class TestApiAudiencias(unittest.TestCase):
    """Contrato de GET /pje-comum-api/api/processos/id/{id}/audiencias.

    Documentado em api/apis.md (26.1) e usado pelo maisPJE
    (`obterAudienciaMarcada`): primeira audiencia da lista, campo `dataInicio`.
    """

    def _client(self, resposta_json):
        from Fix.variaveis import PjeApiClient
        sess = MagicMock()
        sess.get.return_value.ok = True
        sess.get.return_value.json.return_value = resposta_json
        return PjeApiClient(sess, "https://pje.trt2.jus.br")

    def test_le_data_inicio_da_primeira_audiencia(self):
        client = self._client([
            {"dataInicio": "2026-12-09T08:50:00", "status": "M"},
        ])
        self.assertEqual(client.data_proxima_audiencia("8885568"), "2026-12-09T08:50:00")

    def test_aceita_resposta_embrulhada_em_content(self):
        client = self._client({"content": [{"dataInicio": "2026-11-06T09:00:00"}]})
        self.assertEqual(client.data_proxima_audiencia("8885568"), "2026-11-06T09:00:00")

    def test_sem_audiencia_retorna_none(self):
        self.assertIsNone(self._client([]).data_proxima_audiencia("8885568"))

    def test_erro_de_http_retorna_lista_vazia(self):
        client = self._client([])
        client.sess.get.return_value.ok = False
        self.assertEqual(client.audiencias_processo("8885568"), [])
        self.assertIsNone(client.data_proxima_audiencia("8885568"))


class TestPecPorDiaDaAudiencia(unittest.TestCase):
    """callback_bucket2 escolhe o wrapper do PEC conforme o dia."""

    def _assert_wrapper(self, usados, esperado):
        alvo = {"arsumv": False, "arordv": False, "arsum": False, "arord": False}
        alvo[esperado] = True
        self.assertEqual(usados, alvo)

    def test_sumaria_sexta_usa_arsumv(self):
        ok, usados = _executar_callback("2026-11-06T09:00:00")
        self.assertTrue(ok)
        self._assert_wrapper(usados, "arsumv")

    def test_sumaria_segunda_usa_arsumv(self):
        ok, usados = _executar_callback("2026-11-02T09:00:00")
        self.assertTrue(ok)
        self._assert_wrapper(usados, "arsumv")

    def test_sumaria_quinta_usa_arsum(self):
        ok, usados = _executar_callback("2026-11-05T09:00:00")
        self.assertTrue(ok)
        self._assert_wrapper(usados, "arsum")

    def test_ordinaria_terca_usa_arordv(self):
        ok, usados = _executar_callback("2026-11-03T09:00:00", tipo="ATOrd")
        self.assertTrue(ok)
        self._assert_wrapper(usados, "arordv")

    def test_ordinaria_quarta_usa_arord(self):
        ok, usados = _executar_callback("2026-11-04T09:00:00", tipo="ATOrd")
        self.assertTrue(ok)
        self._assert_wrapper(usados, "arord")

    def test_dia_indefinido_cai_no_padrao(self):
        """Sem data em lugar nenhum: mantem o comportamento antigo (padrao)."""
        ok, usados = _executar_callback(None)
        self.assertTrue(ok)
        self._assert_wrapper(usados, "arsum")


if __name__ == "__main__":
    unittest.main()
