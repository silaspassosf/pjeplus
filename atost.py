# atost.py - Versão customizada de atos.py para ambiente e caminhos específicos
from Fix import (
    safe_click,
    esperar_elemento,
    criar_gigs,
    aplicar_filtro_100,
    limpar_temp_selenium,
    buscar_seletor_robusto,
    preencher_campos_prazo,
    esperar_url_conter,
    buscar_documentos_sequenciais,
    indexar_e_processar_lista
)
from selenium.webdriver.common.keys import Keys
import os
import logging
import time
from selectors_pje import BTN_TAREFA_PROCESSO
from selenium.webdriver.common.by import By

# --- Configurações customizadas ---
FIREFOX_PROFILE_PATH = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2y17wq63.default'
FIREFOX_EXECUTABLE_PATH = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
GECKODRIVER_PATH = r'C:\Users\s164283\Desktop\pjeplus\geckodriver.exe'
LOGIN_AHK_PATH = r'C:\Users\s164283\Desktop\pjeplus\Login.ahk'
DADOS_ATUAIS_PATH = r'C:\Users\s164283\Desktop\pjeplus\dadosatuais.json'
AHK_ROOT = r'C:\Users\s164283\Desktop\pjeplus\AHK\UX'

# ...existing code...
# Copie o restante do código de atos.py aqui, sem alterar as demais funções.
# ...existing code...
