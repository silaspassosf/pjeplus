# Chip “Advogado Impedido” — situação da OAB no DOM x no painel de validação

Análise dos achados nos processos **6394282** (1001321-62.2024.5.02.0703, retificação de autuação) e **5931322**.

---

## 1. Resumo

Existem duas fontes distintas para a situação do advogado na OAB:

1. **DOM / `/detalhe`** — campo `situacaoOab` do vínculo da parte com o processo, obtido em `/processos/id/{id}/partes`.
2. **Painel “Validar na OAB”** — consulta live ao WS da OAB, via `POST /pessoas/fisicas/{idPessoa}/validacaooab`.

O DOM é um **snapshot** do vínculo processual e depende da grafia do número da OAB e da query usada. O POST é **live** e consulta por pessoa (`idPessoa`), sem depender da grafia do processo.

As inconsistências encontradas explicam por que um advogado **regular** pode aparecer como impedido no DOM e por que existe processo com o chip sem nenhum advogado marcado.

---

## 2. As duas fontes de dados

### 2.1 Fonte DOM (`/detalhe`)

- Chamada da tela: `GET /pje-comum-api/api/processos/id/{id}/partes?retornaEndereco=true`.
- Campo usado pelo painel: `representante.situacaoOab`.
- Regra do painel:
  - advogado é “irregular” quando `tipo = ADVOGADO` e `situacaoOab != "REGULAR"`;
  - o tooltip mostra `situacaoOab`; se o campo estiver vazio/ausente, mostra **“NÃO ENCONTRADA”**.
- Natureza do dado: valor **gravado no vínculo parte↔processo** (snapshot). Pode estar vazio, desatualizado ou variar conforme os parâmetros da consulta.
- O painel do `/detalhe` lista apenas as partes **ativas**; advogados inativos não são exibidos.

### 2.2 Fonte POST (painel “Validar na OAB”)

- Chamada: `POST /pje-comum-api/api/pessoas/fisicas/{idPessoa}/validacaooab?especializacao=Advogado`.
- Consulta o **WS da OAB na hora** e devolve:
  - `dadosOab[]`: `uf`, `numInscricao`, `tipoInscricao`, `codigoSituacao`, `nomeSituacao`, `id`;
  - `pessoaOab`: inscrição atualmente usada pelo cadastro;
  - `multiplasOab`: true quando há mais de uma inscrição;
  - `dadosWsOab`: indica se o WS respondeu.
- Códigos de `codigoSituacao`:

| Código | Situação |
|---|---|
| 1 | Regular |
| 2 | Cancelado |
| 3 | Falecido |
| 4 | Suspenso |
| 5 | Licenciado |
| 6 | Excluído |
| 7 | Em processo de inscrição |

- Chave da consulta: **pessoa** (`idPessoa`), não o texto da OAB do processo.

---

## 3. Achados no processo 6394282

### 3.1 Representantes encontrados

`/partes?comInativas=true` devolveu **9 advogados**: 2 ativos e 7 inativos.

| Advogado | Ativo | OAB do processo | `/partes` (sem query) | `/partes?retornaEndereco=true` | POST live (inscrição do processo) | `multiplasOab` |
|---|---|---|---|---|---|---|
| Daniel Alves | Sim | SP321616 | REGULAR | REGULAR | Regular (SP321616) | False |
| Nelson Wilians | Sim | AP1551 | REGULAR | REGULAR | **Regular (AP1551-A)** | True |
| Raquel Nassif | Não | SP173491 | REGULAR | **vazio** | Regular (SP173491) | True |
| Viviane Castro | Não | SP136069 | REGULAR | **vazio** | Regular (SP136069) | True |
| Liliana Regina | Não | SP55002 | REGULAR | **vazio** | Regular (SP55002) | False |
| Marcelo Costa | Não | SP116776 | REGULAR | **vazio** | Regular (SP116776) | True |
| Alonso Santos | Não | SP246387 | REGULAR | **vazio** | Regular (SP246387) | False |
| Luiz Henrique | Não | SP252925 | REGULAR | **vazio** | Regular (SP252925) | False |
| Jaime Ballen | Não | SP171184 | REGULAR | **vazio** | Regular (SP171184) | False |

