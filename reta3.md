# PJePlus — Plano de Refatoração Estrutural

> **Documento para uso direto com Claude Sonnet / Copilot**  
> Idioma do projeto: Python 3.10+ | JavaScript (scripts injetados via Selenium)  
> Repositório: `github.com/silaspassosf/pjeplus`  
> Filosofia inegociável: **mudanças cirúrgicas, zero perda de comportamento funcional**

***

## 1. Contexto e Diagnóstico

O PJePlus é um sistema de automação judicial que aciona o PJe (Angular SPA pesado) via Selenium/Firefox.
O código funciona, está quase completo e em uso. O objetivo desta refatoração é **reduzir complexidade
acidental** — não reimplementar nada. Cada item abaixo é independente; podem ser aplicados em qualquer ordem.

### 1.1 Topologia atual relevante

```
Fix/
  core.py          ← ~600 linhas de wrappers de uma linha (PROBLEMA #1)
  variaveis.py     ← ~12 wrappers de uma linha (PROBLEMA #1)
  abas.py          ← funções com 5+ níveis de indentação (PROBLEMA #2)
  __init__.py      ← re-exporta tudo de core.py

atos/
  comunicacao.py   ← makecomunicacaowrapper: factory pattern OK, mas wrapper() tem 80+ linhas
  wrappersato.py   ← 30+ instâncias de makeatowrapper (padrão OK)
  wrapperspec.py   ← 15+ instâncias de makecomunicacaowrapper (padrão OK)
  wrappersmov.py   ← funções com try/except retornando False (PROBLEMA #3)
  wrappersutils.py ← visibilidadesigilosos: 120+ linhas, 5 níveis de indent (PROBLEMA #2)

SISB/
  standards.py     ← @dataclass JÁ USADO AQUI (modelo a replicar)

x.py               ← orquestrador: aninhamento excessivo, try/except triple-nested (PROBLEMA #2)
```

### 1.2 Padrões problemáticos encontrados no dump

| # | Padrão | Arquivo(s) principal(is) | Impacto |
|---|--------|--------------------------|---------|
| P1 | Wrapper de uma linha com `from X import Y as impl; return impl(...)` | `Fix/core.py` (~40 funções), `Fix/variaveis.py` (~12 funções) | Indireção vazia, dificulta rastreamento |
| P2 | Funções com 5+ níveis de indentação | `Fix/abas.py`, `atos/wrappersutils.py`, `x.py` | Viola PEP8, difícil testar |
| P3 | `except Exception as e: return False` sem re-raise | `atos/wrappersmov.py`, `atos/comunicacao.py` | Silencia erros, impossibilita diagnóstico |
| P4 | `time.sleep(N)` hardcoded onde `aguardar_renderizacao_nativa` existe | `atos/wrappersmov.py`, `atos/wrappersutils.py` | Race conditions, lentidão |
| P5 | JavaScript de 80-150 linhas embutido em f-strings Python | `SISB/`, `PEC/` | Inlegível, sem syntax highlight |
| P6 | `dict` solto como objeto de retorno/entrada | `atos/comunicacao.py` (callkwargs), `x.py` (resultado) | Sem tipagem, acesso por string |
| P7 | Driver criado/destruído sem context manager | `x.py` (main), múltiplos orquestradores | Driver pode vazar em exceção |
| P8 | Import lazy dentro de função repetido milhares de vezes | `Fix/core.py` (cada wrapper importa na chamada) | Overhead de import lookup |

***

## 2. Refatoração #1 — Eliminar wrappers de uma linha em `Fix/core.py`

### Diagnóstico

`Fix/core.py` contém ~40 funções neste formato:

```python
# PADRÃO ATUAL (problemático)
def wait(driver: WebDriver, selector: str, timeout: int = 10, by: str = By.CSS_SELECTOR) -> Any:
    """Wrapper para Fix.seleniumbase.waitoperations.wait."""
    from Fix.seleniumbase.waitoperations import wait as impl
    return impl(driver, selector, timeout=timeout, by=by)

def buscarseletorrobusto(driver: WebDriver, textos: List[str], ...) -> Optional[WebElement]:
    """Wrapper para Fix.seleniumbase.retrylogic.buscarseletorrobusto."""
    from Fix.seleniumbase.retrylogic import buscarseletorrobusto as impl
    return impl(driver, textos, contexto=contexto, timeout=timeout, log=log)

# ... repetido ~40 vezes
```

