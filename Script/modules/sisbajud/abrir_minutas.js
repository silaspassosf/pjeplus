'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — abrir_minutas.js (botão "Abrir minutas")
// Onde: https://sisbajud.cnj.jus.br/minuta (e sisbajud.pdpj.jus.br/minuta)
// Posição: dentro do divisor .uikit-actions, ao lado do botão "Consultar"
// Injeção: basta estar em /minuta (sem exigir radio/tabela); o clique em
//          "Consultar" também serve de gatilho e o clique no botão avisa o
//          que falta (radio do juiz marcado / tabela carregada)
// O que faz, a cada clique:
//   1. Ignora processos/minutas já abertos e pega o próximo processo na ordem da tabela
//   2. Reúne até 2 minutas desse mesmo processo na tabela
//   3. Abre em novas abas (sem sair de /minuta), primeiro a mais abaixo e depois a de cima
//      (URL: <origin>/minuta/<idMinuta>/alterar)
//   4. Antes de abrir, apaga as GIGS vencidas com "teimosinha" do processo
//      e abre a aba no PJe em /documento/anexar
//      (Atalhos.abrir_processo_direto(numero, { rota: 'anexar', limparGigsTeimosinha: true }))
//   5. Colore/destaca as linhas já abertas na tabela
// Injetado pelo orquestrador (sisbajud.js → injetarUI) e também disparado ao Consultar.
// ═══════════════════════════════════════════════════════════════════

