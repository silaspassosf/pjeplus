// ── PJeT — background/background.js ─────────────────────────────
// Script de background (compatível com Firefox MV3 scripts e Chrome MV3 SW).
// Gerencia instalação, ciclo de vida e comunicação com abas.
'use strict';

const _browser = typeof browser !== 'undefined' ? browser : chrome;

console.log('%c[PJeT::BG]%c Background script inicializado.', 'background:#4a148c;color:#fff;font-weight:bold;padding:2px 6px;border-radius:3px;', 'color:inherit;');

// Ciclo de vida para Service Worker (se executado como tal)
if (typeof self.skipWaiting === 'function') {
  self.addEventListener('install', () => {
    console.log('[PJeT::BG] Service Worker instalado. Executando skipWaiting.');
    self.skipWaiting();
  });
  self.addEventListener('activate', () => {
    console.log('[PJeT::BG] Service Worker ativado.');
  });
}

// Evento de instalação / atualização da extensão
_browser.runtime.onInstalled?.addListener((details) => {
  console.log(`[PJeT::BG] Extensão instalada/atualizada (motivo: ${details.reason}, versão anterior: ${details.previousVersion || 'n/a'}).`);
});

// Repassar mensagens do popup/options para os content scripts das abas PJe
_browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.tipo === 'pjet_preferencias_atualizadas') {
    console.log('[PJeT::BG] Preferências atualizadas. Propagando para abas ativas...');
    _browser.tabs.query({ url: ['https://pje.trt2.jus.br/*', 'https://pje1g.trt2.jus.br/*'] })
      .then(tabs => {
        let count = 0;
        tabs.forEach(tab => {
          if (tab.id) {
            _browser.tabs.sendMessage(tab.id, msg).catch(() => {});
            count++;
          }
        });
        console.log(`[PJeT::BG] Mensagem enviada para ${count} aba(s) PJe.`);
      })
      .catch(err => console.error('[PJeT::BG] Erro ao consultar abas:', err));
  }
  return false;
});
