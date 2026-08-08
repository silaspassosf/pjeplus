# Prompt do orquestrador (sessão nova, com agentes)

Para uma sessão do Claude Sonnet que vai despachar agentes. Diferente do
`PROMPT-JANELA.md`, que serve para janelas de chat manuais sem agentes.

Com agentes dá para rodar **8 etapas em paralelo**, não 3 — a partição de
arquivos suporta isso.

---

## Ordem de execução

```
1. E1                      sozinha    — fecha o vocabulário de espera
2. E2 E3 E4 E5 E6 E7 E8 E9 paralelo   — 8 agentes, arquivos disjuntos
3. R02                     sozinha    — varre todos os diretórios
4. R01, R03                sequencial — dependem de E3 e E9
5. E10                     manual     — precisa de PJe real, não é agente
```

R01/R02/R03 varrem o escopo inteiro, então **não** podem correr junto com
E2–E8 nem entre si.

## Modelo por etapa (o que define o custo)

| Etapa | Modelo | Por quê |
|---|---|---|
| E1 | **sonnet** | refatora dependência circular e projeta funções novas |
| E2–E9 | **sonnet** | cada sítio exige decidir a condição pelo contexto |
| R01, R02, R03 | **haiku** | reconhecimento de forma, antes/depois literal |

Não use Opus em nenhuma: o plano já está decidido, sobra execução.

Não use `ceo`/`cto`: o `CLAUDE.md` manda passar por eles em pedido não-trivial,
mas aqui a decomposição **já está feita nos documentos**. Fazer a diretoria
re-derivar o plano é custo puro.

---

## O prompt

````
Projeto PJePlus em D:\PjePlus — automação do PJe em Selenium. Estou migrando o
motor de browser para Playwright. O plano JÁ ESTÁ DECIDIDO e documentado; sua
função é orquestrar a execução, não replanejar.

LEIA APENAS ISTO ANTES DE COMEÇAR:
  play/docs/03-etapas.md        (mapa de etapas e propriedade de arquivos)
  play/docs/PROMPT-ORQUESTRADOR.md  (ordem, modelos e protocolo)

Não leia código. Não leia os docs das etapas — quem lê é o agente de cada uma.
Não acione os agentes `ceo` nem `cto`: a decomposição já existe.

PROTOCOLO

Passo 1 — despache UM agente para a etapa E1, modelo sonnet, e AGUARDE.
E1 fecha o vocabulário de espera; sem ela as outras travam em vários sítios.

Passo 2 — quando E1 terminar, despache OITO agentes SIMULTANEAMENTE, todos
modelo sonnet, um para cada etapa: E2, E3, E4, E5, E6, E7, E8, E9.
Os conjuntos de arquivos são disjuntos — não há conflito. Despache todos numa
única mensagem.

Passo 3 — quando as oito terminarem, despache a receita R02, modelo haiku.
Ela varre todos os diretórios, então roda sozinha.

Passo 4 — depois, R01 e R03, modelo haiku, uma de cada vez.

Passo 5 — pare e me reporte. A etapa E10 é minha: exige PJe real.

PROMPT PARA CADA AGENTE (troque <ETAPA> e o tipo)

  Para E1–E9, subagent_type "senior-dev-backend":

    Execute a etapa <ETAPA> da migração Playwright do PJePlus (D:\PjePlus).

    Leia nesta ordem, e nada além disso:
      1. play/docs/00-contexto.md
      2. play/docs/02-esperas.md
      3. play/docs/etapas/<ETAPA>.md
      4. play/docs/01-traducao.md  (consulta, conforme a necessidade)

    Execute até o fim o que o documento da etapa manda.

    Cinco regras acima de qualquer instinto:
    1. O `teto` de uma conversão é EXATAMENTE o valor que já estava no código.
       Nunca aumente, nunca diminua.
    2. Só converta quando o código adjacente revelar a condição sem ambiguidade,
       usando o MESMO seletor que ele já usa. Não invente seletor.
    3. Na dúvida, DEIXE COMO ESTÁ. Deixar é resultado correto, não fracasso.
    4. Edite SOMENTE os arquivos que a sua etapa declara como exclusivos. Outros
       agentes estão em outros arquivos AGORA. Editar fora do seu conjunto
       corrompe o trabalho deles.
    5. Se precisar de função que ainda não existe em Fix/espera.py, PARE naquele
       sítio e reporte. Não a implemente.

    SISB/Core/ é proibido, sem exceção.

    Valide antes de reportar:
      python -m py_compile <cada arquivo tocado>
      py play/smoke.py --projeto        (precisa dar 91/91)
      py play/guarda.py                 (precisa sair 0)
      git diff --name-only SISB/Core/   (precisa sair vazio)

    Se qualquer um falhar, conserte antes de reportar. Não commite.
    Entregue o relatório no formato que o documento da etapa define.

  Para R01/R02/R03, subagent_type "pjeplus-surgeon", modelo haiku:

    Tarefa mecânica no projeto PJePlus (D:\PjePlus).

    Leia play/docs/receitas/<RECEITA>.md e execute exatamente o que ele manda.
    Ele é autossuficiente: não leia mais nada.

    1. Aplique a troca SOMENTE onde o código bater EXATAMENTE com o bloco
       "ANTES". Parecido não conta — pule e anote.
    2. Não altere nenhuma outra linha. Não reformate. Não renomeie.
    3. Não invente seletor, variável nem parâmetro.
    4. Nunca toque em nada dentro de SISB/Core/.
    5. Na dúvida, PULE. Pular é resultado correto.

    Rode a validação que a receita indica e cole a saída. Não commite.

AO RECEBER OS RELATÓRIOS

Consolide e me entregue, sem enfeite:
  - por etapa: quantas conversões, quantas deixadas, smoke passou ou não
  - a lista agregada de "bloqueado por E1" — se aparecer algo depois de E1 ter
    rodado, falta função no vocabulário e vale uma etapa curta
  - qualquer agente que tenha reportado smoke < 91/91 ou diff não-vazio em
    SISB/Core/ — isso é falha, não detalhe

Se um agente falhar, NÃO tente refazer o trabalho dele você mesmo. Reporte.

NÃO COMMITE NADA. Eu reviso antes.
````

---

## Se der rate limit no meio

O estado é recuperável: cada etapa é independente e o `git diff` mostra o que já
foi feito. Numa sessão nova, despache só as etapas que ainda não rodaram.

Para saber quais faltam:

```bash
git diff --stat
```

E, se preferir tocar sem agentes, o `PROMPT-JANELA.md` tem a mesma coisa dividida
em 3 janelas manuais.
