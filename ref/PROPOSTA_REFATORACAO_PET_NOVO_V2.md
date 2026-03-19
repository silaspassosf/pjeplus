# PROPOSTA DE REFATORAÇÃO: pet_novo.py → Padrão p2b.py (VERSÃO CORRIGIDA)

## ⚠️ OBSERVAÇÕES CRÍTICAS DO USUÁRIO

### **1. ESTRUTURA DE DADOS DA PETIÇÃO**
```python
class PeticaoLinha:
    """Representa uma linha da tabela de petições com MÚLTIPLAS COLUNAS"""
    def __init__(self, ...):
        self.numero_processo = numero_processo      # Coluna 2: Número do processo
        self.tipo_peticao = tipo_peticao           # Coluna 4: Tipo de petição
        self.descricao = descricao                 # Coluna 5: Descrição da petição
        self.tarefa = tarefa                       # Coluna 6 (parte 1): Tarefa
        self.fase = fase                           # Coluna 6 (parte 2): Fase processual
        self.data_juntada = data_juntada           # Coluna 3: Data de juntada
        self.eh_perito = eh_perito                 # Flag: ícone de perito presente
        self.data_audiencia = data_audiencia       # Data de audiência (ex: "10/03/2026 11:35")
        self.polo = polo                           # Polo: 'ativo', 'passivo' ou None
```

### **2. COMO AS REGRAS ATUAIS FUNCIONAM (CORRETO!)**
```python
# ✅ FASE 1: REGEX BUSCA EM CAMPOS CONCATENADOS (maioria dos blocos)
texto = normalizar_texto(
    f"{peticao.tipo_peticao} {peticao.descricao} {peticao.tarefa} {peticao.fase}"
)
# Exemplo: "manifestação manifestação conhecimento aguardando cumprimento de acordo"

# ✅ PADRÕES PODEM TESTAR MÚLTIPLOS CAMPOS DIFERENTES
# Exemplo 1: "Acordo" - Tarefa + Tipo de petição
regra_acordo = [
    gerar_regex_flexivel('aguardando cumprimento de acordo'),  # ← busca TAREFA
    lambda txt: (gerar_regex_flexivel('contestação').search(txt) or  # ← busca TIPO_PETICAO
                 gerar_regex_flexivel('habilitação').search(txt) or
                 gerar_regex_flexivel('procuração').search(txt))
]

# Exemplo 2: "Agravo Conhecimento" - Tipo de petição + Fase
regra_agravo_conhec = [
    gerar_regex_flexivel('agravo de instrumento'),  # ← busca TIPO_PETICAO
    gerar_regex_flexivel('conhecimento')            # ← busca FASE
]

# Exemplo 3: "Manifestação Carta" - Descrição + Tipo de petição
regra_manifestacao = [
    gerar_regex_flexivel('manifestação'),           # ← busca DESCRIÇÃO
    lambda txt: (gerar_regex_flexivel('carta de preposição').search(txt) or  # ← busca TIPO_PETICAO
                 gerar_regex_flexivel('substabelecimento').search(txt))
]

# ✅ TODOS OS PADRÕES DEVEM BATER (AND lógico)
# Se lista tem 3 padrões, TODOS devem encontrar match no texto concatenado

# ⚠️ EXCEÇÃO: BLOCO ANÁLISE
# Se petição bate com padrão de ANÁLISE (ex: "manifestação" genérica):
# 1. Abre processo em nova aba
# 2. EXTRAI CONTEÚDO DO PDF da petição
# 3. Aplica NOVO CONJUNTO DE REGRAS no texto do PDF
# 4. Executa ação baseada no conteúdo (não nos campos!)
```

### **3. VALIDAÇÕES ESPECIAIS POR BLOCO**
```python
# ✅ PERÍCIAS: ALÉM dos padrões, requer eh_perito=True
def verifica_peticao_pericias(peticao, padroes):
    if not peticao.eh_perito:  # ← FLAG do ícone
        return False
    return verifica_peticao_contra_hipotese(peticao, padroes)

# ✅ DIRETOS: ALÉM dos padrões, requer:
# - data_audiencia != None
# - data_audiencia > 01/02/2026
# - Para "Impugnação": fase = "Liquidação"
def verifica_peticao_diretos(peticao, padroes):
    if not verifica_peticao_contra_hipotese(peticao, padroes):
        return False
    
    if not peticao.data_audiencia:
        return False
    
    data_aud = datetime.strptime(peticao.data_audiencia.split()[0], "%d/%m/%Y")
    if data_aud < datetime.strptime("01/02/2026", "%d/%m/%Y"):
        return False
    
    # Validação especial para Impugnação
    if 'impugnação' in normalizar_texto(f"{peticao.tipo_peticao} {peticao.descricao}"):
        if not peticao.fase or 'liquidação' not in peticao.fase.lower():
            return False
    
    return True
```

