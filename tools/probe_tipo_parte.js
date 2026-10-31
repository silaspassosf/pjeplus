/**
 * PJe Probe v7 — campo de TIPO da parte na API (para PJDP sem nome)
 *
 * A triagem classifica PJDP por keyword no nome (_PJDP_NOME_KEYWORDS), nao por
 * campo da API. Precisamos do CAMPO.
 *
 * Endpoint usado pela propria triagem (bianca/triagem/coleta.py:551):
 *   GET /pje-comum-api/api/processos/id/{id}/partes?retornaEndereco=true
 *   -> { ATIVO: [...], PASSIVO: [...] }
 *
 * Este probe mostra, por parte do PASSIVO, todos os campos e destaca os que
 * podem indicar ente publico.
 *
 * Uso: await pjeProbeTipoParte()
 *      await pjeProbeTipoParte('9010617')
 */
(async function pjeProbeTipoParte(idProcessoArg) {
  'use strict';

  const log = (t, ...a) => console.log('%c[TIPO]', 'color:#0a0;font-weight:bold', t, ...a);
  const warn = (t, ...a) => console.warn('%c[TIPO]', 'color:#a80;font-weight:bold', t, ...a);

  let idProcesso = idProcessoArg;
  if (!idProcesso) {
    const m = location.pathname.match(/\/processo\/(\d+)/);
    if (m) idProcesso = m[1];
  }
  if (!idProcesso) {
    console.error('[TIPO] informe o id: pjeProbeTipoParte("9010617")');
    return null;
  }

  const url = `/pje-comum-api/api/processos/id/${idProcesso}/partes?retornaEndereco=true`;
  const r = await fetch(new URL(url, location.origin).toString(), {
    credentials: 'include', headers: { 'Accept': 'application/json' },
  });
  if (!r.ok) { console.error('[TIPO] HTTP', r.status); return null; }
  const dados = await r.json();
  log('idProcesso =', idProcesso);

  const ativos = dados.ATIVO || [];
  const passivos = dados.PASSIVO || [];
  log(`ATIVO: ${ativos.length} | PASSIVO: ${passivos.length}`);

  const todos = [...ativos, ...passivos];
  if (!todos.length) { warn('nenhuma parte'); return null; }

  // ---- 1. Todos os campos ----------------------------------------------
  const campos = new Set();
  for (const p of todos) Object.keys(p).forEach(k => campos.add(k));
  log('CAMPOS DISPONIVEIS:', [...campos].sort().join(', '));

  // ---- 2. Objeto completo do PASSIVO -----------------------------------
  console.group('%c PASSIVO - objeto completo ', 'background:#046;color:#fff;font-weight:bold');
  for (const p of passivos) {
    console.group(`${p.nome || '?'}  (doc=${p.documento || '-'})`);
    console.log(JSON.parse(JSON.stringify(p)));
    console.groupEnd();
  }
  console.groupEnd();

  // ---- 3. Campos categoricos (poucos valores distintos) ----------------
  console.group('%c CAMPOS CATEGORICOS (candidatos a tipo) ', 'background:#640;color:#fff;font-weight:bold');
  const dist = {};
  for (const p of todos) {
    for (const [k, v] of Object.entries(p)) {
      if (v === null || v === undefined || typeof v === 'object') continue;
      if (!dist[k]) dist[k] = new Set();
      dist[k].add(String(v));
    }
  }
  const candidatos = [];
  for (const [campo, vals] of Object.entries(dist)) {
    const arr = [...vals];
    if (arr.length <= 8 && arr.every(v => v.length <= 50)) {
      candidatos.push({ campo, n_valores: arr.length, valores: arr.join(' | ') });
    }
  }
  console.table(candidatos);
  console.groupEnd();

  // ---- 4. Busca por valores que indiquem ente publico ------------------
  console.group('%c VALORES COM "publico/orgao/ente/poder" ', 'background:#404;color:#fff;font-weight:bold');
  const achados = [];
  const varrer = (obj, caminho, nome) => {
    if (!obj || typeof obj !== 'object') return;
    for (const [k, v] of Object.entries(obj)) {
      const novo = caminho ? `${caminho}.${k}` : k;
      if (typeof v === 'string' && /public|órgão|orgao|ente\b|poder|fazend|uni[aã]o|municip/i.test(v)) {
        achados.push({ nome: (nome || '').slice(0, 35), campo: novo, valor: String(v).slice(0, 60) });
      }
      if (v && typeof v === 'object' && !Array.isArray(v)) varrer(v, novo, nome);
    }
  };
  for (const p of todos) varrer(p, '', p.nome);
  if (achados.length) console.table(achados);
  else warn('Nenhum campo com valor indicando ente publico.');
  console.groupEnd();

  // ---- 5. PASSIVO resumido: nome + campos de tipo + documento ----------
  console.group('%c PASSIVO RESUMIDO ', 'background:#046;color:#fff;font-weight:bold');
  console.table(passivos.map(p => {
    const o = { nome: (p.nome || '').slice(0, 40), documento: p.documento };
    for (const c of ['tipo', 'tipoParte', 'natureza', 'idTipoParte', 'descricaoTipoParte',
                     'tipoPessoa', 'id', 'idPessoa', 'polo', 'grau']) {
      if (c in p) o[c] = p[c];
    }
    return o;
  }));
  console.groupEnd();

  const pacote = { idProcesso, campos: [...campos].sort(), ativos, passivos };
  try { copy(JSON.stringify(pacote, null, 2)); log('JSON copiado.'); } catch (_) {}
  return pacote;
})();
