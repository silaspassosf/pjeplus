"""
Fix/diagnostico_runtime.py - Diagnostico e instrumentacao do runtime PJe Plus.

Consolida os antigos:
    - Fix/log.py                Logger estruturado unificado
    - Fix/debug_interativo.py   Debug interativo com pausa para analise
    - Fix/utils_observer.py     Re-export de aguardar_renderizacao_nativa (Fix.core)
    - Fix/utils_tempo.py        Re-export de medir_tempo / TIME_ENABLED (Fix.core)

Uso:
    from Fix.diagnostico_runtime import logger, log_start, log_fim
    from Fix.diagnostico_runtime import DebugInterativo, on_erro_critico
    from Fix.diagnostico_runtime import aguardar_renderizacao_nativa, medir_tempo
"""

# =============================================================================
# Parte 1 — Logger estruturado (original: Fix/log.py)
# =============================================================================

import os
import logging
import sys

# ── mapeamento de string para nivel ──
_LOG_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}


def _resolver_nivel() -> int:
    """Resolve o nivel de logging a partir de PJE_LOG_LEVEL ou PJEPLUS_DEBUG legado."""
    nivel_str = os.getenv('PJE_LOG_LEVEL', '').strip().upper()
    if nivel_str in _LOG_LEVEL_MAP:
        return _LOG_LEVEL_MAP[nivel_str]

    # Compatibilidade reversa com PJEPLUS_DEBUG
    debug_env = os.getenv('PJEPLUS_DEBUG', '0').lower()
    if debug_env in ('1', 'true', 'on'):
        return logging.DEBUG

    return logging.INFO


class _NivelFormatter(logging.Formatter):
    """Formatter que usa formato compacto para INFO/DEBUG e expandido para ERROR."""

    def format(self, record):
        if record.levelno >= logging.ERROR:
            # Formato: HH:MM:SS [modulo] ERRO em funcao: mensagem
            return ('%(asctime)s [%(module)s] ERRO em %(funcName)s: %(message)s' %
                    {'asctime': self.formatTime(record, '%H:%M:%S'),
                     'module': record.module,
                     'funcName': record.funcName,
                     'message': record.getMessage()})
        # Formato compacto: HH:MM:SS [modulo] mensagem
        return ('%(asctime)s [%(module)s] %(message)s' %
                {'asctime': self.formatTime(record, '%H:%M:%S'),
                 'module': record.module,
                 'message': record.getMessage()})


class PJELogger:
    """Logger estruturado para PJe Plus com niveis configuraveis."""

    def __init__(self, nome='pjeplus'):
        self.logger = logging.getLogger(nome)
        self._configurar()

    def _configurar(self):
        self.logger.setLevel(_resolver_nivel())
        self.logger.handlers.clear()

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_NivelFormatter())
        self.logger.addHandler(handler)

    def debug(self, mensagem):
        self.logger.debug(mensagem)

    def info(self, mensagem):
        self.logger.info(mensagem)

    def warning(self, mensagem):
        self.logger.warning(mensagem)

    def error(self, mensagem):
        self.logger.error(mensagem)


# ── Instancia global ──
_instancia = PJELogger('pjeplus')
logger = _instancia.logger


# ══════════════════════════════════════════════════════
# Funcoes padronizadas de evento
# ══════════════════════════════════════════════════════

def log_start(modulo: str) -> None:
    """Registra inicio de processamento em *modulo*."""
    logger.info('[%s] START', modulo)


def log_item(modulo: str, item_id) -> None:
    """Registra que um item esta sendo processado."""
    logger.info('[%s] ITEM %s', modulo, item_id)


def log_sucesso(modulo: str, item_id) -> None:
    """Registra que um item foi processado com sucesso."""
    logger.info('[%s] SUCESSO %s', modulo, item_id)


def log_erro(modulo: str, item_id, erro) -> None:
    """Registra erro no processamento de um item."""
    logger.error('[%s] ERRO %s: %s', modulo, item_id, erro)


def log_fim(modulo: str, resumo) -> None:
    """Registra conclusao do processamento com *resumo* (dict ou str)."""
    logger.info('[%s] FIM %s', modulo, resumo)


# ── funcoes legadas ──

def get_module_logger(module_name: str):
    """Compatibilidade para modulos que pedem logger nomeado por modulo."""
    return logging.getLogger(module_name)


