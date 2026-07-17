"""
PEC.anexos.juntador.helpers - Helpers de decomposicao para juntada.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contem helpers para executar_juntada_ate_editor e substituir_marcador_por_conteudo.
"""

from Fix.log import logger

import os
import re
import time
import types
from typing import Optional, Dict, Any, Callable, Union, List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Imports do Fix
from Fix.core import (
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    safe_click,
    wait_for_clickable,
    wait_for_visible,
)
from Fix.utils import (
    inserir_html_no_editor_apos_marcador,
    obter_ultimo_conteudo_clipboard,
    executar_coleta_parametrizavel,
    inserir_link_ato_validacao,
    substituir_marcador_por_conteudo,
)


def _abrir_interface_anexacao(self: types.SimpleNamespace) -> bool:
    """Abre a interface de anexacao de documentos."""
    driver = self.driver
    logger.debug('[JUNTADA] Abrindo interface de anexacao...')

    # 1. Clique no menu (icone hamburguer)
    logger.debug('[JUNTADA] Clicando no menu hamburguer...')
    if not aguardar_e_clicar(driver, 'i[class*="fa-bars"].icone-botao-menu', 'Menu hamburguer'):
        return False
    time.sleep(1)

    # 2. Clique em "Anexar Documentos"
    logger.debug('[JUNTADA] Clicando em "Anexar documentos"...')
    if not aguardar_e_clicar(driver, 'button[aria-label="Anexar Documentos"]', 'Anexar documentos'):
        return False
    time.sleep(2)

    # 3. Aguarda nova aba/janela e muda para ela
    logger.debug('[JUNTADA] Mudando para aba de anexacao...')
    all_windows = driver.window_handles
    if len(all_windows) > 1:
        driver.switch_to.window(all_windows[-1])
        # CORRECAO: esperar_url_conter em vez de wait_for_visible(..., 'String') que causava erro de float
        from Fix.core import esperar_url_conter
        if not esperar_url_conter(driver, '/anexar', timeout=10):
            logger.warning('[JUNTADA] URL nao contem /anexar, mas prosseguindo...')
    else:
        logger.debug('[JUNTADA] Nova aba nao detectada, prosseguindo na mesma aba...')

    time.sleep(1) # Reduzido de 3s para 1s
    return True


def _preencher_campos_basicos(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool:
    """Preenche os campos basicos: tipo, descricao e sigilo."""
    driver = self.driver
    # Tipo de Documento
    tipo = configuracao.get('tipo', 'Certidao')
    if not selecionar_opcao(driver, 'input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento'):
        return False

    # Descricao
    descricao = configuracao.get('descricao', '')
    if descricao:
        if not preencher_campo(driver, 'input[aria-label="Descricao"]', descricao, 'Descricao'):
            return False

    # Sigilo
    sigilo = configuracao.get('sigilo', 'nao').lower()
    if 'sim' in sigilo:
        if not aguardar_e_clicar(driver, 'input[name="sigiloso"]', 'Sigilo'):
            return False

    return True


def _inserir_modelo(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool:
    """Insere o modelo no editor e verifica se foi carregado."""
    driver = self.driver
    modelo_original = configuracao.get('modelo', '')
    if modelo_original:
        logger.debug('[JUNTADA] Selecionando e inserindo modelo: %s', modelo_original)
        if not self._selecionar_modelo_gigs(modelo_original):
            return False
        logger.debug('[JUNTADA] Aguardando modelo ser inserido no editor...')
        time.sleep(3)

    logger.debug('[JUNTADA] Verificando se editor esta disponivel apos insercao do modelo...')

    seletores_editor = [
        'div[aria-label="Conteudo principal. Alt+F10 para acessar a barra de tarefas"].area-conteudo.ck.ck-content.ck-editor__editable',
        '.area-conteudo.ck.ck-content.ck-editor__editable.ck-rounded-corners.ck-editor__editable_inline',
        '.area-conteudo.ck-editor__editable[contenteditable="true"]',
        '.ck-editor__editable[contenteditable="true"]',
        'div.fr-element[contenteditable="true"]',
        '[contenteditable="true"]'
    ]

    editor_encontrado = None
    for i, seletor in enumerate(seletores_editor):
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
            logger.debug('[JUNTADA] Seletor %s "%s": %s elementos', i+1, seletor, len(elementos))
            if elementos:
                editor_encontrado = elementos[0]
                logger.debug('[JUNTADA] Editor encontrado com seletor: %s', seletor)
                logger.debug('[JUNTADA] Editor visivel: %s', editor_encontrado.is_displayed())
                logger.debug('[JUNTADA] Editor habilitado: %s', editor_encontrado.is_enabled())
                conteudo = editor_encontrado.get_attribute('innerHTML')
                logger.debug('[JUNTADA] Conteudo do editor (primeiros 200 chars): %s...', conteudo[:200])
                if 'marker-yellow' in conteudo and 'link' in conteudo:
                    logger.debug('[JUNTADA] Editor contem termo "link" marcado em amarelo')
                elif conteudo.strip() and len(conteudo) > 100:
                    logger.debug('[JUNTADA] Editor contem conteudo do modelo inserido')
                else:
                    logger.warning('[JUNTADA] Editor parece vazio - modelo pode nao ter sido inserido')
                break
        except Exception as e:
            logger.debug('[JUNTADA] Erro com seletor %s: %s', i+1, e)
            continue

    if not editor_encontrado:
        logger.error("ERRO em _inserir_modelo: Nenhum editor encontrado com os seletores disponiveis")
        return False

    logger.debug('[JUNTADA] Editor disponivel para manipulacao')
    return True
