# Correcoes — `Andrei/` vs Legado `Peticao/`

**Data:** 2026-05-06
**Metodo:** Comparacao arquivo-por-arquivo entre `Andrei/` e `Peticao/`, analisando fluxo de execucao real e imports.

---

## 1. [CRITICO] `atos_*` wrappers sao todos stubs genericos

**Arquivo:** `Andrei/regras.py` linhas 21-50

`regras.py` importa `ato_*` de `Andrei.atos_judicial`, onde sao criados via `_make_stub_ato()`:

```python
# atos_judicial.py:1585-1621 — TODOS usam "Despacho" + "Geral"
def _make_stub_ato(nome: str):
    stub = make_ato_wrapper(conclusao_tipo="Despacho", modelo_nome="Geral", descricao=nome)
    stub.__name__ = nome
    return stub

ato_instc = _make_stub_ato("ato_instc")      # "Despacho" + "Geral" — era pra ser "Admissibilidade" + "instrumento em r"
ato_laudo = _make_stub_ato("ato_laudo")      # "Despacho" + "Geral" — era pra ser "Geral - Ciencia do laudo pericial"
ato_teim  = _make_stub_ato("ato_teim")       # "Despacho" + "Geral" — era pra ter sigilo=True, intimar=False
ato_adesivo = _make_stub_ato("ato_adesivo")  # "Despacho" + "Geral" — era pra ter movimento=1059
# ... 20+ wrappers todos com parametros errados
```

Mas `Andrei/atos_wrappers.py` contem as configuracoes **reais** portadas do legado:

```python
# atos_wrappers.py — CONFIGURACOES CORRETAS
ato_instc = make_ato_wrapper(conclusao_tipo="Admissibilidade", modelo_nome="instrumento em r", prazo=8, ...)
ato_inste = make_ato_wrapper(conclusao_tipo="Admissibilidade", modelo_nome="instrumento em a", prazo=8, ...)
ato_laudo = make_ato_wrapper(conclusao_tipo="Despacho", modelo_nome="Geral - Ciencia do laudo pericial", prazo=5, ...)
ato_teim  = make_ato_wrapper(conclusao_tipo="Despacho", modelo_nome="e teimosinha", sigilo=True, intimar=False, ...)
ato_adesivo = make_ato_wrapper(conclusao_tipo="Admissibilidade", modelo_nome="recebade", movimento=1059, ...)
# ... todas as 25+ configuracoes corretas
```

**Consequencia:** Todo ato judicial executado pelo pipeline usa "Despacho" + "Geral" em vez do modelo, prazo, movimento, sigilo e flags especificos. Exemplos do que sai errado:

| Ato | Stub (errado) | Wrapper real (correto) |
|-----|---------------|----------------------|
| `ato_instc` | Despacho / Geral, sem prazo | Admissibilidade / "instrumento em r", prazo=8 |
| `ato_laudo` | Despacho / Geral, sem prazo | Despacho / "Geral - Ciencia do laudo pericial", prazo=5 |
| `ato_teim` | Despacho / Geral, intimar padrao, sem sigilo | Despacho / "e teimosinha", intimar=False, sigilo=True |
| `ato_adesivo` | Despacho / Geral, sem movimento | Admissibilidade / "recebade", movimento=1059 |
| `ato_assistente` | Despacho / Geral, sem prazo | Despacho / "de assis", prazo=1 |

**Correcao — `Andrei/regras.py`:**

Trocar os imports dos `ato_*` de `atos_judicial` para `atos_wrappers`. Manter apenas `make_ato_wrapper` vindo de `atos_judicial` (a factory nao existe em `atos_wrappers`).

```python
# ANTES (linhas 21-50)
from Andrei.atos_judicial import (
    make_ato_wrapper,
    ato_instc,
    ato_inste,
    ato_gen,
    ato_laudo,
    ato_esc,
    ...
)

# DEPOIS
from Andrei.atos_judicial import make_ato_wrapper  # apenas a factory
from Andrei.atos_wrappers import (
    ato_instc,
    ato_inste,
    ato_gen,
    ato_laudo,
    ato_esc,
    ato_escliq,
    ato_datalocal,
    ato_ceju,
    ato_respcalc,
    ato_contestar,
    ato_revel,
    ato_concor,
    ato_prevjud,
    ato_naocoaf,
    ato_naosimba,
    ato_teim,
    ato_adesivo,
    ato_agpetidpj,
    ato_agpet,
    ato_agpinter,
    ato_assistente,
    ato_homacordo,
    ato_uber,
    ato_ccs,
    ato_censec,
    ato_serp,
    ato_conv,
)
```

