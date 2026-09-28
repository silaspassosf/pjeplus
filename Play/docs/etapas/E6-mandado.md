# E6 — `Mandado/`

**Leia antes:** `00-contexto.md`, `02-esperas.md`, `01-traducao.md` §1 e §5.

## Arquivos exclusivos

```
Mandado/**    exceto Mandado/core.py e Mandado/processamento.py
```

`Mandado/core.py` e `Mandado/processamento.py` são **legado fora do caminho de
execução** (`idx.md` §4). Não edite.

Reais: `entrada_api.py`, `fluxo_argos.py`, `apoio_fluxos.py`, `anexos_argos.py`,
`regras.py`, `fluxo_ui.py`.

## Volume

15 `WebDriverWait`, 10 `EC.`, 3 `time.sleep`, 13 `espera.assentar`.

## Cuidados específicos

- **XPath é comum aqui.** `anexos_argos.py:119` (`btn_salvar` via `By.XPATH`) e
  `fluxo_ui.py:138, 146` (`//button[contains(...)]`) usam XPath. O vocabulário
  **já aceita XPath** — `__pjeEls` detecta e usa `document.evaluate`. Pode
  converter usando o mesmo XPath que o código já usa.
- **`anexos_argos.py:126`** — um `EC.staleness_of(modal)` logo acima já
  confirmou que o modal sumiu; o `assentar` seguinte é buffer sem alvo próprio.
  Converta o `EC.staleness_of` (→ `espera.ate_obsoleto`, pendente de E1), deixe
  o `assentar`.
- **`apoio_fluxos.py:183`** — laço de retry manual em torno de
  `_tem_sigilo_link()`. O `assentar` é a cadência do poll, não a espera. Deixe.
- **SISBAJUD do Mandado não é browser.** `processar_sisbajud(texto_certidao)`
  recebe *texto* e analisa a certidão de devolução. Não há espera a converter
  ali, e não confunda com o SISB do PEC (que é E8).

## Regras

- `teto` = exatamente o valor que já estava. Nunca ajuste.
- Não converta espera em `except` nem em laço de tentativa.
- Use o **mesmo seletor** (CSS ou XPath) que o código já usa logo antes/depois.
- Na dúvida, deixe.
- Se precisar de função pendente de E1 (`ate_obsoleto`, `ate_abas`, `elemento`),
  pare naquele sítio e reporte.

## Validação

```bash
python -m py_compile $(git diff --name-only Mandado/)
```

```bash
python -c "import Mandado.entrada_api, Mandado.fluxo_argos, Mandado.apoio_fluxos, Mandado.regras; print('OK')"
```

```bash
py play/smoke.py --projeto
```

## Relatório

```
por arquivo: waits N/N, EC N/N, sleeps N/N, assentar refinados N/N
por conversão: <arquivo>:L<n>  <antes> -> <depois>  | porque: <evidência>
deixados: agrupados por motivo
bloqueado por E1: <lista>
VALIDAÇÃO smoke: __/91 | py_compile: ok | imports: ok
```
