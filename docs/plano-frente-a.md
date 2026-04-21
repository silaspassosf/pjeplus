# Plano Frente A — Bug Fixes Críticos Selenium

## Overview

Corrigir 3 problemas de automação Selenium que causam falhas silenciosas no PJePlus. A1 é crítico (falso-positive garante que Angular nunca estabiliza corretamente). A2 e A3 são melhorias de alta ROI sobre infraestrutura de retry existente.

**Escopo:** 3 arquivos modificados, sem impacto em lógica de negócio, retrocompatível.

## Decisões de Arquitetura

- **A1 substitui** a implementação existente de `aguardar_angular_*` (alias retrocompatível garante zero quebra)
- **A2 acrescenta** ao final de `retry_logic.py` — `com_retry` existente não é alterado
- **A3 adiciona** função opt-in em `wait_operations.py` — `WebDriverWait` não é substituído globalmente

## Task List

---

### Phase 1: Correção Crítica Angular

## Task A1: Corrigir `Fix/utils_angular.py` para Angular 2+

**Descrição:** O código atual usa `angular.element(document).injector().$http.pendingRequests` — API do AngularJS 1.x que não existe no PJe (Angular 2+). Qualquer chamada a `aguardar_angular_carregar` ou `aguardar_angular_requests` retorna silenciosamente sem esperar nada. Substituir pela API `getAllAngularTestabilities()` que é a forma correta para Angular 2+.

**Acceptance criteria:**
- [ ] `Fix/utils_angular.py` contém `aguardar_angular_estavel(driver, timeout)` usando `execute_async_script` com `whenStable`
- [ ] `aguardar_angular_carregar` e `aguardar_angular_requests` são aliases para `aguardar_angular_estavel`
- [ ] Nenhum caller existente precisa ser alterado

**Verificação:**
```bash
py -m py_compile Fix/utils_angular.py
py -c "from Fix.utils_angular import aguardar_angular_carregar, aguardar_angular_requests, aguardar_angular_estavel; print('OK')"
```

**Dependências:** Nenhuma

**Arquivos:**
- `Fix/utils_angular.py`

**Escopo:** XS — 1 arquivo, substituição de implementação

**Implementação:**
```python
def aguardar_angular_estavel(driver, timeout: int = 10) -> None:
    """Aguarda Zone.js estabilizar (Angular 2+). Cobre XHR, setTimeout e animações."""
    driver.set_script_timeout(timeout + 2)
    driver.execute_async_script("""
        var cb = arguments[arguments.length - 1];
        var ts = window.getAllAngularTestabilities();
        if (!ts || ts.length === 0) { cb(); return; }
        ts[0].whenStable(cb);
    """)

# Aliases retrocompatíveis
aguardar_angular_carregar = aguardar_angular_estavel
aguardar_angular_requests = aguardar_angular_estavel
```

---

### Checkpoint: Após A1
- [ ] `py -m py_compile Fix/utils_angular.py` limpo
- [ ] Aliases importáveis sem erro
- [ ] Testar manualmente em 1 fluxo que usa `mat-select` (ex: comunicação judicial)

---

### Phase 2: Circuit Breaker

## Task A2: Adicionar `CircuitBreaker` em `Fix/selenium_base/retry_logic.py`

**Descrição:** `com_retry` já existe com backoff exponencial, mas não tem controle de estado: após N falhas consecutivas o script continua tentando indefinidamente. Adicionar `CircuitBreaker` como classe independente ao final do arquivo, com singletons pré-criados para os subsistemas mais críticos (SISBAJUD, PJe API).

**Acceptance criteria:**
- [ ] Classe `CircuitBreaker` com `failure_threshold` e `recovery_timeout` adicionada ao arquivo
- [ ] Após `failure_threshold` falhas consecutivas, próxima chamada lança `RuntimeError` imediatamente
- [ ] Após `recovery_timeout` segundos, circuito fecha automaticamente
- [ ] Singletons `cb_sisbajud` e `cb_pje_api` exportados
- [ ] `com_retry` existente não foi alterado

**Verificação:**
```bash
py -m py_compile Fix/selenium_base/retry_logic.py
py -c "from Fix.selenium_base.retry_logic import CircuitBreaker, cb_sisbajud, cb_pje_api; print('OK')"
# Smoke test lógico:
py -c "
from Fix.selenium_base.retry_logic import CircuitBreaker
cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
try:
    for _ in range(3):
        try: cb.call(lambda: (_ for _ in ()).throw(ValueError('falha')))
        except ValueError: pass
except RuntimeError as e:
    print('Circuit abriu corretamente:', e)
"
```

**Dependências:** Nenhuma (A1 é independente)

