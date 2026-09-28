# E4 — `atos/`

**Leia antes:** `00-contexto.md`, `02-esperas.md`, `01-traducao.md` §1 e §5.

## Arquivos exclusivos

```
atos/**            (todos, menos as fachadas listadas abaixo)
```

Não edite as fachadas — são re-exportação pura (ver `idx.md` §6):
`atos/judicial.py`, `atos/movimentos.py`, `atos/regras.py`,
`atos/anexos/core.py`, `atos/anexos/anexos_wrappers.py`.

## Volume — o maior bolsão do projeto

69 `WebDriverWait`, 72 `EC.`, 13 `time.sleep`, 16 `espera.assentar` a refinar.

Implementações reais (onde o trabalho está): `judicial_fluxo.py`,
`judicial_navegacao.py`, `judicial_modelos.py`, `judicial_utils.py`,
`judicial_helpers.py`, `comunicacao.py`, `comunicacao_coleta.py`,
`comunicacao_navigation.py`, `comunicacao_preenchimento.py`,
`comunicacao_destinatarios.py`, `comunicacao_finalizacao.py`,
`movimentos_fluxo.py`, `movimentos_navegacao.py`, `movimentos_sobrestamento.py`,
`movimentos_fimsob.py`, `movimentos_despacho.py`, `movimentos_chips.py`,
`wrappers_utils.py`, `anexos_sigilo.py`, `core.py`.

## Sinais conhecidos deste módulo

O `atos/` é onde o PJe dá as confirmações mais explícitas — aproveite:

```
simple-snack-bar                          snackbar de confirmação
  texto 'Ato elaborado com sucesso'           → ato finalizado
  texto 'Modelo de documento inserido com sucesso'  → modelo inserido
snack-bar-container.success simple-snack-bar span   variante com sucesso
div.cdk-overlay-pane                      overlay do mat-select (animando)
.cdk-overlay-backdrop                     backdrop
mat-dialog-container                      modal
mat-spinner                               loading
button[aria-label="Salva as alterações"]  salvar destinatários
i.fa.fa-window-close.btn-fechar           fechar (é <i>: use ate_aparecer,
                                          não ate_habilitar — <i> não tem
                                          estado disabled real)
```

O snackbar é **confirmação definitiva**: quando ele aparece, a ação terminou.
`espera.ate_texto(driver, 'simple-snack-bar', '<texto>', teto=N)` é a conversão
mais valiosa deste módulo.

## Cuidados específicos

- **Botão de confirmação genérico**: em `movimentos_chips.py` e
  `movimentos_navegacao.py` o "Sim" só é localizável por seletor `button`
  genérico. Risco real de falso positivo — **deixe `assentar`**.
- **Espera por nova aba** (`movimentos_sobrestamento.py` ~L175): depende de
  `window_handles`, não de DOM. Nenhuma `ate_*` expressa isso hoje; precisa de
  `espera.ate_abas`, que é de E1. Se não existir, reporte e deixe.
- **Buffers de transição Angular** (`judicial_fluxo.py` ~L504, L803): sem
  seletor único subsequente. Deixe `assentar`.
- `judicial_helpers.py` já teve um `NameError` mascarado por `except`
  genérico — confirme o `from Fix import espera` no topo de todo arquivo tocado.

## Regras

- `teto` = exatamente o valor que já estava. Nunca ajuste.
- Não converta espera em `except` nem em laço de tentativa.
- Use o **mesmo seletor** que o código já usa logo antes/depois.
- `ate_habilitar` só para elementos com estado `disabled` real (`button`,
  `input`). Para `<i>`, `<span>`, `<a>`: `ate_aparecer`.
- Na dúvida, deixe. Prefira 20 conversões corretas a 60 chutadas.
- Se precisar de função pendente de E1, pare naquele sítio e reporte.

## Validação

```bash
python -m py_compile $(git diff --name-only atos/)
```

```bash
python -c "import atos.judicial_fluxo, atos.comunicacao, atos.movimentos_fluxo, atos.wrappers_ato, atos.wrappers_pec, atos.wrappers_mov, atos.regras; print('OK')"
```

```bash
py play/smoke.py --projeto
```

## Relatório

```
por arquivo: waits N/N, EC N/N, sleeps N/N, assentar refinados N/N
por conversão: <arquivo>:L<n>  <antes> -> <depois>  | porque: <evidência>
deixados: agrupados por motivo
bloqueado por E1: <sítios que precisam de ate_abas/elemento/...>
VALIDAÇÃO smoke: __/91 | py_compile: ok | imports: ok
```
