
# Script para limpeza automatizada do Gmail - Versão Simplificada
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

# Configurações
CHROME_PROFILE = r'C:\Users\Silas\AppData\Local\Google\Chrome\User Data\Profile 2'
DOMINIOS_JS = 'dominios.js'
DEBUG_MODE = True  # Mude para False quando confirmar funcionamento

def registrar_dominio(dominio, cancelado):
    """Registra domínio processado no arquivo dominios.js"""
    linha = f'{dominio} | sim | cancelado: {"sim" if cancelado else "nao"}\n'

    if not os.path.exists(DOMINIOS_JS):
        with open(DOMINIOS_JS, 'w', encoding='utf-8') as f:
            f.write(linha)
        return

    # Atualiza registro existente ou adiciona novo
    with open(DOMINIOS_JS, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    novas_linhas = []
    atualizado = False
    for l in linhas:
        if l.startswith(dominio):
            novas_linhas.append(linha)
            atualizado = True
        else:
            novas_linhas.append(l)

    if not atualizado:
        novas_linhas.append(linha)

    with open(DOMINIOS_JS, 'w', encoding='utf-8') as f:
        f.writelines(novas_linhas)

def dominio_ja_registrado(dominio):
    """Verifica se domínio já foi processado"""
    if not os.path.exists(DOMINIOS_JS):
        return False

    with open(DOMINIOS_JS, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    return any(l.startswith(dominio) for l in linhas)

def abrir_primeira_mensagem_nao_lida(driver):
    """Abre primeira mensagem não lida da inbox"""
    print('[LOG] ✓ Procurando primeira mensagem não lida...')

    for tentativa in range(3):
        try:
            mensagens = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.zA.zE'))
            )

            if not mensagens:
                print('[LOG] ❌ Nenhuma mensagem não lida encontrada.')
                return False

            mensagens[0].click()
            print(f'[LOG] ✓ Clique na primeira mensagem não lida (tentativa {tentativa+1}/3)')

            # Confirma abertura
            opened = False
            for _ in range(12):
                url = driver.current_url
                if '/inbox/' in url or '/inbox?' in url or '/inbox#' in url:
                    opened = True
                    break

                try:
                    responder = driver.find_element(By.CSS_SELECTOR, 'span.ams.bkH')
                    if responder.is_displayed() and 'Responder' in responder.text:
                        opened = True
                        break
                except Exception:
                    pass

                time.sleep(0.5)

            if opened:
                print('[LOG] ✓ Mensagem aberta e confirmada.')
                if DEBUG_MODE:
                    time.sleep(2)  # Pausa para observar
                return True
            else:
                print(f'[LOG] ⚠️ Não foi possível confirmar abertura (tentativa {tentativa+1}/3)')
                time.sleep(1)

        except Exception as e:
            print(f'[LOG] ❌ Erro ao abrir mensagem: {e}')

    print('[LOG] ❌ Falha ao abrir mensagem após 3 tentativas.')
    # Refresh + navega para inbox + reinicia loop
    try:
        driver.refresh()
        print('[LOG] 🔄 Página recarregada após falha.')
        time.sleep(2)
        driver.get('https://mail.google.com/mail/u/0/#inbox')
        print('[LOG] 🏠 Navegou para inbox após falha.')
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.zA'))
        )
        time.sleep(1)
    except Exception as e:
        print(f'[LOG] ❌ Erro ao tentar reiniciar após falha: {e}')
    return False

def extrair_dominio_remetente(driver):
    """Extrai domínio do remetente da mensagem aberta"""
    try:
        remetente_span = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span.gD[email]'))
        )
        email = remetente_span.get_attribute('email')
        if email and '@' in email:
            dominio = email.split('@')[-1].strip()
            print(f'[LOG] ✓ Domínio extraído: {dominio}')
            return dominio
        else:
            print(f'[LOG] ⚠️ Email inválido: {email}')
            return None
    except Exception as e:
        print(f'[LOG] ❌ Erro ao extrair domínio: {e}')
        return None

