import logging
logger = logging.getLogger(__name__)

"""
PEC.regras — wrappers / re-exports usados por codigo em producao.

Mantem apenas o que e efetivamente importado por outros modulos da arvore
de producao. Remove re-exports obsoletos (get_action_rules, .helpers,
.sobrestamento, .prescricao, .ajuste_gigs, get_or_create_driver_sisbajud).
"""

from .regras_pec import determinar_regra as _determinar_regra


def determinar_acoes_por_observacao(observacao: str) -> list:
    """Wrapper: extrai acao do 3-tuplo retornado por determinar_regra()."""
    match = _determinar_regra(observacao)
    return [match[2]] if match else []


def executar_acao_pec(driver, acao, *args, **kwargs):
    """Stub: use PEC.orquestrador para execucao real."""
    if callable(acao):
        return acao(driver)
    return False


try:
    from .sisbajud_driver import fechar_driver_sisbajud_global
except ImportError:
    def fechar_driver_sisbajud_global(*args, **kwargs):
        raise NotImplementedError('fechar_driver_sisbajud_global nao disponivel')


__all__ = [
    'determinar_acoes_por_observacao',
    'executar_acao_pec',
    'fechar_driver_sisbajud_global',
]
