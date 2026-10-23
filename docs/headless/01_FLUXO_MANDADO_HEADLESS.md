# Headless — Fluxo Mandado (`Mandado/`)

> Implementação: [`EDITAR_AQUI.md`](EDITAR_AQUI.md). Entrada: `x.py` `FLOW_HANDLERS['A']` → `Mandado/entrada_api.py` (`processar_mandados_devolvidos_api`).

## Veredito: compatível; sem mudança específica deste fluxo

- A leitura é por API (`Fix/variaveis.py: PjeApiClient`) com cookies do contexto Playwright → idêntica em headless.
- `fluxo_argos.py`/`regras.py` são lógica sobre dados; não dependem de tela.
- Não há `pyperclip` em `Mandado/` (verificado por grep) → o clipboard virtual não é necessário aqui.

## Pontos a validar em execução real (hipóteses, não requisitos)

| Ponto | Arquivo | O que observar |
|---|---|---|
| Abertura/fechamento de aba | `Mandado/fluxo_ui.py` | Foco volta à aba correta após fechar a secundária |
| Clique em lixeira/modal de exclusão | `Mandado/apoio_fluxos.py` | `click_headless_safe` já cobre overlay; só agir se falhar |
| Transição de tarefa | `atos/movimentos_fluxo.py` | Timeouts de rota Angular |

Se algum falhar em headless, registrar log e criar compensação **dentro de `Play/pjeplay/headless.py`**, nunca em `Mandado/`.

## Checklist (execução real pendente)

- [ ] Rodar `PJEPLUS_DRIVER=PC_HEADLESS PJEPLUS_FLUXO=A py pw.py` e comparar resultado com o visível.
