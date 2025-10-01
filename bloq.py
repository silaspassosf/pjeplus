import time
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium import webdriver
import re
import subprocess
import tempfile
import os

# =================================================================
# FUNÇÕES AUXILIARES
# =================================================================

def _extrair_ordens_da_serie(driver, log=True):
    """Extrai ordens da página de detalhes da série"""
    ordens = []
    try:
        tabela = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody"))
        )
        
        linhas = tabela.find_elements(By.CSS_SELECTOR, "tr.mat-row")
        meses = {
            "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
            "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12
        }
        
        for linha in linhas:
            try:
                cols = linha.find_elements(By.CSS_SELECTOR, "td")
                sequencial = int(cols[0].text.strip())
                data_txt = cols[2].text.strip()
                protocolo = cols[5].text.strip()
                valor_txt = cols[4].text.strip()

                # Converter data
                data_ordem = None
                # Suporte ao formato 'dd/mm/yyyy, HH:MM'
                if "/" in data_txt:
                    partes = data_txt.split(",")
                    data_parte = partes[0].strip() if len(partes) > 0 else data_txt.strip()
                    hora_parte = partes[1].strip() if len(partes) > 1 else None
                    data_split = data_parte.split("/")
                    if len(data_split) == 3:
                        try:
                            dia, mes, ano = map(int, data_split)
                            if hora_parte:
                                hora_min = hora_parte.split(":")
                                if len(hora_min) == 2:
                                    hora, minuto = map(int, hora_min)
                                    data_ordem = datetime(ano, mes, dia, hora, minuto)
                                else:
                                    data_ordem = datetime(ano, mes, dia)
                            else:
                                data_ordem = datetime(ano, mes, dia)
                        except Exception as e:
                            if log:
                                print(f"[SISBAJUD] Ignorando ordem: data/hora inválida '{data_txt}' - {e}")
                            continue
                    else:
                        if log:
                            print(f"[SISBAJUD] Ignorando ordem: data com formato inesperado '{data_txt}'")
                        continue
                else:
                    partes = data_txt.split()
                    if len(partes) == 3:
                        try:
                            dia = int(partes[0])
                            mes_abr = partes[1].upper()
                            ano = int(partes[2])
                            mes = meses.get(mes_abr)
                            if not mes:
                                if log:
                                    print(f"[SISBAJUD] Ignorando ordem: mês inválido '{mes_abr}' em '{data_txt}'")
                                continue
                            data_ordem = datetime(ano, mes, dia)
                        except Exception as e:
                            if log:
                                print(f"[SISBAJUD] Ignorando ordem: data inválida '{data_txt}' - {e}")
                            continue
                    else:
                        if log:
                            print(f"[SISBAJUD] Ignorando ordem: data com formato inesperado '{data_txt}'")
                        continue

                if not data_ordem:
                    continue

                # Converter valor
                try:
                    valor = float(valor_txt.replace("R$", "")
                                   .replace("\u00a0", "")
                                   .replace(".", "")
                                   .replace(",", ".")
                                   .strip())
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] Ignorando ordem: valor inválido '{valor_txt}' - {e}")
                    continue

                ordens.append({
                    "sequencial": sequencial,
                    "data": data_ordem,
                    "valor_bloquear": valor,
                    "protocolo": protocolo,
                    "linha_el": linha
                })

                if log:
                    print(f"[SISBAJUD] Ordem {sequencial}: Data={data_ordem.strftime('%d/%m/%Y')}, Valor=R$ {valor:.2f}")

            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Ignorando linha: erro inesperado - {e}")
                continue
        
        # Ordenar por data
        ordens.sort(key=lambda x: x["data"])
        return ordens
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] Erro ao extrair ordens: {e}")
        return []

def _identificar_ordens_com_bloqueio(ordens):
    """Identifica ordens que geraram bloqueio"""
    bloqueios = []
    for i in range(len(ordens) - 1):
        if ordens[i]["valor_bloquear"] > ordens[i + 1]["valor_bloquear"]:
            bloqueios.append(ordens[i])
    return bloqueios

