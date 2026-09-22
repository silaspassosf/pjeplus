// Script/alvara/extracao_siscondj.js — extração de dados dentro do SISCONDJ (fase 2).
//
// Responsabilidade: ler a tela/API do SISCONDJ e devolver dados estruturados
// para a minuta (Alv.minuta). Roda SOMENTE quando a aba ativa é do SISCONDJ.
//
// Alvo de tamanho na fase 2: ~300 linhas. Estrutura abaixo já organiza os
// pontos de extensão para chegar lá sem retrabalho:
//   - CONFIG: seletores/endpoints (preencher com os valores reais levantados
//     na fase 2 — usar o padrão de levantamento do gigs-plugin.js/hcalc-prep).
//   - _dom(): leitura de campos por seletor.
//   - _api(): leitura por endpoint, se disponível (XSRF igual dados_processo).
//   - extrairDadosSiscondj(): orquestra e devolve objeto canônico.

(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    // ─────────────────────────────────────────────────────────────────
    // CONFIG — preencher na fase 2 com valores reais do SISCONDJ.
    // ─────────────────────────────────────────────────────────────────
    const CONFIG = {
        dominios: [
            'siscondj',
            // 'siacont', etc — confirmar na fase 2
        ],
        seletores: {
            // TODO fase 2: seletores dos campos/telas do SISCONDJ
            // exemplo: fluxoAtual: 'select[name="fluxo"]',
        },
        endpoints: {
            // TODO fase 2: endpoints REST do SISCONDJ, se existirem
        }
    };

    function _ehSiscondj() {
        const host = (window.location.hostname || '').toLowerCase();
        return CONFIG.dominios.some(d => host.includes(d));
    }

    function _log(...args) {
        console.log('[PjeAlvara][siscondj]', ...args);
    }

    // ─────────────────────────────────────────────────────────────────
    // LEITURA POR DOM
    // ─────────────────────────────────────────────────────────────────
    function _valorDoCampo(seletor) {
        const el = document.querySelector(seletor);
        return el ? String(el.value || el.innerText || '').trim() : '';
    }

    function _lerTela() {
        const dados = {};

        for (const [chave, seletor] of Object.entries(CONFIG.seletores)) {
            const valor = _valorDoCampo(seletor);
            if (valor) dados[chave] = valor;
        }

        return dados;
    }

    // ─────────────────────────────────────────────────────────────────
    // LEITURA POR API (opcional, fase 2)
    // ─────────────────────────────────────────────────────────────────
    async function _lerApi() {
        // TODO fase 2: GET com credentials include + XSRF, mesmo padrão de
        // Alv.dados (ver dados_processo.js). Retornar null se não houver.
        return null;
    }

    // ─────────────────────────────────────────────────────────────────
    // ORQUESTRADOR
    // ─────────────────────────────────────────────────────────────────

    /**
     * Extrai os dados correntes do SISCONDJ para a minuta.
     * Formato canônico devolvido (fase 2 define os campos finais):
     * {
     *     sucesso: true|false,
     *     tela: { ...campos lidos por seletor... },
     *     api:  { ...dados de endpoint, se houver... },
     *     origem: 'siscondj'
     * }
     */
    async function extrairDadosSiscondj() {
        if (!_ehSiscondj()) {
            return {
                sucesso: false,
                erro: 'aba atual nao e do SISCONDJ',
                origem: 'siscondj'
            };
        }

        const tela = _lerTela();
        const api = await _lerApi();

        const sucesso = Object.keys(tela).length > 0 || !!api;

        _log('extracao concluida — campos de tela:', Object.keys(tela).length);

        return {
            sucesso,
            tela,
            api,
            origem: 'siscondj'
        };
    }

    // API pública usada pelo painel de AUD; a busca efetiva fica centralizada
    // em siscon_consulta.js, que já conhece os endpoints e o parser do SISCON.
    async function consultarDocumento(documento) {
        if (!Alv.siscon || typeof Alv.siscon.consultarDocumento !== 'function') {
            throw new Error('Módulo de consulta SISCON não disponível.');
        }
        return Alv.siscon.consultarDocumento(documento);
    }

    Alv.siscondj = { extrairDadosSiscondj, consultarDocumento };
})();
