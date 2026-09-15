'use strict';

// ── PJeT — content/loader.js ─────────────────────────────────────
// Orquestrador principal da extensão.
// Lê preferências do storage, detecta contexto SPA e inicializa
// os módulos ativos com logging estruturado e rastreamento de erros.
// ─────────────────────────────────────────────────────────────────

const _browser = typeof browser !== 'undefined' ? browser : (typeof chrome !== 'undefined' ? chrome : null);
const STORAGE_KEY = 'pjet_modulos';

// Logger de fallback caso core/logger.js falhe em carregar
const log = window.PJeLogger || {
  boot:    (...a) => console.log('[PJeT::BOOT]', ...a),
  loader:  (...a) => console.log('[PJeT::LOADER]', ...a),
  router:  (...a) => console.log('[PJeT::ROUTER]', ...a),
  dom:     (...a) => console.log('[PJeT::DOM]', ...a),
  warn:    (c, ...a) => console.warn(`[PJeT::${c}]`, ...a),
  error:   (c, m, e) => console.error(`[PJeT::${c} ERRO] ${m}:`, e),
  success: (c, ...a) => console.log(`[PJeT::${c}] ✅`, ...a),
};

// Anti-execução dupla
if (window.__pjetLoaderAtivo) {
  log.warn('LOADER', 'Loader já ativo nesta aba — ignorando injeção duplicada.');
  throw new Error('[PJeT] loader já ativo — ignorando injeção dupla');
}
window.__pjetLoaderAtivo = true;

// ── Helpers ───────────────────────────────────────────────────────

/** Lê as preferências do storage de forma segura com fallback. */
async function lerPreferencias() {
  try {
    if (!_browser?.storage?.sync && !_browser?.storage?.local) {
      log.warn('LOADER', 'browser.storage não disponível; usando defaults.');
      return {};
    }
    const storageApi = _browser.storage.sync || _browser.storage.local;
    const result = await storageApi.get(STORAGE_KEY);
    const prefs = result[STORAGE_KEY] || {};
    log.loader('Preferências carregadas:', prefs);
    return prefs;
  } catch (err) {
    log.error('LOADER', 'Falha ao ler preferências do storage', err);
    return {};
  }
}

/** Retorna true se o módulo está habilitado (default: true). */
function modAtivo(prefs, key) {
  return (key in prefs) ? !!prefs[key] : true;
}

// ── Detecção de URL e Contexto ────────────────────────────────────
const url = window.location.href;

const isPje      = url.includes('pje.trt2.jus.br') || url.includes('pje1g.trt2.jus.br');
const isAud      = url.includes('/aud/');
const isReceita  = url.includes('cav.receita.fazenda.gov.br');
const isSimba    = url.includes('simba-novo.redejt');
const isBcb      = url.includes('bcb.gov.br/saj/requisicao-extratos-cadastro');

// Bloqueia em iframes que não sejam AUD
if (window.self !== window.top && !isAud) {
  log.loader('Iframe ignorado (apenas AUD tem suporte em iframe).');
  throw new Error('[PJeT] iframe ignorado (não é AUD)');
}

