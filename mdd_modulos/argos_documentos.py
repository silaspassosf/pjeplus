"""
Módulo responsável pela busca e análise de documentos no fluxo Argos.

Responsabilidades:
- Busca de documentos relevantes na timeline
- Busca de documentos sequenciais
- Lógica de busca antes da planilha
- Extração de texto de documentos

Funções extraídas do m1.py:
- buscar_documento_argos()
- buscar_documentos_sequenciais()
"""

import re
from selenium.webdriver.common.by import By
from Fix import wait_for_visible, wait, safe_click, sleep, extrair_documento

def buscar_documentos_sequenciais(driver, log=True):
    """
    Busca documentos sequenciais na timeline do processo.
    
    Args:
        driver: Instância do WebDriver
        log (bool): Se True, imprime logs de debug
    
    Returns:
        list: Lista de elementos de documentos encontrados
    """
    try:
        documentos_alvo = [
            "Certidão de devolução",
            "Certidão de expedição", 
            "Planilha",
            "Intimação",
            "Decisão"
        ]
        
        if log:
            print(f'[DOCS_SEQUENCIAIS] Buscando documentos alvos: {documentos_alvo}')
            
        resultados = []
        
        # Espera documentos carregarem na timeline
        selector = ".tl-data, li.tl-item-container"
        sleep(2000)  # Pausa para garantir carregamento da página
        
        # Tenta primeiro usar wait para garantir que algum elemento existe
        primeiro_elemento = wait(driver, selector, timeout=10)
        
        if not primeiro_elemento:
            if log:
                print('[DOCS_SEQUENCIAIS][ERRO] Nenhum documento encontrado na timeline')
            return []
            
        elementos = driver.find_elements(By.CSS_SELECTOR, selector)
        
        if log:
            print(f'[DOCS_SEQUENCIAIS] Total de elementos encontrados na timeline: {len(elementos)}')
        
        indice_doc_atual = 0
        for elemento in elementos:
            if indice_doc_atual >= len(documentos_alvo):
                break
                
            texto_item = elemento.text.strip().lower()
            documento_atual = documentos_alvo[indice_doc_atual]
            
            if documento_atual.lower() in texto_item:
                resultados.append(elemento)
                if log:
                    print(f'[DOCS_SEQUENCIAIS] Encontrado documento: "{documento_atual}" - {texto_item[:50]}...')
                indice_doc_atual += 1
                
        if log:
            print(f'[DOCS_SEQUENCIAIS] Total de documentos alvos encontrados: {len(resultados)}')
            
        return resultados
    except Exception as e:
        if log:
            print(f'[DOCS_SEQUENCIAIS][ERRO] Falha ao buscar documentos: {str(e)}')
        return []

def buscar_documento_argos(driver, log=True):
    """
    Busca documentos relevantes na timeline do Argos, priorizando decisões/despachos anteriores à Planilha de Atualização de Cálculos.
    
    Args:
        driver: Instância do WebDriver
        log (bool): Se True, imprime logs de debug
    
    Returns:
        tuple: (texto_documento, tipo_documento) ou (None, None) se não encontrado
    """
    try:
        print('[ARGOS][DOC] Iniciando busca de documento relevante...')
        
        # Aguarda a timeline carregar (aguarda pelo menos um item na timeline)
        timeline_selector = 'li.tl-item-container'
        print('[ARGOS][DOC] Aguardando carregamento da timeline...')
        
        # Usando as novas funções do Fix.py
        timeline_item = wait(driver, timeline_selector, timeout=15)
        
        if not timeline_item:
            print('[ARGOS][DOC][ERRO] Timeline não carregou após 15 segundos de espera')
            return None, None
            
        print('[ARGOS][DOC] Timeline carregada com sucesso')
        
        # Garantimos um tempo extra para carregar completamente a timeline
        sleep(1000)
        
        # Buscamos todos os itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, timeline_selector)
        print(f'[ARGOS][DOC] Encontrados {len(itens)} itens na timeline')
        
        # NOVA REGRA: Busca por decisões/despachos anteriores à Planilha de Atualização de Cálculos
        planilha_index = _encontrar_planilha_timeline(itens, log)
        
        if planilha_index is not None:
            # Busca documentos antes da planilha
            resultado = _buscar_documentos_antes_planilha(driver, itens, planilha_index, log)
            if resultado:
                return resultado
        
        # FALLBACK: Se não encontrou planilha ou documentos antes dela, usa a lógica original
        if log:
            print('[ARGOS][DEBUG] Usando lógica fallback: procurando primeiro despacho/decisão na timeline...')
        
        resultado = _buscar_primeiro_documento_relevante(driver, itens, log)
        if resultado:
            return resultado
        
        if log:
            print('[ARGOS] Nenhum documento relevante encontrado após varrer os itens.')
        return None, None
        
    except Exception as e:
        if log:
            print(f'[ARGOS][ERRO] Falha ao buscar documento: {e}')
            print('[ARGOS][INFO] Tentando fallback...')
        
        # Fallback final
        return _fallback_buscar_documento(driver, log)

def _encontrar_planilha_timeline(itens, log):
    """
    Encontra a primeira planilha de atualização na timeline.
    
    Args:
        itens: Lista de elementos da timeline
        log (bool): Se True, imprime logs de debug
    
    Returns:
        int: Índice da planilha ou None se não encontrada
    """
    planilha_index = None
    
    for idx, item in enumerate(itens):
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento')
            doc_text = link.text.lower()
            if 'planilha de atualização' in doc_text or 'planilha de atuali' in doc_text:
                planilha_index = idx
                if log:
                    print(f'[ARGOS][DEBUG] Planilha de Atualização encontrada no item {idx}: {doc_text}')
                break
        except Exception:
            continue
    
    return planilha_index

