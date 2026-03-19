# PJePlus – Architecture Knowledge Map (`pjeplus-architecture.md`)

Este arquivo é o "mapa da mina" do projeto PJePlus. O agente deve consultá-lo **após** `idx.md` e **antes** de abrir `LEGADO.md`. Objetivo: dar conhecimento prévio suficiente para agir sem precisar ler código legado bruto.

---

## 1. Fluxo de Leitura Recomendado

```
idx.md  →  pjeplus-architecture.md  →  trechos pontuais de LEGADO.md (se ainda necessário)
```

Nunca abrir `LEGADO.md` inteiro. Usar o índice de funções na Seção 7 para localizar trechos.

---

## 2. Módulos do CORE e Responsabilidades

### `Fix/`
Motor utilitário moderno. Todo código novo de suporte deve viver aqui.

| Arquivo/Submódulo | Responsabilidade |
|---|---|
| `Fix/core.py` | `finalizar_driver`, gerenciamento de ciclo de vida do driver |
| `Fix/utils.py` | `login_cpf` — entrada principal pós-driver |
| `Fix/smart_finder.py` | `SmartFinder`, `injetar_smart_finder_global` — cache de seletores + auto-healing |
| `Fix/selectors_pje.py` | Constantes de seletores nomeados (Angular Material, PJe) + `buscar_seletor_robusto` |
| `Fix/otimizacao_wrapper.py` | `inicializar_otimizacoes`, `finalizar_otimizacoes` — wrapper de performance opcional |

**Funções críticas a conhecer (equivalentes modernos dos legados):**

- `login_cpf(driver)` — faz login completo, equivalente ao `logincpf` do legado (`refpje.py:15326`)
- `finalizar_driver(driver)` — encerra driver com segurança, equivalente a `finalizardriver` do legado (`ref.py:9200`)
- `injetar_smart_finder_global(driver)` — monkey-patch no `driver.find_element` com cache + fallback heurístico
- `SmartFinder.find(driver, key, candidates)` — busca com cache persistente em `aprendizado_seletores.json`
- `aguardar_renderizacao_nativa(driver)` — MutationObserver JS nativo, substitui polling com sleep

---

### `x.py` (Orquestrador)

Substitui `1.py`, `1b.py`, `2.py`, `2b.py`. Ponto de entrada único.

**Estrutura interna:**
- `criar_driver_pc(headless)` / `criar_driver_vt(headless)` — dois perfis de driver
- `criar_e_logar_driver(driver_type)` — cria driver + login + injeta SmartFinder
- `executar_bloco_completo(driver)` — Mandado → Prazo → P2B → PEC em sequência
- `executar_mandado/prazo/pec/p2b(driver)` — execuções isoladas
- `resetar_driver(driver)` — fecha abas extras + navega para URL base do PJe
- `menu_ambiente()` / `menu_execucao()` — menus interativos de seleção

**Enums:**
```
DriverType: PC_VISIBLE | PC_HEADLESS | VT_VISIBLE | VT_HEADLESS
```

---

### `Mandado/`

Automação de mandados (documentos internos).

**Ponto de entrada via `x.py`:**
```python
from Mandado.core import navegacao as mandado_navegacao
from Mandado.core import iniciar_fluxo_robusto as mandado_fluxo
```

**Equivalentes no legado (`LEGADO.md`):**
- `navegacao` → `ref2bfluxohelpers.py:44268` (`navegacao`)
- `iniciar_fluxo_robusto` → `ref2bfluxohelpers.py:44402` (`iniciarfluxorobusto`)
- Fluxo de callback central: `ref.py:45589` (`fluxocallback`)
- Análise de documento/mandado: `ref.py:45680` (`analisepadrao`)
- `ultimomdd` (último mandado): `ref.py:45493`
- Tratamento de anexos ARGOS: `ref.py:45066` (`trataranexosargos`)
- Processamento SISBAJUD em mandado: `ref.py:44973` (`processarsisbajud`)

---

### `PEC/`

Fluxos de execução colaborativa no PJe.

**Ponto de entrada via `x.py`:**
```python
from PEC.processamento import executar_fluxo_novo as pec_fluxo
```

