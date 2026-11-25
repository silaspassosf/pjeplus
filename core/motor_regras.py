"""
core/motor_regras.py — Motor centralizado de regras (P2B, Mandado/Argos e PEC).

Unifica os 3 fluxos principais sob o mesmo modelo declarativo do P2B:
    ([padrao_1, padrao_2, ...], (acao_1, acao_2, ...))

Suporta:
1. Gatilhos (Matchers):
   - Termo simples em texto plano -> convertido via `gerar_regex_geral` (tolerante a acentos, espaços e pontuação, estilo P2B).
   - Regex explícito (`re.Pattern` ou string com sintaxe regex quando `modo_regex=True` / `rx(...)`).
   - Filtros opcionais de contexto: `tipos_documento=('decisao', 'despacho')` (Mandado) e `bucket='comunicacoes'` (PEC).

2. Ações (Pipeline):
   - Ação única ou sequência `(acao_1, acao_2, ...)` com curto-circuito em falha (`False`).
   - String DSL: `"criar_gigs[dias/resp/obs]"`, `"mov_int[Destino]"`, `"mov_sob[sob N]"`, `"bndt[inclusao]"`.
   - Função direta `fn(driver)` (atos, comunicacoes, movimentos).
   - Helper contextual `fn(driver, ctx)` (detectado automaticamente pela assinatura).
"""

from __future__ import annotations

import inspect
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Pattern, Sequence, Tuple, Union

from Fix.utils import normalizar_texto

logger = logging.getLogger(__name__)

PadraoInput = Union[str, Pattern[str]]
AcaoInput = Union[str, Callable[..., Any]]
PipelineInput = Union[AcaoInput, Sequence[AcaoInput]]


def gerar_regex_geral(termo: str) -> Pattern[str]:
    """Gera regex tolerante para busca de termos em texto normalizado (padrão P2B)."""
    termo_norm = normalizar_texto(termo)
    palavras = termo_norm.split()
    partes = [re.escape(p) for p in palavras]
    costura = r'[\s\.,;:!\-–—()$/]*'
    regex = costura.join(partes)
    return re.compile(rf"{regex}", re.IGNORECASE)


def rx(pattern: str) -> Pattern[str]:
    """Atalho explícito para declarar regex cru na tabela de regras."""
    return re.compile(pattern, re.IGNORECASE)


def parse_gigs_param(parametro: str) -> Tuple[str, str, str]:
    """Faz parse de 'dias/responsavel/observacao'."""
    partes = parametro.split('/')
    if len(partes) == 3:
        return partes[0], partes[1], partes[2]
    return "1", parametro, parametro


def normalizar_resultado_acao(resultado: Any) -> Any:
    """Converte None em True mantendo False e tuplas explícitas."""
    if resultado is None:
        return True
    if isinstance(resultado, tuple) and len(resultado) != 3:
        return bool(resultado[0]) if resultado else False
    return resultado


@dataclass
class ContextoRegra:
    """Contexto unificado passado aos matchers e helpers dos 3 fluxos."""
    texto: str = ""
    tipo_documento: Optional[str] = None
    numero_processo: Optional[str] = None
    observacao: Optional[str] = None
    atv: Any = None
    resultado_sisbajud: Optional[str] = None
    sigilo_anexos: Optional[Dict[str, str]] = None
    doc_idx: int = 0
    itens_timeline: Optional[List[Any]] = None
    data_decisao: Optional[str] = None
    debug: bool = False
    extras: Dict[str, Any] = field(default_factory=dict)

    @property
    def texto_normalizado(self) -> str:
        base = self.texto or self.observacao or ""
        return normalizar_texto(str(base))

    @property
    def tipo_normalizado(self) -> str:
        return normalizar_texto(str(self.tipo_documento or ""))

    @property
    def tem_anexos_sigilosos(self) -> bool:
        return any(v == 'sim' for v in (self.sigilo_anexos or {}).values())


@dataclass
class Regra:
    """Regra declarativa unificada."""
    padroes: List[Pattern[str]]
    acoes: Tuple[AcaoInput, ...]
    nome: str = ""
    bucket: str = "default"
    tipos_documento: Optional[Tuple[str, ...]] = None
    condicao_extra: Optional[Callable[[ContextoRegra], bool]] = None

    def casar(self, ctx: ContextoRegra) -> Optional[re.Match[str]]:
        """Retorna o re.Match se a regra atender ao contexto e ao texto, ou None."""
        if self.tipos_documento:
            tipo_norm = ctx.tipo_normalizado
            if not any(t in tipo_norm for t in self.tipos_documento):
                return None

        if self.condicao_extra is not None and not self.condicao_extra(ctx):
            return None

        alvo = ctx.texto_normalizado
        if not alvo:
            return None

        for padrao in self.padroes:
            m = padrao.search(alvo)
            if m:
                return m
        return None


