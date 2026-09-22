# PLANO DE MIGRAÇÃO — Playwright como arquitetura única do PJePlus

> Documento de execução para agente de codificação. Escopo: migração completa
> Selenium → Playwright nativo, limpeza de comentários, política de log de falha
> e inventário de código morto. Baseline medido em 22/09/2026.

---

## RESUMO EXECUTIVO (leia antes de qualquer coisa)

**Objetivo:** ao final, `pw.py` roda sobre Playwright nativo, sem nenhuma dependência
de Selenium no código de negócio, sem camada de compatibilidade, com log de falha
(único artefato útil) e código morto inventariado.

**Números do baseline (medidos):**

| Métrica | Valor |
|---|---|
| Arquivos com `import selenium` | 87 |
| `driver.find_element` / `find_elements` | 288 / 151 |
| `driver.execute_script` | 278 |
| `driver.window_handles` | 72 |
| `time.sleep` / `WebDriverWait` / `expected_conditions` | 120 / 182 / 34 |
| Camada de compatibilidade | `Play/pjeplay/` — 17 módulos, ~120 KB |
| Vocabulário nativo já existente e em uso | `Fix/espera.py` (15 fns) + `pjeplay/nativo.py` (~25 fns); 128 call sites já migrados |
| Comentários (linhas `#`) | 3.476 de 52.949 linhas (6,6%) |
| `logger.info` / `print` / `logger.debug` | 1.337 / 226 / 441 |
| `logger.warning` / `logger.error` | 376 / 770 |

**Regra de ouro:** nenhuma fase muda comportamento. Migração é mecânica e
verificável. Onde não houver substituição segura, o agente **para e registra**
— nunca adivinha.

---

## 1. MODELO EXECUTOR (pesquisa — decisão tomada)

**Primário: Gemini 3.8 Flash. Escalada: Gemini 3.1 Pro** (para `Fix/core.py` e
arquivos onde o Flash falhar 2 vezes).

Dados que sustentam a escolha:

| Benchmark | 3.8 Flash | 3.1 Pro | Leitura |
|---|---|---|---|
| Terminal-Bench 2.1 (agêntico) | **89,4%** | 70,8% | Flash é muito melhor no laço "editar → rodar teste → corrigir" |
| DeepSWE v1.1 (long-horizon SWE) | **73,7%** | — | Migração longa em vários arquivos |
| SWE-bench Verified | ~75% | **80,6%** | Pro ganha em bug isolado de tentativa única |
| Preço (in/out por 1M) | **$0,75 / $3,75** | ~$2 / $12 | Flash é ~5× mais barato — e o trabalho são milhares de edições pequenas |
| Contexto | 1M | 1M | Empate |

**Por que Flash:** este trabalho é um laço agêntico longo e repetitivo com verificação
automática — exatamente onde o Flash 3.8 (GA 02/09/2026) lidera e onde o custo por
iteração domina o custo total. O Pro só compensa em raciocínio isolado difícil
(`Fix/core.py`, 3.532 linhas) — use-o ali, não no atacado.

**Aviso de preço:** o preço promocional do Flash dobra em 01/01/2027. Faça o atacado antes.

**Lição da pesquisa (importa mais que o modelo):** o formato de edição/harness pesa
mais que o modelo na taxa de sucesso de patch (+15 pts em média só trocando a
ferramenta de edição). Por isso este plano impõe: edições pequenas, teste após cada
arquivo, reverter em vez de "consertar". **Teste e reversão garantem a migração, não o modelo.**

---

## 2. BRANCH, BACKUP E PONTOS DE RETORNO

**Branch:** `refactor/pw-nativo`, criada a partir de `main`.

```bash
git checkout main && git pull
git checkout -b refactor/pw-nativo
git tag pre-refac                       # ponto zero — rollback total
git bundle create ../backup-pjeplus-pre-refac-$(date +%Y%m%d).bundle --all
```

**Tags por fase (o "ponto de retorno preciso"):** `refac-f0`, `refac-f1`, … `refac-f7`.
Ao fechar cada fase com teste verde:

```bash
git tag refac-fN
git bundle create ../backup-refac-fN-$(date +%Y%m%d).bundle --all   # ~8 MB, barato
```

