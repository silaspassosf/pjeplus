# Plano de Implementação: Pasta `Andrei/` — Módulo Petição Standalone

## Visão Geral

Criar a pasta `Andrei/` como um módulo Python completamente autossuficiente para
executar o fluxo G (Petição) do `x.py`, sem depender de nenhum outro módulo do
projeto (`Fix/`, `atos/`, `Prazo/`, `core/`, etc.). Login é **exclusivamente manual**
(o código navega até a URL e aguarda o usuário logar no browser).

---

## Mapa de Dependências do Módulo Petição

```
Peticao/runtime_pet.py (entry point run_pet)
  ├── Peticao/regras_execucao.py
  │     ├── core/rule_registry.py          (RuleRegistry — inlinar)
  │     ├── Prazo/p2b_regras_execucao.py   (normalizar_texto — inlinar)
  │     ├── atos/judicial_fluxo.py         (make_ato_wrapper — inlinar)
  │     └── Peticao/helpers/helpers.py     (checar_habilitacao, etc)
  ├── Peticao/core/extracao/extracao.py    (criar_gigs, extrair_direto, extrair_documento)
  ├── Peticao/core/utils/observer.py       (aguardar_renderizacao_nativa)
  ├── Peticao/api/client.py                (PjeApiClient + session_from_driver)
  ├── Fix/extracao.py                      (extrair_dados_processo)
  ├── Fix/selenium_base/wait_operations.py (esperar_elemento)
  ├── Fix/core.py                          (aguardar_renderizacao_nativa, fechar_abas_extras)
  ├── Fix/log.py                           (getmodulelogger)
  ├── Fix/variaveis.py                     (obter_chave_ultimo_despacho_decisao_sentenca)
  ├── Fix/utils.py                         (driver_pc, configurar_recovery_driver, handle_exception_with_recovery)
  ├── utilitarios_processamento.py         (resultado_ok, resultado_falha)
  └── [progresso unificado — ignorar, req. 3]
```

---

## Estrutura de Arquivos Proposta

```
Andrei/
├── __init__.py                 (vazio)
├── config.py                   (~60 linhas)   — caminhos geckodriver, Firefox, URLs base
├── driver.py                   (~120 linhas)  — criar driver PC + login MANUAL
├── utils_selenium.py           (~600 linhas)  — selenium utils de Fix/core, Fix/selenium_base, Fix/abas
├── extracao.py                 (~700 linhas)  — Fix/extracao + Peticao/core/extracao (PDF/HTML)
├── atos_judicial.py            (~800 linhas)  — make_ato_wrapper + atos de atos/judicial_fluxo + wrappers de regras_execucao
├── regras.py                   (~500 linhas)  — RuleRegistry (inlinada) + classificar + resolver_acao + _Dados
├── api_client.py               (~250 linhas)  — PjeApiClient + session_from_driver (Peticao/api/client.py)
├── helpers.py                  (~400 linhas)  — Peticao/helpers + Fix/variaveis helpers + normalizar_texto
├── pipeline.py                 (~700 linhas)  — PeticaoAPIClient, PETOrquestrador, run_pet, analise_pet
└── main.py                     (~60 linhas)   — entry point (py -m Andrei.main ou py Andrei/main.py)
```

**Total estimado:** ~4190 linhas em 10 arquivos. Maior arquivo (`atos_judicial.py`) = 800 linhas (no limite).

---

## Arquitetura Decisions

- **Login manual exclusivo:** `driver.py` cria o browser, navega para `https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas` e bloqueia até detectar que o usuário já está logado (checa URL / elemento da página). Nenhuma senha ou CPF automatizado.
- **Perfil Firefox temporário:** Criar um `tempfile.mkdtemp()` a cada execução. Nenhum perfil fixo ou persistente.
- **Zero import de outros módulos do projeto:** Todas as funções são copiadas/inlinadas dentro de `Andrei/`. Imports são apenas de `selenium`, `requests`, `pdfplumber`, stdlib.
- **Sem controle de progresso:** Nenhum arquivo de progresso. Nenhuma lógica de skip. Todos os itens do escaninho são processados a cada execução.
- **`dadosatuais.json` dentro de `Andrei/`:** Caminho hardcoded como `Andrei/dadosatuais.json` em todas as chamadas de `extrair_dados_processo`.
- **geckodriver copiado:** `Andrei/drivers/geckodriver.exe` copiado de `Fix/geckodriver.exe`.
- **`config.py` é a única fonte de caminhos:** geckodriver, diretório de logs, URL base.

---

## Task List

### Fase 1: Infraestrutura Base

