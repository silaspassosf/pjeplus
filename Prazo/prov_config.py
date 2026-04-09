import logging
import os

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

TIPO_EXECUCAO = 'prov'
URL_PAINEL = 'https://pje.trt2.jus.br/pjekz/painel/global/6/lista-processos'

# Importar funções de caminhos
from ..Fix.utils_paths import (
    obter_caminho_geckodriver,
    obter_caminho_firefox_executavel,
    obter_caminho_firefox_alt,
    obter_caminho_perfil_vt_pje,
    obter_caminho_perfil_vt_pje_alt
)

# Caminhos do Geckodriver
GECKODRIVER_PATH = obter_caminho_geckodriver()

# Firefox Developer Edition
FIREFOX_BINARY = obter_caminho_firefox_executavel()
FIREFOX_BINARY_ALT = obter_caminho_firefox_alt()

# Perfis VT
VT_PROFILE_PJE = obter_caminho_perfil_vt_pje()
VT_PROFILE_PJE_ALT = obter_caminho_perfil_vt_pje_alt()

# Uso de perfil compartilhado deixa o startup mais lento; desligado por padrão
USAR_PERFIL_VT = False

# Suprimir logs internos
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)