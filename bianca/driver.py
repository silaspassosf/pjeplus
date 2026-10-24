# -*- coding: utf-8 -*-
"""
bianca/driver.py - Driver e login do fluxo Bianca.

O driver vem do mesmo criador usado por pw.py (Fix.driver_factory.criar_driver_PC)
e o login usa a sessao canonica (Fix.sessao), com credenciais do Gerenciador de
Credenciais do Windows. Nao ha caminho de login por input() no terminal.
"""

from typing import Optional, Any

from Fix.log import logger


# =============================================================================
# Driver
# =============================================================================

def criar_driver() -> Any:
    """Cria o driver Playwright (mesmo criador de pw.py/x.py)."""
    from Fix.driver_factory import criar_driver_PC
    return criar_driver_PC()


# =============================================================================
# Login
# =============================================================================

def fazer_login_manual(driver: Any) -> None:
    """Autentica no PJe com a sessao canonica.

    Mantem o nome historico (chamado por bianca/triagem/runner.py), mas delega
    para Fix.sessao.login_cpf, que le as credenciais do Gerenciador de
    Credenciais do Windows e trata SSO, OTP e o fallback manual no navegador.
    """
    from Fix.sessao import login_cpf
    login_cpf(driver)


# =============================================================================
# Verificacao e recuperacao de sessao
# =============================================================================


def verificar_sessao(driver: Any) -> bool:
    """True se a URL atual nao indica pagina de login, erro ou acesso negado."""
    try:
        url = (driver.current_url or '').lower()
    except Exception:
        return False

    if any(k in url for k in ["login", "auth", "realms", "acesso-negado", "error"]):
        logger.warning("Sessao invalida — URL atual: %s", url[:120])
        return False

    return True


def resetar_driver(driver: Any) -> bool:
    """Tenta recuperar a sessao: refresh, depois navegacao para a base."""
    from Fix import espera

    try:
        logger.info("Resetando driver — tentando refresh...")
        driver.refresh()
        espera.assentar(driver, 2.0)

        if verificar_sessao(driver):
            logger.info("Driver recuperado apos refresh.")
            return True

        try:
            from bianca.config import URL_PJE_BASE

            logger.info("Refresh insuficiente — navegando para PJE_BASE...")
            driver.get(URL_PJE_BASE)
            espera.assentar(driver, 3.0)
        except Exception:
            pass

        return verificar_sessao(driver)
    except Exception as e:
        logger.error("Erro ao resetar driver: %s", e)
        return False


# =============================================================================
# Combinado
# =============================================================================

def criar_driver_e_fazer_login() -> Optional[Any]:
    """Cria o driver e autentica. Retorna o driver ou None se falhar."""
    try:
        driver = criar_driver()
    except Exception as e:
        logger.error("Falha ao criar driver: %s", e)
        return None

    try:
        fazer_login_manual(driver)
    except Exception as e:
        logger.error("Falha durante login: %s", e)
        try:
            driver.quit()
        except Exception:
            pass
        return None

    return driver
