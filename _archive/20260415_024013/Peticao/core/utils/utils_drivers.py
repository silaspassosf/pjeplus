import logging
logger = logging.getLogger(__name__)

"""
Utils drivers module for Peticao - contains driver management functions
"""

def _obter_caminhos_ahk():
    """Obtém caminhos do executável e script AutoHotkey"""
    # Caminhos padrão - podem ser ajustados conforme necessário
    ahk_exe = r'C:\Program Files\AutoHotkey\AutoHotkey.exe'
    ahk_script = r'D:\PjePlus\Login.ahk'

    return ahk_exe, ahk_script