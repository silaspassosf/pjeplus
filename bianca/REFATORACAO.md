# Plano de Refatoração — `bianca/`

**Data:** 2026-05-04 (revisado: flow-based)  
**Objetivo:** Eliminar código morto, preservar o caminho ativo sem quebrar nada.

---

## Confirmação via Legado (git commit aaeb61a)

Antes de `bianca/` existir, o fluxo vinha de `Triagem/` (14 arquivos separados):

```
x.py → Triagem.runner.run_triagem
       → Triagem.runtime_triagem.run_triagem
            → Triagem.service.triagem_peticao
                 → Triagem.coleta._coletar_textos_processo   ← COM OCR
                 → Triagem.regras._checar_*
            → Triagem.regras.determinar_acao_pos_triagem     ← via alerta_registry
            → Triagem.acoes.acao_bucket_a/b/c/d
```

`bianca/triagem_engine.py` é a **consolidação monolítica** desses 14 arquivos num único módulo. Confirmado: todas as `_checar_*`, `acao_bucket_*` e `buscar_lista_triagem` foram portadas.

### O que `bianca/triagem_regras.py` realmente é

Não é código gerado do nada — é uma **segunda tentativa de port do legado**, feita independentemente, que reproduz:
- `Triagem/regras.py` → as `_checar_*` (idênticas ao que o engine já tem)
- `Triagem/coleta.py` → `_coletar_textos_processo` com o pipeline OCR completo
- `Triagem/utils.py` → `_norm` na versão original-equivalente

Nunca foi conectada ao fluxo. Por isso nunca é importada.

---

## Fluxo Real Atual

```
x.py (linha 50)
  └─ from bianca.triagem_engine import run_triagem
       └─ run_triagem(driver)
            └─ triagem_peticao(driver)
                 └─ _coletar_textos_processo(driver)   ← engine local, SEM OCR
                 └─ _checar_*(...)                      ← engine local (todas)
```

`triagem_regras.py` **nunca é importado** por nenhum arquivo do fluxo ativo.  
Confirmado: `grep -r "triagem_regras"` no projeto retorna apenas o próprio arquivo (autodescrição no docstring).

---

## Situação Real dos "25 Duplicados"

As 25 funções que aparecem em ambos os arquivos **não são duplicatas a remover do engine** — são a implementação ativa. O `triagem_engine.py` é auto-contido por design e é o código que roda.

`triagem_regras.py` é código morto. Contém as mesmas 25 funções + pipeline OCR que nunca chega a ser chamado.

---

## Diferenças entre as Cópias (onde importa)

### `_norm`
| Arquivo | Algoritmo |
|---------|-----------|
| **Legado** `Triagem/utils.py` (original) | `NFD + encode('ascii','ignore').decode().lower()` |
| `triagem_engine.py` (ativo) | `NFKD + re.sub(r'[^\w\s]', '', s)` — divergiu do original |
| `triagem_regras.py` (morto) | `NFD + unicodedata.category(c) != "Mn"` — equivalente ao original, mais Pythonica |

### `_coletar_textos_processo`
| Arquivo | Implementação |
|---------|---------------|
| `triagem_engine.py` (ativo) | `client.documento_por_id()` → extrai texto/HTML via API REST |
| `triagem_regras.py` (morto) | `_extrair_texto_pdf_api()` → `pdfplumber` → `_ocr_via_pymupdf()` — pipeline PDF/OCR completo, threading 30s, re-auth 401, enriquecimento de endereço das partes |

A versão do engine funciona para processos onde a API retorna texto. A versão de regras seria necessária apenas para PDFs digitalizados/escaneados — cenário não coberto pelo fluxo atual.

---

## Decisões Assertivas

### Decisão 1: `triagem_regras.py` é código morto → DELETAR

`triagem_regras.py` não é importado por ninguém no fluxo ativo. As "25 funções duplicadas" que ele contém são cópias das versões do engine — o engine não depende delas. Manter o arquivo cria confusão sobre qual versão é canônica.

