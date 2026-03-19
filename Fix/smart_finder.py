import json
import threading
import logging
from pathlib import Path
from typing import List, Optional

# Cache file at project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARQUIVO_CACHE = PROJECT_ROOT / 'aprendizado_seletores.json'
LEARN_LOG = PROJECT_ROOT / 'monitor_aprendizado.log'

# Learning logger (isolated)
learn_logger = logging.getLogger('monitor_aprendizado')
if not learn_logger.handlers:
    fh = logging.FileHandler(LEARN_LOG, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    learn_logger.addHandler(fh)
    learn_logger.setLevel(logging.INFO)


def carregar_cache():
    try:
        if ARQUIVO_CACHE.exists():
            return json.loads(ARQUIVO_CACHE.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {}


def salvar_cache(cache: dict):
    try:
        ARQUIVO_CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception:
        learn_logger.exception('ERRO_SALVAR_CACHE')


class SmartFinder:
    """Cache-backed selector finder with background updates and isolated learning log."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cache = carregar_cache()

    def _save_cache_bg(self, key: str, selector: str):
        def _save():
            with self._lock:
                self._cache[key] = selector
                try:
                    salvar_cache(self._cache)
                    learn_logger.info('CACHE_UPDATE %s -> %s', key, selector)
                except Exception:
                    learn_logger.exception('CACHE_SAVE_ERROR')

        t = threading.Thread(target=_save, daemon=True)
        t.start()

    def find(self, driver, key: str, candidates: List[str]):
        """Try cache first, then candidates; update cache on success."""
        cached = self._cache.get(key)
        try:
            if cached:
                if cached.strip().startswith('//'):
                    return driver.find_element('xpath', cached)
                return driver.find_element('css selector', cached)
        except Exception:
            pass

        for s in candidates:
            try:
                if s.strip().startswith('//'):
                    el = driver.find_element('xpath', s)
                else:
                    el = driver.find_element('css selector', s)
                try:
                    self._save_cache_bg(key, s)
                except Exception:
                    pass
                return el
            except Exception:
                continue

        learn_logger.info('NOT_FOUND %s candidates=%d', key, len(candidates))
        return None


def injetar_smart_finder_global(driver):
    """Replace driver.find_element with a smart wrapper using SmartFinder."""
    original_find_element = driver.find_element
    sf = SmartFinder()

    def smart_find_element(by, value):
        cache = carregar_cache()
        chave_busca = f"{by}_{value}"

        # 1. Try cache
        if chave_busca in cache:
            try:
                return original_find_element(by, cache[chave_busca])
            except Exception:
                pass

        # 2. Try original
        try:
            return original_find_element(by, value)
        except Exception:
            # 3. Fallback heuristics
            try:
                elemento, novo_seletor = _tentar_encontrar_fallback(driver, contexto_ou_valor_antigo=value)
                if elemento and novo_seletor:
                    learn_logger.info('FALLBACK_FOUND %s -> %s', chave_busca, novo_seletor)
                    cache[chave_busca] = novo_seletor
                    salvar_cache(cache)
                    return elemento
            except Exception:
                learn_logger.exception('FALLBACK_ERROR')
            raise

    driver.find_element = smart_find_element
    learn_logger.info('Smart Finder ativado no driver')


def _tentar_encontrar_fallback(driver, contexto_ou_valor_antigo=None):
    """Embedded heuristic fallback — returns (element, selector) or (None, None)."""
    from selenium.common.exceptions import NoSuchElementException
    orig = contexto_ou_valor_antigo or ''
    orig_text = str(orig).strip()

    candidates = []
    if orig_text:
        candidates.append(orig_text)
        safe = orig_text.replace('"', '\\"')
        candidates.append(f"//*[contains(normalize-space(.), \"{safe}\")]")
        candidates.append(f"//button[contains(normalize-space(.), \"{safe}\")]")
        candidates.append(f"//a[contains(normalize-space(.), \"{safe}\")]")
        candidates.append(f"//input[@placeholder=\"{safe}\"]")
        candidates.append(f"//label[contains(normalize-space(.), \"{safe}\")]//following::input[1]")

        # PJe-aware attribute heuristics: match Angular Material and accessibility attributes
        pje_attrs = ['mattooltip', 'aria-label', 'placeholder', 'name', 'title']
        for attr in pje_attrs:
            candidates.append(f'*[{attr}*="{safe}"]')
            candidates.append(f'button[{attr}*="{safe}"]')
            candidates.append(f'input[{attr}*="{safe}"]')
            candidates.append(f'img[{attr}*="{safe}"]')
    candidates.extend([
        "button",
        "input[type=submit]",
        "a[role=button]",
    ])

    seen = set()
    for s in candidates:
        if not s or s in seen:
            continue
        seen.add(s)
        try:
            if s.strip().startswith('//'):
                el = driver.find_element('xpath', s)
            else:
                el = driver.find_element('css selector', s)
            return el, s
        except NoSuchElementException:
            continue
        except Exception:
            continue

    return None, None


__all__ = ['SmartFinder', 'injetar_smart_finder_global']
