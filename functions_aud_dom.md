
# Funções e suas Origens em `aud.py` e `bianca/dom.py`

Este documento lista todas as funções chamadas nos módulos `aud.py` e `bianca/dom.py`, indicando o módulo de origem e o arquivo onde a função é definida.

## `aud.py` - Funções Chamadas e Origens

| Função Chamada | Origem (Módulo) | Arquivo de Definição |
|---|---|---|
| `carregar_progresso_aud` | Interno (`aud.py`) | `aud.py` |
| `salvar_progresso_aud` | Interno (`aud.py`) | `aud.py` |
| `processo_ja_executado_aud` | Interno (`aud.py`) | `aud.py` |
| `marcar_processo_executado_aud` | Interno (`aud.py`) | `aud.py` |
| `_esperar_responsavel` | Interno (`aud.py`) | `aud.py` |
| `acao_bucket_a` | Interno (`aud.py`) | `aud.py` |
| `obter_processos_triagem_api` | Interno (`aud.py`) | `aud.py` |
| `indexar_e_processar_lista_aud` | Interno (`aud.py`) | `aud.py` |
| `criar_driver_e_logar` | Interno (`aud.py`) | `aud.py` |
| `coletar_lista_processos` | Interno (`aud.py`) | `aud.py` |
| `agrupar_em_buckets` | Interno (`aud.py`) | `aud.py` |
| `reindexar_linha_js` | Interno (`aud.py`) | `aud.py` |
| `_abrir_nova_aba` | Interno (`aud.py`) | `aud.py` |
| `desmarcar_100` | Interno (`aud.py`) | `aud.py` |
| `remarcar_100_pos_aud` | Interno (`aud.py`) | `aud.py` |
| `marcar_aud` | Interno (`aud.py`) | `aud.py` |
| `executar_acoes_por_bucket` | Interno (`aud.py`) | `aud.py` |
| `run_aud` | Interno (`aud.py`) | `aud.py` |
| `configurar_recovery_driver` | `Fix.utils` | `Fix/utils.py` |
| `handle_exception_with_recovery` | `Fix.utils` | `Fix/utils.py` |
| `validar_conexao_driver` | `Fix.abas` | `Fix/abas.py` |
| `trocar_par-nova_aba` | `Fix.abas` | `Fix/abas.py` |
| `abrir_detalhes_processo` | `Fix.extracao` | `Fix/extracao.py` |
| `criar_gigs` | `Fix.extracao` | `Fix/extracao.py` |
| `extrair_dados_processo` | `Fix.extracao` | `Fix/extracao.py` |
| `preencher_multiplos_campos` | `Fix.core` | `Fix/core.py` |
| `aguardar_e_clicar` | `Fix.core` | `Fix/core.py` |
| `aguardar_renderizacao_nativa` | `Fix.core` | `Fix/core.py` |
| `esperar_elemento` | `Fix.core` | `Fix/core.py` |
| `safe_click` | `Fix.core` | `Fix/core.py` |
| `preencher_campo` | `Fix.core` | `Fix/core.py` |
| `ProgressoUnificado` (instância) | `progresso_unificado` | `progresso_unificado.py` |
| `ato_unap` | `atos` | `atos/atos.py` (assumido) |
| `ato_100` | `atos` | `atos/atos.py` (assumido) |
| `driver_pc` | `Fix.utils` | `Fix/utils.py` |
| `login_cpf` | `Fix.utils` | `Fix/utils.py` |
| `pec_sum` | `atos` | `atos/atos.py` (assumido) |
| `mov_aud` | `atos` | `atos/atos.py` (assumido) |
| `pec_ord` | `atos` | `atos/atos.py` (assumido) |
| `ato_ratif` | `xx.atos` | `xx/atos/atos.py` (assumido) |

## `bianca/dom.py` - Funções Chamadas e Origens

