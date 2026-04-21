# Plano de Implementação — PJePlus Otimização
> Consolidação de `docs/ideas/` · Atualizado em 17/04/2026

---

## Resumo Executivo

Três frentes de trabalho, em ordem de impacto:

| Frente | Ganho | Esforço | Status |
|--------|-------|---------|--------|
| A — Fix bugs críticos Selenium | Menos falhas silenciosas | 1–2 h | **Pendente** |
| B — Consolidar `Fix/` (89 → 18 arquivos) | -78% arquivos, imports limpos | ~8 h | **Pendente** |
| C — Limpar código morto restante | Menor superfície de manutenção | ~2 h | 🔄 Em andamento |

---

## Frente A — Bug Crítico + Melhorias Selenium

### A1 — Corrigir `Fix/utils_angular.py` (CRÍTICO)

**Problema:** o código atual usa `angular.element(document).injector().$http.pendingRequests` — API do AngularJS 1.x que **não existe** no PJe (Angular 2+). Resulta em falso-positive silencioso.

**Implementação — substituir função em `Fix/utils_angular.py`:**

```python
def aguardar_angular_estavel(driver, timeout: int = 10) -> None:
    """Aguarda Zone.js estabilizar (Angular 2+). Cobre XHR, setTimeout, animações."""
    driver.set_script_timeout(timeout + 2)
    driver.execute_async_script("""
        var cb = arguments[arguments.length - 1];
        var ts = window.getAllAngularTestabilities();
        if (!ts || ts.length === 0) { cb(); return; }
        ts[0].whenStable(cb);
    """)

# Alias retrocompatível — não quebra callers existentes
aguardar_angular_carregar = aguardar_angular_estavel
aguardar_angular_requests = aguardar_angular_estavel
```

**Validar antes de fazer o merge de Fix/:**
```bash
py -c "from Fix.utils_angular import aguardar_angular_estavel; print('OK')"
```

**Quando usar:** após navegações de rota Angular e submissões de formulário com `mat-select` encadeados.

---

### A2 — Circuit Breaker em `Fix/selenium_base/retry_logic.py`

**Problema:** loops de retry manuais espalhados por SISB, Prazo, PEC sem controle centralizado de falhas em cascata.

**Implementação — acrescentar ao final de `retry_logic.py`:**

```python
import time as _time

class CircuitBreaker:
    """Abre o circuito após N falhas consecutivas; reabre após recovery_timeout segundos."""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self._failures = 0
        self._open_until = 0.0
        self.threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    def call(self, func, *args, **kwargs):
        if _time.time() < self._open_until:
            raise RuntimeError("CircuitBreaker OPEN — operação bloqueada temporariamente")
        try:
            result = func(*args, **kwargs)
            self._failures = 0
            return result
        except Exception as e:
            self._failures += 1
            if self._failures >= self.threshold:
                self._open_until = _time.time() + self.recovery_timeout
            raise

# Singletons por subsistema — instanciar nos módulos que precisam
cb_sisbajud = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
cb_pje_api  = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
```

**Uso nos módulos:**
```python
from Fix.selenium_base.retry_logic import cb_sisbajud
result = cb_sisbajud.call(funcao_sisbajud, driver, processo)
```

---

### A3 — `aguardar_mutacao_async` em `Fix/selenium_base/wait_operations.py`

**Problema:** `WebDriverWait` com polling de 500ms cria overhead de rede redundante em formulários complexos.

**Implementação — nova função opt-in (não substitui WebDriverWait global):**

