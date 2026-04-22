# Plano: Aprendizado Contínuo nas Execuções — PJePlus

**Data:** 31/03/2026  
**Status:** ANÁLISE COMPLETA — Implementação incremental em 4 etapas  
**Arquivos alvo:** `Fix/otimizacao_wrapper.py` (novo), `x.py` (2 patches), `monitor.py` (1 patch)  
**Dependências:** `monitor.py`, `selector_learning.py`, `Fix/smart_finder.py` — todos existem

---

## 1. Diagnóstico do Estado Atual

### 1.1 Infraestrutura já existente (não criar novamente)

| Componente | Arquivo | O que faz | Status |
|---|---|---|---|
| Coleta de métricas | `monitor.py::MonitorData` | Registra stats de chamadas, seletores, erros | ✅ Funcional |
| Sessão de monitoramento | `monitor.py::MonitorSession` | Context manager que wraps execução | ✅ Funcional |
| Score de seletores | `selector_learning.py::SelectorLearning` | Calcula score 0-1 por seletor | ✅ Funcional |
| Persistência de aprendizado | `aprendizado.json` | DB de histórico de seletores | ✅ Em uso |
| Cache SmartFinder | `aprendizado_seletores.json` | Cache de seletores eficazes | ✅ Em uso |
| Ponto de entrada no orq. | `x.py::main()` | Chama `Fix.otimizacao_wrapper` | ⚠️ Parcial (módulo não existe) |

### 1.2 O gap: ausência de feedback loop

```
ATUAL (dados coletados mas não retroalimentados):

x.py inicia
    → executar_bloco_completo()
        → Prazo, Mandado, PEC rodam
        → SmartFinder usa aprendizado_seletores.json ← cache lido
    → x.py encerra
    → MonitorSession? NÃO usada em x.py
    → SelectorLearning? NÃO consultada em x.py
    → aprendizado.json? NÃO atualizado após execução

DESEJADO (loop fechado):

x.py inicia
    → MonitorSession.__enter__()  ← instrumenta Fix functions
    → executar_bloco_completo()
        → Prazo, Mandado, PEC rodam com instrumentação ativa
        → SmartFinder usa aprendizado_seletores.json (com scores do histórico)
        → Cada sucesso/falha de seletor é registrado em MonitorData
    → MonitorSession.__exit__()
        → Gera relatório JSON da sessão
        → Atualiza SelectorLearning com resultados desta execução
        → SelectorLearning persiste scores atualizados em aprendizado.json
        → SmartFinder priorizará seletores com score alto na próxima execução
```

### 1.3 Por que x.py já está preparado

```python
# x.py:main() já chama (linhas 862-865, 940-942):
try:
    from Fix.otimizacao_wrapper import inicializar_otimizacoes
    inicializar_otimizacoes()
except:
    pass

# ...execução...

try:
    from Fix.otimizacao_wrapper import finalizar_otimizacoes
    finalizar_otimizacoes()
except:
    pass
```

O orquestrador JÁ tem os hooks de inicialização e finalização. Só falta criar `Fix/otimizacao_wrapper.py`.

---

## 2. Arquitetura do Aprendizado Contínuo

### 2.1 Diagrama de fluxo

```
x.py startup
    └─ inicializar_otimizacoes()
           └─ Carrega SelectorLearning (aprendizado.json)
           └─ Prepara MonitorSession global

Execução de fluxo (Mandado/Prazo/PEC)
    └─ MonitorSession ativa (instrumentação via patch)
           └─ Cada chamada Fix: tempo registrado
           └─ Cada erro: registrado com source + mensagem
           └─ SmartFinder: ao usar fallback, registra como "selector_miss"

x.py encerramento
    └─ finalizar_otimizacoes()
           └─ MonitorSession.__exit__() gera report JSON
           └─ _processar_aprendizado_pos_execucao()
                  └─ Para cada seletor com falha: report_result(success=False)
                  └─ Para cada seletor de sucesso: report_result(success=True)
                  └─ SelectorLearning._save() persiste scores atualizados
           └─ Log resumo: "Aprendizado: X seletores atualizados, Y lembranças novas"
```

### 2.2 Integração com SmartFinder

O `SmartFinder` já usa `aprendizado_seletores.json`. O aprendizado contínuo proposto NÃO muda o SmartFinder diretamente.

A **retroalimentação indireta** ocorre assim:
- `SelectorLearning` persiste scores em `aprendizado.json`
- Após N execuções, um script de manutenção pode sincronizar os top-scorers para `aprendizado_seletores.json` (cache do SmartFinder)
- Isso é uma etapa futura — a fase 1 foca apenas em **coletar + persistir scores**

> **Princípio de não-invasão:** A integração com SmartFinder é futura (etapa 4). As etapas 1-3 apenas coletam e persistem dados, sem alterar comportamento de busca de elementos.

---

## 3. Implementação Incremental

### Etapa 3.1 — Criar `Fix/otimizacao_wrapper.py` (Baixo risco, isolado)

**Descrição:** Módulo que encapsula inicialização/finalização do aprendizado. É o único novo arquivo desta proposta.

