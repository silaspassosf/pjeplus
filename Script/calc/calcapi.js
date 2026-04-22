// ==UserScript==
// @name         CalcAPI — Mapeamento hcalc → API (Teste)
// @namespace    http://tampermonkey.net/
// @version      0.1.0
// @description  Sonda os endpoints REST do pje-comum-api para substituir as operações DOM do hcalc-prep.js. Expõe window.calcApi com métodos de teste individuais e orquestrado.
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    if (window.self !== window.top) return;
    if (window.__calcApiLoaded) return;
    window.__calcApiLoaded = true;

    // ══════════════════════════════════════════════════════════
    // HELPERS INTERNOS
    // ══════════════════════════════════════════════════════════

    function _xsrf() {
        const c = document.cookie.split(';').map(s => s.trim())
            .find(s => s.toLowerCase().startsWith('xsrf-token='));
        return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
    }

    function _headers(accept) {
        const h = {
            'Accept': accept || 'application/json',
            'Content-Type': 'application/json',
            'X-Grau-Instancia': '1',
        };
        const x = _xsrf();
        if (x) h['X-XSRF-TOKEN'] = x;
        return h;
    }

    function _idProcesso() {
        const m = window.location.pathname.match(/\/processo\/(\d+)/);
        return m ? m[1] : null;
    }

    function _base() {
        return location.origin + '/pje-comum-api/api/processos/id/' + _idProcesso();
    }

    // ISO "2024-11-17T..." → "17/11/24"
    function _normData(s) {
        if (!s) return '';
        const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
        return m ? `${m[3]}/${m[2]}/${m[1].slice(2)}` : s;
    }

    function _normalize(str) {
        return (str || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    }

    function _stripHtml(html) {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return (tmp.innerText || tmp.textContent || '').trim();
    }

    // Fetch JSON simples com XSRF
    async function _get(url) {
        const resp = await fetch(url, {
            method: 'GET',
            credentials: 'include',
            headers: _headers(),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);
        const txt = await resp.text();
        try { return JSON.parse(txt); } catch (_) { return txt; }
    }

    // Fetch raw (pode retornar PDF ou HTML)
    async function _getRaw(url) {
        const resp = await fetch(url, {
            method: 'GET',
            credentials: 'include',
            headers: _headers('*/*'),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);
        const ct = resp.headers.get('content-type') || '';
        if (ct.includes('application/pdf') || ct.includes('octet-stream')) {
            return { tipo: 'pdf-buffer', conteudo: await resp.arrayBuffer(), contentType: ct };
        }
        const text = await resp.text();
        // Alguns endpoints retornam PDF como texto começando com %PDF
        if (text.startsWith('%PDF')) {
            const enc = new TextEncoder();
            return { tipo: 'pdf-buffer', conteudo: enc.encode(text).buffer, contentType: ct };
        }
        if (ct.includes('application/json')) {
            try {
                const data = JSON.parse(text);
                const html = data.conteudo || data.conteudoHtml || data.html || data.conteudoBase64 || null;
                if (html) return { tipo: 'json-html', conteudo: html, raw: data, contentType: ct };
                return { tipo: 'json-raw', conteudo: text, raw: data, contentType: ct };
            } catch (_) { /* fall through */ }
        }
        return { tipo: 'html', conteudo: text, contentType: ct };
    }

    // ══════════════════════════════════════════════════════════
    // E1 — PARTES
    // ══════════════════════════════════════════════════════════

    function _shapePartes(dados) {
        const flatten = (partes, tipo) => (partes || []).map(p => ({
            nome: (p.nome || '').trim(),
            cpfcnpj: p.documento || '',
            tipo,
            telefone: (() => {
                const pf = p.pessoaFisica;
                if (!pf) return '';
                return [
                    pf.dddCelular && pf.numeroCelular ? `(${pf.dddCelular}) ${pf.numeroCelular}` : '',
                    pf.dddResidencial && pf.numeroResidencial ? `(${pf.dddResidencial}) ${pf.numeroResidencial}` : '',
                ].filter(Boolean).join(' | ');
            })(),
            representantes: (p.representantes || []).map(r => ({
                nome: (r.nome || '').trim(),
                oab: r.numeroOab || '',
                tipo: r.tipo || '',
            })),
        }));
        return {
            ativo: flatten(dados.ATIVO, 'AUTOR'),
            passivo: flatten(dados.PASSIVO, 'RÉU'),
            outros: flatten(dados.TERCEIROS, 'TERCEIRO'),
        };
    }

    async function _fetchPartes() {
        const raw = await _get(_base() + '/partes');
        return _shapePartes(raw);
    }

    // ══════════════════════════════════════════════════════════
    // E2 — TIMELINE
    // ══════════════════════════════════════════════════════════

    const TIMELINE_URL = () => _base() + '/timeline?' + new URLSearchParams({
        buscarMovimentos: 'false',
        buscarDocumentos: 'true',
        somenteDocumentosAssinados: 'false',
    });

    async function _fetchTimeline() {
        return _get(TIMELINE_URL());
    }

    // Classifica item da timeline sem tocar no DOM.
    // Retorna categoria: 'sentenca' | 'acordao' | 'RO' | 'RR' | 'edital' | 'hon_ajjt' | 'outro'
    function _classifyItem(item) {
        const low = _normalize(
            (item.titulo || '') + ' ' +
            (item.nomeDocumento || '') + ' ' +
            (item.descricao || '') + ' ' +
            (item.tipo || '')
        );

        let categoria = 'outro';
        if (/senten[cç]a/.test(low)) categoria = 'sentenca';
        else if (/acord[aã]o/.test(low) && !/intima/.test(low)) categoria = 'acordao';
        else if (/recurso de revista/.test(low)) categoria = 'RR';
        else if (/recurso ordin[aá]rio/.test(low)) categoria = 'RO';
        else if (/edital/.test(low)) categoria = 'edital';
        else if (/periciai.*aj.*jt|periciai.*aj|perito.*aj.*jt/.test(low)) categoria = 'hon_ajjt';

        return {
            categoria,
            uid: item.idUnicoDocumento || null,
            idDoc: item.id ? Number(item.id) : null,
            titulo: item.titulo || '',
            tipo: item.tipo || '',
            data: _normData(item.data || item.atualizadoEm || ''),
            // Polo do documento: campo 'polo' da API ou null se não existir
            polo: item.polo || item.tipoItemTimeline || null,
            nomeParte: item.nomeParte || item.nomeAutor || null,
            anexos: (item.anexos || []).map(a => ({
                uid: a.idUnicoDocumento || null,
                idDoc: a.id ? Number(a.id) : null,
                titulo: a.titulo || a.nomeDocumento || '',
                data: _normData(a.data || a.atualizadoEm || ''),
            })),
            // Campos brutos para descoberta — remover após validação
            _raw: item,
        };
    }

    // ══════════════════════════════════════════════════════════
    // E3 — METADADOS DE DOCUMENTO
    // ══════════════════════════════════════════════════════════

    async function _fetchDocMeta(idDoc) {
        return _get(_base() + '/documentos/id/' + idDoc);
    }

    // ══════════════════════════════════════════════════════════
    // E4/E5 — CONTEÚDO / HTML DE DOCUMENTO
    // ══════════════════════════════════════════════════════════

    // Tenta /conteudo primeiro, depois /html.
    // Retorna { tipo, texto, html?, chars, idDoc }
    async function _fetchDocConteudo(idDoc) {
        const endpoints = [
            _base() + '/documentos/id/' + idDoc + '/conteudo',
            _base() + '/documentos/id/' + idDoc + '/html',
        ];
        let lastErr = null;
        for (const url of endpoints) {
            try {
                const r = await _getRaw(url);
                if (r.tipo === 'pdf-buffer') {
                    return { tipo: 'pdf', texto: null, buffer: r.conteudo, idDoc };
                }
                const texto = (r.tipo === 'json-html' || r.tipo === 'html') ? _stripHtml(r.conteudo) : (r.conteudo || '');
                if (texto.length >= 10) {
                    return { tipo: r.tipo, texto, html: r.conteudo, chars: texto.length, idDoc };
                }
            } catch (e) {
                lastErr = e;
                console.warn('[calcApi] endpoint falhou:', url, e.message);
            }
        }
        throw lastErr || new Error('Nenhum endpoint retornou conteúdo para idDoc=' + idDoc);
    }

    // Extrai texto de PDF usando pdf.js nativo do PJe ou CDN
    async function _pdfToText(arrayBuffer) {
        let lib = window.pdfjsLib;
        // 1ª tentativa: pdf.js interno do PJe (mais confiável, sem CSP)
        if (!lib) {
            try {
                await new Promise((res, rej) => {
                    const s = document.createElement('script');
                    s.src = location.origin + '/pjekz/assets/pdf/build/pdf.js';
                    s.onload = res; s.onerror = rej;
                    document.head.appendChild(s);
                });
                lib = window.pdfjsLib;
            } catch (_) { /* prosseguir para CDN */ }
        }
        // 2ª tentativa: CDN (fallback)
        if (!lib) {
            await new Promise((res, rej) => {
                const s = document.createElement('script');
                s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js';
                s.onload = res; s.onerror = rej;
                document.head.appendChild(s);
            });
            lib = window.pdfjsLib;
        }
        if (!lib) throw new Error('pdf.js não disponível');
        try {
            lib.GlobalWorkerOptions.workerSrc = location.origin + '/pjekz/assets/pdf/build/pdf.worker.js';
        } catch (_) {
            lib.GlobalWorkerOptions.workerSrc =
                'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
        }
        const pdf = await lib.getDocument({ data: arrayBuffer }).promise;
        const pages = [];
        for (let p = 1; p <= pdf.numPages; p++) {
            const content = await (await pdf.getPage(p)).getTextContent();
            const lines = {};
            content.items.filter(it => it.str && it.str.trim()).forEach(it => {
                const y = Math.round(it.transform[5]);
                const k = Object.keys(lines).find(k => Math.abs(parseInt(k) - y) <= 4) || String(y);
                if (!lines[k]) lines[k] = [];
                lines[k].push({ str: it.str, x: Math.round(it.transform[4]) });
            });
            pages.push(
                Object.keys(lines).map(Number).sort((a, b) => b - a)
                    .map(y => lines[y].sort((a, b) => a.x - b.x).map(it => it.str.trim()).filter(Boolean).join(' '))
                    .join('\n')
            );
        }
        return pages.join('\n\n--- PÁGINA ---\n\n').trim();
    }

    // Retorna texto legível, resolvendo PDF se necessário
    async function _fetchDocHtml(idDoc) {
        const r = await _fetchDocConteudo(idDoc);
        if (r.tipo === 'pdf' && r.buffer) {
            const texto = await _pdfToText(r.buffer);
            return { tipo: 'pdf-extraido', texto, chars: texto.length, idDoc };
        }
        return r;
    }

    // ══════════════════════════════════════════════════════════
    // EXTRAÇÃO DE DADOS DA SENTENÇA (espelho de hcalc-prep.js)
    // ══════════════════════════════════════════════════════════

    function _extrairDadosSentenca(texto) {
        const result = {
            custas: null,
            hsusp: false,
            trteng: false,
            trtmed: false,
            responsabilidade: null,
            honorariosPericiais: [],
        };

        const custasMatch =
            texto.match(/no\s+importe\s+(?:m[ií]nim[oa]\s+|m[áa]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+),?\s*calculadas\s+sobre/i) ||
            texto.match(/[Cc]ustas[^,]*,\s*(?:pela\s+)?[Rr]eclamad[ao][^,]*,\s*no\s+importe\s+(?:m[ií]nim[oa]\s+|m[áa]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+)/i) ||
            texto.match(/[Cc]ustas[^,]*de\s+R\$\s*([\d.,]+)/i);
        if (custasMatch) result.custas = custasMatch[1].replace(/[.,]+$/, '');

        result.hsusp = /obriga[cç][aã]o\s+ficar[aá]\s+sob\s+condi[cç][aã]o\s+suspensiva/i.test(texto);
        result.trteng = /honor[aá]rios\s+periciais\s+t[eé]cnicos.*pagos\s+pelo\s+Tribunal/i.test(texto) ||
            /pagos\s+pelo\s+Tribunal\s+Regional.*periciais\s+t[eé]cnicos/i.test(texto);
        result.trtmed = /honor[aá]rios\s+periciais\s+m[eé]dicos.*pagos\s+pelo\s+Tribunal/i.test(texto) ||
            /pagos\s+pelo\s+Tribunal\s+Regional.*periciais\s+m[eé]dicos/i.test(texto);

        if (/condenar\s+(de\s+forma\s+)?subsidi[aá]ri/i.test(texto)) result.responsabilidade = 'subsidiaria';
        else if (/condenar\s+(de\s+forma\s+)?solid[aá]ri/i.test(texto)) result.responsabilidade = 'solidaria';

        const reHon = /honor[aá]rios\s+periciais[^.]*?R\$\s*([\d.,]+)[^.]*?\./gi;
        let m;
        while ((m = reHon.exec(texto)) !== null) {
            const trt = /pagos?\s+pelo\s+Tribunal/i.test(m[0]) || /TRT/i.test(m[0]);
            result.honorariosPericiais.push({ valor: m[1], trt });
        }

        return result;
    }

    // ══════════════════════════════════════════════════════════
    // EXTRAÇÃO DE PERITOS EM DOC AJ-JT
    // ══════════════════════════════════════════════════════════

    async function _lerPeritosAjJt(ajJtItems, peritosConhecimento) {
        const encontrados = [];
        const jaAchados = new Set();
        for (const item of ajJtItems) {
            if (jaAchados.size >= peritosConhecimento.length) break;
            if (!item.idDoc) continue;
            try {
                const r = await _fetchDocHtml(item.idDoc);
                if (!r.texto) continue;
                const textoNorm = _normalize(r.texto);
                for (const perito of peritosConhecimento) {
                    if (jaAchados.has(perito)) continue;
                    const pNorm = _normalize(perito);
                    const partes = pNorm.split(/\s+/).filter(Boolean);
                    const found = textoNorm.includes(pNorm) ||
                        (partes.length > 1 && textoNorm.includes(partes[0]) && textoNorm.includes(partes[partes.length - 1]));
                    if (found) {
                        encontrados.push({ nome: perito, trt: true, idAjJt: item.idDoc });
                        jaAchados.add(perito);
                    }
                }
            } catch (e) {
                console.warn('[calcApi] AJ-JT idDoc=' + item.idDoc + ' falhou:', e.message);
            }
        }
        return encontrados;
    }

    // ══════════════════════════════════════════════════════════
    // DETECÇÃO DE PARTES EM EDITAL
    // ══════════════════════════════════════════════════════════

    async function _lerPartesEdital(editais, passivo) {
        if (passivo.length === 1) return [passivo[0].nome];
        const intimadas = new Set();
        const reclamadas = passivo.map(p => ({ nome: p.nome, norm: _normalize(p.nome) }));
        for (const edital of editais) {
            if (intimadas.size >= passivo.length || !edital.idDoc) continue;
            try {
                const r = await _fetchDocHtml(edital.idDoc);
                if (!r.texto) continue;
                const textoNorm = _normalize(r.texto);
                for (const r2 of reclamadas) {
                    if (!intimadas.has(r2.nome) && textoNorm.includes(r2.norm)) {
                        intimadas.add(r2.nome);
                    }
                }
            } catch (e) {
                console.warn('[calcApi] Edital idDoc=' + edital.idDoc + ' falhou:', e.message);
            }
        }
        return Array.from(intimadas);
    }

    // ══════════════════════════════════════════════════════════
    // DETECÇÃO DE POLO PASSIVO SEM DOM
    // Cruza titulo do item com nomes do passivo (fallback quando API não retorna campo polo)
    // ══════════════════════════════════════════════════════════

    function _detectarPoloPassivo(item, passivo) {
        // 1. Campo nativo da API (confirmar se existe)
        if (item.polo) return item.polo;
        if (item.nomeParte) {
            const norm = _normalize(item.nomeParte);
            return passivo.some(p => _normalize(p.nome).includes(norm) || norm.includes(_normalize(p.nome)))
                ? 'PASSIVO' : 'ATIVO';
        }
        // 2. Cruzar titulo com nomes do passivo
        const tituloNorm = _normalize(item.titulo);
        const temReclamada = passivo.some(p => {
            const nomeNorm = _normalize(p.nome);
            const partes = nomeNorm.split(/\s+/).filter(Boolean);
            return partes.length >= 2 &&
                (tituloNorm.includes(nomeNorm) ||
                    (tituloNorm.includes(partes[0]) && tituloNorm.includes(partes[partes.length - 1])));
        });
        return temReclamada ? 'PASSIVO' : null; // null = não determinado
    }

    // ══════════════════════════════════════════════════════════
    // ORQUESTRADOR PRINCIPAL — espelho de executarPrep()
    // ══════════════════════════════════════════════════════════

    async function _prep() {
        const t0 = Date.now();
        const idProcesso = _idProcesso();
        if (!idProcesso) throw new Error('ID do processo não encontrado na URL');

        // ── E1: Partes ──────────────────────────────────────────
        console.log('[calcApi] Buscando partes...');
        const partes = await _fetchPartes();
        console.log('[calcApi] Partes:', partes.ativo.length, 'ativo(s),', partes.passivo.length, 'passivo(s)');

        // ── E2: Timeline classificada ───────────────────────────
        console.log('[calcApi] Buscando timeline...');
        const rawItems = await _fetchTimeline();
        const items = rawItems.map(_classifyItem);
        console.log('[calcApi] Timeline:', rawItems.length, 'itens classificados:', {
            sentencas: items.filter(i => i.categoria === 'sentenca').length,
            acordaos: items.filter(i => i.categoria === 'acordao').length,
            RO: items.filter(i => i.categoria === 'RO').length,
            RR: items.filter(i => i.categoria === 'RR').length,
            editais: items.filter(i => i.categoria === 'edital').length,
            honAjJt: items.filter(i => i.categoria === 'hon_ajjt').length,
        });

        // ── Sentença ────────────────────────────────────────────
        const sentencas = items.filter(i => i.categoria === 'sentenca');
        // Manter mesma lógica que hcalc-prep: mais antiga = índice maior (timeline é desc)
        // Na timeline API a ordem é cronológica DESC (mais recente primeiro)
        const sentencaAlvo = sentencas.length > 0 ? sentencas[sentencas.length - 1] : null;
        let sentencaDados = { custas: null, hsusp: false, trteng: false, trtmed: false, responsabilidade: null, honorariosPericiais: [] };
        let sentencaTextoBruto = null;
        if (sentencaAlvo?.idDoc) {
            console.log('[calcApi] Lendo sentença idDoc=' + sentencaAlvo.idDoc + '...');
            try {
                // Preferir pjeExtrairApi (extrair.js) se disponível — extração mais robusta
                if (typeof window.pjeExtrairApi === 'function' && sentencaAlvo.uid) {
                    console.log('[calcApi] Usando pjeExtrairApi uid=' + sentencaAlvo.uid);
                    const ext = await window.pjeExtrairApi(sentencaAlvo.uid, { idProcesso });
                    if (ext.sucesso && ext.conteudo_bruto) {
                        sentencaTextoBruto = ext.conteudo_bruto;
                        console.log('[calcApi] pjeExtrairApi ok:', ext.tipo, ext.chars, 'chars');
                    } else {
                        console.warn('[calcApi] pjeExtrairApi falhou:', ext.erro || 'sem conteúdo');
                    }
                }
                // Fallback: _fetchDocHtml próprio
                if (!sentencaTextoBruto) {
                    const r = await _fetchDocHtml(sentencaAlvo.idDoc);
                    sentencaTextoBruto = r.texto || null;
                }
                if (sentencaTextoBruto) {
                    sentencaDados = _extrairDadosSentenca(sentencaTextoBruto);
                    console.log('[calcApi] Sentença extraída:', sentencaDados);
                    console.log('[calcApi] Sentença preview:\n' + sentencaTextoBruto.slice(0, 600));
                } else {
                    console.warn('[calcApi] Sentença: conteúdo vazio');
                }
            } catch (e) {
                console.error('[calcApi] Sentença falhou:', e.message);
            }
        } else {
            console.warn('[calcApi] Nenhuma sentença encontrada na timeline');
        }

        // ── Depósitos / Recursos ────────────────────────────────
        // Recursos do polo passivo com anexos (depositante = reclamada)
        const todosRecursos = items.filter(i => i.categoria === 'RO' || i.categoria === 'RR');
        const acordaos = items.filter(i => i.categoria === 'acordao');
        const oldestAcordaoIdx = acordaos.length > 0 ? Math.max(...acordaos.map((_, idx) => idx)) : -1;

        const depositos = todosRecursos.map((rec, idx) => {
            const poloDetectado = _detectarPoloPassivo(rec._raw, partes.passivo);
            // Se acórdão existe: recursos com idx < oldestAcordaoIdx são posteriores ao acórdão (basta ter polo)
            // Se não: exige polo detectado como PASSIVO
            const ocorreuDepoisDoAcordao = oldestAcordaoIdx !== -1 && idx < oldestAcordaoIdx;
            const incluir = ocorreuDepoisDoAcordao || poloDetectado === 'PASSIVO';
            if (!incluir) return null;

            return {
                tipo: rec.categoria,
                data: rec.data,
                idDoc: rec.idDoc,
                uid: rec.uid,
                titulo: rec.titulo,
                depositante: rec.nomeParte || partes.passivo.map(p => p.nome).find(n =>
                    _normalize(rec.titulo).includes(_normalize(n))
                ) || '',
                polo: poloDetectado,
                anexos: rec.anexos,
            };
        }).filter(Boolean);

        // Ordenar por data (mais antigas primeiro)
        depositos.sort((a, b) => {
            const ts = s => {
                if (!s) return 0;
                const p = s.split('/');
                if (p.length < 3) return 0;
                return new Date(2000 + parseInt(p[2]), parseInt(p[1]) - 1, parseInt(p[0])).getTime();
            };
            return ts(a.data) - ts(b.data);
        });

        // ── Honorários AJ-JT (identificar peritos) ──────────────
        const honAjJt = items.filter(i => i.categoria === 'hon_ajjt');
        let peritos = [];
        // Nota: _lerPeritosAjJt requer lista de peritos conhecidos (não disponível sem heurística)
        // Para o teste, retornamos os itens brutos; integração plena requer partes ou heurística
        console.log('[calcApi] AJ-JT encontrados:', honAjJt.length);

        // ── Editais ─────────────────────────────────────────────
        const editais = items.filter(i => i.categoria === 'edital');
        let partesIntimadasEdital = [];
        if (editais.length > 0 && partes.passivo.length > 0) {
            console.log('[calcApi] Lendo editais...');
            partesIntimadasEdital = await _lerPartesEdital(editais, partes.passivo);
            console.log('[calcApi] Partes intimadas por edital:', partesIntimadasEdital);
        }

        const durMs = Date.now() - t0;
        console.log(`[calcApi] prep() concluído em ${durMs}ms`);

        return {
            idProcesso,
            partes,
            sentenca: {
                ...sentencaAlvo ? {
                    data: sentencaAlvo.data,
                    idDoc: sentencaAlvo.idDoc,
                    uid: sentencaAlvo.uid,
                    titulo: sentencaAlvo.titulo,
                } : {},
                ...sentencaDados,
                _textoBruto: sentencaTextoBruto,
            },
            acordaos: acordaos.map(a => ({ data: a.data, idDoc: a.idDoc, uid: a.uid, titulo: a.titulo })),
            depositos,
            honAjJt: honAjJt.map(h => ({ data: h.data, idDoc: h.idDoc, uid: h.uid, titulo: h.titulo })),
            editais: editais.map(e => ({ data: e.data, idDoc: e.idDoc, uid: e.uid, titulo: e.titulo })),
            partesIntimadasEdital,
            peritos,
            _meta: {
                durMs,
                versao: '0.1',
                endpointsUsados: ['E1:partes', 'E2:timeline',
                    sentencaAlvo ? 'E4/E5:sentenca' : null,
                    editais.length ? 'E4/E5:edital' : null,
                ].filter(Boolean),
            },
        };
    }

    // ══════════════════════════════════════════════════════════
    // UI — PAINEL FLUTUANTE DE RESULTADOS
    // ══════════════════════════════════════════════════════════

    function _renderUI(result) {
        const old = document.getElementById('calc-api-panel');
        if (old) old.remove();

        const panel = document.createElement('div');
        panel.id = 'calc-api-panel';
        panel.style.cssText = [
            'position:fixed', 'top:60px', 'right:12px', 'z-index:999999',
            'width:340px', 'max-height:80vh', 'overflow-y:auto',
            'background:#1e1e2e', 'color:#cdd6f4', 'font-family:monospace',
            'font-size:12px', 'border-radius:8px', 'box-shadow:0 4px 20px rgba(0,0,0,.6)',
            'padding:12px', 'line-height:1.5',
        ].join(';');

        const btn = document.createElement('button');
        btn.textContent = '✕';
        btn.style.cssText = 'float:right;background:none;border:none;color:#cdd6f4;cursor:pointer;font-size:14px;';
        btn.onclick = () => panel.remove();
        panel.appendChild(btn);

        function row(label, val, color) {
            color = color || '#a6e3a1';
            const d = document.createElement('div');
            d.style.marginBottom = '4px';
            d.innerHTML = `<span style="color:#89b4fa">${label}:</span> <span style="color:${color}">${val}</span>`;
            panel.appendChild(d);
        }

        function section(title) {
            const d = document.createElement('div');
            d.style.cssText = 'margin-top:10px;margin-bottom:4px;font-weight:bold;color:#cba6f7;border-bottom:1px solid #313244;';
            d.textContent = title;
            panel.appendChild(d);
        }

        function badge(ok) { return ok ? '✅' : '❌'; }

        section('CalcAPI v0.1 — ' + result.idProcesso);
        row('Duração', result._meta.durMs + 'ms');
        row('Endpoints', result._meta.endpointsUsados.join(', '), '#f9e2af');

        section('Partes');
        row('Ativo', result.partes.ativo.map(p => p.nome).join(', ') || '—');
        row('Passivo', result.partes.passivo.map(p => p.nome).join(', ') || '—');

        section('Sentença');
        row('Data', result.sentenca.data || '—');
        row('idDoc', result.sentenca.idDoc || '—');
        row('Custas', result.sentenca.custas || 'não detectado');
        row('Responsabilidade', result.sentenca.responsabilidade || 'única/não detectado');
        row('H. Suspensiva', badge(result.sentenca.hsusp));
        row('Perícia TRT Eng', badge(result.sentenca.trteng));
        row('Perícia TRT Med', badge(result.sentenca.trtmed));
        if (result.sentenca.honorariosPericiais?.length) {
            row('Hon. Periciais', result.sentenca.honorariosPericiais.map(h => `R$${h.valor}${h.trt ? '(TRT)' : ''}`).join(' | '));
        }
        // Preview do texto extraído (debug — 400 chars)
        if (result.sentenca._textoBruto) {
            const preview = result.sentenca._textoBruto.slice(0, 400).replace(/</g, '&lt;').replace(/\n/g, '↵ ');
            const d = document.createElement('div');
            d.style.cssText = 'margin-top:6px;font-size:10px;color:#a6adc8;white-space:pre-wrap;word-break:break-word;cursor:pointer;';
            d.title = 'Click para copiar texto completo';
            d.textContent = '[preview] ' + preview + (result.sentenca._textoBruto.length > 400 ? '…' : '');
            d.onclick = () => navigator.clipboard.writeText(result.sentenca._textoBruto).then(() => alert('Texto copiado (' + result.sentenca._textoBruto.length + ' chars)'));
            panel.appendChild(d);
        } else {
            const d = document.createElement('div');
            d.style.cssText = 'margin-top:6px;font-size:10px;color:#f38ba8;';
            d.textContent = '[!] Texto da sentença não extraído';
            panel.appendChild(d);
        }

        section('Acórdãos (' + result.acordaos.length + ')');
        result.acordaos.forEach((a, i) => row(`  [${i}]`, `${a.data} — ${a.titulo.slice(0, 30)}`));

        section('Depósitos Recursais (' + result.depositos.length + ')');
        result.depositos.forEach((d, i) => row(`  [${i}] ${d.tipo}`, `${d.data} ${d.depositante ? '— ' + d.depositante.slice(0, 20) : ''} (${d.anexos.length} anexo(s))`));

        section('Editais (' + result.editais.length + ')');
        if (result.partesIntimadasEdital.length) row('Intimadas', result.partesIntimadasEdital.join(', '));

        section('AJ-JT (' + result.honAjJt.length + ')');
        result.honAjJt.forEach((h, i) => row(`  [${i}]`, h.titulo.slice(0, 40)));

        document.body.appendChild(panel);
    }

    // ══════════════════════════════════════════════════════════
    // API PÚBLICA — window.calcApi
    // ══════════════════════════════════════════════════════════

    window.calcApi = {
        // E1
        partes: async () => {
            const r = await _fetchPartes();
            console.log('[calcApi] partes:', r);
            return r;
        },

        // E2 bruto
        timeline: async () => {
            const r = await _fetchTimeline();
            console.log('[calcApi] timeline raw (', r.length, 'itens):', r);
            console.table(r.slice(0, 10).map(i => ({
                id: i.id,
                uid: i.idUnicoDocumento,
                titulo: i.titulo,
                tipo: i.tipo,
                polo: i.polo,
                nomeParte: i.nomeParte,
                nomeAutor: i.nomeAutor,
                data: i.data,
                anexos: (i.anexos || []).length,
                // Expõe todos os campos desconhecidos para descoberta
                _keys: Object.keys(i).join(', '),
            })));
            return r;
        },

        // E2 classificado
        timelineClass: async () => {
            const raw = await _fetchTimeline();
            const items = raw.map(_classifyItem);
            console.log('[calcApi] timeline classificada:', items);
            console.table(items.map(i => ({ categoria: i.categoria, titulo: i.titulo, idDoc: i.idDoc, uid: i.uid, data: i.data, polo: i.polo, anexos: i.anexos.length })));
            return items;
        },

        // E3
        docMeta: async (idDoc) => {
            const r = await _fetchDocMeta(idDoc);
            console.log('[calcApi] docMeta idDoc=' + idDoc + ':', r);
            return r;
        },

        // E4/E5 — retorna objeto com tipo e texto/buffer
        docConteudo: async (idDoc) => {
            const r = await _fetchDocConteudo(idDoc);
            console.log('[calcApi] docConteudo idDoc=' + idDoc + ':', r.tipo, r.chars || '(binary)');
            return r;
        },

        // E4/E5 + pdf fallback — retorna texto legível
        docHtml: async (idDoc) => {
            const r = await _fetchDocHtml(idDoc);
            console.log('[calcApi] docHtml idDoc=' + idDoc + ':', r.tipo, r.chars, 'chars');
            if (r.texto) console.log('[calcApi] Preview:\n' + r.texto.slice(0, 500));
            return r;
        },

        // Extração de dados da sentença a partir de um idDoc
        lerSentenca: async (idDoc) => {
            if (!idDoc) {
                // Detectar automaticamente pela timeline
                const raw = await _fetchTimeline();
                const sentencas = raw.map(_classifyItem).filter(i => i.categoria === 'sentenca');
                if (!sentencas.length) { console.warn('[calcApi] Nenhuma sentença encontrada'); return null; }
                idDoc = sentencas[sentencas.length - 1].idDoc;
                console.log('[calcApi] Sentença detectada idDoc=' + idDoc);
            }
            const r = await _fetchDocHtml(idDoc);
            if (!r.texto) { console.warn('[calcApi] Conteúdo vazio'); return null; }
            const dados = _extrairDadosSentenca(r.texto);
            console.log('[calcApi] lerSentenca:', dados);
            return dados;
        },

        // Partes intimadas em primeiro edital encontrado
        lerEdital: async () => {
            const partes = await _fetchPartes();
            const raw = await _fetchTimeline();
            const editais = raw.map(_classifyItem).filter(i => i.categoria === 'edital');
            if (!editais.length) { console.warn('[calcApi] Nenhum edital'); return []; }
            const r = await _lerPartesEdital(editais, partes.passivo);
            console.log('[calcApi] lerEdital:', r);
            return r;
        },

        // Depósitos recursais classificados
        depositos: async () => {
            const partes = await _fetchPartes();
            const raw = await _fetchTimeline();
            const items = raw.map(_classifyItem);
            const deps = items.filter(i => i.categoria === 'RO' || i.categoria === 'RR')
                .map(rec => ({
                    tipo: rec.categoria,
                    data: rec.data,
                    idDoc: rec.idDoc,
                    uid: rec.uid,
                    titulo: rec.titulo,
                    polo: _detectarPoloPassivo(rec._raw, partes.passivo),
                    anexos: rec.anexos,
                }));
            console.log('[calcApi] depositos:', deps);
            console.table(deps.map(d => ({ tipo: d.tipo, data: d.data, polo: d.polo, idDoc: d.idDoc, anexos: d.anexos.length })));
            return deps;
        },

        // Orquestrador completo — espelho de executarPrep()
        prep: async () => {
            const r = await _prep();
            _renderUI(r);
            return r;
        },

        // Só UI (re-renderiza com último resultado de prep)
        ui: () => {
            const last = window.__calcApiLastPrep;
            if (!last) { console.warn('[calcApi] Execute calcApi.prep() primeiro'); return; }
            _renderUI(last);
        },

        // Ajuda
        help: () => {
            console.log(`
╔══════════════════════════════════════════╗
║  calcApi — Comandos disponíveis          ║
╚══════════════════════════════════════════╝
  await calcApi.partes()          → E1: partes do processo
  await calcApi.timeline()        → E2: itens brutos (console.table)
  await calcApi.timelineClass()   → E2: itens classificados
  await calcApi.docMeta(idDoc)    → E3: metadados do documento
  await calcApi.docConteudo(id)   → E4/E5: conteúdo raw
  await calcApi.docHtml(id)       → E4/E5 + fallback pdf: texto legível
  await calcApi.lerSentenca(id?)  → Extrai dados da sentença (idDoc opcional)
  await calcApi.lerEdital()       → Partes intimadas por edital
  await calcApi.depositos()       → Recursos recursais classificados
  await calcApi.prep()            → Orquestrador completo (+ painel visual)
  calcApi.help()                  → Exibe esta ajuda

  Ver calcapi.md para o plano de testes e mapeamento completo.
            `);
        },
    };

    // Interceptar resultado de prep para ui()
    const _origPrep = window.calcApi.prep.bind(window.calcApi);
    window.calcApi.prep = async () => {
        const r = await _origPrep();
        window.__calcApiLastPrep = r;
        return r;
    };

    // ── Botão de atalho na página ───────────────────────────────
    function _addButton() {
        if (document.getElementById('calc-api-btn')) return;
        const btn = document.createElement('button');
        btn.id = 'calc-api-btn';
        btn.textContent = 'CalcAPI';
        btn.title = 'Executar calcApi.prep() — teste de migração hcalc → API';
        btn.style.cssText = [
            'position:fixed', 'bottom:14px', 'right:14px', 'z-index:999998',
            'padding:6px 12px', 'background:#7c3aed', 'color:#fff',
            'border:none', 'border-radius:6px', 'cursor:pointer',
            'font-size:12px', 'font-family:monospace', 'opacity:.9',
        ].join(';');
        btn.onclick = () => { btn.disabled = true; btn.textContent = '...'; window.calcApi.prep().finally(() => { btn.disabled = false; btn.textContent = 'CalcAPI'; }); };
        document.body.appendChild(btn);
    }

    // Aguardar DOM mínimo
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        _addButton();
    } else {
        document.addEventListener('DOMContentLoaded', _addButton);
    }

    console.log('[calcApi] v0.1 carregado. Use window.calcApi.help() para ver os comandos disponíveis.');
    console.log('[calcApi] Processo:', _idProcesso() || '(URL sem idProcesso)');

})();
