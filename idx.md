# PJePlus — Arquitetura e Contexto (IDX)

Atualizado: 2026-05-02 (pós-Xcode Phase 6)

> **Nota de refatoração (xcode):** Ainda em fase de testes. Para consultar qualquer arquivo no estado anterior ao xcode, usar:
> ```bash
> git show 2ab0fca:<caminho/do/arquivo.py>
> # Exemplo: git show 2ab0fca:Fix/core.py
> ```
> `2ab0fca` = "snapshot pre-erase baseline" (01/05/2026) — estado salvo imediatamente antes do xcode começar.

## 1. Visao Geral

O **PJePlus** e um ecossistema de automacao em Python (Selenium + Firefox) focado no Processo Judicial Eletronico (PJe TRT2).

- **Navegador:** Firefox (PC visivel ou headless)
- **Meta:** Execucao 100% headless em nuvem (GitHub Actions)
- **Entry points:** `x.py` (principal, ~630 linhas), `f.py` (variante)
- **Filosofia:** Mudancas cirurgicas, sem mega-refatoracoes. Foco em eliminacao de `time.sleep`, reducao de erros de corrida Angular, e eficiencia termica/rede.

---

## 2. Topologia do Projeto

### Core (Infraestrutura compartilhada)

| Diretorio | Papel |
|---|---|
| `Fix/` | Motor utilitario: login, driver, injecoes JS, cache de seletores, extracao, progresso, logs |
| `core/` | Contratos e registries compartilhados: `RuleRegistry`, `ResultadoExecucao`, `adapt_action` |
| `api/` | API Gateway Core: `PjeApiClient`, `variaveis_client`, `variaveis_helpers` |
| `atos/` | Wrappers de movimentacao e acoes judiciais (20+ modulos) |
| `utilitarios_processamento.py` | Flow Engine generico: `run_batch()`, `resultado_ok()`, `resultado_falha()`, `create_skip_checker()` |

### Modulos de Negocio

| Diretorio | Fluxo | Entry point |
|---|---|---|
| `Mandado/` | Fluxos A, B — processamento de mandados (Argos + Outros) | `processamento_api.py` |
| `Prazo/` | Fluxos C, D — prazos e P2B | `fluxo_api.py`, `p2b_fluxo.py` |
| `PEC/` | Fluxo E — PEC (comunicacoes, sob, cartas, SISBAJUD) | `orquestrador.py`, `regras_pec.py` |
| `Triagem/` | Fluxo F — Triagem Inicial de processos | `runner.py`, `regras.py` |
| `Peticao/` | Fluxo G — Processamento de petições | `pet.py`, `regras.py`, `orquestrador.py` |
| `SISB/` | Integracao SISBAJUD (bloqueios, minutas, ordens) | `core.py`, `s_orquestrador.py` |

### Extensoes Firefox (referencia JS)

| Diretorio | Descricao |
|---|---|
| `AVJT/` | Extensao principal: paineis, GIGS, calculos, captcha, correios |
| `maispje/` | Extensao complementar: interface PJe avancada |

### Ferramentas e Suporte

| Diretorio | Descricao |
|---|---|
| `Agente/` | Extensao VSCode para PJePlus (TypeScript) |
| `AHK/` | Scripts AutoHotKey (UX Windows) |
| `scripts/` | Scripts auxiliares |
| `tools/` | Ferramentas de diagnostico e analise |
| `docs/` | Documentacao complementar |
| `xcode/` | Plano de simplificacao (9 docs + README) — referencia da refatoracao |
| `_archive/` | Codigo removido/legado organizado por data |
| `ref/` | Referencia externa e manifests de arquitetura |
| `cache/tessdata/` | Dados Tesseract OCR |
| `logs_execucao/` | Logs de execucao |
| `cookies_sessoes/` | Cookies de sessao persistentes |

---

## 3. Phase 6 — Unified Rules-Action (2026-05-02)

### Registry unificado de regras

`core/rule_registry.py` fornece o contrato padrao para todos os modulos:

```python
from core.rule_registry import RuleRegistry, adapt_action

# Action = Callable[[Any, dict], Optional[dict]]
registry = RuleRegistry("nome", ["bucket1", "bucket2", ...])
registry.register(r'pattern', 'bucket1', acao_fn)
bucket, action = registry.match(observacao)
```

### Status por modulo

| Modulo | Registry | Estado |
|---|---|---|
| `PEC/regras_pec.py` | `registry = RuleRegistry("pec", BUCKET_ORDEM)` | Concluido |
| `Mandado/regras.py` | `registry_argos` — camada complementar sobre estrategias | Concluido |
| `Triagem/regras.py` | `alerta_registry` — alertas pos-triagem | Concluido |
| `Peticao/regras.py` | `peticao_registry` — buckets apagar/pericias/recurso/diretos/analise | Concluido |
| `Prazo/p2b_fluxo_regras.py` | `prazo_registry` — 22 buckets de prioridade | Concluido |

---

## 4. Diretrizes de Codigo (A Biblia do PJePlus)

### A. Busca de Elementos — SmartFinder + Cache

- Proibido `try css1, try css2, try xpath...` em modulos de negocio
- Usar `SmartFinder` com consulta a cache de seletores
- Falhas de seletor → log isolado (`monitor_aprendizado.log`), nunca no log principal

