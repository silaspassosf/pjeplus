"""
Módulo responsável pela análise de documentos no fluxo Outros.

Responsabilidades:
- Verificação de autoria de documentos
- Busca do último mandado na timeline
- Análise de padrões em documentos
- Lógica de mandados positivos/negativos

Funções extraídas do m1.py:
- verificar_autor_documento()
- ultimo_mdd()
"""

import re
import unicodedata
from selenium.webdriver.common.by import By
from Fix import wait_for_visible, wait, validar_conexao_driver

def verificar_autor_documento(documento, driver):
    """
    Função para verificar quem assinou/é responsável por um documento.
    Extrai informações de autor/responsável do texto do documento.
    
    Args:
        documento: Texto do documento ou elemento
        driver: Instância do WebDriver
    
    Returns:
        str: Nome do autor ou None se não encontrado
    """
    try:
        if not documento:
            print("[MANDADOS][OUTROS][LOG] Documento vazio, não é possível verificar autor")
            return None
            
        # Converte para string se necessário
        texto = str(documento).lower()
        
        # Padrões de assinatura/responsabilidade para buscar
        padroes_autor = [
            r'assinado por\s*[:\-]?\s*([^,\n\.]+)',
            r'assinatura digital\s*[:\-]?\s*de\s*([^,\n\.]+)',
            r'responsável\s*[:\-]?\s*([^,\n\.]+)',
            r'elaborado por\s*[:\-]?\s*([^,\n\.]+)',
            r'autor\s*[:\-]?\s*([^,\n\.]+)',
            r'oficial de justiça\s*[:\-]?\s*([^,\n\.]+)',
        ]
        
        # Buscar padrões no texto
        for padrao in padroes_autor:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                nome_autor = match.group(1).strip()
                # Limpar caracteres extras
                nome_autor = re.sub(r'[^\w\s]', ' ', nome_autor).strip()
                # Capitalizar nome
                nome_autor = nome_autor.title()
                print(f"[MANDADOS][OUTROS][LOG] Autor identificado: {nome_autor}")
                return nome_autor
                
        # Busca específica por "silas passos" no texto
        if 'silas passos' in texto:
            print("[MANDADOS][OUTROS][LOG] Referência a 'Silas Passos' encontrada diretamente no texto")
            return 'Silas Passos'
            
        print("[MANDADOS][OUTROS][LOG] Nenhum autor identificado no documento")
        return None
        
    except Exception as e:
        print(f"[MANDADOS][OUTROS][ERRO] Falha ao verificar autor do documento: {e}")
        return None

def ultimo_mdd(driver, log=True):
    """
    Busca o último mandado na timeline (item com texto começando por 'Mandado' e ícone de gavel) e retorna (nome_autor, elemento_mandado).
    Versão robusta com verificações de conectividade.
    
    Args:
        driver: Instância do WebDriver
        log (bool): Se True, imprime logs de debug
    
    Returns:
        tuple: (nome_autor, elemento_mandado) ou (None, None) se não encontrado
    """
    try:
        # Verificação inicial de conexão 
        if not validar_conexao_driver(driver, contexto="MDD_INICIO"):
            if log:
                print('[MDD][ERRO_FATAL] Driver em estado inválido ao buscar mandado')
            return None, None
            
        # Usando wait_for_visible ao invés de find_elements direto para maior robustez
        timeline = wait_for_visible(driver, 'ul.timeline-container', timeout=5)
        if not timeline:
            if log:
                print('[MDD][ERRO] Timeline não encontrada, tentando método direto')
            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        else:
            itens = timeline.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        
        if not itens:
            if log:
                print('[MDD][ALERTA] Nenhum item encontrado na timeline')
            return None, None
            
        for idx, item in enumerate(itens):
            try:
                # Verificação periódica de conexão durante loop
                if idx % 10 == 0 and idx > 0:  # Verificar a cada 10 itens para não impactar performance
                    if not validar_conexao_driver(driver, contexto=f"MDD_LOOP_{idx}"):
                        if log:
                            print(f'[MDD][ERRO_FATAL] Driver em estado inválido durante loop (item {idx})')
                        return None, None
                        
                # Usa wait com timeout curto para não prejudicar performance
                try:
                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                except Exception:
                    continue
                    
                doc_text = link.text.strip().lower()
                if doc_text.startswith('mandado'):
                    # Procura ícone de gavel (fa-gavel)
                    icones = item.find_elements(By.CSS_SELECTOR, 'i.fa-gavel')
                    if not icones:
                        continue  # Não é mandado assinado por oficial
                    
                    # Procura nome do autor próximo ao link ou assinatura
                    nome_autor = _extrair_nome_autor(item, doc_text, log)
                    
                    if log:
                        print(f'[MDD][DEBUG] Mandado encontrado: {doc_text} | Autor: {nome_autor}')
                    return nome_autor, item
                    
            except Exception as e:
                if log:
                    print(f'[MDD][DEBUG] Erro ao processar item {idx}: {e}')
                continue
                
        # Verificação final de conexão
        if not validar_conexao_driver(driver, contexto="MDD_FIM"):
            if log:
                print('[MDD][ERRO_FATAL] Driver em estado inválido ao finalizar busca de mandado')
            return None, None
            
        if log:
            print('[MDD][DEBUG] Nenhum mandado encontrado na timeline.')
        return None, None
        
    except Exception as e:
        if log:
            print(f'[MDD][ERRO] Falha ao buscar último mandado: {e}')
        return None, None

