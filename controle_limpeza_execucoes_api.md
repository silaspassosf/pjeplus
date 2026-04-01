# Controle de Limpeza — Execuções API vs DOM (x.py)
> Gerado: 31/03/2026  
> Escopo: x.py + PEC/Mandado/P2B  
> Contexto: PEC, Mandado e P2B agora têm execuções iniciadas por chamada de API.  
> A navegação inicial DOM e o processamento por lista de processos nesses três fluxos devem ser removidos.

---

## ESTADO ATUAL DE x.py (O QUE ESTÁ ERRADO HOJE)

| Fluxo | Opção Menu | Execução atual | Deveria usar |
|---|---|---|---|
| Mandado (B) | B | `mandado_navegacao` + `mandado_fluxo` (DOM) | `processar_mandados_devolvidos_api` |
| PEC (E) | E | `pec_fluxo` = `executar_fluxo_novo` DOM | `executar_fluxo_novo_simplificado` |
| PEC modular (F) | F | `executar_fluxo_novo_simplificado` ✅ | — já correto, mas duplicado com E |
| P2B (D) | D | `processar_gigs_sem_prazo_p2b` ✅ | — já correto |
| Mandado API (G) | G | `processar_mandados_devolvidos_api` ✅ | — correto, mas duplicado com B |
| Prazo (C) | C | `loop_prazo` DOM | **MANTER** — Prazo ainda é DOM |

---

## PROGRESSO

| Item | Descrição | Status |
|---|---|---|
| 1 | Mandado: remover DOM, unificar B=G | ✅ CONCLUÍDO |
| 2 | PEC: remover DOM, unificar E=F | ✅ CONCLUÍDO |
| 3 | x.py: remover imports mortos | ✅ CONCLUÍDO |
| 4 | x.py: limpar menu (remover opções F e G) | ✅ CONCLUÍDO |
| 5 | Validar compilação + teste manual | ✅ CONCLUÍDO |

---

## ITEM 1 — Mandado: substituir DOM por API

### O que muda em x.py

**REMOVER** (linha 81):
```python
from Mandado.core import navegacao as mandado_navegacao, iniciar_fluxo_robusto as mandado_fluxo
```

**MANTER** (linha 85):
```python
from Mandado.processamento_api import processar_mandados_devolvidos_api
```

**SUBSTITUIR** função `executar_mandado()`:
```python
# ANTES
def executar_mandado(driver) -> Dict[str, Any]:
    if not mandado_navegacao(driver):
        return {"sucesso": False, "status": "ERRO_NAVEGACAO", ...}
    resultado = mandado_fluxo(driver)
    ...

# DEPOIS
def executar_mandado(driver) -> Dict[str, Any]:
    """Mandado Isolado — API (sem navegação DOM inicial)"""
    print("\n" + "=" * 80)
    print(" MANDADO ISOLADO")
    print("=" * 80)
    inicio = datetime.now()
    try:
        resultado = processar_mandados_devolvidos_api(driver)
        resultado = normalizar_resultado(resultado)
        tempo = (datetime.now() - inicio).total_seconds()
        resultado['tempo'] = tempo
        if resultado.get("sucesso"):
            print(f"[MANDADO]  Concluído")
        else:
            print(f"[MANDADO]  Falha: {resultado.get('erro', 'Desconhecido')}")
        return resultado
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[MANDADO]  Exceção: {e}")
        return {"sucesso": False, "status": "ERRO_EXECUCAO", "erro": str(e), "tempo": tempo}
```

**Status:** ✅ CONCLUÍDO

---

## ITEM 2 — PEC: substituir DOM por API modular

### O que muda em x.py

**REMOVER** (linha 83):
```python
from PEC.processamento import executar_fluxo_novo as pec_fluxo
```

**ADICIONAR** (junto aos imports do PEC):
```python
from PEC.orquestrador import executar_fluxo_novo_simplificado as pec_fluxo_api
```

