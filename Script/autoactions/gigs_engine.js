// ==PJeTools Module: autoactions/gigs_engine.js==
// Motor autônomo para automação do GIGS (inclusão e conclusão de atividades, chips e observações)
// Desacoplado de background scripts e APIs WebExtension específicas.

(function () {
    'use strict';

    window.PjeAutoActions = window.PjeAutoActions || {};

    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

    function log(msg, ...args) {
        console.log(`[PjeAutoActions][GIGS] ${msg}`, ...args);
    }

    function warn(msg, ...args) {
        console.warn(`[PjeAutoActions][GIGS] ${msg}`, ...args);
    }

    async function waitElem(selector, timeout = 7000, parent = document) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            const el = parent.querySelector(selector);
            if (el) return el;
            await sleep(100);
        }
        return null;
    }

    function setNativeValue(element, value) {
        const valueSetter = Object.getOwnPropertyDescriptor(
            element instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype,
            'value'
        )?.set;
        if (valueSetter) {
            valueSetter.call(element, value);
        } else {
            element.value = value;
        }
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.dispatchEvent(new Event('blur', { bubbles: true }));
    }

    async function garantirGigsAberto(timeout = 8000) {
        log('Verificando se o painel GIGS está visível...');
        let ficha = document.querySelector('pje-gigs-ficha-processo');
        if (ficha && ficha.offsetParent !== null) {
            return true;
        }

        const btnAbrir = document.querySelector('button[aria-label="Mostrar o GIGS"], button[mattooltip*="GIGS"], button[aria-label*="GIGS"]');
        if (btnAbrir) {
            log('Clicando para abrir painel GIGS...');
            btnAbrir.click();
            ficha = await waitElem('pje-gigs-ficha-processo', timeout);
            if (ficha) {
                await sleep(500);
                return true;
            }
        }

        // Se estiver em rota isolada de GIGS, ficha já deve existir
        return document.querySelector('pje-gigs-ficha-processo') !== null;
    }

    async function selecionarOpcaoMatAutocomplete(inputElem, valorAlvo, timeout = 5000) {
        if (!inputElem || !valorAlvo) return false;
        inputElem.focus();
        inputElem.click();
        await sleep(150);

        setNativeValue(inputElem, valorAlvo);
        inputElem.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
        await sleep(300);

        // Aguarda opções renderizarem no overlay global do CDK
        const start = Date.now();
        while (Date.now() - start < timeout) {
            const options = Array.from(document.querySelectorAll('mat-option[role="option"], .mat-option'));
            if (options.length > 0) {
                const target = options.find(opt => {
                    const txt = (opt.textContent || '').trim().toLowerCase();
                    return txt.includes(valorAlvo.toLowerCase());
                }) || options[0];

                if (target) {
                    target.click();
                    await sleep(200);
                    return true;
                }
            }
            await sleep(150);
        }
        return false;
    }

    /**
     * Cria uma nova atividade no GIGS.
     * @param {Object} params
     * @param {string} params.tipoAtividade Ex: 'Cumprimento de Alvará', 'Minutar', etc.
     * @param {string} [params.responsavel] Nome ou papel do responsável
     * @param {string|number} [params.prazo] Dias ou data limite
     * @param {string} [params.observacao] Texto da observação
     */
    async function criarAtividade(params = {}) {
        const { tipoAtividade, responsavel, prazo, observacao } = params;
        log(`Criando atividade: tipo="${tipoAtividade}", prazo="${prazo}", resp="${responsavel}"`);

        const aberto = await garantirGigsAberto();
        if (!aberto) {
            throw new Error('Não foi possível abrir ou localizar o painel GIGS.');
        }

        // Clica no botão "Nova atividade"
        const btnNova = await waitElem('pje-gigs-lista-atividades button, button[aria-label="Nova atividade"], button[mattooltip*="Nova atividade"]', 5000);
        if (!btnNova) {
            throw new Error('Botão "Nova atividade" não encontrado no GIGS.');
        }
        btnNova.click();
        log('Botão Nova Atividade clicado. Aguardando formulário...');

        // Aguarda formulário de cadastro de atividades
        const formAtividade = await waitElem('pje-gigs-cadastro-atividades, form[name="formAtividade"]', 6000);
        if (!formAtividade) {
            throw new Error('Formulário de cadastro de atividade GIGS não apareceu.');
        }

        // Aguarda eventuais barras de progresso do Angular Material terminarem
        await sleep(400);

        // 1. Tipo de Atividade
        if (tipoAtividade) {
            const inputTipo = await waitElem('input[formcontrolname="tipoAtividade"], input[aria-label*="Tipo de Atividade"]', 3000, formAtividade);
            if (inputTipo) {
                log(`Preenchendo tipo de atividade: ${tipoAtividade}`);
                await selecionarOpcaoMatAutocomplete(inputTipo, tipoAtividade);
            }
        }

        // 2. Responsável
        if (responsavel) {
            const inputResp = await waitElem('input[formcontrolname="responsavel"], input[aria-label*="Responsável"]', 3000, formAtividade);
            if (inputResp) {
                log(`Preenchendo responsável: ${responsavel}`);
                await selecionarOpcaoMatAutocomplete(inputResp, responsavel);
            }
        }

        // 3. Prazo
        if (prazo) {
            const inputPrazo = await waitElem('input[formcontrolname="prazo"], input[aria-label*="Prazo"]', 3000, formAtividade);
            if (inputPrazo) {
                log(`Preenchendo prazo: ${prazo}`);
                setNativeValue(inputPrazo, String(prazo));
                await sleep(200);
            }
        }

        // 4. Observação
        if (observacao) {
            const inputObs = await waitElem('textarea[formcontrolname="observacao"], textarea[aria-label*="Observação"]', 3000, formAtividade);
            if (inputObs) {
                log(`Preenchendo observação: ${observacao.slice(0, 40)}...`);
                setNativeValue(inputObs, observacao);
                await sleep(200);
            }
        }

        // 5. Salvar Atividade
        const btnSalvar = Array.from(formAtividade.querySelectorAll('button')).find(b => {
            const t = (b.textContent || '').trim().toLowerCase();
            return t === 'salvar' || t.includes('adicionar');
        });

        if (!btnSalvar) {
            throw new Error('Botão Salvar atividade não encontrado.');
        }

        log('Salvando atividade GIGS...');
        btnSalvar.click();
        await sleep(1000);

        log('Atividade GIGS cadastrada com sucesso.');
        return { sucesso: true, tipoAtividade, observacao };
    }

    /**
     * Conclui atividade existente no GIGS com base em critérios.
     */
    async function concluirAtividade(params = {}) {
        const { tipoAtividade, observacao } = params;
        log(`Tentando concluir atividade GIGS: tipo="${tipoAtividade}", obs="${observacao}"`);

        await garantirGigsAberto();
        await sleep(800);

        const linhas = Array.from(document.querySelectorAll('div[id="tabela-atividades"] table tbody tr, pje-gigs-atividades table tbody tr'));
        if (linhas.length === 0) {
            warn('Nenhuma atividade listada na tabela GIGS.');
            return { sucesso: false, motivo: 'Nenhuma atividade encontrada' };
        }

        for (const linha of linhas) {
            const textoLinha = (linha.textContent || '').toLowerCase();
            const bateTipo = !tipoAtividade || textoLinha.includes(tipoAtividade.toLowerCase());
            const bateObs = !observacao || textoLinha.includes(observacao.toLowerCase());

            if (bateTipo && bateObs) {
                log('Atividade correspondente encontrada. Acionando conclusão...');
                const btnConcluir = linha.querySelector('button[mattooltip*="Concluir"], button[aria-label*="Concluir"], button .fa-check, button.mat-icon-button');
                if (btnConcluir) {
                    btnConcluir.click();
                    await sleep(500);

                    // Confirmação no modal se houver
                    const modalBtnSim = await waitElem('mat-dialog-container button', 3000);
                    if (modalBtnSim) {
                        const btnSim = Array.from(document.querySelectorAll('mat-dialog-container button')).find(b =>
                            (b.textContent || '').trim().toLowerCase().includes('sim')
                        );
                        if (btnSim) btnSim.click();
                    }
                    await sleep(800);
                    return { sucesso: true, concluida: true };
                }
            }
        }

        return { sucesso: false, motivo: 'Atividade alvo não encontrada para conclusão' };
    }

    // Exportação do motor GIGS
    window.PjeAutoActions.gigs = async function (params = {}) {
        const acao = (params.acao || 'criar').toLowerCase();
        if (acao === 'concluir') {
            return await concluirAtividade(params);
        }
        return await criarAtividade(params);
    };

})();
