from typing import Optional, List

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

from Fix.log import logger


def retirar_sigilo(elemento: WebElement, driver: Optional[WebDriver] = None, debug: bool = False) -> bool:
    """
    ✅ DIRETO E SIMPLES: Verifica tl-nao-sigiloso (AZUL) antes de qualquer ação.
    
    Lógica clara:
    1. Busca botão de sigilo
    2. Se TEM tl-nao-sigiloso (azul) → retorna True (JÁ SEM SIGILO)
    3. Se TEM tl-sigiloso (vermelho) → clica para remover
    4. Caso contrário → retorna True (sem sigilo)
    
    Args:
        elemento: WebElement do documento na timeline
        driver: WebDriver Selenium
        debug: Exibir logs detalhados
    
    Returns:
        True se sigilo foi removido ou já estava removido, False em erro
    """
    import time
    from selenium.webdriver.common.by import By

    if not elemento:
        return False

    if not driver:
        try:
            if hasattr(elemento, '_parent') and hasattr(elemento._parent, 'execute_script'):
                driver = elemento._parent
            else:
                return False
        except Exception:
            return False

    try:
        # Buscar botão de sigilo
        btn_sigilo = None
        seletores = [
            "pje-doc-sigiloso button",
            "pje-doc-sigiloso span button",
            "button i.fa-wpexplorer",
            "i.fa-wpexplorer"
        ]
        
        for seletor in seletores:
            try:
                btn_sigilo = elemento.find_element(By.CSS_SELECTOR, seletor)
                if btn_sigilo.is_displayed():
                    break
                else:
                    btn_sigilo = None
            except Exception:
                continue
        
        # Sem botão = sem sigilo
        if not btn_sigilo:
            return True
        
        #  USAR ARIA-LABEL COMO INDICADOR DEFINITIVO
        aria_label = (btn_sigilo.get_attribute("aria-label") or "").lower()
        
        if "inserir sigilo" in aria_label:
            # Botão para INSERIR = documento JÁ ESTÁ SEM SIGILO
            return True
        
        #  VERIFICAÇÃO: Se aria-label TEM "retirar sigilo" = PRECISA REMOVER
        if "retirar sigilo" in aria_label:
            # TEM "retirar sigilo" no aria-label = SIGILO ATIVO → REMOVER
            pass
        else:
            # Sem aria-label claro = verificar ícone dentro do botão
            try:
                icone = btn_sigilo.find_element(By.CSS_SELECTOR, "i.fa-wpexplorer")
                classes_icone = (icone.get_attribute("class") or "").lower()
                
                if 'tl-nao-sigiloso' in classes_icone:
                    return True
                
                if 'tl-sigiloso' not in classes_icone:
                    return True
                
                # Se chegou aqui e tem tl-sigiloso, vai clicar
            except Exception as e_icone:
                if debug:
                    logger.error(f"[SIGILO_DEBUG] Erro ao verificar ícone: {e_icone} → considerando SEM SIGILO")
                return True
        
        try:
            driver.execute_script('arguments[0].click();', btn_sigilo)
            time.sleep(0.3)  # Aguardar processamento
            
            #  VERIFICAR se aria-label mudou para "inserir sigilo"
            tentativas = 0
            while tentativas < 5:
                time.sleep(0.2)
                try:
                    novo_aria = (btn_sigilo.get_attribute("aria-label") or "").lower()
                    if "inserir sigilo" in novo_aria:
                        return True
                    tentativas += 1
                except Exception:
                    break
            
            return True
        except Exception as e1:
            if debug:
                logger.error(f"[SIGILO_DEBUG] Erro no clique JS: {e1}")
            try:
                btn_sigilo.click()
                time.sleep(0.8)
                return True
            except Exception as e2:
                if debug:
                    logger.error(f"[SIGILO_DEBUG]  Erro no clique direto: {e2}")
                return False
    
    except Exception as e:
        if debug:
            logger.error(f"[SIGILO_DEBUG]  Erro geral: {e}")
        return False

