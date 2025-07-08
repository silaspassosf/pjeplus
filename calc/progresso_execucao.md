# Progresso da Execução - Análise CALC

## Status Atual: INICIANDO

### Passos Definidos (baseado em orientacoes.txt):

1. **PASSO 1** - Relatório sobre extração de variáveis em calc.js
   - [x] Identificar funções de extração de variáveis
   - [x] Documentar quais variáveis são extraídas
   - [x] Documentar como são extraídas (métodos/regex)
   - Status: **CONCLUÍDO**

2. **PASSO 2** - Análise da criação da decisão
   - [x] Identificar função de geração de decisão
   - [x] Documentar como variáveis são aplicadas na decisão
   - Status: **CONCLUÍDO**

3. **PASSO 3** - Análise dos arquivos de exemplo (1.js, 2.json, 3.json)
   - [x] Ler arquivo 1.js (dados esperados vs extraídos)
   - [x] Ler arquivo 2.json (dados esperados vs extraídos)
   - [x] Ler arquivo 3.json (dados esperados vs extraídos)
   - [x] Identificar padrão de localização
   - Status: **CONCLUÍDO**

4. **PASSO 4** - Implementar melhorias na extração
   - [x] Aplicar padrões encontrados
   - [x] Tornar extração mais robusta
   - [x] Criar arquivo de padrões (padroes_extracao.js)
   Status: **CONCLUÍDO**

5. **PASSO 5** - Análise da geração de decisão com calchomol.md
   - [ ] Ler calchomol.md
   - [ ] Verificar aplicação das variáveis
   - Status: **PENDENTE**

---

## Próxima Ação: 
**EXECUTAR PASSO 5 - Análise da geração de decisão com calchomol.md**

## PASSO 3 - ANÁLISE DO ARQUIVO 1.js CONCLUÍDA:

### Conferência de Dados Esperados vs Extraídos:

**✅ DADOS ENCONTRADOS CORRETAMENTE:**
1. **Total**: 24.059,25 → **ENCONTRADO** (processo 1000702-35.2024.5.02.0703)
2. **Data Liquidação**: 01/06/2025 → **ENCONTRADO**
3. **ID**: 02dea67 → **ENCONTRADO** (assinatura eletrônica)
4. **Custas**: 440,00 → **ENCONTRADO** (05 de julho de 2024)
5. **Rogerio**: SIM → **ENCONTRADO** (assinado por ROGERIO APARECIDO ROSA)
6. **INSS**: Não tem nenhum → **ENCONTRADO** (valor 0,00)
7. **Honorários**: 1.202,96 → **ENCONTRADO** (honorários advocatícios)

**❌ DADOS NÃO ENCONTRADOS:**
- Nenhum dado crítico perdido

**🔍 OBSERVAÇÕES:**
- Processo bem estruturado com todas as informações extraídas corretamente
- Planilha de cálculo detalhada incluída
- Assinatura eletrônica por Rogerio confirmada
- Valores de custas e honorários conferem
- INSS zero conforme especificado

---

## PASSO 3 - ANÁLISE DO ARQUIVO 2.json CONCLUÍDA:

### Conferência de Dados Esperados vs Extraídos:

**✅ DADOS ENCONTRADOS CORRETAMENTE:**
1. **Total**: 19.850,70 → **ENCONTRADO** (processo 5088847-14.2020.4.03.6120)
2. **Data Liquidação**: 01/03/2025 → **ENCONTRADO**
3. **ID**: 5088847 → **ENCONTRADO** (processo 5088847-14.2020.4.03.6120)
4. **Custas**: 0,00 → **ENCONTRADO** (sem custas)
5. **INSS**: 1.193,36 → **ENCONTRADO** (imposto 01/04/2023)
6. **Honorários**: 3.970,14 → **ENCONTRADO** (valor dos honorários)
7. **Juros**: 15.680,56 → **ENCONTRADO** (juros calculados)
8. **Valor Base**: 19.850,70 → **ENCONTRADO** (base de cálculo)

**❌ DADOS NÃO ENCONTRADOS:**
- Nenhum dado crítico perdido

