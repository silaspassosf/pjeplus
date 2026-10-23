# Histórico do Legado — PjePlus (registro de conhecimento)

**Data:** 2026-10-23 · **Origem da decisão:** dono do projeto — "o projeto atual é maduro o suficiente para não precisar mais do LEGADO.md". O conhecimento relevante foi destilado aqui; o arquivo original (2.193 KB) foi removido do repositório.

---

## 1. O que era o LEGADO.md

Snapshot **integral do monólito pré-modularização** ("Legado Funcional — Código Fonte Completo"), com **831 seções** organizadas por arquivo de origem (`ref/atos/__init__.py`, `ref/atos/comunicacao.py`, `ref/atos/core.py`, `ref/atos/judicial.py`, `ref/atos/movimentos.py`, `ref/atos/wrappers_ato.py`, `ref/atos/wrappers_mov.py`, …). Servia como referência de comportamento original durante a migração para a estrutura atual.

**Como recuperar (nada se perdeu de fato):**
```bash
git log --oneline --all -- LEGADO.md     # revisões em que existiu
git show <revisão>:LEGADO.md             # conteúdo integral de qualquer ponto
```
Complementos que continuam no disco: `_archive/` (código removido por data), `leg/` (snapshots pré-xcode), `TRADUCAO_MONOLITO_GIGS.md` (mapa do monólito GIGS → módulos atuais), `968047a^` via `git show` (estado pré-limpeza, regra `comparacao-historica`).

---

## 2. Mapa de migração (monólito → projeto atual)

| Monólito / ref | Onde vive hoje |
|---|---|
| `Fix.py` (monólito de ações) | `Fix/core.py` (cliques/esperas/preenchimento), `Fix/utils.py` (login/cookies/texto), `Fix/extracao.py` (extração/GIGS/BNDT), `Fix/browser_suporte.py` |
| Cliente API + resolvers | `Fix/variaveis.py` (helpers + `cliente_para`) **+** `api/variaveis_client.py` (gateway POST/PATCH/paginação) — split deliberado (idx §4) |
| `ref/atos/judicial.py` + helpers | `atos/judicial_fluxo.py`, `atos/judicial_helpers.py`, `atos/judicial.py` |
| `ref/atos/wrappers_ato.py` | `atos/wrappers_ato.py` (inclui `ato_edidpj`, `ato_ed`, `ato_ceju`, `ato_respcalc`, …) |
| `ref/atos/movimentos.py` | `atos/movimentos_fluxo.py`, `atos/movimentos.py` |
| `ref/atos/comunicacao.py` | `atos/comunicacao.py` + `atos/wrappers_pec.py` (`pec_ord`, `pec_sum`, `pec_editalidpj`, …) |
| GIGS do `gigs-plugin.js` | `Fix/extracao.py` (`criar_gigs` canônico) — tradução em `TRADUCAO_MONOLITO_GIGS.md` |
| Função IDPJ ("instaurado em face") | `atos/judicial_helpers.py::idpj` → `ato_bloq`/`ato_meios` + `atos/wrappers_ato.py::ato_idpj` |

---

## 3. Conhecimento essencial que sobrevive em outros lugares

- **`idx.md`** — referência única e viva do projeto (topologia, shims, API de interação, P1–P9). Regra do dono (2026-10-23): *a referência deve ser apenas idx.md*, que segue em atualização.
- **`.agents/rules/anti-selenium.md`** — Playwright é a única via; lista de proibições; ratchet `tools/pw_baseline.json`.
- **`.agents/rules/comparacao-historica.md`** — diagnóstico comparativo com `git show 968047a^:<arquivo>` (sem restauração automática).
- **`docs/PROJETO_LIMPEZA_PJEPLUS.md`** — projeto de limpeza/consolidação (fases F0–F11), com as decisões do dono registradas.

---

## 4. Registro das remoções da F1 (2026-10-23)

> **Critério corrigido no mesmo dia:** a F1 inicial usou só "alcançável a partir do pw.py" como teste de vida. O dono corrigiu: **Petição (e bianca/triagem) têm motor próprio, executados isoladamente mesmo sem fluxo no pw.py** — usam a estrutura geral, mas continuam vivos. Critério definitivo: **alcançável do pw.py OU pertencente a motor próprio ativo (Peticao, bianca)**. Com isso, `Peticao/regras.py`, `Peticao/Despachos/wrappers.py` e `bianca/mov_int.py` foram **restaurados** (shims de compatibilidade do motor, recuperados de HEAD antes do commit) e `bianca/main.py` (runner do motor bianca) fica **mantido por princípio**.

Arquivos mortos removidos (todos versionados → recuperáveis via `git show <rev>:<caminho>`):

| Arquivo | Nota |
|---|---|
| `PEC/c_ord.py` (24 l) | `mov_int` do fluxo "c.ord" — homônimos locais não o importam; fluxo interno do pw.py (PEC), confirmado morto |
| `PEC/anexos/anexos_juntador.py` (23 l) | re-export órfão de `anexos_juntador_base` |
| `PEC/regras_idpj_timeline.py` (114 l) | **regra preservada abaixo** |

JSONs de estado de runtime (`Peticao/dadosatuais.json`, `progresso*.json`, `SISB/dadosatuais.json`, `bianca/progresso_triagem*.json`) deixaram de ser versionados (untracking), mas **permanecem em disco** — são consumidos/gerados pelos motores em execução (ex.: `extrair_dados_processo` grava `dadosatuais.json`, SISB o lê) e já estão no `.gitignore`.

**Regra preservada de `regras_idpj_timeline.py`** (verificação de timeline após sentença IDPJ, via API REST):
> Há mandado **e** edital na timeline pós-IDPJ?
> - Não → não executa nada (False)
> - Sim, tudo em **apenas uma data** → não executa (False)
> - Sim, em **pelo menos 2 datas** (só mandado em várias datas, ou só edital em várias datas — nunca ambos) → **executa** (True)

**Ficaram pendentes de decisão do dono (não removidos):** `Peticao/testpet.py` (playground manual, não versionado), `Peticao/consolida_delete.py` (citado só em docstring), `api/variaveis.py` (só a cópia morta `Triagem/` importa — decidir na F10). `bianca/main.py` foi resolvido: **mantido** (runner do motor bianca, executado isolado).

> **LEGADO.md (2.193 KB):** removido nesta mesma data; conteúdo recuperável por git (comando na §1).
