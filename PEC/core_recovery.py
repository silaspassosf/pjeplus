import logging
logger = logging.getLogger(__name__)

import time

from .core_progresso import verificar_acesso_negado_pec


def verificar_e_recuperar_acesso_negado(driver, criar_driver_func, login_func):
    """
    Verifica se o driver está em estado de acesso negado e tenta recuperar.

    Returns:
        tuple: (driver_valido, foi_recuperado)
    """
    try:
        if not verificar_acesso_negado_pec(driver):
            return driver, False

        try:
            driver.quit()
        except Exception as e:
            logger.error(f"[RECOVERY]  Erro ao fechar driver: {e}")

        novo_driver = criar_driver_func(headless=False)
        if not novo_driver:
            raise Exception("Falha ao criar driver durante recuperação")

        if not login_func(novo_driver):
            novo_driver.quit()
            raise Exception("Falha no login durante recuperação")

        return novo_driver, True

    except Exception as e:
        logger.error(f"[RECOVERY]  Erro crítico na recuperação: {e}")
        raise


def reiniciar_driver_e_logar_pje(driver, log=True):
    """
    Reinicia o driver do PJe e executa o login.
    Retorna o novo driver se bem-sucedido, ou None em caso de falha.
    """
    try:
        try:
            driver.quit()
        except Exception:
            pass

        from Fix.core import criar_driver_PC
        from Fix.utils import login_cpf

        novo_driver = criar_driver_PC(headless=False)
        if not novo_driver:
            return None

        ok = False
        try:
            ok = login_cpf(novo_driver)
        except Exception as e:
            if log:
                logger.error(f"[RECOVERY][RESTART] Erro ao executar login_func: {e}")
            ok = False

        if not ok:
            try:
                novo_driver.quit()
            except Exception:
                pass
            return None

        try:
            url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
            novo_driver.get(url_atividades)
            time.sleep(4)
            try:
                from Fix.navigation import aplicar_filtro_100
                aplicar_filtro_100(novo_driver)
                time.sleep(1)
            except Exception:
                pass
        except Exception:
            pass

        return novo_driver

    except Exception as e:
        logger.error(f"[RECOVERY][RESTART][ERRO] Exceção inesperada: {e}")
        return None
