# PJePlus - Índice Completo de Funções

> **Nota:** Este arquivo serve como mapa técnico do projeto. Use Ctrl+F para buscar funções específicas.

## 🧭 Principais Pontos de Entrada

| Arquivo | Função | Descrição |
| :--- | :--- | :--- |
| `x.py` | `main()` | Orquestrador principal com menu para Mandado, Prazo e PEC. |
| `f.py` | `main()` | Runner de testes para análise Argos e extrações. |
| `1.py` | - | Script legado completo para execução direta de fluxos P2B. |
| `Prazo/__init__.py` | `loop_prazo()` | Gateway para o fluxo de lotes e processamento individual de Prazos. |

---
## 📂 ref

### 📄 `ref\a.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\aud.py`
- **Funções:** `carregar_progresso_aud`, `salvar_progresso_aud`, `processo_ja_executado_aud`, `marcar_processo_executado_aud`, `acao_bucket_a`, `indexar_e_processar_lista_aud`, `criar_driver_e_logar`, `coletar_lista_processos`, `agrupar_em_buckets`, `reindexar_linha_js`, `_abrir_nova_aba`, `desmarcar_100`, `remarcar_100_pos_aud`, `marcar_aud`, `executar_acoes_por_bucket`, `run_aud`, `processar_bucket`, `acao_bucket_b`, `acao_bucket_c`, `processar_resultados_bucket`

### 📄 `ref\f.py`
- **Funções:** `criar_driver_pc_visivel`, `criar_driver_vt_visivel`, `executar_testes`, `main`

### 📄 `ref\log.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\monitor.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\pass_cleanup.py`
- **Funções:** `_leading_ws`, `_is_blank_or_comment`, `_find_prev_same_indent`, `_find_next_same_indent`, `_is_noop_block`, `_next_same_indent_header`, `remove_redundant_passes`, `remove_noop_if_blocks`, `should_skip`, `process_file`, `main`

### 📄 `ref\progresso_unificado.py`
- **Funções:** `inicializar_progresso_unificado`, `carregar_progresso_modulo`, `salvar_progresso_modulo`, `marcar_processo_executado_modulo`, `processo_ja_executado_modulo`, `__init__`, `carregar_progresso`, `_deve_limpar_progresso_antigo`, `_limpar_progresso_automaticamente`, `salvar_progresso`, `processo_ja_executado`, `marcar_processo_executado`, `_detectar_erro_critico`, `_validar_sucesso_real`, `gerar_relatorio_simples`, `obter_estatisticas`, `resetar_progresso`, `_estrutura_modulo_padrao`, `_migrar_arquivo_antigo`, `_migrar_arquivo_antigo_simples`, `_criar_estrutura_limpa`, `_salvar_modulo_no_unificado`, `_criar_backup_corrompido`, `_salvar_arquivo_compatibilidade`, `_atualizar_estatisticas_gerais`, `_remover_de_listas_erro`, `_registrar_historico`

### 📄 `ref\run_debug_auto.py`
- **Funções:** `limpar_progresso`, `executar_x_py_auto`, `analisar_logs_debug`, `main`

### 📄 `ref\s.py`
- **Funções:** `testar_segunda_minuta_completa`

### 📄 `ref\selector_learning.py`
- **Funções:** `report_selector_result`, `get_recommended_selectors`, `get_learning_stats`, `save_learning_db`, `use_best_selector`, `__new__`, `__init__`, `_load`, `_save`, `_calculate_score`, `report_result`, `get_recommendations`, `get_stats`, `force_save`

### 📄 `ref\x.py`
- **Funções:** `criar_driver_pc`, `criar_driver_vt`, `criar_e_logar_driver`, `verificar_acesso_negado`, `normalizar_resultado`, `resetar_driver`, `executar_com_recuperacao`, `executar_bloco_completo`, `executar_mandado`, `executar_prazo`, `executar_pec`, `executar_p2b`, `menu_ambiente`, `menu_execucao`, `configurar_logging`, `main`, `__init__`, `write`, `flush`, `close`, `pec_fluxo`, `pec_fluxo`

### 📄 `ref\atos\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\atos\comunicacao.py`
- **Funções:** `comunicacao_judicial`, `make_comunicacao_wrapper`, `log`, `normalizar_string`, `selecionar_destinatario_por_documento`, `wrapper`, `_preencher_input_js`, `_escolher_opcao_select_js`, `_clicar_radio_button_js`

### 📄 `ref\atos\core.py`
- **Funções:** `selecionar_opcao_select`, `verificar_carregamento_pagina`, `aguardar_e_verificar_aba`, `verificar_carregamento_detalhe`, `aguardar_e_verificar_detalhe`

### 📄 `ref\atos\judicial.py`
- **Funções:** `fluxo_cls`, `esperar_insercao_modelo`, `ato_judicial`, `make_ato_wrapper`, `ato_pesquisas`, `idpj`, `preencher_prazos_destinatarios`, `verificar_bloqueio_recente`, `wrapper`

### 📄 `ref\atos\movimentos.py`
- **Funções:** `mov_simples`, `mov`, `mov_arquivar`, `mov_exec`, `mov_aud`, `mov_prazo`, `mov_sob`, `mov_fimsob`, `def_chip`, `despacho_generico`, `log_debug`, `log_debug`, `buscar_aba_detalhe`, `tentar_encontrar_alvo`, `log_msg`, `log_msg`, `log_msg`, `garantir_aba_detalhe`

### 📄 `ref\atos\wrappers_ato.py`
- **Funções:** `_inserir_relatorio_conciso_sisbajud`

### 📄 `ref\atos\wrappers_mov.py`
- **Funções:** `mov_arquivar`, `mov_exec`, `mov_aud`, `mov_prazo`

### 📄 `ref\atos\wrappers_pec.py`
- **Funções:** `wrapper_pec_ord_com_domicilio`, `wrapper_pec_sum_com_domicilio`

### 📄 `ref\atos\wrappers_utils.py`
- **Funções:** `visibilidade_sigilosos`, `executar_visibilidade_sigilosos_se_necessario`

### 📄 `ref\Fix\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\Fix\abas.py`
- **Funções:** `is_browsing_context_discarded_error`, `validar_conexao_driver`, `trocar_para_nova_aba`, `forcar_fechamento_abas_extras`

### 📄 `ref\Fix\core.py`
- **Funções:** `_log_info`, `_log_error`, `_audit`, `wait`, `wait_for_visible`, `wait_for_clickable`, `safe_click`, `buscar_seletor_robusto`, `esperar_elemento`, `aguardar_e_clicar`, `_clicar_botao_movimentar`, `_clicar_botao_tarefa_processo`, `selecionar_opcao`, `preencher_campo`, `preencher_campos_prazo`, `preencher_multiplos_campos`, `com_retry`, `escolher_opcao_inteligente`, `encontrar_elemento_inteligente`, `js_base`, `criar_driver_PC`, `criar_driver_VT`, `criar_driver_notebook`, `criar_driver_sisb_pc`, `criar_driver_sisb_notebook`, `finalizar_driver`, `salvar_cookies_sessao`, `credencial`, `carregar_cookies_sessao`, `verificar_e_aplicar_cookies`, `exibir_configuracao_ativa`, `aplicar_filtro_100`, `filtro_fase`, `_aguardar_loader_painel`, `filtrofases`, `esperar_url_conter`, `verificar_documento_decisao_sentenca`, `visibilidade_sigilosos`, `criar_botoes_detalhes`, `buscar_ultimo_mandado`, `buscar_mandado_autor`, `buscar_documentos_sequenciais`, `buscar_documentos_polo_ativo`, `_tentar_click_padrao`, `_tentar_click_javascript`, `_tentar_click_actionchains`, `_tentar_click_javascript_avancado`, `buscar_documentos_polo_ativo`, `buscar_documento_argos`, `smart_sleep`, `sleep`, `buscar_input_associado`, `__init__`, `registrar_erro`, `registrar_sucesso`, `gerar_relatorio`, `exportar_csv`, `limpar`, `tem_erros`, `get_taxa_sucesso`, `__init__`, `get_delay`, `_selecionar`

### 📄 `ref\Fix\debug_interativo.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\Fix\extracao.py`
- **Funções:** `extrair_direto`, `extrair_documento`, `extrair_pdf`, `extrair_dados_processo`, `extrair_destinatarios_decisao`, `salvar_destinatarios_cache`, `carregar_destinatarios_cache`, `_normalizar_texto_decisao`, `_extrair_linha_tipo`, `_extrair_formatar_texto`, `_extrair_info_documento`, `_extrair_via_pdf_viewer`, `_extrair_via_iframe`, `_extrair_via_elemento_dom`, `_gigs_responsavel_valido`, `criar_lembrete_posit`, `_parse_gigs_string`, `criar_gigs`, `criar_comentario`, `bndt`, `_bndt_validar_localizacao`, `_bndt_abrir_menu`, `_bndt_clicar_icone`, `_bndt_abrir_nova_aba`, `_bndt_selecionar_operacao`, `_bndt_selecionar_operacao_para_polo`, `_bndt_processar_selecoes`, `_bndt_processar_selecoes_polo`, `_bndt_gravar_e_confirmar`, `_bndt_gravar_e_confirmar_polo`, `filtrofases`, `indexar_processos`, `reindexar_linha`, `abrir_detalhes_processo`, `trocar_para_nova_aba`, `_indexar_preparar_contexto`, `_indexar_tentar_reindexar`, `_indexar_tentar_trocar_aba`, `_indexar_processar_item`, `indexar_e_processar_lista`, `analise_argos`, `tratar_anexos_argos`, `analise_outros`, `get_cookies_dict`, `extrair_numero_processo_url`, `extrair_trt_host`, `obter_id_processo_via_api`, `obter_dados_processo_via_api`, `criar_pessoa_limpa`, `obter_linhas_frescas`, `callback_wrapper`

### 📄 `ref\Fix\headless_helpers.py`
- **Funções:** `limpar_overlays_headless`, `scroll_to_element_safe`, `click_headless_safe`, `wait_and_click_headless`, `find_element_headless_safe`, `executar_com_retry_headless`, `is_headless_mode`, `aguardar_elemento_headless_safe`

### 📄 `ref\Fix\log.py`
- **Funções:** `__init__`, `_configurar_nivel`, `_configurar_formatador`, `debug`, `info`, `warning`, `error`

### 📄 `ref\Fix\monitoramento_progresso_unificado.py`
- **Funções:** `_log_progresso`, `_validar_tipo_execucao`, `_validar_e_limpar_progresso`, `carregar_progresso_unificado`, `salvar_progresso_unificado`, `limpar_progresso_corrompido`, `extrair_numero_processo_unificado`, `verificar_acesso_negado_unificado`, `processo_ja_executado_unificado`, `processo_tem_erro_unificado`, `marcar_processo_executado_unificado`, `executar_com_monitoramento_unificado`, `carregar_progresso_p2b`, `salvar_progresso_p2b`, `extrair_numero_processo_p2b`, `verificar_acesso_negado_p2b`, `processo_ja_executado_p2b`, `marcar_processo_executado_p2b`, `carregar_progresso`, `salvar_progresso`, `extrair_numero_processo`, `verificar_acesso_negado`, `processo_ja_executado`, `marcar_processo_executado`, `carregar_progresso_mandado`, `salvar_progresso_mandado`, `extrair_numero_processo_mandado`, `verificar_acesso_negado_mandado`, `processo_ja_executado_mandado`, `marcar_processo_executado_mandado`, `exemplo_uso_monitoramento_unificado`, `__init__`, `carregar_progresso`, `salvar_progresso`, `processo_ja_executado`, `marcar_progresso_executado`, `marcar_processo_executado`

### 📄 `ref\Fix\movimento_helpers.py`
- **Funções:** `_normalize_text`, `selecionar_movimento_dois_estagios`, `selecionar_movimento_auto`

