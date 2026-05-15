/**
 * bookmarklet_dom_filtros.js — Bookmarklet linha única para API do fluxo DOM
 *
 * Filtros: Fase Conhecimento + chips domicílio eletrônico
 *   - Prazo de Ciência Expirado
 *   - Prazo de Resposta Excedido (ciência automática)
 *   - Erro na Transmissão
 *
 * Tenta 3 estratégias em paralelo:
 *   1. PATCH /agrupamentotarefas/10/processos com subCaixa + faseProcessualString
 *   2. POST  /agrupamentotarefas/processos/todos com subCaixa + faseProcessualString
 *   3. PATCH /agrupamentotarefas/10/processos só com fase (fallback sem chips)
 *
 * Mostra resultado em console.table + alert com contagem.
 *
 * Gere o bookmarklet minificado com:
 *   node -e "console.log('javascript:'+encodeURIComponent(require('fs').readFileSync('scripts/bookmarklet_dom_filtros.js','utf8').replace(/\/\*[\s\S]*?\*\//g,'').replace(/\/\/.*/g,'').replace(/\n/g,' ').replace(/\s+/g,' ').trim()))"
 *
 * Ou copie a versão minificada abaixo (já pronta para usar como URL de bookmark):
 */

// ========== BOOKMARKLET (minificar esta função) ==========
(async function domFiltrosAPI() {
  const BASE = location.origin;
  const CHIPS = [
    'Domicílio Eletrônico - Prazo de Ciência Expirado',
    'Domicílio Eletrônico - Prazo de Resposta Excedido',
    'Domicílio Eletrônico - Erro na Transmissão'
  ];

  // XSRF token do cookie
  const m = document.cookie.match(/(?:^|;\s*)XSRF-TOKEN=([^;]+)/);
  const xsrf = m ? decodeURIComponent(m[1]) : '';

  const H = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-XSRF-TOKEN': xsrf,
    'X-Grau-Instancia': '1'
  };

  const bodyComChips = {
    pagina: 1, tamanhoPagina: 100,
    faseProcessualString: 'Conhecimento',
    subCaixa: CHIPS,
    tipoAtividade: null,
    processos: null,
    nomeConclusoMagistrado: null,
    usuarioResponsavel: null,
    numeroProcesso: null,
    juizoDigital: null
  };

  const bodySemChips = { ...bodyComChips, subCaixa: null };

  async function fetchAPI(label, url, method, body) {
    try {
      const opts = { method, credentials: 'include', headers: H };
      if (body) opts.body = JSON.stringify(body);
      const r = await fetch(url, opts);
      const dados = await r.json().catch(() => null);
      const lista = dados?.resultado || dados?.content || dados || [];
      const total = dados?.totalRegistros || lista.length || 0;
      return { label, ok: r.ok, status: r.status, total, lista };
    } catch (e) {
      return { label, ok: false, status: 0, total: 0, lista: [], erro: e.message };
    }
  }

  // 3 estratégias em paralelo
  const [r1, r2, r3] = await Promise.all([
    fetchAPI('PATCH /10/processos + chips',
      BASE + '/pje-comum-api/api/agrupamentotarefas/10/processos', 'PATCH', bodyComChips),
    fetchAPI('POST /todos + chips',
      BASE + '/pje-comum-api/api/agrupamentotarefas/processos/todos', 'POST', bodyComChips),
    fetchAPI('PATCH /10/processos só fase (sem chips)',
      BASE + '/pje-comum-api/api/agrupamentotarefas/10/processos', 'PATCH', bodySemChips)
  ]);

  // Resultados
  console.group('🔍 DOM Flow — Fase Conhecimento + Chips Domicílio Eletrônico');
  for (const r of [r1, r2, r3]) {
    const icon = r.ok ? '✅' : '❌';
    console.log(`${icon} ${r.label} → HTTP ${r.status} | ${r.total} processos`);
    if (r.lista.length > 0) {
      console.table(r.lista.slice(0, 20).map(p => ({
        id: p.id || p.idProcesso,
        numero: p.numeroProcesso || p.numero,
        fase: p.faseProcessual || p.labelFaseProcessual || '?',
        classe: p.classeJudicial?.sigla || p.classe?.sigla || '?',
        tarefa: p.tarefa?.nome || p.nomeTarefa || '?',
        juizoDigital: p.juizoDigital
      })));
    }
    if (r.erro) console.warn(`  ⚠️ ${r.erro}`);
  }
  console.groupEnd();

  // Melhor resultado
  const melhor = [r1, r2, r3].find(r => r.ok && r.total > 0) || r3;
  const total = melhor.total;
  const lista = melhor.lista;

  // Painel flutuante
  const div = document.createElement('div');
  div.innerHTML = `<div style="position:fixed;top:10px;right:10px;z-index:99999;background:#0f0f23;color:#e0e0e0;padding:14px 18px;border-radius:10px;max-width:480px;max-height:80vh;overflow:auto;font:12px monospace;box-shadow:0 4px 24px rgba(0,0,0,.6);border:1px solid #334">
    <b style="font-size:14px">🔍 DOM Flow — Conhecimento + Chips</b><br>
    <span style="color:#4fc3f7">${melhor.label}: ${total} processos</span>
    <hr style="border-color:#333;margin:6px 0">
    ${lista.slice(0, 15).map(p => {
      const num = p.numeroProcesso || p.numero || '?';
      const cls = p.classeJudicial?.sigla || p.classe?.sigla || '';
      const tar = p.tarefa?.nome || p.nomeTarefa || '';
      return `<div style="margin:2px 0;padding:3px 6px;background:#1a1a3e;border-radius:4px;font-size:11px">
        <b>${num}</b> ${cls} ${tar}
      </div>`;
    }).join('')}
    ${lista.length > 15 ? `<div style="color:#888;font-size:10px;margin-top:4px">... +${lista.length - 15} mais (ver console F12)</div>` : ''}
    <button onclick="this.parentElement.remove()" style="margin-top:8px;padding:3px 12px;background:#e94560;color:#fff;border:0;border-radius:4px;cursor:pointer;font-size:11px">✕ Fechar</button>
  </div>`;
  document.body.appendChild(div.firstElementChild);

  // Resumo
  alert(`DOM Flow — Conhecimento + Chips Domicílio Eletrônico\n\n` +
    `${r1.label}: ${r1.total} proc (HTTP ${r1.status})\n` +
    `${r2.label}: ${r2.total} proc (HTTP ${r2.status})\n` +
    `${r3.label}: ${r3.total} proc (HTTP ${r3.status})\n\n` +
    `Ver console (F12) para tabela completa.`
  );
})();
