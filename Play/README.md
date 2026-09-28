# play/ — backend Playwright do PJePlus

`pjeplay` **não é uma cópia do projeto**. É uma camada que implementa a
superfície do WebDriver sobre o Playwright e se registra em `sys.modules` no
lugar do `selenium`. O código de negócio real — `Fix/`, `atos/`, `PEC/`,
`Prazo/`, `Mandado/`, `SISB/` — roda sem uma linha alterada, nos dois motores.

Consequência: **não existe nada para re-sincronizar.**

---

## Uso

```bash
pip install -r play/requirements.txt
```

```bash
playwright install firefox
```

```bash
py pw.py
```

Mesmo menu e mesmos fluxos do `x.py`, com o motor trocado. O executor é o `pw.py` na raiz; o motor vive em `play/pjeplay/`.

| comando | o que faz |
|---|---|
| `py pw.py` | Playwright, helpers nativos ligados |
| `py pw.py --selenium` | Selenium com a mesma instrumentação (baseline) |
| `py pw.py --trace` | + `trace.zip` navegável (DOM, rede, console por ação) |
| `py pw.py --sem-nativo` | só a camada de compatibilidade |
| `py pw.py --comparar a.json b.json` | atribui o ganho: motor vs reescrita |
| `py play/smoke.py --projeto` | 91 verificações offline |
| `py play/guarda.py` | falha se a fronteira do fork for violada |
| `py play/migrar_sleeps.py` | troca mecânica de `time.sleep` (dry-run) |

Em código:

```python
import pjeplay
pjeplay.iniciar()                     # ANTES de qualquer import do projeto

from Fix.core import criar_driver_PC  # já devolve um driver Playwright
driver = criar_driver_PC(headless=False)
```

> A ordem importa: `from Fix.core import esperar_elemento` fixa o nome no
> momento do import, então `iniciar()` tem que vir antes.

---

## Documentação

A implementação restante está fatiada em **etapas isoladas**, cada uma
executável por uma janela de chat independente, sem conflito de arquivos.

| Documento | Quando ler |
|---|---|
| **[`docs/00-contexto.md`](docs/00-contexto.md)** | **Sempre.** Arquitetura, proibições, garantias, estado. |
| [`docs/01-traducao.md`](docs/01-traducao.md) | Consulta: Selenium → Playwright, `WebDriverWait`/`EC`, Angular Material, CKEditor, abas, API |
| [`docs/02-esperas.md`](docs/02-esperas.md) | Contrato do vocabulário `Fix/espera.py` |
| [`docs/03-etapas.md`](docs/03-etapas.md) | Mapa: quem edita o quê, o que roda em paralelo, o que ficou de fora |
| [`docs/04-headless.md`](docs/04-headless.md) | Por que o headless falha em Selenium e não em Playwright |
| **[`docs/PROMPT-JANELA.md`](docs/PROMPT-JANELA.md)** | Prompt pronto para colar numa janela nova + as 3 trilhas |
| [`docs/etapas/E1`–`E10`](docs/etapas/) | Uma por janela — exige modelo de contexto grande |
| [`docs/receitas/`](docs/receitas/) | Tarefas mecânicas para modelos pequenos (Flash, Mini) |

Para abrir uma janela nova: use o prompt de `PROMPT-JANELA.md`. Ele instrui a
janela a ler `00-contexto` → `02-esperas` → o doc da etapa. Nada mais é
necessário.

---

## Arquitetura

`pjeplay.iniciar()` faz três coisas:

1. **Registra o backend** — substitui `selenium.*` em `sys.modules`. `By`,
   `Keys`, `WebDriverWait`, `expected_conditions`, `ActionChains`, `Select`, as
   exceções e até `webdriver.Firefox()` passam a ser implementações Playwright.
   É isso que permite rodar os ~1.500 pontos que falam WebDriver direto sem
   tocar em nenhum.
2. **Carrega `Fix/`** já sobre esse backend.
3. **Troca os helpers quentes** pelo auto-wait do Playwright.

| Arquivo | Papel |
|---|---|
| `pjeplay/compat.py` | registra o backend em `sys.modules` |
| `pjeplay/driver.py` | `PWDriver` — fachada WebDriver (janelas, frames, cookies, diálogos) |
| `pjeplay/element.py` | `PWElement` — fachada WebElement |
| `pjeplay/script.py` | ponte `execute_script` / `execute_async_script` |
| `pjeplay/waits.py` | `WebDriverWait` + `expected_conditions` compatíveis |
| `pjeplay/actions.py` | `ActionChains` + `Select` |
| `pjeplay/locators.py` | `By` / `Keys` → dialeto Playwright |
| `pjeplay/launcher.py` | fábricas de driver (prefs espelhadas de `Fix/core.py`) |
| `pjeplay/nativo.py` | caminho rápido: helpers de `Fix/` em Playwright puro |
| `pjeplay/pje.py` | vocabulário PJe nativo (mat-select, CKEditor, abas, tabelas) |
| `pjeplay/api.py` | API pelo contexto do browser (`expect_response`, auth compartilhada) |
| `pjeplay/medicao.py` | instrumentação comparável entre motores |

O vocabulário de espera fica na **raiz** (`Fix/espera.py`), não aqui: ele serve
aos dois motores.

---

## Diferenças de comportamento conhecidas

- **Diálogos** (`alert`/`confirm`) são aceitos automaticamente — no Playwright
  um diálogo não respondido congela a página, e o PJe nunca consome alertas.
  Para o fluxo Selenium clássico: `driver.auto_dialogo = None`. A última
  mensagem fica em `driver.ultimo_dialogo`.
- **Perfil de usuário**: `criar_driver(perfil=...)` usa
  `launch_persistent_context`. Perfis do Firefox instalado não são reutilizáveis
  pelo Firefox do Playwright — sessão e certificados precisam ser refeitos.
- **`execute_cdp_cmd`** é no-op (Firefox não expõe CDP). Havia 1 chamada.
- **`driver.page`** dá acesso à `Page` crua, para código novo.

---

## Estado

Verificado por `play/smoke.py` (91/91) até a carga dos módulos de negócio, sem
mocks. **Nada foi validado contra o PJe real** — é o que a etapa E10 faz, e é
ela que decide se o Selenium se aposenta.
