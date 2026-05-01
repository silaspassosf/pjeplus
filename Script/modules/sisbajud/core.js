'use strict';

// ═══════════════════════════════════════════════════════════════════
// SISBAJUD Core - Extração e Acumulação de Dados
// Baseado em SISB/relatorios/generator.py
// ═══════════════════════════════════════════════════════════════════

/**
 * Estrutura do acumulador:
 * {
 *   executados: {
 *     'NOME|DOCUMENTO': {
 *       nome: 'Nome Executado',
 *       documento: 'CPF/CNPJ',
 *       protocolos: [
 *         {numero: '123', valor: 100.50, valor_formatado: 'R$ 100,50', erro_bloqueio: null}
 *       ],
 *       total: 100.50
 *     }
 *   },
 *   total_geral: 100.50,
 *   ordens_com_erro_bloqueio: []
 * }
 */

window.SisbCore = {
    // ── Acumulador global ────────────────────────────────────────────
    acumulador: {
        executados: {},
        total_geral: 0.0,
        ordens_com_erro_bloqueio: []
    },

    timerId: null,
    // TIMEOUT retained for compatibility but auto-reset is disabled to persist until user finalization
    TIMEOUT: 0,

    // ── Reset ────────────────────────────────────────────────────────
    reset() {
        this.acumulador = {
            executados: {},
            total_geral: 0.0,
            ordens_com_erro_bloqueio: []
        };
        if (this.timerId) {
            clearTimeout(this.timerId);
            this.timerId = null;
        }
        // persist cleared state
        try {
            if (typeof GM_setValue !== 'undefined') {
                GM_setValue('sisbajud_acumulador', JSON.stringify(this.acumulador));
            }
        } catch (e) { console.warn('[SISB Core] GM_setValue reset failed', e); }
        console.log('[SISB Core] Acumulador resetado');
    },

    // ── Agrupar dados (merge) ────────────────────────────────────────
    agruparDados(dados_novos) {
        if (!dados_novos || !dados_novos.executados) return;

        for (const [chave, dados_exec] of Object.entries(dados_novos.executados)) {
            // Se executado já existe, merge protocolos
            if (this.acumulador.executados[chave]) {
                const exec_acum = this.acumulador.executados[chave];

                // Adicionar todos os protocolos (extend)
                const protocolos_novos = Array.isArray(dados_exec.protocolos)
                    ? dados_exec.protocolos
                    : [dados_exec.protocolos].filter(Boolean);

                exec_acum.protocolos.push(...protocolos_novos);
                exec_acum.total += dados_exec.total || 0;
            } else {
                // Novo executado - adicionar integralmente
                this.acumulador.executados[chave] = {
                    nome: dados_exec.nome || 'Executado',
                    documento: dados_exec.documento || '',
                    protocolos: Array.isArray(dados_exec.protocolos)
                        ? [...dados_exec.protocolos]
                        : [dados_exec.protocolos].filter(Boolean),
                    total: parseFloat(dados_exec.total) || 0.0
                };
            }

            // Somar ao total geral
            this.acumulador.total_geral += dados_exec.total || 0;
        }

        // Adicionar ordens com erro (se houver)
        if (dados_novos.ordens_com_erro_bloqueio) {
            this.acumulador.ordens_com_erro_bloqueio.push(
                ...dados_novos.ordens_com_erro_bloqueio
            );
        }

        // Resetar timer
        // Persistir acumulador para sobreviver a navegações/paginas
        try {
            if (typeof GM_setValue !== 'undefined') {
                GM_setValue('sisbajud_acumulador', JSON.stringify(this.acumulador));
            }
        } catch (e) { console.warn('[SISB Core] GM_setValue failed', e); }

        console.log('[SISB Core] Dados agrupados:', {
            executados: Object.keys(this.acumulador.executados).length,
            total_geral: this.acumulador.total_geral
        });
    },

    // ── Extrair dados da página SISBAJUD ─────────────────────────────
    async extrairDadosBloqueios() {
        console.log('[SISB Core] Iniciando extração de bloqueios...');

        // Aguardar container principal (modal ou página PDPJ) e painéis de réus aparecerem (até 15s)
        let cont = null;
        for (let tentativa = 0; tentativa < 25; tentativa++) {
            cont = document.querySelector('.cdk-overlay-container .mat-dialog-container') || document.querySelector('.container-fluid');
            if (cont) {
                const txt = cont.innerText || cont.textContent || '';
                const formatTxt = txt.toLowerCase();
                if (formatTxt.includes('protocolo')) {
                    break;
                }
            }
            await new Promise(resolve => setTimeout(resolve, 600));
        }

        if (!cont) {
            console.warn('[SISB Core] Container de dados não encontrado');
            return null;
        }

        // Aguardar headers de executados aparecerem
        await new Promise(resolve => setTimeout(resolve, 500));

        // Extrair protocolo da ordem
        let protocolo = 'N/A';
        // 1. Tentar estrutura HTML PDPJ
        const protoLabels = Array.from(document.querySelectorAll('.sisbajud-label')).filter(el => {
            return el.textContent && el.textContent.trim().toLowerCase().includes('protocolo');
        });
        if (protoLabels.length > 0 && protoLabels[0].nextElementSibling) {
            protocolo = protoLabels[0].nextElementSibling.textContent.trim();
        } else {
            // 2. Tentar regex ignorando tags HTML
            const txtSemTags = cont.innerHTML.replace(/<[^>]+>/g, ' ');
            const matchProto = txtSemTags.match(/Número do protocolo:\s*(\d+)/i);
            if (matchProto) {
                protocolo = matchProto[1];
            }
        }

        console.log('[SISB Core] Protocolo encontrado:', protocolo);

        // Estrutura de retorno
        const dados_bloqueios = {
            executados: {},
            total_geral: 0.0,
            ordens_com_erro_bloqueio: []
        };

        // Buscar todos os headers de executados globalmente no documento 
        const headers = document.querySelectorAll('mat-expansion-panel-header.sisbajud-mat-expansion-panel-header');

        if (!headers || headers.length === 0) {
            console.warn('[SISB Core] Nenhum header de executado encontrado');
            return dados_bloqueios;
        }

        console.log(`[SISB Core] Encontrados ${headers.length} executados`);

        // Processar cada executado
        for (let idx = 0; idx < headers.length; idx++) {
            const header = headers[idx];

            try {
                // Extrair nome
                let nome = 'Executado não identificado';
                const nomeEl = header.querySelector('.col-reu-dados-nome-pessoa');
                if (nomeEl) {
                    nome = nomeEl.textContent.trim();
                }

                // Extrair documento (CPF/CNPJ)
                let documento = '';
                const docEl = header.querySelector('.col-reu-dados a');
                if (docEl) {
                    documento = docEl.textContent.trim();
                }

                // Extrair valor bloqueado
                let valor_float = 0.0;
                let valor_texto = '';
                const valorEl = header.querySelector('.div-description-reu span');
                if (valorEl) {
                    valor_texto = valorEl.textContent.trim();

                    // Regex para extrair valor: "R$ 187,94"
                    const valorMatch = valor_texto.match(/R\$\s*([0-9.,]+)/);
                    if (valorMatch) {
                        const valorStr = valorMatch[1];
                        // Converter formato BR (1.234,56) para float
                        valor_float = parseFloat(
                            valorStr.replace(/\./g, '').replace(',', '.')
                        );
                    }
                }

                // Pular se valor for 0
                if (valor_float <= 0) {
                    console.log(`[SISB Core] Executado ${idx + 1} sem bloqueio (valor=0)`);
                    continue;
                }

                // Formatar valor
                const valor_formatado = this.formatarValor(valor_float);

                // Criar chave única
                const chave = `${nome}|${documento}`;

                // Inicializar executado se não existir
                if (!dados_bloqueios.executados[chave]) {
                    dados_bloqueios.executados[chave] = {
                        nome: nome,
                        documento: documento,
                        protocolos: [],
                        total: 0.0
                    };
                }

                // Adicionar protocolo
                dados_bloqueios.executados[chave].protocolos.push({
                    numero: protocolo,
                    valor: valor_float,
                    valor_formatado: valor_formatado,
                    erro_bloqueio: null
                });

                // Somar aos totais
                dados_bloqueios.executados[chave].total += valor_float;
                dados_bloqueios.total_geral += valor_float;

                console.log(`[SISB Core] Executado ${idx + 1}: ${nome} - ${valor_formatado}`);

            } catch (err) {
                console.error(`[SISB Core] Erro ao processar executado ${idx + 1}:`, err);
                continue;
            }
        }

        console.log('[SISB Core] Extração concluída:', {
            executados: Object.keys(dados_bloqueios.executados).length,
            total: dados_bloqueios.total_geral
        });

        return dados_bloqueios;
    },

    // ── Formatação de valores ────────────────────────────────────────
    formatarValor(valor) {
        if (!Number.isFinite(valor)) return 'R$ 0,00';

        return valor.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    },

    // ── Detectar erros de bloqueio ───────────────────────────────────
    detectarErroBloqueio(modal, protocolo) {
        // TODO: Implementar detecção de erros específicos
        // Exemplos: "Bloqueio indisponível", "Erro no processamento", etc.
        const texto = modal.textContent || '';

        if (texto.includes('indisponível') || texto.includes('erro')) {
            return {
                protocolo: protocolo,
                valor_esperado: 0.0,
                mensagem: 'Bloqueio indisponível'
            };
        }

        return null;
    }
};

// Carregar acumulador persistido (se existir)
try {
    if (typeof GM_getValue !== 'undefined') {
        const saved = GM_getValue('sisbajud_acumulador');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                if (parsed && parsed.executados) {
                    window.SisbCore.acumulador = parsed;
                    console.log('[SISB Core] Acumulador carregado do storage -', Object.keys(parsed.executados).length, 'executados');
                }
            } catch (e) { console.warn('[SISB Core] parse persisted acumulador failed', e); }
        }
    }
} catch (e) { console.warn('[SISB Core] GM_getValue load failed', e); }

// Registrar cleanup se disponível
if (window.PJeState && window.PJeState.registry) {
    window.PJeState.registry.add(() => {
        if (window.SisbCore.timerId) {
            clearTimeout(window.SisbCore.timerId);
        }
        // Não resetar automaticamente para preservar dados acumulados até finalização pelo usuário
    });
}
