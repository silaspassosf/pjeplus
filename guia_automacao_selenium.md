# Guia Detalhado de Automação Web com Selenium

Este guia foi elaborado para explicar, de forma minuciosa e didática, como as funcionalidades típicas de uma extensão de automação (como a MaisPje) podem ser abstraídas e aplicadas para automatizar qualquer site utilizando Selenium, sem se prender a uma interface ou sistema específico. O objetivo é fornecer um esqueleto de codificação flexível, parametrizável e robusto, além de listar dependências complementares que potencializam a automação.

---

## 1. Introdução ao Selenium

**Selenium** é um framework open-source para automação de navegadores web. Ele permite interagir com páginas como se fosse um usuário humano: clicar, preencher formulários, extrair dados, navegar entre abas, entre outros.

- **Drivers suportados:** Chrome, Firefox, Edge, Safari, Opera.
- **Linguagens:** Python, Java, C#, Ruby, JavaScript etc. (Aqui focaremos em Python.)

---

## 2. Estrutura Básica de um Script Selenium

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Inicialização do driver
options = webdriver.FirefoxOptions()
options.add_argument('--start-maximized')
driver = webdriver.Firefox(options=options)
driver.get('https://www.sitequalquer.com')

# Espera robusta por um elemento
elemento = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, 'input#usuario'))
)
elemento.send_keys('meu_usuario')
```

---

## 3. Princípios de Parametrização e Modularização

### 3.1. Funções Utilitárias

Crie funções genéricas para:
- **Buscar elementos por diferentes seletores (CSS, XPath, texto, atributos)**
- **Clicar com robustez**
- **Preencher campos**
- **Esperar condições específicas**
- **Navegar entre abas e frames**
- **Extrair dados estruturados**

**Exemplo:**
```python
def buscar_elemento(driver, seletor, by=By.CSS_SELECTOR, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, seletor))
    )

def safe_click(driver, seletor, by=By.CSS_SELECTOR, timeout=10):
    elemento = buscar_elemento(driver, seletor, by, timeout)
    driver.execute_script('arguments[0].scrollIntoView(true);', elemento)
    elemento.click()
```

### 3.2. Parametrização

- **Seletores como parâmetros:** Permite reuso para qualquer site.
- **Timeouts configuráveis:** Sites diferentes têm tempos de resposta variados.
- **Funções callback:** Para aplicar lógica customizada em listas, tabelas, popups etc.

---

## 4. Estratégias para Buscar e Interagir com Elementos

### 4.1. Seletores
- **CSS Selector:** Rápido, flexível, preferido para maioria dos casos.
- **XPath:** Poderoso para estruturas complexas ou elementos sem IDs/classes.
- **By.TEXT:** Para buscar por texto visível (pode usar XPath ou funções auxiliares).

### 4.2. Exemplo de Busca por Texto
```python
def buscar_por_texto(driver, texto, tag='*', timeout=10):
    xpath = f"//{tag}[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{texto.lower()}')]"
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
```

### 4.3. Listas, Tabelas e Itens Dinâmicos
- Percorra listas/tabelas com `find_elements`.
- Use callbacks para aplicar ações em cada item.
- Exemplo:
```python
def processar_lista(driver, seletor_itens, callback):
    itens = driver.find_elements(By.CSS_SELECTOR, seletor_itens)
    for item in itens:
        callback(driver, item)
