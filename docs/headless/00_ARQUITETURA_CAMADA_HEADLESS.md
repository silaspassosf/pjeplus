# Arquitetura da Camada Headless — PJePlus

> **Ponto de entrada para implementação: [`EDITAR_AQUI.md`](EDITAR_AQUI.md).** Este doc é só contexto.
> Revisado em 13/10/2026 após validação contra o código (ver `04_VALIDACAO_E_AJUSTES.md`).

## 1. Princípio

Camada **extra** que só existe em headless. O driver visível não muda:
- código de negócio (`Mandado/`, `Prazo/`, `PEC/`, `atos/`, `Fix/`) intocado;
- módulo novo `Play/pjeplay/headless.py`, importado **apenas** se `criar_driver(headless=True)`;
- único gancho em arquivo existente: `Play/pjeplay/launcher.py`, dentro de `if headless:`.

## 2. Diagnóstico empírico (sonda `sonda_headless.py`)

| Critério | Headed | Headless | Impacto |
|---|---|---|---|
| Viewport | janela do SO | 1920x1080 fixa (`launcher.py:124`) | nenhum (já tratado) |
| `visibilityState` / `hasFocus` | visible/true | visible/true | nenhum |
| rAF em background | 38 frames/600ms | 38 frames/600ms | nenhum |
| `execCommand('copy')` na página | true | true | — |
| **Clipboard do SO (`pyperclip`)** | atualizado | **NÃO atualizado** | **único problema comprovado** |
| Teclado, click fora do viewport, cookies/SSO | ok | ok | nenhum |

## 3. O que a camada faz (escopo real)

1. **Clipboard virtual**: captura cópias da página em `window.__pjeplay_clipboard` e faz `pyperclip.paste()` ler disso em headless. Consumidores reais: `PEC/anexos/anexos_extracao.py:44` e `Fix/extracao.py:213` (ambos já tentam outro caminho antes).
2. **Recovery headless**: `Fix/utils.py:1594` recria driver com `headless=False`; a camada faz a factory padrão (`Fix.utils.obter_driver_padronizado`) forçar `headless=True` em runtime.

## 4. O que NÃO entra (já existe / sem evidência)

| Ideia do doc original | Situação |
|---|---|
| Overlay auto-buster | Já existe: `limpar_overlays_headless`, `click_headless_safe` (`Fix/browser_suporte.py`, usados em `Fix/core.py`) |
| CKEditor via `setData` | Já é `setData` (`anexos_juntador_helpers.py:415`, `comunicacao_finalizacao.py:103`, `pjeplay/pje.py:49`) |
| Guarda de `input()` | Só 4 `input(`: `x.py:793,832` (evitados por `PJEPLUS_DRIVER`/`PJEPLUS_FLUXO`), `loop_orquestrador.py:66` (atrás de `DEBUG_PAUSAS_LOOP=False`), `diagnostico_runtime.py:402` (debug) |
| `input()` do SISB | Não existe |
| Intercepção de upload (`set_input_files`) | Sem evidência do problema; **a testar** |
| Gestão de abas / checkbox invisível / datepicker | Hipóteses; **a testar** em execução real |
| Login headless | Já existe em `x.py:137` |

## 5. Estado do código

Nada implementado ainda. Implementação descrita em `EDITAR_AQUI.md`.
