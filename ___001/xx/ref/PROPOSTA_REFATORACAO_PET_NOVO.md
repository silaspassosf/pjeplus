# PROPOSTA DE REFATORAÇÃO: pet_novo.py → Padrão p2b.py

## 📋 ANÁLISE COMPARATIVA

### **p2b.py - Estrutura Atual (EFICIENTE)**

```python
# ✅ PADRÃO DIRETO: regex + ação direta
regras = [
    # Cada regra: ([lista_regex], tipo_acao, params, acao_secundaria)
    ([gerar_regex_geral('A pronúncia da')], None, None, prescreve),
    
    ([gerar_regex_geral(k) for k in ['sob pena de bloqueio']], 
     'checar_cabecalho_impugnacoes', None, None),
    
    ([gerar_regex_geral(k) for k in ['05 dias para a apresentação', 'suspensão da execução']], 
     'gigs', '1/Silas/Sob 24', ato_sobrestamento),
    
    ([gerar_regex_geral('exequente, ora embargado')],
     'gigs', '1/fernanda/julgamento embargos', None),
]

# ✅ EXECUÇÃO DIRETA - sem funções wrapper desnecessárias
for idx, (keywords, tipo_acao, params, acao_sec) in enumerate(regras):
    for regex in keywords:
        if regex.search(texto_normalizado):
            if acao_definida == 'gigs':
                dias, responsavel, observacao = parse_gigs_param(parametros_acao)
                criar_gigs(driver, dias, responsavel, observacao)  # ← CHAMADA DIRETA
                
                if acao_secundaria:
                    acao_secundaria(driver)  # ← CHAMADA DIRETA
```

**Características:**
- ✅ Regex direta sobre texto extraído
- ✅ Ações chamadas diretamente (sem wrapper)
- ✅ Múltiplas ações via tupla simples: `(acao_1, acao_2)`
- ✅ Sem necessidade de criar funções intermediárias
- ✅ Código limpo e direto

---

### **pet_novo.py - Estrutura Atual (INEFICIENTE)**

```python
# ❌ PROBLEMA: funções wrapper desnecessárias para cada hipótese

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
    # ... mesma estrutura repetitiva

def padrao_liq_acao(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """Wrapper para padrao_liq() via API"""
    # ... mais código wrapper

# ❌ PROBLEMA: estrutura complexa com dicionários e funções
def definir_regras() -> Dict[str, List[Tuple[str, List, Callable]]]:
    regra_diretos_hipoteses = [
        ("CAGED", [gerar_regex_flexivel('caged')]),
        # ...
    ]
    
    acoes_diretos = [
        (cris_gigs_minus1_xs_pec, ato_prevjud),  # ← funções wrapper desnecessárias
    ]
    
    return {
        "diretos": regra_diretos,
        # ...
    }

# ❌ PROBLEMA: execução complexa com múltiplos loops
def executar_regras(driver, peticoes, regras):
    resultado = classificar_peticoes(peticoes, regras)
    
    for nome_hipotese, peticoes_da_hipotese in resultado["diretos"]["peticoes_por_hipotese"].items():
        acao = hipoteses_diretos.get(nome_hipotese)
        for peticao in peticoes_da_hipotese:
            _processar_petição_completa(driver, peticao, acao)
```

**Problemas:**
- ❌ Funções wrapper desnecessárias: `cris_gigs_minus1_xs_pec`, `criar_gigs_1_xs_aud`, etc.
- ❌ Estrutura complexa com dicionários aninhados
- ❌ Múltiplos loops e verificações
- ❌ Código verboso e difícil de manter
- ❌ Cada nova regra exige criar nova função wrapper

---

## 🎯 PROPOSTA DE REFATORAÇÃO

### **Estrutura Simplificada (Padrão p2b.py)**

