# API do Painel Global — Filtros por Fase + Chips

## Visão Geral

O **Painel Global** (`/pjekz/painel/global/todos/lista-processos`) usa a API:

```
POST|PATCH /pje-comum-api/api/agrupamentotarefas/{id}/processos
```

com autenticação XSRF (token lido de `document.cookie`).

---

## Estrutura Atual (apiaud.py / Triagem/api.py)

### Payload (body) da Chamada

```javascript
{
    pagina: 1,
    tamanhoPagina: 100,
    subCaixa: null,                      // chips: "Sub-caixa"
    tipoAtividade: null,                 // chips: "Tipo de Atividade"
    processos: null,                     // lista de números de processo (filtro adicional)
    nomeConclusoMagistrado: null,        // chips: "Nome do Concluso Magistrado"
    usuarioResponsavel: null,            // chips: "Usuário Responsável"
    faseProcessualString: null,          // chips: "Fase Processual"
    numeroProcesso: null,                // número do processo (filtro simples)
    juizoDigital: null                   // chips: "Juízo Digital" (true|false|null)
}
```

**Observação:** Todos os campos de filtro aceitam:
- `null` — sem filtro
- `string` — valor único (ex: `"Conhecimento"`, `"Execução"`)
- `array` — múltiplos valores (ex: `["Conhecimento", "Execução"]`)

---

## Valores de Fase Processual (`faseProcessualString`)

Baseado em observação no código (`00dump.md`, `gigs-plugin.js`):

| Valor | Descrição |
|-------|-----------|
| `"Conhecimento"` | Fase de conhecimento (análise do mérito) |
| `"Liquidação"` | Fase de liquidação (fixação do valor) |
| `"Execução"` | Fase de execução (cumprimento da sentença) |
| `"Cautelar"` | Ação cautelar |
| `"Recursal"` | Fase recursal |

---

## Exemplos de Chamadas

### 1. Todos os processos (sem filtro)

```javascript
// JavaScript (execute_async_script)
const xsrf = document.cookie.split(';')
    .map(c => c.trim())
    .find(c => c.toLowerCase().startsWith('xsrf-token='))
    ?.split('=').slice(1).join('=') || '';

fetch(location.origin + '/pje-comum-api/api/agrupamentotarefas/10/processos', {
    method: 'PATCH',
    credentials: 'include',
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-XSRF-TOKEN': xsrf
    },
    body: JSON.stringify({
        pagina: 1,
        tamanhoPagina: 100,
        subCaixa: null,
        tipoAtividade: null,
        processos: null,
        nomeConclusoMagistrado: null,
        usuarioResponsavel: null,
        faseProcessualString: null,
        numeroProcesso: null,
        juizoDigital: null
    })
})
    .then(r => r.json())
    .then(d => console.log('Resultado:', d))
    .catch(e => console.error('Erro:', e));
```

### 2. Apenas processos em fase de Execução

```javascript
const payload = {
    pagina: 1,
    tamanhoPagina: 100,
    faseProcessualString: "Execução",  // ← FILTRO DE FASE
    subCaixa: null,
    tipoAtividade: null,
    processos: null,
    nomeConclusoMagistrado: null,
    usuarioResponsavel: null,
    numeroProcesso: null,
    juizoDigital: null
};

// ... fetch com XSRF (veja exemplo 1)
```

### 3. Executar filtrado por fase + chip (sub-caixa + tipo de atividade)

```javascript
const payload = {
    pagina: 1,
    tamanhoPagina: 100,
    faseProcessualString: "Execução",             // ← FASE
    subCaixa: ["Sub-caixa 1", "Sub-caixa 2"],   // ← CHIP (múltiplos)
    tipoAtividade: ["Procuração"],               // ← CHIP
    processos: null,
    nomeConclusoMagistrado: null,
    usuarioResponsavel: null,
    numeroProcesso: null,
    juizoDigital: null
};

// ... fetch com XSRF
```

### 4. Juízo Digital (chip booleano)

```javascript
const payload = {
    pagina: 1,
    tamanhoPagina: 100,
    juizoDigital: true,  // ← Apenas processos em juízo digital
    // ... resto null
};
```

---

## Respondedor (Response Body)

O servidor retorna um objeto JSON com a lista de processos:

```json
{
    "resultado": [
        {
            "id": 123456,
            "numeroProcesso": "0001234-56.2024.5.12.0059",
            "classeJudicial": {
                "sigla": "ATOrd",
                "descricao": "Ação Trabalhista Ordinária"
            },
            "faseProcessual": "Execução",
            "labelFaseProcessual": "Execução",
            "juizoDigital": false,
            "dataProximaAudiencia": null,
            "tarefa": {
                "id": 456,
                "nome": "Triagem Inicial",
                "descricao": "Triagem Inicial"
            },
            "orgaoJulgador": {
                "id": 23,
                "descricao": "VARA DO TRABALHO DE PALHOÇA",
                "sigla": "PCA"
            }
            // ... mais campos
        }
    ],
    "totalRegistros": 150,
    "qtdPaginas": 2,
    "paginaAtual": 1
}
```

---

