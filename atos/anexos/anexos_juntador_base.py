"""atos.anexos.juntador.base - Funções base de juntada automática."""

import logging
logger = logging.getLogger(__name__)

import os
import re
import types
from typing import Optional, Dict, Any, Callable, Union, List
from Fix import espera

from Fix.core import (
    aguardar_e_clicar,
    aguardar_renderizacao_nativa,
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
    driver: Any,
    tipo: str = 'Certidão',
    descricao: Optional[str] = None,
    sigilo: str = 'nao',
    modelo: Optional[str] = None,
    inserir_conteudo: Optional[Callable[[Any, Optional[str], bool], bool]] = None,
    assinar: str = 'nao',
    coleta_conteudo: Optional[str] = None,
    substituir_link: bool = False,
    debug: bool = True,
    fechar_aba_apos: bool = True
) -> bool:
    """Wrapper geral para juntada automática, sequencial e parametrizado, inspirado em ato_judicial de atos.py."""
    if not driver:
        if debug:
            logger.error('[WRAPPER_JUNTADA_GERAL] Driver inválido')
        return False

    try:
        aba_original = driver.current_window_handle
    except Exception:
        aba_original = None

    if debug:
        logger.info('[WRAPPER_JUNTADA_GERAL] Iniciando juntada automática...')

    if coleta_conteudo:
        try:
            numero_processo = extrair_numero_processo_da_url(driver)
            if numero_processo:
                logger.info(f'[WRAPPER_JUNTADA_GERAL][COLETA] Iniciando coleta: {coleta_conteudo} | processo: {numero_processo}')
                executar_coleta_parametrizavel(driver, numero_processo, coleta_conteudo, debug=debug)
            else:
                if debug:
                    logger.warning('[WRAPPER_JUNTADA_GERAL][COLETA][WARN] Número do processo não identificado')
        except Exception as e:
            if debug:
                logger.warning(f'[WRAPPER_JUNTADA_GERAL][COLETA][WARN] Falha ao executar coleta opcional: {e}')

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
    resultado = False
    if hasattr(juntador, 'executar_juntada'):
        resultado = juntador.executar_juntada(configuracao, substituir_link=substituir_link)
    else:
        if debug:
            logger.error('[WRAPPER_JUNTADA_GERAL][ERRO] Objeto juntador não possui método executar_juntada')
        return False

    if resultado and fechar_aba_apos and aba_original:
        try:
            from Fix.abas import forcar_fechamento_abas_extras
            forcar_fechamento_abas_extras(driver, aba_original)
            if debug:
                logger.info('[WRAPPER_JUNTADA_GERAL] Aba de anexação fechada, retornando à aba original')
        except Exception as e:
            if debug:
                logger.warning('[WRAPPER_JUNTADA_GERAL] Erro ao fechar aba de anexação: %s', e)
    elif not resultado and aba_original:
        try:
            from Fix.abas import forcar_fechamento_abas_extras
            forcar_fechamento_abas_extras(driver, aba_original)
            if debug:
                logger.info('[WRAPPER_JUNTADA_GERAL] Aba de anexação fechada após falha, foco restaurado na aba original')
        except Exception as e:
            if debug:
                logger.warning('[WRAPPER_JUNTADA_GERAL] Erro ao restaurar aba original: %s', e)

    if resultado:
        if debug:
            logger.info('[WRAPPER_JUNTADA_GERAL] Juntada automática concluída com sucesso!')
    else:
        if debug:
            logger.warning('[WRAPPER_JUNTADA_GERAL] Juntada automática falhou ou foi pulada')
    return resultado


def make_juntada_wrapper(
    tipo: str = 'Certidao',
    descricao: Optional[str] = None,
    sigilo: str = 'nao',
    modelo: Optional[str] = None,
    assinar: str = 'nao',
    inserir_conteudo: Optional[Callable[[Any, Optional[str], bool], bool]] = None,
    coleta_conteudo: Optional[str] = None,
    **extra: Any
) -> Callable[..., bool]:
    """Factory que cria wrappers de juntada com parametros pre-definidos."""
    def wrapper(driver: Any, numero_processo: Optional[str] = None, debug: bool = True, **overrides: Any) -> bool:
        params = {
            'tipo': tipo,
            'descricao': descricao,
            'sigilo': sigilo,
            'modelo': modelo,
            'assinar': assinar,
            'inserir_conteudo': inserir_conteudo,
            'coleta_conteudo': coleta_conteudo,
        }
        params.update(overrides)
        return wrapper_juntada_geral(driver=driver, debug=debug, **params)

    modelo_part = modelo.lower().replace(' ', '_') if modelo else 'sem_modelo'
    wrapper.__name__ = f'juntada_{tipo.lower()}_{modelo_part}'
    return wrapper