def getmodulelogger(module_name: str):
    """Alias legado de get_module_logger."""
    return get_module_logger(module_name)


def _log_info(message: str):
    logger.info(message)


def _log_error(message: str):
    logger.error(message)


def log_seletor_multiplo(prefixo: str, seletor: str, status: str, erro: str = None) -> None:
    if status == 'FALHA' and erro:
        logger.warning(f"{prefixo}[{status}] {seletor} :: {erro}")
        return
    logger.info(f"{prefixo}[{status}] {seletor}")


# =============================================================================
# Parte 2 — Debug interativo (original: Fix/debug_interativo.py)
# =============================================================================

import time as _time_module
from datetime import datetime as _datetime
from typing import Optional, Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver


class DebugInterativo:
    """
    Sistema de debug que pausa execucao em erros criticos.
    Permite analise e correcao interativa de problemas headless.
    """

    # Padroes de erro que devem pausar execucao
    ERROS_CRITICOS = [
        'click intercepted',
        'element click intercepted',
        'obscures it',
        'not clickable at point',
        'backdrop',
        'overlay',
        'timeout',
        'timed out',
        'no such element',
        'stale element',
    ]

    def __init__(self, enabled: bool = False, debug_dir: str = "debug_interativo",
                 auto_mode: bool = False):
        self.enabled = enabled
        self.auto_mode = auto_mode
        self.debug_dir = debug_dir
        self.erro_count = 0
        self.pausa_count = 0
        self.screenshots_salvos = []
        self.erros_log = []

        if enabled and not os.path.exists(debug_dir):
            os.makedirs(debug_dir)

    def is_erro_critico(self, erro_msg: str) -> bool:
        """Verifica se erro e critico o suficiente para pausar"""
        if not erro_msg:
            return False

        erro_lower = str(erro_msg).lower()
        return any(padrao in erro_lower for padrao in self.ERROS_CRITICOS)

    def capturar_contexto(self, driver: WebDriver, erro_msg: str) -> Dict[str, Any]:
        """Captura screenshot e contexto do DOM para analise"""
        timestamp = _datetime.now().strftime('%Y%m%d_%H%M%S')
        contexto = {
            'timestamp': timestamp,
            'erro_msg': erro_msg,
            'url': None,
            'screenshot': None,
            'html': None,
            'overlays': [],
        }

        try:
            contexto['url'] = driver.current_url
        except Exception:
            pass

        try:
            screenshot_path = os.path.join(self.debug_dir, f'erro_{timestamp}.png')
            driver.save_screenshot(screenshot_path)
            contexto['screenshot'] = screenshot_path
            self.screenshots_salvos.append(screenshot_path)
            print(f" Screenshot salvo: {screenshot_path}")
        except Exception as e:
            print(f" Erro ao salvar screenshot: {e}")

        try:
            overlays = driver.execute_script("""
                const overlays = [];

                document.querySelectorAll('.cdk-overlay-backdrop').forEach(el => {
                    overlays.push({
                        type: 'cdk-backdrop',
                        classes: el.className,
                        visible: el.offsetParent !== null,
                        zIndex: window.getComputedStyle(el).zIndex
                    });
                });

                document.querySelectorAll('.modal-backdrop, .fade.show').forEach(el => {
                    overlays.push({
                        type: 'modal-backdrop',
                        classes: el.className,
                        visible: el.offsetParent !== null
                    });
                });

                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    const zIndex = parseInt(window.getComputedStyle(el).zIndex);
                    if (zIndex > 1000 && el.offsetParent !== null) {
                        overlays.push({
                            type: 'high-zindex',
                            tag: el.tagName,
                            classes: el.className,
                            zIndex: zIndex
                        });
                    }
                });

                return overlays;
            """)
            contexto['overlays'] = overlays
            if overlays:
                print(f" Overlays detectados: {len(overlays)}")
                for ov in overlays[:3]:
                    print(f"   - {ov.get('type')}: z-index={ov.get('zIndex', 'N/A')}")
        except Exception:
            pass

        try:
            html_path = os.path.join(self.debug_dir, f'dom_{timestamp}.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            contexto['html'] = html_path
            print(f" HTML salvo: {html_path}")
        except Exception as e:
            print(f" Erro ao salvar HTML: {e}")

        return contexto

    def pausar_para_analise(self, driver: WebDriver, erro_msg: str, contexto_extra: dict = None) -> str:
        """
        Pausa execucao em modo interativo para analise de erro.
        Em modo auto, aplica fix automatico e continua.

        Returns:
            'c' = continuar
            's' = skip (pular este item)
            'a' = abortar execucao
            'f' = fix (tentar correcao automatica)
        """
        if not self.enabled:
            return 'c'

        self.pausa_count += 1

        erro_info = {
            'numero': self.pausa_count,
            'mensagem': erro_msg[:500],
            'contexto': contexto_extra,
            'timestamp': _datetime.now().isoformat()
        }
        self.erros_log.append(erro_info)

        print("\n" + "=" * 80)
        print(" DEBUG INTERATIVO - ERRO CRITICO DETECTADO")
        print("=" * 80)
        print(f"Pausa #{self.pausa_count} | Erros totais: {self.erro_count}")
        print(f"\n Erro: {erro_msg[:200]}")

        contexto = self.capturar_contexto(driver, erro_msg)

        if contexto_extra:
            print(f"\n Contexto adicional:")
            for key, value in contexto_extra.items():
                print(f"   {key}: {value}")

        if self.auto_mode:
            print("\n MODO AUTOMATICO ATIVADO")
            print("   Aplicando correcao automatica...")
            self._tentar_fix_automatico(driver)
            self._salvar_relatorio_erro(erro_info, contexto)
            print("    Continuando execucao automaticamente...")
            return 'f'

        print("\n" + "-" * 80)
        print("OPCOES:")
        print("  [C] Continuar - Tenta continuar execucao")
        print("  [S] Skip - Pula este item e vai para o proximo")
        print("  [F] Fix - Tenta correcao automatica (limpa overlays)")
        print("  [I] Info - Mostra mais informacoes do erro")
        print("  [A] Abortar - Para execucao completamente")
        print("-" * 80)

        while True:
            try:
                escolha = input("\n Escolha uma opcao [C/S/F/I/A]: ").strip().upper()

                if escolha == 'C':
                    print(" Continuando execucao...")
                    return 'c'

                elif escolha == 'S':
                    print(" Pulando item atual...")
                    return 's'

                elif escolha == 'F':
                    print(" Tentando correcao automatica...")
                    self._tentar_fix_automatico(driver)
                    return 'f'

                elif escolha == 'I':
                    self._mostrar_info_detalhada(contexto)
                    continue

                elif escolha == 'A':
                    print(" Abortando execucao...")
                    return 'a'

                else:
                    print(" Opcao invalida. Use C, S, F, I ou A.")

            except (KeyboardInterrupt, EOFError):
                print("\n Interrompido pelo usuario - Abortando")
                return 'a'

    def _tentar_fix_automatico(self, driver: WebDriver):
        """Tenta correcoes automaticas conhecidas"""
        print(" Aplicando correcoes automaticas:")

        try:
            print("   - Limpando overlays...")
            from Fix.headless_helpers import limpar_overlays_headless
            limpar_overlays_headless(driver)
            _time_module.sleep(0.5)
            print("    Overlays limpos")
        except Exception as e:
            print(f"    Erro ao limpar overlays: {e}")

        try:
            print("   - Scroll para topo da pagina...")
            driver.execute_script("window.scrollTo(0, 0);")
            _time_module.sleep(0.3)
            print("    Scroll realizado")
        except Exception as e:
            print(f"    Erro no scroll: {e}")

        try:
            print("   - Fechando modals...")
            driver.execute_script("""
                document.querySelectorAll('.modal .close, .modal button[aria-label*="fechar"]').forEach(el => {
                    el.click();
                });
                document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
            """)
            _time_module.sleep(0.5)
            print("    Modals processados")
        except Exception as e:
            print(f"    Erro ao fechar modals: {e}")

        print(" Correcoes automaticas aplicadas")

    def _salvar_relatorio_erro(self, erro_info: Dict, contexto: Dict):
        """Salva relatorio detalhado do erro para analise"""
        try:
            relatorio_path = os.path.join(self.debug_dir, f'erro_{erro_info["numero"]:03d}_relatorio.json')
            relatorio = {
                **erro_info,
                'screenshot': contexto.get('screenshot'),
                'html': contexto.get('html'),
                'url': contexto.get('url'),
                'overlays_count': len(contexto.get('overlays', [])),
                'overlays': contexto.get('overlays', [])[:5],
            }

            import json
            with open(relatorio_path, 'w', encoding='utf-8') as f:
                json.dump(relatorio, f, indent=2, ensure_ascii=False)

            print(f"    Relatorio salvo: {relatorio_path}")
        except Exception as e:
            print(f"    Erro ao salvar relatorio: {e}")

    def obter_relatorio_final(self) -> Dict[str, Any]:
        """Retorna relatorio final de todos os erros encontrados"""
        return {
            'total_erros': self.erro_count,
            'total_pausas': self.pausa_count,
            'screenshots': self.screenshots_salvos,
            'erros_detalhados': self.erros_log,
            'modo_automatico': self.auto_mode,
        }

    def _mostrar_info_detalhada(self, contexto: Dict[str, Any]):
        """Mostra informacoes detalhadas do erro"""
        print("\n" + "=" * 80)
        print(" INFORMACOES DETALHADAS")
        print("=" * 80)

        print(f"\n Timestamp: {contexto['timestamp']}")
        print(f" URL: {contexto['url']}")
        print(f" Screenshot: {contexto['screenshot']}")
        print(f" HTML: {contexto['html']}")

        if contexto['overlays']:
            print(f"\n Overlays encontrados ({len(contexto['overlays'])}):")
            for ov in contexto['overlays']:
                print(f"   - Tipo: {ov.get('type')}")
                print(f"     Classes: {ov.get('classes', 'N/A')}")
                print(f"     Z-Index: {ov.get('zIndex', 'N/A')}")
                print(f"     Visivel: {ov.get('visible', 'N/A')}")
                print()
        else:
            print("\n Nenhum overlay detectado")

        print("\n SUGESTOES:")
        print("   1. Abra o screenshot para ver estado visual")
        print("   2. Verifique o HTML para encontrar elementos bloqueadores")
        print("   3. Use opcao [F] para tentar correcao automatica")
        print("   4. Se persistir, reporte o erro com screenshot/HTML")
        print("=" * 80)


# Singleton global
_debug = None


def get_debug_interativo() -> Optional[DebugInterativo]:
    """Retorna instancia do debug interativo (ou None se nao inicializado)"""
    return _debug


def on_erro_critico(driver: WebDriver, erro_msg: str,
                    contexto: Optional[Dict] = None) -> str:
    """
    Callback para ser chamado quando erro critico ocorre.

    Returns:
        'c' = continuar, 's' = skip, 'a' = abortar, 'f' = fix
    """
    debug = get_debug_interativo()
    if not debug or not debug.enabled:
        return 'c'

    debug.erro_count += 1

    if debug.is_erro_critico(erro_msg):
        return debug.pausar_para_analise(driver, erro_msg, contexto)

    return 'c'


# =============================================================================
# Parte 3 — Re-exports de Fix.core (original: Fix/utils_observer.py, Fix/utils_tempo.py)
#
# Usam __getattr__  + importlib p/ evitar circular import:
#   Fix.core → Fix.log (shim) → Fix.diagnostico_runtime → ??? → Fix.core
# =============================================================================

def __getattr__(name):
    """Lazy re-exports from Fix.core to avoid circular imports."""
    _CORE_LAZY = {
        'aguardar_renderizacao_nativa': 'aguardar_renderizacao_nativa',
        'medir_tempo': 'medir_tempo',
        'TIME_ENABLED': 'TIME_ENABLED',
    }
    if name in _CORE_LAZY:
        import importlib
        mod = importlib.import_module('Fix.core')
        return getattr(mod, _CORE_LAZY[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# =============================================================================
# Public API (__all__)
# =============================================================================

__all__ = [
    # Logger
    'logger', 'PJELogger',
    'log_start', 'log_item', 'log_sucesso', 'log_erro', 'log_fim',
    'get_module_logger', 'getmodulelogger',
    '_log_info', '_log_error',
    'log_seletor_multiplo',
    # Debug interativo
    'DebugInterativo', 'get_debug_interativo', 'on_erro_critico',
    # Re-exports de Fix.core
    'aguardar_renderizacao_nativa', 'medir_tempo', 'TIME_ENABLED',
]