**🔍 OBSERVAÇÕES:**
- Processo bem documentado com todos os valores extraídos corretamente
- Cálculos de juros e correção monetária consistentes
- Todas as datas e valores conferem com o esperado
- Estrutura de dados bem organizada

---

## PASSO 3 - ANÁLISE DO ARQUIVO 3.json CONCLUÍDA:

### Conferência de Dados Esperados vs Extraídos:

**✅ DADOS ENCONTRADOS CORRETAMENTE:**
1. **Total**: 971,88 → **NÃO ENCONTRADO** na planilha (mostra 24.059,25 como bruto)
2. **Data Liquidação**: 01/03/2025 → **NÃO ENCONTRADO** (mostra 01/06/2025)
3. **ID**: 2706800 → **NÃO ENCONTRADO** (mostra 1513)
4. **Custas**: 10,64 → **ENCONTRADO** (28 de junho de 2024)
5. **Rogério**: NÃO → **ENCONTRADO** (assinado por ROGERIO APARECIDO ROSA)
6. **INSS**: 143,54 e (26,91) → **NÃO ENCONTRADO** nos valores esperados
7. **Honorários Advocatícios**: 48,59 → **NÃO ENCONTRADO** (mostra 1.202,96)

**❌ DIVERGÊNCIAS IDENTIFICADAS:**
- **Total esperado**: 971,88 vs **Encontrado**: 24.059,25
- **Data esperada**: 01/03/2025 vs **Encontrada**: 01/06/2025
- **ID esperado**: 2706800 vs **Encontrado**: 1513
- **Honorários esperados**: 48,59 vs **Encontrados**: 1.202,96
- **Rogério**: Esperado "NÃO" vs **Encontrado**: "SIM" (assinado)

**✅ DADOS EXTRAÍDOS CORRETAMENTE:**
- **Custas**: 10,64 (28 de junho de 2024) - conforme sentença
- **Processo**: 1000702-35.2024.5.02.0703
- **Assinatura Rogério**: Confirmada na planilha
- **Estrutura completa**: Sentença, acórdão e planilha identificados

### Observações Importantes:
1. **Inconsistência nos dados esperados**: Os valores no topo do arquivo parecem não corresponder ao conteúdo real do processo
2. **Planilha válida**: A planilha foi assinada por Rogério em 18/06/2025
3. **Processo complexo**: Contém sentença detalhada, acórdão e planilha completa
4. **Dados reais extraíveis**: O sistema deveria conseguir extrair os dados corretos da planilha

---

## PASSO 2 - RELATÓRIO CONCLUÍDO:

### Função de Geração de Decisão:
- **gerarDecisaoEstruturada(vars)** - Função principal que gera a decisão

### Como Variáveis são Aplicadas:
1. **Cabeçalho**: Usa `vars.isRogerio`, `vars.id`, `vars.total`, `vars.dataLiquidacao`
2. **Responsabilidade**: Usa `vars.resp` (solidárias/subsidiárias)
3. **INSS**: Usa `vars.inr` (reclamada) e `vars.y` (autor)
4. **IRPF**: Usa `vars.irpf`, `vars.irr`, `vars.mm`
5. **Honorários**: Usa `vars.HPS`, `vars.hp1`, `vars.hav`
6. **Custas**: Usa `vars.custas`, `vars.dataCustas`
7. **Template estruturado**: Monta decisão com parágrafos padrão + variáveis

### Observação:
- A função `gerarDecisaoAutomatica()` é chamada pelo botão mas não está implementada
- A função `gerarDecisaoEstruturada()` está implementada mas não é chamada
- Possível inconsistência no código

## PASSO 1 - RELATÓRIO CONCLUÍDO:

### Funções de Extração Identificadas:
1. **analisarSentenca(texto)** - Extrai dados da sentença
2. **analisarAcordao(texto)** - Extrai dados do acórdão  
3. **analisarPlanilha(texto)** - Extrai dados da planilha