**Regras de controle:**

1. `main` só recebe merge **depois** de execução real de `py pw.py` aprovada pelo Silas — nunca antes.
2. Nunca `push --force` na `refactor/pw-nativo` depois de um run real aprovado (as tags são o contrato).
3. Rollback por arquivo: `git checkout refac-fN -- <arquivo>`.
4. Rollback por fase: `git reset --hard refac-fN`.
5. Rollback total: checkout da tag `pre-refac` ou restauração do bundle.
6. **Um commit por tarefa**, mensagem `refac(fN): <escopo> — <ação>`. Nunca misturar fase mecânica com mudança de comportamento.

---

## 3. CONTRATO DO EXECUTOR (regras invioláveis)

1. **Mecânica ≠ comportamento.** Se um teste falhar após uma edição mecânica, **reverta o arquivo** (`git checkout -- <arquivo>`), registre em `docs/PENDENCIAS.md` e siga. Não "conserte" — isso transformaria migração em mudança de lógica.
2. **Não criar helpers novos.** Usar o vocabulário existente (`Fix/espera.py`, `nativo.py` — tabela na seção 9). Se faltar uma operação, registre a lacuna; não invente função.
3. **Não tocar em:** `Play/pjeplay/*` (exceto na fase F5), sleeps anti-detecção do SISB, fluxo de cookies/login, `.venv`, `requirements` (exceto F6).
4. **Não adivinhar.** Sem substituição segura → `docs/PENDENCIAS.md` com arquivo:linha e motivo. Nunca reescrever lógica por conta própria.
5. **Sem varredura de formatação.** Nada de reformatar arquivo inteiro, reordenar imports ou trocar aspas. Diff tem que ser legível e revisável.
6. **Testar depois de cada edição** (protocolo na seção 8) e reportar a saída real — não "deve funcionar".
7. **Duas falhas no mesmo arquivo → pare e escale** ao Pro 3.1 (ou ao Silas, se for decisão de comportamento).
8. **Não editar:** `logs_execucao/`, `erro.md`, `.pje_watch_state.json`, `Play/medicoes/` (são artefatos de execução/observação).
9. **Ordem importa:** `pjeplay.iniciar()` deve continuar sendo chamado antes de qualquer import do projeto no `pw.py` (ver seção 11).

---

## 4. POLÍTICA DE COMENTÁRIOS

**Escopo:** todo código que roda em `pw.py` (`atos/`, `Fix/`, `Mandado/`, `PEC/`,
`Prazo/`, `SISB/`, `Triagem/`, `Peticao/`, `bianca/`, `x.py` e scripts da raiz).

**Regra:** zero comentários e zero docstrings descritivos. Remover:
- narração (`# Buffer curto pos-click`, `# Pequena espera adicional`, `# no primeiro select`);
- docstrings de função com descrição do óbvio;
- blocos de explicação histórica.

**Permanecem (únicos casos permitidos):**
- pragmas funcionais: `# noqa`, `# type: ignore`, `# pylint:`, `# fmt: off/on`;
- shebang e linha de encoding (se houver);
- marcadores temporários `# DEAD:` (seção 6) — saem junto com o código morto.

**Fatias de conhecimento que NÃO podem virar fumaça:** os fatos que hoje vivem em
comentários críticos (throttle SISB, ordem do `iniciar()`, particularidades do
CDK overlay) migram para **`docs/INVARIANTES.md`** — um arquivo, não espalhados.
O lint (seção 10) referencia essa lista.

**Exceção de área:** `tools/`, `Play/smoke.py`, `play/` (ferramental de teste) ficam
com seus docstrings — não são código de execução.

---

## 5. POLÍTICA DE LOG — SÓ FALHA (CONTRATO DE LOG)

**Princípio:** o log existe para depurar falha. Sucesso não gera linha.

**Remover:** `logger.info` de narração (1.337), `print` (226), `logger.debug` (441,
salvo sob flag `PJE_DEBUG=1`), linhas de sucesso por item (`✅ Processo marcado`,
`OK (n s)` de passo interno), marcadores de progresso não-falha.

