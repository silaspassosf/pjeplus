# PJePlus — Índice de Navegação Precisa (IDX)

Atualizado: 2026-05-11 (granularização cirúrgica pós-agentes)

> **LEITURA OBRIGATÓRIA PARA IA:** Este arquivo é o filtro de escopo primário e inegociável. Antes de qualquer Grep, Glob ou Agent de exploração, consulte este índice. Se o índice não cobrir o termo buscado, a busca é permitida — mas o índice deve ser atualizado ao final. Buscas genéricas sem consulta prévia a este índice são proibidas.

---

## 0. Árvore de Decisão de Escopo

Para qualquer tarefa, responda em sequência para encontrar os arquivos exatos:

```
TAREFA: "preciso fazer X"

Q1: X envolve driver/login/sessão?
  → SIM: Fix/core.py (driver factory), Fix/utils.py (login_cpf), Fix/browser_suporte.py (validação)
  → NÃO: continue

Q2: X envolve API REST do PJe (GIGS, timeline, documentos, partes)?
  → SIM: Fix/variaveis.py (PjeApiClient + todas as funções de API)
  → NÃO: continue

Q3: X envolve extração de PDF/HTML, GIGS, BNDT, indexação de processos?
  → SIM: Fix/extracao.py
  → NÃO: continue

Q4: X envolve CKEditor, coleta de conteúdo, clipboard, recovery de driver?
  → SIM: Fix/utils.py
  → NÃO: continue

Q5: X envolve logger, debug interativo, medir_tempo?
  → SIM: Fix/diagnostico_runtime.py (logger), Fix/core.py (medir_tempo)
  → NÃO: continue

Q6: X envolve progresso/checkpoint/retomada de execução?
  → SIM: Fix/monitoramento_progresso_unificado.py
  → NÃO: continue

Q7: X envolve click/espera/preenchimento em modais PJe?
  → SIM: Fix/core.py (safe_click, esperar_elemento, preencher_campo, aguardar_renderizacao_nativa, click_headless_safe)
  → NÃO: continue

Q8: X é um fluxo de negócio específico?
  → Mandado (Argos/Outros): Mandado/entrada_api.py → Mandado/fluxo_argos.py → Mandado/apoio_fluxos.py → Mandado/regras.py
  → Prazo (ciclo1+2+3): Prazo/loop_orquestrador.py → Prazo/loop_lote.py → Prazo/loop_execucao_final.py
  → P2B (GIGS sem prazo): Prazo/p2b_gateway.py → Prazo/p2b_regras_execucao.py → Prazo/p2b_documentos.py
  → PEC (comunicações/cartas): PEC/runtime_pec.py → PEC/regras_execucao.py → atos/comunicacao*.py
  → Triagem: bianca/triagem_engine.py (runner)
  → Petição: Peticao/runtime_pet.py
  → SISBAJUD: SISB/core.py
  → NÃO: continue

Q9: X é um ato judicial (conclusão, minutar, assinar)?
  → SIM: atos/judicial_fluxo.py (implementação real), atos/judicial_navegacao.py (navegação)
  → NÃO: continue

Q10: X é uma comunicação judicial (PEC, expedição)?
  → SIM: atos/comunicacao.py (orquestrador), atos/comunicacao_preenchimento.py, atos/comunicacao_destinatarios.py
  → NÃO: continue

Q11: X é um movimento processual (navegar entre tarefas)?
  → SIM: atos/movimentos_fluxo.py, atos/movimentos_navegacao.py
  → NÃO: continue

Q12: X é um wrapper/instância concreta de ato ou comunicação?
  → Ato: atos/wrappers_ato.py (45+ atos via make_ato_wrapper)
  → Comunicação: atos/wrappers_pec.py (19+ wrappers via make_comunicacao_wrapper)
  → Movimento: atos/wrappers_mov.py (mov_arquivar, mov_exec, mov_aud, mov_prazo)
  → NÃO: continue

Q13: X envolve anexos/juntada de documentos?
  → SIM: PEC/anexos/anexos_juntador_base.py, PEC/anexos/anexos_wrappers.py
  → NÃO: buscar termo específico na Seção 5 (Índice de Palavras-Chave)
```

---

## 1. Mapa de Domínios Funcionais (Cross-Cutting)

Arquivos agrupados pelo QUE fazem, independente de ONDE estão:

### Driver & Sessão
| Função | Arquivo | Nota |
|---|---|---|
| Criar driver Firefox (PC/VT, visible/headless) | `Fix/core.py` | `criar_driver_PC`, `criar_driver_VT`, `criar_driver_notebook`, `criar_driver_sisb_*` |
| Login (CPF, automático, manual) | `Fix/utils.py` | `login_cpf`, `login_automatico`, `login_manual` |
| Finalizar driver | `Fix/core.py` | `finalizar_driver` |
| Cookies (salvar/carregar) | `Fix/core.py` | `salvar_cookies_sessao`, `carregar_cookies_sessao` |
| Validação de conexão | `Fix/browser_suporte.py` | `validar_conexao_driver`, `is_browsing_context_discarded_error` |
| Otimizações (iniciar/finalizar) | `Fix/browser_suporte.py` | `inicializar_otimizacoes`, `finalizar_otimizacoes` |
| Abas (trocar, fechar, aguardar) | `Fix/browser_suporte.py` | `trocar_para_nova_aba`, `forcar_fechamento_abas_extras` |
| Resetar driver entre módulos | `x.py` | `resetar_driver()` |

