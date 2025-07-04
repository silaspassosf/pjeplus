// Teste específico com valores corretos fornecidos pelo usuário

const testesComValoresCorretos = {
    processo1: {
        // Texto simulado baseado no calcextrai.md processo 1
        texto: `Demonstrativo de Honorários Nome: HONORÁRIOS DEVIDOS PELO RECLAMADO Valores Calculados C=(A x B) Valor (C) Alíquota (B) Descrição Credor Ocorrência Base (A) Composição de Base: (Bruto) x 5,00% 31/05/2025 145.951,09 5,00 % 7.297,55 HONORÁRIOS ADVOCATÍCIOS ADVOGADO DA RECLAMANTE 7.297,55 Total
        
        VERBAS 145.951,09 145.951,09 Bruto Devido ao Reclamante
        Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc
        Custas, pela Reclamada, no importe de R$ 1.000,00, calculadas sobre a condenação, ora arbitrada em R$ 50.000,00. 07 de março de 2025`,
        
        esperado: {
            total: '145.951,09',
            dataLiquidacao: '31/05/2025',
            id: '28142dc',
            honorarios: '7.297,55',
            assinatura: 'GABRIELA CARR',
            custas: '1.000,00'
        }
    }
};

// Padrões corrigidos do CALC.user.js
const padroesBrutoCorrigidos = [
    /(\d{1,3}(?:\.\d{3})*,\d{2})\s+(?:bruto\s+devido\s+ao\s+reclamante|Bruto\s+Devido\s+ao\s+Reclamante)/i,
    /(?:bruto\s+devido\s+ao\s+reclamante|Bruto\s+Devido\s+ao\s+Reclamante)\s+(\d{1,3}(?:\.\d{3})*,\d{2})/i,
    /verbas\s+(\d{1,3}(?:\.\d{3})*,\d{2})/i,
    /resumo\s+do\s+c[aá]lculo.*?(\d{1,3}(?:\.\d{3})*,\d{2})/gis
];

const padroesDataCorrigidos = [
    /(\d{1,2}\/\d{1,2}\/\d{4})\s+\d{1,3}(?:\.\d{3})*,\d{2}\s+5,00?\s*%.*?HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/i,
    /(\d{1,2}\/\d{1,2}\/\d{4})\s+\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/i,
    /(\d{1,2}\/\d{1,2}\/\d{4})\s+WELLINGTON\s+ANGELO/i,
    /Data\s+Liquidação:\s*(\d{1,2}\/\d{1,2}\/\d{4})/i
];

const padroesAssinatura = [
    /Documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+[A-Z])\s*,?\s*em\s+[\d\/]+,\s+às\s+[\d:]+\s+-\s+([a-z0-9]{6,})/gi,
    /documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+[A-Z])\s*,?\s*.*?às\s+[\d:]+\s+-\s+([a-z0-9]{6,})/gi
];

const padroesHonorariosCorrigidos = [
    /HONOR[ÁA]RIOS?\s*L[ÍI]QUIDOS?\s*PARA\s*ADVOGADO[^\d]*?(\d{1,3}(?:\.\d{3})*,\d{2})/gi,
    /(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi,
    /5,00\s*%\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/gi
];

function testarPadroes(texto, padroes, nome) {
    for (let i = 0; i < padroes.length; i++) {
        const match = texto.match(padroes[i]);
        if (match) {
            return { valor: match[1] || match[2], padrao: i + 1, match: match[0], fullMatch: match };
        }
    }
    return null;
}

console.log('=== VALIDAÇÃO DOS PADRÕES CORRIGIDOS ===');

Object.entries(testesComValoresCorretos).forEach(([nomeProcesso, dados]) => {
    console.log(`\n--- PROCESSO: ${nomeProcesso} ---`);
    
    // Teste Total Bruto
    const totalResult = testarPadroes(dados.texto, padroesBrutoCorrigidos, 'Total Bruto');
    console.log(`Total Bruto: ${totalResult ? totalResult.valor : 'NÃO ENCONTRADO'} (esperado: ${dados.esperado.total})`);
    console.log(`  Status: ${totalResult && totalResult.valor === dados.esperado.total ? '✅ CORRETO' : '❌ ERRO'}`);
    
    // Teste Data
    const dataResult = testarPadroes(dados.texto, padroesDataCorrigidos, 'Data');
    console.log(`Data: ${dataResult ? dataResult.valor : 'NÃO ENCONTRADO'} (esperado: ${dados.esperado.dataLiquidacao})`);
    console.log(`  Status: ${dataResult && dataResult.valor === dados.esperado.dataLiquidacao ? '✅ CORRETO' : '❌ ERRO'}`);
    
    // Teste Assinatura e ID
    const assinaturaResult = testarPadroes(dados.texto, padroesAssinatura, 'Assinatura');
    if (assinaturaResult && assinaturaResult.fullMatch) {
        console.log(`Assinatura: ${assinaturaResult.fullMatch[1]} (esperado: ${dados.esperado.assinatura})`);
        console.log(`ID: ${assinaturaResult.fullMatch[2]} (esperado: ${dados.esperado.id})`);
        console.log(`  Status Assinatura: ${assinaturaResult.fullMatch[1] === dados.esperado.assinatura ? '✅ CORRETO' : '❌ ERRO'}`);
        console.log(`  Status ID: ${assinaturaResult.fullMatch[2] === dados.esperado.id ? '✅ CORRETO' : '❌ ERRO'}`);
    } else {
        console.log(`Assinatura: NÃO ENCONTRADO (esperado: ${dados.esperado.assinatura})`);
        console.log(`ID: NÃO ENCONTRADO (esperado: ${dados.esperado.id})`);
    }
    
    // Teste Honorários
    const honorariosResult = testarPadroes(dados.texto, padroesHonorariosCorrigidos, 'Honorários');
    console.log(`Honorários: ${honorariosResult ? honorariosResult.valor : 'NÃO ENCONTRADO'} (esperado: ${dados.esperado.honorarios})`);
    console.log(`  Status: ${honorariosResult && honorariosResult.valor === dados.esperado.honorarios ? '✅ CORRETO' : '❌ ERRO'}`);
});

console.log('\n=== RESUMO ===');
console.log('✅ = Padrão funcionando corretamente');
console.log('❌ = Padrão precisa de ajuste');
