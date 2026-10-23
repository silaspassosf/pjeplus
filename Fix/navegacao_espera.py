"""navegacao_espera — extraído de Fix/core.py (F7: split verbatim, re-exportado pelo core).

Corpos idênticos aos originais (mesma ordem interna). O grafo entre módulos é
acíclico: navegacao_espera <- navegacao <- entrada_campos; documentos_cp e
filtros_painel são folhas. """

import re
import time

from .log import logger
from Play.pjeplay.locators import By
from typing import Any
from typing import Optional
from typing import Union

from Fix import espera

# Constantes de módulo que acompanham este grupo (usadas por suas funções).
TIME_ENABLED = True

def medir_tempo(label: str = None):
    """Decorator simples para medir tempo de funções de alto nível."""
    def _decorator(func):
        def _wrapper(*args, **kwargs):
            if not TIME_ENABLED:
                return func(*args, **kwargs)
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.time() - start
                logger.info('[TEMPO] %s.%s: %.3fs', func.__name__, label or func.__name__, elapsed)
        try:
            _wrapper.__name__ = func.__name__
            _wrapper.__doc__ = func.__doc__
        except Exception as e:
            logger.debug("medir_tempo: falha ao copiar __name__/__doc__: %s", e)
            pass
        return _wrapper
    return _decorator

def aguardar_renderizacao_nativa(
    driver,
    seletor: Optional[str] = None,
    modo: str = "aparecer",
    timeout: Union[int, float] = 10,
):
    """Contrato estável para espera de renderização e transição de DOM."""
    timeout_segundos = float(timeout)
    try:
        if not seletor:
            return espera.ate_js(driver, "document.readyState === 'complete'", teto=timeout_segundos)

        if modo == "sumir":
            return espera.ate_sumir(driver, seletor, teto=timeout_segundos)

        if modo == "habilitado":
            return espera.ate_habilitar(driver, seletor, teto=timeout_segundos)

        return espera.ate_aparecer(driver, seletor, teto=timeout_segundos)
    except Exception as e:
        logger.warning("aguardar_renderizacao_nativa: %s", e)
        return False

