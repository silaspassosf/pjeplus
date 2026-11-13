// ==UserScript==
// @name         SISB - Leitura de ordens da Teimosinha via API
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Le as series da Teimosinha pela API v1/serie, monta o relatorio do fluxo e copia para a area de transferencia
// @author       Silas
// @match        https://sisbajud.pdpj.jus.br/*
// @match        https://sisbajud.cnj.jus.br/*
// @connect      sisbajud.pdpj.jus.br
// @run-at       document-idle
// @grant        none
// ==/UserScript==

// Espelha SISB/api_series.py::ler_series_api + decidir_fluxo e
// SISB/processamento/relatorios_ordem.py::_gerar_relatorio_ordem.
// O token vem do localStorage (mesmo par de chaves de
// SISB/core.py::salvar_tokens_sisbajud) — nao depende do arquivo
// ~/.pjeplus/sisbajud_tokens.json nem de driver.

(function () {
    'use strict';

    var TAG = '[sisb]';
    var CLS = 'sisb-api';
    var URL_API = 'https://sisbajud.pdpj.jus.br/v1/serie';
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

    // Comparacao sem acento: o rotulo varia com encoding do PJe.
    function semAcento(v) {
        return String(v == null ? '' : v).normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '').toUpperCase();
    }

    function brl(v) {
        return 'R$ ' + Number(v || 0).toFixed(2)
            .replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }

    function dataCurta(ms) {
        var d = new Date(Number(ms));
        return ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2) + '/' + d.getFullYear();
    }

    function dataLonga(ms) {
        var d = new Date(Number(ms));
        return d.getDate() + ' DE ' + MESES[d.getMonth()] + ' DE ' + d.getFullYear();
    }

    // =========================================================================
    // Token (mesmas chaves de SISB/core.py)
    // =========================================================================
    function lerToken() {
        try {
            return localStorage.getItem('sisbajud-token')
                || localStorage.getItem('LS.sisbajud-token') || '';
        } catch (e) { return ''; }
    }

    function expDoJwt(token) {
        try {
            var partes = String(token).split('.');
            if (partes.length < 2) return 0;
            var b64 = partes[1].replace(/-/g, '+').replace(/_/g, '/');
            b64 += '='.repeat((4 - (b64.length % 4)) % 4);
            var json = decodeURIComponent(escape(atob(b64)));
            return Number(JSON.parse(json).exp || 0);
        } catch (e) { return 0; }
    }

    // =========================================================================
    // Numero do processo (DOM, igual ao bookmarklet end.js; campo editavel)
    // =========================================================================
    function numeroDoDom() {
        try {
            var labels = document.querySelectorAll('div.sisbajud-label');
            for (var i = 0; i < labels.length; i++) {
                if (semAcento(labels[i].textContent).indexOf('NUMERO DO PROCESSO') < 0) continue;
                var v = labels[i].nextElementSibling;
                while (v && v.nodeType === 8) v = v.nextElementSibling;
                if (v) return (v.textContent || '').trim();
            }
        } catch (e) { }
        var m = location.href.match(/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/);
        return m ? m[1] : '';
    }

    // =========================================================================
    // API
    // =========================================================================
    async function lerSeries(numero) {
        var token = lerToken();
        if (!token) {
            return { erro: 'Token nao encontrado no localStorage (sisbajud-token). Faca login no SISBAJUD nesta aba.' };
        }
        var exp = expDoJwt(token);
        if (exp && exp * 1000 < Date.now()) {
            log('ATENCAO: token expirado em', new Date(exp * 1000).toISOString());
        }

        var url = URL_API + '?codProcesso=' + digitos(numero);
        var resp;
        try {
            resp = await fetch(url, {
                headers: { 'Accept': 'application/json', 'Authorization': 'Bearer ' + token },
                credentials: 'include',
            });
        } catch (e) {
            return { erro: 'Falha de rede/CORS ao chamar a API: ' + e.message };
        }
        log('HTTP', resp.status, 'v1/serie');

        if (resp.status === 401 || resp.status === 403) {
            return { erro: 'API recusou o token (HTTP ' + resp.status + '). Renove a sessao do SISBAJUD.' };
        }
        if (resp.status !== 200) {
            return { erro: 'API devolveu HTTP ' + resp.status + '.' };
        }
        var texto = await resp.text();
        var bruto;
        try { bruto = JSON.parse(texto); } catch (e) {
            return { erro: 'Corpo nao-JSON da API: ' + texto.slice(0, 120) };
        }
        if (!Array.isArray(bruto)) {
            return { erro: 'Corpo inesperado da API (' + typeof bruto + ').' };
        }
        log('series recebidas:', bruto.length);

        var limite = new Date();
        limite.setHours(0, 0, 0, 0);
        limite.setDate(limite.getDate() - DIAS_CORTE);

        // Filtro identico a ler_series_api: encerrada + dataLimite dentro do prazo.
        var validas = [];
        bruto.forEach(function (s) {
            try {
                if (s.tipoSituacaoSerie !== TIPO_SITUACAO_ENCERRADA) return;
                var fim = s.dataLimite;
                if (!fim) return;
                if (new Date(Number(fim)) < limite) return;
                var ordem = s.ordemOriginal || {};
                var vb = Number(s.valorBloqueioRealizado || 0);
                var vbr = Number(s.valorBloqueioTotal || 0);
                validas.push({
                    id_serie: String(s.codSerie),
                    protocolo: String(ordem.protocolo || ''),
                    acao: String(ordem.descricaoTipoOrdem || ''),
                    data_ms: Number(fim),
                    data_conclusao_text: dataLonga(fim),
                    situacao: 'Encerrada',
                    valor_bloqueado: vb,
                    valor_bloquear: vbr,
                    valor_bloqueado_text: brl(vb),
                    valor_bloquear_text: brl(vbr),
                });
            } catch (e) { log('serie ignorada:', e.message); }
        });
        log('validas:', validas.length, 'de', bruto.length);
        return { series: validas, total_bruto: bruto.length, limite: limite };
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
        h.push('<p ' + P_STYLE + '><strong>Relatorio de series executadas:</strong></p>');

        if (!series.length) {
            h.push('<p ' + P_STYLE + '>Nenhuma serie encerrada localizada nos ultimos '
                + DIAS_CORTE + ' dias.</p>');
        }
        series.forEach(function (s) {
            h.push('<p ' + P_STYLE + '>- (Serie ' + esc(s.id_serie) + ') - Data da finalizacao: ('
                + esc(dataCurta(s.data_ms)) + ') - Total bloqueado: (' + esc(s.valor_bloqueado_text) + ')</p>');
        });

        if (decisao.estrategia) {
            var e = decisao.estrategia;
            h.push('<p ' + P_STYLE + '><strong>Valor da execucao:</strong> ' + esc(brl(e.valor_execucao)) + '</p>');
            h.push('<p ' + P_STYLE + '><strong>Total bloqueado nas series:</strong> '
                + esc(brl(e.total_bloqueado))
                + (e.tipo === 'TRANSFERIR_PARCIAL' ? ' (excede valor da execucao)' : '') + '</p>');
        }

        if (decisao.tipo_fluxo === 'NEGATIVO') {
            h.push('<p ' + P_STYLE + '>Nao houve bloqueios realizados.</p>');
        } else if (decisao.tipo_fluxo === 'DESBLOQUEIO') {
            h.push('<p ' + P_STYLE + '>Considerando as regras sobre bloqueios irrisorios, as quantias '
                + 'localizadas foram <strong>DESBLOQUEADAS</strong>, acao que sera efetivada em ate 48h uteis.</p>');
        } else {
            h.push('<p ' + P_STYLE + '>Considerando os bloqueios realizados, as quantias localizadas foram '
                + '<strong>TRANSFERIDAS</strong> a conta judicial do processo, acao que sera efetivada em ate 48h uteis.</p>');
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
            var sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            ok = document.execCommand('copy');
            sel.removeAllRanges();
        } catch (e) {
            log('copiar falhou:', e.message);
        }
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
            '#sisb-api-panel{position:fixed;bottom:70px;right:20px;z-index:2147483001;width:700px;max-width:96vw;max-height:80vh;overflow:auto;background:#fff;color:#111;border:1px solid #b0b0b0;border-radius:8px;box-shadow:0 6px 22px rgba(0,0,0,.35);font:12px/1.45 "Segoe UI",Arial,sans-serif}',
            '#sisb-api-panel .sb-cab{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#0d4f8b;color:#fff;border-radius:8px 8px 0 0;font-weight:bold;font-size:13px;position:sticky;top:0;z-index:1}',
            '#sisb-api-panel .sb-cab button{background:none;border:none;color:#fff;font-size:16px;cursor:pointer}',
            '#sisb-api-panel .sb-body{padding:10px 12px}',
            '#sisb-api-panel .sb-linha{display:flex;gap:6px;margin-bottom:8px}',
            '#sisb-api-panel input{flex:1;padding:6px 8px;border:1px solid #bbb;border-radius:4px;font-size:12px}',
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

    function fechar() { if (painel) { painel.remove(); painel = null; } }

    function formulario() {
        var numero = numeroDoDom();
        abrirPainel();
        render('<div class="sb-linha">'
            + '<input id="sisb-numero" type="text" placeholder="Numero do processo (CNJ)" value="'
            + esc(numero) + '">'
            + '<button id="sisb-consultar" class="sb-btn" type="button">Consultar via API</button></div>'
            + '<div id="sisb-saida"><div class="sb-aviso">Token lido do localStorage desta aba; '
            + 'consumo em ' + URL_API + '</div></div>');

        painel.querySelector('#sisb-consultar').addEventListener('click', async function () {
            var campo = painel.querySelector('#sisb-numero');
            var num = (campo.value || '').trim();
            var saida = painel.querySelector('#sisb-saida');
            if (digitos(num).length < 15) {
                saida.innerHTML = '<div class="sb-erro">Numero invalido (precisa de 15+ digitos).</div>';
                return;
            }
            var btn = painel.querySelector('#sisb-consultar');
            btn.disabled = true;
            saida.innerHTML = '<div class="sb-aviso">Consultando a API…</div>';
            try {
                await executar(num, saida);
            } catch (e) {
                log('ERRO', e && e.stack || e);
                saida.innerHTML = '<div class="sb-erro">' + esc(e && e.stack || e) + '</div>';
            } finally {
                btn.disabled = false;
            }
        });
    }

    async function executar(numero, saida) {
        log('consulta', numero);
        var r = await lerSeries(numero);
        if (r.erro) {
            saida.innerHTML = '<div class="sb-erro">' + esc(r.erro) + '</div>';
            return;
        }

        var series = r.series;
        var decisao = decidirFluxo(series);
        log('decisao:', decisao.tipo_fluxo, 'bloqueado', decisao.total_bloqueado,
            'a bloquear', decisao.total_bloquear);

        var cls = { NEGATIVO: 'sb-neg', POSITIVO: 'sb-pos', DESBLOQUEIO: 'sb-des' }[decisao.tipo_fluxo] || '';
        var linhas = series.map(function (s) {
            return '<tr><td>' + esc(s.id_serie) + '</td><td>' + esc(s.protocolo || '—') + '</td>'
                + '<td>' + esc(s.acao || '—') + '</td><td>' + esc(dataCurta(s.data_ms)) + '</td>'
                + '<td>' + esc(s.valor_bloqueado_text) + '</td><td>' + esc(s.valor_bloquear_text) + '</td></tr>';
        }).join('');

        var html = '<div class="sb-fluxo ' + cls + '">Fluxo: ' + esc(decisao.tipo_fluxo) + '</div>'
            + '<div><b>' + series.length + '</b> serie(s) valida(s) de <b>' + r.total_bruto + '</b> · '
            + 'bloqueado ' + esc(brl(decisao.total_bloqueado)) + ' · a bloquear '
            + esc(brl(decisao.valor_a_bloquear))
            + (decisao.estrategia ? ' · estrategia ' + esc(decisao.estrategia.tipo) : '') + '</div>'
            + (series.length ? '<table><thead><tr><th>Serie</th><th>Protocolo</th><th>Acao</th>'
                + '<th>Finalizacao</th><th>Bloqueado</th><th>A bloquear</th></tr></thead><tbody>'
                + linhas + '</tbody></table>' : '')
            + '<div class="sb-linha" style="margin-top:8px">'
            + '<button class="sb-btn sb-sec" type="button" id="sisb-copiar">Copiar relatorio</button></div>';

        saida.innerHTML = html;

        var relatorio = gerarRelatorio(numero, series, decisao);
        var ok = copiarHtml(relatorio);
        toast(ok ? 'Relatorio copiado para a area de transferencia'
            : 'Nao foi possivel copiar (use o botao)', ok ? null : '#a11');

        painel.querySelector('#sisb-copiar').addEventListener('click', function () {
            toast(copiarHtml(relatorio) ? 'Relatorio copiado'
                : 'Nao foi possivel copiar', '#a11');
        });
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
    log('iniciando');

    if (document.body) init();
    else document.addEventListener('DOMContentLoaded', init, { once: true });
})();
