# Plano de Implementação — Pasta `bianca`

**Projeto:** bianca — execução standalone de Triagem + DOM  
**Data:** 2026-05-04  
**Status:** Planejamento  
**Objetivo:** A pasta `bianca/` deve ser capaz de executar os módulos `triagem` e `dom` de `x.py` de forma completamente autônoma, sem depender da estrutura de pastas do projeto principal.

---

## Visão Geral

`bianca/` é um projeto Python standalone que replica apenas os dois fluxos necessários:

- **Triagem Inicial** — `run_triagem(driver)` de `Triagem/runtime_triagem.py`
- **DOM Eletrônico** — `run_dom(driver)` de `Triagem/dom.py`

O login é **exclusivamente manual** (CPF + senha digitados no terminal). Nenhuma variável de ambiente, arquivo de config com credenciais, ou automação de login é incluída.

---

## Grafo de Dependências

```
main.py  (entry point)
│
├── driver.py           ← Fix.core (criar_driver_pc) + login manual interativo
│
├── triagem_engine.py   ← runtime_triagem.py + analise_execucao.py
│   ├── triagem_regras.py   ← coleta.py + regras.py
│   ├── api_client.py       ← api/variaveis_client.py + variaveis_helpers.py
│   ├── selenium_utils.py   ← Fix.core + Fix.browser_suporte
│   ├── extracao.py         ← Fix.extracao (subconjunto relevante)
│   └── utils.py            ← utilitarios_processamento + Fix.tipos + core/rule_registry
│
├── dom_engine.py       ← Triagem/dom.py
│   ├── selenium_utils.py
│   ├── extracao.py
│   └── atos_utils.py   ← atos/movimentos_chips + atos/wrappers_pec
│
└── config.py           ← caminhos gecko, constantes CEP/salário
```

**Fontes no projeto principal:**

| Arquivo bianca            | Extrai de                                                     |
|---------------------------|---------------------------------------------------------------|
| `config.py`               | `Triagem/runtime_triagem.py` (constantes), `Triagem/constants.py` |
| `driver.py`               | `Fix/core.py` (criar_driver_pc), `Fix/utils.py` (login_cpf stub) |
| `utils.py`                | `utilitarios_processamento.py`, `Fix/tipos.py`, `core/rule_registry.py` |
| `selenium_utils.py`       | `Fix/core.py`, `Fix/browser_suporte.py`, `Fix/selenium_base/__init__.py` |
| `api_client.py`           | `api/variaveis_client.py`, `api/variaveis_helpers.py`         |
| `extracao.py`             | `Fix/extracao.py` (criar_gigs, criar_comentario, criar_lembrete_posit, abrir_detalhes_processo, indexar_processos, abas) |
| `atos_utils.py`           | `atos/movimentos_chips.py` (def_chip), `atos/wrappers_pec.py` (pec_sumc/2, pec_ordc/2) |
| `triagem_regras.py`       | `Triagem/coleta.py`, `Triagem/regras.py`                      |
| `triagem_engine.py`       | `Triagem/runtime_triagem.py`, `Triagem/analise_execucao.py`   |
| `dom_engine.py`           | `Triagem/dom.py`                                              |
| `main.py`                 | `x.py` (executar_triagem, executar_dom, menus, TeeOutput)     |

---

## Arquitetura de Arquivos

```
bianca/
├── config.py              (~80 linhas)   — caminhos e constantes
├── driver.py              (~120 linhas)  — Firefox + login manual
├── utils.py               (~280 linhas)  — tipos, resultado_ok/falha, run_batch, RuleRegistry
├── selenium_utils.py      (~450 linhas)  — operações Selenium (Fix.core subset)
├── api_client.py          (~420 linhas)  — PjeApiClient, session_from_driver, paginação
├── extracao.py            (~600 linhas)  — criar_gigs/comentario/lembrete, indexar, abas
├── atos_utils.py          (~350 linhas)  — def_chip, pec wrappers
├── triagem_regras.py      (~750 linhas)  — coleta (API/PDF/OCR), regras/alertas
├── triagem_engine.py      (~800 linhas)  — busca lista, enriquece, run_triagem + buckets
├── dom_engine.py          (~700 linhas)  — run_dom, bucket1/bucket2, callbacks
├── main.py                (~180 linhas)  — menus + entry point
├── requirements.txt       (~20 linhas)   — todas as dependências Python
├── instalar.bat           (~40 linhas)   — setup completo (venv, pip, Firefox Dev check)
├── PLANO.md               — este arquivo
├── ARQUITETURA.md         — decisões de arquitetura detalhadas
└── drivers/
    └── geckodriver.exe    — copiado de Fix/geckodriver.exe
```

