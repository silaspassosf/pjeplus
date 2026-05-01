# ERASE.md — Plano de Limpeza PjePlus

> Objetivo: remover do projeto **apenas o que não é alcançável nem executável a partir de `x.py`**, sem derrubar contratos de importação, facades de compatibilidade ou imports lazy ainda vivos.

## Progresso

- [x] Iniciado
- [x] Documentar escopo e metodologia
- [x] Marcar cada passo diretamente em `erase.md`
- [x] Reenquadrar o plano pelo grafo real enraizado em `x.py`
- [x] Incluir imports dinâmicos e fluxos A-G no escopo lógico
- [x] Diferenciar "importado" de "realmente executado por fluxo"
- [ ] Executar limpeza incremental
- [ ] Revisar e validar alterações
- [x] Limpar imports mortos iniciais em `Mandado/utils.py`
- [x] Limpar imports mortos em `Mandado/processamento.py`
- [x] Limpar imports mortos em `Mandado/core.py`
- [x] Remover função morta `tempo_execucao` em `Fix/core.py`
- [x] Remover funções mortas em `Fix/utils_sleep.py`
- [x] Corrigir re-export redundante em `Fix/selenium_base/__init__.py`
- [x] Corrigir re-export redundante em `Fix/__init__.py`

## Escopo da Análise

| Item | Detalhe |
|---|---|
| Ponto de entrada | `x.py` (orquestrador unificado) |
| Fluxos rastreados | Menu A-G de `x.py`: Mandado, Prazo, P2B, PEC, Triagem e Petição |
| Pastas excluídas | `bianca/` e legado fora da raiz operacional; `Peticao/` e `Triagem/` entram no escopo porque `x.py` as importa dinamicamente |
| Wrappers protegidos | `wrappers_pec.py`, `wrappers_ato.py` e facades/shims de compatibilidade — export só sai com prova de não alcance |
| Metodologia | `x.py` como raiz → imports estáticos + imports dinâmicos/lazy + despacho por fluxo + execução real; AST local serve apenas para gerar candidatos |
| Gate executável | `test_imports.py` + smoke de `py x.py` sem executar fluxo completo |

## Resumo Quantitativo

| Métrica | Valor |
|---|---|
| Arquivos analisados | 248 |
| Módulos no escopo | 235 |
| **Funções não utilizadas** | **153** |
| **Imports mortos** | **1.143** |
| Arquivos com funções mortas | 50 |
| Arquivos com imports mortos | 68 |

---

> [!IMPORTANT]
> Os números acima são **triagem AST inicial**. Eles não autorizam remoção automática. A decisão final agora depende do grafo alcançável a partir de `x.py`, incluindo imports dinâmicos, facades de compatibilidade e checagens executáveis.

## Critério Operacional de Limpeza

Antes de remover qualquer import, função ou arquivo, classificar o item em uma destas camadas:

1. **Superfície de importação**: tudo o que precisa existir para `import x` e `test_imports.py` carregarem sem erro.
2. **Superfície de despacho por fluxo**: tudo o que `x.py` pode importar/chamar a partir dos menus A-G, inclusive imports dentro de função.
3. **Superfície de execução real**: o que é de fato chamado dentro de cada fluxo, após preservar a camada de importação.
4. **Candidato local AST**: import ou função que parece morta no arquivo, mas ainda precisa passar pelas 3 camadas acima.

Regras práticas:

- Import morto local só pode sair se o módulo continuar importável e o fluxo correspondente continuar íntegro.
- Re-export, shim e facade de compatibilidade não entram em remoção automática por parecerem ociosos localmente.
- `Triagem` e `Peticao` fazem parte do escopo porque `x.py` as importa de forma lazy.
- Função importada mas nunca executada em um fluxo continua candidata, mas só **depois** de estabilizar a superfície de importação.

---

## FASE 1 — Baseline de Import e Compatibilidade (obrigatória)

> [!IMPORTANT]
> Antes de qualquer limpeza mais agressiva, o projeto precisa manter verde a superfície de importação enraizada em `x.py`. Nesta fase, a lista abaixo é um inventário de candidatos, não uma fila automática de remoção.

### 1.1 Facades e re-exports: revisar export por export

Estes arquivos foram marcados pelo AST inicial como camadas de indireção com muitos imports locais mortos. Isso **não basta** para removê-los: primeiro é preciso confirmar se ainda participam do baseline de import, de imports dinâmicos ou de compatibilidade legada viva.

