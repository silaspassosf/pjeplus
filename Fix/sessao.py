"""Fix/sessao.py — cluster canônico de sessão/login/cookies (F3).

Conteúdo MOVIDO verbatim de Fix/utils.py, que é a via executada pelos
orquestradores (x.py, f.py, Triagem, Peticao, SISB, atos, tools). O cluster
homônimo de Fix/core.py era divergente e sem nenhum chamador — removido.
Fix/utils.py e Fix/facade_publica.py re-exportam estes nomes (compat).
"""
import glob
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import Optional

import keyring

from .log import logger
from Fix import espera
from Fix.core import aguardar_e_clicar, preencher_campo, safe_click_no_scroll


USAR_COOKIES_AUTOMATICO = True
SALVAR_COOKIES_AUTOMATICO = True


def obter_credencial(
    nome: str,
    servicos: tuple = ('pjeplus', 'sisbajud', 'SISB'),
    aliases: tuple = ()
) -> Optional[str]:
    """
    Obtém credencial SOMENTE do Gerenciador de Credenciais do Windows (keyring):
      - keyring.get_password(servico, nome) para cada servico ('pjeplus', 'sisbajud', 'SISB')
      - keyring.get_password(nome, nome)
      - keyring.get_password(nome, '')
      - keyring.get_password(nome, os.environ.get('USERNAME', ''))
    Variáveis de ambiente NÃO são mais usadas (evita dado errado vencer o keyring).
    Retorna o valor como string ou None se não encontrado.
    """
    if not nome:
        return None
    nomes = (nome,) + tuple(aliases)

    # Windows Credential Manager via keyring (única fonte)
    try:
        import keyring
        for s in servicos:
            for n in nomes:
                for chave in (n, n.upper(), n.lower()):
                    val = keyring.get_password(s, chave)
                    if val:
                        return str(val).strip()

        for n in nomes:
            for chave in (n, n.upper(), n.lower()):
                for usuario in (chave, '', os.environ.get('USERNAME', '')):
                    try:
                        val = keyring.get_password(chave, usuario)
                        if val:
                            return str(val).strip()
                    except Exception:
                        pass
    except Exception:
        pass

    return None

def login_manual(driver, aguardar_url_painel=True):
    """Login manual: navega para login e aguarda usuário fazer login"""
    if verificar_e_aplicar_cookies(driver):
        if SALVAR_COOKIES_AUTOMATICO:
            salvar_cookies_sessao(driver, info_extra='cookies_reutilizados')
        return True
    
    url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
    logger.info('[LOGIN_MANUAL] Navegando para tela de login: %s', url_login)
    driver.get(url_login)
    painel_url = 'https://pje.trt2.jus.br/pjekz/gigs/meu-painel'
    _urls_validas = (painel_url, 'pjekz/quadro-avisos/visualizar')
    logger.info('[LOGIN_MANUAL] Aguarde o login manual ate: %s', painel_url)

    if aguardar_url_painel:
        while True:
            try:
                cur = driver.current_url
                if any(cur.startswith(u) if u.startswith('http') else u in cur
                       for u in _urls_validas):
                    logger.debug('[LOGIN_MANUAL] Painel detectado, login realizado')
                    if SALVAR_COOKIES_AUTOMATICO:
                        salvar_cookies_sessao(driver, info_extra='login_manual')
                    break
            except Exception as e:
                # Se a janela foi fechada manualmente, driver.current_url levanta exceção
                logger.error('[LOGIN_MANUAL] Erro ao verificar URL (janela fechada?): %s', e)
                return False
                
            try:
                espera.assentar(driver, 1)
            except Exception as e:
                logger.error('[LOGIN_MANUAL] Erro durante espera (janela fechada?): %s', e)
                return False
    return True

