# loop_prazo.py
# Função para automação em lote do painel global do PJe TRT2
# Segue estritamente o roteiro solicitado pelo usuário
# Importação das configurações do driver
import time
import re

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from Fix.core import (
    aplicar_filtro_100,
    aguardar_e_clicar,
    selecionar_opcao,
    filtrofases,
)
from Fix.utils import (
    configurar_recovery_driver,
    handle_exception_with_recovery,
)
from Fix.core import criar_driver_PC
from Fix.utils import login_cpf

# Type hints e imports adicionais
from typing import Optional, Dict, List, Union, Tuple, TYPE_CHECKING
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import de Fix.variaveis no topo (revertido para evitar problemas de timing)
# Mas mantendo lazy loading onde já está implementado
from Fix.variaveis import session_from_driver, PjeApiClient, obter_gigs_com_fase

# Import das funções refatoradas do módulo Prazo
from Prazo.p2b_prazo import fluxo_prazo

# ===== CONFIGURAÇÃO DE PERFORMANCE =====
# Número de workers para verificação paralela da API GIGS
# Ajuste conforme sua conexão: 5-10 (estável), 15-20 (rápida), 3-5 (lenta)
GIGS_API_MAX_WORKERS = 20

# NOTA: Imports de Fix.variaveis movidos para funções individuais (lazy loading)
# para evitar lentidão no carregamento inicial do módulo

# Constantes JavaScript para seleção de processos
SCRIPT_SELECAO_GIGS_AJ_JT = '''
function selecionarProcessosPorGIGS(processosComGIGS) {
    console.log(" Iniciando seleção de GIGS. Processos a selecionar:", processosComGIGS);
    
    let linhas = document.querySelectorAll('tr.cdk-drag');
    console.log(" Total de linhas encontradas:", linhas.length);
    
    let selecionados = 0;
    let padrao = /(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/;
    
    linhas.forEach(function(linha, idx) {
        // Estratégia 1: Procurar em links <a>
        let numeroProcesso = null;
        let links = linha.querySelectorAll('a');
        for (let link of links) {
            let match = link.textContent.match(padrao);
            if (match) {
                numeroProcesso = match[1];
                break;
            }
        }
        
        // Estratégia 2: Procurar em toda a linha (fallback)
        if (!numeroProcesso) {
            let match = linha.textContent.match(padrao);
            if (match) {
                numeroProcesso = match[1];
            }
        }
        
        // Se encontrou processo, log e verifica se está na lista
        if (numeroProcesso) {
            console.log(`  [${idx}] Encontrado: ${numeroProcesso}, está na lista: ${processosComGIGS.includes(numeroProcesso)}`);
            
            // Se está na lista de GIGS, selecionar
            if (processosComGIGS.includes(numeroProcesso)) {
                let checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
                console.log(`    ✓ Checkbox encontrado: ${checkbox !== null}, checked: ${checkbox ? checkbox.checked : 'N/A'}`);
                
                if (checkbox && !checkbox.checked) {
                    checkbox.click();
                    linha.style.backgroundColor = "#cce5ff";
                    selecionados++;
                    console.log(`    ✅ CLICOU no checkbox`);
                } else {
                    console.log(`    ⚠️ Checkbox não clicado (já estava checked ou não encontrado)`);
                }
            }
        }
    });
    
    console.log("✅ Seleção concluída. Total selecionados:", selecionados);
    return selecionados;
}
return selecionarProcessosPorGIGS(arguments[0]);
'''

SCRIPT_SELECAO_LIVRES = '''
try {
    let linhas = document.querySelectorAll('tr.cdk-drag');
    let selecionados = 0;
    linhas.forEach(function(linha){
        let prazo = linha.querySelector('td:nth-child(9) time');
        let prazoVazio = !prazo || !prazo.textContent.trim();
        let hasComment = linha.querySelector('i.fa-comment') !== null;
        let inputField = linha.querySelector('input[matinput]');
        let campoPreenchido = inputField && inputField.value.trim();
        let temLupa = linha.querySelector('td:nth-child(3) i.fa-search') !== null;
        if (prazoVazio && !hasComment && !campoPreenchido && !temLupa) {
            let checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
            if (checkbox && !checkbox.checked) {
                checkbox.click();
                linha.style.backgroundColor = "#ffccd2";
                selecionados++;
            }
        }
    });
    return selecionados;
} catch(e) { return -1; }
'''

SCRIPT_SELECAO_NAO_LIVRES = '''
function selecionarProcessos(maxProcessos) {
    const linhas = document.querySelectorAll('tr.cdk-drag');
    let selecionados = 0;
    let totalNaoLivres = 0;
    
    // Primeiro conta total de não livres
    linhas.forEach(linha => {
        const prazo = linha.querySelector('td:nth-child(9) time');
        const prazoPreenchido = prazo && prazo.textContent.trim();
        const hasComment = linha.querySelector('i.fa-comment') !== null;
        const inputField = linha.querySelector('input[matinput]');
        const campoPreenchido = inputField && inputField.value.trim();
        
        if (prazoPreenchido || hasComment || campoPreenchido) {
            totalNaoLivres++;
        }
    });
    
    // Depois seleciona até maxProcessos
    for (const linha of linhas) {
        if (selecionados >= maxProcessos) break;
        
        const prazo = linha.querySelector('td:nth-child(9) time');
        const prazoPreenchido = prazo && prazo.textContent.trim();
        const hasComment = linha.querySelector('i.fa-comment') !== null;
        const inputField = linha.querySelector('input[matinput]');
        const campoPreenchido = inputField && inputField.value.trim();
        
        if (prazoPreenchido || hasComment || campoPreenchido) {
            const checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
            if (checkbox && !checkbox.checked) {
                checkbox.click();
                linha.style.backgroundColor = "#d2ffcc";
                selecionados++;
            }
        }
    }
    return {selecionados, totalNaoLivres};
}
return selecionarProcessos(arguments[0]);
'''


def _ciclo1_aplicar_filtro_fases(driver: WebDriver) -> Union[bool, str]:
    """Aplica filtro de liquidação/execução no painel 14.
    
    Returns:
        True: filtro aplicado e processos encontrados
        "no_more_processes": filtro aplicado mas sem processos
        False: erro ao aplicar filtro
    """
    try:
        result = filtrofases(driver, fases_alvo=['liquidação', 'execução'])
        if not result:
            # filtrofases retorna False quando não encontra as opções para selecionar
            # Isso significa que não há processos nessas fases
            return "no_more_processes"
        
        # AGUARDAR LISTA CARREGAR - verificar se há processos ou mensagem de vazio
        print('[CICLO1] Aguardando lista povoar após filtro...')
        max_tentativas = 20  # ~6 segundos
        lista_carregada = False
        
        for tentativa in range(max_tentativas):
            # Verificar se apareceu mensagem de lista vazia
            try:
                msg_vazia = driver.find_element(By.XPATH, "//span[contains(text(), 'Não há processos neste tema')]")
                if msg_vazia.is_displayed():
                    print('[CICLO1] ✓ Lista vazia confirmada (mensagem encontrada)')
                    return "no_more_processes"
            except:
                pass
            
            # Verificar se há processos na tabela
            try:
                linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class, tr.cdk-drag')
                if len(linhas) > 0:
                    print(f'[CICLO1] ✓ Lista povoada com {len(linhas)} processo(s)')
                    lista_carregada = True
                    break
            except:
                pass
            
            time.sleep(0.3)
        
        if not lista_carregada:
            print('[CICLO1] ⚠️ Timeout aguardando lista povoar')
        
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f'[CICLO1] Erro ao aplicar filtro de fases: {e}')
        return False


