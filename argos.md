# Correção do Processamento Argos — v3

## Premissa Corrigida: Fluxo SISBAJUD

> [!CAUTION]
> O plano anterior estava errado sobre SISBAJUD. **Não existe** "buscar documento SISBAJUD nos anexos". O fluxo correto é:
>
> 1. A **Certidão de Devolução** JÁ ESTÁ SELECIONADA na timeline
> 2. Abrir anexos → tratar sigilo+visibilidade (infojud, etc.)
> 3. **Certidão de Devolução CONTINUA SELECIONADA** após fechar anexos
> 4. Ler a certidão via `extrair_direto` → texto para `processar_sisbajud`
> 5. Buscar documento (despacho/decisão) → aplicar regras Argos

A FASE 2 dentro de `tratar_anexos_argos` que busca um sub-documento "Certidão de devolução de ordem de pesquisa patrimonial" nos anexos e chama `extrair_pdf` é **uma invenção errada** que não existe no fluxo real. Deve ser removida.

---

## Referência

- Código correto: **EXCLUSIVAMENTE** `leg/Mandado/`
- Arquitetura: `idx.md` (P4: sem `time.sleep`, P8: imports no topo)
- Waits: `aguardar_renderizacao_nativa` — seção 6 do idx.md

---

## Divergências e Correções

### 1. 🔴 CRÍTICO — `tratar_anexos_argos` mistura sigilo com SISBAJUD