| Arquivo | Imports mortos | Triagem AST original |
|---|---|---|
| `Fix/__init__.py` | 107 | Limpar todos os re-exports não usados |
| `Fix/selenium_base/__init__.py` | 24 | Limpar todos |
| `Fix/progress/__init__.py` | 13 | Limpar todos |
| `Fix/navigation/__init__.py` | 4 | Limpar todos |
| `Fix/session/__init__.py` | 4 | Limpar todos |
| `Fix/drivers/__init__.py` | 8 | Limpar todos |
| `Fix/documents/__init__.py` | 10 | Limpar todos |
| `Fix/extraction/__init__.py` | 10 | Limpar todos |
| `Fix/monitoramento_progresso_unificado.py` | 29 | Re-export puro — limpar |
| `Fix/progresso_unificado.py` | 8 | Re-export puro — limpar |
| `Fix/extracao_indexacao.py` | 10 | Re-export puro — limpar |
| `Fix/extracao_processo.py` | 5 | Re-export puro — limpar |
| `Fix/variaveis.py` | 14 | Re-export puro — limpar |
| `Fix/exceptions.py` | 6 | Re-export puro — limpar |
| `Mandado/__init__.py` | 19 | Limpar |
| `Mandado/atos_wrapper.py` | 13 | Todos os imports são mortos |
| `PEC/__init__.py` | 10 | Limpar |
| `PEC/anexos/__init__.py` | 6 | Limpar |
| `atos/__init__.py` | 54 | Limpar |
| `SISB/__init__.py` | 23 | Limpar |
| `SISB/processamento/__init__.py` | 27 | Limpar |

> [!NOTE]
> Parte desta tabela já se mostrou viva pelo gate executável atual. Exemplos: superfícies de progresso, drivers, variáveis, smart finder, element wait e outros shims só podem ser reduzidos depois de provar não alcance a partir de `x.py`.

## Checagem rápida (2026-04-30)

- Verifiquei os seguintes arquivos para avaliar progresso da FASE 1:
  - `Fix/__init__.py`: limpeza aplicada parcialmente; re-exports redundantes principais removidos e o módulo compilou com sucesso.
  - `Fix/selenium_base/__init__.py`: contém re-exports padrão (limpeza não aplicada).
  - `Mandado/utils.py`: imports mortos de `typing` e stdlib removidos; o módulo compilou com sucesso.
  - `Mandado/__init__.py`: ainda expõe múltiplos re-exports (limpeza não aplicada).

- Conclusão parcial: `Fix/__init__.py` foi restaurado de HEAD e sofreu remoções seguras de re-exports redundantes.
  - foram removidos os imports duplicados `filtrofases` (de `.navigation`) e `buscar_documento_argos` (de `.documents`), mantendo a versão correta que já era re-exportada mais tarde.
  - `Fix/selenium_base/__init__.py` teve imports redundantes removidos (`criar_driver_VT`, `criar_driver_notebook`, `criar_driver_sisb_pc`, `criar_driver_sisb_notebook`, `credencial`, `escolher_opcao_inteligente`, `encontrar_elemento_inteligente`), e o módulo compilou com sucesso.
  - `Fix/core.py` teve imports mortos de compatibilidade removidos (`SimpleConfig`, `config` de `Fix.utils`), e o módulo compilou com sucesso.
  - `Fix/core.py` recebeu um novo corte de imports mortos e re-exports redundantes (`logging` duplicado, `ErroCollector` duplicado e bloco AHK/configuração não usado), e o módulo compilou com sucesso.
  - `Fix/debug_interativo.py` perdeu o import morto `Callable` de `typing`, e o módulo compilou com sucesso.
  - `Fix/element_wait.py` perdeu o import morto `Optional` de `typing`, e o módulo compilou com sucesso.
  - `Fix/utils_selectors.py` foi reduzido aos seletores compartilhados e ao helper de busca usado; helpers mortos foram removidos e o módulo compilou com sucesso.
  - `Fix/utils_collect.py` perdeu os helpers de coleta mortos, mantendo apenas as funções ainda usadas; o módulo compilou com sucesso.
  - `Fix/utils_paths.py` perdeu os helpers mortos `configurar_caminho_credencial` e `exibir_configuracao_atual`, e o módulo compilou com sucesso.
  - `Fix/utils_angular.py` foi reduzido aos helpers ainda usados; funções de apoio mortas foram removidas e o módulo compilou com sucesso.
  - `Fix/utils_error.py` foi simplificado ao contêiner `ErroCollector`; métodos mortos de relatório/exportação foram removidos e o módulo compilou com sucesso.
  - `Fix/utils_cookies.py` perdeu os helpers mortos de manutenção de arquivos de cookies, e o módulo compilou com sucesso.
  - `Fix/utils_drivers.py` perdeu os helpers mortos `configurar_driver_avancado` e `fechar_driver_safely`, e o módulo compilou com sucesso.
  - `Fix/headless_helpers.py` perdeu os helpers mortos `find_element_headless_safe` e `executar_com_retry_headless`, e o módulo compilou com sucesso.
  - `Fix/selectors_pje.py` perdeu os construtores mortos `seletor_processo_por_numero` e `seletor_pec_por_numero`, e o módulo compilou com sucesso.
  - `Fix/element_wait.py` perdeu os métodos mortos de navegação/customização, e o módulo compilou com sucesso.
  - `Fix/otimizacao_wrapper.py` perdeu os wrappers mortos `with_learning` e `usar_headless_safe`, e o módulo compilou com sucesso.
  - `Fix/log.py` perdeu o método morto `set_level` e o helper morto `tentar_seletores_com_registro`, e o módulo compilou com sucesso.
  - `Fix/progress/monitoramento.py` perdeu o exemplo morto `exemplo_uso_monitoramento_unificado`, e o módulo compilou com sucesso.
  - `Fix/gigs/__init__.py` perdeu os helpers mortos `_preencher_texto_colado` e `_find_button_by_text`, e o módulo compilou com sucesso.
  - `Fix/__init__.py`, `Fix/progress/__init__.py`, `Fix/navigation/__init__.py`, e `Fix/documents/__init__.py` também foram compilados com sucesso após a limpeza.
