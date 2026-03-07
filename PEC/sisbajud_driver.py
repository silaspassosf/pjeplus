import logging
logger = logging.getLogger(__name__)

"""Gerenciamento de driver SISBAJUD global persistente."""

# ===== DRIVER SISBAJUD GLOBAL PERSISTENTE =====
# Mantém um único driver SISBAJUD durante toda a sessão PEC
_DRIVER_SISBAJUD_GLOBAL = None


def get_or_create_driver_sisbajud(driver_pje):
    """
    Retorna o driver SISBAJUD global existente ou cria um novo se necessário.
    Esta função garante que apenas um driver SISBAJUD seja usado durante toda a sessão.
    """
    global _DRIVER_SISBAJUD_GLOBAL
    
    # Se já existe e ainda está válido, reutilizar
    if _DRIVER_SISBAJUD_GLOBAL:
        try:
            # Verificar se o driver ainda está ativo
            _ = _DRIVER_SISBAJUD_GLOBAL.current_url
            logger.info('[SISBAJUD_GLOBAL]  Reutilizando driver SISBAJUD existente')
            return _DRIVER_SISBAJUD_GLOBAL
        except Exception:
            logger.info('[SISBAJUD_GLOBAL]  Driver anterior inválido, criando novo...')
            _DRIVER_SISBAJUD_GLOBAL = None
    
    # Criar novo driver SISBAJUD
    logger.info('[SISBAJUD_GLOBAL]  Criando novo driver SISBAJUD global...')
    try:
        # Importar dinamicamente para evitar erros de módulo
        try:
            from SISB import core as sisb_core
        except:
            import sisb as sisb_core
        
        _DRIVER_SISBAJUD_GLOBAL = sisb_core.iniciar_sisbajud(driver_pje=driver_pje, extrair_dados=False)
        
        if _DRIVER_SISBAJUD_GLOBAL:
            logger.info('[SISBAJUD_GLOBAL]  Driver SISBAJUD global criado com sucesso')
        else:
            logger.info('[SISBAJUD_GLOBAL]  Falha ao criar driver SISBAJUD global')
        
        return _DRIVER_SISBAJUD_GLOBAL
    except Exception as e:
        logger.info(f'[SISBAJUD_GLOBAL]  Erro ao criar driver SISBAJUD: {e}')
        import traceback
        logger.exception("Erro detectado")
        return None


def fechar_driver_sisbajud_global():
    """Fecha o driver SISBAJUD global se existir."""
    global _DRIVER_SISBAJUD_GLOBAL
    if _DRIVER_SISBAJUD_GLOBAL:
        logger.info('[SISBAJUD_GLOBAL]  Fechando driver SISBAJUD global...')
        try:
            _DRIVER_SISBAJUD_GLOBAL.quit()
            logger.info('[SISBAJUD_GLOBAL]  Driver SISBAJUD fechado com sucesso')
        except Exception as e:
            # Ignorar erros de conexão ao fechar driver já inativo
            logger.debug(f'[SISBAJUD_GLOBAL]  Driver já estava inativo ou erro ao fechar: {e}')
        finally:
            _DRIVER_SISBAJUD_GLOBAL = None
