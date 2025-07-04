// Script de teste para verificar as melhorias do CALC.user.js
// com dados reais dos processos em calcextrai.md

// Simulando as funções principais do CALC.user.js para teste
let dadosExtraidos = {
    sentenca: {
        HPS: null,
        ds: null,
        hp1: null,
        custas: null,
        resp: null
    },
    acordao: {
        rec: null,console.log('=== ANÁLISE DOS TESTES ===');
console.log('Teste 1: Verifica extração com GABRIELA CARR e dados do processo real');
console.log('Teste 2: Verifica extração com ROGÉRIO e padrões alternativos');
console.log('Ambos os testes devem extrair corretamente: data, total, ID e assinatura');     custasAc: null
    },
    planilha: {
        rog: null,
        isRogerio: false,
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

function segmentarTexto(texto) {
    console.log('=== INICIANDO SEGMENTAÇÃO DO TEXTO ===');
    
    const segmentos = {
        sentenca: '',
        acordao: '',
        planilhaCalculos: '',
        planilhaAtualizacao: '',
        textoCompleto: texto
    };
    
    // Padrões contextuais imutáveis identificados em processos reais
    const marcadoresSentenca = [
        /SENTENÇA/i,
        /III\s*–\s*DISPOSITIVO/i,
        /Ante\s+todo\s+o\s+exposto/i,
        /condenar\s+a\s+reclamada/i,
        /Custas[,\s]+pela\s+Reclamada/i,
        /honorários\s+periciais.*em\s+R\$\s*[\d.,]+/i,
        /TERMO\s+DE\s+AUDIÊNCIA.*?foram\s+apregoados/i
    ];
    
    const marcadoresAcordao = [
        /ACÓRDÃO/i,
        /Embargos\s+de\s+Declaração/i,
        /recurso.*ordinário/i,
        /reforma.*sentença/i,
        /mantém.*sentença/i,
        /Vistos\s*etc\./i,
        /A\s+reclamada\s+opõe\s+Embargos/i
    ];
    
    // Padrões mais robustos para planilhas baseados nos exemplos reais
    const marcadoresPlanilhaCalculo = [
        /PLANILHA\s+DE\s+CÁLCULO/i,
        /Resumo\s+do\s+Cálculo/i,
        /\d+\s+Processo:\s+Reclamante:/i,  // Padrão: "3948 Processo: Reclamante:"
        /Cálculo:\s+\d+\s+Processo:/i,     // Padrão: "Cálculo: 3948 Processo:"
        /Data\s+Liquidação:.*?Reclamado:/i,
        /Total\s+Devido\s+pelo\s+Reclamado/i,
        /Descrição\s+do\s+Bruto\s+Devido/i
    ];
    
    const marcadoresPlanilhaAtualizacao = [
        /PLANILHA\s+DE\s+ATUALIZAÇÃO/i,
        /Resumo\s+da\s+Atualização/i,
        /Atualização\s+liquidada\s+por\s+offline/i,
        /Data\s+Liquidação:.*?PLANILHA\s+DE\s+ATUALIZAÇÃO/i,
        /Saldo\s+Devedor\s+em\s+\d{2}\/\d{2}\/\d{4}/i
    ];
    
    // Encontra limites das seções
    let inicioSentenca = -1, inicioAcordao = -1, inicioPlanilhaCalc = -1, inicioPlanilhaAtual = -1;
    
    // Busca sentença
    for (const marcador of marcadoresSentenca) {
        const match = texto.match(marcador);
        if (match && inicioSentenca === -1) {
            inicioSentenca = match.index;
            console.log(`Sentença encontrada com marcador: "${match[0]}" na posição ${inicioSentenca}`);
            break;
        }
    }
    
    // Busca acórdão
    for (const marcador of marcadoresAcordao) {
        const match = texto.match(marcador);
        if (match) {
            inicioAcordao = match.index;
            console.log(`Acórdão encontrado com marcador: "${match[0]}" na posição ${inicioAcordao}`);
            break;
        }
    }
    
    // Busca planilha de cálculo com múltiplos padrões
    for (const marcador of marcadoresPlanilhaCalculo) {
        const match = texto.match(marcador);
        if (match && inicioPlanilhaCalc === -1) {
            inicioPlanilhaCalc = match.index;
            console.log(`Planilha de cálculo encontrada com marcador: "${match[0]}" na posição ${inicioPlanilhaCalc}`);
            break;
        }
    }
    
    // Se não encontrou planilha pelos marcadores principais, busca por padrão de assinatura de contabilista
    if (inicioPlanilhaCalc === -1) {
        const assinaturaMatch = texto.match(/Cálculo\s+liquidado\s+por\s+offline.*?Documento\s+assinado\s+eletronicamente\s+por\s+(?:GABRIELA|ROGERIO|[A-Z]+\s+[A-Z]+)/i);
        if (assinaturaMatch) {
            // Busca retroativamente o início da planilha
            const textoAntes = texto.substring(0, assinaturaMatch.index);
            const inicioRetroativo = textoAntes.search(/(?:PLANILHA|Processo:\s*\d|\d+\s+Processo:)[\s\S]*$/i);
            if (inicioRetroativo !== -1) {
                inicioPlanilhaCalc = inicioRetroativo;
                console.log(`Planilha de cálculo encontrada por busca retroativa na posição ${inicioPlanilhaCalc}`);
            }
        }
    }
    
    // Define seções baseado nas posições encontradas
    const posicoes = [
        { nome: 'sentenca', inicio: inicioSentenca },
        { nome: 'acordao', inicio: inicioAcordao },
        { nome: 'planilhaCalc', inicio: inicioPlanilhaCalc },
        { nome: 'planilhaAtual', inicio: inicioPlanilhaAtual }
    ].filter(p => p.inicio !== -1).sort((a, b) => a.inicio - b.inicio);
    
    for (let i = 0; i < posicoes.length; i++) {
        const atual = posicoes[i];
        const proximo = posicoes[i + 1];
        let fim = proximo ? proximo.inicio : texto.length;
        
        // Para planilha de cálculo, limita até encontrar planilha de atualização ou assinatura
        if (atual.nome === 'planilhaCalc' && !proximo) {
            const limitePlanilha = texto.search(/(?:PLANILHA\s+DE\s+ATUALIZAÇÃO|Documento\s+assinado\s+eletronicamente\s+por\s+(?:GABRIELA|ROGERIO|[A-Z]+\s+[A-Z]+))/i);
            if (limitePlanilha !== -1 && limitePlanilha > atual.inicio) {
                fim = limitePlanilha;
            }
        }
        
        const secao = texto.substring(atual.inicio, fim);
        
        switch (atual.nome) {
            case 'sentenca':
                segmentos.sentenca = secao;
                console.log(`Seção sentença extraída: ${secao.length} caracteres`);
                break;
            case 'acordao':
                segmentos.acordao = secao;
                console.log(`Seção acórdão extraída: ${secao.length} caracteres`);
                break;
            case 'planilhaCalc':
                segmentos.planilhaCalculos = secao;
                console.log(`Seção planilha de cálculos extraída: ${secao.length} caracteres`);
                break;
            case 'planilhaAtual':
                segmentos.planilhaAtualizacao = secao;
                console.log(`Seção planilha de atualização extraída: ${secao.length} caracteres`);
                break;
        }
    }
    
    console.log('=== RESULTADO DA SEGMENTAÇÃO ===');
    console.log(`Sentença: ${segmentos.sentenca.length} caracteres`);
    console.log(`Acórdão: ${segmentos.acordao.length} caracteres`);
    console.log(`Planilha Cálculos: ${segmentos.planilhaCalculos.length} caracteres`);
    console.log(`Planilha Atualização: ${segmentos.planilhaAtualizacao.length} caracteres`);
    
    return segmentos;
}

function analisarPlanilha(texto) {
    console.log('=== INICIANDO ANÁLISE DA PLANILHA ===');
    
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
        /(\d{1,2}\/\d{1,2}\/\d{4})\s+WELLINGTON\s+ANGELO/i,
        /Data\s+Liquidação:\s*(\d{1,2}\/\d{1,2}\/\d{4})/i,
        /data\s+liquidação\s*[:\s]*(\d{1,2}\/\d{1,2}\/\d{4})/i,
        /data\s+liquidação\s+(\d{1,2}\/\d{1,2}\/\d{4})/i
    ];
    
    let dataMatch = null;
    for (let i = 0; i < padroesData.length; i++) {
        dataMatch = texto.match(padroesData[i]);
        if (dataMatch) {
            console.log(`✅ Data encontrada com padrão ${i + 1}: "${dataMatch[0]}" -> Data: "${dataMatch[1]}"`);
            dadosExtraidos.planilha.data = dataMatch[1];
            break;
        }
    }
    
    // Busca assinatura e ID
    console.log('Buscando assinatura do perito e ID da planilha...');
    const padroesAssinatura = [
        /Documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+[A-Z])\s*,?\s*em\s+[\d\/]+,\s+às\s+[\d:]+\s+-\s+([a-z0-9]{6,})/gi,
        /documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+[A-Z])\s*,?\s*.*?às\s+[\d:]+\s+-\s+([a-z0-9]{6,})/gi
    ];
    
    let rogerioMatch = null;
    let isRogerio = false;
    let idExtraido = null;
    
    for (let i = 0; i < padroesAssinatura.length; i++) {
        const matches = texto.matchAll(padroesAssinatura[i]);
        for (let match of matches) {
            const nome = match[1].trim();
            const potencialId = match[2] ? match[2].trim() : null;
            
            console.log(`Verificando assinatura: "${nome}" com ID: "${potencialId}"`);
            
            if (nome.includes('ROGERIO')) {
                console.log(`✅ Assinatura de ROGERIO encontrada: "${nome}"`);
                isRogerio = true;
                dadosExtraidos.planilha.rog = nome;
                
                if (potencialId) {
                    idExtraido = potencialId;
                    console.log(`✅ ID da planilha encontrado na assinatura: "${idExtraido}"`);
                }
                
                rogerioMatch = match;
                break;
            } else if (nome.includes('GABRIELA') || nome.length > 10) {
                console.log(`✅ Assinatura de perito/autor da planilha encontrada: "${nome}"`);
                dadosExtraidos.planilha.rog = nome;
                
                if (potencialId) {
                    idExtraido = potencialId;
                    console.log(`✅ ID da planilha encontrado na assinatura: "${idExtraido}"`);
                }
                
                rogerioMatch = match;
                if (nome.includes('GABRIELA')) break;
            }
        }
        if (rogerioMatch) break;
    }
    
    // Armazena o ID se foi encontrado na assinatura
    if (idExtraido) {
        dadosExtraidos.planilha.idd = idExtraido;
    }
    
    dadosExtraidos.planilha.isRogerio = isRogerio;
    
    console.log('=== ANÁLISE DA PLANILHA CONCLUÍDA ===');
    console.log('Dados da planilha extraídos:', dadosExtraidos.planilha);
}

