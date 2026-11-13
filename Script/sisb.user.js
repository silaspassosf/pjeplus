// ==UserScript==
// @name         SISB - Leitura de ordens da Teimosinha via API
// @namespace    http://tampermonkey.net/
// @version      3.0.0
// @description  Na aba /detalhe, le as series da Teimosinha pela API v1/serie, monta o relatorio do fluxo e copia para a area de transferencia
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @match        https://sisbajud.pdpj.jus.br/*
// @match        https://sisbajud.cnj.jus.br/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      pje.trt2.jus.br
// @connect      sisbajud.pdpj.jus.br
// @run-at       document-idle
// ==/UserScript==

// Espelha SISB/api_series.py::ler_series_api + decidir_fluxo e
// SISB/processamento/relatorios_ordem.py::_gerar_relatorio_ordem.
//
// Roda no /detalhe (como o hcalc): o numero do processo ja esta na propria
// pagina e sai de `numeroProcessoDaPagina()` — a mesma funcao que o botao
// "Saldo" do painel do pjetools usa (Script/alvara/extracao_siscondj.js).
//
// A API do SISBAJUD e outro dominio: vai por GM_xmlhttpRequest (sem CORS).
//
// Cookie de sessao NAO resolve, ao contrario do Alvará/SISCONDJ: la o host
// (alvaraeletronico.trt2.jus.br) e SAME-SITE com o PJe (trt2.jus.br) e o cookie
// httpOnly viaja; aqui e CROSS-SITE (pdpj.jus.br x trt2.jus.br), o navegador
// nao manda o cookie e a API responde 401. A API exige o Bearer.
//
// O access_token vive no localStorage do dominio SISBAJUD, fora do alcance
// desta origem. Por isso o script tambem roda la (@match acima): na aba do
// SISBAJUD ele so coleta o token para o GM_setValue; aqui usa o valor coletado.
// O campo de token fica como sobreposicao manual.

