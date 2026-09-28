# E5 — `PEC/`

**Leia antes:** `00-contexto.md`, `02-esperas.md`, `01-traducao.md` §1 e §5.

## Arquivos exclusivos

```
PEC/**
```

Não edite os shims de 2 linhas (`PEC/api_client.py`, `PEC/carta_formatacao.py`,
`PEC/carta_utils.py`, `PEC/core_progresso.py`, `PEC/orquestrador.py`,
`PEC/regras_pec.py`, `PEC/sobrestamento.py`, `PEC/helpers.py`).

## Volume

26 `WebDriverWait`, 41 `EC.`, 3 `time.sleep`, 8 `espera.assentar`.

O grosso desta etapa é `WebDriverWait`/`EC` — os `assentar` já foram analisados
e **nenhum** tinha condição inequívoca. Não force.

## Referência de calibração

`PEC/anexos/anexos_juntador_metodos.py` tem conversões feitas à mão que servem
de padrão:

```python
# o Salvar desabilita enquanto a requisição corre
espera.ate_desabilitar(self.driver, 'button[aria-label="Salvar"]', teto=2)

# o diálogo de preview fecha quando o modelo entra no editor
espera.ate_sumir(driver, 'pje-dialogo-visualizar-modelo', teto=2)

# o Assinar habilita quando o documento está pronto
espera.ate_habilitar(self.driver,
    'button[aria-label="Assinar documento e juntar ao processo"]', teto=3)
```

Leia esse arquivo antes de começar.

## Sinais conhecidos

```
button[aria-label="Salvar"]                       desabilita durante o save
button[aria-label="Assinar documento e juntar ao processo"]
pje-dialogo-visualizar-modelo                     preview de modelo
.documento-visualizacao, #documento, pje-arvore-documento
mat-dialog-container / simple-snack-bar / mat-spinner
CKEDITOR: "typeof CKEDITOR !== 'undefined' && Object.keys(CKEDITOR.instances || {}).length > 0"
```

## Cuidados específicos

- **`regras_execucao.py:511`** — um `WebDriverWait` logo acima já esperou
  `.documento-visualizacao, #documento, pje-arvore-documento`; o `assentar`
  seguinte é buffer extra sem alvo próprio. Converta o `WebDriverWait`, deixe o
  `assentar`.
- **SISBAJUD**: `PEC/regras_execucao.py::_executar_sisbajud` abre um **segundo
  driver** via `SISB.core.iniciar_sisbajud`. As esperas do lado SISB pertencem a
  E8 — aqui só o que estiver em arquivo `PEC/`.
- **`anexos_juntador_helpers.py` ~L241, L246** e **`carta_ecarta_api.py` ~L183**:
  settle pós-scroll/foco, sem seletor. Deixe.
- **`core_pos_carta.py` ~L59, L62**: idem.

## Regras

- `teto` = exatamente o valor que já estava. Nunca ajuste.
- Não converta espera em `except` nem em laço de tentativa.
- Use o **mesmo seletor** que o código já usa logo antes/depois.
- Na dúvida, deixe.
- Se precisar de função pendente de E1, pare naquele sítio e reporte.

## Validação

```bash
python -m py_compile $(git diff --name-only PEC/)
```

```bash
python -c "import PEC.runtime_pec, PEC.regras_execucao, PEC.carta_execucao, PEC.anexos.anexos_juntador_base; print('OK')"
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
