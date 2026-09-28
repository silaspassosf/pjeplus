// ==UserScript==
// @name         PJe Suite1
// @namespace    pjetools
// @version      1.0.0
// @description  Orquestrador enxuto: Elaboração de Alvará + Argos + Homologação de Cálculos (hcalc)
// @author       Silas
// @updateURL    https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/suite1.user.js
// @downloadURL  https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/suite1.user.js

// ── PJe: detalhe do processo (Alvará + hcalc + pilar do Argos)
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @match        https://pje.trt*.jus.br/pjekz/processo/*/detalhe*
// ── PJe: rota do ARGOS (onde o Argos retoma o fluxo e finaliza)
// @match        https://pje.trt2.jus.br/argos/*
// @match        https://pje.trt*.jus.br/argos/*
// ── Alvará Eletrônico (botão "Extrair saldo" em contas judiciais)
// @match        https://alvaraeletronico.trt2.jus.br/*

// ── Grants: SUPERSET de tudo que os módulos carregados exigem individualmente
//    (alv.user.js: GM_xmlhttpRequest + unsafeWindow; argos.js: GM_setValue/getValue/deleteValue + window.close)
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_deleteValue
// @grant        GM_xmlhttpRequest
// @grant        window.close
// @grant        unsafeWindow

// ── Connects = união dos @connect dos sub-orquestradores (alv.user.js + hcalc.user.js)
// @connect      raw.githubusercontent.com
// @connect      aplicacoes1.trt2.jus.br
// @connect      pje.trt2.jus.br
// @connect      cdnjs.cloudflare.com
// @connect      unpkg.com
// @connect      cdn.jsdelivr.net
// @run-at       document-idle

// ═══════════════════════════════════════════════════════════════════════════
// ATENÇÃO — LEIA ANTES DE EDITAR A LISTA DE @require
// ═══════════════════════════════════════════════════════════════════════════
// O Tampermonkey NÃO resolve @require aninhado: um arquivo puxado via @require
// é tratado como biblioteca JS pura e o header ==UserScript== dele é IGNORADO.
// Por isso o pool de dependências de alv.user.js e hcalc.user.js está
// REDECLARADO aqui, na ordem correta de dependência.
//
// Consequência prática:
//   - Ao adicionar/remover módulo em alv.user.js ou hcalc.user.js, replique aqui.
//   - hcalc.user.js NÃO é exigido: o corpo dele é só "esperar o PJe ficar
//     pronto e chamar window.hcalcInitBotao()" — replicado em aguardarPJe().
//     Exigi-lo apenas adicionaria uma camada com guard próprio (data-hcalc-boot)
//     e concorreria com o boot daqui.
//   - alv.user.js É exigido: é o único arquivo que define window.PjeAlvara.
//     NÃO remova os módulos do pool acima — o TM não os traria sozinho.
//
// Sobre as versões (?v=): mantidas IDÊNTICAS às dos sub-orquestradores para que
// o cache do TM seja reaproveitado (sem download duplicado) e não exista estado
// de "versão mista". Ao publicar release de módulo, bumpe aqui também.
// ═══════════════════════════════════════════════════════════════════════════

// ── CDNs compartilhadas (pdf.js + Tesseract usados por core/extrair.js e hcalc-pdf.js)
//    OBS: pdf-lib NÃO é necessário — só pdf.compress.js (módulo PDF) o usa.
// @require      https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js
// @require      https://unpkg.com/tesseract.js@5.1.1/dist/tesseract.min.js

// ── Primitivas do core: sleep / showToast / waitElementVisible / normalizeText /
//    parseMoney — consumidas pelo argos.js (todas têm fallback interno, mas sem
//    elas o Argos loga em console em vez de exibir toast ao usuário).
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/utils.js?v=2.1.70
// ── Extrator universal (window.pjeExtrair) — extrator PRIMÁRIO de
//    Script/alvara/extracao.js (que só cai no fallback local se ele faltar).
//    Depende de pdf.js + Tesseract, já declarados acima.
//    OBS: core/state.js NÃO é carregado — nenhum dos três módulos usa PJeState;
//    ele só serve ao painel.js genérico, que ficou fora do Suite1.
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/extrair.js?v=2.3.23

