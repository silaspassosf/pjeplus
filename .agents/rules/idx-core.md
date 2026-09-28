---
trigger: always_on
---

# PJePlus — Índice Core (Quick Reference + Árvore de Decisão)

> Este é o núcleo sempre carregado do índice do projeto. O detalhe completo (mapa de domínios cross-cutting, índice de palavras-chave, cadeias de chamada por fluxo, catálogo completo de `atos/`, API de interação obrigatória, diretrizes de código P1–P9, referência legada) está em `@idx.md` na raiz do projeto — leia sob demanda quando esta tabela não cobrir a tarefa.

**LEITURA OBRIGATÓRIA:** filtro de escopo primário e inegociável. Antes de qualquer grep/glob/busca exploratória, consulte esta tabela e a árvore de decisão abaixo. Se não cobrir o termo buscado, a busca é permitida — mas `idx.md` deve ser atualizado ao final. Buscas genéricas sem consulta prévia são proibidas.

---

## Quick Reference Card — Acesso Direto (Sem Busca)

> GARANTIA DE NO-SEARCH: se a tarefa corresponde a uma linha desta tabela, vá direto ao arquivo/função indicados. Proibido usar grep/search antes de consultar esta tabela.

### Executor & Motor

| Tarefa | Arquivo | Função/Símbolo |
|---|---|---|
| Rodar o projeto | `pw.py` | `main()` — `py pw.py` (ponto de entrada real, não `x.py`) |
| Orquestrador de sessão | `x.py` | `main()` — loop driver + fluxos |
| Criar e logar driver | `x.py` | `criar_e_logar_driver(driver_type)` |
| Driver headless (login via janela visível) | `x.py` | `_criar_driver_headless_com_login_visivel()` |
| Selecionar ambiente + fluxo (menus / env) | `x.py` | `selecionar_ambiente_e_fluxo()` |
| Mapa fluxo → handler | `x.py` | `FLOW_HANDLERS` (dict A–H, L772) |
| Backend Playwright | `play/pjeplay/` | `pjeplay.iniciar()` |

### Driver, Sessão & DOM

| Tarefa | Arquivo | Função/Símbolo |
|---|---|---|
| Criar driver (PC/VT/headless) | `Fix/core.py` | `criar_driver_PC`, `criar_driver_VT`, `criar_driver_notebook` |
| Login (CPF/auto/manual) | `Fix/utils.py` | `login_cpf`, `login_automatico`, `login_manual` |
| **Clicar (caso geral)** | `Fix/browser_suporte.py` | `click_headless_safe(driver, seletor)` |
| Esperar presença de elemento | `Fix/core.py` | `esperar_elemento(driver, seletor)` |
| **Aguardar Angular renderizar** | `Fix/core.py` | `aguardar_renderizacao_nativa(driver, sel)` |
| Busca inteligente de seletor | `Fix/core.py` | `buscar_seletor_robusto`, `encontrar_elemento_inteligente` |

### API REST, Extração & Negócio

| Tarefa | Arquivo | Função/Símbolo |
|---|---|---|
| Cliente API principal | `Fix/variaveis.py` | `PjeApiClient` |
| Extrair PDF/documento | `Fix/extracao.py` | `extrair_pdf`, `extrair_documento` |
| Indexar processos | `Fix/extracao.py` | `indexar_processos` |
| Logger estruturado | `Fix/diagnostico_runtime.py` | `PJELogger`, `log_start`, `log_sucesso`, `log_erro` |

### Entry Points de Negócio (chamados por `x.py`)

| Fluxo | Arquivo | Função |
|---|---|---|
| Mandado | `Mandado/entrada_api.py` | `processar_mandados_devolvidos_api` |
| Prazo | `Prazo/loop_orquestrador.py` | `loop_prazo` |
| P2B (GIGS sem prazo) | `Prazo/p2b_gateway.py` | `processar_gigs_sem_prazo_p2b` |
| PEC | `PEC/orquestrador.py` | `executar_fluxo_novo_simplificado` |
| Triagem | `bianca/triagem_engine.py` | `run_triagem` |
| Petição | `Peticao/runtime_pet.py` | `run_pet` |
| SISBAJUD | `SISB/core.py` | `iniciar_sisbajud` |
| DOM (Domicílio Eletrônico) | `bianca/dom_engine.py` | `run_dom_api` (não `run_dom`) |

### Atos Judiciais & Scripts JS

| Tarefa | Arquivo/Símbolo |
|---|---|
| Ato judicial (motor) | `atos/judicial_fluxo.py` — `fluxo_cls`, `ato_judicial`, `make_ato_wrapper` |
| 45+ atos prontos | `atos/wrappers_ato.py` |
| Comunicação judicial | `atos/comunicacao.py` — `comunicacao_judicial` |
| 19+ wrappers PEC | `atos/wrappers_pec.py` |
| Movimentar processo | `atos/movimentos_fluxo.py` — `mov`, `mov_simples` |
| PJeTools Orquestrador TM | `Script/pjetools.user.js` |
| Motor AutoActions | `Script/autoactions/autoactions.js` |

