"""
core/rule_registry.py — Registry de regras unificado para todos os modulos.

Contrato:
    Action = Callable[[Any, dict], Optional[dict]]
    Rule = Tuple[Pattern, str, Action]

Uso:
    registry = RuleRegistry("modulo", ["bucket1", "bucket2", ...])
    registry.register(r'pattern', 'bucket1', acao_fn)
    bucket, action = registry.match(observacao)
"""

import re
from typing import List, Tuple, Pattern, Callable, Any, Optional

Action = Callable[[Any, dict], Optional[dict]]
Rule = Tuple[Pattern, str, Action]


class RuleRegistry:
    """Registry de regras unificado para todos os modulos."""

    def __init__(self, name: str, bucket_order: List[str]):
        self.name = name
        self.bucket_order = bucket_order
        self._rules: List[Rule] = []

    def register(self, pattern: str, bucket: str, action: Action):
        """Registra uma regra: pattern regex, bucket, e acao callable."""
        self._rules.append((re.compile(pattern, re.IGNORECASE), bucket, action))

    def match(self, observacao: str) -> Tuple[Optional[str], Optional[Action]]:
        """Retorna (bucket, action) do primeiro match respeitando bucket_order, ou (None, None)."""
        if not observacao:
            return None, None
        for bucket in self.bucket_order:
            for rule_pattern, rule_bucket, action in self._rules:
                if rule_bucket == bucket and rule_pattern.search(observacao):
                    return bucket, action
        return None, None

    def get_actions_for_bucket(self, bucket: str) -> List[Action]:
        """Retorna todas as acoes registradas para um bucket."""
        return [a for p, b, a in self._rules if b == bucket]

    def all_rules(self) -> List[Rule]:
        """Retorna copia da lista de regras."""
        return list(self._rules)


def adapt_action(fn):
    """Adapta callable (driver,) → (driver, atv) esperado pelo registry."""
    if fn is None:
        return None
    return lambda driver, atv: fn(driver)
