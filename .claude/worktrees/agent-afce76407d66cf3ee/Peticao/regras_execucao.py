"""
Peticao/regras_execucao.py — Registry de regras + wrappers de atos (consolidado).

Consolida: regras.py (classificacao, resolucao) + atos/wrappers.py (wrappers diretos).

Uso:
  from Peticao.regras_execucao import classificar, resolver_acao
  bucket = classificar(peticao)
  acao   = resolver_acao(peticao, driver)
"""

import re
import json
from pathlib import Path
from typing import Optional, Any, Callable

from core.rule_registry import RuleRegistry
from Prazo.p2b_core import normalizar_texto
from Peticao.core.extracao import criar_gigs

# ============================================================================
# Logger
# ============================================================================

from Peticao.suporte_pet import get_module_logger

logger = get_module_logger(__name__)

# ============================================================================
# Helpers (podem falhar em ambiente sem dependencias)
# ============================================================================

try:
    from Peticao.helpers import checar_habilitacao, agravo_peticao, def_quesitos, contesta_calc
except ImportError:
    checar_habilitacao = agravo_peticao = def_quesitos = contesta_calc = None

# ============================================================================
# Wrapper factory — make_ato_wrapper
# ============================================================================

try:
    from atos.judicial_fluxo import make_ato_wrapper
except ImportError:
    def make_ato_wrapper(**kwargs):
        def wrapper(driver):
            logger.warning("[ATO_WRAPPER] Funcao make_ato_wrapper nao disponivel. params=%s", kwargs)
            return False
        return wrapper

# ============================================================================
# ATOS — wrappers diretos
# ============================================================================

ato_instc = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='instrumento em r',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de agravo de Instrumento'
)

ato_inste = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='instrumento em a',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de agravo de Instrumento'
)

ato_gen = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome=None,
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Despacho'
)

ato_laudo = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='Geral - Ciencia do laudo pericial',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Ciencia Laudo'
)

ato_esc = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='Conhecimento - Ciencia dos esclarecimentos do Perito',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Ciencia esclarecimentos'
)

ato_escliq = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='aos esclare',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Ciencia esclarecimentos'
)

ato_datalocal = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='data da pericia',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Ciencia dados pericia'
)

ato_ceju = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='sse na rem',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Interesse CEJUSC'
)

ato_respcalc = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xrespcalc',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Contestar Calculos'
)

ato_contestar = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome=None,
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Contestar Calculos de Liquidacao'
)

ato_revel = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome=None,
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Revel - Apresentar Calculos'
)

ato_concor = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='cia com os c',
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Informar Concordancia'
)

ato_prevjud = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='ere prevjud',
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Defere Previdenciario'
)

ato_naocoaf = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='ere coaf',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Indefere COAF'
)

ato_naosimba = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='a - indeferime',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Indefere Simba'
)

ato_teim = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='e teimosinha',
    prazo=None,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    descricao='Teimosinha',
    intimar=False,
    sigilo=True
)

ato_adesivo = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='recebade',
    prazo=8,
    marcar_pec=False,
    movimento=1059,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de Recurso Adesivo'
)

ato_agpetidpj = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='o em idpj',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de agravo de Peticao em IDPJ'
)

ato_agpet = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='recebagp',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Recebimento de agravo de Peticao'
)

ato_agpinter = make_ato_wrapper(
    conclusao_tipo='Admissibilidade',
    modelo_nome='o interloc',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Nao-Recebimento de agravo de Peticao'
)

ato_assistente = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='de assis',
    prazo=1,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=False,
    descricao='Admissao de Assistentes'
)

ato_homacordo = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='homaco',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Homologacao de Acordo'
)

ato_uber = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='uberoficio',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='Oficio Uber'
)

ato_ccs = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='e ccs',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='defere ccs'
)

ato_censec = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='e censec',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='defere censec'
)

ato_serp = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xserp',
    prazo=5,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='defere SERP'
)

