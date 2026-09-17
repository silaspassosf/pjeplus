# AUD - Arquivos Consolidados

## pjetools.user.js

```javascript
// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      2.4.0
// @description  Suite de ferramentas para PJe
// @author       Silas
// @updateURL    https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/pjetools.user.js
// @downloadURL  https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/pjetools.user.js
// ── PJe (cobre todas as rotas com um único match)
// @match        https://pje.trt2.jus.br/aud/*
// @match        https://pje.trt2.jus.br/*
// @match        https://pje.trt2.jus.br/pjekz/*
// @match        https://pje.trt2.jus.br/primeirograu/*
// @match        https://pje.trt2.jus.br/segundograu/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
// @match        https://simba-novo.redejt/*
// @match        https://www3.bcb.gov.br/saj/requisicao-extratos-cadastro*
// ── Alvará Eletrônico (módulo saldo_extracao)
// @match        https://alvaraeletronico.trt2.jus.br/*
// ── eCarta (módulo carta — botões Últimas/Antigas com auditoria de falsos positivos)
// @match        https://aplicacoes1.trt2.jus.br/eCarta-web/*
// ── Único require: o loader (bumpar só ele ao adicionar módulos)
// (loader injetado inline — remove dependência externa)
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_deleteValue
// @grant        GM_openInTab
// @grant        GM_xmlhttpRequest
// @grant        window.close
// @grant        unsafeWindow
// @grant        GM_setClipboard
// @connect      raw.githubusercontent.com
// @connect      consultadecep.com
// @connect      viacep.com.br
// @connect      brasilapi.com.br
// @connect      brasilcep.dev
// @connect      aplicacoes1.trt2.jus.br
// @run-at       document-idle
// ── pdf.js no sandbox do userscript (mesma técnica do hcalc.user.js:
// a injeção dinâmica via <script> é bloqueada pelo CSP da página)
// @require      https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js
// @require      https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js
// @require      https://unpkg.com/tesseract.js@5.1.1/dist/tesseract.min.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/utils.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/state.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/extrair.js?v=2.3.21
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.check.js?v=2.3.50
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.edital.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.pgto.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.worker.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/ui/painel.js?v=2.3.85
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/infojud/infojud.js?v=2.1.80
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/core.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/relatorios.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/sisbajud.js?v=2.1.79
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/sisbpje.js?v=2.3.19
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/extracao_siscondj.js?v=2.1.2
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/siscon_consulta.js?v=2.1.12
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/saldo_extracao.js?v=2.1.1
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/carta/carta.js?v=2.1.0
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/simba/simba.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/debito/registrar_debito.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/argos/argos.js?v=2.3.1
// ── AUD modularizado: DADOS (textos jurídicos) carregados ANTES da LÓGICA;
// Aud.js original permanece no repo como fallback, mas não é mais carregado.
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/Aud/Aud.data.js?v=1.0.1
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/Aud/Aud.core.js?v=2.3.92
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/Aud/marcar.js?v=1.3.4
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/pdf/pdf.compress.js?v=2.1.0
// ==/UserScript==

(async function () {
    'use strict';
    console.log('[Loader] PJe Tools Pro v2.2.0 loaded');

    const url = window.location.href;
    const isAud = url.includes('/aud') || (function () { try { return window.top && window.top.location.href.includes('/aud'); } catch (e) { return false; } })();

    // Módulos SISB carregados via @require (git), como os demais módulos.
    // Permite execução em iframes APENAS se for ambiente AUD
    if (window.self !== window.top && !isAud) return;

    // W = window real da página (unsafeWindow quando disponível)
    const W = (typeof unsafeWindow !== 'undefined') ? unsafeWindow : window;

    // ── Módulo AUD (carregado via @require de Script/modules/Aud/Aud.js) ──
    if (isAud) {
        if (window.PJeAud && typeof window.PJeAud.init === 'function') {
            window.PJeAud.init();
        }
    }
    const isReceita = url.includes('cav.receita.fazenda.gov.br');
    const isSisbajud = url.includes('sisbajud.cnj.jus.br') || url.includes('sisbajud.pdpj.jus.br');
    const isPjeDomain = url.includes('pje.trt2.jus.br') || url.includes('pje1g.trt2.jus.br');
    const isBcb = url.includes('bcb.gov.br/saj/requisicao-extratos-cadastro');

    // (No match da Receita, content scripts já estão via @require em header)
    if (isSisbajud) return;

    // ── Alvará Eletrônico (injeção do botão "Extrair saldo") ──
    // O módulo também se auto-injeta no @require; esta rota é rede de segurança
    // e fonte de diagnóstico no console (loga se o módulo carregou ou não).
    const isAlvaraEletronico = url.includes('alvaraeletronico.trt2.jus.br');
    if (isAlvaraEletronico) {
        console.log('[Loader] Alvará Eletrônico detectado:', url, '| PjeAlvaraSaldo:', typeof window.PjeAlvaraSaldo);
        const tentarAlv = function (restantes) {
            if (window.PjeAlvaraSaldo && typeof window.PjeAlvaraSaldo.injetarBotao === 'function') {
                window.PjeAlvaraSaldo.injetarBotao('loader');
            } else if (restantes > 0) {
                console.warn('[Loader] PjeAlvaraSaldo ainda indisponível — tentativas restantes:', restantes);
                setTimeout(function () { tentarAlv(restantes - 1); }, 1000);
            } else {
                console.error('[Loader] PjeAlvaraSaldo NÃO carregou — verifique o @require saldo_extracao.js no header do userscript');
            }
        };
        tentarAlv(5);
        return;
    }

    // ── Lógica BCB (terceira execução Simba) ──
    if (isBcb) {        console.log('[Loader] Detectada URL do BCB, carregando Simba BCB...');
        setTimeout(() => {
            if (!document.getElementById('btnSimbaBcbExtratos')) {
                const btn = document.createElement('button');
                btn.id = 'btnSimbaBcbExtratos';
                btn.textContent = '🦁 Preencher BCB';
                btn.title = 'Preencher automaticamente o formulário de requisição de extratos do BCB';
                btn.style.cssText = `position:fixed;bottom:20px;right:20px;z-index:999999999;
                    padding:10px 15px;background-color:#ff6600;color:white;border:none;
                    border-radius:4px;font-weight:bold;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,0.3);
                    font-size:14px;text-shadow:0 1px 2px rgba(0,0,0,0.3);`;

                btn.onclick = async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    btn.disabled = true;
                    btn.textContent = 'Processando...';
                    try {
                        await window.executarSimbaBcb?.();
                    } catch (err) {
                        console.error('[Loader BCB] Erro:', err);
                        alert('Erro ao preencher formulário BCB: ' + err.message);
                    }
                    btn.textContent = '🦁 Preencher BCB';
                    btn.disabled = false;
                };

                document.body.appendChild(btn);
                console.log('[Loader] Botão BCB criado com sucesso');
            }
        }, 800);
        return;
    }

    // ── Roteamento (roda depois de todos os @require carregados)
    if (isPjeDomain || isReceita) {

        // Se for Receita Federal (e-CAC), não roteamos aqui — o módulo carregado via @require
        // já executa sua Parte 2 quando a aba do e-CAC abre. Permitimos que o módulo aja.
        if (isReceita) return;
        // Dynamic loader removed: all modules must be provided via @require in the userscript header.

        // ── Monitoramento SPA global
        if (!window.__pjeToolsLoaded) {
            window.__pjeToolsLoaded = true;
            console.log('[Loader] Registrando monitor de SPA...');

            window.monitorarSPA && window.monitorarSPA(() => {
                console.log('[Loader] Navegação SPA detectada. Verificando rota...');
                setTimeout(rotear, 300);
            });
        }

        rotear();

        function rotear() {
            const currentUrl = window.location.href;
            const routeMinutas = currentUrl.includes('/comunicacoesprocessuais/minutas');
            const routeDetalhe = /\/processo\/\d+\/detalhe/.test(currentUrl);
            const routeObrigacao = currentUrl.includes('/obrigacao-pagar/');
            const routeAud = currentUrl.includes('/aud');
            const routeRetificar = /\/processo\/\d+\/retificar/.test(currentUrl);
            const routePauta = currentUrl.includes('/pauta-audiencias');

            if (routeRetificar) {
                if (window.PjeMarcarAud && window.PjeMarcarAud.initRetificar) {
                    window.PjeMarcarAud.initRetificar();
                }
                return;
            }

            if (routePauta) {
                if (window.PjeMarcarAud && window.PjeMarcarAud.initPauta) {
                    window.PjeMarcarAud.initPauta();
                }
                return;
            }

            if (routeMinutas) {
                if (window.__infojudWorkerRodando) return;
                window.__infojudWorkerRodando = true;
                console.log('[Loader] Iniciando Worker Infojud...');
                setTimeout(() => {
                    if (W.runInfojudWorker) {
                        W.runInfojudWorker();
                    }
                    window.__infojudWorkerRodando = false;
                }, 1500);
                return;
            }

            if (routeObrigacao) {
                setTimeout(() => {
                    try {
                        if (/\/obrigacao-pagar\/\d+\/cadastro/.test(currentUrl)) {
                            window.PjeRegistrarDebito?.onCadastro();
                        } else if (/\/obrigacao-pagar\/\d+\/inclusao/.test(currentUrl)) {
                            window.PjeRegistrarDebito?.onInclusao();
                        }
                    } catch (e) { }
                }, 1500);
                return;
            }

            if (routeAud) {
                console.log('[Loader] Detectado ambiente AUD:', window.location.href);
                window.__pjeAudFechadoManualmente = false;

                const tentarInitAud = () => {
                    const audApi = window.PJeAud || W.PJeAud;
                    if (typeof audApi?.init === 'function') {
                        audApi.init();
                    }
                };

                tentarInitAud();
                setTimeout(tentarInitAud, 500);
                setTimeout(tentarInitAud, 1500);
                return;
            }

            if (routeDetalhe) {
                if (window.PjeMarcarAud && window.PjeMarcarAud.checarConfirmacao) {
                    window.PjeMarcarAud.checarConfirmacao();
                }
                window.PJeState && window.PJeState.dispose && window.PJeState.dispose();
                bootDetalhe();
                return;
            }
        }

        function bootDetalhe() {
            if (!/\/processo\/\d+\/detalhe/.test(window.location.href)) {
                return;
            }
            // FIX: módulos registrados via @require expõem suas funções no sandbox `window`,
            // portanto chamamos `window.*` aqui em vez de `W` (unsafeWindow).
            if (!window.PJeState) {
                console.warn('[Loader] bootDetalhe: window.PJeState ainda não existe! Módulo state.js carregou?');
                return;
            }
            if (window.PJeState._iniciado) {
                console.log('[Loader] bootDetalhe: já inicializado anteriormente (PJeState._iniciado=true).');
                return;
            }
            window.PJeState._iniciado = true;
            console.log('[Loader] Inicializando painel e atalhos. inicializarPainel existe?', typeof window.inicializarPainel, '| initAtalhos existe?', typeof window.initAtalhos);
            window.inicializarPainel && window.inicializarPainel();
            window.initAtalhos && window.initAtalhos();
            window.__pjeAudFechadoManualmente = false;
            const audApi = window.PJeAud || W.PJeAud;
            if (typeof audApi?.init === 'function') {
                audApi.init();
            }
        }
    }
})();
```

## Aud.core.js

