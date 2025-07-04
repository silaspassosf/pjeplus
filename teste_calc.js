// Script de teste para validar CALC.user.js
// Simula dados reais extraídos dos exemplos em calcextrai.md

// Importar apenas as funções necessárias do CALC.user.js
const fs = require('fs');
const path = require('path');

// Ler o conteúdo do CALC.user.js
const calcScript = fs.readFileSync('CALC.user.js', 'utf8');

// Extrair as funções segmentarTexto e analisarPlanilha
// Criar um contexto simulado para executar as funções
function extrairFuncoes(scriptContent) {
    // Simular ambiente do navegador
    const window = {};
    const document = {};
    const GM = {
        addStyle: () => {},
        setValue: () => {},
        getValue: () => null
    };
    
    // Executar o script em um contexto seguro
    eval(`
        ${scriptContent}
        
        // Exportar funções para teste
        if (typeof segmentarTexto !== 'undefined') {
            exports.segmentarTexto = segmentarTexto;
        }
        if (typeof analisarPlanilha !== 'undefined') {
            exports.analisarPlanilha = analisarPlanilha;
        }
    `);
    
    return exports;
}

// Dados de teste extraídos dos exemplos reais
const exemploProcesso1 = {
    textoCompleto: `PODER JUDICIÁRIO JUSTIÇA DO TRABALHO TRIBUNAL REGIONAL DO TRABALHO DA 2ª REGIÃO 3ª VARA DO TRABALHO DE SÃO PAULO - ZONA SUL 1001713-02.2024.5.02.0703 : WELLINGTON ANGELO DE SOUZA MANZAN : BANCO BRADESCO S.A. TERMO DE AUDIÊNCIA Processo n. 1001713-02.2024.5.02.0703 3ª Vara do Trabalho de São Paulo – Zona Sul Aos sete dias do mês de março do ano de dois mil e vinte e cinco às 13h20, na sala de audiências desta Vara do Trabalho, sob a presidência do MM. Juiz do Trabalho, Dr. Otávio Augusto Machado de Oliveira, foram apregoados os litigantes: Reclamante: Wellington Ângelo de Souza Manzan Reclamada: Banco Bradesco S/A Ausentes as partes, prejudicada a proposta de conciliação, foi submetido o processo a julgamento e esta Vara proferiu a seguinte SENTENÇA I – RELATÓRIO Wellington   Ângelo   de   Souza   Manzan,   qualificado   na   inicial, moveu reclamação trabalhista em face de Banco Bradesco S/A alegando o autor que faz jus a equiparação salarial, que tem direito ao recebimento de comissões, verbas de representação, premiações e PLR, que trabalhou em sobrejornada sem a remuneração correspondente, que não cumpria integralmente intervalo intrajornada, que adquiriu  Documento assinado eletronicamente por OTAVIO AUGUSTO MACHADO DE OLIVEIRA, em 07/03/2025, às 16:18:59 - 206be40  Documento assinado eletronicamente por ANTONIO CARLOS DE SOUZA SANTANA, em 06/05/2025, às 21:37:44 - 17a9993

PLANILHA DE CÁLCULO Resumo do Cálculo  Descrição do Bruto Devido ao Reclamante   Juros   Total Valor Corrigido  AUXILIO ALIMENTAÇÃO   1.854,56   57.456,85 55.602,29 AUXILIO REFEIÇÃO   2.169,37   67.212,39 65.043,02 MULTA DO ARTIGO 477 DA CLT   350,53   10.860,14 10.509,61 PLR PROPORCIONAL DE 2024   336,38   10.421,71 10.085,33  145.951,09 4.710,84 141.240,25 Total  Data Liquidação: 26/06/2025 Cálculo liquidado por offline na versão 2.13.2 em 17/06/2025 às 08:13:37.  Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc

HONORÁRIOS ADVOCATÍCIOS   ADVOGADO DA RECLAMANTE  7.352,36 Total`,
    
    resultadoEsperado: {
        totalDevido: "145.951,09",
        dataLiquidacao: "26/06/2025",
        idPlanilha: "206be40",
        honorarios: "7.352,36",
        assinaturaRogerio: "OTAVIO AUGUSTO MACHADO DE OLIVEIRA",
        inssAutor: "10",
        irpfDevido: "0,00"
    }
};

