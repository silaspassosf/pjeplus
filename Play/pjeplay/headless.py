"""pjeplay.headless — Camada headless não invasiva para PJePlus.

Ativa-se EXCLUSIVAMENTE quando driver.headless é True.
Em modo visível (headed), este módulo não é importado pelo launcher.

Responsabilidades comprovadas:
1. Virtual Clipboard Polyfill: intercepta cópias na página (execCommand,
   navigator.clipboard.writeText, DataTransfer) e supre pyperclip.paste()
   em ambiente headless onde o SO não recebe o clipboard gráfico.
2. Recovery Headless-Aware: assegura que chamadas ao mecanismo de recovery
   em Fix.utils recriem o driver com headless=True.
"""
import logging
import sys
from typing import Any, Optional

logger = logging.getLogger("pjeplay")

_JS_CLIPBOARD = """(() => {
  if (window.__pjeplay_clipboard_installed) return;
  window.__pjeplay_clipboard_installed = true;
  window.__pjeplay_clipboard = window.__pjeplay_clipboard || '';

  function extrairTextoAtivo() {
    try {
      const el = document.activeElement;
      if (el && (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT')) {
        const s = el.selectionStart;
        const e = el.selectionEnd;
        if (typeof s === 'number' && typeof e === 'number' && s !== e) {
          return el.value.substring(s, e);
        }
        return el.value || '';
      }
      if (window.getSelection) {
        const sel = window.getSelection();
        if (sel) {
          const s = sel.toString();
          if (s) return s;
        }
      }
    } catch (_) {}
    return '';
  }

  // 1. DataTransfer.prototype.setData (quando scripts usam e.clipboardData.setData)
  try {
    if (typeof DataTransfer !== 'undefined' && DataTransfer.prototype && DataTransfer.prototype.setData) {
      const origSetData = DataTransfer.prototype.setData;
      DataTransfer.prototype.setData = function(format, data) {
        try {
          if (typeof format === 'string' && (format.toLowerCase() === 'text/plain' || format.toLowerCase() === 'text')) {
            window.__pjeplay_clipboard = String(data || '');
          }
        } catch (_) {}
        return origSetData.apply(this, arguments);
      };
    }
  } catch (_) {}

  // 2. Listener de 'copy' em fase de captura
  try {
    document.addEventListener('copy', function(e) {
      try {
        const txt = extrairTextoAtivo();
        if (txt) {
          window.__pjeplay_clipboard = txt;
        }
      } catch (_) {}
    }, true);
  } catch (_) {}

  // 3. Envolver document.execCommand('copy')
  try {
    if (document.execCommand) {
      const origExec = document.execCommand.bind(document);
      document.execCommand = function(cmd, ...args) {
        let ret = false;
        try {
          ret = origExec(cmd, ...args);
        } catch (_) {
          ret = false;
        }
        if (String(cmd).toLowerCase() === 'copy') {
          try {
            const txt = extrairTextoAtivo();
            if (txt) {
              window.__pjeplay_clipboard = txt;
            }
          } catch (_) {}
        }
        return ret;
      };
    }
  } catch (_) {}

  // 4. Envolver navigator.clipboard.writeText
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      const origWriteText = navigator.clipboard.writeText.bind(navigator.clipboard);
      navigator.clipboard.writeText = function(text) {
        try {
          window.__pjeplay_clipboard = String(text || '');
        } catch (_) {}
        try {
          return origWriteText(text).catch(() => {});
        } catch (_) {
          return Promise.resolve();
        }
      };
    }
  } catch (_) {}
})();"""

_paste_original = None
_instalado_clipboard = False
_instalado_recovery = False
_obter_padronizado_original = None
_driver_pc_original = None
_driver_registrado = None


def _obter_driver_ativo() -> Optional[Any]:
    global _driver_registrado
    try:
        from . import api_resiliencia
        d = getattr(api_resiliencia, "_driver_ativo", None)
        if d is not None:
            return d
    except Exception:
        pass
    return _driver_registrado


