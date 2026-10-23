import logging
logger = logging.getLogger(__name__)

"""
SISB/core.py - Módulo Core do SISBAJUD

Este módulo contém as funções essenciais para inicialização e autenticação no SISBAJUD:
- driver_sisbajud(): Cria driver Firefox configurado para SISBAJUD
- login_automatico_sisbajud(): Login automatizado com simulação humana
- login_manual_sisbajud(): Login manual aguardando usuário
- salvar_dados_processo_temp(): Salva dados temporários do processo
- iniciar_sisbajud(): Função unificada de inicialização completa

E as funções orquestradoras principais:
- minuta_bloqueio(): Orquestra criação de minuta de bloqueio
- processar_ordem_sisbajud(): Orquestra processamento de ordens
- processar_bloqueios(): Orquestra processamento de bloqueios
- processar_endereco(): Orquestra processamento de endereços

Criado durante refatoração modular do sisb.py (275KB → 4 módulos)
"""

import os
import json
import time
import random
import base64
import unicodedata
from datetime import datetime, timedelta

# Imports do projeto
from Fix.driver_factory import criar_driver_sisb_pc as criar_driver_sisb  # referência canônica
from Fix.driver_factory import criar_driver_sisb_vt  # referência canônica
from . import helpers
# Importar função diretamente do módulo de campos para evitar depender
# do namespace `processamento` em tempo de execução.
from .processamento_campos import _configurar_valor
from . import utils
from Fix import espera
from Fix.core import aguardar_renderizacao_nativa, preencher_campo, safe_click_no_scroll

# Função auxiliar para simulação humana (extraída de sisb.py)
def simular_movimento_humano(driver, elemento=None):
    """
    Simula movimento de mouse humano antes de clicar em elemento
    """
    try:
        if hasattr(driver, 'page') and hasattr(driver.page, 'mouse'):
            driver.page.mouse.move(random.randint(100, 700), random.randint(100, 500))
    except Exception as e:
        _ = e

# Variável global para armazenar dados do processo
processo_dados_extraidos = None


# ═══════════════════════════════════════════════════════════════════════════
# Token Storage: SISBAJUD (localStorage) - Reutilização de sessão
# ═══════════════════════════════════════════════════════════════════════════

def _extrair_jwt_exp_sisbajud(token_value: str) -> int:
    """Extrai campo 'exp' do JWT SISBAJUD.
    
    JWT formato: header.payload.signature
    payload é Base64URL encoded.
    """
    try:
        partes = token_value.split('.')
        if len(partes) < 2:
            return 0
        payload_b64 = partes[1]
        # Base64URL decode: substitui -_ para +/, adiciona padding
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
        payload_dict = json.loads(payload_json)
        return int(payload_dict.get('exp', 0))
    except Exception as e:
        logger.debug(f'[SISBAJUD][TOKEN] Erro ao extrair exp: {e}')
        return 0


def salvar_tokens_sisbajud(driver) -> bool:
    """Salva tokens SISBAJUD do localStorage para arquivo JSON.
    
    Extracts: sisbajud-token (access_token), sisbajud-refresh-token
    Saves to: ~/.pjeplus/sisbajud_tokens.json com expiry de access_token
    """
    try:
        # Leitura de localStorage via JavaScript (suporta formato com ou sem prefixo LS.)
        access_token = driver.execute_script(
            "return localStorage.getItem('sisbajud-token') || localStorage.getItem('LS.sisbajud-token');"
        )
        refresh_token = driver.execute_script(
            "return localStorage.getItem('sisbajud-refresh-token') || localStorage.getItem('LS.sisbajud-refresh-token');"
        )
        
        if not access_token:
            logger.debug('[SISBAJUD][TOKEN] Nenhum access_token encontrado em localStorage')
            return False
        
        # Extrair expiry do JWT
        access_token_exp = _extrair_jwt_exp_sisbajud(access_token)
        if access_token_exp <= 0:
            logger.warning('[SISBAJUD][TOKEN] Nao consegui extrair exp do access_token')
            return False
        
        # Preparar caminho do arquivo
        home = os.path.expanduser('~')
        config_dir = os.path.join(home, '.pjeplus')
        os.makedirs(config_dir, exist_ok=True)
        token_file = os.path.join(config_dir, 'sisbajud_tokens.json')
        
        # Salvar
        dados = {
            'access_token': access_token,
            'access_token_exp': access_token_exp,
            'refresh_token': refresh_token or None,
            'salvo_em': time.time(),
        }
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        
        logger.info(f'[SISBAJUD][TOKEN] Tokens salvos em {token_file}')
        return True
    except Exception as e:
        logger.warning(f'[SISBAJUD][TOKEN] Erro ao salvar tokens: {e}')
        return False


def carregar_tokens_sisbajud() -> dict:
    """Carrega e valida tokens SISBAJUD salvos.
    
    Retorna: {'sucesso': bool, 'access_token': str|None, 'refresh_token': str|None}
    Valida: exp - time.time() < 60s → rejeitado se expirado em < 60s
    """
    try:
        home = os.path.expanduser('~')
        token_file = os.path.join(home, '.pjeplus', 'sisbajud_tokens.json')
        
        if not os.path.exists(token_file):
            logger.debug('[SISBAJUD][TOKEN] Arquivo de tokens nao encontrado')
            return {'sucesso': False, 'access_token': None, 'refresh_token': None}
        
        with open(token_file, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        access_token = dados.get('access_token')
        refresh_token = dados.get('refresh_token')
        access_token_exp = dados.get('access_token_exp', 0)
        
        # Validar expiry
        agora = time.time()
        tempo_ate_expiry = access_token_exp - agora
        
        if tempo_ate_expiry < 60:
            logger.info(f'[SISBAJUD][TOKEN] Token expirado ou expira em {tempo_ate_expiry:.0f}s (<60s) — rejeitado')
            return {'sucesso': False, 'access_token': None, 'refresh_token': None}
        
        logger.info(f'[SISBAJUD][TOKEN] Token carregado — expira em {tempo_ate_expiry:.0f}s')
        return {'sucesso': True, 'access_token': access_token, 'refresh_token': refresh_token}
    except Exception as e:
        logger.warning(f'[SISBAJUD][TOKEN] Erro ao carregar tokens: {e}')
        return {'sucesso': False, 'access_token': None, 'refresh_token': None}


def injetar_tokens_sisbajud(driver, access_token: str, refresh_token: str = None) -> bool:
    """Injeta tokens SISBAJUD em localStorage do driver.
    
    Aplica em https://sisbajud.cnj.jus.br/ e https://sisbajud.pdpj.jus.br/.
    """
    try:
        for dom in ['https://sisbajud.cnj.jus.br/', 'https://sisbajud.pdpj.jus.br/']:
            try:
                driver.get(dom)
                espera.assentar(driver, 0.5)
                driver.execute_script("""
                    localStorage.setItem('sisbajud-token', arguments[0]);
                    localStorage.setItem('LS.sisbajud-token', arguments[0]);
                    if (arguments[1]) {
                        localStorage.setItem('sisbajud-refresh-token', arguments[1]);
                        localStorage.setItem('LS.sisbajud-refresh-token', arguments[1]);
                    }
                """, access_token, refresh_token)
            except Exception:
                pass
        
        logger.info('[SISBAJUD][TOKEN] Tokens injetados em localStorage')
        return True
    except Exception as e:
        logger.warning(f'[SISBAJUD][TOKEN] Erro ao injetar tokens: {e}')
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Verificação de Autenticação e Sessão SISBAJUD
# ═══════════════════════════════════════════════════════════════════════════

def is_tela_login_sisbajud(driver) -> bool:
    """
    Identifica de forma conclusiva se o driver SISBAJUD está na tela de login
    (Keycloak SSO PDPJ, formulário de credenciais, OTP ou página de autenticação).
    NUNCA deduz que está logado só pela URL.
    """
    try:
        cur_url = (getattr(driver, 'current_url', '') or '').lower()

        # 1. URL explícita de autenticação / SSO / Keycloak / login
        indicadores_url_login = (
            'sso.cloud.pje.jus.br',
            '/auth/realms/',
            'protocol/openid-connect',
            '/login',
            '/autenticacao',
            'auth_session_id',
        )
        if any(ind in cur_url for ind in indicadores_url_login):
            return True

        # 2. Elementos DOM de formulário de login / SSO
        seletores_login = (
            '#username, input[name="username"], '
            '#password, input[name="password"], '
            '#kc-login, #kc-form-login, #kc-page-title, '
            '#otp, input[name="otp"], '
            'form[action*="/auth/realms/"]'
        )
        if espera.ate_aparecer(driver, seletores_login, teto=0.5):
            return True

        # 3. Botão ou link explícito de chamada para login em landing page
        try:
            is_landing_login = driver.execute_script("""
                const botoes = Array.from(document.querySelectorAll('button, a, .btn'));
                return botoes.some(b => {
                    const txt = (b.textContent || '').trim().toLowerCase();
                    return (
                        txt === 'entrar' ||
                        txt.includes('entrar com') ||
                        txt.includes('login') ||
                        txt === 'acessar' ||
                        txt.includes('autenticar')
                    ) && b.offsetParent !== null;
                });
            """)
            if is_landing_login:
                return True
        except Exception:
            pass

        return False
    except Exception as e:
        logger.debug(f'[SISBAJUD][LOGIN_CHECK] Erro ao checar tela de login: {e}')
        return False


def is_sessao_ativa_sisbajud(driver) -> bool:
    """
    Verifica se há uma sessão autenticada REAL e ATIVA no SISBAJUD.
    Critérios estritos:
    1. Se estiver na tela de login (is_tela_login_sisbajud), retorna False imediatamente.
    2. URL deve ser de domínio do SISBAJUD (sisbajud.cnj.jus.br ou sisbajud.pdpj.jus.br).
    3. Prova positiva 1: JWT token válido no localStorage (exp > agora + 15s).
    4. Prova positiva 2: Componentes Angular autenticados no DOM (dialog de ordens, menus internos, toolbar autenticada).
    NUNCA assume que está logado apenas porque a URL tem 'sisbajud' e não tem 'login'.
    """
    try:
        if is_tela_login_sisbajud(driver):
            return False

        cur_url = (getattr(driver, 'current_url', '') or '').lower()
        if not any(h in cur_url for h in ['sisbajud.cnj.jus.br', 'sisbajud.pdpj.jus.br']):
            return False

        # Prova Positiva A: Token JWT válido no localStorage
        try:
            token_valido = driver.execute_script("""
                try {
                    const token = localStorage.getItem('sisbajud-token') || localStorage.getItem('LS.sisbajud-token');
                    if (!token) return false;
                    const partes = token.split('.');
                    if (partes.length < 2) return false;
                    const payload = JSON.parse(atob(partes[1].replace(/-/g, '+').replace(/_/g, '/')));
                    const exp = payload.exp || 0;
                    return exp > ((Date.now() / 1000) + 15);
                } catch(e) {
                    return false;
                }
            """)
            if token_valido:
                return True
        except Exception:
            pass

        # Prova Positiva B: Elementos do sistema autenticado no DOM
        seletores_autenticado = (
            'sisbajud-dialog-aviso-ordem-pendente, '
            'sisbajud-cadastro-minuta, '
            'sisbajud-detalhes-teimosinha, '
            'a[href*="/minuta"], a[routerlink*="/minuta"], '
            'a[href*="/teimosinha"], a[routerlink*="/teimosinha"], '
            'button[mat-menu-item]'
        )
        if espera.ate_aparecer(driver, seletores_autenticado, teto=0.5):
            return True

        return False
    except Exception as e:
        logger.debug(f'[SISBAJUD][SESSION_CHECK] Erro ao checar sessão ativa: {e}')
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Sessão / Cookies SISBAJUD — evita novo OTP entre execuções
# Padrão idêntico ao driver PJe (cookies_sessoes/ + storage_state)
# ═══════════════════════════════════════════════════════════════════════════

USAR_COOKIES_AUTOMATICO = True
SALVAR_COOKIES_AUTOMATICO = True


def _arquivo_sessao_sisbajud() -> str:
    config_dir = os.path.join(os.path.expanduser('~'), '.pjeplus')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'sisbajud_sessao.json')


