"""
tools/grab.py
Recorder de sessao autenticada PJe.

Abre um driver Firefox autenticado, injeta dois scripts em paralelo:
  - Script/Java/pjeapi.js    → intercepta fetch + XHR (API calls)
  - tools/grab_recorder.js   → captura cliques, inputs, changes, focus

Faz poll a cada POLL_INTERVAL segundos. Ao fechar o browser (ou Ctrl+C),
exporta e organiza os dados em grab_out/session_<timestamp>/.

Uso:
  py tools/grab.py                 # driver PC padrao
  py tools/grab.py --notebook      # driver notebook
  py tools/grab.py --verbose       # log de cada evento em tempo real

Saida (grab_out/session_<ts>/):
  raw_events.json       todos os eventos de interacao humana
  raw_api.json          log completo da API (window.__pje.log)
  selectors.json        seletores agrupados por pagina/componente
  api_map.json          endpoints por template de URL
  merged.json           eventos com API calls correlacionadas
  patch_seletores.json  delta para aprendizado_seletores.json
"""

import json
import time
import sys
import datetime
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from Fix.core import criar_driver_PC, criar_driver_notebook  # noqa: E402

GRAB_JS  = ROOT / 'tools' / 'grab_recorder.js'
SPY_JS   = ROOT / 'Script' / 'Java' / 'pjeapi.js'
OUT_DIR  = ROOT / 'grab_out'
SELETORES_JSON = ROOT / 'aprendizado_seletores.json'

POLL_INTERVAL = 2.0  # segundos entre polls


# ── Injecao ───────────────────────────────────────────────────────────────────

def _injetar(driver, verbose=False):
    """Injeta pjeapi.js + grab_recorder.js no contexto da aba atual."""
    spy_src  = SPY_JS.read_text(encoding='utf-8')
    grab_src = GRAB_JS.read_text(encoding='utf-8')
    driver.execute_script(spy_src)
    driver.execute_script(grab_src)
    if verbose:
        print(f'  [GRAB] injetado em {driver.current_url[:80]}')


# ── Coleta ────────────────────────────────────────────────────────────────────

def _flush(driver):
    """Retorna novos eventos desde o ultimo poll (grab_recorder.js)."""
    try:
        return driver.execute_script('return window.__grab ? window.__grab.flush() : []') or []
    except Exception:
        return []


def _api_log(driver):
    """Retorna log completo do pjeapi.js para esta aba."""
    try:
        return driver.execute_script('return window.__pje ? window.__pje.log : []') or []
    except Exception:
        return []


# ── Loop principal ────────────────────────────────────────────────────────────

def _rodar_sessao(driver, verbose=False):
    """
    Loop de captura ate o browser fechar ou Ctrl+C.
    Retorna (all_events, all_api_log).
    """
    all_events: list  = []
    all_api:    list  = []
    injected:   set   = set()

    print('[GRAB] Sessao iniciada. Navegue normalmente.')
    print('[GRAB] Feche o browser ou pressione Ctrl+C para exportar.')
    print('[GRAB] Atalhos no console do browser:')
    print('         Shift+Alt+W  = watchNext (pjeapi)')
    print('         Shift+Alt+S  = summary (pjeapi)')
    print('         __grab.stats() = estatisticas do recorder')

    try:
        while True:
            time.sleep(POLL_INTERVAL)

            # ── injetar em novas abas ──
            try:
                handles = driver.window_handles
            except Exception:
                break  # browser fechado

            for h in handles:
                if h not in injected:
                    try:
                        driver.switch_to.window(h)
                        _injetar(driver, verbose)
                        injected.add(h)
                    except Exception as e:
                        print(f'[GRAB] Falha ao injetar em nova aba: {e}')

            # ── remover handles que fecharam ──
            injected &= set(handles)

            # ── poll de eventos em cada aba ──
            for h in list(injected):
                if h not in handles:
                    continue
                try:
                    driver.switch_to.window(h)
                    novos = _flush(driver)
                    if novos:
                        all_events.extend(novos)
                        if verbose:
                            for ev in novos:
                                print(f'  [{ev["type"]:8s}] {ev["page_path"]} | {ev.get("el_info", {}).get("best_selector", "?")}')
                        else:
                            tipos = {}
                            for ev in novos:
                                tipos[ev['type']] = tipos.get(ev['type'], 0) + 1
                            print(f'[GRAB] +{len(novos)} evento(s): {tipos}  (total={len(all_events)})')
                except Exception:
                    injected.discard(h)

    except KeyboardInterrupt:
        print('\n[GRAB] Ctrl+C detectado — exportando...')

    # ── coleta final da API de todas as abas vivas ──
    print('[GRAB] Coletando log de API de todas as abas...')
    try:
        for h in list(injected):
            if h not in driver.window_handles:
                continue
            driver.switch_to.window(h)
            log = _api_log(driver)
            if log:
                all_api.extend(log)
                print(f'  [GRAB] aba {h[:8]}: {len(log)} chamadas API')
    except Exception as e:
        print(f'[GRAB] Erro na coleta API final: {e}')

    try:
        driver.quit()
    except Exception:
        pass

    return all_events, all_api