def _buscar_documentos_antes_planilha(driver, itens, planilha_index, log):
    """
    Busca documentos relevantes antes da planilha.
    
    Args:
        driver: Instância do WebDriver
        itens: Lista de elementos da timeline
        planilha_index (int): Índice da planilha
        log (bool): Se True, imprime logs de debug
    
    Returns:
        tuple: (texto_documento, tipo_documento) ou None se não encontrado
    """
    documentos_antes_planilha = []
    
    if log:
        print(f'[ARGOS][DEBUG] Procurando decisões/despachos antes da planilha (itens 0 a {planilha_index-1})...')
    
    for idx in range(planilha_index):
        try:
            item = itens[idx]
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            doc_text = link.text.lower()
            
            # Verifica se é despacho ou decisão
            if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                documentos_antes_planilha.append((idx, item, link, doc_text))
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: documento relevante encontrado antes da planilha: {doc_text}')
        except Exception:
            continue
    
    # Se encontrou documentos antes da planilha, processa o primeiro
    if documentos_antes_planilha:
        idx, item, link, doc_text = documentos_antes_planilha[0]
        if log:
            print(f'[ARGOS][DEBUG] Processando primeiro documento antes da planilha: item {idx}')
        
        # Abre o documento
        if _abrir_documento(driver, link, doc_text, log):
            texto, _ = extrair_documento(driver)
            
            if log:
                print(f'[ARGOS][DEBUG] TEXTO EXTRAÍDO DO DOCUMENTO (antes da planilha):\n---\n{texto}\n---')
            
            # Determina o tipo do documento
            if 'decisão' in doc_text or 'sentença' in doc_text:
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: documento é decisão/sentença anterior à planilha.')
                return texto, 'decisao'
            else:
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: documento é despacho anterior à planilha.')
                return texto, 'despacho'
    
    return None

def _buscar_primeiro_documento_relevante(driver, itens, log):
    """
    Busca o primeiro documento relevante na timeline (fallback).
    
    Args:
        driver: Instância do WebDriver
        itens: Lista de elementos da timeline
        log (bool): Se True, imprime logs de debug
    
    Returns:
        tuple: (texto_documento, tipo_documento) ou None se não encontrado
    """
    for idx, item in enumerate(itens):
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            doc_text = link.text.lower()
            if log:
                print(f'[ARGOS][DEBUG] Item {idx}: texto do link = {doc_text}')
            
            # Verifica se é despacho ou decisão
            if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: documento relevante encontrado (fallback), clicando para ativar.')
                
                # Abre o documento
                if _abrir_documento(driver, link, doc_text, log):
                    texto, _ = extrair_documento(driver)
                    if log:
                        print(f'[ARGOS][DEBUG] TEXTO EXTRAÍDO DO DOCUMENTO (fallback):\n---\n{texto}\n---')
                    
                    if 'decisão' in doc_text or 'sentença' in doc_text:
                        if log:
                            print(f'[ARGOS][DEBUG] Item {idx}: documento é decisão/sentença (fallback).')
                        return texto, 'decisao'
                    else:
                        if log:
                            print(f'[ARGOS][DEBUG] Item {idx}: documento é despacho (fallback).')
                        return texto, 'despacho'
            else:
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: não é despacho/decisão/sentença/conclusão.')
        except Exception as e:
            if log:
                print(f'[ARGOS][DEBUG] Item {idx}: erro ao processar item: {e}')
            continue
    
    return None

def _abrir_documento(driver, link, doc_text, log):
    """
    Abre um documento na timeline.
    
    Args:
        driver: Instância do WebDriver
        link: Elemento do link do documento
        doc_text (str): Texto do documento
        log (bool): Se True, imprime logs de debug
    
    Returns:
        bool: True se documento foi aberto com sucesso
    """
    print(f'[ARGOS][DOC] Tentando abrir documento: {doc_text}')
    
    # Primeiro rolamos para o elemento para garantir visibilidade
    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', link)
    sleep(500)  # Breve pausa após scroll
    
    # Tentamos o clique seguro
    click_resultado = safe_click(driver, link, log=True)
    
    if not click_resultado:
        print(f'[ARGOS][DOC][ERRO] Falha ao clicar no documento usando safe_click. Tentando método alternativo.')
        try:
            driver.execute_script('arguments[0].click();', link)
            print(f'[ARGOS][DOC] Clique via JavaScript executado com sucesso')
        except Exception as e:
            print(f'[ARGOS][DOC][ERRO] Falha no clique alternativo: {e}')
            return False
    
    sleep(1500)  # Esperamos mais tempo para carregar o documento
    print(f'[ARGOS][DOC] Extraindo texto do documento...')
    return True

def _fallback_buscar_documento(driver, log):
    """
    Fallback final para buscar documento.
    
    Args:
        driver: Instância do WebDriver
        log (bool): Se True, imprime logs de debug
    
    Returns:
        tuple: (texto_documento, tipo_documento) ou (None, None)
    """
    try:
        elementos = driver.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
        for elem in elementos:
            if elem.is_displayed() and not elem.get_attribute('target'):
                if log:
                    print('[ARGOS][DEBUG] Fallback: clicando em documento visível.')
                safe_click(driver, elem)
                sleep(1000)
                texto, _ = extrair_documento(driver)
                if texto:
                    return texto, 'fallback'
    except Exception as e_fb:
        if log:
            print(f'[ARGOS][ERRO] Fallback também falhou: {e_fb}')
    
    return None, None
