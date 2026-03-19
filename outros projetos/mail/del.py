# Script para apagar emails por domínio baseado no arquivo dominios.js
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

# Configurações
CHROME_PROFILE = r'C:\Users\Silas\AppData\Local\Google\Chrome\User Data\Profile 2'
DOMINIOS_JS = 'dominios.js'
DEBUG_MODE = True  # Para ver logs detalhados e pausas entre ações

def ler_dominios_para_apagar():
    """Lê o arquivo dominios.js e retorna lista de domínios marcados para apagar (SIM)"""
    dominios_apagar = []

    if not os.path.exists(DOMINIOS_JS):
        print(f"[ERRO] ❌ Arquivo {DOMINIOS_JS} não encontrado!")
        return dominios_apagar

    print(f"[LOG] 📁 Lendo arquivo {DOMINIOS_JS}...")

    with open(DOMINIOS_JS, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    for linha in linhas:
        linha = linha.strip()
        if not linha:  # Pula linhas vazias
            continue

        # Parse do formato: dominio | sim/nao | cancelado: sim/nao
        partes = linha.split(' | ')
        if len(partes) >= 2:
            dominio = partes[0].strip()
            apagar = partes[1].strip().lower()

            if apagar == 'sim':
                dominios_apagar.append(dominio)
                print(f"[LOG] ✓ Domínio marcado para APAGAR: {dominio}")
            else:
                print(f"[LOG] ⚪ Domínio NÃO marcado para apagar: {dominio}")

    print(f"[LOG] 📊 Total de domínios para apagar: {len(dominios_apagar)}")
    return dominios_apagar

def navegar_para_inbox(driver):
    """1- Navega para a inbox do Gmail"""
    print('[LOG] 🏠 Navegando para inbox...')
    driver.get('https://mail.google.com/mail/u/0/#inbox')

    # Aguarda carregamento da inbox
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="main"]'))
    )

    if DEBUG_MODE:
        print('[LOG] ✓ Inbox carregada, aguardando 2s...')
        time.sleep(2)

    print('[LOG] ✅ Inbox carregada com sucesso.')

def aplicar_filtro_dominio(driver, dominio):
    """2- Aplica filtro de busca para um domínio específico"""
    print(f'[LOG] 🔍 Aplicando filtro para domínio: {dominio}')

    try:
        # a- clica no campo de pesquisa específico
        print('[LOG] a- Clicando no campo de pesquisa...')

        campo_pesquisa = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input.gb_se.aJh[name="q"]'))
        )
        campo_pesquisa.click()

        if DEBUG_MODE:
            print('[LOG] ✓ Campo de pesquisa clicado')
            time.sleep(1)

        # b- digitar o filtro como from:@dominio.com
        print(f'[LOG] b- Digitando filtro: from:@{dominio}')
        campo_pesquisa.clear()

        filtro = f"from:@{dominio}"
        campo_pesquisa.send_keys(filtro)

        if DEBUG_MODE:
            print(f'[LOG] ✓ Filtro digitado: {filtro}')
            time.sleep(1)

        # c- enter para confirmar
        print('[LOG] c- Pressionando Enter...')
        campo_pesquisa.send_keys(Keys.ENTER)

        if DEBUG_MODE:
            print('[LOG] ✓ Enter pressionado, aguardando resultados...')
            time.sleep(3)

        # Aguarda os resultados carregarem
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="main"]'))
        )

        print(f'[LOG] ✅ Filtro aplicado com sucesso para domínio: {dominio}')
        return True

    except Exception as e:
        print(f'[ERRO] ❌ Falha ao aplicar filtro para domínio {dominio}: {e}')
        return False