def retirar_sigilo_fluxo_argos(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True, debug: bool = False) -> dict:
    """
    ✅ FUNÇÃO ÚNICA PARA TODO O FLUXO DE REMOÇÃO DE SIGILO DO ARGOS
    
    Respeita a ORDEM OBRIGATÓRIA do fluxo ARGOS:
    1º - Certidão de devolução (PRIMEIRO)
    2º - Demais documentos: certidão expedição, intimação, decisão, planilha
    
    Args:
        driver: WebDriver Selenium
        documentos_sequenciais: Lista de WebElements dos documentos
        log: Exibir logs detalhados
        debug: Ativar modo debug com detalhes das classes CSS
    
    Returns:
        dict com status de cada etapa e documentos processados
    """
    if not documentos_sequenciais:
        return {'sucesso': False, 'etapa_erro': 'nenhum_documento'}
    
    resultado = {
        'sucesso': True,
        'certidao_devolucao': None,
        'demais_documentos': [],
        'total_processados': 0
    }
    
    if log:
        pass
    
    # =======================================================
    # ETAPA 1: CERTIDÃO DE DEVOLUÇÃO (PRIMEIRO!)
    # =======================================================
    certidao_encontrada = None
    for doc in reversed(documentos_sequenciais):
        texto = doc.text.strip().lower()
        if "certidão de devolução" in texto or "certidao de devolucao" in texto:
            certidao_encontrada = doc
            break
    
    if not certidao_encontrada:
        resultado['certidao_devolucao'] = {'status': 'nao_encontrada'}
    else:
        # Verificar se tem sigilo
        links_doc = certidao_encontrada.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
        tem_sigilo = False
        
        if links_doc:
            link_correto = None
            for link in links_doc:
                target = link.get_attribute('target') or ''
                role = link.get_attribute('role') or ''
                if role == 'button' or target != '_blank':
                    link_correto = link
                    break
            
            if not link_correto and links_doc:
                link_correto = links_doc[-1]
            
            if link_correto:
                classes_link = (link_correto.get_attribute('class') or '')
                tem_sigilo = 'is-sigiloso' in classes_link
        
        if not tem_sigilo:
            resultado['certidao_devolucao'] = {'status': 'ja_sem_sigilo'}
        else:
            if retirar_sigilo(certidao_encontrada, driver, debug=debug):
                resultado['certidao_devolucao'] = {'status': 'removido'}
                resultado['total_processados'] += 1
            else:
                resultado['certidao_devolucao'] = {'status': 'erro'}
                resultado['sucesso'] = False
    
    # =======================================================
    # ETAPA 2: DEMAIS DOCUMENTOS ESPECÍFICOS (DENTRO DO BLOCO)
    # =======================================================
    tipos_especificos = {
        'certidao_expedicao': {
            'palavras': ['certidão de expedição', 'certidao de expedicao'],
            'limite': 1,
            'encontrados': []
        },
        'intimacao': {
            'palavras': ['intimação(', 'intimacao('],
            'limite': 1,
            'encontrados': []
        },
        'decisao': {
            'palavras': ['decisão(', 'decisao('],
            'limite': 1,
            'encontrados': []
        },
        'planilha': {
            'palavras': ['planilha de atualização', 'planilha de atualizacao'],
            'limite': 1,
            'encontrados': []
        }
    }
    
    # Encontrar onde está a decisão (fim do bloco)
    idx_decisao = None
    for idx in range(len(documentos_sequenciais)):
        texto = documentos_sequenciais[idx].text.strip().lower()
        if "decisão(" in texto or "decisao(" in texto:
            idx_decisao = idx
            break
    
    if idx_decisao is None:
        return resultado
    
    # Processar índices 1, 2, 3... até ANTES da decisão
    for idx in range(1, idx_decisao):
        doc = documentos_sequenciais[idx]
        texto = doc.text.strip().lower()
        
        for tipo_nome, tipo_config in tipos_especificos.items():
            if len(tipo_config['encontrados']) >= tipo_config['limite']:
                continue
            
            for palavra in tipo_config['palavras']:
                if palavra in texto:
                    tipo_config['encontrados'].append({
                        'elemento': doc,
                        'texto': texto[:50],
                        'palavra': palavra
                    })
                    break
    
    # Adicionar decisão (índice 4 - fim do bloco)
    doc_decisao = documentos_sequenciais[idx_decisao]
    texto_decisao = doc_decisao.text.strip().lower()
    tipos_especificos['decisao']['encontrados'].append({
        'elemento': doc_decisao,
        'texto': texto_decisao[:50],
        'palavra': 'decisão'
    })
    
    # Remover sigilo dos demais documentos
    for tipo_nome, tipo_config in tipos_especificos.items():
        if not tipo_config['encontrados']:
            continue
        
        for doc_info in tipo_config['encontrados']:
            elemento = doc_info['elemento']
            texto = doc_info['texto']
            
            # Verificar se tem sigilo
            links_doc = elemento.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
            tem_sigilo = False
            
            if links_doc:
                link_correto = None
                for link in links_doc:
                    target = link.get_attribute('target') or ''
                    role = link.get_attribute('role') or ''
                    if role == 'button' or target != '_blank':
                        link_correto = link
                        break
                
                if not link_correto and links_doc:
                    link_correto = links_doc[-1]
                
                if link_correto:
                    classes_link = (link_correto.get_attribute('class') or '')
                    tem_sigilo = 'is-sigiloso' in classes_link
                    
                    if debug:
                        pass
            
            if not tem_sigilo:
                resultado['demais_documentos'].append({
                    'tipo': tipo_nome,
                    'texto': texto,
                    'status': 'ja_sem_sigilo'
                })
            else:
                if retirar_sigilo(elemento, driver, debug=debug):
                    resultado['demais_documentos'].append({
                        'tipo': tipo_nome,
                        'texto': texto,
                        'status': 'removido'
                    })
                    resultado['total_processados'] += 1
                else:
                    if log:
                        logger.error(f"[SIGILO_ARGOS][2/2] {tipo_nome.upper()}:  Erro")
                    resultado['demais_documentos'].append({
                        'tipo': tipo_nome,
                        'texto': texto,
                        'status': 'erro'
                    })
                    resultado['sucesso'] = False
    
    return resultado

