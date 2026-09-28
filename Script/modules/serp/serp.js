// serp.js — Módulo PJeTools — SERP Constrições (Solicitar)
// =====================================================================
// Página-alvo:
//   https://serp.registros.org.br/constricoes/solicitar
//
// Injeta o botão flutuante "Preencher" que seleciona e preenche os
// campos do formulário de solicitação de constrição com os valores de
// referência:
//   - Natureza do processo ....... Execução trabalhista (2)
//   - Tipo de constrição ......... Penhora (1)
//   - Data do auto ou termo ...... 01/07/2026
//   - Advogado/solicitante ....... Solicitante (requester)
//   - Forma de pagamento ......... Diferimento (deferral)
//   - Fundamento do diferimento .. Execução trabalhista em favor do
//                                  empregado (4)
//   - Nome/celular/e-mail ........ não tocados (sem valor de referência)
(function () {
    'use strict';

    // ── Gate: só atua na página de solicitação de constrições ──
    if (window.location.hostname !== 'serp.registros.org.br') return;
    if (!window.location.pathname.includes('/constricoes/solicitar')) return;

    const BTN_ID = 'serp-preencher-btn';

    const showToast = window.showToast || function (texto, cor) {
        alert(texto);
    };
    const sleep = window.sleep || function (ms) {
        return new Promise(function (r) { setTimeout(r, ms); });
    };

    // ── Valores de referência (formulário capturado) ──────────────
    const VALORES = {
        natureza: '2',              // Execução trabalhista
        tipoConstricao: '1',        // Penhora
        dataAuto: '2026-07-01',     // 01/07/2026
        solicitante: 'requester',   // rádio "Solicitante"
        pagamento: 'deferral',      // rádio "Diferimento"
        fundamento: '4'             // Execução trabalhista em favor do empregado
    };

    // ── Helpers de evento (Vue/Radix reagem a input/change/click) ──
    function disparar(el, tipos) {
        const opts = { bubbles: true, cancelable: true, view: window };
        tipos.forEach(function (tipo) {
            if (tipo === 'click') {
                el.dispatchEvent(new MouseEvent('click', opts));
            } else {
                el.dispatchEvent(new Event(tipo, opts));
            }
        });
    }

    // Select nativo escondido irmão do botão combobox [data-testid]
    function selecionarSelect(testId, valor, rotulo) {
        const btn = document.querySelector('[data-testid="' + testId + '"]');
        if (!btn) {
            showToast('SERP: campo "' + rotulo + '" não encontrado', '#dc3545');
            return false;
        }
        const select = btn.parentElement
            ? btn.parentElement.querySelector('select')
            : null;
        if (!select) {
            showToast('SERP: select de "' + rotulo + '" não encontrado', '#dc3545');
            return false;
        }
        const opcao = Array.prototype.find.call(
            select.options,
            function (o) { return o.value === String(valor); }
        );
        if (!opcao) {
            showToast('SERP: opção "' + valor + '" ausente em "' + rotulo + '"', '#dc3545');
            return false;
        }
        select.value = valor;
        disparar(select, ['input', 'change']);
        return true;
    }

    // Rádio Radix: botão [role=radio][value=...] — clique dispara o state
    function clicarRadio(valor, rotulo) {
        const radio = document.querySelector('button[role="radio"][value="' + valor + '"]');
        if (!radio) {
            showToast('SERP: rádio "' + rotulo + '" não encontrado', '#dc3545');
            return false;
        }
        if (radio.getAttribute('aria-checked') === 'true') return true;
        disparar(radio, ['click']);
        return true;
    }

    // Data do auto/termo: Radix DateField com input oculto + segmentos visíveis
    function preencherData(iso) {
        const trigger = document.querySelector('button[data-radix-vue-date-field-segment="trigger"]');
        if (!trigger) {
            showToast('SERP: campo de data não encontrado', '#dc3545');
            return false;
        }
        const input = trigger.querySelector('input[aria-hidden="true"]');
        if (!input) {
            showToast('SERP: input de data não encontrado', '#dc3545');
            return false;
        }
        input.value = iso;
        disparar(input, ['input', 'change', 'blur']);
        // Segmentos visíveis (spans dd / mm / yyyy) — espelho visual imediato
        const partes = iso.split('-'); // [aaaa, mm, dd]
        const spans = trigger.querySelectorAll('div.tw-mfe-flex-tw-mfe-items-center > span');
        if (spans.length >= 5 && partes.length === 3) {
            spans[0].textContent = partes[2]; // dia
            spans[2].textContent = partes[1]; // mês
            spans[4].textContent = partes[0]; // ano
        }
        return true;
    }

    // ── Preenchimento completo ────────────────────────────────────
    async function preencher() {
        try {
            let ok = true;

            ok = selecionarSelect('order-details-process-type-input', VALORES.natureza, 'Natureza do processo') && ok;
            await sleep(80);
            ok = selecionarSelect('order-details-constriction-type-input', VALORES.tipoConstricao, 'Tipo de constrição') && ok;
            await sleep(80);
            ok = preencherData(VALORES.dataAuto) && ok;
            await sleep(80);
            ok = clicarRadio(VALORES.solicitante, 'Solicitante') && ok;
            await sleep(80);
            ok = clicarRadio(VALORES.pagamento, 'Diferimento') && ok;
            await sleep(80);
            ok = selecionarSelect('order-details-payment-type-input', VALORES.fundamento, 'Fundamento do diferimento') && ok;

            if (ok) {
                showToast('SERP: formulário preenchido — confira a data e clique em "Avançar"', '#28a745', 5000);
            } else {
                showToast('SERP: preenchimento parcial — verifique os campos', '#ff9800', 5000);
            }
        } catch (e) {
            showToast('SERP: erro ao preencher — ' + e.message, '#dc3545', 5000);
        }
    }

    // ── Injeção do botão ──────────────────────────────────────────
    function injetarBotao() {
        if (document.getElementById(BTN_ID)) return;

        const btn = document.createElement('button');
        btn.id = BTN_ID;
        btn.type = 'button';
        btn.textContent = 'Preencher';
        btn.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:2147483647;'
            + 'background:#DF763A;color:#fff;border:none;border-radius:500px;'
            + 'padding:12px 28px;font:bold 14px sans-serif;cursor:pointer;'
            + 'box-shadow:0 4px 12px rgba(0,0,0,.35);';
        btn.addEventListener('click', function () {
            preencher();
        });
        document.body.appendChild(btn);
    }

    // ── Bootstrap: espera o form e mantém o botão presente ────────
    async function iniciar() {
        const form = await (window.waitElementVisible
            ? window.waitElementVisible('form', 15000)
            : new Promise(function (res) {
                const start = Date.now();
                const id = setInterval(function () {
                    const f = document.querySelector('form');
                    if (f) { clearInterval(id); res(f); }
                    else if (Date.now() - start > 15000) { clearInterval(id); res(null); }
                }, 100);
            }));
        if (!form) {
            showToast('SERP: formulário não carregou', '#dc3545', 5000);
            return;
        }
        injetarBotao();

        // Reinsere o botão se a SPA remover o nó (registro em CleanupRegistry)
        if (window.CleanupRegistry) {
            const obs = new MutationObserver(function () {
                if (!document.getElementById(BTN_ID)) injetarBotao();
            });
            obs.observe(document.body, { childList: true, subtree: true });
            if (window.PJeState && window.PJeState.registry) {
                window.PJeState.registry.observer(obs);
            }
        }
    }

    iniciar();
})();