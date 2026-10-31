(function () {
    'use strict';

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

    // ── Task (Storage cross-tab para pjetools) ─────────────────────────────────────────────────────
    const TASK_KEY = 'pje_mau_task';
    const getTask  = () => { try { return JSON.parse(localStorage.getItem(TASK_KEY) || 'null'); } catch { return null; } };
    const setTask  = t  => localStorage.setItem(TASK_KEY, JSON.stringify(t));
    const clearTask = () => localStorage.removeItem(TASK_KEY);

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

        let dataStr, horaStr;
        let tipo = task.ata_tipo || 'Una';

        if (task.ata_data && task.ata_hora) {
            // Se já tem data/hora fixa da Ata, usar diretamente
            // Normaliza ano curto (26 → 2026) para garantir navegação correta no calendário
            dataStr = normalizarData(task.ata_data);
            horaStr = task.ata_hora;
        } else {
            // Logica original: buscar o primeiro horário vago
            const linhaXPath = task.rito === 'ATSUM'
                ? '//tr[.//span[contains(normalize-space(.),"Una (rito sumar")]]'
                : "//tr[.//span[normalize-space(.)='Una'] and not(.//span[contains(normalize-space(.),'sumar')])]";

            const linha = await waitXPath(linhaXPath, 10000);
            if (!linha) throw new Error('Linha de pauta não encontrada para rito ' + task.rito);

            const tds = linha.querySelectorAll('td.td-class');
            if (tds.length < 3) throw new Error('Colunas insuficientes na tabela (' + tds.length + ')');
            dataStr = tds[1].querySelector('span')?.textContent.trim();
            horaStr = tds[2].querySelector('span')?.textContent.trim();
            if (!dataStr || !horaStr) throw new Error(`Data/hora vazios: data='${dataStr}' hora='${horaStr}'`);
        }

        overlay(`Navegando para ${dataStr} às ${horaStr}…`, '#1565c0');
        await navegarCalendario(dataStr);

        // Julgamento (e Encerramento de instrução via ata): o modal "Novo Horário -
        // Designação de Audiência" é aberto pelo botão global Designar (cabeçalho),
        // sem procurar horário na lista — o slot de julgamento não existe na pauta.
        if (tipo === 'Julgamento' || tipo === 'Instrução') {
            await abrirModalNovoHorario();
            await preencherModalNovoHorario(task.numero, dataStr, horaStr, tipo, task.rito);
            return true; // preenchimento manual: usuário confirma no modal
        }

        await clicarSlotHora(horaStr, tipo);
        await preencherModal(task.numero);
    }

    // ── Modal "Novo Horário" (julgamento/encerramento de instrução) ────────────
    // Botão global "Designar Audiência" no cabeçalho da pauta do dia.
    async function abrirModalNovoHorario() {
        const btn = await waitXPath(
            "//button[@mattooltip='Designar Audiência' or @aria-label='Designar Audiência']" +
            "[.//i[contains(@class,'fa-plus-circle')]]",
            15000
        );
        if (!btn) throw new Error('Botão global Designar Audiência não encontrado');
        btn.click();
        await sleep(800);
    }

    // Preenche o modal "Novo Horário - Designação de Audiência":
    // nº do processo e data já vêm preenchidos pela navegação; informa hora e tipo.
    async function preencherModalNovoHorario(numero, dataStr, horaStr, tipo, rito) {
        const modal = await waitEl('mat-dialog-container', 15000);
        if (!modal) throw new Error('Modal Novo Horário não abriu');

        // Espera o PJe povoar o campo nº do processo; só então preenche os
        // demais campos. Nenhuma interação com o campo de processo.
        await aguardarNumeroProcesso(modal, numero);

        // Mapeia tipo do dialog → texto(s) EXATOS da opção do dropdown.
        // O painel tem tanto "Instrução" quanto "Instrução por videoconferência"
        // (e "Encerramento de instrução" / "... por videoconferência") — por isso
        // a busca abaixo é por igualdade exata, não includes.
        // Para cada tipo, tenta os candidatos NA ORDEM: usa o primeiro que
        // existir no painel (Julgamento prefere "Julgamento"; o encerramento
        // é só fallback quando a opção "Julgamento" não existir).
        const mapaTipo = {
            'Julgamento': ['Julgamento', 'Encerramento de instrução por videoconferência'],
            'Instrução': ['Instrução']
        };
        const candidatos = (mapaTipo[tipo] || (
            // Padrão: Una (ou Una rito sumaríssimo, conforme o rito do processo)
            rito === 'ATSUM'
                ? ['Una (rito sumaríssimo)', 'Una']
                : ['Una', 'Una (rito sumaríssimo)']
        )).map(s => s.trim().toLowerCase());

        // 1) Hora (pje-horario > input#horario)
        const inpHora = modal.querySelector('pje-horario input#horario')
                     || modal.querySelector('input#horario');
        if (!inpHora) throw new Error('Campo Horário de Início não encontrado no modal');
        setAngularInput(inpHora, horaStr);
        await sleep(400);

        // 2) Tipo da audiência (mat-select → dropdown)
        const selTipo = modal.querySelector('mat-select');
        if (!selTipo) throw new Error('Select Tipo da audiência não encontrado no modal');
        selTipo.click();
        const painel = await waitEl('.mat-select-panel', 10000);
        if (!painel) throw new Error('Dropdown de Tipo da audiência não abriu');
        const opcoes = [...painel.querySelectorAll('mat-option')];
        let opcao = null;
        for (const cand of candidatos) {
            opcao = opcoes.find(o => (o.textContent || '').trim().toLowerCase() === cand);
            if (opcao) break;
        }
        if (!opcao) throw new Error(`Nenhuma opção ${JSON.stringify(mapaTipo[tipo] || ['Una', 'Una (rito sumaríssimo)'])} encontrada no dropdown`);
        console.log('[MarcarAud][Pauta] tipo selecionado no modal:', opcao.textContent.trim());
        opcao.click();
        await sleep(600);

        // NÃO confirma: o usuário confere os dados e clica em Confirmar ele mesmo.
        console.log('[MarcarAud][Pauta] modal preenchido (hora + tipo) — aguardando confirmação manual');
    }

    // ── Normalização de data (dd/mm/aa ou dd/mm/aaaa → dd/mm/aaaa) ────────────
    // Ano com 2 dígitos recebe prefixo "20" (ex: 16/11/26 → 16/11/2026).
    // Sem isso, new Date(26, ...) vira ano 26 d.C. e o delta de meses fica
    // negativo → o calendário sequer navega para o mês correto.
    function normalizarData(dataStr) {
        const m = String(dataStr || '').trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{2}|\d{4})$/);
        if (!m) return dataStr;
        const [, d, mo, y] = m;
        const yyyy = y.length === 2 ? '20' + y : y;
        return `${d.padStart(2, '0')}/${mo.padStart(2, '0')}/${yyyy}`;
    }

    async function navegarCalendario(dataStr) {
        dataStr = normalizarData(dataStr); // tolerância: garante ano de 4 dígitos
        const [dd, mm, yyyy] = dataStr.split('/').map(Number);
        const alvo  = new Date(yyyy, mm - 1, dd);
        const hoje  = new Date();
        const delta = (alvo.getFullYear() - hoje.getFullYear()) * 12 + (alvo.getMonth() - hoje.getMonth());

        console.log('[MarcarAud][Pauta] navegarCalendario → alvo:', dataStr,
            '| hoje:', hoje.toLocaleDateString('pt-BR'), '| delta meses:', delta);
        if (delta < 0) console.warn('[MarcarAud][Pauta] data alvo no passado — delta negativo:', delta);

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

    async function clicarSlotHora(horaStr, tipo) {
        // Tenta achar a linha específica pelo horário e tipo, mas a visualização do calendário pode não listar o tipo na mesma linha,
        // então procura pela horaStr na primeira coluna.
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

    // Alias para compatibilidade
    const aguardarNumeroProcesso = garantirNumeroProcesso;

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

    // ── Extração de Ata ────────────────────────────────────────────────────────
    
    function extrairDadosAta(textoRaw) {
        if (!textoRaw) { console.log('[MarcarAud][Ata] documento vazio (textoRaw nulo)'); return null; }
        const texto = String(textoRaw);
        console.log('[MarcarAud][Ata] tamanho do documento:', texto.length);

        // Quebra em segmentos (frases) por ponto/vírgula ou quebra de linha.
        const segmentos = texto.split(/[.;]\s*|\r?\n+/).map(s => s.trim()).filter(Boolean);

        // Alvos: segmentos com designação, julgamento ou encerramento de instrução
        const padraoAlvo = /designa|julgamento|encerramento\s+da\s+instru/i;
        const alvos = [];
        segmentos.forEach((s, i) => {
            if (padraoAlvo.test(s)) {
                alvos.push(i);
                console.log(`[MarcarAud][Ata] segmento-alvo [${i}]:`, s.slice(0, 200));
            }
        });
        if (!alvos.length) {
            console.log('[MarcarAud][Ata] nenhum segmento com designa/julgamento/encerramento de instrução');
            return null;
        }

        const regexData = /\b(\d{2})\/(\d{2})\/(\d{2}|\d{4})\b/;
        // Hora aceita "17:10" e "17h10" (padrão comum nas atas: "às 17h10" / "às 17h10min").
        const regexHora = /\b(\d{1,2})\s*(?::|h)\s*(\d{2})?\b/i;
        const hoje = new Date(); hoje.setHours(0, 0, 0, 0);

        // Varre cada segmento-alvo junto com o seguinte (cobre frases cuja
        // data e hora caem em frases separadas pelo corte do ponto).
        const candidatos = [];
        for (const i of alvos) {
            const bloco = segmentos[i] + ' ' + (segmentos[i + 1] || '');
            const mD = bloco.match(regexData);
            const mH = bloco.match(regexHora);
            if (!mD) { console.log(`[MarcarAud][Ata] alvo [${i}] sem data no bloco`); continue; }
            if (!mH || !mH[2]) { console.log(`[MarcarAud][Ata] alvo [${i}] sem hora no bloco`); continue; }
            const yyyy = mD[3].length === 2 ? '20' + mD[3] : mD[3];
            const data = `${mD[1]}/${mD[2]}/${yyyy}`;
            const dt = new Date(+yyyy, +mD[2] - 1, +mD[1]);
            const hora = `${mH[1].padStart(2, '0')}:${mH[2]}`;
            const posterior = dt >= hoje; // hoje ou futuro é marcável (delta >= 0)
            console.log(`[MarcarAud][Ata] candidato [${i}] → ${data} ${hora} | hoje ou futuro? ${posterior}`);
            candidatos.push({ data, hora, dt, posterior, seg: segmentos[i] });
        }
        if (!candidatos.length) { console.log('[MarcarAud][Ata] nenhum candidato data+hora nos alvos'); return null; }

        // Preferência: a designação fica sempre no FIM da ata (nunca é a data do
        // cabeçalho) — pega a última candidata hoje/futura; fallback: última de todas.
        const escolhido = [...candidatos].reverse().find(c => c.posterior) || candidatos[candidatos.length - 1];
        if (!escolhido.posterior) console.warn('[MarcarAud][Ata] nenhuma data hoje/futura — usando a primeira:', escolhido.data);

        // Tipo pelo segmento escolhido
        const segLower = escolhido.seg.toLowerCase();
        let tipo = 'Una';
        if (segLower.includes('julgamento')) tipo = 'Julgamento';
        else if (segLower.includes('instru')) tipo = 'Instrução';

        const res = { data: escolhido.data, hora: escolhido.hora, tipo };
        console.log('[MarcarAud][Ata] resultado final:', res);
        return res;
    }

    function mostrarDialogAta(callback) {
        document.getElementById('_mau_dialog')?.remove();
        
        const overlayBg = document.createElement('div');
        overlayBg.id = '_mau_dialog';
        overlayBg.style.cssText = `position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999999;display:flex;align-items:center;justify-content:center;`;
        
        const box = document.createElement('div');
        box.style.cssText = `background:#fff;padding:20px;border-radius:8px;box-shadow:0 10px 30px rgba(0,0,0,0.5);font-family:sans-serif;width:300px;`;
        
        const title = document.createElement('h3');
        title.textContent = 'Agendar Audiência (Ata)';
        title.style.cssText = `margin:0 0 15px 0;font-size:16px;color:#333;text-align:center;border-bottom:1px solid #eee;padding-bottom:10px;`;
        box.appendChild(title);
        
        const form = document.createElement('div');
        form.style.cssText = `display:flex;flex-direction:column;gap:12px;`;
        
        // Input Data
        const lblData = document.createElement('label');
        lblData.textContent = 'Data (DD/MM/AAAA):';
        lblData.style.cssText = `font-size:12px;color:#555;font-weight:bold;`;
        const inpData = document.createElement('input');
        inpData.type = 'text';
        inpData.placeholder = 'DD/MM/AAAA (ex: 16/11/26 → 2026)';
        inpData.style.cssText = `padding:8px;border:1px solid #ccc;border-radius:4px;font-size:14px;`;
        form.appendChild(lblData);
        form.appendChild(inpData);

        // Máscara dd/mm/aaaa: dígito + separador automático; ano com 2 dígitos
        // recebe prefixo "20" automaticamente ao sair do campo (ex: 26 → 2026).
        inpData.addEventListener('input', () => {
            let v = inpData.value.replace(/\D/g, '').slice(0, 8);
            if (v.length > 4) v = v.slice(0, 2) + '/' + v.slice(2, 4) + '/' + v.slice(4);
            else if (v.length > 2) v = v.slice(0, 2) + '/' + v.slice(2);
            inpData.value = v;
        });
        inpData.addEventListener('blur', () => {
            const m = inpData.value.match(/^(\d{2})\/(\d{2})\/(\d{2})$/);
            if (m) inpData.value = `${m[1]}/${m[2]}/20${m[3]}`;
        });
        
        // Input Hora
        const lblHora = document.createElement('label');
        lblHora.textContent = 'Hora (HH:MM):';
        lblHora.style.cssText = `font-size:12px;color:#555;font-weight:bold;`;        const inpHora = document.createElement('input');
        inpHora.type = 'text';
        inpHora.placeholder = 'HH:MM';
        inpHora.style.cssText = `padding:8px;border:1px solid #ccc;border-radius:4px;font-size:14px;`;
        form.appendChild(lblHora);
        form.appendChild(inpHora);

        // Máscara HH:MM: somente dígitos, separador automático após o 2º dígito.
        inpHora.addEventListener('input', () => {
            let v = inpHora.value.replace(/\D/g, '').slice(0, 4);
            if (v.length > 2) v = v.slice(0, 2) + ':' + v.slice(2);
            inpHora.value = v;
        });
        
        // Select Tipo
        const lblTipo = document.createElement('label');
        lblTipo.textContent = 'Tipo:';
        lblTipo.style.cssText = `font-size:12px;color:#555;font-weight:bold;`;
        const selTipo = document.createElement('select');
        selTipo.style.cssText = `padding:8px;border:1px solid #ccc;border-radius:4px;font-size:14px;`;
        ['Una', 'Instrução', 'Julgamento'].forEach(op => {
            const opt = document.createElement('option');
            opt.value = op;
            opt.textContent = op;
            selTipo.appendChild(opt);
        });
        form.appendChild(lblTipo);
        form.appendChild(selTipo);
        
        const btnContainer = document.createElement('div');
        btnContainer.style.cssText = `display:flex;justify-content:flex-end;gap:10px;margin-top:15px;`;
        
        const btnCancel = document.createElement('button');
        btnCancel.textContent = 'Cancelar';
        btnCancel.style.cssText = `padding:8px 12px;background:#f5f5f5;border:1px solid #ccc;border-radius:4px;cursor:pointer;color:#333;font-weight:bold;`;
        btnCancel.onclick = () => overlayBg.remove();
        
        const btnConfirm = document.createElement('button');
        btnConfirm.textContent = 'Agendar';
        btnConfirm.style.cssText = `padding:8px 12px;background:#1565c0;border:none;border-radius:4px;cursor:pointer;color:#fff;font-weight:bold;`;
        btnConfirm.onclick = () => {
            let dt = inpData.value.trim();
            const hr = inpHora.value.trim();
            // Aceita ano com 2 dígitos e acrescenta "20" (ex: 16/11/26 → 16/11/2026)
            const mDt = dt.match(/^(\d{2})\/(\d{2})\/(\d{2})$/);
            if (mDt) dt = `${mDt[1]}/${mDt[2]}/20${mDt[3]}`;
            if (!/^\d{2}\/\d{2}\/\d{4}$/.test(dt) || !/^\d{2}:\d{2}$/.test(hr)) {
                alert('Preencha data e hora válidas!\nData: DD/MM/AAAA (ano curto aceito, ex: 16/11/26)\nHora: HH:MM');
                return;
            }
            console.log('[MarcarAud][Ata] dados informados pelo usuário → data:', dt, '| hora:', hr, '| tipo:', selTipo.value);
            overlayBg.remove();
            callback(dt, hr, selTipo.value);
        };
        
        btnContainer.appendChild(btnCancel);
        btnContainer.appendChild(btnConfirm);
        box.appendChild(form);
        box.appendChild(btnContainer);
        overlayBg.appendChild(box);
        document.body.appendChild(overlayBg);
    }

    // ── Disparos ──────────────────────────────────────────────────────────────

    async function dispararProcesso(dadosAta = null) {
        overlay('Iniciando…', '#555');
        try {
            const url = window.location.href;
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

            let precisaDesmarcar100 = is100;
            // Se for Ata de Julgamento, não desmarca o 100%
            if (dadosAta && dadosAta.tipo === 'Julgamento') {
                precisaDesmarcar100 = false;
            }

            const t = { 
                numero: cnj, 
                processoId, 
                rito, 
                is100, 
                precisaDesmarcar100,
                step: precisaDesmarcar100 ? 'retificar' : 'pauta',
                ata_data: dadosAta ? dadosAta.data : null,
                ata_hora: dadosAta ? dadosAta.hora : null,
                ata_tipo: dadosAta ? dadosAta.tipo : null
            };
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
                precisaDesmarcar100
                    ? `https://pje.trt2.jus.br/pjekz/processo/${processoId}/retificar`
                    : buildPautaUrl(t),
                '_blank'
            );
        } catch (err) {
            overlay('❌ ' + err.message, '#c62828');
        }
    }

    // ── /retificar ──────────────────────────────────────────────────────────────
    async function initRetificar() {
        const url = window.location.href;
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
                // Remarcar apenas se antes era 100% digital
                if (task.is100) {
                    await remarcar100();
                }
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
            const manual = await marcarPauta(task);
            if (manual) {
                // Modal preenchido mas NÃO confirmado: mantém a aba aberta para
                // o usuário conferir e clicar em Confirmar. Sinaliza as outras
                // abas (ex.: remarcar 100% digital) sem fechar esta.
                overlay('⚠️ Confira os dados e clique em Confirmar no modal…', '#e65100', 0);
                bc.postMessage(task.precisaDesmarcar100 ? { type: 'PAUTA_DONE' } : { type: 'DONE' });
                bc.close();
                return;
            }
            overlay('✅ Marcado!', '#2e7d32', 2000);
            bc.postMessage(task.precisaDesmarcar100 ? { type: 'PAUTA_DONE' } : { type: 'DONE' });
            bc.close();
            await sleep(600);
            window.close();
        } catch (err) {
            overlay('❌ Pauta: ' + err.message, '#c62828');
        }
    }

    async function checarConfirmacao() {
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
        }
    }

    // ── API Pública ────────────────────────────────────────────────────────────

    window.PjeMarcarAud = {
        executarNova: function() {
            dispararProcesso(null);
        },
        
        executarAta: async function() {
            var extractor = window.pjeExtrair || window.PjeExtrair;
            if (typeof extractor !== 'function') {
                console.error('Extrator não disponível.');
                alert('Extrator não carregado. Verifique se o documento está aberto.');
                return;
            }

            overlay('Extraindo ata...', '#555');
            var res = await extractor().catch(e => ({ sucesso: false, erro: e.message || String(e) }));
            
            if (!res.sucesso) {
                overlay('❌ Falha na extração. Abra o PDF ou Minuta.', '#c62828');
                return;
            }
            
            var textoRaw = res.conteudo_bruto || res.conteudo || '';
            console.log('[MarcarAud][Ata] extração OK — tamanho do texto bruto:', textoRaw.length);
            var dadosAta = extrairDadosAta(textoRaw);
            console.log('[MarcarAud][Ata] dadosAta resultante:', dadosAta);
            
            if (dadosAta) {
                console.log('Dados extraídos da Ata:', dadosAta);
                dispararProcesso(dadosAta);
            } else {
                mostrarDialogAta((data, hora, tipo) => {
                    dispararProcesso({ data, hora, tipo });
                });
            }
        },

        initRetificar: initRetificar,
        initPauta: initPauta,
        checarConfirmacao: checarConfirmacao
    };

})();
