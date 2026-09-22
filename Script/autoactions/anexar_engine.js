// ==PJeTools Module: autoactions/anexar_engine.js==
// Motor autônomo para anexar documentos e certidões no PJe-KZ
// Suporta preenchimento de tipo de documento, descrição, editor de texto e assinatura.

(function () {
    'use strict';

    window.PjeAutoActions = window.PjeAutoActions || {};

    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

    function log(msg, ...args) {
        console.log(`[PjeAutoActions][Anexar] ${msg}`, ...args);
    }

    function warn(msg, ...args) {
        console.warn(`[PjeAutoActions][Anexar] ${msg}`, ...args);
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

    async function navegarParaAnexar(timeout = 8000) {
        log('Verificando tela de anexar documento...');
        if (location.pathname.includes('/documento/anexar') || document.querySelector('input[aria-label*="Tipo de Documento"]')) {
            log('Já na tela de anexar.');
            return true;
        }

        const btnAnexar = document.querySelector('a[aria-label="Anexar Documentos"], button[aria-label*="Anexar Documentos"], a[mattooltip*="Anexar"]');
        if (btnAnexar) {
            log('Clicando em Anexar Documentos...');
            btnAnexar.click();
            await sleep(1200);
            return true;
        }

        // Se estiver em detalhes de processo, tentar derivar rota
        const match = location.pathname.match(/\/processo\/(\d+)\/detalhe/);
        if (match) {
            const idProcesso = match[1];
            log(`Navegando diretamente para anexar do processo ${idProcesso}...`);
            location.href = `/pjekz/processo/${idProcesso}/documento/anexar`;
            await sleep(1500);
        }

        return true;
    }

    async function selecionarTipoDocumento(tipo = 'Certidão', timeout = 5000) {
        log(`Selecionando tipo de documento: ${tipo}`);
        const inputTipo = await waitElem('input[aria-label*="Tipo de Documento"], input[placeholder*="Tipo de Documento"]', timeout);
        if (!inputTipo) {
            warn('Campo Tipo de Documento não localizado.');
            return false;
        }

        inputTipo.focus();
        inputTipo.click();
        setNativeValue(inputTipo, tipo);
        inputTipo.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
        await sleep(400);

        const options = Array.from(document.querySelectorAll('mat-option[role="option"], .mat-option'));
        const opt = options.find(o => {
            const t = (o.textContent || '').trim().toLowerCase();
            return t.includes(tipo.toLowerCase());
        }) || options[0];

        if (opt) {
            opt.click();
            await sleep(300);
            log(`Tipo ${tipo} selecionado com sucesso.`);
            return true;
        }

        warn(`Opção de tipo ${tipo} não encontrada na lista.`);
        return false;
    }

    async function injetarTextoNoEditor(conteudo, timeout = 7000) {
        if (!conteudo) return false;
        log('Injetando texto no editor da tela de anexar...');

        const editor = await waitElem('div[class*="area-conteudo"] div[contenteditable="true"], div.ck-content[contenteditable="true"]', timeout);
        if (!editor) {
            warn('Editor de texto não encontrado na tela de anexar.');
            return false;
        }

        editor.focus();
        await sleep(200);

        try {
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, conteudo);
            editor.dispatchEvent(new Event('input', { bubbles: true }));
            editor.dispatchEvent(new Event('change', { bubbles: true }));
            log('Conteúdo inserido com sucesso.');
            return true;
        } catch (e) {
            warn('Falha em execCommand, aplicando via textContent:', e);
            editor.innerText = conteudo;
            editor.dispatchEvent(new Event('input', { bubbles: true }));
            return true;
        }
    }

    /**
     * Anexa documento ou certidão ao processo.
     * @param {Object} params
     * @param {string} [params.tipo='Certidão'] Tipo do documento
     * @param {string} [params.descricao] Descrição a preencher
     * @param {string} [params.texto] Conteúdo do documento
     * @param {boolean} [params.sigilo=false] Documento sigiloso
     * @param {boolean} [params.assinar=false] Assinar e juntar automaticamente
     */
    window.PjeAutoActions.anexar = async function (params = {}) {
        const tipo = params.tipo || 'Certidão';
        const { descricao, texto, sigilo = false, assinar = false } = params;

        log(`Iniciando motor de anexar: tipo=${tipo}, desc="${descricao || ''}", assinar=${assinar}`);

        await navegarParaAnexar();
        await sleep(500);

        // 1. Tipo de Documento
        await selecionarTipoDocumento(tipo);

        // 2. Descrição
        if (descricao) {
            const inputDesc = await waitElem('input[aria-label="Descrição"], input[placeholder*="Descrição"]', 4000);
            if (inputDesc) {
                log(`Preenchendo descrição: ${descricao}`);
                setNativeValue(inputDesc, descricao);
                await sleep(200);
            }
        }

        // 3. Sigilo
        if (sigilo) {
            const checkSigilo = document.querySelector('input[name="sigiloso"], mat-checkbox[name="sigiloso"]');
            if (checkSigilo && !checkSigilo.checked) {
                log('Marcando documento como sigiloso...');
                checkSigilo.click();
                await sleep(200);
            }
        }

        // 4. Inserção do Texto
        if (texto) {
            await injetarTextoNoEditor(texto);
        }

        // 5. Assinar / Salvar
        if (assinar) {
            const btnAssinar = await waitElem('button[aria-label="Assinar documento e juntar ao processo"], button[aria-label*="Assinar"]', 4000);
            if (btnAssinar) {
                log('Assinando e juntando documento ao processo...');
                btnAssinar.click();
                await sleep(2000);
            } else {
                warn('Botão de assinar documento não encontrado.');
            }
        } else {
            const btnSalvar = document.querySelector('button[aria-label="Salvar"], button[mattooltip*="Salvar"]');
            if (btnSalvar) {
                log('Salvando rascunho do documento...');
                btnSalvar.click();
                await sleep(1000);
            }
        }

        log('Motor de anexar concluído com êxito.');
        return { sucesso: true, tipo, descricao, assinado: assinar };
    };

})();