- Compatibilidade: os wrappers de compatibilidade `Fix.monitoramento_progresso_unificado`, `Fix.progresso_unificado`, `Fix.extracao_indexacao`, `Fix.extracao_processo` e `Mandado/atos_wrapper` são usados por código legado e permanecem como stubs/compatibility shims. Não são candidatos seguros para remoção total nesta fase.
- Próximo: continuar com a FASE 1 em ordem de prioridade, inspecionando o próximo conjunto de wrappers puros e stubs de compatibilidade para identificar remoções seguras ou ajustes de exportação.


### 1.2 Imports Mortos em Arquivos de Lógica

| Arquivo | Mortos | Exemplos principais |
|---|---|---|
| `Mandado/utils.py` | 60 | Todos os `from atos import ato_*`, selenium, typing |
| `Mandado/processamento.py` | 55 | Todos os `from atos import ato_*`, `from processamento_anexos import *` |
| `Mandado/core.py` | 26 | `from atos import ato_*`, typing extras |
| `Mandado/regras.py` | 23 | `from atos_wrapper import ato_*`, selenium, typing |
| `Fix/core.py` | 30 | selenium exceptions, AHK_*, config re-exports |
| `PEC/anexos/anexos_configuracao.py` | 23 | Todas as 23 imports são mortas (arquivo inteiro?) |
| `PEC/anexos/anexos_juntador_base.py` | 18 | selenium, Fix.core, typing |
| `PEC/anexos/anexos_juntador_helpers.py` | 18 | Idem |
| `PEC/anexos/anexos_juntador.py` | 15 | Idem |
| `PEC/anexos/anexos_juntador_metodos.py` | 15 | Idem |
| `Prazo/loop_base.py` | 21 | selenium, Fix.core, typing |
| `Prazo/p2b_fluxo.py` | 15 | Idem |
| `Prazo/__init__.py` | 13 | Idem |
| `SISB/utils.py` | 29 | selenium, typing |
| `SISB/helpers.py` | 26 | selenium, typing |
| `SISB/s_orquestrador.py` | 17 | selenium, typing |
| `atos/core.py` | 24 | selenium, typing |
| `atos/judicial.py` | 24 | selenium, typing |
| `carta/anexos.py` | 33 | selenium, Fix.core |
| `carta/carta.py` | 3 | selenium |
| `x.py` | 2 | `Tuple` (typing), `FirefoxProfile` (selenium) |

### 1.3 Padrão Recorrente: `from typing import ...` mortos

> [!NOTE]
> Praticamente todos os arquivos importam `Optional, Dict, List, Union, Tuple, Callable, Any` do `typing` mas só usam 1-3 deles. Limpar em massa.

---

## FASE 2 — Funções Mortas: Fix/ (SEGURO com cuidado)

> [!IMPORTANT]
> O `Fix/` é o framework base. As funções listadas abaixo **não são chamadas por nenhum arquivo do projeto**. Mas como é módulo de infraestrutura, vale verificar se há chamadas dinâmicas (strings, getattr) antes de apagar.

### Fix/utils_sleep.py — 10 funções mortas removidas

```
REMOVIDO:
  - sleep_random
  - sleep_progressivo
  - aguardar_url_mudar
  - aguardar_elemento_sumir
  - aguardar_texto_mudar
  - aguardar_loading_sumir
  - sleep_condicional
  - sleep_com_logging
  - aguardar_multiplas_condicoes
  - sleep_adaptativo

MANTER:
  - sleep (usado)
  - smart_sleep (usado)
  - sleep_fixed (usado)
  - aguardar_pagina_carregar (usado)
```

### Fix/utils_angular.py — 9 de 11 funções mortas

```
REMOVER:
  - aguardar_angular_requests (line 47)
  - clicar_elemento_angular (line 71)
  - preencher_campo_angular (line 87)
  - aguardar_elemento_angular_visivel (line 103)
  - verificar_angular_app (line 119)
  - aguardar_angular_digest (line 131)
  - obter_angular_scope (line 157)
  - executar_angular_expressao (line 182)
  - esperar_elemento_angular (line 304)

MANTER:
  - aguardar_angular_carregar (usado)
  - criar_js_otimizado (usado)
```

