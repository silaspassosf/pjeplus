"""Mandado - Fluxo Argos (Pesquisa Patrimonial)

Consolidado de:
    processamento_argos.py — fluxo principal Argos (etapas 0-5)
    processamento_anexos.py — tratamento de anexos (sigilo, visibilidade, SISBAJUD)

Entrypoint publico: processar_argos()
Sequencia obrigatoria: ETAPA 0 (fechar intimacao) -> ETAPA 1 (documentos sequenciais)
    -> ETAPA 1.5 (sigilo) -> ETAPA 2 (anexos infojud) -> ETAPA 3 (SISBAJUD)
    -> ETAPA 4 (regras) -> ETAPA 5 (destinatarios)
"""

# ══════════════════════ Imports ══════════════════════
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from Fix.core import buscar_documento_argos
from Fix.core import buscar_documentos_sequenciais
from Fix.extracao import extrair_dados_processo, extrair_destinatarios_decisao, extrair_direto, salvar_destinatarios_cache
from Fix.log import logger

from PEC.core_progresso import extrair_numero_processo_pec as extrair_numero_processo

from atos import ato_meios

from .regras import aplicar_regras_argos
from .apoio_fluxos import retirar_sigilo_fluxo_argos, buscar_documentos_sequenciais_via_api
from .entrada_api import fechar_intimacao


# ══════════════════════ Imports de anexos (refatorado) ══════════════════════

from .anexos_argos import tratar_anexos_argos, processar_sisbajud