**Arquivo a criar:** `Fix/otimizacao_wrapper.py`

```python
"""
Fix/otimizacao_wrapper.py — Wrapper de otimização e aprendizado contínuo.

Ponto de integração entre MonitorSession (monitor.py) e SelectorLearning
(selector_learning.py). Chamado pelo orquestrador x.py via:
    inicializar_otimizacoes()   ← no início do main()
    finalizar_otimizacoes()     ← no finally do main()
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from Fix.log import getmodulelogger

logger = getmodulelogger(__name__)

_monitor_session: Optional[Any] = None
_selector_learning: Optional[Any] = None
_inicio_execucao: Optional[datetime] = None


def inicializar_otimizacoes() -> None:
    """Inicializa coleta de métricas e carrega histórico de aprendizado."""
    global _selector_learning, _inicio_execucao

    _inicio_execucao = datetime.now()

    # Carregar histórico de aprendizado de seletores
    try:
        from selector_learning import SelectorLearning
        _selector_learning = SelectorLearning()
        logger.info(f"Aprendizado carregado: {len(_selector_learning.db)} seletores no histórico")
    except Exception as e:
        logger.warning(f"Aprendizado indisponivel: {e}")


def registrar_resultado_fluxo(
    fluxo: str,
    sucesso: bool,
    tempo_s: float,
    erros: Optional[list] = None,
) -> None:
    """Registra resultado de um fluxo completo para aprendizado."""
    if _selector_learning is None:
        return

    try:
        # Registrar seletores que falharam durante este fluxo
        if erros:
            for erro in erros:
                fonte = erro.get("source", "unknown")
                msg = erro.get("message", "")
                # Heurística: se a mensagem menciona seletor, registrar como falha
                if any(s in msg.lower() for s in ["nosuchelement", "not found", "nao encontrado", "timeout"]):
                    _selector_learning.report_result(
                        context=fluxo,
                        operation="elemento_nao_encontrado",
                        selector=fonte,
                        success=False,
                    )
        logger.info(f"Fluxo {fluxo}: {'SUCESSO' if sucesso else 'FALHA'} em {tempo_s:.1f}s registrado")
    except Exception as e:
        logger.warning(f"Erro ao registrar resultado de fluxo: {e}")


def finalizar_otimizacoes() -> None:
    """Persiste estado de aprendizado e gera resumo da sessão."""
    global _selector_learning, _inicio_execucao

    if _selector_learning is None:
        return

    try:
        _selector_learning._save()
        duracao = (datetime.now() - _inicio_execucao).total_seconds() if _inicio_execucao else 0
        total = len(_selector_learning.db)
        blacklist = len(_selector_learning.blacklist)
        logger.info(
            f"Sessao encerrada em {duracao:.0f}s | "
            f"Historico: {total} seletores | Blacklist: {blacklist}"
        )
    except Exception as e:
        logger.warning(f"Erro ao finalizar otimizacoes: {e}")
    finally:
        _selector_learning = None
        _inicio_execucao = None
```

**Validação:** `py -m py_compile Fix/otimizacao_wrapper.py`  
**Risco:** Nulo — módulo isolado, chamado apenas no try/except de x.py

---

### Etapa 3.2 — Integrar `registrar_resultado_fluxo()` em x.py (Baixo risco)

**Descrição:** Após cada `executar_*()`, reportar resultado para o aprendizado.

**Patch em x.py** — adicionar chamada após o relatório final no bloco `with driver_session`:

Localizar o bloco (aproximadamente linha 890 de x.py):
```python
                    print(f"  Tempo total: {tempo_total:.2f}s")
                    print("=" * 80)
```

Adicionar após (dentro do mesmo `try`):
```python
                    # Aprendizado contínuo: registrar resultado desta execução
                    try:
                        from Fix.otimizacao_wrapper import registrar_resultado_fluxo
                        sucesso_exec = resultado.get('sucesso', resultado.get('sucesso_geral', False)) if resultado else False
                        registrar_resultado_fluxo(
                            fluxo=fluxo,
                            sucesso=bool(sucesso_exec),
                            tempo_s=tempo_total,
                        )
                    except Exception:
                        pass
```

**Risco:** Nulo — wrapped em try/except

---

### Etapa 3.3 — Conectar MonitorSession ao fluxo principal (Médio risco)

**Pré-requisito:** Etapas 3.1 e 3.2 validadas e estáveis por ao menos 3 execuções reais.

**Descrição:** Envolver `executar_*()` em `MonitorSession` para instrumentação automática de funções Fix.

**Onde:** Criar `_executar_com_monitor(driver, fluxo)` em x.py:

```python
def _executar_com_monitor(driver, fluxo: str) -> dict:
    """Executa fluxo com MonitorSession ativa para coleta de métricas."""
    import monitor as monitor_mod
    
    session = monitor_mod.MonitorSession(driver=driver)
    try:
        session.__enter__()
        inicio = datetime.now()
        
        if fluxo == "A":
            resultado = executar_bloco_completo(driver)
        elif fluxo == "B":
            resultado = executar_mandado(driver)
        elif fluxo == "C":
            resultado = executar_prazo(driver)
        elif fluxo == "D":
            resultado = executar_p2b(driver)
        elif fluxo == "E":
            resultado = executar_pec(driver)
        else:
            resultado = {"sucesso": False, "erro": "Fluxo desconhecido"}
        
        tempo_total = (datetime.now() - inicio).total_seconds()
        return resultado, tempo_total, session.data.errors
        
    except Exception as e:
        session.__exit__(type(e), e, None)
        raise
    else:
        session.__exit__(None, None, None)
        return resultado, tempo_total, session.data.errors
```