### Fix/utils_selectors.py — 7 de 8 funções mortas

```
REMOVER:
  - obter_seletor_pje (line 56)
  - gerar_seletor_dinamico (line 78)
  - detectar_seletor_elemento (line 108)
  - validar_seletor (line 154)
  - encontrar_seletor_estavel (line 168)
  - criar_seletor_fallback (line 198)
  - aplicar_estrategia_seletor (line 206)

MANTER:
  - SELECTORS_PJE (constante dict - usado)
  - buscar_seletor_robusto (usado)
```

### Fix/utils_collect.py — 6 de 9 funções mortas

```
REMOVER:
  - coletar_valor_atributo (line 25)
  - coletar_multiplos_elementos (line 37)
  - coletar_tabela_como_lista (line 47)
  - coletar_links_pagina (line 74)
  - coletar_dados_formulario (line 95)
  - coletar_dados_pagina (line 189)

MANTER:
  - coletar_texto_seletor (usado)
  - extrair_numero_processo (usado)
  - extrair_cpf_cnpj (usado)
```

### Fix/debug_interativo.py — 5 de 14 funções mortas

```
REMOVER:
  - obter_relatorio_debug (line 322)
  - inicializar_debug_interativo (line 329)
  - on_erro_critico (line 341)
  - is_debug_ativo (line 360)
  - salvar_relatorio_erro (line 259)
```

### Fix/utils_error.py — 4 de 6 mortas (só ErroCollector classe usada)

```
REMOVER:
  - registrar_erro (line 26)
  - registrar_sucesso (line 36)
  - gerar_relatorio (line 40)
  - exportar_csv (line 64)
```

### Fix/ — outras funções isoladas

| Arquivo | Função morta | Linha |
|---|---|---|
| `Fix/core.py` | `tempo_execucao` | 405 |
| `Fix/element_wait.py` | `navegar_e_esperar` | 176 |
| `Fix/element_wait.py` | `adicionar_elemento_customizado` | 199 |
| `Fix/element_wait.py` | `remover_elemento_customizado` | 214 |
| `Fix/extracao_bndt.py` | `_bndt_selecionar_operacao` | 226 |
| `Fix/extracao_bndt.py` | `_bndt_processar_selecoes` | 315 |
| `Fix/extracao_bndt.py` | `_bndt_gravar_e_confirmar` | 359 |
| `Fix/gigs/__init__.py` | `_preencher_texto_colado` | 81 |
| `Fix/gigs/__init__.py` | `_find_button_by_text` | 95 |
| `Fix/headless_helpers.py` | `find_element_headless_safe` | 156 |
| `Fix/headless_helpers.py` | `executar_com_retry_headless` | 186 |
| `Fix/log.py` | `tentar_seletores_com_registro` | 524 |
| `Fix/log.py` | `set_level` | 235 |
| `Fix/otimizacao_wrapper.py` | `with_learning` | 22 |
| `Fix/otimizacao_wrapper.py` | `usar_headless_safe` | 58 |
| `Fix/progress.py` | `marcar_progresso_executado_p2b` | 397 |
| `Fix/progress.py` | `marcar_progresso_executado_mandado` | 435 |
| `Fix/progress/monitoramento.py` | `exemplo_uso_monitoramento_unificado` | 647 |
| `Fix/selectors_pje.py` | `seletor_processo_por_numero` | 59 |
| `Fix/selectors_pje.py` | `seletor_pec_por_numero` | 63 |
| `Fix/selenium_base/element_interaction.py` | `_tentar_click_padrao` | 544 |
| `Fix/selenium_base/element_interaction.py` | `_tentar_click_javascript` | 571 |
| `Fix/selenium_base/element_interaction.py` | `_tentar_click_actionchains` | 595 |
| `Fix/selenium_base/element_interaction.py` | `_tentar_click_javascript_avancado` | 619 |
| `Fix/utils_cookies.py` | `limpar_cookies_antigos` | 159 |
| `Fix/utils_cookies.py` | `listar_cookies_salvos` | 178 |
| `Fix/utils_drivers.py` | `configurar_driver_avancado` | 117 |
| `Fix/utils_drivers.py` | `fechar_driver_safely` | 135 |
| `Fix/utils_observer.py` | `aguardar_colecao_sync` | 42 |
| `Fix/utils_paths.py` | `configurar_caminho_credencial` | 152 |
| `Fix/utils_paths.py` | `exibir_configuracao_atual` | 171 |
| `Fix/variaveis_client.py` | `execucao_gigs` | 44 |
| `Fix/variaveis_client.py` | `associados` | 67 |