**Remover também a duplicação:** hoje cada linha aparece 2× (FileHandler + `TeeOutput`
capturando `print` para o mesmo arquivo). Corrigir para **um único sink de arquivo**.

**CONTRATO FIXO — estas linhas NÃO podem ser alteradas nem removidas** (o monitor
`pje_watch.py` e a leitura diária dependem delas; strings exatas):

| Linha | Papel |
|---|---|
| `── fluxo: <X> ──` | abertura de fluxo |
| `[RESUMO] <fluxo> total=<N> sucesso=<M> erro=<K>` | **uma por fluxo, no fim** — veredito legível por máquina |
| `[FLUXO] OK (<t>)` / `[FLUXO] FALHA (<t>)` | veredito humano |
| `encerrando` | fim limpo do processo |
| todo `[ERROR]` / `[WARNING]` | falha com contexto: processo (`#id`), ação, exceção/texto |
| linha de item falhado com motivo | ex.: `[MANDADOS][CP] #<id>: baixarCP() falhou: <motivo>` |

**Formato de linha de falha (padrão a adotar):**
`[<MODULO>][<ACAO>] #<processo>: <motivo curto> | <detalhe>` — permite agrupar por módulo/ação.

**`erro.md` permanece** como está (já é só-falha, com stack).

**Consequência assumida:** o monitor será recalibrado depois da F1 para o novo contrato
(a presença/ausência do `[RESUMO]` passa a ser o sinal de execução completa).

---

## 6. CÓDIGO MORTO — MARCAÇÃO E INVENTÁRIO

**Arquivo-mestre:** `docs/CODIGO_MORTO.md` — inventário com evidência (arquivo:linha,
por que é morto, o que depende dele). Atualizado na mesma fase em que o item é detectado.

**Marcação inline (única exceção de comentário permitida):** `# DEAD: <id-do-inventário>`
— greppável, auditável, removido junto com o código na fase final.

**Semente do inventário (verificado em 22/09/2026):**

| Item | Evidência | Ação |
|---|---|---|
| `Andrei/` | 0 referências no pipeline (`x.py`/`pw.py` não importam) | marcar; deletar na F7 |
| `gen_bm.py`, `ad.py`, `temp_main_navegacao.py` (raiz) | 0 referências | marcar; deletar na F7 |
| `f.py` (harness multi-testes manual) | ferramenta manual, não roda em `pw.py` | decidir: `tools/` ou deletar |
| `Fix/driver_factory.py` | untracked, sem `criar_driver_pc` (função esperada não existe) | marcar; deletar na F7 |
| `Play/pjeplay/compat.py`, `element.py`, `waits.py`, `locators.py`, `actions.py` | camada Selenium falsa | deletar na F5 |
| `Play/migrar_sleeps.py` | ferramenta de migração | deletar ao fim da F2 |
| `TeeOutput` + handlers duplicados em `x.py` | causa da duplicação de linhas | deletar na F1 |
| flags `--sem-nativo` e `--selenium` | baseline de comparação | deletar na F6 |
| `ecarta_api.py` (raiz) | 1 referência — verificar | verificar na F2 |
| `limp.py`, `log.py` (raiz) | verificar sobreposição com `Fix/` | verificar na F2 |

Regra: **nada é deletado antes da F7** (exceto o que as fases F5/F6 já eliminam por
construção). Até lá, o marcador é o contrato.

---

## 7. FASES

Cada fase termina com: lint verde → smoke verde → **execução real de `py pw.py`
pelo Silas** → tag + bundle. Sem o run real, a fase não fecha.

### F0 — Preparação e travas (nenhuma mudança de comportamento)
- criar branch, tags e bundles (seção 2);
- criar `tools/check_pw.py` (especificação na seção 10) + `tools/pw_baseline.json` (contagem por arquivo);
- hook pre-commit que roda o lint em modo ratchet (mesmo padrão do hook do gitleaks já existente);
- criar `docs/INVARIANTES.md` (seção 11), `docs/CODIGO_MORTO.md` (seção 6), `docs/PENDENCIAS.md`;
- snapshot de referência: rodar `py play/smoke.py --projeto` e colar a saída em `docs/PENDENCIAS.md` (linha de base);
- adicionar a regra anti-Selenium ao `idx.md`/`.agents/rules/` (texto na seção 10.3).

