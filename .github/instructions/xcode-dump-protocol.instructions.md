---
description: "Protocolo concreto de extracao e formatacao de dumps de funcao para o Xcode Agent. Define o que extrair, como extrair, e o formato de saida para bug.md."
applyTo: "bug.md"
---

# Xcode Dump Protocol — Extracao Eficiente de Funcoes

Este protocolo define COMO o Xcode Agent extrai e formata funcoes para popular a secao 5 (Dump de Funcoes) do `bug.md`.

---

## Principio Zero: Duas Fases (Automatizadas via Script)

O `bug.md` e escrito em **duas fases distintas**:

1. **Fase A — Esqueleto:** o agente escreve secoes 1 a 4 + 6. A secao 5 fica com placeholder exato:
   ```
   ## 5. Dump de Funcoes

   *(a preencher na Fase B)*
   ```

2. **Fase B — Dump automatizado:** o agente gera `dump_config.json` e executa:
   ```bash
   py tools/xcode_dump.py --config dump_config.json --output bug.md
   ```
   O script `tools/xcode_dump.py` implementa este protocolo: localiza funcoes, extrai codigo completo, formata blocos, e substitui o placeholder pelos dumps.

> **Implementacao:** `tools/xcode_dump.py` — ler docstring do script para detalhes de uso.

---

## O Que Extrair (Regra de Inclusao)

Incluir no dump APENAS funcoes que satisfacam PELO MENOS UM destes criterios:

| Criterio | Exemplo |
|---|---|
| A funcao contem a falha suspeita | `safe_click` que suprime `NoSuchElementException` |
| A funcao e chamada diretamente pelo ponto de entrada e tem logica de negocio | `processar_bloqueio()` chamada por `fluxo_sisb()` |
| A funcao esta no caminho cross-module (profundidade 1 ou 2) | `Fix.core.safe_click()` chamada por `atos/wrappers/mov.py` |
| A funcao encapsula um padrao problematico (P1-P8) relevante ao bug | `time.sleep(5)` onde deveria usar `aguardar_renderizacao_nativa` |

**Excluir sempre:**
- `get_module_logger`, `logger.info/debug/error`
- `aguardar_renderizacao_nativa`, `aguardar_angular_*`
- `tempo_execucao`, `medir_tempo`
- Constantes de `Fix/selectorspje.py`
- `scrollIntoView`
- Funcoes com menos de 5 linhas sem logica de decisao (getters, setters, wrappers triviais)

---

## Como Extrair (Processo Mecanico)

### Para cada funcao a incluir no dump:

```
1. Localizar a funcao com precisao:
   a. grep/regex: "^def nome_funcao\(" no arquivo alvo
   b. Confirmar indentacao (top-level vs metodo de classe)

2. Determinar o range exato:
   a. Ler da linha do `def` ate encontrar `^def ` ou `^class ` no mesmo nivel de indentacao
   b. Se a funcao for a ultima do arquivo, ler ate EOF
   c. Anotar: {arquivo} L{inicio}-L{fim} ({fim-inicio+1} linhas)

3. Extrair com read/file usando o range exato:
   read/file {arquivo} startLine={inicio} endLine={fim}

4. Identificar callers e callees (ja feito no Passo 4 do agente):
   - Callers: quem chama esta funcao (do mapeamento cross-module)
   - Callees: quais funcoes externas esta funcao chama (so as relevantes — nao listar logger, sleep, scroll)

5. Se a funcao for muito longa (>80 linhas), adicionar nota:
   "⚠ Funcao longa ({N} linhas). Trecho completo abaixo. Pontos criticos: L{xx}, L{yy}, L{zz}."
```

---

## Formato de Cada Bloco de Dump (Padrao Rigido)

Cada funcao gera UM bloco exatamente neste formato. Sem variacao.

```markdown
### {N}. `{arquivo}` — `{funcao}({params})`

**Range:** L{inicio}-L{fim} ({total} linhas)
**Callers:** `{caller1}`, `{caller2}`
**Callees:** `{callee1}`, `{callee2}`
**Relevancia:** {1 frase dizendo por que esta no dump — "contem a falha suspeita", "chamada cross-module", "padrao P3", etc.}

```python
# {arquivo} L{inicio}-L{fim}
{codigo completo da funcao}
```
```

**Regras de formatacao:**
- Numero sequencial comeca em 1 para cada `bug.md` (nao reinicia por arquivo).
- Parametros da funcao no titulo: apenas os 2-3 primeiros se forem muitos. Ex: `processar(driver, config, ...)`.
- Callers: `modulo/arquivo.py:funcao()` — caminho relativo a raiz do projeto.
- Callees: apenas `modulo.funcao()` — sem caminho de arquivo para nao poluir.
- O bloco de codigo Python DEVE ser o codigo real, lido com `read/file`, nunca reconstruido de memoria.
- Se houver decorators, inclui-los no bloco de codigo.

---

## Ordem dos Dumps

Os dumps sao appendados em ordem de relevancia para o bug:

1. **Funcao com a falha** (ponto exato do problema)
2. **Funcao de entrada** (ponto de contato do usuario com o fluxo)
3. **Callers cross-module** (profundidade 1)
4. **Callees cross-module** (profundidade 2)
5. **Funcoes auxiliares** com padroes problematicos

---

## Exemplo Concreto