### **4. ORDEM DE EXECUÇÃO E FLUXO DE AÇÃO**
```python
# ✅ ORDEM DE EXECUÇÃO (APAGAR SEMPRE POR ÚLTIMO!)
ordem_execucao = [
    "pericias",   # 1º - Abre processo → executa ação → fecha
    "recurso",    # 2º - Abre processo → executa ação → fecha
    "diretos",    # 3º - Abre processo → executa ação → fecha
    "gigs",       # 4º - Abre processo → executa ação → fecha
    "analise",    # 5º - Abre processo → extrai PDF → decide ação → executa → fecha
    "apagar"      # 6º - ÚNICO que executa DIRETO NA LISTA (sem abrir processo)
]

# ✅ FLUXO DE EXECUÇÃO POR BLOCO
def executar_acao_por_bloco(driver, peticao, bloco, acao):
    if bloco == "apagar":
        # APAGAR: executa direto na lista (sem abrir processo)
        return acao(driver, peticao)
    
    elif bloco == "analise":
        # ANÁLISE: abre → extrai PDF → decide ação → executa → fecha
        aba_lista = abrir_processo(driver, peticao)
        try:
            conteudo_pdf = extrair_pdf(driver)
            acao_decidida = decidir_acao_por_conteudo(conteudo_pdf)
            resultado = acao_decidida(driver, peticao)
        finally:
            fechar_e_voltar(driver, aba_lista)
        return resultado
    
    else:
        # PERÍCIAS, RECURSO, DIRETOS, GIGS: abre → executa → fecha
        aba_lista = abrir_processo(driver, peticao)
        try:
            resultado = acao(driver, peticao)
        finally:
            fechar_e_voltar(driver, aba_lista)
        return resultado
```

---

## 📋 DIFERENÇAS FUNDAMENTAIS: p2b.py vs pet_novo.py

### **p2b.py - Trabalha com TEXTO EXTRAÍDO de DOCUMENTOS**

```python
# p2b.py: EXTRAI texto de documentos PDF abertos na timeline
texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=True)
texto, _, _ = texto_tuple
texto_normalizado = normalizar_texto(texto)  # ← texto do PDF

# Regex busca NO CONTEÚDO DO DOCUMENTO
regras = [
    ([gerar_regex_geral('A pronúncia da')], None, None, prescreve),
    ([gerar_regex_geral(k) for k in ['05 dias', 'suspensão']], 
     'gigs', '1/Silas/Sob 24', ato_sobrestamento),
]

# Loop DIRETO sobre documento único
for idx, (keywords, tipo_acao, params, acao_sec) in enumerate(regras):
    for regex in keywords:
        if regex.search(texto_normalizado):  # ← busca no PDF
            # ... executa ação
```

**Características p2b.py:**
- ✅ Processa UM documento por vez
- ✅ Regex busca NO CONTEÚDO do PDF
- ✅ Não há estrutura de campos/colunas
- ✅ Ação executada direto no driver

---

### **pet_novo.py - Trabalha com LINHAS DE TABELA (2 FASES)**

#### **FASE 1: Classificação por Campos (todos os blocos)**

```python
# pet_novo.py: EXTRAI lista de petições da TABELA do escaninho
peticoes = extrair_peticoes_tabela(driver)

# Cada petição tem MÚLTIPLOS CAMPOS extraídos das COLUNAS
for peticao in peticoes:
    # peticao.tipo_peticao    ← Coluna "Tipo de Petição"
    # peticao.descricao       ← Coluna "Descrição"
    # peticao.tarefa          ← Coluna "Tarefa/Fase" (parte 1)
    # peticao.fase            ← Coluna "Tarefa/Fase" (parte 2)
    # peticao.eh_perito       ← Flag do ícone
    # peticao.data_audiencia  ← Campo extraído
    # peticao.polo            ← Polo da petição

# Regex busca NOS CAMPOS CONCATENADOS (TODOS OS BLOCOS)
texto = normalizar_texto(
    f"{peticao.tipo_peticao} {peticao.descricao} {peticao.tarefa} {peticao.fase}"
)

# Validações podem usar FLAGS e CAMPOS ADICIONAIS
if peticao.eh_perito and 'esclarecimentos' in texto:
    # Abre processo → executa ação → fecha
    acao_esclarecimentos(driver, peticao)
```

**Características FASE 1 (TODOS OS BLOCOS - classificação):**
- ✅ Processa LISTA de petições (múltiplas linhas da tabela)
- ✅ Regex busca NOS CAMPOS CONCATENADOS da tabela
- ✅ Usa FLAGS adicionais (eh_perito, data_audiencia, polo)
- ✅ Validações especiais por bloco
- ✅ Detecta qual BLOCO e qual HIPÓTESE

#### **FASE 2: Execução de Ação (diferentes por bloco)**

##### **2A. BLOCO APAGAR (único que NÃO abre processo)**