**Restrição:** Nenhum arquivo deve ultrapassar 800 linhas. Se `triagem_engine.py` crescer, split em `triagem_engine_runtime.py` (busca/enriquece) + `triagem_engine_execute.py` (run_triagem + execute_item).

---

## Decisões de Arquitetura

1. **Sem import de módulos externos do projeto** — `bianca/` não faz `from Fix.core import ...` nem `from Triagem.runtime_triagem import ...`. Todo código necessário é copiado/adaptado nos arquivos locais.

2. **Login 100% manual** — `driver.py` exibe `input("CPF: ")` e `input("Senha: ")` no terminal. Sem leitura de `.env`, sem variáveis de ambiente, sem credenciais hardcoded. A função `login_cpf` do Fix é reescrita como stub simples que preenche os campos CPF e senha interativamente.

3. **geckodriver local** — `config.py` define `GECKODRIVER_PATH = Path(__file__).parent / "drivers" / "geckodriver.exe"`. O arquivo deve ser copiado de `Fix/geckodriver.exe`.

4. **Firefox Developer Edition** — `instalar.bat` verifica a presença do executável padrão (`C:\Program Files\Firefox Developer Edition\firefox.exe`) e instrui o usuário se não encontrar.

5. **Sem controle de progresso** — `run_triagem` e `run_dom` em `bianca/` **não** registram progresso em `progresso.json`. O `ProgressoUnificado` é omitido. `should_skip` retorna sempre `False`.

6. **Mínimo de arquivos** — dependências de módulos diferentes são agrupadas por camada (selenum utils, extração, atos), não por módulo de origem.

7. **RuleRegistry embutido** — `utils.py` inclui a classe `RuleRegistry` diretamente (copiada de `core/rule_registry.py`) para evitar dependência do pacote `core/`.

---

## Lista de Tarefas

### Fase 0: Base e Configuração

---

#### Tarefa 1: `config.py` — Constantes e Caminhos

**Descrição:** Centraliza todas as constantes do projeto: caminho do geckodriver, profile Firefox, URLs PJe, salário mínimo e intervalos de CEP (Zona Sul, Zona Leste, Rui Barbosa).

**Fontes:**
- `Triagem/runtime_triagem.py` linhas 34–77 (constantes e CEPs)
- `api/variaveis.py` (GECKODRIVER_PATH pattern)

**Acceptance criteria:**
- [ ] `GECKODRIVER_PATH` aponta para `bianca/drivers/geckodriver.exe`
- [ ] `FIREFOX_BINARY` aponta para Firefox Developer Edition
- [ ] `SALARIO_MINIMO`, `ALCADA`, `RITO_SUMARISSIMO_MAX` definidos
- [ ] Os três conjuntos de intervalos de CEP definidos como listas de tuplas
- [ ] `URL_PJE_BASE`, `URL_LISTA_TRIAGEM`, `URL_LISTA_DOM` definidas

**Verificação:**
- [ ] `py -c "from bianca.config import GECKODRIVER_PATH, SALARIO_MINIMO; print(GECKODRIVER_PATH)"`

**Dependências:** Nenhuma  
**Estimativa:** XS (1 arquivo, ~80 linhas)

---

#### Tarefa 2: `drivers/geckodriver.exe` — Copiar executável

**Descrição:** Copiar `Fix/geckodriver.exe` para `bianca/drivers/geckodriver.exe`.