### 3.2 Leitura dos dados

- **Nenhum** dos 9 advogados tem a inscrição do processo em situação não-Regular no POST.
- Nos **ativos**, DOM e POST concordam: REGULAR.
- Nos **inativos**, o `/partes?retornaEndereco=true` (fonte do DOM) devolve `situacaoOab` **vazio**, enquanto o `/partes` sem query (e com `comInativas=true`) devolve REGULAR; o POST devolve Regular.
- O caso do **Nelson** é o exemplo mais claro de falso positivo: ele tem **27 inscrições**, sendo **18 não-Regulares** (Suspenso em SP, RJ, ES, SE, MS, PR, PA, AL, AM, BA, RS, DF, CE, AC, GO, TO, MT, RN), mas a inscrição que o processo usa é **AP1551-A = Regular**. Qualquer regra do tipo “se existe alguma Suspenso, marca impedido” erraria.
- Outros inativos também têm inscrições não-Regulares em outras UFs:
  - Raquel: ES38193 = Cancelado;
  - Marcelo: PA20603-A e ES22919 = Cancelados.
  - Em ambos, a inscrição do processo (SP) é Regular.
- Não houve, neste processo, nenhuma inscrição do processo não-Regular.

---

## 4. A falha que marca advogado regular como impedido

A falha tem duas causas que se somam.

### 4.1 Campo vazio é tratado como irregular

A regra do painel é `situacaoOab != "REGULAR"`. Quando o campo vem **vazio/ausente**, a condição é verdadeira e o tooltip mostra **“NÃO ENCONTRADA”**. Ou seja: ausência de informação é interpretada como impedimento.

### 4.2 A resolução do `situacaoOab` é sensível à grafia do número da OAB

O mesmo número aparece em formatos diferentes conforme a fonte:

| Origem | Exemplo |
|---|---|
| `/partes` (UF + número concatenados) | `AP1551`, `PE22616`, `SP321616` |
| `pessoaOab` (campos separados) | `ufOab = AP`, `numeroOab = 1551`, `letraOab = A` |
| `pessoaOab` com letra no número | `numeroOab = "22616-D"` (caso ANA) |
| `dadosOab.numInscricao` | `1551-A`, `00922`, `4.923-A`, `11065/A`, `00725A`, `128341-A`, `21188A` |

Variações observadas que quebram uma comparação literal:

- **letra/sufixo anexado**: `AP1551` x `AP1551-A`; `PE22616` x `22616-D`;
- **zeros à esquerda**: `00922`, `00725A`;
- **ponto**: `4.923-A`;
- **barra**: `11065/A`;
- **letra sem separador**: `21188A`, `128341-A`;
- **UF e número juntos no processo** (`AP1551`) x separados no cadastro (`AP` + `1551` + letra `A`);
- **tipo de inscrição** (`A`, `S`, `E`) que às vezes acompanha o número e às vezes não.

Quando a grafia não casa, o backend deixa `situacaoOab` **vazio**. O painel então mostra “NÃO ENCONTRADA” e trata o advogado como irregular — mesmo ele estando Regular na OAB.

### 4.3 A escolha da inscrição errada

Além do campo vazio, uma heurística que escolha “a primeira não-Regular” ou “qualquer Suspenso” pega uma inscrição de **outra UF** que não é a do processo. No caso do Nelson, isso marcaria SP128341 (Suspenso) como se fosse o impedimento do processo, quando a inscrição do processo é AP1551-A (Regular).

A comparação correta é: **UF + dígitos do número**, ignorando letra, sufixo, ponto, barra e zeros à esquerda; e olhar **essa** inscrição, não qualquer outra.