def _processar_ordem(driver, ordem, tipo_fluxo, log=True):
    """Processa uma ordem individual"""
    try:
        # Abrir menu da ordem
        if log:
            print(f"[SISBAJUD] Abrindo menu da ordem {ordem['sequencial']}")
        
        menu_clicado = False
        for tentativa in range(3):
            try:
                botao_menu = ordem["linha_el"].find_element(By.CSS_SELECTOR, "mat-icon.fas.fa-ellipsis-h")
                botao_menu.click()
                
                # Aguardar menu aparecer
                WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.mat-menu-panel"))
                )
                menu_clicado = True
                break
            except StaleElementReferenceException:
                if log:
                    print(f"[SISBAJUD] Tentativa {tentativa+1}: Elemento obsoleto, tentando novamente...")
                time.sleep(1)
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Tentativa {tentativa+1}: Erro ao clicar no menu: {e}")
                time.sleep(1)
        
        if not menu_clicado:
            if log:
                print(f"[SISBAJUD] ❌ Não foi possível abrir o menu da ordem {ordem['sequencial']}")
            return False
        
        # Clicar em Desdobrar
        if log:
            print(f"[SISBAJUD] Clicando em Desdobrar")

        desdobrar_clicado = False
        for tentativa in range(3):
            try:
                # Buscar botão pelo ícone fa-search-plus e texto Detalhar
                botoes_menu = driver.find_elements(By.CSS_SELECTOR, "button[role='menuitem']")
                for btn in botoes_menu:
                    try:
                        icone = btn.find_element(By.CSS_SELECTOR, "mat-icon.fas.fa-search-plus")
                        texto = btn.text.strip().lower()
                        if icone and "detalhar" in texto:
                            btn.click()
                            desdobrar_clicado = True
                            break
                    except Exception:
                        continue
                if desdobrar_clicado:
                    break
                time.sleep(1)
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Tentativa {tentativa+1}: Erro ao clicar em Detalhar: {e}")
                time.sleep(1)

        if not desdobrar_clicado:
            if log:
                print(f"[SISBAJUD] ❌ Não foi possível clicar em Detalhar")
            return False
        
        # Confirmar navegação para /desdobrar
        desdobrar_carregado = False
        for _ in range(10):
            if "/desdobrar" in driver.current_url:
                desdobrar_carregado = True
                break
            time.sleep(1)
        
        if not desdobrar_carregado:
            if log:
                print(f"[SISBAJUD] ❌ Página de desdobramento não carregou")
            return False
        
        if log:
            print(f"[SISBAJUD] ✅ Página de desdobramento carregada")

        # Reduzir zoom para 40% após abrir cada ordem
        try:
            driver.execute_script("document.body.style.zoom='0.4'")
            if log:
                print("[SISBAJUD] ✅ Zoom da página ajustado para 40%")
        except Exception as e:
            if log:
                print(f"[SISBAJUD] ⚠️ Não foi possível ajustar o zoom: {e}")
        
        # Preencher campos conforme tipo de fluxo
        if tipo_fluxo == "DESBLOQUEIO":
            if log:
                print(f"[SISBAJUD] Preenchendo campos para DESBLOQUEIO")
            
            # Selecionar Juiz
            try:
                juiz_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
                )
                juiz_input.clear()
                juiz_input.send_keys("OTAVIO AUGUSTO")
                time.sleep(1)
                # Clicar na opção correta do dropdown
                opcoes_juiz = driver.find_elements(By.CSS_SELECTOR, "span.mat-option-text")
                juiz_clicado = False
                for opcao in opcoes_juiz:
                    if "OTAVIO AUGUSTO MACHADO DE OLIVEIRA" in opcao.text:
                        opcao.click()
                        juiz_clicado = True
                        if log:
                            print(f"[SISBAJUD] ✅ Juiz 'OTAVIO AUGUSTO MACHADO DE OLIVEIRA' selecionado")
                        break
                if not juiz_clicado:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Opção de juiz não encontrada no dropdown")
                # Clicar fora para fechar o dropdown do juiz
                try:
                    driver.find_element(By.TAG_NAME, "body").click()
                    time.sleep(0.5)
                except Exception:
                    pass
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar juiz: {e}")
            
            # Seleciona ação no dropdown conforme o tipo de fluxo
            selects = driver.find_elements(By.CSS_SELECTOR, "mat-select[name*='acao']")
            for i, sel in enumerate(selects):
                try:
                    if log:
                        print(f"[SISBAJUD] [DEBUG] Tentando clicar na caixa de ação (dropdown) {i+1}")
                    # Clique robusto no dropdown
                    clicado = False
                    try:
                        WebDriverWait(driver, 3).until(EC.element_to_be_clickable(sel)).click()
                        clicado = True
                        if log:
                            print(f"[SISBAJUD] [DEBUG] Dropdown {i+1} clicado via WebDriverWait")
                    except Exception as e1:
                        if log:
                            print(f"[SISBAJUD] [DEBUG] WebDriverWait falhou: {e1}")
                        try:
                            sel.click()
                            clicado = True
                            if log:
                                print(f"[SISBAJUD] [DEBUG] Dropdown {i+1} clicado via .click()")
                        except Exception as e2:
                            if log:
                                print(f"[SISBAJUD] [DEBUG] .click() falhou: {e2}")
                            try:
                                driver.execute_script("arguments[0].click();", sel)
                                clicado = True
                                if log:
                                    print(f"[SISBAJUD] [DEBUG] Dropdown {i+1} clicado via JS")
                            except Exception as e3:
                                if log:
                                    print(f"[SISBAJUD] [DEBUG] JS click falhou: {e3}")
                                try:
                                    from selenium.webdriver.common.action_chains import ActionChains
                                    ActionChains(driver).move_to_element(sel).click().perform()
                                    clicado = True
                                    if log:
                                        print(f"[SISBAJUD] [DEBUG] Dropdown {i+1} clicado via ActionChains")
                                except Exception as e4:
                                    if log:
                                        print(f"[SISBAJUD] [DEBUG] ActionChains falhou: {e4}")
                    if not clicado and log:
                        print(f"[SISBAJUD] ⚠️ Não foi possível clicar no dropdown {i+1}")
                    # Polling para aguardar opções
                    for tentativa in range(10):
                        opcoes_acao = driver.find_elements(By.CSS_SELECTOR, "span.mat-option-text")
                        if opcoes_acao:
                            break
                        time.sleep(0.25)
                    if log:
                        print(f"[SISBAJUD] [DEBUG] {len(opcoes_acao)} opções encontradas no dropdown {i+1}: {[o.text for o in opcoes_acao]}")
                    # Seleciona apenas "Desbloquear valor" no fluxo DESBLOQUEIO
                    encontrou = False
                    for opcao in opcoes_acao:
                        if "Desbloquear valor" in opcao.text.strip():
                            opcao.click()
                            encontrou = True
                            if log:
                                print(f"[SISBAJUD] ✅ Ação desbloquear selecionada no dropdown {i+1}")
                            break
                    if not encontrou:
                        if opcoes_acao:
                            opcoes_acao[0].click()
                            if log:
                                print(f"[SISBAJUD] ⚠️ Nenhuma ação específica encontrada, selecionada opção em branco no dropdown {i+1}")
                        else:
                            if log:
                                print(f"[SISBAJUD] ⚠️ Nenhuma opção encontrada no dropdown {i+1}")
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Erro ao selecionar ação no dropdown {i+1}: {e}")
            
        else:  # POSITIVO
            if log:
                print(f"[SISBAJUD] Preenchendo campos para POSITIVO")
            
            # Implementação para fluxo positivo
            try:
                juiz_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
                )
                juiz_input.clear()
                juiz_input.send_keys("OTAVIO AUGUSTO\n")
                if log:
                    print(f"[SISBAJUD] ✅ Juiz selecionado")
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao selecionar juiz: {e}")
            
            # Selecionar ação "Transferir valor" em todos os dropdowns
            selects = driver.find_elements(By.CSS_SELECTOR, "mat-select[name*='acao']")
            for i, sel in enumerate(selects):
                try:
                    sel.click()
                    opc_transferir = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and normalize-space(text())='Transferir valor']"))
                    )
                    opc_transferir.click()
                    if log:
                        print(f"[SISBAJUD] ✅ Ação transferir selecionada no dropdown {i+1}")
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] ⚠️ Erro ao selecionar ação no dropdown {i+1}: {e}")
        

        # Clicar em Salvar
        if log:
            print(f"[SISBAJUD] Clicando em Salvar")
        salvar_clicado = False
        for tentativa in range(3):
            try:
                seletores_salvar = [
                    "button.mat-fab.mat-primary mat-icon.fa-save",
                    "//button[contains(@class,'mat-fab') and .//mat-icon[contains(@class,'fa-save')]]",
                    "//button[contains(@class,'mat-primary') and .//mat-icon[contains(@class,'fa-save')]]"
                ]
                for seletor in seletores_salvar:
                    try:
                        if seletor.startswith("//"):
                            btn_salvar = driver.find_element(By.XPATH, seletor)
                        else:
                            btn_salvar = driver.find_element(By.CSS_SELECTOR, seletor)
                        btn_salvar.click()
                        salvar_clicado = True
                        break
                    except:
                        continue
                if salvar_clicado:
                    break
                time.sleep(1)
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] Tentativa {tentativa+1}: Erro ao clicar em Salvar: {e}")
                time.sleep(1)
        if not salvar_clicado:
            if log:
                print(f"[SISBAJUD] ❌ Não foi possível clicar em Salvar")
            return False

        # Após salvar, preencher dados de transferência no fluxo POSITIVO
        if tipo_fluxo == "POSITIVO":
            try:
                if log:
                    print("[SISBAJUD] Preenchendo dados de transferência (depósito)")
                # Tipo de crédito: Geral
                tipo_credito_select = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'mat-select[formcontrolname="tipoCredito"]'))
                )
                tipo_credito_select.click()
                time.sleep(1)
                opcoes_tipo = driver.find_elements(By.CSS_SELECTOR, "span.mat-option-text")
                for opcao in opcoes_tipo:
                    if "Geral" in opcao.text:
                        opcao.click()
                        if log:
                            print("[SISBAJUD] ✅ Tipo de crédito 'Geral' selecionado")
                        break
                # Banco: 0001 Banco do Brasil
                banco_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="instituicaoFinanceiraPorCategoria"]'))
                )
                banco_input.click()
                time.sleep(1)
                opcoes_banco = driver.find_elements(By.CSS_SELECTOR, "span.mat-option-text")
                for opcao in opcoes_banco:
                    if "0001 Banco do Brasil" in opcao.text:
                        opcao.click()
                        if log:
                            print("[SISBAJUD] ✅ Banco '0001 Banco do Brasil' selecionado")
                        break
                # Agência: 5905
                agencia_input = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="agencia"]'))
                )
                agencia_input.clear()
                agencia_input.send_keys("5905")
                if log:
                    print("[SISBAJUD] ✅ Agência '5905' preenchida")
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ⚠️ Erro ao preencher dados de transferência: {e}")
        
        # Aguardar botão Protocolar aparecer
        protocolar_apareceu = False
        for _ in range(10):
            try:
                driver.find_element(By.XPATH, "//button[contains(@class,'mat-fab') and @title='Protocolar']")
                protocolar_apareceu = True
                break
            except:
                time.sleep(1)
        
        if not protocolar_apareceu:
            if log:
                print(f"[SISBAJUD] ❌ Botão Protocolar não apareceu após salvar")
            return False
        
        if log:
            print(f"[SISBAJUD] ✅ Ordem {ordem['sequencial']} processada com sucesso")
        
        return True
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro ao processar ordem {ordem['sequencial']}: {e}")
        return False

