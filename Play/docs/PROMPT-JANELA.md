# Modelo de prompt — uma janela por trilha

Copie o bloco, troque `<ETAPA>` e cole na janela nova. Nada mais é necessário:
a janela lê os documentos sozinha.

---

## Antes de abrir as 3 janelas: rode E1 sozinha

E1 fecha o vocabulário de espera (`espera.elemento`, `elementos`, `ate_url`,
`ate_abas`, `ate_obsoleto` ainda não existem). Se as três janelas começarem
juntas, E2–E9 vão esbarrar nessas funções e ter de parar em vários sítios.

E1 é curta. Rode-a primeiro, sozinha, e só então abra as três. Isso elimina a
única dependência entre etapas.

---

## As três trilhas

Dentro de uma trilha, execute em ordem. Entre trilhas, não há ordem — e não há
conflito de arquivo.

| Janela | Etapas, em ordem | Arquivos | Volume |
|---|---|---|---|
| **1** | E2 → E3 | `Fix/utils.py`, `Fix/extracao.py`, `Fix/browser_suporte.py` | 42 waits, 44 EC, 11 sleeps |
| **2** | E4 → E7 → E9 | `atos/**`, `Prazo/**`, `Fix/variaveis.py` | 95 waits, 93 EC, 18 sleeps |
| **3** | E5 → E6 → E8 | `PEC/**`, `Mandado/**`, `SISB/**` (não-`Core/`) | 76 waits, 94 EC, 27 sleeps |

E10 (baseline) vem depois das três, e precisa de PJe real.

---

## O prompt

```
Projeto PJePlus em D:\PjePlus — automação do PJe. Estou migrando o motor de
browser de Selenium para Playwright.

Você vai executar UMA etapa da migração. Outras janelas estão executando outras
etapas AGORA, em paralelo, em arquivos diferentes. Por isso a regra mais
importante é: edite SOMENTE os arquivos que a sua etapa declara como exclusivos.
Editar qualquer outro arquivo corrompe o trabalho das outras janelas.

Leia nesta ordem, antes de qualquer coisa:

  1. play/docs/00-contexto.md      — arquitetura, proibições, garantias
  2. play/docs/02-esperas.md       — o vocabulário de espera
  3. play/docs/etapas/<ETAPA>.md   — a sua etapa
  4. play/docs/01-traducao.md      — consulta, conforme a necessidade

Execute a etapa até o fim, seguindo o que o documento dela manda.

Cinco regras que valem acima de qualquer instinto:

  1. O `teto` de uma conversão é EXATAMENTE o valor que já estava no código.
     Nunca aumente, nunca diminua. É o que garante que a troca nunca piore.
  2. Só converta quando o código adjacente revelar a condição sem ambiguidade,
     usando o MESMO seletor que ele já usa. Não invente seletor.
  3. Na dúvida, DEIXE COMO ESTÁ. Deixar é resultado correto, não fracasso.
     Prefiro 20 conversões certas a 60 chutadas.
  4. SISB/Core/ é proibido. É onde mora a evasão de detecção do SISBAJUD
     (sistema do CNJ) — encurtar aquelas esperas pode causar bloqueio.
  5. Se precisar de uma função que ainda não existe em Fix/espera.py, PARE
     naquele sítio e reporte. Não a implemente: aquele arquivo é de outra etapa.

Ao terminar, rode e cole a saída:

  python -m py_compile <cada arquivo que você tocou>
  py play/smoke.py --projeto        # precisa dar 91/91
  py play/guarda.py                 # precisa sair 0
  git diff --name-only SISB/Core/   # precisa sair vazio

Se qualquer um desses falhar, conserte antes de reportar. Depois entregue o
relatório no formato que o documento da etapa define.

Não commite nada. Eu reviso antes.
```

---

## Encadeando etapas na mesma janela

Ao terminar uma etapa, para seguir para a próxima da trilha:

```
Etapa concluída. Agora execute play/docs/etapas/<PRÓXIMA>.md, com as mesmas
cinco regras e a mesma validação ao final. Confirme antes que os arquivos
exclusivos da etapa nova não conflitam com o que você já tocou.
```

---

## O que fazer com o relatório

Cada etapa devolve, entre outras coisas, duas listas que importam:

- **`bloqueado por E1`** — sítios que precisaram de função ainda inexistente.
  Se E1 já rodou e mesmo assim apareceu algo aqui, é sinal de que falta uma
  função no vocabulário. Vale uma etapa curta própria.
- **`deixados`** — agrupados por motivo. É onde se vê se a janela foi
  conservadora demais ou de menos. Um `deixados` cheio de "sem seletor
  adjacente" é saudável; cheio de "não entendi" pede revisão.

Nada disso vira verdade até **E10** medir contra o PJe real.
