# E10 — Baseline, comparação e decisão

**Leia antes:** `00-contexto.md`.

> Esta é a **única** etapa que exige PJe real. Nenhuma das outras foi validada
> em produção — até aqui tudo é teoria sustentada por testes offline.

## Arquivos exclusivos

```
play/medicoes/**
```

Esta etapa **não edita código de produção**. Se ela precisar mudar código, algo
está errado: registre o achado e abra uma etapa própria.

## Por que ela existe

Sem número, "o Playwright é melhor" é opinião. Pior: parte do ganho vem de ter
*reescrito* as esperas — e isso somaria em qualquer motor. Decidir aposentar o
Selenium com base numa comparação que mistura as duas coisas seria decidir com
dado viciado.

`play/pjeplay/medicao.py` separa:

- `tempo_espera` — dentro do vocabulário `Fix.espera`. Os dois motores rodam o
  **mesmo código**, então a diferença aqui é atribuível ao **motor**.
- `tempo_morto` — `time.sleep` cru que sobrou. Some em qualquer motor: é
  **reescrita**, não Playwright.
- `tempo_helper` — demais helpers de `Fix/`.

## Procedimento

### 1. Isolar um lote reproduzível

Escolha processos que possam ser reprocessados sem efeito colateral. Comece por
**P2B** — é leitura-pesada (timeline → extrai documento → regex → ação) e erra
barato. Depois Petição/Triagem, e só então PEC e Mandado, que escrevem.

Registre a lista de processos: os dois lados precisam rodar **o mesmo lote**.

### 2. Baseline em Selenium

```bash
py play/rodar.py --selenium
```

Grava `play/medicoes/selenium-<timestamp>.json`.

### 3. Mesma coisa em Playwright

```bash
py play/rodar.py
```

Grava `play/medicoes/playwright-<timestamp>.json`.

Para diagnosticar uma falha, acrescente `--trace`: gera um `.zip` navegável com
snapshot de DOM, rede e console **por ação**.

```bash
playwright show-trace play/medicoes/<arquivo>.zip
```

### 4. Comparar

```bash
py play/rodar.py --comparar play/medicoes/selenium-X.json play/medicoes/playwright-Y.json
```

Saída:

```
  total          ...s ->    ...s   (...%)
  em helpers     ...
  em esperas     ...          ← diferença atribuível ao motor
  tempo morto    ...          ← some em qualquer motor: reescrita

  atribuicao do ganho:
    motor: esperas      +...s
    motor: demais       +...s
    reescrita (sleeps)  +...s
    -> N% do ganho e do Playwright
```

### 5. Repetir — e incluir headless

Uma execução não é dado. Rode o mesmo lote **pelo menos 3 vezes em cada
combinação**, alternando a ordem para diluir variação de rede e de carga do PJe:

```
selenium headed  |  playwright headed  |  playwright headless
```

Anote a mediana, não a média — uma execução com timeout de rede distorce a média.

O terceiro cenário responde a uma pergunta separada (ver `04-headless.md`): o
projeto **nunca rodou headless** — `headless=False` em 14 pontos, `True` em
nenhum. Headless só é aprovado se a taxa de falha empatar com a do headed.
Ganho de tempo sem paridade de falha não vale: foi assim que a tentativa
anterior morreu.

## O que também precisa ser observado (e não sai no relatório)

O número mede tempo. A decisão depende também de:

- **Falhas.** Quantos processos falharam de cada lado, e por quê. Um motor 30%
  mais rápido que falha mais não é melhor.
- **Flakiness.** Rodar o mesmo lote 3× e obter resultados diferentes é sinal de
  corrida — anote qual lado varia mais.
- **Comportamento em headless.** O projeto usa headless em parte dos fluxos.
- **SISBAJUD.** Rodar o fluxo PEC→SISB e confirmar que **nenhum bloqueio ou
  CAPTCHA** apareceu com frequência anormal. Se o Playwright disparar detecção
  mais que o Selenium, isso sozinho reprova a migração para esse fluxo.

## Critério de decisão

Só faz sentido aposentar o Selenium se, no lote repetido:

1. o Playwright for consistentemente mais rápido **na parcela atribuída ao
   motor** (não só no total);
2. a taxa de falha for igual ou menor;
3. o SISBAJUD não mostrar sinal de detecção aumentada.

Se (1) for marginal e (2)/(3) forem iguais, a resposta honesta é **manter os
dois** — o custo de manter a camada de compatibilidade é baixo, e ela já
funciona.

## Relatório

```
LOTE          processos: <lista>  | fluxo: <P2B|PEC|Mandado>  | execuções: N por lado
TEMPO         mediana selenium: ...s   mediana playwright: ...s
ATRIBUIÇÃO    motor: ...s   reescrita: ...s   → N% do ganho é do Playwright
FALHAS        selenium: N/N   playwright: N/N   | causas distintas: <lista>
FLAKINESS     variação entre execuções: selenium ±...s  playwright ±...s
SISBAJUD      CAPTCHA/bloqueio observado: sim/não  | frequência comparada
TRACES        <arquivos .zip das execuções que falharam>
RECOMENDAÇÃO  aposentar Selenium | manter os dois | reprovar
              + justificativa em 3 linhas, ancorada nos números acima
```