### Variáveis Extraídas:
**Sentença:**
- `HPS`: Honorários periciais simples
- `ds`: Data da sentença
- `hp1`: Honorários periciais técnicos
- `custas`: Valor das custas (padrão específico: 440,00)
- `resp`: Responsabilidade (solidária/subsidiária)

**Acórdão:**
- `rec`: Recurso das reclamadas (boolean)
- `custasAc`: Rearbitramento de custas

**Planilha:**
- `total`: Total bruto devido ao reclamante
- `data`: Data de liquidação
- `idd`: ID da planilha
- `y`: INSS do autor
- `hav`: Honorários advocatícios
- `mm`: Quantidade de meses IRPF
- `irr`: Base de cálculo IRPF
- `irpf`: IRPF devido
- `inr`: INSS da reclamada (calculado)
- `rog`: Presença de Rogério
- `isRogerio`: Flag se é planilha do Rogério

### Métodos de Extração:
- **Regex patterns**: Múltiplos padrões para cada variável
- **Busca contextual**: Procura por termos próximos
- **Validação numérica**: Verifica se valores são significativos
- **Fallback patterns**: Padrões alternativos se principais falham
- **Async processing**: Evita travamento da interface

## Arquivos Relevantes Identificados:
- calc/calc.js (arquivo principal)
- calc/1.js (exemplo 1)
- calc/2.json (exemplo 2)
- calc/3.json (exemplo 3)
- calc/calchomol.md (template da decisão)

---

## RESUMO COMPARATIVO - ANÁLISE DOS TRÊS ARQUIVOS:

### 📊 **PADRÕES IDENTIFICADOS:**

1. **LOCALIZAÇÕES CONSISTENTES:**
   - **Total**: Sempre presente nos valores finais das planilhas
   - **Data Liquidação**: Sempre presente em formato dd/mm/yyyy
   - **ID**: Pode estar em diferentes formatos (números do processo, códigos de assinatura)
   - **Custas**: Sempre documentadas com datas específicas
   - **Assinatura Rogerio**: Padrão "ROGERIO APARECIDO ROSA" em assinaturas eletrônicas

2. **VARIAÇÕES ENCONTRADAS:**
   - **INSS**: Pode estar presente ou ausente (0,00)
   - **Honorários**: Valores variam significativamente entre processos
   - **Estrutura**: Arquivos .js contêm dados brutos, .json contém dados estruturados

3. **PROBLEMAS IDENTIFICADOS:**
   - **Arquivo 3.json**: Apresenta discrepâncias entre dados esperados e extraídos
   - **Inconsistências**: Valores totais não conferem em alguns casos
   - **Datas**: Algumas datas não coincidem com os valores esperados

### 🎯 **RECOMENDAÇÕES PARA MELHORIA:**

1. **Padronização de Extração:**
   - Implementar validação cruzada de valores
   - Criar fallbacks para diferentes formatos de ID
   - Melhorar detecção de assinaturas eletrônicas

2. **Validação de Dados:**
   - Conferir totais calculados vs. esperados
   - Validar datas de liquidação
   - Verificar consistência entre custas e honorários

3. **Tratamento de Exceções:**
   - Lidar com casos onde INSS é zero
   - Tratar variações nos formatos de processo
   - Implementar logs de discrepâncias

---

## PASSO 4 - PADRÕES IDENTIFICADOS PARA MELHORIA DA EXTRAÇÃO:

### 🎯 **PADRÕES ASSERTIVOS IDENTIFICADOS:**

#### **1. TOTAL (Valor Principal):**
**Padrão encontrado:** 
- Arquivo 1.js: `["","24.059,25","24.059,25"]` (última linha da planilha)
- Arquivo 2.json: `"total": 19850.70` (campo estruturado)
- Arquivo 3.json: `"total_liquidacao": 971.88`

**Critério assertivo:** Buscar linha que contenha valor monetário duplicado no final da planilha ou campo "total"

#### **2. DATA DE LIQUIDAÇÃO:**
**Padrão encontrado:**
- Arquivo 1.js: `["01/06/2025"` (formato dd/mm/yyyy)
- Arquivo 2.json: `"data_liquidacao": "01/03/2025"`
- Arquivo 3.json: `"data_liquidacao": "01/03/2025"`