```python
# APAGAR: executa DIRETO NA LISTA
if match_bloco_apagar(peticao):
    # NÃO abre processo - executa direto
    acao_apagar(driver, peticao)  # ← remove da tabela
```

**Fluxo APAGAR:**
1. ✅ Localiza linha na tabela
2. ✅ Clica no ícone de trash
3. ✅ Confirma com SPACE
4. ✅ Petição removida da lista
5. ❌ **NÃO abre processo** - trabalha direto na lista

##### **2B. BLOCOS PERÍCIAS, RECURSO, DIRETOS, GIGS (ação direta)**

```python
# Esses blocos: abre processo → executa ação → fecha
if match_bloco_direto(peticao):
    # 1. Abre processo
    aba_lista = abrir_processo(driver, peticao)
    
    try:
        # 2. Executa ação (já sabe qual ação executar)
        ato_concor(driver, peticao)  # ← ação já definida na classificação
    finally:
        # 3. Fecha processo e volta para lista
        fechar_e_voltar(driver, aba_lista)
```

**Fluxo PERÍCIAS/RECURSO/DIRETOS/GIGS:**
1. ✅ Abre processo em nova aba
2. ✅ Executa ação (já definida na Fase 1)
3. ✅ Fecha aba e volta para lista
4. ❌ **NÃO extrai PDF** - ação já está definida

##### **2C. BLOCO ANÁLISE (extrai PDF para decidir)**

```python
# ANÁLISE: usa REGEX nos campos para DETECTAR que precisa análise
if 'manifestação' in texto_campos:  # ← regex nos campos (Fase 1 - CLASSIFICAÇÃO)
    
    # 1. Abre processo
    aba_lista = abrir_processo(driver, peticao)
    
    try:
        # 2. EXTRAI CONTEÚDO DO PDF da petição
        conteudo_pdf = extrair_pdf(driver)
        texto_normalizado = normalizar_texto(conteudo_pdf)
        
        # 3. Aplica regras NO CONTEÚDO do PDF (padrão p2b.py!)
        # ✅ FORMATO SIMPLES: ([padrões], ação_ou_tupla)
        # ❌ SEM categorias/nomes - apenas lista de regras
        
        regras_pdf = [
            # Palavra sozinha
            ([gerar_regex_flexivel('perícia')], ato_laudo),
            
            # Trecho exato
            ([gerar_regex_flexivel('vistos, examinados e discutidos')], ato_gen),
            
            # Grupo de palavras separadas
            ([gerar_regex_flexivel('cinco dias para apresentação')], ato_instc),
            
            # Múltiplos padrões (AND)
            ([gerar_regex_flexivel('agravo'), gerar_regex_flexivel('instrumento')], ato_instc),
            
            # Ação composta (tupla)
            ([gerar_regex_flexivel('concordância')], 
             (criar_acao_gigs("1", "Silvia"), ato_gen)),
        ]
        
        # 4. Testa regras em ordem (primeira match = executa e PARA)
        for padroes, acao in regras_pdf:
            if all(p.search(texto_normalizado) if isinstance(p, re.Pattern) 
                   else p(texto_normalizado) for p in padroes):
                # Executa ação ou tupla
                if callable(acao):
                    acao(driver, peticao)
                elif isinstance(acao, tuple):
                    for a in acao:
                        if a(driver, peticao) is False:
                            break
                break
    finally:
        # 5. Fecha processo e volta para lista
        fechar_e_voltar(driver, aba_lista)
```

**Fluxo ANÁLISE:**
1. ✅ **Classificação:** Regex nos campos detecta "manifestação" → bloco = ANÁLISE
2. ✅ Abre processo em nova aba
3. ✅ **Extrai PDF** da petição
4. ✅ Aplica **regex no conteúdo do PDF** (padrão p2b.py!)
5. ✅ **Decide e executa** ação baseada no conteúdo
6. ✅ Fecha aba e volta para lista

**Tipos de Padrões no PDF:**
- ✅ Palavra sozinha: `gerar_regex_flexivel('perícia')`
- ✅ Trecho exato: `gerar_regex_flexivel('vistos, examinados e discutidos')`
- ✅ Grupo de palavras: `gerar_regex_flexivel('cinco dias para apresentação')`
- ✅ Lambda para OR: `lambda txt: regex1.search(txt) or regex2.search(txt)`
- ✅ AND automático: lista com múltiplos padrões (todos devem bater)

### **Resumo: Como TODOS os Blocos são Detectados**

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: CLASSIFICAÇÃO (TODOS OS BLOCOS)                    │
│ Regex nos campos: tipo_peticao + descricao + tarefa + fase │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        │ Qual BLOCO? (detectado por regex)    │
        └───────────┬───────────────────────────┘
                    ↓
    ┌───────────────┴───────────────┐
    │                               │
    ↓                               ↓
APAGAR/PERÍCIAS/RECURSO/         ANÁLISE
DIRETOS/GIGS                  (manifestação genérica)
    │                               │
    ↓                               ↓
