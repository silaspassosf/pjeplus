"""
judicial_fluxo.py - Fluxos principais de atos judiciais
======================================================

Módulo principal com os fluxos de alto nível para atos judiciais,
usando os módulos especializados para navegação, conclusão, modelos,
prazos e bloqueios.
"""

from Fix.core import aguardar_e_clicar, esperar_elemento, safe_click, safe_click_no_scroll, logger, esperar_url_conter, preencher_multiplos_campos
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.utils import executar_coleta_parametrizavel, inserir_link_ato_validacao
from Fix.extracao import bndt, criar_gigs
from Fix.movimento_helpers import selecionar_movimento_auto
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
import time
import logging

from typing import Optional, Tuple, Dict, List, Union, Callable, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario
from .core import verificar_carregamento_pagina, aguardar_e_verificar_aba

# Importações dos módulos especializados
from .judicial_navegacao import (
    abrir_tarefa_processo,
    limpar_overlays,
    navegar_para_conclusao,
    preparar_campo_minutar
)
from .judicial_modelos import (
    escolher_tipo_conclusao,
    aguardar_transicao_minutar,
    verificar_estado_atual,
    focar_campo_minutar_se_necessario
)
from .judicial_utils import (
    preencher_prazos_destinatarios,
    verificar_bloqueio_recente
)


