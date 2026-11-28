'use strict';

// ═══════════════════════════════════════════════════════════════════
// GIGS — atividades.js (listar / excluir atividades + limpeza de vencidas)
// Onde: https://pje.trt2.jus.br/pjekz/processo/<id>/detalhe
// Endpoints (validados no probe):
//   GET    /pje-gigs-api/api/atividade/processo/{idProcesso}   → Array[atividade]
//   DELETE /pje-gigs-api/api/atividade/{idAtividade}           → 204
// Campos de cada atividade: id, idProcesso, tipoAtividade, dataPrazo,
//   statusAtividade, observacao, dataCriacao, ...
//
// API exposta (console ou outros módulos):
//   PjeGigsAtividades.listar(idProcesso)                       → Promise<Array>
//   PjeGigsAtividades.excluir(idAtividade)                     → Promise<{ok,status}>
//   PjeGigsAtividades.teimosinhaVencidas(idProcesso)           → Promise<Array> (dry-run)
//   PjeGigsAtividades.limparTeimosinhaVencidas(idProcesso, {    // apaga de verdade
//       seco: false,        // true = só lista, não apaga
//       confirmar: true,    // false = não pede confirm() (use com cautela)
//       onProgresso: fn     // (feitos, total, atividade)
//   })
//   PjeGigsAtividades.injetarBotao()                           // botão na tela /detalhe
// ═══════════════════════════════════════════════════════════════════

