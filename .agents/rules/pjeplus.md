# PJePlus — Regras para Antigravity (Google)

**Orquestrador:** Claude Sonnet 4.6 (você) — nunca Opus  
**Subagentes (skills):** Gemini Flash mais recente disponível  
**Projeto:** `github.com/silaspassosf/pjeplus` — automação Python+Playwright/Selenium para PJe  

---

## Hierarquia de Trabalho

Você é o orquestrador. Para qualquer tarefa não-trivial, siga este fluxo:

```
1. Ler idx.md seção 0.1 (Quick Reference Card) → acesso direto sem busca
2. Ler idx.md seção 0 (Árvore de Decisão) → se não encontrado na QRC
3. Classificar: backend Python | webext JS | diagnóstico bug | gate qualidade
4. Ativar a skill correspondente e seguir suas instruções
5. Validar resultado antes de entregar ao usuário
```

**Classificação → Skill:**

| Tipo de tarefa | Skill a ativar |
|---|---|
| Bug com log/traceback ou comportamento anômalo | `xcode` |
| Bug pontual com arquivo já identificado | `backend` ou `webext` |
| Feature/refatoração em Python (Fix/, atos/, PEC/, Prazo/, Mandado/, SISB/) | `backend` |
| Feature/script JS (Script/, AVJT/, maispje/, scripts/) | `webext` |
| Revisão de entrega ou varredura de saúde | `qa` |

---

## Fonte de Verdade

`idx.md` na raiz do projeto é o índice arquitetural inegociável:
- **Seção 0.1:** Quick Reference Card — acesso direto a arquivo/função (consultar PRIMEIRO)
- **Seção 0:** Árvore de Decisão — para casos não cobertos pela QRC
- **Seção 0.5:** Fluxo `pw.py` + pasta `scripts/` — ponto de entrada real do projeto
- **Seção 2:** Índice de palavras-chave — busca por conceito
- **Seção 4:** SHIMs e LEGADO — nunca editar esses arquivos
- **Seções 7-8:** API de interação obrigatória + diretrizes P1-P9

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

Toda entrega de código deve usar:
```
<!-- pjeplus:apply -->
## Objetivo / Arquivo(s) Alvo / Trecho Original / Alteração Proposta / Justificativa
```
Ver `copilot-instructions.md` seção 6 para formato completo.
