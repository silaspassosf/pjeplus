"""Agregador da superficie publica e dos shims leves de compatibilidade do Fix.

Esta unidade concentra re-exports, aliases e implementacoes curtas que antes
estavam dispersas em ~15 arquivos separados (< 150 linhas cada). Os donos reais
da implementacao continuam em ``Fix.core``, ``Fix.extracao``, ``Fix.utils``,
``Fix.abas`` e ``Fix.monitoramento_progresso_unificado``.

Fontes consolidadas:
  - Fix.__init__, Fix.drivers/*, Fix.progress/*, Fix.scripts/__init__
  - Fix.element_wait, Fix.smart_finder, Fix.exceptions
  - Fix.documents, Fix.navigation, Fix.gigs
  - Fix.variaveis_client, Fix.variaveis_helpers, Fix.variaveis_resolvers
  - Fix.selectors_pje (parcial), Fix.movimento_helpers
"""

from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# =============================================================================
# CORE - Re-exports from Fix.core
# =============================================================================
from .core import (
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    preencher_campos_prazo,
    preencher_multiplos_campos,
    com_retry,
    buscar_seletor_robusto,
    esperar_elemento,
    esperar_url_conter,
    escolher_opcao_inteligente,
    encontrar_elemento_inteligente,
    safe_click,
    wait,
    wait_for_visible,
    wait_for_clickable,
    smart_sleep,
    sleep,
    criar_driver_PC,
    criar_driver_VT,
    criar_driver_pc,
    criar_driver_vt,
    criar_driver_notebook,
    criar_driver_sisb_pc,
    criar_driver_sisb_notebook,
    finalizar_driver,
    salvar_cookies_sessao,
    carregar_cookies_sessao,
    verificar_e_aplicar_cookies,
    aplicar_filtro_100,
    filtro_fase,
    verificar_documento_decisao_sentenca,
    visibilidade_sigilosos,
    buscar_ultimo_mandado,
    buscar_mandado_autor,
    buscar_documentos_sequenciais,
    buscar_documentos_polo_ativo,
    criar_botoes_detalhes,
    ErroCollector,
    js_base,
    buscar_documento_argos,
)

# =============================================================================
# EXTRACAO - Re-exports from Fix.extracao
# =============================================================================
from .extracao import (
    extrair_direto,
    extrair_documento,
    extrair_pdf,
    extrair_dados_processo,
    extrair_destinatarios_decisao,
    criar_gigs,
    criar_comentario,
    criar_lembrete_posit,
    bndt,
    filtrofases,
    indexar_processos,
    reindexar_linha,
    abrir_detalhes_processo,
    indexar_e_processar_lista,
    analise_argos,
    tratar_anexos_argos,
    analise_outros,
    salvar_destinatarios_cache,
    carregar_destinatarios_cache,
)

# =============================================================================
# UTILS - Re-exports from Fix.utils
# =============================================================================
from .utils import (
    formatar_moeda_brasileira,
    formatar_data_brasileira,
    normalizar_cpf_cnpj,
    limpar_temp_selenium,
    login_manual,
    login_automatico,
    login_automatico_direto,
    login_cpf,
    login_pc,
    coletar_link_ato_timeline,
    coletar_conteudo_js,
    coletar_elemento_css,
    executar_coleta_parametrizavel,
    inserir_html_editor,
    inserir_texto_editor,
    inserir_html_no_editor_apos_marcador,
    obter_ultimo_conteudo_clipboard,
    inserir_link_ato,
    inserir_link_ato_validacao,
    configurar_recovery_driver,
    verificar_e_tratar_acesso_negado_global,
    handle_exception_with_recovery,
    obter_driver_padronizado,
    driver_pc,
    navegar_para_tela,
    normalizar_texto,
)

# =============================================================================
# ABAS - Re-exports from Fix.abas (FX2 - browser/session support)
# =============================================================================
from .abas import (
    validar_conexao_driver,
    trocar_para_nova_aba,
    forcar_fechamento_abas_extras,
    is_browsing_context_discarded_error,
)

# =============================================================================
# PROGRESSO - Re-exports from Fix.monitoramento_progresso_unificado
# =============================================================================
from .monitoramento_progresso_unificado import (
    ProgressoUnificado,
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    executar_com_monitoramento_unificado,
    ARQUIVO_PROGRESSO_UNIFICADO,
)

# =============================================================================
# ERROR CLASSES
# =============================================================================

class PJePlusError(Exception):
    pass