> [!WARNING]
> `fechar_driver_safely` é usada indiretamente por `Fix/utils.py` → `finalizar_driver()` que delega para ela. Porém a análise AST flagou como morta porque `finalizar_driver` em `utils.py` importa localmente (`from .utils_drivers import fechar_driver_safely`). **NÃO remover `fechar_driver_safely`** — é um falso positivo.

---

## FASE 3 — Funções Mortas: Módulos de Negócio

### Mandado/

| Arquivo | Função morta | Linha | Risco |
|---|---|---|---|
| `Mandado/core.py` | `_main_legado` | 449 | SEGURO |
| `Mandado/processamento.py` | `_lazy_import_mandado` | 54 | SEGURO |
| `Mandado/processamento_anexos.py` | `_aguardar_icone_plus` | 44 | CUIDADO |
| `Mandado/processamento_anexos.py` | `_buscar_icone_plus_direto` | 62 | CUIDADO |
| `Mandado/processamento_anexos.py` | `_extrair_resultado_sisbajud` | 142 | CUIDADO |

### PEC/

| Arquivo | Função morta | Linha | Risco |
|---|---|---|---|
| `PEC/core.py` | `iniciarfluxorobusto` | 83 | SEGURO |
| `PEC/core_recovery.py` | `verificar_e_recuperar_acesso_negado` | 9 | SEGURO |
| `PEC/processamento.py` | `_lazy_import_pec` | 2 | SEGURO |
| `PEC/processamento_fluxo.py` | `callback_pec_centralizado` | 82 | CUIDADO |
| `PEC/regras.py` | `determinar_acao_por_observacao` | 22 | SEGURO |
| `PEC/regras.py` | `get_cached_rules` | 30 | SEGURO |
| `PEC/regras.py` | `chamar_funcao_com_assinatura_correta` | 47 | SEGURO |
| `PEC/anexos/anexos_extracao.py` | `extrair_numero_processo_da_pagina` | 19 | SEGURO |

### Prazo/

| Arquivo | Função morta | Linha | Risco |
|---|---|---|---|
| `Prazo/criteria_matcher.py` | `buscar_prazo_por_tipo` | 115 | SEGURO |
| `Prazo/criteria_matcher.py` | `buscar_primeiro_prazo` | 138 | SEGURO |
| `Prazo/loop_api.py` | `_verificar_processos_xs_paralelo` | 91 | SEGURO |
| `Prazo/loop_base.py` | `clicar_com_multiplos_seletores` | 85 | SEGURO |
| `Prazo/loop_ciclo1_filtros.py` | `_ciclo1_aplicar_filtro_fases` | 4 | SEGURO |
| `Prazo/loop_ciclo1_movimentacao.py` | `_ciclo1_marcar_todas` | 13 | SEGURO |
| `Prazo/loop_ciclo2_processamento.py` | `ciclo2_processar_livres_apenas_uma_vez` | 179 | SEGURO |
| `Prazo/loop_helpers.py` | `selecionar_processos_nao_livres` | 46 | SEGURO |
| `Prazo/p2b_api.py` | `localizar_documento_relevante_api` | 114 | SEGURO |
| `Prazo/p2b_api.py` | `extrair_conteudo_documento_api` | 209 | SEGURO |
| `Prazo/p2b_core.py` | `ato_pesqliq_callback` | 339 | SEGURO |
| `Prazo/p2b_core.py` | `aplicar` | 358 | SEGURO |
| `Prazo/p2b_fluxo_documentos.py` | `_extrair_texto_documento` | 171 | SEGURO |
| `Prazo/p2b_prazo.py` | `executar_prazo_com_otimizacoes` | 93 | SEGURO |
| `Prazo/p2b_prazo.py` | `_gerenciar_abas_apos_processo` | 442 | SEGURO |

### atos/ (respeitando proteção dos wrappers)

| Arquivo | Função morta | Linha | Risco |
|---|---|---|---|
| `atos/comunicacao_finalizacao.py` | `remover_destinatarios_invalidos` | 386 | CUIDADO |
| `atos/comunicacao_finalizacao.py` | `_aguardar_confirmar_save_js` | 438 | CUIDADO |
| `atos/comunicacao_finalizacao.py` | `limpar_destinatarios_existentes` | 741 | CUIDADO |
| `atos/core.py` | `aguardar_e_verificar_detalhe` | 315 | SEGURO |
| `atos/judicial_fluxo.py` | `_verificar_reaplicar_sigilo_pec` | 77 | CUIDADO |
| `atos/movimentos_chips.py` | `def_chip_custom` | 110 | SEGURO |
| `atos/movimentos_fluxo.py` | `verificar_minuta_preenchida` | 756 | SEGURO |
| `atos/movimentos_navegacao.py` | `_obter_nome_tarefa_via_api` | 88 | SEGURO |
| `atos/movimentos_navegacao.py` | `mov_cls` | 363 | SEGURO |
| `atos/wrappers_mov.py` | `mov_para_analise` | 93 | SEGURO |
| `atos/wrappers_mov.py` | `mov_para_comunicacoes` | 101 | SEGURO |
| `atos/wrappers_pec.py` | `wrapper_pec_ord_com_domicilio` | 238 | SEGURO |
| `atos/wrappers_pec.py` | `wrapper_pec_sum_com_domicilio` | 297 | SEGURO |

