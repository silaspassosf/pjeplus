# Expedientes API

Endpoint: `GET /pje-comum-api/api/processos/id/{processoId}/expedientes`

Query parameters:
- `pagina` (int) — página (inicia em 1)
- `tamanhoPagina` (int) — tamanho da página (ex.: 10, 50)
- `instancia` (int) — instância do processo (ex.: 1)

Descrição
--------
Retorna uma lista paginada de "expedientes" relacionados a um processo.

Resposta (resumo relevante):

{
  "pagina": 1,
  "tamanhoPagina": 10,
  "qtdPaginas": 4,
  "totalRegistros": 31,
  "resultado": [
    {
      "id": 12345,
      "nomePessoaParte": "João da Silva",
      "tipoExpediente": "INTIMAÇÃO",
      "meioExpediente": "CORREIO",
      "prazoLegal": 10,
      "dataCriacao": "2026-04-01T10:00:00Z",
      "dataCiencia": "2026-04-02T12:00:00Z",
      "fimDoPrazoLegal": "2026-04-12T12:00:00Z",
      "fechado": false
    }
  ]
}

Campos observados (nomes exatos usados pelo PJe):
- `nomePessoaParte`
- `tipoExpediente`
- `meioExpediente`
- `prazoLegal` (número de dias — quando presente)
- `dataCriacao` (ISO)
- `dataCiencia` (ISO)
- `fimDoPrazoLegal` (ISO — quando disponível)
- `fechado` (boolean)

Normalização recomendada para consumidores (campos retornados pelos exemplos):
- `destinatario` ← `nomePessoaParte`
- `tipo` ← `tipoExpediente`
- `meio` ← `meioExpediente`
- `dataCriacao` ← `dataCriacao` (formatado `DD/MM/YY`)
- `dataCiencia` ← `dataCiencia` (formatado `DD/MM/YY` ou `null`)
- `prazo` ← `prazoLegal` (dias)
- `fimPrazo` ← `fimDoPrazoLegal` (formatado `DD/MM/YY`) — quando ausente, pode ser calculado como `(dataCiencia || dataCriacao) + prazoLegal dias` se `prazoLegal` for numérico
- `fechado` ← `fechado` (boolean)

Autenticação / cabeçalhos
- Execute a chamada a partir de uma sessão autenticada (navegador com credenciais ou `requests.Session` com cookies/headers corretos).
- Para clientes sem cookie de sessão, é necessário prover `X-XSRF-TOKEN` / header apropriado se o servidor exigir.

Observações
- Esta documentação foi gerada a partir de inspeção direta do endpoint em uma sessão autenticada; o cliente deve mapear exatamente os nomes observados acima para evitar regressões.

## Extração específica: Editais por parte (via `expedientes`)

Para localizar *editais* diretamente pelo endpoint de `expedientes`, consultar o mesmo endpoint e filtrar os itens cujo campo `tipoExpediente` é igual a `EDITAL`. O consumidor pode coletar apenas o nome do destinatário (`nomePessoaParte`) e construir um relatório do tipo:

"Editais localizados em nome de: [lista de partes com edital]"

Exemplo de fluxo (navegador autenticado):

1. GET `/pje-comum-api/api/processos/id/{processoId}/expedientes?pagina=1&tamanhoPagina=50&instancia=1`
2. Filtrar `resultado` por `item.tipoExpediente === 'EDITAL'`
3. Mapear `item.nomePessoaParte` e deduplicar para obter a lista de partes

Esta extração está implementada no script `Script/calc/calcapi.js` como `calcApi.editaisPorParte()` — método que pagina o endpoint e retorna a lista de nomes (strings) das partes que aparecem em expedientes do tipo `EDITAL`.

# Guia de Extração de Dados do PJe via API

Este guia reúne todas as informações necessárias para obter dados de processos do PJe (Processo Judicial Eletrônico) utilizando as APIs disponíveis, com foco em automação e integração. O conteúdo foi consolidado a partir da análise da extensão maisPJe, que já implementa diversas chamadas para extrair informações processuais.

## Índice