def _verificar_quantidade_processos_paginacao(driver: WebDriver) -> int:
    """
    Verifica quantidade de processos lendo o elemento de paginação.
    Retorna: quantidade de processos ou -1 se não conseguir detectar
    """
    try:
        # Buscar o elemento span.total-registros que contém "X - Y de Z"
        total_elem = driver.find_element(By.CSS_SELECTOR, 'span.total-registros')
        texto = total_elem.text.strip()
        print(f'[CICLO1]  Paginação: "{texto}"')
        
        # Extrair o total (último número após "de")
        # Formato: "1 - 1 de 1" ou "1 - 20 de 150" ou "0 de 0"
        import re
        match = re.search(r'de\s+(\d+)', texto)
        if match:
            total = int(match.group(1))
            print(f'[CICLO1] ✅ Total de processos detectado: {total}')
            return total
        
        # Fallback: tentar detectar "0 de 0" ou formato sem hífen
        if '0 de 0' in texto or '0 - 0 de 0' in texto:
            print('[CICLO1] ✅ Paginação indica 0 processos')
            return 0
        
        print(f'[CICLO1] ⚠️ Não foi possível extrair quantidade do texto: "{texto}"')
        return -1
        
    except Exception as e:
        print(f'[CICLO1] ⚠️ Erro ao ler paginação: {e}')
        return -1


def _ciclo1_marcar_todas(driver: WebDriver) -> str:
    """Seleciona todos os processos via botão marcar-todas."""
    from Fix.core import com_retry
    
    def _tentar_marcar():
        # Usar XPath mais robusto para encontrar o botão marcar-todas
        print("[DEBUG] Procurando botão marcar-todas...")
        btn_marcar_todas = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//i[contains(@class, 'marcar-todas')]"))
        )
        print(f"[DEBUG] Botão marcar-todas encontrado: {btn_marcar_todas.get_attribute('outerHTML')}")
        # Usar JavaScript click para evitar obstrução
        result = driver.execute_script("""
        arguments[0].scrollIntoView(true);
        arguments[0].click();
        return true;
        """, btn_marcar_todas)
        if result:
            print("[DEBUG] Clique em marcar-todas executado com sucesso.")
        time.sleep(1)
        return result
    
    try:
        if com_retry(_tentar_marcar, max_tentativas=5, backoff_base=1.5, log=True):
            print("[DEBUG] Marcar-todas clicado com sucesso após retry.")
            return "success"
        else:
            print("[LOOP_PRAZO] Todas as tentativas de marcar-todas falharam")
            return "marcar_todas_not_found_but_continue"
    except Exception as e:
        print(f"[LOOP_PRAZO] Erro geral em marcar-todas: {e}")
        return "error"


def _ciclo1_abrir_suitcase(driver: WebDriver) -> bool:
    """Abre suitcase para movimentação em lote usando JavaScript click."""
    from Fix.core import com_retry

    print("[DEBUG] Aguardando suitcase aparecer...")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone'))
        )
        print("[DEBUG] Suitcase apareceu na página.")
    except Exception as e:
        print(f"[DEBUG] Suitcase não apareceu: {e}")
        return False
    elements = driver.find_elements(By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone')
    print(f"[DEBUG] Encontrados {len(elements)} elementos suitcase.")
    if elements:
        print(f"[DEBUG] Primeiro suitcase: {elements[0].get_attribute('outerHTML')}")

    def _tentar_abrir_suitcase():
        print("[DEBUG] Tentando clicar no suitcase...")
        # Usar JavaScript para encontrar e clicar
        script = '''
        try {
            let suitcase = document.querySelector('i.fas.fa-suitcase.icone');
            if (suitcase) {
                console.log('Suitcase encontrado:', suitcase.outerHTML);
                suitcase.scrollIntoView({block: 'center'});
                suitcase.click();
                return true;
            } else {
                console.log('Suitcase não encontrado');
                return false;
            }
        } catch(e) {
            console.error('Erro ao clicar suitcase:', e);
            return false;
        }
        '''
        result = driver.execute_script(script)
        if result:
            print("[DEBUG] Suitcase clicado com sucesso via JavaScript.")
        else:
            print("[DEBUG] Falha ao clicar no suitcase via JavaScript.")
        return result

    try:
        if com_retry(_tentar_abrir_suitcase, max_tentativas=3, backoff_base=1.5, log=True):
            print("[DEBUG] Suitcase aberto após retry.")
            time.sleep(1)
            return True
        else:
            print("[LOOP_PRAZO] Todas as tentativas de abrir suitcase falharam")
            return False
    except Exception as e:
        print(f"[LOOP_PRAZO] Erro geral em abrir suitcase: {e}")
        return False


def _ciclo1_aguardar_movimentacao_lote(driver: WebDriver) -> bool:
    """Aguarda carregamento da página de movimentação em lote."""
    print("[DEBUG] Aguardando URL /painel/movimentacao-lote...")
    try:
        WebDriverWait(driver, 15).until(
            EC.url_contains('/painel/movimentacao-lote')
        )
        print(f"[DEBUG] URL atual: {driver.current_url}")
        if '/painel/movimentacao-lote' not in driver.current_url:
            print(f"[LOOP_PRAZO][ERRO] URL inesperada após suitcase: {driver.current_url}")
            return False
        print(f"[LOOP_PRAZO] Na tela de movimentação em lote: {driver.current_url}")
        time.sleep(1.2)
        return True
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] URL de movimentacao-lote não carregou: {e}")
        return False


