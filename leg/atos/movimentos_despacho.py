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
        import time
        
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
        time.sleep(1)
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            time.sleep(0.3)
        
        if nova_aba:
            driver.switch_to.window(nova_aba)
            time.sleep(1)
        
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
                time.sleep(1.5)
                
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
            time.sleep(1)
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
            time.sleep(1)
            return True
        else:
            return False
        
    except Exception as e:
        logger.error(f'[DESPACHO_GENERICO]  Erro: {e}')
        import traceback
        traceback.print_exc()
        return False
