# RELATÓRIO: Análise do Screenshot da Planilha PJe-Calc Cidadão

## 1. DADOS EXTRAÍDOS DO SCREENSHOT

### Campos Obrigatórios Identificados:

1. **idd (ID da planilha)**: `469`
   - **Localização**: Canto superior direito: "Cálculo: 469"
   - **Padrão implementado**: `/cálculo\s*[:\s]*(\d+)/i`

2. **data (Data de liquidação)**: `01/04/2025`
   - **Localização**: Campo "Data Liquidação:" no cabeçalho
   - **Padrão implementado**: `/data\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i`

3. **total (Total bruto devido)**: `34.572,70`
   - **Localização**: Valor no campo "Bruto Devido ao Reclamante"
   - **Padrão implementado**: `/bruto\s+devido\s+ao\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i`

4. **y (INSS do autor)**: `1.992,07`
   - **Localização**: Valor na seção "DEPÓSITO FGTS"
   - **Padrão implementado**: `/depósito\s+fgts\s*[:\s]*([r\$\s]*[\d.,]+)/i`

5. **hav (Honorários advocatícios)**: `3.457,27`
   - **Localização**: Calculado como 10% do bruto (34.572,70 × 10%)
   - **Fallback implementado**: Cálculo automático se não encontrado

### Campos Opcionais (não visíveis na página 1):

- **inr (INSS Bruto da Reclamada)**: `null` - não aparece nesta página
- **mm (Meses IRPF)**: `null` - não aparece nesta página  
- **irr (Base IRPF)**: `null` - não aparece nesta página
- **rog (Assinatura Rogério)**: `null` - não aparece nesta página

## 2. PADRÕES IMPLEMENTADOS NO SCRIPT

### Para ID da Planilha (idd):
```javascript
// Padrões específicos do PJe-Calc Cidadão
/cálculo\s*[:\s]*(\d+)/i,
/processo\s*[:\s]*(\d+[-\.]?\d*[-\.]?\d*[-\.]?\d*[-\.]?\d*)/i,
/planilha\s+de\s+cálculo\s*[:\s]*([a-zA-Z0-9]+)/i,
```

### Para Data de Liquidação:
```javascript
// Padrões específicos do PJe-Calc Cidadão
/data\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i,
/data\s+ajuizamento\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i,
/período\s+do\s+cálculo\s*[:\s]*.*?(\d{1,2}\/\d{1,2}\/\d{4})/i,
```

### Para Total Bruto:
```javascript
// Padrões específicos do PJe-Calc Cidadão
/bruto\s+devido\s+ao\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/bruto\s+devido\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/líquido\s+devido\s+ao\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/total\s+devido\s+pelo\s+reclamado\s*[:\s]*([r\$\s]*[\d.,]+)/i,
```

### Para INSS do Autor (y):
```javascript
// Padrões específicos do PJe-Calc Cidadão
/depósito\s+fgts\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/fgts\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/dedução\s+de\s+contribuição\s+social\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/irpf\s+devido\s+pelo\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i,
```

### Para Honorários Advocatícios (hav):
```javascript
// Padrões específicos do PJe-Calc Cidadão
/honorários\s+líquidos\s+para\s+patrono\s+do\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/irpf\s+sobre\s+honorários\s+para\s+patrono\s+do\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i,
/custas\s+judiciais\s+devidas\s+pelo\s+reclamado\s*[:\s]*([r\$\s]*[\d.,]+)/i,
```

## 3. SISTEMA DE FALLBACK

O script implementa fallbacks inteligentes:

1. **Para honorários**: Se não encontrado, calcula automaticamente 10% do total bruto
2. **Para campos críticos**: Sistema de fallback com múltiplos padrões alternativos
3. **Para valores numéricos**: Limpeza automática de formatação (R$, espaços, etc.)

## 4. LOGGING E DEBUG

O script gera logs detalhados no console mostrando:
- Qual padrão encontrou cada campo
- Valores extraídos antes e após limpeza
- Status de cada campo (encontrado/não encontrado)
- Aplicação de fallbacks

## 5. EXEMPLO DE DADOS EXTRAÍDOS

Com base no screenshot, o script deveria extrair:

```javascript
dadosExtraidos.planilha = {
    idd: "469",
    data: "01/04/2025", 
    total: "34572,70",
    y: "1992,07",
    hav: "3457,27",
    inr: null,
    mm: null,
    irr: null,
    rog: null
};
```

## 6. PRÓXIMOS PASSOS

1. **Teste com PDF real**: Verificar se os padrões capturam corretamente os dados
2. **Validação de texto**: Confirmar se o texto extraído pelo PDF.js corresponde ao visual
3. **Refinamento de regex**: Ajustar padrões conforme resultados dos testes
4. **Campos da página 2+**: Expandir para capturar inr, mm, irr se necessário

## 7. ARQUIVOS ATUALIZADOS

- `CALC.user.js`: Script principal com novos padrões específicos do PJe-Calc
- Este relatório: Documentação da análise e implementação
