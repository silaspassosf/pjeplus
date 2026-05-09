import logging
logger = logging.getLogger(__name__)

"""
SISB Integration - Integração com PJE
Funções para executar juntada automática e atualizar relatórios
"""

import os


def _atualizar_relatorio_com_segundo_protocolo(numero_processo, protocolo_primeira, protocolo_segunda, log=True):
    """
    Atualiza o relatório no clipboard.txt adicionando o protocolo da segunda minuta.
    
    Modifica a linha de protocolo de:
    "Protocolo: 12345678901234"
    Para:
    "Protocolos: 12345678901234 e 98765432109876"
    
    Args:
        numero_processo: Número do processo
        protocolo_primeira: Protocolo da primeira minuta
        protocolo_segunda: Protocolo da segunda minuta
        log: Se True, exibe logs
        
    Returns:
        bool: True se atualizou com sucesso
    """
    try:
        # Ler clipboard.txt
        from PEC.anexos import obter_caminho_clipboard
        clipboard_path = obter_caminho_clipboard(numero_processo or "SISBAJUD")
        
        if not os.path.exists(clipboard_path):
            return False
        
        with open(clipboard_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Substituir linha de protocolo
        import re
        # Padrão: "Protocolo: XXXXX" -> "Protocolos: XXXXX e YYYYY"
        padrao = r'Protocolo:\s*(\d+)'
        substituicao = f'Protocolos: {protocolo_primeira} e {protocolo_segunda}'
        
        conteudo_atualizado = re.sub(padrao, substituicao, conteudo)
        
        # Salvar de volta
        with open(clipboard_path, 'w', encoding='utf-8') as f:
            f.write(conteudo_atualizado)
        
        return True
        
    except Exception as e:
        if log:
            logger.error(f'[SISBAJUD][RELATORIO]  Erro ao atualizar relatório: {e}')
            import traceback
            logger.exception("Erro detectado")
        return False


def _executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log=True):
    """Delega para a funcao canonica em PEC.anexos."""
    from PEC.anexos import executar_juntada_pje
    return executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log)