// ── Inicializador Principal ───────────────────────────────────────
(async function init() {
  try {
    log.boot(`Inicializando PJeT em: ${url}`);
    const prefs = await lerPreferencias();

    // ── Externos: Receita (InfoJud Parte 2) ─────────────────────────
    if (isReceita) {
      log.router('Contexto detectado: Receita Federal (e-CAC InfoJud)');
      return;
    }

    // ── Externos: SIMBA ──────────────────────────────────────────────
    if (isSimba) {
      log.router('Contexto detectado: Portal SIMBA');
      return;
    }

    // ── Externos: BCB (SIMBA BCB) ────────────────────────────────────
    if (isBcb) {
      log.router('Contexto detectado: BCB SAD (Extratos)');
      if (!modAtivo(prefs, 'simba')) {
        log.loader('Módulo SIMBA desativado nas opções do PJeT.');
        return;
      }
      if (document.getElementById('pjet-btn-bcb')) return;

      setTimeout(() => {
        try {
          const btn = document.createElement('button');
          btn.id = 'pjet-btn-bcb';
          btn.textContent = '🦁 Preencher BCB';
          btn.style.cssText =
            'position:fixed;bottom:20px;right:20px;z-index:999999999;' +
            'padding:10px 15px;background:#ff6600;color:#fff;border:none;' +
            'border-radius:4px;font-weight:bold;cursor:pointer;font-size:14px;' +
            'box-shadow:0 2px 8px rgba(0,0,0,.3);';

          btn.onclick = async (e) => {
            e.preventDefault();
            btn.disabled = true;
            btn.textContent = 'Processando...';
            try {
              log.loader('Disparando automação Simba BCB...');
              await window.executarSimbaBcb?.();
              log.success('LOADER', 'Simba BCB concluído.');
            } catch (err) {
              log.error('LOADER', 'Erro na automação BCB', err);
              alert('Erro BCB: ' + err.message);
            }
            btn.textContent = '🦁 Preencher BCB';
            btn.disabled = false;
          };
          document.body?.appendChild(btn);
          log.dom('Botão BCB injetado com sucesso.');
        } catch (err) {
          log.error('DOM', 'Erro ao injetar botão BCB', err);
        }
      }, 800);
      return;
    }

    // ── PJe Principal ────────────────────────────────────────────────
    if (!isPje) {
      log.warn('LOADER', `URL não corresponde a nenhum padrão suportado: ${url}`);
      return;
    }

    log.loader('Contexto detectado: PJe TRT2');

    // Monitoramento SPA — registra pushState e popstate apenas uma vez por aba
    if (!window.__pjetSpaMonitor) {
      window.__pjetSpaMonitor = true;
      log.loader('Registrando monitor de navegação SPA do PJe...');
      window.monitorarSPA?.(() => {
        log.router(`Navegação SPA detectada: ${window.location.href}`);
        setTimeout(() => rotear(prefs), 300);
      });
    }

    rotear(prefs);

  } catch (err) {
    log.error('LOADER', 'Falha crítica durante a inicialização do loader', err);
  }
})();

// ── Roteador de rotas PJe ─────────────────────────────────────────
function rotear(prefs) {
  try {
    const cur = window.location.href;

    const rotaDetalhe   = /\/processo\/\d+\/detalhe/.test(cur);
    const rotaMinutas   = cur.includes('/comunicacoesprocessuais/minutas');
    const rotaObrigacao = cur.includes('/obrigacao-pagar/');
    const rotaAud       = window.location.pathname.startsWith('/aud/') &&
                          window.location.hash.startsWith('#/audiencia');

    // ── /minutas — InfoJud worker ────────────────────────────────────
    if (rotaMinutas) {
      log.router('Rota ativa: Minutas (/comunicacoesprocessuais/minutas)');
      if (!modAtivo(prefs, 'infojud')) {
        log.loader('InfoJud desativado nas preferências.');
        return;
      }
      if (window.__pjetInfojudRodando) return;
      window.__pjetInfojudRodando = true;
      setTimeout(() => {
        try {
          log.loader('Iniciando worker InfoJud...');
          window.runInfojudWorker?.();
        } catch (err) {
          log.error('INFOJUD', 'Erro no worker InfoJud', err);
        } finally {
          window.__pjetInfojudRodando = false;
        }
      }, 1500);
      return;
    }

    // ── /obrigacao-pagar — Débito ────────────────────────────────────
    if (rotaObrigacao) {
      log.router('Rota ativa: Obrigação de Pagar (/obrigacao-pagar/)');
      if (!modAtivo(prefs, 'debito')) {
        log.loader('Débito desativado nas preferências.');
        return;
      }
      setTimeout(() => {
        try {
          if (/\/obrigacao-pagar\/\d+\/cadastro/.test(cur)) {
            log.loader('Disparando PjeRegistrarDebito.onCadastro()');
            window.PjeRegistrarDebito?.onCadastro();
          } else if (/\/obrigacao-pagar\/\d+\/inclusao/.test(cur)) {
            log.loader('Disparando PjeRegistrarDebito.onInclusao()');
            window.PjeRegistrarDebito?.onInclusao();
          }
        } catch (err) {
          log.error('DEBITO', 'Erro no módulo Débito', err);
        }
      }, 1500);
      return;
    }

    // ── /aud/ — Audiência ────────────────────────────────────────────
    if (rotaAud) {
      log.router('Rota ativa: Audiência (/aud/#/audiencia)');
      if (!modAtivo(prefs, 'audiencia')) {
        log.loader('Audiência desativada nas preferências.');
        return;
      }
      setTimeout(() => {
        try {
          const audApi = window.PJeAud || window.wrappedJSObject?.PJeAud;
          if (typeof audApi?.init !== 'function') {
            log.warn('AUD', 'PJeAud.init não encontrado no escopo');
            return;
          }
          if (window.__pjetAudInicializado) return;
          window.__pjetAudInicializado = true;
          log.loader('Inicializando PJeAud...');
          audApi.init();
        } catch (err) {
          log.error('AUD', 'Erro ao inicializar Audiência', err);
        }
      }, 1500);
      return;
    }

    // ── /detalhe — módulos principais ───────────────────────────────
    if (rotaDetalhe) {
      log.router('Rota ativa: Detalhe do Processo (/processo/:id/detalhe)');
      window.PJeState?.dispose?.();
      bootDetalhe(prefs);
      return;
    }

    log.router(`Rota informativa: nenhuma ação automatizada para ${cur}`);

  } catch (err) {
    log.error('ROUTER', 'Erro ao rotear URL', err);
  }
}