| Função Chamada | Origem (Módulo) | Arquivo de Definição |
|---|---|---|
| `create_driver_and_login` | Interno (`bianca/dom.py`) | `bianca/dom.py` |
| `navigate_to_list` | Interno (`bianca/dom.py`) | `bianca/dom.py` (Comentado) |
| `apply_filters` | Interno (`bianca/dom.py`) | `bianca/dom.py` (Comentado) |
| `filtro_chips` | Interno (`bianca/dom.py`) | `bianca/dom.py` (Comentado) |
| `collect_and_group_items` | Interno (`bianca/dom.py`) | `bianca/dom.py` (Comentado) |
| `has_dom_eletronico_reminder` | Interno (`bianca/dom.py`) | `bianca/dom.py` |
| `process_bucket1` | Interno (`bianca/dom.py`) | `bianca/dom.py` (Comentado) |
| `is_processo_100_digital` | Interno (`bianca/dom.py`) | `bianca/dom.py` |
| `callback_bucket2` | Interno (`bianca/dom.py`) | `bianca/dom.py` |
| `process_bucket2` | Interno (`bianca/dom.py`) | `bianca/dom.py` (Comentado) |
| `navigate_to_activities_and_filter` | Interno (`bianca/dom.py`) | `bianca/dom.py` |
| `execute_list_with_bucket2_callback` | Interno (`bianca/dom.py`) | `bianca/dom.py` |
| `processar_processo_dom` | Interno (`bianca/dom.py`) | `bianca/dom.py` |
| `_gerenciar_abas_apos_processo_dom` | Interno (`bianca/dom.py`) | `bianca/dom.py` |
| `main` | Interno (`bianca/dom.py`) | `bianca/dom.py` |
| `verificar_acesso_negado` | `x` | `x.py` (assumido) |
| `executar_com_recuperacao` | `x` | `x.py` (assumido) |
| `resetar_driver` | `x` | `x.py` (assumido) |
| `carregar_progresso_unificado` | `Fix.monitoramento_progresso_unificado` | `Fix/monitoramento_progresso_unificado.py` |
| `processo_ja_executado_unificado` | `Fix.monitoramento_progresso_unificado` | `Fix/monitoramento_progresso_unificado.py` |
| `marcar_processo_executado_unificado` | `Fix.monitoramento_progresso_unificado` | `Fix/monitoramento_progresso_unificado.py` |
| `criar_e_logar_driver` | `x` | `x.py` (assumido) |
| `DriverType.PC_VISIBLE` | `x` | `x.py` (assumido) |
| `filtrofases` | `Fix.core` | `Fix/core.py` (Comentado) |
| `aplicar_filtro_100` | `Fix.core` (ou `Fix.navigation`) | `Fix/core.py` ou `Fix/navigation.py` |
| `def_chip` | `atos.movimentos_chips` | `atos/movimentos_chips.py` |
| `criar_lembrete_posit` | `Fix.gigs` | `Fix/gigs.py` |
| `pec_sumc` | `atos.wrappers_pec` | `atos/wrappers_pec.py` |
| `pec_sumc2` | `atos.wrappers_pec` | `atos/wrappers_pec.py` |
| `pec_ordc` | `atos.wrappers_pec` | `atos/wrappers_pec.py` |
| `pec_ordc2` | `atos.wrappers_pec` | `atos/wrappers_pec.py` |
| `indexar_processos` | `Fix.extracao` | `Fix/extracao.py` |
| `reindexar_linha` | `Fix.extracao` | `Fix/extracao.py` |
| `processo_tem_erro_unificado` | `Fix.monitoramento_progresso_unificado` | `Fix/monitoramento_progresso_unificado.py` (assumido) |
| `executar_com_monitoramento_unificado` | `Fix.monitoramento_progresso_unificado` | `Fix/monitoramento_progresso_unificado.py` |
| `executar_processamento_iterativo_com_corte_em_erro_critico` | `utilitarios_processamento` | `utilitarios_processamento.py` |
| `esperar_elemento` | `Fix.selenium_base` | `Fix/selenium_base/wait_operations.py` (assumido) |
| `safe_click` | `Fix.selenium_base` | `Fix/selenium_base/wait_operations.py` (assumido) |
| `aguardar_e_clicar` | `Fix.selenium_base` | `Fix/selenium_base/wait_operations.py` (assumido) |
