(function () {
    'use strict';

    console.log('[PJeT][aud.marcar] Módulo carregado.');

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

    // ── Remarcar 100% digital ──────────────────────────────────────────────────
    async function remarcar100() {
        const toggle = await waitEl('mat-slide-toggle[formcontrolname="juizoDigital"]', 10000);
        if (!toggle) throw new Error('Toggle Juízo Digital não encontrado');
        if (toggle.classList.contains('mat-checked')) return; // já marcado

        toggle.scrollIntoView({ block: 'center' });
        toggle.querySelector('label.mat-slide-toggle-label').click();
        await sleep(600);

        const p = await waitXPath(
            "//mat-expansion-panel//mat-panel-title[contains(normalize-space(.),'Confirma a inclusão do movimento')]",
            10000
        );
        if (!p) throw new Error('Painel de confirmação não encontrado');
        const sim = btnByText(p.closest('mat-expansion-panel'), 'Sim');
        if (!sim) throw new Error('Botão Sim não encontrado');
        sim.click();
        await sleep(600);

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
            await preencherModalNovoHorario(task.numero, dataStr, horaStr, tipo);
            return;
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
    async function preencherModalNovoHorario(numero, dataStr, horaStr, tipo) {
        const modal = await waitEl('mat-dialog-container', 15000);
        if (!modal) throw new Error('Modal Novo Horário não abriu');

        // Aguarda o auto-preenchimento do nº do processo antes dos outros campos
        await aguardarNumeroProcesso(modal, numero);

        // Mapeia tipo do dialog → texto da opção do dropdown
        const mapaTipo = {
            'Julgamento': 'Encerramento de instrução por videoconferência',
            'Instrução': 'Instrução por videoconferência'
        };
        const textoOpcao = mapaTipo[tipo] || 'Una por videoconferência';

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
        const opcao = [...painel.querySelectorAll('mat-option')]
            .find(o => (o.textContent || '').trim().toLowerCase().includes(textoOpcao.toLowerCase()));
        if (!opcao) throw new Error(`Opção "${textoOpcao}" não encontrada no dropdown`);
        console.log('[MarcarAud][Pauta] tipo selecionado no modal:', opcao.textContent.trim());
        opcao.click();
        await sleep(600);

        // 3) Confirmar
        const btnOk = await waitXPath(
            "//mat-dialog-container//button[.//span[normalize-space(.)='Confirmar']]", 10000
        );
        if (!btnOk) throw new Error('Botão Confirmar não encontrado');
        btnOk.click();
        await sleep(1000);

        if (!await waitXPath(
            "//mat-dialog-container//*[contains(normalize-space(.),'Designa') and contains(normalize-space(.),'Confirmad')]",
            10000
        )) throw new Error('Confirmação de designação não apareceu no modal');

        const fechar = await waitXPath(
            "//mat-dialog-container//button[.//span[normalize-space(.)='Fechar']]", 10000
        );
        if (fechar) { fechar.click(); await sleep(500); }
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

    // Aguarda o PJe preencher automaticamente o nº do processo no modal
    // (Angular preenche de forma assíncrona após abrir o dialog). Só preenche
    // manualmente se o auto-preenchimento não ocorrer dentro do prazo.
    async function aguardarNumeroProcesso(modal, numero, ms = 8000) {
        const input = modal.querySelector('input#inputNumeroProcesso');
        if (!input) throw new Error('Campo Número do Processo não encontrado no modal');

        const t0 = Date.now();
        while (Date.now() - t0 < ms) {
            const valor = (input.value || '').trim();
            if (valor) {
                console.log('[MarcarAud][Pauta] nº do processo pré-preenchido:', valor);
                return valor;
            }
            await sleep(150);
        }

        console.warn('[MarcarAud][Pauta] auto-preenchimento do nº do processo não ocorreu; preenchendo manualmente:', numero);
        setAngularInput(input, numero);
        await sleep(600);
        return (input.value || '').trim();
    }

    async function preencherModal(numero) {
        const modal = await waitEl('mat-dialog-container', 10000);
        if (!modal) throw new Error('Modal de audiência não abriu');

        // Aguarda o auto-preenchimento do nº do processo antes dos outros campos
        await aguardarNumeroProcesso(modal, numero);

        const btnOk = await waitXPath(
            "//mat-dialog-container//button[.//span[normalize-space(.)='Confirmar']]", 10000
        );
        if (!btnOk) throw new Error('Botão Confirmar não encontrado');
        btnOk.click();
        await sleep(1000);

        if (!await waitXPath(
            "//mat-dialog-container//*[contains(normalize-space(.),'Designa') and contains(normalize-space(.),'Confirmad')]",
            10000
        )) throw new Error('Confirmação de designação não apareceu no modal');

        const fechar = await waitXPath(
            "//mat-dialog-container//button[.//span[normalize-space(.)='Fechar']]", 10000
        );
        if (fechar) { fechar.click(); await sleep(500); }
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
            await marcarPauta(task);
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
