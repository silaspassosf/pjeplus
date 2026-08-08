# 01 — Tradução Selenium → Playwright

Referência de consulta. Não é uma etapa: é o dicionário que as etapas usam.

Consolida o material que estava espalhado nos docs de fase antigos, que foram
removidos por redundância.

---

## 1. A parte que mais importa: `WebDriverWait` + `EC`

São **244 `WebDriverWait` e 249 `EC.`** no escopo. É a maior conversão pendente,
e a que mais muda o comportamento — para melhor.

### Por que o Playwright é mais robusto aqui (três razões distintas)

**a) O piso de latência.** `WebDriverWait` faz *polling*: a cada `poll_frequency`
(padrão **500 ms**) dispara uma requisição HTTP ao geckodriver, que fala com o
Firefox. Um elemento que aparece em 60 ms custa 500 ms. No Playwright a espera é
avaliada **dentro do browser**, em `requestAnimationFrame` — reage ao evento.

**b) A checagem é mais estrita.** `EC.element_to_be_clickable` verifica apenas
*displayed* e *enabled*. Ele **não** verifica se o elemento está coberto por um
overlay, nem se está no meio de uma animação. Por isso é comum um clique passar
pelo `element_to_be_clickable` e mesmo assim estourar
`ElementClickInterceptedException`. A actionability do Playwright checa
*visible + stable (sem animação) + enabled + recebe eventos* e **repete até
passar**. A espera não só é mais rápida: ela verifica mais coisas.

**c) Staleness deixa de existir.** O Angular do PJe re-renderiza o tempo todo.
Um `WebElement` guardado numa variável fica obsoleto e estoura
`StaleElementReferenceException` — daí os 126 blocos de retry do projeto. O
`Locator` do Playwright é uma *consulta*, não um ponteiro: re-resolve a cada uso.

> **Consequência prática para as conversões:** prefira sempre esperar por
> **seletor**, não por elemento já resolvido. `espera.ate_aparecer(d, sel)` é
> mais robusto que guardar o retorno de `espera.elemento(d, sel)` e usá-lo
> depois. Só use o segundo quando precisar do elemento em seguida, e use-o
> imediatamente.

### Tabela de conversão

Escreva sempre no vocabulário do projeto (`Fix/espera.py`) — nunca chame o
Playwright direto num módulo de negócio. O vocabulário funciona nos dois motores.

| Selenium | Vocabulário do projeto |
|---|---|
| `WebDriverWait(d,t).until(EC.presence_of_element_located((By.CSS_SELECTOR,s)))` | `espera.elemento(d, s, teto=t, visivel=False)` |
| `WebDriverWait(d,t).until(EC.visibility_of_element_located((By.CSS_SELECTOR,s)))` | `espera.elemento(d, s, teto=t)` |
| idem, mas o retorno **não** é usado | `espera.ate_aparecer(d, s, teto=t)` ← prefira |
| `WebDriverWait(d,t).until(EC.element_to_be_clickable((By.CSS_SELECTOR,s)))` | `espera.ate_habilitar(d, s, teto=t)` |
| `WebDriverWait(d,t).until(EC.invisibility_of_element_located(...))` | `espera.ate_sumir(d, s, teto=t)` |
| `WebDriverWait(d,t).until_not(EC.presence_of_element_located(...))` | `espera.ate_sumir(d, s, teto=t)` |
| `WebDriverWait(d,t).until(EC.presence_of_all_elements_located(...))` | `espera.elementos(d, s, teto=t)` |
| `WebDriverWait(d,t).until(EC.text_to_be_present_in_element((..,s), txt))` | `espera.ate_texto(d, s, txt, teto=t)` |
| `WebDriverWait(d,t).until(EC.url_contains(x))` | `espera.ate_url(d, x, teto=t)` |
| `WebDriverWait(d,t).until(EC.number_of_windows_to_be(n))` | `espera.ate_abas(d, n, teto=t)` |
| `WebDriverWait(d,t).until(EC.staleness_of(el))` | `espera.ate_obsoleto(d, el, teto=t)` |
| `WebDriverWait(d,t).until(lambda d: <predicado JS>)` | `espera.ate_js(d, "<predicado>", teto=t)` |
| `WebDriverWait(d,t).until(EC.alert_is_present())` | **não converter** — o PJe não usa alertas; ver `00-contexto.md` |
| `time.sleep(n)` com condição identificável | a `espera.ate_*` correspondente, `teto=n` |
| `time.sleep(n)` sem condição identificável | `espera.assentar(d, n)` |
| `time.sleep(n)` deliberado (throttle, anti-detecção) | **não converter** |

> O `teto` recebe **exatamente** o timeout que estava no `WebDriverWait`. Assim
> a conversão nunca piora: no pior caso é o mesmo tempo, no melhor é o evento.

### O que desaparece

Padrões que existiam só para contornar limitações do Selenium e não têm
equivalente porque **não são necessários**:

- `js_base()` + MutationObserver injetado via `execute_async_script`
- zoom hack (`document.body.style.zoom = '60%'`)
- `limpar_overlays_headless` — o Playwright não tem o problema
- `click_headless_safe` — `click()` funciona igual em visible e headless
- cascatas `try css1 / try css2 / try xpath`
- a maior parte dos 126 blocos de retry por `StaleElementReferenceException`

---

## 2. Tipos e ciclo de vida