Idem em `Fix/variaveis.py`:

```python
def resolver_variavel(client, id_processo, variavel):
    from Fix.variaveis.resolvers import resolver_variavel as impl
    return impl(client, id_processo, variavel)
```

### Solução

Substituir todo o corpo de `Fix/core.py` por re-exportações no `__init__.py` e importações diretas no `core.py`.
A interface pública **não muda** — qualquer código que faz `from Fix.core import wait` continua funcionando.

#### `Fix/core.py` — novo padrão (trecho ilustrativo, aplicar ao arquivo completo)

```python
# Fix/core.py
# Re-exportações diretas — sem wrappers intermediários
from Fix.seleniumbase.waitoperations import (
    wait,
    waitforvisible,
    waitforclickable,
    waitforpageload,
    esperarelemento,
    esperarurconter,
)
from Fix.seleniumbase.retrylogic import (
    buscarseletorrobusto,
    comretry,
)
from Fix.seleniumbase.clickoperations import (
    aguardareclicar,
    safeclicknoscroll,
)
from Fix.seleniumbase.elementinteraction import jsbase
from Fix.extracao import (
    safeclick,
    selecionaropcao,
    preenchercampo,
    preenchercamposprazo,
    preenchermultiploscampos,
    escolheropcaointeligente,
    encontrarelementointeligente,
    extrairdireto,
    extrairdocumento,
    extrairdadosprocesso,
)
from Fix.drivers.lifecycle import (
    criardriverPC,
    criardriverVT,
    criardrivernotebook,
    criardriversisbpc,
    criardriversisbnotebook,
)
from Fix.utils import finalizardriver, ErroCollector
from Fix.utilsobserver import aguardarrenderizacaonativa
from Fix.abas import (
    validarconexaodriver,
    trocarparanovaaba,
    forcarfechamentoabasextras,
    isbrowsingcontextdiscardederror,
)
# ... demais importações
```

#### `Fix/variaveis/__init__.py` — novo padrão

```python
# Fix/variaveis/__init__.py  (substitui os wrappers em Fix/variaveis.py)
from .client import PjeApiClient, session_from_driver
from .resolvers import (
    resolver_variavel,
    get_all_variables,
    obterchaveultimodespachodecisaosentenca,
)
from .helpers import verificar_bndt, domicilio_eletronico
```

### Regras de aplicação

1. **Não renomear nenhuma função.** Apenas mover o `import` de dentro da função para o topo do módulo.
2. Se a função tinha docstring, mover a docstring para o módulo de origem.
3. Verificar `Fix/__init__.py` — ele re-exporta de `core.py`. Após a mudança, continua funcionando.
4. Testar com `python -c "from Fix.core import wait, aguardareclicar, criardriverPC"` — deve importar sem erro.

***

## 3. Refatoração #2 — Limitar indentação máxima a 3 níveis

### Diagnóstico

`Fix/abas.py` — `forcarfechamentoabasextras` e `validarconexaodriver` têm 5-6 níveis:

```python
# PADRÃO ATUAL — 5 níveis de indentação
def forcarfechamentoabasextras(driver, abalistaoriginal: str):
    try:
        try:
            abasatuais = driver.window_handles
            for idx, aba in enumerate(abasextras, 1):
                for tentativa in range(3):
                    try:
                        driver.switch_to.window(aba)
                        try:
                            urlaba = driver.current_url[:60]  # ← nível 5
                        except:
                            pass
```

`atos/wrappersutils.py` — `visibilidadesigilosos` tem 120+ linhas com o mesmo problema.

`x.py` — `main()` tem try/except triplo aninhado.

### Solução: "Extract Until It Hurts"

Regra: **máximo 3 níveis de indentação por função** (módulo > bloco > linha).
Técnica: extrair blocos internos para funções com nomes descritivos.

#### Exemplo aplicado a `Fix/abas.py`

