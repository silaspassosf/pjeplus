# 🚀 Manifesto de Otimização Contínua: Selenium + MutationObserver Nativo

## 📌 1. Objetivo Arquitetural
O objetivo deste guia é orientar a refatoração do código legado do projeto em Python/Selenium (mapeado em `LEGADO.md`) para eliminar gargalos de performance e instabilidade causados pelo "Mal do Polling".

**O Problema (Legado):** O uso de `time.sleep()` congela a execução de forma cega. O uso de `WebDriverWait(driver).until(...)` gera dezenas de requisições na rede local (WebDriver) perguntando repetidamente ao navegador se um elemento mudou. Em um sistema SPA (Angular) como o PJe, isso causa *race conditions* e lentidão.

**A Solução (Nova Arquitetura):** Substituir esperas estáticas e *polling* pelo método `aguardar_renderizacao_nativa`. Este método injeta um script JavaScript com um `MutationObserver` que aguarda a mudança diretamente no motor do navegador (V8) e avisa o Python no exato milissegundo em que a DOM é alterada, utilizando apenas 1 requisição assíncrona (`execute_async_script`).

---

## 🛠️ 2. A Função Core (A Fonte da Verdade)

Certifique-se de que a seguinte função esteja implementada em um arquivo base (ex: `Fix/utils_observer.py` ou `Fix/core.py`). Toda a refatoração dependerá desta importação.

```python
from selenium.webdriver.remote.webdriver import WebDriver
from Fix.log import logger

def aguardar_renderizacao_nativa(driver: WebDriver, seletor: str, modo: str = "aparecer", timeout: int = 10) -> bool:
    """
    Função universal que injeta um MutationObserver (JavaScript Nativo) no PJe
    para aguardar de forma ultrarrápida e sem pooling uma alteração no DOM.
    
    :param driver: Instância do Selenium WebDriver.
    :param seletor: O Seletor CSS do elemento que estamos vigiando.
    :param modo: "aparecer" (espera o elemento ser criado) ou "sumir" (espera ser deletado/oculto).
    :param timeout: Tempo máximo em segundos antes de desistir.
    :return: True se a condição foi atingida, False se deu timeout.
    """
    logger.debug(f"[OBSERVER] Vigiando '{seletor}' (modo: {modo})...")
    
    # Aumentamos o timeout do script do Python para dar tempo do JS responder
    driver.set_script_timeout(timeout + 2)

    script_js = """
        var seletor = arguments[0];
        var modo = arguments[1];
        var timeoutMs = arguments[2] * 1000;
        var callback = arguments[arguments.length - 1];
        
        // 1. Checagem instantânea
        var elementos = document.querySelectorAll(seletor);
        var visiveis = Array.from(elementos).filter(e => window.getComputedStyle(e).display !== 'none');
        
        if (modo === 'aparecer' && visiveis.length > 0) { callback(true); return; }
        if (modo === 'sumir' && visiveis.length === 0) { callback(true); return; }

        // 2. Cria o Vigia (MutationObserver)
        var observer = new MutationObserver(function(mutations, me) {
            var elAgora = document.querySelectorAll(seletor);
            var visAgora = Array.from(elAgora).filter(e => window.getComputedStyle(e).display !== 'none');
            
            if (modo === 'aparecer' && visAgora.length > 0) {
                me.disconnect(); callback(true);
            } 
            else if (modo === 'sumir' && visAgora.length === 0) {
                me.disconnect(); callback(true);
            }
        });

        // 3. Configura para vigiar a página inteira
        observer.observe(document.body, { 
            childList: true, 
            subtree: true, 
            attributes: true, 
            attributeFilter: ['style', 'class'] 
        });

        // 4. Timer de segurança (Timeout)
        setTimeout(function() { 
            observer.disconnect(); 
            callback(false); 
        }, timeoutMs);
    """

    try:
        resultado = driver.execute_async_script(script_js, seletor, modo, timeout)
        return resultado
    except Exception as e:
        logger.error(f"[OBSERVER] ❌ Erro ao executar script assíncrono: {e}")
        return False
```

---

## 🔍 3. Padrões de Refatoração (Antes x Depois)

Sempre procure no código legado pelos seguintes "Anti-Padrões" e os substitua pela nova abordagem.