#### Task 1: `config.py` — Configurações e Caminhos
**Descrição:** Criar arquivo com todas as constantes do módulo: caminho do geckodriver, URL base do PJe, diretório de logs. Perfil Firefox é sempre temporário (criado em runtime).

**Acceptance criteria:**
- [ ] `GECKODRIVER_PATH` aponta para `Andrei/drivers/geckodriver.exe`
- [ ] `PJE_BASE_URL = "https://pje.trt2.jus.br"`
- [ ] `ESCANINHO_URL = "https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas"`
- [ ] `DADOSATUAIS_JSON = "Andrei/dadosatuais.json"`
- [ ] `LOG_DIR = "Andrei/logs"`
- [ ] Sem `FIREFOX_PROFILE_PATH` fixo — perfil sempre temporário via `tempfile.mkdtemp()`

**Verification:**
- [ ] `py -c "from Andrei.config import GECKODRIVER_PATH, ESCANINHO_URL; print(ESCANINHO_URL)"`

**Dependencies:** None

**Files:**
- `Andrei/config.py`
- `Andrei/drivers/geckodriver.exe` (cópia de `Fix/geckodriver.exe`)

**Scope:** XS

---

#### Task 2: `driver.py` — Driver + Login Manual
**Descrição:** Criar driver Firefox (PC visível) usando geckodriver de `config.py`. Perfil Firefox é um diretório temporário criado com `tempfile.mkdtemp()` a cada execução e apagado ao fechar o driver. Login é **manual**: o código navega para o PJe e aguarda o usuário completar o login interativamente (loop que verifica URL / presença de elemento).

**Acceptance criteria:**
- [ ] `criar_driver(headless=False)` retorna WebDriver com perfil temporário e geckodriver de `config.py`
- [ ] Perfil criado em `tempfile.mkdtemp()` no início e removido em `fechar_driver(driver)`
- [ ] `aguardar_login_manual(driver, timeout=300)` espera até 5 min pelo usuário e retorna `True` se logado ou `False` se timeout
- [ ] Nenhuma referência a CPF, senha, ou qualquer credencial
- [ ] `criar_driver_e_logar()` combina criação + navegação + espera manual

**Verification:**
- [ ] `py -c "from Andrei.driver import criar_driver; print('OK')"`

**Dependencies:** Task 1

**Files:**
- `Andrei/driver.py`

**Scope:** S

---

### Checkpoint Fase 1
- [ ] `py -c "from Andrei.config import *; from Andrei.driver import criar_driver_e_logar"` sem erro de import

---

### Fase 2: Utils e Extração

#### Task 3: `utils_selenium.py` — Utilitários Selenium
**Descrição:** Copiar e consolidar funções Selenium usadas pelo módulo Petição. Fontes: `Fix/core.py`, `Fix/selenium_base/wait_operations.py`, `Fix/abas.py`, `Fix/core.py (aguardar_renderizacao_nativa)`.

**Funções a incluir:**
- `esperar_elemento(driver, seletor, texto=None, timeout=10, by=...) → WebElement | None`
- `aguardar_renderizacao_nativa(driver, seletor, modo='aparecer', timeout=10) → bool`
- `fechar_abas_extras(driver)`
- `safe_click(driver, elemento) → bool`
- `aguardar_e_clicar(driver, seletor, timeout=10, by=...) → bool`
- `wait_for_clickable(driver, seletor, timeout=10) → WebElement | None`
- `preencher_multiplos_campos(driver, mapa_campos) → bool`
- `esperar_url_conter(driver, fragmento, timeout=15) → bool`

**Acceptance criteria:**
- [ ] Todas as funções acima definidas sem importar de `Fix/`
- [ ] Arquivo ≤ 600 linhas

**Verification:**
- [ ] `py -c "from Andrei.utils_selenium import esperar_elemento, fechar_abas_extras"`

**Dependencies:** None (apenas stdlib + selenium)

**Files:**
- `Andrei/utils_selenium.py`

**Scope:** M

---

#### Task 4: `extracao.py` — Extração de Dados
**Descrição:** Consolidar funções de extração. Fontes: `Fix/extracao.py (extrair_dados_processo, bndt, criar_gigs)`, `Peticao/core/extracao/extracao.py (extrair_direto, extrair_documento, criar_gigs)`.

**Funções a incluir:**
- `extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)`
- `extrair_direto(driver, timeout=10, debug=False, formatar=True) → dict`
- `extrair_documento(driver, regras_analise=None, timeout=10, log=False) → tuple`
- `criar_gigs(driver, tipo, descricao, observacao='') → bool`
- `bndt(driver) → str | None`