```python
# ANTES — tudo dentro de forcarfechamentoabasextras
for idx, aba in enumerate(abasextras, 1):
    fechouaba = False
    for tentativa in range(3):
        try:
            driver.switch_to.window(aba)
            try:
                urlaba = driver.current_url[:60]
            except Exception:
                urlaba = "URL não disponível"
            driver.close()
            fechouaba = True
            break
        except Exception as e:
            if tentativa == 2:
                logger.error(f"LIMPEZA:ERRO — Não foi possível fechar aba {idx}")
    if fechouaba:
        time.sleep(0.1)

# DEPOIS — lógica extraída para função auxiliar privada
def _fechar_aba_com_retry(driver, aba: str, idx: int) -> bool:
    """Tenta fechar uma aba até 3 vezes. Retorna True se fechou."""
    for tentativa in range(3):
        try:
            driver.switch_to.window(aba)
            driver.close()
            return True
        except Exception:
            if tentativa == 2:
                logger.error(f"LIMPEZA:ERRO — Não foi possível fechar aba {idx} após 3 tentativas")
    return False


def _obter_url_aba(driver) -> str:
    """Obtém URL da aba atual de forma segura."""
    try:
        return driver.current_url[:60]
    except Exception:
        return "URL não disponível"


def forcarfechamentoabasextras(driver, abalistaoriginal: str):
    """Fecha todas as abas extras. Retorna True/False/'FATAL'."""
    conexaostatus = validarconexaodriver(driver, "LIMPEZA")
    if conexaostatus == "FATAL":
        logger.error("LIMPEZA:FATAL — Contexto do navegador foi descartado")
        return "FATAL"
    if not conexaostatus:
        logger.error("LIMPEZA:ERRO — Conexão perdida")
        return False

    try:
        abasatuais = driver.window_handles
    except Exception as e:
        logger.error(f"LIMPEZA:ERRO — Falha ao obter lista de abas: {e}")
        return False

    if abalistaoriginal not in abasatuais:
        logger.error("LIMPEZA:ERRO — Aba original não encontrada!")
        return False

    abasextras = [aba for aba in abasatuais if aba != abalistaoriginal]
    for idx, aba in enumerate(abasextras, 1):
        if _fechar_aba_com_retry(driver, aba, idx):
            time.sleep(0.1)

    return _verificar_e_voltar_para_original(driver, abalistaoriginal)
```

#### Exemplo aplicado a `x.py` — função `main()`

```python
# ANTES — try/except triplo aninhado em main()
try:
    while True:
        resultado_menu = menuambiente()
        if not resultado_menu:
            print("Cancelado")
            break
        ...
        try:
            inicio = datetime.now()
            if fluxo == "A":
                resultado = executar_bloco_completo(driver)
            ...
        except KeyboardInterrupt:
            print("Interrompido Ctrl+C")
            try:
                safeimmediateshutdown(driver, teeoutput, reason="KeyboardInterrupt")
            except Exception:
                try:
                    finalizardriverimediato(fix)(driver)
                except Exception:
                    pass
            os._exit(0)
except KeyboardInterrupt:
    ...
except Exception as e:
    ...
finally:
    ...

# DEPOIS — responsabilidades isoladas em funções de ciclo de vida
def _executar_fluxo(driver, fluxo: str) -> dict:
    """Despacha para o executor correto. Levanta exceção em falha."""
    executores = {
        "A": executar_bloco_completo,
        "B": executar_mandado,
        "C": executar_prazo,
        "D": executar_p2b,
        "E": executar_pec,
    }
    if fluxo not in executores:
        raise ValueError(f"Fluxo desconhecido: {fluxo}")
    return executores[fluxo](driver)


def _ciclo_de_sessao(driver_type, fluxo: str, teeoutput) -> dict:
    """Executa uma sessão completa: driver → fluxo → finalização."""
    driver = criarelog_driver(driver_type)
    if not driver:
        return {"sucesso": False, "erro": "Falha ao criar driver"}
    try:
        inicio = datetime.now()
        resultado = _executar_fluxo(driver, fluxo)
        resultado["tempo"] = (datetime.now() - inicio).total_seconds()
        return resultado
    finally:
        finalizardriver(fix)(driver)


def main():
    """Orquestrador principal — apenas menus e loop de sessões."""
    _inicializar_otimizacoes()
    teeoutput = None
    try:
        while True:
            driver_type, debug_mode = menuambiente() or (None, False)
            if not driver_type:
                break
            fluxo = menuexecucao()
            if not fluxo:
                continue
            logfile, teeoutput = configurar_logging(driver_type)
            resultado = _ciclo_de_sessao(driver_type, fluxo, teeoutput)
            _imprimir_relatorio(resultado)
    except KeyboardInterrupt:
        safeimmediateshutdown(None, teeoutput, reason="outer-KeyboardInterrupt")
    finally:
        if teeoutput:
            teeoutput.close()
        _finalizar_otimizacoes()
```

