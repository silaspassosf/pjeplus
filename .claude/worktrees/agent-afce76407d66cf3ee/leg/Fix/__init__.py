"""
Fix - Pacote modular para automação PJe.

Módulos:
  - Fix.core: Funções Selenium base (aguardar_e_clicar, selecionar_opcao, criar_driver_PC)
  - Fix.extracao: Extração, BNDT, GIGS, indexação
  - Fix.utils: Formatação, login, coleta, utilitários
  - Fix.abas: Gerenciamento de abas, validação de conexão

Uso recomendado:
    from Fix import aguardar_e_clicar, criar_gigs, login_cpf, validar_conexao_driver
"""

# ===== CORE =====
from .core import (
    # Consolidadas (performance)
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    preencher_campos_prazo,
    preencher_multiplos_campos,
    # Retry e robustez
    com_retry,
    buscar_seletor_robusto,
    esperar_elemento,
    esperar_url_conter,
    escolher_opcao_inteligente,
    encontrar_elemento_inteligente,
    # Legadas (compatibilidade)
    safe_click,
    wait,
    wait_for_visible,
    wait_for_clickable,
    smart_sleep,
    sleep,
    # Drivers
    criar_driver_PC,
    criar_driver_VT,
    criar_driver_notebook,
    criar_driver_sisb_pc,
    criar_driver_sisb_notebook,
    finalizar_driver,
    # Cookies/Sessão
    salvar_cookies_sessao,
    carregar_cookies_sessao,
    verificar_e_aplicar_cookies,
    # Filtros e navegação
    aplicar_filtro_100,
    filtro_fase,
    # Documentos
    verificar_documento_decisao_sentenca,
    visibilidade_sigilosos,
    buscar_ultimo_mandado,
    buscar_mandado_autor,
    buscar_documentos_sequenciais,
    buscar_documentos_polo_ativo,
    criar_botoes_detalhes,
    # Classes e JS
    ErroCollector,
    js_base,
)

# ===== EXTRACAO =====
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
    # Extracao
    'extrair_direto', 'extrair_documento', 'extrair_pdf', 'extrair_dados_processo',
    'extrair_destinatarios_decisao', 'criar_gigs', 'criar_comentario', 'criar_lembrete_posit',
    'bndt', 'filtrofases', 'indexar_processos', 'reindexar_linha',
    'abrir_detalhes_processo', 'indexar_e_processar_lista',
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
]

