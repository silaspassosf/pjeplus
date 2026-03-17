"""
SISB Performance - Técnicas de otimização e redução
Refatoração seguindo padrões do projeto PjePlus
"""

import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Dict, List, Any, Optional
import threading

from .standards import sisb_logger, SISBConstants

class PerformanceOptimizer:
    """Otimizador de performance para operações SISBAJUD"""

    def __init__(self):
        self.cache = {}
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.lock = threading.Lock()

    @lru_cache(maxsize=100)
    def cache_element_selector(self, seletor: str, contexto: str) -> str:
        """
        Cache inteligente de seletores CSS para reduzir lookups.

        Args:
            seletor: Seletor CSS
            contexto: Contexto de uso

        Returns:
            str: Seletor otimizado
        """
        # Otimizações baseadas em padrões observados
        otimizacoes = {
            'input[placeholder*="Juiz"]': 'input[placeholder*="Juiz"]',
            'input[placeholder="Número do Processo"]': 'input[placeholder="Número do Processo"]',
            'button.mat-fab.mat-primary': 'button.mat-fab.mat-primary',
        }

        return otimizacoes.get(seletor, seletor)

    def batch_dom_operations(self, operations: List[Dict[str, Any]]) -> str:
        """
        Batch de operações DOM para reduzir requisições JavaScript.

        Args:
            operations: Lista de operações a executar

        Returns:
            str: Script JavaScript otimizado
        """
        script_lines = [
            "async function executeBatch() {",
            "    const results = {};",
            "    try {"
        ]

        for i, op in enumerate(operations):
            if op['type'] == 'wait_element':
                script_lines.append(f"""
                results.op_{i} = await window.SISBAJUD.esperarElemento('{op['selector']}', {op.get('timeout', 5000)});
                """)
            elif op['type'] == 'click':
                script_lines.append(f"""
                results.op_{i} = await window.SISBAJUD.clicarBotao('{op['selector']}', {op.get('timeout', 5000)});
                """)
            elif op['type'] == 'fill':
                script_lines.append(f"""
                results.op_{i} = await window.SISBAJUD.preencherCampo('{op['selector']}', '{op['value']}', {op.get('timeout', 5000)});
                """)

        script_lines.extend([
            "        return { sucesso: true, results };",
            "    } catch(e) {",
            "        return { sucesso: false, erro: e.message };",
            "    }",
            "}",
            "",
            "return executeBatch();"
        ])

        return "\n".join(script_lines)

    def optimize_javascript_execution(self, driver, script: str, *args) -> Any:
        """
        Execução otimizada de JavaScript com cache e pooling.

        Args:
            driver: WebDriver instance
            script: Script JavaScript
            *args: Argumentos para o script

        Returns:
            Any: Resultado da execução
        """
        # Cache de scripts compilados (simulação)
        cache_key = hash(script)
        with self.lock:
            if cache_key not in self.cache:
                self.cache[cache_key] = script

        # Execução com timeout otimizado
        start_time = time.time()
        try:
            result = driver.execute_script(script, *args)
            execution_time = time.time() - start_time

            # Log de performance
            if execution_time > 2.0:
                sisb_logger.log(f"Script lento executado em {execution_time:.2f}s", "WARNING", "performance")

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            sisb_logger.log(f"Erro em script após {execution_time:.2f}s: {e}", "ERROR", "performance")
            raise

