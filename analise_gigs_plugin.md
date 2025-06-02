# Análise do Botão Guardar Dados e Integração SISBAJUD

## 1. Armazenamento do Número do Processo

### Botão `maisPJe_bt_detalhes_guardarDados` (linha ~12000)
```javascript
// O botão usa localStorage para guardar dados extraídos
function guardarDadosPartes() {
    var numeroProcesso = extrairNumeroProcesso();
    var dadosProcesso = {
        numero: numeroProcesso,
        partes: extrairPartes(),
        magistrado: extrairMagistrado(),
        juizo: extrairJuizo()
    };
    localStorage.setItem('dadosProcessoAtual', JSON.stringify(dadosProcesso));
}
```

### Implementação para Fix.py
```python
def extrair_dados_processo_melhorado(driver, max_tentativas=3, intervalo_tentativas=5):
    """
    Versão melhorada baseada no padrão do gigs-plugin.js
    Armazena dados em JSON local similar ao localStorage do navegador
    """
    dados_processo = {"numero": "", "partes": [], "magistrado": "", "juizo": ""}
    json_path = "d:\\PjePlus\\dadosatuais.json"
    
    # Estratégia 1: ID específico (mais confiável)
    try:
        elemento_numero = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "_numeroProcessoDetalhes"))
        )
        numero_processo = elemento_numero.text.strip()
        if numero_processo and re.match(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', numero_processo):
            dados_processo["numero"] = numero_processo
            
            # Extrai magistrado usando padrão do gigs-plugin
            try:
                magistrado_elem = driver.find_element(By.CSS_SELECTOR, 
                    '[data-label*="Magistrado"], .magistrado-nome, #magistradoResponsavel')
                dados_processo["magistrado"] = magistrado_elem.text.strip()
            except:
                pass
                
            # Extrai juízo usando padrão do gigs-plugin  
            try:
                juizo_elem = driver.find_element(By.CSS_SELECTOR,
                    '[data-label*="Juízo"], .juizo-nome, #juizoProcesso')
                dados_processo["juizo"] = juizo_elem.text.strip()
            except:
                pass
                
            # Salva no JSON (simula localStorage)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(dados_processo, f, ensure_ascii=False, indent=4)
                
            return dados_processo
    except:
        # ...existing fallback strategies...
        pass
```

## 2. Função preenchercamposSisbajud Melhorada

### Análise da Função Original (linha 12706)
```javascript
function preenchercamposSisbajud(dadosProcesso) {
    // Preenche número do processo
    var campoNumero = document.querySelector('#numeroProcesso, [name="numeroProcesso"]');
    if (campoNumero) {
        campoNumero.value = dadosProcesso.numero;
        triggerChange(campoNumero);
    }
    
    // Preenche juízo
    var campoJuizo = document.querySelector('#juizo, [name="juizo"]');
    if (campoJuizo) {
        campoJuizo.value = dadosProcesso.juizo;
        triggerChange(campoJuizo);
    }
    
    // Preenche magistrado
    var campoMagistrado = document.querySelector('#magistrado, [name="magistrado"]');
    if (campoMagistrado) {
        campoMagistrado.value = dadosProcesso.magistrado;
        triggerChange(campoMagistrado);
    }
}
```

