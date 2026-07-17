(async function() {
    const baseUrl = 'https://pje.trt2.jus.br/audapi/rest';
    
    // Extrair XSRF token de document.cookie (conforme api/apis.md seção 0)
    const xsrfCookie = document.cookie.split(';')
        .map(c => c.trim())
        .find(c => c.toLowerCase().startsWith('xsrf-token='));
    const xsrfToken = xsrfCookie ? xsrfCookie.split('=').slice(1).join('=') : '';

    // Normalizar CNPJ/CPF
    const norm = (str) => {
        if (!str) return str;
        const nums = str.replace(/\D/g, '');
        if (nums.length === 14) return nums.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        if (nums.length === 11) return nums.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        return str;
    };

    try {
        console.log('%c🔄 Carregando 15 audiências...', 'color: lime; font-weight: bold');
        
        const idsAudiencias = [
            12174224, 12273392, 12350305, 12203321, 12351168, 12276741, 12504763, 
            12278192, 12268971, 12208416, 12205664, 12206010, 12509755, 12406275, 12431351
        ];

        // Chamar /audapi/rest/audiencia/{id} com X-XSRF-TOKEN
        const promessas = idsAudiencias.map(id =>
            fetch(`${baseUrl}/audiencia/${id}`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'X-XSRF-TOKEN': xsrfToken,
                    'Accept': 'application/json'
                }
            })
            .then(r => r.status === 200 ? r.json() : null)
            .catch(e => { console.warn(`⚠️ ID ${id}:`, e.message); return null; })
        );

        const audiencias = (await Promise.all(promessas)).filter(a => a !== null);

        // Extrair: horário, partes, tipo (ignorar julgamento)
        const resultado = audiencias.map(aud => ({
            horario: aud.hora || aud.horaAudiencia || '',
            partes: (aud.partes || [])
                .filter(p => p.tipo?.toUpperCase() !== 'JULGAMENTO')
                .map(p => ({ nome: p.nome || '', documento: norm(p.documento || '') })),
            tipo: aud.tipo || aud.tipoAudiencia || ''
        }));

        console.log(`%c✅ ${resultado.length} audiências\n`, 'color: cyan; font-weight: bold');
        console.table(resultado);

        await navigator.clipboard.writeText(JSON.stringify(resultado, null, 2));
        console.log('%c✅ Copiado para clipboard', 'color: lime');

        return resultado;
    } catch (err) {
        console.error('❌ Erro:', err.message);
    }
})();
