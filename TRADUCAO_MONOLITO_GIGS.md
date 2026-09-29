# Tradução do monólito GIGS → arquitetura Playwright (PJePlus)

> Análise de 22/09/2026. Fonte: `+pje/PJe-Atual/gigs-plugin.js` (37.807 linhas, 627 funções) e
> módulos `+pje/comum/` (mini-selenium.js, seletores.js, editor-documento.js).
> Objetivo: verificar como os **elementos e padrões de interação** do monólito (que é
> funcional e testado em produção) estão traduzidos no bot, e o que falta traduzir.

---

## 1. Os dois projetos têm a MESMA arquitetura conceitual

| Papel | Monólito (extensão, JS in-page) | Bot (Playwright, Python out-of-page) |
|---|---|---|
| Camada de primitivas | `+pje/comum/mini-selenium.js` (1.411 linhas) | `Play/pjeplay/nativo.py` + `Fix/espera.py` |
| Fluxo de negócio | `gigs-plugin.js` (627 funções) | `atos/`, `PEC/`, `Mandado/`, `Prazo/`, `SISB/` |
| Confirmação | MutationObserver (62 usos) | polling + `espera.*` |
| Vocabulário de espera | `esperarElemento/esperarColecao/esperarDesaparecer` | `ate_aparecer/ate_sumir/ate_habilitar/...` |

**Boa notícia:** o vocabulário é isomórfico — a tradução é direta, função por função.
O monólito é a **melhor referência de seletores** que existe para o PJe (foi escrito contra o
DOM real e está em uso).

---

## 2. Tabela de tradução de padrões (JS → Playwright → vocabulário do bot)

| Monólito (JS) | Playwright idiomático | Vocabulário já existente no bot |
|---|---|---|
| `esperarElemento(sel)` — MutationObserver, 5 s, espera `!disabled` | `page.locator(sel).wait_for(state="visible")` + `expect(l).to_be_enabled()` | `espera.ate_aparecer` + `espera.ate_habilitar` |
| `esperarElemento(sel, "texto")` | `expect(locator.filter(has_text=...)).to_be_visible()` | `espera.ate_texto` |
| `esperarColecao(sel, n)` | `expect(page.locator(sel)).to_have_count(n)` | `espera.elementos` / `ate_abas` |
| `esperarDesaparecer(el)` | `expect(locator).to_be_hidden()` | `espera.ate_sumir` |
| `clicarBotao(sel)` (893 usos) | `locator.click()` (auto-wait nativo) | `safe_click` / `aguardar_e_clicar` |
| `preencherInput(sel, v)` | `locator.fill(v)` | `preencher_campo` |
| `preencherInput(..., usarExecCommand)` | `locator.evaluate(el => execCommand...)` | Fix/utils.py (abordagem execCommand) ✅ já traduzido |
| `querySelectorByText(tag, txt)` | `page.get_by_text(txt)` ou `.filter(has_text=)` | `espera.ate_texto` |
| `ligar_mutation_observer` (confirma por **remoção** do nó) | `expect(locator).to_be_hidden()` | `espera.ate_sumir` |
| snackbar "inserido com sucesso no editor" | `expect(page.locator('simple-snack-bar')).to_contain_text(...)` | polling atual — ver achado 2 |
| seletor escopado `pje-x button[aria-label=...]` | `page.locator('pje-x').locator('button[...]')` | **escopo ainda não usado** — ver achado 1 |

---

## 3. Vocabulário de seletores — comparação

| Família | Monólito | Bot | Leitura |
|---|---|---|---|
| `aria-label` | **96 únicos** | 65 | monólito é mais "aria-first" |
| `pje-*` (custom elements) | 56 | 44 | monólito escopa mais |
| `mat-*` | 79 | 130 | bot mais dependente de Angular Material |
| `cdk-overlay*` | 3 | 19 | bot tem mais overlay-workarounds |
| `id` | 81 | 41 | — |
| classe | 98 | 113 | — |
| **xpath** | **0** | **162 usos (`By.XPATH`)** | monólito nunca usa xpath |
| **posicionais** (`nth-child`) | **0** | 6+ sítios | monólito usa `td[data-label*="..."]` |

---

## 4. ACHADOS ACIONÁVEIS (verificados no código do bot)