```javascript
(function() {
    console.log('[Aud.core.js] Script iniciado.');
    // Espera por window.AUD_DATA (Aud.data.js) — segurança para instalação
    // standalone; no pjetools a ordem dos @require já garante os dados.
    function aguardarDados(cb) {
        if (window.AUD_DATA) {
            console.log('[Aud.core.js] AUD_DATA encontrado, invocando callback.');
            return cb();
        }
        console.log('[Aud.core.js] Aguardando window.AUD_DATA...');
        setTimeout(function () { aguardarDados(cb); }, 50);
    }

    aguardarDados(function () {
        console.log('[Aud.core.js] Callback de aguardarDados disparado.');

        function isRouteAud() {
        return window.location.href.indexOf('/aud') !== -1;
    }

    function isRouteDetalhe() {
        var href = window.location.href;
        return href.indexOf('/detalhe') !== -1 || /\/processo\/\d+\/detalhe/.test(href);
    }

    function init(force) {
        console.log('[Aud.core.js] init() chamado. force:', force, '| Rota /aud:', isRouteAud());
        if (!force && !isRouteAud()) {
            console.log('[Aud.core.js] init() abortado: não forçado e fora da rota /aud');
            return;
        }
        if (!document.body) {
            console.log('[Aud.core.js] init() aguardando document.body...');
            setTimeout(function() { init(force); }, 300);
            return;
        }
        var topDoc = document;
        try {
            if (window.top && window.top.document) topDoc = window.top.document;
        } catch(e) {}
        var existing = document.getElementById('pjetools-aud-container') || (topDoc && topDoc.getElementById('pjetools-aud-container'));
        if (existing) {
            console.log('[Aud.core.js] init() abortado: painel (pjetools-aud-container) já existe no DOM.');
            window.__pjeAudFechadoManualmente = false;
            return;
        }
        console.log('[Aud.core.js] Criando painel. Coletando dados de AUD_DATA...');
        window.__pjeAudFechadoManualmente = false;

                var perfis = window.AUD_DATA.perfis;
        var S2 = window.AUD_DATA.S2;
        var PR = window.AUD_DATA.PR;
        var HH = window.AUD_DATA.HH;

var diaDaSemana = new Date().getDay(); // 0 = Dom, 1 = Seg, 2 = Ter, 3 = Qua, 4 = Qui, 5 = Sex, 6 = Sáb
        var perfilAtual = "";
        if (diaDaSemana === 1 || diaDaSemana === 2) {
            perfilAtual = "victor";
        } else if (diaDaSemana === 3 || diaDaSemana === 4) {
            perfilAtual = "otavio";
        }

        function renderizarPainel(perfilId, estaRetraido) {
            if (window.__pjeAudDomObs) {
                try { window.__pjeAudDomObs.disconnect(); } catch (e) {}
                window.__pjeAudDomObs = null;
            }
            console.log('[Aud.core.js] renderizarPainel() chamado. perfilId:', perfilId);
            var ex = document.getElementById('pjetools-aud-container');
            if (ex) {
                console.log('[Aud.core.js] Removendo container existente antes de renderizar novo');
                ex.remove();
            }

            if (typeof estaRetraido === 'undefined') {
                estaRetraido = false;
            }

            if (!perfilId) {
                console.log('[Aud.core.js] Sem perfilId. Chamando criarSeletor()');
                criarSeletor();
                return;
            }
            console.log('[Aud.core.js] Construindo painel para o perfil:', perfilId);

            var perfil = perfis[perfilId];
            var T = perfil.title;
            var S1 = perfil.S1;
            var S2_list = perfil.S2 || S2;
            var S3 = perfil.S3;
            var S4 = perfil.S4;
            var S5 = perfil.S5;

            function calcularTopMinimo() {
                var toolbar = document.querySelector('mat-toolbar.barra-ata, mat-toolbar, .barra-ata');
                if (toolbar) {
                    var rectT = toolbar.getBoundingClientRect();
                    return Math.max(65, Math.ceil(rectT.bottom + 8));
                }
                var btnEnviar = document.getElementById('enviarInformacoesParaPje');
                if (btnEnviar) {
                    var rectB = btnEnviar.getBoundingClientRect();
                    return Math.max(65, Math.ceil(rectB.bottom + 8));
                }
                var cabecalho = document.querySelector('app-ata-cabecalho, .header, .toolbar');
                if (cabecalho) {
                    var rectC = cabecalho.getBoundingClientRect();
                    return Math.max(65, Math.ceil(rectC.bottom + 8));
                }
                return 75;
            }

            var topMinimo = calcularTopMinimo();

            var P = document.createElement('div');
            P.id = 'pjetools-aud-container';
            P.style.cssText = 'position:fixed;top:' + topMinimo + 'px;right:10px;background:#fff;border:1px solid #c8d0ea;border-radius:10px;padding:8px 12px;z-index:2147483647;box-shadow:0 6px 24px rgba(30,50,130,.2);font-family:Arial,sans-serif;font-size:14px;box-sizing:border-box;user-select:none;transform-origin:top right;';

            // Mede o zoom REAL do navegador comparando o tamanho de um elemento
            // de referência em unidades físicas (1cm) com seu tamanho renderizado
            // em pixels CSS. Isso é imune a devicePixelRatio (não confunde DPI de
            // monitor com zoom do Ctrl +/-) e funciona igual em todos os navegadores.
            function medirZoomNavegador() {
                var ref = document.getElementById('__pjeAudZoomRef');
                if (!ref) {
                    ref = document.createElement('div');
                    ref.id = '__pjeAudZoomRef';
                    ref.style.cssText = 'position:absolute;visibility:hidden;pointer-events:none;width:1cm;height:1cm;top:-9999px;left:-9999px;';
                    document.body.appendChild(ref);
                }
                var pxPorCm = ref.getBoundingClientRect().width;
                // 1cm = 37.7952755906px em 96dpi sem zoom algum (referência CSS padrão).
                var zoom = pxPorCm / 37.7952755906;
                return (isFinite(zoom) && zoom > 0) ? zoom : 1;
            }

            // Aplica contra-escala: o painel sempre ocupa o mesmo tamanho FÍSICO em
            // tela (medido em cm/polegadas reais do monitor), independente do
            // zoom da página. transform-origin no canto ancorado evita que a
            // contra-escala desloque o elemento da posição calculada.
            function aplicarZoomComp() {
                try {
                    var zoom = medirZoomNavegador();
                    window.__pjeAudZoomAtual = zoom;
                    var contraEscala = 1 / zoom;
                    P.style.transform = (Math.abs(zoom - 1) < 0.02) ? 'none' : 'scale(' + contraEscala + ')';
                    P.dataset.zoomComp = String(contraEscala);
                } catch (e) {
                    P.style.transform = 'none';
                    P.dataset.zoomComp = '1';
                }
            }

            function fatorVisual() {
                return window.__pjeAudZoomAtual || medirZoomNavegador();
            }

            function posicionarAoLadoDoEditor() {
                var fator = fatorVisual();
                var larguraVisual = P.getBoundingClientRect().width || (P.offsetWidth * fator);
                var margem = 8;
                var margemDir = 4;
                var maxLeft = window.innerWidth - larguraVisual - margemDir;
                var alvo = null;
                var edRight = null;
                var ed = acharEditor();
                if (ed) {
                    try {
                        edRight = Math.ceil(ed.getBoundingClientRect().right);
                        alvo = edRight + margem;
                    } catch (e) { }
                }
                if (alvo === null) alvo = maxLeft;

                // Painel expandido: se o espaço vazio entre o editor e a borda
                // da tela for menor que o painel (zoom alto), REDUZ a largura
                // para caber — nunca invadindo o editor. Piso de 260px visuais;
                // abaixo disso, mantém o tamanho e apenas clampa. Restaura os
                // 380px quando o espaço voltar (zoom out).
                if (edRight !== null && !estaRetraido) {
                    var disponivel = window.innerWidth - edRight - margem - margemDir;
                    var nominalVisual = 380 * fator;
                    var PISO = 260;
                    if (disponivel >= PISO) {
                        var alvoVisual;
                        if (disponivel < larguraVisual) {
                            alvoVisual = disponivel;
                        } else if (larguraVisual < nominalVisual - 2 && disponivel >= nominalVisual) {
                            alvoVisual = nominalVisual;
                        } else {
                            alvoVisual = null;
                        }
                        if (alvoVisual !== null) {
                            // Com transform:scale(1/fator) aplicado ao painel, width em CSS já
                            // é multiplicado pela contra-escala visualmente. Para o resultado
                            // físico em tela ser exatamente "alvoVisual" pixels, a largura CSS
                            // deve ser alvoVisual * fator (compensando a contra-escala).
                            P.style.width = Math.floor(alvoVisual * fator) + 'px';
                            larguraVisual = alvoVisual;
                        }
                    } else if (!estaRetraido && !P.dataset.dragged) {
                        // Espaço insuficiente até para o piso mínimo: retrai automaticamente
                        // para o ícone flutuante, evitando qualquer sobreposição do editor.
                        setTimeout(function () { aplicarRetracao(true); }, 0);
                    }
                    maxLeft = window.innerWidth - larguraVisual - margemDir;
                }

                alvo = Math.max(10, Math.min(maxLeft, alvo));
                // Mesma lógica do width: left em CSS precisa ser multiplicado pelo
                // fator para compensar a contra-escala do transform e cair exatamente
                // na posição física "alvo" calculada em pixels de tela.
                P.style.left = (alvo * fator) + 'px';
                P.style.right = 'auto';
            }

            function E(t, c, x) {
                var e = document.createElement(t);
                if (c) e.style.cssText = c;
                if (x != null) e.textContent = x;
                return e;
            }

            var bodyDiv = E('div', 'display:block;user-select:text;overflow-y:auto;overflow-x:hidden;height:360px;box-sizing:border-box;padding-right:4px;');

            // Altura fixa do corpo: o painel não estica com a página nem com o
            // conteúdo — tudo que exceder fica disponível pela barra de rolagem.
            // O header (hdr) fica sempre visível no topo, pois só o bodyDiv rola.
            var ALTURA_CORPO = 360;

            // ST agora cria um grupo colapsável de botões: o título funciona
            // como toggle. `aberto` define o estado inicial (apenas o primeiro
            // grupo é criado expandido; os demais nascem retraídos).
            function ST(t, aberto) {
                var expandido = !!aberto;
                var d = E('div', 'margin-top:6px;border-top:1px solid #eef;');
                var titulo = E('div', 'display:flex;align-items:center;gap:5px;cursor:pointer;padding:6px 0 5px 0;user-select:none;');
                var chevron = E('span', 'font-size:11px;color:#8899cc;width:12px;display:inline-block;text-align:center;flex:0 0 12px;', expandido ? '▾' : '▸');
                var rotulo = E('span', 'font-weight:bold;font-size:13px;color:#8899cc;text-transform:uppercase;letter-spacing:.7px;', t);
                var conteudo = E('div', expandido ? 'padding:0 0 5px 0;' : 'display:none;padding:0 0 5px 0;');
                titulo.appendChild(chevron);
                titulo.appendChild(rotulo);
                d.appendChild(titulo);
                d.appendChild(conteudo);
                function toggleGrupo(e) {
                    if (e) { e.preventDefault(); e.stopPropagation(); }
                    expandido = !expandido;
                    conteudo.style.display = expandido ? 'block' : 'none';
                    chevron.textContent = expandido ? '▾' : '▸';
                }
                titulo.onclick = toggleGrupo;
                bodyDiv.appendChild(d);
                d._conteudo = conteudo;
                return conteudo;
            }

            // Localiza o editor CKEditor 5 (ou contenteditable) sem alertar.
            // Usado tanto pelo getEditor() quanto pelo posicionamento do painel.
            function acharEditor() {
                function findInDoc(d) {
                    if (!d) return null;
                    try {
                        return [...d.querySelectorAll('.ck-editor__editable[contenteditable="true"],.ck-editor__editable_inline[contenteditable="true"],[contenteditable="true"]')].find(function (x) { return x && x.ckeditorInstance; });
                    } catch(e) { return null; }
                }
                var ed = findInDoc(document);
                if (!ed && typeof unsafeWindow !== 'undefined' && unsafeWindow && unsafeWindow.document) {
                    ed = findInDoc(unsafeWindow.document);
                }
                if (!ed) {
                    var iframes = document.querySelectorAll('iframe');
                    for (var i = 0; i < iframes.length; i++) {
                        try {
                            var idoc = iframes[i].contentDocument || (iframes[i].contentWindow && iframes[i].contentWindow.document);
                            ed = findInDoc(idoc);
                            if (ed) break;
                        } catch(e) {}
                    }
                }
                return ed;
            }

            function getEditor() {
                var ed = acharEditor();
                if (!ed) {
                    alert('Editor CKEditor 5 não encontrado na tela. Abra a ata primeiro.');
                    return null;
                }
                return ed;
            }

            function getSelectionRange(ck) {
                try {
                    var s = ck.model.document.selection;
                    var r = [...s.getRanges()];
                    return r.length > 0 ? r[0] : null;
                } catch (e) {
                    return null;
                }
            }

            // Hora de encerramento: hora atual + 12 minutos, formato HH:MM
            function horaEncerramento() {
                var d = new Date(Date.now() + 12 * 60000);
                var hh = String(d.getHours()).padStart(2, '0');
                var mm = String(d.getMinutes()).padStart(2, '0');
                return hh + ':' + mm;
            }

            // Os templates contêm o marcador %HEC% em "Audiência encerrada às %HEC%."
            // (marcado direto na ocorrência); aqui é expandido no momento do clique.
            function completarEncerramento(html) {
                var texto = String(html || '');
                var hora = horaEncerramento();
                return texto.split('%HEC%').join(hora)
                    .replace(/Audiência encerrada às\s*\./gi, 'Audiência encerrada às ' + hora + '.')
                    .replace(/Audiência encerrada às\s*(?=<|$)/gi, 'Audiência encerrada às ' + hora + '.');
            }

            function ins(h) {
                var ed = getEditor();
                if (!ed) return;
                h = completarEncerramento(h);
                var ck = ed.ckeditorInstance;
                var SR = getSelectionRange(ck);
                if (!SR) {
                    alert('Posicione o cursor no editor antes de usar o botão.');
                    return;
                }
                try {
                    var v = ck.data.processor.toView(h);
                    var m = ck.data.toModel(v);
                    ck.model.change(function () { ck.model.insertContent(m, SR); });
                    ed.focus();
                } catch (e) {
                    alert('Erro: ' + e.message);
                }
            }

            function BF(b) {
                var btn = E('button', 'flex:1 1 auto;min-width:70px;padding:7px 4px;background:#e8f0fe;border:1px solid #b0c4f8;border-radius:6px;cursor:pointer;font-size:14px;text-align:center;line-height:1.3;');
                btn.textContent = b.t;
                btn.onclick = function () { ins(b.h); };
                btn.onmouseover = function () { this.style.background = '#c5d8ff'; };
                btn.onmouseout = function () { this.style.background = '#e8f0fe'; };
                return btn;
            }

            function BC(b, bg) {
                var btn = E('button', 'display:block;width:100%;padding:7px 8px;margin:3px 0;background:' + (bg || '#f5f8ff') + ';border:1px solid #c8d4f0;border-radius:6px;cursor:pointer;font-size:16px;text-align:left;');
                btn.textContent = b.t;
                btn.onclick = function () { ins(b.h); };
                btn.onmouseover = function () { this.style.background = '#d8e4ff'; };
                btn.onmouseout = function () { this.style.background = (bg || '#f5f8ff'); };
                return btn;
            }

            function BP(b) {
                var btn = E('button', 'padding:6px 4px;background:#f5f8ff;border:1px solid #c8d4f0;border-radius:5px;cursor:pointer;font-size:14px;text-align:center;width:100%;');
                btn.textContent = b.t;
                btn.onclick = function () { ins(b.h); };
                btn.onmouseover = function () { this.style.background = '#d8e4ff'; };
                btn.onmouseout = function () { this.style.background = '#f5f8ff'; };
                return btn;
            }

            var hdr = E('div', 'display:flex;justify-content:space-between;align-items:center;gap:6px;cursor:grab;margin:-8px -12px 8px -12px;padding:8px 12px;background:#f4f6fc;border-top-left-radius:9px;border-top-right-radius:9px;border-bottom:1px solid #e8edff;');

            var titleBox = E('div', 'display:flex;align-items:center;gap:6px;cursor:pointer;flex:1;min-width:0;');
            var titleLabel = E('span', 'font-weight:bold;font-size:14px;color:#1e293b;white-space:nowrap;', '📌 Painel AUD');
            titleBox.appendChild(titleLabel);
            var selPerfil = E('select', 'font-size:14px;color:#223;font-weight:bold;border:1px solid #ccc;border-radius:4px;padding:2px 4px;background:#fff;cursor:pointer;');
            var opO = E('option', null, 'Otavio'); opO.value = 'otavio';
            var opV = E('option', null, 'Victor'); opV.value = 'victor';
            selPerfil.appendChild(opO);
            selPerfil.appendChild(opV);
            selPerfil.value = perfilId;
            selPerfil.onchange = function(e) {
                e.stopPropagation();
                renderizarPainel(this.value, false);
            };
            titleBox.appendChild(selPerfil);


            var rightControls = E('div', 'display:flex;align-items:center;gap:4px;');
            var toggleBtn = E('button', 'border:none;background:none;cursor:pointer;font-size:16px;color:#475569;padding:2px 4px;font-weight:bold;', estaRetraido ? '➕' : '➖');
            var fc = E('button', 'border:none;background:none;cursor:pointer;font-size:20px;color:#94a3b8;padding:0 2px;', '✕');
            fc.onclick = function (e) {
                e.stopPropagation();
                window.__pjeAudFechadoManualmente = true;
                if (window.__pjeAudDomObs) { try { window.__pjeAudDomObs.disconnect(); } catch (err) {} window.__pjeAudDomObs = null; }
                P.remove();
            };

            rightControls.appendChild(toggleBtn);
            rightControls.appendChild(fc);

            hdr.appendChild(titleBox);
            hdr.appendChild(rightControls);
            P.appendChild(hdr);
            P.appendChild(bodyDiv);

            function aplicarRetracao(retraido) {
                estaRetraido = retraido;
                var minTop = calcularTopMinimo();

                if (!P.dataset.dragged) {
                    P.style.top = minTop + 'px';
                    posicionarAoLadoDoEditor();
                } else {
                    P.style.top = Math.max(minTop, P.getBoundingClientRect().top || minTop) + 'px';
                }

                if (estaRetraido) {
                    bodyDiv.style.display = 'none';
                    P.style.width = 'auto';
                    P.style.maxWidth = 'none';
                    P.style.maxHeight = 'none';
                    P.style.overflowY = 'visible';
                    P.style.padding = '4px 10px';
                    P.style.background = '#1e293b';
                    P.style.color = '#ffffff';
                    P.style.borderRadius = '20px';
                    P.style.boxShadow = '0 4px 14px rgba(0,0,0,0.3)';
                    P.title = 'Dois cliques em qualquer lugar para expandir';

                    hdr.style.marginBottom = '0';
                    hdr.style.borderBottom = 'none';
                    hdr.style.background = 'transparent';

                    titleLabel.style.color = '#f8fafc';
                    titleLabel.textContent = '📌 Painel AUD';
                    toggleBtn.textContent = '➕';
                    toggleBtn.style.color = '#cbd5e1';
                    toggleBtn.title = 'Expandir Painel de Consultas (ou clique duplo)';
                } else {
                    // Painel expandido: tamanho fixo — largura 380px e corpo com
                    // altura fixa (ALTURA_CORPO). O conteúdo que exceder fica
                    // disponível pela barra de rolagem interna do bodyDiv;
                    // o header (hdr) permanece sempre visível no topo.
                    bodyDiv.style.display = 'block';
                    bodyDiv.style.height = ALTURA_CORPO + 'px';
                    P.style.width = '380px';
                    P.style.maxWidth = 'min(380px, calc(100vw - 20px))';
                    P.style.padding = '8px 12px';
                    P.style.background = '#ffffff';
                    P.style.color = '#0f172a';
                    P.style.borderRadius = '10px';
                    P.style.boxShadow = '0 6px 24px rgba(30,50,130,.2)';
                    P.title = 'Dois cliques em qualquer lugar para retrair';

                    hdr.style.marginBottom = '8px';
                    hdr.style.borderBottom = '1px solid #e8edff';
                    hdr.style.background = '#f4f6fc';

                    titleLabel.style.color = '#1e293b';
                    titleLabel.textContent = '📌 Painel AUD';
                    toggleBtn.textContent = '➖';
                    toggleBtn.style.color = '#475569';
                    toggleBtn.title = 'Retrair Painel de Consultas (ou clique duplo)';

                    // Sem altura dinâmica: o painel não se adapta à página —
                    // a rolagem interna do corpo resolve o excedente.
                    P.style.overflowY = 'visible';
                    P.style.maxHeight = 'none';
                }
            }

            function alternarRetracao(e) {
                if (e && e.target && (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION')) return;
                aplicarRetracao(!estaRetraido);
            }

            titleBox.onclick = alternarRetracao;
            toggleBtn.onclick = alternarRetracao;

            // Evento dblclick padrão
            P.addEventListener('dblclick', function (e) {
                if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'TEXTAREA')) {
                    return;
                }
                e.stopPropagation();
                aplicarRetracao(!estaRetraido);
            });

            // Detector de duplo clique por intervalo (resiliente a sombras/Angular)
            var lastClickTime = 0;
            P.addEventListener('click', function (e) {
                if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'A')) {
                    return;
                }
                var now = Date.now();
                if (now - lastClickTime < 350) {
                    e.stopPropagation();
                    aplicarRetracao(!estaRetraido);
                    lastClickTime = 0;
                } else {
                    lastClickTime = now;
                }
            });

            (function tornarArrastavel(el, handle) {
                let ox = 0, oy = 0, drag = false;
                handle.addEventListener('mousedown', function (e) {
                    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'INPUT') return;
                    drag = true;
                    var rect = el.getBoundingClientRect();
                    ox = e.clientX - rect.left;
                    oy = e.clientY - rect.top;
                    e.preventDefault();
                });
                document.addEventListener('mousemove', function (e) {
                    if (!drag) return;
                    el.dataset.dragged = 'true';
                    var minTop = calcularTopMinimo();
                    var fator = fatorVisual();
                    var larguraVisual = el.getBoundingClientRect().width;
                    var targetTop = Math.max(minTop, e.clientY - oy);
                    var targetLeft = Math.max(10, Math.min(window.innerWidth - larguraVisual - 4, e.clientX - ox));
                    el.style.left = (targetLeft / fator) + 'px';
                    el.style.top = targetTop + 'px';
                    el.style.right = 'auto';
                    el.style.bottom = 'auto';
                    el.style.transform = 'none';
                });
                document.addEventListener('mouseup', function () {
                    drag = false;
                });
            })(P, hdr);

            function ajustarAoZoomEScroll() {
                if (!P || !document.body.contains(P)) return;
                aplicarZoomComp();
                if (!P.dataset.dragged) {
                    P.style.top = calcularTopMinimo() + 'px';
                    posicionarAoLadoDoEditor();
                } else {
                    var minTop = calcularTopMinimo();
                    var rect = P.getBoundingClientRect();
                    if (rect.top < minTop) {
                        P.style.top = minTop + 'px';
                    }
                }
            }

            window.addEventListener('resize', ajustarAoZoomEScroll);
            window.addEventListener('scroll', ajustarAoZoomEScroll, { passive: true });

            try {
                var domObs = new MutationObserver(function (mutations) {
                    // Ignora mutações originadas pelo próprio painel P (evita
                    // o ciclo escrita-de-estilo -> mutação -> callback -> escrita).
                    for (var i = 0; i < mutations.length; i++) {
                        if (P.contains(mutations[i].target) || mutations[i].target === P) return;
                    }
                    ajustarAoZoomEScroll();
                });
                // Observa só a área do editor (ou um ancestral pequeno e estável),
                // nunca document.body inteiro. Isso elimina o feedback loop com o
                // change detection do Angular da página.
                var alvoObservado = (acharEditor() && acharEditor().closest('mat-toolbar, .barra-ata, app-ata-cabecalho, .header')) || document.body;
                domObs.observe(alvoObservado, { childList: true, subtree: false });
                window.__pjeAudDomObs = domObs;
            } catch (e) { }

            aplicarZoomComp();
            aplicarRetracao(estaRetraido);
            // Posiciona após aplicar zoom/retração (largura final conhecida).
            posicionarAoLadoDoEditor();

            // Grupo Base (S1): primeiro grupo do painel — único que começa expandido.
            var dBase = ST('Base', true);
            var r1 = E('div', 'display:flex;flex-wrap:wrap;gap:4px;');
            S1.forEach(function (b) { r1.appendChild(BF(b)); });
            dBase.appendChild(r1);

            // Grupo Consultas (Infojud / CEP / SisconDJ) — colapsado por padrão.
            var dConsultas = ST('Consultas', false);
            var consultas = E('div', 'display:flex;flex-direction:column;gap:5px;');

            function linhaConsulta(rotulo, placeholder, cor) {
                var linha = E('div', 'display:flex;align-items:center;gap:4px;');
                var label = E('label', 'flex:0 0 76px;margin:0;font-size:14px;font-weight:bold;', rotulo);
                var input = E('input', 'flex:1;min-width:0;box-sizing:border-box;padding:5px;font-size:16px;border:1px solid #ccc;border-radius:3px;');
                input.type = 'text';
                input.placeholder = placeholder;
                input.inputMode = 'numeric';
                var buscar = E('button', 'flex:0 0 62px;padding:5px 3px;background:' + cor + ';color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;font-weight:bold;', 'Buscar');
                var status = E('span', 'display:none;flex:0 0 38px;color:#188038;font-size:13px;font-weight:bold;white-space:nowrap;overflow:hidden;', 'Dados copiados');
                
                input.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        buscar.click();
                    }
                });

                linha.appendChild(label);
                linha.appendChild(input);
                linha.appendChild(buscar);
                linha.appendChild(status);
                consultas.appendChild(linha);
                return { input: input, buscar: buscar, status: status, cor: cor };
            }

            // O próprio botão vira confirmação (DADOS OK / FALHA) e volta a Buscar depois.
            function feedbackBuscar(linha, ok) {
                linha.buscar.textContent = ok ? 'DADOS OK' : 'FALHA';
                linha.buscar.style.background = ok ? '#188038' : '#c5221f';
                setTimeout(function () {
                    linha.buscar.textContent = 'Buscar';
                    linha.buscar.style.background = linha.cor;
                }, 3000);
            }

            async function copiarTexto(texto) {
                if (typeof GM_setClipboard === 'function') {
                    GM_setClipboard(String(texto));
                    return;
                }
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    try {
                        await navigator.clipboard.writeText(String(texto));
                        return;
                    } catch(e) {}
                }
                var area = document.createElement('textarea');
                area.value = String(texto);
                area.style.cssText = 'position:fixed;left:-9999px;top:0;';
                document.body.appendChild(area);
                area.select();
                if (!document.execCommand('copy')) throw new Error('Não foi possível copiar os dados.');
                area.remove();
            }

            var fInfo = linhaConsulta('Infojud', 'CPF ou CNPJ', '#43a047');
            fInfo.buscar.onclick = async function () {
                var c = fInfo.input.value.replace(/\D/g, '');
                fInfo.input.value = c;
                if (c.length !== 11 && c.length !== 14) {
                    feedbackBuscar(fInfo, false);
                    return;
                }
                fInfo.buscar.disabled = true;
                fInfo.buscar.textContent = 'Buscando...';
                try {
                    var consultarInfojud = window.consultarInfojudComRetorno;
                    if (typeof consultarInfojud !== 'function' && typeof unsafeWindow !== 'undefined') {
                        consultarInfojud = unsafeWindow.consultarInfojudComRetorno;
                    }
                    if (typeof consultarInfojud === 'function') {
                        var resultado = await consultarInfojud(c);
                        await copiarTexto(resultado.texto);
                        feedbackBuscar(fInfo, true);
                    } else {
                        var urlDecjuiz = (c.length === 11 ? 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICPF.asp?NI=' : 'https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/detalheNICNPJ.asp?NI=') + encodeURIComponent(c);
                        window.open(urlDecjuiz, '_blank');
                        feedbackBuscar(fInfo, true);
                    }
                } catch (e) {
                    feedbackBuscar(fInfo, false);
                } finally {
                    fInfo.buscar.disabled = false;
                    fInfo.buscar.textContent = 'Buscar';
                }
            };

            var fCep = linhaConsulta('CEP', 'Digite o CEP', '#1e88e5');
            async function buscarEnderecoPorCEP(cep) {
                var cepNumerico = String(cep).replace(/\D/g, '');
                if (cepNumerico.length !== 8) {
                    throw new Error('Digite um CEP válido com 8 números.');
                }
                var fontes = [
                    {
                        nome: 'ViaCEP',
                        url: 'https://viacep.com.br/ws/' + cepNumerico + '/json/',
                        parse: function (d) { return d.erro ? null : {
                            logradouro: d.logradouro, bairro: d.bairro, complemento: d.complemento,
                            cidade: d.localidade, uf: d.uf, cep: d.cep
                        }; }
                    },
                    {
                        nome: 'BrasilAPI',
                        url: 'https://brasilapi.com.br/api/cep/v2/' + cepNumerico,
                        parse: function (d) { return d.errors ? null : {
                            logradouro: d.street, bairro: d.neighborhood, complemento: '',
                            cidade: d.city, uf: d.state, cep: d.cep
                        }; }
                    },
                    {
                        nome: 'BrasilCEP',
                        url: 'https://brasilcep.dev/v1/' + cepNumerico + '.json',
                        parse: function (d) { return d.erro ? null : {
                            logradouro: d.logradouro, bairro: d.bairro, complemento: d.complemento,
                            cidade: d.localidade, uf: d.uf, cep: d.cep
                        }; }
                    }
                ];
                var resultados = [];
                for (var i = 0; i < fontes.length; i++) {
                    var fonte = fontes[i];
                    try {
                        var resposta = await fetch(fonte.url, { headers: { Accept: 'application/json' } });
                        if (!resposta.ok) continue;
                        var parsed = fonte.parse(await resposta.json());
                        if (parsed && parsed.logradouro) resultados.push(parsed);
                    } catch (e) {
                        console.warn('[CEP] Falha em ' + fonte.nome + ':', e.message);
                    }
                }
                if (!resultados.length) throw new Error('Não foi possível localizar o CEP em nenhuma API.');
                var combinado = resultados.reduce(function (acc, atual) {
                    return {
                        logradouro: acc.logradouro || atual.logradouro || '',
                        bairro: acc.bairro || atual.bairro || '',
                        complemento: acc.complemento || atual.complemento || '',
                        cidade: acc.cidade || atual.cidade || '',
                        uf: acc.uf || atual.uf || '',
                        cep: acc.cep || atual.cep || cepNumerico
                    };
                }, {});
                var cepLimpo = String(combinado.cep).replace(/\D/g, '') || cepNumerico;
                var cepFormatado = cepLimpo.length === 8 ? cepLimpo.substring(0, 5) + '-' + cepLimpo.substring(5) : cepLimpo;
                var texto = [combinado.logradouro + ', número __', combinado.bairro, combinado.complemento,
                    'CEP - ' + cepFormatado, combinado.cidade + '/' + combinado.uf]
                    .filter(Boolean).join(' - ');
                return texto;
            }
            fCep.buscar.onclick = async function () {
                var c = fCep.input.value.replace(/\D/g, '');
                fCep.input.value = c;
                if (c.length !== 8) { alert('Digite um CEP válido com 8 números.'); return; }
                fCep.buscar.disabled = true;
                fCep.buscar.textContent = 'Buscando...';
                try {
                    var endereco = await buscarEnderecoPorCEP(c);
                    await copiarTexto(endereco);
                    feedbackBuscar(fCep, true);
                } catch (e) {
                    feedbackBuscar(fCep, false);
                } finally {
                    fCep.buscar.disabled = false;
                    fCep.buscar.textContent = 'Buscar';
                }
            };

            var fSiscon = linhaConsulta('SisconDJ', 'Dados da consulta', '#8e44ad');
            dConsultas.appendChild(consultas);
            var sisconCard = E('div', 'display:none;margin-top:6px;padding:7px;background:#faf5ff;border:1px solid #c084fc;border-radius:5px;font-size:14px;');
            dConsultas.appendChild(sisconCard);
            function safeTxt(t) {
                return String(t || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }

            function formatarDoc(d) {
                var digits = String(d || '').replace(/\D/g, '');
                if (digits.length === 11) return digits.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4');
                if (digits.length === 14) return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
                return d || '';
            }

            function exibirDadosSiscon(resultado, docBusca) {
                var dados = (resultado.data && resultado.data.primeiro) || resultado.data || {};
                console.log('[AUD][SISCON] resultado recebido:', resultado);
                console.log('[AUD][SISCON] primeiro bloco usado:', dados);

                var nome = (resultado.data && resultado.data.nome) || dados.nome || dados.razaoSocial || '';
                var docBruto = (resultado.data && resultado.data.documento) || dados.documento || dados.cnpj || docBusca || '';
                var docFormatado = formatarDoc(docBruto);

                var textoDados = (dados.conta || '') +
                    ', agência ' + (dados.agencia || '') +
                    ', do Banco ' + (dados.banco || '') +
                    (dados.contaJuridica ? ' (Conta PJ em nome de ' + (dados.razaoSocial || '') +
                        (dados.cnpj ? ' - ' + dados.cnpj : '') + ')' : '');

                var textoCopiado = 'Nome: ' + nome + ' CPF/CNPJ: ' + docFormatado + '\n' +
                    'Dados: ' + textoDados + '\n' +
                    'Chave Pix: ';

                sisconCard.innerHTML = '<strong>Nome:</strong> ' + safeTxt(nome) + ' &nbsp;<strong>CPF/CNPJ:</strong> ' + safeTxt(docFormatado) + '<br>' +
                    '<strong>Dados:</strong> ' + safeTxt(textoDados) + '<br>' +
                    '<strong>Chave Pix:</strong> ' +
                    (resultado.detailUrl ? ' <a href="' + resultado.detailUrl + '" target="_blank" rel="noopener">confirmar</a>' : '');
                sisconCard.style.display = 'block';

                return textoCopiado;
            }
            fSiscon.buscar.onclick = async function () {
                var c = fSiscon.input.value.replace(/\D/g, '');
                fSiscon.input.value = c;
                if (c.length !== 11 && c.length !== 14) { alert('Digite um CPF ou CNPJ válido.'); return; }
                fSiscon.buscar.disabled = true;
                fSiscon.buscar.textContent = 'Buscando...';
                try {
                    var api = (window.Alv && (window.Alv.siscondj || window.Alv.siscon)) || (typeof unsafeWindow !== 'undefined' && unsafeWindow && unsafeWindow.Alv && (unsafeWindow.Alv.siscondj || unsafeWindow.Alv.siscon));
                    if (api && typeof api.consultarDocumento === 'function') {
                        var resultado = await api.consultarDocumento(c);
                        if (resultado.status === 'empty') {
                            feedbackBuscar(fSiscon, false);
                            sisconCard.innerHTML = 'Nenhum dado bancário encontrado. ' + (resultado.searchLink ? '<a href="' + resultado.searchLink + '" target="_blank" rel="noopener">abrir busca</a>' : '');
                            sisconCard.style.display = 'block';
                            return;
                        }
                        var textoParaCopiar = exibirDadosSiscon(resultado, c);
                        await copiarTexto(textoParaCopiar);
                        feedbackBuscar(fSiscon, true);
                    } else {
                        var urlBusca = 'https://aplicacoes1.trt2.jus.br/adv-dados-bancarios-consulta/' + (c.length === 11 ? 'consulta-pf?cpf=' : 'consulta-pj?cnpj=') + c;
                        window.open(urlBusca, '_blank');
                        feedbackBuscar(fSiscon, true);
                    }
                } catch (e) {
                    feedbackBuscar(fSiscon, false);
                    sisconCard.style.display = 'none';
                } finally {
                    fSiscon.buscar.disabled = false;
                    fSiscon.buscar.textContent = 'Buscar';
                }
            };


            if (S2_list.length > 0) {
                var d2 = ST('Perícias', false);
                var g2 = E('div', 'display:grid;grid-template-columns:1fr 1fr;gap:4px;');
                S2_list.forEach(function (b) { g2.appendChild(BP(b)); });
                d2.appendChild(g2);
            }

            if (S3.length > 0) {
                var d3 = ST('Adiamento - Testemunhas', false);
                S3.forEach(function (b) { d3.appendChild(BC(b)); });
            }

            var d4 = ST('Acordo', false);
            S4.forEach(function (b) { d4.appendChild(BC(b)); });

            var honBtn = E('button', 'display:block;width:100%;padding:7px 8px;margin:3px 0;background:#fff8e1;border:1px solid #f0c060;border-radius:6px;cursor:pointer;font-size:16px;text-align:left;', 'Honorários periciais - acordo pós perícia');
            var honEx = E('div', 'display:none;margin-top:4px;padding:6px;background:#fffdf0;border:1px solid #f0d080;border-radius:5px;');
            var selP = E('select', 'width:100%;margin-bottom:4px;padding:4px;font-size:16px;border:1px solid #ccc;border-radius:3px;');
            var op0 = E('option', null, 'Selecione o perito aqui');
            op0.value = '';
            selP.appendChild(op0);
            Object.keys(PR).forEach(function (n) {
                var o = E('option', null, n);
                o.value = n;
                selP.appendChild(o);
            });
            honEx.appendChild(selP);

            var bColar = E('button', 'display:block;width:100%;padding:5px;background:#4caf50;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:16px;', 'Colar dados');
            bColar.onclick = function () {
                var n = selP.value;
                if (!n) { selP.style.borderColor = 'red'; return; }
                selP.style.borderColor = '#ccc';
                var pp = PR[n];
                var hf = HH.replace('perito *', n).replace('Banco *', pp.banco || '(banco não informado)').replace('agência *', pp.agencia || '(agência não informada)').replace('conta corrente *', pp.conta || '(conta não informada)');
                ins(hf);
            };
            honEx.appendChild(bColar);

            honBtn.onclick = function () {
                honEx.style.display = honEx.style.display === 'none' ? 'block' : 'none';
            };

            d4.appendChild(honBtn);
            d4.appendChild(honEx);

            if (S5.length > 0) {
                var d5 = ST('Outros', false);
                S5.forEach(function (b) { d5.appendChild(BC(b, '#fdf5ff')); });
            }

            document.body.appendChild(P);
            console.log('[Aud.core.js] Painel anexado ao document.body com sucesso!');

            if (window.PJeState && window.PJeState.registry) {
                window.PJeState.registry.add(function () {
                    if (window.__pjeAudDomObs) { try { window.__pjeAudDomObs.disconnect(); } catch (err) {} window.__pjeAudDomObs = null; }
                    var el = document.getElementById('pjetools-aud-container');
                    if (el) el.remove();
                });
            }
        }

        function criarSeletor() {
            var overlay = document.createElement('div');
            overlay.id = 'pjetools-aud-container'; // same ID so it doesn't duplicate
            overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;justify-content:center;align-items:center;z-index:9999999;';
            
            var modal = document.createElement('div');
            modal.style.cssText = 'background:#fff;padding:20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);text-align:center;font-family:Arial,sans-serif;';
            
            var titulo = document.createElement('h3');
            titulo.textContent = 'Qual o juiz da pauta de hoje?';
            titulo.style.marginTop = '0';
            modal.appendChild(titulo);
            
            var btns = document.createElement('div');
            btns.style.cssText = 'display:flex;gap:10px;justify-content:center;margin-top:20px;';
            
            var btnO = document.createElement('button');
            btnO.textContent = 'Otavio';
            btnO.style.cssText = 'padding:10px 20px;font-size:18px;cursor:pointer;background:#2196f3;color:#fff;border:none;border-radius:4px;';
            btnO.onclick = function() {
                overlay.remove();
                renderizarPainel('otavio');
            };
            
            var btnV = document.createElement('button');
            btnV.textContent = 'Victor';
            btnV.style.cssText = 'padding:10px 20px;font-size:18px;cursor:pointer;background:#4caf50;color:#fff;border:none;border-radius:4px;';
            btnV.onclick = function() {
                overlay.remove();
                renderizarPainel('victor');
            };
            
            btns.appendChild(btnO);
            btns.appendChild(btnV);
            modal.appendChild(btns);
            overlay.appendChild(modal);
            document.body.appendChild(overlay);
        }

        console.log('[Aud.core.js] Chamando renderizarPainel() ao final de init()');
        renderizarPainel(perfilAtual, false);
    }

    console.log('[Aud.core.js] Verificando se devemos disparar init na carga do script...');
    if (isRouteAud()) {
        console.log('[Aud.core.js] Estamos em /aud, disparando init(true)');
        init(true);
    } else {
        console.log('[Aud.core.js] Não estamos em /aud, ignorando init inicial');
    }

    var _targetWin = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;
    _targetWin.PJeAud = _targetWin.PJeAud || {};
    _targetWin.PJeAud.init = init;
    window.PJeAud = window.PJeAud || _targetWin.PJeAud;
    window.PJeAud.init = init;

    // Re-injeção automática do painel no ambiente /aud (remoção fora dele).
    if (typeof window.__pjeAudInterval === 'undefined') {
        console.log('[Aud.core.js] Registrando interval de monitoramento (__pjeAudInterval).');
        window.__pjeAudInterval = setInterval(function() {
            if (isRouteAud()) {
                if (!document.getElementById('pjetools-aud-container') && document.body && !window.__pjeAudFechadoManualmente) {
                    init();
                }
            } else {
                var el = document.getElementById('pjetools-aud-container');
                if (el) el.remove();
            }
        }, 1000);
    }

    }); // fim aguardarDados

})();
```

