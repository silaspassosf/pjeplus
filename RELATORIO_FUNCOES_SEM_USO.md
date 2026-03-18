# Relatório de Funções Sem Uso - Projeto PjePlus

**Data da Análise:** 2026-01-30  
**Total de Funções Analisadas:** 821  
**Total de Funções Sem Uso Detectadas:** 252  
**Percentual:** 30.7%

---

## 📊 Resumo por Módulo

| Módulo | Funções Sem Uso | % do Total |
|--------|-----------------|------------|
| Fix/   | 144             | 57.1%      |
| SISB/  | 38              | 15.1%      |
| atos/  | 21              | 8.3%       |
| Prazo/ | 19              | 7.5%       |
| PEC/   | 19              | 7.5%       |
| Mandado/ | 11            | 4.4%       |

---

## 🔍 Análise Detalhada

### Fix/ (144 funções)

#### Categorias Principais:

**1. Utilitários Angular (11 funções) - `Fix\utils_angular.py`**
- `aguardar_angular_carregar` (linha 13)
- `aguardar_angular_requests` (linha 47)
- `clicar_elemento_angular` (linha 71)
- `preencher_campo_angular` (linha 87)
- `aguardar_elemento_angular_visivel` (linha 103)
- `verificar_angular_app` (linha 119)
- `aguardar_angular_digest` (linha 131)
- `obter_angular_scope` (linha 157)
- `executar_angular_expressao` (linha 182)
- `esperar_elemento_angular` (linha 304)

**Motivo:** Módulo completo de integração Angular não utilizado. Possível código preparatório para versão futura do PJe.

**2. Debug Interativo (10 funções) - `Fix\debug_interativo.py`**
- `is_erro_critico` (linha 47)
- `capturar_contexto` (linha 55)
- `pausar_para_analise` (linha 143)
- `salvar_relatorio_erro` (linha 259)
- `obter_relatorio_final` (linha 280)
- `obter_relatorio_debug` (linha 322)
- `inicializar_debug_interativo` (linha 329)
- `get_debug_interativo` (linha 337)
- `on_erro_critico` (linha 341)
- `is_debug_ativo` (linha 360)

**Motivo:** Sistema de debug interativo completo não ativado. Pode ser útil para desenvolvimento/troubleshooting.

**3. Coleta de Dados (9 funções) - `Fix\utils_collect.py`**
- `coletar_texto_seletor` (linha 13)
- `coletar_valor_atributo` (linha 25)
- `coletar_multiplos_elementos` (linha 37)
- `coletar_tabela_como_lista` (linha 47)
- `coletar_links_pagina` (linha 74)
- `coletar_dados_formulario` (linha 95)
- `extrair_cpf_cnpj` (linha 163)
- `coletar_dados_pagina` (linha 189)

**Motivo:** Utilitários de coleta genéricos. Possivelmente substituídos por funções mais específicas em `Fix\extracao.py`.

**4. Waiters Genéricos (10 funções) - `Fix\waiters.py`**
- `wait_for_element_visible` (linha 17)
- `wait_for_element_clickable` (linha 42)
- `wait_for_element_present` (linha 67)
- `wait_for_text_in_element` (linha 92)
- `wait_for_url_contains` (linha 118)
- `safe_wait_and_click` (linha 167)
- `safe_wait_and_fill` (linha 193)
- `wait_for_any_element` (linha 221)
- `any_element_present` (linha 237)

**Motivo:** Duplicação com `Fix\selenium_base\wait_operations.py`. Arquivo legado.

**5. Headless Helpers (5 funções) - `Fix\headless_helpers.py`**
- `scroll_to_element_safe` (linha 67)
- `wait_and_click_headless` (linha 144)
- `find_element_headless_safe` (linha 151)
- `executar_com_retry_headless` (linha 181)
- `aguardar_elemento_headless_safe` (linha 236)

**Motivo:** Modo headless não utilizado no projeto atual.

**6. Converters (6 funções) - `Fix\converters.py`**
- `converter_valor_monetario` (linha 12)
- `parsear_data_brasileira` (linha 48)
- `formatar_data_hora_brasileira` (linha 115)
- `validar_cpf` (linha 134)
- `limpar_texto` (linha 163)