# =================================================================
# FUNÇÃO PRINCIPAL DE PROCESSAMENTO
# =================================================================

def processar_ordem_sisbajud(driver, dados_processo, log=True):
    """
    Processamento completo de ordens no SISBAJUD:
    1. Navegação para teimosinha
    2. Filtro de ordens recentes
    3. Extração de dados
    4. Processamento individual de cada ordem
    5. Fechamento do driver
    
    Args:
        driver: WebDriver do SISBAJUD (já logado)
        dados_processo: Dados do processo extraído do PJe
        log: Boolean para ativar logs detalhados
        
    Returns:
        dict: Resultado do processamento com status e detalhes
    """
    resultado = {
        'status': 'pendente',
        'tipo_fluxo': None,
        'series_processadas': 0,
        'ordens_processadas': 0,
        'erros': [],
        'detalhes': {}
    }
    
    try:
        # ETAPA 1: NAVEGAÇÃO INICIAL
        if log:
            print("\n" + "="*80)
            print("[SISBAJUD] INICIANDO PROCESSAMENTO COMPLETO")
            print("="*80)
        
        # Verificar URL inicial
        current_url = driver.current_url
        if 'sisbajud.cnj.jus.br' not in current_url:
            erro = f"URL inválida: {current_url}"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        # Navegar para /minuta se necessário
        if '/minuta' not in current_url:
            if log:
                print("[SISBAJUD] Navegando para /minuta...")
            driver.get('https://sisbajud.cnj.jus.br/minuta')
            time.sleep(2)
        
        # ETAPA 2: ACESSAR TEIMOSINHA
        if log:
            print("\n[SISBAJUD] ETAPA 1: NAVEGAÇÃO PARA TEIMOSINHA")
        
        # Clicar no menu hamburguer
        if log:
            print("[SISBAJUD] 1. Clicando no menu hamburguer...")
        hamburger_clicado = False
        seletores_hamburger = [
            'button.btn-hamburger.hamburger--slider.mat-flat-button',
            'button[aria-label="Abri menu de navegação"]',
            'button.btn-hamburger',
            'button[mattooltip="Abri menu de navegação"]'
        ]
        
        for i, seletor in enumerate(seletores_hamburger, 1):
            try:
                hamburguer_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                )
                hamburguer_btn.click()
                if log:
                    print(f"[SISBAJUD] ✅ Menu hamburguer clicado com seletor {i}: {seletor}")
                hamburger_clicado = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not hamburger_clicado:
            erro = "Não foi possível clicar no menu hamburguer"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        time.sleep(1)
        
        # Clicar no link Teimosinha
        if log:
            print("[SISBAJUD] 2. Clicando no link Teimosinha...")
        teimosinha_clicado = False
        seletores_teimosinha = [
            'a[href="/teimosinha"]',
            'a[aria-label="Ir para Teimosinha"]',
            'a:contains("Teimosinha")',
            'a.mat-button[href="/teimosinha"]'
        ]
        
        for i, seletor in enumerate(seletores_teimosinha, 1):
            try:
                if ':contains(' in seletor:
                    teimosinha_link = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Teimosinha')]"))
                    )
                else:
                    teimosinha_link = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                    )
                teimosinha_link.click()
                if log:
                    print(f"[SISBAJUD] ✅ Link Teimosinha clicado com seletor {i}: {seletor}")
                teimosinha_clicado = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not teimosinha_clicado:
            erro = "Não foi possível clicar no link Teimosinha"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        time.sleep(2)
        
        # Confirmar URL /teimosinha
        current_url = driver.current_url
        if '/teimosinha' not in current_url:
            erro = f"Falha na navegação para teimosinha. URL atual: {current_url}"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        if log:
            print(f"[SISBAJUD] ✅ Navegação confirmada: {current_url}")
        
        # Preencher campo do processo
        if log:
            print("[SISBAJUD] 3. Preenchendo número do processo...")
        
        numero_processo = None
        if dados_processo and isinstance(dados_processo, dict):
            numero_processo = dados_processo.get('numero_processo')
        
        if not numero_processo:
            erro = "Número do processo não encontrado nos dados extraídos"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        if log:
            print(f"[SISBAJUD] Processo a consultar: {numero_processo}")
        
        input_preenchido = False
        seletores_input_processo = [
            'input[placeholder="Número do Processo"]',
            'input[mask="0000000-00.0000.0.00.0000"]',
            'input.mat-input-element[maxlength="25"]',
            'input[id*="mat-input"]'
        ]
        
        for i, seletor in enumerate(seletores_input_processo, 1):
            try:
                input_processo = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                )
                input_processo.clear()
                input_processo.send_keys(numero_processo)
                if log:
                    print(f"[SISBAJUD] ✅ Campo processo preenchido com seletor {i}: {seletor}")
                input_preenchido = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not input_preenchido:
            erro = "Não foi possível preencher o campo do processo"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        time.sleep(1)
        
        # Clicar no botão Consultar
        if log:
            print("[SISBAJUD] 4. Clicando no botão Consultar...")
        consultar_clicado = False
        seletores_btn_consultar = [
            'button.mat-fab.mat-primary:has(mat-icon.fa-search)',
            'button[color="primary"][mat-fab]:has(mat-icon)',
            'button.mat-fab:contains("Consultar")',
            'button.mat-fab.mat-primary'
        ]
        
        for i, seletor in enumerate(seletores_btn_consultar, 1):
            try:
                if ':has(' in seletor or ':contains(' in seletor:
                    btn_consultar = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'mat-fab') and contains(@class, 'mat-primary')]//mat-icon[contains(@class, 'fa-search')]//ancestor::button"))
                    )
                else:
                    btn_consultar = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                    )
                btn_consultar.click()
                if log:
                    print(f"[SISBAJUD] ✅ Botão Consultar clicado com seletor {i}: {seletor}")
                consultar_clicado = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not consultar_clicado:
            erro = "Não foi possível clicar no botão Consultar"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        time.sleep(3)
        
        # Confirmar página de resultados
        if log:
            print("[SISBAJUD] 5. Confirmando página de resultados...")
        header_encontrado = False
        seletores_header_serie = [
            'th.mat-header-cell:contains("ID da série")',
            'th[class*="sequencial"]:contains("ID")',
            'th.cdk-column-sequencial'
        ]
        
        for i, seletor in enumerate(seletores_header_serie, 1):
            try:
                if ':contains(' in seletor:
                    header = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//th[contains(text(), 'ID da série')]"))
                    )
                else:
                    header = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                    )
                if log:
                    print(f"[SISBAJUD] ✅ Cabeçalho encontrado com seletor {i}: {seletor}")
                header_encontrado = True
                break
            except Exception as e:
                if log:
                    print(f"[SISBAJUD] ❌ Seletor {i} falhou: {seletor} - {str(e)[:50]}...")
        
        if not header_encontrado:
            erro = "Página de resultados não confirmada - cabeçalho 'ID da série' não encontrado"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        if log:
            print("[SISBAJUD] ✅ Navegação inicial concluída com sucesso!")
        
        # ETAPA 3: FILTRO E EXTRAÇÃO DE SÉRIES
        if log:
            print("\n[SISBAJUD] ETAPA 2: FILTRO E EXTRAÇÃO DE SÉRIES")
        
        # Calcular data limite (15 dias antes da data atual)
        data_atual = datetime.now()
        data_limite = data_atual - timedelta(days=15)
        if log:
            print(f"[SISBAJUD] Data limite para filtro: {data_limite.strftime('%d/%m/%Y')}")
        
        # Extrair dados das séries
        series_validas = []
        try:
            tabela = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.mat-table'))
            )
            
            linhas = tabela.find_elements(By.CSS_SELECTOR, 'tbody tr.mat-row')
            if log:
                print(f"[SISBAJUD] Encontradas {len(linhas)} linhas na tabela")
            
            if len(linhas) == 0:
                erro = "Nenhuma série encontrada na tabela"
                if log:
                    print(f"[SISBAJUD] ❌ {erro}")
                resultado['status'] = 'erro'
                resultado['erros'].append(erro)
                return resultado
            
            for idx, linha in enumerate(linhas, 1):
                try:
                    # Extrair dados da linha
                    id_serie = linha.find_element(By.CSS_SELECTOR, 'td[data-label="sequencial"]').text.strip()
                    situacao = linha.find_element(By.CSS_SELECTOR, 'td[data-label="dataFim"]').text.strip()
                    data_programada_text = linha.find_element(By.CSS_SELECTOR, 'td[data-label="dataProgramada"]').text.strip()
                    valor_bloqueado_text = linha.find_element(By.CSS_SELECTOR, 'td[data-label="valorBloqueado"]').text.strip()
                    valor_bloquear_text = linha.find_element(By.CSS_SELECTOR, 'td[data-label="valorBloquear"]').text.strip()

                    if log:
                        print(f"[SISBAJUD] Série {idx}: ID={id_serie}, Situação={situacao}, Data={data_programada_text}")

                    # Verificar se situação é "Encerrada"
                    if 'encerrada' not in situacao.lower():
                        if log:
                            print(f"[SISBAJUD] Série {id_serie} rejeitada: situação não é 'Encerrada' ({situacao})")
                        continue

                    # Verificar data programada
                    try:
                        meses = {
                            'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
                            'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
                        }

                        partes = data_programada_text.upper().split()
                        if len(partes) >= 5:
                            dia = int(partes[0])
                            mes = meses.get(partes[2], 1)
                            ano = int(partes[4])
                            data_programada = datetime(ano, mes, dia)

                            # CORREÇÃO: considerar apenas séries finalizadas nos últimos 15 dias
                            if data_programada < data_limite:
                                if log:
                                    print(f"[SISBAJUD] Série {id_serie} rejeitada: data muito antiga ({data_programada.strftime('%d/%m/%Y')} < {data_limite.strftime('%d/%m/%Y')})")
                                continue
                        else:
                            if log:
                                print(f"[SISBAJUD] Série {id_serie}: formato de data inválido - {data_programada_text}")
                            continue
                            
                    except Exception as e:
                        if log:
                            print(f"[SISBAJUD] Erro ao processar data da série {id_serie}: {e}")
                        continue
                    
                    # Converter valores monetários
                    def extrair_valor_monetario(texto):
                        texto_limpo = texto.replace('R$', '').replace('\\xa0', '').replace('&nbsp;', '').strip()
                        texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
                        try:
                            return float(texto_limpo)
                        except:
                            return 0.0
                    
                    valor_bloqueado = extrair_valor_monetario(valor_bloqueado_text)
                    valor_bloquear = extrair_valor_monetario(valor_bloquear_text)
                    
                    # Adicionar série válida
                    serie_data = {
                        'id_serie': id_serie,
                        'situacao': situacao,
                        'data_programada': data_programada,
                        'valor_bloqueado': valor_bloqueado,
                        'valor_bloquear': valor_bloquear,
                        'valor_bloqueado_text': valor_bloqueado_text,
                        'valor_bloquear_text': valor_bloquear_text
                    }
                    
                    series_validas.append(serie_data)
                    if log:
                        print(f"[SISBAJUD] ✅ Série {id_serie} válida: R$ {valor_bloqueado:.2f} bloqueado")
                    
                except Exception as e:
                    if log:
                        print(f"[SISBAJUD] Erro ao processar linha {idx}: {e}")
                    continue
            
        except Exception as e:
            erro = f"Erro ao extrair dados da tabela: {str(e)}"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'erro'
            resultado['erros'].append(erro)
            return resultado
        
        # Verificar se há séries válidas
        if len(series_validas) == 0:
            erro = "Não há teimosinha para processar"
            if log:
                print(f"[SISBAJUD] ❌ {erro}")
            resultado['status'] = 'concluido'
            resultado['erros'].append(erro)
            return resultado
        
        if log:
            print(f"[SISBAJUD] ✅ Encontradas {len(series_validas)} séries válidas para processamento")
        
        # ETAPA 4: DEFINIÇÃO DE FLUXO
        if log:
            print("\n[SISBAJUD] ETAPA 3: DEFINIÇÃO DE FLUXO")
        
        total_bloqueado = sum(s['valor_bloqueado'] for s in series_validas)
        total_bloquear = sum(s['valor_bloquear'] for s in series_validas)
        
        if log:
            print(f"[SISBAJUD] Total bloqueado: R$ {total_bloqueado:.2f}")
            print(f"[SISBAJUD] Total a bloquear: R$ {total_bloquear:.2f}")
        
        # Determinar tipo de fluxo
        if total_bloqueado == 0.0:
            tipo_fluxo = 'NEGATIVO'
            if log:
                print("[SISBAJUD] 🔴 FLUXO NEGATIVO: Total bloqueado = 0")
        elif total_bloqueado < 100.0 and total_bloquear >= 1000.0:
            tipo_fluxo = 'DESBLOQUEIO'
            if log:
                print(f"[SISBAJUD] 🟡 FLUXO DESBLOQUEIO: Total bloqueado < R$ 100,00 e valor a bloquear >= R$ 1.000,00")
        elif total_bloqueado < 100.0 and total_bloquear < 1000.0:
            tipo_fluxo = 'POSITIVO'
            if log:
                print(f"[SISBAJUD] 🟢 FLUXO POSITIVO: Total bloqueado < R$ 100,00 mas valor a bloquear < R$ 1.000,00")
        else:
            tipo_fluxo = 'POSITIVO'
            if log:
                print(f"[SISBAJUD] 🟢 FLUXO POSITIVO: Total bloqueado >= R$ 100,00")
        
        resultado['tipo_fluxo'] = tipo_fluxo
        
        # ETAPA 5: PROCESSAMENTO DE ORDENS
        if log:
            print("\n[SISBAJUD] ETAPA 4: PROCESSAMENTO DE ORDENS")
            print(f"[SISBAJUD] Tipo de fluxo: {tipo_fluxo}")
        
        if tipo_fluxo == 'NEGATIVO':
            if log:
                print("[SISBAJUD] Fluxo NEGATIVO, nenhuma série será processada.")
            resultado['status'] = 'concluido'
            return resultado
        
        # Processar cada série
        for idx, serie in enumerate(series_validas, 1):
            if log:
                print(f"\n[SISBAJUD] >>> Processando série {idx}/{len(series_validas)} ID={serie['id_serie']}")

            # Navegar para detalhes da série via clique
            try:
                # 1. Clicar no menu da linha da série
                if log:
                    print(f"[SISBAJUD] Clicando no menu da série {serie['id_serie']}")
                linha_serie = None
                # Buscar a linha correspondente na tabela
                tabela = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'table.mat-table'))
                )
                linhas = tabela.find_elements(By.CSS_SELECTOR, 'tbody tr.mat-row')
                for linha in linhas:
                    try:
                        id_serie_linha = linha.find_element(By.CSS_SELECTOR, 'td[data-label="sequencial"]').text.strip()
                        if id_serie_linha == serie['id_serie']:
                            linha_serie = linha
                            break
                    except:
                        continue
                if not linha_serie:
                    erro = f"Linha da série {serie['id_serie']} não encontrada para clique no menu"
                    if log:
                        print(f"[SISBAJUD] ❌ {erro}")
                    resultado['erros'].append(erro)
                    continue

                botao_menu = linha_serie.find_element(By.CSS_SELECTOR, 'button.mat-menu-trigger.mat-icon-button')
                botao_menu.click()
                time.sleep(1)

                # 2. Clicar em 'Detalhar' no menu
                if log:
                    print(f"[SISBAJUD] Clicando em 'Detalhar' para série {serie['id_serie']}")
                detalhar_clicado = False
                for tentativa in range(3):
                    try:
                        botoes_menu = driver.find_elements(By.CSS_SELECTOR, 'button[role="menuitem"]')
                        for btn in botoes_menu:
                            try:
                                texto_btn = btn.text.strip().lower()
                                if 'detalhar' in texto_btn:
                                    btn.click()
                                    detalhar_clicado = True
                                    break
                            except:
                                continue
                        if detalhar_clicado:
                            break
                        time.sleep(1)
                    except Exception as e:
                        if log:
                            print(f"[SISBAJUD] Tentativa {tentativa+1}: Erro ao clicar em 'Detalhar': {e}")
                        time.sleep(1)
                if not detalhar_clicado:
                    erro = f"Não foi possível clicar em 'Detalhar' para série {serie['id_serie']}"
                    if log:
                        print(f"[SISBAJUD] ❌ {erro}")
                    resultado['erros'].append(erro)
                    continue

                # 3. Confirmar navegação
                detalhes_carregado = False
                for _ in range(10):
                    if "/detalhes" in driver.current_url and serie["id_serie"] in driver.current_url:
                        detalhes_carregado = True
                        break
                    time.sleep(1)
                if not detalhes_carregado:
                    erro = f"Falha ao abrir detalhes da série {serie['id_serie']}"
                    if log:
                        print(f"[SISBAJUD] ❌ {erro}")
                    resultado['erros'].append(erro)
                    continue
                if log:
                    print(f"[SISBAJUD] ✅ Detalhes da série {serie['id_serie']} carregados")
            except Exception as e:
                erro = f"Erro na navegação para detalhes da série {serie['id_serie']}: {e}"
                if log:
                    print(f"[SISBAJUD] ❌ {erro}")
                resultado['erros'].append(erro)
                continue
            
            # Extrair ordens da série
            try:
                ordens = _extrair_ordens_da_serie(driver, log)
                if log:
                    print(f"[SISBAJUD] Encontradas {len(ordens)} ordens na série")
                
                # Identificar ordens com bloqueio
                ordens_bloqueio = _identificar_ordens_com_bloqueio(ordens)
                if log:
                    print(f"[SISBAJUD] Encontradas {len(ordens_bloqueio)} ordens com bloqueio")
                
                # Processar cada ordem com bloqueio
                for ordem in ordens_bloqueio:
                    if log:
                        print(f"[SISBAJUD] Processando ordem {ordem['sequencial']} - Protocolo: {ordem['protocolo']}")
                    
                    sucesso = _processar_ordem(driver, ordem, tipo_fluxo, log)
                    if sucesso:
                        resultado['ordens_processadas'] += 1
                        if log:
                            print(f"[SISBAJUD] ✅ Ordem {ordem['sequencial']} processada com sucesso")
                    else:
                        erro = f"Falha ao processar ordem {ordem['sequencial']}"
                        if log:
                            print(f"[SISBAJUD] ❌ {erro}")
                        resultado['erros'].append(erro)
                
                resultado['series_processadas'] += 1
                
            except Exception as e:
                erro = f"Erro ao processar série {serie['id_serie']}: {str(e)}"
                if log:
                    print(f"[SISBAJUD] ❌ {erro}")
                resultado['erros'].append(erro)
            
            # Fechar aba de detalhes
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
        
        # ETAPA 6: FINALIZAÇÃO
        if log:
            print("\n[SISBAJUD] ETAPA 5: FINALIZAÇÃO")
        
        # Fechar driver SISBAJUD
        driver.quit()
        if log:
            print("[SISBAJUD] ✅ Driver SISBAJUD fechado")
        
        resultado['status'] = 'concluido'
        return resultado
        
    except Exception as e:
        erro = f"Erro geral no processamento: {str(e)}"
        if log:
            print(f"[SISBAJUD] ❌ {erro}")
        resultado['status'] = 'erro'
        resultado['erros'].append(erro)
        
        try:
            driver.quit()
        except:
            pass
        
        return resultado

