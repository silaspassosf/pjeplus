// ==UserScript==
// @name         Chip Advogado Impedido - Relatório OAB (DOM x POST)
// @namespace    http://tampermonkey.net/
// @version      1.2.0
// @description  Na aba /detalhe, compara as variantes de /partes (DOM) com a OAB live (POST validacaooab) e indica a solucao conforme f.py/adv.py
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @connect      pje.trt2.jus.br
// @run-at       document-idle
// @grant        none
// ==/UserScript==

// Referencias:
//  * f.py::teste_advogados_oab  -> fluxo e regras de escolha da inscricao
//  * Fix/variaveis.py (session_from_driver) -> headers que a API aceita:
//    Accept json, Content-Type json, X-Grau-Instancia e X-XSRF-TOKEN do cookie
//    (sem o token o POST /validacaooab devolve 403)

(function () {
    'use strict';

    if (window.self !== window.top) return;

    var TAG = '[chipadv]';
    var CLS = 'chipadv-oab';
    var ORIGIN = location.origin;

    var CODIGOS = {
        1: 'Regular', 2: 'Cancelado', 3: 'Falecido', 4: 'Suspenso',
        5: 'Licenciado', 6: 'Excluido', 7: 'Em processo de inscricao',
    };

    function log() {
        try {
            console.log.apply(console, [TAG].concat([].slice.call(arguments)));
        } catch (e) { /* ignore */ }
    }

    function getProcessIdFromUrl() {
        var m = location.pathname.match(/\/processo\/(\d+)/);
        return m ? m[1] : null;
    }

    function grau() {
        return /\/pje2g\//.test(location.pathname) ? '2' : '1';
    }

    function cookie(nome) {
        var alvo = nome.toLowerCase() + '=';
        var c = (document.cookie || '').split(';').map(function (x) { return x.trim(); })
            .find(function (x) { return x.toLowerCase().indexOf(alvo) === 0; });
        return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
    }

    function xsrf() {
        var nomes = ['XSRF-TOKEN', 'xsrf-token', 'csrf-token', 'X-CSRF-TOKEN'];
        for (var i = 0; i < nomes.length; i++) {
            var v = cookie(nomes[i]);
            if (v) return v;
        }
        return '';
    }

    function norm(v) {
        return String(v == null ? '' : v)
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().trim();
    }

    function codigo(d) {
        return (d && d.codigoSituacao !== undefined && d.codigoSituacao !== null)
            ? Number(d.codigoSituacao) : null;
    }

    function esc(str) {
        return String(str == null ? '' : str).replace(/&/g, '&amp;')
            .replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // =========================================================================
    // Transporte
    // =========================================================================
    function headersGet() {
        var h = { 'Accept': 'application/json, text/plain, */*', 'X-Grau-Instancia': grau() };
        var t = xsrf();
        if (t) h['X-XSRF-TOKEN'] = t;
        return h;
    }

    function headersPost() {
        var h = headersGet();
        h['Content-Type'] = 'application/json';
        return h;
    }

    async function req(url, opts) {
        var ctrl = new AbortController();
        var timer = setTimeout(function () { ctrl.abort(); }, 120000);
        try {
            var r = await fetch(url, Object.assign({ credentials: 'include', signal: ctrl.signal }, opts || {}));
            var t = await r.text();
            var b = t;
            try { b = JSON.parse(t); } catch (e) { /* nao e json */ }
            log(r.status, (opts && opts.method || 'GET'), url.replace(ORIGIN, ''));
            return { status: r.status, body: b };
        } catch (e) {
            log('FALHA', (opts && opts.method || 'GET'), url.replace(ORIGIN, ''), String(e));
            return { status: 0, erro: String(e) };
        } finally {
            clearTimeout(timer);
        }
    }

    var getJson = function (u) { return req(u, { headers: headersGet() }); };
    var postJson = function (u, body) {
        return req(u, { method: 'POST', headers: headersPost(), body: JSON.stringify(body || {}) });
    };

    // =========================================================================
    // Coleta
    // =========================================================================
    function polos(resp) {
        var b = (resp && resp.body) || {};
        if (b && b.resultado && typeof b.resultado === 'object' && !Array.isArray(b.resultado)) {
            b = b.resultado;
        }
        return (b && typeof b === 'object' && !Array.isArray(b)) ? b : {};
    }

    function estaAtivo(r) {
        var st = norm(r && r.status);
        if (st) return st === 'A';
        var sit = norm(r && r.situacao);
        return sit === '' || sit === 'ATIVO';
    }

    function porPessoa(resp) {
        var m = new Map();
        var body = (resp && resp.body && typeof resp.body === 'object') ? resp.body : {};
        ['ATIVO', 'PASSIVO', 'TERCEIROS'].forEach(function (polo) {
            (body[polo] || []).forEach(function (p) {
                ((p && p.representantes) || []).forEach(function (r) {
                    var pid = r.idPessoa || r.id;
                    if (pid) m.set(String(pid), r);
                });
            });
        });
        return m;
    }

    async function coletar(idp) {
        var base = ORIGIN + '/pje-comum-api/api/processos/id/' + idp;
        var out = {};

        out.partes = await getJson(base + '/partes');
        out.processo = await getJson(base);
        // A tela /detalhe usa ?retornaEndereco=true; comparar as variantes mostra
        // se o `situacaoOab` vazio ("NAO ENCONTRADA" no DOM) vem da query.
        out.partes_endereco = await getJson(base + '/partes?retornaEndereco=true');
        out.partes_oab = await getJson(base + '/partes?retornaEndereco=true&retornaOab=true');
        // comInativas=true e a UNICA forma de ver advogados inativos (chip).
        out.partes_inativas = await getJson(base + '/partes?comInativas=true');

        var fonte = polos(out.partes_inativas);
        var src = Object.keys(fonte).length ? fonte : polos(out.partes);

        var advs = [];
        ['ATIVO', 'PASSIVO', 'TERCEIROS'].forEach(function (polo) {
            (src[polo] || []).forEach(function (p) {
                ((p && p.representantes) || []).forEach(function (r) {
                    var tipo = norm(r.tipo);
                    var oab = r.numeroOab || '';
                    if (tipo.indexOf('ADVOGADO') < 0 && tipo.indexOf('OAB') < 0 && !oab) return;
                    advs.push(Object.assign({ _polo: polo, _parte: (p.nome || '').trim(), _ativo: estaAtivo(r) }, r));
                });
            });
        });
        out.advogados = advs;
        out.mapEndereco = porPessoa(out.partes_endereco);
        out.mapOab = porPessoa(out.partes_oab);
        log('coleta: partes HTTP', out.partes.status, '| advogados', advs.length);
        return out;
    }

    // =========================================================================
    // Avaliacao por pessoa (espelha f.py)
    // =========================================================================
    async function avaliarPessoa(pid, a, dados) {
        var item = {
            idPessoa: pid,
            nome: a.nome || '',
            cpf: a.documento || a.cpf || '',
            polo: a._polo,
            parte: a._parte,
            ativo: a._ativo,
            oabPartes: a.numeroOab || '',
            situacaoPartes: a.situacaoOab || '',
        };
        var rEnd = dados.mapEndereco.get(String(pid)) || {};
        var rOab = dados.mapOab.get(String(pid)) || {};
        item.situacaoPartesEndereco = rEnd.situacaoOab || '';
        item.situacaoPartesOab = rOab.situacaoOab || '';

        var cad = await getJson(ORIGIN + '/pje-comum-api/api/pessoas/fisicas/advogados/' + pid);
        item.cadastro = (cad.body && typeof cad.body === 'object') ? cad.body : {};

        var val = await postJson(
            ORIGIN + '/pje-comum-api/api/pessoas/fisicas/' + pid
                + '/validacaooab?especializacao=' + encodeURIComponent('Advogado'), {});
        item.validacao = val;
        if (val.status !== 200) {
            item.erroHttp = 'validacaooab HTTP ' + (val.status || 'sem resposta')
                + (xsrf() ? '' : ' (sem XSRF-TOKEN no cookie)');
            return item;
        }

        var body = (val.body && typeof val.body === 'object') ? val.body : {};
        var dadosOab = Array.isArray(body.dadosOab) ? body.dadosOab : [];
        item.dadosOab = dadosOab.map(function (d) {
            return Object.assign({}, d, { situacaoLabel: CODIGOS[codigo(d)] || d.nomeSituacao || '' });
        });

        var mOab = String(item.oabPartes).match(/^([A-Za-z]{2})\s*(\d+)/);
        var ufAlvo = mOab ? mOab[1].toUpperCase() : '';
        var numAlvo = mOab ? String(parseInt(mOab[2], 10)) : '';
        var mesmoNumero = function (d) {
            var num = String(d.numInscricao || '').replace(/\D/g, '').replace(/^0+/, '');
            return !!numAlvo && num === numAlvo;
        };
        var match = (ufAlvo && numAlvo)
            ? (item.dadosOab.find(function (d) {
                return norm(d.uf) === ufAlvo && mesmoNumero(d);
            }) || null)
            : null;
        var regular = item.dadosOab.find(function (d) { return codigo(d) === 1; }) || null;
        var escolhida = match || regular || item.dadosOab[0] || null;
        // Impedimento = a inscricao do PROCESSO existe e nao e Regular.
        // Sem match e sem nenhuma regular, a primeira inscricao e a suspeita.
        var impedimento = (match && codigo(match) !== null && codigo(match) !== 1)
            ? match
            : ((!match && !regular && item.dadosOab.length) ? item.dadosOab[0] : null);

        item.multiplasOab = !!body.multiplasOab;
        item.dadosWsOab = body.dadosWsOab;
        item.pessoaOab = body.pessoaOab || null;
        item.matchProcesso = !!match;
        item.situacaoLive = escolhida
            ? (CODIGOS[codigo(escolhida)] || escolhida.nomeSituacao || '')
            : (body.dadosWsOab ? 'SEM_INSCRICAO' : 'NAO_CONSULTADO');
        item.inscricaoEscolhida = escolhida
            ? String(escolhida.uf || '') + String(escolhida.numInscricao || '') : '';
        item.impedimento = !!impedimento;
        item.motivoEscolha = impedimento
            ? (match ? 'match_impedimento' : 'sem_match_sem_regular')
            : (match ? 'match_regular' : 'sem_match_regular');

        var partes = norm(item.situacaoPartes);
        var partesEnd = norm(item.situacaoPartesEndereco);
        var partesOab = norm(item.situacaoPartesOab);
        var partesEfetiva = partesEnd || partesOab || partes;
        var live = norm(item.situacaoLive);
        var liveConhecida = live && live !== 'NAO_CONSULTADO' && live !== 'SEM_INSCRICAO';
        item.divergenciaVariantes = (partesEnd !== partes) || (partesOab !== partes);
        item.divergente = (partesEfetiva !== '' && partesEfetiva !== 'REGULAR' && live === 'REGULAR')
            || ((partesEfetiva === '' || partesEfetiva === 'REGULAR') && liveConhecida && live !== 'REGULAR');

        log('pessoa', pid, 'live=' + item.situacaoLive, 'match=' + item.matchProcesso,
            'motivo=' + item.motivoEscolha, 'divergente=' + item.divergente);
        return item;
    }

    // Solucao indicada (docs/CHIPADV_OAB_DOM_VS_POST.md §7 + adv.py).
    function solucao(item) {
        var live = norm(item.situacaoLive);
        if (item.erroHttp) {
            return { cls: 'manual', rotulo: 'verificar (falha HTTP)', detalhe: item.erroHttp + ' — repetir/validar manual.' };
        }
        if (live === 'NAO_CONSULTADO') {
            return { cls: 'manual', rotulo: 'verificar (WS nao respondeu)', detalhe: 'WS da OAB nao respondeu; validar manualmente.' };
        }
        if (live === 'SEM_INSCRICAO') {
            return { cls: 'manual', rotulo: 'sem inscricao na OAB', detalhe: 'WS sem inscricoes para a pessoa; conferir cadastro.' };
        }
        if (item.impedimento) {
            return {
                cls: 'gigs',
                rotulo: 'VALIDAR + GIGS',
                detalhe: 'Inscricao do processo (' + (item.inscricaoEscolhida || '?') + ') esta ' + item.situacaoLive
                    + '. Acao: validar na OAB e criar GIGS "Advogado suspenso".',
            };
        }
        if (!item.ativo) {
            return {
                cls: 'chips',
                rotulo: 'REPROCESSAR CHIPS',
                detalhe: 'Advogado INATIVO e regular na OAB: chip orfao. Acao: reprocessar os chips do processo.',
            };
        }
        if (item.divergente || item.divergenciaVariantes) {
            return {
                cls: 'manual',
                rotulo: 'VALIDAR CADASTRO',
                detalhe: 'DOM diverge da OAB live para advogado ativo; validar o cadastro.',
            };
        }
        return { cls: 'chips', rotulo: 'reprocessar/ok', detalhe: 'Sem impedimento na OAB para este advogado.' };
    }

    // =========================================================================
    // UI
    // =========================================================================
    var overlay = null;

    function injectStyle() {
        if (document.getElementById(CLS + '-style')) return;
        var s = document.createElement('style');
        s.id = CLS + '-style';
        s.textContent = [
            '#btn-chipadv-oab{position:fixed;bottom:20px;right:20px;z-index:2147483000;background:#7a1f1f;color:#fff;border:none;border-radius:6px;padding:10px 16px;font-size:13px;font-weight:bold;cursor:pointer;box-shadow:0 3px 6px rgba(0,0,0,.35)}',
            '#btn-chipadv-oab:hover{background:#5f1717}',
            '#chipadv-oab-panel{position:fixed;bottom:70px;right:20px;z-index:2147483001;width:660px;max-width:96vw;max-height:80vh;overflow:auto;background:#fff;color:#111;border:1px solid #b0b0b0;border-radius:8px;box-shadow:0 6px 22px rgba(0,0,0,.35);font:12px/1.45 "Segoe UI",Arial,sans-serif}',
            '#chipadv-oab-panel .cn-cab{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#7a1f1f;color:#fff;border-radius:8px 8px 0 0;font-weight:bold;font-size:13px;position:sticky;top:0;z-index:1}',
            '#chipadv-oab-panel .cn-cab button{background:none;border:none;color:#fff;font-size:16px;cursor:pointer}',
            '#chipadv-oab-panel .cn-body{padding:10px 12px}',
            '#chipadv-oab-panel table{width:100%;border-collapse:collapse}',
            '#chipadv-oab-panel th,#chipadv-oab-panel td{border:1px solid #ddd;padding:4px 6px;text-align:left;vertical-align:top;font-size:11px}',
            '#chipadv-oab-panel th{background:#f3f3f3;position:sticky;top:33px;z-index:1}',
            '.cn-sol-chips{color:#0a6b1f;font-weight:bold}',
            '.cn-sol-gigs{color:#a11;font-weight:bold}',
            '.cn-sol-manual{color:#b0720a;font-weight:bold}',
            '.cn-inativo{background:#fff4d6}',
            '.cn-summ{margin-bottom:8px}',
            '.cn-load{color:#555;padding:8px 0}',
            '.cn-erro{color:#a11;white-space:pre-wrap;font-family:Consolas,monospace;font-size:11px}',
            '.cn-flag{display:inline-block;background:#7a1f1f;color:#fff;border-radius:3px;padding:0 4px;font-size:10px}',
        ].join('\n');
        document.head.appendChild(s);
    }

    function abrirPainel() {
        if (overlay && document.body.contains(overlay)) return overlay;
        overlay = document.createElement('div');
        overlay.id = 'chipadv-oab-panel';
        overlay.innerHTML = '<div class="cn-cab"><span class="cn-cab-title">Chip Advogado Impedido</span>'
            + '<button type="button" data-close>×</button></div>'
            + '<div class="cn-body"><div class="cn-load">Analisando…</div></div>';
        overlay.querySelector('[data-close]').addEventListener('click', fechar);
        document.body.appendChild(overlay);
        return overlay;
    }

    function renderer(titulo, html) {
        if (!overlay || !document.body.contains(overlay)) abrirPainel();
        overlay.querySelector('.cn-cab-title').textContent = titulo;
        overlay.querySelector('.cn-body').innerHTML = html;
    }

    function fechar() { if (overlay) { overlay.remove(); overlay = null; } }

    async function analisar() {
        try {
            var idp = getProcessIdFromUrl();
            log('inicio; processo', idp, 'xsrf=' + (xsrf() ? 'ok' : 'AUSENTE'));
            if (!idp) return renderer('Erro', '<div class="cn-erro">Id do processo nao encontrado na URL.</div>');

            renderer('Analisando…', '<div class="cn-load">Consultando variantes de /partes e validando na OAB (live)…</div>');

            var dados = await coletar(idp);
            if (dados.partes.status !== 200) {
                return renderer('Erro', '<div class="cn-erro">/partes devolveu HTTP '
                    + dados.partes.status + '. Sessao ok?</div>');
            }
            if (!dados.advogados.length) {
                return renderer('Sem representantes', '<div class="cn-erro">Nenhum advogado/OAB encontrado (partes com inativas: '
                    + dados.partes_inativas.status + ').</div>');
            }

            // Um POST por pessoa (advogado repetido em polos nao repete a chamada).
            var pessoas = new Map();
            dados.advogados.forEach(function (a) {
                var pid = a.idPessoa || a.id;
                if (!pid || pessoas.has(pid)) return;
                pessoas.set(pid, a);
            });

            var itens = [];
            var lista = Array.from(pessoas);
            for (var i = 0; i < lista.length; i++) {
                itens.push(await avaliarPessoa(lista[i][0], lista[i][1], dados));
            }

            var conta = { impedidos: 0, inativos: 0, semImpedimento: 0, manual: 0, divergentes: 0 };
            var rows = itens.map(function (it) {
                var s = solucao(it);
                if (s.cls === 'gigs') conta.impedidos++;
                else if (s.cls === 'manual') conta.manual++;
                else if (!it.ativo) conta.inativos++;
                else conta.semImpedimento++;
                if (it.divergente) conta.divergentes++;

                var flags = [];
                if (it.divergente) flags.push('<span class="cn-flag">DIVERGENTE</span>');
                if (it.divergenciaVariantes) flags.push('<span class="cn-flag">VARIANTES DIFEREM</span>');
                if (it.multiplasOab) flags.push('<span class="cn-flag">MULTIPLAS OAB</span>');

                return '<tr' + (it.ativo ? '' : ' class="cn-inativo"') + '>'
                    + '<td>' + esc(it.nome) + '<br><small>' + esc(it.parte) + ' · ' + esc(it.polo)
                    + ' · ' + (it.ativo ? 'ATIVO' : 'INATIVO') + '</small></td>'
                    + '<td>' + esc(it.oabPartes || '—') + '</td>'
                    + '<td>' + esc(it.situacaoPartes || '—') + '</td>'
                    + '<td>' + esc(it.situacaoPartesEndereco || '—') + '</td>'
                    + '<td>' + esc(it.situacaoPartesOab || '—') + '</td>'
                    + '<td><b>' + esc(it.situacaoLive || '—') + '</b>'
                    + (it.inscricaoEscolhida ? '<br><small>' + esc(it.inscricaoEscolhida)
                        + ' (' + esc(it.motivoEscolha) + ')</small>' : '')
                    + (flags.length ? '<br>' + flags.join(' ') : '') + '</td>'
                    + '<td class="cn-sol-' + s.cls + '">' + esc(s.rotulo) + '<br><small>' + esc(s.detalhe) + '</small></td>'
                    + '</tr>';
            }).join('');

            renderer('Relatório — ' + itens.length + ' pessoa(s)',
                '<div class="cn-summ"><b>' + conta.impedidos + '</b> impedido(s) · <b>'
                + conta.inativos + '</b> so inativo · <b>' + conta.semImpedimento + '</b> sem impedimento · <b>'
                + conta.manual + '</b> conferir manual · <b>' + conta.divergentes + '</b> divergente(s) DOM x live</div>'
                + '<table><thead><tr><th>Advogado</th><th>OAB proc.</th><th>/partes</th>'
                + '<th>retornaEndereco</th><th>retornaOab</th><th>OAB live</th><th>Solucao</th></tr></thead>'
                + '<tbody>' + rows + '</tbody></table>');
            log('fim:', JSON.stringify(conta));
        } catch (e) {
            log('ERRO', e && e.stack || e);
            renderer('Erro', '<div class="cn-erro">' + esc(e && e.stack || e) + '</div>');
        }
    }

    function init() {
        try {
            injectStyle();
            if (document.getElementById('btn-chipadv-oab')) { log('botao ja existe'); return; }
            var btn = document.createElement('button');
            btn.id = 'btn-chipadv-oab';
            btn.type = 'button';
            btn.textContent = '◌ Chip Impedido OAB';
            btn.addEventListener('click', function () {
                log('clique');
                if (overlay && document.body.contains(overlay)) { fechar(); return; }
                abrirPainel();
                analisar();
            });
            document.body.appendChild(btn);
            log('botao injetado');
        } catch (e) {
            log('ERRO ao injetar botao', e && e.stack || e);
        }
    }

    if (document.documentElement.getAttribute('data-' + CLS + '-boot')) {
        log('boot ja marcado, saindo');
        return;
    }
    document.documentElement.setAttribute('data-' + CLS + '-boot', '1');
    log('iniciando v' + (typeof GM_info !== 'undefined' && GM_info.script
        ? GM_info.script.version : '?'));

    if (document.body) init();
    else document.addEventListener('DOMContentLoaded', init, { once: true });
})();
