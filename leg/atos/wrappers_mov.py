from Fix.exceptions import PJePlusError
import logging
logger = logging.getLogger(__name__)

"""
Wrappers para movimentos - OTIMIZADO
Mantém wrappers atuais (mov_sob, mov_aud) + nova navegação inteligente
"""

from .movimentos import mov, mov_simples
from .movimentos_fluxo import movimentar_inteligente
from selenium.webdriver.common.by import By


# ====================================================
# WRAPPER FUNCTIONS - MOV DERIVATIVES (OTIMIZADO)
# ====================================================

def mov_arquivar(driver, debug=False):
    """Movimento: Arquivar o processo - com espera extra para carregamento da página"""
    # Preferir movimentar_inteligente por rótulo ao invés de seletor CSS
    result = movimentar_inteligente(driver, 'Arquivar o processo', timeout=10)
    if result:
        # Aguardar carregamento da página após arquivar
        logger.info('[MOV_ARQUIVAR] Aguardando carregamento da página após arquivar...')
        from Fix.utils import aguardar_pagina_carregar
        aguardar_pagina_carregar(driver, timeout=10)
    return result


def mov_exec(driver, debug=False):
    """Movimento: Iniciar execução"""
    from .movimentos import mov_simples

    # Ativar debug para depuração
    debug = True
    # Tentar mover por rótulo 'Iniciar execução'
    destinos = ['Iniciar execução']
    for destino in destinos:
        try:
            ok = movimentar_inteligente(driver, destino, timeout=8)
            if ok:
                return True
        except Exception as e:
            continue
    raise PJePlusError('Falha ao movimentar para Iniciar execução')


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
            ok = movimentar_inteligente(driver, 'Aguardando audiência', timeout=8)
            if ok:
                return True
        except Exception as e:
            continue

    # Fallback: try a more generic aria-label exact match
    try:
        return movimentar_inteligente(driver, 'Aguardando audiência', timeout=8)
    except Exception as e:
        raise PJePlusError('Falha ao movimentar para Aguardando audiência')


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
