// ==UserScript==
// @name         Triagem Petição Trabalhista - OTIMIZADO - Zona Sul SP
// @namespace    http://tampermonkey.net/
// @version      4.0
// @description  Análise automática otimizada de petição inicial trabalhista - TRT2 Zona Sul SP
// @author       AI Assistant
// @match        *://pje.trt2.jus.br/*/detalhe*
// @match        *://pje.trt2.jus.br/primeirograu/Processo/ConsultaProcesso/Detalhe/list.seam*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ===== CONFIGURAÇÕES =====
    const INTERVALOS_CEP_ZONA_SUL = [
        [4307000, 4314999], [4316000, 4477999], [4603000, 4620999],
        [4624000, 4703999], [4708000, 4967999], [5640000, 5642999],
        [5657000, 5665999], [5692000, 5692999], [5703000, 5743999],
        [5745000, 5750999], [5752000, 5895999]
    ];

    const SALARIO_MINIMO_2025 = 1518.00;
    const ALCADA = SALARIO_MINIMO_2025 * 2;
    const RITO_SUMARISSIMO_MAX = SALARIO_MINIMO_2025 * 40;

    let textoExtraido = '';
    let capaProcesso = '';
    let corpoProcesso = '';

    // ===== UTILITÁRIOS =====
    function normalizarTexto(texto) {
        return texto
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/\s+/g, ' ')
            .trim();
    }

    function extrairCEP(texto, contexto = '') {
        // Regex mais flexível para capturar CEP com ou sem formatação
        const regexCEP = /CEP[:\s]*(\d{2})\.?(\d{3})-?(\d{3})/gi;
        const ceps = [];
        let match;

        while ((match = regexCEP.exec(texto)) !== null) {
            const cepFormatado = `${match[1]}.${match[2]}-${match[3]}`;
            const cepNumerico = parseInt(match[1] + match[2] + match[3]);
            const posicao = match.index;
            
            // Capturar contexto ao redor (100 caracteres antes e depois)
            const inicio = Math.max(0, posicao - 100);
            const fim = Math.min(texto.length, posicao + 150);
            const trechoContexto = texto.substring(inicio, fim);

            ceps.push({
                formatado: cepFormatado,
                numerico: cepNumerico,
                posicao: posicao,
                contexto: trechoContexto
            });
        }

        return ceps;
    }

    function verificarCEPCompetencia(cepNumerico) {
        for (const [min, max] of INTERVALOS_CEP_ZONA_SUL) {
            if (cepNumerico >= min && cepNumerico <= max) {
                return true;
            }
        }
        return false;
    }

    function extrairValoresMonetarios(texto) {
        // Busca valores no formato R$ X.XXX,XX
        const regexValor = /R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)/g;
        const valores = [];
        let match;

        while ((match = regexValor.exec(texto)) !== null) {
            const valorStr = match[1].replace(/\./g, '').replace(',', '.');
            const valorNum = parseFloat(valorStr);
            
            if (!isNaN(valorNum) && valorNum > 0) {
                valores.push({
                    valor: valorNum,
                    formatado: match[0],
                    posicao: match.index
                });
            }
        }

        return valores;
    }

    function separarCapaCorpo(texto) {
        // Identifica a capa (primeira página) e o corpo da petição
        const marcadores = [
            'PAGINA_CAPA_PROCESSO',
            'EXCELENTÍSSIMO',
            'EXCELENTISSIMO',
            'Partes:',
            'RECLAMANTE:',
            'RECLAMADO:'
        ];

        let indiceCapa = -1;
        for (const marcador of marcadores) {
            const idx = texto.indexOf(marcador);
            if (idx !== -1 && (indiceCapa === -1 || idx < indiceCapa)) {
                indiceCapa = idx;
            }
        }

        if (indiceCapa === -1) {
            return { capa: '', corpo: texto };
        }

        // Considera os primeiros 2000 caracteres como capa
        const fimCapa = Math.min(indiceCapa + 2000, texto.length);
        
        // Procura por marcadores do início do corpo
        const inicioCorpoMarcadores = ['PRELIMINARMENTE', 'DO MÉRITO', 'DOS FATOS'];
        let indiceCorpo = fimCapa;
        
        for (const marcador of inicioCorpoMarcadores) {
            const idx = texto.indexOf(marcador, indiceCapa);
            if (idx !== -1 && idx < indiceCorpo) {
                indiceCorpo = idx;
            }
        }

        return {
            capa: texto.substring(indiceCapa, fimCapa),
            corpo: texto.substring(indiceCorpo)
        };
    }

    // ===== FUNÇÕES DE ANÁLISE =====

    function analisarCompetenciaTerritorial(texto) {
        const ceps = extrairCEP(texto);
        
        if (ceps.length === 0) {
            return {
                status: '❌',
                alerta: '🔔 ALERTA: Nenhum CEP identificado no documento',
                trecho: 'Não foi possível localizar CEPs',
                detalhe: ''
            };
        }

        // Prioridade 1: CEP com contexto de "último local de prestação"
        const contextosPrioritarios = [
            'ultimo local',
            'último local',
            'prestacao de servico',
            'prestação de serviço',
            'competencia territorial',
            'competência territorial',
            'local de trabalho'
        ];

        let cepPrioritario = null;
        for (const cep of ceps) {
            const contextoNorm = normalizarTexto(cep.contexto);
            for (const ctx of contextosPrioritarios) {
                if (contextoNorm.includes(ctx)) {
                    cepPrioritario = cep;
                    break;
                }
            }
            if (cepPrioritario) break;
        }

        // Prioridade 2: CEP da reclamada
        if (!cepPrioritario) {
            for (const cep of ceps) {
                const contextoNorm = normalizarTexto(cep.contexto);
                if (contextoNorm.includes('reclamad')) {
                    cepPrioritario = cep;
                    break;
                }
            }
        }

        // Prioridade 3: Primeiro CEP encontrado (exceto reclamante)
        if (!cepPrioritario) {
            for (const cep of ceps) {
                const contextoNorm = normalizarTexto(cep.contexto);
                if (!contextoNorm.includes('reclamante')) {
                    cepPrioritario = cep;
                    break;
                }
            }
        }

        if (!cepPrioritario && ceps.length > 0) {
            cepPrioritario = ceps[0];
        }

        const competente = verificarCEPCompetencia(cepPrioritario.numerico);

        if (competente) {
            return {
                status: '✅',
                alerta: `✅ Competência da Zona Sul: CEP ${cepPrioritario.formatado}`,
                trecho: cepPrioritario.contexto.substring(0, 100) + '...',
                detalhe: `CEP ${cepPrioritario.formatado} está dentro da jurisdição`
            };
        } else {
            return {
                status: '⚠️',
                alerta: `🔔 ALERTA: Incompetência Territorial - CEP ${cepPrioritario.formatado} fora da jurisdição`,
                trecho: cepPrioritario.contexto.substring(0, 100) + '...',
                detalhe: 'Verificar redistribuição'
            };
        }
    }

    function analisarPartes(texto) {
        const capa = capaProcesso || texto.substring(0, 2000);
        
        // Extrair reclamante
        const regexReclamante = /RECLAMANTE:\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]+)\s*-\s*CPF:\s*([\d\.\-]+)/i;
        const matchReclamante = capa.match(regexReclamante);
        
        // Extrair reclamado(s)
        const regexReclamado = /RECLAMADO:\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]+)\s*-\s*(CNPJ|CPF):\s*([\d\.\-\/]+)/gi;
        const reclamados = [];
        let matchReclamado;
        
        while ((matchReclamado = regexReclamado.exec(capa)) !== null) {
            reclamados.push({
                nome: matchReclamado[1].trim(),
                tipo: matchReclamado[2],
                documento: matchReclamado[3]
            });
        }

        let alertas = [];
        
        if (!matchReclamante) {
            alertas.push('Reclamante não identificado claramente na capa');
        }
        
        if (reclamados.length === 0) {
            alertas.push('Nenhum reclamado identificado na capa');
        }

        if (alertas.length > 0) {
            return {
                status: '⚠️',
                alerta: '🔔 ALERTA: ' + alertas.join('; '),
                trecho: capa.substring(0, 200) + '...',
                detalhe: 'Verificar qualificação das partes'
            };
        }

        return {
            status: '✅',
            alerta: `✅ Partes identificadas: Reclamante e ${reclamados.length} reclamado(s)`,
            trecho: '',
            detalhe: ''
        };
    }

    function analisarSegredoJustica(texto) {
        const termos = [
            'segredo de justica',
            'segredo de justiça',
            'tramitacao sigilosa',
            'tramitação sigilosa',
            'art.*189.*cpc',
            'artigo.*189'
        ];

        for (const termo of termos) {
            const regex = new RegExp(termo, 'gi');
            if (regex.test(normalizarTexto(texto))) {
                const match = texto.match(regex);
                const posicao = texto.indexOf(match[0]);
                const trecho = texto.substring(Math.max(0, posicao - 50), Math.min(texto.length, posicao + 100));
                
                return {
                    status: '⚠️',
                    alerta: '🔔 ALERTA: Pedido de segredo de justiça identificado',
                    trecho: trecho,
                    detalhe: 'Verificar fundamentação legal'
                };
            }
        }

        return {
            status: '✅',
            alerta: '✅ Sem pedido de segredo de justiça',
            trecho: '',
            detalhe: ''
        };
    }

    function analisarCNPJReclamadas(texto) {
        // Buscar CNPJs no formato xx.xxx.xxx/xxxx-xx ou xxxxxxxxxxxxxx
        const regexCNPJ = /CNPJ[:\s]*(\d{2})\.?(\d{3})\.?(\d{3})\/?(\d{4})-?(\d{2})/gi;
        const cnpjs = [];
        let match;

        while ((match = regexCNPJ.exec(texto)) !== null) {
            const cnpjFormatado = `${match[1]}.${match[2]}.${match[3]}/${match[4]}-${match[5]}`;
            const sufixo = match[4];
            const tipo = sufixo === '0001' ? 'Matriz' : 'Filial';
            
            cnpjs.push({
                cnpj: cnpjFormatado,
                tipo: tipo,
                sufixo: sufixo
            });
        }

        if (cnpjs.length === 0) {
            return {
                status: '⚠️',
                alerta: '🔔 ALERTA: Nenhum CNPJ identificado',
                trecho: '',
                detalhe: 'Verificar se há reclamadas pessoa jurídica'
            };
        }

        const temFilial = cnpjs.some(c => c.tipo === 'Filial');
        const temMatriz = cnpjs.some(c => c.tipo === 'Matriz');

        if (temFilial && !temMatriz) {
            return {
                status: '⚠️',
                alerta: `🔔 ALERTA: CNPJ de filial sem menção à matriz`,
                trecho: cnpjs.map(c => c.cnpj).join(', '),
                detalhe: 'Verificar se deve constar CNPJ da matriz'
            };
        }

        return {
            status: '✅',
            alerta: `✅ ${cnpjs.length} CNPJ(s) identificado(s)`,
            trecho: cnpjs.map(c => `${c.cnpj} (${c.tipo})`).join('; '),
            detalhe: ''
        };
    }

    function analisarTutelasProvisionais(texto) {
        // Buscar termos específicos de tutela provisória
        const termosTutela = [
            'tutela\\s+de\\s+urgencia',
            'tutela\\s+de\\s+urgência',
            'tutela\\s+antecipada',
            'tutela\\s+provisoria',
            'tutela\\s+provisória',
            'tutela\\s+cautelar',
            'art\\.?\\s*300',
            'art\\.?\\s*305',
            'art\\.?\\s*311',
            'artigo\\s*300',
            'artigo\\s*305',
            'artigo\\s*311'
        ];

        // Procurar na seção de pedidos (geralmente no final)
        const indicePedidos = Math.max(
            texto.lastIndexOf('PEDIDOS'),
            texto.lastIndexOf('DOS PEDIDOS'),
            texto.lastIndexOf('REQUERIMENTOS'),
            texto.length - 3000
        );

        const secaoPedidos = texto.substring(Math.max(0, indicePedidos));

        for (const termo of termosTutela) {
            const regex = new RegExp(termo, 'gi');
            if (regex.test(normalizarTexto(secaoPedidos))) {
                const match = secaoPedidos.match(regex);
                if (match) {
                    const posicao = secaoPedidos.indexOf(match[0]);
                    const trecho = secaoPedidos.substring(Math.max(0, posicao - 80), Math.min(secaoPedidos.length, posicao + 120));
                    
                    return {
                        status: '⚠️',
                        alerta: '🔔 ALERTA: Pedido de tutela provisória identificado',
                        trecho: trecho,
                        detalhe: 'Necessário encaminhamento imediato para despacho'
                    };
                }
            }
        }

        return {
            status: '✅',
            alerta: '✅ Sem pedido de tutela provisória',
            trecho: '',
            detalhe: ''
        };
    }

    function analisarJuizo100Digital(texto) {
        const termos = [
            'juizo\\s*100%?\\s*digital',
            'juízo\\s*100%?\\s*digital',
            'rito\\s*100%?\\s*digital',
            'atos.*virtuais',
            'audiencia.*virtual',
            'audiência.*virtual',
            'telepresencial'
        ];

        for (const termo of termos) {
            const regex = new RegExp(termo, 'gi');
            if (regex.test(normalizarTexto(texto))) {
                const match = texto.match(regex);
                if (match) {
                    const posicao = texto.indexOf(match[0]);
                    const trecho = texto.substring(Math.max(0, posicao - 50), Math.min(texto.length, posicao + 100));
                    
                    return {
                        status: '⚠️',
                        alerta: '⚠️ ATENÇÃO: Manifestação de adesão ao Juízo 100% Digital',
                        trecho: trecho,
                        detalhe: 'Verificar compatibilidade'
                    };
                }
            }
        }

        return {
            status: '✅',
            alerta: '✅ Sem pedido de Juízo 100% Digital',
            trecho: '',
            detalhe: ''
        };
    }

    function analisarValorCausa(texto) {
        // Buscar valor da causa na capa
        const capa = capaProcesso || texto.substring(0, 2000);
        const regexValorCausa = /Valor\s+da\s+causa:\s*R\$\s*([\d\.,]+)/i;
        const matchValorCausa = capa.match(regexValorCausa);

        let valorCausa = 0;
        if (matchValorCausa) {
            const valorStr = matchValorCausa[1].replace(/\./g, '').replace(',', '.');
            valorCausa = parseFloat(valorStr);
        }

        // Buscar valores liquidados na seção de pedidos
        const indicePedidos = Math.max(
            texto.lastIndexOf('PEDIDOS'),
            texto.lastIndexOf('DOS PEDIDOS'),
            texto.length - 3000
        );

        const secaoPedidos = texto.substring(Math.max(0, indicePedidos));
        const valoresEncontrados = extrairValoresMonetarios(secaoPedidos);

        // Filtrar valores maiores que R$ 50 (evitar valores irrelevantes)
        const valoresRelevantes = valoresEncontrados.filter(v => v.valor > 50);

        if (valoresRelevantes.length === 0) {
            return {
                status: '⚠️',
                alerta: '🔔 ALERTA: Pedidos não liquidados - valores não encontrados',
                trecho: 'Não foram identificados valores específicos nos pedidos',
                detalhe: 'Verificar se os pedidos foram apresentados de forma líquida'
            };
        }

        // Somar valores dos pedidos
        const totalPedidos = valoresRelevantes.reduce((sum, v) => sum + v.valor, 0);

        const resultado = {
            status: '✅',
            alerta: `✅ Pedidos liquidados identificados: Total aprox. R$ ${totalPedidos.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`,
            trecho: valoresRelevantes.slice(0, 5).map(v => v.formatado).join(', ') + (valoresRelevantes.length > 5 ? '...' : ''),
            detalhe: `${valoresRelevantes.length} valores identificados na seção de pedidos`
        };

        return resultado;
    }

    function analisarPessoasFisicas(texto) {
        const capa = capaProcesso || texto.substring(0, 2000);
        
        // Buscar especificamente na seção RECLAMADO
        const regexReclamadoInicio = /RECLAMADO:/i;
        const matchInicio = capa.match(regexReclamadoInicio);
        
        if (!matchInicio) {
            return {
                status: '⚠️',
                alerta: '⚠️ Não foi possível identificar seção RECLAMADO',
                trecho: '',
                detalhe: ''
            };
        }

        const inicioReclamado = capa.indexOf(matchInicio[0]);
        const secaoReclamado = capa.substring(inicioReclamado, inicioReclamado + 500);

        // Buscar CPF na seção de reclamado (indicando pessoa física)
        const regexCPF = /CPF:\s*([\d\.\-]+)/i;
        const matchCPF = secaoReclamado.match(regexCPF);

        if (matchCPF) {
            // Encontrou CPF no polo passivo - é pessoa física
            return {
                status: '⚠️',
                alerta: '🔔 ALERTA: Pessoa física no polo passivo',
                trecho: secaoReclamado.substring(0, 150) + '...',
                detalhe: 'Verificar fundamentação jurídica para inclusão'
            };
        }

        return {
            status: '✅',
            alerta: '✅ Apenas pessoas jurídicas no polo passivo',
            trecho: '',
            detalhe: ''
        };
    }

    function analisarOutrosProcessos(texto) {
        // Buscar número de processo no formato padrão: 0000000-00.0000.0.00.0000
        const regexProcesso = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/g;
        const processos = [];
        let match;

        while ((match = regexProcesso.exec(texto)) !== null) {
            processos.push({
                numero: match[0],
                posicao: match.index
            });
        }

        if (processos.length > 1) {
            // Mais de um processo mencionado (além do atual)
            const trechos = processos.slice(0, 2).map(p => {
                const inicio = Math.max(0, p.posicao - 80);
                const fim = Math.min(texto.length, p.posicao + 100);
                return texto.substring(inicio, fim);
            });

            return {
                status: '⚠️',
                alerta: `🔔 ALERTA: Menção a outro(s) processo(s): ${processos.slice(1).map(p => p.numero).join(', ')}`,
                trecho: trechos.join(' | '),
                detalhe: 'Verificar litispendência, prevenção ou conexão'
            };
        }

        return {
            status: '✅',
            alerta: '✅ Sem menção a outros processos',
            trecho: '',
            detalhe: ''
        };
    }

    function analisarResponsabilidade(texto) {
        const capa = capaProcesso || texto.substring(0, 2000);
        
        // Contar número de reclamados
        const regexReclamado = /RECLAMADO:/gi;
        const matches = capa.match(regexReclamado);
        const numReclamados = matches ? matches.length : 0;

        if (numReclamados <= 1) {
            return {
                status: '✅',
                alerta: '✅ Apenas um reclamado - análise não aplicável',
                trecho: '',
                detalhe: ''
            };
        }

        // Buscar termos de responsabilidade
        const termosResp = [
            'responsabilidade\\s+subsidiaria',
            'responsabilidade\\s+subsidiária',
            'responsabilidade\\s+solidaria',
            'responsabilidade\\s+solidária',
            'responsabilizacao\\s+subsidiaria',
            'responsabilização\\s+subsidiária'
        ];

        let encontrouPedido = false;
        let trechoEncontrado = '';

        for (const termo of termosResp) {
            const regex = new RegExp(termo, 'gi');
            if (regex.test(normalizarTexto(texto))) {
                encontrouPedido = true;
                const match = texto.match(regex);
                if (match) {
                    const posicao = texto.indexOf(match[0]);
                    trechoEncontrado = texto.substring(Math.max(0, posicao - 80), Math.min(texto.length, posicao + 120));
                }
                break;
            }
        }

        if (!encontrouPedido) {
            return {
                status: '⚠️',
                alerta: `🔔 ALERTA: ${numReclamados} reclamados mas sem pedido de responsabilidade subsidiária/solidária`,
                trecho: '',
                detalhe: 'Verificar necessidade de emenda'
            };
        }

        return {
            status: '✅',
            alerta: '✅ Pedido de responsabilidade identificado',
            trecho: trechoEncontrado,
            detalhe: ''
        };
    }

    function analisarEnderecoReclamante(texto) {
        const capa = capaProcesso || texto.substring(0, 2000);
        
        // Buscar endereço do reclamante
        const regexReclamante = /RECLAMANTE:[\s\S]{0,500}?(Rua|Av\.|Avenida|Travessa)[^,]+,[^,]+,([^,\n]+)/i;
        const matchEndereco = capa.match(regexReclamante);

        if (!matchEndereco) {
            // Tentar buscar no corpo da petição (qualificação)
            const inicioCorpo = corpoProcesso || texto.substring(2000, 5000);
            const regexCorpo = /residente\s+e\s+domiciliado[^\.]+?([A-Z][a-záàâãéèêíïóôõöúçñ\s]+\/[A-Z]{2})/i;
            const matchCorpo = inicioCorpo.match(regexCorpo);

            if (matchCorpo) {
                const cidade = matchCorpo[1];
                if (normalizarTexto(cidade).includes('sao paulo') || normalizarTexto(cidade).includes('são paulo')) {
                    return {
                        status: '✅',
                        alerta: '✅ Reclamante reside em São Paulo/SP',
                        trecho: matchCorpo[0],
                        detalhe: ''
                    };
                } else {
                    return {
                        status: '⚠️',
                        alerta: `🔔 ALERTA: Reclamante reside fora de São Paulo/SP: ${cidade}`,
                        trecho: matchCorpo[0],
                        detalhe: 'Verificar adequação para audiência virtual'
                    };
                }
            }

            return {
                status: '⚠️',
                alerta: '⚠️ Não foi possível identificar endereço do reclamante',
                trecho: '',
                detalhe: ''
            };
        }

        const enderecoCompleto = matchEndereco[0];
        const cidade = matchEndereco[2];

        if (normalizarTexto(cidade).includes('sao paulo') || normalizarTexto(cidade).includes('são paulo')) {
            return {
                status: '✅',
                alerta: '✅ Reclamante reside em São Paulo/SP',
                trecho: enderecoCompleto.substring(0, 150),
                detalhe: ''
            };
        } else {
            return {
                status: '⚠️',
                alerta: `🔔 ALERTA: Reclamante reside fora de São Paulo/SP`,
                trecho: enderecoCompleto.substring(0, 150),
                detalhe: 'Verificar adequação para audiência virtual'
            };
        }
    }

    function analisarRitoProcessual(texto) {
        const capa = capaProcesso || texto.substring(0, 2000);
        
        // Extrair valor da causa
        const regexValorCausa = /Valor\s+da\s+causa:\s*R\$\s*([\d\.,]+)/i;
        const matchValor = capa.match(regexValorCausa);

        if (!matchValor) {
            return {
                status: '⚠️',
                alerta: '⚠️ Valor da causa não identificado',
                trecho: '',
                detalhe: ''
            };
        }

        const valorStr = matchValor[1].replace(/\./g, '').replace(',', '.');
        const valorCausa = parseFloat(valorStr);

        // Extrair rito declarado
        const regexRito = /RITO\s+(SUMARÍSSIMO|ORDINÁRIO|SUMARISSIMO|ORDINARIO)/i;
        const matchRito = capa.match(regexRito);
        
        if (!matchRito) {
            return {
                status: '⚠️',
                alerta: '⚠️ Rito não identificado na capa',
                trecho: '',
                detalhe: ''
            };
        }

        const ritoDeclarado = normalizarTexto(matchRito[1]).includes('sumarissimo') ? 'SUMARÍSSIMO' : 'ORDINÁRIO';

        // Verificar se há pessoa jurídica de direito público
        const temPessoaPublica = /\b(municipio|município|estado|união|autarquia|fazenda\s+publica|fazenda\s+pública)\b/i.test(texto);

        let ritoCorreto;
        if (temPessoaPublica) {
            ritoCorreto = 'ORDINÁRIO';
        } else if (valorCausa <= ALCADA) {
            ritoCorreto = 'ALÇADA';
        } else if (valorCausa <= RITO_SUMARISSIMO_MAX) {
            ritoCorreto = 'SUMARÍSSIMO';
        } else {
            ritoCorreto = 'ORDINÁRIO';
        }

        if (ritoDeclarado === ritoCorreto || (ritoCorreto === 'ALÇADA' && ritoDeclarado === 'SUMARÍSSIMO')) {
            return {
                status: '✅',
                alerta: `✅ Rito ${ritoDeclarado} compatível com valor da causa R$ ${valorCausa.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`,
                trecho: `Valor: ${matchValor[0]}, Rito: ${matchRito[0]}`,
                detalhe: temPessoaPublica ? 'Rito Ordinário devido à presença de pessoa jurídica de direito público' : ''
            };
        } else {
            return {
                status: '⚠️',
                alerta: `🔔 ALERTA: Rito declarado (${ritoDeclarado}) incompatível. Rito correto: ${ritoCorreto}`,
                trecho: `Valor: ${matchValor[0]}, Rito declarado: ${matchRito[0]}`,
                detalhe: `Valor da causa: R$ ${valorCausa.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`
            };
        }
    }

    function analisarArt611BCLT(texto) {
        const regex = /art\.?\s*611-?B|artigo\s*611-?B/gi;
        
        if (regex.test(texto)) {
            const match = texto.match(regex);
            const posicao = texto.indexOf(match[0]);
            const trecho = texto.substring(Math.max(0, posicao - 80), Math.min(texto.length, posicao + 100));
            
            return {
                status: '⚠️',
                alerta: '🔔 ALERTA: Menção ao art. 611-B da CLT - colocar lembrete no processo',
                trecho: trecho,
                detalhe: ''
            };
        }

        return {
            status: '✅',
            alerta: '✅ Sem menção ao art. 611-B da CLT',
            trecho: '',
            detalhe: ''
        };
    }

    function analisarProcuracao(texto) {
        // Buscar indicadores de procuração
        const termosProcuracao = [
            'procuração',
            'procuracao',
            'poderes',
            'outorga',
            'constituir.*advogado',
            'nomeia.*advogado'
        ];

        let encontrouProcuracao = false;
        let trechoEncontrado = '';

        for (const termo of termosProcuracao) {
            const regex = new RegExp(termo, 'gi');
            if (regex.test(normalizarTexto(texto))) {
                encontrouProcuracao = true;
                const match = texto.match(regex);
                if (match) {
                    const posicao = texto.indexOf(match[0]);
                    trechoEncontrado = texto.substring(Math.max(0, posicao - 80), Math.min(texto.length, posicao + 100));
                }
                break;
            }
        }

        if (!encontrouProcuracao) {
            return {
                status: '⚠️',
                alerta: '🔔 ALERTA: Procuração não identificada no documento extraído',
                trecho: '',
                detalhe: 'Verificar se a procuração foi anexada ao PDF'
            };
        }

        return {
            status: '✅',
            alerta: '✅ Procuração identificada',
            trecho: trechoEncontrado,
            detalhe: ''
        };
    }

    // ===== PROCESSAMENTO E INTERFACE =====

    async function processarArquivo(file) {
        const statusEl = document.getElementById('trg-status-v4');
        const resultadoEl = document.getElementById('trg-resultado-v4');

        try {
            statusEl.textContent = '📄 Extraindo texto do PDF...';
            statusEl.style.color = '#60a5fa';

            const arrayBuffer = await file.arrayBuffer();
            
            // Carregar pdf.js
            if (!window.pdfjsLib) {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
                document.head.appendChild(script);
                await new Promise(resolve => script.onload = resolve);
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
            }

            const pdf = await window.pdfjsLib.getDocument(arrayBuffer).promise;
            let textoCompleto = '';

            for (let i = 1; i <= pdf.numPages; i++) {
                const page = await pdf.getPage(i);
                const content = await page.getTextContent();
                const pageText = content.items.map(item => item.str).join(' ');
                textoCompleto += pageText + '\n';
            }

            textoExtraido = textoCompleto;
            const separacao = separarCapaCorpo(textoCompleto);
            capaProcesso = separacao.capa;
            corpoProcesso = separacao.corpo;

            statusEl.textContent = '⚙️ Analisando petição...';

            // Executar análises
            const analises = [
                { nome: 'Competência Territorial (CEP)', func: analisarCompetenciaTerritorial },
                { nome: 'Análise das Partes', func: analisarPartes },
                { nome: 'Segredo de Justiça', func: analisarSegredoJustica },
                { nome: 'CNPJs das Reclamadas', func: analisarCNPJReclamadas },
                { nome: 'Tutelas Provisórias', func: analisarTutelasProvisionais },
                { nome: 'Juízo 100% Digital', func: analisarJuizo100Digital },
                { nome: 'Valor da Causa e Pedidos', func: analisarValorCausa },
                { nome: 'Pessoas Físicas no Polo Passivo', func: analisarPessoasFisicas },
                { nome: 'Outros Processos', func: analisarOutrosProcessos },
                { nome: 'Responsabilidade Subsidiária/Solidária', func: analisarResponsabilidade },
                { nome: 'Endereço Reclamante', func: analisarEnderecoReclamante },
                { nome: 'Rito Processual', func: analisarRitoProcessual },
                { nome: 'Art. 611-B CLT', func: analisarArt611BCLT },
                { nome: 'Procuração', func: analisarProcuracao }
            ];

            const resultados = [];
            for (const analise of analises) {
                const resultado = analise.func(textoExtraido);
                resultados.push({
                    nome: analise.nome,
                    ...resultado
                });
            }

            // Gerar relatório sucinto
            statusEl.textContent = '✅ Análise concluída!';
            statusEl.style.color = '#10b981';

            gerarRelatorioSucinto(resultados, resultadoEl);

        } catch (error) {
            console.error('Erro ao processar arquivo:', error);
            statusEl.textContent = '❌ Erro ao processar arquivo';
            statusEl.style.color = '#ef4444';
            resultadoEl.innerHTML = `<p style="color:#ef4444;">Erro: ${error.message}</p>`;
        }
    }

    function gerarRelatorioSucinto(resultados, container) {
        // Relatório sucinto - mostra apenas CEP e alertas
        let html = '<div style="margin-top:16px;">';
        
        // CEP sempre primeiro
        const cepAnalise = resultados.find(r => r.nome === 'Competência Territorial (CEP)');
        if (cepAnalise) {
            html += `<div style="background:${cepAnalise.status === '✅' ? '#10b981' : '#ef4444'};color:white;padding:12px;border-radius:6px;margin-bottom:12px;font-weight:bold;">`;
            html += `📍 CEP: ${cepAnalise.alerta}`;
            if (cepAnalise.trecho) {
                html += `<div style="font-size:11px;margin-top:8px;opacity:0.9;">${cepAnalise.trecho}</div>`;
            }
            html += '</div>';
        }

        // Alertas e atenções
        html += '<div style="background:#1e293b;padding:12px;border-radius:6px;margin-bottom:12px;">';
        html += '<div style="font-weight:bold;margin-bottom:8px;color:#60a5fa;">⚠️ Itens que requerem atenção:</div>';
        
        const alertas = resultados.filter(r => r.status === '⚠️' && r.nome !== 'Competência Territorial (CEP)');
        
        if (alertas.length === 0) {
            html += '<div style="color:#10b981;font-size:13px;">✅ Nenhum alerta adicional</div>';
        } else {
            html += '<ul style="margin:0;padding-left:20px;font-size:13px;">';
            for (const alerta of alertas) {
                html += `<li style="margin-bottom:8px;"><strong>${alerta.nome}:</strong> ${alerta.alerta}`;
                if (alerta.trecho) {
                    html += `<div style="font-size:11px;color:#94a3b8;margin-top:4px;font-style:italic;">"${alerta.trecho.substring(0, 100)}..."</div>`;
                }
                html += '</li>';
            }
            html += '</ul>';
        }
        html += '</div>';

        // Botão para ver relatório completo
        html += '<button id="trg-ver-completo" style="width:100%;padding:10px;background:#3b82f6;color:white;border:none;border-radius:6px;cursor:pointer;font-weight:bold;">📋 Ver Relatório Completo</button>';
        
        html += '</div>';

        container.innerHTML = html;

        // Event listener para botão de relatório completo
        document.getElementById('trg-ver-completo').addEventListener('click', () => {
            gerarRelatorioCompleto(resultados, container);
        });
    }

    function gerarRelatorioCompleto(resultados, container) {
        let html = '<div style="margin-top:16px;">';
        html += '<div style="background:#1e293b;padding:12px;border-radius:6px;margin-bottom:12px;">';
        html += '<div style="font-weight:bold;color:#60a5fa;margin-bottom:12px;">📊 RELATÓRIO COMPLETO DE TRIAGEM</div>';
        html += `<div style="font-size:12px;color:#94a3b8;">Data: ${new Date().toLocaleString('pt-BR')}</div>`;
        html += '</div>';

        for (const resultado of resultados) {
            const corStatus = resultado.status === '✅' ? '#10b981' : 
                             resultado.status === '⚠️' ? '#f59e0b' : '#ef4444';
            
            html += `<div style="background:#1e293b;padding:12px;border-radius:6px;margin-bottom:8px;border-left:4px solid ${corStatus};">`;
            html += `<div style="font-weight:bold;margin-bottom:4px;">${resultado.status} ${resultado.nome}</div>`;
            html += `<div style="font-size:13px;margin-bottom:4px;">${resultado.alerta}</div>`;
            
            if (resultado.trecho) {
                html += `<div style="font-size:11px;color:#94a3b8;font-style:italic;margin-top:6px;">Trecho: "${resultado.trecho.substring(0, 150)}${resultado.trecho.length > 150 ? '...' : ''}"</div>`;
            }
            
            if (resultado.detalhe) {
                html += `<div style="font-size:11px;color:#fbbf24;margin-top:4px;">ℹ️ ${resultado.detalhe}</div>`;
            }
            
            html += '</div>';
        }

        html += '<button id="trg-voltar-sucinto" style="width:100%;padding:10px;background:#6b7280;color:white;border:none;border-radius:6px;cursor:pointer;font-weight:bold;margin-top:12px;">← Voltar ao Resumo</button>';
        html += '</div>';

        container.innerHTML = html;

        document.getElementById('trg-voltar-sucinto').addEventListener('click', () => {
            gerarRelatorioSucinto(resultados, container);
        });
    }

    function criarInterface() {
        let root = document.getElementById('trg-peticao-root-v4');
        if (root) root.remove();

        root = document.createElement('div');
        root.id = 'trg-peticao-root-v4';
        root.style = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 99999;
            background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
            color: white;
            border: 2px solid #3b82f6;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 500px;
            max-height: 80vh;
            overflow-y: auto;
            box-sizing: border-box;
        `;

        root.innerHTML = `
            <div style="margin-bottom:16px;border-bottom:2px solid #3b82f6;padding-bottom:12px;">
                <div style="font-size:18px;font-weight:bold;margin-bottom:4px;">⚖️ Triagem Petição - Zona Sul SP</div>
                <div style="font-size:12px;opacity:0.9;">Versão 4.0 - Otimizada</div>
            </div>
            
            <button id="trg-gerar-pdf-v4" style="width:100%;padding:12px;background:#10b981;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:bold;margin-bottom:12px;font-size:14px;">
                📄 Gerar PDF Automaticamente
            </button>
            
            <div style="text-align:center;margin:12px 0;color:#94a3b8;font-size:12px;">ou</div>
            
            <label for="trg-file-v4" style="display:block;width:100%;padding:12px;background:#3b82f6;color:white;border:none;border-radius:8px;cursor:pointer;text-align:center;font-weight:bold;font-size:14px;box-sizing:border-box;">
                📂 Carregar PDF Manualmente
            </label>
            <input type="file" id="trg-file-v4" accept="application/pdf" style="display:none;">
            
            <div id="trg-status-v4" style="margin-top:16px;font-size:13px;color:#94a3b8;text-align:center;"></div>
            <div id="trg-resultado-v4"></div>
        `;

        document.body.appendChild(root);

        // Event listeners
        document.getElementById('trg-gerar-pdf-v4').addEventListener('click', () => {
            extrairIdEAbrirJanelaAutomatizada();
        });

        document.getElementById('trg-file-v4').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                processarArquivo(file);
            }
        });
    }

    // Função de automação para página de download
    function executarAutomacaoDownload() {
        const automate = localStorage.getItem('pje_automate_download');
        if (automate !== 'true') {
            console.log('Automação não solicitada para esta janela');
            return;
        }

        console.log('🤖 Executando automação de download...');
        
        setTimeout(() => {
            // 1. Clicar no ícone PDF
            const iconePdf = document.querySelector('img[src="/primeirograu/img/cp/pdf.png"]');
            if (iconePdf) {
                console.log('✓ Clicando no ícone PDF');
                iconePdf.click();

                setTimeout(() => {
                    // 2. Selecionar documentos (petição inicial + procuração)
                    const checkboxes = document.querySelectorAll('input[type="checkbox"][name="documentosSelecionados"]');
                    console.log(`✓ Encontrados ${checkboxes.length} checkboxes de documentos`);
                    
                    // Selecionar primeiros 2 documentos (geralmente petição e procuração)
                    for (let i = 0; i < Math.min(2, checkboxes.length); i++) {
                        checkboxes[i].checked = true;
                    }

                    setTimeout(() => {
                        // 3. Clicar em "Gerar PDF"
                        const botaoGerar = document.querySelector('input[value="Gerar PDF"]');
                        if (botaoGerar) {
                            console.log('✓ Clicando em Gerar PDF');
                            botaoGerar.click();

                            // 4. Sinalizar conclusão
                            setTimeout(() => {
                                localStorage.setItem('pje_pdf_status', 'generated');
                                localStorage.removeItem('pje_automate_download');
                                console.log('✅ PDF gerado com sucesso!');
                                
                                // Fechar janela após 2 segundos
                                setTimeout(() => {
                                    window.close();
                                }, 2000);
                            }, 1000);
                        }
                    }, 1000);
                }, 2000);
            }
        }, 1000);
    }

    // Inicialização
    function inicializar() {
        const urlAtual = window.location.href;
        const isPaginaDetalhe = urlAtual.includes('/detalhe');
        const isPaginaDownload = urlAtual.includes('/ConsultaProcesso/Detalhe/list.seam');

        if (isPaginaDownload) {
            executarAutomacaoDownload();
        } else if (isPaginaDetalhe) {
            criarInterface();
        }
    }

    // Aguardar carregamento completo da página
    if (document.readyState === 'complete') {
        inicializar();
    } else {
        window.addEventListener('load', inicializar);
    }

})();
