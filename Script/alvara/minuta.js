// Script/alvara/minuta.js — GANCHO DA FASE 2 (SISCONDJ).
//
// PLACEHOLDER DEFINITIVO: este módulo NÃO muda mais na fase 1.
// Ele é o ponto de entrada do processo seguinte, chamado pelo botão
// "Criar alvarás" do overlay. Quando a fase 2 (SISCONDJ) for implementada,
// a lógica real entra DENTRO de iniciarFluxoMinuta(), sem alterar o contrato:
//
//     Alv.minuta.iniciarFluxoMinuta(estado) -> { iniciado: boolean, motivo?: string }
//
// Contrato do `estado` recebido (congelado — ver PLANO-MODULAR.md):
// {
//     processo: { numero, partes: { ativo, passivo, outros }, peritos },
//     itens: [ { id, tipo, valor, valorFixo, destinoTipo, destinatarioNome,
//                destinatarioDocumento, dados: { banco, agencia, conta, tipoConta },
//                deposito, transferencia, siscon } ]
// }

(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    function validarEstado(estado) {
        if (!estado) return 'estado ausente';
        if (!Array.isArray(estado.itens) || estado.itens.length === 0) {
            return 'nenhuma verba no estado';
        }
        return null;
    }

    function extrairNumeroProcesso(estado) {
        if (estado && estado.processo && estado.processo.numero) {
            return estado.processo.numero;
        }

        const matchCorpo = document.body?.innerText?.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
        if (matchCorpo) {
            return matchCorpo[0];
        }

        const titulo = document.title?.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
        if (titulo) {
            return titulo[0];
        }

        return '';
    }

    function obterUrlSiscondj(numeroProcesso, argConsulta) {
        let tribunal = '2';
        const trtMatch = numeroProcesso.match(/\.5\.(\d{2})\./);
        if (trtMatch) {
            tribunal = parseInt(trtMatch[1], 10).toString();
        }

        const param = encodeURIComponent(argConsulta);

        if (tribunal === '2') {
            return `https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/new?numeroDoProcesso=${param}`;
        }

        if (tribunal === '4') {
            return `https://siscondj.trt4.jus.br/portaltrtrs/pages/movimentacao/conta/new?numeroDoProcesso=${param}`;
        }

        return `https://siscondj.trt${tribunal}.jus.br/portaltrt${tribunal}/pages/movimentacao/conta/new?numeroDoProcesso=${param}`;
    }

    function iniciarFluxoMinuta(estado) {
        const erro = validarEstado(estado);

        if (erro) {
            console.warn('[PjeAlvara][minuta] fluxo não iniciado:', erro);
            return { iniciado: false, motivo: erro };
        }

        const numeroProcesso = extrairNumeroProcesso(estado);
        const argConsulta = 'avjtSiscondjConsultarAlvaras' + numeroProcesso;

        // 1. Copia o comando com o número do processo para a área de transferência (padrão AVJT)
        try {
            if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                navigator.clipboard.writeText(argConsulta);
            }
        } catch (e) {
            console.warn('[PjeAlvara][minuta] falha ao escrever na área de transferência:', e);
        }

        // 2. Salva o estado de forma compartilhada via GM_setValue para a página de destino (fase 2)
        try {
            if (typeof GM_setValue === 'function') {
                GM_setValue('pje_alvara_estado', JSON.stringify(estado));
                if (numeroProcesso) {
                    GM_setValue('pje_alvara_processo', numeroProcesso);
                }
            }
        } catch (e) {
            console.warn('[PjeAlvara][minuta] falha ao gravar GM_setValue:', e);
        }

        // 3. Constrói a URL do Siscondj e abre nova aba
        const url = obterUrlSiscondj(numeroProcesso, argConsulta);
        window.open(url, '_blank');

        console.log('[PjeAlvara][minuta] SISCONDJ aberto via:', url);
        return { iniciado: true, url };
    }

    Alv.minuta = {
        iniciarFluxoMinuta: iniciarFluxoMinuta,
        extrairNumeroProcesso: extrairNumeroProcesso,
        obterUrlSiscondj: obterUrlSiscondj
    };
})();