# Manter aliases para compatibilidade com código existente
def retirar_sigilo_certidao_devolucao_primeiro(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True) -> bool:
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna apenas status da certidão."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    cert_status = resultado.get('certidao_devolucao', {}).get('status', 'erro')
    return cert_status in ['removido', 'ja_sem_sigilo', 'nao_encontrada']

def retirar_sigilo_demais_documentos_especificos(driver, documentos_sequenciais, log=True):
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna lista de demais documentos."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    return resultado.get('demais_documentos', [])

def retirar_sigilo_documentos_especificos(driver, documentos_sequenciais, log=True):
    """
    ✅ FUNÇÃO EFICIENTE - Remove sigilo APENAS dos documentos específicos fornecidos:
    Os documentos_sequenciais já vêm filtrados da buscar_documentos_sequenciais()
    MÁXIMO 5 documentos: 1 certidão devolução, 1 certidão expedição, 1 intimação, 1 decisão, 1 planilha
    
    NADA MAIS que isso - SEM VARRER TIMELINE INTEIRA!
    """
    if not documentos_sequenciais:
        return []
    
    #  EFICIÊNCIA: Os documentos já vêm filtrados, apenas remover sigilo diretamente
    documentos_processados = []
    total_processados = 0
    
    #  PROCESSAMENTO DIRETO: Remove sigilo apenas dos documentos fornecidos
    for i, elemento in enumerate(documentos_sequenciais):
        try:
            texto = elemento.text.strip()[:50] if elemento.text else f"DOCUMENTO_{i+1}"
            
            resultado_sigilo = retirar_sigilo(elemento, driver)
            
            if resultado_sigilo:
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'sucesso'
                })
                total_processados += 1
            else:
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'falha'
                })
                
        except Exception as e:
            if log:
                logger.error(f"[SIGILO_ESPECÍFICO]  Erro ao processar documento {i+1}: {e}")
            documentos_processados.append({
                'indice': i+1,
                'texto': texto if 'texto' in locals() else f"DOCUMENTO_{i+1}",
                'status': 'erro',
                'erro': str(e)
            })
    
    #  RELATÓRIO FINAL
    if log:
        
        for doc in documentos_processados:
            status_icon = "" if doc['status'] == 'sucesso' else "" if doc['status'] == 'erro' else ""
        
    
    return documentos_processados