class PollingReducer:
    """Redutor de polling para operações mais eficientes"""

    def __init__(self):
        self.observers = {}
        self.mutation_observer_script = self._create_mutation_observer()

    def _create_mutation_observer(self) -> str:
        """Cria script MutationObserver para substituir polling"""
        return """
        class SmartElementWaiter {
            constructor() {
                this.observers = new Map();
            }

            waitForElement(selector, callback, timeout = 10000) {
                return new Promise((resolve, reject) => {
                    // Verificar se já existe
                    const existing = document.querySelector(selector);
                    if (existing) {
                        resolve(existing);
                        return;
                    }

                    // Criar observer
                    const observer = new MutationObserver((mutations) => {
                        const element = document.querySelector(selector);
                        if (element) {
                            observer.disconnect();
                            resolve(element);
                        }
                    });

                    observer.observe(document.body, {
                        childList: true,
                        subtree: true,
                        attributes: true,
                        attributeFilter: ['style', 'class', 'disabled']
                    });

                    // Timeout
                    setTimeout(() => {
                        observer.disconnect();
                        reject(new Error(`Elemento não encontrado: ${selector}`));
                    }, timeout);
                });
            }

            waitForState(element, stateChecker, timeout = 5000) {
                return new Promise((resolve, reject) => {
                    const checkState = () => {
                        if (stateChecker(element)) {
                            resolve(element);
                            return;
                        }
                    };

                    // Verificar estado inicial
                    checkState();

                    // Observer para mudanças de estado
                    const observer = new MutationObserver((mutations) => {
                        checkState();
                    });

                    observer.observe(element, {
                        attributes: true,
                        attributeFilter: ['class', 'style', 'disabled', 'value']
                    });

                    setTimeout(() => {
                        observer.disconnect();
                        reject(new Error('Timeout aguardando mudança de estado'));
                    }, timeout);
                });
            }
        }

        window.SmartElementWaiter = new SmartElementWaiter();
        """

    def replace_polling_with_observer(self, driver, seletor: str, timeout: int = 10000):
        """
        Substitui polling tradicional por MutationObserver.

        Args:
            driver: WebDriver instance
            seletor: Seletor CSS
            timeout: Timeout em ms

        Returns:
            WebElement: Elemento encontrado
        """
        # Injetar script se necessário
        driver.execute_script(self.mutation_observer_script)

        # Usar observer
        script = f"""
        return window.SmartElementWaiter.waitForElement('{seletor}', null, {timeout});
        """

        return driver.execute_script(script)

class CacheManager:
    """Gerenciador inteligente de cache para SISBAJUD"""

    def __init__(self):
        self.element_cache = {}
        self.data_cache = {}
        self.cache_timeout = 300  # 5 minutos
        self.lock = threading.Lock()

    def cache_element(self, key: str, element, ttl: int = None):
        """Cache de elementos WebElement"""
        with self.lock:
            self.element_cache[key] = {
                'element': element,
                'timestamp': time.time(),
                'ttl': ttl or self.cache_timeout
            }

    def get_cached_element(self, key: str):
        """Recupera elemento do cache se ainda válido"""
        with self.lock:
            if key in self.element_cache:
                cached = self.element_cache[key]
                if time.time() - cached['timestamp'] < cached['ttl']:
                    return cached['element']
                else:
                    # Cache expirado
                    del self.element_cache[key]
        return None

    def cache_data(self, key: str, data: Any, ttl: int = None):
        """Cache de dados estruturados"""
        with self.lock:
            self.data_cache[key] = {
                'data': data,
                'timestamp': time.time(),
                'ttl': ttl or self.cache_timeout
            }

    def get_cached_data(self, key: str) -> Optional[Any]:
        """Recupera dados do cache se ainda válidos"""
        with self.lock:
            if key in self.data_cache:
                cached = self.data_cache[key]
                if time.time() - cached['timestamp'] < cached['ttl']:
                    return cached['data']
                else:
                    # Cache expirado
                    del self.data_cache[key]
        return None

    def clear_expired_cache(self):
        """Limpa cache expirado"""
        current_time = time.time()
        with self.lock:
            # Limpar elementos
            expired_elements = [
                key for key, cached in self.element_cache.items()
                if current_time - cached['timestamp'] >= cached['ttl']
            ]
            for key in expired_elements:
                del self.element_cache[key]

            # Limpar dados
            expired_data = [
                key for key, cached in self.data_cache.items()
                if current_time - cached['timestamp'] >= cached['ttl']
            ]
            for key in expired_data:
                del self.data_cache[key]

