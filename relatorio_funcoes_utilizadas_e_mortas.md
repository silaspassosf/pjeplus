# Relatório de Funções Utilizadas e Mortas

Este relatório detalha as funções efetivamente utilizadas nos fluxos principais de execução (x.py) e as funções que podem ser consideradas mortas nas pastas atos, mandado, prazo e pec.

## 1. Funções Efetivamente Utilizadas

### 1.1. Pasta `atos`

#### 1.1.1. Módulo `judicial.py`
- `ato_pesquisas`
- `preencher_prazos_destinatarios`
- `verificar_bloqueio_recente`

#### 1.1.2. Módulo `judicial_wrappers.py`
- `make_ato_wrapper`

#### 1.1.3. Módulo `movimentos_sobrestamento.py`
- `mov_sob`

#### 1.1.4. Módulo `movimentos_fimsob.py`
- `mov_fimsob`

#### 1.1.5. Módulo `movimentos_chips.py`
- `def_chip`
- `def_chip_custom`

#### 1.1.6. Módulo `movimentos_fluxo.py`
- `_movimento_de_analise`
- `_movimento_comunicacoes`
- `_movimento_arquivo_provisorio`
- `_movimento_sobrestamento_final`
- `_movimento_padrao_para_analise`
- `_movimento_para_analise_se_necessario`
- `_movimento_arquivo`
- `_movimento_iniciar_execucao`
- `_movimento_iniciar_liquidacao`
- `_movimento_remeter`
- `_movimento_prazos_secretaria`
- `_movimento_prazos_gabinete`
- `_movimento_recurso_interno`
- `_movimento_transito_julgado`
- `mov_cls`

#### 1.1.7. Módulo `movimentos_navegacao.py`
- `_obter_tarefa_atual`
- `_obter_nome_tarefa_via_api`
- `_extrair_tarefa_do_dom`
- `_normalizar_tarefa`
- `_deve_interromper_movimento`
- `_esperar_transicao`

#### 1.1.8. Módulo `wrappers_mov.py`
- `mov_arquivar`
- `mov_exec`
- `mov_aud`
- `mov_prazo`
- `mov_para_analise`
- `mov_para_comunicacoes`

#### 1.1.9. Módulo `wrappers_ato.py`
- `_inserir_relatorio_conciso_sisbajud`

#### 1.1.10. Módulo `wrappers_utils.py`
- `esperar_insercao_modelo`
- `visibilidade_sigilosos`
- `executar_visibilidade_sigilosos_se_necessario`
- `preparar_campo_filtro_modelo`

#### 1.1.11. Módulo `comunicacao.py`
- `_extrair_observacao_gigs_vencida_xs_pec`

#### 1.1.12. Módulo `comunicacao_navigation.py`
- `abrir_minutas`

#### 1.1.13. Módulo `comunicacao_finalizacao.py`
- `alterar_meio_expedicao`
- `remover_destinatarios_invalidos`
- `salvar_minuta_final`
- `limpar_destinatarios_existentes`

#### 1.1.14. Módulo `comunicacao_destinatarios.py`
- `normalizar_string`
- `_normalizar_nome_para_match`
- `_partial_name_match`
- `_carregar_dadosatuais_local`
- `_montar_destinatarios_por_observacao`
- `_clicar_polo_passivo`
- `_clicar_botao_polo_passivo`
- `selecionar_destinatario_por_documento`
- `_selecionar_por_lista`
- `selecionar_destinatarios`

#### 1.1.15. Módulo `comunicacao_coleta.py`
- `executar_coleta_conteudo`

#### 1.1.16. Módulo `comunicacao_preenchimento.py`
- `normalizar_string`
- `preencher_input_js`
- `escolher_opcao_select_js`
- `clicar_radio_button_js`

#### 1.1.17. Módulo `oficio.py`
- `_carregar_storage_oficio`
- `_salvar_storage_oficio`
- `dados`
- `mail`
- `mailVT`
- `minuta`
- `info`
- `oficio`

### 1.2. Pasta `mandado`

#### 1.2.1. Módulo `core.py`
- `_aguardar_estabilizacao_pos_processo`
- `setup_driver`
- `navegacao`
- `iniciar_fluxo_robusto`
- `main`

