# 🔄 PROJETO DE REFATORAÇÃO - M1.PY

## 📊 **ANÁLISE DO ARQUIVO ATUAL**

### **Situação Atual:**
- **Arquivo:** `m1.py` (2,112 linhas)
- **Funções identificadas:** 20+
- **Principais problemas:**
  - Código monolítico com múltiplas responsabilidades
  - Funções muito longas (algumas com mais de 200 linhas)
  - Mistura de lógica de negócio com código de automação
  - Dificuldade de manutenção e testes
  - Violação do princípio de responsabilidade única

## 🎯 **OBJETIVO DA REFATORAÇÃO**

Dividir o código em módulos menores (máximo 400 linhas cada) mantendo:
- ✅ **Funcionalidade idêntica** (mesmo comportamento)
- ✅ **Mesmas importações** (sem alterações)
- ✅ **Fluxo preservado** (lógica intacta)
- ✅ **Compatibilidade total** com código existente

## 🗂️ **ESTRUTURA PROPOSTA**

### **Pasta de Módulos:**
```
d:\PjePlus\mdd_modulos\
├── __init__.py
├── setup_driver.py          # Setup e configuração do driver
├── navegacao.py             # Navegação e controle de fluxo
├── argos_core.py            # Lógica principal do fluxo Argos
├── argos_anexos.py          # Processamento de anexos Argos
├── argos_regras.py          # Regras de negócio Argos
├── argos_documentos.py      # Busca e análise de documentos Argos
├── outros_core.py           # Lógica principal do fluxo Outros
├── outros_analise.py        # Análise de padrões e documentos Outros
├── sisbajud_utils.py        # Utilitários para processamento SISBAJUD
├── intimacao_utils.py       # Utilitários para fechamento de intimação
└── teste_utils.py           # Funções de teste e debug
```

### **Arquivo Principal:**
```
d:\PjePlus\mdd.py            # Orquestrador principal (máx. 100 linhas)
```

## 📋 **DIVISÃO DETALHADA POR MÓDULO**

### **1. setup_driver.py** (≈ 50 linhas)
```python
# Responsabilidades:
- setup_driver()
- Configuração inicial do driver
- Limpeza de arquivos temporários
- Importações relacionadas ao driver

# Funções extraídas:
- setup_driver()
```

### **2. navegacao.py** (≈ 150 linhas)
```python
# Responsabilidades:
- navegacao(driver)
- iniciar_fluxo(driver)
- Controle de navegação entre telas
- Gerenciamento de janelas/abas

# Funções extraídas:
- navegacao(driver)
- iniciar_fluxo(driver)
```

### **3. argos_core.py** (≈ 300 linhas)
```python
# Responsabilidades:
- processar_argos(driver, log=False)
- Orquestração principal do fluxo Argos
- Coordenação entre módulos Argos
- Lógica de alto nível

# Funções extraídas:
- processar_argos(driver, log=False)
- andamento_argos(driver, resultado_sisbajud, sigilo_anexos, log=True)
```

### **4. argos_anexos.py** (≈ 400 linhas)
```python
# Responsabilidades:
- tratar_anexos_argos(driver, documentos_sequenciais, log=True)
- Processamento de anexos sigilosos
- Controle de visibilidade de documentos
- Lógica de sigilo/remoção de sigilo

# Funções extraídas:
- tratar_anexos_argos(driver, documentos_sequenciais, log=True)
- retirar_sigilo(elemento)
```

### **5. argos_regras.py** (≈ 350 linhas)
```python
# Responsabilidades:
- aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False)
- Regras de negócio específicas do Argos
- Decisões baseadas em SISBAJUD
- Lógica de prioridades

# Funções extraídas:
- aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False)
- lembrete_bloq(driver, debug=False)
```

### **6. argos_documentos.py** (≈ 250 linhas)
```python
# Responsabilidades:
- buscar_documento_argos(driver, log=True)
- buscar_documentos_sequenciais(driver, log=True)
- Lógica de busca na timeline
- Extração de texto de documentos

# Funções extraídas:
- buscar_documento_argos(driver, log=True)
- buscar_documentos_sequenciais(driver, log=True)
```

### **7. outros_core.py** (≈ 200 linhas)
```python
# Responsabilidades:
- fluxo_mandados_outros(driver, log=True)
- Orquestração do fluxo Outros
- Verificação de tipos de certidão
- Coordenação com módulos de análise

# Funções extraídas:
- fluxo_mandados_outros(driver, log=True)
```

### **8. outros_analise.py** (≈ 300 linhas)
```python
# Responsabilidades:
- verificar_autor_documento(documento, driver)
- ultimo_mdd(driver, log=True)
- Análise de padrões em documentos
- Lógica de mandados positivos/negativos

# Funções extraídas:
- verificar_autor_documento(documento, driver)
- ultimo_mdd(driver, log=True)
- Função analise_padrao (extraída de fluxo_mandados_outros)
```

