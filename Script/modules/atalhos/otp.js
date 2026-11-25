'use strict';

/**
 * Script/modules/atalhos/otp.js
 * Botões manuais de preenchimento TOTP (PJe / SISBAJUD) na tela de SSO Keycloak.
 * Segredos ficam APENAS no storage local do Tampermonkey (GM_getValue/GM_setValue),
 * nunca no código-fonte.
 */
(function () {
    const STORAGE_KEYS = {
        pje: 'pjeplus_totp_secret_pje',
        sisb: 'pjeplus_totp_secret_sisb',
    };
    const BRIDGE_BASE_URL = 'http://127.0.0.1:8765';
    const SESSION_CTX_KEY = 'pjeplus_sso_ctx';
    const CONTAINER_ID = 'pjeplus-otp-bar';
    const OTP_SELECTOR = '#otp, input[name="otp"]';

    // ── Bridge local (Windows Credential Manager via tools/otp_bridge.py) ────
    function obterTotpViaKeyring(tipo) {
        const url = `${BRIDGE_BASE_URL}/otp/${tipo === 'sisb' ? 'sisb' : 'pje'}`;
        return new Promise((resolve) => {
            if (typeof GM_xmlhttpRequest === 'function') {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url,
                    timeout: 1800,
                    onload: (resp) => {
                        try {
                            const data = JSON.parse(resp.responseText || '{}');
                            if (resp.status === 200 && data && data.ok && data.codigo) {
                                resolve({ ok: true, codigo: String(data.codigo), restante: Number(data.restante || 0) });
                                return;
                            }
                            resolve({ ok: false, motivo: data?.erro || `HTTP ${resp.status}` });
                        } catch (e) {
                            resolve({ ok: false, motivo: 'Resposta inválida do bridge' });
                        }
                    },
                    onerror: () => resolve({ ok: false, offline: true }),
                    ontimeout: () => resolve({ ok: false, offline: true }),
                });
                return;
            }
            resolve({ ok: false, offline: true });
        });
    }

    // ── Storage seguro (GM_* com fallback localStorage) ──────────────────────
    function lerValor(chave) {
        try {
            if (typeof GM_getValue === 'function') return GM_getValue(chave, '') || '';
        } catch (e) { /* noop */ }
        try {
            return localStorage.getItem(chave) || '';
        } catch (e) {
            return '';
        }
    }

    function salvarValor(chave, valor) {
        try {
            if (typeof GM_setValue === 'function') {
                GM_setValue(chave, valor);
                return;
            }
        } catch (e) { /* noop */ }
        try {
            localStorage.setItem(chave, valor);
        } catch (e) { /* noop */ }
    }

    // ── TOTP RFC 6238 (HMAC-SHA1, 30s, 6 dígitos) via Web Crypto API ─────────
    function extrairSeedBase32(raw) {
        if (!raw) return '';
        let txt = String(raw).trim();
        if (txt.toLowerCase().startsWith('otpauth://')) {
            try {
                const u = new URL(txt);
                txt = u.searchParams.get('secret') || '';
            } catch (e) {
                const m = txt.match(/[?&]secret=([^&]+)/i);
                txt = m ? decodeURIComponent(m[1]) : '';
            }
        }
        return txt.toUpperCase().replace(/[^A-Z2-7]/g, '');
    }

    function base32ParaBytes(base32) {
        const alfabeto = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
        let bits = 0;
        let valor = 0;
        const saida = [];
        for (let i = 0; i < base32.length; i++) {
            const idx = alfabeto.indexOf(base32[i]);
            if (idx === -1) continue;
            valor = (valor << 5) | idx;
            bits += 5;
            if (bits >= 8) {
                bits -= 8;
                saida.push((valor >>> bits) & 0xff);
            }
        }
        return new Uint8Array(saida);
    }

    async function gerarTotp(secretRaw, periodo = 30, digitos = 6) {
        const seed = extrairSeedBase32(secretRaw);
        if (!seed) return null;

        const keyBytes = base32ParaBytes(seed);
        if (!keyBytes.length) return null;

        const agoraSeg = Math.floor(Date.now() / 1000);
        const contador = Math.floor(agoraSeg / periodo);
        const restante = periodo - (agoraSeg % periodo);

        const buf = new ArrayBuffer(8);
        const view = new DataView(buf);
        const hi = Math.floor(contador / 0x100000000);
        const lo = contador >>> 0;
        view.setUint32(0, hi, false);
        view.setUint32(4, lo, false);

        const cryptoKey = await crypto.subtle.importKey(
            'raw',
            keyBytes,
            { name: 'HMAC', hash: 'SHA-1' },
            false,
            ['sign']
        );
        const assinatura = new Uint8Array(await crypto.subtle.sign('HMAC', cryptoKey, buf));
        const offset = assinatura[assinatura.length - 1] & 0x0f;
        const binario =
            ((assinatura[offset] & 0x7f) << 24) |
            ((assinatura[offset + 1] & 0xff) << 16) |
            ((assinatura[offset + 2] & 0xff) << 8) |
            (assinatura[offset + 3] & 0xff);

        const mod = Math.pow(10, digitos);
        const codigo = String(binario % mod).padStart(digitos, '0');
        return { codigo, restante };
    }

    // ── Detecção de contexto (PJe vs SISBAJUD) ───────────────────────────────
    function detectarContexto() {
        const href = (window.location.href || '').toLowerCase();
        const params = new URLSearchParams(window.location.search || '');
        const clientId = (params.get('client_id') || '').toLowerCase();
        const redirectUri = (params.get('redirect_uri') || '').toLowerCase();

        if (clientId.includes('sisbajud') || redirectUri.includes('sisbajud') || href.includes('sisbajud')) {
            try { sessionStorage.setItem(SESSION_CTX_KEY, 'sisb'); } catch (e) { /* noop */ }
            return 'sisb';
        }
        if (clientId.includes('pje') || redirectUri.includes('pje.trt')) {
            try { sessionStorage.setItem(SESSION_CTX_KEY, 'pje'); } catch (e) { /* noop */ }
            return 'pje';
        }

        // Na tela pós-submit (/login-actions/authenticate), o client_id pode estar no form ou em sessionStorage
        const formAction = (document.querySelector('form')?.getAttribute('action') || '').toLowerCase();
        if (formAction.includes('sisbajud')) {
            try { sessionStorage.setItem(SESSION_CTX_KEY, 'sisb'); } catch (e) { /* noop */ }
            return 'sisb';
        }

        try {
            const salvo = sessionStorage.getItem(SESSION_CTX_KEY);
            if (salvo === 'sisb' || salvo === 'pje') return salvo;
        } catch (e) { /* noop */ }

        return null;
    }

    // ── Preenchimento do campo OTP ───────────────────────────────────────────
    function localizarCampoOtp() {
        return document.querySelector(OTP_SELECTOR);
    }

    function preencherInput(input, valor) {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
        if (setter) {
            setter.call(input, valor);
        } else {
            input.value = valor;
        }
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        input.focus();
    }

    function pedirEGravarSeed(tipo) {
        const rotulo = tipo === 'sisb' ? 'SISBAJUD' : 'PJe';
        const atual = lerValor(STORAGE_KEYS[tipo]);
        const aviso = atual ? ' (já configurado — deixe vazio para cancelar)' : '';
        const entrada = window.prompt(
            `Informe a chave TOTP (Base32 ou URI otpauth://) para ${rotulo}${aviso}:`,
            ''
        );
        if (!entrada || !entrada.trim()) return null;
        const limpa = extrairSeedBase32(entrada);
        if (!limpa || limpa.length < 8) {
            window.alert(`Chave TOTP inválida para ${rotulo}. Verifique o segredo Base32.`);
            return null;
        }
        salvarValor(STORAGE_KEYS[tipo], limpa);
        return limpa;
    }

    async function acionarBotaoOtp(tipo, statusEl) {
        const input = localizarCampoOtp();
        if (!input) {
            if (statusEl) statusEl.textContent = 'Campo OTP não encontrado.';
            return;
        }

        const rotulo = tipo === 'sisb' ? 'SISB' : 'PJe';
        if (statusEl) {
            statusEl.textContent = `Buscando ${rotulo} no keyring...`;
            statusEl.style.color = '#495057';
        }

        // 1) Prioridade: Windows Credential Manager (keyring) via bridge local
        const viaBridge = await obterTotpViaKeyring(tipo);
        if (viaBridge && viaBridge.ok) {
            preencherInput(input, viaBridge.codigo);
            if (statusEl) {
                statusEl.textContent = `${rotulo}: ${viaBridge.codigo} (${viaBridge.restante}s • keyring)`;
                statusEl.style.color = '#1b5e20';
            }
            return;
        }

        // 2) Fallback: segredo salvo no storage local do Tampermonkey (se já configurado)
        const secret = lerValor(STORAGE_KEYS[tipo]);
        if (!secret) {
            if (statusEl) {
                statusEl.textContent = viaBridge?.offline
                    ? 'Bridge keyring offline (inicie tools/otp_bridge.py) ou configure em ⚙'
                    : (viaBridge?.motivo || `Chave ${rotulo} não encontrada no keyring`);
                statusEl.style.color = '#b71c1c';
            }
            return;
        }

        try {
            const res = await gerarTotp(secret);
            if (!res) {
                if (statusEl) statusEl.textContent = 'Erro ao gerar TOTP.';
                return;
            }
            preencherInput(input, res.codigo);
            if (statusEl) {
                statusEl.textContent = `${rotulo}: ${res.codigo} (${res.restante}s)`;
                statusEl.style.color = '#1b5e20';
            }
        } catch (err) {
            console.error('[PjeOtp] Erro ao gerar TOTP:', err);
            if (statusEl) {
                statusEl.textContent = 'Falha ao calcular TOTP.';
                statusEl.style.color = '#b71c1c';
            }
        }
    }

    function abrirConfiguracao(statusEl) {
        const temPje = Boolean(lerValor(STORAGE_KEYS.pje));
        const temSisb = Boolean(lerValor(STORAGE_KEYS.sisb));
        const escolha = window.prompt(
            `Configurar chave TOTP:\n` +
            `1 - PJe (${temPje ? 'configurado' : 'não configurado'})\n` +
            `2 - SISBAJUD (${temSisb ? 'configurado' : 'não configurado'})\n\n` +
            `Digite 1 ou 2:`,
            '1'
        );
        if (escolha === '1') {
            if (pedirEGravarSeed('pje') && statusEl) {
                statusEl.textContent = 'Chave PJe salva.';
                statusEl.style.color = '#1b5e20';
            }
        } else if (escolha === '2') {
            if (pedirEGravarSeed('sisb') && statusEl) {
                statusEl.textContent = 'Chave SISB salva.';
                statusEl.style.color = '#1b5e20';
            }
        }
    }

    // ── Injeção da barra de botões ───────────────────────────────────────────
    function criarBotao(texto, destaque, corFundo, onClick) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = texto;
        btn.style.cssText = [
            'padding: 6px 12px',
            'border-radius: 4px',
            'font-size: 13px',
            'font-weight: 600',
            'cursor: pointer',
            `background: ${destaque ? corFundo : '#f1f3f5'}`,
            `color: ${destaque ? '#ffffff' : '#212529'}`,
            `border: ${destaque ? `2px solid ${corFundo}` : '1px solid #adb5bd'}`,
            'transition: opacity 0.15s ease',
        ].join(';');
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            onClick();
        });
        return btn;
    }

    function injetarBarraOtp() {
        const contexto = detectarContexto();
        const inputOtp = localizarCampoOtp();
        if (!inputOtp) return;
        if (document.getElementById(CONTAINER_ID)) return;

        const bar = document.createElement('div');
        bar.id = CONTAINER_ID;
        bar.style.cssText = [
            'display: flex',
            'flex-wrap: wrap',
            'align-items: center',
            'gap: 8px',
            'margin: 10px 0',
            'padding: 8px 10px',
            'background: #f8f9fa',
            'border: 1px solid #dee2e6',
            'border-radius: 6px',
            'font-family: system-ui, -apple-system, sans-serif',
        ].join(';');

        const statusEl = document.createElement('span');
        statusEl.style.cssText = 'font-size: 12px; color: #495057; margin-left: 4px;';
        if (contexto === 'sisb') {
            statusEl.textContent = 'Detectado: SISBAJUD';
        } else if (contexto === 'pje') {
            statusEl.textContent = 'Detectado: PJe';
        }

        const btnPje = criarBotao(
            contexto === 'pje' ? '🔐 OTP PJe ★' : '🔐 OTP PJe',
            contexto !== 'sisb',
            '#1565c0',
            () => acionarBotaoOtp('pje', statusEl)
        );
        const btnSisb = criarBotao(
            contexto === 'sisb' ? '🔐 OTP SISB ★' : '🔐 OTP SISB',
            contexto === 'sisb',
            '#2e7d32',
            () => acionarBotaoOtp('sisb', statusEl)
        );

        const btnCfg = document.createElement('button');
        btnCfg.type = 'button';
        btnCfg.textContent = '⚙';
        btnCfg.title = 'Configurar chaves TOTP (PJe / SISBAJUD)';
        btnCfg.style.cssText = [
            'padding: 5px 8px',
            'border-radius: 4px',
            'font-size: 13px',
            'cursor: pointer',
            'background: #ffffff',
            'color: #495057',
            'border: 1px solid #ced4da',
        ].join(';');
        btnCfg.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            abrirConfiguracao(statusEl);
        });

        // Se detectou SISB, coloca SISB primeiro; senão PJe primeiro
        if (contexto === 'sisb') {
            bar.appendChild(btnSisb);
            bar.appendChild(btnPje);
        } else {
            bar.appendChild(btnPje);
            bar.appendChild(btnSisb);
        }
        bar.appendChild(btnCfg);
        bar.appendChild(statusEl);

        const alvoPai = inputOtp.parentElement || document.body;
        alvoPai.insertAdjacentElement('afterend', bar);
        console.log('[PjeOtp] Barra OTP injetada (contexto:', contexto || 'indefinido', ')');
    }

    function init() {
        detectarContexto();
        injetarBarraOtp();

        if (!window.__pjeOtpObserver && document.body) {
            const obs = new MutationObserver(() => {
                if (!document.getElementById(CONTAINER_ID) && localizarCampoOtp()) {
                    injetarBarraOtp();
                }
            });
            obs.observe(document.body, { childList: true, subtree: true });
            window.__pjeOtpObserver = obs;
        }
    }

    window.PjeOtp = {
        init,
        gerarTotp,
        detectarContexto,
    };
})();
