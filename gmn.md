# GMN — Guia de Mapeamento de Agentes (estrutura real do pjeplus)

Compilado em: 2026-09-18
Objetivo: mostrar a estrutura REAL de arquivos de agentes/regras criados para o Antigravity,
para revisão. Tudo abaixo foi verificado em disco neste momento.

---

## 1. Estrutura de arquivos (real, verificada)

```
pjeplus/
├── gmn.md                                        ← este arquivo (compilador/revisor)
├── idx.md                                        ← índice completo (48 KB, na raiz, como hoje)
├── CLAUDE.md                                     ← orquestração estilo Paperclip (desenvolvimento)
│
├── .agents/
│   └── rules/                                    ← regras "always on" (carregadas em toda sessão)
│       ├── idx-core.md                           ← núcleo do idx.md (Quick Reference + Árvore de Decisão)
│       ├── GEMINI.md                             ← ponte de contexto para o Gemini CLI/Antigravity
│       └── agents/                               ← agentes especializados (invocados sob demanda)
│           ├── pjeplus-analyst/
│           │   └── agent.md                      ← ex-"Analise.md" (análise + geração de patch pjeplus:apply)
│           ├── pjeplus-debug/
│           │   └── agent.md                      ← ex-"Bug.md" (diagnóstico cross-module leve → 00act.md)
│           ├── pjeplus-surgical/
│           │   └── agent.md                      ← ex-"PJE.md" (aplicação cirúrgica de patch mínimo)
│           └── pjeplus-script/
│               └── agent.md                      ← ex-"Java.md" (especialista exclusivo em Script/)
│
├── Play/pjeplay/                                 ← backend Playwright (shim de selenium.*)
│   ├── __init__.py  compat.py  driver.py  element.py  errors.py
│   ├── launcher.py  locators.py  medicao.py  nativo.py  pje.py
│   ├── script.py  waits.py  api.py  actions.py
│   └── __pycache__/
│
├── Script/                                       ← escopo exclusivo do pjeplus-script
│   ├── pjetools.user.js                          ← orquestrador Tampermonkey
│   ├── hcalc.user.js                             ← calculadora hcalc (versões ?v=NNN)
│   ├── SCRIPT_README.md                          ← bíblia do pjeplus-script (leitura obrigatória)
│   └── autoactions/  calc/  alvara/  lista/ ...
│
└── (demais módulos de negócio — ver idx.md: Mandado/, PEC/, Prazo/, SISB/, atos/, Fix/, bianca/)
```

Nota: os agentes ficam em `.agents/rules/agents/` (e não `.agents/agents/`) — caminho real
no disco, já operacional no workspace.

---

## 2. Índice dos agentes — o que cada um faz

| Agente (arquivo) | Papel | Modelo (frontmatter) | Ferramentas declaradas | Tamanho |
|---|---|---|---|---|
| `.agents/rules/agents/pjeplus-analyst/agent.md` | Análise e geração de patches: recebe pedido em português livre → devolve bloco `<!-- pjeplus:apply -->` completo. Fluxo de análise obrigatório, gate de clarificação, MESA (execução sequencial autônoma), padrões inegociáveis (SmartFinder, waits, exceções tipadas, dataclass). | `claude-sonnet-4-6` | edit/editFiles, execute/runInTerminal, search, execute/getTerminalOutput, search/usages, read/file | 19.976 B |
| `.agents/rules/agents/pjeplus-debug/agent.md` | Diagnóstico cirúrgico leve: lê e mapeia cross-module (máx. 2 níveis), produz diagnóstico + correção pontual **sem editar**. Resposta final curta (Diagnóstico + Correção). | `raptor-mini` | search, search/usages, read/file, edit/editFiles, execute/runInTerminal, execute/getTerminalOutput | 4.369 B |
| `.agents/rules/agents/pjeplus-surgical/agent.md` | Aplicação cirúrgica: recebe o `pjeplus:apply` como lei, patch mínimo (âncora + bloco), `<reasoning>` antes de agir, silêncio pós-edição ("Edição aplicada."), política de reversão com bloco de erro, DAP para ações destrutivas. | `raptor-mini` | edit/editFiles, execute/runInTerminal, search, execute/getTerminalOutput, search/usages, read/file | 9.937 B |
| `.agents/rules/agents/pjeplus-script/agent.md` | Especialista exclusivo em `Script/`: Tampermonkey, console, bookmarklets. Leitura obrigatória de `Script/SCRIPT_README.md`, **deploy obrigatório** (bump de `@version` + commit/push imediato, nunca `git add -A`), ESLint rápido, checklist de reaproveitamento de APIs (`PjeExtrair`, `PjeLibParser`, `CleanupRegistry`…). | `claude-sonnet-4-6` | read/file, search, search/usages, edit/editFiles, execute/runInTerminal | 8.844 B |

