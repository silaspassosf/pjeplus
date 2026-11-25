// ==UserScript==
// @name         PJe Argos — Teste API Reaproveitamento + PDF Único (standalone)
// @namespace    pjeplus.argos.teste.api
// @version      1.4
// @description  Script isolado para consultar por API todas as pesquisas reaproveitáveis do processo, aplicar automaticamente as regras do Art. 131 CNC (ARISP 12m, RENAJUD 6m, INFOJUD 3 anos mais recentes por tipo) e gerar PDFs por empresa.
// @author       Silas
// @match        https://pje.trt2.jus.br/argos/*
// @require      https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js
// @grant        unsafeWindow
// @run-at       document-end
// ==/UserScript==
(function () {
    'use strict';

    const API_BASE = window.location.origin + '/pje-argos-api/api';
    const DEFAULT_PAGE_SIZE = 500;
    const DEFAULT_TIMEOUT_MS = 60000;

    // ── Helpers HTTP / Auth ──────────────────────────────────────────────
    function _xsrf() {
        const c = document.cookie
            .split(';')
            .map(s => s.trim())
            .find(s => s.toLowerCase().startsWith('xsrf-token='));
        return c ? decodeURIComponent(c.split('=').slice(1).join('=')) : '';
    }

    function _headers(extra) {
        const h = Object.assign({ Accept: 'application/json' }, extra || {});
        const x = _xsrf();
        if (x) h['X-XSRF-TOKEN'] = x;
        return h;
    }

    async function _fetchComTimeout(url, opts, timeoutMs) {
        const ctrl = new AbortController();
        const tid = setTimeout(() => ctrl.abort(), timeoutMs || DEFAULT_TIMEOUT_MS);
        try {
            const fullUrl = url.startsWith('http') ? url : (API_BASE + url);
            return await fetch(fullUrl, Object.assign({ credentials: 'include', signal: ctrl.signal }, opts || {}));
        } finally {
            clearTimeout(tid);
        }
    }

    async function _getJson(path, timeoutMs) {
        const t0 = performance.now();
        const r = await _fetchComTimeout(path, { method: 'GET', headers: _headers() }, timeoutMs);
        if (!r.ok) {
            const txt = await r.text().catch(() => '');
            throw new Error('HTTP ' + r.status + ' em ' + path + (txt ? ' — ' + txt.slice(0, 120) : ''));
        }
        const data = await r.json();
        return { data, ms: Math.round(performance.now() - t0) };
    }

    async function _getBytes(path, timeoutMs) {
        const r = await _fetchComTimeout(path, { method: 'GET', headers: _headers({ Accept: '*/*' }) }, timeoutMs);
        if (!r.ok) throw new Error('HTTP ' + r.status + ' ao baixar ' + path);
        const bytes = new Uint8Array(await r.arrayBuffer());
        return {
            bytes,
            contentType: (r.headers.get('content-type') || '').toLowerCase(),
            contentDisposition: r.headers.get('content-disposition') || '',
        };
    }

    // ── Extração do número CNJ da URL atual ──────────────────────────────
    function extrairNumeroProcessoDaUrl(href) {
        const u = href || window.location.href;
        const re = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/;
        const m = decodeURIComponent(u).match(re);
        return m ? m[0] : null;
    }

    // ── Camada de API do Argos ───────────────────────────────────────────
    async function buscarConvenios() {
        const { data, ms } = await _getJson('/convenios', 15000);
        const byId = {};
        for (const c of (data || [])) byId[c.id] = c;
        return { lista: data || [], byId, ms };
    }

    async function buscarProcesso(numeroProcesso) {
        const { data, ms } = await _getJson('/processos/' + encodeURIComponent(numeroProcesso), 15000);
        const partes = (data.partesProcessuais || []).map(p => ({
            idProcessoParte: p.idProcessoParte,
            nome: String(p.nome || '').trim(),
            documento: String(p.numeroCpj || '').replace(/\D/g, ''),
            pessoaFisica: !!p.pessoaFisica,
            tipoPolo: String(p.tipoPolo || '').toUpperCase(),
        }));
        return { raw: data, partes, ms };
    }

    async function buscarTarefasDoProcesso(numeroProcesso) {
        const qs = new URLSearchParams({
            numeroProcesso,
            situacao: 'CONCLUIDA',
            pagina: '1',
            tamanhoPagina: String(DEFAULT_PAGE_SIZE),
        });
        const { data, ms } = await _getJson('/consulta-tarefas?' + qs.toString(), 20000);
        return {
            total: data.totalRegistros ?? (data.resultado || []).length,
            resultado: data.resultado || [],
            ms,
        };
    }

    async function buscarTodasReaproveitaveis(docs, opts) {
        opts = opts || {};
        const tamanhoPagina = opts.tamanhoPagina || DEFAULT_PAGE_SIZE;
        const apenasLocalizacaoUsuario = !!opts.apenasLocalizacaoUsuario;
        const onProgress = typeof opts.onProgress === 'function' ? opts.onProgress : null;

        if (!docs || !docs.length) {
            return { totalRegistros: 0, qtdPaginas: 0, paginasLidas: 0, resultado: [], msTotal: 0 };
        }

        const t0 = performance.now();
        const todos = [];
        let pagina = 1;
        let qtdPaginas = 1;
        let totalRegistros = 0;

        while (pagina <= qtdPaginas) {
            const qs = new URLSearchParams();
            qs.set('pesquisarProcessos', 'true');
            qs.set('pesquisasRealizadasNaLocalizacaoUsuarioLogado', String(apenasLocalizacaoUsuario));
            for (const d of docs) qs.append('pesquisaRapidaMultiplaTarefas', d);
            qs.set('pagina', String(pagina));
            qs.set('tamanhoPagina', String(tamanhoPagina));

            if (onProgress) onProgress({ pagina, qtdPaginas, carregados: todos.length });

            const { data } = await _getJson('/consulta-tarefas-reaproveitaveis?' + qs.toString(), DEFAULT_TIMEOUT_MS);
            totalRegistros = data.totalRegistros ?? totalRegistros;
            qtdPaginas = data.qtdPaginas ?? 1;
            const lote = Array.isArray(data.resultado) ? data.resultado : [];
            for (const item of lote) todos.push(normalizarTarefa(item));

            if (!lote.length) break;
            pagina += 1;
        }

        return {
            totalRegistros,
            qtdPaginas,
            paginasLidas: pagina - 1,
            resultado: todos,
            msTotal: Math.round(performance.now() - t0),
        };
    }

    /**
     * Obtém o PDF da Certidão / Sumário de reaproveitamento gerado pelo próprio Argos.
     */
    async function obterCertidaoReaproveitamentoPdf(numeroProcesso, idsTarefas) {
        const path = '/processos/' + encodeURIComponent(numeroProcesso) + '/tarefas-processo/certidao-avulsa-reaproveitamento';
        const r = await _fetchComTimeout(
            path,
            {
                method: 'POST',
                headers: _headers({ 'Content-Type': 'application/json', Accept: '*/*' }),
                body: JSON.stringify({
                    numeroProcesso,
                    idsTarefasReaproveitadas: idsTarefas,
                }),
            },
            30000
        );
        if (!r.ok) {
            const txt = await r.text().catch(() => '');
            throw new Error('HTTP ' + r.status + ' ao gerar certidão de reaproveitamento' + (txt ? ' — ' + txt.slice(0, 120) : ''));
        }
        return new Uint8Array(await r.arrayBuffer());
    }

    /**
     * Lista os anexos (PDFs/arquivos) vinculados a uma tarefa/resultado.
     */
    async function listarArquivosTarefa(idTarefa, idResultado) {
        const { data } = await _getJson('/tarefas/' + idTarefa + '/resultados/' + idResultado + '/arquivos', 20000);
        return Array.isArray(data) ? data : [];
    }

    /**
     * Baixa os bytes de um anexo específico de tarefa/resultado.
     */
    async function baixarArquivoAnexo(idTarefa, idResultado, idArquivo) {
        return _getBytes(
            '/tarefas/' + idTarefa + '/resultados/' + idResultado + '/arquivos/' + idArquivo + '/conteudo/download',
            60000
        );
    }

    // ── Geração do PDF Único ("Poupa Convenios - <numero>.pdf") ──────────
    function _getPdfLib() {
        const lib = (typeof PDFLib !== 'undefined' && PDFLib)
            || window.PDFLib
            || (typeof unsafeWindow !== 'undefined' && unsafeWindow.PDFLib);
        if (!lib || !lib.PDFDocument) {
            throw new Error('PDFLib não disponível. Verifique @require pdf-lib no Tampermonkey.');
        }
        return lib;
    }

    function _isPdfBytes(u8) {
        return u8 && u8.length >= 5 && u8[0] === 0x25 && u8[1] === 0x50 && u8[2] === 0x44 && u8[3] === 0x46 && u8[4] === 0x2D;
    }

    async function _anexarBytesAoPdf(pdfDestino, bytes, contentType, nomeArquivo, avisos) {
        const { PDFDocument } = _getPdfLib();
        if (_isPdfBytes(bytes) || contentType.includes('pdf')) {
            const src = await PDFDocument.load(bytes, { ignoreEncryption: true });
            const paginas = await pdfDestino.copyPages(src, src.getPageIndices());
            for (const p of paginas) pdfDestino.addPage(p);
            return paginas.length;
        }
        if (contentType.includes('png') || /\.png$/i.test(nomeArquivo || '')) {
            const img = await pdfDestino.embedPng(bytes);
            const page = pdfDestino.addPage([img.width, img.height]);
            page.drawImage(img, { x: 0, y: 0, width: img.width, height: img.height });
            return 1;
        }
        if (contentType.includes('jpeg') || contentType.includes('jpg') || /\.jpe?g$/i.test(nomeArquivo || '')) {
            const img = await pdfDestino.embedJpg(bytes);
            const page = pdfDestino.addPage([img.width, img.height]);
            page.drawImage(img, { x: 0, y: 0, width: img.width, height: img.height });
            return 1;
        }
        avisos.push('Ignorado (não-PDF/imagem): ' + (nomeArquivo || 'sem nome') + ' [' + contentType + ']');
        return 0;
    }

    function _dispararDownloadBlob(bytes, nomeArquivo) {
        const blob = new Blob([bytes], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = nomeArquivo;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 15000);
    }

    function _siglaPesquisa(t, incluirAno) {
        const tipo = String(t.tipoTarefa || '').toUpperCase();
        const mapa = {
            ARISP_CONSULTA: 'ARISP',
            RENAJUD_CONSULTA: 'Renajud',
            INFOJUD_CONSULTA_DOI: 'DOI',
            INFOJUD_CONSULTA_DIMOB: 'DIMOB',
            INFOJUD_CONSULTA_ECF: 'ECF',
            INFOJUD_CONSULTA_E_FINANCEIRA: 'e-Financeira',
            INFOJUD_CONSULTA_DECRED: 'DECRED',
            INFOJUD_CONSULTA_DIRPF: 'DIRPF',
            INFOJUD_CONSULTA_DIRPJ: 'DIRPJ',
            INFOJUD_CONSULTA_DITR: 'DITR',
            SISBAJUD_BLOQUEIO: 'Sisbajud',
            CNIB_INDISPONIBILIDADE: 'CNIB',
            SERASAJUD_INCLUSAO: 'Serasajud',
        };
        let base = mapa[tipo];
        if (!base) {
            base = String(t.nomeTarefa || t.rotuloTarefa || tipo)
                .replace(/^Consulta\s+/i, '')
                .replace(/\s+(no|na)\s+(INFOJUD|ARISP|RENAJUD|SISBAJUD)$/i, '')
                .replace(/\s*\(Consulta\)$/i, '')
                .trim();
        }
        if (incluirAno && t.anoDocumentoInfojud) {
            return base + ' ' + t.anoDocumentoInfojud;
        }
        return base;
    }

    function _sanitizarNomeArquivo(nome) {
        let limpo = String(nome || 'documento')
            .replace(/[\\/:*?"<>|]+/g, ' ')
            .replace(/\s+/g, ' ')
            .trim()
            .replace(/\.+$/, '');
        if (limpo.length > 180) {
            limpo = limpo.slice(0, 177).trim() + '...';
        }
        return limpo;
    }

    function _ordenarPositivasDepoisNegativas(tarefas) {
        return tarefas.slice().sort((a, b) => {
            if (a.resultadoPositivo !== b.resultadoPositivo) {
                return a.resultadoPositivo ? -1 : 1;
            }
            return _siglaPesquisa(a, true).localeCompare(_siglaPesquisa(b, true));
        });
    }

    function _normCmp(s) {
        return String(s || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toUpperCase()
            .trim();
    }

    /**
     * Calcula o menor prefixo de palavras que diferencia cada empresa no conjunto.
     * Ex.: ["EMBA CONTROLADORA...", "PEEQFLEX INDUSTRIA...", "PEEQFLEX PARTICIPACOES..."]
     *   -> EMBA | PEEQFLEX INDUSTRIA | PEEQFLEX PARTICIPACOES
     */
    function _abreviarNomesEmpresas(grupos) {
        const entries = grupos.map(g => {
            const tokens = String(g.nomeEmpresa || g.documento || 'Executado')
                .replace(/[,.;:]+/g, ' ')
                .replace(/\s+/g, ' ')
                .trim()
                .split(' ')
                .filter(Boolean);
            return { doc: g.documento, tokens, len: 1 };
        });

        let houveColisao = true;
        while (houveColisao) {
            houveColisao = false;
            const contagem = new Map();
            for (const e of entries) {
                const chave = _normCmp(e.tokens.slice(0, e.len).join(' '));
                contagem.set(chave, (contagem.get(chave) || 0) + 1);
            }
            for (const e of entries) {
                const chave = _normCmp(e.tokens.slice(0, e.len).join(' '));
                if (contagem.get(chave) > 1 && e.len < e.tokens.length) {
                    e.len += 1;
                    houveColisao = true;
                }
            }
        }

        const mapa = new Map();
        const usados = new Map();
        for (const e of entries) {
            let curto = e.tokens.slice(0, e.len).join(' ') || e.doc;
            const chave = _normCmp(curto);
            usados.set(chave, (usados.get(chave) || 0) + 1);
            mapa.set(e.doc, curto);
        }
        // Desempate final caso duas empresas tenham exatamente o mesmo nome completo
        for (const e of entries) {
            const curto = mapa.get(e.doc);
            if (usados.get(_normCmp(curto)) > 1 && e.doc && e.doc !== 'SEM_DOC') {
                mapa.set(e.doc, curto + ' ' + e.doc.slice(-4));
            }
        }
        return mapa;
    }

    function _montarNomeArquivoEmpresa(nomeEmpresa, tarefasOrdenadas) {
        // Verifica se há múltiplos anos do mesmo tipoTarefa neste lote
        const contagemTipo = {};
        for (const t of tarefasOrdenadas) {
            const k = t.tipoTarefa || t.nomeTarefa || '';
            contagemTipo[k] = (contagemTipo[k] || 0) + 1;
        }
        const itensRotulo = [];
        const vistos = new Set();
        for (const t of tarefasOrdenadas) {
            const k = t.tipoTarefa || t.nomeTarefa || '';
            const sigla = _siglaPesquisa(t, contagemTipo[k] > 1);
            const tag = sigla + ' ' + (t.resultadoPositivo ? 'OK' : 'NEG');
            if (!vistos.has(tag)) {
                vistos.add(tag);
                itensRotulo.push(tag);
            }
        }
        const empresaLimpa = String(nomeEmpresa || 'Executado').replace(/\s+/g, ' ').trim();
        return _sanitizarNomeArquivo(empresaLimpa + ' (' + itensRotulo.join(', ') + ')') + '.pdf';
    }

    /**
     * Gera um PDF único contendo:
     *  1) Certidão / Sumário consolidado de reaproveitamento (gerado pelo Argos)
     *  2) Todos os anexos PDF/imagem das tarefas selecionadas (Positivas primeiro, depois Negativas)
     */
    async function gerarPdfUnico(numeroProcesso, tarefasSelecionadas, opts) {
        opts = opts || {};
        const num = numeroProcesso || extrairNumeroProcessoDaUrl();
        if (!num) throw new Error('Número do processo não informado.');
        if (!tarefasSelecionadas || !tarefasSelecionadas.length) {
            throw new Error('Selecione ao menos uma pesquisa para gerar o PDF.');
        }

        const tarefasOrdenadas = _ordenarPositivasDepoisNegativas(tarefasSelecionadas);
        const incluirCertidao = opts.incluirCertidao !== false;
        const baixarArquivo = opts.download !== false;
        const onStatus = typeof opts.onStatus === 'function' ? opts.onStatus : function () {};

        const { PDFDocument } = _getPdfLib();
        const pdfFinal = await PDFDocument.create();
        const avisos = [];
        const resumoArquivos = [];
        let totalPaginas = 0;

        // 1. Certidão / Sumário consolidado do Argos
        if (incluirCertidao) {
            onStatus('Gerando certidão/sumário no Argos...');
            const ids = Array.from(new Set(tarefasOrdenadas.map(t => t.idTarefa).filter(Boolean)));
            const certBytes = await obterCertidaoReaproveitamentoPdf(num, ids);
            const pagsCert = await _anexarBytesAoPdf(pdfFinal, certBytes, 'application/pdf', 'Certidao_Reaproveitamento.pdf', avisos);
            totalPaginas += pagsCert;
            resumoArquivos.push({ origem: 'certidao', nome: 'Certidão de Reaproveitamento', paginas: pagsCert, bytes: certBytes.byteLength });
        }

        // 2. Listar anexos de todas as tarefas com possuiAnexo (já ordenadas: Positivas -> Negativas)
        const tarefasComAnexo = tarefasOrdenadas.filter(t => t.possuiAnexo && t.idTarefa && t.idResultado);
        const filaDownloads = [];
        for (let i = 0; i < tarefasComAnexo.length; i++) {
            const t = tarefasComAnexo[i];
            onStatus('Listando anexos (' + (i + 1) + '/' + tarefasComAnexo.length + ') — ' + t.rotuloTarefa + '...');
            try {
                const arqs = await listarArquivosTarefa(t.idTarefa, t.idResultado);
                for (const arq of arqs) {
                    filaDownloads.push({ tarefa: t, arquivo: arq });
                }
            } catch (err) {
                avisos.push('Falha ao listar anexos tarefa ' + t.idTarefa + ': ' + (err.message || err));
            }
        }

        // 3. Baixar e mesclar cada anexo no PDF único
        for (let i = 0; i < filaDownloads.length; i++) {
            const { tarefa, arquivo } = filaDownloads[i];
            const nomeArq = arquivo.nomeArquivo || ('anexo_' + arquivo.id + '.pdf');
            onStatus('Baixando e mesclando anexo ' + (i + 1) + '/' + filaDownloads.length + ': ' + nomeArq);
            try {
                const { bytes, contentType } = await baixarArquivoAnexo(tarefa.idTarefa, tarefa.idResultado, arquivo.id);
                const pags = await _anexarBytesAoPdf(pdfFinal, bytes, contentType, nomeArq, avisos);
                totalPaginas += pags;
                resumoArquivos.push({
                    origem: 'anexo',
                    idTarefa: tarefa.idTarefa,
                    rotuloTarefa: tarefa.rotuloTarefa,
                    resultadoPositivo: tarefa.resultadoPositivo,
                    idArquivo: arquivo.id,
                    nome: nomeArq,
                    paginas: pags,
                    bytes: bytes.byteLength,
                });
            } catch (err) {
                avisos.push('Falha ao mesclar "' + nomeArq + '" (tarefa ' + tarefa.idTarefa + '): ' + (err.message || err));
            }
        }

        onStatus('Salvando PDF (' + totalPaginas + ' páginas)...');
        const pdfBytes = await pdfFinal.save();
        const nomeSaida = opts.nomeArquivo || ('Poupa Convenios - ' + num + '.pdf');

        if (baixarArquivo) {
            _dispararDownloadBlob(pdfBytes, nomeSaida);
        }

        return {
            nomeArquivo: nomeSaida,
            totalPaginas,
            bytesFinal: pdfBytes.byteLength,
            tarefasProcessadas: tarefasOrdenadas.length,
            anexosMesclados: resumoArquivos.filter(x => x.origem === 'anexo').length,
            resumoArquivos,
            avisos,
        };
    }

    /**
     * Agrupa as pesquisas por empresa (documentoExecutado) e gera:
     *  - separarPositivasNegativas = true  -> até 2 PDFs por empresa (1 só Positivas + 1 só Negativas)
     *  - separarPositivasNegativas = false -> 1 PDF por empresa (Positivas primeiro, depois Negativas)
     * Nome do arquivo: "Nome da Empresa (DOI OK, Renajud OK, DIMOB NEG).pdf"
     */
    async function gerarPdfsPorEmpresa(numeroProcesso, tarefasSelecionadas, opts) {
        opts = opts || {};
        const num = numeroProcesso || extrairNumeroProcessoDaUrl();
        if (!num) throw new Error('Número do processo não informado.');
        if (!tarefasSelecionadas || !tarefasSelecionadas.length) {
            throw new Error('Selecione ao menos uma pesquisa.');
        }

        const separar = opts.separarPositivasNegativas !== false;
        const onStatus = typeof opts.onStatus === 'function' ? opts.onStatus : function () {};

        // Agrupar por documentoExecutado
        const gruposMap = new Map();
        for (const t of tarefasSelecionadas) {
            const doc = t.documentoExecutado || 'SEM_DOC';
            if (!gruposMap.has(doc)) {
                gruposMap.set(doc, { documento: doc, nomeEmpresa: t.nomeExecutado || doc, tarefas: [] });
            }
            gruposMap.get(doc).tarefas.push(t);
        }

        const grupos = Array.from(gruposMap.values());
        const nomesCurtos = _abreviarNomesEmpresas(grupos);

        const lotes = [];
        for (const g of grupos) {
            const nomeCurto = nomesCurtos.get(g.documento) || g.nomeEmpresa;
            const ordenadas = _ordenarPositivasDepoisNegativas(g.tarefas);
            if (separar) {
                const pos = ordenadas.filter(t => t.resultadoPositivo);
                const neg = ordenadas.filter(t => !t.resultadoPositivo);
                if (pos.length) {
                    lotes.push({
                        documento: g.documento,
                        nomeEmpresa: g.nomeEmpresa,
                        nomeCurto,
                        tipoLote: 'POSITIVAS',
                        tarefas: pos,
                        nomeArquivo: _montarNomeArquivoEmpresa(nomeCurto, pos),
                    });
                }
                if (neg.length) {
                    lotes.push({
                        documento: g.documento,
                        nomeEmpresa: g.nomeEmpresa,
                        nomeCurto,
                        tipoLote: 'NEGATIVAS',
                        tarefas: neg,
                        nomeArquivo: _montarNomeArquivoEmpresa(nomeCurto, neg),
                    });
                }
            } else {
                lotes.push({
                    documento: g.documento,
                    nomeEmpresa: g.nomeEmpresa,
                    nomeCurto,
                    tipoLote: 'UNIFICADO',
                    tarefas: ordenadas,
                    nomeArquivo: _montarNomeArquivoEmpresa(nomeCurto, ordenadas),
                });
            }
        }

        const gerados = [];
        for (let i = 0; i < lotes.length; i++) {
            const lote = lotes[i];
            const prefixo = '[' + (i + 1) + '/' + lotes.length + ' ' + lote.tipoLote + '] ';
            const res = await gerarPdfUnico(num, lote.tarefas, {
                nomeArquivo: lote.nomeArquivo,
                incluirCertidao: opts.incluirCertidao,
                download: opts.download,
                onStatus: msg => onStatus(prefixo + msg),
            });
            gerados.push(Object.assign({ documento: lote.documento, nomeEmpresa: lote.nomeEmpresa, tipoLote: lote.tipoLote }, res));
            // Pequena pausa entre downloads múltiplos no navegador
            if (opts.download !== false && i < lotes.length - 1) {
                await new Promise(r => setTimeout(r, 400));
            }
        }

        return {
            numeroProcesso: num,
            modo: separar ? '2_por_empresa_pos_neg' : '1_por_empresa_unificado',
            totalArquivos: gerados.length,
            arquivos: gerados,
        };
    }

    // ── Normalização & Resumo ────────────────────────────────────────────
    function normalizarTarefa(it) {
        const ano = it.anoDocumentoInfojud || it.anodocumentoinfojud || null;
        const ocultaAno = !!(it.ocultaAnoNaExibicao ?? it.ocultaanonaexibicao);
        const nomeBase = it.nomeTarefa || it.nometarefa || it.tipoTarefa || it.tipotarefa || '';
        const rotuloTarefa = (ano && !ocultaAno) ? (nomeBase + ' (' + ano + ')') : nomeBase;
        return {
            idTarefa: it.idTarefa ?? it.idtarefa,
            idResultado: it.idResultado ?? it.idresultado,
            idConvenio: it.idconvenio ?? it.idConvenio ?? null,
            documentoExecutado: String(it.documentoExecutado || it.documentoexecutado || '').replace(/\D/g, ''),
            nomeExecutado: String(it.nomeExecutado || it.nomeexecutado || '').trim(),
            executadoPessoaFisica: !!(it.executadoPessoaFisica ?? it.executadopessoafisica),
            numeroProcessoOrigem: it.numeroProcesso || it.numeroprocesso || '',
            nomeOrgaoJulgador: it.nomeOrgaoJulgador || it.nomeorgaojulgador || '',
            tipoTarefa: it.tipoTarefa || it.tipotarefa || '',
            nomeTarefa: nomeBase,
            rotuloTarefa,
            anoDocumentoInfojud: ano,
            dataFinalizacao: it.dataFinalizacao || it.datafinalizacao || '',
            resultadoPositivo: !!(it.resultadoPositivo ?? it.resultadopositivo),
            possuiAnexo: !!(it.possuiAnexo ?? it.possuianexo),
            reaproveitamento: !!it.reaproveitamento,
            sempreReaproveitavel: !!(it.semprereaproveitavel ?? it.sempreReaproveitavel),
            diasReaproveitamento: it.quantidadediasreaproveitamentotarefa ?? null,
            ocultaAnoNaExibicao: ocultaAno,
            statusTarefa: it.statustarefa || it.statusTarefa || '',
        };
    }

    // ── Regras Ofício Circular CR nº 124/2026 (Art. 131 CNC) ─────────────
    const MAX_ANOS_INFOJUD_POR_TIPO = 3;
    const TIPOS_CONSTRICAO = new Set([
        'SISBAJUD_BLOQUEIO',
        'CNIB_INDISPONIBILIDADE',
        'SERASAJUD_INCLUSAO',
    ]);

    function _subtrairMeses(dataRef, meses) {
        const d = new Date(dataRef.getTime());
        const diaOriginal = d.getDate();
        d.setMonth(d.getMonth() - meses);
        if (d.getDate() < diaOriginal) {
            d.setDate(0);
        }
        return d;
    }

    /**
     * Avalia uma tarefa segundo o Art. 131 da CNC (Provimento GP/CR nº 4/2026):
     *  - ARISP: 12 meses
     *  - RENAJUD: 6 meses
     *  - INFOJUD: a qualquer tempo
     *  - Demais consultas: 12 meses
     *  - Atos de constrição (SISBAJUD/CNIB/SERASAJUD): não reaproveitáveis (§ 4º)
     */
    function avaliarElegibilidadeArt131(tarefa, dataRef) {
        const agora = dataRef ? new Date(dataRef) : new Date();
        const tipo = String(tarefa.tipoTarefa || '').toUpperCase();

        if (TIPOS_CONSTRICAO.has(tipo)) {
            return { elegivel: false, regra: 'Constrição (§ 4º)', motivo: 'Ato de constrição não reaproveitável', prazoMeses: 0 };
        }

        const dtFin = tarefa.dataFinalizacao ? new Date(tarefa.dataFinalizacao) : null;
        const diasDecorridos = (dtFin && !Number.isNaN(dtFin.getTime()))
            ? Math.floor((agora.getTime() - dtFin.getTime()) / (24 * 60 * 60 * 1000))
            : null;

        // c) INFOJUD: a qualquer tempo
        if (tipo.startsWith('INFOJUD_') || tarefa.idConvenio === 3 || tarefa.sempreReaproveitavel) {
            return {
                elegivel: true,
                regra: 'INFOJUD (a qualquer tempo)',
                motivo: 'Válida a qualquer tempo (art. 131, c)',
                prazoMeses: null,
                diasDecorridos,
            };
        }

        // a) ARISP: 12 meses | b) RENAJUD: 6 meses | d) demais: 12 meses
        let prazoMeses = 12;
        let rotuloRegra = 'Demais (12 meses)';
        if (tipo.startsWith('ARISP_') || tarefa.idConvenio === 4) {
            prazoMeses = 12;
            rotuloRegra = 'ARISP (12 meses)';
        } else if (tipo.startsWith('RENAJUD_') || tarefa.idConvenio === 2) {
            prazoMeses = 6;
            rotuloRegra = 'RENAJUD (6 meses)';
        }

        if (!dtFin || Number.isNaN(dtFin.getTime())) {
            return { elegivel: false, regra: rotuloRegra, motivo: 'Sem data de finalização', prazoMeses, diasDecorridos: null };
        }

        const limite = _subtrairMeses(agora, prazoMeses);
        const dentroDoPrazo = dtFin.getTime() >= limite.getTime();
        return {
            elegivel: dentroDoPrazo,
            regra: rotuloRegra,
            motivo: dentroDoPrazo
                ? ('Válida — realizada há ' + diasDecorridos + 'd')
                : ('Expirada — realizada há ' + diasDecorridos + 'd (limite ' + prazoMeses + 'm)'),
            prazoMeses,
            diasDecorridos,
        };
    }

    /**
     * Aplica o Art. 131 CNC sobre a lista completa:
     *  1) Filtra apenas pesquisas dentro da validade normativa
     *  2) Deduplica por (documentoExecutado, tipoTarefa, ano visível), mantendo a mais recente
     *  3) Para INFOJUD com ano-calendário visível, limita aos 3 anos disponíveis mais recentes por empresa e tipo
     *  4) Ordena por empresa e Positivas -> Negativas
     */
    function selecionarElegiveisArt131(itens, dataRef, opts) {
        opts = opts || {};
        const maxAnosInfojud = opts.maxAnosInfojud || MAX_ANOS_INFOJUD_POR_TIPO;
        const agora = dataRef ? new Date(dataRef) : new Date();
        const avaliadas = itens.map(it => {
            const av = avaliarElegibilidadeArt131(it, agora);
            return Object.assign({}, it, { art131: av });
        });

        const validas = avaliadas.filter(it => it.art131.elegivel);
        const dedup = resumirPorExecutadoETipo(validas);

        // Limitar INFOJUD com ano visível aos N anos disponíveis mais recentes por (empresa, tipoTarefa)
        const gruposInfojud = new Map();
        const naoInfojudAnual = [];
        for (const it of dedup) {
            const isInfojudAnual = (String(it.tipoTarefa || '').toUpperCase().startsWith('INFOJUD_') || it.idConvenio === 3)
                && it.anoDocumentoInfojud
                && !it.ocultaAnoNaExibicao;
            if (!isInfojudAnual) {
                naoInfojudAnual.push(it);
                continue;
            }
            const chave = it.documentoExecutado + '|' + it.tipoTarefa;
            if (!gruposInfojud.has(chave)) gruposInfojud.set(chave, []);
            gruposInfojud.get(chave).push(it);
        }

        const descartadasPorLimiteAnos = [];
        const infojudMantidas = [];
        for (const lista of gruposInfojud.values()) {
            // Ordena do ano mais recente para o mais antigo (desempate por dataFinalizacao)
            lista.sort((a, b) =>
                Number(b.anoDocumentoInfojud) - Number(a.anoDocumentoInfojud) ||
                String(b.dataFinalizacao).localeCompare(String(a.dataFinalizacao))
            );
            lista.forEach((it, idx) => {
                if (idx < maxAnosInfojud) {
                    infojudMantidas.push(it);
                } else {
                    descartadasPorLimiteAnos.push(Object.assign({}, it, {
                        art131: Object.assign({}, it.art131, {
                            elegivel: false,
                            motivo: 'Fora dos ' + maxAnosInfojud + ' anos mais recentes disponíveis de ' + it.nomeTarefa,
                        }),
                    }));
                }
            });
        }

        const maisRecentesValidas = naoInfojudAnual.concat(infojudMantidas).sort((a, b) =>
            a.documentoExecutado.localeCompare(b.documentoExecutado) ||
            (a.resultadoPositivo === b.resultadoPositivo ? 0 : (a.resultadoPositivo ? -1 : 1)) ||
            a.rotuloTarefa.localeCompare(b.rotuloTarefa)
        );

        // Resumo por empresa
        const porEmpresa = {};
        for (const it of maisRecentesValidas) {
            const doc = it.documentoExecutado || 'SEM_DOC';
            if (!porEmpresa[doc]) {
                porEmpresa[doc] = {
                    documento: doc,
                    nomeExecutado: it.nomeExecutado,
                    elegiveis: [],
                    positivas: 0,
                    negativas: 0,
                };
            }
            porEmpresa[doc].elegiveis.push(it);
            if (it.resultadoPositivo) porEmpresa[doc].positivas += 1;
            else porEmpresa[doc].negativas += 1;
        }
        for (const emp of Object.values(porEmpresa)) {
            emp.elegiveis = _ordenarPositivasDepoisNegativas(emp.elegiveis);
        }

        return {
            todasAvaliadas: avaliadas,
            elegiveis: maisRecentesValidas,
            expiradasOuExcluidas: avaliadas.filter(it => !it.art131.elegivel).concat(descartadasPorLimiteAnos),
            porEmpresa,
        };
    }

    function resumirPorExecutadoETipo(itens) {
        const mapa = new Map();
        for (const it of itens) {
            const anoChave = (it.anoDocumentoInfojud && !it.ocultaAnoNaExibicao) ? String(it.anoDocumentoInfojud) : '';
            const chave = [it.documentoExecutado, it.tipoTarefa, anoChave].join('|');
            const atual = mapa.get(chave);
            if (!atual || String(it.dataFinalizacao) > String(atual.dataFinalizacao)) {
                mapa.set(chave, it);
            }
        }
        return Array.from(mapa.values()).sort((a, b) =>
            a.documentoExecutado.localeCompare(b.documentoExecutado) ||
            (a.resultadoPositivo === b.resultadoPositivo ? 0 : (a.resultadoPositivo ? -1 : 1)) ||
            a.rotuloTarefa.localeCompare(b.rotuloTarefa)
        );
    }

    async function consultarProcessoCompleto(numeroProcesso, opts) {
        opts = opts || {};
        const num = numeroProcesso || extrairNumeroProcessoDaUrl();
        if (!num) throw new Error('Número do processo não encontrado na URL atual.');

        const [convenios, processo, tarefasNoProcesso] = await Promise.all([
            buscarConvenios(),
            buscarProcesso(num),
            buscarTarefasDoProcesso(num).catch(err => ({ total: 0, resultado: [], erro: String(err), ms: 0 })),
        ]);

        const partesFiltradas = opts.incluirPoloAtivo
            ? processo.partes
            : processo.partes.filter(p => p.tipoPolo === 'PASSIVO');

        const docs = Array.from(new Set(partesFiltradas.map(p => p.documento).filter(Boolean)));
        const reap = await buscarTodasReaproveitaveis(docs, opts);
        const analiseArt131 = selecionarElegiveisArt131(reap.resultado);
        const maisRecentes = resumirPorExecutadoETipo(analiseArt131.todasAvaliadas);

        const relatorio = {
            numeroProcesso: num,
            idProcesso: processo.raw.idProcesso,
            orgaoJulgador: processo.raw.descricaoOrgaoJulgador,
            partesConsultadas: partesFiltradas,
            docsConsultados: docs,
            convenios: convenios.byId,
            tarefasJaConcluidasNoProcesso: tarefasNoProcesso.total,
            reaproveitaveis: {
                totalRegistros: reap.totalRegistros,
                carregados: reap.resultado.length,
                qtdPaginas: reap.qtdPaginas,
                paginasLidas: reap.paginasLidas,
                msTotal: reap.msTotal,
                todos: analiseArt131.todasAvaliadas,
                maisRecentesPorExecutadoETipo: maisRecentes,
                elegiveisArt131: analiseArt131.elegiveis,
                expiradasArt131: analiseArt131.expiradasOuExcluidas,
                porEmpresaArt131: analiseArt131.porEmpresa,
            },
            temposMs: {
                convenios: convenios.ms,
                processo: processo.ms,
                tarefasNoProcesso: tarefasNoProcesso.ms,
                reaproveitaveis: reap.msTotal,
            },
        };

        try {
            window.__argosReap = relatorio;
            if (typeof unsafeWindow !== 'undefined') unsafeWindow.__argosReap = relatorio;
        } catch (e) { /* ignore */ }

        return relatorio;
    }

    // ── Exposição global para console / automação ────────────────────────
    const apiPublica = {
        extrairNumeroProcessoDaUrl,
        buscarConvenios,
        buscarProcesso,
        buscarTarefasDoProcesso,
        buscarTodasReaproveitaveis,
        resumirPorExecutadoETipo,
        avaliarElegibilidadeArt131,
        selecionarElegiveisArt131,
        consultar: consultarProcessoCompleto,
        obterCertidaoReaproveitamentoPdf,
        listarArquivosTarefa,
        baixarArquivoAnexo,
        gerarPdfUnico,
        gerarPdfsPorEmpresa,
    };

    try {
        window.ArgosReapApi = apiPublica;
        if (typeof unsafeWindow !== 'undefined') unsafeWindow.ArgosReapApi = apiPublica;
    } catch (e) { /* ignore */ }

    // ── UI Flutuante de Teste ────────────────────────────────────────────
    function _fmtData(iso) {
        if (!iso) return '-';
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
        return d.toLocaleDateString('pt-BR');
    }

    function _escapeHtml(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function renderizarModal(relatorio) {
        let modal = document.getElementById('argos-reap-api-modal');
        if (modal) modal.remove();

        modal = document.createElement('div');
        modal.id = 'argos-reap-api-modal';
        modal.style.cssText = [
            'position:fixed', 'inset:24px', 'z-index:999999',
            'background:#111827', 'color:#f3f4f6', 'border:1px solid #374151',
            'border-radius:10px', 'box-shadow:0 20px 60px rgba(0,0,0,.6)',
            'display:flex', 'flex-direction:column', 'font-family:system-ui,sans-serif',
            'font-size:13px', 'overflow:hidden',
        ].join(';');

        const docsUnicos = Array.from(new Set(relatorio.reaproveitaveis.todos.map(x => x.documentoExecutado)));
        const convUnicos = Array.from(new Set(relatorio.reaproveitaveis.todos.map(x => x.rotuloTarefa))).sort();
        // Pré-seleciona automaticamente as elegíveis pelo Art. 131 CNC
        const selecionadasIds = new Set((relatorio.reaproveitaveis.elegiveisArt131 || []).map(x => x.idTarefa));

        modal.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:#1f2937;border-bottom:1px solid #374151;gap:12px;">
                <div>
                    <strong style="font-size:14px;">Argos API — Pesquisas Reaproveitáveis (Art. 131 CNC)</strong>
                    <span style="margin-left:10px;color:#9ca3af;">Processo ${_escapeHtml(relatorio.numeroProcesso)}</span>
                    <span style="margin-left:10px;color:#34d399;">Elegíveis: ${(relatorio.reaproveitaveis.elegiveisArt131 || []).length}</span>
                    <span style="margin-left:10px;color:#60a5fa;">Total API: ${relatorio.reaproveitaveis.carregados}/${relatorio.reaproveitaveis.totalRegistros}</span>
                    <span style="margin-left:10px;color:#fbbf24;">${(relatorio.temposMs.reaproveitaveis / 1000).toFixed(1)}s</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center;">
                    <button id="ar-btn-pdf-sep" style="padding:6px 12px;background:#059669;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:600;">PDFs por Empresa (Pos/Neg) (0)</button>
                    <button id="ar-btn-pdf-uni" style="padding:6px 10px;background:#0d9488;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:600;">1 PDF/Empresa (0)</button>
                    <button id="ar-btn-copy" style="padding:6px 10px;background:#2563eb;color:#fff;border:none;border-radius:5px;cursor:pointer;">Copiar JSON</button>
                    <button id="ar-btn-close" style="padding:6px 10px;background:#dc2626;color:#fff;border:none;border-radius:5px;cursor:pointer;">Fechar</button>
                </div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:10px;padding:10px 16px;background:#182030;border-bottom:1px solid #374151;align-items:center;">
                <label>Modo:
                    <select id="ar-f-modo" style="background:#111827;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;padding:3px 6px;">
                        <option value="art131">Elegíveis Art. 131 CNC (${(relatorio.reaproveitaveis.elegiveisArt131 || []).length})</option>
                        <option value="recentes">Mais recente por Executado × Tipo (${relatorio.reaproveitaveis.maisRecentesPorExecutadoETipo.length})</option>
                        <option value="todos">Todas (${relatorio.reaproveitaveis.carregados})</option>
                    </select>
                </label>
                <label>Executado:
                    <select id="ar-f-doc" style="background:#111827;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;padding:3px 6px;">
                        <option value="">Todos (${docsUnicos.length})</option>
                        ${docsUnicos.map(d => `<option value="${_escapeHtml(d)}">${_escapeHtml(d)}</option>`).join('')}
                    </select>
                </label>
                <label>Tarefa:
                    <select id="ar-f-tarefa" style="background:#111827;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;padding:3px 6px;">
                        <option value="">Todas</option>
                        ${convUnicos.map(c => `<option value="${_escapeHtml(c)}">${_escapeHtml(c)}</option>`).join('')}
                    </select>
                </label>
                <label>Resultado:
                    <select id="ar-f-res" style="background:#111827;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;padding:3px 6px;">
                        <option value="">Todos</option>
                        <option value="pos">Positivo</option>
                        <option value="neg">Negativo</option>
                    </select>
                </label>
                <button id="ar-btn-sel-vis" style="padding:4px 8px;background:#374151;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;cursor:pointer;">Marcar visíveis</button>
                <button id="ar-btn-limpar-sel" style="padding:4px 8px;background:#374151;color:#f3f4f6;border:1px solid #4b5563;border-radius:4px;cursor:pointer;">Limpar seleção</button>
                <span id="ar-f-count" style="margin-left:auto;color:#9ca3af;"></span>
            </div>
            <div id="ar-status-bar" style="display:none;padding:8px 16px;background:#0f172a;color:#93c5fd;border-bottom:1px solid #374151;font-size:12px;"></div>
            <div style="flex:1;overflow:auto;">
                <table style="width:100%;border-collapse:collapse;font-size:12px;">
                    <thead style="position:sticky;top:0;background:#1f2937;">
                        <tr>
                            <th style="text-align:center;padding:7px 8px;border-bottom:1px solid #374151;width:32px;">✓</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">ID</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Executado / Doc</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Tarefa</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Data</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Art. 131</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Resultado</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Anexo</th>
                            <th style="text-align:left;padding:7px 8px;border-bottom:1px solid #374151;">Processo Origem / Vara</th>
                        </tr>
                    </thead>
                    <tbody id="ar-tbody"></tbody>
                </table>
            </div>
        `;

        document.body.appendChild(modal);

        const selModo = modal.querySelector('#ar-f-modo');
        const selDoc = modal.querySelector('#ar-f-doc');
        const selTarefa = modal.querySelector('#ar-f-tarefa');
        const selRes = modal.querySelector('#ar-f-res');
        const tbody = modal.querySelector('#ar-tbody');
        const countEl = modal.querySelector('#ar-f-count');
        const btnPdfSep = modal.querySelector('#ar-btn-pdf-sep');
        const btnPdfUni = modal.querySelector('#ar-btn-pdf-uni');
        const statusBar = modal.querySelector('#ar-status-bar');

        let filtradosAtuais = [];

        function atualizarContadorPdf() {
            btnPdfSep.textContent = 'PDFs por Empresa (Pos/Neg) (' + selecionadasIds.size + ')';
            btnPdfUni.textContent = '1 PDF/Empresa (' + selecionadasIds.size + ')';
        }

        function atualizarTabela() {
            const base = selModo.value === 'art131'
                ? (relatorio.reaproveitaveis.elegiveisArt131 || [])
                : selModo.value === 'recentes'
                    ? relatorio.reaproveitaveis.maisRecentesPorExecutadoETipo
                    : relatorio.reaproveitaveis.todos;

            filtradosAtuais = base.filter(it => {
                if (selDoc.value && it.documentoExecutado !== selDoc.value) return false;
                if (selTarefa.value && it.rotuloTarefa !== selTarefa.value) return false;
                if (selRes.value === 'pos' && !it.resultadoPositivo) return false;
                if (selRes.value === 'neg' && it.resultadoPositivo) return false;
                return true;
            });

            countEl.textContent = 'Exibindo ' + filtradosAtuais.length + ' de ' + base.length;
            tbody.innerHTML = filtradosAtuais.map(it => {
                const av = it.art131 || avaliarElegibilidadeArt131(it);
                return `
                <tr style="border-bottom:1px solid #1f2937;">
                    <td style="text-align:center;padding:6px 8px;">
                        <input type="checkbox" class="ar-chk" data-id="${_escapeHtml(it.idTarefa)}" ${selecionadasIds.has(it.idTarefa) ? 'checked' : ''} />
                    </td>
                    <td style="padding:6px 8px;color:#9ca3af;">${_escapeHtml(it.idTarefa)}</td>
                    <td style="padding:6px 8px;">
                        <div>${_escapeHtml(it.nomeExecutado)}</div>
                        <div style="color:#9ca3af;font-size:11px;">${_escapeHtml(it.documentoExecutado)}</div>
                    </td>
                    <td style="padding:6px 8px;color:#93c5fd;">${_escapeHtml(it.rotuloTarefa)}</td>
                    <td style="padding:6px 8px;white-space:nowrap;">${_escapeHtml(_fmtData(it.dataFinalizacao))}</td>
                    <td style="padding:6px 8px;color:${av.elegivel ? '#34d399' : '#f59e0b'};font-size:11px;" title="${_escapeHtml(av.motivo)}">
                        ${av.elegivel ? '✓ ' : '✗ '}${_escapeHtml(av.regra)}
                    </td>
                    <td style="padding:6px 8px;color:${it.resultadoPositivo ? '#34d399' : '#f87171'};font-weight:600;">
                        ${it.resultadoPositivo ? 'Positivo' : 'Negativo'}
                    </td>
                    <td style="padding:6px 8px;">${it.possuiAnexo ? 'Sim' : 'Não'}</td>
                    <td style="padding:6px 8px;">
                        <div>${_escapeHtml(it.numeroProcessoOrigem)}</div>
                        <div style="color:#9ca3af;font-size:11px;">${_escapeHtml(it.nomeOrgaoJulgador)}</div>
                    </td>
                </tr>
            `;
            }).join('');

            tbody.querySelectorAll('.ar-chk').forEach(chk => {
                chk.addEventListener('change', () => {
                    const id = Number(chk.getAttribute('data-id'));
                    if (chk.checked) selecionadasIds.add(id);
                    else selecionadasIds.delete(id);
                    atualizarContadorPdf();
                });
            });
            atualizarContadorPdf();
        }

        [selModo, selDoc, selTarefa, selRes].forEach(el => el.addEventListener('change', atualizarTabela));

        modal.querySelector('#ar-btn-sel-vis').addEventListener('click', () => {
            for (const it of filtradosAtuais) selecionadasIds.add(it.idTarefa);
            atualizarTabela();
        });
        modal.querySelector('#ar-btn-limpar-sel').addEventListener('click', () => {
            selecionadasIds.clear();
            atualizarTabela();
        });

        async function executarGeracaoPorEmpresa(separarPosNeg) {
            const selecionadas = relatorio.reaproveitaveis.todos.filter(t => selecionadasIds.has(t.idTarefa));
            if (!selecionadas.length) {
                alert('Marque ao menos uma pesquisa na tabela antes de gerar os PDFs.');
                return;
            }
            btnPdfSep.disabled = true;
            btnPdfUni.disabled = true;
            statusBar.style.display = 'block';
            statusBar.style.color = '#93c5fd';
            try {
                const res = await gerarPdfsPorEmpresa(relatorio.numeroProcesso, selecionadas, {
                    separarPositivasNegativas: separarPosNeg,
                    onStatus: msg => { statusBar.textContent = msg; },
                });
                console.log('[ArgosReapApi] PDFs por empresa gerados:', res);
                const nomes = res.arquivos.map(a => a.nomeArquivo + ' (' + a.totalPaginas + 'p)').join(' | ');
                statusBar.style.color = '#34d399';
                statusBar.textContent = 'Pronto! ' + res.totalArquivos + ' PDF(s): ' + nomes;
            } catch (err) {
                console.error('[ArgosReapApi] Erro ao gerar PDFs por empresa:', err);
                statusBar.style.color = '#f87171';
                statusBar.textContent = 'Erro: ' + (err && err.message ? err.message : err);
            } finally {
                btnPdfSep.disabled = false;
                btnPdfUni.disabled = false;
            }
        }

        btnPdfSep.addEventListener('click', () => executarGeracaoPorEmpresa(true));
        btnPdfUni.addEventListener('click', () => executarGeracaoPorEmpresa(false));

        modal.querySelector('#ar-btn-close').addEventListener('click', () => modal.remove());
        modal.querySelector('#ar-btn-copy').addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(JSON.stringify(relatorio, null, 2));
                const btn = modal.querySelector('#ar-btn-copy');
                btn.textContent = 'Copiado!';
                setTimeout(() => { btn.textContent = 'Copiar JSON'; }, 1500);
            } catch (e) {
                console.log('[ArgosReapApi] JSON completo:', relatorio);
            }
        });

        atualizarTabela();
    }

    function montarBotaoFlutuante() {
        if (document.getElementById('argos-reap-api-btn')) return;
        const btn = document.createElement('button');
        btn.id = 'argos-reap-api-btn';
        btn.type = 'button';
        btn.textContent = 'API Reaproveitáveis';
        btn.style.cssText = [
            'position:fixed', 'right:18px', 'bottom:18px', 'z-index:999998',
            'padding:9px 14px', 'background:#1d4ed8', 'color:#fff',
            'border:1px solid #60a5fa', 'border-radius:8px', 'cursor:pointer',
            'font-family:system-ui,sans-serif', 'font-size:13px', 'font-weight:600',
            'box-shadow:0 6px 20px rgba(0,0,0,.35)',
        ].join(';');

        btn.addEventListener('click', async () => {
            const num = extrairNumeroProcessoDaUrl();
            if (!num) {
                alert('Abra um processo no Argos (/argos/home-servidor/processos/...) para consultar.');
                return;
            }
            const original = btn.textContent;
            btn.disabled = true;
            btn.textContent = 'Consultando API...';
            try {
                const rel = await consultarProcessoCompleto(num, {
                    onProgress: p => {
                        btn.textContent = 'API pág ' + p.pagina + '/' + p.qtdPaginas + ' (' + p.carregados + ')...';
                    },
                });
                console.log('[ArgosReapApi] Relatório completo:', rel);
                renderizarModal(rel);
            } catch (err) {
                console.error('[ArgosReapApi] Erro:', err);
                alert('Erro na consulta API: ' + (err && err.message ? err.message : err));
            } finally {
                btn.disabled = false;
                btn.textContent = original;
            }
        });

        document.body.appendChild(btn);
    }

    montarBotaoFlutuante();
    console.log('[ArgosReapApi] v1.1 carregado. Use o botão "API Reaproveitáveis" ou window.ArgosReapApi.');
})();
