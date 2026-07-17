// ==UserScript==
// @name         PJe Aud1 – Pauta Extractor IIFE
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Extrai pauta (horário, partes, tipo) via API
// @author       Silas
// @match        https://pje.trt2.jus.br/aud/*
// @grant        GM_log
// ==/UserScript==

(async function() {
    'use strict';

    // ─────────────────────────────────────────────────────────────────────────
    // UTILITY: Extrair XSRF token do cookie
    // ─────────────────────────────────────────────────────────────────────────
    function getXsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === 'xsrf-token') return decodeURIComponent(value);
        }
        return null;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // UTILITY: Normalizar CNPJ
    // ─────────────────────────────────────────────────────────────────────────
    function normalizarCNPJ(str) {
        if (!str) return str;
        const nums = str.replace(/\D/g, '');
        if (nums.length === 14) {
            return nums.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        return str;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // UTILITY: Normalizar CPF
    // ─────────────────────────────────────────────────────────────────────────
    function normalizarCPF(str) {
        if (!str) return str;
        const nums = str.replace(/\D/g, '');
        if (nums.length === 11) {
            return nums.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        }
        return str;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // MAIN: Extrator de Pauta
    // ─────────────────────────────────────────────────────────────────────────
    async function extrairPauta() {
        const baseUrl = 'https://pje.trt2.jus.br/audapi/rest';
        const xsrfToken = getXsrfToken();

        console.log('%c🎯 Iniciando extração de pauta...', 'color: lime; font-weight: bold; font-size: 14px');
        console.log(`XSRF Token: ${xsrfToken ? '✓ Encontrado' : '✗ Não encontrado'}`);

        // ────────────────────────────────────────────────────────────────────
        // TENTATIVA 1: Chamar /audiencia com filtro de data
        // ────────────────────────────────────────────────────────────────────
        let audiencias = [];
        const dataInicio = '20/07/2026';
        const dataFim = '21/07/2026';
        
        try {
            console.log(`\n📡 Tentando endpoint: /audiencia?dataInicio=${dataInicio}&dataFim=${dataFim}`);
            
            const response = await fetch(
                `${baseUrl}/audiencia?dataInicio=${dataInicio}&dataFim=${dataFim}`,
                {
                    method: 'GET',
                    credentials: 'include',
                    headers: xsrfToken ? { 'xsrf-token': xsrfToken } : {}
                }
            );

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Resposta recebida:', data);
                
                if (Array.isArray(data)) {
                    audiencias = data;
                } else if (data.content && Array.isArray(data.content)) {
                    audiencias = data.content;
                } else if (data.resultado && Array.isArray(data.resultado)) {
                    audiencias = data.resultado;
                }
            } else {
                console.log(`❌ Erro ${response.status}: ${response.statusText}`);
            }
        } catch (err) {
            console.error('❌ Erro ao chamar endpoint:', err.message);
        }

        // ────────────────────────────────────────────────────────────────────
        // Processar resultados
        // ────────────────────────────────────────────────────────────────────
        if (audiencias.length === 0) {
            console.log('%c⚠️  Nenhuma audiência encontrada com este endpoint.', 'color: orange');
            console.log('Teste com outro endpoint ou parâmetros diferentes.');
            return;
        }

        console.log(`\n📊 ${audiencias.length} audiências carregadas!\n`);

        // ────────────────────────────────────────────────────────────────────
        // Extrair dados: horário, partes, tipo (ignorar julgamento)
        // ────────────────────────────────────────────────────────────────────
        const resultado = audiencias.map(aud => {
            // Extrair horário
            let horario = '';
            if (aud.hora || aud.horaAudiencia) {
                horario = aud.hora || aud.horaAudiencia;
            }

            // Extrair partes (ignorar julgamento)
            let partes = [];
            if (aud.partes && Array.isArray(aud.partes)) {
                partes = aud.partes
                    .filter(p => p.tipo !== 'JULGAMENTO' && p.tipo !== 'julgamento')
                    .map(p => ({
                        nome: p.nome || p.descricao || '',
                        documento: p.documento ? 
                            (p.documento.length === 14 ? normalizarCNPJ(p.documento) : normalizarCPF(p.documento))
                            : '',
                        tipo: p.tipo || ''
                    }));
            }

            // Extrair tipo (da audiência, não de julgamento)
            let tipo = aud.tipo || aud.tipoAudiencia || '';

            return {
                horario,
                partes,
                tipo,
                id: aud.id,
                data: aud.data || aud.dataAudiencia
            };
        });

        // ────────────────────────────────────────────────────────────────────
        // Exibir em console.table
        // ────────────────────────────────────────────────────────────────────
        console.log('%c📋 PAUTA EXTRAÍDA:', 'color: cyan; font-weight: bold; font-size: 12px');
        console.table(resultado);

        // ────────────────────────────────────────────────────────────────────
        // Exportar para clipboard
        // ────────────────────────────────────────────────────────────────────
        const json = JSON.stringify(resultado, null, 2);
        navigator.clipboard.writeText(json).then(() => {
            console.log('%c✅ JSON copiado para clipboard!', 'color: lime');
        }).catch(err => {
            console.log('%c⚠️  Erro ao copiar:', 'color: orange', err);
        });

        // Retornar dados também
        return resultado;
    }

    // ────────────────────────────────────────────────────────────────────────
    // Executar e expor globalmente
    // ────────────────────────────────────────────────────────────────────────
    window.extrairPauta = extrairPauta;
    console.log('%c💡 Execute no console: extrairPauta()', 'color: yellow; font-weight: bold');

})();
