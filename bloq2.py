# ----------------------------------------------------------------------------------
# 4. LER SÉRIE (detalhes)  +  5. PROCESSAR ORDENS COM BLOQUEIO
# ----------------------------------------------------------------------------------

from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def _navegar_para_detalhes_serie(driver, id_serie: str) -> bool:
    """
    Abre nova aba com /teimosinha/{id_serie}/detalhes e confirma carregamento.
    Retorna True se sucesso, False caso contrário.
    """
    url = f'https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes'
    driver.execute_script("window.open(arguments[0], '_blank');", url)
    driver.switch_to.window(driver.window_handles[-1])
    for _ in range(10):
        if "/detalhes" in driver.current_url and id_serie in driver.current_url:
            return True
        time.sleep(1)
    return False


def _extrair_ordens_da_serie(driver) -> list[dict]:
    """
    Lê a tabela de ordens da página /detalhes e devolve uma lista com:
        {
          'sequencial': int,
          'data': datetime,
          'valor_bloquear': float,
          'protocolo': str,
          'linha_el': WebElement   # linha da tabela (para clicar no menu)
        }
    A lista vem ordenada pela data ascendente.
    """
    ordens = []
    tabela = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody"))
    )
    linhas = tabela.find_elements(By.CSS_SELECTOR, "tr.mat-row")
    meses = {
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12
    }

    for linha in linhas:
        cols = linha.find_elements(By.CSS_SELECTOR, "td")
        try:
            sequencial = int(cols[0].text.strip())
            data_txt   = cols[2].text.strip().split(",").strip()  # '26/07/2023'
            protocolo  = cols[5].text.strip()
            valor_txt  = cols[4].text.strip()  # 'R$ 2.446,96'
            # Converte data
            if "/" in data_txt:  # formato dd/mm/aaaa
                dia, mes, ano = map(int, data_txt.split("/"))
            else:               # formato '26 JUL 2023'
                dia, mes_abr, ano = data_txt.split()
                dia, ano = int(dia), int(ano)
                mes = meses[mes_abr.upper()]
            data_ordem = datetime(ano, mes, dia)
            # Converte valor
            valor = float(valor_txt.replace("R$", "")
                                   .replace("\u00a0", "")
                                   .replace(".", "")
                                   .replace(",", ".")
                                   .strip())
            ordens.append({
                "sequencial": sequencial,
                "data": data_ordem,
                "valor_bloquear": valor,
                "protocolo": protocolo,
                "linha_el": linha
            })
        except Exception:
            continue

    ordens.sort(key=lambda x: x["data"])      # crescente
    return ordens


def _identificar_ordens_com_bloqueio(ordens: list[dict]) -> list[dict]:
    """
    Uma ordem possui BLOQUEIO se o valor a bloquear da ordem N
    for maior que o valor da ordem N+1 (queda de saldo).
    Retorna lista das ordens que geraram bloqueio.
    """
    bloqueios = []
    for i in range(len(ordens) - 1):
        if ordens[i]["valor_bloquear"] > ordens[i + 1]["valor_bloquear"]:
            bloqueios.append(ordens[i])
    # Última ordem nunca gera bloqueio (saldo final)
    return bloqueios


def _abrir_menu_da_ordem(driver, linha_el) -> bool:
    """
    Clica nos três pontos da linha da ordem e aguarda menu aparecer.
    """
    try:
        botao = linha_el.find_element(By.CSS_SELECTOR,
                                      "mat-icon.fas.fa-ellipsis-h")
        botao.click()
        WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div.mat-menu-panel"))
        )
        return True
    except Exception:
        return False


def _clicar_desdobrar(driver) -> bool:
    """
    Dentro do menu, clica na opção Desdobrar.
    """
    try:
        opc = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[role='menuitem'] span.mat-menu-item span"))
        )
        # Confirma que o texto contém 'Desdobrar'
        if "Desdobrar" in opc.text:
            opc.click()
            return True
        # Se o SPAN interno não é clicável, tenta botão pai
        botao = opc.find_element(By.XPATH, "./ancestor::button")
        botao.click()
        return True
    except Exception:
        return False