**Acceptance criteria:**
- [ ] Arquivo existe em `bianca/drivers/geckodriver.exe`
- [ ] `instalar.bat` inclui passo de cópia automática

**Verificação:**
- [ ] `Test-Path bianca\drivers\geckodriver.exe` retorna True

**Dependências:** Tarefa 1  
**Estimativa:** XS

---

### Fase 1: Infraestrutura

---

#### Tarefa 3: `utils.py` — Tipos, Resultados, Batch, RuleRegistry

**Descrição:** Agrupa utilitários base que são usados por todos os outros módulos bianca: tipo `ResultadoFluxo`, funções `resultado_ok`/`resultado_falha`, engine `run_batch`, classe `RuleRegistry`.

**Fontes:**
- `Fix/tipos.py` — `ResultadoFluxo`
- `utilitarios_processamento.py` — `resultado_ok`, `resultado_falha`, `run_batch`
- `core/rule_registry.py` — `RuleRegistry`
- `Fix/log.py` — `logger`, `log_start`, `log_fim`, `log_item` (pode ser apenas `logging.getLogger`)

**Acceptance criteria:**
- [ ] `resultado_ok()` retorna `{'ok': True}`; `resultado_falha("msg")` retorna `{'ok': False, 'erro': 'msg'}`
- [ ] `run_batch(items, should_skip, open_item, execute_item, persist_result)` funciona com lista vazia
- [ ] `RuleRegistry` permite `add_rule(pattern, bucket, descricao)` e `all_rules()` retorna lista
- [ ] Nenhum import de módulos do projeto principal

**Verificação:**
- [ ] `py -c "from bianca.utils import resultado_ok, run_batch, RuleRegistry; print('ok')"`

**Dependências:** Nenhuma  
**Estimativa:** S (1 arquivo, ~280 linhas)

---

#### Tarefa 4: `selenium_utils.py` — Funções Selenium

**Descrição:** Copia subconjunto relevante de `Fix/core.py` + `Fix/browser_suporte.py`: as funções Selenium usadas por `triagem_engine.py` e `dom_engine.py`.

**Fontes:**
- `Fix/core.py` — `esperar_elemento`, `safe_click`, `preencher_campo`, `selecionar_opcao`, `com_retry`, `buscar_seletor_robusto`, `aguardar_renderizacao_nativa`, `aplicar_filtro_100`, `filtrofases`
- `Fix/browser_suporte.py` — `aguardar_e_clicar`, `safe_click_no_scroll`
- `Fix/abas.py` — `fechar_abas_extras`, `trocar_para_nova_aba`
- `Fix/headless_helpers.py` — `limpar_overlays_headless`

**Acceptance criteria:**
- [ ] Todas as funções listadas acessíveis como `from bianca.selenium_utils import aguardar_e_clicar`
- [ ] Nenhum import circular
- [ ] `aguardar_e_clicar(driver, seletor, timeout=10)` assinatura compatível com uso em `dom.py`

**Verificação:**
- [ ] `py -m py_compile bianca/selenium_utils.py`

**Dependências:** Nenhuma  
**Estimativa:** M (1 arquivo, ~450 linhas)

---

#### Tarefa 5: `api_client.py` — Cliente API PJe

**Descrição:** Copia `PjeApiClient`, `session_from_driver` e helpers de paginação de `api/variaveis_client.py` e `api/variaveis_helpers.py`.

**Fontes:**
- `api/variaveis_client.py` — `PjeApiClient`, `session_from_driver`
- `api/variaveis_helpers.py` — `obter_texto_documento`, `buscar_atividade_gigs_por_observacao`
- Stub mínimo de `buscar_todas_paginas`

**Acceptance criteria:**
- [ ] `PjeApiClient(session, trt_host)` instanciável sem erro
- [ ] `session_from_driver(driver)` retorna `(session, trt_host)`
- [ ] `gateway_patch(path, json_data, timeout)` presente
- [ ] Nenhum import de `api.*` do projeto principal

