#!/usr/bin/env python
"""testpet.py - Executor de teste para Peticao

Uso:
    py testpet.py
    py testpet.py --processo 0000000-00.0000.0.00.0000

Relatório final: Markdown com número do processo, bucket e ação prevista.

Notas:
- Não executa nenhuma ação real (dry run puro).
- Bucket 'analise': lê o PDF da petição via API e detecta a ação que seria tomada.
"""

from __future__ import annotations

import argparse
import inspect
import os
import re
import sys
from typing import List, Optional

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from Peticao.api_client import PeticaoAPIClient, PeticaoItem
from Peticao.core.utils import criar_driver_e_logar
from Peticao.orquestrador import ESCANINHO_URL
from Peticao.pet import classificar, resolver_acao

BUCKETS_ORDEM = ['apagar', 'diretos', 'pericias', 'recurso', 'analise']


# ---------------------------------------------------------------------------
# Resolução de nomes a partir de closures (elimina "<lambda>" no relatório)
# ---------------------------------------------------------------------------

def _resolve_callable_name(func) -> str:
    """
    Extrai nome real de qualquer callable, incluindo lambdas.
    Estratégia:
      1. inspect.getsource → extrai nome da função chamada no corpo do lambda
         (funciona mesmo quando a variável capturada é None por import failure)
      2. Closure inspection → suporte para:
         - _gigs: extrai valor de obs dos args capturados
         - _w(fn): quando fonte mostra 'fn(driver)', closure dá o __name__ real
         - fallback geral quando fonte não disponível
    """
    if func is None:
        return 'None'

    name = getattr(func, '__name__', None)
    if name and name != '<lambda>':
        return name

    # --- Pré-carrega closure (usada em múltiplos pontos abaixo) ---
    closure = getattr(func, '__closure__', None) or []
    closure_callables: list[str] = []
    closure_strings: list[str] = []
    for cell in closure:
        try:
            val = cell.cell_contents
            if callable(val):
                vname = getattr(val, '__name__', None)
                if vname and vname != '<lambda>':
                    closure_callables.append(vname)
            elif isinstance(val, str):
                closure_strings.append(val)
        except ValueError:
            pass

    # --- Inspeção de fonte (primária) ---
    src_name: str | None = None
    src_is_indirect = False   # True quando corpo é 'fn(...)' — padrão _w
    src_cond_alt: str | None = None  # função no else de lambdas condicionais

    try:
        raw = inspect.getsource(func).strip()
        # Isola o corpo do lambda (tudo depois do primeiro ':')
        m = re.search(r'lambda\s+[^:]+:\s*(.+)', raw)
        if m:
            body = m.group(1).strip().rstrip(',)').strip()
            fn_m = re.match(r'(\w+)\s*\(', body)
            if fn_m:
                src_name = fn_m.group(1)
                # Padrão _w: lambda driver, _: fn(driver)
                src_is_indirect = (src_name == 'fn')
                # Padrão condicional: func1(...) if COND else func2(...)
                if ' if ' in body and ' else ' in body:
                    alt = re.search(r'\belse\b\s+(\w+)\s*\(', body)
                    if alt:
                        src_cond_alt = alt.group(1)
    except (OSError, TypeError, IndentationError):
        pass

    # --- Decisão ---

    # _w(fn): fonte diz 'fn(...)' → nome real vem da closure
    if src_is_indirect:
        if closure_callables:
            return closure_callables[0]
        return 'ato_wrapper'

    # _gigs: fonte ou closure aponta 'criar_gigs' → completa com obs
    if src_name == 'criar_gigs' or (not src_name and closure_callables and closure_callables[0] == 'criar_gigs'):
        obs = next(
            (s for s in closure_strings if s.strip() and not s.lstrip('-').isdigit()),
            ''
        )
        return f'criar_gigs("{obs}")' if obs else 'criar_gigs'

    # Lambda direto: fonte encontrou um nome de função
    if src_name:
        if src_cond_alt:
            return f'{src_name} | {src_cond_alt}'
        return src_name

    # Fallback via closure
    if closure_callables:
        if len(closure_callables) > 1:
            return ' | '.join(closure_callables)
        return closure_callables[0]

    return 'lambda_generico'


def _format_acao(action) -> str:
    """Formata ação (tuple ou callable) como string legível."""
    if action is None:
        return 'sem_acao'
    if isinstance(action, tuple):
        return ' + '.join(_resolve_callable_name(f) for f in action)
    return _resolve_callable_name(action)


# ---------------------------------------------------------------------------
# Motivo do apagar (replica as condições de _regras sem chamar pet.py)
# ---------------------------------------------------------------------------

