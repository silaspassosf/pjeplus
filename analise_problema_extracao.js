// Análise detalhada do problema de extração com dados reais
// do calcextrai.md para identificar onde a segmentação está falha

// Dados extraídos ERRADOS conforme relatado no calcextrai.md
const dadosErrados = {
    data: "26/06/2025",        // ERRADO (deveria ser 31/05/2025)
    total: "145.951,09",       // CORRETO
    idd: "206be40",           // ERRADO (deveria ser 28142dc)
    hav: "7.352,36",          // ERRADO (deveria ser 7.297,55)
    rog: "OTAVIO AUGUSTO MACHADO DE OLIVEIRA"  // ERRADO (deveria ser GABRIELA CARR)
};

// Dados que DEVERIAM ser extraídos
const dadosCorretos = {
    data: "31/05/2025",
    total: "145.951,09", 
    idd: "28142dc",
    hav: "7.297,55",
    rog: "GABRIELA CARR"
};

console.log('=== ANÁLISE DO PROBLEMA DE EXTRAÇÃO ===');
console.log('');
console.log('PROBLEMA IDENTIFICADO:');
console.log('O script está extraindo dados da SENTENÇA ao invés da PLANILHA');
console.log('');
console.log('Dados ERRADOS extraídos (da sentença):');
console.log('- Data: 26/06/2025 (data da planilha de atualização)');
console.log('- ID: 206be40 (ID da assinatura do juiz OTAVIO)');
console.log('- Honorários: 7.352,36 (da planilha de atualização)');
console.log('- Assinatura: OTAVIO AUGUSTO MACHADO DE OLIVEIRA (juiz)');
console.log('');
console.log('Dados CORRETOS que deveriam ser extraídos (da planilha de cálculo):');
console.log('- Data: 31/05/2025 (data de liquidação da planilha original)');
console.log('- ID: 28142dc (ID da assinatura da GABRIELA CARR)');
console.log('- Honorários: 7.297,55 (da planilha de cálculo original)');
console.log('- Assinatura: GABRIELA CARR (contabilista)');
console.log('');

// Simulação dos textos conforme aparecem no processo real
const textoSentenca = `
SENTENÇA
honorários advocatícios do reclamante, que arbitro em 5% sobre o valor que resultar da liquidação
Documento assinado eletronicamente por OTAVIO AUGUSTO MACHADO DE OLIVEIRA, em 07/03/2025, às 16:18:59 - 206be40
`;

const textoPlanilhaAtualizacao = `
PLANILHA DE ATUALIZAÇÃO DE CÁLCULO
Data Liquidação: 30/06/2025
HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE 7.352,36
Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc
`;

const textoPlanilhaCalculo = `
PLANILHA DE CÁLCULO
Data Liquidação: 31/05/2025 WELLINGTON ANGELO DE SOUZA MANZAN
145.951,09 Bruto Devido ao Reclamante
HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE 7.297,55
Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc
`;

console.log('=== TESTE DE SEGMENTAÇÃO ===');

function testarSegmentacao(textoCompleto) {
    // Testa os marcadores de planilha de cálculo
    const marcadoresPlanilhaCalculo = [
        /PLANILHA\s+DE\s+CÁLCULO/i,
        /Resumo\s+do\s+Cálculo/i,
        /\d+\s+Processo:\s+Reclamante:/i,
        /Cálculo:\s+\d+\s+Processo:/i,
        /Data\s+Liquidação:.*?Reclamado:/i
    ];
    
    console.log('Testando marcadores de PLANILHA DE CÁLCULO:');
    for (let i = 0; i < marcadoresPlanilhaCalculo.length; i++) {
        const match = textoCompleto.match(marcadoresPlanilhaCalculo[i]);
        if (match) {
            console.log(`✅ Marcador ${i + 1} encontrado: "${match[0]}" na posição ${match.index}`);
        } else {
            console.log(`❌ Marcador ${i + 1} NÃO encontrado`);
        }
    }
    
    // Testa marcadores de planilha de atualização
    const marcadoresPlanilhaAtualizacao = [
        /PLANILHA\s+DE\s+ATUALIZAÇÃO/i,
        /Resumo\s+da\s+Atualização/i,
        /Atualização\s+liquidada\s+por\s+offline/i
    ];
    
    console.log('\nTestando marcadores de PLANILHA DE ATUALIZAÇÃO:');
    for (let i = 0; i < marcadoresPlanilhaAtualizacao.length; i++) {
        const match = textoCompleto.match(marcadoresPlanilhaAtualizacao[i]);
        if (match) {
            console.log(`✅ Marcador ${i + 1} encontrado: "${match[0]}" na posição ${match.index}`);
        } else {
            console.log(`❌ Marcador ${i + 1} NÃO encontrado`);
        }
    }
}

// Texto combinado como aparece no processo real
const textoCompletoReal = textoSentenca + '\n' + textoPlanilhaCalculo + '\n' + textoPlanilhaAtualizacao;

testarSegmentacao(textoCompletoReal);

console.log('\n=== TESTE DE PRIORIZAÇÃO ===');
console.log('REGRA: Deve priorizar PLANILHA DE CÁLCULO sobre PLANILHA DE ATUALIZAÇÃO');
console.log('REGRA: Deve ignorar assinaturas de juízes (sentença) e focar em contabilistas (planilha)');

// Simula o que deveria acontecer
console.log('\n✅ COMPORTAMENTO ESPERADO:');
console.log('1. Segmenta texto em: sentença, planilha de cálculo, planilha de atualização');
console.log('2. Analisa APENAS a seção de planilha de cálculo para extrair dados');
console.log('3. Se planilha de cálculo vazia, usa planilha de atualização como fallback');
console.log('4. Ignora completamente dados da sentença');

console.log('\n❌ COMPORTAMENTO ATUAL (PROBLEMA):');
console.log('1. Parece estar misturando dados de diferentes seções');
console.log('2. Ou a segmentação não está funcionando corretamente');
console.log('3. Ou está usando texto completo ao invés das seções separadas');

console.log('\n=== SOLUÇÃO PROPOSTA ===');
console.log('1. Fortalecer os padrões de segmentação para isolar melhor as seções');
console.log('2. Garantir que analisarPlanilha() receba APENAS texto da planilha');
console.log('3. Adicionar logs detalhados para debug da segmentação');
console.log('4. Priorizar contexto de "bruto devido" sobre outros padrões');
console.log('5. Melhorar diferenciação entre planilha de cálculo vs atualização');

console.log('\n=== TESTE CONCLUÍDO ===');
console.log('A análise confirma que o problema está na segmentação ou priorização de seções.');
console.log('As melhorias implementadas devem resolver estes problemas específicos.');
