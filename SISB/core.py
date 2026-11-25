"""SISB/core.py — Inicialização, autenticação e orquestração de minutas/ordens SISBAJUD."""

import base64
import json
import logging
import os
import random
import time
import unicodedata
from datetime import datetime, timedelta

from Fix import espera
from Fix.core import aguardar_renderizacao_nativa, preencher_campo, safe_click_no_scroll
from Fix.driver_factory import criar_driver_sisb_pc as criar_driver_sisb
from Fix.driver_factory import criar_driver_sisb_vt
from Fix.extracao import criar_comentario, criar_gigs, extrair_dados_processo
from . import helpers, utils
from .processamento_campos import _configurar_valor

logger = logging.getLogger(__name__)


def _exec_js(driver, script, *args):
    return espera._executar_script(driver, script, *args)


def _abas(driver):
    return list(getattr(driver, 'window' + '_handles', []))

def simular_movimento_humano(driver, elemento=None):
    """Simula movimento de mouse humano antes de clicar em elemento"""
    try:
        if hasattr(driver, 'page') and hasattr(driver.page, 'mouse'):
            driver.page.mouse.move(random.randint(100, 700), random.randint(100, 500))
    except Exception as e:
        _ = e

processo_dados_extraidos = None


# Token Storage: SISBAJUD (localStorage) - Reutilização de sessão

def _extrair_jwt_exp_sisbajud(token_value: str) -> int:
    """Extrai campo 'exp' do JWT SISBAJUD."""
    try:
        partes = token_value.split('.')
        if len(partes) < 2:
            return 0
        payload_b64 = partes[1]
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
        payload_dict = json.loads(payload_json)
        return int(payload_dict.get('exp', 0))
    except Exception as e:
        logger.debug(f'[SISBAJUD][TOKEN] Erro ao extrair exp: {e}')
        return 0


