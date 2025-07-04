// Análise específica dos padrões de data que estão falhando

const textoRealProcesso2 = `
As impugnações apresentadas pela reclamada já foram objeto de esclarecimentos pelo sr. Perito nos Id. ZZZZ, nada havendo a ser reparado no laudo.

Destarte, dou por encerradas as impugnações ao laudo e HOMOLOGO os cálculos de liquidação elaborados pelo sr. Perito (02dea67), fixando o crédito do autor em R$ 24.059,25, referente ao principal acrescido do FGTS, para 16/06/2025, atualizado pelo IPCA-E na fase pré-judicial e, a partir do ajuizamento da ação, pela taxa SELIC (art. 406 do Código Civil), conforme decisão do E. STF nas ADCs 58 e 59 e ADI 5867.

Arbitro honorários periciais contábeis no montante de R$2.500,00, pela reclamada.

Não há débitos ou descontos previdenciários.

Não há deduções fiscais cabíveis.

Honorários advocatícios sucumbenciais pela reclamada, no importe de R$ 1202,96, para 16/06/2025.

Custas de R$ 440,00, pela reclamada, para 05/07/2024.

Ante os termos da decisão proferida pelo E. STF na ADI 5766, e considerando o deferimento dos benefícios da justiça gratuita ao autor, é indevido o pagamento de honorários sucumbenciais pelo trabalhador ao advogado da parte reclamada.

Intimações:

Documento assinado eletronicamente por ROGERIO APARECIDO ROSA, em 18/06/2025, às 09:16:41 - 02dea67
`;

// Análise das datas no texto:
console.log('🔍 ANÁLISE DAS DATAS NO TEXTO REAL');
console.log('='.repeat(50));

console.log('\n📅 Datas encontradas no texto:');
const todasAsDatas = textoRealProcesso2.match(/\d{1,2}\/\d{1,2}\/\d{4}/g);
console.log('Todas as datas:', todasAsDatas);

console.log('\n📝 Contexto das datas:');
// Data de liquidação esperada: 16/06/2025
console.log('1. "para 16/06/2025" - Esta é a data de liquidação');
console.log('2. "para 16/06/2025" - Esta é repetida para honorários');  
console.log('3. "para 05/07/2024" - Esta é a data das custas');
console.log('4. "em 18/06/2025" - Esta é a data da assinatura');

// Valores esperados
const esperados = {
    dataLiquidacao: '16/06/2025',
    dataCustas: '05/07/2024'
};

// Padrões atuais
const padraoAtualDataLiquidacao = /(?:Data\s+(?:de\s+)?Liquidação|Atualização|Cálculo|para\s+)[\s\S]*?(\d{1,2}\/\d{1,2}\/\d{4})/i;
const padraoAtualCustas = /(?:Custas?\s+(?:de\s+)?(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}))/i;

console.log('\n🧪 TESTE DO PADRÃO ATUAL - DATA DE LIQUIDAÇÃO');
console.log('Padrão atual:', padraoAtualDataLiquidacao);
const matchDataLiquidacao = textoRealProcesso2.match(padraoAtualDataLiquidacao);
console.log('Match encontrado:', matchDataLiquidacao);
if (matchDataLiquidacao) {
    console.log('Data extraída:', matchDataLiquidacao[1]);
    console.log('Esperada:', esperados.dataLiquidacao);
    console.log('Está correto?', matchDataLiquidacao[1] === esperados.dataLiquidacao ? '✅' : '❌');
}

console.log('\n🧪 TESTE DO PADRÃO ATUAL - CUSTAS');
console.log('Padrão atual:', padraoAtualCustas);
const matchCustas = textoRealProcesso2.match(padraoAtualCustas);
console.log('Match encontrado:', matchCustas);
if (matchCustas) {
    console.log('Valor extraído:', matchCustas[1]);
    console.log('Esperado: 440,00');
    console.log('Está correto?', matchCustas[1] === '440,00' ? '✅' : '❌');
}

// Vamos analisar o problema específico
console.log('\n🔍 ANÁLISE DO PROBLEMA');
console.log('='.repeat(30));

// O padrão de data de liquidação está pegando a primeira data após "para"
// Mas precisamos pegar especificamente a data relacionada ao crédito do autor
// No texto: "fixando o crédito do autor em R$ 24.059,25, referente ao principal acrescido do FGTS, para 16/06/2025"

console.log('\n💡 NOVA ESTRATÉGIA - DATA DE LIQUIDAÇÃO');
const novoPadraoDataLiquidacao = /(?:crédito\s+(?:do\s+)?autor[\s\S]*?para\s+|fixando[\s\S]*?para\s+)(\d{1,2}\/\d{1,2}\/\d{4})/i;
console.log('Novo padrão:', novoPadraoDataLiquidacao);
const testeLiquidacao = textoRealProcesso2.match(novoPadraoDataLiquidacao);
console.log('Resultado:', testeLiquidacao);
if (testeLiquidacao) {
    console.log('Data extraída:', testeLiquidacao[1]);
    console.log('✅ Correto!');
}

console.log('\n💡 ESTRATÉGIA PARA DATA DAS CUSTAS');
// Precisamos extrair a data que vem após "custas" e o valor
// No texto: "Custas de R$ 440,00, pela reclamada, para 05/07/2024"
const padraoDataCustas = /Custas[\s\S]*?para\s+(\d{1,2}\/\d{1,2}\/\d{4})/i;
console.log('Padrão para data das custas:', padraoDataCustas);
const testeDataCustas = textoRealProcesso2.match(padraoDataCustas);
console.log('Resultado:', testeDataCustas);
if (testeDataCustas) {
    console.log('Data extraída:', testeDataCustas[1]);
    console.log('Esperada:', esperados.dataCustas);
    console.log('✅ Correto!');
}