> ⚠️ **Atenção:** `MonitorSession` suprime prints (redireciona para log silencioso). Verificar comportamento em produção antes de ativar em todos os fluxos.

**Risco:** Médio — MonitorSession altera comportamento de prints durante execução.  
**Recomendação:** Ativar por variável de ambiente `PJEPLUS_MONITOR=1` antes de tornar padrão.

---

### Etapa 3.4 — Sincronizar SelectorLearning → SmartFinder (Longo prazo)

**Pré-requisito:** Etapas 3.1-3.3 estáveis com histórico de pelo menos 50 execuções.

**Descrição:** Periodicamente, promover seletores com score alto do `aprendizado.json` para o cache do `aprendizado_seletores.json` (usado pelo SmartFinder).

**Estratégia:** Criar script utilitário `tools/sync_learning.py` (não integrar no fluxo principal):

```python
# tools/sync_learning.py — execução manual
"""Sincroniza top-seletores de aprendizado.json para aprendizado_seletores.json"""
import json

def sincronizar(min_score=0.8, min_tentativas=10):
    with open("aprendizado.json") as f:
        aprendizado = json.load(f)
    
    with open("aprendizado_seletores.json") as f:
        cache_sf = json.load(f)
    
    promovidos = 0
    for key, data in aprendizado.get('selectors', {}).items():
        score = data.get('score', 0)
        attempts = data.get('attempts', 0)
        if score >= min_score and attempts >= min_tentativas:
            # key é "context.operation.selector"
            partes = key.split('.', 2)
            if len(partes) == 3:
                _, _, seletor = partes
                chave_sf = key.replace('.', '_')
                cache_sf[chave_sf] = seletor
                promovidos += 1
    
    with open("aprendizado_seletores.json", 'w') as f:
        json.dump(cache_sf, f, indent=2, ensure_ascii=False)
    
    print(f"Sincronizados {promovidos} seletores para SmartFinder cache")

if __name__ == "__main__":
    sincronizar()
```

**Risco:** Baixo — script isolado, execução manual, não altera fluxo de automação.

---

## 4. Plano de Execução

| Etapa | Arquivo(s) | Linhas | Risco | Validação |
|---|---|---|---|---|
| **3.1** — Criar otimizacao_wrapper.py | `Fix/otimizacao_wrapper.py` (novo) | ~70 | Nulo | `py -m py_compile` |
| **3.2** — Registrar resultado em x.py | `x.py` | +8 linhas | Nulo | Executar x.py, confirmar log "registrado" |
| **3.3** — MonitorSession em x.py | `x.py` | +25 linhas | Médio | Ativar via `PJEPLUS_MONITOR=1` primeiro |
| **3.4** — Sync tools/sync_learning.py | `tools/sync_learning.py` (novo) | ~30 | Baixo | Execução manual após 50+ runs |

---

## 5. Observações de Segurança

### 5.1 Não alterar comportamento de automação
As etapas 3.1 e 3.2 são **observação pura** — apenas coletam dados e persistem. Nenhuma decisão de automação é tomada com base no aprendizado nas fases iniciais.

### 5.2 MonitorSession suprime prints (etapa 3.3)
`MonitorSession._filter_prints()` redireciona prints não-críticos para `data.suppressed_logs`. Em produção, isso pode ocultar mensagens importantes durante debug.  
**Mitigação:** Ativar apenas com variável de ambiente, nunca como padrão silencioso.

### 5.3 Blacklist de seletores
`SelectorLearning` adiciona automaticamente à blacklist seletores com score < 0.3 após 10+ tentativas. Monitorar `aprendizado.json['blacklist']` periodicamente para garantir que seletores legítimos não sejam descartados por instabilidade do ambiente (ex: servidor PJe lento por dia/hora).

### 5.4 Tamanho do histórico
O arquivo `aprendizado.json` pode crescer indefinidamente. Adicionar rotina de limpeza no `SelectorLearning._save()` para manter apenas os últimos 1000 seletores ativos não é necessário agora, mas deve ser planejado quando o arquivo ultrapassar 500KB.

---

## 6. Verificação de Sucesso

Após implementar etapas 3.1 + 3.2, o log de cada execução deve conter:

```
[Fix.otimizacao_wrapper] Aprendizado carregado: 142 seletores no histórico
... execução normal ...
[Fix.otimizacao_wrapper] Fluxo A: SUCESSO em 847.3s registrado
[Fix.otimizacao_wrapper] Sessao encerrada em 852s | Historico: 143 seletores | Blacklist: 2
```

Após 10+ execuções, `aprendizado.json` deve crescer com scores variados — sinal de que o aprendizado está sendo coletado.
