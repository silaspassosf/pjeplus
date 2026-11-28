'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD — desbloquear.js (botão "Desbloquear")
// Onde: https://sisbajud.pdpj.jus.br/ordem-judicial/*/desdobrar (e /detalhar)
// O que faz, ao clicar:
//   1. Altera os mat-select visíveis em "Transferir valor" para "Desbloquear valor"
//   2. Clica em "Salvar" (button.mat-fab.mat-primary)
//   3. Aguarda aparecer e clica em "Protocolar"
//   4. Na dialog de protocolo, preenche a senha e clica em "Confirmar"
// Injetado pelo orquestrador (sisbajud.js → injetarUI), sem timer próprio.
// ═══════════════════════════════════════════════════════════════════

(function () {
    if (window.SisbDesbloquear) return;

    var ID_BOTAO = 'pjetools-sisb-desbloquear-btn';
    var TEXTO_PADRAO = 'Desbloquear';
    var CHAVE_SENHA = 'pjeplus_sisb_senha';
    var BRIDGE_URL = 'http://127.0.0.1:8765/cred/sisb-senha';
    var TITULO_INFO = 'Dados da Ordem Judicial de Requisição de Informações';
    var executando = false;

    function norm(s) {
        return String(s || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase();
    }

    function esperar(ms) {
        return new Promise(function (r) { setTimeout(r, ms); });
    }

    async function esperarAte(fn, timeoutMs, intervaloMs) {
        var fim = Date.now() + (timeoutMs || 4000);
        var passo = intervaloMs || 120;
        while (Date.now() < fim) {
            var res = fn();
            if (res) return res;
            await esperar(passo);
        }
        return null;
    }

    function visivel(el) {
        if (!el || !el.isConnected) return false;
        var st = window.getComputedStyle(el);
        if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
        var r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
    }

    function naRotaAlvo() {
        var h = window.location.hostname || '';
        if (!/^sisbajud\.(pdpj|cnj)\.jus\.br$/.test(h)) return false;
        return /^\/ordem-judicial\/[^/]+\/(desdobrar|detalhar)\/?$/.test(window.location.pathname || '');
    }

    function ehRequisicaoInformacoes() {
        var titulos = document.querySelectorAll('mat-card-title');
        var alvo = norm(TITULO_INFO);
        for (var i = 0; i < titulos.length; i++) {
            if (norm(titulos[i].textContent).indexOf(alvo) > -1) return true;
        }
        return false;
    }

    function temDropdownsOuPaineis() {
        return !!(document.querySelector('mat-select') || document.querySelector('mat-expansion-panel-header'));
    }

    function toast(msg, tipo) {
        if (window.SisbCore && typeof window.SisbCore.mostrarToast === 'function') {
            window.SisbCore.mostrarToast(msg, tipo || 'info');
            return;
        }
        var cores = { ok: '#2e7d32', erro: '#c62828', aviso: '#ef6c00', info: '#1565c0' };
        var d = document.createElement('div');
        d.style.cssText = 'position:fixed;top:20px;right:20px;z-index:2147483002;background:' +
            (cores[tipo] || cores.info) + ';color:#fff;padding:10px 16px;border-radius:6px;' +
            'font:bold 13px Arial,sans-serif;box-shadow:0 3px 10px rgba(0,0,0,.3);';
        d.textContent = msg;
        document.body.appendChild(d);
        setTimeout(function () { if (d.parentNode) d.remove(); }, 4500);
    }

    // ── Senha do SISBAJUD (bridge local keyring -> GM_getValue -> prompt) ──
    function obterSenhaBridge() {
        return new Promise(function (resolve) {
            if (typeof GM_xmlhttpRequest !== 'function') { resolve(''); return; }
            GM_xmlhttpRequest({
                method: 'GET',
                url: BRIDGE_URL,
                timeout: 1500,
                onload: function (r) {
                    try {
                        var j = JSON.parse(r.responseText || '{}');
                        if (r.status === 200 && j && j.ok && j.senha) {
                            resolve(String(j.senha));
                            return;
                        }
                    } catch (e) { /* noop */ }
                    resolve('');
                },
                onerror: function () { resolve(''); },
                ontimeout: function () { resolve(''); },
            });
        });
    }

    async function obterSenhaSisbajud() {
        var viaBridge = await obterSenhaBridge();
        if (viaBridge) return viaBridge;

        var salva = '';
        try {
            if (typeof GM_getValue === 'function') salva = String(GM_getValue(CHAVE_SENHA, '') || '');
        } catch (e) { /* noop */ }
        if (salva) return salva;

        var digitada = window.prompt(
            'Informe a senha do SISBAJUD para protocolar (ficará salva apenas localmente no Tampermonkey):'
        );
        if (!digitada) return '';
        try {
            if (typeof GM_setValue === 'function') GM_setValue(CHAVE_SENHA, digitada);
        } catch (e) { /* noop */ }
        return digitada;
    }

    function preencherInputAngular(input, valor) {
        input.focus();
        var desc = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
        if (desc && desc.set) {
            desc.set.call(input, valor);
        } else {
            input.value = valor;
        }
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'Enter' }));
    }

    // ── 1. Mudar todos os dropdowns visíveis "Transferir" -> "Desbloquear" ──
    function listarSelectsTransferir() {
        return Array.from(document.querySelectorAll('mat-select')).filter(function (sel) {
            if (!visivel(sel)) return false;
            if (sel.getAttribute('aria-disabled') === 'true' || sel.classList.contains('mat-select-disabled')) return false;
            var txt = norm(sel.textContent);
            return txt.indexOf('transferir') > -1;
        });
    }

    async function fecharOverlaySeAberto() {
        var backdrop = document.querySelector('.cdk-overlay-backdrop.cdk-overlay-backdrop-showing');
        if (backdrop) {
            backdrop.click();
            await esperar(180);
            return;
        }
        if (document.querySelector('mat-option[role="option"]')) {
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }));
            await esperar(180);
        }
    }

    async function trocarTodosParaDesbloquear(btn) {
        var alterados = 0;
        var tentativasMax = 40;
        var visitados = new Set();

        for (var passo = 0; passo < tentativasMax; passo++) {
            var pendentes = listarSelectsTransferir().filter(function (s) { return !visitados.has(s); });
            if (!pendentes.length) break;

            var sel = pendentes[0];
            visitados.add(sel);

            btn.textContent = 'Desbloqueando (' + (alterados + 1) + ')...';
            sel.scrollIntoView({ block: 'center' });
            await esperar(100);
            sel.click();

            var opcoes = await esperarAte(function () {
                var lista = Array.from(document.querySelectorAll('mat-option[role="option"]')).filter(visivel);
                return lista.length ? lista : null;
            }, 2500, 80);

            if (!opcoes) {
                await fecharOverlaySeAberto();
                continue;
            }

            var alvo = opcoes.find(function (o) { return norm(o.textContent) === 'desbloquear valor'; }) ||
                opcoes.find(function (o) { return norm(o.textContent).indexOf('desbloquear') > -1; });

            if (alvo) {
                alvo.click();
                alterados++;
                await esperarAte(function () {
                    return !document.querySelector('mat-option[role="option"]');
                }, 1500, 80);
                await esperar(180);
            } else {
                await fecharOverlaySeAberto();
            }
        }
        return alterados;
    }

    // ── 3. Salvar e Protocolar ───────────────────────────────────────
    function acharBotaoSalvar() {
        var fabs = Array.from(document.querySelectorAll('button.mat-fab.mat-primary, button.mat-fab'));
        for (var i = 0; i < fabs.length; i++) {
            if (!visivel(fabs[i]) || fabs[i].disabled) continue;
            var t = norm(fabs[i].textContent) + ' ' + norm(fabs[i].getAttribute('title')) + ' ' + norm(fabs[i].getAttribute('aria-label'));
            if (t.indexOf('salvar') > -1) return fabs[i];
        }
        var todos = Array.from(document.querySelectorAll('button'));
        for (var j = 0; j < todos.length; j++) {
            if (!visivel(todos[j]) || todos[j].disabled) continue;
            if (norm(todos[j].textContent) === 'salvar') return todos[j];
        }
        return null;
    }

    function acharBotaoProtocolar() {
        var botoes = Array.from(document.querySelectorAll('button'));
        for (var i = 0; i < botoes.length; i++) {
            var b = botoes[i];
            if (!visivel(b) || b.disabled) continue;
            if (b.id === ID_BOTAO) continue;
            var t = norm(b.textContent) + ' ' + norm(b.getAttribute('title')) + ' ' + norm(b.getAttribute('aria-label'));
            if (t.indexOf('protocolar') > -1) return b;
        }
        return null;
    }

    function acharCampoSenhaNoModal() {
        var modal = document.querySelector('mat-dialog-container');
        if (!modal || !visivel(modal)) return null;
        return modal.querySelector('input[type="password"]') ||
            modal.querySelector('input.mat-input-element[formcontrolname="senha"]') ||
            modal.querySelector('input.mat-input-element');
    }

    function acharBotaoConfirmarNoModal() {
        var modal = document.querySelector('mat-dialog-container');
        if (!modal) return null;
        var botoes = Array.from(modal.querySelectorAll('button'));
        return botoes.find(function (b) {
            return visivel(b) && !b.disabled && norm(b.textContent) === 'confirmar';
        }) || botoes.find(function (b) {
            return visivel(b) && !b.disabled && norm(b.textContent).indexOf('confirmar') > -1;
        }) || null;
    }

    async function finalizarSalvarEProtocolar(btn) {
        // 3a. Clicar em Salvar
        btn.textContent = 'Salvando...';
        var btnSalvar = acharBotaoSalvar();
        if (!btnSalvar) {
            toast('Dropdowns alterados, mas botão Salvar não foi encontrado.', 'aviso');
            return false;
        }
        btnSalvar.scrollIntoView({ block: 'center' });
        btnSalvar.click();

        // Aguarda o botão Protocolar aparecer após o Salvar (e fecha snackbar OK se vier)
        btn.textContent = 'Aguardando Protocolar...';
        var btnProto = await esperarAte(function () {
            var snackOk = document.querySelector('button.snack-messenger-close-button');
            if (snackOk && visivel(snackOk)) snackOk.click();
            return acharBotaoProtocolar();
        }, 8000, 150);

        if (!btnProto) {
            toast('Salvo! Botão Protocolar não apareceu na tela.', 'aviso');
            return false;
        }

        // 3b. Clicar em Protocolar para abrir a dialog de senha
        btn.textContent = 'Protocolando...';
        btnProto.scrollIntoView({ block: 'center' });
        await esperar(150);
        btnProto.click();

        // 3c. Aguardar modal "Protocolar - Digite sua senha para confirmar"
        var campoSenha = await esperarAte(acharCampoSenhaNoModal, 6000, 120);
        if (!campoSenha) {
            toast('Modal de senha para protocolar não abriu.', 'aviso');
            return false;
        }

        var senha = await obterSenhaSisbajud();
        if (!senha) {
            toast('Senha não informada — digite manualmente e clique em Confirmar.', 'aviso');
            return false;
        }

        preencherInputAngular(campoSenha, senha);
        await esperar(250);

        var btnConfirmar = await esperarAte(acharBotaoConfirmarNoModal, 3000, 100);
        if (!btnConfirmar) {
            toast('Senha preenchida, mas botão Confirmar não ficou habilitado.', 'aviso');
            return false;
        }

        btn.textContent = 'Confirmando...';
        btnConfirmar.click();
        return true;
    }

    // ── Ação principal do botão ──────────────────────────────────────
    async function aoClicar(btn) {
        if (executando) return;
        executando = true;
        btn.disabled = true;
        btn.style.opacity = '0.75';

        try {
            var alterados = await trocarTodosParaDesbloquear(btn);
            console.log('[SisbDesbloquear] dropdowns alterados para Desbloquear valor:', alterados);

            var protocolou = await finalizarSalvarEProtocolar(btn);
            if (protocolou) {
                toast('Desbloqueio salvo e protocolado (' + alterados + ' alterado(s))!', 'ok');
                btn.textContent = 'Protocolado!';
                setTimeout(function () {
                    btn.textContent = TEXTO_PADRAO;
                    btn.disabled = false;
                    btn.style.opacity = '1';
                    executando = false;
                }, 2500);
                return;
            }
        } catch (e) {
            console.error('[SisbDesbloquear] erro:', e);
            toast('Erro ao desbloquear: ' + ((e && e.message) || e), 'erro');
        }

        btn.textContent = TEXTO_PADRAO;
        btn.disabled = false;
        btn.style.opacity = '1';
        executando = false;
    }

    // ── Injeção do botão (centro inferior) ───────────────────────────
    function injetarBotao() {
        if (!document.body) return;
        var existente = document.getElementById(ID_BOTAO);

        if (!naRotaAlvo() || ehRequisicaoInformacoes() || !temDropdownsOuPaineis()) {
            if (existente) existente.remove();
            return;
        }
        if (existente) return;

        var btn = document.createElement('button');
        btn.id = ID_BOTAO;
        btn.type = 'button';
        btn.textContent = TEXTO_PADRAO;
        btn.title = 'Muda todos os dropdowns Transferir para Desbloquear, salva e protocola';
        btn.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:999999;' +
            'padding:12px 22px;border:none;border-radius:8px;background:#c62828;color:#fff;' +
            'font:bold 15px Arial,sans-serif;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);';
        btn.addEventListener('click', function () { aoClicar(btn); });
        document.body.appendChild(btn);
    }

    window.SisbDesbloquear = {
        injetarBotao: injetarBotao,
        executar: function () {
            var b = document.getElementById(ID_BOTAO);
            if (b) aoClicar(b);
        },
        limparSenhaSalva: function () {
            try { if (typeof GM_deleteValue === 'function') GM_deleteValue(CHAVE_SENHA); } catch (e) { /* noop */ }
        },
    };
})();
