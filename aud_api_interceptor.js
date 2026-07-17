/**
 * PJe Aud Probe — IIFE Autoexecutável (Console)
 * Cole no console do PJe autenticado. Saída direta da API, sem fallback.
 *
 * Endpoint: GET /audapi/rest/pje/audpje/pautas?dataInicio=2026-07-21&dataFim=2026-07-21&orgaoJulgador=187
 * Resultado: window.__audProbe + JSON no clipboard
 */

(async function probeAudiencias() {
  'use strict';

  const TAG = '%c🔍 AudProbe';
  const C_GREEN = 'color: lime; font-weight: bold';
  const C_CYAN  = 'color: cyan; font-weight: bold';
  const C_RED   = 'color: red; font-weight: bold';

  console.log(TAG, C_GREEN, '=== AUD PROBE — 21/07/2026 ===');

  // ─── Helpers ────────────────────────────────────────────────────────────
  function normalizarDoc(doc) {
    if (!doc) return '';
    const nums = doc.replace(/\D/g, '');
    if (nums.length === 14) return nums.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
    if (nums.length === 11) return nums.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    return doc;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Chamada direta ao endpoint real (ambiente logado)
  // ═══════════════════════════════════════════════════════════════════════════
  const url = `${location.origin}/audapi/rest/pje/audpje/pautas?dataInicio=2026-07-21&dataFim=2026-07-21&orgaoJulgador=187`;

  console.log(TAG, C_CYAN, '📡 GET', url);

  let resultado = { dataAlvo: '21/07/2026', pautas: [], erro: null };

  try {
    const r = await fetch(url, { credentials: 'include', headers: { 'Accept': 'application/json' } });
    const text = await r.text();
    const data = text ? JSON.parse(text) : null;

    if (!r.ok) {
      console.log(TAG, C_RED, `❌ HTTP ${r.status}`);
      resultado.erro = { status: r.status, body: (text || '').slice(0, 500) };
    } else if (!data) {
      console.log(TAG, C_RED, '❌ Resposta vazia');
      resultado.erro = { status: r.status, body: '(vazio)' };
    } else {
      // Desembrulhar resposta paginada ou array direto
      const lista = Array.isArray(data) ? data : (data.content || data.resultado || data.pautas || data.lista || []);

      console.log(TAG, C_GREEN, `✅ ${lista.length} pautas`);

      // ── PASSO 1: Mapear pautas com chaves reais ──
      const pautasBrutas = lista.map(p => ({
        idProcessoAudiencia: p.idProcessoAudiencia,
        numeroProcesso: p.numeroProcesso || '',
        idProcesso: p.idProcesso,
        tipoAudiencia: p.tipoAudiencia || '',
        dataAudiencia: p.dataAudiencia || '',
        sala: p.nomeSala || '',
        vara: p.vara || '',
        classeJudicial: p.classeJudicial || '',
        siglaClasse: p.siglaClasseJudicial || '',
        valorCausa: p.valorCausa || null,
        idOrgaoJulgador: p.idOrgaoJulgador
      }));

      // ── PASSO 2: Buscar partes via pje-comum-api ──
      // Resposta: { "ATIVO": [...], "PASSIVO": [...] }
      const idsProcesso = [...new Set(pautasBrutas.map(p => p.idProcesso).filter(Boolean))];
      console.log(TAG, C_CYAN, `🔍 Buscando partes de ${idsProcesso.length} processos...`);

      const partesCache = {};
      let buscados = 0;
      const API = location.origin + '/pje-comum-api/api';

      for (let i = 0; i < idsProcesso.length; i += 5) {
        const lote = idsProcesso.slice(i, i + 5);
        const resultados = await Promise.all(lote.map(async id => {
          try {
            const r = await fetch(`${API}/processos/id/${id}/partes`,
              { credentials: 'include', headers: { 'Accept': 'application/json' } });
            if (!r.ok) return { id, ok: false, status: r.status };
            return { id, ok: true, data: await r.json() };
          } catch (e) {
            return { id, ok: false, erro: e.message };
          }
        }));

        for (const res of resultados) {
          buscados++;
          if (res.ok && res.data) {
            // data = { ATIVO: [...], PASSIVO: [...] }
            const todas = [];
            for (const polo of ['ATIVO', 'PASSIVO']) {
              const arr = res.data[polo] || [];
              for (const pt of arr) {
                if (pt.tipo === 'ADVOGADO') continue; // pular representantes
                todas.push({
                  nome: pt.nome || '',
                  documento: normalizarDoc(pt.documento || ''),
                  tipo: pt.tipo || '',
                  polo: polo
                });
              }
            }
            partesCache[res.id] = todas;
          } else {
            partesCache[res.id] = { _erro: res.status || res.erro };
          }
        }
        if (buscados < idsProcesso.length) {
          console.log(TAG, `   ${buscados}/${idsProcesso.length}...`);
        }
      }

      // ── MONTAR RESULTADO FINAL ──
      resultado.pautas = pautasBrutas.map(p => ({
        ...p,
        dataAudiencia: p.dataAudiencia ? p.dataAudiencia.slice(0, 16) : '',
        partes: partesCache[p.idProcesso] || { _erro: 'não buscado' }
      }));

      console.table(resultado.pautas.map(p => ({
        Hora: p.dataAudiencia.slice(11, 16),
        Tipo: p.tipoAudiencia,
        Sala: p.sala,
        Processo: p.numeroProcesso,
        'Polo Ativo': Array.isArray(p.partes) ? p.partes.filter(pt => pt.polo === 'ATIVO').map(pt => `${pt.nome} (${pt.documento})`).join(', ') : '?',
        'Polo Passivo': Array.isArray(p.partes) ? p.partes.filter(pt => pt.polo === 'PASSIVO').map(pt => `${pt.nome} (${pt.documento})`).join(', ') : '?'
      })));
    }
  } catch (e) {
    console.log(TAG, C_RED, '💥', e.message);
    resultado.erro = { mensagem: e.message };
  }

  // ─── Exportar ────────────────────────────────────────────────────────────
  window.__audProbe = resultado;
  console.log(TAG, C_GREEN, `\n📊 ${resultado.pautas.length} pautas | Erro: ${resultado.erro ? 'sim' : 'não'}`);

  const json = JSON.stringify(resultado, null, 2);
  try {
    await navigator.clipboard.writeText(json);
    console.log(TAG, C_GREEN, '📋 JSON no clipboard!');
  } catch (_) {
    console.log(TAG, C_CYAN, '💡 window.__audProbe');
  }

  return resultado;
})();
