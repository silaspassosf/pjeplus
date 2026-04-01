# Plano 4 — SmartFinder Efetivo

**Status:** Diagnóstico concluído — implementação da função universal `buscar()`  
**Risco:** Baixo (adição de função nova, sem alterar existentes)  
**Modelo alvo:** GPT-4.1 via PJE.md (Surgical Mode)

---

## Diagnóstico

### Por que o SmartFinder não está funcionando de fundo

O `Fix/smart_finder.py` tem a lógica correta mas o **padrão de uso está errado** em
todos os módulos de negócio:

| Problema | Evidência | Consequência |
|---|---|---|
| `_SF = SmartFinder()` sem driver no nível de módulo | `Prazo/loop_ciclo2_*.py` linhas 7-8 | `self.driver = None` — `find_element` vai dar `AttributeError` silencioso |
| `injetar_smart_finder_global(driver)` chamado em `x.py` mas módulos criam seus próprios `_SF` | `x.py` linha ~50 | O shim global NÃO beneficia instâncias locais `_SF` |
| Módulos usam `driver.find_element()` diretamente sem passar pela camada de cache | `atos/`, `Fix/selenium_base/` etc. | Cache nunca é populado por essas buscas |
| Não há função utilitária de busca universal | — | Cada dev inventa seu padrão |

### O que existe e funciona
- `SmartFinder.find(driver, chave, candidatos)` — passa `driver` explicitamente → **correto**
- `SmartFinder._carregar_cache()` / `_salvar_cache()` — lê/grava `aprendizado_seletores.json` assincronamente → **correto**
- `_gerar_e_testar_candidatos()` — heurística de fallback → **correto**

### O que falta
Uma **função de nível de módulo** que encapsula uma instância singleton do SmartFinder
e pode ser chamada em qualquer arquivo com apenas `buscar(driver, chave, candidatos)`.

---

## Solução: Singleton de Módulo + Função Universal

### Etapa 4.1 — Adicionar `buscar()` ao `Fix/smart_finder.py`

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: Fix/smart_finder.py
operacao: insert_before
ancora: "__all__ = ['SmartFinder', 'injetar_smart_finder_global']"
```

```python
# ---------------------------------------------------------------------------
# Singleton de módulo — instância compartilhada com cache carregado uma vez
# ---------------------------------------------------------------------------
_singleton: SmartFinder | None = None


def _get_singleton() -> SmartFinder:
    """Retorna (ou cria) a instância global do SmartFinder sem driver."""
    global _singleton
    if _singleton is None:
        _singleton = SmartFinder()
    return _singleton


def buscar(driver, chave: str, candidatos: list):
    """
    Função universal de busca de elementos com cache automático.

    Uso em qualquer módulo:
        from Fix.smart_finder import buscar
        el = buscar(driver, 'btn_salvar', ['.salvar-btn', '//button[@aria-label="Salvar"]'])

    Parâmetros:
        driver     — WebDriver ativo
        chave      — identificador único para o cache (snake_case descritivo)
        candidatos — lista de seletores CSS ou XPath (// = xpath, demais = css)

    Retorna o WebElement ou None se não encontrado.
    Log de aprendizado vai para monitor_aprendizado.log (separado do log principal).
    """
    sf = _get_singleton()
    sf.set_driver(driver)
    return sf.find(driver, chave, candidatos)
```

```python
# Atualizar __all__
__all__ = ['SmartFinder', 'injetar_smart_finder_global', 'buscar']
```

---

### Etapa 4.2 — Migrar Prazo/loop_ciclo2_selecao.py para usar `buscar()`

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: Prazo/loop_ciclo2_selecao.py
operacao: replace
ancora: "from Fix.smart_finder import SmartFinder"
```

```python
# ANTES
from Fix.smart_finder import SmartFinder

# Reuse SmartFinder instance
_SF = SmartFinder()
```

```python
# DEPOIS
from Fix.smart_finder import buscar
```

> **Nota para Surgical Mode:** após substituir, trocar chamadas
> `_SF.find(driver, chave, candidatos)` por `buscar(driver, chave, candidatos)`.

---

### Etapa 4.3 — Migrar Prazo/loop_ciclo2_processamento.py (mesmo padrão)

Mesmo patch da Etapa 4.2 aplicado em `Prazo/loop_ciclo2_processamento.py`.

---

### Etapa 4.4 — Documentar uso em idx.md

<!-- pjeplus:apply -->
## Alteração Proposta

```
arquivo: idx.md
operacao: replace
ancora: "Fix/smartfinder.py | SmartFinder — busca com cache e fallback heurístico"
```

```markdown
| `Fix/smart_finder.py` | `SmartFinder` — busca com cache e fallback; **usar** `buscar(driver, chave, candidatos)` como ponto único de entrada |
```

---

## Como usar `buscar()` em módulos novos

```python
# Import único — sem instanciar classe
from Fix.smart_finder import buscar

# Em qualquer função que receba driver:
def minha_funcao(driver):
    btn = buscar(driver, 'btn_confirmar_ato', [
        'button.confirmar-ato',
        '//button[contains(@aria-label, "Confirmar")]',
        '[mattooltip*="Confirmar"]',
    ])
    if btn:
        driver.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'}); arguments[0].click();", btn)
```

**Regras de chave de cache:**
- snake_case descritivo: `btn_salvar_minuta`, `input_numero_processo`
- Prefixar por contexto: `prazo_btn_proxima`, `sisb_campo_valor`
- Nunca usar seletores CSS como chave — a chave é o **nome semântico** do elemento

---

## Verificação

```bash
py -m py_compile Fix/smart_finder.py
py -m py_compile Prazo/loop_ciclo2_selecao.py
py -m py_compile Prazo/loop_ciclo2_processamento.py

# Validar que cache é lido/gravado
py -c "
from Fix.smart_finder import buscar, _get_singleton
sf = _get_singleton()
print('Cache carregado:', len(sf.cache), 'entradas')
"
```
