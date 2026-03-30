# Controle de Refatoração: Próxima Fase (reta3)

## 1. Diagnóstico dos Próximos Problemas

### P1: Wrappers de uma linha
- **Onde:** Fix/core.py (~40 funções), Fix/variaveis.py (~12 funções)
- **Problema:** Indireção vazia, dificulta rastreamento e debug.

### P2: Funções com 5+ níveis de indentação
- **Onde:** Fix/abas.py, atos/wrappers_utils.py, x.py
- **Problema:** Viola PEP8, dificulta manutenção e testes.

### P3: except Exception retornando False
- **Onde:** atos/wrappers_mov.py, atos/comunicacao.py
- **Problema:** Silencia erros, dificulta diagnóstico.

### P4: time.sleep(N) hardcoded
- **Onde:** atos/wrappers_mov.py, atos/wrappers_utils.py
- **Problema:** Race conditions, lentidão.

### P5: JS longo embutido em f-string
- **Onde:** SISB/, PEC/
- **Problema:** Inlegível, sem syntax highlight.

### P6: dict solto como retorno/entrada
- **Onde:** atos/comunicacao.py, x.py
- **Problema:** Sem tipagem, acesso por string.

### P7: Driver criado/destruído sem context manager
- **Onde:** x.py, orquestradores
- **Problema:** Driver pode vazar em exceção.

### P8: Import lazy dentro de função
- **Onde:** Fix/core.py (cada wrapper)
- **Problema:** Overhead de import lookup.

---

## 2. Etapas Incrementais Sugeridas

### 2.1 Eliminar wrappers de uma linha (P1, P8)
- Substituir wrappers por importações diretas no topo do módulo.
- Aplicar em Fix/core.py (**CONCLUÍDO**), Fix/variaveis.py (**CONCLUÍDO**).
- Testar re-exportação em Fix/__init__.py.
- **Status:** Pendente

### 2.2 Limitar indentação máxima (P2)
- Extrair blocos internos para funções auxiliares privadas.
- Aplicar em Fix/abas.py, atos/wrappers_utils.py, x.py.
- **Status:** Fix/abas.py já refatorado na fase anterior (CONCLUÍDO)

### 2.3 Remover time.sleep hardcoded (P4)
- Substituir por aguardar_renderizacao_nativa.
- Aplicar em atos/wrappers_mov.py, atos/wrappers_utils.py.
- **Status:** CONCLUÍDO

### 2.4 Extrair JS longo para scripts (P5)
- Mover JS de 80+ linhas para arquivos .js em scripts/.
- Aplicar em SISB/, PEC/.
- **Status:** CONCLUÍDO

### 2.5 Substituir dict solto por dataclass (P6)
- Aplicar modelo de SISB/standards.py.
- Aplicar em atos/comunicacao.py, x.py.
- **Status:** Pendente

### 2.6 Usar context manager para driver (P7)
- Aplicar driver_session do Fix/drivers/lifecycle.py.
- Aplicar em x.py, orquestradores.
- **Status:** Pendente

---

## 3. Progresso Atual
- Exceções tipadas implementadas e aplicadas (primeira fase: CONCLUÍDO)
- Fix/abas.py já refatorado para 3 níveis de indentação (CONCLUÍDO)
- Demais etapas pendentes para próxima fase

---

**Atualize este arquivo a cada etapa concluída para controle incremental.**