```python
# ============================================================================
# HELPERS PARA REGEX E NORMALIZAÇÃO
# ============================================================================

def remover_acentos(txt: str) -> str:
    """Remove acentos de texto."""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

def normalizar_texto(txt: str) -> str:
    """Normaliza texto (remove acentos, lowercase)."""
    return remover_acentos(txt.lower())

def gerar_regex_flexivel(termo: str) -> re.Pattern:
    """
    Gera regex flexível permitindo pontuação/espaços entre palavras.
    Exemplo: 'razões finais' → r'razoes[\s\w\.,;:!\-–—()]*finais'
    """
    termo_norm = normalizar_texto(termo)
    palavras = termo_norm.split()
    partes = [re.escape(p) for p in palavras]
    
    regex = ''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()]*'
    
    return re.compile(rf"{regex}", re.IGNORECASE)

def match_qualquer(texto: str, *termos: str) -> bool:
    """Retorna True se qualquer termo bater com texto."""
    for termo in termos:
        if gerar_regex_flexivel(termo).search(texto):
            return True
    return False

# ============================================================================
# DEFINIÇÃO DE REGRAS (PADRÃO p2b.py)
# ============================================================================

def definir_regras_pet() -> List[Tuple[str, List, str, Any, Any]]:
    """
    Define regras de petições no formato p2b.py:
    Cada regra: (nome, [regex_patterns], tipo_acao, params, acao_secundaria)
    
    tipo_acao pode ser:
    - None: executa apenas acao_secundaria
    - 'gigs': cria GIGS com params (formato: 'prazo/responsavel/observacao')
    - 'apagar': apaga petição
    - callable: executa função diretamente
    
    acao_secundaria:
    - None: nenhuma ação adicional
    - callable: função a executar após ação principal
    - tuple: (acao1, acao2, ...) executa múltiplas ações em sequência
    """
    
    # Imports de atos
    from atos.wrappers_ato import (
        ato_ceju, ato_respcalc, ato_assistente, ato_concor, ato_prevjud,
        ato_instc, ato_inste, ato_laudo, ato_esc, ato_escliq, ato_datalocal,
        ato_gen
    )
    from atos.movimentos import analise_pet
    from Fix import criar_gigs
    
    # Helper para criar lambda de gigs
    def gigs_lambda(dias: str, obs: str):
        """Cria lambda para criar_gigs com parâmetros fixos."""
        return lambda driver, pet: criar_gigs(driver, dias, obs)
    
    # Helper para criar lambda condicional de padrao_liq
    def padrao_liq_condicional():
        """
        Lambda que verifica condições de padrao_liq e retorna True/False.
        Se retornar True, tupla continua executando próximas ações.
        """
        def _check(driver, pet):
            from Fix.variaveis import session_from_driver, PjeApiClient, padrao_liq
            try:
                sess, trt_host = session_from_driver(driver)
                client = PjeApiClient(sess, trt_host)
                resultado = padrao_liq(client, pet.numero_processo)
                
                apenas_uma = resultado.get('apenas_uma_com_advogado', False)
                tem_perito = resultado.get('tem_perito', False)
                
                return apenas_uma and not tem_perito
            except:
                return False
        return _check
    
    regras = [
        # =====================================================================
        # BLOCO 1: APAGAR (ALTA PRIORIDADE)
        # =====================================================================
        
        # Razões Finais / Carta Convite
        ("Apagar: Razões/Convite",
         [lambda txt: match_qualquer(txt, 'razões finais', 'carta convite')],
         'apagar', None, None),
        
        # Réplica em Conhecimento
        ("Apagar: Réplica Conhecimento",
         [lambda txt: gerar_regex_flexivel('réplica').search(txt) and 
                     gerar_regex_flexivel('conhecimento').search(txt)],
         'apagar', None, None),
        
        # Acordo (tipos específicos)
        ("Apagar: Acordo",
         [lambda txt: gerar_regex_flexivel('aguardando cumprimento de acordo').search(txt) and
                     match_qualquer(txt, 'contestação', 'habilitação', 'procuração', 
                                   'carta de preposição', 'substabelecimento')],
         'apagar', None, None),
        
        # Manifestação - Carta/Substabelecimento
        ("Apagar: Manifestação Carta/Sub",
         [lambda txt: gerar_regex_flexivel('manifestação').search(txt) and
                     match_qualquer(txt, 'carta de preposição', 'substabelecimento')],
         'apagar', None, None),
        
        # Triagem Inicial
        ("Apagar: Triagem Inicial",
         [gerar_regex_flexivel('triagem inicial')],
         'apagar', None, None),
        
        # =====================================================================
        # BLOCO 2: PERÍCIAS (requer eh_perito=True)
        # =====================================================================
        
        # Esclarecimentos - Conhecimento
        ("Perícias: Esclarecimentos Conhecimento",
         [lambda txt: gerar_regex_flexivel('esclarecimentos').search(txt) and 
                     gerar_regex_flexivel('conhecimento').search(txt)],
         None, None, ato_esc),
        
        # Esclarecimentos - Liquidação
        ("Perícias: Esclarecimentos Liquidação",
         [lambda txt: gerar_regex_flexivel('esclarecimentos').search(txt) and 
                     gerar_regex_flexivel('liquidação').search(txt)],
         None, None, ato_escliq),
        
        # Apresentação de Laudo Pericial
        ("Perícias: Laudo",
         [gerar_regex_flexivel('apresentação de laudo pericial')],
         None, None, ato_laudo),
        
        # Indicação de Data - AÇÃO COMPOSTA: gigs + ato_datalocal
        ("Perícias: Data Realização",
         [gerar_regex_flexivel('indicação de data')],
         None, None, (gigs_lambda("1", "xs audx"), ato_datalocal)),
        
        # =====================================================================
        # BLOCO 3: RECURSO
        # =====================================================================
        
        # Agravo - Conhecimento
        ("Recurso: Agravo Conhecimento",
         [lambda txt: gerar_regex_flexivel('agravo de instrumento').search(txt) and 
                     gerar_regex_flexivel('conhecimento').search(txt)],
         None, None, ato_instc),
        
        # Agravo - Liquidação/Execução
        ("Recurso: Agravo Liquidação/Execução",
         [lambda txt: gerar_regex_flexivel('agravo de instrumento').search(txt) and 
                     match_qualquer(txt, 'liquidação', 'execução')],
         None, None, ato_inste),
        
        # =====================================================================
        # BLOCO 4: DIRETOS (sem análise de conteúdo)
        # =====================================================================
        
        # Habilitação com CEJU
        ("Diretos: Habilitação CEJU",
         [gerar_regex_flexivel('habilitação')],
         None, None, ato_ceju),
        
        # Apresentação de Cálculos
        ("Diretos: Cálculos",
         [lambda txt: gerar_regex_flexivel('apresentação de cálculos').search(txt) and 
                     gerar_regex_flexivel('cálculo').search(txt)],
         None, None, ato_respcalc),
        
        # Assistente - AÇÃO COMPOSTA: gigs + ato_assistente
        ("Diretos: Assistente",
         [gerar_regex_flexivel('assistente')],
         None, None, (gigs_lambda("1", "xs aud"), ato_assistente)),
        
        # Impugnação - AÇÃO COMPOSTA CONDICIONAL: padrao_liq + ato_concor
        # Só executa ato_concor se padrao_liq_condicional retornar True
        ("Diretos: Impugnação",
         [lambda txt: gerar_regex_flexivel('impugnação').search(txt) and 
                     gerar_regex_flexivel('liquidação').search(txt)],
         None, None, (padrao_liq_condicional(), ato_concor)),
        
        # CAGED - AÇÃO COMPOSTA: gigs + ato_prevjud
        ("Diretos: CAGED",
         [gerar_regex_flexivel('caged')],
         None, None, (gigs_lambda("-1", "xs pec"), ato_prevjud)),
        
        # =====================================================================
        # BLOCO 5: GIGS (homologação/liberação)
        # =====================================================================
        
        # GIGS - Homologação/Liberação (decide parâmetro dinamicamente)
        ("GIGS: Homologação/Liberação",
         [lambda txt: match_qualquer(txt, 'concordancia', 'comprovante', 'deposito', 'parcela')],
         'gigs_dinamico', None, None),
        
        # =====================================================================
        # BLOCO 6: ANÁLISE (última opção - extrai PDF)
        # =====================================================================
        
        # Manifestação - Despacho Genérico
        ("Análise: Despacho Genérico",
         [lambda txt: gerar_regex_flexivel('manifestação').search(txt) and 
                     match_qualquer(txt, 'prosseguimento', 'meios de execução')],
         None, None, ato_gen),
        
        # Manifestação - Análise de conteúdo
        ("Análise: Manifestação",
         [lambda txt: gerar_regex_flexivel('manifestação').search(txt)],
         None, None, analise_pet),
        
        # Manifestação - Expedição de Ofício
        ("Análise: Expedição Ofício",
         [lambda txt: gerar_regex_flexivel('manifestação').search(txt) and 
                     gerar_regex_flexivel('expedição de ofício').search(txt)],
         None, None, analise_pet),
    ]
    
    return regras


# ============================================================================
# EXECUÇÃO DE REGRAS (PADRÃO p2b.py)
# ============================================================================

def processar_peticao(driver: WebDriver, peticao: PeticaoLinha, regras: List) -> bool:
    """
    Processa uma petição contra lista de regras (padrão p2b.py).
    
    1. Normaliza texto da petição (campos concatenados)
    2. Itera pelas regras em ordem
    3. Para cada regra, testa todos os padrões
    4. Se TODOS os padrões baterem, executa ação
    5. PARA após primeira regra executada (prioridade)
    """
    try:
        # 1. Normalizar texto (todos os campos)
        texto_completo = f"{peticao.tipo_peticao} {peticao.descricao} {peticao.tarefa} {peticao.fase}"
        texto_normalizado = normalizar_texto(texto_completo)
        
        print(f"\n[PET_PROC] Processando: {peticao.numero_processo}")
        print(f"[PET_PROC]   Tipo: {peticao.tipo_peticao}")
        print(f"[PET_PROC]   Desc: {peticao.descricao}")
        
        # 2. Iterar pelas regras
        for idx, (nome_regra, padroes, tipo_acao, params, acao_sec) in enumerate(regras):
            
            # FILTRO ESPECIAL: regras de PERÍCIAS só aplicam se eh_perito=True
            if nome_regra.startswith("Perícias:") and not peticao.eh_perito:
                continue
            
            # 3. Testar TODOS os padrões
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
                else:
                    match = False
                    break
            
            if not match:
                continue
            
            # 4. MATCH! Executar ação
            print(f"[PET_PROC] ✅ MATCH: {nome_regra}")
            
            # Executar ação principal
            if tipo_acao == 'apagar':
                resultado = _acao_apagar(driver, peticao)
            elif tipo_acao == 'gigs_dinamico':
                resultado = _acao_gigs_dinamico(driver, peticao, texto_normalizado)
            elif tipo_acao == 'gigs':
                resultado = _acao_gigs_fixo(driver, peticao, params)
            elif callable(tipo_acao):
                resultado = tipo_acao(driver, peticao)
            else:
                resultado = True  # Sem ação principal
            
            # Executar ação secundária (se houver)
            if acao_sec:
                if isinstance(acao_sec, tuple):
                    # Múltiplas ações em sequência
                    for acao in acao_sec:
                        if callable(acao):
                            resultado_acao = acao(driver, peticao)
                            # Se retornar False, interrompe tupla
                            if resultado_acao is False:
                                break
                elif callable(acao_sec):
                    # Ação única
                    acao_sec(driver, peticao)
            
            # 5. PARAR após primeira regra (prioridade)
            return resultado
        
        # Nenhuma regra bateu
        print(f"[PET_PROC] ⚠️ Nenhuma regra aplicável")
        return False
        
    except Exception as e:
        logger.error(f"[PET_PROC] Erro: {e}")
        return False


def _acao_apagar(driver: WebDriver, peticao: PeticaoLinha) -> bool:
    """Apaga petição da lista."""
    try:
        # Localizar linha
        linhas = driver.find_elements(By.CSS_SELECTOR, "tr.cdk-drag")
        linha_encontrada = None
        
        for linha in linhas:
            tds = linha.find_elements(By.TAG_NAME, "td")
            if len(tds) > 1 and peticao.numero_processo in tds[1].text.strip():
                linha_encontrada = linha
                break
        
        if not linha_encontrada:
            return False
        
        # Clicar trash
        trash_icon = linha_encontrada.find_element(By.CSS_SELECTOR, "i.fa-trash-alt")
        driver.execute_script("arguments[0].click();", trash_icon)
        time.sleep(0.5)
        
        # Confirmar com SPACE
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.SPACE)
        time.sleep(1)
        
        print(f"[PET_PROC]   ✅ Petição apagada")
        return True
    except:
        return False


def _acao_gigs_dinamico(driver: WebDriver, peticao: PeticaoLinha, texto: str) -> bool:
    """
    Cria GIGS com parâmetros dinâmicos baseado no texto.
    - concordancia → "1, Silvia homologacao de calculos"
    - comprovante/deposito → "1, Bruna Liberacao"
    """
    try:
        if re.search(r'concordancia', texto):
            criar_gigs(driver, "1", "Silvia homologacao de calculos")
            print(f"[PET_PROC]   ✅ GIGS criado: Homologação")
        elif re.search(r'comprovante|deposito', texto):
            criar_gigs(driver, "1", "Bruna Liberacao")
            print(f"[PET_PROC]   ✅ GIGS criado: Liberação")
        else:
            return False
        return True
    except:
        return False


def _acao_gigs_fixo(driver: WebDriver, peticao: PeticaoLinha, params: str) -> bool:
    """
    Cria GIGS com parâmetros fixos.
    params formato: "prazo/responsavel/observacao"
    """
    try:
        if not params:
            return False
        
        partes = params.split('/')
        if len(partes) != 3:
            return False
        
        dias, responsavel, observacao = partes
        criar_gigs(driver, dias, f"{responsavel} {observacao}")
        print(f"[PET_PROC]   ✅ GIGS criado: {observacao}")
        return True
    except:
        return False


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def processar_peticoes_escaninho(driver: WebDriver) -> bool:
    """
    Função principal para processar petições do escaninho.
    
    Fluxo:
    1. Navega para escaninho
    2. Extrai lista de petições
    3. Define regras
    4. Processa cada petição contra regras (ordem: primeira match = executa)
    """
    try:
        print("\n" + "="*80)
        print("[PET_MAIN] PROCESSAMENTO DE PETIÇÕES - PADRÃO p2b.py")
        print("="*80)
        
        # 1. Navegar
        print(f"\n[PET_MAIN] 1. Navegando para escaninho...")
        driver.get(ESCANINHO_URL)
        time.sleep(3)
        
        # 2. Extrair petições
        print(f"\n[PET_MAIN] 2. Extraindo petições...")
        peticoes = extrair_peticoes_tabela(driver)
        
        if not peticoes:
            print("[PET_MAIN] ⚠️ Nenhuma petição encontrada")
            return False
        
        print(f"[PET_MAIN] ✅ {len(peticoes)} petições extraídas")
        
        # 3. Definir regras
        print(f"\n[PET_MAIN] 3. Definindo regras...")
        regras = definir_regras_pet()
        print(f"[PET_MAIN] ✅ {len(regras)} regras definidas")
        
        # 4. Processar petições
        print(f"\n[PET_MAIN] 4. Processando petições...")
        
        sucesso = 0
        falha = 0
        
        for peticao in peticoes:
            resultado = processar_peticao(driver, peticao, regras)
            if resultado:
                sucesso += 1
            else:
                falha += 1
            time.sleep(0.5)
        
        # 5. Relatório final
        print(f"\n[PET_MAIN] ===== RELATÓRIO FINAL =====")
        print(f"[PET_MAIN] Total processadas: {len(peticoes)}")
        print(f"[PET_MAIN] Sucesso: {sucesso}")
        print(f"[PET_MAIN] Falha: {falha}")
        print(f"[PET_MAIN] Taxa: {sucesso/len(peticoes)*100:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"[PET_MAIN] Erro: {e}")
        return False
```