def _descrever_apagar(item: PeticaoItem) -> str:
    """Determina qual condição de apagar se aplicou ao item."""
    from Prazo.p2b_core import normalizar_texto
    tipo  = normalizar_texto(item.tipo_peticao or '')
    desc  = normalizar_texto(item.descricao or '')
    tarefa = normalizar_texto(item.tarefa or '')
    f     = normalizar_texto(item.fase or '')

    if 'parecer do assistente' in desc:
        return 'parecer do assistente'
    if 'razoes finais' in tipo:
        return 'razoes finais'
    if 'carta convite' in tipo:
        return 'carta convite'
    if 'conhecimento' in f and 'manifestacao' in tipo and any(
        x in desc for x in ['replica', 'razoes finais', 'preposicao', 'substabelecimento']
    ):
        return 'manifestacao c/ replica/substabelecimento em conhecimento'
    if 'replica' in tipo and 'conhecimento' in f:
        return 'replica em conhecimento'
    if 'aguardando cumprimento de acordo' in tarefa:
        return 'aguardando cumprimento de acordo'
    if 'manifestacao' in tipo and any(x in desc for x in ['carta de preposicao', 'substabelecimento']):
        return 'manifestacao c/ carta/substabelecimento'
    if 'triagem inicial' in f:
        return 'triagem inicial'
    if 'contestacao' in tipo and 'conhecimento' in f:
        return 'contestacao em conhecimento'
    return 'cond_nao_identificada'


# ---------------------------------------------------------------------------
# Resolução do bucket 'analise' via leitura real da petição (sem executar nada)
# ---------------------------------------------------------------------------

def _acao_analise_seca(driver, item: PeticaoItem) -> str:
    """
    Lê a petição via API e determina a ação que seria tomada (dry run).
    Se a API não retornar texto, reporta ato_gen como fallback.
    """
    from Peticao.pet import extrair_texto_peticao_via_api, _detectar_acao_analise, _Dados

    texto = extrair_texto_peticao_via_api(driver, item)
    if not texto:
        return 'ato_gen (texto_nao_disponivel_via_api)'

    dados = _Dados()
    acao = _detectar_acao_analise(texto, dados)

    if acao is None:
        return 'ato_gen (fallback)'
    if acao == 'flag_apagar':
        return 'flag_apagar → apagar'

    return f'{_format_acao(acao)} [via analise]'


# ---------------------------------------------------------------------------
# Ação prevista por bucket
# ---------------------------------------------------------------------------

def _acao_prevista(driver, item: PeticaoItem, bucket: str) -> str:
    if bucket == 'analise':
        return _acao_analise_seca(driver, item)
    if bucket == 'apagar':
        return f'apagar | motivo: {_descrever_apagar(item)}'

    try:
        action = resolver_acao(item, driver=None)
    except Exception:
        return 'acao_indeterminada_sem_driver'

    return _format_acao(action)


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _selecionar_por_processo(itens: List[PeticaoItem], processo_id: str) -> List[PeticaoItem]:
    filtro = processo_id.strip()
    return [
        item for item in itens
        if filtro in (item.numero_processo or '')
        or filtro in (item.id_processo or '')
        or filtro in (item.id_item or '')
    ]


def _fetch_peticoes(driver) -> List[PeticaoItem]:
    driver.get(ESCANINHO_URL)
    return PeticaoAPIClient().fetch(driver)


def _gerar_relatorio_markdown(rows: List[tuple[str, str, str]]) -> str:
    header = '| Processo | Bucket | Ação prevista |'
    separator = '|---|---|---|'
    lines = [header, separator]
    for processo, bucket, acao in rows:
        lines.append(f'| {processo} | {bucket} | {acao} |')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Orquestrador do teste
# ---------------------------------------------------------------------------

def executar_teste(driver, processo_id: Optional[str] = None) -> str:
    itens = _fetch_peticoes(driver)
    if processo_id:
        itens = _selecionar_por_processo(itens, processo_id)
        if not itens:
            raise RuntimeError(f'Processo não encontrado na API: {processo_id}')

    buckets: dict[str, List[PeticaoItem]] = {nome: [] for nome in BUCKETS_ORDEM}
    for item in itens:
        bucket = classificar(item)
        buckets.setdefault(bucket, []).append(item)

    rows: List[tuple[str, str, str]] = []
    for bucket in BUCKETS_ORDEM:
        for item in buckets.get(bucket, []):
            acao = _acao_prevista(driver, item, bucket)
            rows.append((item.numero_processo or item.id_processo or 'n/a', bucket, acao))

    return _gerar_relatorio_markdown(rows)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Teste rápido de bucket e ação de Peticao')
    parser.add_argument('--processo', '-p', help='ID ou número do processo para teste individual')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    driver = criar_driver_e_logar()
    if not driver:
        print('Erro: não foi possível criar ou logar no driver.', file=sys.stderr)
        return 1

    try:
        resultado = executar_teste(driver, processo_id=args.processo)
        print(resultado)
        return 0
    except Exception as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 2
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    raise SystemExit(main())
