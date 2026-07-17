# tools/vulture_whitelist.py
# Falsos positivos conhecidos — funcoes/imports que parecem mortos mas sao vivos.
#
# Convenção vulture: atribuir a _ para silenciar.
# https://github.com/jendrikseipp/vulture#whitelists

# Fix/utils.py é uma fachada de re-export. Os imports abaixo existem para que
# chamadores externos possam fazer "from Fix.utils import X". Vulture vê como
# "não usados" porque não enxerga chamadores externos — mas eles são API pública.
# Verificar individualmente com grep antes de remover.
_ = [
    # Fix/utils.py re-exports de utils_sleep (usados por callers via Fix.utils)
    "aguardar_loading_sumir",
    "aguardar_multiplas_condicoes",
    "aguardar_texto_mudar",
    "aguardar_url_mudar",
    "sleep_adaptativo",
    "sleep_com_logging",
    "sleep_condicional",
    "sleep_progressivo",
    "sleep_random",
    "aguardar_elemento_sumir",
    # Fix/utils.py re-exports de utils_angular
    "aguardar_angular_digest",
    "aguardar_angular_requests",
    "aguardar_elemento_angular_visivel",
    "clicar_elemento_angular",
    "esperar_elemento_angular",
    "executar_angular_expressao",
    "obter_angular_scope",
    "preencher_campo_angular",
    "verificar_angular_app",
    # Fix/utils.py re-exports de utils_selectors
    "aplicar_estrategia_seletor",
    "criar_seletor_fallback",
    "detectar_seletor_elemento",
    "encontrar_seletor_estavel",
    "gerar_seletor_dinamico",
    "obter_seletor_pje",
    "validar_seletor",
    # Fix/utils.py re-exports de utils_collect
    "coletar_dados_formulario",
    "coletar_dados_pagina",
    "coletar_links_pagina",
    "coletar_multiplos_elementos",
    "coletar_tabela_como_lista",
    "coletar_valor_atributo",
    # Fix/utils.py re-exports de utils_login
    "limpar_cookies_antigos",
    "listar_cookies_salvos",
    "configurar_caminho_credencial",
    "exibir_configuracao_atual",
    # Fix/utils.py re-exports de utils_drivers
    "configurar_driver_avancado",
    # Fix/utils.py re-exports de utils_editor
    # (nenhum salvo automaticamente — verificar manualmente)
    # NoSuchWindowException — usada em blocos except como tipo de excecao
    "NoSuchWindowException",
    # AHK — usadas condicionalmente dependendo do ambiente
    "AHK_EXE_ACTIVE",
    "AHK_SCRIPT_ACTIVE",
    # TYPE_CHECKING — padrao Python para imports so em type hints
    "TYPE_CHECKING",
    # variaveis.py re-exports
    "get_all_variables",
    "padrao_liq",
]
