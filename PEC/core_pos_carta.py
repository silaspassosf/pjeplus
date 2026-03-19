import logging
logger = logging.getLogger(__name__)

import time

from selenium.webdriver.common.by import By


def analisar_documentos_pos_carta(driver, numero_processo, observacao, debug=False):
    """
    Analisa documentos após execução de carta para observação "xs pz carta".
    Busca até 4 documentos (sentença, decisão ou despacho) e aplica regras específicas.
    """
    from Fix import extrair_documento, criar_gigs

    def log_msg(msg):
        if debug:
            logger.info(f"[POS_CARTA] {msg}")

    log_msg(f"Iniciando análise de documentos para processo {numero_processo}")

    try:
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            log_msg("Nenhum item encontrado na timeline")
            return False

        log_msg(f"Encontrados {len(itens)} itens na timeline")

        documentos_processados = 0
        max_documentos = 4

        for item in itens:
            if documentos_processados >= max_documentos:
                log_msg(f"Limite de {max_documentos} documentos atingido")
                break

            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                if not link:
                    continue

                doc_text = link.text.lower()
                log_msg(f"Verificando documento: {doc_text}")

                if not any(termo in doc_text for termo in ['sentença', 'decisão', 'despacho']):
                    continue

                log_msg(f"Documento relevante encontrado: {doc_text}")

                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.5)

                    link.click()
                    time.sleep(2)

                    log_msg("Documento aberto com sucesso")

                    resultado_extracao = extrair_documento(driver, timeout=10, log=debug)
                    if not resultado_extracao or not resultado_extracao[0]:
                        log_msg("Falha ao extrair conteúdo do documento")
                        continue

                    texto_documento = resultado_extracao[0].lower()
                    log_msg(f"Conteúdo extraído: {texto_documento[:100]}...")

                    regra_aplicada = False

                    if "defiro a instauração" in texto_documento:
                        log_msg("Regra aplicada: 'defiro a instauração' -> ato_idpj")
                        from atos import ato_idpj
                        resultado_idpj = ato_idpj(driver, debug=debug)

                        if resultado_idpj:
                            log_msg("ato_idpj executado com sucesso")
                            regra_aplicada = True
                        else:
                            log_msg("Falha ao executar ato_idpj")

                    elif "bloqueio realizado" in texto_documento or "844" in texto_documento:
                        log_msg("Regra aplicada: 'bloqueio realizado' ou '844' -> criar GIGS")
                        resultado_gigs = criar_gigs(
                            driver=driver,
                            dias_uteis=1,
                            responsavel="Bruna",
                            observacao="Liberação",
                            timeout=10,
                            log=debug,
                        )

                        if resultado_gigs:
                            log_msg("GIGS criado com sucesso")
                            regra_aplicada = True
                        else:
                            log_msg("Falha ao criar GIGS")

                    elif "instaurado em face" in texto_documento:
                        log_msg("Regra aplicada: 'instaurado em face' -> ato_meios")
                        from atos import ato_meios
                        resultado_meios = ato_meios(driver, debug=debug)

                        if resultado_meios:
                            log_msg("ato_meios executado com sucesso")
                            regra_aplicada = True
                        else:
                            log_msg("Falha ao executar ato_meios")

                    if regra_aplicada:
                        documentos_processados += 1
                        log_msg(f"Documento processado com sucesso ({documentos_processados}/{max_documentos})")
                    else:
                        log_msg("Nenhuma regra aplicável para este documento")

                except Exception as e:
                    log_msg(f"Erro ao processar documento: {e}")
                    continue

            except Exception as e:
                log_msg(f"Erro ao analisar item da timeline: {e}")
                continue

        log_msg(f"Análise concluída. {documentos_processados} documentos processados.")
        return documentos_processados > 0

    except Exception as e:
        log_msg(f"Erro geral na análise de documentos: {e}")
        return False
