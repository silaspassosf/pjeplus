# -*- coding: utf-8 -*-
"""
tests/test_dom_lembrete.py -- Testes unitários para a extração de IDs de Notificação
e geração do conteúdo do lembrete no fluxo DOM (Domicílio Eletrônico).
"""

import unittest
from unittest.mock import MagicMock, patch

from bianca.dom_engine import (
    _checar_empresas_e_ids_api,
    _montar_conteudo_lembrete_dom,
)


class TestDomLembreteIdNotificacao(unittest.TestCase):
    """Garante que _checar_empresas_e_ids_api prioriza a Notificação individual

    sobre a Intimação/Despacho genérico compartilhado por várias partes.
    """

    def test_prioriza_notificacao_sobre_intimacao_generica(self):
        id_processo = "8885568"
        mock_driver = MagicMock()

        # Expedientes retornados pela API: a Intimação genérica (486923683) vem PRIMEIRO no array,
        # seguida pelas Notificações específicas (481290565, etc).
        expedientes_falsos = [
            # 0. Genéricos (Intimação compartilhada)
            {
                "id": 100,
                "nomePessoaParte": "M CASSAB COMERCIO E INDUSTRIA LTDA",
                "idDocumento": 486923683,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 101,
                "nomePessoaParte": "ASCENDANT COMERCIO DE VEICULOS LTDA",
                "idDocumento": 486923683,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 102,
                "nomePessoaParte": "CONDOMINIO SHOPPING JARDIM SUL",
                "idDocumento": 486923683,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            # 1. Específicos (Notificação individual para cada parte)
            {
                "id": 200,
                "nomePessoaParte": "SP MARKET ADMINISTRACAO E SERVICOS LTDA.",
                "idDocumento": 481290573,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 201,
                "nomePessoaParte": "BANCO CSF S/A",
                "idDocumento": 481290569,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 202,
                "nomePessoaParte": "ASCENDANT COMERCIO DE VEICULOS LTDA",
                "idDocumento": 481290570,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 203,
                "nomePessoaParte": "CONDOMINIO SHOPPING JARDIM SUL",
                "idDocumento": 481290566,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
            {
                "id": 204,
                "nomePessoaParte": "M CASSAB COMERCIO E INDUSTRIA LTDA",
                "idDocumento": 481290565,
                "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
                "cienciaViaSistema": True,
                "dataCiencia": None,
            },
        ]

        documentos_mock = {
            486923683: {"id": 486923683, "titulo": "Intimação", "idUnicoDocumento": "7432019"},
            481290573: {"id": 481290573, "titulo": "Notificação", "idUnicoDocumento": "8201597"},
            481290569: {"id": 481290569, "titulo": "Notificação", "idUnicoDocumento": "030869f"},
            481290570: {"id": 481290570, "titulo": "Notificação", "idUnicoDocumento": "46fa065"},
            481290566: {"id": 481290566, "titulo": "Notificação", "idUnicoDocumento": "a011ede"},
            481290565: {"id": 481290565, "titulo": "Notificação", "idUnicoDocumento": "512224b"},
        }

        mock_client = MagicMock()
        mock_client.expedientes_processo.return_value = expedientes_falsos
        mock_client.documento_por_id.side_effect = lambda pid, doc_id: documentos_mock.get(doc_id)

        with patch("Fix.variaveis.session_from_driver", return_value=(MagicMock(), "https://base")), \
             patch("Fix.variaveis.PjeApiClient", return_value=mock_client), \
             patch("bianca.dom_engine._pjdp_do_passivo_api", return_value=[]):

            resultado = _checar_empresas_e_ids_api(id_processo, mock_driver)

        # Mapear resultado por empresa
        mapa = {d["empresa"]: d["id_unico_documento"] for d in resultado}

        # Verificação rigorosa: nenhuma deve receber o id 7432019 (Intimação genérica)
        self.assertNotIn("7432019", mapa.values(), "O ID genérico 7432019 não deve ser atribuído quando houver Notificação individual")

        # Cada empresa deve receber o ID exato da sua respectiva Notificação
        self.assertEqual(mapa["M CASSAB COMERCIO E INDUSTRIA LTDA"], "512224b")
        self.assertEqual(mapa["ASCENDANT COMERCIO DE VEICULOS LTDA"], "46fa065")
        self.assertEqual(mapa["CONDOMINIO SHOPPING JARDIM SUL"], "a011ede")
        self.assertEqual(mapa["SP MARKET ADMINISTRACAO E SERVICOS LTDA."], "8201597")
        self.assertEqual(mapa["BANCO CSF S/A"], "030869f")

    def test_montar_conteudo_lembrete_dom(self):
        destinatarios = [
            {"empresa": "M CASSAB", "id_unico_documento": "512224b"},
            {"empresa": "BANCO CSF", "id_unico_documento": "030869f"},
        ]
        conteudo = _montar_conteudo_lembrete_dom(destinatarios)
        self.assertEqual(
            conteudo,
            "Citação - renovei via correios: M CASSAB - 512224b, BANCO CSF - 030869f"
        )
        self.assertTrue(len(conteudo) <= 200)

    def test_montar_conteudo_lembrete_dom_truncamento_200(self):
        # Gera lista longa para testar limite do PJe
        destinatarios = [
            {"empresa": f"EMPRESA MUITO LONGA DE TESTE NUMERO {i} LTDA", "id_unico_documento": f"uid{i}abc"}
            for i in range(15)
        ]
        conteudo = _montar_conteudo_lembrete_dom(destinatarios)
        self.assertTrue(len(conteudo) <= 200)
        self.assertTrue(conteudo.startswith("Citação - renovei via correios: "))

    @patch("bianca.dom_engine.has_dom_eletronico_reminder", return_value=False)
    @patch("bianca.dom_engine._checar_empresas_e_ids_api")
    @patch("bianca.dom_engine.criar_gigs")
    @patch("bianca.dom_engine.criar_comentario", return_value=True)
    @patch("bianca.dom_engine.criar_lembrete_posit", return_value=True)
    @patch("bianca.dom_engine.def_chip", return_value=True)
    @patch("bianca.dom_engine._verificar_acesso_negado")
    @patch("bianca.dom_engine._obter_abas", side_effect=[['aba1'], ['aba1', 'aba2']])
    @patch("bianca.dom_engine.pec_arordv", return_value=True)
    def test_callback_bucket2_executa_comentario_e_lembrete_sem_gigs(
        self,
        mock_pec,
        mock_abas,
        mock_acesso,
        mock_chip,
        mock_lembrete,
        mock_coment,
        mock_gigs,
        mock_checar_api,
        mock_verif_lembrete,
    ):
        """Verifica se callback_bucket2 executa apenas Comentário + Lembrete DomElet (sem GIGS)."""
        from bianca.dom_engine import ListaDestinatariosDOM, callback_bucket2

        mock_driver = MagicMock()
        mock_driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/8885568/detalhe"
        mock_driver._numero_processo_lista = "1000123-45.2026.5.02.0001"

        destinatarios_mock = ListaDestinatariosDOM([
            {"empresa": "BANCO CSF", "id_unico_documento": "030869f"},
        ])
        destinatarios_mock.pjdp_detectado = []
        mock_checar_api.return_value = destinatarios_mock

        processo_info = {"dataAudiencia": "2026-11-02 09:00:00"}  # segunda-feira

        with patch("bianca.dom_engine._dia_semana_audiencia", return_value=0):
            res = callback_bucket2(mock_driver, tipo_processo="ATOrd", processo_info=processo_info)

        self.assertTrue(res)
        # GIGS NÃO deve ser criado
        mock_gigs.assert_not_called()
        # Comentário deve ser criado
        mock_coment.assert_called_once_with(mock_driver, "DOM", log=True)
        # Lembrete Post-it DomElet deve ser criado
        mock_lembrete.assert_called_once_with(
            mock_driver,
            "DomElet",
            "Citação - renovei via correios: BANCO CSF - 030869f",
            debug=True,
            marcadores_titulo=["domelet", "not. id"],
            marcadores_conteudo=["renovei via correios"],
        )
        # Chips sao apagados uma unica vez (primeiro passo do fluxo)
        self.assertEqual(mock_chip.call_count, 1)
        mock_pec.assert_called_once()

    @patch("bianca.dom_engine._checar_empresas_e_ids_api")
    @patch("bianca.dom_engine.criar_gigs")
    @patch("bianca.dom_engine.criar_comentario")
    @patch("bianca.dom_engine.criar_lembrete_posit")
    @patch("bianca.dom_engine.def_chip")
    @patch("bianca.dom_engine.pec_arord", return_value=True)
    def test_callback_bucket2_pula_sem_acoes_quando_unica_reclamada_e_pjdp(
        self,
        mock_pec,
        mock_chip,
        mock_lembrete,
        mock_coment,
        mock_gigs,
        mock_checar_api,
    ):
        """Quando a única reclamada com domicílio eletrônico é PJDP, não executa o wrapper nem ações."""
        from bianca.dom_engine import ListaDestinatariosDOM, callback_bucket2

        mock_driver = MagicMock()
        mock_driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/8881116/detalhe"
        mock_driver._numero_processo_lista = "1001572-12.2026.5.02.0703"

        # 0 empresas filtradas, e PJDP detectada
        destinatarios_mock = ListaDestinatariosDOM([])
        destinatarios_mock.pjdp_detectado = ["EMPRESA BRASILEIRA DE CORREIOS E TELEGRAFOS"]
        mock_checar_api.return_value = destinatarios_mock

        res = callback_bucket2(mock_driver, tipo_processo="ATOrd")

        # Deve pular retornando True
        self.assertTrue(res)
        # NENHUMA ação deve ser executada (não cria comentário, lembrete, chips, gigs ou PEC)
        mock_coment.assert_not_called()
        mock_lembrete.assert_not_called()
        mock_chip.assert_not_called()
        mock_gigs.assert_not_called()
        mock_pec.assert_not_called()

    def test_def_chip_normalizacao_e_matching(self):
        """Garante que normalização de chips desconsidera maiúsculas, acentos, traços e pontuação."""
        from atos.movimentos_chips import normalizar_chip_texto, chip_corresponde_padrao

        padrao = "Domicilio Eletronico - Ciencia Automatica"
        padrao_norm = normalizar_chip_texto(padrao)

        casos_validos = [
            "Domicílio Eletrônico – Ciência Automática",  # en-dash
            "Domicílio Eletrônico — Ciência Automática",  # em-dash
            "Domicilio Eletronico - Ciencia Automatica\ncancel",  # newline + botão
            "DOMICÍLIO ELETRÔNICO: CIÊNCIA AUTOMÁTICA",  # maiúsculas e dois pontos
            "  Domicílio  Eletrônico  -  Ciência  Automática  ",  # espaços múltiplos
        ]

        for texto in casos_validos:
            chip_norm = normalizar_chip_texto(texto)
            self.assertTrue(
                chip_corresponde_padrao(chip_norm, padrao_norm),
                f"Falha ao casar '{texto}' com '{padrao}'",
            )

    # ------------------------------------------------------------------
    # Filtro de advogado: parte alvo COM advogado sai do fluxo DOM
    # (mesmo criterio do prep.js: `representantes` nao vazio).
    # ------------------------------------------------------------------

    @staticmethod
    def _partes_api(representantes_por_nome):
        """Monta o dict /partes no formato {"PASSIVO": [...]}."""
        return {
            "ATIVO": [{"nome": "RECLAMANTE", "documento": "111.111.111-11", "representantes": []}],
            "PASSIVO": [
                {
                    "nome": nome,
                    "documento": "17.858.016/0001-32",
                    "representantes": [{"nome": "ADVOGADO X", "idPessoa": 1}] if tem else [],
                }
                for nome, tem in representantes_por_nome
            ],
        }

    def _rodar_checar(self, partes, expedientes, documentos):
        mock_client = MagicMock()
        mock_client.expedientes_processo.return_value = expedientes
        mock_client.partes.return_value = partes
        mock_client.documento_por_id.side_effect = lambda pid, doc_id: documentos.get(doc_id)
        with patch("Fix.variaveis.session_from_driver", return_value=(MagicMock(), "https://base")), \
             patch("Fix.variaveis.PjeApiClient", return_value=mock_client), \
             patch("bianca.dom_engine._pjdp_do_passivo_api", return_value=set()):
            return _checar_empresas_e_ids_api("8894351", MagicMock())

    def _expediente_dom(self, nome, id_exp, id_documento):
        return {
            "id": id_exp,
            "nomePessoaParte": nome,
            "idDocumento": id_documento,
            "meioExpedienteEnum": "DOMICILIO_ELETRONICO",
            "cienciaViaSistema": True,
            "dataCiencia": None,
        }

    def test_alvo_com_advogado_sai_do_filtro(self):
        """Empresa COM advogado nao entra no filtro DOM; empresa SEM entrou."""
        partes = self._partes_api([("COM ADVOGADO LTDA", True), ("SEM ADVOGADO LTDA", False)])
        expedientes = [
            self._expediente_dom("COM ADVOGADO LTDA", 1, 501),
            self._expediente_dom("SEM ADVOGADO LTDA", 2, 502),
        ]
        documentos = {
            501: {"id": 501, "titulo": "Notificação", "idUnicoDocumento": "aaa1111"},
            502: {"id": 502, "titulo": "Notificação", "idUnicoDocumento": "bbb2222"},
        }

        resultado = self._rodar_checar(partes, expedientes, documentos)

        self.assertEqual([d["empresa"] for d in resultado], ["SEM ADVOGADO LTDA"])
        self.assertEqual(resultado[0]["id_unico_documento"], "bbb2222")
        self.assertEqual(resultado.alvos_com_advogado, ["COM ADVOGADO LTDA"])

    def test_todas_com_advogado_resulta_em_lista_vazia(self):
        """Se TODOS os alvos tem advogado, a lista fica vazia (callback pula o processo)."""
        partes = self._partes_api([("EMPRESA A LTDA", True), ("EMPRESA B LTDA", True)])
        expedientes = [
            self._expediente_dom("EMPRESA A LTDA", 1, 601),
            self._expediente_dom("EMPRESA B LTDA", 2, 602),
        ]
        documentos = {
            601: {"id": 601, "titulo": "Notificação", "idUnicoDocumento": "ccc3333"},
            602: {"id": 602, "titulo": "Notificação", "idUnicoDocumento": "ddd4444"},
        }

        resultado = self._rodar_checar(partes, expedientes, documentos)

        self.assertEqual(list(resultado), [])
        self.assertEqual(sorted(resultado.alvos_com_advogado), ["EMPRESA A LTDA", "EMPRESA B LTDA"])

    def test_alvo_com_advogado_casa_ignorando_acentos_e_caixa(self):
        """Match por nome normalizado: 'CONDOMÍNIO' vs 'CONDOMINIO' nao escapa do filtro."""
        partes = self._partes_api([("CONDOMÍNIO SHOPPING JARDIM SUL", True)])
        expedientes = [self._expediente_dom("CONDOMINIO SHOPPING JARDIM SUL", 1, 901)]
        documentos = {901: {"id": 901, "titulo": "Notificação", "idUnicoDocumento": "ggg7777"}}

        resultado = self._rodar_checar(partes, expedientes, documentos)

        self.assertEqual(list(resultado), [])
        # O match com a API foi por nome normalizado; o registro guarda o nome
        # como veio da API (com acento), nao o do expediente (sem acento).
        self.assertEqual(resultado.alvos_com_advogado, ["CONDOMÍNIO SHOPPING JARDIM SUL"])

    def test_nenhum_alvo_com_advogado_entra_igual_antes(self):
        """Sem advogado em ninguem, o filtro nao remove nada (comportamento antigo preservado)."""
        partes = self._partes_api([("EMPRESA C LTDA", False)])
        expedientes = [self._expediente_dom("EMPRESA C LTDA", 1, 701)]
        documentos = {701: {"id": 701, "titulo": "Notificação", "idUnicoDocumento": "eee5555"}}

        resultado = self._rodar_checar(partes, expedientes, documentos)

        self.assertEqual([d["empresa"] for d in resultado], ["EMPRESA C LTDA"])
        self.assertEqual(resultado.alvos_com_advogado, [])

    def test_falha_na_api_de_partes_nao_remove_alvos(self):
        """Se /partes falhar, ninguem e' filtrado (fail-open: nao perde alvo por erro de API)."""
        partes = self._partes_api([("EMPRESA D LTDA", False)])
        expedientes = [self._expediente_dom("EMPRESA D LTDA", 1, 801)]
        documentos = {801: {"id": 801, "titulo": "Notificação", "idUnicoDocumento": "fff6666"}}

        mock_client = MagicMock()
        mock_client.expedientes_processo.return_value = expedientes
        mock_client.partes.side_effect = RuntimeError("boom")
        mock_client.documento_por_id.side_effect = lambda pid, doc_id: documentos.get(doc_id)
        with patch("Fix.variaveis.session_from_driver", return_value=(MagicMock(), "https://base")), \
             patch("Fix.variaveis.PjeApiClient", return_value=mock_client), \
             patch("bianca.dom_engine._pjdp_do_passivo_api", return_value=set()):
            resultado = _checar_empresas_e_ids_api("8894351", MagicMock())

        self.assertEqual([d["empresa"] for d in resultado], ["EMPRESA D LTDA"])

    @patch("bianca.dom_engine.has_dom_eletronico_reminder", return_value=False)
    @patch("bianca.dom_engine._checar_empresas_e_ids_api")
    @patch("bianca.dom_engine.criar_gigs")
    @patch("bianca.dom_engine.criar_comentario", return_value=True)
    @patch("bianca.dom_engine.criar_lembrete_posit", return_value=True)
    @patch("bianca.dom_engine.def_chip", return_value=True)
    @patch("bianca.dom_engine._verificar_acesso_negado")
    @patch("bianca.dom_engine._obter_abas", side_effect=[['aba1'], ['aba1', 'aba2']])
    @patch("bianca.dom_engine.pec_arordv", return_value=True)
    def test_lembrete_so_lista_empresas_sem_advogado(
        self,
        mock_pec,
        mock_abas,
        mock_acesso,
        mock_chip,
        mock_lembrete,
        mock_coment,
        mock_gigs,
        mock_checar_api,
        mock_verif_lembrete,
    ):
        """O lembrete deve constar apenas as empresas SEM advogado."""
        from bianca.dom_engine import ListaDestinatariosDOM, callback_bucket2

        mock_driver = MagicMock()
        mock_driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/8894351/detalhe"
        mock_driver._numero_processo_lista = "1000123-45.2026.5.02.0001"

        destinatarios = ListaDestinatariosDOM([
            {"empresa": "SEM ADVOGADO LTDA", "id_unico_documento": "bbb2222"},
        ])
        destinatarios.alvos_com_advogado = ["COM ADVOGADO LTDA"]
        mock_checar_api.return_value = destinatarios

        with patch("bianca.dom_engine._dia_semana_audiencia", return_value=0):
            res = callback_bucket2(mock_driver, tipo_processo="ATOrd")

        self.assertTrue(res)
        mock_lembrete.assert_called_once_with(
            mock_driver,
            "DomElet",
            "Citação - renovei via correios: SEM ADVOGADO LTDA - bbb2222",
            debug=True,
            marcadores_titulo=["domelet", "not. id"],
            marcadores_conteudo=["renovei via correios"],
        )
        # "COM ADVOGADO LTDA" nao pode aparecer no lembrete
        conteudo = mock_lembrete.call_args[0][2]
        self.assertNotIn("COM ADVOGADO", conteudo)



if __name__ == "__main__":
    unittest.main()

