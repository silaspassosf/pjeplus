// Teste com valores corretos fornecidos pelo usuário

const valoresesperados = {
    processo1: {
        total: '145.951,09',
        dataLiquidacao: '31/05/2025', 
        id: '28142dc',
        custas: '07 de março de 2025 1000,00',
        assinaturaPlanilha: 'GABRIELA CARR',
        inss: null, // não tem
        honorarios: '7.297,55'
    },
    processo2: {
        total: '24.059,25',
        dataLiquidacao: '01/06/2025',
        id: '02dea67', 
        custas: '440,00 05 de julho de 2024',
        assinaturaPlanilha: 'ROGERIO APARECIDO ROSA',
        inss: null, // não tem
        honorarios: '1.202,96'
    }
};

console.log('=== VALORES CORRETOS ESPECIFICADOS ===');
console.log('PROCESSO 1:');
Object.entries(valoresesperados.processo1).forEach(([key, value]) => {
    console.log(`  ${key}: ${value || 'null'}`);
});

console.log('\nPROCESSO 2:');
Object.entries(valoresesperados.processo2).forEach(([key, value]) => {
    console.log(`  ${key}: ${value || 'null'}`);
});

console.log('\n=== ANÁLISE DOS PROBLEMAS IDENTIFICADOS ===');
console.log('1. Total: extraindo 141.240,25 e 22.559,25 em vez de 145.951,09 e 24.059,25');
console.log('2. Data liquidação: extraindo datas de documentos em vez da data correta da planilha');
console.log('3. ID: extraindo IDs incorretos');  
console.log('4. Honorários: processo 2 deveria ser 1.202,96 não 1.200,00');
console.log('5. Assinatura: correto para processo 1, precisa ajustar lógica para processo 2');
