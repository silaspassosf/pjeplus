import logging
logger = logging.getLogger(__name__)

import time
from typing import Optional, Dict, Any, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Importar otimizações de execução
from Fix.element_wait import ElementWaitPool

from .core import (
    carregar_progresso_pec,
    navegar_para_atividades,
    reiniciar_driver_e_logar_pje,
    verificar_acesso_negado_pec,
)


from selenium.webdriver.remote.webdriver import WebDriver

def executar_fluxo_robusto(driver: WebDriver) -> Dict[str, Any]:
    """
    Versão robusta do fluxo PEC que usa o sistema centralizado do PJE.PY
    Esta função substitui executar_fluxo_novo() para integração com retry centralizado
    """
    driver_sisb = None  #  NOVO: Driver SISBAJUD compartilhado
    
    try:
        logger.info("[FLUXO_ROBUSTO_PEC] Iniciando fluxo robusto com sistema centralizado...")
        
        # Validar parâmetro driver
        if driver is None:
            logger.info("[FLUXO_ROBUSTO_PEC]  Erro: driver não fornecido (None)")
            return {"sucesso": False, "status": "ERRO_DRIVER", "erro": "Driver não fornecido"}
        
        #  NOVO: Criar driver SISBAJUD compartilhado (sem extrair dados ainda)
        try:
            logger.info("[FLUXO_ROBUSTO_PEC]  Criando driver SISBAJUD compartilhado...")
            from SISB.core import iniciar_sisbajud
            driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
            
            if driver_sisb:
                # Anexar driver SISBAJUD ao driver PJE para acesso global
                driver._driver_sisb_compartilhado = driver_sisb
                logger.info("[FLUXO_ROBUSTO_PEC]  Driver SISBAJUD compartilhado criado e anexado ao driver PJE")
            else:
                logger.info("[FLUXO_ROBUSTO_PEC]  Falha ao criar driver SISBAJUD - continuando sem ele")
        except Exception as e:
            logger.info(f"[FLUXO_ROBUSTO_PEC]  Erro ao criar driver SISBAJUD: {e}")
            driver_sisb = None
        
        # Importar função centralizada do PJE
        from pje import executar_processo_com_retry
        
        # Carregar progresso atual
        progresso = carregar_progresso_pec()
        logger.info(f"[FLUXO_ROBUSTO_PEC] Progresso atual: {len(progresso)} processos executados")
        
        # Verificar se já navegou para atividades
        url_atual = driver.current_url
        if "atividade" not in url_atual.lower():
            logger.info("[FLUXO_ROBUSTO_PEC] Navegando para atividades...")
            if not navegar_para_atividades(driver):
                logger.info("[FLUXO_ROBUSTO_PEC]  Falha ao navegar para atividades")
                return {"sucesso": False, "status": "ERRO_NAVEGACAO", "erro": "Falha na navegação para atividades"}
        
        # Aplicar filtros básicos
        try:
            from Fix.core import aplicar_filtro_100
            logger.info("[FLUXO_ROBUSTO_PEC] Aplicando filtro de 100 itens...")
            if aplicar_filtro_100(driver):
                logger.info("[FLUXO_ROBUSTO_PEC]  Filtro aplicado")
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'table tbody tr'))
                )
        except Exception as e:
            logger.info(f"[FLUXO_ROBUSTO_PEC]  Erro ao aplicar filtro: {e}")
        
        # Callback que usa sistema centralizado
        def callback_pec_centralizado(driver: WebDriver) -> bool:
            """Callback que integra com sistema centralizado de retry"""
            aba_lista_original = None
            try:
                # Preservar aba original para cleanup posterior
                try:
                    aba_lista_original = driver.window_handles[0] if driver.window_handles else None
                except Exception:
                    pass

                numero_processo = extrair_numero_processo_pec(driver)
                if not numero_processo:
                    return False
                
                # Usar sistema centralizado com retry automático
                resultado = executar_processo_com_retry(
                    processar_processo_pec_individual,  # Função específica do PEC
                    driver, 
                    numero_processo, 
                    "PEC"
                )
                
                # Log do resultado
                if not resultado["sucesso"]:
                    logger.error(f"[CALLBACK_PEC]  Processo {numero_processo} falhou: {resultado.get('status', 'Erro desconhecido')}")
                
                return resultado["sucesso"]
            
            finally:
                # ===== CALLBACK GERENCIA SUA PRÓPRIA LIMPEZA DE ABAS =====
                # Após processar_processo_pec_individual completar, fechar suas abas extras
                try:
                    if aba_lista_original:
                        try:
                            current_handles = driver.window_handles
                        except Exception:
                            return  # Driver pode estar em estado inconsistente
                        
                        if len(current_handles) > 1 and aba_lista_original in current_handles:
                            # Fechar todas abas exceto a primeira (original)
                            for aba in current_handles[1:]:
                                try:
                                    driver.switch_to.window(aba)
                                    driver.close()
                                    logger.debug(f'[CALLBACK_PEC][CLEANUP] Aba fechada')
                                except Exception:
                                    pass
                            
                            # Retornar para aba principal
                            try:
                                driver.switch_to.window(aba_lista_original)
                                logger.debug(f'[CALLBACK_PEC][CLEANUP] Retornando à aba principal')
                            except Exception:
                                pass
                except Exception as cleanup_err:
                    logger.debug(f'[CALLBACK_PEC][CLEANUP] Erro durante cleanup (não crítico): {cleanup_err}')
        
        # Executar processamento da lista com callback robusto
        # Usar apenas funções da pasta PEC - sem legado
        if not _organizar_e_executar_buckets(driver, progresso):
            return {"sucesso": False, "status": "ERRO_PROCESSAMENTO", "erro": "Falha na organização e execução de buckets"}
        
        # Calcular estatísticas finais
        progresso_final = carregar_progresso_pec()
        processos_executados = len(progresso_final)

        return {"sucesso": True, "status": "SUCESSO", "processos_executados": processos_executados}
        
    except Exception as e:
        # Se o chamador sinalizou RESTART_PEC, tratamos como pedido explicito de reiniciar o fluxo
        msg = str(e)
        if 'RESTART_PEC' in msg:
            try:
                novo_driver = reiniciar_driver_e_logar_pje(driver, log=True)
            except Exception as restart_exc:
                logger.error(f"[FLUXO_ROBUSTO_PEC]  Erro ao tentar reiniciar driver: {restart_exc}")
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(e)}

            if not novo_driver:
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(e)}

            # Re-executa o fluxo usando o novo driver. A função recarregará o progresso e pulará processos já executados.
            try:
                resultado_reexec = executar_fluxo_robusto(novo_driver)
                return resultado_reexec
            except Exception as reexec_exc:
                logger.error(f"[FLUXO_ROBUSTO_PEC]  Erro na re-execução: {reexec_exc}")
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(reexec_exc)}

        tipo_erro = "OPERACIONAL"
        try:
            url_atual = driver.current_url
            if "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower():
                tipo_erro = "ACESSO_NEGADO"
        except:
            tipo_erro = "CRITICO"

        logger.error(f"[FLUXO_ROBUSTO_PEC]  Erro no fluxo: {e}")

        # Se for acesso negado, tentar reiniciar driver e retomar o fluxo
        if tipo_erro == "ACESSO_NEGADO":
            try:
                novo_driver = reiniciar_driver_e_logar_pje(driver, log=True)
            except Exception as restart_exc:
                logger.error(f"[FLUXO_ROBUSTO_PEC]  Erro ao tentar reiniciar driver: {restart_exc}")
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(e)}

            if not novo_driver:
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(e)}

            try:
                resultado_reexec = executar_fluxo_robusto(novo_driver)
                return resultado_reexec
            except Exception as reexec_exc:
                logger.error(f"[FLUXO_ROBUSTO_PEC]  Erro na re-execução: {reexec_exc}")
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(reexec_exc)}

        return {"sucesso": False, "status": tipo_erro, "erro": str(e)}
    
    finally:
        #  NOVO: Fechar driver SISBAJUD compartilhado
        if driver_sisb:
            try:
                driver_sisb.quit()
            except Exception as e:
                logger.error(f"[FLUXO_ROBUSTO_PEC]  Erro ao fechar driver SISBAJUD: {e}")