def login_automatico(driver):
    """Login automático via AutoHotkey - OTIMIZADO: usa aguardar_e_clicar() e _obter_caminhos_ahk()"""
    if verificar_e_aplicar_cookies(driver):
        if SALVAR_COOKIES_AUTOMATICO:
            salvar_cookies_sessao(driver, info_extra='cookies_reutilizados')
        return True
    
    import subprocess
    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    driver.get(login_url)
    logger.info("[LOGIN_AUTOMATICO] Navegando para URL de login: %s", login_url)

    try:
        if not aguardar_e_clicar(driver, '#btnSsoPdpj', timeout=10):
            logger.error("ERRO em login_automatico: Botao #btnSsoPdpj nao encontrado")
            return False

        if not aguardar_e_clicar(driver, '.botao-certificado-titulo', timeout=10):
            logger.error("ERRO em login_automatico: Botao certificado nao encontrado")
            return False

        ahk_exe, ahk_script = _obter_caminhos_ahk()

        if not ahk_exe or not os.path.exists(ahk_exe):
            logger.error("ERRO em login_automatico: Executavel AutoHotkey nao encontrado: %s", ahk_exe)
            return False
        if not ahk_script or not os.path.exists(ahk_script):
            logger.error("ERRO em login_automatico: Script AutoHotkey nao encontrado: %s", ahk_script)
            return False

        subprocess.Popen([ahk_exe, ahk_script])
        logger.debug("[LOGIN_AUTOMATICO] Script AutoHotkey chamado para digitar a senha")

        for _ in range(60):
            if "login" not in driver.current_url.lower():
                logger.debug("[LOGIN_AUTOMATICO] Login detectado, prosseguindo")
                if SALVAR_COOKIES_AUTOMATICO:
                    salvar_cookies_sessao(driver, info_extra='login_automatico')
                return True
            espera.assentar(driver, 1)

        logger.error("ERRO em login_automatico: Timeout aguardando login")
        return False
    except Exception as e:
        logger.error("ERRO em login_automatico: %s: %s", type(e).__name__, e)
        return False

def login_automatico_direto(driver):
    """Login automático DIRETO via AutoHotkey - OTIMIZADO: usa aguardar_e_clicar() e _obter_caminhos_ahk()"""
    import subprocess
    
    logger.info('[LOGIN_AUTOMATICO_DIRETO] Iniciando login direto sem cookies')
    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    driver.get(login_url)
    logger.info("[LOGIN_AUTOMATICO_DIRETO] Navegando para URL de login: %s", login_url)

    try:
        if not aguardar_e_clicar(driver, '#btnSsoPdpj', timeout=10):
            logger.error("ERRO em login_automatico_direto: Botao #btnSsoPdpj nao encontrado")
            return False

        if not aguardar_e_clicar(driver, '.botao-certificado-titulo', timeout=10):
            logger.error("ERRO em login_automatico_direto: Botao certificado nao encontrado")
            return False

        ahk_exe, ahk_script = _obter_caminhos_ahk()

        if not ahk_exe or not os.path.exists(ahk_exe):
            logger.error("ERRO em login_automatico_direto: Executavel AutoHotkey nao encontrado: %s", ahk_exe)
            return False
        if not ahk_script or not os.path.exists(ahk_script):
            logger.error("ERRO em login_automatico_direto: Script AutoHotkey nao encontrado: %s", ahk_script)
            return False

        subprocess.Popen([ahk_exe, ahk_script])
        logger.debug("[LOGIN_AUTOMATICO_DIRETO] Script AutoHotkey chamado para digitar a senha")

        for _ in range(60):
            if "login" not in driver.current_url.lower():
                logger.debug("[LOGIN_AUTOMATICO_DIRETO] Login detectado, prosseguindo")
                if SALVAR_COOKIES_AUTOMATICO:
                    salvar_cookies_sessao(driver, info_extra='login_automatico_direto')
                return True
            espera.assentar(driver, 1)

        logger.error("ERRO em login_automatico_direto: Timeout aguardando login")
        return False

    except Exception as e:
        logger.error("ERRO em login_automatico_direto: %s: %s", type(e).__name__, e)
        return False