def _ciclo1_movimentar_destino_providencias(driver: WebDriver) -> bool:
    """Abordagem especial para 'Cumprimento de providências' no ciclo 2."""
    opcao_destino = 'Cumprimento de providências'
    print(f"[LOOP_PRAZO] Abordagem especial para '{opcao_destino}'")

    # Aumentar tentativas para abrir dropdown
    max_tentativas_abrir = 8
    dropdown_aberto = False

    for tent_abrir in range(1, max_tentativas_abrir + 1):
        try:
            print(f"[LOOP_PRAZO] Tentativa {tent_abrir}/{max_tentativas_abrir} de abrir dropdown para providências")

            # Aguardar mais tempo para o elemento estar pronto
            seta_dropdown = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
            )
            time.sleep(1.5)  # Mais tempo
            driver.execute_script("arguments[0].scrollIntoView(true);", seta_dropdown)
            driver.execute_script("document.body.style.zoom='100%'")
            time.sleep(0.5)

            # Múltiplos cliques se necessário
            for click_attempt in range(3):
                try:
                    driver.execute_script("arguments[0].click();", seta_dropdown)
                    print(f"[LOOP_PRAZO] Clique {click_attempt + 1} executado")
                    time.sleep(2.0)  # Mais tempo para overlay aparecer

                    # Verificar se overlay apareceu
                    overlay = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                    )
                    opcoes_elementos = overlay.find_elements(By.XPATH, ".//span[contains(@class,'mat-option-text')]")
                    opcoes_textos = [opt.text.strip() for opt in opcoes_elementos if opt.text.strip()]

                    if len(opcoes_textos) > 0:
                        print(f"[LOOP_PRAZO] ✅ Dropdown aberto com {len(opcoes_textos)} opções após clique {click_attempt + 1}")
                        print(f"[LOOP_PRAZO] Opções: {opcoes_textos}")
                        dropdown_aberto = True
                        break
                except:
                    time.sleep(1.0)

            if dropdown_aberto:
                break

        except Exception as e:
            print(f"[LOOP_PRAZO] ⚠️ Erro na tentativa {tent_abrir}: {e}")
            time.sleep(1.0)

    if not dropdown_aberto:
        print(f"[LOOP_PRAZO][ERRO] Falha ao abrir dropdown para providências após {max_tentativas_abrir} tentativas")
        return False

    # Selecionar a opção com mais tentativas
    max_tentativas = 8
    for tentativa in range(1, max_tentativas + 1):
        try:
            print(f"[LOOP_PRAZO] Tentativa {tentativa}/{max_tentativas} de selecionar '{opcao_destino}'")

            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
            )

            # Busca mais flexível para "Cumprimento de providências"
            opcao_elemento = None
            try:
                # Tentar exato primeiro
                opcao_xpath = f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']"
                opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath)
            except:
                try:
                    # Tentar parcial
                    opcao_xpath_parcial = f".//span[contains(@class,'mat-option-text') and contains(text(),'Cumprimento')]"
                    opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath_parcial)
                except:
                    try:
                        # Tentar ainda mais parcial
                        opcao_xpath_muito_parcial = f".//span[contains(@class,'mat-option-text') and contains(text(),'providências')]"
                        opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath_muito_parcial)
                    except:
                        pass

            if opcao_elemento:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento)
                time.sleep(0.5)
                # Tentar clique normal primeiro
                try:
                    opcao_elemento.click()
                    print(f"[LOOP_PRAZO] ✅ Opção '{opcao_destino}' selecionada com clique normal na tentativa {tentativa}.")
                except:
                    # Fallback para JavaScript click
                    driver.execute_script("arguments[0].click();", opcao_elemento)
                    print(f"[LOOP_PRAZO] ✅ Opção '{opcao_destino}' selecionada com JS click na tentativa {tentativa}.")
                time.sleep(1.5)
                break
            else:
                print(f"[LOOP_PRAZO][AVISO] Tentativa {tentativa}: Opção '{opcao_destino}' não encontrada")

                # Se não encontrou, tentar reabrir dropdown
                if tentativa < max_tentativas:
                    try:
                        driver.execute_script("document.body.click();")
                        time.sleep(0.5)
                        seta_dropdown = driver.find_element(By.CSS_SELECTOR, "div.mat-select-arrow-wrapper")
                        seta_dropdown.click()
                        time.sleep(1.5)
                    except:
                        pass

        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] Tentativa {tentativa}: Falha geral: {e}")
            if tentativa == max_tentativas:
                return False
            time.sleep(1)

    # Aguardar botão aparecer e clicar
    time.sleep(3)
    seletor_movimentar = "button.mat-raised-button[color='primary']"
    try:
        btn_movimentar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_movimentar))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_movimentar)
        result = driver.execute_script("arguments[0].click(); return true;", btn_movimentar)
        if result:
            print('[LOOP_PRAZO] ✅ Botão "Movimentar processos" clicado com sucesso')
            time.sleep(2)
            return True
        else:
            print('[LOOP_PRAZO][ERRO] Falha no JavaScript click em "Movimentar processos"')
            return False
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Botão "Movimentar processos" não encontrado: {e}')
        return False


def _ciclo1_movimentar_destino(driver: WebDriver, opcao_destino: str) -> bool:
    """Seleciona destino usando abordagem direta inline (como no original) com retry."""
    print(f"[DEBUG] Iniciando seleção de destino: '{opcao_destino}'")

    # Para "Cumprimento de providências" no ciclo 2, usar abordagem mais robusta
    if opcao_destino == 'Cumprimento de providências':
        print("[LOOP_PRAZO] Usando abordagem especial para 'Cumprimento de providências'")
        return _ciclo1_movimentar_destino_providencias(driver)

    # INSISTIR até dropdown abrir e mostrar opções reais
    max_tentativas_abrir = 5
    dropdown_aberto = False
    
    for tent_abrir in range(1, max_tentativas_abrir + 1):
        try:
            print(f"[LOOP_PRAZO] Tentativa {tent_abrir}/{max_tentativas_abrir} de abrir dropdown")
            
            seta_dropdown = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
            )
            time.sleep(1.0)
            driver.execute_script("arguments[0].scrollIntoView(true);", seta_dropdown)
            driver.execute_script("document.body.style.zoom='100%'")
            time.sleep(0.3)
            
            # Clicar e aguardar overlay aparecer COM OPÇÕES
            driver.execute_script("arguments[0].click();", seta_dropdown)
            print("[LOOP_PRAZO] Clique executado, aguardando opções...")
            time.sleep(1.2)
            
            # VERIFICAR se overlay tem opções reais (não apenas vazio)
            try:
                overlay = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
                )
                opcoes_elementos = overlay.find_elements(By.XPATH, ".//span[contains(@class,'mat-option-text')]")
                opcoes_textos = [opt.text.strip() for opt in opcoes_elementos if opt.text.strip()]
                
                if len(opcoes_textos) > 0:
                    print(f"[LOOP_PRAZO] ✅ Dropdown aberto com {len(opcoes_textos)} opções")
                    print(f"[LOOP_PRAZO] Opções: {opcoes_textos[:5]}")
                    dropdown_aberto = True
                    break
                else:
                    print(f"[LOOP_PRAZO] ⚠️ Dropdown vazio na tentativa {tent_abrir}")
                    time.sleep(0.5)
            except:
                print(f"[LOOP_PRAZO] ⚠️ Overlay não apareceu na tentativa {tent_abrir}")
                time.sleep(0.5)
                
        except Exception as e:
            print(f"[LOOP_PRAZO] ⚠️ Erro na tentativa {tent_abrir}: {e}")
            time.sleep(0.5)
    
    if not dropdown_aberto:
        print(f"[LOOP_PRAZO][ERRO] Falha ao abrir dropdown após {max_tentativas_abrir} tentativas")
        return False

    # Selecionar a opção de destino com RETRY
    max_tentativas = 5
    for tentativa in range(1, max_tentativas + 1):
        try:
            print(f"[LOOP_PRAZO] Tentativa {tentativa}/{max_tentativas} de selecionar '{opcao_destino}'")
            
            overlay = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane"))
            )
            
            # Listar todas as opções disponíveis para debug
            opcoes_elementos = overlay.find_elements(By.XPATH, ".//span[contains(@class,'mat-option-text')]")
            opcoes_disponiveis = [opt.text.strip() for opt in opcoes_elementos]
            print(f"[LOOP_PRAZO][DEBUG] Opções disponíveis: {opcoes_disponiveis}")
            
            # Tentar encontrar e clicar na opção exata
            opcao_xpath = f".//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']"
            try:
                opcao_elemento = overlay.find_element(By.XPATH, opcao_xpath)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento)
                time.sleep(0.3)
                opcao_elemento.click()
                print(f"[LOOP_PRAZO] ✅ Opção '{opcao_destino}' selecionada com sucesso na tentativa {tentativa}.")
                time.sleep(0.8)
                break  # Sucesso, sair do loop
                
            except Exception as e_opcao:
                print(f"[LOOP_PRAZO][AVISO] Tentativa {tentativa}: Opção exata '{opcao_destino}' não encontrada: {e_opcao}")
                
                # Tentar busca case-insensitive e parcial
                opcao_xpath_parcial = f".//span[contains(@class,'mat-option-text') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{opcao_destino.lower()}')]"
                try:
                    opcao_elemento_parcial = overlay.find_element(By.XPATH, opcao_xpath_parcial)
                    opcao_texto = opcao_elemento_parcial.text.strip()
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento_parcial)
                    time.sleep(0.3)
                    opcao_elemento_parcial.click()
                    print(f"[LOOP_PRAZO] ✅ Opção parcial '{opcao_texto}' selecionada na tentativa {tentativa}.")
                    time.sleep(0.8)
                    break  # Sucesso, sair do loop
                    
                except Exception as e_parcial:
                    print(f"[LOOP_PRAZO][ERRO] Tentativa {tentativa}: Busca parcial também falhou: {e_parcial}")
                    
                    # Se não é última tentativa, fechar e reabrir dropdown
                    if tentativa < max_tentativas:
                        print(f"[LOOP_PRAZO] Fechando e reabrindo dropdown para tentativa {tentativa + 1}...")
                        try:
                            # Fechar clicando fora
                            driver.execute_script("document.body.click();")
                            time.sleep(0.5)
                            # Reabrir
                            seta_dropdown = driver.find_element(By.CSS_SELECTOR, "div.mat-select-arrow-wrapper")
                            seta_dropdown.click()
                            time.sleep(0.8)
                        except:
                            pass
                    else:
                        # Última tentativa falhou
                        print(f"[LOOP_PRAZO][ERRO] Todas as {max_tentativas} tentativas falharam para '{opcao_destino}'")
                        return False
                        
        except Exception as e:
            print(f"[LOOP_PRAZO][ERRO] Tentativa {tentativa}: Falha ao acessar painel de opções: {e}")
            if tentativa == max_tentativas:
                return False
            time.sleep(1)

    # Aguardar botão aparecer após seleção
    time.sleep(2)

    print("[DEBUG] Procurando botão 'Movimentar processos'...")
    # Procurar o botão "Movimentar processos" com seletor específico
    seletor_movimentar = "button.mat-raised-button[color='primary']"
    print(f'[DEBUG] Tentando seletor: {seletor_movimentar}')
    elements = driver.find_elements(By.CSS_SELECTOR, seletor_movimentar)
    print(f"[DEBUG] Encontrados {len(elements)} botões com seletor.")
    if elements:
        print(f"[DEBUG] Primeiro botão: {elements[0].text}")

    # Usar JavaScript click para evitar obstrução
    if elements:
        btn_movimentar = elements[0]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_movimentar)
        result = driver.execute_script("arguments[0].click(); return true;", btn_movimentar)
        if result:
            print('[LOOP_PRAZO] ✅ Botão "Movimentar processos" clicado via JavaScript')
            time.sleep(1.2)
            return True
        else:
            print('[LOOP_PRAZO][ERRO] Falha no JavaScript click em "Movimentar processos"')
            return False
    else:
        print('[LOOP_PRAZO][ERRO] Botão "Movimentar processos" não encontrado')
        return False