### Interação Selenium (Click, Wait, Preenchimento)
| Função | Arquivo | Nota |
|---|---|---|
| Clique headless-safe | `Fix/browser_suporte.py` | `click_headless_safe` — usar em vez de `.click()` |
| Clique em elemento já encontrado | `Fix/core.py` | `safe_click_no_scroll` |
| Clique com retry e fallback | `Fix/core.py` | `safe_click` |
| Esperar elemento presente | `Fix/core.py` | `esperar_elemento` |
| Aguardar renderização Angular | `Fix/core.py` | `aguardar_renderizacao_nativa` — usar em vez de `time.sleep` |
| Preencher campo Angular Material | `Fix/core.py` | `preencher_campo` |
| Selecionar opção (mat-select) | `Fix/core.py` | `selecionar_opcao` |
| Retry genérico | `Fix/core.py` | `com_retry` |
| Busca inteligente de seletor | `Fix/core.py` | `buscar_seletor_robusto`, `encontrar_elemento_inteligente` |
| JS base | `Fix/core.py` | `js_base` |
| Scroll seguro (headless) | `Fix/browser_suporte.py` | `scroll_to_element_safe` |
| Limpar overlays (headless) | `Fix/browser_suporte.py` | `limpar_overlays_headless` |

### API REST PJe
| Função | Arquivo | Nota |
|---|---|---|
| PjeApiClient (classe principal) | `Fix/variaveis.py` | Timeline, documentos, partes, cálculos, perícias, GIGS, BNDT, domicílio eletrônico |
| session_from_driver | `Fix/variaveis.py` | Ponte Selenium → requests.Session |
| GIGS com fase | `Fix/variaveis.py` | `obter_gigs_com_fase` |
| Documentos (conteúdo, chave, peça) | `Fix/variaveis.py` | `obter_texto_documento`, `obter_codigo_validacao_documento` |
| Domicílio eletrônico | `Fix/variaveis.py` | `obter_domicilio_eletronico_parte`, `verificar_domicilio_eletronico_partes` |
| BNDT | `Fix/variaveis.py` | `verificar_bndt`, `processar_com_verificacao_bndt` |
| URL de detalhe | `Fix/variaveis.py` | `url_processo_detalhe` |

### Extração de Dados
| Função | Arquivo | Nota |
|---|---|---|
| Extrair PDF (pdfplumber) | `Fix/extracao.py` | `extrair_pdf` |
| Extrair documento (HTML/PDF) | `Fix/extracao.py` | `extrair_documento`, `extrair_direto` |
| Extrair dados do processo | `Fix/extracao.py` | `extrair_dados_processo` |
| Criar GIGS/comentário/lembrete | `Fix/extracao.py` | `criar_gigs`, `criar_comentario`, `criar_lembrete_posit` |
| BNDT (operações) | `Fix/extracao.py` | `bndt` — abrir, selecionar operação, gravar |
| Indexar processos em lista | `Fix/extracao.py` | `indexar_processos`, `indexar_e_processar_lista` |
| Destinatários (cache) | `Fix/extracao.py` | `extrair_destinatarios_decisao`, `salvar_destinatarios_cache` |
| Análise Argos | `Fix/extracao.py` | `analise_argos`, `tratar_anexos_argos` |

### Editor CKEditor
| Função | Arquivo | Nota |
|---|---|---|
| Inserir HTML no editor | `Fix/utils.py` | `inserir_html_editor` |
| Inserir texto no editor | `Fix/utils.py` | `inserir_texto_editor` |
| Coletar conteúdo formatado | `Fix/utils.py` | `coletar_conteudo_formatado_documento` |
| Coletar link de ato na timeline | `Fix/utils.py` | `coletar_link_ato_timeline` |
| Clipboard interno | `Fix/utils.py` | `obter_ultimo_conteudo_clipboard`, `salvar_conteudo_clipboard` |
| Substituir marcador por conteúdo | `PEC/anexos/anexos_juntador_helpers.py` | `substituir_marcador_por_conteudo` |

### Progresso & Checkpoint
| Função | Arquivo | Nota |
|---|---|---|
| Progresso unificado (todos os módulos) | `Fix/monitoramento_progresso_unificado.py` | `ProgressoUnificado`, `carregar_progresso_unificado`, `marcar_processo_executado_unificado` |
| Progresso PEC | `PEC/runtime_pec.py` | `carregar_progresso_pec`, `marcar_processo_executado_pec` |
| Progresso P2B | `Prazo/p2b_regras_execucao.py` | `carregar_progresso_p2b`, `marcar_processo_executado_p2b` |
| Progresso Petição | `Peticao/runtime_pet.py` | `carregar_progresso_pet`, `marcar_processo_executado_pet` |

