from Fix.selenium_base.element_interaction import safe_click
from Fix.log import logger
from Fix.extracao import bndt
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from .judicial_fluxo import ato_judicial
from .wrappers_ato import ato_bloq, ato_meios


def ato_pesquisas(driver, debug=False, gigs=None, **kwargs):
    """
    Wrapper para ato de pesquisas com lógica especial.
    Verifica e clica em 'Iniciar a execução' antes de executar o ato judicial.
    IMPORTANTE: Retorna (sucesso, sigilo_ativado) para aplicação de visibilidade posterior.
    """
    try:
        # 1. Lógica especial: Se existir botão 'Iniciar a execução', clicar antes de seguir
        try:
            from selenium.webdriver.common.by import By
            btn_iniciar = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Iniciar a execução'], button[mattooltip*='Iniciar a execução']")
            if btn_iniciar and btn_iniciar.is_displayed() and btn_iniciar.is_enabled():
                safe_click(driver, btn_iniciar)
                import time
                time.sleep(1)
        except Exception:
            pass
        
        # 2. Segue fluxo padrão do ato judicial com parâmetros fixos
        sucesso, sigilo_ativado = ato_judicial(
            driver,
            conclusao_tipo='BACEN',
            modelo_nome='xsbacen',
            prazo=30,
            marcar_pec=False,
            movimento='bloqueio',
            gigs=gigs,
            marcar_primeiro_destinatario=True,
            debug=debug,
            sigilo=True,
            atribuir_visibilidade_autor=True,
            descricao='Pesquisas para execução',
            intimar=False
        )
        
        # Para compatibilidade, armazena sigilo_ativado como atributo
        ato_pesquisas.ultimo_sigilo_ativado = sigilo_ativado
        
        # CORREÇÃO: Retorna tupla (sucesso, sigilo_ativado) para visibilidade externa
        return sucesso, sigilo_ativado
        
    except Exception as e:
        logger.error(f'[ATO_PESQUISAS][ERRO] Falha no fluxo do ato de pesquisas: {e}')
        try:
            driver.save_screenshot('erro_ato_pesquisas.png')
        except Exception:
            pass
        return False, False  # CORREÇÃO: Retorna tupla mesmo em erro


def idpj(
    driver: WebDriver,
    debug: bool = False
) -> bool:
    """
    Função IDPJ para casos "instaurado em face"
    
    Fluxo:
    0. Executa BNDT inclusão (nova etapa)
    1. Verifica lembretes de bloqueio na seção de post-its
    2. Se tem bloqueio com data não superior a 100 dias: executa ato_bloq
    3. Se não tem: executa ato_meios
    
    Returns:
        bool: True se executou com sucesso, False caso contrário
    """
    try:
        try:
            resultado_bndt = bndt(driver, inclusao=True)
            if resultado_bndt:
                pass
            else:
                pass
        except Exception as e:
            if debug:
                logger.error(f'[IDPJ]  Erro no BNDT inclusão: {e}')
            # Continua mesmo com erro no BNDT
        
        # 1. Verificar se há lembretes de bloqueio
        tem_bloqueio_recente = verificar_bloqueio_recente(driver, debug=debug)
        
        if tem_bloqueio_recente:
            return ato_bloq(driver)
        else:
            return ato_meios(driver)
            
    except Exception as e:
        if debug:
            logger.error(f'[IDPJ]  Erro na função idpj: {e}')
        return False


# Reexportar a implementação canônica de preencher_prazos_destinatarios
from atos.judicial_utils import preencher_prazos_destinatarios


def verificar_bloqueio_recente(driver, debug=False):
    """
    Verifica se existe lembrete de bloqueio com data não superior a 100 dias.
    Versão simplificada baseada na função original.
    
    Returns:
        bool: True se encontrou bloqueio recente, False caso contrário
    """
    try:
        import re
        from datetime import datetime, timedelta
        
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            lembretes_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.post-it-set'))
            )
        except:
            return False
        
        # Encontrar todos os lembretes expandidos
        lembretes = lembretes_section.find_elements(By.CSS_SELECTOR, 'mat-expansion-panel.mat-expanded')
        
        data_limite = datetime.now() - timedelta(days=100)
        
        for lembrete in lembretes:
            try:
                # Verificar título do lembrete
                titulo_element = lembrete.find_element(By.CSS_SELECTOR, 'mat-panel-title')
                titulo = titulo_element.text.strip().lower()
                
                # Verificar conteúdo do lembrete
                conteudo_element = lembrete.find_element(By.CSS_SELECTOR, 'div.post-it-conteudo')
                conteudo = conteudo_element.text.strip().lower()
                
                if ('bloq' in titulo or 'bloq' in conteudo or 
                    'bloqueio' in titulo or 'bloqueio' in conteudo):
                    
                    try:
                        rodape = lembrete.find_element(By.CSS_SELECTOR, 'div.rodape-post-it-usuario span')
                        rodape_texto = rodape.text.strip()
                        
                        # Buscar padrão de data (formato DD/MM/AA HH:MM)
                        match_data = re.search(r'(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})', rodape_texto)
                        
                        if match_data:
                            data_str = match_data.group(1)
                            # Converter para formato completo (assumindo 20XX)
                            dia, mes, ano = data_str.split('/')
                            ano_completo = f"20{ano}"
                            
                            data_lembrete = datetime.strptime(f"{dia}/{mes}/{ano_completo}", "%d/%m/%Y")
                            
                            if debug:
                                pass
                            
                            # Verificar se a data é dentro dos últimos 100 dias
                            if data_lembrete >= data_limite:
                                return True
                            else:
                                pass
                        else:
                            pass
                    except Exception as e:
                        if debug:
                            logger.error(f'[IDPJ][BLOQUEIO]  Erro ao extrair data: {e}')
                        continue
                
            except Exception as e:
                if debug:
                    logger.error(f'[IDPJ][BLOQUEIO]  Erro ao analisar lembrete: {e}')
                continue
        
        return False
        
    except Exception as e:
        if debug:
            logger.error(f'[IDPJ][BLOQUEIO]  Erro na verificação de bloqueio: {e}')
        return False