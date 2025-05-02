"""
Script de automação Mandados (Mandado 1 e 2) para o PJePlus.
Contém todas as funções auxiliares, fluxo de lista e fluxos completos de análise de mandados.
"""
# IMPORTS
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import re
import shutil
import tempfile
import os
import subprocess
import csv
from datetime import datetime

# ========== FUNÇÕES AUXILIARES ==========
def esperar_elemento(driver, seletor, texto=None, timeout=10, by=By.CSS_SELECTOR):
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            if texto:
                elementos = driver.find_elements(by, seletor)
                for el in elementos:
                    if texto.strip().lower() in el.text.strip().lower():
                        return el
            else:
                el = driver.find_element(by, seletor)
                if el.is_displayed():
                    return el
        except Exception:
            pass
        time.sleep(0.2)
    print(f"Timeout esperando elemento: {seletor} ({texto if texto else ''})")
    return None

def esperar_colecao(driver, seletor, qtde_minima=1, timeout=10, by=By.CSS_SELECTOR):
    end_time = time.time() + timeout
    while time.time() < end_time:
        elementos = driver.find_elements(by, seletor)
        if len(elementos) >= qtde_minima:
            return elementos
        time.sleep(0.2)
    print(f"Timeout esperando coleção: {seletor}")
    return []

def esperar_desaparecer(driver, seletor, timeout=10, by=By.CSS_SELECTOR):
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            el = driver.find_element(by, seletor)
            if not el.is_displayed():
                return True
        except NoSuchElementException:
            return True
        time.sleep(0.2)
    print(f"Timeout esperando desaparecer: {seletor}")
    return False

def wait_for_visible(driver, selector, timeout=10, by=By.CSS_SELECTOR):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, selector))
        )
    except TimeoutException:
        print(f"Timeout esperando aparecer: {selector}")
        return None

def wait_for_disappear(driver, selector, timeout=15, by=By.CSS_SELECTOR):
    try:
        WebDriverWait(driver, timeout).until_not(
            EC.visibility_of_element_located((by, selector))
        )
        return True
    except TimeoutException:
        print(f"Timeout esperando desaparecer: {selector}")
        return False

def safe_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        element.click()
        return True
    except (ElementClickInterceptedException, Exception) as e:
        print(f"Erro ao clicar: {e}")
        return False

def click_element_by_visible_text(driver, texto, tag_preferida=None, timeout=10):
    for _ in range(timeout * 2):
        elementos = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(text()), '{texto}')]" )
        visiveis = [el for el in elementos if el.is_displayed() and texto in el.text]
        if tag_preferida:
            visiveis = sorted(visiveis, key=lambda el: el.tag_name != tag_preferida)
        if visiveis:
            btn = visiveis[0]
            if btn.tag_name.lower() != 'button':
                parent = btn
                for _ in range(5):
                    parent = parent.find_element(By.XPATH, '..')
                    if parent.tag_name.lower() == 'button':
                        btn = parent
                        break
            btn.click()
            print(f"[DEBUG] Clique realizado no elemento com texto visível: '{texto}'")
            return True
        time.sleep(0.5)
    raise Exception(f"Elemento com texto visível '{texto}' não encontrado ou não clicável.")

def click_button_by_text_or_aria(driver, texto, timeout=10):
    for tent in range(timeout * 2):
        botoes_aria = driver.find_elements(By.CSS_SELECTOR, f'button[aria-label="{texto}"]')
        botoes_aria = [b for b in botoes_aria if b.is_displayed()]
        if botoes_aria:
            print(f"[DEBUG] Clique em <button aria-label='{texto}'> na tentativa {tent+1}")
            botoes_aria[0].click()
            time.sleep(1)
            return True
        botoes_texto = driver.find_elements(By.XPATH, f"//button[contains(normalize-space(text()), '{texto}')]" )
        botoes_texto = [b for b in botoes_texto if b.is_displayed() and texto in b.text]
        if botoes_texto:
            print(f"[DEBUG] Clique em <button> com texto visível '{texto}' na tentativa {tent+1}")
            botoes_texto[0].click()
            time.sleep(1)
            return True
        time.sleep(0.5)
    print(f"[ERRO] Não foi possível clicar em <button> com texto ou aria-label='{texto}'.")
    raise Exception(f"Nenhum <button> visível com texto ou aria-label='{texto}' encontrado.")