#### 1.2.2. Módulo `processamento.py`
- `_lazy_import_mandado`
- `processar_argos`

#### 1.2.3. Módulo `processamento_argos.py`
- `processar_argos`

#### 1.2.4. Módulo `processamento_anexos.py`
- `_identificar_tipo_anexo`
- `_aguardar_icone_plus`
- `_buscar_icone_plus_direto`
- `_localizar_modal_visibilidade`
- `_processar_modal_visibilidade`
- `_extrair_resultado_sisbajud`
- `_extrair_executados_pdf`
- `processar_sisbajud`
- `tratar_anexos_argos`

#### 1.2.5. Módulo `processamento_fluxo.py`
- `fluxo_mandado`

#### 1.2.6. Módulo `processamento_outros.py`
- `ultimo_mdd`
- `fluxo_mandados_outros`

#### 1.2.7. Módulo `regras.py`
- `_lazy_import_mandado_regras`
- `_normalizar_texto_match`
- `_carregar_reus_dadosatuais`
- `_identificar_destinatarios_idpj`
- `estrategia_defiro_instauracao`
- `estrategia_despacho_argos`
- `estrategia_infojud`
- `estrategia_decisao_manifestar`
- `estrategia_tendo_em_vista_que`

#### 1.2.8. Módulo `utils_intimacao.py`
- `_selecionar_checkbox_intimacao`
- `fechar_intimacao`

#### 1.2.9. Módulo `utils_lembrete.py`
- `lembrete_bloq`

#### 1.2.10. Módulo `utils.py`
- `retirar_sigilo_demais_documentos_especificos`
- `retirar_sigilo_documentos_especificos`

#### 1.2.11. Módulo `utils_sigilo.py`
- `retirar_sigilo`
- `retirar_sigilo_fluxo_argos`
- `retirar_sigilo_certidao_devolucao_primeiro`
- `retirar_sigilo_demais_documentos_especificos`
- `retirar_sigilo_documentos_especificos`

### 1.3. Pasta `prazo`

#### 1.3.1. Módulo `criteria_matcher.py`
- `__init__`
- `buscar_prazo_ativo`
- `buscar_prazo_por_tipo`
- `buscar_primeiro_prazo`
- `_extrair_dados_pagina`
- `_extrair_prazos_tabela`
- `_ir_proxima_pagina`
- `_obter_numero_pagina`
- `_obter_total_paginas`
- `_prazo_vencido`
- `_timestamp_atual`

#### 1.3.2. Módulo `loop_api.py`
- `_selecionar_processos_por_gigs_aj_jt`
- `_verificar_processo_tem_xs`
- `_verificar_processos_xs_paralelo`

#### 1.3.3. Módulo `loop_ciclo2_selecao.py`
- `_ciclo2_aplicar_filtros`
- `_ciclo2_processar_livres`
- `_ciclo2_selecionar_nao_livres`

#### 1.3.4. Módulo `loop_ciclo2_processamento.py`
- `_ciclo2_criar_atividade_xs`
- `_ciclo2_movimentar_lote`
- `ciclo2_processar_livres_apenas_uma_vez`
- `ciclo2_loop_providencias`
- `ciclo2`

#### 1.3.5. Módulo `loop_ciclo1_movimentacao.py`
- `_ciclo1_marcar_todas`
- `_ciclo1_abrir_suitcase`
- `_ciclo1_aguardar_movimentacao_lote`
- `_ciclo1_movimentar_destino_providencias`
- `_ciclo1_movimentar_destino`
- `_ciclo1_retornar_lista`

#### 1.3.6. Módulo `loop_ciclo1_filtros.py`
- `_ciclo1_aplicar_filtro_fases`
- `_verificar_quantidade_processos_paginacao`

#### 1.3.7. Módulo `loop_ciclo1.py`
- `ciclo1`

#### 1.3.8. Módulo `loop_base.py`
- `pausar_confirmacao`
- `log_seletor_vencedor`
- `medir_latencia`

#### 1.3.9. Módulo `p2b_fluxo_regras.py`
- `_definir_regras_processamento`
- `_processar_regras_gerais`

#### 1.3.10. Módulo `__init__.py`
- `loop_prazo`

