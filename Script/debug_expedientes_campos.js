// Colar no console do browser (F12) estando na página do processo PJe
// Ex: /processo/8485392/detalhe
// Mostra TODOS os campos brutos retornados pela API de expedientes.

(async () => {
  const m = location.href.match(/\/processo\/(\d+)\//);
  if (!m) { console.error('[EXP] Abra a página de um processo primeiro'); return; }
  const id = m[1];

  const xsrf = document.cookie.match(/XSRF-TOKEN=([^;]+)/);
  const headers = {
    'Content-Type': 'application/json',
    'X-Grau-Instancia': '1',
    ...(xsrf ? { 'X-XSRF-TOKEN': decodeURIComponent(xsrf[1]) } : {}),
  };

  const base = location.origin;
  const url = `${base}/pje-comum-api/api/processos/id/${id}/expedientes?pagina=1&tamanhoPagina=50&instancia=1`;
  console.log('[EXP] GET', url);

  const res = await fetch(url, { headers, credentials: 'include' });
  if (!res.ok) { console.error('[EXP] HTTP', res.status, await res.text()); return; }

  const data = await res.json();
  const lista = data.resultado || [];
  console.log(`[EXP] totalRegistros=${data.totalRegistros}  retornados=${lista.length}`);

  if (!lista.length) { console.warn('[EXP] Nenhum expediente retornado.'); return; }

  // Todos os campos do primeiro item
  console.log('\n=== TODOS OS CAMPOS DO 1º EXPEDIENTE ===');
  console.table([lista[0]]);
  console.log('(objeto completo):', lista[0]);

  // Resumo de todos os itens: nome + confirmação + todos os campos não conhecidos
  const conhecidos = new Set(['id','nomePessoaParte','tipoExpediente','meioExpediente',
    'prazoLegal','dataCriacao','dataCiencia','fimDoPrazoLegal','fechado']);

  console.log('\n=== CAMPOS EXTRAS (fora dos documentados) POR ITEM ===');
  lista.forEach((exp, i) => {
    const extras = Object.fromEntries(Object.entries(exp).filter(([k]) => !conhecidos.has(k)));
    console.log(
      `[${i}] ${exp.nomePessoaParte} | meio=${exp.meioExpediente} | fechado=${exp.fechado}` +
      ` | dataCiencia=${exp.dataCiencia} | EXTRAS:`, extras
    );
  });

  // União de todos os nomes de campos encontrados
  const allKeys = [...new Set(lista.flatMap(e => Object.keys(e)))].sort();
  console.log('\n=== TODOS OS CAMPOS ENCONTRADOS (union) ===', allKeys);
})();
