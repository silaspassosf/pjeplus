"""
Testes unitários para autenticação e detecção de tela de login no SISBAJUD (SISB/core.py).
Valida que:
1. is_tela_login_sisbajud identifica Keycloak SSO, formulário e landing pages não autenticadas.
2. is_sessao_ativa_sisbajud exige prova positiva (JWT válido ou componentes Angular autenticados)
   e NUNCA deduz login por mera ausência de 'login' na URL.
3. carregar_cookies_sisbajud rejeita arquivos com tokens expirados ou quando a sessão não fica ativa.
"""
import unittest
from unittest.mock import MagicMock, patch
import time
import json


class TestSisbajudAutenticacao(unittest.TestCase):

    def test_is_tela_login_por_url_sso(self):
        """URL do Keycloak SSO deve ser identificada como tela de login."""
        from SISB.core import is_tela_login_sisbajud

        driver = MagicMock()
        driver.current_url = 'https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?client_id=sisbajud'
        self.assertTrue(is_tela_login_sisbajud(driver))

    def test_is_tela_login_por_elementos_dom(self):
        """Presença de #username ou #kc-login no DOM deve ser identificada como tela de login."""
        from SISB.core import is_tela_login_sisbajud

        driver = MagicMock()
        driver.current_url = 'https://sisbajud.pdpj.jus.br/'
        with patch('Fix.espera.ate_aparecer', return_value=True):
            self.assertTrue(is_tela_login_sisbajud(driver))

    def test_is_tela_login_falso_quando_logado(self):
        """Página interna do SISBAJUD sem elementos de login deve retornar False."""
        from SISB.core import is_tela_login_sisbajud

        driver = MagicMock()
        driver.current_url = 'https://sisbajud.pdpj.jus.br/teimosinha'
        driver.execute_script.return_value = False
        with patch('Fix.espera.ate_aparecer', return_value=False):
            self.assertFalse(is_tela_login_sisbajud(driver))

    def test_is_sessao_ativa_falso_se_tela_login(self):
        """Se estiver na tela de login, sessão ativa NUNCA deve ser True."""
        from SISB.core import is_sessao_ativa_sisbajud

        driver = MagicMock()
        driver.current_url = 'https://sso.cloud.pje.jus.br/auth/realms/pje/'
        self.assertFalse(is_sessao_ativa_sisbajud(driver))

    def test_is_sessao_ativa_falso_se_apenas_url_sisbajud(self):
        """URL contendo 'sisbajud' sem token válido ou componentes Angular NÃO é sessão ativa."""
        from SISB.core import is_sessao_ativa_sisbajud

        driver = MagicMock()
        driver.current_url = 'https://sisbajud.pdpj.jus.br/'
        driver.execute_script.return_value = False  # token inválido ou ausente
        with patch('Fix.espera.ate_aparecer', return_value=False):
            self.assertFalse(is_sessao_ativa_sisbajud(driver))

    def test_is_sessao_ativa_verdadeiro_com_token_jwt_valido(self):
        """Sessão é ativa quando há JWT válido no localStorage com exp futuro."""
        from SISB.core import is_sessao_ativa_sisbajud

        driver = MagicMock()
        driver.current_url = 'https://sisbajud.pdpj.jus.br/'

        def mock_exec(script, *args):
            if 'localStorage' in script:
                return True
            return False

        driver.execute_script.side_effect = mock_exec
        with patch('Fix.espera.ate_aparecer', return_value=False):
            self.assertTrue(is_sessao_ativa_sisbajud(driver))

    def test_is_sessao_ativa_verdadeiro_com_componentes_angular_autenticados(self):
        """Sessão é ativa quando componentes Angular autenticados estão no DOM."""
        from SISB.core import is_sessao_ativa_sisbajud

        driver = MagicMock()
        driver.current_url = 'https://sisbajud.pdpj.jus.br/minuta/cadastrar'
        driver.execute_script.return_value = False
        # Mock ate_aparecer retornando True para seletor autenticado
        with patch('Fix.espera.ate_aparecer', side_effect=lambda d, sel, teto=0.5: 'sisbajud-cadastro-minuta' in sel):
            self.assertTrue(is_sessao_ativa_sisbajud(driver))

    def test_carregar_cookies_rejeita_token_expirado_no_arquivo(self):
        """Arquivo com JWT expirado deve ser rejeitado sem injetar."""
        from SISB.core import carregar_cookies_sisbajud

        driver = MagicMock()
        # JWT expirado (exp no passado: 100000)
        jwt_expirado = "header.eyJleHAiOjEwMDAwMH0.signature"
        mock_dados = {
            'timestamp': '2026-10-22T01:00:00',
            'cookies': [{'name': 'c1', 'value': 'v1'}],
            'origins': [{
                'origin': 'https://sisbajud.cnj.jus.br',
                'localStorage': [{'name': 'sisbajud-token', 'value': jwt_expirado}]
            }]
        }
        with patch('os.path.exists', return_value=True), \
             patch('glob.glob', return_value=['cookies_sessoes/cookies_sisbajud_teste.json']), \
             patch('os.path.getmtime', return_value=time.time()), \
             patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(mock_dados))):
            resultado = carregar_cookies_sisbajud(driver, max_idade_horas=12)
            self.assertFalse(resultado)

    def test_carregar_cookies_rejeita_se_sessao_nao_ficar_ativa(self):
        """Se após injetar cookies a sessão não for confirmada ativa, descarta e retorna False."""
        from SISB.core import carregar_cookies_sisbajud

        driver = MagicMock()
        driver.current_url = 'https://sisbajud.pdpj.jus.br/'
        mock_dados = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'cookies': [{'name': 'c1', 'value': 'v1', 'expires': time.time() + 3600}],
            'origins': []
        }
        with patch('os.path.exists', return_value=True), \
             patch('glob.glob', return_value=['cookies_sessoes/cookies_sisbajud_teste.json']), \
             patch('os.path.getmtime', return_value=time.time()), \
             patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(mock_dados))), \
             patch('SISB.core.is_sessao_ativa_sisbajud', return_value=False), \
             patch('SISB.core.is_tela_login_sisbajud', return_value=True):
            resultado = carregar_cookies_sisbajud(driver, max_idade_horas=12)
            self.assertFalse(resultado)
            driver.delete_all_cookies.assert_called_once()


if __name__ == '__main__':
    unittest.main()
