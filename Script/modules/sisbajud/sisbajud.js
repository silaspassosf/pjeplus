'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD Main - Controle principal e UI
// Baseado em SISB/relatorios/generator.py
// Requer: core.js, relatorios.js
// ═══════════════════════════════════════════════════════════════════

if (window.location.href.includes('sisbajud.cnj.jus.br') || window.location.href.includes('sisbajud.pdpj.jus.br')) {

    // ── UI: Container de botões ──────────────────────────────────────
    let containerBotoes = null;

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
                alert('⚠ Nenhum modal de detalhamento do SISBAJUD foi encontrado aberto.\n\n' +
                    'Certifique-se de que o modal com os dados de bloqueio está visível na tela.');
                return;
            }

            // Agrupar nos dados acumulados
            window.SisbCore.agruparDados(dados);

            const numExec = Object.keys(window.SisbCore.acumulador.executados).length;
            const totalFmt = window.SisbCore.formatarValor(window.SisbCore.acumulador.total_geral);

            alert(`✅ Dados extraídos e acumulados!\n\n` +
                `Executados: ${numExec}\n` +
                `Total acumulado: ${totalFmt}\n\n` +
                `Use os botões de relatório para gerar a saída final.`);

        } catch (err) {
            console.error('[SISB] Erro na extração:', err);
            alert(`❌ Erro: ${err.message}`);
        } finally {
            btn.textContent = '📥 Extrair Dados';
            btn.style.background = '#2196f3';
            btn.disabled = false;
        }
    }

    async function gerarRelatorioDetalhado() {
        const btn = document.getElementById('btn-sisb-detalhado');

        if (Object.keys(window.SisbCore.acumulador.executados).length === 0) {
            alert('⚠ Nenhum dado acumulado.\n\nClique em "Extrair Dados" primeiro.');
            return;
        }

        btn.textContent = '⏳ Gerando...';
        btn.style.background = '#9c27b0';
        btn.disabled = true;

        try {
            await sleep(100);
            const resultado = await window.SisbRelatorios.gerarECopiarDetalhado();
            alert(resultado.mensagem);
        } catch (err) {
            console.error('[SISB] Erro ao gerar relatório:', err);
            alert(`❌ Erro: ${err.message}`);
        } finally {
            btn.textContent = '📄 Relatório Detalhado';
            btn.style.background = '#6f42c1';
            btn.disabled = false;
        }
    }

    async function gerarRelatorioConciso() {
        const btn = document.getElementById('btn-sisb-conciso');

        if (Object.keys(window.SisbCore.acumulador.executados).length === 0) {
            alert('⚠ Nenhum dado acumulado.\n\nClique em "Extrair Dados" primeiro.');
            return;
        }

        btn.textContent = '⏳ Gerando...';
        btn.style.background = '#009688';
        btn.disabled = true;

        try {
            await sleep(100);
            const resultado = await window.SisbRelatorios.gerarECopiarConciso();
            alert(resultado.mensagem);
        } catch (err) {
            console.error('[SISB] Erro ao gerar relatório:', err);
            alert(`❌ Erro: ${err.message}`);
        } finally {
            btn.textContent = '📋 Relatório Conciso';
            btn.style.background = '#00796b';
            btn.disabled = false;
        }
    }

    async function resetarDados() {
        if (!confirm('🔄 Resetar todos os dados acumulados?')) {
            return;
        }

        window.SisbCore.reset();
        alert('✅ Dados resetados!\n\nO acumulador foi limpo.');
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

        console.log('[SISB] UI injetada com sucesso');
    }

    // Injetar periodicamente para lidar com SPA
    setInterval(injetarUI, 1500);
}