### Logging & Diagnóstico
| Função | Arquivo | Nota |
|---|---|---|
| Logger estruturado | `Fix/diagnostico_runtime.py` | `PJELogger`, `log_start`, `log_item`, `log_sucesso`, `log_erro`, `log_fim` |
| Debug interativo | `Fix/diagnostico_runtime.py` | `DebugInterativo`, `get_debug_interativo`, `on_erro_critico` |
| Medir tempo (decorator) | `Fix/core.py` | `medir_tempo`, ativar com `PJEPLUS_TIME=1` |
| Logger do módulo Fix | `Fix/log.py` | SHIM → `diagnostico_runtime.py` |
| Erro.md (handler de erro) | `x.py` | Configurado em `configurar_logging()` |

### Formatação & Texto
| Função | Arquivo | Nota |
|---|---|---|
| Remover acentos | `Fix/utils.py` | `remover_acentos` |
| Normalizar texto | `Fix/utils.py` | `normalizar_texto` |
| Formatar moeda (R$) | `Fix/utils.py` | `formatar_moeda_brasileira` |
| Formatar data (dd/mm/aaaa) | `Fix/utils.py` | `formatar_data_brasileira` |
| Normalizar CPF/CNPJ | `Fix/utils.py` | `normalizar_cpf_cnpj` |

---

## 2. Índice de Palavras-Chave (Keyword → Arquivo)

Busque pela palavra-chave que descreve sua tarefa:

