/* =====================================================================
 * PJe Tools Pro — Marcador do dia da semana da audiência em /detalhe
 * ---------------------------------------------------------------------
 * Por que este arquivo existe separado do Aud.core.js:
 *
 *   O Aud.core.js é um módulo da ROTA /aud. Tanto lá quanto no Aud.js, o
 *   `init()` aborta fora de /aud e o loader só chama `PJeAud.init()` quando
 *   `isRouteAud()` é verdadeiro. A função `isRouteDetalhe()` existe nos dois
 *   arquivos mas NUNCA é usada -- é código morto. Resultado: qualquer coisa
 *   colocada dentro de `renderizarPainel()` jamais executa em /detalhe.
 *
 *   Este módulo roda por conta própria, injetado pelo pjetools.user.js via
 *   @require, e só age quando a URL é de /detalhe.
 *
 * O que faz:
 *   Acha no cabeçalho do processo o <dd> que descreve a audiência:
 *
 *     <dd class="campo-informacao-icone ng-star-inserted">
 *         Dia 17/12/2026 às 08:30 - Una por videoconferência ... - Sala Principal
 *     </dd>
 *
 *   e insere logo APÓS ele um marcador com o dia da semana:
 *
 *     📅 Quinta-feira
 *
 *   Se não houver audiência marcada, nada é inserido.
 * ===================================================================== */