// Teste com dados do primeiro processo do calcextrai.md
console.log('=== TESTE 1: PRIMEIRO PROCESSO ===');

// Simulando dados do primeiro processo (apenas parte relevante)
const textoProcesso1 = `
PLANILHA DE CÁLCULO

3948 Processo: Reclamante: WELLINGTON ANGELO DE SOUZA MANZAN

Data Liquidação: 31/05/2025 WELLINGTON ANGELO DE SOUZA MANZAN

145.951,09 Bruto Devido ao Reclamante

HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE 7.297,55

IRPF DEVIDO PELO RECLAMANTE 0,00

DEDUÇÃO DE CONTRIBUIÇÃO SOCIAL 4.378,53

Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc
`;

// Testa segmentação
const segmentos1 = segmentarTexto(textoProcesso1);

// Testa análise da planilha
analisarPlanilha(textoProcesso1);

console.log('\n=== RESULTADOS DO TESTE 1 ===');
console.log('Data extraída:', dadosExtraidos.planilha.data);
console.log('Total bruto:', dadosExtraidos.planilha.total);
console.log('ID da planilha:', dadosExtraidos.planilha.idd);
console.log('Assinatura:', dadosExtraidos.planilha.rog);
console.log('É Rogério?', dadosExtraidos.planilha.isRogerio);

