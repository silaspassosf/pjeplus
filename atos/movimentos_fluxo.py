import logging
logger = logging.getLogger(__name__)

from .core import *

from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait


def _localizar_botao_tarefa(driver: WebDriver, timeout: int = 8):
    """Tentativa robusta de localizar o botão 'Abrir tarefa do processo'.
    Retorna WebElement ou None.
    """
    from selenium.webdriver.common.by import By
    try:
        # 1) seletor canônico
        btn = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=timeout)
        if btn:
            return btn
    except Exception:
        pass

    try:
        # 2) busca robusta por textos/atributos (maisPje style)
        textos = ['Abre a tarefa do processo', 'Abrir tarefa', 'tarefa do processo', 'tarefa']
        el = buscar_seletor_robusto(driver, textos, timeout=timeout)
        if el:
            return el
    except Exception:
        pass

    try:
        # 3) tentativas por seletores alternativos
        alt = ["button[mattooltip*='tarefa']", "button[aria-label*='tarefa']", "button[title*='tarefa']"]
        for s in alt:
            try:
                el = driver.find_element(By.CSS_SELECTOR, s)
                if el and el.is_displayed():
                    return el
            except Exception:
                continue
    except Exception:
        pass

    return None


def mov_simples(
    driver: WebDriver,
    seletor_alvo: str,
    texto_confirmacao: Optional[str] = None,
    debug: bool = False,
    timeout: int = 15
) -> bool:
    """
    Versão SIMPLIFICADA do movimento - apenas uma tentativa:
    1. Busca aba /detalhe
    2. Clica uma vez no botão "Abrir tarefa do processo" 
    3. Troca para nova aba
    4. Procura o botão alvo diretamente (sem clicar em "Análise" novamente)
    5. Clica no botão alvo
    6. (Opcional) Confirma ação
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    def log_debug(msg):
        if debug:
            try:
                print(msg)
            except Exception:
                pass

    try:
        # ===== ETAPA 1: GARANTIR QUE ESTÁ EM /DETALHE =====
        log_debug("Buscando aba /detalhe...")
        abas_atuais = driver.window_handles
        aba_detalhe = None

        for aba in abas_atuais:
            driver.switch_to.window(aba)
            url_atual = driver.current_url
            if '/detalhe' in url_atual:
                aba_detalhe = aba
                log_debug(f" Aba /detalhe encontrada: {url_atual}")
                break

        if not aba_detalhe:
            logger.error('[MOV_SIMPLES][ERRO] Aba /detalhe não encontrada!')
            return False

        # ===== ETAPA 2: ABRIR TAREFA DO PROCESSO =====
        log_debug("Procurando botão 'Abrir tarefa do processo'...")
        btn_abrir_tarefa = _localizar_botao_tarefa(driver, timeout=max(2, timeout//2))
        if not btn_abrir_tarefa:
            logger.error(f'[MOV_SIMPLES][ERRO] Botão "Abrir tarefa do processo" não encontrado!')
            return False

        # Captura o texto da tarefa
        tarefa_do_botao = None
        try:
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                log_debug(f"Tarefa identificada: '{tarefa_do_botao}'")
        except Exception:
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
                log_debug(f"Tarefa identificada (texto completo): '{tarefa_do_botao}'")
            except Exception:
                log_debug("Não foi possível capturar nome da tarefa")

        # Clica na tarefa (usar estratégia sem scroll/dispatchEvent)
        abas_antes = set(driver.window_handles)
        click_resultado = safe_click_no_scroll(driver, btn_abrir_tarefa, log=debug)

        if not click_resultado:
            logger.error(f'[MOV_SIMPLES][ERRO] Falha no clique do botão da tarefa')
            return False

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
            log_debug("Foco trocado para nova aba da tarefa")
        else:
            log_debug("Nenhuma nova aba detectada, prosseguindo na aba atual")

        # ===== ETAPA 4: PROCURAR E CLICAR NO BOTÃO ALVO =====
        log_debug(f"Procurando botão alvo: {seletor_alvo}")
        try:
            btn_alvo = WebDriverWait(driver, timeout//2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_alvo))
            )
            safe_click(driver, btn_alvo)
        except Exception:
            logger.error(f'[MOV_SIMPLES][ERRO] Botão alvo não encontrado: {seletor_alvo}')
            return False

        # ===== ETAPA 5: CONFIRMAÇÃO (OPCIONAL) =====
        if texto_confirmacao:
            try:
                btn_confirma = WebDriverWait(driver, timeout//2).until(
                    EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{texto_confirmacao}') or .//span[contains(., '{texto_confirmacao}')]]"))
                )
                btn_confirma.click()
            except Exception as e:
                logger.error(f'[MOV_SIMPLES][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}": {e}')
                return False

        return True

    except Exception as e:
        logger.error(f'[MOV_SIMPLES][ERRO] Falha geral no movimento simples: {e}')
        return False


def mov(
    driver: WebDriver,
    seletor_alvo: str,
    texto_confirmacao: Optional[str] = None,
    debug: bool = False,
    timeout: int = 15
) -> bool:
    """
    Fluxo geral MELHORADO para movimentos:
    1. Verifica se está em /detalhe, se não estiver busca a aba /detalhe
    2. Clica no botão "Abrir tarefa do processo" (BTN_TAREFA_PROCESSO)
    3. Troca para nova aba, se aberta
    4. Procura o botão alvo (seletor_alvo)
       - Se não encontrar, SEMPRE clica em "Análise" e tenta novamente
       - Se ainda não der certo, recomeça do passo 1 (volta para /detalhe)
    5. Clica no botão alvo
    6. (Opcional) Confirma ação se texto_confirmacao for fornecido
    """
    print(f'[MOV] 🔍 Iniciando movimento geral - Seletor: {seletor_alvo}')  # Log forçado para debug
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    def log_debug(msg):
        if debug:
            try:
                print(msg)
            except Exception:
                pass

    def buscar_aba_detalhe():
        """Busca e troca para aba /detalhe"""
        log_debug("Buscando aba /detalhe...")
        abas_atuais = driver.window_handles
        aba_detalhe = None
        
        for aba in abas_atuais:
            driver.switch_to.window(aba)
            url_atual = driver.current_url
            if '/detalhe' in url_atual:
                aba_detalhe = aba
                log_debug(f"✅ Aba /detalhe encontrada: {url_atual}")
                break
        
        if aba_detalhe:
            driver.switch_to.window(aba_detalhe)
            return True
        else:
            print('[MOV][ERRO] Aba /detalhe não encontrada!')
            return False
    
    def tentar_encontrar_alvo():
        """Tenta encontrar o botão alvo, com fallback para Análise"""
        try:
            # Primeira tentativa: buscar o alvo diretamente
            btn_alvo = WebDriverWait(driver, timeout//3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_alvo))
            )
            safe_click(driver, btn_alvo)
            return True
        except Exception:
            # Verificar se já está em "Análise" - se sim, e botão não encontrado, está correto
            if seletor_alvo == "button[aria-label='Aguardando prazo']":
                try:
                    # Verificar se estamos em uma tarefa de análise
                    elementos_analise = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ANÁLISE', 'análise'), 'análise')]")
                    em_analise = any('análise' in el.text.lower() for el in elementos_analise if el.is_displayed())
                    if em_analise:
                        log_debug("Já está em 'Análise' e botão 'Aguardando prazo' não disponível - está correto")
                        return True
                except Exception:
                    pass

            # SEMPRE tenta clicar em "Análise" se não encontrar o alvo
            log_debug("Botão alvo não encontrado. Tentando clicar em 'Análise'...")
            btn_analise = None
            
            # Busca por texto "Análise"
            btns_analise = driver.find_elements(By.XPATH, "//button[contains(translate(normalize-space(text()), 'ANÁLISE', 'análise'), 'análise')]")
            for btn in btns_analise:
                if btn.is_displayed() and btn.is_enabled():
                    btn_analise = btn
                    break
            
            # Fallback: busca por aria-label
            if not btn_analise:
                btns_analise = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Análise']")
                for btn in btns_analise:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_analise = btn
                        break
            
            if btn_analise:
                safe_click(driver, btn_analise)
                time.sleep(1.5)  # Aguarda carregamento após análise
                
                # Segunda tentativa: buscar o alvo após Análise
                try:
                    btn_alvo = WebDriverWait(driver, timeout//3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_alvo))
                    )
                    safe_click(driver, btn_alvo)
                    return True
                except Exception:
                    log_debug("Botão alvo não encontrado mesmo após 'Análise'")
                    return False
            else:
                log_debug("Botão 'Análise' não encontrado")
                return False
    
    # Máximo de 2 tentativas completas
    for tentativa in range(1, 3):
        try:
            
            # ===== ETAPA 1: GARANTIR QUE ESTÁ EM /DETALHE =====
            if not buscar_aba_detalhe():
                logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Não foi possível encontrar aba /detalhe')
                if tentativa == 2:  # Última tentativa
                    return False
                continue
            
            # ===== ETAPA 2: ABRIR TAREFA DO PROCESSO =====
            log_debug("Procurando botão 'Abrir tarefa do processo'...")
            btn_abrir_tarefa = _localizar_botao_tarefa(driver, timeout=max(2, timeout//2))
            if not btn_abrir_tarefa:
                logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Botão "Abrir tarefa do processo" não encontrado!')
                if tentativa == 2:
                    return False
                continue
            
            # Captura o texto da tarefa antes do clique
            tarefa_do_botao = None
            try:
                span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
                if span_tarefa:
                    tarefa_do_botao = span_tarefa.text.strip()
                    log_debug(f"Tarefa identificada: '{tarefa_do_botao}'")
            except Exception:
                try:
                    tarefa_do_botao = btn_abrir_tarefa.text.strip()
                    log_debug(f"Tarefa identificada (texto completo): '{tarefa_do_botao}'")
                except Exception:
                    log_debug("Não foi possível capturar nome da tarefa")
            
            # Clica na tarefa (usar dispatchEvent/sem scroll)
            abas_antes = set(driver.window_handles)
            click_resultado = safe_click_no_scroll(driver, btn_abrir_tarefa, log=debug)
            
            if not click_resultado:
                logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Falha no clique do botão da tarefa')
                if tentativa == 2:
                    return False
                continue
            
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
                log_debug("Foco trocado para nova aba da tarefa")
            else:
                log_debug("Nenhuma nova aba detectada, prosseguindo na aba atual")
            
            # ===== ETAPA 4: ENCONTRAR E CLICAR NO ALVO =====
            if tentar_encontrar_alvo():
                # ===== ETAPA 5: CONFIRMAÇÃO (OPCIONAL) =====
                if texto_confirmacao:
                    try:
                        btn_confirma = WebDriverWait(driver, timeout//2).until(
                            EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{texto_confirmacao}') or .//span[contains(., '{texto_confirmacao}')]]"))
                        )
                        btn_confirma.click()
                    except Exception as e:
                        logger.error(f'[MOV][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}": {e}')
                        return False
                
                return True
            else:
                logger.warning(f'[MOV][WARN] Tentativa {tentativa}: Não foi possível encontrar o alvo, tentando novamente...')
                if tentativa == 2:
                    logger.error('[MOV][ERRO] Esgotadas todas as tentativas')
                    return False
                # Fechar aba da tarefa antes de tentar novamente
                try:
                    if nova_aba and nova_aba in driver.window_handles:
                        driver.close()
                        # Voltar para primeira aba disponível
                        if driver.window_handles:
                            driver.switch_to.window(driver.window_handles[0])
                except Exception:
                    pass
                continue
                
        except Exception as e:
            logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Falha no fluxo de movimento: {e}')
            if tentativa == 2:
                return False
            continue
    
    return False


def _remover_acentos(texto: str) -> str:
    import unicodedata
    if not texto:
        return ''
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def movimentar_inteligente(driver, destino: str, ultimo_lance: str = '', chip: Optional[str] = None, responsavel: Optional[str] = None, timeout: int = 15) -> bool:
    from selenium.webdriver.common.by import By
    import time

    def log(msg):
        try:
            print(msg)
        except Exception:
            pass

    try:
        tarefa_el = esperar_elemento(driver, 'pje-cabecalho-tarefa h1.titulo-tarefa', timeout=3)
        tarefa_text = tarefa_el.text if tarefa_el else None
        if not tarefa_text:
            el = buscar_seletor_robusto(driver, ['titulo-tarefa', 'pje-cabecalho-tarefa', 'tarefa'], timeout=3)
            tarefa_text = el.text if el else 'Análise'

        tarefa_norm = _remover_acentos((tarefa_text or '').lower())
        destino_norm = _remover_acentos((destino or '').lower())
        if '?' in destino:
            destino_norm = destino_norm.replace('?', '') + ' ' + tarefa_norm

        log(f"[MOV_INT] tarefa='{tarefa_text}' destino='{destino}'")

        if destino_norm and destino_norm in tarefa_norm:
            if ultimo_lance:
                try:
                    btn = esperar_elemento(driver, 'button', texto=ultimo_lance, timeout=3)
                    if btn:
                        safe_click_no_scroll(driver, btn)
                except Exception:
                    pass
            if chip:
                try:
                    safe_click_no_scroll(driver, esperar_elemento(driver, 'button[aria-label="Incluir Chip Amarelo"]', timeout=2))
                except Exception:
                    pass
            if responsavel:
                try:
                    buscar_seletor_robusto(driver, ['Abrir o GIGS', 'GIGS'], timeout=2)
                except Exception:
                    pass
            return True

        if 'elaborar' in tarefa_norm or 'assinar' in tarefa_norm:
            log('[MOV_INT] tarefa de elaborar/assinar - abortando')
            return False

        if 'analise' in tarefa_norm:
            try:
                bt = esperar_elemento(driver, 'button', texto=destino, timeout=max(5, timeout//2))
                if not bt:
                    time.sleep(1)
                    bt = esperar_elemento(driver, 'button', texto=destino, timeout=5)
                if bt and bt.is_enabled():
                    safe_click_no_scroll(driver, bt)
                    # último lance, chip e responsavel manejados por helpers
                    if ultimo_lance:
                        try:
                            clicar_ultimo_lance(driver, ultimo_lance)
                        except Exception:
                            pass
                    try:
                        chip_responsavel(driver, chip=chip, responsavel=responsavel)
                    except Exception:
                        pass
                    return True
                return False
            except Exception:
                return False

        try:
            btn_analise = buscar_seletor_robusto(driver, ['Análise', 'analise'], timeout=4)
            if btn_analise:
                safe_click_no_scroll(driver, btn_analise)
                aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao', modo='aparecer', timeout=6)
                return movimentar_inteligente(driver, destino, ultimo_lance=ultimo_lance, chip=chip, responsavel=responsavel, timeout=timeout)
        except Exception:
            pass

        return False
    except Exception as e:
        try:
            logger.error(f'[MOV_INT][ERRO] {e}')
        except Exception:
            pass
        return False


def clicar_ultimo_lance(driver, texto_ultimo_lance: str, timeout: int = 5) -> bool:
    """Tenta clicar no último lance indicado pelo texto.

    Retorna True se clicou, False caso contrário.
    """
    try:
        if not texto_ultimo_lance:
            return False
        btn = None
        try:
            btn = esperar_elemento(driver, 'button', texto=texto_ultimo_lance, timeout=max(2, timeout//2))
        except Exception:
            btn = None

        if not btn:
            # tentar buscar por parcial do texto
            try:
                btns = driver.find_elements_by_xpath(f"//button[contains(., '{texto_ultimo_lance}')]")
                for b in btns:
                    try:
                        if b.is_displayed() and b.is_enabled():
                            btn = b
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if btn:
            try:
                safe_click_no_scroll(driver, btn)
                return True
            except Exception:
                return False
        return False
    except Exception:
        return False


def chip_responsavel(driver, chip: Optional[str] = None, responsavel: Optional[str] = None, timeout: int = 5) -> None:
    """Clica no chip (se solicitado) e tenta abrir seleção de responsável (GIGS) se solicitado.

    Não lança exceções em falhas, apenas tenta realizar as ações.
    """
    try:
        # Chip amarelo padrão
        if chip:
            try:
                el = esperar_elemento(driver, 'button[aria-label="Incluir Chip Amarelo"]', timeout=max(1, timeout//2))
                if el:
                    safe_click_no_scroll(driver, el)
            except Exception:
                pass

        # Responsável: abrir o GIGS para escolher, se aplicável
        if responsavel:
            try:
                gg = buscar_seletor_robusto(driver, ['Abrir o GIGS', 'GIGS'], timeout=max(1, timeout//2))
                if gg:
                    safe_click_no_scroll(driver, gg)
            except Exception:
                pass
    except Exception:
        pass


def verificar_minuta_preenchida(driver, timeout: int = 2) -> bool:
    """Heurística simples para detectar minuta em elaboração.

    Retorna True se identificar sinais de minuta em edição, False caso contrário.
    """
    try:
        # tentar detectar editor de texto/minuta (heurística)
        possible = ['pje-editor', 'textarea', 'cke_editable', 'editor-minuta']
        for sel in possible:
            try:
                el = esperar_elemento(driver, sel, timeout=timeout)
                if el:
                    text = ''
                    try:
                        text = el.text or el.get_attribute('value') or ''
                    except Exception:
                        text = ''
                    if text and len(text.strip()) > 5:
                        return True
            except Exception:
                continue
        return False
    except Exception:
        return False