Ação JÁ DEFINIDA              Ação INDEFINIDA
(executa direto)           (precisa ler PDF para decidir)
```

---

## 🎯 PROPOSTA DE REFATORAÇÃO (CORRIGIDA)

### **Manter Estrutura Atual de Regras (JÁ ESTÁ CORRETA!)**

```python
# ============================================================================
# ESTRUTURA DE REGRAS ATUAL (NÃO MUDAR!)
# ============================================================================

def definir_regras() -> Dict[str, List[Tuple[str, List, Callable]]]:
    """
    Define regras por BLOCOS.
    Cada regra: (nome_hipotese, [padroes], acao)
    
    ✅ PADRÕES buscam em campos concatenados:
       texto = f"{tipo_peticao} {descricao} {tarefa} {fase}"
    
    ✅ PADRÕES podem ser:
       - re.Pattern: gerar_regex_flexivel('termo')
       - callable: lambda txt: condicao(txt)
    
    ✅ TODOS os padrões devem bater (AND lógico)
    """
    
    # BLOCO 1: APAGAR (executado por último!)
    regra_apagar_hipoteses = [
        ("Razões Finais / Carta Convite", [
            lambda txt: (gerar_regex_flexivel('razões finais').search(txt) or 
                       gerar_regex_flexivel('carta convite').search(txt)),
        ]),
        ("Réplica em Conhecimento", [
            gerar_regex_flexivel('réplica'),
            gerar_regex_flexivel('conhecimento'),
        ]),
        ("Acordo", [
            gerar_regex_flexivel('aguardando cumprimento de acordo'),
            lambda txt: (gerar_regex_flexivel('contestação').search(txt) or
                       gerar_regex_flexivel('habilitação').search(txt) or
                       gerar_regex_flexivel('procuração').search(txt) or
                       gerar_regex_flexivel('carta de preposição').search(txt) or
                       gerar_regex_flexivel('substabelecimento').search(txt)),
        ]),
        ("Manifestação - Carta/Substabelecimento", [
            gerar_regex_flexivel('manifestação'),
            lambda txt: (gerar_regex_flexivel('carta de preposição').search(txt) or
                       gerar_regex_flexivel('substabelecimento').search(txt)),
        ]),
        ("Triagem Inicial", [
            gerar_regex_flexivel('triagem inicial'),
        ]),
    ]
    
    # BLOCO 2: PERÍCIAS (requer eh_perito=True)
    regra_pericias_hipoteses = [
        ("Esclarecimentos ao Laudo - Conhecimento", [
            gerar_regex_flexivel('esclarecimentos'),
            gerar_regex_flexivel('conhecimento'),
        ]),
        ("Esclarecimentos ao Laudo - Liquidação", [
            gerar_regex_flexivel('esclarecimentos'),
            gerar_regex_flexivel('liquidação'),
        ]),
        ("Apresentação de Laudo Pericial", [
            gerar_regex_flexivel('apresentação de laudo pericial'),
        ]),
        ("Indicação de Data de Realização", [
            gerar_regex_flexivel('indicação de data'),
        ]),
    ]
    
    # BLOCO 3: RECURSO
    regra_recurso_hipoteses = [
        ("Agravo de Instrumento - Conhecimento", [
            gerar_regex_flexivel('agravo de instrumento'),
            gerar_regex_flexivel('conhecimento'),
        ]),
        ("Agravo de Instrumento - Liquidação/Execução", [
            gerar_regex_flexivel('agravo de instrumento'),
            lambda txt: (gerar_regex_flexivel('liquidação').search(txt) or 
                       gerar_regex_flexivel('execução').search(txt)),
        ]),
    ]
    
    # BLOCO 4: DIRETOS (requer data_audiencia > 01/02/2026)
    regra_diretos_hipoteses = [
        ("Solicitação de Habilitação - CEJU", [
            gerar_regex_flexivel('habilitação'),
        ]),
        ("Apresentação de Cálculos", [
            gerar_regex_flexivel('apresentação de cálculos'),
            gerar_regex_flexivel('cálculo'),
        ]),
        ("Assistente", [
            gerar_regex_flexivel('assistente'),
        ]),
        ("Impugnação", [
            gerar_regex_flexivel('impugnação'),
        ]),
        ("CAGED", [
            gerar_regex_flexivel('caged'),
        ]),
    ]
    
    # BLOCO 5: GIGS
    regra_gigs_hipoteses = [
        ("GIGS - Homologação/Liberação", [
            lambda txt: (gerar_regex_flexivel('concordancia').search(txt) or 
                       gerar_regex_flexivel('comprovante').search(txt) or
                       gerar_regex_flexivel('deposito').search(txt) or
                       gerar_regex_flexivel('parcela').search(txt)),
        ]),
    ]
    
    # BLOCO 6: ANÁLISE
    regra_analise_hipoteses = [
        ("Manifestação - Despacho Genérico", [
            gerar_regex_flexivel('manifestação'),
            lambda txt: (gerar_regex_flexivel('prosseguimento').search(txt) or 
                       gerar_regex_flexivel('meios de execução').search(txt)),
        ]),
        ("Manifestação - Análise", [
            gerar_regex_flexivel('manifestação'),
            gerar_regex_flexivel('manifestação'),
        ]),
        ("Manifestação - Expedição de Ofício", [
            gerar_regex_flexivel('manifestação'),
            gerar_regex_flexivel('expedição de ofício'),
        ]),
    ]
    
    # ... (converter para tuplas com ações - código já existe)
