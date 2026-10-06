// Script/alvara/extracao_siscondj.js — extração de dados dentro do SISCONDJ (fase 2).
//
// Responsabilidade: ler a tela/API do SISCONDJ e devolver dados estruturados
// para a minuta e preenchimento. Roda SOMENTE quando a aba ativa é do SISCONDJ.

(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    // ─────────────────────────────────────────────────────────────────
    // CONFIG — seletores e endpoints do SISCONDJ
    // ─────────────────────────────────────────────────────────────────
    const CONFIG = {
        dominios: [
            'siscondj',
            'alvaraeletronico',
            'portaltrtsp'
        ],
        seletores: {
            numeroProcesso: '#numeroProcesso',
            btnBuscar: '#bt_buscar',
            tabelaContas: '#table_contas',
            btnEmitirMandato: '#bt_emitir_mandato'
        },
        endpoints: {}
    };

    function ehSiscondj() {
        const host = (window.location.hostname || '').toLowerCase();
        const href = (window.location.href || '').toLowerCase();
        return CONFIG.dominios.some(d => host.includes(d) || href.includes(d));
    }

    function logSiscondj(...args) {
        console.log('[PjeAlvara][siscondj]', ...args);
    }

    function parseMoeda(str) {
        if (!str) return 0;
        const limpo = String(str).replace(/[^\d,\.-]/g, '').replace(/\./g, '').replace(',', '.');
        const num = parseFloat(limpo);
        return isNaN(num) ? 0 : num;
    }

    // ─────────────────────────────────────────────────────────────────
    // LEITURA POR DOM
    // ─────────────────────────────────────────────────────────────────
    function valorDoCampo(seletor) {
        const el = document.querySelector(seletor);
        return el ? String(el.value || el.innerText || '').trim() : '';
    }

    function lerTela() {
        const dados = {};
        for (const [chave, seletor] of Object.entries(CONFIG.seletores)) {
            const valor = valorDoCampo(seletor);
            if (valor) dados[chave] = valor;
        }
        return dados;
    }

    function lerContasJudiciais() {
        const tabela = document.getElementById('table_contas') || document.querySelector('table.relatorio');
        if (!tabela) return [];

        const linhas = Array.from(tabela.querySelectorAll('tr[id^="linhaConta_"]'));
        return linhas.map(tr => {
            const idMatch = tr.id.match(/linhaConta_(\d+)/);
            const contaId = idMatch ? idMatch[1] : '';
            const tdSaldo = tr.querySelector('[id^="td_saldo_corrigido_conta_"]');
            const saldoTexto = (tdSaldo?.innerText || '').trim();
            const carregando = !!tr.querySelector('img.rotate');

            return {
                id: contaId,
                linhaEl: tr,
                saldoTexto,
                saldoValor: parseMoeda(saldoTexto),
                carregando
            };
        });
    }

    function lerParcelasConta(contaId) {
        const subTabela = contaId ? document.getElementById('contaId_' + contaId) : document.querySelector('tr.subtabela');
        if (!subTabela) return [];

        const linhasParcelas = Array.from(subTabela.querySelectorAll('tr[id^="linhaParcela_"]'));
        return linhasParcelas.map(tr => {
            const tdSaldo = tr.querySelector('[id^="td_saldo_parcela_saldo_"]');
            const saldoTexto = (tdSaldo?.innerText || '').trim();
            const chk = tr.querySelector('input[name="parcelasSelecionadas"], input[id^="parcelasSelecionadas_"], input[type="checkbox"]');

            return {
                linhaEl: tr,
                saldoTexto,
                saldoValor: parseMoeda(saldoTexto),
                checkboxEl: chk,
                marcado: chk ? chk.checked : false
            };
        });
    }

    // ─────────────────────────────────────────────────────────────────
    // ORQUESTRADOR DE EXTRAÇÃO
    // ─────────────────────────────────────────────────────────────────
    async function extrairDadosSiscondj() {
        if (!ehSiscondj()) {
            return {
                sucesso: false,
                erro: 'aba atual nao e do SISCONDJ',
                origem: 'siscondj'
            };
        }

        const tela = lerTela();
        const contas = lerContasJudiciais();
        const sucesso = Object.keys(tela).length > 0 || contas.length > 0;

        logSiscondj('extracao concluida — contas encontradas:', contas.length);

        return {
            sucesso,
            tela,
            contas,
            origem: 'siscondj'
        };
    }

    // Consulta externa (pelo módulo AUD)
    async function consultarDocumento(documento) {
        if (!Alv.siscon || typeof Alv.siscon.consultarDocumento !== 'function') {
            throw new Error('Módulo de consulta SISCON não disponível.');
        }
        return Alv.siscon.consultarDocumento(documento);
    }

    Alv.siscondj = Alv.siscondj || {};
    Object.assign(Alv.siscondj, {
        CONFIG,
        ehSiscondj,
        logSiscondj,
        parseMoeda,
        valorDoCampo,
        lerTela,
        lerContasJudiciais,
        lerParcelasConta,
        extrairDadosSiscondj,
        consultarDocumento
    });
})();
