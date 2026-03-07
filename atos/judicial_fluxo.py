"""
judicial_fluxo.py - Fluxos principais de atos judiciais
======================================================

Módulo principal com os fluxos de alto nível para atos judiciais,
usando os módulos especializados para navegação, conclusão, modelos,
prazos e bloqueios.
"""

from Fix.core import aguardar_e_clicar, esperar_elemento, safe_click, logger, esperar_url_conter, preencher_multiplos_campos
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
    try:
        logger.info('=' * 60)
        logger.info('FLUXO CLS - INICIANDO')
        logger.info('=' * 60)

        # ===== VERIFICAÇÃO INICIAL: Estados especiais =====
        estado_atual = verificar_estado_atual(driver)
        if estado_atual == 'assinar':
            logger.info('[CLS]  Processo já está em /assinar - ato cumprido')
            return True
        elif estado_atual == 'minutar':
            logger.info('[CLS]  Já estamos em /minutar - focando no campo')
            focar_campo_minutar_se_necessario(driver)
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
            sucesso, ja_em_minutar = abrir_tarefa_processo(driver)
            if not sucesso:
                logger.error('[CLS] Falha ao abrir tarefa do processo')
                return False
            
            # Se já está em /minutar após abrir tarefa, pular navegação e transição
            if ja_em_minutar:
                logger.info('[CLS] ✅ Já em /minutar após abrir tarefa - fluxo CLS concluído')
                return True

        # ===== PASSO 2: LIMPAR OVERLAYS =====
        logger.info('[CLS] Passo 2: Limpando overlays...')
        limpar_overlays(driver)

        # ===== PASSO 3: NAVEGAR PARA CONCLUSÃO (se necessário) =====
        if not ja_em_conclusao:
            logger.info('[CLS] Passo 3: Navegando para conclusão...')
            if not navegar_para_conclusao(driver):
                logger.error('[CLS] Falha ao navegar para conclusão')
                return False

        # ===== PASSO 4: ESCOLHER TIPO DE CONCLUSÃO =====
        logger.info(f'[CLS] Passo 4: Escolhendo tipo de conclusão: {conclusao_tipo}')
        if not escolher_tipo_conclusao(driver, conclusao_tipo):
            logger.error(f'[CLS] Falha ao escolher tipo de conclusão: {conclusao_tipo}')
            return False

        # ===== PASSO 5: AGUARDAR TRANSIÇÃO PARA MINUTAR =====
        logger.info('[CLS] Passo 5: Aguardando transição para minutar...')
        if not aguardar_transicao_minutar(driver):
            logger.error('[CLS] Falha na transição para minutar')
            return False

        # ===== PASSO 6: PREPARAR CAMPO DE MINUTAR =====
        logger.info('[CLS] Passo 6: Preparando campo de minutar...')
        if not preparar_campo_minutar(driver):
            logger.error('[CLS] Falha ao preparar campo de minutar')
            return False

        logger.info('=' * 60)
        logger.info('FLUXO CLS - CONCLUÍDO COM SUCESSO')
        logger.info('=' * 60)
        return True

    except Exception as e:
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
            if not fluxo_cls(driver, conclusao_tipo or 'decisão'):
                logger.error('[ATO][MODELO]  Falha no fluxo CLS')
                return False, False

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
                
                # GRAVAR prazos (botão "Gravar" da aba destinatários)
                logger.info('[ATO][PRAZO] Gravando prazos...')
                btn_gravar_prazo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Gravar'] and contains(@class, 'mat-raised-button') and not(contains(@aria-label, 'movimentos'))]"))
                )
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_gravar_prazo)
                time.sleep(0.5)
                
                try:
                    driver.execute_script("arguments[0].click();", btn_gravar_prazo)
                    logger.info('[ATO][PRAZO] Gravado via JS')
                except Exception:
                    btn_gravar_prazo.click()
                    logger.info('[ATO][PRAZO] Gravado via Selenium')
                
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
                # Buscar mat-checkbox (padrão do gigs-plugin.js)
                pec_checkbox = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-checkbox[aria-label="Enviar para PEC"]'))
                )
                
                # Verificar se está marcado pela classe (mesmo padrão do gigs-plugin.js)
                is_checked = 'mat-checkbox-checked' in pec_checkbox.get_attribute('class')
                
                logger.info(f'[ATO][PEC] Estado: {"marcado" if is_checked else "desmarcado"} → esperado: {"marcar" if marcar_pec_bool else "desmarcar"}')
                
                # Clicar no label se estado é diferente do esperado (padrão do gigs-plugin.js)
                if marcar_pec_bool != is_checked:
                    label = pec_checkbox.find_element(By.CSS_SELECTOR, 'label.mat-checkbox-label')
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', label)
                    time.sleep(0.2)
                    driver.execute_script('arguments[0].click();', label)
                    time.sleep(0.3)
                    
                    # Verificar novo estado
                    novo_checked = 'mat-checkbox-checked' in pec_checkbox.get_attribute('class')
                    logger.info(f'[ATO][PEC] ✅ {"Marcado" if novo_checked else "Desmarcado"}')
                else:
                    logger.info(f'[ATO][PEC] ✓ Já está conforme esperado')
                    
            except Exception as e:
                logger.error(f'[ATO][PEC] ❌ {e}')
                # Não interrompe o fluxo

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

        if intimar:
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
        return True, sigilo_ativado

    except Exception as e:
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
