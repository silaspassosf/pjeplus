"""
PEC.anexos.juntador.base - Funções base de juntada automática.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém wrapper_juntada_geral, create_juntador e executar_juntada_ate_editor.
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
)

# Imports dos módulos refatorados
from .anexos_extracao import extrair_numero_processo_da_url
from .anexos_formatacao import formatar_conteudo_ecarta
from .anexos_juntador_metodos import (
    _escolher_opcao_gigs,
    _preencher_input_gigs,
    _clicar_elemento_gigs,
    _selecionar_modelo_gigs,
    _executar_coleta_opcional,
    _preencher_tipo,
    _preencher_descricao,
    _configurar_sigilo,
    _selecionar_e_inserir_modelo,
    _inserir_conteudo_customizado,
    _salvar_documento,
    _assinar_se_necessario,
)
from .anexos_juntador_helpers import (
    _abrir_interface_anexacao,
    _preencher_campos_basicos,
    _inserir_modelo,
)


def wrapper_juntada_geral(
    driver: WebDriver,
    tipo: str = 'Certidão',
    descricao: Optional[str] = None,
    sigilo: str = 'nao',
    modelo: Optional[str] = None,
    inserir_conteudo: Optional[Callable[[WebDriver, Optional[str], bool], bool]] = None,
    assinar: str = 'nao',
    coleta_conteudo: Optional[str] = None,
    substituir_link: bool = False,
    debug: bool = True
) -> bool:
    """
    Wrapper geral para juntada automática, sequencial e parametrizado, inspirado em ato_judicial de atos.py.
    Permite criar wrappers específicos apenas repassando os parâmetros desejados.
    """
    # Guard clause: validar driver
    if not driver:
        if debug:
            print('[WRAPPER_JUNTADA_GERAL] ✗ Driver inválido')
        return False

    if debug:
        print('[WRAPPER_JUNTADA_GERAL] Iniciando juntada automática...')

    # 0. Coleta de conteúdo (opcional)
    if coleta_conteudo:
        try:
            numero_processo = extrair_numero_processo_da_url(driver)
            if numero_processo:
                print(f'[WRAPPER_JUNTADA_GERAL][COLETA] Iniciando coleta: {coleta_conteudo} | processo: {numero_processo}')
                executar_coleta_parametrizavel(driver, numero_processo, coleta_conteudo, debug=debug)
            else:
                if debug:
                    print('[WRAPPER_JUNTADA_GERAL][COLETA][WARN] Número do processo não identificado')
        except Exception as e:
            if debug:
                print(f'[WRAPPER_JUNTADA_GERAL][COLETA][WARN] Falha ao executar coleta opcional: {e}')

    # 1. Cria juntador
    juntador = create_juntador(driver)
    configuracao = {
        'tipo': tipo,
        'descricao': descricao if descricao else 'Juntada automática',
        'sigilo': sigilo,
        'modelo': modelo,
        'inserir_conteudo': inserir_conteudo,
        'assinar': assinar,
        'coleta_conteudo': coleta_conteudo,
    }
    # 2. Executa juntada principal
    resultado = False
    if hasattr(juntador, 'executar_juntada'):
        resultado = juntador.executar_juntada(configuracao, substituir_link=substituir_link)
    else:
        if debug:
            print('[WRAPPER_JUNTADA_GERAL][ERRO] Objeto juntador não possui método executar_juntada')
        return False

    if resultado:
        if debug:
            print('[WRAPPER_JUNTADA_GERAL] ✓ Juntada automática concluída com sucesso!')
    else:
        if debug:
            print('[WRAPPER_JUNTADA_GERAL] ✗ Juntada automática falhou ou foi pulada')
    return resultado


def create_juntador(driver: WebDriver) -> Any:
    """Cria um objeto simples com driver e métodos vinculados aos helpers existentes."""
    ns = types.SimpleNamespace(driver=driver)
    # Bind helpers
    try:
        ns._escolher_opcao_gigs = types.MethodType(globals().get('_escolher_opcao_gigs'), ns)
    except Exception:
        pass
    try:
        ns._preencher_input_gigs = types.MethodType(globals().get('_preencher_input_gigs'), ns)
    except Exception:
        pass
    try:
        ns._clicar_elemento_gigs = types.MethodType(globals().get('_clicar_elemento_gigs'), ns)
    except Exception:
        pass
    try:
        ns._selecionar_modelo_gigs = types.MethodType(globals().get('_selecionar_modelo_gigs'), ns)
    except Exception:
        pass
    # Bind flows
    ns.executar_juntada_ate_editor = types.MethodType(executar_juntada_ate_editor, ns)
    try:
        ns.executar_juntada = types.MethodType(globals().get('executar_juntada'), ns)
    except Exception:
        pass
    # Bind decomposed helpers for executar_juntada
    try:
        ns._executar_coleta_opcional = types.MethodType(globals().get('_executar_coleta_opcional'), ns)
    except Exception:
        pass
    try:
        ns._preencher_tipo = types.MethodType(globals().get('_preencher_tipo'), ns)
    except Exception:
        pass
    try:
        ns._preencher_descricao = types.MethodType(globals().get('_preencher_descricao'), ns)
    except Exception:
        pass
    try:
        ns._configurar_sigilo = types.MethodType(globals().get('_configurar_sigilo'), ns)
    except Exception:
        pass
    try:
        ns._selecionar_e_inserir_modelo = types.MethodType(globals().get('_selecionar_e_inserir_modelo'), ns)
    except Exception:
        pass
    try:
        ns._inserir_conteudo_customizado = types.MethodType(globals().get('_inserir_conteudo_customizado'), ns)
    except Exception:
        pass
    try:
        ns._salvar_documento = types.MethodType(globals().get('_salvar_documento'), ns)
    except Exception:
        pass
    try:
        ns._assinar_se_necessario = types.MethodType(globals().get('_assinar_se_necessario'), ns)
    except Exception:
        pass
    # Bind decomposed helpers for executar_juntada_ate_editor
    try:
        ns._abrir_interface_anexacao = types.MethodType(globals().get('_abrir_interface_anexacao'), ns)
    except Exception:
        pass
    try:
        ns._preencher_campos_basicos = types.MethodType(globals().get('_preencher_campos_basicos'), ns)
    except Exception:
        pass
    try:
        ns._inserir_modelo = types.MethodType(globals().get('_inserir_modelo'), ns)
    except Exception:
        pass
    return ns


def executar_juntada_ate_editor(self, configuracao: Dict[str, Any]) -> bool:
    """
    Executa a juntada até o ponto em que o editor está disponível e o modelo foi inserido,
    mas NÃO clica em Salvar. Retorna True se sucesso, False se falha.

    Orquestra: validação → abrir interface → preencher campos → inserir modelo
    """
    # Guard clause: validar parâmetros
    if not self or not hasattr(self, 'driver') or not self.driver:
        return False

    if not configuracao:
        return False

    driver = self.driver
    modelo = configuracao.get('modelo', '').strip().upper()

    # Guard clause: validar modelo
    if modelo == 'PDF':
        logger.error('[JUNTADA][ERRO] Não faz sentido juntar PDF nesse fluxo!')
        return False

    try:
        # 1. Abrir interface de anexação
        if not self._abrir_interface_anexacao():
            return False

        # 2. Preencher campos básicos
        if not self._preencher_campos_basicos(configuracao):
            return False

        # 3. Inserir modelo e verificar editor
        if not self._inserir_modelo(configuracao):
            return False

        return True

    except Exception as e:
        logger.error(f'[JUNTADA][ERRO] Erro ao executar juntada até o editor: {e}')
        return False


def executar_juntada(self, configuracao: Dict[str, Any], substituir_link: bool = False) -> bool:
    """
    Orquestra juntada automática de anexos.

    Fluxo: validação → coleta → tipo → descrição → sigilo → modelo → inserção → salvar → assinar
    """
    # Guard clause: validar parâmetros
    if not self or not hasattr(self, 'driver') or not self.driver:
        return False

    if not configuracao:
        return False

    driver = self.driver

    # 1. Coleta opcional
    if not self._executar_coleta_opcional(configuracao):
        return False

    # 2. Preencher tipo
    if not self._preencher_tipo(configuracao):
        return False

    # 3. Preencher descrição
    if not self._preencher_descricao(configuracao):
        return False

    # 4. Configurar sigilo
    if not self._configurar_sigilo(configuracao):
        return False

    # 5. Selecionar modelo
    if not self._selecionar_e_inserir_modelo(configuracao):
        return False

    # 6. Inserir conteúdo customizado
    if not self._inserir_conteudo_customizado(configuracao, substituir_link):
        return False

    # 7. Salvar documento
    if not self._salvar_documento():
        return False

    # 8. Assinar se necessário
    if not self._assinar_se_necessario(configuracao):
        return False

    return True