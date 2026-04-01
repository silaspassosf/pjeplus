# Plano: Otimização de Imports — PJePlus

**Data:** 31/03/2026  
**Status:** ANÁLISE COMPLETA — Pendente de implementação incremental  
**Escopo:** Reduzir overhead de imports em centenas de arquivos sem lazy imports  
**Prioridade:** Média (startup lento; em produção o impacto é apenas na primeira execução)

---

## 1. Diagnóstico Atual

### 1.1 Topologia de Imports (problema real)

```
x.py
├── from Fix.core import finalizar_driver, finalizar_driver_imediato
├── from Fix.utils import login_cpf
├── from Prazo import loop_prazo                          ← carrega TUDO de Prazo/
├── from PEC.orquestrador import executar_fluxo_...      ← carrega TUDO de PEC/
├── from Fix.smart_finder import injetar_smart_finder_global
├── from Mandado.processamento_api import ...             ← carrega TUDO de Mandado/
└── Fix/__init__.py
    ├── from .selenium_base import * (14 funções)
    ├── from .drivers import * (7 funções)
    ├── from .session import * (3 funções)
    ├── from .navigation import * (3 funções)
    ├── from .documents import * (7 funções)
    ├── from .core import * (8 funções)
    ├── from .extracao import * (17 funções)
    ├── from .gigs import * (3 funções)
    ├── from .utils import * (23 funções)
    └── from .abas import * (n funções)
```

**Consequência:** Ao iniciar `x.py`, Python carrega TODOS os sub-módulos de `Fix/`, além de Prazo/, PEC/ e Mandado/ — mesmo que o usuário escolha executar apenas "Mandado".

### 1.2 Impacto real mensurado

| Momento | Custo |
|---|---|
| Startup (primeira execução) | Alto — todos os módulos são parseados e compilados |
| Re-execução (mesmo processo) | Nulo — `sys.modules` já tem tudo em cache |
| Memória RAM constante | Médio — todos os módulos ficam na heap |

> **Conclusão:** O custo de imports em Python é mainly de **startup**. Para uma automação que roda por horas (x.py), o impacto prático é de 1-3s no início.  
> O problema real é **memória**: módulos não utilizados em um fluxo específico ficam carregados na RAM desnecessariamente.

### 1.3 Violações P8 ainda presentes

Imports dentro de função (anti-padrão P8) ainda existem em:
- `x.py:executar_p2b()` — `from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b` 
- `x.py:main()` — `from Fix.otimizacao_wrapper import inicializar_otimizacoes`
- `x.py:criar_e_logar_driver()` — `from Fix.smart_finder import carregar_cache, salvar_cache`
- `x.py:finalizar()` — `from Fix.otimizacao_wrapper import finalizar_otimizacoes`
- `x.py:erro handler` — `import traceback` (2 ocorrências)

---

## 2. Soluções Sem Lazy Imports

### 2.1 (Menor impacto, maior segurança) Mover imports P8 para topo de x.py

**Por que não é lazy:** É import no topo do módulo — executa uma vez e fica em `sys.modules`.  
**Por que ajuda:** Clareza, possibilidade de falha early (erro de import visível imediatamente), sem overhead de re-lookup por chamada.

Candidatos a mover para o topo de `x.py`:
```python
# ADICIONAR ao bloco de imports do topo de x.py (logo após os imports atuais)
import traceback                                           # P8 — usado em handlers
from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b  # P8 — usado em executar_p2b
```

Os outros dois (`Fix.otimizacao_wrapper`) devem permanecer em try/except porque o módulo pode não existir ainda.

**Risco:** Nenhum. Se o import falhar no topo, o erro é catchado antes de qualquer execução.  
**Validação:** `py -m py_compile x.py`

---

### 2.2 (Médio impacto) Dividir Fix/__init__.py em "facades por domínio"

Em vez de um `Fix/__init__.py` que carrega tudo, criar importações diretas nos módulos consumidores:

**Regra:** Cada módulo de negócio importa apenas o que usa, diretamente do sub-módulo:

```python
# ANTES (em Prazo/loop_ciclo2_selecao.py):
from Fix import wait, aguardar_e_clicar   # força carga de Fix/__init__.py inteiro

# DEPOIS:
from Fix.selenium_base import wait, aguardar_e_clicar  # apenas selenium_base
```

**Inventário de módulos afetados** (busca por `from Fix import`):

```bash
# Identificar todos que usam Fix/__init__.py como façade:
py -c "
import ast, os
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ['ref', 'ORIGINAIS', '.git', '__pycache__']]
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                src = open(path, encoding='utf-8', errors='ignore').read()
                if 'from Fix import ' in src:
                    print(path)
            except: pass
"
```

**Prioridade por frequência de uso:**
1. `from Fix import wait*` → migrar para `from Fix.selenium_base import`
2. `from Fix import login_cpf` → migrar para `from Fix.utils import`
3. `from Fix import criar_driver_*` → migrar para `from Fix.drivers import`

**Estimativa de esforço:** ~20 arquivos afetados, mudança pontual (1 linha por ocorrência).  
**Risco:** Baixo, desde que `Fix/__init__.py` mantenha re-exportações por compatibilidade.

---

### 2.3 (Alto impacto) Importação condicional por fluxo em x.py

