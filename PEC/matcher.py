import logging
logger = logging.getLogger(__name__)

"""Motor de matching de regras observação -> ação."""

import re
from typing import Optional, Callable, List, Tuple, Any
from .helpers import gerar_regex_geral, normalizar_texto

# ===== CACHE GLOBAL PARA REGRAS DE AÇÃO =====
# Inicializado como None - será preenchido na primeira chamada de get_cached_rules()
_ACAO_RULES_CACHE = None


def _build_action_rules() -> List[Tuple[List, Any]]:
    """
    Constrói as regras de mapeamento observação -> ação uma única vez.
    Chamada apenas na primeira utilização, resultado é cacheado globalmente.
    """
    from importlib import import_module
    
    # Import locally to avoid circular imports
    try:
        _jud = import_module('atos.judicial')
    except Exception:
        _jud = None
    try:
        _movmod = import_module('atos.movimentos')
    except Exception:
        _movmod = None
    try:
        _fix_carta = import_module('PEC.carta')
    except Exception:
        _fix_carta = None
    try:
        _fix_ext = import_module('Fix.extracao')
    except Exception:
        _fix_ext = None
    
    # Importar SISB.core
    _sisb = None
    try:
        _sisb = import_module('SISB.core')
        logger.info(f'[PEC_REGRAS]  SISB importado')
    except Exception as e:
        logger.info(f'[PEC_REGRAS]  Falha ao importar SISB.core: {e}')
    
    try:
        _wraps = import_module('atos.wrappers_ato')
    except Exception:
        _wraps = None
    
    try:
        _wraps_pec = import_module('atos.wrappers_pec')
    except Exception:
        _wraps_pec = None
    
    try:
        _oficio = import_module('atos.oficio')
    except Exception:
        _oficio = None
    
    # Import def_sob from analysis
    try:
        from PEC.sobrestamento import def_sob
    except Exception:
        def_sob = None
    
    # Import criar_gigs
    try:
        from Fix.extracao import criar_gigs
    except Exception:
        criar_gigs = None

    # Helper to resolve attribute safely
    def _attr(mod, name, default=None):
        if not mod:
            return default
        return getattr(mod, name, default)

    # Helper functions for actions
    def _gigs_edital_intimacao(driver):
        """GIGS: Edital intimação correio para Ingrid"""
        return criar_gigs(driver, 1, 'Ingrid', 'edital intimação correio')
    
    return [
        ([gerar_regex_geral(k) for k in ['exclusão', 'exclusao', 'excluir', 'indeferido']], _attr(_wraps_pec, 'pec_excluiargos')),
        # SISBAJUD - TEIMOSINHA COM 60 DIAS (60d, 60 dias, sessenta)
        ([gerar_regex_geral(k) for k in ['teimosinha 60', 't2 60', '60d', '60 dias', 'sessenta']], _attr(_sisb, 'minuta_bloqueio_60')),
        # SISBAJUD - TEIMOSINHA PADRÃO (30 dias)
        ([gerar_regex_geral(k) for k in ['teimosinha', 't2']], _attr(_sisb, 'minuta_bloqueio')),
        # SISBAJUD - RESULTADO (processar ordens)
        ([gerar_regex_geral(k) for k in ['xs resultado', 'resultado']], _attr(_sisb, 'processar_ordem_sisbajud')),
        ([gerar_regex_geral(k) for k in ['xs ord']], _attr(_wraps_pec, 'pec_ord')),
        ([gerar_regex_geral(k) for k in ['xs sum']], _attr(_wraps_pec, 'pec_sum')),
        ([gerar_regex_geral(k) for k in ['xs audx', 'audx', 'aud x']], _attr(_jud, 'mov_aud')),
        ([gerar_regex_geral(k) for k in ['sob chip']], _attr(_movmod, 'def_chip')),
        # Regra para "sobrestamento vencido" - agora ativada
        ([gerar_regex_geral(k) for k in ['sobrestamento vencido']], def_sob),
        ([gerar_regex_geral(k) for k in ['pz idpj', 'idpjd']], [_gigs_edital_intimacao, _attr(_jud, 'ato_idpj')]),
        ([gerar_regex_geral(k) for k in ['xs parcial']], _attr(_jud, 'ato_bloq')),
        ([gerar_regex_geral(k) for k in ['meios']], [(_attr(_fix_ext, 'bndt'), {'inclusao': True}), _attr(_jud, 'ato_meios')]),
        ([gerar_regex_geral(k) for k in ['pec aud']], _attr(_wraps_pec, 'pec_editalaud')),
        ([gerar_regex_geral(k) for k in ['pec cp', 'xs pec cp']], _attr(_wraps_pec, 'pec_cpgeral')),
        ([gerar_regex_geral(k) for k in ['xs edital']], _attr(_wraps_pec, 'pec_editaldec')),
        ([gerar_regex_geral(k) for k in ['pec edital', 'xs pec edital']], _attr(_wraps_pec, 'pec_editaldec')),
        ([gerar_regex_geral(k) for k in ['pec dec', 'xs pec dec']], _attr(_wraps_pec, 'pec_decisao')),
        ([gerar_regex_geral(k) for k in ['pec idpj', 'xs pec idpj']], _attr(_wraps_pec, 'pec_editalidpj')),
        ([gerar_regex_geral(k) for k in ['xs carta']], _attr(_fix_carta, 'carta')),
        # Regex restritiva: captura apenas "bloq" como palavra completa, não "bloqueio"
        ([re.compile(r'\b(xs|pec)\s+bloq\b', re.IGNORECASE)], _attr(_wraps_pec, 'pec_bloqueio')),
        ([gerar_regex_geral(k) for k in ['xs sigilo']], _attr(_wraps_pec, 'pec_sigilo')),
        ([gerar_regex_geral(k) for k in ['xs socio']], [(_attr(_fix_ext, 'bndt'), {'inclusao': True}), _attr(_wraps, 'ato_termoS')]),
        ([gerar_regex_geral(k) for k in ['empresa termo', 'empresatermo', 'termoempresa']], [(_attr(_fix_ext, 'bndt'), {'inclusao': True}), _attr(_wraps, 'ato_termoE')]),
        # PEC Ofício - executado por último no bucket outros
        ([gerar_regex_geral(k) for k in ['pec oficio', 'pec ofício']], _attr(_oficio, 'oficio')),
        # xs (numero) sozinho = xs sob (numero) - mesmo bucket/ações
        ([re.compile(r'^xs\s+\d+$', re.IGNORECASE)], [_attr(_movmod, 'def_chip'), _attr(_movmod, 'mov_sob')]),
        ([re.compile(r'\bsob\s+\d+', re.IGNORECASE)], [_attr(_movmod, 'def_chip'), _attr(_movmod, 'mov_sob')]),
        ([gerar_regex_geral(k) for k in ['sob']], [_attr(_movmod, 'def_chip'), _attr(_movmod, 'mov_sob')]),
    ]


