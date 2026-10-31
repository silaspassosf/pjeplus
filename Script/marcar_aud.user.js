// ==UserScript==
// @name         PJe – Marcar Audiência
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Marca audiência na pauta. Suporta processo 100% digital.
// @author       Silas
// @match        https://pje.trt2.jus.br/pjekz/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        window.close
// @run-at       document-idle
// ==/UserScript==

(async function () {
    'use strict';
    if (window.self !== window.top) return;

    // ── Primitivas ──────────────────────────────────────────────────────────────
    const sleep = ms => new Promise(r => setTimeout(r, ms));

    function waitEl(sel, ms = 10000) {
        const found = document.querySelector(sel);
        if (found) return Promise.resolve(found);
        return new Promise(resolve => {
            const obs = new MutationObserver(() => {
                const el = document.querySelector(sel);
                if (el) { obs.disconnect(); clearTimeout(timer); resolve(el); }
            });
            obs.observe(document.body || document.documentElement, { childList: true, subtree: true });
            const timer = setTimeout(() => { obs.disconnect(); resolve(null); }, ms);
        });
    }

    function waitXPath(xpath, ms = 8000) {
        return new Promise(resolve => {
            const hit = () => document.evaluate(
                xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
            ).singleNodeValue;
            const found = hit();
            if (found) return resolve(found);
            const t = Date.now();
            const id = setInterval(() => {
                const el = hit();
                if (el) { clearInterval(id); resolve(el); return; }
                if (Date.now() - t > ms) { clearInterval(id); resolve(null); }
            }, 150);
        });
    }

    function overlay(msg, color = '#2e7d32', duration = 0) {
        document.getElementById('_mau_ov')?.remove();
        const el = document.createElement('div');
        el.id = '_mau_ov';
        el.textContent = msg;
        el.style.cssText =
            `position:fixed;bottom:20px;right:20px;background:${color};color:#fff;` +
            `padding:12px 18px;z-index:9999999;border-radius:6px;font-weight:bold;` +
            `box-shadow:0 3px 8px rgba(0,0,0,.4);font-family:sans-serif;max-width:420px;` +
            `white-space:pre-wrap;font-size:14px;cursor:pointer;`;
        el.onclick = () => el.remove();
        document.body.appendChild(el);
        if (duration > 0) setTimeout(() => el?.remove(), duration);
    }

    function setAngularInput(el, value) {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
        if (setter) setter.call(el, value); else el.value = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function btnByText(container, text) {
        return [...(container?.querySelectorAll('button') || [])].find(b => b.textContent.includes(text)) || null;
    }

    // ── Task (GM cross-tab) ─────────────────────────────────────────────────────
    const TASK_KEY = 'pje_mau_task';
    const getTask  = () => { try { return JSON.parse(GM_getValue(TASK_KEY, 'null')); } catch { return null; } };
    const setTask  = t  => GM_setValue(TASK_KEY, JSON.stringify(t));
    const clearTask = () => GM_setValue(TASK_KEY, null);

    const BC = 'pje_mau_v1';

    // ════════════════════════════════════════════════════════════════════════════
    // FLUXOS
    // ════════════════════════════════════════════════════════════════════════════

    function buildPautaUrl(task) {
        return `https://pje.trt2.jus.br/pjekz/pauta-audiencias?maisPje=true` +
               `&numero=${encodeURIComponent(task.numero)}&rito=${task.rito}&fase=Conhecimento`;
    }

    // ── Desmarcar 100% digital ─────────────────────────────────────────────────
    async function desmarcar100() {
        const step4 = await waitEl('mat-step-header[aria-posinset="4"]', 15000);
        if (!step4) throw new Error('Step Características não encontrado');
        step4.scrollIntoView({ block: 'center' });
        step4.click();
        await sleep(1000);

        const toggle = await waitEl('mat-slide-toggle[formcontrolname="juizoDigital"]', 10000);
        if (!toggle) throw new Error('Toggle Juízo Digital não encontrado');
        if (!toggle.classList.contains('mat-checked')) return; // já desmarcado

        toggle.scrollIntoView({ block: 'center' });
        toggle.querySelector('label.mat-slide-toggle-label').click();
        await sleep(600);

        // Painel 1 — "Tem certeza de que deseja retirar" → Sim
        const p1 = await waitXPath(
            "//mat-expansion-panel//mat-panel-title[contains(normalize-space(.),'Tem certeza de que deseja retirar')]",
            10000
        );
        if (!p1) throw new Error('Painel "Tem certeza" não encontrado');
        const sim = btnByText(p1.closest('mat-expansion-panel'), 'Sim');
        if (!sim) throw new Error('Botão Sim não encontrado');
        sim.click();
        await sleep(600);

        // Painel 2 — "Confirma a inclusão do movimento" → Não
        const p2 = await waitXPath(
            "//mat-expansion-panel//mat-panel-title[contains(normalize-space(.),'Confirma a inclusão do movimento')]",
            10000
        );
        if (!p2) throw new Error('Painel "Confirma inclusão" não encontrado');
        const nao = btnByText(p2.closest('mat-expansion-panel'), 'Não');
        if (!nao) throw new Error('Botão Não não encontrado');
        nao.click();
        await sleep(600);

        await waitXPath(
            "//mat-slide-toggle[@formcontrolname='juizoDigital' and not(contains(@class,'mat-checked'))]",
            10000
        );
        await sleep(800);
    }

    async function clicarSimConfirmacao(ms = 10000) {
        const t0 = Date.now();
        while (Date.now() - t0 < ms) {
            // 1. Procura em dialogs, modais e overlays (mat-dialog-container, pje-modal-juizo-digital, .cdk-overlay-pane, mat-expansion-panel)
            const containers = Array.from(document.querySelectorAll(
                'mat-dialog-container, pje-modal-juizo-digital, .cdk-overlay-pane, mat-expansion-panel'
            ));
            for (const c of containers) {
                const btns = Array.from(c.querySelectorAll('button'));
                const btnSim = btns.find(b => {
                    const txt = (b.textContent || '').trim();
                    return txt === 'Sim' || txt.startsWith('Sim') || /\bSim\b/i.test(txt);
                });
                if (btnSim && btnSim.offsetParent !== null) {
                    console.log('[MarcarAud][Retificar] Clicando em Sim na confirmação:', c.tagName);
                    btnSim.click();
                    const w = btnSim.querySelector('span.mat-button-wrapper');
                    if (w) w.click();
                    return true;
                }
            }

            // 2. Fallback direto por XPath para qualquer botão com span "Sim" em modal/dialog/painel
            const hit = document.evaluate(
                "//mat-dialog-container//button[.//span[normalize-space(.)='Sim']] | " +
                "//pje-modal-juizo-digital//button[.//span[normalize-space(.)='Sim']] | " +
                "//div[contains(@class,'cdk-overlay-pane')]//button[.//span[normalize-space(.)='Sim']] | " +
                "//mat-expansion-panel//button[.//span[normalize-space(.)='Sim']]",
                document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
            ).singleNodeValue;
            if (hit) {
                console.log('[MarcarAud][Retificar] Clicando em Sim via XPath direto');
                hit.click();
                const w2 = hit.querySelector('span.mat-button-wrapper');
                if (w2) w2.click();
                return true;
            }

            await sleep(250);
        }
        return false;
    }

    // ── Remarcar 100% digital ──────────────────────────────────────────────────
    async function remarcar100() {
        const toggle = await waitEl('mat-slide-toggle[formcontrolname="juizoDigital"]', 10000);
        if (!toggle) throw new Error('Toggle Juízo Digital não encontrado');
        if (toggle.classList.contains('mat-checked')) return; // já marcado

        toggle.scrollIntoView({ block: 'center' });
        const label = toggle.querySelector('label.mat-slide-toggle-label') || toggle;
        label.click();
        await sleep(600);

        const clicou = await clicarSimConfirmacao(10000);
        if (!clicou) {
            console.warn('[MarcarAud][Retificar] Confirmação com botão Sim não encontrada em 10s');
        }

        await waitEl('mat-slide-toggle[formcontrolname="juizoDigital"].mat-checked', 10000);
        await sleep(800);
    }

    // ── Marcação na pauta ──────────────────────────────────────────────────────
    async function marcarPauta(task) {
        await waitEl('mat-card.card-pauta', 15000);
        await sleep(500);

        // Linha por rito na Tabela de Horários Vagos
        const linhaXPath = task.rito === 'ATSUM'
            ? '//tr[.//span[contains(normalize-space(.),"Una (rito sumar")]]'
            : "//tr[.//span[normalize-space(.)='Una'] and not(.//span[contains(normalize-space(.),'sumar')])]";

        const linha = await waitXPath(linhaXPath, 10000);
        if (!linha) throw new Error('Linha de pauta não encontrada para rito ' + task.rito);

        const tds = linha.querySelectorAll('td.td-class');
        if (tds.length < 3) throw new Error('Colunas insuficientes na tabela (' + tds.length + ')');
        const dataStr = tds[1].querySelector('span')?.textContent.trim();
        const horaStr = tds[2].querySelector('span')?.textContent.trim();
        if (!dataStr || !horaStr) throw new Error(`Data/hora vazios: data='${dataStr}' hora='${horaStr}'`);

        overlay(`Navegando para ${dataStr} às ${horaStr}…`, '#1565c0');
        await navegarCalendario(dataStr);
        await clicarSlotHora(horaStr);
        await preencherModal(task.numero);
    }

    async function navegarCalendario(dataStr) {
        const [dd, mm, yyyy] = dataStr.split('/').map(Number);
        const alvo  = new Date(yyyy, mm - 1, dd);
        const hoje  = new Date();
        const delta = (alvo.getFullYear() - hoje.getFullYear()) * 12 + (alvo.getMonth() - hoje.getMonth());

        for (let i = 0; i < delta; i++) {
            const btn = await waitEl('#next', 10000);
            if (!btn) throw new Error('Botão próximo mês não encontrado');
            btn.click();
            await sleep(600);
        }

        const MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                       'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
        const mesNome = MESES[alvo.getMonth()];
        if (!await waitXPath(`//h2[contains(normalize-space(.),'${mesNome}, ${alvo.getFullYear()}')]`, 10000))
            throw new Error(`Mês "${mesNome}, ${alvo.getFullYear()}" não confirmado`);

        const diaCell = await waitXPath(
            `//span[contains(@class,'cal-day-cell') and .//label[normalize-space(.)='${alvo.getDate()}']]`,
            10000
        );
        if (!diaCell) throw new Error(`Célula do dia ${alvo.getDate()} não encontrada`);
        diaCell.click();
        await sleep(800);

        const diaFmt = `${String(dd).padStart(2,'0')}/${String(mm).padStart(2,'0')}/${yyyy}`;
        if (!await waitXPath(`//h2[contains(normalize-space(.),'${diaFmt}')]`, 10000))
            throw new Error(`Confirmação do dia ${diaFmt} não encontrada`);
    }

    async function clicarSlotHora(horaStr) {
        const linha = await waitXPath(`//tr[.//span[normalize-space(.)='${horaStr}']]`, 15000);
        if (!linha) throw new Error(`Linha com horário '${horaStr}' não encontrada na pauta diária`);
        const btn = linha.querySelector('button[aria-label*="Designar"]')
                 || linha.querySelector('i.fa-plus-circle')?.closest('button');
        if (!btn) throw new Error('Botão Designar Audiência não encontrado na linha');
        btn.click();
        await sleep(500);
    }

    // ── Preenchimento e Autocomplete do Número do Processo no Modal ────────────
    function tirarFocoBodyDialog(modal) {
        const alvo = modal.querySelector('.container-conteudo') || modal.querySelector('form') || modal;
        if (alvo) alvo.click();
    }

    async function aguardarCarregamento(ms = 8000) {
        const t0 = Date.now();
        while (Date.now() - t0 < ms) {
            const loading = document.querySelector(
                'mat-dialog-container mat-progress-bar, mat-dialog-container mat-spinner, .mat-progress-bar'
            );
            if (!loading) break;
            await sleep(200);
        }
    }

    function encontrarOpcaoProcesso(alvo) {
        const opcoes = Array.from(document.querySelectorAll(
            '.mat-autocomplete-panel mat-option, mat-autocomplete mat-option'
        ));
        for (const opt of opcoes) {
            const digitos = (opt.textContent || '').replace(/\D/g, '');
            if (digitos === alvo) return opt;
        }
        return null;
    }

    async function digitarCaractere(el, ch) {
        el.dispatchEvent(new KeyboardEvent('keydown', { key: ch, code: 'Digit' + ch, bubbles: true, cancelable: true }));
        el.dispatchEvent(new KeyboardEvent('keypress', { key: ch, code: 'Digit' + ch, bubbles: true, cancelable: true }));

        let inserted = false;
        try {
            inserted = document.execCommand && document.execCommand('insertText', false, ch);
        } catch (_) {
            inserted = false;
        }

        if (!inserted) {
            const curVal = el.value || '';
            const newVal = curVal + ch;
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
            if (setter) setter.call(el, newVal); else el.value = newVal;
            el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: ch }));
        }

        el.dispatchEvent(new KeyboardEvent('keyup', { key: ch, code: 'Digit' + ch, bubbles: true, cancelable: true }));
    }

    async function selecionarProcessoPorAutocomplete(modal, alvo) {
        const input = modal.querySelector('input#inputNumeroProcesso');
        if (!input) return false;

        input.focus();
        await sleep(150);

        // Limpa o campo
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
        if (setter) setter.call(input, ''); else input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(150);

        const minDigitos = 7;
        let opcao = null;

        for (let i = 0; i < alvo.length; i++) {
            const ch = alvo[i];
            await digitarCaractere(input, ch);

            if (i + 1 >= minDigitos) {
                // Aguarda reação da busca do PJe (debounce da API é 300ms)
                await sleep(i + 1 === minDigitos ? 500 : 250);
                opcao = encontrarOpcaoProcesso(alvo);
                if (opcao) {
                    console.log(`[MarcarAud][Pauta] Opção do processo apareceu com ${i + 1} dígitos`);
                    break;
                }
            } else {
                await sleep(50);
            }
        }

        if (!opcao) {
            const t0 = Date.now();
            while (Date.now() - t0 < 3000) {
                opcao = encontrarOpcaoProcesso(alvo);
                if (opcao) break;
                await sleep(200);
            }
        }

        if (!opcao) {
            console.warn('[MarcarAud][Pauta] Autocomplete não ofereceu opção para:', alvo);
            return false;
        }

        console.log('[MarcarAud][Pauta] Clicando na opção do autocomplete...');
        opcao.scrollIntoView({ block: 'nearest' });
        opcao.click();
        await sleep(500);

        const valDepois = (input.value || '').replace(/\D/g, '');
        if (valDepois === alvo || valDepois.includes(alvo)) {
            console.log('[MarcarAud][Pauta] Processo selecionado via autocomplete com sucesso:', input.value);
            return true;
        }
        return false;
    }

    async function preencherNumeroFallback(modal, numero, alvo) {
        const input = modal.querySelector('input#inputNumeroProcesso');
        if (!input) return;

        let formatado = numero;
        if (alvo.length === 20 && !numero.includes('-')) {
            formatado = `${alvo.slice(0, 7)}-${alvo.slice(7, 9)}.${alvo.slice(9, 13)}.${alvo.slice(13, 14)}.${alvo.slice(14, 16)}.${alvo.slice(16, 20)}`;
        }

        setAngularInput(input, formatado);
        await sleep(300);

        input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
        input.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
        await sleep(500);

        const opt = encontrarOpcaoProcesso(alvo) || document.querySelector('.mat-autocomplete-panel mat-option');
        if (opt) {
            opt.click();
            await sleep(400);
        } else {
            tirarFocoBodyDialog(modal);
            await sleep(300);
        }
    }

    async function garantirNumeroProcesso(modal, numero) {
        const input = modal.querySelector('input#inputNumeroProcesso');
        if (!input) throw new Error('Campo Número do Processo não encontrado no modal');

        const alvo = String(numero || '').replace(/\D/g, '');
        if (!alvo) throw new Error('Número do processo inválido ou vazio');

        // 1. Verifica se já está pré-preenchido pelo PJe
        let valAtual = (input.value || '').replace(/\D/g, '');
        if (valAtual.includes(alvo)) {
            console.log('[MarcarAud][Pauta] Campo já pré-preenchido pelo PJe:', input.value);
            return true;
        }

        await sleep(600);
        valAtual = (input.value || '').replace(/\D/g, '');
        if (valAtual.includes(alvo)) {
            console.log('[MarcarAud][Pauta] Campo pré-preenchido após espera:', input.value);
            return true;
        }

        console.log('[MarcarAud][Pauta] Digitando processo no autocomplete:', numero);
        const selecionado = await selecionarProcessoPorAutocomplete(modal, alvo);

        if (!selecionado) {
            console.warn('[MarcarAud][Pauta] Seleção por autocomplete falhou -- aplicando fallback');
            await preencherNumeroFallback(modal, numero, alvo);
        }

        return true;
    }

    async function preencherModal(numero) {
        const modal = await waitEl('mat-dialog-container', 15000);
        if (!modal) throw new Error('Modal de audiência não abriu');

        // Preenche o nº do processo via digitação + seleção no autocomplete
        await garantirNumeroProcesso(modal, numero);

        // Aguarda spinners e loadings sumirem
        await aguardarCarregamento(8000);
        await sleep(500);

        const btnOk = await waitXPath(
            "//mat-dialog-container//button[.//span[normalize-space(.)='Confirmar']]", 10000
        );
        if (!btnOk) throw new Error('Botão Confirmar não encontrado no modal');

        // Aguarda o botão Confirmar ser habilitado pelo Angular
        const tBtn = Date.now();
        while (Date.now() - tBtn < 5000) {
            if (!btnOk.disabled && !btnOk.classList.contains('disabled')) break;
            await sleep(200);
        }

        console.log('[MarcarAud][Pauta] Clicando em Confirmar...');
        btnOk.click();
        await sleep(1000);

        // Monitora confirmação ou mensagem "Consulte o processo"
        const t0 = Date.now();
        let confirmado = false;
        while (Date.now() - t0 < 20000) {
            const txtModal = modal.textContent || '';
            if (/Designa.*Confirmad|Audiência designada|Designação confirmada/i.test(txtModal)) {
                confirmado = true;
                console.log('[MarcarAud][Pauta] ✅ Designação confirmada pelo PJe');
                break;
            }
            if (/consulte o processo/i.test(txtModal)) {
                console.warn('[MarcarAud][Pauta] ⚠️ PJe acusou "Consulte o processo" -- aplicando retry...');
                tirarFocoBodyDialog(modal);
                await sleep(2000);
                if (!btnOk.disabled && !btnOk.classList.contains('disabled')) {
                    btnOk.click();
                }
            }
            await sleep(400);
        }

        if (!confirmado) {
            throw new Error('Confirmação de designação não apareceu no modal');
        }

        const fechar = await waitXPath(
            "//mat-dialog-container//button[.//span[normalize-space(.)='Fechar']]", 10000
        ) || modal.querySelector('button[aria-label="Fechar"]');
        if (fechar) {
            fechar.click();
            await sleep(500);
        }
    }

    // ════════════════════════════════════════════════════════════════════════════
    // ROUTER — roda no load inicial E em cada navegação SPA (pushState/popstate)
    // ════════════════════════════════════════════════════════════════════════════

    async function boot() {
        const cur = location.href;

        if (/\/processo\/\d+\/detalhe/.test(cur)) {
            // Remove botão de navegação anterior antes de re-injetar
            document.getElementById('_mau_btn')?.remove();
            await initDetalhe(cur);
        } else if (/\/processo\/\d+\/retificar/.test(cur)) {
            await initRetificar(cur);
        } else if (cur.includes('/pauta-audiencias')) {
            await initPauta(cur);
        }
    }

    // Monitor SPA: intercepta pushState e popstate
    const _origPush = history.pushState.bind(history);
    history.pushState = function (...args) {
        _origPush(...args);
        setTimeout(boot, 200);
    };
    window.addEventListener('popstate', () => setTimeout(boot, 200));

    boot(); // load inicial

    // ── /detalhe ────────────────────────────────────────────────────────────────
    async function initDetalhe(url) {
        const task = getTask();

        // Volta pós-marcação: mostrar confirmação
        if (task?.step === 'confirmar') {
            clearTask();
            await sleep(1500);
            const dd = await waitXPath(
                "//dd[contains(normalize-space(.), ' às ') and contains(normalize-space(.), 'Una')]",
                8000
            );
            overlay(
                `✅ Audiência marcada:\n${dd ? dd.textContent.trim() : '(sem dados na página)'}`,
                '#2e7d32',
                0
            );
            return;
        }

        // Aguardar timeline carregar (mesmo seletor do exec.js)
        await waitEl('li.tl-item-container, .timeline-item', 15000);

        // Botão fixo (id para anti-duplicação no SPA)
        const btn = document.createElement('button');
        btn.id = '_mau_btn';
        btn.textContent = '📅 Marcar Aud';
        btn.style.cssText =
            'position:fixed;bottom:20px;left:20px;z-index:9999990;background:#1565c0;' +
            'color:#fff;border:none;padding:10px 16px;border-radius:6px;cursor:pointer;' +
            'font-weight:bold;font-size:14px;box-shadow:0 2px 6px rgba(0,0,0,.4);';
        document.body.appendChild(btn);

        btn.onclick = async () => {
            btn.disabled = true;
            btn.textContent = '⏳';
            overlay('Iniciando…', '#555');
            try {
                const m = url.match(/\/processo\/(\d+)\/detalhe/);
                const processoId = m?.[1];
                if (!processoId) throw new Error('ID do processo não encontrado na URL');

                const toolbar = document.querySelector('mat-toolbar');
                const is100   = !!toolbar?.querySelector('img[src*="juizo_digital"]');
                const rito    = [...(toolbar?.querySelectorAll('span') || [])].some(s => s.textContent.trim() === 'ATSum')
                                    ? 'ATSUM' : 'ATVARI';
                const cnj     = toolbar?.querySelector('a[aria-label*="Detalhes do Processo"]')
                                         ?.getAttribute('aria-label')
                                         ?.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/)?.[0];
                if (!cnj) throw new Error('Número CNJ não encontrado no cabeçalho');

                const t = { numero: cnj, processoId, rito, is100, step: is100 ? 'retificar' : 'pauta' };
                setTask(t);

                // Listener: espera sinal DONE para recarregar
                const bc = new BroadcastChannel(BC);
                bc.onmessage = async (e) => {
                    if (e.data.type === 'DONE') {
                        bc.close();
                        setTask({ ...t, step: 'confirmar' });
                        location.reload();
                    }
                };

                window.open(
                    is100
                        ? `https://pje.trt2.jus.br/pjekz/processo/${processoId}/retificar`
                        : buildPautaUrl(t),
                    '_blank'
                );
            } catch (err) {
                overlay('❌ ' + err.message, '#c62828');
                btn.disabled = false;
                btn.textContent = '📅 Marcar Aud';
            }
        };
    }

    // ── /retificar ──────────────────────────────────────────────────────────────
    async function initRetificar(url) {
        const task = getTask();
        if (!task || task.step !== 'retificar') return;
        if (!url.includes(`/processo/${task.processoId}/retificar`)) return;

        overlay('Desmarcando 100% digital…', '#555');
        const bc = new BroadcastChannel(BC);

        // Aguarda conclusão da pauta para remarcar
        bc.onmessage = async (e) => {
            if (e.data.type !== 'PAUTA_DONE') return;
            overlay('Remarcando 100% digital…', '#555');
            try {
                await remarcar100();
                bc.postMessage({ type: 'DONE' });
                bc.close();
                await sleep(400);
                window.close();
            } catch (err) {
                overlay('❌ Remarcar: ' + err.message, '#c62828');
            }
        };

        try {
            await desmarcar100();
            overlay('Abrindo pauta…', '#555');
            setTask({ ...task, step: 'pauta' });      // atualiza antes de abrir a aba
            window.open(buildPautaUrl(task), '_blank');
        } catch (err) {
            overlay('❌ Desmarcar: ' + err.message, '#c62828');
        }
    }

    // ── /pauta-audiencias ───────────────────────────────────────────────────────
    async function initPauta() {
        const task = getTask();
        if (!task || task.step !== 'pauta') return;

        overlay('Carregando pauta…', '#555');
        const bc = new BroadcastChannel(BC);

        try {
            await marcarPauta(task);
            overlay('✅ Marcado!', '#2e7d32', 2000);
            bc.postMessage(task.is100 ? { type: 'PAUTA_DONE' } : { type: 'DONE' });
            bc.close();
            await sleep(600);
            window.close();
        } catch (err) {
            overlay('❌ Pauta: ' + err.message, '#c62828');
        }
    }

})();