> [!NOTE]
> Em `wrappers_pec.py`, todas as instâncias de `make_comunicacao_wrapper(...)` (como `pec_bloqueio`, `pec_decisao`, etc.) são **USADAS** pelo fluxo de regras do PEC. Apenas as duas funções `def` no final (`wrapper_pec_ord_com_domicilio` e `wrapper_pec_sum_com_domicilio`) são mortas.

### SISB/

| Arquivo | Função morta | Linha | Risco |
|---|---|---|---|
| `SISB/core.py` | `processar_endereco` | 1114 | SEGURO |
| `SISB/performance.py` | `optimized_element_wait` | 369 | SEGURO |
| `SISB/performance.py` | `batched_form_fill` | 384 | SEGURO |
| `SISB/performance.py` | `cached_selector_lookup` | 408 | SEGURO |
| `SISB/performance.py` | `parallel_series_processing` | 421 | SEGURO |
| `SISB/performance.py` | `smart_cache_operation` | 435 | SEGURO |
| `SISB/performance.py` | `cache_element` | 235 | SEGURO |
| `SISB/performance.py` | `get_cached_element` | 244 | SEGURO |
| `SISB/performance.py` | `clear_expired_cache` | 277 | SEGURO |
| `SISB/processamento/ordens_acao.py` | `_classificar_selects` | 53 | CUIDADO |
| `SISB/processamento/ordens_acao.py` | `_acao_com_saldo` | 87 | CUIDADO |
| `SISB/processamento/ordens_acao.py` | `_acao_nao_resposta` | 144 | CUIDADO |
| `SISB/s_orquestrador.py` | `trigger_event` | 169 | SEGURO |
| `SISB/s_orquestrador.py` | `safe_execute_script` | 176 | SEGURO |
| `SISB/s_orquestrador.py` | `otimizar_performance_sisbajud` | 210 | SEGURO |
| `SISB/standards.py` | 14 classes/funções | vários | SEGURO |

### Outros

| Arquivo | Função morta | Linha | Risco |
|---|---|---|---|
| `dom.py` | `buscar_processos_dom_eletronico` | 56 | SEGURO |
| `dom.py` | `navigate_to_list` | 104 | SEGURO |
| `p2.py` | `buscar_peticoes_escaninho_direto` | 5 | SEGURO |
| `apiaud.py` | `_normalizar_lista` | 19 | SEGURO |
| `carta/anexos.py` | `extrair_numero_processo_da_pagina` | 96 | SEGURO |
| `carta/carta.py` | `teste_juntada_carta_html` | 1021 | SEGURO |
| `api/variaveis_client.py` | `execucao_gigs` | 44 | SEGURO |

---

## FASE 4 — Arquivos Potencialmente Inteiros para Remoção

> [!CAUTION]
> Estes arquivos só entram em remoção total depois de quatro provas simultâneas: nenhuma aresta enraizada em `x.py`, nenhum import lazy/dinâmico restante, `test_imports.py` verde e smoke de `py x.py` sem erro estrutural.

| Arquivo | Sinal AST | Situação atual |
|---|---|---|
| `Fix/monitoramento_progresso_unificado.py` | 100% imports mortos | **Bloqueado**: owner ativo do progresso unificado e base de compatibilidade |
| `Fix/progresso_unificado.py` | 100% imports mortos | **Bloqueado**: shim importado por fluxos ainda vivos |
| `Fix/extracao_indexacao.py` | 100% imports mortos | Validar alcance real antes de qualquer remoção |
| `Fix/extracao_processo.py` | 100% imports mortos | Validar alcance real antes de qualquer remoção |
| `PEC/anexos/anexos_configuracao.py` | 100% imports mortos | Candidato forte, mas ainda precisa prova de não alcance |
| `Mandado/atos_wrapper.py` | 100% imports mortos | Compat shim; não remover sem prova de não alcance |
| `Mandado/processamento.py` | 95%+ morto | Wrapper legado; tratar por fatiamento, não por exclusão direta |
| `Fix/utils_selectors.py` | 87% funções mortas | Reduzir só após separar importação de execução real |
| `Fix/utils_angular.py` | 82% funções mortas | Reduzir só após separar importação de execução real |
| `Fix/utils_sleep.py` | 71% funções mortas | Reduzir só após separar importação de execução real |
| `Fix/utils_collect.py` | 67% funções mortas | Reduzir só após separar importação de execução real |
| `Fix/utils_error.py` | 67% funções mortas | Reduzir só após separar importação de execução real |
| `SISB/standards.py` | 33% funções mortas | Candidato tardio; não é prioridade enquanto o grafo raiz ainda estiver em ajuste |

