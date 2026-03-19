from typing import Optional, List

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
import time

from Fix.log import logger


def retirar_sigilo(elemento: WebElement, driver: Optional[WebDriver] = None, debug: bool = False) -> bool:
    """
     DIRETO E SIMPLES: Verifica tl-nao-sigiloso (AZUL) antes de qualquer ação.
    
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

    def _link_documento() -> Optional[WebElement]:
        links = elemento.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
        if not links:
            return None
        for link in links:
            role = (link.get_attribute('role') or '').lower()
            target = (link.get_attribute('target') or '').lower()
            if role == 'button' or target != '_blank':
                return link
        return links[-1]

    def _tem_sigilo_link() -> bool:
        link = _link_documento()
        if not link:
            return False
        classes = (link.get_attribute('class') or '').lower()
        if debug:
            logger.info(f"[SIGILO_DEBUG] Classes link documento: {classes}")
        return 'is-sigiloso' in classes

    try:
        if not _tem_sigilo_link():
            if debug:
                logger.info('[SIGILO_DEBUG] Link sem is-sigiloso → JÁ SEM SIGILO')
            return True

        btn_sigilo = None
        seletores = [
            'pje-doc-sigiloso button',
            'pje-doc-sigiloso span button',
            'button i.fa-wpexplorer',
            'i.fa-wpexplorer.tl-sigiloso',
            'i.fa-wpexplorer',
        ]
        for seletor in seletores:
            try:
                candidato = elemento.find_element(By.CSS_SELECTOR, seletor)
                if candidato.is_displayed():
                    btn_sigilo = candidato
                    break
            except Exception:
                continue

        if not btn_sigilo:
            if debug:
                logger.error('[SIGILO_DEBUG] Botão de sigilo não encontrado com link is-sigiloso ativo')
            return False

        try:
            driver.execute_script('arguments[0].click();', btn_sigilo)
        except Exception:
            btn_sigilo.click()

        for _ in range(8):
            time.sleep(0.25)
            try:
                if not _tem_sigilo_link():
                    if debug:
                        logger.info('[SIGILO_DEBUG] ✅ is-sigiloso removido após clique')
                    return True
            except Exception:
                pass

        if debug:
            logger.error('[SIGILO_DEBUG] ❌ Clique executado, mas classe is-sigiloso permaneceu')
        return False

    except Exception as e:
        if debug:
            logger.error(f"[SIGILO_DEBUG] ❌ Erro geral: {e}")
        return False

def retirar_sigilo_fluxo_argos(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True, debug: bool = False) -> dict:
    """
     FUNÇÃO ÚNICA PARA TODO O FLUXO DE REMOÇÃO DE SIGILO DO ARGOS
    
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
    # ETAPA 1: CERTIDÃO DE DEVOLUÇÃO (PRIMEIRO - DOCUMENTO ÚNICO!)
    # =======================================================
    certidao_encontrada = None
    # No fluxo Argos, buscar a certidão mais recente que está no FINAL da lista
    # A lista vem do topo para baixo da timeline, mas precisamos buscar de baixo para cima
    # para pegar o documento mais recente do bloco (mesmo comportamento do legado)
    for doc in reversed(documentos_sequenciais):
        try:
            texto = doc.text.strip().lower()
            # Marcador único: "certidão de devolução" (documento único, sempre o primeiro)
            if "certidão de devolução" in texto or "certidao de devolucao" in texto:
                certidao_encontrada = doc
                if log:
                    logger.info(f'[SIGILO_ARGOS] Certidão de devolução identificada: {texto[:50]}...')
                break
        except:
            continue
    
    if not certidao_encontrada:
        if log:
            logger.info("[SIGILO_ARGOS] Certidão de devolução não encontrada - pulando")
        resultado['certidao_devolucao'] = {'status': 'nao_encontrada'}
    else:
        # Verificar se tem sigilo (lógica simplificada do legado)
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
                
                if debug:
                    logger.info(f"[SIGILO_ARGOS][DEBUG] Classes do link: {classes_link}")
                    logger.info(f"[SIGILO_ARGOS][DEBUG] tem_sigilo (pré-check): {tem_sigilo}")
        
        if not tem_sigilo:
            if log:
                logger.info("[SIGILO_ARGOS] Certidão JÁ SEM SIGILO (verificação prévia)")
            resultado['certidao_devolucao'] = {'status': 'ja_sem_sigilo'}
        else:
            if log:
                logger.info("[SIGILO_ARGOS] Removendo sigilo da certidão (detectado via is-sigiloso)...")
            # A função retirar_sigilo fará verificação definitiva via aria-label
            if retirar_sigilo(certidao_encontrada, driver, debug=debug):
                if log:
                    logger.info("[SIGILO_ARGOS] ✅ Sigilo removido com sucesso")
                resultado['certidao_devolucao'] = {'status': 'removido'}
                resultado['total_processados'] += 1
            else:
                if log:
                    logger.error("[SIGILO_ARGOS] ❌ Falha ao remover sigilo")
                resultado['certidao_devolucao'] = {'status': 'erro'}
                resultado['sucesso'] = False
    
    # =======================================================
    # ETAPA 2: DEMAIS DOCUMENTOS ESPECÍFICOS (DENTRO DO BLOCO)
    # =======================================================
    tipos_especificos = {
        'certidao_pesquisa': {
            'palavras': ['certidão de pesquisa', 'certidao de pesquisa', 'certidão de devolução de pesquisa', 'certidao de devolucao de pesquisa'],
            'limite': 1,
            'encontrados': []
        },
        'certidao_expedicao': {
            'palavras': ['certidão de expedição', 'certidao de expedicao'],
            'limite': 1,
            'encontrados': []
        },
        'intimacao': {
            'palavras': ['intimação(', 'intimacao(', 'intimação', 'intimacao'],
            'limite': 1,
            'encontrados': []
        },
        'decisao': {
            'palavras': ['decisão', 'decisao'],
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
            if debug:
                logger.info(f"[SIGILO_ARGOS][DEBUG] Decisão no índice {idx} - FIM DO BLOCO")
            break
    
    if idx_decisao is None:
        if log:
            logger.info("[SIGILO_ARGOS] Decisão não encontrada")
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
                        logger.info(f"[SIGILO_ARGOS][DEBUG] {tipo_nome.upper()} - Classes link: {classes_link}")
                        logger.info(f"[SIGILO_ARGOS][DEBUG] {tipo_nome.upper()} - tem_sigilo: {tem_sigilo}")
            
            if not tem_sigilo:
                if log:
                    logger.info(f"[SIGILO_ARGOS] {tipo_nome.upper()}: JÁ SEM SIGILO - {texto}")
                resultado['demais_documentos'].append({
                    'tipo': tipo_nome,
                    'texto': texto,
                    'status': 'ja_sem_sigilo'
                })
            else:
                if log:
                    logger.info(f"[SIGILO_ARGOS] {tipo_nome.upper()}: Removendo sigilo...")
                if retirar_sigilo(elemento, driver, debug=debug):
                    if log:
                        logger.info(f"[SIGILO_ARGOS] {tipo_nome.upper()}: Removido")
                    resultado['demais_documentos'].append({
                        'tipo': tipo_nome,
                        'texto': texto,
                        'status': 'removido'
                    })
                    resultado['total_processados'] += 1
                else:
                    if log:
                        logger.error(f"[SIGILO_ARGOS] {tipo_nome.upper()}: Erro")
                    resultado['demais_documentos'].append({
                        'tipo': tipo_nome,
                        'texto': texto,
                        'status': 'erro'
                    })
                    resultado['sucesso'] = False
    
    if log:
        logger.info(f"[SIGILO_ARGOS] Concluído: {resultado['total_processados']} documentos processados")
    
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
     FUNÇÃO EFICIENTE - Remove sigilo APENAS dos documentos específicos fornecidos:
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