def sessao_oauth_completa(driver) -> bool:
    """Sessão REALMENTE completa = cookies OAuth do gateway presentes.

    URL "autenticada" sem access_token = handshake OAuth pela metade
    (KC_RESTART pendente) — o gateway pje-comum-api responde 403 ARQ-516.
    """
    try:
        nomes = {c.get('name') for c in driver.get_cookies()}
    except Exception:
        return False
    return bool(nomes & {'access_token', 'sso_refresh_token'})

def _is_driver_headless(driver) -> bool:
    """Verifica se o driver está em modo headless (Playwright ou legado)."""
    if getattr(driver, 'headless', False) or getattr(driver, '_headless', False):
        return True
    try:
        from Fix.browser_suporte import is_headless_mode
        return is_headless_mode(driver)
    except Exception:
        return False

def login_cpf(driver, url_login=None, cpf=None, senha=None, aguardar_url_final=True, forcar=False):
    """Login automático por CPF/senha alimentado pelo Gerenciador de Credenciais do Windows.

    Recupera credenciais do Windows (keyring - serviço 'pjeplus').
    Preenche automaticamente no formulário Keycloak/PDPJ (conforme padrão LEGADO.md ~15323).
    Se as credenciais estiverem ausentes ou em caso de MFA/captcha, faz fallback
    transparente para login manual no browser.
    """
    try:
        # Apagar cookies se sessao morta ou forcar reautenticacao
        if forcar or not sessao_oauth_completa(driver):
            try:
                driver.delete_all_cookies()
            except Exception:
                pass
        else:
            # Verificar se ja esta logado via cookies salvos
            if not forcar and verificar_e_aplicar_cookies(driver):
                if SALVAR_COOKIES_AUTOMATICO:
                    try:
                        salvar_cookies_sessao(driver, info_extra='cookies_reutilizados_login_cpf')
                    except Exception:
                        pass
                return True

        if not url_login:
            url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'

        logger.info("[LOGIN_CPF] Navegando para a pagina de login: %s", url_login)
        driver.get(url_login)
        espera.ate_js(driver, "document.readyState === 'complete'", teto=5)

        # Se ja estamos logados, retorna direto
        try:
            cur = (getattr(driver, 'current_url', '') or '').lower()
            if not any(k in cur for k in ['login', 'auth', 'realms']) and sessao_oauth_completa(driver):
                logger.info('[LOGIN_CPF] Ja autenticado (URL indica sessao ativa)')
                return True
        except Exception:
            pass

        # Obter credenciais do Gerenciador de Credenciais do Windows (keyring)
        if not cpf or not senha:
            if not cpf:
                cpf = obter_credencial(
                    'PJE_CPF',
                    servicos=('pjeplus', 'pje', 'sisbajud', 'SISB'),
                    aliases=('PJE_USER', 'CPF', 'PJE_SILAS', 'SILAS', 'SISB_CPF', 'BP_SISB')
                )
            if not senha:
                senha = obter_credencial(
                    'PJE_SENHA',
                    servicos=('pjeplus', 'pje', 'sisbajud', 'SISB'),
                    aliases=('PJE_PASSWORD', 'SENHA', 'PASSWORD', 'SISB_SENHA', 'BP_PASS')
                )

        if not cpf or not senha:
            logger.warning(
                '[LOGIN_CPF] Credenciais PJE_CPF / PJE_SENHA nao encontradas no '
                'Gerenciador de Credenciais do Windows. Prosseguindo com login manual.'
            )
            return login_manual(driver, aguardar_url_painel=aguardar_url_final)

        # Clicar no botao SSO PDPJ antes de preencher credenciais se presente (LEGADO.md ~15354)
        if espera.ate_aparecer(driver, '#btnSsoPdpj', teto=3):
            try:
                if hasattr(driver, 'page') and driver.page:
                    driver.page.click('#btnSsoPdpj')
                else:
                    safe_click_no_scroll(driver, '#btnSsoPdpj')
                logger.info('[LOGIN_CPF] Botao SSO PDPJ clicado')
                espera.pausa(driver, 1.0)
            except Exception as e:
                logger.debug('[LOGIN_CPF] Aviso ao clicar no botao SSO PDPJ: %s', e)

        # Aguardar campo de usuario do Keycloak (#username) ou campo OTP direto
        if not espera.ate_aparecer(driver, '#username', teto=10):
            if espera.ate_aparecer(driver, '#otp, input[name="otp"]', teto=2):
                logger.info('[LOGIN_CPF] Tela de OTP detectada diretamente sem #username')
            else:
                logger.warning('[LOGIN_CPF] Campo #username nao localizado. Redirecionando para login manual...')
                if _is_driver_headless(driver):
                    logger.error('[LOGIN_CPF] Driver em modo headless — login manual na tela nao suportado.')
                    return False
                return login_manual(driver, aguardar_url_painel=aguardar_url_final)
        else:
            # Preencher CPF e senha
            try:
                from Fix.core import preencher_campo
                if hasattr(driver, 'page') and driver.page:
                    driver.page.fill('#username', str(cpf))
                    driver.page.fill('#password', str(senha))
                else:
                    preencher_campo(driver, '#username', cpf)
                    preencher_campo(driver, '#password', senha)
                logger.info('[LOGIN_CPF] Credenciais preenchidas via Windows Credential Manager')
            except Exception as e:
                logger.error('[LOGIN_CPF] Falha ao preencher credenciais: %s', e)
                if _is_driver_headless(driver):
                    return False
                return login_manual(driver, aguardar_url_painel=aguardar_url_final)

            # Clicar no botao de login (#kc-login - LEGADO.md ~15390)
            try:
                if hasattr(driver, 'page') and driver.page:
                    driver.page.click('#kc-login')
                else:
                    safe_click_no_scroll(driver, '#kc-login')
                logger.info('[LOGIN_CPF] Botao de login clicado (#kc-login)')
            except Exception as e:
                logger.error('[LOGIN_CPF] Falha ao clicar no botao de login: %s', e)
                if _is_driver_headless(driver):
                    return False
                return login_manual(driver, aguardar_url_painel=aguardar_url_final)

        # Aguardar redirecionamento / conclusao do login / tela de OTP
        if aguardar_url_final:
            is_hl = _is_driver_headless(driver)
            timeout_login = 90 if is_hl else 240
            inicio = time.time()
            _urls_pos_login = ('gigs/meu-painel', 'meu-painel', 'quadro-avisos/visualizar', 'pjekz')
            otp_processado = False
            while time.time() - inicio < timeout_login:
                try:
                    cur = (getattr(driver, 'current_url', '') or '').lower()
                    if any(u in cur for u in _urls_pos_login) or (not any(k in cur for k in ['login', 'auth', 'realms']) and sessao_oauth_completa(driver)):
                        if not any(u in cur for u in _urls_pos_login):
                            try:
                                logger.info('[LOGIN_CPF] Sessão ativa detectada. Carregando meu painel...')
                                driver.get('https://pje.trt2.jus.br/pjekz/gigs/meu-painel')
                                espera.ate_js(driver, "document.readyState === 'complete'", teto=5)
                            except Exception:
                                pass
                        logger.info('[LOGIN_CPF] Login realizado com sucesso (URL: %s)', getattr(driver, 'current_url', cur))
                        if SALVAR_COOKIES_AUTOMATICO:
                            try:
                                salvar_cookies_sessao(driver, info_extra='login_cpf')
                            except Exception:
                                pass
                        return True

                    # Verificar se apareceu tela de OTP / validação em 2 etapas
                    if not otp_processado:
                        tem_otp = False
                        if hasattr(driver, 'page') and driver.page:
                            try:
                                loc = driver.page.locator('#otp, input[name="otp"]')
                                if loc.count() > 0 and loc.first.is_visible():
                                    tem_otp = True
                            except Exception:
                                pass
                        elif espera.elemento(driver, '#otp, input[name="otp"]', teto=0.3):
                            tem_otp = True

                        if tem_otp:
                            otp_processado = True
                            if is_hl:
                                logger.info('[LOGIN_CPF] Tela de validação em duas etapas (OTP) detectada (modo headless).')
                                codigo = input("\n[LOGIN] Digite o código de validação (OTP): ").strip()
                                if hasattr(driver, 'page') and driver.page:
                                    driver.page.fill('#otp, input[name="otp"]', codigo)
                                    submetido = False
                                    try:
                                        btn_sub = driver.page.locator('input[type="submit"], button[type="submit"], #kc-login')
                                        if btn_sub.count() > 0 and btn_sub.first.is_visible():
                                            btn_sub.first.click()
                                            submetido = True
                                    except Exception:
                                        pass
                                    if not submetido:
                                        try:
                                            driver.page.locator('#otp, input[name="otp"]').first.press('Enter')
                                        except Exception:
                                            driver.page.keyboard.press('Enter')
                                else:
                                    from Fix.core import preencher_campo
                                    preencher_campo(driver, '#otp', codigo)
                                    safe_click_no_scroll(driver, 'input[type="submit"], button[type="submit"], #kc-login')
                                logger.info('[LOGIN_CPF] Código OTP enviado. Aguardando conclusão do login...')
                                inicio = time.time()
                            else:
                                logger.info(
                                    '[LOGIN_CPF] Tela de validação em duas etapas (OTP) detectada no navegador. '
                                    'Aguardando conclusão do login e carregamento de meu painel...'
                                )
                except Exception:
                    pass
                espera.pausa(driver, 0.5)

            logger.warning('[LOGIN_CPF] Timeout no login automatico por CPF (pode requerer MFA/captcha).')
            if is_hl:
                logger.error('[LOGIN_CPF] Driver em modo headless — login manual na tela nao suportado.')
                return False
            if sessao_oauth_completa(driver):
                return True
            return login_manual(driver, aguardar_url_painel=True)

        return True

    except Exception as e:
        logger.error("ERRO em login_cpf: %s: %s", type(e).__name__, e)
        return False