### 📄 `ref\Fix\otimizacao_wrapper.py`
- **Funções:** `with_learning`, `usar_headless_safe`, `inicializar_otimizacoes`, `finalizar_otimizacoes`, `decorator`, `wrapper`

### 📄 `ref\Fix\progresso_unificado.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\Fix\selectors_pje.py`
- **Funções:** `seletor_processo_por_numero`, `seletor_pec_por_numero`, `buscar_seletor_robusto`

### 📄 `ref\Fix\utils.py`
- **Funções:** `formatar_moeda_brasileira`, `formatar_data_brasileira`, `normalizar_cpf_cnpj`, `extrair_raiz_cnpj`, `identificar_tipo_documento`, `_audit`, `_log_info`, `_log_error`, `limpar_temp_selenium`, `login_manual`, `login_automatico`, `login_automatico_direto`, `login_cpf`, `_obter_caminhos_ahk`, `_log_msg_coleta`, `_extrair_numero_processo_cnj`, `coletar_link_ato_timeline`, `coletar_conteudo_formatado_documento`, `coletar_conteudo_js`, `coletar_elemento_css`, `_get_editable`, `_place_selection_at_marker`, `inserir_html_editor`, `inserir_texto_editor`, `obter_ultimo_conteudo_clipboard`, `inserir_html_editor`, `inserir_link_ato`, `executar_coleta_parametrizavel`, `inserir_html_no_editor_apos_marcador`, `inserir_no_editor_apos_marcador`, `inserir_link_ato_validacao`, `inserir_conteudo_formatado`, `configurar_recovery_driver`, `verificar_e_tratar_acesso_negado_global`, `handle_exception_with_recovery`, `is_browsing_context_discarded_error`, `validar_conexao_driver`, `obter_driver_padronizado`, `driver_pc`, `navegar_para_tela`, `login_pc`, `aguardar_e_clicar`, `js_base`, `salvar_cookies_sessao`, `carregar_cookies_sessao`, `verificar_e_aplicar_cookies`, `preencher_campos_angular_material`, `log_msg`, `log_msg`, `log_msg`, `log_msg`, `_norm`

### 📄 `ref\Fix\variaveis.py`
- **Funções:** `obter_gigs_com_fase`, `session_from_driver`, `obter_codigo_validacao_documento`, `obter_peca_processual_da_timeline`, `resolver_variavel`, `get_all_variables`, `obter_chave_ultimo_despacho_decisao_sentenca`, `obter_texto_documento`, `buscar_atividade_gigs_por_observacao`, `obter_todas_atividades_gigs_com_observacao`, `padrao_liq`, `verificar_bndt`, `obter_domicilio_eletronico_parte`, `verificar_domicilio_eletronico_partes`, `__init__`, `_url`, `timeline`, `documento_por_id`, `execucao_gigs`, `processo_por_id`, `partes`, `id_processo_por_numero`, `calculos`, `pericias`, `atividades_gigs`, `debitos_trabalhistas_bndt`, `domicilio_eletronico`

### 📄 `ref\Mandado\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\Mandado\atos_wrapper.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\Mandado\core.py`
- **Funções:** `setup_driver`, `navegacao`, `iniciar_fluxo_robusto`, `main`, `fluxo_callback`, `recovery_credencial`

### 📄 `ref\Mandado\log.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\Mandado\processamento.py`
- **Funções:** `_lazy_import_mandado`, `_identificar_tipo_anexo`, `_aguardar_icone_plus`, `_buscar_icone_plus_direto`, `_localizar_modal_visibilidade`, `_processar_modal_visibilidade`, `_extrair_resultado_sisbajud`, `_extrair_executados_pdf`, `processar_sisbajud`, `tratar_anexos_argos`, `processar_argos`, `ultimo_mdd`, `fluxo_mandado`, `fluxo_mandados_outros`, `remover_acentos`, `fluxo_callback`, `analise_padrao`, `_buscar_modal`

### 📄 `ref\Mandado\regras.py`
- **Funções:** `_lazy_import_mandado_regras`, `estrategia_defiro_instauracao`, `estrategia_despacho_argos`, `estrategia_infojud`, `estrategia_decisao_manifestar`, `estrategia_tendo_em_vista_que`, `aplicar_regras_argos`

### 📄 `ref\Mandado\utils.py`
- **Funções:** `lembrete_bloq`, `_selecionar_checkbox_intimacao`, `fechar_intimacao`, `retirar_sigilo`, `retirar_sigilo_fluxo_argos`, `retirar_sigilo_certidao_devolucao_primeiro`, `retirar_sigilo_demais_documentos_especificos`, `retirar_sigilo_documentos_especificos`, `marcado`

### 📄 `ref\PEC\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\PEC\anexos.py`
- **Funções:** `extrair_numero_processo_da_pagina`, `carta_wrapper`, `consulta_wrapper`, `wrapper_bloqneg`, `wrapper_parcial`, `formatar_conteudo_ecarta`, `_obter_conteudo_relatorio_sisbajud`, `_wrapper_sisbajud_generico`, `wrapper_juntada_geral`, `create_juntador`, `executar_juntada_ate_editor`, `executar_juntada`, `_escolher_opcao_gigs`, `_preencher_input_gigs`, `_clicar_elemento_gigs`, `_selecionar_modelo_gigs`, `_executar_coleta_opcional`, `_preencher_tipo`, `_preencher_descricao`, `_configurar_sigilo`, `_selecionar_e_inserir_modelo`, `_inserir_conteudo_customizado`, `_salvar_documento`, `_assinar_se_necessario`, `_abrir_interface_anexacao`, `_preencher_campos_basicos`, `_inserir_modelo`, `substituir_marcador_por_conteudo`, `salvar_conteudo_clipboard`, `extrair_numero_processo_da_url`, `inserir_fn`, `inserir_fn`, `carregar_clipboard_arquivo`, `_condicao_html`

### 📄 `ref\PEC\carta.py`
- **Funções:** `_carregar_calendario_dias_uteis`, `_somar_dias_uteis`, `_parse_data_ecarta`, `_obter_numero_processo`, `carta`, `teste_juntada_carta_html`, `_texto_e_correio`, `_extrair_texto_completo`, `_processar_item`, `gerar_html_carta_para_juntada`

### 📄 `ref\PEC\core.py`
- **Funções:** `carregar_progresso_pec`, `salvar_progresso_pec`, `extrair_numero_processo_pec`, `verificar_acesso_negado_pec`, `verificar_e_recuperar_acesso_negado`, `processo_ja_executado_pec`, `marcar_processo_executado_pec`, `reiniciar_driver_e_logar_pje`, `navegar_para_atividades`, `aplicar_filtro_xs`, `indexar_processo_atual_gigs`, `analisar_documentos_pos_carta`, `main`, `log_msg`, `recovery_credencial`

### 📄 `ref\PEC\pet.py`
- **Funções:** `navegacao_inicial_pet`, `aplicar_filtro_50`, `reordenar_coluna_tipo_peticao`, `extrair_tabela_peticoes`, `carregar_progresso_pet`, `salvar_progresso_pet`, `marcar_hipotese_executada`, `definir_regras_apagar`, `verifica_condicoes`, `normalizar_texto`, `gerar_regex_flexivel`, `acao_apagar`, `agrupar_por_hipotese`, `executar_grupo_apagar`, `executar_fluxo_pet`, `__init__`, `__repr__`, `gerar_chave_regra`, `_selecionar`

### 📄 `ref\PEC\pet2.py`
- **Funções:** `normalizar_texto`, `gerar_regex_flexivel`, `campo`, `qualquer_campo`, `criar_acao_gigs`, `criar_acao_padrao_liq`, `definir_regras`, `definir_regras_analise_conteudo`, `verifica_peticao_contra_hipotese`, `verifica_peticao_pericias`, `verifica_peticao_diretos`, `_acao_apagar`, `navegacao_inicial_pet`, `aplicar_filtro_50`, `reordenar_coluna_tipo_peticao`, `extrair_tabela_peticoes`, `extrair_tabela_peticoes_selenium`, `_abrir_detalhe_peticao`, `_fechar_e_voltar_lista`, `processar_analise_pdf`, `_executar_acao_completa`, `classificar_peticoes`, `executar_classificadas`, `clicar_proxima_pagina`, `processar_peticoes_escaninho`, `criar_driver_vt`, `main`, `__init__`, `__repr__`, `_gigs`, `_check`, `_selecionar`

### 📄 `ref\PEC\pet_novo.py`
- **Funções:** `carregar_progresso_pet`, `salvar_progresso_pet`, `marcar_processo_executado_pet`, `processo_ja_executado_pet`, `normalizar_texto`, `gerar_regex_flexivel`, `navegacao_inicial_pet`, `aplicar_filtro_50`, `reordenar_coluna_tipo_peticao`, `extrair_tabela_peticoes`, `acao_apagar`, `acao_pericias_com_data`, `acao_gigs`, `criar_gigs_1_xs_aud`, `cris_gigs_minus1_xs_pec`, `padrao_liq_acao`, `definir_regras`, `verifica_peticao_contra_hipotese`, `verifica_peticao_pericias`, `verifica_peticao_diretos`, `agrupar_por_regra`, `_abrir_detalhe_petição`, `_fechar_e_voltar_lista`, `_processar_petição_completa`, `_executar_acao_unica`, `_executar_acoes_sequenciais`, `_executar_acao`, `executar_regras`, `localizar_ultima_peticao`, `extrair_conteudo_peticao`, `definir_regras_analise`, `analise_pet`, `executar_fluxo_pet`, `__init__`, `__repr__`, `_selecionar`, `simplificar_processo`

### 📄 `ref\PEC\petjs.py`
- **Funções:** `criar_driver_vt`, `aplicar_filtro_50`, `extrair_tabela_js`, `salvar_resultado_json`, `converter_json_para_peticoes`, `processar_peticoes_js_integrado`, `executar_motor_teste`, `_formatar_acao_detalhada`, `_obter_nome_acao`, `main`

### 📄 `ref\PEC\processamento.py`
- **Funções:** `_lazy_import_pec`, `executar_acao`, `processar_processo_pec_individual`, `executar_fluxo_robusto`, `executar_fluxo_novo`, `_configurar_driver`, `_navegar_atividades`, `_aplicar_filtros`, `_organizar_e_executar_buckets`, `criar_lista_sisbajud`, `executar_lista_sisbajud_por_abas`, `criar_lista_resto`, `_indexar_todos_processos`, `_filtrar_por_observacao`, `_salvar_amostra_debug_rows`, `_filtrar_por_progresso`, `_filtrar_por_acoes_validas`, `_agrupar_em_buckets`, `_executar_dry_run`, `_processar_buckets`, `_processar_bucket_generico`, `_processar_bucket_demais`, `_processar_bucket_sisbajud`, `_imprimir_relatorio_final`, `indexar_e_criar_buckets_unico`, `chamar_funcao_com_assinatura_correta`, `_solicitar_reinicio_por_stale`, `callback_pec_centralizado`

### 📄 `ref\PEC\processamento_backup.py`
- **Funções:** `executar_acao`, `processar_processo_pec_individual`, `executar_fluxo_robusto`, `executar_fluxo_novo`, `_configurar_driver`, `_navegar_atividades`, `_aplicar_filtros`, `_organizar_e_executar_buckets`, `criar_lista_sisbajud`, `executar_lista_sisbajud_por_abas`, `criar_lista_resto`, `_indexar_todos_processos`, `_filtrar_por_observacao`, `_salvar_amostra_debug_rows`, `_filtrar_por_progresso`, `_filtrar_por_acoes_validas`, `_agrupar_em_buckets`, `_executar_dry_run`, `_processar_buckets`, `_processar_bucket_generico`, `_processar_bucket_demais`, `_processar_bucket_sisbajud`, `_imprimir_relatorio_final`, `indexar_e_criar_buckets_unico`, `chamar_funcao_com_assinatura_correta`, `callback_pec_centralizado`

