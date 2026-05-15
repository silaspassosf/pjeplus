/**
 * Bookmarklet — Fase Conhecimento + chips DOM (274/275/302) + audiência
 *
 * Fluxo confirmado pelo spy (Angular faz exatamente isso):
 *   1. PATCH /agrupamentotarefas/processos/todos {subCaixa:null, faseProcessualString:['Conhecimento']}
 *      subCaixa com nomes nao eh filtro server-side neste endpoint.
 *   2. POST /etiquetas/etiquetasprocessos {idsProcesso:[...]} (paralelo por lote)
 *   3. Filtro client-side: chips 274/275/302 + tarefa/data com audiencia
 */

(async function domFlowApiReal() {
  var BASE = location.origin;
  var TAM = 100;
  var CHIP_IDS = [274, 275, 302];

  var HEADERS = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    'X-Grau-Instancia': '1'
  };

  var xsrfCookie = (document.cookie.split(';').map(function(c) { return c.trim(); })
    .find(function(c) { return c.toLowerCase().indexOf('xsrf-token=') === 0; }) || '').split('=').slice(1).join('=');
  if (xsrfCookie) HEADERS['X-XSRF-TOKEN'] = decodeURIComponent(xsrfCookie);

  function cnj(proc) { return proc.numeroProcesso || proc.numero || ''; }

  function temAudiencia(proc) {
    if (proc.dataProximaAudiencia) return true;
    var t = (proc.tarefa || '').toLowerCase();
    return t.indexOf('audi\u00eancia') >= 0 || t.indexOf('audiencia') >= 0;
  }

  async function copiar(text) {
    try { await navigator.clipboard.writeText(text); return; } catch (e) {}
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px';
    document.body.appendChild(ta); ta.focus(); ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
  }

  async function buscarPagina(pagina) {
    var resp = await fetch(BASE + '/pje-comum-api/api/agrupamentotarefas/processos/todos', {
      method: 'PATCH', credentials: 'include', headers: HEADERS,
      body: JSON.stringify({
        pagina: pagina, tamanhoPagina: TAM,
        subCaixa: null, tipoAtividade: null, processos: null,
        nomeConclusoMagistrado: null, usuarioResponsavel: null,
        faseProcessualString: ['Conhecimento'], numeroProcesso: null
      })
    });
    if (!resp.ok) throw new Error('PATCH /processos/todos -> HTTP ' + resp.status);
    var d = await resp.json();
    return { lista: d.resultado || [], total: d.totalRegistros || 0 };
  }

  async function buscarEtiquetasLote(ids) {
    var resp = await fetch(BASE + '/pje-etiquetas-api/api/etiquetas/etiquetasprocessos', {
      method: 'POST', credentials: 'include', headers: HEADERS,
      body: JSON.stringify({ idsProcesso: ids })
    });
    if (!resp.ok) return [];
    return await resp.json();
  }

  console.group('DOM Flow — Conhecimento + chips 274/275/302 + audiencia');

  try {
    // Passo 1: p1 para saber o total, depois todas as paginas restantes em paralelo
    var p1 = await buscarPagina(1);
    var totalRegistros = p1.total;
    var totalPaginas = totalRegistros > 0 ? Math.ceil(totalRegistros / TAM) : 1;
    console.log('[p1] ' + p1.lista.length + ' / ' + totalRegistros + ' (total ' + totalPaginas + ' pags)');

    var extras = [];
    for (var pag = 2; pag <= totalPaginas; pag += 1) extras.push(buscarPagina(pag));
    var demais = await Promise.all(extras);

    var todos = [p1].concat(demais).reduce(function(acc, r) {
      return acc.concat(r.lista.filter(temAudiencia));
    }, []);

    console.log('Com audiencia: ' + todos.length + ' / ' + totalRegistros + ' em Conhecimento');

    if (!todos.length) {
      alert('DOM Flow — 0 processos com audiencia em Conhecimento');
      console.groupEnd(); return;
    }

    var lotes = [];
    for (var i = 0; i < todos.length; i += 100) {
      lotes.push(todos.slice(i, i + 100).map(function(p) { return p.id; }));
    }
    console.log('Etiquetas: ' + lotes.length + ' lotes em paralelo...');

    var resultados = await Promise.all(lotes.map(buscarEtiquetasLote));
    var mapa = {};
    resultados.forEach(function(lista) {
      lista.forEach(function(item) {
        mapa[item.idProcesso] = (item.etiquetas || []).map(function(e) { return e.id; });
      });
    });

    var filtrados = todos.filter(function(p) {
      var chips = mapa[p.id] || [];
      return chips.some(function(id) { return CHIP_IDS.indexOf(id) >= 0; });
    });

    console.log('Com chips 274/275/302: ' + filtrados.length + ' / ' + todos.length);

    if (!filtrados.length) {
      alert('DOM Flow — 0 processos com chips DOM + audiencia');
      console.groupEnd(); return;
    }

    console.table(filtrados.slice(0, 200).map(function(p) {
      return {
        id: p.id, numero: cnj(p),
        classe: (p.classeJudicial || {}).sigla || p.classeJudicial || '',
        tarefa: (p.tarefa || '').replace(/\s+/g, ' ').trim().slice(0, 40),
        audiencia: p.dataProximaAudiencia || '',
        chips: (mapa[p.id] || []).filter(function(id) { return CHIP_IDS.indexOf(id) >= 0; }).join(',')
      };
    }));

    var cnjs = filtrados.map(cnj).filter(Boolean).join('\n');
    await copiar(cnjs);
    console.log('\nCNJs (' + filtrados.length + '):\n' + cnjs);
    console.groupEnd();
    alert('DOM Flow — ' + filtrados.length + ' processos (chips DOM + audiencia)\nCNJs copiados — ver console F12');
  } catch (e) {
    console.error('Falha:', e.message);
    console.groupEnd();
    alert('DOM Flow — Falhou\n' + e.message);
  }
})();
