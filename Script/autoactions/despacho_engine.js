// ==PJeTools Module: autoactions/despacho_engine.js==
// Motor autônomo para elaboração de minutas de Despacho/Decisão no PJe-KZ
// Suporta navegação para conclusão, seleção de magistrado, escolha de modelo ou injeção de texto direto no editor.

(function () {
    'use strict';

    window.PjeAutoActions = window.PjeAutoActions || {};

    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

    function log(msg, ...args) {
        console.log(`[PjeAutoActions][Despacho] ${msg}`, ...args);
    }

    function warn(msg, ...args) {
        console.warn(`[PjeAutoActions][Despacho] ${msg}`, ...args);
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

    async function navegarParaConclusao(timeout = 8000) {
        log('Verificando se já estamos na tela de elaboração ou conclusão...');
        if (document.querySelector('PJE-ARVORE-MODELO-DOCUMENTO, div[class*="area-conteudo"] div[contenteditable="true"]')) {
            log('Já na tela do editor de minuta.');
            return true;
        }

        // Procura botão/link de conclusão ao magistrado
        const btnConclusao = document.querySelector('a[aria-label="Concluso ao Magistrado"], button[aria-label*="Conclusão"], button[aria-label*="concluso"], a[mattooltip*="Concluso"]');
        if (btnConclusao) {
            log('Clicando para mover para Conclusão ao Magistrado...');
            btnConclusao.click();
            await sleep(1200);
        }

        return true;
    }

    async function selecionarMagistrado(nomeJuiz, timeout = 5000) {
        if (!nomeJuiz) return false;
        log(`Tentando selecionar magistrado: ${nomeJuiz}`);

        const selectMagistrado = await waitElem('mat-select[placeholder*="Magistrado"], mat-select[aria-label*="Magistrado"]', timeout);
        if (!selectMagistrado) {
            warn('Select de Magistrado não localizado.');
            return false;
        }

        selectMagistrado.click();
        await sleep(300);

        const options = Array.from(document.querySelectorAll('mat-option[role="option"], .mat-option'));
        const alvo = options.find(opt => {
            const txt = (opt.textContent || '').toLowerCase();
            return txt.includes(nomeJuiz.toLowerCase());
        });

        if (alvo) {
            alvo.click();
            await sleep(500);
            log(`Magistrado ${nomeJuiz} selecionado.`);
            return true;
        }

        warn(`Magistrado ${nomeJuiz} não encontrado nas opções.`);
        return false;
    }

    async function escolherTipoConclusao(tipo = 'Despacho', timeout = 6000) {
        log(`Selecionando tipo de conclusão: ${tipo}`);
        const botoesTipo = Array.from(document.querySelectorAll('pje-concluso-tarefa-botao button, pje-conclusao-dependencia button, button.mat-raised-button'));
        const btnTipo = botoesTipo.find(b => {
            const t = (b.textContent || '').trim().toLowerCase();
            return t === tipo.toLowerCase() || t.includes(tipo.toLowerCase());
        });

        if (btnTipo) {
            btnTipo.click();
            log(`Botão do tipo ${tipo} clicado. Aguardando editor...`);
            await sleep(1500);
            return true;
        }

        warn(`Botão do tipo "${tipo}" não encontrado.`);
        return false;
    }

    async function aplicarModeloArvore(nomeModelo, timeout = 7000) {
        if (!nomeModelo) return false;
        log(`Buscando modelo na árvore: ${nomeModelo}`);

        const inputFiltro = await waitElem('input[id="inputFiltro"], input[placeholder*="Filtro"], input[aria-label*="filtro"]', timeout);
        if (!inputFiltro) {
            warn('Campo de busca de modelos não encontrado.');
            return false;
        }

        inputFiltro.focus();
        setNativeValue(inputFiltro, nomeModelo);
        await sleep(600);

        // Localiza nó da árvore correspondente
        const nosArvore = Array.from(document.querySelectorAll('mat-tree-node, mat-nested-tree-node, .mat-tree-node'));
        const noAlvo = nosArvore.find(no => {
            const t = (no.textContent || '').toLowerCase();
            return t.includes(nomeModelo.toLowerCase());
        });

        if (noAlvo) {
            const clicavel = noAlvo.querySelector('span, a, button') || noAlvo;
            clicavel.click();
            log(`Modelo "${nomeModelo}" acionado na árvore.`);
            await sleep(1000);
            return true;
        }

        warn(`Modelo "${nomeModelo}" não encontrado na árvore de modelos.`);
        return false;
    }

    async function injetarTextoNoEditor(conteudo, timeout = 7000) {
        if (!conteudo) return false;
        log('Injetando conteúdo diretamente no editor de texto...');

        const editor = await waitElem('div[class*="area-conteudo"] div[contenteditable="true"], div.ck-content[contenteditable="true"]', timeout);
        if (!editor) {
            warn('Área editável do editor não encontrada.');
            return false;
        }

        editor.focus();
        await sleep(200);

        try {
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, conteudo);
            editor.dispatchEvent(new Event('input', { bubbles: true }));
            editor.dispatchEvent(new Event('change', { bubbles: true }));
            log('Texto inserido com sucesso via execCommand.');
            return true;
        } catch (e) {
            warn('Falha no execCommand, aplicando via textContent/innerHTML:', e);
            editor.innerText = conteudo;
            editor.dispatchEvent(new Event('input', { bubbles: true }));
            return true;
        }
    }

    /**
     * Elabora minuta de despacho/decisão.
     * @param {Object} params
     * @param {string} [params.tipo='Despacho'] 'Despacho', 'Decisão' ou 'Sentença'
     * @param {string} [params.juiz] Nome do magistrado
     * @param {string} [params.modelo] Nome do modelo a carregar
     * @param {string} [params.texto] Texto livre para o corpo
     * @param {string} [params.descricao] Descrição da minuta
     * @param {boolean} [params.assinar=false] Enviar para assinatura
     * @param {boolean} [params.salvar=true] Salvar a minuta
     */
    window.PjeAutoActions.despacho = async function (params = {}) {
        const tipo = params.tipo || 'Despacho';
        const { juiz, modelo, texto, descricao, assinar = false, salvar = true } = params;

        log(`Iniciando motor de despacho: tipo=${tipo}, modelo=${modelo || 'nenhum'}, assinar=${assinar}`);

        await navegarParaConclusao();
        await sleep(500);

        if (juiz) {
            await selecionarMagistrado(juiz);
        }

        await escolherTipoConclusao(tipo);

        // Aguarda carregar tela do editor
        await waitElem('PJE-ARVORE-MODELO-DOCUMENTO, div[class*="area-conteudo"]', 8000);
        await sleep(800);

        // 1. Descrição
        if (descricao) {
            const inputDesc = document.querySelector('input[aria-label="Descrição"], input[placeholder*="Descrição"]');
            if (inputDesc) {
                log(`Preenchendo descrição: ${descricao}`);
                setNativeValue(inputDesc, descricao);
            }
        }

        // 2. Modelo da árvore (se informado)
        if (modelo) {
            await aplicarModeloArvore(modelo);
        }

        // 3. Texto customizado (se informado)
        if (texto) {
            await injetarTextoNoEditor(texto);
        }

        // 4. Salvar
        if (salvar) {
            const btnSalvar = document.querySelector('button[aria-label="Salvar"], button[mattooltip*="Salvar"]');
            if (btnSalvar) {
                log('Clicando em Salvar minuta...');
                btnSalvar.click();
                await sleep(1500);
            }
        }

        // 5. Assinar / Enviar para assinatura
        if (assinar) {
            const btnAssinar = document.querySelector('button[aria-label="Enviar para assinatura"], button[aria-label*="Assinar"]');
            if (btnAssinar) {
                log('Enviando minuta para assinatura...');
                btnAssinar.click();
                await sleep(1200);
            }
        }

        log('Motor de despacho concluído com êxito.');
        return { sucesso: true, tipo, descricao, salvo: salvar, assinado: assinar };
    };

})();