### 📄 `ref\PEC\regras.py`
- **Funções:** `_lazy_import_pec_regras`, `_get_or_create_driver_sisbajud`, `fechar_driver_sisbajud_global`, `_remover_acentos`, `_normalizar_texto`, `_gerar_regex_geral`, `_build_action_rules`, `get_cached_rules`, `get_action_rules`, `determinar_acoes_por_observacao`, `determinar_acao_por_observacao`, `executar_acao_pec`, `def_sob`, `def_presc`, `def_ajustegigs`, `determinar_acoes_por_observacao`, `determinar_acao_por_observacao`, `_attr`, `_eh_documento_relevante`, `_tem_assinatura_magistrado`, `log_msg`, `log_msg`, `log_msg`, `remover_acentos`, `normalizar_texto`, `gerar_regex_geral`, `executar_mov_sob_precatorio`, `executar_juizo_universal`, `executar_def_presc`, `executar_ato_prov`, `executar_socio`, `executar_mov_sob_retorno_feito`, `executar_penhora_rosto`, `extrair_data_item`, `converter_data_texto_para_numerico`, `converter_data_para_datetime`

### 📄 `ref\PEC\test_leitura_real.py`
- **Funções:** `normalizar_texto`, `gerar_regex_flexivel`, `campo`, `qualquer_campo`, `verifica_peticao_contra_hipotese`, `definir_regras`, `extrair_texto_limpo`, `parse_numero_processo`, `parse_tarefa_fase`, `parse_data`, `extrair_peticoes_html`, `testar_peticao_contra_regras`, `main`

### 📄 `ref\PEC\test_pet2.py`
- **Funções:** `parse_test_data`, `create_peticao_linha`, `test_petition`, `print_test_results`, `main`

### 📄 `ref\PEC\test_pet2_real.py`
- **Funções:** `extrair_peticoes_html`, `testar_peticao`, `main`

### 📄 `ref\Prazo\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\Prazo\__main__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\Prazo\loop.py`
- **Funções:** `_ciclo1_aplicar_filtro_fases`, `_verificar_quantidade_processos_paginacao`, `_ciclo1_marcar_todas`, `_ciclo1_abrir_suitcase`, `_ciclo1_aguardar_movimentacao_lote`, `_ciclo1_movimentar_destino_providencias`, `_ciclo1_movimentar_destino`, `_ciclo1_retornar_lista`, `ciclo1`, `_ciclo2_aplicar_filtros`, `_extrair_numero_processo_da_linha`, `_selecionar_processos_por_gigs_aj_jt`, `_verificar_processo_tem_xs`, `_verificar_processos_xs_paralelo`, `_ciclo2_processar_livres`, `_ciclo2_criar_atividade_xs`, `_ciclo2_selecionar_nao_livres`, `_ciclo2_movimentar_lote`, `ciclo2_processar_livres_apenas_uma_vez`, `ciclo2_loop_providencias`, `ciclo2`, `selecionar_processos_nao_livres`, `loop_prazo`, `main`, `_tentar_marcar`, `_tentar_abrir_suitcase`, `verificar_um`, `recovery_credencial`

### 📄 `ref\Prazo\p2b_core.py`
- **Funções:** `remover_acentos`, `normalizar_texto`, `gerar_regex_geral`, `parse_gigs_param`, `carregar_progresso_p2b`, `salvar_progresso_p2b`, `marcar_processo_executado_p2b`, `processo_ja_executado_p2b`, `checar_prox`, `ato_pesqliq_callback`, `aplicar`

### 📄 `ref\Prazo\p2b_fluxo.py`
- **Funções:** `fluxo_pz`

### 📄 `ref\Prazo\p2b_fluxo_helpers.py`
- **Funções:** `_lazy_import`, `prescreve`, `analisar_timeline_prescreve_js_puro`, `_encontrar_documento_relevante`, `_extrair_texto_documento`, `_extrair_com_extrair_direto`, `_extrair_com_extrair_documento`, `_definir_regras_processamento`, `_processar_regras_gerais`, `_processar_cabecalho_impugnacoes`, `_processar_checar_cabecalho`, `_executar_visibilidade_sigilosos`, `_fechar_aba_processo`

### 📄 `ref\Prazo\p2b_fluxo_helpers_backup.py`
- **Funções:** `_encontrar_documento_relevante`, `_extrair_texto_documento`, `_extrair_com_extrair_direto`, `_extrair_com_extrair_documento`, `_definir_regras_processamento`, `_processar_regras_gerais`, `_processar_cabecalho_impugnacoes`, `_processar_checar_cabecalho`, `_executar_visibilidade_sigilosos`, `_fechar_aba_processo`

### 📄 `ref\Prazo\p2b_prazo.py`
- **Funções:** `fluxo_prazo`, `aplicar_filtro_atividades_xs`, `_indexar_processos_lista`, `_filtrar_processos_nao_executados`, `_processar_lista_processos`, `_processar_processo_individual`, `_reindexar_linha_se_necessario`, `_executar_callback_processo`, `_gerenciar_abas_apos_processo`

### 📄 `ref\Prazo\prov.py`
- **Funções:** `criar_driver`, `_criar_driver_vt`, `_criar_driver_pc`, `criar_e_logar_driver`, `fluxo_prov`, `navegacao_prov`, `selecionar_e_processar`, `aplicar_xs_e_registrar`, `main`, `fluxo_prov_integrado`

### 📄 `ref\SISB\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `ref\SISB\batch.py`
- **Funções:** `processar_lote_sisbajud`, `_processar_grupo`

### 📄 `ref\SISB\core.py`
- **Funções:** `simular_movimento_humano`, `driver_sisbajud`, `login_automatico_sisbajud`, `login_manual_sisbajud`, `salvar_dados_processo_temp`, `iniciar_sisbajud`, `minuta_bloqueio`, `processar_ordem_sisbajud`, `processar_bloqueios`, `processar_endereco`, `coletar_dados_minuta_sisbajud`, `minuta_bloqueio_60`

### 📄 `ref\SISB\helpers.py`
- **Funções:** `_validar_dados`, `_selecionar_prazo_bloqueio`, `_preencher_campos_iniciais`, `_processar_reus_otimizado`, `_salvar_minuta`, `_gerar_relatorio_minuta`, `_atualizar_relatorio_com_segundo_protocolo`, `_protocolar_minuta`, `_criar_minuta_agendada_por_copia`, `_criar_minuta_agendada`, `_carregar_dados_ordem`, `_filtrar_series`, `_voltar_para_lista_ordens_serie`, `_voltar_para_lista_principal`, `_navegar_e_extrair_ordens_serie`, `_extrair_ordens_da_serie`, `_aplicar_acao_por_fluxo`, `_identificar_ordens_com_bloqueio`, `_agrupar_dados_bloqueios`, `extrair_dados_bloqueios_processados`, `gerar_relatorio_bloqueios_processados`, `gerar_relatorio_bloqueios_conciso`, `_extrair_nome_executado_serie`, `_processar_series`, `_calcular_estrategia_bloqueio`, `_gerar_relatorio_ordem`, `_executar_juntada_pje`, `criar_js_otimizado`, `extrair_valor_monetario`

### 📄 `ref\SISB\performance.py`
- **Funções:** `optimized_element_wait`, `batched_form_fill`, `cached_selector_lookup`, `parallel_series_processing`, `smart_cache_operation`, `__init__`, `cache_element_selector`, `batch_dom_operations`, `optimize_javascript_execution`, `__init__`, `_create_mutation_observer`, `replace_polling_with_observer`, `__init__`, `cache_element`, `get_cached_element`, `cache_data`, `get_cached_data`, `clear_expired_cache`, `__init__`, `process_series_parallel`

### 📄 `ref\SISB\processamento.py`
- **Funções:** `minuta_bloqueio_refatorada`, `_preencher_campos_principais`, `_processar_reus_otimizado`, `_configurar_valor`, `_configurar_opcoes_adicionais`, `_salvar_minuta`, `_gerar_relatorio_minuta`, `_salvar_relatorios`, `_finalizar_minuta`, `_extrair_cpf_autor`, `_extrair_nome_autor`, `_processar_ordem`

### 📄 `ref\SISB\s_orquestrador.py`
- **Funções:** `criar_js_otimizado_legacy`, `iniciar_sisbajud_legacy`, `minuta_bloqueio_legacy`, `executar_sisbajud_completo`, `minuta_bloqueio`, `minuta_endereco`, `processar_ordem_sisbajud`, `processar_bloqueios`, `trigger_event`, `safe_execute_script`, `debug_sisbajud_status`, `otimizar_performance_sisbajud`

### 📄 `ref\SISB\standards.py`
- **Funções:** `validar_numero_processo_padronizado`, `formatar_valor_monetario_padronizado`, `calcular_data_limite_padronizada`, `criar_timestamp_padronizado`, `log_operacao`, `validar_parametros`, `retry_on_failure`, `__post_init__`, `__post_init__`, `valor_bloqueado_text`, `valor_bloquear_text`, `__init__`, `log`, `log_erro`, `log_sucesso`, `__init__`, `__init__`, `__init__`, `__init__`, `__init__`, `__init__`, `decorator`, `decorator`, `decorator`, `wrapper`, `wrapper`, `wrapper`

### 📄 `ref\SISB\test_refatoracao.py`
- **Funções:** `run_tests`, `test_constants`, `test_status_processamento`, `test_tipo_fluxo`, `test_dados_processo`, `test_resultado_processamento`, `test_logger`, `test_validar_numero_processo`, `test_formatar_valor_monetario`, `test_criar_js_otimizado`, `test_safe_click`, `test_aguardar_elemento`, `test_performance_optimizer`, `test_cache_manager`, `test_polling_reducer`, `test_executar_sisbajud_completo_sucesso`, `test_executar_sisbajud_completo_erro_inicializacao`, `test_executar_sisbajud_completo_dados_invalidos`, `test_imports_modulares`, `test_compatibilidade_legacy`, `test_func`

### 📄 `ref\SISB\utils.py`
- **Funções:** `criar_js_otimizado`, `safe_click`, `simulate_human_movement`, `aguardar_elemento`, `aguardar_e_clicar`, `escolher_opcao_sisbajud`, `extrair_protocolo`, `validar_numero_processo`, `formatar_valor_monetario`, `calcular_data_limite`, `criar_timestamp`, `log_sisbajud`, `registrar_erro_minuta`, `carregar_dados_processo`, `mutation_observer_script`, `rate_limiting_manager`, `advanced_dom_manipulator`, `consolidated_js_framework`, `aplicar_rate_limiting`, `detectar_captcha`, `anti_detection_measures`, `smart_wait`, `_extrair_dados_pje`, `_criar_driver_sisbajud`, `_realizar_login`, `_navegar_minuta`, `_validar_dados`, `_preencher_campos_iniciais`, `_processar_reus_otimizado`, `_salvar_minuta`

### 📄 `ref\SISB\utils_refatorado_backup.py`
- *(Sem funções definidas ou erro de parsing)*

## 📂 Fix

### 📄 `Fix\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\abas.py`
- **Funções:** `is_browsing_context_discarded_error`, `validar_conexao_driver`, `trocar_para_nova_aba`, `forcar_fechamento_abas_extras`

### 📄 `Fix\core.py`
- **Funções:** `wait`, `wait_for_visible`, `wait_for_clickable`, `buscar_seletor_robusto`, `esperar_elemento`, `safe_click`, `aguardar_e_clicar`, `selecionar_opcao`, `preencher_campo`, `preencher_campos_prazo`, `preencher_multiplos_campos`, `com_retry`, `escolher_opcao_inteligente`, `encontrar_elemento_inteligente`, `js_base`, `criar_driver_PC`, `criar_driver_VT`, `criar_driver_notebook`, `criar_driver_sisb_pc`, `criar_driver_sisb_notebook`, `finalizar_driver`, `salvar_cookies_sessao`, `credencial`, `carregar_cookies_sessao`, `verificar_e_aplicar_cookies`, `aplicar_filtro_100`, `filtro_fase`, `filtrofases`, `esperar_url_conter`, `verificar_documento_decisao_sentenca`, `visibilidade_sigilosos`, `criar_botoes_detalhes`, `buscar_ultimo_mandado`, `buscar_mandado_autor`, `buscar_documentos_sequenciais`, `buscar_documentos_polo_ativo`, `buscar_documento_argos`, `smart_sleep`, `sleep`