// ── Boot da rota /detalhe ─────────────────────────────────────────
function bootDetalhe(prefs) {
  try {
    if (!/\/processo\/\d+\/detalhe/.test(window.location.href)) return;

    if (!window.PJeState) {
      log.error('STATE', 'window.PJeState não encontrado! Verifique se core/state.js foi carregado.');
      return;
    }
    if (window.PJeState._iniciado) {
      log.loader('bootDetalhe: processo já inicializado no PJeState.');
      return;
    }

    window.PJeState._iniciado = true;
    log.loader('Iniciando componentes da rota /detalhe...');

    // Painel flutuante
    try {
      if (typeof window.inicializarPainel === 'function') {
        window.inicializarPainel(prefs);
        log.success('PAINEL', 'Painel flutuante inicializado.');
      } else {
        log.warn('PAINEL', 'window.inicializarPainel não encontrado.');
      }
    } catch (err) {
      log.error('PAINEL', 'Erro ao inicializar painel flutuante', err);
    }

    // Atalhos de teclado
    try {
      if (typeof window.initAtalhos === 'function') {
        window.initAtalhos();
        log.loader('Atalhos de teclado vinculados.');
      }
    } catch (err) {
      log.error('ATALHOS', 'Erro ao inicializar atalhos de teclado', err);
    }

    // HCalc
    if (modAtivo(prefs, 'hcalc')) {
      log.loader('HCalc ativo nas preferências. Aguardando estabilização do PJe...');
      aguardarPJe(() => {
        if (typeof window.hcalcInitBotao === 'function') {
          try {
            window.hcalcInitBotao();
            log.success('HCALC', 'Botão HCalc anexado.');
          } catch (e) {
            log.error('HCALC', 'Erro ao executar hcalcInitBotao', e);
          }
        } else {
          log.warn('HCALC', 'hcalcInitBotao não encontrado.');
        }
      });
    }

  } catch (err) {
    log.error('LOADER', 'Erro fatal no bootDetalhe', err);
  }
}

// ── Aguarda Angular/DOM do PJe estabilizar ─────────────────────────
function aguardarPJe(cb, tentativas = 0) {
  if (tentativas > 40) {
    log.warn('DOM', 'Timeout aguardando DOM do PJe (40 tentativas atingidas).');
    return;
  }
  const pronto =
    document.querySelector('pje-cabecalho') ||
    document.querySelector('li.tl-item-container') ||
    document.querySelector('[class*="processo"]');

  if (pronto) {
    log.dom(`DOM do PJe estabilizado após ${tentativas} tentativa(s).`);
    cb();
  } else {
    setTimeout(() => aguardarPJe(cb, tentativas + 1), 200);
  }
}

// ── Listener de atualização em tempo real (vindo do popup) ────────
if (_browser?.runtime?.onMessage) {
  _browser.runtime.onMessage.addListener((msg) => {
    if (msg?.tipo === 'pjet_preferencias_atualizadas') {
      log.loader('Recebida notificação de atualização de preferências. Recarregando página...');
      window.location.reload();
    }
  });
}