**Motivo:** Funções utilitárias criadas mas não integradas. Verificar se há equivalentes em `Fix\utils.py`.

**7. Session Pool (5 funções) - `Fix\session_pool.py`**
- `criar_sessao` (linha 79)
- `reutilizar_sessao` (linha 122)
- `finalizar_sessao` (linha 169)
- `listar_sessoes_ativas` (linha 196)
- `limpar_sessoes_expiradas` (linha 215)

**Motivo:** Sistema de pool de sessões não implementado. Possível otimização futura.

**8. Outras Funções Notáveis:**
- `is_browsing_context_discarded_error` (Fix\abas.py:16) - Verificação de erro específico
- `navegar_e_esperar` (Fix\element_wait.py:176) - Navegação com espera
- `obter_linhas_frescas` (Fix\extracao_indexacao.py:149) - Extração de linhas
- `extrair_numero_processo_url` (Fix\extracao_processo.py:39) - Extração de número
- `obter_id_processo_via_api` (Fix\extracao_processo.py:63) - API não utilizada
- `obter_dados_processo_via_api` (Fix\extracao_processo.py:76) - API não utilizada
- `enviar_url_infojud` (Fix\infojud.py:16) - Integração Infojud não ativa
- `consultar_cnpjs_infojud` (Fix\infojud.py:34) - Integração Infojud não ativa

---

### SISB/ (38 funções)

#### Categorias Principais:

**1. Performance/Cache (16 funções) - `SISB\performance.py`**
- `cache_element_selector` (linha 27)
- `batch_dom_operations` (linha 47)
- `optimize_javascript_execution` (linha 89)
- `replace_polling_with_observer` (linha 204)
- `cache_element` (linha 235)
- `get_cached_element` (linha 244)
- `cache_data` (linha 256)
- `get_cached_data` (linha 265)
- `clear_expired_cache` (linha 277)
- `process_series_parallel` (linha 327)
- `optimized_element_wait` (linha 369)
- `batched_form_fill` (linha 384)
- `cached_selector_lookup` (linha 408)
- `parallel_series_processing` (linha 421)
- `smart_cache_operation` (linha 435)

**Motivo:** Módulo completo de otimização de performance não ativado. Implementação futura.

**2. Funções Legacy (3 funções) - `SISB\s_orquestrador.py`**
- `criar_js_otimizado_legacy` (linha 66)
- `iniciar_sisbajud_legacy` (linha 73)
- `minuta_bloqueio_legacy` (linha 80)

**Motivo:** Código legado mantido como backup. **CANDIDATO FORTE PARA REMOÇÃO**.

**3. Standards/Validação (9 funções) - `SISB\standards.py`**
- `valor_bloqueado_text` (linha 169)
- `valor_bloquear_text` (linha 174)
- `log_erro` (linha 220)
- `log_sucesso` (linha 224)
- `validar_numero_processo_padronizado` (linha 288)
- `formatar_valor_monetario_padronizado` (linha 315)
- `calcular_data_limite_padronizada` (linha 335)
- `criar_timestamp_padronizado` (linha 348)
- `log_operacao` (linha 359)
- `validar_parametros` (linha 379)
- `retry_on_failure` (linha 393)

**Motivo:** Funções de padronização criadas mas não integradas ao fluxo principal.

**4. Outras:**
- `processar_endereco` (SISB\core.py:1077)
- `minuta_bloqueio_60` (SISB\core.py:1216)
- `minuta_endereco` (SISB\s_orquestrador.py:176)
- `run_tests` (SISB\test_refatoracao.py:274) - Arquivo de teste

---

### atos/ (21 funções)

**1. Comunicação (5 funções)**
- `selecionar_destinatario_por_documento` (atos\comunicacao_destinatarios.py:118)
- `remover_destinatarios_invalidos` (atos\comunicacao_finalizacao.py:175)
- `preencher_input_js` (atos\comunicacao_preenchimento.py:20)
- `escolher_opcao_select_js` (atos\comunicacao_preenchimento.py:55)
- `clicar_radio_button_js` (atos\comunicacao_preenchimento.py:78)

