# -*- coding: utf-8 -*-
"""
bianca/triagem/progress.py -- Progress tracking simplificado para triagem.

Arquivo de progresso: ``bianca/progresso_triagem.json``
Sem dependencias de Fix.* -- JSON puro.

Estrutura do JSON::

    {
        "tipo": "TRIAGEM",
        "processos": {
            "0000123-...": {"status": "SUCESSO", "erro": null, "executado_em": "..."},
            ...
        },
        "atualizado_em": "2026-05-07T10:00:00"
    }

Uso:
    from bianca.triagem.progress import ProgressoTriagem
    prog = ProgressoTriagem()
    dados = prog.carregar_progresso()
    if not prog.processo_ja_executado(numero, dados):
        ...
        prog.marcar_processo_executado(numero, "SUCESSO", None, dados)
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger("bianca.triagem.progress")

_PROGRESSO_ARQUIVO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "progresso_triagem.json",
)


class ProgressoTriagem:
    """Progress tracking simplificado para triagem.

    Gerencia um arquivo JSON de progresso para evitar reprocessar
    processos ja analisados.
    """

    # ------------------------------------------------------------------
    # Carregar / salvar
    # ------------------------------------------------------------------

    @staticmethod
    def carregar_progresso() -> Dict[str, Any]:
        """Le o JSON de progresso do arquivo.

        Returns:
            Dict com a estrutura de progresso, ou dict vazio se o
            arquivo nao existir ou estiver corrompido.
        """
        if not os.path.exists(_PROGRESSO_ARQUIVO):
            logger.debug("Arquivo de progresso nao encontrado: %s", _PROGRESSO_ARQUIVO)
            return {}
        try:
            with open(_PROGRESSO_ARQUIVO, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if not isinstance(dados, dict):
                logger.warning("Progresso com formato invalido -- resetando")
                return {}
            return dados
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Erro ao ler progresso: %s -- resetando", e)
            return {}

    @staticmethod
    def salvar_progresso(dados: Dict[str, Any]) -> None:
        """Escreve o JSON de progresso no arquivo.

        Args:
            dados: Dict com a estrutura de progresso.
        """
        try:
            dados["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
            dir_path = os.path.dirname(_PROGRESSO_ARQUIVO)
            os.makedirs(dir_path, exist_ok=True)
            with open(_PROGRESSO_ARQUIVO, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            logger.debug("Progresso salvo em %s", _PROGRESSO_ARQUIVO)
        except OSError as e:
            logger.error("Erro ao salvar progresso: %s", e)

    # ------------------------------------------------------------------
    # Consulta / marcacao
    # ------------------------------------------------------------------

    @staticmethod
    def processo_ja_executado(numero: str, progresso: Dict[str, Any]) -> bool:
        """Verifica se um numero de processo ja foi executado com sucesso.

        Args:
            numero: Numero CNJ do processo.
            progresso: Dict carregado de ``carregar_progresso()``.

        Returns:
            True somente se o numero consta em ``progresso["processos"]``
            com status ``"SUCESSO"``. Processos com status ``"FALHA"``
            retornam False para permitir nova tentativa.
        """
        if not numero or not isinstance(progresso, dict):
            return False
        processos = progresso.get("processos") or {}
        entry = processos.get(numero)
        if not entry:
            return False
        return entry.get("status") == "SUCESSO"

    @staticmethod
    def marcar_processo_executado(
        numero: str,
        status: str,
        erro: Optional[str],
        progresso: Dict[str, Any],
    ) -> None:
        """Marca um processo como executado no dict de progresso.

        Args:
            numero: Numero CNJ do processo.
            status: ``"SUCESSO"`` ou ``"FALHA"``.
            erro: Mensagem de erro se houver, ou ``None``.
            progresso: Dict de progresso (modificado in-place).

        Nota:
            Nao persiste automaticamente -- chamar ``salvar_progresso()``
            apos marcar todos os processos.
        """
        if "tipo" not in progresso:
            progresso["tipo"] = "TRIAGEM"
        if "processos" not in progresso:
            progresso["processos"] = {}

        progresso["processos"][numero] = {
            "status": status,
            "erro": erro,
            "executado_em": datetime.now().isoformat(timespec="seconds"),
        }
        ProgressoTriagem.salvar_progresso(progresso)
