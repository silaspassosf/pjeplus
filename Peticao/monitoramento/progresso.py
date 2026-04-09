"""
Sistema de monitoramento de progresso para o módulo Peticao
"""

import os
import json
import time
import re
import shutil
from datetime import datetime
from typing import Optional, Dict, Any
from selenium.webdriver.common.by import By

from ..core.log import get_module_logger

logger = get_module_logger(__name__)

# Arquivo de progresso específico para petições
ARQUIVO_PROGRESSO_PET = "progresso_pet.json"

def carregar_progresso_pet() -> Dict[str, Any]:
    """
    Carrega o estado de progresso do arquivo JSON específico para petições.

    Returns:
        Dict com estado do progresso para petições
    """
    try:
        if os.path.exists(ARQUIVO_PROGRESSO_PET):
            with open(ARQUIVO_PROGRESSO_PET, "r", encoding="utf-8") as f:
                dados = json.load(f)

                # Verificar se é um dicionário válido
                if not isinstance(dados, dict):
                    raise ValueError("Dados não são um dicionário válido")

                # Garantir que tenha a estrutura esperada
                if "processos_executados" not in dados:
                    dados["processos_executados"] = []

                if not isinstance(dados["processos_executados"], list):
                    dados["processos_executados"] = []

                logger.info(f"[PROGRESSO_PET] Progresso carregado: {len(dados['processos_executados'])} executados")
                return dados
        else:
            logger.info("[PROGRESSO_PET] Arquivo de progresso não encontrado, criando novo")
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
        logger.warning(f"[PROGRESSO_PET] Arquivo corrompido ou inválido: {e}")
        logger.info("[PROGRESSO_PET] Criando novo arquivo de progresso...")

        # Tentar fazer backup do arquivo corrompido
        try:
            if os.path.exists(ARQUIVO_PROGRESSO_PET):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{ARQUIVO_PROGRESSO_PET.replace('.json', '')}_backup_{timestamp}.json"
                shutil.copy(ARQUIVO_PROGRESSO_PET, backup_path)
                logger.info(f"[PROGRESSO_PET] Backup criado: {backup_path}")
        except Exception as backup_e:
            logger.error(f"[PROGRESSO_PET] Erro ao criar backup: {backup_e}")

    # Retornar estrutura padrão
    dados_padrao = {
        "processos_executados": [],
        "session_active": True,
        "last_update": None
    }

    # Salvar estrutura padrão
    try:
        salvar_progresso_pet(dados_padrao)
        logger.info("[PROGRESSO_PET] Arquivo de progresso limpo criado")
    except Exception as save_e:
        logger.error(f"[PROGRESSO_PET] Erro ao salvar progresso limpo: {save_e}")

    return dados_padrao

def salvar_progresso_pet(progresso: Dict[str, Any]):
    """
    Salva o estado de progresso no arquivo JSON específico para petições.

    Args:
        progresso: Dict com estado do progresso
    """
    try:
        # Validar e limpar dados antes de salvar
        progresso_validado = _validar_e_limpar_progresso(progresso)

        # Atualizar timestamp
        progresso_validado["last_update"] = datetime.now().isoformat()

        # Salvar arquivo
        with open(ARQUIVO_PROGRESSO_PET, "w", encoding="utf-8") as f:
            json.dump(progresso_validado, f, ensure_ascii=False, indent=2)

        logger.info("[PROGRESSO_PET] Progresso salvo com segurança")
    except Exception as e:
        logger.error(f"[PROGRESSO_PET] Falha ao salvar progresso: {e}")

def _validar_e_limpar_progresso(progresso: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida e limpa dados de progresso antes de salvar.

    Args:
        progresso: Dados de progresso a serem validados

    Returns:
        Dados validados e limpos
    """
    if not isinstance(progresso, dict):
        raise ValueError("Progresso deve ser um dicionário")

    # Criar cópia para não modificar original
    progresso_limpo = progresso.copy()

    # Validar e limpar listas
    if "processos_executados" not in progresso_limpo:
        progresso_limpo["processos_executados"] = []
    elif not isinstance(progresso_limpo["processos_executados"], list):
        progresso_limpo["processos_executados"] = []
    else:
        # Filtrar apenas strings válidas e remover duplicatas
        progresso_limpo["processos_executados"] = list(set(
            item for item in progresso_limpo["processos_executados"]
            if isinstance(item, str) and item.strip()
        ))

    # Validar campos booleanos
    for campo in ["session_active"]:
        if campo not in progresso_limpo:
            progresso_limpo[campo] = False
        elif not isinstance(progresso_limpo[campo], bool):
            progresso_limpo[campo] = bool(progresso_limpo[campo])

    # Remover campos temporários que não devem ser persistidos
    campos_temporarios = ["temp_data", "cache", "session_data"]
    for campo in campos_temporarios:
        progresso_limpo.pop(campo, None)

    return progresso_limpo

def processo_ja_executado_pet(numero_processo: str, progresso: Dict[str, Any]) -> bool:
    """
    Verifica se o processo já foi executado com sucesso.

    Args:
        numero_processo: Número do processo
        progresso: Dict com estado do progresso

    Returns:
        True se já foi executado
    """
    if not numero_processo:
        return False

    executados = progresso.get("processos_executados", [])

    # Normalizar para comparação
    if numero_processo and re.match(r'^\d{20}$', numero_processo):
        n = numero_processo
        numero_processo = f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13:14]}.{n[14:16]}.{n[16:]}"

    return numero_processo in executados

def marcar_processo_executado_pet(numero_processo: str, progresso: Dict[str, Any]) -> None:
    """
    Marca processo como executado com sucesso.

    Args:
        numero_processo: Número do processo
        progresso: Dict com estado do progresso
    """
    if not numero_processo or not isinstance(numero_processo, str):
        logger.warning("[PROGRESSO_PET] Número do processo inválido, ignorando marcação")
        return

    numero_processo = numero_processo.strip()
    if not numero_processo:
        logger.warning("[PROGRESSO_PET] Número do processo vazio, ignorando marcação")
        return

    # Normalizar formato CNJ (20 dígitos para formato formatado)
    if re.match(r'^\d{20}$', numero_processo):
        # Converter 20 dígitos para 0000000-00.0000.0.00.0000
        n = numero_processo
        numero_processo = f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13:14]}.{n[14:16]}.{n[16:]}"
        logger.debug(f"[PROGRESSO_PET] Número normalizado para CNJ: {numero_processo}")

    # Validar formato final
    if not re.match(r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$', numero_processo):
        logger.warning(f"[PROGRESSO_PET] Formato de número do processo inválido: {numero_processo}")
        return

    # Marcar como executado com sucesso
    if numero_processo not in progresso.get("processos_executados", []):
        progresso.setdefault("processos_executados", []).append(numero_processo)
        logger.info(f"[PROGRESSO_PET] Processo marcado como executado: {numero_processo}")

        # Salvar progresso atualizado
        salvar_progresso_pet(progresso)
    else:
        logger.debug(f"[PROGRESSO_PET] Processo já estava marcado como executado: {numero_processo}")