import logging
logger = logging.getLogger(__name__)

from .core import *

from selenium.webdriver.remote.webdriver import WebDriver


# ============================================================================
# DESPACHO GENÉRICO - PARA PETIÇÕES EM PROSSEGUIMENTO/MEIOS DE EXECUÇÃO
# ============================================================================

def despacho_generico(driver: WebDriver, peticao) -> bool:
    """
    Executa despacho genérico para petições em "Prosseguimento/Meios de Execução".
    
    Fluxo:
    1. Abre tarefa do processo (clica em BTN_TAREFA_PROCESSO)
    2. Troca para nova aba
    3. Tenta clicar em "Conclusão ao Magistrado"
       - Se não encontrar, clica em "Análise" e então clica em "Conclusão ao Magistrado"
    4. Clica em "Despacho"
    5. Confirma
    
    Args:
        driver: WebDriver do Selenium
        peticao: Objeto PeticaoLinha com dados da petição
    
    Returns:
        bool: True se despacho foi bem-sucedido, False caso contrário
    """
    
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # ===== ETAPA 1: GARANTIR QUE ESTÁ EM /DETALHE =====
        abas_atuais = driver.window_handles
        aba_detalhe = None
        
        for aba in abas_atuais:
            driver.switch_to.window(aba)
            url_atual = driver.current_url
            if '/detalhe' in url_atual:
                aba_detalhe = aba
                break
        
        if not aba_detalhe:
            return False
        
        # ===== ETAPA 2: ABRIR TAREFA DO PROCESSO =====
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=10)
        if not btn_abrir_tarefa:
            return False
        
        abas_antes = set(driver.window_handles)
        safe_click(driver, btn_abrir_tarefa)

        # ===== ETAPA 3: TROCAR PARA NOVA ABA =====
        nova_aba = None
        if abas_antes:
            try:
                from Fix.abas import aguardar_nova_aba
                nova_aba = aguardar_nova_aba(driver, next(iter(abas_antes)), timeout=10)
            except Exception:
                logger.info('[DESPACHO_GENERICO] Nenhuma nova aba detectada (continuando na mesma aba)')

        if nova_aba:
            driver.switch_to.window(nova_aba)
        
        # ===== ETAPA 4: TENTAR CLICAR EM "CONCLUSÃO AO MAGISTRADO" =====
        
        btn_conclusao = None
        try:
            # Tentativa 1: Busca por CSS/XPath direto
            btns = driver.find_elements(By.XPATH, 
                "//button[contains(translate(normalize-space(text()), 'ÇÃOA', 'çãoa'), 'conclusão ao magistrado') or contains(normalize-space(text()), 'Conclusão ao magistrado')]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn_conclusao = btn
                    break
        except Exception:
            pass
        
        # Se não encontrou, clica em "Análise" e tenta novamente
        if not btn_conclusao:
            
            btn_analise = None
            try:
                btns = driver.find_elements(By.XPATH, 
                    "//button[contains(translate(normalize-space(text()), 'ANÁLISE', 'análise'), 'análise')]")
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_analise = btn
                        break
            except Exception:
                pass
            
            if btn_analise:
                safe_click(driver, btn_analise)
                try:
                    from Fix.core import aguardar_renderizacao_nativa
                    aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', 'aparecer', timeout=8)
                except Exception:
                    pass
                
                # Tenta novamente encontrar "Conclusão ao Magistrado"
                try:
                    btns = driver.find_elements(By.XPATH, 
                        "//button[contains(translate(normalize-space(text()), 'ÇÃOA', 'çãoa'), 'conclusão ao magistrado') or contains(normalize-space(text()), 'Conclusão ao magistrado')]")
                    for btn in btns:
                        if btn.is_displayed() and btn.is_enabled():
                            btn_conclusao = btn
                            break
                except Exception:
                    pass
            else:
                return False
        
        if btn_conclusao:
            safe_click(driver, btn_conclusao)
            try:
                from Fix.core import aguardar_renderizacao_nativa
                aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', 'aparecer', timeout=8)
            except Exception:
                pass
        else:
            return False
        
        # ===== ETAPA 5: CLICAR EM "DESPACHO" =====
        
        btn_despacho = None
        try:
            btns = driver.find_elements(By.XPATH, 
                "//button[contains(translate(normalize-space(text()), 'DESPACHO', 'despacho'), 'despacho')]")
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    btn_despacho = btn
                    break
        except Exception:
            pass
        
        if btn_despacho:
            safe_click(driver, btn_despacho)
            try:
                from Fix.core import aguardar_renderizacao_nativa
                aguardar_renderizacao_nativa(driver, timeout=5)
            except Exception:
                pass
            return True
        else:
            return False
        
    except Exception as e:
        logger.error(f'[DESPACHO_GENERICO]  Erro: {e}')
        import traceback
        traceback.print_exc()
        return False