const exemploProcesso2 = {
    textoCompleto: `PODER JUDICIÁRIO JUSTIÇA DO TRABALHO processo diferente texto exemplo
    
    PLANILHA DE CÁLCULO Resumo do Cálculo  Descrição do Bruto Devido ao Reclamante   Juros   Total Valor Corrigido  AUXILIO ALIMENTAÇÃO   500,00   1.000,00 900,00 AUXILIO REFEIÇÃO   300,00   800,00 700,00  24.059,25 1.500,00 22.559,25 Total  Data Liquidação: 16/06/2025 Cálculo liquidado por offline na versão 2.13.2 em 17/06/2025 às 08:14:16.  Documento assinado eletronicamente por ROGERIO APARECIDO ROSA, em 16/06/2025, às 15:30:45 - 02dea67

    HONORÁRIOS ADVOCATÍCIOS   ADVOGADO DA RECLAMANTE  1.200,00 Total`,
    
    resultadoEsperado: {
        totalDevido: "24.059,25",
        dataLiquidacao: "16/06/2025", 
        idPlanilha: "02dea67",
        honorarios: "1.200,00",
        assinaturaRogerio: "ROGERIO APARECIDO ROSA",
        inssAutor: null,
        irpfDevido: null
    }
};

// Função de teste principal
function executarTestes() {
    console.log("=== TESTE DO SCRIPT CALC.user.js ===");
    console.log("Data/Hora:", new Date().toLocaleString('pt-BR'));
    console.log();
    
    try {
        // Tentativa de extrair funções (pode falhar se as funções não existirem como esperado)
        const funcoes = extrairFuncoes(calcScript);
        
        console.log("✓ Script carregado com sucesso");
        console.log("✓ Funções disponíveis:", Object.keys(funcoes));
        console.log();
        
        // Teste 1: Processo exemplo 1
        console.log("--- TESTE 1: Processo Exemplo 1 ---");
        testarProcesso(funcoes, exemploProcesso1, "Processo 1");
        
        console.log();
        
        // Teste 2: Processo exemplo 2  
        console.log("--- TESTE 2: Processo Exemplo 2 ---");
        testarProcesso(funcoes, exemploProcesso2, "Processo 2");
        
    } catch (error) {
        console.error("❌ Erro ao carregar script:", error.message);
        console.log();
        
        // Teste alternativo usando padrões regex simples
        console.log("--- TESTE ALTERNATIVO COM REGEX SIMPLES ---");
        testarComRegexSimples();
    }
}

function testarProcesso(funcoes, exemplo, nome) {
    try {
        // Testar segmentação de texto
        let segmentos = null;
        if (funcoes.segmentarTexto) {
            segmentos = funcoes.segmentarTexto(exemplo.textoCompleto);
            console.log(`✓ ${nome}: Texto segmentado`);
            console.log("  Segmentos encontrados:", Object.keys(segmentos || {}));
        }
        
        // Testar análise da planilha
        let dadosExtraidos = null;
        if (funcoes.analisarPlanilha) {
            dadosExtraidos = funcoes.analisarPlanilha(exemplo.textoCompleto, segmentos);
            console.log(`✓ ${nome}: Planilha analisada`);
        }
        
        // Comparar resultados esperados
        console.log(`--- Resultados ${nome} ---`);
        if (dadosExtraidos) {
            compararResultados(dadosExtraidos, exemplo.resultadoEsperado);
        } else {
            console.log("❌ Dados não extraídos - função não disponível");
        }
        
    } catch (error) {
        console.error(`❌ Erro no ${nome}:`, error.message);
    }
}

function compararResultados(obtido, esperado) {
    const campos = ['totalDevido', 'dataLiquidacao', 'idPlanilha', 'honorarios', 'assinaturaRogerio', 'inssAutor', 'irpfDevido'];
    
    campos.forEach(campo => {
        const valorObtido = obtido[campo];
        const valorEsperado = esperado[campo];
        
        if (valorObtido === valorEsperado) {
            console.log(`  ✓ ${campo}: "${valorObtido}" ✓`);
        } else {
            console.log(`  ❌ ${campo}: obtido "${valorObtido}" ≠ esperado "${valorEsperado}"`);
        }
    });
}

function testarComRegexSimples() {
    console.log("Executando teste com regex simplificados...");
    
    // Padrões básicos para teste
    const padroes = {
        totalDevido: /(\d+\.?\d*,\d{2})\s+Total/,
        dataLiquidacao: /Data Liquidação:\s*(\d{2}\/\d{2}\/\d{4})/,
        idPlanilha: /(\w{7})\s*$/m,
        honorarios: /HONORÁRIOS.*?(\d+\.?\d*,\d{2})\s+Total/,
        assinaturaRogerio: /assinado eletronicamente por ([A-Z\s]+),/
    };
    
    [exemploProcesso1, exemploProcesso2].forEach((exemplo, index) => {
        console.log(`\n--- Processo ${index + 1} (Regex Simples) ---`);
        
        Object.entries(padroes).forEach(([campo, regex]) => {
            const match = exemplo.textoCompleto.match(regex);
            const valorObtido = match ? match[1] : null;
            const valorEsperado = exemplo.resultadoEsperado[campo];
            
            if (valorObtido === valorEsperado) {
                console.log(`  ✓ ${campo}: "${valorObtido}" ✓`);
            } else {
                console.log(`  ❌ ${campo}: obtido "${valorObtido}" ≠ esperado "${valorEsperado}"`);
            }
        });
    });
}

// Executar testes
executarTestes();