def executar_fluxo_novo(driver: Optional[WebDriver] = None) -> bool:
    """
    Executa o novo fluxo conforme especificações:
    1- usar driver fornecido ou criar novo e executar login conforme definido em driver_config.py
    2- iniciar fluxo logo após login navegando até atividades
    3- não clicar no ícone "Atividades sem prazo"
    4- filtrar com xs na descrição ANTES do filtro 100
    5- indexar lista com a função definida de fix.py
    6- ao indexar numero do processo - atividade (observação)
    """
    import time

    # Inicializar otimizações de execução
    wait_pool = None  # Será inicializado quando driver estiver disponível

    progresso = carregar_progresso_pec()
    driver_criado_aqui = False

    try:
        # Configurar driver e fazer login
        driver, driver_criado_aqui = _configurar_driver(driver)
        if not driver:
            return False

        # Inicializar ElementWaitPool agora que temos o driver
        wait_pool = ElementWaitPool(driver, explicit_wait=10)

        # Navegar para atividades
        if not _navegar_atividades(driver):
            if driver_criado_aqui:
                driver.quit()
            return False

        # Aplicar filtros necessários
        if not _aplicar_filtros(driver):
            if driver_criado_aqui:
                driver.quit()
            return False

        # Organizar processos em buckets e executar individualmente
        if not _organizar_e_executar_buckets(driver, progresso):
            if driver_criado_aqui:
                driver.quit()
            return False

        return True

    except Exception as e:
        logger.error(f"[FLUXO_NOVO]  Erro durante o processamento: {e}")
        if driver_criado_aqui and driver:
            try:
                driver.quit()
            except:
                pass
        return False
    finally:
        # Fechar driver SISBAJUD global ANTES do driver principal para evitar erros de sessão
        try:
            from PEC.regras import fechar_driver_sisbajud_global
            fechar_driver_sisbajud_global()
        except Exception as e:
            logger.error(f'[FLUXO_NOVO]  Erro ao fechar driver SISBAJUD global: {e}')
        
        # Aguardar um pouco para garantir que o driver SISBAJUD foi completamente fechado
        import time
        time.sleep(0.5)
        
        # Só fecha o driver PJE se foi criado aqui
        if driver_criado_aqui and driver:
            try:
                logger.info('[FLUXO_NOVO]  Fechando driver PJE...')
                driver.quit()
                logger.info('[FLUXO_NOVO]  Driver PJE fechado com sucesso')
            except Exception as e:
                logger.error(f'[FLUXO_NOVO]  Erro ao fechar driver PJE: {e}')


