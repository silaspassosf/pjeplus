import time
from selenium.webdriver.remote.webdriver import WebDriver

from Fix.documents import buscar_documentos_sequenciais
from Fix.extracao import extrair_dados_processo, extrair_destinatarios_decisao, salvar_destinatarios_cache
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
    # === TIMING: INÍCIO DO PROCESSAMENTO ===
    timing_inicio = time.time()
    logger.info('[ARGOS][TIMING][PROCESAR_ARGOS][INICIO]')
    
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
            logger.info('[ARGOS][ETAPA 2][AVISO] Nenhum anexo especial encontrado ou processamento não crítico; prosseguindo sem anexos')
            anexos_info = {
                'tem_anexos': False,
                'resultado_sisbajud': None,
                'sigilo_anexos': {},
                'executados': []
            }
        else:
            logger.info('[ARGOS][ETAPA 2]  Anexos especiais processados com sucesso')

        # Extrair dados de anexos para decisão de rota
        if hasattr(anexos_info, 'detalhes') and isinstance(anexos_info.detalhes, dict):
            resultado_sisbajud = anexos_info.detalhes.get('resultado_sisbajud', None)
            sigilo_anexos = anexos_info.detalhes.get('sigilo_anexos', {})
            executados = anexos_info.detalhes.get('executados', [])
            tem_anexos = anexos_info.detalhes.get('tem_anexos', False)
        else:
            resultado_sisbajud = anexos_info.get('resultado_sisbajud', None)
            sigilo_anexos = anexos_info.get('sigilo_anexos', {})
            executados = anexos_info.get('executados', [])
            tem_anexos = anexos_info.get('tem_anexos', False)

        # Sem anexos = sem SISBAJUD = certidão negativa → ato_meios direto
        if not tem_anexos:
            logger.info('[ARGOS][ETAPA 2.5] Certidao sem anexos — ato_meios direto')
            ato_meios(driver, debug=log)
            return True

        # === ETAPA 3: SISBAJUD - EXTRAIR DOCUMENTO PDF + REGRAS ===
        logger.info('[ARGOS][ETAPA 3] SISBAJUD - Extraindo documento PDF e aplicando regras...')
        if resultado_sisbajud:
            logger.info(f'[ARGOS][ETAPA 3]  SISBAJUD processado: {resultado_sisbajud}')
        else:
            logger.info('[ARGOS][ETAPA 3][AVISO] SISBAJUD não encontrado nos anexos')

        # === ETAPA 4: BUSCAR E APLICAR REGRAS ARGOS (LOOP ITERATIVO) ===
        # Loop: abrir despacho/decisão → extrair → comparar regras → aplicar se tem regra → próximo se não
        # LIMITE: Máximo 3 documentos. Se passar de 3 sem encontrar regra, abortar busca.
        
        timing_etapa4_inicio = time.time()
        logger.info('[ARGOS][TIMING][ETAPA4][INICIO] Iniciando busca e aplicação de regras ARGOS')
        
        regra_aplicada = False
        max_documentos_testados = 3  # LIMITE: máximo 3 documentos
        documentos_testados = 0
        documentos_ignorados = []  # Rastrear índices já tentados que não tinham regra
        
        while documentos_testados < max_documentos_testados and not regra_aplicada:
            # Buscar próximo documento com regra Argos, ignorando os que já falharam
            timing_busca_inicio = time.time()
            resultado_documento = buscar_documento_argos(driver, log=True, ignorar_indices=documentos_ignorados)
            timing_busca_fim = time.time()
            logger.info(f'[ARGOS][TIMING][BUSCA_DOC] {timing_busca_fim - timing_busca_inicio:.3f}s')
            
            if not resultado_documento or not resultado_documento[0]:
                logger.info('[ARGOS][ETAPA 4] Fim da busca: Nenhum documento candidato restou na timeline')
                break
            
            documento_texto, documento_tipo, documento_idx = resultado_documento
            
            if not documento_texto:
                if documento_idx is not None:
                    documentos_ignorados.append(documento_idx)
                continue
            
            documentos_testados += 1
            if log:
                logger.info(f'[ARGOS][ETAPA 4] Testando documento {documentos_testados}/{max_documentos_testados} (índice #{documento_idx}, tipo: {documento_tipo})...')

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
            timing_regras_inicio = time.time()
            regras_aplicadas = aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, documento_tipo, documento_texto, debug=True)
            timing_regras_fim = time.time()
            logger.info(f'[ARGOS][TIMING][APLICAR_REGRAS] {timing_regras_fim - timing_regras_inicio:.3f}s')
            
            if regras_aplicadas:
                regra_aplicada = True
                logger.info(f'[ARGOS][ETAPA 4] ✅ SUCESSO: Regra aplicada no documento #{documento_idx} ({documentos_testados}/{max_documentos_testados})')
                break
            else:
                logger.info(f'[ARGOS][ETAPA 4] ❌ Nenhuma regra encontrada no documento #{documento_idx}')
                documentos_ignorados.append(documento_idx)
                
                # Se atingiu limite de documentos testados, parar busca
                if documentos_testados >= max_documentos_testados:
                    logger.info(f'[ARGOS][ETAPA 4] Limite de documentos ({max_documentos_testados}) atingido. Interrompendo busca por regras.')
                    break
                continue
        
        # === TIMING: FIM DA ETAPA 4 ===
        timing_etapa4_total = time.time() - timing_etapa4_inicio
        logger.info(f'[ARGOS][TIMING][ETAPA4][TOTAL] {timing_etapa4_total:.3f}s documentos_testados={documentos_testados} regra_aplicada={regra_aplicada}')
        
        if not regra_aplicada:
            logger.info(f'[ARGOS][ETAPA 4] ❌ ERRO: Nenhuma regra Argos encontrada nos {documentos_testados} documento(s) testado(s) (limite: {max_documentos_testados})')
            timing_total = time.time() - timing_inicio
            logger.info(f'[ARGOS][TIMING][PROCESSAR_ARGOS][FALHA] {timing_total:.3f}s')
            return False

        timing_total = time.time() - timing_inicio
        logger.info(f'[ARGOS][TIMING][PROCESSAR_ARGOS][SUCESSO] {timing_total:.3f}s')
        return True

    except Exception as e:
        timing_erro = time.time() - timing_inicio
        logger.info(f'[ARGOS][TIMING][PROCESSAR_ARGOS][ERRO] {timing_erro:.3f}s')
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