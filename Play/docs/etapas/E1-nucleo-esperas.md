# E1 — Fechar o vocabulário de espera e converter `Fix/core.py`

**Leia antes:** `00-contexto.md`, `02-esperas.md`, `01-traducao.md` §1.

## Arquivos exclusivos desta etapa

```
Fix/espera.py
Fix/core.py
play/pjeplay/nativo.py
```

Não toque em mais nada. Outras janelas estão em `Fix/utils.py`, `atos/`, `PEC/`…

---

## Por que esta etapa existe

`Fix/core.py` é o arquivo mais atravessado do projeto e tem **34 `time.sleep` e
31 `WebDriverWait`** — todos no caminho quente de Mandado, PEC e P2B. Ele ficou
de fora da migração mecânica por uma dependência circular:

```
Fix/espera.py  --importa-->  Fix.core.aguardar_renderizacao_nativa
Fix/core.py    --precisaria importar-->  Fix.espera        ❌ ciclo
```

E1 quebra o ciclo e depois converte o core.

---

## Parte 1 — Tornar `Fix/espera.py` autossuficiente

`ate_aparecer`, `ate_sumir` e `ate_habilitar` hoje delegam para
`aguardar_renderizacao_nativa` (que vem do `core`). Reimplemente as três sobre
`ate_js`, que só precisa de `driver.execute_script`. Aí o import do `core` sai e
o ciclo deixa de existir.

Os predicados já estão prontos no próprio arquivo:

```python
_VISIVEL    = "el => el.getClientRects().length > 0"
_HABILITADO = ("el => el.getClientRects().length && !el.disabled"
               " && el.getAttribute('aria-disabled') !== 'true'")
```

E o caminho XPath já usa exatamente essa forma:

```python
ate_js(driver, "__pjeEls(%r).some(%s)" % (seletor, _VISIVEL), teto)
```

Ou seja: basta remover a bifurcação `if e_xpath(seletor)` e usar sempre o ramo
`ate_js`, já que `__pjeEls` trata CSS e XPath.

> ⚠️ **Armadilha já cometida uma vez:** não remova o
> `from Fix.core import aguardar_renderizacao_nativa` antes de reimplementar as
> três funções. O módulo continua importando (o `NameError` só aparece em
> runtime), então o erro passa despercebido pelo `py_compile` e pelo `import`.
> Reimplemente primeiro, remova o import depois.

**Plano B, se a reimplementação der trabalho:** `Fix/core.py` já usa import
tardio para quebrar ciclo — `from .utils import login_cpf, ...` fica no meio do
arquivo, não no topo (por volta da L2446), justamente porque `Fix/utils.py`
importa do `core`. É precedente estabelecido no próprio arquivo. Preferir a
solução limpa (Parte 1), mas o import tardio de `espera` dentro do `core.py` é
aceitável se necessário — documente a escolha no relatório.

Depois disso, ajuste `play/pjeplay/nativo.py`:

- `_ALVOS["Fix.espera"]` não deve mais listar `aguardar_renderizacao_nativa`
  (a função sai do módulo);
- confirme que `ate_js` e `assentar` continuam na lista — são o caminho rápido.

`Fix/core.py` **continua** exportando `aguardar_renderizacao_nativa`: dezenas de
módulos a importam de lá. Não a remova, não a mova.

## Parte 2 — Implementar as funções que faltam

Especificação em `02-esperas.md` (seção "Pendentes"). Todas seguem o mesmo
contrato: limitadas pelo `teto`, sem levantar exceção.

```python
def elemento(driver, seletor, teto=10, visivel=True): ...   # elemento ou None
def elementos(driver, seletor, teto=10): ...                # list (vazia se nada)
def ate_url(driver, trecho, teto=10): ...                   # bool
def ate_abas(driver, quantidade, teto=10): ...              # bool
def ate_obsoleto(driver, elemento, teto=10): ...            # bool
```

Notas de implementação:

- `elemento` / `elementos` devolvem objetos do motor corrente (`WebElement` no
  Selenium, `PWElement` no backend Playwright). Ambos respondem à mesma
  superfície, então o chamador não precisa saber a diferença.