| Palavra-chave | Arquivo(s) exato(s) |
|---|---|
| `abrir_tarefa`, `abrir_tarefa_processo` | `atos/judicial_navegacao.py` |
| `aguardar_renderizacao_nativa` | `Fix/core.py` (real), `Fix/diagnostico_runtime.py` (lazy re-export) |
| `anex_carta`, `anexar`, `anexos` | `PEC/anexos/anexos_wrappers.py`, `PEC/anexos/anexos_juntador_base.py` |
| `aplicar_filtro_100`, `filtro_fase` | `Fix/core.py` |
| `argos`, `processar_argos` | `Mandado/fluxo_argos.py`, `Fix/extracao.py` (`analise_argos`) |
| `assinatura`, `assinar` | `atos/comunicacao_finalizacao.py` (`salvar_minuta_final`) |
| `ato_judicial`, `make_ato_wrapper`, `fluxo_cls` | `atos/judicial_fluxo.py` (IMPLEMENTAÇÃO REAL), `atos/judicial.py` (FACHADA) |
| `ato_bloq`, `ato_pesqliq`, `ato_prev`, `ato_*` | `atos/wrappers_ato.py` (45+ instâncias) |
| `bloqueio`, `bloq`, `sisbajud` | `SISB/core.py`, `atos/wrappers_ato.py` (`ato_bloq`), `Mandado/apoio_fluxos.py` (`lembrete_bloq`) |
| `bndt` | `Fix/extracao.py` (DOM), `Fix/variaveis.py` (API) |
| `buscar_documentos_sequenciais` | `Fix/core.py` |
| `buscar_seletor_robusto` | `Fix/core.py` |
| `carta`, `ecarta`, `carta_execucao` | `PEC/carta_execucao.py`, `PEC/runtime_pec.py` (formatar_dados_ecarta) |
| `ciclo1`, `ciclo2`, `ciclo3`, `loop_prazo` | `Prazo/loop_orquestrador.py`, `Prazo/loop_lote.py`, `Prazo/loop_execucao_final.py` |
| `ckeditor`, `editor`, `inserir_html` | `Fix/utils.py` |
| `click_headless_safe`, `safe_click` | `Fix/browser_suporte.py` (`click_headless_safe`), `Fix/core.py` (`safe_click`) |
| `clipboard` | `Fix/utils.py` (`obter_ultimo_conteudo_clipboard`), `PEC/anexos/anexos_configuracao.py` |
| `com_retry` | `Fix/core.py` |
| `comunicacao_judicial`, `make_comunicacao_wrapper` | `atos/comunicacao.py` (IMPLEMENTAÇÃO REAL) |
| `conclusao`, `conclusao_ao_magistrado` | `atos/judicial_navegacao.py` (`navegar_para_conclusao`), `atos/judicial_modelos.py` (`escolher_tipo_conclusao`) |
| `cookies`, `sessao` | `Fix/core.py` (`salvar_cookies_sessao`, `carregar_cookies_sessao`) |
| `criar_driver` | `Fix/core.py` (`criar_driver_PC`, `criar_driver_VT`, etc.) |
| `destinatarios`, `selecionar_destinatarios` | `atos/comunicacao_destinatarios.py` |
| `domicilio_eletronico` | `Fix/variaveis.py` (`obter_domicilio_eletronico_parte`, `verificar_domicilio_eletronico_partes`) |
| `esperar_elemento`, `wait_for_clickable` | `Fix/core.py` |
| `extrair_documento`, `extrair_pdf` | `Fix/extracao.py` |
| `fechar_abas_extras` | `Fix/browser_suporte.py` (`forcar_fechamento_abas_extras`) |
| `finalizar_driver` | `Fix/core.py` |
| `gigs`, `criar_gigs`, `atividades_gigs` | `Fix/extracao.py` (criação DOM), `Fix/variaveis.py` (consulta API) |
| `headless`, `is_headless_mode` | `Fix/browser_suporte.py` |
| `idpj` | `atos/judicial_helpers.py` |
| `indexar`, `indexar_processos` | `Fix/extracao.py` |
| `juntada`, `juntar`, `wrapper_juntada` | `PEC/anexos/anexos_juntador_base.py` |
| `login`, `login_cpf`, `login_manual` | `Fix/utils.py` |
| `mandado`, `mandados_devolvidos` | `Mandado/entrada_api.py` |
| `medir_tempo`, `tempo_execucao` | `Fix/core.py` (decorator `medir_tempo`) |
| `minuta`, `minutar`, `modelo` | `atos/judicial_modelos.py`, `atos/comunicacao_preenchimento.py` |
| `modelo_insercao`, `snackbar` | `atos/comunicacao_preenchimento.py` (`aguardar_ato_confeccionado`) |
| `movimentar`, `mov`, `mov_simples` | `atos/movimentos_fluxo.py` (IMPLEMENTAÇÃO REAL), `atos/movimentos.py` (FACHADA) |
| `mov_arquivar`, `mov_exec`, `mov_aud` | `atos/wrappers_mov.py` |
| `mov_sob`, `sobrestamento` | `atos/movimentos_sobrestamento.py` |
| `mov_fimsob` | `atos/movimentos_fimsob.py` |
| `navegar_para_tarefa` | `atos/movimentos_navegacao.py` |
| `p2b`, `gigs_sem_prazo` | `Prazo/p2b_gateway.py` |
| `pec_ord`, `pec_sum`, `pec_bloqueio`, `pec_*` | `atos/wrappers_pec.py` (19+ wrappers) |
| `preencher_campo`, `preencher_campos_prazo` | `Fix/core.py` |
| `prescricao`, `prescreve` | `Prazo/p2b_fluxo_prescricao.py` (satélite) |
| `progresso`, `checkpoint`, `ja_executado` | `Fix/monitoramento_progresso_unificado.py` (unificado), ou arquivo runtime_*.py do módulo específico |
| `recovery`, `acesso_negado` | `Fix/utils.py` (`configurar_recovery_driver`, `verificar_e_tratar_acesso_negado_global`) |
| `regras`, `RuleRegistry`, `adapt_action` | `core/rule_registry.py` (contrato), `*/regras*.py` (instâncias por módulo) |
| `resetar_driver` | `x.py` |
| `retirar_sigilo`, `visibilidade_sigilosos` | `Mandado/apoio_fluxos.py`, `Fix/core.py` |
| `run_batch`, `resultado_ok`, `resultado_falha` | `utilitarios_processamento.py` (genérico), `bianca/utils.py` (cópia) |
| `selecionar_opcao` | `Fix/core.py` |
| `sisbajud`, `minuta_bloqueio` | `SISB/core.py`, `PEC/anexos/anexos_sisbajud.py` |
| `sob`, `def_sob` | `PEC/regras_execucao.py` |
| `timeline`, `documento_por_id` | `Fix/variaveis.py` (`PjeApiClient`) |
| `triagem`, `run_triagem` | `bianca/triagem_engine.py` (runner), `Triagem/` (cópia legada) |
| `chip`, `def_chip`, `remover etiqueta` | `atos/movimentos_chips.py` |
| `despacho_generico` | `atos/movimentos_despacho.py` |
| `peticao`, `run_pet`, `escaninho` | `Peticao/runtime_pet.py` |

---

## 3. Cadeias de Chamada por Fluxo de Negócio

### Fluxo A/B — Mandado
```
x.py: executar_mandado()
  → Mandado/entrada_api.py: processar_mandados_devolvidos_api(driver)
    → run_batch() [utilitarios_processamento.py]
      → open_item: url_processo_detalhe (API)
      → execute_item: _selecionar_doc_via_timeline() [DOM]
        ├─ Se ARGOS: Mandado/fluxo_argos.py: processar_argos(driver)
        │   ├─ ETAPA 0: fechar_intimacao()
        │   ├─ ETAPA 1: buscar_documentos_sequenciais [Fix/core.py]
        │   ├─ ETAPA 1.5: Mandado/apoio_fluxos.py: retirar_sigilo_fluxo_argos()
        │   ├─ ETAPA 2: anexos infojud
        │   ├─ ETAPA 3: processar_sisbajud() [SISB/core.py]
        │   ├─ ETAPA 4: Mandado/regras.py: aplicar_regras_argos()
        │   └─ ETAPA 5: destinatários + atos
        └─ Se OUTROS: Mandado/apoio_fluxos.py: fluxo_mandados_outros()
            → ato_judicial, ato_meios, ato_pesquisas, etc. [atos/wrappers_ato.py]
```