def create_juntador(driver: Any) -> Any:
    """Cria um objeto simples com driver e métodos vinculados aos helpers existentes."""
    ns = types.SimpleNamespace(driver=driver)
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
    ns.executar_juntada_ate_editor = types.MethodType(executar_juntada_ate_editor, ns)
    try:
        ns.executar_juntada = types.MethodType(globals().get('executar_juntada'), ns)
    except Exception:
        pass
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
    """Executa a juntada até o ponto em que o editor está disponível e o modelo foi inserido,"""
    if not self or not hasattr(self, 'driver') or not self.driver:
        return False

    if not configuracao:
        return False

    driver = self.driver
    modelo = configuracao.get('modelo', '').strip().upper()

    if modelo == 'PDF':
        logger.error('[JUNTADA][ERRO] Não faz sentido juntar PDF nesse fluxo!')
        return False

    try:
        if not self._abrir_interface_anexacao():
            return False

        if not self._preencher_campos_basicos(configuracao):
            return False

        if not self._inserir_modelo(configuracao):
            return False

        return True

    except Exception as e:
        logger.error(f'[JUNTADA][ERRO] Erro ao executar juntada até o editor: {e}')
        return False


def executar_juntada(self, configuracao: Dict[str, Any], substituir_link: bool = False) -> bool:
    """Orquestra juntada automatica de anexos COM auto-navegacao."""
    if not self or not hasattr(self, 'driver') or not self.driver:
        return False

    if not configuracao:
        return False

    driver = self.driver

    try:
        logger.info('[JUNTADA] entrada na juntada: url=%s', (getattr(driver, 'current_url', '') or ''))
        em_anexar = '/anexar' in (driver.current_url or '')
        tem_campo = bool(espera.elementos(driver, 'input[aria-label="Tipo de Documento"]', teto=0.2))
        if not (em_anexar and tem_campo):
            if not self._abrir_interface_anexacao():
                logger.error('[JUNTADA][ERRO] Falha ao abrir interface de anexação (url=%s)',
                             (getattr(driver, 'current_url', '') or ''))
                return False
        espera.ate_sumir(driver, 'mat-progress-bar, mat-progress-spinner, pje-dialogo-status-progresso', teto=10)
        if not espera.ate_habilitar(driver, 'input[aria-label="Tipo de Documento"]', teto=5):
            logger.warning('[JUNTADA] Campo "Tipo de Documento" não habilitou em 5s (url=%s)',
                           (getattr(driver, 'current_url', '') or ''))
    except Exception as e:
        logger.error(f'[JUNTADA][ERRO] Erro ao garantir interface de anexacao: {e}')
        return False

    if not self._executar_coleta_opcional(configuracao):
        return False

    if not self._preencher_tipo(configuracao):
        return False

    if not self._preencher_descricao(configuracao):
        return False

    # 4. Configurar sigilo
    if not self._configurar_sigilo(configuracao):
        return False

    if not self._selecionar_e_inserir_modelo(configuracao):
        return False

    if not self._inserir_conteudo_customizado(configuracao, substituir_link):
        return False

    if not self._salvar_documento():
        return False

    if not self._assinar_se_necessario(configuracao):
        return False

    return True


def wrapper_juntada_com_navegacao(
    driver: Any,
    tipo: str = 'Certidao',
    descricao: Optional[str] = None,
    sigilo: str = 'nao',
    modelo: Optional[str] = None,
    inserir_conteudo: Optional[Callable[[Any, Optional[str], bool], bool]] = None,
    assinar: str = 'nao',
    coleta_conteudo: Optional[str] = None,
    substituir_link: bool = False,
    debug: bool = True,
    fechar_aba_apos: bool = True
) -> bool:
    """Wrapper completo de juntada COM navegacao."""
    if not driver:
        if debug:
            logger.error('[JUNTADA_COMPLETA] Driver invalido')
        return False

    try:
        aba_original = driver.current_window_handle
    except Exception:
        aba_original = None

    if debug:
        logger.info('[JUNTADA_COMPLETA] Iniciando juntada com navegacao...')

    juntador_nav = create_juntador(driver)
    if not juntador_nav._abrir_interface_anexacao():
        if debug:
            logger.error('[JUNTADA_COMPLETA] Falha ao abrir interface de anexacao')
        return False

    resultado = wrapper_juntada_geral(
        driver=driver,
        tipo=tipo,
        descricao=descricao,
        sigilo=sigilo,
        modelo=modelo,
        inserir_conteudo=inserir_conteudo,
        assinar=assinar,
        coleta_conteudo=coleta_conteudo,
        substituir_link=substituir_link,
        debug=debug,
        fechar_aba_apos=False,
    )

    if fechar_aba_apos and aba_original:
        try:
            from Fix.abas import forcar_fechamento_abas_extras
            forcar_fechamento_abas_extras(driver, aba_original)
            if debug:
                logger.info('[JUNTADA_COMPLETA] Aba de anexacao fechada, retornando a aba original')
        except Exception as e:
            if debug:
                logger.warning('[JUNTADA_COMPLETA] Erro ao fechar aba de anexacao: %s', e)

    return resultado
