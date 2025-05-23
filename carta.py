from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from datetime import datetime
import re
from Fix import extrair_dados_processo
from Fix import extrair_documento

def carta(driver, log=True):
    """
    Automação do fluxo de consulta eCarta:
    Busca intimações na timeline (não na lista de documentos), apenas da data mais recente.
    Loga a data, IDs e texto completo das intimações dessa data.
    O restante do fluxo (eCarta, anexos) permanece igual.
    """
    try:
        notification_data = []
        # 1. Identifica o bloco com intimações da última data
        timeline = driver.find_element(By.CSS_SELECTOR, 'ul.pje-timeline')
        items = timeline.find_elements(By.XPATH, './li')
        first_date_found = False
        first_date = None
        in_first_block = False
        intims = []
        for idx, item in enumerate(items):
            # Detecta bloco de data
            try:
                date_div = item.find_element(By.CSS_SELECTOR, 'div.tl-data')
                date_text = date_div.text.strip()
                match = re.search(r'(\d{2}) (\w{3})\. (\d{4})', date_text)
                if match:
                    meses = {'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'}
                    d, m, y = match.groups()
                    m = meses.get(m.lower(), '01')
                    this_date = f'{d}/{m}/{y}'
                    if not first_date_found:
                        first_date = this_date
                        first_date_found = True
                        in_first_block = True
                        if log:
                            print(f'[CARTA][INFO] Primeira data da timeline: {first_date}')
                    else:
                        if log:
                            print(f'[CARTA][INFO] Nova data encontrada, encerrando busca de intimações.')
                        break
            except Exception:
                pass
            if not in_first_block:
                break
            # Procura por Intimação via link e aria-label
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento')
                aria = link.get_attribute('aria-label') or ''
                texto_link = link.text.strip().lower()
                if 'intimação' in texto_link or 'intimação' in aria.lower():
                    el_id = item.get_attribute('id')
                    intims.append({'element': item, 'link': link, 'id': el_id, 'aria': aria, 'texto': texto_link})
                else:
                    break  # Parar ao encontrar outro tipo de documento
            except Exception:
                break  # Parar ao não encontrar link de intimação
        if log:
            print(f'[CARTA][INFO] Data do primeiro bloco: {first_date}')
            print(f'[CARTA][INFO] Intimações localizadas na primeira data:')
            for i, intim in enumerate(intims):
                print(f'  [CARTA][INFO] Intimação {i+1}: id={intim["id"]}, aria-label={intim["aria"]}, texto-link={intim["texto"]}')
        # 2. Seleciona cada intimação, extrai conteúdo integral e filtra por frase
        process_number = None
        for i, intim in enumerate(intims):
            el = intim['element']
            aria = intim['aria']
            id_match = re.search(r'Id: ([a-f0-9]+)', aria)
            id_curto = id_match.group(1) if id_match else intim['id']
            driver.execute_script('arguments[0].scrollIntoView(true);', el)
            intim['link'].click()
            time.sleep(1)
            texto_completo, _ = extrair_documento(driver, log=log)
            if not texto_completo:
                if log:
                    print(f'  [CARTA][ERRO] Não foi possível extrair o texto da intimação id={id_curto}')
                break
            # 4. Confirma que é de correio pelo trecho
            if 'NAO APAGAR NENHUM CARACTERE' not in texto_completo.upper():
                if log:
                    print(f'  [CARTA][FIM] Intimação id={id_curto} não é correio (filtro de frase). Interrompendo registro.')
                break
            # 5. Registra id e número do processo
            if not process_number:
                proc_match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})', texto_completo)
                if proc_match:
                    process_number = proc_match.group(1)
                    if log:
                        print(f'  [CARTA][INFO] Número do processo extraído do texto: {process_number}')
            if log:
                print(f'  [CARTA][ARMAZENADO] id={id_curto}, processo={process_number}')
            notification_data.append({
                "id": id_curto,
                "processo": process_number,
                "content": texto_completo
            })
        if log:
            print(f'[CARTA][RESULT] IDs e processo das intimações CORREIO extraídas:')
            for i, intim in enumerate(notification_data):
                print(f'  [CARTA][RESULT] Intimação {i+1}: id={intim["id"]}, processo={intim["processo"]}, resumo={intim["content"][:60]}')
        if not notification_data:
            if log:
                print('[CARTA] Nenhuma intimação relevante encontrada.')
            return False
        # 7. Abrir site ecarta com o número do processo
        ecarta_url = f"https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo={process_number}"
        driver.get(ecarta_url)
        # Pausa para garantir que a página da eCarta carregue completamente antes de prosseguir
        time.sleep(2)
        # 5. Login e busca na eCarta
        try:
            try:
                username_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#input_user"))
                )
                if username_field:
                    username_field.send_keys("s164283")
                    driver.find_element(By.CSS_SELECTOR, "#input_password").send_keys("59Justdoit!1")
                    driver.find_element(By.CSS_SELECTOR, "input.btn").click()
                    time.sleep(2)
            except TimeoutException:
                pass  # Já logado
            # Espera tabela de resultados
            ecarta_data = []
            try:
                table = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
                )
                rows = table.find_elements(By.CSS_SELECTOR, "tr")
                for notification in notification_data:
                    for row in rows:
                        if notification["id"] in row.text:
                            ecarta_data.append(row.text)
                            break
            except Exception as e:
                if log:
                    print(f"[CARTA] Erro ao extrair dados da eCarta: {e}")
        finally:
            # NÃO fechar a aba da eCarta, manter aberta
            driver.switch_to.window(original_window)
        # 6. Chama anexos.def_carta com os dados coletados
        if ecarta_data:
            try:
                from anexos import def_carta as anexos_def_carta
                anexos_def_carta(driver, ecarta_data)
            except Exception as e:
                if log:
                    print(f"[CARTA] Erro ao chamar anexos.def_carta: {e}")
                return False
        return True
    except Exception as e:
        if log:
            print(f"[CARTA] Erro geral no fluxo carta: {e}")
        return False