```python
def aguardar_mutacao_async(driver, seletor: str, timeout: int = 10) -> bool:
    """Aguarda elemento via MutationObserver com callback — zero polling."""
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

**Usar seletivamente** — apenas onde polling causa inconsistência (formulários Angular com routing).

---

## Frente B — Consolidar `Fix/` (89 → 18 arquivos)

### Estado Atual
- **89 arquivos Python**, ~16.5k linhas
- 12 subpacotes: `selenium_base/`, `drivers/`, `session/`, `navigation/`, `documents/`, `extraction/`, `progress/`, `gigs/`, `forms/`, `scripts/`, `legacy/`
- 9 stubs (só re-exportam, sem lógica)

### Estrutura Final Alvo (18 arquivos)

```
Fix/
├── __init__.py          # API pública re-exports              (~250 l)
├── core.py              # Core facade + debug + abas + headless + forms (~2.300 l)
├── log.py               # Log + exceptions + log_cleaner      (~676 l)
├── extracao.py          # Extração + BNDT + gigs              (~1.700 l)
├── extraction.py        # Indexação de processos              (~700 l)
├── progress.py          # Progresso unificado                 (~800 l)
├── drivers.py           # Driver lifecycle + paths + login    (~1.000 l)
├── session.py           # Cookies + auth                      (~730 l)
├── navigation.py        # Filtros + sigilo + navegação        (~635 l)
├── documents.py         # Busca de documentos                 (~770 l)
├── variaveis.py         # Variáveis completo                  (~1.056 l)
├── utils.py             # Formatting/sleep/error/collect      (~900 l)
├── utils_editor.py      # Editor + collect + timeline         (~650 l)
├── selectors.py         # Selectors + angular + smart_finder  (~550 l)
├── selenium.py          # selenium_base core ops              (~1.200 l)
├── selenium_wait.py     # selenium_base wait/retry/click      (~800 l)
├── selenium_select.py   # selenium_base selection/robust      (~670 l)
└── js_helpers.py        # JS helpers + scripts                (~115 l)
```

### Mapa de Merge por Grupo

| Destino | Fontes a Mergear |
|---------|-----------------|
| `core.py` | `core.py`, `otimizacao_wrapper.py`, `debug_interativo.py`, `debug_assinatura.py`, `assinatura_cookies.py`, `movimento_helpers.py`, `infojud.py`, `timeline.py`, `native_host.py`, `abas.py`, `headless_helpers.py`, `forms/__init__.py`, `forms/multi_fields.py` |
| `log.py` | `log.py`, `log_cleaner.py`, `exceptions.py` |
| `extracao.py` | `extracao_conteudo.py`, `extracao_bndt.py`, `extracao.py` (shim → real), `gigs/__init__.py`, `gigs/creation.py` |
| `extraction.py` | `extraction/indexacao.py`, `extraction/__init__.py` |
| `progress.py` | `progress/monitoramento.py`, `progress/models.py`, `progress/__init__.py` |
| `drivers.py` | `drivers/__init__.py`, `drivers/factory.py`, `utils_drivers.py`, `utils_paths.py`, `utils_login.py` |
| `session.py` | `session/__init__.py`, `session/manager.py`, `utils_cookies.py` |
| `navigation.py` | `navigation/__init__.py`, `navigation/filtros.py`, `navigation/sigilo.py` |
| `documents.py` | `documents/__init__.py`, `documents/busca.py`, `documents/download.py` |
| `variaveis.py` | `variaveis.py`, `variaveis_client.py`, `variaveis_helpers.py`, `variaveis_painel.py`, `variaveis_resolvers.py` |
| `utils.py` | `utils_formatting.py`, `utils_sleep.py`, `utils_error.py`, `utils_tempo.py`, `utils_recovery.py`, `utils_observer.py`, `utils_driver_legacy.py`, `converters.py`, `utils_collect.py`, `scripts/loader.py` |
| `utils_editor.py` | `utils_editor.py`, `utils_collect_content.py`, `utils_collect_timeline.py` |
| `selectors.py` | `utils_angular.py` (com fix A1), `utils_selectors.py`, `selectors_pje.py`, `element_wait.py`, `smart_finder.py` |
| `selenium.py` | `selenium_base/element_interaction.py`, `selenium_base/driver_operations.py` |
| `selenium_wait.py` | `selenium_base/wait_operations.py`, `selenium_base/retry_logic.py` (com A2), `selenium_base/click_operations.py` |
| `selenium_select.py` | `selenium_base/smart_selection.py`, `selenium_base/field_operations.py` |
| `js_helpers.py` | `selenium_base/js_helpers.py` |

**Eliminar (stubs sem lógica real):**
`extracao_analise.py`, `extracao_documento.py`, `extracao_indexacao.py`, `extracao_indexacao_fluxo.py`, `extracao_processo.py`, `monitoramento_progresso_unificado.py`, `progresso_unificado.py`, `progress_models.py`, `progress.py` (stub), `legacy/extracao_analise.py`, `legacy/progress_models.py`

### Ordem de Execução

```bash
# 1. Backup obrigatório
cp -r Fix/ Fix/backup_pre_merge/

# 2. Eliminar stubs (ver lista acima)
# 3. Mergear grupos (ver tabela), um por vez
# 4. Após cada grupo:
py -m py_compile Fix/*.py
py tools/check_imports.py     # ou: py -c "import x"

# 5. Atualizar __init__.py com re-exports do novo layout
# 6. Validação final completa
py -c "from Fix.core import finalizar_driver"
py -c "from Mandado.processamento_api import processar_mandados_devolvidos_api"
py -c "from PEC.orquestrador import executar_fluxo_novo_simplificado"
py -c "from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b"
py -c "from Triagem.runner import run_triagem"
py -c "from Peticao.pet import run_pet"
```

### Critérios de Aceitação

- [ ] `Fix/` tem ≤ 20 arquivos (excluindo `__pycache__`)
- [ ] `py -m py_compile Fix/*.py` limpo
- [ ] 6 imports de validação acima passam
- [ ] Nenhum código foi reescrito (apenas movido)
- [ ] Backup `Fix/backup_pre_merge/` existe

---

## Frente C — Código Morto Restante (vulture)

Status das fases já executadas (ver `limpar-repositorio.md`):

- **Phase 1 ✅** — 60 arquivos mortos arquivados em `_archive/20260415_024013/`
- **Phase 2 🔄** — Slices 1, 2, 3 concluídos; revisão vulture em andamento

**Próximos passos (continuação do Slice 4+):**

```bash
# Gerar relatório vulture atualizado após merges
py -m vulture Fix/ atos/ SISB/ Prazo/ PEC/ Mandado/ Peticao/ Triagem/ \
   tools/vulture_whitelist.py --min-confidence 80 > tools/vulture_report_latest.txt

# Revisar e remover por lote de 5 arquivos
# Após cada lote: py -c "import x"
```

**Não fazer:**
- Funções com `# noqa: vulture` já documentadas como keeper
- Remover qualquer coisa em `Fix/` antes de concluir Frente B

---

## Não Fazer (escopo explicitamente excluído)

| Item | Motivo |
|------|--------|
| Page Object formal com `Fix/pages/` | `SmartFinder` já cobre; custo > benefício agora |
| GitHub Actions headless | Depende de decisão de infra; não bloqueia hoje |
| Substituição global de `WebDriverWait` | Quebra API pública sem ganho proporcional |
| Refatoração de lógica de negócio | Fora de escopo — apenas mover/mergear |
| Dividir arquivos >600 linhas | Trade-off consciente para reduzir contagem de arquivos |
