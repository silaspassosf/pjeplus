// Script/alvara/dados_processo.js - dados do processo via pje-comum-api
// (mesma logica do hcalc-prep.js) + regras de preenchimento automatico.
(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});
    const logAviso = Alv.log.aviso;
    function obterProcessoId() {
        const match = window.location.pathname.match(
            /\/processo\/(\d+)\/detalhe(?:\/|$)/i
        );

        return match ? match[1] : '';
    }
    function _xsrfToken() {
        const cookie = document.cookie
            .split(';')
            .map(s => s.trim())
            .find(s => s.toLowerCase().startsWith('xsrf-token='));

        return cookie
            ? decodeURIComponent(cookie.split('=').slice(1).join('='))
            : '';
    }

    function _apiHeaders(accept) {
        const h = {
            'Accept': accept || 'application/json',
            'Content-Type': 'application/json',
            'X-Grau-Instancia': '1'
        };

        const x = _xsrfToken();
        if (x) h['X-XSRF-TOKEN'] = x;

        return h;
    }

    function _apiIdProcesso() {
        const m = window.location.pathname.match(/\/processo\/(\d+)/) ||
            window.location.search.match(/processo=(\d+)/i);

        return m ? m[1] : null;
    }

    function _apiBase() {
        return location.origin + '/pje-comum-api/api/processos/id/' + _apiIdProcesso();
    }

    async function _apiGet(url) {
        const resp = await fetch(url, {
            method: 'GET',
            credentials: 'include',
            headers: _apiHeaders()
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);

        const txt = await resp.text();

        try { return JSON.parse(txt); } catch (_) { return txt; }
    }

    function _shapePartes(dados) {
        const flatten = (partes, tipo) => (partes || []).map((p, idx) => ({
            nome: (p.nome || '').trim(),
            cpfcnpj: p.documento || '',
            tipo,
            ordem: `${idx + 1}ª`,
            representantes: (p.representantes || []).map(r => ({
                nome: (r.nome || '').trim(),
                oab: r.numeroOab || '',
                cpfcnpj: r.documento || r.cpfCnpj || '',
                tipo: r.tipo || ''
            }))
        }));

        return {
            ativo: flatten(dados.ATIVO, 'AUTOR'),
            passivo: flatten(dados.PASSIVO, 'REU'),
            outros: flatten(dados.TERCEIROS, 'TERCEIRO')
        };
    }

    let _dadosProcessoCache = null;

    async function buscarDadosProcesso() {
        // Sempre consulta a API (dados sempre corretos) e devolve
        // { processoId, numero, partes: { ativo, passivo, outros }, consultadoEm }.
        const id = _apiIdProcesso();

        if (!id) {
            logAviso('sem id de processo na URL; dados do processo indisponíveis.');
            return null;
        }

        let numero = null;
        let partes = { ativo: [], passivo: [], outros: [] };

        try {
            const meta = await _apiGet(_apiBase());
            numero = (meta && (meta.numeroProcesso || meta.numero)) || null;
        } catch (error) {
            logAviso('metadados do processo indisponíveis:', error.message);
        }

        try {
            const raw = await _apiGet(_apiBase() + '/partes');
            partes = _shapePartes(raw);
        } catch (error) {
            logAviso('partes do processo indisponíveis:', error.message);
        }

        let peritos = [];

        try {
            const rawPeritos = await _apiGet(_apiBase() + '/peritos');
            peritos = _shapePeritos(rawPeritos, partes);
        } catch (error) {
            logAviso('peritos do processo indisponíveis via endpoint; tentando partes:', error.message);
        }

        if (!peritos.length) {
            peritos = _shapePeritos(null, partes);
        }

        _dadosProcessoCache = {
            processoId: id,
            numero,
            partes,
            peritos,
            consultadoEm: new Date().toISOString()
        };

        return _dadosProcessoCache;
    }

    // Peritos: aceita array de strings, objetos {nome|pessoa.nome, documento}
    // ou fallback nos TERCEIROS marcados como perito na resposta de /partes.
    function _shapePeritos(raw, partes) {
        const nomes = [];

        if (Array.isArray(raw)) {
            for (const p of raw) {
                if (typeof p === 'string') {
                    nomes.push({ nome: p.trim(), cpfcnpj: '' });
                    continue;
                }

                const nome = (p && (p.nome || (p.pessoa && p.pessoa.nome)) || '').trim();
                const doc = (p && (p.documento || (p.pessoa && p.pessoa.documento)) || '').trim();

                if (nome) {
                    nomes.push({ nome, cpfcnpj: doc });
                }
            }
        }

        if (!nomes.length && partes) {
            for (const p of (partes.outros || [])) {
                const tipo = (p.tipo || '').toLowerCase();
                const nomeParte = (p.nome || '').toLowerCase();

                if (tipo.includes('perito') || nomeParte.includes('perito')) {
                    nomes.push({ nome: p.nome, cpfcnpj: p.cpfcnpj || '' });
                }
            }
        }

        return nomes;
    }

    function primeiraPerito(dados) {
        if (!dados || !Array.isArray(dados.peritos)) return null;

        return dados.peritos[0] || null;
    }

    function primeiraParte(dados, polo) {
        if (!dados) return null;

        const lista = polo === 'PASSIVO'
            ? dados.partes.passivo
            : dados.partes.ativo;

        return (lista && lista[0]) || null;
    }

    function primeiroAdvogado(dados, polo) {
        if (!dados) return null;

        const lista = polo === 'PASSIVO'
            ? dados.partes.passivo
            : dados.partes.ativo;

        for (const parte of (lista || [])) {
            const adv = (parte.representantes || [])[0];

            if (adv && adv.nome) {
                return { ...adv, parteNome: parte.nome };
            }
        }

        return null;
    }

    function preencherDestinatario(item, dados, polo, usarAdvogado) {
        const alvo = usarAdvogado
            ? primeiroAdvogado(dados, polo)
            : primeiraParte(dados, polo);

        if (alvo && alvo.nome) {
            item.destinatarioNome = alvo.nome;
            item.destinatarioDocumento = alvo.cpfcnpj || '';
        }

        return item;
    }

    // Regras de preenchimento automático por tipo de verba (detectada OU adicionada):
    //  - Crédito do exequente: beneficiário = polo ativo; se destino é conta do
    //    advogado/escritório → Nome e CPF do PRIMEIRO advogado do autor.
    //  - Devolução à reclamada: beneficiário = polo passivo; procurador da
    //    reclamada → primeiro advogado do passivo.
    //  - Honorários advocatícios: sempre o primeiro advogado do autor por padrão
    //    (da reclamada NUNCA é automático — só se adicionado manualmente).
    //  - Honorários periciais: se a decisão detectou a verba mas NÃO nomeou o
    //    perito, preenche com o primeiro perito dos dados da API. Se a decisão
    //    nomeou, o nome extraído prevalece. Verba não detectada nem entra no
    //    overlay (regra geral).
    function aplicarPreenchimentoAutomatico(item, dados) {
        if (!dados) return item;

        if (item.id === 'credito' || item.tipo === 'Crédito do exequente') {
            if ((item.destinoTipo || '').includes('reclamante')) {
                preencherDestinatario(item, dados, 'ATIVO', false);
            } else {
                preencherDestinatario(item, dados, 'ATIVO', true);
            }
        }

        if (item.id === 'devolucao-reclamada' || item.tipo === 'Devolução à reclamada') {
            if ((item.destinoTipo || '').includes('procurador')) {
                preencherDestinatario(item, dados, 'PASSIVO', true);
            } else {
                preencherDestinatario(item, dados, 'PASSIVO', false);
            }
        }

        if (item.id === 'honorarios-advocaticios' || item.tipo === 'Honorários advocatícios') {
            preencherDestinatario(item, dados, 'ATIVO', true);
        }

        if (item.id === 'honorarios-periciais' || item.tipo === 'Honorários periciais') {
            if (!item.perito) {
                const perito = primeiraPerito(dados);

                if (perito && perito.nome) {
                    item.perito = perito.nome;
                }
            }
        }

        return item;
    }

    Alv.dados = {
        buscarDadosProcesso: buscarDadosProcesso,
        aplicarPreenchimentoAutomatico: aplicarPreenchimentoAutomatico,
        obterProcessoId: obterProcessoId,
        primeiraParte: primeiraParte,
        primeiroAdvogado: primeiroAdvogado
    };
})();
