# 03 — Mapa de etapas

Cada etapa é executável por **uma janela de chat isolada**, sem conhecer as
outras. O que garante isso é a **propriedade exclusiva de arquivos**: duas
etapas nunca editam o mesmo arquivo.

---

## Como usar

Em cada janela nova, na ordem:

1. `play/docs/00-contexto.md` — obrigatório, contém as proibições
2. `play/docs/02-esperas.md` — o vocabulário
3. `play/docs/etapas/E<n>-*.md` — a etapa daquela janela
4. `play/docs/01-traducao.md` e `04-headless.md` — consulta

O prompt pronto para colar numa janela nova está em
[`PROMPT-JANELA.md`](PROMPT-JANELA.md), com a divisão em 3 trilhas.

Nenhuma etapa depende do relatório de outra. Se uma delas parar no meio, as
demais seguem.

---

## Propriedade de arquivos

| Etapa | Arquivos exclusivos | Trabalho |
|---|---|---|
| **E1** | `Fix/espera.py`, `Fix/core.py`, `play/pjeplay/nativo.py` | fecha o vocabulário + 34 sleeps e 31 waits do core |
| **E2** | `Fix/utils.py`, `Fix/extracao.py` | 35 waits, 41 EC, 10 sleeps |
| **E3** | `Fix/browser_suporte.py` | 7 waits + abas nativas |
| **E4** | `atos/**` | 69 waits, 72 EC, 13 sleeps ← maior bolsão |
| **E5** | `PEC/**` | 26 waits, 41 EC, 3 sleeps |
| **E6** | `Mandado/**` | 15 waits, 10 EC, 3 sleeps |
| **E7** | `Prazo/**` | 26 waits, 21 EC, 5 sleeps |
| **E8** | `SISB/**` **exceto** `SISB/Core/` | 35 waits, 43 EC, 21 sleeps |
| **E9** | `Fix/variaveis.py` | pontos de entrada da API nativa |
| **E10** | `play/medicoes/**` (não edita produção) | baseline e decisão |

Ninguém edita: `SISB/Core/`, `leg/`, `_archive/`, shims listados no `idx.md`.

---

## Paralelismo

**E1 a E9 podem rodar simultaneamente** — os conjuntos de arquivos são
disjuntos. Não há ordem obrigatória entre elas.

Duas ressalvas, e só duas:

- **E1 fecha o vocabulário.** E2–E8 podem precisar de `espera.elemento`,
  `elementos`, `ate_url`, `ate_abas`, `ate_obsoleto`, que só existem depois de
  E1. Se uma etapa esbarrar numa função ausente, o correto é **deixar aquele
  sítio como está e reportar** — nunca implementar a função por conta própria
  (isso editaria `Fix/espera.py`, que pertence a E1). Se puder escolher a ordem,
  rode **E1 primeiro**.
- **E10 é a última.** Precisa das outras para ter o que medir, e de acesso ao
  PJe real.

Ordem recomendada quando houver escolha:

```
E1  →  E2, E3, E4, E5, E6, E7, E8, E9  (em paralelo, qualquer ordem)  →  E10
```

---

## O que cada etapa entrega

Toda etapa termina com:

1. `py play/smoke.py --projeto` → **91/91**
2. `python -m py_compile <cada arquivo tocado>` → sem erro
3. `py play/guarda.py` → sai 0
4. `git diff --name-only SISB/Core/` → vazio
5. Um relatório no formato definido no doc da etapa

Se qualquer um dos quatro primeiros falhar, a etapa **não** está pronta.

---

## Fora deste mapa — e por quê

**Estas etapas não são tudo que o Playwright pode otimizar.** São a camada
segura: conversões locais, verificáveis, com o teto garantindo que nada piore.

Existe um segundo nível de ganho que exige **reescrever fluxo**, não converter
chamada. Ele fica de fora deliberadamente, porque só faz sentido depois que E10
provar que o motor compensa:

| O que ficaria de fora | Por que não agora |
|---|---|
| Fluxos nativos em `Locator` (P2B, PEC, Mandado reescritos sem a fachada WebDriver) | reescrita grande, apostada em ganho ainda não medido |
| `expect_page` adotado nos ~383 sítios de aba | E3 entrega o helper; a adoção é reescrita de fluxo |
| `api.esperar_resposta` no lugar de adivinhar pelo DOM | idem — E9 entrega o ponto de entrada |
| `get_by_role` / `:has-text` / `filter()` no lugar das cascatas `try css1 / css2 / xpath` | muda a estratégia de seleção, não só a espera |
| `frame_locator` no lugar de `switch_to.frame` | poucos sítios; ganho pequeno |
| `expect_download` / `expect_file_chooser` | nenhum fluxo depende de download hoje (verificado) |
| Paralelismo por `BrowserContext` | mexe em progresso/checkpoint |
| Tracing no tratamento de erro de produção | depende de E10 aprovar o motor |

O critério é o mesmo em todos: **converter é seguro, reescrever é aposta.**
Estas etapas convertem. A aposta espera o número.

### A parte mecânica dessa segunda camada

Nem tudo lá em cima exige julgamento. Três padrões são reconhecíveis por forma,
com antes/depois literais — e foram extraídos para
[`receitas/`](receitas/README.md), num formato que **modelo de contexto pequeno**
(Flash, Mini) consegue executar:

| Receita | Padrão | Sítios | Depende de |
|---|---|---|---|
| R01 | abas por `window_handles` → `abrir_em_nova_aba` | 11 | E3 |
| R02 | `execute_script("arguments[0].click()")` → clique real com fallback | 113 | nada |
| R03 | `session_from_driver` → `cliente_para` | 11 | E9 |

O resto da segunda camada continua exigindo contexto grande.