**Correcao adicional — `Andrei/atos_judicial.py`:**

Remover `_make_stub_ato` e todas as 20+ definicoes de stubs (linhas 1585-1621). Esses stubs nao tem uso real no pipeline e sua presenca causa confusao. O arquivo `atos_judicial.py` deve conter apenas:

- `make_ato_wrapper` (factory)
- `ato_judicial` (fluxo principal)
- `fluxo_cls` (sub-fluxo)
- `_escape_js_string` (helper interno)

---

## 2. [CRITICO] Funcoes helper nunca sao vinculadas ao `regras.py`

**Arquivo:** `Andrei/regras.py` linhas 124-127

```python
checar_habilitacao = None   # DEVERIA ser: from Andrei.helpers import checar_habilitacao
agravo_peticao = None       # DEVERIA ser: from Andrei.helpers import agravo_peticao
def_quesitos = None          # DEVERIA ser: from Andrei.helpers import def_quesitos
contesta_calc = None         # DEVERIA ser: from Andrei.helpers import contesta_calc
```

No legado `Peticao/regras_execucao.py` (linhas 33-36), estas funcoes sao resolvidas via `try/except ImportError`:

```python
# Peticao/regras_execucao.py (FUNCIONA)
try:
    from Peticao.helpers import checar_habilitacao, agravo_peticao, def_quesitos, contesta_calc
except ImportError:
    checar_habilitacao = agravo_peticao = def_quesitos = contesta_calc = None
```

Em `Andrei/regras.py`, as 4 variaveis sao hardcoded como `None`. Como as condicoes em `_regras()` usam `callable(checar_habilitacao)` (que e `False`) e verificacoes de truthiness (`agravo_peticao` como `None` e falsy), as regras dependentes **nunca disparam**.

**Consequencia — Regras que deixam de funcionar:**

| Linha | Regra | Condicao quebrada | Impacto |
|-------|-------|-------------------|---------|
| ~370 | `agravo de peticao` em recurso | `agravo_peticao` e `None` (falsy) | Agravos de peticao nunca sao processados |
| ~378 | `habilitacao` em diretos | `callable(checar_habilitacao)` = False | Processos de habilitacao nunca analisados |
| ~386 | `quesitos` em conhecimento | `callable(def_quesitos)` = False | Quesitos em fase de conhecimento nunca processados |
| ~401 | `calculos` em liquidacao | `contesta_calc` e `None` → cai no fallback `ato_respcalc` | Nunca decide entre `ato_contestar` (com advogado) e `ato_revel` (sem advogado); sempre usa `ato_respcalc` |

**Correcao — `Andrei/regras.py`:**

Substituir as 4 linhas `= None` por imports diretos:

```python
# ANTES (linhas 124-127)
checar_habilitacao = None
agravo_peticao = None
def_quesitos = None
contesta_calc = None

# DEPOIS
from Andrei.helpers import (
    checar_habilitacao,
    agravo_peticao,
    def_quesitos,
    contesta_calc,
)
```

**Verificacao de segurança:** Nao ha import circular. `Andrei/helpers.py` importa de `Andrei/api_client.py`, `Andrei/extracao.py`, `Andrei/utils_selenium.py` e `Andrei/atos_wrappers.py`. Nenhum desses importa de `Andrei/regras.py`. O `Andrei/regras.py` por sua vez importa de `Andrei/atos_judicial.py` e `Andrei/extracao.py`. O ciclo nao se fecha.

---

## 3. [CRITICO] `extrair_documento()` retorna string, mas e tratada como tupla

**Arquivo:** `Andrei/helpers.py` linhas 610-615 (funcao `agravo_peticao`)

```python
# ERRADO — texto_tuple[0] extrai o primeiro CARACTERE da string, nao o texto todo
texto_tuple = extrair_documento(
    driver, regras_analise=None, timeout=10, log=False
)
if texto_tuple and texto_tuple[0]:
    texto = texto_tuple[0].lower()
```