def _configurar_driver(driver: Optional[WebDriver]) -> Tuple[Optional[WebDriver], bool]:
    """
    Helper: Configura driver e realiza login.

    Args:
        driver: Driver fornecido ou None

    Returns:
        tuple: (driver_configurado, driver_criado_aqui)
    """
    driver_criado_aqui = False

    try:
        # Se não recebeu driver, cria um novo
        if driver is None:
            from driver_config import criar_driver, login_func, login_manual
            driver = criar_driver(headless=False)
            driver_criado_aqui = True
            if not driver:
                return None, False

            # Realizar login
            if not login_func(driver):
                try:
                    if not login_manual(driver):
                        driver.quit()
                        return None, False
                except Exception as e:
                    logger.error(f'[FLUXO_NOVO]  Erro no login manual: {e}')
                    driver.quit()
                    return None, False

        return driver, driver_criado_aqui

    except Exception as e:
        logger.error(f"[FLUXO_NOVO]  Erro ao configurar driver: {e}")
        if driver_criado_aqui and driver:
            driver.quit()
        return None, False


def _navegar_atividades(driver: WebDriver) -> bool:
    """
    Helper: Navega para a tela de atividades.

    Args:
        driver: WebDriver configurado

    Returns:
        bool: True se navegação bem-sucedida
    """
    try:
        if not navegar_para_atividades(driver):
            return False
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'table'))
        )
        return True
    except Exception as e:
        logger.error(f"[FLUXO_NOVO]  Erro ao navegar para atividades: {e}")
        return False