(function () {
    if (window.SisbAbrirMinutas) return;

    var ID_BOTAO = 'pjetools-sisb-abrir-minutas-btn';
    var TEXTO_PADRAO = 'Abrir minutas';
    var RE_CNJ = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;

    var ultimosItens = [];       // array content[] retornado por GET /v2/ordem/minuta
    var ultimaUrlApi = '';
    var idsAbertos = new Set();  // idMinuta já abertos na sessão
    var procsAbertos = new Set(); // numeroProcesso (dígitos) já abertos
    var ultimoLoteIds = new Set(); // lote aberto no clique mais recente
    var executando = false;

    function hostSisbajud() {
        return /^sisbajud\.(pdpj|cnj)\.jus\.br$/.test(window.location.hostname || '');
    }

    function naRotaMinuta() {
        var p = window.location.pathname || '';
        return p === '/minuta' || p === '/minuta/';
    }

    function esperar(ms) {
        return new Promise(function (r) { setTimeout(r, ms); });
    }

    function digitos(s) {
        return String(s || '').replace(/\D/g, '');
    }

    function norm(s) {
        return String(s || '').replace(/\s+/g, ' ').trim();
    }

    function extrairCnj(s) {
        var m = String(s || '').match(RE_CNJ);
        return m ? m[0] : norm(s);
    }

    function radioJuizSelecionado() {
        if (document.querySelector('mat-radio-button.mat-radio-juiz.mat-radio-checked')) return true;
        // fallback: qualquer radio marcado cujo rótulo fale de "juiz"
        var marcados = document.querySelectorAll('mat-radio-button.mat-radio-checked');
        for (var i = 0; i < marcados.length; i++) {
            if (norm(marcados[i].textContent).toLowerCase().indexOf('juiz') > -1) return true;
        }
        return false;
    }

    function linhasTabela() {
        return Array.from(document.querySelectorAll('table.mat-table tbody tr.mat-row'));
    }

    function toast(msg, cor) {
        if (window.SisbCore && typeof window.SisbCore.mostrarToast === 'function') {
            var tipo = cor === '#c62828' ? 'erro' : (cor === '#ef6c00' ? 'aviso' : 'ok');
            window.SisbCore.mostrarToast(msg, tipo);
            return;
        }
        var d = document.createElement('div');
        d.style.cssText = 'position:fixed;top:64px;right:20px;z-index:2147483002;background:' +
            (cor || '#1565c0') + ';color:#fff;padding:10px 16px;border-radius:6px;' +
            'font:bold 13px Arial,sans-serif;box-shadow:0 3px 10px rgba(0,0,0,.3);';
        d.textContent = msg;
        document.body.appendChild(d);
        setTimeout(function () { if (d.parentNode) d.remove(); }, 4000);
    }

    // ── Interceptador de GET /v2/ordem/minuta (captura idMinuta) ─────
    function registrarRespostaApi(url, texto) {
        if (!url || String(url).indexOf('/v2/ordem/minuta') === -1) return;
        try {
            var json = JSON.parse(texto);
            var lista = Array.isArray(json) ? json : (Array.isArray(json && json.content) ? json.content : null);
            if (lista) {
                ultimosItens = lista;
                ultimaUrlApi = String(url);
                console.log('[SisbAbrirMinutas] capturadas', lista.length, 'minutas de /v2/ordem/minuta');
                setTimeout(function () {
                    injetarBotao();
                    reaplicarDestaques();
                }, 250);
            }
        } catch (e) { /* resposta não-JSON */ }
    }

    function instalarInterceptador() {
        var win = (typeof unsafeWindow !== 'undefined' && unsafeWindow) ? unsafeWindow : window;
        if (!win || win.__pjetoolsMinutaHooked) return;
        win.__pjetoolsMinutaHooked = true;

        try {
            var XHR = win.XMLHttpRequest;
            if (XHR && XHR.prototype) {
                var origOpen = XHR.prototype.open;
                var origSend = XHR.prototype.send;
                XHR.prototype.open = function (method, url) {
                    this.__pjeUrl = url;
                    return origOpen.apply(this, arguments);
                };
                XHR.prototype.send = function () {
                    var self = this;
                    if (self.__pjeUrl && String(self.__pjeUrl).indexOf('/v2/ordem/minuta') !== -1) {
                        self.addEventListener('load', function () {
                            if (self.status === 200) registrarRespostaApi(self.__pjeUrl, self.responseText || '');
                        });
                    }
                    return origSend.apply(this, arguments);
                };
            }
        } catch (e) {
            console.warn('[SisbAbrirMinutas] falha ao hookar XHR:', e);
        }

        try {
            if (typeof win.fetch === 'function') {
                var origFetch = win.fetch;
                win.fetch = function (input) {
                    var url = typeof input === 'string' ? input : (input && input.url) || '';
                    var p = origFetch.apply(this, arguments);
                    if (url.indexOf('/v2/ordem/minuta') !== -1) {
                        p.then(function (resp) {
                            if (resp && resp.ok) {
                                resp.clone().text().then(function (txt) { registrarRespostaApi(url, txt); }).catch(function () { });
                            }
                        }).catch(function () { });
                    }
                    return p;
                };
            }
        } catch (e) {
            console.warn('[SisbAbrirMinutas] falha ao hookar fetch:', e);
        }
    }

    // ── Fallback: consulta /v2/ordem/minuta direto se ainda não capturou ──
    function lerTokenLocal() {
        var storages = [];
        try { if (typeof unsafeWindow !== 'undefined' && unsafeWindow.localStorage) storages.push(unsafeWindow.localStorage); } catch (e) { }
        try { if (window.localStorage) storages.push(window.localStorage); } catch (e) { }
        for (var i = 0; i < storages.length; i++) {
            try {
                var t = String(storages[i].getItem('sisbajud-token') || storages[i].getItem('LS.sisbajud-token') || '')
                    .trim().replace(/^"+|"+$/g, '');
                if (t) return t;
            } catch (e) { }
        }
        return '';
    }

    async function buscarItensViaApiFallback() {
        var token = lerTokenLocal();
        var headers = { Accept: 'application/json' };
        if (token) headers.Authorization = 'Bearer ' + token;

        // Se já temos a última URL, apenas reconsulta
        if (ultimaUrlApi) {
            var u = /^https?:/.test(ultimaUrlApi) ? ultimaUrlApi : (location.origin + ultimaUrlApi);
            var r0 = await fetch(u, { headers: headers, credentials: 'include' });
            if (r0.ok) {
                var j0 = await r0.json();
                var l0 = Array.isArray(j0) ? j0 : (j0 && j0.content) || [];
                if (l0.length) { ultimosItens = l0; return l0; }
            }
        }

        // Descobre codJuizSolicitante pelo nome selecionado em mat-select[name="juizSolicitante"]
        var selJuiz = document.querySelector('mat-select[name="juizSolicitante"]');
        var nomeJuizSel = norm(selJuiz ? selJuiz.textContent : '').toUpperCase();
        var codJuiz = '';

        try {
            var cpfAssessor = '';
            if (token) {
                var p = token.split('.')[1];
                if (p) {
                    var b = p.replace(/-/g, '+').replace(/_/g, '/');
                    while (b.length % 4) b += '=';
                    var payload = JSON.parse(atob(b));
                    cpfAssessor = digitos(payload.preferred_username || payload.cpf || payload.sub || '');
                }
            }
            if (cpfAssessor) {
                var rDel = await fetch(
                    location.origin + '/v1/delegacao-protocolizacao/ativa/juiz?cpfAssessor=' + encodeURIComponent(cpfAssessor),
                    { headers: headers, credentials: 'include' }
                );
                if (rDel.ok) {
                    var listaJuizes = await rDel.json();
                    if (Array.isArray(listaJuizes) && listaJuizes.length) {
                        var match = listaJuizes.find(function (j) {
                            var nm = norm(j.nome || j.nomeJuiz || '').toUpperCase();
                            return nomeJuizSel && nm.indexOf(nomeJuizSel) > -1;
                        }) || listaJuizes[0];
                        codJuiz = digitos(match.cpf || match.codJuiz || match.codigo || match.cpfJuiz || '');
                    }
                }
            }
        } catch (e) {
            console.warn('[SisbAbrirMinutas] erro ao buscar delegação:', e);
        }

        if (!codJuiz) return [];

        var urlApi = location.origin + '/v2/ordem/minuta?pageIndex=0&colunaAtiva=dataAlteracao' +
            '&ordenacaoAsc=false&acaoSistema=false&criadaPeloUsuario=false&codJuizSolicitante=' +
            encodeURIComponent(codJuiz);
        var rMin = await fetch(urlApi, { headers: headers, credentials: 'include' });
        if (!rMin.ok) return [];
        var jMin = await rMin.json();
        var lista = Array.isArray(jMin) ? jMin : (jMin && jMin.content) || [];
        if (lista.length) {
            ultimosItens = lista;
            ultimaUrlApi = urlApi;
        }
        return lista;
    }

    // ── Casamento das linhas da tabela com os itens da API ───────────
    function mapearLinhasComItens(rows, itens) {
        var usados = new Set();
        return rows.map(function (tr, idx) {
            var tdProc = tr.querySelector('td.cdk-column-numeroProcesso');
            var tdData = tr.querySelector('td.cdk-column-dataAlteracao');
            var proc = extrairCnj(tdProc ? tdProc.textContent : '');
            var procDig = digitos(proc);
            var dataTxt = norm(tdData ? tdData.textContent : '');

            var item = null;
            // 1. Tentativa direta pelo mesmo índice
            if (itens[idx] && !usados.has(idx) && digitos(itens[idx].numeroProcesso) === procDig) {
                item = itens[idx];
                usados.add(idx);
            } else {
                // 2. Busca por processo + data
                for (var i = 0; i < itens.length; i++) {
                    if (usados.has(i)) continue;
                    if (digitos(itens[i].numeroProcesso) === procDig && norm(itens[i].dataMinuta) === dataTxt) {
                        item = itens[i];
                        usados.add(i);
                        break;
                    }
                }
                // 3. Busca apenas por processo
                if (!item) {
                    for (var j = 0; j < itens.length; j++) {
                        if (usados.has(j)) continue;
                        if (digitos(itens[j].numeroProcesso) === procDig) {
                            item = itens[j];
                            usados.add(j);
                            break;
                        }
                    }
                }
            }

            var idMinuta = item ? String(item.idMinuta || item.codigo || item.id || '') : '';
            if (idMinuta) tr.dataset.pjetoolsMinutaId = idMinuta;
            if (procDig) tr.dataset.pjetoolsProcDig = procDig;

            return {
                idx: idx,
                tr: tr,
                numeroProcesso: proc,
                procDig: procDig,
                idMinuta: idMinuta,
            };
        });
    }

    // ── Destaque visual das linhas já abertas ────────────────────────
    function colorirLinha(tr, atual) {
        if (!tr) return;
        tr.style.backgroundColor = atual ? '#c8e6c9' : '#e8f5e9';
        tr.style.borderLeft = atual ? '5px solid #1b5e20' : '4px solid #66bb6a';
        tr.style.transition = 'background-color 0.25s ease';
    }

    function reaplicarDestaques() {
        var rows = linhasTabela();
        if (!rows.length) return;
        var mapeadas = mapearLinhasComItens(rows, ultimosItens);
        mapeadas.forEach(function (m) {
            var jaAberta = (m.idMinuta && idsAbertos.has(m.idMinuta)) || (m.procDig && procsAbertos.has(m.procDig));
            if (jaAberta) {
                var ehUltimo = m.idMinuta ? ultimoLoteIds.has(m.idMinuta) : false;
                colorirLinha(m.tr, ehUltimo);
            }
        });
    }

    // ── Abertura de abas (minuta no SISBAJUD + processo no PJe) ──────
    function abrirNovaAba(url) {
        try {
            if (typeof GM_openInTab === 'function') {
                GM_openInTab(url, { active: false, insert: true, setParent: true });
                return true;
            }
        } catch (e) { /* fallback */ }
        try {
            window.open(url, '_blank', 'noopener');
            return true;
        } catch (e) {
            return false;
        }
    }

    function abrirProcessoNoPJe(numero) {
        var fn = (window.Atalhos && window.Atalhos.abrir_processo_direto) || window.abrir_processo_direto;
        if (typeof fn !== 'function' || !numero) {
            console.log('[SisbAbrirMinutas] abrir_processo_direto indisponível ou número vazio:', numero);
            return;
        }
        Promise.resolve(fn(numero, { focar: false, rota: 'anexar', limparGigsTeimosinha: true })).then(
            function (r) { console.log('[SisbAbrirMinutas] PJe:', numero, r); },
            function (e) { console.warn('[SisbAbrirMinutas] falha ao abrir PJe:', numero, e); }
        );
    }

    // ── Ação do botão "Abrir minutas" ────────────────────────────────
    async function aoClicar(btn) {
        if (executando) return;
        executando = true;
        btn.disabled = true;

        try {
            var rows = linhasTabela();
            if (!rows.length) {
                console.log('[SisbAbrirMinutas] sem linhas | radioJuiz=' + radioJuizSelecionado());
                toast(radioJuizSelecionado()
                    ? 'Tabela vazia — clique em "Consultar" e aguarde carregar.'
                    : 'Marque "Minutas a protocolizar destinadas ao juiz" e clique em "Consultar".',
                    '#ef6c00');
                return;
            }

            if (!ultimosItens.length) {
                definirRotulo(btn, 'Buscando IDs...');
                await buscarItensViaApiFallback();
            }

            if (!ultimosItens.length) {
                toast('Não foi possível obter os IDs das minutas. Clique em "Consultar" novamente.', '#c62828');
                return;
            }

            var mapeadas = mapearLinhasComItens(rows, ultimosItens);

            // Encontra o primeiro processo ainda não aberto na ordem da tabela
            var primeiro = mapeadas.find(function (m) {
                if (!m.procDig || !m.idMinuta) return false;
                if (procsAbertos.has(m.procDig)) return false;
                if (idsAbertos.has(m.idMinuta)) return false;
                return true;
            });

            if (!primeiro) {
                toast('Todos os processos desta página já foram abertos!', '#ef6c00');
                return;
            }

            // Reúne até 2 minutas do mesmo processo, mantendo a ordem da tabela
            var grupo = mapeadas.filter(function (m) {
                return m.procDig === primeiro.procDig && m.idMinuta && !idsAbertos.has(m.idMinuta);
            }).slice(0, 2);

            // Rebaixa destaque do lote anterior para "já aberto"
            reaplicarDestaques();
            ultimoLoteIds = new Set();

            // Abre primeiro a mais abaixo e depois a de cima (ordem reversa do grupo)
            var ordemAbertura = grupo.slice().reverse();
            definirRotulo(btn, 'Abrindo (' + ordemAbertura.length + ')...');

            for (var i = 0; i < ordemAbertura.length; i++) {
                var item = ordemAbertura[i];
                var urlMinuta = location.origin + '/minuta/' + encodeURIComponent(item.idMinuta) + '/alterar';
                abrirNovaAba(urlMinuta);
                idsAbertos.add(item.idMinuta);
                ultimoLoteIds.add(item.idMinuta);
                colorirLinha(item.tr, true);
                if (i < ordemAbertura.length - 1) await esperar(200);
            }

            procsAbertos.add(primeiro.procDig);

            // Abre também a aba do PJe do processo respectivo
            await esperar(180);
            abrirProcessoNoPJe(primeiro.numeroProcesso);

            // Rola suavemente até a linha aberta para facilitar acompanhamento visual
            try { grupo[0].tr.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch (e) { }

            toast(
                'Abertas ' + ordemAbertura.length + ' minuta(s) + PJe: ' + primeiro.numeroProcesso,
                '#2e7d32'
            );
        } catch (e) {
            console.error('[SisbAbrirMinutas] erro:', e);
            toast('Erro ao abrir minutas: ' + ((e && e.message) || e), '#c62828');
        } finally {
            definirRotulo(btn, TEXTO_PADRAO);
            btn.disabled = false;
            executando = false;
        }
    }

    // ── Injeção do botão (no divisor de ações, ao lado de "Consultar") ──
    // Não depende de radio/tabela: basta estar em /minuta. O clique é que
    // valida o estado e avisa o que falta (radio do juiz, tabela vazia).
    function botaoConsultar() {
        var botoes = Array.prototype.slice.call(document.querySelectorAll('button.mat-fab'));
        for (var i = 0; i < botoes.length; i++) {
            if (norm(botoes[i].textContent).toLowerCase().indexOf('consultar') > -1) return botoes[i];
        }
        return null;
    }

    // .uikit-actions é o divisor que contém Nova / Protocolar / Consultar
    function containerAcoes() {
        var consultar = botaoConsultar();
        if (consultar && consultar.parentNode) return consultar.parentNode;
        return document.querySelector('div.uikit-actions') || null;
    }

    function definirRotulo(btn, texto) {
        var wrap = btn.querySelector('.mat-button-wrapper');
        if (!wrap) { btn.textContent = texto; return; }
        Array.prototype.slice.call(wrap.childNodes).forEach(function (n) {
            if (n.nodeType === 3) wrap.removeChild(n);
        });
        wrap.appendChild(document.createTextNode(' ' + texto));
    }

    // Clona o "Consultar" para herdar classes/estrutura (mat-fab, ripple, ícone)
    function montarBotao() {
        var modelo = botaoConsultar();
        var btn = modelo ? modelo.cloneNode(true) : document.createElement('button');
        if (!modelo) {
            btn.type = 'button';
            btn.className = 'mat-fab mat-button-base';
            btn.innerHTML = '<span class="mat-button-wrapper"></span>';
        }
        btn.id = ID_BOTAO;
        btn.removeAttribute('onclick');
        btn.title = 'Abre em novas abas (de baixo para cima, até 2) as minutas do próximo processo + aba do PJe';
        var icone = btn.querySelector('mat-icon');
        if (icone) {
            icone.className = icone.className.replace(/\bfa-[a-z0-9-]+\b/, 'fa-folder-open');
        }
        definirRotulo(btn, TEXTO_PADRAO);
        btn.addEventListener('click', function () { aoClicar(btn); });
        return btn;
    }

    function injetarBotao() {
        if (!hostSisbajud() || !document.body) return;
        var existente = document.getElementById(ID_BOTAO);

        if (!naRotaMinuta()) {
            if (existente) existente.remove();
            return;
        }

        var destino = containerAcoes();
        if (existente) {
            if (destino && existente.parentNode === destino) { reaplicarDestaques(); return; }
            if (!destino && existente.getAttribute('data-pjetools-fixo') === '1') { reaplicarDestaques(); return; }
            existente.remove();
        }

        var btn = montarBotao();
        if (destino) {
            destino.appendChild(btn); // entra depois de "Consultar", dentro de .uikit-actions
            btn.setAttribute('data-pjetools-no-divisor', '1');
        } else {
            // reserva: só se o divisor ainda não existir no DOM
            btn.setAttribute('data-pjetools-fixo', '1');
            btn.style.cssText = 'position:fixed;top:14px;right:20px;z-index:999999;' +
                'padding:10px 18px;border:none;border-radius:8px;background:#2e7d32;color:#fff;' +
                'font:bold 14px Arial,sans-serif;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,0.3);';
            document.body.appendChild(btn);
        }
        console.log('[SisbAbrirMinutas] botão injetado ' +
            (destino ? 'no divisor de ações' : 'flutuante (divisor ausente)') +
            ' | radioJuiz=' + radioJuizSelecionado() + ' linhas=' + linhasTabela().length);
        reaplicarDestaques();
    }

    // Escuta cliques em "Consultar" para reagir rápido após a tabela carregar
    function observarCliqueConsultar() {
        if (!hostSisbajud()) return;
        document.addEventListener('click', function (ev) {
            if (!naRotaMinuta()) return;
            var b = ev.target && ev.target.closest ? ev.target.closest('button') : null;
            if (!b) return;
            var t = norm(b.textContent).toLowerCase();
            if (t.indexOf('consultar') > -1) {
                setTimeout(injetarBotao, 800);
                setTimeout(injetarBotao, 1800);
            }
        }, true);
    }

    if (hostSisbajud()) {
        instalarInterceptador();
        observarCliqueConsultar();
        // injeta cedo em /minuta (o orquestrador também chama a cada 1,5 s)
        setTimeout(injetarBotao, 600);
        setTimeout(injetarBotao, 1800);
    }

    window.SisbAbrirMinutas = {
        injetarBotao: injetarBotao,
        resetarAbertos: function () {
            idsAbertos.clear();
            procsAbertos.clear();
            ultimoLoteIds.clear();
        },
    };

    console.log('[SisbAbrirMinutas] módulo carregado em', location.host + location.pathname,
        '| api?', typeof window.SisbAbrirMinutas);
})();
