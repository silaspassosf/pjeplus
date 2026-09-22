# INVENTÁRIO DE CÓDIGO MORTO

> Inventário com evidências para remoção planejada de código morto durante a migração.
> **Regra inviolável:** Nada é deletado antes da Fase F7 (exceto o que as fases F5/F6 já eliminam por construção).
> Marcação permitida no código: `# DEAD: <id-do-inventário>`.

---

| ID | Item / Arquivo | Evidência | Ação Planejada | Fase |
|---|---|---|---|---|
| DEAD-001 | `Andrei/` | 0 referências no pipeline de execução (`x.py`/`pw.py`) | Mantido para execução isolada e testes (NÃO DELETAR, decisão usuário) | — |
| DEAD-002 | `gen_bm.py`, `ad.py`, `temp_main_navegacao.py` (raiz) | 0 referências em todo o projeto | Marcar e deletar na F7 | F7 |
| DEAD-003 | `f.py` (harness multi-testes manual) | Ferramenta manual, não roda em `pw.py` | Mover para `tools/` ou deletar | F7 |
| DEAD-004 | `Fix/driver_factory.py` | Untracked / legado, sem `criar_driver_pc` (função esperada não existe) | Marcar e deletar na F7 | F7 |
| DEAD-005 | `Play/pjeplay/compat.py`, `element.py`, `waits.py`, `locators.py`, `actions.py` | Camada de compatibilidade falsa com Selenium | Deletar assim que zero call sites usarem | F5 |
| DEAD-006 | `Play/migrar_sleeps.py` | Ferramenta de transição de migração | Deletar após fechamento da F2 | F2 |
| DEAD-007 | `TeeOutput` + handlers duplicados em `x.py` | Causa da duplicação de cada linha de log no arquivo e console | Deletar / unificar na F1 | F1 |
| DEAD-008 | Flags `--sem-nativo` e `--selenium` | Usadas apenas como baseline de comparação durante refatoração | Deletar na F6 | F6 |
| DEAD-009 | `ecarta_api.py` (raiz) | 1 referência identificada no código | Auditar e consolidar na F2 | F2 |
| DEAD-010 | `limp.py`, `log.py` (raiz) | Sobreposição com utilitários de `Fix/` | Auditar e unificar na F2 | F2 |