**Acceptance criteria:**
- [ ] Sem imports de `Fix.extracao` ou `Peticao.core.extracao`
- [ ] Arquivo ≤ 700 linhas

**Verification:**
- [ ] `py -c "from Andrei.extracao import extrair_direto, criar_gigs"`

**Dependencies:** Task 3

**Files:**
- `Andrei/extracao.py`

**Scope:** M

---

### Checkpoint Fase 2
- [ ] `py -c "from Andrei.utils_selenium import *; from Andrei.extracao import *"` sem erro

---

### Fase 3: Atos e Regras

#### Task 5: `atos_judicial.py` — Wrappers de Atos Judiciais
**Descrição:** Copiar `make_ato_wrapper` e funções do fluxo judicial de `atos/judicial_fluxo.py`. Incluir todos os `ato_*` wrappers definidos em `Peticao/regras_execucao.py` (ato_instc, ato_inste, ato_gen, ato_laudo, ato_esc, ato_escliq, ato_datalocal, ato_ceju, ato_respcalc, ato_adesivo, ato_agpetidpj, ato_agpet, ato_agpinter, ato_assistente, ato_homacordo, ato_uber, ato_ccs, ato_censec, ato_serp, ato_conv, etc.).

**Acceptance criteria:**
- [ ] `make_ato_wrapper(**kwargs) → Callable[[driver], bool]` funcional
- [ ] Todos os `ato_*` wrappers instanciados no módulo
- [ ] Arquivo ≤ 800 linhas (se exceder, dividir em `atos_judicial.py` + `atos_wrappers.py`)
- [ ] Sem imports de `atos/` ou `Fix/` — usa `Andrei.utils_selenium`

**Verification:**
- [ ] `py -c "from Andrei.atos_judicial import make_ato_wrapper, ato_instc, ato_gen"`

**Dependencies:** Tasks 3, 4

**Files:**
- `Andrei/atos_judicial.py`
- `Andrei/atos_wrappers.py` (overflow se > 800 linhas)

**Scope:** L

---

#### Task 6: `regras.py` — Registry e Classificação
**Descrição:** Copiar **integralmente** `Peticao/regras_execucao.py` — todas as regras registradas, todos os `ato_*` instanciados ali, `_Dados`, `_dados`, `_detectar_acao_analise`, `_executar_acao`, `classificar`, `resolver_acao`, `peticao_registry`. Inlinar `RuleRegistry` + `adapt_action` de `core/rule_registry.py` e `normalizar_texto` de `Prazo/p2b_regras_execucao.py`. Nenhuma regra é omitida ou considerada não essencial.

**Acceptance criteria:**
- [ ] `RuleRegistry` e `adapt_action` definidas localmente
- [ ] `classificar(item) → str` retorna nome do bucket
- [ ] `resolver_acao(item, driver) → str | None`
- [ ] `normalizar_texto(texto) → str`
- [ ] Todas as regras de `Peticao/regras_execucao.py` presentes sem omissões
- [ ] Sem imports de `core/`, `Prazo/`, `Peticao/regras_execucao`

**Verification:**
- [ ] `py -c "from Andrei.regras import classificar, RuleRegistry, normalizar_texto"`

**Dependencies:** Tasks 4, 5

**Files:**
- `Andrei/regras.py`

**Scope:** M

---

### Checkpoint Fase 3
- [ ] `py -c "from Andrei.atos_judicial import ato_instc; from Andrei.regras import classificar"` sem erro

---

### Fase 4: API e Helpers

#### Task 7: `api_client.py` — Cliente API PJe
**Descrição:** Copiar `PjeApiClient` e `session_from_driver` de `Peticao/api/client.py`.

**Funções a incluir:**
- `session_from_driver(driver) → Tuple[requests.Session, str]`
- `PjeApiClient(session, trt_host)` com métodos: `timeline`, `documento_por_id`, `execucao_gigs`, `processo_por_id`

**Acceptance criteria:**
- [ ] Sem imports de `Peticao.api.client` ou `api.variaveis_client`
- [ ] `py -c "from Andrei.api_client import PjeApiClient, session_from_driver"`

**Dependencies:** None (apenas `requests`)

**Files:**
- `Andrei/api_client.py`

**Scope:** S

---

#### Task 8: `helpers.py` — Helpers Específicos
**Descrição:** Copiar helpers de `Peticao/helpers/helpers.py` (checar_habilitacao, agravo_peticao, def_quesitos, contesta_calc, apagar, _buscar_documento_relevante_timeline) e `Fix/variaveis.py (obter_chave_ultimo_despacho_decisao_sentenca)`.

