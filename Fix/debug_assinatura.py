import json
import os
from Fix.log import logger

_CACHE_PATH = os.path.join(os.path.dirname(__file__), '..', 'cache', 'delta_assinatura.json')
_ATIVO = os.environ.get('PJEPLUS_DEBUG_ASSINATURA', '').lower() in ('1', 'true')


def ativo():
    return _ATIVO


def capturar_estado_browser(driver):
    try:
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    except Exception:
        cookies = {}
    try:
        ls = driver.execute_script("return Object.assign({}, localStorage)") or {}
    except Exception:
        ls = {}
    try:
        ss = driver.execute_script("return Object.assign({}, sessionStorage)") or {}
    except Exception:
        ss = {}
    return {'cookies': cookies, 'localStorage': ls, 'sessionStorage': ss}


def diff_estado(antes, depois):
    delta = {}
    for chave in ('cookies', 'localStorage', 'sessionStorage'):
        novos = {k: v for k, v in depois[chave].items() if k not in antes[chave]}
        alterados = {
            k: {'antes': antes[chave][k], 'depois': v}
            for k, v in depois[chave].items()
            if k in antes[chave] and antes[chave][k] != v
        }
        removidos = {k: v for k, v in antes[chave].items() if k not in depois[chave]}
        if novos or alterados or removidos:
            delta[chave] = {}
            if novos:
                delta[chave]['novos'] = novos
            if alterados:
                delta[chave]['alterados'] = alterados
            if removidos:
                delta[chave]['removidos'] = removidos
    return delta


def salvar_delta(delta):
    try:
        os.makedirs(os.path.dirname(os.path.abspath(_CACHE_PATH)), exist_ok=True)
        with open(_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(delta, f, indent=2, ensure_ascii=False)
        logger.info(f"DEBUG_ASSINATURA | Delta salvo em {_CACHE_PATH}")
    except Exception as e:
        logger.info(f"DEBUG_ASSINATURA | Falha ao salvar delta: {e}")
