/**
 * PJe Probe — IDs de notificação de Domicílio Eletrônico
 *
 * Roda no console da página /detalhe do processo, usando a MESMA API do fluxo
 * de domicílio eletrônico (pje-comum-api).
 *
 * Uso:
 *   await pjeProbeDomExp()            // detecta o id do processo pela URL
 *   await pjeProbeDomExp('9010617')   // id explícito
 *
 * Caminho (confirmado no probe de 30/10/2026):
 *   1. GET /processos/id/{id}/expedientes
 *        -> lista com nomePessoaParte, meioExpedienteEnum, cienciaViaSistema,
 *           dataCiencia, prazoVencido, fechado
 *   2. para cada expediente DOMINIO_ELETRONICO:
 *        GET /processos/id/{id}/expedientes/{idExpediente}/partes
 *        -> array com idDestinatarioExpedienteDomicilioEletronico
 *
 * Os dois endpoints são os mesmos que o ícone de envelope / "Ver ato" usam —
 * portanto os IDs obtidos aqui são os que o modal de notificação mostraria.
 */
(async function pjeProbeDomExp(idProcessoArg) {
  'use strict';

  const log = (...a) => console.log('%c[DOM-PROBE]', 'color:#0a0;font-weight:bold', ...a);
  const warn = (...a) => console.warn('%c[DOM-PROBE]', 'color:#a80;font-weight:bold', ...a);
  const err = (...a) => console.error('%c[DOM-PROBE]', 'color:#a00;font-weight:bold', ...a);

  // ---- 1. Descobrir o id do processo -------------------------------------
  let idProcesso = idProcessoArg;
  if (!idProcesso) {
    // /pjekz/processo/9010617/detalhe  (numeroProcesso às vezes vem como 2o segmento)
    const m = location.pathname.match(/\/processo\/(\d+)/);
    if (m) idProcesso = m[1];
  }
  if (!idProcesso) {
    err('Não consegui o id do processo pela URL. Passe manualmente: pjeProbeDomExp("9010617")');
    return null;
  }
  log('idProcesso =', idProcesso);

  // ---- 2. Helper de fetch com cookies de sessão --------------------------
  const api = async (path) => {
    const url = new URL(path, location.origin).toString();
    const r = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      headers: { 'Accept': 'application/json, text/plain, */*', 'X-Requested-With': 'XMLHttpRequest' },
    });
    if (!r.ok) throw new Error(`HTTP ${r.status} em ${path}`);
    return r.json();
  };

  // ---- 3. Expedientes (paginado, igual ao fluxo Python) ------------------
  const expedientes = [];
  for (let pagina = 1; pagina <= 50; pagina++) {
    const j = await api(
      `/pje-comum-api/api/processos/id/${idProcesso}/expedientes` +
      `?pagina=${pagina}&tamanhoPagina=100&instancia=1`
    );
    const lista = (j && j.resultado) || [];
    expedientes.push(...lista);
    if (lista.length < 100) break;
  }
  log(`expedientes: ${expedientes.length}`);

  // ---- 4. Filtrar Domicílio Eletrônico -----------------------------------
  const dom = expedientes.filter(e =>
    String(e.meioExpedienteEnum || '').toUpperCase() === 'DOMICILIO_ELETRONICO'
  );
  log(`expedientes DOMICILIO_ELETRONICO: ${dom.length}`);

  const motivo = (e) => {
    const partes = [];
    if (e.cienciaViaSistema) partes.push('ciencia automatica');
    if (e.dataCiencia === null || e.dataCiencia === undefined) partes.push('sem ciencia (prazo expirado)');
    if (e.prazoVencido) partes.push('prazo vencido');
    if (e.fechado) partes.push('fechado');
    return partes.join(' | ') || '-';
  };

  // ---- 5. Para cada expediente, buscar as partes (onde está o ID) --------
  const resultado = [];
  for (const e of dom) {
    const linha = {
      idExpediente: e.id,
      nomePessoaParte: (e.nomePessoaParte || '').trim(),
      idDocumento: e.idDocumento,
      idProcessoExpediente: e.idProcessoExpediente,
      tipoExpediente: e.tipoExpediente,
      meioExpediente: e.meioExpediente,
      dataCriacao: e.dataCriacao,
      dataCiencia: e.dataCiencia,
      fimDoPrazoLegal: e.fimDoPrazoLegal,
      cienciaViaSistema: e.cienciaViaSistema,
      prazoVencido: e.prazoVencido,
      fechado: e.fechado,
      _motivo: motivo(e),
      partes: [],
    };

    try {
      const partes = await api(
        `/pje-comum-api/api/processos/id/${idProcesso}/expedientes/${e.id}/partes`
      );
      linha.partes = (partes || []).map(p => ({
        nomeParte: p.nomeParte,
        idDestinatarioExpedienteDomicilioEletronico: p.idDestinatarioExpedienteDomicilioEletronico,
        idProcessoParteExpediente: p.idProcessoParteExpediente,
        idProcessoParteExpedienteEndereco: p.idProcessoParteExpedienteEndereco,
        idDestinatarioExpedienteCorreiosEcarta: p.idDestinatarioExpedienteCorreiosEcarta,
        idConfiguracaoExpedicaoSistemaExterno: p.idConfiguracaoExpedicaoSistemaExterno,
        idParteProcessual: p.idParteProcessual,
        prazoLegal: p.prazoLegal,
        prazoExpedienteAutomatico: p.prazoExpedienteAutomatico,
        fechado: p.fechado,
      }));
    } catch (ex) {
      warn(`falha ao buscar partes do expediente ${e.id}: ${ex.message}`);
    }
    resultado.push(linha);
  }

  // ---- 6. Relatório -------------------------------------------------------
  console.group('%c RESUMO DOMICÍLIO ELETRÔNICO ', 'background:#046;color:#fff;font-weight:bold');
  const tabela = resultado.map(r => ({
    expediente: r.idExpediente,
    empresa: r.nomePessoaParte,
    motivo: r._motivo,
    idDestinatarioDOM: r.partes.map(p => p.idDestinatarioExpedienteDomicilioEletronico).join(', ') || '(vazio)',
    doc: r.idDocumento,
  }));
  console.table(tabela);
  console.groupEnd();

  // ---- 7. Objeto completo para copiar ------------------------------------
  const pacote = { idProcesso, totalExpedientes: expedientes.length, expedientesDom: resultado };
  log('objeto completo:', pacote);
  try {
    copy(JSON.stringify(pacote, null, 2));
    log('JSON copiado para a área de transferência (cole em um arquivo .json).');
  } catch (_) {}

  // ---- 8. Lista compacta "empresa -> ids" --------------------------------
  const resumo = resultado.map(r => {
    const ids = r.partes.map(p => p.idDestinatarioExpedienteDomicilioEletronico).filter(Boolean);
    return `${r.nomePessoaParte} [exp ${r.idExpediente}]: ${ids.length ? ids.join(', ') : 'SEM id'}`;
  });
  log('resumo:\n  ' + resumo.join('\n  '));

  return pacote;
})();
