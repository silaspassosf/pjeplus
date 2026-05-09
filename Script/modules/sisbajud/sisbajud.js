'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD Main - Controle principal e UI
// Baseado em SISB/relatorios/generator.py
// Requer: core.js, relatorios.js
// ═══════════════════════════════════════════════════════════════════

if (window.location.href.includes('sisbajud.cnj.jus.br') || window.location.href.includes('sisbajud.pdpj.jus.br')) {

    // ── UI: Container de botões ──────────────────────────────────────
    let containerBotoes = null;

    // ── Badge: contador de dados acumulados ─────────────────────────
    let badgeEl = null;
    function atualizarBadge() {
        const numExec = Object.keys(window.SisbCore.acumulador.executados).length;
        if (!badgeEl) {
            badgeEl = document.createElement('div');
            badgeEl.id = 'pjetools-sisb-badge';
            badgeEl.style.cssText = `
                position: fixed; bottom: 160px; right: 20px; z-index: 999998;
                background: #1b1b2f; color: #e0e0e0;
                padding: 8px 14px; border-radius: 6px; font-size: 12px;
                font-family: sans-serif; font-weight: bold;
                box-shadow: 0 3px 10px rgba(0,0,0,0.3);
                border-left: 4px solid #2196f3;
                display: none;
            `;
            document.body.appendChild(badgeEl);
        }
        if (numExec === 0) {
            badgeEl.style.display = 'none';
            return;
        }
        const total = window.SisbCore.formatarValor(window.SisbCore.acumulador.total_geral);
        badgeEl.textContent = numExec + ' executados | Total: ' + total;
        badgeEl.style.display = 'block';
    }

    let toastTimer = null;

    function mostrarToast(mensagem, tipo) {
        // Remove toast anterior
        const prev = document.getElementById('pjetools-sisb-toast');
        if (prev) prev.remove();
        if (toastTimer) clearTimeout(toastTimer);

        const toast = document.createElement('div');
        toast.id = 'pjetools-sisb-toast';
        const cores = { ok: '#28a745', erro: '#dc3545', aviso: '#ffc107' };
        const icones = { ok: '✅', erro: '❌', aviso: '⚠' };
        toast.style.cssText = `
            position: fixed; bottom: 160px; right: 20px; z-index: 9999999;
            background: ${cores[tipo] || '#333'}; color: #fff;
            padding: 10px 16px; border-radius: 6px; font-size: 13px;
            font-family: sans-serif; max-width: 360px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.3);
            transition: opacity 0.3s; opacity: 1;
        `;
        toast.textContent = (icones[tipo] || '') + ' ' + mensagem;
        document.body.appendChild(toast);

        toastTimer = setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => { if (toast.parentNode) toast.remove(); }, 300);
        }, tipo === 'erro' ? 5000 : 3000);
    }

    function criarContainer() {
        if (containerBotoes) return containerBotoes;

        containerBotoes = document.createElement('div');
        containerBotoes.id = 'pjetools-sisb-container';
        containerBotoes.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 999999;
            display: flex;
            flex-direction: column;
            gap: 8px;
        `;
        document.body.appendChild(containerBotoes);
        return containerBotoes;
    }

    function criarBotao(id, texto, cor, onclick) {
        const btn = document.createElement('button');
        btn.id = id;
        btn.textContent = texto;
        btn.style.cssText = `
            background: ${cor};
            color: #fff;
            border: none;
            border-radius: 4px;
            padding: 10px 16px;
            font-weight: bold;
            font-size: 13px;
            cursor: pointer;
            box-shadow: 0 3px 8px rgba(0,0,0,0.25);
            transition: transform 0.2s, box-shadow 0.2s;
            min-width: 200px;
            text-align: left;
        `;
        btn.onmouseover = () => {
            btn.style.transform = 'translateY(-2px)';
            btn.style.boxShadow = '0 5px 12px rgba(0,0,0,0.35)';
        };
        btn.onmouseout = () => {
            btn.style.transform = 'translateY(0)';
            btn.style.boxShadow = '0 3px 8px rgba(0,0,0,0.25)';
        };
        btn.onclick = onclick;
        return btn;
    }

    // ── Ações dos botões ─────────────────────────────────────────────

    async function extrairDados() {
        const btn = document.getElementById('btn-sisb-extrair');
        btn.textContent = '⏳ Extraindo...';
        btn.style.background = '#e6a8d7';
        btn.disabled = true;

        try {
            const dados = await window.SisbCore.extrairDadosBloqueios();

            if (!dados || Object.keys(dados.executados).length === 0) {
                mostrarToast('Nenhum modal de detalhamento do SISBAJUD encontrado aberto', 'aviso');
                return;
            }

            // Agrupar nos dados acumulados
            window.SisbCore.agruparDados(dados);

            const numExec = Object.keys(window.SisbCore.acumulador.executados).length;
            const totalFmt = window.SisbCore.formatarValor(window.SisbCore.acumulador.total_geral);

            mostrarToast(`Dados extraídos! ${numExec} executados | Total: ${totalFmt}`, 'ok');
            atualizarBadge();

        } catch (err) {
            console.error('[SISB] Erro na extração:', err);
            mostrarToast('Erro: ' + err.message, 'erro');
        } finally {
            btn.textContent = '📥 Extrair Dados';
            btn.style.background = '#2196f3';
            btn.disabled = false;
        }
    }

    async function gerarRelatorioDetalhado() {
        const btn = document.getElementById('btn-sisb-detalhado');

        if (Object.keys(window.SisbCore.acumulador.executados).length === 0) {
            mostrarToast('Nenhum dado acumulado. Extraia dados primeiro.', 'aviso');
            return;
        }

        btn.textContent = '⏳ Gerando...';
        btn.style.background = '#9c27b0';
        btn.disabled = true;

        try {
            await sleep(100);
            const resultado = await window.SisbRelatorios.gerarECopiarDetalhado();
            mostrarToast(resultado.mensagem, 'ok');
        } catch (err) {
            console.error('[SISB] Erro ao gerar relatório:', err);
            mostrarToast('Erro: ' + err.message, 'erro');
        } finally {
            btn.textContent = '📄 Relatório Detalhado';
            btn.style.background = '#6f42c1';
            btn.disabled = false;
        }
    }

    async function gerarRelatorioConciso() {
        const btn = document.getElementById('btn-sisb-conciso');

        if (Object.keys(window.SisbCore.acumulador.executados).length === 0) {
            mostrarToast('Nenhum dado acumulado. Extraia dados primeiro.', 'aviso');
            return;
        }

        btn.textContent = '⏳ Gerando...';
        btn.style.background = '#009688';
        btn.disabled = true;

        try {
            await sleep(100);
            const resultado = await window.SisbRelatorios.gerarECopiarConciso();
            mostrarToast(resultado.mensagem, 'ok');
        } catch (err) {
            console.error('[SISB] Erro ao gerar relatório:', err);
            mostrarToast('Erro: ' + err.message, 'erro');
        } finally {
            btn.textContent = '📋 Relatório Conciso';
            btn.style.background = '#00796b';
            btn.disabled = false;
        }
    }

    let _resetClickTime = 0;
    async function resetarDados() {
        const agora = Date.now();
        if (agora - _resetClickTime > 1500) {
            _resetClickTime = agora;
            mostrarToast('Clique novamente em Reset para confirmar', 'aviso');
            return;
        }
        _resetClickTime = 0;
        window.SisbCore.reset();
        mostrarToast('Dados resetados!', 'ok');
        atualizarBadge();
    }

    // ── Injetar UI ───────────────────────────────────────────────────
    function injetarUI() {
        const isDetalhar = window.location.href.includes('/detalhar');
        const containerAtivo = document.getElementById('pjetools-sisb-container');

        if (!isDetalhar) {
            if (containerAtivo) containerAtivo.style.display = 'none';
            return;
        }

        if (containerAtivo) {
            containerAtivo.style.display = 'flex';
            return;
        }

        const container = criarContainer();

        // Botão 1: Extrair dados
        const btnExtrair = criarBotao(
            'btn-sisb-extrair',
            '📥 Extrair Dados',
            '#2196f3',
            extrairDados
        );
        container.appendChild(btnExtrair);

        // Botão 2: Relatório detalhado
        const btnDetalhado = criarBotao(
            'btn-sisb-detalhado',
            '📄 Relatório Detalhado',
            '#6f42c1',
            gerarRelatorioDetalhado
        );
        container.appendChild(btnDetalhado);

        // Botão 3: Relatório conciso
        const btnConciso = criarBotao(
            'btn-sisb-conciso',
            '📋 Relatório Conciso',
            '#00796b',
            gerarRelatorioConciso
        );
        container.appendChild(btnConciso);

        // Botão 4: Reset (menor e discreto)
        const btnReset = criarBotao(
            'btn-sisb-reset',
            '🔄 Reset',
            '#757575',
            resetarDados
        );
        btnReset.style.fontSize = '11px';
        btnReset.style.padding = '6px 12px';
        btnReset.style.minWidth = '100px';
        btnReset.style.textAlign = 'center';
        container.appendChild(btnReset);

        // Mostrar badge se já houver dados acumulados
        atualizarBadge();

        console.log('[SISB] UI injetada com sucesso');
    }

    // Injetar periodicamente para lidar com SPA
    setInterval(injetarUI, 1500);
}