0. [Autenticação: requests.Session vs execute\_async\_script](#0-autenticação-requestssession-vs-execute_async_script)
1. [Configuração Inicial](#1-configuração-inicial)
2. [Estrutura da API e Cliente Python](#2-estrutura-da-api-e-cliente-python)
3. [Dados Básicos do Processo](#3-dados-básicos-do-processo)
4. [Partes, Advogados e Representantes](#4-partes-advogados-e-representantes)
5. [Movimentos e Timeline](#5-movimentos-e-timeline)
6. [Documentos e Conteúdo](#6-documentos-e-conteúdo)
7. [GIGS (Gestão de Atividades)](#7-gigs-gestão-de-atividades)
8. [Cálculos e Valores de Execução](#8-cálculos-e-valores-de-execução)
9. [Perícias](#9-perícias)
10. [BNDT – Banco Nacional de Devedores Trabalhistas](#10-bndt--banco-nacional-de-devedores-trabalhistas)
11. [Dados Financeiros (SIF / SISCONDJ / GARIMPO)](#11-dados-financeiros-sif--siscondj--garimpo)
12. [Domicílio Eletrônico e Endereços](#12-domicílio-eletrônico-e-endereços)
13. [Lembretes e Post-its](#13-lembretes-e-post-its)
14. [Resolução de Variáveis MaisPJe](#14-resolução-de-variáveis-maispje)
15. [Exemplos Práticos de Uso](#15-exemplos-práticos-de-uso)
16. [Escaninho de Petições — `PeticaoAPIClient`](#16-escaninho-de-petições--peticaoapiclient-peticaoapiclientpy)
17. [Triagem de Petição Inicial — `triagem_peticao`](#17-triagem-de-petição-inicial--triagem_peticao-trpy)

---

## 0. Autenticação: requests.Session vs execute_async_script

### O problema do XSRF-TOKEN em chamadas Python puras

O PJe usa o padrão **Angular CSRF**: o servidor define um cookie `XSRF-TOKEN` (não-HttpOnly,
legível pelo JS), e toda requisição que muta estado (POST/PUT/DELETE) deve enviar esse valor
de volta no header `X-XSRF-TOKEN`. Sem ele, a resposta é HTTP 403.

Quando se usa `requests.Session` criado a partir de `session_from_driver` (Fix/variaveis_client.py),
os cookies são copiados do driver — mas na prática o cookie `XSRF-TOKEN` pode não aparecer
ou ter restrições de path/SameSite que impedem a busca por nome no `CookieJar`. Resultado:
o header nunca é enviado e todos os POSTs retornam 403.

### Duas abordagens — quando usar cada uma

| Situação | Abordagem correta | Motivo |
|---|---|---|
| Endpoint **GET** sem mutação de estado | `requests.Session` via `session_from_driver` | Não exige XSRF; funciona com cookie de sessão |
| Endpoint **POST/PATCH/PUT/DELETE** protegido por XSRF | `execute_async_script` com JS `fetch` | Roda dentro do browser; cookie visível em `document.cookie`; sem jogo de path/domain |

> **Atenção — método correto para `agrupamentotarefas/10/processos`:** o endpoint da fila de processos usa **`PATCH`** (não `POST`). Confirmado pelo `apiaud.py` em produção. `POST` retorna HTTP 405.

### Abordagem ERRADA — requests.Session para PATCH/POST protegido

```python
# NAO FUNCIONA para endpoints PATCH/POST que exigem XSRF
from Fix.variaveis_client import session_from_driver

sess, host = session_from_driver(driver)
# Tentativa de extrair XSRF do CookieJar — FALHA: cookie pode nao aparecer
xsrf = sess.cookies.get('XSRF-TOKEN') or ''   # frequentemente vazio
sess.headers['X-XSRF-TOKEN'] = xsrf           # header vazio => HTTP 403

r = sess.patch(f'https://{host}/pje-comum-api/api/agrupamentotarefas/10/processos',
               json={'pagina': 1, 'tamanhoPagina': 100})
# => HTTP 403: "Header X-XSRF-TOKEN não informado"
```

### Abordagem CORRETA — execute_async_script (padrão Peticao/api_client.py)

```python
# Versão correta: PATCH (não POST) — confirmado em apiaud.py
_JS_PATCH_ENDPOINT = """
const payload  = arguments[0];
const callback = arguments[1];

// 1. Ler XSRF direto do document.cookie — sempre disponivel no contexto do browser
var xsrfCookie = document.cookie.split(';')
    .map(function(c) { return c.trim(); })
    .find(function(c) { return c.toLowerCase().indexOf('xsrf-token=') === 0; });
var xsrf = xsrfCookie ? xsrfCookie.split('=').slice(1).join('=') : '';

(async function() {
    var r = await fetch(location.origin + '/pje-comum-api/api/agrupamentotarefas/10/processos', {
        method: 'PATCH',                 // PATCH — não POST (405 com POST)
        credentials: 'include',          // envia cookies de sessao automaticamente
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-XSRF-TOKEN': xsrf         // XSRF lido do document.cookie — funciona
        },
        body: JSON.stringify(payload)
    });
    if (!r.ok) { callback({ erro: 'HTTP_' + r.status }); return; }
    callback({ resultado: await r.json() });
})();
"""

def buscar_processos(driver, pagina: int = 1):
    driver.set_script_timeout(60)
    res = driver.execute_async_script(_JS_PATCH_ENDPOINT, {'pagina': pagina, 'tamanhoPagina': 100})
    driver.set_script_timeout(30)
    if res.get('erro'):
        raise RuntimeError(res['erro'])
    return res['resultado']
```

### Por que `execute_async_script` resolve e `requests.Session` não

1. **Cookie path/SameSite**: O browser respeita automaticamente os atributos do cookie.
   O `requests.CookieJar` pode descartar o cookie se o path da requisição não bater.

2. **Visibilidade de `document.cookie`**: O `XSRF-TOKEN` é não-HttpOnly (projetado para ser
   lido pelo JS Angular). Dentro do `execute_async_script`, `document.cookie` **sempre**
   tem o token. No Python, o mesmo cookie pode não aparecer na cópia feita por
   `driver.get_cookies()` dependendo da ordem de navegação.

3. **`credentials: 'include'`**: O browser envia todos os cookies qualificados para o
   domínio — sem precisar copiá-los manualmente.

### Regra prática

> **GET simples** (consultar processo, listar tarefas): `session_from_driver` é suficiente.
>
> **PATCH/POST/PUT/DELETE** (fila, triagem, petições com mutação): sempre usar
> `execute_async_script` com `fetch` + `X-XSRF-TOKEN` lido de `document.cookie`.
>
> **Endpoint `agrupamentotarefas/10/processos`**: usa **PATCH** com paginação. Ver `apiaud.py` para implementação completa com loop de páginas.

---

## 1. Configuração Inicial

Para acessar as APIs do PJe, é necessário:

- **Domínio do TRT**: exemplo `pje.trt12.jus.br`
- **Sessão autenticada**: via cookies de navegador (recomenda-se usar `requests.Session` com cookies importados de um navegador autenticado)
- **Grau de instância**: `1` (primeiro grau) ou `2` (segundo grau)
- **Headers**: `Accept: application/json`, `Content-Type: application/json` e `X-Grau-Instancia: <1 ou 2>`.

### 1.1. Exemplo de criação de cliente em Python

```python
import requests
from urllib.parse import urlparse

class PjeApiClient:
    def __init__(self, session: requests.Session, trt_host: str, grau: int = 1):
        self.sess = session
        self.trt_host = trt_host
        self.grau = grau

    def _url(self, path: str) -> str:
        base = self.trt_host
        if not base.startswith('http'):
            base = 'https://' + base
        return f"{base}{path}"

# Exemplo de criação a partir de um driver Selenium
from selenium import webdriver
driver = webdriver.Firefox()  # ou Chrome
driver.get('https://pje.trt12.jus.br/primeirograu/login.seam')
# ... faça login manualmente ou automático ...
sess = requests.Session()
for cookie in driver.get_cookies():
    sess.cookies.set(cookie['name'], cookie['value'])
parsed = urlparse(driver.current_url)
trt_host = parsed.netloc
client = PjeApiClient(sess, trt_host, grau=1)
```

### 1.2. Identificação do Perfil e Órgão Julgador

Sempre que a interface do PJe necessitar de validar se o utilizador possui contexto para executar ações (ex: ações em lote ou trocas de papel), pode ser consultada a API de Órgãos Julgadores.

**Endpoint:** `GET /pje-comum-api/api/orgaosjulgadores/`

- **Utilidade:** Retorna os dados do Órgão Julgador associados à sessão atual. Se o utilizador mudar de contexto (ex: passar de Magistrado para Servidor noutra vara), este endpoint refletirá o novo `codigoOJ`.

---

## 2. Estrutura da API e Cliente Python

A seguir, listamos os principais endpoints que podem ser consumidos. Para facilitar, os exemplos utilizam a classe `PjeApiClient` que encapsula as chamadas. Caso prefira chamadas diretas com `requests`, basta montar a URL conforme indicado.

### 2.1. Métodos da classe `PjeApiClient` (referência)

```python
# Obtém a timeline do processo (documentos e movimentos)
def timeline(self, id_processo: str, buscarDocumentos: bool = True, buscarMovimentos: bool = False) -> Optional[List[Dict]]

# Obtém detalhes de um documento pelo ID interno
def documento_por_id(self, id_processo: str, id_documento: str, incluirAssinatura: bool = False, incluirAnexos: bool = False) -> Optional[Dict]

# Obtém dados da execução GIGS (valor atualizado)
def execucao_gigs(self, id_processo: str) -> Optional[Dict]

# Obtém dados gerais do processo (inclui fase, justiça gratuita, etc.)
def processo_por_id(self, id_processo: str) -> Optional[Dict]

# Obtém a lista de partes do processo
def partes(self, id_processo: str) -> Optional[List[Dict]]

# Converte número CNJ para ID interno
def id_processo_por_numero(self, numero_processo: str) -> Optional[str]

# Obtém lista de cálculos homologados
def calculos(self, id_processo: str) -> Optional[Dict]

# Obtém lista de perícias
def pericias(self, id_processo: str) -> Optional[Dict]

# Obtém atividades GIGS do processo
def atividades_gigs(self, id_processo: str) -> Optional[List[Dict]]

# Obtém partes cadastradas no BNDT
def debitos_trabalhistas_bndt(self, id_processo: str) -> Optional[List[Dict]]

# Verifica domicílio eletrônico de uma parte (PJ)
# True = habilitada | False = não habilitada | None = PF ou não encontrada
def domicilio_eletronico(self, id_parte: str) -> Optional[bool]
```

---

## 3. Dados Básicos do Processo

**Endpoint:** `/pje-comum-api/api/processos/id/{idProcesso}`  
**Método:** GET  

**Campos úteis retornados** (exemplo):

```json
{
  "id": 123456,
  "numero": "0001234-56.2024.5.12.0059",
  "classeJudicial": { "descricao": "ATOrd", "sigla": "ATOrd" },
  "faseProcessual": "Conhecimento",
  "justicaGratuita": false,
  "segredoDeJustica": false,
  "juizoDigital": false,
  "autuadoEm": "2024-01-15T10:00:00",
  "orgaoJulgador": { "id": 23, "descricao": "VARA DO TRABALHO DE PALHOÇA", "sigla": "PCA" },
  "orgaoJulgadorCargo": { "descricao": "Titular" },
  "dataTransito": null,
  "prioridades": [ ... ]
}
```

**Exemplo de uso no Python:**

```python
dados = client.processo_por_id('123456')
if dados:
    numero = dados['numero']
    classe = dados['classeJudicial']['descricao']
    fase = dados['faseProcessual']
    justica_gratuita = dados.get('justicaGratuita', False)
    juizo_digital = dados.get('juizoDigital', False)
    data_autuacao = dados.get('autuadoEm')
```

---

## 4. Partes, Advogados e Representantes

**Endpoint:** `/pje-comum-api/api/processos/id/{idProcesso}/partes`  
**Método:** GET  

Retorna um dicionário com três listas: `ATIVO`, `PASSIVO` e `TERCEIROS`. Cada parte contém informações como `idPessoa`, `nome`, `documento` (CPF/CNPJ), `representantes` (lista de advogados/procuradores) e `pessoaFisica` (com dataNascimento, nomeGenitora, etc.).

**Exemplo de estrutura:**

```json
{
  "ATIVO": [
    {
      "idPessoa": 123456,
      "nome": "Fulano de Tal",
      "documento": "123.456.789-00",
      "pessoaFisica": {
        "dataNascimento": "1980-01-01",
        "nomeGenitora": "Maria da Silva"
      },
      "representantes": [
        {
          "idPessoa": 789012,
          "nome": "Dr. Advogado",
          "documento": "987.654.321-00",
          "numeroOab": "12345/SC"
        }
      ]
    }
  ],
  "PASSIVO": [...],
  "TERCEIROS": [...]
}
```

**Exemplo de uso:**

```python
partes = client.partes('123456')
if partes:
    for ativo in partes.get('ATIVO', []):
        nome = ativo['nome']
        cpf = ativo.get('documento')
        advs = ativo.get('representantes', [])
        for adv in advs:
            print(f"Advogado: {adv['nome']} OAB: {adv['numeroOab']}")
```

---

## 5. Movimentos e Timeline

A timeline agrupa documentos e movimentos do processo em ordem cronológica (do mais recente para o mais antigo, ou vice-versa conforme ordenação).

**Endpoint:** `/pje-comum-api/api/processos/id/{idProcesso}/timeline`  
**Parâmetros:** `somenteDocumentosAssinados=false`, `buscarMovimentos=true/false`, `buscarDocumentos=true/false`.

Retorna uma lista de objetos, cada um representando um documento ou movimento.

**Exemplo de movimento:**

```json
{
  "tipo": "Movimento",
  "codEvento": 848,
  "titulo": "Transitado em julgado em 10/10/2024",
  "data": "2024-10-10T00:00:00",
  "textoFinalExterno": "..."
}
```

**Exemplo de documento:**

```json
{
  "tipo": "Sentença",
  "id": 987654,
  "idUnicoDocumento": "abc1234",
  "titulo": "Sentença - ID. abc1234",
  "data": "2024-09-15T00:00:00",
  "assinado": true,
  "anexos": [ ... ]
}
```

**Filtrar movimentos por código:**  
Use o endpoint `/pje-comum-api/api/processos/id/{idProcesso}/movimentos/` com `codEventos` e `ordemAscendente` para extrair apenas os movimentos relevantes.

**Parâmetros de query:**
- `ordemAscendente`: `true` ou `false`
- `codEventos`: lista de ids dos eventos do CNJ; pode ser enviado como lista ou como múltiplos parâmetros `codEventos`.

**Exemplo:** `codEventos=334&codEventos=11024` ou `codEventos=[334, 11024]`.

```python
movimentos = client.sess.get(
    client._url(f"/pje-comum-api/api/processos/id/{id_processo}/movimentos/"),
    params={"codEventos": [334, 11024], "ordemAscendente": "false"}
).json()
```

**Tabela de Códigos Comuns:**
| Código CNJ | Descrição Prática |
|:---:|---|
| **26** | Distribuído por Sorteio (Data de Autuação) |
| **221** | Julgado Procedente em Parte (Sentença) |
| **848** | Transitado em Julgado |
| **50047** | Homologada a Liquidação (Decisão Homologatória) |

*Nota: essa filtragem evita a necessidade de processar toda a timeline quando a busca precisa ser focada em eventos-chave.*

---

## 6. Documentos e Conteúdo

### 6.1. Obter metadados de um documento

**Endpoint:** `/pje-comum-api/api/processos/id/{idProcesso}/documentos/id/{idDocumento}`  
**Parâmetros opcionais:** `incluirAssinatura`, `incluirAnexos`, `incluirMovimentos`, `incluirApreciacao`.

```python
doc = client.documento_por_id('123456', '987654', incluirAnexos=True)
tipo = doc['tipo']
id_unico = doc['idUnicoDocumento']
anexos = doc.get('anexos', [])
```

### 6.2. Obter conteúdo textual (HTML) de um documento

Para extrair o texto sem abrir PDF, você pode tentar os seguintes endpoints:

- `/pje-comum-api/api/processos/id/{idProcesso}/documentos/id/{idDocumento}/html`
- `/pje-comum-api/api/processos/id/{idProcesso}/documentos/id/{idDocumento}/conteudo`

Se o retorno for JSON com campos `conteudo` ou `conteudoHtml`, extraia o texto removendo tags.

A função `obter_texto_documento` no arquivo `variaveis_helpers.py` implementa essa lógica:

```python
from Fix.variaveis_helpers import obter_texto_documento

texto = obter_texto_documento(client, id_processo, id_documento)
if texto:
    print(texto)
```

### 6.2.1. Dois tipos de identificador de documento — e como converter

Todo documento no PJe tem **dois identificadores distintos**:

| Campo | Tipo | Exemplo | Usado em |
|---|---|---|---|
| `id` | inteiro numérico | `987654` | endpoints de API (`/documentos/id/{id}/conteudo`, `/documentos/id/{id}/html`) |
| `idUnicoDocumento` | hex 7 chars | `abc1234` | URL do PJe (`?documentoId=abc1234`), DOM da timeline, links internos |

**Regra geral:** qualquer endpoint `/documentos/id/{idDocumento}/...` exige o `id` **numérico**. Passar `idUnicoDocumento` resulta em HTTP 404.

#### Estratégia correta: resolver via `/documentos?idUnicoDocumento={uid}`

O endpoint `/documentos` aceita `idUnicoDocumento` como query parameter e retorna o objeto completo do documento, incluindo seu `id` numérico:

**Endpoint:** `GET /pje-comum-api/api/processos/id/{idProcesso}/documentos?idUnicoDocumento={uid}`

**Resposta:** array (geralmente 1 item) ou objeto com `id` numérico.

```javascript
// JavaScript (Tampermonkey/extensão)
async function resolverUidParaId(idProcesso, uid) {
    const url = `${location.origin}/pje-comum-api/api/processos/id/${idProcesso}/documentos?` +
        new URLSearchParams({ idUnicoDocumento: uid });
    const resp = await fetch(url, { credentials: 'include' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const item = Array.isArray(data) ? data[0] : data;
    return item?.id;  // id numérico
}

// Uso
const idDoc = await resolverUidParaId('7530597', '217ddae');
const conteudo = await fetch(
    `${location.origin}/pje-comum-api/api/processos/id/7530597/documentos/id/${idDoc}/conteudo`,
    { credentials: 'include' }
);
```

```python
# Python
def resolver_uid_para_id(client, id_processo, uid):
    resp = client.sess.get(
        client._url(f"/pje-comum-api/api/processos/id/{id_processo}/documentos"),
        params={"idUnicoDocumento": uid}
    ).json()
    item = resp[0] if isinstance(resp, list) else resp
    return item.get("id")

id_doc = resolver_uid_para_id(client, "7530597", "217ddae")
```

> **Nota:** Não use a timeline para essa resolução. Percorrer todos os itens da timeline para encontrar o `id` numérico é desnecessário — o endpoint `/documentos?idUnicoDocumento` faz esse lookup diretamente.

#### Origem dos identificadores na timeline

A timeline (`/timeline?buscarDocumentos=true`) retorna os dois campos juntos no mesmo objeto:

```json
{
  "tipo": "Planilha de Cálculos",
  "id": 987654,
  "idUnicoDocumento": "abc1234",
  "titulo": "Planilha de Cálculos - ID. abc1234"
}
```

Quando o dado já vem da timeline (ex: durante processamento de itens), use `item["id"]` diretamente sem chamada adicional.

---

### 6.3. Chave de validação de documento

A chave é construída a partir de `dataInclusaoBin` e `idBin`. A função `obter_codigo_validacao_documento` a calcula:

```python
from Fix.variaveis_resolvers import obter_codigo_validacao_documento

chave = obter_codigo_validacao_documento(client, id_processo, id_documento)
# chave é uma string de ~29 dígitos
```

### 6.4. Localizar documentos específicos na timeline

A função `obter_peca_processual_da_timeline` permite buscar o primeiro documento de um tipo (ex: "Sentença") e retornar seu ID, chave ou lista de anexos.

```python
from Fix.variaveis_resolvers import obter_peca_processual_da_timeline

# Obter chave da última sentença
chave = obter_peca_processual_da_timeline(client, id_processo, 'Sentença', modo='chave')
# Obter ID (idUnicoDocumento)
id_unico = obter_peca_processual_da_timeline(client, id_processo, 'Sentença', modo='id')
# Obter lista de anexos
anexos_str = obter_peca_processual_da_timeline(client, id_processo, 'Sentença', modo='anexos')
```

**Tipos comuns**: 'Sentença', 'Despacho', 'Decisão', 'Acórdão', 'Ata da Audiência', 'Certidão', 'Petição Inicial', 'Contestação', 'Manifestação', 'Planilha de Cálculos', 'Chave de Acesso'.

---

## 7. GIGS (Gestão de Atividades)

As atividades GIGS representam tarefas ou compromissos vinculados ao processo (prazos, lembretes, etc.).

### 7.1. Listar todas as atividades

**Endpoint:** `/pje-gigs-api/api/atividade/processo/{idProcesso}`  
**Método:** GET  

```python
atividades = client.atividades_gigs('123456')
for atv in atividades:
    print(atv['tipoAtividade'], atv['statusAtividade'], atv.get('dataPrazo'), atv.get('observacao'))
```

### 7.2. Filtrar atividades por observação e status

Use as funções helpers:

```python
from Fix.variaveis_helpers import buscar_atividade_gigs_por_observacao, obter_todas_atividades_gigs_com_observacao

# Buscar a primeira atividade com observação contendo "AJ-JT" e prazo aberto
atividade = buscar_atividade_gigs_por_observacao(client, id_processo, ['AJ-JT'], prazo_aberto=True)

# Obter todas as atividades com "AJ-JT"
atividades = obter_todas_atividades_gigs_com_observacao(client, id_processo, ['AJ-JT'], prazo_aberto=True)
```

### 7.3. Obter GIGS e fase do processo em uma única chamada

```python
from Fix.variaveis_helpers import obter_gigs_com_fase

dados = obter_gigs_com_fase(client, id_processo)
if dados:
    fase = dados['fase']
    atividades = dados['atividades_gigs']
```

### 7.4. Bloqueio de Tarefas

Ao manipular transições de tarefas ou mudar de Órgão Julgador, o PJe dispara um bloqueio de segurança para evitar que múltiplos utilizadores alterem o mesmo contexto.

**Endpoint:** `POST /pje-comum-api/api/processos/id/{idProcesso}/bloqueiotarefas`

- **Atenção:** por ser um pedido `POST`, exige o cabeçalho `X-XSRF-TOKEN`. Use `execute_async_script` com `fetch` no browser para garantir que o token seja lido de `document.cookie`.

---

## 8. Cálculos e Valores de Execução

### 8.1. Valor da execução via GIGS

**Endpoint:** `/pje-gigs-api/api/execucao/{idProcesso}` (ou `/pje-gigs-api/api/processo/{idProcesso}`)

```python
execucao = client.execucao_gigs('123456')
if execucao:
    valor = execucao.get('valor')
    data = execucao.get('data')
```

### 8.2. Cálculos homologados (PJeCalc)

**Endpoint:** `/pje-comum-api/api/calculos/processo`  
**Parâmetros:** `idProcesso`, `pagina`, `tamanhoPagina`, `ordenacaoCrescente`

```python
calculos = client.calculos('123456')
if calculos and calculos.get('resultado'):
    ultimo = calculos['resultado'][0]
    valor_total = ultimo.get('total')
    data_liquidacao = ultimo.get('dataLiquidacao')
```

### 8.3. Obrigações de pagar

**Endpoint:** `/pje-comum-api/api/processos/id/{idProcesso}/obrigacoespagar`

```python
r = client.sess.get(client._url(f"/pje-comum-api/api/processos/id/{id_processo}/obrigacoespagar"))
obrigacoes = r.json()
# cada obrigação tem credor, devedor, valor, rubricas, etc.
```

---

## 9. Perícias

**Endpoint:** `/pje-comum-api/api/pericias`  
**Parâmetros:** `idProcesso`

```python
pericias = client.pericias('123456')
if pericias and pericias.get('resultado'):
    for pericia in pericias['resultado']:
        print(pericia['nomePerito'], pericia['situacaoPericia'], pericia['prazoEntrega'])
```

---

## 10. BNDT – Banco Nacional de Devedores Trabalhistas

**Endpoint:** `/pje-comum-api/api/processos/id/{idProcesso}/debitostrabalhistas`

```python
from Fix.variaveis_helpers import verificar_bndt

resultado = verificar_bndt(client, '123456')
if resultado['tem_partes']:
    print(resultado['mensagem'])
    for nome in resultado['partes']:
        print(nome)
```

---

## 11. Dados Financeiros (SIF / SISCONDJ / GARIMPO)

Estes endpoints exigem permissões específicas e geralmente são usados apenas por servidores. Eles estão documentados no `apis.js`:

### 11.1. SIF (Sistema de Informações Financeiras)

- **Lista de contas:** `/sif-financeiro-api/api/listas/contas/{numeroProcesso}`
- **Extrato:** `/sif-financeiro-api/api/contas/{processo}/104/{conta}/extrato/0/{dataAutuacao}/{dataFim}`
- **Detalhes da conta:** `/sif-financeiro-api/api/contas/{processo}/104/{conta}/detalhes`
- **Alvarás:** `/sif-financeiro-api/api/alvaras/lista/{numeroProcesso}/104/{contajudicial}`

### 11.2. SISCONDJ (Sistema de Contas Judiciais)

- **Relatórios e contas:** URLs baseadas em configuração do usuário (`preferencias.configURLs.urlSiscondj`).
- **Extratos:** `/pages/movimentacao/conta/downloadPdf/extrato/{dataInicio}/{dataFim}/{conta}`

### 11.3. GARIMPO (Depósitos Recursais/Judiciais)

- **Consulta de contas:** URL do garimpo (ex: `https://deposito.trt12.jus.br/#/conta`) com parâmetros `?maisPje=true&tipo=1&processo={numero}`. A resposta é capturada via storage ou parsing.

---

## 12. Domicílio Eletrônico e Endereços

### 12.1. Domicílio eletrônico

**Endpoint:** `/pje-comum-api/api/pessoajuridicadomicilioeletronico/{idParte}`  
**Método:** GET  
**Retorno:** `{"habilitada": true/false}` — apenas para **Pessoa Jurídica** (PF retorna 404 → `None`)

**Via método `PjeApiClient.domicilio_eletronico()`** (padrão — usado em `aud.py`):

```python
# True = habilitada, False = não habilitada, None = PF ou não encontrada
habilitada = client.domicilio_eletronico(id_parte)
```

**Verificação em lote das partes passivas** (padrão real de `def_citacao` em `aud.py`):

```python
partes_raw = client.partes(id_processo) or {}
passivos = partes_raw.get('PASSIVO') or []
com_dom = 0
for parte in passivos:
    id_parte = str(
        parte.get('idPessoa') or parte.get('id') or
        parte.get('idParticipante') or parte.get('idParte') or ''
    )
    # Checar flag inline primeiro (evita chamada extra)
    dom_flag = parte.get('domicilioEletronico') or parte.get('possuiDomicilioEletronico')
    if dom_flag is True:
        com_dom += 1
        continue
    if dom_flag is False:
        continue
    # Fallback: consultar endpoint individual
    if id_parte and client.domicilio_eletronico(id_parte) is True:
        com_dom += 1

sem_dom = len(passivos) - com_dom
# sem_dom == 0 → todos têm domicílio → xs ord / xs sum
# com_dom == 0 → nenhum tem domicílio → xs ordc / xs sumc
# misto → criar ambos os GIGS
```

**Chamada direta (fallback sem método):**

```python
r = client.sess.get(client._url(f"/pje-comum-api/api/pessoajuridicadomicilioeletronico/{id_parte}"))
habilitada = r.json().get('habilitada', False) if r.ok else None
```

### 12.2. Endereços de uma pessoa

**Endpoint:** `/pje-comum-api/api/pessoas/{idPessoa}/enderecos`  
**Parâmetros:** `somenteValidos=true`, `ordenacaoColuna=id`, `ordenacaoAscendente=false`, `pagina=1`, `tamanhoPagina=10000`

```python
r = client.sess.get(client._url(f"/pje-comum-api/api/pessoas/{id_pessoa}/enderecos"), params={'tamanhoPagina': 10000})
enderecos = r.json().get('resultado', [])
```

*Recomendação: forçar `tamanhoPagina=10000` para evitar múltiplas requisições paginadas ao listar endereços completos de uma parte.*

---

## 13. Lembretes e Post-its

Atualmente não há um endpoint direto para lembretes (post-its) do processo. A extensão utiliza a interface gráfica para interagir com eles. No entanto, é possível que exista um endpoint não documentado; caso necessário, inspecione as requisições da interface.

---

## 14. Resolução de Variáveis MaisPJe

A extensão utiliza variáveis como `[maisPje:exequente]` ou `[maisPje:últimaSentença:chave]`. A função `resolver_variavel` implementa a lógica:

```python
from Fix.variaveis_resolvers import resolver_variavel

valor = resolver_variavel(client, id_processo, "últimaSentença:chave")
# valor será a chave de validação da última sentença

valor2 = resolver_variavel(client, id_processo, "exequente")
# valor2 será o nome do exequente (polo ativo)
```

A função `get_all_variables` retorna um dicionário com todas as variáveis comuns:

```python
from Fix.variaveis_resolvers import get_all_variables

variaveis = get_all_variables(client, id_processo)
print(variaveis['exequente'])
print(variaveis['valorDivida'])
print(variaveis['audiencia:data'])
```

---

## 15. Exemplos Práticos de Uso

### 15.1. Obter dados completos de um processo

```python
id_processo = "0001234-56.2024.5.12.0059"
# Se tiver número CNJ, resolva o ID interno
id_interno = client.id_processo_por_numero(id_processo)
if not id_interno:
    raise ValueError("Processo não encontrado")

# 1. Dados gerais
proc = client.processo_por_id(id_interno)
print(f"Número: {proc['numero']}")
print(f"Fase: {proc['faseProcessual']}")
print(f"Juízo digital: {proc.get('juizoDigital')}")

# 2. Partes
partes = client.partes(id_interno)
exequentes = [p['nome'] for p in partes.get('ATIVO', [])]
executados = [p['nome'] for p in partes.get('PASSIVO', [])]
print(f"Exequentes: {exequentes}")
print(f"Executados: {executados}")

# 3. Última sentença (chave)
chave = resolver_variavel(client, id_interno, "últimaSentença:chave")
if chave:
    print(f"Chave da sentença: {chave}")

# 4. GIGS
gigs = client.atividades_gigs(id_interno)
for atv in gigs:
    print(f"Atividade: {atv['tipoAtividade']} - {atv['statusAtividade']} - {atv.get('dataPrazo')}")

# 5. Valor da execução
execucao = client.execucao_gigs(id_interno)
if execucao:
    print(f"Valor da execução: R$ {execucao.get('valor')} (data: {execucao.get('data')})")
```

### 15.2. Extrair texto de um documento

```python
from Fix.variaveis_helpers import obter_texto_documento

id_documento = "12345678"
texto = obter_texto_documento(client, id_interno, id_documento)
if texto:
    print(texto[:500])  # primeiros 500 caracteres
```

### 15.3. Verificar se há documento não assinado

```python
from Fix.variaveis_resolvers import obter_peca_processual_da_timeline

# Verificar se existe documento com tipo 'Despacho' não assinado
timeline = client.timeline(id_interno, buscarDocumentos=True, buscarMovimentos=False)
for item in timeline:
    if item.get('tipo') == 'Despacho' and not item.get('assinado', True):
        print(f"Despacho não assinado: {item['idUnicoDocumento']}")
```

---

## 16. Escaninho de Petições — `PeticaoAPIClient` (`Peticao/api_client.py`)

Cliente especializado em buscar petições juntadas no escaninho via `execute_async_script`.  
**Endpoint:** `GET /pje-comum-api/api/escaninhos/peticoesjuntadas`  
**Método:** GET paginado — **não** requer XSRF. `credentials: 'include'` é suficiente.

### 16.1. Uso básico

```python
from Peticao.api_client import PeticaoAPIClient

client = PeticaoAPIClient()
itens = client.fetch(driver)          # retorna List[PeticaoItem]
for item in itens:
    print(item.numero_processo, item.tipo_peticao, item.tarefa, item.polo)
```

### 16.2. Dataclass `PeticaoItem`

```python
@dataclass
class PeticaoItem:
    numero_processo: str          # número CNJ
    tipo_peticao:    str          # nomeTipoProcessoDocumento
    descricao:       str          # descricao / descricaoPeticao
    tarefa:          str          # nome da tarefa atual
    fase:            str          # faseProcessual
    data_juntada:    str          # dataJuntada / dataCadastro (ISO string)
    eh_perito:       bool         # True se nomePapelUsuarioDocumento == "Perito"
    parte:           str          # "Ativo (Advogado)" | "Passivo (Perito)" etc.
    id_processo:     str          # id interno do processo
    id_item:         str          # id da petição/documento
    data_audiencia:  Optional[str]
    polo:            Optional[str]  # "ativo" | "passivo" | None
```

### 16.3. Normalização de campos do item bruto

A função `_normalizar(raw)` mapeia campos alternativos do JSON da API:

| Campo `PeticaoItem` | Campos tentados no JSON bruto |
|---|---|
| `numero_processo` | `processo.numero`, `processo.numeroProcesso`, `numeroProcesso`, `nrProcesso` |
| `tipo_peticao` | `nomeTipoProcessoDocumento`, `nomeTipoPeticao`, `descricaoTipoPeticao`, `tipoPeticao` |
| `tarefa` | `nomeTarefa`, `tarefa.nome`, `tarefa.descricao` |
| `fase` | `faseProcessual`, `fase`, `nomeFase`, `processo.fase` |
| `id_processo` | `processo.id`, `processo.idProcesso`, `idProcesso` |
| `polo` | `poloPeticionante` → normalizado para `"ativo"` / `"passivo"` / `None` |

### 16.4. Paginação automática

O JS itera até `min(totalPaginas, 10)` páginas. Para mais de 10 páginas, implemente loop externo.

---

## 17. Triagem de Petição Inicial — `triagem_peticao` (`tr.py`)

Análise completa de petição inicial trabalhista. Driver deve estar na página de detalhe do processo.

### 17.1. Uso

```python
from tr import triagem_peticao

resultado = triagem_peticao(driver)
print(resultado)  # max 8000 chars
```

**Saída estruturada:**
```
[COMPETENCIA]
CEP: 04.307-000 (4307000) - intervalo 4307000-4314999 Zona Sul [ultimo local de prestacao de servicos]

[Alertas]
- Documentos essenciais: ALERTA - falta procuracao em anexo (doc identidade: titulo)
- Rito processual: ALERTA - rito declarado SUMARISSIMO incompativel; correto: ORDINARIO ...

[ITENS OK]
- Partes: reclamante: FULANO DA SILVA CPF: 12345678901
- Reclamadas: OK - EMPRESA LTDA CNPJ 12.345.678/0001-99 (matriz)
```

### 17.2. Arquitetura interna

**Fluxo de coleta** (`_coletar_textos_processo`):

1. `session_from_driver(driver, grau=1)` → `PjeApiClient` (todos os GETs — sem XSRF)
2. `_extrair_id_processo_da_url(driver.current_url)` → regex `/processo/(\d+)`
3. `client.partes(id_processo)` → partes definitivas (sobrescreve dados da certidão)
4. `client.timeline(id_processo)` → lista de documentos (thread com timeout 30s)
5. Localizar petição inicial por tipo/título (`_eh_peticao_inicial`)
6. `GET /documentos/id/{id_doc}/conteudo` → bytes PDF
7. `pdfplumber` (nativo) → se média < 30 chars/pág → fallback `pytesseract+pdf2image`
8. Localizar `Certidão de Distribuição` (excluindo redistribuição) com mesma data da PI
9. `client.processo_por_id` → `valorCausa`, `juizoDigital`

**Extração de PDF** (`_extrair_texto_pdf_api`):

```python
# Endpoint
GET /pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_doc}/conteudo
# Content-Type esperado: application/pdf

# Estratégia em cascata:
# 1. pdfplumber.extract_text() — nativo, rápido
# 2. Se media_chars/pag < 30 → pytesseract OCR (lento, requer poppler)
```

**Dependências opcionais para OCR:**
```bash
pip install pdfplumber pytesseract pdf2image
# + Poppler: D:\poppler\bin (Windows) ou pdftoppm no PATH
```

### 17.3. Blocos de análise (B1–B14)

| Bloco | Função | O que verifica |
|---|---|---|
| B1 | `_checar_procuracao_e_identidade` | Procuração + doc identidade nos anexos (por título e conteúdo) |
| B2 | `_checar_cep` | Competência territorial — CEP dentro dos intervalos Zona Sul TRT2 |
| B3 | `_checar_partes` | Reclamante identificado; menor de idade; PJDP no polo passivo |
| B4 | `_checar_segredo` | Pedido de segredo de justiça + art. 189 CPC |
| B5 | `_checar_reclamadas` | CNPJ/CPF das reclamadas; filial sem matriz |
| B6 | `_checar_tutela` | Pedidos de tutela provisória/cautelar/liminar |
| B7 | `_checar_digital` | Pedido de Juízo 100% Digital vs. marcação na API |
| B8 | `_checar_pedidos_liquidados` | Pedidos com valores `R$` (excluindo valor da causa) |
| B9 | `_checar_pessoa_fisica` | Pessoa física no polo passivo sem fundamentação |
| B10 | `_checar_litispendencia` | Menção a outros processos CNJ; litispendência/coisa julgada |
| B11 | `_checar_responsabilidade` | Responsabilidade subsidiária/solidária quando > 1 reclamada |
| B12 | `_checar_endereco_reclamante` | Residência fora de SP; pedido de audiência virtual |
| B13 | `_checar_rito` | Rito declarado vs. calculado por valor da causa + PJDP |
| B14 | `_checar_art611b` | Menção ao art. 611-B CLT (lembrete obrigatório) |

**Constantes (2026):**

```python
SALARIO_MINIMO      = 1622.00
ALCADA              = SALARIO_MINIMO * 2      # R$ 3.244,00
RITO_SUMARISSIMO_MAX = SALARIO_MINIMO * 40   # R$ 64.880,00
```

### 17.4. Dados enriquecidos via API (prioridade sobre certidão)

`_coletar_textos_processo` sobrescreve os dados extraídos do PDF com os definitivos da API:

| Campo `capa_dados` | Fonte da API |
|---|---|
| `reclamante_nome`, `reclamante_cpf` | `partes.ATIVO[0].nome / documento` |
| `reclamados` (lista) | `partes.PASSIVO[*].{nome, cpfcnpj}` |
| `reclamado_nome`, `reclamado_cnpj` | `reclamados[0]` (compat. legado) |
| `valor_causa` | `processo.valorCausa / valorDaCausa / valor` |
| `juizo_digital` | `processo.juizoDigital` (bool normalizado) |

---

## Considerações Finais

- **Autenticação:** Todas as chamadas exigem que a sessão esteja autenticada. Utilize cookies de um navegador logado ou obtenha via Selenium.
- **Tratamento de erros:** As funções retornam `None` ou listas vazias em caso de falha; implemente verificações.
- **Limitações:** Nem todos os endpoints são públicos; alguns podem exigir permissões especiais (SIF, SISCONDJ). Para esses, é necessário estar logado como servidor.
- **Método HTTP crítico:** `agrupamentotarefas/10/processos` usa **PATCH** (não POST). `peticoesjuntadas` usa GET paginado.

Este guia consolida o conhecimento extraído da extensão maisPJe e das implementações reais em `apiaud.py`, `Peticao/api_client.py` e `tr.py`.