// ── MÓDULO 1 — Elaboração de Alvará (pacote window.Alv + boot do botão)
//    Ordem obrigatória: utils → extracao → dados/estado → estilos → overlay →
//    siscon → siscondj → minuta → boot.
//    Nenhum módulo lê Alv.* no top-level (só em tempo de chamada), logo a ordem
//    acima é segura; ela é mantida igual à do alv.user.js.
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/utils.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/extracao.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/dados_processo.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/estado.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/estilos.js?v=4
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/overlay.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/siscon_consulta.js?v=4
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/extracao_siscondj.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/minuta.js?v=3
// ── Alvará Eletrônico: botão "Extrair saldo" (auto-injeta na página de contas)
//    Autocontido: só registra Alv.saldo / window.PjeAlvaraSaldo e injeta o
//    próprio botão. Fica aqui (antes do boot) para que TODO o pacote
//    Script/alvara/* esteja carregado quando alv.user.js rodar.
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/saldo_extracao.js?v=2.1.1

// ── Boot do Alvará — alv.user.js (fecha o pool acima e traz a API).
//    Por que ESTE arquivo é exigido, ao contrário do hcalc.user.js:
//    o Tampermonkey ignora o @require ANINHADO dele, mas EXECUTA o corpo
//    IIFE normalmente — e é esse corpo que define window.PjeAlvara
//    (abrir / criarBotao / extrairValores) e injeta/reinjeta o botão
//    "Alvará" na toolbar. Nenhum arquivo de Script/alvara/*.js cria
//    window.PjeAlvara. Sem ele, o painel do Suite1 não tem o que chamar.
//    ORDEM IMPORTA: vem depois do pool acima, pois o corpo lê
//    Alv.extracao / Alv.estado / Alv.minuta / Alv.siscon no top-level.
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/alv.user.js

// -- MÓDULO 2 — Argos (botão "Nova Pesquisa" no ARGOS a partir do processo)
//    Rota /argos/*: tem boot PRÓPRIO (window.executarArgos + _boot que lê o
//    checkpoint no GM/sessionStorage) — o Suite1 não precisa orquestrar nada.
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/argos/argos.js?v=2.3.1

// ── MÓDULO 3 — Homologação de Cálculos (hcalc) — módulos do hcalc.user.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-core.js?v=3179&t=202608290040
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-pdf.js?v=3180&t=202608290040
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-prep.js?v=3181&t=202608290040
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-draft.js?v=3179&t=202608290040
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-depositos.js?v=3179&t=202608290040
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-responsabilidades.js?v=3179&t=202608290040
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-partes.js?v=3181&t=202608290040
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay-decisao.js?v=3179&t=202608290040
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/calc/BASE/hcalc-overlay.js?v=3181&t=202609021030
// ==/UserScript==

/* PJe Suite1 — orquestrador enxuto
 * =====================================================================
 * Versão cirúrgica do pjetools.user.js: em vez dos ~30 módulos, carrega
 * apenas os três de uso diário.
 *
 *   1) Alvará  — elaboração de alvará a partir da decisão (/detalhe)
 *                + "Extrair saldo" no Alvará Eletrônico
 *   2) Argos   — abre "Nova Pesquisa" no ARGOS e finaliza ao voltar
 *   3) hcalc   — homologação de cálculos (/detalhe)
 *
 * O QUE NÃO ESTÁ AQUI (por design): lista, atalhos, simba, sisbajud,
 * aud, infojud, pdf, débito e o painel genérico de Script/ui/painel.js.
 * O painel do Suite1 (abaixo) tem apenas os 3 botões e não depende de
 * PJeState / invalidarCacheTimeline / executarEdital.
 *
 * Módulos e boot (ver o comentário longo antes da lista de @require):
 *   - o pool de dependências de alv.user.js e hcalc.user.js está
 *     REDECLARADO no header, porque o TM não resolve @require aninhado;
 *   - alv.user.js é exigido (fecha o pool) — é o único lugar que define
 *     window.PjeAlvara; o hcalc.user.js NÃO é exigido, pois o corpo dele é
 *     só "esperar o PJe e chamar hcalcInitBotao()", replicado aqui;
 *   - botão do Alvará na toolbar: vem do próprio alv.user.js, com o botão
 *     do Suite1 apenas como segundo caminho (idempotente);
 *   - botão do hcalc na toolbar: injetado no load de /detalhe (paridade com
 *     hcalc.user.js) e reinicializável pelo painel — idempotente via
 *     window.__hcalcBotaoInitialized.
 * =====================================================================
 */