**SUBSTITUIR** função `executar_pec()`:
```python
# ANTES
def executar_pec(driver) -> Dict[str, Any]:
    resultado = pec_fluxo(driver)  # DOM antigo
    ...

# DEPOIS
def executar_pec(driver) -> Dict[str, Any]:
    """PEC Isolado — API modular (sem navegação DOM inicial)"""
    print("\n" + "=" * 80)
    print(" PEC ISOLADO")
    print("=" * 80)
    inicio = datetime.now()
    try:
        sucesso = pec_fluxo_api(driver)
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[PEC]  {'Concluído' if sucesso else 'Falha'}")
        return {"sucesso": sucesso, "tempo": tempo}
    except Exception as e:
        tempo = (datetime.now() - inicio).total_seconds()
        print(f"[PEC]  Exceção: {e}")
        return {"sucesso": False, "status": "ERRO_EXECUCAO", "erro": str(e), "tempo": tempo}
```

**REMOVER** função `executar_pec_modular()` inteira (linhas 22-39 de x.py) — agora é o próprio `executar_pec()`.

**Status:** ✅ CONCLUÍDO

---

## ITEM 3 — Remover imports mortos de x.py

Após itens 1 e 2, os seguintes imports em x.py são mortos:

| Import | Linha | Motivo |
|---|---|---|
| `from Mandado.core import navegacao as mandado_navegacao, iniciar_fluxo_robusto as mandado_fluxo` | 81 | Substituído por API |
| `from PEC.processamento import executar_fluxo_novo as pec_fluxo` | 83 | Substituído por orquestrador |
| `from Prazo import loop_prazo, fluxo_pz, fluxo_prazo` (parcial) | 82 | `fluxo_pz` e `fluxo_prazo` não são usados em x.py; `loop_prazo` é usado |

**Status:** ✅ CONCLUÍDO

> **NOTA sobre `fluxo_pz` e `fluxo_prazo`:** importados mas não chamados diretamente em x.py (usados dentro de Prazo/). Remover apenas do import de x.py.

---

## ITEM 4 — Limpar menu de x.py

Após unificação:
- Opção **F** (PEC modular) → remover do menu (E já é modular)
- Opção **G** (Mandado API direto) → remover do menu (B já é API)

```python
# DEPOIS do menu_execucao():
print("  A - Bloco Completo (Mandado → Prazo → PEC)")
print("  B - Mandado Isolado")
print("  C - Prazo Isolado")
print("  D - P2B Isolado")
print("  E - PEC Isolado")
print("  X - Cancelar")
```

Remover do `elif` do menu:
```python
# REMOVER:
elif fluxo == "F":
    resultado = executar_pec_modular(driver)
elif fluxo == "G":
    resultado = processar_mandados_devolvidos_api(driver)
```

**Status:** ✅ CONCLUÍDO

---

## ITEM 5 — Validação

```bash
py -m py_compile x.py
py -c "from x import executar_mandado, executar_pec, executar_p2b"
```

**Status:** ✅ CONCLUÍDO

---

## EFEITO CASCATA — Funções que viram mortas APÓS esta limpeza

Após concluir os itens 1-4, atualizar `controle_limpeza_funcoes_mortas.md`:

| Arquivo | Funções | Ação |
|---|---|---|
| `Mandado/core.py` | `navegacao()`, `iniciar_fluxo_robusto()` | Marcar como PENDENTE para deleção |
| `PEC/processamento_fluxo.py` | `executar_fluxo_novo()` (DOM) | Marcar como PENDENTE para deleção |
| `PEC/core_main.py` | Arquivo inteiro | Verificar + deletar se morto |
| `x.py` | `executar_pec_modular()` | Remover função |

---

## NOTA: O QUE NÃO MUDA

- `executar_prazo()` (fluxo C): `loop_prazo` DOM ainda é o fluxo correto — **não tocar**
- `executar_p2b()` (fluxo D): já usa API ✅ — **não tocar**
- `_executar_mandado_bloco()`, `_executar_pec_bloco()`: chamados por `executar_bloco_completo()` — atualizar automaticamente ao mudar `executar_mandado()` e `executar_pec()`
