// ==UserScript==
// @name         PJeTools — Elaboração de Alvará
// @namespace    pjetools
// @version      0.6.0
// @description  Analisa decisão ativa e prepara dados para elaboração de alvarás
// @author       PJeTools
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe#*
// @match        https://pje.trt*.jus.br/pjekz/processo/*/detalhe
// @match        https://pje.trt*.jus.br/pjekz/processo/*/detalhe#*
// @grant        GM_xmlhttpRequest
// @connect      aplicacoes1.trt2.jus.br
// @run-at       document-start
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/extrair.js
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/utils.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/extracao.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/dados_processo.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/estado.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/estilos.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/overlay.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/siscon_consulta.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/extracao_siscondj.js?v=3
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/alvara/minuta.js?v=3
// ==/UserScript==

(function () {
    'use strict';

    const INSTANCE_KEY =
        '__PJE_ALVARA_USERSCRIPT_INSTANCE__';

    const INSTANCE_VERSION = '0.5.0';

    if (window[INSTANCE_KEY]) {
        console.warn(
            '[PjeAlvara] segunda execução ignorada:',
            location.href
        );
        return;
    }

    window[INSTANCE_KEY] = {
        version: INSTANCE_VERSION,
        startedAt: new Date().toISOString()
    };

    function isPaginaDetalhe() {
        return /^\/pjekz\/processo\/\d+\/detalhe(?:\/.*)?$/i
            .test(location.pathname);
    }

    const Alv = (window.Alv = window.Alv || {});
    const BUTTON_ID = Alv.const.BUTTON_ID;
    const BUTTON_HOST_ID = Alv.const.BUTTON_HOST_ID;
    const OVERLAY_ID = Alv.const.OVERLAY_ID;
    const logDiagnostico = Alv.log.diag;
    const logAviso = Alv.log.aviso;
    const obterTextoDecisao = Alv.extracao.obterTextoDecisao;
    const extrairValores = Alv.extracao.extrairValores;
    const buscarDadosProcesso = Alv.dados.buscarDadosProcesso;
    const obterProcessoId = Alv.dados.obterProcessoId;
    const criarEstado = Alv.estado.criarEstado;
    const abrirOverlay = Alv.overlay.abrirOverlay;
    async function analisarDecisao() {
        const processoId = obterProcessoId();

        if (!processoId) {
            alert(
                'Não foi possível identificar o número do processo.'
            );
            return;
        }

        const visualizador = document.querySelector(
            'object.conteudo-pdf,' +
            'mat-card.container-html,' +
            '.visualizador-html,' +
            'iframe,' +
            'embed,' +
            '[class*="visualizador"],' +
            '[class*="documento"],' +
            '[class*="pdf"],' +
            '[class*="conteudo"]'
        );

        if (!visualizador) {
            logAviso(
                'visualizador não identificado; ' +
                'a extração incorporada será tentada mesmo assim.'
            );
        }

        const botao = document.getElementById(BUTTON_ID);

        if (botao) {
            botao.disabled = true;
            botao.textContent = 'Analisando...';
        }

        try {
            const texto = await obterTextoDecisao();

            console.log(
                '[PjeAlvara] TEXTO EXTRAIDO DA DECISAO (por fonte):'
            );
            console.log(texto);

            const valores = extrairValores(texto);

            console.log(
                '[PjeAlvara] PADROES RECONHECIDOS:'
            );
            console.log(JSON.stringify({
                credito: valores.credito,
                creditoPorDepositoSemValor: valores.creditoPorDepositoSemValor,
                creditoParcialDeposito: valores.creditoParcialDeposito,
                deposito: valores.deposito,
                inss: valores.inss,
                custas: valores.custas,
                honorariosAdvocaticios: valores.honorariosAdvocaticios,
                honorariosPericiais: valores.honorariosPericiais,
                peritoNome: valores.peritoNome,
                devolucaoReclamada: valores.devolucaoReclamada,
                devolucaoReclamadaValor: valores.devolucaoReclamadaValor,
                transferenciaOutroProcesso: valores.transferenciaOutroProcesso,
                transferenciaProcessoDestino: valores.transferenciaProcessoDestino
            }, null, 2));

            // Dados do processo via API (partes + advogados) — sempre frescos.
            const dadosProcesso = await buscarDadosProcesso();

            // Sem perguntas: o overlay SEMPRE abre, com apenas os tipos
            // detectados na decisão (ou a linha de nenhum tipo detectado).
            const estado = criarEstado(valores, dadosProcesso);

            console.log(
                '[PjeAlvara] ITENS CRIADOS NO OVERLAY:'
            );
            console.log(JSON.stringify(estado.itens.map(function (i) {
                return {
                    id: i.id,
                    valor: i.valor,
                    valorFixo: i.valorFixo === true,
                    perito: i.perito,
                    destinatario: i.destinatarioNome
                };
            }), null, 2));

            abrirOverlay(estado);
        } catch (error) {
            console.error('[PjeAlvara] Erro:', error);

            alert(
                'Não foi possível analisar a decisão:\n\n' +
                error.message
            );
        } finally {
            if (botao) {
                botao.disabled = false;
                botao.textContent = 'Alvará';
            }
        }
    }

    function criarBotao() {
        if (!isPaginaDetalhe()) {
            logDiagnostico(
                'rota atual não é detalhe:',
                location.pathname
            );
            return false;
        }

        const botaoExistente =
            document.getElementById(BUTTON_ID);

        if (botaoExistente) {
            return true;
        }

        if (!document.body) {
            logAviso(
                'document.body ainda não existe; nova tentativa será feita.'
            );
            return false;
        }

        const botao = document.createElement('button');

        botao.id = BUTTON_ID;
        botao.type = 'button';
        botao.textContent = 'Alvará';
        botao.title =
            'Analisar decisão e preparar alvarás';

        Object.assign(botao.style, {
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            minWidth: '86px',
            height: '36px',
            margin: '0',
            padding: '7px 14px',
            border: '1px solid #166534',
            borderRadius: '5px',
            background: '#16a34a',
            color: '#ffffff',
            cursor: 'pointer',
            fontFamily: 'Arial, sans-serif',
            fontWeight: 'bold',
            fontSize: '13px',
            lineHeight: '1',
            boxSizing: 'border-box',
            position: 'relative',
            zIndex: '2147483647'
        });

        botao.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            analisarDecisao();
        });

        const candidatos = [
            '.mat-toolbar',
            'mat-toolbar',
            '.cabecalho',
            '.toolbar',
            '[role="toolbar"]',
            '.header',
            'header'
        ];

        for (const seletor of candidatos) {
            const destino = document.querySelector(seletor);

            if (!destino) {
                continue;
            }

            destino.appendChild(botao);

            logDiagnostico(
                'botão injetado no elemento:',
                seletor
            );

            return true;
        }

        const host = document.createElement('div');

        host.id = BUTTON_HOST_ID;

        Object.assign(host.style, {
            position: 'fixed',
            top: '12px',
            right: '18px',
            zIndex: '2147483647',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0',
            margin: '0',
            pointerEvents: 'auto'
        });

        host.appendChild(botao);
        document.body.appendChild(host);

        logDiagnostico(
            'nenhuma toolbar encontrada; botão injetado em host fixo.'
        );

        return true;
    }

    function removerElementosDaPagina() {
        document.getElementById(BUTTON_ID)?.remove();
        document.getElementById(BUTTON_HOST_ID)?.remove();
        document.getElementById(OVERLAY_ID)?.remove();
    }

    function iniciar() {
        if (window.top !== window.self) {
            logDiagnostico(
                'execução em iframe; instância mantida para diagnóstico:',
                location.href
            );
        }

        const iniciarQuandoPossivel = () => {
            if (!document.body) {
                setTimeout(iniciarQuandoPossivel, 250);
                return;
            }

            if (isPaginaDetalhe()) {
                criarBotao();
            } else {
                logDiagnostico(
                    'aguardando rota de detalhe:',
                    location.pathname
                );
            }
        };

        iniciarQuandoPossivel();

        const observer = new MutationObserver(() => {
            if (!document.body) {
                return;
            }

            if (isPaginaDetalhe()) {
                criarBotao();
            } else {
                const host =
                    document.getElementById(BUTTON_HOST_ID);

                if (host) {
                    removerElementosDaPagina();
                }
            }
        });

        const iniciarObserver = () => {
            if (!document.documentElement) {
                setTimeout(iniciarObserver, 250);
                return;
            }

            observer.observe(document.documentElement, {
                childList: true,
                subtree: true
            });

            logDiagnostico(
                'MutationObserver ativo.',
                'pathname:',
                location.pathname,
                'hash:',
                location.hash
            );
        };

        iniciarObserver();

        let ultimaUrl =
            location.href;

        setInterval(() => {
            if (location.href === ultimaUrl) {
                return;
            }

            ultimaUrl = location.href;

            logDiagnostico(
                'mudança de URL detectada:',
                location.href
            );

            if (isPaginaDetalhe()) {
                criarBotao();
            } else {
                removerElementosDaPagina();
            }
        }, 500);
    }

    iniciar();


    window.PjeAlvara = {
        abrir: analisarDecisao,
        extrairValores: Alv.extracao.extrairValores,
        salvarEstado: Alv.estado.salvarEstado,
        carregarEstado: Alv.estado.carregarEstado,
        criarItemManual: Alv.estado.criarItemManual,
        criarEstado: Alv.estado.criarEstado,
        obterProcessoId: Alv.dados.obterProcessoId,
        isPaginaDetalhe: isPaginaDetalhe,
        criarBotao: criarBotao,
        obterTextoDecisao: Alv.extracao.obterTextoDecisao,
        extrairDocumentoAtualLocal: Alv.extracao.extrairDocumentoAtualLocal,
        obterTextoDocumentoAtual: Alv.extracao.obterTextoDocumentoAtual,
        buscarDadosProcesso: Alv.dados.buscarDadosProcesso,
        minuta: Alv.minuta,
        siscon: Alv.siscon,
        siscondj: Alv.siscondj
    };

    window.PjeAlvara.extrairReferenciaDeposito = Alv.extracao.extrairReferenciaDeposito;
    window.PjeAlvara.REGEX = Alv.extracao.REGEX;
})();