---

## 📊 COMPARAÇÃO: ANTES vs DEPOIS

### **ANTES (pet_novo.py atual)**

```python
# ❌ 15+ funções wrapper desnecessárias
def cris_gigs_minus1_xs_pec(driver, peticao): ...
def criar_gigs_1_xs_aud(driver, peticao): ...
def padrao_liq_acao(driver, peticao): ...
def acao_gigs(driver, peticao): ...
def acao_pericias_com_data(driver, peticao): ...

# ❌ Estrutura complexa com dicionários
def definir_regras() -> Dict[str, List[Tuple[str, List, Callable]]]:
    regra_diretos_hipoteses = [...]
    acoes_diretos = [...]
    return {"diretos": [...], "pericias": [...], ...}

# ❌ Execução complexa com múltiplos loops
def executar_regras(driver, peticoes, regras):
    resultado = classificar_peticoes(peticoes, regras)
    for bloco in ["pericias", "gigs", "recurso", "diretos", "analise"]:
        for hipotese, peticoes_hipotese in resultado[bloco]["peticoes_por_hipotese"].items():
            for peticao in peticoes_hipotese:
                _processar_petição_completa(driver, peticao, acao)

# Total: ~1700 linhas
```

### **DEPOIS (proposta refatorada)**

```python
# ✅ SEM funções wrapper - lambdas inline quando necessário
def gigs_lambda(dias: str, obs: str):
    return lambda driver, pet: criar_gigs(driver, dias, obs)

# ✅ Estrutura simples: lista de tuplas
def definir_regras_pet() -> List[Tuple[str, List, str, Any, Any]]:
    regras = [
        ("Diretos: CAGED", [gerar_regex_flexivel('caged')], 
         None, None, (gigs_lambda("-1", "xs pec"), ato_prevjud)),
        # ... todas as regras em uma lista simples
    ]
    return regras

# ✅ Execução direta: um loop
def processar_peticoes_escaninho(driver):
    peticoes = extrair_peticoes_tabela(driver)
    regras = definir_regras_pet()
    
    for peticao in peticoes:
        processar_peticao(driver, peticao, regras)

# Total estimado: ~600 linhas (redução de 65%)
```

