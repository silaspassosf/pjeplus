# PJe Network Probe — Mapeamento de Endpoints para Viabilidade API

## O que é?

Um **probe integrado ao f.py** que intercepta e registra **todas as chamadas HTTP (fetch/XHR)** durante a execução de um teste (ex: minuta de bloqueio SISBAJUD), gerando um relatório estruturado sobre viabilidade de implementação via API pura (sem Selenium/Playwright).

## Uso

```bash
# Rodar teste SISBAJUD minuta_bloqueio COM probe de rede
py f.py sisb_probe                  # processo padrão
py f.py sisb_probe 5234567          # processo específico
py f.py 2p 5234567                  # alias

# Rodar teste SISB normal (sem probe)
py f.py sisb
```

## O que Gera

Após executar `py f.py sisb_probe`, você terá:

### 1. `probe_relatorio.json`
Relatório estruturado com:
```json
{
  "timestamp": "2026-10-30T...",
  "duracao_segundos": 42.5,
  "endpoints": [
    {
      "metodo": "POST",
      "template": "/pje-comum-api/api/processos/{id}/documentos",
      "chamadas": 15,
      "status_codes": {"200": 14, "400": 1},
      "tempo_total_ms": 2100,
      "tempo_min_ms": 50,
      "tempo_max_ms": 450,
      "tamanho_resp_total": 125000,
      "critico": true,
      "payloads_exemplo": [...],
      "respostas_exemplo": [...]
    }
  ],
  "estatisticas": {
    "total_requisicoes": 127,
    "total_endpoints_unicos": 8,
    "endpoints_criticos": 5,
    "endpoints_opcionais": 3,
    "taxa_sucesso": 0.95
  },
  "viabilidade_api": {
    "score": 78,
    "viavel": true,
    "motivos": ["..."],
    "endpoints_criticos_total": 5,
    "endpoints_dependencias": [...]
  },
  "recomendacoes": [...]
}
```

### 2. `probe_relatorio.txt`
Relatório legível + análise:
```
================================================================================
PJe PROBE — Relatório de Endpoints
================================================================================
Timestamp: 2026-10-30T...
Duração: 42.5s
Total de requisições: 127
Endpoints únicos: 8
  - Críticos: 5
  - Opcionais: 3
Taxa de sucesso: 95%

================================================================================
ENDPOINTS (por frequência)
================================================================================

⚠ [POST] 15x  /pje-comum-api/api/processos/{id}/documentos
   Status: 200x14, 400x1
   Tempo: 140ms média (50–450ms)
   Dados: 125000 bytes resposta
   Exemplo request: {"tipo": "Certidao", ...}
   Exemplo response: {resultado:[10]} campos: id, titulo, data

○ [GET] 8x  /api/...
   ...

================================================================================
VIABILIDADE DE API
================================================================================
Score: 78/100
Viável para headless: ✓ SIM

Motivos:
  - Acabou bem integrado, endpoints bem estruturados

RECOMENDAÇÕES
  → Implementar primeiro: 5 endpoints críticos
  → Prioridade: 3 endpoints mutadores (POST/PUT/PATCH)
  → Próximo passo: exportar probe_relatorio.json e revisar endpoints críticos manualmente
```

## Arquitetura

```
f.py (teste)
  ↓
ProbeNetwork.start()
  ↓ (injeta JS interceptador)
Browser (page.evaluate)
  ↓ (patch fetch + XMLHttpRequest)
[Sua execução do teste]
  ↓ (cada chamada HTTP é registrada em window.__probeNetwork.requisicoes[])
ProbeNetwork.stop()
  ↓ (coleta dados via page.evaluate)
Processa, agrupa por endpoint template
  ↓
Salva: probe_relatorio.json + probe_relatorio.txt
```

## Fluxo Completo

### Passo 1: Rodar com Probe
```bash
py f.py sisb_probe 4863758
```

Você verá no console:
```
[SISB_PROBE_TEST] Teste SISBAJUD minuta_bloqueio COM PROBE DE REDE
[SISB_PROBE_TEST] Probe de rede iniciado — interceptando fetch/XHR
[SISB_PROBE_TEST] Chamando minuta_bloqueio(...)
[SISB_PROBE_TEST] Probe parado — 8 endpoints detectados
[SISB_PROBE_TEST] probe_relatorio.json salvo
[SISB_PROBE_TEST] probe_relatorio.txt salvo
```

