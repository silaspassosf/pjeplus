# Plano: `Fix.timeline` — Função Universal de Leitura de Timeline

**Data:** 13/04/2026  
**Técnica:** plano-divisao-etapas  
**Contexto:** Eliminar lógica duplicada de identificação/leitura de documentos na timeline entre `Mandado/` e `Prazo/p2b`.

---

## 1. Diagnóstico: Onde a lógica de timeline existe hoje

### 1a. `Mandado/processamento_api.py — _selecionar_doc_via_timeline(driver)`

```
Tipo: Selenium (DOM scraping)
O que faz:
  - Itera `li.tl-item-container` via find_elements
  - Lê link.text e classifica por substrings ('devolução de ordem' → argos, 'certidão de oficial' → outros)
  - Clica no link via safe_click_no_scroll
  - Retorna string 'argos' | 'outros' | None
Limitação: só classifica em 2 tipos, sem ler conteúdo do documento
```

### 1b. `Mandado/processamento_fluxo.py — fluxo_mandado() → _processar_atual()`

```
Tipo: Selenium (header scraping)
O que faz:
  - Navega até a aba do documento já aberto
  - Lê texto do <mat-card-title> (cabeçalho)
  - Decide fluxo por matches: 'argos', 'pesquisa patrimonial' → processar_argos; 'oficial de justiça' → fluxo_mandados_outros
Limitação: depende de estado do driver (aba já aberta), sem isolamento
```

### 1c. `Prazo/p2b_fluxo_documentos.py — _encontrar_documento_relevante(driver)`

```
Tipo: Selenium (DOM scraping)  
O que faz:
  - Itera `li.tl-item-container`
  - Extrai o PRIMEIRO <span> do link (tipo real, sem descrição enganosa)
  - Regex: r'^(despacho|decisão|sentença|conclusão)'
  - Retorna (item, link, idx)
Limitação: busca mais antigo→recente (idx 0 = mais antigo), sem conteúdo
```

### 1d. `Prazo/p2b_fluxo_documentos.py — _extrair_texto_documento(driver, doc_link)`

```
Tipo: Selenium (click + render + extração)
O que faz:
  - Clica no doc_link
  - Aguarda renderização Angular
  - Tenta extrair_direto → extrair_documento (2 estratégias)
  - Detecta __DOC_NAO_ASSINADO__ por ícone na timeline
  - Retorna texto ou None
Limitação: acoplado ao estado do driver, 2 fallbacks implícitos
```

### 1e. `Peticao/api/contexto.py — analisar_contexto_peticao()` (REFERÊNCIA)

```
Tipo: API pura (requests.Session)
O que faz:
  - 1 GET /timeline → lista completa de documentos c/ metadados (tipo, data, polo, id)
  - Filtra despacho/decisão/sentença (ponto de corte)
  - Coleta petições extras entre o despacho e o presente
  - Opcional: 1 GET /documentos/id/{id} por documento para obter conteúdo
  - Retorna ContextoPeticao (pode_agir, deve_aguardar, partes, etc.)
Vantagem: zero Selenium, zero click, zero render wait, dados ricos
```

---

## 2. Análise: O que cada módulo precisa

| Módulo | Input mínimo | Necessidade | Decisão de saída |
|--------|-------------|-------------|------------------|
| **Mandado** | id_processo / numero | Tipo do documento mais recente na timeline (argos vs outros) | str: 'argos' \| 'outros' \| None |
| **Prazo/p2b** | id_processo aberto no driver | Primeiro despacho/decisão/sentença + seu texto | texto: str \| None |
| **Peticao** | id_processo + id_peticao | Despacho anterior + petições extras + partes | ContextoPeticao completo |

---

## 3. Decisões de Arquitetura

