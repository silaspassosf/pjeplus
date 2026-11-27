(function () {
    'use strict';

    var TAG = '[sisb-series]';
    var URL_API = 'https://sisbajud.pdpj.jus.br/v1/serie';
    var CHAVE_TOKEN = 'pjetools_sisbajud_token';
    var TIPO_SITUACAO_ATIVA = 1;
    var TIPO_SITUACAO_ENCERRADA = 2;
    var DIAS_CORTE = 30;
    var LIMITE_IRRISORIO = 100.0;
    var LIMITE_BLOQUEIO = 1000.0;
    var VALOR_EXECUCAO_FALLBACK = 1003.0;

    var P_STYLE = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;'
        + 'text-align:justify !important;text-indent:4.5cm;"';

    var RE_CNJ = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;

    function log() {
        try { console.log.apply(console, [TAG].concat([].slice.call(arguments))); } catch (e) { }
    }

    function esc(s) {
        return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function digitos(v) { return String(v || '').replace(/\D/g, ''); }

    function brl(v) {
        return 'R$ ' + Number(v || 0).toFixed(2)
            .replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }

    function dataCurta(ms) {
        if (!ms) return '—';
        var d = new Date(Number(ms));
        return ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2) + '/' + d.getFullYear();
    }

    function numeroProcessoDaPagina() {
        var doTitulo = String(document.title || '').match(RE_CNJ);
        if (doTitulo) return doTitulo[0];

        var el = document.querySelector('.texto-numero-processo');
        if (el) {
            var doEl = String(el.textContent || '').match(RE_CNJ);
            if (doEl) return doEl[0];
        }

        var campo = document.querySelector('#numeroProcesso');
        if (campo && campo.value && RE_CNJ.test(campo.value)) {
            return String(campo.value).match(RE_CNJ)[0];
        }

        var doHref = String(location.href || '').match(RE_CNJ);
        if (doHref) return doHref[0];

        return '';
    }

    // ── Token e ponte com a aba do SISBAJUD via GM_* ───────────────────
    var CHAVE_TOKEN_REQ = 'pjetools_sisbajud_token_req';
    var CHAVE_TOKEN_RESP = 'pjetools_sisbajud_token_resp';
    var CHAVE_API_REQ = 'pjetools_sisbajud_series_req';
    var CHAVE_API_RESP = 'pjetools_sisbajud_series_resp';

    function ehHostSisbajud() {
        return /^sisbajud\.(pdpj|cnj)\.jus\.br$/.test(location.hostname);
    }

    function limparToken(t) {
        return String(t || '').trim().replace(/^"+|"+$/g, '');
    }

    function lerToken() {
        try {
            if (typeof GM_getValue === 'function') return limparToken(GM_getValue(CHAVE_TOKEN, '') || '');
        } catch (e) { }
        try { return limparToken(localStorage.getItem(CHAVE_TOKEN) || ''); } catch (e) { return ''; }
    }

    function salvarToken(t) {
        t = limparToken(t);
        if (!t) return;
        try {
            if (typeof GM_setValue === 'function') { GM_setValue(CHAVE_TOKEN, t); return; }
        } catch (e) { }
        try { localStorage.setItem(CHAVE_TOKEN, t); } catch (e) { }
    }

    function pedirTokenParaAbaSisbajud(timeoutMs) {
        return new Promise(function (resolve) {
            if (typeof GM_setValue !== 'function' || typeof GM_addValueChangeListener !== 'function') {
                resolve('');
                return;
            }
            var reqId = Date.now() + '_' + Math.random().toString(36).slice(2, 8);
            var resolvido = false;
            var listenerRespId = null;
            var listenerTokId = null;
            var timer = null;

            function finalizar(val) {
                if (resolvido) return;
                resolvido = true;
                if (timer) clearTimeout(timer);
                try {
                    if (typeof GM_removeValueChangeListener === 'function') {
                        if (listenerRespId != null) GM_removeValueChangeListener(listenerRespId);
                        if (listenerTokId != null) GM_removeValueChangeListener(listenerTokId);
                    }
                } catch (e) { }
                resolve(limparToken(val));
            }

            listenerRespId = GM_addValueChangeListener(CHAVE_TOKEN_RESP, function (_name, _oldVal, newVal) {
                if (newVal && newVal.id === reqId) finalizar(newVal.token || '');
            });

            listenerTokId = GM_addValueChangeListener(CHAVE_TOKEN, function (_name, _oldVal, newVal) {
                var limpo = limparToken(newVal);
                if (limpo) finalizar(limpo);
            });

            timer = setTimeout(function () {
                var atual = lerToken();
                finalizar(atual || '');
            }, timeoutMs || 1500);

            GM_setValue(CHAVE_TOKEN_REQ, { id: reqId, ts: Date.now() });
        });
    }

    function requisitarViaAbaSisbajud(url, timeoutMs) {
        return new Promise(function (resolve) {
            if (typeof GM_setValue !== 'function' || typeof GM_addValueChangeListener !== 'function') {
                resolve(null);
                return;
            }
            var reqId = Date.now() + '_' + Math.random().toString(36).slice(2, 8);
            var resolvido = false;
            var listenerId = null;
            var timer = null;

            function finalizar(val) {
                if (resolvido) return;
                resolvido = true;
                if (timer) clearTimeout(timer);
                try {
                    if (listenerId != null && typeof GM_removeValueChangeListener === 'function') {
                        GM_removeValueChangeListener(listenerId);
                    }
                } catch (e) { }
                resolve(val);
            }

            listenerId = GM_addValueChangeListener(CHAVE_API_RESP, function (_name, _oldVal, newVal) {
                if (newVal && newVal.id === reqId) {
                    finalizar({ status: Number(newVal.status || 0), texto: String(newVal.texto || '') });
                }
            });

            timer = setTimeout(function () { finalizar(null); }, timeoutMs || 8000);
            GM_setValue(CHAVE_API_REQ, { id: reqId, url: url, ts: Date.now() });
        });
    }

    function expDoJwt(token) {
        try {
            var partes = String(token).split('.');
            if (partes.length < 2) return 0;
            var b64 = partes[1].replace(/-/g, '+').replace(/_/g, '/');
            while (b64.length % 4) b64 += '=';
            var payload = JSON.parse(atob(b64));
            return Number(payload.exp || 0);
        } catch (e) { return 0; }
    }

    // ── Chamada à API do SISBAJUD ──────────────────────────────────────
    function requisitarSameOrigin(url, token) {
        var headers = { Accept: 'application/json' };
        if (token) headers.Authorization = 'Bearer ' + token;
        return fetch(url, { method: 'GET', headers: headers, credentials: 'include' })
            .then(function (r) {
                return r.text().then(function (t) { return { status: r.status, texto: t }; });
            });
    }

    function requisitar(url, token) {
        if (ehHostSisbajud()) {
            var caminho = url.replace(/^https?:\/\/[^/]+/, '');
            return requisitarSameOrigin(location.origin + caminho, token);
        }
        return new Promise(function (resolve, reject) {
            // Backend Spring do SISBAJUD devolve 403 "Invalid CORS request" se
            // receber Origin de outro domínio (ex: https://pje.trt2.jus.br).
            var headers = {
                Accept: 'application/json',
                Origin: 'https://sisbajud.pdpj.jus.br',
                Referer: 'https://sisbajud.pdpj.jus.br/',
            };
            if (token) headers.Authorization = 'Bearer ' + token;
            if (typeof GM_xmlhttpRequest === 'function') {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: url,
                    headers: headers,
                    anonymous: !!token,
                    timeout: 20000,
                    onload: function (r) { resolve({ status: r.status, texto: r.responseText || '' }); },
                    onerror: function () { reject(new Error('Falha de rede ao consultar API do SISBAJUD.')); },
                    ontimeout: function () { reject(new Error('Timeout (20s) na API do SISBAJUD.')); },
                });
                return;
            }
            requisitarSameOrigin(url, token).then(resolve, reject);
        });
    }

    async function lerSeries(numero) {
        var dig = digitos(numero);
        if (dig.length < 15) return { erro: 'Número inválido: ' + numero };

        var token = lerToken();
        var exp = token ? expDoJwt(token) : 0;
        if (!token || (exp && exp * 1000 < Date.now())) {
            log('token ausente ou expirado — solicitando à aba do SISBAJUD...');
            var novo = await pedirTokenParaAbaSisbajud(1500);
            if (novo) token = novo;
        }

        var url = URL_API + '?codProcesso=' + encodeURIComponent(dig);
        var resp = await requisitar(url, token);
        log('HTTP', resp.status, 'v1/serie', token ? '(bearer)' : '(sem-token)', resp.status !== 200 ? String(resp.texto || '').slice(0, 120) : '');

        // Se o navegador/Tampermonkey ignorou o override de Origin e o backend
        // devolveu 403 ("Invalid CORS request"), executa o GET same-origin
        // dentro da aba do SISBAJUD aberta via GM_addValueChangeListener.
        if (resp.status === 403 && !ehHostSisbajud()) {
            log('HTTP 403 cross-origin — delegando fetch same-origin para a aba do SISBAJUD...');
            var viaAba = await requisitarViaAbaSisbajud(url, 8000);
            if (viaAba) {
                log('HTTP (via aba SISBAJUD)', viaAba.status, 'v1/serie', viaAba.status !== 200 ? String(viaAba.texto || '').slice(0, 120) : '');
                resp = viaAba;
            } else {
                log('aba do SISBAJUD não respondeu à delegação (fechada ou sem pjetools atualizado)');
            }
        }

        if (resp.status === 401 || resp.status === 403) {
            var tokenAntigo = token;
            var recoletado = await pedirTokenParaAbaSisbajud(1500);
            if (recoletado && recoletado !== tokenAntigo) {
                token = recoletado;
                resp = await requisitar(url, token);
                log('HTTP (retry)', resp.status, 'v1/serie (bearer)');
                if (resp.status === 403 && !ehHostSisbajud()) {
                    var viaAba2 = await requisitarViaAbaSisbajud(url, 8000);
                    if (viaAba2) {
                        log('HTTP (retry via aba SISBAJUD)', viaAba2.status, 'v1/serie');
                        resp = viaAba2;
                    }
                }
            }
        }

        if (resp.status === 401 || resp.status === 403) {
            var detalhe = String(resp.texto || '').replace(/\s+/g, ' ').trim().slice(0, 80);
            var ehCors = resp.status === 403 && /cors/i.test(detalhe);
            return {
                erro: 'API SISBAJUD recusou (HTTP ' + resp.status + (detalhe ? ': ' + detalhe : '') + '). '
                    + (ehCors
                        ? 'Mantenha uma aba logada do SISBAJUD aberta (e atualizada com F5) para consulta same-origin.'
                        : 'Atualize (F5) a aba do SISBAJUD logada; se persistir, faça logout/login para renovar o token.'),
            };
        }
        if (resp.status !== 200) {
            return { erro: 'API SISBAJUD devolveu HTTP ' + resp.status + (resp.status <= 0 ? ' (rede/CORS)' : '') + '.' };
        }

        var bruto;
        try { bruto = JSON.parse(resp.texto); } catch (e) {
            return { erro: 'Corpo não-JSON da API: ' + String(resp.texto).slice(0, 120) };
        }
        if (!Array.isArray(bruto)) {
            return { erro: 'Corpo inesperado da API (' + typeof bruto + ').' };
        }

        var limite = new Date();
        limite.setHours(0, 0, 0, 0);
        limite.setDate(limite.getDate() - DIAS_CORTE);

        var validas = [];
        bruto.forEach(function (s) {
            try {
                var sit = s.tipoSituacaoSerie;
                if (sit !== TIPO_SITUACAO_ATIVA && sit !== TIPO_SITUACAO_ENCERRADA) return;
                var fim = s.dataLimite;
                if (!fim && sit === TIPO_SITUACAO_ENCERRADA) return;
                if (fim && new Date(Number(fim)) < limite) return;
                var ordem = s.ordemOriginal || {};
                var vb = Number(s.valorBloqueioRealizado || 0);
                var vbr = Number(s.valorBloqueioTotal || 0);
                validas.push({
                    id_serie: String(s.codSerie),
                    protocolo: String(ordem.protocolo || ''),
                    acao: String(ordem.descricaoTipoOrdem || ''),
                    data_ms: fim ? Number(fim) : 0,
                    situacao: sit === TIPO_SITUACAO_ATIVA ? 'Ativa' : 'Encerrada',
                    valor_bloqueado: vb,
                    valor_bloquear: vbr,
                    valor_bloqueado_text: brl(vb),
                    valor_bloquear_text: brl(vbr),
                });
            } catch (e) { log('série ignorada:', e.message); }
        });
        log('válidas:', validas.length, 'de', bruto.length);
        return { series: validas, total_bruto: bruto.length };
    }

    // ── Decisão do fluxo ───────────────────────────────────────────────
    function decidirFluxo(series) {
        var totalBloqueado = series.reduce(function (a, s) { return a + Number(s.valor_bloqueado || 0); }, 0);
        var totalBloquear = series.reduce(function (a, s) { return a + Number(s.valor_bloquear || 0); }, 0);
        var maiorABloquear = series.length
            ? Math.max.apply(null, series.map(function (s) { return Number(s.valor_bloquear || 0); })) : 0;

        var tipo;
        if (totalBloqueado === 0) tipo = 'NEGATIVO';
        else if (totalBloqueado < LIMITE_IRRISORIO && totalBloquear >= LIMITE_BLOQUEIO) tipo = 'DESBLOQUEIO';
        else tipo = 'POSITIVO';

        var estrategia = null;
        if (tipo === 'POSITIVO') {
            var valorExecucao = maiorABloquear || VALOR_EXECUCAO_FALLBACK;
            estrategia = {
                tipo: totalBloqueado <= valorExecucao ? 'TRANSFERIR_TUDO' : 'TRANSFERIR_PARCIAL',
                valor_execucao: valorExecucao,
                total_bloqueado: totalBloqueado,
            };
        }
        return {
            tipo_fluxo: tipo,
            total_bloqueado: totalBloqueado,
            total_bloquear: totalBloquear,
            valor_a_bloquear: maiorABloquear,
            estrategia: estrategia,
        };
    }

    // ── Geração do relatório HTML ──────────────────────────────────────
    function gerarRelatorio(numero, series, decisao) {
        var h = [];
        h.push('<p ' + P_STYLE + '><strong>Relatório de séries executadas:</strong></p>');

        if (!series.length) {
            h.push('<p ' + P_STYLE + '>Nenhuma série ativa ou encerrada localizada nos últimos '
                + DIAS_CORTE + ' dias.</p>');
        }
        series.forEach(function (s) {
            var parteData = s.situacao === 'Ativa'
                ? ''
                : ' - Data da finalização: (' + esc(dataCurta(s.data_ms)) + ')';
            h.push('<p ' + P_STYLE + '>- (Série ' + esc(s.id_serie) + ')' + parteData
                + ' - Total bloqueado: (' + esc(s.valor_bloqueado_text) + ')</p>');
        });

        if (decisao.estrategia) {
            var e = decisao.estrategia;
            h.push('<p ' + P_STYLE + '><strong>Valor da execução:</strong> ' + esc(brl(e.valor_execucao)) + '</p>');
            h.push('<p ' + P_STYLE + '><strong>Total bloqueado nas séries:</strong> '
                + esc(brl(e.total_bloqueado))
                + (e.tipo === 'TRANSFERIR_PARCIAL' ? ' (excede o valor da execução)' : '') + '</p>');
        }

        if (decisao.tipo_fluxo === 'NEGATIVO') {
            h.push('<p ' + P_STYLE + '>Não houve bloqueios realizados.</p>');
        } else if (decisao.tipo_fluxo === 'DESBLOQUEIO') {
            h.push('<p ' + P_STYLE + '>Considerando as regras sobre bloqueios irrisórios, as quantias '
                + 'localizadas foram <strong>DESBLOQUEADAS</strong>, ação que será efetivada em até 48h úteis.</p>');
        } else if (decisao.estrategia && decisao.estrategia.tipo === 'TRANSFERIR_PARCIAL') {
            var excedente = decisao.total_bloqueado - decisao.estrategia.valor_execucao;
            h.push('<p ' + P_STYLE + '>Considerando os bloqueios realizados, as quantias localizadas foram '
                + '<strong>TRANSFERIDAS</strong> à conta judicial do processo e os valores excedentes ('
                + esc(brl(excedente)) + ') foram devidamente <strong>DESBLOQUEADOS</strong>, '
                + 'ações que serão efetivadas em até 48h úteis.</p>');
        } else {
            h.push('<p ' + P_STYLE + '>Considerando os bloqueios realizados, as quantias localizadas foram '
                + '<strong>TRANSFERIDAS</strong> à conta judicial do processo, ação que será efetivada em até 48h úteis.</p>');
        }

        h.push('<p ' + P_STYLE + '>Processo: ' + esc(numero) + ' — gerado em '
            + new Date().toLocaleString('pt-BR') + '.</p>');

        return h.join('');
    }

    // ── Clipboard HTML rico ────────────────────────────────────────────
    function copiarHtml(html) {
        var div = document.createElement('div');
        div.innerHTML = html;
        div.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0;pointer-events:none;';
        document.body.appendChild(div);
        var ok = false;
        try {
            var range = document.createRange();
            range.selectNodeContents(div);
            var sel = (document.getSelection && document.getSelection()) || window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            ok = document.execCommand('copy');
            sel.removeAllRanges();
        } catch (e) { log('copiar falhou:', e.message); }
        document.body.removeChild(div);
        return ok;
    }

    function notificar(msg, cor, duracao) {
        if (typeof window.showToast === 'function') {
            window.showToast(msg, cor || '#0a6b1f', duracao || 4000);
            return;
        }
        var d = document.createElement('div');
        d.style.cssText = 'position:fixed;top:20px;right:20px;z-index:2147483002;background:'
            + (cor || '#0a6b1f') + ';color:#fff;padding:10px 16px;border-radius:6px;'
            + 'font:bold 13px "Segoe UI",Arial,sans-serif;box-shadow:0 3px 10px rgba(0,0,0,.3)';
        d.textContent = msg;
        document.body.appendChild(d);
        setTimeout(function () { if (d.parentNode) d.remove(); }, duracao || 4000);
    }

    // ── Execução acionada pelo botão "Séries" no painel ────────────────
    async function consultarSeries() {
        var numero = numeroProcessoDaPagina();
        if (!numero) {
            notificar('Processo não detectado na página.', '#dc3545', 3500);
            return;
        }

        notificar('Consultando séries SISBAJUD...', '#1e88e5', 2000);

        try {
            var r = await lerSeries(numero);
            if (r.erro) {
                notificar(r.erro, '#dc3545', 5000);
                return;
            }

            var decisao = decidirFluxo(r.series);
            var relatorio = gerarRelatorio(numero, r.series, decisao);
            var ok = copiarHtml(relatorio);

            if (ok) {
                notificar(
                    'Séries (' + decisao.tipo_fluxo + ', ' + r.series.length
                    + '): relatório copiado para a área de transferência!',
                    '#0a6b1f',
                    4500
                );
            } else {
                notificar('Relatório gerado, mas não foi possível copiar para a área de transferência.', '#dc3545', 4500);
            }
        } catch (e) {
            log('ERRO', e && e.stack || e);
            notificar('Erro ao consultar séries: ' + (e && e.message || e), '#dc3545', 5000);
        }
    }

    // ── Coletor de token e ponte same-origin na aba do SISBAJUD ────────
    function coletarTokenSisbajud() {
        var ultimo = '';

        function ler() {
            var storages = [];
            try { if (typeof unsafeWindow !== 'undefined' && unsafeWindow.localStorage) storages.push(unsafeWindow.localStorage); } catch (e) { }
            try { if (window.localStorage) storages.push(window.localStorage); } catch (e) { }
            for (var i = 0; i < storages.length; i++) {
                try {
                    var t = limparToken(
                        storages[i].getItem('sisbajud-token')
                        || storages[i].getItem('LS.sisbajud-token')
                        || ''
                    );
                    if (t) return t;
                } catch (e) { }
            }
            return '';
        }

        function passo(forcar) {
            var t = ler();
            if (t && (forcar || t !== ultimo)) {
                ultimo = t;
                salvarToken(t);
                var exp = expDoJwt(t);
                log('token coletado' + (exp ? ' (expira ' + new Date(exp * 1000).toISOString() + ')' : ''));
            }
            return t;
        }

        log('aba SISBAJUD: coletor + ponte same-origin ativos');
        passo(true);
        setInterval(function () { passo(false); }, 5000);
        try { window.addEventListener('storage', function () { passo(false); }); } catch (e) { }
        try { document.addEventListener('visibilitychange', function () { if (!document.hidden) passo(false); }); } catch (e) { }
        try {
            if (typeof GM_addValueChangeListener === 'function') {
                GM_addValueChangeListener(CHAVE_TOKEN_REQ, function (_n, _o, req) {
                    var t = passo(true);
                    if (req && req.id && typeof GM_setValue === 'function') {
                        GM_setValue(CHAVE_TOKEN_RESP, { id: req.id, token: t || '', ts: Date.now() });
                    }
                });
                GM_addValueChangeListener(CHAVE_API_REQ, function (_n, _o, req) {
                    if (!req || !req.id || !req.url || typeof GM_setValue !== 'function') return;
                    var t = passo(true);
                    var caminho = String(req.url).replace(/^https?:\/\/[^/]+/, '');
                    var urlLocal = location.origin + caminho;
                    requisitarSameOrigin(urlLocal, t)
                        .then(function (r) {
                            GM_setValue(CHAVE_API_RESP, {
                                id: req.id,
                                status: r.status,
                                texto: r.texto,
                                ts: Date.now(),
                            });
                        })
                        .catch(function (e) {
                            GM_setValue(CHAVE_API_RESP, {
                                id: req.id,
                                status: 0,
                                texto: String((e && e.message) || e || ''),
                                ts: Date.now(),
                            });
                        });
                });
            }
        } catch (e) { }
    }

    if (ehHostSisbajud()) {
        coletarTokenSisbajud();
    }

    window.SisbSeries = {
        consultar: consultarSeries,
    };
})();
