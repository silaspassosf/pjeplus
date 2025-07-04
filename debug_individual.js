// Debug individual dos padrões

const texto = `Demonstrativo de Honorários Nome: HONORÁRIOS DEVIDOS PELO RECLAMADO Valores Calculados C=(A x B) Valor (C) Alíquota (B) Descrição Credor Ocorrência Base (A) Composição de Base: (Bruto) x 5,00% 31/05/2025 145.951,09 5,00 % 7.297,55 HONORÁRIOS ADVOCATÍCIOS ADVOGADO DA RECLAMANTE 7.297,55 Total

VERBAS 145.951,09 145.951,09 Bruto Devido ao Reclamante
Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc
Custas, pela Reclamada, no importe de R$ 1.000,00, calculadas sobre a condenação, ora arbitrada em R$ 50.000,00. 07 de março de 2025`;

console.log('=== DEBUG INDIVIDUAL DOS PADRÕES ===');

console.log('\n--- TESTE HONORÁRIOS ---');
const padroesHonorarios = [
    /HONOR[ÁA]RIOS?\s*L[ÍI]QUIDOS?\s*PARA\s*ADVOGADO[^\d]*?(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    /(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi,
    /5,00\s*%\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi,
    /(\d{1,3}(?:\.\d{3})*,\d{2})\s+HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi,
    /7\.297,55/gi // Teste específico
];

padroesHonorarios.forEach((padrao, i) => {
    const match = texto.match(padrao);
    console.log(`Padrão ${i + 1}: ${match ? `ENCONTROU: "${match[0]}" -> ${match[1] || match[0]}` : 'NÃO ENCONTROU'}`);
});

console.log('\n--- TESTE ASSINATURA ---');
const padroesAssinatura = [
    /Documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+[A-Z])\s*,?\s*em\s+[\d\/]+,\s+às\s+[\d:]+\s+-\s+([a-z0-9]{6,})/gi,
    /Documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+)\s*,?\s*em\s+[\d\/]+,\s+às\s+[\d:]+\s+-\s+([a-z0-9]+)/gi,
    /GABRIELA\s+CARR/gi, // Teste específico
    /28142dc/gi // Teste específico
];

padroesAssinatura.forEach((padrao, i) => {
    const match = texto.match(padrao);
    console.log(`Padrão ${i + 1}: ${match ? `ENCONTROU: "${match[0]}" -> grupos: [${match[1] || 'N/A'}, ${match[2] || 'N/A'}]` : 'NÃO ENCONTROU'}`);
});

console.log('\n--- ANÁLISE DO TEXTO ---');
console.log('Texto contém "HONORÁRIOS": ', texto.includes('HONORÁRIOS'));
console.log('Texto contém "ADVOCATÍCIOS": ', texto.includes('ADVOCATÍCIOS'));
console.log('Texto contém "7.297,55": ', texto.includes('7.297,55'));
console.log('Texto contém "GABRIELA CARR": ', texto.includes('GABRIELA CARR'));
console.log('Texto contém "28142dc": ', texto.includes('28142dc'));

console.log('\n--- BUSCA MANUAL ---');
// Busca manual pelos valores esperados
const honorariosIndex = texto.indexOf('7.297,55');
if (honorariosIndex !== -1) {
    const contexto = texto.substring(Math.max(0, honorariosIndex - 50), honorariosIndex + 100);
    console.log('Contexto do valor dos honorários:', contexto);
}

const assinaturaIndex = texto.indexOf('GABRIELA CARR');
if (assinaturaIndex !== -1) {
    const contexto = texto.substring(Math.max(0, assinaturaIndex - 50), assinaturaIndex + 100);
    console.log('Contexto da assinatura:', contexto);
}
