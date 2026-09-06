// ==PJeTools Module: autoactions/autoactions.js==
// Fachada global e dispatcher do Motor de Ações Automatizadas (PjeAutoActions)
// Permite invocação programática direta (headless) ou acionamento via botões de interface.

(function () {
    'use strict';

    window.PjeAutoActions = window.PjeAutoActions || {};

    const self = window.PjeAutoActions;

    self.versao = '1.0.0';

    /**
     * Executa uma ação automatizada pelo nome e parâmetros.
     * @param {string} nomeAcao 'gigs', 'despacho' ou 'anexar'
     * @param {Object} params Parâmetros específicos da ação
     * @returns {Promise<Object>} Resultado da execução
     */
    self.executar = async function (nomeAcao, params = {}) {
        if (!nomeAcao || typeof nomeAcao !== 'string') {
            throw new Error('[PjeAutoActions] Nome da ação deve ser informado.');
        }

        const acaoNorm = nomeAcao.trim().toLowerCase();

        console.log(`[PjeAutoActions] Despachando ação: "${acaoNorm}" com parâmetros:`, params);

        switch (acaoNorm) {
            case 'gigs':
            case 'autogigs':
                if (typeof self.gigs !== 'function') {
                    throw new Error('[PjeAutoActions] Submotor gigs_engine.js não carregado.');
                }
                return await self.gigs(params);

            case 'despacho':
            case 'decisao':
            case 'minuta':
                if (typeof self.despacho !== 'function') {
                    throw new Error('[PjeAutoActions] Submotor despacho_engine.js não carregado.');
                }
                return await self.despacho(params);

            case 'anexar':
            case 'juntada':
            case 'certidao':
                if (typeof self.anexar !== 'function') {
                    throw new Error('[PjeAutoActions] Submotor anexar_engine.js não carregado.');
                }
                return await self.anexar(params);

            default:
                throw new Error(`[PjeAutoActions] Ação desconhecida: "${nomeAcao}". Ações disponíveis: gigs, despacho, anexar.`);
        }
    };

    /**
     * Executa uma lista sequencial de ações automatizadas (Pipeline).
     * @param {Array<{acao: string, params: Object}>} passos
     * @param {Function} [onProgress] Callback opcional de progresso (passoAtual, total)
     * @returns {Promise<Array<Object>>} Resultados de cada passo
     */
    self.executarPipeline = async function (passos = [], onProgress = null) {
        if (!Array.isArray(passos) || passos.length === 0) {
            console.warn('[PjeAutoActions] Pipeline vazio recebido.');
            return [];
        }

        console.log(`[PjeAutoActions] Iniciando pipeline de ${passos.length} passo(s)...`);
        const resultados = [];

        for (let i = 0; i < passos.length; i++) {
            const passo = passos[i];
            console.log(`[PjeAutoActions] Executando passo ${i + 1}/${passos.length}: ${passo.acao}`);

            if (typeof onProgress === 'function') {
                try {
                    onProgress(i + 1, passos.length, passo);
                } catch (e) {
                    console.warn('[PjeAutoActions] Erro no callback onProgress:', e);
                }
            }

            try {
                const res = await self.executar(passo.acao, passo.params);
                resultados.push({ sucesso: true, passo: passo.acao, resultado: res });
            } catch (err) {
                console.error(`[PjeAutoActions] Falha no passo ${i + 1} (${passo.acao}):`, err);
                resultados.push({ sucesso: false, passo: passo.acao, erro: String(err) });
                // Se passo falhar, interrompe pipeline por segurança
                break;
            }
        }

        console.log('[PjeAutoActions] Pipeline finalizado.', resultados);
        return resultados;
    };

    console.log(`[PjeAutoActions] Motor v${self.versao} pronto para uso.`);
})();