**Onde:** [fluxo_argos.py:375-431](file:///d:/PjePlus/Mandado/fluxo_argos.py#L375-L431) — FASE 2 do `tratar_anexos_argos`

**Problema:** `tratar_anexos_argos` contém uma "FASE 2: PROCESSAR SISBAJUD" que:
- Procura nos anexos por "Certidão de devolução de ordem de pesquisa patrimonial"
- Clica nesse sub-documento
- Chama `extrair_pdf(driver, log=False)` para extrair texto
- Processa SISBAJUD a partir desse PDF

**Isso está errado.** O SISBAJUD é analisado **lendo a certidão de devolução que já está aberta/selecionada na timeline**, via `extrair_direto`. Não há sub-documento a clicar.

**Correção:**

1. **Remover a FASE 2 inteira** de `tratar_anexos_argos` (linhas 375-431)
2. `tratar_anexos_argos` retorna APENAS informação de sigilo/visibilidade:

```python
return ResultadoExecucao(
    sucesso=True,
    status='OK',
    detalhes={
        'found_sigilo': found_sigilo,
        'sigilo_anexos': sigilo_anexos,
        'sigiloso': any_sigilo,
        'tem_anexos': tem_anexos
    }
)
```

3. **A análise SISBAJUD migra para `processar_argos`** como ETAPA 3 separada, usando `extrair_direto`:

```python
# === ETAPA 3: ANÁLISE SISBAJUD VIA CERTIDÃO DE DEVOLUÇÃO ===
# A certidão de devolução JÁ ESTÁ selecionada na timeline.
# Após tratamento de anexos (ETAPA 2), ela continua selecionada.
# Usar extrair_direto para ler o conteúdo da certidão.
logger.info('[ARGOS][ETAPA 3] Lendo certidão de devolução via extrair_direto para análise SISBAJUD...')

resultado_sisbajud = None
executados = []

try:
    resultado_extracao = extrair_direto(driver, timeout=10, debug=log, formatar=True)
    texto_certidao = resultado_extracao.get('conteudo') if resultado_extracao and resultado_extracao.get('sucesso') else None

    if texto_certidao:
        logger.info('[ARGOS][ETAPA 3] Certidão extraída: %d chars', len(texto_certidao))
        try:
            resultado_sisbajud, motivo, executados = processar_sisbajud(texto_certidao, log=False)
            if resultado_sisbajud == 'positivo':
                logger.info('[ARGOS][ETAPA 3] SISBAJUD POSITIVO')
            elif resultado_sisbajud == 'negativo':
                logger.info('[ARGOS][ETAPA 3] SISBAJUD NEGATIVO')
        except ValueError:
            resultado_sisbajud = None
            executados = []
        except Exception as e:
            logger.error('[ARGOS][ETAPA 3] Erro na análise SISBAJUD: %s', e)
            resultado_sisbajud = None
            executados = []
    else:
        logger.info('[ARGOS][ETAPA 3] Certidão sem conteúdo — SISBAJUD indisponível')
except Exception as e:
    logger.error('[ARGOS][ETAPA 3] Falha ao extrair certidão: %s', e)
```

---

### 2. 🔴 CRÍTICO — `processar_argos` extrai `resultado_sisbajud` do retorno de `tratar_anexos_argos`

**Onde:** [fluxo_argos.py:520-531](file:///d:/PjePlus/Mandado/fluxo_argos.py#L520-L531)

**Problema:** Após a correção #1, `tratar_anexos_argos` não retorna mais `resultado_sisbajud`. O código que extrai esse campo dos detalhes fica obsoleto.

**Correção:** Simplificar a extração de dados da ETAPA 2:

```diff
     # Extrair dados de anexos para decisão de rota
     if hasattr(anexos_info, 'detalhes') and isinstance(anexos_info.detalhes, dict):
-        resultado_sisbajud = anexos_info.detalhes.get('resultado_sisbajud', None)
         sigilo_anexos = anexos_info.detalhes.get('sigilo_anexos', {})
-        executados = anexos_info.detalhes.get('executados', [])
         tem_anexos = anexos_info.detalhes.get('tem_anexos', False)
     else:
-        resultado_sisbajud = anexos_info.get('resultado_sisbajud', None)
         sigilo_anexos = anexos_info.get('sigilo_anexos', {})
-        executados = anexos_info.get('executados', [])
         tem_anexos = anexos_info.get('tem_anexos', False)
```

E mover `resultado_sisbajud` e `executados` para a nova ETAPA 3 (correção #1).

---

### 3. 🔴 CRÍTICO — `import unicodedata` ausente em `regras.py`

**Onde:** [regras.py](file:///d:/PjePlus/Mandado/regras.py)

**Problema:** `estrategia_infojud` chama `unicodedata.normalize()` diretamente sem import. `NameError` em runtime. O LEG ([leg/Mandado/regras.py:29](file:///d:/PjePlus/leg/Mandado/regras.py#L29)) tem `import unicodedata`.

> [!IMPORTANT]
> P8: imports sempre no topo do módulo.

**Correção:** Adicionar `import unicodedata` no topo de `regras.py`.

---

### 4. 🟡 ALTO — Render barriers no loop de modal de visibilidade

**Onde:** [fluxo_argos.py:335-369](file:///d:/PjePlus/Mandado/fluxo_argos.py#L335-L369)

**Problema:** O loop de sigilo+visibilidade não tem barreiras de render suficientes entre operações DOM. Após clicar no ícone `+` para abrir modal, e após processar o modal, o DOM precisa estabilizar antes da próxima iteração.

**Correção (P4: sem `time.sleep`, usar `aguardar_renderizacao_nativa`):**

```diff
         if sigilo_foi_aplicado or tem_sigilo:
             try:
                 icone_plus = anexo.find_element(By.CSS_SELECTOR, _SELETORES_ANEXOS['icone_plus'])
                 driver.execute_script("arguments[0].click();", icone_plus)
+                # Barreira: modal aparecendo
+                aguardar_renderizacao_nativa(driver, _SELETORES_ANEXOS['modal_container'], modo='aparecer', timeout=4)

                 modal = _localizar_modal_visibilidade(driver, timeout=6)
                 if modal:
+                    # Barreira: checkboxes renderizados dentro do modal
+                    aguardar_renderizacao_nativa(driver, 'mat-checkbox', modo='aparecer', timeout=3)
                     modal_ok = _processar_modal_visibilidade(driver, modal, log=False)
                     if modal_ok:
                         any_sigilo = True
                         anexos_processados += 1
+                        # Barreira: modal fechou
+                        aguardar_renderizacao_nativa(driver, _SELETORES_ANEXOS['modal_container'], modo='sumir', timeout=3)
```

E em `_processar_modal_visibilidade`, adicionar barreira pré-salvar:
```diff
+        # Barreira pré-salvar: DOM estabilizado
+        aguardar_renderizacao_nativa(driver, timeout=1)
         btn_salvar = modal.find_element(By.XPATH, _SELETORES_ANEXOS['btn_salvar'])
```

---

### 5. 🟢 MÉDIO — Imports desnecessários após refatoração

**Onde:** [fluxo_argos.py:31](file:///d:/PjePlus/Mandado/fluxo_argos.py#L31)

**Problema:** Após remover FASE 2 (SISBAJUD) de `tratar_anexos_argos`, o import de `extrair_pdf` fica desnecessário.

**Correção:**

```diff
-from Fix.extracao import extrair_dados_processo, extrair_destinatarios_decisao, extrair_direto, extrair_pdf, salvar_destinatarios_cache
+from Fix.extracao import extrair_dados_processo, extrair_destinatarios_decisao, extrair_direto, salvar_destinatarios_cache
```

`processar_sisbajud` já é importado via `from .processamento_anexos import processar_sisbajud` ou precisa ser adicionado. Verificar import:

```diff
+from leg.Mandado.processamento_anexos import processar_sisbajud
```

Ou se `processar_sisbajud` está disponível localmente no Mandado ativo, usar esse import.

---

## Fluxo Corrigido (sequência final)

```
ETAPA 0: fechar_intimacao(driver)
   │
ETAPA 1: buscar_documentos_sequenciais (API → fallback DOM)
   │  resultado: documentos_sequenciais[]
   │
ETAPA 1.5: retirar_sigilo_fluxo_argos(driver, documentos_sequenciais)
   │  resultado: sigilo removido dos doc sequenciais
   │  ⚠ CERTIDÃO DE DEVOLUÇÃO CONTINUA SELECIONADA
   │
ETAPA 2: tratar_anexos_argos(driver, documentos_sequenciais)
   │  APENAS: abrir anexos → sigilo + visibilidade de infojud/especiais
   │  resultado: sigilo_anexos{}, tem_anexos
   │  NÃO faz SISBAJUD
   │  ⚠ CERTIDÃO DE DEVOLUÇÃO CONTINUA SELECIONADA
   │
ETAPA 3: ANÁLISE SISBAJUD (NOVO — extraída do tratar_anexos_argos)
   │  extrair_direto(driver) → texto da certidão de devolução
   │  processar_sisbajud(texto) → resultado_sisbajud
   │
ETAPA 4: buscar_documento_argos(driver, ignorar_indices=documentos_ignorados)
   │  Loop: abrir despacho/decisão → extrair → aplicar regras
   │  usa resultado_sisbajud + sigilo_anexos da ETAPA anterior
```

---

## Proposed Changes

### Mandado

#### [MODIFY] [fluxo_argos.py](file:///d:/PjePlus/Mandado/fluxo_argos.py)

| Região | Mudança |
|---|---|
| Imports L31 | Remover `extrair_pdf`, adicionar `processar_sisbajud` |
| `tratar_anexos_argos` L375-431 | **REMOVER** FASE 2 inteira (busca sub-doc + extrair_pdf + processar_sisbajud) |
| `tratar_anexos_argos` retorno L432-442 | Remover `resultado_sisbajud` e `executados` do `ResultadoExecucao` |
| Loop modal L335-369 | Adicionar barreiras `aguardar_renderizacao_nativa` |
| `_processar_modal_visibilidade` L98-132 | Adicionar barreira pré-salvar |
| `processar_argos` L520-531 | Simplificar extração de dados (sem `resultado_sisbajud`, sem `executados`) |
| `processar_argos` L538-544 | **REESCREVER ETAPA 3** — usar `extrair_direto` + `processar_sisbajud` |

#### [MODIFY] [regras.py](file:///d:/PjePlus/Mandado/regras.py)

| Região | Mudança |
|---|---|
| Imports L28 | Adicionar `import unicodedata` |

---

## Resumo

| # | Sev. | Arquivo | Problema | Fix |
|---|---|---|---|---|
| 1 | 🔴 | `fluxo_argos.py` | SISBAJUD buscado como sub-anexo via `extrair_pdf` | Remover FASE 2; SISBAJUD via `extrair_direto` da certidão na ETAPA 3 |
| 2 | 🔴 | `fluxo_argos.py` | `processar_argos` extrai `resultado_sisbajud` de `tratar_anexos_argos` | Mover para ETAPA 3 autônoma |
| 3 | 🔴 | `regras.py` | `import unicodedata` ausente → `NameError` | Adicionar import (P8) |
| 4 | 🟡 | `fluxo_argos.py` | Render barriers insuficientes no modal | `aguardar_renderizacao_nativa` com seletores (P4) |
| 5 | 🟢 | `fluxo_argos.py` | `extrair_pdf` import desnecessário | Remover import |

## Verification Plan

### Automated Tests
- `python -c "from Mandado.fluxo_argos import processar_argos"` — sem ImportError
- `python -c "from Mandado.regras import aplicar_regras_argos"` — sem NameError
- Grep: `extrair_pdf` ausente em `fluxo_argos.py`
- Grep: `extrair_direto` presente na ETAPA 3 de `processar_argos`
- Grep: `processar_sisbajud` importado em `fluxo_argos.py`

### Manual Verification
- Processo com certidão de devolução contendo SISBAJUD positivo: `extrair_direto` captura texto → `processar_sisbajud` retorna `positivo`
- Processo com certidão sem SISBAJUD: `processar_sisbajud` lança ValueError → `resultado_sisbajud = None` → rota padrão
- Processo com anexos infojud: sigilo+visibilidade aplicados sequencialmente sem erros de modal
