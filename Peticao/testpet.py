#!/usr/bin/env python
"""testpet.py - Executor de teste para Peticao"""

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

from Peticao.runtime_pet import PeticaoAPIClient, PeticaoItem
from Peticao.core.utils import criar_driver_e_logar
from Peticao.runtime_pet import ESCANINHO_URL
from Peticao.runtime_pet import classificar, resolver_acao

BUCKETS_ORDEM = ['apagar', 'diretos', 'pericias', 'recurso', 'analise']


def _resolve_callable_name(func) -> str:
    """Extrai nome real de qualquer callable, incluindo lambdas."""
    if func is None:
        return 'None'

    name = getattr(func, '__name__', None)
    if name and name != '<lambda>':
        return name

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

    src_name: str | None = None
    src_is_indirect = False
    src_cond_alt: str | None = None

    try:
        raw = inspect.getsource(func).strip()
        m = re.search(r'lambda\s+[^:]+:\s*(.+)', raw)
        if m:
            body = m.group(1).strip().rstrip(',)').strip()
            fn_m = re.match(r'(\w+)\s*\(', body)
            if fn_m:
                src_name = fn_m.group(1)
                src_is_indirect = (src_name == 'fn')
                if ' if ' in body and ' else ' in body:
                    alt = re.search(r'\belse\b\s+(\w+)\s*\(', body)
                    if alt:
                        src_cond_alt = alt.group(1)
    except (OSError, TypeError, IndentationError):
        pass

    if src_is_indirect:
        if closure_callables:
            return closure_callables[0]
        return 'ato_wrapper'

    if src_name == 'criar_gigs' or (not src_name and closure_callables and closure_callables[0] == 'criar_gigs'):
        obs = next(
            (s for s in closure_strings if s.strip() and not s.lstrip('-').isdigit()),
            ''
        )
        return f'criar_gigs("{obs}")' if obs else 'criar_gigs'

    if src_name:
        if src_cond_alt:
            return f'{src_name} | {src_cond_alt}'
        return src_name

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


def _acao_analise_seca(driver, item: PeticaoItem) -> str:
    """Lê a petição via API e determina a ação que seria tomada (dry run)."""
    from Peticao.runtime_pet import extrair_texto_peticao_via_api, _detectar_acao_analise, _Dados

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