**Ação: deletar `bianca/triagem_regras.py`.**

### Decisão 2: As 25 funções no `triagem_engine.py` NÃO são removidas

Elas são a implementação de produção. Não há o que remover: o engine é auto-contido e é o que `x.py` chama.

### Decisão 3: Extrair pipeline PDF/OCR antes de deletar regras

A capacidade OCR de `triagem_regras.py` (`_garantir_tessdata_por` + `_ocr_via_pymupdf` + `_extrair_texto_pdf_api`) não existe no engine. Se a API retornar vazio para um processo com PDF digitalizado, o engine falha silenciosamente.

**Ação: mover as 3 funções OCR para `triagem_engine.py` como fallback em `_coletar_textos_processo`**, ativado quando `documento_por_id` retorna texto vazio.

### Decisão 4: Corrigir `_norm` no engine

A versão NFD+category de `triagem_regras.py` é mais correta. Como é uma função utilitária de texto, a substituição é segura.

**Ação: substituir `_norm` em `triagem_engine.py` pela versão NFD+category.**

### Decisão 5: CEP constants — nada a fazer

`triagem_engine.py` já importa `ZONA_SUL_CEPS`, `ZONA_LESTE_CEPS`, `RUI_BARBOSA_CEPS` de `bianca.config`. Quando `triagem_regras.py` for deletado, as cópias internas dele somem junto. Nenhuma ação adicional.

---

## Impacto nos Arquivos

| Arquivo | Ação | Resultado |
|---------|------|-----------|
| `triagem_regras.py` | **DELETAR** | 2182 linhas eliminadas |
| `triagem_engine.py` | Adicionar 3 funções OCR + corrigir `_norm` | +~80 linhas (de 1632 para ~1710) |

---

## Plano de Execução

### Tarefa 1 — Mover pipeline PDF/OCR para `triagem_engine.py`

**Escopo:** Copiar as 3 funções de `triagem_regras.py` e conectar como fallback em `_coletar_textos_processo`.

**Funções a mover:**
- `_garantir_tessdata_por(lang)` (linha 414 de regras)
- `_ocr_via_pymupdf(pdf_bytes, lang)` (linha 440 de regras)
- `_extrair_texto_pdf_api(client, id_processo, id_doc)` (linha 505 de regras)

**Ponto de inserção em `triagem_engine.py`:** após o bloco de extração de `texto_inicial` em `_coletar_textos_processo`. Se `texto_inicial` ficar vazio após `documento_por_id`, tentar `_extrair_texto_pdf_api`.

```python
# fallback OCR — se API retornou texto vazio
if not texto_inicial and id_inicial:
    try:
        texto_inicial = _extrair_texto_pdf_api(client, id_processo, id_inicial) or ''
        if texto_inicial:
            logger.debug('[TRIAGEM] texto_inicial via OCR: %s chars', len(texto_inicial))
    except Exception as e:
        logger.warning('[TRIAGEM] OCR fallback falhou: %s', e)
```

**Dependências externas necessárias:** `pdfplumber`, `fitz` (PyMuPDF), `pytesseract` — já usados em `triagem_regras.py`, verificar se estão no ambiente.

**Verificação:**
- [ ] `py -m py_compile bianca/triagem_engine.py`
- [ ] `py -c "from bianca.triagem_engine import run_triagem"`

**Dependências:** Nenhuma  
**Estimativa:** S

---

### Tarefa 2 — Corrigir `_norm` em `triagem_engine.py`

**Escopo:** Substituir a implementação atual de `_norm` (linha ~48) pela versão NFD+category.

**Antes (engine):**
```python
def _norm(s: str) -> str:
    s = unicodedata.normalize('NFKD', s)
    return re.sub(r'[^\w\s]', '', s).lower()
```

**Depois (versão regras, mais correta):**
```python
def _norm(s: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    )
```