# =================================================================
# FUNÇÃO DE PREAMBULO
# =================================================================

def preambulo_sisbajud(driver_pje, log=True):
    """
    Função de preâmbulo para preparar o ambiente SISBAJUD:
    1. Copia número do processo no PJe
    2. Inicia driver SISBAJUD
    3. Aguarda login manual
    4. Retorna driver SISBAJUD e número do processo
    
    Args:
        driver_pje: WebDriver do PJe (já logado e com processo aberto)
        log: Boolean para ativar logs detalhados
        
    Returns:
        tuple: (driver_sisbajud, numero_processo) ou (None, None) em caso de erro
    """
    try:
        if log:
            print("\n" + "="*80)
            print("[SISBAJUD] INICIANDO PREAMBULO")
            print("="*80)
        
        # ETAPA 1: Copiar número do processo no PJe
        if log:
            print("[PREAMBULO] ETAPA 1: Copiando número do processo no PJe")
        
        # Clicar no ícone de cópia
        if log:
            print("[PREAMBULO] 1. Clicando no ícone de cópia...")
        
        try:
            # Usar o seletor fornecido
            icone_copia = WebDriverWait(driver_pje, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "i.far.fa-copy.fa-lg"))
            )
            icone_copia.click()
            if log:
                print("[PREAMBULO] ✅ Ícone de cópia clicado")
        except Exception as e:
            if log:
                print(f"[PREAMBULO] ❌ Erro ao clicar no ícone de cópia: {e}")
            return None, None
        
        time.sleep(1)
        
        # Obter número do processo da área de transferência
        if log:
            print("[PREAMBULO] 2. Obtendo número da área de transferência...")
        
        try:
            # Usar JavaScript para ler a área de transferência
            numero_processo = driver_pje.execute_script("""
                return navigator.clipboard.readText().then(text => text).catch(err => '');
            """)
            
            if numero_processo:
                # Extrair apenas o número do processo (padrão: 0000000-00.0000.0.00.0000)
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})', numero_processo)
                if match:
                    numero_processo = match.group(1)
                    if log:
                        print(f"[PREAMBULO] ✅ Número do processo extraído: {numero_processo}")
                else:
                    if log:
                        print(f"[PREAMBULO] ⚠️ Número do processo não encontrado no texto: {numero_processo}")
                    return None, None
            else:
                if log:
                    print("[PREAMBULO] ❌ Não foi possível obter texto da área de transferência")
                return None, None
                
        except Exception as e:
            if log:
                print(f"[PREAMBULO] ❌ Erro ao obter número da área de transferência: {e}")
            return None, None
        
        # ETAPA 2: Iniciar driver SISBAJUD
        if log:
            print("\n[PREAMBULO] ETAPA 2: Iniciando driver SISBAJUD")
        
        try:
            # Função para criar driver SISBAJUD
            def criar_driver_sisbajud():
                try:
                    from selenium.webdriver.firefox.options import Options
                    from selenium.webdriver.firefox.service import Service
                    
                    # Configurações do Firefox
                    options = Options()
                    options.add_argument("--width=1200")
                    options.add_argument("--height=800")
                    
                    # Caminhos específicos (ajuste conforme necessário)
                    firefox_binary = r'C:\Program Files\Firefox Developer Edition\firefox.exe'
                    geckodriver_path = r'd:\PjePlus\geckodriver.exe'
                    
                    options.binary_location = firefox_binary
                    service = Service(executable_path=geckodriver_path)
                    
                    driver = webdriver.Firefox(service=service, options=options)
                    driver.implicitly_wait(10)
                    return driver
                except Exception as e:
                    if log:
                        print(f"[PREAMBULO] ❌ Erro ao criar driver SISBAJUD: {e}")
                    return None
            
            driver_sisbajud = criar_driver_sisbajud()
            
            if not driver_sisbajud:
                if log:
                    print("[PREAMBULO] ❌ Falha ao criar driver SISBAJUD")
                return None, None
            
            if log:
                print("[PREAMBULO] ✅ Driver SISBAJUD criado com sucesso")
                # Maximizar a janela do driver SISBAJUD
                try:
                    driver_sisbajud.maximize_window()
                    if log:
                        print("[PREAMBULO] ✅ Janela do SISBAJUD maximizada")
                except Exception as e:
                    if log:
                        print(f"[PREAMBULO] ⚠️ Não foi possível maximizar a janela: {e}")
                
        except Exception as e:
            if log:
                print(f"[PREAMBULO] ❌ Erro ao iniciar driver SISBAJUD: {e}")
            return None, None
        
        # ETAPA 3: Aguardar login manual
        if log:
            print("\n[PREAMBULO] ETAPA 3: Aguardando login manual no SISBAJUD")
            print("[PREAMBULO] Por favor, faça o login manualmente no SISBAJUD...")
        
        try:
            # Navegar para a página inicial do SISBAJUD
            driver_sisbajud.get('https://sisbajud.cnj.jus.br/')
            
            # Aguardar login (verificar periodicamente)
            login_realizado = False
            tempo_espera = 0
            intervalo_verificacao = 5  # segundos
            
            while tempo_espera < 600:  # Máximo 10 minutos
                try:
                    # Verificar se já está logado
                    current_url = driver_sisbajud.current_url
                    
                    # Se não estiver mais na página de login/autenticação
                    if not any(indicador in current_url.lower() for indicador in ['login', 'auth', 'realms', 'sso']):
                        login_realizado = True
                        break
                    
                    # Verificar se há elementos da página inicial do SISBAJUD
                    try:
                        driver_sisbajud.find_element(By.CSS_SELECTOR, "button.btn-hamburger")
                        login_realizado = True
                        break
                    except:
                        pass
                    
                except:
                    pass
                
                if log and tempo_espera % 30 == 0:  # A cada 30 segundos
                    print(f"[PREAMBULO] Aguardando login... ({tempo_espera}s)")
                
                time.sleep(intervalo_verificacao)
                tempo_espera += intervalo_verificacao
            
            if login_realizado:
                if log:
                    print(f"[PREAMBULO] ✅ Login realizado após {tempo_espera} segundos")
                return driver_sisbajud, numero_processo
            else:
                if log:
                    print("[PREAMBULO] ❌ Login não realizado dentro do tempo limite")
                driver_sisbajud.quit()
                return None, None
                
        except Exception as e:
            if log:
                print(f"[PREAMBULO] ❌ Erro durante aguardo de login: {e}")
            try:
                driver_sisbajud.quit()
            except:
                pass
            return None, None
            
    except Exception as e:
        if log:
            print(f"[PREAMBULO] ❌ Erro geral no preâmbulo: {e}")
        return None, None