```

---

## 5. Esperas Inteligentes e Robustez

- **WebDriverWait + ExpectedConditions:** Evita erros por elementos não carregados.
- **Tratamento de exceções:** Sempre use try/except para garantir que o script continue mesmo com falhas pontuais.

---

## 6. Navegação Avançada

### 6.1. Abas e Janelas
```python
# Abrir nova aba
original = driver.current_window_handle
driver.execute_script("window.open('https://www.exemplo.com', '_blank');")
driver.switch_to.window(driver.window_handles[-1])
# ...
driver.close()
driver.switch_to.window(original)
```

### 6.2. Frames e Iframes
```python
iframe = driver.find_element(By.TAG_NAME, 'iframe')
driver.switch_to.frame(iframe)
# ...
driver.switch_to.default_content()
```

---

## 7. Extração de Dados

- **Campos de texto, tabelas, PDFs embutidos, etc.**
- Use `.text`, `.get_attribute('value')`, ou execute JavaScript para casos complexos.

---

## 8. Outras Dependências e Ferramentas Complementares

### 8.1. BeautifulSoup
- Útil para parsing de HTML fora do contexto do navegador, ou para pós-processamento de grandes blocos de HTML extraídos.

### 8.2. Pandas
- Facilita a manipulação de tabelas e dados extraídos para análise ou exportação.

### 8.3. PyAutoGUI
- Permite automação de interações fora do navegador (mouse, teclado, screenshots), útil para sites que bloqueiam automação pura.

### 8.4. Tesseract OCR (pytesseract)
- Para extrair texto de imagens ou PDFs não pesquisáveis.

### 8.5. Requests + Selenium
- Use `requests` para baixar arquivos ou interagir com APIs REST do site, quando possível, complementando a automação.

### 8.6. Playwright
- Alternativa moderna ao Selenium, com suporte a múltiplos navegadores, automação mais rápida e API moderna.

### 8.7. SeleniumBase
- Framework de alto nível sobre Selenium, com comandos simplificados, asserts, screenshots automáticos e geração de relatórios.

---

## 9. Boas Práticas

- **Sempre modularize e documente suas funções.**
- **Use logs detalhados para depuração.**
- **Implemente mecanismos de retry para etapas críticas.**
- **Evite hardcode de seletores: centralize-os em variáveis/configs.**
- **Mantenha o driver e dependências atualizados.**

---

## 10. Esqueleto Parametrizável para Automação Universal

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def iniciar_driver(url, headless=False):
    options = webdriver.FirefoxOptions()
    if headless:
        options.add_argument('--headless')
    driver = webdriver.Firefox(options=options)
    driver.get(url)
    return driver

def acao_generica(driver, seletor, acao, by=By.CSS_SELECTOR, valor=None):
    elemento = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((by, seletor))
    )
    if acao == 'click':
        elemento.click()
    elif acao == 'preencher':
        elemento.clear()
        elemento.send_keys(valor)
    elif acao == 'extrair':
        return elemento.text
    # Adicione outras ações conforme necessário

# Exemplo de uso
if __name__ == '__main__':
    driver = iniciar_driver('https://www.sitequalquer.com')
    acao_generica(driver, 'input#usuario', 'preencher', valor='meu_usuario')
    acao_generica(driver, 'button#entrar', 'click')
    # ...
    driver.quit()
```

---

## 11. Conclusão

A automação web robusta e parametrizável depende de abstrair as ações em funções reutilizáveis, parametrizar seletores e lógicas, e combinar Selenium com outras ferramentas conforme a necessidade do projeto. O esqueleto acima pode ser adaptado para qualquer site, bastando ajustar seletores, fluxos e adicionar tratamentos específicos para cada contexto.

---

**Dúvidas ou sugestões? Edite e expanda este guia conforme seus próprios desafios!**

---

## 12. Aplicando Lógicas Avançadas Inspiradas no Fix.py (Generalização)

O arquivo `Fix.py` do seu projeto traz uma série de padrões e funções utilitárias que podem ser generalizadas e adaptadas para automação de qualquer interface web. Abaixo, destaco e explico como essas lógicas podem ser abstraídas para uso universal:

### 12.1. Preenchimento Robusto de Campos
Função inspirada em `preencher_campos_prazo`:
```python
def preencher_campos_generico(driver, seletor, valor, by=By.CSS_SELECTOR, timeout=10, log=True):
    try:
        campos = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((by, seletor))
        )
        for campo in campos:
            driver.execute_script("arguments[0].focus();", campo)
            campo.clear()
            campo.send_keys(str(valor))
            driver.execute_script('arguments[0].dispatchEvent(new Event("input", {bubbles:true}));', campo)
            driver.execute_script('arguments[0].dispatchEvent(new Event("change", {bubbles:true}));', campo)
            if log:
                print(f'[Auto] Campo preenchido com {valor}')
        return True
    except Exception as e:
        if log:
            print(f'[Auto][ERRO] Falha ao preencher campos: {e}')
        return False
```
- **Generalização:** Permite preencher qualquer campo de texto, em qualquer site, disparando eventos JS para máxima compatibilidade.

### 12.2. Seleção de Opções em Selects Personalizados
Função inspirada em `selecionar_tipo_expediente`:
```python
def selecionar_opcao_por_texto(driver, seletor_dropdown, texto_opcao, by=By.CSS_SELECTOR, timeout=10, log=True):
    try:
        dropdown = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, seletor_dropdown))
        )
        dropdown.click()
        opcoes = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'option, mat-option, li'))
        )
        for opcao in opcoes:
            if texto_opcao.lower() in opcao.text.lower():
                opcao.click()
                if log:
                    print(f'[Auto] Opção selecionada: {texto_opcao}')
                return True
        if log:
            print(f'[Auto] Opção "{texto_opcao}" não encontrada.')
        return False
    except Exception as e:
        if log:
            print(f'[Auto][ERRO] Falha ao selecionar opção: {e}')
        return False
```
- **Generalização:** Funciona para qualquer dropdown customizado ou tradicional.