class ElementoNaoEncontradoError(PJePlusError):
    pass


class NavegacaoError(PJePlusError):
    pass

# =============================================================================
# API CLIENT RE-EXPORTS (formerly Fix.variaveis_client / _helpers / _resolvers)
# =============================================================================
from api.variaveis_client import PjeApiClient, session_from_driver

from api.variaveis_helpers import (
    obter_gigs_com_fase,
    obter_texto_documento,
    buscar_atividade_gigs_por_observacao,
    obter_todas_atividades_gigs_com_observacao,
    padrao_liq,
    verificar_bndt,
)

from api.variaveis_resolvers import (
    obter_codigo_validacao_documento,
    obter_peca_processual_da_timeline,
    resolver_variavel,
    get_all_variables,
    obter_chave_ultimo_despacho_decisao_sentenca,
)

# =============================================================================
# SELECTORS PJe (formerly Fix.selectors_pje)
# =============================================================================

BTN_TAREFA_PROCESSO = 'button[mattooltip="Abre a tarefa do processo"]'

# buscar_seletor_robusto is re-exported from Fix.core above

# =============================================================================
# MOVIMENTO HELPERS (formerly Fix.movimento_helpers)
# =============================================================================

import re as _re
import time as _time


def _normalize_text(s: str) -> str:
    if not s:
        return ''
    s = normalizar_texto(s.strip())  # canonical from Fix.utils
    s = _re.sub(r'\s+', ' ', s)
    return s


def selecionar_movimento_dois_estagios(driver, movimento: str, timeout_select: int = 2) -> bool:
    """Seleciona movimentos em multiplos estagios (comboboxes / complementos).

    Uso: chamar esta funcao dentro de ``ato_judicial`` quando o parametro ``movimento``
    contem separadores (``/`` ou ``-``). A funcao tenta, em ordem:
      1) localizar ``mat-select`` dentro de ``pje-complemento`` e escolher
         ``mat-option`` que contenha o termo;
      2) preencher ``input`` ou ``textarea`` dentro do complemento correspondente;
      3) fallback: abrir qualquer ``mat-select`` visivel e buscar a opcao.

    Retorna True se todas as etapas (segmentos) do movimento foram satisfeitas,
    False caso contrario.
    """
    termos = [t.strip() for t in _re.split(r'[/\\-]', movimento) if t.strip()]
    if not termos:
        return False

    complementos = driver.find_elements(By.CSS_SELECTOR, 'pje-complemento')
    usados = set()

    for termo in termos:
        termo_norm = _normalize_text(termo)
        encontrado = False

        # 1) tenta mat-select dentro dos complementos
        for idx, comp in enumerate(complementos):
            if idx in usados:
                continue
            try:
                sel = comp.find_element(By.CSS_SELECTOR, 'mat-select')
                try:
                    driver.execute_script(
                        'arguments[0].parentElement.parentElement.click();', sel
                    )
                except Exception:
                    driver.execute_script('arguments[0].click();', sel)

                opts = WebDriverWait(driver, timeout_select).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "mat-option[role='option']")
                    )
                )
                for op in opts:
                    try:
                        if termo_norm in _normalize_text(op.text or ''):
                            driver.execute_script('arguments[0].click();', op)
                            usados.add(idx)
                            encontrado = True
                            break
                    except Exception:
                        continue
                if encontrado:
                    break
            except Exception:
                continue

        # 2) tentar input/textarea no complemento
        if not encontrado:
            for idx, comp in enumerate(complementos):
                if idx in usados:
                    continue
                try:
                    inp = comp.find_element(By.CSS_SELECTOR, 'input')
                    driver.execute_script(
                        "arguments[0].value = arguments[1]; "
                        "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));",
                        inp, termo,
                    )
                    usados.add(idx)
                    encontrado = True
                    break
                except Exception:
                    try:
                        ta = comp.find_element(By.CSS_SELECTOR, 'textarea')
                        driver.execute_script(
                            "arguments[0].value = arguments[1]; "
                            "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));",
                            ta, termo,
                        )
                        usados.add(idx)
                        encontrado = True
                        break
                    except Exception:
                        continue

        # 3) fallback: qualquer mat-select visivel na pagina
        if not encontrado:
            all_selects = driver.find_elements(By.CSS_SELECTOR, 'mat-select')
            for sel in all_selects:
                try:
                    try:
                        driver.execute_script(
                            'arguments[0].parentElement.parentElement.click();', sel
                        )
                    except Exception:
                        driver.execute_script('arguments[0].click();', sel)
                    opts = WebDriverWait(driver, 1).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "mat-option[role='option']")
                        )
                    )
                    for op in opts:
                        if termo_norm in _normalize_text(op.text or ''):
                            driver.execute_script('arguments[0].click();', op)
                            encontrado = True
                            break
                    if encontrado:
                        break
                except Exception:
                    continue

        if not encontrado:
            return False

        _time.sleep(0.2)

    return True