### Fluxo C/D — Prazo + P2B
```
x.py: executar_prazo()
  ├─ Prazo/loop_orquestrador.py: loop_prazo(driver)
  │   ├─ Painel 14 (Análise): ciclo1()
  │   │   └─ Prazo/loop_lote.py: _ciclo1_aplicar_filtro_fases(), _ciclo1_marcar_todas(),
  │   │      _ciclo1_abrir_suitcase(), _ciclo1_movimentar_destino()
  │   ├─ Painel 8 (Cumprimento): ciclo2() [Prazo/loop_execucao_final.py]
  │   │   └─ Prazo/loop_lote.py: _ciclo2_aplicar_filtros(), _ciclo2_processar_livres(),
  │   │      _ciclo2_selecionar_nao_livres()
  │   └─ ciclo3() [Prazo/loop_execucao_final.py]
  └─ x.py: executar_p2b()
      └─ Prazo/p2b_gateway.py: processar_gigs_sem_prazo_p2b(driver)
          ├─ testar_gigs_sem_prazo() [API: GIGS API]
          ├─ Prazo/p2b_documentos.py: _encontrar_documento_relevante() [DOM: timeline]
          ├─ Prazo/p2b_gateway.py: extrair_documento_relevante() [API: /timeline → /conteudo → pdfplumber]
          └─ Prazo/p2b_regras_execucao.py: CriteriaMatcher + RegraProcessamento
```

### Fluxo E — PEC
```
x.py: executar_pec()
  → PEC/runtime_pec.py: PECOrquestrador.executar()
    ├─ PECAPIClient.fetch_atividades_vencidas() [API: GIGS API]
    ├─ PEC/regras_execucao.py: determinar_regra(observacao) → RuleRegistry.match()
    │   └─ Buckets: carta, comunicacoes, sobrestamento, sob, outros, sisbajud
    └─ run_batch() por processo:
        ├─ Se "carta": PEC/carta_execucao.py: carta(driver)
        │   → coletar_intimacoes() → coletar_tabela_ecarta() → formatar_dados_ecarta()
        │   → PEC/anexos/anexos_wrappers.py: anex_carta()
        │   → PEC/anexos/anexos_juntador_base.py: wrapper_juntada_geral()
        ├─ Se "comunicacoes": atos/comunicacao.py: comunicacao_judicial()
        │   → atos/comunicacao_coleta.py → atos/comunicacao_navigation.py
        │   → atos/comunicacao_preenchimento.py → atos/comunicacao_destinatarios.py
        │   → atos/comunicacao_finalizacao.py
        ├─ Se "sobrestamento" ou "sob": PEC/regras_execucao.py: def_sob()
        └─ Se "sisbajud": PEC/anexos/anexos_sisbajud.py: executar_juntada_pje()
```

### Fluxo F — Triagem
```
x.py: executar_triagem()
  → bianca/triagem_engine.py: run_triagem(driver)
    → bianca/triagem/api.py: buscar_lista_triagem() [API]
    → bianca/triagem/runner.py: run_triagem()
    → Triagem/regras.py: determinar_acao_pos_triagem() → RuleRegistry
    → Triagem/analise_execucao.py: acao_bucket_* [DOM]
```

### Fluxo G — Petição
```
x.py: executar_pet()
  → Peticao/runtime_pet.py: run_pet(driver)
    → PETOrquestrador + PeticaoAPIClient
    → Peticao/regras_execucao.py: classificar(), resolver_acao()
    → Peticao/helpers/helpers.py: apagar(), checar_habilitacao(), agravo_peticao()
```

### Fluxo H — DOM
```
x.py: executar_dom()
  → bianca/dom_engine.py: run_dom(driver)
    → has_dom_eletronico_reminder(), checar_empresas(), is_processo_100_digital()
    → navigate_to_activities_and_filter() → callback_bucket2()
    → processar_processo_dom()
```

---

## 4. Topologia do Projeto

### Core (Infraestrutura compartilhada)

| Diretório | Papel | Arquivos REAIS (não shims) |
|---|---|---|
| `Fix/` | Motor utilitário | `core.py`, `browser_suporte.py`, `utils.py`, `extracao.py`, `variaveis.py`, `diagnostico_runtime.py`, `monitoramento_progresso_unificado.py`, `facade_publica.py`, `tipos.py` |
| `core/` | Contratos compartilhados | `rule_registry.py` (RuleRegistry, adapt_action), `resultado_execucao.py` (ResultadoExecucao) |
| `atos/` | Wrappers de ações judiciais | Ver seção 6 para catálogo completo |
| `utilitarios_processamento.py` | Flow Engine genérico | `run_batch()`, `resultado_ok()`, `resultado_falha()` |

