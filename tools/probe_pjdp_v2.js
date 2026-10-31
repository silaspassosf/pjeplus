/**
 * PJe Probe v8 — PJDP pela API de partes (campo idPessoa)
 *
 * A documentacao (api/apis.md secao 4) confirma que /partes retorna:
 *   { ATIVO: [...], PASSIVO: [...], TERCEIROS: [...] }
 *   cada parte: idPessoa, nome, documento (CPF/CNPJ), representantes, pessoaFisica
 *
 * NAO existe campo de tipo/natureza na documentacao. Mas idPessoa permite
 * consultar o cadastro de pessoas do PJe, que distingue PF de PJ e marca
 * orgao publico.
 *
 * Este probe:
 *   1. Lista o PASSIVO com os campos documentados (idPessoa, nome, documento).
 *   2. Testa /pessoas/{idPessoa} — cadastro da pessoa.
 *   3. Testa /pessoas/juridicas?cnpj= — cadastro de PJ publica.
 *   4. Mostra o objeto completo de cada resposta para achar o campo de tipo.
 *
 * Uso: await pjeProbePJDP2()
 *      await pjeProbePJDP2('9010617')
 */
(async function pjeProbePJDP2(idProcessoArg) {
  'use strict';

  const log = (t, ...a) => console.log('%c[PJDP2]', 'color:#0a0;font-weight:bold', t, ...a);
  const warn = (t, ...a) => console.warn('%c[PJDP2]', 'color:#a80;font-weight:bold', t, ...a);

  let idProcesso = idProcessoArg;
  if (!idProcesso) {
    const m = location.pathname.match(/\/processo\/(\d+)/);
    if (m) idProcesso = m[1];
  }
  if (!idProcesso) {
    console.error('[PJDP2] informe o id: pjeProbePJDP2("9010617")');
    return null;
  }

  const get = async (path) => {
    const r = await fetch(new URL(path, location.origin).toString(), {
      credentials: 'include', headers: { 'Accept': 'application/json' },
    });
    let body = null;
    try { body = await r.json(); } catch (_) { body = '(nao-json)'; }
    return { status: r.status, ok: r.ok, body };
  };

  // ---- 1. /partes -------------------------------------------------------
  const pr = await get(`/pje-comum-api/api/processos/id/${idProcesso}/partes`);
  if (!pr.ok) { console.error('[PJDP2] /partes HTTP', pr.status); return null; }
  const partes = pr.body;
  const passivos = partes.PASSIVO || [];
  const ativos = partes.ATIVO || [];
  log(`idProcesso=${idProcesso} | ATIVO=${ativos.length} PASSIVO=${passivos.length}`);

  console.group('%c PASSIVO (campos documentados) ', 'background:#046;color:#fff;font-weight:bold');
  console.table(passivos.map(p => ({
    idPessoa: p.idPessoa,
    nome: (p.nome || '').slice(0, 40),
    documento: p.documento,
    temPessoaFisica: !!p.pessoaFisica,
    n_representantes: (p.representantes || []).length,
  })));
  console.groupEnd();

  // objeto completo de um PASSIVO, para ver TODOS os campos reais
  if (passivos.length) {
    console.group('%c OBJETO COMPLETO - 1o PASSIVO ', 'background:#404;color:#fff;font-weight:bold');
    console.log(JSON.parse(JSON.stringify(passivos[0])));
    console.groupEnd();
  }

  // ---- 2. /pessoas/{idPessoa} -------------------------------------------
  console.group('%c /pessoas/{idPessoa} ', 'background:#640;color:#fff;font-weight:bold');
  for (const p of passivos.slice(0, 8)) {
    if (!p.idPessoa) { warn(`sem idPessoa: ${p.nome}`); continue; }
    const r = await get(`/pje-comum-api/api/pessoas/${p.idPessoa}`);
    console.group(`${(p.nome || '').slice(0, 40)} | idPessoa=${p.idPessoa} -> HTTP ${r.status}`);
    if (r.ok) console.log(r.body);
    else warn('falhou');
    console.groupEnd();
  }
  console.groupEnd();

  // ---- 3. /pessoas/juridicas?cnpj= --------------------------------------
  console.group('%c /pessoas/juridicas?cnpj= (cadastro PJ publica) ', 'background:#046;color:#fff;font-weight:bold');
  for (const p of passivos.slice(0, 8)) {
    const doc = (p.documento || '').replace(/\D/g, '');
    if (doc.length !== 14) { log(`  ${(p.nome || '').slice(0, 35)}: sem CNPJ (doc=${p.documento})`); continue; }
    const cnpjFmt = doc.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
    const r = await get(`/pje-comum-api/api/pessoas/juridicas?cnpj=${encodeURIComponent(cnpjFmt)}`);
    const resumo = r.ok && r.body
      ? (Array.isArray(r.body) ? `${r.body.length} resultado(s)` : JSON.stringify(r.body).slice(0, 200))
      : `HTTP ${r.status}`;
    console.log(`  ${(p.nome || '').slice(0, 35)} | ${cnpjFmt} -> ${resumo}`);
    if (r.ok && r.body && (!Array.isArray(r.body) || r.body.length)) {
      console.log('     ', r.body);
    }
  }
  console.groupEnd();

  // ---- 4. Campos categóricos do PASSIVO ---------------------------------
  console.group('%c CAMPOS CATEGORICOS DO PASSIVO ', 'background:#404;color:#fff;font-weight:bold');
  const dist = {};
  for (const p of passivos) {
    for (const [k, v] of Object.entries(p)) {
      if (v === null || v === undefined || typeof v === 'object') continue;
      if (!dist[k]) dist[k] = new Set();
      dist[k].add(String(v));
    }
  }
  const linhas = [];
  for (const [campo, vals] of Object.entries(dist)) {
    const arr = [...vals];
    if (arr.length <= 6 && arr.every(v => v.length <= 45)) {
      linhas.push({ campo, n: arr.length, valores: arr.join(' | ') });
    }
  }
  console.table(linhas);
  console.groupEnd();

  const pacote = { idProcesso, partes };
  try { copy(JSON.stringify(pacote, null, 2)); log('JSON copiado.'); } catch (_) {}
  return pacote;
})();