(function () {
    if (window.PjeGigsAtividades) return;

    var API = '/pje-gigs-api/api';
    var ID_BOTAO = 'pjetools-gigs-limpar-teimosinha';
    var TEXTO_PADRAO = 'Excluir GIGS Teimosinha vencidas';
    var RE_TEIMOSINHA = /teimosinha/i;

    // ── utilidades ──────────────────────────────────────────────────
    function hostPje() {
        return /(^|\.)pje[a-z0-9-]*\.jus\.br$/i.test(window.location.hostname || '') &&
            (window.location.pathname || '').indexOf('/pjekz/') === 0;
    }

    function rotaDetalhe() {
        return /\/processo\/\d+\/detalhe/.test(window.location.pathname || '');
    }

    function idProcessoAtual() {
        var m = (window.location.pathname || '').match(/\/processo\/(\d+)/);
        return m ? m[1] : null;
    }

    function norm(s) {
        return String(s === null || s === undefined ? '' : s).replace(/\s+/g, ' ').trim();
    }

    function confirmar(msg) {
        var w = (typeof unsafeWindow !== 'undefined' && unsafeWindow) ? unsafeWindow : window;
        var fn = (w && w.confirm) || window.confirm;
        return typeof fn === 'function' ? fn.call(w || window, msg) : false;
    }

    function tokenXsrf() {
        var m = String(document.cookie || '').match(/(?:^|;\s*)XSRF-TOKEN=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : '';
    }

    function headersJson(extra) {
        var h = { 'Accept': 'application/json', 'Content-Type': 'application/json' };
        var t = tokenXsrf();
        if (t) h['X-XSRF-TOKEN'] = t;
        return Object.assign(h, extra || {});
    }

    // Texto usado no casamento de "teimosinha" (tipo, observação e descrição crua)
    function textoAtividade(a) {
        if (!a) return '';
        return norm([a.tipoAtividade, a.observacao, a.descricao, a.processo, a.nome].join(' '));
    }

    function ehTeimosinha(a) {
        return RE_TEIMOSINHA.test(textoAtividade(a));
    }

    // dataPrazo vem como 'YYYY-MM-DD' (ou ISO); sem hora, vence no fim do dia
    function dataPrazoMs(a) {
        var v = a && (a.dataPrazo || a.dataPrazoFinal);
        if (v === null || v === undefined || v === '') return NaN;
        if (typeof v === 'number') return v;
        var s = String(v).trim();
        var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (m) return new Date(+m[1], +m[2] - 1, +m[3], 23, 59, 59, 999).getTime();
        m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
        if (m) return new Date(+m[3], +m[2] - 1, +m[1], 23, 59, 59, 999).getTime();
        var t = Date.parse(s);
        return isNaN(t) ? NaN : t;
    }

    function vencida(a, agora) {
        var t = dataPrazoMs(a);
        return isFinite(t) && t < (agora || Date.now());
    }

    // Atividade ainda "aberta": status vazio ou sem CONCLU/CANCEL/EXCLU
    function aberta(a) {
        var st = norm(a && a.statusAtividade).toUpperCase();
        if (!st) return true;
        return st.indexOf('CONCLU') === -1 && st.indexOf('CANCEL') === -1 && st.indexOf('EXCLU') === -1;
    }

    function toast(msg, tipo) {
        if (window.SisbCore && typeof window.SisbCore.mostrarToast === 'function') {
            window.SisbCore.mostrarToast(msg, tipo || 'ok');
            return;
        }
        var cores = { ok: '#2e7d32', aviso: '#ef6c00', erro: '#c62828' };
        var d = document.createElement('div');
        d.style.cssText = 'position:fixed;bottom:72px;left:20px;z-index:2147483002;background:' +
            (cores[tipo] || cores.ok) + ';color:#fff;padding:10px 16px;border-radius:6px;' +
            'font:bold 13px Arial,sans-serif;box-shadow:0 3px 10px rgba(0,0,0,.3);max-width:520px;';
        d.textContent = msg;
        document.body.appendChild(d);
        setTimeout(function () { if (d.parentNode) d.remove(); }, 5000);
    }

    // ── API ─────────────────────────────────────────────────────────
    async function listar(idProcesso) {
        var id = idProcesso || idProcessoAtual();
        if (!id) throw new Error('sem idProcesso');
        var r = await fetch(location.origin + API + '/atividade/processo/' + encodeURIComponent(id), {
            method: 'GET',
            credentials: 'include',
            headers: headersJson()
        });
        if (!r.ok) throw new Error('GET atividades HTTP ' + r.status);
        var dados = await r.json();
        return Array.isArray(dados) ? dados : [];
    }

    async function excluir(idAtividade) {
        if (!idAtividade) return { ok: false, status: 0, erro: 'idAtividade vazio' };
        try {
            var r = await fetch(location.origin + API + '/atividade/' + encodeURIComponent(idAtividade), {
                method: 'DELETE',
                credentials: 'include',
                headers: headersJson()
            });
            var ok = r.ok || r.status === 204;
            if (!ok) console.warn('[PjeGigsAtividades] DELETE', idAtividade, 'HTTP', r.status);
            return { ok: ok, status: r.status, id: idAtividade };
        } catch (e) {
            console.warn('[PjeGigsAtividades] DELETE falhou', idAtividade, e);
            return { ok: false, status: 0, id: idAtividade, erro: String(e && e.message || e) };
        }
    }

    // ── Regra do pedido: vencida + "teimosinha" ─────────────────────
    function teimosinhaVencidas(idProcesso) {
        return listar(idProcesso).then(function (lista) {
            var agora = Date.now();
            var alvo = lista.filter(function (a) {
                return aberta(a) && ehTeimosinha(a) && vencida(a, agora);
            });
            console.log('[PjeGigsAtividades] ' + alvo.length + ' de ' + lista.length +
                ' atividade(s) vencida(s) com "teimosinha"', alvo.map(descrever));
            return alvo;
        });
    }

    function descrever(a) {
        return {
            id: a.id,
            tipo: norm(a.tipoAtividade),
            prazo: norm(a.dataPrazo),
            status: norm(a.statusAtividade),
            observacao: norm(a.observacao).slice(0, 120)
        };
    }

    async function limparTeimosinhaVencidas(idProcesso, opcoes) {
        var opts = Object.assign({ seco: false, confirmar: true, onProgresso: null }, opcoes || {});
        var id = idProcesso || idProcessoAtual();
        if (!id) return { ok: false, motivo: 'sem idProcesso (abra /pjekz/processo/<id>/detalhe)' };

        var alvo = await teimosinhaVencidas(id);
        if (!alvo.length) {
            return { ok: true, total: 0, excluidas: 0, falhas: 0, itens: [] };
        }
        if (opts.seco) {
            return { ok: true, seco: true, total: alvo.length, itens: alvo.map(descrever) };
        }

        if (opts.confirmar !== false) {
            var resumo = alvo.slice(0, 10).map(function (a) {
                return '• ' + (a.id + ' — ' + norm(a.tipoAtividade) + ' — prazo ' + norm(a.dataPrazo));
            }).join('\n');
            var msg = 'Excluir ' + alvo.length + ' GIGS vencida(s) com "teimosinha" do processo ' +
                id + '?\n\n' + resumo + (alvo.length > 10 ? '\n… e mais ' + (alvo.length - 10) : '');
            if (!confirmar(msg)) return { ok: false, cancelado: true, total: alvo.length };
        }

        var excluidas = 0;
        var falhas = [];
        for (var i = 0; i < alvo.length; i++) {
            var a = alvo[i];
            var r = await excluir(a.id);
            if (r.ok) {
                excluidas++;
                removerLinhaTabela(a.id);
            } else {
                falhas.push({ id: a.id, status: r.status, erro: r.erro || '' });
            }
            if (typeof opts.onProgresso === 'function') {
                try { opts.onProgresso(i + 1, alvo.length, a, r); } catch (e) { }
            }
        }

        console.log('[PjeGigsAtividades] limpeza concluída: ' + excluidas + '/' + alvo.length +
            ' excluída(s)', falhas);
        return { ok: falhas.length === 0, total: alvo.length, excluidas: excluidas, falhas: falhas.length, erros: falhas };
    }

    // Remove a linha da tabela #tabela-atividades (id do botão: #excluir-atividade-<id>)
    function removerLinhaTabela(idAtividade) {
        var btn = document.getElementById('excluir-atividade-' + idAtividade);
        var tr = btn && btn.closest ? btn.closest('tr') : null;
        if (tr && tr.parentNode) tr.parentNode.removeChild(tr);
    }

    // ── Botão na tela /detalhe ──────────────────────────────────────
    function injetarBotao() {
        if (!hostPje() || !document.body) return;
        var existente = document.getElementById(ID_BOTAO);
        if (!rotaDetalhe()) {
            if (existente) existente.remove();
            return;
        }
        if (existente) return;

        var btn = document.createElement('button');
        btn.id = ID_BOTAO;
        btn.type = 'button';
        btn.textContent = TEXTO_PADRAO;
        btn.title = 'Lista as GIGS vencidas com "teimosinha" no processo e exclui pela API (DELETE /pje-gigs-api/api/atividade/{id})';
        btn.style.cssText = 'position:fixed;bottom:20px;left:20px;z-index:999999;' +
            'padding:9px 14px;border:none;border-radius:8px;background:#c62828;color:#fff;' +
            'font:bold 13px Arial,sans-serif;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,0.3);';
        btn.addEventListener('click', function () { aoClicar(btn); });
        document.body.appendChild(btn);
    }

    async function aoClicar(btn) {
        var id = idProcessoAtual();
        if (!id) {
            toast('Não achei o idProcesso na URL.', 'erro');
            return;
        }
        btn.disabled = true;
        btn.textContent = 'Verificando…';
        try {
            var previa = await limparTeimosinhaVencidas(id, { seco: true });
            if (!previa.total) {
                toast('Nenhuma GIGS vencida com "teimosinha" neste processo.', 'aviso');
                btn.textContent = TEXTO_PADRAO;
                btn.disabled = false;
                return;
            }
            btn.textContent = 'Excluindo 0/' + previa.total + '…';
            var res = await limparTeimosinhaVencidas(id, {
                confirmar: true,
                onProgresso: function (feitos, total) {
                    btn.textContent = 'Excluindo ' + feitos + '/' + total + '…';
                }
            });
            if (res.cancelado) {
                toast('Exclusão cancelada.', 'aviso');
            } else if (res.excluidas) {
                toast('Excluídas ' + res.excluidas + ' de ' + res.total + ' GIGS vencidas.' +
                    (res.falhas ? ' Falhas: ' + res.falhas : ''), res.falhas ? 'aviso' : 'ok');
            } else {
                toast('Nenhuma GIGS excluída' + (res.falhas ? ' (' + res.falhas + ' falha(s))' : '.'), 'aviso');
            }
        } catch (e) {
            console.error('[PjeGigsAtividades] erro:', e);
            toast('Erro: ' + ((e && e.message) || e), 'erro');
        } finally {
            btn.textContent = TEXTO_PADRAO;
            btn.disabled = false;
        }
    }

    // ── Boot ────────────────────────────────────────────────────────
    window.PjeGigsAtividades = {
        listar: listar,
        excluir: excluir,
        teimosinhaVencidas: teimosinhaVencidas,
        limparTeimosinhaVencidas: limparTeimosinhaVencidas,
        injetarBotao: injetarBotao,
        idProcessoAtual: idProcessoAtual
    };

    if (hostPje() && rotaDetalhe()) {
        setTimeout(injetarBotao, 800);
        setInterval(injetarBotao, 2000);
    }

    console.log('[PjeGigsAtividades] módulo carregado em', location.host + location.pathname);
})();