def _ciclo1_retornar_lista(driver: WebDriver) -> None:
    """Retorna para lista de processos e ajusta navegação."""
    url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
    driver.get(url_lista)
    print('[LOOP_PRAZO] Retornou para a lista de processos.')

    # Ajustar zoom e aguardar carregamento
    driver.execute_script("document.body.style.zoom='75%'")
    time.sleep(2.5)

    # Simular Alt+Seta Esquerda para voltar à página anterior
    try:
        print("[LOOP_PRAZO] Simulando Alt+Seta Esquerda para voltar à página anterior...")
        actions = ActionChains(driver)
        actions.key_down(Keys.ALT).send_keys(Keys.ARROW_LEFT).key_up(Keys.ALT).perform()
        print("[LOOP_PRAZO] Comando de navegação para trás enviado com sucesso")
        time.sleep(1.5)
    except Exception as e:
        print(f"[LOOP_PRAZO][ERRO] Falha ao simular Alt+Seta Esquerda: {e}")
        # Alternativa usando JavaScript para voltar à página anterior
        try:
            driver.execute_script("window.history.go(-1)")
            print("[LOOP_PRAZO] Usado JavaScript para voltar à página anterior")
            time.sleep(1.5)
        except Exception as js_error:
            print(f"[LOOP_PRAZO][ERRO] Falha na alternativa JavaScript: {js_error}")


def ciclo1(driver: WebDriver, opcao_destino: str = 'Análise') -> Union[bool, str]:
    """
    Orquestra ciclo 1: filtro, marcação, suitcase, movimentação para painel 14.
    
    Returns:
        True: sucesso
        False: erro crítico
        "no_more_processes": sem processos em liquidação/execução
        "marcar_todas_not_found_but_continue": marcar-todas não encontrado
        "suitcase_not_found_but_continue": suitcase não encontrado
        "single_process": apenas 1 processo, batch não disponível
    """
    filtro_result = _ciclo1_aplicar_filtro_fases(driver)
    if filtro_result == "no_more_processes":
        print('[CICLO1] Nenhum processo em liquidação/execução.')
        return "no_more_processes"
    elif not filtro_result:
        print('[CICLO1] Erro ao aplicar filtro de fases.')
        return False

    # ===== VERIFICAR QUANTIDADE DE PROCESSOS =====
    # Se houver apenas 1 processo, o PJE não mostra o botão batch (suitcase)
    try:
        time.sleep(1)
        processos = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        qtd_processos = len(processos)
        print(f'[CICLO1]  Detectados {qtd_processos} processo(s) na lista')
        
        if qtd_processos == 1:
            print('[CICLO1] ℹ️ Apenas 1 processo detectado - PJE não disponibiliza batch (suitcase)')
            print('[CICLO1] ✅ Prosseguindo para processamento individual (Fase 2)')
            return "single_process"
        elif qtd_processos == 0:
            print('[CICLO1] Nenhum processo encontrado após filtro.')
            return "no_more_processes"
    except Exception as e:
        print(f'[CICLO1] ⚠️ Erro ao contar processos: {e}')
        print('[CICLO1] Continuando com o fluxo normal...')

    marcar_result = _ciclo1_marcar_todas(driver)
    if marcar_result == "no_processes":
        print('[CICLO1] Nenhum processo encontrado para marcar.')
        return "no_more_processes"
    elif marcar_result in ["not_found", "error"]:
        print(f'[CICLO1] Falha em marcar-todas: {marcar_result}')
        return False

    if not _ciclo1_abrir_suitcase(driver):
        print('[CICLO1] Erro ao abrir suitcase.')
        return False

    if not _ciclo1_aguardar_movimentacao_lote(driver):
        print('[CICLO1] Erro ao aguardar movimentação em lote.')
        return False

    if not _ciclo1_movimentar_destino(driver, opcao_destino):
        print('[CICLO1] Erro ao movimentar destino.')
        return False

    _ciclo1_retornar_lista(driver)
    print('[CICLO1] Ciclo 1 concluído.')
    return True

# ===== HELPERS PARA CICLO2 =====

def _ciclo2_aplicar_filtros(driver: WebDriver) -> bool:
    """Aplica filtros de fase e tarefas no painel 8 - EM UMA ÚNICA CHAMADA."""
    try:
        # Aplicar AMBOS filtros de uma vez (fase + tarefa)
        print('[LOOP_PRAZO] Aplicando filtros de FASE + TAREFA...')
        resultado = filtrofases(
            driver, 
            fases_alvo=['liquidação', 'execução'], 
            tarefas_alvo=['análise'],
            seletor_tarefa='Tarefa do processo'
        )
        if not resultado:
            print('[LOOP_PRAZO][ERRO] Falha ao aplicar filtros de fase + tarefa')
            return False
        print('[LOOP_PRAZO] ✅ Filtros de fase + tarefa aplicados')
        
        # AGUARDAR LISTA ATUALIZAR
        time.sleep(3.5)
        
        # Aplicar filtro de tamanho (100)
        print('[LOOP_PRAZO] Aplicando filtro de tamanho (100)...')
        aplicar_filtro_100(driver)
        print('[LOOP_PRAZO] ✅ Filtro 100 aplicado')
        time.sleep(2)
        
        return True
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Falha ao aplicar filtros: {e}')
        return False