def fluxo_cls(
    driver: WebDriver,
    conclusao_tipo: str,
    forcar_iniciar_execucao: bool = False
) -> bool:
    '''
    Fluxo principal para CLS (Conclusão ao Magistrado  Minutar).

    LÓGICA SEQUENCIAL:
    1. Verificar estados especiais (/assinar, /minutar, /conclusao)
    2. Abrir tarefa do processo se necessário
    3. Navegar para 'Conclusão ao Magistrado'
    4. Escolher tipo de conclusão
    5. Aguardar transição para minutar e preparar campo

    Returns:
        bool: True se sucesso, False se falha
    '''
    # === TIMING: INICIO ===
    timing_inicio = time.time()
    logger.info('[CLS][TIMING][INICIO]')
    
    try:
        # Helper local: verifica e reaplica sigilo/PEC após um save que possa ter resetado o estado
        def _verificar_reaplicar_sigilo_pec():
            try:
                changed = False
                # Reaplicar sigilo se solicitado
                if sigilo:
                    try:
                        checkbox_sig = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-checkbox#sigilo'))
                        )
                        try:
                            is_selected = checkbox_sig.is_selected()
                        except Exception:
                            is_selected = 'mat-checked' in (checkbox_sig.get_attribute('class') or '')
                        if not is_selected:
                            try:
                                checkbox_sig.click()
                            except Exception:
                                driver.execute_script('arguments[0].click();', checkbox_sig)
                            logger.info('[ATO][SIGILO] Reaplicado sigilo após save')
                            changed = True
                    except Exception as e:
                        logger.debug(f'[ATO][SIGILO] Não foi possível reencontrar sigilo: {e}')

                # Reaplicar PEC se solicitado
                if marcar_pec is not None:
                    want_pec = str(marcar_pec).lower() in ("sim", "true", "1", "yes")
                    try:
                        pec_elem = None
                        try:
                            pec_elem = driver.find_element(By.CSS_SELECTOR, 'mat-checkbox[aria-label="Enviar para PEC"]')
                        except Exception:
                            try:
                                pec_elem = driver.find_element(By.CSS_SELECTOR, 'pje-intimacao-automatica mat-checkbox[aria-label="Enviar para PEC"]')
                            except Exception:
                                try:
                                    pec_input = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Enviar para PEC"]')
                                    pec_elem = pec_input.find_element(By.XPATH, '..')
                                except Exception:
                                    pec_elem = None

                        if pec_elem:
                            # Implementação legada mais robusta para togglear PEC (scroll + clicar label via JS)
                            try:
                                # localizar pec_checkbox e pec_input como no legado
                                pec_checkbox = None
                                pec_input = None
                                try:
                                    pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'mat-checkbox[aria-label="Enviar para PEC"]')
                                    pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                                except Exception:
                                    try:
                                        pec_checkbox = driver.find_element(By.CSS_SELECTOR, 'div.checkbox-pec mat-checkbox')
                                        pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                                    except Exception:
                                        try:
                                            pec_input = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Enviar para PEC"]')
                                            pec_checkbox = pec_input.find_element(By.XPATH, './ancestor::mat-checkbox[1]')
                                        except Exception:
                                            pec_checkbox = None
                                            pec_input = None

                                if not pec_checkbox or not pec_input:
                                    logger.debug('[ATO][PEC] Checkbox PEC não encontrado na estrutura esperada')
                                else:
                                    # debug: estado antes
                                    try:
                                        cls = pec_checkbox.get_attribute('class') or ''
                                    except Exception:
                                        cls = ''
                                    try:
                                        aria_checked = pec_input.get_attribute('aria-checked')
                                    except Exception:
                                        aria_checked = None
                                    try:
                                        checked_attr = pec_input.get_attribute('checked')
                                    except Exception:
                                        checked_attr = None
                                    try:
                                        is_selected_prop = pec_input.is_selected()
                                    except Exception:
                                        is_selected_prop = None
                                    

                                    checked = False
                                    try:
                                        if aria_checked == 'true' or checked_attr == 'true' or is_selected_prop or 'mat-checkbox-checked' in cls:
                                            checked = True
                                    except Exception:
                                        checked = False

                                    # ação: marcar ou desmarcar via clique no label quando disponível
                                    if want_pec and not checked:
                                        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', pec_checkbox)
                                        time.sleep(0.2)
                                        try:
                                            label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout')
                                            driver.execute_script('arguments[0].click();', label)
                                        except Exception:
                                            driver.execute_script('arguments[0].click();', pec_checkbox)
                                        logger.info('[ATO][PEC] Marcado (legado)')
                                        time.sleep(0.3)
                                    elif not want_pec and checked:
                                        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', pec_checkbox)
                                        time.sleep(0.2)
                                        try:
                                            label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout')
                                            driver.execute_script('arguments[0].click();', label)
                                        except Exception:
                                            driver.execute_script('arguments[0].click();', pec_checkbox)
                                        logger.info('[ATO][PEC] Desmarcado (legado)')
                                        time.sleep(0.3)

                                    # debug: estado depois
                                    try:
                                        cls2 = pec_checkbox.get_attribute('class') or ''
                                    except Exception:
                                        cls2 = ''
                                    try:
                                        aria_checked2 = pec_input.get_attribute('aria-checked')
                                    except Exception:
                                        aria_checked2 = None
                                    try:
                                        checked_attr2 = pec_input.get_attribute('checked')
                                    except Exception:
                                        checked_attr2 = None
                                    try:
                                        is_selected_prop2 = pec_input.is_selected()
                                    except Exception:
                                        is_selected_prop2 = None
                                    

                                    changed = True
                                    try:
                                        btn_gravar_local = WebDriverWait(driver, 2).until(
                                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'pje-intimacao-automatica button[aria-label*="Gravar"]'))
                                        )
                                        btn_gravar_local.click()
                                        time.sleep(0.6)
                                    except Exception:
                                        pass
                            except Exception as e:
                                logger.error(f'[ATO][PEC] Erro na rotina legada de PEC: {e}')
                    except Exception as e:
                        logger.debug(f'[ATO][PEC] Não foi possível verificar/reaplicar PEC: {e}')

                return changed
            except Exception as e:
                logger.debug(f'[ATO][REAPLICAR] Erro geral ao reaplicar sigilo/PEC: {e}')
                return False
        logger.info('=' * 60)
        logger.info('FLUXO CLS - INICIANDO')
        logger.info('=' * 60)

        # ===== VERIFICAÇÃO INICIAL: Estados especiais =====
        timing_check_estado = time.time()
        estado_atual = verificar_estado_atual(driver)
        timing_check_estado = time.time() - timing_check_estado
        logger.info(f'[CLS][TIMING][CHECK_ESTADO] {timing_check_estado:.3f}s estado={estado_atual}')
        
        if estado_atual == 'assinar':
            logger.info('[CLS]  Processo já está em /assinar - ato cumprido')
            timing_total = time.time() - timing_inicio
            logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (estado pré-assinar)')
            return True
        elif estado_atual == 'minutar':
            logger.info('[CLS]  Já estamos em /minutar - focando no campo')
            focar_campo_minutar_se_necessario(driver)
            timing_total = time.time() - timing_inicio
            logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (já em /minutar)')
            return True
        elif estado_atual == 'conclusao':
            logger.info('[CLS] Já estamos em /conclusao - pulando navegação')
            ja_em_conclusao = True
        else:
            ja_em_conclusao = False

        # ===== PASSO 1: ABRIR TAREFA DO PROCESSO (se necessário) =====
        ja_em_minutar = False
        if not ja_em_conclusao:
            logger.info('[CLS] Passo 1: Abrindo tarefa do processo...')
            timing_tarefa_inicio = time.time()
            sucesso, ja_em_minutar = abrir_tarefa_processo(driver)
            timing_tarefa = time.time() - timing_tarefa_inicio
            logger.info(f'[CLS][TIMING][ABRIR_TAREFA] {timing_tarefa:.3f}s sucesso={sucesso}')
            
            if not sucesso:
                logger.error('[CLS] Falha ao abrir tarefa do processo')
                timing_total = time.time() - timing_inicio
                logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha ao abrir tarefa')
                return False
            
            # Se já está em /minutar após abrir tarefa, pular navegação e transição
            if ja_em_minutar:
                # Abertura da tarefa pode ter levado diretamente a /assinar, /minutar ou /conclusao
                current = (driver.current_url or '').lower()
                if '/assinar' in current:
                    logger.info('[CLS] ✅ Já em /assinar após abrir tarefa - ato cumprido')
                    timing_total = time.time() - timing_inicio
                    logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (já em /assinar após abrir tarefa)')
                    return True
                elif '/minutar' in current:
                    logger.info('[CLS] ✅ Já em /minutar após abrir tarefa - fluxo CLS concluído')
                    focar_campo_minutar_se_necessario(driver)
                    timing_total = time.time() - timing_inicio
                    logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (já em /minutar após abrir tarefa)')
                    return True
                elif '/conclusao' in current:
                    logger.info('[CLS] Detectado /conclusao após abrir tarefa — executando tipo de conclusão para transicionar a /minutar')
                    # Escolher o tipo de conclusão e aguardar transição para minutar
                    try:
                        if not escolher_tipo_conclusao(driver, conclusao_tipo):
                            logger.error(f'[CLS] Falha ao escolher tipo de conclusão após abrir tarefa: {conclusao_tipo}')
                            timing_total = time.time() - timing_inicio
                            logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha ao escolher tipo conclusão')
                            return False
                        if not aguardar_transicao_minutar(driver):
                            logger.error('[CLS] Falha na transição para minutar após escolher tipo de conclusão')
                            timing_total = time.time() - timing_inicio
                            logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha na transição minutar')
                            return False
                        focar_campo_minutar_se_necessario(driver)
                        timing_total = time.time() - timing_inicio
                        logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (transicionado para /minutar após conclusão)')
                        return True
                    except Exception as e:
                        logger.error(f'[CLS][ERRO CRÍTICO] Exceção ao processar /conclusao após abrir tarefa: {e}')
                        import traceback
                        logger.error(traceback.format_exc())
                        return False
                else:
                    # Estado inesperado — continuar o fluxo padrão
                    logger.info(f'[CLS] Estado inesperado após abrir tarefa: {current} — continuando fluxo')

        # ===== PASSO 2: LIMPAR OVERLAYS =====
        logger.info('[CLS] Passo 2: Limpando overlays...')
        timing_overlays_inicio = time.time()
        limpar_overlays(driver)
        timing_overlays = time.time() - timing_overlays_inicio
        logger.info(f'[CLS][TIMING][LIMPAR_OVERLAYS] {timing_overlays:.3f}s')

        # ===== PASSO 3: NAVEGAR PARA CONCLUSÃO (se necessário) =====
        if not ja_em_conclusao:
            logger.info('[CLS] Passo 3: Navegando para conclusão...')
            timing_nav_inicio = time.time()
            try:
                if not navegar_para_conclusao(driver):
                    logger.error('[CLS] Falha ao navegar para conclusão')
                    timing_total = time.time() - timing_inicio
                    logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha ao navegar conclusão')
                    return False
            except Exception as e:
                logger.error(f'[CLS][ERRO CRÍTICO] Exceção em navegar_para_conclusao: {e}')
                import traceback
                logger.error(traceback.format_exc())
                return False
            timing_nav = time.time() - timing_nav_inicio
            logger.info(f'[CLS][TIMING][NAVEGAR_CONCLUSAO] {timing_nav:.3f}s')

        # ===== PASSO 4: ESCOLHER TIPO DE CONCLUSÃO =====
        logger.info(f'[CLS] Passo 4: Escolhendo tipo de conclusão: {conclusao_tipo}')
        timing_tipo_inicio = time.time()
        try:
            if not escolher_tipo_conclusao(driver, conclusao_tipo):
                logger.error(f'[CLS] Falha ao escolher tipo de conclusão: {conclusao_tipo}')
                timing_total = time.time() - timing_inicio
                logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha ao escolher tipo conclusão')
                return False
        except Exception as e:
            logger.error(f'[CLS][ERRO CRÍTICO] Exceção em escolher_tipo_conclusao: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return False
        timing_tipo = time.time() - timing_tipo_inicio
        logger.info(f'[CLS][TIMING][ESCOLHER_TIPO] {timing_tipo:.3f}s tipo={conclusao_tipo}')

        # ===== PASSO 5: AGUARDAR TRANSIÇÃO PARA MINUTAR =====
        logger.info('[CLS] Passo 5: Aguardando transição para minutar...')
        timing_transicao_inicio = time.time()
        try:
            if not aguardar_transicao_minutar(driver):
                logger.error('[CLS] Falha na transição para minutar')
                timing_total = time.time() - timing_inicio
                logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha na transição minutar')
                return False
        except Exception as e:
            logger.error(f'[CLS][ERRO CRÍTICO] Exceção em aguardar_transicao_minutar: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return False
        timing_transicao = time.time() - timing_transicao_inicio
        logger.info(f'[CLS][TIMING][TRANSICAO_MINUTAR] {timing_transicao:.3f}s')

        # ===== PASSO 6: PREPARAR CAMPO DE MINUTAR =====
        logger.info('[CLS] Passo 6: Preparando campo de minutar...')
        timing_campo_inicio = time.time()
        try:
            if not preparar_campo_minutar(driver):
                logger.error('[CLS] Falha ao preparar campo de minutar')
                timing_total = time.time() - timing_inicio
                logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha ao preparar campo minutar')
                return False
        except Exception as e:
            logger.error(f'[CLS][ERRO CRÍTICO] Exceção em preparar_campo_minutar: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return False
        timing_campo = time.time() - timing_campo_inicio
        logger.info(f'[CLS][TIMING][PREPARAR_CAMPO] {timing_campo:.3f}s')

        logger.info('=' * 60)
        logger.info('FLUXO CLS - CONCLUÍDO COM SUCESSO')
        logger.info('=' * 60)
        
        timing_total = time.time() - timing_inicio
        logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (fluxo completo)')
        return True

    except Exception as e:
        timing_total = time.time() - timing_inicio
        logger.error(f'[CLS][TIMING][ERRO] {timing_total:.3f}s erro inesperado: {e}')
        logger.error(f'[CLS] Erro inesperado no fluxo CLS: {e}')
        return False


def ato_judicial(
    driver: WebDriver,
    conclusao_tipo: Optional[str] = None,
    modelo_nome: Optional[str] = None,
    prazo: Optional[Union[str, int]] = None,
    marcar_pec: Optional[bool] = None,
    movimento: Optional[str] = None,
    gigs: Optional[Any] = None,
    marcar_primeiro_destinatario: Optional[bool] = None,
    debug: bool = False,
    sigilo: Optional[str] = None,
    descricao: Optional[str] = None,
    perito: bool = False,
    Assinar: bool = False,
    coleta_conteudo: Optional[Callable] = None,
    inserir_conteudo: Optional[Callable] = None,
    intimar: Optional[bool] = None,
    **kwargs: Any
) -> Tuple[bool, bool]:
    '''
    Fluxo generalizado para qualquer ato judicial, seguindo a ordem:
    0. Coleta de conteúdo parametrizável (PRIMEIRO PASSO - na aba /detalhe)
    1. Modelo (fluxo_cls)
    2. Descrição
    3. Sigilo
    4. Intimar
    5. PEC
    6. Prazo
    7. Movimento
    8. Assinar
    9. Função extra de sigilo (NOTA: não executada aqui, deve ser feita externamente)

    NOVO COMPORTAMENTO DE SIGILO:
    - A função visibilidade_sigilosos não é mais executada automaticamente
    - Deve ser executada externamente após fechar a aba e estar na URL /detalhe
    - Use executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado)

    :return: (sucesso: bool, sigilo_ativado: bool)
    '''
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    # === TIMING: INÍCIO ===
    timing_inicio = time.time()
    logger.info('[ATO][TIMING][INICIO] conclusao_tipo={} modelo_nome={}'.format(conclusao_tipo, modelo_nome))

    try:
        # 0. PRIMEIRO: Executar coleta de conteúdo parametrizável na aba /detalhe (se especificado)
        if coleta_conteudo:
            logger.info('[ATO][COLETA] Executando coleta de conteúdo parametrizável ANTES do fluxo principal...')
            try:
                # Verifica se está na aba /detalhe
                current_url = driver.current_url
                if '/detalhe' not in current_url:
                    logger.warning(f'[ATO][COLETA][WARN] URL atual não contém /detalhe: {current_url}')
                    logger.warning('[ATO][COLETA][WARN] Coleta deve ser executada na aba /detalhe')

                # Executa a coleta
                executar_coleta_parametrizavel(driver, coleta_conteudo)
                logger.info('[ATO][COLETA]  Coleta de conteúdo parametrizável concluída')
            except Exception as e:
                logger.error(f'[ATO][COLETA]  Erro na coleta de conteúdo: {e}')
                return False, False

        # 1. MODELO: Executar fluxo_cls se modelo_nome especificado
        if modelo_nome:
            logger.info(f'[ATO][MODELO] Iniciando fluxo CLS com modelo: {modelo_nome}')
            timing_fluxo_cls_inicio = time.time()
            if not fluxo_cls(driver, conclusao_tipo or 'decisão'):
                logger.error('[ATO][MODELO]  Falha no fluxo CLS')
                timing_total = time.time() - timing_inicio
                logger.info(f'[ATO][TIMING][ERRO] {timing_total:.3f}s falha fluxo CLS')
                return False, False
            timing_fluxo_cls = time.time() - timing_fluxo_cls_inicio
            logger.info(f'[ATO][TIMING][FLUXO_CLS] {timing_fluxo_cls:.3f}s')

            # ===== DESCRIÇÃO (ANTES de inserir modelo para evitar DOM refresh) =====
            if descricao:
                logger.info(f'[ATO][DESCRICAO] Preenchendo descrição: {descricao}')
                try:
                    # Seletor correto: input[aria-label="Descrição"]
                    campo_descricao = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[aria-label="Descrição"]'))
                    )
                    campo_descricao.clear()
                    # Técnica validada no console: value direto + eventos
                    driver.execute_script("""
                        var input = arguments[0];
                        var valor = arguments[1];
                        input.focus();
                        input.value = valor;
                        ['input', 'change', 'keyup'].forEach(function(ev) {
                            input.dispatchEvent(new Event(ev, {bubbles: true}));
                        });
                        input.blur();
                    """, campo_descricao, descricao)
                    time.sleep(0.3)
                    logger.info('[ATO][DESCRICAO]  Descrição preenchida')
                except Exception as e:
                    logger.error(f'[ATO][DESCRICAO]  Erro ao preencher descrição: {e}')
                    # Não interrompe o fluxo por erro na descrição

            # Preencher filtro do modelo (como no jud.py)
            try:
                logger.info(f'[ATO][MODELO] Preenchendo filtro com modelo: {modelo_nome}')
                campo_filtro_modelo = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
                )

                # Preenche o modelo usando JavaScript (como no jud.py)
                driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
                driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, modelo_nome)

                # Dispara eventos (como no jud.py)
                for ev in ['input', 'change', 'keyup']:
                    driver.execute_script('var evt = new Event(arguments[1], {bubbles:true}); arguments[0].dispatchEvent(evt);', campo_filtro_modelo, ev)

                # Simula Enter para aplicar filtro
                campo_filtro_modelo.send_keys(Keys.ENTER)
                logger.info(f'[ATO][MODELO] Modelo "{modelo_nome}" preenchido via JS e ENTER pressionado no filtro.')

                # Aguarda carregamento da tela após filtro (como no jud.py)
                time.sleep(2)

            except Exception as e:
                logger.error(f'[ATO][MODELO] Erro ao preencher filtro do modelo: {e}')
                return False, False

            # Inserir modelo específico - versão baseada no jud.py (simplificada)
            try:
                # O filtro já foi aplicado, nodo-filtrado já está ativo
                # Basta clicar no nodo-filtrado e inserir (como no jud.py)

                # Seleciona o modelo filtrado destacado (fundo amarelo) - como no jud.py
                seletor_item_filtrado = '.nodo-filtrado'
                nodo = aguardar_e_clicar(driver, seletor_item_filtrado, timeout=15)
                if not nodo:
                    logger.error('[ATO][MODELO] Nodo do modelo não encontrado!')
                    return False, False
                logger.info('[ATO][MODELO] Clique em nodo-filtrado realizado!')

                # Aguarda modal de visualização abrir - como no jud.py
                modal_aberto = False
                for tentativa in range(5):
                    try:
                        modal = driver.find_element(By.CSS_SELECTOR, 'pje-dialogo-visualizar-modelo')
                        if modal.is_displayed():
                            modal_aberto = True
                            break
                    except:
                        pass
                    time.sleep(0.5)

                if not modal_aberto:
                    logger.warning('[ATO][MODELO] Modal não abriu, tentando inserir mesmo assim...')

                # Localiza botão inserir - buscar elemento FRESCO para evitar stale element
                # Usa retry loop para lidar com StaleElementReferenceException
                seletor_btn_inserir = 'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button'
                time.sleep(0.5)
                
                btn_inserir = None
                for tentativa in range(5):
                    try:
                        # Buscar elemento fresco a cada tentativa
                        btn_inserir = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_btn_inserir))
                        )
                        break  # Sucesso - sai do loop
                    except (TimeoutException, StaleElementReferenceException):
                        if tentativa < 4:  # Não é a última tentativa
                            time.sleep(0.3)
                            continue
                        else:
                            logger.error('[ATO][MODELO] Botão inserir não encontrado após 5 tentativas!')
                            return False, False

                # Insere modelo com SPACE (como no legado)
                try:
                    btn_inserir.send_keys(Keys.SPACE)
                    logger.info('[ATO][MODELO] ✅ Modelo inserido')
                except StaleElementReferenceException:
                    # Se ficou stale entre encontrar e clicar, tentar uma última vez
                    logger.warning('[ATO][MODELO] Elemento ficou stale, tentando novamente...')
                    btn_inserir = driver.find_element(By.CSS_SELECTOR, seletor_btn_inserir)
                    btn_inserir.send_keys(Keys.SPACE)
                    logger.info('[ATO][MODELO] ✅ Modelo inserido (2ª tentativa)')
                
                time.sleep(1.5)

            except Exception as e:
                logger.error(f'[ATO][MODELO] Erro ao inserir modelo: {e}')
                return False, False

        # ===== INSERIR CONTEÚDO (antes do salvar, como no jud.py) =====
        if inserir_conteudo:
            logger.info('[ATO][INSERIR] Executando inserção de conteúdo...')
            try:
                inserir_conteudo(driver)
                logger.info('[ATO][INSERIR]  Conteúdo inserido')
            except Exception as e:
                logger.error(f'[ATO][INSERIR]  Erro ao inserir conteúdo: {e}')
                return False, False

        # ===== SALVAR IMEDIATAMENTE APÓS INSERÇÃO (como no jud.py) =====
        logger.info('[ATO][SALVAR] Salvando modelo após inserção...')
        try:
            btn_salvar = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "mat-raised-button") and contains(@class, "mat-primary") and contains(., "Salvar") and @aria-label="Salvar"]'))
            )
            safe_click(driver, btn_salvar)
            logger.info('[ATO][SALVAR] ✅ Clique no botão Salvar realizado!')

            # Aguardar transição para aba de destinatários
            time.sleep(1.5)
            logger.info('[ATO][SALVAR] Aguardando ativação da aba destinatários...')

        except Exception as e:
            logger.error(f'[ATO][SALVAR] ❌ Botão Salvar não encontrado ou não clicável: {e}')
            return False, False

        # ===== ABA DESTINATÁRIOS - PRAZOS =====
        # Verificar intimar_ativado (como no legado)
        intimar_ativado = True if intimar is None else str(intimar).lower() in ("sim", "true", "1")

        # Se intimar_ativado for False, desativa o toggle de intimações (comportamento do legado)
        if not intimar_ativado:
            logger.info('[ATO][INTIMAR] Desativando intimações automáticas...')
            try:
                guia_intimacoes = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-editor-lateral div[aria-posinset="1"]'))
                )
                if guia_intimacoes.get_attribute('aria-selected') == "false":
                    guia_intimacoes.click()
                    time.sleep(0.5)

                toggle_intimar = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-intimacao-automatica label.mat-slide-toggle-label'))
                )
                parent_toggle = toggle_intimar.find_element(By.XPATH, '..')
                if 'mat-checked' in parent_toggle.get_attribute('class'):
                    toggle_intimar.click()
                    logger.info('[ATO][INTIMAR] Toggle "Intimar?" desativado.')
                else:
                    logger.info('[ATO][INTIMAR] Toggle "Intimar?" já estava desativado.')
            except Exception as e:
                logger.error(f'[ATO][INTIMAR] Erro ao desativar intimações: {e}')

        if prazo is not None and intimar_ativado:
            logger.info(f'[ATO][PRAZO] Preenchendo prazos: {prazo} (apenas_primeiro={marcar_primeiro_destinatario})')
            try:
                if not preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=marcar_primeiro_destinatario, perito=perito):
                    logger.error('[ATO][PRAZO]  Falha ao preencher prazos')
                    return False, False
                
                # Remover overlays que possam bloquear
                driver.execute_script("""
                    const overlays = document.querySelectorAll('.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-pane');
                    overlays.forEach(overlay => {
                        if (overlay.style) overlay.style.display = 'none';
                    });
                    const snackbars = document.querySelectorAll('snack-bar-container, simple-snack-bar');
                    snackbars.forEach(snack => {
                        if (snack.style) snack.style.display = 'none';
                    });
                    document.body.style.overflow = 'visible';
                """)
                
                # Gravar prazos (usar safe_click_no_scroll em vez de scrollIntoView + click)
                logger.info('[ATO][PRAZO] Gravando prazos...')
                btn_gravar_prazo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Gravar'] and contains(@class, 'mat-raised-button') and not(contains(@aria-label, 'movimentos'))]"))
                )
                
                if safe_click_no_scroll(driver, btn_gravar_prazo, log=False):
                    logger.info('[ATO][PRAZO] Gravado via safe_click_no_scroll')
                else:
                    logger.warning('[ATO][PRAZO] Falha em safe_click_no_scroll, tentando .click()')
                    btn_gravar_prazo.click()
                
                time.sleep(1)
                logger.info('[ATO][PRAZO]  Prazos concluídos')
            except Exception as e:
                logger.error(f'[ATO][PRAZO]  Erro ao preencher prazos: {e}')
                return False, False

        # ===== ABA DESTINATÁRIOS - PEC =====
        if marcar_pec is not None:
            # Converter para booleano: "sim" / "nao" / True / False
            marcar_pec_bool = str(marcar_pec).lower() in ("sim", "true", "1", "yes")
            logger.info(f'[ATO][PEC] Parâmetro: marcar_pec={marcar_pec!r}')
            try:
                pec_checkbox = None
                pec_input = None
                
                # Tentar múltiplas formas de encontrar o checkbox PEC (fallbacks)
                try:
                    pec_checkbox = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-checkbox[aria-label="Enviar para PEC"]'))
                    )
                    pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                except:
                    try:
                        pec_checkbox = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.checkbox-pec mat-checkbox'))
                        )
                        pec_input = pec_checkbox.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                    except:
                        pec_input = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Enviar para PEC"]'))
                        )
                        pec_checkbox = pec_input.find_element(By.XPATH, './ancestor::mat-checkbox[1]')
                
                if not pec_checkbox or not pec_input:
                    raise Exception("Checkbox PEC não encontrado")
                
                # Verificar estado atual
                is_checked = False
                try:
                    if (pec_input.get_attribute('aria-checked') == 'true' or 
                        pec_input.get_attribute('checked') == 'true' or 
                        pec_input.is_selected() or 
                        'mat-checkbox-checked' in pec_checkbox.get_attribute('class')):
                        is_checked = True
                except:
                    is_checked = False
                
                logger.info(f'[ATO][PEC] Estado: {"marcado" if is_checked else "desmarcado"} → esperado: {"marcar" if marcar_pec_bool else "desmarcar"}')
                
                # Clicar checkbox PEC (usar safe_click_no_scroll em vez de scrollIntoView + click)
                if marcar_pec_bool != is_checked:
                    # Tentar clicar no label, se não funcionar clicar no checkbox
                    try:
                        label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-layout')
                        safe_click_no_scroll(driver, label, log=False)
                    except:
                        safe_click_no_scroll(driver, pec_checkbox, log=False)
                        driver.execute_script('arguments[0].click();', pec_checkbox)
                    
                    time.sleep(0.3)
                    logger.info(f'[ATO][PEC] ✅ {"Marcado" if marcar_pec_bool else "Desmarcado"}')
                else:
                    logger.info(f'[ATO][PEC] ✓ Já está conforme esperado')
                    
            except Exception as e:
                logger.error(f'[ATO][PEC] ❌ {e}')
                # Não interrompe o fluxo

        # Após manipular PEC, gravar localmente antes de ir para Movimentos
        try:
            logger.info('[ATO][PEC] Tentando gravar alterações de PEC antes do movimento...')
            # seletor direto para o botão mostrado pelo usuário
            btn_gravar_pec = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Gravar a intimação/notificação"]'))
            )
            if safe_click_no_scroll(driver, btn_gravar_pec, log=False):
                logger.info('[ATO][PEC] ✅ Clique em Gravar (intimação) realizado')
            else:
                try:
                    btn_gravar_pec.click()
                    logger.info('[ATO][PEC] ✅ Clique padrão em Gravar realizado')
                except Exception as e:
                    logger.debug(f'[ATO][PEC] Falha ao clicar em Gravar via .click(): {e}')
            time.sleep(0.8)
        except Exception as e:
            logger.debug(f'[ATO][PEC] Botão Gravar não encontrado/acionável: {e}')

        # ===== ABA DESTINATÁRIOS - MOVIMENTO =====
        if movimento:
            logger.info(f'[ATO][MOVIMENTO] Selecionando movimento: {movimento}')
            try:
                # Movimento multi-estágio (combobox) vs simples (checkbox)
                if '/' in movimento or '-' in movimento:
                    # Fluxo combobox de dois estágios
                    if not selecionar_movimento_auto(driver, movimento):
                        logger.error(f'[ATO][MOVIMENTO]  Movimento não encontrado: {movimento}')
                        return False, False
                    logger.info('[ATO][MOVIMENTO]  Movimento selecionado via combobox')
                else:
                    # Fluxo checkbox simples (legado)
                    js_mov = f'''
                    (function() {{
                        var tentativas = 0, abaMov = null;
                        while (tentativas < 3 && !abaMov) {{
                            var abas = Array.from(document.querySelectorAll('.mat-tab-label'));
                            abaMov = abas.find(a => a.textContent && a.textContent.normalize('NFD').replace(/[\\W_]/g, '').toLowerCase().includes('movimentos'));
                            if (abaMov && abaMov.getAttribute('aria-selected') !== 'true') {{
                                abaMov.click();
                                break;
                            }}
                            tentativas++;
                        }}
                        
                        setTimeout(function() {{
                            var textoMov = '{movimento}'.trim().toLowerCase().replace(/\\s+/g, ' ');
                            var checkboxes = Array.from(document.querySelectorAll('mat-checkbox.mat-checkbox.movimento'));
                            var selecionado = false;
                            
                            function normalizarTexto(texto) {{
                                return texto.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
                            }}
                            
                            var termoPesquisa = normalizarTexto(textoMov);
                              
                            for (var cb of checkboxes) {{
                                try {{
                                    var label = cb.querySelector('label.mat-checkbox-layout .mat-checkbox-label');
                                    var labelText = label && label.textContent ? label.textContent : '';
                                    var labelNorm = labelText.trim().toLowerCase().replace(/\\s+/g, ' ');
                                    var labelSemAcento = normalizarTexto(labelText);
                                    
                                    var encontrado = labelNorm.includes(textoMov) || 
                                                    labelSemAcento.includes(termoPesquisa) ||
                                                    (textoMov === 'frustrada' && (labelSemAcento.includes('execucao frustrada') || labelSemAcento.includes('276'))) ||
                                                    (textoMov.match(/^\\d+$/) && labelText.includes('(' + textoMov + ')'));
                                    
                                    if (encontrado) {{
                                        var input = cb.querySelector('input[type="checkbox"]');
                                        if (input && !input.checked) {{
                                            var inner = cb.querySelector('.mat-checkbox-inner-container');
                                            if(inner) {{
                                                inner.click();
                                            }} else {{
                                                input.click();
                                            }}
                                        }}
                                        window.selecionadoMovimento = true;
                                        window.labelSelecionadoMovimento = labelText;
                                        selecionado = true;
                                        break;
                                    }}
                                }} catch (e) {{
                                    console.warn('[ATO][MOVIMENTO] Erro ao processar checkbox:', e);
                                }}
                            }}
                            
                            if (!selecionado) {{
                                console.warn('[ATO][MOVIMENTO] Movimento não encontrado');
                                window.selecionadoMovimento = false;
                            }} else {{
                                console.log('[ATO][MOVIMENTO] Movimento marcado');
                            }}
                        }}, 800);
                    }})();
                    '''
                    driver.execute_script(js_mov)
                    time.sleep(1.5)
                    
                    # Verificar se foi selecionado
                    selecionado = driver.execute_script('return window.selecionadoMovimento;')
                    if not selecionado:
                        logger.error(f'[ATO][MOVIMENTO]  Movimento não encontrado: {movimento}')
                        return False, False
                    label_mov = driver.execute_script('return window.labelSelecionadoMovimento;')
                    logger.info(f'[ATO][MOVIMENTO]  Checkbox marcado: {label_mov}')
                
                # Gravar movimentos (botão "Gravar os movimentos a serem lançados")
                logger.info('[ATO][MOVIMENTO] Gravando movimento...')
                btn_gravar_mov = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Gravar os movimentos a serem lançados']"))
                )
                btn_gravar_mov.click()
                time.sleep(1.5)
                
                # Confirmar com "Sim"
                logger.info('[ATO][MOVIMENTO] Confirmando...')
                btn_sim = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mat-button') and contains(@class, 'mat-primary') and .//span[text()='Sim']]"))
                )
                btn_sim.click()
                time.sleep(1)
                logger.info('[ATO][MOVIMENTO]  Movimento gravado e confirmado')
                
            except Exception as e:
                logger.error(f'[ATO][MOVIMENTO]  Erro ao selecionar movimento: {e}')
                return False, False

        # ===== SIGILO/INTIMAR (se necessário na aba destinatários) =====
        sigilo_ativado = False
        if sigilo:
            logger.info('[ATO][SIGILO] Ativando sigilo...')
            try:
                checkbox_sigilo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-checkbox#sigilo'))
                )
                if not checkbox_sigilo.is_selected():
                    checkbox_sigilo.click()
                    sigilo_ativado = True
                logger.info('[ATO][SIGILO]  Sigilo ativado')
            except Exception as e:
                logger.error(f'[ATO][SIGILO]  Erro ao ativar sigilo: {e}')
                # Não interrompe o fluxo

        if intimar_ativado:
            logger.info('[ATO][INTIMAR] Marcando intimação...')
            try:
                checkbox_intimar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-checkbox#intimar'))
                )
                if not checkbox_intimar.is_selected():
                    checkbox_intimar.click()
                logger.info('[ATO][INTIMAR]  Intimação marcada')
            except Exception as e:
                logger.error(f'[ATO][INTIMAR]  Erro ao marcar intimação: {e}')
                # Não interrompe o fluxo

        # ===== GRAVAR/SALVAR FINAL =====
        # Se tem movimento, o SALVAR é feito após confirmar movimento
        # Se não tem movimento, precisa GRAVAR as configurações (prazo/PEC/etc) e depois SALVAR
        if movimento:
            # Movimento já grava automaticamente, só precisa SALVAR
            logger.info('[ATO][SALVAR] Salvando ato após movimento...')
            try:
                btn_salvar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Salvar'][color='primary']"))
                )
                btn_salvar.click()
                logger.info('[ATO][SALVAR] ✅ Ato salvo')
                time.sleep(1.5)
                # Verifica e reaplica sigilo/PEC caso o save tenha re-renderizado a aba
                try:
                    changed = _verificar_reaplicar_sigilo_pec()
                    if changed:
                        logger.info('[ATO][SALVAR] Mudança detectada após reaplicar; salvando novamente...')
                        try:
                            btn_salvar2 = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Salvar'][color='primary']"))
                            )
                            btn_salvar2.click()
                            time.sleep(1)
                        except Exception as e:
                            logger.debug(f'[ATO][SALVAR] Não foi possível salvar novamente: {e}')
                except Exception:
                    pass
            except Exception as e:
                logger.error(f'[ATO][SALVAR] ❌ {e}')
                return False, False
        else:
            # Sem movimento: GRAVAR configurações e depois SALVAR
            logger.info('[ATO][GRAVAR] Gravando configurações...')
            try:
                btn_gravar = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Gravar a intimação/notificação"]'))
                )
                btn_gravar.click()
                logger.info('[ATO][GRAVAR] ✅ Gravado')
                time.sleep(1)
            except Exception as e:
                logger.error(f'[ATO][GRAVAR] ❌ {e}')
                return False, False

            # Após gravar localmente, revalidar/reaplicar sigilo/PEC antes do save final
            try:
                changed = _verificar_reaplicar_sigilo_pec()
                if changed:
                    logger.info('[ATO][GRAVAR] Mudança detectada após reaplicar; executando save final...')
                    try:
                        btn_salvar_final = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Salvar'][color='primary']"))
                        )
                        btn_salvar_final.click()
                        time.sleep(1)
                    except Exception as e:
                        logger.debug(f'[ATO][GRAVAR] Não foi possível executar save final: {e}')
            except Exception:
                pass

        # 8. ASSINAR: Clicar em assinar se especificado
        if Assinar:
            logger.info('[ATO][ASSINAR] Clicando em assinar...')
            try:
                btn_assinar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button#assinar'))
                )
                btn_assinar.click()
                logger.info('[ATO][ASSINAR]  Assinar clicado')
            except Exception as e:
                logger.error(f'[ATO][ASSINAR]  Erro ao clicar em assinar: {e}')
                return False, False

        logger.info('=' * 60)
        logger.info('ATO JUDICIAL - CONCLUÍDO COM SUCESSO')
        logger.info('=' * 60)
        timing_total = time.time() - timing_inicio
        logger.info(f'[ATO][TIMING][SUCESSO] {timing_total:.3f}s (fluxo completo)')
        return True, sigilo_ativado

    except Exception as e:
        timing_total = time.time() - timing_inicio
        logger.error(f'[ATO][TIMING][ERRO] {timing_total:.3f}s erro inesperado: {e}')
        logger.error(f'[ATO]  Erro inesperado no ato judicial: {e}')
        return False, False


