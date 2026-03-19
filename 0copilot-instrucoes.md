# INSTRUÇÕES PARA GITHUB COPILOT - PROJETO PJE PYTHON

## REGRAS ABSOLUTAS (NUNCA VIOLAR)

1. **FAZER APENAS O SOLICITADO** - Nada mais, nada menos
2. **ZERO ARQUIVOS NOVOS** - Nunca criar arquivos não pedidos (testes, logs, relatórios)
3. **REUTILIZAR CÓDIGO EXISTENTE** - Sempre usar funções de Fix.py, pec.py, atos.py, carta.py, sisb.py
4. **RESPOSTAS DIRETAS** - Sem explicações técnicas, diagnósticos ou sugestões posteriores
5. **SEM SUMÁRIOS/RELATÓRIOS** - Nunca incluir resumo, análise ou conclusão ao final

---

## TESTES E VALIDAÇÃO

### PODE E DEVE fazer testes quando apropriado:
- ✅ Criar scripts `.py` de teste de **execução direta no terminal**
- ✅ Testes de funções específicas **sem dependências de driver/ambiente real**
- ✅ Validação de sintaxe com `py -m py_compile arquivo.py`
- ✅ Testes rápidos de imports: `py -c "from modulo import funcao"`
- ✅ Verificação de lógica isolada (cálculos, formatações, validações)

### NÃO fazer:
- ❌ Testes que requerem Selenium/WebDriver
- ❌ Testes que requerem banco de dados ou APIs externas
- ❌ Testes complexos com mocks/fixtures não solicitados
- ❌ Frameworks de teste (pytest, unittest) sem solicitação explícita

### Comando Correto para Python:
**SEMPRE usar `py` (não `python`):**
```bash
# ✅ CORRETO
py script.py
py -c "print('teste')"
py -m py_compile arquivo.py

# ❌ ERRADO
python script.py
python3 script.py
```

### Exemplo de Teste Válido:
```python
# test_validacao.py
from Fix import validar_cpf

# Teste direto - execução simples
cpf_valido = validar_cpf("12345678901")
print(f"CPF válido: {cpf_valido}")

# Executar: py test_validacao.py
```

---

## EFICIÊNCIA DE BUSCA (ARQUIVOS GRANDES)

### Estratégia de Busca em 3 Níveis

**Nível 1**: Buscar termo exato da solicitação
**Nível 2**: Se falhar 2x, buscar termos relacionados ou sinônimos
**Nível 3**: Se falhar novamente, buscar por padrão de código (import, def, class)

### Exemplo Prático
```
Pedido: "encontrar função processar_pec"

Tentativa 1: buscar "processar_pec"
Tentativa 2: buscar "pec" + "def"
Tentativa 3: buscar "executar" ou "iniciar" + "pec"

❌ NUNCA: ler linhas aleatórias ou mudar termo sem estratégia
```

### Quando Arquivos São Grandes (>200KB)
- Usar busca por seção: `import`, `class`, `def funcao_alvo`
- Buscar em múltiplas variações ANTES de desistir
- Exemplo: `def processar` → `def process` → `class Processador` → `executar`

---

## CONTEXTO DO PROJETO

### Arquivos Principais (SEMPRE consultar antes de criar código novo)
- **Fix.py** - Utilitários Selenium (safeclick, safenav, wait, etc)
- **pec.py** - Lógica PEC + SISBAJUD
- **atos.py** - Ações processuais (comunicacao_judicial, movimentacoes)
- **sisb.py** - Integração SISBAJUD
- **carta.py** - Cartas precatórias
- **p2b.py** - Processamento prazo
- **m1.py** - Mandados

### Importações Padrão
```python
from Fix import safeclick, safenav, wait_el, get_el, extracao_dados
# SEMPRE verificar Fix.py antes de criar função similar
```

---

## WORKFLOW CORRETO

### 1. Receber Pedido
- Ler pedido completo
- Identificar arquivo(s) alvo
- Verificar se função já existe em Fix.py ou outros

