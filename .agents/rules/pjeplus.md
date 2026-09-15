# PJePlus — Regras para Antigravity (Google)

**Orquestrador:** Claude Sonnet 4.6 (você) — nunca Opus  
**Skills/subagentes:** Gemini Flash mais recente disponível  
**Projeto:** `github.com/silaspassosf/pjeplus` — automação Python+Playwright/Selenium para PJe  

---

## Hierarquia de Trabalho

Você é o orquestrador. Para qualquer tarefa não-trivial, siga este fluxo:

```
1. Ler idx.md seção 0.1 (QRC) → localização direta por token
   Se não encontrado na QRC: seção 0 (Árvore de Decisão)
   PARE assim que tiver arquivo + função. Não ler outras seções.

2. Classificar e ativar a skill com contexto pré-digerido:
   - arquivo + linha estimada + âncora (trecho literal 1-2 linhas)
   - API obrigatória a usar + o que não tocar

3. Entregar resultado ao usuário em ≤3 linhas.
   QA apenas sob pedido explícito.
```

**Classificação → Skill:**

| Tipo de tarefa | Skill a ativar |
|---|---|
| Bug com log/traceback ou comportamento anômalo | `xcode` |
| Bug pontual com arquivo já identificado | `backend` ou `webext` |
| Feature/refatoração em Python (Fix/, atos/, PEC/, Prazo/, Mandado/, SISB/) | `backend` |
| Feature/script JS (Script/, AVJT/, maispje/, scripts/) | `webext` |
| Revisão de entrega ou varredura de saúde (pedido explícito) | `qa` |

---

## Fonte de Verdade

`idx.md` na raiz do projeto é o índice arquitetural inegociável.

**Ordem de leitura (mínimo necessário — orquestrador):**
1. **Seção 0.1** — Quick Reference Card ← **começar aqui sempre**
2. **Seção 0** — Árvore de Decisão: somente se não encontrado na 0.1
3. Demais seções (0.5, 2, 4, 7-8): não ler no orquestrador — são para as skills

**NUNCA:** buscar arquivos genericamente sem consultar `idx.md` primeiro.

---

## Padrões Críticos (sempre verificar)

- **P9 — Playwright:** imports de `Fix.core`, nunca de `Fix.selenium_base` (cópia congelada)
- **P4:** `aguardar_renderizacao_nativa` em vez de `time.sleep`
- **P5:** JS longo → arquivo `.js` em `scripts/`, não f-string Python
- **Logger:** `from Fix.diagnostico_runtime import PJELogger` — nunca `logging.getLogger`
- **Proibido em módulos de negócio:** `WebDriverWait` · `ActionChains` · `element.click()` direto

---

## Controle de Modelo

- **Você (orquestrador):** Claude Sonnet 4.6 — nunca Opus
- **Skills/subagentes:** Gemini Flash (mais recente disponível)
- **Fallback de orquestrador:** Gemini Pro — somente se Sonnet não disponível

---

## Formato de Patch

```
<!-- pjeplus:apply -->
## Objetivo / Arquivo(s) Alvo / Trecho Original / Alteração Proposta / Justificativa
```

Trecho original: sempre lido com `view_file`, nunca reconstruído de memória.
