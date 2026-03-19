import time
import unicodedata
from typing import Optional, Any, Tuple

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Fix import aguardar_e_clicar, extrair_direto, extrair_documento
from Fix.abas import validar_conexao_driver
from Fix.log import logger

from atos import ato_meios, ato_edital


def ultimo_mdd(driver: WebDriver, log: bool = True) -> Tuple[Optional[str], Optional[Any]]:
    """
    Busca o último mandado na timeline (item com texto começando por 'Mandado' e ícone de gavel) e retorna (nome_autor, elemento_mandado).
    Versão robusta com verificações de conectividade.
    """
    try:
        # Verificação inicial de conexão 
        if not validar_conexao_driver(driver, contexto="MDD_INICIO"):
            if log:
                logger.error('[MDD][ERRO_FATAL] Driver em estado inválido ao buscar mandado')
            return None, None
            
        # Usando aguardar_e_clicar ao invés de find_elements direto para maior robustez
        timeline = aguardar_e_clicar(driver, 'ul.timeline-container', timeout=5)
        if not timeline:
            if log:
                logger.error('[MDD][ERRO] Timeline não encontrada, tentando método direto')
            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        else:
            itens = timeline.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        
        if not itens:
            if log:
                logger.warning('[MDD][ALERTA] Nenhum item encontrado na timeline')
            return None, None
            
        for idx, item in enumerate(itens):
            try:
                # Verificação periódica de conexão durante loop
                if idx % 10 == 0 and idx > 0:  # Verificar a cada 10 itens para não impactar performance
                    if not validar_conexao_driver(driver, contexto=f"MDD_LOOP_{idx}"):
                        if log:
                            logger.error(f'[MDD][ERRO_FATAL] Driver em estado inválido durante loop (item {idx})')
                        return None, None
                        
                # Usa wait com timeout curto para não prejudicar performance
                link = aguardar_e_clicar(driver, item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])'), timeout=1)
                if not link:
                    continue
                    
                doc_text = link.text.strip().lower()
                if doc_text.startswith('mandado'):
                    # Procura ícone de gavel (fa-gavel)
                   
                    icones = item.find_elements(By.CSS_SELECTOR, 'i.fa-gavel')
                    if not icones:
                        continue  # Não é mandado assinado por oficial
                    # Procura nome do autor próximo ao link ou assinatura
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
                    return nome_autor, item
            except Exception as e:
                if log:
                    logger.error(f'[MDD][DEBUG] Erro ao processar item {idx}: {e}')
                continue
                
        # Verificação final de conexão
        if not validar_conexao_driver(driver, contexto="MDD_FIM"):
            if log:
                logger.error('[MDD][ERRO_FATAL] Driver em estado inválido ao finalizar busca de mandado')
            return None, None
            
        return None, None
    except Exception as e:
        if log:
            logger.error(f'[MDD][ERRO] Falha ao buscar último mandado: {e}')
        return None, None

