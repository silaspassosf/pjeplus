# -*- coding: utf-8 -*-
"""
bianca/triagem/progress.py -- Progress tracking para triagem (logica p2b).

Mesma logica do progresso unificado do p2b (Fix/monitoramento_progresso_unificado),
mas autossuficiente dentro de /bianca/ — sem dependencias de Fix.*.

Arquivo de progresso: ``bianca/progresso_triagem.json``

Estrutura do JSON (identica ao padrao p2b)::

    {
        "processos_executados": ["0000123-...", "0000456-..."],
        "processos_com_erro": ["0000789-..."],
        "atualizado_em": "2026-05-07T10:00:00"
    }

Regras (identicas ao p2b):
  - processo_ja_executado: True se estiver em ``processos_executados``
    (apenas sucessos; falhas sao retentadas).
  - marcar_processo_executado com SUCESSO: append em ``processos_executados``,
    remove de ``processos_com_erro`` se estava la.
  - marcar_processo_executado com FALHA: append em ``processos_com_erro``
    (NAO vai para executados — sera retentado na proxima execucao).
  - Validacao de formato CNJ antes de marcar.
  - Backup do arquivo antes de sobrescrever.

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
import re
import shutil
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger("bianca.triagem.progress")

_PROGRESSO_ARQUIVO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "progresso_triagem.json",
)

# Mesmo regex de validacao do p2b (Fix/monitoramento_progresso_unificado)
_RE_CNJ = re.compile(r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$')


def _validar_cnj(numero: str) -> bool:
    """Valida formato basico do numero CNJ (identico ao p2b)."""
    return bool(numero and isinstance(numero, str) and _RE_CNJ.match(numero.strip()))


class ProgressoTriagem:
    """Progress tracking para triagem com logica identica ao p2b.

    Gerencia um arquivo JSON de progresso para evitar reprocessar
    processos ja analisados com sucesso. Processos com falha sao
    retentados na proxima execucao.
    """

    # ------------------------------------------------------------------
    # Carregar / salvar
    # ------------------------------------------------------------------

    @staticmethod
    def carregar_progresso() -> Dict[str, Any]:
        """Le o JSON de progresso do arquivo.

        Returns:
            Dict com ``processos_executados``, ``processos_com_erro``
            e ``atualizado_em``. Retorna dict vazio se o arquivo nao
            existir ou estiver corrompido.
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

            # --- Migracao de formato antigo para p2b ---
            # Formato antigo: {"tipo": "...", "processos": {"CNJ": {"status": "SUCESSO", ...}, ...}}
            # Formato novo (p2b): {"processos_executados": [...], "processos_com_erro": [...]}
            if "processos" in dados and isinstance(dados.get("processos"), dict):
                logger.info("Detectado formato antigo de progresso — migrando para p2b...")
                executados = []
                com_erro = []
                for cnj, entry in dados["processos"].items():
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("status") == "SUCESSO":
                        executados.append(cnj)
                    else:
                        com_erro.append(cnj)
                dados = {
                    "processos_executados": executados,
                    "processos_com_erro": com_erro,
                }
                # Salvar formato migrado imediatamente
                ProgressoTriagem.salvar_progresso(dados)
                logger.info(
                    "Migracao concluida: %d executados, %d com erro",
                    len(executados), len(com_erro),
                )
                return dados

            # Garantir listas (identico ao p2b)
            for campo in ("processos_executados", "processos_com_erro"):
                if campo not in dados or not isinstance(dados.get(campo), list):
                    dados[campo] = []

            # Filtrar apenas strings validas e remover duplicatas (identico ao p2b)
            for campo in ("processos_executados", "processos_com_erro"):
                dados[campo] = list(set(
                    item for item in dados[campo]
                    if isinstance(item, str) and item.strip()
                ))

            return dados

        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Erro ao ler progresso: %s -- resetando", e)
            return {}

    @staticmethod
    def salvar_progresso(dados: Dict[str, Any]) -> None:
        """Escreve o JSON de progresso no arquivo, com backup previo.

        Args:
            dados: Dict com ``processos_executados``, ``processos_com_erro``.
        """
        try:
            # Garantir estrutura minima
            dados.setdefault("processos_executados", [])
            dados.setdefault("processos_com_erro", [])
            dados["atualizado_em"] = datetime.now().isoformat(timespec="seconds")

            # Backup antes de sobrescrever (identico ao p2b)
            if os.path.exists(_PROGRESSO_ARQUIVO):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = _PROGRESSO_ARQUIVO.replace(".json", f"_backup_{timestamp}.json")
                    shutil.copy(_PROGRESSO_ARQUIVO, backup_path)
                except OSError:
                    pass  # backup nao critico

            dir_path = os.path.dirname(_PROGRESSO_ARQUIVO)
            os.makedirs(dir_path, exist_ok=True)

            with open(_PROGRESSO_ARQUIVO, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)

            logger.debug("Progresso salvo em %s", _PROGRESSO_ARQUIVO)

        except OSError as e:
            logger.error("Erro ao salvar progresso: %s", e)

    # ------------------------------------------------------------------
    # Consulta / marcacao (logica identica ao p2b)
    # ------------------------------------------------------------------

    @staticmethod
    def processo_ja_executado(numero: str, progresso: Dict[str, Any]) -> bool:
        """Verifica se um numero de processo ja foi executado com SUCESSO.

        Identico ao p2b: apenas processos em ``processos_executados``
        sao pulados. Processos em ``processos_com_erro`` NAO sao pulados
        (serao retentados).

        Args:
            numero: Numero CNJ do processo.
            progresso: Dict carregado de ``carregar_progresso()``.

        Returns:
            True somente se o numero consta em ``processos_executados``.
        """
        if not numero or not isinstance(progresso, dict):
            return False
        return numero.strip() in progresso.get("processos_executados", [])

    @staticmethod
    def processo_tem_erro(numero: str, progresso: Dict[str, Any]) -> bool:
        """Verifica se um processo teve erro em execucao anterior.

        Args:
            numero: Numero CNJ do processo.
            progresso: Dict carregado de ``carregar_progresso()``.

        Returns:
            True se o numero consta em ``processos_com_erro``.
        """
        if not numero or not isinstance(progresso, dict):
            return False
        return numero.strip() in progresso.get("processos_com_erro", [])

    @staticmethod
    def marcar_processo_executado(
        numero: str,
        status: str,
        erro: Optional[str],
        progresso: Dict[str, Any],
    ) -> None:
        """Marca um processo como executado no dict de progresso.

        Logica identica ao p2b (marcar_processo_executado_unificado):
          - SUCESSO: append em ``processos_executados``, remove de
            ``processos_com_erro``.
          - FALHA: append em ``processos_com_erro`` (NAO vai para
            executados — sera retentado).

        So persiste se o numero passou na validacao CNJ e houve
        modificacao real nas listas.

        Args:
            numero: Numero CNJ do processo.
            status: ``"SUCESSO"`` ou ``"FALHA"``.
            erro: Mensagem de erro se houver, ou ``None``.
            progresso: Dict de progresso (modificado in-place e salvo).
        """
        if not numero or not isinstance(numero, str):
            logger.warning("[PROGRESSO] Numero de processo invalido, ignorando marcacao")
            return

        numero = numero.strip()
        if not numero:
            logger.warning("[PROGRESSO] Numero de processo vazio, ignorando marcacao")
            return

        if not _validar_cnj(numero):
            logger.warning("[PROGRESSO] Formato CNJ invalido: %s", numero)
            return

        # Garantir estrutura minima
        progresso.setdefault("processos_executados", [])
        progresso.setdefault("processos_com_erro", [])

        modificado = False
        sucesso = status == "SUCESSO"

        if sucesso:
            # Marcar como executado (identico ao p2b)
            if numero not in progresso["processos_executados"]:
                progresso["processos_executados"].append(numero)
                modificado = True

            # Remover de erros se estava la
            if numero in progresso["processos_com_erro"]:
                progresso["processos_com_erro"].remove(numero)
                modificado = True

            logger.info("[PROGRESSO][%s] Processo marcado como executado", numero)
        else:
            # Marcar como erro (identico ao p2b)
            if numero not in progresso["processos_com_erro"]:
                progresso["processos_com_erro"].append(numero)
                modificado = True

            logger.info("[PROGRESSO][%s] Erro: %s", numero, erro or "desconhecido")

        if modificado:
            ProgressoTriagem.salvar_progresso(progresso)
        else:
            logger.debug("[PROGRESSO][%s] Nenhuma modificacao no progresso", numero)