### Implementação Python Equivalente
```python
def preencher_campos_sisbajud(driver, dados_processo, log=True):
    """
    Preenche campos do SISBAJUD baseado na função preenchercamposSisbajud
    do gigs-plugin.js (linha 12706)
    """
    try:
        if log:
            print('[SISBAJUD] Iniciando preenchimento de campos...')
            
        # 1. Preenche número do processo
        seletores_numero = [
            '#numeroProcesso', 
            '[name="numeroProcesso"]',
            'input[placeholder*="Número"]',
            'input[aria-label*="Processo"]'
        ]
        
        for seletor in seletores_numero:
            try:
                campo = driver.find_element(By.CSS_SELECTOR, seletor)
                if campo.is_displayed() and campo.is_enabled():
                    campo.clear()
                    campo.send_keys(dados_processo.get("numero", ""))
                    
                    # Dispara eventos JS (equivalente ao triggerChange)
                    driver.execute_script(
                        'arguments[0].dispatchEvent(new Event("input", {bubbles:true}));'
                        'arguments[0].dispatchEvent(new Event("change", {bubbles:true}));',
                        campo
                    )
                    if log:
                        print(f'[SISBAJUD] Número preenchido: {dados_processo.get("numero", "")}')
                    break
            except:
                continue
                
        # 2. Preenche juízo
        seletores_juizo = [
            '#juizo',
            '[name="juizo"]', 
            'input[placeholder*="Juízo"]',
            'select[aria-label*="Juízo"]'
        ]
        
        for seletor in seletores_juizo:
            try:
                campo = driver.find_element(By.CSS_SELECTOR, seletor)
                if campo.is_displayed() and campo.is_enabled():
                    if campo.tag_name.lower() == 'select':
                        # Para campos select, procura pela opção
                        opcoes = campo.find_elements(By.TAG_NAME, 'option')
                        for opcao in opcoes:
                            if dados_processo.get("juizo", "").lower() in opcao.text.lower():
                                opcao.click()
                                break
                    else:
                        campo.clear()
                        campo.send_keys(dados_processo.get("juizo", ""))
                        
                    driver.execute_script(
                        'arguments[0].dispatchEvent(new Event("change", {bubbles:true}));',
                        campo
                    )
                    if log:
                        print(f'[SISBAJUD] Juízo preenchido: {dados_processo.get("juizo", "")}')
                    break
            except:
                continue
                
        # 3. Preenche magistrado
        seletores_magistrado = [
            '#magistrado',
            '[name="magistrado"]',
            'input[placeholder*="Magistrado"]',
            'select[aria-label*="Magistrado"]'
        ]
        
        for seletor in seletores_magistrado:
            try:
                campo = driver.find_element(By.CSS_SELECTOR, seletor)
                if campo.is_displayed() and campo.is_enabled():
                    if campo.tag_name.lower() == 'select':
                        opcoes = campo.find_elements(By.TAG_NAME, 'option')
                        for opcao in opcoes:
                            if dados_processo.get("magistrado", "").lower() in opcao.text.lower():
                                opcao.click()
                                break
                    else:
                        campo.clear() 
                        campo.send_keys(dados_processo.get("magistrado", ""))
                        
                    driver.execute_script(
                        'arguments[0].dispatchEvent(new Event("change", {bubbles:true}));',
                        campo
                    )
                    if log:
                        print(f'[SISBAJUD] Magistrado preenchido: {dados_processo.get("magistrado", "")}')
                    break
            except:
                continue
                
        if log:
            print('[SISBAJUD] Preenchimento de campos concluído.')
        return True
        
    except Exception as e:
        if log:
            print(f'[SISBAJUD][ERRO] Falha no preenchimento: {e}')
        return False
```

## 3. Integração Completa

### Função de Uso Conjunto
```python
def processar_sisbajud_completo(driver, log=True):
    """
    Função completa que replica o fluxo do gigs-plugin para SISBAJUD
    """
    try:
        # 1. Extrai dados do processo (equivale ao guardarDadosPartes)
        dados = extrair_dados_processo_melhorado(driver, log=log)
        
        if not dados or not dados.get("numero"):
            if log:
                print('[SISBAJUD][ERRO] Não foi possível extrair dados do processo')
            return False
            
        # 2. Preenche campos do SISBAJUD
        sucesso = preencher_campos_sisbajud(driver, dados, log=log)
        
        if log:
            print(f'[SISBAJUD] Processamento {"concluído" if sucesso else "falhou"}')
            
        return sucesso
        
    except Exception as e:
        if log:
            print(f'[SISBAJUD][ERRO] Falha geral: {e}')
        return False
```
