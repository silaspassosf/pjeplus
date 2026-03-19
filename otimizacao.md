# OTIMIZAÇÃO PJEPLUS - PONTOS CRÍTICOS

## 📊 STATUS ATUAL
- **Erro headless:** ~40% vs 5% visível
- **Causa:** Click intercepted, overlays, timing
- **Monitor.py:** Coleta dados mas sem autoaprendizado

---

## 🎯 FASE 1: FIX HEADLESS (CRÍTICO)

### Problema
```
Element click intercepted - overlays bloqueiam cliques
Configuração cache desabilitado prejudica performance
Wait strategies inadequadas para headless
```

### Solução
**Fix/headless_helpers.py** - 3 estratégias click:
1. Wait padrão element_to_be_clickable
2. Scroll + wait + click
3. JavaScript click (fallback)

**x.py** - Configuração otimizada:
- Cache HABILITADO em headless
- Viewport maior (1920x1200)
- Animações desabilitadas

### Impacto Esperado
- ✅ **-80%** click intercepted
- ✅ Timeouts headless = visível

---

## 🧠 FASE 2: AUTOAPRENDIZADO MÍNIMO

### Arquitetura
```
monitor.py → selector_learning.py → aprendizado.json
                    ↓
    Prazo/Mandado/PEC (consulta recomendações)
```

### Dados Coletados
```json
{
  "selector": "button.mat-raised",
  "successes": 145,
  "failures": 5,
  "avg_time_ms": 320,
  "score": 0.95
}
```

### Integração Mínima
```python
# Nos fluxos - apenas wrap nas chamadas críticas
from selector_learning import use_best_selector

# Antes: aguardar_e_clicar(driver, "button.submit")
# Depois: use_best_selector(driver, "prazo.submit", aguardar_e_clicar)
```

---

## 📦 ARQUIVOS CRIADOS

### Novos
1. **Fix/headless_helpers.py** (~150 linhas)
2. **selector_learning.py** (~300 linhas)
3. **aprendizado.json** (gerado auto)

### Modificados (mínimo)
1. **monitor.py** (+10 linhas - track success/fail)
2. **Prazo/loop.py** (+5 linhas - import helper)
3. **Mandado/core.py** (+5 linhas - import helper)
4. **PEC/processamento.py** (+5 linhas - import helper)

---

## ⚡ QUICK WINS

### Headless (Dia 1)
```python
# Fix/headless_helpers.py
def click_headless_safe(driver, selector):
    try: return element.click()
    except: return js_click(driver, selector)
```

### Aprendizado (Dia 2)
```python
# selector_learning.py
def report_result(context, operation, selector, success):
    db[selector]["score"] += 0.1 if success else -0.2
    save_json(db)
```

---

## 📈 MÉTRICAS DE SUCESSO

| Métrica | Antes | Meta Fase 1 | Meta Fase 2 |
|---------|-------|-------------|-------------|
| Erro headless | 40% | <10% | <5% |
| Tempo exec | 100% | 90% | 75% |
| Manutenção manual | 100% | 80% | <20% |

---

## 🚀 CRONOGRAMA

**Fase 1 (2 dias):**
- Criar headless_helpers.py
- Modificar x.py (config)
- Integrar em 3 fluxos

**Fase 2 (3 dias):**
- Criar selector_learning.py
- Modificar monitor.py
- Testes iniciais

---

## ⚠️ PRINCÍPIOS

1. **Mínima invasão** - Novos arquivos > modificar existentes
2. **Backward compatible** - Funciona sem aprendizado
3. **Fail-safe** - Fallback para modo antigo
4. **Poucas chamadas** - Wrap, não refatorar
