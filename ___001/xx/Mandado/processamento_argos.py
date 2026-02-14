from selenium.webdriver.remote.webdriver import WebDriver

from Fix import (
    buscar_documentos_sequenciais,
    extrair_dados_processo,
    extrair_destinatarios_decisao,
    salvar_destinatarios_cache,
)
from Fix.core import buscar_documento_argos
from Fix.log import logger
from PEC.core import extrair_numero_processo_pec as extrair_numero_processo

from atos import ato_meios
from .processamento_anexos import tratar_anexos_argos
from .regras import aplicar_regras_argos
from .utils import fechar_intimacao, retirar_sigilo_fluxo_argos


def processar_argos(driver: WebDriver, log: bool = False) -> bool:
    """
    Processa fluxo Argos com sequência rigorosa e validações entre etapas.

    SEQUÊNCIA OBRIGATÓRIA (não pode ser alterada):
    0. Documentos sequenciais (identificar certidão, ordem de pesquisa, cálculos, intimação, decisão)
    1. Tirar sigilo da certidão
    2. Tratar anexos especiais infojud (sigilo+visibilidade)
    3. SISBAJUD - extrair documento PDF + regras
    4. Retirar sigilo dos demais documentos sequenciais que forem ainda sigilosos

    Cada etapa deve ser executada completamente antes de passar para a próxima.
    """
    try:
        print('[ARGOS][INICIO] Iniciando processamento do fluxo Argos com sequência rigorosa')

        # === ETAPA 0: FECHAR INTIMAÇÃO ===
        print('[ARGOS][ETAPA 0] Fechando intimação...')
        if not fechar_intimacao(driver, log=log):
            print('[ARGOS][ETAPA 0][ERRO CRÍTICO] Falha ao fechar intimação - ABORTANDO FLUXO')
            return False
        print('[ARGOS][ETAPA 0] ✅ Intimação fechada com sucesso')

        # === ETAPA 1: IDENTIFICAR DOCUMENTOS SEQUENCIAIS ===
        print('[ARGOS][ETAPA 1] Identificando documentos sequenciais (certidão, ordem de pesquisa, cálculos, intimação, decisão)...')
        documentos_sequenciais = buscar_documentos_sequenciais(driver, log=log)
        if not documentos_sequenciais:
            print('[ARGOS][ETAPA 1][ERRO] Nenhum documento sequencial encontrado - abortando fluxo')
            return False
        print(f'[ARGOS][ETAPA 1] ✅ Encontrados {len(documentos_sequenciais)} documentos sequenciais')

        # === ETAPA 1.5: RETIRAR SIGILO DOS DOCUMENTOS SEQUENCIAIS ===
        resultado_sigilo = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log=log)
        if resultado_sigilo.get('total_processados', 0) > 0:
            pass
        anexos_info = tratar_anexos_argos(driver, documentos_sequenciais, log=log)
        if not anexos_info:
            print('[ARGOS][ETAPA 2][ERRO] Falha no processamento de anexos - abortando fluxo')
            return False

        # === ETAPA 3: SISBAJUD - EXTRAIR DOCUMENTO PDF + REGRAS ===
        resultado_sisbajud = anexos_info.get('resultado_sisbajud', None)
        sigilo_anexos = anexos_info.get('sigilo_anexos', {})
        executados = anexos_info.get('executados', [])

        if resultado_sisbajud:
            pass
        tem_anexos = anexos_info.get('tem_anexos', False)
        if not tem_anexos:
            ato_meios(driver, debug=log)
            return True

        # === ETAPA 4: BUSCAR E APLICAR REGRAS ARGOS (LOOP ITERATIVO SIMPLES) ===
        # Loop: abrir despacho/decisão → extrair → comparar regras → aplicar se tem regra → próximo se não
        
        regra_aplicada = False
        max_tentativas = 10  # Limite para evitar loop infinito
        tentativa = 0
        
        while tentativa < max_tentativas and not regra_aplicada:
            tentativa += 1
            
            # Buscar próximo documento com regra Argos
            resultado_documento = buscar_documento_argos(driver, log=True)
            
            if not resultado_documento or not resultado_documento[0]:
                break
            
            documento_texto, documento_tipo = resultado_documento[0], resultado_documento[1]
            
            if not documento_texto or not documento_tipo:
                continue
            

            # === ETAPA 5: EXTRAIR DESTINATÁRIOS ===
            try:
                dados_processo_cache = extrair_dados_processo(driver, debug=log)
            except Exception as dados_err:
                dados_processo_cache = {}

            try:
                numero_proc_atual = extrair_numero_processo(driver)
            except Exception:
                numero_proc_atual = ''

            try:
                destinatarios_extraidos = extrair_destinatarios_decisao(
                    documento_texto,
                    dados_processo=dados_processo_cache,
                    debug=log
                )
                if destinatarios_extraidos:
                    salvar_destinatarios_cache(
                        "ATUAL",
                        destinatarios_extraidos,
                        origem=f'argos_{documento_tipo}'
                    )
            except Exception as dest_err:
                pass
            regras_aplicadas = aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, documento_tipo, documento_texto, debug=True)
            
            if regras_aplicadas:
                regra_aplicada = True
                break
            else:
                continue
        
        if not regra_aplicada:
            print('[ARGOS][ETAPA 4-6][ERRO] Nenhum documento teve regra Argos aplicada com sucesso após {tentativa} tentativas')
            return False

        return True

    except Exception as e:
        print(f'[ARGOS][ERRO] Falha crítica no processamento: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        # ===== GARANTIR FECHAMENTO DA ABA /DETALHE MESMO EM CASO DE ERRO =====
        try:
            all_windows = driver.window_handles
            current_url = driver.current_url.lower() if driver.current_url else ''
            
            # Se estamos em uma aba /detalhe e há mais de uma aba aberta
            if '/detalhe' in current_url and len(all_windows) > 1:
                current_window = driver.current_window_handle
                main_window = all_windows[0]
                
                # Fecha a aba atual
                driver.close()
                
                # Troca para aba principal
                if main_window in driver.window_handles:
                    driver.switch_to.window(main_window)
                else:
                    # Se a aba principal não existe mais, vai para a última aba disponível
                    driver.switch_to.window(driver.window_handles[-1])
        except Exception as cleanup_err:
            print(f'[ARGOS][CLEANUP][ERRO] Falha ao fechar aba: {cleanup_err}')
            # Não propaga o erro de cleanup para não mascarar erro original