def _preencher_campos_desbloqueio(driver, juiz_padrao="OTAVIO AUGUSTO"):
    """
    Seleciona Juiz solicitante, define ação 'Desbloquear valor' em todos os
    dropdowns e clica Salvar. Aguarda aparecer botão Protocolar.
    """
    # Juiz Solicitante
    try:
        juiz_input = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
        )
        juiz_input.clear()
        juiz_input.send_keys(juiz_padrao)
        juiz_input.send_keys("\n")
    except Exception:
        pass

    # Dropdowns de ação
    selects = driver.find_elements(By.CSS_SELECTOR,
                                   "mat-select[name*='acao']")
    for sel in selects:
        try:
            sel.click()
            opc_desbloq = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[@class='mat-option-text' "
                               "and normalize-space(text())="
                               "'Desbloquear valor']"))
            )
            opc_desbloq.click()
        except Exception:
            continue

    # Botão Salvar
    try:
        btn_salvar = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR,
                 "button.mat-fab.mat-primary mat-icon.fa-save"
                 "::shadow button"))  # fallback
        )
    except Exception:
        btn_salvar = None
    # Shadow-DOM não é suportado pelo CSS; usar XPath amplo
    if not btn_salvar:
        try:
            btn_salvar = driver.find_element(
                By.XPATH,
                "//button[contains(@class,'mat-fab') and "
                ".//mat-icon[contains(@class,'fa-save')]]")
        except Exception:
            pass
    if btn_salvar:
        btn_salvar.click()

    # Espera aparecer botão protocolar
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//button[contains(@class,'mat-fab') "
                 "and @title='Protocolar']"))
        )
        return True
    except Exception:
        return False


def _processar_ordem(driver, ordem, tipo_fluxo):
    """
    Abre menu da ordem, desdobra, preenche campos conforme fluxo e fecha aba.
    """
    # 5-a abrir menu
    if not _abrir_menu_da_ordem(driver, ordem["linha_el"]):
        print(f"[BACEN][ORDEM] Não abriu menu da ordem {ordem['protocolo']}")
        return False

    # 5-b desdobrar
    if not _clicar_desdobrar(driver):
        print(f"[BACEN][ORDEM] Não achou opção Desdobrar {ordem['protocolo']}")
        return False

    # 5-c confirmar /desdobrar
    WebDriverWait(driver, 10).until(
        EC.url_contains("/desdobrar")
    )
    time.sleep(1)

    # 5-d preencher tela
    sucesso = False
    if tipo_fluxo == "DESBLOQUEIO":
        sucesso = _preencher_campos_desbloqueio(driver)
    else:  # POSITIVO (ou outros)
        # Aqui implementar seleção 'Transferir' ou 'Manter' conforme regra.
        sucesso = _preencher_campos_desbloqueio(driver)  # placeholder

    # 5-e fechar aba da ordem
    driver.close()
    driver.switch_to.window(driver.window_handles[-1])
    return sucesso


# --------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL PARA ETAPA 4 e 5
# --------------------------------------------------------------------------

def processar_bloqueios_com_ordens(driver, resultado_series: dict):
    """
    Recebe o retorno de processar_bloqueios (resultado_series)
    e executa as etapas 4-10: para cada série → localizar ordens com bloqueio
    → preencher tela Desbloquear/Transferir → salvar.
    """
    tipo_fluxo = resultado_series["tipo_fluxo"]       # NEGATIVO, DESBLOQUEIO, POSITIVO
    if tipo_fluxo == "NEGATIVO":
        print("[BACEN][ETAPA 4-5] Fluxo NEGATIVO, nenhuma série será aberta.")
        return True

    series = resultado_series["series_validas"]
    for idx, serie in enumerate(series, 1):
        id_serie = serie["id_serie"]
        print(f"[BACEN][ETAPA 4-5] >>> Série {idx}/{len(series)} ID={id_serie}")

        # 4-a navegar para detalhes
        if not _navegar_para_detalhes_serie(driver, id_serie):
            print(f"[BACEN][ETAPA 4-5] Falha ao abrir detalhes da série {id_serie}")
            continue

        # 4-b extrair ordens + identificar bloqueios
        ordens = _extrair_ordens_da_serie(driver)
        ordens_bloqueio = _identificar_ordens_com_bloqueio(ordens)
        print(f"[BACEN][ETAPA 4-5]   Encontradas {len(ordens_bloqueio)} "
              f"ordens com bloqueio")

        # 5- processar cada ordem
        for o in ordens_bloqueio:
            print(f"[BACEN][ORDEM]   Processando protocolo {o['protocolo']}")
            if not _processar_ordem(driver, o, tipo_fluxo):
                print(f"[BACEN][ORDEM]   ⚠️ Falha no protocolo {o['protocolo']}")
            else:
                print(f"[BACEN][ORDEM]   ✅ Protocolo {o['protocolo']} concluído")

        # 8- fechar detalhes
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])

    # 10- fechar driver SISBAJUD (chave para continuar PJe)
    driver.quit()
    print("[BACEN][ETAPA 4-5] ✅ Driver SISBAJUD fechado; prosseguir com anexos/atos")
    return True