### 📄 `Fix\debug_interativo.py`
- **Funções:** `obter_relatorio_debug`, `inicializar_debug_interativo`, `get_debug_interativo`, `on_erro_critico`, `is_debug_ativo`, `__init__`, `is_erro_critico`, `capturar_contexto`, `pausar_para_analise`, `_tentar_fix_automatico`, `salvar_relatorio_erro`, `obter_relatorio_final`, `_mostrar_info_detalhada`

### 📄 `Fix\extracao.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\extracao_analise.py`
- **Funções:** `analise_argos`, `tratar_anexos_argos`, `analise_outros`

### 📄 `Fix\extracao_bndt.py`
- **Funções:** `bndt`, `_bndt_validar_localizacao`, `_bndt_abrir_menu`, `_bndt_clicar_icone`, `_bndt_abrir_nova_aba`, `_bndt_selecionar_operacao`, `_bndt_selecionar_operacao_para_polo`, `_bndt_processar_selecoes`, `_bndt_processar_selecoes_polo`, `_bndt_gravar_e_confirmar`, `_bndt_gravar_e_confirmar_polo`

### 📄 `Fix\extracao_documento.py`
- **Funções:** `extrair_direto`, `_normalizar_texto_decisao`, `_extrair_linha_tipo`, `_extrair_formatar_texto`, `_extrair_info_documento`, `_extrair_via_pdf_viewer`, `_extrair_via_iframe`, `_extrair_via_elemento_dom`, `extrair_documento`, `extrair_pdf`

### 📄 `Fix\extracao_indexacao.py`
- **Funções:** `filtrofases`, `indexar_processos`, `reindexar_linha`, `abrir_detalhes_processo`, `trocar_para_nova_aba`, `_indexar_preparar_contexto`, `_indexar_tentar_reindexar`, `_indexar_tentar_trocar_aba`, `obter_linhas_frescas`

### 📄 `Fix\extracao_indexacao_fluxo.py`
- **Funções:** `_indexar_processar_item`, `indexar_e_processar_lista`, `callback_wrapper`

### 📄 `Fix\extracao_processo.py`
- **Funções:** `extrair_dados_processo`, `extrair_destinatarios_decisao`, `salvar_destinatarios_cache`, `carregar_destinatarios_cache`, `get_cookies_dict`, `extrair_numero_processo_url`, `extrair_trt_host`, `obter_id_processo_via_api`, `obter_dados_processo_via_api`, `criar_pessoa_limpa`

### 📄 `Fix\headless_helpers.py`
- **Funções:** `limpar_overlays_headless`, `scroll_to_element_safe`, `click_headless_safe`, `wait_and_click_headless`, `find_element_headless_safe`, `executar_com_retry_headless`, `is_headless_mode`, `aguardar_elemento_headless_safe`

### 📄 `Fix\log.py`
- **Funções:** `_log_info(msg: str, driver: WebDriver = None) -> None`, `_log_error(msg: str, driver: WebDriver = None) -> None`, `_audit(msg: str) -> None`, `__init__(name: str, level: int = logging.INFO)`, `info(msg: str)`, `error(msg: str)`, `debug(msg: str)`, `warning(msg: str)`

### 📄 `Fix\monitoramento_progresso_unificado.py`
- **Funções:** `_log_progresso`, `_validar_tipo_execucao`, `_validar_e_limpar_progresso`, `carregar_progresso_unificado`, `salvar_progresso_unificado`, `limpar_progresso_corrompido`, `extrair_numero_processo_unificado`, `verificar_acesso_negado_unificado`, `processo_ja_executado_unificado`, `processo_tem_erro_unificado`, `marcar_processo_executado_unificado`, `executar_com_monitoramento_unificado`, `carregar_progresso_p2b`, `salvar_progresso_p2b`, `extrair_numero_processo_p2b`, `verificar_acesso_negado_p2b`, `processo_ja_executado_p2b`, `marcar_processo_executado_p2b`, `carregar_progresso`, `salvar_progresso`, `extrair_numero_processo`, `verificar_acesso_negado`, `processo_ja_executado`, `marcar_processo_executado`, `carregar_progresso_mandado`, `salvar_progresso_mandado`, `extrair_numero_processo_mandado`, `verificar_acesso_negado_mandado`, `processo_ja_executado_mandado`, `marcar_processo_executado_mandado`, `exemplo_uso_monitoramento_unificado`, `__init__`, `carregar_progresso`, `salvar_progresso`, `processo_ja_executado`, `marcar_progresso_executado`, `marcar_processo_executado`

### 📄 `Fix\movimento_helpers.py`
- **Funções:** `_normalize_text`, `selecionar_movimento_dois_estagios`, `selecionar_movimento_auto`

### 📄 `Fix\otimizacao_wrapper.py`
- **Funções:** `with_learning`, `usar_headless_safe`, `inicializar_otimizacoes`, `finalizar_otimizacoes`, `decorator`, `wrapper`

### 📄 `Fix\progresso_unificado.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\selectors_pje.py`
- **Funções:** `seletor_processo_por_numero`, `seletor_pec_por_numero`, `buscar_seletor_robusto`

### 📄 `Fix\utils.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\utils_angular.py`
- **Funções:** `aguardar_angular_carregar`, `aguardar_angular_requests`, `clicar_elemento_angular`, `preencher_campo_angular`, `aguardar_elemento_angular_visivel`, `verificar_angular_app`, `aguardar_angular_digest`, `obter_angular_scope`, `executar_angular_expressao`

### 📄 `Fix\utils_collect.py`
- **Funções:** `coletar_texto_seletor`, `coletar_valor_atributo`, `coletar_multiplos_elementos`, `coletar_tabela_como_lista`, `coletar_links_pagina`, `coletar_dados_formulario`, `extrair_numero_processo`, `extrair_cpf_cnpj`, `coletar_dados_pagina`

### 📄 `Fix\utils_collect_content.py`
- **Funções:** `_log_msg_coleta`, `coletar_conteudo_formatado_documento`, `coletar_conteudo_js`, `coletar_elemento_css`, `executar_coleta_parametrizavel`, `log_msg`, `log_msg`, `log_msg`

### 📄 `Fix\utils_collect_timeline.py`
- **Funções:** `_log_msg_coleta`, `coletar_link_ato_timeline`, `log_msg`

### 📄 `Fix\utils_cookies.py`
- **Funções:** `carregar_cookies_sessao`, `verificar_e_aplicar_cookies`, `salvar_cookies_sessao`, `limpar_cookies_antigos`, `listar_cookies_salvos`, `__init__`, `get_delay`

### 📄 `Fix\utils_driver_legacy.py`
- **Funções:** `obter_driver_padronizado`, `driver_pc`, `navegar_para_tela`

### 📄 `Fix\utils_drivers.py`
- **Funções:** `_obter_caminhos_ahk`, `criar_driver_firefox`, `criar_driver_PC`, `criar_driver_VT`, `criar_driver_notebook`, `criar_driver_sisb_pc`, `criar_driver_sisb_notebook`, `configurar_driver_avancado`, `verificar_driver_ativo`, `fechar_driver_safely`, `limpar_temp_selenium`

### 📄 `Fix\utils_editor.py`
- **Funções:** `_get_editable`, `_place_selection_at_marker`, `inserir_html_editor`, `inserir_texto_editor`, `obter_ultimo_conteudo_clipboard`, `inserir_link_ato`, `inserir_html_no_editor_apos_marcador`, `inserir_link_ato_validacao`, `inserir_conteudo_formatado`, `_norm`

### 📄 `Fix\utils_error.py`
- **Funções:** `__init__`, `registrar_erro`, `registrar_sucesso`, `gerar_relatorio`, `exportar_csv`

### 📄 `Fix\utils_formatting.py`
- **Funções:** `formatar_moeda_brasileira`, `formatar_data_brasileira`, `normalizar_cpf_cnpj`, `extrair_raiz_cnpj`, `identificar_tipo_documento`

### 📄 `Fix\utils_login.py`
- **Funções:** `login_manual`, `login_automatico`, `login_automatico_direto`, `login_cpf`, `exibir_configuracao_ativa`, `login_pc`

### 📄 `Fix\utils_recovery.py`
- **Funções:** `configurar_recovery_driver`, `verificar_e_tratar_acesso_negado_global`, `handle_exception_with_recovery`

### 📄 `Fix\utils_selectors.py`
- **Funções:** `obter_seletor_pje`, `buscar_seletor_robusto`, `gerar_seletor_dinamico`, `detectar_seletor_elemento`, `validar_seletor`, `encontrar_seletor_estavel`, `criar_seletor_fallback`, `aplicar_estrategia_seletor`

### 📄 `Fix\utils_sleep.py`
- **Funções:** `sleep_random(min_s: float, max_s: float) -> None`, `sleep_fixed(s: float) -> None`, `sleep_adaptativo(contexto: str, fator: float = 1.0) -> None`, `sleep(seconds: float) -> None`, `smart_sleep(seconds: float) -> None`

### 📄 `Fix\variaveis.py`
- **Funções:** `obter_gigs_com_fase`, `session_from_driver`, `obter_codigo_validacao_documento`, `obter_peca_processual_da_timeline`, `resolver_variavel`, `get_all_variables`, `obter_chave_ultimo_despacho_decisao_sentenca`, `obter_texto_documento`, `buscar_atividade_gigs_por_observacao`, `obter_todas_atividades_gigs_com_observacao`, `padrao_liq`, `verificar_bndt`, `__new__`

### 📄 `Fix\variaveis_client.py`
- **Funções:** `session_from_driver`, `__init__`, `_url`, `timeline`, `documento_por_id`, `execucao_gigs`, `processo_por_id`, `partes`, `id_processo_por_numero`, `calculos`, `pericias`, `atividades_gigs`, `debitos_trabalhistas_bndt`

### 📄 `Fix\variaveis_helpers.py`
- **Funções:** `obter_gigs_com_fase`, `obter_texto_documento`, `buscar_atividade_gigs_por_observacao`, `obter_todas_atividades_gigs_com_observacao`, `padrao_liq`, `verificar_bndt`

### 📄 `Fix\variaveis_resolvers.py`
- **Funções:** `obter_codigo_validacao_documento`, `obter_peca_processual_da_timeline`, `resolver_variavel`, `get_all_variables`, `obter_chave_ultimo_despacho_decisao_sentenca`

### 📄 `Fix\documents\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\documents\buttons.py`
- **Funções:** `criar_botoes_detalhes(driver: WebDriver) -> None`

### 📄 `Fix\documents\search.py`
- **Funções:** `verificar_documento_decisao_sentenca(driver: WebDriver) -> bool`, `buscar_ultimo_mandado(driver: WebDriver, log: bool = True) -> Tuple[Optional[str], Optional[str]]`, `buscar_mandado_autor(driver: WebDriver, log: bool = True) -> Optional[Dict[str, str]]`, `buscar_documentos_sequenciais(driver: WebDriver, log: bool = True) -> List[Any]`, `buscar_documentos_polo_ativo(driver: WebDriver, polo: str = "autor", limite_dias: Optional[int] = None, debug: bool = False) -> List[Dict[str, str]]`, `buscar_documento_argos(driver: WebDriver, log: bool = True, ignorar_indices: Optional[List[int]] = None) -> Tuple[Optional[str], Optional[str], Optional[int]]`

