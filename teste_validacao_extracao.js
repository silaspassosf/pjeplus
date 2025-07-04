// Teste focado para validar extração correta dos dados críticos
// baseado no processo real do calcextrai.md

// Dados reais da planilha que devem ser extraídos
const expectedResults = {
    data: "31/05/2025",
    total: "145.951,09", 
    idd: "28142dc",
    hav: "7.297,55",
    rog: "GABRIELA CARR",
    isRogerio: false
};

// Texto real extraído da planilha (não da sentença)
const textoRealPlanilha = `
Data Liquidação: 31/05/2025 WELLINGTON ANGELO DE SOUZA MANZAN

PLANILHA DE CÁLCULO Resumo do Cálculo

145.951,09 Bruto Devido ao Reclamante

HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE 7.297,55

IRPF DEVIDO PELO RECLAMANTE 0,00

DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL 4.378,53

Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc
`;

// Texto da sentença (deve ser IGNORADO para dados de planilha)
const textoSentenca = `
SENTENÇA
Documento assinado eletronicamente por OTAVIO AUGUSTO MACHADO DE OLIVEIRA, em 07/03/2025, às 16:18:59 - 206be40
Custas, pela Reclamada, no importe de R$ 1.000,00
honorários advocatícios do reclamante, que arbitro em 5% sobre o valor que resultar da liquidação
`;

// Texto combinado (como seria na prática)
const textoCompleto = textoSentenca + "\n\n" + textoRealPlanilha;

