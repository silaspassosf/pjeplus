from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def add_botao_anexar_selenium(driver):
    """
    Adiciona um botão flutuante na página para ativar a ação automatizada de anexar documentos.
    """
    driver.execute_script('''
        if (!document.getElementById('btn-anexar-auto')) {
            var btn = document.createElement('button');
            btn.id = 'btn-anexar-auto';
            btn.innerText = 'Anexar Documento Automático';
            btn.style.position = 'fixed';
            btn.style.top = '90px';
            btn.style.right = '10px';
            btn.style.zIndex = 9999;
            btn.style.background = '#8e24aa';
            btn.style.color = '#fff';
            btn.style.padding = '10px 16px';
            btn.style.border = 'none';
            btn.style.borderRadius = '6px';
            btn.style.fontSize = '16px';
            btn.onclick = function() { alert("Execute o comando Python para anexar documento automático!"); };
            document.body.appendChild(btn);
        }
    ''')

def acao_bt_anexar_selenium(driver, config):
    """
    Executa o fluxo automatizado de anexar documentos, fiel ao gigs-plugin.js (acao_bt_aaAnexar).
    config: dict com chaves tipo, descricao, sigilo, modelo, assinar, extras, etc.
    """
    try:
        print(f"[ANEXAR] Iniciando ação automatizada de anexar: {config.get('tipo','')} - {config.get('modelo','')}")
        # 1. Clicar no botão de anexar documentos (fa-paperclip)
        try:
            btn_anexar = driver.find_element(By.ID, 'pjextension_bt_detalhes_4')
            btn_anexar.click()
            print('[ANEXAR] Botão de anexar documentos clicado.')
            time.sleep(1)
        except Exception:
            print('[ANEXAR] Botão de anexar documentos não encontrado ou já clicado.')
        # 2. PDF?
        if config.get('modelo','').lower() == 'pdf':
            try:
                switch_pdf = driver.find_element(By.CSS_SELECTOR, 'input[role="switch"]')
                switch_pdf.click()
                print('[ANEXAR] Switch PDF ativado.')
                time.sleep(0.5)
            except Exception:
                print('[ANEXAR] Switch PDF não encontrado.')
        # 3. Preencher tipo
        tipo = config.get('tipo') or 'Certidão'
        try:
            campo_tipo = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Tipo de Documento"]')
            campo_tipo.clear()
            campo_tipo.send_keys(tipo)
            campo_tipo.send_keys(Keys.ENTER)
            print(f"[ANEXAR] Tipo de documento selecionado: {tipo}")
            time.sleep(0.5)
        except Exception as e:
            print(f'[ANEXAR][ERRO] Falha ao selecionar tipo: {e}')
        # 4. Preencher descrição
        if config.get('descricao'):
            try:
                campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                campo_desc.clear()
                campo_desc.send_keys(config['descricao'])
                print(f"[ANEXAR] Descrição preenchida: {config['descricao']}")
            except Exception:
                print('[ANEXAR] Campo de descrição não encontrado.')
        # 5. Sigilo
        sigilo = (config.get('sigilo') or 'nao').lower()
        if 'sim' in sigilo:
            try:
                chk_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                if not chk_sigilo.is_selected():
                    chk_sigilo.click()
                print('[ANEXAR] Sigilo ativado.')
                time.sleep(0.5)
            except Exception:
                print('[ANEXAR] Campo de sigilo não encontrado.')
        # 6. Escolha do modelo
        if config.get('modelo') and config.get('modelo','').lower() != 'pdf':
            try:
                campo_modelo = driver.find_element(By.CSS_SELECTOR, 'input[id="inputFiltro"]')
                campo_modelo.clear()
                campo_modelo.send_keys(config['modelo'])
                campo_modelo.send_keys(Keys.ENTER)
                print(f"[ANEXAR] Modelo selecionado: {config['modelo']}")
                time.sleep(1)
                modelo_item = driver.find_element(By.XPATH, f"//div[@role='treeitem' and contains(.,'{config['modelo']}')]")
                modelo_item.click()
                print('[ANEXAR] Modelo inserido no editor.')
            except Exception as e:
                print(f'[ANEXAR][ERRO] Não foi possível selecionar/inserir modelo: {e}')
        # 7. Upload de PDF (se modelo for PDF)
        if config.get('modelo','').lower() == 'pdf':
            try:
                btn_upload = driver.find_element(By.CSS_SELECTOR, 'label.upload-button')
                btn_upload.click()
                print('[ANEXAR] Botão de upload de PDF clicado. Aguarde seleção manual do arquivo.')
                # Espera o nome do arquivo aparecer
                for _ in range(120):
                    if driver.find_elements(By.CSS_SELECTOR, 'span.nome-arquivo-pdf'):
                        print('[ANEXAR] PDF carregado.')
                        break
                    time.sleep(0.5)
                # Se descrição vazia, preenche com nome do arquivo
                if not config.get('descricao'):
                    try:
                        el_pdf = driver.find_element(By.CSS_SELECTOR, 'span.nome-arquivo-pdf')
                        nome_pdf = el_pdf.text.replace('.pdf','')
                        campo_desc = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Descrição"]')
                        campo_desc.clear()
                        campo_desc.send_keys(nome_pdf)
                        print(f"[ANEXAR] Descrição preenchida com nome do PDF: {nome_pdf}")
                    except Exception:
                        print('[ANEXAR] Não foi possível preencher descrição com nome do PDF.')
            except Exception as e:
                print(f'[ANEXAR][ERRO] Upload de PDF: {e}')
        # 8. Juntada de depoimentos/anexos
        extras = config.get('extras','')
        if '[anexos]' in extras.lower() or extras == 'ID997_Anexar Depoimento':
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
                btn_salvar.click()
                print('[ANEXAR] Documento salvo para anexos.')
                time.sleep(1)
                guia_anexos = driver.find_element(By.CSS_SELECTOR, 'div[aria-posinset="2"]')
                guia_anexos.click()
                print('[ANEXAR] Guia Anexos aberta.')
                time.sleep(0.5)
                btn_upload = driver.find_element(By.CSS_SELECTOR, 'label.upload-button')
                btn_upload.click()
                print('[ANEXAR] Botão de upload de anexo clicado.')
                # Espera o salvamento do documento (pode ser ajustado conforme DOM real)
                time.sleep(2)
                if extras == 'ID997_Anexar Depoimento':
                    guia_anexos.click()
                    print('[ANEXAR] Fluxo de depoimento finalizado.')
                    return True
            except Exception as e:
                print(f'[ANEXAR][ERRO] Juntada de anexos: {e}')
        # 9. Assinar ou salvar
        assinar = (config.get('assinar') or 'nao').lower()
        if assinar == 'sim':
            try:
                btn_assinar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Assinar documento e juntar ao processo"]')
                btn_assinar.click()
                print('[ANEXAR] Documento assinado e juntado ao processo.')
                time.sleep(2)
            except Exception as e:
                print(f'[ANEXAR][ERRO] Assinar documento: {e}')
        else:
            try:
                btn_salvar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Salvar"]')
                btn_salvar.click()
                print('[ANEXAR] Documento salvo.')
                time.sleep(1)
            except Exception as e:
                print(f'[ANEXAR][ERRO] Salvar documento: {e}')
        print('[ANEXAR] Fluxo de anexar documento automatizado finalizado.')
        return True
    except Exception as e:
        print(f'[ANEXAR][ERRO] {e}')
        return False