def executar_processo_exclusao(driver, dominio):
    """Executa todo o processo de seleção e exclusão conforme especificado"""
    print(f'[LOG] 🗑️ Iniciando processo de exclusão para: {dominio}')

    try:
        # d- clique nas checkboxes das três primeiras linhas
        print('[LOG] d- Selecionando checkboxes das três primeiras linhas...')

        # Busca as três primeiras checkboxes específicas
        checkboxes_seletor = 'div[id*=":"][class*="oZ-jc T-Jo J-J5-Ji"][role="checkbox"]'
        checkboxes = driver.find_elements(By.CSS_SELECTOR, checkboxes_seletor)[:3]

        for i, checkbox in enumerate(checkboxes):
            try:
                if checkbox.is_displayed() and checkbox.is_enabled():
                    checkbox.click()
                    if DEBUG_MODE:
                        print(f'[LOG] ✓ Checkbox {i+1} selecionada')
                        time.sleep(0.5)
            except Exception as e:
                print(f'[LOG] ⚠️ Erro ao clicar checkbox {i+1}: {e}')

        # e- clicar no ícone de lixeira com SVG específico
        print('[LOG] e- Clicando no ícone de lixeira...')
        try:
            delete_svg = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.asa svg[viewBox="0 -960 960 960"]'))
            )
            delete_svg.click()

            if DEBUG_MODE:
                print('[LOG] ✓ Ícone de lixeira clicado')
                time.sleep(1)

        except Exception as e:
            print(f'[LOG] ⚠️ Ícone lixeira não encontrado: {e}')

        # f- clicar no checkbox misto
        print('[LOG] f- Clicando no checkbox misto...')
        try:
            checkbox_misto = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.T-Jo.J-J5-Ji.T-Jo-auq.T-Jo-ayH[role="checkbox"]'))
            )
            checkbox_misto.click()

            if DEBUG_MODE:
                print('[LOG] ✓ Checkbox misto clicado')
                time.sleep(1)

        except Exception as e:
            print(f'[LOG] ⚠️ Checkbox misto não encontrado: {e}')

        # g- clicar no checkbox false
        print('[LOG] g- Clicando no checkbox false...')
        try:
            checkbox_falso = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.T-Jo.J-J5-Ji.T-Jo-auq.T-Jo-iAfbIe[role="checkbox"]'))
            )
            checkbox_falso.click()

            if DEBUG_MODE:
                print('[LOG] ✓ Checkbox false clicado')
                time.sleep(1)

        except Exception as e:
            print(f'[LOG] ⚠️ Checkbox false não encontrado: {e}')

        # h- clicar em "Selecionar todas as conversas que correspondem a esta pesquisa"
        print('[LOG] h- Clicando em "Selecionar todas as conversas"...')
        try:
            selecionar_todas = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Selecionar todas as conversas que correspondem a esta pesquisa')]"))
            )
            selecionar_todas.click()

            if DEBUG_MODE:
                print('[LOG] ✓ "Selecionar todas as conversas" clicado')
                time.sleep(2)

        except Exception as e:
            print(f'[LOG] ⚠️ Link "Selecionar todas" não encontrado: {e}')

        # i- clicar no botão de delete com classe específica
        print('[LOG] i- Clicando no botão de delete específico...')
        try:
            delete_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.asa div.ar9.T-I-J3.J-J5-Ji'))
            )
            delete_btn.click()

            if DEBUG_MODE:
                print('[LOG] ✓ Botão delete específico clicado')  
                time.sleep(1)

        except Exception as e:
            print(f'[LOG] ⚠️ Botão delete específico não encontrado: {e}')

        # g- clicar na confirmação final (div.bBf)
        print('[LOG] g- Aguardando e clicando na confirmação final...')
        print('[LOG] ⏳ AGUARDANDO até conseguir clicar na confirmação (não fazer NADA)...')

        # Aguarda até que o elemento esteja clicável
        confirmacao_final = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.bBf'))
        )
        confirmacao_final.click()

        if DEBUG_MODE:
            print('[LOG] ✅ Confirmação final clicada')

        # Aguarda 2s conforme especificado
        print('[LOG] ⏳ Aguardando 2 segundos...')
        time.sleep(2)

        print(f'[LOG] ✅ Domínio {dominio} processado e APAGADO com sucesso!')
        return True

    except Exception as e:
        print(f'[ERRO] ❌ Falha ao processar exclusão do domínio {dominio}: {e}')
        return False