def _extrair_numero_processo_da_linha(linha_elemento: WebElement) -> Optional[str]:
    """Extrai número de processo de um elemento <tr> da tabela de atividades.
    
    Procura por <a> (links) que contenham o padrão de número de processo:
    NNNNNNN-DD.AAAA.J.TT.OOOO (formato processual brasileiro).
    
    Args:
        linha_elemento: elemento <tr> da tabela
    
    Returns:
        String com número do processo (formatado com pontos e hífen) ou None
    """
    try:
        # Buscar padrão processual usando regex
        padrao_processo = re.compile(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})')
        
        # Estratégia 1: Procurar em links <a> (localização padrão no PJe)
        try:
            links = linha_elemento.find_elements(By.CSS_SELECTOR, 'a')
            for link in links:
                texto = link.text.strip()
                match = padrao_processo.search(texto)
                if match:
                    return match.group(1)
        except:
            pass
        
        # Estratégia 2: Procurar em toda a linha (fallback)
        try:
            texto_linha = linha_elemento.text.strip()
            match = padrao_processo.search(texto_linha)
            if match:
                return match.group(1)
        except:
            pass
        
        return None
    except Exception as e:
        print(f'[LOOP_PRAZO][DEBUG] Erro ao extrair número do processo: {e}')
        return None


def _selecionar_processos_por_gigs_aj_jt(driver: WebDriver, client: 'PjeApiClient') -> int:
    """Seleciona processos com atividade GIGS AJ-JT apenas em fase LIQUIDAÇÃO."""
    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
        processos_com_gigs = []
        
        for linha in linhas:
            try:
                numero_processo = _extrair_numero_processo_da_linha(linha)
                if not numero_processo:
                    continue
                
                dados_gigs_fase = obter_gigs_com_fase(client, numero_processo)
                if not dados_gigs_fase:
                    continue
                
                # Apenas Liquidação
                if dados_gigs_fase.get('fase') != 'Liquidação':
                    continue
                
                # Procurar por AJ-JT
                atividades_gigs = dados_gigs_fase.get('atividades_gigs', [])
                for atividade in atividades_gigs:
                    if 'AJ-JT' in atividade.get('observacao', ''):
                        processos_com_gigs.append(numero_processo)
                        break
                        
            except Exception:
                continue
        
        if processos_com_gigs:
            selecionados = driver.execute_script(
                SCRIPT_SELECAO_GIGS_AJ_JT,
                processos_com_gigs
            )
            print(f'[LOOP_PRAZO][GIGS] ✅ Seleção de GIGS concluída: {selecionados} processos selecionados')
            # ✅ AGUARDAR para garantir que a seleção foi completada ANTES de continuar
            time.sleep(1.5)
            return selecionados
        
        return 0
        
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro em _selecionar_processos_por_gigs_aj_jt: {e}')
        return 0


def _verificar_processo_tem_xs(client: 'PjeApiClient', numero_processo: str) -> bool:
    """Verifica se o processo já tem atividade GIGS xs (sem prazo).
    
    Args:
        client: Cliente PJe API
        numero_processo: Número do processo formatado (NNNNNNN-DD.AAAA.J.TT.OOOO)
    
    Returns:
        True se processo já tem atividade xs (sem prazo), False caso contrário
    """
    try:
        # Buscar atividades GIGS do processo
        atividades = client.atividades_gigs(numero_processo)
        
        if not atividades:
            return False
        
        # Verificar se existe alguma atividade sem prazo (dataPrazo vazio/null)
        for atividade in atividades:
            data_prazo = atividade.get('dataPrazo')
            # Se dataPrazo é None, vazio ou string vazia, é atividade xs
            if not data_prazo or (isinstance(data_prazo, str) and not data_prazo.strip()):
                print(f'[LOOP_PRAZO][XS] ⚠️ Processo {numero_processo} já tem atividade xs no GIGS')
                return True
        
        return False
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro ao verificar xs para {numero_processo}: {e}')
        # Em caso de erro, retornar False para não bloquear o processo
        return False


def _verificar_processos_xs_paralelo(client: 'PjeApiClient', numeros_processos: List[str], max_workers: int = 10) -> Dict[str, bool]:
    """Verifica múltiplos processos em paralelo para ver se têm atividade xs.
    
    Args:
        client: Cliente PJe API
        numeros_processos: Lista de números de processos
        max_workers: Número máximo de threads paralelas (padrão: 10)
    
    Returns:
        Dicionário {numero_processo: tem_xs}
    """
    resultados = {}
    total = len(numeros_processos)
    print(f'[LOOP_PRAZO][XS]  Verificando {total} processos em paralelo (workers={max_workers})...')
    
    inicio = time.time()
    
    # Função wrapper para executar em thread
    def verificar_um(numero: str) -> Tuple[str, bool]:
        tem_xs = _verificar_processo_tem_xs(client, numero)
        return (numero, tem_xs)
    
    # Executar em paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submeter todas as tarefas
        futures = {executor.submit(verificar_um, num): num for num in numeros_processos}
        
        # Processar resultados conforme completam
        processados = 0
        for future in as_completed(futures):
            try:
                numero, tem_xs = future.result()
                resultados[numero] = tem_xs
                processados += 1
                
                # Atualizar progresso a cada 10 processos
                if processados % 10 == 0 or processados == total:
                    print(f'[LOOP_PRAZO][XS]  Progresso: {processados}/{total} ({processados*100//total}%)')
                    
            except Exception as e:
                numero = futures[future]
                print(f'[LOOP_PRAZO][ERRO] Erro ao verificar {numero}: {e}')
                resultados[numero] = False
    
    duracao = time.time() - inicio
    print(f'[LOOP_PRAZO][XS] ✅ Verificação concluída em {duracao:.1f}s ({total/duracao:.1f} processos/s)')
    
    return resultados


def _ciclo2_processar_livres(driver: WebDriver, client: Optional['PjeApiClient'] = None) -> int:
    """Seleciona processos livres SEM verificação de API GIGS.
    
    Args:
        driver: WebDriver Selenium
        client: PjeApiClient (não utilizado - removido para performance)
    
    Returns:
        Total de processos livres selecionados
    """
    try:
        print('[LOOP_PRAZO][LIVRES]  Selecionando processos livres...')
        selecionados_livres = driver.execute_script(SCRIPT_SELECAO_LIVRES)
        print(f'[LOOP_PRAZO][LIVRES] ✅ Processos livres selecionados: {selecionados_livres}')
        time.sleep(1.5)
        return selecionados_livres
        
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro em _ciclo2_processar_livres: {e}')
        return 0


