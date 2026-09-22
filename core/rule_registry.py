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
from typing import Dict, List, Tuple, Pattern, Callable, Any, Optional

Action = Callable[[Any, dict], Optional[dict]]
Rule = Tuple[Pattern, str, Action]


class RuleRegistry:
    """Registry de regras unificado para todos os modulos."""

    def __init__(self, name: str, bucket_order: List[str]):
        self.name = name
        self.bucket_order = bucket_order
        self._rules: List[Rule] = []
        self._rules_by_bucket: Dict[str, List[Rule]] = {
            bucket: [] for bucket in bucket_order
        }

    def register(self, pattern: str, bucket: str, action: Action):
        """Registra uma regra: pattern regex, bucket, e acao callable."""
        regra = (re.compile(pattern, re.IGNORECASE), bucket, action)
        self._rules.append(regra)
        self._rules_by_bucket.setdefault(bucket, []).append(regra)

    def match_rule(
        self,
        observacao: str,
    ) -> Tuple[Optional[Pattern], Optional[str], Optional[Action]]:
        """Retorna (pattern, bucket, action) da primeira regra que casar."""
        if not observacao:
            return None, None, None

        for bucket in self.bucket_order:
            for rule_pattern, rule_bucket, action in self._rules_by_bucket.get(bucket, []):
                if rule_pattern.search(observacao):
                    return rule_pattern, rule_bucket, action

        return None, None, None

    def match(self, observacao: str) -> Tuple[Optional[str], Optional[Action]]:
        """Retorna (bucket, action) do primeiro match respeitando bucket_order, ou (None, None)."""
        _, bucket, action = self.match_rule(observacao)
        return bucket, action

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