## Aud.data.js

```javascript
// ==UserScript==
// @name         Aud - Dados (perfis, peritos, textos padrão)
// @namespace    pjetools
// @version      1.0
// @grant        none
// ==/UserScript==
(function () {
    'use strict';
    console.log('[Aud.data.js] Iniciando carregamento do modulo de dados...');

var perfis = {
            // @SECAO: PERFIL OTAVIO
otavio: {
                title: "Otavio",
// @SUBSECAO: S1
                S1: [// @ITEM: Instrução
{"t": "Instrução", "h": "<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Prazo de 02 dias para regularização processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Recebida defesa com documentos. Concede-se o prazo de 05 dias para a reclamante se manifestar sobre a defesa e documentos, apontando eventuais diferenças que entender devidas, ainda que por amostragem, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Prazo de 05 dias para regularização processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\"><u>CONCILIAÇÃO REJEITADA</u></p>\
<p style=\"text-align:justify;text-indent:3cm;\">Defesa com documentos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Concede-se o prazo de 05 dias para o reclamante se manifestar sobre a(s) defesa(s) e documento(s), apontando, inclusive, eventuais diferenças que entende devidas, ainda que por amostragem, sob pena de preclusão, observando os termos do artigo 372 do CPC.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O Ato Normativo 003626-80.2025.2.00.0000 do CNJ, de setembro de 2025, estipula a obrigatoriedade do registro audiovisual de todas as audiências (arts. 1º e 3º). Nesse sentido, esclareço que a audiência será gravada, com disponibilização de link no acervo eletrônico dos autos, exceto na fase de tratativas de conciliação, ao início e ao final da audiência (CLT, arts. 846 e 850), haja vista a confidencialidade garantida pelo art. 30 da Lei 13.140/15, como aliás já decidiu o TED da OAB/SP (Processo: E-6.115/2023).</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Portanto, os depoimentos prestados na presente audiência serão integralmente gravados, razão pela qual não haverá pelo(a) magistrado (a), a transcrição exata das declarações dos depoentes.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Havendo interesse de se valer, em razões finais ou para fins recursais, de trechos específicos dos depoimentos, deverão as partes indicar com precisão o nome do arquivo, o minuto e o segundo em que o trecho degravado está registrado. A parte adversa, caso discorde da degravação, deverá apresentar impugnação especificada.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Oportuno destacar que a gravação da audiência pelas partes e por seus advogados é lícita, independentemente da gravação feita pelo juízo (CPC, art. 367, §§ 5º e 6º), mas deve ser precedida de comunicação e identificação prévia dos envolvidos (Art. 5º, § 1º ato normativo), sendo limitada ao uso processual, sendo EXPRESSAMENTE VEDADA a sua utilização para outras finalidades, notadamente publicações em redes sociais, monetização, transmissões on-line, páginas de internet ou compartilhamentos por meio de aplicativos de mensagens (art. 5º, § 4º, II, B, do referido ato).</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Assim, e considerando ainda que a imagem e a voz humanas são protegidas legal e constitucionalmente contra reproduções não autorizadas pelo titular do direito de personalidade respectivo, ficam as partes advertidas de que o Juízo não autoriza o uso ou a reprodução da imagem e ou da voz de qualquer um dos sujeitos processuais por qualquer meio externo ao processo, físico ou eletrônico, sob pena de responsabilidade civil e criminal dos envolvidos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Neste momento, inicia-se a gravação da audiência.<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Depoimento pessoal do(a) reclamante:\"Que<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Depoimento pessoal do(a) preposto(a) da &nbsp;1ª reclamada: \"Que</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Testemunha do(a) reclamante, CPF, residente e domiciliada, São Paulo/SP.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Advertida e compromissada.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Depoimento: \"</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As partes não pretendem outras provas.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Após o prazo de réplica, estará encerrada a instrução processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Razões finais em 05 dias.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Conciliação final rejeitada.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Designo julgamento para o dia 11/09/26, às 13h__, sendo que as partes serão intimadas da decisão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Lida e conferida a ata pelos presentes é dispensada a assinatura das partes e dos respectivos patronos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Audiência encerrada às %HEC%.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Nada mais.</p>"}, // @ITEM: Encerramento s/ oitiva
{"t": "Encerramento s/ oitiva", "h": "<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Recebida defesa com documentos. Concede-se o prazo de 05 dias para o reclamante se manifestar sobre a defesa e documentos, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As partes dispensam os depoimentos pessoais reciprocamente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As partes não têm testemunhas.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Fica preclusa a produção de prova oral.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Fica encerrada a instrução processual. Razões finais pelas partes em 05 dias.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Designa-se audiência de JULGAMENTO para o dia 25/09/2026 às 13:55 horas, com intimação via diário oficial.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Audiência encerrada às %HEC%.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Nada mais.</p>"}, // @ITEM: revelia
{"t": "revelia", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Diante da ausência injustificada da reclamada, aplico-lhe a pena de revelia e confissão.</p>"}, // @ITEM: Dispensa Testemunha
{"t": "Dispensa Testemunha", "h": "<p style=\"text-align:justify;text-indent:3cm;\">O reclamante requer a oitiva da testemunha **** , com o intuito de comprovar a existência de vínculo de emprego.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No particular, considero desnecessária a oitiva da testemunha, porquanto os depoimentos pessoais das partes são convergentes entre si, praticamente uníssonos, dirimindo a controvérsia sobre as questões de fato que abarcam o presente processo. Por conta disso, indefiro o depoimento. Protestos.</p>"}, // @ITEM: Inst LLM
{"t": "Inst LLM", "h": "<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">A(s) defesa(s) está(ão) nos autos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O Ato Normativo 003626-80.2025.2.00.0000 do CNJ, de setembro de 2025, estipula a obrigatoriedade do registro audiovisual de todas as audiências (arts. 1º e 3º). Nesse sentido, esclareço que a audiência será gravada, com disponibilização de link no acervo eletrônico dos autos, exceto na fase de tratativas de conciliação, ao início e ao final da audiência (CLT, arts. 846 e 850), haja vista a confidencialidade garantida pelo art. 30 da Lei 13.140/15, como aliás já decidiu o TED da OAB/SP (Processo: E-6.115/2023).</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Portanto, os depoimentos prestados na presente audiência serão integralmente gravados, razão pela qual não haverá pelo(a) magistrado (a), a transcrição exata das declarações dos depoentes.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Todavia, visando apenas a facilitação de suas manifestações sobre o conteúdo da prova, será elaborado por ferramenta de Inteligência Artificial (Google) um breve resumo das informações úteis ao julgamento da causa (art. 851 e 852-F da CLT), ficando expressamente destacado que esse breve resumo não substitui, para fins probatórios, a íntegra dos depoimentos - que estarão documentados em meio audiovisual - e nem implica aquiescência das partes quanto ao conteúdo do resumo, servindo apenas e tão somente para auxílio na análise das provas. Portanto, prevalece em caso de divergências a versão original do vídeo disponibilizada no sistema PJe.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Havendo interesse de se valer, em razões finais ou para fins recursais, de trechos específicos dos depoimentos, deverão as partes indicar com precisão o nome do arquivo, o minuto e o segundo em que o trecho degravado está registrado. A parte adversa, caso discorde da degravação, deverá apresentar impugnação especificada.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Oportuno destacar que a gravação da audiência pelas partes e por seus advogados é lícita, independentemente da gravação feita pelo juízo (CPC, art. 367, §§ 5º e 6º), mas deve ser precedida de comunicação e identificação prévia dos envolvidos (Art. 5º, § 1º ato normativo), sendo limitada ao uso processual, sendo EXPRESSAMENTE VEDADA a sua utilização para outras finalidades, notadamente publicações em redes sociais, monetização, transmissões on-line, páginas de internet ou compartilhamentos por meio de aplicativos de mensagens (art. 5º, § 4º, II, B, do referido ato).</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Assim, e considerando ainda que a imagem e a voz humanas são protegidas legal e constitucionalmente contra reproduções não autorizadas pelo titular do direito de personalidade respectivo, ficam as partes advertidas de que o Juízo não autoriza o uso ou a reprodução da imagem e ou da voz de qualquer um dos sujeitos processuais por qualquer meio externo ao processo, físico ou eletrônico, sob pena de responsabilidade civil e criminal dos envolvidos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Neste momento, inicia-se a gravação da audiência.<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Depoimento pessoal do(a) reclamante: Gravado em áudio e vídeo.<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Depoimento pessoal do(a) preposto(a) da 1ª reclamada: Gravado em áudio e vídeo.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">1ª testemunha do(a) <u>reclamante</u>: *, CPF nº *, residente no endereço *.&nbsp;<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">1ª testemunha do(a) <u>reclamado(a)</u>: *, CPF nº *, residente no endereço *.<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As partes não têm outras provas a produzir.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Encerrada a instrução processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Frustrada a última tentativa conciliatória.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Razões finais facultadas no prazo comum de 05 dias.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Designa-se para julgamento a data de 25/09/2026 às 13h05, sendo que as partes serão intimadas da sentença via Diário Oficial.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Audiência encerrada às %HEC%.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Nada mais.</p>"}],
// @SUBSECAO: S3
                S3: [// @ITEM: provimento
{"t": "provimento", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Prazo de 02 dias para regularização processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O(a) advogado(a) do(a) * requer o adiamento da presente audiência, tendo em vista que a(s) testemunha(s) *, embora convidada(s), não compareceu(ram).&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O advogado requer que a intimação seja feita na forma do Provimento.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Deferido.</p>\
<p style=\"text-align:justify;text-indent:3cm;\"><u>Designa-se nova audiência UNA para o dia /11/26, às * horas, mantendo-se as cominações anteriores.&nbsp;</u></p>\
<p style=\"text-align:justify;text-indent:3cm;\">Servirá o presente como MANDADO DE INTIMAÇÃO DE TESTEMUNHA, comprometendo-se o(a) * a entregar à testemunha acima indicada.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">A ausência ensejará multa e condução coercitiva. Local: Av. Guido Caloi, 1000, Santo Amaro, São Paulo/SP, CEP 05802-140.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Saem cientes &nbsp;da nova designação as seguintes testemunhas:</p>\
<p style=\"text-align:justify;text-indent:3cm;\">-Do reclamante -&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">-Da reclamada -&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As demais testemunhas virão independentemente de notificação, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Lida e conferida a ata pelos presentes é dispensada a assinatura das partes e dos respectivos patronos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Audiência encerrada às .</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Nada mais.</p>"}, // @ITEM: Testemunha - independente
{"t": "Testemunha - independente", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Prazo de 02 dias para regularização processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O(a) advogado(a) do(a) * requer o adiamento da presente audiência, tendo em vista que a(s) testemunha(s) *, embora convidada(s), não compareceu(ram), comprometendo-se a trazê-la(s) na próxima sessão independentemente de intimação, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Defiro.</p>\
<p style=\"text-align:justify;text-indent:3cm;\"><u>Designa-se nova audiência UNA para o dia /11/26, às * horas, mantendo-se as cominações anteriores.&nbsp;</u></p>\
<p style=\"text-align:justify;text-indent:3cm;\">Saem cientes da nova designação as seguintes testemunhas:</p>\
<p style=\"text-align:justify;text-indent:3cm;\">-Do reclamante -&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">-Da reclamada -&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As demais testemunhas virão independentemente de notificação, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Lida e conferida a ata pelos presentes é dispensada a assinatura das partes e dos respectivos patronos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Audiência encerrada às %HEC%.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Nada mais.</p>"}],
// @SUBSECAO: S4
                S4: [// @ITEM: Alvará
{"t": "Alvará", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">A presente ata tem força de ALVARÁ perante a CEF para liberação do FGTS, assim como suprimindo a inexistência do Termo de Rescisão do Contrato de Trabalho/CD, dos recolhimentos rescisórios do FGTS e do carimbo de baixa da CTPS, fornecendo-se, inclusive, os seguintes elementos relativos ao contrato de trabalho: PIS nº: *, data de admissão: * e demissão: *, CNPJ: *. CTPS * Série *-SP tipo de rescisão do contrato de trabalho::<u>****</u></p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">A presente ata possui força de ALVARÁ perante a CEF, SINE e demais órgãos competentes para requerimento do seguro-desemprego, suprindo, inclusive, a inexistência do TRCT, das guias SD/CD e do carimbo de baixa da CTPS, caso os prazos de carência e eventuais solicitações anteriores forem atendidas. PIS nº: * , data de admissão: * e demissão: *, CNPJ: * CTPS * Série *-SP&nbsp; tipo de rescisão do contrato de trabalho:<u>****</u></p>"}, // @ITEM: Suspender subsidiária
{"t": "Suspender subsidiária", "h": "<p style=\"text-align:justify;text-indent:3cm;\">A segunda reclamada não concorda em permanecer no polo responsável pelo acordo e o reclamante não concorda com sua exclusão nesse momento. Assim, o processo ficará suspenso até o cumprimento total do acordo quando a quitação também se dará em relação à segunda reclamada. Uma vez não cumprido o acordo, o processo voltará ao estado em que se encontra com apresentação de defesas e produção de provas. Ficará estipulada multa de 20% sobre o valor do acordo em caso de descumprimento para que não seja utilizado como medida protelatória do feito.</p>"}, // @ITEM: Acordo - Suspensão +Retorno ao estado anterior
{"t": "Acordo - Suspensão +Retorno ao estado anterior", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">As partes, neste ato, ajustam a suspensão do processo <strong>até o dia ******</strong>, data do pagamento da última parcela do acordo.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">O(a) reclamante terá o prazo de 15 dias, contado do termo final da suspensão, para noticiar eventual inadimplemento por parte da reclamada, ficando ciente desde já que no seu silêncio considerar-se-ão adimplidas todas as parcelas.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Nessa hipótese, os autos virão conclusos para homologação do acordo e exclusão das demais reclamadas.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Em caso de descumprimento do acordo, o processo retornará ao estado em que se encontrava, isto é, será designada nova audiência ***<strong>UNA / UNA/RS</strong> para recebimento das defesas e instrução do processo, de sorte que eventual valor parcial do acordo quitado será deduzido de futura execução.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Com o pagamento integral do acordo, o(a) reclamante dará geral e plena quitação pelo objeto da inicial e extinto contrato de trabalho.</p>"}, // @ITEM: acordo subsidiária
{"t": "acordo subsidiária", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Fica ajustada, ainda, a responsabilidade subsidiária da segunda reclamada, pelo valor integral do acordo na hipótese de inadimplemento por parte da primeira reclamada. Desta feita, caso descumprido o acordo pela primeira reclamada, a segunda reclamada deverá ser intimada para proceder ao pagamento do quanto inadimplido no prazo de 15 dias, observado o valor das parcelas e a sua periodicidade, sendo certo que na hipótese de pagamento tempestivo pela responsável subsidiária não lhe será cobrada multa acima estipulada, sendo que nesse caso a multa será devida exclusivamente pela primeira reclamada</p>"}, // @ITEM: diverso entre as partes
{"t": "diverso entre as partes", "h": "<p style=\"text-align:justify;text-indent:3cm;\">As partes ajustam, outrossim, que as primeira/segunda e segunda/terceira reclamadas responderão exclusivamente pelos valores que se comprometeram a pagar, conforme discriminação supra.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Dessa forma, em caso de inadimplemento, apenas da empresa que der causa ao descumprimento do acordo será cobrada a multa acima prevista, bem como será iniciada a respectiva execução do valor inadimplido.</p>"}, // @ITEM: INSS s/ vínculo
{"t": "INSS s/ vínculo", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Após a quitação do acordo, a reclamada deverá comprovar, em 30 dias, o recolhimento das contribuições previdenciárias relacionadas ao item b da discriminação, na forma do Tema 310 do TST.</p>"}],
// @SUBSECAO: S5
                S5: []
            },
            // @SECAO: PERFIL VICTOR
victor: {
                title: "Victor",
// @SUBSECAO: S2
                S2: [
                    // @ITEM: pericia - allan
{"t": "pericia - allan", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">O Juízo observa que o reclamante postula o reconhecimento de doença ocupacional, com requerimento de realização de perícia. A fim de imprimir celeridade e efetividade ao feito, proceder-se-á à produção integral da prova oral nesta audiência, inclusive quanto ao objeto da perícia a ser realizada, com a designação de perícia após o encerramento da produção de prova oral.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Tendo em vista o pedido de adicional de PERICULOSIDADE, determina-se a realização da perícia técnica. Fica nomeado o Sr. Perito Eng. ALLAN STRUCK PINHEIRO - Cel: (11) 94264-5345 - e-mail: peritoallan.pinheiro@gmail.com, devendo apresentar seu laudo no prazo de 30 dias, acompanhado da proposta de honorários, ficando advertido de que eventuais atrasos serão levados em consideração na fixação do valor. Intime-se.&nbsp;</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">No mesmo prazo da réplica acima deferido, as partes poderão apresentar quesitos e indicar assistentes técnicos, sendo que nesta oportunidade o(a) reclamante poderá descrever suas atividades, local e o setor de trabalho, sob pena de preclusão e de serem consideradas as atividades e informações descritas no laudo pericial.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Atente-se o Expert para esta determinação. Fica autorizado o acompanhamento da diligência pelo(a) reclamante e assistentes técnicos das partes, devendo entrar em contato diretamente com o Sr. Perito, sob pena de preclusão.&nbsp;</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">As partes serão intimadas da data da perícia, a qual se realizará no seguinte endereço: *&nbsp;</p>"},
                    // @ITEM: pericia - regiane
{"t": "pericia - regiane", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">O Juízo observa que o reclamante postula o reconhecimento de doença ocupacional, com requerimento de realização de perícia. A fim de imprimir celeridade e efetividade ao feito, proceder-se-á à produção integral da prova oral nesta audiência, inclusive quanto ao objeto da perícia a ser realizada, com a designação de perícia após o encerramento da produção de prova oral.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Tendo &nbsp;em &nbsp;vista &nbsp;o &nbsp;pedido &nbsp;de &nbsp;adicional &nbsp;de INSALUBRIDADE, &nbsp;determina-se &nbsp;a &nbsp;realização &nbsp;da perícia técnica. Fica nomeado o Sra. Perita &nbsp;REGIANE SOUZA ROCHA SILVA - e-mail: peritaregianesilva@gmail.com, &nbsp;devendo &nbsp;apresentar &nbsp;seu &nbsp;laudo &nbsp;no &nbsp;prazo &nbsp;de &nbsp;30 &nbsp;dias, &nbsp;acompanhado &nbsp;da proposta &nbsp;de &nbsp;honorários, &nbsp;ficando &nbsp;advertido &nbsp;de &nbsp;que &nbsp;eventuais &nbsp;atrasos &nbsp;serão &nbsp;levados &nbsp;em &nbsp;consideração &nbsp;na fixação do valor. Intime-se.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No &nbsp;mesmo &nbsp;prazo &nbsp;da &nbsp;réplica &nbsp;acima &nbsp;deferido, &nbsp;as &nbsp;partes &nbsp;poderão &nbsp;apresentar &nbsp;quesitos &nbsp;e &nbsp;indicar assistentes &nbsp;técnicos, &nbsp;sendo &nbsp;que &nbsp;nesta &nbsp;oportunidade &nbsp;o(a) &nbsp;reclamante &nbsp;poderá &nbsp;descrever &nbsp;suas &nbsp;atividades, local &nbsp;e &nbsp;o &nbsp;setor &nbsp;de &nbsp;trabalho, &nbsp;sob &nbsp;pena &nbsp;de &nbsp;preclusão &nbsp;e &nbsp;de &nbsp;serem &nbsp;consideradas &nbsp;as &nbsp;atividades &nbsp;e &nbsp;informações descritas no laudo pericial. Atente-se o Expert para esta determinação. Fica &nbsp;autorizado &nbsp;o &nbsp;acompanhamento &nbsp;da &nbsp;diligência &nbsp;pelo(a) &nbsp;reclamante &nbsp;e &nbsp;assistentes técnicos &nbsp;das &nbsp;partes, &nbsp;devendo &nbsp;entrar &nbsp;em &nbsp;contato &nbsp;diretamente &nbsp;com &nbsp;o &nbsp;Sr. &nbsp;Perito, &nbsp;sob &nbsp;pena &nbsp;de preclusão.As &nbsp;partes &nbsp;serão &nbsp;intimadas &nbsp;da &nbsp;data &nbsp;da &nbsp;perícia, &nbsp;a &nbsp;qual &nbsp;se &nbsp;realizará &nbsp;no &nbsp;endereço: Rua&nbsp;</p>"},
                    // @ITEM: Pericia - cirino
{"t": "Pericia - cirino", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">O Juízo observa que o reclamante postula o reconhecimento de doença ocupacional, com requerimento de realização de perícia. A fim de imprimir celeridade e efetividade ao feito, proceder-se-á à produção integral da prova oral nesta audiência, inclusive quanto ao objeto da perícia a ser realizada, com a designação de perícia após o encerramento da produção de prova oral.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Tendo em vista o pedido de PERÍCIA MÉDICA, determina-se a realização da perícia técnica. Fica nomeado o Sr. Perito Médico ALEXANDRE CIRINO, que deverá apresentar seu laudo no prazo de 20 dias após a realização da perícia médica, que ocorrerá na data de 06/10/26 às 14h30min na 3ª Vara do Trabalho do Fórum da Zona Sul: Av. Guido Caloi, 1000, 2º andar, São Paulo/SP - Cel (11) 97160-1309 - e-mail: alecirino@terra.com.br, acompanhado da proposta de honorários, ficando advertido de que eventuais atrasos serão levados em consideração na fixação do valor.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O reclamante deverá portar todas as suas CTPS no dia da perícia. Intime-se.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No mesmo prazo da réplica acima deferido, as partes poderão apresentar quesitos e indicar assistentes técnicos, sendo que nesta oportunidade o(a) reclamante poderá descrever suas atividades, local e o setor de trabalho, sob pena de preclusão e de serem consideradas as atividades e informações descritas no laudo pericial.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Atente-se o Expert para esta determinação.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Fica autorizado o acompanhamento da diligência pelo(a) reclamante assistentes técnicos das partes. As partes já estão cientes da data da perícia médica.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">A ausência da parte reclamante acarretará a preclusão da prova pericial e aplicação de multa por litigância de má fé, se não comprovadamente justificada NOS AUTOS em até 48 horas após a data do exame, independentemente de intimação específica para tanto.</p>"},
                    // @ITEM: Pericia Vladia
{"t": "Pericia Vladia", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">O Juízo observa que o reclamante postula o reconhecimento de doença ocupacional, com requerimento de realização de perícia. A fim de imprimir celeridade e efetividade ao feito, proceder-se-á à produção integral da prova oral nesta audiência, inclusive quanto ao objeto da perícia a ser realizada, com a designação de perícia após o encerramento da produção de prova oral.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Tendo em vista o pedido de PERÍCIA MÉDICA, determina-se a realização da perícia técnica.<br>Fica nomeado o Sr. Perito Médico VLADIA JUOZEPAVICIUS GONÇALVES (email vladia2112@yahoo.com.br e telefone: 11 4992-9209), que deverá apresentar seu laudo no prazo de 30 dias após a realização da perícia médica, que ocorrerá em data e local a serem informados pela expert &nbsp;acompanhado da proposta de honorários, ficando advertido de que eventuais atrasos serão levados em consideration na fixação do valor.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O reclamante deverá portar todas as suas CTPS no dia da perícia. Intime-se.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No prazo de 05 dias, as partes poderão apresentar quesitos e indicar assistentes técnicos, sendo que nesta oportunidade o(a) reclamante poderá descrever suas atividades, local e o setor de trabalho, sob pena de preclusão e de serem consideradas as atividades e informações descritas no laudo pericial.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Atente-se o Expert para esta determinação.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Fica autorizado o acompanhamento da diligência pelo(a) reclamante assistentes técnicos das partes.</p>"},
                    // @ITEM: pericia (sem instrução)
{"t": "pericia (sem instrução)", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">O Juízo observa que o reclamante postula o reconhecimento de doença ocupacional / adicional de insalubridade / periculosidade, com requerimento de realização de perícia.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">As partes dispensam os depoimentos pessoais reciprocamente.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">As partes não têm testemunhas.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Fica preclusa a produção de prova oral.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Determina-se a realização da perícia técnica. Fica nomeado o Sr. Perito, devendo apresentar seu laudo no prazo de 30 dias, acompanhado da proposta de honorários. Intime-se.&nbsp;</p>"},
                    // @ITEM: Prova emprestada
{"t": "Prova emprestada", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Nos termos da Tese 140, recentemente editada pelo C. TST, “a utilização de prova pericial emprestada para comprovar insalubridade ou periculosidade é válida, independentemente da concordância da parte contrária, desde que esteja presente a identidade fática entre o processo de origem e o processo em que a prova é utilizada, e seja observado o contraditório na produção da prova original e nos autos em que é trasladada, não configurando nulidade processual o indeferimento de nova perícia quando observados esses requisitos.”</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No particular, a primeira reclamada informa que a obra na qual o reclamante se ativou já foi encerrada, inviabilizando a realização de perícia no local.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Por conta disso, determino a utilização de prova emprestada nos autos, consistente na juntada de laudo pericial pelas partes no prazo de 05 dias.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O contraditório será exercido de forma plena na apresentação de razões finais, bem como na possibilidade de produção de prova oral nesta audiência.</p>"}
                ],
// @SUBSECAO: S1
                S1: [// @ITEM: Sem dep pessoal
{"t": "Sem dep pessoal", "h": "<p style=\"text-align:justify;text-indent:3cm;\">As partes pleiteiam a oitiva do depoimento pessoal da parte adversa, a despeito de ter trazido consigo testemunhas para serem ouvidas.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Considerando o disposto no artigo 848 da CLT, a oitiva das partes constitui faculdade do magistrado, e não direito subjetivo das partes, razão pela qual é inaplicável, ao processo do trabalho, a regra prevista no artigo 385 do CPC de 2015, diante da existência de disciplina específica na legislação consolidada.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Outrossim, o artigo 765 da CLT confere ao juiz amplos poderes na direção do processo, autorizando-o a indeferir provas que reputar desnecessárias à formação do seu convencimento. No caso, este magistrado entende prescindível a colheita dos depoimentos pessoais, notadamente porque as partes conduziram ao átrio da sala de audiências pessoas para serem ouvidas na condição de testemunhas. Isto é, a prova a ser produzida é apta a esclarecer, com qualidade, os fatos trazidos à discussão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">A jurisprudência da Subseção I Especializada em Dissídios Individuais do Tribunal Superior do Trabalho, cf. TST - E-RRAg: 00017111520175060014, Relator.: Breno Medeiros, Data de Julgamento: 16/05/2024, Subseção I Especializada em Dissídios Individuais, Data de Publicação: 08/11/2024, consolidou entendimento no sentido de que o interrogatório das partes é prerrogativa do magistrado, à luz dos artigos 848 e 765 da CLT, sendo igualmente afastada a aplicação subsidiária do artigo 385 do CPC, ante a inexistência de lacuna normativa.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No julgamento levado a efeito pela Subseção I Especializada em Dissídios Individuais do Tribunal Superior do Trabalho, a ratio decidendi foi construída a partir do contexto fático em que a parte reclamada alegava cerceamento do direito de defesa em razão do indeferimento, pelo juízo de origem, tanto do pedido de adiamento da audiência para a oitiva de testemunha quanto da colheita dos depoimentos pessoais, sendo certo que, naquela assentada, nenhuma das partes dispunha de testemunhas a serem ouvidas.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Constatou-se que o adiamento fora indeferido por ausência de comprovação tempestiva do convite à testemunha, nos termos do artigo 455, § 1º, do CPC de 2015, e que, quanto aos depoimentos pessoais, o Tribunal Regional do Trabalho da 6ª Região reconhecera tratar-se de ato inserido no poder discricionário do magistrado, à luz do artigo 848 da CLT.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">A SDI-I, ao manter tal compreensão, firmou o entendimento de que a inexistência de prova oral a produzir, por si só, não impõe a realização do interrogatório das partes, porquanto a oitiva pessoal não constitui direito das partes, mas faculdade do juiz.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">A fortiori, em casos como o em comento, em que há testemunhas a serem ouvidas, também se mostra dispensável a oitiva das partes.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Dessa forma, a decisão acerca da realização, ou não, dos depoimentos pessoais insere-se no âmbito do poder de condução do processo atribuído ao magistrado, não se tratando de prerrogativa das partes.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Indefiro, portanto, o pleito de oitiva das partes.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Protestos das partes.</p>"}, // @ITEM: Instrução
{"t": "Instrução", "h": "<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">A(s) defesa(s) está(ão) nos autos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O Ato Normativo 003626-80.2025.2.00.0000 do CNJ, de setembro de 2025, estipula a obrigatoriedade do registro audiovisual de todas as audiências (arts. 1º e 3º). Nesse sentido, esclareço que a audiência será gravada, com disponibilização de link no acervo eletrônico dos autos, exceto na fase de tratativas de conciliação, ao início e ao final da audiência (CLT, arts. 846 e 850), haja vista a confidencialidade garantida pelo art. 30 da Lei 13.140/15, como aliás já decidiu o TED da OAB/SP (Processo: E-6.115/2023).</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Portanto, os depoimentos prestados na presente audiência serão integralmente gravados, razão pela qual não haverá pelo(a) magistrado (a), a transcrição exata das declarações dos depoentes.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Todavia, visando apenas a facilitação de suas manifestações sobre o conteúdo da prova, será elaborado por ferramenta de Inteligência Artificial (Google) um breve resumo das informações úteis ao julgamento da causa (art. 851 e 852-F da CLT), ficando expressamente destacado que esse breve resumo não substitui, para fins probatórios, a íntegra dos depoimentos - que estarão documentados em meio audiovisual - e nem implica aquiescência das partes quanto ao conteúdo do resumo, servindo apenas e tão somente para auxílio na análise das provas. Portanto, prevalece em caso de divergências a versão original do vídeo disponibilizada no sistema PJe.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Havendo interesse de se valer, em razões finais ou para fins recursais, de trechos específicos dos depoimentos, deverão as partes indicar com precisão o nome do arquivo, o minuto e o segundo em que o trecho degravado está registrado. A parte adversa, caso discorde da degravação, deverá apresentar impugnação especificada.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Oportuno destacar que a gravação da audiência pelas partes e por seus advogados é lícita, independentemente da gravação feita pelo juízo (CPC, art. 367, §§ 5º e 6º), mas deve ser precedida de comunicação e identificação prévia dos envolvidos (Art. 5º, § 1º ato normativo), sendo limitada ao uso processual, sendo EXPRESSAMENTE VEDADA a sua utilização para outras finalidades, notadamente publicações em redes sociais, monetização, transmissões on-line, páginas de internet ou compartilhamentos por meio de aplicativos de mensagens (art. 5º, § 4º, II, B, do referido ato).</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Assim, e considerando ainda que a imagem e a voz humanas são protegidas legal e constitucionalmente contra reproduções não autorizadas pelo titular do direito de personalidade respectivo, ficam as partes advertidas de que o Juízo não autoriza o uso ou a reprodução da imagem e ou da voz de qualquer um dos sujeitos processuais por qualquer meio externo ao processo, físico ou eletrônico, sob pena de responsabilidade civil e criminal dos envolvidos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Neste momento, inicia-se a gravação da audiência.<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Depoimento pessoal do(a) reclamante: Gravado em áudio e vídeo.<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Depoimento pessoal do(a) preposto(a) da 1ª reclamada: Gravado em áudio e vídeo.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">1ª testemunha do(a) <u>reclamante</u>: *, CPF nº *, residente no endereço *.&nbsp;<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">1ª testemunha do(a) <u>reclamado(a)</u>: *, CPF nº *, residente no endereço *.<br>&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As partes não têm outras provas a produzir.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Encerrada a instrução processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Frustrada a última tentativa conciliatória.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Razões finais facultadas no prazo comum de 02 dias, devendo o(a) reclamante manifestar-se acerca da defesa e documentos no mesmo prazo.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Designa-se para julgamento a data de 16/09/2026 às 16:__ horas, sendo que as partes serão intimadas da sentença via Diário Oficial.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Audiência encerrada às %HEC%.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Nada mais.</p>"}, // @ITEM: Victor - Instrução com peritos
{"t": "Victor - Instrução com peritos", "h": "<p style=\"text-align:justify;text-indent:3cm;\"><strong>Prejudicada a conciliação.&nbsp;</strong></p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Recebida a(s) defesa(a) e documentos juntados via sistema.&nbsp;</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Prazo de 5 dias para réplica, sob pena de preclusão.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">O Juízo observa que o reclamante postula o pagamento de adicional de <strong>***periculosidade e ***insalubridade, c</strong>om requerimento de realização de perícia. A fim de imprimir celeridade e efetividade ao feito, proceder-se-á à produção integral da prova oral nesta audiência, inclusive quanto ao objeto da perícia a ser realizada, com a designação de perícia após o encerramento da produção de prova oral.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">A Recomendação CNJ n. 94 de 2021 recomenda aos tribunais brasileiros a gravação de atos processuais, sejam presenciais ou virtuais e a gravação dos depoimentos encontra-se autorizada pelas Resoluções 105/2010 do CNJ, 185/2017 do CSJT e 313/2021 do CSJT. Portanto, os depoimentos prestados na presente audiência serão integralmente gravados, razão pela qual não haverá pelo(a) magistrado (a), a transcrição exata das declarações dos depoentes.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Todavia, visando apenas a facilitação de suas manifestações sobre o conteúdo da prova, será elaborado por ferramenta de Inteligência Artificial (Google) um breve resumo das informações úteis ao julgamento da causa (art. 851 e 852-F da CLT), ficando expressamente destacado que esse breve resumo não substitui, para fins probatórios, a íntegra dos depoimentos - que estarão documentados em meio audiovisual - e nem implica aquiescência das partes quanto ao conteúdo do resumo, servindo apenas e tão somente para auxílio na análise das provas. Portanto, prevalece em caso de divergências a versão original do vídeo disponibilizada no sistema PJe.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Havendo interesse de se valer, em razões finais ou para fins recursais, de trechos específicos dos depoimentos, deverão as partes indicar com precisão o nome do arquivo, o minuto e o segundo em que o trecho degravado está registrado. A parte adversa, caso discorde da degravação, deverá apresentar impugnação especificada.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">A gravação audiovisual de audiências, a despeito de se tratar de faculdade conferida às partes pelo artigo 367, § 6.º, do CPC, destina-se exclusivamente a finalidades endoprocessuais, nos autos da reclamatória trabalhista em que realizada. Assim, e considerando ainda que a imagem e a voz humanas são protegidas legal e constitucionalmente contra reproduções não autorizadas pelo titular do direito de personalidade respectivo, ficam as partes advertidas de que o Juízo não autoriza o uso ou a reprodução da imagem e/ou da voz de qualquer um dos sujeitos processuais por qualquer meio externo ao processo, físico ou eletrônico, sob pena de responsabilidade civil e criminal dos envolvidos.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\"><strong><u>Neste momento, inicia-se a gravação da audiência.</u></strong></p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Depoimento pessoal do(a) reclamante: Gravado em áudio e vídeo.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Depoimento pessoal do(a) preposto(a) da * reclamada: Gravado em áudio e vídeo.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">1ª testemunha do(a) <u>reclamante</u>: *, CPF nº *, residente no endereço *.&nbsp;</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\"><strong>Gravado em áudio e vídeo.</strong></p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">1ª testemunha do(a)&nbsp;<u>reclamando(a)</u>: *, CPF nº *, residente no endereço *.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\"><strong>Gravado em áudio e vídeo.</strong></p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Fica preclusa a produção de prova oral.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Em&nbsp;observância&nbsp;ao&nbsp;disposto&nbsp;no&nbsp; art.&nbsp; 34&nbsp;da&nbsp;Consolidação&nbsp;das Normas da Corregedoria desse Regional, designa-se audiência de <strong>Encerramento da Instrução para o dia 16/09/2026 às 16:__ horas</strong>, dispensado o comparecimento das partes e procuradores.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Audiência encerrada às 15:22.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Nada mais.</p>"}, // @ITEM: Encerramento s/ oitiva
{"t": "Encerramento s/ oitiva", "h": "<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Recebida defesa com documentos. Concede-se o prazo de 05 dias para o reclamante se manifestar sobre a defesa e documentos, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As partes dispensam os depoimentos pessoais reciprocamente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As partes não têm testemunhas.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Fica preclusa a produção de prova oral.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Fica encerrada a instrução processual. Razões finais pelas partes em 05 dias.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Designa-se audiência de JULGAMENTO para o dia 25/09/2026 às 13:55 horas, com intimação via diário oficial.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Audiência encerrada às %HEC%.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Nada mais.</p>"}, // @ITEM: revelia
{"t": "revelia", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Diante da ausência injustificada da reclamada, aplico-lhe a pena de revelia e confissão.</p>"}, // @ITEM: Dispensa Testemunha
{"t": "Dispensa Testemunha", "h": "<p style=\"text-align:justify;text-indent:3cm;\">O reclamante requer a oitiva da testemunha **** , com o intuito de comprovar a existência de vínculo de emprego.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No particular, considero desnecessária a oitiva da testemunha, porquanto os depoimentos pessoais das partes são convergentes entre si, praticamente uníssonos, dirimindo a controvérsia sobre as questões de fato que abarcam o presente processo. Por conta disso, indefiro o depoimento. Protestos.</p>"}],
// @SUBSECAO: S3
                S3: [// @ITEM: provimento
{"t": "provimento", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Prazo de 02 dias para regularização processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O(a) advogado(a) do(a) * requer o adiamento da presente audiência, tendo em vista que a(s) testemunha(s) *, embora convidada(s), não compareceu(ram).&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O advogado requer que a intimação seja feita na forma do Provimento.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Deferido.</p>\
<p style=\"text-align:justify;text-indent:3cm;\"><u>Designa-se nova audiência UNA para o dia /11/26, às * horas, mantendo-se as cominações anteriores.&nbsp;</u></p>\
<p style=\"text-align:justify;text-indent:3cm;\">Servirá o presente como MANDADO DE INTIMAÇÃO DE TESTEMUNHA, comprometendo-se o(a) * a entregar à testemunha acima indicada.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">A ausência ensejará multa e condução coercitiva. Local: Av. Guido Caloi, 1000, Santo Amaro, São Paulo/SP, CEP 05802-140.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Saem cientes &nbsp;da nova designação as seguintes testemunhas:</p>\
<p style=\"text-align:justify;text-indent:3cm;\">-Do reclamante -&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">-Da reclamada -&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As demais testemunhas virão independentemente de notificação, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Lida e conferida a ata pelos presentes é dispensada a assinatura das partes e dos respectivos patronos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Audiência encerrada às .</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Nada mais.</p>"}, // @ITEM: Testemunha - independente
{"t": "Testemunha - independente", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Prazo de 02 dias para regularização processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O(a) advogado(a) do(a) * requer o adiamento da presente audiência, tendo em vista que a(s) testemunha(s) *, embora convidada(s), não compareceu(ram), comprometendo-se a trazê-la(s) na próxima sessão independentemente de intimação, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Defiro.</p>\
<p style=\"text-align:justify;text-indent:3cm;\"><u>Designa-se nova audiência UNA para o dia /11/26, às * horas, mantendo-se as cominações anteriores.&nbsp;</u></p>\
<p style=\"text-align:justify;text-indent:3cm;\">Saem cientes da nova designação as seguintes testemunhas:</p>\
<p style=\"text-align:justify;text-indent:3cm;\">-Do reclamante -&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">-Da reclamada -&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As demais testemunhas virão independentemente de notificação, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Lida e conferida a ata pelos presentes é dispensada a assinatura das partes e dos respectivos patronos.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Registra-se que magistrado, partes e advogados estão no fórum, presencialmente.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Audiência encerrada às %HEC%.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Nada mais.</p>"}, // @ITEM: Citar por mandado e Edital
{"t": "Citar por mandado e Edital", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Considerando que não há comprovante de recebimento da notificação por parte da&nbsp;<strong>***reclamada</strong>, (aviso de recebimento), determino a renovação da citação da ré por&nbsp;<strong>Oficial de Justiça</strong>, a fim de evitar futura alegação de cerceio de defesa, fato que vem ocorrendo com certa frequência nessas situações.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Vale dizer, as notificações postais não são entregues pessoalmente a prepostos das reclamadas ou pessoalmente aos reclamantes, mas sim deixadas em \"caixas de correio\" como uma correspondência comum, o que certamente não se pode aceitar em relação a intimações judiciais.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Cite-se a reclamada por&nbsp;<strong>edital, concomitantemente.</strong></p>"}],
// @SUBSECAO: S4
                S4: [// @ITEM: Alvará
{"t": "Alvará", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">A presente ata tem força de ALVARÁ perante a CEF para liberação do FGTS, assim como suprimindo a inexistência do Termo de Rescisão do Contrato de Trabalho/CD, dos recolhimentos rescisórios do FGTS e do carimbo de baixa da CTPS, fornecendo-se, inclusive, os seguintes elementos relativos ao contrato de trabalho: PIS nº: *, data de admissão: * e demissão: *, CNPJ: *. CTPS * Série *-SP tipo de rescisão do contrato de trabalho::<u>****</u></p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">A presente ata possui força de ALVARÁ perante a CEF, SINE e demais órgãos competentes para requerimento do seguro-desemprego, suprindo, inclusive, a inexistência do TRCT, das guias SD/CD e do carimbo de baixa da CTPS, caso os prazos de carência e eventuais solicitações anteriores forem atendidas. PIS nº: * , data de admissão: * e demissão: *, CNPJ: * CTPS * Série *-SP&nbsp; tipo de rescisão do contrato de trabalho:<u>****</u></p>"}, // @ITEM: Acordo - Suspensão +Retorno ao estado anterior
{"t": "Acordo - Suspensão +Retorno ao estado anterior", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">As partes, neste ato, ajustam a suspensão do processo <strong>até o dia ******</strong>, data do pagamento da última parcela do acordo.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">O(a) reclamante terá o prazo de 15 dias, contado do termo final da suspensão, para noticiar eventual inadimplemento por parte da reclamada, ficando ciente desde já que no seu silêncio considerar-se-ão adimplidas todas as parcelas.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Nessa hipótese, os autos virão conclusos para homologação do acordo e exclusão das demais reclamadas.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Em caso de descumprimento do acordo, o processo retornará ao estado em que se encontrava, isto é, será designada nova audiência ***<strong>UNA / UNA/RS</strong> para recebimento das defesas e instrução do processo, de sorte que eventual valor parcial do acordo quitado será deduzido de futura execução.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Com o pagamento integral do acordo, o(a) reclamante dará geral e plena quitação pelo objeto da inicial e extinto contrato de trabalho.</p>"}, // @ITEM: acordo subsidiária
{"t": "acordo subsidiária", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Fica ajustada, ainda, a responsabilidade subsidiária da segunda reclamada, pelo valor integral do acordo na hipótese de inadimplemento por parte da primeira reclamada. Desta feita, caso descumprido o acordo pela primeira reclamada, a segunda reclamada deverá ser intimada para proceder ao pagamento do quanto inadimplido no prazo de 15 dias, observado o valor das parcelas e a sua periodicidade, sendo certo que na hipótese de pagamento tempestivo pela responsável subsidiária não lhe será cobrada multa acima estipulada, sendo que nesse caso a multa será devida exclusivamente pela primeira reclamada</p>"}, // @ITEM: INSS s/ vínculo
{"t": "INSS s/ vínculo", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Após a quitação do acordo, a reclamada deverá comprovar, em 30 dias, o recolhimento das contribuições previdenciárias relacionadas ao item b da discriminação, na forma do Tema 310 do TST.</p>"}],
// @SUBSECAO: S5
                S5: [// @ITEM: Município revel
{"t": "Município revel", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">A fazenda pública não está dispensada do comparecimento à audiência, razão pela qual a sua ausência acarreta a revelia e consequente confissão (OJ 152 da SDI-I do C. TST), sendo certo que seu preposto poderia ser ouvido em audiência.</p>"}, // @ITEM: Tele - Atraso da reclamada
{"t": "Tele - Atraso da reclamada", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Neste ato, o Juízo aguardou o ingresso da reclamada por 10 minutos e, além disso, o próprio magistrado procedeu ao ingresso nessa sala utilizando as informações constantes no despacho de fls 115, razão pela qual, não há falar sobre qualquer hipótese de irregularidade por inconsistência técnica no acesso à audiência telepresencial.</p>"}]
            }
        };

        var S2 = [// @ITEM: pericia - allan
{"t": "pericia - allan", "h": "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Prazo de 02 dias para regularização processual.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Recebida defesa com documentos. Concede-se o prazo de 05 dias para a reclamante se manifestar sobre a defesa e documentos, apontando eventuais diferenças que entender devidas, ainda que por amostragem, sob pena de preclusão.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Tendo em vista o pedido de adicional de PERICULOSIDADE, determina-se a realização da perícia técnica. Fica nomeado o Sr. Perito Eng. ALLAN STRUCK PINHEIRO - Cel: (11) 94264-5345 - e-mail: peritoallan.pinheiro@gmail.com, devendo apresentar seu laudo no prazo de 30 dias, acompanhado da proposta de honorários, ficando advertido de que eventuais atrasos serão levados em consideração na fixação do valor. Intime-se.&nbsp;</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">No mesmo prazo da réplica acima deferido, as partes poderão apresentar quesitos e indicar assistentes técnicos, sendo que nesta oportunidade o(a) reclamante poderá descrever suas atividades, local e o setor de trabalho, sob pena de preclusão e de serem consideradas as atividades e informações descritas no laudo pericial.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Atente-se o Expert para esta determinação. Fica autorizado o acompanhamento da diligência pelo(a) reclamante e assistentes técnicos das partes, devendo entrar em contato diretamente com o Sr. Perito, sob pena de preclusão.&nbsp;</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">As partes serão intimadas da data da perícia, a qual se realizará no seguinte endereço: *&nbsp;</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">Designa-se audiência de instrução PRESENCIAL para o dia /02/27 às __h00.</p>\
<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">As testemunhas virão independentemente de notificação, sob pena de preclusão. </p>"}, // @ITEM: pericia - regiane
{"t": "pericia - regiane", "h": "<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Prazo de 02 dias para regularização processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Recebida defesa com documentos. Concede-se o prazo de 05 dias para a reclamante se manifestar sobre a defesa e documentos, apontando eventuais diferenças que entender devidas, ainda que por amostragem, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Tendo &nbsp;em &nbsp;vista &nbsp;o &nbsp;pedido &nbsp;de &nbsp;adicional &nbsp;de INSALUBRIDADE, &nbsp;determina-se &nbsp;a &nbsp;realização &nbsp;da perícia técnica. Fica nomeado o Sra. Perita &nbsp;REGIANE SOUZA ROCHA SILVA - e-mail: peritaregianesilva@gmail.com, &nbsp;devendo &nbsp;apresentar &nbsp;seu &nbsp;laudo &nbsp;no &nbsp;prazo &nbsp;de &nbsp;30 &nbsp;dias, &nbsp;acompanhado &nbsp;da proposta &nbsp;de &nbsp;honorários, &nbsp;ficando &nbsp;advertido &nbsp;de &nbsp;que &nbsp;eventuais &nbsp;atrasos &nbsp;serão &nbsp;levados &nbsp;em &nbsp;consideração &nbsp;na fixação do valor. Intime-se.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No &nbsp;mesmo &nbsp;prazo &nbsp;da &nbsp;réplica &nbsp;acima &nbsp;deferido, &nbsp;as &nbsp;partes &nbsp;poderão &nbsp;apresentar &nbsp;quesitos &nbsp;e &nbsp;indicar assistentes &nbsp;técnicos, &nbsp;sendo &nbsp;que &nbsp;nesta &nbsp;oportunidade &nbsp;o(a) &nbsp;reclamante &nbsp;poderá &nbsp;descrever &nbsp;suas &nbsp;atividades, local &nbsp;e &nbsp;o &nbsp;setor &nbsp;de &nbsp;trabalho, &nbsp;sob &nbsp;pena &nbsp;de &nbsp;preclusão &nbsp;e &nbsp;de &nbsp;serem &nbsp;consideradas &nbsp;as &nbsp;atividades &nbsp;e &nbsp;informações descritas no laudo pericial. Atente-se o Expert para esta determinação. Fica &nbsp;autorizado &nbsp;o &nbsp;acompanhamento &nbsp;da &nbsp;diligência &nbsp;pelo(a) &nbsp;reclamante &nbsp;e &nbsp;assistentes técnicos &nbsp;das &nbsp;partes, &nbsp;devendo &nbsp;entrar &nbsp;em &nbsp;contato &nbsp;diretamente &nbsp;com &nbsp;o &nbsp;Sr. &nbsp;Perito, &nbsp;sob &nbsp;pena &nbsp;de preclusão.As &nbsp;partes &nbsp;serão &nbsp;intimadas &nbsp;da &nbsp;data &nbsp;da &nbsp;perícia, &nbsp;a &nbsp;qual &nbsp;se &nbsp;realizará &nbsp;no &nbsp;endereço: Rua&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Designa-se audiência de instrução PRESENCIAL para o dia /02/27 às __h00.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As testemunhas virão independentemente de notificação, sob pena de preclusão.&nbsp;</p>"}, // @ITEM: Pericia - cirino
{"t": "Pericia - cirino", "h": "<p style=\"text-align:justify;text-indent:3cm;\">INCONCILIADOS.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Prazo de 02 dias para regularização processual.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Recebida defesa com documentos. Concede-se o prazo de 05 dias para a reclamante se manifestar sobre a defesa e documentos, apontando eventuais diferenças que entender devidas, ainda que por amostragem, sob pena de preclusão.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Tendo em vista o pedido de PERÍCIA MÉDICA, determina-se a realização da perícia técnica. Fica nomeado o Sr. Perito Médico ALEXANDRE CIRINO, que deverá apresentar seu laudo no prazo de 20 dias após a realização da perícia médica, que ocorrerá na data de 06/10/26 às 14h30min na 3ª Vara do Trabalho do Fórum da Zona Sul: Av. Guido Caloi, 1000, 2º andar, São Paulo/SP - Cel (11) 97160-1309 - e-mail: alecirino@terra.com.br, acompanhado da proposta de honorários, ficando advertido de que eventuais atrasos serão levados em consideração na fixação do valor.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O reclamante deverá portar todas as suas CTPS no dia da perícia. Intime-se.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No mesmo prazo da réplica acima deferido, as partes poderão apresentar quesitos e indicar assistentes técnicos, sendo que nesta oportunidade o(a) reclamante poderá descrever suas atividades, local e o setor de trabalho, sob pena de preclusão e de serem consideradas as atividades e informações descritas no laudo pericial.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Atente-se o Expert para esta determinação.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Fica autorizado o acompanhamento da diligência pelo(a) reclamante assistentes técnicos das partes. As partes já estão cientes da data da perícia médica.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">A ausência da parte reclamante acarretará a preclusão da prova pericial e aplicação de multa por litigância de má fé, se não comprovadamente justificada NOS AUTOS em até 48 horas após a data do exame, independentemente de intimação específica para tanto.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Designa-se audiência de instrução PRESENCIAL para o dia /02/27 às __h00.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">As testemunhas virão independentemente de notificação, sob pena de preclusão.</p>"}, // @ITEM: Pericia Vladia
{"t": "Pericia Vladia", "h": "<p style=\"text-align:justify;text-indent:3cm;\">Tendo em vista o pedido de PERÍCIA MÉDICA, determina-se a realização da perícia técnica.<br>Fica nomeado o Sr. Perito Médico VLADIA JUOZEPAVICIUS GONÇALVES (email vladia2112@yahoo.com.br e telefone: 11 4992-9209), que deverá apresentar seu laudo no prazo de 30 dias após a realização da perícia médica, que ocorrerá em data e local a serem informados pela expert &nbsp;acompanhado da proposta de honorários, ficando advertido de que eventuais atrasos serão levados em consideração na fixação do valor.&nbsp;</p>\
<p style=\"text-align:justify;text-indent:3cm;\">O reclamante deverá portar todas as suas CTPS no dia da perícia. Intime-se.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">No prazo de 05 dias, as partes poderão apresentar quesitos e indicar assistentes técnicos, sendo que nesta oportunidade o(a) reclamante poderá descrever suas atividades, local e o setor de trabalho, sob pena de preclusão e de serem consideradas as atividades e informações descritas no laudo pericial.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Atente-se o Expert para esta determinação.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Fica autorizado o acompanhamento da diligência pelo(a) reclamante assistentes técnicos das partes.</p>\
<p style=\"text-align:justify;text-indent:3cm;\">Designa-se audiência de instrução PRESENCIAL para o dia /11/26 às _h </p>"}];
        var PR = {// @PERITO
"ROGERIO APARECIDO ROSA": {"banco": "001 — Banco do Brasil", "agencia": "1832", "conta": "160235-7"}, // @PERITO
"REGIANE SOUZA ROCHA SILVA": {"banco": "001 — Banco do Brasil", "agencia": "0717", "conta": "127844-4"}, // @PERITO
"CARLOS IRAYBA CREMONINI": {"banco": "341 — Itáu Unibanco", "agencia": "8215", "conta": "13827-5"}, // @PERITO
"ALEXANDRE MARCOS INACO CIRINO": {"banco": "237 — Banco Bradesco", "agencia": "2677", "conta": "0049115-2"}, // @PERITO
"ALLAN STRUCK PINHEIRO": {"banco": "001 — Banco do Brasil", "agencia": "1563", "conta": "30305-4"}, // @PERITO
"MARIANA ACCARDO DE MORAES FONTES": {"banco": "341 — Itáu Unibanco", "agencia": "3768", "conta": "39697-4"}, // @PERITO
"VLADIA JUOZEPAVICIUS GONÇALVES": {"banco": "", "agencia": "", "conta": ""}};
// @SECAO: TEXTO PADRAO HONORARIOS (HH)
        var HH = "<p style=\"margin-left:0cm;text-align:justify;text-indent:3cm;\">A reclamada depositará os honorários periciais no valor de R$*, no prazo de 30 dias, após o pagamento do acordo, na conta do perito * cujos dados bancários seguem: Banco *, agência *, conta corrente *.</p>";

        
    window.AUD_DATA = { perfis: perfis, S2: S2, PR: PR, HH: HH };
    console.log('[Aud.data.js] window.AUD_DATA definido com sucesso. Chaves:', Object.keys(window.AUD_DATA));
})();

```