def make_ato_wrapper(
    conclusao_tipo: str,
    modelo_nome: str,
    prazo: Optional[Union[str, int]] = None,
    marcar_pec: Optional[bool] = None,
    movimento: Optional[str] = None,
    gigs: Optional[Any] = None,
    marcar_primeiro_destinatario: Optional[bool] = None,
    descricao: Optional[str] = None,
    sigilo: Optional[str] = None,
    perito: bool = False,
    Assinar: bool = False,
    coleta_conteudo: Optional[Callable] = None,
    inserir_conteudo: Optional[Callable] = None,
    intimar: Optional[bool] = None
) -> Callable[[WebDriver, Any], Tuple[bool, bool]]:
    '''
    Factory function que cria um wrapper para ato_judicial com parâmetros pré-definidos.
    Permite criar funções especializadas como aaDespacho, aaDecisao, etc.
    
    Returns:
        function: Wrapper para ato_judicial com parâmetros fixos
    '''
    def wrapper(driver, **kwargs):
        '''
        Wrapper para ato_judicial com parâmetros pré-configurados.
        Aceita kwargs para sobrescrever parâmetros padrão.
        '''
        # Combinar parâmetros padrão com kwargs
        params = {
            'conclusao_tipo': conclusao_tipo,
            'modelo_nome': modelo_nome,
            'prazo': prazo,
            'marcar_pec': marcar_pec,
            'movimento': movimento,
            'gigs': gigs,
            'marcar_primeiro_destinatario': marcar_primeiro_destinatario,
            'descricao': descricao,
            'sigilo': sigilo,
            'perito': perito,
            'Assinar': Assinar,
            'coleta_conteudo': coleta_conteudo,
            'inserir_conteudo': inserir_conteudo,
            'intimar': intimar
        }
        params.update(kwargs)  # kwargs sobrescrevem padrões

        # Chamar ato_judicial com os parâmetros
        return ato_judicial(driver, **params)

    # Definir nome da função para debugging
    modelo_part = modelo_nome.lower().replace(" ", "_") if modelo_nome else "sem_modelo"
    wrapper.__name__ = f'ato_{conclusao_tipo.lower()}_{modelo_part}'
    return wrapper