**Equivalentes no legado:**
- `executar_fluxo_novo` → `ref.py:27015` (`executarfluxonovo`) — versão refatorada
- `executar_fluxo_robusto` → `ref.py:26852` (`executarfluxorobusto`) — versão com retry
- `processar_processo_pec_individual` → `ref.py:26781`
- Navegação para atividades PEC: `ref.py:27138` (`navegaratividades`)
- Aplicar filtros: `ref.py:27159` (`aplicarfiltros`)
- Organizar e executar buckets: `ref.py:27213` (`organizareexecutarbuckets`)
- Criar lista SISBAJUD: `ref.py:27312` (`criarlistasisbajud`)
- Executar SISBAJUD por abas: `ref.py:27418` (`executarlistasisbajudporabas`)
- Indexar todos os processos: `ref.py:27740` (`indexartodosprocessos`)
- Agrupar em buckets: `ref.py:27917` (`agruparembuckets`)
- Processar bucket genérico: `ref.py:28013` (`processarbucketgenerico`)

**Seletores relevantes para PEC (em `Fix/selectors_pje.py`):**
```python
BTN_PEC = "#cke_16"
BTN_INCLUIR_PEC = 'a[title="Incluir processo eletrônico colaborativo"]'
BTN_OK_PEC = "#btnOk"
TEXTAREA_OBSERVACOES_PEC = "textarea[id*='observacoes']"
```

---

### `Prazo/`

Loops de prazo e atividades (ciclos 1 e 2).

**Ponto de entrada via `x.py`:**
```python
from Prazo import loop_prazo, fluxo_pz, fluxo_prazo
```

**Equivalentes no legado:**
- `loop_prazo` → `ref2bprazo.py:48412` (`loopprazo`)
- `fluxo_pz` → `refbackup.py:48948` (`fluxopz`)
- `fluxo_prazo` → `ref2bfluxo.py:50629` (`fluxoprazo`)

**Estrutura de ciclos (legado `ref2bprazo.py`):**
- Ciclo 1 (movimentação em lote):
  - `ciclo1aplicarfiltrofases` (47264) → `ciclo1marcartodas` (47349) → `ciclo1abrirsuitcase` (47383) → `ciclo1movimentardestino` (47598) → `ciclo1` (47781)
- Ciclo 2 (processamento individual):
  - `ciclo2aplicarfiltros` (47846) → `selecionarprocessosporgigsajjt` (47919) → `ciclo2criaratividadexs` (48070) → `ciclo2loopprovidencias` (48243) → `ciclo2` (48302)

**Helpers de fluxo (`ref2bfluxo.py`):**
- `aplicarfiltroatividadesxs` (50665)
- `indexarprocessoslista` (50715)
- `filtrarprocessosnaoexecutados` (50734)
- `processarprocessoindividual` (50801)
- `executarcallbackprocesso` (50860)
- `gerenciarabasaposprocesso` (50898)

---

### `SISB/`

Rotinas de SISBAJUD — bloqueios, consultas, relatórios.

**Equivalentes no legado:**
- `inserirrelatorioconcisosisbajud` (`ref.py:5908`)
- `wrappersisbajudgenerico` (`refinit.py:18729`)
- `wrapperjuntadageral` (`refinit.py:18780`)
- `criarjsotimizado` (`ref.py:38899`) — JS otimizado para juntada
- `executarjuntadapje` (`ref.py:38841`)
- Extração de resultados: `extrairresultadossisbajud` (`ref.py:44908`)
- Cálculo de estratégia de bloqueio: `calcularestrategiabloqueio` (`ref.py:38550`)
- Geração de relatório completo: `gerarrelatorioordem` (`ref.py:38629`)

---

### `atos/`

Wrappers para atos judiciais, comunicações e movimentos.

**Exports principais (do legado `ref.py`):**
```python
# Atos judiciais
fluxocls, atojudicial, atopesquisas, makeatowrapper, idpj

# Comunicação judicial
comunicacaojudicial, makecomunicacaowrapper

# Movimentos
mov, movsob, movfimsob, movarquivar, movexec, movaud, movprazo

# Wrappers PEC
pecbloqueio, pecdecisao, pecidpj, peceditalidpj, peceditaldec,
peccpgeral, pecexcluiargos, pecmddgeral, pecmddaud, peceditalaud,
pecsigilo, pecord, pecsum

# Visibilidade
visibilidadesigilosos, executarvisibilidadesigilosossenecessario
```

