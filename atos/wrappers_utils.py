import logging
logger = logging.getLogger(__name__)

"""
Utilitários e funções auxiliares para automação de processos.
Contém funções de visibilidade de sigilosos e controle de sigilo.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from Fix.utils import aguardar_pagina_carregar
from Fix.core import aguardar_renderizacao_nativa


def esperar_insercao_modelo(driver, timeout=8000):
    """
    Aguarda a inserção do modelo monitorando o DOM via MutationObserver.
    Implementação baseada no legado: observa dialog de visualização e snackbar
    e retorna True se detectados dentro do timeout, False caso contrário.
    """
    try:
        timeout_ms = int(timeout)
        logger.info(f'[MODELO] Monitorando inserção do modelo por {timeout_ms}ms')
        js = f"""
var callback = arguments[arguments.length - 1];
(function() {{
    console.log('maisPje: esperar_insercao_modelo() - iniciando com timeout {timeout_ms}ms');
    var startTime = Date.now();
    var timeoutId = setTimeout(function() {{
        console.log('maisPje: esperar_insercao_modelo() - timeout esgotado após ' + (Date.now() - startTime) + ' ms');
        try {{ callback(false); }} catch(e){{}}
    }}, {timeout_ms});

    function verificarInsercao() {{
        try {{
            var dialog = document.querySelector('pje-dialogo-visualizar-modelo');
            var dialogVisivel = dialog && (dialog.offsetParent !== null);
            var snackbar = document.querySelector('simple-snack-bar');
            var snackbarVisivel = snackbar && (snackbar.offsetParent !== null);
            if (dialogVisivel && snackbarVisivel) {{
                console.log('maisPje: esperar_insercao_modelo() - inserção confirmada');
                clearTimeout(timeoutId);
                try {{ callback(true); }} catch(e){{}}
                return true;
            }}
        }} catch (e) {{ console.warn('maisPje: esperar_insercao_modelo() - erro na verificação:', e); }}
        return false;
    }}

    if (!verificarInsercao()) {{
        var observer = new MutationObserver(function(mutations) {{
            if (verificarInsercao()) {{
                try {{ observer.disconnect(); }} catch(e){{}}
            }}
        }});

        observer.observe(document.body, {{ childList: true, subtree: true, attributes: true, attributeFilter: ['style','class'] }});

        var checkInterval = setInterval(function() {{
            if (verificarInsercao()) {{
                clearInterval(checkInterval);
                try {{ observer.disconnect(); }} catch(e){{}}
            }}
        }}, 500);

        setTimeout(function() {{
            clearInterval(checkInterval);
            try {{ observer.disconnect(); }} catch(e){{}}
        }}, {timeout_ms});
    }}
}})();
"""

        try:
            resultado = driver.execute_async_script(js)
            if resultado:
                logger.info('[MODELO] Inserção confirmada via observer')
                return True
            else:
                logger.warning(f'[MODELO] Timeout aguardando inserção ({timeout_ms}ms)')
                return False
        except WebDriverException as e:
            logger.warning(f'[MODELO] Falha ao executar monitor JS: {e}')
            return False
        except Exception as e:
            logger.warning(f'[MODELO] Falha ao executar monitor JS: {e}')
            return False
    except Exception as e:
        logger.exception(f'[MODELO] Exceção em esperar_insercao_modelo: {e}')
        return False



def _trocar_para_aba_detalhe(driver, log):
    """Tenta trocar para a aba /detalhe. Se não encontrar, tenta restaurá-la na primeira aba."""
    current_url = driver.current_url
    
    # 1. Procurar se alguma aba aberta já é a /detalhe
    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            if '/detalhe' in driver.current_url:
                return driver.current_url
        except Exception:
            continue
            
    # 2. Se não encontrou nenhuma aba /detalhe (ex: foi consumida por uma transição nativa)
    try:
        driver.switch_to.window(driver.window_handles[0])
        url_atual = driver.current_url
        if '/processo/' in url_atual:
            import re
            match = re.search(r'/processo/(\d+)', url_atual)
            if match:
                id_proc = match.group(1)
                base_match = re.search(r'^(https?://[^/]+/pjekz)', url_atual)
                if base_match:
                    base_url = base_match.group(1)
                    nova_url = f"{base_url}/processo/{id_proc}/detalhe"
                    logger.info(f"[VISIBILIDADE] Aba /detalhe ausente. Restaurando navegação para: {nova_url}")
                    driver.get(nova_url)
                    return driver.current_url
    except Exception as e:
        logger.error(f"[VISIBILIDADE][ERRO] Falha ao tentar restaurar URL de detalhe: {e}")

    return driver.current_url

def _refresh_e_aguardar(driver, log):
    try:
        driver.refresh()
        try:
            aguardar_renderizacao_nativa(driver, 'ul.pje-timeline', modo='aparecer', timeout=15)
        except Exception:
            pass
        return True
    except Exception as refresh_err:
        logger.error(f"[VISIBILIDADE][F5][ERRO] Falha no refresh: {refresh_err}")
        return False

def _ativar_multipla_selecao(driver, log):
    try:
        btn_multi = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Exibir múltipla seleção."]'))
        )
        btn_multi.click()
        aguardar_renderizacao_nativa(driver, 'ul.pje-timeline mat-card mat-checkbox', 'aparecer', 3)
        return True
    except Exception as e:
        logger.error(f'[VISIBILIDADE][ERRO] Falha ao ativar múltipla seleção: {e}')
        return False

def _clicar_primeira_checkbox(driver, log):
    try:
        primeira_checkbox = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'ul.pje-timeline mat-card mat-checkbox label'))
        )
        primeira_checkbox.click()
        aguardar_renderizacao_nativa(driver, 'ul.pje-timeline mat-card mat-checkbox.mat-checkbox-checked', 'aparecer', 3)
        return True
    except Exception as e:
        logger.error(f'[VISIBILIDADE][ERRO] Falha ao marcar primeira checkbox: {e}')
        return False

def _clicar_botao_visibilidade(driver, log):
    try:
        # Novo seletor: button com aria-label="Remover visibilidade para Sigilo" (dentro do commentário)
        # Esta é a seleção de visibilidade após sigilo ser marcado na timeline
        btn_visibilidade = None
        
        # Tenta primeiro o novo seletor (aria-label)
        try:
            btn_visibilidade = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label*="visibilidade para Sigilo"]'))
            )
        except:
            # Fallback: tenta pelo mattooltip antigo
            btn_visibilidade = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]'))
            )
        
        if not btn_visibilidade:
            logger.error('[VISIBILIDADE][ERRO] Botão de visibilidade não encontrado')
            return False
            
        driver.execute_script('arguments[0].scrollIntoView(true);', btn_visibilidade)
        time.sleep(0.3)
        driver.execute_script('arguments[0].click();', btn_visibilidade)
        
        aguardar_renderizacao_nativa(driver, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"]', 'aparecer', 5)
        return True
    except Exception as e:
        logger.error(f'[VISIBILIDADE][ERRO] Falha ao clicar no botão de visibilidade: {e}')
        return False

def _selecionar_polo(driver, polo, log):
    try:
        if polo == 'ativo':
            icones = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-ativo'))
            )
            for icone in icones:
                linha = icone.find_element(By.XPATH, './../../..')
                label = linha.find_element(By.CSS_SELECTOR, 'label')
                label.click()
        elif polo == 'passivo':
            icones = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] i.icone-polo-passivo'))
            )
            for icone in icones:
                linha = icone.find_element(By.XPATH, './../../..')
                label = linha.find_element(By.CSS_SELECTOR, 'label')
                label.click()
        elif polo == 'ambos':
            btn_todos = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'th button'))
            )
            btn_todos.click()
        return True
    except Exception as e:
        logger.error(f'[VISIBILIDADE][ERRO] Falha ao selecionar polo: {e}')
        return False

def _clicar_salvar(driver, log):
    try:
        btn_salvar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(),"Salvar")]]'))
        )
        btn_salvar.click()
        aguardar_renderizacao_nativa(driver, 'simple-snack-bar', 'aparecer', 5)
        return True
    except Exception as e:
        if log:
            logger.error(f'[VISIBILIDADE][ERRO] Falha ao salvar configuração: {e}')
        return False

def _ocultar_multipla_selecao(driver):
    try:
        btn_ocultar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Ocultar múltipla seleção."]')
        btn_ocultar.click()
    except Exception:
        logger.debug('[VISIBILIDADE] Botão ocultar múltipla seleção não encontrado (normal se já oculto)')

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
        current_url = _trocar_para_aba_detalhe(driver, log)
        if not _refresh_e_aguardar(driver, log):
            return False
        if not _ativar_multipla_selecao(driver, log):
            return False
        if not _clicar_primeira_checkbox(driver, log):
            return False
        if not _clicar_botao_visibilidade(driver, log):
            return False
        if not _selecionar_polo(driver, polo, log):
            return False
        if not _clicar_salvar(driver, log):
            return False
        _ocultar_multipla_selecao(driver)
        return True
    except Exception as e:
        logger.error(f'[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade (função principal): {e}')
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
        # A própria visibilidade_sigilosos fará o switch de aba para /detalhe e o F5.
        
        # Usa a função local que já tem tab switching e F5
        # Passando log=True fixo para garantir que falhas sejam relatadas no logger independentemente do modo debug.
        resultado = visibilidade_sigilosos(driver, log=True)
        
        if resultado:
            logger.info('[ATO][VISIBILIDADE] Execução da visibilidade concluída com sucesso')
            return True
        else:
            logger.error('[VISIBILIDADE][ERRO] Função visibilidade_sigilosos falhou.')
            return False
            
    except Exception as e:
        logger.error(f'[VISIBILIDADE][ERRO] Exceção ao executar visibilidade_sigilosos: {e}')
        import traceback
        logger.error(traceback.format_exc())
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
        aguardar_renderizacao_nativa(driver, 'input#inputFiltro', 'aparecer', 2)
        return True
    except Exception as e:
        if log:
            logger.error(f'[CLS][MODELO][ERRO] Falha ao acessar/interagir com o campo de filtro de modelos: {e}')
        return False