**Acceptance criteria:**
- [ ] Todas as funções acima disponíveis sem imports de `Fix.variaveis` ou `Peticao.helpers`
- [ ] `apagar(numero_processo, id_documento)` escreve em `Andrei/delete.js`
- [ ] Arquivo ≤ 400 linhas

**Verification:**
- [ ] `py -c "from Andrei.helpers import checar_habilitacao, apagar"`

**Dependencies:** Tasks 3, 4, 7

**Files:**
- `Andrei/helpers.py`

**Scope:** S

---

### Checkpoint Fase 4
- [ ] `py -c "from Andrei import config, driver, utils_selenium, extracao, atos_judicial, regras, api_client, helpers"` sem erro

---

### Fase 5: Pipeline e Entry Point

#### Task 9: `pipeline.py` — Orquestrador Principal
**Descrição:** Copiar e adaptar `runtime_pet.py` integralmente — `PeticaoAPIClient`, `PeticaoItem`, `_normalizar`, `PETOrquestrador`, `executar_fluxo_pet`, `analise_pet`, buckets, e `run_pet`. Substituir:
- `Fix.monitoramento_progresso_unificado` → remover completamente. Sem progresso, sem skip de processos.
- `carregar_progresso_pet / salvar_progresso_pet / marcar_processo_executado_pet / processo_ja_executado_pet` → remover. `_executar_bucket_normal` e `_executar_bucket_analise` executam todos os itens sem verificação.
- `Fix.utils.configurar_recovery_driver` + `handle_exception_with_recovery` → copiar as funções de `Fix/utils.py` para `helpers.py`
- `resultado_ok / resultado_falha` de `utilitarios_processamento` → dicts inline
- `extrair_dados_processo(driver, caminho_json='dadosatuais.json')` → `extrair_dados_processo(driver, caminho_json='Andrei/dadosatuais.json')`
- Todos os demais imports do projeto → imports de `Andrei.*`

**Acceptance criteria:**
- [ ] `run_pet(driver=None)` funciona com driver já logado manualmente
- [ ] `executar_fluxo_pet(driver)` orquestra os buckets corretamente
- [ ] Sem imports de `Fix/`, `Peticao/`, `atos/`, `Prazo/`, `core/`, `utilitarios_processamento`
- [ ] Arquivo ≤ 700 linhas

**Verification:**
- [ ] `py -c "from Andrei.pipeline import run_pet, executar_fluxo_pet"`

**Dependencies:** Tasks 3, 4, 5, 6, 7, 8

**Files:**
- `Andrei/pipeline.py`

**Scope:** L

---

#### Task 10: `main.py` — Entry Point
**Descrição:** Script de entrada. Cria driver, aguarda login manual do usuário, executa pipeline, fecha driver.

**Acceptance criteria:**
- [ ] `py Andrei/main.py` ou `py -m Andrei.main` executa o fluxo completo
- [ ] Imprime instruções claras para o usuário fazer o login
- [ ] Aguarda login com timeout de 5 min (configurável)
- [ ] Arquivo ≤ 80 linhas

**Verification:**
- [ ] `py -c "import Andrei.main"` sem ImportError

**Dependencies:** Tasks 1, 2, 9

**Files:**
- `Andrei/main.py`
- `Andrei/__init__.py`

**Scope:** XS

---

### Checkpoint Final
- [ ] `py -c "import Andrei.main"` sem erro de import
- [ ] `py Andrei/main.py` abre Firefox e solicita login manual
- [ ] Após login, executa pipeline de petições

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| `make_ato_wrapper` + `ato_judicial` dependem de muitas funções de `Fix/` | Alto | Copiar também as funções de apoio de `Fix/core` para `utils_selenium.py` |
| `atos_judicial.py` ultrapassa 800 linhas | Médio | Dividir em `atos_judicial.py` (make_ato_wrapper + fluxo_cls) + `atos_wrappers.py` (instâncias ato_*) |
| `Peticao/regras_execucao.py` tem muitas regras registradas | Médio | Mover apenas o essencial; deixar `regras.py` focado em classificar/resolver |
| `helpers.checar_habilitacao` usa API (`session_from_driver`) | Baixo | Task 7 é dependência de Task 8 — ordem garante disponibilidade |
| geckodriver não copiado | Alto | Task 1 inclui explicitamente a cópia do binário |

## Perguntas Abertas

*(Nenhuma — todos os pontos foram esclarecidos pelo usuário.)*