**Verificação:**
- [ ] `py -m py_compile bianca/triagem_engine.py`
- [ ] Resultado de `_norm('procuração')` deve ser `'procuracao'` (sem cedilha, sem acento, sem pontuação)

**Dependências:** Nenhuma (independente da Tarefa 1)  
**Estimativa:** XS

---

### Tarefa 3 — Deletar `triagem_regras.py`

**Pré-condição:** Tarefas 1 e 2 concluídas e validadas.

**Ação:** `del bianca\triagem_regras.py`

**Verificação:**
- [ ] `py -c "from bianca.triagem_engine import run_triagem"` — sem erro
- [ ] `py -c "from bianca import triagem_regras"` — deve dar `ModuleNotFoundError` (confirmação de remoção)
- [ ] `py -m py_compile bianca/triagem_engine.py`

**Dependências:** Tarefas 1 e 2  
**Estimativa:** XS

**Dependências:** Tarefa 1  
**Estimativa:** S (leitura comparativa + ajuste pontual se necessário)

---

### Fase 2: Remover duplicatas de `triagem_engine.py`

---

#### Tarefa 3: Adicionar imports das funções movidas no topo de `triagem_engine.py`

**Descrição:** Adicionar bloco de import de `bianca.triagem_regras` no cabeçalho de `triagem_engine.py` para todas as 25 funções que serão removidas.

**Funções a importar:**
```python
from bianca.triagem_regras import (
    _norm,
    _remover_artefatos_pje,
    _aprender_cabecalho,
    _remover_cabecalho_por_pagina,
    _strip_cabecalho_rodape,
    _pag_contexto,
    _extrair_id_processo_da_url,
    _coletar_textos_processo,
    _foro_competente,
    _cep_tag,
    _checar_cep,
    _detectar_pjdp_api,
    _checar_partes,
    _checar_segredo,
    _checar_reclamadas,
    _checar_tutela,
    _checar_digital,
    _checar_rito,
    _checar_art611b,
    _checar_pedidos_liquidados,
    _checar_pessoa_fisica,
    _checar_litispendencia,
    _checar_responsabilidade,
    _checar_endereco_reclamante,
    _checar_procuracao_e_identidade,
)
```

**Acceptance criteria:**
- [ ] Import adicionado sem erros de sintaxe
- [ ] `py -m py_compile bianca/triagem_engine.py` passa (antes de remover as definições)

**Dependências:** Tarefa 2  
**Estimativa:** XS

---

#### Tarefa 4: Remover as 25 definições duplicadas de `triagem_engine.py`

**Descrição:** Deletar cada uma das 25 funções do corpo de `triagem_engine.py`. Manter apenas as 22 funções exclusivas do motor.

**Funções a remover de `triagem_engine.py`** (linhas aproximadas):
- `_norm` (linha 48)
- `_remover_artefatos_pje` (linha 85)
- `_aprender_cabecalho` (linha 89)
- `_remover_cabecalho_por_pagina` (linha 127)
- `_strip_cabecalho_rodape` (linha 135)
- `_pag_contexto` (linha 581)
- `_extrair_id_processo_da_url` (linha 1271)
- `_coletar_textos_processo` (linha 1278)
- `_foro_competente` (linha 613)
- `_cep_tag` (linha 623)
- `_checar_cep` (linha 637)
- `_detectar_pjdp_api` (linha 773)
- `_checar_partes` (linha 783)
- `_checar_segredo` (linha 845)
- `_checar_reclamadas` (linha 859)
- `_checar_tutela` (linha 891)
- `_checar_digital` (linha 913)
- `_checar_rito` (linha 932)
- `_checar_art611b` (linha 974)
- `_checar_pedidos_liquidados` (linha 982)
- `_checar_pessoa_fisica` (linha 1038)
- `_checar_litispendencia` (linha 1210)
- `_checar_responsabilidade` (linha 1062)
- `_checar_endereco_reclamante` (linha 1119)
- `_checar_procuracao_e_identidade` (linha 520)