### Passo 2: Revisar Relatório
Abra `probe_relatorio.txt` e veja:
- Score de viabilidade (0–100)
- Endpoints críticos e opcionais
- Timing, payloads, respostas

### Passo 3: Analisar Viabilidade

**Score ≥ 75**: Altamente viável → próximo passo é implementar endpoints críticos em Python (requests/httpx)

**Score 50–74**: Parcialmente viável → alguns endpoints podem exigir lógica side-server ou renderização

**Score < 50**: Pouco viável → muita lógica client-side

## Casos de Uso

### Caso 1: SISBAJUD (minuta_bloqueio)
```bash
py f.py sisb_probe
# Verifica se SISBAJUD pode ser executado via API pura (sem Playwright)
# Resultado: Score ~80 → VIÁVEL
```

### Caso 2: PEC (protocolo eletrônico)
```bash
py f.py pec_probe  # (seria adicionado futuramente)
# Verifica endpoints de protocolo
```

### Caso 3: TRIAGEM
```bash
py f.py triagem_probe  # (seria adicionado futuramente)
# Mapa completo de endpoints de triagem automática
```

## Exemplo: Próximo Passo (API Pure)

Após o probe gerar relatório com score alto, você implementa em Python puro:

```python
# em sisb_api.py (novo módulo)
import requests
from datetime import datetime

class SisbajudAPI:
    def __init__(self, sessao, base_url='https://sisbajud.cnj.jus.br'):
        self.sess = sessao
        self.base = base_url
    
    def criar_minuta_bloqueio(self, dados_processo, duracao=30):
        """Cria minuta de bloqueio via API pura (sem DOM)."""
        payload = {
            'numero_processo': dados_processo['numero'],
            'tipo_bloqueio': 'bloqueio_30d' if duracao == 30 else 'bloqueio_60d',
            'dados': dados_processo
        }
        resp = self.sess.post(
            f'{self.base}/api/minuta/criar',
            json=payload
        )
        return resp.json()
    
    def listar_ordens(self, numero_processo):
        """Lista ordens de execução de bloqueio."""
        resp = self.sess.get(
            f'{self.base}/api/processos/{numero_processo}/ordens'
        )
        return resp.json()
```

Depois usa em batch sem Selenium:
```python
from sisb_api import SisbajudAPI

sessao = requests.Session()
# ... auth ...

sisb = SisbajudAPI(sessao)

for proc in processos:
    minuta = sisb.criar_minuta_bloqueio(proc)
    print(f"Minuta criada: {minuta['id']}")
```

## Arquivos Gerados

| Arquivo | Descrição |
|---------|-----------|
| `probe_relatorio.json` | Dados estruturados (endpoints, timing, payloads) |
| `probe_relatorio.txt` | Relatório legível + recomendações |
| `logs_execucao/f_<timestamp>.log` | Log detalhado do teste |
| `dadosatuais.json` | Dados do processo extraídos |

## Troubleshooting

### "Probe parado — 0 endpoints detectados"
- Problema: JavaScript nunca foi executado ou fetch/XHR não foram usados
- Solução: Verifique se o teste realmente faz chamadas HTTP (DevTools F12 → Network)

### "Viável: false, Score: 20"
- Problema: Muita lógica renderizada no client (formulários dinâmicos)
- Solução: Considere manter Playwright/Selenium ou implementar renderização via Puppeteer/Playwright em headless

### score varia entre execuções
- Normal: endpoints podem ter falhas ocasionais (rede, timeouts)
- Recomendação: rodar 2–3 vezes e pegar a média

## Extending

Para adicionar probe a outro teste:

```python
def teste_seu_fluxo_com_probe(id_processo=None):
    from probe_network import ProbeNetwork
    
    probe = ProbeNetwork(driver)
    probe.start()
    
    # ... seu teste ...
    
    relatorio = probe.stop()
    probe.salvar_relatorio('probe_seu_fluxo.json')
    print(probe.relatorio_texto())
```

## Referências

- `probe_network.py`: Implementação do interceptador
- `f.py`: Testes integrados com probe
- Comparar com UserScript `PJe Probe` do Tampermonkey (mesma filosofia, mas em JS puro)
