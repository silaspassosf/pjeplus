"""
Configurações centralizadas do sistema P2B
"""

import os

# Configurações de arquivo de estado
STATE_FILE = "progresso_p2b.json"

# Configurações de debug
DEBUG_MODE = os.getenv('P2B_DEBUG', 'false').lower() == 'true'

# Configurações de timeout
DEFAULT_TIMEOUT = 30
ELEMENT_WAIT_TIMEOUT = 15

# Configurações de JavaScript
JS_EXECUTION_TIMEOUT = 60

# Configurações de logging
LOG_LEVEL = 'DEBUG' if DEBUG_MODE else 'INFO'
LOG_FILE = 'p2b_refatorado.log'

# URLs do PJE
PJE_BASE_URL = os.getenv('PJE_BASE_URL', 'https://pje.trt2.jus.br/pjekz')
PJE_LOGIN_URL = os.getenv('PJE_LOGIN_URL', f'{PJE_BASE_URL}/login')
PJE_ESCANINHO_URL = os.getenv('PJE_ESCANINHO_URL', f'{PJE_BASE_URL}/escaninho/documentos-internos')
PJE_ATIVIDADES_URL = os.getenv('PJE_ATIVIDADES_URL', f'{PJE_BASE_URL}/gigs/relatorios/atividades')

# Configurações de filtros
DEFAULT_FILTERS = {
    'observacao_filter': 'xs',
    'items_per_page': 100,
    'vencidas_filter': False
}

# Tipos de documento suportados
SUPPORTED_DOCUMENT_TYPES = [
    'Certidão devolução pesquisa',
    'Certidão de oficial de justiça',
    'Alvará',
    'Decisão (Sobrestamento)',
    'SerasaAntigo',
    'Serasa',
    'CNIB'
]

# Configurações de recuperação de sessão
SESSION_RECOVERY_ATTEMPTS = 3
SESSION_RECOVERY_DELAY = 5