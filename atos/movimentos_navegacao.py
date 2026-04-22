import logging
import re
import unicodedata
logger = logging.getLogger(__name__)

"""
Navegação inteligente entre tarefas do PJe - baseada na lógica da aaMovimentos da a.py
Move o processo para uma tarefa específica independente de onde ele estiver.
"""

from .core import *
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver


def navegar_para_tarefa(
    driver: WebDriver,
    tarefa_destino: str,
    debug: bool = False,
    timeout: int = 30,
    tarefa_atual_conhecida: Optional[str] = None
) -> bool:
    """
    Navegação inteligente entre tarefas do PJe - baseada na lógica da aaMovimentos da a.py

    Move o processo para uma tarefa específica independente de onde ele estiver,
    seguindo as regras de transição do PJe.

    Args:
        driver: WebDriver instance
        tarefa_destino: Nome da tarefa de destino (ex: "análise", "comunicações e expedientes")
        debug: Habilita logs detalhados
        timeout: Timeout geral para operações
        tarefa_atual_conhecida: Nome da tarefa atual já conhecida (ex: lida do botão)

    Returns:
        bool: Sucesso da navegação
    """
    logger.info(f'[NAVEGAR_TAREFA] Iniciando navegação para: {tarefa_destino}')

    try:
        # 1. Identificar tarefa atual
        tarefa_atual = tarefa_atual_conhecida or _obter_tarefa_atual(driver, debug)
        if not tarefa_atual:
            logger.error('[NAVEGAR_TAREFA] Não foi possível identificar tarefa atual')
            return False

        tarefa_atual_norm = _normalizar_tarefa(tarefa_atual)
        tarefa_destino_norm = _normalizar_tarefa(tarefa_destino)

        logger.info(f'[NAVEGAR_TAREFA] Tarefa atual: "{tarefa_atual}" -> Destino: "{tarefa_destino}"')

        # 2. Verificar se já está no destino
        if tarefa_atual_norm == tarefa_destino_norm:
            logger.info('[NAVEGAR_TAREFA] Processo já está na tarefa destino')
            return True

        # 3. Verificar condições especiais que impedem movimento
        if _deve_interromper_movimento(tarefa_atual_norm, tarefa_destino_norm, debug):
            logger.warning('[NAVEGAR_TAREFA] Movimento interrompido por condição especial')
            return False

        # 4. Executar movimento baseado na tarefa atual
        return _executar_movimento_para_destino(driver, tarefa_atual_norm, tarefa_destino_norm, debug, timeout)

    except Exception as e:
        logger.error(f'[NAVEGAR_TAREFA] Erro na navegação: {e}')
        return False


def _obter_tarefa_atual(driver: WebDriver, debug: bool) -> Optional[str]:
    """Obtém o nome da tarefa atual do processo"""
    try:
        # Fallback: via URL
        url = driver.current_url
        if 'nomeTarefa=Arquivo+provis' in url:
            return 'Arquivo provisório'
        elif 'nomeTarefa=Arquivo+definitivo' in url:
            return 'Arquivo definitivo'

        # Fallback: buscar no DOM
        return _extrair_tarefa_do_dom(driver)

    except Exception as e:
        if debug:
            logger.warning(f'[OBTER_TAREFA] Erro ao obter tarefa atual: {e}')
        return None


def _obter_nome_tarefa_via_api(driver: WebDriver) -> Optional[str]:
    """REMOVIDO: Usar tarefa conhecida do botão ao invés de API"""
    return None


def _extrair_tarefa_do_dom(driver: WebDriver) -> Optional[str]:
    """Extrai nome da tarefa do DOM da página"""
    try:
        # Buscar no cabeçalho da tarefa
        elementos_tarefa = driver.find_elements_by_css_selector('pje-cabecalho-tarefa h1.titulo-tarefa')
        if elementos_tarefa:
            return elementos_tarefa[0].text.strip()

        # Fallback: outras possibilidades
        return 'Análise'  # Default fallback
    except Exception:
        return None


def _normalizar_tarefa(tarefa: str) -> str:
    """Normaliza nome da tarefa para comparação (similar ao removeAcento do gigs-plugin.js)"""
    if not tarefa:
        return ""

    # Remove prefixo DOM "Tarefa:\n" ou "Tarefa: " antes de qualquer coisa
    tarefa = re.sub(r'^tarefa:\s*', '', tarefa.strip(), flags=re.IGNORECASE)

    # Remove acentos via NFD
    tarefa_norm = unicodedata.normalize('NFD', tarefa)
    tarefa_norm = ''.join(c for c in tarefa_norm if unicodedata.category(c) != 'Mn')
    tarefa_norm = tarefa_norm.lower()

    # Correções específicas (baseado na a.py)
    tarefa_norm = tarefa_norm.replace('preparar expedientes e comunicacoes', 'comunicacoes e expedientes')
    tarefa_norm = tarefa_norm.replace('aguardando cumprimento de acordo', 'controle de acordo')

    return tarefa_norm