**Acceptance criteria:**
- [ ] Nenhuma das 25 funções permanece definida em `triagem_engine.py`
- [ ] `py -m py_compile bianca/triagem_engine.py` passa
- [ ] `py -c "from bianca.triagem_engine import run_triagem"` passa sem erro

**Verificação:**
- [ ] Contagem de linhas: `triagem_engine.py` < 900 linhas

**Dependências:** Tarefa 3  
**Estimativa:** M (edição cuidadosa de arquivo grande)

---

### Fase 3: Validação

---

#### Tarefa 5: Verificar integridade de imports circulares

**Descrição:** Confirmar que não há imports circulares entre `triagem_regras.py` e `triagem_engine.py` após a mudança.

**Acceptance criteria:**
- [ ] `triagem_regras.py` NÃO importa de `triagem_engine`
- [ ] `triagem_engine.py` importa de `triagem_regras` (correto e unidirecional)
- [ ] `main.py` continua funcionando: `py -c "import bianca.main"`

**Verificação:**
```bash
py -c "from bianca.triagem_engine import run_triagem, triagem_peticao; print('OK')"
py -c "from bianca.triagem_regras import determinar_acao_pos_triagem, _coletar_textos_processo; print('OK')"
py -m py_compile bianca/triagem_regras.py bianca/triagem_engine.py bianca/main.py
```

**Dependências:** Tarefa 4  
**Estimativa:** XS

---

#### Tarefa 6: Limpeza de imports não usados em `triagem_engine.py`

**Descrição:** Após remover as 25 funções, alguns imports do topo de `triagem_engine.py` podem ter ficado órfãos (ex: `import threading`, constantes de CEP que eram usadas só nas funções removidas).

**Acceptance criteria:**
- [ ] Imports não utilizados removidos
- [ ] `py -m py_compile bianca/triagem_engine.py` passa

**Dependências:** Tarefa 4  
**Estimativa:** XS

---

### Checkpoint Final

- [ ] `py -m py_compile bianca/triagem_regras.py` — OK
- [ ] `py -m py_compile bianca/triagem_engine.py` — OK
- [ ] `py -c "from bianca.triagem_engine import run_triagem"` — OK
- [ ] `py -c "from bianca.triagem_regras import determinar_acao_pos_triagem"` — OK
- [ ] `triagem_engine.py` < 900 linhas
- [ ] Nenhuma das 25 funções duplicadas definida duas vezes

---

## Limpeza da Pasta (fora das tarefas acima)

A pasta `bianca/` está limpa. Nenhum arquivo órfão identificado:
- `logs/` — vazia (propositalmente, para receber logs em runtime)
- `drivers/` — contém `geckodriver.exe` (necessário)
- `__pycache__/` — gerado automaticamente, ignorar

**Não há arquivos para remover.**

---

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Versão de `_norm` diverge e quebra comportamento | Médio | `triagem_regras.py` usa NFD (mais correto); testar `_norm("Ação")` == `"acao"` em ambas antes de remover |
| `_checar_cep` da engine tem lógica extra não percebida | Alto | Leitura linha a linha das duas versões antes de remover a do engine |
| Import circular se `triagem_regras.py` acidentalmente importar `triagem_engine` | Alto | Grep antes de finalizar |
| Constantes CEP duplicadas (engine usa `ZONA_SUL_CEPS` de `config.py`; regras define as próprias) | Médio | Confirmar que ambos os módulos apontam para mesma fonte após limpeza |

---

## Observações

- A ressalva mencionada pelo usuário está correta e é exatamente o que este plano formaliza.
- Após esta refatoração, `triagem_regras.py` se torna a fonte única de verdade para coleta + regras, e `triagem_engine.py` se torna um orquestrador puro.
- Nenhuma função pública é renomeada — contratos externos preservados.