def _aceita_contexto(fn: Callable[..., Any]) -> bool:
    """Verifica se o callable aceita 2+ parâmetros posicionais `(driver, ctx/atv)`."""
    try:
        sig = inspect.signature(fn)
        params = [
            p for p in sig.parameters.values()
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        if any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values()):
            return True
        return len(params) >= 2
    except (ValueError, TypeError):
        return False


class MotorRegras:
    """
    Motor centralizado de regras para P2B, Mandado e PEC.

    Permite registrar regras tanto no formato enxuto do P2B:
        motor.adicionar_tabela([
            (['sob pena de bloqueio', 'homologo os calculos'], (inicar_exec,)),
            (['Ante a notícia de descumprimento'], ("criar_gigs[1/Ana Lucia/Argos]", ato_pesqliq)),
        ])
    quanto com metadados de Mandado (`tipos_documento`) ou PEC (`bucket`).
    """

    def __init__(
        self,
        nome: str,
        bucket_order: Optional[List[str]] = None,
        modo_regex_padrao: bool = False,
         handlers_dsl: Optional[Dict[str, Callable[[Any, str, ContextoRegra], Any]]] = None,
    ):
        self.nome = nome
        self.bucket_order = bucket_order or ["default"]
        self.modo_regex_padrao = modo_regex_padrao
        self._regras: List[Regra] = []
        self._handlers_dsl: Dict[str, Callable[[Any, str, ContextoRegra], Any]] = {
            "criar_gigs": self._dsl_criar_gigs,
            "mov_int": self._dsl_mov_int,
            "mov_sob": self._dsl_mov_sob,
            "bndt": self._dsl_bndt,
        }
        if handlers_dsl:
            self._handlers_dsl.update(handlers_dsl)

    def _compilar(self, padrao: PadraoInput, como_regex: Optional[bool] = None) -> Pattern[str]:
        if isinstance(padrao, re.Pattern):
            return padrao
        usar_regex = self.modo_regex_padrao if como_regex is None else como_regex
        if usar_regex:
            return re.compile(normalizar_texto(padrao), re.IGNORECASE)
        return gerar_regex_geral(padrao)

    def registrar(
        self,
        padroes: Union[PadraoInput, Iterable[PadraoInput]],
        acoes: PipelineInput,
        *,
        nome: str = "",
        bucket: str = "default",
        tipos_documento: Optional[Union[str, Sequence[str]]] = None,
        condicao_extra: Optional[Callable[[ContextoRegra], bool]] = None,
        como_regex: Optional[bool] = None,
    ) -> Regra:
        """Registra uma regra no motor."""
        if isinstance(padroes, (str, re.Pattern)):
            lista_padroes = [self._compilar(padroes, como_regex=como_regex)]
        else:
            lista_padroes = [self._compilar(p, como_regex=como_regex) for p in padroes]

        if isinstance(acoes, (str, Callable)) or not isinstance(acoes, Sequence):
            tupla_acoes = (acoes,)
        else:
            tupla_acoes = tuple(acoes)

        if isinstance(tipos_documento, str):
            tipos_norm: Optional[Tuple[str, ...]] = (normalizar_texto(tipos_documento),)
        elif tipos_documento:
            tipos_norm = tuple(normalizar_texto(t) for t in tipos_documento)
        else:
            tipos_norm = None

        if bucket not in self.bucket_order:
            self.bucket_order.append(bucket)

        regra = Regra(
            padroes=lista_padroes,
            acoes=tupla_acoes,
            nome=nome or (lista_padroes[0].pattern[:40] if lista_padroes else "regra"),
            bucket=bucket,
            tipos_documento=tipos_norm,
            condicao_extra=condicao_extra,
        )
        self._regras.append(regra)
        return regra

    def adicionar_tabela(
        self,
        linhas: Sequence[Tuple[ Sequence[PadraoInput], PipelineInput ]],
        *,
        bucket: str = "default",
        tipos_documento: Optional[Union[str, Sequence[str]]] = None,
        como_regex: Optional[bool] = None,
    ) -> None:
        """Carrega uma tabela no formato direto do P2B: `[([trechos...], (acoes...)), ...]`."""
        for padroes, acoes in linhas:
            self.registrar(
                padroes,
                acoes,
                bucket=bucket,
                tipos_documento=tipos_documento,
                como_regex=como_regex,
            )

    def regras_ordenadas(self) -> List[Regra]:
        """Retorna as regras respeitando a ordem de `bucket_order` e a ordem de inserção."""
        if len(self.bucket_order) <= 1:
            return list(self._regras)
        ordenadas: List[Regra] = []
        for b in self.bucket_order:
            ordenadas.extend(r for r in self._regras if r.bucket == b)
        return ordenadas

    def avaliar(
        self,
        entrada: Union[str, ContextoRegra],
        **kwargs: Any,
    ) -> Optional[Tuple[Regra, re.Match[str]]]:
        """Encontra a primeira regra que casa com o texto/contexto sem executar ações."""
        ctx = entrada if isinstance(entrada, ContextoRegra) else ContextoRegra(texto=str(entrada or ""), **kwargs)
        for regra in self.regras_ordenadas():
            match = regra.casar(ctx)
            if match:
                return regra, match
        return None

    def executar(
        self,
        driver: Any,
        entrada: Union[str, ContextoRegra],
        **kwargs: Any,
    ) -> Any:
        """Avalia e executa o pipeline de ações da primeira regra que casar."""
        ctx = entrada if isinstance(entrada, ContextoRegra) else ContextoRegra(texto=str(entrada or ""), **kwargs)
        avaliacao = self.avaliar(ctx)
        if not avaliacao:
            return None

        regra, match = avaliacao
        logger.info(
            "[MOTOR:%s] Regra casada: nome=%r bucket=%s match=%r",
            self.nome,
            regra.nome,
            regra.bucket,
            match.group(0)[:80],
        )
        return self._executar_pipeline(driver, regra.acoes, ctx)

    def _executar_pipeline(
        self,
        driver: Any,
        acoes: Tuple[AcaoInput, ...],
        ctx: ContextoRegra,
    ) -> Any:
        ultimo_resultado: Any = True
        for acao in acoes:
            if acao is None:
                continue
            res = self._executar_passo(driver, acao, ctx)
            # Retorno especial de 3 elementos do checar_prox: (item, link, idx)
            if isinstance(res, tuple) and len(res) == 3:
                return res
            norm = normalizar_resultado_acao(res)
            if norm is False:
                logger.warning("[MOTOR:%s] Passo falhou e interrompeu pipeline: %r", self.nome, acao)
                return False
            if norm is not True:
                ultimo_resultado = norm
        return ultimo_resultado

    def _executar_passo(self, driver: Any, acao: AcaoInput, ctx: ContextoRegra) -> Any:
        if isinstance(acao, str):
            m_dsl = re.match(r'^([a-zA-Z0-9_]+)\[(.*)\]$', acao.strip())
            if not m_dsl:
                logger.error("[MOTOR:%s] DSL inválida: %r", self.nome, acao)
                return False
            cmd, arg = m_dsl.group(1), m_dsl.group(2)
            handler = self._handlers_dsl.get(cmd)
            if not handler:
                logger.error("[MOTOR:%s] Comando DSL desconhecido: %r", self.nome, cmd)
                return False
            return handler(driver, arg, ctx)

        if callable(acao):
            if _aceita_contexto(acao):
                # Compatibilidade com PEC: se ctx.atv existir e o 2º param se chamar 'atv', passa atv ou ctx
                sig = inspect.signature(acao)
                params = list(sig.parameters.keys())
                if len(params) >= 2 and params[1] == "atv" and ctx.atv is not None:
                    return acao(driver, ctx.atv)
                return acao(driver, ctx)
            return acao(driver)

        return False

    # ── Handlers DSL Nativos ──────────────────────────────────────────────────

    @staticmethod
    def _dsl_criar_gigs(driver: Any, arg: str, ctx: ContextoRegra) -> Any:
        from Fix.extracao import criar_gigs
        dias, responsavel, observacao = parse_gigs_param(arg)
        return criar_gigs(driver, dias, responsavel, observacao)

    @staticmethod
    def _dsl_mov_int(driver: Any, arg: str, ctx: ContextoRegra) -> Any:
        from atos.movimentos_fluxo import movimentar_inteligente
        return movimentar_inteligente(driver, arg.strip())

    @staticmethod
    def _dsl_mov_sob(driver: Any, arg: str, ctx: ContextoRegra) -> Any:
        from atos.movimentos import mov_sob
        num = ctx.numero_processo or getattr(ctx.atv, "numero_processo", "")
        obs = arg.strip() or ctx.observacao or getattr(ctx.atv, "observacao", "")
        return mov_sob(driver, num, obs, debug=ctx.debug)

    @staticmethod
    def _dsl_bndt(driver: Any, arg: str, ctx: ContextoRegra) -> Any:
        from Fix.extracao import bndt
        inclusao = arg.strip().lower() != "exclusao"
        return bndt(driver, inclusao=inclusao)