1. **Localização:** `Fix/timeline.py` — neutro, sem dependência de domínio
2. **Transporte:** API via `requests.Session` (como `Peticao/api/client.py`), não Selenium DOM
3. **Session bootstrap:** extraída dos cookies do browser via JS (mesmo padrão de `Mandado/processamento_api.py::obter_mandados_devolvidos`) — uma função `_sessao_do_driver(driver)` converte cookies do driver em um `requests.Session`
4. **Sem duplicação de PjeApiClient:** `Fix/timeline.py` expõe funções diretas (não uma classe), reutilizando o `PjeApiClient` de `Peticao/api/client.py` internamente, OU reimplementando só o necessário para não criar dependência cruzada entre Fix e Peticao
5. **Assinatura rica:** todos os campos do API response disponíveis no retorno — chamador escolhe o que usa
6. **Caller zero-helper:** cada módulo chama 1 função, recebe dados prontos, sem precisar de helpers extras

---

## 4. Estrutura do Novo `Fix/timeline.py`

```python
# Fix/timeline.py

@dataclass
class DocTimeline:
    id_interno: str | None
    id_unico: str | None
    tipo: str              # 'Despacho', 'Sentença', 'Devolução de Ordem', etc.
    titulo: str
    data: str
    is_assinado: bool
    polo: str | None       # 'ativo' | 'passivo' | 'terceiro' | None
    nome_peticionante: str | None
    conteudo: str | None   # None se extrair_conteudo=False


def sessao_do_driver(driver) -> requests.Session:
    """Extrai cookies do Selenium WebDriver e retorna requests.Session autenticada."""

def obter_timeline(
    driver_ou_sessao,        # WebDriver (extrai cookies) OU requests.Session
    id_processo: str,
    *,
    buscar_movimentos: bool = False,
    apenas_assinados: bool = False,
) -> list[DocTimeline]:
    """1 GET — retorna todos os docs da timeline em ordem cronológica reversa."""

def encontrar_doc_por_tipo(
    timeline: list[DocTimeline],
    *,
    tipos: list[str],                     # ex: ['Despacho', 'Decisão', 'Sentença']
    padrao_regex: str | None = None,      # ex: r'^(despacho|decisão|sentença)'
    mais_recente: bool = True,            # True=idx0, False=mais antigo
    ignorar_nao_assinados: bool = True,
) -> DocTimeline | None:
    """Filtra e retorna o primeiro DocTimeline que satisfaz os critérios."""

def obter_conteudo_doc(
    driver_ou_sessao,
    id_processo: str,
    id_documento: str,
) -> str | None:
    """1 GET — retorna texto limpo de um documento específico."""

def obter_timeline_com_conteudo(
    driver_ou_sessao,
    id_processo: str,
    *,
    tipos_alvo: list[str],               # apenas esses tipos terão conteúdo baixado
    max_docs: int = 1,                   # limitar downloads para economizar
    mais_recente: bool = True,
) -> list[DocTimeline]:
    """
    Combina obter_timeline + obter_conteudo_doc para tipos_alvo.
    Evita N+1 quando só precisa de alguns documentos.
    """
```

---

## 5. Como cada módulo vai usar

### Mandado (substitui `_selecionar_doc_via_timeline`)

```python
# Mandado/processamento_api.py — NOVA VERSÃO
from Fix.timeline import obter_timeline, encontrar_doc_por_tipo

def _classificar_mandado_via_api(driver, id_processo) -> str | None:
    timeline = obter_timeline(driver, id_processo)
    
    argos = encontrar_doc_por_tipo(timeline, padrao_regex=r'devolução de ordem|devolucao de ordem|certidão de devolução')
    if argos:
        return 'argos'
    
    outros = encontrar_doc_por_tipo(timeline, padrao_regex=r'certidão de oficial|oficial de justiça')
    if outros:
        return 'outros'
    
    return None
```

### Prazo/p2b (substitui `_encontrar_documento_relevante` + `_extrair_texto_documento`)

