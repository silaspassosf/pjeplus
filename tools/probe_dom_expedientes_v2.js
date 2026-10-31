/**
 * PJe Probe v2 — descobrir onde está o ID de notificação do Domicílio Eletrônico
 *
 * A v1 usou /expedientes/{e.id}/partes e todos os ids vieram null.
 * O probe original registrou /expedientes/85830981/partes, mas os expedientes
 * reais têm id 101116266/101116267 — então o id correto do path é OUTRO campo
 * (idProcessoExpediente provavelmente).
 *
 * Esta v2:
 *   1. Dumpa TODOS os campos de cada expediente (para achar 85830981).
 *   2. Testa /partes com cada candidato de id.
 *   3. Dumpa o JSON cru de cada resposta.
 *   4. Testa endpoints alternativos (detalhar expediente, destinatários, etc).
 *
 * Uso: await pjeProbeDomExp2()
 *      await pjeProbeDomExp2('9010617')
 */
(async function pjeProbeDomExp2(idProcessoArg) {
  'use strict';

  const C = (t, cor) => [`%c[PROBE2]`, `color:${cor};font-weight:bold`, t];
  const log = (t, ...a) => console.log(...C(t, '#0a0'), ...a);
  const warn = (t, ...a) => console.warn(...C(t, '#a80'), ...a);
  const err = (t, ...a) => console.error(...C(t, '#a00'), ...a);

  let idProcesso = idProcessoArg;
  if (!idProcesso) {
    const m = location.pathname.match(/\/processo\/(\d+)/);
    if (m) idProcesso = m[1];
  }
  if (!idProcesso) {
    err('Informe o id do processo: pjeProbeDomExp2("9010617")');
    return null;
  }
  log('idProcesso =', idProcesso);

  const api = async (path) => {
    const url = new URL(path, location.origin).toString();
    const r = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      headers: { 'Accept': 'application/json, text/plain, */*' },
    });
    const txt = await r.text();
    let json = null;
    try { json = JSON.parse(txt); } catch (_) {}
    return { ok: r.ok, status: r.status, json, txt };
  };

  // ---- 1. Expedientes, com TODOS os campos -------------------------------
  const expedientes = [];
  for (let p = 1; p <= 50; p++) {
    const r = await api(`/pje-comum-api/api/processos/id/${idProcesso}/expedientes?pagina=${p}&tamanhoPagina=100&instancia=1`);
    const lista = (r.json && r.json.resultado) || [];
    expedientes.push(...lista);
    if (lista.length < 100) break;
  }
  log(`expedientes: ${expedientes.length}`);

  console.group('%c TODOS os campos de cada expediente ', 'background:#046;color:#fff;font-weight:bold');
  for (const e of expedientes) {
    console.group(`exp: ${e.nomePessoaParte} | meio=${e.meioExpedienteEnum}`);
    console.log(JSON.parse(JSON.stringify(e)));
    console.groupEnd();
  }
  console.groupEnd();

  // ---- 2. Mapa campo -> valor, para achar 85830981 -----------------------
  log('--- procurando o valor 85830981 em qualquer campo dos expedientes ---');
  let achou = null;
  for (const e of expedientes) {
    for (const [k, v] of Object.entries(e)) {
      if (String(v) === '85830981') {
        achou = { expediente: e, campo: k, valor: v };
        log(`  ENCONTRADO: expediente "${e.nomePessoaParte}" campo "${k}" = ${v}`);
      }
    }
  }
  if (!achou) warn('  85830981 NAO aparece em nenhum campo dos expedientes atuais (pode ter mudado)');

  // ---- 3. Testar /partes com TODOS os candidatos de id -------------------
  const dom = expedientes.filter(e => String(e.meioExpedienteEnum || '').toUpperCase() === 'DOMICILIO_ELETRONICO');
  log(`expedientes DOMICILIO_ELETRONICO: ${dom.length}`);

  console.group('%c /partes com cada candidato de id ', 'background:#640;color:#fff;font-weight:bold');
  const achadosPartes = [];
  for (const e of dom) {
    console.group(`exp ${e.id} / ${e.nomePessoaParte}`);
    const candidatos = [
      ['e.id', e.id],
      ['e.idProcessoExpediente', e.idProcessoExpediente],
      ['e.idDocumento', e.idDocumento],
    ].filter(([, v]) => v != null);
    for (const [nome, valor] of candidatos) {
      const r = await api(`/pje-comum-api/api/processos/id/${idProcesso}/expedientes/${valor}/partes`);
      const lista = Array.isArray(r.json) ? r.json : [];
      const comId = lista.filter(p => p.idDestinatarioExpedienteDomicilioEletronico != null);
      console.log(`  ${nome}=${valor} -> HTTP ${r.status} | partes=${lista.length} | com idDest=${comId.length}`);
      if (comId.length) {
        console.log('     ACHOU COM ID:', comId);
        achadosPartes.push({ expediente: e.id, empresa: e.nomePessoaParte, via: nome, valor, partes: comId });
      }
      if (lista.length && nome === 'e.id') {
        console.log('     amostra do 1o item:', lista[0]);
      }
    }
    console.groupEnd();
  }
  console.groupEnd();

  // ---- 4. Endpoints alternativos -----------------------------------------
  console.group('%c Endpoints alternativos ', 'background:#404;color:#fff;font-weight:bold');
  const alvos = [
    `/pje-comum-api/api/processos/id/${idProcesso}/expedientes/${dom[0] ? (dom[0].idProcessoExpediente || dom[0].id) : 'X'}`,
    `/pje-comum-api/api/processos/id/${idProcesso}/expedientes/${dom[0] ? (dom[0].idProcessoExpediente || dom[0].id) : 'X'}/destinatarios`,
    `/pje-comum-api/api/processos/id/${idProcesso}/documentos/id/${dom[0] ? dom[0].idDocumento : 'X'}/destinatarios`,
    `/pje-comum-api/api/processos/id/${idProcesso}/expedientes/${dom[0] ? (dom[0].idProcessoExpediente || dom[0].id) : 'X'}/notificacoes`,
  ];
  for (const path of alvos) {
    const r = await api(path);
    console.log(`  ${path.split(`id/${idProcesso}`)[1]} -> HTTP ${r.status}${r.ok ? '' : ' (falhou)'}`);
    if (r.ok && r.json) console.log('     ', r.json);
  }
  console.groupEnd();

  // ---- 5. Resumo ---------------------------------------------------------
  console.group('%c RESULTADO ', 'background:#046;color:#fff;font-weight:bold');
  if (achadosPartes.length) {
    console.table(achadosPartes.map(a => ({
      empresa: a.empresa,
      expediente: a.expediente,
      via: a.via,
      valor: a.valor,
      idDestinatarioDOM: a.partes.map(p => p.idDestinatarioExpedienteDomicilioEletronico).join(', '),
    })));
  } else {
    warn('Nenhum idDestinatarioExpedienteDomicilioEletronico encontrado nos endpoints testados.');
    warn('Cole aqui a saída do bloco "/partes com cada candidato" e o dump dos expedientes.');
  }
  console.groupEnd();

  const pacote = { idProcesso, expedientes, dom, achadosPartes, campo8583: achou };
  try { copy(JSON.stringify(pacote, null, 2)); log('JSON copiado.'); } catch (_) {}
  return pacote;
})();
