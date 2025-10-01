# monitor.py
# Módulo de monitoramento e análise de performance para execução sequencial
# Gera relatório "EXECUCAO TOTAL" com hipóteses de otimização

import time
import os
from datetime import datetime
import json

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class MonitorExecucao:
    """Monitor de execução que coleta métricas e gera relatórios de otimização"""

    def __init__(self):
        self.inicio_execucao = None
        self.fim_execucao = None
        self.metricas_etapas = {}
        self.metricas_sistema = []
        self.logs_seletores = []
        self.hipoteses_otimizacao = []

    def iniciar_monitoramento(self):
        """Inicia o monitoramento da execução total"""
        self.inicio_execucao = time.time()
        print("[MONITOR] 📊 Iniciando monitoramento da execução total...")

    def finalizar_monitoramento(self):
        """Finaliza o monitoramento e gera relatório"""
        self.fim_execucao = time.time()
        self._gerar_relatorio_execucao_total()

    def registrar_inicio_etapa(self, nome_etapa):
        """Registra o início de uma etapa"""
        if nome_etapa not in self.metricas_etapas:
            self.metricas_etapas[nome_etapa] = {}
        self.metricas_etapas[nome_etapa]['inicio'] = time.time()
        self.metricas_etapas[nome_etapa]['metricas_sistema'] = self._coletar_metricas_sistema()
        print(f"[MONITOR] ⏱️ Iniciando etapa: {nome_etapa}")

    def registrar_fim_etapa(self, nome_etapa, sucesso=True):
        """Registra o fim de uma etapa"""
        if nome_etapa in self.metricas_etapas:
            self.metricas_etapas[nome_etapa]['fim'] = time.time()
            self.metricas_etapas[nome_etapa]['duracao'] = (
                self.metricas_etapas[nome_etapa]['fim'] - self.metricas_etapas[nome_etapa]['inicio']
            )
            self.metricas_etapas[nome_etapa]['sucesso'] = sucesso
            print(f"[MONITOR] ✅ Etapa {nome_etapa} concluída em {self.metricas_etapas[nome_etapa]['duracao']:.2f}s")

    def registrar_log_seletor(self, script, seletor, sucesso, contexto=""):
        """Registra uso de seletor para análise de otimização"""
        log_entry = {
            'timestamp': time.time(),
            'script': script,
            'seletor': seletor,
            'sucesso': sucesso,
            'contexto': contexto
        }
        self.logs_seletores.append(log_entry)

    def _coletar_metricas_sistema(self):
        """Coleta métricas do sistema"""
        try:
            if PSUTIL_AVAILABLE:
                return {
                    'cpu_percent': psutil.cpu_percent(interval=0.1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'memory_used_mb': psutil.virtual_memory().used / 1024 / 1024,
                    'disk_usage_percent': psutil.disk_usage('/').percent
                }
            else:
                return {'status': 'psutil não disponível - métricas limitadas'}
        except:
            return {'erro': 'Não foi possível coletar métricas do sistema'}

    def _analisar_padroes_seletores(self):
        """Analisa padrões de uso de seletores para gerar hipóteses de otimização"""
        if not self.logs_seletores:
            return

        # Agrupar seletores por script
        seletores_por_script = {}
        for log in self.logs_seletores:
            script = log['script']
            if script not in seletores_por_script:
                seletores_por_script[script] = []
            seletores_por_script[script].append(log)

        # Analisar cada script
        for script, logs in seletores_por_script.items():
            seletores_sucesso = [log for log in logs if log['sucesso']]
            seletores_falha = [log for log in logs if not log['sucesso']]

            if seletores_sucesso:
                # Encontrar seletor mais usado com sucesso
                seletor_mais_usado = max(set([log['seletor'] for log in seletores_sucesso]),
                                       key=lambda x: [log['seletor'] for log in seletores_sucesso].count(x))

                self.hipoteses_otimizacao.append({
                    'tipo': 'seletor_prioritario',
                    'script': script,
                    'hipotese': f"No {script}, priorizar seletor '{seletor_mais_usado}' que teve sucesso em {len([log for log in seletores_sucesso if log['seletor'] == seletor_mais_usado])} casos",
                    'beneficio_esperado': 'Redução de tentativas de localização de elementos'
                })

            if seletores_falha:
                self.hipoteses_otimizacao.append({
                    'tipo': 'seletor_problematico',
                    'script': script,
                    'hipotese': f"No {script}, {len(seletores_falha)} seletores falharam - considerar remoção ou melhoria",
                    'beneficio_esperado': 'Redução de tempo gasto em seletores que não funcionam'
                })

    def _gerar_relatorio_execucao_total(self):
        """Gera o relatório EXECUCAO TOTAL"""
        self._analisar_padroes_seletores()

        duracao_total = self.fim_execucao - self.inicio_execucao

        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'duracao_total_segundos': duracao_total,
            'duracao_total_formatada': f"{duracao_total:.2f}s",
            'etapas': {},
            'metricas_sistema': self.metricas_sistema,
            'hipoteses_otimizacao': self.hipoteses_otimizacao,
            'resumo': {
                'etapas_executadas': len([e for e in self.metricas_etapas.values() if e.get('sucesso', False)]),
                'etapas_falharam': len([e for e in self.metricas_etapas.values() if not e.get('sucesso', True)]),
                'total_etapas': len(self.metricas_etapas)
            }
        }

        # Adicionar detalhes das etapas
        for nome_etapa, dados in self.metricas_etapas.items():
            relatorio['etapas'][nome_etapa] = {
                'duracao': dados.get('duracao', 0),
                'sucesso': dados.get('sucesso', False),
                'percentual_total': (dados.get('duracao', 0) / duracao_total * 100) if duracao_total > 0 else 0
            }

        # Salvar relatório
        nome_arquivo = f"EXECUCAO_TOTAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2)

        # Imprimir relatório no console
        print("\n" + "="*80)
        print("📊 RELATÓRIO EXECUÇÃO TOTAL")
        print("="*80)
        print(f"⏱️ Duração Total: {duracao_total:.2f}s")
        print(f"📈 Etapas Executadas: {relatorio['resumo']['etapas_executadas']}/{relatorio['resumo']['total_etapas']}")

        print("\n📋 DETALHES POR ETAPA:")
        for nome_etapa, dados in relatorio['etapas'].items():
            status = "✅" if dados['sucesso'] else "❌"
            print(f"  {status} {nome_etapa}: {dados['duracao']:.2f}s ({dados['percentual_total']:.1f}%)")

        if self.hipoteses_otimizacao:
            print("\n🎯 HIPÓTESES DE OTIMIZAÇÃO:")
            for i, hipotese in enumerate(self.hipoteses_otimizacao, 1):
                print(f"  {i}. {hipotese['hipotese']}")
                print(f"     Benefício: {hipotese['beneficio_esperado']}")

        print(f"\n💾 Relatório salvo em: {nome_arquivo}")
        print("="*80)

# Instância global do monitor
monitor = MonitorExecucao()

def analisar_script(script_nome, seletor_usado=None, contexto=""):
    """
    Função para registrar análise de seletor usado em um script
    Deve ser chamada quando um seletor é usado com sucesso
    """
    if seletor_usado:
        monitor.registrar_log_seletor(script_nome, seletor_usado, True, contexto)