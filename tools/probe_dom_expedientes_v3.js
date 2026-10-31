/**
 * PJe Probe v3 — caminho definitivo do ID de notificação DOM
 *
 * CONFIRMADO na v2:
 *   /expedientes/{idProcessoExpediente}/partes  ->  traz
 *   idDestinatarioExpedienteDomicilioEletronico
 *
 *   /expedientes/{id}/partes          -> partes=0  (ERRADO)
 *   /expedientes/{idDocumento}/partes -> partes=0  (ERRADO)
 *
 * Exemplo real (processo 9010617):
 *   exp 101116266 / VOS OBRAS  / idProcessoExpediente=85830981 -> id 2534639
 *   exp 101116267 / MUNICIPIO  / idProcessoExpediente=85830982 -> id 2534640
 *
 * Este probe e' a versao enxuta: só o caminho que funciona.
 *
 * Uso: await pjeProbeDomExp3()
 *      await pjeProbeDomExp3('9010617')
 */
(async function pjeProbeDomExp3(idProcessoArg) {
  'use strict';

  const log = (t, ...a) => console.log('%c[PROBE3]', 'color:#0a0;font-weight:bold', t, ...a);
  const warn = (t, ...a) => console.warn('%c[PROBE3]', 'color:#a80;font-weight:bold', t, ...a);

  let idProcesso = idProcessoArg;
  if (!idProcesso) {
    const m = location.pathname.match(/\/processo\/(\d+)/);
    if (m) idProcesso = m[1];
  }
  if (!idProcesso) {
    console.error('[PROBE3] informe o id: pjeProbeDomExp3("9010617")');
    return null;
  }

  const api = async (path) => {
    const r = await fetch(new URL(path, location.origin).toString(), {
      credentials: 'include',
      headers: { 'Accept': 'application/json' },
    });
    if (!r.ok) throw new Error(`HTTP ${r.status} em ${path}`);
    return r.json();
  };

  // 1. Expedientes
  const expedientes = [];
  for (let p = 1; p <= 50; p++) {
    const j = await api(`/pje-comum-api/api/processos/id/${idProcesso}/expedientes?pagina=${p}&tamanhoPagina=100&instancia=1`);
    const lista = (j && j.resultado) || [];
    expedientes.push(...lista);
    if (lista.length < 100) break;
  }

  // 2. Só domicílio eletrônico, filtro do fluxo (ciência automática OU sem dataCiencia)
  const dom = expedientes.filter(e =>
    String(e.meioExpedienteEnum || '').toUpperCase() === 'DOMICILIO_ELETRONICO'
  );

  const linhas = [];
  for (const e of dom) {
    const alvo = e.idProcessoExpediente;
    if (alvo == null) {
      warn(`exp ${e.id} sem idProcessoExpediente — pulando`);
      continue;
    }
    let partes = [];
    try {
      partes = await api(`/pje-comum-api/api/processos/id/${idProcesso}/expedientes/${alvo}/partes`) || [];
    } catch (ex) {
      warn(`falha /partes de ${alvo}: ${ex.message}`);
    }

    for (const p of partes) {
      const idDom = p.idDestinatarioExpedienteDomicilioEletronico;
      const cienciaAuto = !!e.cienciaViaSistema;
      const semCiencia = e.dataCiencia === null || e.dataCiencia === undefined;
      linhas.push({
        empresa: (e.nomePessoaParte || '').trim(),
        idExpediente: e.id,
        idProcessoExpediente: alvo,
        idDestinatarioDOM: idDom,
        nomeParte: p.nomeParte,
        idParteProcessual: p.idParteProcessual,
        idDestCorreios: p.idDestinatarioExpedienteCorreiosEcarta,
        cienciaViaSistema: cienciaAuto,
        dataCiencia: e.dataCiencia,
        prazoVencido: e.prazoVencido,
        fechado: e.fechado,
        idDocumento: e.idDocumento,
        // regra do fluxo Python (_checar_empresas_api)
        entraNoFiltro: (cienciaAuto || semCiencia),
      });
    }
  }

  console.group('%c DOM — empresa -> id de notificação ', 'background:#046;color:#fff;font-weight:bold');
  console.table(linhas);
  console.groupEnd();

  log(`${linhas.filter(l => l.idDestinatarioDOM != null).length}/${linhas.length} com idDestinatarioExpedienteDomicilioEletronico`);

  const pacote = { idProcesso, totalExpedientes: expedientes.length, linhas };
  try { copy(JSON.stringify(pacote, null, 2)); log('JSON copiado.'); } catch (_) {}
  return pacote;
})();