def _aplicar_filtros(driver: WebDriver) -> bool:
    """
    Helper: Aplica filtros necessários (xs na descrição, depois 100 itens por página).

    Args:
        driver: WebDriver na tela de atividades

    Returns:
        bool: True se filtros aplicados com sucesso
    """
    try:
        # 1. Aplicar filtro xs na descrição PRIMEIRO
        from PEC.core_navegacao import aplicar_filtro_xs
        logger.info("[FLUXO_NOVO] Aplicando filtro 'xs' na descrição...")
        if not aplicar_filtro_xs(driver):
            logger.warning("[FLUXO_NOVO]  Falha ao aplicar filtro xs, continuando...")
        
        # Aguardar tabela recarregar após filtro xs
        import time
        time.sleep(2)
        
        # 2. Aplicar filtro 100 itens por página
        logger.info("[FLUXO_NOVO] Aplicando filtro 100 itens...")
        from Fix.core import aplicar_filtro_100
        if aplicar_filtro_100(driver):
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table tbody tr'))
            )
            logger.info("[FLUXO_NOVO]  Filtros aplicados com sucesso")

        return True

    except Exception as e:
        logger.error(f"[FLUXO_NOVO]  Erro ao aplicar filtros: {e}")
        return False


def _organizar_e_executar_buckets(driver: WebDriver, progresso: Dict[str, Any]) -> bool:
    """
    Helper: Organiza processos em buckets e executa TODOS os processos de cada bucket individualmente.

    Args:
        driver: WebDriver configurado
        progresso: Dicionário de progresso

    Returns:
        bool: True se processamento bem-sucedido
    """
    try:
        from .processamento_indexacao import indexar_e_criar_buckets_unico
        from .processamento_buckets import _processar_bucket_demais, _processar_bucket_sisbajud

        # Usar a função de buckets para organizar processos (dry_run=True para apenas organizar)
        filtros_observacao = ['xs', 'silas', 'sobrestamento', 'sob ']
        buckets = indexar_e_criar_buckets_unico(driver, filtros_observacao, dry_run=True)

        if not buckets:
            return False

        # MOSTRAR RESUMO DOS BUCKETS FORMADOS
        buckets_com_processos = {}
        logger.info("[BUCKETS_PEC] 🪣 Buckets formados:")
        for bucket_name in ['sobrestamento', 'carta', 'comunicacoes', 'outros', 'sisbajud']:
            bucket = buckets.get(bucket_name, [])
            if bucket:  # Só mostrar buckets que têm processos
                buckets_com_processos[bucket_name] = bucket
                count = len(bucket)

                logger.info(f"[BUCKETS_PEC] {bucket_name.upper():<12}: {count:>3} processos")

                # Mostrar exemplos dos processos
                for i, proc in enumerate(bucket[:3]):  # Máximo 3 exemplos
                    obs_curta = proc['observacao'][:50] + ('...' if len(proc['observacao']) > 50 else '')
                    logger.info(f"  {i+1}. {proc['numero']}: '{obs_curta}'")

        if not buckets_com_processos:
            return True

        # EXECUTAR TODOS OS PROCESSOS DE CADA BUCKET INDIVIDUALMENTE
        total_results = {'sucesso': 0, 'erro': 0}

        # Processar buckets não-SISBAJUD primeiro
        for bucket_name in ['sobrestamento', 'carta', 'comunicacoes', 'outros']:
            bucket = buckets_com_processos.get(bucket_name, [])
            if not bucket:
                continue

            res = _processar_bucket_demais(driver, bucket, progresso, descricao=f"{bucket_name.upper()}")
            total_results['sucesso'] += res.get('sucesso', 0)
            total_results['erro'] += res.get('erro', 0)

        # Processar SISBAJUD por último
        bucket_sisbajud = buckets_com_processos.get('sisbajud', [])
        if bucket_sisbajud:
            res = _processar_bucket_sisbajud(driver, bucket_sisbajud, progresso)
            total_results['sucesso'] += res.get('sucesso', 0)
            total_results['erro'] += res.get('erro', 0)

        # Relatório final
        processos_sucesso = total_results['sucesso']
        processos_erro = total_results['erro']
        buckets_processados = len(buckets_com_processos)
        total_processos = sum(len(bucket) for bucket in buckets_com_processos.values())

        logger.error(f"[BUCKETS_PEC] Erros: {processos_erro}")

        return True

    except Exception as e:
        # RESTART_PEC deve ser propagado para o nível superior
        if 'RESTART_PEC' in str(e):
            raise
        logger.error(f"[BUCKETS_PEC]  Erro ao organizar e executar buckets: {e}")
        return False
