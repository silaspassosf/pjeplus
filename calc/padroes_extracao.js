// PADRÕES DE EXTRAÇÃO PARA CALC.JS
// Baseado na análise dos arquivos 1.js, 2.json e 3.json

// =============================================================================
// PADRÕES REGEX ASSERTIVOS PARA EXTRAÇÃO
// =============================================================================

const PADROES_EXTRACAO = {
    
    // 1. TOTAL (Valor Principal)
    TOTAL: {
        regex: /(?:total|bruto|devido|líquido).*?([0-9]{1,3}(?:\.[0-9]{3})*,\d{2})/gi,
        contexto: ['total', 'bruto', 'devido', 'líquido'],
        validacao: (valor) => parseFloat(valor.replace(/\./g, '').replace(',', '.')) > 0,
        exemplo: "24.059,25"
    },
    
    // 2. DATA DE LIQUIDAÇÃO
    DATA_LIQUIDACAO: {
        regex: /(?:liquidação|data.*liquidação).*?(\d{2}\/\d{2}\/\d{4})/gi,
        contexto: ['liquidação', 'data liquidação'],
        validacao: (data) => /^\d{2}\/\d{2}\/\d{4}$/.test(data),
        exemplo: "01/06/2025"
    },
    
    // 3. ID (Identificador)
    ID: {
        regex: [
            /([a-f0-9]{7})/gi,  // ID de assinatura
            /(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})/gi  // Número do processo
        ],
        contexto: ['processo', 'assinatura', 'documento'],
        validacao: (id) => id.length === 7 || /^\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}$/.test(id),
        exemplo: "02dea67"
    },
    
    // 4. CUSTAS
    CUSTAS: {
        regex: /(?:custas).*?([0-9]{1,3}(?:\.[0-9]{3})*,\d{2})/gi,
        contexto: ['custas', 'Custas'],
        validacao: (valor) => parseFloat(valor.replace(/\./g, '').replace(',', '.')) >= 0,
        exemplo: "440,00"
    },
    
    // 5. ROGERIO (Assinatura)
    ROGERIO: {
        regex: /ROGERIO\s+APARECIDO\s+ROSA/gi,
        contexto: ['assinado', 'assinatura', 'documento'],
        validacao: (texto) => texto.includes('ROGERIO APARECIDO ROSA'),
        exemplo: "ROGERIO APARECIDO ROSA"
    },
    
    // 6. INSS
    INSS: {
        regex: /(?:inss|INSS).*?([0-9]{1,3}(?:\.[0-9]{3})*,\d{2})/gi,
        contexto: ['inss', 'INSS', 'previdência'],
        validacao: (valor) => parseFloat(valor.replace(/\./g, '').replace(',', '.')) >= 0,
        exemplo: "1.193,36"
    },
    
    // 7. HONORÁRIOS
    HONORARIOS: {
        regex: /(?:honorários|honorarios).*?([0-9]{1,3}(?:\.[0-9]{3})*,\d{2})/gi,
        contexto: ['honorários', 'honorarios', 'advocatícios'],
        validacao: (valor) => parseFloat(valor.replace(/\./g, '').replace(',', '.')) > 0,
        exemplo: "1.202,96"
    }
};

// =============================================================================
// FUNÇÃO DE EXTRAÇÃO MELHORADA
// =============================================================================

function extrairDadosComPatroes(linhasEstruturadas) {
    const dados = {};
    const textoCompleto = linhasEstruturadas.flat().join(' ');
    
    // Log para debugging
    console.log('[CALC] Iniciando extração com padrões assertivos');
    console.log('[CALC] Texto completo tem', textoCompleto.length, 'caracteres');
    
    // Extrair cada campo usando os padrões
    Object.entries(PADROES_EXTRACAO).forEach(([campo, config]) => {
        try {
            const resultado = extrairCampo(textoCompleto, campo, config);
            dados[campo.toLowerCase()] = resultado;
            console.log(`[CALC] ${campo}: ${resultado || 'NÃO ENCONTRADO'}`);
        } catch (error) {
            console.error(`[CALC] Erro ao extrair ${campo}:`, error);
            dados[campo.toLowerCase()] = null;
        }
    });
    
    return dados;
}

function extrairCampo(texto, nomeCampo, config) {
    const { regex, contexto, validacao } = config;
    
    // Se regex é array, tenta cada um
    const regexArray = Array.isArray(regex) ? regex : [regex];
    
    for (const reg of regexArray) {
        const matches = [...texto.matchAll(reg)];
        
        for (const match of matches) {
            const valor = match[1] || match[0];
            
            // Valida o valor encontrado
            if (validacao && !validacao(valor)) {
                continue;
            }
            
            // Verifica se está no contexto correto
            if (contexto && contexto.length > 0) {
                const temContexto = contexto.some(ctx => 
                    texto.toLowerCase().includes(ctx.toLowerCase())
                );
                if (!temContexto) {
                    continue;
                }
            }
            
            return valor;
        }
    }
    
    return null;
}

// =============================================================================
// VALIDAÇÕES ESPECÍFICAS
// =============================================================================

function validarDadosExtraidos(dados) {
    const erros = [];
    
    // Validar total
    if (!dados.total || parseFloat(dados.total.replace(/\./g, '').replace(',', '.')) <= 0) {
        erros.push('Total inválido ou não encontrado');
    }
    
    // Validar data
    if (!dados.data_liquidacao || !/^\d{2}\/\d{2}\/\d{4}$/.test(dados.data_liquidacao)) {
        erros.push('Data de liquidação inválida');
    }
    
    // Validar ID
    if (!dados.id) {
        erros.push('ID não encontrado');
    }
    
    // Validar Rogerio
    if (!dados.rogerio) {
        erros.push('Assinatura de Rogerio não encontrada');
    }
    
    return erros;
}

// =============================================================================
// EXEMPLO DE USO
// =============================================================================

/*
const dadosExtraidos = extrairDadosComPatroes(linhasEstruturadas);
const erros = validarDadosExtraidos(dadosExtraidos);

if (erros.length > 0) {
    console.warn('[CALC] Erros na extração:', erros);
}

console.log('[CALC] Dados extraídos:', dadosExtraidos);
*/
