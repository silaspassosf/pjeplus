# INSTRUÇÕES PARA GEMINI CODE ASSIST - PROJETO PJE PYTHON

**Versão:** 2.0 - Otimizada para Gemini Code Assist
**Data:** 14 de Fevereiro de 2026
**Objetivo:** Máxima precisão, mínimo desperdício, zero alucinação
**Token Efficiency:** -90% através de INDEX.md + busca direcionada

---

## ⚡ REGRAS ABSOLUTAS (NUNCA VIOLAR)

### R0: HIERARQUIA DE LEITURA OBRIGATÓRIA

FLUXO CORRETO:
1. INDEX.md → Localizar módulo/arquivo alvo (50 tokens)
2. Arquivo específico → Ler apenas seção relevante (300-500 tokens)
3. Dependências → Consultar Fix/ quando necessário (200 tokens)
4. Executar → Apenas o solicitado

TOKEN BUDGET ALVO: 550 tokens/operação (vs 8000+ lendo aleatoriamente)

**PROIBIDO:** Ler arquivos inteiros aleatoriamente, buscar sem estratégia, ignorar INDEX.md

### R0.1: REF E INDEX DA RAIZ

- NUNCA editar nada na pasta `ref` (legada).
- Sempre ler `INDEX.md` na raiz do projeto (xx).
- Quando necessário usar `ref` para comparar funções, procurar no legado até identificar o trecho exato. É garantido que o trecho existe no legado, então não pode desistir da busca.
- Não copiar funções de `ref` para o projeto refatorado; ajustar apenas as funções prontas do projeto refatorado usando o INDEX.md como guia.
- O INDEX.md é o mapa do projeto refatorado; `ref` é apenas backup do código legado.

### R1: ESCOPO EXATO - FAZER APENAS O SOLICITADO

- ✅ Implementar exatamente o que foi pedido
- ✅ Usar código existente sempre que possível
- ❌ NÃO adicionar validações não solicitadas
- ❌ NÃO criar abstrações "para facilitar no futuro"
- ❌ NÃO sugerir melhorias não pedidas
- ❌ NÃO modificar assinaturas de função sem permissão

### R2: ZERO ARQUIVOS NOVOS (exceto quando explicitamente solicitado)

**Proibido criar sem solicitação:**
- ❌ Frameworks de teste complexos (pytest, unittest)
- ❌ Arquivos de configuração (.json, .yaml, .ini)
- ❌ Diretórios de logs ou relatórios
- ❌ Arquivos de documentação não pedidos

**Permitido quando útil:**
- ✅ Scripts de teste SIMPLES de execução direta (`python test_X.py`)
- ✅ Validação de sintaxe/import
- ✅ Arquivos explicitamente solicitados pelo usuário

### R3: REUTILIZAÇÃO MANDATÓRIA

**SEMPRE consultar estes arquivos ANTES de criar função similar:**

- `Fix/core.py` - Operações Selenium (aguardar_e_clicar, safe_click, wait, preencher_campo)
- `Fix/utils.py` - Utilitários gerais
- `Fix/extracao.py` - Extração de dados
- `atos/judicial.py` - Atos judiciais (ato_judicial, make_ato_wrapper)
- `atos/movimentos.py` - Movimentos processuais (mov, mov_simples)
- `atos/comunicacao.py` - Comunicações judiciais

**Processo:**
1. Verificar INDEX.md se função similar existe
2. Se existir: reutilizar e adaptar
3. Se não existir: criar apenas se necessário

### R4: RESPOSTAS TÉCNICAS DIRETAS

**Formato ideal:**
```python
# test_funcao.py - Teste de função isolada
from Fix.utils import validar_cpf

resultado = validar_cpf("12345678901")
print(f"✓ Validação: {resultado}")

# Executar: python test_funcao.py
```

**Características dos testes permitidos:**
- ✅ Execução direta no terminal
- ✅ Sem dependências de driver/ambiente real
- ✅ Validação de sintaxe e imports
- ✅ Testes de lógica isolada (cálculos, formatações)
- ✅ Verificação rápida (<5 segundos)

### Testes Proibidos (sem solicitação explícita)

- ❌ Testes que requerem Selenium/WebDriver
- ❌ Testes que requerem banco de dados
- ❌ Testes que requerem APIs externas
- ❌ Frameworks complexos (pytest, unittest, mocks, fixtures)
- ❌ Testes de integração sem ambiente configurado

---

## 📁 CONTEXTO DO PROJETO (Referência INDEX.md)

### Estrutura de Módulos

**Fix/** - Core Selenium e Utilitários PJe
- `core.py` (2915 linhas) - Operações Selenium base, retry, wait, click
- `extracao.py` (2127 linhas) - Extração de dados de processos
- `utils.py` (2013 linhas) - Utilitários gerais
- `variaveis.py` (897 linhas) - Variáveis e constantes globais

**atos/** - Atos Judiciais e Movimentos Processuais
- `judicial.py` (1695 linhas) - `ato_judicial()`, `make_ato_wrapper()`
- `comunicacao.py` (1386 linhas) - Comunicações judiciais
- `movimentos.py` (1092 linhas) - `mov()`, `mov_simples()`, `mov_arquivar()`

**SISB/** - Integração com SISBAJUD
- `helpers.py` (3551 linhas) - **MAIOR ARQUIVO** - Bloqueios, validação, relatórios

**Prazo/** - Processamento de Prazos em Lote
- `p2b_prazo.py` - `fluxo_prazo()`, processamento de lista

**PEC/** - Workflow de Petições
- `processamento.py` (1622 linhas) - Processamento de petições
- `regras.py` (1615 linhas) - Regras de negócio

**Mandado/** - Processamento de Mandados Judiciais
- `processamento.py` (1138 linhas) - Processamento principal

---

## ✅ CHECKLIST PRÉ-RESPOSTA

Antes de enviar qualquer resposta, verificar:

### Contexto e Busca
```
[ ] Li INDEX.md primeiro para localizar arquivo/função?
[ ] Identifiquei o arquivo correto usando INDEX.md?
[ ] Li apenas a seção relevante (não arquivo inteiro)?
```

### Implementação
```
[ ] Verifiquei se função similar existe em Fix/ antes de criar?
[ ] Reutilizei código existente sempre que possível?
[ ] Fiz APENAS o que foi solicitado (zero código extra)?
[ ] Criei ZERO arquivos não pedidos?
[ ] Não modifiquei funções não relacionadas?
```

### Testes
```
[ ] Se criei teste: é execução direta sem driver/DB/API?
[ ] Usei comando `python` (ou `py`)?
[ ] Validei sintaxe se apropriado (python -m py_compile)?
```

### Resposta
```
[ ] Minha resposta tem <50 palavras de texto + código?
[ ] Removi explicações linha-por-linha?
[ ] Excluí sumário/relatório/sugestões do final?
[ ] Formato está técnico e direto?
[ ] Incluí apenas arquivo modificado + comando teste?
```

**Resultado:**
- **Todos ✅** → Enviar resposta
- **Algum ❌** → Revisar antes de enviar

---

**FIM DO DOCUMENTO**
