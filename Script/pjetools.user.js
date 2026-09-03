// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      2.3.42
// @description  Suite de ferramentas para PJe
// @author       Silas
// ── PJe (cobre todas as rotas com um único match)
// @match        https://pje.trt2.jus.br/aud/*
// @match        https://pje.trt2.jus.br/*
// @match        https://pje.trt2.jus.br/pjekz/*
// @match        https://pje.trt2.jus.br/primeirograu/*
// @match        https://pje.trt2.jus.br/segundograu/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
// @match        https://simba-novo.redejt/*
// @match        https://www3.bcb.gov.br/saj/requisicao-extratos-cadastro*
// ── Único require: o loader (bumpar só ele ao adicionar módulos)
// (loader injetado inline — remove dependência externa)
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_deleteValue
// @grant        GM_openInTab
// @grant        GM_xmlhttpRequest
// @grant        window.close
// @grant        unsafeWindow
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
// @require      https://unpkg.com/tesseract.js@5.1.1/dist/tesseract.min.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/utils.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/state.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/extrair.js?v=2.3.20
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.check.js?v=2.3.2
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.edital.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.pgto.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.worker.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/ui/painel.js?v=2.1.72
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/infojud/infojud.js?v=2.1.73
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/core.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/relatorios.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/sisbajud.js?v=2.1.78
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/sisbpje.js?v=2.3.18
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/extracao_siscondj.js?v=2.1.2
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/siscon_consulta.js?v=2.1.10
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/simba/simba.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/debito/registrar_debito.js?v=2.1.70
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/argos/argos.js?v=2.3.1
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/Aud/Aud.js?v=2.3.19
// ==/UserScript==

(async function () {
    'use strict';
    console.log('[Loader] PJe Tools Pro v2.2.0 loaded');

    const url = window.location.href;
    const isAud = url.includes('/aud/');
    
    // Módulos SISB carregados via @require (git), como os demais módulos.
    // Permite execução em iframes APENAS se for ambiente AUD
    if (window.self !== window.top && !isAud) return;

    // W = window real da página (unsafeWindow quando disponível)
    const W = (typeof unsafeWindow !== 'undefined') ? unsafeWindow : window;

    const isReceita  = url.includes('cav.receita.fazenda.gov.br');
    const isSisbajud = url.includes('sisbajud.cnj.jus.br') || url.includes('sisbajud.pdpj.jus.br');
    const isPjeDomain = url.includes('pje.trt2.jus.br') || url.includes('pje1g.trt2.jus.br');
    const isBcb = url.includes('bcb.gov.br/saj/requisicao-extratos-cadastro');

    // (No match da Receita, content scripts já estão via @require em header)
    if (isSisbajud) return;

    // ── Lógica BCB (terceira execução Simba) ──
    if (isBcb) {
        console.log('[Loader] Detectada URL do BCB, carregando Simba BCB...');
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
            const routeAud = window.location.pathname.startsWith('/aud/') && window.location.hash.startsWith('#/audiencia');

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
                    } catch (e) {}
                }, 1500);
                return;
            }

            if (routeAud) {
                console.log('[Loader] Detectado ambiente AUD:', window.location.href);

                setTimeout(() => {
                    const audApi = window.PJeAud || W.PJeAud;

                    if (typeof audApi?.init !== 'function') {
                        console.error('[Loader] PJeAud.init não encontrado.', {
                            windowPJeAud: window.PJeAud,
                            unsafeWindowPJeAud: W.PJeAud
                        });
                        return;
                    }

                    if (window.__pjeAudInicializado) {
                        console.log('[Loader] AUD já inicializado.');
                        return;
                    }

                    window.__pjeAudInicializado = true;
                    audApi.init();
                    console.log('[Loader] PJeAud inicializado com sucesso.');
                }, 1500);
                
                return;
            }

            if (routeDetalhe) {
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
        }
    }
})();