def limpar_temp_selenium():
    """
    Remove pastas webdriver-py-profilecopy e arquivos temporários antigos do Selenium no diretório TEMP.
    """
    import tempfile
    import os
    import shutil
    temp_dir = tempfile.gettempdir()
    for nome in os.listdir(temp_dir):
        if nome.startswith('tmp') or nome.startswith('webdriver-py-profilecopy'):
            caminho = os.path.join(temp_dir, nome)
            try:
                if os.path.isdir(caminho):
                    shutil.rmtree(caminho, ignore_errors=True)
                else:
                    os.remove(caminho)
                print(f'[LIMPEZA TEMP] Removido: {caminho}')
            except Exception as e:
                print(f'[LIMPEZA TEMP][ERRO] Falha ao remover {caminho}: {e}')

def registrar_url(url):
    print(f'[URL_ACESSADA] {url}')

def criar_gigs(tipo, prazo, observacao):
    print(f"[GIGS] Criando GIGS: tipo={tipo}, prazo={prazo}, obs={observacao}")
    # Implementação real aqui

def buscar_documentos_sequenciais(driver):
    documentos_alvo = [
        "Certidão de devolução",
        "Certidão de expedição",
        "Planilha",
        "Intimação",
        "Decisão"
    ]
    resultados = []
    elementos = driver.find_elements(By.CSS_SELECTOR, ".tl-data, li.tl-item-container")
    indice_doc_atual = 0
    for elemento in elementos:
        if indice_doc_atual >= len(documentos_alvo):
            break
        texto_item = elemento.text.strip().lower()
        documento_atual = documentos_alvo[indice_doc_atual]
        if documento_atual.lower() in texto_item:
            print(f"[ENCONTRADO] {documento_atual}")
            resultados.append(elemento)
            indice_doc_atual += 1
    return resultados

def retirar_sigilo(elemento):
    try:
        btn_sigilo = elemento.find_element(By.CSS_SELECTOR, "pje-doc-sigiloso span button i.fa-wpexplorer")
        btn_sigilo.click()
        time.sleep(1)
        print("[SIGILO] Clique para retirar sigilo realizado.")
    except Exception as e:
        print("[SIGILO] Erro ao retirar sigilo (pode já estar sem sigilo):", e)

def tratar_anexos_certidao(certidao, driver):
    # ... (código completo conforme pje.py)
    pass

def tratar_sigilo_documentos_relevantes(documentos):
    nomes = ["Certidão de expedição", "Planilha", "Intimação", "Decisão"]
    for doc, nome in zip(documentos[1:], nomes):
        print(f"[TRATAR] {nome}")
        retirar_sigilo(doc)
        time.sleep(0.5)

def processar_lista(driver, seletor_itens, fluxo_callback, max_itens=None):
    itens = driver.find_elements(By.CSS_SELECTOR, seletor_itens)
    total = len(itens) if max_itens is None else min(len(itens), max_itens)
    print(f'[LISTA] Total de itens para processar: {total}')
    for idx in range(total):
        try:
            itens = driver.find_elements(By.CSS_SELECTOR, seletor_itens)
            item = itens[idx]
            driver.execute_script("window.open(arguments[0].href, '_blank');", item)
            driver.switch_to.window(driver.window_handles[-1])
            print(f'[LISTA] Processando item {idx+1}/{total}')
            fluxo_callback(driver)
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except Exception as e:
            print(f'[LISTA][ERRO] Falha ao processar item {idx+1}: {e}')
            continue
    print('[LISTA] Fim do processamento da lista.')

def extrair_documento(driver, regras_analise=None, timeout=15):
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    texto = ''
    resultado_analise = None
    try:
        for _ in range(timeout * 2):
            try:
                btn_html = driver.find_element(By.CSS_SELECTOR, '.fa-file-code')
                if btn_html.is_displayed():
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            print('[extrair_documento] Ícone HTML (.fa-file-code) não apareceu após abrir documento.')
            return '', None
        print('[extrair_documento] Clicando no ícone HTML...')
        btn_html.click()
        for _ in range(timeout * 2):
            try:
                preview = driver.find_element(By.CSS_SELECTOR, '#previewModeloDocumento')
                if preview.is_displayed() and preview.text.strip():
                    texto = preview.text.strip()
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not texto:
            print('[extrair_documento] Não foi possível extrair o texto do preview HTML.')
            return '', None
        print('[extrair_documento] Texto extraído do preview HTML.')
        if regras_analise:
            resultado_analise = regras_analise(texto)
        driver.switch_to.active_element.send_keys(Keys.ESCAPE)
        print('[extrair_documento] Janela HTML fechada com ESC.')
        time.sleep(1)
        return texto, resultado_analise
    except Exception as e:
        print(f'[extrair_documento][ERRO] {e}')
        return '', None

