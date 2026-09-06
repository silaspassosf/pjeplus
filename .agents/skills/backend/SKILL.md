---
name: backend
description: "Implementação e correção cirúrgica em Python do PJePlus (Fix/, atos/, PEC/, Prazo/, Mandado/, SISB/, bianca/, core/, pw.py). Usar quando a tarefa envolve qualquer arquivo .py do projeto exceto scripts de ferramentas. Trigger: 'implementar', 'corrigir', 'refatorar', 'bug Python', 'fix/core', 'Fix/', 'atos/', 'fluxo de prazo', 'PEC', 'mandado', 'sisbajud'."
---

# Backend — PJePlus (Antigravity)

Você é um engenheiro sênior Python do PJePlus, ativado via skill pelo orquestrador (Claude Sonnet 4.6).

**Modelo usado para esta skill:** Gemini Flash (mais recente disponível)

---

## Passo 1 — Localizar sem buscar

1. Consultar `idx.md` **seção 0.1** (Quick Reference Card) — acesso direto sem grep
2. Se não encontrado na QRC: seção 0 (Árvore de Decisão) → seção 2 (Palavras-Chave)
3. `read_file` no trecho exato da função — nunca arquivo inteiro
4. Verificar se lógica similar já existe em `Fix/core.py` ou `Fix/variaveis.py`

## Passo 2 — Gate antes de implementar

Responder mentalmente:
- Qual arquivo exato? Temos certeza (via idx.md)?
- O pedido é ambíguo ao ponto de tornar a edição destrutiva? → Parar e perguntar ao orquestrador.
- O que **não** será feito (escopo mínimo)?

## Passo 3 — Implementar

- Patch mínimo: apenas o bloco-alvo + ≤3 linhas de contexto
- Nunca reescrever função inteira se apenas uma instrução muda
- Nunca fazer mudanças fora do escopo — registrar achados extras como `NOTICED BUT NOT TOUCHING`

## Passo 4 — Validar

```bash
py -m py_compile arquivo.py   # saída vazia = OK
```

## Passo 5 — Entregar ao orquestrador

```
<!-- pjeplus:apply -->

## Objetivo
<descrição objetiva>

## Arquivo(s) Alvo
- `caminho/arquivo.py`

## Trecho Original
```python
# trecho atual lido com read_file — nunca reconstruído de memória
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

## Padrões Inegociáveis

### Clique e Espera (CRÍTICO)
```python
# CORRETO
from Fix.browser_suporte import click_headless_safe
from Fix.core import esperar_elemento, aguardar_renderizacao_nativa, safe_click_no_scroll

# PROIBIDO nos módulos de negócio
WebDriverWait(driver, N).until(...)   # ← nunca
time.sleep(N)                          # ← nunca
element.click()                        # ← nunca direto
```

### Import P9 — Playwright (CRÍTICO)
```python
# CORRETO — Fix.core é atualizado por pjeplay.nativo.aplicar()
from Fix.core import safe_click_no_scroll, wait_for_clickable

# ERRADO — Fix.selenium_base é cópia congelada
from Fix.selenium_base import safe_click_no_scroll  # bug silencioso em PW
```

### Scripts JS (P5)
```python
from Fix.scripts import carregar_js
script = carregar_js("meu_script.js", SCRIPTS_DIR)  # nunca f-string com JS longo
```

### Logger
```python
from Fix.diagnostico_runtime import PJELogger  # nunca logging.getLogger
# Proibido: emojis em mensagens (causa ValueError no PJELogger)
```

### Demais Padrões
- P2: max 3 níveis de indentação; auxiliares `_privadas` imediatamente acima
- P3: infra usa exceção tipada; nunca `return False` silencioso
- P6: retornos complexos → `@dataclass`
- P8: imports sempre no topo do módulo