ato_conv = make_ato_wrapper(
    conclusao_tipo='Despacho',
    modelo_nome='xconvx',
    prazo=8,
    marcar_pec=False,
    movimento=None,
    gigs=None,
    marcar_primeiro_destinatario=True,
    descricao='despacho'
)

# ============================================================================
# Adaptadores de assinatura de acao
# ============================================================================

def _w(fn):
    """Adapta ato (driver) -> (driver, item) esperado pelo orquestrador."""
    if fn is None:
        return None
    return lambda driver, _: fn(driver)


def _gigs(dias, resp, obs):
    """Factory: callable (driver, item) que chama criar_gigs(driver, dias, resp, obs)."""
    return lambda driver, _: criar_gigs(driver, dias, resp, obs)


# ============================================================================
# Acesso a dados do processo (dadosatuais.json)
# ============================================================================

class _Dados:
    """
    Wrapper sobre dadosatuais.json (gravado por extrair_dados_processo antes de cada acao).
    Expoe condicoes nomeadas reutilizaveis nas regras de classificacao.
    Sem chamada de rede — usa apenas o JSON ja presente em disco.
    """
    def __init__(self):
        self._d: dict = {}
        try:
            p = Path('dadosatuais.json')
            if p.exists():
                self._d = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass

    def fase(self) -> str:
        return normalizar_texto(self._d.get('labelFaseProcessual') or '')

    def reus(self) -> list:
        return self._d.get('reu') or []

    def terceiros(self) -> list:
        return self._d.get('terceiro') or []

    def autores(self) -> list:
        return self._d.get('autor') or []

    def um_reu_com_advogado(self) -> bool:
        reus = self.reus()
        return (
            len(reus) == 1
            and bool(reus[0].get('advogado', {}).get('nome', '').strip())
        )

    def sem_perito_terceiro(self) -> bool:
        return not any(
            'perito' in str(t.get('nome', '')).lower()
            for t in self.terceiros()
        )

    def sem_perito_rogerio(self) -> bool:
        def nome_partes() -> list[str]:
            nomes = []
            for pessoa in self.autores() + self.reus() + self.terceiros():
                nomes.append(str(pessoa.get('nome', '')).lower())
            return nomes
        return not any(
            'rogerio' in nome
            for nome in nome_partes()
        )


def _dados() -> _Dados:
    """Le dadosatuais.json e retorna wrapper com condicoes prontas."""
    return _Dados()


# ============================================================================
# Condicoes complexas
# ============================================================================

def _cond_impugnacao_liq(item) -> bool:
    tipo = normalizar_texto(item.tipo_peticao or '')
    if 'impugnacao' not in tipo or 'liquidacao' not in _nfase(item):
        return False
    d = _dados()
    return d.um_reu_com_advogado() and d.sem_perito_terceiro() and d.sem_perito_rogerio()


# ============================================================================
# Executor de acao
# ============================================================================

def _executar_acao(driver, item, acao) -> bool:
    if isinstance(acao, tuple):
        for f in acao:
            if f is None:
                return False
            if callable(f) and not f(driver, item):
                return False
        return True
    return acao(driver, item) if callable(acao) else False


# ============================================================================
# Deteccao textual para bucket 'analise'
# ============================================================================

def _detectar_acao_analise(texto: str, dados: _Dados):
    if not texto:
        return None
    texto = normalizar_texto(texto)
    if 'ccs' in texto and 'censec' in texto and 'infojud' in texto:
        return (_gigs("1", "", "xs cumprir"), _w(ato_conv)) if ato_conv else (_gigs("1", "", "xs cumprir"),)
    if 'censec' in texto and 'ccs' not in texto:
        return (_gigs("1", "", "xs censec"), _w(ato_censec)) if ato_censec else (_gigs("1", "", "xs censec"),)
    if 'ccs' in texto:
        return (_gigs("1", "", "xs ccs"), _w(ato_ccs)) if ato_ccs else (_gigs("1", "", "xs ccs"),)
    if any(x in texto for x in ['plataformas digitais', 'uber', 'ifood']):
        return (_w(ato_uber),) if ato_uber else None
    if 'crcjud' in texto or 'crc-jud' in texto or 'crc jud' in texto:
        return (_gigs("1", "", "xs serp"), _w(ato_serp)) if ato_serp else (_gigs("1", "", "xs serp"),)
    if 'discordancia aos esclarecimentos' in texto or 'discordancia aos esclarecimentos' in texto:
        return 'flag_apagar'
    if 'assistente tecnico' in texto or 'assistente tecnico' in texto:
        return (_w(ato_assistente),)
    if 'comprovante de pagamento' in texto and 'execucao' in dados.fase():
        return (_gigs("-1", "", "Bruna Liberacao"),)
    return None


