# Fechar Gaps Técnicos em Fix/ (a partir de funcoes.md)

## Problem Statement
Como fechar os 5 gaps entre a prática atual de automação Selenium no PJePlus e o estado da arte em 2025, integrando cada melhoria na arquitetura `Fix/` que já existe sem reescrever o que já funciona?

## O que o código real revela (não estava em funcoes.md)

Antes de recomendar qualquer direção: três dos cinco gaps têm uma surpresa no estado real do código:

- `Fix/utils_angular.py` → usa **AngularJS 1.x API** (`angular.element(document).injector().$http.pendingRequests`). O PJe é Angular **2+** (Zone.js). Isso significa que `aguardar_angular_carregar` e `aguardar_angular_requests` **não funcionam** no PJe e dão false-positive silencioso. É o bug mais crítico do lote.
- `Fix/selenium_base/retry_logic.py` → já tem `com_retry` com backoff exponencial — o Circuit Breaker é uma **extensão** de 30-50 linhas, não uma reescrita.
- `Fix/selenium_base/wait_operations.py` → usa `WebDriverWait` com polling de 500ms — a troca por `execute_async_script` elimina I/O de rede redundante mas não é transparente (quebra a assinatura pública).

## Recommended Direction

**Implementar os 3 gaps de alta ROI na ordem abaixo. Ignorar os outros 2 por agora.**

### 1. Angular Testability — crítico, simples (1 arquivo, 40 linhas)

Reescrever `Fix/utils_angular.py` — **não adicionar, substituir** o comportamento existente:

```python
def aguardar_angular_estavel(driver, timeout=10):
    """Aguarda Zone.js estabilizar (Angular 2+). Substitui aguardar_angular_carregar."""
    driver.set_script_timeout(timeout + 2)
    driver.execute_async_script("""
        var cb = arguments[arguments.length - 1];
        var ts = window.getAllAngularTestabilities();
        if (!ts || ts.length === 0) { cb(); return; }
        ts[0].whenStable(cb);
    """)
```

O `whenStable` cobre `setTimeout`, `XHR`, `Promises` e animações — tudo que `MutationObserver` ou `$http` não cobrem. Alias retrocompatível: `aguardar_angular_carregar = aguardar_angular_estavel`.

### 2. Circuit Breaker — alto impacto, médio esforço (estende retry_logic.py)

`com_retry` já existe com backoff exponencial. Adicionar estado de circuito **aberto/fechado** como wrapper simples:

```python
# Fix/selenium_base/retry_logic.py — acrescentar ao final
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self._failures = 0
        self._open_until = 0
        self.threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    def call(self, func, *args, **kwargs):
        import time
        if time.time() < self._open_until:
            raise RuntimeError("CircuitBreaker OPEN — operação bloqueada temporariamente")
        try:
            result = func(*args, **kwargs)
            self._failures = 0
            return result
        except Exception as e:
            self._failures += 1
            if self._failures >= self.threshold:
                self._open_until = time.time() + self.recovery_timeout
                logger.error(f"CircuitBreaker ABERTO após {self._failures} falhas")
            raise

# Singleton por operação — uso:
_cb_sisbajud = CircuitBreaker(failure_threshold=5)
```

Manter retrocompatível com `com_retry` sem nenhuma mudança de assinatura.

### 3. execute_async_script para observers — médio impacto, médio esforço

**Não substituir** `WebDriverWait` globalmente — ele é correto para a maioria dos casos. Criar uma função complementar opcional em `wait_operations.py`:

```python
def aguardar_mutacao_async(driver, seletor, timeout=10):
    """Alternativa a aguardar_renderizacao_nativa: blocking nativo, zero polling."""
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

Usar seletivamente onde o polling de 500ms causa inconsistência (formulários `mat-select` encadeados + Angular routing).

## Key Assumptions to Validate
- [ ] `getAllAngularTestabilities()` está disponível no PJe em produção — testar via `py -c "..."` ou console do browser. (É Angular 2+?)
- [ ] `com_retry` é a única camada de retry usada nos módulos críticos (`SISB`, `Prazo`, `PEC`) — ou existem loops manuais adicionais que precisam de CircuitBreaker também?
- [ ] `execute_async_script` não sofre timeout silencioso no perfil Firefox com extensões do PJePlus ativos.

## MVP Scope

Implementar nesta ordem, um de cada vez:

1. **`aguardar_angular_estavel`** em `Fix/utils_angular.py` — reescrever função + alias + testes manuais em 2 fluxos que usam `mat-select`.
2. **`CircuitBreaker`** em `Fix/selenium_base/retry_logic.py` — acrescentar classe + singleton para SISBAJUD (módulo mais crítico).
3. **`aguardar_mutacao_async`** em `Fix/selenium_base/wait_operations.py` — nova função opt-in, sem tocar nas existentes.

**Estimativa:** Gap 1 = 1h, Gap 2 = 2h, Gap 3 = 1h.

## Not Doing (e por quê)
- **Page Object formal** — `SmartFinder` já existe. Formalizar a regra "sem seletores fora de `Fix/`" é uma revisão de código, não uma feature. Não merece uma task agora; vai junto com a reorganização de `Fix/`.
- **GitHub Actions headless** — depende de decisão de infraestrutura (cloud vs local). Não bloqueia nada hoje. Adiar até que a migração cloud seja timebox.
- **Substituição global de WebDriverWait** — quebraria API pública sem ganho correspondente. Opt-in localizado é a escolha certa.

## Open Questions
- `getAllAngularTestabilities()` funciona no PJe atual? (Validar antes de implementar Gap 1.)
- Quais são os 2-3 fluxos com maior taxa de falha silenciosa hoje? (Para priorizar quais usar CircuitBreaker primeiro.)
- O timeout de `execute_async_script` no GeckoDriver replica o `set_script_timeout` do driver ou é independente?

---
*Gerado em 13/04/2026 — baseado em leitura real de `Fix/utils_angular.py`, `Fix/selenium_base/retry_logic.py`, `Fix/selenium_base/wait_operations.py` e análise de `funcoes.md`.*
