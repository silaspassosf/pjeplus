"""atos.anexos.configuracao - Módulo de funções de configuração."""

import logging
logger = logging.getLogger(__name__)

import os
import re
import time
import pyperclip
from typing import Optional, Dict, Any, Callable, Union, List

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

from .anexos_extracao import extrair_numero_processo_da_url


def salvar_conteudo_clipboard(conteudo: str, numero_processo: str, tipo_conteudo: str = "generico", debug: bool = True) -> bool:
    """Salva conteúdo no clipboard.txt em formato simplificado: apenas PROCESSO e CONTEÚDO."""
    if debug:
        logger.info(f"[CLIPBOARD] Salvando conteúdo tipo '{tipo_conteudo}'...")

    try:
        if not numero_processo:
            raise ValueError("Número do processo é obrigatório e deve ser fornecido pela função chamadora")

        separador = "=" * 50
        registro = (
            "\n" +
            separador + "\n" +
            f"PROCESSO: {numero_processo}\n" +
            separador + "\n" +
            f"{conteudo}\n" +
            separador + "\n\n"
        )

        projeto_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        clipboard_file = os.path.join(projeto_root, 'PEC', 'clipboard.txt')
        os.makedirs(os.path.dirname(clipboard_file), exist_ok=True)
        with open(clipboard_file, 'a', encoding='utf-8', newline='') as f:
            f.write(registro)
            f.flush()

        if debug:
            logger.info(f"[CLIPBOARD] Conteúdo salvo: {len(conteudo)} chars")
            logger.info(f"[CLIPBOARD] Processo: {numero_processo}")
            logger.info(f"[CLIPBOARD] Tipo (informativo): {tipo_conteudo}")
            logger.info(f"[CLIPBOARD] Arquivo: {clipboard_file}")

        return True

    except Exception as e:
        if debug:
            try:
                logger.error(f"[CLIPBOARD] Erro ao salvar: {e}")
                logger.info(f"[CLIPBOARD] CWD: {os.getcwd()}")
                base_dir = os.path.dirname(os.path.abspath(__file__))
                logger.info(f"[CLIPBOARD] Destino esperado: {os.path.join(base_dir, 'clipboard.txt')}")
            except Exception:
                pass
        return False