**Motivo:** Funções auxiliares de comunicação judicial não utilizadas no fluxo atual.

**2. Movimentos (6 funções)**
- `def_chip_custom` (atos\movimentos_chips.py:110)
- `log_debug` (atos\movimentos_fluxo.py:32, 154)
- `buscar_aba_detalhe` (atos\movimentos_fluxo.py:161)
- `tentar_encontrar_alvo` (atos\movimentos_fluxo.py:182)
- `mov_cls` (atos\movimentos_navegacao.py:370)
- `garantir_aba_detalhe` (atos\movimentos_sobrestamento.py:64)

**Motivo:** Helpers de movimentos não utilizados. Possível código preparatório.

**3. Wrappers (5 funções)**
- `mov_prazo` (atos\wrappers_mov.py:83)
- `mov_para_analise` (atos\wrappers_mov.py:99)
- `mov_para_comunicacoes` (atos\wrappers_mov.py:107)
- `wrapper_pec_ord_com_domicilio` (atos\wrappers_pec.py:238)
- `wrapper_pec_sum_com_domicilio` (atos\wrappers_pec.py:297)

**Motivo:** Wrappers específicos não utilizados. Verificar se há necessidade futura.

**4. Ofício (3 funções) - `atos\oficio.py`**
- `mail` (linha 108)
- `mailVT` (linha 145)
- `oficio` (linha 416)

**Motivo:** Funcionalidade de ofício não implementada no fluxo atual.

---

### Prazo/ (19 funções)

**1. Criteria Matcher (6 funções) - `Prazo\criteria_matcher.py`**
- `buscar_com_criterio` (linha 50)
- `criterio_prazo_ativo` (linha 100)
- `buscar_prazo_por_tipo` (linha 115)
- `criterio_tipo_prazo` (linha 126)
- `buscar_primeiro_prazo` (linha 138)
- `criterio_qualquer_prazo` (linha 148)

**Motivo:** Sistema de critérios de busca não utilizado. Possível refatoração futura.

**2. Loop/Ciclos (4 funções)**
- `verificar_um` (Prazo\loop_api.py:105)
- `ciclo2_processar_livres_apenas_uma_vez` (Prazo\loop_ciclo2_processamento.py:99)
- `ciclo2_loop_providencias` (Prazo\loop_ciclo2_processamento.py:152)
- `selecionar_processos_nao_livres` (Prazo\loop_helpers.py:46)

**Motivo:** Funções de ciclo alternativas não utilizadas no fluxo principal.

**3. Providências (5 funções) - `Prazo\prov_fluxo.py`**
- `fluxo_prov` (linha 36)
- `navegacao_prov` (linha 111)
- `selecionar_e_processar` (linha 148)
- `aplicar_xs_e_registrar` (linha 230)
- `fluxo_prov_integrado` (linha 371)

**Motivo:** Fluxo de providências alternativo. Verificar se `Prazo\prov.py` é o ativo.

**4. Outras:**
- `aplicar` (Prazo\p2b_core.py:313)
- `executar_prazo_com_otimizacoes` (Prazo\p2b_prazo.py:93)
- `aplicar_filtro_atividades_xs` (Prazo\p2b_prazo.py:131)
- `processar_item_prazo` (Prazo\p2b_prazo.py:270)

---

### PEC/ (19 funções)

**1. Arquivos de Teste (4 funções)**
- `parse_test_data` (PEC\test_pet2.py:36)
- `create_peticao_linha` (PEC\test_pet2.py:86)
- `print_test_results` (PEC\test_pet2.py:120)
- `testar_peticao` (PEC\test_pet2_real.py:70)

**Motivo:** Arquivos de teste. **MANTER** para validação.

**2. Backup (2 funções) - `PEC\processamento_backup.py`**
- `testar_coluna_observacao` (linha 224)
- `testar_coluna_observacao_novo` (linha 508)

**Motivo:** Arquivo de backup. **CANDIDATO PARA REMOÇÃO** se não for mais necessário.