def _deve_interromper_movimento(tarefa_atual: str, tarefa_destino: str, debug: bool) -> bool:
    """Verifica se o movimento deve ser interrompido por condições especiais"""
    # Interromper se estiver em elaborar ou assinar (exceto se for cancelar conclusão)
    if 'elaborar' in tarefa_atual or 'assinar' in tarefa_atual:
        if debug:
            logger.info('[INTERROMPER] Processo em tarefa de elaborar/assinar')
        return True

    # Interromper se estiver em controle de acordo (exceto com último lance)
    if 'controle de acordo' in tarefa_atual:
        if debug:
            logger.info('[INTERROMPER] Processo em controle de acordo')
        return True

    return False


def _executar_movimento_para_destino(
    driver: WebDriver,
    tarefa_atual: str,
    tarefa_destino: str,
    debug: bool,
    timeout: int
) -> bool:
    """Executa o movimento — espelha movimentar_destino do gigs-plugin.js.
    Se já está em análise, clica direto no destino.
    Caso contrário, usa _movimentar_para_analise (autônoma) e depois tenta destino.
    """
    if 'analise de recurso interno' in tarefa_atual:
        # recurso interno → análise de gabinete (intermediário) → destino
        sucesso = _movimentar_para_analise(driver, tarefa_atual, debug)
        if sucesso:
            return _executar_movimento_para_destino(driver, _obter_tarefa_atual(driver, debug) or tarefa_atual, tarefa_destino, debug, timeout)
        return False

    if 'analise' in tarefa_atual:
        return _movimento_de_analise(driver, tarefa_destino, debug, timeout)

    # Para qualquer outra tarefa: mover para análise primeiro, depois ao destino
    sucesso = _movimentar_para_analise(driver, tarefa_atual, debug)
    if sucesso:
        tarefa_apos = _obter_tarefa_atual(driver, debug) or ''
        tarefa_apos_norm = _normalizar_tarefa(tarefa_apos)
        if 'analise' in tarefa_apos_norm:
            return _movimento_de_analise(driver, tarefa_destino, debug, timeout)
    return False


def _movimento_de_analise(driver: WebDriver, tarefa_destino: str, debug: bool, timeout: int) -> bool:
    """Já está em análise — clica diretamente no botão do destino.
    Espelha o bloco 'tarefa.includes(analise)' de movimentar_destino no gigs-plugin.
    """
    try:
        if debug:
            logger.info('[ANALISE] Já está em análise, clicando diretamente no destino')

        from .movimentos_fluxo import _localizar_botao_destino_movimento

        btn_destino = _localizar_botao_destino_movimento(driver, tarefa_destino, timeout=timeout)
        if not btn_destino:
            if debug:
                logger.warning(f'[ANALISE] Botão destino "{tarefa_destino}" não encontrado')
            return False

        if btn_destino.get_attribute('disabled'):
            if debug:
                logger.warning('[ANALISE] Botão destino está desabilitado')
            return False

        safe_click(driver, btn_destino)
        _esperar_transicao(driver, debug)
        return True

    except Exception as e:
        if debug:
            logger.warning(f'[ANALISE] Erro no movimento de análise: {e}')
        return False