```python
# Prazo/p2b_fluxo_documentos.py — NOVA VERSÃO
from Fix.timeline import obter_timeline_com_conteudo

def encontrar_despacho_com_texto(driver, id_processo) -> tuple[DocTimeline | None, str | None]:
    docs = obter_timeline_com_conteudo(
        driver, id_processo,
        tipos_alvo=['Despacho', 'Decisão', 'Sentença', 'Conclusão'],
        max_docs=1,
        mais_recente=False,  # p2b busca do mais antigo → recente
    )
    doc = docs[0] if docs else None
    return doc, (doc.conteudo if doc else None)
```

### Peticao (já tem sua própria lógica, pode reusar parcialmente)

```python
# Peticao/api/contexto.py — pode reusar obter_timeline e obter_conteudo_doc
# mas mantém ContextoPeticao e analisar_contexto_peticao intactos
# (não é objetivo deste plano refatorar Peticao)
```

---

## 6. Task List

### Fase 1: Análise e fundação

#### Task 1: Mapear endpoints exatos usados (XS)
**Descrição:** Confirmar campos reais do JSON de timeline para cada tipo de documento.  
**Critérios de aceitação:**
- [ ] Listar todos os campos presentes em `DocTimeline` que existem no JSON real da API
- [ ] Confirmar que `tipo`, `titulo`, `data`, `id`, `idUnicoDocumento` existem no response
- [ ] Confirmar endpoint `/conteudo` ou campos inline para texto do documento

**Verificação:** `py -c "from Fix.timeline import obter_timeline; print('ok')"`  
**Dependências:** Nenhuma  
**Arquivos:** `Fix/timeline.py` (novo)  
**Escopo:** S

---

#### Task 2: Implementar `sessao_do_driver` e `obter_timeline`
**Descrição:** Função que extrai cookies do driver Selenium e faz GET na timeline via requests.  
**Critérios de aceitação:**
- [ ] `sessao_do_driver(driver)` retorna `requests.Session` com cookies e headers XSRF
- [ ] `obter_timeline(driver, id_processo)` retorna `list[DocTimeline]` sem raises se timeline vazia
- [ ] Campos `tipo`, `titulo`, `data`, `id_interno`, `id_unico`, `is_assinado` preenchidos
- [ ] Reutiliza mesma lógica de extração XSRF de `Mandado/processamento_api.py`

**Verificação:** `py -m py_compile Fix/timeline.py`  
**Dependências:** Task 1  
**Arquivos:** `Fix/timeline.py`  
**Escopo:** S

---

#### Task 3: Implementar `encontrar_doc_por_tipo` e `obter_conteudo_doc`
**Descrição:** Filtro e download de conteúdo de documento individual.  
**Critérios de aceitação:**
- [ ] `encontrar_doc_por_tipo` aceita `tipos` (lista exata) OU `padrao_regex` (re.search)
- [ ] Parâmetro `mais_recente=True` retorna idx 0; `False` retorna o mais antigo que satisfaz
- [ ] `obter_conteudo_doc` tenta campos JSON inline antes de fazer GET para `/conteudo`
- [ ] Limpa HTML com regex simples (sem BeautifulSoup)

**Verificação:** `py -m py_compile Fix/timeline.py`  
**Dependências:** Task 2  
**Arquivos:** `Fix/timeline.py`  
**Escopo:** S

---

#### Task 4: Implementar `obter_timeline_com_conteudo`
**Descrição:** Conveniência que combina timeline + conteúdo para tipos selecionados.  
**Critérios de aceitação:**
- [ ] Faz apenas 1 GET de timeline + N GETs de conteúdo (N ≤ max_docs)
- [ ] `tipos_alvo` é case-insensitive e suporta match parcial via `re.search`
- [ ] Retorna lista de `DocTimeline` com `.conteudo` preenchido para os alvos

**Dependências:** Task 2, Task 3  
**Arquivos:** `Fix/timeline.py`  
**Escopo:** XS

---

