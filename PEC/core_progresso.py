import logging
logger = logging.getLogger(__name__)

import re
from typing import Optional, Dict, Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Fix.monitoramento_progresso_unificado import (
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    processo_ja_executado_unificado,
    marcar_processo_executado_unificado,
    extrair_numero_processo_unificado,
    verificar_acesso_negado_unificado,
)


def carregar_progresso_pec() -> Dict[str, Any]:
    """Carrega o estado de progresso usando sistema unificado."""
    return carregar_progresso_unificado('pec')


def salvar_progresso_pec(progresso: Dict[str, Any]) -> bool:
    """Salva o estado de progresso usando sistema unificado."""
    salvar_progresso_unificado('pec', progresso)
    return True


def extrair_numero_processo_pec(driver: WebDriver) -> Optional[str]:
    """
    Extrai o número do processo da URL ou elemento da página (adaptado para PEC).
    Funciona tanto na visualização de processo individual quanto na lista.
    """
    try:
        url = driver.current_url
        if "processo/" in url:
            match = re.search(r"processo/(\d+)", url)
            if match:
                numero_limpo = match.group(1)
                # Formatar como CNJ se tiver 20 dígitos (específico para PJE)
                if len(numero_limpo) == 20:
                    n = numero_limpo
                    numero_formatado = f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13:14]}.{n[14:16]}.{n[16:]}"
                    logger.info(f"[PROGRESSO_PEC]  Número extraído da URL e formatado: {numero_formatado}")
                    return numero_formatado
                
                logger.info(f"[PROGRESSO_PEC]  Número extraído da URL: {numero_limpo}")
                return numero_limpo

        try:
            candidatos = driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho, .numero-processo')
            for elemento in candidatos:
                texto = elemento.text.strip()
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                if match:
                    numero_limpo = re.sub(r'[^\d]', '', match.group(1))
                    logger.info(f"[PROGRESSO_PEC]  Número extraído do elemento: {numero_limpo}")
                    return numero_limpo
        except Exception as inner_e:
            logger.info(f"[PROGRESSO_PEC]  Erro ao buscar por seletores: {inner_e}")

        try:
            numero_js = driver.execute_script("""
                var textoCompleto = document.body.innerText || document.body.textContent || '';
                var matches = textoCompleto.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/g);
                if (matches && matches.length > 0) {
                    return matches[0].replace(/[^\d]/g, '');
                }

                var titulo = document.title;
                var matchTitulo = titulo.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
                if (matchTitulo) {
                    return matchTitulo[0].replace(/[^\d]/g, '');
                }

                return null;
            """)

            if numero_js:
                logger.info(f"[PROGRESSO_PEC]  Número extraído via JavaScript: {numero_js}")
                return numero_js

        except Exception as js_e:
            logger.info(f"[PROGRESSO_PEC]  Erro no JavaScript de extração: {js_e}")

        logger.info("[PROGRESSO_PEC]  Nenhum número de processo encontrado")
        return None

    except Exception as e:
        logger.info(f"[PROGRESSO_PEC][ERRO] Falha ao extrair número do processo: {e}")
        return None


def verificar_acesso_negado_pec(driver: Any) -> bool:
    """Verifica se estamos na página de acesso negado no sistema PEC."""
    try:
        url_atual = driver.current_url
        return "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower()
    except Exception as e:
        msg = str(e)
        logger.error(f"[PROGRESSO_PEC][ERRO] Falha ao verificar acesso negado: {msg}")
        if "browsing context has been discarded" in msg.lower() or "session deleted because of page crash" in msg.lower():
            return True
        return False


def processo_ja_executado_pec(numero_processo: str, progresso: Optional[Dict[str, Any]] = None) -> bool:
    """Verifica se o processo já foi executado no fluxo PEC usando sistema unificado."""
    if not numero_processo:
        return False

    if progresso is None:
        progresso = carregar_progresso_pec()

    return processo_ja_executado_unificado(numero_processo, progresso)


def marcar_processo_executado_pec(
    numero_processo: str,
    progresso: Optional[Dict[str, Any]] = None,
    status: str = "SUCESSO",
    detalhes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Marca processo como executado no fluxo PEC usando sistema unificado."""
    if not numero_processo:
        return progresso

    if progresso is None:
        progresso = carregar_progresso_pec()

    sucesso = True if (status or "").upper() == "SUCESSO" else False
    marcar_processo_executado_unificado('pec', numero_processo, progresso, sucesso=sucesso)

    return progresso
