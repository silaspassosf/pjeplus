import logging
import os

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

TIPO_EXECUCAO = 'prov'
URL_PAINEL = 'https://pje.trt2.jus.br/pjekz/painel/global/6/lista-processos'

# Caminhos do Geckodriver
GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), '..', 'Fix', 'geckodriver.exe')
if not os.path.exists(GECKODRIVER_PATH):
    # Fallback: tenta na raiz
    GECKODRIVER_PATH = os.path.join(os.path.dirname(__file__), '..', 'geckodriver.exe')

# Firefox Developer Edition
FIREFOX_BINARY = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
FIREFOX_BINARY_ALT = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'

# Perfis VT
VT_PROFILE_PJE = r'C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\13zemix3.default-release-1623328432485'
VT_PROFILE_PJE_ALT = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2bge54ld.Robot'

# Uso de perfil compartilhado deixa o startup mais lento; desligado por padrão
USAR_PERFIL_VT = False

# Suprimir logs internos
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)