def _obter_caminhos_ahk():
    """Função auxiliar para obter caminhos AutoHotkey (evita duplicação)"""
    try:
        ahk_exe = globals().get('AHK_EXE_ACTIVE')
        ahk_script = globals().get('AHK_SCRIPT_ACTIVE')
        if not ahk_exe or not ahk_script:
            if globals().get('criar_driver') == globals().get('criar_driver_notebook'):
                ahk_exe = globals().get('AHK_EXE_NOTEBOOK')
                ahk_script = globals().get('AHK_SCRIPT_NOTEBOOK')
            else:
                ahk_exe = globals().get('AHK_EXE_PC')
                ahk_script = globals().get('AHK_SCRIPT_PC')
    except Exception:
        ahk_exe = globals().get('AHK_EXE_PC')
        ahk_script = globals().get('AHK_SCRIPT_PC')
    
    return ahk_exe, ahk_script

def login_pc(driver):
    """Processo de login humanizado via AutoHotkey, aguardando login terminar antes de prosseguir."""
    import subprocess
    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    driver.get(login_url)
    logger.info("[LOGIN_PC] Navegando para URL de login: %s", login_url)
    try:
        btn_sso = espera.elemento(driver, "#btnSsoPdpj")
        if btn_sso:
            btn_sso.click()
        logger.debug("[LOGIN_PC] Botao #btnSsoPdpj clicado")
        btn_certificado = espera.elemento(driver, ".botao-certificado-titulo")
        if btn_certificado:
            btn_certificado.click()
        logger.debug("[LOGIN_PC] Botao .botao-certificado-titulo clicado")
        espera.assentar(driver, 1)
        subprocess.Popen([r"C:\\Program Files\\AutoHotkey\\AutoHotkey.exe", r"D:\\PjePlus\\Login.ahk"])
        logger.debug("[LOGIN_PC] Script AutoHotkey chamado para digitar a senha")
        for _ in range(60):
            if "login" not in driver.current_url.lower():
                logger.debug("[LOGIN_PC] Login detectado, prosseguindo")
                return True
            espera.assentar(driver, 1)
        logger.error("ERRO em login_pc: Timeout aguardando login")
        return False
    except Exception as e:
        logger.error("ERRO em login_pc: %s: %s", type(e).__name__, e)
        return False

