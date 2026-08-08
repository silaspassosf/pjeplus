# E7 — `Prazo/` (inclui P2B)

**Leia antes:** `00-contexto.md`, `02-esperas.md`, `01-traducao.md` §1 e §5.

## Arquivos exclusivos

```
Prazo/**    exceto Prazo/p2b_fluxo_prescricao.py
```

`p2b_fluxo_prescricao.py` é satélite legado fora do caminho principal
(`idx.md` §4). Não edite.

Reais: `loop_orquestrador.py`, `loop_lote.py`, `loop_execucao_final.py`,
`p2b_gateway.py`, `p2b_documentos.py`, `p2b_regras_execucao.py`,
`p2b_fluxo_lazy.py`.

## Volume

26 `WebDriverWait`, 21 `EC.`, 5 `time.sleep`, 1 `espera.assentar`.

Praticamente tudo aqui é conversão de `WebDriverWait`/`EC` — é a etapa mais
"pura" nesse sentido.

## Contexto dos fluxos

- **Prazo (ciclos 1–3)**: `loop_orquestrador.py` → `loop_lote.py` →
  `loop_execucao_final.py`. Muita manipulação de painel: filtros de fase, marcar
  todos, abrir suitcase, movimentar destino. Sinais típicos: `mat-spinner`,
  `mat-table`/`mat-row`, `div.cdk-overlay-pane` (mat-select de destino).
- **P2B**: `p2b_gateway.py` (API GIGS + extração) → `p2b_documentos.py`
  (timeline DOM) → regras por regex. É o fluxo mais leve e de menor risco.

## Cuidados específicos

- **`p2b_gateway.py:200`** — comentário diz "pequena espera para carregar
  timeline", e a função chamada depois é caixa-preta. Sem sinal DOM. Deixe
  `assentar`.
- **Filtros de painel** (`loop_lote.py`): `aplicar_filtro_100` e `filtrofases`
  vivem em `Fix/core.py` (E1). Aqui só as esperas dos chamadores.
- Muitos `EC.presence_of_all_elements_located` para tabelas — o alvo natural é
  `espera.elementos`, **pendente de E1**. Se não existir, deixe e reporte.

## Regras

- `teto` = exatamente o valor que já estava. Nunca ajuste.
- Não converta espera em `except` nem em laço de tentativa.
- Use o **mesmo seletor** que o código já usa logo antes/depois.
- Na dúvida, deixe.
- Se precisar de função pendente de E1, pare naquele sítio e reporte.

## Validação

```bash
python -m py_compile $(git diff --name-only Prazo/)
```

```bash
python -c "import Prazo.loop_orquestrador, Prazo.loop_lote, Prazo.loop_execucao_final, Prazo.p2b_gateway, Prazo.p2b_documentos; print('OK')"
```

```bash
py play/smoke.py --projeto
```

## Relatório

```
por arquivo: waits N/N, EC N/N, sleeps N/N, assentar refinados N/N
por conversão: <arquivo>:L<n>  <antes> -> <depois>  | porque: <evidência>
deixados: agrupados por motivo
bloqueado por E1: <lista — especialmente espera.elementos>
VALIDAÇÃO smoke: __/91 | py_compile: ok | imports: ok
```
