import logging
import keyring
import os

logger = logging.getLogger(__name__)

"""
Fix.utils_paths - Módulo para gerenciamento de caminhos do sistema via credenciais do Windows.

Este módulo permite armazenar e recuperar caminhos do sistema (como perfis do Firefox e executáveis)
usando o keyring do Windows, permitindo configurações específicas por máquina sem alterar o código.
"""

def obter_caminho_perfil_firefox() -> str:
    """
    Obtém o caminho do perfil do Firefox a partir das credenciais do Windows.

    Returns:
        str: Caminho do perfil do Firefox ou valor padrão se não encontrado
    """
    try:
        perfil_path = keyring.get_password('pjeplus_paths', 'FIREFOX_PROFILE_PATH')
        if perfil_path and os.path.exists(perfil_path):
            logger.info(f"[PATHS] Perfil Firefox obtido via credenciais: {perfil_path}")
            return perfil_path
        else:
            # Valor padrão caso não esteja configurado nas credenciais
            default_path = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
            logger.info(f"[PATHS] Usando caminho padrão para perfil Firefox: {default_path}")
            return default_path
    except Exception as e:
        logger.error(f"[PATHS] Erro ao obter caminho do perfil Firefox: {e}")
        default_path = r"C:\Users\Silas\AppData\Roaming\Mozilla\Dev\Selenium"
        logger.info(f"[PATHS] Usando caminho padrão: {default_path}")
        return default_path

def obter_caminho_firefox_executavel() -> str:
    """
    Obtém o caminho do executável do Firefox a partir das credenciais do Windows.

    Returns:
        str: Caminho do executável do Firefox ou valor padrão se não encontrado
    """
    try:
        exe_path = keyring.get_password('pjeplus_paths', 'FIREFOX_BINARY')
        if exe_path and os.path.exists(exe_path):
            logger.info(f"[PATHS] Executável Firefox obtido via credenciais: {exe_path}")
            return exe_path
        else:
            # Valor padrão caso não esteja configurado nas credenciais
            default_path = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
            logger.info(f"[PATHS] Usando caminho padrão para executável Firefox: {default_path}")
            return default_path
    except Exception as e:
        logger.error(f"[PATHS] Erro ao obter caminho do executável Firefox: {e}")
        default_path = r"C:\Program Files\Firefox Developer Edition\firefox.exe"
        logger.info(f"[PATHS] Usando caminho padrão: {default_path}")
        return default_path

def obter_caminho_geckodriver() -> str:
    """
    Obtém o caminho do geckodriver a partir das credenciais do Windows.

    Returns:
        str: Caminho do geckodriver ou valor padrão se não encontrado
    """
    try:
        gecko_path = keyring.get_password('pjeplus_paths', 'GECKODRIVER_PATH')
        if gecko_path and os.path.exists(gecko_path):
            logger.info(f"[PATHS] Geckodriver obtido via credenciais: {gecko_path}")
            return gecko_path
        else:
            # Valor padrão caso não esteja configurado nas credenciais
            default_path = r"d:\PjePlus\Fix\geckodriver.exe"
            logger.info(f"[PATHS] Usando caminho padrão para geckodriver: {default_path}")
            return default_path
    except Exception as e:
        logger.error(f"[PATHS] Erro ao obter caminho do geckodriver: {e}")
        default_path = r"d:\PjePlus\Fix\geckodriver.exe"
        logger.info(f"[PATHS] Usando caminho padrão: {default_path}")
        return default_path

def obter_caminho_perfil_vt_pje() -> str:
    """
    Obtém o caminho do perfil VT PJE a partir das credenciais do Windows.

    Returns:
        str: Caminho do perfil VT PJE ou valor padrão se não encontrado
    """
    try:
        vt_profile = keyring.get_password('pjeplus_paths', 'VT_PROFILE_PJE')
        if vt_profile and os.path.exists(vt_profile):
            logger.info(f"[PATHS] Perfil VT PJE obtido via credenciais: {vt_profile}")
            return vt_profile
        else:
            # Valor padrão caso não esteja configurado nas credenciais
            default_path = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
            logger.info(f"[PATHS] Usando caminho padrão para perfil VT PJE: {default_path}")
            return default_path
    except Exception as e:
        logger.error(f"[PATHS] Erro ao obter caminho do perfil VT PJE: {e}")
        default_path = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
        logger.info(f"[PATHS] Usando caminho padrão: {default_path}")
        return default_path