def wait(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    """Espera até que um elemento esteja visível na página."""
    try:
        sel = selector
        if by:
            from Play.pjeplay.locators import traduzir
            sel = traduzir(by, selector)
        if espera.ate_aparecer(driver, sel, teto=timeout):
            return espera.elemento(driver, sel)
        logger.error(f'[WAIT][ERRO] Elemento não encontrado: {selector}')
        return None
    except Exception:
        logger.error(f'[WAIT][ERRO] Elemento não encontrado: {selector}')
        return None

def garantir_carregamento_pagina(
    driver: Any,
    seletor_esperado: Optional[str] = None,
    timeout_refresh: Optional[float] = None,
    timeout_pos_refresh: float = 10.0,
    log: bool = True,
    url_alvo: Optional[str] = None,
) -> bool:
    """Garante carregamento da página com barreira anti-travamento.

    Se qualquer elemento válido de conteúdo for detectado dentro do timeout,
    o refresh é cancelado/abortado na hora e a página segue.
    Se passar do tempo sem qualquer elemento válido no DOM, tenta destravar
    e aguarda recuperação pós-recuperação.
    """
    if hasattr(driver, 'garantir_carregamento'):
        try:
            return driver.garantir_carregamento(
                seletor_esperado=seletor_esperado,
                timeout_refresh=timeout_refresh,
                timeout_pos_refresh=timeout_pos_refresh,
                log=log,
                url_alvo=url_alvo,
            )
        except Exception as e:
            logger.warning("[CARREGAMENTO] Erro ao delegar garantir_carregamento para driver: %s", e)

    target_url = url_alvo or getattr(driver, '_ultima_url_navegada', None) or getattr(driver, 'current_url', '')
    is_processo_ou_tarefa = bool(target_url and ('/processo/' in target_url or '/tarefa/' in target_url))

    if timeout_refresh is None:
        timeout_refresh = 10.0 if is_processo_ou_tarefa else 5.0

    # Fallback genérico caso o driver não seja PWDriver direto
    js_verificar = """
    (args) => {
        const seletorExtra = args.seletorExtra;
        const isProcessoOuTarefa = args.isProcessoOuTarefa;

        if (seletorExtra) {
            try {
                const extraEls = document.querySelectorAll(seletorExtra);
                for (let i = 0; i < extraEls.length; i++) {
                    const el = extraEls[i];
                    if (el && (el.getClientRects().length > 0 || (el.offsetWidth > 0 && el.offsetHeight > 0))) {
                        return { ok: true, seletor: seletorExtra, tag: el.tagName.toLowerCase() };
                    }
                }
            } catch(e) {}
            return { ok: false, seletor: null, tag: null };
        }
        const seletoresPje = [
            'pje-cabecalho-processo',
            'pje-cabecalho-tarefa',
            'pje-timeline',
            'pje-botoes-transicao button',
            'pje-concluso-tarefa-botao button',
            'pje-arvore-modelo-documento',
            'input#inputFiltro',
            'pje-detalhes-processo',
            'mat-tab-group',
            'button[aria-label*="Conclusão"]',
            'button[aria-label*="Análise"]'
        ];
        if (!isProcessoOuTarefa) {
            seletoresPje.push('#botao-menu');
        }
        for (let i = 0; i < seletoresPje.length; i++) {
            const sel = seletoresPje[i];
            const el = document.querySelector(sel);
            if (el && (el.getClientRects().length > 0 || (el.offsetWidth > 0 && el.offsetHeight > 0))) {
                return { ok: true, seletor: sel, tag: el.tagName.toLowerCase() };
            }
        }
        if (!isProcessoOuTarefa) {
            const appRoot = document.querySelector('app-root');
            if (appRoot && appRoot.children.length > 0) {
                const filhosReais = Array.from(appRoot.children).filter(c => {
                    const tag = c.tagName.toLowerCase();
                    const cls = (c.className || '').toLowerCase();
                    return !cls.includes('splash') && 
                           !cls.includes('spinner') && 
                           !cls.includes('carregando') &&
                           tag !== 'mat-progress-bar';
                });
                for (let i = 0; i < filhosReais.length; i++) {
                    const f = filhosReais[i];
                    if (f && (f.getClientRects().length > 0 || (f.offsetWidth > 0 && f.offsetHeight > 0))) {
                        return { ok: true, seletor: 'app-root > ' + f.tagName.toLowerCase(), tag: f.tagName.toLowerCase() };
                    }
                }
            }
        }
        return { ok: false, seletor: null, tag: null };
    }
    """
    payload = {"seletorExtra": seletor_esperado, "isProcessoOuTarefa": is_processo_ou_tarefa}

    t_inicio = time.time()
    alvo_str = f" [alvo: {seletor_esperado}]" if seletor_esperado else ""
    if log:
        logger.info(f"[CARREGAMENTO] ⏳ Monitorando carregamento inicial (barreira de {timeout_refresh:.1f}s){alvo_str}...")

    def _eval():
        if hasattr(driver, 'page') and driver.page:
            return driver.page.evaluate(js_verificar, payload)
        fn = getattr(driver, 'execute_script', None)
        if fn:
            return fn(js_verificar, payload)
        return None

    while time.time() - t_inicio < timeout_refresh:
        try:
            res = _eval()
            if res and res.get('ok'):
                elapsed = time.time() - t_inicio
                sel_achado = res.get('seletor') or res.get('tag')
                if log:
                    logger.info(f"[CARREGAMENTO] ✅ Elemento válido detectado em {elapsed:.2f}s ({sel_achado}) — página viva, refresh abortado.")
                return True
        except Exception:
            pass
        espera.assentar(driver, 0.15)

    elapsed_antes = time.time() - t_inicio
    if log:
        logger.warning(
            f"[CARREGAMENTO] ⚠️ Nenhum elemento válido detectado após {elapsed_antes:.2f}s "
            f"(lentidão/travamento sistêmico detectado) — tentando destravar..."
        )

    try:
        if target_url and ('/tarefa/' in target_url or '/processo/' in target_url) and hasattr(driver, 'page') and driver.page:
            driver.page.goto(target_url)
        elif hasattr(driver, 'refresh'):
            driver.refresh()
        elif hasattr(driver, 'page') and driver.page:
            driver.page.reload()
    except Exception as e:
        if log:
            logger.warning(f"[CARREGAMENTO] Falha ao executar refresh: {e}")

    if log:
        logger.info(f"[CARREGAMENTO] 🔄 Recuperação executada. Monitorando recuperação pós-recuperação (teto de {timeout_pos_refresh:.1f}s)...")

    t_pos = time.time()
    while time.time() - t_pos < timeout_pos_refresh:
        try:
            res = _eval()
            if res and res.get('ok'):
                elapsed_pos = time.time() - t_pos
                sel_achado = res.get('seletor') or res.get('tag')
                if log:
                    logger.info(f"[CARREGAMENTO] ✅ Elemento válido detectado pós-recuperação em {elapsed_pos:.2f}s ({sel_achado}) — página destravada com sucesso.")
                return True
        except Exception:
            pass
        espera.assentar(driver, 0.2)

    if log:
        logger.error(f"[CARREGAMENTO] ❌ Página não renderizou elemento válido após recuperação ({timeout_pos_refresh:.1f}s).")
    return False

def wait_for_page_load(driver, timeout=10, seletor=None):
    """Compatibilidade para esperar o carregamento básico da página com proteção de 5s."""
    try:
        return garantir_carregamento_pagina(driver, seletor_esperado=seletor, timeout_refresh=min(5.0, float(timeout)))
    except Exception as e:
        logger.warning("wait_for_page_load: %s", e)
        return False

def extrair_id_processo(driver) -> Optional[str]:
    """ID numérico do processo na URL atual do PJe (`/processo/{id}`).

    Leitura direta da URL — sem tocar no DOM e sem dependência de motor. Ponto
    único para quem precisa do id nas chamadas de API (`cliente_para` +
    `partes`/`domicilio_eletronico`/`obter_texto_documento`).
    """
    try:
        m = re.search(r'/processo/(\d+)', getattr(driver, 'current_url', '') or '')
        return m.group(1) if m else None
    except Exception as e:
        logger.debug('extrair_id_processo: %s', e)
        return None

def wait_for_visible(driver, selector, timeout=10, by=None):
    """Wait for an element to be visible in the DOM."""
    try:
        sel = selector
        if by:
            from Play.pjeplay.locators import traduzir
            sel = traduzir(by, selector)
        if espera.ate_aparecer(driver, sel, teto=timeout):
            return espera.elemento(driver, sel)
        if isinstance(selector, str):
            logger.warning("[WAIT_VISIBLE] Elemento nao visivel: %s", selector)
        return None
    except Exception:
        if isinstance(selector, str):
            logger.warning("[WAIT_VISIBLE] Elemento nao visivel: %s", selector)
        return None

def wait_for_clickable(driver, selector, timeout=10, by=None):
    """Wait for an element to be clickable in the DOM."""
    try:
        sel = selector
        if by:
            from Play.pjeplay.locators import traduzir
            sel = traduzir(by, selector)
        if espera.ate_habilitar(driver, sel, teto=timeout):
            return espera.elemento(driver, sel)
        if isinstance(selector, str):
            logger.warning("[WAIT_CLICKABLE] Elemento nao clicavel: %s", selector)
        return None
    except Exception:
        if isinstance(selector, str):
            logger.warning("[WAIT_CLICKABLE] Elemento nao clicavel: %s", selector)
        return None

def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR, log=False):
    """Espera até que um elemento esteja presente (e opcionalmente contenha texto)."""
    if not driver:
        return None
    try:
        if not isinstance(seletor, str):
            raise ValueError(f"Seletor deve ser string, recebido: {type(seletor)}")
        if texto and not isinstance(texto, str):
            raise ValueError(f"Text must be a string, got: {type(texto)}")

        sel = seletor
        if by:
            from Play.pjeplay.locators import traduzir
            sel = traduzir(by, seletor)

        if texto:
            if espera.ate_texto(driver, sel, texto, teto=timeout):
                return espera.elemento(driver, sel)
            if log:
                logger.error(f"[ESPERAR][ERRO] Falha ao esperar texto '{texto}' em elemento: '{seletor}'")
            return None

        if espera.ate_aparecer(driver, sel, teto=timeout):
            return espera.elemento(driver, sel)

        if log:
            logger.error(f"[ESPERAR][ERRO] Falha ao esperar elemento: '{seletor}'")
        return None
    except Exception as e:
        if log:
            logger.error(f"[ESPERAR][ERRO] Falha ao esperar elemento: '{seletor}' -> {e}")
        return None

def esperar_url_conter(driver, substring, timeout=10):
    """
    Espera até que a URL atual contenha a substring especificada.
    Args:
        driver: driver ativo
        substring: String a ser encontrada na URL
        timeout: Tempo máximo de espera em segundos
    Returns:
        bool: True se encontrou, False se timeout
    """
    if not driver:
        return False
    try:
        return bool(espera.ate(driver, lambda d: substring in getattr(d, 'current_url', ''), teto=timeout))
    except Exception as e:
        logger.error('[URL] Erro ao esperar URL: %s', e)
        return False

def sleep(ms):
    """Compatibilidade: converte milissegundos para segundos"""
    espera.pausa(ms / 1000.0)
