import logging
logger = logging.getLogger(__name__)

"""
Wrappers para movimentos - OTIMIZADO
Mantém wrappers atuais (mov_sob, mov_aud) + nova navegação inteligente
"""

from .movimentos import mov, mov_simples
from selenium.webdriver.common.by import By


# ====================================================
# WRAPPER FUNCTIONS - MOV DERIVATIVES (OTIMIZADO)
# ====================================================

def mov_arquivar(driver, debug=False):
    """Movimento: Arquivar o processo - com espera extra para carregamento da página"""
    result = mov(driver, "button[aria-label='Arquivar o processo']", debug=debug)
    if result:
        # Aguardar carregamento da página após arquivar
        logger.info('[MOV_ARQUIVAR] Aguardando carregamento da página após arquivar...')
        import time
        time.sleep(3)  # Espera extra para garantir carregamento completo
    return result


def mov_exec(driver, debug=False):
    """Movimento: Iniciar execução"""
    from .movimentos import mov_simples

    # Ativar debug para depuração
    debug = True
    selectors = [
        "button[aria-label='Iniciar execução']",
        "button[aria-label='Iniciar a execução']",
        "button[aria-label*='Iniciar execução']",
        "//button[contains(text(),'Iniciar execução')]",
        "//button[contains(.//span, 'Iniciar execução')]",
    ]

    # Tentar apenas uma vez - se não encontrar "Iniciar execução", é porque não está disponível
    for sel in selectors:
        try:
            ok = mov_simples(driver, sel, debug=debug)
            if ok:
                return True
        except Exception:
            continue

    # Se chegou aqui, "Iniciar execução" não está disponível - retornar False para executar ato_pesqliq
    return False


def mov_aud(driver, debug=False):
    """Movimento: Aguardando audiência

    Tenta seletores robustos para localizar o botão de movimento que contenha
    a indicação de 'Aguardando audiência'. Usa alguns seletores com e sem
    acentuação como fallback e chama a função genérica `mov`.
    """
    selectors = [
        "button[aria-label*='Aguardando audiência']",
        "button[aria-label*='Aguardando audiencia']",
        "button[aria-label*='Aguardando']",
    ]

    for sel in selectors:
        try:
            ok = mov(driver, sel, debug=debug)
            if ok:
                return True
        except Exception:
            continue

    # Fallback: try a more generic aria-label exact match (may fail harmlessly)
    try:
        return mov(driver, "button[aria-label='Aguardando audiência']", debug=debug)
    except Exception:
        return False


def mov_prazo(driver, debug=False):
    """
    Movimento: Aguardando prazo - DESABILITADO POR ENQUANTO

    OTIMIZADO: Apenas VERIFICA se a tarefa já é "Aguardando prazo".
    Se sim, retorna sucesso sem abrir a tarefa (já está no estado correto).
    Se não, executa o movimento normal.
    """
    # DESABILITADO: Não será usado por enquanto
    return True


# ====================================================
# EXEMPLOS DE USO DA NOVA NAVEGAÇÃO INTELIGENTE
# ====================================================

def mov_para_analise(driver, debug=False):
    """
    Exemplo: Move o processo para "Análise" independente de onde estiver
    Baseado na lógica da aaMovimentos da a.py
    """
    return navegar_para_tarefa(driver, "análise", debug=debug)


def mov_para_comunicacoes(driver, debug=False):
    """
    Exemplo: Move o processo para "Comunicações e Expedientes"
    """
    return navegar_para_tarefa(driver, "comunicações e expedientes", debug=debug)
