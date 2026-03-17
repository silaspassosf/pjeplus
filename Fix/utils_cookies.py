import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_cookies - Módulo de gerenciamento de cookies para PJe automação.

Parte da refatoração do Fix.utils.py para melhor granularidade IA.
"""

import json
import os
import time
import glob
from datetime import datetime, timedelta

# Configurações de cookies
USAR_COOKIES_AUTOMATICO = True
SALVAR_COOKIES_AUTOMATICO = USAR_COOKIES_AUTOMATICO
COOKIES_DIR = r"D:\PjePlus\___001\cookies_sessoes"

def carregar_cookies_sessao(driver, max_idade_horas=24):
    """Carrega o arquivo mais recente de cookies e valida se ainda e valido."""
    try:
        if not os.path.exists(COOKIES_DIR):
            os.makedirs(COOKIES_DIR)
            return False

        arquivos_cookies = glob.glob(os.path.join(COOKIES_DIR, 'cookies_sessao*.json'))
        if not arquivos_cookies:
            logger.info('[COOKIES] Nenhum arquivo de cookies encontrado.')
            return False

        arquivo_mais_recente = max(arquivos_cookies, key=os.path.getmtime)
        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        if isinstance(dados, dict) and 'timestamp' in dados:
            timestamp_str = dados.get('timestamp')
            cookies = dados.get('cookies', [])
        else:
            timestamp_str = datetime.fromtimestamp(os.path.getmtime(arquivo_mais_recente)).isoformat()
            cookies = dados

        timestamp_cookies = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+00:00', ''))
        idade = datetime.now() - timestamp_cookies

        if idade > timedelta(hours=max_idade_horas):
            logger.info(f"[COOKIES] Cookies muito antigos ({idade.total_seconds()/3600:.1f}h).")
            return False

        # Navegar para o dominio antes de aplicar cookies
        driver.get('https://pje.trt2.jus.br/primeirograu/')

        cookies_carregados = 0
        for cookie in cookies:
            try:
                cookie_limpo = {k: v for k, v in cookie.items() if k not in ['expiry', 'httpOnly', 'secure', 'sameSite']}
                driver.add_cookie(cookie_limpo)
                cookies_carregados += 1
            except Exception as e:
                logger.warning(f"[COOKIES] Erro ao carregar cookie {cookie.get('name', 'unknown')}: {e}")

        logger.info(f"[COOKIES] {cookies_carregados} cookies carregados de {os.path.basename(arquivo_mais_recente)}")

        # Testar cookies em pagina protegida.
        # Usa page_load_timeout curto para retornar assim que o redirect acontecer,
        # sem esperar o Angular SPA terminar de renderizar (~60s).
        timeout_original = driver.timeouts.page_load
        try:
            driver.set_page_load_timeout(8)
            driver.get('https://pje.trt2.jus.br/pjekz/gigs/meu-painel')
        except Exception:
            pass  # TimeoutException esperada — URL ja reflete o redirect
        finally:
            try:
                driver.set_page_load_timeout(timeout_original)
            except Exception:
                pass

        if 'acesso-negado' in driver.current_url.lower():
            logger.warning('[COOKIES] Acesso negado apos aplicar cookies; limpando cookies.')
            try:
                driver.delete_all_cookies()
            except Exception as e:
                logger.warning(f"[COOKIES] Erro ao apagar cookies: {e}")
            return False

        if 'login' in driver.current_url.lower():
            logger.info('[COOKIES] Cookies invalidos - redirecionado para login.')
            return False

        logger.info('[COOKIES] Cookies validos - login automatico realizado.')
        return True

    except Exception as e:
        logger.error(f"[COOKIES][ERRO] Falha ao carregar cookies: {e}")
        return False


def verificar_e_aplicar_cookies(driver):
    """Verifica e aplica cookies automaticamente. Retorna True se login via cookies funcionar."""
    if not USAR_COOKIES_AUTOMATICO:
        return False

    logger.info('[COOKIES] Tentando login automatico via cookies salvos...')
    return carregar_cookies_sessao(driver)

def salvar_cookies_sessao(driver, info_extra=''):
    """Salva os cookies da sessão atual"""
    try:
        if not os.path.exists(COOKIES_DIR):
            os.makedirs(COOKIES_DIR)

        cookies = driver.get_cookies()
        if not cookies:
            logger.warning("Nenhum cookie para salvar")
            return False

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"cookies_sessao_{info_extra}_{timestamp}.json" if info_extra else f"cookies_sessao_{timestamp}.json"
        caminho_arquivo = os.path.join(COOKIES_DIR, nome_arquivo)

        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        logger.info(f"Cookies salvos em: {nome_arquivo}")
        return True

    except Exception as e:
        logger.error(f"Erro ao salvar cookies: {e}")
        return False

def limpar_cookies_antigos(dias_manter=7):
    """Remove arquivos de cookies mais antigos que X dias"""
    try:
        if not os.path.exists(COOKIES_DIR):
            return

        agora = time.time()
        limite = agora - (dias_manter * 24 * 60 * 60)

        for arquivo in os.listdir(COOKIES_DIR):
            if arquivo.startswith('cookies_sessao_') and arquivo.endswith('.json'):
                caminho = os.path.join(COOKIES_DIR, arquivo)
                if os.path.getmtime(caminho) < limite:
                    os.remove(caminho)
                    logger.info(f"Cookie antigo removido: {arquivo}")

    except Exception as e:
        logger.error(f"Erro ao limpar cookies antigos: {e}")

def listar_cookies_salvos():
    """Retorna lista de arquivos de cookies salvos"""
    try:
        if not os.path.exists(COOKIES_DIR):
            return []

        arquivos = [f for f in os.listdir(COOKIES_DIR) if f.startswith('cookies_sessao_') and f.endswith('.json')]
        return sorted(arquivos, key=lambda x: os.path.getmtime(os.path.join(COOKIES_DIR, x)), reverse=True)

    except Exception as e:
        logger.error(f"Erro ao listar cookies salvos: {e}")
        return []

class SimpleConfig:
    """Classe de configuração simples para controle de delays e estatísticas"""
    def __init__(self):
        self.stats = {'consecutive_errors': 0, 'total_actions': 0, 'rate_limit_detected': False}
        self.delays = {
            'default': 0.3,
            'click': 0.3,
            'navigation': 0.6,
            'form_fill': 0.8,
            'api_call': 1.0,
            'page_load': 2.0,
            'retry_base': 1.5,
        }

    def get_delay(self, t='default'):
        base = self.delays.get(t, 0.6)
        if self.stats['rate_limit_detected']:
            return base * 5.0
        elif self.stats['consecutive_errors'] > 5:
            return base * 3.0
        elif self.stats['consecutive_errors'] > 2:
            return base * 2.0
        return base

# Instância global de configuração
config = SimpleConfig()