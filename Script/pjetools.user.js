// ==UserScript==
// @name         PJe Tools Pro
// @namespace    http://tampermonkey.net/
// @version      2.1.62
// @description  Suite de ferramentas para PJe
// @author       Silas
// ── PJe (cobre todas as rotas com um único match)
// @match        https://pje.trt2.jus.br/*
// @match        https://pje1g.trt2.jus.br/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
// ── Externos (domínios distintos mantidos individuais)
// @match        https://sisbajud.cnj.jus.br/*
// @match        https://sisbajud.pdpj.jus.br/*
// @match        https://cav.receita.fazenda.gov.br/Servicos/ATSDR/Decjuiz/*
// @match        https://simba-novo.redejt/*
// @match        https://www3.bcb.gov.br/saj/requisicao-extratos-cadastro*
// ── Único require: o loader (bumpar só ele ao adicionar módulos)
// (loader injetado inline — remove dependência externa)
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_openInTab
// @grant        window.close
// @grant        unsafeWindow
// @run-at       document-idle
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/utils.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/state.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/extrair.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.check.js?v=2.1.37
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.edital.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/lista/lista.pgto.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/atalhos/atalhos.worker.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/ui/painel.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/infojud/infojud.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/core.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/relatorios.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/sisbajud/sisbajud.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/debito/registrar_debito.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/modules/simba/simba.js?v=2.1.62
// ==/UserScript==

(async function () {
    'use strict';
    console.log('[Loader] PJe Tools Pro v2.1.62 loaded');
    if (window.self !== window.top) return;

    // W = window real da página (unsafeWindow quando disponível)
    const W = (typeof unsafeWindow !== 'undefined') ? unsafeWindow : window;

    const url = window.location.href;

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

        // ── Roteamento (só roda DEPOIS de tudo carregado)
        const isMinutas  = url.includes('/comunicacoesprocessuais/minutas');
        const isDetalhe  = /\/processo\/\d+\/detalhe/.test(url);
        const isObrigacao = url.includes('/obrigacao-pagar/');

        if (isMinutas) {
            // FIX #3: usar flag em memória por sessão para evitar persistência entre navegações SPA
            if (window.__infojudWorkerRodando) return;
            window.__infojudWorkerRodando = true;
            console.log('[Loader] Iniciando Worker Infojud...');

            setTimeout(() => {
                if (W.runInfojudWorker) {
                    W.runInfojudWorker();
                } else {
                    console.error('[Loader] runInfojudWorker não encontrado no window! Verifique o @require do infojud.js.');
                }
                // liberar para próximas navegações SPA
                window.__infojudWorkerRodando = false;
            }, 1500);
            return;
        }

        if (isObrigacao) {
            setTimeout(() => {
                try {
                    if (/\/obrigacao-pagar\/\d+\/cadastro/.test(url)) {
                        window.PjeRegistrarDebito?.onCadastro();
                    } else if (/\/obrigacao-pagar\/\d+\/inclusao/.test(url)) {
                        window.PjeRegistrarDebito?.onInclusao();
                    }
                } catch (e) { console.error('[Loader] erro ao iniciar PjeRegistrarDebito:', e); }
            }, 1500);
            return;
        }

        if (!isDetalhe) return;

        // ── Detalhe: registrar SPA monitor uma vez e inicializar
        if (!window.__pjeToolsLoaded) {
            window.__pjeToolsLoaded = true;

            window.monitorarSPA && window.monitorarSPA(() => {
                window.PJeState && window.PJeState.dispose();
                setTimeout(() => {
                    if (/\/processo\/\d+\/detalhe/.test(window.location.href)) {
                        bootDetalhe();
                    }
                }, 300);
            });
        }

        bootDetalhe();

        function bootDetalhe() {
            if (!/\/processo\/\d+\/detalhe/.test(window.location.href)) return;
            // FIX: módulos registrados via @require expõem suas funções no sandbox `window`,
            // portanto chamamos `window.*` aqui em vez de `W` (unsafeWindow).
            if (!window.PJeState || window.PJeState._iniciado) return;
            window.PJeState._iniciado = true;
            window.inicializarPainel && window.inicializarPainel();
            window.initAtalhos && window.initAtalhos();
        }
    }
})();
