# INSTRUÇÕES PARA GITHUB COPILOT - PROJETO PJE PYTHON

**Versão:** 2.0 - Otimizada para Claude 4.5/Haiku + GitHub Copilot  
**Data:** 30 de Janeiro de 2026  
**Objetivo:** Máxima precisão, mínimo desperdício, zero alucinação  
**Token Efficiency:** -90% através de INDEX.md + busca direcionada

---

## ⚡ GARANTIA DE LEITURA OBRIGATÓRIA

Este arquivo é automaticamente carregado pelo GitHub Copilot quando localizado em `.github/copilot-instructions.md`.

**Alternativas de reforço:**

1. **Custom Instructions** (GitHub Copilot Chat): Settings → GitHub Copilot → Custom Instructions
2. **Prefixo de prompt**: Iniciar comandos com `[REF: INDEX.md + RULES]` 
3. **Claude Projects**: Incluir INDEX.md + este arquivo no Project Knowledge

---

## 🎯 REGRAS ABSOLUTAS (NUNCA VIOLAR)

### R0: HIERARQUIA DE LEITURA OBRIGATÓRIA

```
FLUXO CORRETO:
1. INDEX.md → Localizar módulo/arquivo alvo (50 tokens)
2. Arquivo específico → Ler apenas seção relevante (300-500 tokens)
3. Dependências → Consultar Fix/ quando necessário (200 tokens)
4. Executar → Apenas o solicitado

TOKEN BUDGET ALVO: 550 tokens/operação (vs 8000+ lendo aleatoriamente)
```

**PROIBIDO:** Ler arquivos inteiros aleatoriamente, buscar sem estratégia, ignorar INDEX.md

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
- ✅ Scripts de teste SIMPLES de execução direta (`py test_X.py`)
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
est_funcao.py - Teste de função isolada
from Fix.utils import validar_cpf

resultado = validar_cpf("12345678901")
print(f"✓ Validação: {resultado}")

# Executar: py test_funcao.py
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

### Comandos de Validação Rápida

```bash
# Validar sintaxe Python
py -m py_compile arquivo.py

# Testar import específico
py -c "from modulo import funcao"

# Executar script de teste simples
py test_script.py

# Verificar módulo
py -m arquivo --help
```

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
- `wrappers_ato.py` (418 linhas) - Wrappers específicos
- `wrappers_utils.py` - Utilitários de wrappers

