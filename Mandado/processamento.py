import logging
logger = logging.getLogger(__name__)

# m1.py
# Fluxo automatizado de mandados PJe TRT2
###DIRETRIZES MÁXIMAS INEGOCIÁVEIS
# Priorizar edições apenas no código selecionado ou referenciado  
# Sempre validar se as alterações propostas estão estritamente alinhadas com o prompt do usuário.  
# Evitar modificações em arquivos não explicitamente mencionados.  
# Respeitar convenções de estilo definidas no projeto (ex: indentação com tabs, aspas duplas).  
# Workspace preference: NÃO altere, traduza ou reescreva NENHUMA linha do código, exceto exatamente o trecho solicitado.
# NÃO traduza palavras-chave, nomes de variáveis, comentários, strings, nem nada do código.
# NÃO faça ajustes automáticos, refatorações, nem ‘melhorias’ não solicitadas.
# Se precisar editar, use sempre o padrão # ...existing code... para indicar partes não alteradas. 
# As edições devem ser ESPECIFICAMENTE sobre erros de log ou pedidos EXPLICITOS do usuario, nada alem disso.
# tenha em mente que descumprir essas diretizes estraga o codigo e causa perda de tempo
# nao é neceasário varrer o codigo todo para cada edição pedida 
# use a busca de termos para ir diretamente à região correta e edirtar apenas o necessário, para ser mais eficiente
# ====================================================
# BLOCO 0 - GERAL
# ====================================================

# 0. Importações Padrão
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from typing import Optional, Dict, List, Union, Tuple, Callable, Any

# Selenium
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchWindowException,
    StaleElementReferenceException,
)

# ===== IMPORTS PESADOS REMOVIDOS (LAZY LOADING) =====
# Movidos para cache sob demanda para carregamento 8-10x mais rápido
# Anteriormente importados do Fix e outros módulos no topo
# Agora cada função importa apenas o que precisa, quando precisa

# Cache de módulos para lazy loading
_mandado_modules_cache = {}

def _lazy_import_mandado():
    """Carrega módulos pesados sob demanda (lazy loading)."""
    global _mandado_modules_cache
    
    if not _mandado_modules_cache:
        from Fix.core import navegar_para_tela, buscar_seletor_robusto
        from Fix.extracao import extrair_pdf, analise_outros, extrair_documento, extrair_direto, extrair_dados_processo, buscar_mandado_autor, buscar_ultimo_mandado, extrair_destinatarios_decisao, indexar_e_processar_lista
        from Fix.gigs import criar_gigs
        from Fix.selenium_base import esperar_elemento, aguardar_e_clicar
        from Fix.utils import limpar_temp_selenium, configurar_recovery_driver
        
        _mandado_modules_cache.update({
            'navegar_para_tela': navegar_para_tela,
            'extrair_pdf': extrair_pdf,
            'analise_outros': analise_outros,
            'extrair_documento': extrair_documento,
            'extrair_direto': extrair_direto,
            'criar_gigs': criar_gigs,
            'esperar_elemento': esperar_elemento,
            'aguardar_e_clicar': aguardar_e_clicar,
            'buscar_seletor_robusto': buscar_seletor_robusto,
            'limpar_temp_selenium': limpar_temp_selenium,
            'indexar_e_processar_lista': indexar_e_processar_lista,
            'extrair_dados_processo': extrair_dados_processo,
            'buscar_mandado_autor': buscar_mandado_autor,
            'buscar_ultimo_mandado': buscar_ultimo_mandado,
            'extrair_destinatarios_decisao': extrair_destinatarios_decisao,
            'configurar_recovery_driver': configurar_recovery_driver,
        })
    
    return _mandado_modules_cache

# Módulos Locais (mantidos leves)
from Fix.utils import verificar_e_tratar_acesso_negado_global, handle_exception_with_recovery
from Fix.core import buscar_documento_argos
from Fix.selenium_base import preencher_campo
from Fix.extracao import salvar_destinatarios_cache
from Fix.documents import buscar_documentos_sequenciais
from Fix.abas import validar_conexao_driver
from Fix.extracao import criar_lembrete_posit, extrair_pdf
from Fix.log import logger
from atos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    ato_idpj,
    mov_arquivar,
    ato_meiosub
)
from .utils import (
    fechar_intimacao,
    retirar_sigilo,
    retirar_sigilo_fluxo_argos,
    retirar_sigilo_certidao_devolucao_primeiro,
    retirar_sigilo_demais_documentos_especificos,
)
from .regras import aplicar_regras_argos

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

# ====================================================
# CONTROLE DE SESSÃO E PROGRESSO UNIFICADO
# ====================================================

# Use o monitoramento unificado para extração e marcação de progresso
# Isso garante comportamento idêntico ao usado em p2b.py (validação/formato do número)

from .processamento_anexos import (
    _SIGILO_TYPES,
    _SELETORES_ANEXOS,
    _identificar_tipo_anexo,
    _localizar_modal_visibilidade,
    _processar_modal_visibilidade,
    _extrair_executados_pdf,
    processar_sisbajud,
    tratar_anexos_argos,
)
from .processamento_argos import processar_argos
from .processamento_outros import ultimo_mdd, fluxo_mandados_outros
from .processamento_fluxo import fluxo_mandado
            
