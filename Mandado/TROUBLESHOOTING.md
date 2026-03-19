# 🔧 TROUBLESHOOTING - FLUXO ARGOS

## ❓ Se `retirar_sigilo()` ainda não estiver funcionando

### 1. Verificar se aria-label existe
```python
# Debug: Ver qual aria-label está sendo lido
def retirar_sigilo(..., debug=True):
    # ... código ...
    print(f"[DEBUG] aria-label: '{aria_label}'")
    # Se vazio, significa que o botão tem aria-label diferente
```

**Solução**: Se aria-label for diferente do esperado:
- Adicionar novo padrão no código
- Exemplo: `if "remover" in aria_label:` (se aria-label disser "remover" ao invés de "retirar sigilo")

### 2. Verificar se ícone tem classe correta
```python
# Debug: Ver classes do ícone
icone = btn_sigilo.find_element(By.CSS_SELECTOR, "i.fa-wpexplorer")
classes = icone.get_attribute("class")
print(f"[DEBUG] Classes do ícone: {classes}")
# Procurar por: tl-nao-sigiloso ou tl-sigiloso
```

**Solução**: Se classes forem diferentes:
- Exemplo: `if 'sealed' in classes:` (se usarem "sealed" ao invés de "tl-sigiloso")
- Atualizar os seletores no código

### 3. Verificar se o botão está visível
```python
# Debug: Ver se o botão é exibido
print(f"[DEBUG] Botão visível? {btn_sigilo.is_displayed()}")
print(f"[DEBUG] Botão habilitado? {btn_sigilo.is_enabled()}")
```

**Solução**: Se não visível ou desabilitado:
- Pode estar oculto por outro elemento
- Tentar scroll até o elemento: `driver.execute_script("arguments[0].scrollIntoView();", btn_sigilo)`
- Tentar aguardar o elemento aparecer: `WebDriverWait(driver, 10).until(EC.visibility_of_element_located(...))`

---

## ❓ Se `processar_argos()` continua sem aplicar regras

### 1. Verificar se `buscar_documento_argos()` retorna documento
```python
# Debug na ETAPA 4
resultado = buscar_documento_argos(driver, log=True)
print(f"[DEBUG] Resultado: {resultado}")
print(f"[DEBUG] É None? {resultado is None}")
print(f"[DEBUG] Texto vazio? {not resultado[0] if resultado else 'N/A'}")
```

**Solução**: Se retorna None ou texto vazio:
- Verificar se há documentos na timeline
- Verificar se `extrair_direto()` e `extrair_documento()` funcionam
- Aumentar timeout em: `extrair_direto(driver, timeout=15)` (ao invés de 10)

### 2. Verificar se `aplicar_regras_argos()` encontra estratégia
```python
# Debug na ETAPA 6
regras_aplicadas = aplicar_regras_argos(
    driver, 
    resultado_sisbajud, 
    sigilo_anexos, 
    documento_tipo, 
    documento_texto, 
    debug=True  # ← ATIVAR DEBUG
)
print(f"[DEBUG] Regras aplicadas? {regras_aplicadas}")
```

**Solução**: Se debug=True não mostrar nenhuma estratégia:
- Verificar texto extraído: `print(f"[DEBUG] Texto primeiro 500 chars: {documento_texto[:500]}")`
- Comparar com padrões em `regras.py`
- Adicionar nova estratégia se o padrão não está sendo reconhecido

### 3. Verificar se loop está executando
```python
# Debug no loop da ETAPA 4-6
# Adicionar prints dentro do while:
while tentativa < max_tentativas and not sucesso_regras:
    tentativa += 1
    print(f'[DEBUG] Loop tentativa {tentativa}')  # ← Ver se entra no loop
    # ... resto do código ...
    print(f'[DEBUG] Saiu com sucesso_regras={sucesso_regras}')  # ← Ver se saiu
```

**Solução**: 
- Se nunca entra no loop: `max_tentativas` pode estar 0 ou loop pode estar em posição errada
- Se não sai do loop: Verificar se `sucesso_regras` está sendo setado para True

---

## ❓ Se os logs não estão aparecendo

### 1. Verificar se log=True está sendo passado
```python
# CORRETO:
processar_argos(driver, log=True)  # ← log=True

# ERRADO:
processar_argos(driver)  # ← log=False (padrão)
```

### 2. Verificar se debug=True está sendo passado
```python
# CORRETO para ver logs detalhados:
aplicar_regras_argos(..., debug=True)  # ← debug=True

# PADRÃO:
aplicar_regras_argos(...)  # ← debug=False (padrão)
```

### 3. Verificar se stdout está sendo capturado
```python
# Se usar pytest ou outro test runner, podem capturar output
# Solução: Redirecionar para file

import sys
with open("debug.log", "w") as f:
    sys.stdout = f
    processar_argos(driver, log=True)
    sys.stdout = sys.__stdout__

# Depois:
with open("debug.log", "r") as f:
    print(f.read())
```