// Reset para segundo teste
dadosExtraidos.planilha = {
    rog: null,
    isRogerio: false,
    total: null,
    y: null,
    hav: null,
    mm: null,
    irr: null,
    irpf: null,
    data: null,
    idd: null,
    inr: null
};

console.log('\n=== TESTE 2: SEGUNDO PROCESSO ===');

// Simulando dados do segundo processo (apenas parte relevante)
const textoProcesso2 = `
PLANILHA DE CÁLCULO

RESUMO DO CÁLCULO

Total Bruto Devido 13.815,67

Data de Liquidação: 26/06/2025

HONORÁRIOS LÍQUIDOS PARA ADVOGADO 690,78

INSS DEVIDO PELA EMPRESA 5.526,27

Documento assinado eletronicamente por ROGÉRIO DA SILVA SANTOS, em 26/06/2025, às 14:30:15 - abc123f
`;

// Testa segmentação
const segmentos2 = segmentarTexto(textoProcesso2);

// Testa análise da planilha
analisarPlanilha(textoProcesso2);

console.log('\n=== RESULTADOS DO TESTE 2 ===');
console.log('Data extraída:', dadosExtraidos.planilha.data);
console.log('Total bruto:', dadosExtraidos.planilha.total);
console.log('ID da planilha:', dadosExtraidos.planilha.idd);
console.log('Assinatura:', dadosExtraidos.planilha.rog);
console.log('É Rogério?', dadosExtraidos.planilha.isRogerio);

console.log('\n=== ANÁLISE DOS TESTES ===');
console.log('Teste 1: Verifica extração com GABRIELA CARR e dados do processo real');
console.log('Teste 2: Verifica extração com ROGÉRIO e padrões alternativos');
console.log('Ambos os testes devem extrair corretamente: data, total, ID e assinatura');
`;
