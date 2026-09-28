# -*- coding: utf-8 -*-
"""
bianca/driver.py - Gerenciamento do driver e login para o fluxo Bianca.
"""

import logging
from typing import Optional, Any

from Fix import espera
from Fix.core import aguardar_e_clicar, preencher_campo, criar_driver_PC

logger = logging.getLogger(__name__)


# =============================================================================
# Driver
# =============================================================================

def criar_driver() -> Any:
    """Cria um driver configurado para o ambiente."""
    return criar_driver_PC()


# =============================================================================
# Login
# =============================================================================

def fazer_login_manual(driver: Any) -> None:
    """Faz login no PJe com CPF e senha fornecidos pelo usuario.

    Etapas:
      1. Le CPF e senha via terminal (input())
      2. Navega para pagina de login do PJe
      3. Tenta preencher campos automaticamente (opcao A)
      4. Se falhar, permite login manual (opcao B)

    Nunca le credenciais de variaveis de ambiente ou arquivos.
    """
    cpf = input("Digite o CPF (somente numeros): ").strip()
    senha = input("Digite a senha: ").strip()

    if not cpf or not senha:
        logger.error("CPF ou senha nao informados. Abortando login.")
        return

    url_login = "https://pje.trt2.jus.br/primeirograu/login.seam"
    logger.info("Navegando para %s", url_login)
    driver.get(url_login)

    # Aguarda carregamento
    espera.ate_js(driver, "document.readyState === 'complete'", teto=10)

    # Se ja estiver logado, retorna
    try:
        cur = (driver.current_url or '').lower()
        if not any(k in cur for k in ["login", "auth", "realms"]):
            logger.info("Ja autenticado.")
            return
    except Exception:
        pass

    # ---- Opcao A: preenchimento automatico ----
    try:
        # Clicar no botao SSO PDPJ
        if aguardar_e_clicar(driver, "#btnSsoPdpj", "Botão SSO PDPJ"):
            logger.info("Botao SSO PDPJ clicado")
            espera.assentar(driver, 1.0)

        # Preencher CPF
        preencher_campo(driver, "#username", str(cpf))
        logger.info("CPF digitado no campo username")

        # Preencher senha
        preencher_campo(driver, "#password", str(senha))
        logger.info("Senha digitada no campo password")

        # Clicar em Entrar
        aguardar_e_clicar(driver, "button[type='submit'], input[type='submit']", "Entrar")

        # Aguarda redirecionamento
        for _ in range(30):
            try:
                cur = (driver.current_url or '').lower()
                if not any(k in cur for k in ["login", "auth", "realms"]):
                    logger.info("Login automatico bem-sucedido!")
                    return
            except Exception:
                pass
            espera.assentar(driver, 1.0)

        logger.warning(
            "Preenchimento automatico concluido, mas nao foi possivel "
            "confirmar redirecionamento. Prosseguindo..."
        )

    except Exception as e:
        logger.warning(
            "Preenchimento automatico falhou (%s). "
            "Usando opcao B - login manual.",
            e,
        )
        _login_manual_fallback(driver)


def _login_manual_fallback(driver: Any) -> None:
    """Opcao B: usuario faz login manualmente no navegador."""
    print("\n" + "=" * 60)
    print("LOGIN MANUAL")
    print("=" * 60)
    print("Preencha CPF e senha manualmente no navegador aberto.")
    print("Acesse: https://pje.trt2.jus.br/primeirograu/login.seam")
    print("Apos concluir o login, pressione Enter para continuar...")
    input()
    logger.info("Usuario confirmou login manual.")


# =============================================================================
# Verificacao e recuperacao de sessao
# =============================================================================


def verificar_sessao(driver: Any) -> bool:
    """Verifica se a sessao atual ainda e valida.

    Checa se a URL atual nao contem indicadores de pagina de login,
    autenticacao ou acesso negado.

    Args:
        driver: Driver do navegador.

    Returns:
        bool: True se a sessao parece valida, False caso contrario.
    """
    try:
        url = (driver.current_url or '').lower()
    except Exception:
        return False

    if any(k in url for k in ["login", "auth", "realms", "acesso-negado", "error"]):
        logger.warning("Sessao invalida — URL atual: %s", url[:120])
        return False

    return True


def resetar_driver(driver: Any) -> bool:
    """Tenta recuperar sessao do driver: refresh + navegacao para pagina conhecida.

    Args:
        driver: Driver do navegador.

    Returns:
        bool: True se a sessao foi recuperada com sucesso.
    """
    try:
        logger.info("Resetando driver — tentando refresh...")
        driver.refresh()
        espera.assentar(driver, 2.0)

        if verificar_sessao(driver):
            logger.info("Driver recuperado apos refresh.")
            return True

        # Tentar navegar para pagina base conhecida
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
    """Cria o driver e faz login. Retorna o driver ou None se falhar."""
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
