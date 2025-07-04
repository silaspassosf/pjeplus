// Teste manual para PROCESSO 2 com valores exatos fornecidos pelo usuário
// Este teste simula o texto que deveria ser extraído para o PROCESSO 2

// Simulação do texto real do PROCESSO 2 baseado nos valores fornecidos
const textoProcesso2 = `
PLANILHA DE CÁLCULO DE LIQUIDAÇÃO DE SENTENÇA

Processo: 0123456-78.2023.4.03.6109

TOTAL BRUTO: R$ 24.059,25

Data de Liquidação: 01/06/2025

CUSTAS PROCESSUAIS: R$ 440,00
Data: 05 de julho de 2024 (sentença)

HONORÁRIOS ADVOCATÍCIOS: R$ 1.202,96

VALOR LÍQUIDO FINAL: R$ 23.619,25

Documento assinado eletronicamente por ROGERIO APARECIDO ROSA, em 18/06/2025, às 09:16:41 - 02dea67

Esta planilha foi elaborada conforme determinação judicial.
`;

// Valores esperados para PROCESSO 2
const valoresEsperados = {
    total: "24.059,25",
    dataLiquidacao: "01/06/2025", 
    id: "02dea67",
    custas: "440,00 05 de julho de 2024 (sentença)",
    assinatura: "Documento assinado eletronicamente por ROGERIO APARECIDO ROSA, em 18/06/2025, às 09:16:41 - 02dea67",
    inss: null, // não tem
    honorarios: "1.202,96"
};

// Padrões de regex do CALC.user.js
const padroes = {
    // Total bruto
    total: /(?:TOTAL\s*BRUTO|TOTAL\s*GERAL|VALOR\s*TOTAL)[:\s]*R?\$?\s*([\d.,]+)/i,
    
    // Data de liquidação
    dataLiquidacao: /(?:Data\s*de\s*Liquidação|Data\s*da\s*Liquidação)[:\s]*(\d{2}\/\d{2}\/\d{4})/i,
    
    // ID da planilha (extração da assinatura)
    id: /Documento\s+assinado\s+eletronicamente.*?-\s*([a-f0-9]{7,8})/i,
    
    // Custas
    custas: /CUSTAS?\s*PROCESSUAIS?[:\s]*R?\$?\s*([\d.,]+(?:\s+\d{2}\s+de\s+\w+\s+de\s+\d{4})?(?:\s*\([^)]*\))?)/i,
    
    // Assinatura completa
    assinatura: /(Documento\s+assinado\s+eletronicamente\s+por\s+[^,]+,\s*em\s+\d{2}\/\d{2}\/\d{4},\s*às\s+\d{2}:\d{2}:\d{2}\s*-\s*[a-f0-9]{7,8})/i,
    
    // INSS
    inss: /(?:INSS|Previdência)[:\s]*R?\$?\s*([\d.,]+)/i,
    
    // Honorários advocatícios
    honorarios: /HONORÁRIOS?\s*ADVOCATÍCIOS?[:\s]*R?\$?\s*([\d.,]+)/i
};

console.log("=== TESTE MANUAL PROCESSO 2 ===");
console.log("Valores esperados:", valoresEsperados);
console.log("\n=== TESTANDO PADRÕES ===");

let todosCorretos = true;

// Teste cada padrão
Object.keys(padroes).forEach(campo => {
    const padrao = padroes[campo];
    const match = textoProcesso2.match(padrao);
    const valorExtraido = match ? match[1] : null;
    const valorEsperado = valoresEsperados[campo];
    
    const correto = (campo === 'inss' && !valorExtraido && !valorEsperado) || 
                   (valorExtraido === valorEsperado);
    
    if (!correto) todosCorretos = false;
    
    console.log(`\n${campo.toUpperCase()}:`);
    console.log(`  Esperado: "${valorEsperado}"`);
    console.log(`  Extraído: "${valorExtraido}"`);
    console.log(`  Status: ${correto ? '✅ CORRETO' : '❌ ERRO'}`);
    
    if (!correto && match) {
        console.log(`  Match completo:`, match);
    }
});

console.log(`\n=== RESULTADO FINAL ===`);
console.log(`Status: ${todosCorretos ? '✅ TODOS OS PADRÕES CORRETOS' : '❌ ALGUNS PADRÕES COM ERRO'}`);

// Teste específico para assinatura completa (caso especial)
console.log("\n=== TESTE ASSINATURA COMPLETA ===");
const matchAssinatura = textoProcesso2.match(padroes.assinatura);
if (matchAssinatura) {
    console.log("Assinatura extraída:", matchAssinatura[1]);
    console.log("Assinatura esperada:", valoresEsperados.assinatura);
    console.log("Match correto:", matchAssinatura[1] === valoresEsperados.assinatura ? '✅' : '❌');
}
