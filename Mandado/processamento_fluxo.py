import time
import unicodedata

from Fix import esperar_elemento, indexar_e_processar_lista
from Fix.log import logger
from Fix.progress import registrar_modulo, atualizar, completar
from Fix.waiters import wait_for_page_load

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
        try:
            # Atualizar progresso - iniciando processamento de item
            atualizar('MANDADO_PROCESSAMENTO', item_atual='processando_mandado')

            # REMOVIDO: Passo 0 de clique na lupa (fa-search lupa-doc-nao-apreciado)
            # Busca o cabeçalho do documento após o carregamento da página
            try:
                # Usar WebDriverWait ao invés de time.sleep
                wait_for_page_load(driver, timeout=10)
                # Busca o cabeçalho usando as funções do Fix.py
                cabecalho_selector = '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'
                cabecalho = esperar_elemento(driver, cabecalho_selector, timeout=15)  # Aumentado de 10 para 15
                if not cabecalho:
                    logger.error('Cabeçalho do documento não encontrado após espera')
                    atualizar('MANDADO_PROCESSAMENTO', erro=True)
                    return False
                texto_doc = cabecalho.text
                if not texto_doc:
                    logger.error('Cabeçalho do documento vazio')
                    atualizar('MANDADO_PROCESSAMENTO', erro=True)
                    return False
            except Exception as e:
                logger.error(f'Erro ao buscar cabeçalho após carregamento: {e}')
                atualizar('MANDADO_PROCESSAMENTO', erro=True)
                return False

            texto_lower = remover_acentos(texto_doc.lower().strip())

            # Identificação dos fluxos
            if any(remover_acentos(termo) in texto_lower for termo in ['pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa', 'certidao de devolucao']):
                logger.info('Identificado fluxo Argos')
                resultado = processar_argos(driver, log=True)
                if not resultado:
                    atualizar('MANDADO_PROCESSAMENTO', erro=True)
                    return False  # Indicar falha ao indexador
            elif any(remover_acentos(termo) in texto_lower for termo in ['oficial de justica', 'certidao de oficial', 'certidao de oficial de justica']):
                logger.info('Identificado fluxo Outros (Oficial de Justiça)')
                fluxo_mandados_outros(driver, log=False)
            else:
                logger.warning(f'Tipo de documento não identificado: {texto_doc}')
                atualizar('MANDADO_PROCESSAMENTO', erro=True)
                return False

            # Sucesso - atualizar progresso
            atualizar('MANDADO_PROCESSAMENTO')
            return True  # Sucesso para indexador

        except Exception as e:
            logger.error(f'Falha ao processar mandado: {str(e)}')
            atualizar('MANDADO_PROCESSAMENTO', erro=True)
            return False

        finally:
            # ===== CALLBACK GERENCIA SUA PRÓPRIA LIMPEZA DE ABAS =====
            # Não deixar abas abertas para o indexador fechar (como fazia o legacy)
            # Assim quando callback retorna, o estado já está limpo.
            try:
                try:
                    current_handles = driver.window_handles
                    current_handle = driver.current_window_handle
                except Exception:
                    return  # Driver pode estar em estado inconsistente
                
                # Se há múltiplas abas, fechar extras e retornar à principal
                main_window = current_handles[0] if current_handles else None
                
                if len(current_handles) > 1 and main_window:
                    # Fechar todas abas exceto a primeira
                    for aba in current_handles[1:]:
                        try:
                            driver.switch_to.window(aba)
                            driver.close()
                            logger.debug(f'[CALLBACK][CLEANUP] Aba fechada')
                        except Exception:
                            pass
                    
                    # Retornar para aba principal
                    try:
                        driver.switch_to.window(main_window)
                        logger.debug(f'[CALLBACK][CLEANUP] Retornando à aba principal')
                    except Exception:
                        pass
            except Exception as cleanup_err:
                logger.debug(f'[CALLBACK][CLEANUP] Erro durante cleanup (não crítico): {cleanup_err}')

    try:
        sucesso_fluxo = bool(indexar_e_processar_lista(driver, fluxo_callback))
        # Completar módulo com sucesso
        completar('MANDADO_PROCESSAMENTO', sucesso=sucesso_fluxo)
    except Exception as e:
        logger.error(f'Erro fatal no processamento de mandados: {e}')
        completar('MANDADO_PROCESSAMENTO', sucesso=False)
        raise