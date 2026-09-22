'use strict';

// ── PJeT — popup/popup.js ─────────────────────────────────────────
// Popup de gerenciamento rápido de módulos do PJeT.
// ─────────────────────────────────────────────────────────────────

const _browser = typeof browser !== 'undefined' ? browser : chrome;

const MODULOS = [
  // PJe
  { key: 'lista-check',   id: 'mod-lista-check'  },
  { key: 'lista-edital',  id: 'mod-lista-edital' },
  { key: 'sisbajud',      id: 'mod-sisbajud'     },
  { key: 'argos',         id: 'mod-argos'        },
  { key: 'hcalc',         id: 'mod-hcalc'        },
  { key: 'debito',        id: 'mod-debito'       },
  { key: 'alvara',        id: 'mod-alvara'       },
  { key: 'audiencia',     id: 'mod-audiencia'    },
  // Externos
  { key: 'infojud',       id: 'mod-infojud'      },
  { key: 'simba',         id: 'mod-simba'        },
];

const STORAGE_KEY = 'pjet_modulos';

function getStorage() {
  return _browser?.storage?.sync || _browser?.storage?.local;
}

// ── Utilitários ───────────────────────────────────────────────────
function setStatus(msg, tipo = '') {
  const el = document.getElementById('status');
  if (!el) return;
  el.textContent = msg;
  el.className = 'status ' + tipo;
}

function clearStatusAfter(ms = 2000) {
  setTimeout(() => setStatus(''), ms);
}

// ── Carregar preferências do storage ─────────────────────────────
async function carregarPreferencias() {
  try {
    const storage = getStorage();
    if (!storage) throw new Error('API de storage não disponível.');

    const result = await storage.get(STORAGE_KEY);
    const prefs  = result[STORAGE_KEY] || {};

    for (const mod of MODULOS) {
      const el = document.getElementById(mod.id);
      if (!el) continue;
      // Default: todos habilitados se não houver preferência salva
      el.checked = (mod.key in prefs) ? !!prefs[mod.key] : true;
    }
    console.log('[PJeT Popup] Preferências carregadas:', prefs);
  } catch (e) {
    setStatus('Erro ao carregar', 'err');
    console.error('[PJeT Popup] Erro ao carregar preferências:', e);
  }
}

// ── Salvar preferências no storage ───────────────────────────────
async function salvarPreferencias() {
  const btn = document.getElementById('btn-salvar');
  if (btn) btn.disabled = true;

  try {
    const storage = getStorage();
    if (!storage) throw new Error('API de storage não disponível.');

    const prefs = {};
    for (const mod of MODULOS) {
      const el = document.getElementById(mod.id);
      prefs[mod.key] = el ? el.checked : true;
    }

    await storage.set({ [STORAGE_KEY]: prefs });
    console.log('[PJeT Popup] Preferências salvas:', prefs);

    // Notifica background ou abas ativas
    try {
      const tabs = await _browser.tabs.query({ active: true, currentWindow: true });
      if (tabs[0]?.id) {
        _browser.tabs.sendMessage(tabs[0].id, {
          tipo: 'pjet_preferencias_atualizadas',
          prefs,
        }).catch(() => {});
      }
    } catch (_) {}

    // Notifica background para difusão ampla
    try {
      _browser.runtime.sendMessage({
        tipo: 'pjet_preferencias_atualizadas',
        prefs
      }).catch(() => {});
    } catch (_) {}

    setStatus('✓ Salvo', 'ok');
    clearStatusAfter(1800);
  } catch (e) {
    setStatus('Erro ao salvar', 'err');
    console.error('[PJeT Popup] Erro ao salvar preferências:', e);
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await carregarPreferencias();
  document.getElementById('btn-salvar')?.addEventListener('click', salvarPreferencias);
});
