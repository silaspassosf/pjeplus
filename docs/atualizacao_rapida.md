# Atualização rápida do PJe-Calc: o que pode ser feito sem DOM?

**A consulta de cálculos é viável por API para uma sessão autorizada e um `idProcesso` conhecido. A atualização completa, não demonstrada.** O repositório contém clientes para listar cálculos no PJe, mas as fontes examinadas só mostram como abrir o cálculo no PJe-Calc, liquidar, consolidar e enviar usando a interface. Não há base nelas para substituir essas etapas por chamadas de escrita. Análise estática local, orientada por [idx.md](../idx.md); nenhum script foi executado contra o PJe e não houve acesso a produção.

| Etapa | Evidência local | Limite para operar sem DOM |
|---|---|---|
| Identificar o processo e abrir o PJe-Calc | No [atalho AVJT](../AVJT/publicas/pje-paginas.js#L68), `pjeCalcBuscarProcesso` copia o número CNJ e abre `pages/principal.jsf`. No [userscript](../Script/alvara/atualizacao_rapida.user.js#L70), `captureActivation` lê o ID da URL e o CNJ do cabeçalho ou título. | A página JSF é entrada de navegação, não um serviço de atualização. O cliente de consulta não precisa do cabeçalho se já recebe o ID correto. |
| Listar os cálculos do processo | [`PjeApiClient.calculos`](../Fix/variaveis.py#L251) faz `GET /pje-comum-api/api/calculos/processo` com `idProcesso` e paginação. [`latestCalculationNumber`](../Script/alvara/atualizacao_rapida.user.js#L146) consulta a mesma rota com a sessão do navegador e lê `resultado`. | Evidência de leitura, não de liquidação nem de envio. Não demonstra acesso anônimo ou autenticação independente do navegador. |
| Selecionar e abrir o cálculo correto | [Busca AVJT](../AVJT/publicas/pje-calc.js#L30) preenche os seis campos do CNJ. No [userscript](../Script/alvara/atualizacao_rapida.user.js#L213), o número candidato volta ao formulário e o primeiro link “Abrir” é acionado. | O script pede só a primeira página (até 100 itens) e ordena por `dataHoraImportacao` ou `dataLiquidacao`. Isso não resolve paginação, datas inválidas ou empate. A tentativa de usar `idCalculo` na falta de `numeroCalculo` não prova que o número pesquisável e o ID interno sejam equivalentes. |
| Liquidar na data escolhida | [`validateCurrentProcess` e `liquidate`](../Script/alvara/atualizacao_rapida.user.js#L252) conferem o CNJ, acrescentam o marcador à observação, preenchem a data e aguardam “Operação realizada com sucesso.” | Confere o processo, não distingue dois cálculos do mesmo processo. Campos e mensagem são elementos da tela; não especificam método, corpo ou resposta de uma API. |
| Consolidar e enviar ao PJe | [`consolidateAndSend` e `complete`](../Script/alvara/atualizacao_rapida.user.js#L296) aguardam a mensagem de prontidão, acionam o envio e só finalizam diante de “Sucesso!”. | Pronto para envio não significa enviado. O código observa mensagens da interface; não mostra recibo consultável por API, garantia contra duplicidade ou forma de reconciliar um envio sem confirmação. |

**Decisão:** manter a leitura por API separada das ações que alteram o cálculo. Não usar a lista como autorização para agir sobre o primeiro resultado. Um formulário JSF pode gerar requisições HTTP, mas isso não o torna uma API estável: a sequência de requisições, o estado de tela (por exemplo, eventual `ViewState`) e os efeitos de repetir uma ação não estão estabelecidos pelas fontes citadas. Isso limita a conclusão ao que o repositório demonstra, não significa que inexista uma integração oficial.

**O que mudaria a decisão:** obter documentação oficial aplicável à versão instalada ou evidência autorizada e sanitizada de homologação que vincule inequivocamente processo, cálculo e atualização. Antes de propor escrita sem DOM, é preciso conhecer o contrato de cada etapa, as permissões, a confirmação persistente do envio e o comportamento após falha ou repetição. Sem isso, um timeout deve ser tratado como resultado desconhecido, não como sinal para reenviar.

---

## Réplica implementada (execução autônoma via interface)

A rotina do botão `#botao_atualizacaoRapida` do +PJe ([`gigs-plugin.js`](../+pje/PJe-Atual/gigs-plugin.js), ramo `atualizacaorapida`, ~L24076–24396) foi replicada em:

| Arquivo | Papel |
|---|---|
| [`Fix/atualizacao_rapida.py`](../Fix/atualizacao_rapida.py) | Orquestrador Python: `executar_atualizacao_rapida(driver, numero_processo=None, *, data=None, id_calculo=None) -> bool`. Abre aba própria do PJe-Calc, injeta a configuração, executa o motor JS e fecha a aba ao terminar. |
| [`Fix/atualizacao_rapida.js`](../Fix/atualizacao_rapida.js) | Motor DOM (carregado via `carregar_js`): busca o processo, seleciona o cálculo, liquida na data, consolida e envia ao PJe. |
| `x.py` | Fluxo **K** (`executar_atualizacao_rapida_fluxo`), com retry externo de sessão **desligado** para falha pós-envio (`pos_envio`). |
| `pw.py` | Atalho `--atualizacao-rapida <CNJ> [--calculo N] [--data dd/mm/aaaa]`. |

### Diferenças em relação ao +PJe (requisito: finalizar sozinho)

1. **Data atual automática, sem confirmação.** O +PJe abria `criarCaixaDePergunta('data', ...)` exigindo o usuário confirmar a data. A réplica injeta `datetime.now()` (dd/mm/aaaa) direto no campo `formulario:dataDeLiquidacaoInputDate`. `data=` explícito sobrescreve; nunca há prompt.
2. **Sem caixa de seleção de cálculo.** Com um único cálculo, abre-o. Com vários, exige `id_calculo` (número da listagem, comparação exata da célula) — **nunca** escolhe arbitrariamente. Ambiguidade sem `id_calculo` → falha controlada, nada é enviado.
3. **Sucesso só após "Sucesso!" do envio.** `True` apenas quando o `h2` "Sucesso!" aparece. A aba própria é fechada ao terminar.

### Proveniência dos seletores (réplica vs. original)

A maioria é literal do ramo `atualizacaorapida` do [`gigs-plugin.js`](../+pje/PJe-Atual/gigs-plugin.js):

| Seletor | Origem |
|---|---|
| `a.linkSelecionar[title="Abrir"]` | +PJe L24069/24093/24161 |
| `span.box-msg-livre` ("Não existem resultados") | +PJe L24082 |
| `input[id*="numeroCalculoBusca"]` + `formulario:buscar` (filtro) | +PJe L24158–24159 |
| `img[title="Próximo"]` (paginação, alt "desabilitado") | +PJe L24131–24132 |
| `div[id="barraTitulo"]` (estados de tela) | +PJe L24175/24297/24354 |
| `li a` "Liquidar Atualização" | +PJe L24292 |
| `span#formulario:panelDadosCalculo` (conferência CNJ) | +PJe L24309 |
| `textarea#formulario:comentarios` + marcador `MAISPJE: ATUALIZAÇÃO RÁPIDA` | +PJe L24303–24305 |
| `input#formulario:dataDeLiquidacaoInputDate` e `input#formulario:liquidar` | +PJe L24312–24323 — **lidos dentro do frame** (`barraTitulo.parentElement.parentElement`), como o comentário do fonte exige (senão pega o liquidar do menu Operações) |
| `div#divMensagem` ("Operação realizada com sucesso.") | +PJe L24327 |
| `li#li_operacoes_validar_atualizacao a` | +PJe L24329 |
| `input[value="Consolidar Dados"]` | +PJe L24360 |
| `span.rich-messages-label` ("Os dados estão prontos…") | +PJe L24365 |
| `input[value="Enviar para o PJe"]` | +PJe L24367 |
| `input#popup_ok` | +PJe L24371 |
| `h2` "Sucesso!" | +PJe L24380 |

Exceções — pontos onde o +PJe depende de recursos da própria extensão (que não existem sem ela), tomados do userscript/AVJT:

| Seletor/passo | Origem |
|---|---|
| `[title="Buscar Cálculo"]` (entrada na tela de busca) | `AVJT/publicas/pje-calc.js` L5 — o +PJe entra via `#maisPJe_PJECAL_botao_BuscaMemoria1` (L24047) |
| Campos `numeroProcessoBusca/digito/ano/justica/regiao/vara` + `formulario:setor` | `AVJT/publicas/pje-calc.js` L35–43 / userscript L187–204 — o +PJe preenche via memória da extensão |
| Encerramento | O +PJe clica `li[class*="header"]` "Operações" + `.menuImageClose` antes de `window.close()` (L24391–24395); a réplica, autônoma em aba própria, fecha a aba direto |

### Segurança

- Conferência do CNJ no painel `formulario:panelDadosCalculo` antes de liquidar (bug do PJeCalc de abrir cálculo de outro processo).
- A partir do clique em "Enviar para o PJe", qualquer falha é marcada `pos_envio=True` e **não é reenviada** (o orquestrador desliga o retry de sessão para esse caso). Timeout de transporte também é tratado como resultado desconhecido (`pos_envio=True`).
- `id_calculo` é o **número da listagem** do PJe-Calc, não o `idCalculo` REST. O fallback `numeroCalculo ?? idCalculo` do userscript legado **não** é usado como prova de identidade.

### Uso

```powershell
# processo com cálculo único, data atual, headless:
py pw.py --atualizacao-rapida 1001190-87.2024.5.02.0000

# escolhendo o cálculo entre vários:
py pw.py --atualizacao-rapida 1001190-87.2024.5.02.0000 --calculo 2

# data específica (opcional):
py pw.py --atualizacao-rapida 1001190-87.2024.5.02.0000 --data 31/12/2025

# via orquestrador (menu K ou env):
$env:PJEPLUS_DRIVER="PC_HEADLESS"; $env:PJEPLUS_FLUXO="K"; $env:PJEPLUS_AR_PROCESSO="1001190-87.2024.5.02.0000"; py pw.py
```

```python
from Fix.atualizacao_rapida import executar_atualizacao_rapida
ok = executar_atualizacao_rapida(driver, "1001190-87.2024.5.02.0000")  # data atual
```

### Validação offline

- `python -m unittest discover -s tests -p "test_atualizacao_rapida.py"` — 28 testes (motor + integração + elo teimosinha + regressões de navegação SISBAJUD, sem rede/browser).
- `node tests/atualizacao_rapida_dom_harness.js` — máquina de estados DOM simulada (7 cenários: sucesso, seleção por número, sem cálculo, ambiguidade, mais recente, processo errado, pós-envio sem sucesso). Dev-only.

**Não executado contra produção.** A validação é estática/offline; o comportamento real dos seletores JSF deve ser confirmado em homologação antes do primeiro envio real.

---

## Integração no fluxo PEC teimosinha (cálculo antigo)

O gap ">3 meses" já existia inline em `SISB/core.py` (`pendencia = 'calculo_antigo'` quando `divida.data` tem >90 dias), nos dois pontos de detecção: `minuta_bloqueio` (simples) e `minuta_bloqueio_amanha` (dupla — a usada pelo fluxo PEC teimosinha). Antes, só marcava o GIGS `xs resultado CALC` para atualização manual posterior.

Agora, **naquele mesmo ponto**, a atualização roda automaticamente:

```
PEC teimosinha → minuta_bloqueio_amanha (SISB/core.py)
  deteccão: divida.data > 90 dias → pendencia='calculo_antigo'
    └─ _atualizar_calculo_antigo(driver_pje, dados_processo, valor)   [SISB/core.py]
         └─ atualizar_calculo_se_antigo(...)                          [Fix/atualizacao_rapida.py]
              1. executar_atualizacao_rapida_detalhada(driver_pje, CNJ,
                    selecionar_mais_recente=True)  ← data ATUAL, sem confirmação
              2. espera observável (poll 5s, teto 30s) na API
                 GET /pje-comum-api/api/calculos/processo (mesma consulta de
                 extrair_dados_processo: resultado[0], ordenação decrescente)
              3. muta dados_processo['divida'] = {valor, data} novos
    └─ se atualizado e API reflete: pendencia=None → minuta usa o valor novo
       (em _configurar_valor, que lê dados_processo['divida']['valor'])
    └─ se falhou OU API ainda não reflete: mantém 'calculo_antigo'
       → comportamento anterior preservado (GIGS 'xs resultado CALC')
```

Pontos de segurança mantidos:

- **Juntada não é pré-requisito** — a atualização vale por si; se a juntada falhar adiante, o GIGS `xs resultado CALC` continua cobrindo a retomada.
- **Falha pós-envio nunca reenvia** — `AtualizacaoRapidaErro(pos_envio=True)` propaga até a ponte SISB, que mantém o fluxo antigo em vez de repetir.
- **Valor novo só entra se a API o confirmar** — envio confirmado mas API defasada ⇒ dívida anterior mantida (nunca usa valor não confirmado como se fosse novo).
- **Cálculo mais recente = maior número da listagem** (mesma escolha implícita da API `resultado[0]`), nunca um `idCalculo` REST como prova de identidade.

---

## Sobrevivência à navegação do PJe-Calc (por que a 1ª versão falhava)

O `principal.jsf` **navega logo após o carregamento** (redirecionamento JSF/SSO). A primeira versão injetava o motor assim que o `DOMContentLoaded` disparava e morria com `Page.evaluate: Execution context was destroyed` em ~1s, sem tocar em nada (log de 17/11 22:59:56).

O +PJe sobrevive a isso porque guarda o passo em `browser.storage` (`tempAR:passo1/passo2/…`) e **re-roda a cada carga de página**. A réplica faz o equivalente, respeitando a fronteira de segurança:

1. **Assentamento antes de injetar** — `_assentar_aba` espera `load`, controle JSF presente e URL estável por ~1,2 s: o redirecionamento se completa antes do `evaluate` começar.
2. **Espelho de fase em `sessionStorage`** — o motor grava a fase **antes** de agir; `sessionStorage` sobrevive à navegação da mesma aba.
3. **Retomada só quando provadamente sem efeito** — após contexto destruído, o Python lê o espelho: fases até `menu-liquidar` (busca/lista/seleção/abertura) são idempotentes → reassenta e reexecuta (até 2 vezes). De `liquidar` em diante o estado é desconhecido → falha com `pos_envio=True` e **não** reexecuta.

### Modo `somente_busca`

`executar_atualizacao_rapida_detalhada(..., somente_busca=True)` abre o cálculo, confere o CNJ no painel de dados e **para**: nada é liquidado nem enviado. Retorna `fase="somente-busca"` com o número do cálculo. É o modo padrão do teste isolado:

```
py f.py ar                       # processo do caso, só busca (não altera nada)
py f.py ar 6334837 --executar    # atualização real (liquida hoje e envia)
```
