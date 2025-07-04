// Teste da extração de dados da planilha corrigida
// Simula o texto extraído do PDF da planilha

const textoTeste = `
1001713-02.2024.5.02.0703  Cálculo:   3948  Processo:  Reclamante:  16/10/2019 a 17/09/2024 BANCO BRADESCO S.A. 31/05/2025 WELLINGTON ANGELO DE SOUZA MANZAN  Data Liquidação: Reclamado:  16/10/2024 Data Ajuizamento: Período do Cálculo:  PLANILHA DE CÁLCULO Resumo do Cálculo  

145.951,09 Bruto Devido ao Reclamante

LÍQUIDO DEVIDO AO RECLAMANTE   145.951,09 HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE   7.297,55 IRRF SOBRE HONORÁRIOS PARA ADVOGADO DA RECLAMANTE   0,00 IRPF DEVIDO PELO RECLAMANTE   0,00

Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc
`;

// Dados que deveriam ser extraídos
const dadosExtraidos = {
    planilha: {
        rog: null,      
        total: null,    
        y: null,        
        hav: null,      
        mm: null,       
        irr: null,      
        irpf: null,     
        data: null,     
        idd: null,      
        inr: null       
    }
};

// Função de teste da extração (cópia da função corrigida)
function testarExtracao(texto) {
    console.log('=== TESTE DE EXTRAÇÃO ===');
    
    // total - Total bruto devido ao reclamante
    console.log('Buscando total bruto devido ao reclamante...');
    const padroesBruto = [
        /([\d.,]+)\s+bruto\s+devido\s+ao\s+reclamante/i,
        /bruto\s+devido\s+ao\s+reclamante\s+([\d.,]+)/i,
        /total.*?([\d]{2,3}\.[\d]{3},[\d]{2})/i
    ];
    
    let totalMatch = null;
    for (let i = 0; i < padroesBruto.length; i++) {
        totalMatch = texto.match(padroesBruto[i]);
        if (totalMatch) {
            const valor = totalMatch[1].replace(/[^\d.,]/g, '');
            const valorNumerico = parseFloat(valor.replace('.', '').replace(',', '.'));
            if (valorNumerico > 1000) {
                console.log(`✅ Total bruto encontrado com padrão ${i + 1}: "${totalMatch[0]}" -> Valor: "${valor}"`);
                dadosExtraidos.planilha.total = valor;
                break;
            }
        }
    }
    
    // data - Data de liquidação
    console.log('Buscando data de liquidação...');
    const padroesData = [
        /data\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i,
        /(\d{1,2}\/\d{1,2}\/\d{4})/g
    ];
    
    let dataMatch = texto.match(padroesData[0]);
    if (dataMatch) {
        console.log(`✅ Data encontrada: "${dataMatch[0]}" -> Data: "${dataMatch[1]}"`);
        dadosExtraidos.planilha.data = dataMatch[1];
    } else {
        const todasDatas = texto.match(padroesData[1]);
        if (todasDatas && todasDatas.length > 0) {
            dadosExtraidos.planilha.data = todasDatas[todasDatas.length - 1];
            console.log(`✅ Data extraída via fallback: "${dadosExtraidos.planilha.data}"`);
        }
    }
    
    // idd - ID da planilha
    console.log('Buscando ID da planilha...');
    const padroesID = [
        /cálculo\s*[:\s]*(\d+)/i,
        /calculo\s*[:\s]*(\d+)/i
    ];
    
    let idMatch = null;
    for (let i = 0; i < padroesID.length; i++) {
        idMatch = texto.match(padroesID[i]);
        if (idMatch) {
            console.log(`✅ ID da planilha encontrado: "${idMatch[0]}" -> ID: "${idMatch[1]}"`);
            dadosExtraidos.planilha.idd = idMatch[1];
            break;
        }
    }
    
    // hav - Honorários advocatícios
    console.log('Buscando honorários advocatícios...');
    const padroesHonorarios = [
        /honorários\s+líquidos\s+para\s+advogado\s+da\s+reclamante\s+([\d.,]+)/i,
        /honorarios\s+liquidos\s+para\s+advogado\s+da\s+reclamante\s+([\d.,]+)/i
    ];
    
    let havMatch = null;
    for (let i = 0; i < padroesHonorarios.length; i++) {
        havMatch = texto.match(padroesHonorarios[i]);
        if (havMatch) {
            const valor = havMatch[1].replace(/[^\d.,]/g, '');
            console.log(`✅ Honorários encontrados: "${havMatch[0]}" -> Valor: "${valor}"`);
            dadosExtraidos.planilha.hav = valor;
            break;
        }
    }
    
    // irpf - IRPF DEVIDO PELO RECLAMANTE
    console.log('Buscando IRPF DEVIDO PELO RECLAMANTE...');
    const padroesIRPF = [
        /irpf\s+devido\s+pelo\s+reclamante\s+([\d.,]+)/i
    ];
    
    let irpfMatch = null;
    for (let i = 0; i < padroesIRPF.length; i++) {
        irpfMatch = texto.match(padroesIRPF[i]);
        if (irpfMatch) {
            const valor = irpfMatch[1].replace(/[^\d.,]/g, '');
            console.log(`✅ IRPF devido encontrado: "${irpfMatch[0]}" -> Valor: "${valor}"`);
            dadosExtraidos.planilha.irpf = valor;
            break;
        }
    }
    
    // rog - Assinatura do Rogério
    console.log('Buscando assinatura eletrônica...');
    const padroesRogerio = [
        /documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+)/gi
    ];
    
    let rogerioMatch = null;
    const matches = texto.matchAll(padroesRogerio[0]);
    for (let match of matches) {
        const nome = match[1].trim();
        if (nome.includes('ROGERIO') || nome.includes('GABRIELA') || nome.length > 10) {
            console.log(`✅ Assinatura encontrada: "${match[0]}" -> Nome: "${nome}"`);
            dadosExtraidos.planilha.rog = `Documento assinado eletronicamente por ${nome}`;
            break;
        }
    }
    
    console.log('\n=== RESULTADO DA EXTRAÇÃO ===');
    console.log('TOTAL DEVIDO:', dadosExtraidos.planilha.total);
    console.log('DATA LIQUIDAÇÃO:', dadosExtraidos.planilha.data);
    console.log('ID PLANILHA:', dadosExtraidos.planilha.idd);
    console.log('HONORÁRIOS ADV:', dadosExtraidos.planilha.hav);
    console.log('IRPF DEVIDO:', dadosExtraidos.planilha.irpf);
    console.log('ASSINATURA:', dadosExtraidos.planilha.rog);
    
    // Verifica se os dados esperados foram extraídos
    const esperados = {
        total: '145.951,09',
        data: '31/05/2025',
        idd: '3948',
        hav: '7.297,55',
        irpf: '0,00'
    };
    
    console.log('\n=== VALIDAÇÃO ===');
    let sucessos = 0;
    for (let campo in esperados) {
        const extraido = dadosExtraidos.planilha[campo];
        const esperado = esperados[campo];
        if (extraido === esperado) {
            console.log(`✅ ${campo.toUpperCase()}: CORRETO (${extraido})`);
            sucessos++;
        } else {
            console.log(`❌ ${campo.toUpperCase()}: ERRO - Extraído: "${extraido}" | Esperado: "${esperado}"`);
        }
    }
    
    console.log(`\n=== RESULTADO FINAL ===`);
    console.log(`Sucessos: ${sucessos}/${Object.keys(esperados).length}`);
    console.log(`Taxa de sucesso: ${(sucessos/Object.keys(esperados).length*100).toFixed(1)}%`);
}

// Executa o teste
testarExtracao(textoTeste);
