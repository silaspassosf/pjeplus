// Teste com o texto real da decisão do processo 2

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

// Valores esperados corretos do processo 2
const valoresEsperadosProcesso2 = {
    total: '24.059,25',
    dataLiquidacao: '16/06/2025', // Corrigido
    idPlanilha: '02dea67',
    custas: '440,00',
    assinatura: '02dea67',
    inss: null, // Não há débitos previdenciários
    honorarios: '1202,96'
};

// Padrões atuais do CALC.user.js
const padroes = {
    totalBruto: /(?:Total\s+(?:Bruto|Geral|dos\s+Créditos?)[\s\S]*?|TOTAL[\s\S]*?|Valor\s+Total[\s\S]*?|crédito\s+(?:do\s+)?autor[\s\S]*?)(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})/i,
    dataLiquidacao: /(?:Data\s+(?:de\s+)?Liquidação|Atualização|Cálculo|para\s+)[\s\S]*?(\d{1,2}\/\d{1,2}\/\d{4})/i,
    assinaturaId: /(?:Planilha|ID|Identificação|Assinatura|Perito\s*\()[\s\S]*?([A-Za-z0-9]{6,})/i,
    custas: /(?:Custas?\s+(?:de\s+)?(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}))/i,
    honorarios: /(?:Honorários?\s+(?:Advocatícios?|Sucumbenciais?|de\s+Sucumbência)|Hon\.?\s+Adv)[\s\S]*?(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})/i,
    inss: /(?:INSS|Instituto\s+Nacional|débitos\s+(?:ou\s+)?descontos\s+previdenciários)[\s\S]*?(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})/i
};

function testarPadrao(nome, padrao, textoTeste, valorEsperado) {
    console.log(`\n=== Testando ${nome} ===`);
    console.log(`Padrão: ${padrao}`);
    console.log(`Esperado: ${valorEsperado}`);
    
    const match = textoTeste.match(padrao);
    
    if (match) {
        const valorExtraido = match[1];
        console.log(`Extraído: ${valorExtraido}`);
        
        if (valorExtraido === valorEsperado) {
            console.log('✅ SUCESSO!');
            return true;
        } else {
            console.log('❌ FALHOU!');
            console.log(`Match completo:`, match);
            return false;
        }
    } else {
        if (valorEsperado === null) {
            console.log('✅ SUCESSO! (Nenhum valor encontrado, como esperado)');
            return true;
        } else {
            console.log('❌ NENHUM MATCH ENCONTRADO!');
            return false;
        }
    }
}

function executarTestesProcesso2() {
    console.log('🧪 TESTE COM TEXTO REAL - PROCESSO 2');
    console.log('=' + '='.repeat(50));
    
    const testes = [
        ['Total Bruto', padroes.totalBruto, valoresEsperadosProcesso2.total],
        ['Data de Liquidação', padroes.dataLiquidacao, valoresEsperadosProcesso2.dataLiquidacao],
        ['ID/Assinatura', padroes.assinaturaId, valoresEsperadosProcesso2.assinatura],
        ['Custas', padroes.custas, valoresEsperadosProcesso2.custas],
        ['Honorários', padroes.honorarios, valoresEsperadosProcesso2.honorarios],
        ['INSS', padroes.inss, valoresEsperadosProcesso2.inss]
    ];
    
    let sucessos = 0;
    const total = testes.length;
    
    for (const [nome, padrao, esperado] of testes) {
        if (testarPadrao(nome, padrao, textoRealProcesso2, esperado)) {
            sucessos++;
        }
    }
    
    console.log(`\n${'='.repeat(50)}`);
    console.log('📊 RESUMO FINAL');
    console.log(`Sucessos: ${sucessos}/${total}`);
    console.log(`Taxa de acerto: ${(sucessos/total*100).toFixed(1)}%`);
    
    if (sucessos === total) {
        console.log('🎉 TODOS OS TESTES PASSARAM!');
    } else {
        console.log('⚠️  ALGUNS TESTES FALHARAM!');
        console.log('\n📝 Texto utilizado:');
        console.log(textoRealProcesso2);
    }
    
    return sucessos === total;
}

// Executar os testes
executarTestesProcesso2();
