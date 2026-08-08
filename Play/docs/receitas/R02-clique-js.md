# R02 — Clique via JavaScript → clique real com fallback

Tarefa mecânica. Não precisa entender o fluxo. **113 sítios.**

---

## O padrão

O projeto clica por JavaScript em 113 lugares:

```python
driver.execute_script("arguments[0].click();", elemento)
```

Isso dispara o evento de clique **sem checar nada**: sem ver se o elemento está
visível, habilitado, ou coberto por outro. Funciona sempre — inclusive quando
não deveria, o que esconde bug.

A troca usa `safe_click_no_scroll`, que tenta o clique real primeiro e **cai
para exatamente este mesmo clique por JavaScript** se o real falhar. Ou seja: no
pior caso o comportamento é idêntico ao de hoje; no melhor, ganha a verificação.

---

## ANTES

```python
driver.execute_script("arguments[0].click();", elemento)
```

Variações que também contam (o nome da variável muda, o resto não):

```python
driver.execute_script("arguments[0].click();", botao)
driver.execute_script("arguments[0].click()", el)
self.driver.execute_script("arguments[0].click();", elemento)
```

## DEPOIS

```python
safe_click_no_scroll(driver, elemento)
```

Mantendo o mesmo objeto de driver e o mesmo nome de variável do elemento:

```python
safe_click_no_scroll(self.driver, botao)
```

## Import necessário

No topo do arquivo (só se ainda não houver):

```python
from Fix.core import safe_click_no_scroll
```

Se o arquivo já importa de `Fix.core`, **acrescente o nome à lista existente**
em vez de criar uma linha nova.

---

## Encontrar os candidatos

```bash
grep -rn 'execute_script("arguments\[0\]\.click()' --include=*.py Fix atos PEC Prazo Mandado SISB
```

```bash
grep -rn "execute_script('arguments\[0\]\.click()" --include=*.py Fix atos PEC Prazo Mandado SISB
```

---

## NÃO aplique quando

Pule e anote, sem tentar adaptar:

1. **O caminho contém `SISB/Core/`.** Proibido, sem exceção.
2. **A linha está dentro de `safe_click_no_scroll` ou de `safe_click`.** Seria
   recursão infinita. Verifique se a função que contém a linha tem um desses
   nomes.
3. **O script faz mais do que clicar.** Se houver qualquer coisa além de
   `arguments[0].click();` dentro das aspas — por exemplo
   `"arguments[0].scrollIntoView(); arguments[0].click();"` — **pule**.
4. **O retorno é usado.** Se a linha for `resultado = driver.execute_script(...)`
   ou estiver dentro de um `if`, **pule**.
5. **Há mais de um argumento.** Se for
   `execute_script("...", elemento, outro)`, **pule**.
6. **O elemento não é uma variável simples.** Se for
   `execute_script("arguments[0].click();", driver.find_element(...))`, **pule**.

Na dúvida, pule. Pular é resultado correto.

---

## Validação

Para cada arquivo que você alterou:

```bash
python -m py_compile <arquivo>
```

E no fim, sempre:

```bash
py play/smoke.py --projeto
```

Precisa terminar em **91/91**. Se der menos, desfaça a última alteração e
reporte.

```bash
git diff --name-only SISB/Core/
```

Precisa sair **vazio**.

---

## Relatório

Uma linha por troca:

```
<arquivo>:<linha>  ok
```

Uma linha por pulo, com o número da regra:

```
<arquivo>:<linha>  pulado — regra 3 (script faz mais que clicar)
```

E no fim:

```
trocados: N    pulados: N    total encontrado: N
smoke: __/91
py_compile: ok
diff SISB/Core: vazio
```
