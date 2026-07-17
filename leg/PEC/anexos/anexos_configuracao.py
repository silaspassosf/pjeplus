"""
PEC.anexos.configuracao - Módulo de funções de configuração.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém funções de configuração e utilitários diversos.
"""

import logging
logger = logging.getLogger(__name__)

import os
import re
import time
import pyperclip
from typing import Optional, Dict, Any, Callable, Union, List
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Imports do Fix
from Fix.core import (
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    safe_click,
    wait_for_clickable,
    wait_for_visible,
)
from Fix.utils import (
    inserir_html_no_editor_apos_marcador,
    obter_ultimo_conteudo_clipboard,
    executar_coleta_parametrizavel,
    inserir_link_ato_validacao,
)

# Imports dos módulos refatorados
from .anexos_extracao import extrair_numero_processo_da_url


def salvar_conteudo_clipboard(conteudo: str, numero_processo: str, tipo_conteudo: str = "generico", debug: bool = True) -> bool:
    """
    Salva conteúdo no clipboard.txt em formato simplificado: apenas PROCESSO e CONTEÚDO.

    Observação: O parâmetro tipo_conteudo é mantido para compatibilidade, mas não é mais
    persistido no arquivo. O histórico permanece por entradas sequenciais.

    Args:
        conteudo: O conteúdo a ser salvo
        numero_processo: Número do processo (obrigatório)
        tipo_conteudo: Tipo do conteúdo (informativo)
        debug: Se deve exibir logs
    """
    if debug:
        print(f"[CLIPBOARD] Salvando conteúdo tipo '{tipo_conteudo}'...")

    try:
        # Validar número do processo
        if not numero_processo:
            raise ValueError("Número do processo é obrigatório e deve ser fornecido pela função chamadora")

        # Preparar o registro (formato novo: somente PROCESSO + CONTEÚDO)
        separador = "=" * 50
        registro = (
            "\n" +
            separador + "\n" +
            f"PROCESSO: {numero_processo}\n" +
            separador + "\n" +
            f"{conteudo}\n" +
            separador + "\n\n"
        )

        # Salvar no arquivo (modo append para manter histórico)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        clipboard_file = os.path.join(base_dir, "clipboard.txt")
        os.makedirs(base_dir, exist_ok=True)
        with open(clipboard_file, 'a', encoding='utf-8', newline='') as f:
            f.write(registro)
            f.flush()

        if debug:
            print(f"[CLIPBOARD] ✅ Conteúdo salvo: {len(conteudo)} chars")
            print(f"[CLIPBOARD] ✅ Processo: {numero_processo}")
            print(f"[CLIPBOARD] ✅ Tipo (informativo): {tipo_conteudo}")
            print(f"[CLIPBOARD] ✅ Arquivo: {clipboard_file}")

        return True

    except Exception as e:
        if debug:
            try:
                print(f"[CLIPBOARD] ✗ Erro ao salvar: {e}")
                print(f"[CLIPBOARD] CWD: {os.getcwd()}")
                base_dir = os.path.dirname(os.path.abspath(__file__))
                print(f"[CLIPBOARD] Destino esperado: {os.path.join(base_dir, 'clipboard.txt')}")
            except Exception:
                pass
        return False