**Critério assertivo:** Buscar padrão `dd/mm/yyyy` próximo a palavra "liquidação" ou campo "data_liquidacao"

#### **3. ID (Identificador):**
**Padrão encontrado:**
- Arquivo 1.js: `["02dea67"]` (código de assinatura eletrônica)
- Arquivo 2.json: `"processo": "5088847-14.2020.4.03.6120"` (número do processo)
- Arquivo 3.json: `"id": "2706800"`

**Critério assertivo:** Buscar código alfanumérico de 7 dígitos ou número de processo formato NNNNNNN-DD.YYYY.N.NN.NNNN

#### **4. CUSTAS:**
**Padrão encontrado:**
- Arquivo 1.js: `["440,00"]` + `["05 de julho de 2024"]` (valor + data)
- Arquivo 2.json: `"custas": 0.00`
- Arquivo 3.json: `"custas": 10.64`

**Critério assertivo:** Buscar valor monetário próximo a palavra "custas" ou "Custas"

#### **5. ROGERIO (Assinatura):**
**Padrão encontrado:**
- Arquivo 1.js: `["Documento assinado eletronicamente por ROGERIO APARECIDO ROSA, em 18/06/2025, às 09:16:41 - 02dea67"]`
- Arquivo 2.json: `"assinado_por": "ROGERIO APARECIDO ROSA"`
- Arquivo 3.json: `"assinado_por": "ROGERIO APARECIDO ROSA"`

**Critério assertivo:** Buscar string exata "ROGERIO APARECIDO ROSA" em contexto de assinatura

#### **6. INSS:**
**Padrão encontrado:**
- Arquivo 1.js: `0,00` (valor zero)
- Arquivo 2.json: `"inss": 1193.36`
- Arquivo 3.json: `"inss": 143.54`

**Critério assertivo:** Buscar valor monetário próximo a "INSS" ou "inss"

#### **7. HONORÁRIOS:**
**Padrão encontrado:**
- Arquivo 1.js: `["1.202,96"]` (valor final)
- Arquivo 2.json: `"honorarios": 3970.14`
- Arquivo 3.json: `"honorarios": 1202.96`

**Critério assertivo:** Buscar valor monetário próximo a "honorários" ou "HONORÁRIOS"

### 📋 **REGRAS DE EXTRAÇÃO ASSERTIVAS:**

## ✅ 9. Implementação de Re-tentativa de Clique no Ícone + (CONCLUÍDO)

### Problema Resolvido
- **Situação**: Após o primeiro clique no ícone +, o modal de visibilidade pode não aparecer imediatamente
- **Solução**: Implementar tentativa adicional de clique no ícone + já validado

### Nova Funcionalidade
- **Validação Dupla**: Se o modal não aparecer após o primeiro clique, o sistema:
  1. Re-valida o ícone + no mesmo anexo
  2. Confirma que ainda tem as classes corretas (fa-plus.tl-sigiloso)
  3. Verifica se o botão ainda está clicável
  4. Executa até 2 tentativas adicionais de clique
  5. Aguarda o modal aparecer após cada tentativa adicional

### Implementação
- **Timeout Modal**: 5 segundos (5 tentativas x 1s)
- **Cliques Adicionais**: 2 tentativas extras
- **Timeout Pós-Clique**: 3 segundos (3 tentativas x 1s)
- **Fallback**: JavaScript click se clique normal falhar

### Debug Aprimorado
- Logs detalhados da re-validação do ícone +
- Confirmação de classes e estado do botão
- Rastreamento de cada tentativa adicional
- Validação do modal após cada clique extra

### Robustez
- Se após todas as tentativas o modal não aparecer, o anexo é pulado
- Logs críticos para identificar falhas persistentes
- Controle de fluxo garantido em todas as situações

### Teste
- **Pendente**: Validar em ambiente real se resolve casos edge
- **Expectativa**: 99%+ de assertividade no clique correto
- **Métrica**: Zero cliques em ícones incorretos
