import json
import threading
import logging
import time
import os
from pathlib import Path
from typing import List, Optional

# Cache file at project root
import json
import threading
import logging
import time
from pathlib import Path
from selenium.common.exceptions import NoSuchElementException

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
    def __init__(self, driver):
        self.driver = driver
        self.cache = self._carregar_cache()
        self.lock = threading.Lock()
        
        # Dicionário para evitar repetir fallbacks pesados seguidos (Cooldown)
        # Formato: {'by_value': timestamp_da_ultima_falha}
        self._fallback_cooldown = {}

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