def salvar_cookies_sisbajud(driver, caminho_arquivo=None, info_extra=None) -> bool:
    """
    Salva todos os cookies e localStorage da sessão SISBAJUD em arquivo JSON.
    Mesmo padrão de salvar_cookies_sessao do driver PJe.
    """
    try:
        cookies = []
        if hasattr(driver, 'get_cookies'):
            try:
                cookies = driver.get_cookies()
            except Exception:
                pass
        contexto = getattr(driver, '_context', None)
        estado = {}
        if contexto and hasattr(contexto, 'storage_state'):
            try:
                estado = contexto.storage_state()
            except Exception:
                pass

        if not cookies and not estado.get('cookies'):
            logger.debug('[SISBAJUD][COOKIES] Nenhum cookie encontrado para salvar')
            return False

        pasta = os.path.join(os.getcwd(), 'cookies_sessoes')
        os.makedirs(pasta, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        info = f'_{info_extra}' if info_extra else ''
        if not caminho_arquivo:
            caminho_arquivo = os.path.join(pasta, f'cookies_sisbajud{info}_{timestamp}.json')

        dados = {
            'timestamp': datetime.now().isoformat(),
            'url_base': getattr(driver, 'current_url', 'https://sisbajud.pdpj.jus.br/'),
            'cookies': cookies or estado.get('cookies', []),
            'origins': estado.get('origins', [])
        }

        # Garantir persistência dos tokens em origins se storage_state não os incluiu
        if not dados['origins']:
            try:
                cur_token = driver.execute_script("return localStorage.getItem('sisbajud-token') || localStorage.getItem('LS.sisbajud-token');")
                cur_refresh = driver.execute_script("return localStorage.getItem('sisbajud-refresh-token') || localStorage.getItem('LS.sisbajud-refresh-token');")
                if cur_token:
                    ls_items = [{'name': 'sisbajud-token', 'value': cur_token}]
                    if cur_refresh:
                        ls_items.append({'name': 'sisbajud-refresh-token', 'value': cur_refresh})
                    dados['origins'] = [{'origin': 'https://sisbajud.pdpj.jus.br', 'localStorage': ls_items}]
            except Exception:
                pass

        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

        # Também salvar cópia no arquivo fixo ~/.pjeplus/sisbajud_sessao.json
        try:
            with open(_arquivo_sessao_sisbajud(), 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        logger.info(f'[SISBAJUD][COOKIES] Cookies salvos em: {caminho_arquivo} ({len(dados["cookies"])} cookies)')
        return True
    except Exception as e:
        logger.error(f"[SISBAJUD][COOKIES] Erro ao salvar cookies: {e}")
        return False


def carregar_cookies_sisbajud(driver, max_idade_horas=12) -> bool:
    """
    Carrega cookies e sessão SISBAJUD mais recentes e válidos automaticamente.
    Valida rigorosamente:
    1. Verifica idade e integridade do token no arquivo antes de injetar.
    2. Injeta cookies e localStorage nos domínios do SISBAJUD.
    3. Confirma se a sessão realmente ficou ativa (is_sessao_ativa_sisbajud).
    4. Se a tela de login for detectada ou a sessão não for confirmada, descarta os cookies e retorna False.
    """
    try:
        pasta = os.path.join(os.getcwd(), 'cookies_sessoes')
        import glob
        arquivos = []
        if os.path.exists(pasta):
            arquivos = glob.glob(os.path.join(pasta, 'cookies_sisbajud*.json'))
            if not arquivos:
                arquivos = glob.glob(os.path.join(pasta, '*sisbajud*.json'))

        caminho_fixo = _arquivo_sessao_sisbajud()
        if not arquivos and os.path.exists(caminho_fixo):
            arquivos = [caminho_fixo]

        if not arquivos:
            logger.info('[SISBAJUD][COOKIES] Nenhum arquivo de cookies do SISBAJUD encontrado')
            return False

        arquivo_mais_recente = max(arquivos, key=os.path.getmtime)
        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        if 'timestamp' in dados:
            timestamp_str = dados['timestamp']
            cookies = dados.get('cookies', [])
        else:
            timestamp_str = datetime.fromtimestamp(os.path.getmtime(arquivo_mais_recente)).isoformat()
            cookies = dados.get('cookies', dados if isinstance(dados, list) else [])

        # Validar idade do arquivo (sessões SSO de SISBAJUD expiram em 8-12h)
        try:
            timestamp_cookies = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+00:00', ''))
            idade = datetime.now() - timestamp_cookies
            if idade > timedelta(hours=max_idade_horas):
                logger.info(f'[SISBAJUD][COOKIES] Cookies muito antigos ({idade.total_seconds() / 3600:.1f}h > {max_idade_horas}h). Pulando.')
                return False
        except Exception:
            pass

        # Pré-validação do token JWT dentro do arquivo: se já expirou, rejeitar
        for origem in dados.get('origins', []):
            for item in origem.get('localStorage', []):
                if item.get('name') in ('sisbajud-token', 'LS.sisbajud-token'):
                    exp = _extrair_jwt_exp_sisbajud(item.get('value', ''))
                    if exp > 0 and exp < time.time():
                        logger.info(f'[SISBAJUD][COOKIES] Token JWT no arquivo {os.path.basename(arquivo_mais_recente)} já expirou. Pulando restauração.')
                        return False

        contexto = getattr(driver, '_context', None)
        agora = time.time()
        cookies_validos = []
        for c in cookies:
            exp = c.get('expires') or c.get('expiry') or -1
            if exp and exp > 0 and exp < agora:
                continue
            cookies_validos.append(c)

        if not cookies_validos:
            logger.info('[SISBAJUD][COOKIES] Sessão salva sem cookies válidos')
            return False

        # Injetar cookies via contexto Playwright
        if contexto and hasattr(contexto, 'add_cookies'):
            try:
                pw_cookies = []
                for c in cookies_validos:
                    item = dict(c)
                    if 'expiry' in item and 'expires' not in item:
                        item['expires'] = float(item.pop('expiry'))
                    if not item.get('domain'):
                        item['domain'] = '.pdpj.jus.br'
                    item.setdefault('path', '/')
                    pw_cookies.append(item)
                contexto.add_cookies(pw_cookies)
            except Exception as e:
                logger.debug(f'[SISBAJUD][COOKIES] contexto.add_cookies: {e}')

        # Restaurar localStorage se presente em ambas as origens
        origins = dados.get('origins', [])
        itens_restaurar = []
        for origem in origins:
            itens_restaurar.extend(origem.get('localStorage') or [])

        if itens_restaurar:
            for dominio_alvo in ['https://sisbajud.cnj.jus.br/', 'https://sisbajud.pdpj.jus.br/']:
                try:
                    driver.get(dominio_alvo)
                    for item in itens_restaurar:
                        driver.execute_script(
                            "localStorage.setItem(arguments[0], arguments[1]);",
                            item['name'], item['value']
                        )
                except Exception:
                    pass

        # Navega para a página principal do SISBAJUD (dominio CNJ — pdpj nao carrega)
        driver.get('https://sisbajud.cnj.jus.br/')
        espera.assentar(driver, 2)

        # Checagem conclusiva de sessão ativa vs tela de login
        if is_sessao_ativa_sisbajud(driver):
            logger.info(f'[SISBAJUD][COOKIES] Sessão ativa confirmada a partir de {os.path.basename(arquivo_mais_recente)}! Login reaproveitado.')
            return True

        if is_tela_login_sisbajud(driver):
            logger.info(f'[SISBAJUD][COOKIES] Tela de login detectada após carregar cookies de {os.path.basename(arquivo_mais_recente)} (cookies inválidos/expirados).')
        else:
            logger.info(f'[SISBAJUD][COOKIES] Sessão não autenticada após carregar cookies (url={getattr(driver, "current_url", "")}).')

        try:
            driver.delete_all_cookies()
        except Exception:
            pass
        return False
    except Exception as e:
        logger.error(f"[SISBAJUD][COOKIES] Falha ao carregar cookies: {e}")
        return False


def verificar_e_aplicar_cookies_sisbajud(driver) -> bool:
    """Função integrada que verifica e aplica cookies do SISBAJUD automaticamente."""
    if not USAR_COOKIES_AUTOMATICO:
        return False
    logger.debug('[SISBAJUD][COOKIES] Tentando login automatico via cookies salvos...')
    return carregar_cookies_sisbajud(driver)


def salvar_sessao_sisbajud(driver) -> bool:
    """Alias para salvar_cookies_sisbajud."""
    return salvar_cookies_sisbajud(driver)


def restaurar_sessao_sisbajud(driver) -> bool:
    """Alias para carregar_cookies_sisbajud."""
    return carregar_cookies_sisbajud(driver)


def driver_sisbajud(headless=False):
    """Cria o driver para SISBAJUD usando a fábrica definida em driver_config.

    headless: se True, o driver SISB também será headless (herdado do driver PJe).
    """
    try:
        if not criar_driver_sisb:
            logger.info('[SISBAJUD][DRIVER]  criar_driver_sisb indisponível (driver_config ausente)')
        else:
            logger.info('[SISBAJUD][DRIVER] Iniciando criação do driver Firefox SISBAJUD...')
            # A fábrica criar_driver_sisb devolve um WebDriver configurado para SISBAJUD
            driver = criar_driver_sisb(headless=headless)
            if driver:
                logger.info('[SISBAJUD][DRIVER]  Driver criado com sucesso')
                return driver
            logger.info('[SISBAJUD][DRIVER]  criar_driver_sisb retornou None, tentando driver temporario (VT)')
    except Exception as e:
        logger.info(f"[SISBAJUD][DRIVER]  Erro ao criar driver SISBAJUD via driver_config: {e}")
        logger.exception("Erro detectado")

    if not criar_driver_sisb_vt:
        logger.info('[SISBAJUD][DRIVER]  criar_driver_sisb_vt indisponível')
        return None
    try:
        logger.info('[SISBAJUD][DRIVER] Iniciando criação do driver Firefox SISBAJUD temporario (VT)...')
        driver = criar_driver_sisb_vt(headless=headless)
        if driver:
            logger.info('[SISBAJUD][DRIVER]  Driver temporario (VT) criado com sucesso')
        else:
            logger.info('[SISBAJUD][DRIVER]  criar_driver_sisb_vt retornou None')
        return driver
    except Exception as e:
        logger.info(f"[SISBAJUD][DRIVER]  Erro ao criar driver SISB VT temporario: {e}")
        logger.exception("Erro detectado")
        return None


def login_automatico_sisbajud(driver):
    """
    Login automatizado no SISBAJUD com credenciais do Windows Credential Manager.
    Detecta a dialog de ordens pendentes (<mat-dialog-container> / <sisbajud-dialog-aviso-ordem-pendente>)
    para confirmar login valido e fecha via ESC.
    """
    try:
        from Fix import espera
        from Fix.utils import obter_credencial, _is_driver_headless

        cpf = obter_credencial('SISB_CPF', servicos=('sisbajud', 'pjeplus', 'SISB'), aliases=('BP_SISB', 'PJE_USER', 'PJE_CPF'))
        senha = obter_credencial('SISB_SENHA', servicos=('sisbajud', 'pjeplus', 'SISB'), aliases=('BP_PASS', 'PJE_SENHA', 'PJE_PASSWORD'))

        if not cpf or not senha:
            logger.warning('[SISBAJUD][LOGIN] Credenciais SISB_CPF / SISB_SENHA não encontradas no Windows Credential Manager.')
            return False

        logger.info('[SISBAJUD][LOGIN] Navegando para SISBAJUD (https://sisbajud.cnj.jus.br/)...')
        driver.get('https://sisbajud.cnj.jus.br/')
        espera.assentar(driver, 1)

        # 1. Verificar se já tem sessão ativa no SISBAJUD
        if is_sessao_ativa_sisbajud(driver):
            logger.info('[SISBAJUD][LOGIN] Sessão já ativa detectada!')
            return True

        # 2. Aguardar tela de login (Keycloak SSO / campos de usuário)
        logger.info('[SISBAJUD][LOGIN] Aguardando tela de autenticação do SISBAJUD...')
        if not is_tela_login_sisbajud(driver):
            espera.ate(driver, lambda d: is_tela_login_sisbajud(d) or is_sessao_ativa_sisbajud(d), teto=10)

        if is_sessao_ativa_sisbajud(driver):
            logger.info('[SISBAJUD][LOGIN] Sessão ativa confirmada!')
            return True

        # Se não aparecer campo de login diretamente, tentar clicar no botão de entrada da landing page se houver
        if not espera.ate_aparecer(driver, '#username, input[name="username"]', teto=3):
            try:
                clicou_entrar = driver.execute_script("""
                    const botoes = Array.from(document.querySelectorAll('button, a, .btn'));
                    for (const b of botoes) {
                        const txt = (b.textContent || '').trim().toLowerCase();
                        if (txt === 'entrar' || txt.includes('entrar com') || txt.includes('login') || txt === 'acessar') {
                            b.click();
                            return true;
                        }
                    }
                    return false;
                """)
                if clicou_entrar:
                    logger.info('[SISBAJUD][LOGIN] Botão de entrada acionado na landing page')
                    espera.ate_aparecer(driver, '#username, input[name="username"]', teto=8)
            except Exception:
                pass

        if not espera.ate_aparecer(driver, '#username, input[name="username"]', teto=5):
            if is_sessao_ativa_sisbajud(driver):
                logger.info('[SISBAJUD][LOGIN] Sessão ativa detectada!')
                return True
            logger.warning('[SISBAJUD][LOGIN] Campo #username não localizado e sessão não está ativa.')
            return False

        # Preencher CPF e Senha
        logger.info('[SISBAJUD][LOGIN] Preenchendo credenciais do SISBAJUD via Windows Credential Manager...')
        try:
            if hasattr(driver, 'page') and driver.page:
                driver.page.fill('#username, input[name="username"]', str(cpf))
                driver.page.fill('#password, input[name="password"]', str(senha))
            else:
                preencher_campo(driver, '#username', cpf)
                preencher_campo(driver, '#password', senha)
        except Exception as e_fill:
            logger.error('[SISBAJUD][LOGIN] Falha ao preencher credenciais: %s', e_fill)
            return False

        # Clicar em #kc-login
        logger.info('[SISBAJUD][LOGIN] Clicando no botão de login (#kc-login)...')
        try:
            if hasattr(driver, 'page') and driver.page:
                driver.page.click('#kc-login')
            else:
                safe_click_no_scroll(driver, '#kc-login')
        except Exception as e_btn:
            logger.error('[SISBAJUD][LOGIN] Falha ao clicar no botão de login: %s', e_btn)
            return False

        # Verificar se surgiu tela de OTP (código de verificação em duas etapas)
        otp_detectado = False
        if espera.ate_aparecer(driver, '#otp, input[name="otp"]', teto=3):
            otp_detectado = True
            if _is_driver_headless(driver):
                logger.info('[SISBAJUD][LOGIN] Tela de validação em duas etapas (OTP) detectada (modo headless).')
                codigo = input("\n[SISBAJUD] Digite o código de validação (OTP): ").strip()
                if hasattr(driver, 'page') and driver.page:
                    driver.page.fill('#otp, input[name="otp"]', codigo)
                    try:
                        driver.page.locator('input[type="submit"], button[type="submit"], #kc-login').first.click()
                    except Exception:
                        driver.page.keyboard.press('Enter')
                else:
                    preencher_campo(driver, '#otp', codigo)
                    safe_click_no_scroll(driver, 'input[type="submit"], button[type="submit"], #kc-login')
            else:
                logger.info('[SISBAJUD][LOGIN] Tela de validação em duas etapas (OTP) detectada. Digite o código no navegador e confirme...')

        # Validação pós-login via Dialog de ordens pendentes ou sessão ativa
        logger.info('[SISBAJUD][LOGIN] Aguardando confirmação de login válido via dialog de ordens pendentes ou sessão ativa...')
        seletor_dialog = 'sisbajud-dialog-aviso-ordem-pendente, mat-dialog-container:has(sisbajud-dialog-aviso-ordem-pendente), mat-dialog-container'

        login_confirmado = False
        inicio = time.time()
        timeout_dialog = 120.0 if otp_detectado else 45.0

        while (time.time() - inicio) < timeout_dialog:
            # 1. Dialog de aviso de ordens pendentes detectada
            if espera.ate_aparecer(driver, seletor_dialog, teto=1):
                logger.info('[SISBAJUD][LOGIN] Dialog <sisbajud-dialog-aviso-ordem-pendente> detectada! Login confirmado com sucesso.')
                login_confirmado = True

                # Pressionar ESC para fechar a dialog
                logger.info('[SISBAJUD][LOGIN] Pressionando ESC para fechar a dialog...')
                try:
                    if hasattr(driver, 'page') and driver.page:
                        driver.page.keyboard.press('Escape')
                    else:
                        _executar_js = getattr(driver, '_executar_js', getattr(driver, 'execute_script', None))
                        if _executar_js:
                            _executar_js("document.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Escape', 'code': 'Escape', 'keyCode': 27, 'which': 27, bubbles: true}));")
                except Exception as e_esc:
                    logger.debug('[SISBAJUD][LOGIN] Aviso ao enviar tecla ESC: %s', e_esc)

                # Esperar dialog sumir (Fix.espera.ate_sumir)
                espera.ate_sumir(driver, 'sisbajud-dialog-aviso-ordem-pendente', teto=4)

                # Garantia caso ESC não feche o mat-dialog
                try:
                    from SISB.processamento.series_navegar import dispensar_dialog_ordem_pendente
                    dispensar_dialog_ordem_pendente(driver, log=False, timeout=1.5)
                except Exception:
                    pass
                break

            # 2. Sessão ativa comprovada (JWT válido ou DOM autenticado)
            if is_sessao_ativa_sisbajud(driver):
                logger.info('[SISBAJUD][LOGIN] Interface e sessão ativa do SISBAJUD confirmadas. Login concluído com sucesso.')
                login_confirmado = True
                break

            espera.pausa(driver, 0.5)

        if login_confirmado:
            try:
                driver.maximize_window()
            except Exception:
                pass
            return True

        logger.warning('[SISBAJUD][LOGIN] Login automático não confirmado no tempo limite.')
        return False

    except Exception as e:
        logger.info(f'[SISBAJUD][LOGIN] Erro durante login automático: {e}')
        logger.exception("Erro detectado")
        return False


def login_manual_sisbajud(driver, aguardar_url_final=True):
    """
    Login manual para SISBAJUD: navega até a página de login e aguarda o usuário completar o login.
    Detecta conclusão através de is_sessao_ativa_sisbajud(driver).
    NUNCA assume que está logado apenas por ausência de 'login' na URL.
    """
    try:
        logger.info('[SISBAJUD][LOGIN_MANUAL] Navegando para SISBAJUD e aguardando login manual...')
        
        # Verificar se já está com sessão ativa
        if is_sessao_ativa_sisbajud(driver):
            logger.info('[SISBAJUD][LOGIN_MANUAL] Sessão já está ativa no SISBAJUD!')
            return True

        # Se não estiver na tela de login nem no SISBAJUD, navegar
        if not is_tela_login_sisbajud(driver):
            driver.get('https://sisbajud.cnj.jus.br/')
        else:
            logger.info('[SISBAJUD][LOGIN_MANUAL] Já está na página de autenticação, aguardando conclusão...')
        
        # Aguarda o usuário completar o login
        timeout = 300  # 5 minutos para login manual
        inicio = time.time()
        while True:
            try:
                if is_sessao_ativa_sisbajud(driver):
                    logger.info('[SISBAJUD][LOGIN_MANUAL] Login manual detectado com sucesso (URL: %s).', getattr(driver, 'current_url', ''))
                    
                    # Salvar cookies da sessão SISBAJUD
                    if SALVAR_COOKIES_AUTOMATICO:
                        try:
                            salvar_cookies_sisbajud(driver, info_extra='login_manual_sisbajud')
                            logger.info('[SISBAJUD][LOGIN_MANUAL] Cookies salvos após login manual SISBAJUD')
                        except Exception as e:
                            logger.info(f"[SISBAJUD][LOGIN_MANUAL] Falha ao salvar cookies: {e}")
                    return True
            except Exception as e:
                _ = e

            if not aguardar_url_final:
                return False

            if time.time() - inicio > timeout:
                logger.warning('[SISBAJUD][LOGIN_MANUAL] Timeout aguardando login manual.')
                return False

            espera.pausa(driver, 0.5)
    except Exception as e:
        logger.info(f'[SISBAJUD][LOGIN_MANUAL] Erro durante login manual: {e}')
        return False


def salvar_dados_processo_temp(params_adicionais=None):
    """
    Salva dados do processo no arquivo do projeto (dadosatuais.json) para integração entre janelas
    """
    try:
        # Usa caminho do projeto ao invés de pasta temporária
        project_path = os.path.dirname(os.path.abspath(__file__))  # Pasta onde está o sisbajud.py
        dados_path = os.path.join(project_path, 'dadosatuais.json')

        # Adicionar parâmetros de automação aos dados do processo
        dados_para_salvar = processo_dados_extraidos.copy()
        if params_adicionais:
            dados_para_salvar['parametros_automacao'] = params_adicionais
            logger.info(f'[SISBAJUD] Parâmetros de automação adicionados: {params_adicionais}')

        # Sempre sobrescreve o arquivo para não acumular dados de múltiplos processos
        with open(dados_path, 'w', encoding='utf-8') as f:
            json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
        logger.info(f'[SISBAJUD] Dados do processo salvos em: {dados_path}')
    except Exception as e:
        logger.info(f'[SISBAJUD][ERRO] Falha ao salvar dados do processo: {e}')


def iniciar_sisbajud(driver_pje=None, extrair_dados=False):
    """
    Função unificada de inicialização do SISBAJUD:
    1. [OPCIONAL] Extrai dados do processo PJe (somente se extrair_dados=True E processo aberto)
    2. Cria driver Firefox SISBAJUD
    3. Realiza login automatizado
    4. Retorna o driver SISBAJUD logado

    IMPORTANTE: Para uso em lote, chamar com extrair_dados=False.
    A extração de dados deve ser feita DEPOIS de abrir cada processo individual.
    """
    global processo_dados_extraidos

    try:
        logger.info('[SISBAJUD] ============================================')
        logger.info('[SISBAJUD] Iniciando sessão SISBAJUD...')
        logger.info(f'[SISBAJUD][DEBUG] extrair_dados={extrair_dados}, driver_pje presente={driver_pje is not None}')
        logger.info('[SISBAJUD] ============================================')

        # 1. Extrair dados do processo PJe (SOMENTE se solicitado explicitamente E driver fornecido)
        if extrair_dados and driver_pje:
            logger.info('[SISBAJUD] Extraindo dados do processo PJe...')
            from Fix.extracao import extrair_dados_processo
            processo_dados_extraidos = extrair_dados_processo(driver_pje)
            if processo_dados_extraidos:
                # Corrigir para usar o campo correto do dadosatuais.json
                numero_lista = processo_dados_extraidos.get("numero", [])
                numero_display = numero_lista[0] if numero_lista else "N/A"
                logger.info(f'[SISBAJUD]  Dados extraídos: {numero_display}')
                salvar_dados_processo_temp()
            else:
                logger.info('[SISBAJUD]  Não foi possível extrair dados do processo')
        elif extrair_dados and not driver_pje:
            logger.info('[SISBAJUD]  Driver PJE não fornecido, não é possível extrair dados')

        # 2. Criar driver Firefox SISBAJUD (herda modo headless do driver PJe)
        sisb_headless = False
        if driver_pje is not None:
            # PWDriver expõe .headless; Selenium usa is_headless_mode()
            if hasattr(driver_pje, 'headless'):
                sisb_headless = bool(driver_pje.headless)
            else:
                from Fix.browser_suporte import is_headless_mode
                sisb_headless = is_headless_mode(driver_pje)
        logger.info(f'[SISBAJUD] Criando driver Firefox SISBAJUD (headless={sisb_headless})...')
        driver = driver_sisbajud(headless=sisb_headless)
        
        if not driver:
            logger.info('[SISBAJUD]  Falha ao criar driver - driver_sisbajud() retornou None')
            return None
        
        logger.info(f'[SISBAJUD][DEBUG] Driver criado com sucesso: {type(driver)}')

        # 1. Tentar reutilizar sessão via cookies (mesmo padrão PJe)
        cookie_restored = False
        if USAR_COOKIES_AUTOMATICO:
            try:
                if carregar_cookies_sisbajud(driver):
                    if is_sessao_ativa_sisbajud(driver):
                        logger.info('[SISBAJUD] Cookies SISBAJUD carregados com sucesso e sessão ativa confirmada; pulando etapa de login.')
                        cookie_restored = True
                    else:
                        logger.warning('[SISBAJUD] Cookies foram carregados mas sessão não está ativa.')
            except Exception as e:
                logger.debug(f'[SISBAJUD] Falha ao carregar cookies SISBAJUD: {e}')
                cookie_restored = False

        login_ok = cookie_restored

        # 2. Se cookies não restauraram, tentar tokens do localStorage
        if not login_ok:
            try:
                result_token = carregar_tokens_sisbajud()
                if result_token.get('sucesso'):
                    at = result_token['access_token']
                    rt = result_token.get('refresh_token')
                    if injetar_tokens_sisbajud(driver, at, rt):
                        driver.get('https://sisbajud.cnj.jus.br/')
                        espera.assentar(driver, 2)
                        if is_sessao_ativa_sisbajud(driver):
                            logger.info('[SISBAJUD] Tokens salvos injetados com sucesso e sessão ativa confirmada; pulando login.')
                            login_ok = True
                        else:
                            logger.info('[SISBAJUD] Tokens injetados mas sessão não confirmada como ativa.')
            except Exception as e:
                logger.debug('[SISBAJUD] Nao foi possivel reutilizar tokens: %s', e)

        # 3. Login automático com CPF/Senha do Windows Credential Manager
        if not login_ok:
            logger.info('[SISBAJUD] Executando login automático via CPF...')
            login_ok = login_automatico_sisbajud(driver)
            if login_ok:
                logger.info('[SISBAJUD] Login automático concluído com sucesso!')
                try:
                    salvar_tokens_sisbajud(driver)
                except Exception:
                    pass
                if SALVAR_COOKIES_AUTOMATICO:
                    try:
                        salvar_cookies_sisbajud(driver, info_extra='login_automatico_sisbajud')
                    except Exception as e:
                        logger.debug(f'[SISBAJUD] Falha ao salvar cookies: {e}')

        # 4. Fallback: solicitar login manual apenas se o automático falhar (ex: MFA/Captcha)
        if not login_ok:
            logger.warning('[SISBAJUD] Login automático não concluído. Solicitando login manual...')
            print('\n' + '=' * 60)
            print('  LOGIN SISBAJUD MANUAL NECESSARIO')
            print('=' * 60)
            print('  O browser esta aberto na pagina de login do SISBAJUD.')
            print('  Faca o login manualmente (CPF + senha + MFA se necessario).')
            print('  Apos concluir o login no browser, volte aqui e')
            print('  pressione ENTER para continuar o fluxo.')
            print('=' * 60)
            input('  [SISBAJUD] Login concluido? Pressione ENTER para continuar... ')
            print()

            # Aguardar confirmacao de sessao ativa
            if login_manual_sisbajud(driver, aguardar_url_final=True):
                login_ok = True
                logger.info('[SISBAJUD] Login manual SISBAJUD concluido com sucesso')
                try:
                    salvar_tokens_sisbajud(driver)
                except Exception:
                    pass
                if SALVAR_COOKIES_AUTOMATICO:
                    try:
                        salvar_cookies_sisbajud(driver, info_extra='login_manual_sisbajud')
                    except Exception as e:
                        logger.debug(f'[SISBAJUD] Falha ao salvar cookies: {e}')
            else:
                logger.error('[SISBAJUD] Login manual SISBAJUD nao foi confirmado')

        if not login_ok:
            logger.info('[SISBAJUD]  Nao foi possivel autenticar no SISBAJUD')
            try:
                driver.quit()
            except Exception as e:
                _ = e
            return None

        # Aguardar confirmação de sessão ativa do SISBAJUD após login
        if not is_sessao_ativa_sisbajud(driver):
            espera.ate(driver, is_sessao_ativa_sisbajud, teto=10)

        if not is_sessao_ativa_sisbajud(driver):
            logger.error('[SISBAJUD] Sessão ativa não confirmada após fluxo de autenticação')
            try:
                driver.quit()
            except Exception:
                pass
            return None

        # Maximizar janela rapidamente
        try:
            driver.maximize_window()
            logger.info('[SISBAJUD]  Janela maximizada')
        except Exception as e:
            logger.info(f'[SISBAJUD]  Não foi possível maximizar a janela: {e}')

        # Garantia final: dispensar dialog de ordens pendentes se ainda estiver aberta
        logger.info('[SISBAJUD] Verificando e dispensando dialog inicial (ordens pendentes)...')
        try:
            from SISB.processamento.series_navegar import dispensar_dialog_ordem_pendente
            dispensar_dialog_ordem_pendente(driver, log=True, timeout=2.0)
        except Exception as e_dlg:
            logger.debug(f'[SISBAJUD] Erro ao verificar dialog: {e_dlg}')

        logger.info('[SISBAJUD]  Sessão SISBAJUD inicializada com sucesso - login realizado e pronto para execução')
        return driver
# exceção externa para toda inicialização
    except Exception as e:
        logger.info(f'[SISBAJUD][ERRO] Falha ao iniciar sessão SISBAJUD: {e}')
        try:
            logger.exception("Erro detectado")
        except Exception as trace_err:
            _ = trace_err

    return None


def minuta_bloqueio(driver, dados_processo=None, driver_pje=None, log=True, fechar_driver=True, prazo_dias=None, protocolar=False):
    """
    Orquestra a criação de minuta de bloqueio no SISBAJUD:
    0. Extrair dados do processo (se necessário) e verificar valor
    1. Se não houver valor: criar GIGS -1/xs valor e retornar
    2. Se houver valor: prosseguir com criação da minuta
    3. Validar dados do processo
    4. Preencher campos iniciais
    5. Processar REUs otimizado
    6. Salvar minuta
    7. Gerar relatório
    
    Args:
        fechar_driver: Se True, fecha o driver SISBAJUD ao final. Use False para processamento em lote.
        prazo_dias: Prazo em dias (30 ou 60). Se None, solicita ao usuário via diálogo.
    """
    resultado = {
        'status': 'pendente',
        'reus_processados': 0,
        'erros': [],
        'detalhes': {}
    }

    try:
        logger.info('\n[SISBAJUD] INICIANDO CRIAÇÃO DE MINUTA DE BLOQUEIO')
        logger.info('=' * 60)

        pendencia = None  # será definido após verificação de cálculo

        # 0. EXTRAIR DADOS DO PROCESSO (se necessário) e VERIFICAR VALOR
        if dados_processo is None:
            if log:
                logger.info('[SISBAJUD] Extraindo dados do processo do PJe...')
            try:
                from Fix.extracao import extrair_dados_processo
                if driver_pje:
                    dados_processo = extrair_dados_processo(driver_pje)
                else:
                    # Fallback: carregar do arquivo
                    from .utils import carregar_dados_processo
                    dados_processo = carregar_dados_processo()
                
                if not dados_processo:
                    if log:
                        logger.info('[SISBAJUD]  Falha ao extrair/carregar dados do processo')
                    resultado['status'] = 'erro'
                    resultado['erros'].append('Falha ao extrair/carregar dados do processo')
                    return resultado
                    
                if log:
                    logger.info('[SISBAJUD]  Dados do processo extraídos/carregados com sucesso')
            except Exception as e:
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao extrair dados do processo: {e}')
                resultado['status'] = 'erro'
                resultado['erros'].append(f'Erro ao extrair dados: {e}')
                return resultado

        # VERIFICAR SE HÁ VALOR DE BLOQUEIO (validação final - normalmente já verificado antes no lote)
        divida = dados_processo.get('divida', {}) if dados_processo else {}
        valor = divida.get('valor')
        
        if not valor:
            # Usar valor padrão 33,33 para garantir criação da minuta
            # mesmo quando o valor da execução não foi extraído do processo
            valor_padrao = '33,33'
            if log:
                logger.info(f'[SISBAJUD]  Sem valor de bloqueio — usando padrão: R$ {valor_padrao}')
            if 'divida' not in dados_processo or not isinstance(dados_processo.get('divida'), dict):
                dados_processo['divida'] = {}
            dados_processo['divida']['valor'] = valor_padrao
            valor = valor_padrao

        # Detectar pendências de cálculo
        pendencia = None
        _data_divida = divida.get('data', '') if isinstance(divida, dict) else ''
        _usando_padrao = (valor == '33,33')

        if _usando_padrao:
            pendencia = 'sem_calculo'
            if log:
                logger.info('[SISBAJUD]  Pendência: sem cálculo (padrão 33,33)')
        elif _data_divida:
            try:
                from datetime import datetime as _dt
                _dt_divida = _dt.strptime(_data_divida, '%d/%m/%Y')
                if (_dt.now() - _dt_divida).days > 90:
                    pendencia = 'calculo_antigo'
                    if log:
                        logger.info(f'[SISBAJUD]  Pendência: cálculo de {_data_divida} (>3 meses)')
            except Exception:
                pass
        
        if log:
            logger.info(f'[SISBAJUD]  Valor encontrado: {valor} - prosseguindo com minuta')

        # 1. Clicar em "Nova Minuta" para iniciar criação de minuta
        try:
            from SISB.processamento.series_navegar import dispensar_dialog_ordem_pendente
            dispensar_dialog_ordem_pendente(driver, log=log, timeout=1.0)
        except Exception:
            pass

        logger.info('[SISBAJUD] Clicando em "Nova Minuta" para iniciar criação...')
        script_nova_minuta = """
        var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
        if (!botaoNova) {
            botaoNova = document.querySelector('button.mat-fab.mat-primary');
        }
        if (botaoNova) {
            // Se for ícone, clica no botão pai
            if (botaoNova.tagName === 'MAT-ICON') {
                botaoNova = botaoNova.closest('button');
            }
            botaoNova.click();
            return true;
        }
        return false;
        """

        sucesso_nova_minuta = driver.execute_script(script_nova_minuta)
        if sucesso_nova_minuta:
            logger.info('[SISBAJUD]  Botão "Nova Minuta" clicado automaticamente')
            # Aguardar navegação com wait condicional (time.sleep(2) substituído)
            try:
                espera.ate_aparecer(driver, 'input[placeholder*="Juiz"], .mat-form-field, form', teto=10)
            except Exception:
                logger.info('[SISBAJUD] Timeout aguardando formulário da minuta - continuando')
        else:
            logger.info('[SISBAJUD]  Botão "Nova Minuta" não encontrado')
            return {
                'status': 'erro',
                'erros': ['Botão "Nova Minuta" não encontrado'],
                'reus_processados': 0,
                'detalhes': {}
            }

        # 2. Validar dados do processo
        dados_validos, numero_processo = helpers._validar_dados(dados_processo)
        if not dados_validos:
            resultado['status'] = 'erro'
            resultado['erros'].append('Dados do processo inválidos ou insuficientes')
            return resultado

        # 2.1 Usar prazo_dias fornecido ou padrão 30
        if prazo_dias is None:
            prazo_dias = 30

        # 3. Preencher campos iniciais (com o prazo selecionado)
        campos_preenchidos = helpers._preencher_campos_iniciais(driver, dados_processo, prazo_dias)
        if not campos_preenchidos:
            resultado['status'] = 'erro'
            resultado['erros'].append('Falha ao preencher campos iniciais')
            return resultado

        # 4. Processar REUs otimizado (com alerta de excesso)
        todos_reus = dados_processo.get('reu', []) or []
        if len(todos_reus) > 10 and log:
            logger.info(
                '[SISBAJUD] ALERTA: %d reus excedem limite de 10 — '
                'apenas os 10 primeiros validos serao incluidos nesta minuta',
                len(todos_reus)
            )
            resultado['alerta_excesso_reus'] = True
            resultado['total_reus'] = len(todos_reus)
        reus_processados = helpers._processar_reus_otimizado(driver, todos_reus, max_validos=10)
        resultado['reus_processados'] = reus_processados

        # 5. Configurar valor da execução
        _configurar_valor(driver, dados_processo)

        # 6. Salvar minuta
        minuta_salva = helpers._salvar_minuta(driver)
        if not minuta_salva:
            resultado['status'] = 'erro'
            resultado['erros'].append('Falha ao salvar minuta')
            return resultado

        # 6.1 PROTOCOLAR/ASSINAR MINUTA
        # REMOVIDO: passo de protocolar/assinar foi desativado (pulamos essa fase)
        minuta_protocolada = False
        resultado['minuta_protocolada'] = False
        if log:
            logger.info('[SISBAJUD]  Passo 6.1 (protocolar/assinar) foi removido - continuando fluxo')

        # 6.2 Gerar relatório (para juntada posterior manual/automática)
        relatorio_gerado = helpers._gerar_relatorio_minuta(driver, numero_processo)
        if not relatorio_gerado:
            if log:
                logger.info('[SISBAJUD]  Falha ao gerar relatório da minuta')
            # Prosseguir com fechamento e retorno com status de erro parcial

        # Se valor mock (33,33), substituir no relatório
        if relatorio_gerado and pendencia == 'sem_calculo':
            conteudo = relatorio_gerado.get('conteudo', '') if isinstance(relatorio_gerado, dict) else relatorio_gerado
            if isinstance(conteudo, str) and '33,33' in conteudo:
                conteudo = conteudo.replace('33,33', '(ver planilha mais recente)')
                if isinstance(relatorio_gerado, dict):
                    relatorio_gerado['conteudo'] = conteudo
                try:
                    from PEC.anexos import salvar_conteudo_clipboard
                    salvar_conteudo_clipboard(
                        conteudo=conteudo,
                        numero_processo=numero_processo,
                        tipo_conteudo="sisbajud_minuta",
                        debug=log
                    )
                except Exception:
                    pass

        # 6.5 Se o relatório foi gerado e um driver PJE foi passado, executar a juntada
        # (usa relatório da PRIMEIRA minuta)
        juntada_executada = False
        if relatorio_gerado:
            if log:
                logger.info(f'[SISBAJUD][DEBUG] relatorio_gerado: {bool(relatorio_gerado)}, driver_pje presente: {driver_pje is not None}')
            # Debug: mostrar tipo/representação do driver_pje
            if driver_pje is not None and log:
                try:
                    logger.info(f'[SISBAJUD][DEBUG] driver_pje type: {type(driver_pje)}')
                except Exception as e:
                    _ = e
        if relatorio_gerado and driver_pje:
            try:
                # A juntada da minuta de bloqueio deve usar o próprio modelo da minuta
                # (modelo 'xteim') — não usar os wrappers de ordem genéricos.
                if log:
                    logger.info('[SISBAJUD] Executando juntada DA MINUTA no PJe (modelo xteim)...')

                # Garantir que o foco está na aba /detalhe do PJe antes de executar a juntada
                try:
                    if driver_pje:
                        aba_detalhe = None
                        for handle in list(driver_pje.window_handles):
                            try:
                                driver_pje.switch_to.window(handle)
                                try:
                                    url = driver_pje.current_url or ''
                                except Exception:
                                    url = ''
                                if '/detalhe' in url:
                                    aba_detalhe = handle
                                    break
                            except Exception:
                                continue

                        if aba_detalhe:
                            try:
                                driver_pje.switch_to.window(aba_detalhe)
                                logger.info('[SISBAJUD]  Foco ajustado para aba /detalhe do PJe antes da juntada')
                            except Exception:
                                pass
                        else:
                            # Tentar aguardar brevemente por /detalhe na aba atual como fallback
                            try:
                                from Fix.core import esperar_url_conter
                                driver_pje.switch_to.window(driver_pje.window_handles[-1])
                                esperar_url_conter(driver_pje, '/detalhe', timeout=5)
                                logger.info('[SISBAJUD]  Aguardando /detalhe na aba atual (fallback)')
                            except Exception:
                                logger.info('[SISBAJUD]  Aviso: não foi possível garantir aba /detalhe antes da juntada')
                except Exception as e:
                    logger.info(f'[SISBAJUD]  Erro ao tentar ajustar foco para PJe: {e}')

                # Juntada (wrapper ja inclui navegacao, juntada e fechamento da aba)
                from PEC.anexos import anex_sisbconsulta
                juntada_executada = anex_sisbconsulta(driver_pje, numero_processo, debug=log, modelo='xteim')
                resultado['juntada_executada'] = bool(juntada_executada)
                if juntada_executada and log:
                    logger.info('[SISBAJUD]  Juntada da minuta realizada no PJe')
                elif log:
                    logger.info('[SISBAJUD]  Juntada da minuta pode nao ter sido executada corretamente')

                # Apos a juntada, aplicar visibilidade para certidao sigilosa
                if juntada_executada and driver_pje:
                    from atos.wrappers_utils import executar_visibilidade_sigilosos_se_necessario
                    if log:
                        logger.info('[SISBAJUD] Aplicando visibilidade para certidão sigilosa no PJe (/detalhe)...')
                    vis_ok = executar_visibilidade_sigilosos_se_necessario(driver_pje, True, debug=log)
                    resultado['visibilidade_certidao_sigilosa'] = bool(vis_ok)
                    if vis_ok and log:
                        logger.info('[SISBAJUD]  Visibilidade para certidão sigilosa aplicada')
                    elif log:
                        logger.info('[SISBAJUD]  Falha ao aplicar visibilidade para certidão sigilosa')

                    # Criar GIGS (após visibilidade, ainda em /detalhe)
                    from Fix.extracao import criar_gigs, criar_comentario
                    gigs_prazo = '60' if prazo_dias == 60 else '22'
                    if pendencia == 'calculo_antigo':
                        gigs_str = f'{gigs_prazo}/xs resultado CALC'
                    else:
                        gigs_str = f'{gigs_prazo}/xs resultado'
                    if log:
                        logger.info(f'[SISBAJUD] Criando GIGS {gigs_str}...')
                    resultado_gigs = criar_gigs(driver_pje, gigs_str, log=log)
                    if resultado_gigs and log:
                        logger.info(f'[SISBAJUD]  GIGS {gigs_str} criado')
                    elif log:
                        logger.info(f'[SISBAJUD]  GIGS {gigs_str} não foi criado')

                    if pendencia == 'sem_calculo':
                        if log:
                            logger.info('[SISBAJUD] Criando comentário "Bruna - Atualizar"...')
                        criar_comentario(driver_pje, 'Bruna - Atualizar', log=log)
            except Exception as e:
                resultado['erros'].append(f'Erro na juntada PJE (minuta): {e}')
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao executar juntada da minuta: {e}')

        # 7. Fechar driver SISBAJUD (minuta salva e relatório gerado/parcial)
        if fechar_driver:
            try:
                driver.quit()
                if log:
                    logger.info('[SISBAJUD]  Driver SISBAJUD fechado')
            except Exception as e:
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao fechar driver: {e}')
        else:
            if log:
                logger.info('[SISBAJUD] Driver SISBAJUD mantido aberto (modo lote)')

        resultado['status'] = 'concluido'
        resultado['pendencia'] = pendencia
        if log:
            logger.info(f'[SISBAJUD]  Minuta de bloqueio concluída: {resultado["reus_processados"]} REUs processados')

        return resultado

    except Exception as e:
        erro = f"Erro geral na criação de minuta: {str(e)}"
        if log:
            logger.info(f'[SISBAJUD]  {erro}')
        resultado['status'] = 'erro'
        resultado['erros'].append(erro)

        if fechar_driver:
            try:
                driver.quit()
            except Exception as e:
                _ = e

        return resultado


def processar_ordem_sisbajud(driver, dados_processo, driver_pje=None, log=True, fechar_driver=True):
    """
    Processamento completo de ordens no SISBAJUD:
    1. Carregar dados do processo
    2. Filtrar séries válidas
    3. Processar séries e ordens
    4. Gerar relatório
    5. Executar juntada no PJE
    
    Args:
        fechar_driver: Se True, fecha o driver SISBAJUD ao final. Use False para processamento em lote.
    """
    resultado = {
        'status': 'pendente',
        'tipo_fluxo': None,
        'series_processadas': 0,
        'ordens_processadas': 0,
        'erros': [],
        'detalhes': {}
    }

    try:
        logger.info('\n[SISBAJUD] INICIANDO PROCESSAMENTO DE ORDENS')
        logger.info('=' * 60)

        # 1. Carregar dados do processo (usa parâmetro se passado, senão carrega do arquivo)
        if dados_processo:
            # Usar dados passados por parâmetro (processamento em lote)
            numero_processo = dados_processo.get('numero_processo') or dados_processo.get('numero')
            # Garantir que numero_processo seja string (pode vir como lista)
            if isinstance(numero_processo, list):
                numero_processo = numero_processo[0] if numero_processo else None
            if log:
                logger.info(f'[SISBAJUD] Usando dados do processo passados por parâmetro: {numero_processo}')
        else:
            # Fallback: carregar do arquivo (modo standalone)
            dados_processo, numero_processo = helpers._carregar_dados_ordem()
        
        if not dados_processo or not numero_processo:
            resultado['status'] = 'erro'
            resultado['erros'].append('Falha ao carregar dados do processo')
            return resultado

        # 1.5. Navegar para teimosinha e inserir número do processo
        if log:
            logger.info(f'[SISBAJUD] Navegando para teimosinha com processo: {numero_processo}')

        teimosinha_ok = False
        ultimo_erro = None
        for tentativa in range(2):
            try:
                # Resetar driver para estado limpo antes de navegar (evita conflito com SPA residual)
                if tentativa > 0 or not fechar_driver:
                    driver.get("about:blank")
                    aguardar_renderizacao_nativa(driver, timeout=2)

                # Navegar para a URL da teimosinha (dominio CNJ — pdpj nao carrega)
                driver.get("https://sisbajud.cnj.jus.br/teimosinha")
                # Aguardar carregamento completo da página antes de buscar elemento
                aguardar_renderizacao_nativa(driver, timeout=10)
                if log:
                    logger.info('[SISBAJUD]  Navegação para teimosinha realizada')

                # Aguardar carregamento da página e campo de processo
                campo_processo = espera.ate_aparecer(driver, 'input[placeholder="Número do Processo"]', teto=15)
                if not campo_processo:
                    # Formulario nao carregou (SPA lenta/travada) — refresh automatico
                    # evita depender de refresh manual, quando o fluxo perde o fio por timeout.
                    if log:
                        logger.info('[SISBAJUD]  Campo de processo não apareceu — refresh automático da página...')
                    driver.get("https://sisbajud.cnj.jus.br/teimosinha")
                    aguardar_renderizacao_nativa(driver, timeout=10)
                    campo_processo = espera.ate_aparecer(driver, 'input[placeholder="Número do Processo"]', teto=15)
                if campo_processo:
                    try:
                        preencher_campo(driver, 'input[placeholder="Número do Processo"]', numero_processo)
                        if hasattr(driver, 'page') and driver.page:
                            driver.page.keyboard.press('Enter')
                        elif hasattr(campo_processo, 'press'):
                            campo_processo.press('Enter')
                    except Exception as e_proc:
                        logger.debug(f'[SISBAJUD] Aviso ao preencher processo: {e_proc}')

                if log:
                    logger.info('[SISBAJUD]  Processo inserido e ENTER pressionado')

                # Aguardar o carregamento da busca do processo (SPA Angular)
                import time
                espera.assentar(driver, 5)

                # Aguardar carregamento da série
                from Fix.utils import aguardar_pagina_carregar
                aguardar_pagina_carregar(driver, timeout=15)

                if log:
                    logger.info('[SISBAJUD]  Processo inserido no SISBAJUD e série aberta')

                # Dispensar dialog de ordens pendentes se aparecer
                try:
                    from SISB.processamento.series_navegar import dispensar_dialog_ordem_pendente
                    dispensar_dialog_ordem_pendente(driver, log)
                except Exception:
                    pass

                teimosinha_ok = True
                break

            except Exception as e:
                ultimo_erro = e
                if log and tentativa == 0:
                    logger.info(f'[SISBAJUD]  Tentativa {tentativa + 1} falhou, retentando... ({str(e)[:100]})')

        if not teimosinha_ok:
            erro = f'Erro ao navegar/inserir processo no SISBAJUD: {str(ultimo_erro)}'
            if log:
                logger.info(f'[SISBAJUD]  {erro}')
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado

        # 2. Calcular data limite para filtro (30 dias atrás)
        data_limite = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
        if log:
            logger.info(f'[SISBAJUD] Data limite para filtro: {data_limite.strftime("%d/%m/%Y")} (30 dias)')

        # 3. Filtrar séries válidas
        series_validas = helpers._filtrar_series(driver, data_limite)
        if not series_validas:
            resultado['status'] = 'concluido'
            resultado['erros'].append('Não há séries válidas para processar')
            return resultado

        # 4. Determinar tipo de fluxo baseado nos valores das séries
        total_bloqueado = sum(float(s.get('valor_bloqueado', 0)) for s in series_validas)
        total_bloquear = sum(float(s.get('valor_bloquear', 0)) for s in series_validas)

        if total_bloqueado == 0.0:
            tipo_fluxo = 'NEGATIVO'
        elif total_bloqueado < 100.0 and total_bloquear >= 1000.0:
            tipo_fluxo = 'DESBLOQUEIO'
        else:
            tipo_fluxo = 'POSITIVO'

        resultado['tipo_fluxo'] = tipo_fluxo
        if log:
            logger.info(f'[SISBAJUD] Tipo de fluxo determinado: {tipo_fluxo}')

        # 4.5 Calcular estratégia de bloqueio (apenas para POSITIVO)
        estrategia = None
        if tipo_fluxo == 'POSITIVO':
            estrategia = helpers._calcular_estrategia_bloqueio(series_validas, dados_processo, log)
            resultado['estrategia'] = estrategia
            
            # Ordenar séries por valor de bloqueio (decrescente) para otimizar transferências
            if estrategia.get('tipo') == 'TRANSFERIR_PARCIAL':
                series_validas_ordenadas = sorted(series_validas, key=lambda s: float(s.get('valor_bloqueado', 0)), reverse=True)
                if log:
                    logger.info(f'[SISBAJUD]  Séries ordenadas por valor (maior primeiro) para otimizar transferências')
                series_validas = series_validas_ordenadas

        # 5. Processar séries e ordens (APENAS se houver algo para processar)
        if tipo_fluxo in ['POSITIVO', 'DESBLOQUEIO']:
            resultado_processamento = helpers._processar_series(driver, series_validas, tipo_fluxo, log, estrategia=estrategia)
            resultado.update(resultado_processamento)

            # Fail-safe: se havia series para processar mas 0 foram processadas, e erro
            if len(series_validas) > 0 and resultado.get('series_processadas', 0) == 0 and resultado.get('ordens_processadas', 0) == 0:
                if not resultado.get('erros'):
                    resultado['erros'] = []
                resultado['erros'].append('Falha ao processar series: nenhuma ordem extraida (possivel problema de navegacao)')
                if log:
                    logger.error('[SISBAJUD] FAIL-SAFE: 0 ordens extraidas de %d series — marcando como erro', len(series_validas))
        else:
            # NEGATIVO: sem bloqueios, pular processamento de séries
            if log:
                logger.info('[SISBAJUD] ⏭ Fluxo NEGATIVO: pulando processamento de séries')
            resultado['series_processadas'] = 0
            resultado['ordens_processadas'] = 0

        # 6. Gerar relatório (incluindo dados das séries e estratégia)
        # Para fluxo POSITIVO, passar o driver para extrair dados dos bloqueios da página
        relatorio_gerado = helpers._gerar_relatorio_ordem(
            tipo_fluxo,
            resultado['series_processadas'],
            resultado['ordens_processadas'],
            resultado['detalhes'],
            series_validas,  # Passar séries para o relatório
            driver if tipo_fluxo == 'POSITIVO' else None,  # Driver para extrair bloqueios
            log,
            numero_processo=numero_processo,  # Passar número do processo para o clipboard
            estrategia=estrategia  # Passar estratégia para o relatório
        )

        # 7. Executar juntada no PJE
        if relatorio_gerado and driver_pje:
            juntada_executada = helpers._executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log)
            resultado['juntada_executada'] = juntada_executada
            
            # 7.1 Executar ato apropriado após juntada
            if juntada_executada:
                try:
                    from atos.wrappers_ato import ato_meios, ato_bloq
                    
                    # Fechar aba da juntada (minuta de anexo) após salvar e voltar para /detalhe
                    try:
                        # Fechar aba atual (juntada)
                        driver_pje.close()
                        if log:
                            logger.info('[SISBAJUD]  Aba de juntada fechada')
                        
                        # Procurar aba /detalhe e focar nela
                        abas_disponiveis = driver_pje.window_handles
                        aba_detalhe_encontrada = False
                        
                        for aba in abas_disponiveis:
                            try:
                                driver_pje.switch_to.window(aba)
                                url_atual = driver_pje.current_url
                                if '/detalhe' in url_atual:
                                    aba_detalhe_encontrada = True
                                    if log:
                                        logger.info(f'[SISBAJUD]  Foco na aba /detalhe: {url_atual}')
                                    break
                            except Exception:
                                continue
                        
                        if not aba_detalhe_encontrada:
                            if log:
                                logger.info('[SISBAJUD]  Aba /detalhe não encontrada, usando primeira aba disponível')
                            # Fallback: usar primeira aba
                            driver_pje.switch_to.window(driver_pje.window_handles[0])
                            
                    except Exception as e_fechar:
                        if log:
                            logger.info(f'[SISBAJUD]  Erro ao fechar aba de juntada: {e_fechar}')
                    
                    if tipo_fluxo == 'POSITIVO':
                        # Fluxo POSITIVO: executar ato_bloq
                        if log:
                            logger.info('[SISBAJUD] Executando ato_bloq (fluxo POSITIVO)...')
                        ato_bloq(driver_pje)
                        if log:
                            logger.info('[SISBAJUD]  ato_bloq executado com sucesso')
                        
                        # Criar GIGS após ato_bloq (voltando para aba detalhe)
                        try:
                            if log:
                                logger.info('[SISBAJUD] Criando GIGS "1/xs pec dec"...')
                            from Fix.extracao import criar_gigs
                            criar_gigs(driver_pje, "1/xs pec dec", log=log)
                            if log:
                                logger.info('[SISBAJUD]  GIGS criado com sucesso')
                        except Exception as e_gigs:
                            if log:
                                logger.info(f'[SISBAJUD]  Erro ao criar GIGS: {e_gigs}')
                    else:
                        # Fluxo NEGATIVO ou DESBLOQUEIO: executar ato_meios
                        if log:
                            logger.info(f'[SISBAJUD] Executando ato_meios (fluxo {tipo_fluxo})...')
                        ato_meios(driver_pje)
                        if log:
                            logger.info('[SISBAJUD]  ato_meios executado com sucesso')
                            
                    resultado['ato_executado'] = True
                except Exception as e_ato:
                    if log:
                        logger.info(f'[SISBAJUD]  Erro ao executar ato: {e_ato}')
                    resultado['ato_executado'] = False

        # 8. Fechar driver SISBAJUD
        if fechar_driver:
            try:
                driver.quit()
                if log:
                    logger.info('[SISBAJUD]  Driver SISBAJUD fechado')
            except Exception as e:
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao fechar driver: {e}')
        else:
            if log:
                logger.info('[SISBAJUD] Driver SISBAJUD mantido aberto (modo lote)')

        resultado['status'] = 'concluido'
        if log:
            logger.info(f'[SISBAJUD]  Processamento concluído: {resultado["series_processadas"]} séries, {resultado["ordens_processadas"]} ordens')

        return resultado

    except Exception as e:
        erro = f"Erro geral no processamento: {str(e)}"
        if log:
            logger.info(f'[SISBAJUD]  {erro}')
        resultado['status'] = 'erro'
        resultado['erros'].append(erro)

        if fechar_driver:
            try:
                driver.quit()
            except Exception as e:
                _ = e

        return resultado


def processar_bloqueios(driver_pje=None):
    """
    Processa bloqueios no SISBAJUD usando a função processar_ordem_sisbajud
    SEMPRE carrega dados de dadosatuais.json - nenhum parâmetro necessário
    """
    try:
        logger.info('\n[SISBAJUD] INICIANDO PROCESSAMENTO DE BLOQUEIOS')
        logger.info('=' * 60)

        # 1. Inicializar SISBAJUD
        driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisbajud:
            logger.info('[SISBAJUD]  Falha ao inicializar SISBAJUD')
            return None

        # 2. Carregar dados do processo do arquivo (ÚNICA FONTE)
        dados_processo = utils.carregar_dados_processo()
        if not dados_processo:
            logger.info('[SISBAJUD]  Arquivo dadosatuais.json não encontrado. Execute extrair_dados_processo NO PJE antes!')
            return None

        # 3. Processar ordens SISBAJUD
        resultado = processar_ordem_sisbajud(driver_sisbajud, dados_processo, driver_pje=driver_pje)

        # 4. Retornar resultado para o PJe
        if resultado['status'] == 'concluido':
            logger.info('[SISBAJUD]  Processamento de bloqueios concluído com sucesso!')

            return {
                'status': 'sucesso',
                'dados_processamento': resultado,
                'acao_posterior': {
                    'tipo': 'atualizar_pje_bloqueios',
                    'parametros': {
                        'id_processo': dados_processo.get('id_processo'),
                        'tipo_fluxo': resultado.get('tipo_fluxo'),
                        'series_processadas': resultado.get('series_processadas', 0),
                        'ordens_processadas': resultado.get('ordens_processadas', 0)
                    }
                }
            }
        else:
            logger.info('[SISBAJUD]  Falha no processamento de bloqueios')
            return {
                'status': 'erro',
                'erros': resultado.get('erros', []),
                'acao_posterior': None
            }

    except Exception as e:
        logger.info(f'[SISBAJUD][ERRO] Falha no processamento de bloqueios: {e}')
        logger.exception("Erro detectado")
        return None


def coletar_dados_minuta_sisbajud(driver, dados_processo=None, numero_processo=None):
    """
    Executa JavaScript para coletar dados da minuta SISBAJUD e retorna o texto formatado.
    Combina seletores robustos (.sisbajud-label, labels flexíveis, TreeWalker)
    com fallbacks para dados_processo/numero_processo garantindo que nenhum campo fique vazio.
    """
    try:
        logger.info('[SISBAJUD] Executando script de coleta de dados da minuta...')

        proc_fallback = str(numero_processo or (dados_processo or {}).get('numero') or '')
        divida_obj = (dados_processo or {}).get('divida') if isinstance(dados_processo, dict) else {}
        valor_fallback = (divida_obj or {}).get('valor', '') if isinstance(divida_obj, dict) else ''

        reus_fallback = []
        if isinstance(dados_processo, dict) and dados_processo.get('reu'):
            for r in dados_processo['reu']:
                nome = r.get('nome', '')
                doc = r.get('cpfcnpj', '')
                if nome and doc:
                    reus_fallback.append(f"{nome} - [{doc}]")
                elif nome:
                    reus_fallback.append(nome)

        import json
        payload_fallback = json.dumps({
            'processo': proc_fallback,
            'valor': valor_fallback,
            'reus': reus_fallback
        }, ensure_ascii=False)

        script_coleta = f"""
        const fb = {payload_fallback};

        function getValueByLabel(targetText) {{
            if (!targetText) return null;
            const cleanTarget = targetText.replace(/[:\\s]+/g, ' ').trim().toLowerCase();

            // 1. .sisbajud-label
            const labels = Array.from(document.querySelectorAll('.sisbajud-label'));
            const targetLabel = labels.find(label => {{
                const txt = (label.textContent || '').replace(/[:\\s]+/g, ' ').trim().toLowerCase();
                return txt.includes(cleanTarget);
            }});
            if (targetLabel) {{
                const parentDiv = targetLabel.closest('.col-md-3') || targetLabel.parentElement;
                const valueElement = (parentDiv && parentDiv.querySelector('.sisbajud-label-valor'))
                    || targetLabel.parentElement.querySelector('.sisbajud-label-valor')
                    || targetLabel.nextElementSibling;
                if (valueElement && valueElement.textContent.trim()) {{
                    return valueElement.textContent.trim();
                }}
            }}

            // 2. Qualquer elemento label/span/strong contendo o texto
            const allSpans = Array.from(document.querySelectorAll('label, span, strong, dt, div'));
            for (let i = 0; i < allSpans.length; i++) {{
                const el = allSpans[i];
                const txt = (el.textContent || '').replace(/[:\\s]+/g, ' ').trim().toLowerCase();
                if (txt === cleanTarget || (txt.startsWith(cleanTarget) && txt.length < cleanTarget.length + 5)) {{
                    const nextVal = el.nextElementSibling || (el.parentElement && el.parentElement.querySelector('.sisbajud-label-valor'));
                    if (nextVal && nextVal.textContent.trim()) return nextVal.textContent.trim();
                }}
            }}
            return null;
        }}

        function extrairNumeroProcesso() {{
            const porLabel = getValueByLabel('Número do Processo')
                          || getValueByLabel('Número do processo')
                          || getValueByLabel('Processo');
            if (porLabel) {{
                const m = porLabel.match(/\\d{{7}}-\\d{{2}}\\.\\d{{4}}\\.\\d\\.\\d{{2}}\\.\\d{{4}}/);
                if (m) return m[0];
                const digits = porLabel.replace(/\\D/g, '');
                if (digits.length === 20) return porLabel.trim();
            }}

            try {{
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let node;
                while ((node = walker.nextNode())) {{
                    const m = node.nodeValue && node.nodeValue.match(/\\b\\d{{7}}-\\d{{2}}\\.\\d{{4}}\\.\\d\\.\\d{{2}}\\.\\d{{4}}\\b/);
                    if (m) return m[0];
                }}
            }} catch(e) {{}}

            const inp = document.querySelector('input[placeholder*="Processo"], input[formcontrolname*="processo"]');
            if (inp && inp.value) {{
                const m = inp.value.match(/\\d{{7}}-\\d{{2}}\\.\\d{{4}}\\.\\d\\.\\d{{2}}\\.\\d{{4}}/);
                if (m) return m[0];
                return inp.value.trim();
            }}

            return fb.processo || null;
        }}

        function extrairNumeroProtocolo() {{
            const porLabel = getValueByLabel('Número do Protocolo')
                          || getValueByLabel('Número do protocolo')
                          || getValueByLabel('Protocolo')
                          || getValueByLabel('Número da Ordem')
                          || getValueByLabel('Número da ordem')
                          || getValueByLabel('Número da Minuta')
                          || getValueByLabel('Número da minuta')
                          || getValueByLabel('Ordem')
                          || getValueByLabel('Minuta')
                          || getValueByLabel('ID');
            if (porLabel) {{
                const m = porLabel.match(/\\d{{6,25}}/);
                if (m) return m[0];
            }}

            const elProto = document.querySelector('.col-protocolo, [data-label*="protocolo"], [data-label*="Protocolo"]');
            if (elProto && elProto.textContent) {{
                const m = elProto.textContent.match(/\\d{{6,25}}/);
                if (m) return m[0];
            }}

            try {{
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let node;
                while ((node = walker.nextNode())) {{
                    const text = node.nodeValue || '';
                    const m = text.match(/(?:[Pp]rotocolo|[Nn]úmero da [Oo]rdem|[Mm]inuta)[\\s:]+(\\d{{6,25}})/);
                    if (m) return m[1];
                }}
            }} catch(e) {{}}

            const mUrl = window.location.href.match(/\\/(\\d{{6,}})/);
            if (mUrl) return mUrl[1];

            return porLabel ? porLabel.replace(/\\D/g, '') : null;
        }}

        function extrairValor() {{
            const elValor = document.querySelector('td[data-label="valorBloquear:"], td[data-label*="valor"], td.mat-column-valorBloquear');
            if (elValor && elValor.textContent.trim()) {{
                return elValor.textContent.trim().split('\\n')[0];
            }}
            const porLabel = getValueByLabel('Valor a ser bloqueado')
                          || getValueByLabel('Valor do bloqueio')
                          || getValueByLabel('Valor da dívida');
            if (porLabel) return porLabel;
            return fb.valor || null;
        }}

        function extrairExecutados() {{
            const executados = [];
            const rows = document.querySelectorAll('tr.element-row, tr.mat-row, mat-row');
            rows.forEach(row => {{
                const nomeElement = row.querySelector('.col-reu-dados-nome-pessoa, td.mat-column-identificacao, .mat-column-nome');
                const documentoElement = row.querySelector('.col-reu-dados a, a[href*="receita"], td.mat-column-cpfCnpj');
                if (nomeElement) {{
                    const nome = nomeElement.textContent.trim();
                    const documento = documentoElement ? documentoElement.textContent.trim() : '';
                    if (documento && !nome.includes('Qtde')) {{
                        executados.push(`${{nome}} - [${{documento}}]`);
                    }} else if (nome && !nome.includes('Qtde') && !nome.includes('Identificação')) {{
                        executados.push(nome);
                    }}
                }}
            }});
            if (executados.length > 0) return executados;
            return (fb.reus && fb.reus.length > 0) ? fb.reus : [];
        }}

        try {{
            const numeroProcesso = extrairNumeroProcesso();
            const numeroProtocolo = extrairNumeroProtocolo();
            const repeticaoProgramada = getValueByLabel('Repetição programada?') || getValueByLabel('Repetir ordem?') || 'Sim';

            let limiteRepeticao = null;
            const labelsData = Array.from(document.querySelectorAll('.sisbajud-label'));
            for (const lbl of labelsData) {{
                if ((lbl.textContent || '').toLowerCase().includes('data limite da repetição')) {{
                    const cont = lbl.closest('.col-md-3') || lbl.parentElement;
                    const v = cont ? cont.querySelector('.sisbajud-label-valor') : null;
                    if (v && v.textContent.trim()) {{
                        limiteRepeticao = v.textContent.trim();
                        break;
                    }}
                }}
            }}
            if (!limiteRepeticao) {{
                limiteRepeticao = getValueByLabel('Data limite da repetição:') || 'Não informado';
            }}

            const valorBloqueio = extrairValor();
            const executados = extrairExecutados();

            const pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"';

            let resultado = `<p ${{pStyle}}><strong>Dados da Teimosinha protocolada:</strong></p>`;
            resultado += `<p ${{pStyle}}>Número do processo: <strong>${{numeroProcesso || ''}}</strong></p>`;
            resultado += `<p ${{pStyle}}>Protocolo: <strong></strong></p>`;
            resultado += `<p ${{pStyle}}>Data limite da repetição: <strong>${{limiteRepeticao || ''}}</strong></p>`;
            resultado += `<p ${{pStyle}}>Valor do bloqueio: <strong>${{valorBloqueio || ''}}</strong></p>`;
            resultado += `<p ${{pStyle}}><strong>Partes alvo do bloqueio:</strong></p>`;

            if (executados.length > 0) {{
                executados.forEach(executado => {{
                    resultado += `<p ${{pStyle}}><strong>${{executado}}</strong></p>`;
                }});
            }} else {{
                resultado += `<p ${{pStyle}}><strong>Nenhum executado encontrado</strong></p>`;
            }}

            resultado += `<p ${{pStyle}}>Notas:</p>`;
            resultado += `<p ${{pStyle}}>-Por padrão é consultado CNPJ raiz.</p>`;
            resultado += `<p ${{pStyle}}>-Eventuais partes faltantes se referem a CPF ou CNPJ sem relacionamento bancário.</p>`;

            return resultado;

        }} catch (error) {{
            return 'ERRO: ' + error.message;
        }}
        """

        resultado = driver.execute_script(script_coleta)

        if resultado and not str(resultado).startswith('ERRO:'):
            logger.info('[SISBAJUD]  Dados da minuta coletados com sucesso')
            return resultado
        else:
            logger.info(f'[SISBAJUD]  Erro na coleta de dados: {resultado}')
            return None

    except Exception as e:
        logger.info(f'[SISBAJUD]  Falha ao executar script de coleta: {e}')
        return None


def minuta_bloqueio_60(driver, dados_processo=None, driver_pje=None, log=True, fechar_driver=True):
    """
    Wrapper para minuta_bloqueio com prazo de 60 dias.
    Chama minuta_bloqueio com prazo_dias=60.

    Args:
        Mesmos argumentos de minuta_bloqueio

    Returns:
        Mesmo retorno de minuta_bloqueio
    """
    return minuta_bloqueio(
        driver=driver,
        dados_processo=dados_processo,
        driver_pje=driver_pje,
        log=log,
        fechar_driver=fechar_driver,
        prazo_dias=60,
        protocolar=False
    )


def minuta_bloqueio_amanha(driver, dados_processo=None, driver_pje=None, log=True,
                           fechar_driver=True, prazo_dias=None):
    """
    Cria DUAS minutas de bloqueio no SISBAJUD no mesmo fluxo de forma independente.

    - 1ª minuta: prazo normal (30 ou 60 dias) - fluxo idêntico ao original.
    - 2ª minuta: navega para /minuta/cadastrar, preenche idêntico à 1ª (30 ou 60 dias),
                 mas marca "Agendar protocolo: Sim" com a data de amanhã.

    A juntada no PJe (se driver_pje fornecido) é feita UMA única vez ao final.
    """
    resultado = {
        'status': 'pendente',
        'minuta_1': None,
        'minuta_2': None,
        'juntada_executada': False,
        'erros': []
    }

    try:
        logger.info('\n[SISBAJUD] INICIANDO CRIAÇÃO DE MINUTA DE BLOQUEIO (DUPLA — AGENDADA PARA AMANHÃ)')
        logger.info('=' * 60)

        # 0. EXTRAIR / CARREGAR DADOS DO PROCESSO
        if dados_processo is None:
            if log:
                logger.info('[SISBAJUD] Extraindo dados do processo do PJe...')
            try:
                from Fix.extracao import extrair_dados_processo
                if driver_pje:
                    dados_processo = extrair_dados_processo(driver_pje)
                else:
                    from .utils import carregar_dados_processo
                    dados_processo = carregar_dados_processo()

                if not dados_processo:
                    if log:
                        logger.info('[SISBAJUD]  Falha ao extrair/carregar dados do processo')
                    resultado['status'] = 'erro'
                    resultado['erros'].append('Falha ao extrair/carregar dados do processo')
                    return resultado
            except Exception as e:
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao extrair dados do processo: {e}')
                resultado['status'] = 'erro'
                resultado['erros'].append(f'Erro ao extrair dados: {e}')
                return resultado

        # 1. VERIFICAR/GARANTIR VALOR (padrão 33,33 se ausente)
        divida = dados_processo.get('divida', {}) if dados_processo else {}
        valor = divida.get('valor')

        if not valor:
            valor_padrao = '33,33'
            if log:
                logger.info(f'[SISBAJUD]  Sem valor de bloqueio — usando padrão: R$ {valor_padrao}')
            if 'divida' not in dados_processo or not isinstance(dados_processo.get('divida'), dict):
                dados_processo['divida'] = {}
            dados_processo['divida']['valor'] = valor_padrao
            valor = valor_padrao

        # Detectar pendências de cálculo
        pendencia = None
        _data_divida = divida.get('data', '') if isinstance(divida, dict) else ''
        _usando_padrao = (valor == '33,33')

        if _usando_padrao:
            pendencia = 'sem_calculo'
            if log:
                logger.info('[SISBAJUD]  Pendência: sem cálculo (padrão 33,33)')
        elif _data_divida:
            try:
                from datetime import datetime as _dt
                _dt_divida = _dt.strptime(_data_divida, '%d/%m/%Y')
                if (_dt.now() - _dt_divida).days > 90:
                    pendencia = 'calculo_antigo'
                    if log:
                        logger.info(f'[SISBAJUD]  Pendência: cálculo de {_data_divida} (>3 meses)')
            except Exception:
                pass

        # 2. VALIDAR DADOS DO PROCESSO
        dados_validos, numero_processo = helpers._validar_dados(dados_processo)
        if not dados_validos:
            resultado['status'] = 'erro'
            resultado['erros'].append('Dados do processo inválidos ou insuficientes')
            return resultado

        # 3. PRAZO DAS MINUTAS
        if prazo_dias is None:
            prazo_dias = 30

        # =====================================================================
        # === 1ª MINUTA (idêntica ao normal) ===
        # =====================================================================
        logger.info(f'[SISBAJUD] === CRIANDO 1ª MINUTA (prazo {prazo_dias} dias) ===')

        # 3a. Navegar diretamente para /minuta/cadastrar (evita delay e refresh de listagem)
        URL_CADASTRAR = "https://sisbajud.cnj.jus.br/minuta/cadastrar"
        try:
            logger.info(f'[SISBAJUD] Navegando diretamente para cadastro de minuta: {URL_CADASTRAR}')
            driver.get(URL_CADASTRAR)
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, timeout=3)
        except Exception as e_nav:
            if log:
                logger.info(f'[SISBAJUD]  Erro ao navegar para /minuta/cadastrar: {e_nav}')

        # Fallback caso a rota direta não abra o formulário: clica em Nova Minuta
        if '/cadastrar' not in (driver.current_url or ''):
            sucesso_nova = _clicar_nova_minuta(driver, log)
            if not sucesso_nova:
                resultado['status'] = 'erro'
                resultado['erros'].append('1ª minuta: Botão "Nova Minuta" não encontrado')
                return resultado

        # 3b. Preencher campos iniciais (1ª minuta: prazo teimosinha, SEM agendar protocolo)
        agendar_m1 = False
        campos_ok = helpers._preencher_campos_iniciais(
            driver, dados_processo, prazo_dias,
            agendar_amanha=agendar_m1, agendar_offset=1
        )
        if not campos_ok:
            resultado['status'] = 'erro'
            resultado['erros'].append('1ª minuta: Falha ao preencher campos iniciais')
            return resultado

        # 3c. Processar réus — loteamento (máx. 10 válidos por minuta)
        todos_reus = dados_processo.get('reu', []) or []
        if len(todos_reus) > 10 and log:
            logger.info(
                '[SISBAJUD] ALERTA: %d reus excedem limite de 10 por minuta — '
                'serao distribuidos em lotes', len(todos_reus)
            )
            resultado['alerta_excesso_reus'] = True
            resultado['total_reus'] = len(todos_reus)

        resultado_reus_1 = helpers._processar_reus_otimizado(driver, todos_reus, max_validos=10)
        processados_ate = resultado_reus_1.get('processados_ate', len(todos_reus)) if isinstance(resultado_reus_1, dict) else len(todos_reus)
        reus_restantes = todos_reus[processados_ate:] if processados_ate < len(todos_reus) else []

        # 3d. Configurar valor
        _configurar_valor(driver, dados_processo)

        # 3e. Salvar
        minuta_1_salva = helpers._salvar_minuta(driver)
        if not minuta_1_salva:
            resultado['status'] = 'erro'
            resultado['erros'].append('1ª minuta: Falha ao salvar')
            return resultado

        logger.info('[SISBAJUD]  1ª minuta salva com sucesso')

        # 3f. PROTOColar 1ª minuta: desativado (teimosinhas são salvas sem protocolar direto no SISBAJUD)
        protocolo_1 = ""
        if log:
            logger.info('[SISBAJUD]  1ª minuta salva (sem protocolar — aguarda assinatura do magistrado)')

        # 3g. Coletar dados da 1ª minuta (relatório em memória, sem salvar clipboard)
        dados_rel_1 = helpers._gerar_relatorio_minuta(
            driver, numero_processo, dados_processo=dados_processo, salvar_clipboard=False
        )
        resultado['relatorio_minuta_1'] = (dados_rel_1 or {}).get('conteudo') if isinstance(dados_rel_1, dict) else None
        resultado['minuta_1'] = {
            'prazo_dias': prazo_dias,
            'protocolo': "",
            'relatorio_gerado': bool(dados_rel_1)
        }

        # =====================================================================
        # === 2ª MINUTA (prazo teimosinha normal + AGENDAMENTO para amanhã) ===
        # =====================================================================
        logger.info('[SISBAJUD] === CRIANDO 2ª MINUTA (agendamento dia seguinte) ===')

        # Navegar diretamente para /minuta/cadastrar
        URL_CADASTRAR = "https://sisbajud.cnj.jus.br/minuta/cadastrar"
        try:
            logger.info(f'[SISBAJUD] Navegando diretamente para cadastro da 2ª minuta: {URL_CADASTRAR}')
            driver.get(URL_CADASTRAR)
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, timeout=3)
            espera.ate_aparecer(driver, 'input[formcontrolname="numeroProcesso"], input[placeholder*="processo"]', teto=10)
        except Exception as e_nav:
            if log:
                logger.info(f'[SISBAJUD]  Erro ao navegar para /minuta/cadastrar: {e_nav}')
            resultado['erros'].append(f'2ª minuta: erro ao navegar: {e_nav}')

        # Fallback caso a rota direta não abra o formulário: clica em Nova Minuta
        if '/cadastrar' not in (driver.current_url or ''):
            sucesso_nova = _clicar_nova_minuta(driver, log)
            if not sucesso_nova:
                resultado['erros'].append('2ª minuta: Botão "Nova Minuta" não encontrado')

        # 4b. Preencher campos (mesmo prazo, MAS com agendar_amanha=True)
        campos_ok_2 = False
        try:
            from .processamento.minutas_campos import _preencher_campos_iniciais as preencher_campos_atualizado
            agendar_m2 = True  # sempre agenda a 2ª minuta; offset depende de pendencia
            offset_m2 = 2 if pendencia == 'sem_calculo' else 1
            campos_ok_2 = preencher_campos_atualizado(
                driver, dados_processo, prazo_dias=prazo_dias,
                agendar_amanha=agendar_m2, agendar_offset=offset_m2
            )
        except Exception as e_kwargs:
            if log:
                logger.info(f'[SISBAJUD] Erro ao preencher campos da 2ª minuta com agendar_amanha: {e_kwargs}')

        if not campos_ok_2:
            if log:
                logger.info('[SISBAJUD]  2ª minuta: Falha ao preencher campos — pulando')
            resultado['erros'].append('2ª minuta: Falha ao preencher campos')
        else:
            # 4c. Processar réus restantes (se houver)
            if reus_restantes:
                if log:
                    logger.info(
                        '[SISBAJUD] Processando %d reus restantes na 2ª minuta',
                        len(reus_restantes)
                    )
                helpers._processar_reus_otimizado(driver, reus_restantes, max_validos=10)
            else:
                helpers._processar_reus_otimizado(driver, todos_reus, max_validos=10)

            # 4d. Configurar valor
            _configurar_valor(driver, dados_processo)

            # 4e. Salvar
            minuta_2_salva = helpers._salvar_minuta(driver)
            if minuta_2_salva:
                logger.info('[SISBAJUD]  2ª minuta salva com sucesso')

                # 4f. PROTOColar 2ª minuta: desativado (teimosinhas são salvas sem protocolar direto no SISBAJUD)
                protocolo_2 = ""
                if log:
                    logger.info('[SISBAJUD]  2ª minuta salva (sem protocolar — aguarda assinatura do magistrado)')

                dados_rel_2 = helpers._gerar_relatorio_minuta(
                    driver, numero_processo, dados_processo=dados_processo, salvar_clipboard=False
                )
                resultado['relatorio_minuta_2'] = (dados_rel_2 or {}).get('conteudo') if isinstance(dados_rel_2, dict) else None

                resultado['minuta_2'] = {
                    'prazo_dias': prazo_dias,
                    'protocolo': "",
                    'salva': True
                }
            else:
                if log:
                    logger.info('[SISBAJUD]  2ª minuta: falha ao salvar — prosseguindo para juntada')
                resultado['erros'].append('2ª minuta: falha ao salvar')
                resultado['minuta_2'] = {'prazo_dias': prazo_dias, 'salva': False}

        # =====================================================================
        # === CONSOLIDAR RELATÓRIO COM TODOS OS RÉUS (após a 2ª minuta) ===
        # =====================================================================
        # Gera o relatório consolidado e salva no clipboard após a 2ª minuta.
        # Os campos de protocolo ficam vazios (<strong></strong>), pois são minutas ainda não protocoladas.
        if todos_reus and (dados_rel_1 or minuta_1_salva or resultado.get('minuta_2', {}).get('salva')):
            # Determinar data limite da repetição da 2ª minuta na página final pós-salvamento
            data_limite_calc = None
            try:
                val_limite = driver.execute_script("""
                    const labels = Array.from(document.querySelectorAll('.sisbajud-label'));
                    for (const lbl of labels) {
                        const txt = (lbl.textContent || '').trim().toLowerCase();
                        if (txt.includes('data limite da repetição') || txt.includes('data limite')) {
                            const container = lbl.closest('.col-md-3') || lbl.parentElement;
                            const val = container ? container.querySelector('.sisbajud-label-valor') : null;
                            if (val && val.textContent.trim()) {
                                return val.textContent.trim();
                            }
                        }
                    }
                    const todosValores = Array.from(document.querySelectorAll('.sisbajud-label-valor'));
                    for (const v of todosValores) {
                        const t = (v.textContent || '').trim();
                        if (/^\\d{2}\\/\\d{2}\\/\\d{4}$/.test(t)) {
                            return t;
                        }
                    }
                    return null;
                """)
                if val_limite:
                    data_limite_calc = str(val_limite).strip()
            except Exception:
                pass

            if not data_limite_calc:
                prazo_base = prazo_dias if prazo_dias in (30, 60) else 30
                data_limite_calc = (datetime.now() + timedelta(days=prazo_base + 1)).strftime('%d/%m/%Y')

            def _fmt_doc(doc_str):
                nums = ''.join(filter(str.isdigit, str(doc_str or '')))
                if len(nums) == 11:
                    return f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"
                elif len(nums) == 14:
                    return f"{nums[:2]}.{nums[2:5]}.{nums[5:8]}/{nums[8:12]}-{nums[12:]}"
                return str(doc_str or '').strip()

            pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
            consolidado = f'<p {pStyle}><strong>Dados da Teimosinha protocolada:</strong></p>'
            consolidado += f'<p {pStyle}>Número do processo: <strong>{numero_processo}</strong></p>'
            consolidado += f'<p {pStyle}>Protocolo: <strong></strong></p>'
            consolidado += f'<p {pStyle}>Data limite da repetição: <strong>{data_limite_calc}</strong></p>'

            valor_exibicao = valor
            if pendencia == 'sem_calculo':
                valor_exibicao = '(ver planilha mais recente)'
            consolidado += f'<p {pStyle}>Valor do bloqueio: <strong>{valor_exibicao}</strong></p>'
            consolidado += f'<p {pStyle}><strong>Partes alvo do bloqueio:</strong></p>'

            for reu in todos_reus:
                nome = reu.get('nome', '')
                doc = reu.get('cpfcnpj', '')
                if nome:
                    doc_formatado = _fmt_doc(doc)
                    if doc_formatado:
                        consolidado += f'<p {pStyle}><strong>{nome} - {doc_formatado}</strong></p>'
                    else:
                        consolidado += f'<p {pStyle}><strong>{nome}</strong></p>'

            consolidado += f'<p {pStyle}>Notas:</p>'
            consolidado += f'<p {pStyle}>-Por padrão é consultado CNPJ raiz.</p>'
            consolidado += f'<p {pStyle}>-Partes sem relacionamento bancário são '
            consolidado += f'automaticamente removidas pelo sistema (0 contas/recuperação judicial).</p>'

            resultado['relatorio_consolidado'] = consolidado
            try:
                from PEC.anexos import salvar_conteudo_clipboard
                salvar_conteudo_clipboard(
                    conteudo=consolidado,
                    numero_processo=numero_processo,
                    tipo_conteudo="sisbajud_minuta",
                    debug=log
                )
                if log:
                    logger.info('[SISBAJUD]  Relatório consolidado salvo no clipboard com %d reclamadas (apenas na 2ª minuta)', len(todos_reus))
            except Exception as e_cons:
                if log:
                    logger.info(f'[SISBAJUD]  Aviso: erro ao salvar relatório consolidado no clipboard: {e_cons}')
        elif dados_rel_1 and isinstance(dados_rel_1, dict) and dados_rel_1.get('conteudo'):
            # Fallback caso a 2ª minuta não tenha executado
            try:
                from PEC.anexos import salvar_conteudo_clipboard
                salvar_conteudo_clipboard(
                    conteudo=dados_rel_1['conteudo'],
                    numero_processo=numero_processo,
                    tipo_conteudo="sisbajud_minuta",
                    debug=log
                )
            except Exception:
                pass

        # =====================================================================
        # === JUNTADA NO PJe (única, ao final de ambas as minutas) ===
        # =====================================================================
        juntada_executada = False
        if (dados_rel_1 or minuta_1_salva or resultado.get('minuta_2', {}).get('salva')) and driver_pje:
            try:
                # Garantir foco na aba /detalhe do PJe
                aba_detalhe = None
                for handle in list(driver_pje.window_handles):
                    try:
                        driver_pje.switch_to.window(handle)
                        url = driver_pje.current_url or ''
                        if '/detalhe' in url:
                            aba_detalhe = handle
                            break
                    except Exception:
                        continue

                if aba_detalhe:
                    try:
                        driver_pje.switch_to.window(aba_detalhe)
                    except Exception:
                        pass

                # Executar juntada (modelo xteim)
                from PEC.anexos import anex_sisbconsulta
                if log:
                    logger.info('[SISBAJUD] Executando juntada da minuta no PJe (modelo xteim)...')
                juntada_executada = anex_sisbconsulta(driver_pje, numero_processo, debug=log, modelo='xteim')
                resultado['juntada_executada'] = bool(juntada_executada)

                # Visibilidade + GIGS
                if juntada_executada:
                    from atos.wrappers_utils import executar_visibilidade_sigilosos_se_necessario
                    vis_ok = executar_visibilidade_sigilosos_se_necessario(driver_pje, True, debug=log)
                    resultado['visibilidade_certidao_sigilosa'] = bool(vis_ok)

                    from Fix.extracao import criar_gigs, criar_comentario
                    gigs_prazo = '60' if prazo_dias == 60 else '22'
                    if pendencia == 'calculo_antigo':
                        gigs_str = f'{gigs_prazo}/xs resultado CALC'
                    else:
                        gigs_str = f'{gigs_prazo}/xs resultado'
                    if log:
                        logger.info(f'[SISBAJUD] Criando GIGS {gigs_str}...')
                    resultado_gigs = criar_gigs(driver_pje, gigs_str, log=log)

                    if pendencia == 'sem_calculo':
                        if log:
                            logger.info('[SISBAJUD] Criando comentário "Bruna - Atualizar"...')
                        criar_comentario(driver_pje, 'Bruna - Atualizar', log=log)
            except Exception as e_junt:
                resultado['erros'].append(f'Erro na juntada PJE: {e_junt}')
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao executar juntada: {e_junt}')

        # =====================================================================
        # === FECHAR DRIVER ===
        # =====================================================================
        if fechar_driver:
            try:
                driver.quit()
            except Exception as e:
                pass

        resultado['status'] = 'concluido'
        resultado['pendencia'] = pendencia
        if log:
            logger.info('[SISBAJUD]  Fluxo duplo de minutas concluído')

        return resultado

    except Exception as e:
        erro = f'Erro geral na criação de minuta dupla: {str(e)}'
        if log:
            logger.info(f'[SISBAJUD]  {erro}')
        resultado['status'] = 'erro'
        resultado['erros'].append(erro)

        if fechar_driver:
            try:
                driver.quit()
            except Exception:
                pass

        return resultado


def _clicar_nova_minuta(driver, log=True):
    """
    Helper interno: clica no botão 'Nova Minuta' e aguarda o formulário carregar.
    """
    try:
        from SISB.processamento.series_navegar import dispensar_dialog_ordem_pendente
        dispensar_dialog_ordem_pendente(driver, log=log, timeout=1.0)
    except Exception:
        pass

    script_nova_minuta = """
    var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
    if (!botaoNova) {
        botaoNova = document.querySelector('button.mat-fab.mat-primary');
    }
    if (botaoNova) {
        if (botaoNova.tagName === 'MAT-ICON') {
            botaoNova = botaoNova.closest('button');
        }
        botaoNova.click();
        return true;
    }
    return false;
    """
    sucesso = driver.execute_script(script_nova_minuta)
    if sucesso:
        try:
            espera.ate_aparecer(driver, 'input[placeholder*="Juiz"], .mat-form-field, form', teto=10)
        except Exception:
            pass
    return bool(sucesso)