### 📄 `Fix\drivers\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\drivers\lifecycle.py`
- **Funções:** `criar_driver_PC(headless: bool = False) -> webdriver.Firefox`, `criar_driver_VT(headless: bool = False) -> webdriver.Firefox`, `criar_driver_notebook(headless: bool = False) -> webdriver.Firefox`, `criar_driver_sisb_pc(headless: bool = False) -> Optional[webdriver.Firefox]`, `criar_driver_sisb_notebook(headless: bool = False) -> webdriver.Firefox`, `finalizar_driver(driver: webdriver.Firefox, log: bool = True) -> bool`

### 📄 `Fix\forms\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\forms\multiple_fields.py`
- **Funções:** `_log_info`, `_log_error`, `_audit`, `preencher_multiplos_campos`

### 📄 `Fix\gigs\__init__.py`
- **Funções:** `_gigs_responsavel_valido(responsavel: Optional[str]) -> bool`, `_parse_gigs_string(string: str) -> Dict[str, Optional[Union[int, str]]]`, `criar_lembrete_posit(driver: WebDriver, titulo: str, conteudo: str, prazo: str = 'LOCAL', salvar: bool = True, debug: bool = False) -> bool`, `criar_gigs(driver: WebDriver, dias_uteis: Optional[Union[int, str]] = None, responsavel: Optional[str] = None, observacao: Optional[str] = None, timeout: int = 10, log: bool = True) -> bool`, `criar_comentario(driver: WebDriver, observacao: str, visibilidade: str = 'LOCAL', timeout: int = 10, log: bool = True) -> bool`

### 📄 `Fix\navigation\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\navigation\filters.py`
- **Funções:** `aplicar_filtro_100(driver: WebDriver) -> bool`, `filtro_fase(driver: WebDriver) -> bool`, `filtrofases(driver: WebDriver, fases_alvo: List[str] = ['liquidação', 'execução'], tarefas_alvo: Optional[List[str]] = None, seletor_tarefa: str = 'Tarefa do processo') -> bool`, `_selecionar() -> bool`

### 📄 `Fix\navigation\sigilo.py`
- **Funções:** `visibilidade_sigilosos(driver: WebDriver, polo: str = 'ativo', log: bool = True) -> bool`

### 📄 `Fix\selenium_base\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\selenium_base\click_operations.py`
- **Funções:** `aguardar_e_clicar(driver: WebDriver, seletor: str, log: bool = False, timeout: int = 10, by: By = By.CSS_SELECTOR, usar_js: bool = True, retornar_elemento: bool = False, debug: Optional[bool] = None) -> Union[bool, Optional[WebElement]]`

### 📄 `Fix\selenium_base\driver_operations.py`
- **Funções:** `criar_driver_PC(headless: bool = False) -> WebDriver`, `criar_driver_VT(headless: bool = False) -> WebDriver`, `criar_driver_notebook(headless: bool = False) -> WebDriver`, `criar_driver_sisb_pc(headless: bool = False) -> Optional[WebDriver]`, `criar_driver_sisb_notebook(headless: bool = False) -> WebDriver`, `finalizar_driver(driver: WebDriver, log: bool = True) -> bool`, `salvar_cookies_sessao(driver: WebDriver, caminho_arquivo: Optional[str] = None, info_extra: Optional[str] = None) -> bool`, `carregar_cookies_sessao(driver: WebDriver, max_idade_horas: int = 24) -> bool`, `credencial(tipo_driver: str = 'PC', tipo_login: str = 'CPF', headless: bool = False, cpf: Optional[str] = None, senha: Optional[str] = None, url_login: Optional[str] = None, max_idade_cookies: int = 24) -> Optional[WebDriver]`

### 📄 `Fix\selenium_base\element_interaction.py`
- **Funções:** `_log_info(msg: str) -> None`, `_log_error(msg: str) -> None`, `_audit(action: str, target: str, status: str, extra: dict = None) -> None`, `js_base() -> str`, `safe_click(driver: WebDriver, selector_or_element: Union[str, WebElement], timeout: int = 10, by: Optional[By] = None, log: bool = False) -> bool`, `preencher_campo(driver: WebDriver, seletor: str, valor: Union[str, int], trigger_events: bool = True, limpar: bool = True, log: bool = False) -> bool`, `preencher_campos_prazo(driver: WebDriver, valor: int = 0, timeout: int = 10, log: bool = True) -> bool`, `preencher_multiplos_campos(driver: WebDriver, campos_dict: Dict[str, Union[str, int]], log: bool = False) -> Dict[str, bool]`, `_clicar_botao_movimentar(driver: WebDriver, timeout: int = 10, log: bool = False) -> bool`, `_clicar_botao_tarefa_processo(driver: WebDriver, timeout: int = 10, log: bool = False) -> bool`, `_tentar_click_padrao(driver: WebDriver, element: WebElement, log: bool, attempt: int) -> bool`, `_tentar_click_javascript(driver: WebDriver, element: WebElement, log: bool) -> bool`, `_tentar_click_actionchains(driver: WebDriver, element: WebElement, log: bool) -> bool`, `_tentar_click_javascript_avancado(driver: WebDriver, element: WebElement, log: bool) -> bool`

### 📄 `Fix\selenium_base\field_operations.py`
- **Funções:** `preencher_campo(driver: WebDriver, seletor: str, valor: Union[str, int], trigger_events: bool = True, limpar: bool = True, log: bool = False) -> bool`

### 📄 `Fix\selenium_base\js_helpers.py`
- **Funções:** `js_base() -> str`

### 📄 `Fix\selenium_base\retry_logic.py`
- **Funções:** `_log_info(msg: str) -> None`, `com_retry(func: Callable[..., T], max_tentativas: int = 3, backoff_base: int = 2, log_enabled: bool = False, *args: Any, **kwargs: Any) -> Optional[T]`, `buscar_seletor_robusto(driver: WebDriver, textos: List[str], contexto: Optional[Any] = None, timeout: int = 5, log: bool = False) -> Optional[WebElement]`, `buscar_input_associado(elemento: WebElement) -> Optional[WebElement]`

### 📄 `Fix\selenium_base\smart_selection.py`
- **Funções:** `selecionar_opcao(driver: WebDriver, seletor_dropdown: Optional[str], texto_opcao: str, timeout: int = 10, exato: bool = False, log: bool = False) -> bool`, `_tentar_selecionar_com_seletor(driver: WebDriver, seletor: str, texto_opcao: str, exato: bool, log: bool, timeout: int = 10) -> bool`, `_tentar_selecionar_via_painel(driver: WebDriver, texto_opcao: str, log: bool) -> bool`, `_tentar_selecionar_via_javascript(driver: WebDriver, seletores_possiveis: Optional[List[str]], texto_opcao: str, log: bool) -> bool`, `escolher_opcao_inteligente(driver: WebDriver, valor: str, estrategias_custom: Optional[List[Tuple[By, str]]] = None, debug: bool = False) -> bool`, `encontrar_elemento_inteligente(driver: WebDriver, valor: str, estrategias_custom: Optional[List[Tuple[By, str]]] = None, debug: bool = False) -> Optional[WebElement]`, `buscar_seletor_robusto(driver: WebDriver, textos: List[str], contexto=None, timeout: int = 5, log: bool = False) -> Optional[WebElement]`, `buscar_input_associado(elemento: WebElement) -> Optional[WebElement]`

### 📄 `Fix\selenium_base\wait_operations.py`
- **Funções:** `_log_info(msg: str) -> None`, `wait(driver: WebDriver, selector: str, timeout: int = 10, by: By = By.CSS_SELECTOR) -> Optional[WebElement]`, `wait_for_visible(driver: WebDriver, selector: str, timeout: int = 10, by: Optional[By] = None) -> Optional[WebElement]`, `wait_for_clickable(driver: WebDriver, selector: str, timeout: int = 10, by: Optional[By] = None) -> Optional[WebElement]`, `esperar_elemento(driver: WebDriver, seletor: str, texto: Optional[str] = None, timeout: int = 10, by: By = By.CSS_SELECTOR, log: bool = False) -> Optional[WebElement]`, `aguardar_e_clicar(driver: WebDriver, seletor: str, log: bool = False, timeout: int = 10, by: By = By.CSS_SELECTOR, usar_js: bool = True, retornar_elemento: bool = False, debug: Optional[bool] = None) -> Union[bool, Optional[WebElement]]`, `esperar_url_conter(driver: WebDriver, substring: str, timeout: int = 10) -> bool`, `_aguardar_loader_painel(driver: WebDriver, timeout: int = 10) -> None`

### 📄 `Fix\session\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Fix\session\auth.py`
- **Funções:** `salvar_cookies_sessao(driver: WebDriver, caminho_arquivo: Optional[str] = None, info_extra: Optional[str] = None) -> bool`, `carregar_cookies_sessao(driver: WebDriver, max_idade_horas: int = 24) -> bool`, `credencial(tipo_driver: str = 'PC', tipo_login: str = 'CPF', headless: bool = False, cpf: Optional[str] = None, senha: Optional[str] = None, url_login: Optional[str] = None, max_idade_cookies: int = 24) -> Optional[WebDriver]`, `verificar_e_aplicar_cookies(driver: WebDriver) -> bool`

## 📂 PEC

### 📄 `PEC\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `PEC\ajuste_gigs.py`
- **Funções:** `def_ajustegigs`, `log_msg`

### 📄 `PEC\carta.py`
- **Funções:** `carta`

### 📄 `PEC\carta_ecarta.py`
- **Funções:** `_texto_e_correio`, `_extrair_texto_completo`, `_processar_item`, `coletar_intimacoes`, `coletar_tabela_ecarta`

### 📄 `PEC\carta_formatacao.py`
- **Funções:** `gerar_html_carta_para_juntada`, `formatar_dados_ecarta`

### 📄 `PEC\carta_utils.py`
- **Funções:** `_carregar_calendario_dias_uteis`, `_somar_dias_uteis`, `_parse_data_ecarta`, `_obter_numero_processo`

### 📄 `PEC\core.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `PEC\core_main.py`
- **Funções:** `main`, `recovery_credencial`

### 📄 `PEC\core_navegacao.py`
- **Funções:** `navegar_para_atividades`, `aplicar_filtro_xs`, `indexar_processo_atual_gigs`

### 📄 `PEC\core_pos_carta.py`
- **Funções:** `analisar_documentos_pos_carta`, `log_msg`

### 📄 `PEC\core_progresso.py`
- **Funções:** `carregar_progresso_pec`, `salvar_progresso_pec`, `extrair_numero_processo_pec`, `verificar_acesso_negado_pec`, `processo_ja_executado_pec`, `marcar_processo_executado_pec`

### 📄 `PEC\core_recovery.py`
- **Funções:** `verificar_e_recuperar_acesso_negado`, `reiniciar_driver_e_logar_pje`

### 📄 `PEC\executor.py`
- **Funções:** `chamar_funcao_com_assinatura_correta(fn: Callable, driver_pje: WebDriver, dados: Dict[str, Any], driver_sisb: Optional[WebDriver] = None) -> Any`, `executar_acao(driver_pje: WebDriver, acao: Dict[str, Any], driver_sisb: Optional[WebDriver] = None) -> bool`

### 📄 `PEC\helpers.py`
- **Funções:** `remover_acentos`, `normalizar_texto`, `gerar_regex_geral`

### 📄 `PEC\matcher.py`
- **Funções:** `_build_action_rules`, `get_cached_rules`, `get_action_rules`, `determinar_acoes_por_observacao`, `determinar_acao_por_observacao`, `_attr`, `_gigs_edital_intimacao`

### 📄 `PEC\petjs.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `PEC\prescricao.py`
- **Funções:** `def_presc`, `log_msg`