**Saída:** `py tools/check_pw.py` roda e reporta o baseline; smoke verde; tag `refac-f0`.

### F1 — Piloto: `atos/comunicacao_preenchimento.py` (633 linhas, 18 chamadas)
Arquivo apontado como a origem da confusão (é o que faz o modelo "voltar ao Selenium").
Fazer a receita completa, em 4 commits pequenos:
1. **imports/tipos:** trocar `from selenium... import By` pelo `By` nativo; `driver: WebDriver` → `driver: Any`; remover imports Selenium só de tipagem;
2. **chamadas:** aplicar a tabela da seção 9;
3. **comentários/docstrings:** aplicar a seção 4;
4. **logs:** aplicar a seção 5 (sem tocar no contrato).

**Saída:** lint zero no arquivo; smoke verde; **run real** de um fluxo que use comunicação/minuta; tag `refac-f1`.
Se o run real validar a receita, ela vira o procedimento padrão das fases seguintes.

### F2 — Folhas e utilitários
`atos/wrappers_utils.py`, `atos/movimentos_*` (chips, despacho, fimsob, navegacao),
`atos/anexos*`, `atos/wrappers_mov.py`, `Fix/utils.py`, `Fix/facade_publica.py`,
`Fix/espera.py` (se necessário), `Fix/extracao.py`. Lotes de 3–5 arquivos, um commit
por lote, lint ratchet a cada lote. Rodar `py play/migrar_sleeps.py` (dry-run) antes
de aplicar em cada arquivo e `--aplicar` onde o relatório aprovar.

**Saída por lote:** lint zero nos arquivos; smoke verde. **Saída da fase:** run real; tag `refac-f2`.

### F3 — Domínios
`Mandado/`, `PEC/`, `Prazo/`, `SISB/`, `Peticao/`, `Triagem/`, `bianca/`, `atos/judicial*`,
`atos/comunicacao*` (restantes). **Atenção SISB:** sleeps anti-detecção e fluxo de
sessão/cookies são intocáveis (seção 11).

**Saída por módulo:** lint zero; smoke verde. **Saída da fase:** run real de cada fluxo tocado (mandado, pec, p2b); tag `refac-f3`.

### F4 — Núcleo (aqui use o Pro 3.1)
`Fix/core.py` (3.532 linhas), `x.py`, `Fix/variaveis.py`, `Fix/browser_suporte.py`,
`Fix/diagnostico_runtime.py`, `Fix/monitoramento_progresso_unificado.py`, `pw.py`.
Trabalhar por função/seção, um commit por bloco de ~200 linhas.

**Bug conhecido a NÃO "consertar" aqui** (registrar em PENDENCIAS): `Fix/core.py:2551` importa
`obter_sessao_do_driver` de `Fix.variaveis`, que não existe (reais: `session_from_driver`,
`cliente_para`) — é mudança de comportamento, não migração.

**Saída:** lint zero; smoke verde; run real completo dos 3 formatos (mandado, pec, p2b); tag `refac-f4`.

### F5 — Desligar a compatibilidade
Quando **zero call sites** usarem a superfície Selenium: deletar `compat.py`, `element.py`,
`waits.py`, `locators.py`, `actions.py` (e o que sobrar de shim); remover a injeção em
`sys.modules` (`instalar()`); reduzir `PWDriver` a lançador/transporte (ou eliminar, se o
nativo cobrir). `Play/guarda.py` deve continuar verde.

**Saída:** smoke verde + run real; tag `refac-f5`.

### F6 — Selenium fora
Remover `--selenium` e `--sem-nativo`; remover Selenium de `requirements` e do `.venv`;
rodar `py pw.py` final; atualizar `Play/README.md` e docs para o estado novo.

**Saída:** `grep -r "import selenium" --include=*.py .` retorna **zero**; run real aprovado; tag `refac-f6`.

### F7 — Deleção do código morto (depois de ~5 execuções reais verdes)
Deletar todo item do `docs/CODIGO_MORTO.md` que não apareceu em nenhuma execução real
em 5 runs consecutivos; remover os marcadores `# DEAD:`; atualizar docs.