**SISB/** - Integração com SISBAJUD
- `helpers.py` (3551 linhas) - **MAIOR ARQUIVO** - Bloqueios, validação, relatórios
- `utils.py` (1490 linhas) - Utilitários SISBAJUD
- `processamento.py` (1480 linhas) - Processamento de ordens
- `core.py` (1107 linhas) - Core SISBAJUD

**Prazo/** - Processamento de Prazos em Lote
- `p2b_prazo.py` - `fluxo_prazo()`, processamento de lista
- `p2b_fluxo_helpers.py` (902 linhas) - Helpers do fluxo
- `prov.py` (750 linhas) - Providências
- `loop.py` (1253 linhas) - Loop principal

**PEC/** - Workflow de Petições
- `processamento.py` (1622 linhas) - Processamento de petições
- `regras.py` (1615 linhas) - Regras de negócio
- `carta.py` (990 linhas) - Cartas precatórias
- `anexos/core.py` (1284 linhas) - Processamento de anexos

**Mandado/** - Processamento de Mandados Judiciais
- `processamento.py` (1138 linhas) - Processamento principal
- `utils.py` (690 linhas) - Utilitários (sigilo, lembretes)
- `regras.py` (420 linhas) - `aplicar_regras_argos()`

**Peticao/** - Análise de Petições Iniciais
- `pet_novo.py` (1626 linhas) - Versão mais recente
- `pet2.py` (1690 linhas) - Versão intermediária
- Nota: Consolidação pendente (duplicação ~80%)

### Importações Padrão do Projeto

```python
# Selenium Base (Fix/core.py)
from Fix.core import aguardar_e_clicar, safe_click, wait_for_visible
from Fix.core import preencher_campo, selecionar_opcao
from Fix.core import esperar_elemento, buscar_seletor_robusto
from Fix.core import com_retry

# Utilitários (Fix/utils.py)
from Fix.utils import validar_cpf, formatar_data, limpar_texto

# Atos Judiciais (atos/)
from atos.judicial import ato_judicial, make_ato_wrapper
from atos.movimentos import mov, mov_simples, mov_arquivar
from atos.comunicacao import comunicacao_judicial

# SISBAJUD (SISB/)
from SISB.helpers import extrair_dados_bloqueios_processados
from SISB.helpers import gerar_relatorio_bloqueios_processados
from SISB.helpers import gerar_relatorio_bloqueios_conciso

# Prazos (Prazo/)
from Prazo.p2b_prazo import fluxo_prazo
from Prazo.prov import fluxo_prov

# Mandados (Mandado/)
from Mandado.regras import aplicar_regras_argos
from Mandado.utils import retirar_sigilo, lembrete_bloq
```

### Busca Rápida por Conceito (INDEX.md)

**Operações Selenium:**
- Criar driver: `Fix.core.criar_driver_PC()`
- Clicar elemento: `Fix.core.aguardar_e_clicar()` ⭐ MAIS USADA
- Esperar elemento: `Fix.core.wait()`, `Fix.core.esperar_elemento()`
- Preencher campo: `Fix.core.preencher_campo()`
- Selecionar dropdown: `Fix.core.selecionar_opcao()`

**Atos Judiciais:**
- Criar ato: `atos.judicial.ato_judicial()` ⭐ PRINCIPAL
- Criar movimento: `atos.movimentos.mov()`
- Movimento simples: `atos.movimentos.mov_simples()`
- Gerenciar sigilo: `atos.wrappers_utils.visibilidade_sigilosos()`

**SISBAJUD:**
- Extrair bloqueios: `SISB.helpers.extrair_dados_bloqueios_processados()`
- Relatório completo: `SISB.helpers.gerar_relatorio_bloqueios_processados()`
- Relatório conciso: `SISB.helpers.gerar_relatorio_bloqueios_conciso()`

**Prazos:**
- Processar prazos: `Prazo.p2b_prazo.fluxo_prazo()`
- Providências: `Prazo.prov.fluxo_prov()`

**Mandados:**
- Regras Argos: `Mandado.regras.aplicar_regras_argos()`
- Retirar sigilo: `Mandado.utils.retirar_sigilo()`
- Lembrete bloqueio: `Mandado.utils.lembrete_bloq()`

---

## ✅ CHECKLIST PRÉ-RESPOSTA

Antes de enviar qualquer resposta, verificar:

### Contexto e Busca
```
[ ] Li INDEX.md primeiro para localizar arquivo/função?
[ ] Identifiquei o arquivo correto usando INDEX.md?
[ ] Usei estratégia de busca 3-níveis (para arquivos grandes)?
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
[ ] Usei comando `py` (não `python` ou `python3`)?
[ ] Validei sintaxe se apropriado (py -m py_compile)?
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

## 🔐 VERSÃO CONDENSADA PARA CUSTOM INSTRUCTIONS

Para uso em Custom Instructions do GitHub Copilot (<1500 caracteres):

```
# REGRAS COPILOT - PJE PYTHON

## OBRIGATÓRIO
1. Ler INDEX.md primeiro → localizar arquivo/função (50 tokens)
2. Ler APENAS seção relevante, não arquivo inteiro (500 tokens max)
3. Reutilizar Fix/ antes de criar código novo
4. Fazer SÓ o pedido - zero código extra, zero sugestões
5. ZERO arquivos novos não solicitados

## BUSCA (arquivos >1000 linhas)
Nível 1: termo exato (2x) → Nível 2: variações (2x) → Nível 3: padrão estrutural (1x)
Max 3 tentativas → reportar se falhar

## TESTES
✅ Scripts .py diretos: py test_X.py
✅ Validação: py -m py_compile arquivo.py
✅ Import: py -c "from modulo import funcao"
❌ Frameworks pytest/unittest sem pedido
❌ Selenium/DB/API sem ambiente

## RESPOSTA
Arquivo: {nome}.py linha {N}
{código modificado}
Teste: py -c "from modulo import funcao"

SEM: explicações, sumários, "análise", "sugestões", "próximos passos"
Tamanho: <50 palavras + código

## REFERÊNCIA RÁPIDA
Fix/core.py → aguardar_e_clicar, preencher_campo, selecionar_opcao
atos/judicial.py → ato_judicial
SISB/helpers.py → extrair_dados_bloqueios_processados
INDEX.md → mapa completo projeto

## COMANDO
SEMPRE: py (não python/python3)

## ARQUIVOS CRÍTICOS (>2000 linhas)
SISB/helpers.py (3551) → busca por seção obrigatória
Fix/core.py (2915) → busca por grupo funcional
Fix/extracao.py (2127) → busca estratégica
```

---

## 🎯 COMO USAR ESTAS INSTRUÇÕES

### Setup Inicial (Uma Vez)

```bash
# 1. Criar arquivo de instruções na pasta .github
mkdir -p .github

# 2. Copiar este arquivo para .github/copilot-instructions.md
cp copilot-instructions.md .github/copilot-instructions.md

# 3. Garantir que INDEX.md está na raiz do projeto
ls INDEX.md  # deve existir

# 4. Commitar ambos arquivos
git add .github/copilot-instructions.md INDEX.md
git commit -m "feat: Add GitHub Copilot instructions + project index"
git push
```

### Verificação

```bash
# Verificar estrutura
project/
├── .github/
│   └── copilot-instructions.md  ← Este arquivo
├── INDEX.md                      ← Índice do projeto
├── Fix/
├── atos/
├── SISB/
└── ...
```

### Uso Diário com GitHub Copilot

```
# GitHub Copilot lerá automaticamente .github/copilot-instructions.md

# Para reforçar:
Prompt: [REF: INDEX.md] adicionar validação em processar_pec

# Ou simplesmente:
Prompt: adicionar validação em processar_pec
```

### Uso com Claude (Projects/API)

```
1. Claude Projects:
   - Project Knowledge → Upload INDEX.md + copilot-instructions.md
   - System Prompt → "Seguir regras em copilot-instructions.md"

2. Claude API:
   - Incluir ambos arquivos no contexto inicial
   - Referenciar no system prompt
```

---

## 📄 METADADOS

**Arquivo:** `.github/copilot-instructions.md`  
**Versão:** 2.0  
**Data Criação:** 30 de Janeiro de 2026  
**Última Atualização:** 30 de Janeiro de 2026  
**Mantido por:** Equipe de Desenvolvimento  
**Modelo Alvo:** GitHub Copilot, Claude 4.5 Sonnet, Claude Haiku  
**Token Efficiency:** -90% através de INDEX.md + busca direcionada

---

**FIM DO DOCUMENTO**
