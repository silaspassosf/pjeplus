# 🐛 RELATÓRIO DE DEBUG - CALC Script

## PROBLEMAS IDENTIFICADOS NO HML.MD

Analisando a decisão gerada em `HML.MD`, foram identificados os seguintes problemas:

### ❌ **CAMPOS COM VALORES VAZIOS OU INCORRETOS:**

1. **ID da planilha:** `"amente"` (truncado/incorreto)
2. **Total bruto:** `"R$ ,,"` (completamente vazio)
3. **INSS do autor:** `"R$ ."` (vazio, apenas ponto)
4. **Base IRPF:** `"R$ ,"` (vazio, apenas vírgula)

### ✅ **CAMPOS QUE FUNCIONARAM:**

1. **Data:** `"12/09/2024"` (extraída corretamente)
2. **Honorários advocatícios:** `"R$ 13.467"` (correto)
3. **Data de custas:** `"15/05/2024"` (correto)
4. **IRPF meses:** `"5 meses"` (correto)
5. **Rogério Aparecido:** `"honorários periciais contábeis"` (correto)
6. **Status custas:** `"Custas pagas"` (correto)

## MELHORIAS DE DEBUG IMPLEMENTADAS

### 🔍 **1. EXTRAÇÃO DE PDF COM LOG DETALHADO**

- ✅ Log do número de páginas do PDF
- ✅ Log do processamento de cada página
- ✅ Salvamento do texto extraído no localStorage
- ✅ Exibição dos primeiros 1000 caracteres extraídos
- ✅ Separação clara entre páginas do PDF

### 📊 **2. ANÁLISE DETALHADA DA PLANILHA**

- ✅ Log de cada padrão de busca testado
- ✅ Identificação de qual padrão encontrou cada dado
- ✅ Exibição do texto exato encontrado vs valor extraído
- ✅ Status claro de ✅ Encontrado / ❌ Não encontrado

### 🔄 **3. SISTEMA DE FALLBACK COM DEBUG**

- ✅ Log detalhado dos candidatos encontrados
- ✅ Lista de todas as datas encontradas
- ✅ Lista de todos os IDs candidatos
- ✅ Lista de todos os valores monetários
- ✅ Processo de seleção do melhor candidato

### 🎯 **4. GERAÇÃO DE DECISÃO COM RASTREAMENTO**

- ✅ JSON completo dos dados antes da geração
- ✅ Log de cada variável usada na decisão
- ✅ Identificação de valores vazios ou incorretos
- ✅ Mapeamento direto: dado extraído → campo na decisão

### 🛠️ **5. FERRAMENTA DE EXPORTAÇÃO DEBUG**

- ✅ Botão "Debug: Exportar Texto" na interface
- ✅ Relatório completo com dados extraídos
- ✅ Texto integral extraído do PDF
- ✅ Download automático do arquivo de debug
- ✅ Timestamp e metadados incluídos

## PROCESSO DE DEBUG RECOMENDADO

### **Passo 1: Upload e Extração**
1. Fazer upload do PDF problema
2. Verificar console do navegador (F12)
3. Analisar logs de extração página por página

### **Passo 2: Análise dos Padrões**
1. Verificar quais padrões estão encontrando dados
2. Identificar se o texto está sendo extraído corretamente
3. Verificar se as regex estão capturando os valores

### **Passo 3: Exportar Debug**
1. Clicar em "Debug: Exportar Texto"
2. Analisar o arquivo `calc_debug_TIMESTAMP.txt`
3. Verificar texto extraído vs dados encontrados

### **Passo 4: Ajustar Padrões**
1. Identificar padrões específicos do PDF problema
2. Adicionar novos padrões de busca se necessário
3. Testar com o mesmo PDF

## COMANDOS DO CONSOLE PARA DEBUG

```javascript
// Ver dados extraídos atuais
console.log('Dados extraídos:', dadosExtraidos);

// Ver texto extraído salvo
Object.keys(localStorage).filter(k => k.startsWith('calc_texto')).forEach(k => {
    console.log(k, localStorage.getItem(k).substring(0, 500));
});

// Limpar dados para novo teste
dadosExtraidos = {
    sentenca: { HPS: null, ds: null, hp1: null, custas: null, resp: null },
    acordao: { rec: null, custasAc: null },
    planilha: { rog: null, total: null, y: null, hav: null, mm: null, irr: null, data: null, idd: null, inr: null }
};
```

## PRÓXIMOS PASSOS

1. **Testar com PDF problemático:**
   - Upload do PDF que gerou HML.MD
   - Analisar logs detalhados
   - Exportar relatório de debug

2. **Identificar padrões específicos:**
   - Verificar layout exato do PDF
   - Ajustar regex para capturar dados corretamente
   - Adicionar padrões específicos se necessário

3. **Validar correções:**
   - Testar com mesmo PDF
   - Comparar dados extraídos
   - Verificar decisão gerada

## STATUS DE IMPLEMENTAÇÃO

✅ **Logging detalhado de extração PDF**
✅ **Debug de análise de padrões**  
✅ **Sistema de fallback com logs**
✅ **Rastreamento de geração de decisão**
✅ **Ferramenta de exportação debug**
✅ **Interface de debug integrada**

**O script agora está preparado para identificar exatamente onde está o problema na extração de dados!** 🎯

---

**Data:** $(date)  
**Status:** ✅ SISTEMA DE DEBUG IMPLEMENTADO  
**Próximo:** Testar com PDF problemático e ajustar padrões