### A1 — Botão "Gravar movimentos" sem escopo (risco de clique no botão errado)
- **Monólito (34 usos):** `pje-lancador-movimentos-dialogo button[aria-label="Gravar os movimentos a serem lançados"]`
- **Bot:** `atos/judicial_fluxo.py:876` — `button[aria-label='Gravar os movimentos a serem lançados']` **sem escopo**.
- **Tradução:** `espera.elemento(driver, 'pje-lancador-movimentos-dialogo button[aria-label="Gravar os movimentos a serem lançados"]')`.
- **Por quê importa:** com múltiplas janelas/diálogos abertos (cenário real do PEC), o seletor sem escopo
  pode casar com o botão de outra janela.

### A2 — Validação do editor usa `querySelector` global (pode validar o editor errado)
- **Bot:** `atos/comunicacao_preenchimento.py:129-135` (`_aguardar_ck_com_conteudo`) testa
  `.ck-editor__editable`, `.ck-content`, `div[contenteditable=true]`, `textarea`, `iframe` — via
  `document.querySelector(sel)` **global, sem escopo**, e aceita o **primeiro** que casar.
  Numa página com mais de um editor (minuta + despacho), pode validar o editor errado → falso
  "conteúdo confirmado" (ou falso "não confirmado", como no run de 22/09: *Conteudo do modelo nao
  presente no editor*).
- **Monólito (referência):** `verificarSeExisteTextoNoEditor()` espera `pje-arvore-modelo-documento`,
  pega `SELETORES.editor.areaConteudo` e valida `innerText.length > 1` **ou** `querySelector('figure')`
  (imagem anexada sem texto) — sempre no editor escopado.
- **Tradução:** escopar por `pje-arvore-modelo-documento` e usar o seletor do editor completo (ver A3),
  aceitando também `figure` como conteúdo válido.

### A3 — Seletor do editor incompleto em 3 lugares (o monólito tem as 3 condições juntas)
- **Monólito:** `div[class*="area-conteudo"][contenteditable="true"][role="textbox"]`
- **Bot:**
  - `atos/judicial_fluxo.py:429` → `div[class*="area-conteudo"][contenteditable="true"]` (falta `[role="textbox"]`)
  - `Fix/utils.py:1019` → `div[role="textbox"][contenteditable="true"]` (falta `[class*="area-conteudo"]`)
  - `PEC/anexos/anexos_juntador_helpers.py:281` → idem
- **Tradução:** unificar na forma do monólito (3 condições) — é o seletor que está em produção na extensão.

### A4 — Chips: bot remove sem expandir e sem escopo
- **Bot:** `atos/movimentos_chips.py:47` — `//mat-chip` global, sem escopo `pje-lista-etiquetas`
  e **sem** clicar em "Expandir Chips".
- **Monólito:** `pje-lista-etiquetas button[aria-label="Expandir Chips"]` (se existir) →
  `esperarColecao('pje-lista-etiquetas mat-chip', 1, 1000)` → só então opera.
- **Por quê importa:** se os chips estiverem colapsados, o bot não os vê (remoção silenciosamente vazia).

### A5 — Sobrestamento: bot não usa o custom element do botão de prazo
- **Monólito:** `pje-motivos-sobrestamento button[aria-label="Definir prazo para este motivo de sobrestamento"]`
  e `pje-dialog-prazo-sobrestamento input[data-placeholder*="Prazo em meses"]`.
- **Bot:** usa `pje-dialog-prazo-sobrestamento` (✅) mas **não** usa `pje-motivos-sobrestamento`.
- **Observação:** a confirmação do monólito é por **mutação** (o diálogo sumir = sucesso) — o que em
  Playwright é `expect(locator).to_be_hidden()`. O bot faz polling com fallback "assume sucesso",
  origem do falso-negativo do `mov_sob` já relatado. Traduzir a confirmação para condição observável
  (diálogo sumiu **ou** erro explícito na snackbar) elimina o falso-negativo.

### A6 — Posicionais: bot usa `nth-child` onde o monólito usa `data-label`
- **Bot:** `Prazo/loop_orquestrador.py:159,185,223` → `td:nth-child(9) time`; `Fix/extracao.py:892` → `li:nth-child(16)`.
- **Monólito (0 nth-child):** `td[data-label*="sequencial"|"dataProgramada"|"valorBloqueado"|"dataFim"|"processo"]`.
- **Tradução:** trocar índice por `data-label` — imune a reordenação de coluna.