| Selenium | Playwright |
|---|---|
| `WebDriver` | `Page` (via `PWDriver`, que fala WebDriver) |
| `WebElement` (ponteiro) | `Locator` (consulta, re-resolve) |
| `driver.get(url)` | `page.goto(url)` |
| `driver.current_url` | `page.url` |
| `driver.quit()` | `browser.close(); pw.stop()` |
| `driver.implicitly_wait(n)` | não existe — auto-wait por locator |

Em módulo de negócio isso é invisível: o `PWDriver` implementa a superfície do
WebDriver. `driver.page` é a escotilha para a `Page` crua quando código novo
quiser usar locators direto.

---

## 3. Localização

| Selenium | Playwright |
|---|---|
| `find_element(By.CSS_SELECTOR, s)` | `page.locator(s)` |
| `find_element(By.XPATH, x)` | `page.locator(f'xpath={x}')` |
| `find_element(By.ID, i)` | `page.locator(f'#{i}')` |
| `element.find_element(...)` | `locator.locator(s)` (sub-locator) |
| — | `get_by_role`, `get_by_label`, `get_by_placeholder`, `get_by_text` |
| — | `.filter(has_text=...)`, `:has-text()`, `:visible` |

⚠️ `document.querySelectorAll` **estoura com sintaxe XPath**. O vocabulário de
espera já trata isso (`__pjeEls` usa `document.evaluate` quando detecta XPath),
mas qualquer JS novo que você escrever precisa da mesma cautela.

---

## 4. Interação

| Selenium | Playwright |
|---|---|
| `element.click()` | `locator.click()` (auto-scroll + actionability inclusos) |
| `execute_script("arguments[0].click()", el)` | `locator.click(force=True)` |
| `element.send_keys('t')` | `locator.fill('t')` (limpa e dispara input/change) |
| `element.send_keys('t')` (append) | `locator.press_sequentially('t')` |
| `element.send_keys(Keys.ENTER)` | `locator.press('Enter')` |
| `element.clear()` | `locator.clear()` |
| `element.text` | `locator.inner_text()` |
| `ActionChains(d).move_to_element(e).click().perform()` | `locator.click()` |
| `execute_script("arguments[0].scrollIntoView()", el)` | `locator.scroll_into_view_if_needed()` |

---

## 5. Angular Material — receitas PJe

Tudo isto já está implementado em `play/pjeplay/pje.py`. Use as funções de lá;
as receitas cruas ficam aqui só como referência do que elas fazem.

### mat-select (risco R2 — timing do overlay CDK)

As `mat-option` **não** estão no DOM quando o overlay abre. Clicar cedo demais
não acha a opção, ou o overlay fecha sozinho.

```python
pje.mat_select(page, 'mat-select[formcontrolname="destinos"]', 'Análise')
# abre → espera div.cdk-overlay-pane visível → espera 1ª mat-option
# → clica → confirma que o overlay fechou
```

Use `exato=True` quando uma opção for prefixo de outra (`Execução` vs
`Execução Fiscal`).

### Estabilização Angular (risco R4)

```python
pje.aguardar_angular(page, timeout=10)
```

Usa `getAllAngularTestabilities`. Em build de produção com otimizações essa API
some — o fallback é ausência de `mat-spinner`. Degrada, não trava.

### CKEditor (risco R3)

```python
pje.ckeditor_versao(page)      # 'ck4' | 'ck5' | None — detecta em runtime
pje.ckeditor_definir(page, html)
pje.ckeditor_obter(page)
```

### Abas

```python
nova = pje.abrir_em_nova_aba(page, lambda: page.locator('#abrir').click())
```

`expect_page` arma a escuta **antes** do clique. É isso que elimina a corrida do
padrão `window_handles` antes/depois — a aba não pode abrir e fechar entre duas
leituras.

### Outros

```python
pje.mat_input(page, sel, valor)          # fill dispara os eventos do Angular
pje.mat_checkbox(page, sel, marcar=True) # sem toggle indevido
pje.mat_data(page, sel, '15/01/2025')    # preenche e fecha o picker
pje.esperar_spinner(page)                # True também se nunca apareceu
pje.abrir_modal(page) / pje.fechar_modal(page)
pje.linha_tabela(page, '12345')          # locator lazy da linha
pje.filtro_100(page)
pje.acesso_negado(page) / pje.sessao_expirada(page)
```

---

## 6. API REST

| Selenium | Playwright |
|---|---|
| `session_from_driver(driver)` | **funciona sem alteração** — usa `get_cookies()` e `current_url`, que o `PWDriver` implementa |
| — | `api.requisicao(driver)` → `APIRequestContext`: auth compartilhada com a aba, sem copiar cookie |
| adivinhar pelo DOM quando o XHR terminou | `api.esperar_resposta(driver, padrao, acao)` |
| — | `api.esperar_conclusao(driver, padrao, acao)` → bool |
| — | `api.registrar_trafego(driver, filtro)` → diagnóstico |

`page.route()` **não** alcança o `APIRequestContext` — a requisição sai fora da
aba. Para interceptar, roteie no contexto (`driver.context.route`).

---

## 7. Exceções

| Selenium | Playwright |
|---|---|
| `TimeoutException` | `playwright.sync_api.TimeoutError` |
| `NoSuchElementException` | `locator.count() == 0` |
| `StaleElementReferenceException` | **não existe** — locator re-resolve |
| `ElementClickInterceptedException` | `locator.click(force=True)` ou remover overlay |
| `WebDriverException` | `playwright.sync_api.Error` |

A camada de compatibilidade (`play/pjeplay/errors.py`) traduz nos dois sentidos,
então `except NoSuchElementException` continua funcionando no backend Playwright.