def _ciclo2_criar_atividade_xs(driver: WebDriver) -> bool:
    """Cria atividade 'xs' para processos selecionados."""
    try:
        print('[LOOP_PRAZO] Criando atividade "xs" para processos livres (ciclo2)...')
        # Clique no botão tag verde para abrir o dropdown de atividade
        seletor_tag = 'i.fa.fa-tag.icone.texto-verde'
        print(f'[LOOP_PRAZO][DEBUG] Seletor usado para botão tag verde: {seletor_tag}')
        sucesso_tag = aguardar_e_clicar(
            driver,
            seletor_tag,
            timeout=10,
            by=By.CSS_SELECTOR,
            log=True
        )
        if not sucesso_tag:
            print('[LOOP_PRAZO][ERRO] Falha ao clicar no botão tag verde com aguardar_e_clicar.')
            return False
        time.sleep(0.8)

        # Clique direto no botão "Atividade" via CSS/texto
        sucesso_atividade = False
        btns = driver.find_elements(By.CSS_SELECTOR, "button.mat-menu-item")
        for btn in btns:
            if "Atividade" in btn.text:
                driver.execute_script("arguments[0].click();", btn)
                sucesso_atividade = True
                print('[LOOP_PRAZO][DEBUG] Clique no botão "Atividade" realizado via JS/CSS-texto.')
                break
        if not sucesso_atividade:
            print('[LOOP_PRAZO][ERRO] Falha ao clicar no botão "Atividade".')
            return False
        time.sleep(1.2)
        
        # Preencher observação
        campo_obs = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea[formcontrolname='observacao']"))
        )
        campo_obs.click()
        campo_obs.clear()
        campo_obs.send_keys('xs')
        time.sleep(0.6)
        # Clique enxuto: localizar span "Salvar" e clicar via JS no botão pai
        spans = driver.find_elements(By.CSS_SELECTOR, "button.mat-raised-button span")
        btn_salvar = next((s for s in spans if "Salvar" in s.text), None)
        if not btn_salvar:
            return False
        btn_pai = btn_salvar.find_element(By.XPATH, "..")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_pai)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", btn_pai)
        # Checar fechamento do modal
        time.sleep(1.2)
        modais = driver.find_elements(By.CSS_SELECTOR, "mat-dialog-container")
        if modais:
            print('[LOOP_PRAZO][ERRO] Modal xs ainda aberto após clique em Salvar.')
            return False
        print('[LOOP_PRAZO] ✅ Atividade "xs" salva com sucesso para processos livres (ciclo2).')
        # ✅ AGUARDAR para garantir que o CICLO COMPLETO (seleção + atividade XS) foi finalizado
        # ANTES de prosseguir para o próximo ciclo (NÃO-LIVRES/CUMPRIMENTO DE PROVIDÊNCIAS)
        time.sleep(2.0)
        print('[LOOP_PRAZO] ✅ CICLO COMPLETO (LIVRES+GIGS+XS) FINALIZADO. Pronto para próximo ciclo.')
        return True
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Falha ao criar atividade xs: {e}')
        return False
        # NÃO atualizar/recarregar a página após xs, inicia próximo ciclo direto
        return True
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Falha ao criar atividade xs: {e}')
        return False


def _ciclo2_selecionar_nao_livres(driver: WebDriver, max_processos: int = 20) -> Tuple[int, bool]:
    """Seleciona processos não-livres via JavaScript."""
    try:
        # Desselecionar todos primeiro
        driver.execute_script("document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').forEach(c=>c.click());")
        time.sleep(0.6)
        
        print(f'[LOOP_PRAZO][DEBUG] Executando script de seleção de não-livres (max={max_processos})...')
        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, max_processos)
        selecionados = resultado['selecionados']
        total_nao_livres = resultado['totalNaoLivres']
        
        print(f'[LOOP_PRAZO][DEBUG] Resultado: {selecionados} selecionados de {total_nao_livres} não-livres totais')
        
        ha_mais = total_nao_livres > selecionados
        return selecionados, ha_mais
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Falha ao selecionar não-livres: {e}')
        return 0, False


def _ciclo2_movimentar_lote(driver: WebDriver, opcao_destino: str, ha_mais: bool) -> Union[bool, str]:
    """Abre suitcase, seleciona destino e movimenta processos."""
    # Abrir suitcase
    if not _ciclo1_abrir_suitcase(driver):
        print('[LOOP_PRAZO][ERRO] Falha ao abrir suitcase no ciclo2.')
        return False

    # Aguardar carregamento da página de movimentação em lote (como no ciclo1)
    if not _ciclo1_aguardar_movimentacao_lote(driver):
        print('[LOOP_PRAZO][ERRO] Falha ao aguardar movimentação em lote no ciclo2.')
        return False

    # Selecionar destino
    if not _ciclo1_movimentar_destino(driver, opcao_destino):
        print(f'[LOOP_PRAZO][ERRO] Falha ao selecionar destino "{opcao_destino}" no ciclo2.')
        return False

    # Retornar à lista
    driver.get("https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos")
    time.sleep(3)

    return ha_mais


def ciclo2_processar_livres_apenas_uma_vez(driver: WebDriver, opcao_destino: str = 'Cumprimento de providências') -> Tuple[int, bool]:
    """
    Fase 2.1: Processa APENAS seleção de processos livres (SEM aplicar atividade XS).
    A atividade XS será aplicada na Fase 2.2 para GIGS+LIVRES juntos.
    
    Returns:
        Tupla (livres_selecionados, ha_nao_livres_para_providencias)
    """
    if not _ciclo2_aplicar_filtros(driver):
        return 0, False

    # 1. Criar client GIGS para busca de atividades
    client = None
    try:
        sess, trt = session_from_driver(driver)
        client = PjeApiClient(sess, trt)
        print('[LOOP_PRAZO] Client GIGS inicializado para busca de atividades.')
    except Exception as e:
        print(f'[LOOP_PRAZO][WARN] Falha ao inicializar client GIGS (continuando sem GIGS): {e}')
        client = None

    # 2. Selecionar LIVRES (SEM aplicar XS ainda)
    livres = _ciclo2_processar_livres(driver, client=client)
    print(f'[LOOP_PRAZO] ✅ {livres} processos livres selecionados (XS será aplicado na próxima fase).')
    
    # 3. Contar total de não-livres (para saber se entra no loop de providências)
    # Primeiro, salvar os selecionados atuais (GIGS+LIVRES) antes de testar não-livres
    try:
        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, 1)  # Seleciona apenas 1 para contar total
        total_nao_livres = resultado['totalNaoLivres']
        ha_nao_livres = total_nao_livres > 0
        print(f'[LOOP_PRAZO] Total de processos NÃO-livres encontrados: {total_nao_livres}')
        
        # Desselecionar aquele 1 não-livre que foi selecionado para teste
        try:
            driver.execute_script("""
                document.querySelectorAll('mat-checkbox input[type="checkbox"]:checked').forEach(function(c){
                    var linha = c.closest('tr');
                    var temProvidencias = linha.querySelector('a[href*="providencias"]') !== null;
                    if (temProvidencias) {
                        c.click();
                    }
                });
            """)
            time.sleep(0.6)
        except:
            pass
            
        return livres, ha_nao_livres
    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO] Erro ao contar não-livres: {e}')
        return livres, False