**3. Sobrestamento (6 funções) - `PEC\sobrestamento.py`**
- `executar_mov_sob_retorno_feito` (linha 188)
- `executar_penhora_rosto` (linha 193)
- `executar_mov_sob_precatorio` (linha 207)
- `executar_juizo_universal` (linha 234)
- `executar_def_presc` (linha 238)
- `executar_ato_prov` (linha 244)

**Motivo:** Funções específicas de sobrestamento não utilizadas. Verificar se há casos de uso futuros.

**4. Outras:**
- `extrair_numero_processo_da_pagina` (PEC\anexos\anexos_extracao.py:19)
- `gerar_html_carta_para_juntada` (PEC\carta_formatacao.py:9)
- `salvar_progresso_pec` (PEC\core_progresso.py:25)
- `get_cached_rules` (PEC\matcher.py:124)
- `get_action_rules` (PEC\matcher.py:135)
- `processar_item_pec` (PEC\processamento_buckets.py:309)
- `get_or_create_driver_sisbajud` (PEC\sisbajud_driver.py:11)

---

### Mandado/ (11 funções)

**1. Core (3 funções) - `Mandado\core.py`**
- `setup_driver` (linha 147)
- `navegacao` (linha 157)
- `iniciar_fluxo_robusto` (linha 293)

**Motivo:** Funções de setup alternativas não utilizadas.

**2. Regras/Estratégias (5 funções) - `Mandado\regras.py`**
- `estrategia_defiro_instauracao` (linha 286)
- `estrategia_despacho_argos` (linha 367)
- `estrategia_infojud` (linha 433)
- `estrategia_decisao_manifestar` (linha 493)
- `estrategia_tendo_em_vista_que` (linha 515)

**Motivo:** Estratégias específicas não utilizadas. Verificar se `aplicar_regras_argos` cobre todos os casos.

**3. Outras:**
- `processar_sisbajud` (Mandado\processamento_anexos.py:207)
- `analise_padrao` (Mandado\processamento_outros.py:130)
- `retirar_sigilo_certidao_devolucao_primeiro` (Mandado\utils_sigilo.py:352)

---

## 🎯 Recomendações de Ação

### ✅ REMOVER IMEDIATAMENTE (Alta Confiança)

1. **Funções Legacy Explícitas:**
   - `SISB\s_orquestrador.py`: `criar_js_otimizado_legacy`, `iniciar_sisbajud_legacy`, `minuta_bloqueio_legacy`

2. **Arquivos de Backup Antigos:**
   - `PEC\processamento_backup.py` (se confirmado que não é mais necessário)
   - Verificar data de criação e última modificação

3. **Duplicações Confirmadas:**
   - `Fix\waiters.py` (todo o arquivo - duplica `Fix\selenium_base\wait_operations.py`)

### ⚠️ AVALIAR PARA REMOÇÃO (Média Confiança)

1. **Módulos Completos Não Utilizados:**
   - `Fix\utils_angular.py` (11 funções) - Se PJe não usa Angular
   - `Fix\headless_helpers.py` (5 funções) - Se modo headless não é necessário
   - `Fix\session_pool.py` (5 funções) - Se pool de sessões não é prioridade
   - `SISB\performance.py` (16 funções) - Se otimizações não são necessárias agora

2. **Integrações Não Ativas:**
   - `Fix\infojud.py` (2 funções) - Se Infojud não está integrado

### 📝 DOCUMENTAR COMO "FUTURO USO" (Manter)

1. **Debug e Diagnóstico:**
   - `Fix\debug_interativo.py` (10 funções) - Útil para troubleshooting

2. **Utilitários Genéricos:**
   - `Fix\converters.py` (6 funções) - Podem ser úteis no futuro
   - `Fix\utils_collect.py` (9 funções) - Coleta genérica de dados

3. **Funcionalidades Preparatórias:**
   - Wrappers específicos em `atos\wrappers_*.py`
   - Estratégias em `Mandado\regras.py`

### 🔍 INVESTIGAR MANUALMENTE (Requer Análise)

1. **Funções de Fluxo Alternativo:**
   - `Prazo\prov_fluxo.py` vs `Prazo\prov.py` - Qual é o ativo?
   - `Prazo\criteria_matcher.py` - Sistema de critérios é necessário?

