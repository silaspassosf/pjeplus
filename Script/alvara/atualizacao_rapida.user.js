// ==UserScript==
// @name         Atualização Rápida PJeCalc
// @namespace    pjeplus
// @version      1.0.0
// @description  Automatiza a atualização rápida a partir do atalho PJe Calc do AVJT
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe*
// @match        https://pje.trt2.jus.br/pjecalc/*
// @run-at       document-idle
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_deleteValue
// @grant        GM_addValueChangeListener
// @grant        GM_removeValueChangeListener
// @grant        window.close
// ==/UserScript==

(function () {
    'use strict';

    const STATE_KEY = 'pjeplus_atualizacao_rapida';
    const PROCESS_NUMBER_RE = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;
    const isCalcPage = location.pathname.startsWith('/pjecalc/');

    // Storage compatível com a extensão +pje (browser.storage.local).
    // GM_* é storage separado do Tampermonkey — não compartilha com a extensão.
    const storage = (typeof browser !== 'undefined' && browser.storage && browser.storage.local)
        ? browser.storage.local
        : (typeof GM_setValue !== 'undefined' ? { async: true } : null);

    async function storageSet(key, value) {
        if (!storage) throw new Error('Storage indisponível.');
        if (storage.set && typeof storage.set === 'function' && !storage.async) {
            return new Promise((resolve, reject) => {
                storage.set({ [key]: value }, () => {
                    if (browser.runtime && browser.runtime.lastError) reject(browser.runtime.lastError);
                    else resolve();
                });
            });
        }
        return new Promise((resolve, reject) => {
            GM_setValue(key, value, () => {
                if (GM_install?.lastError) reject(GM_install.lastError);
                else resolve();
            });
        });
    }

    async function storageGet(key, defaultValue = null) {
        if (!storage) return defaultValue;
        if (storage.get && typeof storage.get === 'function' && !storage.async) {
            return new Promise((resolve) => {
                storage.get(key, (result) => {
                    resolve(result?.[key] ?? defaultValue);
                });
            });
        }
        return new Promise((resolve) => {
            GM_getValue(key, defaultValue, (value) => resolve(value));
        });
    }

    async function storageDelete(key) {
        if (!storage) return;
        if (storage.remove && typeof storage.remove === 'function' && !storage.async) {
            return new Promise((resolve) => {
                storage.remove(key, () => resolve());
            });
        }
        return new Promise((resolve) => {
            GM_deleteValue(key, () => resolve());
        });
    }

    function storageAddListener(callback) {
        if (storage?.onChanged && typeof storage.onChanged.addListener === 'function') {
            return storage.onChanged.addListener((changes, area) => {
                if (area !== 'local') return;
                if (changes[STATE_KEY]) callback(changes[STATE_KEY].newValue);
            });
        }
        return GM_addValueChangeListener(STATE_KEY, (_key, _oldValue, newValue) => callback(newValue));
    }

    function storageRemoveListener(listenerId) {
        if (storage?.onChanged && typeof storage.onChanged.removeListener === 'function') {
            storage.onChanged.removeListener(listenerId);
        } else if (typeof GM_removeValueChangeListener === 'function') {
            GM_removeValueChangeListener(listenerId);
        }
    }

    function notify(message, color = '#b3261e') {
        document.getElementById('pjeplus-atualizacao-rapida-toast')?.remove();
        const toast = document.createElement('div');
        toast.id = 'pjeplus-atualizacao-rapida-toast';
        toast.textContent = message;
        toast.style.cssText = 'position:fixed;top:16px;right:16px;z-index:2147483647;max-width:420px;padding:12px 16px;background:' + color + ';color:#fff;font:14px sans-serif;box-shadow:0 2px 8px #0006;';
        document.body.appendChild(toast);
        window.setTimeout(() => toast.remove(), 8000);
    }

    function waitFor(test, timeout = 20000) {
        return new Promise(resolve => {
            let observer;
            const finish = value => {
                observer?.disconnect();
                window.clearTimeout(timer);
                resolve(value || null);
            };
            const check = () => {
                try {
                    const value = test();
                    if (value) finish(value);
                } catch (error) {
                    finish(null);
                }
            };
            const timer = window.setTimeout(() => finish(null), timeout);
            observer = new MutationObserver(check);
            observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, characterData: true });
            check();
        });
    }

    function setValue(element, value) {
        if (!element) throw new Error('Campo necessário não encontrado.');
        const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, value);
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function click(element) {
        if (!element) throw new Error('Controle necessário não encontrado.');
        element.click();
    }

    function injectButton() {
        if (document.getElementById('botao-atualizacao-rapida')) return;
        const btn = document.createElement('button');
        btn.id = 'botao-atualizacao-rapida';
        btn.textContent = '⚡ Atualização Rápida';
        btn.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:999999;'
            + 'padding:10px 18px;background:#b3261e;color:#fff;border:none;'
            + 'border-radius:6px;font-size:14px;font-weight:bold;cursor:pointer;'
            + 'box-shadow:0 2px 8px #0006;transition:background .2s;';
        btn.addEventListener('mouseenter', () => btn.style.background = '#d4351f');
        btn.addEventListener('mouseleave', () => btn.style.background = '#b3261e');
        document.body.appendChild(btn);
    }

    async function iniciarAtualizacaoRapida() {
        console.log('[Atualização Rápida] Iniciando...');
        injectButton();

        // Pega o ID do processo da URL
        const matchId = location.pathname.match(/\/processo\/(\d+)\/detalhe/);
        if (!matchId) {
            notify('Não foi possível identificar o processo na URL.');
            return;
        }
        const processId = matchId[1];

        // Puxa o número CNJ via API
        let processNumber = null;
        try {
            const resp = await fetch(location.origin + `/pje-comum-api/api/processos/id/${processId}`, {
                credentials: 'include',
                headers: { Accept: 'application/json' }
            });
            if (resp.ok) {
                const data = await resp.json();
                processNumber = data.numeroProcesso || data.processo?.numeroProcesso;
            }
        } catch (e) {
            console.warn('[Atualização Rápida] Falha ao buscar número via API, tentando DOM:', e);
        }

        // Fallback: tenta ler do cabeçalho ou título
        if (!processNumber) {
            processNumber = document.querySelector('pje-cabecalho-processo')?.textContent?.match(PROCESS_NUMBER_RE)?.[0]
                || document.title.match(PROCESS_NUMBER_RE)?.[0];
        }

        if (!processNumber) {
            notify('Não foi possível identificar o número do processo.');
            return;
        }

        console.log('[Atualização Rápida] Processo:', processNumber, '(id:', processId + ')');

        const date = new Intl.DateTimeFormat('pt-BR').format(new Date());
        const state = {
            processId,
            processNumber,
            liquidationDate: date,
            phase: 'search-process',
            createdAt: Date.now()
        };

        try {
            await storageSet(STATE_KEY, state);
            console.log('[Atualização Rápida] Estado salvo, abrindo PJeCalc...');
            await abrirAba(location.origin + '/pjecalc/pages/principal.jsf');
            notify('Abrindo PJeCalc para atualização de ' + processNumber + '...');
        } catch (error) {
            console.error('[Atualização Rápida] Erro ao iniciar:', error);
            notify('Falha ao iniciar atualização: ' + error.message);
        }
    }

    function captureActivation() {
        injectButton();
        document.getElementById('botao-atualizacao-rapida').addEventListener('click', () => {
            iniciarAtualizacaoRapida();
        }, true);
    }

    async function readState() {
        const current = await storageGet(STATE_KEY, null);
        if (current?.processId && Date.now() - current.createdAt < 10 * 60 * 1000) return current;

        return new Promise(resolve => {
            let listenerId;
            const timer = window.setTimeout(() => {
                if (listenerId !== undefined) storageRemoveListener(listenerId);
                resolve(null);
            }, 12000);
            listenerId = storageAddListener((newValue) => {
                if (!newValue?.processId || Date.now() - newValue.createdAt >= 10 * 60 * 1000) return;
                window.clearTimeout(timer);
                storageRemoveListener(listenerId);
                resolve(newValue);
            });
        });
    }

    async function saveState(state, phase) {
        state.phase = phase;
        await storageSet(STATE_KEY, state);
    }

    function splitProcessNumber(number) {
        const parts = number.match(/^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$/);
        if (!parts) throw new Error('Número do processo fora do padrão CNJ.');
        return {
            numero: parts[1],
            digito: parts[2],
            ano: parts[3],
            justica: parts[4],
            regiao: parts[5],
            vara: parts[6]
        };
    }

    function xsrfToken() {
        const cookie = document.cookie.split(';').map(value => value.trim())
            .find(value => value.toLowerCase().startsWith('xsrf-token='));
        return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : '';
    }

    async function latestCalculationNumber(state) {
        const query = new URLSearchParams({
            idProcesso: state.processId,
            pagina: '1',
            tamanhoPagina: '100',
            ordenacaoCrescente: 'false',
            mostrarCalculosHomologados: 'true',
            incluirCalculosHomologados: 'true'
        });
        const token = xsrfToken();
        const response = await fetch(location.origin + '/pje-comum-api/api/calculos/processo?' + query, {
            credentials: 'include',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                'X-Grau-Instancia': '1',
                ...(token ? { 'X-XSRF-TOKEN': token } : {})
            }
        });
        if (!response.ok) throw new Error('Consulta de cálculos falhou (HTTP ' + response.status + ').');

        const data = await response.json();
        const calculations = Array.isArray(data.resultado) ? data.resultado : [];
        if (!calculations.length) throw new Error('A API não encontrou cálculos para este processo.');

        calculations.sort((left, right) => {
            const leftDate = new Date(left.dataHoraImportacao || left.dataLiquidacao || 0).getTime();
            const rightDate = new Date(right.dataHoraImportacao || right.dataLiquidacao || 0).getTime();
            return rightDate - leftDate;
        });
        const latest = calculations[0];
        const rawNumber = latest.numeroCalculo ?? latest.calculo?.numeroCalculo ?? latest.calculo ?? latest.idCalculo;
        const calculationNumber = typeof rawNumber === 'object' ? rawNumber?.numero : rawNumber;
        if (calculationNumber === undefined || calculationNumber === null || String(calculationNumber).trim() === '') {
            throw new Error('A API retornou cálculos, mas não expôs um número de cálculo seguro para selecionar.');
        }
        return String(calculationNumber).trim();
    }

    async function searchProcess(state) {
        const parts = splitProcessNumber(state.processNumber);
        const fields = [
            ['numeroProcessoBusca', parts.numero],
            ['digitoProcessoBusca', parts.digito],
            ['anoProcessoBusca', parts.ano],
            ['justicaBusca', parts.justica],
            ['regiaoBusca', parts.regiao],
            ['varaProcessoBusca', parts.vara]
        ];
        for (const [name, value] of fields) {
            const input = await waitFor(() => document.querySelector('input[id*="' + name + '"]'));
            if (!input) throw new Error('Campo de busca do processo não carregou: ' + name + '.');
            setValue(input, value);
        }

        const sector = document.querySelector('input[id*="formulario:setor"]');
        if (sector?.hasAttribute('checked')) click(sector);
        await saveState(state, 'find-calculation');
        click(await waitFor(() => document.querySelector('input[id*="formulario:buscar"]')));
        const found = await waitFor(() => document.querySelector('a.linkSelecionar[title="Abrir"]')
            || document.querySelector('span.box-msg-livre'), 30000);
        if (!found) throw new Error('A busca do PJeCalc não retornou resultados em 30 segundos.');
        if (found.matches('span.box-msg-livre') && found.textContent.includes('Não existem resultados')) {
            throw new Error('Este processo não possui cálculo registrado no PJeCalc.');
        }
    }

    async function searchLatestCalculation(state) {
        const number = await latestCalculationNumber(state);
        const input = await waitFor(() => document.querySelector('input[id*="numeroCalculoBusca"]'));
        if (!input) throw new Error('Campo para selecionar o cálculo não encontrado.');
        setValue(input, number);
        await saveState(state, 'open-calculation');
        click(await waitFor(() => document.querySelector('input[id*="formulario:buscar"]')));
        const result = await waitFor(() => document.querySelector('a.linkSelecionar[title="Abrir"]')
            || document.querySelector('span.box-msg-livre'), 30000);
        if (!result || result.matches('span.box-msg-livre')) {
            throw new Error('O PJeCalc não localizou o cálculo mais recente retornado pela API.');
        }
    }

    async function openLatestCalculation(state) {
        const openLink = await waitFor(() => document.querySelector('a.linkSelecionar[title="Abrir"]'));
        if (!openLink) throw new Error('Link para abrir o cálculo não encontrado.');
        await saveState(state, 'liquidation-menu');
        click(openLink);
        if (!await waitFor(() => pageTitle().includes('Cálculo > Dados do Cálculo'), 30000)) {
            throw new Error('A tela dos dados do cálculo não abriu.');
        }
    }

    function pageTitle() {
        return document.querySelector('div[id="barraTitulo"]')?.textContent?.trim() || '';
    }

    async function clickLiquidationMenu(state) {
        const menu = await waitFor(() => [...document.querySelectorAll('li a')]
            .find(element => element.textContent.includes('Liquidar Atualização')));
        if (!menu) throw new Error('A opção “Liquidar Atualização” não apareceu.');
        await saveState(state, 'update-form');
        click(menu);
        if (!await waitFor(() => pageTitle().includes('Atualização > Liquidar Atualização'), 30000)) {
            throw new Error('A tela de liquidação da atualização não abriu.');
        }
    }

    function validateCurrentProcess(state) {
        const text = document.querySelector('span[id="formulario:panelDadosCalculo"]')?.textContent || '';
        const processNumber = text.match(PROCESS_NUMBER_RE)?.[0];
        if (processNumber !== state.processNumber) {
            throw new Error('O cálculo aberto não pertence ao processo iniciado. A liquidação foi cancelada.');
        }
    }

    async function liquidate(state) {
        validateCurrentProcess(state);
        const comment = await waitFor(() => document.querySelector('textarea[id="formulario:comentarios"]'));
        if (!comment) throw new Error('Campo de observação não carregou.');
        const marker = 'MAISPJE: ATUALIZAÇÃO RÁPIDA';
        if (!comment.value.includes(marker)) setValue(comment, comment.value + '\n' + marker);

        const dateInput = await waitFor(() => document.querySelector('input[id="formulario:dataDeLiquidacaoInputDate"]'));
        if (!dateInput) throw new Error('Campo de data de liquidação não carregou.');
        setValue(dateInput, state.liquidationDate);

        await saveState(state, 'liquidating');
        click(await waitFor(() => document.querySelector('input[id="formulario:liquidar"]')));
        const message = await waitFor(() => {
            const element = document.querySelector('div[id="divMensagem"]');
            return element?.textContent?.trim() ? element : null;
        }, 30000);
        if (!message) throw new Error('O PJeCalc não confirmou o resultado da liquidação em 30 segundos.');
        if (!message.textContent.includes('Operação realizada com sucesso.')) {
            throw new Error(message.textContent.includes('Erro.')
                ? 'O PJeCalc informou erro na liquidação.'
                : 'O PJeCalc não confirmou sucesso na liquidação.');
        }
        await saveState(state, 'liquidated');
    }

    async function sendToPje(state) {
        const sendLink = await waitFor(() => document.querySelector('li[id="li_operacoes_validar_atualizacao"] a'));
        if (!sendLink) throw new Error('A opção “Enviar para o PJe” não apareceu após liquidar.');
        await saveState(state, 'consolidate');
        click(sendLink);
        if (!await waitFor(() => pageTitle().includes('Enviar para o PJe'), 30000)) {
            throw new Error('A tela “Enviar para o PJe” não abriu.');
        }
    }

    async function consolidateAndSend(state) {
        if (state.phase === 'consolidate') {
            const consolidate = await waitFor(() => document.querySelector('input[value="Consolidar Dados"]'), 5000);
            if (consolidate) {
                await saveState(state, 'consolidating');
                click(consolidate);
            } else {
                state.phase = 'consolidating';
            }
        }

        if (state.phase === 'consolidating') {
            const ready = await waitFor(() => [...document.querySelectorAll('span.rich-messages-label')]
                .find(element => element.textContent.includes('Os dados estão prontos para serem enviados para o PJe')),
            30000);
            if (!ready) throw new Error('O PJeCalc não concluiu a consolidação em 30 segundos.');
            await saveState(state, 'send');
        }

        const send = await waitFor(() => document.querySelector('input[value="Enviar para o PJe"]'));
        if (!send) throw new Error('Botão “Enviar para o PJe” não encontrado.');
        await saveState(state, 'sending');
        click(send);
        const outcome = await waitFor(() => document.querySelector('input[id="popup_ok"]')
            || [...document.querySelectorAll('h2')].find(element => element.textContent.includes('Sucesso!')), 30000);
        if (!outcome) throw new Error('O PJe não confirmou o envio em 30 segundos.');
        if (outcome.matches('input[id="popup_ok"]')) click(outcome);
        await saveState(state, 'finish');
    }

    async function complete(state) {
        const success = await waitFor(() => [...document.querySelectorAll('h2')]
            .find(element => element.textContent.includes('Sucesso!')), 30000);
        if (!success) throw new Error('O envio ao PJe não confirmou sucesso.');
        await storageDelete(STATE_KEY);
        notify('Atualização rápida concluída para ' + state.processNumber + '.', '#137333');
        window.close();
    }

    async function run() {
        console.log('[Atualização Rápida] Iniciando run()...');
        console.log('[Atualização Rápida] location:', location.href);
        console.log('[Atualização Rápida] readyState:', document.readyState);
        let state = await readState();
        if (!state) {
            console.log('[Atualização Rápida] Nenhum estado encontrado — nada a fazer.');
            return;
        }
        console.log('[Atualização Rápida] Estado lido:', JSON.stringify(state));
        if (Date.now() - state.createdAt >= 10 * 60 * 1000) {
            console.log('[Atualização Rápida] Estado expirado (>10 min) — limpando.');
            await storageDelete(STATE_KEY);
            return;
        }

        try {
            const title = await waitFor(() => pageTitle()
                || ((state.phase === 'sending' || state.phase === 'finish')
                    && (document.querySelector('input[id="popup_ok"]') || document.querySelector('h2'))
                    ? 'postback' : null)
                || (document.querySelector('input[id*="numeroProcessoBusca"]')
                    && document.querySelector('input[id*="formulario:buscar"]')
                    ? 'principal' : null), 30000);
            if (!title) throw new Error('A tela do PJeCalc não carregou.');
            console.log('[Atualização Rápida] Tela detectada:', title);

            if (state.phase === 'liquidating') {
                const message = await waitFor(() => {
                    const element = document.querySelector('div[id="divMensagem"]');
                    return element?.textContent?.trim() ? element : null;
                }, 30000);
                if (!message?.textContent.includes('Operação realizada com sucesso.')) {
                    throw new Error('O PJeCalc não confirmou sucesso após a retomada da liquidação.');
                }
                await saveState(state, 'liquidated');
                state = await storageGet(STATE_KEY, state);
            }

            if (state.phase === 'sending') {
                const outcome = await waitFor(() => document.querySelector('input[id="popup_ok"]')
                    || [...document.querySelectorAll('h2')].find(element => element.textContent.includes('Sucesso!')),
                30000);
                if (!outcome) throw new Error('O PJe não confirmou o envio após a retomada.');
                if (outcome.matches('input[id="popup_ok"]')) click(outcome);
                await saveState(state, 'finish');
                state = await storageGet(STATE_KEY, state);
            }

            if (state.phase === 'finish') {
                await complete(state);
                return;
            }

            if (title.includes('Cálculo > Buscar') || title === 'principal') {
                if (state.phase === 'search-process') await searchProcess(state);
                state = await storageGet(STATE_KEY, state);
                if (state.phase === 'find-calculation') await searchLatestCalculation(state);
                state = await storageGet(STATE_KEY, state);
                if (state.phase === 'open-calculation') {
                    await openLatestCalculation(state);
                    return run();
                }
                return;
            }

            if (title.includes('Cálculo > Dados do Cálculo') && state.phase === 'liquidation-menu') {
                await clickLiquidationMenu(state);
                return run();
            }

            if (title.includes('Atualização > Liquidar Atualização')) {
                if (state.phase === 'update-form') await liquidate(state);
                state = await storageGet(STATE_KEY, state);
                if (state.phase === 'liquidated') {
                    await sendToPje(state);
                    return run();
                }
                return;
            }

            if (title.includes('Enviar para o PJe')) {
                if (state.phase === 'consolidate' || state.phase === 'consolidating' || state.phase === 'send') {
                    await consolidateAndSend(state);
                    state = await storageGet(STATE_KEY, state);
                    if (state.phase === 'finish') await complete(state);
                    return;
                }
            }
        } catch (error) {
            console.error('[Atualização Rápida]', error);
            await storageDelete(STATE_KEY);
            notify('Atualização rápida interrompida: ' + error.message);
        }
    }

    if (isCalcPage) void run();
    else if (location.pathname.includes('/detalhe')) captureActivation();
})();