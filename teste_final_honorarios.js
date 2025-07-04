// Teste final dos padrões implementados no CALC.user.js

// Padrões implementados exatamente como no CALC.user.js
const padroesHonorariosImplementados = [
    // Padrão 1: Planilhas simples
    /HONOR[ÁA]RIOS?\s*L[ÍI]QUIDOS?\s*PARA\s*ADVOGADO[^\d]*?(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    
    // Padrão 2: Demonstrativo completo
    /(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi,
    
    // Padrão 3: Demonstrativo com alíquota
    /5,00\s*%\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi,
    
    // Padrão 4: Atualização com percentual
    /HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS?\s*devidos.*?\d{1,3}(?:\.\d{3})*,\d{2}\s*5,0000%\s*-\s*(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    
    // Padrão 5: Demonstrativo com múltiplas linhas
    /(?:Demonstrativo.*?Honor[áa]rios.*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*(?:HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS|Total))|(?:(\d{1,3}(?:\.\d{3})*,\d{2})\s*Total(?:\s*$|\s*\n|\s*Pág))/gis
];

// Textos de teste
const testesReais = {
    planilhaOriginal: `HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE   7.297,55`,
    planilhaAtualizada: `HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE   7.352,36`,
    demonstrativoCompleto: `Demonstrativo de Honorários  Nome: HONORÁRIOS DEVIDOS PELO RECLAMADO  Valores Calculados   C=(A x B)  Valor (C) Alíquota (B) Descrição   Credor Ocorrência   Base (A) Composição de Base: (Bruto) x 5,00%  31/05/2025   145.951,09   5,00 %   7.297,55 HONORÁRIOS ADVOCATÍCIOS   ADVOGADO DA RECLAMANTE  7.297,55 Total`,
    demonstrativoAtualizado: `- HONORÁRIOS ADVOCATÍCIOS devidos para ADVOGADO DA RECLAMANTE   147.047,11   5,0000%   -   7.352,36   0,00   7.352,36`
};

// Simular a lógica do CALC.user.js
function testarHonorarios(texto, nomeTexto) {
    console.log(`\n=== TESTANDO: ${nomeTexto} ===`);
    
    let havMatch = null;
    for (let i = 0; i < padroesHonorariosImplementados.length; i++) {
        havMatch = texto.match(padroesHonorariosImplementados[i]);
        if (havMatch) {
            // Simular a lógica do CALC.user.js
            let valor = havMatch[1] || havMatch[2];
            if (valor) {
                valor = valor.replace(/[^\d.,]/g, '');
                console.log(`✅ Honorários encontrados com padrão ${i + 1}: "${havMatch[0]}" -> Valor: "${valor}"`);
                return valor;
            }
        }
    }
    
    console.log('❌ Honorários NÃO encontrados com nenhum padrão');
    return null;
}

// Executar testes
Object.entries(testesReais).forEach(([nome, texto]) => {
    testarHonorarios(texto, nome);
});

console.log('\n=== RESULTADOS ESPERADOS ===');
console.log('planilhaOriginal: 7.297,55');
console.log('planilhaAtualizada: 7.352,36');
console.log('demonstrativoCompleto: 7.297,55');
console.log('demonstrativoAtualizado: 7.352,36');