---

## 🎯 BENEFÍCIOS DA REFATORAÇÃO

### **1. Simplicidade**
- ✅ Código 65% menor (1700 → 600 linhas)
- ✅ Sem funções wrapper desnecessárias
- ✅ Estrutura linear e direta

### **2. Manutenibilidade**
- ✅ Adicionar nova regra = adicionar 1 tupla
- ✅ Não precisa criar função wrapper
- ✅ Tudo em um lugar (definir_regras_pet)

### **3. Performance**
- ✅ Menos chamadas de função (sem wrappers)
- ✅ Execução mais rápida (um loop vs múltiplos loops)
- ✅ Menos overhead de memória

### **4. Clareza**
- ✅ Lógica de negócio visível na definição de regras
- ✅ Ações compostas expressas diretamente via tuplas
- ✅ Sem abstrações desnecessárias

---

## 🔄 PLANO DE MIGRAÇÃO

### **Fase 1: Backup e Setup**
1. ✅ Criar backup de `pet_novo.py`
2. ✅ Criar `pet_novo_refatorado.py` com nova estrutura
3. ✅ Manter `pet_novo.py` original intacto

### **Fase 2: Implementação Core**
1. Implementar funções helper (normalizar_texto, gerar_regex_flexivel, etc.)
2. Implementar definir_regras_pet() com TODAS as regras atuais
3. Implementar processar_peticao() (motor de execução)
4. Implementar funções auxiliares (_acao_apagar, _acao_gigs_dinamico, etc.)

