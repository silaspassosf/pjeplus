# 00 — Contexto obrigatório

> **Leia este arquivo inteiro antes de executar qualquer etapa.** Ele é curto de
> propósito. Uma janela de chat que comece uma etapa sem este contexto vai
> tomar decisões erradas — principalmente sobre o que **não** pode ser tocado.

---

## O que é o `play/`

`play/pjeplay/` é um **backend Playwright** para o PJePlus. Não é uma cópia do
projeto: implementa a superfície do WebDriver sobre o Playwright e se registra
em `sys.modules` no lugar do `selenium`.

Consequência: `Fix/`, `atos/`, `PEC/`, `Prazo/`, `Mandado/`, `SISB/`,
`Peticao/`, `Triagem/`, `bianca/` rodam **sem uma linha alterada**, nos dois
motores. Não existe nada para re-sincronizar.

```
py x.py                    # Selenium (produção, intocado)
py play/rodar.py           # Playwright, mesmo x.py, mesmos fluxos
py play/rodar.py --selenium  # Selenium com a mesma instrumentação (baseline)
```

### Por que não é um fork

Existiu um fork antes: cópia integral do projeto, que apodreceu em ~1 mês.
Nenhuma das divergências tinha a ver com Playwright — eram regras de negócio e
API evoluindo na raiz enquanto a cópia ficava parada.

A regra que impede isso de voltar é **verificável**, não é disciplina:

> Se um módulo não importa `selenium`/`playwright` nem recebe `driver`/`page`,
> ele **não é copiado** — é importado da raiz.

```bash
py play/guarda.py    # sai != 0 se a fronteira for violada
```

---

## Escopo

**Dentro:** Mandado, PEC, P2B — mais `Fix/` e `atos/`, que os três atravessam,
e a superfície do **SISBAJUD alcançável pelo PEC**.

SISB não é fluxo próprio: `PEC/regras_execucao.py:225::_executar_sisbajud`
chama `SISB.core.iniciar_sisbajud(driver_pje=driver)`, que abre um **segundo
driver** noutro site. Os buckets `sisbajud_teimosinha` e `sisbajud_resultado`
estão no `BUCKET_ORDEM` do PEC.

O SISB do Mandado é outra coisa: `processar_sisbajud(texto_certidao)` recebe
*texto* e analisa a certidão de devolução — sem browser, nada a migrar.

**Fora:** Petição, Triagem, DOM e o SISB standalone. Seguem em Selenium.

---

## ⛔ Proibições absolutas

Violar qualquer uma delas causa dano real. Não há exceção "só desta vez".

### 1. `SISB/Core/` é intocável

É onde mora a evasão de detecção do SISBAJUD (sistema do CNJ):

- `simulate_human_movement` — os `sleep` existem **para** gastar tempo; sem
  eles a função vira no-op;
- `aplicar_rate_limiting`, `smart_wait`, `anti_detection_measures`;
- há um `time.sleep(30)` que aguarda intervenção manual em CAPTCHA.

Encurtar qualquer uma dessas esperas pode causar **bloqueio**. Não abra, não
edite. Confirme ao final de qualquer etapa:

```bash
git diff --name-only SISB/Core/    # PRECISA sair vazio
```

Pela mesma razão, **fora** de `SISB/Core/`: qualquer espera cujo contexto
sugira throttle, ritmo, intervalo entre requisições, simulação de comportamento
humano ou jitter aleatório — **deixe como está**.

### 2. Shims e legado

`idx.md` lista os arquivos que são apenas re-exportação (`Fix/abas.py`,
`Fix/element_wait.py`, `Fix/selenium_base/*`, `atos/judicial.py`, …) e os
legados (`leg/`, `_archive/`, `Mandado/core.py`). Alterações vão nos arquivos
reais. Consulte `idx.md` antes de editar qualquer arquivo de `Fix/`.

### 3. Esperas de retry/backoff

Espera dentro de `except` ou de laço de tentativa é **política de retry**, não
espera de UI. Não converta.

---

## 🔒 A propriedade de segurança que torna tudo isso reversível

