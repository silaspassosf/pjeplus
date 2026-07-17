"""
atos/regras.py — Registry unificado de regras/acoes para atos.

Registra todos os wrappers de atos judiciais, comunicacoes e movimentos
no padrao RuleRegistry (core/rule_registry).

Buckets:
    - ato_judicial:          wrappers de atos judiciais (wrappers_ato.py)
    - comunicacao_judicial:  wrappers de comunicacao (wrappers_pec.py)
    - movimentos:            movimentos processuais (movimentos.py)

Contrato:
    Action = Callable[[Any, dict], Optional[dict]]
    Cada action registrada aceita (driver, atv) conforme RuleRegistry.
    Para uso como catalogo de descoberta, os wrappers sao registrados
    com padrao de nome literal (re.escape) para match por nome.

Uso:
    from atos.regras import registry
    wrappers = registry.get_actions_for_bucket('ato_judicial')
    bucket, action = registry.match('nome_do_wrapper')
"""

import re
from core.rule_registry import RuleRegistry

BUCKET_ORDEM = ['ato_judicial', 'comunicacao_judicial', 'movimentos']

registry = RuleRegistry("atos", BUCKET_ORDEM)

# ────────────────────────────────────────────────────────────────
# ato_judicial: wrappers de atos judiciais (wrappers_ato.py)
# ────────────────────────────────────────────────────────────────

from .wrappers_ato import (
    ato_meios,
    ato_reitmeios,
    ato_ratif,
    ato_100,
    ato_unap,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    ato_sobrestamento,
    ato_prov,
    ato_180,
    ato_x90,
    ato_pesqliq_original,
    ato_pesqliq,
    ato_calc2,
    ato_meiosub,
    ato_presc,
    ato_fal,
    ato_parcela,
    ato_prev,
    ato_instc,
    ato_laudo,
    ato_esc,
    ato_escliq,
    ato_datalocal,
    ato_gen,
    ato_naocoaf,
    ato_naosimba,
    ato_teim,
    ato_inste,
    ato_agpetidpj,
    ato_agpet,
    ato_adesivo,
    ato_agpinter,
    ato_ceju,
    ato_respcalc,
    ato_revel,
    ato_assistente,
    ato_concor,
    ato_ccs,
    ato_censec,
    ato_serp,
    ato_conv,
    ato_prevjud,
    ato_ed,
)

_ATO_JUDICIAL_WRAPPERS = {
    'ato_meios': ato_meios,
    'ato_reitmeios': ato_reitmeios,
    'ato_ratif': ato_ratif,
    'ato_100': ato_100,
    'ato_unap': ato_unap,
    'ato_crda': ato_crda,
    'ato_crte': ato_crte,
    'ato_bloq': ato_bloq,
    'ato_idpj': ato_idpj,
    'ato_termoE': ato_termoE,
    'ato_termoS': ato_termoS,
    'ato_edital': ato_edital,
    'ato_sobrestamento': ato_sobrestamento,
    'ato_prov': ato_prov,
    'ato_180': ato_180,
    'ato_x90': ato_x90,
    'ato_pesqliq_original': ato_pesqliq_original,
    'ato_pesqliq': ato_pesqliq,
    'ato_calc2': ato_calc2,
    'ato_meiosub': ato_meiosub,
    'ato_presc': ato_presc,
    'ato_fal': ato_fal,
    'ato_parcela': ato_parcela,
    'ato_prev': ato_prev,
    'ato_instc': ato_instc,
    'ato_laudo': ato_laudo,
    'ato_esc': ato_esc,
    'ato_escliq': ato_escliq,
    'ato_datalocal': ato_datalocal,
    'ato_gen': ato_gen,
    'ato_naocoaf': ato_naocoaf,
    'ato_naosimba': ato_naosimba,
    'ato_teim': ato_teim,
    'ato_inste': ato_inste,
    'ato_agpetidpj': ato_agpetidpj,
    'ato_agpet': ato_agpet,
    'ato_adesivo': ato_adesivo,
    'ato_agpinter': ato_agpinter,
    'ato_ceju': ato_ceju,
    'ato_respcalc': ato_respcalc,
    'ato_revel': ato_revel,
    'ato_assistente': ato_assistente,
    'ato_concor': ato_concor,
    'ato_ccs': ato_ccs,
    'ato_censec': ato_censec,
    'ato_serp': ato_serp,
    'ato_conv': ato_conv,
    'ato_prevjud': ato_prevjud,
    'ato_ed': ato_ed,
}

for _name, _fn in _ATO_JUDICIAL_WRAPPERS.items():
    registry.register(re.escape(_name), 'ato_judicial', _fn)

# ────────────────────────────────────────────────────────────────
# comunicacao_judicial: wrappers de comunicacao (wrappers_pec.py)
# ────────────────────────────────────────────────────────────────

from .wrappers_pec import (
    pec_bloqueio,
    pec_decisao,
    pec_idpj,
    pec_editalidpj,
    pec_editaldec,
    pec_cpgeral,
    pec_excluiargos,
    pec_mddgeral,
    pec_mddaud,
    pec_editalaud,
    pec_sigilo,
    pec_ord,
    pec_sum,
    pec_ordc,
    pec_sumc,
    pec_arsum,
    pec_arord,
    wrapper_pec_ord_com_domicilio,
    wrapper_pec_sum_com_domicilio,
)

_COMUNICACAO_WRAPPERS = {
    'pec_bloqueio': pec_bloqueio,
    'pec_decisao': pec_decisao,
    'pec_idpj': pec_idpj,
    'pec_editalidpj': pec_editalidpj,
    'pec_editaldec': pec_editaldec,
    'pec_cpgeral': pec_cpgeral,
    'pec_excluiargos': pec_excluiargos,
    'pec_mddgeral': pec_mddgeral,
    'pec_mddaud': pec_mddaud,
    'pec_editalaud': pec_editalaud,
    'pec_sigilo': pec_sigilo,
    'pec_ord': pec_ord,
    'pec_sum': pec_sum,
    'pec_ordc': pec_ordc,
    'pec_sumc': pec_sumc,
    'pec_arsum': pec_arsum,
    'pec_arord': pec_arord,
    'wrapper_pec_ord_com_domicilio': wrapper_pec_ord_com_domicilio,
    'wrapper_pec_sum_com_domicilio': wrapper_pec_sum_com_domicilio,
}

for _name, _fn in _COMUNICACAO_WRAPPERS.items():
    registry.register(re.escape(_name), 'comunicacao_judicial', _fn)

# ────────────────────────────────────────────────────────────────
# movimentos (movimentos.py)
# ────────────────────────────────────────────────────────────────

from .movimentos import (
    mov,
    mov_simples,
    mov_sob,
    mov_fimsob,
    def_chip,
    despacho_generico,
)

_MOVIMENTOS_WRAPPERS = {
    'mov': mov,
    'mov_simples': mov_simples,
    'mov_sob': mov_sob,
    'mov_fimsob': mov_fimsob,
    'def_chip': def_chip,
    'despacho_generico': despacho_generico,
}

for _name, _fn in _MOVIMENTOS_WRAPPERS.items():
    registry.register(re.escape(_name), 'movimentos', _fn)

# ────────────────────────────────────────────────────────────────
# Conveniencia: dicionarios nomeados de wrappers por bucket
# ────────────────────────────────────────────────────────────────

ATOS_JUDICIAIS = dict(_ATO_JUDICIAL_WRAPPERS)
COMUNICACOES = dict(_COMUNICACAO_WRAPPERS)
MOVIMENTOS = dict(_MOVIMENTOS_WRAPPERS)