**Verificação:**
- [ ] `py -m py_compile bianca/api_client.py`

**Dependências:** Tarefa 3  
**Estimativa:** M (1 arquivo, ~420 linhas)

---

### Fase 2: Extração e Atos

---

#### Tarefa 6: `extracao.py` — Funções de Extração de Dados

**Descrição:** Subconjunto de `Fix/extracao.py` usado pelos engines: `criar_gigs`, `criar_comentario`, `criar_lembrete_posit`, `abrir_detalhes_processo`, `indexar_processos`, `reindexar_linha`.

**Fontes:**
- `Fix/extracao.py` — funções listadas acima

**Acceptance criteria:**
- [ ] `criar_gigs(driver, observacao)` assinatura compatível
- [ ] `criar_comentario(driver, texto)` assinatura compatível
- [ ] `criar_lembrete_posit(driver, titulo, conteudo, debug)` assinatura compatível
- [ ] `indexar_processos(driver)` retorna lista de `(proc_id, linha_element)`
- [ ] `abrir_detalhes_processo(driver, linha)` retorna bool

**Verificação:**
- [ ] `py -m py_compile bianca/extracao.py`

**Dependências:** Tarefas 3, 4  
**Estimativa:** M (1 arquivo, ~600 linhas)

---

#### Tarefa 7: `atos_utils.py` — def_chip + PEC Wrappers

**Descrição:** Copia `def_chip` de `atos/movimentos_chips.py` e os quatro wrappers PEC (`pec_sumc`, `pec_sumc2`, `pec_ordc`, `pec_ordc2`) de `atos/wrappers_pec.py`.

**Fontes:**
- `atos/movimentos_chips.py` — `def_chip`
- `atos/wrappers_pec.py` — `pec_sumc`, `pec_sumc2`, `pec_ordc`, `pec_ordc2`

**Acceptance criteria:**
- [ ] `def_chip(driver, numero_processo, chips_para_remover, ...)` presente
- [ ] Quatro funções PEC presentes com assinaturas compatíveis
- [ ] Nenhum import de `atos.*` do projeto principal

**Verificação:**
- [ ] `py -m py_compile bianca/atos_utils.py`

**Dependências:** Tarefas 3, 4, 6  
**Estimativa:** S (1 arquivo, ~350 linhas)

---

### Fase 3: Engine de Triagem

---

#### Tarefa 8: `triagem_regras.py` — Coleta e Regras de Alertas

**Descrição:** Consolida a camada de coleta (API + PDF + OCR) e o registry de regras de alertas. Resulta nas funções: `coletar_dados_processo`, `_parsear_capa`, `_eh_peticao_inicial`, `_checar_procuracao_e_identidade`, `alerta_registry`, `determinar_acao_pos_triagem`.

**Fontes:**
- `Triagem/coleta.py` — coleta via API e parsing
- `Triagem/regras.py` — `alerta_registry`, `determinar_acao_pos_triagem`, `_checar_procuracao_e_identidade`

**Acceptance criteria:**
- [ ] `alerta_registry` é uma instância de `RuleRegistry` com regras carregadas
- [ ] `determinar_acao_pos_triagem(texto)` retorna `(bucket, descricao)`
- [ ] `coletar_dados_processo(client, id_processo)` retorna dict com textos
- [ ] Nenhum import de `Triagem.*` do projeto principal

**Verificação:**
- [ ] `py -m py_compile bianca/triagem_regras.py`

**Dependências:** Tarefas 3, 5  
**Estimativa:** L (1 arquivo, ~750 linhas — no limite; avaliar split)

---

#### Tarefa 9: `triagem_engine.py` — Runtime Triagem + Análise

**Descrição:** Consolida `runtime_triagem.py` e `analise_execucao.py`. Expõe `run_triagem(driver)` e funções de análise de petição (`triagem_peticao`), buckets (`acao_bucket_a/b/c/d`) e pós-triagem (`_aplicar_acao_pos_triagem`).

