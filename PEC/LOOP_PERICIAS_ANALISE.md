# DOCUMENTAÇÃO: LOOP DE PERÍCIAS - PET_NOVO.PY

**Última atualização:** 2025-01-30  
**Arquivo principal:** `PEC/pet_novo.py` (1399 linhas)  
**Escopo:** Loop de processamento automático de petições com foco em **PERÍCIAS**

---

## 📋 ÍNDICE

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [BLOCO 1: PERÍCIAS (Loop Principal)](#2-bloco-1-perícias-loop-principal)
3. [Estrutura de Hipóteses](#3-estrutura-de-hipóteses)
4. [Mapeamento de Ações](#4-mapeamento-de-ações)
5. [Fluxo de Processamento Completo](#5-fluxo-de-processamento-completo)
6. [Condições por Hipótese](#6-condições-por-hipótese)
7. [Ações por Hipótese](#7-ações-por-hipótese)

---

## 1. VISÃO GERAL DA ARQUITETURA

### Estrutura de 5 BLOCOS em pet_novo.py

O processamento de petições é dividido em **5 BLOCOS EXECUTADOS SEQUENCIALMENTE**:

```
┌─────────────────────────────────────────────────────────────────┐
│  BLOCO 1: PERÍCIAS (REGRA 3)          ← FOCO DESTA ANÁLISE     │
├─────────────────────────────────────────────────────────────────┤
│  BLOCO 2: GIGS (REGRA 5)              ← Homologação/Liberação  │
├─────────────────────────────────────────────────────────────────┤
│  BLOCO 3: RECURSO (REGRA 2)           ← Agravos/Apelações     │
├─────────────────────────────────────────────────────────────────┤
│  BLOCO 4: DIRETOS (Placeholder)       ← A implementar          │
├─────────────────────────────────────────────────────────────────┤
│  BLOCO 5: ANÁLISE (REGRA 4)           ← Manifestações          │
├─────────────────────────────────────────────────────────────────┤
│  BLOCO 0: APAGAR (REGRA 1) - ÚLTIMO   ← Segurança (último)     │
└─────────────────────────────────────────────────────────────────┘
```

**Por que APAGAR é executado por último?** Para evitar mudança de índices que quebraria referências das outras regras.

---

## 2. BLOCO 1: PERÍCIAS (Loop Principal)

### Localização no código
- **Arquivo:** `PEC/pet_novo.py`
- **Função:** `executar_regras()` (linhas 870-920)
- **Seção:** "BLOCO 1: PERÍCIAS"

### Pseudocódigo do Loop de Perícias

```python
def executar_regras(driver: WebDriver, peticoes: List[PeticaoLinha]) -> bool:
    # ... (setup)
    
    # ===== BLOCO 1: PERÍCIAS =====
    print("BLOCO 1: PERÍCIAS")
    regra_pericias = resultado["pericias"]
    
    FOR cada hipótese em regra_pericias:
        IF hipótese tem petições:
            FOR cada petição na hipótese:
                # Abre aba de detalhes
                abrir_detalhe_petição(driver, peticao)
                
                # Executa a ação (conforme hipótese)
                executar_acao_pericias(driver, peticao)
                
                # Fecha aba e volta à lista
                fechar_e_voltar_lista(driver)
                
                time.sleep(0.5)
```

### Fluxo de Processamento por Petição

```
┌──────────────────────────────────────┐
│  Petição Extraída do Escaninho       │
│  (número_processo, tipo_peticao,     │
│   descricao, tarefa, fase)           │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  Verificar contra 4 Hipóteses de     │
│  PERÍCIAS (padrões regex)            │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  Se bater em 1+ hipótese:            │
│  → Agrupar em resultado["pericias"]  │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  Processar em BLOCO 1:               │
│  1. Abrir aba de detalhes            │
│  2. Executar ação (por hipótese)     │
│  3. Fechar aba e voltar              │
└──────────────────────────────────────┘
```

---

## 3. ESTRUTURA DE HIPÓTESES

### Regra PERÍCIAS: 4 Hipóteses

Definido em `definir_regras()` (linhas 529-560):

**⚠️ ORDEM IMPORTANTE:** As hipóteses são ordenadas de **MAIS ESPECÍFICA para MENOS ESPECÍFICA** para evitar que uma genérica absorva uma específica.

```python
regra_pericias_hipoteses = [
    # HIPÓTESE 1: Apresentação de Esclarecimentos ao Laudo Pericial + Fase Conhecimento
    # (MAIS ESPECÍFICA - testada PRIMEIRA porque tem 2 condições)
    (
        "Esclarecimentos ao Laudo - Conhecimento",
        [
            gerar_regex_flexivel('apresentação de esclarecimentos ao laudo pericial'),
            gerar_regex_flexivel('conhecimento')
        ]
    ),
    
    # HIPÓTESE 2: Apresentação de Esclarecimentos ao Laudo Pericial + Fase Liquidação
    # (MAIS ESPECÍFICA - testada SEGUNDA porque tem 2 condições)
    (
        "Esclarecimentos ao Laudo - Liquidação",
        [
            gerar_regex_flexivel('apresentação de esclarecimentos ao laudo pericial'),
            gerar_regex_flexivel('liquidação')
        ]
    ),
    
    # HIPÓTESE 3: Apresentação de Laudo Pericial
    # (MENOS ESPECÍFICA - testada TERCEIRA porque é genérica)
    (
        "Apresentação de Laudo Pericial",
        [gerar_regex_flexivel('apresentação de laudo pericial')]
    ),
    
    # HIPÓTESE 4: Indicação de Data de Realização
    # (ESPECÍFICA - testada QUARTA)
    (
        "Indicação de Data de Realização",
        [gerar_regex_flexivel('indicação de data de realização')]
    ),
]
```

**Por que essa ordem?** 
- Se uma petição contém "Apresentação de Esclarecimentos ao Laudo Pericial + Conhecimento", ela também contém "Apresentação de Laudo Pericial"
- Sem a reordenação correta, a HIPÓTESE 3 genérica absorveria a HIPÓTESE 1 específica
- Com a reordenação, a HIPÓTESE 1 (específica) é testada ANTES
    
    # HIPÓTESE 2: Apresentação de Esclarecimentos ao Laudo Pericial + Fase Conhecimento
    (
        "Esclarecimentos ao Laudo - Conhecimento",
        [
            gerar_regex_flexivel('apresentação de esclarecimentos ao laudo pericial'),
            gerar_regex_flexivel('conhecimento')
        ]
    ),
    
    # HIPÓTESE 3: Apresentação de Esclarecimentos ao Laudo Pericial + Fase Liquidação
    (
        "Esclarecimentos ao Laudo - Liquidação",
        [
            gerar_regex_flexivel('apresentação de esclarecimentos ao laudo pericial'),
            gerar_regex_flexivel('liquidação')
        ]
    ),
    
    # HIPÓTESE 4: Indicação de Data de Realização
    (
        "Indicação de Data de Realização",
        [gerar_regex_flexivel('indicação de data de realização')]
    ),
]
```

---

## 4. MAPEAMENTO DE AÇÕES

### Ações Específicas para Cada Hipótese

Definido em `definir_regras()` (linhas 620-628):

```python
acoes_pericias = [
    ato_laudo if ato_laudo else lambda driver, pet: False,      
    # ↑ HIPÓTESE 1: ato_laudo

    ato_esc if ato_esc else lambda driver, pet: False,          
    # ↑ HIPÓTESE 2: ato_esc (Esclarecimentos - Conhecimento)

    ato_escliq if ato_escliq else lambda driver, pet: False,    
    # ↑ HIPÓTESE 3: ato_escliq (Esclarecimentos - Liquidação)

    acao_pericias_com_data,                                     
    # ↑ HIPÓTESE 4: Ação Composta (criar_gigs + ato_datalocal)
]

regra_pericias = [
    (nome, padroes, acao)
    for (nome, padroes), acao in zip(regra_pericias_hipoteses, acoes_pericias)
]
```

**Resultado:** Lista de tuplas `(nome_hipotese, padroes_regex, acao_funcao)`

---

## 5. FLUXO DE PROCESSAMENTO COMPLETO

### A. Fase de Agrupamento (`agrupar_por_regra()`)

```python
def agrupar_por_regra(peticoes: List[PeticaoLinha]) -> Dict[str, Any]:
    """
    Agrupa petições pelas 5 REGRAS.
    Retorna: {
        "pericias": {
            "peticoes_por_hipotese": {
                "Apresentação de Laudo Pericial": [pet1, pet2, ...],
                "Esclarecimentos ao Laudo - Conhecimento": [pet3, ...],
                ...
            },
            "peticoes_sem_hipotese": [],
            "total": N
        },
        ...
    }
    """
    
    for peticao in peticoes:
        for nome_regra in regras.keys():
            for nome_hipotese, padroes, acao in regras[nome_regra]:
                
                # Verifica se petição bate com hipótese
                if verifica_peticao_contra_hipotese(peticao, padroes):
                    resultado[nome_regra]["peticoes_por_hipotese"][nome_hipotese].append(peticao)
                    break  # Uma petição só pode pertencer a UMA regra
```

**Critério de Correspondência:** Uma petição é testada contra padrões da regra em sequência:
- Se TODOS os padrões da hipótese forem encontrados (AND lógico) → corresponde
- Se corresponde → adiciona à hipótese e passa para próxima petição

### B. Fase de Processamento (`executar_regras()` - BLOCO 1)

```python
def executar_regras(driver: WebDriver, peticoes: List[PeticaoLinha]) -> bool:
    # ... (linhas 870-920)
    
    # ===== BLOCO 1: PERÍCIAS =====
    regra_pericias = resultado["pericias"]
    hipoteses_pericias = {nome: acao for nome, padroes, acao in regras["pericias"]}
    
    for nome_hipotese, peticoes_da_hipotese in regra_pericias["peticoes_por_hipotese"].items():
        if not peticoes_da_hipotese:
            continue  # Pula se hipótese está vazia
        
        print(f"• {nome_hipotese}: {len(peticoes_da_hipotese)}")
        acao = hipoteses_pericias.get(nome_hipotese)
        
        sucesso = 0
        for peticao in peticoes_da_hipotese:
            # Abre detalhes → Executa ação → Fecha
            if acao and _processar_petição_completa(driver, peticao, acao):
                sucesso += 1
            time.sleep(0.5)
        
        print(f"└─ {sucesso}/{len(peticoes_da_hipotese)} processadas")
```

### C. Processamento Individual (`_processar_petição_completa()`)

```python
def _processar_petição_completa(driver: WebDriver, peticao: PeticaoLinha, acao: Callable) -> bool:
    """
    Ciclo completo de uma petição:
    1. Abre aba de detalhes
    2. Executa ação
    3. Fecha aba e volta para lista
    """
    
    # PASSO 1: Abre aba de detalhes
    sucesso_abertura, aba_lista = _abrir_detalhe_petição(driver, peticao)
    if not sucesso_abertura:
        return False
    
    try:
        # PASSO 2: Executa a ação
        sucesso_acao = _executar_acoes_sequenciais(driver, peticao, (acao,))
        
        # PASSO 3: Fecha aba e volta para lista
        _fechar_e_voltar_lista(driver, aba_lista)
        
        return sucesso_acao
    except Exception as e:
        print(f"❌ Erro ao processar: {e}")
        try:
            _fechar_e_voltar_lista(driver, aba_lista)
        except:
            pass
        return False
```

---

## 6. CONDIÇÕES POR HIPÓTESE

### HIPÓTESE 1: Apresentação de Laudo Pericial

**Condição (1 padrão - AND):**
```python
[gerar_regex_flexivel('apresentação de laudo pericial')]
```

**Regex gerada (aproximada):**
```
/apresentação.*laudo.*pericial/i
```

**Campos analisados (concatenados):**
```
f"{peticao.tipo_peticao} {peticao.descricao} {peticao.tarefa} {peticao.fase}"
```

**Exemplo que bate:**
```
tipo_peticao: "Apresentação de Laudo Pericial"
descricao: "Laudo Pericial da Perícia Médica"
→ texto = "apresentação de laudo pericial laudo pericial da perícia médica ..."
→ BATE ✓
```

---

### HIPÓTESE 2: Esclarecimentos ao Laudo - Conhecimento

**Condição (2 padrões - AND):**
```python
[
    gerar_regex_flexivel('apresentação de esclarecimentos ao laudo pericial'),
    gerar_regex_flexivel('conhecimento')
]
```

**Regex (aproximadas):**
```
/apresentação.*esclarecimentos.*laudo.*pericial/i
AND
/conhecimento/i
```

**Exemplo que bate:**
```
tipo_peticao: "Apresentação de Esclarecimentos ao Laudo Pericial"
fase: "Conhecimento"
→ texto = "apresentação de esclarecimentos ao laudo pericial ... conhecimento"
→ BATA AMBOS ✓
```

**Nota:** Se estiver em LIQUIDAÇÃO, não bate nesta hipótese → vai para HIPÓTESE 3

---

### HIPÓTESE 3: Esclarecimentos ao Laudo - Liquidação

**Condição (2 padrões - AND):**
```python
[
    gerar_regex_flexivel('apresentação de esclarecimentos ao laudo pericial'),
    gerar_regex_flexivel('liquidação')
]
```

**Regex (aproximadas):**
```
/apresentação.*esclarecimentos.*laudo.*pericial/i
AND
/liquidação/i
```

**Exemplo que bate:**
```
tipo_peticao: "Apresentação de Esclarecimentos ao Laudo Pericial"
fase: "Liquidação"
→ texto = "apresentação de esclarecimentos ao laudo pericial ... liquidação"
→ BATE AMBOS ✓
```

---

### HIPÓTESE 4: Indicação de Data de Realização

**Condição (1 padrão - AND):**
```python
[gerar_regex_flexivel('indicação de data de realização')]
```

**Regex (aproximada):**
```
/indicação.*data.*realização/i
```

**Exemplo que bate:**
```
tipo_peticao: "Indicação de Data de Realização da Perícia"
descricao: "Data agendada para perícia"
→ texto = "indicação de data de realização da perícia..."
→ BATE ✓
```

---

## 7. AÇÕES POR HIPÓTESE

### HIPÓTESE 1: ato_laudo (Apresentação de Laudo Pericial)

**Ação:** `ato_laudo` (wrapper de atos)  
**Origem:** Importado de `atos.wrappers_ato`  
**Função:** Processa apresentação de laudo pericial  
**Assinatura:**
```python
ato_laudo(driver: WebDriver, peticao: PeticaoLinha) -> bool
```

**Fluxo típico:**
```
1. Aguarda elemento específico do laudo
2. Clica para abrir/visualizar
3. Executa ação de validação
4. Retorna True se bem-sucedido
```

---

### HIPÓTESE 2: ato_esc (Esclarecimentos - Conhecimento)

**Ação:** `ato_esc` (wrapper de atos)  
**Origem:** Importado de `atos.wrappers_ato`  
**Função:** Processa esclarecimentos ao laudo em FASE CONHECIMENTO  
**Assinatura:**
```python
ato_esc(driver: WebDriver, peticao: PeticaoLinha) -> bool
```

**Diferença para Liquidação:** 
- `ato_esc` é especificamente para **Conhecimento**
- Para **Liquidação**, usa `ato_escliq` (abaixo)

---

### HIPÓTESE 3: ato_escliq (Esclarecimentos - Liquidação)

**Ação:** `ato_escliq` (wrapper de atos)  
**Origem:** Importado de `atos.wrappers_ato`  
**Função:** Processa esclarecimentos ao laudo em FASE LIQUIDAÇÃO  
**Assinatura:**
```python
ato_escliq(driver: WebDriver, peticao: PeticaoLinha) -> bool
```

**Diferença para Conhecimento:**
- `ato_escliq` é especificamente para **Liquidação**
- Para **Conhecimento**, usa `ato_esc` (acima)

---

### HIPÓTESE 4: acao_pericias_com_data (Indicação de Data - Composta)

**Ação:** `acao_pericias_com_data` (ação composta)  
**Origem:** Definida em `pet_novo.py` (linhas 375-407)  
**Função:** Ação **COMPOSTA** em 2 etapas  
**Assinatura:**
```python
def acao_pericias_com_data(driver: WebDriver, peticao: PeticaoLinha) -> bool:
```

**Fluxo:**
```python
def acao_pericias_com_data(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """
    Ação composta para Indicação de Data de Realização:
    1. Chama criar_gigs(driver, "1,xs audx")    → Extração de GIGs
    2. Chama ato_datalocal(driver, peticao)    → Despacho de data
    """
    try:
        # ETAPA 1: criar_gigs
        print(f"[PET_ACAO] Executando criar_gigs(driver, '1,xs audx')...")
        try:
            resultado_gigs = criar_gigs(driver, "1,xs audx")
            print(f"[PET_ACAO] ✅ criar_gigs executado")
        except Exception as e:
            print(f"[PET_ACAO] ⚠️ criar_gigs falhou: {e}")
            resultado_gigs = False
        
        time.sleep(0.5)
        
        # ETAPA 2: ato_datalocal
        print(f"[PET_ACAO] Executando ato_datalocal...")
        try:
            resultado_ato = ato_datalocal(driver, peticao) if ato_datalocal else False
            print(f"[PET_ACAO] ✅ ato_datalocal executado")
            return resultado_ato
        except Exception as e:
            print(f"[PET_ACAO] ⚠️ ato_datalocal falhou: {e}")
            return False
            
    except Exception as e:
        logger.error(f"[PET_ACAO] Erro em acao_pericias_com_data: {e}")
        return False
```

**Etapas:**

**Etapa 1: criar_gigs(driver, "1,xs audx")**
- **Função:** Criar GIG (atividade de auditório)
- **Parâmetros:**
  - `"1"` → Prazo de 1 dia
  - `"xs audx"` → Tipo de atividade extrauditório
- **Objetivo:** Extrair informações relacionadas

**Etapa 2: ato_datalocal(driver, peticao)**
- **Função:** Criar despacho de data/local
- **Objetivo:** Indicar data local de realização
- **Retorno:** Retorna resultado dessa ação

**Comportamento de falha:**
- Se ETAPA 1 falhar → continua para ETAPA 2
- Se ETAPA 2 falhar → retorna False (falha geral)

---

## 📊 RESUMO DE CONDIÇÕES E AÇÕES

| # | Hipótese | Condições (AND) | Ação | Tipo |
|---|----------|-----------------|------|------|
| 1 | "Apresentação de Laudo Pericial" | `apresentação de laudo pericial` | `ato_laudo` | Simples |
| 2 | "Esclarecimentos ao Laudo - Conhecimento" | `apresentação de esclarecimentos ao laudo pericial` + `conhecimento` | `ato_esc` | Simples |
| 3 | "Esclarecimentos ao Laudo - Liquidação" | `apresentação de esclarecimentos ao laudo pericial` + `liquidação` | `ato_escliq` | Simples |
| 4 | "Indicação de Data de Realização" | `indicação de data de realização` | `acao_pericias_com_data` | **Composta** |

---

## 🔄 FLUXO COMPLETO DE UMA PETIÇÃO DE PERÍCIA

```
1. EXTRAÇÃO (linhas 1280-1320)
   ├─ URL: "https://pje.trt2.jus.br/pjekz/escaninho/peticoes-juntadas"
   ├─ extrair_tabela_peticoes() → Lista de PeticaoLinha
   └─ Cada petição tem: (número_processo, tipo_peticao, descricao, tarefa, fase)

2. AGRUPAMENTO (linhas 870-920)
   ├─ agrupar_por_regra(peticoes)
   ├─ Testa cada petição contra 4 hipóteses de PERÍCIAS
   └─ Agrupa em resultado["pericias"]["peticoes_por_hipotese"]

3. PROCESSAMENTO BLOCO 1 (linhas 870-920)
   ├─ FOR cada hipótese em PERÍCIAS:
   │   ├─ FOR cada petição na hipótese:
   │   │   ├─ _abrir_detalhe_petição()      [abre aba]
   │   │   ├─ executar_acao(acao)           [executa ação]
   │   │   └─ _fechar_e_voltar_lista()      [fecha aba]
   │   │
   │   └─ time.sleep(0.5)
   │
   └─ Próxima hipótese

4. RASTREAMENTO (linhas 1340-1350)
   ├─ marcar_processo_executado_pet()
   └─ salvar_progresso_pet()
```

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

- [x] 4 Hipóteses de PERÍCIAS definidas
- [x] Padrões regex para cada hipótese
- [x] Mapeamento de ações (3 simples + 1 composta)
- [x] Loop de processamento implementado
- [x] Tratamento de erros com try-except
- [x] Logging detalhado com [PET_EXEC], [PET_ACAO]
- [x] Sincronização com time.sleep()
- [x] Rastreamento de progresso

---

## 🎯 NOTAS IMPORTANTES

1. **Ordem de Verificação:** Uma petição é verificada em sequência:
   - Hipótese 1 (Laudo)
   - Hipótese 2 (Esclarecimentos + Conhecimento)
   - Hipótese 3 (Esclarecimentos + Liquidação)
   - Hipótese 4 (Data de Realização)
   
   Assim que uma corresponde, é adicionada àquela hipótese e passa para próxima petição.

2. **Ação Composta (Hipótese 4):** A única ação que executa 2 funções em sequência:
   - Primeiro `criar_gigs()`
   - Depois `ato_datalocal()`

3. **Diferença Esclarecimentos:** As hipóteses 2 e 3 diferem apenas pela FASE (Conhecimento vs Liquidação), mas usam ações diferentes (`ato_esc` vs `ato_escliq`).

4. **Execução:** PERÍCIAS é SEMPRE o BLOCO 1 (executado primeiro, antes de GIGS, RECURSO, etc.)

---

## 📝 VERSÃO

- **Data:** 2025-01-30
- **Arquivo base:** PEC/pet_novo.py (1399 linhas)
- **Função main:** `executar_fluxo_pet()` (linhas 1260-1390)
- **Função BLOCO 1:** `executar_regras()` → seção PERÍCIAS (linhas 870-920)