### A7 — XPath: 162 usos no bot, 0 no monólito
- Top: `Fix/extracao.py` (21), `bianca/triagem/acoes.py` (20), `Fix/core.py` (18), `Triagem/analise_execucao.py` (10).
- O monólito prova que **todo** o DOM necessário é alcançável por CSS + aria-label + custom elements.
- **Tradução:** converter por prioridade (primeiro os de `Fix/core.py` e `Fix/extracao.py`, que ficam no caminho de execução).

### A8 — Catálogo de seletores com override remoto (ideia do monólito)
- `+pje/comum/seletores.js`: objeto central `SELETORES` + `carregarSeletoresRemotos(URL_BASE, versaoPje)`
  que baixa `seletores.json` por versão do PJe e faz merge — **atualiza seletor sem mexer no código**.
- O bot tem `Play/pjeplay/monitor_seletores.py` (mede HIT/MISS) mas nenhum catálogo central.
- **Decisão sua** (envolve criar estrutura nova); a versão mínima é só centralizar os seletores mais
  frágeis num único módulo já existente.

---

## 5. Arsenal de referência: seletores do monólito ausentes no bot

178 `aria-label` usados pelo monólito não aparecem no bot (excluída a UI própria da extensão).
Destaques com valor direto para os fluxos do bot:

| aria-label | Usos no monólito | Uso provável no bot |
|---|---|---|
| `Ir para Minuta` | 6 | navegação de tarefa |
| `Meu Painel` | 5 | retorno ao painel |
| `Limpar Filtro` / `Limpa o filtro aplicado pela busca` | 4 / 5 | filtros de painel |
| `Classe Judicial` / `Filtro Classe Judicial` | 4 / 4 | filtros |
| `Expandir Chips` | 4 | A4 acima |
| `Classe Judicial`, `Fase processual` | 2-4 | filtros |
| `Ato confeccionado` | 3 | verificação de comunicação |
| `Retornar minuta para elaboração` | 2 | fluxo de comunicação |
| `Adicionar parte ao processo` | 4 | fluxo de comunicação |
| `Pesquisar CPF` / `Pesquisar CNPJ` | 4 / 2 | destinatários |

**Não traduzir** (é UI da própria extensão, não do PJe): tooltips, menus `maisPje_*`, caixas de
alerta, barra de botões, ícones — ~40% do arquivo. Também não traduzir: `style.visibility`
(826 usos), `document.createElement` (585), `browser.runtime.sendMessage` (181) — são o *chrome*
da extensão, sem análogo no bot.

---

## 6. Resumo do estado da tradução

| Área | Traduzido? | Nota |
|---|---|---|
| Vocabulário de espera (`espera.*`) | ✅ equivalente | isomórfico ao `mini-selenium.js` |
| Cliques e preenchimento | ✅ equivalente | `safe_click`/`preencher_campo` já cobrem |
| execCommand (Angular/CKEditor) | ✅ presente | Fix/utils.py |
| Snackbar de confirmação | ⚠️ parcial | polling funciona; melhorável com condição observável |
| Escopo por custom element (`pje-x ...`) | ❌ ausente | achados A1, A4 |
| Seletor do editor (3 condições) | ⚠️ 2/3 em 3 lugares | achado A3 |
| Validação de conteúdo do editor | ⚠️ frágil | achado A2 |
| `data-label` em vez de índice | ❌ não feito | achado A6 |
| XPath → CSS/aria | ❌ 162 usos | achado A7 |
| Catálogo de seletores | ❌ inexistente | achado A8 (decisão sua) |

---

## 7. Recomendação de sequência (para encaixar na migração)

1. **A3 + A2 juntos** (mesmo arquivo/fluxo, é o que falhou em 22/09): unificar o seletor do editor
   nas 3 condições e escopar a validação de conteúdo por `pje-arvore-modelo-documento`.
2. **A1** (uma linha): escopar o botão "Gravar movimentos".
3. **A4** (bloco curto): expandir chips antes de operar, com escopo.
4. **A5** (fecha o falso-negativo do `mov_sob`): confirmação por desaparecimento do diálogo.
5. **A6** (pontual): `nth-child` → `data-label`.
6. **A7** (por módulo, junto da migração Selenium→Playwright de cada arquivo): xpath → CSS/aria.

Nenhum desses itens contraria `PLANO_MIGRACAO_PW.md` — todos usam o vocabulário já existente,
sem abstração nova.