### **9. sisbajud_utils.py** (≈ 200 linhas)
```python
# Responsabilidades:
- extract_sisbajud_result_from_text(text, log=True)
- Processamento de resultados SISBAJUD
- Análise de texto para extrair resultados
- Regras de interpretação

# Funções extraídas:
- extract_sisbajud_result_from_text(text, log=True)
```

### **10. intimacao_utils.py** (≈ 350 linhas)
```python
# Responsabilidades:
- fechar_intimacao(driver, log=True)
- Lógica de fechamento de intimação
- Interação com modais e formulários
- Tratamento de expedientes

# Funções extraídas:
- fechar_intimacao(driver, log=True)
```

### **11. teste_utils.py** (≈ 150 linhas)
```python
# Responsabilidades:
- fluxo_teste(driver)
- testar_regra_argos_planilha()
- Funções de teste e debug
- Validações e exemplos

# Funções extraídas:
- fluxo_teste(driver)
- testar_regra_argos_planilha()
```

## 📄 **ARQUIVO ORQUESTRADOR - mdd.py**

```python
# mdd.py - Orquestrador principal (≈ 100 linhas)

# Importações dos módulos
from mdd_modulos import (
    setup_driver,
    navegacao,
    argos_core,
    outros_core,
    teste_utils
)

# Importações existentes preservadas
from Fix import (
    navegar_para_tela,
    extrair_pdf,
    analise_outros,
    # ... todas as importações originais
)

# Função principal simplificada
def main():
    """
    Função principal que coordena todo o fluxo do programa.
    """
    # Setup inicial
    driver = setup_driver.setup_driver()
    if not driver:
        return

    # Login process
    if not login_func(driver):
        driver.quit()
        return

    # Navegação
    if not navegacao.navegacao(driver):
        driver.quit()
        return

    # Fluxo principal
    fluxo_mandado(driver)

    print("[INFO] Processamento concluído. Pressione ENTER para encerrar...")
    input()
    driver.quit()

def fluxo_mandado(driver):
    """Função de orquestração extraída do módulo navegacao"""
    from mdd_modulos.navegacao import fluxo_mandado
    return fluxo_mandado(driver)

if __name__ == "__main__":
    main()
```

## 🔧 **BENEFÍCIOS DA REFATORAÇÃO**

### **Manutenibilidade:**
- ✅ Código organizado por responsabilidade
- ✅ Módulos com tamanho gerenciável (máx. 400 linhas)
- ✅ Funções menores e mais focadas
- ✅ Separação clara de responsabilidades

### **Testabilidade:**
- ✅ Módulos podem ser testados isoladamente
- ✅ Funções específicas podem ser validadas
- ✅ Mock de dependências facilitado
- ✅ Testes unitários mais simples

### **Reutilização:**
- ✅ Módulos podem ser reutilizados em outros projetos
- ✅ Funções específicas podem ser chamadas individualmente
- ✅ Lógica de negócio separada da automação
- ✅ Facilita criação de novos fluxos

### **Desenvolvimento:**
- ✅ Equipe pode trabalhar em módulos separados
- ✅ Conflitos de merge reduzidos
- ✅ Debugging mais eficiente
- ✅ Novas funcionalidades mais fáceis de adicionar

## 🚀 **PLANO DE IMPLEMENTAÇÃO**

### **Fase 1: Criação da estrutura**
1. Criar pasta `mdd_modulos/`
2. Criar arquivo `__init__.py`
3. Criar arquivo orquestrador `mdd.py`

### **Fase 2: Divisão por módulos (ordem sugerida)**
1. **setup_driver.py** (mais simples)
2. **teste_utils.py** (isolado)
3. **sisbajud_utils.py** (utilitário)
4. **intimacao_utils.py** (utilitário)
5. **argos_documentos.py** (busca/extração)
6. **outros_analise.py** (análise)
7. **argos_anexos.py** (processamento complexo)
8. **argos_regras.py** (regras de negócio)
9. **outros_core.py** (fluxo outros)
10. **argos_core.py** (fluxo principal)
11. **navegacao.py** (orquestração)

### **Fase 3: Validação e testes**
1. Testar cada módulo isoladamente
2. Testar integração entre módulos
3. Validar fluxo completo
4. Comparar resultados com versão original

### **Fase 4: Documentação**
1. Documentar cada módulo
2. Atualizar README
3. Criar guia de desenvolvimento
4. Documentar APIs internas

## ⚠️ **CONSIDERAÇÕES IMPORTANTES**

### **Preservação Total:**
- **ZERO alterações** na lógica existente
- **ZERO alterações** no fluxo atual
- **ZERO alterações** nas importações externas
- **ZERO alterações** no comportamento

### **Compatibilidade:**
- Código existente deve continuar funcionando
- Todas as funções devem manter assinaturas
- Imports devem ser redirecionados adequadamente
- Logs e debugging preservados

### **Qualidade:**
- Cada módulo deve ter máximo 400 linhas
- Funções devem ter responsabilidade única
- Imports devem ser organizados e otimizados
- Documentação deve ser mantida/melhorada

---

**Este projeto de refatoração visa melhorar a estrutura do código mantendo 100% de compatibilidade e funcionalidade.**