**Fontes:**
- `Triagem/runtime_triagem.py` — `buscar_lista_triagem`, `enriquecer_processo`, `run_triagem`, CEPs/constantes
- `Triagem/analise_execucao.py` — `triagem_peticao`, `acao_bucket_a/b/c/d`, `_strip_cabecalho_rodape`, formatação

**Acceptance criteria:**
- [ ] `run_triagem(driver)` retorna `{"sucesso": bool, "processados": int, "sucesso_count": int, "total": int}`
- [ ] `buscar_lista_triagem(driver)` retorna lista de dicts
- [ ] `enriquecer_processo(item)` retorna dict com chave `bucket` ∈ {A, B, C, D}
- [ ] `triagem_peticao(driver)` retorna string de análise ou string de erro
- [ ] Sem progresso unificado (should_skip sempre retorna False)
- [ ] Nenhum import de `Triagem.*` ou `Fix.*` do projeto principal

**Verificação:**
- [ ] `py -m py_compile bianca/triagem_engine.py`

**Dependências:** Tarefas 3, 4, 5, 6, 8  
**Estimativa:** L (1 arquivo, ~800 linhas — se ultrapassar, split em `triagem_runtime.py` + `triagem_analise.py`)

---

### Fase 4: Engine DOM

---

#### Tarefa 10: `dom_engine.py` — Fluxo Dom Eletrônico

**Descrição:** Copia e adapta `Triagem/dom.py`. Remove import circular de `x.py` (substituindo por import local de `driver.py`). Expõe `run_dom(driver)`.

**Fontes:**
- `Triagem/dom.py` — `run_dom`, `navigate_to_activities_and_filter`, `execute_list_with_bucket2_callback`, `callback_bucket2`, `callback_bucket1`, `checar_empresas`, `has_dom_eletronico_reminder`, etc.

**Acceptance criteria:**
- [ ] `run_dom(driver)` retorna `{"sucesso": bool}`
- [ ] Import circular com `x.py` eliminado — usa `bianca.driver` em vez de `from x import ...`
- [ ] `callback_bucket2` usa `from bianca.atos_utils import def_chip, pec_sumc, ...`
- [ ] Nenhum `input()` de debug permanece (remover `input("DEBUG: Pressione Enter...")`)

**Verificação:**
- [ ] `py -m py_compile bianca/dom_engine.py`

**Dependências:** Tarefas 3, 4, 6, 7  
**Estimativa:** M (1 arquivo, ~700 linhas)

---

### Fase 5: Driver e Login Manual

---

#### Tarefa 11: `driver.py` — Firefox + Login Manual

**Descrição:** Cria o driver Firefox e implementa login **estritamente manual**. O usuário digita CPF e senha no terminal. Nenhuma automação de login, nenhuma variável de ambiente, nenhum arquivo de config com credenciais.

**Fontes:**
- `Fix/core.py` — `criar_driver_pc` (padrão Firefox Dev Edition + geckodriver local)
- `Fix/utils.py` — `login_cpf` (reescrita como stub interativo)

**Acceptance criteria:**
- [ ] `criar_driver() -> WebDriver` — cria Firefox Dev Edition visível usando `bianca/config.py::GECKODRIVER_PATH`
- [ ] `fazer_login_manual(driver)` — exibe prompts no terminal para CPF e senha, preenche campos PJe
- [ ] `criar_driver_e_fazer_login() -> Optional[WebDriver]` — combina os dois passos
- [ ] Nenhuma credencial hardcoded; nenhum `.env` ou variável de ambiente lida
- [ ] Instrução clara no terminal: `"Aguardando login manual no navegador (pressione Enter quando logado)"` é uma opção alternativa aceitável se o preenchimento automático de campos for frágil

**Verificação:**
- [ ] `py -m py_compile bianca/driver.py`
- [ ] Manual: executar `py bianca/driver.py` e verificar que Firefox abre e pede credenciais

**Dependências:** Tarefa 1  
**Estimativa:** S (1 arquivo, ~120 linhas)

---

### Fase 6: Entry Point + Setup

---

#### Tarefa 12: `main.py` — Menus + Orquestrador

