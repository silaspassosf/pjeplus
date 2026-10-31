"""Testes unitários para modos 'primeiro' e 'terceiros' em selecionar_destinatarios."""

import unittest
from unittest.mock import MagicMock, patch
from atos.comunicacao_destinatarios import selecionar_destinatarios


class TestComunicacaoDestinatariosModos(unittest.TestCase):

    def setUp(self):
        self.driver = MagicMock()
        self.page = MagicMock()
        self.driver.page = self.page

    @patch('atos.comunicacao_destinatarios.wait_for_clickable')
    @patch('atos.comunicacao_destinatarios._clicar_e_aguardar_spinner')
    def test_terceiros_com_terceiros_disponiveis(self, mock_spinner, mock_wait):
        """Polo passivo 1x adicionado e terceiros adicionados quando botão habilitado."""
        btn_pp = MagicMock()
        mock_wait.return_value = btn_pp

        btn_terceiro = MagicMock()
        btn_terceiro._js.return_value = False  # is_disabled = False

        with patch('atos.comunicacao_destinatarios.espera.elemento', return_value=btn_terceiro):
            logs = []
            res = selecionar_destinatarios(self.driver, destinatarios='terceiros', log=logs.append)

            self.assertTrue(res.sucesso)
            self.assertEqual(res.status, 'geral')
            self.assertTrue(res.detalhes['polo_passivo'])
            self.assertTrue(res.detalhes['terceiros'])
            mock_spinner.assert_any_call(self.driver, btn_pp)
            mock_spinner.assert_any_call(self.driver, btn_terceiro)

    @patch('atos.comunicacao_destinatarios.wait_for_clickable')
    @patch('atos.comunicacao_destinatarios._clicar_e_aguardar_spinner')
    def test_terceiros_sem_terceiros_nao_falha(self, mock_spinner, mock_wait):
        """Quando não há terceiros (botão desabilitado), salva apenas com polo passivo sem falhar."""
        btn_pp = MagicMock()
        mock_wait.return_value = btn_pp

        btn_terceiro = MagicMock()
        btn_terceiro._js.return_value = True  # is_disabled = True

        with patch('atos.comunicacao_destinatarios.espera.elemento', return_value=btn_terceiro):
            logs = []
            res = selecionar_destinatarios(self.driver, destinatarios='terceiros', log=logs.append)

            self.assertTrue(res.sucesso)
            self.assertEqual(res.status, 'geral')
            self.assertTrue(res.detalhes['polo_passivo'])
            self.assertFalse(res.detalhes['terceiros'])
            mock_spinner.assert_called_once_with(self.driver, btn_pp)
            self.assertTrue(any('sem terceiros no processo' in m for m in logs))

    @patch('atos.comunicacao_destinatarios.aguardar_renderizacao_nativa', return_value=True)
    def test_primeiro_destinatario_sucesso(self, mock_render):
        """Modo primeiro expande polo passivo e clica no primeiro destinatário."""
        # Mock do JS do page.evaluate: expansão e clique
        self.page.evaluate.side_effect = [
            {'ok': True, 'clicou': True},   # expansão do header
            {'ok': True, 'seletor': 'button.icone-clicavel'},  # clique no 1º botão
        ]

        with patch('atos.comunicacao_destinatarios.espera.elemento', return_value=None), \
             patch('atos.comunicacao_destinatarios.espera.assentar'):
            logs = []
            res = selecionar_destinatarios(self.driver, destinatarios='primeiro', log=logs.append)

            self.assertTrue(res.sucesso)
            self.assertEqual(res.status, 'ok')
            self.assertTrue(any('Primeira seta (primeiro destinatário) clicada' in m for m in logs))

    @patch('atos.comunicacao_destinatarios._selecionar_por_lista')
    @patch('atos.comunicacao_destinatarios._resolver_destinatarios_por_documento_api')
    def test_informado_despacho_chama_extracao_api(self, mock_resolver, mock_selecionar):
        """Verifica que 'informado despacho' roteia tipo_alvo='despacho' e chama _resolver_destinatarios_por_documento_api."""
        from core.resultado_execucao import ResultadoExecucao
        mock_resolver.return_value = [{'nome_oficial': 'EMPRESA X LTDA', 'documento': '123'}]
        mock_selecionar.return_value = ResultadoExecucao(sucesso=True, status='ok', detalhes={'count': 1})

        logs = []
        res = selecionar_destinatarios(
            self.driver,
            destinatarios='informado despacho',
            dados_processo={'reu': [{'nome': 'EMPRESA X LTDA'}]},
            log=logs.append
        )

        mock_resolver.assert_called_once_with(
            self.driver,
            tipo_alvo='despacho',
            dados_processo={'reu': [{'nome': 'EMPRESA X LTDA'}]},
            numero_processo=None,
            padrao_proximidade=None,
            debug=False,
            log=logs.append
        )
        self.assertTrue(res.sucesso)
        self.assertTrue(any('informado (despacho)' in m.lower() for m in logs))

    def test_extrair_reus_mencionados_no_texto(self):
        """Valida que o match textual identifica os réus mencionados no documento."""
        from atos.comunicacao_destinatarios import _extrair_reus_mencionados_no_texto

        texto = "Vistos etc. Intime-se a ré VIA VAREJO S/A para manifestação sobre o laudo no prazo legal."
        reus = [
            {'nome': 'VIA VAREJO S/A', 'cpfcnpj': '33.041.260/0652-90'},
            {'nome': 'BANCO DO BRASIL SA', 'cpfcnpj': '00.000.000/0001-91'}
        ]

        encontrados = _extrair_reus_mencionados_no_texto(texto, reus)
        self.assertEqual(len(encontrados), 1)
        self.assertEqual(encontrados[0]['nome_oficial'], 'VIA VAREJO S/A')

    def test_pec_idpj_wrapper_configuracao(self):
        """Valida que o wrapper pec_idpj está configurado com destinatarios='informado decisao' e cliques_informado=2."""
        from atos.wrappers_pec import pec_idpj
        import inspect
        closure_vars = inspect.getclosurevars(pec_idpj)
        kwargs = closure_vars.nonlocals
        self.assertEqual(kwargs.get('destinatarios'), 'informado decisao')
        self.assertEqual(kwargs.get('cliques_informado'), 2)

    def test_pec_mddid_wrappers_configuracao(self):
        """Valida que pec_mddsent e pec_editalsent (pec mddid) usam destinatarios='informado sentenca suscitados'."""
        from atos.wrappers_pec import pec_mddsent, pec_editalsent
        import inspect
        vars_mdd = inspect.getclosurevars(pec_mddsent).nonlocals
        vars_edital = inspect.getclosurevars(pec_editalsent).nonlocals

        self.assertEqual(vars_mdd.get('destinatarios'), 'informado sentenca suscitados')
        self.assertEqual(vars_mdd.get('cliques_informado'), 2)

        self.assertEqual(vars_edital.get('destinatarios'), 'informado sentenca suscitados')
        self.assertEqual(vars_edital.get('cliques_informado'), 1)

    def test_pec_sid_wrapper_configuracao(self):
        """Valida que pec_sid está configurado com destinatarios='informado sentenca suscitados' e gigs_extra=(7, 'xs carta')."""
        from atos.wrappers_pec import pec_sid
        import inspect
        vars_sid = inspect.getclosurevars(pec_sid).nonlocals
        self.assertEqual(vars_sid.get('destinatarios'), 'informado sentenca suscitados')
        self.assertEqual(vars_sid.get('gigs_extra'), (7, 'xs carta'))

    @patch('atos.comunicacao_destinatarios._extrair_reus_mencionados_no_texto')
    def test_resolver_destinatarios_por_documento_com_partes_dict(self, mock_match):
        """Valida que _resolver_destinatarios_por_documento_api processa partes em formato dict {'PASSIVO': [...]}."""
        from atos.comunicacao_destinatarios import _resolver_destinatarios_por_documento_api
        mock_driver = MagicMock()
        mock_driver.current_url = 'https://pje.trt2.jus.br/pjekz/processo/4464248/detalhe'

        mock_client = MagicMock()
        mock_client.partes.return_value = {
            'ATIVO': [{'nome': 'AUTOR DA SILVA', 'documento': '111'}],
            'PASSIVO': [{'nome': 'EMPRESA REU LTDA', 'documento': '222'}]
        }
        mock_client.timeline.return_value = [
            {'id': '999', 'tipo': 'Decisão', 'titulo': 'Decisão'}
        ]
        mock_match.return_value = [{'nome_oficial': 'EMPRESA REU LTDA', 'documento': '222'}]

        with patch('Fix.variaveis.cliente_para', return_value=mock_client), \
             patch('Fix.variaveis.obter_texto_documento', return_value='Texto da decisão com EMPRESA REU LTDA'):
            resultado = _resolver_destinatarios_por_documento_api(
                mock_driver,
                tipo_alvo='decisao',
                dados_processo=None
            )
            self.assertEqual(len(resultado), 1)
            self.assertEqual(resultado[0]['nome_oficial'], 'EMPRESA REU LTDA')

    def test_extrair_reus_com_proximidade_suscitados(self):
        """Valida que apenas os réus próximos ao termo 'suscitados' são extraídos, ignorando a empresa ré principal."""
        from atos.comunicacao_destinatarios import _extrair_reus_mencionados_no_texto

        texto = (
            "Vistos etc. Trata-se de incidente de desconsideração da personalidade jurídica instaurado "
            "em face de CONKETAL CONSTRUCOES LTDA, CNPJ: 00.880.282/0001-69; "
            "suscitados ANTONIO NUNES DOS SANTOS, CPF: 094.982.598-01; "
            "ROSEMEIRE NEVES DA ROCHA SANTOS, CPF: 094.591.558-63. "
            "Cite-se para manifestação."
        )
        reus = [
            {'nome': 'CONKETAL CONSTRUCOES LTDA', 'cpfcnpj': '00.880.282/0001-69'},
            {'nome': 'ANTONIO NUNES DOS SANTOS', 'cpfcnpj': '094.982.598-01'},
            {'nome': 'ROSEMEIRE NEVES DA ROCHA SANTOS', 'cpfcnpj': '094.591.558-63'}
        ]

        # Com detecção automática de suscitados ou padrão explícito
        encontrados = _extrair_reus_mencionados_no_texto(texto, reus, padrao_proximidade=r'\b(?:suscitad[oas]{1,2})\b')
        nomes_encontrados = [e['nome_oficial'] for e in encontrados]

        self.assertIn('ANTONIO NUNES DOS SANTOS', nomes_encontrados)
        self.assertIn('ROSEMEIRE NEVES DA ROCHA SANTOS', nomes_encontrados)
        self.assertNotIn('CONKETAL CONSTRUCOES LTDA', nomes_encontrados)
        self.assertEqual(len(encontrados), 2)

    def test_informado_decisao_idpj_com_cpf_sem_proximidade(self):
        """Valida que em decisão IDPJ (informado decisao, sem padrao_proximidade),
        o match por CPF identifica unicamente o sócio pessoa física e ignora a empresa ré do cabeçalho."""
        from atos.comunicacao_destinatarios import _extrair_reus_mencionados_no_texto

        texto = (
            "PODER JUDICIÁRIO JUSTIÇA DO TRABALHO TRIBUNAL REGIONAL DO TRABALHO DA 2ª REGIÃO "
            "ATSum 1000940-20.2025.5.02.0703 "
            "RECLAMANTE: NAILMA ARAUJO DOS SANTOS "
            "RECLAMADO: M S DANTAS INFORMATICA E IDIOMAS E OUTROS (1) "
            "DECISÃO: defiro a instauração do Incidente de Desconsideração da Personalidade Jurídica (IDPJ). "
            "Providencie a Secretaria da Vara retificação da autuação no sistema, para incluir o sócio "
            "MARCELO SATURNINO DANTAS, CPF: 087.608.508-76 na autuação. "
            "Uma vez que o(s) suscitado(s) pode(m) se desfazer de seus patrimônios... concedo a tutela."
        )
        reus = [
            {'nome': 'M S DANTAS INFORMATICA E IDIOMAS', 'cpfcnpj': '22.600.542/0001-38'},
            {'nome': 'MARCELO SATURNINO DANTAS', 'cpfcnpj': '087.608.508-76'}
        ]

        # Em informado decisao, padrao_proximidade é None
        encontrados = _extrair_reus_mencionados_no_texto(texto, reus, padrao_proximidade=None)
        nomes_encontrados = [e['nome_oficial'] for e in encontrados]

        self.assertEqual(len(encontrados), 1)
        self.assertIn('MARCELO SATURNINO DANTAS', nomes_encontrados)
        self.assertNotIn('M S DANTAS INFORMATICA E IDIOMAS', nomes_encontrados)
        self.assertEqual(encontrados[0]['documento'], '087.608.508-76')


if __name__ == '__main__':
    unittest.main()

