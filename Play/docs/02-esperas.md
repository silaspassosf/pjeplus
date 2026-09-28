# 02 — Vocabulário de espera (`Fix/espera.py`)

Contrato do vocabulário que **todas** as etapas usam. Fica na raiz, não em
`play/`, porque serve aos dois motores: em Selenium usa poll; em Playwright o
`pjeplay/nativo.py` troca a implementação por auto-wait orientado a evento.

Módulo de negócio **nunca** chama Playwright direto. Chama isto.

```python
from Fix import espera        # sempre no topo do módulo (regra P8)
```

---

## A garantia

> Toda função é limitada pelo `teto`. Se a condição nunca ocorrer, o custo é
> **idêntico** ao código original. Nunca mais lenta, nunca menos confiável.

O `teto` de uma conversão é **exatamente** o valor que já estava no `sleep` ou
no `WebDriverWait`. Nunca ajuste.

Nenhuma função levanta exceção. Todas devolvem `bool` (ou o elemento / `None`).

---

## Estado de implementação

### ✅ Implementadas

| Função | Devolve | Espera até |
|---|---|---|
| `ate_aparecer(driver, seletor, teto=2.0)` | `bool` | algum elemento visível |
| `ate_sumir(driver, seletor, teto=2.0)` | `bool` | nenhum visível |
| `ate_habilitar(driver, seletor, teto=2.0)` | `bool` | algum visível **e** habilitado |
| `ate_desabilitar(driver, seletor, teto=2.0)` | `bool` | nenhum habilitado |
| `ate_texto(driver, seletor, texto, teto=2.0)` | `bool` | algum contém `texto` |
| `ate_js(driver, expressao, teto=2.0)` | `bool` | predicado JS verdadeiro |
| `assentar(driver, teto=2.0, motivo="")` | `bool` | a interface aquietar |
| `pausa(driver, segundos, motivo="")` | `True` | — espera cega deliberada |
| `e_xpath(seletor)` | `bool` | — utilitário |

### 🔴 Pendentes — implementadas na etapa **E1**

Necessárias para converter `WebDriverWait`. Até E1 existir, uma etapa que
precise delas deve **parar e reportar**, não improvisar.

| Função | Devolve | Substitui |
|---|---|---|
| `elemento(driver, seletor, teto=10, visivel=True)` | elemento ou `None` | `WebDriverWait(...).until(EC.visibility_of_element_located / presence_of_element_located)` |
| `elementos(driver, seletor, teto=10)` | `list` (vazia se nada) | `EC.presence_of_all_elements_located` |
| `ate_url(driver, trecho, teto=10)` | `bool` | `EC.url_contains` |
| `ate_abas(driver, quantidade, teto=10)` | `bool` | `EC.number_of_windows_to_be` |
| `ate_obsoleto(driver, elemento, teto=10)` | `bool` | `EC.staleness_of` |

---

## Qual usar

```
A espera é deliberada? (throttle, anti-detecção, ritmo, jitter)
  → NÃO CONVERTA. Deixe o time.sleep como está.

Está dentro de `except` ou de laço de tentativa?
  → NÃO CONVERTA. É política de retry.

Você precisa do elemento logo em seguida?
  → espera.elemento(...)   e use-o IMEDIATAMENTE (ele fica obsoleto)

O código adjacente revela um seletor sem ambiguidade?
  → a `ate_*` correspondente, com o MESMO seletor que o código já usa

O predicado é arbitrário?
  → espera.ate_js(...)     ( __pjeEls(sel) aceita CSS e XPath )

Nada disso?
  → espera.assentar(driver, N)   ← resultado correto, não fracasso
```

`assentar` **já entrega o ganho do Playwright**: em Selenium dorme o teto; no
backend Playwright aguarda quiescência sustentada (Angular estável + sem
spinner por 150 ms) e tipicamente retorna em 50–200 ms. Trocar por uma `ate_*`
precisa é melhoria adicional, **não** pré-requisito.

> Deixar `assentar` onde a condição não é óbvia é a decisão certa.
> Prefira 10 conversões corretas a 40 chutadas.

---

## Detalhes que já causaram bug

**XPath.** `document.querySelectorAll` estoura com sintaxe XPath, e o projeto
usa `By.XPATH` em ~117 pontos. O helper `__pjeEls(sel)` — disponível dentro de
qualquer expressão passada a `ate_js` — detecta e usa `document.evaluate`. Sem
ele, um XPath devolveria `False` na hora, silenciosamente: pior que o `sleep`
que substituiu.

**Quiescência sustentada.** `assentar` no Playwright não pode testar "Angular
estável" instantaneamente: logo após um clique a requisição ainda não saiu, o
Angular está momentaneamente estável, e a função retornaria cedo entregando uma
tela que ainda vai mudar — furo que o `sleep` original não tinha. Por isso exige
150 ms contínuos de quietude.

**Import faltando.** A migração mecânica já produziu um `NameError` mascarado
por `except Exception: pass` em `atos/judicial_helpers.py`. Ao terminar qualquer
etapa, confirme:

```bash
for f in $(grep -rl "espera\." --include=*.py PEC Mandado atos Fix SISB Prazo); do grep -q "from Fix import espera" "$f" || echo "FALTA: $f"; done
```

---

## Ferramenta de apoio

`play/migrar_sleeps.py` faz a troca mecânica `time.sleep(N)` →
`espera.assentar(driver, N)`, recusando por AST o que não deve tocar (retry,
throttle, função deliberada, sem driver no escopo, `SISB/Core/`).

```bash
py play/migrar_sleeps.py             # dry-run
py play/migrar_sleeps.py --aplicar
```