**Arquivos:**
- `Fix/selenium_base/retry_logic.py`

**Escopo:** S — 1 arquivo, acréscimo ao final

**Implementação a acrescentar ao final do arquivo:**
```python
import time as _time

class CircuitBreaker:
    """Abre o circuito após N falhas consecutivas; fecha após recovery_timeout segundos."""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self._failures = 0
        self._open_until = 0.0
        self.threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    @property
    def is_open(self) -> bool:
        return _time.time() < self._open_until

    def call(self, func, *args, **kwargs):
        if self.is_open:
            raise RuntimeError("CircuitBreaker OPEN — operação bloqueada temporariamente")
        try:
            result = func(*args, **kwargs)
            self._failures = 0
            return result
        except Exception:
            self._failures += 1
            if self._failures >= self.threshold:
                self._open_until = _time.time() + self.recovery_timeout
            raise

    def reset(self) -> None:
        """Força fechamento manual do circuito."""
        self._failures = 0
        self._open_until = 0.0

# Singletons por subsistema
cb_sisbajud = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
cb_pje_api  = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
```

**Uso nos módulos:**
```python
from Fix.selenium_base.retry_logic import cb_sisbajud
result = cb_sisbajud.call(funcao_sisbajud, driver, processo)
```

---

### Checkpoint: Após A2
- [ ] `py -m py_compile Fix/selenium_base/retry_logic.py` limpo
- [ ] Smoke test lógico do circuito passa
- [ ] `com_retry` ainda importável e sem alteração de assinatura

---

### Phase 3: MutationObserver Async

## Task A3: Adicionar `aguardar_mutacao_async` em `Fix/selenium_base/wait_operations.py`

**Descrição:** O padrão atual injeta MutationObserver e depois faz polling via `WebDriverWait`. Adicionar função opt-in que bloqueia o Python até o JS chamar o callback — eliminando overhead de polling para formulários Angular complexos. Não substitui `WebDriverWait` global.

**Acceptance criteria:**
- [ ] Função `aguardar_mutacao_async(driver, seletor, timeout)` adicionada ao arquivo
- [ ] Retorna `True` quando elemento aparece, sem polling do lado Python
- [ ] Se elemento já existe no DOM, retorna imediatamente
- [ ] `WebDriverWait` existente não foi alterado

**Verificação:**
```bash
py -m py_compile Fix/selenium_base/wait_operations.py
py -c "from Fix.selenium_base.wait_operations import aguardar_mutacao_async; print('OK')"
```

**Dependências:** Nenhuma (independente de A1 e A2)

**Arquivos:**
- `Fix/selenium_base/wait_operations.py`

**Escopo:** XS — 1 arquivo, nova função opt-in

**Implementação a acrescentar ao final do arquivo:**
```python
def aguardar_mutacao_async(driver, seletor: str, timeout: int = 10) -> bool:
    """Aguarda elemento via MutationObserver com callback — zero polling do lado Python.
    Usar seletivamente onde WebDriverWait causa inconsistência (formulários Angular com routing).
    """
    driver.set_script_timeout(timeout + 2)
    return driver.execute_async_script("""
        var sel = arguments[0], cb = arguments[arguments.length - 1];
        if (document.querySelector(sel)) { cb(true); return; }
        var obs = new MutationObserver(function() {
            if (document.querySelector(sel)) { obs.disconnect(); cb(true); }
        });
        obs.observe(document.body, {childList: true, subtree: true});
    """, seletor)
```

---

### Checkpoint Final: Frente A Completa
- [ ] `py -m py_compile Fix/utils_angular.py Fix/selenium_base/retry_logic.py Fix/selenium_base/wait_operations.py`
- [ ] Todos os 3 imports validados sem erro
- [ ] `py -c "import x"` limpo (nenhum import quebrado)
- [ ] Smoke test manual: fluxo com `mat-select` Angular usa `aguardar_angular_estavel` e não trava

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| `getAllAngularTestabilities()` não disponível em alguma página do PJe | Médio | Callback é chamado imediatamente quando `ts.length === 0` — comportamento seguro |
| `execute_async_script` com timeout silencioso no GeckoDriver | Baixo | `set_script_timeout(timeout + 2)` garante margem; testar em perfil Firefox real |
| `CircuitBreaker` aberto bloqueia fluxo inteiro | Médio | `reset()` disponível; singletons por subsistema isolam impacto |

## Questões Abertas

- `getAllAngularTestabilities()` está disponível no PJe em produção? Validar via console do browser antes do deploy de A1.
- Quais são os 2–3 fluxos com maior taxa de falha silenciosa hoje? Priorizar esses para usar `cb_sisbajud` primeiro.