---

## ✅ Checklist de Validação

### Antes de chamar `processar_argos()`:
- [ ] Driver está conectado a PJe?
- [ ] Você está na página do mandado (timeline visível)?
- [ ] Timeline tem pelo menos 1 despacho/decisão?
- [ ] `extrair_direto()` funciona em seu ambiente?

### Ao chamar `processar_argos()`:
- [ ] Passar `log=True` para ver logs detalhados
- [ ] Verificar output da ETAPA 4 (busca documento)
- [ ] Verificar output da ETAPA 6 (aplicação de regras)

### Se falhar:
- [ ] Ativar `debug=True` em `buscar_documento_argos()` e `aplicar_regras_argos()`
- [ ] Copiar texto extraído do documento
- [ ] Comparar com padrões esperados em [regras.py](regras.py)
- [ ] Abrir issue com logs e texto extraído

---

## 🐛 Bugs Conhecidos

### Problema: Loop nunca sai mesmo após encontrar regra
**Causa**: `sucesso_regras` não está sendo setado para True
**Solução**: Verificar se linha `sucesso_regras = True` está presente e sendo executada
**Localização**: [processamento.py](processamento.py#L760)

### Problema: Clique em sigilo não funciona no Firefox
**Causa**: `driver.execute_script()` pode não funcionar em todos os drivers
**Solução**: Código já tem fallback para `btn_sigilo.click()`
**Verificar**: Se ambos falharem, verificar se botão está visível

### Problema: "Nenhum despacho/decisão encontrado"
**Causa**: Timeline vazia ou documentos têm nomes diferentes
**Solução**: Verificar seletor CSS em `buscar_documento_argos()`: `a.tl-documento:not([target="_blank"])`
**Debug**: 
```python
itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
for item in itens:
    try:
        link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento')
        print(f"[DEBUG] Documento encontrado: {link.text}")
    except:
        print("[DEBUG] Item sem link tl-documento")
```

---

## 📞 Reportar Problema

Se encontrar bug, por favor forneça:

1. **Contexto**
   - Qual mandado está testando?
   - Qual é o tipo (Argos, Ordinário, etc)?

2. **Logs Completos**
   - Saída com `log=True` e `debug=True`
   - Incluir todas as tentativas do loop

3. **Valores de Entrada**
   - `resultado_sisbajud` (dicionário)
   - `sigilo_anexos` (dicionário)
   - Primeiro 500 caracteres do `documento_texto`
   - `documento_tipo` (despacho, decisão, etc)

4. **Ambiente**
   - Python version
   - Selenium version
   - Browser (Chrome, Firefox, etc)

5. **Tela Atual**
   - Screenshot da timeline se possível
   - Qual aba está aberta (/detalhe, /lista, etc)

---

## 🎯 Performance

### Se o loop está lento:
- **Problema**: `extrair_direto()` timeout muito alto (10s)
- **Solução**: Reduzir timeout: `extrair_direto(driver, timeout=5)`
- **Risco**: Pode não conseguir extrair texto

### Se muitos loops estão rodando:
- **Problema**: 5 tentativas pode ser demais para seu caso
- **Solução**: Reduzir `max_tentativas = 3` em vez de 5
- **Trade-off**: Menos iterações = risco de perder documentos

---

## 🎓 Exemplos de Debug

### Exemplo 1: Ver todos os documentos na timeline
```python
from selenium.webdriver.common.by import By

itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
for i, item in enumerate(itens):
    try:
        link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento')
        print(f"{i}: {link.text}")
    except:
        print(f"{i}: (sem link)")
```

### Exemplo 2: Ver aria-label de um botão
```python
from selenium.webdriver.common.by import By

elemento = driver.find_element(By.CSS_SELECTOR, 'li.tl-item-container')
btn = elemento.find_element(By.CSS_SELECTOR, 'button i.fa-wpexplorer')
aria = btn.get_attribute('aria-label')
classes = btn.get_attribute('class')
print(f"aria-label: {aria}")
print(f"classes: {classes}")
```

### Exemplo 3: Ver texto extraído de um documento
```python
from Fix.extracao import extrair_direto

resultado = extrair_direto(driver, timeout=10, debug=True, formatar=True)
if resultado and resultado.get('sucesso'):
    texto = resultado.get('conteudo')
    print(f"Texto extraído ({len(texto)} chars):")
    print(texto[:500])  # Primeiros 500 caracteres
else:
    print("Falha ao extrair")
```

---

## 📚 Referências

- [Mandado/utils.py](utils.py#L216) - Função `retirar_sigilo()`
- [Mandado/processamento.py](processamento.py#L663) - Função `processar_argos()`
- [Mandado/regras.py](regras.py#L342) - Função `aplicar_regras_argos()`
- [Fix/core.py](../Fix/core.py#L2885) - Função `buscar_documento_argos()`

