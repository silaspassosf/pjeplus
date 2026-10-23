# Headless — Fluxo Prazo / P2B (`Prazo/`)

> Implementação: [`EDITAR_AQUI.md`](EDITAR_AQUI.md). Entrada: `x.py` `FLOW_HANDLERS['B']` → `Prazo/loop_orquestrador.py: loop_prazo`; P2B em `Prazo/p2b_gateway.py`.

## Veredito: compatível; ajuste só no ambiente de execução

- Não há `pyperclip` em `Prazo/` (verificado) → clipboard virtual não é necessário.
- `Prazo/loop_orquestrador.py:66` tem `input()`, mas só dentro de `pausar_confirmacao`, que retorna `True` logo se `DEBUG_PAUSAS_LOOP=False` (valor atual) e tem `except` para falta de TTY. **Manter `DEBUG_PAUSAS_LOOP=False`.**
- Menus de `x.py:793,832` usam `input()`; evitar com `PJEPLUS_DRIVER=PC_HEADLESS PJEPLUS_FLUXO=B`.
- CKEditor já é preenchido via `setData` (não há digitação a trocar).
- Extração de documentos usa API (`PjeApiClient`) — independente de renderização.

## Pontos a validar em execução real (hipóteses)

| Ponto | Onde | Observar |
|---|---|---|
| Filtro `#inputFiltro` | `Prazo/p2b_gateway.py` | Angular reage ao preenchimento |
| Menus overlay de movimentação | `atos/movimentos_navegacao.py` | Backdrop não intercepta (`click_headless_safe`/`limpar_overlays_headless` existem) |
| Tabelas com virtual scroll | `p2b_gateway.py` | Todas as linhas renderizadas no viewport 1920x1080 |
| Recovery de driver | `Fix/utils.py:1594` | Não usado por este fluxo; só relevante se registrado |

Compensações, se necessárias, vão **só em `Play/pjeplay/headless.py`**.

## Checklist (execução real pendente)

- [ ] Rodar `PJEPLUS_DRIVER=PC_HEADLESS PJEPLUS_FLUXO=B py pw.py` e comparar com o visível.