**Funções-chave do legado para referência:**
- `mov` (`ref.py:4801`) — movimentação com retry e gestão de aba de detalhe
- `movsob` (`ref.py:5090`) — movimentação de sobrestamento (complexa, ~290 linhas)
- `atojudicial` (`ref.py:3578`) — ato judicial completo (~720 linhas)
- `comunicacaojudicial` (`ref.py:1167`) — comunicação judicial com destinatário inteligente
- `selecionardestinatariopordocumento` (`ref.py:1221`) — seleção de destinatário por CPF/CNPJ

---

## 3. Utilitários Transversais

### Monitoramento de Progresso (Unificado)

Padrão moderno: funções em `Fix/` baseadas em JSON de progresso por módulo.

**Legado de referência (`ref.py` e `refprogressounificado.py`):**
- `carregarprogressounificado` / `salvarprogressounificado` (14040/14081)
- `marcarprocessoexecutadounificado` (14265)
- `processojaexecutadounificado` (14231)
- `executarcommonitoramentounificado` (14323) — wrapper completo com retry e log
- Versões específicas por módulo: `*pec`, `*mandado`, `*p2b`, `*pet`

### Coleta de Dados do Processo (API REST PJe)

O PJe expõe API interna. O legado a usa extensivamente:

- `extrairdadosprocesso` (`refinterativo.py:11411`) — dados completos via API
- `obteridprocessoviaapi` (`refinterativo.py:11452`)
- `obterdadosprocessoviaapi` (`refinterativo.py:11466`)
- `sessionfromdriver` (`ref.py:17530`) — extrai sessão HTTP do driver para reuso em API
- `idprocessopornumero` (`ref.py:17327`) — converte número CNJ em ID interno PJe
- `atividadesgigs` (`ref.py:17379`) — lista atividades GIGS do processo
- `obtergigscomfase` (`ref.py:17473`) — GIGS com fase processual
- `obterchaveultimodespachodecisaosentenca` (`ref.py:17799`)
- `obtertextodocumento` (`ref.py:17887`)

### Inserção de Conteúdo no Editor CKEditor (PJe)

- `inserirhtmleditor` (`ref.py:15990` e `16173`) — duas versões, a segunda mais robusta
- `inserirtextoeditor` (`ref.py:16051`)
- `inserirlinkatovalidacao` (`ref.py:16360`)
- `substituirmarcadorporconteudo` (`ref.py:19548`) — substitui marcadores no template (~270 linhas)
- `preenchercamposangularmaterial` (`ref.py:17016`) — preenche campos Angular Material (~160 linhas)

### Login e Driver

- `logincpf` (`refpje.py:15326`) — login principal com CPF (~100 linhas)
- `loginautomaticodireto` (`refpje.py:15276`)
- `salvarcookiessessao` / `carregarcookiessessao` (`ref.py:9231/9368`) — reutilização de sessão
- `verificareaplicarcookies` (`ref.py:9440`)
- `criardriverVT` (`ref.py:51052`) — driver VT legado (240 linhas, muito detalhe de perfil)
- `criardriverPC` (`ref.py:9022`) — driver PC legado

### Helpers Headless (todos em `ref.py`, seção ~13483–13738)

| Função legado | Propósito |
|---|---|
| `limparoverlaysheadless` (13483) | Remove overlays/modais que bloqueiam cliques |
| `scrolltoelementsafe` (13530) | scrollIntoView seguro com fallback |
| `clickheadlesssafe` (13562) | Click com scroll + JS fallback (~50 linhas) |
| `waitandclickheadless` (13614) | Aguarda + clica de forma headless-safe |
| `findelementheadlesssafe` (13622) | Find com múltiplas estratégias |
| `executarcomretryheadless` (13653) | Retry com backoff para operações instáveis |
| `aguardarelementoheadlesssafe` (13710) | Wait com observer nativo |

---

## 4. Seletores Angular Material (PJe)

O PJe usa Angular Material pesado. Atributos mais confiáveis para localizar elementos:

```
mattooltip      → botões de ação (ex.: 'button[mattooltip="Salvar"]')
aria-label      → inputs e regiões
mat-dialog      → .mat-dialog-content, .mat-dialog-actions
mat-table       → mat-table.mat-table, tr.cdk-drag
mat-chip        → .mat-chip-remove
mat-form-field  → mat-form-field input
fa-*            → ícones FontAwesome (ex.: .fa-tags, .fa-bars)
```

