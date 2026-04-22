"""
judicial_bloqueios.py - Funções de verificação de bloqueios

"""

from Fix.core import logger
from Fix.exceptions import ElementoNaoEncontradoError, NavegacaoError

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import re

from datetime import datetime, timedelta





def verificar_bloqueio_recente(driver, debug=False):

    """

    Verifica se existe lembrete de bloqueio com data não superior a 100 dias.

    Versão simplificada baseada na função original.

    

    Returns:

        bool: True se encontrou bloqueio recente, False caso contrário

    """

    try:

        if debug:

            logger.info('[IDPJ][BLOQUEIO] Buscando seção de lembretes...')

        

        # Procurar pela seção de lembretes (post-it-set)

        try:

            lembretes_section = WebDriverWait(driver, 10).until(

                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.post-it-set'))

            )

        except (TimeoutException, NoSuchElementException):

            if debug:

                logger.info('[IDPJ][BLOQUEIO]  Seção de lembretes não encontrada')

            return False

        except Exception as e:

            if debug:

                logger.info(f'[IDPJ][BLOQUEIO]  Erro ao buscar seção de lembretes: {e}')

            raise ElementoNaoEncontradoError('div.post-it-set', f'verificar_bloqueio_recente: {e}')

        

        # Encontrar todos os lembretes expandidos

        lembretes = lembretes_section.find_elements(By.CSS_SELECTOR, 'mat-expansion-panel.mat-expanded')

        

        if debug:

            logger.info(f'[IDPJ][BLOQUEIO] {len(lembretes)} lembrete(s) encontrado(s)')

        

        data_limite = datetime.now() - timedelta(days=100)

        

        for lembrete in lembretes:

            try:

                # Verificar título do lembrete

                titulo_element = lembrete.find_element(By.CSS_SELECTOR, 'mat-panel-title')

                titulo = titulo_element.text.strip().lower()

                

                # Verificar conteúdo do lembrete

                conteudo_element = lembrete.find_element(By.CSS_SELECTOR, 'div.post-it-conteudo')

                conteudo = conteudo_element.text.strip().lower()

                

                if debug:

                    logger.info(f'[IDPJ][BLOQUEIO] Analisando - Título: "{titulo}" | Conteúdo: "{conteudo[:50]}..."')

                

                # Verificar se é um lembrete de bloqueio

                if ('bloq' in titulo or 'bloq' in conteudo or 

                    'bloqueio' in titulo or 'bloqueio' in conteudo):

                    

                    if debug:

                        logger.info('[IDPJ][BLOQUEIO]  Lembrete de bloqueio encontrado - verificando data...')

                    

                    # Extrair data do rodapé

                    try:

                        rodape = lembrete.find_element(By.CSS_SELECTOR, 'div.rodape-post-it-usuario span')

                        rodape_texto = rodape.text.strip()

                        

                        # Buscar padrão de data (formato DD/MM/AA HH:MM)

                        match_data = re.search(r'(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})', rodape_texto)

                        

                        if match_data:

                            data_str = match_data.group(1)

                            # Converter para formato completo (assumindo 20XX)

                            dia, mes, ano = data_str.split('/')

                            ano_completo = f"20{ano}"

                            

                            data_lembrete = datetime.strptime(f"{dia}/{mes}/{ano_completo}", "%d/%m/%Y")

                            

                            if debug:

                                logger.info(f'[IDPJ][BLOQUEIO] Data do lembrete: {data_lembrete.strftime("%d/%m/%Y")}')

                                logger.info(f'[IDPJ][BLOQUEIO] Data limite (100 dias): {data_limite.strftime("%d/%m/%Y")}')

                            

                            # Verificar se a data é dentro dos últimos 100 dias

                            if data_lembrete >= data_limite:

                                if debug:

                                    logger.info('[IDPJ][BLOQUEIO]  Bloqueio recente (d" 100 dias) encontrado!')

                                return True

                            else:

                                if debug:

                                    logger.info('[IDPJ][BLOQUEIO]  Bloqueio antigo (> 100 dias)')

                        else:

                            if debug:

                                logger.info('[IDPJ][BLOQUEIO]  Não foi possível extrair data do lembrete')

                    

                    except Exception as e:

                        if debug:

                            logger.info(f'[IDPJ][BLOQUEIO]  Erro ao extrair data: {e}')

                        continue

                

            except Exception as e:

                if debug:

                    logger.info(f'[IDPJ][BLOQUEIO]  Erro ao analisar lembrete: {e}')

                continue

        

        if debug:

            logger.info('[IDPJ][BLOQUEIO]  Nenhum bloqueio recente encontrado')

        return False

        

    except Exception as e:

        if debug:

            logger.info(f'[IDPJ][BLOQUEIO]  Erro na verificação de bloqueio: {e}')

        raise NavegacaoError(f'verificar_bloqueio_recente: {e}')