---

## 5. Inconsistência entre a API do DOM e a do POST

### 5.1 Onde concordam

Nos advogados **ativos** do processo 6394282, as duas fontes concordam: `situacaoOab = REGULAR` e POST Regular.

### 5.2 Onde divergem

Nos advogados **inativos**:

- `/partes?retornaEndereco=true` (fonte do DOM) → `situacaoOab` **vazio**;
- `/partes` sem query / `comInativas=true` → `situacaoOab = REGULAR`;
- POST → **Regular**.

Ou seja: **o mesmo endpoint `/partes`, com query diferente, devolve situação diferente para o inativo**. O DOM, que usa `retornaEndereco=true`, vê vazio; o POST, que consulta a pessoa, vê Regular.

### 5.3 Por que isso acontece

- O `situacaoOab` do `/partes` é um dado **do vínculo processual**, não uma consulta live. Em partes inativas, esse vínculo pode não ser resolvido/atualizado e o campo vem vazio.
- O POST vai ao **WS da OAB** por `idPessoa` e devolve todas as inscrições da pessoa, independentemente da grafia usada no processo.
- O DOM só exibe partes ativas; por isso o vazio dos inativos não gera aviso visível no `/detalhe`, mas o chip do processo permanece.

### 5.4 Consequência

O DOM não é fonte confiável para:

- advogados **inativos**;
- números de OAB com **letra/sufixo/formatação** diferente;
- situações em que o vínculo processual está **desatualizado** (o caso “SUSPENSO no `/detalhe` e REGULAR no painel” já relatado).

O POST é a fonte live; o DOM serve, no máximo, como indicação de que algo precisa ser checado.

---

## 6. Chip órfão por presença de advogado inativo

### 6.1 Como o chip aparece

O chip “Advogado impedido de Atuar” é **do processo**, não aponta para um advogado específico. Ele é criado pela presença de **advogado inativo** (parte inativa + cadastro inativo), **independentemente da situação na OAB**.

### 6.2 O que se vê no processo 6394282

- 7 advogados inativos;
- todos com a inscrição do processo **Regular** no POST;
- os 2 ativos também regulares;
- nenhum advogado com impedimento.

Resultado: o chip está **órfão/desatualizado**. Não há advogado a marcar no DOM — e o DOM nem mostra os inativos. O chip só sai com o **reprocessamento de chips do processo**.

### 6.3 Corroboração no processo 5931322

- 6 advogados ativos, todos regulares no POST;
- nenhum impedimento;
- chip presente sem ninguém marcado no DOM.

Mesmo padrão: chip sem respaldo na situação atual dos advogados.

### 6.4 Se o inativo estiver realmente irregular

A presença do inativo explica o chip, mas não garante que ele esteja regular. Só a comparação com o POST revela:

- se a inscrição do processo do inativo estiver não-Regular → há impedimento real;
- se estiver Regular → o chip é apenas reflexo do inativo e cai com o reprocessamento.

---

## 7. Conclusão dos achados

1. O DOM e o POST podem divergir; o POST é a fonte live e resolve a grafia da OAB.
2. A falha de marcar um advogado regular como impedido vem de:
   - `situacaoOab` vazio sendo tratado como irregular (“NÃO ENCONTRADA”);
   - comparação literal do número da OAB, que quebra com letra/sufixo (`-A`, `-D`), ponto, barra, zeros à esquerda;
   - escolha de uma inscrição não-Regular de outra UF em vez da inscrição do processo.
3. A comparação correta é por **UF + dígitos**, olhando a inscrição que o processo usa.
4. O chip pode existir sem nenhum advogado impedido: é o caso de **advogado inativo**, independentemente da situação na OAB.
5. Nesse cenário, a ação é **reprocessar os chips do processo**; validação/GIGS só se a inscrição do processo estiver de fato não-Regular.
