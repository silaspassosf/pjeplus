from typing import Optional, Tuple, Dict, List, Union, Callable, Any
from Fix import espera
from Fix.utils import login_pc
from Fix.core import (
    safe_click,
    safe_click_no_scroll,
    esperar_elemento,
    esperar_url_conter,
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    aguardar_renderizacao_nativa,
    aplicar_filtro_100,
    buscar_documentos_sequenciais,
)
from Fix.extracao import criar_gigs
from Fix.utils import limpar_temp_selenium
from Fix.extracao import indexar_e_processar_lista, extrair_dados_processo, carregar_destinatarios_cache
from Fix.errors import ElementoNaoEncontradoError, NavegacaoError
import os
import logging
import time
from Fix.selectors_pje import BTN_TAREFA_PROCESSO

logger = logging.getLogger(__name__)


def _is_doc_ready_complete(driver: Any) -> bool:
    try:
        if hasattr(driver, 'page'):
            return bool(driver.page.evaluate("() => document.readyState === 'complete'"))
        return True
    except Exception:
        return True


def selecionar_opcao_select(
    driver: Any,
    seletor: str,
    texto_opcao: str,
    timeout: int = 10
) -> bool:
    """
    Seleciona uma opção em um mat-select de forma robusta.
    """
    try:
        if not espera.ate_habilitar(driver, seletor, teto=timeout):
            raise Exception(f'{seletor} não habilitou')
        safe_click_no_scroll(driver, seletor)
        espera.ate_aparecer(driver, 'mat-option', teto=timeout)
        opcoes = espera.elementos(driver, 'mat-option', teto=timeout)
        for opcao in opcoes:
            txt = getattr(opcao, 'text', '') or ''
            if texto_opcao.lower() in txt.lower():
                safe_click(driver, opcao)
                return True
        raise Exception(f'Opção "{texto_opcao}" não encontrada em {seletor}!')
    except Exception as e:
        logger.error(f'Erro em selecionar_opcao_select: {e}')
        raise ElementoNaoEncontradoError(texto_opcao, f'selecionar_opcao_select: {e}')


def verificar_carregamento_pagina(
    driver: Any,
    timeout_spinner: float = 1.0,
    max_tentativas: int = 5,
    log: bool = False
) -> bool:
    """
    Verifica se a página está em estado de carregamento (spinner visível).
    Continua tentando até o spinner desaparecer - NÃO desiste facilmente.
    """
    for tentativa in range(1, max_tentativas + 1):
        espera.assentar(driver, timeout_spinner, motivo='aguardar spinner')
        
        try:
            _sel = 'mat-progress-spinner, mat-spinner, .mat-progress-spinner, .loading-spinner, .loading-overlay, .modal-backdrop, .cdk-overlay-backdrop'
            try:
                _ok = aguardar_renderizacao_nativa(driver, _sel, modo='sumir', timeout=timeout_spinner)
            except Exception:
                _ok = False

            if _ok:
                if _is_doc_ready_complete(driver):
                    return True

            status = 'complete'
            if hasattr(driver, 'page'):
                try:
                    status = driver.page.evaluate("""() => {
                        if (document.readyState !== 'complete') return 'loading';
                        const spinner = document.querySelector('mat-progress-spinner, mat-spinner, .mat-progress-spinner');
                        if (spinner && window.getComputedStyle(spinner).display !== 'none') return 'spinner';
                        return 'complete';
                    }""")
                except Exception:
                    status = 'complete'
            
            if status == 'complete':
                return True
            
            if status == 'loading':
                espera.assentar(driver, 0.3, motivo='aguardar readyState complete')
                if _is_doc_ready_complete(driver):
                    return True
            
            if log:
                logger.warning(f"[CARREGAMENTO] Status={status}, F5...")
            
            driver.refresh()
            try:
                espera.ate_js(driver, "document.readyState === 'complete'", teto=10)
            except Exception:
                pass
            
            try:
                aguardar_renderizacao_nativa(driver, 'mat-progress-spinner, mat-spinner, .loading-spinner, .loading-overlay', 'sumir', 5)
            except Exception:
                espera.assentar(driver, 0.5, motivo='espera de segurança pós reload')
            
        except Exception as e:
            if log:
                logger.warning(f"[CARREGAMENTO] Erro: {e}")
            return True
    
    if log:
        logger.error(f"[CARREGAMENTO] Falha após {max_tentativas} tentativas")
    raise NavegacaoError(f"verificar_carregamento_pagina: falha após {max_tentativas} tentativas")


