Você está certo. A fase 1 não precisa antecipar todos os campos internos do SISCONDJ. Ela deve entregar apenas o **tipo de operação**, o **destinatário**, os **dados já conhecidos**, o **valor** e, quando houver, o **ID do depósito**. A fase 2 usará essas informações para escolher o fluxo correspondente dentro do SISCONDJ; o próprio sistema exibirá os campos adicionais conforme a finalidade selecionada. [tjrj.jus](https://www.tjrj.jus.br/documents/10136/228498448/Manual-SISCONDJ-Geral-Administrador-Geral-v1-2.pdf)

# Ajuste da fase 1

## Tipos de alvará

A fase 1 deverá trabalhar com estes tipos:

```text
Crédito do exequente
INSS
Custas
Honorários advocatícios
Honorários periciais
Devolução à reclamada
Transferência para outro processo
```

Além dos tipos lidos automaticamente na decisão, o overlay deverá permitir inserir manualmente qualquer tipo por meio do botão:

```text
Adicionar tipo
```

A seleção manual deverá usar os mesmos cards e campos dos itens extraídos automaticamente.

***

# Estrutura mínima de cada item

Cada alvará deverá possuir apenas:

```text
id
tipo
valor
destinatarioTipo
destinatarioNome
destinatarioDocumento
dados
deposito
observacao
origem
```

## Campos comuns

```text
id
tipo
valor
observacao
origem
```

`origem` deverá indicar se o item foi:

```text
extraído da decisão
adicionado manualmente
```

## Destinatário

Quando houver destinatário, usar:

```text
destinatarioTipo
destinatarioNome
destinatarioDocumento
```

Tipos possíveis:

```text
exequente
reclamante
reclamada
advogado
escritorio
perito
outro
```

## Dados bancários

Manter apenas quando o tipo de operação envolver crédito em conta:

```text
dados:
  banco
  agencia
  conta
  tipoConta
```

Não criar dados bancários para:

```text
INSS
Custas
Transferência para outro processo
```

salvo se algum campo específico for necessário posteriormente no SISCONDJ.

## Depósito

Quando o item estiver vinculado a um depósito judicial:

```text
deposito:
  id
  banco
  valor
```

Se o valor depender de consulta posterior:

```text
deposito:
  id
  banco
  valor: ''
  pendenteConsulta: true
```

***

# Tipos automáticos

## Crédito do exequente

### Identificação

Criar automaticamente quando a decisão indicar liberação:

```text
libere-se ao exequente
libere-se ao reclamante
libere-se ao autor
libere-se ao demandante
libere-se em favor do exequente
libere-se em favor do reclamante
libere-se em favor do autor
libere-se em favor do demandante
```

### Campos do card

```text
tipo: Crédito do exequente
valor
destinatarioTipo
destinatarioNome
destinatarioDocumento
dados:
  banco
  agencia
  conta
  tipoConta
deposito:
  id
  banco
  valor
```

### Opções de destinatário

O campo de destinatário deverá permitir:

```text
Transferência para conta do advogado
Conta escritório
Conta reclamante
```

A fase 2 decidirá no SISCONDJ se será crédito em conta do Banco do Brasil, crédito em outros bancos ou comparecimento ao banco, de acordo com a opção escolhida e os dados bancários existentes. [tjrj.jus](https://www.tjrj.jus.br/documents/10136/228498448/Manual-SISCONDJ-Geral-Administrador-Geral-v1-2.pdf)

***

## INSS

### Identificação

Criar automaticamente quando a decisão apresentar contribuição previdenciária ou INSS.

### Campos do card

```text
tipo: INSS
valor
destinatarioTipo: órgão arrecadador
destinatarioNome: INSS
destinatarioDocumento: vazio
dados: null
deposito: null
```

### Tipo fixo

```text
DARF
```

O campo de dados bancários não deverá aparecer.

A fase 2 selecionará a finalidade DARF no SISCONDJ e preencherá os campos que o sistema apresentar. [trt20.jus](https://www.trt20.jus.br/download/siscondj/Manual%20do%20Usu%C3%A1rio.pdf)

***

## Custas

### Identificação

Criar automaticamente quando a decisão mencionar custas com valor.

### Campos do card

```text
tipo: Custas
valor
destinatarioTipo: órgão arrecadador
destinatarioNome: Justiça
destinatarioDocumento: vazio
dados: null
deposito: null
```

### Tipo fixo

```text
GRU
```

O campo de dados bancários não deverá aparecer.

A fase 2 selecionará GRU no SISCONDJ ou seguirá o fluxo de GRU adotado no ambiente correspondente.

***

## Honorários advocatícios

### Identificação

Criar automaticamente quando a decisão apresentar honorários advocatícios.

### Campos do card

```text
tipo: Honorários advocatícios
valor
destinatarioTipo
destinatarioNome
destinatarioDocumento
dados:
  banco
  agencia
  conta
  tipoConta
deposito: null
```

### Opções de destinatário

```text
Conta do advogado autor
Conta escritório
```

O campo deverá possuir o botão:

```text
Puxar do SISCON
```

A fase 2 utilizará os dados selecionados para preencher o fluxo de crédito em conta.

***

## Honorários periciais

### Identificação

Criar automaticamente quando a decisão indicar honorários periciais, técnicos, médicos ou contábeis.

### Campos do card

```text
tipo: Honorários periciais
valor
destinatarioTipo: perito
destinatarioNome
destinatarioDocumento
dados:
  banco
  agencia
  conta
  tipoConta
deposito: null
```

### Destinatário

O campo deverá ser um seletor de perito:

```text
Selecione o perito
```

Inicialmente, manter o placeholder da planilha futura.

Não incluir botão “Puxar do SISCON” para o perito nesta etapa.

***

# Novo tipo: Devolução à reclamada

## Quando adicionar automaticamente

Criar esse tipo quando a decisão indicar:

```text
devolução à reclamada
devolva-se à reclamada
restituição à reclamada
liberação em favor da reclamada
devolução do depósito recursal
restituição do depósito recursal
```

A detecção deverá também considerar expressões equivalentes que indiquem que o depósito será devolvido à parte reclamada.

## Campos do card

```text
tipo: Devolução à reclamada
valor
destinatarioTipo: reclamada
destinatarioNome
destinatarioDocumento
dados:
  banco
  agencia
  conta
  tipoConta
deposito:
  id
  banco
  valor
  pendenteConsulta
```

## Destinatário

O campo deverá permitir:

```text
Conta da reclamada
Conta do procurador da reclamada
Conta escritório da reclamada
```

O usuário deverá poder preencher ou selecionar:

```text
Nome
CPF ou CNPJ
Banco
Agência
Conta
Tipo de conta
```

Deixar também disponível:

```text
Puxar do SISCON
```

A fase 2 usará esses dados para preencher o beneficiário e os dados bancários no fluxo de crédito em conta.

## Depósito recursal

Quando a decisão mencionar um ID de depósito recursal:

- Salvar o ID.
- Salvar o banco mencionado.
- Deixar o valor vazio quando não estiver na decisão.
- Exibir indicação de valor pendente.
- Permitir edição manual do valor.
- Manter o ID para localização posterior no SISCONDJ.

A fase 2 deverá localizar o depósito pelo ID, conferir o saldo e decidir entre valor total ou valor informado conforme o valor salvo no card e a determinação da decisão.

***

# Novo tipo: Transferência para outro processo

## Quando adicionar automaticamente

Criar esse tipo quando a decisão indicar:

```text
transfira-se para outro processo
transferência para outro processo
transfira-se o valor para os autos
realize-se novo depósito
depósito em outro processo
transfira-se para a conta judicial do processo
```

Também considerar expressões que indiquem transferência entre contas judiciais.

## Campos do card

```text
tipo: Transferência para outro processo
valor
destinatarioTipo: processo_destino
destinatarioNome
destinatarioDocumento
dados: null
deposito:
  id
  banco
  valor
  pendenteConsulta
transferencia:
  processoDestino
  tribunalDestino
  unidadeDestino
```

## Campos adicionais

O card deverá apresentar:

```text
Número do processo de destino
Tribunal de destino
Unidade judicial de destino
Observações
```

O campo “Número do processo de destino” deverá ser editável.

Os demais campos poderão permanecer vazios até o preenchimento manual.

## Regra

Não exibir campos de:

```text
Banco
Agência
Conta
```

A operação será tratada na fase 2 como transferência ou novo depósito judicial, conforme as opções disponíveis no SISCONDJ.

O SISCONDJ possui fluxo próprio para novo depósito judicial em outro processo, inclusive com possibilidade de transferência para processo do mesmo ou de outro tribunal. [tjba.jus](https://www.tjba.jus.br/portal/sistema-de-controle-de-depositos-judiciais-recebe-alteracoes-confira/)

***

# Botão “Adicionar tipo”

## Localização

Adicionar na parte inferior do overlay, próximo ao botão:

```text
Criar alvarás
```

O novo botão deverá se chamar:

```text
Adicionar tipo
```

## Opções

Ao clicar, abrir um seletor com:

```text
Crédito do exequente
INSS
Custas
Honorários advocatícios
Honorários periciais
Devolução à reclamada
Transferência para outro processo
```

O usuário selecionará um tipo e o sistema adicionará um novo card vazio com os campos correspondentes.

## Regras

O item criado manualmente deverá:

```text
origem: adicionado manualmente
valor: vazio ou R$ 0,00
```

O usuário deverá poder:

- Preencher o valor.
- Alterar o destinatário.
- Informar dados bancários.
- Informar o ID do depósito.
- Remover o card.
- Editar o tipo.
- Salvar o item no `localStorage`.

O tipo adicionado manualmente deverá seguir exatamente a mesma estrutura dos tipos extraídos da decisão.

***

# Fase 2 usando a fase 1

A fase 2 deverá utilizar apenas o campo `tipo` para escolher o fluxo inicial no SISCONDJ:

| Tipo da fase 1 | Fluxo inicial da fase 2 |
|---|---|
| Crédito do exequente | Novo alvará para crédito ao beneficiário |
| INSS | Novo alvará para DARF |
| Custas | Novo alvará para GRU |
| Honorários advocatícios | Novo alvará para crédito ao advogado ou escritório |
| Honorários periciais | Novo alvará para crédito ao perito |
| Devolução à reclamada | Novo alvará para crédito à reclamada ou procurador |
| Transferência para outro processo | Novo depósito ou transferência judicial |

Depois de escolher o fluxo, a fase 2 deverá preencher somente os campos apresentados pelo próprio SISCONDJ.

A fase 1 não precisa armazenar previamente todas as opções internas do SISCONDJ, pois a finalidade selecionada determinará os campos exibidos na tela. O manual do SISCONDJ-JT descreve justamente o fluxo de pesquisar o processo, selecionar conta ou parcela, selecionar o tipo de finalidade e preencher os campos necessários para adicionar a solicitação. [trt20.jus](https://www.trt20.jus.br/download/siscondj/Manual%20do%20Usu%C3%A1rio.pdf)

***

# Alterações necessárias na fase 1

A fase 1 precisa receber apenas estas alterações:

## Adicionar o tipo Devolução à reclamada

Incluir:

```text
Devolução à reclamada
```

com:

```text
valor
destinatarioTipo
destinatarioNome
destinatarioDocumento
dados bancários
deposito.id
deposito.banco
deposito.valor
deposito.pendenteConsulta
```

## Adicionar o tipo Transferência para outro processo

Incluir:

```text
Transferência para outro processo
```

com:

```text
valor
deposito.id
deposito.banco
deposito.valor
deposito.pendenteConsulta
transferencia.processoDestino
transferencia.tribunalDestino
transferencia.unidadeDestino
```

## Adicionar o botão Adicionar tipo

O botão deverá permitir inserir manualmente qualquer um dos sete tipos, mesmo que o tipo não tenha sido reconhecido na decisão.

## Não ampliar excessivamente a fase 1

Não acrescentar ainda:

```text
código de receita do DARF
campos internos de GRU
tipo de resgate do SISCONDJ
opções internas de finalidade
campos técnicos da tela do SISCONDJ
status de assinatura
número do alvará
```

Esses dados pertencem à fase 2 e deverão ser definidos somente depois que o HTML e os campos reais do SISCONDJ forem analisados.