def fluxo_mandados_outros(driver: WebDriver, log: bool = True) -> None:
    """
    Processa o fluxo de mandados não-Argos (Oficial de Justiça).
    1. Verifica se é certidão de oficial através do cabeçalho
    2. Extrai e analisa o texto da certidão
    3. Verifica padrões de mandado positivo/negativo
    4. Cria GIGS ou executa atos conforme resultado
    """
    try:
        # Usa aguardar_e_clicar mais robusto ao invés de find_element direto
        cabecalho = aguardar_e_clicar(driver, ".cabecalho-conteudo .mat-card-title", timeout=5, retornar_elemento=True)
        if not cabecalho:
            if log:
                logger.warning('[MANDADOS][OUTROS][ALERTA] Cabeçalho não encontrado. Tentando fallback.')
            cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")
            
        titulo_documento = cabecalho.text.lower()
        if log:
            logger.info(f"[MANDADOS][OUTROS] Cabeçalho detectado: {cabecalho.text}")
        
        eh_certidao_oficial = any(p in titulo_documento for p in [
            "certidão de oficial",
            "certidão de oficial de justiça"
        ])
        
        if not eh_certidao_oficial:
            return
        
    except Exception as e:
        if log:
            logger.error(f"[MANDADOS][OUTROS][ERRO] Erro ao verificar cabeçalho: {e}. Criando GIGS fallback.")
        # REMOVIDO: GIGS 0/PZ MDD considerado inútil
        
        # Fechamento simples sem verificações excessivas (igual ao ARGOS)
        return
    
    def analise_padrao(texto):
        # Diagnostic: confirmar entrada em analise_padrao
        logger.info('[MANDADOS][OUTROS] ENTER analise_padrao()')
        # Normalizar texto removendo acentos para facilitar matching
        try:
            texto_norm = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        except Exception as e:
            logger.info(f'[MANDADOS][OUTROS] analise_padrao: falha na normalizacao: {e}')
            texto_norm = texto
        texto_lower = texto_norm.lower()
        if log:
            logger.info(f"[MANDADOS][OUTROS] Texto (normalizado) para análise (len={len(texto_lower)}):\n{texto_lower[:800]}\n---Fim do documento---")
        
        padrao_positivo = any(p in texto_lower for p in [
            "citei", 
            "intimei", 
            "recebeu o mandado", 
            "de tudo ficou ciente"
            "procedi à intimação",
            "procedi à citação",
            "procedi à entrega do mandado",
            "procedi à penhora",
            "penhorei"

        ])
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
            "não foi possível efetuar"
            "parou de responder",
            "não foi possível localizar",
        ])
        
        padrao_cancelamento_total = any(p in texto_lower for p in [
            "ordem de cancelamento total",
        ])        
        if padrao_cancelamento_total:
            return None
        
        if padrao_positivo:
            pass
        elif padrao_negativo:
            if log:
                logger.info("Padrão de mandado NEGATIVO encontrado no texto.")  # NOVA REGRA: localizar mandado anterior na timeline, extrair conteúdo e, se contiver 'penhora', chamar ato_meios
                logger.info('[MANDADOS][OUTROS] padrao_negativo detectado — invocando ultimo_mdd()')
                autor_ant, elemento_ant = ultimo_mdd(driver, log=log)
                if elemento_ant:
                    try:
                        link_ant = elemento_ant.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                        # Comportamento idêntico ao p2b: abrir link, aguardar estabilização e chamar extrair_direto
                        try:
                            aguardar_e_clicar(driver, link_ant)
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", link_ant)
                            except Exception:
                                pass
                        # Usar WebDriverWait ao invés de time.sleep
                        from Fix.core import wait_for_page_load
                        wait_for_page_load(driver, timeout=5)
                        try:
                            texto_mandado_ant_result = extrair_direto(driver, timeout=10, debug=True, formatar=True)
                        except Exception:
                            texto_mandado_ant_result = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
                        texto_mandado_ant = texto_mandado_ant_result.get('conteudo', '') if texto_mandado_ant_result and texto_mandado_ant_result.get('sucesso') else None
                        if texto_mandado_ant and 'penhora' in texto_mandado_ant.lower():
                            ato_meios(driver)
                    except Exception as e:
                        if log:
                            logger.error(f"Falha ao processar mandado anterior: {e}")
            # Verifica se contém "penhora de bens" no texto
            if "penhora de bens" in texto_lower:
                ato_meios(driver)
            elif "deixei de penhorar" in texto_lower:
                ato_meios(driver)
            else:
                # Busca último mandado na timeline
                autor, elemento = ultimo_mdd(driver, log=log)
                if autor:
                    if 'silas passos' in autor.lower():
                        ato_edital(driver)
                    else:
                        pass
                else:
                    pass
        else:
            pass
    try:
        # ALWAYS emit a short diagnostic log before attempting extraction
        logger.info('[MANDADOS][OUTROS] Invocando extrair_direto() (debug ON para diagnóstico)')
        texto_result = extrair_direto(driver, timeout=10, debug=True, formatar=True)
        logger.info(f'[MANDADOS][OUTROS] extrair_direto returned (diagnostic): {bool(texto_result and texto_result.get("sucesso"))}')
    except Exception as e:
        logger.error(f'[MANDADOS][OUTROS] extrair_direto falhou: {e}')
        texto_result = None

    if not texto_result or not texto_result.get('sucesso'):
        if log:
            logger.info('[MANDADOS][OUTROS] extrair_direto não retornou conteúdo; usando extrair_documento() fallback')
        texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
        texto = texto_tuple[0] if texto_tuple and texto_tuple[0] else None
    else:
        texto = texto_result.get('conteudo', '')
    # Diagnostic: confirmar atribuição de texto
    logger.info(f'[MANDADOS][OUTROS] Texto atribuído len={len(texto) if texto else 0}')
    if not texto:
        if log:
            logger.error("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return
    if log:
        logger.info(f"[MANDADOS][OUTROS] Texto extraído (primeiros 200 chars): {texto[:200].replace('\n',' ')}")
    logger.info('[MANDADOS][OUTROS] Chamando analise_padrao()')
    # Analisar o texto extraído e executar ações padrão (positivo/negativo/cancelamento)
    try:
        analise_padrao(texto)
    except Exception as e:
        if log:
            logger.error(f"[MANDADOS][OUTROS][ERRO] Falha na análise padrão: {e}")
    return