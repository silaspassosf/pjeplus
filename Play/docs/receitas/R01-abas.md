# R01 — Abrir aba sem corrida

Tarefa mecânica. **11 sítios.**

> ⚠️ **Pré-requisito.** Esta receita só pode ser executada se a função
> `abrir_em_nova_aba` já existir em `Fix/browser_suporte.py` (entregue pela
> etapa E3). Confirme antes de qualquer coisa:
>
> ```bash
> grep -n "def abrir_em_nova_aba" Fix/browser_suporte.py
> ```
>
> Se não retornar nada, **pare e reporte "E3 ainda não rodou"**. Não implemente
> a função — ela pertence a outra tarefa.

---

## O padrão

Para trabalhar numa aba que um clique abre, o código hoje lê os handles antes,
clica, e procura o handle novo depois:

```python
aba_original = driver.current_window_handle
botao.click()
nova_aba = trocar_para_nova_aba(driver, aba_original)
```

Isso tem uma corrida real: se a aba abre e fecha entre as duas leituras, o
handle nunca é visto e o código segue achando que nada abriu.

A troca arma a escuta **antes** do clique, então a aba não pode passar
despercebida.

---

## ANTES

```python
aba_original = driver.current_window_handle
<UMA LINHA que clica>
nova_aba = trocar_para_nova_aba(driver, aba_original)
```

O nome das variáveis muda de arquivo para arquivo. O que precisa bater é a
**sequência de três passos**: ler o handle atual → clicar → chamar
`trocar_para_nova_aba` (ou `aguardar_nova_aba`) com esse handle.

## DEPOIS

```python
aba_original = driver.current_window_handle
nova_aba = abrir_em_nova_aba(driver, lambda: <A MESMA LINHA que clicava>)
```

Exemplo concreto:

```python
# antes
aba_original = driver.current_window_handle
botao_abrir.click()
nova_aba = trocar_para_nova_aba(driver, aba_original)

# depois
aba_original = driver.current_window_handle
nova_aba = abrir_em_nova_aba(driver, lambda: botao_abrir.click())
```

A linha do clique vai inteira para dentro do `lambda:`, sem alteração nenhuma.
`aba_original` continua existindo — outras linhas depois costumam usá-la.

## Import necessário

No topo do arquivo, só se ainda não houver:

```python
from Fix.browser_suporte import abrir_em_nova_aba
```

Se o arquivo já importa de `Fix.browser_suporte`, **acrescente o nome à lista
existente**.

---

## Encontrar os candidatos

```bash
grep -rn "trocar_para_nova_aba(\|aguardar_nova_aba(" --include=*.py Fix atos PEC Prazo Mandado SISB
```

Ignore as linhas em `Fix/browser_suporte.py` — é onde as funções são definidas.

---

## NÃO aplique quando

Pule e anote:

1. **O caminho contém `SISB/Core/`.** Proibido.
2. **A linha é uma definição** (`def trocar_para_nova_aba`) e não uma chamada.
   Atenção: existe uma segunda definição em `Fix/extracao.py`, além da de
   `Fix/browser_suporte.py`. Nenhuma das duas é para ser tocada aqui.
3. **Entre o clique e o `trocar_para_nova_aba` há outras linhas.** A receita só
   vale para os três passos seguidos. Se houver qualquer coisa no meio, **pule**.
4. **A ação que abre a aba não é uma linha só.** Se forem duas ou mais linhas,
   **pule** — não tente montar uma função.
5. **`trocar_para_nova_aba` é chamada sem um clique imediatamente antes.**
   Alguns lugares a chamam para recuperar uma aba já aberta. **Pule.**

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