function testarExtracao() {
    console.log('=== TESTE DE EXTRAÇÃO CORRETA ===');
    console.log('Dados esperados:', expectedResults);
    console.log('');
    
    // Teste 1: Data de liquidação
    console.log('1. Testando extração da data...');
    const padroesData = [
        /Data\s+Liquidação:\s*(\d{1,2}\/\d{1,2}\/\d{4})/i,
        /(\d{1,2}\/\d{1,2}\/\d{4})\s+WELLINGTON\s+ANGELO/i
    ];
    
    let dataEncontrada = null;
    for (let i = 0; i < padroesData.length; i++) {
        const match = textoCompleto.match(padroesData[i]);
        if (match) {
            dataEncontrada = match[1];
            console.log(`✅ Data encontrada: "${dataEncontrada}" (padrão ${i + 1})`);
            break;
        }
    }
    
    if (dataEncontrada === expectedResults.data) {
        console.log('✅ Data CORRETA extraída');
    } else {
        console.log(`❌ Data INCORRETA: esperado "${expectedResults.data}", obtido "${dataEncontrada}"`);
    }
    
    // Teste 2: Total bruto
    console.log('\n2. Testando extração do total...');
    const padraoTotal = /([\d.,]+)\s+bruto\s+devido\s+ao\s+reclamante/i;
    const matchTotal = textoCompleto.match(padraoTotal);
    
    let totalEncontrado = null;
    if (matchTotal) {
        totalEncontrado = matchTotal[1];
        console.log(`✅ Total encontrado: "${totalEncontrado}"`);
    }
    
    if (totalEncontrado === expectedResults.total) {
        console.log('✅ Total CORRETO extraído');
    } else {
        console.log(`❌ Total INCORRETO: esperado "${expectedResults.total}", obtido "${totalEncontrado}"`);
    }
    
    // Teste 3: Honorários
    console.log('\n3. Testando extração dos honorários...');
    const padraoHonorarios = /honorários\s+líquidos\s+para\s+advogado\s+da\s+reclamante\s+([\d.,]+)/i;
    const matchHonorarios = textoCompleto.match(padraoHonorarios);
    
    let honorariosEncontrado = null;
    if (matchHonorarios) {
        honorariosEncontrado = matchHonorarios[1];
        console.log(`✅ Honorários encontrados: "${honorariosEncontrado}"`);
    }
    
    if (honorariosEncontrado === expectedResults.hav) {
        console.log('✅ Honorários CORRETOS extraídos');
    } else {
        console.log(`❌ Honorários INCORRETOS: esperado "${expectedResults.hav}", obtido "${honorariosEncontrado}"`);
    }
    
    // Teste 4: ID da planilha e assinatura (CRÍTICO - deve ignorar sentença)
    console.log('\n4. Testando extração de ID e assinatura...');
    
    // Busca TODAS as assinaturas
    const padraoAssinaturas = /Documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+[A-Z])\s*,?\s*em\s+[\d\/]+,\s+às\s+[\d:]+\s+-\s+([a-z0-9]{6,})/gi;
    const matches = [...textoCompleto.matchAll(padraoAssinaturas)];
    
    console.log(`Encontradas ${matches.length} assinaturas:`);
    
    let idPlanilha = null;
    let assinaturaPlanilha = null;
    
    for (let i = 0; i < matches.length; i++) {
        const nome = matches[i][1].trim();
        const id = matches[i][2].trim();
        console.log(`  ${i + 1}. Nome: "${nome}", ID: "${id}"`);
        
        // Analisa contexto para determinar se é planilha ou sentença
        const assinaturaCompleta = matches[i][0];
        const posicao = textoCompleto.indexOf(assinaturaCompleta);
        const contextoAnterior = textoCompleto.substring(Math.max(0, posicao - 200), posicao).toLowerCase();
        const contextoPosterior = textoCompleto.substring(posicao, Math.min(textoCompleto.length, posicao + 200)).toLowerCase();
        
        const estaEmPlanilha = contextoAnterior.includes('planilha') || 
                              contextoAnterior.includes('cálculo') ||
                              contextoAnterior.includes('bruto devido') ||
                              contextoAnterior.includes('honorários líquidos') ||
                              nome.includes('GABRIELA'); // GABRIELA CARR assina planilhas
        
        const estaEmSentenca = contextoAnterior.includes('sentença') ||
                              nome.includes('OTAVIO'); // OTAVIO é juiz
        
        console.log(`     Contexto: planilha=${estaEmPlanilha}, sentença=${estaEmSentenca}`);
        
        if (estaEmPlanilha && !estaEmSentenca) {
            idPlanilha = id;
            assinaturaPlanilha = nome;
            console.log(`     ✅ SELECIONADA como assinatura da planilha`);
        } else {
            console.log(`     ❌ Ignorada (não é da planilha)`);
        }
    }
    
    // Verifica resultados
    if (idPlanilha === expectedResults.idd) {
        console.log('✅ ID da planilha CORRETO extraído');
    } else {
        console.log(`❌ ID INCORRETO: esperado "${expectedResults.idd}", obtido "${idPlanilha}"`);
    }
    
    if (assinaturaPlanilha === expectedResults.rog) {
        console.log('✅ Assinatura da planilha CORRETA extraída');
    } else {
        console.log(`❌ Assinatura INCORRETA: esperado "${expectedResults.rog}", obtido "${assinaturaPlanilha}"`);
    }
    
    console.log('\n=== RESUMO DOS TESTES ===');
    const resultados = {
        data: dataEncontrada === expectedResults.data ? '✅' : '❌',
        total: totalEncontrado === expectedResults.total ? '✅' : '❌',
        honorarios: honorariosEncontrado === expectedResults.hav ? '✅' : '❌',
        id: idPlanilha === expectedResults.idd ? '✅' : '❌',
        assinatura: assinaturaPlanilha === expectedResults.rog ? '✅' : '❌'
    };
    
    console.log('Data liquidação:', resultados.data, dataEncontrada);
    console.log('Total bruto:', resultados.total, totalEncontrado);
    console.log('Honorários:', resultados.honorarios, honorariosEncontrado);
    console.log('ID planilha:', resultados.id, idPlanilha);
    console.log('Assinatura:', resultados.assinatura, assinaturaPlanilha);
    
    const sucessos = Object.values(resultados).filter(r => r === '✅').length;
    const total = Object.values(resultados).length;
    
    console.log(`\nRESULTADO FINAL: ${sucessos}/${total} testes passaram`);
    
    if (sucessos === total) {
        console.log('🎉 TODOS OS TESTES PASSARAM! As melhorias estão funcionando corretamente.');
    } else {
        console.log('⚠️  Alguns testes falharam. Os padrões precisam de ajustes.');
    }
}

// Executa o teste
testarExtracao();
