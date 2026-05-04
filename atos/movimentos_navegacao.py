import logging
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
    """Normaliza nome da tarefa para comparação (similar ao removeAcento da a.py)"""
    if not tarefa:
        return ""

    # Remove acentos e deixa minúsculo
    tarefa_norm = tarefa.lower()

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
    """Executa o movimento específico baseado na tarefa atual"""

    # Se já está em análise, tentar clicar diretamente no destino
    if 'analise' in tarefa_atual:
        return _movimento_de_analise(driver, tarefa_destino, debug, timeout)

    # Movimentos específicos por tarefa
    movimentos = {
        'comunicacoes e expedientes': lambda: _movimento_comunicacoes(driver, debug),
        'arquivo provisorio': lambda: _movimento_arquivo_provisorio(driver, debug),
        'aguardando final do sobrestamento': lambda: _movimento_sobrestamento_final(driver, debug),
    }

    movimento_func = movimentos.get(tarefa_atual)
    if movimento_func:
        sucesso = movimento_func()
        if sucesso:
            # Após movimento específico, tentar ir para análise se necessário
            return _movimento_para_analise_se_necessario(driver, tarefa_destino, debug, timeout)
    else:
        # Movimento padrão: ir para análise
        return _movimento_padrao_para_analise(driver, tarefa_destino, debug, timeout)

    return False


def _movimento_de_analise(driver: WebDriver, tarefa_destino: str, debug: bool, timeout: int) -> bool:
    """Movimento quando já está em análise - clica diretamente no botão do destino"""
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


def _movimento_comunicacoes(driver: WebDriver, debug: bool) -> bool:
    """Movimento específico para comunicações e expedientes"""
    try:
        if debug:
            logger.info('[COMUNICACOES] Movendo de comunicações')

        btn_cancelar = esperar_elemento(driver, "button[aria-label*='cancelar expedientes']", timeout=10)
        if btn_cancelar:
            safe_click(driver, btn_cancelar)
            _esperar_transicao(driver, debug, esperar=False)
            return True
        return False
    except Exception as e:
        if debug:
            logger.error(f'[COMUNICACOES] Erro: {e}')
        return False


def _movimento_arquivo_provisorio(driver: WebDriver, debug: bool) -> bool:
    """Movimento específico para arquivo provisório"""
    try:
        if debug:
            logger.info('[ARQUIVO_PROVISORIO] Movendo de arquivo provisório')

        # Clicar em "Arquivo" e fechar janela
        btn_arquivo = esperar_elemento(driver, "input[value='Arquivo']", timeout=10)
        if btn_arquivo:
            safe_click(driver, btn_arquivo)
            _esperar_transicao(driver, debug)
            # Interromper qualquer ação vinculada e fechar
            return True
        return False
    except Exception as e:
        if debug:
            logger.error(f'[ARQUIVO_PROVISORIO] Erro: {e}')
        return False


def _movimento_sobrestamento_final(driver: WebDriver, debug: bool) -> bool:
    """Movimento específico para aguardando final do sobrestamento"""
    try:
        if debug:
            logger.info('[SOBRESTAMENTO_FINAL] Movendo de aguardando final do sobrestamento')

        # Clicar em "encerrar" e confirmar
        btn_encerrar = esperar_elemento(driver, "button[aria-label*='encerrar']", timeout=10)
        if btn_encerrar:
            safe_click(driver, btn_encerrar)

            btn_sim = esperar_elemento(driver, "button[aria-label='Sim']", timeout=5)
            if btn_sim:
                safe_click(driver, btn_sim)
                _esperar_transicao(driver, debug)
                return True
        return False
    except Exception as e:
        if debug:
            logger.error(f'[SOBRESTAMENTO_FINAL] Erro: {e}')
        return False


def _movimento_padrao_para_analise(driver: WebDriver, tarefa_destino: str, debug: bool, timeout: int) -> bool:
    """Movimento padrão: ir para análise primeiro"""
    try:
        if debug:
            logger.info('[PADRAO] Movimento padrão: indo para análise primeiro')

        # Clicar em "análise"
        btn_analise = esperar_elemento(driver, "button[aria-label='Análise']", timeout=10)
        if btn_analise and not btn_analise.get_attribute('disabled'):
            safe_click(driver, btn_analise)
            _esperar_transicao(driver, debug)

            # Agora tentar ir para o destino final
            return _movimento_de_analise(driver, tarefa_destino, debug, timeout)
        return False
    except Exception as e:
        if debug:
            logger.error(f'[PADRAO] Erro no movimento padrão: {e}')
        return False


def _movimento_para_analise_se_necessario(driver: WebDriver, tarefa_destino: str, debug: bool, timeout: int) -> bool:
    """Após movimento específico, vai para análise se necessário"""
    tarefa_atual = _obter_tarefa_atual(driver, debug)
    if tarefa_atual and 'analise' not in _normalizar_tarefa(tarefa_atual):
        return _movimento_padrao_para_analise(driver, tarefa_destino, debug, timeout)
    return True


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