### 📄 `PEC\processamento.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `PEC\processamento_backup.py`
- **Funções:** `executar_acao`, `processar_processo_pec_individual`, `executar_fluxo_robusto`, `executar_fluxo_novo`, `_configurar_driver`, `_navegar_atividades`, `_aplicar_filtros`, `_organizar_e_executar_buckets`, `criar_lista_sisbajud`, `executar_lista_sisbajud_por_abas`, `criar_lista_resto`, `_indexar_todos_processos`, `_filtrar_por_observacao`, `_salvar_amostra_debug_rows`, `_filtrar_por_progresso`, `_filtrar_por_acoes_validas`, `_agrupar_em_buckets`, `_executar_dry_run`, `_processar_buckets`, `_processar_bucket_generico`, `_processar_bucket_demais`, `_processar_bucket_sisbajud`, `_imprimir_relatorio_final`, `indexar_e_criar_buckets_unico`, `chamar_funcao_com_assinatura_correta`, `callback_pec_centralizado`

### 📄 `PEC\processamento_base.py`
- **Funções:** `_lazy_import_pec`, `executar_acao`, `processar_processo_pec_individual`

### 📄 `PEC\processamento_buckets.py`
- **Funções:** `_formatar_nome_acao`, `_processar_buckets`, `_processar_bucket_generico`, `_processar_bucket_demais`, `_processar_bucket_sisbajud`, `_imprimir_relatorio_final`, `_solicitar_reinicio_por_stale`

### 📄 `PEC\processamento_fluxo.py`
- **Funções:** `executar_fluxo_robusto(driver: WebDriver, config: Dict[str, Any]) -> ResultadoProcessamento`, `executar_fluxo_novo(...) -> ResultadoProcessamento`, `callback_pec_centralizado(driver: WebDriver, acao: Dict[str, Any], driver_sisb: Optional[WebDriver] = None) -> bool`

### 📄 `PEC\processamento_indexacao.py`
- **Funções:** `_indexar_todos_processos(driver: WebDriver) -> Optional[List[Dict[str, Any]]]`, `_filtrar_por_observacao`, `_salvar_amostra_debug_rows`, `_filtrar_por_progresso`, `_filtrar_por_acoes_validas`, `_agrupar_em_buckets`, `_executar_dry_run`, `indexar_e_criar_buckets_unico(driver: Union[WebDriver, str], filtros_observacao: Optional[List[str]] = None, dry_run: bool = False) -> Union[bool, Dict[str, List[Dict[str, Any]]]]`

### 📄 `PEC\processamento_listas.py`
- **Funções:** `criar_lista_sisbajud`, `executar_lista_sisbajud_por_abas`, `criar_lista_resto`

### 📄 `PEC\regras.py`
- **Funções:** `executar_acao_pec`, `chamar_funcao_com_assinatura_correta`, `def_sob`, `def_presc`, `def_ajustegigs`, `get_or_create_driver_sisbajud`, `fechar_driver_sisbajud_global`

### 📄 `PEC\sisbajud_driver.py`
- **Funções:** `get_or_create_driver_sisbajud`, `fechar_driver_sisbajud_global`

### 📄 `PEC\sobrestamento.py`
- **Funções:** `def_sob`, `log_msg`, `remover_acentos`, `normalizar_texto`, `gerar_regex_geral`, `executar_mov_sob_retorno_feito`, `executar_penhora_rosto`, `executar_mov_sob_precatorio`, `executar_juizo_universal`, `executar_def_presc`, `executar_ato_prov`

### 📄 `PEC\test_leitura_real.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `PEC\test_pet2.py`
- **Funções:** `parse_test_data`, `create_peticao_linha`, `test_petition`, `print_test_results`, `main`

### 📄 `PEC\test_pet2_real.py`
- **Funções:** `extrair_peticoes_html`, `testar_peticao`, `main`

### 📄 `PEC\anexos\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `PEC\anexos\anexos_configuracao.py`
- **Funções:** `salvar_conteudo_clipboard`

### 📄 `PEC\anexos\anexos_extracao.py`
- **Funções:** `extrair_numero_processo_da_pagina(driver: WebDriver, debug: bool = True) -> Optional[str]`, `extrair_numero_processo_da_url(driver: WebDriver) -> str`

### 📄 `PEC\anexos\anexos_formatacao.py`
- **Funções:** `formatar_conteudo_ecarta`

### 📄 `PEC\anexos\anexos_gigs.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `PEC\anexos\anexos_juntador.py`
- **Funções:** `wrapper_juntada_geral(driver: WebDriver, tipo: str = 'Certidão', descricao: Optional[str] = None, sigilo: str = 'nao', modelo: Optional[str] = None, inserir_conteudo: Optional[Callable] = None, assinar: str = 'nao', coleta_conteudo: Optional[str] = None, substituir_link: bool = False, debug: bool = True) -> bool`, `create_juntador(driver: WebDriver) -> Any`, `executar_juntada_ate_editor(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool`, `executar_juntada(self: types.SimpleNamespace, configuracao: Dict[str, Any], substituir_link: bool = False) -> bool`

### 📄 `PEC\anexos\anexos_juntador_base.py`
- **Funções:** `wrapper_juntada_geral`, `create_juntador`, `executar_juntada_ate_editor`, `executar_juntada`

### 📄 `PEC\anexos\anexos_juntador_helpers.py`
- **Funções:** `_abrir_interface_anexacao(self: types.SimpleNamespace) -> bool`, `_preencher_campos_basicos(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool`, `_inserir_modelo(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool`, `substituir_marcador_por_conteudo(driver: WebDriver, conteudo_customizado: Optional[str] = None, debug: bool = True, marcador: str = "--") -> bool`, `carregar_clipboard_arquivo(caminho: str) -> str`, `_condicao_html(texto: str) -> bool`

### 📄 `PEC\anexos\anexos_juntador_metodos.py`
- **Funções:** `_escolher_opcao_gigs`, `_preencher_input_gigs`, `_clicar_elemento_gigs`, `_selecionar_modelo_gigs`, `_executar_coleta_opcional`, `_preencher_tipo`, `_preencher_descricao`, `_configurar_sigilo`, `_selecionar_e_inserir_modelo`, `_inserir_conteudo_customizado`, `_salvar_documento`, `_assinar_se_necessario`

### 📄 `PEC\anexos\anexos_sisbajud.py`
- **Funções:** `_obter_conteudo_relatorio_sisbajud`, `_wrapper_sisbajud_generico`, `inserir_fn`

### 📄 `PEC\anexos\anexos_wrappers.py`
- **Funções:** `carta_wrapper(driver: WebDriver, numero_processo: Optional[str] = None, debug: bool = True, ecarta_html: Optional[str] = None) -> bool`, `consulta_wrapper(driver: WebDriver, numero_processo: Optional[str] = None, debug: bool = True, tipo: str = 'Certidão', descricao: str = 'Consulta SISBAJUD', modelo: str = 'xteim', assinar: str = 'nao', sigilo: str = 'sim') -> bool`, `wrapper_bloqneg(driver: WebDriver, numero_processo: Optional[str] = None, debug: bool = True, tipo: str = 'Certidão', descricao: str = 'Consulta sisbajud NEGATIVA', modelo: str = 'xjsisbneg', assinar: str = 'nao', sigilo: str = 'nao') -> bool`, `wrapper_parcial(driver: WebDriver, numero_processo: Optional[str] = None, debug: bool = True, tipo: str = 'Certidão', descricao: str = 'Consulta sisbajud POSITIVA', modelo: str = 'XSISBPARCIAL', assinar: str = 'nao', sigilo: str = 'nao') -> bool`, `inserir_fn(driver: WebDriver, numero_processo: Optional[str] = None, debug: bool = True) -> bool`

### 📄 `PEC\anexos\core.py`
- *(Sem funções definidas ou erro de parsing)*

## 📂 SISB

### 📄 `SISB\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\batch.py`
- **Funções:** `processar_lote_sisbajud(driver_pje: WebDriver, processos: List[Dict[str, Any]], progresso: Dict[str, Any], fn_reindexar_linha, fn_abrir_detalhes, fn_trocar_aba, fn_ja_executado, fn_marcar_executado, log: bool = True) -> Dict[str, int]`, `_processar_grupo(driver_pje: WebDriver, driver_sisbajud: Optional[WebDriver], processos: List[Dict[str, Any]], tipo: str, fn_executar: Callable, progresso: Dict[str, Any], aba_lista_pje: str, ...) -> Tuple[Optional[WebDriver], Dict[str, int]]`

### 📄 `SISB\core.py`
- **Funções:** `simular_movimento_humano`, `driver_sisbajud`, `login_automatico_sisbajud`, `login_manual_sisbajud`, `salvar_dados_processo_temp`, `iniciar_sisbajud`, `minuta_bloqueio`, `processar_ordem_sisbajud`, `processar_bloqueios`, `processar_endereco`, `coletar_dados_minuta_sisbajud`, `minuta_bloqueio_60`

### 📄 `SISB\helpers.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\helpers_original_backup.py`
- **Funções:** `_validar_dados`, `_preencher_campos_iniciais`, `_processar_reus_otimizado`, `_salvar_minuta`, `_gerar_relatorio_minuta`, `_atualizar_relatorio_com_segundo_protocolo`, `_protocolar_minuta`, `_criar_minuta_agendada_por_copia`, `_criar_minuta_agendada`, `_carregar_dados_ordem`, `_filtrar_series`, `_voltar_para_lista_ordens_serie`, `_voltar_para_lista_principal`, `_navegar_e_extrair_ordens_serie`, `_extrair_ordens_da_serie`, `_aplicar_acao_por_fluxo`, `_identificar_ordens_com_bloqueio`, `_agrupar_dados_bloqueios`, `extrair_dados_bloqueios_processados`, `gerar_relatorio_bloqueios_processados`, `gerar_relatorio_bloqueios_conciso`, `_extrair_nome_executado_serie`, `_processar_series`, `_calcular_estrategia_bloqueio`, `_gerar_relatorio_ordem`, `_executar_juntada_pje`, `criar_js_otimizado`, `extrair_valor_monetario`

### 📄 `SISB\performance.py`
- **Funções:** `optimized_element_wait`, `batched_form_fill`, `cached_selector_lookup`, `parallel_series_processing`, `smart_cache_operation`, `__init__`, `cache_element_selector`, `batch_dom_operations`, `optimize_javascript_execution`, `__init__`, `_create_mutation_observer`, `replace_polling_with_observer`, `__init__`, `cache_element`, `get_cached_element`, `cache_data`, `get_cached_data`, `clear_expired_cache`, `__init__`, `process_series_parallel`

### 📄 `SISB\processamento.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\processamento_campos.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\processamento_campos_principais.py`
- **Funções:** `_preencher_campos_principais`

### 📄 `SISB\processamento_campos_reus.py`
- **Funções:** `_processar_reus_otimizado`, `_configurar_valor`, `_configurar_opcoes_adicionais`

### 📄 `SISB\processamento_extracao.py`
- **Funções:** `_extrair_cpf_autor`, `_extrair_nome_autor`

### 📄 `SISB\processamento_minuta.py`
- **Funções:** `minuta_bloqueio_refatorada`

### 📄 `SISB\processamento_ordens.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\processamento_ordens_extracao.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\processamento_ordens_processamento.py`
- **Funções:** `_processar_ordem`

### 📄 `SISB\processamento_ordens_processamento_auxiliar.py`
- **Funções:** `_processar_ordem_auxiliar`

### 📄 `SISB\processamento_ordens_processamento_principal.py`
- **Funções:** `_processar_ordem_principal`

### 📄 `SISB\processamento_relatorios.py`
- **Funções:** `_salvar_minuta`, `_gerar_relatorio_minuta`, `_salvar_relatorios`, `_finalizar_minuta`

