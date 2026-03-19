# 🎯 Restricted Copilot - Guia para Workspace PjePlus

## ✅ STATUS: EXTENSÃO INSTALADA E PRONTA PARA USO

A extensão "Restricted Copilot" foi instalada com sucesso no seu VS Code e está disponível para uso no workspace PjePlus.

## 🚀 Como Usar no PjePlus

### 1. Abrir o Workspace PjePlus
```powershell
cd "d:\PjePlus"
code .
```

### 2. Testar a Extensão

#### Exemplo 1: Analisar função no bacen.py
1. Abra o arquivo `bacen.py`
2. Coloque o cursor dentro de qualquer função (ex: `processar_dados_bacen`)
3. **Clique com botão direito** → `Analyze Current Function`
4. Painel lateral abrirá mostrando análise restrita apenas dessa função

#### Exemplo 2: Analisar trecho no p2.py  
1. Abra o arquivo `p2.py`
2. **Selecione** um trecho de código (ex: regras de fluxo)
3. **Clique com botão direito** → `Analyze Selection with Limited Context`
4. Extensão analisará apenas seleção + 50 linhas de contexto

#### Exemplo 3: Via Command Palette
1. **Ctrl+Shift+P**
2. Digite `Restricted Copilot`
3. Escolha uma das opções:
   - `Analyze Current Function`
   - `Analyze Selection with Limited Context`
   - `Toggle Restrictive Mode`

## ⚙️ Configuração Recomendada para PjePlus

### Configuração de Máxima Segurança (Recomendada)
1. **File** → **Preferences** → **Settings**
2. Procure por `Restricted Copilot`
3. Configure:
   - ✅ `Restrictive Mode`: **true** (sem sugestões não solicitadas)
   - ✅ `Inquisitive Mode`: **true** (pergunta antes de mudar)
   - 🔢 `Max Context Lines`: **25** (contexto mínimo para segurança)

### Para Aplicar Apenas no PjePlus
1. Abra o workspace PjePlus
2. **File** → **Preferences** → **Settings**
3. Clique na aba **"Workspace"**
4. Configure as opções acima
5. Configurações ficarão salvas em `.vscode/settings.json`

## 🔍 Casos de Uso Específicos

### Analisar Correções de Bugs
```python
# Exemplo: função com erro no bacen.py
def processar_resposta_bacen(resposta):
    # Coloque cursor aqui e use "Analyze Current Function"
    if resposta.status_code = 200:  # Bug: = ao invés de ==
        return resposta.json()
```

### Revisar Fluxos de Automação
```python
# Exemplo: revisar lógica no p2.py
def verificar_prazo():
    # Selecione este bloco e use "Analyze Selection"
    if prazo_vencido:
        executar_acao('urgente')
    else:
        executar_acao('normal')
```

### Otimizar Funções Selenium
```python
# Exemplo: otimizar código no atos.py
def aguardar_elemento(driver, xpath):
    # Cursor na função + análise para sugestões de melhoria
    wait = WebDriverWait(driver, 10)
    return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
```

## 🛡️ Comportamento Restritivo

### ✅ O que a extensão FAZ:
- Analisa **apenas** a função onde está o cursor
- Analisa **apenas** a seleção + contexto limitado
- **Pergunta** antes de sugerir mudanças
- **Explica** o escopo de qualquer alteração
- Respeita limites de linhas de contexto

### ❌ O que a extensão NÃO faz:
- ❌ Não analisa arquivos inteiros sem permissão
- ❌ Não sugere mudanças em outras funções
- ❌ Não faz alterações automáticas
- ❌ Não propõe refatorações amplas
- ❌ Não analisa imports ou dependências sem solicitar

## 🎯 Fluxo de Trabalho Recomendado

### Para Debug de Função Específica:
1. Identifique a função com problema
2. Cursor na função → `Analyze Current Function`
3. Pergunte: "Há algum bug nesta função?"
4. Revise sugestões antes de aplicar

### Para Revisão de Código Sensível:
1. Selecione apenas o trecho crítico
2. `Analyze Selection with Limited Context`
3. Pergunte: "Esta lógica está segura?"
4. Confirme mudanças uma por vez

### Para Otimização Performance:
1. Cursor na função lenta
2. `Analyze Current Function`
3. Pergunte: "Como otimizar performance?"
4. Aplique mudanças incrementalmente

## 🔄 Atualizar a Extensão

Se fizer mudanças na extensão:
```powershell
cd "d:\PjePlus\Agente"
instalar_extensao.bat
```

## 🆘 Solução de Problemas

### Extensão não aparece no menu
1. Verifique se está instalada: VS Code → Extensions → procure "Restricted Copilot"
2. Recarregue janela: **Ctrl+Shift+P** → "Developer: Reload Window"

### Configurações não funcionam
1. Feche e abra o VS Code
2. Verifique se configurações estão no escopo correto (User vs Workspace)

### Análise não aparece
1. Certifique-se que cursor está dentro de uma função
2. Para seleção, certifique-se que há texto selecionado
3. Verifique console de desenvolvimento: **Help** → **Toggle Developer Tools**

## 💡 Dicas de Uso

- **Use para código sensível**: Perfeito para revisar automações críticas
- **Análise focada**: Mantenha análises pequenas e específicas
- **Pergunte específico**: "Há vazamentos de memória?" vs "Melhore isso"
- **Confirme mudanças**: Sempre revise antes de aplicar sugestões

---

**🎉 Sua extensão Restricted Copilot está pronta para uso no PjePlus!**

**Comando rápido para testar:**
1. Abra `d:\PjePlus\bacen.py`
2. Cursor em qualquer função
3. Botão direito → "Analyze Current Function"
