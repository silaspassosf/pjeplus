import logging
logger = logging.getLogger(__name__)

"""
Utilitários e funções auxiliares para automação de processos.
Contém funções de visibilidade de sigilosos e controle de sigilo.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def esperar_insercao_modelo(driver, timeout=8000):
    """
    Aguarda a inserção do modelo monitorando a aparição do dialog e snackbar.
    Versão simplificada baseada nos padrões do a.py - usa MutationObserver + setTimeout.
    """
    try:
        # JavaScript simplificado baseado no padrão do a.py
        js_monitor = f"""
        var callback = arguments[arguments.length - 1];
        console.log('maisPje: esperar_insercao_modelo() - iniciando com timeout {timeout}ms');

        var startTime = Date.now();
        var timeoutId = setTimeout(function() {{
            console.log('maisPje: esperar_insercao_modelo() - timeout esgotado após ' + (Date.now() - startTime) + ' ms');
            callback(false);
        }}, {timeout});

        function verificarInsercao() {{
            try {{
                var dialog = document.querySelector('pje-dialogo-visualizar-modelo');
                var dialogVisivel = dialog && dialog.offsetParent !== null;

                var snackbar = document.querySelector('simple-snack-bar');
                var snackbarVisivel = snackbar && snackbar.offsetParent !== null;

                if (dialogVisivel && snackbarVisivel) {{
                    console.log('maisPje: esperar_insercao_modelo() - inserção confirmada');
                    clearTimeout(timeoutId);
                    callback(true);
                    return true;
                }}
            }} catch (e) {{
                console.warn('maisPje: esperar_insercao_modelo() - erro na verificação:', e);
            }}
            return false;
        }}

        if (!verificarInsercao()) {{
            var observer = new MutationObserver(function() {{
                if (verificarInsercao()) {{
                    observer.disconnect();
                    clearInterval(checkInterval);
                }}
            }});

            observer.observe(document.body, {{
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['style', 'class']
            }});

            var checkInterval = setInterval(function() {{
                if (verificarInsercao()) {{
                    clearInterval(checkInterval);
                    observer.disconnect();
                }}
            }}, 500);

            setTimeout(function() {{
                clearInterval(checkInterval);
                observer.disconnect();
            }}, {timeout});
        }}
        """

        # Executa o JavaScript e aguarda resultado
        resultado = driver.execute_async_script(js_monitor)

        if resultado:
            pass
        return resultado

    except Exception as e:
        logger.error(f'[ATO][ESPERAR_MODELO][ERRO] Falha no monitoramento: {e}')
        return False


def visibilidade_sigilosos(driver, polo='ativo', log=False):
    """
    Aplica visibilidade a documentos sigilosos anexados automaticamente.
    NOVO: Automaticamente troca para aba /detalhe e atualiza a página com driver.refresh().
    Sequência: Tab switch → refresh → Múltipla seleção → Primeira checkbox → Visibilidade → Salvar
    
    :param driver: A instância do WebDriver.
    :param polo: 'ativo', 'passivo', 'ambos'. Define qual polo será selecionado.
    :param log: Ativa logs detalhados.
    :return: True se executou com sucesso, False caso contrário.
    """
    try:
        # Preferir a aba cuja URL contenha '/detalhe'. Se não existir, tentar a segunda aba
        current_url = driver.current_url
        if len(driver.window_handles) > 1:
            detalhe_handle = None
            for handle in driver.window_handles:
                try:
                    driver.switch_to.window(handle)
                    url = driver.current_url
                    if '/detalhe' in url:
                        detalhe_handle = handle
                        break
                except Exception:
                    continue

            if detalhe_handle:
                driver.switch_to.window(detalhe_handle)
                current_url = driver.current_url
            else:
                # Se não encontrou, tentar a segunda aba (índice 1) e aguardar até que sua URL contenha /detalhe
                try:
                    segundo = driver.window_handles[1]
                    driver.switch_to.window(segundo)
                    waited = 0
                    while '/detalhe' not in driver.current_url and waited < 10:
                        time.sleep(1)
                        waited += 1
                    current_url = driver.current_url
                except Exception as e:
                    pass
        else:
            pass
        try:
            driver.refresh()
            time.sleep(3)  # Aguarda a página recarregar
        except Exception as refresh_err:
            if log:
                logger.error(f"[VISIBILIDADE][F5][ERRO] Falha no refresh: {refresh_err}")
            return False
        
        # Aguarda a página estar completamente carregada
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
        try:
            btn_multi = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Exibir múltipla seleção."]')
            btn_multi.click()
            time.sleep(0.5)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE][ERRO] Falha ao ativar múltipla seleção: {e}')
            return False
            
        # 2. Clica na primeira checkbox encontrada na timeline
        try:
            primeira_checkbox = driver.find_element(By.CSS_SELECTOR, 'ul.pje-timeline mat-card mat-checkbox label')
            primeira_checkbox.click()
            time.sleep(0.5)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE][ERRO] Falha ao marcar primeira checkbox: {e}')
            return False
            
        # 3. Clica no botão de visibilidade
        try:
            btn_visibilidade = driver.find_element(By.CSS_SELECTOR, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]')
            btn_visibilidade.click()
            time.sleep(1)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE][ERRO] Falha ao clicar no botão de visibilidade: {e}')
            return False
            
        # 4. No modal, seleciona o polo desejado
        try:
            if polo == 'ativo':
                icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-ativo')
                for icone in icones:
                    linha = icone.find_element(By.XPATH, './../../..')
                    label = linha.find_element(By.CSS_SELECTOR, 'label')
                    label.click()
            elif polo == 'passivo':
                icones = driver.find_elements(By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-passivo')
                for icone in icones:
                    linha = icone.find_element(By.XPATH, './../../..')
                    label = linha.find_element(By.CSS_SELECTOR, 'label')
                    label.click()
            elif polo == 'ambos':
                # Marca todos
                btn_todos = driver.find_element(By.CSS_SELECTOR, 'th button')
                btn_todos.click()
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE][ERRO] Falha ao selecionar polo: {e}')
            return False
            
        # 5. Confirma no botão Salvar
        try:
            btn_salvar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(),"Salvar")]]'))
            )
            btn_salvar.click()
            time.sleep(1)
        except Exception as e:
            if log:
                logger.error(f'[VISIBILIDADE][ERRO] Falha ao salvar configuração: {e}')
            return False
            
        # 6. Oculta múltipla seleção
        try:
            btn_ocultar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Ocultar múltipla seleção."]')
            btn_ocultar.click()
        except:
            pass
        return True
        
    except Exception as e:
        if log:
            logger.error(f'[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade: {e}')
        return False



def executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=False):
    """
    Executa a função visibilidade_sigilosos se sigilo foi ativado.
    NOVO: Atualiza a página com F5 antes de executar as ações de visibilidade.
    Deve ser chamada na aba /detalhe.
    
    :param driver: WebDriver
    :param sigilo_ativado: Boolean indicando se sigilo foi ativado
    :param debug: Boolean para logs detalhados
    :return: True se executou com sucesso ou não era necessário, False se falhou
    """
    if not sigilo_ativado:
        return True
    
    try:
        # Verifica se está na URL correta (/detalhe)
        current_url = driver.current_url
        if '/detalhe' not in current_url:
            logger.warning(f'[VISIBILIDADE][WARN] URL atual não contém /detalhe: {current_url}')
            logger.warning('[VISIBILIDADE][WARN] A função visibilidade_sigilosos deve ser executada na URL /detalhe')
        
        # NOVO: Atualiza a página com F5 como primeira ação
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.F5)
        
        # Aguarda a página recarregar
        time.sleep(3)
        
        # Usa a função local que já tem tab switching e F5
        resultado = visibilidade_sigilosos(driver, log=debug)
        
        if resultado:
            return True
        else:
            logger.error('[VISIBILIDADE][ERRO] ✗ Função visibilidade_sigilosos falhou.')
            return False
            
    except Exception as e:
        logger.error(f'[VISIBILIDADE][ERRO] ✗ Exceção ao executar visibilidade_sigilosos: {e}')
        import traceback
        traceback.print_exc()
        return False


def preparar_campo_filtro_modelo(driver, log=False):
    """
    Foca e limpa o campo de filtro de modelos na tela /minutar.
    Retorna True se conseguiu preparar o campo, False caso contrário.
    """
    try:
        campo_filtro_modelo = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
        )
        driver.execute_script('arguments[0].removeAttribute("disabled"); arguments[0].removeAttribute("readonly");', campo_filtro_modelo)
        driver.execute_script('arguments[0].focus();', campo_filtro_modelo)
        driver.execute_script('arguments[0].value = arguments[1];', campo_filtro_modelo, "")
        driver.execute_script(
            'var el=arguments[0]; el.dispatchEvent(new Event("input", {bubbles:true})); el.dispatchEvent(new Event("keyup", {bubbles:true}));',
            campo_filtro_modelo
        )
        time.sleep(0.3)
        return True
    except Exception as e:
        if log:
            logger.error(f'[CLS][MODELO][ERRO] Falha ao acessar/interagir com o campo de filtro de modelos: {e}')
        return False
