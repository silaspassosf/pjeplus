// Teste com padrões corrigidos

const texto = `Demonstrativo de Honorários Nome: HONORÁRIOS DEVIDOS PELO RECLAMADO Valores Calculados C=(A x B) Valor (C) Alíquota (B) Descrição Credor Ocorrência Base (A) Composição de Base: (Bruto) x 5,00% 31/05/2025 145.951,09 5,00 % 7.297,55 HONORÁRIOS ADVOCATÍCIOS ADVOGADO DA RECLAMANTE 7.297,55 Total

VERBAS 145.951,09 145.951,09 Bruto Devido ao Reclamante
Documento assinado eletronicamente por GABRIELA CARR, em 26/06/2025, às 16:28:01 - 28142dc
Custas, pela Reclamada, no importe de R$ 1.000,00, calculadas sobre a condenação, ora arbitrada em R$ 50.000,00. 07 de março de 2025`;

console.log('=== PADRÕES CORRIGIDOS ===');

// Padrão de honorários correto
const honorariosCorreto = /(\d{1,3}(?:\.\d{3})*,\d{2})\s+HONOR[ÁA]RIOS?\s*ADVOCAT[ÍI]CIOS/i;
const matchHonorarios = texto.match(honorariosCorreto);
console.log('Honorários:', matchHonorarios ? matchHonorarios[1] : 'NÃO ENCONTRADO');

// Padrão de assinatura correto 
const assinaturaCorreta = /Documento\s+assinado\s+eletronicamente\s+por\s+([A-Z\s]+?),\s+em\s+[\d\/]+,\s+às\s+[\d:]+\s+-\s+([a-z0-9]+)/i;
const matchAssinatura = texto.match(assinaturaCorreta);
console.log('Assinatura:', matchAssinatura ? matchAssinatura[1] : 'NÃO ENCONTRADO');
console.log('ID:', matchAssinatura ? matchAssinatura[2] : 'NÃO ENCONTRADO');

// Teste alternativo para assinatura
const assinaturaAlternativa = /por\s+([A-Z\s]+),\s+em.*?-\s+([a-z0-9]+)/i;
const matchAlt = texto.match(assinaturaAlternativa);
console.log('Assinatura (alt):', matchAlt ? matchAlt[1] : 'NÃO ENCONTRADO');
console.log('ID (alt):', matchAlt ? matchAlt[2] : 'NÃO ENCONTRADO');

console.log('\n=== VALIDAÇÃO FINAL ===');
console.log('✅ Honorários: 7.297,55 =', matchHonorarios && matchHonorarios[1] === '7.297,55' ? 'CORRETO' : 'ERRO');
console.log('✅ Assinatura: GABRIELA CARR =', matchAlt && matchAlt[1] === 'GABRIELA CARR' ? 'CORRETO' : 'ERRO');
console.log('✅ ID: 28142dc =', matchAlt && matchAlt[2] === '28142dc' ? 'CORRETO' : 'ERRO');