(function () {
    'use strict';

    var LOG = '[Aud.detalhe]';
    var MARCA = 'data-pjetools-dia-aud';
    var SELECTOR_DD = 'dd.campo-informacao-icone';

    var DIAS_SEMANA = [
        'Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira',
        'Quinta-feira', 'Sexta-feira', 'Sábado'
    ];

    function log() {
        try {
            var partes = Array.prototype.slice.call(arguments);
            partes.unshift(LOG);
            console.log.apply(console, partes);
        } catch (e) {}
    }

    function warn() {
        try {
            var partes = Array.prototype.slice.call(arguments);
            partes.unshift(LOG);
            console.warn.apply(console, partes);
        } catch (e) {}
    }

    function isRouteDetalhe() {
        var href = window.location.href || '';
        return href.indexOf('/detalhe') !== -1;
    }

    /** "Dia 17/12/2026 às 08:30 - Una..." -> {nome:'Quinta-feira', data:Date}. */
    function diaDaSemana(texto) {
        if (!texto) return null;
        var d = null, m = null, y = null;
        var hit = /(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(texto);
        if (hit) {
            d = +hit[1]; m = +hit[2]; y = +hit[3];
        } else {
            hit = /(\d{4})-(\d{1,2})-(\d{1,2})/.exec(texto);
            if (hit) { y = +hit[1]; m = +hit[2]; d = +hit[3]; }
        }
        if (!y) return null;
        var dt = new Date(y, m - 1, d);
        // Rejeita data inexistente (ex.: 31/02/2027)
        if (isNaN(dt.getTime()) || dt.getDate() !== d || dt.getMonth() !== m - 1) return null;
        return { nome: DIAS_SEMANA[dt.getDay()], dia: dt.getDay(), data: dt };
    }

    /** Acha o <dd> da audiência no cabeçalho do processo. */
    function acharDdAudiencia() {
        var dds = document.querySelectorAll(SELECTOR_DD);
        for (var i = 0; i < dds.length; i++) {
            var t = dds[i].textContent || '';
            if (/Dia\s+\d{1,2}\/\d{1,2}\/\d{4}/.test(t)) return dds[i];
        }
        return null;
    }

    function removerMarcadores() {
        var antigos = document.querySelectorAll('[' + MARCA + ']');
        for (var i = 0; i < antigos.length; i++) {
            try { antigos[i].remove(); } catch (e) {}
        }
    }

    /**
     * Cria o marcador (um <dd>, para ficar alinhado com a lista do cabeçalho)
     * e o insere logo após o <dd> da audiência.
     */
    function inserirMarcador(dd, nomeDia) {
        var marca = document.createElement('dd');
        marca.setAttribute(MARCA, '1');
        marca.className = 'campo-informacao-icone';
        marca.style.cssText = 'color:#1e40af;font-weight:bold;';

        var icone = document.createElement('i');
        icone.className = 'fa fa-calendar';
        icone.setAttribute('aria-hidden', 'true');
        icone.style.marginRight = '6px';

        marca.appendChild(icone);
        marca.appendChild(document.createTextNode(nomeDia));

        // Insertamos logo depois do <dd> da audiência: é o lugar pedido
        if (dd.nextSibling) {
            dd.parentNode.insertBefore(marca, dd.nextSibling);
        } else {
            dd.parentNode.appendChild(marca);
        }
        return marca;
    }

    /** Uma passada: garante o marcador coerente com o que está na tela. */
    function atualizar(origem) {
        var dd = acharDdAudiencia();
        if (!dd) {
            // Sem audiência é o caso comum; avisar a cada tentativa só suja o
            // console. Loga uma vez por ciclo e segue silencioso.
            if (!_avisouSemDd) {
                _avisouSemDd = true;
                log('[tentativa ' + origem + '] nenhum <dd> de audiência (sem audiência marcada?)');
            }
            removerMarcadores();
            return false;
        }
        _avisouSemDd = false;

        var texto = (dd.textContent || '').replace(/\s+/g, ' ').trim();
        var info = diaDaSemana(texto);
        log('[' + origem + '] dd encontrado:', JSON.stringify(texto.slice(0, 100)));
        log('[' + origem + '] diaDaSemana() =', info ? info.nome : null);

        if (!info) {
            warn('[' + origem + '] não consegui extrair a data desse <dd>');
            removerMarcadores();
            return false;
        }

        var atual = document.querySelector('[' + MARCA + ']');
        var textoAtual = atual ? (atual.textContent || '').trim() : '';

        // Já está correto e no lugar: nada a fazer
        if (atual && textoAtual === info.nome && atual.previousSibling === dd) {
            log('[' + origem + '] marcador já está correto:', info.nome);
            return true;
        }

        removerMarcadores();
        var novo = inserirMarcador(dd, info.nome);
        log('[' + origem + '] ✅ marcador inserido:', JSON.stringify(novo.textContent));
        return true;
    }

    // ── agendamento das tentativas ──────────────────────────────────────
    // O Angular renderiza o cabeçalho depois do load, e o usuário pode trocar
    // de processo sem recarregar a página. Por isso: tentativas curtas no
    // início e um observador que detecta troca de conteúdo da <dl>.
    var _tentativas = 0;
    var _timer = null;
    var _observador = null;
    var _avisouSemDd = false;
    var MAX_TENTATIVAS = 2;

    function pararTentativas() {
        if (_timer) { clearInterval(_timer); _timer = null; }
    }

    function iniciarTentativas() {
        pararTentativas();
        _tentativas = 0;
        _avisouSemDd = false;
        _timer = setInterval(function () {
            _tentativas++;
            var ok = atualizar('tentativa ' + _tentativas);
            if (ok || _tentativas >= MAX_TENTATIVAS) {
                log('tentativas encerradas após', _tentativas, '| sucesso =', ok);
                pararTentativas();
            }
        }, 500);
    }

    function observarCabecalho() {
        if (_observador || typeof MutationObserver === 'undefined') return;

        var _ultimoTexto = null;
        _observador = new MutationObserver(function () {
            var dd = acharDdAudiencia();
            var t = dd ? (dd.textContent || '') : '';
            if (t === _ultimoTexto) return;
            _ultimoTexto = t;
            log('mudança no cabeçalho detectada; reavaliando');
            atualizar('mutação');
        });

        try {
            _observador.observe(document.body, { childList: true, subtree: true });
            log('observador de mutações instalado');
        } catch (e) {
            warn('falha ao instalar o observador:', e.message);
        }
    }

    function iniciar() {
        if (window.__pjeAudDetalheIniciado) {
            log('já iniciado anteriormente; reavaliando apenas');
            atualizar('reinicio');
            return;
        }
        window.__pjeAudDetalheIniciado = true;

        log('=== módulo carregado ===');
        log('href =', window.location.href);

        if (!isRouteDetalhe()) {
            warn('rota não é /detalhe -> nada a fazer');
            return;
        }
        log('rota /detalhe confirmada; procurando o <dd> da audiência');

        atualizar('imediato');
        iniciarTentativas();
        observarCabecalho();
    }

    // Exposto para o loader (bootDetalhe) e para inspeção manual no console
    window.PjeAudDetalhe = {
        iniciar: iniciar,
        atualizar: atualizar,
        diaDaSemana: diaDaSemana,
        acharDdAudiencia: acharDdAudiencia
    };

    // Fallback: se o loader não chamar iniciar(), dispara sozinho na rota certa.
    function autoIniciar() {
        if (isRouteDetalhe()) iniciar();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoIniciar, { once: true });
    } else {
        autoIniciar();
    }
})();
