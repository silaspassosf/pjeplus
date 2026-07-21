'use strict';
// lista.check.debug.js v1.0 — IIFE depurador isolado para chamadas API da timeline
// Uso: Cole no console do navegador na página de processo PJe e execute.
// Resultados: console.log com prefixo [DEBUG LISTA] + painel flutuante na página.

(function () {
    'use strict';

    const D = '[DEBUG LISTA]';
    const results = {};

    // ────────────────────────────────────────────────────────────
    // HELPERS
    // ────────────────────────────────────────────────────────────
    function log(step, label, data) {
        const ok = data !== undefined && data !== null && data !== false && !(Array.isArray(data) && data.length === 0 && label !== 'itensBrutos');
        const status = ok ? '✅' : '❌';
        console.log(`${D} ${status} ${step}: ${label}`, data !== undefined ? data : '');
        results[step] = { status: ok, label, data };
        updatePanel();
    }

    function logError(step, label, err) {
        console.error(`${D} ❌ ${step}: ${label}`, err);
        results[step] = { status: false, label, error: String(err?.message || err) };
        updatePanel();
    }

    // ────────────────────────────────────────────────────────────
    // PAINEL FLUTUANTE
    // ────────────────────────────────────────────────────────────
    function createPanel() {
        const existing = document.getElementById('pje-debug-lista-panel');
        if (existing) existing.remove();

        const panel = document.createElement('div');
        panel.id = 'pje-debug-lista-panel';
        panel.style.cssText = `
            position: fixed; top: 10px; right: 10px; z-index: 999999999;
            background: #1a1a2e; color: #e0e0e0; font-family: 'Consolas', monospace;
            font-size: 12px; border: 2px solid #e94560; border-radius: 10px;
            padding: 12px 16px; max-width: 480px; max-height: 80vh; overflow-y: auto;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5); pointer-events: auto;
        `;

        panel.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;border-bottom:1px solid #333;padding-bottom:8px">
                <strong style="color:#e94560;font-size:14px">🐞 DEBUG LISTA CHECK</strong>
                <div>
                    <button id="pje-debug-run-btn" style="background:#0f3460;color:#fff;border:none;border-radius:4px;padding:4px 10px;cursor:pointer;font-size:11px;margin-right:4px">🔄 Executar</button>
                    <button id="pje-debug-close-btn" style="background:#533483;color:#fff;border:none;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:11px">✕</button>
                </div>
            </div>
            <div id="pje-debug-results" style="min-height:60px">
                <div style="color:#888;font-style:italic;text-align:center;padding:20px 0">Clique em "Executar" para iniciar o debug...</div>
            </div>
            <div style="margin-top:8px;padding-top:6px;border-top:1px solid #333;font-size:10px;color:#888">
                Abra o console (F12) para logs detalhados
            </div>
        `;

        document.body.appendChild(panel);

        document.getElementById('pje-debug-run-btn').onclick = () => { runDebug(); };
        document.getElementById('pje-debug-close-btn').onclick = () => { panel.remove(); };

        panel.addEventListener('mousedown', e => e.stopPropagation());
        panel.addEventListener('click', e => e.stopPropagation());
    }

    function updatePanel() {
        const container = document.getElementById('pje-debug-results');
        if (!container) return;

        const steps = [
            { key: 'url', label: 'URL da página' },
            { key: 'idProcesso', label: 'ID do processo extraído' },
            { key: 'cookies', label: 'Cookies disponíveis' },
            { key: 'xsrf', label: 'XSRF-TOKEN encontrado' },
            { key: 'headers', label: 'Headers montados' },
            { key: 'apiUrl', label: 'URL da API construída' },
            { key: 'apiCall', label: 'Chamada fetch()' },
            { key: 'apiStatus', label: 'Status HTTP da resposta' },
            { key: 'apiBody', label: 'Corpo da resposta (raw)' },
            { key: 'apiParse', label: 'JSON parseado' },
            { key: 'itensBrutos', label: 'Itens retornados pela API' },
            { key: 'classificacao', label: 'Classificação _pjeTlClassApi()' },
            { key: 'documentos', label: 'Documentos após pipeline' },
            { key: 'filtrados', label: 'Após filtrarDocs()' },
            { key: 'relatorio', label: 'Relatório final (construirOrdem)' },
        ];

        let html = '<table style="width:100%;border-collapse:collapse">';
        for (const step of steps) {
            const r = results[step.key];
            let icon = '⏳';
            let detail = '';
            if (r) {
                icon = r.status ? '✅' : '❌';
                detail = r.error ? `: ${truncate(r.error, 50)}` : '';
                if (r.data !== undefined && r.data !== null && typeof r.data !== 'object') {
                    detail = `: ${truncate(String(r.data), 50)}`;
                } else if (Array.isArray(r.data)) {
                    detail = ` (${r.data} itens)`;
                }
            }
            html += `<tr>
                <td style="padding:2px 4px;width:22px">${icon}</td>
                <td style="padding:2px 4px;color:#aaa">${step.label}</td>
                <td style="padding:2px 4px;color:#4ade80;font-size:10px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${detail}</td>
            </tr>`;
        }
        html += '</table>';

        const total = steps.length;
        const ok = steps.filter(s => results[s.key]?.status === true).length;
        const fail = steps.filter(s => results[s.key]?.status === false).length;
        const pending = total - ok - fail;

        html += `<div style="margin-top:8px;padding-top:6px;border-top:1px solid #333;font-size:10px;display:flex;justify-content:space-between">
            <span style="color:#4ade80">✅ ${ok}</span>
            <span style="color:#e94560">❌ ${fail}</span>
            <span style="color:#888">⏳ ${pending}</span>
            <span style="color:#555">/ ${total}</span>
        </div>`;

        container.innerHTML = html;
    }

    function truncate(str, max) {
        if (!str) return '';
        return str.length > max ? str.substring(0, max) + '...' : str;
    }

    // ────────────────────────────────────────────────────────────
    // FUNÇÕES DE DEBUG (cópias isoladas)
    // ────────────────────────────────────────────────────────────

    function _debugXsrf() {
        const cookies = document.cookie.split(';').map(s => s.trim());
        const xsrfCookie = cookies.find(s => s.toLowerCase().startsWith('xsrf-token='));
        if (xsrfCookie) {
            const token = decodeURIComponent(xsrfCookie.split('=').slice(1).join('='));
            return { found: true, token: token.substring(0, 20) + '...' + token.substring(token.length - 5), fullLength: token.length };
        }
        const variacoes = ['x-xsrf-token', 'xsrf-token', 'x-csrf-token', 'csrf-token', 'x-csrftoken'];
        for (const nome of variacoes) {
            const found = cookies.find(s => s.toLowerCase().startsWith(nome + '='));
            if (found) return { found: true, cookieName: nome, token: found.substring(nome.length + 1).substring(0, 25) + '...' };
        }
        return { found: false, cookiesDisponiveis: cookies };
    }

    function _debugIdProcesso() {
        const fullUrl = window.location.href;
        const path = window.location.pathname;
        const m1 = path.match(/\/processo\/(\d+)/);
        const m2 = fullUrl.match(/processo[\/=](\d+)/);
        const m3 = path.match(/\/\d+\/(\d+)/);
        const m4 = fullUrl.match(/\/(\d{7,})/);
        return {
            url: fullUrl,
            pathname: path,
            hash: window.location.hash,
            search: window.location.search,
            patternOriginal: m1 ? m1[1] : null,
            patternHash: m2 ? m2[1] : null,
            patternPath: m3 ? m3[1] : null,
            patternAny: m4 ? m4[1] : null,
        };
    }

    function _debugHeaders(idProcesso) {
        const h = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Grau-Instancia': '1',
        };
        const xsrfInfo = _debugXsrf();
        if (xsrfInfo.found) {
            const cookies = document.cookie.split(';').map(s => s.trim());
            const xsrfCookie = cookies.find(s => s.toLowerCase().startsWith('xsrf-token='));
            if (xsrfCookie) {
                const token = decodeURIComponent(xsrfCookie.split('=').slice(1).join('='));
                h['X-XSRF-TOKEN'] = token;
            }
        }
        return { headers: h, hasXsrf: !!h['X-XSRF-TOKEN'] };
    }

    function _debugBuildUrl(idProcesso) {
        if (!idProcesso) return { error: 'Sem ID do processo' };
        const params = new URLSearchParams({
            buscarMovimentos: 'false',
            buscarDocumentos: 'true',
            somenteDocumentosAssinados: 'false',
        });
        const url = window.location.origin + '/pje-comum-api/api/processos/id/' + idProcesso + '/timeline?' + params;
        return { url, origin: window.location.origin, idProcesso, params: params.toString() };
    }

    function _debugClassApi(item) {
        const low = ((item.titulo || '') + ' ' + (item.nomeDocumento || '') + ' ' + (item.descricao || '')).toLowerCase();
        if (low.includes('devolução de ordem')) return 'Certidão devolução pesquisa';
        if (low.includes('certidão de oficial') || low.includes('oficial de justiça')) return 'Certidão de oficial de justiça';
        if (low.includes('mandado de pagamento') && low.includes('alvará')) return 'Alvarás';
        if (low.includes('alvará') || low.includes('juntada de alvará')) return 'Alvarás';
        if (low.includes('sobrestamento')) return 'Decisão (Sobrestamento)';
        if (low.includes('serasa') || low.includes('apjur') || low.includes('carta ação') || low.includes('carta acao')) return 'SerasaAntigo';
        if (low.includes('edital')) return 'Edital';
        return null;
    }

    // ────────────────────────────────────────────────────────────
    // PIPELINE COMPLETO DE DEBUG
    // ────────────────────────────────────────────────────────────

    async function runDebug() {
        console.clear();
        console.log(`%c${D} ===== INÍCIO DEBUG LISTA CHECK =====`, 'color:#e94560;font-weight:bold;font-size:14px');
        console.log(`${D} Timestamp: ${new Date().toISOString()}`);
        console.log(`${D} User Agent: ${navigator.userAgent}`);
        console.log('');

        // ── ETAPA 1: URL / Ambiente ──
        console.log(`%c${D} 📍 ETAPA 1: Environment Probe`, 'color:#0f3460;font-weight:bold');
        const urlInfo = _debugIdProcesso();
        log('url', 'URL completa', urlInfo.url);
        console.log(`${D} 🔍 Padrões testados:`, urlInfo);

        // ── ETAPA 2: ID do Processo ──
        console.log(`\n%c${D} 🔢 ETAPA 2: ID do Processo`, 'color:#0f3460;font-weight:bold');
        const idProcesso = urlInfo.patternOriginal || urlInfo.patternHash || urlInfo.patternPath || urlInfo.patternAny;
        log('idProcesso', 'ID extraído', idProcesso);
        if (!idProcesso) {
            logError('idProcesso', 'Nenhum ID encontrado');
            console.warn(`${D} ⚠️ Dica: A URL atual pode não ser uma página de processo PJe.`);
            console.warn(`${D} ⚠️ Hash:`, window.location.hash);
            console.warn(`${D} ⚠️ Search:`, window.location.search);
        }

        // ── ETAPA 3: Cookies ──
        console.log(`\n%c${D} 🍪 ETAPA 3: Cookies / XSRF Probe`, 'color:#0f3460;font-weight:bold');
        const cookieList = document.cookie.split(';').map(s => s.trim()).filter(Boolean);
        log('cookies', 'Total de cookies', cookieList.length);
        if (cookieList.length > 0) {
            console.table(cookieList.map(c => {
                const [name, ...rest] = c.split('=');
                const value = rest.join('=');
                return { name: name || '', value: value.substring(0, 30) + (value.length > 30 ? '...' : '') };
            }));
        } else {
            console.warn(`${D} ⚠️ Nenhum cookie encontrado! document.cookie está vazio.`);
        }

        const xsrfInfo = _debugXsrf();
        log('xsrf', 'XSRF-TOKEN', xsrfInfo.found ? xsrfInfo.token : 'NÃO ENCONTRADO');
        if (!xsrfInfo.found) {
            console.warn(`${D} ⚠️ XSRF-TOKEN não encontrado.`);
            console.warn(`${D} 🔍 Cookies:`, cookieList);
        }

        // ── ETAPA 4: Headers ──
        console.log(`\n%c${D} 📋 ETAPA 4: Headers montados`, 'color:#0f3460;font-weight:bold');
        const headerInfo = _debugHeaders(idProcesso);
        log('headers', 'Headers', headerInfo.headers);
        console.log(`${D} Headers:`, JSON.stringify(headerInfo.headers, null, 2));

        // ── ETAPA 5: URL da API ──
        console.log(`\n%c${D} 🔗 ETAPA 5: URL da API`, 'color:#0f3460;font-weight:bold');
        const urlInfo2 = _debugBuildUrl(idProcesso);
        log('apiUrl', 'URL completa', urlInfo2.url || urlInfo2.error);
        if (urlInfo2.url) {
            console.log(`${D} URL: ${urlInfo2.url}`);
        } else {
            logError('apiUrl', 'Falha ao montar URL:', urlInfo2.error);
        }

        // ── ETAPA 6: Chamada API ──
        console.log(`\n%c${D} 🌐 ETAPA 6: Chamada fetch()`, 'color:#0f3460;font-weight:bold');
        log('apiCall', 'Iniciando chamada...', true);

        if (!idProcesso || !urlInfo2.url) {
            logError('apiCall', 'ID do processo ou URL inválidos. Pulando chamada API.');
            logError('apiStatus', 'N/A');
            logError('apiBody', 'N/A');
        } else {
            try {
                console.time(`${D} ⏱ fetch`);
                const resp = await fetch(urlInfo2.url, {
                    method: 'GET',
                    credentials: 'include',
                    headers: headerInfo.headers,
                });
                console.timeEnd(`${D} ⏱ fetch`);

                log('apiCall', 'fetch concluído', true);
                log('apiStatus', `HTTP ${resp.status} ${resp.statusText}`, resp.status);
                console.log(`${D} Response headers:`);
                resp.headers.forEach((v, k) => console.log(`   ${k}: ${v}`));

                const ct = resp.headers.get('content-type') || '';
                log('apiStatus', 'Content-Type', ct);

                if (!resp.ok) {
                    logError('apiCall', `HTTP ${resp.status} - ${resp.statusText}`);
                    try {
                        const errorBody = await resp.text();
                        logError('apiBody', 'Corpo do erro', errorBody.substring(0, 500));
                        console.error(`${D} Corpo completo do erro:`, errorBody);
                    } catch (e) {
                        logError('apiBody', 'Não foi possível ler corpo do erro', e);
                    }
                } else {
                    log('apiCall', 'Status OK', true);

                    // ── ETAPA 7: Corpo da resposta ──
                    console.log(`\n%c${D} 📦 ETAPA 7: Corpo da resposta`, 'color:#0f3460;font-weight:bold');
                    let rawBody;
                    try {
                        rawBody = await resp.text();
                    } catch (e) {
                        logError('apiBody', 'Erro ao ler corpo', e);
                        rawBody = null;
                    }

                    if (rawBody) {
                        log('apiBody', 'Corpo bruto', rawBody.substring(0, 300) + (rawBody.length > 300 ? '...' : ''));
                        console.log(`${D} Tamanho: ${rawBody.length} bytes`);
                        console.log(`${D} Primeiros 500 chars:`, rawBody.substring(0, 500));

                        // ── ETAPA 8: Parse JSON ──
                        console.log(`\n%c${D} 🔧 ETAPA 8: Parse JSON`, 'color:#0f3460;font-weight:bold');
                        let parsed;
                        try {
                            parsed = JSON.parse(rawBody);
                            log('apiParse', 'JSON parseado com sucesso', true);
                            console.log(`${D} Tipo: ${Array.isArray(parsed) ? 'Array' : typeof parsed}`);

                            if (Array.isArray(parsed)) {
                                log('itensBrutos', 'Total de itens na API', parsed.length);
                                console.log(`${D} Primeiros 3 itens:`);
                                parsed.slice(0, 3).forEach((item, i) => {
                                    console.log(`   [${i}] id:${item.id} | uid:${item.idUnicoDocumento} | titulo:${item.titulo} | nomeDoc:${item.nomeDocumento}`);
                                });

                                // ── ETAPA 9: Classificação ──
                                console.log(`\n%c${D} 🏷️ ETAPA 9: Classificação _pjeTlClassApi()`, 'color:#0f3460;font-weight:bold');
                                const classificados = parsed.map(item => ({
                                    id: item.id,
                                    idUnico: item.idUnicoDocumento,
                                    titulo: item.titulo,
                                    nomeDocumento: item.nomeDocumento,
                                    descricao: item.descricao,
                                    classificadoComo: _debugClassApi(item),
                                    temAnexos: Array.isArray(item.anexos) && item.anexos.length > 0,
                                    qtdAnexos: Array.isArray(item.anexos) ? item.anexos.length : 0,
                                }));
                                log('classificacao', 'Itens classificados', classificados.length);
                                console.table(classificados);

                                const naoClassificados = classificados.filter(c => c.classificadoComo === null);
                                if (naoClassificados.length > 0) {
                                    console.warn(`${D} ⚠️ ${naoClassificados.length} itens NÃO classificados (null)!`);
                                    console.warn(`${D} ⚠️ Esses itens serão IGNORADOS.`);
                                    console.table(naoClassificados);
                                }

                                // ── ETAPA 10: Simular pipeline completo ──
                                console.log(`\n%c${D} 🔄 ETAPA 10: Pipeline completo`, 'color:#0f3460;font-weight:bold');

                                const docs = [];
                                for (const item of parsed) {
                                    if (!item.idUnicoDocumento) continue;
                                    const tipo = _debugClassApi(item);
                                    if (!tipo) continue;
                                    const uid = item.idUnicoDocumento;
                                    docs.push({
                                        tipo, texto: item.titulo || '', id: uid,
                                        idDoc: item.id ? String(item.id) : null,
                                        data: item.data || item.atualizadoEm || '', isAnexo: false,
                                    });
                                    if (Array.isArray(item.anexos)) {
                                        for (const anexo of item.anexos) {
                                            const t = ((anexo.titulo || '') + ' ' + (anexo.nomeDocumento || '')).toLowerCase();
                                            const tipoAnexo = /serasa|serasajud/.test(t) ? 'Serasa' : /cnib|indisp/.test(t) ? 'CNIB' : null;
                                            if (!tipoAnexo) continue;
                                            docs.push({
                                                tipo: tipoAnexo, texto: anexo.titulo || '',
                                                id: anexo.idUnicoDocumento || `anexo_${uid}_${tipoAnexo}`,
                                                idDoc: anexo.id ? String(anexo.id) : null,
                                                data: anexo.data || anexo.atualizadoEm || '',
                                                isAnexo: true, parentId: uid,
                                            });
                                        }
                                    }
                                }
                                log('documentos', 'Documentos montados', docs.length);
                                console.table(docs.map(d => ({
                                    tipo: d.tipo, texto: (d.texto || '').substring(0, 40),
                                    id: d.id, isAnexo: d.isAnexo, parentId: d.parentId || '-'
                                })));

                                if (docs.length === 0) {
                                    console.error(`${D} ❌ NENHUM documento gerado! _pjeTlClassApi() retornou null para todos.`);
                                }

                                // Simular filtrarDocs
                                const filtrados = docs.filter(d => {
                                    const tipo = (d.tipo || '').toLowerCase();
                                    const texto = (d.texto || '').toLowerCase();
                                    if (tipo === 'edital') return false;
                                    if (/expedi[cç][aã]o/.test(tipo) && /ordem/.test(tipo)) return false;
                                    if (/expedi[cç][aã]o/.test(texto) && /ordem/.test(texto)) return false;
                                    if (tipo === 'alvarás' && /(expedi[cç][aã]o|expedid[ao]s?|devolvid[ao]s?)/.test(texto)) return false;
                                    return true;
                                });
                                log('filtrados', 'Após filtrarDocs()', filtrados.length);
                                console.log(`${D} Filtrados: ${filtrados.length} de ${docs.length}`);

                                // Simular construirOrdem
                                const usados = new Set();
                                const relatorio = [];
                                const certs = filtrados.filter(d => !d.isAnexo && /pesquisa|certid[aã]o/i.test(d.tipo)).sort((a, b) => {
                                    const da = (a.data || '').split('/').reverse().join('').padEnd(8, '0');
                                    const db = (b.data || '').split('/').reverse().join('').padEnd(8, '0');
                                    return db.localeCompare(da);
                                });
                                for (const cert of certs) {
                                    const anexos = filtrados.filter(x => x.parentId === cert.id && (x.tipo === 'Serasa' || x.tipo === 'CNIB'));
                                    if (!anexos.length && /oficial/i.test(cert.tipo)) continue;
                                    usados.add(cert.id);
                                    relatorio.push({ ...cert, _label: 'Pesquisa' });
                                    for (const ax of anexos) {
                                        usados.add(ax.id);
                                        relatorio.push({ ...ax, _label: ax.tipo });
                                    }
                                }
                                filtrados.filter(d => !usados.has(d.id)).forEach(d => {
                                    relatorio.push({ ...d, _label: d.tipo || 'Documento' });
                                });
                                log('relatorio', 'Relatório final', relatorio.length);
                                console.table(relatorio.map(r => ({
                                    label: r._label, texto: (r.texto || '').substring(0, 40),
                                    id: r.id, data: r.data
                                })));

                                if (relatorio.length === 0) {
                                    console.error(`${D} ❌❌❌ RELATÓRIO VAZIO!`);
                                    console.error(`${D} Causas: 1) Classificação null 2) Filtro removeu tudo 3) Sem idUnicoDocumento`);
                                }

                            } else if (typeof parsed === 'object' && parsed !== null) {
                                log('itensBrutos', 'Objeto (não array)', true);
                                console.log(`${D} Chaves:`, Object.keys(parsed));
                                console.log(`${D} Objeto:`, parsed);
                                if (parsed.content && Array.isArray(parsed.content)) {
                                    console.log(`${D} 🔍 Campo 'content' (Spring pagination) com ${parsed.content.length} itens`);
                                }
                                if (parsed.data && Array.isArray(parsed.data)) {
                                    console.log(`${D} 🔍 Campo 'data' com ${parsed.data.length} itens`);
                                }
                            } else {
                                log('itensBrutos', 'Tipo inesperado', typeof parsed);
                            }
                        } catch (e) {
                            logError('apiParse', 'Erro ao parsear JSON', e);
                            console.error(`${D} ❌ JSON inválido! Primeiros 300 chars:`, rawBody.substring(0, 300));
                        }
                    } else {
                        logError('apiBody', 'Corpo vazio');
                    }
                }
            } catch (e) {
                logError('apiCall', 'Erro no fetch', e);
                console.error(`${D} ❌ fetch() exceção:`, e);
            }
        }

        // ── RESUMO FINAL ──
        console.log(`\n%c${D} ===== RESUMO DO DEBUG =====`, 'color:#e94560;font-weight:bold;font-size:14px');
        const stepKeys = ['url', 'idProcesso', 'cookies', 'xsrf', 'headers', 'apiUrl', 'apiCall', 'apiStatus', 'apiBody', 'apiParse', 'itensBrutos', 'classificacao', 'documentos', 'filtrados', 'relatorio'];
        for (const s of stepKeys) {
            const r = results[s];
            if (r) {
                console.log(`${D} ${r.status ? '✅' : '❌'} ${s}: ${r.label}${r.error ? ' - ERRO: ' + r.error : ''}`);
            } else {
                console.log(`${D} ⏳ ${s}: não executado`);
            }
        }

        if (results.relatorio?.status === true && results.relatorio?.data > 0) {
            console.log(`${D} ✅✅✅ Pipeline OK! ${results.relatorio.data} itens no relatório.`);
        } else {
            console.error(`${D} ❌❌❌ PIPELINE COM FALHAS - relatório vazio ou não gerado.`);
        }
        console.log(`%c${D} ===== FIM DEBUG =====`, 'color:#e94560;font-weight:bold;font-size:14px');
    }

    // ────────────────────────────────────────────────────────────
    // INICIALIZAÇÃO: Cria painel e já executa debug automaticamente
    // ────────────────────────────────────────────────────────────
    console.log(`%c${D} Inicializando debugger...`, 'color:#0f3460;font-weight:bold');
    try {
        createPanel();
        // Auto-execução com delay para garantir que o DOM esteja pronto
        setTimeout(() => runDebug(), 300);
    } catch (e) {
        console.error(`${D} Erro na inicialização:`, e);
    }
})();