(function () {
    'use strict';

    const VERSION = '1.0.0';

    // ── Guard de instância (evita dupla execução em F5 / recarga do TM) ──
    const INSTANCE_KEY = '__PJE_SUITE1_INSTANCE__';
    if (window[INSTANCE_KEY]) {
        console.warn('[Suite1] segunda execução ignorada:', location.href);
        return;
    }
    window[INSTANCE_KEY] = { version: VERSION, startedAt: new Date().toISOString() };

    // ── Anti-iframe: nenhum dos três módulos opera dentro de iframe ──
    if (window.self !== window.top) return;

    const W = (typeof unsafeWindow !== 'undefined') ? unsafeWindow : window;

    const PAINEL_ID = 'suite1-painel';
    const CSS_ID = 'suite1-style';

    // Estado de UI: painel fechado pelo usuário. Volta a aparecer quando a
    // rota muda de verdade (outro processo / outra tela do PJe).
    let painelOculto = false;

    // ── API dos módulos: @require registra no sandbox `window`; alguns pontos
    //    expõem em unsafeWindow (W). Consulta os dois, como faz o pjetools. ──
    function api(nome) {
        return (typeof window[nome] !== 'undefined') ? window[nome] : W[nome];
    }

    function toast(texto, cor) {
        const show = api('showToast');
        if (typeof show === 'function') {
            show(texto, cor || '#dc3545', 3000);
        } else {
            console.log('[Suite1]', texto);
        }
    }

    function moduloAusente(nomeModulo) {
        toast('Módulo ' + nomeModulo + ' não carregado', '#dc3545');
    }

    // ═══════════════════════════════════════════════════════════════════
    // PAINEL — 3 botões, arrastável, canto inferior direito
    // ═══════════════════════════════════════════════════════════════════
    const CSS_PAINEL = `
        #${PAINEL_ID} {
            position: fixed; bottom: 170px; right: 20px; z-index: 99999;
            background: #ffffff; border: 1px solid #d0d7de; border-radius: 10px;
            box-shadow: 0 10px 30px rgba(15,23,42,.22);
            padding: 10px 12px 11px; font-family: Inter, "Segoe UI", Arial, sans-serif;
            min-width: 196px; user-select: none;
        }
        #${PAINEL_ID} .suite1-titulo {
            display: flex; align-items: center; justify-content: space-between;
            gap: 8px; cursor: move; margin-bottom: 8px; padding-bottom: 7px;
            border-bottom: 1px solid #eef1f4;
        }
        #${PAINEL_ID} .suite1-nome {
            font-size: 11px; font-weight: 700; letter-spacing: .04em;
            text-transform: uppercase; color: #475569;
        }
        #${PAINEL_ID} .suite1-fechar {
            border: none; background: transparent; cursor: pointer; padding: 0 2px;
            font-size: 14px; line-height: 1; color: #94a3b8; border-radius: 4px;
        }
        #${PAINEL_ID} .suite1-fechar:hover { color: #dc2626; }
        #${PAINEL_ID} .suite1-grid {
            display: grid; grid-template-columns: 1fr; gap: 6px;
        }
        #${PAINEL_ID} .suite1-btn {
            padding: 8px 10px; border: none; border-radius: 6px; cursor: pointer;
            font-family: inherit; font-size: 12px; font-weight: 700; color: #fff;
            text-align: left; transition: filter .15s, transform .1s;
        }
        #${PAINEL_ID} .suite1-btn:hover { filter: brightness(1.08); }
        #${PAINEL_ID} .suite1-btn:active { transform: scale(.985); }
        #${PAINEL_ID} .suite1-btn:disabled { opacity: .55; cursor: default; }
    `;

    function addStyles(css, id) {
        const adicionar = api('addStyles');
        if (typeof adicionar === 'function') {
            adicionar(css, id);
            return;
        }
        if (document.getElementById(id)) return;
        const s = document.createElement('style');
        s.id = id;
        s.textContent = css;
        document.head.appendChild(s);
    }

    function botao(painel, def) {
        const b = document.createElement('button');
        b.id = def.id;
        b.type = 'button';
        b.className = 'suite1-btn';
        b.textContent = def.texto;
        b.title = def.titulo;
        b.style.background = def.bg;
        b.addEventListener('click', async event => {
            event.preventDefault();
            event.stopPropagation();
            const alvo = api(def.api);
            const fn = def.metodo
                ? (alvo && typeof alvo[def.metodo] === 'function' ? alvo[def.metodo].bind(alvo) : null)
                : (typeof alvo === 'function' ? alvo : null);
            if (!fn) {
                moduloAusente(def.modulo);
                return;
            }
            b.disabled = true;
            try {
                await fn();
            } catch (e) {
                console.error('[Suite1] erro em ' + def.modulo + ':', e);
                toast(def.modulo + ': ' + (e && e.message ? e.message : e), '#dc3545');
            } finally {
                b.disabled = false;
            }
        });
        painel.appendChild(b);
        return b;
    }

    function tornaArrastavel(el) {
        const alca = el.querySelector('.suite1-titulo');
        if (!alca) return;

        let ox = 0, oy = 0, arrastando = false;

        const onDown = e => {
            if (e.target.classList.contains('suite1-fechar')) return;
            arrastando = true;
            ox = e.clientX - el.offsetLeft;
            oy = e.clientY - el.offsetTop;
            e.preventDefault();
        };
        const onMove = e => {
            if (!arrastando) return;
            el.style.left = (e.clientX - ox) + 'px';
            el.style.top = (e.clientY - oy) + 'px';
            el.style.right = 'auto';
            el.style.bottom = 'auto';
        };
        const onUp = () => { arrastando = false; };

        alca.addEventListener('mousedown', onDown);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }

    function criarPainel() {
        if (document.getElementById(PAINEL_ID)) return;
        if (!document.body) return;
        // O roteador roda a cada frame de mutação: sem esta flag, fechar o
        // painel seria inútil (ele voltaria no frame seguinte).
        if (painelOculto) return;

        addStyles(CSS_PAINEL, CSS_ID);

        const painel = document.createElement('div');
        painel.id = PAINEL_ID;

        const cabecalho = document.createElement('div');
        cabecalho.className = 'suite1-titulo';

        const nome = document.createElement('span');
        nome.className = 'suite1-nome';
        nome.textContent = 'PJe Suite1';

        const fechar = document.createElement('button');
        fechar.type = 'button';
        fechar.className = 'suite1-fechar';
        fechar.textContent = '\u00d7';
        fechar.title = 'Ocultar painel';
        fechar.addEventListener('click', ev => {
            ev.preventDefault();
            ev.stopPropagation();
            painelOculto = true;
            painel.remove();
        });

        cabecalho.appendChild(nome);
        cabecalho.appendChild(fechar);
        painel.appendChild(cabecalho);

        const grid = document.createElement('div');
        grid.className = 'suite1-grid';
        painel.appendChild(grid);

        botao(grid, {
            id: 'suite1-btn-alvara', texto: '\u2696\uFE0F Alvará', bg: '#16a34a',
            titulo: 'Analisar a decisão ativa e preparar os alvarás',
            api: 'PjeAlvara', metodo: 'abrir', modulo: 'Alvará',
        });

        botao(grid, {
            id: 'suite1-btn-argos', texto: '\u2696\uFE0F Argos', bg: '#6f42c1',
            titulo: 'Abrir "Nova Pesquisa" no ARGOS a partir deste processo',
            api: 'executarArgos', modulo: 'Argos',
        });

        botao(grid, {
            id: 'suite1-btn-hcalc', texto: '\uD83E\uDDEE hcalc', bg: '#00509e',
            titulo: 'Homologação de cálculos: injetar/restaurar o botão de planilha',
            api: 'hcalcInitBotao', modulo: 'hcalc',
        });

        tornaArrastavel(painel);
        document.body.appendChild(painel);
    }

    // ═══════════════════════════════════════════════════════════════════
    // BOOT dos módulos que precisam de gatilho externo
    // ═══════════════════════════════════════════════════════════════════

    // ── hcalc: o Script/hcalc.user.js só fazia "esperar o PJe e chamar
    //    hcalcInitBotao()". Aqui a espera é por MutationObserver (sem polling
    //    de intervalo fixo), com timeout de segurança. ──
    function aguardarPJe(cb, timeout) {
        const SEL = 'pje-cabecalho, li.tl-item-container, [class*="processo"]';

        if (document.querySelector(SEL)) { cb(); return; }
        if (!document.documentElement) { setTimeout(cb, 500); return; }

        let obs = null;
        const finalizar = () => { if (obs) { obs.disconnect(); obs = null; } };

        obs = new MutationObserver(() => {
            if (document.querySelector(SEL)) { finalizar(); cb(); }
        });
        obs.observe(document.documentElement, { childList: true, subtree: true });

        setTimeout(() => {
            if (obs) { finalizar(); cb(); } // timeout: tenta mesmo assim
        }, timeout || 15000);
    }

    function bootHcalc() {
        const init = api('hcalcInitBotao');
        if (typeof init !== 'function') {
            console.error('[Suite1] hcalcInitBotao indisponível — verifique os @require de calc/BASE/*.js');
            return;
        }
        aguardarPJe(() => {
            try {
                init();
                console.log('[Suite1] hcalc inicializado.');
            } catch (e) {
                console.error('[Suite1] erro ao inicializar hcalc:', e);
            }
        });
    }

    // ── Alvará: o boot inicial (botão + observer + re-injeção em SPA) é feito
    //    pelo próprio corpo do alv.user.js, exigido no header. Esta chamada é
    //    só rede de segurança para remontagens de toolbar que o observer dele
    //    não pegue; criarBotao() é idempotente (sai cedo se o botão já existe). ──
    function bootAlvara() {
        const alvara = api('PjeAlvara');
        if (!alvara || typeof alvara.criarBotao !== 'function') {
            // O roteador chama isto a cada frame de mutação: avisa só uma vez.
            if (!bootAlvara.avisado) {
                bootAlvara.avisado = true;
                console.warn('[Suite1] PjeAlvara.criarBotao indisponível — pacote ao lado de alv.user.js carregou?');
            }
            return;
        }
        try {
            alvara.criarBotao();
        } catch (e) {
            console.error('[Suite1] erro ao injetar botão do Alvará:', e);
        }
    }

    function ehPaginaDetalhe() {
        return /\/processo\/\d+\/detalhe/.test(location.pathname);
    }

    // ═══════════════════════════════════════════════════════════════════
    // ROTEAMENTO SPA — só o necessário para os 3 módulos
    // ═══════════════════════════════════════════════════════════════════
    function rotear() {
        // /argos/* — nada a fazer: argos.js tem boot próprio (_boot lê o
        // sessionStorage e retoma o fluxo ou o checkpoint de finalização).
        if (ehPaginaDetalhe()) {
            criarPainel();
            // O Angular remonta a toolbar ao navegar entre processos: sem
            // reinjetar, o botão do Alvará sumiria. criarBotao() é idempotente
            // (retorna cedo se já existe), então chamar aqui é barato.
            bootAlvara();
            return;
        }
        document.getElementById(PAINEL_ID)?.remove();
    }

    function iniciarRoteamento() {
        let ultimaUrl = location.href;
        let agendado = false;

        // Coalesce: o MutationObserver dispara em rajada (SPA Angular pesado).
        // Só um roteamento por frame, no máximo.
        const agendar = () => {
            if (agendado) return;
            agendado = true;
            requestAnimationFrame(() => { agendado = false; rotear(); });
        };

        const aoMudarRota = () => {
            if (location.href === ultimaUrl) {
                // Mesma rota: só re-injeta o que o Angular tenha removido.
                agendar();
                return;
            }
            ultimaUrl = location.href;
            painelOculto = false; // rota nova: o painel volta a se oferecer
            setTimeout(agendar, 300); // deixa o Angular montar a nova tela
        };

        // Canal oficial do core para SPA Angular
        const monitor = api('monitorarSPA');
        if (typeof monitor === 'function') monitor(aoMudarRota);

        // Rede de segurança: rotas internas do PJe nem sempre passam por
        // pushState. Observa mutações (event-driven) em vez de polling de DOM.
        if (document.documentElement) {
            new MutationObserver(aoMudarRota).observe(document.documentElement, {
                childList: true, subtree: true
            });
        }

        rotear();
    }

    // ═══════════════════════════════════════════════════════════════════
    // ENTRADA
    // ═══════════════════════════════════════════════════════════════════
    console.log('[Suite1] PJe Suite1 v' + VERSION + ' carregado —', location.href);

    if (ehPaginaDetalhe()) {
        bootAlvara();
        bootHcalc();
    }

    iniciarRoteamento();

    // Diagnóstico no console: deixa claro o que carregou e o que faltou.
    console.log('[Suite1] módulos — Alvará:', typeof api('PjeAlvara'),
        '| Argos:', typeof api('executarArgos'),
        '| hcalc:', typeof api('hcalcInitBotao'),
        '| saldo:', typeof api('PjeAlvaraSaldo'));
})();
