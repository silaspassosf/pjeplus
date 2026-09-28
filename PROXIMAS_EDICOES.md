# PRÓXIMAS EDIÇÕES — PJePlus pós-migração Playwright

Documento de execução. Cada item tem arquivo:linha, evidência no monólito de referência
(`+pje/PJe-Atual/gigs-plugin.js`, em produção) e ação esperada. Execute **um item por vez**,
teste, commite, siga para o próximo.

**Base do levantamento:** `TRADUCAO_MONOLITO_GIGS.md` (achados A1–A8) cruzado com o bot Playwright.

**Fora do escopo — NÃO fazer:** A6 (seletores posicionais `nth-child`) e A7 (xpath remanescentes).

---

## Regras de execução

- Branch de trabalho: `refactor/pw-nativo`.
- **1 commit por item**, mensagem no padrão `refac: <item> — <o que mudou>`.
- Rodar **antes de cada commit**:
  - `py play/smoke.py --projeto` — 91 verificações (tem que continuar 91/91).
  - `py tools/check_pw.py` — ratchet (não pode subir a contagem de padrões legados).
- Comentários no código: **zero** (só pragma quando indispensável). Log: **só de falha**.
- Contrato de log é intocável: `── fluxo ──`, `[RESUMO]`, `[FLUXO] OK|FALHA`, `encerrando`.
- Não alterar estrutura de pastas nem mover arquivos.
- Ratchet e smoke verdes são a condição para o commit. Item vermelho = para tudo e reporta.

---

## Item 0 — BUG (prioridade máxima): import inexistente derruba a timeline via API

**Arquivo:** `Fix/core.py:2398` — dentro de `_obter_timeline_via_api()` (def em ~2391; chamada da
API em ~2420). Chamadores: `Fix/core.py` ~2645-2660 e ~2788-2800.

**Código atual:**

```python
from Fix.variaveis import PjeApiClient, obter_sessao_do_driver
...
sess = obter_sessao_do_driver(driver)
if not sess:
    ...
    return None
from urllib.parse import urlparse
_host = urlparse(url_atual).netloc
client = PjeApiClient(sess, _host)
```

**Problema:** `obter_sessao_do_driver` **não existe** em `Fix/variaveis.py`. O que existe:

| Nome real | Onde | O que faz |
|---|---|---|
| `session_from_driver(driver, grau=1)` | `Fix/variaveis.py:364` | devolve `(sess, host)` |
| `cliente_para(driver, grau=1) -> PjeApiClient` | `Fix/variaveis.py:410` | devolve o cliente já com a sessão correta e **nunca levanta** |

`cliente_para` usa o `APIRequestContext` do próprio contexto Playwright (`pjeplay.api.requisicao`)
e cai para o caminho `requests`/`session_from_driver` se algo falhar. É o caminho moderno, já usado
pelo resto do código migrado.

**Efeito real:** o `ImportError` é engolido pelo `except` da função → retorno `None` sempre →
fallback DOM → em execução real: `[BAIXAR_CP] Nem Certidao de Distribuicao nem Despacho encontrados`.
Atinge o caminho do mandado e do p2b (baixar CP / timeline).

**Correção (mínima):**

```python
from Fix.variaveis import cliente_para
...
client = cliente_para(driver)
```

Ajustar as referências `sess` remanescentes e remover o import de `PjeApiClient` se ele não for
usado em outro ponto da função.

**Verificação:** smoke + ratchet; em execução real de mandado, o log deve trazer
`[TIMELINE_API] ✓ Obtido timeline com N itens via API` e não mais o erro de import.

---

## Item 1 — A1: escopar o botão "Gravar os movimentos"

**Arquivo:** `atos/judicial_fluxo.py:785`

**Hoje:**

```python
btn_gravar_mov = wait_for_clickable(driver, "button[aria-label='Gravar os movimentos a serem lançados']", timeout=10)
```

Seletor global. Com outro diálogo aberto na página, pode casar com o botão de outra janela.

**Monólito:** usa o escopo do diálogo do lançador de movimentos —
`pje-lancador-movimentos-dialogo button[aria-label='Gravar os movimentos a serem lançados']`.

**Ação:** prefixar o seletor com `pje-lancador-movimentos-dialogo ` (1 linha).

---

## Item 2 — A4: chips — expandir antes de ler/remover

**Arquivo:** `atos/movimentos_chips.py`

**Hoje:** a leitura é `//mat-chip` **global** e não há nenhum clique em "Expandir Chips".
Com a lista de etiquetas colapsada, os chips não estão no DOM → a remoção vira **no-op silencioso**
(falso sucesso).