### Regras de aplicação

- **Limite duro:** 3 níveis de indentação por função (módulo → bloco lógico → linha).
- **Convenção de nomenclatura:** funções auxiliares privadas (não exportadas) começam com `_`.
- **Funções auxiliares ficam no mesmo arquivo**, imediatamente acima da função que as usa.
- Nenhuma lógica de negócio deve ser perdida — apenas reorganizada.

***

## 4. Refatoração #3 — Substituir `return False` por exceções tipadas

### Diagnóstico

O padrão `except Exception as e: return False` está em ~20 funções. O problema:
o chamador não sabe *por que* falhou. Exemplo real do dump:

```python
# Fix/abas.py — padrão atual
def trocarparanovaaba(driver, abalistaoriginal: str):
    try:
        ...
    except Exception as e:
        logger.error(f"ABAS:ERRO — Erro geral: {e}")
        return None   # ← chamador não sabe se foi timeout, driver morto ou aba inexistente

# atos/wrappersmov.py — padrão atual
def movexec(driver, debug=False):
    destinos = ["Iniciar execução"]
    for destino in destinos:
        try:
            ok = movimentarinteligente(driver, destino, timeout=8)
            if ok:
                return True
        except Exception:
            continue
    return False   # ← silencia todas as exceções
```

### Solução

Criar hierarquia de exceções tipadas em `Fix/exceptions.py` (arquivo novo, ~30 linhas):

```python
# Fix/exceptions.py  (NOVO ARQUIVO)
"""Hierarquia de exceções do PJePlus."""


class PJePlusError(Exception):
    """Exceção base do PJePlus."""


class DriverFatalError(PJePlusError):
    """Contexto do navegador foi descartado — driver inutilizável."""


class ElementoNaoEncontradoError(PJePlusError):
    """Elemento não foi localizado no DOM após tentativas."""
    def __init__(self, seletor: str, contexto: str = ""):
        self.seletor = seletor
        self.contexto = contexto
        super().__init__(f"Elemento '{seletor}' não encontrado. Contexto: {contexto}")


class TimeoutFluxoError(PJePlusError):
    """Operação excedeu o tempo limite."""
    def __init__(self, operacao: str, timeout_s: int):
        self.operacao = operacao
        self.timeout_s = timeout_s
        super().__init__(f"Timeout de {timeout_s}s em '{operacao}'")


class NavegacaoError(PJePlusError):
    """Falha ao trocar de aba ou navegar para uma tela."""


class LoginError(PJePlusError):
    """Falha no processo de login."""
```

Aplicar nas funções de infraestrutura (NÃO nas funções de negócio em `atos/`):

```python
# Fix/abas.py — com exceções tipadas
from Fix.exceptions import DriverFatalError, NavegacaoError

def trocarparanovaaba(driver, abalistaoriginal: str) -> str:
    """Troca para nova aba. Levanta NavegacaoError se não conseguir."""
    if not validarconexaodriver(driver, "ABAS"):
        raise NavegacaoError("Driver desconectado ao tentar trocar de aba")

    abas = driver.window_handles
    for handle in abas:
        if handle != abalistaoriginal:
            driver.switch_to.window(handle)
            if driver.current_window_handle == handle:
                return handle

    raise NavegacaoError("Nenhuma aba nova disponível para troca")
```

```python
# atos/wrappersmov.py — com exceções tipadas
from Fix.exceptions import ElementoNaoEncontradoError

def movexec(driver, debug=False):
    """Move processo para 'Iniciar execução'. Levanta ElementoNaoEncontradoError se não achar."""
    for destino in ["Iniciar execução"]:
        if movimentarinteligente(driver, destino, timeout=8):
            return True
    raise ElementoNaoEncontradoError("Iniciar execução", contexto="movexec")
```

Os **orquestradores** (`x.py`, fluxos de `Prazo/`, `Mandado/`) capturam uma vez:

```python
# x.py — captura no nível correto
from Fix.exceptions import PJePlusError, DriverFatalError

def _ciclo_de_sessao(driver_type, fluxo, teeoutput):
    driver = criarelog_driver(driver_type)
    try:
        return _executar_fluxo(driver, fluxo)
    except DriverFatalError:
        logger.error("Driver inutilizável — encerrando sessão")
        return {"sucesso": False, "erro": "driver_fatal"}
    except PJePlusError as e:
        logger.error(f"Erro de automação: {e}")
        return {"sucesso": False, "erro": str(e)}
    finally:
        finalizardriver(fix)(driver)
```