def aguardar_e_verificar_aba(
    driver: Any,
    url_esperada: str = None,
    timeout_aba: int = 10,
    timeout_spinner: float = 2.0,
    max_tentativas_reload: int = 3,
    log: bool = False
) -> bool:
    """
    Aguarda uma nova aba carregar e verifica se não está travada no spinner.
    """
    try:
        if url_esperada:
            if not espera.ate_url(driver, url_esperada, teto=timeout_aba):
                if log:
                    logger.warning(f"[ABA] Timeout aguardando URL com '{url_esperada}'. URL atual: {driver.current_url}")
        
        return verificar_carregamento_pagina(
            driver,
            timeout_spinner=timeout_spinner,
            max_tentativas=max_tentativas_reload,
            log=log
        )
        
    except Exception as e:
        logger.error(f"[ABA] Erro ao verificar aba: {e}")
        raise NavegacaoError(f'aguardar_e_verificar_aba: {e}')


def verificar_carregamento_detalhe(
    driver: Any,
    timeout_inicial: float = 2.0,
    max_tentativas: int = 3,
    log: bool = False
) -> bool:
    """
    Verifica se a página /detalhe carregou corretamente.
    A página /detalhe não tem spinner, então verificamos a presença do botão de filtro.
    """
    FILTRO_SELECTORS = [
        'button[aria-label="Filtrar"] i.fa-filter',
        'button.botao-menu i.fa-filter',
        'button[name="Mostrar ou Esconder Filtros"]',
        'button[accesskey="o"] i.fa-filter',
        '.botao-menu i.fa-filter.botao-menu-texto',
        'button.mat-mini-fab[aria-label="Filtrar"]'
    ]
    
    for tentativa in range(1, max_tentativas + 1):
        try:
            SELECTOR_JOINED = ', '.join(FILTRO_SELECTORS)
            try:
                _found = aguardar_renderizacao_nativa(driver, SELECTOR_JOINED, modo='aparecer', timeout=timeout_inicial)
            except Exception:
                _found = False
            if _found:
                if _is_doc_ready_complete(driver):
                    return True
        except Exception:
            pass

        try:
            current_url = driver.current_url or ''
            if '/detalhe' not in current_url.lower():
                if log:
                    logger.warning(f"[DETALHE] URL não contém /detalhe: {current_url}")
                return True
        except Exception:
            pass
        
        filtro_encontrado = False
        for selector in FILTRO_SELECTORS:
            try:
                elementos = espera.elementos(driver, selector, teto=1)
                for elemento in elementos:
                    if getattr(elemento, 'is_displayed', lambda: True)():
                        filtro_encontrado = True
                        break
                if filtro_encontrado:
                    break
            except Exception:
                continue
        
        if filtro_encontrado:
            try:
                if _is_doc_ready_complete(driver):
                    return True
                else:
                    try:
                        aguardar_renderizacao_nativa(driver, SELECTOR_JOINED, 'aparecer', 2)
                    except Exception:
                        pass
                    if _is_doc_ready_complete(driver):
                        return True
            except Exception:
                pass
            
            return True
        
        if log:
            logger.warning(f"[DETALHE] Botão de filtro não encontrado na tentativa {tentativa}. Recarregando página (F5)...")
        
        try:
            driver.refresh()
            try:
                aguardar_renderizacao_nativa(driver, SELECTOR_JOINED, 'aparecer', 5)
            except Exception:
                pass
            espera.ate_js(driver, "document.readyState === 'complete'", teto=15)
        except Exception as e:
            if log:
                logger.error(f"[DETALHE] Erro ao recarregar página: {e}")
    
    logger.error(f"[DETALHE] Falha após {max_tentativas} tentativas. Página /detalhe não carregou.")
    raise NavegacaoError(f"verificar_carregamento_detalhe: falha após {max_tentativas} tentativas")