### Entrada (Passo 4 mapeou estas funcoes):
- `SISB/helpers.py:extrair_dados_bloqueios_processados()` — entrada
- `SISB/helpers.py:_parse_linha_bloqueio()` — contem falha (regex quebrado)
- `Fix/core.py:safe_click()` — chamada cross-module (P3: suprime excecao)

### Fase A — Esqueleto do bug.md:
```markdown
# Bug Analysis — Bloqueios SISB nao parseados

**Data:** 2026-07-27
**Modulo:** SISB
**Severidade:** bloqueante

---

## 1. Relato Original
> Ao processar bloqueios, os valores monetarios saem zerados no relatorio.

## 2. Pontos de Entrada
| Arquivo | Funcao | Linha | Papel no fluxo |
|---|---|---|---|
| `SISB/helpers.py` | `extrair_dados_bloqueios_processados()` | L890 | Extrai e formata dados de bloqueios |

## 3. Diagnostico

### 3.1 Causa Raiz
O regex `r'R\$ ?(\d+[\.,]?\d*)'` em `_parse_linha_bloqueio()` nao captura valores com notacao brasileira (ponto como separador de milhar + virgula decimal). Alem disso, `safe_click()` em `Fix/core.py` suprime `NoSuchElementException` com `return False`, fazendo o fluxo continuar silenciosamente apos falha de clique no botao "Processar".

### 3.2 Evidencias
- `SISB/helpers.py:L420` — regex nao captura `R$ 1.234,56`
- `Fix/core.py:L150` — `except Exception: return False` (padrao P3)
- O fluxo nao loga falha de parse — valores zerados chegam ao relatorio sem alerta

### 3.3 Impacto
Relatorios de bloqueio com valores zerados. Usuario nao percebe falha ate conferencia manual. Afeta `SISB/helpers.py:gerar_relatorio_bloqueios_processados()` e `gerar_relatorio_bloqueios_conciso()`.

## 4. Correcao Sugerida

### 4.1 Estrategia
Corrigir regex em `_parse_linha_bloqueio()` para capturar notacao brasileira completa (ponto de milhar + virgula decimal). Substituir `return False` em `safe_click()` por `raise ElementoNaoEncontradoError` de `Fix/exceptions.py`. Adicionar log de warning quando valor parseado for zero.

### 4.2 Pontos de Alteracao
1. **`SISB/helpers.py:_parse_linha_bloqueio()`** — trocar regex para `r'R\$ ?([\d\.]*\d+,\d{2})'` com normalizacao pos-match
2. **`Fix/core.py:safe_click()`** — trocar `except Exception: return False` por `raise ElementoNaoEncontradoError(seletor, contexto)`

### 4.3 Riscos
- `safe_click()` e chamado por 40+ locais — alterar assinatura de retorno pode quebrar chamadores que esperam `bool`. Avaliar introducao de `safe_click_or_raise()` como alternativa nao-destrutiva.

## 5. Dump de Funcoes
*(a preencher na Fase B)*

## 6. Ambiente
- **Navegador:** Firefox
- **Headless:** sim
```

### Fase B — Append dos dumps (3 chamadas a insert_edit_into_file):

**Dump 1** (funcao com a falha):
```markdown
### 1. `SISB/helpers.py` — `_parse_linha_bloqueio(linha_texto)`

**Range:** L415-L445 (31 linhas)
**Callers:** `SISB/helpers.py:extrair_dados_bloqueios_processados()`
**Callees:** (nenhuma externa relevante)
**Relevancia:** Contem a falha — regex nao captura notacao brasileira

```python
def _parse_linha_bloqueio(linha_texto):
    import re
    match = re.search(r'R\$ ?(\d+[\.,]?\d*)', linha_texto)
    ...
```
```

**Dump 2** (funcao de entrada):
```markdown
### 2. `SISB/helpers.py` — `extrair_dados_bloqueios_processados(driver, ...)`

**Range:** L890-L980 (91 linhas)
**Callers:** `SISB/core.py:fluxo_sisb()`
**Callees:** `_parse_linha_bloqueio()`, `Fix.core.safe_click()`
**Relevancia:** Ponto de entrada do fluxo — orquestra extracao e chamada as funcoes com falha

```python
def extrair_dados_bloqueios_processados(driver, config=None):
    ...
```
```

**Dump 3** (cross-module com padrao problematico):
```markdown
### 3. `Fix/core.py` — `safe_click(driver, elemento, ...)`

**Range:** L140-L175 (36 linhas)
**Callers:** `SISB/helpers.py:extrair_dados_bloqueios_processados()`, +40 outros
**Callees:** `driver.execute_script()`
**Relevancia:** Padrao P3 — suprime excecao com `return False`, mascarando falha de clique

```python
def safe_click(driver, elemento, tentativas=3):
    try:
        ...
    except Exception:
        return False
```
```

---

## Check de Qualidade do Dump

Antes de finalizar o `bug.md`, verificar:

```
[ ] Cada dump tem range exato (L{inicio}-L{fim})?
[ ] Cada dump tem codigo REAL (read/file), nao reconstruido?
[ ] Callers usam caminho relativo: modulo/arquivo.py:funcao()?
[ ] Callees usam formato curto: modulo.funcao()?
[ ] Ordem: falha → entrada → cross-module → auxiliares?
[ ] Funcoes >80 linhas tem nota de pontos criticos?
[ ] Nenhuma funcao de infraestrutura generica no dump?
[ ] bug.md pode ser lido por alguem sem acesso ao repositorio?
```
