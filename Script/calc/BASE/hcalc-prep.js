(function () {
    'use strict';
    const HCALC_DEBUG = false;
    const dbg = (...args) => { if (HCALC_DEBUG) console.log('[hcalc]', ...args); };
    const warn = (...args) => console.warn('[hcalc]', ...args);
    const err = (...args) => console.error('[hcalc]', ...args);

    // prep.js - Preparação pré-overlay para hcalc.js (API-only)
    // Sem DOM polling, sem clicks, sem sleep no fluxo principal.
    // Uso: const result = await window.executarPrep(partesData, peritosConhecimento);

    // ==========================================
    // UTILIDADES GERAIS
    // ==========================================

    function normalizeText(str) {
        return (str || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    }

    // ==========================================
    // API HELPERS
    // ==========================================

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
        const m = window.location.pathname.match(/\/processo\/(\d+)/) ||
            window.location.search.match(/processo=(\d+)/i);
        return m ? m[1] : null;
    }

    function _base() {
        return location.origin + '/pje-comum-api/api/processos/id/' + _idProcesso();
    }

    // ISO "2024-11-17T..." -> "17/11/2024" (4 digitos de ano - obrigatorio para overlay)
    function _normData(s) {
        if (!s || typeof s !== 'string') return s;
        const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
        return m ? `${m[3]}/${m[2]}/${m[1]}` : s;
    }

    // Monta href sintetico usado pelo overlay para localizar itens na timeline
    function _montarHref(uid) {
        if (!uid) return null;
        try {
            return `${location.origin}/pjekz/processo/${_idProcesso() || ''}/detalhe?documentoId=${uid}`;
        } catch (e) { return null; }
    }

    function _normalize(str) {
        return (str || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    }

    function _compactNormalize(str) {
        return _normalize((str || '').replace(/\s+/g, ' '));
    }

    function _windowAround(text, idx, before, after) {
        const b = before === undefined ? 120 : before;
        const a = after === undefined ? 120 : after;
        const start = Math.max(0, idx - b);
        const end = Math.min(text.length, idx + a);
        return text.slice(start, end);
    }

    function _cooccursInWindow(textNorm, termsA, termsB, windowSize) {
        const ws = windowSize === undefined ? 120 : windowSize;
        if (!textNorm) return false;
        for (const a of termsA) {
            const aNorm = _normalize(a);
            let idx = textNorm.indexOf(aNorm);
            while (idx !== -1) {
                const win = _windowAround(textNorm, idx, ws, ws);
                for (const b of termsB) {
                    if (win.includes(_normalize(b))) return true;
                }
                idx = textNorm.indexOf(aNorm, idx + aNorm.length);
            }
        }
        return false;
    }

    function _stripHtml(html) {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return (tmp.innerText || tmp.textContent || '').trim();
    }

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

    // ==========================================
    // E1 - PARTES
    // ==========================================

    function _shapePartes(dados) {
        const flatten = (partes, tipo) => (partes || []).map((p, idx) => ({
            nome: (p.nome || '').trim(),
            cpfcnpj: p.documento || '',
            tipo,
            ordem: `${idx + 1}a`,
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
            passivo: flatten(dados.PASSIVO, 'REU'),
            outros: flatten(dados.TERCEIROS, 'TERCEIRO'),
        };
    }

    async function _fetchPartes() {
        const raw = await _get(_base() + '/partes');
        return _shapePartes(raw);
    }

    // ==========================================
    // E2 - TIMELINE
    // ==========================================

    function _TIMELINE_URL() {
        return _base() + '/timeline?' + new URLSearchParams({
            buscarMovimentos: 'false',
            buscarDocumentos: 'true',
            somenteDocumentosAssinados: 'false',
        });
    }

    async function _fetchTimeline() {
        return _get(_TIMELINE_URL());
    }

    // Classifica item da timeline sem tocar no DOM.
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
        else if (/despacho/.test(low) || (/decis[aã]o/.test(low) && /despacho/.test(low))) categoria = 'despacho';
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
            polo: item.polo || item.tipoItemTimeline || null,
            nomeParte: item.nomeParte || item.nomeAutor || null,
            anexos: (item.anexos || []).map(function(a) {
                return {
                    uid: a.idUnicoDocumento || null,
                    idDoc: a.id ? Number(a.id) : null,
                    titulo: a.titulo || a.nomeDocumento || '',
                    data: _normData(a.data || a.atualizadoEm || ''),
                };
            }),
            _raw: item,
        };
    }

    // ==========================================
    // E3-E5 - CONTEUDO DE DOCUMENTO
    // ==========================================

    async function _fetchDocMeta(idDoc) {
        return _get(_base() + '/documentos/id/' + idDoc);
    }

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
                warn('[prep] endpoint falhou:', url, e.message);
            }
        }
        throw lastErr || new Error('Nenhum endpoint retornou conteudo para idDoc=' + idDoc);
    }

    async function _pdfToText(arrayBuffer) {
        let lib = window.pdfjsLib;
        if (!lib) {
            try {
                await new Promise(function(res, rej) {
                    const s = document.createElement('script');
                    s.src = location.origin + '/pjekz/assets/pdf/build/pdf.js';
                    s.onload = res; s.onerror = rej;
                    document.head.appendChild(s);
                });
                lib = window.pdfjsLib;
            } catch (_) { /* prosseguir para CDN */ }
        }
        if (!lib) {
            await new Promise(function(res, rej) {
                const s = document.createElement('script');
                s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js';
                s.onload = res; s.onerror = rej;
                document.head.appendChild(s);
            });
            lib = window.pdfjsLib;
        }
        if (!lib) throw new Error('pdf.js nao disponivel');
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
            const linesMap = {};
            content.items.filter(function(it) { return it.str && it.str.trim(); }).forEach(function(it) {
                const y = Math.round(it.transform[5]);
                const k = Object.keys(linesMap).find(function(k) { return Math.abs(parseInt(k) - y) <= 4; }) || String(y);
                if (!linesMap[k]) linesMap[k] = [];
                linesMap[k].push({ str: it.str, x: Math.round(it.transform[4]) });
            });
            pages.push(
                Object.keys(linesMap).map(Number).sort(function(a, b) { return b - a; })
                    .map(function(y) { return linesMap[y].sort(function(a, b) { return a.x - b.x; }).map(function(it) { return it.str.trim(); }).filter(Boolean).join(' '); })
                    .join('\n')
            );
        }
        return pages.join('\n\n--- PAGINA ---\n\n').trim();
    }

    async function _fetchDocHtml(idDoc) {
        const r = await _fetchDocConteudo(idDoc);
        if (r.tipo === 'pdf' && r.buffer) {
            const texto = await _pdfToText(r.buffer);
            return { tipo: 'pdf-extraido', texto, chars: texto.length, idDoc };
        }
        return r;
    }

    // ==========================================
    // EXTRACAO DE DADOS DA SENTENCA
    // ==========================================

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
            texto.match(/no\s+importe\s+(?:m[ii]nim[oa]\s+|m[aa]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+),?\s*calculadas\s+sobre/i) ||
            texto.match(/[Cc]ustas[^,]*,\s*(?:pela\s+)?[Rr]eclamad[ao][^,]*,\s*no\s+importe\s+(?:m[ii]nim[oa]\s+|m[aa]xim[oa]\s+|total\s+)?de\s+R\$\s*([\d.,]+)/i) ||
            texto.match(/[Cc]ustas[^,]*de\s+R\$\s*([\d.,]+)/i);
        if (custasMatch) result.custas = custasMatch[1].replace(/[.,]+$/, '');

        result.hsusp = /obriga[cç][aã]o\s+ficar[aá]\s+sob\s+condi[cç][aã]o\s+suspensiva/i.test(texto);
        result.trteng =
            /honor[aá]rios\s+periciais\s+t[eé]cnicos.*pagos\s+pelo\s+Tribunal/i.test(texto) ||
            /pagos\s+pelo\s+Tribunal\s+Regional.*periciais\s+t[eé]cnicos/i.test(texto);
        result.trtmed =
            /honor[aá]rios\s+periciais\s+m[eé]dicos.*pagos\s+pelo\s+Tribunal/i.test(texto) ||
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

    // ==========================================
    // EXTRACAO DE PERITOS EM DOC AJ-JT
    // ==========================================

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
                warn('[prep] AJ-JT idDoc=' + item.idDoc + ' falhou:', e.message);
            }
        }
        return encontrados;
    }

    // ==========================================
    // DETECCAO DE PARTES EM EDITAL
    // ==========================================

    async function _lerPartesEdital(editais, passivo) {
        if (passivo.length === 1) return [passivo[0].nome];
        const intimadas = new Set();
        const reclamadas = passivo.map(function(p) { return { nome: p.nome, norm: _normalize(p.nome) }; });
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
                warn('[prep] Edital idDoc=' + edital.idDoc + ' falhou:', e.message);
            }
        }
        return Array.from(intimadas);
    }

    // ==========================================
    // DETECCAO DE POLO PASSIVO SEM DOM
    // ==========================================

    function _detectarPoloPassivo(itemRaw, passivo) {
        if (itemRaw.polo) return itemRaw.polo;
        if (itemRaw.nomeParte) {
            const norm = _normalize(itemRaw.nomeParte);
            return passivo.some(function(p) { return _normalize(p.nome).includes(norm) || norm.includes(_normalize(p.nome)); })
                ? 'PASSIVO' : 'ATIVO';
        }
        const tituloNorm = _normalize(itemRaw.titulo || '');
        const temReclamada = passivo.some(function(p) {
            const nomeNorm = _normalize(p.nome);
            const partes = nomeNorm.split(/\s+/).filter(Boolean);
            return partes.length >= 2 &&
                (tituloNorm.includes(nomeNorm) ||
                    (tituloNorm.includes(partes[0]) && tituloNorm.includes(partes[partes.length - 1])));
        });
        return temReclamada ? 'PASSIVO' : null;
    }

    // ==========================================
    // CONFERENCIA DE ACORDAO
    // ==========================================

    async function _conferirAcordao() {
        const partes = await _fetchPartes();
        const raw = await _fetchTimeline();
        const items = raw.map(_classifyItem);

        const acordaoIdxs = items.map(function(it, idx) { return it.categoria === 'acordao' ? idx : -1; }).filter(function(i) { return i >= 0; });
        if (!acordaoIdxs.length) return { ok: false, erro: 'Nenhum acordao encontrado na timeline' };

        const targetAcordaoIdx = Math.max.apply(null, acordaoIdxs);
        const targetAcordao = items[targetAcordaoIdx];

        function isDespachoLike(it) { return it && it.categoria === 'despacho'; }

        function isFirstInstance(it) {
            if (!it || !it._raw) return false;
            const raw = it._raw;
            const candidates = ['grauInstancia', 'grau', 'instancia', 'grau_instancia', 'grauInst'];
            for (const k of candidates) {
                if (raw[k] !== undefined && raw[k] !== null) {
                    const v = String(raw[k]).replace(/[^0-9]/g, '');
                    if (v === '1') return true;
                    if (v) return false;
                }
            }
            const unitKeys = ['unidade', 'nomeUnidade', 'unidadeJudiciaria', 'orgaoJudicial', 'local'];
            for (const k of unitKeys) {
                if (raw[k] && typeof raw[k] === 'string' && /vara/i.test(raw[k])) return true;
            }
            return false;
        }

        async function readTextoFor(it) {
            try {
                if (!it) return { texto: '' };
                if (typeof window.pjeExtrairApi === 'function' && it.uid) {
                    try {
                        const ext = await window.pjeExtrairApi(it.uid, { idProcesso: _idProcesso() });
                        if (ext && ext.sucesso) {
                            if (ext.conteudo) return { texto: String(ext.conteudo) };
                            if (ext.conteudo_bruto) return { texto: String(ext.conteudo_bruto) };
                        }
                    } catch (e) { /* fallback */ }
                }
                if (it.idDoc) {
                    try {
                        const r = await _fetchDocHtml(it.idDoc);
                        if (r && r.texto) return { texto: r.texto };
                    } catch (e) { /* ignore */ }
                }
            } catch (e) { warn('[prep] readTextoFor falhou:', e.message); }
            return { texto: '' };
        }

        let despachoItem = null;
        const requiredPhrase = _compactNormalize('ante o retorno');

        for (let i = targetAcordaoIdx - 1; i >= 0; i--) {
            const it = items[i];
            if (!isDespachoLike(it)) continue;
            if (!isFirstInstance(it)) continue;
            const res = await readTextoFor(it);
            const textoCand = res.texto || '';
            if (!textoCand) continue;
            if (_compactNormalize(textoCand).includes(requiredPhrase)) {
                despachoItem = it;
                break;
            }
        }

        if (!despachoItem) {
            return { ok: false, erro: 'Nenhum despacho relevante encontrado apos o acordao alvo', lastAcordao: targetAcordao };
        }

        let texto = '';
        try {
            if (typeof window.pjeExtrairApi === 'function' && despachoItem.uid) {
                const ext = await window.pjeExtrairApi(despachoItem.uid, { idProcesso: _idProcesso() });
                if (ext && ext.sucesso && ext.conteudo_bruto) texto = ext.conteudo_bruto;
            }
        } catch (e) { /* ignore */ }
        if (!texto && despachoItem.idDoc) {
            try { const r = await _fetchDocHtml(despachoItem.idDoc); texto = r.texto || ''; } catch (e) { /* ignore */ }
        }

        const mantida = /manuten[cç][aã]o|mantida a senten[cç]a|mantido o julgado|mant(e|e)m? a senten[cç]a/i.test(texto);
        const rearbitramento = /rearbitrad.*custas|custas.*rearbitrad|rearbitradas.*custas/i.test(texto);

        function detectarExclusoes(texto, passivo) {
            const tnorm = _normalize(texto || '');
            const exclusoesSet = new Set();
            const numRe = /(\d+)\s*[aAoO]?\s*reclamad[aoas]/g;
            let mm;
            while ((mm = numRe.exec(tnorm)) !== null) {
                const win = _windowAround(tnorm, mm.index, 120, 120);
                if (/(afast|exclu|retir)/.test(win) && /(subsidi|solidar)/.test(win)) {
                    const n = parseInt(mm[1], 10);
                    if (passivo[n - 1]) exclusoesSet.add(passivo[n - 1].nome);
                }
            }
            for (const p of (passivo || [])) {
                if (!p || !p.nome) continue;
                const nomeNorm = _normalize(p.nome);
                let idx2 = tnorm.indexOf(nomeNorm);
                while (idx2 !== -1) {
                    const win = _windowAround(tnorm, idx2, 120, 120);
                    if (/(afast|exclu|retir)/.test(win) && /(subsidi|solidar)/.test(win)) {
                        exclusoesSet.add(p.nome); break;
                    }
                    idx2 = tnorm.indexOf(nomeNorm, idx2 + nomeNorm.length);
                }
            }
            return Array.from(exclusoesSet);
        }

        const exclusoes = detectarExclusoes(texto, partes.passivo || []);
        const tnorm = _normalize(texto);
        const ctpsDespacho = _cooccursInWindow(tnorm,
            ['ctps', 'carteira de trabalho', 'carteira profissional'],
            ['anotar', 'retificar', 'anotacao', 'anotacao', 'retifica', 'registrar', 'lancar', 'lancar'], 120) ||
            _cooccursInWindow(tnorm,
                ['ctps', 'carteira de trabalho'],
                ['dever', 'devera', 'determina', 'determinar', 'ordem', 'ordenar'], 120);
        const fgtsDespacho = _cooccursInWindow(tnorm,
            ['fgts'],
            ['deposito', 'depositar', 'recolhimento', 'recolher', 'guia', 'darf', 'gps', 'conta vinculada', 'vinculada'], 120);

        return {
            ok: true,
            lastAcordao: { data: targetAcordao.data, idDoc: targetAcordao.idDoc, uid: targetAcordao.uid, titulo: targetAcordao.titulo },
            despacho: { data: despachoItem.data, idDoc: despachoItem.idDoc, uid: despachoItem.uid, titulo: despachoItem.titulo },
            analise: {
                mantidaSentenca: !!mantida,
                exclusaoReclamadas: exclusoes,
                rearbitramentoCustas: !!rearbitramento,
                ctpsAnotacao: !!ctpsDespacho,
                fgtsDeposito: !!fgtsDespacho,
            },
        };
    }

    // ==========================================
    // CLASSIFICACAO DE ANEXOS
    // ==========================================

    function classificarAnexo(textoAnexo) {
        const t = (textoAnexo || '').toLowerCase();
        if (/jurisprudencia|jurisprudencia|sentenca|sentenca|isencao|isencao/.test(t)) return { tipo: 'Anexo', ordem: 4 };
        if (/deposito|deposito|preparo/.test(t)) return { tipo: 'Deposito', ordem: 1 };
        if (/gru|custas/.test(t)) return { tipo: 'Custas', ordem: 2 };
        if (/garantia|seguro|susep|apolice|apolice/.test(t)) return { tipo: 'Garantia', ordem: 3 };
        return { tipo: 'Anexo', ordem: 4 };
    }

    // ==========================================
    // DOM-UI HELPERS (usados pelo overlay pos-carga - manter)
    // ==========================================

    function safeDispatch(el, type, opts) {
        try { el.dispatchEvent(new MouseEvent(type, opts || {})); return true; }
        catch (e) {
            try {
                const safeOpts = Object.assign({}, opts || {});
                if ('view' in safeOpts) delete safeOpts.view;
                el.dispatchEvent(new MouseEvent(type, safeOpts));
                return true;
            } catch (e2) { try { el.click(); return true; } catch (e3) { /* ignore */ } }
        }
        return false;
    }

    function getTimelineItems() {
        const selectors = ['li.tl-item-container', '.tl-data .tl-item-container', '.timeline-item'];
        for (const sel of selectors) {
            const items = Array.from(document.querySelectorAll(sel));
            if (items.length > 0) return items;
        }
        return [];
    }

    function encontrarItemTimeline(href) {
        if (!href) return null;
        const items = getTimelineItems();
        for (const item of items) {
            const link = item.querySelector('a.tl-documento[target="_blank"]');
            if (link && link.href === href) return item;
        }
        return null;
    }

    async function expandirAnexos(container) {
        const sleep = function(ms) { return new Promise(function(r) { setTimeout(r, ms); }); };
        try {
            const anexosRoot = container.querySelector('pje-timeline-anexos');
            if (!anexosRoot) return false;
            const toggle = anexosRoot.querySelector('div[name="mostrarOuOcultarAnexos"]');
            if (!toggle) return false;
            if (toggle.getAttribute('aria-pressed') === 'true') return true;
            toggle.click();
            await sleep(400);
            return true;
        } catch (error) {
            err('Erro ao expandir anexos:', error);
            return false;
        }
    }

    function destacarElementoNaTimeline(href) {
        const container = encontrarItemTimeline(href);
        if (!container) { warn('Elemento nao encontrado para href:', href); return; }
        try {
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
            const orig = {
                border: container.style.border,
                background: container.style.background,
                transition: container.style.transition,
            };
            container.style.transition = 'all 0.3s ease';
            container.style.border = '2px solid #fbbf24';
            container.style.background = '#fffbeb';
            setTimeout(function() { expandirAnexos(container); }, 500);
            setTimeout(function() {
                container.style.transition = 'all 0.5s ease';
                container.style.border = orig.border;
                container.style.background = orig.background;
                setTimeout(function() { container.style.transition = orig.transition; }, 500);
            }, 3000);
        } catch (error) { err('Erro ao destacar elemento:', error); }
    }

    // ==========================================
    // ORQUESTRADOR PRINCIPAL - API puro
    // ==========================================

    async function executarPrep(partesData, peritosConhecimento) {
        if (window.hcalcPrepRunning) {
            console.log('[prep.js] Prep ja em execucao, ignorando chamada duplicada');
            return;
        }
        window.hcalcPrepRunning = true;

        try {
            console.log('[prep.js] Iniciando preparacao via API...');

            // 1. Partes - reutilizar partesData.passivo se valido, senao buscar via API
            let passivo = [];
            if (partesData && Array.isArray(partesData.passivo) && partesData.passivo.length > 0) {
                passivo = partesData.passivo;
            } else {
                const partes = await _fetchPartes();
                passivo = partes.passivo || [];
            }
            dbg('[prep] Passivo:', passivo.length, 'parte(s)');

            // 2. Timeline via API
            const rawItems = await _fetchTimeline();
            const items = rawItems.map(_classifyItem);
            console.log('[prep.js] Timeline:', rawItems.length, 'itens classificados:', {
                sentencas: items.filter(function(i) { return i.categoria === 'sentenca'; }).length,
                acordaos: items.filter(function(i) { return i.categoria === 'acordao'; }).length,
                RO: items.filter(function(i) { return i.categoria === 'RO'; }).length,
                RR: items.filter(function(i) { return i.categoria === 'RR'; }).length,
                editais: items.filter(function(i) { return i.categoria === 'edital'; }).length,
                honAjJt: items.filter(function(i) { return i.categoria === 'hon_ajjt'; }).length,
            });

            // 3. Classificar por categoria
            const sentencas = items.filter(function(i) { return i.categoria === 'sentenca'; });
            const acordaos = items.filter(function(i) { return i.categoria === 'acordao'; });
            const editais = items.filter(function(i) { return i.categoria === 'edital'; });
            const honAjJt = items.filter(function(i) { return i.categoria === 'hon_ajjt'; });
            const todosRecursos = items.filter(function(i) { return i.categoria === 'RO' || i.categoria === 'RR'; });

            // 4. Sentenca - mais antiga = ultimo no array (timeline DESC)
            const sentencaAlvo = sentencas.length > 0 ? sentencas[sentencas.length - 1] : null;
            let sentencaDados = { custas: null, hsusp: false, trteng: false, trtmed: false, responsabilidade: null, honorariosPericiais: [] };
            if (sentencaAlvo && sentencaAlvo.idDoc) {
                try {
                    let texto = null;
                    if (typeof window.pjeExtrairApi === 'function' && sentencaAlvo.uid) {
                        try {
                            const ext = await window.pjeExtrairApi(sentencaAlvo.uid, { idProcesso: _idProcesso() });
                            if (ext && ext.sucesso) texto = ext.conteudo_bruto || ext.conteudo || null;
                        } catch (e) { /* fallback */ }
                    }
                    if (!texto) {
                        const r = await _fetchDocHtml(sentencaAlvo.idDoc);
                        texto = r.texto || null;
                    }
                    if (texto) sentencaDados = _extrairDadosSentenca(texto);
                    dbg('[prep] Sentenca extraida:', sentencaDados);
                } catch (e) { warn('[prep] Falha ao ler sentenca:', e.message); }
            }

            // 5. Peritos AJ-JT
            let peritosComAjJt = [];
            if (Array.isArray(peritosConhecimento) && peritosConhecimento.length > 0) {
                peritosComAjJt = await _lerPeritosAjJt(honAjJt, peritosConhecimento);
            }

            // 6. Depositos - filtrar por polo passivo; usar indice real dentro de items
            const acordaoItemIndices = items
                .map(function(it, idx) { return it.categoria === 'acordao' ? idx : -1; })
                .filter(function(i) { return i >= 0; });
            const oldestAcordaoItemIdx = acordaoItemIndices.length > 0 ? Math.max.apply(null, acordaoItemIndices) : -1;

            const depositos = todosRecursos.map(function(rec) {
                const recItemIdx = items.indexOf(rec);
                const ocorreuDepoisDoAcordao = oldestAcordaoItemIdx !== -1 && recItemIdx < oldestAcordaoItemIdx;
                const poloDetectado = _detectarPoloPassivo(rec._raw, passivo);
                if (!ocorreuDepoisDoAcordao && poloDetectado !== 'PASSIVO') return null;

                const depositante = rec.nomeParte ||
                    passivo.map(function(p) { return p.nome; }).find(function(n) { return _normalize(rec.titulo).includes(_normalize(n)); }) || '';

                return {
                    tipo: rec.categoria,
                    texto: rec.titulo,
                    href: _montarHref(rec.uid),
                    data: rec.data,
                    depositante,
                    anexos: rec.anexos.map(function(a) {
                        const cls = classificarAnexo(a.titulo);
                        return {
                            texto: a.titulo,
                            id: a.uid || (a.idDoc ? String(a.idDoc) : null),
                            tipo: cls.tipo,
                            ordem: cls.ordem,
                        };
                    }).sort(function(a, b) { return a.ordem - b.ordem; }),
                };
            }).filter(Boolean);

            // Ordenar depositos por data (mais antigos primeiro)
            depositos.sort(function(a, b) {
                const ts = function(s) {
                    if (!s) return 0;
                    const p = s.split('/');
                    if (p.length < 3) return 0;
                    return new Date(parseInt(p[2]), parseInt(p[1]) - 1, parseInt(p[0])).getTime();
                };
                return ts(a.data) - ts(b.data);
            });

            // 7. Editais - partes intimadas
            let partesIntimadasEdital = [];
            if (editais.length > 0 && passivo.length > 0) {
                partesIntimadasEdital = await _lerPartesEdital(editais, passivo);
            }

            // 8. Conferencia de acordao
            let conferenciaAcordao = null;
            try {
                conferenciaAcordao = await _conferirAcordao();
            } catch (e) {
                warn('[prep] _conferirAcordao falhou:', e.message);
                conferenciaAcordao = { ok: false, erro: e.message };
            }

            // 9. Montar prepResult - shape 100% compativel com overlay (+ conferenciaAcordao)
            const prepResult = {
                sentenca: {
                    data: sentencaAlvo ? sentencaAlvo.data : null,
                    href: sentencaAlvo ? _montarHref(sentencaAlvo.uid) : null,
                    custas: sentencaDados.custas,
                    hsusp: sentencaDados.hsusp,
                    responsabilidade: sentencaDados.responsabilidade,
                    honorariosPericiais: sentencaDados.honorariosPericiais,
                },
                pericia: {
                    trteng: sentencaDados.trteng,
                    trtmed: sentencaDados.trtmed,
                    peritosComAjJt,
                },
                acordaos: acordaos.map(function(a) {
                    return { data: a.data, href: _montarHref(a.uid), id: a.uid || String(a.idDoc || '') };
                }),
                depositos,
                editais: editais.map(function(e) { return { data: e.data, href: _montarHref(e.uid) }; }),
                partesIntimadasEdital,
                conferenciaAcordao,
            };

            console.log('[prep.js] prepResult montado:', {
                sentencaData: prepResult.sentenca.data,
                acordaos: prepResult.acordaos.length,
                depositos: prepResult.depositos.length,
                editais: prepResult.editais.length,
                partesIntimadasEdital: prepResult.partesIntimadasEdital.length,
                conferenciaOk: prepResult.conferenciaAcordao ? prepResult.conferenciaAcordao.ok : null,
            });

            window.hcalcPrepResult = prepResult;
            return prepResult;
        } finally {
            window.hcalcPrepRunning = false;
        }
    }

    // ==========================================
    // EXPORTS
    // ==========================================
    window.executarPrep = executarPrep;
    window.destacarElementoNaTimeline = destacarElementoNaTimeline;
    window.encontrarItemTimeline = encontrarItemTimeline;
    window.expandirAnexos = expandirAnexos;

})();