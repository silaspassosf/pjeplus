import logging
logger = logging.getLogger(__name__)

"""
Documents - Busca e Extração de Documentos PJe
===============================================

Extração do Fix/core.py → documents/ (~600 linhas)

FUNÇÕES EXTRAÍDAS (lines 2270-3050):
- verificar_documento_decisao_sentenca: Verifica decisão/sentença
- buscar_ultimo_mandado: Busca último mandado na timeline
- buscar_mandado_autor: Busca mandado com identificação do autor
- buscar_documentos_sequenciais: Busca bloco ARGOS sequencial
- buscar_documentos_polo_ativo: Busca docs do polo ativo (2 versões)
- buscar_documento_argos: Busca documento com regras ARGOS

RESPONSABILIDADE:
- Buscar documentos específicos na timeline PJe
- Validar tipos de documentos
- Extrair metadados (autor, data, tipo)
- Filtrar por polo (ativo/passivo)

DEPENDÊNCIAS:
- selenium.webdriver
- Fix.selenium_base: esperar_elemento
- Fix.extracao: extrair_direto, extrair_documento
- re, time

USO TÍPICO:
    from Fix.documents import (
        verificar_documento_decisao_sentenca,
        buscar_documentos_sequenciais,
        buscar_documento_argos
    )
    
    # Verificar decisão
    if verificar_documento_decisao_sentenca(driver):
        print("Decisão encontrada!")
    
    # Buscar bloco ARGOS
    docs = buscar_documentos_sequenciais(driver)

AUTOR: Extração PJePlus Refactoring Phase 2
DATA: 2025-01-29
"""

import re
import time
from typing import Optional, List, Dict, Tuple, Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Fix.selenium_base.wait_operations import esperar_elemento

def verificar_documento_decisao_sentenca(driver: WebDriver) -> bool:
    """
    Verifica se existe um documento com 'decisão' ou 'sentença' no nome.
    
    Args:
        driver: WebDriver do Selenium
    
    Returns:
        True se encontrou, False caso contrário
    
    Exemplo:
        if verificar_documento_decisao_sentenca(driver):
            print("Documento de decisão/sentença encontrado")
    """
    try:
        seletor_nomes_docs = 'pje-arvore-documento .node-content-wrapper span'
        nomes_docs = driver.find_elements(By.CSS_SELECTOR, seletor_nomes_docs)

        for nome_element in nomes_docs:
            doc_text = nome_element.text.lower()
            if 'decisão' in doc_text or 'sentença' in doc_text:
                return True

        return False
        
    except Exception as e:
        logger.error(f'[DOC CHECK][ERRO] Falha ao verificar documentos: {e}')
        return False