def selecionar_movimento_auto(driver, movimento: str) -> bool:
    """Chamada auxiliar: decide a estrategia e executa selecao.

    - se ``movimento`` contem ``/`` ou ``-`` -> usa
      ``selecionar_movimento_dois_estagios``
    - caso contrario retorna False para indicar que o chamador deve usar
      a logica por checkbox

    Retorna True se a selecao foi feita aqui, False se o chamador deve usar
    fluxo por checkbox.
    """
    if not movimento:
        return False
    if '/' in movimento or '-' in movimento:
        return selecionar_movimento_dois_estagios(driver, movimento)
    return False


# =============================================================================
# COMPATIBILITY SHIMS
# (legados de Fix.element_wait, Fix.smart_finder, Fix.progress, Fix.scripts)
# =============================================================================

_JS_CACHE: Dict[Tuple[str, str], str] = {}


class ElementWaitPool:
    """Pool minimo de waits consistente com os consumidores ativos."""

    def __init__(self, driver, explicit_wait: int = 10):
        self.driver = driver
        self.explicit_wait = explicit_wait

    def esperar_elemento(self, selector, timeout=None, by=By.CSS_SELECTOR):
        return WebDriverWait(self.driver, timeout or self.explicit_wait).until(
            EC.presence_of_element_located((by, selector))
        )

    def esperar_visivel(self, selector, timeout=None, by=By.CSS_SELECTOR):
        return WebDriverWait(self.driver, timeout or self.explicit_wait).until(
            EC.visibility_of_element_located((by, selector))
        )

    def esperar_clicavel(self, selector, timeout=None, by=By.CSS_SELECTOR):
        return WebDriverWait(self.driver, timeout or self.explicit_wait).until(
            EC.element_to_be_clickable((by, selector))
        )


def buscar(driver, cache_key, seletores):
    """Busca sequencial simples por CSS ou XPath.

    ``cache_key`` e mantido so por compatibilidade de assinatura.
    """
    _ = cache_key
    for seletor in seletores or []:
        try:
            by = (
                By.XPATH
                if isinstance(seletor, str) and seletor.startswith("//")
                else By.CSS_SELECTOR
            )
            elementos = driver.find_elements(by, seletor)
            for elemento in elementos:
                try:
                    if elemento.is_displayed():
                        return elemento
                except Exception:
                    continue
            if elementos:
                return elementos[0]
        except Exception:
            continue
    return None


def carregar_js(nome_arquivo: str, pasta: Optional[Union[str, Path]] = None) -> str:
    """Load a JS file from disk, with simple in-memory cache."""
    base_dir = Path(pasta) if pasta else Path(__file__).resolve().parent
    cache_key = (str(base_dir.resolve()), nome_arquivo)

    if cache_key in _JS_CACHE:
        return _JS_CACHE[cache_key]

    caminho = base_dir / nome_arquivo
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except Exception:
        return ""

    _JS_CACHE[cache_key] = conteudo
    return conteudo


def limpar_cache_js() -> None:
    """Clear JS file cache."""
    _JS_CACHE.clear()


def registrar_modulo(nome_modulo: str, total_items: int) -> None:
    """Compatibilidade legada: no-op."""
    _ = (nome_modulo, total_items)


def atualizar(
    nome_modulo: str,
    processados: int = None,
    item_atual: str = None,
    proximo_item: str = None,
    erro: bool = False,
) -> None:
    """Compatibilidade legada: no-op."""
    _ = (nome_modulo, processados, item_atual, proximo_item, erro)


def completar(nome_modulo: str, sucesso: bool = True) -> None:
    """Compatibilidade legada: no-op."""
    _ = (nome_modulo, sucesso)


# =============================================================================
# __all__  -  Todos os nomes publicos
# =============================================================================

