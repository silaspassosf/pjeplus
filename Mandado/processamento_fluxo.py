import time
import unicodedata

from Fix import esperar_elemento, indexar_e_processar_lista
from Fix.log import logger
from Fix.progress import registrar_modulo, atualizar, completar
from Fix.monitoramento_progresso_unificado import executar_com_monitoramento_unificado
from Fix.core import wait_for_page_load

from .processamento_argos import processar_argos
from .processamento_outros import fluxo_mandados_outros


def fluxo_mandado(driver):
    """
    Percorre a lista de processos e executa o fluxo adequado (Argos ou Outros) para cada mandado.
    Usa sistema centralizado de progresso.
    """
    def remover_acentos(txt):
        return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

    # Registrar módulo no sistema de progresso
    registrar_modulo('MANDADO_PROCESSAMENTO', 0)  # Total será atualizado dinamicamente

    def fluxo_callback(driver):
        proc_id = getattr(driver, '_numero_processo_lista', '[sem número]')
        logger.info(f'[MANDADO][CALLBACK] invoked for {proc_id}')

        # Atualiza módulo (visão geral)
        atualizar('MANDADO_PROCESSAMENTO', item_atual='processando_mandado')

        # Função interna que executa o processamento real e retorna bool
        def _processar_atual(driver):
            try:
                # Esperar carregamento e obter cabeçalho
                wait_for_page_load(driver, timeout=10)
                cabecalho_selector = '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'
                cabecalho = esperar_elemento(driver, cabecalho_selector, timeout=15)
                if not cabecalho:
                    logger.error('Cabeçalho do documento não encontrado após espera')
                    return False
                texto_doc = cabecalho.text
                if not texto_doc:
                    logger.error('Cabeçalho do documento vazio')
                    return False

                texto_lower = remover_acentos(texto_doc.lower().strip())

                # Identificação dos fluxos
                if any(remover_acentos(termo) in texto_lower for termo in ['pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa', 'certidao de devolucao']):
                    logger.info('Identificado fluxo Argos')
                    resultado = processar_argos(driver, log=True)
                    return bool(resultado)
                elif any(remover_acentos(termo) in texto_lower for termo in ['oficial de justica', 'certidao de oficial', 'certidao de oficial de justica']):
                    logger.info('Identificado fluxo Outros (Oficial de Justiça)')
                    fluxo_mandados_outros(driver, log=False)
                    return True
                else:
                    logger.warning(f'Tipo de documento não identificado: {texto_doc}')
                    return False

            except Exception as e:
                logger.error(f'Falha ao processar mandado: {str(e)}')
                return False

            finally:
                # Cleanup de abas (sempre tentar)
                try:
                    current_handles = driver.window_handles
                    main_window = current_handles[0] if current_handles else None
                    if len(current_handles) > 1 and main_window:
                        for aba in current_handles[1:]:
                            try:
                                driver.switch_to.window(aba)
                                driver.close()
                                logger.debug(f'[CALLBACK][CLEANUP] Aba fechada')
                            except Exception:
                                pass
                        try:
                            driver.switch_to.window(main_window)
                            logger.debug(f'[CALLBACK][CLEANUP] Retornando à aba principal')
                        except Exception:
                            pass
                except Exception as cleanup_err:
                    logger.debug(f'[CALLBACK][CLEANUP] Erro durante cleanup (não crítico): {cleanup_err}')

        # Executar com monitoramento unificado (skipa se já processado)
        try:
            sucesso, numero = executar_com_monitoramento_unificado('mandado', driver, None, _processar_atual, suppress_load_log=True)
            # Atualizar progresso de módulo conforme resultado
            if sucesso:
                atualizar('MANDADO_PROCESSAMENTO')
            else:
                atualizar('MANDADO_PROCESSAMENTO', erro=True)
            return bool(sucesso)
        except Exception as e:
            logger.error(f'Erro ao executar com monitoramento unificado: {e}')
            atualizar('MANDADO_PROCESSAMENTO', erro=True)
            return False

    try:
        sucesso_fluxo = bool(indexar_e_processar_lista(driver, fluxo_callback))
        # Completar módulo com sucesso
        completar('MANDADO_PROCESSAMENTO', sucesso=sucesso_fluxo)
    except Exception as e:
        logger.error(f'Erro fatal no processamento de mandados: {e}')
        completar('MANDADO_PROCESSAMENTO', sucesso=False)
        raise