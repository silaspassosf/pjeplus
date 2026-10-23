# Headless — Fluxo PEC (`PEC/`, `atos/comunicacao*`)

> Implementação: [`EDITAR_AQUI.md`](EDITAR_AQUI.md). Entrada: `x.py` `FLOW_HANDLERS['D']` → `PEC/orquestrador.py: executar_fluxo_novo_simplificado`.

## Veredito: único ponto crítico confirmado é o clipboard

- **`PEC/anexos/anexos_extracao.py:44`** (`extrair_numero_processo_da_pagina`): clica `i.far.fa-copy.fa-lg` e lê `pyperclip.paste()`. Em headless o SO não recebe a cópia → leitura obsoleta. Só é alcançado se o cabeçalho `span.texto-numero-processo` falhar (fallback). **Coberto pelo clipboard virtual** de `EDITAR_AQUI.md` (A1), sem editar o arquivo.
- `Fix/extracao.py:213` (`extrair_pdf`, usado por fluxos que extraem texto): mesmo problema, também só no fallback quando `<pre>` está vazio. Coberto pela mesma camada.
- `PEC/anexos/anexos_configuracao.py:14` importa `pyperclip` sem leitura relevante (sem impacto).

## Já resolvido (não implementar nada)

- Substituição de marcadores no CKEditor: já via `setData` (`PEC/anexos/anexos_juntador_helpers.py:415`).
- Overlays/cliques: `click_headless_safe`/`limpar_overlays_headless`.

## Pontos a validar em execução real (hipóteses)

| Ponto | Arquivo | Observar |
|---|---|---|
| Upload/juntada de anexos | `PEC/anexos/anexos_juntador_base.py` | Como o arquivo é enviado hoje (não há `set_input_files` no código); confirmar que funciona sem janela de SO |
| Seleção de destinatários | `atos/comunicacao_destinatarios.py` | Checkbox clicável em tabela com scroll |
| Meio/prazo/datas | `atos/comunicacao_preenchimento.py` | Dropdown em `.cdk-overlay-container` e datepicker |

Compensações, se necessárias, vão **só em `Play/pjeplay/headless.py`**.

## Checklist (execução real pendente)

- [ ] Rodar `PJEPLUS_DRIVER=PC_HEADLESS PJEPLUS_FLUXO=D py pw.py` e comparar com o visível.
- [ ] Teste de aceitação do clipboard (`tools/check_headless_layer.py`).
