import logging
logger = logging.getLogger(__name__)

import time
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from Fix.core import preencher_campo


def navegar_para_atividades(driver):
    """Navega para a tela de atividades do GIGS através da URL direta."""
    try:
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        driver.get(url_atividades)
        time.sleep(3)

        if 'atividades' in driver.current_url:
            return True

        logger.error(f"[NAVEGAR]  Erro: URL atual é {driver.current_url}")
        return False

    except Exception as e:
        logger.error(f"[NAVEGAR] Erro ao navegar para atividades: {e}")
        return False


def aplicar_filtro_xs(driver):
    """Aplica filtro 'xs' no campo Descrição da Atividade do GIGS."""
    try:
        from Fix import esperar_elemento
        import time

        # Buscar campo de descrição usando aria-label ou data-placeholder
        seletores = [
            'input[aria-label="Descrição da Atividade"]',
            'input[data-placeholder="Descrição da Atividade"]',
            'input#mat-input-3'  # ID específico caso os outros falhem
        ]
        
        campo_descricao = None
        for seletor in seletores:
            campo_descricao = esperar_elemento(driver, seletor, timeout=10)
            if campo_descricao:
                logger.info(f"[FILTRO_XS]  Campo encontrado com seletor: {seletor}")
                break
        
        if not campo_descricao:
            logger.error("[FILTRO_XS]  Campo de descrição não encontrado")
            return False

        # Limpar campo e digitar 'xs'
        campo_descricao.clear()
        time.sleep(0.5)
        campo_descricao.send_keys('xs')
        time.sleep(0.5)
        
        # Pressionar Enter para aplicar filtro
        campo_descricao.send_keys(Keys.ENTER)
        logger.info("[FILTRO_XS]  Filtro 'xs' aplicado, aguardando recarga...")
        
        # Aguardar recarga da tabela
        time.sleep(3)
        
        return True

    except Exception as e:
        logger.error(f"[FILTRO_XS]  Erro ao aplicar filtro: {e}")
        return False


def indexar_processo_atual_gigs(driver):
    """
    Extrai número do processo e observação da página atual de atividades GIGS.
    Assume que já está na página de detalhes do processo.
    """
    try:
        url_atual = driver.current_url
        numero_processo = None
        if "processo" in url_atual:
            match_url = re.search(r'processo/(\d+)', url_atual)
            if match_url:
                numero_processo = match_url.group(1)

        try:
            candidatos = driver.find_elements(
                By.CSS_SELECTOR,
                'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho',
            )
            for elemento in candidatos:
                texto = elemento.text.strip()
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                if match:
                    numero_processo = match.group(1)
                    break

            if not numero_processo:
                numero_processo = f"PROC_{hash(url_atual) % 1000000}"

        except Exception as e:
            logger.error(f"[INDEXAR_GIGS]  Erro ao buscar número na página: {e}")
            numero_processo = "UNKNOWN"

        observacao = ""
        try:
            elementos_descricao = driver.find_elements(By.CSS_SELECTOR, 'span.descricao')
            for elemento in elementos_descricao:
                try:
                    texto_completo = elemento.text.strip()
                    if texto_completo.startswith('Prazo:'):
                        observacao = texto_completo[6:].strip().lower()
                        observacao = observacao.rstrip('.')
                        break
                except Exception as e:
                    logger.error(f"[INDEXAR_GIGS] Erro ao processar elemento descricao: {e}")
                    continue

            if not observacao:
                texto_pagina = driver.page_source.lower()
                padroes_conhecidos = [
                    'xs carta',
                    'xs pec cp',
                    'xs pec edital',
                    'xs bloq',
                    'sob chip',
                    'sobrestamento vencido',
                ]
                for padrao in padroes_conhecidos:
                    if padrao in texto_pagina:
                        observacao = padrao
                        break

                if not observacao:
                    observacao = "observacao nao encontrada"

        except Exception as e:
            logger.error(f"[INDEXAR_GIGS]  Erro ao buscar observação: {e}")
            observacao = "erro ao extrair observacao"

        return (numero_processo, observacao)

    except Exception as e:
        logger.error(f"[INDEXAR_GIGS]  Erro geral ao indexar processo atual: {e}")
        return None