**Saída:** inventário vazio; tag `refac-f7`; merge em `main`.

---

## 8. PROTOCOLO DE TESTE INCREMENTAL

**Depois de cada arquivo editado:**
```bash
py -m py_compile <arquivo>          # sintaxe
py tools/check_pw.py               # ratchet: o arquivo não pode piorar
```

**Depois de cada lote/módulo:**
```bash
py play/smoke.py --projeto         # 82 verificações + carga real de Fix/ e negócio
py play/guarda.py                  # fronteira do fork (não recrescer cópia)
```

**Antes/depois de migrar sleeps:**
```bash
py play/migrar_sleeps.py           # dry-run: relata o que faria
py play/migrar_sleeps.py --aplicar # grava (só onde o relatório aprovar)
```

**Portão real (só o Silas, com login manual):**
```bash
py pw.py                           # execução definitiva
py pw.py --comparar a.json b.json  # comparação de medições entre fases
```
Guardar os JSON de `Play/medicoes/` de cada portão — são a evidência de não-regressão.

**Falhou um teste após edição mecânica?** `git checkout -- <arquivo>` e PENDENCIAS.md. Não consertar.

---

## 9. TABELA DE MAPEAMENTO — Selenium → nativo existente

| Hoje | Substituir por | Observação |
|---|---|---|
| `driver.find_element(By.X, s)` | `espera.elemento(driver, s)` | re-resolve o DOM (sem referência obsoleta) |
| `driver.find_elements(By.X, s)` | `espera.elementos(driver, s)` | |
| `WebDriverWait + EC.visibility_of_element_located` | `espera.ate_aparecer(driver, s)` | condição observável |
| `EC.invisibility_of_element_located` | `espera.ate_sumir(driver, s)` | |
| `EC.element_to_be_clickable` | `espera.ate_habilitar(driver, s)` + clique | |
| `EC.text_to_be_present_in_element` | `espera.ate_texto(driver, s, texto)` | |
| `time.sleep(n)` | `espera.assentar(driver, n)` | via `migrar_sleeps.py`; teto idêntico |
| `driver.execute_script("return ...")` | `espera.ate_js(driver, expr)` | leitura de estado |
| `driver.execute_script("<ação>")` | helper nomeado existente (`safe_click`, `safe_click_no_scroll`, `click_headless_safe`, `scroll_to_element_safe`) | ação JS nunca fica solta no negócio |
| `driver.send_keys(v)` | `preencher_campo(driver, seletor, v)` | |
| `.clear()` + send_keys | `preencher_campo(..., limpar=True)` | |
| `driver.window_handles` + switch_to | `espera.ate_abas(driver, n)` | |
| `driver.get(url)` / esperar navegação | `espera.ate_url(driver, trecho)` | |
| `StaleElementReferenceException` | `espera.ate_obsoleto(driver, el)` | |
| `aguardar_renderizacao_nativa(...)` | manter (já é nativo) | usado no SISB |
| `By`, `Keys` | imports de `pjeplay.locators` | tirar o import Selenium |

**Não usar Playwright cru no negócio:** o código fala o vocabulário do projeto
(`espera.*` / `nativo.*`); `Page`/`Locator` ficam na camada nativa.

---

## 10. FERRAMENTA DE TRAVA — `tools/check_pw.py`

### 10.1 Comportamento
- varre `--include=*.py` fora de `.venv`, `worktrees`, `outros projetos`, `ORIGINAIS`;
- conta por arquivo os padrões proibidos:
  `import selenium`, `from selenium`, `driver.find_element`, `driver.find_elements`,
  `driver.execute_script`, `driver.send_keys`, `driver.window_handles`,
  `WebDriverWait`, `expected_conditions`, `time.sleep`, tipagem `WebDriver`;
- compara com `tools/pw_baseline.json` (**ratchet**): falha se qualquer arquivo **piorar**;
  arquivo que zerar entra em `migrados` e nunca mais pode voltar a ter ocorrência;
- `--atualizar-baseline` só é permitido após revisão humana (usado na F0 e no fecho de fase);
- saída legível: `arquivo — hoje N (baseline M) — status`.