### ⚠️ SHIMS em Fix/ — NUNCA EDITAR

Estes arquivos têm ≤30 linhas e apenas re-exportam de `facade_publica.py` ou `browser_suporte.py`. **Modificações devem ir nos arquivos reais, não aqui:**

| Shim | Redireciona para |
|---|---|
| `Fix/abas.py` | `Fix/browser_suporte.py` |
| `Fix/headless_helpers.py` | `Fix/browser_suporte.py` |
| `Fix/otimizacao_wrapper.py` | `Fix/browser_suporte.py` |
| `Fix/element_wait.py` | `Fix/facade_publica.py` → `Fix/core.py` |
| `Fix/smart_finder.py` | `Fix/facade_publica.py` |
| `Fix/documents.py` | `Fix/facade_publica.py` → `Fix/core.py` / `Fix/extracao.py` |
| `Fix/navigation.py` | `Fix/facade_publica.py` → `Fix/core.py` |
| `Fix/gigs.py` | `Fix/facade_publica.py` → `Fix/extracao.py` |
| `Fix/selectors_pje.py` | `Fix/facade_publica.py` → `Fix/core.py` |
| `Fix/variaveis_client.py` | `Fix/variaveis.py` |
| `Fix/variaveis_helpers.py` | `Fix/variaveis.py` |
| `Fix/variaveis_resolvers.py` | `Fix/variaveis.py` |
| `Fix/movimento_helpers.py` | `Fix/facade_publica.py` |
| `Fix/errors.py`, `Fix/exceptions.py` | `Fix/facade_publica.py` |
| `Fix/log.py` | `Fix/diagnostico_runtime.py` |
| `Fix/debug_interativo.py` | `Fix/diagnostico_runtime.py` |
| `Fix/utils_observer.py` | `Fix/diagnostico_runtime.py` → `Fix/core.py` |
| `Fix/utils_tempo.py` | `Fix/diagnostico_runtime.py` → `Fix/core.py` |
| `Fix/progresso_unificado.py` | `Fix/monitoramento_progresso_unificado.py` |
| `Fix/selenium_base/*` (5 arquivos) | `Fix/core.py` / `Fix/browser_suporte.py` |
| `Fix/drivers/*` (2 arquivos) | `Fix/core.py` |
| `Fix/progress/*` (2 arquivos) | `Fix/monitoramento_progresso_unificado.py` |
| `Fix/scripts/__init__.py` | `Fix/facade_publica.py` |

### ⚠️ Arquivos LEGADO — NUNCA EDITAR (apenas referência)

| Arquivo/Diretório | Nota |
|---|---|
| `leg/` (todo o diretório) | Snapshots pré-xcode. Referência de comportamento original. |
| `Mandado/core.py` | Versão antiga, fora do caminho do x.py atual |
| `Mandado/processamento.py` | Comentado como "LEGADO — fora do caminho de execução" |
| `Prazo/p2b_fluxo_prescricao.py` | Satélite legado, fora do caminho principal |
| `PEC/prescricao.py` | Placeholder ("pendente") |
| `_archive/` | Código removido organizado por data |

### ⚠️ Diretórios duplicados — USAR A VERSÃO CORRETA

| Diretório | Status | Usar em vez disso |
|---|---|---|
| `bianca/` | CÓPIA ATIVA (pré-xcode mantida separada) | Usar `bianca/` para Triagem e DOM — é a versão chamada por `x.py` |
| `Triagem/` | CÓPIA LEGADA | `bianca/triagem_engine.py` é o entry point real |
| `api/` (raiz) | CÓPIA | `Fix/variaveis.py` é a implementação real do PjeApiClient |
| `api/` (em `leg/api/`) | Snapshot legado | Referência apenas |

---

## 5. Módulos de Negócio (Entry Points)

| Módulo | Entry point real (chamado por x.py) | Orquestrador interno | Regras |
|---|---|---|---|
| **Mandado** | `Mandado/entrada_api.py::processar_mandados_devolvidos_api` | `Mandado/fluxo_argos.py::processar_argos` | `Mandado/regras.py::aplicar_regras_argos` |
| **Prazo** | `Prazo/loop_orquestrador.py::loop_prazo` | `Prazo/loop_lote.py`, `Prazo/loop_execucao_final.py` | N/A (regras embutidas nos loops) |
| **P2B** | `Prazo/p2b_gateway.py::processar_gigs_sem_prazo_p2b` | `Prazo/p2b_gateway.py` | `Prazo/p2b_regras_execucao.py::CriteriaMatcher` |
| **PEC** | `PEC/runtime_pec.py::executar_fluxo_novo_simplificado` | `PEC/runtime_pec.py::PECOrquestrador` | `PEC/regras_execucao.py::determinar_regra` |
| **Triagem** | `bianca/triagem_engine.py::run_triagem` | `bianca/triagem/runner.py` | `Triagem/regras.py::determinar_acao_pos_triagem` |
| **Petição** | `Peticao/runtime_pet.py::run_pet` | `Peticao/runtime_pet.py::PETOrquestrador` | `Peticao/regras_execucao.py::classificar` |
| **SISBAJUD** | `SISB/core.py::iniciar_sisbajud` | `SISB/batch.py::processar_lote_sisbajud` | N/A |