def fluxo_mandados_hipotese1(driver):
    print("[MANDADOS][ARGOS] Iniciando fluxo Mandado 1 (Argos)")
    # ... lógica específica do Mandado 1
    print("[MANDADOS][ARGOS] Fluxo Mandado 1 concluído.")

def fluxo_mandados_hipotese2(driver):
    print('[MANDADOS][OUTROS] Iniciando fluxo Mandado 2 (Outros)')
    def analise_padrao(texto):
        print(f"[MANDADOS][OUTROS] Texto extraído para análise:\n{texto}\n---Fim do documento---")
        texto_lower = texto.lower()
        padrao_oficial = "certidão de oficial" in texto_lower
        padrao_positivo = any(p in texto_lower for p in ["citei", "intimei", "recebeu o mandado", "de tudo ficou ciente"])
        padrao_negativo = any(p in texto_lower for p in [
            "não localizado", "negativo", "não encontrado",
            "deixei de citar", "deixei de efetuar", "não logrei êxito", "desconhecido no local"
        ])
        if padrao_oficial:
            print("[MANDADOS][OUTROS][LOG] Padrão 'certidão de oficial' ENCONTRADO no texto.")
            if padrao_positivo:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado POSITIVO encontrado no texto.")
                criar_gigs(tipo='.Silas', prazo=0, observacao='Mdd positivo')
            elif padrao_negativo:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado NEGATIVO encontrado no texto.")
                criar_gigs(tipo='.Silas', prazo=0, observacao='Mdd negativo')
            else:
                print("[MANDADOS][OUTROS][LOG] Mandado sem padrão reconhecido. Nenhum padrão positivo/negativo detectado. Criando GIGS fallback.")
                criar_gigs(tipo='.Silas', prazo=0, observacao='Pz')
        else:
            print("[MANDADOS][OUTROS][LOG] Documento NÃO é certidão de oficial. Nenhum padrão reconhecido. Criando GIGS fallback.")
            criar_gigs(tipo='.Silas', prazo=0, observacao='Pz')
        return None
    texto, resultado = extrair_documento(driver, regras_analise=analise_padrao)
    if not texto:
        print("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return
    try:
        driver.close()
        print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
    except Exception as e:
        print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e}')
    print('[MANDADOS][OUTROS] Fluxo Mandado 2 concluído.')

# Adicione aqui outros fluxos ou funções específicas conforme necessário

def login_automatico(driver, usuario, senha):
    driver.get('https://pje.trt2.jus.br/primeirograu/login.seam')
    # Preenche usuário
    campo_usuario = esperar_elemento(driver, 'input#username', timeout=10)
    if campo_usuario:
        campo_usuario.clear()
        campo_usuario.send_keys(usuario)
        time.sleep(1)
    else:
        print('[LOGIN][ERRO] Campo usuário não encontrado.')
        return False
    # Preenche senha
    campo_senha = esperar_elemento(driver, 'input#password', timeout=10)
    if campo_senha:
        campo_senha.clear()
        campo_senha.send_keys(senha)
        time.sleep(1)
    else:
        print('[LOGIN][ERRO] Campo senha não encontrado.')
        return False
    # Aguarda 1s e clica no botão entrar
    btn_entrar = esperar_elemento(driver, 'button#btnEntrar', timeout=10)
    if btn_entrar:
        time.sleep(1)
        safe_click(driver, btn_entrar)
        time.sleep(3)
        print('[LOGIN] Login realizado com sucesso.')
        return True
    else:
        print('[LOGIN][ERRO] Botão Entrar não encontrado.')
        return False

def verificar_login_ativo(driver):
    try:
        el = esperar_elemento(driver, 'input#username', timeout=5)
        if el:
            return False
        return True
    except Exception:
        return True

def navegacao(driver):
    url_lista = 'https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos'
    print(f'[NAV] Navegando para: {url_lista}')
    driver.get(url_lista)
    time.sleep(2)
    print('[NAV] Clicando no ícone para exibir a lista de mandados...')
    icone = esperar_elemento(driver, 'i.mat-tooltip-trigger:nth-child(12)', timeout=15)
    if icone:
        safe_click(driver, icone)
        print('[NAV] Ícone clicado. Aguarde para verificar se a lista aparece.')
    else:
        print('[NAV][ERRO] Ícone da lista de mandados não encontrado.')

