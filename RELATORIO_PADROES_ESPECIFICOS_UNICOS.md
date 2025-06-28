# RELATÓRIO: Padrões Específicos Únicos - Conforme Determinado

## 1. PADRÕES IMPLEMENTADOS (APENAS OS ESPECÍFICOS)

### ✅ **Campos com Padrões Únicos Específicos:**

1. **total (Total bruto devido)**: 
   - **Padrão único**: `/bruto\s+devido\s+ao\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i`
   - **Busca exatamente**: "Bruto Devido ao Reclamante"

2. **y (INSS do autor)**:
   - **Padrão único**: `/dedução\s+de\s+contribuição\s+social\s*[:\s]*[\(]?([r\$\s]*[\d.,]+)[\)]?/i`
   - **Busca exatamente**: "DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL"

3. **hav (Honorários advocatícios)**:
   - **Padrão único**: `/honorários\s+líquidos\s+para\s+patrono\s+do\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i`
   - **Busca exatamente**: "HONORÁRIOS LÍQUIDOS PARA PATRONO DO RECLAMANTE"

4. **data (Data de liquidação)**:
   - **Padrão único**: `/data\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i`
   - **Busca exatamente**: "Data Liquidação:"

5. **idd (ID da planilha)**:
   - **Padrão único**: `/às\s+\d{2}:\d{2}:\d{2}\s*-\s*([a-zA-Z0-9]{7,8})\s*$/im`
   - **Busca exatamente**: "às HH:MM:SS - ID" no final do documento

## 2. CAMPOS REMOVIDOS

- **inr (INSS Bruto da Reclamada)**: Removido completamente (não solicitado)
- **Todos os padrões gerais**: Removidos conforme instruções

## 3. ESTRUTURA FINAL DE EXTRAÇÃO

```javascript
// Total: APENAS "Bruto Devido ao Reclamante"
padroesBruto = [/bruto\s+devido\s+ao\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i];

// INSS Autor: APENAS "DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL"  
padroesINSSAutor = [/dedução\s+de\s+contribuição\s+social\s*[:\s]*[\(]?([r\$\s]*[\d.,]+)[\)]?/i];

// Honorários: APENAS "HONORÁRIOS LÍQUIDOS PARA PATRONO DO RECLAMANTE"
padroesHonorarios = [/honorários\s+líquidos\s+para\s+patrono\s+do\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i];

// Data: APENAS "Data Liquidação:"
padroesData = [/data\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i];

// ID: APENAS assinatura eletrônica final
padroesID = [/às\s+\d{2}:\d{2}:\d{2}\s*-\s*([a-zA-Z0-9]{7,8})\s*$/im];
```

## 4. DADOS ESPERADOS PARA TESTE

```javascript
dadosExtraidos.planilha = {
    idd: "9a990d8",           // Via padrão de assinatura
    data: "01/04/2025",       // Via "Data Liquidação:"
    total: "34572,70",        // Via "Bruto Devido ao Reclamante"
    y: "11,28",               // Via "DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL"
    hav: "3457,27",           // Via "HONORÁRIOS LÍQUIDOS PARA PATRONO DO RECLAMANTE"
    inr: null,                // Removido
    mm: null,                 // Não visível na página 1
    irr: null,                // Não visível na página 1
    rog: null                 // Não visível na página 1 (mantém busca por Rogério)
};
```

## 5. VANTAGENS DA ABORDAGEM ESPECÍFICA

1. **Precisão**: Busca exatamente os campos informados
2. **Performance**: Menos regex para processar
3. **Confiabilidade**: Sem falsos positivos de padrões gerais
4. **Manutenibilidade**: Código mais limpo e focado
5. **Debug**: Mais fácil identificar problemas

## 6. PRÓXIMO TESTE

Agora o script:
- ✅ Busca **APENAS** os padrões específicos informados
- ✅ Remove todos os padrões gerais não solicitados  
- ✅ Foca nos campos exatos do screenshot da planilha
- ✅ Mantém logging detalhado para cada campo específico

**Para testar**: Faça upload do PDF e verifique se extrai exatamente os 5 campos com os valores corretos.
