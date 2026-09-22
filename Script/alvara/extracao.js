// Script/alvara/extracao.js - REGEX da decisao, extrairValores e extrator de documento.
// Extrator primario continua sendo Script/core/extrair.js (window.pjeExtrair via @require);
// este modulo tambÃ©m traz o fallback local (HTML/iframe/embed/selecao).
(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});
    const utils = Alv.utils;
    const logDiagnostico = Alv.log.diag;
    const logAviso = Alv.log.aviso;
    const REGEX = {
        depositoCreditoSemValor: [
            // aceita ao/à/para o/para a/em favor do/da e masculino+féminino
            // ("libere-se à autora", "libere-se ao exequente", "em favor da exequenta")
            /(?:ante\s+o\s+)?dep[oó]sito\s+efetuado[\s\S]{0,500}?(?:libere-se|liber[eê]-se)\s+(?:ao|à|para\s+(?:o|a)|em\s+favor\s+(?:do|da))\s+(?:exequente|exequenta|reclamante|autora?|demandante)/i,
            /(?:libere-se|liber[eê]-se)\s+(?:ao|à|para\s+(?:o|a)|em\s+favor\s+(?:do|da))\s+(?:exequente|exequenta|reclamante|autora?|demandante)[\s\S]{0,180}?cr[eé]dito/i
        ],

        credito: [
            /crédito\s+do\s+(?:autor|reclamante|exequente|demandante)[\s\S]{0,100}?R\$\s*([\d.,]+)/i,
            /crédito[\s\S]{0,100}?R\$\s*([\d.,]+)/i
        ],

        devolucaoReclamada: [
            /(?:devolu[cç][aã]o|devolva-se|restitui[cç][aã]o|libera[cç][aã]o)[\s\S]{0,180}?(?:à|a|para a)\s+reclamada/i,
            /dep[oó]sito\s+recursal[\s\S]{0,220}?(?:devolu[cç][aã]o|devolva-se|restitui[cç][aã]o)[\s\S]{0,180}?reclamada/i,
            /(?:devolu[cç][aã]o|devolva-se|restitui[cç][aã]o)[\s\S]{0,180}?dep[oó]sito\s+recursal/i
        ],

        transferenciaOutroProcesso: [
            /transfer[eê]ncia[\s\S]{0,180}?(?:outro\s+processo|processo\s+de\s+destino)/i,
            /transfira-se[\s\S]{0,180}?(?:outro\s+processo|processo\s+de\s+destino)/i,
            /(?:novo\s+dep[oó]sito|dep[oó]sito)[\s\S]{0,180}?(?:em|para)\s+outro\s+processo/i,
            /transfira-se[\s\S]{0,180}?para\s+os\s+autos/i
        ],

        inssReclamante: [
            /\(cota\s+do\s+reclamante\)[\s\S]{0,120}?R\$\s*([\d.,]+)/i,
            /inss[\s\S]{0,120}?reclamante[\s\S]{0,120}?R\$\s*([\d.,]+)/i
        ],

        inssReclamada: [
            /cota[\s-]*parte\s+no\s+INSS[\s\S]{0,120}?R\$\s*([\d.,]+)/i,
            /inss[\s\S]{0,120}?reclamada[\s\S]{0,120}?R\$\s*([\d.,]+)/i
        ],

        custas: [
            /custas\s+de\s*(?:\|\s*)?R\$\s*([\d.,]+)/i,
            /custas[\s\S]{0,100}?R\$\s*([\d.,]+)/i
        ],

        honorariosAdvogado: [
            /honorários\s+advocatícios[\s\S]{0,150}?R\$\s*([\d.,]+)/i,
            /honorários\s+sucumbenciais[\s\S]{0,150}?R\$\s*([\d.,]+)/i
        ],

        honorariosPericiais: [
            /honorários\s+periciais[\s\S]{0,180}?R\$\s*([\d.,]+)/gi,
            /honorários\s+(?:periciais\s+)?técnicos[\s\S]{0,120}?R\$\s*([\d.,]+)/gi,
            /honorários\s+médicos[\s\S]{0,120}?R\$\s*([\d.,]+)/gi,
            /honorários\s+(?:periciais\s+)?contábeis[\s\S]{0,120}?R\$\s*([\d.,]+)/gi
        ],

        peritoNome: [
            /honorários\s+periciais[\s\S]{0,240}?(?:em favor de|para o perito|para a perita|para)\s+([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+(?:de|da|do|das|dos|[A-ZÀ-ÿ][a-zà-ÿ]+)){1,5})/i,
            /(?:perito|perita|perícia)[\s\S]{0,160}?nome\s*:?\s*([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+){1,5})/i
        ]
    };

    function firstMatch(text, patterns) {
        for (const pattern of patterns) {
            const match = text.match(pattern);
            if (match && match[1]) {
                return match[1].trim();
            }
        }

        return null;
    }

    function allMatches(text, patterns) {
        const result = [];

        for (const pattern of patterns) {
            const regex = new RegExp(pattern.source, pattern.flags);

            let match;
            while ((match = regex.exec(text)) !== null) {
                if (match[1]) {
                    result.push(match[1].trim());
                }

                if (!regex.global) break;
            }
        }

        return result;
    }

    function extrairReferenciaDeposito(texto) {
        const match = texto.match(
            /dep[oó]sito\s+efetuado[\s\S]{0,120}?#\s*id\s*:\s*\[?\s*(\w+)\s*\]?/i
        );

        if (!match) {
            return {
                detectado: false,
                id: '',
                banco: ''
            };
        }

        // O match original termina no próprio id, então o trecho para buscar o
        // banco precisa se estender além dele (o " - BB" vem depois do id).
        const trecho = texto.slice(
            match.index,
            match.index + match[0].length + 60
        );

        const bancoMatch = trecho.match(
            /#\s*id\s*:\s*\w+\s*-\s*([A-Za-zÀ-ÿ0-9]+(?:[ ._-][A-Za-zÀ-ÿ0-9]+)*)/i
        );

        return {
            detectado: true,
            id: match[1] || '',
            banco: bancoMatch
                ? bancoMatch[1].trim()
                : ''
        };
    }

    function detectarPrimeiroPadrao(texto, patterns) {
        return patterns.some(pattern => {
            pattern.lastIndex = 0;
            return pattern.test(texto);
        });
    }

    function extrairValorGenerico(texto, limite = 220) {
        const match = texto.match(
            new RegExp(
                'R\\$\\s*([\\d.,]+)[\\s\\S]{0,' +
                limite +
                '}',
                'i'
            )
        );

        return match && match[1]
            ? match[1].trim()
            : '';
    }

    function extrairIdDepositoRelacionado(texto) {
        const deposito = extrairReferenciaDeposito(texto);

        if (deposito && deposito.detectado) {
            return deposito;
        }

        const match = texto.match(
            /(?:dep[oó]sito|guia|parcela|extrato)[\s\S]{0,100}?#\s*id\s*:\s*\[?\s*(\w+)\s*\]?/i
        );

        if (!match) {
            return {
                detectado: false,
                id: '',
                banco: ''
            };
        }

        const trecho = texto.slice(
            match.index,
            match.index + match[0].length + 60
        );

        const bancoMatch = trecho.match(
            /#\s*id\s*:\s*\w+\s*-\s*([A-Za-zÀ-ÿ0-9]+(?:[ ._-][A-Za-zÀ-ÿ0-9]+)*)/i
        );

        return {
            detectado: true,
            id: match[1] || '',
            banco: bancoMatch
                ? bancoMatch[1].trim()
                : ''
        };
    }

    function extrairProcessoDestino(texto) {
        const match = texto.match(
            /(?:processo\s+de\s+destino|outro\s+processo|para\s+os\s+autos)[\s\S]{0,100}?(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/i
        );

        return match && match[1]
            ? match[1]
            : '';
    }
    function extrairValores(textoBruto) {
        const texto = utils.normalizeText(textoBruto);

        const credito = firstMatch(texto, REGEX.credito);

        const creditoPorDepositoSemValor =
            REGEX.depositoCreditoSemValor.some(pattern => {
                pattern.lastIndex = 0;
                return pattern.test(texto);
            });

        // Extrator estendido: cobre "depósito efetuado", "extrato de", guias e parcelas.
        const depositoCredito = extrairIdDepositoRelacionado(texto);

        const devolucaoReclamada = detectarPrimeiroPadrao(
            texto,
            REGEX.devolucaoReclamada
        );

        const transferenciaOutroProcesso = detectarPrimeiroPadrao(
            texto,
            REGEX.transferenciaOutroProcesso
        );

        const inssReclamante = firstMatch(
            texto,
            REGEX.inssReclamante
        );

        const inssReclamada = firstMatch(
            texto,
            REGEX.inssReclamada
        );

        const inssTotal = (
            utils.parseMoney(inssReclamante) +
            utils.parseMoney(inssReclamada)
        );

        const custas = firstMatch(texto, REGEX.custas);

        const honorariosAdvogado = firstMatch(
            texto,
            REGEX.honorariosAdvogado
        );

        const honorariosPericiaisValores = allMatches(
            texto,
            REGEX.honorariosPericiais
        );

        const honorariosPericiaisTotal =
            honorariosPericiaisValores.reduce(
                (total, valor) => total + utils.parseMoney(valor),
                0
            );

        const depositoRelacionado = extrairIdDepositoRelacionado(texto);

        const valorDevolucao = devolucaoReclamada
            ? (
                firstMatch(texto, REGEX.credito) ||
                extrairValorGenerico(texto)
            )
            : '';

        const valorTransferencia = transferenciaOutroProcesso
            ? extrairValorGenerico(texto)
            : '';

        return {
            credito: credito
                ? utils.formatMoney(credito)
                : '',

            creditoPorDepositoSemValor,

            creditoOrigem: creditoPorDepositoSemValor
                ? 'Depósito identificado sem valor monetário'
                : credito
                    ? 'Valor monetário identificado na decisão'
                    : '',

            deposito: depositoCredito,

            devolucaoReclamada,

            devolucaoReclamadaValor: valorDevolucao
                ? utils.formatMoney(valorDevolucao)
                : '',

            devolucaoReclamadaDeposito: devolucaoReclamada
                ? depositoRelacionado
                : {
                    detectado: false,
                    id: '',
                    banco: ''
                },

            transferenciaOutroProcesso,

            transferenciaOutroProcessoValor: valorTransferencia
                ? utils.formatMoney(valorTransferencia)
                : '',

            transferenciaOutroProcessoDeposito:
                transferenciaOutroProcesso
                    ? depositoRelacionado
                    : {
                        detectado: false,
                        id: '',
                        banco: ''
                    },

            transferenciaProcessoDestino:
                transferenciaOutroProcesso
                    ? extrairProcessoDestino(texto)
                    : '',

            inss: inssTotal > 0
                ? utils.formatMoney(inssTotal)
                : '',

            custas: custas
                ? utils.formatMoney(custas)
                : '',

            honorariosAdvocaticios: honorariosAdvogado
                ? utils.formatMoney(honorariosAdvogado)
                : '',

            honorariosPericiais: honorariosPericiaisTotal > 0
                ? utils.formatMoney(honorariosPericiaisTotal)
                : '',

            peritoNome: (function () {
                const nome = firstMatch(texto, REGEX.peritoNome) || '';

                // Remove preposições/conectivos arrastados pelo regex
                // ("Maria Contadora em" -> "Maria Contadora").
                const limpo = nome
                    .replace(/\s+(?:em|para|de|do|da|dos|das|a|o|e)$/i, '')
                    .trim();

                return limpo;
            })(),

            creditoParcialDeposito:
                /parte\s+de\s+(?:seu|meu)\s+cr[eé]dito/i.test(texto),

            detalhes: {
                inssReclamante: inssReclamante || '',
                inssReclamada: inssReclamada || '',
                honorariosPericiais: honorariosPericiaisValores
            }
        };
    }
    function limparTextoExtraido(texto) {
        return String(texto || '')
            .replace(/\u00a0/g, ' ')
            .replace(/\r/g, '\n')
            .replace(/[ \t]+/g, ' ')
            .replace(/\n{3,}/g, '\n\n')
            .trim();
    }

    function textoVisivelDoElemento(elemento) {
        if (!elemento) {
            return '';
        }

        return limparTextoExtraido(
            elemento.innerText ||
            elemento.textContent ||
            ''
        );
    }

    function textoDeDocumentoHtml() {
        const seletores = [
            'mat-card.container-html',
            '.visualizador-html',
            '.conteudo-html',
            '.documento-html',
            '[class*="container-html"]',
            '[class*="visualizador-html"]',
            '[class*="documento-html"]'
        ];

        for (const seletor of seletores) {
            const elemento =
                document.querySelector(seletor);

            const texto =
                textoVisivelDoElemento(elemento);

            if (texto.length > 40) {
                return texto;
            }
        }

        const candidatos = Array.from(
            document.querySelectorAll(
                'main, article, mat-card, section, div'
            )
        );

        const textos = candidatos
            .map(textoVisivelDoElemento)
            .filter(texto => texto.length > 40)
            .sort((a, b) => b.length - a.length);

        return textos[0] || '';
    }

    function textoDeIframeHtml() {
        const iframes = Array.from(
            document.querySelectorAll('iframe')
        );

        for (const iframe of iframes) {
            try {
                const doc =
                    iframe.contentDocument ||
                    iframe.contentWindow?.document;

                if (!doc) {
                    continue;
                }

                const texto = limparTextoExtraido(
                    doc.body?.innerText ||
                    doc.body?.textContent ||
                    ''
                );

                if (texto.length > 40) {
                    return texto;
                }
            } catch (error) {
                logDiagnostico(
                    'iframe inacessível por política do navegador:',
                    error.message
                );
            }
        }

        return '';
    }

    function textoDeObjectPdf() {
        const objetos = Array.from(
            document.querySelectorAll(
                'object.conteudo-pdf, object[type="application/pdf"], object'
            )
        );

        for (const objeto of objetos) {
            const textoFallback =
                textoVisivelDoElemento(objeto);

            if (textoFallback.length > 40) {
                return textoFallback;
            }
        }

        return '';
    }

    function textoDeEmbedPdf() {
        const embeds = Array.from(
            document.querySelectorAll(
                'embed[type="application/pdf"], embed'
            )
        );

        for (const embed of embeds) {
            const textoFallback =
                textoVisivelDoElemento(embed);

            if (textoFallback.length > 40) {
                return textoFallback;
            }
        }

        return '';
    }

    function textoDeSelecaoAtual() {
        const selecao =
            window.getSelection?.()?.toString() || '';

        return limparTextoExtraido(selecao);
    }

    function obterTextoDocumentoAtual() {
        const fontes = [
            {
                nome: 'HTML do visualizador',
                obter: textoDeDocumentoHtml
            },
            {
                nome: 'iframe do visualizador',
                obter: textoDeIframeHtml
            },
            {
                nome: 'fallback do object PDF',
                obter: textoDeObjectPdf
            },
            {
                nome: 'fallback do embed PDF',
                obter: textoDeEmbedPdf
            },
            {
                nome: 'seleção atual',
                obter: textoDeSelecaoAtual
            }
        ];

        for (const fonte of fontes) {
            try {
                const texto = limparTextoExtraido(
                    fonte.obter()
                );

                if (texto.length > 40) {
                    logDiagnostico(
                        'texto extraído por:',
                        fonte.nome,
                        'caracteres:',
                        texto.length
                    );

                    return texto;
                }
            } catch (error) {
                logAviso(
                    'falha na fonte de extração:',
                    fonte.nome,
                    error.message
                );
            }
        }

        return '';
    }

    async function aguardarTextoDocumentoAtual(
        timeout = 10000
    ) {
        const inicio = Date.now();

        while (Date.now() - inicio < timeout) {
            const texto =
                obterTextoDocumentoAtual();

            if (texto.length > 40) {
                return texto;
            }

            await new Promise(resolve => {
                setTimeout(resolve, 300);
            });
        }

        return '';
    }

    async function extrairDocumentoAtualLocal() {
        try {
            const texto =
                await aguardarTextoDocumentoAtual(10000);

            if (!texto) {
                return {
                    sucesso: false,
                    erro:
                        'Nenhum texto foi localizado no documento atual. ' +
                        'Abra a decisão/minuta na timeline e aguarde o ' +
                        'conteúdo aparecer antes de clicar em Alvará.'
                };
            }

            return {
                sucesso: true,
                conteudo_bruto: texto,
                conteudo: texto,
                origem: 'extrator incorporado'
            };
        } catch (error) {
            console.error(
                '[PjeAlvara] erro no extrator incorporado:',
                error
            );

            return {
                sucesso: false,
                erro: error.message ||
                    'Erro desconhecido no extrator incorporado.'
            };
        }
    }

    async function obterTextoDecisao() {
        // Preferência 1: extrator canônico do projeto (Script/core/extrair.js,
        // carregado via @require OU pelo loader.js do pjetools) — suporta PDF
        // via pdf.js e API (window.pjeExtrair / window.pjeExtrairApi).
        const extractor =
            window.pjeExtrair ||
            window.PjeExtrair;

        if (typeof extractor === 'function') {
            logDiagnostico(
                'usando extrator externo:',
                extractor.name || 'função anônima'
            );

            let resultado;

            try {
                resultado = await extractor();
            } catch (error) {
                throw new Error(
                    'Erro ao chamar o extrator externo: ' +
                    error.message
                );
            }

            if (!resultado || resultado.sucesso === false) {
                throw new Error(
                    resultado?.erro ||
                    'O extrator externo não retornou conteúdo.'
                );
            }

            return resultado.conteudo_bruto ||
                resultado.conteudo ||
                '';
        }

        logDiagnostico(
            'window.pjeExtrair não disponível; usando extrator incorporado.'
        );

        const resultadoLocal =
            await extrairDocumentoAtualLocal();

        if (!resultadoLocal.sucesso) {
            throw new Error(
                resultadoLocal.erro ||
                'Não foi possível extrair o texto da decisão.'
            );
        }

        return resultadoLocal.conteudo_bruto ||
            resultadoLocal.conteudo ||
            '';
    }

    // ═══════════════════════════════════════════════════════════
    // DADOS DO PROCESSO VIA API (mesma lógica do hcalc-prep.js)
    // pje-comum-api: /partes → polos + advogados (representantes)
    // ═══════════════════════════════════════════════════════════

    Alv.extracao = {
        REGEX: REGEX,
        extrairValores: extrairValores,
        obterTextoDecisao: obterTextoDecisao,
        extrairDocumentoAtualLocal: extrairDocumentoAtualLocal,
        obterTextoDocumentoAtual: obterTextoDocumentoAtual,
        extrairReferenciaDeposito: extrairReferenciaDeposito,
        extrairProcessoDestino: extrairProcessoDestino
    };
})();
