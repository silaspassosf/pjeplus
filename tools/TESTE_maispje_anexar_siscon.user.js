// ==UserScript==
// @name         TESTE maisPJe — anexar/siscon
// @namespace    pjeplus.teste
// @version      1.0
// @description  Teste isolado do hover+clique em botao da maisPJe, com log de cada etapa
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @run-at       document-end
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    const LOG_PREFIX = '[TESTE maisPJe]';

    function log(msg, ...args) {
        console.log('%c' + LOG_PREFIX + ' ' + msg, 'color:#0a0;font-weight:bold', ...args);
    }
    function logErro(msg, ...args) {
        console.log('%c' + LOG_PREFIX + ' ' + msg, 'color:#c00;font-weight:bold', ...args);
    }
    function logPasso(msg, ...args) {
        console.log('%c' + LOG_PREFIX + ' ' + msg, 'color:#06c', ...args);
    }

    // ══════════════════════════════════════════════════════════════════
    // CÓPIA FIEL da lógica de Script/modules/atalhos/atalhos.js
    // (hoverAndClickTarget / safeDispatch / esperarElemento)
    // ══════════════════════════════════════════════════════════════════

    function esperarElemento(selector, timeout = 3000) {
        return new Promise((resolve) => {
            const start = Date.now();
            const interval = setInterval(() => {
                const el = document.querySelector(selector);
                if (el && el.offsetParent !== null) { clearInterval(interval); resolve(el); }
                if (Date.now() - start > timeout) { clearInterval(interval); resolve(null); }
            }, 100);
        });
    }

    // ══════════════════════════════════════════════════════════════════
    // TESTE
    // ══════════════════════════════════════════════════════════════════

    async function testar(iconeNome, alvoNome) {
        const wait = (ms) => new Promise(r => setTimeout(r, ms));

        console.log('\n');
        log('════════ INÍCIO DO TESTE ════════');
        log('ícone (hover):', iconeNome, '| alvo (clique):', alvoNome);

        // ── ETAPA 1: achar o ícone ────────────────────────────────────
        logPasso('ETAPA 1 — localizar o ícone do hover');

        const base = document.querySelector('#maisPJe_bt_detalhes_base');
        if (!base) {
            logErro('FALHA: #maisPJe_bt_detalhes_base não existe na página!');
            logErro('A extensão maisPJe está ativa? A barra de botões apareceu?');
            return;
        }
        log('✓ base encontrada:', base.id, '| filhos:', base.children.length);

        const botoes = Array.from(base.querySelectorAll('button[aria-label]'));
        log('botões na base:', botoes.length);
        botoes.forEach((b, i) => {
            const rotulo = b.getAttribute('aria-label');
            if (!rotulo.includes('Expandir')) {
                log('   [' + i + '] id=' + (b.id || '(sem id)') + ' | aria="' + rotulo + '"');
            }
        });

        const MAPA = {
            concluso: 'concluso', movimentar: 'movimentar', movimento: 'movimentar',
            guardar: 'guardarDados', guardarDados: 'guardarDados', gigs: 'gigs',
            anexar: 'anexarDocumentos', anexarDocumentos: 'anexarDocumentos',
            bndt: 'bndt', calculos: 'abrirCalculos', abrirCalculos: 'abrirCalculos',
            intimacao: 'intimacaoEExpediente', intimacaoEExpediente: 'intimacaoEExpediente',
            expedientes: 'Expedientes', lembretes: 'Lembretes', pagamento: 'pagamento',
            retificar: 'retificarAutuacao', retificarAutuacao: 'retificarAutuacao',
            domicilio: 'DomicilioEletronico', DomicilioEletronico: 'DomicilioEletronico'
        };
        const sufixo = MAPA[iconeNome] || iconeNome;
        const iconeEl = base.querySelector('#maisPJe_bt_detalhes_' + sufixo);

        if (!iconeEl) {
            logErro('FALHA: ícone #maisPJe_bt_detalhes_' + sufixo + ' não encontrado!');
            return;
        }
        log('✓ ícone encontrado: id=' + iconeEl.id + ' | aria="' + iconeEl.getAttribute('aria-label') + '"');
        log('   visível? offsetParent=' + (iconeEl.offsetParent ? 'sim' : 'NÃO') +
            ' | display=' + getComputedStyle(iconeEl).display);

        // ── ETAPA 2: hover ────────────────────────────────────────────
        logPasso('ETAPA 2 — disparar hover no ícone');

        function safeDispatch(el, type, opts) {
            try { el.dispatchEvent(new MouseEvent(type, opts || {})); return true; }
            catch (e) {
                try {
                    const safeOpts = Object.assign({}, opts || {});
                    if ('view' in safeOpts) delete safeOpts.view;
                    el.dispatchEvent(new MouseEvent(type, safeOpts));
                    return true;
                } catch (e2) { try { el.click(); return true; } catch (e3) { } }
            }
            return false;
        }

        const opts = { bubbles: true, cancelable: true, view: window };
        ['mouseover', 'mouseenter', 'mousemove'].forEach(tipo => {
            const ok = safeDispatch(iconeEl, tipo, opts);
            log('   dispatch ' + tipo + ' no ícone → ' + (ok ? 'OK' : 'FALHOU'));
        });

        // A extensão usa elementoAtivo para saber se o mouse está no botão.
        // Simulamos o que o browser faria: mouseover no ícone e no container.
        log('   dispatch extra no container base (igual ao motor):');
        ['mouseover', 'mouseenter', 'mousemove'].forEach(tipo => {
            safeDispatch(base, tipo, opts);
        });
        log('   feito');

        // ── ETAPA 3: esperar o container ──────────────────────────────
        logPasso('ETAPA 3 — aguardar o container do menu');
        log('   (a extensão monta os botões 500ms APÓS o hover)');

        const t0 = Date.now();
        let container = null;
        let ultimoLog = 0;

        // Poll manual com log a cada 500ms
        while (Date.now() - t0 < 6000) {
            container = document.querySelector('maisPjeContainerAA');
            const decorrido = Date.now() - t0;

            if (decorrido - ultimoLog >= 500) {
                ultimoLog = decorrido;
                if (container) {
                    log('   ' + decorrido + 'ms → container ENCONTRADO (id=' + (container.id || '(vazio)') +
                        ') botões: ' + container.querySelectorAll('button').length);
                } else {
                    log('   ' + decorrido + 'ms → ainda sem container');
                }
            }
            if (container) break;
            await wait(100);
        }

        if (!container) {
            logErro('FALHA: container maisPjeContainerAA NÃO apareceu em 6s!');
            logErro('   Possíveis causas:');
            logErro('   - mouseover não abriu o menu (a extensão escuta onmouseenter, não mouseover)');
            logErro('   - a extensão está desligada');
            logErro('   - o container tem outro nome');
            log('   Todos os elementos com "maisPje" no id:');
            document.querySelectorAll('[id*="maisPje"], [id*="maispje"]').forEach(e => {
                log('      <' + e.tagName.toLowerCase() + ' id="' + e.id + '">');
            });
            return;
        }

        log('✓ container encontrado em ' + (Date.now() - t0) + 'ms');

        // Detalhar o conteúdo do container
        await wait(600);
        const filhos = container.children;
        log('   container tem ' + filhos.length + ' filhos diretos:');
        Array.from(filhos).forEach((f, i) => {
            if (f.tagName === 'BUTTON') {
                log('      [' + i + '] BUTTON id=' + (f.id || '(sem id)') +
                    ' | name="' + (f.name || '(vazio)') + '"' +
                    ' | texto="' + (f.textContent || '').trim() + '"' +
                    ' | visível=' + (f.style.display !== 'none' && f.offsetParent !== null));
            } else {
                log('      [' + i + '] <' + f.tagName.toLowerCase() + '> id=' + (f.id || '(sem id)') +
                    ' | texto="' + (f.textContent || '').trim().slice(0, 50) + '"');
            }
        });

        // ── ETAPA 4: procurar o alvo ──────────────────────────────────
        logPasso('ETAPA 4 — procurar o alvo "' + alvoNome + '" no container');

        const alvoLower = String(alvoNome).trim().toLowerCase();

        // Critério original do atalhos.js
        const todos = Array.from(container.querySelectorAll('button, div, span, a'));
        log('   candidatos no container: ' + todos.length);

        // Mostrar o que tem name ou texto parecido
        const parecidos = todos.filter(el => {
            const name = (el.getAttribute('name') || '').toLowerCase();
            const texto = (el.textContent || '').toLowerCase();
            return name.includes(alvoLower) || texto.includes(alvoLower);
        });
        log('   candidatos que contêm "' + alvoNome + '": ' + parecidos.length);
        parecidos.forEach(el => {
            log('      <' + el.tagName.toLowerCase() + '> name="' + (el.getAttribute('name') || '') +
                '" texto="' + (el.textContent || '').trim().slice(0, 60) + '"');
        });

        const alvo = todos.find(el => {
            const name = (el.getAttribute('name') || '').toLowerCase();
            const texto = (el.textContent || '').toLowerCase();
            return texto.trim() === alvoLower || name === alvoLower || texto.includes(alvoLower);
        });

        if (!alvo) {
            logErro('FALHA: alvo "' + alvoNome + '" NÃO encontrado no container!');
            logErro('   Todos os botões do container, com name e texto:');
            container.querySelectorAll('button').forEach((b, i) => {
                logErro('      [' + i + '] id=' + (b.id || '(sem id)') +
                    ' | name="' + (b.name || '(vazio)') + '"' +
                    ' | texto="' + (b.textContent || '').trim() + '"');
            });
            return;
        }

        log('✓ alvo encontrado: <' + alvo.tagName.toLowerCase() + '>' +
            ' name="' + (alvo.getAttribute('name') || '') + '"' +
            ' texto="' + (alvo.textContent || '').trim() + '"');
        log('   visível? offsetParent=' + (alvo.offsetParent ? 'sim' : 'NÃO') +
            ' | display=' + getComputedStyle(alvo).display);

        // ── ETAPA 5: clicar ───────────────────────────────────────────
        logPasso('ETAPA 5 — clicar no alvo');

        alvo.style.border = '2px solid red';
        alvo.style.boxShadow = '0 0 10px red';
        await wait(200);

        const wrapper = alvo.querySelector('.mat-button-wrapper');
        log('   .mat-button-wrapper existe? ' + (wrapper ? 'sim' : 'NÃO'));

        if (wrapper) {
            try { wrapper.click(); log('   ✓ wrapper.click() executado'); }
            catch (e) { logErro('   wrapper.click() falhou: ' + e.message); }
        }

        try { alvo.click(); log('   ✓ alvo.click() executado'); }
        catch (e) { logErro('   alvo.click() falhou: ' + e.message); }

        await wait(1500);

        // ── ETAPA 6: verificar resultado ──────────────────────────────
        logPasso('ETAPA 6 — resultado');
        const containerDepois = document.querySelector('maisPjeContainerAA');

        log('   container ainda na tela? ' + (containerDepois ? 'sim' : 'não (fechou = ação executou)'));
        log('   URL atual: ' + location.href);
        log('   (se o SISCON abriu, deve ter aparecido outra aba/janela)');
        log('════════ FIM DO TESTE ════════');
    }

    // ══════════════════════════════════════════════════════════════════
    // PAINEL
    // ══════════════════════════════════════════════════════════════════

    function criarPainel() {
        const painel = document.createElement('div');
        painel.setAttribute('data-teste-maispje', '1');
        painel.style.cssText = [
            'position:fixed', 'bottom:76px', 'right:20px', 'z-index:2147483647',
            'background:#1e1e2e', 'color:#cdd6f4', 'border-radius:10px',
            'padding:12px', 'font:13px monospace', 'box-shadow:0 4px 20px rgba(0,0,0,.5)',
            'display:flex', 'flex-direction:column', 'gap:8px', 'min-width:260px'
        ].join(';');

        const titulo = document.createElement('div');
        titulo.textContent = '🧪 Teste maisPJe';
        titulo.style.cssText = 'font-weight:bold;color:#a6e3a1;margin-bottom:4px';
        painel.appendChild(titulo);

        const inputIcone = document.createElement('input');
        inputIcone.value = 'anexar';
        inputIcone.placeholder = 'ícone (hover)';
        inputIcone.style.cssText = 'padding:6px;border-radius:5px;border:1px solid #45475a;background:#313244;color:#cdd6f4;font:12px monospace';
        painel.appendChild(inputIcone);

        const inputAlvo = document.createElement('input');
        inputAlvo.value = 'siscon';
        inputAlvo.placeholder = 'alvo (clique)';
        inputAlvo.style.cssText = 'padding:6px;border-radius:5px;border:1px solid #45475a;background:#313244;color:#cdd6f4;font:12px monospace';
        painel.appendChild(inputAlvo);

        const btn = document.createElement('button');
        btn.textContent = '▶ Executar teste';
        btn.style.cssText = 'padding:8px;border:none;border-radius:5px;background:#89b4fa;color:#1e1e2e;font:bold 13px monospace;cursor:pointer';
        btn.onclick = () => {
            btn.disabled = true;
            btn.textContent = '⏳ Executando...';
            console.clear();
            testar(inputIcone.value.trim(), inputAlvo.value.trim()).finally(() => {
                btn.disabled = false;
                btn.textContent = '▶ Executar teste';
            });
        };
        painel.appendChild(btn);

        const dica = document.createElement('div');
        dica.textContent = 'Resultado no console (F12)';
        dica.style.cssText = 'font-size:11px;color:#6c7086;text-align:center';
        painel.appendChild(dica);

        document.body.appendChild(painel);
        return painel;
    }

    // Botão flutuante para abrir/fechar o painel
    const fab = document.createElement('button');
    fab.textContent = '🧪';
    fab.title = 'Teste maisPJe anexar/siscon';
    fab.style.cssText = [
        'position:fixed', 'bottom:20px', 'right:20px', 'z-index:2147483646',
        'width:44px', 'height:44px', 'border-radius:50%', 'border:none',
        'background:#89b4fa', 'color:#1e1e2e', 'font-size:20px', 'cursor:pointer',
        'box-shadow:0 4px 16px rgba(0,0,0,.4)'
    ].join(';');
    fab.onclick = () => {
        const aberto = document.querySelector('[data-teste-maispje]');
        if (aberto) { aberto.remove(); }
        else { criarPainel(); }
    };
    document.body.appendChild(fab);

    console.log('%c[TESTE maisPJe] carregado — clique no 🧪 no canto inferior direito',
        'color:#89b4fa;font-weight:bold');
})();