**Monólito:** antes de operar, expande a lista e escopa tudo em `pje-lista-etiquetas`.

**Ação:**
1. Antes de ler/remover, clicar em "Expandir Chips" (quando o botão existir).
2. Escopar a busca e a remoção para `//pje-lista-etiquetas//mat-chip`.

---

## Item 3 — A2/A3: editor — seletor de 3 condições + validação escopada

O monólito usa **3 condições** para achar o editor:
`div[class*="area-conteudo"][contenteditable="true"][role="textbox"]`.
O bot usa variações de 2 condições (sem `role="textbox"` ou sem `area-conteudo`) em 3 lugares, e
valida conteúdo de forma global em um quarto.

**(a) `atos/judicial_fluxo.py:419`** — hoje usa 2 condições
(`div[class*="area-conteudo"][contenteditable="true"]`). Falta `[role="textbox"]`.

**(b) `Fix/utils.py:1022`** — em `_get_editable()`, a lista tem
`'div[role="textbox"][contenteditable="true"]'`. Falta `[class*="area-conteudo"]` — pode casar com
editor que não é o alvo.

**(c) `PEC/anexos/anexos_juntador_helpers.py:288`** — mesma lista, mesma entrada incompleta.

**(d) `atos/comunicacao_preenchimento.py`** — `_aguardar_ck_com_conteudo()` (:77) aceita **qualquer**
editor da página: percorre `.ck-editor__editable`, `.ck-content`, `div[contenteditable="true"]`,
`textarea`, `iframe` e ainda varre `window.CKEDITOR.instances` globalmente. É a raiz do falso
`Conteudo do modelo nao presente no editor` (execução de 22/09).
O monólito (`verificarSeExisteTextoNoEditor`, ~10765-10830) valida **só o editor alvo** e aceita
`figure` (imagem colada) como conteúdo válido.

**Ação:** alinhar (a), (b) e (c) ao seletor de 3 condições do monólito; em (d) escopar a checagem
ao editor alvo e aceitar `figure` como conteúdo válido.

---

## Item 4 — A5: confirmação do sobrestamento

**Arquivo:** `atos/movimentos_sobrestamento.py` (~145-153)

**Hoje:** o loop detecta snackbar de sucesso e fechamento do diálogo, mas termina em
`return True` sem confirmação — "assume sucesso". Já produziu falso-positivo com retrabalho
(registros de 20/09 e 21/09: mesmo processo "confirmado" e depois reaparecendo).

**Monólito** (bloco ~13055-13135): sucesso é **condição observável positiva** —
diálogo sumiu **ou** snackbar `Sobrestamento(s) registrado(s) com sucesso`; caso contrário,
falha explícita (`Falha ao tentar registrar o prazo do sobrestamento`).

**Ação:** trocar o retorno otimista por confirmação positiva; na ausência dela, retornar falha
(nunca "assume sucesso").

---

## Item 5 — A8: catálogo único de seletores (estrutural — executar por ÚLTIMO)

Os mesmos seletores aparecem repetidos e com variações em `atos/`, `Fix/` e `PEC/` — foi
exatamente isso que gerou o item 3. O monólito tem um catálogo único (`+pje/comum/seletores.js`,
chave `areaConteudo`).

**Ação:** centralizar os seletores frágeis num único módulo **já existente**, migrando os pontos
tocados nos itens 1 a 4. Não criar estrutura nova.
**Só executar depois dos itens 0 a 4 estarem verdes e commitados.**

---

## Fora do escopo (decisão do Silas — não fazer agora)

- **A6** — seletores posicionais (`nth-child`): 162 `By.XPATH` no bot e posições frágeis como
  `td:nth-child(9)` (`Prazo/loop_orquestrador.py`) e `li:nth-child(16)` (`Fix/extracao.py:883`).
- **A7** — xpath remanescentes.

---

## Protocolo de execução e rollback

1. `git status` limpo e branch `refactor/pw-nativo` sincronizado antes de começar.
2. Um item por vez: editar → smoke → ratchet → commit.
3. Rollback de um item: `git revert <hash>` (cada item é um commit isolado).
4. Itens 0 → 1 → 2 → 3 → 4 → 5 (o 5 por último).
5. Ponto de retorno seguro: tag `refac-f7` (estado atual fechado, F0–F7 completas).
6. Ao fechar o lote, atualizar a seção 0 do `PW.md` (contrato de progresso) e marcar o novo
   estado com uma tag.
