"""
core — registry de regras e utilitarios de governanca.

Superficie publica:
  RuleRegistry    — registry de regras unificado
  adapt_action    — decorator para adaptar funcoes como acoes de regra
  Action          — tipo Callable para acoes
  Rule            — tipo Tuple para regras registradas
"""

from .rule_registry import RuleRegistry, adapt_action, Action, Rule

__all__ = [
    'RuleRegistry',
    'adapt_action',
    'Action',
    'Rule',
]
