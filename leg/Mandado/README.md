## Mandado - Módulo Modularizado

### Estrutura

```
Mandado/
├── __init__.py         - Re-exporta tudo dos submódulos
├── core.py             - Setup, navegação, login e main (~600 linhas)
├── processamento.py    - processar_argos, fluxo_mandados_outros (~800 linhas)
├── regras.py           - aplicar_regras_argos com Strategy Pattern (~400 linhas)
└── utils.py            - Funções utilitárias: lembrete, sigilo, intimação (~400 linhas)
```

### Submódulos

#### **core.py** (Setup, Navegação, Main)
- `setup_driver()` - Inicializa Selenium WebDriver
- `navegacao(driver)` - Navega para tela de mandados devolvidos
- `iniciar_fluxo_robusto(driver)` - Fluxo com recuperação de sessão centralizada
- `iniciar_fluxo(driver)` - Fluxo principal com callback
- `main()` - Ponto de entrada

#### **processamento.py** (Fluxos Argos e Outros)
- `processar_argos(driver, log=False)` - Orquestra fluxo ARGOS com **LOOP DE ITERAÇÃO** para múltiplos documentos
  - **✅ NOVO**: Itera até encontrar documento com regra aplicável
  - **✅ NOVO**: Executa ação correspondente uma única vez
  - **✅ NOVO**: Max 5 tentativas antes de abortar
- `fluxo_mandados_outros(driver, log=True)` - Processa mandados de oficial de justiça
- `ultimo_mdd(driver, log=True)` - Processa último mandado
- `fluxo_mandado(driver)` - Callback de fluxo
- Funções auxiliares para extração e processamento

#### **regras.py** (Strategy Pattern)
- `aplicar_regras_argos()` - Orquestra com Strategy Pattern
- `ESTRATEGIAS_REGRAS` - Dict de estratégias
- 6+ funções de handlers (`_avaliar_regra_*()`)

#### **utils.py** (Utilitários)
- `lembrete_bloq(driver, debug=False)` - Wrapper para criar_lembrete_posit
- `retirar_sigilo()` - Remove sigilo de documentos
  - **✅ CORRIGIDO**: Lógica de verificação de aria-label e ícones
  - **✅ CORRIGIDO**: Agora realmente clica quando há sigilo ativo
- `retirar_sigilo_certidao_devolucao_primeiro()` - ETAPA 1 Argos
- `retirar_sigilo_demais_documentos_especificos()` - ETAPA 3 Argos
- `retirar_sigilo_documentos_especificos()` - Variante
- `fechar_intimacao(driver, log=True)` - Fecha intimação

### Uso

```python
# Novo uso (recomendado):
from Mandado import main, processar_argos, fluxo_mandados_outros

if __name__ == "__main__":
    main()

# Ou imports específicos:
from Mandado.core import setup_driver, navegacao
from Mandado.processamento import processar_argos
from Mandado.regras import aplicar_regras_argos
from Mandado.utils import lembrete_bloq, fechar_intimacao
```

### Status de Migração

✅ **Completo:**
- [x] Pasta Mandado/ criada
- [x] __init__.py com re-exports
- [x] 4 módulos criados (core, processamento, regras, utils)
- [x] Imports organizados
- [x] Type hints em funções críticas
- [x] Docstrings Google Style
- [x] **NOVO**: Correção de `retirar_sigilo()` - lógica de verificação
- [x] **NOVO**: Implementação de loop iterativo em `processar_argos()`

⏳ **Pendente:**
- [ ] m1.py será marcado como OBSOLETO
- [ ] Código externo deverá usar `from Mandado import`
- [ ] Limpeza de funções deprecated

### Tamanho Estimado (pós-refatoração)

| Arquivo | Linhas | Tamanho |
|---------|--------|--------|
| core.py | ~600 | 23 KB |
| processamento.py | ~800 | 31 KB |
| regras.py | ~400 | 15 KB |
| utils.py | ~400 | 15 KB |
| **TOTAL** | **~2.200** | **~84 KB** |

### Comparação

| Métrica | Antes | Depois |
|---------|-------|--------|
| Linhas | 3.230 | 2.200 (-32%) |
| Funções | 28 | 28 (mesmas) |
| Type Hints | Parcial | 100% críticas |
| Organização | Monolítico | Modularizado |

### Migração para Novo Código

Se você tem código que importava de m1.py:

```python
# ❌ ANTIGO (m1.py):
from m1 import main, processar_argos

# ✅ NOVO (Mandado):
from Mandado import main, processar_argos
```

Ambos funcionarão no período de transição (m1.py pode re-exportar de Mandado), mas o novo uso é recomendado.

### Próximas Etapas

1. Validar imports de Mandado em ambiente Python
2. Testar execução de Mandado.main()
3. Marcar m1.py como obsoleto
4. Remover m1.py da árvore de código
