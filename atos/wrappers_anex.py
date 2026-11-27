"""
Wrappers para juntada/anexos - Factory make_juntada_wrapper e instâncias declarativas.

Contrato unificado: atos/regras.py registra todos os wrappers
deste modulo no RuleRegistry (bucket 'juntada'), no mesmo padrão
de atos/wrappers_ato.py (ato_*) e atos/wrappers_pec.py (pec_*).
"""
import html
import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


def make_juntada_wrapper(
    tipo: str = 'Certidão',
    descricao: Optional[str] = None,
    modelo: Optional[str] = None,
    sigilo: str = 'nao',
    assinar: str = 'nao',
    inserir_conteudo: Optional[Callable[[Any, Optional[str], bool], bool]] = None,
    coleta_conteudo: Optional[str] = None,
    substituir_link: bool = False,
    fechar_aba_apos: bool = True,
    sisbajud_tipo: Optional[str] = None,
    conteudo_builder: Optional[Callable[..., Optional[Callable[[Any, Optional[str], bool], bool]]]] = None,
    wrapper_name: Optional[str] = None,
) -> Callable[..., bool]:
    """Factory declarativa de wrappers de juntada (espelho de make_ato_wrapper / make_comunicacao_wrapper).

    Cada wrapper gerado aceita ``(driver, numero_processo=None, debug=True, **overrides)``.
    - Se ``sisbajud_tipo`` for informado (``'SISB'``, ``'BLOQNEG'``, ``'PARCIAL'``), delega
      para ``_wrapper_sisbajud_generico``.
    - Se ``conteudo_builder`` for informado, resolve ``inserir_conteudo`` dinamicamente por chamada
      (ex.: ``anex_carta`` com ``ecarta_html`` / clipboard).
    - Caso contrário, executa ``wrapper_juntada_geral`` com ``inserir_conteudo`` (ou no-op padrão).
    """
    def _noop_inserir(driver: Any, numero_processo: Optional[str] = None, debug: bool = True) -> bool:
        return True

    def wrapper(
        driver: Any,
        numero_processo: Optional[str] = None,
        debug: bool = True,
        **overrides: Any,
    ) -> bool:
        tipo_eff = overrides.pop('tipo', tipo)
        descricao_eff = overrides.pop('descricao', descricao)
        modelo_eff = overrides.pop('modelo', modelo)
        sigilo_eff = overrides.pop('sigilo', sigilo)
        assinar_eff = overrides.pop('assinar', assinar)
        coleta_eff = overrides.pop('coleta_conteudo', coleta_conteudo)
        substituir_eff = overrides.pop('substituir_link', substituir_link)
        fechar_eff = overrides.pop('fechar_aba_apos', fechar_aba_apos)

        if sisbajud_tipo:
            from .anexos.anexos_sisbajud import _wrapper_sisbajud_generico
            return _wrapper_sisbajud_generico(
                driver,
                tipo_eff,
                descricao_eff or '',
                modelo_eff or '',
                assinar_eff,
                sigilo_eff,
                sisbajud_tipo,
                numero_processo,
                debug,
            )

        inserir_eff = overrides.pop('inserir_conteudo', None)
        if inserir_eff is None:
            if conteudo_builder is not None:
                inserir_eff = conteudo_builder(
                    driver=driver,
                    numero_processo=numero_processo,
                    debug=debug,
                    **overrides,
                )
            elif inserir_conteudo is not None:
                inserir_eff = inserir_conteudo
            else:
                inserir_eff = _noop_inserir

        from .anexos.anexos_juntador_base import wrapper_juntada_geral
        return wrapper_juntada_geral(
            driver=driver,
            tipo=tipo_eff,
            descricao=descricao_eff,
            modelo=modelo_eff,
            assinar=assinar_eff,
            sigilo=sigilo_eff,
            inserir_conteudo=inserir_eff,
            coleta_conteudo=coleta_eff,
            substituir_link=substituir_eff,
            debug=debug,
            fechar_aba_apos=fechar_eff,
        )

    if wrapper_name:
        wrapper.__name__ = wrapper_name
        wrapper.__qualname__ = wrapper_name
    wrapper._juntada_config = {
        'tipo': tipo,
        'descricao': descricao,
        'modelo': modelo,
        'sigilo': sigilo,
        'assinar': assinar,
        'sisbajud_tipo': sisbajud_tipo,
        'wrapper_name': wrapper_name,
    }
    return wrapper


def _builder_conteudo_ecarta(
    driver: Any = None,
    numero_processo: Optional[str] = None,
    debug: bool = True,
    ecarta_html: Optional[str] = None,
    **_: Any,
) -> Callable[[Any, Optional[str], bool], bool]:
    """Resolve conteúdo HTML de e-Carta (parâmetro explícito ou clipboard)."""
    from Fix.utils import obter_ultimo_conteudo_clipboard, substituir_marcador_por_conteudo

    conteudo = ecarta_html if ecarta_html is not None else obter_ultimo_conteudo_clipboard(numero_processo, debug=debug)

    def inserir_fn(driver: Any, numero_processo: Optional[str] = None, debug: bool = True) -> bool:
        return substituir_marcador_por_conteudo(
            driver=driver,
            conteudo_customizado=conteudo or '',
            debug=True,
            marcador='--',
        )

    return inserir_fn


anex_carta = make_juntada_wrapper(
    tipo='Certidão',
    descricao='Rastreamentos e-Carta',
    modelo='xs carta',
    assinar='nao',
    sigilo='nao',
    coleta_conteudo=None,
    substituir_link=False,
    conteudo_builder=_builder_conteudo_ecarta,
    wrapper_name='anex_carta',
)