Constantes prontas em `Fix/selectors_pje.py`:

```python
FA_TAGS_ICON = ".fa-tags"
MENU_FA_BARS = ".fa-bars"
TABELA_PROCESSOS = "mat-table.mat-table"
LINHAS_PROCESSOS = "tr.cdk-drag"
BTN_TAREFA_PROCESSO = 'button[mattooltip="Abre a tarefa do processo"]'
BTN_CONFIRMAR_DIALOG = ".mat-dialog-actions > button:nth-child(1) > span"
BTN_ANEXOS = "pje-timeline-anexos > div > div"
ANEXOS_LIST = ".tl-item-anexo"
INPUT_TITULO_POSTIT = "#tituloPostit"
```

---

## 5. Padrões Que NÃO Devem Retornar do Legado

Estes padrões existem no LEGADO mas estão **banidos** no código moderno:

| Padrão legado | Substituição moderna |
|---|---|
| `try/except` chains de seletores | `SmartFinder.find(driver, key, candidates)` |
| `time.sleep()` como espera primária | `aguardar_renderizacao_nativa(driver)` |
| `WebDriverWait` em loop | MutationObserver via `Fix/` |
| Logs verbosos de tentativas | Apenas mudanças de estado no log principal |
| Coordenadas absolutas / ActionChains com posição | `scrollIntoView` + `.click()` |
| Polling de spinner com sleep | Observer nativo que detecta remoção do `.mat-progress-spinner` |

---

## 6. Arquivos de Estado e Cache (Runtime)

| Arquivo | Propósito |
|---|---|
| `aprendizado_seletores.json` | Cache do SmartFinder com seletores vencedores por chave |
| `monitor_aprendizado.log` | Log isolado do SmartFinder (não poluir o log principal) |
| `logs_execucao/` | Logs da execução principal gerados por `x.py` |
| `progress_*.json` | Arquivos de progresso por módulo (mandado, pec, prazo, p2b) |

---

## 7. Índice de Referência para Consulta Cirúrgica no LEGADO

Use este índice para abrir **apenas** o trecho necessário de `LEGADO.md`:

### Drivers e Login
- Driver PC: `ref.py:9022` | Driver VT: `ref.py:51052` | Login CPF: `refpje.py:15326`
- Cookies: `ref.py:9231` (salvar), `ref.py:9368` (carregar)
- Validar conexão driver: `refinit.py:7195` | `ref.py:16538`

### Waits e Headless
- Helpers headless: `ref.py:13483–13738`
- `safeclick`: `ref.py:7642` | `aguardareclicar`: `ref.py:7903` | `esperarelemento`: `ref.py:7825`
- MutationObserver/observer: `ref.py:39103` (`createmutationobserver`)

### Fluxos Mandado
- Navegação + fluxo robusto: `ref2bfluxohelpers.py:44258–44533`
- Análise mandado: `ref.py:45493–45807`

### Fluxos PEC
- `executarfluxonovo`: `ref.py:27015` | `executarfluxorobusto`: `ref.py:26852`
- Buckets PEC: `ref.py:27213–28449`

### Fluxos Prazo
- `loopprazo`: `ref2bprazo.py:48412` | `ciclo1`: `ref2bprazo.py:47781` | `ciclo2`: `ref2bprazo.py:48302`
- Helpers fluxo prazo: `ref2bfluxo.py:50629–50921`

### Atos e Movimentos
- `atojudicial`: `ref.py:3578` | `mov`: `ref.py:4801` | `movsob`: `ref.py:5090`
- Comunicação judicial: `ref.py:1167`

### API e Coleta
- Dados processo: `refinterativo.py:11411` | Session do driver: `ref.py:17530`
- GIGS completo: `ref.py:17379–17527`

### Editor CKEditor
- Inserir HTML: `ref.py:16173` | Substituir marcadores: `ref.py:19548`
- Campos Angular Material: `ref.py:17016`

### Progresso Unificado
- Monitoramento completo: `ref.py:14323` (`executarcommonitoramentounificado`)
- Progresso PEC: `ref.py:21016–21173` | Progresso Mandado: `ref.py:14461–14477`

### SISB / Bloqueios
- Estratégia bloqueio: `ref.py:38550` | Relatório ordem: `ref.py:38629`
- JS otimizado juntada: `ref.py:38899`