# =================================================================
# FUNÇÃO ORQUESTRADORA
# =================================================================

def bloqsisb(driver_pje, log=True):
    """
    Fluxo completo para processamento SISBAJUD:
    1. Executa preâmbulo (copia processo, inicia driver, aguarda login)
    2. Executa processamento de ordens
    3. Finaliza driver
    
    Args:
        driver_pje: WebDriver do PJe (já logado e com processo aberto)
        log: Boolean para ativar logs detalhados
        
    Returns:
        dict: Resultado do processamento
    """
    try:
        # Executar preâmbulo
        driver_sisbajud, numero_processo = preambulo_sisbajud(driver_pje, log)
        
        if not driver_sisbajud or not numero_processo:
            if log:
                print("[SISBAJUD] ❌ Falha no preâmbulo")
            return {
                'status': 'erro',
                'erro': 'Falha no preâmbulo',
                'detalhes': {}
            }
        
        # Preparar dados do processo
        dados_processo = {
            'numero_processo': numero_processo
        }
        
        if log:
            print(f"\n[SISBAJUD] Iniciando processamento do processo: {numero_processo}")
        
        # Executar processamento principal
        resultado = processar_ordem_sisbajud(driver_sisbajud, dados_processo, log)
        
        return resultado
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro no fluxo completo: {e}")
        return {
            'status': 'erro',
            'erro': str(e),
            'detalhes': {}
        }