def salvar_cookies_sessao(driver, caminho_arquivo=None, info_extra=None):
    """
    Salva todos os cookies da sessão Selenium em um arquivo JSON.
    O nome do arquivo inclui data/hora e info_extra se fornecido.
    """
    try:
        cookies = driver.get_cookies()
        if not cookies:
            logger.debug('[COOKIES] Nenhum cookie encontrado para salvar')
            return False
        if not caminho_arquivo:
            pasta = os.path.join(os.getcwd(), 'cookies_sessoes')
            os.makedirs(pasta, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            info = f'_{info_extra}' if info_extra else ''
            caminho_arquivo = os.path.join(pasta, f'cookies_sessao{info}_{timestamp}.json')

        dados_cookies = {
            'timestamp': datetime.now().isoformat(),
            'url_base': driver.current_url,
            'cookies': cookies
        }

        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_cookies, f, ensure_ascii=False, indent=2)
        logger.debug('[COOKIES] Cookies salvos em: %s', caminho_arquivo)
        return True
    except Exception as e:
        logger.error("ERRO em salvar_cookies_sessao: %s: %s", type(e).__name__, e)
        return False

def carregar_cookies_sessao(driver, max_idade_horas=24):
    """
    Carrega cookies de sessão mais recentes e válidos automaticamente.
    Retorna True se cookies foram carregados com sucesso, False caso contrário.
    """
    try:
        pasta = os.path.join(os.getcwd(), 'cookies_sessoes')
        if not os.path.exists(pasta):
            logger.debug('[COOKIES] Pasta de cookies nao encontrada')
            return False

        arquivos_cookies = glob.glob(os.path.join(pasta, 'cookies_sessao*.json'))
        if not arquivos_cookies:
            logger.debug('[COOKIES] Nenhum arquivo de cookies encontrado')
            return False

        arquivo_mais_recente = max(arquivos_cookies, key=os.path.getmtime)
        
        with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Verifica se é formato antigo ou novo
        if 'timestamp' in dados:
            timestamp_str = dados['timestamp']
            cookies = dados['cookies']
        else:
            # Formato antigo - usa timestamp do arquivo
            timestamp_str = datetime.fromtimestamp(os.path.getmtime(arquivo_mais_recente)).isoformat()
            cookies = dados

        # Verifica idade dos cookies
        timestamp_cookies = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+00:00', ''))
        idade = datetime.now() - timestamp_cookies

        if idade > timedelta(hours=max_idade_horas):
            logger.debug('[COOKIES] Cookies muito antigos (%.1fh). Pulando.', idade.total_seconds()/3600)
            return False

        driver.get('https://pje.trt2.jus.br/primeirograu/')

        cookies_carregados = 0
        for cookie in cookies:
            try:
                cookie_limpo = {k: v for k, v in cookie.items() if k not in ['expiry', 'httpOnly', 'secure', 'sameSite']}
                driver.add_cookie(cookie_limpo)
                cookies_carregados += 1
            except Exception as e:
                logger.warning('carregar_cookies_sessao: Erro ao carregar cookie %s: %s', cookie.get("name", "unknown"), e)

        logger.debug('[COOKIES] %s cookies carregados de %s', cookies_carregados, os.path.basename(arquivo_mais_recente))

        driver.get('https://pje.trt2.jus.br/pjekz/gigs/meu-painel')
        espera.ate_url(driver, "gigs/meu-painel", teto=5)

        if 'acesso-negado' in driver.current_url.lower():
            logger.warning('[COOKIES] URL de acesso negado detectada. Apagando cookies carregados.')
            try:
                driver.delete_all_cookies()
                logger.debug('[COOKIES] Cookies apagados do navegador')
            except Exception as e:
                logger.warning('[COOKIES] Erro ao apagar cookies: %s', e)
            return False

        if 'login' in driver.current_url.lower():
            logger.warning('[COOKIES] Cookies invalidos - ainda redirecionando para login')
            return False

        if not sessao_oauth_completa(driver):
            logger.warning('[COOKIES] URL ok mas access_token ausente (handshake OAuth incompleto) - cookies invalidos')
            try:
                driver.delete_all_cookies()
            except Exception:
                pass
            return False

        logger.debug('[COOKIES] Cookies validos! Login automatico realizado')
        return True

    except Exception as e:
        logger.error("ERRO em carregar_cookies_sessao: %s: %s", type(e).__name__, e)
        return False

