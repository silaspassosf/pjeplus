/*
  pet.js
  Busca direta de peticoes do escaninho sem clique em UI.

  Uso no console:
    await pjePeticoes.buscarPeticoesEscaninhoDireto();
    await pjePeticoes.buscarPeticoesEscaninhoDireto({ tamanhoPagina: 100, maxPaginas: 20 });
*/

(async function () {
  'use strict';

  function getCookie(name) {
    var parts = document.cookie ? document.cookie.split(';') : [];
    var needle = String(name || '').toLowerCase() + '=';
    for (var i = 0; i < parts.length; i += 1) {
      var part = parts[i].trim();
      if (part.toLowerCase().indexOf(needle) === 0) {
        return decodeURIComponent(part.slice(needle.length));
      }
    }
    return null;
  }

  function toQuery(params) {
    var qs = new URLSearchParams();
    Object.keys(params || {}).forEach(function (k) {
      var v = params[k];
      if (v !== undefined && v !== null && v !== '') {
        qs.append(k, String(v));
      }
    });
    return qs.toString();
  }

  function asArray(payload) {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.resultado)) return payload.resultado;
    if (Array.isArray(payload.dados)) return payload.dados;
    if (payload.resultado && Array.isArray(payload.resultado.conteudo)) return payload.resultado.conteudo;
    if (payload.dados && Array.isArray(payload.dados.conteudo)) return payload.dados.conteudo;
    if (payload.conteudo && Array.isArray(payload.conteudo)) return payload.conteudo;
    if (payload.items && Array.isArray(payload.items)) return payload.items;
    return [];
  }

  function pick() {
    for (var i = 0; i < arguments.length; i += 1) {
      var val = arguments[i];
      if (val !== undefined && val !== null && val !== '') return val;
    }
    return null;
  }

  function cleanText(value) {
    if (value === undefined || value === null) return null;
    var text = String(value).replace(/\s+/g, ' ').trim();
    return text || null;
  }

  function isNumericLike(value) {
    var text = cleanText(value);
    if (!text) return false;
    return /^\d+$/.test(text);
  }

  function pickTextual() {
    for (var i = 0; i < arguments.length; i += 1) {
      var text = cleanText(arguments[i]);
      if (!text) continue;
      if (isNumericLike(text)) continue;
      return text;
    }
    return null;
  }

  function deepFindValueByKeyVariants(source, variants, maxDepth) {
    if (!source || !variants || !variants.length) return null;

    var queue = [{ value: source, depth: 0 }];
    var visited = new Set();
    var normalizedVariants = variants.map(function (v) { return String(v).toLowerCase(); });

    while (queue.length) {
      var current = queue.shift();
      if (!current || current.depth > maxDepth) continue;

      var node = current.value;
      if (!node || typeof node !== 'object') continue;
      if (visited.has(node)) continue;
      visited.add(node);

      if (Array.isArray(node)) {
        for (var ai = 0; ai < node.length; ai += 1) {
          queue.push({ value: node[ai], depth: current.depth + 1 });
        }
        continue;
      }

      var keys = Object.keys(node);

      for (var ki = 0; ki < keys.length; ki += 1) {
        var key = keys[ki];
        var lowered = key.toLowerCase();
        var isMatch = normalizedVariants.some(function (v) {
          return lowered === v || lowered.indexOf(v) >= 0;
        });

        if (!isMatch) continue;

        var val = node[key];
        if (val === undefined || val === null) continue;

        if (typeof val === 'string' && val.trim()) return val.trim();
        if (typeof val === 'number' || typeof val === 'boolean') return String(val);
        // Matched key holds an object — check common description sub-fields immediately
        if (val && typeof val === 'object' && !Array.isArray(val)) {
          var _subs = ['descricao', 'nome', 'label', 'rotulo', 'texto', 'descricaoCompleta'];
          for (var si = 0; si < _subs.length; si++) {
            var _sub = val[_subs[si]];
            if (_sub && typeof _sub === 'string' && _sub.trim()) return _sub.trim();
          }
        }
      }

      for (var kj = 0; kj < keys.length; kj += 1) {
        queue.push({ value: node[keys[kj]], depth: current.depth + 1 });
      }
    }

    return null;
  }

  function normalizeItem(raw) {
    var proc = raw && (raw.processo || raw.processoJudicial || raw.dadosProcesso) || {};
    var tarefaObj = raw && (raw.tarefa || raw.tarefaAtual || raw.atividade) || {};
    var parteObj = raw && (raw.parte || raw.peticionante || raw.poloPeticionante) || {};

    var numeroApiProfundo = deepFindValueByKeyVariants(raw, [
      'numeroProcesso', 'nrProcesso', 'processoNumero', 'numero'
    ], 6);

    var numero = pick(
      proc.numero,
      proc.numeroProcesso,
      raw.numeroProcesso,
      raw.nrProcesso,
      raw.processoNumero,
      numeroApiProfundo
    );

    if (numero && String(numero).indexOf('-') < 0) {
      var match = extractNumeroProcesso(String(numero));
      if (match) numero = match;
    }

    var tipoApiProfundo = deepFindValueByKeyVariants(raw, [
      'descricaoTipoPeticao', 'nomeTipoPeticao', 'tipoPeticaoDescricao', 'descricaoTipoDocumento',
      'nomeTipoDocumento', 'tipoDocumentoDescricao', 'classeDocumentoDescricao', 'nomeTipo',
      'labelTipoPeticao', 'labelTipoDocumento', 'tipoPeticao', 'tipoDocumento', 'tipo', 'classeDocumento'
    ], 6);

    var descricaoApiProfunda = deepFindValueByKeyVariants(raw, [
      'descricaoPeticao', 'descricaoDocumento', 'documentoDescricao', 'descricao', 'nomeDocumento', 'assunto', 'resumo'
    ], 6);

    var parteApiProfunda = deepFindValueByKeyVariants(raw, [
      'nomePeticionante', 'nomeParte', 'nomePessoa'
    ], 4);

    var tarefaApiProfunda = deepFindValueByKeyVariants(raw, [
      'nomeTarefa', 'tarefa', 'descricaoTarefa', 'atividade'
    ], 6);

    var faseApiProfunda = deepFindValueByKeyVariants(raw, [
      'nomeFase', 'fase', 'descricaoFase'
    ], 6);

    var dataApiProfunda = deepFindValueByKeyVariants(raw, [
      'dataJuntada', 'dataCadastro', 'dataCriacao', 'dataInclusao', 'instanteCriacao', 'data'
    ], 6);

    var descricao = pick(
      raw.descricao,
      raw.descricaoPeticao,
      raw.tipoPeticao,
      raw.assunto,
      raw.nomeDocumento,
      raw.documentoDescricao,
      descricaoApiProfunda
    );

    // parte: polo + papel combinados — ex: "Ativo (Advogado)", "Terceiro (Perito)"
    var _poloLabel = null;
    if (raw.poloPeticionante && typeof raw.poloPeticionante === 'string') {
      var _pp = raw.poloPeticionante.trim();
      if (/\bativo\b/i.test(_pp))           _poloLabel = 'Ativo';
      else if (/\bpassivo\b/i.test(_pp))    _poloLabel = 'Passivo';
      else if (/\bterceiros?\b/i.test(_pp)) _poloLabel = 'Terceiro';
      else _poloLabel = _pp;
    }
    var _papelLabel = (raw.nomePapelUsuarioDocumento && String(raw.nomePapelUsuarioDocumento).trim()) || null;
    var parte = _poloLabel && _papelLabel ? _poloLabel + ' (' + _papelLabel + ')'
               : _poloLabel || _papelLabel || null;


    // tipoPeticao — nomeTipoProcessoDocumento é o campo confirmado pela API
    var candidatoTipoPeticaoTemporario = pickTextual(
      raw.nomeTipoProcessoDocumento,
      raw.nomeTipoPeticao,
      raw.descricaoTipoPeticao,
      raw.tipoDocumentoDescricao,
      raw.tipoOrigemDocumento,
      raw.tipoPeticao,
      tipoApiProfundo
    );

    var tarefa = pick(
      tarefaObj.nome,
      tarefaObj.descricao,
      raw.tarefa,
      raw.nomeTarefa,
      tarefaApiProfunda
    );

    var fase = pick(
      raw.faseProcessual,
      raw.fase,
      raw.nomeFase,
      proc.fase,
      proc.nomeFase,
      faseApiProfunda
    );

    var dataJuntada = pick(
      raw.dataJuntada,
      raw.dataCadastro,
      raw.dataCriacao,
      raw.dataInclusao,
      raw.instanteCriacao,
      dataApiProfunda
    );

    return {
      numeroProcesso: numero,
      tipoPeticao: candidatoTipoPeticaoTemporario,
      descricao: descricao,
      parte: parte,
      tarefa: tarefa,
      fase: fase,
      dataJuntada: dataJuntada,
      idProcesso: pick(proc.id, proc.idProcesso, raw.idProcesso),
      idItem: pick(raw.id, raw.idPeticao, raw.idDocumento),
      bruto: raw
    };
  }

  function extractNumeroProcesso(text) {
    var m = String(text || '').match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
    return m ? m[0] : null;
  }


  async function doFetch(url, xsrfToken) {
    var response = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'X-XSRF-TOKEN': xsrfToken || ''
      }
    });

    var text = await response.text();
    var json = null;

    try {
      json = text ? JSON.parse(text) : null;
    } catch (e) {
      json = null;
    }

    return {
      ok: response.ok,
      status: response.status,
      url: url,
      body: json,
      bodyText: text
    };
  }

  function readTotalPages(payload, currentPage, pageSize, currentLength) {
    var p = payload || {};

    var candidates = [
      p.totalPaginas,
      p.quantidadePaginas,
      p.totalPaginasResultado,
      p.resultado && p.resultado.totalPaginas,
      p.dados && p.dados.totalPaginas,
      p.paginacao && p.paginacao.totalPaginas,
      p.meta && p.meta.totalPaginas
    ];

    for (var i = 0; i < candidates.length; i += 1) {
      var n = Number(candidates[i]);
      if (Number.isFinite(n) && n > 0) return n;
    }

    if (currentLength < pageSize) return currentPage;
    return currentPage + 1;
  }

  function buildCandidates(origin) {
    return [
      {
        nome: 'escaninhos_peticoesjuntadas',
        path: '/pje-comum-api/api/escaninhos/peticoesjuntadas',
        extraParams: {}
      },
      {
        nome: 'escaninhos_peticoes_juntadas',
        path: '/pje-comum-api/api/escaninhos/peticoes-juntadas',
        extraParams: {}
      },
      {
        nome: 'escaninhos_peticoes',
        path: '/pje-comum-api/api/escaninhos/peticoes',
        extraParams: {}
      },
      {
        nome: 'escaninhos_documentosinternos_flag_peticoesjuntadas',
        path: '/pje-comum-api/api/escaninhos/documentosinternos',
        extraParams: { peticoesJuntadas: true }
      },
      {
        nome: 'escaninhos_documentosinternos_flag_peticoesnaoapreciadas',
        path: '/pje-comum-api/api/escaninhos/documentosinternos',
        extraParams: { peticoesNaoApreciadas: true }
      }
    ].map(function (c) {
      return {
        nome: c.nome,
        baseUrl: origin + c.path,
        extraParams: c.extraParams
      };
    });
  }

  async function tryCandidate(candidate, opts, xsrfToken) {
    var page = Number(opts.paginaInicial || 1);
    var pageSize = Number(opts.tamanhoPagina || 50);
    var maxPaginas = Number(opts.maxPaginas || 100);

    var allRaw = [];
    var trace = [];

    for (var i = 0; i < maxPaginas; i += 1) {
      var params = Object.assign({}, candidate.extraParams, {
        pagina: page,
        tamanhoPagina: pageSize,
        ordenacaoCrescente: !!opts.ordenacaoCrescente
      });

      var url = candidate.baseUrl + '?' + toQuery(params);
      var res = await doFetch(url, xsrfToken);

      var list = asArray(res.body);
      trace.push({
        pagina: page,
        status: res.status,
        ok: res.ok,
        quantidade: list.length,
        url: url
      });

      if (!res.ok) {
        return {
          sucesso: false,
          candidato: candidate.nome,
          erro: 'HTTP_' + String(res.status),
          trace: trace,
          totalBruto: allRaw.length,
          dados: []
        };
      }

      if (!list.length) {
        break;
      }

      allRaw = allRaw.concat(list);

      var totalPages = readTotalPages(res.body, page, pageSize, list.length);
      if (page >= totalPages) break;

      page += 1;
    }

    var normalized = allRaw.map(normalizeItem);

    return {
      sucesso: normalized.length > 0,
      candidato: candidate.nome,
      erro: normalized.length > 0 ? null : 'SEM_DADOS',
      trace: trace,
      totalBruto: allRaw.length,
      dados: normalized
    };
  }

  async function buscarPeticoesEscaninhoDireto(options) {
    var opts = Object.assign({
      paginaInicial: 1,
      tamanhoPagina: 50,
      maxPaginas: 100,
      ordenacaoCrescente: true,
      debug: true,
      logLimite: null
    }, options || {});

    var origin = window.location.origin;
    var xsrfToken = getCookie('XSRF-TOKEN');

    var candidates = buildCandidates(origin);
    var tentativas = [];

    for (var i = 0; i < candidates.length; i += 1) {
      var result = await tryCandidate(candidates[i], opts, xsrfToken);
      tentativas.push(result);
      if (result.sucesso) {
        var output = {
          sucesso: true,
          endpointUsado: result.candidato,
          total: result.dados.length,
          parametros: {
            paginaInicial: opts.paginaInicial,
            tamanhoPagina: opts.tamanhoPagina,
            maxPaginas: opts.maxPaginas,
            ordenacaoCrescente: opts.ordenacaoCrescente,
            logLimite: opts.logLimite
          },
          trace: result.trace,
          dados: result.dados,
          tentativas: tentativas.map(function (t) {
            return {
              candidato: t.candidato,
              sucesso: t.sucesso,
              erro: t.erro,
              totalBruto: t.totalBruto
            };
          })
        };

        if (opts.debug) {
          console.log('[pet.js] endpoint usado:', output.endpointUsado);
          console.log('[pet.js] total:', output.total);

          var limit = (opts.logLimite === null || opts.logLimite === undefined)
            ? output.dados.length
            : Math.max(0, Number(opts.logLimite || 0));

          console.table(output.dados.slice(0, limit).map(function (d) {
            return {
              numeroProcesso: d.numeroProcesso,
              tipoPeticao: d.tipoPeticao,
              descricao: d.descricao,
              parte: d.parte,
              tarefa: d.tarefa,
              fase: d.fase,
              dataJuntada: d.dataJuntada
            };
          }));
        }

        return output;
      }
    }

    return {
      sucesso: false,
      erro: 'NENHUM_ENDPOINT_RETORNOU_DADOS',
      parametros: {
        paginaInicial: opts.paginaInicial,
        tamanhoPagina: opts.tamanhoPagina,
        maxPaginas: opts.maxPaginas,
        ordenacaoCrescente: opts.ordenacaoCrescente
      },
      tentativas: tentativas,
      sugestao: 'Abra a tela de peticoes juntadas e confirme se a sessao/autorizacao esta ativa.'
    };
  }

  window.pjePeticoes = {
    buscarPeticoesEscaninhoDireto: buscarPeticoesEscaninhoDireto
  };

  return await buscarPeticoesEscaninhoDireto();
})();