#### 1.3.11. Módulo `p2b_fluxo_prescricao.py`
- `prescreve`
- `analisar_timeline_prescreve_js_puro`

#### 1.3.12. Módulo `p2b_fluxo_lazy.py`
- `_lazy_import`

#### 1.3.13. Módulo `prov_fluxo.py`
- `fluxo_prov`
- `navegacao_prov`
- `selecionar_e_processar`
- `aplicar_xs_e_registrar`
- `main`
- `fluxo_prov_integrado`

#### 1.3.14. Módulo `p2b_fluxo_helpers.py`
- `obter_fase_processual`
- `inicar_exec`

#### 1.3.15. Módulo `prov_driver.py`
- `criar_driver`
- `_criar_driver_vt`
- `_criar_driver_pc`
- `criar_e_logar_driver`

#### 1.3.16. Módulo `p2b_fluxo_documentos.py`
- `_encontrar_documento_relevante`
- `_documento_nao_assinado`
- `_extrair_texto_documento`
- `_extrair_com_extrair_direto`
- `_extrair_com_extrair_documento`
- `_fechar_aba_processo`

#### 1.3.17. Módulo `loop_helpers.py`
- `_extrair_numero_processo_da_linha`
- `selecionar_processos_nao_livres`

#### 1.3.18. Módulo `loop_ciclo3.py`
- `ciclo3`

#### 1.3.19. Módulo `p2b_fluxo.py`
- `fluxo_pz`

#### 1.3.20. Módulo `p2b_core.py`
- `remover_acentos`
- `normalizar_texto`
- `gerar_regex_geral`
- `parse_gigs_param`
- `carregar_progresso_p2b`
- `salvar_progresso_p2b`
- `marcar_processo_executado_p2b`
- `processo_ja_executado_p2b`
- `checar_prox`
- `ato_pesqliq_callback`

#### 1.3.21. Módulo `p2b_prazo.py`
- `fluxo_prazo`
- `executar_prazo_com_otimizacoes`
- `aplicar_filtro_atividades_xs`
- `_wait_linhas_estaveis`
- `_indexar_processos_lista`
- `_filtrar_processos_nao_executados`
- `_processar_lista_processos`
- `_processar_item_prazo`
- `_processar_processo_individual`
- `_reindexar_linha_se_necessario`
- `_executar_callback_processo`
- `_gerenciar_abas_apos_processo`

### 1.4. Pasta `pec`

#### 1.4.1. Módulo `carta_utils.py`
- `_carregar_calendario_dias_uteis`
- `_somar_dias_uteis`
- `_parse_data_ecarta`
- `_obter_numero_processo`

#### 1.4.2. Módulo `matcher.py`
- `_build_action_rules`
- `get_cached_rules`
- `get_action_rules`
- `determinar_acoes_por_observacao`
- `determinar_acao_por_observacao`

#### 1.4.3. Módulo `carta_formatacao.py`
- `gerar_html_carta_para_juntada`
- `formatar_dados_ecarta`

#### 1.4.4. Módulo `carta_ecarta.py`
- `_texto_e_correio`
- `_extrair_texto_completo`
- `_processar_item`
- `coletar_intimacoes`
- `coletar_tabela_ecarta`

#### 1.4.5. Módulo `sobrestamento.py`
- `def_sob`

#### 1.4.6. Módulo `carta.py`
- `carta`

#### 1.4.7. Módulo `sisbajud_driver.py`
- `get_or_create_driver_sisbajud`
- `fechar_driver_sisbajud_global`

#### 1.4.8. Módulo `processamento_listas.py`
- `criar_lista_sisbajud`
- `executar_lista_sisbajud_por_abas`
- `criar_lista_resto`

#### 1.4.9. Módulo `processamento_indexacao.py`
- `_indexar_todos_processos`
- `_filtrar_por_observacao`
- `_salvar_amostra_debug_rows`
- `_filtrar_por_progresso`
- `_filtrar_por_acoes_validas`
- `_agrupar_em_buckets`
- `_executar_dry_run`
- `indexar_e_criar_buckets_unico`

#### 1.4.10. Módulo `processamento_fluxo.py`
- `executar_fluxo_robusto`
- `executar_fluxo_novo`
- `_configurar_driver`
- `_navegar_atividades`
- `_aplicar_filtros`
- `_organizar_e_executar_buckets`

