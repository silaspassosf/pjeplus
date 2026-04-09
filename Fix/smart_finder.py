import json
import threading
import logging
import time
import os
from pathlib import Path
from typing import List, Optional
from selenium.common.exceptions import NoSuchElementException

# Cache file at project root

# ---------------------------------------------------------
# 1. Configurações Iniciais e de Ficheiros
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARQUIVO_CACHE = PROJECT_ROOT / 'aprendizado_seletores.json'
LEARN_LOG = PROJECT_ROOT / 'monitor_aprendizado.log'

# Isolamento do Logger de aprendizagem
learn_logger = logging.getLogger('monitor_aprendizado')
if not learn_logger.handlers:
    fh = logging.FileHandler(LEARN_LOG, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    learn_logger.addHandler(fh)
    learn_logger.setLevel(logging.INFO)


# ---------------------------------------------------------
# 2. Classe Principal Otimizada
# ---------------------------------------------------------
class SmartFinder:
    """
    Sistema inteligente de busca de seletores com cache e fallback.
    Otimizado para não causar lentidão no loop principal do orquestrador.
    """
    def __init__(self, driver=None):
        self.driver = driver
        self.cache = self._carregar_cache()
        self.lock = threading.Lock()
        
        # Dicionário para evitar repetir fallbacks pesados seguidos (Cooldown)
        # Formato: {'by_value': timestamp_da_ultima_falha}
        self._fallback_cooldown = {}

    def set_driver(self, driver):
        """Set driver post-construction for compatibility."""
        self.driver = driver

    def _is_frio(self, chave: str) -> bool:
        """Em chave `_frio_`, mantém o seletor estático e não substitui aprendizado automático."""
        return isinstance(chave, str) and chave.startswith('_frio_')

    # Compatibility wrapper: maintain legacy API `find(driver, key, candidates)`
    def find(self, driver, key: str, candidates: list):
        """Compatibility: try cache then candidates (css/xpath strings), return element or None."""
        cache_key = key
        # Try cache
        if cache_key in self.cache:
            val = self.cache[cache_key]
            if isinstance(val, (list, tuple)) and len(val) == 2:
                cached_by, cached_val = val
                try:
                    return driver.find_element(cached_by, cached_val)
                except Exception:
                    pass
            # Se inválido, ignora e continua para os candidatos

        # Try provided candidates
        for s in candidates:
            try:
                if s.strip().startswith('//'):
                    el = driver.find_element('xpath', s)
                else:
                    el = driver.find_element('css selector', s)

                # Save learned selector, exceto para chaves `_frio_` estáticas.
                if not self._is_frio(cache_key):
                    self._atualizar_cache(cache_key, 'css selector' if not s.strip().startswith('//') else 'xpath', s)
                return el
            except Exception:
                continue

        # Not found
        return None

    def _carregar_cache(self):
        """Lê o histórico de seletores já aprendidos do disco."""
        try:
            if ARQUIVO_CACHE.exists():
                return json.loads(ARQUIVO_CACHE.read_text(encoding='utf-8'))
        except Exception as e:
            learn_logger.error(f"Erro ao carregar cache: {e}")
        return {}

    def _salvar_cache(self):
        """
        Guarda o cache no ficheiro em segundo plano (Thread).
        Isso impede que a operação de Input/Output atrase a automação principal.
        """
        def gravar():
            with self.lock:
                try:
                    ARQUIVO_CACHE.write_text(json.dumps(self.cache, indent=2, ensure_ascii=False), encoding='utf-8')
                except Exception as e:
                    learn_logger.error(f"Erro ao salvar cache: {e}")
        
        threading.Thread(target=gravar, daemon=True).start()

    def find_element(self, by, value, enable_fallback=True):
        """
        Busca o elemento na página. 
        Se enable_fallback for False, não executa a busca pesada. Ideal para loops de espera (waits).
        """
        chave_cache = f"{by}_{value}"

        # PASSO A: Tentativa Rápida - Usar o Cache aprendido anteriormente
        if chave_cache in self.cache:
            cached_by, cached_val = self.cache[chave_cache]
            try:
                el = self.driver.find_element(cached_by, cached_val)
                return el, cached_val
            except NoSuchElementException:
                pass

        # PASSO B: Tentativa Normal - Usar o seletor original
        try:
            el = self.driver.find_element(by, value)
            
            # Se encontrou e não estava no cache, guardamos para ser instantâneo da próxima vez
            if chave_cache not in self.cache:
                self._atualizar_cache(chave_cache, by, value)
            return el, value
        except NoSuchElementException:
            pass

        # PASSO C: Proteções de Desempenho
        # 1. Se estamos num loop rápido de sondagem, devolvemos None sem travar.
        if not enable_fallback:
            return None, None
            
        agora = time.time()
        # 2. Cooldown: Se falhou há menos de 5 segundos, não repete a pesquisa profunda.
        if chave_cache in self._fallback_cooldown and (agora - self._fallback_cooldown[chave_cache] < 5):
            return None, None

        # PASSO D: Fallback Heurístico (Busca Pesada)
        learn_logger.info(f"Iniciando fallback heuristico para: {value}")
        el, novo_by, novo_valor = self._gerar_e_testar_candidatos(value)

        if el:
            learn_logger.info(f"FALLBACK_FOUND {chave_cache} -> {novo_by}={novo_valor}")
            self._atualizar_cache(chave_cache, novo_by, novo_valor)
            return el, novo_valor
        else:
            # Regista a falha no cooldown para não encravar os próximos 5 segundos
            self._fallback_cooldown[chave_cache] = agora
            return None, None

    def _atualizar_cache(self, chave, by, value):
        """Atualiza a memória RAM e chama a gravação assíncrona."""
        with self.lock:
            if self._is_frio(chave) and chave in self.cache and self.cache[chave] != (by, value):
                learn_logger.info(f"Ignorar atualização de seletor frio: {chave}")
                return
            self.cache[chave] = (by, value)
        self._salvar_cache()

    def _gerar_e_testar_candidatos(self, original_value):
        """
        Gera hipóteses inteligentes de seletores para encontrar o elemento perdido.
        """
        candidates = []
        safe = original_value.replace('"', "'")

        # HEURÍSTICA DE PROTEÇÃO: 
        # Se o seletor parece estrutural (ex: classes do Angular Material), 
        # NÃO procurar por texto (normalize-space), pois isso gera falsos positivos.
        if "mat-" not in safe and "container" not in safe:
            candidates.append(('xpath', f"//a[contains(normalize-space(.), \"{safe}\")]"))
            candidates.append(('xpath', f"//button[contains(normalize-space(.), \"{safe}\")]"))
            candidates.append(('xpath', f"//input[@placeholder=\"{safe}\"]"))
            candidates.append(('xpath', f"//label[contains(normalize-space(.), \"{safe}\")]//following::input[1]"))

        # Atributos específicos e frequentes no PJe
        pje_attrs = ['mattooltip', 'aria-label', 'placeholder', 'name', 'title']
        for attr in pje_attrs:
            candidates.append(('css selector', f'*[{attr}*="{safe}"]'))
            candidates.append(('css selector', f'button[{attr}*="{safe}"]'))
            candidates.append(('css selector', f'input[{attr}*="{safe}"]'))
            candidates.append(('css selector', f'img[{attr}*="{safe}"]'))

        # Testar candidatos de forma limpa
        vistos = set()
        for c_by, c_val in candidates:
            if c_val in vistos:
                continue
            vistos.add(c_val)
            
            try:
                el = self.driver.find_element(c_by, c_val)
                # Só assume que encontrou se o elemento estiver visível no ecrã
                if el.is_displayed():
                    return el, c_by, c_val
            except Exception:
                continue

        return None, None, None


def injetar_smart_finder_global(driver):
    """Backward-compatible shim: wrap driver.find_element e find_elements.

    Behavior:
    - find_element: tenta original, se falhar tenta cache rápido, depois dispara
      fallback em background e re-levanta a exceção original.
    - find_elements: tenta original; se retornar lista vazia E o seletor estiver
      em cache como chave conhecida, retenta com o seletor do cache.
      Isso cobre chamadas do WebDriverWait (EC.element_to_be_clickable etc.)
    """
    try:
        original_find = driver.find_element
        original_find_elements = driver.find_elements
    except Exception:
        original_find = None
        original_find_elements = None

    sf = SmartFinder(driver)

    def smart_find_element(by, value):
        try:
            return original_find(by, value)
        except Exception as orig_exc:
            try:
                el, _ = sf.find_element(by, value, enable_fallback=False)
                if el:
                    return el
            except Exception:
                pass

            def _bg():
                try:
                    sf.find_element(by, value, enable_fallback=True)
                except Exception:
                    pass

            try:
                t = threading.Thread(target=_bg, daemon=True)
                t.start()
            except Exception:
                learn_logger.exception('FALLBACK_THREAD_ERROR_SHIM')

            raise orig_exc

    def smart_find_elements(by, value):
        """Intercepta find_elements para cobrir WebDriverWait/EC.*."""
        result = original_find_elements(by, value)
        if result:
            return result

        # Lista vazia: verificar se há seletor aprendido em cache
        chave_cache = f"{by}_{value}"
        cached = sf.cache.get(chave_cache)
        if cached:
            cached_by, cached_val = cached
            if (cached_by, cached_val) != (by, value):
                try:
                    alt = original_find_elements(cached_by, cached_val)
                    if alt:
                        learn_logger.info(f"find_elements cache-hit: {chave_cache} -> {cached_val}")
                        return alt
                except Exception:
                    pass

        return result  # lista vazia original

    driver.find_element = smart_find_element
    driver.find_elements = smart_find_elements
    setattr(driver, 'smart_finder', sf)
    learn_logger.info('Smart Finder shim injected on driver')


# ---------------------------------------------------------------------------
# Singleton de módulo — instância compartilhada com cache carregado uma vez
# ---------------------------------------------------------------------------
_singleton: 'SmartFinder | None' = None


def _get_singleton() -> 'SmartFinder':
    """Retorna (ou cria) a instância global do SmartFinder sem driver."""
    global _singleton
    if _singleton is None:
        _singleton = SmartFinder()
    return _singleton


def buscar(driver, chave: str, candidatos: list):
    """
    Função universal de busca de elementos com cache automático.

    Uso em qualquer módulo:
        from Fix.smart_finder import buscar
        el = buscar(driver, 'btn_salvar', ['.salvar-btn', '//button[@aria-label="Salvar"]'])

    Parâmetros:
        driver     — WebDriver ativo
        chave      — identificador único para o cache (snake_case descritivo)
        candidatos — lista de seletores CSS ou XPath (// = xpath, demais = css)

    Retorna o WebElement ou None se não encontrado.
    Log de aprendizado vai para monitor_aprendizado.log (separado do log principal).
    """
    sf = _get_singleton()
    sf.set_driver(driver)
    return sf.find(driver, chave, candidatos)


__all__ = ['SmartFinder', 'injetar_smart_finder_global', 'buscar']