def processar_dominio(driver, dominio):
    """Processa um domínio completo: filtro + exclusão"""
    print(f'\n{"="*60}')
    print(f'[LOG] 🎯 PROCESSANDO DOMÍNIO: {dominio}')
    print(f'{"="*60}')

    # Navegar para inbox antes de cada domínio
    navegar_para_inbox(driver)

    # Aplicar filtro
    if not aplicar_filtro_dominio(driver, dominio):
        print(f'[LOG] ❌ Falha no filtro para {dominio}. Pulando para próximo.')
        return False

    # Executar processo de exclusão
    if not executar_processo_exclusao(driver, dominio):
        print(f'[LOG] ❌ Falha na exclusão para {dominio}.')
        return False

    print(f'[LOG] ✅ Domínio {dominio} processado completamente!')
    return True

def main():
    """Função principal"""
    print('🚀 INICIANDO SCRIPT DE EXCLUSÃO DE EMAILS POR DOMÍNIO')
    print('='*60)

    # Lê domínios para apagar
    dominios = ler_dominios_para_apagar()

    if not dominios:
        print('[LOG] ❌ Nenhum domínio marcado para apagar encontrado!')
        print('[LOG] ℹ️ Verifique se o arquivo dominios.js existe e tem domínios marcados como "sim"')
        return

    print(f'\n[LOG] 📋 {len(dominios)} domínios serão APAGADOS:')
    for i, dom in enumerate(dominios, 1):
        print(f'[LOG]   {i}. {dom}')

    print('\n[LOG] ⚠️ ATENÇÃO: Esta operação irá APAGAR permanentemente emails!')

    if DEBUG_MODE:
        input('[LOG] ⏸️ Pressione Enter para continuar ou Ctrl+C para cancelar...')

    # Configurações do Chrome - remote debugging
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        print('[LOG] ✓ Chrome conectado via remote debugging')

        # Processa cada domínio
        sucessos = 0
        falhas = 0

        for i, dominio in enumerate(dominios, 1):
            print(f'\n[LOG] 📧 Processando domínio {i}/{len(dominios)}: {dominio}')

            try:
                if processar_dominio(driver, dominio):
                    sucessos += 1
                    print(f'[LOG] ✅ Domínio {dominio} APAGADO com sucesso!')
                else:
                    falhas += 1
                    print(f'[LOG] ❌ Falha ao processar domínio {dominio}')

                # Pausa entre domínios
                if DEBUG_MODE and i < len(dominios):
                    print('[LOG] ⏸️ Pausando 5 segundos antes do próximo domínio...')
                    time.sleep(5)

            except Exception as e:
                falhas += 1
                print(f'[ERRO] ❌ Exceção ao processar {dominio}: {e}')

        # Relatório final
        print(f'\n{"="*60}')
        print(f'[LOG] 📊 RELATÓRIO FINAL DE EXCLUSÕES:')
        print(f'{"="*60}')
        print(f'[LOG] ✅ Domínios apagados com sucesso: {sucessos}')
        print(f'[LOG] ❌ Domínios com falha: {falhas}')
        print(f'[LOG] 📋 Total processado: {len(dominios)}')
        print(f'[LOG] 🎯 Taxa de sucesso: {(sucessos/len(dominios)*100):.1f}%')

    except Exception as e:
        print(f'[ERRO] ❌ Falha na inicialização: {e}')
        print('[LOG] ⚠️ Certifique-se de que o Chrome está aberto com remote debugging na porta 9222')
        print('[LOG] ℹ️ Comando: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\Users\\Silas\\AppData\\Local\\Google\\Chrome\\User Data"')

    finally:
        try:
            print('[LOG] 🔒 Encerrando driver...')
            driver.quit()
            print('[LOG] ✓ Driver encerrado com segurança')
        except:
            pass

if __name__ == '__main__':
    main()
2