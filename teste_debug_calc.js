// Script de teste para debug do CALC.user.js
// Use este script no console do navegador para testar os padrões de extração

function testarPadroesExtracao() {
    console.log('=== TESTE DE PADRÕES DE EXTRAÇÃO CALC ===');
    
    // Texto de exemplo de uma planilha
    const textoTeste = `
    PLANILHA DE CÁLCULO TRABALHISTA
    Data da Liquidação: 15/12/2024
    
    VALORES DEVIDOS:
    Bruto Devido ao Reclamante: R$ 12.345,67
    Dedução de Contribuição Social: R$ 1.234,56
    Honorários Líquidos para Patrono do Reclamante: R$ 1.234,50
    
    Documento assinado eletronicamente por ROGERIO APARECIDO ROSA
    em 15/12/2024 às 14:30:25 - ABC123XY
    `;
    
    console.log('Texto de teste:', textoTeste);
    
    // Teste padrão total bruto
    console.log('\n--- TESTANDO TOTAL BRUTO ---');
    const padroesBruto = [
        /bruto\s+devido\s+ao\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i,
        /bruto\s+devido\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i,
        /total\s+bruto\s+devido\s*[:\s]*([r\$\s]*[\d.,]+)/i,
        /valor\s+bruto\s+devido\s+ao\s+reclamante\s*[:\s]*([r\$\s]*[\d.,]+)/i
    ];
    
    padroesBruto.forEach((padrao, i) => {
        const match = textoTeste.match(padrao);
        console.log(`Padrão ${i+1}: ${padrao}`);
        console.log(`Resultado: ${match ? `✅ "${match[0]}" -> Valor: "${match[1]}"` : '❌ Não encontrado'}`);
    });
    
    // Teste padrão data
    console.log('\n--- TESTANDO DATA DE LIQUIDAÇÃO ---');
    const padroesData = [
        /data\s+(?:da\s+)?liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i,
        /data\s+da\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i,
        /data\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i,
        /liquidação.*?(\d{1,2}\/\d{1,2}\/\d{4})/i
    ];
    
    padroesData.forEach((padrao, i) => {
        const match = textoTeste.match(padrao);
        console.log(`Padrão ${i+1}: ${padrao}`);
        console.log(`Resultado: ${match ? `✅ "${match[0]}" -> Data: "${match[1]}"` : '❌ Não encontrado'}`);
    });
    
    // Teste padrão ID
    console.log('\n--- TESTANDO ID DA PLANILHA ---');
    const padroesID = [
        /ROGERIO\s+APARECIDO\s+ROSA.*?(\d{1,2}\/\d{1,2}\/\d{4}).*?(\d{2}:\d{2}:\d{2})\s*-\s*([a-zA-Z0-9]{7,8})/i,
        /documento\s+assinado\s+eletronicamente\s+por.*?-\s*([a-zA-Z0-9]{6,8})/i,
        /\d{1,2}\/\d{1,2}\/\d{4}\s+\d{2}:\d{2}:\d{2}\s*-\s*([a-zA-Z0-9]{6,8})/i
    ];
    
    padroesID.forEach((padrao, i) => {
        const match = textoTeste.match(padrao);
        console.log(`Padrão ${i+1}: ${padrao}`);
        if (match) {
            const idExtraido = match[match.length - 1];
            console.log(`Resultado: ✅ "${match[0]}" -> ID: "${idExtraido}"`);
        } else {
            console.log(`Resultado: ❌ Não encontrado`);
        }
    });
    
    console.log('\n=== FIM DO TESTE ===');
}

// Execute a função no console
testarPadroesExtracao();