def cancelar_inscricao_se_necessario(driver, dominio):
    """Cancela inscrição se domínio ainda não foi processado"""
    if dominio_ja_registrado(dominio):
        print(f'[LOG] ⚠️ Domínio {dominio} já processado. Pulando cancelamento.')
        return False

    print(f'[LOG] 🔄 Tentando cancelar inscrição para {dominio}...')
    cancelado = False

    try:
        cancelar_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@class='Ca' and text()='Cancelar inscrição']"))
        )
        cancelar_btn.click()
        print('[LOG] ✓ Botão "Cancelar inscrição" clicado.')

        if DEBUG_MODE:
            time.sleep(2)

        # Tenta confirmar se aparece popup de confirmação OU "Acessar o site"
        try:
            # Primeiro tenta o botão de confirmação padrão
            confirmar_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@jsname='V67aGc' and contains(@class, 'mUIrbf-anl') and text()='Cancelar inscrição']"))
            )
            confirmar_btn.click()
            print('[LOG] ✓ Confirmação de cancelamento realizada.')
            cancelado = True
        except Exception:
            # Tenta localizar "Acessar o site" no popup
            try:
                acessar_site_btn = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, "//span[@jsname='V67aGc' and contains(@class, 'mUIrbf-anl') and text()='Acessar o site']"))
                )
                print('[LOG] ⚠️ Popup pede para acessar o site. Registrando como NÃO cancelado.')
                # Clica no botão de fechar popup
                try:
                    cancelar_popup_btn = driver.find_element(By.XPATH, "//span[@jsname='V67aGc' and contains(@class, 'mUIrbf-anl') and text()='Cancelar']")
                    cancelar_popup_btn.click()
                    print('[LOG] ✓ Popup fechado (botão Cancelar) após "Acessar o site".')
                except Exception:
                    print('[LOG] ⚠️ Não foi possível clicar no botão Cancelar do popup.')
                # Registra como não cancelado e retorna
                registrar_dominio(dominio, False)
                if DEBUG_MODE:
                    time.sleep(2)
                return False
            except Exception:
                print('[LOG] ⚠️ Sem popup de confirmação (cancelamento direto).')
                cancelado = True  # Assume que funcionou mesmo sem popup

    except Exception:
        print('[LOG] ⚠️ Botão "Cancelar inscrição" não encontrado.')

    if DEBUG_MODE and cancelado:
        time.sleep(2)

    return cancelado

def filtrar_mensagens_similares(driver, dominio):
    """Filtra mensagens por domínio específico"""
    print(f'[LOG] 🔍 Filtrando mensagens do domínio: {dominio}')

    try:
        # 1. Clica no botão "Mais opções de mensagem" (ícone de três pontos)
        mais_opcoes_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="Mais opções de mensagem"]'))
        )
        mais_opcoes_btn.click()
        print('[LOG] ✓ Botão "Mais opções de mensagem" clicado.')
        time.sleep(0.5)

        # 2. Clica em "Filtrar mensagens como esta"
        filtrar_como_esta_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Filtrar mensagens como esta')]"))
        )
        filtrar_como_esta_btn.click()
        print('[LOG] ✓ "Filtrar mensagens como esta" clicado.')
        time.sleep(1.5)  # Aguarda carregamento dos resultados

        # Clica em pesquisar
        pesquisar_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="Testar pesquisa"]'))
        )
        pesquisar_btn.click()

        print('[LOG] ✓ Filtro aplicado com sucesso.')
        time.sleep(1.5)  # Aguarda carregamento dos resultados
        return True

    except Exception as e:
        print(f'[LOG] ❌ Erro ao filtrar mensagens: {e}')
        return False