### Padrão A: Esperando Spinners, Modais e Overlays sumirem
**Alvos comuns:** `comunicacao_finalizacao.py`, `judicial_navegacao.py`, `Fix/core.py`.

🔴 **ANTES (Anti-Padrão - Polling cego):**
```python
max_tentativas = 5
for tentativa in range(max_tentativas):
    overlays = driver.find_elements(By.CSS_SELECTOR, '.cdk-overlay-backdrop')
    if overlays:
        time.sleep(0.3)
    else:
        break
```

🟢 **DEPOIS (Otimizado - Observer Nativo):**
```python
from Fix.utils_observer import aguardar_renderizacao_nativa

# Deixa o navegador avisar quando o overlay sumir
aguardar_renderizacao_nativa(driver, '.cdk-overlay-backdrop, .loading-spinner', modo='sumir', timeout=5)
```

### Padrão B: Esperando o Angular desenhar Tabelas ou Painéis
**Alvos comuns:** `comunicacao_destinatarios.py`, `comunicacao.py`, telas com `mat-table`.

🔴 **ANTES (Anti-Padrão - Espera Mágica / WebDriverWait intenso):**
```python
time.sleep(1.5) # Espera cega
linhas_tabela = driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag')

# OU Polling constante
WebDriverWait(driver, 10).until(
    lambda d: len(d.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')) > 0
)
```

🟢 **DEPOIS (Otimizado - Renderização Exata):**
```python
from Fix.utils_observer import aguardar_renderizacao_nativa

# Aguarda o milissegundo exato em que a tag <tr> for desenhada
if aguardar_renderizacao_nativa(driver, 'table.t-class tr.ng-star-inserted', modo='aparecer', timeout=6):
    linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')
else:
    logger.warning("Timeout aguardando renderização nativa da tabela.")
```

### Padrão C: Esperando transição de URLs e Botões
**Alvos comuns:** `judicial_conclusao.py` (Aguardando botões de conclusão carregarem).

🔴 **ANTES (Anti-Padrão):**
```python
try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-botoes-transicao button'))
    )
except Exception:
    pass
```

🟢 **DEPOIS (Otimizado):**
```python
from Fix.utils_observer import aguardar_renderizacao_nativa

aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', modo='aparecer', timeout=10)
```

---

## 🗺️ 4. Mapa de Otimização Prioritária (Baseado no LEGADO.md)

1. **`ref/atos/core.py`:** Refatorar as funções `verificar_carregamento_pagina` e `verificar_carregamento_detalhe` para usar `modo='sumir'` nos spinners e `modo='aparecer'` nos botões de filtro.
2. **`judicial_navegacao.py`:** Refatorar a função `limpar_overlays` e os blocos que aguardam `pje-botoes-transicao`.
3. **`comunicacao_finalizacao.py`:** Refatorar o bloco de código que monitora o carregamento inicial da tabela antes de alterar o meio para os correios, substituindo o loop `while`.
4. **`judicial_prazos.py`:** Substituir o `WebDriverWait(driver, 20).until(lambda d: len(...) > 0)` pela chamada nativa para a tabela de prazos.

---

## 🤖 5. Prompt Padrão para uso com LLMs (Copilot, Claude, Kimi)

**Copie e cole o prompt abaixo junto com o código a ser refatorado:**

> "Atue como um Engenheiro de Performance Sênior em Python/Selenium. Estou lhe passando um arquivo do nosso sistema legado. Nosso projeto agora utiliza uma função customizada de alta performance chamada `aguardar_renderizacao_nativa(driver, seletor, modo, timeout)` importada de `Fix.utils_observer`. Ela usa `execute_async_script` com `MutationObserver` no JavaScript para evitar pooling de rede no WebDriver.
> 
> **Sua tarefa:**
> Analise este código e refatore-o para substituir TODOS os usos de `time.sleep()` e `WebDriverWait` (que sejam apenas para aguardar elementos aparecerem ou desaparecerem da DOM) por chamadas à função `aguardar_renderizacao_nativa`. 
> - Use `modo='aparecer'` para elementos sendo criados na tela.
> - Use `modo='sumir'` para modais, spinners e overlays sumirem da tela.
> Retorne o código refatorado mantendo a lógica de negócios original intacta, focando apenas na otimização da espera."