def _movimentar_para_analise(driver: WebDriver, tarefa: str, debug: bool) -> bool:
    """Move o processo de qualquer tarefa para análise.

    Espelha exatamente movimentar_analise() do gigs-plugin.js — função única
    com if/elif por tarefa, sem funções individuais por nó.
    """
    import time as _time
    try:
        logger.info(f'[MOV_ANALISE] Movendo "{tarefa}" → análise')

        if 'conclusao ao magistrado' in tarefa:
            btn = esperar_elemento(driver, "button[aria-label*='cancelar']", timeout=10)
            if btn:
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        elif 'comunicacoes e expedientes' in tarefa or 'preparar expedientes e comunicacoes' in tarefa:
            btn = esperar_elemento(driver, "button[aria-label*='cancelar expedientes']", timeout=10)
            if btn:
                safe_click(driver, btn)
                _esperar_transicao(driver, debug, esperar=False)
                return True

        elif 'arquivo provisorio' in tarefa:
            btn = esperar_elemento(driver, "input[value='Arquivo']", timeout=10)
            if btn:
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        elif 'arquivo' in tarefa:
            btn = esperar_elemento(driver, "button[aria-label*='desarquivar']", timeout=10)
            if btn:
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        elif 'aguardando final do sobrestamento' in tarefa:
            btn_enc = esperar_elemento(driver, "button[aria-label*='encerrar']", timeout=10)
            if btn_enc:
                safe_click(driver, btn_enc)
                btn_sim = esperar_elemento(driver, "button[aria-label='Sim']", timeout=5)
                if btn_sim:
                    safe_click(driver, btn_sim)
                    _esperar_transicao(driver, debug)
                    return True

        elif 'iniciar execucao' in tarefa or 'iniciar liquidacao' in tarefa:
            btn = esperar_elemento(driver, "pje-transicao-tarefa button[aria-label*='iniciar']", timeout=10)
            if btn:
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        elif 'remeter' in tarefa:
            btn = esperar_elemento(driver, "button[aria-label='Cancelar Remessa']", timeout=10)
            if btn:
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        elif 'prazos vencidos - secretaria' in tarefa:
            btn = esperar_elemento(driver, "button[aria-label*='analise de secretaria']", timeout=10)
            if btn:
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        elif 'prazos vencidos - gabinete' in tarefa:
            btn = esperar_elemento(driver, "button[aria-label*='analise de gabinete']", timeout=10)
            if btn:
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        elif 'analise de recurso interno' in tarefa:
            btn = esperar_elemento(driver, "button[aria-label*='analise de gabinete']", timeout=10)
            if btn:
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        elif 'transito em julgado' in tarefa:
            btn = esperar_elemento(driver, "button[aria-label='Análise']", timeout=10)
            if btn and not btn.get_attribute('disabled'):
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        else:
            # Caso geral: clicar em Análise
            btn = esperar_elemento(driver, "button[aria-label='Análise']", timeout=10)
            if btn and not btn.get_attribute('disabled'):
                safe_click(driver, btn)
                _esperar_transicao(driver, debug)
                return True

        if debug:
            logger.warning(f'[MOV_ANALISE] Botão não encontrado para tarefa "{tarefa}"')
        return False

    except Exception as e:
        if debug:
            logger.error(f'[MOV_ANALISE] Erro: {e}')
        return False



def _esperar_transicao(driver: WebDriver, debug: bool, esperar: bool = True, tempo: int = 5000) -> bool:
    """Espera transição de tarefa (similar ao esperarTransicao da a.py)"""
    if not esperar:
        return True

    try:
        import time
        start_time = time.time()

        while time.time() - start_time < tempo / 1000:  # tempo em segundos
            if '/transicao' in driver.current_url:
                if debug:
                    logger.info('[TRANSICAO] Transição detectada')
                time.sleep(1)  # Aguardar estabilização
                return True
            time.sleep(0.1)

        if debug:
            logger.warning('[TRANSICAO] Timeout aguardando transição')
        return False
    except Exception as e:
        if debug:
            logger.error(f'[TRANSICAO] Erro aguardando transição: {e}')
        return False


# ============================================================================
# WRAPPER ESPECÍFICO PARA CLS
# ============================================================================

def mov_cls(driver: WebDriver, debug: bool = False, tarefa_atual_conhecida: Optional[str] = None) -> bool:
    """
    Movimento específico para CLS: Navega para "Conclusão ao Magistrado"
    
    Usa navegação inteligente baseada na aaMovimentos para levar o processo
    diretamente para "Conclusão ao Magistrado", independente da tarefa atual.
    
    Este wrapper é usado pelo fluxo_cls para navegação inteligente antes
    da escolha do tipo de conclusão.
    
    Args:
        driver: WebDriver instance
        debug: Habilita logs detalhados
        tarefa_atual_conhecida: Nome da tarefa atual lida do botão (opcional)
        
    Returns:
        bool: True se conseguiu navegar para conclusão, False caso contrário
    """
    logger.info('[MOV_CLS] Iniciando navegação para "Conclusão ao Magistrado"...')
    
    # Usar navegação inteligente para ir diretamente para "conclusão ao magistrado"
    sucesso = navegar_para_tarefa(driver, "conclusão ao magistrado", debug=debug, tarefa_atual_conhecida=tarefa_atual_conhecida)
    
    if sucesso:
        logger.info('[MOV_CLS] Navegação para conclusão bem-sucedida')
    else:
        logger.warning('[MOV_CLS] Falha na navegação inteligente para conclusão')
    
    return sucesso