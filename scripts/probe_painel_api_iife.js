/**
 * probe_painel_api_iife.js
 *
 * IIFE de diagnóstico — cole no console do PJe autenticado (qualquer página do painel).
 *
 * O que faz:
 *   1. Mostra as últimas URLs do painel/agrupamento capturadas pelo browser (performance API)
 *   2. Testa GET e POST para /agrupamentotarefas/processos/todos com variações de body
 *   3. Testa GET /agrupamentotarefas/processos (sem numero) com variações
 *   4. Loga status, estrutura do primeiro resultado e campos disponíveis
 *   5. Detecta automaticamente qual combinação funcionou
 *
 * Pré-condição: estar no PJe autenticado. Para melhores resultados, abrir o
 * Painel Global antes de rodar (assim a URL exata aparece nos performance entries).
 *
 * Uso:
 *   Cole o arquivo inteiro no console e aguarde o resumo final.
 */

(async function probeAgruTarefas() {
  const BASE = location.origin;
  const GRAU = 1;
  const H = { 'Content-Type': 'application/json', 'X-Grau-Instancia': String(GRAU) };

  // ─── 1. Capturar URLs recentes do painel via performance entries ──────────
  console.group('[PROBE] Últimas URLs de agrupamentotarefas/processos no browser');
  const entries = performance.getEntriesByType('resource')
    .filter(e => e.name.includes('agrupamentotarefas'))
    .slice(-10);  // últimas 10
  if (entries.length === 0) {
    console.log('  (nenhuma — abra o Painel Global antes de rodar este probe para capturar a URL real)');
  } else {
    entries.forEach((e, i) => console.log(`  [${i}] ${e.name}  (método: ${e.initiatorType})`));
  }
  console.groupEnd();

  // ─── 2. Helper de teste ───────────────────────────────────────────────────
  async function testar(label, url, method, body) {
    try {
      const opts = { method, credentials: 'include', headers: H };
      if (body !== undefined) opts.body = JSON.stringify(body);
      const r = await fetch(url, opts);
      let dados = null;
      let estrutura = null;
      try {
        const text = await r.text();
        dados = text ? JSON.parse(text) : null;
      } catch (_) {}

      if (dados) {
        // Tentar extrair primeiro item para mostrar campos
        const lista = Array.isArray(dados)
          ? dados
          : (dados.lista || dados.content || dados.processos || dados.resultado || dados.data || []);
        estrutura = Array.isArray(lista) && lista.length > 0
          ? Object.keys(lista[0])
          : Array.isArray(dados) ? [] : Object.keys(dados);
      }

      const resumo = {
        status: r.status,
        ok: r.ok,
        tipo: typeof dados,
        ehArray: Array.isArray(dados),
        qtde: Array.isArray(dados)
          ? dados.length
          : (dados && typeof dados === 'object'
              ? ((dados.lista || dados.content || dados.processos || dados.resultado || dados.data || []).length || '—')
              : '—'),
        campos: estrutura,
        primeiroItem: Array.isArray(dados) && dados.length > 0 ? dados[0] : null
      };

      console.log(`[PROBE][${r.ok ? '✅' : '❌'}] ${label} → HTTP ${r.status}`, resumo);
      return { label, status: r.status, ok: r.ok, dados, resumo };
    } catch (e) {
      console.log(`[PROBE][💥] ${label} → EXCEÇÃO: ${e.message}`);
      return { label, status: 0, ok: false, erro: e.message };
    }
  }

  // ─── 3. Candidatos a testar ───────────────────────────────────────────────
  const URL_TODOS  = `${BASE}/pje-comum-api/api/agrupamentotarefas/processos/todos`;
  const URL_BASE   = `${BASE}/pje-comum-api/api/agrupamentotarefas/processos`;
  const URL_TAREFA = `${BASE}/pje-comum-api/api/tarefas`;

  const testes = [];

  // /todos GET (esperado 405 — confirma que rota existe)
  testes.push(testar('GET /todos (sem params)', URL_TODOS, 'GET'));

  // /todos POST — vários formatos de body possíveis
  testes.push(testar('POST /todos {}', URL_TODOS, 'POST', {}));
  testes.push(testar('POST /todos {pagina,tamanhoPagina}', URL_TODOS, 'POST',
    { pagina: 1, tamanhoPagina: 10 }));
  testes.push(testar('POST /todos {filtros vazio}', URL_TODOS, 'POST',
    { pagina: 1, tamanhoPagina: 10, filtros: {} }));
  testes.push(testar('POST /todos {nomeTarefa}', URL_TODOS, 'POST',
    { pagina: 1, tamanhoPagina: 10, nomeTarefa: 'Triagem Inicial' }));
  testes.push(testar('POST /todos {filtros.nomeTarefa}', URL_TODOS, 'POST',
    { pagina: 1, tamanhoPagina: 10, filtros: { nomeTarefa: 'Triagem Inicial' } }));
  testes.push(testar('POST /todos {paginacao wrapper}', URL_TODOS, 'POST',
    { paginacao: { pagina: 1, tamanhoPagina: 10 } }));
  testes.push(testar('POST /todos {ordenacao}', URL_TODOS, 'POST',
    { pagina: 1, tamanhoPagina: 10, ordenacaoCrescente: true }));

  // /processos GET sem numero — já falhou antes com 403, confirmar
  testes.push(testar('GET /processos sem numero', URL_BASE, 'GET'));
  testes.push(testar('GET /processos ?pagina=1', URL_BASE + '?pagina=1&tamanhoPagina=10', 'GET'));

  // /processos POST
  testes.push(testar('POST /processos {}', URL_BASE, 'POST', {}));
  testes.push(testar('POST /processos {pagina}', URL_BASE, 'POST', { pagina: 1, tamanhoPagina: 10 }));

  // /tarefas — endpoint para listar tarefas (pode segurar lista de processos por tarefa)
  testes.push(testar('GET /tarefas', URL_TAREFA, 'GET'));

  // Aguardar todos
  const resultados = await Promise.all(testes);

  // ─── 4. Resumo ────────────────────────────────────────────────────────────
  console.group('[PROBE] === RESUMO FINAL ===');
  const sucesso = resultados.filter(r => r.ok);
  const parcial = resultados.filter(r => !r.ok && r.status > 0 && r.status !== 405 && r.status !== 403);

  if (sucesso.length) {
    console.log('✅ Funcionaram (HTTP 2xx):');
    sucesso.forEach(r => console.log(`  ${r.label} → ${r.status} | itens: ${r.resumo?.qtde} | campos: ${JSON.stringify(r.resumo?.campos)}`));
  } else {
    console.log('❌ Nenhum endpoint retornou 2xx');
  }

  if (parcial.length) {
    console.log('⚠️  Outros status (nem 403/405):');
    parcial.forEach(r => console.log(`  ${r.label} → ${r.status}`));
  }

  const metodo405 = resultados.filter(r => r.status === 405);
  if (metodo405.length) {
    console.log('🔄 405 Method Not Allowed (rota existe, método errado):');
    metodo405.forEach(r => console.log(`  ${r.label}`));
  }

  const proibido403 = resultados.filter(r => r.status === 403);
  if (proibido403.length) {
    console.log('🚫 403 Forbidden (rota existe, sem permissão/params obrigatórios):');
    proibido403.forEach(r => console.log(`  ${r.label}`));
  }

  console.log('\n[PROBE] URLs capturadas pelo browser (agrupamentotarefas):');
  entries.forEach((e, i) => console.log(`  [${i}] ${e.name}`));

  console.groupEnd();
  console.log('[PROBE] Objeto completo disponível como window.__probeResultados');
  window.__probeResultados = resultados;
  return resultados;
})();