# ============================================================================
# Utilitario de normalizacao de fase
# ============================================================================

def _nfase(item) -> str:
    return normalizar_texto(item.fase or '')


# ============================================================================
# TABELA DE REGRAS
# ============================================================================

def _regras(item, driver=None):
    """Tabela unica: (bucket, condicao, acoes).
    Ordem = prioridade. Primeiro match define bucket E acao.
    acoes=None -> apagar (sem abrir processo) ou analise (orquestrador trata).
    checar_habilitacao so avaliado quando driver disponivel.
    """
    tipo   = normalizar_texto(item.tipo_peticao or '')
    desc   = normalizar_texto(item.descricao or '')
    tarefa = normalizar_texto(item.tarefa or '')
    f      = _nfase(item)
    perito = getattr(item, 'eh_perito', False)

    return [
        # -- APAGAR (sem driver, sem abrir processo) -------------------------
        ('apagar',   'parecer do assistente' in desc,                                                      None),
        ('apagar',   'razoes finais' in tipo or 'carta convite' in tipo,                                    None),
        ('apagar',   'conhecimento' in f and 'manifestacao' in tipo and any(x in desc for x in ['replica', 'razoes finais', 'preposicao', 'substabelecimento']), None),
        ('apagar',   'replica' in tipo and 'conhecimento' in f,                                             None),
        ('apagar',   'aguardando cumprimento de acordo' in tarefa,                                          None),
        ('apagar',   'manifestacao' in tipo and any(x in desc for x in ['carta de preposicao', 'substabelecimento']), None),
        ('apagar',   'triagem inicial' in f,                                                                None),
        ('apagar',   'contestacao' in tipo and 'conhecimento' in f,                                        None),
        # -- PERICIAS --------------------------------------------------------
        ('pericias', perito and 'esclarecimentos' in tipo and 'liquidacao' in f and ato_escliq,  (_w(ato_escliq),)),
        ('pericias', perito and 'esclarecimentos' in tipo and ato_esc,                         (_w(ato_esc),)),
        ('pericias', perito and 'apresentacao de laudo pericial' in tipo and ato_laudo,          (_w(ato_laudo),)),
        ('pericias', perito and 'indicacao de data' in tipo and ato_datalocal,                  (_gigs("-1", "", "xs aud"), _w(ato_datalocal))),
        ('pericias', perito and ato_laudo,                                                        (_w(ato_laudo),)),
        # -- RECURSO ---------------------------------------------------------
        ('recurso',  'agravo de instrumento' in tipo and ('liquidacao' in f or 'execucao' in f) and ato_inste, (_w(ato_inste),)),
        ('recurso',  'agravo de instrumento' in tipo and ato_instc,                                             (_w(ato_instc),)),
        ('recurso',  'agravo de peticao' in tipo and agravo_peticao,                         (lambda driver, item: checar_habilitacao(item, driver) if 'habilitacao' in tipo and callable(checar_habilitacao) else agravo_peticao(item, driver),)),
        # -- DIRETOS ---------------------------------------------------------
        ('diretos',  'habilitacao' in tipo and callable(checar_habilitacao),        (lambda driver, item: checar_habilitacao(item, driver),)),
        ('diretos',  ('ratificacao do acordo' in desc or 'ratificacao do acordo' in desc) and ato_homacordo, (_w(ato_homacordo),)),
        ('diretos',  'conhecimento' in f and ('quesitos' in tipo or 'quesitos' in desc) and callable(def_quesitos), (lambda driver, item: def_quesitos(item, driver),)),
        ('diretos',  'coaf' in desc and ato_naocoaf,                                               (_w(ato_naocoaf),)),
        ('diretos',  'simba' in desc and ato_naosimba,                                              (_w(ato_naosimba),)),
        ('diretos',  ('teimosinha' in desc or 'sisbajud' in desc) and ato_teim,                    (_gigs("1", "", "xs teimosinha"), _w(ato_teim))),
        ('diretos',  'recurso adesivo' in tipo and ato_adesivo,                                   (_w(ato_adesivo),)),
        ('diretos',  'calculos' in tipo and (contesta_calc or ato_respcalc),                                           (lambda driver, item: contesta_calc(item, driver),) if contesta_calc else (_w(ato_respcalc),) if ato_respcalc else None),
        ('diretos',  'assistente' in tipo,                                         (_gigs("1", "", "xs aud"), _w(ato_assistente)) if ato_assistente else (_gigs("1", "", "xs aud"),)),
        ('diretos',  _cond_impugnacao_liq(item) and ato_concor,                                 (_w(ato_concor),)),
        ('diretos',  'caged' in desc,                                              (_gigs("-1", "", "xs pec"), _w(ato_prevjud)) if ato_prevjud else (_gigs("-1", "", "xs pec"),)),
        ('diretos',  'concordancia' in desc and 'liquidacao' in f,               (_gigs("1", "Silas", "Homologacao"),)),
        ('diretos',  bool(re.search(r'comprovante|deposito|pagamento|guia', desc)), (_gigs("-1", "", "Bruna Liberacao"),)),
        # -- ANALISE (fallback) ----------------------------------------------
        ('analise',  True,                                                        None),
    ]