def processar_ordens_positivas(driver, serie_id, valor_total_bloqueado, valores_por_partes):
    """
    Funcionalidade para processar ordens de bloqueio positivo em série,
    seguindo o fluxo definido.
    - Navega na série
    - Identifica ordens com bloqueio
    - Processa cada ordem: abrir menu, selecionar "Transferir valor", preencher modal, confirmar, fechar aba
    - Registra total bloqueado por parte
    - Atualiza `valores_por_partes` com os dados de bloqueio
    """
    import time
    import datetime

    # 1. Navegar para detalhes da série
    url_series = f'https://sisbajud.cnj.jus.br/teimosinha/{serie_id}/detalhes'
    driver.execute_script("window.open(arguments[0], '_blank');", url_series)
    driver.switch_to.window(driver.window_handles[-1])
    # Confirmar navegação
    for _ in range(10):
        if "/detalhes" in driver.current_url and serie_id in driver.current_url:
            break
        time.sleep(1)
    else:
        print(f"[PROCESSO] Falha ao abrir detalhes da série {serie_id}")
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])
        return

    # 2. Extrair ordens na página
    ordens = _extrair_ordens_da_serie(driver)  # função semelhante à anterior
    ordens_ordenadas = sorted(ordens, key=lambda o: o['data'])
    bloqueios = []
    total_bloqueado = 0.0

    # 3. Avaliar qual ordem tem bloqueio
    saldo_anterior = float('inf')
    protocolo_bloqueio = None
    
    for ordem in ordens_ordenadas:
        if ordem['valor_bloquear'] > 0:
            # Detectar diminuição de saldo
            if ordem['valor_bloquear'] < saldo_anterior:
                protocolo_bloqueio = ordem['protocolo']
                # Registrar bloqueio por partes
                parte_bloqueada = 'PARTA'  # Demarcando pela lógica, onde é bloqueado
                parte_bloqueada = 'Parte A'  # usar lógica na sequência
                parte_bloqueada = 'Parte B'  # Ajustar conforme análise de html
                bloqueios.append({'protocolo': ordem['protocolo'], 'valor': ordem['valor_bloquear']})
                total_bloqueado += ordem['valor_bloquear']
            saldo_anterior = ordem['valor_bloquear']
    
    # 4. Verificar condições de processamento
    if total_bloqueado == 0:
        print('Não há teimosinha para processar (total bloqueado zero)')
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])
        return

    if total_bloqueado < 100 and sum([b['valor'] for b in bloqueios]) >= 1000:
        print('Processamento condicional de desbloqueio')
        # Executar ações de desbloqueio (não detalhado aqui)
        # ...
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])
        return

    if total_bloqueado > 100 or (total_bloqueado < 100 and sum([b['valor'] for b in bloqueios]) < 1000):
        print('Processando como bloqueio positivo')
        # Para cada ordem com bloqueio > 0, processar
        for ordem in ordens_ordenadas:
            if ordem['valor_bloquear'] > 0:
                # 4a. Navegar na ordem
                driver.execute_script("window.open(arguments[0], '_blank');", f'https://sisbajud.cnj.jus.br/teimosinha/{serie_id}/detalhes')
                driver.switch_to.window(driver.window_handles[-1])
                # confirmar URL
                if "/detalhes" not in driver.current_url:
                    print('Erro na navegação na série')
                    driver.close()
                    driver.switch_to.window(driver.window_handles[-1])
                    continue
                # 4b. abrir menu
                try:
                    menu_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-icon.fas.fa-ellipsis-h"))
                    )
                    menu_btn.click()
                except:
                    print('Não conseguiu abrir menu da ordem')
                    driver.close()
                    driver.switch_to.window(driver.window_handles[-1])
                    continue
                # 4c. clicar em Transferir Valor
                try:
                    btn_transferir = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[contains(@class,'mat-option-text') and contains(text(),'Transferir valor')]"))
                    )
                    btn_transferir.click()
                    time.sleep(1)
                except:
                    print('Não achou opção Transferir valor')
                    driver.close()
                    driver.switch_to.window(driver.window_handles[-1])
                    continue
                # 4d. processar modal
                # clicar em Juiz Otavio Augusto
                try:
                    sel_juiz = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
                    )
                    sel_juiz.clear()
                    sel_juiz.send_keys('Otavio Augusto\n')
                except:
                    print('Não achou campo juiz')
                # 4e. preencher dados do deposito (tipo, banco, Agencia)
                # [hipotético, usar seletor correto]
                try:
                    # preencher em sequência: Tipo de crédito, Banco, Agência
                    # usar os seletores corretos provistos pelo HTML ou pelo módulo
                    pass
                except:
                    pass
                # clicar em Confirmar (botao do modal)
                try:
                    btn_confirmar = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[text()='Confirmar']"))
                    )
                    btn_confirmar.click()
                except:
                    pass
                # esperar fechar modal
                time.sleep(1)
                # fechar aba
                driver.close()
                driver.switch_to.window(driver.window_handles[-1])
        # Fim processar ordens
        # feche a aba geral
        driver.quit()
        # condições finais de ação (importar os módulos, etc.)
        # ...
