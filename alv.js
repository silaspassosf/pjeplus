// ==UserScript==
// @name         PJeTools — Elaboração de Alvará
// @namespace    pjetools
// @version      0.4.2
// @description  Analisa decisão ativa e prepara dados para elaboração de alvarás
// @author       PJeTools
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe
// @match        https://pje.trt2.jus.br/pjekz/processo/*/detalhe#*
// @match        https://pje.trt*.jus.br/pjekz/processo/*/detalhe
// @match        https://pje.trt*.jus.br/pjekz/processo/*/detalhe#*
// @grant        none
// @run-at       document-start
// @require      https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/core/extrair.js
// ==/UserScript==

(function () {
    'use strict';

    const INSTANCE_KEY =
        '__PJE_ALVARA_USERSCRIPT_INSTANCE__';

    const INSTANCE_VERSION = '0.4.2';

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

    const STORAGE_KEY = 'pje_elaboracao_alvara_v1';
    const BUTTON_ID = 'pje-btn-alvara';
    const BUTTON_HOST_ID = 'pje-alvara-button-host';
    const OVERLAY_ID = 'pje-alvara-overlay';

    function isPaginaDetalhe() {
        return /^\/pjekz\/processo\/\d+\/detalhe(?:\/.*)?$/i
            .test(location.pathname);
    }

    // Desativado temporariamente: por enquanto so os logs de extracao ficam ativos.
    function logDiagnostico() { }

    function logAviso(...args) {
        console.warn('[PjeAlvara]', ...args);
    }

    const utils = {
        sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        parseMoney(value) {
            if (value === null || value === undefined) return 0;

            let text = String(value)
                .replace(/R\$\s*/gi, '')
                .replace(/\s/g, '')
                .trim();

            if (!text) return 0;

            text = text.replace(/\./g, '').replace(',', '.');

            const number = parseFloat(text);
            return Number.isFinite(number) ? number : 0;
        },

        formatMoney(value) {
            const number = typeof value === 'number'
                ? value
                : utils.parseMoney(value);

            return number.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        },

        moneyWithSymbol(value) {
            return `R$ ${utils.formatMoney(value)}`;
        },

        normalizeText(text) {
            return String(text || '')
                .replace(/\u00a0/g, ' ')
                .replace(/\s{2,}/g, ' ')
                .trim();
        },

        escapeHtml(value) {
            return String(value ?? '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }
    };

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

    function criarIdItem(prefixo) {
        return `${prefixo}-${Date.now()}-${Math.random()
            .toString(36)
            .slice(2, 8)}`;
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

    function obterProcessoId() {
        const match = window.location.pathname.match(
            /\/processo\/(\d+)\/detalhe(?:\/|$)/i
        );

        return match ? match[1] : '';
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

    function _xsrfToken() {
        const cookie = document.cookie
            .split(';')
            .map(s => s.trim())
            .find(s => s.toLowerCase().startsWith('xsrf-token='));

        return cookie
            ? decodeURIComponent(cookie.split('=').slice(1).join('='))
            : '';
    }

    function _apiHeaders(accept) {
        const h = {
            'Accept': accept || 'application/json',
            'Content-Type': 'application/json',
            'X-Grau-Instancia': '1'
        };

        const x = _xsrfToken();
        if (x) h['X-XSRF-TOKEN'] = x;

        return h;
    }

    function _apiIdProcesso() {
        const m = window.location.pathname.match(/\/processo\/(\d+)/) ||
            window.location.search.match(/processo=(\d+)/i);

        return m ? m[1] : null;
    }

    function _apiBase() {
        return location.origin + '/pje-comum-api/api/processos/id/' + _apiIdProcesso();
    }

    async function _apiGet(url) {
        const resp = await fetch(url, {
            method: 'GET',
            credentials: 'include',
            headers: _apiHeaders()
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);

        const txt = await resp.text();

        try { return JSON.parse(txt); } catch (_) { return txt; }
    }

    function _shapePartes(dados) {
        const flatten = (partes, tipo) => (partes || []).map((p, idx) => ({
            nome: (p.nome || '').trim(),
            cpfcnpj: p.documento || '',
            tipo,
            ordem: `${idx + 1}ª`,
            representantes: (p.representantes || []).map(r => ({
                nome: (r.nome || '').trim(),
                oab: r.numeroOab || '',
                cpfcnpj: r.documento || r.cpfCnpj || '',
                tipo: r.tipo || ''
            }))
        }));

        return {
            ativo: flatten(dados.ATIVO, 'AUTOR'),
            passivo: flatten(dados.PASSIVO, 'REU'),
            outros: flatten(dados.TERCEIROS, 'TERCEIRO')
        };
    }

    let _dadosProcessoCache = null;

    async function buscarDadosProcesso() {
        // Sempre consulta a API (dados sempre corretos) e devolve
        // { processoId, numero, partes: { ativo, passivo, outros }, consultadoEm }.
        const id = _apiIdProcesso();

        if (!id) {
            logAviso('sem id de processo na URL; dados do processo indisponíveis.');
            return null;
        }

        let numero = null;
        let partes = { ativo: [], passivo: [], outros: [] };

        try {
            const meta = await _apiGet(_apiBase());
            numero = (meta && (meta.numeroProcesso || meta.numero)) || null;
        } catch (error) {
            logAviso('metadados do processo indisponíveis:', error.message);
        }

        try {
            const raw = await _apiGet(_apiBase() + '/partes');
            partes = _shapePartes(raw);
        } catch (error) {
            logAviso('partes do processo indisponíveis:', error.message);
        }

        let peritos = [];

        try {
            const rawPeritos = await _apiGet(_apiBase() + '/peritos');
            peritos = _shapePeritos(rawPeritos, partes);
        } catch (error) {
            logAviso('peritos do processo indisponíveis via endpoint; tentando partes:', error.message);
        }

        if (!peritos.length) {
            peritos = _shapePeritos(null, partes);
        }

        _dadosProcessoCache = {
            processoId: id,
            numero,
            partes,
            peritos,
            consultadoEm: new Date().toISOString()
        };

        return _dadosProcessoCache;
    }

    // Peritos: aceita array de strings, objetos {nome|pessoa.nome, documento}
    // ou fallback nos TERCEIROS marcados como perito na resposta de /partes.
    function _shapePeritos(raw, partes) {
        const nomes = [];

        if (Array.isArray(raw)) {
            for (const p of raw) {
                if (typeof p === 'string') {
                    nomes.push({ nome: p.trim(), cpfcnpj: '' });
                    continue;
                }

                const nome = (p && (p.nome || (p.pessoa && p.pessoa.nome)) || '').trim();
                const doc = (p && (p.documento || (p.pessoa && p.pessoa.documento)) || '').trim();

                if (nome) {
                    nomes.push({ nome, cpfcnpj: doc });
                }
            }
        }

        if (!nomes.length && partes) {
            for (const p of (partes.outros || [])) {
                const tipo = (p.tipo || '').toLowerCase();
                const nomeParte = (p.nome || '').toLowerCase();

                if (tipo.includes('perito') || nomeParte.includes('perito')) {
                    nomes.push({ nome: p.nome, cpfcnpj: p.cpfcnpj || '' });
                }
            }
        }

        return nomes;
    }

    function primeiraPerito(dados) {
        if (!dados || !Array.isArray(dados.peritos)) return null;

        return dados.peritos[0] || null;
    }

    function primeiraParte(dados, polo) {
        if (!dados) return null;

        const lista = polo === 'PASSIVO'
            ? dados.partes.passivo
            : dados.partes.ativo;

        return (lista && lista[0]) || null;
    }

    function primeiroAdvogado(dados, polo) {
        if (!dados) return null;

        const lista = polo === 'PASSIVO'
            ? dados.partes.passivo
            : dados.partes.ativo;

        for (const parte of (lista || [])) {
            const adv = (parte.representantes || [])[0];

            if (adv && adv.nome) {
                return { ...adv, parteNome: parte.nome };
            }
        }

        return null;
    }

    function preencherDestinatario(item, dados, polo, usarAdvogado) {
        const alvo = usarAdvogado
            ? primeiroAdvogado(dados, polo)
            : primeiraParte(dados, polo);

        if (alvo && alvo.nome) {
            item.destinatarioNome = alvo.nome;
            item.destinatarioDocumento = alvo.cpfcnpj || '';
        }

        return item;
    }

    // Regras de preenchimento automático por tipo de verba (detectada OU adicionada):
    //  - Crédito do exequente: beneficiário = polo ativo; se destino é conta do
    //    advogado/escritório → Nome e CPF do PRIMEIRO advogado do autor.
    //  - Devolução à reclamada: beneficiário = polo passivo; procurador da
    //    reclamada → primeiro advogado do passivo.
    //  - Honorários advocatícios: sempre o primeiro advogado do autor por padrão
    //    (da reclamada NUNCA é automático — só se adicionado manualmente).
    //  - Honorários periciais: se a decisão detectou a verba mas NÃO nomeou o
    //    perito, preenche com o primeiro perito dos dados da API. Se a decisão
    //    nomeou, o nome extraído prevalece. Verba não detectada nem entra no
    //    overlay (regra geral).
    function aplicarPreenchimentoAutomatico(item, dados) {
        if (!dados) return item;

        if (item.id === 'credito' || item.tipo === 'Crédito do exequente') {
            if ((item.destinoTipo || '').includes('reclamante')) {
                preencherDestinatario(item, dados, 'ATIVO', false);
            } else {
                preencherDestinatario(item, dados, 'ATIVO', true);
            }
        }

        if (item.id === 'devolucao-reclamada' || item.tipo === 'Devolução à reclamada') {
            if ((item.destinoTipo || '').includes('procurador')) {
                preencherDestinatario(item, dados, 'PASSIVO', true);
            } else {
                preencherDestinatario(item, dados, 'PASSIVO', false);
            }
        }

        if (item.id === 'honorarios-advocaticios' || item.tipo === 'Honorários advocatícios') {
            preencherDestinatario(item, dados, 'ATIVO', true);
        }

        if (item.id === 'honorarios-periciais' || item.tipo === 'Honorários periciais') {
            if (!item.perito) {
                const perito = primeiraPerito(dados);

                if (perito && perito.nome) {
                    item.perito = perito.nome;
                }
            }
        }

        return item;
    }

    function valorInicial(valor) {
        return valor ? `R$ ${valor}` : 'R$ 0,00';
    }

    function criarItemDevolucaoReclamada(valores) {
        return {
            id: criarIdItem('devolucao-reclamada'),
            tipo: 'Devolução à reclamada',
            origem: 'extraído da decisão',
            valor: valorInicial(valores.devolucaoReclamadaValor),
            valorPendente: !valores.devolucaoReclamadaValor &&
                Boolean(valores.devolucaoReclamadaDeposito?.id),
            destinoTipo: 'Conta da reclamada',
            destinatarioNome: '',
            destinatarioDocumento: '',
            deposito: valores.devolucaoReclamadaDeposito || {
                detectado: false,
                id: '',
                banco: '',
                valor: '',
                pendenteConsulta: false
            },
            dados: {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            },
            siscon: true
        };
    }

    function criarItemTransferenciaOutroProcesso(valores) {
        return {
            id: criarIdItem('transferencia-outro-processo'),
            tipo: 'Transferência para outro processo',
            origem: 'extraído da decisão',
            valor: valorInicial(
                valores.transferenciaOutroProcessoValor
            ),
            valorPendente: !valores.transferenciaOutroProcessoValor &&
                Boolean(valores.transferenciaOutroProcessoDeposito?.id),
            destinoTipo: 'Novo depósito em outro processo',
            destinatarioNome: '',
            destinatarioDocumento: '',
            deposito: valores.transferenciaOutroProcessoDeposito || {
                detectado: false,
                id: '',
                banco: '',
                valor: '',
                pendenteConsulta: false
            },
            transferencia: {
                processoDestino:
                    valores.transferenciaProcessoDestino || '',
                tribunalDestino: '',
                unidadeDestino: ''
            },
            dados: null,
            siscon: true
        };
    }

    function criarItemManual(tipo) {
        const base = {
            id: criarIdItem('manual'),
            tipo,
            origem: 'adicionado manualmente',
            valor: 'R$ 0,00',
            valorPendente: false,
            destinoTipo: '',
            destinatarioNome: '',
            destinatarioDocumento: '',
            deposito: null,
            dados: null,
            siscon: true
        };

        if (tipo === 'Crédito do exequente') {
            base.destinoTipo =
                'Transferência para conta do advogado';

            base.dados = {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            };
        }

        if (tipo === 'INSS') {
            base.destinoTipo = 'DARF';
            base.siscon = false;
        }

        if (tipo === 'Custas') {
            base.destinoTipo = 'GRU';
            base.siscon = false;
        }

        if (tipo === 'Honorários advocatícios') {
            base.destinoTipo = 'Conta do advogado autor';
            base.dados = {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            };
        }

        if (tipo === 'Honorários periciais') {
            base.destinoTipo = 'Conta do perito';
            base.perito = '';
            base.dados = {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            };
        }

        if (tipo === 'Devolução à reclamada') {
            base.destinoTipo = 'Conta da reclamada';
            base.dados = {
                banco: '',
                agencia: '',
                conta: '',
                tipoConta: ''
            };
            base.deposito = {
                detectado: false,
                id: '',
                banco: '',
                valor: '',
                pendenteConsulta: false
            };
        }

        if (tipo === 'Transferência para outro processo') {
            base.destinoTipo =
                'Novo depósito em outro processo';

            base.dados = null;

            base.transferencia = {
                processoDestino: '',
                tribunalDestino: '',
                unidadeDestino: ''
            };

            base.deposito = {
                detectado: false,
                id: '',
                banco: '',
                valor: '',
                pendenteConsulta: false
            };
        }

        // Mesmas regras de preenchimento das verbas detectadas — usa o
        // cache dos dados do processo da última chamada de API.
        return aplicarPreenchimentoAutomatico(base, _dadosProcessoCache);
    }

    function criarEstado(valores, dadosProcesso) {
        // Só cria campos para os tipos DETECTADOS na decisão.
        // Tipos adicionais entram manualmente pelo botão "Adicionar Verba".
        // dadosProcesso (API /partes) alimenta Nome/CPF de beneficiários e
        // advogados conforme o tipo de verba.
        const itens = [];

        if (valores.credito || valores.creditoPorDepositoSemValor) {
            itens.push(aplicarPreenchimentoAutomatico({
                id: 'credito',
                tipo: 'Crédito do exequente',
                // "pagamento de parte de seu credito" -> valor depende do
                // deposito integral atualizado: texto fixo, NAO editavel.
                valor: valores.creditoParcialDeposito
                    ? 'Depósito integral atualizado'
                    : valorInicial(valores.credito),
                valorFixo: valores.creditoParcialDeposito === true,
                valorPendente: !valores.credito &&
                    valores.creditoPorDepositoSemValor === true &&
                    valores.creditoParcialDeposito !== true,
                origem: valores.creditoOrigem || '',
                deposito: valores.deposito || {
                    detectado: false,
                    id: '',
                    banco: ''
                },
                destinoTipo: 'Transferência para conta do advogado',
                destinatarioNome: '',
                destinatarioDocumento: '',
                dados: {
                    banco: '',
                    agencia: '',
                    conta: '',
                    tipoConta: ''
                },
                siscon: true
            }, dadosProcesso));
        }

        if (valores.inss) {
            itens.push({
                id: 'inss',
                tipo: 'Contribuições previdenciárias — INSS',
                valor: valorInicial(valores.inss),
                destinoTipo: 'DARF',
                dados: null,
                siscon: false
            });
        }

        if (valores.custas) {
            itens.push({
                id: 'custas',
                tipo: 'Custas',
                valor: valorInicial(valores.custas),
                destinoTipo: 'GRU',
                dados: null,
                siscon: false
            });
        }

        if (valores.honorariosAdvocaticios) {
            itens.push(aplicarPreenchimentoAutomatico({
                id: 'honorarios-advocaticios',
                tipo: 'Honorários advocatícios',
                valor: valorInicial(valores.honorariosAdvocaticios),
                destinoTipo: 'Conta do advogado autor',
                destinatarioNome: '',
                destinatarioDocumento: '',
                dados: {
                    banco: '',
                    agencia: '',
                    conta: '',
                    tipoConta: ''
                },
                siscon: true
            }, dadosProcesso));
        }

        if (valores.honorariosPericiais) {
            itens.push(aplicarPreenchimentoAutomatico({
                id: 'honorarios-periciais',
                tipo: 'Honorários periciais',
                valor: valorInicial(valores.honorariosPericiais),
                destinoTipo: 'Conta do perito',
                perito: valores.peritoNome || '',
                dados: {
                    banco: '',
                    agencia: '',
                    conta: '',
                    tipoConta: ''
                },
                siscon: false
            }, dadosProcesso));
        }

        if (valores.devolucaoReclamada) {
            itens.push(aplicarPreenchimentoAutomatico(
                criarItemDevolucaoReclamada(valores),
                dadosProcesso
            ));
        }

        if (valores.transferenciaOutroProcesso) {
            itens.push(criarItemTransferenciaOutroProcesso(valores));
        }

        return {
            versao: 1,
            processoId: (dadosProcesso && dadosProcesso.processoId) || obterProcessoId(),
            processo: dadosProcesso ? {
                numero: dadosProcesso.numero || '',
                partes: dadosProcesso.partes,
                peritos: dadosProcesso.peritos,
                consultadoEm: dadosProcesso.consultadoEm
            } : null,
            url: window.location.href,
            salvoEm: new Date().toISOString(),
            itens
        };
    }

    function salvarEstado(estado) {
        estado.salvoEm = new Date().toISOString();
        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(estado)
        );
    }

    function carregarEstado() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (error) {
            console.error('[PjeAlvara] Erro ao carregar estado:', error);
            return null;
        }
    }

    function aplicarMascaraMonetaria(input) {
        let somenteDigitos = input.value
            .replace(/\D/g, '');

        if (!somenteDigitos) {
            input.value = 'R$ 0,00';
            return;
        }

        const valor = parseInt(somenteDigitos, 10) / 100;

        input.value = utils.moneyWithSymbol(valor);
    }

    function aplicarMascaraCampos(container) {
        container.querySelectorAll(
            '[data-money-input="true"]'
        ).forEach(input => {
            input.addEventListener('focus', () => {
                input.select();
            });

            input.addEventListener('input', () => {
                aplicarMascaraMonetaria(input);
                atualizarEstadoPeloOverlay();
            });

            input.addEventListener('blur', () => {
                aplicarMascaraMonetaria(input);
                atualizarEstadoPeloOverlay();
            });
        });
    }

    function obterDadosDoCard(card) {
        const dados = {
            id: card.dataset.itemId,
            tipo: card.querySelector('[data-field="tipo"]')?.value || '',
            valor: card.querySelector('[data-field="valor"]')?.value || '',
            destinoTipo: card.querySelector('[data-field="destinoTipo"]')?.value || '',
            destinatarioNome:
                card.querySelector('[data-field="destinatarioNome"]')?.value || '',
            destinatarioDocumento:
                card.querySelector('[data-field="destinatarioDocumento"]')?.value || '',
            perito:
                card.querySelector('[data-field="perito"]')?.value || '',
            origem: card.dataset.origem || 'extraído da decisão'
        };

        const banco = card.querySelector('[data-field="banco"]');
        const agencia = card.querySelector('[data-field="agencia"]');
        const conta = card.querySelector('[data-field="conta"]');
        const tipoConta = card.querySelector('[data-field="tipoConta"]');

        if (banco || agencia || conta || tipoConta) {
            dados.dados = {
                banco: banco?.value || '',
                agencia: agencia?.value || '',
                conta: conta?.value || '',
                tipoConta: tipoConta?.value || ''
            };
        } else {
            dados.dados = null;
        }

        const depositoId = card.querySelector(
            '[data-field="depositoId"]'
        );

        const depositoBanco = card.querySelector(
            '[data-field="depositoBanco"]'
        );

        if (depositoId || depositoBanco) {
            dados.deposito = {
                detectado: Boolean(depositoId?.value),
                id: depositoId?.value || '',
                banco: depositoBanco?.value || '',
                valor: dados.valor,
                pendenteConsulta: !dados.valor ||
                    dados.valor === 'R$ 0,00'
            };
        }

        const processoDestino = card.querySelector(
            '[data-field="processoDestino"]'
        );

        const tribunalDestino = card.querySelector(
            '[data-field="tribunalDestino"]'
        );

        const unidadeDestino = card.querySelector(
            '[data-field="unidadeDestino"]'
        );

        if (processoDestino || tribunalDestino || unidadeDestino) {
            dados.transferencia = {
                processoDestino: processoDestino?.value || '',
                tribunalDestino: tribunalDestino?.value || '',
                unidadeDestino: unidadeDestino?.value || ''
            };
        }

        return dados;
    }

    function atualizarEstadoPeloOverlay() {
        const overlay = document.getElementById(OVERLAY_ID);
        if (!overlay) return;

        const estado = carregarEstado() || {
            versao: 1,
            processoId: obterProcessoId(),
            itens: []
        };

        estado.itens = Array.from(
            overlay.querySelectorAll('[data-alvara-card]')
        ).map(obterDadosDoCard).map(item => {
            if (
                item.tipo === 'Devolução à reclamada' ||
                item.id === 'devolucao-reclamada'
            ) {
                item.valorPendente =
                    !item.valor ||
                    item.valor === 'R$ 0,00';

                item.deposito = item.deposito || {
                    detectado: false,
                    id: '',
                    banco: '',
                    valor: '',
                    pendenteConsulta: false
                };
            }

            if (
                item.tipo === 'Transferência para outro processo' ||
                item.id === 'transferencia-outro-processo'
            ) {
                item.valorPendente =
                    !item.valor ||
                    item.valor === 'R$ 0,00';

                item.transferencia = item.transferencia || {
                    processoDestino: '',
                    tribunalDestino: '',
                    unidadeDestino: ''
                };
            }

            return item;
        });

        salvarEstado(estado);

        const status = overlay.querySelector(
            '[data-status-salvamento]'
        );

        if (status) {
            status.textContent =
                `Salvo para conferência às ${new Date().toLocaleTimeString('pt-BR')}`;
        }
    }

    function campoDadosHtml(item) {
        if (
            item.id === 'inss' ||
            item.id === 'custas'
        ) {
            return `
                <div class="pje-alvara-info">
                    Dados bancários não aplicáveis nesta fase.
                </div>
            `;
        }

        if (item.id === 'transferencia-outro-processo' ||
            item.tipo === 'Transferência para outro processo') {
            return `
                <label>
                    Número do processo de destino
                    <input
                        data-field="processoDestino"
                        placeholder="0000000-00.0000.0.00.0000"
                        value="${utils.escapeHtml(
                            item.transferencia?.processoDestino || ''
                        )}"
                    >
                </label>

                <label>
                    Tribunal de destino
                    <input
                        data-field="tribunalDestino"
                        placeholder="Tribunal de destino"
                        value="${utils.escapeHtml(
                            item.transferencia?.tribunalDestino || ''
                        )}"
                    >
                </label>

                <label>
                    Unidade judicial de destino
                    <input
                        data-field="unidadeDestino"
                        placeholder="Vara ou unidade de destino"
                        value="${utils.escapeHtml(
                            item.transferencia?.unidadeDestino || ''
                        )}"
                    >
                </label>

                <div class="pje-alvara-info">
                    A transferência será implementada na fase 2,
                    dentro do SISCONDJ.
                </div>
            `;
        }

        if (item.id === 'honorarios-periciais' ||
            item.tipo === 'Honorários periciais') {
            return `
                <label>
                    Perito
                    <select data-field="perito">
                        <option value="">Selecione o perito</option>
                        <option value="__PLACEHOLDER_PLANILHA__">
                            Lista de peritos — integração futura
                        </option>
                    </select>
                </label>

                <div class="pje-alvara-info">
                    Os dados do perito serão carregados futuramente
                    a partir de uma planilha.
                </div>

                <div class="pje-alvara-dados-grid">
                    <label>
                        Banco
                        <input
                            data-field="banco"
                            placeholder="Banco"
                            value="${utils.escapeHtml(
                                item.dados?.banco || ''
                            )}"
                        >
                    </label>

                    <label>
                        Agência
                        <input
                            data-field="agencia"
                            placeholder="Agência"
                            value="${utils.escapeHtml(
                                item.dados?.agencia || ''
                            )}"
                        >
                    </label>

                    <label>
                        Conta
                        <input
                            data-field="conta"
                            placeholder="Conta"
                            value="${utils.escapeHtml(
                                item.dados?.conta || ''
                            )}"
                        >
                    </label>

                    <label>
                        Tipo de conta
                        <input
                            data-field="tipoConta"
                            placeholder="Corrente ou poupança"
                            value="${utils.escapeHtml(
                                item.dados?.tipoConta || ''
                            )}"
                        >
                    </label>
                </div>
            `;
        }

        // Sequência visual do preenchimento: Nome e documento → Agência →
        // Conta → Banco. ID de depósito não é exibido (irrelevante no overlay).
        return `
            <div class="pje-alvara-dados-grid">
                <label>
                    Nome do destinatário
                    <input
                        data-field="destinatarioNome"
                        placeholder="Nome"
                        value="${utils.escapeHtml(
                            item.destinatarioNome || ''
                        )}"
                    >
                </label>

                <label>
                    CPF ou CNPJ
                    <input
                        data-field="destinatarioDocumento"
                        placeholder="CPF ou CNPJ"
                        value="${utils.escapeHtml(
                            item.destinatarioDocumento || ''
                        )}"
                    >
                </label>

                <label>
                    Agência
                    <input
                        data-field="agencia"
                        placeholder="Agência"
                        value="${utils.escapeHtml(
                            item.dados?.agencia || ''
                        )}"
                    >
                </label>

                <label>
                    Conta
                    <input
                        data-field="conta"
                        placeholder="Conta"
                        value="${utils.escapeHtml(
                            item.dados?.conta || ''
                        )}"
                    >
                </label>

                <label>
                    Banco
                    <input
                        data-field="banco"
                        placeholder="Banco"
                        value="${utils.escapeHtml(
                            item.dados?.banco || ''
                        )}"
                    >
                </label>

                <label>
                    Tipo de conta
                    <input
                        data-field="tipoConta"
                        placeholder="Corrente ou poupança"
                        value="${utils.escapeHtml(
                            item.dados?.tipoConta || ''
                        )}"
                    >
                </label>
            </div>

            <button
                type="button"
                class="pje-alvara-secondary"
                data-siscon-button
            >
                Puxar do SISCON
            </button>
        `;
    }

    function opcoesDestino(item) {
        if (
            item.id === 'credito' ||
            item.tipo === 'Crédito do exequente'
        ) {
            return `
                <option value="Transferência para conta do advogado">
                    Transferência para conta do advogado
                </option>
                <option value="Conta escritório">
                    Conta escritório
                </option>
                <option value="Conta reclamante">
                    Conta reclamante
                </option>
            `;
        }

        if (
            item.id === 'honorarios-advocaticios' ||
            item.tipo === 'Honorários advocatícios'
        ) {
            return `
                <option value="Conta do advogado autor">
                    Conta do advogado autor
                </option>
                <option value="Conta escritório">
                    Conta escritório
                </option>
            `;
        }

        if (
            item.id === 'inss' ||
            item.tipo === 'INSS' ||
            item.tipo === 'Contribuições previdenciárias — INSS'
        ) {
            return `<option value="DARF">DARF</option>`;
        }

        if (
            item.id === 'custas' ||
            item.tipo === 'Custas'
        ) {
            return `<option value="GRU">GRU</option>`;
        }

        if (
            item.id === 'honorarios-periciais' ||
            item.tipo === 'Honorários periciais'
        ) {
            return `
                <option value="Conta do perito">
                    Conta do perito
                </option>
            `;
        }

        if (
            item.id === 'devolucao-reclamada' ||
            item.tipo === 'Devolução à reclamada'
        ) {
            return `
                <option value="Conta da reclamada">
                    Conta da reclamada
                </option>
                <option value="Conta do procurador da reclamada">
                    Conta do procurador da reclamada
                </option>
                <option value="Conta escritório da reclamada">
                    Conta escritório da reclamada
                </option>
            `;
        }

        if (
            item.id === 'transferencia-outro-processo' ||
            item.tipo === 'Transferência para outro processo'
        ) {
            return `
                <option value="Novo depósito em outro processo">
                    Novo depósito em outro processo
                </option>
            `;
        }

        return `
            <option value="">
                Selecione o tipo
            </option>
        `;
    }

    function renderCard(item, index) {
        const temDados = ![
            'inss',
            'custas',
            'transferencia-outro-processo'
        ].includes(item.id) &&
            item.tipo !== 'Transferência para outro processo';

        const avisoValorPendente =
            item.valorPendente === true
                ? `
                <div class="pje-alvara-pendente">
                    Valor não localizado na decisão.
                    <br>
                    Depósito identificado:
                    ${
                        item.deposito?.id
                            ? `#id:${utils.escapeHtml(item.deposito.id)}`
                            : 'ID não identificado'
                    }
                    ${
                        item.deposito?.banco
                            ? ` — ${utils.escapeHtml(item.deposito.banco)}`
                            : ''
                    }
                    <br>
                    Implementar aqui a leitura do depósito via API.
                </div>
              `
                : '';

        return `
            <section
                class="pje-alvara-card"
                data-alvara-card
                data-item-id="${utils.escapeHtml(item.id)}"
                data-origem="${utils.escapeHtml(
                    item.origem || 'extraído da decisão'
                )}"
            >
                <div class="pje-alvara-card-header">
                    <span class="pje-alvara-index">${index + 1}</span>

                    <input
                        class="pje-alvara-tipo"
                        data-field="tipo"
                        value="${utils.escapeHtml(item.tipo)}"
                    >

                    <button
                        type="button"
                        class="pje-alvara-remove"
                        data-remove-card
                        title="Remover este tipo"
                    >
                        Remover
                    </button>
                </div>

                <div class="pje-alvara-origem">
                    ${utils.escapeHtml(
                        item.origem || 'extraído da decisão'
                    )}
                </div>

                ${avisoValorPendente}

                <label>
                    Valor
                    <input
                        data-field="valor"
                        ${
                            item.valorFixo === true
                                ? 'data-fixo="true" readonly'
                                : 'data-money-input="true"'
                        }
                        value="${utils.escapeHtml(item.valor)}"
                    >
                </label>

                <label>
                    Destinatário / tipo
                    <select data-field="destinoTipo">
                        ${opcoesDestino(item)}
                    </select>
                </label>

                ${
                    temDados
                        ? `<div class="pje-alvara-dados">
                            <div class="pje-alvara-subtitle">
                                Dados do destinatário
                            </div>
                            ${campoDadosHtml(item)}
                           </div>`
                        : `<div class="pje-alvara-dados">
                            ${campoDadosHtml(item)}
                           </div>`
                }
            </section>
        `;
    }

    function estilos() {
        return `
            <style id="pje-alvara-style">
                #${OVERLAY_ID} {
                    position: fixed;
                    top: 0;
                    right: 0;
                    height: 100vh;
                    width: min(560px, 96vw);
                    z-index: 2147483647;
                    background: #f8fafc;
                    border-left: 1px solid #cbd5e1;
                    box-shadow: -10px 0 26px rgba(15, 23, 42, .18);
                    display: flex;
                    flex-direction: column;
                    font-family: Arial, sans-serif;
                }

                .pje-alvara-window {
                    flex: 1;
                    min-height: 0;
                    display: flex;
                    flex-direction: column;
                    background: #f8fafc;
                    color: #172033;
                    overflow: hidden;
                }

                .pje-alvara-header {
                    padding: 7px 12px;
                    background: #172554;
                    color: #fff;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 10px;
                }

                .pje-alvara-header h2 {
                    margin: 0;
                    font-size: 14px;
                }

                .pje-alvara-header small {
                    display: block;
                    margin-top: 2px;
                    color: #bfdbfe;
                }

                .pje-alvara-close {
                    border: 0;
                    background: transparent;
                    color: #fff;
                    font-size: 18px;
                    line-height: 1;
                    cursor: pointer;
                }

                .pje-alvara-content {
                    flex: 1;
                    min-height: 0;
                    padding: 8px 10px;
                    overflow-y: auto;
                }

                .pje-alvara-alert {
                    padding: 5px 8px;
                    margin-bottom: 6px;
                    border-radius: 5px;
                    background: #fef3c7;
                    border: 1px solid #f59e0b;
                    color: #78350f;
                    font-size: 10.5px;
                    line-height: 1.25;
                }

                .pje-alvara-pendente {
                    margin: 4px 0 6px;
                    padding: 5px 8px;
                    border: 1px solid #f59e0b;
                    border-radius: 5px;
                    background: #fffbeb;
                    color: #92400e;
                    font-size: 11px;
                    line-height: 1.3;
                }

                .pje-alvara-empty {
                    padding: 8px;
                    border: 1px dashed #94a3b8;
                    border-radius: 6px;
                    background: #fff;
                    color: #475569;
                    font-size: 12px;
                    line-height: 1.3;
                    text-align: center;
                }

                .pje-alvara-card {
                    margin-bottom: 8px;
                    padding: 7px 9px;
                    border: 1px solid #cbd5e1;
                    border-radius: 7px;
                    background: #fff;
                }

                .pje-alvara-card-header {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    margin-bottom: 3px;
                }

                .pje-alvara-index {
                    width: 18px;
                    height: 18px;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    background: #2563eb;
                    color: #fff;
                    font-weight: bold;
                    font-size: 11px;
                    flex: none;
                }

                .pje-alvara-tipo {
                    flex: 1;
                    font-weight: bold;
                    font-size: 12.5px;
                    padding: 3px 6px !important;
                    margin-top: 0 !important;
                }

                .pje-alvara-card label {
                    display: block;
                    margin: 3px 0;
                    color: #334155;
                    font-size: 11px;
                    font-weight: bold;
                }

                .pje-alvara-card input,
                .pje-alvara-card select {
                    box-sizing: border-box;
                    width: 100%;
                    margin-top: 2px;
                    padding: 4px 7px;
                    border: 1px solid #94a3b8;
                    border-radius: 4px;
                    background: #fff;
                    color: #0f172a;
                    font-size: 12px;
                }

                .pje-alvara-dados {
                    margin-top: 5px;
                    padding: 6px 8px;
                    border-radius: 5px;
                    background: #f1f5f9;
                }

                .pje-alvara-dados-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 4px 8px;
                }

                .pje-alvara-subtitle {
                    margin-bottom: 3px;
                    color: #1e3a8a;
                    font-size: 10.5px;
                    font-weight: bold;
                }

                .pje-alvara-info {
                    padding: 4px 6px;
                    margin-top: 4px;
                    border-radius: 4px;
                    background: #e2e8f0;
                    color: #475569;
                    font-size: 10.5px;
                    line-height: 1.3;
                }

                .pje-alvara-secondary {
                    margin-top: 5px;
                    padding: 4px 10px;
                    border: 1px solid #64748b;
                    border-radius: 5px;
                    background: #fff;
                    color: #334155;
                    cursor: pointer;
                    font-size: 11px;
                }

                .pje-alvara-secondary:hover {
                    background: #e2e8f0;
                }

                .pje-alvara-footer {
                    display: flex;
                    flex-direction: column;
                    align-items: stretch;
                    gap: 5px;
                    padding: 7px 10px;
                    border-top: 1px solid #cbd5e1;
                    background: #f1f5f9;
                }

                .pje-alvara-add-row {
                    display: flex;
                    gap: 6px;
                    align-items: stretch;
                }

                .pje-alvara-add-select {
                    flex: 1;
                    padding: 5px 8px;
                    border: 1px solid #94a3b8;
                    border-radius: 5px;
                    background: #fff;
                    color: #0f172a;
                    font-size: 12px;
                    box-sizing: border-box;
                }

                .pje-alvara-add {
                    padding: 5px 12px;
                    border: 0;
                    border-radius: 5px;
                    background: #2563eb;
                    color: #fff;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 12px;
                    flex: none;
                }

                .pje-alvara-add:hover {
                    background: #1d4ed8;
                }

                .pje-alvara-status {
                    color: #475569;
                    font-size: 10.5px;
                    text-align: center;
                }

                .pje-alvara-primary {
                    width: 100%;
                    padding: 7px 12px;
                    border: 0;
                    border-radius: 5px;
                    background: #16a34a;
                    color: #fff;
                    font-weight: bold;
                    cursor: pointer;
                    box-sizing: border-box;
                    font-size: 13px;
                }

                .pje-alvara-primary:hover {
                    background: #15803d;
                }

                .pje-alvara-origem {
                    margin: 0 0 4px;
                    color: #64748b;
                    font-size: 10px;
                    font-style: italic;
                }

                .pje-alvara-remove {
                    padding: 2px 7px;
                    border: 1px solid #dc2626;
                    border-radius: 4px;
                    background: #fff;
                    color: #b91c1c;
                    cursor: pointer;
                    font-size: 10.5px;
                    flex: none;
                }

                .pje-alvara-remove:hover {
                    background: #fee2e2;
                }

                @media (max-width: 700px) {
                    .pje-alvara-dados-grid {
                        grid-template-columns: 1fr;
                    }
                }
            </style>
        `;
    }

    function abrirOverlay(estado) {
        const existente = document.getElementById(OVERLAY_ID);
        if (existente) existente.remove();

        const overlay = document.createElement('div');
        overlay.id = OVERLAY_ID;

        overlay.innerHTML = `
            ${estilos()}

            <div class="pje-alvara-window">
                <header class="pje-alvara-header">
                    <div>
                        <h2>Elaboração de alvarás</h2>
                        <small>
                            ${
                                (estado.processo && estado.processo.numero)
                                    ? `Processo ${utils.escapeHtml(estado.processo.numero)}`
                                    : `Processo ${utils.escapeHtml(estado.processoId || 'não identificado')}`
                            }
                        </small>
                    </div>

                    <button
                        type="button"
                        class="pje-alvara-close"
                        data-close
                        title="Fechar"
                    >
                        ×
                    </button>
                </header>

                <main class="pje-alvara-content">
                    <div class="pje-alvara-alert">
                        Confira valores e destinatários antes de criar os alvarás.
                    </div>

                    <div data-cards>
                        ${
                            estado.itens.length
                                ? estado.itens.map(renderCard).join('')
                                : `<div class="pje-alvara-empty">
                                    Nenhum tipo de verba detectado na decisão.
                                   </div>`
                        }
                    </div>
                </main>

                <footer class="pje-alvara-footer">
                    <span class="pje-alvara-status" data-status-salvamento>
                        Dados carregados para conferência
                    </span>

                    <div class="pje-alvara-add-row">
                        <select class="pje-alvara-add-select" data-novo-tipo>
                            <option value="">Selecione a verba…</option>
                            <option>Crédito do exequente</option>
                            <option>INSS</option>
                            <option>Custas</option>
                            <option>Honorários advocatícios</option>
                            <option>Honorários periciais</option>
                            <option>Devolução à reclamada</option>
                            <option>Transferência para outro processo</option>
                        </select>

                        <button
                            type="button"
                            class="pje-alvara-add"
                            data-adicionar-tipo
                        >
                            Adicionar Verba
                        </button>
                    </div>

                    <button
                        type="button"
                        class="pje-alvara-primary"
                        data-criar-alvaras
                    >
                        Criar alvarás
                    </button>
                </footer>
            </div>
        `;

        document.body.appendChild(overlay);

        aplicarValoresDosSelects(overlay, estado);
        aplicarMascaraCampos(overlay);
        instalarEventosOverlay(overlay);

        salvarEstado(estado);
    }

    function aplicarValoresDosSelects(overlay, estado) {
        estado.itens.forEach(item => {
            const card = overlay.querySelector(
                `[data-item-id="${CSS.escape(item.id)}"]`
            );

            if (!card) return;

            const destino = card.querySelector(
                '[data-field="destinoTipo"]'
            );

            if (destino && item.destinoTipo) {
                destino.value = item.destinoTipo;
            }

            const perito = card.querySelector(
                '[data-field="perito"]'
            );

            if (perito && item.perito) {
                perito.value = item.perito;
            }

            if (item.dados) {
                for (const campo of [
                    'banco',
                    'agencia',
                    'conta',
                    'tipoConta'
                ]) {
                    const input = card.querySelector(
                        `[data-field="${campo}"]`
                    );

                    if (input) {
                        input.value = item.dados[campo] || '';
                    }
                }
            }

            const processoDestino = card.querySelector(
                '[data-field="processoDestino"]'
            );

            if (processoDestino && item.transferencia) {
                processoDestino.value =
                    item.transferencia.processoDestino || '';
            }

            const tribunalDestino = card.querySelector(
                '[data-field="tribunalDestino"]'
            );

            if (tribunalDestino && item.transferencia) {
                tribunalDestino.value =
                    item.transferencia.tribunalDestino || '';
            }

            const unidadeDestino = card.querySelector(
                '[data-field="unidadeDestino"]'
            );

            if (unidadeDestino && item.transferencia) {
                unidadeDestino.value =
                    item.transferencia.unidadeDestino || '';
            }
        });
    }

    function instalarEventosRemocao(overlay) {
        overlay.querySelectorAll('[data-remove-card]')
            .forEach(button => {
                if (button.dataset.bound === 'true') {
                    return;
                }

                button.dataset.bound = 'true';

                button.addEventListener('click', () => {
                    const card = button.closest(
                        '[data-alvara-card]'
                    );

                    if (!card) {
                        return;
                    }

                    const tipo = card.querySelector(
                        '[data-field="tipo"]'
                    )?.value || 'este item';

                    const confirmar = window.confirm(
                        `Remover "${tipo}"?`
                    );

                    if (!confirmar) {
                        return;
                    }

                    card.remove();
                    atualizarEstadoPeloOverlay();
                });
            });
    }

    function instalarEventosOverlay(overlay) {
        overlay.querySelector('[data-close]')
            ?.addEventListener('click', () => {
                atualizarEstadoPeloOverlay();
                overlay.remove();
            });

        overlay.addEventListener('change', event => {
            if (
                event.target.matches(
                    'input, select, textarea'
                )
            ) {
                atualizarEstadoPeloOverlay();
            }
        });

        overlay.addEventListener('input', event => {
            if (
                event.target.matches(
                    'input, select, textarea'
                )
            ) {
                atualizarEstadoPeloOverlay();
            }
        });

        overlay.querySelectorAll('[data-siscon-button]')
            .forEach(button => {
                button.addEventListener('click', () => {
                    alert(
                        'Integração com o SISCON ainda não implementada.'
                    );
                });
            });

        overlay.querySelector('[data-adicionar-tipo]')
            ?.addEventListener('click', () => {
                const select = overlay.querySelector('[data-novo-tipo]');
                const tipo = select?.value;

                if (!tipo) {
                    logAviso('selecione a verba antes de adicionar.');
                    return;
                }

                const novoItem = criarItemManual(tipo);

                const estado = carregarEstado() || {
                    versao: 1,
                    processoId: obterProcessoId(),
                    url: window.location.href,
                    itens: []
                };

                estado.itens = Array.isArray(estado.itens)
                    ? estado.itens
                    : [];

                estado.itens.push(novoItem);
                salvarEstado(estado);

                const cards = overlay.querySelector('[data-cards]');

                if (cards) {
                    const vazio = cards.querySelector('.pje-alvara-empty');

                    if (vazio) {
                        vazio.remove();
                    }

                    cards.insertAdjacentHTML(
                        'beforeend',
                        renderCard(
                            novoItem,
                            estado.itens.length - 1
                        )
                    );
                }

                if (select) {
                    select.value = '';
                }

                aplicarMascaraCampos(overlay);

                overlay.querySelectorAll('[data-siscon-button]')
                    .forEach(button => {
                        if (button.dataset.bound === 'true') {
                            return;
                        }

                        button.dataset.bound = 'true';

                        button.addEventListener('click', () => {
                            alert(
                                'Integração com o SISCON ainda não implementada.'
                            );
                        });
                    });

                instalarEventosRemocao(overlay);
                atualizarEstadoPeloOverlay();
            });

        instalarEventosRemocao(overlay);

        overlay.querySelector('[data-criar-alvaras]')
            ?.addEventListener('click', () => {
                atualizarEstadoPeloOverlay();

                alert(
                    'Estrutura preparada. A criação efetiva dos alvarás será implementada na próxima etapa.'
                );
            });
    }

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
        extrairValores,
        salvarEstado,
        carregarEstado,
        criarItemManual,
        criarEstado,
        obterProcessoId,
        isPaginaDetalhe,
        criarBotao,
        obterTextoDecisao,
        extrairDocumentoAtualLocal,
        obterTextoDocumentoAtual,
        buscarDadosProcesso
    };

    window.PjeAlvara.extrairReferenciaDeposito =
        extrairReferenciaDeposito;

    window.PjeAlvara.REGEX = REGEX;

})()
