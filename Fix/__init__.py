import logging
logger = logging.getLogger(__name__)

"""
Fix - Pacote modular para automação PJe (REFATORADO).

Estrutura modular:
  - Fix.selenium_base: Operações Selenium fundamentais (wait, click, retry, select)
  - Fix.drivers: Criação e gestão de WebDrivers Firefox
  - Fix.session: Cookies, autenticação e sessões
  - Fix.navigation: Filtros e navegação PJe
  - Fix.documents: Busca e extração de documentos
  - Fix.core: Funções legadas (em migração)
  - Fix.extracao: Extração, BNDT, GIGS
  - Fix.utils: Formatação, login, utilitários

Imports recomendados (API pública):
    from Fix.selenium_base import aguardar_e_clicar, selecionar_opcao, com_retry
    from Fix.drivers import criar_driver_PC, finalizar_driver
    from Fix.session import credencial, salvar_cookies_sessao
    from Fix.navigation import aplicar_filtro_100, filtro_fase
    from Fix.documents import buscar_documentos_sequenciais
"""

# ===== MÓDULOS REFATORADOS (PRIORIDADE) =====

# selenium_base: Operações Selenium fundamentais
from .selenium_base import (
    # Wait operations
    wait,
    wait_for_visible,
    wait_for_clickable,
    esperar_elemento,
    aguardar_e_clicar,
    esperar_url_conter,
    # Element interaction
    safe_click,
    preencher_campo,
    preencher_campos_prazo,
    # Retry logic
    com_retry,
    # Smart selection
    selecionar_opcao,
    escolher_opcao_inteligente,
    encontrar_elemento_inteligente,
)

# drivers: Gestão de WebDrivers
from .drivers import (
    criar_driver_PC,
    criar_driver_VT,
    criar_driver_notebook,
    criar_driver_sisb_pc,
    criar_driver_sisb_notebook,
    finalizar_driver,
    driver_session,
)

# session: Cookies e autenticação
from .session import (
    salvar_cookies_sessao,
    carregar_cookies_sessao,
    credencial,
)

# navigation: Filtros e navegação
from .navigation import (
    aplicar_filtro_100,
    filtro_fase,
    filtrofases,
)

# documents: Busca de documentos
from .documents import (
    verificar_documento_decisao_sentenca,
    buscar_ultimo_mandado,
    buscar_mandado_autor,
    buscar_documentos_sequenciais,
    buscar_documentos_polo_ativo,
    buscar_documento_argos,
)

# ===== CORE LEGADO (COMPATIBILIDADE) =====
from .core import (
    # Funções ainda em core.py (TODO: migrar)
    preencher_multiplos_campos,
    buscar_seletor_robusto,
    verificar_e_aplicar_cookies,
    visibilidade_sigilosos,
    criar_botoes_detalhes,
    smart_sleep,
    sleep,
    # Classes e JS
    ErroCollector,
    js_base,
)

# ===== EXTRACAO =====
from .extraction import (
    filtrofases,
    indexar_processos,
    reindexar_linha,
    abrir_detalhes_processo,
    indexar_e_processar_lista,
)
from .extracao import (
    extrair_direto,
    extrair_documento,
    extrair_pdf,
    extrair_dados_processo,
    extrair_destinatarios_decisao,
    bndt,
    analise_argos,
    tratar_anexos_argos,
    analise_outros,
    salvar_destinatarios_cache,
    carregar_destinatarios_cache,
)

# ===== PROGRESS =====
from .progress import (
    ProgressoUnificado,
    carregar_progresso_unificado,
    salvar_progresso_unificado,
    marcar_processo_executado_unificado,
    processo_ja_executado_unificado,
    executar_com_monitoramento_unificado,
    ARQUIVO_PROGRESSO_UNIFICADO,
    StatusModulo,
    NivelLog,
    Checkpoint,
    StatusModuloData,
    RegistroLog,
)

# ===== GIGS =====
from .gigs import (
    criar_gigs,
    criar_comentario,
    criar_lembrete_posit,
)

# `buscar_documento_argos` is implemented centrally in Fix.core to avoid duplicates.
from .core import buscar_documento_argos

# ===== UTILS =====
from .utils import (
    formatar_moeda_brasileira,
    formatar_data_brasileira,
    normalizar_cpf_cnpj,
    extrair_raiz_cnpj,
    identificar_tipo_documento,
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
)

