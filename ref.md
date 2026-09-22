## Causa principal

Sua LLM está “corrigindo” `comunicacao_preenchimento.py` para Selenium porque esse arquivo ainda expõe uma **interface Selenium explícita**, mesmo quando o projeto roda com Playwright por baixo.

No arquivo aparecem vários sinais fortes:

- `from selenium.webdriver.common.by import By`
- `from selenium.webdriver.remote.webdriver import WebDriver`
- `driver.find_elements(...)`
- `driver.execute_script(...)`
- `driver.send_keys(...)`
- `driver.window_handles`
- `time.sleep(...)`
- funções tipadas como `driver: WebDriver`
- imports diretos de `Fix.core`, que possuem compatibilidade Selenium

Para um modelo de linguagem, isso parece um arquivo Selenium tradicional. Ele não “enxerga” automaticamente que `pjeplay.compat` substitui o Selenium e que `pjeplay.nativo.aplicar()` troca os helpers por implementações Playwright. 

## O problema arquitetural

Seu projeto possui **três camadas diferentes**, e elas estão misturadas:

| Camada | Papel | Problema atual |
|---|---|---|
| Playwright nativo | `Page`, `Locator`, auto-wait, `expect_page` | Existe principalmente em `pje.py` |
| Compatibilidade | `PWDriver` simulando Selenium | Faz o projeto antigo continuar funcionando |
| Código de negócio | `comunicacao_preenchimento.py` | Ainda usa APIs Selenium e JS diretamente |

O índice do projeto informa que o backend padrão é Playwright, mas através de uma superfície compatível com WebDriver. O comando normal é `py pw.py`, enquanto `py pw.py --selenium` serve para o baseline Selenium. 

Além disso, o próprio `nativo.py` explica que os helpers de `Fix/` são substituídos por versões Playwright nativas. Porém, isso só acontece para funções que passam pela camada de patch. Chamadas diretas como:

```python
driver.execute_script(...)
driver.find_elements(...)
driver.find_element(...)
driver.send_keys(...)
```

continuam parecendo Selenium e podem continuar usando comportamento compatível, não necessariamente o melhor comportamento nativo do Playwright. 

## Por que ela coloca esperas fixas

A LLM está reagindo a estes padrões:

```python
time.sleep(0.3)
```

```python
espera.ate_aparecer(..., teto=0.3)
```

```python
while time.monotonic() < deadline:
```

```python
for tentativa in range(1, max_tentativas + 1):
```

Mesmo que algumas esperas tenham sido melhoradas, o modelo identifica o estilo geral como:

> “Aguardar alguns milissegundos, consultar DOM, tentar novamente.”

Isso é típico de Selenium legado.

Também há comentários no código que reforçam essa interpretação:

```python
# Buffer curto pos-click
# no primeiro select da pagina...
```

e:

```python
# Pequena espera/trigger adicional...
time.sleep(0.3)
```

A LLM tende a preservar esse padrão porque ele parece necessário para resolver corridas de interface, especialmente em Angular Material, CDK Overlay e CKEditor.

## Outro problema: sua camada nativa ainda está parcialmente Selenium

Mesmo em `nativo.py`, há decisões que parecem Playwright, mas não aproveitam completamente a semântica nativa:

```python
handle = driver._ctx.wait_for_selector(...)
handle.evaluate("el => el.click()")
```

e:

```python
element._handle.evaluate("el => el.click()")
```

Isso usa Playwright internamente, mas ainda opera com `ElementHandle` e clique via JavaScript. O caminho mais idiomático seria trabalhar com `Locator`:

```python
locator = page.locator(seletor).first
locator.wait_for(state="visible")
locator.click()
```

Seu próprio `pje.py` já segue mais corretamente esse padrão em funções como `mat_select`, `mat_input`, `mat_checkbox`, `abrir_em_nova_aba` e `ckeditor_definir`. 

## O ponto mais importante

Você tem duas estratégias coexistindo:

### Compatibilidade

```text
Fluxo antigo
→ Fix.core
→ PWDriver
→ Playwright por baixo
```

### Playwright nativo

```text
Fluxo novo
→ Page/Locator
→ pje.py
→ Playwright diretamente
```

O arquivo `comunicacao_preenchimento.py` está na primeira estratégia. Por isso a LLM continua propondo Selenium: **a arquitetura permite e até incentiva isso**.

O fato de o navegador real ser Playwright não transforma automaticamente o código-fonte em código Playwright nativo.

## Inconsistências específicas no arquivo

### 1. `driver: WebDriver`

```python
def executar_preenchimento_minuta(driver: WebDriver, ...):
```

Isso informa diretamente à LLM que o objeto é um WebDriver Selenium.

Troque por um protocolo abstrato ou por um tipo neutro:

```python
from typing import Any

def executar_preenchimento_minuta(driver: Any, ...):
```

Melhor ainda:

```python
from playwright.sync_api import Page

def executar_preenchimento_minuta(page: Page, ...):
```

### 2. `execute_script` espalhado

Exemplos:

