"""
PEC.anexos.juntador.helpers - Helpers de decomposição para juntada.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém helpers para executar_juntada_ate_editor e substituir_marcador_por_conteudo.
"""

import logging
logger = logging.getLogger(__name__)

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
    """Abre a interface de anexação de documentos."""
    driver = self.driver
    print('[JUNTADA][DEBUG] Abrindo interface de anexação...')

    # 1. Clique no menu (ícone hambúrguer)
    print('[JUNTADA][DEBUG] Clicando no menu hambúrguer...')
    if not aguardar_e_clicar(driver, 'i[class*="fa-bars"].icone-botao-menu', 'Menu hambúrguer'):
        return False
    time.sleep(1)

    # 2. Clique em "Anexar Documentos"
    print('[JUNTADA][DEBUG] Clicando em "Anexar documentos"...')
    if not aguardar_e_clicar(driver, 'button[aria-label="Anexar Documentos"]', 'Anexar documentos'):
        return False
    time.sleep(2)

    # 3. Aguarda nova aba/janela e muda para ela
    print('[JUNTADA][DEBUG] Mudando para aba de anexação...')
    all_windows = driver.window_handles
    if len(all_windows) > 1:
        driver.switch_to.window(all_windows[-1])
        # CORREÇÃO: esperar_url_conter em vez de wait_for_visible(..., 'String') que causava erro de float
        from Fix.core import esperar_url_conter
        if not esperar_url_conter(driver, '/anexar', timeout=10):
            print('[JUNTADA][AVISO] URL não contém /anexar, mas prosseguindo...')
    else:
        print('[JUNTADA][DEBUG] Nova aba não detectada, prosseguindo na mesma aba...')

    time.sleep(1) # Reduzido de 3s para 1s
    return True


def _preencher_campos_basicos(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool:
    """Preenche os campos básicos: tipo, descrição e sigilo."""
    driver = self.driver
    # Tipo de Documento
    tipo = configuracao.get('tipo', 'Certidão')
    if not selecionar_opcao(driver, 'input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento'):
        return False

    # Descrição
    descricao = configuracao.get('descricao', '')
    if descricao:
        if not preencher_campo(driver, 'input[aria-label="Descrição"]', descricao, 'Descrição'):
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
        print(f'[JUNTADA][DEBUG] Selecionando e inserindo modelo: {modelo_original}')
        if not self._selecionar_modelo_gigs(modelo_original):
            return False
        print('[JUNTADA][DEBUG] Aguardando modelo ser inserido no editor...')
        time.sleep(3)

    print('[JUNTADA][DEBUG] Verificando se editor está disponível após inserção do modelo...')

    seletores_editor = [
        'div[aria-label="Conteúdo principal. Alt+F10 para acessar a barra de tarefas"].area-conteudo.ck.ck-content.ck-editor__editable',
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
            print(f'[JUNTADA][DEBUG] Seletor {i+1} "{seletor}": {len(elementos)} elementos')
            if elementos:
                editor_encontrado = elementos[0]
                print(f'[JUNTADA][DEBUG] ✓ Editor encontrado com seletor: {seletor}')
                print(f'[JUNTADA][DEBUG] Editor visível: {editor_encontrado.is_displayed()}')
                print(f'[JUNTADA][DEBUG] Editor habilitado: {editor_encontrado.is_enabled()}')
                conteudo = editor_encontrado.get_attribute('innerHTML')
                print(f'[JUNTADA][DEBUG] Conteúdo do editor (primeiros 200 chars): {conteudo[:200]}...')
                if 'marker-yellow' in conteudo and 'link' in conteudo:
                    print('[JUNTADA][DEBUG] ✓ Editor contém termo "link" marcado em amarelo!')
                elif conteudo.strip() and len(conteudo) > 100:
                    print('[JUNTADA][DEBUG] ✓ Editor contém conteúdo do modelo inserido')
                else:
                    print('[JUNTADA][AVISO] Editor parece vazio - modelo pode não ter sido inserido')
                break
        except Exception as e:
            print(f'[JUNTADA][DEBUG] Erro com seletor {i+1}: {e}')
            continue

    if not editor_encontrado:
        print('[JUNTADA][ERRO] Nenhum editor encontrado com os seletores disponíveis!')
        return False

    print('[JUNTADA][DEBUG] ✓ Editor disponível para manipulação')
    return True


