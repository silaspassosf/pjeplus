# E9 — Pontos de entrada da API nativa (`Fix/variaveis.py`)

**Leia antes:** `00-contexto.md`, `01-traducao.md` §6.

## Arquivo exclusivo

```
Fix/variaveis.py
```

Só este. Não edite `play/pjeplay/api.py` (já está pronto) nem os chamadores nos
fluxos.

## Ponto de partida

**A ponte de sessão já funciona e não precisa de nada.**
`session_from_driver(driver, grau=1)` usa apenas `driver.get_cookies()` e
`driver.current_url` — ambos implementados pelo `PWDriver`. Nos dois motores ela
devolve `(requests.Session, trt_host)` corretamente. Isto está coberto por teste
no `smoke`.

Ou seja: **não escreva `session_from_page`.** Ela seria redundante.

## O que esta etapa faz

`play/pjeplay/api.py` já oferece o caminho nativo:

```python
api.requisicao(driver)        # APIRequestContext — auth compartilhada, sem
                              # copiar cookie; re-login no browser vale na hora
api.obter_json(driver, url)
api.esperar_resposta(driver, padrao, acao)     # aguarda o XHR de verdade
api.esperar_conclusao(driver, padrao, acao)    # bool
api.registrar_trafego(driver, filtro)          # diagnóstico
```

O problema: `Fix/variaveis.py` (o `PjeApiClient`, ~66 pontos de uso) só sabe
falar `requests.Session`. Esta etapa cria a ponte **sem quebrar nada**.

### Tarefa

Acrescente a `Fix/variaveis.py` um cliente alternativo com a **mesma superfície
pública** do `PjeApiClient`, mas que use `api.requisicao(driver)` quando o
driver for um `PWDriver`, e caia para `requests.Session` caso contrário.

```python
def cliente_para(driver, grau=1):
    """Devolve um cliente de API adequado ao motor corrente.

    Playwright: usa o APIRequestContext do contexto do browser — a sessão é a
    mesma da aba, então um re-login vale imediatamente e não há cookie copiado
    envelhecendo.
    Selenium: `session_from_driver` + `PjeApiClient`, como sempre.
    """
```

Requisitos:

- **Nenhum chamador existente pode mudar de comportamento.** `PjeApiClient` e
  `session_from_driver` continuam exatamente como estão.
- A detecção do motor não pode importar `pjeplay` no topo (`Fix/` não conhece
  `play/`). Use duck typing: `hasattr(driver, "page")` e
  `hasattr(driver, "context")`.
- Import de `pjeplay.api` só dentro da função, e dentro de `try/except
  ImportError` — em execução Selenium pura o `play/` pode nem estar no
  `sys.path`.
- Se qualquer coisa falhar, caia para o caminho `requests`. Nunca levante.

### Opcional, se sobrar espaço

Documente (em docstring) quais chamadas de `PjeApiClient` são candidatas a
`api.esperar_resposta` — os pontos em que o fluxo hoje clica e depois adivinha
pelo DOM que o XHR terminou. **Não** altere os fluxos: eles pertencem a E5–E8.

## Regras

- Não mude assinatura nem comportamento do que já existe.
- Não edite fluxos.
- `Fix/variaveis.py` não pode passar a depender de `play/` em tempo de import.

## Validação

```bash
python -m py_compile Fix/variaveis.py
```

```bash
python -c "import Fix.variaveis; print('OK')"
```

Sem `play/` no path (garante que a dependência é opcional de verdade):

```bash
python -c "import sys; sys.path=[p for p in sys.path if 'play' not in p]; import Fix.variaveis; print('OK sem play')"
```

```bash
py play/smoke.py --projeto
```

## Relatório

```
cliente_para implementado: sim/não
Fix/variaveis.py importa sem play/ no path: sim/não
chamadores alterados: DEVE SER ZERO
candidatos a esperar_resposta documentados: <lista, sem alterar fluxo>
VALIDAÇÃO smoke: __/91 | py_compile: ok | imports: ok
```
