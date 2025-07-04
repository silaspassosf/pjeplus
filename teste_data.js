// Teste específico para padrão de data no texto real
const textoRealProcesso1 = `1001713-02.2024.5.02.0703  Cálculo:   3948  Processo:  Reclamante:  16/10/2019 a 17/09/2024 BANCO BRADESCO S.A. 31/05/2025 WELLINGTON ANGELO DE SOUZA MANZAN  Data Liquidação: Reclamado:  16/10/2024 Data Ajuizamento: Período do Cálculo:  PLANILHA DE CÁLCULO`;

const textoRealProcesso1Atualizado = `30/06/2025  1001713-02.2024.5.02.0703 Reclamante: Data Liquidação:  Cálculo:   3948  WELLINGTON ANGELO DE SOUZA MANZAN 16/10/2024 16/10/2019 a 17/09/2024 Período do Cálculo:  PLANILHA DE ATUALIZAÇÃO DE CÁLCULO  BANCO BRADESCO S.A. Processo:  Data Ajuizamento: Reclamado:`;

console.log("=== TESTE PADRÃO DATA DE LIQUIDAÇÃO ===\n");

// Padrões testados
const padroesData = [
    // Padrão 1: Data Liquidação: dd/mm/yyyy
    {
        nome: "Data Liquidação:",
        regex: /Data\s+Liquidação:\s*(\d{1,2}\/\d{1,2}\/\d{4})/i
    },
    // Padrão 2: dd/mm/yyyy WELLINGTON ANGELO
    {
        nome: "dd/mm/yyyy WELLINGTON",
        regex: /(\d{1,2}\/\d{1,2}\/\d{4})\s+WELLINGTON\s+ANGELO/i
    },
    // Padrão 3: Data Liquidação no formato da planilha de atualização
    {
        nome: "Planilha Atualização",
        regex: /(\d{1,2}\/\d{1,2}\/\d{4})\s+\d{4}-\d{2}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/i
    },
    // Padrão 4: Data no começo seguida de processo
    {
        nome: "dd/mm/yyyy processo",
        regex: /(\d{1,2}\/\d{1,2}\/\d{4})\s+\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/i
    }
];

console.log("--- TESTE NO TEXTO PROCESSO 1 ORIGINAL ---");
padroesData.forEach((padrao, index) => {
    const match = textoRealProcesso1.match(padrao.regex);
    console.log(`${index + 1}. ${padrao.nome}: ${match ? match[1] : 'NÃO ENCONTRADO'}`);
});

console.log("\n--- TESTE NO TEXTO PROCESSO 1 ATUALIZADO ---");
padroesData.forEach((padrao, index) => {
    const match = textoRealProcesso1Atualizado.match(padrao.regex);
    console.log(`${index + 1}. ${padrao.nome}: ${match ? match[1] : 'NÃO ENCONTRADO'}`);
});

// Análise específica do formato real
console.log("\n--- ANÁLISE DO FORMATO REAL ---");
console.log("Texto original:", textoRealProcesso1.substring(0, 150) + "...");
console.log("Texto atualizado:", textoRealProcesso1Atualizado.substring(0, 150) + "...");

// Padrão correto para planilha de atualização (26/06/2025)
const padraoCorreto = /(\d{1,2}\/\d{1,2}\/\d{4})\s+\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}/;
const matchCorreto = textoRealProcesso1Atualizado.match(padraoCorreto);
console.log("\nPadrão correto encontrado:", matchCorreto ? matchCorreto[1] : 'NÃO ENCONTRADO');
console.log("Data esperada: 30/06/2025 (do exemplo real)");