# ===== ABAS =====
from .abas import (
    validar_conexao_driver,
    trocar_para_nova_aba,
    forcar_fechamento_abas_extras,
    is_browsing_context_discarded_error,
)

# ===== LOG CLEANER =====
# compat: funções agora exportadas por Fix.log
from .log import resumir_excecao, filtrar_log_arquivo, extrair_seletor_dom

__version__ = "2.0.0"

__all__ = [
    # Core - Consolidadas
    'aguardar_e_clicar', 'selecionar_opcao', 'preencher_campo', 'preencher_campos_prazo',
    'preencher_multiplos_campos',
    # Core - Retry e robustez
    'com_retry', 'buscar_seletor_robusto', 'esperar_elemento', 'esperar_url_conter',
    'escolher_opcao_inteligente', 'encontrar_elemento_inteligente',
    # Core - Legadas
    'safe_click', 'wait', 'wait_for_visible', 'wait_for_clickable',
    'smart_sleep', 'sleep',
    # Core - Drivers
    'criar_driver_PC', 'criar_driver_VT', 'criar_driver_notebook',
    'criar_driver_sisb_pc', 'criar_driver_sisb_notebook', 'finalizar_driver',
    'driver_session',
    # Core - Cookies/Sessão
    'salvar_cookies_sessao', 'carregar_cookies_sessao', 'verificar_e_aplicar_cookies',
    # Core - Filtros e navegação
    'aplicar_filtro_100', 'filtro_fase',
    # Core - Documentos
    'verificar_documento_decisao_sentenca', 'visibilidade_sigilosos',
    'buscar_ultimo_mandado', 'buscar_mandado_autor', 'buscar_documentos_sequenciais',
    'buscar_documentos_polo_ativo', 'criar_botoes_detalhes',
    # Core - Classes e JS
    'ErroCollector', 'js_base',
    # Progress
    'ProgressoUnificado', 'carregar_progresso_unificado', 'salvar_progresso_unificado',
    'marcar_processo_executado_unificado', 'processo_ja_executado_unificado',
    'executar_com_monitoramento_unificado', 'ARQUIVO_PROGRESSO_UNIFICADO',
    'StatusModulo', 'NivelLog', 'Checkpoint', 'StatusModuloData', 'RegistroLog',
    # Extracao
    'extrair_direto', 'extrair_documento', 'extrair_pdf', 'extrair_dados_processo',
    'extrair_destinatarios_decisao',
    'bndt', 'filtrofases', 'indexar_processos', 'reindexar_linha',
    'abrir_detalhes_processo', 'indexar_e_processar_lista',
    # Extraction (novo pacote)
    # (os mesmos acima, agora via Fix.extraction)
    # GIGS
    'criar_gigs', 'criar_comentario', 'criar_lembrete_posit',
    'analise_argos', 'buscar_documento_argos', 'tratar_anexos_argos', 'analise_outros',
    'salvar_destinatarios_cache', 'carregar_destinatarios_cache',
    # Utils
    'formatar_moeda_brasileira', 'formatar_data_brasileira',
    'normalizar_cpf_cnpj', 'extrair_raiz_cnpj', 'identificar_tipo_documento',
    'limpar_temp_selenium', 'login_manual', 'login_automatico', 'login_automatico_direto',
    'login_cpf', 'login_pc', 'coletar_link_ato_timeline', 'coletar_conteudo_js',
    'coletar_elemento_css', 'executar_coleta_parametrizavel',
    'inserir_html_editor', 'inserir_texto_editor',
    'inserir_html_no_editor_apos_marcador', 'obter_ultimo_conteudo_clipboard',
    'inserir_link_ato', 'inserir_link_ato_validacao',
    'configurar_recovery_driver', 'verificar_e_tratar_acesso_negado_global',
    'handle_exception_with_recovery', 'obter_driver_padronizado', 'driver_pc',
    'navegar_para_tela',
    # Abas
    'validar_conexao_driver', 'trocar_para_nova_aba', 'forcar_fechamento_abas_extras',
    'is_browsing_context_discarded_error',
    # Log cleaner
    'resumir_excecao', 'filtrar_log_arquivo', 'extrair_seletor_dom',
]