---

## FASE 5 — `x.py` como raiz: importado vs executado por fluxo

`x.py` define três superfícies diferentes que precisam ser tratadas separadamente:

1. **Imports estáticos no topo do módulo**
  - `Fix.core.finalizar_driver`
  - `Fix.utils.login_cpf`
  - `Prazo.loop_prazo`
  - `PEC.orquestrador.executar_fluxo_novo_simplificado`
  - `Mandado.processamento_api.processar_mandados_devolvidos_api`

2. **Imports dinâmicos/lazy dentro de fluxo**
  - `Triagem.runner.run_triagem` em `executar_triagem`
  - `Peticao.pet.run_pet` em `executar_pet`
  - `Prazo.fluxo_api.processar_gigs_sem_prazo_p2b` e `testar_gigs_sem_prazo` em `executar_p2b`
  - `Fix.otimizacao_wrapper.inicializar_otimizacoes` e `finalizar_otimizacoes` em `main`

3. **Execução real dentro de cada fluxo**
  - Nem todo símbolo importado por um módulo alcançado por `x.py` é necessariamente executado em todos os caminhos.
  - Essas funções continuam candidatas a remoção, mas só depois de estabilizar a superfície de importação.

Regra desta fase:

- Se o símbolo é necessário para `import x` ou para carregar um fluxo A-G, ele **não** entra em remoção imediata.
- Se o símbolo só é importado por um módulo alcançado, mas nunca é chamado em nenhum caminho real daquele fluxo, ele entra em "candidato por execução".
- O corte deve ser por fatias: primeiro manter o módulo importável; depois reduzir helpers e imports que não participam da execução real.

### Montagem 2 — candidatos por execução no grafo atual de `x.py`

Esta montagem não substitui a análise completa. Ela é uma **amostra curta e aplicável** dos símbolos que hoje parecem estar fora da execução real dos fluxos puxados por `x.py`.

#### Mandado

- `Mandado/core.py::_main_legado`
  - Candidato forte por execução: `x.py` entra por `Mandado.processamento_api.processar_mandados_devolvidos_api`, não pelo fluxo standalone legado.
- `Mandado/processamento.py::_lazy_import_mandado`
  - Candidato forte por execução: lazy loader do fluxo legado; não aparece no caminho API atual.
- `Mandado/processamento_anexos.py::_aguardar_icone_plus`
- `Mandado/processamento_anexos.py::_buscar_icone_plus_direto`
- `Mandado/processamento_anexos.py::_extrair_resultado_sisbajud`
  - Candidatos por execução: sem call sites no código vivo observado; validar só ausência de dispatch dinâmico antes de remover.
  - Checagem final de consumidores: a busca no workspace operacional não encontrou usos fora dos arquivos donos.

#### Prazo

- `Prazo/p2b_api.py::localizar_documento_relevante_api`
- `Prazo/p2b_api.py::extrair_conteudo_documento_api`
  - Candidatos fortes por execução: `x.py` entra por `Prazo.fluxo_api.processar_gigs_sem_prazo_p2b`, e o fluxo ativo não chama esses auxiliares.
- `Prazo/criteria_matcher.py::buscar_prazo_por_tipo`
- `Prazo/criteria_matcher.py::buscar_primeiro_prazo`
  - Candidatos por execução: sem uso observado no fluxo atual de prazo.
  - Checagem final de consumidores: não apareceram consumidores operacionais fora de `Prazo/p2b_api.py` e `Prazo/criteria_matcher.py`; as demais ocorrências ficaram restritas à própria documentação do módulo.

#### PEC

- `PEC/core.py::iniciarfluxorobusto`
  - Candidato por execução: `x.py` entra por `PEC.orquestrador.executar_fluxo_novo_simplificado`, não pelo core legado.
- `PEC/processamento.py::_lazy_import_pec`
  - Candidato por execução: stub de compatibilidade fora do caminho atual do orquestrador.
- `PEC/regras.py::determinar_acao_por_observacao`
- `PEC/regras.py::get_cached_rules`
- `PEC/regras.py::chamar_funcao_com_assinatura_correta`
  - Candidatos por execução com checagem final concluída: o orquestrador atual usa `regras_pec.determinar_regra`, e a busca no workspace operacional não encontrou consumidores vivos desses três símbolos fora de `PEC/regras.py`.
  - Ocorrências restantes ficaram restritas a `ref/`, dumps/documentação (`00dump.md`, `LEGADO.md`, `PEC/ANALISE_REFATORACAO_MODULAR.md`) e ao `__all__` stale de `PEC/__init__.py`.

#### Fix

- `Fix/otimizacao_wrapper.py::with_learning`
- `Fix/otimizacao_wrapper.py::usar_headless_safe`
  - Candidatos por execução: no caminho atual, `x.py` usa apenas `inicializar_otimizacoes` e `finalizar_otimizacoes`.
