// Teste específico para demonstrativoAtualizado que não funcionou

const textoProblematico = `- HONORÁRIOS ADVOCATÍCIOS devidos para ADVOGADO DA RECLAMANTE   147.047,11   5,0000%   -   7.352,36   0,00   7.352,36`;

console.log('=== ANALISANDO TEXTO PROBLEMÁTICO ===');
console.log('Texto:', textoProblematico);
console.log('');

// Padrões testados
const padroes = {
    original: /HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS?\s*devidos.*?\d{1,3}(?:\.\d{3})*,\d{2}\s*5,0000%\s*-\s*(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    
    // Padrão mais flexível
    melhorado1: /HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS?\s*devidos.*?5,0000%.*?-\s*(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    
    // Padrão ainda mais simples
    melhorado2: /5,0000%\s*-\s*(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    
    // Padrão baseado no padrão final - último valor da linha
    melhorado3: /HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS.*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*$/gi,
    
    // Padrão mais abrangente - qualquer sequência após percentual
    melhorado4: /5,0+%.*?(\d{1,3}(?:\.\d{3})*,\d{2})\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*(\d{1,3}(?:\.\d{3})*,\d{2})/gi
};

Object.entries(padroes).forEach(([nome, padrao]) => {
    const match = padrao.exec(textoProblematico);
    padrao.lastIndex = 0;
    if (match) {
        console.log(`${nome}: ENCONTROU`);
        console.log(`  Match completo: "${match[0]}"`);
        console.log(`  Grupo 1: "${match[1]}"`);
        if (match[2]) console.log(`  Grupo 2: "${match[2]}"`);
        if (match[3]) console.log(`  Grupo 3: "${match[3]}"`);
    } else {
        console.log(`${nome}: NÃO ENCONTROU`);
    }
    console.log('');
});

console.log('=== ANALISANDO ESTRUTURA DO TEXTO ===');
console.log('Valores encontrados no texto:');
const todosValores = textoProblematico.match(/\d{1,3}(?:\.\d{3})*,\d{2}/g);
console.log(todosValores);
console.log('');
console.log('Esperado: 7.352,36 (deve ser o valor após o traço)');
