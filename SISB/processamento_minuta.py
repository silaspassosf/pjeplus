import logging
logger = logging.getLogger(__name__)

"""
SISB.processamento_minuta - Módulo de criação de minutas SISBAJUD.

Parte da refatoração do SISB/processamento.py para melhor granularidade IA.
"""

import time
from .utils import (
    criar_js_otimizado, log_sisbajud, carregar_dados_processo,
    extrair_protocolo
)

def minuta_bloqueio_refatorada(driver_sisbajud, dados_processo, driver_pje=None, driver_created=False, manter_driver_aberto=False):
    """DEPRECATED: Cria minuta de bloqueio no SISBAJUD - versão refatorada e otimizada."""
    try:
        log_sisbajud("=== INICIANDO MINUTA DE BLOQUEIO (REFATORADA) ===")

        from .helpers import _validar_dados
        dados_validos, numero_processo = _validar_dados(dados_processo)
        if not dados_validos:
            raise ValueError("Dados do processo inválidos ou não encontrados")

        if not dados_processo:
            dados_processo = carregar_dados_processo()
            if not dados_processo:
                raise ValueError("Não foi possível carregar dados do processo do arquivo")

        driver_sisbajud.execute_script(criar_js_otimizado())
        log_sisbajud("JavaScript otimizado injetado")

        from .processamento_campos import _preencher_campos_principais
        resultado_campos = _preencher_campos_principais(driver_sisbajud, dados_processo)
        if not resultado_campos['sucesso']:
            raise Exception(f"Falha no preenchimento de campos: {resultado_campos.get('erro', 'Erro desconhecido')}")

        from .processamento_campos import _processar_reus_otimizado
        resultado_reus = _processar_reus_otimizado(driver_sisbajud, dados_processo)
        if not resultado_reus['sucesso']:
            raise Exception(f"Falha no processamento de réus: {resultado_reus.get('erro', 'Erro desconhecido')}")

        from .processamento_campos import _configurar_valor
        _configurar_valor(driver_sisbajud, dados_processo)

        from .processamento_campos import _configurar_opcoes_adicionais
        _configurar_opcoes_adicionais(driver_sisbajud, dados_processo)

        from .processamento_relatorios import _salvar_minuta
        if not _salvar_minuta(driver_sisbajud):
            raise Exception("Falha ao salvar minuta")

        from .processamento_relatorios import _gerar_relatorio_minuta
        dados_relatorio = _gerar_relatorio_minuta(driver_sisbajud, numero_processo)

        juntada_executada = False
        if driver_pje:
            log_sisbajud("Executando juntada automática no PJE...")
            try:
                from SISB.helpers import _executar_juntada_pje
                tipo_fluxo = 'NEGATIVO'
                juntada_executada = _executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log=True)
                if juntada_executada:
                    log_sisbajud(" Juntada executada com sucesso no PJE")
                else:
                    log_sisbajud(" Juntada pode não ter sido executada corretamente")
            except Exception as e:
                log_sisbajud(f" Erro na execução da juntada: {e}")

        log_sisbajud(" MINUTA DE BLOQUEIO CRIADA COM SUCESSO")

        return {
            'status': 'sucesso',
            'dados_minuta': {
                'tipo': 'bloqueio',
                'repeticao': 'sim',
                'quantidade_reus': len(dados_processo.get('reu', [])),
                'salvo_em': 'clipboard.txt'
            },
            'juntada_executada': juntada_executada
        }

    except Exception as e:
        log_sisbajud(f" Falha na minuta de bloqueio: {e}", "ERROR")

        if not manter_driver_aberto:
            try:
                if driver_created and driver_sisbajud:
                    driver_sisbajud.quit()
            except Exception as e:
                _ = e
        else:
            log_sisbajud("DEBUG: Mantendo driver SISBAJUD aberto para inspeção do erro")

        return None