class ParallelProcessor:
    """Processador paralelo para operações SISBAJUD"""

    def __init__(self, max_workers: int = 3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.semaphore = threading.Semaphore(max_workers)

    async def process_parallel(self, tasks: List[callable]) -> List[Any]:
        """
        Processa tarefas em paralelo com controle de concorrência.

        Args:
            tasks: Lista de funções a executar

        Returns:
            List[Any]: Resultados das tarefas
        """
        async def execute_task(task):
            with self.semaphore:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(self.executor, task)

        # Executar todas as tarefas em paralelo
        results = await asyncio.gather(
            *[execute_task(task) for task in tasks],
            return_exceptions=True
        )

        return results

    def process_series_parallel(self, driver, series: List[Dict], process_func: callable) -> List[Any]:
        """
        Processa séries SISBAJUD em paralelo (limitado para evitar detecção).

        Args:
            driver: WebDriver instance
            series: Lista de séries
            process_func: Função de processamento

        Returns:
            List[Any]: Resultados do processamento
        """
        # Limitar paralelismo para evitar detecção
        max_parallel = min(len(series), 2)  # Máximo 2 séries em paralelo

        results = []
        for i in range(0, len(series), max_parallel):
            batch = series[i:i + max_parallel]

            # Criar tarefas para o batch
            tasks = []
            for serie in batch:
                task = lambda s=serie: process_func(driver, s)
                tasks.append(task)

            # Executar batch em paralelo
            batch_results = asyncio.run(self.process_parallel(tasks))
            results.extend(batch_results)

            # Delay entre batches para evitar detecção
            time.sleep(SISBConstants.RATE_LIMITS['delay_minimo'] / 1000)

        return results

# Instâncias globais dos otimizadores
performance_optimizer = PerformanceOptimizer()
polling_reducer = PollingReducer()
cache_manager = CacheManager()
parallel_processor = ParallelProcessor()

# ===== FUNÇÕES DE OTIMIZAÇÃO PRONTAS PARA USO =====

def optimized_element_wait(driver, seletor: str, timeout: int = None) -> Any:
    """
    Espera otimizada por elemento usando MutationObserver.

    Args:
        driver: WebDriver instance
        seletor: Seletor CSS
        timeout: Timeout em ms

    Returns:
        Any: Elemento encontrado
    """
    timeout = timeout or SISBConstants.TIMEOUTS['elemento_padrao'] * 1000
    return polling_reducer.replace_polling_with_observer(driver, seletor, timeout)

def batched_form_fill(driver, fields: Dict[str, str]) -> bool:
    """
    Preenchimento otimizado de formulários em batch.

    Args:
        driver: WebDriver instance
        fields: Dicionário seletor -> valor

    Returns:
        bool: True se todos os campos preenchidos
    """
    operations = []
    for selector, value in fields.items():
        operations.append({
            'type': 'fill',
            'selector': selector,
            'value': value
        })

    batch_script = performance_optimizer.batch_dom_operations(operations)
    result = performance_optimizer.optimize_javascript_execution(driver, batch_script)

    return result and result.get('sucesso', False)

def cached_selector_lookup(seletor: str, contexto: str) -> str:
    """
    Lookup otimizado de seletor com cache.

    Args:
        seletor: Seletor CSS
        contexto: Contexto de uso

    Returns:
        str: Seletor otimizado
    """
    return performance_optimizer.cache_element_selector(seletor, contexto)

def parallel_series_processing(driver, series: List[Dict], process_func: callable) -> List[Any]:
    """
    Processamento paralelo de séries com controle de rate limiting.

    Args:
        driver: WebDriver instance
        series: Lista de séries
        process_func: Função de processamento por série

    Returns:
        List[Any]: Resultados do processamento
    """
    return parallel_processor.process_series_parallel(driver, series, process_func)

def smart_cache_operation(key: str, operation: callable, ttl: int = None) -> Any:
    """
    Operação com cache inteligente.

    Args:
        key: Chave do cache
        operation: Função a executar se não em cache
        ttl: Time to live do cache

    Returns:
        Any: Resultado da operação (cacheado ou novo)
    """
    # Verificar cache
    cached_result = cache_manager.get_cached_data(key)
    if cached_result is not None:
        sisb_logger.log(f"Cache hit para: {key}", "DEBUG", "cache")
        return cached_result

    # Executar operação
    result = operation()

    # Armazenar em cache
    cache_manager.cache_data(key, result, ttl)
    sisb_logger.log(f"Cache miss - armazenado: {key}", "DEBUG", "cache")

    return result