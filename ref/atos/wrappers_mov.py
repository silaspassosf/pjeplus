"""
Wrappers para movimentos - Instâncias da função mov() com diferentes seletores
"""

from .movimentos import mov
from selenium.webdriver.common.by import By


# ====================================================
# WRAPPER FUNCTIONS - MOV DERIVATIVES
# ====================================================

def mov_arquivar(driver, debug=False):
    """Movimento: Arquivar o processo"""
    return mov(driver, "button[aria-label='Arquivar o processo']", debug=debug)


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
    print('[MOV_EXEC] ⚠️ Botão "Iniciar execução" não encontrado - não está disponível neste processo')
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
    print('[MOV_PRAZO] ⚠️ Função mov_prazo desabilitada por enquanto')
    return True
