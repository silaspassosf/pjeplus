"""
probe_network.py — Interceptador de rede para Playwright/Selenium
Grava TODAS as requisições (fetch/XHR) durante execução de teste.
Estrutura: agrupa por endpoint template, coleta payloads, respostas, timing.

Uso:
    from probe_network import ProbeNetwork
    probe = ProbeNetwork(driver)
    probe.start()
    
    # ... execute seu teste ...
    
    resultado = probe.stop()
    # resultado = {
    #     'endpoints': [...],
    #     'timeline': [...],
    #     'estatisticas': {...},
    #     'viabilidade_api': {...}
    # }
    
    probe.salvar_relatorio('probe_relatorio.json')
"""

import json
import re
import time
from typing import Any, Dict, List, Optional
from collections import defaultdict
from datetime import datetime


class ProbeNetwork:
    """Intercepta requisições HTTP durante execução de teste."""

    def __init__(self, driver):
        self.driver = driver
        self.ativo = False
        self.inicio = None
        self.requisicoes: List[Dict[str, Any]] = []
        self.endpoints: Dict[str, Dict[str, Any]] = {}
        self.js_injetado = False

    def _normalizar_url(self, url: str) -> str:
        """Remove IDs/hashes de URL para criar template."""
        # Remove query string
        url = re.sub(r'[?#].*$', '', url)
        # Substitui números grandes (IDs)
        url = re.sub(r'/\d{5,}', '/{id}', url)
        # Substitui hashes hexadecimais
        url = re.sub(r'/[a-f0-9]{8,}', '/{hash}', url, flags=re.IGNORECASE)
        # Remove domínio, fica só path
        url = re.sub(r'^https?://[^/]+', '', url)
        return url

    def _agrupar_requisicao(self, metodo: str, url: str, status: int, 
                            tamanho_req: int, tamanho_resp: int, 
                            tempo_ms: float, request_body: Optional[str] = None,
                            response_body: Optional[str] = None):
        """Agrupa requisição em endpoint template."""
        template = self._normalizar_url(url)
        chave = f"{metodo.upper()} {template}"

        if chave not in self.endpoints:
            self.endpoints[chave] = {
                'metodo': metodo.upper(),
                'template': template,
                'url_exemplo': url,
                'status_codes': {},
                'chamadas': 0,
                'tamanho_req_total': 0,
                'tamanho_resp_total': 0,
                'tempo_total_ms': 0,
                'tempo_min_ms': float('inf'),
                'tempo_max_ms': 0,
                'payloads_exemplo': [],
                'respostas_exemplo': [],
                'critico': self._eh_critico(template),
            }
        
        ep = self.endpoints[chave]
        ep['status_codes'][status] = ep['status_codes'].get(status, 0) + 1
        ep['chamadas'] += 1
        ep['tamanho_req_total'] += tamanho_req
        ep['tamanho_resp_total'] += tamanho_resp
        ep['tempo_total_ms'] += tempo_ms
        ep['tempo_min_ms'] = min(ep['tempo_min_ms'], tempo_ms)
        ep['tempo_max_ms'] = max(ep['tempo_max_ms'], tempo_ms)

        # Coleta exemplo de payload (primeiros 2)
        if request_body and len(ep['payloads_exemplo']) < 2:
            try:
                ep['payloads_exemplo'].append(json.loads(request_body)[:200] if isinstance(request_body, str) else request_body)
            except:
                ep['payloads_exemplo'].append(f"<{len(request_body)} bytes>")

        # Coleta exemplo de resposta (primeiros 2)
        if response_body and len(ep['respostas_exemplo']) < 2:
            try:
                parsed = json.loads(response_body) if isinstance(response_body, str) else response_body
                # Simplifica resposta: só estrutura principal + sample de arrays
                if isinstance(parsed, dict):
                    simplified = {k: (f"[{len(v)} items]" if isinstance(v, list) else str(v)[:100]) 
                                 for k, v in parsed.items()}
                    ep['respostas_exemplo'].append(simplified)
                else:
                    ep['respostas_exemplo'].append(f"<{type(parsed).__name__} {len(str(parsed))} chars>")
            except:
                ep['respostas_exemplo'].append(f"<{len(response_body) if response_body else 0} bytes>")

    def _eh_critico(self, template: str) -> bool:
        """Heurística: identifica endpoints críticos."""
        criticos = [
            'sisbajud',
            'minuta',
            'processo',
            'documentos',
            'bloqueio',
            'ordem',
            'api',
        ]
        return any(c in template.lower() for c in criticos)

    def start(self):
        """Inicia interceptação de rede via JavaScript."""
        if self.js_injetado or self.ativo:
            return
        
        self.ativo = True
        self.inicio = time.time()
        self.requisicoes = []
        self.endpoints = {}

        js_probe = """
        (function() {
            if (window.__probeNetwork) return;
            window.__probeNetwork = {
                requisicoes: [],
                origFetch: null,
                origOpen: null,
                origSend: null
            };

            var probe = window.__probeNetwork;
            var t0 = Date.now();

            probe.origFetch = window.fetch;
            window.fetch = function(url, init) {
                var metodo = (init && init.method) || 'GET';
                var t_inicio = Date.now();
                var promise = probe.origFetch.apply(this, arguments);
                
                promise.then(function(resp) {
                    var t_duracao = Date.now() - t_inicio;
                    resp.clone().text().then(function(texto) {
                        probe.requisicoes.push({
                            metodo: metodo,
                            url: url instanceof Request ? url.url : url,
                            status: resp.status,
                            tamanho_resp: texto.length,
                            tempo_ms: t_duracao,
                            tipo: 'fetch',
                            corpo_resp: texto.slice(0, 2000),
                            relativo_ms: t_inicio - t0
                        });
                    }).catch(function() {
                        probe.requisicoes.push({
                            metodo: metodo,
                            url: url instanceof Request ? url.url : url,
                            status: resp.status,
                            tamanho_resp: 0,
                            tempo_ms: t_duracao,
                            tipo: 'fetch',
                            corpo_resp: null,
                            relativo_ms: t_inicio - t0
                        });
                    });
                }).catch(function(err) {
                    probe.requisicoes.push({
                        metodo: metodo,
                        url: url instanceof Request ? url.url : url,
                        status: 0,
                        erro: err.message,
                        tempo_ms: Date.now() - t_inicio,
                        tipo: 'fetch',
                        relativo_ms: t_inicio - t0
                    });
                });
                
                return promise;
            };

            probe.origOpen = XMLHttpRequest.prototype.open;
            probe.origSend = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function(metodo, url) {
                this.__probe_info = { metodo: metodo, url: url, t0: Date.now() };
                return probe.origOpen.apply(this, arguments);
            };

            XMLHttpRequest.prototype.send = function(corpo) {
                var info = this.__probe_info;
                var t_inicio = info.t0;
                var xhr = this;

                this.addEventListener('loadend', function() {
                    var t_duracao = Date.now() - t_inicio;
                    probe.requisicoes.push({
                        metodo: info.metodo,
                        url: info.url,
                        status: xhr.status,
                        tamanho_resp: xhr.responseText ? xhr.responseText.length : 0,
                        tempo_ms: t_duracao,
                        tipo: 'xhr',
                        corpo_resp: xhr.responseText ? xhr.responseText.slice(0, 2000) : null,
                        relativo_ms: t_inicio - t0
                    });
                });

                return probe.origSend.call(this, corpo);
            };

            console.log('[PROBE_NETWORK] interceptador ativo');
        })();
        """

        try:
            # Playwright
            if hasattr(self.driver, 'page'):
                self.driver.page.evaluate(js_probe)
            # Fallback legacy
            elif hasattr(self.driver, 'execute_script'):
                getattr(self.driver, 'execute_script')(js_probe)
            self.js_injetado = True
        except Exception as e:
            print(f"[PROBE] Erro ao injetar JS: {e}")

    def stop(self) -> Dict[str, Any]:
        """Para interceptação e coleta resultados."""
        if not self.ativo:
            return {'erro': 'probe não estava ativo'}

        self.ativo = False

        # Coleta dados da página
        try:
            if hasattr(self.driver, 'page'):
                dados = self.driver.page.evaluate("window.__probeNetwork?.requisicoes || []")
            else:
                fn_exec = getattr(self.driver, 'execute_script', lambda s: [])
                dados = fn_exec("return window.__probeNetwork?.requisicoes || []")
        except Exception as e:
            print(f"[PROBE] Erro ao coletar dados: {e}")
            dados = []

        # Processa requisições
        for req in dados:
            self._agrupar_requisicao(
                metodo=req.get('metodo', 'GET'),
                url=req.get('url', ''),
                status=req.get('status', 0),
                tamanho_req=0,  # XHR/fetch não expõe tamanho de request
                tamanho_resp=req.get('tamanho_resp', 0),
                tempo_ms=req.get('tempo_ms', 0),
                response_body=req.get('corpo_resp')
            )
            self.requisicoes.append(req)

        tempo_total = time.time() - self.inicio

        # Estatísticas
        stats = {
            'total_requisicoes': len(self.requisicoes),
            'total_endpoints_unicos': len(self.endpoints),
            'tempo_total_segundos': tempo_total,
            'endpoints_criticos': sum(1 for ep in self.endpoints.values() if ep.get('critico')),
            'endpoints_opcionais': sum(1 for ep in self.endpoints.values() if not ep.get('critico')),
            'taxa_sucesso': sum(1 for ep in self.endpoints.values() 
                               if 200 in ep['status_codes']) / len(self.endpoints) if self.endpoints else 0,
        }

        # Viabilidade API
        viabilidade = self._analisar_viabilidade()

        return {
            'timestamp': datetime.now().isoformat(),
            'duracao_segundos': tempo_total,
            'endpoints': sorted(
                self.endpoints.values(),
                key=lambda x: x['chamadas'],
                reverse=True
            ),
            'timeline': self.requisicoes,
            'estatisticas': stats,
            'viabilidade_api': viabilidade,
            'recomendacoes': self._gerar_recomendacoes()
        }

    def _analisar_viabilidade(self) -> Dict[str, Any]:
        """Analisa viabilidade de implementação via API pura."""
        criticos = [ep for ep in self.endpoints.values() if ep['critico']]
        todos = list(self.endpoints.values())

        falhas = sum(1 for ep in criticos if not any(s in [200, 201] for s in ep['status_codes'].keys()))
        
        score = 100
        motivos = []

        if falhas > 0:
            score -= 30
            motivos.append(f"{falhas} endpoint(s) crítico(s) com falhas")

        if any('/minuta' in ep['template'] for ep in criticos):
            # SISBAJUD tem formulário renderizado — pode ser complicado
            score -= 20
            motivos.append("SISBAJUD detectado (minuta: formulário renderizado)")

        if len(criticos) > 5:
            score -= 10
            motivos.append(f"Muitos endpoints críticos ({len(criticos)})")

        # Endpoints com XMLHttpRequest muitas vezes indicam dados criados server-side
        xhr_count = sum(1 for req in self.requisicoes if req.get('tipo') == 'xhr')
        if len(self.requisicoes) > 0 and xhr_count / len(self.requisicoes) > 0.7:
            score -= 5
            motivos.append("Predominância de XHR (dados dinâmicos)")

        return {
            'score': max(0, min(100, score)),
            'viavel': score >= 60,
            'motivos': motivos,
            'endpoints_criticos_total': len(criticos),
            'endpoints_dependencias': self._detectar_dependencias()
        }

    def _detectar_dependencias(self) -> List[Dict[str, str]]:
        """Detecta sequências de chamadas (dependências)."""
        deps = []
        for i, req in enumerate(self.requisicoes[:-1]):
            prox = self.requisicoes[i + 1]
            # Se diferença < 2s e URLs diferentes, possível dependência
            if abs(req.get('relativo_ms', 0) - prox.get('relativo_ms', 0)) < 2000:
                if req['url'] != prox['url']:
                    deps.append({
                        'primeiro': f"{req['metodo']} {self._normalizar_url(req['url'])}",
                        'seguinte': f"{prox['metodo']} {self._normalizar_url(prox['url'])}",
                        'intervalo_ms': prox.get('relativo_ms', 0) - req.get('relativo_ms', 0)
                    })
        return deps[:10]  # Top 10

    def _gerar_recomendacoes(self) -> List[str]:
        """Recomendações de próximas ações."""
        recomendacoes = []

        if not self.endpoints:
            recomendacoes.append("Nenhum endpoint detectado — verifique se o probe foi ligado antes do teste")
            return recomendacoes

        criticos = [ep for ep in self.endpoints.values() if ep['critico']]
        
        recomendacoes.append(f"Implementar primeiro: {len(criticos)} endpoints críticos")
        
        # Endpoints com POST/PUT (logicamente mutadores) são mais importantes
        mutadores = [ep for ep in criticos if ep['metodo'] in ['POST', 'PUT', 'PATCH']]
        if mutadores:
            recomendacoes.append(f"Prioridade: {len(mutadores)} endpoints mutadores (POST/PUT/PATCH)")

        # Verificar se há endpoints SISBAJUD
        if any('sisbajud' in ep['template'].lower() for ep in criticos):
            recomendacoes.append("AVISO: SISBAJUD detectado — pode ter formulário renderizado lado cliente")

        # Performance
        lentos = [ep for ep in self.endpoints.values() if ep.get('tempo_max_ms', 0) > 5000]
        if lentos:
            recomendacoes.append(f"Endpoints lentos (>5s): {len(lentos)} — considere paralelização/caching")

        recomendacoes.append("Próximo passo: exportar probe_relatorio.json e revisar endpoints críticos manualmente")

        return recomendacoes

    def salvar_relatorio(self, caminho: str):
        """Salva relatório em JSON."""
        resultado = self.stop()
        try:
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2, default=str)
            print(f"[PROBE] Relatório salvo em {caminho}")
        except Exception as e:
            print(f"[PROBE] Erro ao salvar relatório: {e}")

    def relatorio_texto(self) -> str:
        """Gera relatório em texto legível."""
        resultado = self.stop()
        
        # Se houve erro na coleta, retorna relatório simples
        if 'erro' in resultado:
            return f"[PROBE ERROR] {resultado['erro']}"
        
        linhas = [
            "=" * 80,
            "PJe PROBE — Relatório de Endpoints",
            "=" * 80,
            f"Timestamp: {resultado.get('timestamp', 'N/A')}",
            f"Duração: {resultado.get('duracao_segundos', 0):.1f}s",
            f"Total de requisições: {resultado.get('estatisticas', {}).get('total_requisicoes', 0)}",
            f"Endpoints únicos: {resultado.get('estatisticas', {}).get('total_endpoints_unicos', 0)}",
            f"  - Críticos: {resultado.get('estatisticas', {}).get('endpoints_criticos', 0)}",
            f"  - Opcionais: {resultado.get('estatisticas', {}).get('endpoints_opcionais', 0)}",
            f"Taxa de sucesso: {resultado.get('estatisticas', {}).get('taxa_sucesso', 0)*100:.0f}%",
            "",
            "=" * 80,
            "ENDPOINTS (por frequência)",
            "=" * 80,
        ]

        for ep in resultado['endpoints']:
            marker = "⚠" if ep['critico'] else "○"
            status_str = ", ".join(f"{k}x{v}" for k, v in sorted(ep['status_codes'].items()))
            media_tempo = ep['tempo_total_ms'] / ep['chamadas'] if ep['chamadas'] else 0
            
            linhas.append(f"\n{marker} [{ep['metodo']}] {ep['chamadas']}x  {ep['template']}")
            linhas.append(f"   Status: {status_str}")
            linhas.append(f"   Tempo: {media_tempo:.0f}ms média ({ep['tempo_min_ms']:.0f}–{ep['tempo_max_ms']:.0f}ms)")
            linhas.append(f"   Dados: {ep['tamanho_resp_total']} bytes resposta")
            if ep['payloads_exemplo']:
                linhas.append(f"   Exemplo request: {ep['payloads_exemplo'][0]}")
            if ep['respostas_exemplo']:
                linhas.append(f"   Exemplo response: {ep['respostas_exemplo'][0]}")

        linhas.extend([
            "",
            "=" * 80,
            "VIABILIDADE DE API",
            "=" * 80,
            f"Score: {resultado['viabilidade_api']['score']}/100",
            f"Viável para headless: {'✓ SIM' if resultado['viabilidade_api']['viavel'] else '✗ NÃO'}",
        ])

        if resultado['viabilidade_api']['motivos']:
            linhas.append("\nMotivos:")
            for motivo in resultado['viabilidade_api']['motivos']:
                linhas.append(f"  - {motivo}")

        linhas.extend([
            "",
            "RECOMENDAÇÕES",
        ])
        for rec in resultado['recomendacoes']:
            linhas.append(f"  → {rec}")

        return "\n".join(linhas)