---

## Árvore de Decisão de Escopo

Para qualquer tarefa, responda em sequência para encontrar os arquivos exatos:

```
TAREFA: "preciso fazer X"

Q1: X envolve driver/login/sessão?
  → SIM: Fix/core.py (driver factory), Fix/utils.py (login_cpf), Fix/browser_suporte.py (validação)
Q2: X envolve API REST do PJe (GIGS, timeline, documentos, partes)?
  → SIM: Fix/variaveis.py (PjeApiClient)
Q3: X envolve extração de PDF/HTML, GIGS, BNDT, indexação de processos?
  → SIM: Fix/extracao.py
Q4: X envolve CKEditor, coleta de conteúdo, clipboard, recovery de driver?
  → SIM: Fix/utils.py
Q5: X envolve logger, debug interativo, medir_tempo?
  → SIM: Fix/diagnostico_runtime.py, Fix/core.py (medir_tempo)
Q6: X envolve progresso/checkpoint/retomada de execução?
  → SIM: Fix/monitoramento_progresso_unificado.py
Q7: X envolve click/espera/preenchimento em modais PJe?
  → SIM: Fix/core.py (safe_click, esperar_elemento, preencher_campo, aguardar_renderizacao_nativa, click_headless_safe)
Q8: X é um fluxo de negócio específico?
  → Mandado: Mandado/entrada_api.py → Mandado/fluxo_argos.py → Mandado/apoio_fluxos.py → Mandado/regras.py
  → Prazo (ciclo1+2+3): Prazo/loop_orquestrador.py → Prazo/loop_lote.py → Prazo/loop_execucao_final.py
  → P2B: Prazo/p2b_gateway.py → Prazo/p2b_regras_execucao.py → Prazo/p2b_documentos.py
  → PEC: PEC/runtime_pec.py → PEC/regras_execucao.py → atos/comunicacao*.py
  → Triagem: bianca/triagem_engine.py
  → Petição: Peticao/runtime_pet.py
  → SISBAJUD: SISB/core.py
Q9: X é um ato judicial (conclusão, minutar, assinar)?
  → SIM: atos/judicial_fluxo.py, atos/judicial_navegacao.py
Q10: X é uma comunicação judicial (PEC, expedição)?
  → SIM: atos/comunicacao.py, atos/comunicacao_preenchimento.py, atos/comunicacao_destinatarios.py
Q11: X é um movimento processual (navegar entre tarefas)?
  → SIM: atos/movimentos_fluxo.py, atos/movimentos_navegacao.py
Q12: X é um wrapper/instância concreta de ato ou comunicação?
  → Ato: atos/wrappers_ato.py | Comunicação: atos/wrappers_pec.py | Movimento: atos/wrappers_mov.py
Q13: X envolve anexos/juntada de documentos?
  → SIM: PEC/anexos/anexos_juntador_base.py, PEC/anexos/anexos_wrappers.py
  → NÃO: buscar termo específico no Índice de Palavras-Chave (Seção 2 de @idx.md)
```

---

## Regras Críticas (sempre aplicáveis)

- **P9 — Import de interação:** funções de interação (`safe_click_no_scroll`, `wait_for_clickable`, `safe_click`, `esperar_elemento`, `aguardar_renderizacao_nativa`) DEVEM vir de `Fix.core`, nunca de `Fix.selenium_base` (cópia congelada, quebra com backend Playwright). Ver `@idx.md` Seção 8-D para detalhe completo.
- **Nunca editar SHIMS** (`Fix/abas.py`, `Fix/headless_helpers.py`, `Fix/element_wait.py`, etc. — lista completa em `@idx.md` Seção 4) — redirecionam para implementações reais.
- **Nunca editar LEGADO** (`leg/`, `Mandado/core.py`, `Mandado/processamento.py`, `_archive/`) — apenas referência histórica.
- **Diretórios duplicados:** usar `bianca/` (não `Triagem/`) para Triagem e DOM; usar `Fix/variaveis.py` (não `api/` na raiz) para PjeApiClient.
- **Proibido:** `WebDriverWait`, `ActionChains`, `time.sleep()` ou `.click()` direto em módulos de negócio — ver API de Interação Obrigatória em `@idx.md` Seção 7.

**INSTRUÇÃO FINAL:** este core é o filtro de escopo primário. Se a tarefa não for coberta aqui, leia `@idx.md` para o índice de palavras-chave completo, cadeias de chamada por fluxo, e catálogo detalhado de `atos/`. Se nada cobrir o termo buscado, o grep é permitido — mas atualize `idx.md` em seguida.