### 2. Buscar Contexto
- Buscar termos relevantes NO arquivo correto
- Se arquivo >200KB: buscar por seções (imports, classes, funções)
- Máximo 3 tentativas de busca com estratégias diferentes

### 3. Implementar
- Usar código existente sempre que possível
- Fazer APENAS o solicitado
- Testar funcionalidade básica quando apropriado (scripts .py diretos)

### 4. Responder
- Mostrar código modificado
- Informar arquivo(s) alterado(s)
- Se criou teste: mostrar comando `py test_X.py`
- **PARAR AQUI** - Sem sumários, sugestões ou análises

---

## O QUE NUNCA FAZER

❌ Criar frameworks de teste não solicitados
❌ Criar arquivo de log ou relatório
❌ Sugerir "melhorias" não solicitadas
❌ Explicar cada linha de código
❌ Incluir "Próximos passos" ou "Recomendações"
❌ Fazer diagnóstico técnico detalhado
❌ Iterar sem validação do usuário
❌ Focar em perfeição antes de funcionalidade
❌ Perder contexto (sempre reler resumo se necessário)
❌ Usar MCP Server para testes (usar terminal simples)

---

## EXEMPLOS DE BOA EXECUÇÃO

### ❌ ERRADO (Verbose, cria arquivos desnecessários, explica demais)
```
Analisando o código fornecido, identifiquei que a função processar_pec 
precisa de validação adicional. Criei um arquivo test_pec.py para validar...

Relatório de Implementação:
- Função modificada: processar_pec() linha 145
- Testes criados: 3 casos
- Sugestões: considerar adicionar...
```

### ✅ CORRETO (Direto, faz só o pedido, teste simples se relevante)
```python
# pec.py linha 145
def processar_pec(driver, processo):
    validar_processo(processo)  # Validação adicionada
    return executar_acao(driver, processo)

# test_validacao.py (teste simples de sintaxe)
from pec import processar_pec
print("Import OK")
# Executar: py test_validacao.py
```

---

## VALIDAÇÃO RÁPIDA

### Comandos Úteis (SEMPRE usar `py`):
```bash
# Validar sintaxe
py -m py_compile arquivo.py

# Testar import
py -c "from arquivo import funcao"

# Executar script de teste
py test_script.py

# Verificar módulo
py -m arquivo --help
```

---

## FORMATO DE RESPOSTA IDEAL

```markdown
# Arquivo modificado: <nome_arquivo.py>

<```python>
# Código modificado aqui
<```>

# Teste (se relevante):
py test_validacao.py

<!-- FIM - Sem texto adicional -->
```

**Tamanho ideal da resposta:** 5-15 linhas de texto + código modificado + comando de teste (se aplicável)

---

## CHECKLIST ANTES DE RESPONDER

- [ ] Fiz APENAS o solicitado?
- [ ] Reutilizei código de Fix.py/outros quando possível?
- [ ] Busquei no arquivo correto (e usei 3 estratégias se grande)?
- [ ] Criei ZERO arquivos não pedidos?
- [ ] Se criei teste: é execução direta (sem driver/DB/API)?
- [ ] Usei comando `py` (não `python`)?
- [ ] Minha resposta tem <50 palavras de texto + código?
- [ ] Excluí sumário/relatório/sugestões do final?

**Se todos ✅ → enviar resposta**
**Se algum ❌ → revisar antes de enviar**

---

## LEMBRE-SE

**Usuário é leigo** - Sem jargão técnico
**Recursos limitados** - Economia é prioridade
**Arquivos grandes** - Busca estratégica é essencial
**Contexto importa** - Sempre verificar código existente primeiro
**Ação > Palavras** - Código funcional > Explicações longas
**Testes simples** - Scripts `.py` diretos > Frameworks complexos
**Comando correto** - `py` > `python`

---

**VERSÃO:** 1.1 - Otimizada para GitHub Copilot com Claude/GPT-4
**ATUALIZAÇÃO:** Incluído suporte para testes simples e validação
**OBJETIVO:** Máxima eficiência, mínimo desperdício, zero alucinação
