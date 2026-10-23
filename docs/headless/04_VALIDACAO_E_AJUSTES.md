# Validação dos docs 00–03 contra o código real (13/10/2026)

> Método: grep/leitura do código em `main`. Nenhum código foi alterado.
> Veredito: o diagnóstico central (clipboard) é **real mas menor** do que o doc sugere; vários "pilares" já existem ou descrevem problemas inexistentes.

## 1. Afirmações CONFIRMADAS

| Afirmação | Evidência |
|---|---|
| `pyperclip.paste()` não reflete cópia da página em headless | Sonda de ontem (`sonda_headless.py`) |
| Usos de `pyperclip.paste` em fluxos | Apenas 2: `PEC/anexos/anexos_extracao.py:44` e `Fix/extracao.py:213` (`extrair_pdf`) |
| Ambos chamam `pyperclip.paste()` via atributo do módulo | Monkeypatch de `pyperclip.paste` em headless funciona sem tocar o negócio |
| Ponto de ancoragem existe | `Play/pjeplay/launcher.py:172` já faz `context.add_init_script(...)`; `driver.headless` existe (`driver.py:133`) |
| Login headless já tratado | `x.py:137-213` `_criar_driver_headless_com_login_visivel` (cookies → janela visível → headless) |
| `maximize_window` seguro | `driver.py:554-572` já trata headless (fixa 1920x1080) |

## 2. Afirmações REFUTADAS ou REDUNDANTES (corrigir nos docs)

| Doc | Afirmação | Realidade |
|---|---|---|
| 00 Pilar 2 / 03 | Overlay auto-buster é novo | **Já existe**: `limpar_overlays_headless`, `click_headless_safe` em `Fix/browser_suporte.py`, usados em `Fix/core.py` (L474, 2229, 3482). Remover pilar ou reduzir a "reaproveitar". |
| 03 §2 | CKEditor via teclado falha; propor `setData` | **Já é `setData`**: `PEC/anexos/anexos_juntador_helpers.py:415`, `atos/comunicacao_finalizacao.py:103`, `Play/pjeplay/pje.py:49`. Nada a fazer. |
| 03 §2 | SISB usa `input()` para PIN | **Falso**: nenhum `input(` em `SISB/`. Remover. |
| 03 §2 | Upload "intercepta input[type=file] com set_input_files" | Não há `set_input_files` no código; **não verificado** como o upload é feito hoje. Item aberto (ver §4). |
| 03 §3.1 | Intercepta `driver.execute_script('window.__pjeplay_clipboard')` | Funciona, mas o fluxo prioriza `<pre>`/cabeçalho antes do clipboard; o risco real é só nos fallbacks. |
| 00 Pilar 4 | `input()` trava fluxos | Só 4 `input(`: `x.py:793,832` (menus; contornados por `PJEPLUS_DRIVER`/`PJEPLUS_FLUXO`), `Prazo/loop_orquestrador.py:66` (atrás de `DEBUG_PAUSAS_LOOP=False`, já tem `except`), `Fix/diagnostico_runtime.py:402` (debug). **Risco baixo**; pilar vira só "garantir env vars + `DEBUG_PAUSAS_LOOP=False`". |
| 00 Pilar 5 / 03 §3.2-3.3 | Checkbox invisível, datepicker, aba | Sem evidência no código nem na sonda. Tratar como **hipótese a testar**, não como requisito. |

## 3. LACUNAS que os docs não cobriam

1. **Recovery de driver reabre VISÍVEL**: `Fix/utils.py:1594` faz `criar_driver(headless=False)` em "acesso negado". Numa sessão headless, abre janela e quebra a execução autônoma. É o gap real mais importante fora do clipboard.
2. **Perda de sessão em headless**: cookies expirados exigem janela visível (login manual). Em execução autônoma longa, precisa de política: abortar com log claro (e checkpoint via `Fix/monitoramento_progresso_unificado.py`) em vez de pedir interação.
3. **`pyperclip.copy`** em `Fix/utils.py:984` é só fallback de ImportError (clipboard interno é o padrão) — sem impacto.
4. **Falha silenciosa**: a leitura obsoleta do clipboard devolve texto antigo sem erro; a camada deve usar sentinela/limpeza antes do clique para detectar "clipboard não atualizou".

## 4. Plano revisado (mínimo e não invasivo)

Novo módulo único `Play/pjeplay/headless.py`, ativado só se `driver.headless`:

1. **Clipboard virtual** (única necessidade comprovada):
   - init script: listener `copy` + wrap de `navigator.clipboard.writeText`/`execCommand('copy')` → `window.__pjeplay_clipboard`.
   - Python: substituir `pyperclip.paste` por leitor que lê `window.__pjeplay_clipboard` do driver ativo (com `registrar_driver` de `api_resiliencia.py`); retorna ao original se não headless.
   - Gancho: logo após `add_init_script` em `launcher.py:172` e instalação em `pjeplay.iniciar()`.
2. **Recovery headless-aware** (DECIDIDO: sem editar `Fix/utils.py`): `headless.py` troca `Fix.utils.obter_driver_padronizado` em runtime por wrapper que força `headless=True`, só quando o driver é headless. Só Triagem/Peticao/Andrei registram recovery; Mandado/P2B/PEC não usam. Ver `EDITAR_AQUI.md` (A2).
> **Implementação:** tudo especificado em `EDITAR_AQUI.md`.
3. **Guarda não-interativa**: em headless, forçar `DEBUG_PAUSAS_LOOP=False` e exigir `PJEPLUS_DRIVER/FLUXO`.
4. **Pendentes de teste empírico** (rodar fluxo real, não presumir): upload de arquivo na juntada, seleção de destinatários PEC, datepicker, fechamento de abas secundárias.

Descartados: overlay buster (já existe), CKEditor (já `setData`), SISB `input()` (não existe).

## 5. Ordem sugerida

1. Implementar `headless.py` (clipboard) + teste com a sonda.
2. Resolver recovery headless.
3. Rodar Mandado → P2B → PEC em headless e registrar falhas reais; só então decidir ajustes por fluxo.