`extrair_documento()` (definida em `Andrei/extracao.py:302-310`) retorna `Optional[str]`:

```python
def extrair_documento(driver, regras_analise=None, timeout=15, log=False) -> Optional[str]:
    res = extrair_direto(driver, timeout=timeout, debug=log, formatar=True)
    if not res or not res.get('sucesso'):
        return None
    return res.get('conteudo')  # <- retorna STRING
```

Quando a string nao e vazia, `texto_tuple[0]` retorna `'p'` (primeiro caractere de "peticao...") em vez do texto completo. A analise de "desconsideracao" + "defiro/indefiro" sempre falha porque esta procurando palavras num texto de 1 caractere.

**Nota:** O mesmo bug existe no legado `Peticao/runtime_pet.py:148-151` e `Peticao/helpers/helpers.py:352-353`. Foi portado sem correcao.

**Correcao — `Andrei/helpers.py`, funcao `agravo_peticao` (aprox. linha 610):**

```python
# ANTES
texto_tuple = extrair_documento(
    driver, regras_analise=None, timeout=10, log=False
)
if texto_tuple and texto_tuple[0]:
    texto = texto_tuple[0].lower()

# DEPOIS
texto_str = extrair_documento(
    driver, regras_analise=None, timeout=10, log=False
)
if texto_str:
    texto = texto_str.lower()
```

**Aplicar a mesma correcao no legado** `Peticao/runtime_pet.py:148-151` para manter paridade.

---

## 4. [MODERADO] `criar_gigs` e stub vazio — precisa trazer implementacao real do legado

**Arquivo:** `Andrei/extracao.py` linhas 329-338

```python
def criar_gigs(driver, dias, resposta, observacao):
    """Stub — apenas loga, nao faz nada no PJe."""
    try:
        logger.info("[GIGS] Criando GIGS: Dias=%s, Resposta='%s', Obs='%s'", dias, resposta, observacao)
        return True  # <- sempre retorna True sem interagir com a pagina
    except Exception as e:
        logger.error("[GIGS] Erro ao criar GIGS: %s", e)
        return False
```

O legado `Fix/extracao.py:907-1015` tem a implementacao real via Selenium que:
1. Clica no botao "Nova Atividade"
2. Preenche campo de dias (`input[formcontrolname="dias"]`)
3. Preenche campo de responsavel (`input[formcontrolname="responsavel"]`) com ArrowDown + Enter
4. Preenche campo de observacao (`textarea[formcontrolname="observacao"]`)
5. Clica "Salvar" e aguarda confirmacao "Atividade salva com sucesso"
6. Suporta string shorthand: `"7/xs/carta"` → dias=7, responsavel="xs", observacao="carta"

Alem disso, depende de `_parse_gigs_string()` (`Fix/extracao.py:860-904`) para parse das strings shorthand.

