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

    function captureActivation() {
        document.addEventListener('click', event => {
            const button = event.target instanceof Element
                ? event.target.closest('#botao-do-processo-pjeCalc')
                : null;
            if (!button) return;

            const number = document.querySelector('pje-cabecalho-processo')?.textContent?.match(PROCESS_NUMBER_RE)?.[0]
                || document.title.match(PROCESS_NUMBER_RE)?.[0];
            const processId = location.pathname.match(/\/processo\/(\d+)\/detalhe/)?.[1];
            if (!number || !processId) {
                notify('Atualização rápida: não foi possível identificar o processo nesta tela.');
                return;
            }

            const date = new Intl.DateTimeFormat('pt-BR').format(new Date());
            const state = {
                processId,
                processNumber: number,
                liquidationDate: date,
                phase: 'search-process',
                createdAt: Date.now()
            };
            try {
                Promise.resolve(GM_setValue(STATE_KEY, state)).catch(error => {
                    console.error('[Atualização Rápida] Falha ao salvar o processo:', error);
                });
            } catch (error) {
                console.error('[Atualização Rápida] Falha ao salvar o processo:', error);
            }
        }, true);
    }

    async function readState() {
        const current = await GM_getValue(STATE_KEY, null);
        if (current?.processId && Date.now() - current.createdAt < 10 * 60 * 1000) return current;

        return new Promise(resolve => {
            let listenerId;
            const timer = window.setTimeout(() => {
                if (listenerId !== undefined) GM_removeValueChangeListener(listenerId);
                resolve(null);
            }, 12000);
            listenerId = GM_addValueChangeListener(STATE_KEY, (_key, _oldValue, newValue) => {
                if (!newValue?.processId || Date.now() - newValue.createdAt >= 10 * 60 * 1000) return;
                window.clearTimeout(timer);
                GM_removeValueChangeListener(listenerId);
                resolve(newValue);
            });
        });
    }

    async function saveState(state, phase) {
        state.phase = phase;
        await GM_setValue(STATE_KEY, state);
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
        await GM_deleteValue(STATE_KEY);
        notify('Atualização rápida concluída para ' + state.processNumber + '.', '#137333');
        window.close();
    }

    async function run() {
        let state = await readState();
        if (!state) return;
        if (Date.now() - state.createdAt >= 10 * 60 * 1000) {
            await GM_deleteValue(STATE_KEY);
            return;
        }

        try {
            const title = await waitFor(() => pageTitle()
                || ((state.phase === 'sending' || state.phase === 'finish')
                    && (document.querySelector('input[id="popup_ok"]') || document.querySelector('h2'))
                    ? 'postback' : null), 30000);
            if (!title) throw new Error('A tela do PJeCalc não carregou.');

            if (state.phase === 'liquidating') {
                const message = await waitFor(() => {
                    const element = document.querySelector('div[id="divMensagem"]');
                    return element?.textContent?.trim() ? element : null;
                }, 30000);
                if (!message?.textContent.includes('Operação realizada com sucesso.')) {
                    throw new Error('O PJeCalc não confirmou sucesso após a retomada da liquidação.');
                }
                await saveState(state, 'liquidated');
                state = await GM_getValue(STATE_KEY, state);
            }

            if (state.phase === 'sending') {
                const outcome = await waitFor(() => document.querySelector('input[id="popup_ok"]')
                    || [...document.querySelectorAll('h2')].find(element => element.textContent.includes('Sucesso!')),
                30000);
                if (!outcome) throw new Error('O PJe não confirmou o envio após a retomada.');
                if (outcome.matches('input[id="popup_ok"]')) click(outcome);
                await saveState(state, 'finish');
                state = await GM_getValue(STATE_KEY, state);
            }

            if (state.phase === 'finish') {
                await complete(state);
                return;
            }

            if (title.includes('Cálculo > Buscar')) {
                if (state.phase === 'search-process') await searchProcess(state);
                state = await GM_getValue(STATE_KEY, state);
                if (state.phase === 'find-calculation') await searchLatestCalculation(state);
                state = await GM_getValue(STATE_KEY, state);
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
                state = await GM_getValue(STATE_KEY, state);
                if (state.phase === 'liquidated') {
                    await sendToPje(state);
                    return run();
                }
                return;
            }

            if (title.includes('Enviar para o PJe')) {
                if (state.phase === 'consolidate' || state.phase === 'consolidating' || state.phase === 'send') {
                    await consolidateAndSend(state);
                    state = await GM_getValue(STATE_KEY, state);
                    if (state.phase === 'finish') await complete(state);
                    return;
                }
            }
        } catch (error) {
            console.error('[Atualização Rápida]', error);
            await GM_deleteValue(STATE_KEY);
            notify('Atualização rápida interrompida: ' + error.message);
        }
    }

    if (isCalcPage) void run();
    else if (location.pathname.includes('/detalhe')) captureActivation();
})();