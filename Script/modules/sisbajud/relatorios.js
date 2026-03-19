'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD Relatórios - Geração de relatórios detalhados e concisos
// Baseado em SISB/relatorios/generator.py
// ═══════════════════════════════════════════════════════════════════

window.SisbRelatorios = {

    // Estilo padrão dos parágrafos
    P_STYLE: 'style="margin:0;padding:0;text-indent:4.5cm;line-height:1.5;font-size:12pt;text-align:justify;"',

    // ── Relatório DETALHADO ──────────────────────────────────────────
    /**
     * Gera relatório completo com cada protocolo listado individualmente.
     * Formato:
     * - Executado: Nome (documento)
     *   - Protocolo 123 - Valor: R$ 100,00
     *   - Protocolo 456 - Valor: R$ 200,00
     *   - Total do executado: R$ 300,00
     * - Seção de erros (se houver)
     */
    gerarDetalhado(dados_bloqueios) {
        if (!dados_bloqueios || !dados_bloqueios.executados) {
            return 'Nenhum bloqueio processado encontrado.';
        }

        const executados = dados_bloqueios.executados;
        const totalGeral = dados_bloqueios.total_geral || 0;
        const ordensErro = dados_bloqueios.ordens_com_erro_bloqueio || [];

        if (Object.keys(executados).length === 0) {
            return 'Nenhum bloqueio processado encontrado.';
        }

        let html = '';
        const pS = this.P_STYLE;

        // Título
        html += `<p ${pS}><strong>BLOQUEIOS TRANSFERIDOS - SISBAJUD</strong></p>`;

        // Percorrer cada executado
        for (const [chave, dados] of Object.entries(executados)) {
            const nome = dados.nome || 'Executado não identificado';
            const doc = dados.documento || '';
            const protocolos = dados.protocolos || [];
            const total = dados.total || 0;

            // Cabeçalho do executado
            const docStr = doc ? ` - ${doc}` : '';
            html += `<p ${pS}><strong>Executado: ${nome}${docStr}</strong></p>`;

            // Listar cada protocolo
            for (const prot of protocolos) {
                const numero = prot.numero || 'N/A';
                const valorFmt = prot.valor_formatado || 'R$ 0,00';
                const erro = prot.erro_bloqueio;

                if (erro) {
                    html += `<p ${pS}>Protocolo ${numero} - <strong><u>ERRO: ${erro}</u></strong></p>`;
                } else {
                    html += `<p ${pS}>Protocolo ${numero} - Valor: ${valorFmt}</p>`;
                }
            }

            // Total do executado
            const totalFmt = window.SisbCore.formatarValor(total);
            html += `<p ${pS}><strong>Total do executado: ${totalFmt}</strong></p>`;
        }

        // Total geral
        const totalGeralFmt = window.SisbCore.formatarValor(totalGeral);
        html += `<p ${pS}><strong>Total efetivamente transferido à conta judicial do processo: ${totalGeralFmt}</strong></p>`;

        // Mensagem sobre transferência em 48h
        html += `<p ${pS}>Considerando os bloqueios realizados, as quantias localizadas foram <strong>TRANSFERIDAS</strong> à conta judicial do processo, ação que será efetivada em até 48h úteis.</p>`;

        // Seção de erros (se houver)
        if (ordensErro.length > 0) {
            html += `<p ${pS}><strong><u>ORDENS COM ERRO DE BLOQUEIO:</u></strong></p>`;

            for (const ordemErro of ordensErro) {
                const prot = ordemErro.protocolo || 'N/A';
                const valEsp = ordemErro.valor_esperado || 0;
                const valEspFmt = window.SisbCore.formatarValor(valEsp);

                html += `<p ${pS}>Protocolo ${prot}: Bloqueio esperado de ${valEspFmt} está <strong>INDISPONÍVEL</strong> para transferência.</p>`;
            }

            html += `<p ${pS}>As ordens acima, com erro de processamento, serão alvo de ofício ao suporte do SISBAJUD para esclarecimentos, caso os valores não estejam disponíveis em até 10 dias.</p>`;
        }

        return html;
    },

    // ── Relatório CONCISO ────────────────────────────────────────────
    /**
     * Gera relatório resumido com protocolos agrupados por executado.
     * Formato:
     * - Nome (documento):
     *   Ordens com bloqueios transferidos: [123, 456] - Total: R$ 300,00
     */
    gerarConciso(dados_bloqueios) {
        if (!dados_bloqueios || !dados_bloqueios.executados) {
            return '';
        }

        const executados = dados_bloqueios.executados;
        const ordensErro = dados_bloqueios.ordens_com_erro_bloqueio || [];

        if (Object.keys(executados).length === 0) {
            return '';
        }

        let html = '';
        const pS = this.P_STYLE;

        // Título
        html += `<p ${pS}><strong>Relatório de bloqueios discriminado por executado:</strong></p>`;

        // Percorrer cada executado
        for (const [chave, dados] of Object.entries(executados)) {
            const nome = dados.nome || 'Executado não identificado';
            const doc = dados.documento || '';
            const protocolos = dados.protocolos || [];
            const total = dados.total || 0;

            // Linha 1: Nome (documento)
            const docStr = doc ? ` (${doc})` : '';
            html += `<p ${pS}>- ${nome}${docStr}:</p>`;

            // Construir lista de protocolos com marcação de erros
            const protocolosFormatados = [];
            for (const prot of protocolos) {
                const num = prot.numero || 'N/A';
                const erro = prot.erro_bloqueio;

                if (erro) {
                    protocolosFormatados.push(`<strong><u>${num} (${erro})</u></strong>`);
                } else {
                    protocolosFormatados.push(num);
                }
            }

            const protocolosStr = protocolosFormatados.length > 0
                ? protocolosFormatados.join(', ')
                : 'N/A';

            const totalFmt = window.SisbCore.formatarValor(total);

            // Linha 2: Ordens transferidas + total
            html += `<p ${pS}>Ordens com bloqueios transferidos desta parte: [${protocolosStr}] - Total transferido do executado: ${totalFmt}</p>`;
        }

        // Seção de erros (se houver)
        if (ordensErro.length > 0) {
            html += `<p ${pS}><strong><u>ORDENS COM ERRO DE BLOQUEIO:</u></strong></p>`;

            for (const ordemErro of ordensErro) {
                const prot = ordemErro.protocolo || 'N/A';
                const valEsp = ordemErro.valor_esperado || 0;
                const valEspFmt = window.SisbCore.formatarValor(valEsp);

                html += `<p ${pS}>Protocolo ${prot}: Bloqueio esperado de ${valEspFmt} está <strong>INDISPONÍVEL</strong> para transferência.</p>`;
            }

            html += `<p ${pS}>As ordens acima, com erro de processamento, serão alvo de ofício ao suporte do SISBAJUD para esclarecimentos, caso os valores não estejam disponíveis em até 10 dias.</p>`;
        }

        return html;
    },

    // ── Copiar HTML para clipboard ───────────────────────────────────
    copiarHTML(html) {
        if (!html) {
            console.warn('[SISB Relatórios] HTML vazio, nada para copiar');
            return false;
        }

        const div = document.createElement('div');
        div.innerHTML = html;
        document.body.appendChild(div);

        try {
            const sel = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(div);
            sel.removeAllRanges();
            sel.addRange(range);

            const sucesso = document.execCommand('copy');
            sel.removeAllRanges();

            console.log('[SISB Relatórios] HTML copiado:', sucesso);
            return sucesso;
        } catch (err) {
            console.error('[SISB Relatórios] Erro ao copiar:', err);
            return false;
        } finally {
            document.body.removeChild(div);
        }
    },

    // ── Gerar e copiar (detalhado) ───────────────────────────────────
    async gerarECopiarDetalhado() {
        const dados = window.SisbCore.acumulador;
        const html = this.gerarDetalhado(dados);

        if (this.copiarHTML(html)) {
            const numExec = Object.keys(dados.executados).length;
            const totalFmt = window.SisbCore.formatarValor(dados.total_geral);

            return {
                sucesso: true,
                mensagem: `✅ Relatório DETALHADO copiado!\n\n` +
                    `Executados: ${numExec}\n` +
                    `Total: ${totalFmt}`
            };
        } else {
            return {
                sucesso: false,
                mensagem: '❌ Erro ao copiar relatório'
            };
        }
    },

    // ── Gerar e copiar (conciso) ─────────────────────────────────────
    async gerarECopiarConciso() {
        const dados = window.SisbCore.acumulador;
        const html = this.gerarConciso(dados);

        if (this.copiarHTML(html)) {
            const numExec = Object.keys(dados.executados).length;
            const totalFmt = SisbCore.formatarValor(dados.total_geral);

            return {
                sucesso: true,
                mensagem: `✅ Relatório CONCISO copiado!\n\n` +
                    `Executados: ${numExec}\n` +
                    `Total: ${totalFmt}`
            };
        } else {
            return {
                sucesso: false,
                mensagem: '❌ Erro ao copiar relatório'
            };
        }
    }
};