def _formatar_cpf_advdelete(cpf: Any) -> str:
    """Formata CPF em 000.000.000-00 quando tiver 11 dígitos."""
    digitos = re.sub(r'\D', '', str(cpf or ''))
    if len(digitos) == 11:
        return f'{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}'
    return str(cpf or '').strip()


def formatar_conteudo_advdelete(vinculos: Optional[Iterable[Dict[str, Any]]]) -> str:
    """Formata os vínculos excluídos para preencher o marcador `--` de `advdelete`.

    Formato:
      `Nome da empresa, Advogado - CPF: 000.000.000-00`
    - Mais de um advogado da mesma empresa → mesma linha separados por vírgula.
    - Mais de uma empresa → uma por linha (`<br>` para preservar estilo do modelo).
    """
    if not vinculos:
        return ''

    por_empresa: Dict[str, List[str]] = {}
    vistos: set = set()
    for v in vinculos:
        if not isinstance(v, dict):
            continue
        empresa = ' '.join(str(v.get('parte') or v.get('empresa') or '').split())
        adv_nome = ' '.join(str(v.get('nome') or v.get('advogado') or '').split())
        cpf_fmt = _formatar_cpf_advdelete(v.get('cpf') or v.get('documento'))
        if not adv_nome and not cpf_fmt:
            continue
        chave = (empresa.upper(), re.sub(r'\D', '', cpf_fmt) or adv_nome.upper())
        if chave in vistos:
            continue
        vistos.add(chave)

        trecho_adv = f'{adv_nome} - CPF: {cpf_fmt}' if cpf_fmt else adv_nome
        por_empresa.setdefault(empresa, []).append(trecho_adv)

    linhas: List[str] = []
    for empresa, advs in por_empresa.items():
        advs_str = ', '.join(advs)
        linha = f'{empresa}, {advs_str}' if empresa else advs_str
        linhas.append(html.escape(linha))

    return '<br>'.join(linhas)


def _builder_conteudo_advdelete(
    driver: Any = None,
    numero_processo: Optional[str] = None,
    debug: bool = True,
    conteudo_advdelete: Optional[str] = None,
    vinculos: Optional[Iterable[Dict[str, Any]]] = None,
    **_: Any,
) -> Callable[[Any, Optional[str], bool], bool]:
    """Preenche o marcador `--` do modelo `advdelete` com os advogados excluídos."""
    from Fix.utils import substituir_marcador_por_conteudo

    if conteudo_advdelete is not None:
        conteudo = conteudo_advdelete
    else:
        conteudo = formatar_conteudo_advdelete(vinculos)

    def inserir_fn(driver: Any, numero_processo: Optional[str] = None, debug: bool = True) -> bool:
        return substituir_marcador_por_conteudo(
            driver=driver,
            conteudo_customizado=conteudo or '',
            debug=debug,
            marcador='--',
        )

    return inserir_fn


anex_advdelete = make_juntada_wrapper(
    tipo='Certidão',
    descricao='Advogado impedido excluído',
    modelo='advdelete',
    assinar='sim',
    sigilo='nao',
    coleta_conteudo=None,
    substituir_link=False,
    conteudo_builder=_builder_conteudo_advdelete,
    wrapper_name='anex_advdelete',
)

anex_sisbconsulta = make_juntada_wrapper(
    tipo='Certidão',
    descricao='Consulta SISBAJUD',
    modelo='xteim',
    assinar='nao',
    sigilo='sim',
    sisbajud_tipo='SISB',
    wrapper_name='anex_sisbconsulta',
)

anex_bloqneg = make_juntada_wrapper(
    tipo='Certidão',
    descricao='Consulta sisbajud NEGATIVA',
    modelo='xjsisbneg',
    assinar='nao',
    sigilo='nao',
    sisbajud_tipo='BLOQNEG',
    wrapper_name='anex_bloqneg',
)

anex_parcial = make_juntada_wrapper(
    tipo='Certidão',
    descricao='Consulta sisbajud POSITIVA',
    modelo='XSISBPARCIAL',
    assinar='nao',
    sigilo='nao',
    sisbajud_tipo='PARCIAL',
    wrapper_name='anex_parcial',
)

anex_retifidpj = make_juntada_wrapper(
    tipo='Certidão',
    descricao='Retificação - IDPJ indeferido',
    modelo='retifidpj',
    assinar='nao',
    sigilo='nao',
    coleta_conteudo=None,
    substituir_link=False,
    wrapper_name='anex_retifidpj',
)

anex_devcp = make_juntada_wrapper(
    tipo='Certidão',
    descricao='Devolução CP',
    modelo='xj2 d',
    assinar='nao',
    sigilo='nao',
    coleta_conteudo=None,
    substituir_link=False,
    wrapper_name='anex_devcp',
)

anex_poupa = make_juntada_wrapper(
    tipo='Certidão',
    descricao='Certidão de Pesquisas - Poupa Convênios',
    modelo='poupaconv',
    assinar='nao',
    sigilo='nao',
    coleta_conteudo=None,
    substituir_link=False,
    wrapper_name='anex_poupa',
)

# Alias curto mantido para conveniência no P2B
poupa = anex_poupa

__all__ = [
    'make_juntada_wrapper',
    'formatar_conteudo_advdelete',
    'anex_carta',
    'anex_advdelete',
    'anex_sisbconsulta',
    'anex_bloqneg',
    'anex_parcial',
    'anex_retifidpj',
    'anex_devcp',
    'anex_poupa',
    'poupa',
]
