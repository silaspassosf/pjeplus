#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do filtrofases
URL: https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos
"""

from driver_config import criar_driver, login_func
from selenium.webdriver.common.by import By
import time
import sys
import os

# Importa a função filtrofases do arquivo 0c.PY
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=['análise']):
    print(f'Filtrando fase processual: {", ".join(fases_alvo).title()}...')
    try:
        fase_element = None
        try:
            fase_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Fase processual')]")
        except Exception:
            try:
                seletor_fase = 'span.ng-tns-c82-22.ng-star-inserted'
                for elem in driver.find_elements(By.CSS_SELECTOR, seletor_fase):
                    if 'Fase processual' in elem.text:
                        fase_element = elem
                        break
            except Exception:
                print('[ERRO] Não encontrou o seletor de fase processual.')
                return False
        if not fase_element:
            print('[ERRO] Não encontrou o seletor de fase processual.')
            return False
        driver.execute_script("arguments[0].click();", fase_element)
        time.sleep(1)
        painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
        painel = None
        for _ in range(10):
            try:
                painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                if painel.is_displayed():
                    break
            except Exception:
                time.sleep(0.3)
        if not painel or not painel.is_displayed():
            print('[ERRO] Painel de opções não apareceu.')
            return False
        fases_clicadas = set()
        opcoes = painel.find_elements(By.XPATH, ".//mat-option")
        for fase in fases_alvo:
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if fase in texto and opcao.is_displayed():
                        driver.execute_script("arguments[0].click();", opcao)
                        fases_clicadas.add(fase)
                        print(f'[OK] Fase "{fase}" selecionada.')
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
        if len(fases_clicadas) == 0:
            print(f'[ERRO] Não encontrou opções {fases_alvo} no painel.')
            return False
        
        try:
            botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
            driver.execute_script('arguments[0].click();', botao_filtrar)
            print('[OK] Fases selecionadas e filtro aplicado (botão filtrar).')
            time.sleep(1)
        except Exception as e:
            print(f'[ERRO] Não conseguiu clicar no botão de filtrar: {e}')
        
        # Se tarefas_alvo foi informado, aplicar filtro de tarefas também
        if tarefas_alvo:
            print(f'Filtrando tarefa do processo: {", ".join(tarefas_alvo).title()}...')
            tarefa_element = None
            try:
                tarefa_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Tarefa do processo')]")
            except Exception:
                try:
                    seletor_tarefa = 'span.ng-tns-c82-22.ng-star-inserted'
                    for elem in driver.find_elements(By.CSS_SELECTOR, seletor_tarefa):
                        if 'Tarefa do processo' in elem.text:
                            tarefa_element = elem
                            break
                except Exception:
                    print('[ERRO] Não encontrou o seletor de tarefa do processo.')
                    return False
            
            if not tarefa_element:
                print('[ERRO] Não encontrou o seletor de tarefa do processo.')
                return False
            
            driver.execute_script("arguments[0].click();", tarefa_element)
            time.sleep(1)
            
            painel = None
            for _ in range(10):
                try:
                    painel = driver.find_element(By.CSS_SELECTOR, painel_selector)
                    if painel.is_displayed():
                        break
                except Exception:
                    time.sleep(0.3)
            
            if not painel or not painel.is_displayed():
                print('[ERRO] Painel de opções de tarefa não apareceu.')
                return False
            
            tarefas_clicadas = set()
            opcoes = painel.find_elements(By.XPATH, ".//mat-option")
            for tarefa in tarefas_alvo:
                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        if tarefa in texto and opcao.is_displayed():
                            driver.execute_script("arguments[0].click();", opcao)
                            tarefas_clicadas.add(tarefa)
                            print(f'[OK] Tarefa "{tarefa}" selecionada.')
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue
            
            if len(tarefas_clicadas) == 0:
                print(f'[ERRO] Não encontrou opções {tarefas_alvo} no painel de tarefas.')
                return False
            
            try:
                botao_filtrar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-filter')
                driver.execute_script('arguments[0].click();', botao_filtrar)
                print('[OK] Tarefas selecionadas e filtro aplicado (botão filtrar).')
                time.sleep(1)
            except Exception as e:
                print(f'[ERRO] Não conseguiu clicar no botão de filtrar para tarefas: {e}')
                
    except Exception as e:
        print(f'[ERRO] Erro no filtro de fase: {e}')
        return False
    return True

def teste_filtrofases():
    """Testa a função filtrofases na tela de lista de processos."""
    driver = None
    try:
        print("[TESTE] Iniciando teste do filtrofases...")
        
        # 1. Criar driver e fazer login
        print("[TESTE] Criando driver...")
        driver = criar_driver()
        
        print("[TESTE] Fazendo login...")
        login_success = login_func(driver)
        if not login_success:
            print("[TESTE][ERRO] Falha no login!")
            return False
        
        # 2. Navegar para a lista de processos
        url_lista = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"
        print(f"[TESTE] Navegando para a lista: {url_lista}")
        driver.get(url_lista)
        
        # Aguarda carregamento da página
        time.sleep(5)
        print(f"[TESTE] URL atual: {driver.current_url}")
        
        # 3. Executar filtrofases
        print("[TESTE] Executando filtrofases...")
        resultado = filtrofases(driver)
        
        if resultado:
            print("[TESTE] ✓ filtrofases executado com sucesso!")
            print("[TESTE] Filtros aplicados: liquidação, execução e análise")
        else:
            print("[TESTE] ✗ Falha na execução do filtrofases")
            return False
        
        # 4. Aguardar para verificar resultado
        print("[TESTE] Teste concluído. Pressione Enter para fechar o navegador...")
        input()
        
        return True
        
    except Exception as e:
        print(f"[TESTE][ERRO] Exceção durante o teste: {e}")
        return False
    finally:
        if driver:
            try:
                print("[TESTE] Fechando navegador...")
                driver.quit()
            except Exception as e:
                print(f"[TESTE][WARN] Erro ao fechar driver: {e}")

if __name__ == "__main__":
    sucesso = teste_filtrofases()
    if sucesso:
        print("[TESTE] Teste finalizado com sucesso!")
    else:
        print("[TESTE] Teste finalizado com erro!")