# ══════════════════════ 2. Fluxo Principal ARGOS ══════════════════════


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

        # ════════════════════════════════════════
        # === ETAPA 0: FECHAR INTIMAÇÃO ===
        logger.info('[ARGOS][ETAPA 0] Fechando intimação...')
        if not fechar_intimacao(driver, log=log):
            logger.info('[ARGOS][ETAPA 0][ERRO CRÍTICO] Falha ao fechar intimação - ABORTANDO FLUXO')
            return False
        logger.info('[ARGOS][ETAPA 0]  Intimação fechada com sucesso')

        # ════════════════════════════════════════
        # === ETAPA 1: IDENTIFICAR DOCUMENTOS SEQUENCIAIS ===
        logger.info('[ARGOS][ETAPA 1] Identificando documentos sequenciais (certidão, ordem de pesquisa, cálculos, intimação, decisão)...')
        documentos_sequenciais, uids_sigilosos_hint = buscar_documentos_sequenciais_via_api(driver, log=log)
        if documentos_sequenciais and len(documentos_sequenciais) >= 2:
            logger.info(f'[ARGOS][ETAPA 1]  {len(documentos_sequenciais)} doc(s) identificados via API')
        else:
            if documentos_sequenciais:
                logger.info('[ARGOS][ETAPA 1] API retornou %d doc(s) (mínimo 2) — fallback DOM', len(documentos_sequenciais))
            else:
                logger.info('[ARGOS][ETAPA 1] API sem resultado — fallback DOM')
            documentos_sequenciais = buscar_documentos_sequenciais(driver, log=log)
            uids_sigilosos_hint = None
        if not documentos_sequenciais:
            logger.info('[ARGOS][ETAPA 1][ERRO] Nenhum documento sequencial encontrado - abortando fluxo')
            return False
        logger.info(f'[ARGOS][ETAPA 1]  Encontrados {len(documentos_sequenciais)} documentos sequenciais')

        # ════════════════════════════════════════
        # === ETAPA 1.5: RETIRAR SIGILO DOS DOCUMENTOS SEQUENCIAIS ===
        logger.info('[ARGOS][ETAPA 1.5] Removendo sigilo dos documentos sequenciais (se houver)...')
        resultado_sigilo = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log=log, uids_sigilosos_hint=uids_sigilosos_hint)
        if resultado_sigilo.get('total_processados', 0) > 0:
            logger.info(f'[ARGOS][ETAPA 1.5]  {resultado_sigilo["total_processados"]} documento(s) tiveram sigilo removido')
        else:
            logger.info('[ARGOS][ETAPA 1.5]  Todos os documentos sequenciais sem sigilo')

        # ════════════════════════════════════════
        # === ETAPA 2: TRATAR ANEXOS ESPECIAIS INFOJUD (SIGILO + VISIBILIDADE) ===
        logger.info('[ARGOS][ETAPA 2] Tratando anexos especiais infojud (sigilo + visibilidade)...')
        anexos_info = tratar_anexos_argos(driver, documentos_sequenciais, log=log)
        if not anexos_info:
            logger.info('[ARGOS][ETAPA 2][AVISO] Nenhum anexo especial encontrado ou processamento não crítico; prosseguindo sem anexos')
            anexos_info = {
                'tem_anexos': False,
                'sigilo_anexos': {}
            }
        else:
            logger.info('[ARGOS][ETAPA 2]  Anexos especiais processados com sucesso')

        # Extrair dados de anexos para decisão de rota
        if hasattr(anexos_info, 'detalhes') and isinstance(anexos_info.detalhes, dict):
            sigilo_anexos = anexos_info.detalhes.get('sigilo_anexos', {})
            tem_anexos = anexos_info.detalhes.get('tem_anexos', False)
        else:
            sigilo_anexos = anexos_info.get('sigilo_anexos', {})
            tem_anexos = anexos_info.get('tem_anexos', False)

        # Sem anexos = sem SISBAJUD = certidão negativa → ato_meios direto
        if not tem_anexos:
            logger.info('[ARGOS][ETAPA 2.5] Certidao sem anexos — ato_meios direto')
            ato_meios(driver, debug=log)
            return True

        # ════════════════════════════════════════
        # === ETAPA 3: ANÁLISE SISBAJUD VIA CERTIDÃO DE DEVOLUÇÃO ===
        # A certidão de devolução JÁ ESTÁ selecionada na timeline.
        # Após tratamento de anexos (ETAPA 2), ela continua selecionada.
        # Usar extrair_direto para ler o conteúdo da certidão.
        logger.info('[ARGOS][ETAPA 3] Lendo certidão de devolução via extrair_direto para análise SISBAJUD...')

        resultado_sisbajud = None
        executados = []

        try:
            resultado_extracao = extrair_direto(driver, timeout=10, debug=log, formatar=True)
            texto_certidao = resultado_extracao.get('conteudo') if resultado_extracao and resultado_extracao.get('sucesso') else None

            if texto_certidao:
                logger.info('[ARGOS][ETAPA 3] Certidão extraída: %d chars', len(texto_certidao))
                try:
                    resultado_sisbajud, motivo, executados = processar_sisbajud(texto_certidao, log=False)
                    if resultado_sisbajud == 'positivo':
                        logger.info(f'[ARGOS][ETAPA 3] SISBAJUD POSITIVO: {motivo}')
                    elif resultado_sisbajud == 'negativo':
                        logger.info(f'[ARGOS][ETAPA 3] SISBAJUD NEGATIVO: {motivo}')
                except ValueError:
                    logger.info('[ARGOS][ETAPA 3] SISBAJUD INDISPONIVEL: marcador "determinacoes normativas e legais" nao encontrado na certidao')
                    resultado_sisbajud = None
                    executados = []
                except Exception as e:
                    logger.error('[ARGOS][ETAPA 3] Erro na análise SISBAJUD: %s', e)
                    resultado_sisbajud = None
                    executados = []
            else:
                logger.info('[ARGOS][ETAPA 3] Certidão sem conteúdo — SISBAJUD indisponível')
        except Exception as e:
            logger.error('[ARGOS][ETAPA 3] Falha ao extrair certidão: %s', e)

        # ════════════════════════════════════════
        # === ETAPA 4: BUSCAR E APLICAR REGRAS ARGOS (LOOP ITERATIVO) ===
        # Loop: abrir despacho/decisão → extrair → comparar regras → aplicar se tem regra → próximo se não
        # LIMITE: Máximo 3 documentos. Se passar de 3 sem encontrar regra, abortar busca.

        timing_etapa4_inicio = time.time()
        logger.info('[ARGOS][TIMING][ETAPA4][INICIO] Iniciando busca e aplicação de regras ARGOS')

        regra_aplicada = False
        max_documentos_testados = 3  # LIMITE: máximo 3 documentos
        documentos_testados = 0
        documentos_ignorados = []

        while documentos_testados < max_documentos_testados and not regra_aplicada:
            # Buscar próximo documento com regra Argos
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
            logger.info('[ARGOS][ETAPA 4] Testando documento %d/%d (índice #%d, tipo: %s)...',
                       documentos_testados, max_documentos_testados, documento_idx, documento_tipo)

            # ════════════════════════════════════════
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
            logger.info(f'[ARGOS][ETAPA 4] Nenhuma regra Argos encontrada nos {documentos_testados} documento(s) testado(s) (limite: {max_documentos_testados})')
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
        logger.exception("Erro detectado")
        return False