### 10.2 Uso
```bash
py tools/check_pw.py               # verificação (falha ≠ 0 se regressão)
py tools/check_pw.py --relatorio   # visão geral por pasta
```

### 10.3 Regra para `idx.md` / `.agents/rules/` (colar)

```markdown
## Regra de arquitetura: Playwright é a única via

Todo código que roda em `py pw.py` fala o vocabulário nativo do projeto
(`Fix/espera.py`, `Play/pjeplay/nativo.py`) ou `Page`/`Locator`.

É proibido introduzir em arquivos do projeto:
`import selenium`, `driver.find_element`, `driver.find_elements`,
`driver.execute_script`, `driver.send_keys`, `driver.window_handles`,
`WebDriverWait`, `expected_conditions`, tipagem `WebDriver`, `time.sleep`.

Espera é sempre condição observável (`espera.ate_*`), nunca pausa cega.
JS só existe dentro de helper nomeado — nunca solto no fluxo de negócio.
A camada `Play/pjeplay/compat.py` existe apenas para módulos legados ainda não
migrados; ela não é justificativa para código novo no estilo Selenium.
Arquivo listado como migrado em `tools/pw_baseline.json` não pode regredir.
```

---

## 11. INVARIANTES (`docs/INVARIANTES.md` — criar na F0)

1. `Play/README.md`: `pjeplay.iniciar()` **antes** de qualquer import do projeto (hoje `pw.py` viola: importa `Fix.monitoramento_progresso_unificado` — que importa Selenium no topo — antes do `iniciar()`).
2. SISB: sleeps de throttle/anti-detecção são **deliberados** — o `migrar_sleeps.py` recusa tocá-los, e esta regra também.
3. Login PJe/SISBAJUD é **manual**; cookies de sessão e o fluxo OAuth (`login.seam` → `meu-painel`) não mudam.
4. `espera.assentar` é limitada pelo mesmo N do `time.sleep` que substitui: nenhum caminho fica mais lento.
5. Erros HTTP do PJe (ARQ-516/403/500) são ambientais: retry/backoff onde existe, não "correção".
6. `erro.md` é o canal de falha com stack; o log de execução é o canal de falha resumido.

---

## 12. ARMADILHAS CONHECIDAS (histórico real de falhas — não repetir)

| Armadilha | Detalhe |
|---|---|
| Clique em polo ativo | exige escada: limpar overlay → clique real → fallback sintético. `dispatchEvent` sozinho não efetiva em `mat-icon-button`. |
| `mov_sob` | valida por snackbar efêmera → falso-negativo (marca falha sem confirmar). Trocar por condição observável é mudança de comportamento: **registrar, não migrar**. |
| Cascata "Nenhuma janela aberta" | dezenas de processos morrem em cadeia após a janela fechar. Não é regressão de migração; é ausência de health-check. |
| `Fix/core.py:2551` | import quebrado (`obter_sessao_do_driver`) → `baixarCP()` sempre falha. Bug de código: registrar. |
| `pdfplumber` | ausente no `.venv` (3.13) — não é problema de migração. |
| Duplicação de log | `TeeOutput` + FileHandler → cada linha 2×. Só corrigir na F1. |

---

## 13. PROMPT DE KICKOFF (colar no Gemini)

```text
Leia D:\pjeplus\PLANO_MIGRACAO_PW.md por inteiro antes de agir.
Execute fase por fase, na ordem. Para cada fase:
1. crie a tag/bundle de retorno conforme a seção 2;
2. trabalhe em commits pequenos (seção 3), testando após cada arquivo (seção 8);
3. NÃO mude comportamento: se um teste falhar, reverta o arquivo e registre em docs/PENDENCIAS.md;
4. ao fim da fase, rode o protocolo de teste da seção 8 e me mostre a saída real;
5. pare e aguarde minha execução real de `py pw.py` antes de fechar a fase.

Comece pela F0 (travas) e me mostre o baseline do tools/check_pw.py antes de seguir.
Não peça confirmação para tarefas mecânicas dentro da fase; peça apenas quando
o plano disser "registrar" ou quando houver dúvida de comportamento.
```

---

*Baseline e fatos verificados em 22/09/2026. Alterar este plano = revisar as tags de fase.*
