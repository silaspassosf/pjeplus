"""
Andrei.config - Configuracoes do modulo Andrei para processamento de petitions no PJe.
"""

from pathlib import Path

# =============================================================================
# Caminhos do sistema
# =============================================================================

# Localizacao do geckodriver (Firefox) dentro do modulo Andrei
GECKODRIVER_PATH = Path(__file__).parent / "drivers" / "geckodriver.exe"

# Binario do Firefox (Developer Edition) usado pelo Selenium
# Mesmo padrao usado em Fix/core.py (obter_driver_padronizado)
FIREFOX_BINARY = r"C:\Program Files\Firefox Developer Edition\firefox.exe"

# =============================================================================
# URLs do PJe TRT2
# =============================================================================

PJE_BASE_URL = "https://pje.trt2.jus.br"
ESCANINHO_URL = "https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas"

# =============================================================================
# Arquivos de dados e logs
# =============================================================================

DADOSATUAIS_JSON = "Andrei/dadosatuais.json"
LOG_DIR = "Andrei/logs"

# =============================================================================
# Timeouts (segundos)
# =============================================================================

# Tempo maximo para aguardar login manual do usuario
LOGIN_TIMEOUT = 300

# Timeout padrao para espera de elementos na pagina
DEFAULT_TIMEOUT = 10

# =============================================================================
# NOTA: Perfil do Firefox
# =============================================================================
# Nao ha FIREFOX_PROFILE_PATH fixo.
# O perfil e sempre criado via tempfile.mkdtemp() em Andrei/driver.py
# e removido ao fechar o driver.