# ============================================================================
# REGISTRY DE REGRAS
# ============================================================================

peticao_registry = RuleRegistry(
    "peticao",
    ['apagar', 'pericias', 'recurso', 'diretos', 'analise'],
)

peticao_registry.register(r'parecer do assistente', 'apagar', None)
peticao_registry.register(r'(?:razoes finais|carta convite)', 'apagar', None)
peticao_registry.register(r'aguardando cumprimento de acordo', 'apagar', None)
peticao_registry.register(r'triagem inicial', 'apagar', None)
peticao_registry.register(r'contestacao', 'apagar', None)
peticao_registry.register(r'esclarecimentos', 'pericias', None)
peticao_registry.register(r'apresentacao de laudo pericial', 'pericias', None)
peticao_registry.register(r'indicacao de data', 'pericias', None)
peticao_registry.register(r'agravo de instrumento', 'recurso', None)
peticao_registry.register(r'agravo de peticao', 'recurso', None)
peticao_registry.register(r'habilitacao', 'diretos', None)
peticao_registry.register(r'ratificacao do acordo', 'diretos', None)
peticao_registry.register(r'coaf', 'diretos', None)
peticao_registry.register(r'simba', 'diretos', None)
peticao_registry.register(r'(?:teimosinha|sisbajud)', 'diretos', None)
peticao_registry.register(r'recurso adesivo', 'diretos', None)
peticao_registry.register(r'assistente', 'diretos', None)
peticao_registry.register(r'caged', 'diretos', None)
peticao_registry.register(r'concordancia', 'diretos', None)
peticao_registry.register(r'comprovante|deposito|pagamento|guia', 'diretos', None)


# ============================================================================
# API PUBLICA
# ============================================================================

def classificar(item) -> str:
    """Bucket pelo primeiro match em _regras (sem driver — pura API)."""
    for bucket, cond, _ in _regras(item):
        if cond:
            return bucket
    return 'analise'


def resolver_acao(item, driver=None):
    """Acao pelo primeiro match em _regras."""
    for _, cond, acao in _regras(item, driver):
        if cond:
            return acao
    return None
