# -*- coding: utf-8 -*-
"""
bianca/utils.py - Utilitarios base para o projeto bianca.

Contem implementacoes autocontidas de:
  - logger padrao do modulo
  - Tipagem ResultadoFluxo e funcoes resultado_ok / resultado_falha
  - RuleRegistry (registro de regras regex)
  - run_batch (processador generico em lote)

Nenhuma dependencia externa ao modulo bianca.
"""

import logging
import re
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger("bianca")

# =============================================================================
# Tipos genericos
# =============================================================================


# =============================================================================
# resultado_ok / resultado_falha
# =============================================================================


# =============================================================================
# RuleRegistry
# =============================================================================


class RuleRegistry:
    """Registry de regras regex para deteccao de alertas / triagem.

    Uso::

        registry = RuleRegistry()
        registry.add_rule(r"pattern", "bucket_a", "descricao da regra")
        match = registry.check("texto a ser analisado")
    """

    def __init__(self) -> None:
        self._rules: List[Dict[str, Any]] = []

    def add_rule(self, pattern: str, bucket: str, descricao: str) -> None:
        """Registra uma regra: pattern regex, bucket de classificacao e
        descricao textual.

        Args:
            pattern: Expressao regular (compilada com ``re.IGNORECASE``).
            bucket: Nome do bucket / categoria.
            descricao: Descricao textual da regra.
        """
        self._rules.append(
            {
                "pattern": re.compile(pattern, re.IGNORECASE),
                "bucket": bucket,
                "descricao": descricao,
            }
        )

    def all_rules(self) -> List[Dict[str, Any]]:
        """Retorna copia da lista de regras registradas."""
        return list(self._rules)

    def check(self, texto: str) -> Optional[Dict[str, Any]]:
        """Verifica *texto* contra todas as regras.

        Retorna a primeira correspondencia encontrada ou ``None``.

        Returns:
            ``{"bucket": str, "descricao": str}`` ou ``None`` se nenhuma
            regra corresponder.
        """
        if not texto:
            return None
        for rule in self._rules:
            if rule["pattern"].search(texto):
                return {"bucket": rule["bucket"], "descricao": rule["descricao"]}
        return None


# =============================================================================
# run_batch
# =============================================================================