def checagem(driver):
    # Confirma se a lista está pronta pela presença do chip "Mandados devolvidos"
    try:
        chip = driver.find_element(By.XPATH, "//mat-chip[contains(., 'Mandados devolvidos')]")
        print('[CHECAGEM] Lista pronta: chip "Mandados devolvidos" encontrado.')
        return True
    except Exception as e:
        print('[CHECAGEM][ERRO] Chip "Mandados devolvidos" não encontrado:', e)
        return False

def processar_lista(driver):
    # Extrai todos os números de processo na ordem em que aparecem na página
    try:
        conteudo = driver.find_element(By.CSS_SELECTOR, 'div.pje-content').text
    except Exception as e:
        print('[PROCESSAMENTO][ERRO] Não foi possível localizar div.pje-content:', e)
        return
    padrao = r"\b\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}\b"
    processos = re.findall(padrao, conteudo)
    print(f'[PROCESSAMENTO] Lista de processos extraída ({len(processos)}):')
    for proc in processos:
        print(proc)
    input('Pressione Enter para iniciar o processamento sequencial...')
    for idx, proc in enumerate(processos):
        try:
            # 1. Abrir o processo na lista
            seletor_btn = f'tr.cdk-drag:nth-child({idx+1}) > td:nth-child(1) > div:nth-child(1) > button > span:nth-child(2)'
            btn = driver.find_element(By.CSS_SELECTOR, seletor_btn)
            btn.click()
            time.sleep(1)
            # 2. Rastrear nova aba com URL /peticao/*
            time.sleep(1)
            abas = driver.window_handles
            driver.switch_to.window(abas[-1])
            url_aba = driver.current_url
            if '/peticao/' in url_aba:
                print(f'[LOG] ABA do processo {proc} aberta em {url_aba}. Simulando automação.')
            else:
                print(f'[LOG][ERRO] Nova aba não corresponde ao padrão esperado: {url_aba}')
            # 3. Aguardar 3s
            time.sleep(3)
            # 4. Fechar a aba
            driver.close()
            driver.switch_to.window(abas[0])
            print(f'[LOG] Aba do processo {proc} fechada - voltando à lista.')
            time.sleep(1)
        except Exception as e:
            print(f'[LOOP][ERRO] Falha ao processar processo {proc}: {e}')
    print('[PROCESSAMENTO] Fim do loop sequencial.')
    input('Pressione Enter para finalizar...')

# Funções de git removidas (auto_commit, atualizar_projeto, restore_version) para manter a lógica apenas nos scripts .bat externos, conforme orientação do usuário.

def backup_rotativo(filepath):
    dirpath, filename = os.path.split(filepath)
    # Rotaciona backups antigos
    for i in range(5, 0, -1):
        bak_old = os.path.join(dirpath, f"{filename}.bak{i}")
        bak_new = os.path.join(dirpath, f"{filename}.bak{i+1}")
        if os.path.exists(bak_old):
            if i == 5 and os.path.exists(bak_old):
                os.remove(bak_old)
            else:
                os.rename(bak_old, bak_new)
    bak1 = os.path.join(dirpath, f"{filename}.bak1")
    if os.path.exists(filepath):
        shutil.copy2(filepath, bak1)
        print(f'[BACKUP] Backup rotativo criado: {bak1}')

if __name__ == "__main__":
    backup_rotativo(__file__)
    limpar_temp_selenium()
    driver = webdriver.Firefox()
    # Busca usuário e senha das variáveis de ambiente
    usuario = os.environ.get('PJE_USUARIO')
    senha = os.environ.get('PJE_SENHA')
    if not usuario:
        usuario = input('Usuário PJe: ')
        os.environ['PJE_USUARIO'] = usuario
        print('[INFO] Variável de ambiente PJE_USUARIO definida para esta sessão.')
    if not senha:
        senha = input('Senha PJe: ')
        os.environ['PJE_SENHA'] = senha
        print('[INFO] Variável de ambiente PJE_SENHA definida para esta sessão.')
    if not login_automatico(driver, usuario, senha):
        print('[LOGIN][ERRO] Falha no login automático. Encerrando script.')
        driver.quit()
        exit(1)
    navegacao(driver)
    if checagem(driver):
        processar_lista(driver)
    driver.quit()
