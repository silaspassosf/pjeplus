// Teste para corrigir padrões que capturam valores errados

const exemplosReais = {
    demonstrativoAtualizado: `- HONORÁRIOS ADVOCATÍCIOS devidos para ADVOGADO DA RECLAMANTE   147.047,11   5,0000%   -   7.352,36   0,00   7.352,36`,
    
    demonstrativoCompleto: `Demonstrativo de Honorários  Nome: HONORÁRIOS DEVIDOS PELO RECLAMADO  Valores Calculados   C=(A x B)  Valor (C) Alíquota (B) Descrição   Credor Ocorrência   Base (A) Composição de Base: (Bruto) x 5,00%  31/05/2025   145.951,09   5,00 %   7.297,55 HONORÁRIOS ADVOCATÍCIOS   ADVOGADO DA RECLAMANTE  7.297,55 Total`
};

// Padrões corrigidos
const padroesCorrigidos = {
    // Para atualização - pegar o valor APÓS o percentual, não antes
    atualizacaoPercentual: /HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS?\s*devidos.*?\d{1,3}(?:\.\d{3})*,\d{2}\s*5,0000%\s*-\s*(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    
    // Para demonstrativo - pegar o valor antes de HONORÁRIOS ADVOCATÍCIOS
    demonstrativoDetalhado: /(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi,
    
    // Alternativa para demonstrativo - pegar após alíquota
    demonstrativoAliquota: /5,00\s*%\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi
};

console.log('=== TESTE PADRÕES CORRIGIDOS ===');

function testarPadrao(nome, padrao, texto) {
    const match = padrao.exec(texto);
    padrao.lastIndex = 0;
    return match ? match[1] : 'NÃO ENCONTRADO';
}

Object.entries(exemplosReais).forEach(([nomeExemplo, texto]) => {
    console.log(`\n--- ${nomeExemplo} ---`);
    Object.entries(padroesCorrigidos).forEach(([nomePadrao, padrao]) => {
        const resultado = testarPadrao(nomePadrao, padrao, texto);
        console.log(`${nomePadrao}: ${resultado}`);
    });
});

console.log('\n=== VERIFICANDO MÚLTIPLAS MATCHES ===');

// Teste para ver todas as capturas
function testarTodasAsCapturas(texto, padrao) {
    const matches = [];
    let match;
    while ((match = padrao.exec(texto)) !== null) {
        matches.push(match[1]);
        if (!padrao.global) break;
    }
    padrao.lastIndex = 0;
    return matches;
}

console.log('\nDemonstrativo completo - todas as capturas:');
Object.entries(padroesCorrigidos).forEach(([nome, padrao]) => {
    const capturas = testarTodasAsCapturas(exemplosReais.demonstrativoCompleto, padrao);
    console.log(`${nome}: [${capturas.join(', ')}]`);
});

console.log('\nDemonstrativo atualizado - todas as capturas:');
Object.entries(padroesCorrigidos).forEach(([nome, padrao]) => {
    const capturas = testarTodasAsCapturas(exemplosReais.demonstrativoAtualizado, padrao);
    console.log(`${nome}: [${capturas.join(', ')}]`);
});