def zerar_dominio_filtrado(driver):
    """Marca todas as mensagens filtradas como lidas"""
    print('[LOG] 🧹 Iniciando limpeza do domínio filtrado...')

    while True:
        try:
            # Aguarda carregamento das mensagens
            WebDriverWait(driver, 10).until(
                lambda d: len([l for l in d.find_elements(By.CSS_SELECTOR, 'tr.zA') if l.is_displayed()]) > 0
            )
        except Exception:
            print('[LOG] ⚠️ Timeout ao aguardar mensagens.')

        # Verifica se há mensagens não lidas
        linhas_nao_lidas = [l for l in driver.find_elements(By.CSS_SELECTOR, 'tr.zA.zE') if l.is_displayed()]

        if linhas_nao_lidas:
            print(f'[LOG] 📧 Encontradas {len(linhas_nao_lidas)} mensagens não lidas.')

            # Busca botão "Mais opções"
            btn = None
            for _ in range(10):
                candidatos = driver.find_elements(By.XPATH,
                    "//div[@aria-label='Mais opções de e-mail' or @data-tooltip='Mais']"
                )
                for b in candidatos:
                    if b.is_enabled() and b.is_displayed():
                        btn = b
                        break
                if btn:
                    break
                time.sleep(0.5)

            if btn:
                btn.click()
                print('[LOG] ✓ Menu "Mais opções" aberto.')

                try:
                    marcar_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Marcar todas como lidas')]"))
                    )
                    marcar_btn.click()
                    print('[LOG] ✓ "Marcar todas como lidas" executado.')
                    time.sleep(1.2)
                except Exception as e:
                    print(f'[LOG] ❌ Erro ao marcar como lida: {e}')
                    break
            else:
                print('[LOG] ❌ Botão "Mais opções" não encontrado.')
                break

            continue

        print('[LOG] ✓ Nenhuma mensagem não lida nesta página.')

        # Verifica se há mais páginas (botão "Anteriores")
        btn_anteriores = None
        btns = driver.find_elements(By.XPATH, 
            "//div[contains(@data-tooltip,'Anteriores') and not(contains(@class,'T-I-JW'))]")

        for b in btns:
            aria_disabled = b.get_attribute('aria-disabled')
            if b.is_displayed() and b.is_enabled() and aria_disabled != 'true':
                btn_anteriores = b
                break

        if btn_anteriores:
            btn_anteriores.click()
            print('[LOG] ✓ Navegando para página anterior...')
            time.sleep(1.2)
            continue
        else:
            print('[LOG] ✓ Domínio completamente limpo!')
            break

def voltar_inbox_simplificado(driver):
    """Volta para inbox sem refresh - versão simplificada"""
    print('[LOG] 🏠 Voltando para inbox...')

    driver.get('https://mail.google.com/mail/u/0/#inbox')

    # Aguarda carregamento
    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.zA'))
    )

    print('[LOG] ✓ Inbox carregada.')
    if DEBUG_MODE:
        time.sleep(1)

def processar_mensagem(driver):
    """Processa uma mensagem completa seguindo o fluxo definido"""
    print('\n' + '='*50)
    print('[LOG] 🚀 INICIANDO PROCESSAMENTO DE MENSAGEM')
    print('='*50)

    # 1. Abrir primeira mensagem não lida
    if not abrir_primeira_mensagem_nao_lida(driver):
        return False

    # 2. Extrair domínio
    dominio = extrair_dominio_remetente(driver)
    if not dominio:
        print('[LOG] ❌ Não foi possível extrair domínio. Pulando.')
        return True  # Continua para próxima mensagem

    # 3 e 4. Cancelar inscrição se necessário
    cancelado = cancelar_inscricao_se_necessario(driver, dominio)

    # 5. Registrar domínio
    registrar_dominio(dominio, cancelado)
    print(f'[LOG] ✓ Domínio registrado: {dominio} (cancelado: {"sim" if cancelado else "não"})')

    # 6. Filtrar mensagens similares
    if not filtrar_mensagens_similares(driver, dominio):
        print('[LOG] ❌ Erro na filtragem. Continuando...')
        return True

    # 7. Zerar domínio filtrado
    zerar_dominio_filtrado(driver)

    # 8. Voltar para inbox
    voltar_inbox_simplificado(driver)

    print('[LOG] ✅ MENSAGEM PROCESSADA COM SUCESSO!')
    return True

def main():
    """Função principal"""
    print('🤖 INICIANDO LIMPEZA AUTOMATIZADA DO GMAIL')
    print(f'Debug Mode: {"ON" if DEBUG_MODE else "OFF"}')
    print('-' * 50)

    # Conecta ao Chrome já aberto
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get('https://mail.google.com/mail/u/0/#inbox')
        time.sleep(2)

        while True:
            if not processar_mensagem(driver):
                print('[LOG] ❌ Não há mais mensagens para processar.')
                break

    except KeyboardInterrupt:
        print('\n[LOG] ⏹️ Execução interrompida pelo usuário.')
    except Exception as e:
        print(f'\n[LOG] ❌ Erro crítico: {e}')
    finally:
        try:
            driver.quit()
            print('[LOG] ✓ Driver encerrado com segurança.')
        except:
            pass

if __name__ == '__main__':
    main()
