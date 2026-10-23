# Projeto de Limpeza e Consolidação — PjePlus (fluxo pw.py)

**Data:** 2026-10-23 · **Status:** PROJETO (apenas análise — nenhum código foi alterado)
**Escopo:** tudo alcançado a partir de `pw.py`, **exceto Triagem/** (fora do escopo; nem é importada — é ancestral morto de `bianca/dom_engine.py`).
**Método:** 2 auditorias independentes (grafo de dependências + diagnóstico de qualidade), medições próprias, referências: [Refactoring.Guru — Duplicate Code](https://refactoring.guru/pt-br/smells/duplicate-code), [Martin Fowler — Strangler Fig](https://martinfowler.com/bliki/StranglerFigApplication.html), princípio Rule of Three (Fowler, *Refactoring*, 2ª ed.).

---

## 1. Sumário executivo

| Métrica | Valor |
|---|---|
| Grafo alcançado de pw.py | **241 arquivos / ~72.000 linhas** (fluxo de negócio sem Triagem: ~57.400 l) |
| God files >600 linhas | **32 arquivos** (≈1/6 do escopo) — topo: `Fix/core.py` 3.739 l |
| Funções >120 linhas | **79** — campeã: `ato_judicial` (532 l) |
| Duplicatas estruturais | **8 clusters grandes + ~40 nomes** definidos em ≥2 módulos |
| `except Exception:` | **761** — **391 engolem em silêncio** (`pass`) |
| Imports tardios dentro de funções | **503 linhas** |
| Código morto no grafo | **~1.772 l** de `.py` sem importador + `.bak/.backup` + 2 monolitos `.md` (4,9 MB) + zip 11,3 MB |
| Imports quebrados (módulos inexistentes) | **~12 referências** silenciadas por try/except |
| Testes | 15 arquivos em `tests/`; **zero cobertura** em `x.py`, `PEC/runtime_pec`, `Prazo/*`, `Fix/utils`, `Fix/extracao` |

**Diagnóstico em uma frase:** o código não está "sujo por falta de padrão" — está **duplicado em camadas paralelas** (4 clientes API, 4 motores de batch, 15 `_executar_js`, 5 `aguardar_e_clicar`, sessão em 2 versões divergentes) e **colado por ciclos** (infra `Fix` importando negócio `PEC/atos/SISB` via lazy). A limpeza certa é **consolidação por clusters + remoção de mortos**, não reescrita.

---

## 2A. Decisões do dono (2026-10-23) — orientam todo o projeto

1. **Critério de canonicidade = execução real no pw.py.** Onde houver par divergente (ex.: sessão Fix.core × Fix.utils), a versão que de fato roda no fluxo pw.py é a fonte da verdade; a outra se ajusta a ela (ou desaparece se não for chamada).
2. **Fim do isolamento de bianca/Andrei.** O objetivo antigo de "bianca/Andrei não dependem de nada fora das suas pastas" foi abandonado. Triagem e Petição **podem importar o núcleo comum** (Fix, api, utilitarios) sem duplicar funções — mantendo apenas o que é exclusivo deles.
3. **API centralizada única para o projeto todo**, com referência em `api/` (`variaveis_client.py`). O que de melhor/diferente existe no `bianca/api_client.py` (ex.: `session_from_driver` variante mais rica) **é trazido para o api/ central**; depois disso `bianca/api_client.py` deixa de ser usado fora de bianca (o uso atual por `Mandado/fluxo_argos.py:115` migra para o api/ central).
4. **Ordem do esforço:** primeiro a limpeza do geral (F0–F9, escopo pw.py), **depois** uma fase de integração que de-duplica triagem/petição/bianca contra o núcleo comum (F10).

---

## 2B. Arquitetura vigente (fonte: `.agents/rules/*`, `idx.md` — lidas 2026-10-23)

Regras **inegociáveis** que o projeto de limpeza deve respeitar (e que corrigem pontos do diagnóstico):

1. **Branch única `main`** — confirmar com `git branch --show-current` (verificado: estamos em `main`).
2. **Playwright é a única via** (`anti-selenium.md`, idx §8-E): proibido introduzir/ manter em arquivos do projeto `import selenium`, `find_element(s)`, `driver.execute_script` solto, `send_keys`, `window_handles`, `WebDriverWait`, `expected_conditions`, tipagem `WebDriver`, `time.sleep`. Espera é sempre condição observável (`espera.ate_*`). JS só dentro de helper nomeado (P5). `compat.py` é ponte para legado não-migrado, não licença.
3. **P9 — interação vem de `Fix.core`, nunca de `Fix.selenium_base`** (cópia congelada que quebra com Playwright).
4. **NUNCA EDITAR shims** (idx §4): `Fix/abas`, `headless_helpers`, `otimizacao_wrapper`, `element_wait`, `smart_finder`, `documents`, `navigation`, `gigs`, `selectors_pje`, `variaveis_client/helpers/resolvers`, `movimento_helpers`, `errors/exceptions`, `log`, `debug_interativo`, `utils_observer/tempo`, `progresso_unificado`, `selenium_base/*`, `drivers/*`, `progress/*`, `scripts/__init__`; e fachadas de atos (`atos/judicial.py`, `atos/movimentos.py`, `atos/regras.py`, `atos/anexos/*`).
5. **NUNCA EDITAR fontes LEGADO** (idx §4): `leg/`, `Mandado/core.py`, `Mandado/processamento.py`, `Prazo/p2b_fluxo_prescricao.py`, `PEC/prescricao.py`, `_archive/`, `LEGADO.md` — referência apenas.
6. **Canônico por idx §0/§4:** Triagem/DOM = `bianca/` (não `Triagem/`); **API = split deliberado**: `Fix/variaveis.py` (helpers + `cliente_para`) **e** `api/variaveis_client.py` (gateway POST/PATCH + paginação) — ambos canônicos, cada um no seu papel.
7. **Ratchet anti-regressão:** `tools/pw_baseline.json` (965 padrões / 50 arquivos) — arquivo listado como migrado não pode regredir; é o gate das fases que tocam interação.
8. **Comparação histórica:** em dúvida/regressão, comparar com `git show 968047a^:<arquivo>` (pré-limpeza); proibido restaurar código automaticamente.
9. **`idx.md` é o filtro de escopo e a referência ÚNICA** (decisão do dono: "a referência deve ser apenas idx.md") — o `idx-core.md`/`.agents` complementam, mas o idx.md **precisa ser atualizado** (muitas coisas mudaram; ex.: tabela §0.5 cita flag `--selenium` que não existe mais no pw.py atual). Atualização do idx.md entra como entregável de cada fase que muda topologia.

**Impacto no diagnóstico:** parte do "código morto" é na verdade **legado protegido** (§4/§5 acima) — a F1 foi reescrita (§7). O "SISB ignora a camada Fix" é uma **violação da arquitetura em migração** (13 arquivos com `By/Keys/WebDriverWait/EC/ActionChains`, 41 `execute_script` diretos, 21 `time.sleep`) — vira fase própria de migração (F11), não limpeza cosmética.

---

## 2. Princípios do projeto (sem estragar)

1. **Zero mudança de comportamento.** Cada fase é movimentação de código, não reescrita. Regra do **Rule of Three**: só extrair utilitário quando ≥3 cópias e comportamento equivalente confirmado.
2. **Strangler Fig, não big-bang** (Fowler): a superfície canônica cresce (api/, Fix/espera, Fix/sessão), e os módulos antigos viram **shims de deprecação** com data — nada é apagado antes de o chamador real migrar.
3. **Fixar contratos antes de cortar:** para cada cluster, definir qual cópia é canônica (§5) e documentar divergências reais — divergência ≠ cópia; onde divergem, primeira ação é decidir qual comportamento é o correto (às vezes é bug de um dos lados, ex. sessão).
4. **Verificação por execução real:** após cada fase, rodar `pw.py` fluxo E (PEC) + conferir `play/medicoes/*.json`, `erro.md` e `logs_execucao/`. É o melhor "teste de caracterização" que existe aqui — e **antes** de fases maiores, criar 3–5 testes de caracterização para o que vai ser tocado (a auditoria mapeou os 15 testes existentes).
5. **1 fase = 1 commit** revertível. Nunca limpar durante uma execução de batch em andamento.
6. **Fora de escopo, não tocado:** `Triagem/`, `f.py`, `limp.py`, `bianca/` (exceto os 2 pontos de acoplamento com o orquestrador, §7-F9), `Andrei/`, `tools/`.

---

## 3. O grafo real (onde a limpeza pode atuar)

- `pw.py` (115 l) → `import x` → `x.py` (1.154 l, hub) → `FLOW_HANDLERS`: Mandado (`Mandado/entrada_api`), Prazo+P2B (`Prazo/loop_orquestrador`, `p2b_gateway`), PEC (`PEC/orquestrador` shim 2 l → `runtime_pec`), Petição (`Peticao/runtime_pet`), Citação (**inline em x.py:628-708**), Domicílio+Triagem (`bianca/` — acoplamento à parte).
- **O shim do Playwright** (`pjeplay.iniciar` → `compat.instalar`) registra módulos "selenium" falsos e **sobrescreve as fábricas de driver** em `Fix.driver_factory/core/facade_publica/drivers` — por isso nenhum import de `Fix/*` pode preceder `pjeplay.iniciar()`. **Consequência:** `from Fix import espera` (em ~60 arquivos) carrega `Fix/__init__ → facade_publica → core+extracao+utils+abas+monitoramento` — **tocar no Fix puxa ~9 mil linhas**. Qualquer consolidação precisa manter o shim funcionando.
- **Ciclos de camada (achado estrutural nº1):** `Fix.extracao` importa `atos.core` no topo; `Fix.core` importa `SISB.utils` (lazy); `Fix.utils` importa `PEC.anexos` (lazy, 6×). Infra depende de negócio — a direção correta (negócio→infra) está toda em lazy, sinal de refactors inacabados.
- **Identidade dupla pjeplay:** `pjeplay.locators` (via `PLAY/` no sys.path) e `Play.pjeplay.locators` (via RAIZ/) são **sys.modules separados — o mesmo código é carregado 2×** (Fix/core.py:9 vs Play/pjeplay/__init__.py:23-38). Estado por-cópia (`compat._INSTALADO`) pode divergir.

---

## 4. Os 8 clusters de duplicação (o coração da limpeza)

| # | Cluster | Cópias | Canônica | Ação |
|---|---|---|---|---|
| A | **PjeApiClient** | 4 (`api/variaveis_client`, `bianca/api_client` 951-1.107 l, `Fix/variaveis.py:101`, `Peticao/api/client`) + 3 shims | `api/variaveis_client.py` (re-exportada por `Fix/facade_publica.py:169`) | Converter `Fix/variaveis.py` (1.495 l, monólito paralelo **divergente**) e as demais em shims; ~2.200 l fazendo o mesmo trabalho |
| B | **Motores de batch** | 4 protocolos `should_skip/open_item/execute_item/persist_result` inline + `run_batch`/`resultado_ok`/`resultado_falha` copiados byte-a-byte em `bianca/utils.py` | `utilitarios_processamento.py` (já usado por PEC/Mandado/Prazo/Peticao) | Migrar os 4 para o `run_batch` central |
| C | **criar_gigs** | 3 + 1 stub perigoso | `Fix/extracao.py:1088` (139 l) | Apagar **stub de `Peticao/core/extracao/extracao.py:295` (retorna True sem fazer nada!)**; `Andrei/` é cópia antiga fora do grafo |
| D | **Extração** | `extrair_dados_processo` ×2 (183 vs 187 l — quase cópia total), `extrair_direto` ×2, `criar_comentario` ×2, `criar_lembrete_posit` ×2 | `Fix/extracao.py` | Manter Fix, apagar copião de `Peticao/core/extracao` (mesmo pacote do stub) |
| E | **`_executar_js`** | **15 cópias** (~6 l, com fallback Playwright em algumas e não em outras) | escolher 1 (Fix/core ou Fix/espera) com fallback Playwright definido 1× | Substituir as 15 por 1 import |
| F | **`_norm`** | **11 cópias** (6 dentro do próprio `Mandado/apoio_fluxos.py`) | 1 utilitário (`Fix/utils.remover_acentos`/normalizar já existe) | Import único |
| G | **Primitivas de navegador** | `aguardar_e_clicar` ×5 (2 DENTRO do próprio Fix, assinaturas diferentes!), `esperar_elemento` ×4, `preencher_campo` ×3, `safe_click` ×4, `aguardar_renderizacao_nativa` ×3 | `Fix/core.py` | Unificar no Fix/core; SISB decide aderir ou manter núcleo próprio (decisão explícita) |
| H | **Sessão/cookies** | `salvar_cookies_sessao`, `carregar_cookies_sessao`, `verificar_e_aplicar_cookies`, `js_base`, `aguardar_e_clicar` — **pares DIVERGENTES Fix.core × Fix.utils** | **decidir** (risco real: `x.py` usa utils, resto usa core) | Unificar num módulo de sessão único — **fase mais sensível, fazer com teste de caracterização** |

Clusters menores: `gerar_regex_geral` ×2 (variantes), meses-por-extenso em **9+ lugares** (2 parses de data **no mesmo pacote PEC** com comportamento diferente: `carta_ecarta_api._parse_data` aceita "07 de julho de 2026"; `runtime_pec._parse_data_ecarta` não), `log` ×18 (closures em atos/*).

---

## 5. God files — plano de decomposição por responsabilidade

| Arquivo | Linhas | Como está | Decompor em |
|---|---|---|---|
| `Fix/core.py` | 3.739 | ≥6 responsabilidades + re-export de drivers + **função morta por shadowing** (`buscar_documentos_polo_ativo` 2×: 3202 morta, 3382 vence) | `fix/espera.py` (waits), `fix/entrada.py` (clique/seleção/preenchimento), `fix/sessao.py` (cookies/credencial), `fix/documentos.py` (checagens DOM/API), `fix/drivers.py` (fachada pjeplay) |
| `SISB/core.py` | 2.430 | auth + navegação + minutas + orquestração; `minuta_bloqueio` × `minuta_bloqueio_amanha` duplicam lógica (amanha = 440 l) | `sisb/auth.py`, `sisb/minutas.py` (1 função parametrizada), `sisb/ordens.py` — **decidir antigo×novo** (§6-J) |
| `Fix/extracao.py` | 2.375 | extração + GIGS/lembretes + BNDT inteiro (1351-1930) + indexação | `fix/gigs.py`, `fix/bndt.py`, `fix/extracao.py` (só extração) |
| `Fix/utils.py` | 2.318 | 2ª "core" paralela: logins, editor, recovery, cookies **divergentes**, `inserir_html_editor` 2× (1202 morta) | fundir com core por tema; apagar 1ª `inserir_html_editor` |
| `x.py` | 1.154 | menu + logging (847-948) + driver + 9 fluxos + **Citação inteira inline (628-708)** | `orquestrador/log.py`, `fluxos/citacao.py`, `x.py` só menu/loop |
| `PEC/runtime_pec.py` | 1.035 | API + formato eCarta + prazos + GIGS + orquestrador | `pec/api.py`, `pec/carta_formato.py`, `pec/prazos.py`, `pec/orquestrador.py` |
| `Fix/variaveis.py` | 1.495 | monólito paralelo do api/ (§4-A) | shim de deprecação → `api/` |

---

## 6. Código morto / lixo (remoção de baixo risco — ganho imediato)

1. **Módulos `.py` sem importador no grafo (~1.772 l):** `Mandado/core.py` (269), `Mandado/processamento.py` (36, quebrado), `Peticao/regras.py`, `Peticao/Despachos/wrappers.py`, `Peticao/consolida_delete.py`, `Peticao/testpet.py` (script manual), `Peticao/api/examples/`, `PEC/c_ord.py`, `PEC/anexos/anexos_juntador.py`, `PEC/regras_idpj_timeline.py`, `atos/anexos/*` (149 l — espelho morto de PEC.anexos), `api/variaveis.py`, **13 shims do Fix sem nenhum importador** (gigs, documents, element_wait, exceptions, navigation, progresso_unificado, smart_finder, variaveis_client/helpers/resolvers, progress/*, selenium_base/*), `bianca/main.py`, `bianca/mov_int.py`.
2. **Backups/lixo versionado:** `atos/judicial_fluxo.py.bak`, `PEC/anexos/core.py.backup_final`, `Script/*.bak`, `backup_aud_pre_merge/`, `git_backup_pre_filter.zip` (11,3 MB), `bianca/progresso_triagem_backup_*.json` (~45 arquivos), `Peticao|SISB|Prazo/dadosatuais.json`, `*/progresso*.json` commitados **apesar do .gitignore** (precisam `git rm --cached`). `__pycache__`/`.pytest_cache` no disco.
3. **Referências a módulos inexistentes (decidir: morto ou perdido):** `Fix.debug_assinatura`/`Fix.assinatura_cookies` (atos/comunicacao_finalizacao.py:766+), `bacen`/`driver_config` (SISB/Core/sessao_helpers.py:46,56), `selector_learning` (Fix/browser_suporte.py:556 — existe só em `tools/`, fora do sys.path), `PEC.sisbajud_driver` (PEC/regras.py:29), `Mandado.processamento_argos/outros`, `Peticao.atos.wrappers` (helpers.py:359+ — **5 try/except que sempre falham**), `SISB.navegacao` (ordens_execucao.py:265,280 — provavelmente queria `SISB.processamento.navegacao`).
4. **Shims vivos → deprecação com data** (não apagar ainda): ~16 shims do Fix re-exportando facade_publica/core/extracao + shims de 1-4 l do PEC + camada dupla do SISB (`processamento_*.py` planos vs `processamento/`).

---

## 7. Fases (ordem de risco crescente — cada fase é um commit verificável)

| Fase | Conteúdo | Risco | Ganho estimado |
|---|---|---|---|
| **F0 — Segurança & higiene** | Remover **credencial hardcoded** (`PEC/carta_ecarta_api.py:107` → keyring/variável); `git rm --cached` de dados/backups; `.gitignore` cobrir `progresso*.json`, `dadosatuais.json`, `*.bak`; requirements curado (pytesseract/pillow fora do fluxo); deletar `.bak/.zip/backups` | **Zero** | Repo limpo, segredo fora |
| **F1 — Mortos (revisado pela arquitetura + motor próprio)** | Critério definitivo (correção do dono, 2026-10-23): **alcançável do pw.py OU pertencente a motor próprio executado isoladamente** (Peticao e bianca/triagem rodam sem pw.py e continuam vivos, usando a estrutura geral) + lista de proteção do idx §4. **Executado:** removidos `PEC/c_ord.py`, `PEC/anexos/anexos_juntador.py`, `PEC/regras_idpj_timeline.py` (regra preservada em HISTORICO_LEGADO §4), `LEGADO.md` (→ HISTORICO_LEGADO.md) e untracking de JSONs de runtime. **Restaurados após correção do critério:** `Peticao/regras.py`, `Peticao/Despachos/wrappers.py`, `bianca/mov_int.py` (shims do motor). **Resolvidos sem remoção:** `bianca/main.py` (runner do motor bianca — mantido). **Pendentes de decisão:** `Peticao/testpet.py` (playground não versionado), `Peticao/consolida_delete.py`, `Peticao/api/examples/`, `api/variaveis.py` (F10). Imports fantasma (`bacen`, `driver_config`, `Fix.debug_assinatura`...) → logar explicitamente, não apagar às cegas | Baixo (com a checagem) | −~500 l reais + repo limpo, menos falsos caminhos |
| **F2 — Utilitários triviais** | **✅ EXECUTADA (2026-10-23):** `_executar_js` → 1 canônica (`Fix/core.py:2629`, fallback `page.evaluate`); 14 cópias trocadas por `from Fix.core import _executar_js` (13 via codemod + `bianca/atos_utils.py` manual, que tem imports tardios quebrando ciclo). `_norm` → 1 canônica module-level em `Fix/core.py:2624` (NFD→ascii, com guard `(t or '')`); 7 cópias removidas (apoio_fluxos ×6 + nested Fix/core). **NÃO fundidas de propósito:** `Fix/utils.py:1285` `_norm` (\W+ squash p/ nº de processo — semântica própria) e `_norm` ×3 de bianca (NFKD/strip/categoria — motor próprio, dedup na F10). **NÃO fundir com `normalizar_texto` (Fix/utils:40)**: ela usa filtro por categoria e PRESERVA chars sem decomposição (`º`, `ª`, `ß`), enquanto a família `_norm` descarta via ascii-ignore ("12º" → "12") — mudaria matching de regras. Shadowed mortas removidas: `Fix/core.py` `buscar_documentos_polo_ativo` 1ª def (92 l; vence a de polo/limite_dias) e `Fix/utils.py` `inserir_html_editor` 1ª def (59 l). Verificação: py_compile 17/17, import dos 17 módulos OK, ratchet aprovado. Net: +20/−342 | Baixo-médio | −322 l, 1 comportamento de JS, 1 normalizador |
| **F3 — Sessão única** | **✅ EXECUTADA (2026-10-23):** criado **`Fix/sessao.py`** (643 l) — cluster canônico de sessão/login/cookies com os corpos **executados**, movidos **verbatim** de `Fix/utils.py` (12/12 corpos provados idênticos a `HEAD:Fix/utils.py` por hash AST): `obter_credencial`, `login_manual`, `login_automatico`, `login_automatico_direto`, `sessao_oauth_completa`, `_is_driver_headless`, `_obter_caminhos_ahk`, `login_cpf`, `login_pc`, `USAR/SALVAR_COOKIES_AUTOMATICO`, `salvar_cookies_sessao`, `carregar_cookies_sessao`, `verificar_e_aplicar_cookies`. `Fix/utils.py` re-exporta (importadores x.py/f.py/Triagem/Peticao/SISB/atos/tools intocados); `Fix/facade_publica.py` repontuado (trio de cookies saiu do `.core`). **Cluster divergente de `Fix/core.py` removido** (−307 l: `_extrair_jwt_exp`, `salvar/credencial/carregar/verificar` próprios do core — zero chamadores, provado por grep+AST; os nomes já eram sombreados pela via utils). Ciclo core↔utils (`core:1893`) preservado como está; `sessao` não importa utils (sem ciclo novo). Verificação: py_compile 4/4, identidades `utils.login_cpf is sessao.login_cpf`, `core.login_func is sessao.login_cpf`, `facade.salvar_cookies is sessao.salvar_cookies`, ordem utils-first OK, consumidores x/f/SISB/atos/Peticao/bianca/Triagem importam OK, ratchet OK. Net: −298 l. **Pendente:** teste de login/cookies ao vivo nos 2 fluxos (com o dono, na próxima rodagem real) | **Médio-alto** (comportamental) | Sessão em 1 lugar; fim do fork silencioso core×utils |
| **F4 — API consolidada (corrigido pelo idx §4 + decisão do dono)** | **✅ EXECUTADA (2026-10-23):** **descoberta-chave — a absorção já existia**: `Fix/variaveis.py` já abriga os helpers do cliente bianca (`obter_gigs_com_fase:366` — divergência só cosmética/acento, lógica idêntica provada por diff; `obter_texto_documento`, `padrao_liq`, `verificar_bndt`, `buscar_atividade_gigs_por_observacao`, `obter_todas_atividades_gigs_com_observacao`) + `cliente_para:518` (entrada canônica: Playwright via APIRequestContext, senão requests). **Migrações fora de bianca:** `Mandado/fluxo_argos.py` ETAPA 1.6 → `cliente_para(driver)` + `obter_gigs_com_fase` de `Fix.variaveis` (fim da dependência bianca); `f.py` tdbg → par canônico `api.variaveis_client`; `Peticao/api/client.py` (cópia de 211 l, **zero importadores**) → delegado de 9 l para `api.variaveis_client`. **Diferença de valor absorvida:** `session_from_driver` dos 2 canônicos (api + Fix.variaveis) agora injeta **X-XSRF-TOKEN** (unquote do cookie, evita 403 CSRF em POST/PATCH) e **User-Agent real do driver** (evita WAF) — aditivo, fallback defensivo, guard de host SSO mantido; testado com mock (XSRF decodado, UA aplicado, grau 1). **Mapeado e NÃO feito (F7/F10):** 20 métodos compartilhados bianca↔api divergentes (fork completo; merge exige rodagem real); `Fix/variaveis.py` tem um 3º `PjeApiClient` read-only (14 métodos, 12 idênticos, falta POST/PATCH, tem `obrigacoes_pagar`) e o próprio `session_from_driver` duplicado — dedup na F7; bianca/api_client fica restrito à triagem (dom_engine, coleta, citacao) até F10. Verificação: py_compile 5/5, mock test, fachada e delegação idênticas, ratchet OK | Médio | Consumidores fora de bianca no par canônico; sessão endurecida |
| **F5 — GIGS + extração** | **✅ EXECUTADA (2026-10-23):** stub `criar_gigs` do Peticao **removido** (sempre devolvia True sem criar nada; −16 l) + cópia de `extrair_dados_processo` do Peticao/core/extracao removida (−187 l, sem chamadores) — `Peticao/core/extracao/__init__.py` re-exporta os 2 do `Fix.extracao` (compat com `runtime_pet:41`/`regras_execucao:19`). **Bug latente corrigido:** `Mandado/fluxo_ui.py` importava o stub mas chamava com kwargs da assinatura REAL (`dias_uteis=`, `log=`) → TypeError quando alcançado; repontuado para `Fix.extracao`. **Lazy → topo:** 14 imports `from Fix.extracao` dentro de função viraram import de topo (PEC/runtime_pec ×2, regras_execucao ×5 — já cobertos pelo top, Triagem/dom, PEC/core_pos_carta ×2, Mandado/apoio_fluxos ×3, fluxo_argos, SISB/core ×6 linhas, SISB/batch ×3); `Prazo/p2b_fluxo_lazy.py` intocado (LEGADO, lazy é o propósito). **Canônicos confirmados únicos no grafo:** `Fix/extracao.py` `criar_gigs:1088` e `extrair_dados_processo:233`; cópias de bianca/Andrei → F10. **Restante lazy (mesmo padrão, não-criar_gigs):** extrair_dados_processo ×~10 (SISB/Core/sessao_helpers, PEC/carta_execucao:316, Prazo/*), abrir_detalhes/bndt — varredura futura. Verificação: py_compile 11/11, import 11/11, re-export idêntico, ratchet OK. Net: −237 l | Baixo | GIGs reais em todos os caminhos; 1 definição no grafo |
| **F6 — Batch único** | **✅ EXECUTADA (2026-10-23):** o stated-goal (p2b + Mandado no `run_batch` central) **já estava cumprido** — snapshot da auditoria era anterior: `Prazo/p2b_gateway:847`, `Mandado/entrada_api:65`, `PEC/runtime_pec:29`, `Triagem/runtime_triagem:36` e `bianca/triagem/runner:33` já chamavam `utilitarios_processamento.run_batch`. **Entregue nesta fase:** aposentada a cópia de `bianca/utils.py` (−183 l: `run_batch`/`_safe_persist`/`resultado_ok`/`resultado_falha` + aliases) — `bianca/triagem/runner.py` repontuado ao canônico com adaptação mecânica (protocolo difere: bianca passava contexto `execute_item(item, open_result)` — arg nunca usado, removido; `label=` não existe no canônico, removido). **Bug latente da cópia corrigido de quebra:** o engine do bianca checava `exec_result.get("critical")` no topo (nunca dispara com `resultado_falha(critical=True)`, que aninha em `dados`) — o canônico checa `dados.critical` → o stop-on-critical do runner de triagem passa a funcionar de fato. Restam cópias fora de escopo: `SISB/batch.py processar_lote_sisbajud` (F11), `Andrei/pipeline.py` (F10), `bianca/utils.RuleRegistry` (órfão, F10). Verificação: py_compile, import, ratchet OK | Médio | 1 motor de lote no grafo; crítico funcional na triagem |
| **F7 — Decomposição de god files** | §5 (core, extracao, utils, x.py, runtime_pec, SISB antigo×novo) — um arquivo por commit | Alto (volume) | Manutenibilidade |
| **F8 — Observabilidade** | **✅ PARCIAL (2026-10-23) — causa-raiz do log duplicado resolvida:** política única `handler_console_sem_pjeplus(handler)` em `Fix/diagnostico_runtime.py` (o logger `'pjeplus'` mantém handler próprio de console; handlers de console da raiz criados pelos orquestradores registram o filtro e não reimprimem a família `pjeplus`; **file log e erro.md continuam recebendo via propagate** — `propagate=False` ingênuo os quebraria). Aplicado em `x.py` (configurar_logging), `f.py` (harness) e `Peticao/suporte_pet.py` (import local). Prova empírica: sem filtro 2 linhas / com filtro 1 linha; outros loggers intactos. `bianca/main.py` usa logger nomeado (não duplica), `tools/monitor.py` captura pjeplus de propósito, `SISB/facades_contratos` ('SISBAJUD') tem o mesmo padrão → F11. **Pendente (F8b):** extinguir prints de módulos de fluxo (307 hoje: bianca 124 → F10, Fix 85, raiz 62, Script 23, SISB 10, Peticao 3) e retorno padronizado de fluxo (fim do `normalizar_resultado` de x.py) | Baixo | Log limpo, erro.md confiável |
| **F9 — Camadas & identidade dupla** | Quebrar ciclos Fix→negócio (mover dependência para o negócio); resolver `pjeplay` vs `Play.pjeplay` duplicados no sys.modules; boundary Orquestrador↔Triagem (x.py:52,552) | Alto (arquitetural) | Import previsível, ~9k linhas de Fix carregando 1× |
| **F10 — Integração triagem/petição/bianca** | **Fase nova (decisão do dono — pós-limpeza geral):** com o fim do isolamento, `bianca/` e `Peticao/` passam a importar o núcleo comum: apagar `bianca/extracao.py` (criar_gigs/comentário/lembrete → Fix), `bianca/utils.py` (run_batch/resultado_ok ≡ utilitarios), `Peticao/core/extracao/` (stub + copiões → Fix), 6 cópias de `_norm` do apoio_fluxos se ainda restarem; manter só as exclusivas (regras B1-B14, buckets, motor dom). Andrei/ (fora do grafo, cheio de selenium real) vira candidato a arquivo morto | Médio (depois do geral) | −~1.500 l, triagem/petição sem cópias paralelas |
| **F11 — Migração anti-selenium (SISB)** | **ADIADA por decisão do dono (2026-10-23):** SISB com Selenium é aceitável por enquanto (nada migrado lá ainda; "não precisa ser mexido agora"). Fica registrada como trabalho futuro, com o gate do ratchet (`tools/pw_baseline.json`) e método por arquivo quando retomada | — | — |

**Ordem sugerida de execução:** F0 ✅ → F1 → F2 → F8 (rápidas e independentes) → F3 → F5 → F4 → F6 → F7 → F9 → **F10 → F11** (fases novas, por decisão do dono e arquitetura vigente).

---

## 8. Verificação por fase (o "não estragar" na prática)

1. **Antes:** `py -m py_compile` nos arquivos tocados + testes de caracterização existentes (`tests/`, 15 arquivos) + criar 3-5 novos para o módulo tocado (padrão já existe: `test_pec_carta_notificacao`, `test_sisbajud_autenticacao`, `test_caracterizacao_regras`).
2. **Execução:** rodar `pw.py` fluxo **E (PEC)** ponta a ponta; conferir `play/medicoes/*.json` (sem queda vs. baseline), `erro.md` (sem erros novos) e o `progresso.json`.
3. **Depois:** commit único da fase com mensagem `limpeza(Fn): <o que>`; se algo regredir, revert e anotação no doc.
4. **Nunca** limpar com batch rodando; nunca apagar shim que ainda tem importador vivo (checar no grafo).

## 9. Métricas de sucesso

- Linhas no grafo: 72.000 → meta < 60.000 sem perda de função (F1-F6 entregam ~6-8k).
- 15 `_executar_js` → 1; 11 `_norm` → 1; 4 `PjeApiClient` → 1+2 shims; 4 motores de batch → 1; sessão 2× → 1.
- `except Exception: pass` 391 → < 50 (com log ou exceção real).
- Cobertura de testes de caracterização: 15 arquivos → cobrir `x.py`, `PEC/runtime_pec`, `Fix/utils`, `Fix/extracao`, `Prazo`.
- Import de `Fix` carregando ~9k linhas → reduzido pela quebra de ciclos (F9).

## 10. Anexos — evidências por arquivo

Os relatórios completos das duas auditorias (com todas as evidências `arquivo:linha`) estão nas mensagens da sessão: (a) diagnóstico de qualidade — god files top-10 dissecados, 79 funções longas, contagens de padrões, higiene; (b) grafo de dependências — tabela por pacote, top-25 (46% do grafo), clusters A-J, inventário de mortos e referências quebradas.

> **Nota de pesquisa:** o endpoint de web *search* do plugin está sem saldo (erro 402). As referências foram obtidas por fetch direto (Refactoring.Guru/Duplicate Code, Fowler/Strangler Fig) e conhecimento consolidado (Rule of Three, Feathers/Working Effectively with Legacy Code para testes de caracterização).