---

## 6. Catálogo de Arquivos — atos/ (31 arquivos)

### IMPLEMENTAÇÕES REAIS (editar aqui)

**Ato Judicial:**
| Arquivo | Papel |
|---|---|
| `atos/judicial_fluxo.py` | Motor principal: `fluxo_cls`, `ato_judicial`, `make_ato_wrapper` |
| `atos/judicial_navegacao.py` | Navegação: `abrir_tarefa_processo`, `navegar_para_conclusao`, `preparar_campo_minutar` |
| `atos/judicial_modelos.py` | Modelos: `escolher_tipo_conclusao`, `aguardar_transicao_minutar`, `verificar_estado_atual` |
| `atos/judicial_utils.py` | Preenchimento: `preencher_prazos_destinatarios`, `verificar_bloqueio_recente` |
| `atos/judicial_helpers.py` | Helpers: `ato_pesquisas`, `idpj`, `verificar_bloqueio_recente` |

**Comunicação Judicial:**
| Arquivo | Papel |
|---|---|
| `atos/comunicacao.py` | Orquestrador: `comunicacao_judicial`, `make_comunicacao_wrapper` |
| `atos/comunicacao_coleta.py` | Coleta pré-fluxo: `executar_coleta_conteudo` |
| `atos/comunicacao_navigation.py` | Navegação: `abrir_minutas` |
| `atos/comunicacao_preenchimento.py` | Preenchimento: `executar_preenchimento_minuta`, `aguardar_ato_confeccionado` |
| `atos/comunicacao_destinatarios.py` | Destinatários: `selecionar_destinatarios`, `selecionar_destinatario_por_documento` |
| `atos/comunicacao_finalizacao.py` | Finalização: `alterar_meio_expedicao`, `salvar_minuta_final` |

**Movimentação Processual:**
| Arquivo | Papel |
|---|---|
| `atos/movimentos_fluxo.py` | Motor: `mov`, `mov_simples`, `movimentar_inteligente`, `abrir_tarefa_por_api` |
| `atos/movimentos_navegacao.py` | Máquina de estados: `navegar_para_tarefa` (matriz de transição) |
| `atos/movimentos_sobrestamento.py` | Sobrestamento: `mov_sob` |
| `atos/movimentos_fimsob.py` | Fim de sobrestamento: `mov_fimsob` |
| `atos/movimentos_despacho.py` | Despacho genérico: `despacho_generico` |
| `atos/movimentos_chips.py` | Chips/etiquetas: `def_chip` |

**Infra/Utilitários:**
| Arquivo | Papel |
|---|---|
| `atos/core.py` | Engine Selenium: verificação de carregamento, spinner, abas |

### WRAPPERS (instâncias factory-created)

| Arquivo | Conteúdo |
|---|---|
| `atos/wrappers_ato.py` | 45+ atos: `ato_bloq`, `ato_pesqliq`, `ato_prev`, `ato_ccs`, `ato_censec`, `ato_serp`, `ato_conv`, `ato_prevjud`, `ato_ceju`, `ato_meios`, `ato_instc`, `ato_laudo`, `ato_presc`, `ato_sobrestamento`, etc. |
| `atos/wrappers_pec.py` | 19+ wrappers PEC: `pec_ord`, `pec_sum`, `pec_bloqueio`, `pec_decisao`, `pec_idpj`, `pec_sigilo`, `pec_cpgeral`, `pec_mddgeral`, `pec_mddaud`, etc. |
| `atos/wrappers_mov.py` | 4 movimentos: `mov_arquivar`, `mov_exec`, `mov_aud`, `mov_prazo` |
| `atos/wrappers_utils.py` | Utilitários transversais: `visibilidade_sigilosos`, `esperar_insercao_modelo`, `preparar_campo_filtro_modelo` |

### FACHADAS (thin shims, não editar)

| Arquivo | Redireciona para |
|---|---|
| `atos/judicial.py` | `atos/judicial_fluxo.py` + `atos/judicial_helpers.py` |
| `atos/movimentos.py` | `atos/movimentos_*.py` |
| `atos/regras.py` | Registry de descoberta (importa todos os wrappers) |
| `atos/anexos/core.py` | Reexporta de `PEC/anexos/` |
| `atos/anexos/anexos_wrappers.py` | Reexporta de `PEC/anexos/anexos_wrappers.py` |

---

## 7. API de Interação Obrigatória (Fix) — Referência Rápida

