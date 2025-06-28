# RELATÓRIO: Correções dos Padrões de Extração - Screenshot Atualizado

## 1. DADOS CORRETOS EXTRAÍDOS DO NOVO SCREENSHOT

### Campos Obrigatórios Corrigidos:

1. **idd (ID da planilha)**: `9a990d8` 
   - **Localização**: Final da primeira página, última linha: "Documento assinado eletronicamente por ROGERIO APARECIDO ROSA, em 30/04/2025, às 11:12:39 - 9a990d8"
   - **Novo padrão implementado**: `/documento\s+assinado\s+eletronicamente.*?(\w{7,8})\s*$/im`

2. **data (Data de liquidação)**: `01/04/2025` ✅
   - **Localização**: Campo "Data Liquidação:" no cabeçalho
   - **Status**: Padrão já correto

3. **total (Total bruto devido)**: `34.572,70` ✅
   - **Localização**: Valor no campo "Bruto Devido ao Reclamante"
   - **Status**: Padrão já correto

4. **y (INSS do autor)**: `11,28` (CORRIGIDO)
   - **Localização**: Valor na seção "DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL"
   - **Novo padrão implementado**: `/dedução\s+de\s+contribuição\s+social\s*[:\s]*[\(]?([r\$\s]*[\d.,]+)[\)]?/i`

5. **hav (Honorários advocatícios)**: `3.457,27` (CORRIGIDO)
   - **Localização**: Valor direto do campo "HONORÁRIOS LÍQUIDOS PARA PATRONO DO RECLAMANTE"
   - **Novo padrão implementado**: `/honorários\s+líquidos\s+para\s+patrono\s+do\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i`

## 2. PADRÕES CORRIGIDOS NO SCRIPT

### Para ID da Planilha (idd):
```javascript
// NOVO - Padrões específicos para assinatura eletrônica
/documento\s+assinado\s+eletronicamente.*?(\w{7,8})\s*$/im,
/assinado\s+eletronicamente.*?-\s*([a-zA-Z0-9]{7,8})\s*$/im,
/rogerio\s+aparecido.*?-\s*([a-zA-Z0-9]{7,8})\s*$/im,
/às\s+\d{2}:\d{2}:\d{2}\s*-\s*([a-zA-Z0-9]{7,8})\s*$/im,
```

### Para INSS do Autor (y):
```javascript
// NOVO - Padrões específicos para "DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL"
/dedução\s+de\s+contribuição\s+social\s*[:\s]*[\(]?([r\$\s]*[\d.,]+)[\)]?/i,
/contribuição\s+social\s*[:\s]*[\(]?([r\$\s]*[\d.,]+)[\)]?/i,
/dedução.*?contribuição.*?social\s*[:\s]*[\(]?([r\$\s]*[\d.,]+)[\)]?/i,
```

### Para Honorários Advocatícios (hav):
```javascript
// NOVO - Padrões específicos para "HONORÁRIOS LÍQUIDOS PARA PATRONO DO RECLAMANTE"
/honorários\s+líquidos\s+para\s+patrono\s+do\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/líquidos\s+para\s+patrono\s+do\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/honorários\s+líquidos\s*[:\s]*([r\$\s]*[\d.,]+)/i,
```

## 3. DADOS ESPERADOS PARA TESTE

Com os novos padrões, o script deveria extrair:

```javascript
dadosExtraidos.planilha = {
    idd: "9a990d8",           // ✅ CORRIGIDO
    data: "01/04/2025",       // ✅ OK
    total: "34572,70",        // ✅ OK
    y: "11,28",               // ✅ CORRIGIDO
    hav: "3457,27",           // ✅ CORRIGIDO
    inr: null,                // Não visível na página 1
    mm: null,                 // Não visível na página 1
    irr: null,                // Não visível na página 1
    rog: null                 // Não visível na página 1
};
```

## 4. MELHORIAS IMPLEMENTADAS

1. **ID da Planilha**: Agora busca especificamente pela assinatura eletrônica no final do documento
2. **INSS do Autor**: Foca na seção "DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL" em vez de "DEPÓSITO FGTS"
3. **Honorários**: Busca diretamente no campo "HONORÁRIOS LÍQUIDOS PARA PATRONO DO RECLAMANTE"
4. **Flexibilidade**: Mantém padrões alternativos como fallback

## 5. PRÓXIMOS PASSOS

1. **Testar com PDF real**: Verificar se os novos padrões capturam corretamente
2. **Validar logs**: Confirmar nos logs do console qual padrão encontrou cada campo
3. **Usar Debug**: Botão "Debug: Exportar Texto" para analisar o texto extraído
4. **Ajustar se necessário**: Refinar regex baseado nos resultados dos testes

## 6. ARQUIVOS ATUALIZADOS

- `CALC.user.js`: Script principal com padrões corrigidos
- Este relatório: Documentação das correções implementadas

Os padrões agora estão alinhados com os dados exatos mostrados no screenshot da planilha.