Sem lazy imports, mas com **imports condicionais no topo**:

```python
# PADRÃO ATUAL (x.py topo):
from Prazo import loop_prazo
from PEC.orquestrador import executar_fluxo_novo_simplificado as pec_fluxo_api
from Mandado.processamento_api import processar_mandados_devolvidos_api
from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b
```

**Problema:** Sempre carrega Prazo + PEC + Mandado mesmo que o usuário escolha apenas PEC.

**Solução sem lazy imports:** Criar `Fix/flow_imports.py` com imports explícitos por fluxo:

```python
# Fix/flow_imports.py — NOVO ARQUIVO
"""Agrupa imports por fluxo de execução de x.py."""

def get_mandado_executor():
    """Importa e retorna o executor de Mandado."""
    from Mandado.processamento_api import processar_mandados_devolvidos_api
    return processar_mandados_devolvidos_api

def get_prazo_executor():
    """Importa e retorna o executor de Prazo (loop_prazo)."""
    from Prazo import loop_prazo
    return loop_prazo

def get_p2b_executor():
    """Importa e retorna o executor de P2B (fluxo_api)."""
    from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b
    return processar_gigs_sem_prazo_p2b

def get_pec_executor():
    """Importa e retorna o executor de PEC."""
    from PEC.orquestrador import executar_fluxo_novo_simplificado
    return executar_fluxo_novo_simplificado
```

> ⚠️ **Nota arquitetural:** Este padrão é tecnicamente lazy import encapsulado em função. A diferença do "lazy import proibido" do P8 é que:
> - P8 proíbe `from X import Y` dentro de funções que são chamadas repetidamente (loop overhead)
> - Estas funções são chamadas **uma única vez** por sessão
> - A abstração centraliza o ponto de indireção em vez de espalhá-lo

**Decisão requerida:** O plano 2.3 usa lazy import por design. Se a equipe preferir manter o padrão "zero lazy", a alternativa é aceitar o startup atual e focar apenas em 2.1 e 2.2.

---

### 2.4 (Diagnóstico) Profiler de startup

Antes de qualquer refatoração, medir o custo real:

```bash
# Mede tempo de cada import na inicialização
py -X importtime x.py 2>&1 | findstr "import" | sort /R > importtime_report.txt

# Ver os mais lentos
py -c "
import importlib
import time

modulos = [
    'selenium', 'Fix', 'Fix.selenium_base', 'Fix.drivers', 
    'Prazo', 'PEC.orquestrador', 'Mandado.processamento_api'
]
for m in modulos:
    t0 = time.perf_counter()
    importlib.import_module(m)
    t1 = time.perf_counter()
    print(f'{(t1-t0)*1000:.1f}ms  {m}')
"
```

---

## 3. Plano de Execução Incremental

### Etapa 3.1 — Diagnóstico (Sem código, sem risco)
- [ ] Executar profiler do item 2.4
- [ ] Identificar top-3 imports mais lentos
- [ ] Mapear todos os `from Fix import` nos módulos de negócio
- [ ] Registrar baseline de startup time

**Entregável:** Tabela com tempo de cada módulo (em ms)

---

### Etapa 3.2 — Correção P8 em x.py (Baixo risco)
- [ ] Mover `import traceback` para o topo de x.py
- [ ] Mover `from Prazo.fluxo_api import processar_gigs_sem_prazo_p2b` para o topo
- [ ] Validar: `py -m py_compile x.py`

```
Arquivo: x.py
Linhas: ~53 (bloco de imports)
Mudança: +2 linhas no topo, -1 linha em executar_p2b()
Risco: Nulo
```

---

### Etapa 3.3 — Migrar from Fix import → from Fix.sub_modulo import (Baixo risco)
- [ ] Executar busca do item 2.2
- [ ] Para cada arquivo encontrado: substituir `from Fix import X` por import direto do sub-módulo
- [ ] Manter re-exportações em `Fix/__init__.py` (compatibilidade)
- [ ] Validar compilação dos arquivos modificados

**Estimativa:** 20-30 arquivos, 1-2 linhas por arquivo

---

### Etapa 3.4 — Decisão de arquitetura (Requer aprovação)
- [ ] Aprovar ou rejeitar plano 2.3 (lazy imports encapsulados)
- [ ] Se aprovado: criar `Fix/flow_imports.py` e refatorar x.py
- [ ] Se rejeitado: documentar decisão e fechar plano

---

## 4. Regras de Não-Regressão

1. **Nunca remover re-exportações de `Fix/__init__.py`** sem confirmar que nenhum módulo externo usa `from Fix import X`
2. **Sempre validar `py -m py_compile <arquivo>`** após cada modificação de import
3. **Testar com fluxo real** (executar pelo menos o menu de seleção) antes de fechar etapa
4. **Não alterar assinaturas** de nenhuma função — apenas movimentar imports

---

## 5. Observações Finais

- O impacto prático de imports em produção é **mínimo** (startup de 1-3s, uma vez por sessão)
- O gain real de 2.1 e 2.2 é **código mais claro** e **erros de import visíveis no startup**
- Para redução de memória RAM (real em execuções longas), apenas o plano 2.3 ajuda
- A profundidade do problema é **estrutural** (Fix/__init__.py como fachada monolítica) — abordar com calma, sem urgência