Proibido usar `WebDriverWait`, `ActionChains`, `time.sleep` ou `element.click()` direto nos módulos de negócio.

### Clique
| Situação | Função | Import |
|---|---|---|
| Caso geral (headless-safe) | `click_headless_safe(driver, seletor)` | `from Fix.browser_suporte import click_headless_safe` |
| Elemento já encontrado | `safe_click_no_scroll(driver, elemento)` | `from Fix.core import safe_click_no_scroll` |

### Espera
| Situação | Função | Import |
|---|---|---|
| Esperar presença | `esperar_elemento(driver, seletor)` | `from Fix.core import esperar_elemento` |
| Aguardar renderização Angular | `aguardar_renderizacao_nativa(driver, seletor, modo='aparecer')` | `from Fix.core import aguardar_renderizacao_nativa` |

### Regras de Combinação
1. **Para clicar:** `click_headless_safe` com seletor — não buscar separado
2. **Para ler texto/atributo:** `esperar_elemento` → ler do elemento retornado
3. **Para checar estado:** `esperar_elemento` → `.get_attribute()`
4. **Para aguardar tabela/lista:** `aguardar_renderizacao_nativa` antes de `find_elements`
5. **Nunca:** `WebDriverWait(driver, N).until(EC...)` em módulos de negócio

---

## 8. Diretrizes de Código

### A. Busca de Elementos — SmartFinder + Cache
- Proibido `try css1, try css2, try xpath...` em módulos de negócio
- Usar `SmartFinder` com consulta a cache de seletores

### B. Waits — Fim do Polling
- Proibido `time.sleep()` e `WebDriverWait` em loops
- Usar `aguardar_renderizacao_nativa` (MutationObserver nativo)

### C. Sanitização de Logs
- Log principal: apenas mudanças de estado, sucessos, falhas críticas
- Sem "tentativa 1", "buscando...", "scroll realizado"

### D. Padrões Obrigatórios
| ID | Regra |
|---|---|
| P1 | Sem wrappers de uma linha em `Fix/core.py` — apenas re-exportações |
| P2 | Max 3 níveis de indentação; auxiliares `_privadas` imediatamente acima |
| P3 | Infra usa exceção tipada; nunca `return False` silencioso |
| P4 | Sem `time.sleep()` — usar `aguardar_renderizacao_nativa` |
| P5 | JS longo → arquivo `.js`; carregar via `carregar_js()` |
| P6 | Retornos complexos → `@dataclass` |
| P7 | Driver via context manager em orquestradores novos |
| P8 | Imports sempre no topo do módulo |

---

## 9. Referência Legada (`leg/`)

O diretório `leg/` contém as implementações pré-xcode. Usar **apenas como referência** de comportamento original, regras de negócio e seletores base. **Não modificar.**

Para consultar qualquer arquivo no estado anterior ao xcode:
```bash
git show 2ab0fca:<caminho/do/arquivo.py>
```

---

## 10. Registro de Bugs

| Data | ID | Módulo | Sintoma | Causa Raiz | Fix |
|---|---|---|---|---|---|
| 31/03/2026 | #001 | `Fix/navigation/filters.py` | `aplicar_filtro_100` retorna False silencioso | `com_retry` chamado com `log=True` mas implementação usa `log_enabled` → TypeError silencioso | Trocar `log=True` → `log_enabled=True` |

**Regra do Bug #001:** Preferir sempre `from Fix.core import com_retry` e usar `log=True`. Se importar direto de `Fix.selenium_base.retry_logic`, usar `log_enabled=True`.

---

## 11. Extensões Firefox (referência JS)

| Diretório | Descrição |
|---|---|
| `AVJT/` | Extensão principal: painéis, GIGS, cálculos, captcha, correios |
| `maispje/` | Extensão complementar: interface PJe avançada |

---

## 12. Ferramentas e Suporte

| Diretório | Descrição |
|---|---|
| `Agente/` | Extensão VSCode para PJePlus (TypeScript) |
| `AHK/` | Scripts AutoHotKey (UX Windows) |
| `scripts/` | Scripts auxiliares |
| `tools/` | Ferramentas de diagnóstico e análise |
| `docs/` | Documentação complementar |
| `xcode/` | Plano de simplificação (9 docs + README) |
| `_archive/` | Código removido/legado organizado por data |
| `ref/` | Referência externa e manifests de arquitetura |
| `cache/tessdata/` | Dados Tesseract OCR |
| `logs_execucao/` | Logs de execução |
| `cookies_sessoes/` | Cookies de sessão persistentes |

---

**INSTRUÇÃO FINAL PARA IA:** Este índice é o filtro de escopo primário. Use a Árvore de Decisão (Seção 0) para mapear qualquer tarefa a arquivos exatos. Use o Índice de Palavras-Chave (Seção 2) para localizar funções sem grep. Se nada cobrir o termo buscado, o grep é permitido — mas atualize este índice em seguida. Nunca edite arquivos marcados como SHIM ou LEGADO.