Fluxo de trabalho entre eles (como hoje no Copilot):

```
pedido em português
   │
   ├─ pjeplus-debug     → mapeia/diagnostica (sem editar) → diagnóstico + correção pontual
   ├─ pjeplus-analyst   → gera bloco <!-- pjeplus:apply --> completo
   ├─ pjeplus-surgical  → aplica o patch cirúrgico a partir do bloco
   └─ pjeplus-script    → tudo que é JS/Tampermonkey dentro de Script/ (bypass do ciclo acima)
```

---

## 3. Regras "always on" (carregadas automaticamente)

### `.agents/rules/idx-core.md` (7.640 B)

Núcleo condensado do `idx.md`, para não estourar o limite de tamanho por regra
(o idx.md completo tem ~48 KB). Contém:

- **Quick Reference Card** — tabelas diretas tarefa→arquivo→função:
  Executor & Motor (`pw.py`/`x.py`), Driver/Sessão/DOM, API REST/Extração/Negócio,
  Entry Points de Negócio (Mandado, Prazo, P2B, PEC, Triagem, Petição, SISBAJUD, DOM),
  Atos Judiciais & Scripts JS.
- **Árvore de Decisão de Escopo** (Q1–Q13) — roteamento rápido para o arquivo exato.
- **Regras críticas sempre aplicáveis**: P9 (imports de interação só de `Fix.core` — nunca
  `Fix.selenium_base`), nunca editar SHIMs, nunca editar LEGADO, diretórios canônicos
  (`bianca/` vs `Triagem/`), proibição de `WebDriverWait`/`time.sleep`/`.click()` direto.
- Diretriz final: o core é o filtro primário; sob demanda ler `@idx.md` completo.

### `.agents/rules/GEMINI.md` (1.071 B)

Ponte de contexto do workspace: orienta o Gemini CLI/Antigravity a
1. ler `./idx.md` para contexto arquitetural completo;
2. reconhecer que as regras em `.agents/rules/` são carregadas automaticamente;
3. conhecer os 4 agentes de `.agents/agents/` (lista com papéis resumidos);
4. consultar `idx-core.md` antes de qualquer busca exploratória fora do escopo mapeado.

---

## 4. Pontos de atenção na revisão

1. **Modelos no frontmatter**: `claude-sonnet-4-6` e `raptor-mini` são nomes do Copilot
   Marketplace. No Antigravity, trocar para `gemini-3-pro` (analyst/script) e
   `gemini-3-flash` (debug/surgical), conforme a equivalência custo/capacidade.
2. **Ferramentas no frontmatter**: `edit/editFiles`, `execute/runInTerminal`, `search/usages`,
   `read/file` são nomes de tool do Copilot/VS Code. O Antigravity usa nomes próprios
   (ex.: `read_file`, `edit_file`, `run_terminal_command`, `search_files`). Os corpos dos
   agentes referenciam esses nomes de tool em vários pontos — a conversão precisa ser
   consistente entre frontmatter e corpo.
3. **Caminho dos agentes**: os 4 estão em `.agents/rules/agents/` (dentro de `rules/`).
   Se o Antigravity espera custom agents em `.agents/agents/` (fora de `rules/`), mover
   a pasta `agents/` um nível acima — o `GEMINI.md` menciona `.agents/agents/`, o que
   sugere essa intenção original.
4. **bug.md na raiz** (108 KB): é um RELATÓRIO de análise (pec_excluiargos, 2026-07-27),
   não um chatmode — não foi convertido a agente. Se quiser preservá-lo como material
   de referência, considere movê-lo para `docs/` ou `ref/` para não competir com os
   arquivos de configuração de agentes na raiz.
5. **Duplicidade de contexto**: `CLAUDE.md` (orquestração Paperclip: ceo/cto/senior-devs)
   e a estrutura `.agents/` (agents especializados) cobrem papéis parecidos com nomes
   diferentes (`pjeplus-analyst` vs `senior-dev-backend` etc.). Para o Antigravity, vale
   decidir qual das duas hierarquias vale — ou mapear uma para a outra.

---

## 5. Resumo

| Item | Estado |
|---|---|
| Regra global core (idx-core.md) | Criado e operacional |
| Ponte de contexto (GEMINI.md) | Criado e operacional |
| pjeplus-analyst (ex-Analise.md) | Criado (19,9 KB, frontmatter Copilot a converter) |
| pjeplus-debug (ex-Bug.md) | Criado (4,4 KB, frontmatter Copilot a converter) |
| pjeplus-surgical (ex-PJE.md) | Criado (9,9 KB, frontmatter Copilot a converter) |
| pjeplus-script (ex-Java.md) | Criado (8,8 KB, frontmatter Copilot a converter) |
| gmn.md (este compilador) | Criado |
| Conversão de frontmatter (model/tools) | Pendente — ver item 4.1 e 4.2 |