### Regras de aplicação

- Criar `Fix/exceptions.py` primeiro.
- Aplicar exceções tipadas **apenas** em `Fix/abas.py`, `Fix/drivers/lifecycle.py` e funções de movimento em `atos/wrappersmov.py`.
- Código de negócio (`atos/comunicacao.py`, `PEC/`, `Mandado/`) **não muda** — eles continuam chamando as funções normalmente; se houver falha, a exceção sobe automaticamente.
- **Não remover** `try/except` dos orquestradores (`x.py`) — apenas substituir `except Exception` por `except PJePlusError`.

***

## 5. Refatoração #4 — Context Manager para ciclo de vida do driver

### Diagnóstico

Em `x.py` e outros orquestradores, o padrão é:

```python
# PADRÃO ATUAL
driver = criardriverPC(headless=headless)
try:
    login(driver)
    executar_fluxo(driver)
finally:
    finalizardriver(fix)(driver)  # pode ser esquecido
```

### Solução

Adicionar um context manager em `Fix/drivers/lifecycle.py` (arquivo já existente):

```python
# Fix/drivers/lifecycle.py  (ADIÇÃO ao arquivo existente, não substituição)
from contextlib import contextmanager
from Fix.log import logger

@contextmanager
def driver_session(driver_type: str, headless: bool = False):
    """
    Context manager que cria, entrega e finaliza o driver automaticamente.

    Uso:
        with driver_session("PC", headless=True) as driver:
            login(driver)
            executar_fluxo(driver)
        # driver.quit() acontece aqui, mesmo se houver exceção
    """
    _criadores = {
        "PC": lambda: criardriverPC(headless=headless),
        "VT": lambda: criardriverVT(headless=headless),
        "notebook": lambda: criardrivernotebook(headless=headless),
        "SISB_PC": lambda: criardriversisbpc(headless=headless),
        "SISB_notebook": lambda: criardriversisbnotebook(headless=headless),
    }
    if driver_type not in _criadores:
        raise ValueError(f"Tipo de driver desconhecido: {driver_type}")

    driver = None
    try:
        driver = _criadores[driver_type]()
        if driver is None:
            raise RuntimeError(f"Falha ao criar driver do tipo '{driver_type}'")
        yield driver
    finally:
        if driver is not None:
            try:
                finalizardriver(fix)(driver)
            except Exception as e:
                logger.warning(f"DRIVER:WARN — Falha ao finalizar driver: {e}")
```

Aplicar em `x.py`:

```python
# x.py — com context manager
from Fix.drivers.lifecycle import driver_session

def _ciclo_de_sessao(driver_type_str: str, fluxo: str) -> dict:
    with driver_session(driver_type_str, headless=headless) as driver:
        criarelog(driver)  # login
        inicio = datetime.now()
        resultado = _executar_fluxo(driver, fluxo)
        resultado["tempo"] = (datetime.now() - inicio).total_seconds()
        return resultado
    # driver.quit() acontece automaticamente aqui
```

### Regras de aplicação

- Adicionar `driver_session` ao final de `Fix/drivers/lifecycle.py` (não substituir o arquivo).
- Exportar `driver_session` em `Fix/__init__.py`.
- Aplicar em `x.py` primeiro; só depois nos scripts `1.py`, `1b.py`, `2.py`, `2b.py`.
- Manter as funções `criardriverPC`, `criardriverVT` etc. — o context manager as usa internamente.

***

## 6. Refatoração #5 — Scripts JS para arquivos `.js` separados

### Diagnóstico

Em módulos `SISB/`, `PEC/` e partes de `atos/comunicacaocoleta.py`, scripts JavaScript de 60-150 linhas
estão embutidos em strings Python:

```python
# PADRÃO ATUAL — JS inline em string Python
link_validacao_dom = driver.execute_script("""
    var spans = document.querySelectorAll('div[style*="display: block"] span');
    for (var i = 0; i < spans.length; i++) {
        var text = spans[i].textContent.trim();
        if (text.includes('Número do documento')) {
            var numero = text.split('Número do documento') [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_92083c6e-fc4e-43c7-a629-54a34ec21a3e/a6713304-23aa-44bf-878b-8722734d4dde/00dump.md).trim();
            if (numero) return 'https://pje.trt2.jus.br/pje/kz/validacao/' + numero + '?instancia=1';
        }
    }
    var links = document.querySelectorAll('a[href*="validacao"]');
    for (var i = 0; i < links.length; i++) {
        var href = links[i].getAttribute('href');
        if (href && href.includes('validacao')) return href;
    }
    return null;
""")
```

### Solução: arquivos `.js` versionados com loader em cache

#### Estrutura de pastas (nova)

```
Fix/
  scripts/
    __init__.py       ← loader com cache em memória
    observer_wait.js
    extrator_link_validacao.js
    preencher_campos.js

PEC/
  scripts/
    processar_reus.js
    extrair_tabela.js

atos/
  scripts/
    coleta_link_ato.js
```

#### `Fix/scripts/__init__.py` — loader com cache

```python
# Fix/scripts/__init__.py
"""Carrega scripts JS a partir de arquivos .js com cache em memória."""
from pathlib import Path

_cache: dict[str, str] = {}


def carregar_js(nome_arquivo: str, pasta: str | None = None) -> str:
    """
    Carrega o conteúdo de um arquivo .js, com cache em memória.

    Args:
        nome_arquivo: Nome do arquivo, ex: "observer_wait.js"
        pasta: Caminho absoluto da pasta. Se None, usa Fix/scripts/.

    Returns:
        str: Conteúdo do arquivo JS.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
    """
    if pasta is None:
        pasta = Path(__file__).parent

    chave = str(Path(pasta) / nome_arquivo)
    if chave not in _cache:
        caminho = Path(pasta) / nome_arquivo
        _cache[chave] = caminho.read_text(encoding="utf-8")
    return _cache[chave]


def limpar_cache_js() -> None:
    """Limpa o cache de scripts (útil em testes)."""
    _cache.clear()
```

#### Uso no código Python

```python
# atos/comunicacaocoleta.py — DEPOIS
from Fix.scripts import carregar_js
import os

_SCRIPTS_DIR = Path(__file__).parent / "scripts"

def _extrair_link_validacao_dom(driver) -> str | None:
    """Extrai link de validação do DOM via JS."""
    script = carregar_js("coleta_link_ato.js", _SCRIPTS_DIR)
    return driver.execute_script(script)
```

#### `atos/scripts/coleta_link_ato.js` — conteúdo extraído

```javascript
// atos/scripts/coleta_link_ato.js
// Extrai link de validação do DOM do PJe.
// Retorna string com URL ou null.
(function() {
    var spans = document.querySelectorAll('div[style*="display: block"] span');
    for (var i = 0; i < spans.length; i++) {
        var text = spans[i].textContent.trim();
        if (text.includes('Número do documento')) {
            var numero = text.split('Número do documento') [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_92083c6e-fc4e-43c7-a629-54a34ec21a3e/a6713304-23aa-44bf-878b-8722734d4dde/00dump.md).trim();
            if (numero) {
                return 'https://pje.trt2.jus.br/pje/kz/validacao/' + numero + '?instancia=1';
            }
        }
    }
    var links = document.querySelectorAll('a[href*="validacao"]');
    for (var i = 0; i < links.length; i++) {
        var href = links[i].getAttribute('href');
        if (href && href.includes('validacao')) return href;
    }
    return null;
})();
```

### Regras de aplicação

1. Criar `Fix/scripts/__init__.py` com o loader acima.
2. Para cada script JS inline encontrado, criar o arquivo `.js` correspondente na pasta mais próxima.
3. Substituir a string Python pelo `carregar_js(...)`.
4. **Não alterar a lógica JS** — copiar exatamente, apenas mover para arquivo.
5. Scripts com f-strings Python (ex: `f"...{variavel}..."`) devem ser tratados separadamente:
   usar `script.replace("__VARIAVEL__", str(variavel))` em vez de f-string, ou passar como argumento JS:
   ```python
   script = carregar_js("preencher_campos.js", _SCRIPTS_DIR)
   driver.execute_script(script, valor, seletor)  # argumentos via arguments, arguments [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_92083c6e-fc4e-43c7-a629-54a34ec21a3e/a6713304-23aa-44bf-878b-8722734d4dde/00dump.md)