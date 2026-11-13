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

    // ── Token (coletado na aba do SISBAJUD via GM_setValue) ─────────────
    function lerToken() {
        try {
            if (typeof GM_getValue === 'function') return GM_getValue(CHAVE_TOKEN, '') || '';
        } catch (e) { }
        try { return localStorage.getItem(CHAVE_TOKEN) || ''; } catch (e) { return ''; }
    }

    function salvarToken(t) {
        try {
            if (typeof GM_setValue === 'function') { GM_setValue(CHAVE_TOKEN, t); return; }
        } catch (e) { }
        try { localStorage.setItem(CHAVE_TOKEN, t); } catch (e) { }
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
    function requisitar(url, token) {
        return new Promise(function (resolve, reject) {
            var headers = { Accept: 'application/json' };
            if (token) headers.Authorization = 'Bearer ' + token;
            if (typeof GM_xmlhttpRequest === 'function') {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: url,
                    headers: headers,
                    timeout: 20000,
                    onload: function (r) { resolve({ status: r.status, texto: r.responseText || '' }); },
                    onerror: function () { reject(new Error('Falha de rede ao consultar API do SISBAJUD.')); },
                    ontimeout: function () { reject(new Error('Timeout (20s) na API do SISBAJUD.')); },
                });
                return;
            }
            fetch(url, { headers: headers, credentials: 'include' })
                .then(function (r) { return r.text().then(function (t) { resolve({ status: r.status, texto: t }); }); })
                .catch(reject);
        });
    }

    async function lerSeries(numero) {
        var dig = digitos(numero);
        if (dig.length < 15) return { erro: 'Número inválido: ' + numero };

        var token = lerToken().trim();
        if (token) {
            var exp = expDoJwt(token);
            if (exp && exp * 1000 < Date.now()) {
                log('ATENÇÃO: token expirado em', new Date(exp * 1000).toISOString());
            }
        }

        var url = URL_API + '?codProcesso=' + encodeURIComponent(dig);
        var resp = token ? await requisitar(url, token) : await requisitar(url, '');
        log('HTTP', resp.status, 'v1/serie', token ? '(bearer)' : '(sessao)');

        if (resp.status === 401 || resp.status === 403) {
            return {
                erro: 'API SISBAJUD recusou (HTTP ' + resp.status + ').'
                    + (token
                        ? ' Token recusado/vencido — abra uma aba do SISBAJUD para recoletar.'
                        : ' Abra (ou atualize) uma aba do SISBAJUD logada para coletar o token.'),
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

    // ── Coletor de token na aba do SISBAJUD ────────────────────────────
    function coletarTokenSisbajud() {
        var ultimo = '';
        var tentativas = 0;

        function ler() {
            try {
                return localStorage.getItem('sisbajud-token')
                    || localStorage.getItem('LS.sisbajud-token') || '';
            } catch (e) { return ''; }
        }

        function passo() {
            var t = ler();
            if (t && t !== ultimo) {
                ultimo = t;
                salvarToken(t);
                var exp = expDoJwt(t);
                log('token coletado' + (exp ? ' (expira ' + new Date(exp * 1000).toISOString() + ')' : ''));
            }
            if (++tentativas < 30) setTimeout(passo, 2000);
        }

        passo();
        try { window.addEventListener('storage', passo); } catch (e) { }
    }

    if (/^sisbajud\.(pdpj|cnj)\.jus\.br$/.test(location.hostname)) {
        coletarTokenSisbajud();
    }

    window.SisbSeries = {
        consultar: consultarSeries,
    };
})();