(function () {
    'use strict';

    var TAG = '[sisb]';
    var CLS = 'sisb-api';
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

    var MESES = ['JANEIRO', 'FEVEREIRO', 'MARCO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO',
        'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];

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

    function dataLonga(ms) {
        var d = new Date(Number(ms));
        return d.getDate() + ' DE ' + MESES[d.getMonth()] + ' DE ' + d.getFullYear();
    }

    // =========================================================================
    // =========================================================================
    // Numero do processo: ja esta na propria pagina. Mesma ordem de
    // Script/alvara/extracao_siscondj.js::numeroProcessoDaPagina, usada pelo
    // botao "Saldo" do painel do pjetools: titulo, .texto-numero-processo,
    // campo #numeroProcesso e, por ultimo, a URL.
    // =========================================================================
    var RE_CNJ = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;

    function numeroProcessoDaPagina() {
        var doTitulo = String(document.title || "").match(RE_CNJ);
        if (doTitulo) return doTitulo[0];

        var el = document.querySelector(".texto-numero-processo");
        if (el) {
            var doEl = String(el.textContent || "").match(RE_CNJ);
            if (doEl) return doEl[0];
        }

        var campo = document.querySelector("#numeroProcesso");
        if (campo && campo.value && RE_CNJ.test(campo.value)) {
            return String(campo.value).match(RE_CNJ)[0];
        }

        var doHref = String(location.href || "").match(RE_CNJ);
        if (doHref) return doHref[0];

        return "";
    }

    // =========================================================================
    // Token (guardado via GM; origem: localStorage sisbajud-token)
    // =========================================================================
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
            b64 += '='.repeat((4 - (b64.length % 4)) % 4);
            return Number(JSON.parse(decodeURIComponent(escape(atob(b64)))).exp || 0);
        } catch (e) { return 0; }
    }

    // =========================================================================
    // Requisicao cross-origin (GM_xmlhttpRequest; fetch como reserva)
    // =========================================================================
    // Sem token a requisicao vai so com o cookie da sessao do SISBAJUD
    // (GM_xmlhttpRequest envia os cookies do dominio alvo).
    function requisitar(url, token) {
        var headers = { 'Accept': 'application/json' };
        if (token) headers['Authorization'] = 'Bearer ' + token;
        return new Promise(function (resolve) {
            try {
                if (typeof GM_xmlhttpRequest === 'function') {
                    GM_xmlhttpRequest({
                        method: 'GET', url: url, headers: headers, timeout: 30000,
                        onload: function (r) { resolve({ status: r.status, texto: r.responseText || '' }); },
                        onerror: function () { resolve({ status: 0, texto: '' }); },
                        ontimeout: function () { resolve({ status: -1, texto: '' }); },
                    });
                    return;
                }
            } catch (e) { }
            fetch(url, { headers: headers })
                .then(function (r) { return r.text().then(function (t) { resolve({ status: r.status, texto: t }); }); })
                .catch(function () { resolve({ status: 0, texto: '' }); });
        });
    }

    // =========================================================================
    // API
    // =========================================================================
    async function lerSeries(numero) {
        var token = lerToken().trim();
        if (token) {
            var exp = expDoJwt(token);
            if (exp && exp * 1000 < Date.now()) {
                log('ATENCAO: token expirado em', new Date(exp * 1000).toISOString());
            }
        }

        var url = URL_API + '?codProcesso=' + digitos(numero);

        // Bearer primeiro: cookie nao cruza site (ver cabecalho). Sem token a
        // chamada vai so pela sessao, para o 401 virar orientacao util.
        var resp;
        if (token) {
            resp = await requisitar(url, token);
            log('HTTP', resp.status, 'v1/serie (bearer)');
        } else {
            resp = await requisitar(url, '');
            log('HTTP', resp.status, 'v1/serie (sessao)');
        }

        if (resp.status === 401 || resp.status === 403) {
            return {
                erro: 'API recusou (HTTP ' + resp.status + ').'
                    + (token
                        ? ' Token recusado/vencido — abra uma aba do SISBAJUD para recoletar.'
                        : ' Abra (ou atualize) uma aba do SISBAJUD logada: o token é coletado de lá.'),
            };
        }
        if (resp.status !== 200) {
            return { erro: 'API devolveu HTTP ' + resp.status + (resp.status <= 0 ? ' (rede/CORS)' : '') + '.' };
        }
        var bruto;
        try { bruto = JSON.parse(resp.texto); } catch (e) {
            return { erro: 'Corpo nao-JSON da API: ' + String(resp.texto).slice(0, 120) };
        }
        if (!Array.isArray(bruto)) {
            return { erro: 'Corpo inesperado da API (' + typeof bruto + ').' };
        }
        log('series recebidas:', bruto.length);

        var limite = new Date();
        limite.setHours(0, 0, 0, 0);
        limite.setDate(limite.getDate() - DIAS_CORTE);

        // Filtro identico a ler_series_api: ativa (1) ou encerrada (2), com dataLimite >= limite.
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
            } catch (e) { log('serie ignorada:', e.message); }
        });
        log('validas:', validas.length, 'de', bruto.length);
        return { series: validas, total_bruto: bruto.length };
    }

    // =========================================================================
    // Decisao (SISB/api_series.py::decidir_fluxo)
    // =========================================================================
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

    // =========================================================================
    // Relatorio (SISB/processamento/relatorios_ordem.py)
    // =========================================================================
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
            // Excedente: o que passou do valor da execução é devolvido.
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

    // =========================================================================
    // Clipboard (mesmo caminho de Script/modules/sisbajud/core.js)
    // =========================================================================
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

    // =========================================================================
    // UI
    // =========================================================================
    var painel = null;

    function css() {
        if (document.getElementById(CLS + '-style')) return;
        var s = document.createElement('style');
        s.id = CLS + '-style';
        s.textContent = [
            '#btn-sisb-api{position:fixed;bottom:20px;right:20px;z-index:2147483000;background:#0d4f8b;color:#fff;border:none;border-radius:6px;padding:10px 16px;font-size:13px;font-weight:bold;cursor:pointer;box-shadow:0 3px 6px rgba(0,0,0,.35)}',
            '#btn-sisb-api:hover{background:#0a3c69}',
            '#sisb-api-panel{position:fixed;bottom:70px;right:20px;z-index:2147483001;width:720px;max-width:96vw;max-height:80vh;overflow:auto;background:#fff;color:#111;border:1px solid #b0b0b0;border-radius:8px;box-shadow:0 6px 22px rgba(0,0,0,.35);font:12px/1.45 "Segoe UI",Arial,sans-serif}',
            '#sisb-api-panel .sb-cab{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#0d4f8b;color:#fff;border-radius:8px 8px 0 0;font-weight:bold;font-size:13px;position:sticky;top:0;z-index:1}',
            '#sisb-api-panel .sb-cab button{background:none;border:none;color:#fff;font-size:16px;cursor:pointer}',
            '#sisb-api-panel .sb-body{padding:10px 12px}',
            '#sisb-api-panel .sb-linha{display:flex;gap:6px;margin-bottom:6px;align-items:center}',
            '#sisb-api-panel input{flex:1;padding:6px 8px;border:1px solid #bbb;border-radius:4px;font-size:12px;min-width:0}',
            '#sisb-api-panel label{font-weight:bold;white-space:nowrap}',
            '#sisb-api-panel .sb-btn{background:#0d4f8b;color:#fff;border:none;border-radius:4px;padding:6px 12px;font-size:12px;font-weight:bold;cursor:pointer}',
            '#sisb-api-panel .sb-btn:disabled{opacity:.55;cursor:default}',
            '#sisb-api-panel .sb-sec{background:#0a6b1f;color:#fff}',
            '#sisb-api-panel table{width:100%;border-collapse:collapse;margin-top:6px}',
            '#sisb-api-panel th,#sisb-api-panel td{border:1px solid #ddd;padding:4px 6px;font-size:11px;text-align:left}',
            '#sisb-api-panel th{background:#f3f3f3}',
            '#sisb-api-panel .sb-fluxo{font-weight:bold;font-size:14px;margin:8px 0}',
            '#sisb-api-panel .sb-neg{color:#a11}',
            '#sisb-api-panel .sb-pos{color:#0a6b1f}',
            '#sisb-api-panel .sb-des{color:#b0720a}',
            '#sisb-api-panel .sb-erro{color:#a11;white-space:pre-wrap;font-family:Consolas,monospace;font-size:11px}',
            '#sisb-api-panel .sb-aviso{color:#b0720a}',
            '#sisb-api-panel .sb-rel{margin-top:10px;border-top:1px solid #ddd;padding-top:8px}',
            '#sisb-api-panel .sb-rel-txt{margin-top:4px;color:#333}',
            '#sisb-api-panel .sb-rel-txt p{margin:4px 0;font-size:12px;text-indent:0;text-align:left}',
            '#sisb-api-panel small{color:#666}',
            '.sb-toast{position:fixed;top:20px;right:20px;z-index:2147483002;background:#0a6b1f;color:#fff;padding:10px 16px;border-radius:6px;font-weight:bold;font-size:13px}',
        ].join('\n');
        document.head.appendChild(s);
    }

    function toast(msg, cor) {
        var d = document.createElement('div');
        d.className = 'sb-toast';
        if (cor) d.style.background = cor;
        d.textContent = msg;
        document.body.appendChild(d);
        setTimeout(function () { if (d.parentNode) d.remove(); }, 3000);
    }

    function render(html) {
        if (!painel) return;
        painel.querySelector('.sb-body').innerHTML = html;
    }

    function fechar() { if (painel) { painel.remove(); painel = null; } }

    function abrirPainel() {
        if (painel && document.body.contains(painel)) return painel;
        painel = document.createElement('div');
        painel.id = 'sisb-api-panel';
        painel.innerHTML = '<div class="sb-cab"><span>Teimosinha via API</span>'
            + '<button type="button" data-close>×</button></div><div class="sb-body"></div>';
        painel.querySelector('[data-close]').addEventListener('click', fechar);
        document.body.appendChild(painel);
        return painel;
    }

    function avisoToken() {
        var t = lerToken().trim();
        if (!t) return '<small>Sem token. Abra uma aba do SISBAJUD logada: ele é coletado de lá.</small>';
        var exp = expDoJwt(t);
        if (!exp) return '<small>Token coletado (sem exp legível).</small>';
        var venc = exp * 1000 < Date.now();
        return '<small' + (venc ? ' class="sb-aviso"' : '') + '>Token '
            + (venc ? 'EXPIRADO' : 'guardado, válido até ' + new Date(exp * 1000).toLocaleString('pt-BR'))
            + ' .</small>';
    }

    // Clique no botao = consulta direta, sem passo intermediario.
    async function formulario() {
        if (painel && document.body.contains(painel)) { fechar(); return; }
        abrirPainel();

        var numero = numeroProcessoDaPagina();
        render('');

        var saida = painel.querySelector('.sb-body');
        if (!numero) {
            // Sem numero na pagina: unica situacao com intervencao manual.
            render('<div class="sb-aviso">Processo não detectado na página. Informe o número:</div>'
                + '<div class="sb-linha"><input id="sisb-numero" type="text" placeholder="número CNJ">'
                + '<button id="sisb-consultar" class="sb-btn" type="button">Consultar</button></div>');
            var campo = painel.querySelector('#sisb-numero');
            painel.querySelector('#sisb-consultar').addEventListener('click', function () {
                var n = (campo.value || '').trim();
                if (digitos(n).length < 15) {
                    saida.insertAdjacentHTML('beforeend',
                        '<div class="sb-erro">Número inválido (precisa de 15+ dígitos).</div>');
                    return;
                }
                rodar(n, saida);
            });
            return;
        }

        log('numero da pagina:', numero);
        await rodar(numero, saida);
    }

    async function rodar(numero, saida) {
        saida.innerHTML = '<div class="sb-aviso">Consultando a API…</div>';
        try {
            await executar(numero, saida);
        } catch (e) {
            log('ERRO', e && e.stack || e);
            saida.innerHTML = '<div class="sb-erro">' + esc(e && e.stack || e) + '</div>';
        }
    }

    async function executar(numero, saida) {
        log('consulta', numero);
        var r = await lerSeries(numero);
        if (r.erro) {
            saida.innerHTML = '<div class="sb-erro">' + esc(r.erro) + '</div>'
                + '<div id="sisb-token-info">' + avisoToken() + '</div>';
            return;
        }

        var series = r.series;
        var decisao = decidirFluxo(series);
        log('decisao:', decisao.tipo_fluxo, 'bloqueado', decisao.total_bloqueado);

        var cls = { NEGATIVO: 'sb-neg', POSITIVO: 'sb-pos', DESBLOQUEIO: 'sb-des' }[decisao.tipo_fluxo] || '';
        var linhas = series.map(function (s) {
            return '<tr><td>' + esc(s.id_serie) + '</td><td>' + esc(s.protocolo || '—') + '</td>'
                + '<td>' + esc(s.situacao || '—') + '</td>'
                + '<td>' + esc(s.acao || '—') + '</td><td>'
                + esc(s.situacao === 'Ativa' ? '—' : dataCurta(s.data_ms)) + '</td>'
                + '<td>' + esc(s.valor_bloqueado_text) + '</td><td>' + esc(s.valor_bloquear_text) + '</td></tr>';
        }).join('');

        var relatorio = gerarRelatorio(numero, series, decisao);

        saida.innerHTML = '<div class="sb-fluxo ' + cls + '">Fluxo: ' + esc(decisao.tipo_fluxo) + '</div>'
            + '<div><b>' + series.length + '</b> série(s) válida(s) de <b>' + r.total_bruto + '</b> · '
            + 'bloqueado ' + esc(brl(decisao.total_bloqueado)) + ' · a bloquear '
            + esc(brl(decisao.valor_a_bloquear))
            + (decisao.estrategia ? ' · estratégia ' + esc(decisao.estrategia.tipo) : '') + '</div>'
            + (series.length ? '<table><thead><tr><th>Série</th><th>Protocolo</th><th>Situação</th><th>Ação</th>'
                + '<th>Finalização</th><th>Bloqueado</th><th>A bloquear</th></tr></thead><tbody>'
                + linhas + '</tbody></table>' : '')
            + '<div class="sb-linha" style="margin-top:8px">'
            + '<button class="sb-btn sb-sec" type="button" id="sisb-copiar">'
            + 'Copiar relatório novamente</button></div>'
            + '<div class="sb-rel"><b>Relatório gerado e copiado:</b>'
            + '<div class="sb-rel-txt">' + relatorio + '</div></div>';

        var ok = copiarHtml(relatorio);
        toast(ok ? 'Relatório copiado para a área de transferência'
            : 'Não foi possível copiar (use o botão)', ok ? null : '#a11');

        painel.querySelector('#sisb-copiar').addEventListener('click', function () {
            var copiou = copiarHtml(relatorio);
            toast(copiou ? 'Relatório copiado' : 'Não foi possível copiar', copiou ? null : '#a11');
        });
    }

    // =========================================================================
    // Coletor: roda so na aba do SISBAJUD. Guarda o access_token no GM para o
    // lado do PJe (origens diferentes nao compartilham localStorage).
    // =========================================================================
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

    function init() {
        try {
            css();
            if (document.getElementById('btn-sisb-api')) { log('botao ja existe'); return; }
            var btn = document.createElement('button');
            btn.id = 'btn-sisb-api';
            btn.type = 'button';
            btn.textContent = '◌ Teimosinha (API)';
            btn.addEventListener('click', formulario);
            document.body.appendChild(btn);
            log('botao injetado');
        } catch (e) { log('ERRO ao injetar', e && e.stack || e); }
    }

    if (document.documentElement.getAttribute('data-' + CLS + '-boot')) { log('ja iniciado'); return; }
    document.documentElement.setAttribute('data-' + CLS + '-boot', '1');
    log('iniciando v3');

    if (/^sisbajud\.(pdpj|cnj)\.jus\.br$/.test(location.hostname)) {
        log('aba SISBAJUD: coletando token');
        coletarTokenSisbajud();
        return;
    }

    if (document.body) init();
    else document.addEventListener('DOMContentLoaded', init, { once: true });
})();