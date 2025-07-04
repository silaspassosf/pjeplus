// Teste exato da lógica do CALC.user.js

// Todos os textos de teste
const testesCompletos = {
    planilhaOriginal: `HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE   7.297,55`,
    planilhaAtualizada: `HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE   7.352,36`,
    demonstrativoCompleto: `Demonstrativo de Honorários  Nome: HONORÁRIOS DEVIDOS PELO RECLAMADO  Valores Calculados   C=(A x B)  Valor (C) Alíquota (B) Descrição   Credor Ocorrência   Base (A) Composição de Base: (Bruto) x 5,00%  31/05/2025   145.951,09   5,00 %   7.297,55 HONORÁRIOS ADVOCATÍCIOS   ADVOGADO DA RECLAMANTE  7.297,55 Total`,
    demonstrativoAtualizado: `- HONORÁRIOS ADVOCATÍCIOS devidos para ADVOGADO DA RECLAMANTE   147.047,11   5,0000%   -   7.352,36   0,00   7.352,36`
};

// Padrões exatos do CALC.user.js (removendo flag global para teste)
const padroesHonorarios = [
    // Padrão 1
    /HONOR[ÁA]RIOS?\s*L[ÍI]QUIDOS?\s*PARA\s*ADVOGADO[^\d]*?(\d{1,3}(?:\.\d{3})*,\d{2})/i,
    // Padrão 2
    /(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/i,
    // Padrão 3
    /5,00\s*%\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/i,
    // Padrão 4
    /HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS?\s*devidos.*?\d{1,3}(?:\.\d{3})*,\d{2}\s*5,0000%\s*-\s*(\d{1,3}(?:\.\d{3})*,\d{2})/i,
    // Padrão 5
    /(?:Demonstrativo.*?Honor[áa]rios.*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*(?:HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS|Total))|(?:(\d{1,3}(?:\.\d{3})*,\d{2})\s*Total(?:\s*$|\s*\n|\s*Pág))/is
];

// Simular exatamente a lógica do CALC.user.js
function simularExtracao(texto, nomeTexto) {
    console.log(`\n=== SIMULANDO: ${nomeTexto} ===`);
    
    let havMatch = null;
    for (let i = 0; i < padroesHonorarios.length; i++) {
        havMatch = texto.match(padroesHonorarios[i]);
        if (havMatch) {
            // Simular a lógica exata do CALC.user.js
            let valor = havMatch[1] || havMatch[2];
            if (valor) {
                valor = valor.replace(/[^\d.,]/g, '');
                console.log(`✅ Honorários encontrados com padrão ${i + 1}: "${havMatch[0].substring(0, 50)}..." -> Valor: "${valor}"`);
                return valor;
            }
        }
    }
    
    console.log('❌ Honorários NÃO encontrados com nenhum padrão');
    return null;
}

// Testar todos
Object.entries(testesCompletos).forEach(([nome, texto]) => {
    simularExtracao(texto, nome);
});

console.log('\n=== RESULTADOS ESPERADOS ===');
console.log('planilhaOriginal: 7.297,55');
console.log('planilhaAtualizada: 7.352,36');
console.log('demonstrativoCompleto: 7.297,55');
console.log('demonstrativoAtualizado: 7.352,36');
