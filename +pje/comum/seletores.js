var SELETORES = {
    convenios : {
        sisbajud: {
            botaoValorExecucao: '*[id="maisPJe_valor_execucao"]'
        }
    },
    editor: {
        areaConteudo: 'div[class*="area-conteudo"][contenteditable="true"][role="textbox"]',
        botaoPesquisarSubstituir: 'button[data-cke-tooltip-text*="Pesquisar e substituir"]'
    },
    painelGlobal : {
        tituloAgrupamento : 'pje-lista-processos h1'
    }
}
/** @typedef {typeof SELETORES} SeletoresMap */

/**
 * Verifica se existe um arquivo `seletores.json` remoto e, se houver,
 * mescla seu conteúdo na variável SELETORES (somente as chaves presentes
 * no arquivo remoto são sobrescritas; as demais permanecem intactas).
 *
 * @param {string} base_url   - URL base do repositório (sem barra final).
 * @param {string} versaoPJe  - Versão do PJe, ex.: "2.20.3".
 * @returns {Promise<boolean>} Retorna `true` se os seletores remotos foram
 *                             carregados, `false` caso contrário.
 */
async function carregarSeletoresRemotos(base_url, versaoPJe) {
    const url = `${base_url}/${versaoPJe}/seletores.json`;
    try {
        const resposta = await fetch(url);
        if (!resposta.ok) return false;

        const seletoresRemotos = await resposta.json();

        for (const [chave, valor] of Object.entries(seletoresRemotos)) {
            if (valor !== null && typeof valor === 'object' && !Array.isArray(valor)) {
                // Mescla sub-objetos preservando chaves locais ausentes no remoto
                SELETORES[chave] = { ...SELETORES[chave], ...valor };
            } else {
                SELETORES[chave] = valor;
            }
        }

        console.log(`[seletores] Seletores remotos carregados de: ${url}`);
        return true;
    } catch (erro) {
        console.warn(`[seletores] Arquivo remoto não encontrado ou inválido: ${url}`, erro);
        return false;
    }
}
