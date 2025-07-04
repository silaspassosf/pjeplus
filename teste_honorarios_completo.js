// Teste completo dos padrões de honorários baseado em calcextrai.md

// Textos reais extraídos de calcextrai.md
const exemplosReais = {
    planilhaOriginal: `HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE   7.297,55`,
    
    planilhaAtualizada: `HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE   7.352,36`,
    
    demonstrativoCompleto: `Demonstrativo de Honorários  Nome: HONORÁRIOS DEVIDOS PELO RECLAMADO  Valores Calculados   C=(A x B)  Valor (C) Alíquota (B) Descrição   Credor Ocorrência   Base (A) Composição de Base: (Bruto) x 5,00%  31/05/2025   145.951,09   5,00 %   7.297,55 HONORÁRIOS ADVOCATÍCIOS   ADVOGADO DA RECLAMANTE  7.297,55 Total`,
    
    demonstrativoAtualizado: `- HONORÁRIOS ADVOCATÍCIOS devidos para ADVOGADO DA RECLAMANTE   147.047,11   5,0000%   -   7.352,36   0,00   7.352,36`,
    
    sentenca: `d) honorários advocatícios do reclamante, que arbitro em 5% sobre o valor que resultar da liquidação, nos termos do artigo 791-A da CLT.`
};

// Padrões atuais do CALC.user.js
const padroes = {
    honorarios1: /(?:HONORÁRIOS?\s*(?:LÍQUIDOS?\s*)?(?:PARA\s*)?ADVOGADO[^\d]*?)(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    honorarios2: /(?:Demonstrativo.*?Honorários.*?)(\d{1,3}(?:\.\d{3})*,\d{2})\s*(?:HONORÁRIOS?\s*ADVOCATÍCIOS|Total)/gis,
    honorarios3: /(?:Total\s*final[^:]*:?\s*)(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    honorarios4: /(?:HONORÁRIOS?\s*ADVOCATÍCIOS?\s*devidos.*?)(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    honorarios5: /(?:(?:Bruto|Base)\s*[^\d]*5,00?%.*?)(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    // Novo padrão para percentual na sentença
    percentualSentenca: /(?:honorários?\s*advocatícios.*?arbitro\s*em\s*)(\d+(?:,\d+)?)\s*%/gi
};

console.log('=== TESTE COMPLETO PADRÕES HONORÁRIOS ===');

function testarPadrao(nome, padrao, texto) {
    const match = padrao.exec(texto);
    padrao.lastIndex = 0; // Reset regex
    return match ? match[1] : 'NÃO ENCONTRADO';
}

function testarTodosOsPadroes(nome, texto) {
    console.log(`\n--- TESTANDO: ${nome} ---`);
    console.log(`1. Padrão básico: ${testarPadrao('honorarios1', padroes.honorarios1, texto)}`);
    console.log(`2. Demonstrativo: ${testarPadrao('honorarios2', padroes.honorarios2, texto)}`);
    console.log(`3. Total final: ${testarPadrao('honorarios3', padroes.honorarios3, texto)}`);
    console.log(`4. Devidos para: ${testarPadrao('honorarios4', padroes.honorarios4, texto)}`);
    console.log(`5. Base 5%: ${testarPadrao('honorarios5', padroes.honorarios5, texto)}`);
    console.log(`6. % Sentença: ${testarPadrao('percentualSentenca', padroes.percentualSentenca, texto)}`);
}

// Testa todos os exemplos
Object.entries(exemplosReais).forEach(([nome, texto]) => {
    testarTodosOsPadroes(nome, texto);
});

console.log('\n=== TESTE PADRÕES ESPECÍFICOS MELHORADOS ===');

// Padrões melhorados baseados na análise
const padroesMelhorados = {
    // Para planilhas simples
    planilhaSimples: /HONOR[ÁA]RIOS?\s*L[ÍI]QUIDOS?\s*PARA\s*ADVOGADO[^\d]*?(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    
    // Para demonstrativo detalhado
    demonstrativoDetalhado: /(?:Demonstrativo.*?Honor[áa]rios.*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*(?:HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS|Total))|(?:(\d{1,3}(?:\.\d{3})*,\d{2})\s*Total(?:\s*$|\s*\n|\s*Pág))/gis,
    
    // Para atualização com percentual
    atualizacaoPercentual: /HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS?\s*devidos.*?(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    
    // Para base com percentual
    basePercentual: /(?:Base.*?5,00?%.*?|Bruto.*?5,00?%.*?)(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    
    // Para percentual na sentença
    percentualSentenca: /honor[áa]rios?\s*advocat[íi]cios.*?arbitro\s*em\s*(\d+(?:,\d+)?)\s*%/gi
};

function testarPadroesMelhorados(nome, texto) {
    console.log(`\n--- TESTANDO MELHORADO: ${nome} ---`);
    Object.entries(padroesMelhorados).forEach(([nomePadrao, padrao]) => {
        const match = padrao.exec(texto);
        padrao.lastIndex = 0;
        const resultado = match ? (match[1] || match[2]) : 'NÃO ENCONTRADO';
        console.log(`${nomePadrao}: ${resultado}`);
    });
}

Object.entries(exemplosReais).forEach(([nome, texto]) => {
    testarPadroesMelhorados(nome, texto);
});

console.log('\n=== ANÁLISE ESPECÍFICA ===');
console.log('Esperado planilha original: 7.297,55');
console.log('Esperado planilha atualizada: 7.352,36'); 
console.log('Esperado demonstrativo: 7.297,55');
console.log('Esperado atualização: 7.352,36');
console.log('Esperado sentença: 5%');
