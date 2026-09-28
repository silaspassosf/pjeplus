# 04 — Headless

**Resposta curta:** sim, o Playwright é materialmente melhor em headless — e
não por ser mais rápido. É porque no Selenium o headless é um *modo diferente*
que quebra coisas, e no Playwright é o mesmo caminho de renderização.

---

## O fato que enquadra tudo

O projeto **não roda headless hoje**. No código ativo:

```
headless=False   14 ocorrências
headless=True     0 ocorrências
```

Ou seja: existe uma camada inteira de compensação para headless
(`click_headless_safe`, `limpar_overlays_headless`, `scroll_to_element_safe`,
`is_headless_mode`, o zoom hack) e **ela nunca é exercitada em produção**. Foi
construída, não deu confiança suficiente, e os fluxos ficaram todos visuais.

Isso é evidência, não opinião: headless em Selenium foi tentado e abandonado.

---

## Por que o Selenium headless falha

O Firefox headless do geckodriver renderiza por um caminho diferente do headed.
Consequências que o projeto teve de contornar:

| Sintoma | Contorno que existe hoje | Onde |
|---|---|---|
| Elemento "não interagível" que está visível | `click_headless_safe` com 3 estratégias progressivas | `Fix/browser_suporte.py:343` |
| Overlays/modais que não somem | `limpar_overlays_headless` | `Fix/browser_suporte.py:264` |
| Scroll que não leva o elemento à área clicável | `scroll_to_element_safe` | `Fix/browser_suporte.py:311` |
| Elemento fora do viewport mesmo após scroll | `document.body.style.zoom = '60%'` | `Fix/core.py:264-270` |

O zoom hack é o mais revelador: encolher a página inteira a 60% para fazer um
clique funcionar é sintoma de que a geometria em headless não bate com a headed.

## Por que o Playwright não tem esse problema

Headless e headed usam **o mesmo build e o mesmo caminho de renderização**. A
checagem de actionability (`visible` + `stable` + `enabled` + `recebe eventos`) é
idêntica nos dois modos, e o Playwright **repete até passar** em vez de falhar na
primeira tentativa.

Consequência concreta: os quatro contornos acima viram **código morto**. Não é
otimização de velocidade — é remoção de uma classe inteira de falha.

---

## Riscos reais que sobram (e o que fazer)

### 1. `pyperclip.paste()` em `extrair_pdf` — risco médio, já tem saída

`Fix/extracao.py:189-210` clica no botão copiar do PJe e lê a área de
transferência do sistema operacional. Em headless — e principalmente numa
máquina sem sessão gráfica — isso é frágil ou impossível.

**A boa notícia:** o código já tem o caminho correto como fallback, algumas
linhas abaixo:

```python
pre = modal.find_element(By.CSS_SELECTOR, 'pre')
texto = pre.text
```

O texto está no DOM. O clipboard é um desvio desnecessário.

**Ação:** inverter a ordem — ler o `<pre>` primeiro, usar o clipboard só se o
`<pre>` não existir. Mais rápido, mais confiável, e headless-safe.
→ pertence à **etapa E2** (`Fix/extracao.py`).

### 2. Downloads — risco baixo, mas o mecanismo muda

`Fix/core.py` configura `browser.download.dir`,
`browser.helperApps.neverAsk.saveToDisk` e `pdfjs.disabled`. **O Playwright
ignora essas prefs** — ele gerencia downloads pela própria API
(`accept_downloads=True` + evento `download`).

**Verificado:** nenhum fluxo lê a pasta `downloads/`. Os prefs são vestigiais.
Então isto **não é um bug hoje**. Mas se algum fluxo passar a depender de
arquivo baixado, o caminho correto no Playwright é:

```python
with page.expect_download() as info:
    page.locator('#baixar').click()
caminho = info.value.path()
```

→ só vira ação quando algum fluxo precisar. Registrar, não implementar.

### 3. Fontes — risco baixo, mas silencioso

Fontes ausentes mudam métricas de texto e podem alterar quebra de linha e
posição. Afeta extração baseada em posição, não a baseada em DOM. Como este
projeto extrai por DOM e por API, o risco é pequeno — mas é a explicação típica
de "funciona visual, quebra headless" quando ocorre.

### 4. Diagnóstico — o risco mais subestimado

Sem tela, uma falha vira uma linha de log. É por isso que headless costuma ser
abandonado: não pela taxa de falha, mas por não se conseguir investigar.

O Playwright resolve isso melhor que qualquer contorno Selenium:

```bash
py play/rodar.py --trace        # trace.zip: DOM, rede e console POR AÇÃO
```

```bash
playwright show-trace play/medicoes/<arquivo>.zip
```

O trace mostra o snapshot do DOM no instante exato de cada clique. É
literalmente melhor que ter olhado a tela, porque é retroativo.

Vídeo também está disponível (`record_video_dir` no `new_context`) se um caso
específico pedir.

### 5. AutoHotkey — **não é bloqueador**

`Fix/core.py:2432-2438` define caminhos de AHK, mas `AHK_EXE_ACTIVE = None`,
`AHK_SCRIPT_ACTIVE = None` e nada invoca. O login ativo é `login_cpf`, que
preenche o DOM. Constantes vestigiais.

---

## Otimizações que só compensam em headless

| O quê | Como | Ganho |
|---|---|---|
| Bloquear imagens/fontes/mídia | `criar_driver_PC(headless=True, bloquear_midia=True)` | grande — nada precisa ser renderizado, e essas requisições dominam o tráfego das telas de timeline |
| Viewport fixo | já é o padrão do `launcher.py` (1920×1080) | evita a divergência de geometria que o zoom hack contornava |
| Sem `maximize_window()` | o `PWDriver` mapeia para `set_viewport_size` | determinismo entre execuções |

`bloquear_midia` existe e está implementado (`launcher.py::_bloquear_recursos`),
mas **não está ligado por padrão** — é escolha consciente, porque em modo visual
uma página sem imagem confunde quem está olhando.

---

## Como habilitar headless (quando chegar a hora)

Não é uma etapa própria: as ações se distribuem pelas etapas que já possuem os
arquivos.

| Ação | Etapa dona |
|---|---|
| Remover o zoom hack de `Fix/core.py:264-270` | **E1** |
| Inverter clipboard/`<pre>` em `extrair_pdf` | **E2** |
| Marcar `click_headless_safe`, `limpar_overlays_headless`, `scroll_to_element_safe` como legado sob Playwright | **E3** |
| Trocar `headless=False` por parâmetro nos pontos de criação de driver | **E1** (`Fix/core.py`) |
| Rodar o lote de comparação **também** em headless | **E10** |

⚠️ **Não delete** a camada de compensação. Ela ainda é necessária no caminho
Selenium, que continua sendo produção. Marcar como legado ≠ remover.

## Critério para dizer que headless funciona

Em **E10**, rodar o mesmo lote três vezes em cada combinação:

```
selenium headed | playwright headed | playwright headless
```

Headless só é aprovado se a taxa de falha do `playwright headless` for igual à
do `playwright headed`. Ganho de tempo sem paridade de falha não vale — foi
exatamente assim que a tentativa anterior morreu.