def obter_caminho_perfil_vt_pje_alt() -> str:
    """
    Obtém o caminho alternativo do perfil VT PJE a partir das credenciais do Windows.

    Returns:
        str: Caminho alternativo do perfil VT PJE ou valor padrão se não encontrado
    """
    try:
        vt_profile_alt = keyring.get_password('pjeplus_paths', 'VT_PROFILE_PJE_ALT')
        if vt_profile_alt and os.path.exists(vt_profile_alt):
            logger.info(f"[PATHS] Perfil VT PJE alternativo obtido via credenciais: {vt_profile_alt}")
            return vt_profile_alt
        else:
            # Valor padrão caso não esteja configurado nas credenciais
            default_path = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'
            logger.info(f"[PATHS] Usando caminho padrão para perfil VT PJE alternativo: {default_path}")
            return default_path
    except Exception as e:
        logger.error(f"[PATHS] Erro ao obter caminho do perfil VT PJE alternativo: {e}")
        default_path = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'
        logger.info(f"[PATHS] Usando caminho padrão: {default_path}")
        return default_path

def obter_caminho_firefox_alt() -> str:
    """
    Obtém o caminho alternativo do executável do Firefox a partir das credenciais do Windows.

    Returns:
        str: Caminho alternativo do executável do Firefox ou valor padrão se não encontrado
    """
    try:
        firefox_alt = keyring.get_password('pjeplus_paths', 'FIREFOX_BINARY_ALT')
        if firefox_alt and os.path.exists(firefox_alt):
            logger.info(f"[PATHS] Executável Firefox alternativo obtido via credenciais: {firefox_alt}")
            return firefox_alt
        else:
            # Valor padrão caso não esteja configurado nas credenciais
            default_path = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
            logger.info(f"[PATHS] Usando caminho padrão para executável Firefox alternativo: {default_path}")
            return default_path
    except Exception as e:
        logger.error(f"[PATHS] Erro ao obter caminho do executável Firefox alternativo: {e}")
        default_path = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
        logger.info(f"[PATHS] Usando caminho padrão: {default_path}")
        return default_path

def configurar_caminho_credencial(nome_credencial: str, caminho: str) -> bool:
    """
    Configura um caminho específico nas credenciais do Windows.

    Args:
        nome_credencial: Nome da credencial (ex: 'FIREFOX_PROFILE_PATH', 'FIREFOX_BINARY')
        caminho: Caminho completo para o arquivo/diretório

    Returns:
        bool: True se a configuração foi bem sucedida, False caso contrário
    """
    try:
        keyring.set_password('pjeplus_paths', nome_credencial, caminho)
        logger.info(f"[PATHS] Caminho '{nome_credencial}' configurado com sucesso: {caminho}")
        return True
    except Exception as e:
        logger.error(f"[PATHS] Erro ao configurar caminho '{nome_credencial}': {e}")
        return False

def exibir_configuracao_atual():
    """Exibe a configuração atual de caminhos"""
    logger.info("[PATHS] Configuração atual de caminhos:")
    logger.info(f"[PATHS] Perfil Firefox: {obter_caminho_perfil_firefox()}")
    logger.info(f"[PATHS] Executável Firefox: {obter_caminho_firefox_executavel()}")
    logger.info(f"[PATHS] Geckodriver: {obter_caminho_geckodriver()}")
    logger.info(f"[PATHS] Perfil VT PJE: {obter_caminho_perfil_vt_pje()}")
    logger.info(f"[PATHS] Perfil VT PJE Alt: {obter_caminho_perfil_vt_pje_alt()}")
    logger.info(f"[PATHS] Executável Firefox Alt: {obter_caminho_firefox_alt()}")