def verificar_e_aplicar_cookies(driver):
    """
    Função integrada que verifica e aplica cookies automaticamente.
    Retorna True se login via cookies foi bem-sucedido.
    """
    if not USAR_COOKIES_AUTOMATICO:
        return False

    logger.info('[COOKIES] Tentando login automatico via cookies salvos...')
    sucesso = carregar_cookies_sessao(driver)

    if sucesso:
        try:
            current_url = driver.current_url
            if 'acesso-negado' in current_url:
                logger.warning('[COOKIES] Acesso negado detectado apos aplicar cookies - forcando login CPF...')

                url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
                logger.info("[COOKIES][LOGIN_FORCE] Navegando para: %s", url_login)
                driver.get(url_login)
                espera.ate_js(driver, "document.readyState === 'complete'", teto=5)

                try:
                    cpf = obter_credencial('PJE_SILAS', servicos=('pjeplus',),
                                           aliases=('PJE_USER', 'PJE_CPF', 'PJE_LOGIN'))
                    senha = obter_credencial('PJE_SENHA', servicos=('pjeplus',),
                                             aliases=('PJE_PASSWORD', 'PJE_PASS'))
                    if not cpf or not senha:
                        logger.error('ERRO em verificar_e_aplicar_cookies: Credenciais ausentes para login forcado')
                        return False

                    username_field = espera.elemento(driver, '[name="username"]')
                    password_field = espera.elemento(driver, '[name="password"]')
                    submit_button = espera.elemento(driver, 'input[type="submit"], button[type="submit"]')

                    from Fix.core import preencher_campo
                    preencher_campo(driver, '[name="username"]', cpf, limpar=True)
                    espera.assentar(driver, 0.3)

                    preencher_campo(driver, '[name="password"]', senha, limpar=True)
                    espera.assentar(driver, 0.3)

                    submit_button.click()
                    espera.assentar(driver, 3)

                    if SALVAR_COOKIES_AUTOMATICO:
                        salvar_cookies_sessao(driver, info_extra='login_forcado_apos_acesso_negado')

                    logger.info('[COOKIES] Login forcado realizado apos acesso negado!')
                    return True

                except Exception as e:
                    logger.error("ERRO em verificar_e_aplicar_cookies: Falha no login forcado: %s", e)
                    return False
            else:
                logger.info('[COOKIES] Login realizado via cookies!')
        except Exception as e:
            logger.warning('[COOKIES] Erro ao verificar URL atual: %s', e)
    else:
        logger.warning('[COOKIES] Cookies invalidos ou inexistentes. Login manual necessario.')

    return sucesso