**Descrição:** Entry point que replica o menu de fluxo de `x.py` para apenas os dois módulos: Triagem e DOM. Inclui `TeeOutput` para log em arquivo.

**Fontes:**
- `x.py` — `TeeOutput`, `menu_execucao` (simplificado), `executar_triagem`, `executar_dom`, `main()`

**Acceptance criteria:**
- [ ] Menu oferece: `T - Triagem Isolada`, `D - DOM Eletrônico`, `X - Sair`
- [ ] Cria driver + login manual antes de executar fluxo escolhido
- [ ] Log é capturado em arquivo `logs/bianca_TIMESTAMP.log`
- [ ] `py bianca/main.py` executa sem erro de import

**Verificação:**
- [ ] `py -m py_compile bianca/main.py`
- [ ] `py bianca/main.py` — abre menu no terminal

**Dependências:** Tarefas 9, 10, 11  
**Estimativa:** S (1 arquivo, ~180 linhas)

---

#### Tarefa 13: `requirements.txt` + `instalar.bat`

**Descrição:** Arquivo de dependências Python completo e script `.bat` que faz tudo automaticamente: cria venv, instala dependências, copia geckodriver, verifica Firefox Developer Edition.

**`requirements.txt` deve incluir:**
```
selenium>=4.x
requests>=2.x
Pillow>=10.x          # para OCR/PDF
pdf2image>=1.x        # extração de imagens de PDF
pytesseract>=0.3.x    # OCR (opcional mas declarado)
```

**`instalar.bat` deve:**
1. Verificar Python 3.10+
2. Criar `venv` em `bianca\venv`
3. Instalar `requirements.txt`
4. Copiar `Fix\geckodriver.exe` → `bianca\drivers\geckodriver.exe`
5. Verificar presença de Firefox Developer Edition e exibir aviso se ausente
6. Criar pasta `bianca\logs`
7. Exibir mensagem de sucesso

**Acceptance criteria:**
- [ ] `instalar.bat` executa do zero sem erro em máquina Windows com Python 3.10+
- [ ] `requirements.txt` cobre todas as dependências de terceiros usadas no código

**Verificação:**
- [ ] `instalar.bat` roda sem erros críticos
- [ ] `bianca\venv\Scripts\python.exe -c "import selenium, requests; print('ok')"`

**Dependências:** Nenhuma (pode ser feito em paralelo)  
**Estimativa:** S

---

#### Tarefa 14: Documentação MD detalhada

**Descrição:** Criar dois arquivos MD complementares ao `PLANO.md`:

- `bianca/ARQUITETURA.md` — diagrama de camadas, decisões de design, fluxo de execução de `run_triagem` e `run_dom`, descrição de cada arquivo
- `bianca/README.md` — guia de instalação passo-a-passo, uso (`py bianca/main.py`), requisitos de sistema (Windows 10+, Python 3.10+, Firefox Developer Edition), nota sobre login manual

**Acceptance criteria:**
- [ ] `README.md` contém: pré-requisitos, instalação (2 passos), execução, descrição dos fluxos
- [ ] `ARQUITETURA.md` contém: diagrama de grafo de dependências, tabela de arquivos com descrição, detalhes do fluxo triagem e dom

**Dependências:** Tarefas 1–12 (pode ser escrito após)  
**Estimativa:** S

---

## Checkpoints

### Checkpoint A — Infraestrutura OK (após Tarefas 1–7)
- [ ] `py -c "from bianca.config import *; from bianca.utils import *; from bianca.selenium_utils import *; from bianca.api_client import *; from bianca.extracao import *; from bianca.atos_utils import *; print('OK')"`
- [ ] Nenhum import de `Fix.*`, `atos.*`, `api.*` do projeto principal

### Checkpoint B — Engines OK (após Tarefas 8–10)
- [ ] `py -m py_compile bianca/triagem_engine.py bianca/dom_engine.py`
- [ ] `py -c "from bianca.triagem_engine import run_triagem; from bianca.dom_engine import run_dom; print('OK')"`

