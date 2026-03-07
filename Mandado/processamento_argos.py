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
        logger.info('[ARGOS][INICIO] Iniciando processamento do fluxo Argos com sequência rigorosa')

        # === ETAPA 0: FECHAR INTIMAÇÃO ===
        logger.info('[ARGOS][ETAPA 0] Fechando intimação...')
        if not fechar_intimacao(driver, log=log):
            logger.info('[ARGOS][ETAPA 0][ERRO CRÍTICO] Falha ao fechar intimação - ABORTANDO FLUXO')
            return False
        logger.info('[ARGOS][ETAPA 0]  Intimação fechada com sucesso')

        # === ETAPA 1: IDENTIFICAR DOCUMENTOS SEQUENCIAIS ===
        logger.info('[ARGOS][ETAPA 1] Identificando documentos sequenciais (certidão, ordem de pesquisa, cálculos, intimação, decisão)...')
        documentos_sequenciais = buscar_documentos_sequenciais(driver, log=log)
        if not documentos_sequenciais:
            logger.info('[ARGOS][ETAPA 1][ERRO] Nenhum documento sequencial encontrado - abortando fluxo')
            return False
        logger.info(f'[ARGOS][ETAPA 1]  Encontrados {len(documentos_sequenciais)} documentos sequenciais')

        # === ETAPA 1.5: RETIRAR SIGILO DOS DOCUMENTOS SEQUENCIAIS ===
        logger.info('[ARGOS][ETAPA 1.5] Removendo sigilo dos documentos sequenciais (se houver)...')
        resultado_sigilo = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log=log)
        if resultado_sigilo.get('total_processados', 0) > 0:
            logger.info(f'[ARGOS][ETAPA 1.5]  {resultado_sigilo["total_processados"]} documento(s) tiveram sigilo removido')
        else:
            logger.info('[ARGOS][ETAPA 1.5]  Todos os documentos sequenciais sem sigilo')

        # === ETAPA 2: TRATAR ANEXOS ESPECIAIS INFOJUD (SIGILO + VISIBILIDADE) ===
        logger.info('[ARGOS][ETAPA 2] Tratando anexos especiais infojud (sigilo + visibilidade)...')
        anexos_info = tratar_anexos_argos(driver, documentos_sequenciais, log=log)
        if not anexos_info:
            logger.info('[ARGOS][ETAPA 2][ERRO] Falha no processamento de anexos - abortando fluxo')
            return False
        logger.info('[ARGOS][ETAPA 2]  Anexos especiais processados com sucesso')

        # === ETAPA 3: SISBAJUD - EXTRAIR DOCUMENTO PDF + REGRAS ===
        logger.info('[ARGOS][ETAPA 3] SISBAJUD - Extraindo documento PDF e aplicando regras...')
        resultado_sisbajud = anexos_info.get('resultado_sisbajud', None)
        sigilo_anexos = anexos_info.get('sigilo_anexos', {})
        executados = anexos_info.get('executados', [])

        if resultado_sisbajud:
            logger.info(f'[ARGOS][ETAPA 3]  SISBAJUD processado: {resultado_sisbajud}')
        else:
            logger.info('[ARGOS][ETAPA 3][AVISO] SISBAJUD não encontrado nos anexos')
        tem_anexos = anexos_info.get('tem_anexos', False)
        if not tem_anexos and resultado_sisbajud is None:
            ato_meios(driver, debug=log)
            return True

        # === ETAPA 4: BUSCAR E APLICAR REGRAS ARGOS (LOOP ITERATIVO) ===
        # Loop: abrir despacho/decisão → extrair → comparar regras → aplicar se tem regra → próximo se não
        
        regra_aplicada = False
        max_tentativas = 15  # Limite para evitar loop infinito
        tentativa = 0
        documentos_ignorados = [] # Rastrear índices já tentados que não tinham regra
        
        while tentativa < max_tentativas and not regra_aplicada:
            tentativa += 1
            
            # Buscar próximo documento com regra Argos, ignorando os que já falharam
            resultado_documento = buscar_documento_argos(driver, log=True, ignorar_indices=documentos_ignorados)
            
            if not resultado_documento or not resultado_documento[0]:
                logger.info('[ARGOS][ETAPA 4] Fim da busca: Nenhum documento candidato restou na timeline')
                break
            
            documento_texto, documento_tipo, documento_idx = resultado_documento
            
            if not documento_texto:
                if documento_idx is not None:
                    documentos_ignorados.append(documento_idx)
                continue
            
            if log:
                logger.info(f'[ARGOS][ETAPA 4] Analisando candidato #{documento_idx} ({documento_tipo})...')

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

            # TENTAR APLICAR REGRAS
            regras_aplicadas = aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, documento_tipo, documento_texto, debug=True)
            
            if regras_aplicadas:
                regra_aplicada = True
                logger.info(f'[ARGOS][ETAPA 4] SUCESSO: Regra aplicada no documento #{documento_idx}')
                break
            else:
                logger.info(f'[ARGOS][ETAPA 4] Nenhuma regra encontrada no documento #{documento_idx}. Tentando próximo...')
                documentos_ignorados.append(documento_idx)
                continue
        
        if not regra_aplicada:
            logger.info('[ARGOS][ETAPA 4-6][ERRO] Nenhum documento teve regra Argos aplicada com sucesso após {tentativa} tentativas')
            return False

        return True

    except Exception as e:
        logger.info(f'[ARGOS][ERRO] Falha crítica no processamento: {e}')
        import traceback
        logger.exception("Erro detectado")
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
            logger.info(f'[ARGOS][CLEANUP][ERRO] Falha ao fechar aba: {cleanup_err}')
            # Não propaga o erro de cleanup para não mascarar erro original