### 📄 `SISB\s_orquestrador.py`
- **Funções:** `criar_js_otimizado_legacy() -> str`, `iniciar_sisbajud_legacy(driver_pje: Optional[WebDriver] = None) -> Optional[WebDriver]`, `minuta_bloqueio_legacy(driver_sisbajud, dados_processo, driver_pje=None, driver_created=False)`, `executar_sisbajud_completo(dados_processo: Dict[str, Any], driver_pje: WebDriver = None, modo: str = "automatico") -> ResultadoProcessamento`, `minuta_bloqueio(...)`, `minuta_endereco(...)`, `processar_ordem_sisbajud(...)`, `processar_bloqueios(...)`, `trigger_event(elemento: WebElement, tipo: str) -> bool`, `safe_execute_script(driver: WebDriver, script: str, *args: Any) -> Any`, `debug_sisbajud_status()`, `otimizar_performance_sisbajud(habilitar: bool = True)`

### 📄 `SISB\sisb.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\standards.py`
- **Funções:** `validar_numero_processo_padronizado`, `formatar_valor_monetario_padronizado`, `calcular_data_limite_padronizada`, `criar_timestamp_padronizado`, `log_operacao`, `validar_parametros`, `retry_on_failure`, `__post_init__`, `__post_init__`, `valor_bloqueado_text`, `valor_bloquear_text`, `__init__`, `log`, `log_erro`, `log_sucesso`, `__init__`, `__init__`, `__init__`, `__init__`, `__init__`, `__init__`, `decorator`, `decorator`, `decorator`, `wrapper`, `wrapper`, `wrapper`

### 📄 `SISB\test_refatoracao.py`
- **Funções:** `run_tests`, `test_constants`, `test_status_processamento`, `test_tipo_fluxo`, `test_dados_processo`, `test_resultado_processamento`, `test_logger`, `test_validar_numero_processo`, `test_formatar_valor_monetario`, `test_criar_js_otimizado`, `test_safe_click`, `test_aguardar_elemento`, `test_performance_optimizer`, `test_cache_manager`, `test_polling_reducer`, `test_executar_sisbajud_completo_sucesso`, `test_executar_sisbajud_completo_erro_inicializacao`, `test_executar_sisbajud_completo_dados_invalidos`, `test_imports_modulares`, `test_compatibilidade_legacy`, `test_func`

### 📄 `SISB\utils.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\utils_refatorado_backup.py`
- **Funções:** `criar_js_otimizado`, `safe_click`, `simulate_human_movement`, `aguardar_elemento`, `aguardar_e_clicar`, `escolher_opcao_sisbajud`, `extrair_protocolo`, `validar_numero_processo`, `formatar_valor_monetario`, `calcular_data_limite`, `criar_timestamp`, `log_sisbajud`, `registrar_erro_minuta`, `mutation_observer_script`, `rate_limiting_manager`, `advanced_dom_manipulator`, `consolidated_js_framework`, `aplicar_rate_limiting`, `detectar_captcha`, `anti_detection_measures`, `smart_wait`

### 📄 `SISB\Core\driver.py`
- **Funções:** `driver_sisbajud`

### 📄 `SISB\Core\login.py`
- **Funções:** `simular_movimento_humano`, `login_automatico_sisbajud`, `login_manual_sisbajud`

### 📄 `SISB\Core\sessao.py`
- **Funções:** `salvar_dados_processo_temp`, `iniciar_sisbajud`

### 📄 `SISB\Core\sessao_helpers.py`
- **Funções:** `_extrair_dados_pje`, `_criar_driver_sisbajud`, `_realizar_login`, `_navegar_minuta`

### 📄 `SISB\Core\utils_const.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\Core\utils_dados.py`
- **Funções:** `extrair_protocolo`, `validar_numero_processo`, `formatar_valor_monetario`, `calcular_data_limite`, `criar_timestamp`, `log_sisbajud`, `registrar_erro_minuta`, `carregar_dados_processo`

### 📄 `SISB\Core\utils_js.py`
- **Funções:** `criar_js_otimizado`, `mutation_observer_script`, `rate_limiting_manager`, `advanced_dom_manipulator`, `consolidated_js_framework`

### 📄 `SISB\Core\utils_web.py`
- **Funções:** `safe_click`, `simulate_human_movement`, `aguardar_elemento`, `aguardar_e_clicar`, `escolher_opcao_sisbajud`, `aplicar_rate_limiting`, `detectar_captcha`, `anti_detection_measures`, `smart_wait`

### 📄 `SISB\core.backup_20260206\driver.py`
- **Funções:** `driver_sisbajud`

### 📄 `SISB\core.backup_20260206\login.py`
- **Funções:** `simular_movimento_humano`, `login_automatico_sisbajud`, `login_manual_sisbajud`

### 📄 `SISB\core.backup_20260206\sessao.py`
- **Funções:** `salvar_dados_processo_temp`, `iniciar_sisbajud`

### 📄 `SISB\core.backup_20260206\sessao_helpers.py`
- **Funções:** `_extrair_dados_pje`, `_criar_driver_sisbajud`, `_realizar_login`, `_navegar_minuta`

### 📄 `SISB\core.backup_20260206\utils_const.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\core.backup_20260206\utils_dados.py`
- **Funções:** `extrair_protocolo`, `validar_numero_processo`, `formatar_valor_monetario`, `calcular_data_limite`, `criar_timestamp`, `log_sisbajud`, `registrar_erro_minuta`, `carregar_dados_processo`

### 📄 `SISB\core.backup_20260206\utils_js.py`
- **Funções:** `criar_js_otimizado`, `mutation_observer_script`, `rate_limiting_manager`, `advanced_dom_manipulator`, `consolidated_js_framework`

### 📄 `SISB\core.backup_20260206\utils_web.py`
- **Funções:** `safe_click`, `simulate_human_movement`, `aguardar_elemento`, `aguardar_e_clicar`, `escolher_opcao_sisbajud`, `aplicar_rate_limiting`, `detectar_captcha`, `anti_detection_measures`, `smart_wait`

### 📄 `SISB\integration\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\integration\pje_integration.py`
- **Funções:** `_atualizar_relatorio_com_segundo_protocolo`, `_executar_juntada_pje`

### 📄 `SISB\minutas\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\minutas\processor.py`
- **Funções:** `_selecionar_prazo_bloqueio`, `_preencher_campos_iniciais`, `_processar_reus_otimizado`, `_salvar_minuta`, `_gerar_relatorio_minuta`, `_protocolar_minuta`, `_criar_minuta_agendada_por_copia`, `_criar_minuta_agendada`

### 📄 `SISB\navigation\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\navigation\navigator.py`
- **Funções:** `_voltar_para_lista_ordens_serie`, `_voltar_para_lista_principal`

### 📄 `SISB\ordens\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\ordens\processor.py`
- **Funções:** `_carregar_dados_ordem`, `_extrair_ordens_da_serie`, `_aplicar_acao_por_fluxo`, `_identificar_ordens_com_bloqueio`

### 📄 `SISB\processamento\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\processamento\integracao.py`
- **Funções:** `_atualizar_relatorio_com_segundo_protocolo`, `_executar_juntada_pje`

### 📄 `SISB\processamento\minutas_agendada.py`
- **Funções:** `_criar_minuta_agendada`

### 📄 `SISB\processamento\minutas_campos.py`
- **Funções:** `_preencher_campos_iniciais`

### 📄 `SISB\processamento\minutas_copia.py`
- **Funções:** `_criar_minuta_agendada_por_copia`

### 📄 `SISB\processamento\minutas_prazo.py`
- **Funções:** `_selecionar_prazo_bloqueio`

### 📄 `SISB\processamento\minutas_protocolo.py`
- **Funções:** `_protocolar_minuta`

### 📄 `SISB\processamento\minutas_relatorio.py`
- **Funções:** `_gerar_relatorio_minuta`

### 📄 `SISB\processamento\minutas_reus.py`
- **Funções:** `_processar_reus_otimizado`

### 📄 `SISB\processamento\minutas_salvar.py`
- **Funções:** `_salvar_minuta`

### 📄 `SISB\processamento\navegacao.py`
- **Funções:** `_voltar_para_lista_ordens_serie`, `_voltar_para_lista_principal`

### 📄 `SISB\processamento\ordens_acao.py`
- **Funções:** `_aplicar_acao_por_fluxo`

### 📄 `SISB\processamento\ordens_dados.py`
- **Funções:** `_carregar_dados_ordem`, `_extrair_ordens_da_serie`, `_identificar_ordens_com_bloqueio`

### 📄 `SISB\processamento\relatorios_dados.py`
- **Funções:** `_agrupar_dados_bloqueios`, `extrair_dados_bloqueios_processados`

### 📄 `SISB\processamento\relatorios_formatacao.py`
- **Funções:** `gerar_relatorio_bloqueios_processados`, `gerar_relatorio_bloqueios_conciso`

### 📄 `SISB\processamento\relatorios_ordem.py`
- **Funções:** `_gerar_relatorio_ordem`

### 📄 `SISB\processamento\series_estrategia.py`
- **Funções:** `_calcular_estrategia_bloqueio`

### 📄 `SISB\processamento\series_filtro.py`
- **Funções:** `_filtrar_series`, `extrair_valor_monetario`

### 📄 `SISB\processamento\series_fluxo.py`
- **Funções:** `_processar_series`

### 📄 `SISB\processamento\series_fluxo_helpers.py`
- **Funções:** `_tratar_ordem_respondida`, `_executar_transferencia`, `_executar_desbloqueio`, `_navegar_pos_ordem`, `_registrar_erro_processar`

### 📄 `SISB\processamento\series_navegar.py`
- **Funções:** `_navegar_e_extrair_ordens_serie`, `_extrair_nome_executado_serie`

### 📄 `SISB\processamento\validacao.py`
- **Funções:** `_validar_dados`

### 📄 `SISB\relatorios\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\relatorios\generator.py`
- **Funções:** `_agrupar_dados_bloqueios`, `extrair_dados_bloqueios_processados`, `gerar_relatorio_bloqueios_processados`, `gerar_relatorio_bloqueios_conciso`, `_gerar_relatorio_ordem`

### 📄 `SISB\series\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\series\processor.py`
- **Funções:** `_filtrar_series`, `_navegar_e_extrair_ordens_serie`, `_extrair_nome_executado_serie`, `_processar_series`, `_calcular_estrategia_bloqueio`, `extrair_valor_monetario`

### 📄 `SISB\validation\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `SISB\validation\processor.py`
- **Funções:** `_validar_dados`

## 📂 atos

### 📄 `atos\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `atos\comunicacao.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `atos\comunicacao_coleta.py`
- **Funções:** `executar_coleta_conteudo`

### 📄 `atos\comunicacao_destinatarios.py`
- **Funções:** `normalizar_string`, `selecionar_destinatario_por_documento`, `selecionar_destinatarios`, `log`

### 📄 `atos\comunicacao_finalizacao.py`
- **Funções:** `alterar_meio_expedicao`, `remover_destinatarios_invalidos`, `salvar_minuta_final`, `log`, `log`, `log`

### 📄 `atos\comunicacao_fluxo.py`
- **Funções:** `comunicacao_judicial(driver: WebDriver, destinatarios: List[str], modelo: str, prazo: int = 0, sigilo: bool = False, pec: bool = False) -> bool`

### 📄 `atos\comunicacao_navigation.py`
- **Funções:** `abrir_minutas`

### 📄 `atos\comunicacao_preenchimento.py`
- **Funções:** `normalizar_string`, `preencher_input_js`, `escolher_opcao_select_js`, `clicar_radio_button_js`, `executar_preenchimento_minuta`, `log`

### 📄 `atos\core.py`
- **Funções:** `selecionar_opcao_select`, `verificar_carregamento_pagina`, `aguardar_e_verificar_aba`, `verificar_carregamento_detalhe`, `aguardar_e_verificar_detalhe`

### 📄 `atos\judicial.py`
- **Funções:** `fluxo_cls`, `ato_judicial`, `make_ato_wrapper`, `ato_pesquisas`, `idpj`, `preencher_prazos_destinatarios`, `verificar_bloqueio_recente`

### 📄 `atos\judicial_ato.py`
- **Funções:** `ato_judicial(driver: WebDriver, tipo_ato: str, modelo_ato: str, prazo_dias: Optional[int] = None) -> bool`, `make_ato_wrapper(tipo: str) -> Callable`

