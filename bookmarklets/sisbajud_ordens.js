/**
 * BOOKMARKLET: SISBAJUD ORDENS JUDICIAIS
 * =====================================
 *
 * Sistema alvo: SISBAJUD
 * Tamanho: ~18KB
 * Versão: Completa
 *
 * Funcionalidades:
 * - Extração de ordens executadas
 * - Cálculo de valores bloqueados
 * - Geração de relatórios consolidados
 * - Sistema de acumulação de dados
 * - Formatação BRL automática
 * - Cópia automática para clipboard
 *
 * Como usar:
 * 1. Copie o código JavaScript abaixo
 * 2. Crie um bookmarklet no navegador colando no campo URL
 * 3. Execute na página de ordens do SISBAJUD
 */

javascript: (function () {
    'use strict';

    // Armazenamento global de dados acumulados
    let ordensAcumuladas = {
        executados: {},
        totalGeral: 0.0,
        ultimaExtracao: null
    };

    // Utilitários para valores BRL
    function brlToFloat(txt) {
        if (!txt) return 0;
        const n = txt.replace(/R\$/g, '').replace(/\./g, '').replace(',', '.').replace(/\s/g, '').trim();
        const v = parseFloat(n);
        return Number.isFinite(v) ? v : 0;
    }

    function toBRL(n) {
        try {
            return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        } catch {
            return `R$ ${(Number(n) || 0).toFixed(2).replace('.', ',')}`;
        }
    }

    // Notificações
    function mostrarNotificacao(mensagem, tipo = 'info') {
        const cores = { success: '#4CAF50', error: '#f44336', info: '#2196F3', warning: '#FF9800' };
        const notificacao = document.createElement('div');
        notificacao.textContent = mensagem;
        notificacao.style.cssText = `position:fixed;top:20px;right:20px;background:${cores[tipo]};color:white;padding:15px 25px;border-radius:8px;font-size:16px;font-weight:bold;z-index:99999;box-shadow:0 4px 15px rgba(0,0,0,0.3);font-family:Arial,sans-serif;`;
        document.body.appendChild(notificacao);
        setTimeout(() => { if (notificacao.parentNode) notificacao.parentNode.removeChild(notificacao); }, 5000);
    }

    // Extração principal de ordens
    function extrairOrdensJudiciais() {
        console.log('[SISBAJUD ORDENS] Iniciando extração de ordens judiciais...');

        const seletoresOrdens = [
            'tbody tr', '.mat-row', 'tr[data-ordem-id]', 'tr.ordem-row',
            '[class*="ordem"]', '.tabela-ordens tr'
        ];

        let ordensEncontradas = [];

        for (const seletor of seletoresOrdens) {
            const elementos = document.querySelectorAll(seletor);
            if (elementos.length > 0) {
                console.log(`[SISBAJUD ORDENS] Encontrado ${elementos.length} elementos com seletor: ${seletor}`);

                elementos.forEach((elemento, index) => {
                    const textoElemento = elemento.textContent || elemento.innerText || '';
                    const colunas = elemento.querySelectorAll('td, .mat-cell');

                    if (colunas.length >= 4 || textoElemento.length > 20) {
                        let numeroOrdem = '', dataExecucao = '', valorBloqueado = '', idOrdem = '';

                        const atributoId = elemento.getAttribute('data-ordem-id') ||
                            elemento.getAttribute('id') ||
                            elemento.querySelector('[data-ordem-id]')?.getAttribute('data-ordem-id');
                        if (atributoId) idOrdem = atributoId;
                        else {
                            const matchId = textoElemento.match(/ordem\s+(\d+)/i);
                            if (matchId) idOrdem = matchId[1];
                        }

                        const matchProtocolo = textoElemento.match(/(\d{7,}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}|\d{10,})/);
                        if (matchProtocolo) numeroOrdem = matchProtocolo[1];

                        const matchData = textoElemento.match(/(\d{1,2})[\/](\d{1,2})[\/](\d{4})/);
                        if (matchData) dataExecucao = `${matchData[1].padStart(2, '0')}/${matchData[2].padStart(2, '0')}/${matchData[3]}`;

                        const matchValor = textoElemento.match(/R\$\s*([\d.,]+)/);
                        if (matchValor) valorBloqueado = `R$ ${matchValor[1]}`;

                        if (idOrdem || numeroOrdem) {
                            const ordem = {
                                indice: ordensEncontradas.length + 1,
                                idOrdem: idOrdem || `ID-${ordensEncontradas.length + 1}`,
                                numeroOrdem: numeroOrdem || 'Ordem não identificada',
                                dataExecucao: dataExecucao || 'Data não identificada',
                                valorBloqueado: valorBloqueado || 'Valor não identificado',
                                valorNumerico: brlToFloat(valorBloqueado),
                                textoCompleto: textoElemento.trim()
                            };
                            ordensEncontradas.push(ordem);
                        }
                    }
                });

                if (ordensEncontradas.length > 0) break;
            }
        }

        // Fallback para extração por texto
        if (ordensEncontradas.length === 0) {
            console.log('[SISBAJUD ORDENS] Tentando extração baseada em texto...');
            const textoCompleto = document.body.textContent || document.body.innerText || '';
            const linhasTexto = textoCompleto.split('\n').filter(linha => linha.trim().length > 10);

            linhasTexto.forEach(linha => {
                const textoLimpo = linha.trim();
                if (/ordem|protocolo|\d{7,}-\d{2}\.\d{4}/i.test(textoLimpo)) {
                    let numeroOrdem = '', dataExecucao = '', valorBloqueado = '';

                    const matchProtocolo = textoLimpo.match(/(\d{7,}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}|\d{10,})/);
                    if (matchProtocolo) numeroOrdem = matchProtocolo[1];

                    const matchData = textoLimpo.match(/(\d{1,2})[\/](\d{1,2})[\/](\d{4})/);
                    if (matchData) dataExecucao = `${matchData[1].padStart(2, '0')}/${matchData[2].padStart(2, '0')}/${matchData[3]}`;

                    const matchValor = textoLimpo.match(/R\$\s*([\d.,]+)/);
                    if (matchValor) valorBloqueado = `R$ ${matchValor[1]}`;

                    if (numeroOrdem || /ordem/i.test(textoLimpo)) {
                        ordensEncontradas.push({
                            indice: ordensEncontradas.length + 1,
                            idOrdem: `Ordem-${ordensEncontradas.length + 1}`,
                            numeroOrdem: numeroOrdem || 'Ordem não identificada',
                            dataExecucao: dataExecucao || 'Data não identificada',
                            valorBloqueado: valorBloqueado || 'Valor não identificado',
                            valorNumerico: brlToFloat(valorBloqueado),
                            textoCompleto: textoLimpo
                        });
                    }
                }
            });
        }

        // Processar ordens encontradas
        if (ordensEncontradas.length > 0) {
            ordensEncontradas.forEach(ordem => {
                const chave = ordem.numeroOrdem;
                if (!ordensAcumuladas.executados[chave]) {
                    ordensAcumuladas.executados[chave] = { ordens: [], totalValor: 0.0 };
                }
                ordensAcumuladas.executados[chave].ordens.push(ordem);
                ordensAcumuladas.executados[chave].totalValor += ordem.valorNumerico;
                ordensAcumuladas.totalGeral += ordem.valorNumerico;
            });

            ordensAcumuladas.ultimaExtracao = new Date().toISOString();

            // Gerar relatório
            const dataAtual = new Date().toLocaleDateString('pt-BR');
            let relatorioHTML = '';
            relatorioHTML += '<p style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:center;text-indent:4.5cm;" class="corpo"><strong>EXECUÇÃO DE ORDENS JUDICIAIS</strong></p>';
            relatorioHTML += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify;text-indent:4.5cm;">Nessa data, procedo à juntada de informação sobre ordens judiciais executadas no sistema SISBAJUD, conforme dados abaixo transcritos:</p>';
            relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Data da conferência: ${dataAtual}</p>`;
            relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Total de ordens encontradas: <strong>${ordensEncontradas.length}</strong></p>`;
            relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Valor total bloqueado: <strong>${toBRL(ordensAcumuladas.totalGeral)}</strong></p>`;
            relatorioHTML += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;">Discriminação das ordens executadas:</p>';

            ordensEncontradas.forEach((ordem, index) => {
                relatorioHTML += `<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:1cm;text-align:justify !important;text-indent:4.5cm;">• <u>Ordem ${ordem.idOrdem}</u> - Protocolo: ${ordem.numeroOrdem} - Data da execução: ${ordem.dataExecucao} - Valor bloqueado: <strong>${ordem.valorBloqueado}</strong>`;
                if (index < ordensEncontradas.length - 1) relatorioHTML += '<br>';
                relatorioHTML += '</p>';
            });

            relatorioHTML += '<p class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"><br data-cke-filler="true"></p>';

            // Copiar para clipboard
            navigator.clipboard.writeText(relatorioHTML).then(() => {
                mostrarNotificacao(`✅ ${ordensEncontradas.length} ordens copiadas (Total: ${toBRL(ordensAcumuladas.totalGeral)})`, 'success');
            }).catch(() => {
                const textarea = document.createElement('textarea');
                textarea.value = relatorioHTML;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                mostrarNotificacao(`✅ ${ordensEncontradas.length} ordens copiadas (Total: ${toBRL(ordensAcumuladas.totalGeral)})`, 'success');
            });

            console.log('[SISBAJUD ORDENS] Relatório HTML gerado:', relatorioHTML);
            console.log('[SISBAJUD ORDENS] Dados acumulados:', ordensAcumuladas);
        } else {
            mostrarNotificacao('❌ Nenhuma ordem judicial encontrada', 'error');
            console.log('[SISBAJUD ORDENS] Nenhuma ordem encontrada na página');
        }
    }

    // Executar
    extrairOrdensJudiciais();
})();