def get_cached_rules() -> List[Tuple[List, Any]]:
    """
    Retorna regras cacheadas, construindo apenas na primeira chamada.
    Implementa padrão singleton para evitar repetidas compilações de regex.
    """
    global _ACAO_RULES_CACHE
    if _ACAO_RULES_CACHE is None:
        _ACAO_RULES_CACHE = _build_action_rules()
    return _ACAO_RULES_CACHE


def get_action_rules() -> List[Tuple[List, Any]]:
    """
    [DEPRECATED] Mantida para compatibilidade.
    Usa get_cached_rules() internamente.
    """
    return get_cached_rules()


def determinar_acoes_por_observacao(observacao: str) -> List[Any]:
    """
    Determina LISTA DE AÇÕES para uma observação.
    Cada regra que match adiciona sua ação à lista.
    
    Retorna lista de funções, ou [] se nenhuma regra corresponder.
    Usa cache global de regras (construído apenas uma vez).
    """
    # Normalizar observação: remover acentos e converter para minúscula
    observacao_lower = normalizar_texto(observacao)
    regras = get_cached_rules()
    acoes: List[Any] = []
    minuta_ja_detectada = False  # Flag para não adicionar minuta padrão após 60
    
    for idx, (regex_list, funcao) in enumerate(regras, 1):
        for regex in regex_list:
            try:
                if regex.search(observacao_lower):
                    # Se já detectou minuta_bloqueio_60, pular minuta_bloqueio padrão
                    acao_nome = funcao.__name__ if callable(funcao) and hasattr(funcao, '__name__') else str(funcao)
                    if minuta_ja_detectada and acao_nome == 'minuta_bloqueio':
                        break
                    if funcao and funcao not in acoes:
                        acoes.append(funcao)
                        if acao_nome == 'minuta_bloqueio_60':
                            minuta_ja_detectada = True
                    break
            except NameError as ne:
                import traceback as _tb
                logger.info(f"[PEC_RULE_ERROR] NameError while evaluating regex in rule #{idx}: {ne}")
                logger.info(f"[PEC_RULE_ERROR] regex={regex.pattern if hasattr(regex, 'pattern') else regex} funcao={funcao}")
                _tb.print_exc()
                raise
            except Exception:
                import traceback as _tb
                logger.info(f"[PEC_RULE_ERROR] Exception while evaluating regex in rule #{idx}")
                logger.info(f"[PEC_RULE_ERROR] regex={getattr(regex, 'pattern', str(regex))} funcao={funcao}")
                _tb.print_exc()
                continue
    
    return acoes


def determinar_acao_por_observacao(observacao: str) -> Optional[Any]:
    """
    [COMPATIBILIDADE] Retorna PRIMEIRA ação.
    Use determinar_acoes_por_observacao() para lista completa.
    """
    acoes = determinar_acoes_por_observacao(observacao)
    return acoes[0] if acoes else None
