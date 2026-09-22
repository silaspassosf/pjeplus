# LEGADO — codigo movido para Peticao/runtime_pet.py
# Mantido in-situ para evitar circular import com extracao/extracao.py (congelado)

"""
Utils module for Peticao - contains driver and login utilities
"""

import logging
logger = logging.getLogger(__name__)


def criar_driver_e_logar(driver=None, log=True):
    """Cria driver PC e faz login. Retorna driver pronto ou None em falha.
    Se driver ja fornecido, reutiliza sem novo login (padrao aud.py).
    """
    import traceback as _tb
    if driver is not None:
        if log:
            logger.info('[PET] Usando driver fornecido')
        return driver

    try:
        from Fix.utils import driver_pc as _driver_pc, login_cpf as _login_cpf
    except Exception as e:
        logger.error(f'[PET] Erro ao importar Fix.utils: {e}')
        return None

    if log:
        logger.info('[PET] Criando driver...')
    drv = _driver_pc()
    if not drv:
        logger.error('[PET] Falha ao criar driver')
        return None

    ok = False
    try:
        ok = _login_cpf(drv)
    except Exception as e:
        logger.error(f'[PET] Erro ao executar login_cpf: {e}')
        ok = False

    if not ok:
        try:
            drv.quit()
        except Exception:
            pass
        logger.error('[PET] Login falhou')
        return None

    # Verificar se realmente estamos na sessao correta (nao em acesso-negado)
    try:
        url = (drv.current_url or '').lower()
        if any(k in url for k in ['acesso-negado', 'access-denied', 'login.jsp']):
            logger.warning(f'[PET] Login retornou OK mas URL indica bloqueio: {url}')
            try:
                drv.quit()
            except Exception:
                pass
            return None
    except Exception:
        pass

    if log:
        logger.info('[PET] Login OK')
    return drv