# ── Processamento pos-sessao ──────────────────────────────────────────────────

def _organizar_seletores(events: list) -> dict:
    """
    Agrupa eventos de clique por page_path + chave semantica.
    Retorna {page_path: {chave: {count, candidates, best_selector, stability}}}
    """
    by_page: dict = {}
    for ev in events:
        if ev.get('type') not in ('click', 'focus', 'change'):
            continue
        path = ev.get('page_path', '/')
        info = ev.get('el_info') or {}
        # chave semantica: aria-label > texto visivel > tag+classe
        chave = (
            info.get('ariaLabel') or
            info.get('name') or
            info.get('text') or
            (info.get('tag', '') + '_' + '_'.join((info.get('classes') or []))[:25])
        ).strip().lower().replace(' ', '_')[:50]
        chave = chave.replace('"', '').replace("'", '').replace('/', '_')
        if not chave or chave in ('_', ''):
            continue
        by_page.setdefault(path, {})
        rec = by_page[path].setdefault(chave, {
            'count': 0,
            'candidates': [],
            'best_selector': None,
            'stability': 'unknown',
        })
        rec['count'] += 1
        rec['candidates'].extend(info.get('selector_candidates') or [])
        # atualizar best se mais estavel
        for cand in (info.get('selector_candidates') or []):
            rank = {'high': 3, 'medium': 2, 'low': 1, 'unknown': 0}
            if rank.get(cand['stability'], 0) > rank.get(rec['stability'], 0):
                rec['best_selector'] = cand['selector']
                rec['stability']     = cand['stability']
    return by_page


def _api_map(api_log: list) -> dict:
    """
    Agrupa chamadas API por urlTemplate.
    Retorna {urlTemplate: {method, count, example_url, response_fields}}
    """
    by_tmpl: dict = {}
    for entry in api_log:
        tmpl = entry.get('urlTemplate') or entry.get('url', '')
        rec  = by_tmpl.setdefault(tmpl, {
            'method':           entry.get('method', 'GET'),
            'urlTemplate':      tmpl,
            'count':            0,
            'example_url':      entry.get('url'),
            'example_status':   entry.get('status'),
            'response_fields':  [],
        })
        rec['count'] += 1
        if not rec['response_fields']:
            res = entry.get('resBody')
            if isinstance(res, dict):
                arr = (res.get('resultado') or res.get('content') or
                       res.get('conteudo') or res.get('lista') or [])
                if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                    rec['response_fields'] = list(arr[0].keys())
                else:
                    rec['response_fields'] = list(res.keys())
    return by_tmpl


def _merge(events: list, api_log: list) -> list:
    """
    Para cada evento de clique, adiciona as API calls disparadas
    nos 3 segundos seguintes (correlacao por timestamp).
    """
    merged = []
    for ev in events:
        if ev.get('type') != 'click':
            merged.append(ev)
            continue
        ts_ms = ev.get('ts', 0)
        apis  = [
            {
                'method':      a.get('method'),
                'urlTemplate': a.get('urlTemplate'),
                'url':         a.get('url'),
                'status':      a.get('status'),
                'duration_ms': a.get('duration'),
            }
            for a in api_log
            # api_log ts e em ms (performance.timeOrigin + performance.now())
            # event ts e Date.now() em ms — mesma escala
            if ts_ms <= a.get('ts', 0) <= ts_ms + 3000
        ]
        merged.append({**ev, 'triggered_apis': apis})
    return merged