__all__ = [
    # Core - Consolidadas
    'aguardar_e_clicar', 'selecionar_opcao', 'preencher_campo',
    'preencher_campos_prazo', 'preencher_multiplos_campos',
    # Core - Retry e robustez
    'com_retry', 'buscar_seletor_robusto', 'esperar_elemento',
    'esperar_url_conter', 'escolher_opcao_inteligente',
    'encontrar_elemento_inteligente',
    # Core - Legadas
    'safe_click', 'wait', 'wait_for_visible', 'wait_for_clickable',
    'smart_sleep', 'sleep',
    # Core - Drivers
    'criar_driver_PC', 'criar_driver_VT',
    'criar_driver_pc', 'criar_driver_vt',
    'criar_driver_notebook',
    'criar_driver_sisb_pc', 'criar_driver_sisb_notebook',
    'finalizar_driver',
    # Core - Cookies/Sessao
    'salvar_cookies_sessao', 'carregar_cookies_sessao',
    'verificar_e_aplicar_cookies',
    # Core - Filtros e navegacao
    'aplicar_filtro_100', 'filtro_fase',
    # Core - Documentos
    'verificar_documento_decisao_sentenca', 'visibilidade_sigilosos',
    'buscar_ultimo_mandado', 'buscar_mandado_autor',
    'buscar_documentos_sequenciais', 'buscar_documentos_polo_ativo',
    'criar_botoes_detalhes',
    # Core - Classes e JS
    'ErroCollector', 'js_base',
    # Extracao
    'extrair_direto', 'extrair_documento', 'extrair_pdf',
    'extrair_dados_processo', 'extrair_destinatarios_decisao',
    'criar_gigs', 'criar_comentario', 'criar_lembrete_posit',
    'bndt', 'filtrofases', 'indexar_processos', 'reindexar_linha',
    'abrir_detalhes_processo', 'indexar_e_processar_lista',
    'analise_argos', 'buscar_documento_argos', 'tratar_anexos_argos',
    'analise_outros', 'salvar_destinatarios_cache',
    'carregar_destinatarios_cache',
    # Utils
    'formatar_moeda_brasileira', 'formatar_data_brasileira',
    'normalizar_cpf_cnpj', 'limpar_temp_selenium',
    'login_manual', 'login_automatico', 'login_automatico_direto',
    'login_cpf', 'login_pc',
    'coletar_link_ato_timeline', 'coletar_conteudo_js',
    'coletar_elemento_css', 'executar_coleta_parametrizavel',
    'inserir_html_editor', 'inserir_texto_editor',
    'inserir_html_no_editor_apos_marcador',
    'obter_ultimo_conteudo_clipboard',
    'inserir_link_ato', 'inserir_link_ato_validacao',
    'configurar_recovery_driver',
    'verificar_e_tratar_acesso_negado_global',
    'handle_exception_with_recovery', 'obter_driver_padronizado',
    'driver_pc', 'navegar_para_tela',
    # Abas
    'validar_conexao_driver', 'trocar_para_nova_aba',
    'forcar_fechamento_abas_extras',
    'is_browsing_context_discarded_error',
    # Progresso monitorado (ex-Fix.monitoramento_progresso_unificado)
    'ProgressoUnificado', 'carregar_progresso_unificado',
    'salvar_progresso_unificado', 'marcar_processo_executado_unificado',
    'processo_ja_executado_unificado', 'executar_com_monitoramento_unificado',
    'ARQUIVO_PROGRESSO_UNIFICADO',
    # Error classes
    'PJePlusError', 'ElementoNaoEncontradoError', 'NavegacaoError',
    # API client (ex-Fix.variaveis_client)
    'PjeApiClient', 'session_from_driver',
    # API helpers (ex-Fix.variaveis_helpers)
    'obter_gigs_com_fase', 'obter_texto_documento',
    'buscar_atividade_gigs_por_observacao',
    'obter_todas_atividades_gigs_com_observacao',
    'padrao_liq', 'verificar_bndt',
    # API resolvers (ex-Fix.variaveis_resolvers)
    'obter_codigo_validacao_documento',
    'obter_peca_processual_da_timeline',
    'resolver_variavel', 'get_all_variables',
    'obter_chave_ultimo_despacho_decisao_sentenca',
    # Selectors PJe (ex-Fix.selectors_pje)
    'BTN_TAREFA_PROCESSO',
    # Movimento helpers (ex-Fix.movimento_helpers)
    'selecionar_movimento_dois_estagios', 'selecionar_movimento_auto',
    # Shim classes e helpers
    'ElementWaitPool', 'buscar',
    'carregar_js', 'limpar_cache_js',
    'registrar_modulo', 'atualizar', 'completar',
]
