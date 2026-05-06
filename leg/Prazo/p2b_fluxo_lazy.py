from typing import Dict

# Cache de módulos carregados para evitar reimportações
_modules_cache: Dict[str, object] = {}

def _lazy_import():
    """Carrega módulos pesados sob demanda (lazy loading).
    
    Esta função é chamada pelas funções que precisam dos módulos,
    garantindo que só sejam carregados quando realmente necessários.
    """
    global _modules_cache
    
    if not _modules_cache:
        from Fix.core import aguardar_e_clicar
        from Fix.extracao import criar_gigs, criar_lembrete_posit
        from atos.judicial import ato_pesquisas, idpj
        from atos.movimentos import mov
        from atos.wrappers_mov import mov_arquivar
        from atos.wrappers_ato import ato_sobrestamento, ato_pesqliq, ato_180, ato_calc2, ato_prev, ato_meios, ato_idpj, ato_reitmeios
        from atos import pec_excluiargos
        # PEC anexos wrappers
        try:
            from PEC.anexos.anexos_wrappers import retifidpj_wrapper
        except Exception:
            retifidpj_wrapper = None
        
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
            'pec_excluiargos': pec_excluiargos,
            'retifidpj_wrapper': retifidpj_wrapper,
        })
    
    return _modules_cache