def _patch_seletores(organized: dict) -> dict:
    """
    Compara seletores descobertos com aprendizado_seletores.json.
    Retorna apenas entradas novas ou melhoradas.
    """
    try:
        existentes = json.loads(SELETORES_JSON.read_text(encoding='utf-8'))
    except Exception:
        existentes = {}

    patch = {}
    for _page, comps in organized.items():
        for chave, data in comps.items():
            bs = data.get('best_selector')
            st = data.get('stability', 'unknown')
            if not bs:
                continue
            # adicionar se nao existe, ou se a nova estabilidade e maior
            rank = {'high': 3, 'medium': 2, 'low': 1, 'unknown': 0}
            existing_entry = existentes.get(chave)
            if not existing_entry:
                patch[chave] = [st, bs, {'count': data['count'], 'page': _page}]
            else:
                # existente pode ser [tipo, seletor] do formato antigo
                # nao sobrescrever se ja estavel
                existing_stab = existing_entry[0] if isinstance(existing_entry, list) else 'unknown'
                if rank.get(st, 0) > rank.get(existing_stab, 0):
                    patch[chave] = [st, bs, {'count': data['count'], 'page': _page, 'upgrade_from': existing_stab}]
    return patch


# ── Salvar sessao ─────────────────────────────────────────────────────────────

def _salvar(session_dir: Path, events: list, api_log: list):
    session_dir.mkdir(parents=True, exist_ok=True)

    organized = _organizar_seletores(events)
    api_mapa  = _api_map(api_log)
    merged    = _merge(events, api_log)
    patch     = _patch_seletores(organized)

    def dump(name, obj):
        (session_dir / name).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    dump('raw_events.json',      events)
    dump('raw_api.json',         api_log)
    dump('selectors.json',       organized)
    dump('api_map.json',         api_mapa)
    dump('merged.json',          merged)
    dump('patch_seletores.json', patch)

    print(f'\n[GRAB] Sessao salva em: {session_dir}')
    print(f'  raw_events.json       {len(events)} eventos')
    print(f'  raw_api.json          {len(api_log)} chamadas API')
    print(f'  selectors.json        {sum(len(v) for v in organized.values())} componentes')
    print(f'  api_map.json          {len(api_mapa)} endpoints unicos')
    print(f'  patch_seletores.json  {len(patch)} entradas novas/melhoradas')

    if patch:
        print('\n[GRAB] Novos seletores descobertos:')
        for k, v in list(patch.items())[:20]:
            print(f'  {k}: stability={v[0]}  selector={v[1]}')
        if len(patch) > 20:
            print(f'  ... e mais {len(patch) - 20}')

    # Pergunta se aplica o patch
    if patch:
        resp = input('\n[GRAB] Aplicar patch em aprendizado_seletores.json? [s/N] ').strip().lower()
        if resp == 's':
            try:
                existentes = json.loads(SELETORES_JSON.read_text(encoding='utf-8'))
            except Exception:
                existentes = {}
            for k, v in patch.items():
                existentes[k] = v[:2]  # salva apenas [stability, selector]
            SELETORES_JSON.write_text(
                json.dumps(existentes, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            print(f'[GRAB] aprendizado_seletores.json atualizado ({len(existentes)} entradas totais).')
        else:
            print('[GRAB] Patch nao aplicado. Arquivo salvo em patch_seletores.json.')

    return patch


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='PJePlus grab recorder')
    parser.add_argument('--notebook', action='store_true', help='Usar driver notebook')
    parser.add_argument('--verbose',  action='store_true', help='Log de cada evento em tempo real')
    args = parser.parse_args()

    ts          = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = OUT_DIR / f'session_{ts}'

    print('[GRAB] Iniciando driver autenticado...')
    if args.notebook:
        driver = criar_driver_notebook()
    else:
        driver = criar_driver_PC()

    events, api_log = _rodar_sessao(driver, verbose=args.verbose)
    _salvar(session_dir, events, api_log)


if __name__ == '__main__':
    main()
