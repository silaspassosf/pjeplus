"""
Módulo para certificação de intimações no PJe baseado em dados da eCarta
Implementa funcionalidade similar ao AVJT para "Objeto entregue ao destinatário"
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re

def certificar_intimacao_pje(driver, intimacao_data, log=True):
    """
    Certifica uma intimação no PJe baseado nos dados da eCarta
    
    Args:
        driver: WebDriver do Selenium
        intimacao_data: Dict com dados da intimação (id, processo, dados_ecarta)
        log: Se deve fazer log das operações
    
    Returns:
        bool: True se certificação foi bem-sucedida
    """
    try:
        if log:
            print(f"[CERT][INFO] Iniciando certificação para intimação ID: {intimacao_data.get('id', 'N/A')}")
        
        processo_numero = intimacao_data.get('processo')
        if not processo_numero:
            if log:
                print("[CERT][ERRO] Número do processo não encontrado nos dados da intimação")
            return False
        
        # 1. Abre o processo no PJe em nova aba
        original_window = driver.current_window_handle
        pje_url = f"https://pje.trt2.jus.br/pje/ConsultaPublica/DetalheProcessoConsultaPublica/listView.seam?ca={processo_numero}"
        
        driver.execute_script(f"window.open('{pje_url}', '_blank');")
        time.sleep(2)
        
        # Troca para a nova aba
        windows = driver.window_handles
        for window in windows:
            if window != original_window:
                driver.switch_to.window(window)
                break
        
        if log:
            print(f"[CERT][INFO] Abrindo processo no PJe: {processo_numero}")
        
        # 2. Aguarda carregamento da página do processo
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "timeline"))
            )
            if log:
                print("[CERT][INFO] Página do processo carregada")
        except TimeoutException:
            if log:
                print("[CERT][ERRO] Timeout ao carregar página do processo")
            return False
        
        # 3. Localiza a intimação na timeline
        intimacao_encontrada = False
        try:
            # Procura pela intimação com base no ID da eCarta
            intimacao_id = intimacao_data.get('id', '')
            
            # Estratégia 1: Buscar por data ou conteúdo específico
            timeline_items = driver.find_elements(By.CSS_SELECTOR, ".timeline li")
            
            for item in timeline_items:
                item_text = item.text.lower()
                if 'intimação' in item_text:
                    # Verifica se pode estar relacionada com base em data ou conteúdo
                    if log:
                        print(f"[CERT][DEBUG] Verificando item da timeline: {item_text[:100]}...")
                    
                    # Procura por link de certificação ou botão de ação
                    try:
                        # Procura botão de certificar ou similar
                        btn_certificar = item.find_element(By.XPATH, ".//a[contains(@title, 'certificar') or contains(@title, 'Certificar')]")
                        if btn_certificar:
                            intimacao_encontrada = True
                            if log:
                                print(f"[CERT][INFO] Intimação encontrada na timeline, clicando para certificar")
                            
                            # Clica no botão de certificar
                            driver.execute_script("arguments[0].click();", btn_certificar)
                            time.sleep(2)
                            break
                    except NoSuchElementException:
                        continue
            
            if not intimacao_encontrada:
                if log:
                    print("[CERT][WARN] Intimação não encontrada na timeline ou botão de certificar não disponível")
                return False
        
        except Exception as e:
            if log:
                print(f"[CERT][ERRO] Erro ao localizar intimação na timeline: {e}")
            return False
        
        # 4. Preenche dados da certificação baseado na eCarta
        try:
            # Aguarda modal ou página de certificação
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//textarea | //input[@type='text'] | //*[contains(@class, 'certificacao')]"))
            )
            
            # Monta texto da certificação com base nos dados da eCarta
            dados_ecarta = intimacao_data.get('dados_ecarta', '')
            if dados_ecarta:
                texto_certificacao = f"Certifico que, conforme consulta realizada no sistema eCarta dos Correios, o objeto foi entregue ao destinatário.\n\nDados da eCarta:\n{dados_ecarta}"
            else:
                texto_certificacao = "Certifico que, conforme consulta realizada no sistema eCarta dos Correios, o objeto foi entregue ao destinatário."
            
            # Procura campo de texto para certificação
            campos_texto = driver.find_elements(By.XPATH, "//textarea | //input[@type='text'][contains(@placeholder, 'certificação') or contains(@name, 'certificacao')]")
            
            if campos_texto:
                campo_principal = campos_texto[0]
                campo_principal.clear()
                campo_principal.send_keys(texto_certificacao)
                
                if log:
                    print("[CERT][INFO] Texto de certificação preenchido")
                
                # Procura e clica botão de salvar/confirmar
                botoes_salvar = driver.find_elements(By.XPATH, "//button[contains(text(), 'Salvar') or contains(text(), 'Confirmar') or contains(text(), 'Certificar')]")
                
                if botoes_salvar:
                    botoes_salvar[0].click()
                    time.sleep(2)
                    
                    if log:
                        print("[CERT][SUCCESS] Certificação realizada com sucesso")
                    return True
                else:
                    if log:
                        print("[CERT][WARN] Botão de salvar não encontrado")
            else:
                if log:
                    print("[CERT][WARN] Campo de texto para certificação não encontrado")
        
        except TimeoutException:
            if log:
                print("[CERT][ERRO] Timeout ao aguardar modal de certificação")
        except Exception as e:
            if log:
                print(f"[CERT][ERRO] Erro ao preencher certificação: {e}")
        
        return False
        
    except Exception as e:
        if log:
            print(f"[CERT][ERRO] Erro geral na certificação: {e}")
        return False
    
    finally:
        # Volta para a aba original
        try:
            driver.switch_to.window(original_window)
        except:
            pass


def processar_certificacoes_ecarta(driver, ecarta_data, notification_data, log=True):
    """
    Processa todas as certificações possíveis baseado nos dados da eCarta
    
    Args:
        driver: WebDriver do Selenium
        ecarta_data: Lista de dados da eCarta
        notification_data: Lista de dados das intimações extraídas
        log: Se deve fazer log das operações
    
    Returns:
        int: Número de certificações processadas com sucesso
    """
    certificacoes_realizadas = 0
    
    if not ecarta_data or not notification_data:
        if log:
            print("[CERT][INFO] Nenhum dado disponível para certificação")
        return 0
    
    for i, dados_ecarta in enumerate(ecarta_data):
        try:
            # Correlaciona dados da eCarta com intimação
            intimacao_correspondente = None
            
            for notif in notification_data:
                # Tenta correlacionar pelo ID ou processo
                if notif.get('id') in dados_ecarta or notif.get('processo') in dados_ecarta:
                    intimacao_correspondente = notif
                    break
            
            if not intimacao_correspondente:
                if log:
                    print(f"[CERT][WARN] Não foi possível correlacionar dados da eCarta {i+1} com intimação")
                continue
            
            # Prepara dados para certificação
            intimacao_data = {
                'id': intimacao_correspondente.get('id'),
                'processo': intimacao_correspondente.get('processo'),
                'dados_ecarta': dados_ecarta,
                'content': intimacao_correspondente.get('content', '')
            }
            
            # Realiza certificação
            if certificar_intimacao_pje(driver, intimacao_data, log):
                certificacoes_realizadas += 1
                if log:
                    print(f"[CERT][SUCCESS] Certificação {i+1} realizada com sucesso")
            else:
                if log:
                    print(f"[CERT][ERRO] Falha na certificação {i+1}")
        
        except Exception as e:
            if log:
                print(f"[CERT][ERRO] Erro ao processar certificação {i+1}: {e}")
    
    if log:
        print(f"[CERT][RESULT] {certificacoes_realizadas} certificações realizadas de {len(ecarta_data)} possíveis")
    
    return certificacoes_realizadas


def adicionar_funcionalidade_avjt_ecarta(driver, log=True):
    """
    Adiciona funcionalidade estilo AVJT para células "Objeto entregue ao destinatário"
    
    Args:
        driver: WebDriver do Selenium
        log: Se deve fazer log das operações
    
    Returns:
        list: Lista de elementos configurados
    """
    elementos_configurados = []
    
    try:
        # Adiciona CSS para estilo AVJT
        driver.execute_script("""
            // Adiciona CSS estilo AVJT
            var style = document.createElement('style');
            style.textContent = `
                .avjt-certificar {
                    cursor: pointer !important;
                    background-color: #f8f9fa !important;
                    border: 1px solid #dee2e6 !important;
                    transition: all 0.3s ease !important;
                }
                .avjt-certificar:hover {
                    background-color: #e9ecef !important;
                    border-color: #007bff !important;
                    box-shadow: 0 2px 4px rgba(0,123,255,0.2) !important;
                }
                .avjt-certificar-processando {
                    background-color: #fff3cd !important;
                    border-color: #ffc107 !important;
                }
                .avjt-certificar-sucesso {
                    background-color: #d4edda !important;
                    border-color: #28a745 !important;
                }
                .avjt-certificar-erro {
                    background-color: #f8d7da !important;
                    border-color: #dc3545 !important;
                }
            `;
            document.head.appendChild(style);
        """)
        
        # Procura e configura células "Objeto entregue ao destinatário"
        celulas_entregue = driver.find_elements(By.XPATH, "//td[contains(text(), 'Objeto entregue ao destinatário')]")
        
        if log and celulas_entregue:
            print(f"[AVJT][INFO] Configurando {len(celulas_entregue)} células para certificação estilo AVJT")
        
        for i, celula in enumerate(celulas_entregue):
            try:
                # Configura célula estilo AVJT
                driver.execute_script("""
                    var celula = arguments[0];
                    var indice = arguments[1];
                    
                    // Adiciona classes e atributos AVJT
                    celula.classList.add('avjt-certificar');
                    celula.setAttribute('role', 'gridcell');
                    celula.title = 'Abrir Histórico e Certificar no PJe';
                    celula.style.width = '15%';
                    celula.style.textAlign = 'center';
                    celula.style.fontWeight = 'normal';
                    
                    // Adiciona funcionalidade de clique
                    celula.addEventListener('click', function(e) {
                        e.preventDefault();
                        
                        // Marca como processando
                        this.classList.remove('avjt-certificar');
                        this.classList.add('avjt-certificar-processando');
                        this.title = 'Processando certificação...';
                        
                        // Extrai dados da linha
                        var linha = this.closest('tr');
                        var dadosLinha = linha.textContent;
                        
                        console.log('AVJT: Iniciando certificação para:', dadosLinha);
                        
                        // Sinaliza para o Python que certificação foi solicitada
                        window.avjt_certificacao_solicitada = {
                            indice: indice,
                            dados: dadosLinha,
                            elemento: this
                        };
                        
                        // Dispara evento customizado
                        var evento = new CustomEvent('avjt_certificar', {
                            detail: {
                                indice: indice,
                                dados: dadosLinha,
                                elemento: this
                            }
                        });
                        document.dispatchEvent(evento);
                    });
                    
                    console.log('AVJT: Célula configurada:', indice);
                """, celula, i)
                
                elementos_configurados.append({
                    'indice': i,
                    'elemento': celula,
                    'texto': celula.text.strip()
                })
                
            except Exception as e:
                if log:
                    print(f"[AVJT][ERRO] Erro ao configurar célula {i}: {e}")
        
        if log and elementos_configurados:
            print(f"[AVJT][SUCCESS] {len(elementos_configurados)} células configuradas com funcionalidade AVJT")
    
    except Exception as e:
        if log:
            print(f"[AVJT][ERRO] Erro ao adicionar funcionalidade AVJT: {e}")
    
    return elementos_configurados
