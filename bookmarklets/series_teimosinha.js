/**
 * BOOKMARKLET: SÉRIES TEIMOSINHA (Completo)
 * ========================================
 *
 * Sistema alvo: SISBAJUD
 * Tamanho: ~27KB
 * Versão: Anti-conflito
 *
 * Funcionalidades:
 * - Detecção automática de séries elegíveis
 * - Extração de dados (protocolo, data, valor)
 * - Geração de relatório HTML formatado
 * - Sistema de proteção contra conflitos
 * - Múltiplas estratégias de detecção
 * - Cópia automática para clipboard
 *
 * Como usar:
 * 1. Copie o código JavaScript abaixo
 * 2. Crie um bookmarklet no navegador colando no campo URL
 * 3. Execute na página de séries do SISBAJUD
 */

javascript: (function () {
    'use strict';

    // Sistema de proteção contra conflitos
    if (window.seriesTeimosinhaRunning) {
        console.warn('[TEIMOSINHA] Já está executando. Abortando...');
        mostrarNotificacao('⚠️ Extração de séries já está em execução', 'warning');
        return;
    }
    window.seriesTeimosinhaRunning = true;

    // Extração principal
    function extrairSeriesTeimosinha() {
        console.log('[TEIMOSINHA] Iniciando extração de séries elegíveis...');

        const linhasTabela = document.querySelectorAll('tbody tr, .mat-row, tr[data-serie-id], tr.serie-row');

        if (linhasTabela.length === 0) {
            const alternativas = ['table tr:not(:first-child)', '.series-container .serie-item', '[class*="serie"]', '.tabela-series tr'];
            for (const seletor of alternativas) {
                const elementos = document.querySelectorAll(seletor);
                if (elementos.length > 0) {
                    console.log(`[TEIMOSINHA] Encontrado ${elementos.length} elementos com seletor: ${seletor}`);
                    break;
                }
            }
        }

        const series = [];
        linhasTabela.forEach((linha, index) => {
            const textoLinha = linha.textContent || linha.innerText || '';
            const colunas = linha.querySelectorAll('td, .mat-cell');

            if (colunas.length >= 3) {
                let numeroProtocolo = '', dataConclusao = '', valorBloqueado = '', idSerie = '';

                const atributoId = linha.getAttribute('data-serie-id') || linha.getAttribute('id') || linha.querySelector('[data-serie-id]')?.getAttribute('data-serie-id');
                if (atributoId) idSerie = atributoId;
                else {
                    const matchId = textoLinha.match(/série\s+(\d+)/i);
                    if (matchId) idSerie = matchId[1];
                }

                const matchProtocolo = textoLinha.match(/(\d{7,}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}|\d{10,})/);
                if (matchProtocolo) numeroProtocolo = matchProtocolo[1];

                const matchData = textoLinha.match(/(\d{1,2})[\/](\d{1,2})[\/](\d{4})/);
                if (matchData) dataConclusao = `${matchData[1].padStart(2, '0')}/${matchData[2].padStart(2, '0')}/${matchData[3]}`;

                const matchValor = textoLinha.match(/R\$\s*([\d.,]+)/);
                if (matchValor) valorBloqueado = `R$ ${matchValor[1]}`;

                if (idSerie || numeroProtocolo) {
                    series.push({
                        indice: series.length + 1,
                        idSerie: idSerie || `ID-${series.length + 1}`,
                        numeroProtocolo: numeroProtocolo || 'Protocolo não identificado',
                        dataConclusao: dataConclusao || 'Data não identificada',
                        valorBloqueado: valorBloqueado || 'Valor não identificado',
                        textoCompleto: textoLinha.trim()
                    });
                }
            }
        });

        // Fallback para extração por texto
        if (series.length === 0) {
            console.log('[TEIMOSINHA] Tentando extração baseada em texto...');
            const textoCompleto = document.body.textContent || document.body.innerText || '';
            const linhasTexto = textoCompleto.split('\n').filter(linha => linha.trim().length > 10);

            linhasTexto.forEach(linha => {
                const textoLimpo = linha.trim();
                if (/série|protocolo|\d{7,}-\d{2}\.\d{4}/i.test(textoLimpo)) {
                    let numeroProtocolo = '', dataConclusao = '', valorBloqueado = '';

                    const matchProtocolo = textoLimpo.match(/(\d{7,}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}|\d{10,})/);
                    if (matchProtocolo) numeroProtocolo = matchProtocolo[1];

                    const matchData = textoLimpo.match(/(\d{1,2})[\/](\d{1,2})[\/](\d{4})/);
                    if (matchData) dataConclusao = `${matchData[1].padStart(2, '0')}/${matchData[2].padStart(2, '0')}/${matchData[3]}`;

                    const matchValor = textoLimpo.match(/R\$\s*([\d.,]+)/);
                    if (matchValor) valorBloqueado = `R$ ${matchValor[1]}`;

                    if (numeroProtocolo || /série/i.test(textoLimpo)) {
                        series.push({
                            indice: series.length + 1,
                            idSerie: `Série-${series.length + 1}`,
                            numeroProtocolo: numeroProtocolo || 'Protocolo não identificado',
                            dataConclusao: dataConclusao || 'Data não identificada',
                            valorBloqueado: valorBloqueado || 'Valor não identificado',
                            textoCompleto: textoLimpo
                        });
                    }
                }
            });
        }

        // Gerar relatório se encontrou séries
        if (series.length > 0) {
            const dataAtual = new Date().toLocaleDateString('pt-BR');
            let relatorioHTML = '';
            relatorioHTML += '<p style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:center;text-indent:4.5cm;" class="corpo"><strong>JUNTADA</strong></p>';
            relatorioHTML += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify;text-indent:4.5cm;">Nessa data, procedo à juntada de informação sobre séries de teimosinha elegíveis processadas no sistema SISBAJUD, conforme dados abaixo transcritos:</p>';
            relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Data da conferência: ${dataAtual}</p>`;
            relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Total de séries encontradas: <strong>${series.length}</strong></p>`;
            relatorioHTML += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Discriminação das séries elegíveis:</p>';

            series.forEach((serie, index) => {
                relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:1cm;text-align:justify !important;text-indent:4.5cm;">• <u>Série ${serie.idSerie}</u> - Protocolo: ${serie.numeroProtocolo} - Data da conclusão: ${serie.dataConclusao} - Valor bloqueado: <strong>${serie.valorBloqueado}</strong>`;
                if (index < series.length - 1) relatorioHTML += '<br>';
                relatorioHTML += '</p>';
            });

            relatorioHTML += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"><br data-cke-filler="true"></p>';

            navigator.clipboard.writeText(relatorioHTML).then(() => {
                mostrarNotificacao(`✅ ${series.length} séries copiadas (formato HTML)!`, 'success');
            }).catch(() => {
                const textarea = document.createElement('textarea');
                textarea.value = relatorioHTML;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                mostrarNotificacao(`✅ ${series.length} séries copiadas!`, 'success');
            });

            console.log('[TEIMOSINHA] Relatório HTML gerado:', relatorioHTML);
        } else {
            mostrarNotificacao('❌ Nenhuma série elegível encontrada', 'error');
            console.log('[TEIMOSINHA] Nenhuma série encontrada na página');
        }
    }

    // Notificações
    function mostrarNotificacao(mensagem, tipo = 'info') {
        const cores = { success: '#4CAF50', error: '#f44336', info: '#2196F3', warning: '#FF9800' };
        const notificacao = document.createElement('div');
        notificacao.textContent = mensagem;
        notificacao.style.cssText = `position:fixed;top:20px;right:20px;background:${cores[tipo]};color:white;padding:15px 25px;border-radius:8px;font-size:16px;font-weight:bold;z-index:99999;box-shadow:0 4px 15px rgba(0,0,0,0.3);font-family:Arial,sans-serif;`;
        document.body.appendChild(notificacao);
        setTimeout(() => { if (notificacao.parentNode) notificacao.parentNode.removeChild(notificacao); }, 4000);
    }

    // Executar
    extrairSeriesTeimosinha();
    setTimeout(() => { window.seriesTeimosinhaRunning = false; }, 1000);
})();