def buscar_ultimo_mandado(driver: WebDriver, log: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """
    Busca o último documento do tipo 'mandado' na timeline do processo.
    
    Args:
        driver: WebDriver do Selenium
        log: Ativa logging (default: True)
    
    Returns:
        Tupla (texto, tipo) ou (None, None) se não encontrado
    
    Exemplo:
        texto, tipo = buscar_ultimo_mandado(driver)
        if texto:
            print(f"Mandado encontrado: {tipo}")
    """
    try:
        # Espera a timeline carregar
        itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens_timeline:
            return None, None

        # Procura pelo último documento do tipo 'mandado'
        for item in itens_timeline:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()

                # Verifica se é do tipo 'mandado'
                if 'mandado' in doc_text:
                    link.click()
                    time.sleep(1)

                    # Extrai o texto do documento
                    texto = item.text
                    return texto, 'mandado'

            except Exception as e:
                if log:
                    logger.error(f'[MANDADO][ERRO] Falha ao processar item: {e}')
                continue

        return None, None

    except Exception as e:
        if log:
            logger.error(f'[MANDADO][ERRO] Falha geral: {e}')
        return None, None

def buscar_mandado_autor(driver: WebDriver, log: bool = True) -> Optional[Dict[str, str]]:
    """
    Busca o último documento do tipo 'mandado' e identifica o autor.
    
    Após localizar, busca o ícone de martelo (gavel) e registra o autor.
    
    Args:
        driver: WebDriver do Selenium
        log: Ativa logging (default: True)
    
    Returns:
        Dict com chaves 'texto', 'tipo', 'autor' ou None se não encontrado
    
    Exemplo:
        resultado = buscar_mandado_autor(driver)
        if resultado:
            print(f"Mandado de {resultado['autor']}")
    """
    try:
        itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens_timeline:
            return None

        for item in itens_timeline:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                
                if 'mandado' in doc_text:
                    link.click()
                    time.sleep(1)
                    texto = item.text
                    autor = 'DESCONHECIDO'
                    
                    # Busca o ícone de martelo (gavel) e extrai o nome do autor
                    try:
                        gavel_icon = item.find_element(By.CSS_SELECTOR, 'i.fa-gavel, i.fas.fa-gavel')
                        parent = gavel_icon.find_element(By.XPATH, './ancestor::*[1]')
                        autor_text = parent.text.strip().upper()
                        
                        if 'SILAS PASSOS' in autor_text:
                            autor = 'SILAS PASSOS'
                        else:
                            autor = autor_text
                            
                    except Exception:
                        pass
                    return {'texto': texto, 'tipo': 'mandado', 'autor': autor}
                    
            except Exception as e:
                if log:
                    logger.error(f'[MANDADO][ERRO] Falha ao processar item: {e}')
                continue
        
        return None
        
    except Exception as e:
        if log:
            logger.error(f'[MANDADO][ERRO] Falha geral: {e}')
        return None

def buscar_documentos_sequenciais(driver: WebDriver, log: bool = True) -> List[Any]:
    """
    Busca documentos do bloco ARGOS na ordem correta.
    
    Bloco ARGOS (ordem cronológica - mais recente para mais antiga):
    0. Certidão de devolução (mais recente)
    1-3. Documentos do meio: certidão expedição, intimação, planilha
    4. Decisão (mais antiga - fim do bloco)
    
    IMPORTANTE: Intimação deve estar ENTRE certidão devolução e decisão.
    
    Args:
        driver: WebDriver do Selenium
        log: Ativa logging (default: True)
    
    Returns:
        Lista de elementos WebElement dos documentos encontrados
    
    Exemplo:
        docs = buscar_documentos_sequenciais(driver)
        print(f"Encontrados {len(docs)} documentos")
    """
    try:
        time.sleep(2)
        elementos = driver.find_elements(By.CSS_SELECTOR, "li.tl-item-container")
        
        if not elementos:
            if log:
                logger.error('[DOCUMENTOS_SEQUENCIAIS][ERRO] Timeline vazia')
            return []
        
        # ETAPA 1: Encontrar certidão de devolução (início do bloco - documento único)
        if log:
            logger.info('[DOC_SEQ] Buscando certidão de devolução...')
        idx_cert_devolucao = None
        for idx, elem in enumerate(elementos):
            texto = elem.text.strip().lower()
            # Marcador único: "certidão de devolução" (documento único no bloco)
            if "certidão de devolução" in texto or "certidao de devolucao" in texto:
                idx_cert_devolucao = idx
                if log:
                    logger.info(f'[DOC_SEQ] ✅ Certidão de devolução encontrada no índice {idx}: {texto[:60]}...')
                # Sempre escolher a primeira ocorrência (top da timeline)
                break
        
        if idx_cert_devolucao is None:
            if log:
                logger.error('[DOCUMENTOS_SEQUENCIAIS][ERRO] Certidão de devolução não encontrada')
            return []
        
        # ETAPA 2: Encontrar decisão (fim do bloco) APÓS certidão devolução
        if log:
            logger.info('[DOC_SEQ] Buscando decisão/sentença após a certidão...')
        idx_decisao = None
        # Seguir o comportamento legado: procurar a PRIMEIRA decisão após a certidão
        for idx in range(idx_cert_devolucao + 1, len(elementos)):
            texto = elementos[idx].text.strip().lower()
            if "decis" in texto or "sentên" in texto or "sentenca" in texto or "decisão" in texto:
                idx_decisao = idx
                if log:
                    logger.info(f'[DOC_SEQ]  Decisão encontrada no índice {idx}: {texto[:40]}...')
                break
        
        if idx_decisao is None:
            if log:
                logger.error('[DOCUMENTOS_SEQUENCIAIS][ERRO] Decisão não encontrada após certidão')
            return []
        
        # ETAPA 3: Buscar documentos do meio APENAS entre certidão e decisão
        if log:
            logger.info(f'[DOC_SEQ] Identificando documentos entre índices {idx_cert_devolucao} e {idx_decisao}...')
        resultados = [elementos[idx_cert_devolucao]]  # Adicionar certidão
        
        tipos_meio = {
            'Certidão de expedição': ['certidão de expedição', 'certidao de expedicao'],
            'Planilha': ['planilha de atualização', 'planilha de atualizacao'],
            'Intimação': ['intimação(', 'intimacao(']
        }
        
        # Tracking para garantir apenas UM de cada tipo (evitar listas gigantescas)
        tipos_encontrados = set()
        
        for idx in range(idx_cert_devolucao + 1, idx_decisao):
            elem = elementos[idx]
            texto = elem.text.strip().lower()
            
            for tipo_nome, palavras in tipos_meio.items():
                if tipo_nome in tipos_encontrados:
                    continue
                    
                found = False
                for palavra in palavras:
                    if palavra in texto:
                        if log:
                            logger.info(f'[DOC_SEQ]  Documento do meio encontrado: {tipo_nome} ({texto[:30]})')
                        resultados.append(elem)
                        tipos_encontrados.add(tipo_nome)
                        found = True
                        break
                if found:
                    break
        
        # ETAPA 4: Adicionar decisão (fim do bloco)
        resultados.append(elementos[idx_decisao])
        
        if log:
            logger.info(f'[DOC_SEQ] Total de documentos identificados: {len(resultados)}')
        return resultados
        
    except Exception as e:
        if log:
            logger.error(f'[DOCUMENTOS_SEQUENCIAIS][ERRO] {str(e)}')
        return []

def buscar_documentos_polo_ativo(
    driver: WebDriver,
    polo: str = "autor",
    limite_dias: Optional[int] = None,
    debug: bool = False
) -> List[Dict[str, str]]:
    """
    Busca documentos na timeline filtrando por polo ativo (autor/réu).
    
    Args:
        driver: WebDriver do Selenium
        polo: "autor" ou "reu" (default: "autor")
        limite_dias: Se informado, filtra documentos dos últimos N dias (opcional)
        debug: Ativa logging detalhado (default: False)
    
    Returns:
        Lista de dicionários com chaves 'data', 'titulo', 'descricao', 'texto_completo', 'polo'
    
    Exemplo Básico:
        docs = buscar_documentos_polo_ativo(driver, polo="autor")
    
    Exemplo com Limite:
        docs = buscar_documentos_polo_ativo(driver, polo="autor", limite_dias=30)
    
    Exemplo Réu:
        docs = buscar_documentos_polo_ativo(driver, polo="reu", debug=True)
    """
    try:
        esperar_elemento(driver, "li.tl-item-container", timeout=10)

        # Usar JavaScript para extrair dados da timeline de forma otimizada
        script = """
            var poloTarget = arguments[0];
            var limiteDias = arguments[1];

            // Função para determinar se é polo ativo baseado no texto
            function isPoloAtivo(texto, polo) {
                if (!texto) return false;

                texto = texto.toLowerCase();
                if (polo === 'autor') {
                    return (texto.includes('autor') && !texto.includes('réu')) ||
                           texto.includes('reclamante') ||
                           texto.includes('exequente');
                } else if (polo === 'reu') {
                    return (texto.includes('réu') && !texto.includes('autor')) ||
                           texto.includes('reclamado') ||
                           texto.includes('executado');
                }
                return false;
            }

            // Coletar todos os itens da timeline
            var itens = document.querySelectorAll('li.tl-item-container');
            var documentos = [];

            for (var i = 0; i < itens.length; i++) {
                var item = itens[i];

                try {
                    var dataElement = item.querySelector('.tl-item-date');
                    var data = dataElement ? dataElement.textContent.trim() : '';

                    var tituloElement = item.querySelector('.tl-item-title, .tl-item-header');
                    var titulo = tituloElement ? tituloElement.textContent.trim() : '';

                    var descElement = item.querySelector('.tl-item-description, .tl-item-content');
                    var descricao = descElement ? descElement.textContent.trim() : '';

                    var textoCompleto = (titulo + ' ' + descricao).toLowerCase();

                    if (isPoloAtivo(textoCompleto, poloTarget)) {
                        var documentoValido = true;
                        if (limiteDias) {
                            try {
                                var dataObj = new Date(data.split('/').reverse().join('-'));
                                var hoje = new Date();
                                var diffTime = Math.abs(hoje - dataObj);
                                var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                                if (diffDays > limiteDias) {
                                    documentoValido = false;
                                }
                            } catch (e) {
                                documentoValido = true;
                            }
                        }

                        if (documentoValido) {
                            documentos.push({
                                'data': data,
                                'titulo': titulo,
                                'descricao': descricao,
                                'texto_completo': textoCompleto,
                                'polo': poloTarget
                            });
                        }
                    }
                } catch (e) {
                    continue;
                }
            }

            return documentos;
        """

        documentos = driver.execute_script(script, polo, limite_dias)

        return documentos

    except Exception as e:
        return []

def buscar_documento_argos(driver: WebDriver, log: bool = True, ignorar_indices: Optional[List[int]] = None) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Busca documento (decisão/despacho) que contenha REGRAS ARGOS.
    
    Regras ARGOS verificadas:
    - "defiro a instauração"
    - "argos"
    - "realize-se a pesquisa infojud"
    
    Estratégia:
    1. Procura por uma "planilha" na timeline; se encontrada, busca por despacho/decisão ANTERIOR
    2. Se não houver planilha, busca pelo primeiro despacho/decisão visível
    3. Verifica se o documento contém uma das REGRAS ARGOS
    4. Se não contiver, continua buscando o próximo despacho/decisão
    
    Args:
        driver: WebDriver do Selenium
        log: Ativa logging (default: True)
        ignorar_indices: Lista de índices da timeline que devem ser ignorados (já processados sem sucesso)
    
    Returns:
        Tupla (texto, tipo, indice) ou (None, None, None) se não encontrado
    
    Exemplo:
        texto, tipo, idx = buscar_documento_argos(driver)
        if texto:
            print(f"Documento ARGOS encontrado no índice {idx}: {tipo}")
    
    Notas:
        - Requer Fix.extracao instalado
        - Aceita apenas despacho, decisão, sentença ou conclusão
        - Valida conteúdo do documento contra regras ARGOS
    """
    # Importar localmente para evitar import circular
    try:
        from Fix.extracao import extrair_direto, extrair_documento
    except Exception:
        logger.error('[ARGOS][DOC][ERRO] Módulo Fix.extracao não disponível')
        return None, None, None
    
    ignorar_indices = ignorar_indices or []
    
    # Regras ARGOS que o documento deve conter
    REGRAS_ARGOS = [
        'defiro a instauração',
        'defiro a instauracao',
        'argos',
        'realize-se a pesquisa infojud',
        'realize se a pesquisa infojud',
        'através do sistema argos',
        'atraves do sistema argos',
    ]
    
    try:
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            return None, None, None

        # Localizar índice da primeira planilha (se houver)
        planilha_idx = None
        for i, it in enumerate(itens):
            try:
                link = it.find_element(By.CSS_SELECTOR, 'a.tl-documento')
                txt = (link.text or '').lower()
                if 'planilha de atualização' in txt or 'planilha de atuali' in txt:
                    planilha_idx = i
                    break
            except Exception:
                continue

        # Definir range de busca
        if planilha_idx is not None:
            search_range = range(0, planilha_idx)
        else:
            search_range = range(0, len(itens))

        # Buscar candidatos
        candidates = []
        for idx in search_range:
            if idx in ignorar_indices:
                continue
                
            try:
                item = itens[idx]
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = (link.text or '').lower()
                
                # Aceita APENAS despacho, decisão, sentença ou conclusão
                if re.search(r'^(despacho|decisão|sentença|conclusão)', doc_text.strip()):
                    candidates.append((idx, doc_text))
                    
            except Exception:
                continue

        if not candidates:
            return None, None, None

        # Iterar pelos candidatos até encontrar um que contenha uma REGRA ARGOS
        for idx, doc_text in candidates:
            try:
                item = itens[idx]
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                
                # Selecionar o documento na timeline
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                time.sleep(0.5)
                link.click()
                time.sleep(1)
                
                # Extrair o texto REAL do documento usando a função robusta do Fix
                # Essa função lê diretamente do painel ativo sem abrir modais
                extracao_res = extrair_direto(driver, debug=log)
                texto = extracao_res.get('conteudo')
                
                if not texto:
                    if log:
                        logger.warning(f'[ARGOS][DOC] Extração de conteúdo via extrair_direto falhou para candidato #{idx}. Tentando item.text como fallback.')
                    texto = item.text
                
                # Retorna o candidato com o texto extraído
                return texto, ('despacho' if 'despacho' in doc_text else 'decisão'), idx
                
            except Exception as e:
                if log:
                    logger.error(f'[ARGOS][DOC] Erro ao processar candidato #{idx}: {e}')
                continue

        return None, None, None

    except Exception as e:
        if log:
            logger.error(f'[ARGOS][DOC] Erro geral: {e}')
        return None, None, None