## Uso em Python (Selenium + execute_async_script)

Baseado em `apiaud.py` / `Triagem/api.py`:

```python
from selenium.webdriver.remote.webdriver import WebDriver

_JS_FETCH_PAINEL = """
const payload   = arguments[0];
const callback  = arguments[1];

var xsrfCookie = document.cookie.split(';')
    .map(function(c) { return c.trim(); })
    .find(function(c) { return c.toLowerCase().indexOf('xsrf-token=') === 0; });
var xsrf = xsrfCookie ? xsrfCookie.split('=').slice(1).join('=') : '';

(async function() {
    var base = location.origin;
    var url  = base + '/pje-comum-api/api/agrupamentotarefas/10/processos';
    
    try {
        var r = await fetch(url, {
            method: 'PATCH',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-XSRF-TOKEN': xsrf
            },
            body: JSON.stringify(payload)
        });
        
        if (!r.ok) {
            callback({ erro: 'HTTP_' + r.status });
            return;
        }
        
        var data = await r.json();
        callback({ resultado: data.resultado || data, total: data.totalRegistros });
    } catch(e) {
        callback({ erro: 'ASYNC_ERR: ' + e.message });
    }
})();
"""

def buscar_painel_com_filtros(driver: WebDriver, fase: str = None, sub_caixa: list = None, 
                              tipo_atividade: list = None, juizo_digital: bool = None) -> dict:
    """Busca processos do Painel com filtros.
    
    Args:
        driver: WebDriver Selenium
        fase: "Conhecimento", "Execução", "Liquidação" ou None
        sub_caixa: lista de strings ou None
        tipo_atividade: lista de strings ou None
        juizo_digital: True, False ou None
    
    Returns:
        dict com campos 'resultado' (lista de processos) e 'total'
    """
    
    payload = {
        'pagina': 1,
        'tamanhoPagina': 100,
        'subCaixa': sub_caixa,
        'tipoAtividade': tipo_atividade,
        'processos': None,
        'nomeConclusoMagistrado': None,
        'usuarioResponsavel': None,
        'faseProcessualString': fase,
        'numeroProcesso': None,
        'juizoDigital': juizo_digital
    }
    
    driver.set_script_timeout(120)
    try:
        res = driver.execute_async_script(_JS_FETCH_PAINEL, payload)
    finally:
        try:
            driver.set_script_timeout(30)
        except:
            pass
    
    return res or {}

# Exemplo de uso:
# processos = buscar_painel_com_filtros(driver, fase="Execução", sub_caixa=["Minha sub-caixa"])
# for proc in processos.get('resultado', []):
#     print(f"{proc['numeroProcesso']} - {proc['faseProcessual']}")
```

---

## Uso em curl (com cookies exportados)

```bash
# 1. Obter XSRF-TOKEN do navegador (inspecionar cookies em DevTools)
# 2. Exportar cookies da sessão do navegador (por exemplo via cookie extension)
# 3. Usar curl com --cookie-jar / -b para enviar cookies

XSRF_TOKEN="<valor-do-cookie-xsrf>"
COOKIES="<arquivo-de-cookies-ou-string>"

curl -X PATCH \
  'https://pje.trt2.jus.br/pje-comum-api/api/agrupamentotarefas/10/processos' \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "X-XSRF-TOKEN: $XSRF_TOKEN" \
  -b "$COOKIES" \
  -d '{
    "pagina": 1,
    "tamanhoPagina": 100,
    "faseProcessualString": "Execução",
    "subCaixa": null,
    "tipoAtividade": null,
    "processos": null,
    "nomeConclusoMagistrado": null,
    "usuarioResponsavel": null,
    "numeroProcesso": null,
    "juizoDigital": null
  }'
```

---

## Referências no Projeto

- **Implementação pronta:** [Triagem/api.py](Triagem/api.py) `_JS_BUSCAR_TRIAGEM`
- **Exemplo completo:** [apiaud.py](apiaud.py) `_JS_BUSCAR_TRIAGEM` com loop de paginação
- **Documentação de XSRF:** [api/apis.md](apis.md) seção 0 (Autenticação)
- **Probe de diagnóstico:** [scripts/probe_painel_api_iife.js](https://pje.trt2.jus.br/pjekz/painel/global/todos/lista-processos) (cole no console)

---

## Resumo

| Aspecto | Detalhes |
|--------|----------|
| **Endpoint** | `PATCH /pje-comum-api/api/agrupamentotarefas/{id}/processos` |
| **Autenticação** | XSRF-TOKEN (via `document.cookie`) |
| **Filtros disponíveis** | `faseProcessualString`, `subCaixa`, `tipoAtividade`, `usuarioResponsavel`, `juizoDigital`, etc. |
| **Valores de fase** | "Conhecimento", "Execução", "Liquidação", "Cautelar", "Recursal" |
| **Paginação** | `pagina`, `tamanhoPagina` (recomendado: 100) |
| **Método recomendado** | `execute_async_script` com `fetch` (Selenium) ou `requests.patch` + XSRF manual |
| **Exemplo pronto** | [Triagem/api.py](Triagem/api.py), [apiaud.py](apiaud.py) |
