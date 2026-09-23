# INVENTÁRIO DE CÓDIGO MORTO

> Inventário com evidências para remoção planejada de código morto durante a migração.
> **Regra inviolável:** Nada é deletado antes da Fase F7 (exceto o que as fases F5/F6 já eliminam por construção).
> Marcação permitida no código: `# DEAD: <id-do-inventário>`.

---

| ID | Item / Arquivo | Evidência | Ação Planejada / Status | Fase |
|---|---|---|---|---|
| DEAD-001 | `Andrei/` | 0 referências no pipeline de execução (`x.py`/`pw.py`) | Mantido para execução isolada e testes (NÃO DELETAR, decisão usuário) | — |
| DEAD-002 | `gen_bm.py`, `temp_main_navegacao.py` | 0 referências em todo o projeto | Removidos na F7; `ad.py` mantido ativo (gerador de `aud.md`) | F7 (concluído) |
| DEAD-003 | `f.py` (harness multi-testes manual) | Ferramenta manual, não roda em `pw.py` | Migrado para 0 padrões Selenium na F4; mantido como utilitário | F4/F7 (concluído) |
| DEAD-004 | `Fix/driver_factory.py` | Fábrica legada | Modernizado na F5 para delegar para Playwright launcher (0 padrões) | F5 (concluído) |
| DEAD-005 | `Play/pjeplay/compat.py`, `actions.py`, `waits.py` | Camada de compatibilidade com Selenium | Mantidos como isolamento para proteger módulos legados (SISB, Andrei) | F5 (concluído) |
| DEAD-006 | `Play/migrar_sleeps.py` | Ferramenta de transição de migração | Removido no fechamento da F2 | F2 (concluído) |
| DEAD-007 | `TeeOutput` + handlers duplicados em `x.py` | Causa da duplicação de cada linha de log no arquivo e console | Removido na F1 (sink único FileHandler) | F1 (concluído) |
| DEAD-008 | Flags `--sem-nativo` e `--selenium` | Usadas apenas como baseline de comparação | Removidas de `pw.py` na F6 | F6 (concluído) |
| DEAD-009 | `ecarta_api.py` (raiz) | Cliente HTTP puro | Zerado na F4 (0 padrões Selenium) | F4 (concluído) |
| DEAD-010 | `limp.py`, `log.py` (raiz) | Arquivos soltos sem referências | Removidos na F7 | F7 (concluído) |