- `Fix/selectors_pje.py::seletor_processo_por_numero`
- `Fix/selectors_pje.py::seletor_pec_por_numero`
  - Candidatos fortes por execução: sem call sites observados no código vivo.
  - Checagem final de consumidores: a busca no workspace operacional não encontrou usos fora dos arquivos donos.
  - Nota: o antigo bloco de `Fix/element_wait.py` (`navegar_e_esperar`, `adicionar_elemento_customizado`, `remover_elemento_customizado`) já não existe no arquivo ativo e não entra mais no lote atual.

#### SISB

- `SISB/processamento/ordens_acao.py::_classificar_selects`
- `SISB/processamento/ordens_acao.py::_acao_com_saldo`
- `SISB/processamento/ordens_acao.py::_acao_nao_resposta`
  - Candidatos por execução: sem consumidores operacionais encontrados fora do arquivo dono.
- `SISB/s_orquestrador.py::trigger_event`
- `SISB/s_orquestrador.py::safe_execute_script`
- `SISB/s_orquestrador.py::otimizar_performance_sisbajud`
  - Candidatos por execução: sem consumidores operacionais encontrados fora do arquivo dono.

#### atos

- `atos/comunicacao_finalizacao.py::remover_destinatarios_invalidos`
- `atos/comunicacao_finalizacao.py::_aguardar_confirmar_save_js`
- `atos/comunicacao_finalizacao.py::limpar_destinatarios_existentes`
  - Candidatos por execução: sem consumidores operacionais encontrados fora do arquivo dono.
- `atos/core.py::aguardar_e_verificar_detalhe`
  - Sem call site vivo encontrado; resta um import morto em `Fix/extracao.py`, então a ordem segura é limpar esse import antes de remover a função.
- `atos/judicial_fluxo.py::_verificar_reaplicar_sigilo_pec`
- `atos/movimentos_chips.py::def_chip_custom`
- `atos/movimentos_fluxo.py::verificar_minuta_preenchida`
- `atos/movimentos_navegacao.py::_obter_nome_tarefa_via_api`
- `atos/movimentos_navegacao.py::mov_cls`
- `atos/wrappers_mov.py::mov_para_analise`
- `atos/wrappers_mov.py::mov_para_comunicacoes`
  - Candidatos por execução: sem consumidores operacionais encontrados fora dos arquivos donos.

Regra de aplicação desta montagem:

- Itens marcados como **candidato forte por execução** entram primeiro no lote de verificação local.
- Itens marcados como **bloqueados por compatibilidade** não entram em remoção até provar ausência de consumidores externos ou de imports históricos ainda vivos.

O próprio `x.py` já tinha 2 imports mortos óbvios:

```diff
- from typing import Dict, Any, Optional, Tuple
+ from typing import Dict, Any, Optional

- from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
  # (nunca usado)
```

- [x] Limpar imports mortos em `x.py`

---

## Regras de Segurança

> [!CAUTION]
> **ANTES de apagar qualquer função:**
> 1. Verificar se não é chamada via `getattr()`, string dinâmica, ou dicionário de callbacks
> 2. Verificar se não é registrada em algum mapa/registry (ex: `REGRAS_MAP = {'xs ord': wrapper_pec_ord_com_domicilio}`)
> 3. Procurar por referências em arquivos `.js`, `.json`, ou `.md` que possam indicar uso externo
> 4. **Falsos positivos conhecidos:** `fechar_driver_safely` é usada via import local em `finalizar_driver` — NÃO remover

### Ordem Recomendada de Execução

```
1. FASE 1 (baseline de import + compatibilidade) → manter `test_imports.py` verde
2. FASE 5 (`x.py` como raiz) → separar importado, despachado e realmente executado
3. FASE 2 (Fix/ funções) → reduzir helpers/imports só depois da camada de importação estar estável
4. FASE 3 (módulos de negócio) → validar por fluxo após cada lote pequeno
5. FASE 4 (remoção de arquivos) → só no final, com prova de não alcance
```

### Validação Pós-Limpeza

```bash
# 1. Verificar baseline de imports (com a .venv ativa)
py test_imports.py

# 2. Smoke do orquestrador sem executar fluxo completo
py x.py

# 3. Se o lote tocou módulos específicos, compilar só os arquivos alterados
py -m py_compile arquivo1.py arquivo2.py
```

---

## Dados Brutos

Os resultados completos da análise AST estão em:
- [erase_output.txt](file:///d:/PjePlus/tools/erase_output.txt) — Funções mortas por arquivo
- [erase_imports_output.txt](file:///d:/PjePlus/tools/erase_imports_output.txt) — Imports mortos por arquivo
- [erase_analysis_results.json](file:///d:/PjePlus/tools/erase_analysis_results.json) — JSON com dados completos (used_by, line numbers)