### B. Waits — Fim do Polling

- Proibido `time.sleep()` e `WebDriverWait` em loops
- Usar `aguardar_renderizacao_nativa` (MutationObserver nativo)
- Ver secao 6 para referencia rapida de API

### C. Sanitizacao de Logs

- Log principal: apenas mudancas de estado, sucessos, falhas criticas
- Sem "tentativa 1", "buscando...", "scroll realizado"

### D. Instrumentacao de Tempo

- `Fix/core.py`: `tempo_execucao` (context manager), `medir_tempo` (decorator)
- Ativar: `PJEPLUS_TIME=1`
- Exemplos instrumentados: `atos/judicial_fluxo.py`, `Prazo/p2b_fluxo_regras.py`

### E. Padroes Obrigatorios

| ID | Regra |
|---|---|
| P1 | Sem wrappers de uma linha em `Fix/core.py` — apenas re-exportacoes |
| P2 | Max 3 niveis de indentacao; auxiliares `_privadas` imediatamente acima |
| P3 | Infra usa excecao tipada; nunca `return False` silencioso |
| P4 | Sem `time.sleep()` — usar `aguardar_renderizacao_nativa` |
| P5 | JS longo → arquivo `.js` em `scripts/` do modulo; carregar via `carregar_js()` |
| P6 | Retornos complexos → `@dataclass` |
| P7 | Driver via context manager em orquestradores novos |
| P8 | Imports sempre no topo do modulo — nunca dentro de funcao |

---

## 5. Diretrizes para Cloud / Headless

1. **Firefox invisivel (`-headless`):** ActionChains complexos e coordenadas absolutas falham
2. **Downloads silenciosos:** MIME types no profile Firefox, sem dialogos nativos
3. **Scroll virtual:** `scrollIntoView({block: 'center'})` antes de qualquer `.click()`
4. **CI:** `PJEPLUS_TIME=1` em todos os workflows; sanity com `py_compile` e `test_imports.py`
5. **Incidentes:** usar `Fix.log_cleaner` para filtrar excecoes e DOM bruto

---

## 6. API de Interacao Obrigatoria (Fix) — Referencia Rapida

Proibido usar `WebDriverWait`, `ActionChains`, `time.sleep` ou `element.click()` direto nos modulos de negocio.

### 6.1 Clique

| Situacao | Funcao | Import |
|---|---|---|
| Caso geral (headless-safe) | `click_headless_safe(driver, seletor, by=By.CSS_SELECTOR, timeout=10)` | `from Fix.headless_helpers import click_headless_safe` |
| Elemento ja encontrado | `safe_click_no_scroll(driver, elemento)` | `from Fix.selenium_base.click_operations import safe_click_no_scroll` |

### 6.2 Esperar Elemento

| Situacao | Funcao | Import |
|---|---|---|
| Esperar presenca | `esperar_elemento(driver, seletor, timeout=10, by=By.CSS_SELECTOR)` | `from Fix.selenium_base.wait_operations import esperar_elemento` |
| Esperar clicavel | `wait_for_clickable(driver, seletor, timeout=10, by=By.CSS_SELECTOR)` | `from Fix.selenium_base.wait_operations import wait_for_clickable` |
| Aguardar renderizacao Angular | `aguardar_renderizacao_nativa(driver, seletor, modo='aparecer', timeout=5)` | `from Fix.utils_observer import aguardar_renderizacao_nativa` |

### 6.3 Regras de Combinacao

1. **Para clicar:** `click_headless_safe` com seletor — nao buscar separado
2. **Para ler texto/atributo:** `esperar_elemento` → ler do elemento retornado
3. **Para checar estado:** `esperar_elemento` → `.get_attribute()`
4. **Para aguardar tabela/lista:** `aguardar_renderizacao_nativa` antes de `find_elements`
5. **Nunca:** `WebDriverWait(driver, N).until(EC...)` em modulos de negocio

---

## 7. Registro de Bugs

| Data | ID | Modulo | Sintoma | Causa Raiz | Fix |
|---|---|---|---|---|---|
| 31/03/2026 | #001 | `Fix/navigation/filters.py` | `aplicar_filtro_100` retorna False silencioso | `com_retry` chamado com `log=True` mas implementacao usa `log_enabled` → TypeError silencioso | Trocar `log=True` → `log_enabled=True` |

### Regra derivada do Bug #001

```python
# VIA Fix.core (wrapper publico — usar log=True):
from Fix.core import com_retry
com_retry(func, max_tentativas=3, log=True)  # OK

# VIA Fix.selenium_base.retry_logic (direto — usar log_enabled=True):
from Fix.selenium_base.retry_logic import com_retry
com_retry(func, max_tentativas=3, log_enabled=True)  # OK
com_retry(func, max_tentativas=3, log=True)  # ERRO SILENCIOSO
```

Preferir sempre o import via `Fix.core`.

---

**INSTRUCAO FINAL PARA A IA:** Ao iniciar a sessao, confirme a leitura do `IDX.md`, compreenda a topologia e aguarde a indicacao do usuario sobre qual modulo sera trabalhado hoje.
