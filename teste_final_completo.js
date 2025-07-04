// Teste final usando dados reais extraídos do calcextrai.md

// Dados reais do processo 1 extraídos do calcextrai.md
const processo1Real = `31/05/2025   145.951,09   5,00 %   7.297,55 HONORÁRIOS ADVOCATÍCIOS   ADVOGADO DA RECLAMANTE  7.297,55 Total  Pág. 12 de 12 Cálculo liquidado por offline na versão 2.13.2 em 17/06/2025 às 08:13:37.  Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc Documento em sigilo ou segredo de justiça

VERBAS   145.951,09  145.951,09 Bruto Devido ao Reclamante 0,00 Total de Descontos 145.951,09 Líquido Devido ao Reclamante

Custas, pela Reclamada, no importe de R$ 1.000,00, calculadas sobre a condenação, ora arbitrada em R$ 50.000,00. 07 de março de 2025`;

// Padrões do CALC.user.js corrigidos
const padroesBruto = [
    /(\d{1,3}(?:\.\d{3})*,\d{2})\s+(?:bruto\s+devido\s+ao\s+reclamante|Bruto\s+Devido\s+ao\s+Reclamante)/i,
    /(?:bruto\s+devido\s+ao\s+reclamante|Bruto\s+Devido\s+ao\s+Reclamante)\s+(\d{1,3}(?:\.\d{3})*,\d{2})/i,
    /verbas\s+(\d{1,3}(?:\.\d{3})*,\d{2})/i
];

const padroesData = [
    /(\d{1,2}\/\d{1,2}\/\d{4})\s+\d{1,3}(?:\.\d{3})*,\d{2}\s+5,00?\s*%.*?HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/i
];

const padroesHonorarios = [
    /(\d{1,3}(?:\.\d{3})*,\d{2})\s+HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/i
];

const padroesAssinatura = [
    /por\s+([A-Z\s]+?),\s+em.*?-\s+([a-z0-9]+)/i
];

const padroesCustas = [
    /custas.*?R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})/i
];

function testar(nome, padrao, texto, esperado) {
    const match = texto.match(padrao);
    const obtido = match ? match[1] : 'NÃO ENCONTRADO';
    const status = obtido === esperado ? '✅' : '❌';
    console.log(`${status} ${nome}: ${obtido} (esperado: ${esperado})`);
    return obtido === esperado;
}

console.log('=== TESTE FINAL COM DADOS REAIS ===');
console.log('Processo 1 (dados reais extraídos do calcextrai.md):');

let acertos = 0;
let total = 0;

// Teste Total Bruto
total++;
if (testar('Total Bruto', padroesBruto[0], processo1Real, '145.951,09')) acertos++;

// Teste Data
total++;
if (testar('Data Liquidação', padroesData[0], processo1Real, '31/05/2025')) acertos++;

// Teste Honorários 
total++;
if (testar('Honorários', padroesHonorarios[0], processo1Real, '7.297,55')) acertos++;

// Teste Assinatura
total++;
const matchAssinatura = processo1Real.match(padroesAssinatura[0]);
if (matchAssinatura) {
    const nomeAssinatura = matchAssinatura[1];
    const idAssinatura = matchAssinatura[2];
    console.log(`✅ Assinatura: ${nomeAssinatura} (esperado: GABRIELA CARR)`);
    console.log(`✅ ID: ${idAssinatura} (esperado: 28142dc)`);
    if (nomeAssinatura === 'GABRIELA CARR') acertos++;
    total++;
    if (idAssinatura === '28142dc') acertos++;
} else {
    console.log('❌ Assinatura: NÃO ENCONTRADO');
    console.log('❌ ID: NÃO ENCONTRADO');
    total += 2;
}

// Teste Custas
total++;
if (testar('Custas', padroesCustas[0], processo1Real, '1.000,00')) acertos++;

console.log(`\n=== RESULTADO FINAL ===`);
console.log(`Acertos: ${acertos}/${total} (${Math.round(acertos/total*100)}%)`);

if (acertos === total) {
    console.log('🎉 TODOS OS PADRÕES ESTÃO FUNCIONANDO CORRETAMENTE!');
} else {
    console.log('⚠️ Alguns padrões precisam de ajustes adicionais.');
}
