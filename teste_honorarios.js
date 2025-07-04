// Teste específico para honorários
const textoHonorarios = `Descrição de Débitos do Reclamado por Credor   Valor  LÍQUIDO DEVIDO AO RECLAMANTE   145.951,09 HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE   7.297,55 IRRF SOBRE HONORÁRIOS PARA ADVOGADO DA RECLAMANTE   0,00  153.248,64 Total Devido pelo Reclamado`;

const textoHonorariosAtualizado = `LÍQUIDO DEVIDO AO RECLAMANTE   147.047,11 HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE   7.352,36 IRRF SOBRE HONORÁRIOS PARA ADVOGADO DA RECLAMANTE   0,00  154.399,47 Total Devido Pelo Reclamado`;

const textoHonorariosCompleto = `Demonstrativo de Honorários  Nome: HONORÁRIOS DEVIDOS PELO RECLAMADO  Valores Calculados   C=(A x B)  Valor (C) Alíquota (B) Descrição   Credor Ocorrência   Base (A) Composição de Base: (Bruto) x 5,00%  31/05/2025   145.951,09   5,00 %   7.297,55 HONORÁRIOS ADVOCATÍCIOS   ADVOGADO DA RECLAMANTE  7.297,55 Total`;

console.log("=== TESTE PADRÕES HONORÁRIOS ===\n");

const padroesHonorarios = [
    // Padrão 1: HONORÁRIOS LÍQUIDOS PARA ADVOGADO DA RECLAMANTE
    {
        nome: "Honorários Líquidos",
        regex: /HONORÁRIOS\s+LÍQUIDOS\s+PARA\s+ADVOGADO\s+DA\s+RECLAMANTE\s+(\d{1,3}(?:\.\d{3})*,\d{2})/i
    },
    // Padrão 2: Demonstrativo - valor após %
    {
        nome: "Demonstrativo %",
        regex: /5,00\s+%\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+HONORÁRIOS\s+ADVOCATÍCIOS/i
    },
    // Padrão 3: Total após ADVOGADO DA RECLAMANTE
    {
        nome: "Total final",
        regex: /ADVOGADO\s+DA\s+RECLAMANTE\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+Total/i
    },
    // Padrão 4: Qualquer valor após HONORÁRIOS
    {
        nome: "HONORÁRIOS geral",
        regex: /HONORÁRIOS.*?(\d{1,3}(?:\.\d{3})*,\d{2})/i
    }
];

console.log("--- TESTE NO TEXTO PLANILHA ORIGINAL ---");
padroesHonorarios.forEach((padrao, index) => {
    const match = textoHonorarios.match(padrao.regex);
    console.log(`${index + 1}. ${padrao.nome}: ${match ? match[1] : 'NÃO ENCONTRADO'}`);
});

console.log("\n--- TESTE NO TEXTO PLANILHA ATUALIZADA ---");
padroesHonorarios.forEach((padrao, index) => {
    const match = textoHonorariosAtualizado.match(padrao.regex);
    console.log(`${index + 1}. ${padrao.nome}: ${match ? match[1] : 'NÃO ENCONTRADO'}`);
});

console.log("\n--- TESTE NO DEMONSTRATIVO COMPLETO ---");
padroesHonorarios.forEach((padrao, index) => {
    const match = textoHonorariosCompleto.match(padrao.regex);
    console.log(`${index + 1}. ${padrao.nome}: ${match ? match[1] : 'NÃO ENCONTRADO'}`);
});

console.log("\n--- ANÁLISE ESPECÍFICA ---");
console.log("Esperado planilha original: 7.297,55");
console.log("Esperado planilha atualizada: 7.352,36");
console.log("Esperado demonstrativo: 7.297,55");