### Checkpoint Fase 1
- [ ] `py -m py_compile Fix/timeline.py` sem erros
- [ ] Importações funcionam: `py -c "from Fix.timeline import obter_timeline, encontrar_doc_por_tipo, obter_timeline_com_conteudo"`

---

### Fase 2: Integração com Mandado

#### Task 5: Substituir `_selecionar_doc_via_timeline` por chamada via API
**Descrição:** Refatorar `Mandado/processamento_api.py` para usar `Fix.timeline`.  
**Critérios de aceitação:**
- [ ] `_selecionar_doc_via_timeline` removida ou mantida apenas como fallback Selenium
- [ ] Nova função `_classificar_mandado_api(driver, id_processo)` usa `obter_timeline`
- [ ] `processar_mandado_detalhe` chama nova função antes de abrir a aba do processo
- [ ] Sem regressão: classificação 'argos' | 'outros' | None mantida

**Dependências:** Task 2, Task 3  
**Arquivos:** `Mandado/processamento_api.py`  
**Escopo:** S

---

### Fase 3: Integração com Prazo/p2b

#### Task 6: Substituir `_encontrar_documento_relevante` + `_extrair_texto_documento`
**Descrição:** Refatorar `Prazo/p2b_fluxo_documentos.py` para usar `Fix.timeline`.  
**Critérios de aceitação:**
- [ ] Funções Selenium legadas ficam como fallback (não são removidas — p2b ainda abre proc no browser)
- [ ] Nova função `_encontrar_despacho_api(driver, id_processo)` usa `obter_timeline_com_conteudo`
- [ ] `fluxo_pz` tenta API primeiro; cai para Selenium se `id_processo` indisponível
- [ ] `_documento_nao_assinado` ainda detectável via campo `is_assinado` de `DocTimeline`

**Dependências:** Task 4  
**Arquivos:** `Prazo/p2b_fluxo_documentos.py`, `Prazo/p2b_fluxo.py`  
**Escopo:** M

---

### Checkpoint Fase 3
- [ ] Importações sem erro em Mandado e Prazo
- [ ] `py -m py_compile Mandado/processamento_api.py Prazo/p2b_fluxo_documentos.py`

---

## 7. Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Response JSON da timeline tem campos diferentes em alguns processos | Médio | Usar `.get()` com defaults em todos os campos de `DocTimeline` |
| XSRF token expirado entre requests | Médio | Re-extrair cookie do driver a cada chamada (não cachear sessão) |
| Texto do documento disponível apenas via PDF (não JSON) | Alto | Manter `_extrair_texto_documento` Selenium como fallback em p2b |
| `id_processo` numérico interno não disponível na tarefa GIGS sem prazo | Médio | Resolver via `GET /processos?numero={cnj}` (já existe no PjeApiClient) |
| Campos `poloPeticionante` inconsistentes entre endpoints | Baixo | Opcional — Mandado e p2b não precisam de polo |

---

## 8. Respostas confirmadas

- **`tipo`**: campo genérico (ex: 'Certidão'). A descrição completa ('Devolução de Ordem de Pesquisa Patrimonial') fica em **`titulo`**. `encontrar_doc_por_tipo` busca em `"{tipo} {titulo}"` para cobrir ambos.
- **Conteúdo do documento**: endpoint retorna HTML ou PDF. Se PDF → `obter_conteudo_doc` retorna `'__PDF__'` como sinal; caller usa fallback Selenium (`extrair_direto`).
- **`id_processo`**: disponível na URL do browser atual → `re.search(r'/processo/(\d+)/', driver.current_url)`. Função `id_processo_da_url(driver)` em `Fix/timeline.py`.

## 9. Status de implementação

- [x] **Fase 1 completa** → `Fix/timeline.py` criado e validado (`py -m py_compile Fix/timeline.py`)
- [ ] Task 5 — Integrar Mandado
- [ ] Task 6 — Integrar Prazo/p2b