**Consequencia:** Toda chamada a `criar_gigs()` no pipeline (criacao de atividades GIGS no PJe) e no-op. As atividades nunca sao criadas no sistema. Isso afeta:
- Finalizacao de bucket `analise` (fallback: `criar_gigs(driver, '', '', 'Analise - sem filtro reconhecido')`)
- Regras que criam GIGS como acao: `_gigs("1", "", "xs cumprir")`, `_gigs("-1", "", "Bruna Liberacao")`, etc.
- `checar_habilitacao` em `helpers.py` (quando ativada pela correcao #2)

**Correcao — `Andrei/extracao.py`:**

Substituir a funcao `criar_gigs` atual pela implementacao completa de `Fix/extracao.py:907-1015`. Necessario tambem incluir `_parse_gigs_string` (linhas 860-904 do mesmo arquivo).

**Nota sobre assinatura:** A funcao no legado tem assinatura `criar_gigs(driver, dias_uteis=None, responsavel=None, observacao=None, timeout=10, log=True)`. O stub atual em Andrei tem `criar_gigs(driver, dias, resposta, observacao)`. As chamadas no codigo usam padroes como:
- `criar_gigs(driver, "1", "", "xs cumprir")` → 3 params posicionais
- `criar_gigs(driver, '', '', 'Analise - sem filtro reconhecido')` → 3 params posicionais
- `criar_gigs(driver, "-1", "", "Bruna Liberacao")` → 3 params posicionais

A implementacao do legado suporta isso porque tem logica de compatibilidade (`if observacao is None and responsavel is not None: observacao = responsavel; responsavel = None`).

---

## 5. [MODERADO] Consolidacao de `delete.js` ausente

**Arquivo:** `Andrei/pipeline.py` — classe `AndreiOrquestrador.executar()`

Legado `Peticao/runtime_pet.py` (linhas 493-495) chama ao final da execucao:

```python
if apagar_itens:
    logger.info('[PET_ORQ] Consolidando delete.js e gerando bookmarklet')
    _consolidar_delete_bookmarklet()
```

Isso le o `delete.js` acumulado, extrai os processos marcados e gera um bookmarklet JavaScript que o usuario pode clicar para remover os itens do escaninho.

Andrei nunca gera o bookmarklet. A funcao `apagar()` em `helpers.py` escreve em `delete.js`, mas o usuario precisa construir o bookmarklet manualmente.

**Correcao:** Portar as funcoes de `Peticao/suporte_pet.py`:

1. `extrair_processos_delete()` — le e parseia `delete.js` (linhas 284-329)
2. `gerar_bookmarklet_apagar(processos)` — gera o JS do bookmarklet (linhas 332-381)
3. `consolidar_delete_com_bookmarklet()` — orquestra as duas acima (linhas 385-411)

Adicionar a chamada no final de `AndreiOrquestrador.executar()` apos processar o bucket `apagar`.

---

## 6. [MODERADO] Recovery de driver depende de login manual

**Arquivo:** `Andrei/pipeline.py` linha 587

```python
configurar_recovery_driver(criar_driver, aguardar_login_manual)
```

Legado Peticao configura recovery com login CPF automatico:

```python
configurar_recovery_driver(_driver_pc, _login_cpf)
```

**Consequencia:** Se o driver cair durante execucao nao supervisionada (ex.: sessao expira, acesso negado), o recovery abrira um novo Firefox e aguardara **ate 5 minutos** por interacao humana. O pipeline trava indefinidamente.

**Correcao sugerida:** Duas opcoes:
- **A:** Documentar explicitamente que Andrei **nao suporta execucao desassistida** — se o driver cair, o usuario precisa estar presente para logar novamente.
- **B:** Modificar `handle_exception_with_recovery` para, apos falha no recovery manual, retornar `None` imediatamente em vez de aguardar timeout completo. O pipeline entao encerra com erro claro.

---

## 7. [MODERADO] Inconsistencia de caminho do `dadosatuais.json` entre modulos

**Arquivos afetados:** `helpers.py`, `pipeline.py`, `regras.py`

O design definido e que **tudo fica em `Andrei/dadosatuais.json`** independente do CWD. Porem ha divergencia:

| Modulo | Escreve em | Le de | Status |
|--------|-----------|-------|--------|
| `pipeline.py` | `"Andrei/dadosatuais.json"` (via `_CAMINHO_DADOS`) | — | OK |
| `pipeline.py:extrair_dados_processo` | `"Andrei/dadosatuais.json"` (via parametro) | — | OK |
| `regras.py:_Dados.__init__` | — | `Path(__file__).parent / "dadosatuais.json"` = `Andrei/dadosatuais.json` | OK |
| `helpers.py:checar_habilitacao` | `"dadosatuais.json"` (CWD relativo) | `Path("dadosatuais.json")` (CWD relativo) | **ERRADO** |
| `helpers.py:contesta_calc` | `"dadosatuais.json"` (CWD relativo) | `Path("dadosatuais.json")` (CWD relativo) | **ERRADO** |

Quando executado da raiz `D:\PjePlus`:
- `"dadosatuais.json"` resolve para `D:\PjePlus\dadosatuais.json`
- `Path(__file__).parent / "dadosatuais.json"` resolve para `D:\PjePlus\Andrei\dadosatuais.json`

**Nota:** Como `checar_habilitacao` e `contesta_calc` nao estao ativos (ver correcao #2), isso nao se manifesta atualmente. Ao corrigir #2, este problema aparece.

**Correcao — `Andrei/helpers.py`:**

1. Na funcao `checar_habilitacao` (~linha 409): trocar `caminho_json="dadosatuais.json"` por `caminho_json="Andrei/dadosatuais.json"`
2. Na funcao `contesta_calc` (~linha 942): mesmo ajuste
3. Nas leituras de `dadosatuais.json` dentro dessas funcoes (via `Path("dadosatuais.json")`): trocar por `Path("Andrei/dadosatuais.json")`

Alternativa mais robusta: criar constante `_DADOS_PATH = "Andrei/dadosatuais.json"` em `Andrei/config.py` e referencia-la em todos os modulos.

---

## 8. [MENOR] `atos_judicial.py` define stubs que conflitam com `atos_wrappers.py`

**Arquivo:** `Andrei/atos_judicial.py` linhas 1585-1621

O arquivo define `_make_stub_ato` e 20+ instancias `ato_*` como stubs. `atos_wrappers.py` redefine os mesmos nomes com configuracoes reais. Dois arquivos exportando os mesmos simbolos com valores diferentes e receita para bugs de import.

**Correcao:** Remover `_make_stub_ato` e todas as definicoes `ato_* = _make_stub_ato(...)` de `atos_judicial.py`. Os wrappers reais ja estao corretamente definidos em `atos_wrappers.py`. Nada no pipeline usa esses stubs apos a correcao #1.

---

## 9. [MENOR] `extrair_texto_peticao_via_api` duplicada

**Arquivos:** `Andrei/pipeline.py:267-317` e `Andrei/helpers.py:345-392`

A mesma funcao existe em dois lugares com implementacoes quase identicas. Diferencas:
- `pipeline.py` faz `import pdfplumber` dentro da funcao (lazy)
- `helpers.py` tambem faz import lazy identico
- `helpers.py` usa `from Andrei.api_client import session_from_driver, PjeApiClient` no topo
- `pipeline.py` importa dentro da funcao

**Correcao:** Manter apenas em `pipeline.py` (onde e a implementacao principal usada por `analise_pet`). Em `helpers.py:checar_habilitacao`, trocar a chamada local por `from Andrei.pipeline import extrair_texto_peticao_via_api`. Ou mover a funcao para `extracao.py` e ambos importarem de la.

---

## 10. [MENOR] `str()` redundante em `getattr` com default string

**Arquivo:** `Andrei/helpers.py` — multiplas ocorrencias

```python
numero_processo = str(getattr(item, 'numero_processo', '') or '')
```

`getattr` com default `''` ja garante retorno string. O `str()` e `or ''` sao redundantes. Mesmo padrao no legado. Nao quebra execucao, apenas ruido.

**Correcao (opcional):** Simplificar para `getattr(item, 'numero_processo', '') or ''` (apenas o `or ''` para cobrir casos de atributo existir mas ser `None`).

---

## Resumo para Execucao

| # | Severidade | Arquivo(s) | Acao |
|---|-----------|-----------|------|
| 1 | **CRITICO** | `regras.py:21-50`, `atos_judicial.py:1585-1621` | Trocar imports de `ato_*` para `atos_wrappers`; remover stubs |
| 2 | **CRITICO** | `regras.py:124-127` | Importar `checar_habilitacao`, `agravo_peticao`, `def_quesitos`, `contesta_calc` de `helpers` |
| 3 | **CRITICO** | `helpers.py:610-615` | Corrigir `texto_tuple[0]` → `texto_str` (string, nao tupla) |
| 4 | MODERADO | `extracao.py:329-338` | Portar `criar_gigs` real + `_parse_gigs_string` de `Fix/extracao.py` |
| 5 | MODERADO | `pipeline.py`, novo em `helpers.py` | Portar `consolidar_delete_com_bookmarklet` de `Peticao/suporte_pet.py` |
| 6 | MODERADO | `pipeline.py:587` | Tratar recovery manual em execucao nao supervisionada |
| 7 | MODERADO | `helpers.py` (checar_habilitacao, contesta_calc) | Unificar caminho para `Andrei/dadosatuais.json` |
| 8 | MENOR | `atos_judicial.py:1585-1621` | Remover stubs redundantes |
| 9 | MENOR | `helpers.py:345-392`, `pipeline.py:267-317` | Eliminar duplicacao de `extrair_texto_peticao_via_api` |