### Checkpoint C — Sistema completo (após Tarefas 11–14)
- [ ] `instalar.bat` roda do zero
- [ ] `py bianca/main.py` abre menu, cria driver Firefox, permite login manual
- [ ] Fluxo Triagem executa sem erro de import (teste com processo real)
- [ ] Fluxo DOM executa sem erro de import

---

## Tabela de Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| `Fix/extracao.py` tem 2127 linhas — identificar funções exatas a copiar pode ser difícil | Alto | Grep por nome da função + leitura de 50 linhas acima/abaixo |
| `atos/movimentos_chips.py` e `atos/wrappers_pec.py` dependem de `atos/judicial.py` | Médio | Verificar imports no início de cada arquivo antes de copiar |
| `api/variaveis_client.py` pode depender de `Fix.*` internamente | Médio | Verificar e substituir imports por equivalentes locais |
| `triagem_engine.py` pode ultrapassar 800 linhas | Baixo | Split em `triagem_runtime.py` + `triagem_analise.py` |
| OCR via `pytesseract` requer Tesseract instalado no sistema | Médio | Tratar como opcional; exibir aviso se não disponível |
| Firefox Developer Edition pode estar em caminho diferente por máquina | Baixo | `instalar.bat` verifica e exibe instruções de instalação |

---

## Questões Abertas

- `Fix/utils.py::login_cpf` preenche campos automaticamente? Se sim, reutilizar lógica no `driver.py` de bianca, mas com CPF/senha lidos do terminal (não de variáveis). Verificar linhas 376–450 de `Fix/utils.py`.
- `atos/wrappers_pec.py` usa `atos/judicial.py` internamente? Se sim, quantas funções de `judicial.py` são necessárias? Avaliar se vale copiar todo o `judicial.py` ou só as funções usadas pelos wrappers PEC.
- `Fix/monitoramento_progresso_unificado.py` é necessário? Sim — `dom_engine.py` usa `executar_com_monitoramento_unificado`. Mas o requisito diz "não é necessário migrar controle de progresso". Solução: substituir a chamada por execução direta sem monitoramento, ou criar stub que sempre retorna `(True, proc_id)`.

---

## Ordem de Implementação Recomendada

```
Tarefa 1 (config) ──→ Tarefa 2 (geckodriver)
                  ──→ Tarefa 3 (utils)
                        ├──→ Tarefa 4 (selenium_utils)
                        ├──→ Tarefa 5 (api_client)
                        └──→ [Checkpoint A: config+utils+selenium+api ok]
                                ├──→ Tarefa 6 (extracao)
                                │      └──→ Tarefa 7 (atos_utils)
                                │              └──→ Tarefa 10 (dom_engine)
                                └──→ Tarefa 8 (triagem_regras)
                                       └──→ Tarefa 9 (triagem_engine)
                                              └──→ [Checkpoint B]
Tarefa 11 (driver) ──────────────────────────────→ Tarefa 12 (main)
Tarefa 13 (instalar.bat) ────────────────────────→ [Checkpoint C]
Tarefa 14 (docs) ────────────────────────────────→ FIM
```

Tarefas 1, 2, 3, 4, 5, 13 podem ser desenvolvidas **em paralelo** (sem dependência entre si).

---

## Sumário de Escopo

| Fase | Tarefas | Arquivos | Linhas estimadas |
|------|---------|----------|-----------------|
| 0 — Base       | 1, 2         | 1 + 1 binário | ~80      |
| 1 — Infra      | 3, 4, 5      | 3             | ~1150    |
| 2 — Extração   | 6, 7         | 2             | ~950     |
| 3 — Triagem    | 8, 9         | 2             | ~1550    |
| 4 — DOM        | 10           | 1             | ~700     |
| 5 — Driver     | 11           | 1             | ~120     |
| 6 — Setup/Docs | 12, 13, 14   | 4             | ~400     |
| **Total**      | **14**       | **15 arquivos** | **~4950** |

---

*Plano criado em 2026-05-04. Pronto para revisão antes de iniciar implementação.*