#### 1.4.11. Módulo `processamento_buckets.py`
- `_processar_buckets`
- `_processar_item_pec`
- `_processar_bucket_generico`
- `_processar_bucket_demais`
- `_processar_bucket_sisbajud`
- `_imprimir_relatorio_final`

#### 1.4.12. Módulo `processamento_base.py`
- `_lazy_import_pec`
- `executar_acao`
- `processar_processo_pec_individual`

#### 1.4.13. Módulo `prescricao.py`
- `def_presc`

#### 1.4.14. Módulo `helpers.py`
- `remover_acentos`
- `normalizar_texto`
- `gerar_regex_geral`

#### 1.4.15. Módulo `executor.py`
- `_get_func_label`
- `_executar_funcao`

#### 1.4.16. Módulo `petjs.py`
- `criar_driver_vt`
- `aplicar_filtro_50`
- `extrair_tabela_js`
- `salvar_resultado_json`
- `converter_json_para_peticoes`
- `processar_peticoes_js_integrado`
- `executar_motor_teste`
- `_formatar_acao_detalhada`
- `_obter_nome_acao`
- `main`

#### 1.4.17. Módulo `core_recovery.py`
- `verificar_e_recuperar_acesso_negado`
- `reiniciar_driver_e_logar_pje`

#### 1.4.18. Módulo `core_navegacao.py`
- `navegar_para_atividades`
- `aplicar_filtro_xs`
- `indexar_processo_atual_gigs`

#### 1.4.19. Módulo `core_main.py`
- `main`

#### 1.4.20. Módulo `core_progresso.py`
- `carregar_progresso_pec`
- `salvar_progresso_pec`
- `extrair_numero_processo_pec`
- `verificar_acesso_negado_pec`
- `processo_ja_executado_pec`

#### 1.4.21. Módulo `core_pos_carta.py`
- `analisar_documentos_pos_carta`

#### 1.4.22. Módulo `anexos\anexos_extracao.py`
- `extrair_numero_processo_da_pagina`
- `extrair_numero_processo_da_url`

#### 1.4.23. Módulo `anexos\anexos_configuracao.py`
- `salvar_conteudo_clipboard`

#### 1.4.24. Módulo `anexos\anexos_wrappers.py`
- `inserir_fn`

#### 1.4.25. Módulo `anexos\anexos_formatacao.py`
- `formatar_conteudo_ecarta`

#### 1.4.26. Módulo `anexos\anexos_juntador_helpers.py`
- `_abrir_interface_anexacao`
- `_preencher_campos_basicos`
- `_inserir_modelo`

#### 1.4.27. Módulo `anexos\anexos_sisbajud.py`
- `_obter_conteudo_relatorio_sisbajud`
- `inserir_fn`

#### 1.4.28. Módulo `anexos\anexos_juntador_metodos.py`
- `_escolher_opcao_gigs`
- `_preencher_input_gigs`
- `_clicar_elemento_gigs`
- `_selecionar_modelo_gigs`
- `_executar_coleta_opcional`
- `_preencher_tipo`
- `_preencher_descricao`
- `_configurar_sigilo`
- `_selecionar_e_inserir_modelo`
- `_inserir_conteudo_customizado`
- `_salvar_documento`
- `_assinar_se_necessario`

#### 1.4.29. Módulo `anexos\anexos_juntador_base.py`
- `create_juntador`
- `executar_juntada_ate_editor`
- `executar_juntada`

#### 1.4.30. Módulo `ajuste_gigs.py`
- `def_ajustegigs`

#### 1.4.31. Módulo `anexos\anexos_juntador.py`
- `create_juntador`
- `executar_juntada_ate_editor`
- `executar_juntada`

## 2. Funções que Podem ser Consideradas Mortas

Nenhuma função identificada como morta, pois os wrappers serão mantidos sempre conforme decisão anterior.

## 3. Conclusão

Com base na análise dos fluxos de execução principais, identificamos as funções que são efetivamente utilizadas. Não foram identificadas funções mortas, pois os wrappers serão mantidos sempre conforme decisão anterior.

Recomenda-se manter as funções utilizadas e os wrappers. As funções utilizadas podem ser otimizadas conforme necessário.