```

---

### **REFATORAÇÃO: Eliminar Funções Wrapper Desnecessárias**

#### **ANTES (Atual - INEFICIENTE):**

```python
# ❌ PROBLEMA: Função wrapper para cada regra específica

def cris_gigs_minus1_xs_pec(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """Wrapper para criar_gigs(driver, '-1', 'xs pec') para CAGED"""
    try:
        print(f"[PET_ACAO] Criando GIGS: -1, xs pec")
        resultado = criar_gigs(driver, "-1", "xs pec")
        if resultado:
            print(f"[PET_ACAO]   ✅ GIGS criado")
        return resultado
    except Exception as e:
        print(f"[PET_ACAO]   ❌ Erro: {e}")
        return False

def criar_gigs_1_xs_aud(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """Wrapper para criar_gigs(driver, '1', 'xs aud')"""
    try:
        print(f"[PET_ACAO] Criando GIGS: 1,xs aud")
        resultado = criar_gigs(driver, "1", "xs aud")
        # ... mesmo código repetitivo
        return resultado
    except Exception as e:
        print(f"[PET_ACAO]   ❌ Erro: {e}")
        return False

def padrao_liq_acao(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """Wrapper para padrao_liq() via API"""
    try:
        from Fix.variaveis import session_from_driver, PjeApiClient, padrao_liq
        sess, trt_host = session_from_driver(driver)
        client = PjeApiClient(sess, trt_host)
        resultado = padrao_liq(client, peticao.numero_processo)
        # ... 20 linhas de código
        return resultado.get('apenas_uma_com_advogado') and not resultado.get('tem_perito')
    except Exception as e:
        return False

# ❌ Total: ~15 funções wrapper similares!
```

#### **DEPOIS (Proposta - EFICIENTE):**

```python
# ✅ SOLUÇÃO: Lambdas inline + helper genérico

def criar_acao_gigs(dias: str, observacao: str) -> Callable:
    """Helper para criar lambda de GIGS com parâmetros fixos."""
    def _gigs(driver: WebDriver, peticao: PeticaoLinha) -> bool:
        try:
            return criar_gigs(driver, dias, observacao)
        except:
            return False
    return _gigs

def criar_acao_padrao_liq() -> Callable:
    """Helper para criar lambda de padrao_liq condicional."""
    def _check(driver: WebDriver, peticao: PeticaoLinha) -> bool:
        try:
            from Fix.variaveis import session_from_driver, PjeApiClient, padrao_liq
            sess, trt_host = session_from_driver(driver)
            client = PjeApiClient(sess, trt_host)
            resultado = padrao_liq(client, peticao.numero_processo)
            return resultado.get('apenas_uma_com_advogado', False) and not resultado.get('tem_perito', False)
        except:
            return False
    return _check

# ✅ Uso nas definições de ações (sem criar 15 funções!)
acoes_diretos = [
    ato_ceju,                                                    # Habilitação
    ato_respcalc,                                               # Cálculos
    (criar_acao_gigs("1", "xs aud"), ato_assistente),          # Assistente (tupla)
    (criar_acao_padrao_liq(), ato_concor),                     # Impugnação (condicional)
    (criar_acao_gigs("-1", "xs pec"), ato_prevjud),            # CAGED (tupla)
]
```

---

### **REFATORAÇÃO: Simplificar Execução (Padrão p2b.py)**

#### **ANTES (Atual - COMPLEXO):**

```python
# ❌ PROBLEMA: Múltiplos loops e estrutura complexa

def executar_regras(driver, peticoes, regras):
    # 1. Classificar petições por bloco/hipótese
    resultado = classificar_peticoes(peticoes, regras)
    # resultado = {
    #   "pericias": {"peticoes_por_hipotese": {...}, "total": X},
    #   "recurso": {"peticoes_por_hipotese": {...}, "total": Y},
    #   ...
    # }
    
    # 2. Loop por BLOCO
    for bloco in ["pericias", "recurso", "diretos", "gigs", "analise"]:
        regra_bloco = resultado[bloco]
        hipoteses_bloco = {nome: acao for nome, padroes, acao in regras[bloco]}
        
        # 3. Loop por HIPÓTESE dentro do bloco
        for nome_hipotese, peticoes_hipotese in regra_bloco["peticoes_por_hipotese"].items():
            acao = hipoteses_bloco.get(nome_hipotese)
            
            # 4. Loop por PETIÇÃO dentro da hipótese
            for peticao in peticoes_hipotese:
                _processar_petição_completa(driver, peticao, acao)
    
    # 5. APAGAR por último
    for nome_hipotese, peticoes_hipotese in resultado["apagar"]["peticoes_por_hipotese"].items():
        for peticao in peticoes_hipotese:
            _executar_acao(driver, peticao, acao_apagar)

# ❌ Estrutura: 4 níveis de loops, dicionários aninhados
```

#### **DEPOIS (Proposta - SIMPLES):**

```python
# ✅ SOLUÇÃO: Loop direto estilo p2b.py

def executar_regras_simplificado(driver: WebDriver, peticoes: List[PeticaoLinha], 
                                  regras_dict: Dict) -> bool:
    """
    Executa regras estilo p2b.py: loop direto sobre petições.
    
    Para cada petição:
    1. Testa BLOCOS em ordem (pericias → recurso → diretos → gigs → analise → apagar)
    2. Dentro de cada bloco, testa HIPÓTESES em ordem
    3. Primeira HIPÓTESE que bater → executa ação e PARA (prioridade)
    """
    # Ordem de execução (APAGAR por último!)
    ordem_blocos = ["pericias", "recurso", "diretos", "gigs", "analise", "apagar"]
    
    for peticao in peticoes:
        print(f"\n[PET_EXEC] Processando: {peticao.numero_processo}")
        
        acao_executada = False
        
        # Testar blocos em ordem
        for nome_bloco in ordem_blocos:
            if acao_executada:
                break
            
            hipoteses_bloco = regras_dict.get(nome_bloco, [])
            
            # Testar hipóteses do bloco
            for nome_hipotese, padroes, acao in hipoteses_bloco:
                # Validação específica por bloco
                if nome_bloco == "pericias":
                    match = verifica_peticao_pericias(peticao, padroes)
                elif nome_bloco == "diretos":
                    match = verifica_peticao_diretos(peticao, padroes)
                else:
                    match = verifica_peticao_contra_hipotese(peticao, padroes)
                
                if match:
                    print(f"[PET_EXEC] ✅ MATCH: {nome_bloco} → {nome_hipotese}")
                    
                    # Executar ação
                    if _executar_acao_completa(driver, peticao, acao):
                        acao_executada = True
                        break
        
        if not acao_executada:
            print(f"[PET_EXEC] ⚠️ Nenhuma regra aplicável")
    
    return True

# ✅ Estrutura: 2 níveis de loops, lista linear
```

---

### **REFATORAÇÃO: Executar Ações (Tuplas e Chamadas Diretas)**

```python
def _executar_acao_completa(driver: WebDriver, peticao: PeticaoLinha, 
                            bloco: str, acao: Any) -> bool:
    """
    Executa ação de forma completa conforme o BLOCO:
    
    APAGAR: executa direto na lista (sem abrir processo)
    PERÍCIAS/RECURSO/DIRETOS/GIGS: abre → executa → fecha
    ANÁLISE: abre → extrai PDF → decide ação → executa → fecha
    
    Tuplas executam em SEQUÊNCIA:
    - Se elemento retornar False, PARA execução da tupla
    - Caso contrário, continua para próximo elemento
    """
    try:
        # ============================================================
        # BLOCO APAGAR: único que NÃO abre processo
        # ============================================================
        if bloco == "apagar":
            # Executa direto na lista (remove da tabela)
            return acao(driver, peticao)
        
        # ============================================================
        # BLOCOS PERÍCIAS/RECURSO/DIRETOS/GIGS/ANÁLISE: abrem processo
        # ============================================================
        
        # 1. Abre processo em nova aba
        sucesso_abertura, aba_lista = _abrir_detalhe_petição(driver, peticao)
        if not sucesso_abertura:
            return False
        
        resultado_final = False
        
        try:
            # ========================================================
            # BLOCO ANÁLISE: extrai PDF e decide ação
            # ========================================================
            if bloco == "analise":
                # Extrai PDF da petição
                conteudo_pdf = extrair_pdf(driver, log=False)
                if not conteudo_pdf:
                    print(f"[PET_EXEC]   ⚠️ Falha ao extrair PDF")
                    return False
                
                # Processa análise (padrão p2b.py!)
                resultado_final = processar_analise_pdf(driver, peticao, conteudo_pdf)
            
            # ========================================================
            # BLOCOS PERÍCIAS/RECURSO/DIRETOS/GIGS: ação já definida
            # ========================================================
            else:
                # Ação simples (callable)
                if callable(acao):
                    resultado_final = acao(driver, peticao)
                
                # Ação composta (tupla)
                elif isinstance(acao, tuple):
                    # Executar em sequência
                    for idx, acao_item in enumerate(acao):
                        if callable(acao_item):
                            print(f"[PET_EXEC]   Executando ação {idx+1}/{len(acao)}...")
                            resultado = acao_item(driver, peticao)
                            
                            # Se retornar False, para execução da tupla
                            if resultado is False:
                                print(f"[PET_EXEC]   ⚠️ Ação {idx+1} retornou False - parando tupla")
                                break
                            
                            resultado_final = True
        
        finally:
            # 2. Fecha processo e volta para lista
            _fechar_e_voltar_lista(driver, aba_lista)
        
        return resultado_final
        
    except Exception as e:
        print(f"[PET_EXEC] ❌ Erro ao executar ação: {e}")
        return False


def definir_regras_analise_conteudo() -> List[Tuple[List, Any]]:
    """
    Define regras para análise de CONTEÚDO do PDF (padrão p2b.py).
    
    ✅ FORMATO SIMPLES: ([padrões_regex], ação_ou_tupla_ações)
    
    SEM categorias/nomes - apenas lista direta de (padrões, ação)
    
    Padrões suportam:
    - Palavra sozinha: gerar_regex_flexivel('perícia')
    - Trechos exatos: gerar_regex_flexivel('A pronúncia da prescrição')
    - Grupo de palavras: gerar_regex_flexivel('cinco dias para apresentação')
    - Múltiplos padrões: todos devem bater (AND lógico)
    """
    
    # Imports de ações
    from atos.wrappers_ato import ato_laudo, ato_esc, ato_instc, ato_gen
    
    regras = [
        # Regra 1: Perícia (palavras relacionadas)
        ([gerar_regex_flexivel('perícia'), gerar_regex_flexivel('laudo')], ato_laudo),
        
        # Regra 2: Recurso (agravo ou apelação)
        ([lambda txt: (gerar_regex_flexivel('agravo').search(txt) or 
                      gerar_regex_flexivel('apelação').search(txt))], ato_instc),
        
        # Regra 3: Despacho genérico (trecho exato)
        ([gerar_regex_flexivel('vistos, examinados e discutidos')], ato_gen),
        
        # Regra 4: Ação composta - exemplo com tupla
        ([gerar_regex_flexivel('concordância homologação')], 
         (criar_acao_gigs("1", "Silvia homologacao"), ato_gen)),
        
        # ... adicionar mais regras conforme necessário
    ]
    
    return regras


def processar_analise_pdf(driver: WebDriver, peticao: PeticaoLinha, 
                          conteudo_pdf: str) -> bool:
    """
    Processa análise de conteúdo do PDF (padrão p2b.py).
    
    Fluxo:
    1. Normaliza texto do PDF
    2. Testa regras em ordem (primeira match = executa e para)
    3. Executa ação ou tupla de ações
    """
    try:
        texto_normalizado = normalizar_texto(conteudo_pdf)
        regras = definir_regras_analise_conteudo()
        
        # Testar regras em ordem
        for padroes, acao in regras:
            # Verificar se TODOS os padrões batem (AND lógico)
            match = True
            for padrao in padroes:
                if isinstance(padrao, re.Pattern):
                    if not padrao.search(texto_normalizado):
                        match = False
                        break
                elif callable(padrao):
                    if not padrao(texto_normalizado):
                        match = False
                        break
            
            if match:
                print(f"[PET_ANALISE] ✅ Match no conteúdo do PDF")
                
                # Executar ação ou tupla
                if callable(acao):
                    return acao(driver, peticao)
                elif isinstance(acao, tuple):
                    # Executar tupla em sequência
                    for acao_item in acao:
                        if callable(acao_item):
                            resultado = acao_item(driver, peticao)
                            if resultado is False:
                                break
                    return True
        
        print(f"[PET_ANALISE] ⚠️ Nenhuma regra de conteúdo aplicável")
        return False
        
    except Exception as e:
        print(f"[PET_ANALISE] ❌ Erro: {e}")
        return False
```

---

## 📊 COMPARAÇÃO: ANTES vs DEPOIS

### **Funções Wrapper**

| Item | ANTES | DEPOIS |
|------|-------|---------|
| Funções wrapper | 15+ funções | 2 helpers genéricos |
| Linhas de código | ~300 linhas | ~50 linhas |
| Manutenção | Criar função para cada regra | Usar helper existente |

### **Estrutura de Execução**

| Item | ANTES | DEPOIS |
|------|-------|---------|
| Níveis de loop | 4 níveis (bloco → hipótese → petição) | 2 níveis (petição → bloco → hipótese) |
| Estruturas de dados | Dicionários aninhados | Lista linear |
| Prioridade | Implícita (ordem de blocos) | Explícita (break após match) |
| Linhas de código | ~400 linhas | ~150 linhas |

### **Total**

| Métrica | ANTES | DEPOIS | Redução |
|---------|-------|---------|---------|
| Linhas totais | ~1700 | ~800 | 53% |
| Funções | ~40 | ~20 | 50% |
| Complexidade | Alta | Média | - |

---

## ✅ PLANO DE IMPLEMENTAÇÃO

### **Fase 1: Criar Helpers Genéricos**
```python
# ✅ Substituir funções wrapper por 2 helpers
def criar_acao_gigs(dias: str, observacao: str) -> Callable: ...
def criar_acao_padrao_liq() -> Callable: ...
```

### **Fase 2: Atualizar Definição de Ações**
```python
# ✅ Usar helpers nas ações (manter regras inalteradas!)
acoes_diretos = [
    ato_ceju,
    ato_respcalc,
    (criar_acao_gigs("1", "xs aud"), ato_assistente),
    (criar_acao_padrao_liq(), ato_concor),
    (criar_acao_gigs("-1", "xs pec"), ato_prevjud),
]
```

### **Fase 3: Simplificar Execução**
```python
# ✅ Criar executar_regras_simplificado() estilo p2b.py
# - Loop direto sobre petições
# - Testa blocos em ordem
# - Primeira match = executa e para
```

### **Fase 4: Implementar Execução de Ações**
```python
# ✅ Criar _executar_acao_completa()
# - Suporta callable simples
# - Suporta tuplas (sequencial)
# - Suporta condicionais (False = para tupla)
```

### **Fase 5: Remover Código Antigo**
```python
# ✅ Deletar:
# - 15+ funções wrapper
# - classificar_peticoes()
# - executar_regras() antigo com 4 loops
```

---

## 🎯 RESULTADO FINAL

### **Mantém:**
- ✅ TODAS as 20 hipóteses existentes (sem alteração!)
- ✅ Padrões regex exatos (sem alteração!)
- ✅ Validações especiais (pericias, diretos)
- ✅ Ordem de execução (apagar por último)
- ✅ Estrutura de campos da PeticaoLinha
- ✅ Concatenação de campos para regex

### **Melhora:**
- ✅ 53% menos código (1700 → 800 linhas)
- ✅ 50% menos funções (40 → 20)
- ✅ Sem funções wrapper desnecessárias
- ✅ Estrutura mais simples (2 loops vs 4 loops)
- ✅ Prioridade explícita (break após match)
- ✅ Facilidade de manutenção
- ✅ Padrão consistente com p2b.py (onde aplicável)

---

## 📝 OBSERVAÇÕES FINAIS

### **Diferenças Fundamentais Respeitadas:**

1. **p2b.py:** Texto extraído de PDF → regex no conteúdo → executa ação
2. **pet_novo.py (BLOCOS 1-5):** Campos de tabela → regex nos campos concatenados → executa ação
3. **pet_novo.py (BLOCO ANÁLISE):** Campos de tabela → regex detecta "análise" → extrai PDF → regex no PDF → executa ação

### **Arquitetura em 2 Fases do pet_novo.py:**

```
FASE 1: CLASSIFICAÇÃO (todos os blocos)
├─ Regex nos campos concatenados
├─ Detecta qual BLOCO e qual HIPÓTESE
├─ Para maioria dos blocos: ação já está definida
└─ Para ANÁLISE: só detecta que precisa análise (ação indefinida)

FASE 2: EXECUÇÃO DE AÇÃO
│
├─ APAGAR (único que NÃO abre processo)
│  └─ Executa direto na lista (remove da tabela)
│
├─ PERÍCIAS, RECURSO, DIRETOS, GIGS (ação já definida)
│  ├─ Abre processo em nova aba
│  ├─ Executa ação (já conhecida da Fase 1)
│  └─ Fecha processo e volta para lista
│
└─ ANÁLISE (ação ainda indefinida)
   ├─ Abre processo em nova aba
   ├─ Extrai PDF da petição
   ├─ Regex no conteúdo do PDF (padrão p2b.py!)
   ├─ DECIDE qual ação executar
   ├─ Executa ação
   └─ Fecha processo e volta para lista
```

### **Similaridades Aproveitadas:**

1. ✅ Regex flexível (gerar_regex_flexivel)
2. ✅ Normalização de texto
3. ✅ Ações chamadas diretamente (sem wrappers intermediários)
4. ✅ Tuplas para múltiplas ações sequenciais
5. ✅ Prioridade (primeira match = executa e para)
6. ✅ **BLOCO ANÁLISE usa padrão p2b.py:** regex no PDF → ação

### **Decisão de Design:**

**MANTER** estrutura de regras por blocos (já está correta!)  
**ELIMINAR** funções wrapper desnecessárias  
**SIMPLIFICAR** execução (4 loops → 2 loops)  
**PRESERVAR** todas as validações especiais  

---

**Data:** 2025-12-17  
**Versão:** 2.0 (CORRIGIDA)  
**Autor:** GitHub Copilot (Claude Sonnet 4.5)
