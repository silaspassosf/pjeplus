
import logging
import re
import time
import unicodedata
from typing import Any
from selenium.webdriver.common.by import By
from Fix.extracao import extrair_direto, extrair_documento, extrair_pdf, criar_gigs
from atos.movimentos import def_chip, mov_sob, mov_fimsob
from atos.judicial import ato_fal, ato_prov, ato_termoS
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.selenium_base import esperar_elemento, safe_click
from Fix.extracao import bndt
from pathlib import Path
from Fix.scripts import carregar_js

logger = logging.getLogger(__name__)

"""Análise de sobrestamento vencido - função def_sob (extraída de PEC/regras.py)."""


def def_sob(driver: Any, numero_processo: str, observacao: str, debug: bool = False, timeout: int = 10) -> bool:
    """
    Analisa última decisão e executa ação baseada no conteúdo.
    
    Estratégias suportadas:
    - Retorno do feito principal  
    - Penhora no rosto
    - Precatório/RPV/Pequeno valor
    - Juízo universal
    - Prazo prescricional
    - Autos principais
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        observacao: Observação do processo
        debug: Se True, exibe logs detalhados
        timeout: Timeout para operações (segundos)
    
    Returns:
        bool: True se executado com sucesso
    """
    # Guard clauses - validação de parâmetros obrigatórios
    if not driver:
        logger.error("[DEF_SOB] ❌ driver não fornecido")
        return False
    
    if not numero_processo or not isinstance(numero_processo, str):
        logger.error(f"[DEF_SOB] ❌ numero_processo inválido: {numero_processo}")
        return False
    
    if not observacao or not isinstance(observacao, str):
        logger.error(f"[DEF_SOB] ❌ observacao inválida: {observacao}")
        return False
    
    if timeout <= 0:
        logger.error(f"[DEF_SOB] ❌ timeout deve ser positivo: {timeout}")
        return False
    
    def log_msg(msg):
        if debug:
            logger.info(f"[DEF_SOB] {msg}")

    # Log inicial SEMPRE exibido
    logger.info(f"[DEF_SOB] ▶ Iniciando análise sobrestamento: {numero_processo}")
    log_msg(f"Observação: {observacao}")

    try:
        # ===== ETAPA 0: ABRIR TAREFA DO PROCESSO =====
        log_msg("0. Abrindo tarefa do processo...")
        btn_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
        if not btn_tarefa:
            logger.error("[DEF_SOB] ❌ Botão tarefa do processo não encontrado")
            return False
        if not safe_click(driver, btn_tarefa):
            logger.error("[DEF_SOB] ❌ Falha ao clicar no botão tarefa do processo")
            return False

        # ===== ETAPA 1: ENCONTRAR E ITERAR DECISÕES =====
        log_msg("1. Selecionando decisões na timeline...")

        # Procura itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            log_msg(" Nenhum item encontrado na timeline")
            return False
        
        docs_decisao = []
        # O usuário ordenou: "BUSCAR SEMPRE DECISÃO"
        for item in itens:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                
                # Se for decisão ou decisao (ignora sentenças)
                if not re.search(r'decisão|decisao', doc_text):
                    continue
                
                # Ignora expressamente se conter sentença
                if re.search(r'sentença|sentenca', doc_text):
                    continue
                
                docs_decisao.append((item, link))
            except Exception:
                continue
                
        if not docs_decisao:
            logger.error("[DEF_SOB] ❌ Nenhuma decisão encontrada na timeline")
            return False

        # Inicia a iteração
        iteracoes = 0
        for doc_item, doc_link in docs_decisao:
            if iteracoes >= 3:
                log_msg(" Limite de 3 decisões analisadas atingido.")
                logger.warning(f"[DEF_SOB] ⚠️ Limite de iterações atingido sem encontrar regra no processo {numero_processo}. Encaminhando para verificação manual.")
                return True
                
            iteracoes += 1
            log_msg(f" Documento em análise [{iteracoes}/3]: {doc_link.text}")
            
            # ===== EXTRAIR DATA DA DECISÃO =====
            data_decisao_str = None
            try:
                hora_element = doc_item.find_element(By.CSS_SELECTOR, '.tl-item-hora')
                if hora_element:
                    title_attr = hora_element.get_attribute('title')
                    if title_attr:
                        data_decisao_str = title_attr.split(' ')[0]  # "08/08/2023"
                        log_msg(f" Data da decisão extraída: {data_decisao_str}")
            except Exception as e:
                log_msg(f" Erro ao extrair data da decisão: {e}")
            
            # Clica no documento
            try:
                # scroll into view para garantir que está visível
                SCRIPTS_DIR = Path(__file__).parent / "scripts"
                script_scroll = carregar_js("scroll_into_view_instant.js", SCRIPTS_DIR)
                driver.execute_script(script_scroll, doc_link)
                time.sleep(0.5)
                doc_link.click()
                time.sleep(3)  # Aguarda carregar o preview
            except Exception as e:
                log_msg(f" Erro ao clicar no documento: {e}")
                continue

            # ===== ETAPA 2: EXTRAIR CONTEÚDO =====
            log_msg("2. Extraindo conteúdo do documento...")
            texto = None
            try:
                resultado_extracao = extrair_direto(driver, timeout=timeout, debug=debug, formatar=True)
                if resultado_extracao['sucesso']:
                    texto = resultado_extracao['conteudo']
            except Exception as e:
                pass

            if not texto or len(texto.strip()) < 10:
                try:
                    texto = extrair_documento(driver, regras_analise=None, timeout=timeout, log=debug)
                    if texto: texto = texto.lower()
                except Exception:
                    pass

            if not texto or len(texto.strip()) < 10:
                try:
                    texto_pdf = extrair_pdf(driver, log=debug)
                    if texto_pdf: texto = texto_pdf.lower()
                except Exception:
                    pass

            if not texto or len(texto.strip()) < 10:
                log_msg(" Texto extraído muito curto ou vazio para este doc. Pulando para o próximo.")
                continue

            log_texto = texto[:200] + '...' if len(texto) > 200 else texto
            log_msg(f"Texto extraído: {log_texto}")
            
            # ===== ETAPA 3: APLICAR REGRAS BASEADAS NO CONTEÚDO =====
            log_msg("3. Analisando conteúdo e aplicando regras...")
            
            def remover_acentos(txt):
                return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
            
            def normalizar_texto(txt):
                return remover_acentos(txt.lower())
            
            def gerar_regex_geral(termo):
                termo_norm = normalizar_texto(termo)
                palavras = termo_norm.split()
                partes = [re.escape(p) for p in palavras]
                regex = r''  
                for i, parte in enumerate(partes):
                    regex += parte
                    if i < len(partes) - 1:
                        regex += r'[\s\.,;:!\-–—]*'
                return re.compile(rf"{regex}", re.IGNORECASE)
            
            texto_normalizado = normalizar_texto(texto)

            # FUNÇÕES DE AÇÃO
            def executar_mov_sob_retorno_feito():
                try:
                    return mov_sob(driver, numero_processo, "sob 4", debug=True, timeout=timeout)
                except Exception: return False

            def executar_penhora_rosto():
                try:
                    chips_padrao = ["Prazo vencido", "Prazo vencido pós sentença", "SISBAJUD"]
                    try: def_chip(driver, numero_processo=numero_processo, observacao=observacao, chips_para_remover=chips_padrao, debug=debug, timeout=timeout)
                    except: pass
                    ok_gigs = False
                    try:
                        # criar GIGS para 'xs rosto' com 1 dia antes de movimentar
                        ok_gigs = criar_gigs(driver, 1, '', 'xs rosto', detalhe=True)
                    except Exception:
                        ok_gigs = False
                    except: pass
                    try:
                        if mov_sob(driver, numero_processo, "sob 1", debug=debug): return True
                        return ok_gigs
                    except: return ok_gigs
                except Exception: return False

            def executar_mov_sob_precatorio():
                try:
                    chips_padrao = ["Prazo vencido", "Prazo vencido pós sentença", "SISBAJUD"]
                    try: def_chip(driver, numero_processo=numero_processo, observacao=observacao, chips_para_remover=chips_padrao, debug=debug, timeout=timeout)
                    except: pass
                    
                    meses_necessarios = 1
                    try:
                        from datetime import datetime
                        if data_decisao_str:
                            dt = datetime.strptime(data_decisao_str, "%d/%m/%Y")
                            target = datetime(2026, 7, 1)
                            meses_necessarios = (target.year - dt.year) * 12 + (target.month - dt.month)
                            if meses_necessarios < 1: meses_necessarios = 1
                    except: meses_necessarios = 1

                    try:
                        from datetime import datetime
                        hoje = datetime.now()
                        if hoje.year == 2026 and hoje.month == 7:
                            if criar_gigs(driver, '-1', 'silas', 'precatorio'): return True
                            return False
                    except: pass

                    return mov_sob(driver, numero_processo, f"sob {meses_necessarios}", debug=True, timeout=timeout)
                except Exception: return False

            def executar_juizo_universal():
                # implementação complexa omitida - vamos retornar False temporariamente como stava no stub
                return False

            def executar_def_presc():
                try:
                    from PEC.prescricao import def_presc as def_presc_func
                    return def_presc_func(driver, numero_processo, texto, data_decisao_str, debug=debug)
                except Exception: return False

            def executar_ato_prov():
                try:
                    res_fimsob = mov_fimsob(driver, debug=debug)
                    if not res_fimsob: return False
                    res_prov = ato_prov(driver, debug=debug)
                    return True if res_prov else False
                except Exception: return False

            regras_def_sob = [
                (['retorno do feito principal'], executar_mov_sob_retorno_feito, 'Retorno do feito principal'),
                (['penhora no rosto'], executar_penhora_rosto, 'Penhora no rosto'),
                (['precatório', 'RPV', 'pequeno valor'], executar_mov_sob_precatorio, 'Precatório/RPV/Pequeno valor'),
                (['juízo universal'], executar_juizo_universal, 'Juízo universal'),
                (['prazo prescricional'], executar_def_presc, 'Prazo prescricional'),
                (['autos principais', 'processo principal'], executar_ato_prov, 'Autos principais'),
            ]
            
            # Aplicar regras
            regra_com_sucesso = False
            for termos, acao_func, descricao in regras_def_sob:
                for termo in termos:
                    regex = gerar_regex_geral(termo)
                    if regex.search(texto_normalizado):
                        logger.info(f"[DEF_SOB] ✓ Regra encontrada: {descricao} (termo: '{termo}') no doc {doc_link.text}")
                        resultado = acao_func()
                        if resultado:
                            logger.info(f"[DEF_SOB] ✅ Regra '{descricao}' executada com sucesso")
                            return True
                        else:
                            logger.error(f"[DEF_SOB] ❌ Falha na regra '{descricao}'")
                            regra_com_sucesso = True 
                        break
                if regra_com_sucesso:
                    break
            
            if regra_com_sucesso:
                # Se achou a regra e falhou ao executar, consideramos que as mais antigas não devem sobreeescrever o status
                logger.warning(f"[DEF_SOB] Regra encontrada no doc '{doc_link.text}' mas falhou na execução.")
                return False
                
            log_msg(" Nenhuma regra aplicada neste documento, tentando a próxima decisão na timeline...")
        
        # Fim do loop, Nenhuma regra aplicável a NENHUM documento
        logger.warning(f"[DEF_SOB] ⚠️ Nenhuma decisão na timeline validou as regras de sobrestamento para {numero_processo}. Encaminhando para verificação manual.")
        return True
        
    except Exception as e:
        logger.error(f"[DEF_SOB] ❌ Erro geral em def_sob ({numero_processo}): {e}")
        import traceback
        logger.exception("Erro detectado em def_sob")
        return False