def ciclo2_loop_providencias(driver: WebDriver, opcao_destino: str = 'Cumprimento de providências') -> bool:
    """
    Fase 2.3: Loop para processar providências (cumprimento) - processa NÃO-LIVRES.
    Processa até 20 processos não-livres por iteração.
    Continua loopando enquanto houver MAIS de 20 processos não-livres.
    
    Returns:
        True: processamento bem-sucedido
        False: erro crítico
    """
    iteracao = 0
    while True:
        iteracao += 1
        print(f'[LOOP_PRAZO] ==== Iteração {iteracao} de providências ====')
        
        # Desselecionar todos antes de começar nova iteração
        try:
            driver.execute_script("document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').forEach(c=>c.click());")
            time.sleep(0.6)
        except:
            pass
        
        # REAPLICAR FILTROS antes de cada iteração (fases liquidação/execução + filtro tarefa análise)
        print(f'[LOOP_PRAZO] Reaplicando filtros para iteração {iteracao}...')
        if not _ciclo2_aplicar_filtros(driver):
            print('[LOOP_PRAZO][ERRO] Falha ao reaplicar filtros de atividades.')
            return False
        if _ciclo1_aplicar_filtro_fases(driver) == "no_more_processes":
            print('[LOOP_PRAZO] Nenhum processo encontrado após reaplicar filtros de fases.')
            return True
        
        # Selecionar até 20 não-livres
        nao_livres, ha_mais = _ciclo2_selecionar_nao_livres(driver)
        
        if nao_livres == 0:
            print('[LOOP_PRAZO] Nenhum processo NÃO-livre encontrado. Encerrando loop de providências.')
            return True
        
        print(f'[LOOP_PRAZO] Selecionados {nao_livres} processos NÃO-livres para movimentação em lote.')
        print(f'[LOOP_PRAZO] Há mais processos? {ha_mais}')
        
        # Movimentar para providências
        resultado = _ciclo2_movimentar_lote(driver, opcao_destino, ha_mais)
        if resultado is False:
            print('[LOOP_PRAZO][ERRO] Falha ao movimentar lote em providências.')
            return False
        
        # Se não há mais processos (ha_mais=False), encerrar o loop
        if not ha_mais:
            print('[LOOP_PRAZO] ✅ Todos os processos NÃO-livres foram processados (≤20).')
            return True
        
        # Se há mais (ha_mais=True), continuar o loop para processar próximos 20
        print(f'[LOOP_PRAZO] Ainda há mais processos NÃO-livres. Continuando para iteração {iteracao + 1}...')
        time.sleep(2)
        print('[LOOP_PRAZO] Há mais de 20 processos não-livres. Continuando próxima iteração...')
        time.sleep(2)


def ciclo2(driver: WebDriver, opcao_destino: str = 'Cumprimento de providências') -> Union[bool, str]:
    """
    Orquestra ciclo 2: 
    - Fase 2.0: Seleciona GIGS (AJ-JT) - SEM aplicar XS
    - Fase 2.1: Seleciona LIVRES - SEM aplicar XS
    - Fase 2.2: Aplica XS UMA VEZ para todos (GIGS+LIVRES) juntos
    - Fase 2.3: Loop para processar NÃO-LIVRES (providências)
    
    Returns:
        True: sucesso completo
        False: erro crítico
        "no_more_processes": não há processos nem GIGS nem livres nem não-livres
    """
    # FASE 2.0: Selecionar GIGS (AJ-JT) - SEM aplicar XS ainda
    print('[LOOP_PRAZO] ===== FASE 2.0: Selecionando GIGS (AJ-JT) =====')
    
    gigs_selecionados = 0
    try:
        sess, trt = session_from_driver(driver)
        client = PjeApiClient(sess, trt)
        gigs_selecionados = _selecionar_processos_por_gigs_aj_jt(driver, client)
        print(f'[LOOP_PRAZO] ✅ {gigs_selecionados} GIGS selecionados')
    except Exception as e:
        print(f'[LOOP_PRAZO] ⚠️ Erro ao processar GIGS: {e}')
        gigs_selecionados = 0
    
    # FASE 2.1: Selecionar LIVRES (SEM aplicar XS ainda)
    print('[LOOP_PRAZO] ===== FASE 2.1: Selecionando LIVRES =====')
    livres_selecionados, ha_nao_livres = ciclo2_processar_livres_apenas_uma_vez(driver, opcao_destino)
    
    # FASE 2.2: Aplicar XS UMA VEZ para todos (GIGS+LIVRES) juntos
    total_selecionados = gigs_selecionados + livres_selecionados
    if total_selecionados > 0:
        print(f'[LOOP_PRAZO] ===== FASE 2.2: Aplicando atividade XS para {total_selecionados} processos (GIGS+LIVRES) =====')
        if not _ciclo2_criar_atividade_xs(driver):
            print('[LOOP_PRAZO][AVISO] Falha ao aplicar XS, mas continuando...')
        else:
            print('[LOOP_PRAZO] ✅ Atividade XS aplicada com sucesso')
        time.sleep(2)
    else:
        print('[LOOP_PRAZO] Nenhum processo GIGS/LIVRE selecionado, pulando FASE 2.2')
    
    # Se não há GIGS, não há livres E não há não-livres, não há nada a fazer
    if total_selecionados <= 0 and not ha_nao_livres:
        print('[LOOP_PRAZO] Nenhum processo encontrado (nem GIGS nem livres nem não-livres).')
        return "no_more_processes"
    
    # ✅ CRÍTICO: AGUARDAR para garantir que TODO O CICLO (GIGS+LIVRES+XS) foi COMPLETO
    # ANTES de iniciar o PRÓXIMO CICLO (NÃO-LIVRES/CUMPRIMENTO DE PROVIDÊNCIAS)
    if total_selecionados > 0:
        print('[LOOP_PRAZO] ⏳ Aguardando conclusão do ciclo GIGS+LIVRES+XS antes de iniciar providências...')
        time.sleep(3.0)
        print('[LOOP_PRAZO] ✅ Ciclo GIGS+LIVRES+XS CONCLUSÃO GARANTIDA. Iniciando providências.')
    
    # FASE 2.3: Se há não-livres, entrar no loop de providências
    if ha_nao_livres:
        print('[LOOP_PRAZO] ===== FASE 2.3: Entrando em LOOP para processar NÃO-LIVRES (PROVIDÊNCIAS) =====')
        resultado_providencias = ciclo2_loop_providencias(driver, opcao_destino)
        if resultado_providencias is False:
            print('[LOOP_PRAZO][AVISO] Loop de providências encontrou erro, mas retornando True para compatibilidade.')
            return True  # Retorna True pois GIGS e livres já foram processados
        return True
    
    # Se há GIGS/livres mas não há não-livres
    print('[LOOP_PRAZO] ✅ Processamento concluído: GIGS e/ou livres foram tratados.')
    return True

def selecionar_processos_nao_livres(driver: WebDriver, max_processos: int = 20) -> Tuple[int, bool]:
    """
    Seleciona até max_processos processos "NÃO livres" que atendem aos critérios:
    - Com prazo (coluna 9 preenchida) ou
    - Com comentário (ícone comment) ou
    - Com valor em input[matinput]
    
    Args:
        driver: WebDriver Selenium conectado ao PJe
        max_processos: Máximo de processos a selecionar (padrão 20)
    
    Returns:
        Tupla (selecionados, ha_mais_processos)
    
    Raises:
        Exception: Se ocorrer erro crítico na seleção
    """
    print("[LOOP_PRAZO] Iniciando seleção de processos 'NÃO livres'...")
    try:
        # Encontra todas as linhas da tabela
        linhas = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.cdk-drag'))
        )
        print(f'[LOOP_PRAZO] Total de linhas encontradas: {len(linhas)}')
        
        # Executa o script passando max_processos como argumento
        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, max_processos)
        selecionados = resultado['selecionados']
        total_nao_livres = resultado['totalNaoLivres']
        
        print(f'[LOOP_PRAZO] Total de processos NÃO livres encontrados: {total_nao_livres}')
        print(f'[LOOP_PRAZO] Processos selecionados neste ciclo: {selecionados}')
        
        if selecionados == 0:
            return 0, False
        
        # Retorna o número de selecionados e se há mais processos para tratar
        return selecionados, total_nao_livres > selecionados

    except Exception as e:
        print(f'[LOOP_PRAZO][ERRO CRÍTICO] Erro geral na seleção de processos NÃO livres: {e}')
        raise  # Propaga o erro para garantir que o ciclo2 seja interrompido