- `ate_obsoleto` no Selenium é "acessar o elemento levanta
  `StaleElementReferenceException`". No Playwright o locator re-resolve e a
  obsolescência praticamente não ocorre — devolver `True` de imediato é
  aceitável e está correto semanticamente.
- Acrescente os nomes novos ao `__all__`.
- Acrescente ao `_ALVOS["Fix.espera"]` do `nativo.py` os que ganharem
  implementação nativa (no mínimo `elemento`, `elementos`, `ate_url`).

Escreva também a versão nativa em `play/pjeplay/nativo.py`:

- `elemento` → `ctx.wait_for_selector(sel, state="visible"|"attached", timeout=...)`
- `elementos` → aguarda o primeiro e devolve `query_selector_all`
- `ate_url` → `page.wait_for_url(lambda u: trecho in (u or ""), timeout=...)`
- `ate_abas` → poll de `len(driver.window_handles)` com `driver.pulsar()`

## Parte 3 — Converter `Fix/core.py`

Só depois das partes 1 e 2.

1. Acrescente `from Fix import espera` no topo (regra P8). Agora não há ciclo.
2. Rode a troca mecânica dos sleeps — remova `"Fix/core.py"` da tupla `PULAR`
   em `play/migrar_sleeps.py`, e então:

   ```bash
   py play/migrar_sleeps.py             # confira o dry-run primeiro
   py play/migrar_sleeps.py --aplicar
   ```

3. Converta os 31 `WebDriverWait` conforme a tabela de `01-traducao.md` §1.

⚠️ **Não converta** o `WebDriverWait` que estiver **dentro da implementação de
`aguardar_renderizacao_nativa`** — é a primitiva; convertê-la para si mesma é
recursão. O mesmo vale para qualquer wait dentro de `esperar_elemento`,
`aguardar_e_clicar`, `safe_click`, `wait_for_*`: são as primitivas que o
vocabulário embrulha. Converta o resto.

---

## Parte 4 — Headless (ver `04-headless.md`)

Duas ações pequenas, no seu arquivo:

1. **Remover o zoom hack** de `Fix/core.py:264-270`
   (`document.body.style.zoom = '60%'`). Existe para contornar divergência de
   geometria do Firefox headless do geckodriver, que o Playwright não tem. No
   caminho Selenium ele raramente é exercitado — o projeto roda visual
   (`headless=False` em 14 pontos, `True` em nenhum). Se preferir não remover,
   deixe-o condicionado a `is_headless_mode(driver)` e reporte.
2. **Tornar `headless` um parâmetro real** nos pontos de criação de driver, em
   vez de literal. Não mude o padrão (`False`) — só permita passar `True`.

## Regras

- `teto` = exatamente o valor que já estava lá. Nunca ajuste.
- Não converta espera em `except` ou laço de tentativa.
- Não remova esperas.
- Na dúvida, `espera.assentar` — deixar é resultado correto.
- `Fix/core.py` é implementação real, não shim. Pode editar.

## Validação

```bash
python -m py_compile Fix/espera.py Fix/core.py play/pjeplay/nativo.py
```

```bash
python -c "import Fix.espera, Fix.core, Fix.utils, Fix.extracao, atos.judicial_fluxo, PEC.runtime_pec, Mandado.entrada_api, SISB.core; print('IMPORTS OK')"
```

```bash
py play/smoke.py --projeto
```

Teste explicitamente que as três funções reimplementadas funcionam com **CSS**
(o caminho que a bifurcação antiga cobria) e não só com XPath — foi exatamente
aí que a tentativa anterior quebrou. O `smoke` já cobre ambos; ele precisa
passar 91/91.

## Relatório

```
PARTE 1  ciclo quebrado: sim/não  | funções reimplementadas: N
PARTE 2  novas: elemento, elementos, ate_url, ate_abas, ate_obsoleto — quais ficaram
PARTE 3  Fix/core.py — sleeps convertidos: N/34  | waits convertidos: N/31
         primitivas deixadas de propósito: <lista>
VALIDAÇÃO  smoke: __/91  | py_compile: ok  | imports: ok
```