def salvar_tokens_sisbajud(driver) -> bool:
    """Salva tokens SISBAJUD do localStorage para arquivo JSON."""
    try:
        access_token = _exec_js(driver, 
            "return localStorage.getItem('sisbajud-token') || localStorage.getItem('LS.sisbajud-token');"
        )
        refresh_token = _exec_js(driver, 
            "return localStorage.getItem('sisbajud-refresh-token') || localStorage.getItem('LS.sisbajud-refresh-token');"
        )

        if not access_token:
            logger.debug('[SISBAJUD][TOKEN] Nenhum access_token encontrado em localStorage')
            return False

        access_token_exp = _extrair_jwt_exp_sisbajud(access_token)
        if access_token_exp <= 0:
            logger.warning('[SISBAJUD][TOKEN] Nao consegui extrair exp do access_token')
            return False

        home = os.path.expanduser('~')
        config_dir = os.path.join(home, '.pjeplus')
        os.makedirs(config_dir, exist_ok=True)
        token_file = os.path.join(config_dir, 'sisbajud_tokens.json')

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
    """Carrega e valida tokens SISBAJUD salvos."""
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
    """Injeta tokens SISBAJUD em localStorage do driver."""
    try:
        for dom in ['https://sisbajud.cnj.jus.br/', 'https://sisbajud.pdpj.jus.br/']:
            try:
                driver.get(dom)
                espera.assentar(driver, 0.5)
                _exec_js(driver, """
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


# Verificação de Autenticação e Sessão SISBAJUD

def is_tela_login_sisbajud(driver) -> bool:
    """Identifica de forma conclusiva se o driver SISBAJUD está na tela de login"""
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

        seletores_login = (
            '#username, input[name="username"], '
            '#password, input[name="password"], '
            '#kc-login, #kc-form-login, #kc-page-title, '
            '#otp, input[name="otp"], '
            'form[action*="/auth/realms/"]'
        )
        if espera.ate_aparecer(driver, seletores_login, teto=0.5):
            return True

        try:
            is_landing_login = _exec_js(driver, """
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
    """Verifica se há uma sessão autenticada REAL e ATIVA no SISBAJUD."""
    try:
        cur_url = (getattr(driver, 'current_url', '') or '').lower()
        cur_path = cur_url.split('?')[0]
        if any(k in cur_path for k in ('sso.cloud', '/realms/', 'openid-connect', 'login-actions')):
            return False
        if espera.ate_aparecer(driver, '#otp, input[name="otp"]', teto=0.2):
            return False

        if not any(h in cur_url for h in ['sisbajud.cnj.jus.br', 'sisbajud.pdpj.jus.br']):
            return False

        try:
            token_valido = _exec_js(driver, """
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

        seletores_autenticado = (
            'div.breadcrumb breadcrumb, '
            'sisbajud-dialog-aviso-ordem-pendente, '
            'sisbajud-cadastro-minuta, '
            'sisbajud-detalhes-teimosinha, '
            'a[href*="/minuta"], a[routerlink*="/minuta"], '
            'a[href*="/teimosinha"], a[routerlink*="/teimosinha"], '
            'button[mat-menu-item]'
        )
        if espera.ate_aparecer(driver, seletores_autenticado, teto=0.5):
            return True

        try:
            _bc = _exec_js(driver, "return !!document.querySelector('div.breadcrumb breadcrumb');")
            _txt = _exec_js(driver, 
                "return (document.body ? document.body.innerText : '').replace(/\\s+/g, ' ').slice(0, 100);"
            )
        except Exception as e_diag:
            _bc, _txt = f'erro: {e_diag}', ''
        logger.info('[SISBAJUD][SESSION_CHECK] sem prova positiva — url=%s | breadcrumb=%s | texto=%r',
                    cur_url, _bc, _txt)
        return False
    except Exception as e:
        logger.debug(f'[SISBAJUD][SESSION_CHECK] Erro ao checar sessão ativa: {e}')
        return False


# Sessão / Cookies SISBAJUD — evita novo OTP entre execuções

USAR_COOKIES_AUTOMATICO = True
SALVAR_COOKIES_AUTOMATICO = True


def _arquivo_sessao_sisbajud() -> str:
    config_dir = os.path.join(os.path.expanduser('~'), '.pjeplus')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'sisbajud_sessao.json')


def salvar_cookies_sisbajud(driver, caminho_arquivo=None, info_extra=None) -> bool:
    """Salva todos os cookies e localStorage da sessão SISBAJUD em arquivo JSON."""
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

        if not dados['origins']:
            try:
                cur_token = _exec_js(driver, "return localStorage.getItem('sisbajud-token') || localStorage.getItem('LS.sisbajud-token');")
                cur_refresh = _exec_js(driver, "return localStorage.getItem('sisbajud-refresh-token') || localStorage.getItem('LS.sisbajud-refresh-token');")
                if cur_token:
                    ls_items = [{'name': 'sisbajud-token', 'value': cur_token}]
                    if cur_refresh:
                        ls_items.append({'name': 'sisbajud-refresh-token', 'value': cur_refresh})
                    dados['origins'] = [{'origin': 'https://sisbajud.pdpj.jus.br', 'localStorage': ls_items}]
            except Exception:
                pass

        # estiver lá, sem isto o reaproveitamento nunca funciona.
        try:
            ss = _exec_js(driver, 
                "const o = {}; for (let i = 0; i < sessionStorage.length; i++) {"
                " const k = sessionStorage.key(i); o[k] = sessionStorage.getItem(k); } return o;"
            ) or {}
            dados['session_storage'] = [{'origin': 'https://sisbajud.cnj.jus.br', 'items': ss}]
            logger.info('[SISBAJUD][COOKIES] storage salvo — localStorage=%s | sessionStorage=%s',
                        [i.get('name') for o in dados.get('origins', [])
                         for i in (o.get('localStorage') or [])][:12],
                        list(ss.keys())[:12])
        except Exception:
            dados['session_storage'] = []

        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
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
    """Carrega cookies e sessão SISBAJUD mais recentes e válidos automaticamente."""
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
                    if item.get('expires') is None:
                        item.pop('expires', None)
                    pw_cookies.append(item)
                contexto.add_cookies(pw_cookies)
            except Exception as e:
                logger.warning(f'[SISBAJUD][COOKIES] contexto.add_cookies falhou: {e}')

        origins = dados.get('origins', [])
        itens_restaurar = []
        for origem in origins:
            itens_restaurar.extend(origem.get('localStorage') or [])

        if itens_restaurar:
            for dominio_alvo in ['https://sisbajud.cnj.jus.br/', 'https://sisbajud.pdpj.jus.br/']:
                try:
                    driver.get(dominio_alvo)
                    for item in itens_restaurar:
                        _exec_js(driver, 
                            "localStorage.setItem(arguments[0], arguments[1]);",
                            item['name'], item['value']
                        )
                except Exception:
                    pass

        for bloco in dados.get('session_storage') or []:
            try:
                driver.get(bloco.get('origin') or 'https://sisbajud.cnj.jus.br/')
                for k, v in (bloco.get('items') or {}).items():
                    _exec_js(driver, 
                        "sessionStorage.setItem(arguments[0], arguments[1]);", k, v
                    )
            except Exception:
                pass

        # (sisbajud.cnj.jus.br/) não tem breadcrumb e reprovava sessão válida.
        driver.get('https://sisbajud.cnj.jus.br/minuta')
        espera.assentar(driver, 2)

        if espera.ate_aparecer(driver, 'div.breadcrumb breadcrumb', teto=8) or is_sessao_ativa_sisbajud(driver):
            logger.info(f'[SISBAJUD][COOKIES] Sessão ativa confirmada a partir de {os.path.basename(arquivo_mais_recente)}! Login reaproveitado.')
            return True

        logger.info('[SISBAJUD][COOKIES] Sessão não reaproveitada após carregar %s (url=%s) — seguindo para login',
                    os.path.basename(arquivo_mais_recente), getattr(driver, 'current_url', ''))
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
    """Cria o driver para SISBAJUD usando a fábrica definida em driver_config."""
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
    """Login SISBAJUD na URL de minuta com confirmação estrita:"""
    try:
        from Fix import espera
        from Fix.utils import obter_credencial

        cpf = obter_credencial('SISB_CPF', servicos=('sisbajud', 'pjeplus', 'SISB'), aliases=('BP_SISB', 'PJE_USER', 'PJE_CPF'))
        senha = obter_credencial('SISB_SENHA', servicos=('sisbajud', 'pjeplus', 'SISB'), aliases=('BP_PASS', 'PJE_SENHA', 'PJE_PASSWORD'))

        URL_MINUTA = 'https://sisbajud.cnj.jus.br/minuta'
        # sisbajud.pdpj.jus.br/ e o fluxo vai direto para /minuta — por isso o tratamento
        SEL_MINUTAS = 'div.breadcrumb breadcrumb a.mat-button, div.breadcrumb breadcrumb'
        logger.info('[SISBAJUD][LOGIN] Navegando para URL certa: %s', URL_MINUTA)
        driver.get(URL_MINUTA)

        def _verificar_estado(d):
            u = (getattr(d, 'current_url', '') or '').lower()
            if any(k in u for k in ('sso.cloud', '/realms/', 'openid-connect', '/login', '/autenticacao')):
                return 'sso'
            p = getattr(d, 'page', None)
            if p:
                try:
                    if p.locator('#username, input[name="username"], #kc-login').first.is_visible():
                        return 'sso'
                    if p.locator('button.mat-fab, mat-toolbar, sisbajud-cadastro-minuta').first.is_visible():
                        return 'autenticado'
                except Exception:
                    pass
            return None

        estado = espera.ate(driver, _verificar_estado, teto=8)
        if estado == 'autenticado':
            logger.info('[SISBAJUD][LOGIN] Sessão já ativa na URL /minuta!')
        else:
            logger.info('[SISBAJUD][LOGIN] Aguardando tela de autenticação SSO...')
            tem_form = espera.ate_aparecer(driver, '#username, input[name="username"]', teto=8)
            if tem_form:
                if not cpf or not senha:
                    logger.warning('[SISBAJUD][LOGIN] Credenciais não encontradas no Windows Credential Manager')
                    return False

                logger.info('[SISBAJUD][LOGIN] Preenchendo credenciais...')
                preenchido = False
                p = getattr(driver, 'page', None)
                if p:
                    try:
                        p.fill('#username', str(cpf), timeout=1500)
                        p.fill('#password', str(senha), timeout=1500)
                        preenchido = True
                    except Exception:
                        pass
                if not preenchido:
                    preencher_campo(driver, '#username, input[name="username"]', str(cpf))
                    espera.assentar(driver, 0.2)
                    preencher_campo(driver, '#password, input[name="password"]', str(senha))

                espera.assentar(driver, 0.3)
                logger.info('[SISBAJUD][LOGIN] Clicando em login...')
                clicado = False
                if p:
                    try:
                        p.click('#kc-login', timeout=3000)
                        clicado = True
                    except Exception:
                        pass
                if not clicado:
                    try:
                        safe_click_no_scroll(driver, '#kc-login')
                        clicado = True
                    except Exception:
                        pass

            if espera.ate_aparecer(driver, '#otp, input[name="otp"]', teto=4):
                from Fix.sessao import obter_totp_sisbajud

                codigo_otp = obter_totp_sisbajud()
                if codigo_otp:
                    logger.info('[SISBAJUD][LOGIN] OTP gerado automaticamente via TOTP (Windows Credential Manager).')
                    p = getattr(driver, 'page', None)
                    preenchido_otp = False
                    if p:
                        try:
                            p.fill('#otp, input[name="otp"]', codigo_otp, timeout=3000)
                            preenchido_otp = True
                        except Exception:
                            pass
                    if not preenchido_otp:
                        preencher_campo(driver, '#otp, input[name="otp"]', codigo_otp)
                    submetido = False
                    if p:
                        try:
                            btn_sub = p.locator('#kc-login, input[type="submit"], button[type="submit"]')
                            if btn_sub.count() > 0 and btn_sub.first.is_visible():
                                btn_sub.first.click()
                                submetido = True
                        except Exception:
                            pass
                        if not submetido:
                            try:
                                p.locator('#otp, input[name="otp"]').first.press('Enter')
                                submetido = True
                            except Exception:
                                pass
                    if not submetido:
                        try:
                            safe_click_no_scroll(driver, 'input[type="submit"], button[type="submit"], #kc-login')
                        except Exception:
                            pass
                else:
                    logger.info('[SISBAJUD][LOGIN] OTP / 2FA detectado — por favor, insira o código no navegador...')

            logger.info('[SISBAJUD][LOGIN] Aguardando confirmação do login...')

            _visto = {'t0': time.monotonic(), 'dump': False}

            def _login_confirmado(d):
                handles = list(getattr(d, 'window_handles', []))
                for h in reversed(handles):
                    try:
                        d.switch_to.window(h)
                        u_path = (getattr(d, 'current_url', '') or '').lower().split('?')[0]
                        em_sso = any(k in u_path for k in ('sso.cloud', '/realms/', 'openid-connect', 'login-actions'))
                        if u_path != _visto.get('url'):
                            _visto['url'] = u_path
                            logger.info('[SISBAJUD][LOGIN] estado: url=%s | sso=%s', u_path, em_sso)
                        if em_sso or espera.ate_aparecer(d, '#otp, input[name="otp"]', teto=0.2):
                            continue
                        # Só rota /minuta do SISBAJUD (a URL do SSO traz /minuta apenas na query)
                        if not any(k in u_path for k in ('sisbajud.cnj.jus.br', 'sisbajud.pdpj.jus.br')):
                            continue
                        if '/minuta' not in u_path:
                            continue
                        if not _visto['dump'] and (time.monotonic() - _visto['t0']) > 8:
                            _visto['dump'] = True
                            try:
                                info = _exec_js(d, """
                                    return {
                                        titulo: document.title,
                                        url: location.href,
                                        texto: (document.body ? document.body.innerText : '').replace(/\\s+/g, ' ').slice(0, 300),
                                        custom: Array.from(new Set(Array.from(document.querySelectorAll('*'))
                                            .map(e => e.tagName.toLowerCase())
                                            .filter(t => t.includes('-')))).slice(0, 30),
                                        breadcrumb: !!document.querySelector('div.breadcrumb breadcrumb'),
                                        storage: Object.keys(localStorage).slice(0, 15)
                                    };
                                """)
                                logger.info('[SISBAJUD][LOGIN][DUMP] %s', info)
                            except Exception as e_dump:
                                logger.warning('[SISBAJUD][LOGIN][DUMP] falhou: %s', e_dump)
                        if is_sessao_ativa_sisbajud(d):
                            logger.info('[SISBAJUD][LOGIN] prova: sessão ativa (JWT/DOM autenticado)')
                            return True
                        if espera.ate_aparecer(d, SEL_MINUTAS, teto=0.5):
                            logger.info('[SISBAJUD][LOGIN] prova: breadcrumb "Minutas Pendentes" (listagem pronta)')
                            return True
                    except Exception:
                        continue
                return False

            resultado_login = espera.ate(driver, _login_confirmado, teto=120)
            if not resultado_login:
                logger.error('[SISBAJUD][LOGIN] ✗ Timeout aguardando login. URL final: %s', getattr(driver, 'current_url', ''))
                return False

            logger.info('[SISBAJUD][LOGIN] ✓ Login confirmado! URL atual: %s', getattr(driver, 'current_url', ''))

            u_atual = (getattr(driver, 'current_url', '') or '').lower()
            if any(k in u_atual for k in ('sso.cloud', '/realms/', 'openid-connect', 'login-actions')):
                logger.error('[SISBAJUD][LOGIN] ✗ Ainda no SSO (%s) — não navegar (abortaria o OTP)', u_atual)
                return False
            if '/minuta' not in u_atual.split('?')[0]:
                logger.info('[SISBAJUD][LOGIN] Navegando para %s...', URL_MINUTA)
                driver.get(URL_MINUTA)
                def _url_minuta_ok(d):
                    return '/minuta' in (getattr(d, 'current_url', '') or '').lower().split('?')[0]
                espera.ate(driver, _url_minuta_ok, teto=15)
                logger.info('[SISBAJUD][LOGIN] ✓ URL /minuta pronta: %s', getattr(driver, 'current_url', ''))

        logger.info('[SISBAJUD][LOGIN] ✓ Login completado — listagem /minuta pronta')
        return True

    except Exception as e_login:
        logger.error('[SISBAJUD][LOGIN] Erro durante login SISBAJUD: %s', e_login)
        return False


def login_manual_sisbajud(driver, aguardar_url_final=True):
    """Login MANUAL para SISBAJUD - Aguarda usuário fazer login manualmente na tela"""
    try:
        logger.info('[SISBAJUD][LOGIN_MANUAL] Iniciando login manual...')

        logger.info('[SISBAJUD][LOGIN_MANUAL] Navegando para SISBAJUD...')
        driver.get('https://sisbajud.cnj.jus.br/')
        espera.assentar(driver, 2)

        if aguardar_url_final:
            logger.info('[SISBAJUD][LOGIN_MANUAL] Aguardando login manual e URL correta...')
            def url_ok(d):
                url = (d.current_url or '').lower()
                # Aceita: /minuta, /bloqueio, ou sisbajud.cnj sem /login
                if '/minuta' in url or '/bloqueio' in url:
                    return True
                if 'sisbajud.cnj.jus.br' in url and ('/login' not in url and '/auth' not in url):
                    return True
                return False

            espera.ate(driver, url_ok, teto=300)
            logger.info('[SISBAJUD][LOGIN_MANUAL] ✓ URL carregada: %s', driver.current_url)
        else:
            logger.info('[SISBAJUD][LOGIN_MANUAL] Aguardando sem validar URL final...')
            espera.assentar(driver, 5)

        try:
            from SISB.processamento.series_navegar import dispensar_dialog_ordem_pendente
            dispensar_dialog_ordem_pendente(driver, log=False, timeout=2.0)
        except Exception:
            pass

        logger.info('[SISBAJUD][LOGIN_MANUAL] ✓ Login manual completado!')
        return True

    except Exception as e:
        logger.error('[SISBAJUD][LOGIN_MANUAL] Erro durante login manual: %s', e)
        return False


def salvar_dados_processo_temp(params_adicionais=None):
    """Salva dados do processo no arquivo do projeto (dadosatuais.json) para integração entre janelas"""
    try:
        project_path = os.path.dirname(os.path.abspath(__file__))  # Pasta onde está o sisbajud.py
        dados_path = os.path.join(project_path, 'dadosatuais.json')

        dados_para_salvar = processo_dados_extraidos.copy()
        if params_adicionais:
            dados_para_salvar['parametros_automacao'] = params_adicionais
            logger.info(f'[SISBAJUD] Parâmetros de automação adicionados: {params_adicionais}')

        with open(dados_path, 'w', encoding='utf-8') as f:
            json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
        logger.info(f'[SISBAJUD] Dados do processo salvos em: {dados_path}')
    except Exception as e:
        logger.info(f'[SISBAJUD][ERRO] Falha ao salvar dados do processo: {e}')


def iniciar_sisbajud(driver_pje=None, extrair_dados=False):
    """Função unificada de inicialização do SISBAJUD:"""
    global processo_dados_extraidos

    try:
        logger.info('[SISBAJUD] ============================================')
        logger.info('[SISBAJUD] Iniciando sessão SISBAJUD...')
        logger.info(f'[SISBAJUD][DEBUG] extrair_dados={extrair_dados}, driver_pje presente={driver_pje is not None}')
        logger.info('[SISBAJUD] ============================================')

        if extrair_dados and driver_pje:
            logger.info('[SISBAJUD] Extraindo dados do processo PJe...')
            processo_dados_extraidos = extrair_dados_processo(driver_pje)
            if processo_dados_extraidos:
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
        login_recem_confirmado = False

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

        if not login_ok:
            logger.info('[SISBAJUD] Executando login automático via CPF...')
            login_ok = login_automatico_sisbajud(driver)
            if login_ok:
                login_recem_confirmado = True
                logger.info('[SISBAJUD] Login automático concluído com sucesso!')
                try:
                    salvar_tokens_sisbajud(driver)
                except Exception:
                    pass
                if SALVAR_COOKIES_AUTOMATICO:
                    try:
                        espera.ate_aparecer(driver, 'div.breadcrumb breadcrumb', teto=5)
                        espera.assentar(driver, 1.0)
                        salvar_cookies_sisbajud(driver, info_extra='login_automatico_sisbajud')
                    except Exception as e:
                        logger.debug(f'[SISBAJUD] Falha ao salvar cookies: {e}')

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

        if login_recem_confirmado:
            logger.info('[SISBAJUD] Sessão confirmada pela listagem /minuta — seguindo sem revalidar')
        else:
            if not is_sessao_ativa_sisbajud(driver):
                espera.ate(driver, is_sessao_ativa_sisbajud, teto=10)

            if not is_sessao_ativa_sisbajud(driver):
                logger.error('[SISBAJUD] Sessão ativa não confirmada após fluxo de autenticação')
                try:
                    driver.quit()
                except Exception:
                    pass
                return None

        try:
            driver.maximize_window()
            logger.info('[SISBAJUD]  Janela maximizada')
        except Exception as e:
            logger.info(f'[SISBAJUD]  Não foi possível maximizar a janela: {e}')

        logger.info('[SISBAJUD] Verificando e dispensando dialog inicial (ordens pendentes)...')
        try:
            from SISB.processamento.series_navegar import dispensar_dialog_ordem_pendente
            dispensar_dialog_ordem_pendente(driver, log=True, timeout=0.0)
        except Exception as e_dlg:
            logger.debug(f'[SISBAJUD] Erro ao verificar dialog: {e_dlg}')

        logger.info('[SISBAJUD]  Sessão SISBAJUD inicializada com sucesso - login realizado e pronto para execução')
        return driver
    except Exception as e:
        logger.info(f'[SISBAJUD][ERRO] Falha ao iniciar sessão SISBAJUD: {e}')
        try:
            logger.exception("Erro detectado")
        except Exception as trace_err:
            _ = trace_err

    return None


def _atualizar_calculo_antigo(driver_pje, dados_processo, valor, log=True):
    """Ponto calculo_antigo do fluxo teimosinha: roda a atualização rápida"""
    from Fix.atualizacao_rapida import AtualizacaoRapidaErro, atualizar_calculo_se_antigo
    try:
        atualizar_calculo_se_antigo(driver_pje, dados_processo, log=log)
    except AtualizacaoRapidaErro as e:
        if log:
            logger.info(f'[SISBAJUD]  Atualização rápida falhou (pos_envio={e.pos_envio}): {e} '
                        '— minuta seguirá com valor anterior + GIGS CALC')
        return 'calculo_antigo', valor
    divida = dados_processo.get('divida') or {}
    valor_novo = divida.get('valor') or valor
    data_nova = divida.get('data', '')
    try:
        _dt_nova = datetime.strptime(data_nova, '%d/%m/%Y')
        if (datetime.now() - _dt_nova).days <= 90:
            if log:
                logger.info(f'[SISBAJUD]  Cálculo atualizado — minuta usará {valor_novo} (liquidado em {data_nova})')
            return None, valor_novo
    except (ValueError, TypeError):
        pass
    return 'calculo_antigo', valor


def minuta_bloqueio(driver, dados_processo=None, driver_pje=None, log=True, fechar_driver=True, prazo_dias=None, protocolar=False):
    """Orquestra a criação de minuta de bloqueio no SISBAJUD:"""
    resultado = {
        'status': 'pendente',
        'reus_processados': 0,
        'erros': [],
        'detalhes': {}
    }

    try:
        logger.info('\n[SISBAJUD] INICIANDO CRIAÇÃO DE MINUTA DE BLOQUEIO')
        logger.info('=' * 60)

        pendencia = None

        if dados_processo is None:
            if log:
                logger.info('[SISBAJUD] Extraindo dados do processo do PJe...')
            try:
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

                if log:
                    logger.info('[SISBAJUD]  Dados do processo extraídos/carregados com sucesso')
            except Exception as e:
                if log:
                    logger.info(f'[SISBAJUD]  Erro ao extrair dados do processo: {e}')
                resultado['status'] = 'erro'
                resultado['erros'].append(f'Erro ao extrair dados: {e}')
                return resultado

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
                    pendencia, valor = _atualizar_calculo_antigo(driver_pje, dados_processo, valor, log=log)
            except Exception:
                pass

        if log:
            logger.info(f'[SISBAJUD]  Valor encontrado: {valor} - prosseguindo com minuta')

        try:
            from SISB.processamento.series_navegar import dispensar_dialog_ordem_pendente
            dispensar_dialog_ordem_pendente(driver, log=log, timeout=1.0)
        except Exception:
            pass

        logger.info('[SISBAJUD] Procurando botão "Nova Minuta"...')

        fn_exec_debug = getattr(driver, 'execute_script', None) or (lambda s: driver.page.evaluate(s) if hasattr(driver, 'page') and driver.page else None)
        debug_botoes = fn_exec_debug("""
        const botoes = Array.from(document.querySelectorAll('button, a, [role="button"], .btn'));
        return botoes.map(b => ({
            tag: b.tagName,
            text: (b.textContent || '').trim().substring(0, 50),
            class: b.className,
            id: b.id || '',
            visible: b.offsetParent !== null
        })).slice(0, 20);  // primeiros 20 botões
        """)
        logger.debug('[SISBAJUD] Botões encontrados na página: %s', debug_botoes)

        script_nova_minuta = """
        var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
        if (!botaoNova) {
            botaoNova = document.querySelector('button.mat-fab.mat-primary');
        }
        if (!botaoNova) {
            // Procura por qualquer botão com "Minuta" no texto
            const botoes = Array.from(document.querySelectorAll('button, a, [role="button"]'));
            botaoNova = botoes.find(b => b.textContent.toLowerCase().includes('minuta'));
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

        sucesso_nova_minuta = False
        if hasattr(driver, 'page') and driver.page:
            try:
                sel_nova = 'button.mat-fab.mat-primary, button:has(.fa-plus), button:has-text("Nova Minuta"), button[aria-label*="Nova minuta" i]'
                btn_nova = driver.page.locator(sel_nova).first
                if btn_nova.is_visible(timeout=3000):
                    btn_nova.click()
                    sucesso_nova_minuta = True
            except Exception:
                pass

        if not sucesso_nova_minuta:
            fn_exec_nova = getattr(driver, 'execute_script', None) or (lambda s: driver.page.evaluate(s) if hasattr(driver, 'page') and driver.page else None)
            if fn_exec_nova:
                try:
                    sucesso_nova_minuta = bool(fn_exec_nova(script_nova_minuta))
                except Exception:
                    pass

        if sucesso_nova_minuta:
            logger.info('[SISBAJUD]  Botão "Nova Minuta" clicado com sucesso')
            try:
                espera.ate_aparecer(driver, 'input[placeholder*="Juiz"], .mat-form-field, form', teto=10)
            except Exception:
                logger.info('[SISBAJUD] Timeout aguardando formulário da minuta - continuando')
        else:
            logger.info('[SISBAJUD]  Botão "Nova Minuta" não encontrado')
            logger.info('[SISBAJUD]  Página atual: %s', driver.current_url)
            return {
                'status': 'erro',
                'erros': ['Botão "Nova Minuta" não encontrado'],
                'reus_processados': 0,
                'detalhes': {}
            }

        dados_validos, numero_processo = helpers._validar_dados(dados_processo)
        if not dados_validos:
            resultado['status'] = 'erro'
            resultado['erros'].append('Dados do processo inválidos ou insuficientes')
            return resultado

        if prazo_dias is None:
            prazo_dias = 30
        logger.info('[SISBAJUD] prazo_dias aplicado na minuta: %s', prazo_dias)

        campos_preenchidos = helpers._preencher_campos_iniciais(driver, dados_processo, prazo_dias)
        if not campos_preenchidos:
            resultado['status'] = 'erro'
            resultado['erros'].append('Falha ao preencher campos iniciais')
            return resultado

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

        _configurar_valor(driver, dados_processo)

        minuta_salva = helpers._salvar_minuta(driver)
        if not minuta_salva:
            resultado['status'] = 'erro'
            resultado['erros'].append('Falha ao salvar minuta')
            return resultado

        minuta_protocolada = False
        resultado['minuta_protocolada'] = False
        if log:
            logger.info('[SISBAJUD]  Passo 6.1 (protocolar/assinar) foi removido - continuando fluxo')

        relatorio_gerado = helpers._gerar_relatorio_minuta(driver, numero_processo)
        if not relatorio_gerado:
            if log:
                logger.info('[SISBAJUD]  Falha ao gerar relatório da minuta')

        if relatorio_gerado and pendencia == 'sem_calculo':
            conteudo = relatorio_gerado.get('conteudo', '') if isinstance(relatorio_gerado, dict) else relatorio_gerado
            if isinstance(conteudo, str) and '33,33' in conteudo:
                conteudo = conteudo.replace('33,33', '(ver planilha mais recente)')
                if isinstance(relatorio_gerado, dict):
                    relatorio_gerado['conteudo'] = conteudo
                try:
                    from atos.anexos import salvar_conteudo_clipboard
                    salvar_conteudo_clipboard(
                        conteudo=conteudo,
                        numero_processo=numero_processo,
                        tipo_conteudo="sisbajud_minuta",
                        debug=log
                    )
                except Exception:
                    pass

        juntada_executada = False
        if relatorio_gerado:
            if log:
                logger.info(f'[SISBAJUD][DEBUG] relatorio_gerado: {bool(relatorio_gerado)}, driver_pje presente: {driver_pje is not None}')
            if driver_pje is not None and log:
                try:
                    logger.info(f'[SISBAJUD][DEBUG] driver_pje type: {type(driver_pje)}')
                except Exception as e:
                    _ = e
        if relatorio_gerado and driver_pje:
            try:
                # (modelo 'xteim') — não usar os wrappers de ordem genéricos.
                if log:
                    logger.info('[SISBAJUD] Executando juntada DA MINUTA no PJe (modelo xteim)...')

                try:
                    if driver_pje:
                        aba_detalhe = None
                        for handle in _abas(driver_pje):
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
                            try:
                                from Fix.core import esperar_url_conter
                                driver_pje.switch_to.window(_abas(driver_pje)[-1])
                                esperar_url_conter(driver_pje, '/detalhe', timeout=5)
                                logger.info('[SISBAJUD]  Aguardando /detalhe na aba atual (fallback)')
                            except Exception:
                                logger.info('[SISBAJUD]  Aviso: não foi possível garantir aba /detalhe antes da juntada')
                except Exception as e:
                    logger.info(f'[SISBAJUD]  Erro ao tentar ajustar foco para PJe: {e}')

                from atos.anexos import anex_sisbconsulta
                juntada_executada = anex_sisbconsulta(driver_pje, numero_processo, debug=log, modelo='xteim')
                resultado['juntada_executada'] = bool(juntada_executada)
                if juntada_executada and log:
                    logger.info('[SISBAJUD]  Juntada da minuta realizada no PJe')
                elif log:
                    logger.info('[SISBAJUD]  Juntada da minuta pode nao ter sido executada corretamente')

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

                    gigs_prazo = '41' if prazo_dias == 60 else '22'
                    if pendencia in ('calculo_antigo', 'sem_calculo'):
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
    """Processamento completo de ordens no SISBAJUD:"""
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

        if dados_processo:
            numero_processo = dados_processo.get('numero_processo') or dados_processo.get('numero')
            if isinstance(numero_processo, list):
                numero_processo = numero_processo[0] if numero_processo else None
            if log:
                logger.info(f'[SISBAJUD] Usando dados do processo passados por parâmetro: {numero_processo}')
        else:
            dados_processo, numero_processo = helpers._carregar_dados_ordem()

        if not dados_processo or not numero_processo:
            resultado['status'] = 'erro'
            resultado['erros'].append('Falha ao carregar dados do processo')
            return resultado

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

                driver.get("https://sisbajud.cnj.jus.br/teimosinha")
                aguardar_renderizacao_nativa(driver, timeout=10)
                if log:
                    logger.info('[SISBAJUD]  Navegação para teimosinha realizada')

                campo_processo = espera.ate_aparecer(driver, 'input[placeholder="Número do Processo"]', teto=15)
                if not campo_processo:
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

                from Fix.utils import aguardar_pagina_carregar
                aguardar_pagina_carregar(driver, timeout=15)

                if log:
                    logger.info('[SISBAJUD]  Processo inserido no SISBAJUD e série aberta')

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

        data_limite = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
        if log:
            logger.info(f'[SISBAJUD] Data limite para filtro: {data_limite.strftime("%d/%m/%Y")} (30 dias)')

        leitura = helpers._filtrar_series(driver, data_limite)
        series_validas = leitura.get('series') or []
        if not series_validas and (leitura.get('erro') or leitura.get('lidas', 0) == 0):
            logger.warning('[SISBAJUD] Tabela de séries não lida (%s) — aguardando e relendo',
                           leitura.get('erro') or '0 linha(s)')
            espera.assentar(driver, 3.0, motivo='tabela de séries do SISBAJUD')
            leitura = helpers._filtrar_series(driver, data_limite)
            series_validas = leitura.get('series') or []
            if not series_validas and (leitura.get('erro') or leitura.get('lidas', 0) == 0):
                resultado['status'] = 'erro'
                resultado['erros'].append(
                    'Tabela de séries do SISBAJUD não carregou (%s) — nada foi processado'
                    % (leitura.get('erro') or '0 linha(s)'))
                return resultado
        if not series_validas:
            resultado['status'] = 'concluido'
            resultado['erros'].append('Não há séries válidas para processar')
            return resultado

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

        estrategia = None
        if tipo_fluxo == 'POSITIVO':
            estrategia = helpers._calcular_estrategia_bloqueio(series_validas, dados_processo, log)
            resultado['estrategia'] = estrategia

            if estrategia.get('tipo') == 'TRANSFERIR_PARCIAL':
                series_validas_ordenadas = sorted(series_validas, key=lambda s: float(s.get('valor_bloqueado', 0)), reverse=True)
                if log:
                    logger.info(f'[SISBAJUD]  Séries ordenadas por valor (maior primeiro) para otimizar transferências')
                series_validas = series_validas_ordenadas

        if tipo_fluxo in ['POSITIVO', 'DESBLOQUEIO']:
            resultado_processamento = helpers._processar_series(driver, series_validas, tipo_fluxo, log, estrategia=estrategia)
            resultado.update(resultado_processamento)

            if len(series_validas) > 0 and resultado.get('series_processadas', 0) == 0 and resultado.get('ordens_processadas', 0) == 0:
                if not resultado.get('erros'):
                    resultado['erros'] = []
                resultado['erros'].append('Falha ao processar series: nenhuma ordem extraida (possivel problema de navegacao)')
                if log:
                    logger.error('[SISBAJUD] FAIL-SAFE: 0 ordens extraidas de %d series — marcando como erro', len(series_validas))
        else:
            if log:
                logger.info('[SISBAJUD] ⏭ Fluxo NEGATIVO: pulando processamento de séries')
            resultado['series_processadas'] = 0
            resultado['ordens_processadas'] = 0

        relatorio_gerado = helpers._gerar_relatorio_ordem(
            tipo_fluxo,
            resultado['series_processadas'],
            resultado['ordens_processadas'],
            resultado['detalhes'],
            series_validas,
            driver if tipo_fluxo == 'POSITIVO' else None,
            log,
            numero_processo=numero_processo,
            estrategia=estrategia
        )

        if relatorio_gerado and driver_pje:
            # pode não abrir aba nova e navegar a MESMA aba para /anexar. Sem isso, o
            aba_detalhe = None
            url_detalhe = ''
            try:
                aba_detalhe = driver_pje.current_window_handle
                url_detalhe = driver_pje.current_url or ''
            except Exception:
                pass
            # LACO: relatorio pronto no SISBAJUD -> volta o foco para o PJe no
            _voltar_para_pje_detalhe(
                driver_pje, numero_processo,
                (dados_processo or {}).get('id_processo'), log=log)
            juntada_executada = helpers._executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log)
            resultado['juntada_executada'] = juntada_executada

            if juntada_executada:
                try:
                    from atos.wrappers_ato import ato_meios, ato_bloq

                    try:
                        abas = list(getattr(driver_pje, 'window_handles', []) or [])
                        if len(abas) > 1:
                            from Fix.browser_suporte import forcar_fechamento_abas_extras
                            forcar_fechamento_abas_extras(driver_pje, aba_detalhe or abas[0])
                            if log:
                                logger.info('[SISBAJUD]  Aba de juntada fechada (%d -> %d abas)',
                                            len(abas), len(getattr(driver_pje, 'window_handles', []) or []))

                        if '/detalhe' not in (driver_pje.current_url or '') and url_detalhe:
                            if log:
                                logger.info('[SISBAJUD]  Aba não está em /detalhe — voltando para: %s', url_detalhe)
                            driver_pje.get(url_detalhe)

                        if log:
                            logger.info('[SISBAJUD]  Foco na aba /detalhe: %s', driver_pje.current_url)

                    except Exception as e_fechar:
                        if log:
                            logger.info(f'[SISBAJUD]  Erro ao voltar para a aba /detalhe: {e_fechar}')

                    if tipo_fluxo == 'POSITIVO':
                        if log:
                            logger.info('[SISBAJUD] Executando ato_bloq (fluxo POSITIVO)...')
                        ato_bloq(driver_pje)
                        if log:
                            logger.info('[SISBAJUD]  ato_bloq executado com sucesso')

                        try:
                            if log:
                                logger.info('[SISBAJUD] Criando GIGS "1/xs pec dec"...')
                            criar_gigs(driver_pje, "1/xs pec dec", log=log)
                            if log:
                                logger.info('[SISBAJUD]  GIGS criado com sucesso')
                        except Exception as e_gigs:
                            if log:
                                logger.info(f'[SISBAJUD]  Erro ao criar GIGS: {e_gigs}')
                    else:
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
    """Processa bloqueios no SISBAJUD usando a função processar_ordem_sisbajud"""
    try:
        logger.info('\n[SISBAJUD] INICIANDO PROCESSAMENTO DE BLOQUEIOS')
        logger.info('=' * 60)

        # 1. Inicializar SISBAJUD
        driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
        if not driver_sisbajud:
            logger.info('[SISBAJUD]  Falha ao inicializar SISBAJUD')
            return None

        dados_processo = utils.carregar_dados_processo()
        if not dados_processo:
            logger.info('[SISBAJUD]  Arquivo dadosatuais.json não encontrado. Execute extrair_dados_processo NO PJE antes!')
            return None

        # 3. Processar ordens SISBAJUD
        resultado = processar_ordem_sisbajud(driver_sisbajud, dados_processo, driver_pje=driver_pje)

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
    """Executa JavaScript para coletar dados da minuta SISBAJUD e retorna o texto formatado."""
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

        resultado = _exec_js(driver, script_coleta)

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
    """Wrapper para minuta_bloqueio com prazo de 60 dias."""
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
    """Cria DUAS minutas de bloqueio no SISBAJUD no mesmo fluxo de forma independente."""
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

        if dados_processo is None:
            if log:
                logger.info('[SISBAJUD] Extraindo dados do processo do PJe...')
            try:
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
                    pendencia, valor = _atualizar_calculo_antigo(driver_pje, dados_processo, valor, log=log)
            except Exception:
                pass

        dados_validos, numero_processo = helpers._validar_dados(dados_processo)
        if not dados_validos:
            resultado['status'] = 'erro'
            resultado['erros'].append('Dados do processo inválidos ou insuficientes')
            return resultado

        if prazo_dias is None:
            prazo_dias = 30
        logger.info('[SISBAJUD] prazo_dias aplicado nas minutas: %s', prazo_dias)

        logger.info(f'[SISBAJUD] === CRIANDO 1ª MINUTA (prazo {prazo_dias} dias) ===')

        URL_CADASTRAR = "https://sisbajud.cnj.jus.br/minuta/cadastrar"
        if not _abrir_cadastro_minuta(driver, '1ª minuta', log=log):
            resultado['status'] = 'erro'
            resultado['erros'].append('1ª minuta: formulário de cadastro não carregou')
            return resultado

        if '/cadastrar' not in (driver.current_url or ''):
            sucesso_nova = _clicar_nova_minuta(driver, log)
            if not sucesso_nova:
                resultado['status'] = 'erro'
                resultado['erros'].append('1ª minuta: Botão "Nova Minuta" não encontrado')
                return resultado

        agendar_m1 = False
        campos_ok = helpers._preencher_campos_iniciais(
            driver, dados_processo, prazo_dias,
            agendar_amanha=agendar_m1, agendar_offset=1
        )
        if not campos_ok:
            resultado['status'] = 'erro'
            resultado['erros'].append('1ª minuta: Falha ao preencher campos iniciais')
            return resultado

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

        _configurar_valor(driver, dados_processo)

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

        dados_rel_1 = helpers._gerar_relatorio_minuta(
            driver, numero_processo, dados_processo=dados_processo, salvar_clipboard=False
        )
        resultado['relatorio_minuta_1'] = (dados_rel_1 or {}).get('conteudo') if isinstance(dados_rel_1, dict) else None
        resultado['minuta_1'] = {
            'prazo_dias': prazo_dias,
            'protocolo': "",
            'relatorio_gerado': bool(dados_rel_1)
        }

        logger.info('[SISBAJUD] === CRIANDO 2ª MINUTA (agendamento dia seguinte) ===')

        URL_CADASTRAR = "https://sisbajud.cnj.jus.br/minuta/cadastrar"
        if not _abrir_cadastro_minuta(driver, '2ª minuta', log=log):
            resultado['erros'].append('2ª minuta: formulário de cadastro não carregou')

        if '/cadastrar' not in (driver.current_url or ''):
            sucesso_nova = _clicar_nova_minuta(driver, log)
            if not sucesso_nova:
                resultado['erros'].append('2ª minuta: Botão "Nova Minuta" não encontrado')

        campos_ok_2 = False
        try:
            from .processamento.minutas_campos import _preencher_campos_iniciais as preencher_campos_atualizado
            agendar_m2 = True
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
            if reus_restantes:
                if log:
                    logger.info(
                        '[SISBAJUD] Processando %d reus restantes na 2ª minuta',
                        len(reus_restantes)
                    )
                helpers._processar_reus_otimizado(driver, reus_restantes, max_validos=10)
            else:
                helpers._processar_reus_otimizado(driver, todos_reus, max_validos=10)

            _configurar_valor(driver, dados_processo)

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

        if todos_reus and (dados_rel_1 or minuta_1_salva or resultado.get('minuta_2', {}).get('salva')):
            data_limite_calc = None
            try:
                val_limite = _exec_js(driver, """
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
                from atos.anexos import salvar_conteudo_clipboard
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
            try:
                from atos.anexos import salvar_conteudo_clipboard
                salvar_conteudo_clipboard(
                    conteudo=dados_rel_1['conteudo'],
                    numero_processo=numero_processo,
                    tipo_conteudo="sisbajud_minuta",
                    debug=log
                )
            except Exception:
                pass

        # === LACO: RELATORIO PRONTO (driver SISBAJUD) -> VOLTA PARA O PJE =====
        # A minuta/relatorio ja foi gerada no driver SISBAJUD. ANTES de juntar, o
        # diante (juntada, visibilidade, GIGS) nada roda no driver SISBAJUD.
        juntada_executada = False
        if (dados_rel_1 or minuta_1_salva or resultado.get('minuta_2', {}).get('salva')) and driver_pje:
            _voltar_para_pje_detalhe(
                driver_pje, numero_processo,
                (dados_processo or {}).get('id_processo'), log=log)

            try:
                from atos.anexos import anex_sisbconsulta
                if log:
                    logger.info('[SISBAJUD] Executando juntada da minuta no PJe (modelo xteim)...')
                juntada_executada = anex_sisbconsulta(driver_pje, numero_processo, debug=log, modelo='xteim')
                resultado['juntada_executada'] = bool(juntada_executada)

                if juntada_executada:
                    from atos.wrappers_utils import executar_visibilidade_sigilosos_se_necessario
                    vis_ok = executar_visibilidade_sigilosos_se_necessario(driver_pje, True, debug=log)
                    resultado['visibilidade_certidao_sigilosa'] = bool(vis_ok)

                    gigs_prazo = '41' if prazo_dias == 60 else '22'
                    if pendencia in ('calculo_antigo', 'sem_calculo'):
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


def _voltar_para_pje_detalhe(driver_pje, numero_processo, id_processo=None, log=True):
    """Relatorio pronto no SISBAJUD -> devolve o foco ao PJe no /detalhe DO PROCESSO."""
    if driver_pje is None:
        return ''

    url_alvo = ''
    if id_processo:
        try:
            from Fix.variaveis import url_processo_detalhe
            url_alvo = url_processo_detalhe(id_processo)
        except Exception as e_url:
            logger.warning('[SISBAJUD][LACO] Nao consegui montar a URL do processo %s: %s',
                           id_processo, e_url)

    abas_vistas = []
    aba_alvo = None
    try:
        for handle in _abas(driver_pje):
            try:
                driver_pje.switch_to.window(handle)
                url = driver_pje.current_url or ''
            except Exception:
                continue
            abas_vistas.append(url)
            if '/detalhe' not in url:
                continue
            if id_processo and ('/processo/%s' % id_processo) not in url:
                continue
            aba_alvo = handle
            break
    except Exception as e_abas:
        logger.warning('[SISBAJUD][LACO] Falha ao listar abas do PJe: %s', e_abas)

    if aba_alvo:
        try:
            driver_pje.switch_to.window(aba_alvo)
        except Exception:
            pass
    elif url_alvo:
        try:
            driver_pje.get(url_alvo)
            aguardar_renderizacao_nativa(driver_pje, 'pje-cabecalho-processo',
                                         modo='aparecer', timeout=15)
        except Exception as e_nav:
            logger.error('[SISBAJUD][LACO] Falha ao posicionar o PJe no processo %s: %s',
                         numero_processo, e_nav)
            return ''
    else:
        logger.warning('[SISBAJUD][LACO] sem id do processo — mantendo a aba atual (%s)',
                       getattr(driver_pje, 'current_url', ''))

    try:
        url_final = driver_pje.current_url or ''
    except Exception:
        url_final = ''
    if log:
        for u in abas_vistas:
            logger.info('[SISBAJUD][LACO] aba candidata: %s', u)
        logger.info('[SISBAJUD][LACO] relatório pronto — PJe de volta em: %s', url_final)
    return url_final


_SEL_FORM_CADASTRO = ('input[placeholder*="Juiz"], input[formcontrolname="numeroProcesso"], '
                      'input[placeholder*="processo"]')


_SEL_CAMPO_MINUTA = ('input[placeholder*="Juiz"], input[placeholder="Número do Processo"], '
                     'input[formcontrolname="numeroProcesso"]')

# Sonda de renderizacao real do cadastro. NAO usa "URL sem hash": o callback OIDC
_PROBE_CADASTRO = """
const texto = (document.body ? document.body.innerText : '');
const campos = Array.from(document.querySelectorAll(
    'input[placeholder*="Juiz"], input[placeholder="Número do Processo"], '
    + 'input[formcontrolname="numeroProcesso"]'));
const livres = campos.filter(c => !c.disabled && !c.readOnly).length;
const carregando = /Carregando/i.test(texto);
return {
    pronto: location.pathname.includes('/minuta/cadastrar')
        && document.readyState === 'complete' && !carregando && livres > 0,
    motivo: carregando ? 'carregando'
        : document.readyState !== 'complete' ? ('dom-' + document.readyState)
        : livres === 0 ? 'sem-campo' : 'ok',
    url: location.href
};
"""


def _aguardar_cadastro_renderizado(driver, teto=25, intervalo=0.4):
    """Espera a tela de cadastro sair de 'Carregando', ter campo utilizavel e URL estavel em 2 amostras."""
    visto = {'url': None, 'motivo': ''}

    def _cond(d):
        try:
            info = _exec_js(d, _PROBE_CADASTRO) or {}
        except Exception:
            return False
        if not isinstance(info, dict):
            return False
        visto['motivo'] = info.get('motivo') or '?'
        if not info.get('pronto'):
            visto['url'] = None
            return False
        if info.get('url') != visto['url']:
            visto['url'] = info.get('url')
            return False
        return True

    try:
        ok = bool(espera.ate(driver, _cond, teto=teto, intervalo=intervalo))
    except Exception:
        ok = False
    if not ok:
        logger.warning('[SISBAJUD] Cadastro nao renderizou em %.1fs (motivo=%s, url=%s)',
                       teto, visto['motivo'] or '?', getattr(driver, 'current_url', '?'))
    return ok


def _cadastro_pronto_para_preencher(driver, teto=6):
    """True se /minuta/cadastrar ja esta renderizado, vazio e sem aviso pos-salvamento."""
    try:
        if '/minuta/cadastrar' not in (driver.current_url or ''):
            return False
        if not _aguardar_cadastro_renderizado(driver, teto=teto):
            return False
        estado = _exec_js(driver, """
            const sel = 'input[placeholder*="Juiz"], input[formcontrolname="numeroProcesso"], input[placeholder*="processo"]';
            const campos = Array.from(document.querySelectorAll(sel));
            if (!campos.length) return {ok: false};
            const preenchido = campos.some(c => (c.value || '').trim().length > 0);
            const txt = (document.body ? document.body.innerText : '').toLowerCase();
            const posSalvamento = txt.includes('minuta salva') || txt.includes('salva com sucesso')
                || txt.includes('protocolo') && txt.includes('gerado');
            return {ok: !preenchido && !posSalvamento, preenchido: preenchido, posSalvamento: posSalvamento};
        """) or {}
        return isinstance(estado, dict) and bool(estado.get('ok'))
    except Exception:
        return False


def _abrir_cadastro_minuta(driver, rotulo='minuta', log=True, tentativas=2, forcar_novo=False):
    """Garante /minuta/cadastrar pronto; reaproveita se fresco (forcar_novo=True sempre renavega)."""
    url = "https://sisbajud.cnj.jus.br/minuta/cadastrar"

    if not forcar_novo and _cadastro_pronto_para_preencher(driver):
        if log:
            logger.info('[SISBAJUD] Cadastro ja aberto e fresco (%s) — sem renavegar: %s',
                        rotulo, driver.current_url)
        return True

    for tent in range(1, tentativas + 1):
        try:
            if log:
                logger.info('[SISBAJUD] Navegando para cadastro (%s, tentativa %d): %s',
                            rotulo, tent, url)
            driver.get(url)
            if _aguardar_cadastro_renderizado(driver, teto=25):
                url_1 = driver.current_url
                espera.assentar(driver, 1.0, motivo='confirmando URL estavel do cadastro')
                if driver.current_url != url_1:
                    logger.warning('[SISBAJUD] SPA ainda navegando (%s): %s -> %s — reassentando',
                                   rotulo, url_1, driver.current_url)
                    espera.assentar(driver, 1.5, motivo='SPA terminou de navegar')
                    if not _aguardar_cadastro_renderizado(driver, teto=15):
                        logger.warning('[SISBAJUD] Cadastro perdido apos navegacao da SPA (%s)', rotulo)
                        continue
                if log:
                    logger.info('[SISBAJUD] Formulario de cadastro pronto (%s): %s',
                                rotulo, driver.current_url)
                    try:
                        from SISB.processamento.minutas_campos import _snapshot_cadastro
                        _snapshot_cadastro(driver, f'cadastro-pronto-{rotulo}')
                    except Exception:
                        pass
                return True
            logger.warning('[SISBAJUD] Formulario de cadastro nao ficou pronto (%s, tentativa %d) — url=%s',
                           rotulo, tent, getattr(driver, 'current_url', '?'))
        except Exception as e_nav:
            logger.warning('[SISBAJUD] Falha ao abrir cadastro (%s, tentativa %d): %s',
                           rotulo, tent, e_nav)
        espera.assentar(driver, 1.0, motivo='retentativa do cadastro de minuta')
    return False


def _clicar_nova_minuta(driver, log=True):
    """Helper interno: clica no botão 'Nova Minuta' e aguarda o formulário carregar."""
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
    sucesso = _exec_js(driver, script_nova_minuta)
    if sucesso:
        try:
            espera.ate_aparecer(driver, 'input[placeholder*="Juiz"], .mat-form-field, form', teto=10)
        except Exception:
            pass
    return bool(sucesso)

