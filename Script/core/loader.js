// Script/core/loader.js
// Carrega todos os módulos dinamicamente com cache-busting automático.
// Para adicionar módulo: incluir no array MODULES e bumpar ?v= deste arquivo.

(async function () {

  const BASE = 'https://raw.githubusercontent.com/silaspassosf/pjeplus/main/Script/';
  const CB   = '?cb=' + (Date.now()+1); // cache-bust — sempre fresh

  // ── Ordem de carregamento importa (dependências primeiro) ────────────────
  const MODULES = [
    // Core (sempre carregados)
    'core/utils.js',
    'core/state.js',
    'core/extrair.js',

    // Módulos PJe — carregados em runtime pelo loader
    'modules/lista/lista.timeline.js',
    'modules/lista/lista.check.js',
    'modules/lista/lista.edital.js',
    'modules/lista/lista.pgto.js',
    'modules/atalhos/atalhos.js',
    'modules/atalhos/atalhos.worker.js',
    'ui/painel.js',
    'modules/infojud/infojud.js',
    'modules/sisbajud/core.js',
    'modules/sisbajud/relatorios.js',
    'modules/sisbajud/sisbajud.js',
    'modules/debito/registrar_debito.js',
  ];

  async function loadScript(path) {
    try {
      const res  = await fetch(BASE + path + CB);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const code = await res.text();
      // Executa em escopo isolado, módulos que expõem window continuam funcionando
      const fn   = new Function(code);
      fn();
    } catch (e) {
      console.error('[PJeLoader] Falha ao carregar:', path, e);
    }
  }

  // Carrega em série para respeitar dependências
  for (const path of MODULES) {
    await loadScript(path);
  }

  console.log('[PJeLoader] ✅ Todos os módulos carregados.');

})();
