import logging
logger = logging.getLogger(__name__)

"""
SISB.processamento_ordens_processamento_principal - Parte principal do processamento de ordens SISBAJUD.

Parte da refatoração do SISB/processamento.py para melhor granularidade IA.
Contém a lógica principal de navegação e seleção de juiz/ação.
"""

import time as time_module
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from Fix.core import safe_click

def _processar_ordem_principal(driver, ordem, tipo_fluxo, log=True, valor_parcial=None, apenas_extrair=False):
    """
    Parte principal do processamento de ordem - navegação e seleções básicas.

    Args:
        driver: WebDriver SISBAJUD
        ordem: Dict com dados da ordem
        tipo_fluxo: 'POSITIVO' ou 'DESBLOQUEIO'
        log: Se deve fazer log
        valor_parcial: Valor para transferência parcial
        apenas_extrair: Se apenas extrair dados

    Returns:
        tuple: (sucesso, juiz_selecionado, acao_selecionada, tipo_fluxo)
    """
    _start_geral = time_module.time()

    try:
        if log:
            print(f"[SISBAJUD] [ORDEM] Processando ordem {ordem['sequencial']} (tipo: {tipo_fluxo}) +0.0s")
            print(f"[SISBAJUD] [ORDEM] 📍 URL atual: {driver.current_url}")

        # ===== VERIFICAR SE ESTÁ NA PÁGINA CORRETA =====
        url_atual = driver.current_url.lower()

        if "/detalhes" not in url_atual and ("/minuta" in url_atual or url_atual.endswith("/teimosinha")):
            if log:
                print(f"[SISBAJUD] [ORDEM] ⚠️ ALERTA: Página incorreta detectada!")
            return False, False, False, tipo_fluxo

        # ===== LOCALIZAR LINHA DA ORDEM =====
        sequencial = ordem['sequencial']
        xpath_linha = f"//tr[.//td[@class='mat-cell cdk-column-index mat-column-index' and text()='{sequencial}']]"

        try:
            linha_el = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, xpath_linha))
            )
            if log:
                print(f"[SISBAJUD] [ORDEM] Linha localizada via XPath direto +{time_module.time()-_start_geral:.1f}s")
        except:
            if log:
                print(f"[SISBAJUD] [ORDEM] Fallback: buscando linha por CSS selector...")
            try:
                time_module.sleep(0.5)
                tabela = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody"))
                )
                linhas = tabela.find_elements(By.CSS_SELECTOR, "tr.mat-row")
                linha_el = None

                if log:
                    print(f"[SISBAJUD] [ORDEM] Buscando ordem {sequencial} entre {len(linhas)} linhas...")

                for linha in linhas:
                    try:
                        cel_seq = linha.find_element(By.CSS_SELECTOR, "td.mat-cell.cdk-column-index")
                        seq_text = cel_seq.text.strip()
                        if seq_text == str(sequencial):
                            linha_el = linha
                            if log:
                                print(f"[SISBAJUD] [ORDEM] ✅ Linha encontrada: ordem {sequencial}")
                            break
                    except:
                        continue

                if not linha_el:
                    if log:
                        print(f"[SISBAJUD] ❌ Linha não encontrada para ordem {sequencial}")
                    return False, False, False, tipo_fluxo
            except Exception as e_fallback:
                if log:
                    print(f"[SISBAJUD] ❌ Erro no fallback: {e_fallback}")
                return False, False, False, tipo_fluxo

        # ===== CLIQUE NO BOTÃO MENU =====
        try:
            btn_menu = linha_el.find_element(By.CSS_SELECTOR, "button.mat-menu-trigger")
            safe_click(driver, btn_menu, 'click')
            time_module.sleep(0.2)
            if log:
                print(f"[SISBAJUD] [ORDEM] Menu clicado +{time_module.time()-_start_geral:.1f}s")
        except Exception as e:
            if log:
                print(f"[SISBAJUD] ❌ Erro ao clicar em menu: {e}")
            return False, False, False, tipo_fluxo

        # ===== CLICAR "DETALHAR" =====
        try:
            opcoes = WebDriverWait(driver, 2).until(
                EC.presence_of_all_elements_located((By.XPATH, "//button[@role='menuitem']"))
            )

            detalhar_clicado = False
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if "detalh" in texto or "desdobr" in texto:
                        safe_click(driver, opcao, 'click')
                        detalhar_clicado = True
                        if log:
                            print(f"[SISBAJUD] [ORDEM] 'Detalhar' clicado +{time_module.time()-_start_geral:.1f}s")
                        break
                except:
                    continue

            if not detalhar_clicado:
                if log:
                    print(f"[SISBAJUD] ❌ Opção 'Detalhar' não encontrada")
                return False, False, False, tipo_fluxo
        except:
            if log:
                print(f"[SISBAJUD] ❌ Menu não carregou corretamente")
            return False, False, False, tipo_fluxo

        # ===== AGUARDAR /DESDOBRAR =====
        for tentativa in range(6):
            if "/desdobrar" in driver.current_url:
                if log:
                    print(f"[SISBAJUD] [ORDEM] Página /desdobrar carregada +{time_module.time()-_start_geral:.1f}s")
                break
            time_module.sleep(0.5)
        else:
            if log:
                print(f"[SISBAJUD] ❌ Página /desdobrar não carregou")
            return False, False, False, tipo_fluxo

        # ===== MODO APENAS EXTRAÇÃO =====
        if apenas_extrair:
            if log:
                print(f"[SISBAJUD] [ORDEM] Modo apenas extração - coletando dados...")

            try:
                from .helpers import extrair_dados_bloqueios_processados
                protocolo_ordem = ordem.get('protocolo', 'N/A')
                dados_ordem = extrair_dados_bloqueios_processados(driver, log, protocolo_ordem=protocolo_ordem)

                if '_relatorio' in ordem and dados_ordem:
                    ordem['_relatorio']['status'] = 'processado'
                    ordem['_relatorio']['discriminacao'] = dados_ordem

                if log:
                    print(f"[SISBAJUD] [ORDEM] ✅ Dados extraídos e registrados no relatório")

                driver.back()
                time_module.sleep(0.5)
                return True, False, False, tipo_fluxo

            except Exception as e_ext:
                if log:
                    print(f"[SISBAJUD] [ORDEM] ⚠️ Erro ao extrair dados: {e_ext}")
                try:
                    driver.back()
                    time_module.sleep(0.5)
                except:
                    pass
                return False, False, False, tipo_fluxo

        # ===== SELEÇÃO DE JUIZ =====
        time_module.sleep(0.8)
        juiz_selecionado = False

        try:
            if log:
                print(f"[SISBAJUD] [ORDEM] Selecionando juiz...")

            juiz_input = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Juiz']"))
            )

            if log:
                print(f"[SISBAJUD] [ORDEM]    Campo juiz encontrado")

            juiz_input.click()
            time_module.sleep(0.3)
            juiz_input.clear()
            time_module.sleep(0.3)
            juiz_input.send_keys("OTAVIO AUGUSTO")
            time_module.sleep(1.2)

            if log:
                print(f"[SISBAJUD] [ORDEM]    Digitado 'OTAVIO AUGUSTO', aguardando autocomplete...")

            try:
                opcoes = WebDriverWait(driver, 3).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option[role='option']"))
                )
                if log:
                    print(f"[SISBAJUD] [ORDEM]    Encontradas {len(opcoes)} opções de juiz")
            except:
                if log:
                    print(f"[SISBAJUD] [ORDEM]    Autocomplete demorou, aguardando mais 1s...")
                time_module.sleep(1.0)
                try:
                    opcoes = driver.find_elements(By.CSS_SELECTOR, "mat-option[role='option']")
                    if log:
                        print(f"[SISBAJUD] [ORDEM]    Encontradas {len(opcoes)} opções (retry)")
                except:
                    opcoes = []

            for idx, opcao in enumerate(opcoes):
                try:
                    texto = opcao.text.upper()
                    if "OTAVIO" in texto:
                        if log:
                            print(f"[SISBAJUD] [ORDEM]    Clicando em opção {idx+1}: {texto[:50]}")
                        safe_click(driver, opcao, 'click')
                        juiz_selecionado = True
                        time_module.sleep(0.5)
                        break
                except:
                    continue

            if not juiz_selecionado:
                try:
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                    time_module.sleep(0.3)
                except:
                    pass

            if log:
                if juiz_selecionado:
                    print(f"[SISBAJUD] [ORDEM]    ✅ Juiz selecionado")
                else:
                    print(f"[SISBAJUD] [ORDEM]    ⚠️ Juiz NÃO selecionado")

        except Exception as e:
            if log:
                print(f"[SISBAJUD] [ORDEM] ❌ Erro ao selecionar juiz: {e}")
                import traceback
                traceback.print_exc()

        # ===== SELEÇÃO DE AÇÃO =====
        if log:
            print(f"[SISBAJUD] [ORDEM] 🎯 Selecionando ação (tipo: {tipo_fluxo})...")

        acao_selecionada = False
        try:
            from .helpers import _aplicar_acao_por_fluxo
            resultado_acao = _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=log, valor_parcial=valor_parcial)
            acao_selecionada = resultado_acao

            if acao_selecionada:
                if log:
                    print(f"[SISBAJUD] [ORDEM]    ✅ Ação selecionada com sucesso")
            else:
                if log:
                    print(f"[SISBAJUD] [ORDEM]    ⚠️ Ação NÃO foi selecionada")

        except Exception as e:
            if log:
                print(f"[SISBAJUD] [ORDEM] ❌ Erro ao selecionar ação: {e}")
                import traceback
                traceback.print_exc()

        return True, juiz_selecionado, acao_selecionada, tipo_fluxo

    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro geral na ordem {ordem['sequencial']}: {e}")
        return False, False, False, tipo_fluxo