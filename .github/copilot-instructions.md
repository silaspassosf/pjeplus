# PJePlus — Instruções GitHub Copilot

**Atualizado:** 2026-10-01

**Escopo:** Automação Python+Playwright para o sistema PJe (Processo Judicial Eletrônico). Firefox exclusivo.

---

## 0. Leitura Obrigatória Antes de Qualquer Ação

```
1. idx.md (seção 0 → Árvore de Decisão de Escopo)      — localizar módulo/arquivo
2. idx.md (seção 0.5 → pw.py + scripts/)               — ponto de entrada real
3. Arquivo específico → ler apenas a seção relevante
```

**NUNCA:** ler arquivos inteiros aleatoriamente · buscar sem consultar `idx.md` · referenciar `INDEX.md` (não existe; o índice é `idx.md`)

---

## 1. Hierarquia de Agentes

O GitHub Copilot suporta orquestrador + subagentes nativos via `runSubagent`. A estrutura deste projeto:

```
orchestrator.agent.md   ← invoke diretamente para qualquer tarefa não-trivial
  ├── backend.agent.md      Python: Fix/, atos/, PEC/, Prazo/, Mandado/, SISB/
  ├── webext.agent.md       JS: Script/, AVJT/, maispje/, scripts/ (IIFE/bookmarklets)
  ├── xcode.agent.md        Diagnóstico profundo de bugs → gera bug.md
  └── qa.agent.md           Gate de qualidade final
```

**Modelos disponíveis neste ambiente (free tier / local):**

| Agente | Modelo preferido | Fallback |
|---|---|---|
| `orchestrator` | `deepseek/deepseek-chat` | `glm-4-flash` |
| `backend` | `deepseek/deepseek-chat` | `glm-4-flash` |
| `webext` | `glm-4-flash` | `deepseek/deepseek-chat` |
| `xcode` | `deepseek/deepseek-chat` | `glm-4-flash` |
| `qa` | `glm-4-flash` | `deepseek/deepseek-chat` |

> **DeepSeek R1 Pro:** reservado para override manual quando a orquestração atual não resolver. Configurar por agente em `~/.copilot/settings.json` via `/subagents` se necessário — nunca como padrão.

**`user-invocable: false`** nos subagentes (backend, webext, xcode, qa) — sempre invocar via orquestrador.

---

## 2. Regras Absolutas

### R0 — Branch e referência temporal
- **Branch de trabalho é sempre `main`.** Confirme com `git branch --show-current`. Não consulte branches anteriores nem troque de branch.
- Em caso de dúvida, falha ou regressão, compare o código atual com o estado imediatamente anterior ao commit `968047a`: use `git show 968047a^:CAMINHO/ARQUIVO.py`.
- A comparação é apenas evidência histórica; **não restaure nem copie automaticamente** o código antigo. Corrija conforme o pedido atual, mantendo a arquitetura Playwright (`Fix/espera.py`, `espera.ate_*`, `By` de `Play.pjeplay.locators`) — nunca reintroduza Selenium.
- Se a referência `968047a^` ou o arquivo solicitado não estiver disponível, relate a lacuna e peça o acesso correto. Não procure substitutos em branches anteriores.
- `gigs-plugin.js`, `LEGADO.md`, `legado.md` e outras fontes legadas só podem ser consultadas quando o prompt do usuário mencionar expressamente a fonte.
- Detalhes: `.agents/rules/comparacao-historica.md`.
- Validação obrigatória pós-correção: `py tools/check_pw.py` + `py play/smoke.py --projeto` (91/91).

### R1 — Escopo Exato
- ✅ Implementar exatamente o que foi pedido
- ✅ Reutilizar código existente (verificar `idx.md` primeiro)
- ❌ NÃO adicionar validações não solicitadas
- ❌ NÃO criar abstrações "para facilitar no futuro"
- ❌ NÃO modificar assinaturas sem permissão explícita

### R2 — Zero Arquivos Não Pedidos
- ❌ Frameworks de teste (pytest, unittest, mocks)
- ❌ Arquivos de configuração não solicitados
- ✅ Scripts de teste simples: `py -m py_compile arquivo.py`, `py test_X.py`

### R3 — Reutilização Mandatória
Verificar em `idx.md` (seção 2, Índice de Palavras-Chave) antes de criar qualquer função. Funções de interação devem vir de `Fix.core` (nunca de `Fix.selenium_base` — cópia congelada).

### R4 — Comando Python
Sempre `py` (não `python` nem `python3`). Validação: `py -m py_compile arquivo.py`

---

## 3. Ponto de Entrada Real

`pw.py` é o executor principal — não `x.py` diretamente:

```
py pw.py              # Playwright nativo (padrão — ÚNICO caminho em produção)
py pw.py --trace      # + trace.zip navegável
```

> ⚠️ A flag `--selenium` foi REMOVIDA na migração (F6). Não usar, não recriar, não sugerir.

Ver `idx.md` seção 0.5 para detalhes completos.

---

## 4. Padrões de Código (P1–P9)

Detalhados em `idx.md` seções 7-8. Resumo:

| ID | Regra |
|---|---|
| P4 | `aguardar_renderizacao_nativa` em vez de `time.sleep` |
| P5 | JS longo → arquivo `.js` em `scripts/`; carregar via `carregar_js()` |
| P6 | Retornos complexos → `@dataclass` |
| P9 | **CRÍTICO para Playwright:** imports de `Fix.core`, nunca de `Fix.selenium_base` |

**Proibido em módulos de negócio:** `WebDriverWait` · `ActionChains` · `time.sleep` · `element.click()` direto

---

## 5. Shims e Legado — Não Editar

- **SHIMs** (`Fix/abas.py`, `Fix/headless_helpers.py`, `Fix/log.py` etc.) → modificações vão nos arquivos reais (ver `idx.md` seção 4)
- **`leg/`**, `Mandado/core.py`, `_archive/`, `ref/`, `LEGADO.md` → não editar. Consultar qualquer fonte legada somente se o prompt a mencionar expressamente.

---

## 6. Formato de Patch

```markdown
<!-- pjeplus:apply -->

## Objetivo
<descrição objetiva>

## Arquivo(s) Alvo
- `caminho/do/arquivo.py`

## Trecho Original
```python
# trecho atual completo (lido com read/file, nunca reconstruído de memória)
```

## Alteração Proposta
<!-- pjeplus:delta:start -->
```python
# trecho novo completo
```
<!-- pjeplus:delta:end -->

## Justificativa
<motivo técnico, máximo 3 linhas>
```

---

## 7. Referência Rápida — APIs Principais

```python
# Clique (headless-safe)
from Fix.browser_suporte import click_headless_safe
from Fix.core import safe_click_no_scroll, safe_click

# Espera
from Fix.core import esperar_elemento, aguardar_renderizacao_nativa

# Preenchimento
from Fix.core import preencher_campo, selecionar_opcao

# Logger
from Fix.diagnostico_runtime import PJELogger  # nunca logging.getLogger

# API REST PJe
from Fix.variaveis import PjeApiClient, session_from_driver

# Retry
from Fix.core import com_retry  # parâmetro: log=True
```

Ver `idx.md` seção 7 para tabela completa com imports corretos.