### 📄 `atos\judicial_fluxo.py`
- **Funções:** `fluxo_cls`

### 📄 `atos\judicial_helpers.py`
- **Funções:** `ato_pesquisas`, `idpj`, `preencher_prazos_destinatarios`, `verificar_bloqueio_recente`

### 📄 `atos\movimentos.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `atos\movimentos_chips.py`
- **Funções:** `def_chip`, `log_msg`

### 📄 `atos\movimentos_despacho.py`
- **Funções:** `despacho_generico`

### 📄 `atos\movimentos_fimsob.py`
- **Funções:** `mov_fimsob`, `log_msg`

### 📄 `atos\movimentos_fluxo.py`
- **Funções:** `mov_simples`, `mov`, `log_debug`, `log_debug`, `buscar_aba_detalhe`, `tentar_encontrar_alvo`

### 📄 `atos\movimentos_sobrestamento.py`
- **Funções:** `mov_sob`, `log_msg`, `garantir_aba_detalhe`

### 📄 `atos\wrappers_ato.py`
- **Funções:** `ato_meios`, `ato_ratif`, `ato_100`, `ato_unap`, `ato_crda`, `ato_crte`, `ato_bloq`, `ato_idpj`, `ato_termoE`, `ato_termoS`, `ato_edital`, `ato_sobrestamento`, `ato_prov`, `ato_180`, `ato_x90`, `ato_pesqliq_original`, `ato_pesqliq`, `ato_calc2`, `ato_meiosub`, `ato_presc`, `ato_fal`, `ato_parcela`, `ato_prev`, `ato_concor`, `ato_prevjud`, `_inserir_relatorio_conciso_sisbajud`

### 📄 `atos\wrappers_mov.py`
- **Funções:** `mov_arquivar`, `mov_exec`, `mov_aud`, `mov_prazo`

### 📄 `atos\wrappers_pec.py`
- **Funções:** `wrapper_pec_ord_com_domicilio`, `wrapper_pec_sum_com_domicilio`

### 📄 `atos\wrappers_utils.py`
- **Funções:** `esperar_insercao_modelo`, `visibilidade_sigilosos`, `executar_visibilidade_sigilosos_se_necessario`, `preparar_campo_filtro_modelo`

## 📂 Mandado

### 📄 `Mandado\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Mandado\core.py`
- **Funções:** `setup_driver() -> Optional[WebDriver]`, `navegacao(driver: WebDriver) -> bool`, `iniciar_fluxo_robusto(driver: WebDriver) -> Dict[str, Any]`, `main()`, `fluxo_callback(driver: WebDriver, **kwargs) -> bool`, `recovery_credencial(driver: WebDriver)`

### 📄 `Mandado\log.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Mandado\processamento.py`
- **Funções:** `_lazy_import_mandado`

### 📄 `Mandado\processamento_anexos.py`
- **Funções:** `_identificar_tipo_anexo`, `_aguardar_icone_plus`, `_buscar_icone_plus_direto`, `_localizar_modal_visibilidade`, `_processar_modal_visibilidade`, `_extrair_resultado_sisbajud`, `_extrair_executados_pdf`, `processar_sisbajud`, `tratar_anexos_argos`, `_buscar_modal`

### 📄 `Mandado\processamento_argos.py`
- **Funções:** `processar_argos(driver: WebDriver, log: bool = False) -> bool`

### 📄 `Mandado\processamento_fluxo.py`
- **Funções:** `fluxo_mandado`, `remover_acentos`, `fluxo_callback`

### 📄 `Mandado\processamento_outros.py`
- **Funções:** `ultimo_mdd(driver: WebDriver, log: bool = True) -> Tuple[Optional[str], Optional[Any]]`, `fluxo_mandados_outros(driver: WebDriver, log: bool = True) -> None`, `analise_padrao(texto: str) -> Optional[bool]`

### 📄 `Mandado\regras.py`
- **Funções:** `_lazy_import_mandado_regras()`, `estrategia_defiro_instauracao(driver: WebDriver, resultado_sisbajud: Any, sigilo_anexos: Dict[str, str], tipo_documento: str, texto_documento: str, debug: bool = False) -> bool`, `estrategia_despacho_argos(...) -> bool`, `estrategia_infojud(...) -> bool`, `estrategia_decisao_manifestar(...) -> bool`, `estrategia_tendo_em_vista_que(...) -> bool`, `aplicar_regras_argos(driver: WebDriver, resultado_sisbajud: Dict[str, str], sigilo_anexos: Dict[str, str], tipo_documento: str, texto_documento: str, debug: bool = False) -> bool`

### 📄 `Mandado\utils.py`
- **Funções:** `retirar_sigilo_demais_documentos_especificos`, `retirar_sigilo_documentos_especificos`

### 📄 `Mandado\utils_intimacao.py`
- **Funções:** `_selecionar_checkbox_intimacao`, `fechar_intimacao`, `marcado`

### 📄 `Mandado\utils_lembrete.py`
- **Funções:** `lembrete_bloq`

### 📄 `Mandado\utils_sigilo.py`
- **Funções:** `retirar_sigilo`, `retirar_sigilo_fluxo_argos`, `retirar_sigilo_certidao_devolucao_primeiro`, `retirar_sigilo_demais_documentos_especificos`, `retirar_sigilo_documentos_especificos`

## 📂 Prazo

### 📄 `Prazo\__init__.py`
- **Funções:** `loop_prazo`

### 📄 `Prazo\__main__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Prazo\loop.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Prazo\loop_api.py`
- **Funções:** `_selecionar_processos_por_gigs_aj_jt`, `_verificar_processo_tem_xs`, `_verificar_processos_xs_paralelo`, `verificar_um`

### 📄 `Prazo\loop_base.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Prazo\loop_ciclo1.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Prazo\loop_ciclo1_filtros.py`
- **Funções:** `_ciclo1_aplicar_filtro_fases`, `_verificar_quantidade_processos_paginacao`

### 📄 `Prazo\loop_ciclo1_movimentacao.py`
- **Funções:** `_ciclo1_marcar_todas`, `_ciclo1_abrir_suitcase`, `_ciclo1_aguardar_movimentacao_lote`, `_ciclo1_movimentar_destino_providencias`, `_ciclo1_movimentar_destino`, `_ciclo1_retornar_lista`, `_tentar_marcar`, `_tentar_abrir_suitcase`

### 📄 `Prazo\loop_ciclo2_processamento.py`
- **Funções:** `_ciclo2_criar_atividade_xs`, `_ciclo2_movimentar_lote`, `ciclo2_processar_livres_apenas_uma_vez`, `ciclo2_loop_providencias`, `ciclo2`

### 📄 `Prazo\loop_ciclo2_selecao.py`
- **Funções:** `_ciclo2_aplicar_filtros`, `_ciclo2_processar_livres`, `_ciclo2_selecionar_nao_livres`

### 📄 `Prazo\loop_helpers.py`
- **Funções:** `_extrair_numero_processo_da_linha`, `selecionar_processos_nao_livres`

### 📄 `Prazo\p2b_core.py`
- **Funções:** `remover_acentos`, `normalizar_texto`, `gerar_regex_geral`, `parse_gigs_param`, `carregar_progresso_p2b`, `salvar_progresso_p2b`, `marcar_processo_executado_p2b`, `processo_ja_executado_p2b`, `checar_prox`, `ato_pesqliq_callback`, `aplicar`

### 📄 `Prazo\p2b_fluxo.py`
- **Funções:** `fluxo_pz`

### 📄 `Prazo\p2b_fluxo_cabecalho.py`
- **Funções:** `_processar_cabecalho_impugnacoes`, `_processar_checar_cabecalho`, `_executar_visibilidade_sigilosos`

### 📄 `Prazo\p2b_fluxo_documentos.py`
- **Funções:** `_encontrar_documento_relevante`, `_documento_nao_assinado`, `_extrair_texto_documento`, `_extrair_com_extrair_direto`, `_extrair_com_extrair_documento`, `_fechar_aba_processo`

### 📄 `Prazo\p2b_fluxo_helpers.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Prazo\p2b_fluxo_lazy.py`
- **Funções:** `_lazy_import`

### 📄 `Prazo\p2b_fluxo_prescricao.py`
- **Funções:** `prescreve`, `analisar_timeline_prescreve_js_puro`

### 📄 `Prazo\p2b_fluxo_regras.py`
- **Funções:** `_definir_regras_processamento`, `_processar_regras_gerais`

### 📄 `Prazo\p2b_prazo.py`
- **Funções:** `fluxo_prazo(driver: WebDriver, processos: List[Dict[str, Any]], progresso: Dict[str, Any]) -> Dict[str, int]`, `aplicar_filtro_atividades_xs(driver: WebDriver) -> bool`

### 📄 `Prazo\prov.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Prazo\prov_config.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Prazo\prov_driver.py`
- **Funções:** `criar_driver`, `_criar_driver_vt`, `_criar_driver_pc`, `criar_e_logar_driver`

### 📄 `Prazo\prov_fluxo.py`
- **Funções:** `fluxo_prov`, `navegacao_prov`, `selecionar_e_processar`, `aplicar_xs_e_registrar`, `main`, `fluxo_prov_integrado`

## 📂 Peticao

### 📄 `Peticao\__init__.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Peticao\pet.py`
- **Funções:** `navegacao_inicial_pet`, `aplicar_filtro_50`, `reordenar_coluna_tipo_peticao`, `extrair_tabela_peticoes`, `carregar_progresso_pet`, `salvar_progresso_pet`, `marcar_hipotese_executada`, `definir_regras_apagar`, `verifica_condicoes`, `normalizar_texto`, `gerar_regex_flexivel`, `acao_apagar`, `agrupar_por_hipotese`, `executar_grupo_apagar`, `executar_fluxo_pet`, `__init__`, `__repr__`, `gerar_chave_regra`, `_selecionar`

### 📄 `Peticao\pet2.py`
- **Funções:** `normalizar_texto`, `gerar_regex_flexivel`, `campo`, `qualquer_campo`, `criar_acao_gigs`, `criar_acao_padrao_liq`, `definir_regras`, `definir_regras_analise_conteudo`, `verifica_peticao_contra_hipotese`, `verifica_peticao_pericias`, `verifica_peticao_diretos`, `_acao_apagar`, `navegacao_inicial_pet`, `aplicar_filtro_50`, `reordenar_coluna_tipo_peticao`, `extrair_tabela_peticoes`, `extrair_tabela_peticoes_selenium`, `_abrir_detalhe_peticao`, `_fechar_e_voltar_lista`, `processar_analise_pdf`, `_executar_acao_completa`, `classificar_peticoes`, `executar_classificadas`, `clicar_proxima_pagina`, `processar_peticoes_escaninho`, `criar_driver_vt`, `main`, `__init__`, `__repr__`, `_gigs`, `_check`, `_selecionar`

### 📄 `Peticao\pet_novo.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Peticao\petjs.py`
- *(Sem funções definidas ou erro de parsing)*

## 📂 Limpeza

### 📄 `Limpeza\CLEANUP_GUIDE.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Limpeza\EXEMPLO_REFACTORING.py`
- **Funções:** `aguardar_elemento_visivel`, `clicar_com_fallbacks`, `processar_pagina`, `diagnosticar_elemento`, `clicar_e_validar`

### 📄 `Limpeza\LOGGING_STANDARDS.py`
- *(Sem funções definidas ou erro de parsing)*

### 📄 `Limpeza\clean_logs.py`
- **Funções:** `main`, `__init__`, `backup`, `clean_file`, `clean`, `_print_stats`, `restore`

### 📄 `Limpeza\validate_refactoring.py`
- **Funções:** `main`, `__init__`, `check_syntax`, `check_logging_patterns`, `check_imports`, `check_file_sizes`, `print_summary`, `run`

## 📂 cookies_sessoes

## 📂 logs_execucao