Toda função do vocabulário de espera (`Fix/espera.py`) é **limitada pelo
`teto`**, que é a duração do `sleep`/timeout que ela substituiu.

> Se a condição nunca ocorrer, o custo é **idêntico** ao código original.
> Nunca mais lenta, nunca menos confiável — só mais rápida quando a condição
> chega antes.

Isso é o que permite converter centenas de sítios sem apostar. Errar o seletor
degrada para o comportamento de hoje; não quebra.

**Corolário operacional:** o `teto` de uma conversão é sempre **exatamente** o
valor que já estava lá. Nunca aumente, nunca diminua. Se você sentir vontade de
ajustar um teto, você está fora do escopo da etapa.

---

## Estado atual (o que já está pronto)

| Componente | Onde | Estado |
|---|---|---|
| Camada de compatibilidade WebDriver→PW | `play/pjeplay/compat.py`, `driver.py`, `element.py`, `script.py`, `waits.py`, `actions.py`, `locators.py` | ✅ pronto |
| Fábricas de driver | `play/pjeplay/launcher.py` | ✅ pronto |
| Caminho rápido dos helpers de `Fix/` | `play/pjeplay/nativo.py` | ✅ pronto |
| Vocabulário PJe nativo (mat-select, CKEditor, abas…) | `play/pjeplay/pje.py` | ✅ pronto |
| API pelo contexto do browser | `play/pjeplay/api.py` | ✅ pronto |
| Instrumentação e comparação | `play/pjeplay/medicao.py`, `play/rodar.py` | ✅ pronto |
| Vocabulário de espera | `Fix/espera.py` | ✅ pronto — ver `02-esperas.md` |
| Sleeps convertidos | escopo todo | 🟡 129 mecânicos + 37 precisos; ~90 restantes |
| `WebDriverWait`/`EC` convertidos | escopo todo | 🔴 244 + 249 pendentes |
| Fluxos nativos (P2B, PEC, Mandado) | — | 🔴 não iniciados |
| Validação end-to-end contra o PJe real | — | 🔴 **nada foi validado em produção** |

---

## Riscos — estado

| # | Risco | Estado |
|---|---|---|
| R1 | Firefox do Playwright vs geckodriver | ✅ resolvido — `launcher.py`, prefs espelhadas de `Fix/core.py` |
| R2 | Timing do overlay CDK no mat-select | ✅ resolvido — `pje.mat_select` espera abrir, renderizar e fechar |
| R3 | CKEditor 4 vs 5 | ✅ resolvido — `pje.ckeditor_versao` detecta em runtime |
| R4 | Angular zone indisponível em build de produção | ✅ resolvido — fallback para ausência de spinner |
| R5 | Estrutura de cookies difere | ✅ resolvido — `PWDriver.get_cookies()` devolve formato Selenium |
| R6 | ThreadPoolExecutor não é thread-safe no PW | ✅ **descartado** — `ParallelProcessor` é código morto; `series_fluxo.py` é sequencial |
| R7 | Print dialogs do SISB | 🟡 fora do escopo atual |
| R9 | Playwright Firefox não carrega extensões | ✅ **descartado** — nenhum `.xpi` é carregado pelo Python |
| R10 | Sessão PJe expira em loop longo | ✅ detecção + re-login já existem |

---

## Como validar qualquer alteração

Obrigatório ao final de **toda** etapa, sem exceção:

```bash
py play/smoke.py --projeto
```

91 verificações offline (fixture HTML, sem rede): superfície WebDriver,
vocabulário PJe, esperas, API, e carga real dos módulos de negócio. **Sem
mocks** — se passar, funcionou de verdade.

E, para os arquivos que a etapa tocou:

```bash
python -m py_compile <arquivo>
```

```bash
py play/guarda.py
```

---

## O que este projeto ainda não sabe

Nada foi validado contra o PJe real. O plano prevê validação por repetição em
processos isolados (ver `etapas/E10-baseline.md`). Até lá, qualquer afirmação
de ganho é teórica — por isso a instrumentação existe.
