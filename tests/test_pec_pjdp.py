# -*- coding: utf-8 -*-
"""
tests/test_pec_pjdp.py -- Testes unitários para detecção e inserção de PJDP em pec_ord/pec_sum/pec_ordv/pec_sumv.
"""

import unittest
from unittest.mock import MagicMock, patch

from atos.comunicacao_destinatarios import (
    PJDP_NOME_KEYWORDS,
    detectar_pjdp_processo,
    inserir_destinatarios_pjdp,
)
from atos import wrappers_pec as w


class TestPecPJDP(unittest.TestCase):
    """Testes para o suporte a PJDP em comunicações de Notificação Inicial."""

    def test_wrappers_possuem_atributo_pjdp(self):
        """Verifica se pec_ord, pec_sum, pec_ordv e pec_sumv possuem o atributo pjdp=False."""
        for wrapper_name in ('pec_ord', 'pec_sum', 'pec_ordv', 'pec_sumv'):
            wrapper = getattr(w, wrapper_name, None)
            self.assertIsNotNone(wrapper, f"Wrapper {wrapper_name} não encontrado em wrappers_pec")
            self.assertTrue(hasattr(wrapper, 'pjdp'), f"{wrapper_name} deve ter atributo 'pjdp'")
            self.assertFalse(wrapper.pjdp, f"{wrapper_name}.pjdp deve ser False por padrão")

    def test_outros_wrappers_nao_possuem_pjdp(self):
        """Verifica que outros wrappers PEC não possuem pjdp ativo nem como default."""
        outros = ['pec_decisao', 'pec_exeq', 'pec_idpj', 'pec_arord', 'pec_arsum', 'pec_arordv', 'pec_arsumv', 'pec_cpgeral']
        for wrapper_name in outros:
            wrapper = getattr(w, wrapper_name, None)
            if wrapper is not None:
                self.assertFalse(getattr(wrapper, 'pjdp', False), f"{wrapper_name} não deve ter pjdp=True")

    def test_outro_wrapper_ignora_flag_pjdp(self):
        """Qualquer wrapper fora dos 4 permitidos bloqueia rigorosamente a ativação de pjdp."""
        from atos.comunicacao import make_comunicacao_wrapper

        mock_driver = MagicMock()
        setattr(mock_driver, 'window_handles', ['h1'])
        mock_driver.current_window_handle = 'h1'

        wrapper_teste = make_comunicacao_wrapper(
            tipo_expediente='Intimação',
            prazo=5,
            nome_comunicacao='Teste Outro',
            sigilo=False,
            modelo_nome='teste',
            subtipo="Intimação",
            wrapper_name='pec_outro'
        )

        with patch('atos.comunicacao.abrir_minutas', return_value=True), \
             patch('atos.comunicacao.executar_preenchimento_minuta'), \
             patch('atos.comunicacao.selecionar_destinatarios'), \
             patch('atos.comunicacao.remover_destinatarios_endereco_invalido'), \
             patch('atos.comunicacao.contar_linhas_destinatarios', return_value=1), \
             patch('atos.comunicacao.salvar_minuta_final', return_value=True), \
             patch('atos.comunicacao.inserir_destinatarios_pjdp') as mock_inserir_pjdp:

            # Mesmo passando pjdp=True explicitamente, deve ser ignorado para pec_outro
            wrapper_teste(mock_driver, pjdp=True)
            mock_inserir_pjdp.assert_not_called()

    def test_detectar_pjdp_processo_criterio_procuradoria_positivo(self):
        """detectar_pjdp_processo identifica PJDP via campo 'procuradoria' da API."""
        driver_mock = MagicMock()
        driver_mock.current_url = "https://pje.trt2.jus.br/pjekz/processo/12345/detalhe"

        mock_client = MagicMock()
        mock_client.partes.return_value = {
            'ATIVO': [{'nome': 'JOAO DA SILVA'}],
            'PASSIVO': [
                {'nome': 'EMPRESA PUBLICA X', 'procuradoria': {'id': 10, 'nome': 'Procuradoria X'}},
                {'nome': 'EMPRESA PRIVADA LTDA', 'procuradoria': None},
            ]
        }

        with patch('Fix.core.extrair_id_processo', return_value='12345'), \
             patch('Fix.variaveis.cliente_para', return_value=mock_client):
            self.assertTrue(detectar_pjdp_processo(driver_mock))

    def test_detectar_pjdp_processo_criterio_procuradoria_evita_falso_positivo(self):
        """detectar_pjdp_processo evita falso positivo por nome se a API trouxe procuradoria=None."""
        driver_mock = MagicMock()
        driver_mock.current_url = "https://pje.trt2.jus.br/pjekz/processo/12345/detalhe"

        mock_client = MagicMock()
        mock_client.partes.return_value = {
            'ATIVO': [{'nome': 'JOAO DA SILVA'}],
            'PASSIVO': [
                # Tem 'municipio' no nome, mas como a API informou procuradoria=None, não é PJDP
                {'nome': 'AUTO POSTO MUNICIPIO LTDA', 'procuradoria': None},
            ]
        }

        with patch('Fix.core.extrair_id_processo', return_value='12345'), \
             patch('Fix.variaveis.cliente_para', return_value=mock_client):
            self.assertFalse(detectar_pjdp_processo(driver_mock))

    def test_detectar_pjdp_processo_positivo_por_nome(self):
        """detectar_pjdp_processo identifica réu no polo passivo com nome PJDP (ex: Correios)."""
        driver_mock = MagicMock()
        driver_mock.current_url = "https://pje.trt2.jus.br/pjekz/processo/12345/detalhe"

        mock_client = MagicMock()
        mock_client.partes.return_value = {
            'ATIVO': [{'nome': 'JOAO DA SILVA'}],
            'PASSIVO': [
                {'nome': 'EMPRESA BRASILEIRA DE CORREIOS E TELEGRAFOS', 'poloProcessual': 'PASSIVO'},
                {'nome': 'EMPRESA PRIVADA LTDA', 'poloProcessual': 'PASSIVO'},
            ]
        }

        with patch('Fix.core.extrair_id_processo', return_value='12345'), \
             patch('Fix.variaveis.cliente_para', return_value=mock_client):
            self.assertTrue(detectar_pjdp_processo(driver_mock))

    def test_detectar_pjdp_processo_negativo_empresa_privada(self):
        """detectar_pjdp_processo retorna False se nenhuma parte for PJDP."""
        driver_mock = MagicMock()
        driver_mock.current_url = "https://pje.trt2.jus.br/pjekz/processo/12345/detalhe"

        mock_client = MagicMock()
        mock_client.partes.return_value = [
            {'nome': 'JOAO DA SILVA', 'poloProcessual': 'ATIVO'},
            {'nome': 'EMPRESA PRIVADA LTDA', 'poloProcessual': 'PASSIVO'},
            {'nome': 'COMERCIO DE ALIMENTOS ME', 'poloProcessual': 'PASSIVO'},
        ]

        with patch('Fix.core.extrair_id_processo', return_value='12345'), \
             patch('Fix.variaveis.cliente_para', return_value=mock_client):
            self.assertFalse(detectar_pjdp_processo(driver_mock))

    def test_regras_execucao_xs_ord_passa_pjdp_quando_detectada(self):
        """_xs_ord detecta PJDP e repassa pjdp=True para pec_ord."""
        from PEC import regras_execucao

        driver_mock = MagicMock()
        driver_mock.current_url = "https://pje.trt2.jus.br/pjekz/processo/999/detalhe"

        with patch('atos.comunicacao_destinatarios.detectar_pjdp_processo', return_value=True), \
             patch('Fix.core.extrair_id_processo', return_value='999'), \
             patch('Fix.variaveis.cliente_para') as mock_cp, \
             patch('atos.wrappers_pec.pec_ord') as mock_pec_ord, \
             patch('atos.wrappers_mov.mov_aud', return_value=True):

            client_mock = MagicMock()
            client_mock.partes.return_value = [{'poloProcessual': 'passivo', 'id': '10'}]
            client_mock.domicilio_eletronico.return_value = True
            mock_cp.return_value = client_mock

            regras_execucao._xs_ord(driver_mock, MagicMock())

            mock_pec_ord.assert_called_with(driver_mock, pjdp=True)

    def test_regras_execucao_xs_sum_passa_pjdp_quando_detectada(self):
        """_xs_sum detecta PJDP e repassa pjdp=True para pec_sum."""
        from PEC import regras_execucao

        driver_mock = MagicMock()
        driver_mock.current_url = "https://pje.trt2.jus.br/pjekz/processo/999/detalhe"

        with patch('atos.comunicacao_destinatarios.detectar_pjdp_processo', return_value=True), \
             patch('Fix.core.extrair_id_processo', return_value='999'), \
             patch('Fix.variaveis.cliente_para') as mock_cp, \
             patch('atos.wrappers_pec.pec_sum') as mock_pec_sum, \
             patch('atos.wrappers_mov.mov_aud', return_value=True):

            client_mock = MagicMock()
            client_mock.partes.return_value = [{'poloProcessual': 'passivo', 'id': '10'}]
            client_mock.domicilio_eletronico.return_value = True
            mock_cp.return_value = client_mock

            regras_execucao._xs_sum(driver_mock, MagicMock())

            mock_pec_sum.assert_called_with(driver_mock, pjdp=True)

    def test_regras_execucao_xs_ordv_passa_pjdp_quando_detectada(self):
        """_xs_ordv detecta PJDP e repassa pjdp=True para pec_ordv."""
        from PEC import regras_execucao

        driver_mock = MagicMock()

        with patch('atos.comunicacao_destinatarios.detectar_pjdp_processo', return_value=True), \
             patch('atos.wrappers_pec.pec_ordv') as mock_pec_ordv:

            regras_execucao._xs_ordv(driver_mock)

            mock_pec_ordv.assert_called_once_with(driver_mock, pjdp=True)

    def test_regras_execucao_xs_sumv_passa_pjdp_quando_detectada(self):
        """_xs_sumv detecta PJDP e repassa pjdp=True para pec_sumv."""
        from PEC import regras_execucao

        driver_mock = MagicMock()

        with patch('atos.comunicacao_destinatarios.detectar_pjdp_processo', return_value=True), \
             patch('atos.wrappers_pec.pec_sumv') as mock_pec_sumv:

            regras_execucao._xs_sumv(driver_mock)

            mock_pec_sumv.assert_called_once_with(driver_mock, pjdp=True)

    def test_inserir_destinatarios_pjdp_identifica_e_clica_seta(self):
        """inserir_destinatarios_pjdp localiza linha com fas fa-building e clica no botão acrescentar."""
        driver_mock = MagicMock()

        # Mock da linha li.partes-corpo
        linha_pjdp = MagicMock()
        # Indicador de PJDP: i.fas.fa-building
        indicador_pjdp = MagicMock()
        # Nome da parte
        span_nome = MagicMock()
        span_nome.text_content.return_value = "EMPRESA BRASILEIRA DE CORREIOS E TELEGRAFOS"

        def sub_side_effect(elem, seletor):
            if elem == linha_pjdp:
                if 'fa-building' in seletor or 'órgão público' in seletor:
                    return indicador_pjdp
                if 'nome-parte' in seletor:
                    return span_nome
            return None

        with patch('atos.comunicacao_destinatarios._clicar_polo_passivo', return_value=True), \
             patch('Fix.espera.elementos', side_effect=lambda d, sel, **kwargs: [linha_pjdp] if 'partes-corpo' in sel else []), \
             patch('Fix.browser_suporte._sub_elemento', side_effect=sub_side_effect), \
             patch('atos.comunicacao_destinatarios._clicar_btn_acrescentar', return_value=True) as mock_clicar, \
             patch('Fix.espera.assentar'), \
             patch('Fix.espera.pausa'), \
             patch('Fix.core.aguardar_renderizacao_nativa'):

            adicionados = inserir_destinatarios_pjdp(driver_mock)
            self.assertEqual(adicionados, 1)
            mock_clicar.assert_called_once_with(driver_mock, linha_pjdp, qtd_cliques=1, debug=False)


if __name__ == '__main__':
    unittest.main()
