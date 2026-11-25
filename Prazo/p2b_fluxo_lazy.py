from typing import Dict

# Cache de módulos carregados para evitar reimportações
_modules_cache: Dict[str, object] = {}

def _lazy_import():
    """Carrega módulos pesados sob demanda (lazy loading)."""
    global _modules_cache

    if not _modules_cache:
        from Fix.core import aguardar_e_clicar
        from Fix.extracao import criar_gigs, criar_lembrete_posit
        from atos.judicial import ato_pesquisas, idpj
        from atos.movimentos import mov
        from atos.wrappers_mov import mov_arquivar
        from atos.wrappers_ato import ato_sobrestamento, ato_pesqliq, ato_180, ato_calc2, ato_prev, ato_meios, ato_idpj, ato_reitmeios, ato_reit1, ato_HCL
        from atos import pec_excluiargos
        try:
            from atos.anexos.anexos_wrappers import anex_retifidpj, poupa
        except Exception:
            anex_retifidpj = None
            poupa = None

        _modules_cache.update({
            'aguardar_e_clicar': aguardar_e_clicar,
            'criar_gigs': criar_gigs,
            'criar_lembrete_posit': criar_lembrete_posit,
            'ato_pesquisas': ato_pesquisas,
            'idpj': idpj,
            'mov': mov,
            'mov_arquivar': mov_arquivar,
            'ato_sobrestamento': ato_sobrestamento,
            'ato_pesqliq': ato_pesqliq,
            'ato_180': ato_180,
            'ato_calc2': ato_calc2,
            'ato_prev': ato_prev,
            'ato_meios': ato_meios,
            'ato_idpj': ato_idpj,
            'ato_reitmeios': ato_reitmeios,
            'ato_reit1': ato_reit1,
            'ato_HCL': ato_HCL,
            'pec_excluiargos': pec_excluiargos,
            'anex_retifidpj': anex_retifidpj,
            'poupa': poupa,
        })

    return _modules_cache