# Plano 2 — Estrutura Headless

**Status:** Diagnóstico concluído — patches priorizados por risco  
**Risco:** Médio (alterações em Fix/selenium_base/ podem afetar todas as chamadas de click)  
**Modelo alvo:** GPT-4.1 via PJE.md (Surgical Mode)

---

## Diagnóstico

### Situação atual
O `headless_helpers.py` existe com funções corretas (`click_headless_safe`,
`scroll_to_element_safe`, `limpar_overlays_headless`, etc.) **mas nenhum módulo
de negócio o importa.** O `Fix/selenium_base/element_interaction.py` usa `ActionChains`
como estratégia 3 de click — isso funciona em modo visual mas trava em headless.

### Mapa de riscos headless

| Arquivo | Risco | Causa |
|---|---|---|
| `Fix/selenium_base/element_interaction.py` linha 610 | ALTO | `ActionChains(driver).click()` — falha silenciosa em headless |
| `SISB/ordens/processor.py` linhas 214, 266, 276 | MÉDIO | `ActionChains.send_keys(Keys.ESCAPE)` — pode ser substituído por JS |
| `atos/comunicacao_navigation.py` linhas 39, 92 | MÉDIO | `time.sleep(0.2-0.3)` sem MutationObserver |
| `x.py` `_executar_*_bloco` | BAIXO | `time.sleep(3)` após resetar_driver (já documentado em plano_imports.md) |

### Funções disponíveis e NÃO usadas (headless_helpers.py)
- `click_headless_safe(driver, selector, by, timeout)`
- `scroll_to_element_safe(driver, element)`
- `find_element_headless_safe(driver, selector, by, timeout)`
- `aguardar_elemento_headless_safe(driver, selector, timeout)`
- `limpar_overlays_headless(driver)`
- `is_headless_mode(driver)` — detecção automática

---

## Estratégia Incrementa

**Princípio:** Não quebrar o mode visível ao corrigir o headless. A função
`is_headless_mode(driver)` permite branches condicionais.

---

### Etapa 2.1 — ActionChains como fallback de click (element_interaction.py)

**Arquivo:** `Fix/selenium_base/element_interaction.py`  
**Ação:** Substituir `ActionChains(driver).click()` por JS `arguments[0].click()`
na estratégia 3. ActionChains depende de coordenadas físicas de tela.

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: Fix/selenium_base/element_interaction.py
operacao: replace
ancora: "_tentar_click_actionchains"
```

```python
# ANTES
def _tentar_click_actionchains(driver: WebDriver, element: WebElement, log: bool) -> bool:
    """
    Estratégia 3: ActionChains click.
    """
    try:
        if log:
            print(f"[SAFE_CLICK] Tentando click via ActionChains")
        actions = ActionChains(driver)
        actions.move_to_element(element).click().perform()
        if log:
            print(f"[SAFE_CLICK] Click ActionChains bem sucedido!")
        return True
    except Exception as e:
        if log:
            print(f"[SAFE_CLICK] Click ActionChains falhou: {str(e)}")
        return False
```

```python
# DEPOIS — JS click é headless-safe e funciona igual em visível
def _tentar_click_actionchains(driver: WebDriver, element: WebElement, log: bool) -> bool:
    """
    Estratégia 3: JS click (headless-safe, substitui ActionChains).
    """
    try:
        if log:
            print(f"[SAFE_CLICK] Tentando click via JS (headless-safe)")
        driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'}); arguments[0].click();", element)
        if log:
            print(f"[SAFE_CLICK] Click JS bem sucedido!")
        return True
    except Exception as e:
        if log:
            print(f"[SAFE_CLICK] Click JS falhou: {str(e)}")
        return False
```

---

### Etapa 2.2 — ActionChains.send_keys(ESCAPE) em SISB/ordens/processor.py

**Arquivo:** `SISB/ordens/processor.py`  
**Ação:** Substituir `ActionChains(driver).send_keys(Keys.ESCAPE).perform()` por
`driver.execute_script("document.activeElement.blur()")` ou `driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)`.

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: SISB/ordens/processor.py
operacao: replace
ancora: "ActionChains(driver).send_keys(Keys.ESCAPE).perform()" (todas as ocorrências)
```

```python
# ANTES
ActionChains(driver).send_keys(Keys.ESCAPE).perform()
```

```python
# DEPOIS
driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
```

> **Nota para Surgical Mode:** substituir as 3 ocorrências. Remover a linha
> `from selenium.webdriver.common.action_chains import ActionChains` se não houver
> mais usos.

---

### Etapa 2.3 — Downloads headless-safe (x.py criar_driver_pc)

**Arquivo:** `x.py`  
**Condição:** Falta `browser.helperApps.neverAsk.saveToDisk` e `browser.download.folderList`
no `criar_driver_pc` headless, presente no VT mas não no PC.

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: x.py
operacao: insert_after
ancora: 'options.set_preference("media.volume_scale", "0.0")'
```

```python
        # Downloads headless-safe
        if headless:
            options.set_preference("browser.download.folderList", 2)
            options.set_preference("browser.download.manager.showWhenStarting", False)
            options.set_preference("browser.download.dir", os.path.join(os.path.dirname(__file__), "downloads"))
            options.set_preference("browser.helperApps.neverAsk.saveToDisk",
                "application/pdf,application/octet-stream,application/zip,"
                "application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            options.set_preference("pdfjs.disabled", True)
```

---

### Etapa 2.4 — Substituir `time.sleep` em comunicacao_navigation.py

**Arquivo:** `atos/comunicacao_navigation.py`  
**Ação:** Importar e usar `aguardar_renderizacao_nativa`.

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: atos/comunicacao_navigation.py
operacao: replace
ancora: "import time"
```

```python
# ANTES
import time
```

```python
# DEPOIS
from Fix.utils.observer import aguardar_renderizacao_nativa
```

> **Nota para Surgical Mode:** substituir `time.sleep(0.2)` e `time.sleep(0.3)` por
> `aguardar_renderizacao_nativa(driver)` — verificar qual driver está disponível
> no contexto da função antes de aplicar.

---

## Verificação

```bash
py -m py_compile Fix/selenium_base/element_interaction.py
py -m py_compile SISB/ordens/processor.py
py -m py_compile x.py
py -m py_compile atos/comunicacao_navigation.py
```
