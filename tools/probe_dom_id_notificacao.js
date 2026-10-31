/**
 * PJe Probe v5 — o ID da notificação (c3a4c57) e o filtro por idDocumento
 *
 * DESCOBERTA (probe de 30/10/2026):
 *   O envelope ao lado da notificação, na timeline, tem id="doc_c3a4c57".
 *   Esse c3a4c57 é o idUnicoDocumento (chave do documento), que já aparece
 *   no título do documento: "Id c3a4c57 - Notificação.pdf".
 *
 *   E o envelope chama o endpoint de expedientes COM FILTRO:
 *     GET /expedientes?pagina=1&tamanhoPagina=10&instancia=1&idDocumento=495200526
 *     -> resultado:[1]   (só o expediente daquele documento)
 *
 * OBJETIVO deste probe:
 *   A) Verificar se o expediente já traz idUnicoDocumento na listagem
 *      (se trouxer, não precisamos de outra chamada).
 *   B) Testar o filtro ?idDocumento= e o que ele muda.
 *   C) Comparar o que vem do envelope (filtrado) com a listagem completa.
 *
 * Uso: await pjeProbeDomExp5()
 *      await pjeProbeDomExp5('9010617')
 */
(async function pjeProbeDomExp5(idProcessoArg) {
  'use strict';

  const log = (t, ...a) => console.log('%c[PROBE5]', 'color:#0a0;font-weight:bold', t, ...a);
  const warn = (t, ...a) => console.warn('%c[PROBE5]', 'color:#a80;font-weight:bold', t, ...a);

  let idProcesso = idProcessoArg;
  if (!idProcesso) {
    const m = location.pathname.match(/\/processo\/(\d+)/);
    if (m) idProcesso = m[1];
  }
  if (!idProcesso) {
    console.error('[PROBE5] informe o id: pjeProbeDomExp5("9010617")');
    return null;
  }
  log('idProcesso =', idProcesso);

  const api = async (path) => {
    const r = await fetch(new URL(path, location.origin).toString(), {
      credentials: 'include',
      headers: { 'Accept': 'application/json' },
    });
    if (!r.ok) throw new Error(`HTTP ${r.status} em ${path}`);
    return r.json();
  };

  // ---- A) Listagem completa de expedientes -------------------------------
  const expedientes = [];
  for (let p = 1; p <= 50; p++) {
    const j = await api(`/pje-comum-api/api/processos/id/${idProcesso}/expedientes?pagina=${p}&tamanhoPagina=100&instancia=1`);
    const lista = (j && j.resultado) || [];
    expedientes.push(...lista);
    if (lista.length < 100) break;
  }
  log(`expedientes (listagem completa): ${expedientes.length}`);

  const dom = expedientes.filter(e =>
    String(e.meioExpedienteEnum || '').toUpperCase() === 'DOMICILIO_ELETRONICO'
  );
  log(`domicílio eletrônico: ${dom.length}`);

  // ---- A.1) idUnicoDocumento existe na listagem? ------------------------
  console.group('%c A) idUnicoDocumento vem na listagem de expedientes? ', 'background:#046;color:#fff;font-weight:bold');
  const chaves = new Set();
  for (const e of expedientes) Object.keys(e).forEach(k => chaves.add(k));
  const temUid = chaves.has('idUnicoDocumento') || chaves.has('identificadorUnico');
  log('campos disponíveis:', [...chaves].sort().join(', '));
  if (temUid) {
    log('%cSIM%c — o ID já vem na listagem, sem chamada extra.',
      'color:#0a0;font-weight:bold', 'color:inherit');
    console.table(dom.map(e => ({
      empresa: e.nomePessoaParte,
      id: e.id,
      idDocumento: e.idDocumento,
      idUnicoDocumento: e.idUnicoDocumento,
      identificadorUnico: e.identificadorUnico,
      meio: e.meioExpedienteEnum,
    })));
  } else {
    warn('%cNÃO%c — a listagem de expedientes não traz idUnicoDocumento.',
      'color:#a00;font-weight:bold', 'color:inherit');
    warn('   O c3a4c57 deve vir de /documentos/id/{idDocumento}.');
    console.table(dom.map(e => ({
      empresa: e.nomePessoaParte,
      id: e.id,
      idDocumento: e.idDocumento,
      meio: e.meioExpedienteEnum,
    })));
  }
  console.groupEnd();

  // ---- B) Filtro ?idDocumento= (o que o envelope usa) -------------------
  console.group('%c B) Filtro ?idDocumento= — o que o envelope dispara ', 'background:#640;color:#fff;font-weight:bold');
  for (const e of dom) {
    if (e.idDocumento == null) continue;
    const j = await api(`/pje-comum-api/api/processos/id/${idProcesso}/expedientes?pagina=1&tamanhoPagina=10&instancia=1&idDocumento=${e.idDocumento}`);
    const lista = (j && j.resultado) || [];
    console.group(`${e.nomePessoaParte} | idDocumento=${e.idDocumento} -> ${lista.length} resultado(s)`);
    if (lista.length) {
      const x = lista[0];
      console.log('campos:', Object.keys(x).join(', '));
      console.log('idUnicoDocumento =', x.idUnicoDocumento, '| identificadorUnico =', x.identificadorUnico);
      console.log('objeto:', x);
    }
    console.groupEnd();
  }
  console.groupEnd();

  // ---- C) /documentos/id/{idDocumento} -> de onde sai o c3a4c57 ---------
  console.group('%c C) /documentos/id/{idDocumento} — fonte do c3a4c57 ', 'background:#404;color:#fff;font-weight:bold');
  const uids = [];
  for (const e of dom) {
    if (e.idDocumento == null) continue;
    try {
      const d = await api(`/pje-comum-api/api/processos/id/${idProcesso}/documentos/id/${e.idDocumento}?incluirAssinatura=false&incluirAnexos=false`);
      console.group(`${e.nomePessoaParte} | idDocumento=${e.idDocumento}`);
      console.log('titulo        :', d.titulo);
      console.log('idUnicoDocumento:', d.idUnicoDocumento);
      console.log('identificadorUnico:', d.identificadorUnico);
      console.log('idBin         :', d.idBin);
      console.log('md5           :', d.md5);
      console.groupEnd();
      uids.push({
        empresa: e.nomePessoaParte,
        idExpediente: e.id,
        idProcessoExpediente: e.idProcessoExpediente,
        idDocumento: e.idDocumento,
        idUnicoDocumento: d.idUnicoDocumento,
        titulo: d.titulo,
        identificadorUnico: d.identificadorUnico,
      });
    } catch (ex) {
      warn(`falha /documentos/${e.idDocumento}: ${ex.message}`);
    }
  }
  console.groupEnd();

  // ---- D) O seletor da timeline: #doc_<uid> -----------------------------
  console.group('%c D) Seletores #doc_ na timeline (confirmação no DOM) ', 'background:#046;color:#fff;font-weight:bold');
  const noDom = [...document.querySelectorAll('[id^="doc_"]')].map(el => ({
    id: el.id,
    uid: el.id.replace(/^doc_/, ''),
    title: el.getAttribute('title') || '',
    texto: (el.textContent || '').trim().slice(0, 80),
  }));
  if (noDom.length) console.table(noDom);
  else warn('Nenhum #doc_ encontrado no DOM atual (a timeline pode não estar renderizada).');
  console.groupEnd();

  // ---- E) Resumo ---------------------------------------------------------
  console.group('%c RESUMO ', 'background:#046;color:#fff;font-weight:bold');
  console.table(uids.map(u => ({
    empresa: u.empresa,
    idDocumento: u.idDocumento,
    idUnicoDocumento: u.idUnicoDocumento,
    titulo: (u.titulo || '').slice(0, 40),
    seletor: u.idUnicoDocumento ? `#doc_${u.idUnicoDocumento}` : '(sem uid)',
  })));

  const completa = uids.filter(u => u.idUnicoDocumento).length;
  log(`${completa}/${uids.length} com idUnicoDocumento (o "c3a4c57")`);

  const doMenu = [...chaves].some(k => /unico|identificador/i.test(k));
  if (doMenu) {
    log('%cCONCLUSÃO: dá para pegar tudo em 1 chamada — /expedientes já traz o uid.',
      'color:#0a0;font-weight:bold');
  } else {
    log('%cCONCLUSÃO: precisa de 2 chamadas — /expedientes + /documentos/id/{idDocumento}.',
      'color:#a80;font-weight:bold');
  }
  console.groupEnd();

  const pacote = { idProcesso, dom, uids, camposExpediente: [...chaves].sort(), docUidNaListagem: doMenu };
  try { copy(JSON.stringify(pacote, null, 2)); log('JSON copiado.'); } catch (_) {}
  return pacote;
})();