def _extrair_nome_autor(item, doc_text, log):
    """
    Extrai o nome do autor de um item da timeline.
    
    Args:
        item: Elemento da timeline
        doc_text (str): Texto do documento
        log (bool): Se True, imprime logs de debug
    
    Returns:
        str: Nome do autor ou None se não encontrado
    """
    nome_autor = None
    
    # Tenta encontrar assinatura padrão
    try:
        assinatura = item.find_element(By.CSS_SELECTOR, '.assinatura, .autor, .assinante, .nome-assinatura')
        nome_autor = assinatura.text.strip()
    except Exception:
        # Fallback: procura texto logo após o link
        try:
            spans = item.find_elements(By.CSS_SELECTOR, 'span')
            for s in spans:
                s_text = s.text.strip()
                if s_text and s_text.lower() != doc_text:
                    nome_autor = s_text
                    break
        except Exception:
            pass
    
    return nome_autor

def analisar_padrao_mandado(texto, log=True):
    """
    Analisa o padrão de um mandado (positivo/negativo/cancelamento).
    
    Args:
        texto (str): Texto do mandado para análise
        log (bool): Se True, imprime logs de debug
    
    Returns:
        str: 'positivo', 'negativo', 'cancelamento' ou 'indefinido'
    """
    if log:
        print(f"[MANDADOS][OUTROS] Texto extraído para análise:\n{texto}\n---Fim do documento---")
    
    texto_lower = texto.lower()
    
    # Padrão de cancelamento total (prioridade máxima)
    padrao_cancelamento_total = any(p in texto_lower for p in [
        "ordem de cancelamento total",
    ])
    
    if padrao_cancelamento_total:
        if log:
            print("[MANDADOS][OUTROS][LOG] Ordem de cancelamento total detectada")
        return 'cancelamento'
    
    # Padrão positivo
    padrao_positivo = any(p in texto_lower for p in [
        "citei", 
        "intimei", 
        "recebeu o mandado", 
        "de tudo ficou ciente",
        "procedi à intimação",
        "procedi à citação",
        "procedi à entrega do mandado",
        "procedi à penhora",
        "penhorei"
    ])
    
    # Padrão negativo
    padrao_negativo = any(p in texto_lower for p in [
        "não localizado",
        "resultado negativo",
        "diligencias negativas",
        "diligência negativa",
        "não encontrado",
        "deixei de citar",
        "deixei de efetuar",
        "deixei de comparacer",
        "deixei de intimar",
        "deixei de penhorar",
        "não logrei êxito",
        "desconhecido no local",
        "não foi possível efetuar",
        "parou de responder",
        "não foi possível localizar",
    ])
    
    if padrao_positivo:
        if log:
            print("[MANDADOS][OUTROS][LOG] Padrão de mandado POSITIVO encontrado no texto.")
        return 'positivo'
    elif padrao_negativo:
        if log:
            print("[MANDADOS][OUTROS][LOG] Padrão de mandado NEGATIVO encontrado no texto.")
        return 'negativo'
    else:
        if log:
            print("[MANDADOS][OUTROS][LOG] Mandado sem padrão reconhecido.")
        return 'indefinido'

def remover_acentos(txt):
    """
    Remove acentos de um texto para facilitar comparações.
    
    Args:
        txt (str): Texto com acentos
    
    Returns:
        str: Texto sem acentos
    """
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

def verificar_penhora_mandado_anterior(driver, log=True):
    """
    Verifica se o mandado anterior contém 'penhora' no texto.
    
    Args:
        driver: Instância do WebDriver
        log (bool): Se True, imprime logs de debug
    
    Returns:
        bool: True se o mandado anterior contém 'penhora'
    """
    try:
        from Fix import extrair_documento, safe_click
        
        autor_ant, elemento_ant = ultimo_mdd(driver, log=log)
        if elemento_ant:
            try:
                link_ant = elemento_ant.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                # Usar safe_click ao invés de JS direto + click normal
                safe_click(driver, link_ant)
                
                # Aguarda carregamento
                import time
                time.sleep(1)
                
                texto_mandado_ant, _ = extrair_documento(driver)
                if texto_mandado_ant and 'penhora' in texto_mandado_ant.lower():
                    if log:
                        print("[MANDADOS][OUTROS][LOG] Mandado anterior contém 'penhora'")
                    return True
                else:
                    if log:
                        print("[MANDADOS][OUTROS][LOG] Mandado anterior não contém 'penhora'")
                    return False
                    
            except Exception as e:
                if log:
                    print(f"[MANDADOS][OUTROS][ERRO] Falha ao processar mandado anterior: {e}")
                return False
        else:
            if log:
                print("[MANDADOS][OUTROS][LOG] Mandado anterior não encontrado")
            return False
            
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Falha ao verificar mandado anterior: {e}")
        return False
