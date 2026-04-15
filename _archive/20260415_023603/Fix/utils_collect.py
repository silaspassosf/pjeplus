import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_collect - Módulo de coleta de dados para PJe automação.

Parte da refatoração do Fix.utils.py para melhor granularidade IA.
"""

import re
from selenium.webdriver.common.by import By

def coletar_texto_seletor(driver, seletor, timeout=5):
    """Coleta texto de um elemento por seletor CSS"""
    try:
        from .extracao import esperar_elemento
        elemento = esperar_elemento(driver, seletor, timeout=timeout)
        if elemento:
            return elemento.text.strip()
        return ""
    except Exception as e:
        logger.error(f"Erro ao coletar texto do seletor {seletor}: {e}")
        return ""

def coletar_valor_atributo(driver, seletor, atributo, timeout=5):
    """Coleta valor de atributo de um elemento"""
    try:
        from .extracao import esperar_elemento
        elemento = esperar_elemento(driver, seletor, timeout=timeout)
        if elemento:
            return elemento.get_attribute(atributo) or ""
        return ""
    except Exception as e:
        logger.error(f"Erro ao coletar atributo {atributo} do seletor {seletor}: {e}")
        return ""

def coletar_multiplos_elementos(driver, seletor, timeout=5):
    """Coleta múltiplos elementos por seletor"""
    try:
        from .extracao import esperar_elementos
        elementos = esperar_elementos(driver, seletor, timeout=timeout)
        return elementos if elementos else []
    except Exception as e:
        logger.error(f"Erro ao coletar múltiplos elementos {seletor}: {e}")
        return []

def coletar_tabela_como_lista(driver, seletor_tabela, timeout=5):
    """Coleta dados de uma tabela HTML como lista de listas"""
    try:
        from .extracao import esperar_elemento
        tabela = esperar_elemento(driver, seletor_tabela, timeout=timeout)
        if not tabela:
            return []

        linhas = tabela.find_elements(By.TAG_NAME, 'tr')
        dados = []

        for linha in linhas:
            celulas = linha.find_elements(By.TAG_NAME, 'td')
            if not celulas:
                # Tentar th se não há td
                celulas = linha.find_elements(By.TAG_NAME, 'th')

            dados_linha = [celula.text.strip() for celula in celulas]
            if dados_linha:
                dados.append(dados_linha)

        return dados

    except Exception as e:
        logger.error(f"Erro ao coletar tabela {seletor_tabela}: {e}")
        return []

def coletar_links_pagina(driver):
    """Coleta todos os links da página atual"""
    try:
        links = driver.find_elements(By.TAG_NAME, 'a')
        dados_links = []

        for link in links:
            href = link.get_attribute('href')
            texto = link.text.strip()
            if href:
                dados_links.append({
                    'href': href,
                    'texto': texto
                })

        return dados_links

    except Exception as e:
        logger.error(f"Erro ao coletar links da página: {e}")
        return []

def coletar_dados_formulario(driver, seletor_form=None):
    """Coleta dados de um formulário"""
    try:
        if seletor_form:
            from .extracao import esperar_elemento
            form = esperar_elemento(driver, seletor_form)
        else:
            form = driver

        inputs = form.find_elements(By.TAG_NAME, 'input')
        selects = form.find_elements(By.TAG_NAME, 'select')
        textareas = form.find_elements(By.TAG_NAME, 'textarea')

        dados = {}

        # Inputs
        for input_elem in inputs:
            nome = input_elem.get_attribute('name') or input_elem.get_attribute('id')
            tipo = input_elem.get_attribute('type')
            valor = input_elem.get_attribute('value')
            if nome:
                dados[f"input_{nome}"] = {
                    'tipo': tipo,
                    'valor': valor
                }

        # Selects
        for select_elem in selects:
            nome = select_elem.get_attribute('name') or select_elem.get_attribute('id')
            if nome:
                opcoes = [opt.text for opt in select_elem.find_elements(By.TAG_NAME, 'option')]
                selecionado = select_elem.get_attribute('value')
                dados[f"select_{nome}"] = {
                    'opcoes': opcoes,
                    'selecionado': selecionado
                }

        # Textareas
        for textarea in textareas:
            nome = textarea.get_attribute('name') or textarea.get_attribute('id')
            if nome:
                dados[f"textarea_{nome}"] = textarea.text

        return dados

    except Exception as e:
        logger.error(f"Erro ao coletar dados do formulário: {e}")
        return {}

def extrair_numero_processo(texto):
    """Extrai número do processo de um texto"""
    if not texto:
        return ""

    # Padrões comuns de números de processo
    padroes = [
        r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}',  # 1234567-12.3456.7.12.3456
        r'\d{4,7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', # Variações
        r'\d{20,25}',  # Número sequencial longo
    ]

    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            return match.group()

    return ""

def extrair_cpf_cnpj(texto):
    """Extrai CPF ou CNPJ de um texto"""
    if not texto:
        return ""

    # CPF: 123.456.789-01
    cpf_match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', texto)
    if cpf_match:
        return cpf_match.group()

    # CNPJ: 12.345.678/0001-23
    cnpj_match = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', texto)
    if cnpj_match:
        return cnpj_match.group()

    # Apenas números
    cpf_nums = re.search(r'\d{11}', texto)
    if cpf_nums:
        return cpf_nums.group()

    cnpj_nums = re.search(r'\d{14}', texto)
    if cnpj_nums:
        return cnpj_nums.group()

    return ""

def coletar_dados_pagina(driver):
    """Coleta dados gerais da página atual"""
    try:
        dados = {
            'url': driver.current_url,
            'titulo': driver.title,
            'numero_processo': extrair_numero_processo(driver.page_source),
            'cpf_cnpj': extrair_cpf_cnpj(driver.page_source),
        }

        # Tentar coletar alguns elementos comuns
        dados.update({
            'numero_processo_header': coletar_texto_seletor(driver, 'h1, h2, h3'),
            'status_processo': coletar_texto_seletor(driver, '.status, .situacao'),
        })

        return dados

    except Exception as e:
        logger.error(f"Erro ao coletar dados da página: {e}")
        return {}