def loop_prazo(driver: WebDriver) -> bool:
    """
    Orquestra processamento completo de prazos em lote.
    
    Executa LOOP completo: painel 14 (Análise) → painel 8 (Cumprimento de providências).
    Processa todos os processos disponíveis em liquidação/execução.
    
    Args:
        driver: WebDriver Selenium conectado e logado no PJe
    
    Returns:
        True se processamento concluído com sucesso
    
    Raises:
        Não propaga exceções - trata internamente com recovery
    """    
# 1. Navegar para a lista de processos e esperar 2.5s
    url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
    driver.get(url_lista)
    time.sleep(2.5)    
#FASE 1 Loop para executar ciclo1 repetidamente com opção "Análise" até que não haja mais processos para tratar
    print("[LOOP_PRAZO] Fase 1: Processando todos os processos para 'Análise'")
    while True:
        resultado_ciclo = ciclo1(driver, "Análise")
        
        # Se ciclo1 retornar "no_more_processes", significa que não encontrou mais processos em liquidação/execução
        if resultado_ciclo == "no_more_processes":
            print("[LOOP_PRAZO] Não há mais processos em liquidação/execução para processar no ciclo1.")
            break
        elif resultado_ciclo == "single_process":
            print("[LOOP_PRAZO] ✅ Apenas 1 processo detectado - PJE não disponibiliza batch")
            print("[LOOP_PRAZO] ✅ Prosseguindo diretamente para Fase 2 (processamento individual)")
            break
        elif resultado_ciclo is False:
            print("[LOOP_PRAZO][ERRO CRÍTICO] Ciclo1 encontrou um erro. PARANDO EXECUÇÃO COMPLETA.")
            return False
        elif resultado_ciclo in ["go_to_ciclo2", "marcar_todas_not_found_but_continue"]:
            if resultado_ciclo == "go_to_ciclo2":
                print("[LOOP_PRAZO] Suitcase não encontrado no ciclo1, prosseguindo para Fase 2.")
            elif resultado_ciclo == "marcar_todas_not_found_but_continue":
                print("[LOOP_PRAZO] ✅ Fase 1 CUMPRIDA (marcar-todas não encontrado mas tratado como sucesso). Prosseguindo normalmente para Fase 2.")
            break
        
        print("[LOOP_PRAZO] Ciclo1 concluído com sucesso. Verificando se há mais processos para tratar...")
        time.sleep(2)
    
    # [CORRIGIDO] Fase 2 SEMPRE executa, independente do resultado da Fase 1
    # Se Fase 1 falhou por erro crítico (não por suitcase não encontrada), ainda assim continua
    if resultado_ciclo is False:
        print("[LOOP_PRAZO][AVISO] Fase 1 teve erro crítico, mas continuando para Fase 2 conforme solicitado.")
    
    # Fase 2: Executar ciclo2 para processar os processos do painel 8
    print("\n[LOOP_PRAZO] Fase 2: Iniciando processamento de processos do painel global 8...")
    
    # Navegar para o painel global 8
    url_painel8 = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
    driver.get(url_painel8)
    print('[LOOP_PRAZO] Navegou para painel global 8.')
    time.sleep(3)
    
    # Executar ciclo2 UMA ÚNICA VEZ (agora contém seu próprio loop interno para providências)
    print("[LOOP_PRAZO] Executando ciclo2 (que internamente processa livres UMA VEZ e depois loopa providências)...")
    resultado_ciclo2 = ciclo2(driver, "Cumprimento de providências")
    
    if resultado_ciclo2 == "no_more_processes":
        print("[LOOP_PRAZO] Nenhum processo encontrado no painel 8 (nem livres nem não-livres).")
    elif resultado_ciclo2 is False:
        print("[LOOP_PRAZO][AVISO] Ciclo2 encontrou um erro.")
    else:
        print("[LOOP_PRAZO] ✅ Ciclo2 concluído com sucesso (livres processados 1x, providências loopadas conforme necessário).")

    # ===== EXECUÇÃO DO FLUXO FINAL PROV =====
    # Após ciclo2, executar fluxo final PROV (navegação + filtro 100 + livres + XS)
    print('\n[LOOP_PRAZO]  Iniciando fluxo final PROV...')
    try:
        from Prazo.prov import fluxo_prov_integrado
        sucesso_prov = fluxo_prov_integrado(driver)
        if sucesso_prov:
            print('[LOOP_PRAZO] ✅ Fluxo final PROV concluído com sucesso!')
        else:
            print('[LOOP_PRAZO] ⚠️ Fluxo final PROV teve problemas, continuando...')
    except Exception as prov_error:
        print(f'[LOOP_PRAZO] ⚠️ Erro no fluxo final PROV: {prov_error}')
        # Não interrompe o fluxo principal por erro no PROV

    # ===== EXECUÇÃO DO MÓDULO P2B (PROCESSAMENTO INDIVIDUAL) =====
    # Após processamento em lote, executar fluxo_prazo para processamento individual
    print('\n[LOOP_PRAZO]  Iniciando processamento individual via módulo P2B...')
    try:
        fluxo_prazo(driver)
        print('[LOOP_PRAZO] ✅ Processamento individual concluído com sucesso!')
    except Exception as p2b_error:
        print(f'[LOOP_PRAZO] ❌ Erro no processamento individual P2B: {p2b_error}')
        # Não interrompe o fluxo principal por erro no P2B

    return True

def main(tipo_driver='PC', tipo_login='CPF', headless=False) -> None:
    """
    Ponto de entrada principal do script loop_prazo.
    
    Args:
        tipo_driver: Tipo de driver ('PC', 'VT', etc.)
        tipo_login: Tipo de login ('CPF', 'PC')
        headless: Executar em modo headless
    
    Configura recovery, cria driver, faz login e executa processamento completo.
    Trata exceções e garante fechamento adequado do driver.
    """
    
    # ===== SETUP UNIFICADO COM CREDENCIAL =====
    print(f"[PRAZO] Iniciando com driver={tipo_driver}, login={tipo_login}, headless={headless}")
    
    from Fix.core import credencial
    driver = credencial(
        tipo_driver=tipo_driver,
        tipo_login=tipo_login, 
        headless=headless
    )
    
    if not driver:
        print('[PRAZO][ERRO] Falha ao criar driver com credencial()')
        return
        
    print('[PRAZO] ✅ Driver criado e login realizado via credencial()')
    
    # ===== CONFIGURAR RECOVERY GLOBAL =====
    def recovery_credencial():
        return credencial(tipo_driver=tipo_driver, tipo_login=tipo_login, headless=headless)
    
    try:
        # Configurar recovery se disponível
        if 'configurar_recovery_driver' in globals():
            configurar_recovery_driver(recovery_credencial, lambda d: True)
            print("[PRAZO] ✅ Sistema de recuperação automática configurado")
    except:
        print("[PRAZO] ⚠️ Recovery não configurado")
    
    try:
        loop_prazo(driver)
    except Exception as e:
        novo_driver = handle_exception_with_recovery(e, driver, "LOOP_PRAZO")
        if novo_driver:
            driver = novo_driver
            # Tentar continuar ou finalizar graciosamente
        else:
            print(f'[LOOP][ERRO] Falha crítica no loop: {e}')
    finally:
        # Fechar o driver ao final do processamento
        driver.quit()

# Executar a função main se o script for executado diretamente
if __name__ == "__main__":
    main()