def ler_clipboard_virtual(drv: Any) -> str:
    """Lê e consome o valor de window.__pjeplay_clipboard do driver headless."""
    if drv is None:
        return ""
    js_ler_e_limpar = (
        "() => { const t = window.__pjeplay_clipboard || ''; "
        "window.__pjeplay_clipboard = ''; return t; }"
    )
    # 1. Tentar ler da página ativa
    try:
        p = getattr(drv, "page", None)
        if p and not p.is_closed():
            val = p.evaluate(js_ler_e_limpar)
            if val:
                return str(val)
    except Exception as e:
        logger.debug("headless: erro ao ler clipboard da pagina ativa: %s", e)

    # 2. Se vazio, tentar em outras páginas vivas do contexto
    try:
        ctx = getattr(drv, "_context", None)
        if ctx:
            for pg in getattr(ctx, "pages", []):
                try:
                    if not pg.is_closed():
                        val = pg.evaluate(js_ler_e_limpar)
                        if val:
                            return str(val)
                except Exception:
                    continue
    except Exception as e:
        logger.debug("headless: erro ao varrer abas para clipboard: %s", e)

    return ""


def _paste_headless() -> str:
    drv = _obter_driver_ativo()
    if drv is not None and getattr(drv, "headless", False):
        txt = ler_clipboard_virtual(drv)
        return txt or ""
    if _paste_original is not None:
        return _paste_original()
    return ""


def _instalar_clipboard_virtual() -> None:
    global _instalado_clipboard, _paste_original
    if _instalado_clipboard:
        return
    try:
        import pyperclip
        _paste_original = pyperclip.paste
        pyperclip.paste = _paste_headless
        _instalado_clipboard = True
        logger.debug("headless: clipboard virtual instalado em pyperclip.paste")
    except ImportError:
        logger.debug("headless: pyperclip nao disponivel no ambiente")
    except Exception as e:
        logger.warning("headless: falha ao instalar clipboard virtual: %s", e)


def _instalar_recovery_headless() -> None:
    global _instalado_recovery, _obter_padronizado_original, _driver_pc_original
    if _instalado_recovery:
        return
    try:
        import Fix.utils as u
        if hasattr(u, "obter_driver_padronizado"):
            _obter_padronizado_original = u.obter_driver_padronizado

            def _obter_driver_padronizado_headless(*args, **kwargs):
                kwargs["headless"] = True
                return _obter_padronizado_original(*args, **kwargs)

            u.obter_driver_padronizado = _obter_driver_padronizado_headless

            if hasattr(u, "driver_pc"):
                _driver_pc_original = u.driver_pc

                def _driver_pc_headless(*args, **kwargs):
                    kwargs["headless"] = True
                    return _obter_driver_padronizado_headless(*args, **kwargs)

                u.driver_pc = _driver_pc_headless

            for mod_nome in ("Fix.core", "Fix.facade_publica"):
                mod = sys.modules.get(mod_nome)
                if mod and hasattr(mod, "obter_driver_padronizado"):
                    setattr(mod, "obter_driver_padronizado", _obter_driver_padronizado_headless)

            _instalado_recovery = True
            logger.debug("headless: recovery configurado para manter headless=True")
    except Exception as e:
        logger.debug("headless: recovery patch nao aplicado (%s)", e)


def ativar_para_driver(driver: Any) -> None:
    """Chamado pelo launcher quando driver.headless é True."""
    if not getattr(driver, "headless", False):
        return

    global _driver_registrado
    _driver_registrado = driver

    # 1. Injetar JS de clipboard no contexto Playwright
    try:
        ctx = getattr(driver, "_context", None)
        if ctx and hasattr(ctx, "add_init_script"):
            ctx.add_init_script(_JS_CLIPBOARD)
            try:
                p = getattr(driver, "page", None)
                if p and not p.is_closed():
                    p.evaluate(_JS_CLIPBOARD)
            except Exception:
                pass
    except Exception as e:
        logger.warning("headless: falha ao registrar JS_CLIPBOARD: %s", e)

    # 2. Instalar bridge pyperclip.paste
    _instalar_clipboard_virtual()

    # 3. Assegurar que recovery mantenha headless
    _instalar_recovery_headless()


def desinstalar() -> None:
    """Restaura hooks originais (útil para suíte de testes)."""
    global _instalado_clipboard, _paste_original
    global _instalado_recovery, _obter_padronizado_original, _driver_pc_original
    global _driver_registrado

    _driver_registrado = None

    if _instalado_clipboard and _paste_original is not None:
        try:
            import pyperclip
            pyperclip.paste = _paste_original
        except Exception:
            pass
        _instalado_clipboard = False
        _paste_original = None

    if _instalado_recovery:
        try:
            import Fix.utils as u
            if _obter_padronizado_original is not None:
                u.obter_driver_padronizado = _obter_padronizado_original
            if _driver_pc_original is not None:
                u.driver_pc = _driver_pc_original
        except Exception:
            pass
        _instalado_recovery = False
        _obter_padronizado_original = None
        _driver_pc_original = None