```python
driver.execute_script(...)
```

Isso força o modelo a pensar em Selenium, mesmo que o driver seja um adaptador Playwright.

Concentre JavaScript em funções nativas específicas:

```python
def definir_valor_input(page, seletor, valor):
campo = page.locator(seletor).first
campo.fill(str(valor))
```

Use `evaluate()` apenas quando realmente necessário, como para CKEditor ou eventos específicos.

### 3. Busca manual de elementos

Atual:

```python
opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
for opcao in opcoes:
texto_opcao = opcao.get_attribute('innerText') or opcao.text
```

Playwright:

```python
opcoes = page.locator('mat-option[role="option"]')
opcao = opcoes.filter(has_text=valor_desejado).first
opcao.click()
```

Isso fornece auto-wait, re-resolução do DOM e elimina referências obsoletas.

### 4. Uso de `time.sleep`

Mesmo que sejam apenas 300 ms, isso comunica fragilidade:

```python
time.sleep(0.3)
```

Substitua por uma condição observável:

```python
page.locator("div.cdk-overlay-pane").first.wait_for(
state="visible",
timeout=3000,
)
```

Ou, depois da seleção:

```python
page.locator("div.cdk-overlay-pane").first.wait_for(
state="hidden",
timeout=5000,
)
```

### 5. Esperar seletor sem verificar estado correto

O código utiliza:

```python
aguardar_renderizacao_nativa(driver, seletor, 'aparecer', 10)
```

Mas para elementos interativos, “aparecer” pode não ser suficiente. Em Playwright, separe as condições:

```python
botao = page.locator('button[aria-label="Finalizar minuta"]').first
botao.wait_for(state="visible")
expect(botao).to_be_enabled()
```

## Como impedir que a LLM volte ao Selenium

Inclua uma regra explícita no `idx.md` ou em um arquivo de instruções do projeto:

```markdown
## Regra obrigatória para Playwright

Quando o código for executado pelo backend padrão `py pw.py`, os fluxos novos
e os fluxos migrados devem usar Playwright nativo.

É proibido introduzir em arquivos migrados:

- `driver.execute_script`
- `driver.find_element`
- `driver.find_elements`
- `driver.send_keys`
- `driver.window_handles`
- `time.sleep`
- `WebDriverWait`
- `expected_conditions`
- tipagem `WebDriver`

Use:

- `Page`
- `Locator`
- `page.locator(...)`
- `locator.wait_for(...)`
- `locator.click()`
- `locator.fill(...)`
- `locator.press(...)`
- `page.expect_popup()` ou `context.expect_page()`
- `page.wait_for_url(...)`
- `expect(locator).to_be_visible()`
- `expect(locator).to_be_enabled()`

A camada `PWDriver` só deve ser usada para compatibilidade de módulos legados.
Não use a camada de compatibilidade como justificativa para escrever código
novo no estilo Selenium.
```

Também recomendo colocar no cabeçalho de `comunicacao_preenchimento.py`:

```python
"""
Este módulo é Playwright nativo.

Não usar:
- Selenium WebDriver
- execute_script
- find_element/find_elements
- send_keys
- time.sleep
- WebDriverWait

Usar Page, Locator e condições observáveis.
"""
```

## Estrutura recomendada

O ideal é separar o fluxo em uma versão nativa:

```text
atos/
├── comunicacao_preenchimento.py          # fachada pública
├── comunicacao_preenchimento_pw.py       # implementação Playwright
└── comunicacao_preenchimento_legacy.py   # compatibilidade antiga, temporária
```

A fachada poderia selecionar a implementação:

```python
from atos.comunicacao_preenchimento_pw import executar_preenchimento_minuta

__all__ = ["executar_preenchimento_minuta"]
```

E o módulo Playwright receberia `Page`:

```python
from playwright.sync_api import Page, expect

def selecionar_opcao(page: Page, seletor: str, texto: str) -> None:
campo = page.locator(seletor).first
campo.click()

opcao = page.locator(
"div.cdk-overlay-pane mat-option, "
"div.cdk-overlay-pane [role='option']"
).filter(has_text=texto).first

expect(opcao).to_be_visible()
opcao.click()

expect(
page.locator("div.cdk-overlay-pane").first
).to_be_hidden()
```

## Diagnóstico resumido

A LLM não está necessariamente “errando” ao corrigir para Selenium. Ela está seguindo os sinais do código:

1. O arquivo importa Selenium.
2. O parâmetro é declarado como `WebDriver`.
3. O fluxo usa `execute_script`, `find_elements` e `send_keys`.
4. Existem `time.sleep` e loops manuais.
5. O Playwright está escondido atrás de `PWDriver`.
6. O vocabulário Playwright nativo está em `pje.py`, mas o fluxo não o utiliza diretamente.

Portanto, a solução não é apenas pedir à LLM “use Playwright”. É necessário **remover a ambiguidade arquitetural**: fazer `comunicacao_preenchimento.py` receber `Page`, usar `Locator` e proibir explicitamente APIs Selenium nesse módulo.
