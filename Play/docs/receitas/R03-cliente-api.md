# R03 — Cliente de API adequado ao motor

Tarefa mecânica. **11 sítios.**

> ⚠️ **Pré-requisito.** Esta receita só pode ser executada se `cliente_para` já
> existir em `Fix/variaveis.py` (entregue pela etapa E9). Confirme antes:
>
> ```bash
> grep -n "def cliente_para" Fix/variaveis.py
> ```
>
> Se não retornar nada, **pare e reporte "E9 ainda não rodou"**. Não implemente
> a função — ela pertence a outra tarefa.

---

## O padrão

Para falar com a API do PJe, o código monta uma sessão HTTP copiando os cookies
do browser:

```python
sess, trt = session_from_driver(driver)
client = PjeApiClient(sess, trt)
```

Isso funciona, mas a sessão copiada **envelhece**: se o browser fizer re-login,
os cookies copiados continuam os antigos e as chamadas passam a falhar.

`cliente_para` resolve escolhendo o caminho certo conforme o motor — no
Playwright usa a sessão do próprio browser, então re-login vale na hora. No
Selenium faz exatamente o que já fazia.

---

## ANTES

```python
sess, trt = session_from_driver(driver)
client = PjeApiClient(sess, trt)
```

Os nomes das variáveis mudam de arquivo para arquivo (`sess`/`session`,
`trt`/`trt_host`/`host`, `client`/`cliente`/`api`). O que precisa bater é a
**sequência de duas linhas**: chamar `session_from_driver` e usar o resultado
para construir um `PjeApiClient`.

## DEPOIS

```python
client = cliente_para(driver)
```

Uma linha só. Mantenha o nome que a variável do cliente já tinha:

```python
# antes
session, trt_host = session_from_driver(driver)
api = PjeApiClient(session, trt_host)

# depois
api = cliente_para(driver)
```

## Import necessário

`cliente_para` fica no mesmo módulo que `session_from_driver`, então
normalmente basta acrescentar o nome ao import que já existe:

```python
from Fix.variaveis import cliente_para
```

Se o arquivo já importa de `Fix.variaveis`, **acrescente à lista existente**.

Se `session_from_driver` e `PjeApiClient` deixarem de ser usados no arquivo,
remova-os do import. Se ainda forem usados em outro ponto, **mantenha**.

---

## Encontrar os candidatos

```bash
grep -rn "session_from_driver(" --include=*.py Fix atos PEC Prazo Mandado SISB
```

Ignore as linhas em `Fix/variaveis.py` — é onde a função é definida.

---

## NÃO aplique quando

Pule e anote:

1. **O caminho contém `SISB/Core/`.** Proibido.
2. **A linha é a definição** (`def session_from_driver`) e não uma chamada.
3. **A sessão é usada para outra coisa além de construir o `PjeApiClient`.**
   Se `sess` aparecer em qualquer outra linha — `sess.get(...)`,
   `sess.headers`, passada a outra função — **pule**. `cliente_para` devolve o
   cliente, não a sessão.
4. **Um `grau` diferente do padrão é passado**, por exemplo
   `session_from_driver(driver, grau=2)`. **Pule** — não tente adivinhar como
   repassar o parâmetro.
5. **As duas linhas não estão seguidas.** Se houver qualquer coisa entre elas,
   **pule**.
6. **`trt_host` é usado por conta própria** em outra linha (montar URL, log).
   **Pule** — ele deixaria de existir.

A regra 3 e a regra 6 são as que mais aparecem. Leia as linhas seguintes antes
de trocar.

Na dúvida, pule.

---

## Validação

Para cada arquivo alterado:

```bash
python -m py_compile <arquivo>
```

Sempre, no fim:

```bash
py play/smoke.py --projeto
```

Precisa dar **91/91**.

```bash
git diff --name-only SISB/Core/
```

Precisa sair **vazio**.

---

## Relatório

```
<arquivo>:<linha>  ok
<arquivo>:<linha>  pulado — regra N (motivo)
```

```
trocados: N    pulados: N    total encontrado: N
smoke: __/91   py_compile: ok   diff SISB/Core: vazio
```