2. **Funções de API:**
   - `Fix\extracao_processo.py`: `obter_id_processo_via_api`, `obter_dados_processo_via_api`
   - Verificar se há planos de usar API do PJe

3. **Funções de Sobrestamento:**
   - `PEC\sobrestamento.py` (6 funções) - Verificar casos de uso reais

---

## 📋 Checklist de Validação

Antes de remover qualquer função, verificar:

- [ ] Não há chamadas indiretas via `getattr()` ou `eval()`
- [ ] Não é usada em configurações/JSON externos
- [ ] Não é ponto de entrada de scripts externos
- [ ] Não há dependências em código de teste
- [ ] Não é exportada em `__init__.py` para uso externo
- [ ] Não é documentada como API pública
- [ ] Não há TODOs/FIXMEs referenciando a função

---

## 🔧 Problemas Técnicos Detectados

Durante a análise, foram encontrados os seguintes problemas:

1. **Encoding BOM (U+FEFF):**
   - `Fix\extracao.py`
   - `Fix\utils.py`
   - `SISB\processamento_ordens.py`
   - `atos\judicial_fluxo.py`
   - `PEC\anexos\core.py`
   - `Prazo\loop_ciclo1.py`
   - `Prazo\prov.py`

2. **Encoding Inválido (UTF-16):**
   - `atos\judicial_bloqueios.py`
   - `atos\judicial_wrappers.py`

3. **Erros de Sintaxe:**
   - `PEC\petjs.py` (linha 293-295)
   - `PEC\test_leitura_real.py` (linha 410-414)

4. **Regex Inválidas (escape sequences):**
   - `PEC\carta_ecarta.py:283`
   - `PEC\core_progresso.py:65`
   - `Prazo\loop_base.py:132`
   - `Prazo\p2b_fluxo_prescricao.py:98`

**Recomendação:** Corrigir estes problemas antes de qualquer refatoração.

---

## 📈 Estatísticas Adicionais

### Distribuição por Tipo de Função

| Tipo | Quantidade | % |
|------|------------|---|
| Utilitários/Helpers | 98 | 38.9% |
| Getters/Setters | 12 | 4.8% |
| Wrappers | 15 | 6.0% |
| Funções de Teste | 8 | 3.2% |
| Legacy/Obsoletas | 5 | 2.0% |
| Backup | 3 | 1.2% |
| Outras | 111 | 44.0% |

### Arquivos com Maior Concentração

| Arquivo | Funções Sem Uso |
|---------|-----------------|
| Fix\utils_angular.py | 11 |
| Fix\debug_interativo.py | 10 |
| Fix\waiters.py | 10 |
| Fix\utils_collect.py | 9 |
| SISB\performance.py | 16 |
| SISB\standards.py | 11 |

---

## 🚀 Plano de Ação Sugerido

### Fase 1 - Limpeza Imediata (1-2 dias)
1. Remover funções legacy explícitas
2. Remover arquivos de backup confirmados
3. Corrigir problemas de encoding
4. Corrigir erros de sintaxe

### Fase 2 - Avaliação (3-5 dias)
1. Revisar módulos completos não utilizados
2. Decidir sobre integrações não ativas
3. Validar funções de fluxo alternativo
4. Documentar decisões

### Fase 3 - Documentação (2-3 dias)
1. Marcar funções "futuro uso" com decorators
2. Adicionar comentários explicativos
3. Atualizar INDEX.md
4. Criar guia de funções disponíveis

### Fase 4 - Refatoração (opcional)
1. Consolidar utilitários duplicados
2. Reorganizar estrutura de módulos
3. Implementar testes para funções mantidas

---

## 📝 Notas Finais

- Esta análise é baseada em busca estática de código
- Pode haver falsos positivos (chamadas dinâmicas não detectadas)
- Recomenda-se validação manual antes de remover código
- Manter backup antes de qualquer remoção em massa
- Considerar criar branch específica para limpeza

**Próxima Revisão Sugerida:** 3 meses após implementação das mudanças

---

**Gerado por:** `analyze_unused.py`  
**Versão do Script:** 1.0  
**Data:** 2026-01-30