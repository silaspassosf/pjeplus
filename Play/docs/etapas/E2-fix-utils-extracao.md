# E2 — `Fix/utils.py` e `Fix/extracao.py`

**Leia antes:** `00-contexto.md`, `02-esperas.md`, `01-traducao.md` §1.

## Arquivos exclusivos

```
Fix/utils.py
Fix/extracao.py
```

## Volume

| | waits | EC. | sleep | `assentar` já posto |
|---|---:|---:|---:|---:|
| `Fix/utils.py` | 8 | 18 | 2 | 19 |
| `Fix/extracao.py` | 27 | 23 | 8 | 34 |

Duas frentes: converter `WebDriverWait`/`EC` (o grosso) e refinar `assentar`
genérico para `ate_*` preciso onde o código revelar o seletor.

## Contexto dos arquivos

`Fix/utils.py` — login, CKEditor, clipboard, coleta de conteúdo formatado,
recovery de driver.
`Fix/extracao.py` — extração de PDF/HTML, GIGS, BNDT, indexação, destinatários.

Seletores já confirmados nestes arquivos (use-os, não invente):

```
#username                                        login SSO/Keycloak
#previewModeloDocumento                          preview de modelo
pje-conteudo-documento-dialog                    modal de documento
mat-dialog-container pje-documento-original      modal de documento original
.mat-dialog-content, #tituloPostit               post-it / lembrete
textarea[formcontrolname="observacao"]           GIGS
mat-dialog-container                             modal genérico
div[class*="container-loading"] mat-progress-spinner   loading BNDT
.mat-select-panel-wrap                           painel de mat-select
pje-icone-clipboard span[aria-label*="Copiar link de validação"]
```

## Cuidados específicos

- **Digitação caractere a caractere** (`Fix/utils.py` ~L442, L454): o `sleep`
  ali é ritmo de digitação, não espera de UI. **Não converta.**
- **Laços de poll manual** (~L270, L315, L360, L535, L1787): o `assentar` é o
  intervalo entre iterações de um poll que já checa a própria condição.
  Converter para `ate_*` duplicaria a espera. Deixe.
- **CKEditor**: `_get_editable` já valida visível/habilitado antes dos pontos de
  espera adjacentes — não reespere a mesma coisa.
- `Fix/utils.py` tem `WebDriverWait` direto por volta de L764, L892, L909, L2032,
  L2079 (viola a seção 7 do `idx.md`). São alvos legítimos desta etapa.

## Tarefa extra — headless (ver `04-headless.md`)

`Fix/extracao.py::extrair_pdf` (~L189-210) clica no botão copiar do PJe e lê a
área de transferência do **sistema operacional** via `pyperclip.paste()`. Isso é
frágil em headless e impossível numa máquina sem sessão gráfica.

O código já tem o caminho certo, algumas linhas abaixo, como fallback:

```python
pre = modal.find_element(By.CSS_SELECTOR, 'pre')
texto = pre.text
```

**Inverta a ordem:** ler o `<pre>` primeiro; usar o clipboard só se o `<pre>`
não existir ou vier vazio. É mais rápido, mais confiável e headless-safe.
Preserve o `pyperclip` como fallback — não o remova.

## Achado a registrar (não corrigir sem avaliar)

`Fix/extracao.py:2027` define uma segunda `trocar_para_nova_aba`, duplicando a
de `Fix/browser_suporte.py:152`. Quem importa qual depende do import de cada
chamador — e as duas podem ter divergido.

**Não unifique por conta própria** nesta etapa: `Fix/browser_suporte.py` é de E3.
Compare as duas implementações e **reporte** se diferem. Se forem idênticas, a
de `extracao.py` é candidata a virar re-exportação — mas isso é decisão para
depois, com as duas etapas concluídas.

## Regras

- `teto` = exatamente o valor que já estava. Nunca ajuste.
- Não converta espera em `except` nem em laço de tentativa.
- Use o **mesmo seletor** que o código já usa logo antes/depois. Não invente.
- Na dúvida, deixe `assentar` (ou o `WebDriverWait`, se não souber o alvo).
  Deixar é resultado correto.
- Se precisar de `espera.elemento`/`elementos`/`ate_url`/`ate_abas`/`ate_obsoleto`
  e elas ainda não existirem, **pare naquele sítio e reporte** — são de E1.
  Não as implemente (isso editaria `Fix/espera.py`, que não é seu).
- `from Fix import espera` no topo (P8). Confirme que já está lá.

## Validação

```bash
python -m py_compile Fix/utils.py Fix/extracao.py
```

```bash
python -c "import Fix.utils, Fix.extracao; print('OK')"
```

```bash
py play/smoke.py --projeto
```

## Relatório

```
Fix/utils.py     waits: N/8   EC: N/18   assentar refinados: N/19
Fix/extracao.py  waits: N/27  EC: N/23   assentar refinados: N/34
por conversão:   <arquivo>:L<n>  <antes> -> <depois>  | porque: <evidência>
deixados:        quantos e por quê (agrupado por motivo)
bloqueado por E1: <lista de sítios que precisam das funções pendentes>
VALIDAÇÃO        smoke: __/91  | py_compile: ok  | imports: ok
```