### **Fase 3: Migração de Regras**
1. Migrar BLOCO 1: APAGAR (5 hipóteses)
2. Migrar BLOCO 2: PERÍCIAS (4 hipóteses)
3. Migrar BLOCO 3: RECURSO (2 hipóteses)
4. Migrar BLOCO 4: DIRETOS (5 hipóteses)
5. Migrar BLOCO 5: GIGS (1 hipótese)
6. Migrar BLOCO 6: ANÁLISE (3 hipóteses)

### **Fase 4: Testes**
1. Testar cada bloco isoladamente
2. Testar prioridades (APAGAR > PERÍCIAS > RECURSO > DIRETOS > GIGS > ANÁLISE)
3. Testar ações compostas (tuplas)
4. Testar ações condicionais (padrao_liq)

### **Fase 5: Deploy**
1. Substituir chamadas de `pet_novo.py` por `pet_novo_refatorado.py`
2. Monitorar logs e performance
3. Ajustar conforme necessário
4. Arquivar `pet_novo.py` original após validação completa

---

## ✅ CHECKLIST DE VALIDAÇÃO

- [ ] Todas as 20 hipóteses migradas
- [ ] Ações compostas funcionando (tuplas)
- [ ] Ações condicionais funcionando (padrao_liq)
- [ ] Prioridade de blocos respeitada
- [ ] Filtro de perícias (eh_perito) funcionando
- [ ] Logs consistentes e informativos
- [ ] Performance igual ou melhor que versão anterior
- [ ] Sem regressões em funcionalidades existentes