### 12.3. Busca Robusta de Elementos por Texto
Função inspirada em `buscar_seletor_robusto`:
```python
def buscar_elemento_por_textos(driver, textos, tag='*', timeout=10, log=True):
    for texto in textos:
        try:
            xpath = f"//{tag}[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{texto.lower()}')]"
            elemento = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            if log:
                print(f'[Auto] Elemento encontrado: {texto}')
            return elemento
        except Exception:
            continue
    if log:
        print(f'[Auto] Nenhum elemento encontrado para os textos fornecidos.')
    return None
```
- **Generalização:** Permite localizar botões, links ou campos por múltiplos textos possíveis, útil para interfaces dinâmicas.

### 12.4. Esperas Inteligentes e Clics Seguros
Funções inspiradas em `esperar_elemento`, `safe_click`:
```python
def esperar_elemento(driver, seletor, by=By.CSS_SELECTOR, timeout=10, log=True):
    try:
        elemento = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, seletor))
        )
        if log:
            print(f'[Auto] Elemento presente: {seletor}')
        return elemento
    except Exception as e:
        if log:
            print(f'[Auto][ERRO] Falha ao esperar elemento: {e}')
        return None

def safe_click(driver, seletor, by=By.CSS_SELECTOR, timeout=10, log=True):
    elemento = esperar_elemento(driver, seletor, by, timeout, log)
    if elemento:
        driver.execute_script('arguments[0].scrollIntoView(true);', elemento)
        elemento.click()
        if log:
            print(f'[Auto] Clique realizado em: {seletor}')
        return True
    return False
```
- **Generalização:** Garante robustez em qualquer ação de clique ou espera.

### 12.5. Processamento de Listas e Tabelas
Função inspirada em `processar_lista_processos`:
```python
def processar_lista(driver, seletor_itens, callback, by=By.CSS_SELECTOR, log=True):
    itens = driver.find_elements(by, seletor_itens)
    for idx, item in enumerate(itens):
        try:
            callback(driver, item, idx)
        except Exception as e:
            if log:
                print(f'[Auto][ERRO] Falha ao processar item {idx}: {e}')
```
- **Generalização:** Aplica lógica customizada a cada item de uma lista ou tabela.

### 12.6. Extração de Dados Estruturados
Função inspirada em `extrair_documento`:
```python
def extrair_texto_elemento(driver, seletor, by=By.CSS_SELECTOR, timeout=10, log=True):
    try:
        elemento = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, seletor))
        )
        texto = elemento.text
        if log:
            print(f'[Auto] Texto extraído: {texto[:100]}...')
        return texto
    except Exception as e:
        if log:
            print(f'[Auto][ERRO] Falha na extração de texto: {e}')
        return None
```
- **Generalização:** Extração de texto de qualquer elemento, útil para scraping e análise.

### 12.7. Criação de Ações Parametrizadas (GIGS, Tarefas, etc)
Função inspirada em `criar_gigs`:
```python
def acao_parametrizada(driver, parametros, log=True):
    # Exemplo: preencher campos, clicar botões, anexar arquivos, etc.
    for acao in parametros:
        tipo = acao.get('tipo')
        seletor = acao.get('seletor')
        valor = acao.get('valor')
        if tipo == 'preencher':
            preencher_campos_generico(driver, seletor, valor, log=log)
        elif tipo == 'clicar':
            safe_click(driver, seletor, log=log)
        # Adicione outros tipos conforme necessário
```
- **Generalização:** Permite montar fluxos de automação por dicionários/listas de ações, facilitando reuso e configuração.

---

## 13. Recomendações Finais para Generalização
- **Centralize funções utilitárias em um módulo próprio (como Fix.py).**
- **Use logs e tratamento de exceções em todas as etapas.**
- **Parametrize seletores, textos e fluxos para máxima flexibilidade.**
- **Implemente callbacks para lógica customizada em listas, tabelas, popups, etc.**
- **Documente cada função e mantenha exemplos de uso.**

Essas estratégias, inspiradas nas melhores práticas do seu Fix.py, garantem que sua automação seja robusta, adaptável e escalável para qualquer interface web!
