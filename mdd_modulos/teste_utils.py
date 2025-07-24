"""
Módulo responsável por funções de teste e debug.

Responsabilidades:
- Funções de teste isoladas
- Demonstrações de regras e funcionalidades
- Validações e exemplos

Funções extraídas do m1.py:
- fluxo_teste()
- testar_regra_argos_planilha()
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def fluxo_teste(driver):
    """
    Fluxo de teste isolado que começa pelo cabeçalho do documento ativo.
    
    Args:
        driver: Instância do WebDriver
    """
    try:
        # Espera o cabeçalho do documento ativo
        cabecalho = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-card-title.mat-card-title'))
        )
        texto_cabecalho = cabecalho.text.lower()
        print(f"[INFO] Cabeçalho do documento: {texto_cabecalho}")

        if "pesquisa patrimonial" in texto_cabecalho or "argos" in texto_cabecalho:
            print("[FLUXO] Iniciando fluxo Argos")
            # Importação local para evitar dependência circular
            from . import argos_core
            argos_core.processar_argos(driver)
        elif "oficial de justiça" in texto_cabecalho or "certidão de oficial" in texto_cabecalho:
            print("[FLUXO] Iniciando fluxo Outros")
            # Importação local para evitar dependência circular
            from . import outros_core
            outros_core.fluxo_mandados_outros(driver)
        else:
            print(f"[FLUXO] Tipo de documento não identificado: {texto_cabecalho}")

    except Exception as e:
        print(f"[ERRO] Falha ao identificar o cabeçalho do documento: {e}")

def testar_regra_argos_planilha():
    """
    Função de teste que demonstra como a nova regra funciona.
    
    NOVA REGRA IMPLEMENTADA:
    1. Procura pela primeira "Planilha de Atualização de Cálculos" na timeline
    2. Busca por decisões/despachos que vêm ANTES dessa planilha
    3. Prioriza o primeiro documento relevante encontrado antes da planilha
    4. Se não encontrar planilha, usa lógica fallback (primeiro despacho/decisão)
    
    BENEFÍCIOS:
    - Melhora a precisão na seleção de documentos relevantes
    - Evita processar documentos que podem ser posteriores aos cálculos
    - Mantém compatibilidade com casos onde não há planilha
    """
    exemplo_timeline = [
        "Item 0: Petição inicial",
        "Item 1: Despacho ordenando perícia",  # <- Este seria selecionado (primeiro antes da planilha)
        "Item 2: Decisão deferindo pedido",    # <- Este seria ignorado (após item  1)
        "Item 3: Planilha de Atualização de Cálculos",  # <- Referência para busca
        "Item 4: Despacho posterior",          # <- Este seria ignorado (após planilha)
        "Item 5: Decisão final"                # <- Este seria ignorado (após planilha)
    ]
    
    print("="*60)
    print("TESTE DA NOVA REGRA ARGOS - BUSCA ANTES DA PLANILHA")
    print("="*60)
    print("Timeline de exemplo:")
    for item in exemplo_timeline:
        print(f"  {item}")
    
    print("\nLógica da nova regra:")
    print("1. Encontra 'Planilha de Atualização de Cálculos' no item 3")
    print("2. Busca decisões/despachos nos itens 0, 1, 2 (antes da planilha)")
    print("3. Seleciona 'Despacho ordenando perícia' (item 1) - primeiro relevante")
    print("4. Ignora itens 4 e 5 por estarem após a planilha")
    
    print("\nFallback (se não houvesse planilha):")
    print("- Selecionaria 'Despacho ordenando perícia' (item 1) - primeiro relevante geral")
    
    print("\nVantagens da nova regra:")
    print("- Foca em documentos anteriores aos cálculos")
    print("- Evita documentos potencialmente desatualizados")
    print("- Mantém compatibilidade com timelines sem planilha")
    print("="*60)