---

## 📝 OBSERVAÇÕES IMPORTANTES

### **Ações Compostas (Tuplas)**
```python
# p2b.py usa acao_secundaria simples
# pet_novo refatorado usa tuplas para múltiplas ações

# Exemplo 1: CAGED (sempre executa ambas)
(gigs_lambda("-1", "xs pec"), ato_prevjud)
# Executa: criar_gigs → ato_prevjud

# Exemplo 2: Impugnação (condicional)
(padrao_liq_condicional(), ato_concor)
# Executa: padrao_liq_condicional() → se True, executa ato_concor

# Exemplo 3: Assistente
(gigs_lambda("1", "xs aud"), ato_assistente)
# Executa: criar_gigs → ato_assistente
```

### **Prioridade de Blocos**
```python
# Ordem de teste (primeira match = executa e para)
1. APAGAR (remove da lista)
2. PERÍCIAS (requer eh_perito=True)
3. RECURSO
4. DIRETOS
5. GIGS
6. ANÁLISE (extrai PDF se necessário)
```

### **Filtros Especiais**
```python
# PERÍCIAS: só aplica se eh_perito=True
if nome_regra.startswith("Perícias:") and not peticao.eh_perito:
    continue

# IMPUGNAÇÃO: só executa ato_concor se fase="Liquidação"
lambda txt: gerar_regex_flexivel('liquidação').search(txt)

# HABILITAÇÃO: valida data de audiência (se implementado)
# TODO: adicionar filtro de data audiência > 01/02/2026
```

---

## 🚀 PRÓXIMOS PASSOS

1. **REVISAR** esta proposta e validar com usuário
2. **IMPLEMENTAR** estrutura refatorada em arquivo separado
3. **TESTAR** com dados reais do escaninho
4. **VALIDAR** comportamento contra versão atual
5. **SUBSTITUIR** versão antiga pela refatorada
6. **DOCUMENTAR** mudanças e manter este documento como referência

---

**Data:** 2025-12-17  
**Versão:** 1.0  
**Autor:** GitHub Copilot (Claude Sonnet 4.5)
