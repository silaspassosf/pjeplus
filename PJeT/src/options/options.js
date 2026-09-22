'use strict';

// ── PJeT — options/options.js ─────────────────────────────────────
// Gerenciador de configurações e diagnóstico da extensão PJeT.
// ─────────────────────────────────────────────────────────────────

const _browser = typeof browser !== 'undefined' ? browser : chrome;

const MODULOS = [
  { key: 'lista-check',   id: 'mod-lista-check'  },
  { key: 'lista-edital',  id: 'mod-lista-edital' },
  { key: 'sisbajud',      id: 'mod-sisbajud'     },
  { key: 'argos',         id: 'mod-argos'        },
  { key: 'hcalc',         id: 'mod-hcalc'        },
  { key: 'debito',        id: 'mod-debito'       },
  { key: 'alvara',        id: 'mod-alvara'       },
  { key: 'audiencia',     id: 'mod-audiencia'    },
  { key: 'infojud',       id: 'mod-infojud'      },
  { key: 'simba',         id: 'mod-simba'        },
];

const STORAGE_KEY = 'pjet_modulos';

function getStorage() {
  return _browser?.storage?.sync || _browser?.storage?.local;
}

function setStatus(msg, tipo = '') {
  const el = document.getElementById('status');
  if (!el) return;
  el.textContent = msg;
  el.className = 'status ' + tipo;
}

function setDiag(msg, color = '') {
  const el = document.getElementById('diag-msg');
  if (!el) return;
  el.textContent = msg;
  el.style.color = color;
}

async function carregar() {
  try {
    const storage = getStorage();
    if (!storage) throw new Error('API de storage não disponível.');

    const res = await storage.get(STORAGE_KEY);
    const prefs = res[STORAGE_KEY] || {};

    for (const mod of MODULOS) {
      const el = document.getElementById(mod.id);
      if (el) {
        el.checked = (mod.key in prefs) ? !!prefs[mod.key] : true;
      }
    }
  } catch (err) {
    setStatus('Erro ao carregar preferências: ' + err.message, 'err');
    console.error('[PJeT Options]', err);
  }
}

async function salvar() {
  const btn = document.getElementById('btn-salvar');
  if (btn) btn.disabled = true;

  try {
    const storage = getStorage();
    if (!storage) throw new Error('API de storage indisponível');

    const prefs = {};
    for (const mod of MODULOS) {
      const el = document.getElementById(mod.id);
      prefs[mod.key] = el ? el.checked : true;
    }

    await storage.set({ [STORAGE_KEY]: prefs });

    // Notifica background para difusão
    try {
      _browser.runtime?.sendMessage({
        tipo: 'pjet_preferencias_atualizadas',
        prefs
      }).catch(() => {});
    } catch (_) {}

    setStatus('✓ Configurações salvas com sucesso!', 'ok');
    setTimeout(() => setStatus(''), 2500);
  } catch (err) {
    setStatus('Falha ao salvar: ' + err.message, 'err');
    console.error('[PJeT Options]', err);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function restaurarPadroes() {
  for (const mod of MODULOS) {
    const el = document.getElementById(mod.id);
    if (el) el.checked = true;
  }
  setDiag('Padrões restaurados (todos habilitados). Clique em Salvar para gravar.', '#2e7d32');
}

async function testarStorage() {
  try {
    const storage = getStorage();
    if (!storage) throw new Error('Storage API indefinida');

    const testKey = 'pjet_test_' + Date.now();
    await storage.set({ [testKey]: 'OK' });
    const res = await storage.get(testKey);
    await storage.remove(testKey);

    if (res[testKey] === 'OK') {
      setDiag('✓ Teste de leitura/gravação no storage bem-sucedido!', '#2e7d32');
    } else {
      setDiag('⚠️ Teste retornou valor inesperado: ' + JSON.stringify(res), '#f57f17');
    }
  } catch (err) {
    setDiag('❌ Erro no teste de storage: ' + err.message, '#c62828');
    console.error('[PJeT Test]', err);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  carregar();
  document.getElementById('btn-salvar')?.addEventListener('click', salvar);
  document.getElementById('btn-reset')?.addEventListener('click', restaurarPadroes);
  document.getElementById('btn-testar')?.addEventListener('click', testarStorage);
});
