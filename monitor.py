#!/usr/bin/env python3
"""
Sistema de Monitoramento e Adaptação - PJePlus
FUNÇÃO ÚNICA MESTRE para análise e otimização de qualquer script
"""

import json
import time
import os
import re
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional

# Safety: By default the monitor runs in read-only mode and will only produce reports
# and suggestions. To allow the monitor to write/optimize files set this to False
# or export the environment variable PJE_MONITOR_WRITE=1 before running.
MONITOR_READ_ONLY = True

def _monitor_write_enabled() -> bool:
    """Return True if monitor is allowed to modify files.
    Controlled by the MONITOR_READ_ONLY constant or by env var PJE_MONITOR_WRITE=1.
    """
    if not MONITOR_READ_ONLY:
        return True
    return os.environ.get('PJE_MONITOR_WRITE', '') == '1'

def analisar_e_otimizar_script(script_path: str, workspace_path: str = "d:\\PjePlus") -> Dict:
    """
    FUNÇÃO ÚNICA MESTRE - Analisa e otimiza qualquer script Python
    Aplica-se a loop.py, p2b.py, ou qualquer outro script do projeto

    Args:
        script_path: Caminho para o script a ser analisado
        workspace_path: Caminho do workspace

    Returns:
        Dict com análise completa e recomendações
    """

    print(f"🔍 ANALISANDO SCRIPT: {os.path.basename(script_path)}")
    print("=" * 60)

    # 1. LER E ANALISAR O SCRIPT
    if not os.path.exists(script_path):
        return {"erro": f"Script não encontrado: {script_path}"}

    with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
        script_content = f.read()

    lines = script_content.split('\n')
    total_lines = len(lines)

    # 2. EXTRAIR SELETORES
    selectors = _extrair_selectors(script_content)
    selenium_usage = _analisar_selenium(script_content)
    functions = _extrair_functions(script_content)

    # 3. IDENTIFICAR PROBLEMAS (BOTTLENECKS)
    bottlenecks = _identificar_bottlenecks(script_content, selectors)

    # 4. GERAR RECOMENDAÇÕES
    recommendations = _gerar_recommendations(selectors, selenium_usage, bottlenecks)

    # 5. CRIAR RELATÓRIO
    relatorio = _criar_relatorio(script_path, total_lines, selectors, functions,
                               selenium_usage, bottlenecks, recommendations)

    # 6. SALVAR RELATÓRIO
    relatorio_path = _salvar_relatorio(relatorio, script_path)

    # 7. RESULTADO FINAL
    resultado = {
        'script_name': os.path.basename(script_path),
        'analise_timestamp': datetime.now().isoformat(),
        'metricas': {
            'total_lines': total_lines,
            'selectors_count': len(selectors),
            'functions_count': len(functions),
            'selenium_usage': len(selenium_usage),
            'bottlenecks_count': len(bottlenecks)
        },
        'dados_detalhados': {
            'selectors': selectors[:10],  # Top 10
            'functions': functions[:10],  # Top 10
            'selenium_usage': selenium_usage,
            'bottlenecks': bottlenecks
        },
        'recommendations': recommendations,
        'relatorio': relatorio,
        'relatorio_path': relatorio_path
    }

    # 8. EXIBIR RESUMO NO CONSOLE
    _exibir_resumo_console(resultado)

    return resultado

def _extrair_selectors(content: str) -> List[str]:
    """Extrai todos os seletores CSS/XPath do código"""
    selectors = []

    # Padrões para diferentes tipos de seletores
    patterns = [
        r'find_element\(By\.(?:CSS_SELECTOR|XPATH|ID|NAME|CLASS_NAME|TAG_NAME),\s*[\'"]([^\'"]+)[\'"]',
        r'find_elements\(By\.(?:CSS_SELECTOR|XPATH|ID|NAME|CLASS_NAME|TAG_NAME),\s*[\'"]([^\'"]+)[\'"]',
        r'\.css_selector\s*=\s*[\'"]([^\'"]+)[\'"]',
        r'\.xpath\s*=\s*[\'"]([^\'"]+)[\'"]',
        r'selector\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
        r'By\.(?:CSS_SELECTOR|XPATH),\s*[\'"]([^\'"]+)[\'"]'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        selectors.extend(matches)

    # Remover duplicatas mantendo ordem
    seen = set()
    unique_selectors = []
    for selector in selectors:
        if selector not in seen:
            seen.add(selector)
            unique_selectors.append(selector)

    return unique_selectors

def _analisar_selenium(content: str) -> List[str]:
    """Analisa uso do Selenium no código"""
    selenium_patterns = [
        r'from selenium',
        r'import selenium',
        r'webdriver\.',
        r'WebDriverWait',
        r'expected_conditions',
        r'find_element',
        r'find_elements',
        r'click\(\)',
        r'send_keys',
        r'get\(',
        r'By\.'
    ]

    usage = []
    for pattern in selenium_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            usage.append(pattern.replace('\\', ''))

    return list(set(usage))  # Remover duplicatas

def _extrair_functions(content: str) -> List[str]:
    """Extrai nomes de funções definidas no script"""
    functions = []
    lines = content.split('\n')

    for line in lines:
        line = line.strip()
        if line.startswith('def '):
            func_match = re.match(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
            if func_match:
                functions.append(func_match.group(1))

    return functions

def _identificar_bottlenecks(content: str, selectors: List[str]) -> List[str]:
    """Identifica possíveis bottlenecks no código"""
    bottlenecks = []

    # Verificar sleeps longos
    sleep_matches = re.findall(r'time\.sleep\((\d+)\)', content)
    for sleep_time in sleep_matches:
        if int(sleep_time) > 5:
            bottlenecks.append(f"Sleep longo detectado: {sleep_time}s")

    # Verificar loops sem break
    if 'while True:' in content and 'break' not in content:
        bottlenecks.append("Loop infinito potencial (while True sem break)")

    # Verificar muitos seletores similares (possível ineficiência)
    if len(selectors) > 20:
        bottlenecks.append(f"Muitos seletores ({len(selectors)}) - considerar otimização")

    # Verificar try/except sem especificação
    if 'except:' in content and 'Exception' not in content:
        bottlenecks.append("Exception genérica sem especificação")

    # Verificar uso de XPath complexo
    xpath_complex = [s for s in selectors if 'xpath' in s.lower() and len(s) > 100]
    if xpath_complex:
        bottlenecks.append(f"XPath complexo detectado ({len(xpath_complex)} casos)")

    return bottlenecks

def _gerar_recommendations(selectors: List[str], selenium_usage: List[str], bottlenecks: List[str]) -> List[Dict]:
    """Gera recomendações de otimização"""
    recommendations = []

    # Recomendações baseadas em seletores
    if len(selectors) > 15:
        recommendations.append({
            'tipo': 'otimizacao',
            'prioridade': 'alta',
            'titulo': 'Otimizar seletores',
            'descricao': f'Reduzir número de seletores de {len(selectors)} para melhorar performance'
        })

    # Recomendações baseadas em Selenium
    if 'WebDriverWait' not in selenium_usage:
        recommendations.append({
            'tipo': 'melhoria',
            'prioridade': 'media',
            'titulo': 'Implementar WebDriverWait',
            'descricao': 'Usar WebDriverWait ao invés de time.sleep para melhor performance'
        })

    # Recomendações baseadas em bottlenecks
    for bottleneck in bottlenecks:
        if 'sleep longo' in bottleneck:
            recommendations.append({
                'tipo': 'otimizacao',
                'prioridade': 'alta',
                'titulo': 'Substituir sleep por wait',
                'descricao': 'Substituir time.sleep por WebDriverWait explícito'
            })
        elif 'loop infinito' in bottleneck:
            recommendations.append({
                'tipo': 'correcao',
                'prioridade': 'critica',
                'titulo': 'Corrigir loop infinito',
                'descricao': 'Adicionar condição de saída ao loop while True'
            })

    # Recomendação geral se não houver problemas
    if not recommendations:
        recommendations.append({
            'tipo': 'info',
            'prioridade': 'baixa',
            'titulo': 'Código otimizado',
            'descricao': 'Nenhuma otimização crítica identificada'
        })

    return recommendations

def _criar_relatorio(script_path: str, total_lines: int, selectors: List[str],
                   functions: List[str], selenium_usage: List[str],
                   bottlenecks: List[str], recommendations: List[Dict]) -> str:
    """Cria relatório completo em formato texto"""
    script_name = os.path.basename(script_path)

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append(f"RELATÓRIO DE ANÁLISE - {script_name.upper()}")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Métricas gerais
    report_lines.append("📊 MÉTRICAS GERAIS")
    report_lines.append("-" * 40)
    report_lines.append(f"Arquivo: {total_lines} linhas")
    report_lines.append(f"Seletores encontrados: {len(selectors)}")
    report_lines.append(f"Funções definidas: {len(functions)}")
    report_lines.append(f"Uso de Selenium: {len(selenium_usage)} padrões")
    report_lines.append(f"Problemas identificados: {len(bottlenecks)}")
    report_lines.append("")

    # Seletores principais
    if selectors:
        report_lines.append("🎯 SELETORES PRINCIPAIS")
        report_lines.append("-" * 40)
        for i, selector in enumerate(selectors[:10]):
            report_lines.append(f"{i+1:2d}. {selector}")
        if len(selectors) > 10:
            report_lines.append(f"    ... e mais {len(selectors) - 10} seletores")
        report_lines.append("")

    # Funções definidas
    if functions:
        report_lines.append("🔧 FUNÇÕES DEFINIDAS")
        report_lines.append("-" * 40)
        for i, func in enumerate(functions[:10]):
            report_lines.append(f"{i+1:2d}. {func}")
        if len(functions) > 10:
            report_lines.append(f"    ... e mais {len(functions) - 10} funções")
        report_lines.append("")

    # Uso do Selenium
    if selenium_usage:
        report_lines.append("🌐 USO DO SELENIUM")
        report_lines.append("-" * 40)
        for pattern in selenium_usage:
            report_lines.append(f"  • {pattern}")
        report_lines.append("")

    # Problemas identificados
    if bottlenecks:
        report_lines.append("🚨 PROBLEMAS IDENTIFICADOS")
        report_lines.append("-" * 40)
        for bottleneck in bottlenecks:
            report_lines.append(f"  • {bottleneck}")
        report_lines.append("")

    # Recomendações
    report_lines.append("💡 RECOMENDAÇÕES")
    report_lines.append("-" * 40)
    for rec in recommendations:
        priority_icon = {'critica': '🔴', 'alta': '🟠', 'media': '🟡', 'baixa': '🟢', 'info': 'ℹ️'}
        icon = priority_icon.get(rec['prioridade'], '❓')
        report_lines.append(f"{icon} {rec['titulo']} ({rec['prioridade'].upper()})")
        report_lines.append(f"   {rec['descricao']}")
        report_lines.append("")

    # Timestamp
    report_lines.append("=" * 80)
    report_lines.append(f"Relatório gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)

def _salvar_relatorio(relatorio: str, script_path: str) -> str:
    """Salva relatório em arquivo"""
    script_name = os.path.splitext(os.path.basename(script_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"relatorio_{script_name}_{timestamp}.txt"

    filepath = os.path.join(os.path.dirname(script_path), filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(relatorio)
        print(f"📄 Relatório salvo: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Erro ao salvar relatório: {e}")
        return None

def _exibir_resumo_console(resultado: Dict) -> None:
    """Exibe resumo da análise no console"""
    print("\n" + "="*60)
    print("✅ ANÁLISE CONCLUÍDA!")
    print("="*60)

    metrics = resultado['metricas']
    print(f"📊 SCRIPT: {resultado['script_name']}")
    print(f"📏 TAMANHO: {metrics['total_lines']} linhas")
    print(f"🎯 SELETORES: {metrics['selectors_count']}")
    print(f"🔧 FUNÇÕES: {metrics['functions_count']}")
    print(f"🌐 SELENIUM: {metrics['selenium_usage']} padrões")
    print(f"🚨 PROBLEMAS: {metrics['bottlenecks_count']}")

    if resultado['relatorio_path']:
        print(f"📄 RELATÓRIO: {resultado['relatorio_path']}")

    print("="*60)

# FUNÇÃO PRINCIPAL PARA USO DIRETO
def analisar_script(script_name: str) -> Dict:
    """
    Função simplificada para analisar script pelo nome
    Uso: analisar_script('loop.py') ou analisar_script('p2b.py')
    """
    workspace = "d:\\PjePlus"
    script_path = os.path.join(workspace, script_name)

    return analisar_e_otimizar_script(script_path, workspace)

# EXEMPLO DE USO DIRETO
if __name__ == "__main__":
    # Analisar loop.py
    print("🔍 ANALISANDO LOOP.PY...")
    resultado_loop = analisar_script('loop.py')

    print("\n🔍 ANALISANDO P2B.PY...")
    resultado_p2b = analisar_script('p2b.py')

    print("\n✅ ANÁLISES CONCLUÍDAS!")
    print("📄 Relatórios salvos no diretório do projeto")

    def load_data(self):
        """Carrega dados de monitoramento existentes"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.monitoring_data = json.load(f)
                print(f"✅ Dados de monitoramento carregados: {len(self.monitoring_data['selectors'])} seletores")
        except Exception as e:
            print(f"⚠️ Erro ao carregar dados: {e}")

    def save_data(self):
        """Salva dados de monitoramento"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.monitoring_data, f, indent=2, ensure_ascii=False)
            print("💾 Dados de monitoramento salvos")
        except Exception as e:
            print(f"❌ Erro ao salvar dados: {e}")

    def analyze_pec_execution(self, pec_data: Dict):
        """
        Analisa especificamente a execução de PEC e propõe otimizações
        """
        print("\n🔍 ANALISANDO EXECUÇÃO PEC...")

        # Extrair dados da execução PEC
        function_calls = pec_data.get('function_calls', [])
        selectors_used = pec_data.get('selectors_used', [])
        execution_time = pec_data.get('execution_time', 0)
        errors = pec_data.get('errors', [])

        # Análise de funções PEC
        pec_functions = self._analyze_pec_functions(function_calls)

        # Análise de seletores PEC
        pec_selectors = self._analyze_pec_selectors(selectors_used)

        # Identificar oportunidades de otimização
        optimization_opportunities = self._identify_pec_optimizations(pec_functions, pec_selectors, execution_time, errors)

        # Gerar recomendações específicas para PEC
        recommendations = self._generate_pec_recommendations(optimization_opportunities)

        # Armazenar análise
        self.monitoring_data['pec_analysis'] = {
            'last_analysis': datetime.now().isoformat(),
            'functions_analyzed': pec_functions,
            'selectors_analyzed': pec_selectors,
            'optimization_opportunities': optimization_opportunities,
            'recommendations': recommendations
        }

        return {
            'pec_functions': pec_functions,
            'pec_selectors': pec_selectors,
            'optimization_opportunities': optimization_opportunities,
            'recommendations': recommendations
        }

    def _analyze_pec_functions(self, function_calls: List[Dict]) -> Dict:
        """Analisa as funções chamadas durante execução PEC"""
        function_stats = {}

        for call in function_calls:
            func_name = call.get('function', 'unknown')
            execution_time = call.get('execution_time', 0)
            success = call.get('success', True)

            if func_name not in function_stats:
                function_stats[func_name] = {
                    'calls': 0,
                    'total_time': 0,
                    'success_count': 0,
                    'error_count': 0,
                    'avg_time': 0
                }

            stats = function_stats[func_name]
            stats['calls'] += 1
            stats['total_time'] += execution_time

            if success:
                stats['success_count'] += 1
            else:
                stats['error_count'] += 1

            if stats['calls'] > 0:
                stats['avg_time'] = stats['total_time'] / stats['calls']

        return function_stats

    def _analyze_pec_selectors(self, selectors_used: List[Dict]) -> Dict:
        """Analisa os seletores utilizados durante execução PEC"""
        selector_stats = {}

        for selector_data in selectors_used:
            selector = selector_data.get('selector', '')
            response_time = selector_data.get('response_time', 0)
            found = selector_data.get('found', True)
            context = selector_data.get('context', 'unknown')

            if selector not in selector_stats:
                selector_stats[selector] = {
                    'uses': 0,
                    'total_response_time': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'avg_response_time': 0,
                    'contexts': set()
                }

            stats = selector_stats[selector]
            stats['uses'] += 1
            stats['total_response_time'] += response_time
            stats['contexts'].add(context)

            if found:
                stats['success_count'] += 1
            else:
                stats['failure_count'] += 1

            if stats['uses'] > 0:
                stats['avg_response_time'] = stats['total_response_time'] / stats['uses']

        return selector_stats

    def _identify_pec_optimizations(self, pec_functions: Dict, pec_selectors: Dict,
                                   execution_time: float, errors: List) -> List[Dict]:
        """Identifica oportunidades de otimização específicas para PEC"""
        opportunities = []

        # Análise de funções lentas
        for func_name, stats in pec_functions.items():
            if stats['avg_time'] > 5.0:  # Funções que demoram mais de 5 segundos
                opportunities.append({
                    'type': 'slow_function',
                    'target': func_name,
                    'description': f'Função {func_name} demora em média {stats["avg_time"]:.2f}s',
                    'impact': 'high',
                    'suggestion': 'Otimizar lógica interna ou implementar cache',
                    'potential_savings': stats['avg_time'] * 0.3  # 30% de melhoria estimada
                })

        # Análise de seletores com baixa taxa de sucesso
        for selector, stats in pec_selectors.items():
            success_rate = stats['success_count'] / stats['uses'] if stats['uses'] > 0 else 0
            if success_rate < 0.8:  # Menos de 80% de sucesso
                opportunities.append({
                    'type': 'unreliable_selector',
                    'target': selector,
                    'description': f'Seletor tem taxa de sucesso de {success_rate:.1%}',
                    'impact': 'medium',
                    'suggestion': 'Revisar seletor ou implementar fallback',
                    'current_success_rate': success_rate
                })

        # Análise de seletores não utilizados
        all_selectors_in_code = self.extract_selectors_from_file(os.path.join(self.workspace_path, 'pec.py'))
        used_selectors = set(pec_selectors.keys())
        unused_selectors = all_selectors_in_code - used_selectors

        if unused_selectors:
            opportunities.append({
                'type': 'unused_selectors',
                'target': 'pec.py',
                'description': f'{len(unused_selectors)} seletores não utilizados encontrados',
                'impact': 'low',
                'suggestion': 'Remover seletores não utilizados para limpeza de código',
                'unused_selectors': list(unused_selectors)
            })

        # Análise de tempo total de execução
        if execution_time > 60:  # Execuções que demoram mais de 1 minuto
            opportunities.append({
                'type': 'long_execution',
                'target': 'processamento_geral',
                'description': f'Execução PEC demora {execution_time:.1f}s',
                'impact': 'high',
                'suggestion': 'Implementar processamento paralelo ou otimizar algoritmos',
                'current_time': execution_time
            })

        # Análise de erros frequentes
        if errors:
            error_types = {}
            for error in errors:
                error_type = error.get('type', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1

            for error_type, count in error_types.items():
                if count > 3:  # Mais de 3 erros do mesmo tipo
                    opportunities.append({
                        'type': 'recurring_errors',
                        'target': error_type,
                        'description': f'{count} erros do tipo {error_type} detectados',
                        'impact': 'high',
                        'suggestion': 'Implementar tratamento específico para este tipo de erro',
                        'error_count': count
                    })

        return opportunities

    def _generate_pec_recommendations(self, optimization_opportunities: List[Dict]) -> List[Dict]:
        """Gera recomendações específicas baseadas nas oportunidades identificadas"""
        recommendations = []

        for opportunity in optimization_opportunities:
            if opportunity['type'] == 'slow_function':
                recommendations.append({
                    'priority': 'high',
                    'category': 'performance',
                    'action': 'optimize_function',
                    'target': opportunity['target'],
                    'description': opportunity['description'],
                    'implementation_steps': [
                        'Analisar gargalos na função',
                        'Implementar cache se aplicável',
                        'Otimizar algoritmos internos',
                        'Considerar processamento assíncrono'
                    ],
                    'estimated_effort': 'medium',
                    'expected_benefit': f"Redução de {opportunity['potential_savings']:.1f}s por execução"
                })

            elif opportunity['type'] == 'unreliable_selector':
                recommendations.append({
                    'priority': 'medium',
                    'category': 'reliability',
                    'action': 'fix_selector',
                    'target': opportunity['target'],
                    'description': opportunity['description'],
                    'implementation_steps': [
                        'Testar seletor em diferentes condições',
                        'Implementar seletor alternativo',
                        'Adicionar verificação de existência',
                        'Considerar uso de XPath como fallback'
                    ],
                    'estimated_effort': 'low',
                    'expected_benefit': f"Melhoria da taxa de sucesso para >90%"
                })

            elif opportunity['type'] == 'unused_selectors':
                recommendations.append({
                    'priority': 'low',
                    'category': 'maintenance',
                    'action': 'cleanup_selectors',
                    'target': opportunity['target'],
                    'description': opportunity['description'],
                    'implementation_steps': [
                        'Identificar seletores não utilizados',
                        'Verificar se são realmente não utilizados',
                        'Remover seletores obsoletos',
                        'Atualizar comentários e documentação'
                    ],
                    'estimated_effort': 'low',
                    'expected_benefit': 'Código mais limpo e manutenção facilitada'
                })

            elif opportunity['type'] == 'long_execution':
                recommendations.append({
                    'priority': 'high',
                    'category': 'performance',
                    'action': 'optimize_execution',
                    'target': opportunity['target'],
                    'description': opportunity['description'],
                    'implementation_steps': [
                        'Implementar processamento paralelo',
                        'Otimizar algoritmos de busca',
                        'Adicionar cache inteligente',
                        'Revisar lógica de espera'
                    ],
                    'estimated_effort': 'high',
                    'expected_benefit': f"Redução significativa do tempo de execução"
                })

            elif opportunity['type'] == 'recurring_errors':
                recommendations.append({
                    'priority': 'high',
                    'category': 'reliability',
                    'action': 'fix_error_handling',
                    'target': opportunity['target'],
                    'description': opportunity['description'],
                    'implementation_steps': [
                        'Analisar causa raiz dos erros',
                        'Implementar tratamento específico',
                        'Adicionar logs detalhados',
                        'Criar mecanismo de retry inteligente'
                    ],
                    'estimated_effort': 'medium',
                    'expected_benefit': f"Redução significativa de erros recorrentes"
                })

        return recommendations

        self.monitoring_data['executions'].append(execution_record)
        self.monitoring_data['performance_history'].append({
            'timestamp': execution_record['timestamp'],
            'function': function_name,
            'success_rate': execution_record['success_rate'],
            'total_time': execution_record['total_time'],
            'environment': execution_record['environment_conditions']
        })

        # Atualizar estatísticas dos seletores
        for selector_data in execution_data.get('selectors_used', []):
            self.update_selector_stats(selector_data)

        # Análise de performance e adaptação automática
        self.performance_analyzer.analyze_execution(execution_record)
        self.adaptation_system.adapt_based_on_performance(execution_record)

        # Manter apenas últimas 1000 execuções
        if len(self.monitoring_data['executions']) > 1000:
            self.monitoring_data['executions'] = self.monitoring_data['executions'][-1000:]

        # Manter histórico de performance limitado
        if len(self.monitoring_data['performance_history']) > 500:
            self.monitoring_data['performance_history'] = self.monitoring_data['performance_history'][-500:]

        print(f"📊 Execução monitorada: {function_name} ({execution_record['success_rate']:.1%})")

    def detect_environment_conditions(self) -> Dict:
        """Detecta condições atuais do ambiente TRT2"""
        # Simulação de detecção de condições do ambiente
        # Em produção, isso poderia verificar conectividade, latência, etc.
        return {
            'estimated_load': 'normal',  # low, normal, high, critical
            'network_latency': 'normal',  # fast, normal, slow
            'server_response': 'normal',  # fast, normal, slow
            'time_of_day': datetime.now().hour
        }

    def update_selector_stats(self, selector_data: Dict):
        """Atualiza estatísticas de um seletor específico"""
        selector = selector_data['selector']
        success = selector_data['success']
        response_time = selector_data['response_time']
        context = selector_data.get('context', 'unknown')

        if selector not in self.monitoring_data['selectors']:
            self.monitoring_data['selectors'][selector] = {
                'first_seen': datetime.now().isoformat(),
                'total_uses': 0,
                'success_count': 0,
                'failure_count': 0,
                'avg_response_time': 0,
                'contexts': set(),
                'last_used': None,
                'confidence_score': 0.0,
                'recommended': True,
                'performance_trend': []
            }

        stats = self.monitoring_data['selectors'][selector]
        stats['total_uses'] += 1
        stats['last_used'] = datetime.now().isoformat()

        if success:
            stats['success_count'] += 1
        else:
            stats['failure_count'] += 1

        # Atualizar média móvel do tempo de resposta
        if stats['avg_response_time'] == 0:
            stats['avg_response_time'] = response_time
        else:
            stats['avg_response_time'] = (stats['avg_response_time'] * 0.9) + (response_time * 0.1)

        # Atualizar tendência de performance
        stats['performance_trend'].append({
            'timestamp': datetime.now().isoformat(),
            'response_time': response_time,
            'success': success
        })

        # Manter apenas últimas 20 medições
        if len(stats['performance_trend']) > 20:
            stats['performance_trend'] = stats['performance_trend'][-20:]

        # Atualizar contextos
        if context:
            stats['contexts'].add(context)

        # Calcular score de confiança
        total_attempts = stats['success_count'] + stats['failure_count']
        if total_attempts > 0:
            stats['confidence_score'] = stats['success_count'] / total_attempts

        # Marcar como não recomendado se falhar muito
        if stats['confidence_score'] < 0.3 and stats['total_uses'] > 5:
            stats['recommended'] = False

    def get_adaptation_recommendations(self) -> List[Dict]:
        """Retorna recomendações de adaptação baseadas na análise atual"""
        recommendations = []

        # Análise de performance geral
        recent_executions = self.monitoring_data['executions'][-50:]  # Últimas 50 execuções
        if recent_executions:
            avg_success = sum(ex['success_rate'] for ex in recent_executions) / len(recent_executions)
            avg_time = sum(ex['total_time'] for ex in recent_executions) / len(recent_executions)

            if avg_success < 0.7:
                recommendations.append({
                    'type': 'performance_degradation',
                    'priority': 'high',
                    'description': f'Sucesso médio baixo: {avg_success:.1%}',
                    'action': 'Ativar modo defensivo e aumentar timeouts'
                })

            if avg_time > 15:
                recommendations.append({
                    'type': 'slow_performance',
                    'priority': 'medium',
                    'description': f'Tempo médio alto: {avg_time:.1f}s',
                    'action': 'Otimizar seletores e reduzir esperas desnecessárias'
                })

        # Análise de seletores problemáticos
        problematic_selectors = []
        for selector, stats in self.monitoring_data['selectors'].items():
            if stats['confidence_score'] < 0.5 and stats['total_uses'] > 10:
                problematic_selectors.append(selector)

        if problematic_selectors:
            recommendations.append({
                'type': 'selector_issues',
                'priority': 'medium',
                'description': f'{len(problematic_selectors)} seletores com baixa confiança',
                'action': 'Revisar e otimizar seletores problemáticos',
                'selectors': problematic_selectors[:5]  # Top 5
            })

        return recommendations

    def export_monitoring_report(self) -> Dict:
        """Exporta relatório completo de monitoramento"""
        report = {
            'summary': {
                'total_executions': len(self.monitoring_data['executions']),
                'total_selectors': len(self.monitoring_data['selectors']),
                'monitoring_period': self.get_monitoring_period(),
                'current_adaptation_mode': self.monitoring_data['anomaly_detection']['adaptation_mode'],
                'stability_score': self.monitoring_data['anomaly_detection']['stability_score']
            },
            'performance_metrics': self.calculate_performance_metrics(),
            'adaptation_history': self.monitoring_data['environment_adaptations'][-10:],  # Últimas 10
            'recommendations': self.get_adaptation_recommendations(),
            'anomalies': self.monitoring_data['anomaly_detection']['last_anomalies'][-5:],  # Últimas 5
            'generated_at': datetime.now().isoformat()
        }

        return report

    def get_monitoring_period(self) -> str:
        """Calcula período de monitoramento"""
        if not self.monitoring_data['executions']:
            return "Nenhum dado"

        first_execution = self.monitoring_data['executions'][0]['timestamp']
        last_execution = self.monitoring_data['executions'][-1]['timestamp']

        start = datetime.fromisoformat(first_execution)
        end = datetime.fromisoformat(last_execution)

        delta = end - start
        return f"{delta.days} dias, {delta.seconds // 3600} horas"

    def calculate_performance_metrics(self) -> Dict:
        """Calcula métricas de performance"""
        if not self.monitoring_data['executions']:
            return {}

        executions = self.monitoring_data['executions']
        recent_executions = executions[-100:]  # Últimas 100

        return {
            'overall_success_rate': sum(ex['success_rate'] for ex in executions) / len(executions),
            'recent_success_rate': sum(ex['success_rate'] for ex in recent_executions) / len(recent_executions),
            'average_execution_time': sum(ex['total_time'] for ex in executions) / len(executions),
            'recent_average_time': sum(ex['total_time'] for ex in recent_executions) / len(recent_executions),
            'total_functions_monitored': len(set(ex['function'] for ex in executions)),
            'most_used_function': Counter(ex['function'] for ex in executions).most_common(1)[0][0]
        }

    def load_data(self):
        """Carrega dados de otimização existentes"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.optimization_data = json.load(f)
                print(f"✅ Dados de otimização carregados: {len(self.optimization_data['selectors'])} seletores")
        except Exception as e:
            print(f"⚠️ Erro ao carregar dados: {e}")

    def save_data(self):
        """Salva dados de otimização"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.optimization_data, f, indent=2, ensure_ascii=False)
            print("💾 Dados de otimização salvos")
        except Exception as e:
            print(f"❌ Erro ao salvar dados: {e}")

    def monitor_execution(self, function_name: str, execution_data: Dict):
        """
        Monitora uma execução específica e coleta dados de performance
        """
        execution_record = {
            'timestamp': datetime.now().isoformat(),
            'function': function_name,
            'selectors_used': execution_data.get('selectors_used', []),
            'success_rate': execution_data.get('success_rate', 0),
            'total_time': execution_data.get('total_time', 0),
            'errors': execution_data.get('errors', []),
            'page_context': execution_data.get('page_context', {})
        }

        self.monitoring_data['executions'].append(execution_record)

        # Atualizar estatísticas dos seletores
        for selector_data in execution_data.get('selectors_used', []):
            self.update_selector_stats(selector_data)

        # Manter apenas últimas 1000 execuções
        if len(self.monitoring_data['executions']) > 1000:
            self.monitoring_data['executions'] = self.monitoring_data['executions'][-1000:]

        print(f"📊 Execução monitorada: {function_name}")

    def update_selector_stats(self, selector_data: Dict):
        """Atualiza estatísticas de um seletor específico"""
        selector = selector_data['selector']
        success = selector_data.get('success', True)  # Assume sucesso se não especificado
        response_time = selector_data.get('response_time', selector_data.get('avg_time', 0))
        context = selector_data.get('context', 'unknown')

        if selector not in self.monitoring_data['selectors']:
            self.monitoring_data['selectors'][selector] = {
                'first_seen': datetime.now().isoformat(),
                'total_uses': 0,
                'success_count': 0,
                'failure_count': 0,
                'avg_response_time': 0,
                'contexts': set(),
                'last_used': None,
                'confidence_score': 0.0,
                'recommended': True
            }

        stats = self.monitoring_data['selectors'][selector]
        stats['total_uses'] += 1
        stats['last_used'] = datetime.now().isoformat()

        if success:
            stats['success_count'] += 1
        else:
            stats['failure_count'] += 1

        # Atualizar média móvel do tempo de resposta
        if stats['avg_response_time'] == 0:
            stats['avg_response_time'] = response_time
        else:
            stats['avg_response_time'] = (stats['avg_response_time'] * 0.9) + (response_time * 0.1)

        # Atualizar contextos
        if context:
            stats['contexts'].add(context)

        # Calcular score de confiança
        total_attempts = stats['success_count'] + stats['failure_count']
        if total_attempts > 0:
            stats['confidence_score'] = stats['success_count'] / total_attempts

        # Marcar como não recomendado se falhar muito
        if stats['confidence_score'] < 0.3 and stats['total_uses'] > 5:
            stats['recommended'] = False

    def analyze_priority_scripts(self):
        """Analisa especificamente os scripts prioritários do PJePlus"""
        print("🎯 Analisando scripts prioritários do PJePlus...")

        priority_analysis = {}
        total_selectors = 0
        total_functions = 0

        for script_name, description in self.priority_scripts.items():
            script_path = os.path.join(self.workspace_path, script_name)

            if os.path.exists(script_path):
                print(f"  📄 Analisando {script_name} - {description}")

                # Análise detalhada do script
                script_analysis = self.analyze_script_detailed(script_path, script_name)

                priority_analysis[script_name] = script_analysis
                total_selectors += script_analysis['selectors_count']
                total_functions += script_analysis['functions_count']

                print(f"    • {script_analysis['selectors_count']} seletores encontrados")
                print(f"    • {script_analysis['functions_count']} funções identificadas")
                print(f"    • {len(script_analysis['selenium_usage'])} usos de Selenium")
                print(f"    • {len(script_analysis['webdriver_usage'])} usos de WebDriver")

            else:
                print(f"  ⚠️ Script {script_name} não encontrado")
                priority_analysis[script_name] = {
                    'status': 'not_found',
                    'selectors_count': 0,
                    'functions_count': 0
                }

        # Análise de padrões comuns
        common_patterns = self.identify_common_patterns(priority_analysis)

        return {
            'priority_scripts': priority_analysis,
            'summary': {
                'total_scripts_analyzed': len([s for s in priority_analysis.values() if s.get('status') != 'not_found']),
                'total_selectors': total_selectors,
                'total_functions': total_functions,
                'common_patterns': common_patterns
            }
        }

    def analyze_script_detailed(self, script_path: str, script_name: str) -> Dict:
        """Análise detalhada de um script específico"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Análise de seletores
            selectors = self.extract_selectors_from_file(script_path)

            # Análise de funções
            functions = self.extract_functions_from_file(content)

            # Análise de uso de Selenium/WebDriver
            selenium_usage = self.extract_selenium_usage(content)
            webdriver_usage = self.extract_webdriver_usage(content)

            # Análise de padrões de automação
            automation_patterns = self.extract_automation_patterns(content)

            # Análise de performance bottlenecks
            bottlenecks = self.identify_bottlenecks(content, script_name)

            return {
                'status': 'analyzed',
                'selectors_count': len(selectors),
                'selectors': list(selectors),
                'functions_count': len(functions),
                'functions': functions,
                'selenium_usage': selenium_usage,
                'webdriver_usage': webdriver_usage,
                'automation_patterns': automation_patterns,
                'bottlenecks': bottlenecks,
                'file_size': len(content),
                'line_count': len(content.split('\n'))
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'selectors_count': 0,
                'functions_count': 0
            }

    def extract_functions_from_file(self, content: str) -> List[Dict]:
        """Extrai informações sobre funções do arquivo"""
        functions = []

        # Padrão para funções Python
        function_pattern = r'def\s+(\w+)\s*\([^)]*\)\s*:'
        matches = re.findall(function_pattern, content)

        for match in matches:
            functions.append({
                'name': match,
                'type': 'python_function'
            })

        # Procurar por funções JavaScript inline
        js_function_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*\{'
        js_matches = re.findall(js_function_pattern, content)

        for match in js_matches:
            functions.append({
                'name': match,
                'type': 'javascript_function'
            })

        return functions

    def extract_selenium_usage(self, content: str) -> List[Dict]:
        """Extrai uso de Selenium do código"""
        selenium_patterns = [
            (r'WebDriverWait\s*\(', 'WebDriverWait'),
            (r'find_element\s*\(', 'find_element'),
            (r'find_elements\s*\(', 'find_elements'),
            (r'click\s*\(\s*\)', 'click'),
            (r'send_keys\s*\(', 'send_keys'),
            (r'execute_script\s*\(', 'execute_script')
        ]

        usage = []
        for pattern, method in selenium_patterns:
            matches = re.findall(pattern, content)
            if matches:
                usage.append({
                    'method': method,
                    'count': len(matches),
                    'pattern': pattern
                })

        return usage

    def extract_webdriver_usage(self, content: str) -> List[Dict]:
        """Extrai uso de WebDriver do código"""
        webdriver_patterns = [
            (r'webdriver\.\w+', 'webdriver_method'),
            (r'driver\.\w+', 'driver_method'),
            (r'browser\.\w+', 'browser_method'),
            (r'chrome\.\w+', 'chrome_method'),
            (r'firefox\.\w+', 'firefox_method')
        ]

        usage = []
        for pattern, method_type in webdriver_patterns:
            matches = re.findall(pattern, content)
            if matches:
                usage.append({
                    'type': method_type,
                    'count': len(matches),
                    'pattern': pattern,
                    'examples': matches[:3]  # Primeiros 3 exemplos
                })

        return usage

    def extract_automation_patterns(self, content: str) -> List[Dict]:
        """Extrai padrões de automação comuns"""
        patterns = []

        # Padrões de automação PJe
        automation_indicators = [
            ('login', r'login|autenticar|credencial'),
            ('navigation', r'navigate|ir_para|navegar'),
            ('form_filling', r'preencher|fill|input'),
            ('click_actions', r'clicar|click|botao'),
            ('wait_strategies', r'wait|esperar|aguardar'),
            ('error_handling', r'except|try|error|falha'),
            ('data_processing', r'processar|extrair|dados'),
            ('file_operations', r'arquivo|file|salvar|load')
        ]

        for pattern_name, regex in automation_indicators:
            matches = re.findall(regex, content, re.IGNORECASE)
            if matches:
                patterns.append({
                    'pattern': pattern_name,
                    'occurrences': len(matches),
                    'examples': list(set(matches[:5]))  # Exemplos únicos
                })

        return patterns

    def identify_bottlenecks(self, content: str, script_name: str) -> List[Dict]:
        """Identifica possíveis gargalos de performance"""
        bottlenecks = []

        # Verificar sleeps longos
        long_sleeps = re.findall(r'time\.sleep\s*\(\s*(\d+)', content)
        if long_sleeps:
            long_sleeps = [int(s) for s in long_sleeps if int(s) > 5]
            if long_sleeps:
                bottlenecks.append({
                    'type': 'long_sleep',
                    'description': f'Sleeps longos detectados: {long_sleeps}',
                    'impact': 'high',
                    'suggestion': 'Substituir por WebDriverWait ou condições inteligentes'
                })

        # Verificar loops sem timeout
        infinite_loops = re.findall(r'while\s+True\s*:', content)
        if infinite_loops:
            bottlenecks.append({
                'type': 'infinite_loop',
                'description': f'{len(infinite_loops)} loops infinitos detectados',
                'impact': 'critical',
                'suggestion': 'Adicionar timeout e condições de saída'
            })

        # Verificar uso excessivo de execute_script
        execute_scripts = len(re.findall(r'execute_script\s*\(', content))
        if execute_scripts > 10:
            bottlenecks.append({
                'type': 'excessive_javascript',
                'description': f'{execute_scripts} usos de execute_script',
                'impact': 'medium',
                'suggestion': 'Otimizar para usar métodos Selenium nativos quando possível'
            })

        # Verificar ausência de rate limiting
        rate_limiting = re.findall(r'sleep|wait|delay', content, re.IGNORECASE)
        if len(rate_limiting) < 3:
            bottlenecks.append({
                'type': 'no_rate_limiting',
                'description': 'Pouco controle de rate limiting detectado',
                'impact': 'high',
                'suggestion': 'Implementar rate limiting inteligente'
            })

        return bottlenecks

    def identify_common_patterns(self, priority_analysis: Dict) -> Dict:
        """Identifica padrões comuns entre os scripts prioritários"""
        common_selectors = set()
        common_functions = set()
        common_bottlenecks = []

        # Coletar dados de todos os scripts
        for script_name, analysis in priority_analysis.items():
            if analysis.get('status') == 'analyzed':
                # Seletores comuns
                if 'selectors' in analysis:
                    if not common_selectors:
                        common_selectors = set(analysis['selectors'])
                    else:
                        common_selectors &= set(analysis['selectors'])

                # Funções comuns
                if 'functions' in analysis:
                    func_names = {f['name'] for f in analysis['functions']}
                    if not common_functions:
                        common_functions = func_names
                    else:
                        common_functions &= func_names

                # Bottlenecks comuns
                if 'bottlenecks' in analysis:
                    common_bottlenecks.extend(analysis['bottlenecks'])

        return {
            'common_selectors': list(common_selectors),
            'common_functions': list(common_functions),
            'shared_bottlenecks': common_bottlenecks,
            'optimization_opportunities': self.identify_optimization_opportunities(common_selectors, common_functions)
        }

    def identify_optimization_opportunities(self, common_selectors: List, common_functions: List) -> List[Dict]:
        """Identifica oportunidades de otimização baseadas em padrões comuns"""
        opportunities = []

        # Oportunidade: Funções duplicadas
        if len(common_functions) > 0:
            opportunities.append({
                'type': 'function_deduplication',
                'description': f'{len(common_functions)} funções comuns encontradas',
                'benefit': 'Reduzir duplicação de código',
                'effort': 'medium'
            })

        # Oportunidade: Seletores compartilhados
        if len(common_selectors) > 0:
            opportunities.append({
                'type': 'selector_sharing',
                'description': f'{len(common_selectors)} seletores compartilhados',
                'benefit': 'Centralizar configuração de seletores',
                'effort': 'low'
            })

        # Oportunidade: Padrões de automação comuns
        opportunities.append({
            'type': 'common_automation_patterns',
            'description': 'Padrões de automação repetitivos identificados',
            'benefit': 'Criar biblioteca compartilhada de automação',
            'effort': 'high'
        })

        return opportunities

    def find_python_files(self) -> List[str]:
        """Encontra todos os arquivos Python no workspace"""
        python_files = []
        for root, dirs, files in os.walk(self.workspace_path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files

    def extract_selectors_from_file(self, file_path: str) -> Set[str]:
        """Extrai todos os seletores CSS de um arquivo Python"""
        selectors = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Padrões comuns de seletores CSS em strings Python
            patterns = [
                r"'([^']*\[.*?\])'",  # 'seletor[atributo]'
                r'"([^"]*\[.*?\])"',  # "seletor[atributo]"
                r"'([^']*#[^'\s]+)'", # 'seletor#id'
                r'"([^"]*#[^"\s]+)"', # "seletor#id"
                r"'([^']*\.[^'\s]+)'", # 'seletor.classe'
                r'"([^"]*\.[^"\s]+)"', # "seletor.classe"
                r"'([^']*[>\s][^'\s]+)'", # 'seletor > filho' ou 'seletor filho'
                r'"([^"]*[>\s][^"]+)"', # "seletor > filho" ou "seletor filho"
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Filtrar apenas seletores válidos (com caracteres específicos)
                    if any(char in match for char in ['[', ']', '#', '.', '>', ' ']):
                        # Limpar e validar seletor
                        clean_selector = match.strip()
                        if len(clean_selector) > 3 and not clean_selector.startswith('http'):
                            selectors.add(clean_selector)

            # Procurar por seletores em variáveis ou constantes
            var_patterns = [
                r'selector\s*=\s*[\'"]([^\'"]*?)[\'"]',
                r'SELECTOR\s*=\s*[\'"]([^\'"]*?)[\'"]',
                r'selector_\w+\s*=\s*[\'"]([^\'"]*?)[\'"]'
            ]

            for pattern in var_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if any(char in match for char in ['[', ']', '#', '.', '>', ' ']):
                        selectors.add(match.strip())

        except Exception as e:
            print(f"⚠️ Erro ao extrair seletores de {file_path}: {e}")

        return selectors

    def identify_unused_selectors(self, script_path: str, used_selectors: Set[str]) -> Dict:
        """Identifica seletores não utilizados em um script específico"""
        try:
            # Extrair todos os seletores do arquivo
            all_selectors = self.extract_selectors_from_file(script_path)

            # Identificar seletores não utilizados
            unused_selectors = all_selectors - used_selectors

            # Análise detalhada dos seletores não utilizados
            unused_analysis = {}
            for selector in unused_selectors:
                unused_analysis[selector] = {
                    'selector': selector,
                    'complexity': self._calculate_selector_complexity(selector),
                    'type': self._classify_selector_type(selector),
                    'removal_safe': self._is_safe_to_remove(selector, script_path)
                }

            return {
                'total_selectors': len(all_selectors),
                'used_selectors': len(used_selectors),
                'unused_selectors': len(unused_selectors),
                'unused_analysis': unused_analysis,
                'cleanup_recommendations': self._generate_cleanup_recommendations(unused_analysis)
            }

        except Exception as e:
            return {
                'error': str(e),
                'total_selectors': 0,
                'used_selectors': 0,
                'unused_selectors': 0
            }

    def _calculate_selector_complexity(self, selector: str) -> str:
        """Calcula a complexidade de um seletor"""
        complexity_score = 0

        # Contar diferentes tipos de seletores
        if '[' in selector: complexity_score += 2  # Atributos
        if '>' in selector: complexity_score += 1  # Filho direto
        if ' ' in selector and '>' not in selector: complexity_score += 1  # Descendente
        if '+' in selector or '~' in selector: complexity_score += 2  # Irmãos
        if ':' in selector: complexity_score += 1  # Pseudo-classes
        if '::' in selector: complexity_score += 1  # Pseudo-elementos

        # Comprimento do seletor
        if len(selector) > 50: complexity_score += 1
        elif len(selector) > 100: complexity_score += 2

        if complexity_score >= 5: return 'high'
        elif complexity_score >= 3: return 'medium'
        else: return 'low'

    def _classify_selector_type(self, selector: str) -> str:
        """Classifica o tipo de seletor"""
        if '[id=' in selector or '#' in selector:
            return 'id'
        elif '[class' in selector or '.' in selector:
            return 'class'
        elif '[' in selector:
            return 'attribute'
        elif '>' in selector or ' ' in selector:
            return 'combinator'
        else:
            return 'tag'

    def _is_safe_to_remove(self, selector: str, script_path: str) -> bool:
        """Verifica se é seguro remover um seletor"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Verificar se o seletor está em comentários
            if f'#.*{re.escape(selector)}' in content or f'//.*{re.escape(selector)}' in content:
                return False

            # Verificar se está em uma lista de seletores alternativos
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if selector in line:
                    # Verificar linhas próximas para contexto
                    start_line = max(0, i - 3)
                    end_line = min(len(lines), i + 4)
                    context = '\n'.join(lines[start_line:end_line])

                    # Se estiver em uma lista ou dicionário, pode ser fallback
                    if 'fallback' in context.lower() or 'alternative' in context.lower():
                        return False

                    # Se estiver comentado
                    if '#' in line[:line.find(selector)] or '//' in line[:line.find(selector)]:
                        return False

            return True

        except Exception:
            return False

    def _generate_cleanup_recommendations(self, unused_analysis: Dict) -> List[Dict]:
        """Gera recomendações para limpeza de código"""
        recommendations = []

        # Agrupar por tipo e complexidade
        by_type = {}
        by_complexity = {'high': [], 'medium': [], 'low': []}

        for selector, analysis in unused_analysis.items():
            sel_type = analysis['type']
            complexity = analysis['complexity']

            if sel_type not in by_type:
                by_type[sel_type] = []
            by_type[sel_type].append(selector)

            by_complexity[complexity].append(selector)

        # Recomendação para seletores complexos não utilizados
        if by_complexity['high']:
            recommendations.append({
                'type': 'complex_selectors',
                'description': f'{len(by_complexity["high"])} seletores complexos não utilizados',
                'selectors': by_complexity['high'][:5],  # Top 5
                'impact': 'medium',
                'action': 'Remover seletores complexos não utilizados para simplificar código'
            })

        # Recomendação para IDs não utilizados
        if 'id' in by_type and len(by_type['id']) > 0:
            recommendations.append({
                'type': 'unused_ids',
                'description': f'{len(by_type["id"])} seletores de ID não utilizados',
                'selectors': by_type['id'][:3],
                'impact': 'low',
                'action': 'Revisar e remover IDs não utilizados'
            })

        # Recomendação geral de limpeza
        total_unused = len(unused_analysis)
        if total_unused > 10:
            recommendations.append({
                'type': 'bulk_cleanup',
                'description': f'{total_unused} seletores não utilizados no total',
                'impact': 'low',
                'action': 'Executar limpeza em lote dos seletores não utilizados'
            })

        return recommendations

    def generate_pec_optimization_report(self, pec_analysis: Dict, unused_selectors_analysis: Dict) -> str:
        """Gera um relatório detalhado das otimizações propostas"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RELATÓRIO DE OTIMIZAÇÃO - SISTEMA PEC")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Análise de execução PEC
        if 'execution_analysis' in pec_analysis:
            exec_analysis = pec_analysis['execution_analysis']
            report_lines.append("📊 ANÁLISE DE EXECUÇÃO PEC")
            report_lines.append("-" * 40)
            report_lines.append(f"Total de funções analisadas: {exec_analysis.get('total_functions', 0)}")
            report_lines.append(f"Funções com problemas: {exec_analysis.get('problematic_functions', 0)}")
            report_lines.append(f"Tempo médio de execução: {exec_analysis.get('avg_execution_time', 0):.2f}s")
            report_lines.append("")

            if 'performance_issues' in exec_analysis:
                report_lines.append("🚨 PROBLEMAS DE PERFORMANCE IDENTIFICADOS:")
                for issue in exec_analysis['performance_issues'][:5]:  # Top 5
                    report_lines.append(f"  • {issue}")
                report_lines.append("")

        # Análise de seletores não utilizados
        if unused_selectors_analysis:
            report_lines.append("🧹 ANÁLISE DE SELETORES NÃO UTILIZADOS")
            report_lines.append("-" * 40)
            report_lines.append(f"Total de seletores encontrados: {unused_selectors_analysis.get('total_selectors', 0)}")
            report_lines.append(f"Seletores utilizados: {unused_selectors_analysis.get('used_selectors', 0)}")
            report_lines.append(f"Seletores não utilizados: {unused_selectors_analysis.get('unused_selectors', 0)}")
            report_lines.append("")

            # Análise detalhada
            if 'unused_analysis' in unused_selectors_analysis:
                unused_analysis = unused_selectors_analysis['unused_analysis']

                # Agrupar por complexidade
                complexity_count = {'high': 0, 'medium': 0, 'low': 0}
                type_count = {}

                for selector_data in unused_analysis.values():
                    complexity_count[selector_data['complexity']] += 1
                    sel_type = selector_data['type']
                    type_count[sel_type] = type_count.get(sel_type, 0) + 1

                report_lines.append("📈 DISTRIBUIÇÃO POR COMPLEXIDADE:")
                for complexity, count in complexity_count.items():
                    if count > 0:
                        report_lines.append(f"  • {complexity.upper()}: {count} seletores")
                report_lines.append("")

                report_lines.append("🏷️ DISTRIBUIÇÃO POR TIPO:")
                for sel_type, count in type_count.items():
                    report_lines.append(f"  • {sel_type.upper()}: {count} seletores")
                report_lines.append("")

            # Recomendações de limpeza
            if 'cleanup_recommendations' in unused_selectors_analysis:
                recommendations = unused_selectors_analysis['cleanup_recommendations']
                if recommendations:
                    report_lines.append("💡 RECOMENDAÇÕES DE LIMPEZA")
                    report_lines.append("-" * 40)
                    for rec in recommendations:
                        report_lines.append(f"🔧 {rec['description']}")
                        report_lines.append(f"   Impacto: {rec['impact'].upper()}")
                        report_lines.append(f"   Ação: {rec['action']}")

                        if 'selectors' in rec and rec['selectors']:
                            report_lines.append("   Exemplos de seletores:")
                            for selector in rec['selectors'][:3]:  # Top 3 exemplos
                                report_lines.append(f"     - {selector}")

                        report_lines.append("")

        # Recomendações gerais
        report_lines.append("🎯 RECOMENDAÇÕES GERAIS")
        report_lines.append("-" * 40)

        total_issues = 0
        if 'execution_analysis' in pec_analysis:
            total_issues += len(pec_analysis['execution_analysis'].get('performance_issues', []))
        if unused_selectors_analysis:
            total_issues += unused_selectors_analysis.get('unused_selectors', 0)

        if total_issues > 0:
            report_lines.append(f"Total de oportunidades de otimização identificadas: {total_issues}")
            report_lines.append("")
            report_lines.append("✅ PRÓXIMOS PASSOS RECOMENDADOS:")
            report_lines.append("   1. Revisar funções com problemas de performance")
            report_lines.append("   2. Remover seletores não utilizados (começar pelos complexos)")
            report_lines.append("   3. Simplificar seletores desnecessariamente complexos")
            report_lines.append("   4. Implementar cache para seletores frequentemente usados")
            report_lines.append("   5. Adicionar validação de elementos antes do uso de seletores")
        else:
            report_lines.append("✅ Nenhuma otimização crítica identificada!")
            report_lines.append("   O código está bem otimizado.")

        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append(f"Relatório gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def save_optimization_report(self, report_content: str, filename: str = None) -> str:
        """Salva o relatório de otimização em arquivo"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_otimizacao_pec_{timestamp}.txt"

        filepath = os.path.join(os.getcwd(), filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)

            print(f"📄 Relatório salvo em: {filepath}")
            return filepath

        except Exception as e:
            print(f"⚠️ Erro ao salvar relatório: {e}")
            return None

    def run_complete_pec_analysis(self, pec_script_path: str = None) -> Dict:
        """Executa análise completa do sistema PEC e gera relatório"""
        print("🔍 Iniciando análise completa do sistema PEC...")
        print("=" * 60)

        if pec_script_path is None:
            # Procurar arquivo pec.py no diretório atual
            current_dir = os.getcwd()
            pec_script_path = os.path.join(current_dir, 'pec.py')

        if not os.path.exists(pec_script_path):
            print(f"⚠️ Arquivo PEC não encontrado: {pec_script_path}")
            return {'error': 'Arquivo PEC não encontrado'}

        # 1. Análise de execução PEC
        print("📊 Analisando execução PEC...")

        # Preparar dados PEC baseados nos dados de monitoramento
        pec_data = {
            'function_calls': [
                {
                    'function': exec['function'],
                    'execution_time': exec.get('execution_time', 0),
                    'success': exec.get('success_rate', 1.0) > 0.8
                }
                for exec in self.optimization_data['executions']
            ],
            'selectors_used': [],
            'execution_time': sum(exec.get('execution_time', 0) for exec in self.optimization_data['executions']),
            'errors': []
        }

        # Coletar todos os seletores utilizados
        all_selectors = []
        for exec in self.optimization_data['executions']:
            if 'selectors_used' in exec:
                for selector in exec['selectors_used']:
                    all_selectors.append({
                        'selector': selector,
                        'response_time': exec.get('execution_time', 0) / len(exec.get('selectors_used', [1])),
                        'found': True,
                        'context': exec['function']
                    })

        pec_data['selectors_used'] = all_selectors

        pec_analysis = self.analyze_pec_execution(pec_data)

        # 2. Extrair seletores utilizados durante a execução
        print("🎯 Extraindo seletores utilizados...")
        used_selectors = set()

        # Simular coleta de seletores utilizados (baseado nos dados de monitoramento)
        if hasattr(self, 'optimization_data') and 'executions' in self.optimization_data:
            for execution in self.optimization_data['executions']:
                if 'selectors_used' in execution:
                    used_selectors.update(execution['selectors_used'])

        # 3. Identificar seletores não utilizados
        print("🧹 Identificando seletores não utilizados...")
        unused_analysis = self.identify_unused_selectors(pec_script_path, used_selectors)

        # 4. Gerar relatório
        print("📄 Gerando relatório de otimização...")
        report = self.generate_pec_optimization_report(pec_analysis, unused_analysis)

        # 5. Salvar relatório
        print("💾 Salvando relatório...")
        report_file = self.save_optimization_report(report)

        # 6. Resultado final
        result = {
            'pec_analysis': pec_analysis,
            'unused_selectors_analysis': unused_analysis,
            'report_content': report,
            'report_file': report_file,
            'analysis_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_issues': unused_analysis.get('unused_selectors', 0) +
                              len(pec_analysis.get('execution_analysis', {}).get('performance_issues', [])),
                'selectors_analyzed': unused_analysis.get('total_selectors', 0),
                'functions_analyzed': pec_analysis.get('execution_analysis', {}).get('total_functions', 0)
            }
        }

        print("=" * 60)
        print("✅ Análise completa finalizada!")
        print(f"📊 Total de oportunidades de otimização: {result['summary']['total_issues']}")
        if report_file:
            print(f"📄 Relatório salvo em: {report_file}")
        print("=" * 60)

        return result

    def display_analysis_summary(self, analysis_result: Dict):
        """Exibe um resumo da análise no console"""
        if 'error' in analysis_result:
            print(f"❌ Erro na análise: {analysis_result['error']}")
            return

        summary = analysis_result.get('summary', {})

        print("\n" + "="*50)
        print("📊 RESUMO DA ANÁLISE PEC")
        print("="*50)
        print(f"🔍 Funções analisadas: {summary.get('functions_analyzed', 0)}")
        print(f"🎯 Seletores analisados: {summary.get('selectors_analyzed', 0)}")
        print(f"⚡ Oportunidades de otimização: {summary.get('total_issues', 0)}")

        if summary.get('total_issues', 0) > 0:
            print("\n💡 PRINCIPAIS RECOMENDAÇÕES:")
            unused_analysis = analysis_result.get('unused_selectors_analysis', {})
            if unused_analysis.get('cleanup_recommendations'):
                for rec in unused_analysis['cleanup_recommendations'][:3]:  # Top 3
                    print(f"  • {rec['description']}")
        else:
            print("\n✅ Sistema bem otimizado!")

        print("="*50)

    def generate_optimization_report(self) -> Dict:
        """Gera relatório completo de otimização"""
        print("📊 Gerando relatório de otimização...")

        # Estatísticas gerais
        total_selectors = len(self.optimization_data['selectors'])
        total_executions = len(self.optimization_data['executions'])

        # Seletores por performance
        high_performance = []
        low_performance = []
        unused = []

        for selector, stats in self.optimization_data['selectors'].items():
            if stats['confidence_score'] > 0.8 and stats['total_uses'] > 10:
                high_performance.append({
                    'selector': selector,
                    'confidence': stats['confidence_score'],
                    'avg_time': stats['avg_response_time'],
                    'uses': stats['total_uses']
                })
            elif stats['confidence_score'] < 0.4:
                low_performance.append({
                    'selector': selector,
                    'confidence': stats['confidence_score'],
                    'uses': stats['total_uses']
                })

        # Análise de funções
        function_performance = defaultdict(list)
        for execution in self.optimization_data['executions'][-100:]:  # Últimas 100 execuções
            function_performance[execution['function']].append(execution['success_rate'])

        function_stats = {}
        for func, rates in function_performance.items():
            function_stats[func] = {
                'avg_success_rate': sum(rates) / len(rates),
                'total_executions': len(rates)
            }

        report = {
            'summary': {
                'total_selectors_tracked': total_selectors,
                'total_executions_monitored': total_executions,
                'high_performance_selectors': len(high_performance),
                'low_performance_selectors': len(low_performance),
                'analysis_timestamp': datetime.now().isoformat()
            },
            'top_performers': sorted(high_performance, key=lambda x: x['confidence'], reverse=True)[:10],
            'needs_improvement': sorted(low_performance, key=lambda x: x['confidence'])[:10],
            'function_performance': function_stats,
            'recommendations': self.generate_recommendations()
        }

        return report

    def generate_recommendations(self) -> List[str]:
        """Gera recomendações de otimização"""
        recommendations = []

        # Recomendações baseadas em análise
        analysis = self.optimization_data.get('analysis', {})

        if analysis.get('unused_selectors'):
            unused_count = len(analysis['unused_selectors'])
            recommendations.append(f"🗑️ Remover {unused_count} seletores não utilizados do código")

        if analysis.get('low_usage_selectors'):
            low_count = len(analysis['low_usage_selectors'])
            recommendations.append(f"🔧 Otimizar {low_count} seletores com baixa performance")

        # Recomendações baseadas em estatísticas
        high_perf_count = sum(1 for s in self.optimization_data['selectors'].values()
                             if s['confidence_score'] > 0.8)
        if high_perf_count > 0:
            recommendations.append(f"✅ {high_perf_count} seletores com alta performance identificados")

        # Recomendações de funções
        function_recs = []
        for func, stats in self.optimization_data.get('function_performance', {}).items():
            if stats.get('avg_success_rate', 0) < 0.7:
                function_recs.append(func)

        if function_recs:
            recommendations.append(f"🎯 Otimizar funções: {', '.join(function_recs[:3])}")

        return recommendations

    def optimize_code_file(self, file_path: str) -> Dict:
        """Otimiza um arquivo específico baseado nos dados coletados"""
        print(f"🔧 Otimizando arquivo: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            changes_made = []

            # 1. Remover seletores não utilizados
            unused_selectors = set(self.optimization_data.get('analysis', {}).get('unused_selectors', []))
            for selector in unused_selectors:
                # Procurar e remover linhas com seletores não utilizados
                lines = content.split('\n')
                new_lines = []
                for line in lines:
                    if f"'{selector}'" in line or f'"{selector}"' in line:
                        changes_made.append(f"Removido seletor não utilizado: {selector}")
                        continue
                    new_lines.append(line)
                content = '\n'.join(new_lines)

            # 2. Substituir seletores de baixa performance por alternativas melhores
            for selector, stats in self.optimization_data['selectors'].items():
                if stats['confidence_score'] < 0.4 and stats['total_uses'] > 5:
                    # Encontrar seletor alternativo com melhor performance
                    alternative = self.find_better_selector(selector)
                    if alternative:
                        content = content.replace(f"'{selector}'", f"'{alternative}'")
                        content = content.replace(f'"{selector}"', f'"{alternative}"')
                        changes_made.append(f"Substituído {selector} → {alternative}")

            # Salvar arquivo otimizado se houve mudanças
            if content != original_content:
                # Se escrita não estiver habilitada, apenas retornar as mudanças propostas
                if not _monitor_write_enabled():
                    return {
                        'success': True,
                        'changes_made': changes_made,
                        'backup_created': None,
                        'message': 'Monitor em modo apenas leitura - não foram aplicadas alterações. Exporte PJE_MONITOR_WRITE=1 para permitir escrita.'
                    }

                backup_path = file_path + '.backup'
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                return {
                    'success': True,
                    'changes_made': changes_made,
                    'backup_created': backup_path
                }
            else:
                return {
                    'success': True,
                    'changes_made': [],
                    'message': 'Nenhuma otimização necessária'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def find_better_selector(self, bad_selector: str) -> Optional[str]:
        """Encontra um seletor melhor como alternativa"""
        # Procurar seletores similares com melhor performance
        for selector, stats in self.optimization_data['selectors'].items():
            if (stats['confidence_score'] > 0.7 and
                self.selectors_are_similar(bad_selector, selector)):
                return selector
        return None

    def selectors_are_similar(self, selector1: str, selector2: str) -> bool:
        """Verifica se dois seletores são similares"""
        # Lógica simples: mesmo tipo de elemento e atributo similar
        if ('input' in selector1 and 'input' in selector2) or \
           ('button' in selector1 and 'button' in selector2) or \
           ('select' in selector1 and 'select' in selector2):
            return True
        return False

    def run_full_optimization(self):
        """Executa otimização completa do projeto focando nos scripts prioritários"""
        print("🚀 Iniciando otimização completa do projeto PJePlus...")

        # 1. Analisar scripts prioritários
        print("\n📊 FASE 1: Análise dos Scripts Prioritários")
        priority_analysis = self.analyze_priority_scripts()

        # 2. Analisar codebase completo
        print("\n🔍 FASE 2: Análise Geral do Codebase")
        general_analysis = self.analyze_codebase()

        # 3. Gerar relatório abrangente
        print("\n📈 FASE 3: Geração de Relatório de Otimização")
        report = self.generate_comprehensive_report(priority_analysis, general_analysis)

        # 4. Identificar oportunidades específicas
        print("\n🎯 FASE 4: Identificação de Oportunidades Específicas")
        specific_recommendations = self.generate_specific_recommendations(priority_analysis)

        # 5. Otimizar arquivos (opcional - apenas se solicitado)
        optimization_results = []
        if self.should_optimize_files():
            print("\n🔧 FASE 5: Otimização de Arquivos")
            optimization_results = self.optimize_priority_files(priority_analysis)

        # 6. Salvar dados atualizados
        self.save_data()

        final_report = {
            'priority_analysis': priority_analysis,
            'general_analysis': general_analysis,
            'comprehensive_report': report,
            'specific_recommendations': specific_recommendations,
            'optimization_results': optimization_results,
            'timestamp': datetime.now().isoformat(),
            'scripts_optimized': list(self.priority_scripts.keys())
        }

        print("\n✅ OTIMIZAÇÃO COMPLETA CONCLUÍDA!")
        print(f"   • Scripts prioritários analisados: {priority_analysis['summary']['total_scripts_analyzed']}")
        print(f"   • Seletores identificados: {priority_analysis['summary']['total_selectors']}")
        print(f"   • Funções mapeadas: {priority_analysis['summary']['total_functions']}")
        print(f"   • Recomendações geradas: {len(specific_recommendations)}")

        return final_report

    def generate_comprehensive_report(self, priority_analysis: Dict, general_analysis: Dict) -> Dict:
        """Gera relatório abrangente combinando análises prioritárias e gerais"""
        return {
            'summary': {
                'total_priority_scripts': len(self.priority_scripts),
                'analyzed_scripts': priority_analysis['summary']['total_scripts_analyzed'],
                'total_selectors': priority_analysis['summary']['total_selectors'],
                'total_functions': priority_analysis['summary']['total_functions'],
                'common_selectors': len(priority_analysis['summary']['common_patterns']['common_selectors']),
                'common_functions': len(priority_analysis['summary']['common_patterns']['common_functions'])
            },
            'priority_scripts_status': {
                script_name: analysis.get('status', 'not_found')
                for script_name, analysis in priority_analysis['priority_scripts'].items()
            },
            'optimization_opportunities': priority_analysis['summary']['common_patterns']['optimization_opportunities'],
            'performance_insights': self.generate_performance_insights(priority_analysis)
        }

    def generate_specific_recommendations(self, priority_analysis: Dict) -> List[Dict]:
        """Gera recomendações específicas baseadas na análise dos scripts prioritários"""
        recommendations = []

        for script_name, analysis in priority_analysis['priority_scripts'].items():
            if analysis.get('status') == 'analyzed':
                script_recs = self.generate_script_recommendations(script_name, analysis)
                recommendations.extend(script_recs)

        # Adicionar recomendações globais
        global_recs = self.generate_global_recommendations(priority_analysis)
        recommendations.extend(global_recs)

        return recommendations

    def generate_script_recommendations(self, script_name: str, analysis: Dict) -> List[Dict]:
        """Gera recomendações específicas para um script"""
        recommendations = []

        # Recomendações baseadas em bottlenecks
        if 'bottlenecks' in analysis and analysis['bottlenecks']:
            for bottleneck in analysis['bottlenecks']:
                recommendations.append({
                    'type': 'bottleneck_fix',
                    'script': script_name,
                    'category': bottleneck['type'],
                    'description': bottleneck['description'],
                    'impact': bottleneck['impact'],
                    'suggestion': bottleneck['suggestion'],
                    'effort': 'medium'
                })

        # Recomendações baseadas em uso de Selenium
        if 'selenium_usage' in analysis and analysis['selenium_usage']:
            execute_script_count = sum(item['count'] for item in analysis['selenium_usage']
                                     if item['method'] == 'execute_script')
            if execute_script_count > 5:
                recommendations.append({
                    'type': 'selenium_optimization',
                    'script': script_name,
                    'category': 'javascript_execution',
                    'description': f'{execute_script_count} usos de execute_script detectados',
                    'impact': 'medium',
                    'suggestion': 'Otimizar para usar métodos Selenium nativos quando possível',
                    'effort': 'medium'
                })

        return recommendations

    def generate_global_recommendations(self, priority_analysis: Dict) -> List[Dict]:
        """Gera recomendações globais para todo o projeto"""
        recommendations = []

        common_patterns = priority_analysis['summary']['common_patterns']

        # Recomendação para funções comuns
        if common_patterns['common_functions']:
            recommendations.append({
                'type': 'code_deduplication',
                'script': 'global',
                'category': 'function_sharing',
                'description': f'{len(common_patterns["common_functions"])} funções comuns identificadas',
                'impact': 'high',
                'suggestion': 'Criar módulo compartilhado para funções comuns',
                'effort': 'high'
            })

        # Recomendação para seletores comuns
        if common_patterns['common_selectors']:
            recommendations.append({
                'type': 'selector_centralization',
                'script': 'global',
                'category': 'configuration',
                'description': f'{len(common_patterns["common_selectors"])} seletores compartilhados',
                'impact': 'medium',
                'suggestion': 'Centralizar configuração de seletores em arquivo único',
                'effort': 'low'
            })

        return recommendations

    def generate_performance_insights(self, priority_analysis: Dict) -> Dict:
        """Gera insights de performance baseados na análise"""
        insights = {
            'most_complex_script': None,
            'script_with_most_bottlenecks': None,
            'most_used_patterns': [],
            'optimization_potential': 'low'
        }

        max_functions = 0
        max_bottlenecks = 0

        for script_name, analysis in priority_analysis['priority_scripts'].items():
            if analysis.get('status') == 'analyzed':
                # Verificar script mais complexo
                if analysis.get('functions_count', 0) > max_functions:
                    max_functions = analysis['functions_count']
                    insights['most_complex_script'] = script_name

                # Verificar script com mais bottlenecks
                bottleneck_count = len(analysis.get('bottlenecks', []))
                if bottleneck_count > max_bottlenecks:
                    max_bottlenecks = bottleneck_count
                    insights['script_with_most_bottlenecks'] = script_name

        # Determinar potencial de otimização
        total_bottlenecks = sum(len(analysis.get('bottlenecks', []))
                               for analysis in priority_analysis['priority_scripts'].values()
                               if analysis.get('status') == 'analyzed')

        if total_bottlenecks > 10:
            insights['optimization_potential'] = 'high'
        elif total_bottlenecks > 5:
            insights['optimization_potential'] = 'medium'

        return insights

    def should_optimize_files(self) -> bool:
        """Determina se deve otimizar arquivos (sempre retorna False para segurança)"""
        return False  # Por segurança, nunca otimiza automaticamente

    def optimize_priority_files(self, priority_analysis: Dict) -> List[Dict]:
        """Otimiza apenas os arquivos prioritários (não implementado para segurança)"""
        return []

# Função global para integração com código existente
_optimizer_instance = None

def get_optimizer():
    """Retorna instância singleton do otimizador"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = Monitor()
    return _optimizer_instance


def gerar_relatorio_execucoes(output_file: str = None, read_only: bool = True) -> Optional[str]:
    """Gera um relatório consolidado de execuções usando dados já coletados.

    Esta função é segura por padrão (read_only=True) e NÃO modifica arquivos de código
    do projeto. Escreve apenas um arquivo de relatório (texto) com recomendações e
    métricas coletadas das execuções monitoradas.

    Args:
        output_file: caminho do arquivo de saída. Se None, o nome é auto-gerado.
        read_only: se False, permite operações adicionais de salvamento de dados
                   internos (não recomendado sem consentimento explícito).

    Returns:
        Caminho do arquivo gerado ou None em caso de erro.
    """

    optimizer = get_optimizer()

    # Carregar dados existentes se houver
    try:
        optimizer.load_data()
    except Exception:
        # load_data lida com exceções internamente; ignorar falhas aqui
        pass

    # Para segurança, garantir que não vamos executar otimizações que modifiquem código
    if read_only:
        # Temporariamente garantir que o monitor reconheça modo apenas leitura
        # (não altera global, apenas impede escrita nesta execução)
        write_allowed = _monitor_write_enabled()
        if write_allowed:
            # Não permitir escrita se read_only solicitado
            os.environ.pop('PJE_MONITOR_WRITE', None)

    # Gerar relatório completo baseado nos dados de otimização/execução
    try:
        # Prefer using the high-level PEC analysis / report generator if available
        report = optimizer.generate_pec_optimization_report(
            optimizer.analyze_pec_execution({
                'function_calls': [],
                'selectors_used': [],
                'execution_time': 0,
                'errors': []
            }),
            optimizer.identify_unused_selectors(os.path.join(os.getcwd(), 'pec.py'), set())
        )

        # Save the report to a file using the existing helper which writes only report files
        report_path = optimizer.save_optimization_report(report, filename=output_file)

    except Exception as e:
        print(f"⚠️ Erro ao gerar relatório de execuções: {e}")
        return None

    return report_path

def monitor_function_execution(function_name: str, selectors_used: List[Dict], total_time: float, success_rate: float):
    """Função para monitorar execuções de funções existentes"""
    optimizer = get_optimizer()

    execution_data = {
        'selectors_used': selectors_used,
        'total_time': total_time,
        'success_rate': success_rate,
        'errors': [],
        'page_context': {}
    }

    # Adicionar à instância do otimizador
    optimizer.add_execution_record(function_name, execution_data)

class AdaptationSystem:
    """
    Sistema de adaptação automática que ajusta configurações baseado na performance real
    """

    def __init__(self):
        self.adaptation_history = []
        self.current_mode = 'normal'  # normal, defensive, aggressive
        self.last_adaptation = None

    def adapt_based_on_performance(self, execution_record: Dict):
        """Adapta configurações baseado na performance da execução"""
        success_rate = execution_record['success_rate']
        total_time = execution_record['total_time']
        environment = execution_record.get('environment_conditions', {})

        # Lógica de adaptação baseada em múltiplos fatores
        adaptation_needed = self._analyze_adaptation_need(
            success_rate, total_time, environment
        )

        if adaptation_needed:
            self._apply_adaptation(adaptation_needed, execution_record)
            self._log_adaptation(adaptation_needed, execution_record)

    def _analyze_adaptation_need(self, success_rate: float, total_time: float,
                                environment: Dict) -> Optional[Dict]:
        """Analisa se adaptação é necessária"""

        # Critérios para adaptação
        if success_rate < 0.5:
            return {
                'type': 'defensive_mode',
                'reason': 'taxa_sucesso_baixa',
                'priority': 'high'
            }

        if total_time > 30 and success_rate > 0.8:
            return {
                'type': 'optimize_timeouts',
                'reason': 'tempo_alto_com_sucesso',
                'priority': 'medium'
            }

        if environment.get('estimated_load') == 'high':
            return {
                'type': 'environment_adaptation',
                'reason': 'ambiente_carregado',
                'priority': 'medium'
            }

        return None

    def _apply_adaptation(self, adaptation: Dict, execution_record: Dict):
        """Aplica a adaptação necessária"""
        adaptation_type = adaptation['type']

        if adaptation_type == 'defensive_mode':
            self._activate_defensive_mode()
        elif adaptation_type == 'optimize_timeouts':
            self._optimize_timeouts(execution_record)
        elif adaptation_type == 'environment_adaptation':
            self._adapt_to_environment(execution_record)

    def _activate_defensive_mode(self):
        """Ativa modo defensivo com configurações mais conservadoras"""
        try:
            # Importar configurações dinamicamente
            import sys
            sys.path.append(self.workspace_path)

            # Tentar importar e ajustar configurações
            try:
                from Fix import selenium_config
                selenium_config.TIMEOUT_NORMAL = min(25, selenium_config.TIMEOUT_NORMAL * 1.5)
                selenium_config.VELOCIDADE_INTERACAO['normal'] = 1.2
                print("🛡️ Modo defensivo ativado - configurações ajustadas")
            except ImportError:
                print("⚠️ Não foi possível ajustar configurações - Fix.py não encontrado")

        except Exception as e:
            print(f"⚠️ Erro ao ativar modo defensivo: {e}")

    def _optimize_timeouts(self, execution_record: Dict):
        """Otimiza timeouts baseado na performance real"""
        try:
            from Fix import selenium_config
            total_time = execution_record['total_time']

            # Se execução foi rápida mas timeout alto, reduzir
            if total_time < 5 and selenium_config.TIMEOUT_NORMAL > 15:
                selenium_config.TIMEOUT_NORMAL = max(8, selenium_config.TIMEOUT_NORMAL * 0.7)
                print(f"⚡ Timeout otimizado: {selenium_config.TIMEOUT_NORMAL:.1f}s")

        except Exception as e:
            print(f"⚠️ Erro ao otimizar timeouts: {e}")

    def _adapt_to_environment(self, execution_record: Dict):
        """Adapta às condições do ambiente"""
        try:
            from Fix import selenium_config
            environment = execution_record.get('environment_conditions', {})

            if environment.get('estimated_load') == 'high':
                selenium_config.TIMEOUT_NORMAL = min(30, selenium_config.TIMEOUT_NORMAL * 1.3)
                selenium_config.VELOCIDADE_INTERACAO['normal'] = 1.5
                print("🏭 Adaptação para ambiente carregado")

        except Exception as e:
            print(f"⚠️ Erro na adaptação ambiental: {e}")

    def _log_adaptation(self, adaptation: Dict, execution_record: Dict):
        """Registra a adaptação aplicada"""
        adaptation_record = {
            'timestamp': datetime.now().isoformat(),
            'type': adaptation['type'],
            'reason': adaptation['reason'],
            'function': execution_record['function'],
            'before_metrics': {
                'success_rate': execution_record['success_rate'],
                'total_time': execution_record['total_time']
            }
        }

        self.adaptation_history.append(adaptation_record)

        # Manter apenas últimas 50 adaptações
        if len(self.adaptation_history) > 50:
            self.adaptation_history = self.adaptation_history[-50:]

class PerformanceAnalyzer:
    """
    Analisador de performance que detecta anomalias e tendências
    """

    def __init__(self):
        self.performance_baseline = {}
        self.anomaly_threshold = 0.2  # 20% de variação
        self.trend_window = 10  # Análise das últimas 10 execuções

    def analyze_execution(self, execution_record: Dict):
        """Analisa uma execução e atualiza métricas de performance"""
        function_name = execution_record['function']
        success_rate = execution_record['success_rate']
        total_time = execution_record['total_time']

        # Atualizar baseline da função
        if function_name not in self.performance_baseline:
            self.performance_baseline[function_name] = {
                'executions': [],
                'avg_success_rate': success_rate,
                'avg_time': total_time,
                'stability_score': 1.0
            }

        baseline = self.performance_baseline[function_name]

        # Adicionar execução ao histórico
        baseline['executions'].append({
            'timestamp': execution_record['timestamp'],
            'success_rate': success_rate,
            'total_time': total_time
        })

        # Manter apenas últimas execuções
        if len(baseline['executions']) > self.trend_window:
            baseline['executions'] = baseline['executions'][-self.trend_window:]

        # Recalcular médias
        recent_executions = baseline['executions']
        if recent_executions:
            baseline['avg_success_rate'] = sum(ex['success_rate'] for ex in recent_executions) / len(recent_executions)
            baseline['avg_time'] = sum(ex['total_time'] for ex in recent_executions) / len(recent_executions)

        # Calcular score de estabilidade
        baseline['stability_score'] = self._calculate_stability_score(recent_executions)

        # Detectar anomalias
        anomaly = self._detect_anomaly(function_name, success_rate, total_time)
        if anomaly:
            self._handle_anomaly(anomaly, execution_record)

    def _calculate_stability_score(self, executions: List[Dict]) -> float:
        """Calcula score de estabilidade baseado na variabilidade"""
        if len(executions) < 3:
            return 1.0

        success_rates = [ex['success_rate'] for ex in executions]
        times = [ex['total_time'] for ex in executions]

        # Calcular variabilidade
        success_variability = max(success_rates) - min(success_rates)
        time_variability = max(times) - min(times) / max(times) if max(times) > 0 else 0

        # Score de estabilidade (0-1, onde 1 é mais estável)
        stability = 1 - (success_variability * 0.5 + time_variability * 0.5)
        return max(0, min(1, stability))

    def _detect_anomaly(self, function_name: str, success_rate: float, total_time: float) -> Optional[Dict]:
        """Detecta anomalias na performance"""
        baseline = self.performance_baseline[function_name]

        # Verificar se há dados suficientes
        if len(baseline['executions']) < 3:
            return None

        # Calcular desvios
        success_deviation = abs(success_rate - baseline['avg_success_rate']) / max(0.1, baseline['avg_success_rate'])
        time_deviation = abs(total_time - baseline['avg_time']) / max(1, baseline['avg_time'])

        # Detectar anomalia
        if success_deviation > self.anomaly_threshold or time_deviation > self.anomaly_threshold:
            return {
                'function': function_name,
                'type': 'performance_anomaly',
                'success_deviation': success_deviation,
                'time_deviation': time_deviation,
                'current_success': success_rate,
                'current_time': total_time,
                'baseline_success': baseline['avg_success_rate'],
                'baseline_time': baseline['avg_time']
            }

        return None

    def _handle_anomaly(self, anomaly: Dict, execution_record: Dict):
        """Trata anomalia detectada"""
        print(f"🚨 Anomalia detectada em {anomaly['function']}:")
        print(f"   Taxa de sucesso: {anomaly['current_success']:.1%} (baseline: {anomaly['baseline_success']:.1%})")
        print(f"   Tempo: {anomaly['current_time']:.1f}s (baseline: {anomaly['baseline_time']:.1f}s)")

        # Registrar anomalia no sistema de monitoramento
        try:
            from Fix import log_smart
            log_smart(f"Anomalia de performance detectada em {anomaly['function']}",
                     'WARN', f"Sucesso: {anomaly['current_success']:.1%}, Tempo: {anomaly['current_time']:.1f}s")
        except ImportError:
            print("⚠️ Sistema de logging não disponível")

# Função global para integração com código existente
_monitor_instance = None

def get_monitor():
    """Retorna instância singleton do monitor"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = AdaptationSystem()
    return _monitor_instance

def monitor_function_execution(function_name: str, selectors_used: List[Dict], total_time: float, success_rate: float):
    """Função para monitorar execuções de funções existentes"""
    monitor = get_monitor()

    execution_data = {
        'selectors_used': selectors_used,
        'total_time': total_time,
        'success_rate': success_rate,
        'errors': [],
        'page_context': {}
    }

    monitor.monitor_execution(function_name, execution_data)

# Exemplo de uso
if __name__ == "__main__":
    monitor = Monitor()

    # Simular monitoramento de execução
    sample_execution = {
        'selectors_used': [
            {'selector': 'input[placeholder="CPF/CNPJ"]', 'success': True, 'response_time': 1.2},
            {'selector': 'button[aria-label="Salvar"]', 'success': False, 'response_time': 3.1},
            {'selector': 'mat-select[name="vara"]', 'success': True, 'response_time': 0.8}
        ],
        'total_time': 5.1,
        'success_rate': 0.67
    }

    monitor.monitor_execution('minuta_bloqueio', sample_execution)

    # Executar análise completa
    results = monitor.export_monitoring_report()

    print("\n" + "="*60)
    print("📊 RESULTADO DO MONITORAMENTO")
    print("="*60)
    print(f"Execuções monitoradas: {results['summary']['total_executions']}")
    print(f"Seletores analisados: {results['summary']['total_selectors']}")
    print(f"Modo de adaptação: {results['summary']['current_adaptation_mode']}")

    print("\n🔧 RECOMENDAÇÕES:")
    for rec in results['recommendations']:
        print(f"  • {rec['description']} ({rec['priority']})")

    print("\n✅ MONITORAMENTO CONCLUÍDO!")

    def analisar_loop_p2b_com_funcoes_existentes(self):
        """
        Analisa loop.py e p2b.py usando APENAS as funções já existentes no monitor.py
        SEM criar novas funções ou alterar os scripts originais
        """
        print("🔍 ANÁLISE DE LOOP.PY E P2B.PY - USANDO FUNÇÕES EXISTENTES")
        print("=" * 60)

        # 1. Usar analyze_priority_scripts() - função já existente
        print("📊 1. Executando análise de scripts prioritários...")
        priority_analysis = self.analyze_priority_scripts()

        # 2. Análise específica de loop.py usando analyze_script_detailed()
        loop_path = os.path.join(self.workspace_path, 'loop.py')
        if os.path.exists(loop_path):
            print("\n🔄 2. Análise detalhada de loop.py...")
            loop_analysis = self.analyze_script_detailed(loop_path, 'loop.py')

            print("   📈 MÉTRICAS LOOP.PY:")
            print(f"   • Arquivo: {loop_analysis['line_count']} linhas")
            print(f"   • Seletores: {loop_analysis['selectors_count']}")
            print(f"   • Funções: {loop_analysis['functions_count']}")
            print(f"   • Usos Selenium: {len(loop_analysis['selenium_usage'])}")
            print(f"   • Bottlenecks: {len(loop_analysis['bottlenecks'])}")

            # Identificar possíveis problemas de loop
            if loop_analysis['selectors_count'] > 0:
                print("   🎯 SELETORES ENCONTRADOS:")
                for i, selector in enumerate(loop_analysis['selectors'][:5]):  # Top 5
                    print(f"     {i+1}. {selector}")

            if loop_analysis['bottlenecks']:
                print("   🚨 BOTTLENECKS IDENTIFICADOS:")
                for bottleneck in loop_analysis['bottlenecks'][:3]:  # Top 3
                    print(f"     • {bottleneck}")

        # 3. Análise específica de p2b.py usando analyze_script_detailed()
        p2b_path = os.path.join(self.workspace_path, 'p2b.py')
        if os.path.exists(p2b_path):
            print("\n📊 3. Análise detalhada de p2b.py...")
            p2b_analysis = self.analyze_script_detailed(p2b_path, 'p2b.py')

            print("   📈 MÉTRICAS P2B.PY:")
            print(f"   • Arquivo: {p2b_analysis['line_count']} linhas")
            print(f"   • Seletores: {p2b_analysis['selectors_count']}")
            print(f"   • Funções: {p2b_analysis['functions_count']}")
            print(f"   • Usos Selenium: {len(p2b_analysis['selenium_usage'])}")
            print(f"   • Bottlenecks: {len(p2b_analysis['bottlenecks'])}")

            # Identificar possíveis problemas de processamento
            if p2b_analysis['selectors_count'] > 0:
                print("   🎯 SELETORES ENCONTRADOS:")
                for i, selector in enumerate(p2b_analysis['selectors'][:5]):  # Top 5
                    print(f"     {i+1}. {selector}")

            if p2b_analysis['bottlenecks']:
                print("   🚨 BOTTLENECKS IDENTIFICADOS:")
                for bottleneck in p2b_analysis['bottlenecks'][:3]:  # Top 3
                    print(f"     • {bottleneck}")

        # 4. Usar get_adaptation_recommendations() - função já existente
        print("\n💡 4. Gerando recomendações de adaptação...")
        recommendations = self.get_adaptation_recommendations()

        # 5. Gerar relatório final usando dados coletados
        print("\n📄 5. Gerando relatório de otimização...")
        relatorio = self._gerar_relatorio_loop_p2b_existente(loop_analysis if 'loop_analysis' in locals() else None,
                                                           p2b_analysis if 'p2b_analysis' in locals() else None,
                                                           recommendations)

        # Salvar relatório
        arquivo_relatorio = self.save_comprehensive_report(relatorio, "relatorio_otimizacao_loop_p2b_existente.txt")

        print("\n" + "="*60)
        print("✅ ANÁLISE CONCLUÍDA COM SUCESSO!")
        print("🔧 Scripts originais NÃO foram alterados")
        print("📊 Usadas APENAS funções já existentes no monitor.py")
        print(f"📄 Relatório salvo: {arquivo_relatorio}")
        print("="*60)

        return {
            'loop_analysis': loop_analysis if 'loop_analysis' in locals() else None,
            'p2b_analysis': p2b_analysis if 'p2b_analysis' in locals() else None,
            'recommendations': recommendations,
            'relatorio': relatorio,
            'arquivo_relatorio': arquivo_relatorio
        }

    def _gerar_relatorio_loop_p2b_existente(self, loop_analysis, p2b_analysis, recommendations):
        """Gera relatório usando dados das funções existentes"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RELATÓRIO DE OTIMIZAÇÃO - LOOP.PY E P2B.PY")
        report_lines.append("USANDO APENAS FUNÇÕES EXISTENTES DO MONITOR.PY")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Análise Loop.py
        if loop_analysis:
            report_lines.append("🔄 ANÁLISE LOOP.PY")
            report_lines.append("-" * 40)
            report_lines.append(f"Arquivo: {loop_analysis['line_count']} linhas")
            report_lines.append(f"Seletores encontrados: {loop_analysis['selectors_count']}")
            report_lines.append(f"Funções identificadas: {loop_analysis['functions_count']}")
            report_lines.append(f"Usos de Selenium: {len(loop_analysis['selenium_usage'])}")
            report_lines.append(f"Bottlenecks detectados: {len(loop_analysis['bottlenecks'])}")
            report_lines.append("")

            if loop_analysis['selectors']:
                report_lines.append("SELETORES PRINCIPAIS:")
                for selector in loop_analysis['selectors'][:10]:  # Top 10
                    report_lines.append(f"  • {selector}")
                report_lines.append("")

            if loop_analysis['bottlenecks']:
                report_lines.append("PROBLEMAS IDENTIFICADOS:")
                for bottleneck in loop_analysis['bottlenecks']:
                    report_lines.append(f"  • {bottleneck}")
                report_lines.append("")

        # Análise P2B.py
        if p2b_analysis:
            report_lines.append("📊 ANÁLISE P2B.PY")
            report_lines.append("-" * 40)
            report_lines.append(f"Arquivo: {p2b_analysis['line_count']} linhas")
            report_lines.append(f"Seletores encontrados: {p2b_analysis['selectors_count']}")
            report_lines.append(f"Funções identificadas: {p2b_analysis['functions_count']}")
            report_lines.append(f"Usos de Selenium: {len(p2b_analysis['selenium_usage'])}")
            report_lines.append(f"Bottlenecks detectados: {len(p2b_analysis['bottlenecks'])}")
            report_lines.append("")

            if p2b_analysis['selectors']:
                report_lines.append("SELETORES PRINCIPAIS:")
                for selector in p2b_analysis['selectors'][:10]:  # Top 10
                    report_lines.append(f"  • {selector}")
                report_lines.append("")

            if p2b_analysis['bottlenecks']:
                report_lines.append("PROBLEMAS IDENTIFICADOS:")
                for bottleneck in p2b_analysis['bottlenecks']:
                    report_lines.append(f"  • {bottleneck}")
                report_lines.append("")

        # Recomendações gerais
        report_lines.append("💡 RECOMENDAÇÕES GERAIS")
        report_lines.append("-" * 40)

        total_problems = 0
        if loop_analysis:
            total_problems += len(loop_analysis['bottlenecks'])
        if p2b_analysis:
            total_problems += len(p2b_analysis['bottlenecks'])

        if total_problems > 0:
            report_lines.append(f"Total de problemas identificados: {total_problems}")
            report_lines.append("")
            report_lines.append("PRÓXIMOS PASSOS RECOMENDADOS:")
            report_lines.append("  1. Revisar seletores identificados para possíveis conflitos")
            report_lines.append("  2. Implementar melhor tratamento de erros nos bottlenecks")
            report_lines.append("  3. Considerar otimização de seletores mais específicos")
            report_lines.append("  4. Adicionar validação de elementos antes do uso")
            report_lines.append("  5. Implementar sistema de retry para operações críticas")
        else:
            report_lines.append("✅ Nenhum problema crítico identificado!")
            report_lines.append("   Os scripts estão bem estruturados.")

        # Adicionar recomendações do sistema de adaptação
        if recommendations:
            report_lines.append("")
            report_lines.append("ADAPTAÇÕES RECOMENDADAS:")
            for rec in recommendations[:5]:  # Top 5
                report_lines.append(f"  • {rec.get('description', 'Recomendação geral')}")

        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append(f"Relatório gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("Análise realizada usando funções existentes do monitor.py")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def save_comprehensive_report(self, content: str, filename: str) -> str:
        """
        Análise específica para execução de loop.py
        Monitora loops, iterações e detecta padrões de repetição
        """
        print("\n🔄 ANALISANDO EXECUÇÃO LOOP.PY...")

        if loop_data is None:
            # Simular coleta de dados baseada no histórico de execuções
            loop_data = self._collect_loop_execution_data()

        # Análise de padrões de loop
        loop_patterns = self._analyze_loop_patterns(loop_data)

        # Detecção de loops infinitos potenciais
        infinite_loop_risks = self._detect_infinite_loop_risks(loop_data)

        # Análise de performance por iteração
        iteration_performance = self._analyze_iteration_performance(loop_data)

        # Identificação de gargalos
        bottlenecks = self._identify_loop_bottlenecks(loop_data)

        # Geração de recomendações específicas para loop.py
        recommendations = self._generate_loop_recommendations(
            loop_patterns, infinite_loop_risks, iteration_performance, bottlenecks
        )

        analysis_result = {
            'script_name': 'loop.py',
            'analysis_timestamp': datetime.now().isoformat(),
            'loop_patterns': loop_patterns,
            'infinite_loop_risks': infinite_loop_risks,
            'iteration_performance': iteration_performance,
            'bottlenecks': bottlenecks,
            'recommendations': recommendations,
            'optimization_score': self._calculate_loop_optimization_score(recommendations)
        }

        # Armazenar análise
        self.monitoring_data['loop_analysis'] = analysis_result

        return analysis_result

    def analyze_p2b_execution(self, p2b_data: Dict = None) -> Dict:
        """
        Análise específica para execução de p2b.py
        Monitora processamento P2B, extrações e conversões
        """
        print("\n📊 ANALISANDO EXECUÇÃO P2B.PY...")

        if p2b_data is None:
            # Simular coleta de dados baseada no histórico de execuções
            p2b_data = self._collect_p2b_execution_data()

        # Análise de processamento de dados
        data_processing = self._analyze_p2b_data_processing(p2b_data)

        # Análise de extrações e conversões
        extraction_analysis = self._analyze_p2b_extractions(p2b_data)

        # Análise de performance por tipo de operação
        operation_performance = self._analyze_p2b_operation_performance(p2b_data)

        # Detecção de falhas recorrentes
        failure_patterns = self._detect_p2b_failure_patterns(p2b_data)

        # Geração de recomendações específicas para p2b.py
        recommendations = self._generate_p2b_recommendations(
            data_processing, extraction_analysis, operation_performance, failure_patterns
        )

        analysis_result = {
            'script_name': 'p2b.py',
            'analysis_timestamp': datetime.now().isoformat(),
            'data_processing': data_processing,
            'extraction_analysis': extraction_analysis,
            'operation_performance': operation_performance,
            'failure_patterns': failure_patterns,
            'recommendations': recommendations,
            'optimization_score': self._calculate_p2b_optimization_score(recommendations)
        }

        # Armazenar análise
        self.monitoring_data['p2b_analysis'] = analysis_result

        return analysis_result

    def _collect_loop_execution_data(self) -> Dict:
        """Coleta dados de execução do loop.py baseado no histórico"""
        loop_executions = [
            exec for exec in self.monitoring_data['executions']
            if exec.get('script', '').lower() == 'loop.py' or 'loop' in exec.get('function', '').lower()
        ]

        return {
            'total_executions': len(loop_executions),
            'execution_times': [exec.get('execution_time', 0) for exec in loop_executions],
            'success_rates': [exec.get('success_rate', 0) for exec in loop_executions],
            'functions_called': [exec.get('function', '') for exec in loop_executions],
            'selectors_used': [
                selector for exec in loop_executions
                for selector in exec.get('selectors_used', [])
            ],
            'error_patterns': [
                exec.get('error', '') for exec in loop_executions
                if exec.get('error')
            ]
        }

    def _collect_p2b_execution_data(self) -> Dict:
        """Coleta dados de execução do p2b.py baseado no histórico"""
        p2b_executions = [
            exec for exec in self.monitoring_data['executions']
            if exec.get('script', '').lower() == 'p2b.py' or 'p2b' in exec.get('function', '').lower()
        ]

        return {
            'total_executions': len(p2b_executions),
            'execution_times': [exec.get('execution_time', 0) for exec in p2b_executions],
            'success_rates': [exec.get('success_rate', 0) for exec in p2b_executions],
            'data_processed': [exec.get('data_items', 0) for exec in p2b_executions],
            'extraction_methods': [exec.get('extraction_method', '') for exec in p2b_executions],
            'conversion_rates': [exec.get('conversion_success', 0) for exec in p2b_executions],
            'selectors_used': [
                selector for exec in p2b_executions
                for selector in exec.get('selectors_used', [])
            ],
            'error_patterns': [
                exec.get('error', '') for exec in p2b_executions
                if exec.get('error')
            ]
        }

    def _analyze_loop_patterns(self, loop_data: Dict) -> Dict:
        """Analisa padrões de execução do loop"""
        functions = loop_data.get('functions_called', [])
        execution_times = loop_data.get('execution_times', [])

        # Padrões de função mais executadas
        function_counts = Counter(functions)

        # Análise de tempo de execução
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        max_time = max(execution_times) if execution_times else 0
        min_time = min(execution_times) if execution_times else 0

        # Detecção de padrões temporais
        time_variance = max_time - min_time if execution_times else 0

        return {
            'most_frequent_functions': dict(function_counts.most_common(5)),
            'avg_execution_time': avg_time,
            'max_execution_time': max_time,
            'min_execution_time': min_time,
            'time_variance': time_variance,
            'total_unique_functions': len(function_counts)
        }

    def _analyze_p2b_data_processing(self, p2b_data: Dict) -> Dict:
        """Analisa processamento de dados do P2B"""
        data_processed = p2b_data.get('data_processed', [])
        conversion_rates = p2b_data.get('conversion_rates', [])
        extraction_methods = p2b_data.get('extraction_methods', [])

        # Estatísticas de processamento
        total_data = sum(data_processed) if data_processed else 0
        avg_conversion = sum(conversion_rates) / len(conversion_rates) if conversion_rates else 0

        # Métodos de extração mais usados
        method_counts = Counter(extraction_methods)

        return {
            'total_data_processed': total_data,
            'avg_data_per_execution': total_data / len(data_processed) if data_processed else 0,
            'avg_conversion_rate': avg_conversion,
            'extraction_methods': dict(method_counts.most_common(3)),
            'processing_efficiency': avg_conversion * (total_data / max(len(data_processed), 1))
        }

    def _detect_infinite_loop_risks(self, loop_data: Dict) -> List[Dict]:
        """Detecta riscos de loops infinitos"""
        risks = []

        execution_times = loop_data.get('execution_times', [])
        functions = loop_data.get('functions_called', [])

        # Risco baseado em tempo de execução crescente
        if len(execution_times) > 5:
            recent_times = execution_times[-5:]
            if recent_times[-1] > recent_times[0] * 1.5:  # Aumento de 50%
                risks.append({
                    'type': 'increasing_execution_time',
                    'severity': 'high',
                    'description': 'Tempo de execução aumentando progressivamente',
                    'evidence': f'Última: {recent_times[-1]:.2f}s, Primeira: {recent_times[0]:.2f}s'
                })

        # Risco baseado em funções repetitivas sem progresso
        if len(functions) > 10:
            recent_functions = functions[-10:]
            if len(set(recent_functions)) <= 2:  # Pouca variação
                risks.append({
                    'type': 'lack_of_progress',
                    'severity': 'medium',
                    'description': 'Pouca variação nas funções executadas',
                    'evidence': f'Apenas {len(set(recent_functions))} funções diferentes nas últimas 10 execuções'
                })

        return risks

    def _detect_p2b_failure_patterns(self, p2b_data: Dict) -> List[Dict]:
        """Detecta padrões de falha no P2B"""
        patterns = []
        error_patterns = p2b_data.get('error_patterns', [])

        if error_patterns:
            error_counts = Counter(error_patterns)

            for error, count in error_counts.most_common(3):
                if count > 2:  # Erro recorrente
                    patterns.append({
                        'error_type': error,
                        'frequency': count,
                        'severity': 'high' if count > 5 else 'medium',
                        'description': f'Erro recorrente: {error[:50]}...'
                    })

        # Padrão de baixa taxa de conversão
        conversion_rates = p2b_data.get('conversion_rates', [])
        if conversion_rates:
            avg_conversion = sum(conversion_rates) / len(conversion_rates)
            if avg_conversion < 0.5:  # Menos de 50% de sucesso
                patterns.append({
                    'error_type': 'low_conversion_rate',
                    'frequency': len([r for r in conversion_rates if r < 0.5]),
                    'severity': 'medium',
                    'description': f'Taxa de conversão baixa: {avg_conversion:.1%}'
                })

        return patterns

    def _generate_loop_recommendations(self, patterns: Dict, risks: List, performance: Dict, bottlenecks: List) -> List[Dict]:
        """Gera recomendações específicas para loop.py"""
        recommendations = []

        # Recomendações baseadas em riscos de loop infinito
        for risk in risks:
            if risk['type'] == 'increasing_execution_time':
                recommendations.append({
                    'type': 'loop_optimization',
                    'description': 'Implementar timeout e verificação de progresso em cada iteração',
                    'priority': 'high',
                    'implementation': 'Adicionar contador de iterações e verificação de estado'
                })
            elif risk['type'] == 'lack_of_progress':
                recommendations.append({
                    'type': 'progress_tracking',
                    'description': 'Adicionar tracking de progresso para detectar iterações improdutivas',
                    'priority': 'medium',
                    'implementation': 'Implementar verificação de mudança de estado entre iterações'
                })

        # Recomendações baseadas em performance
        if patterns.get('time_variance', 0) > 10:  # Variação alta
            recommendations.append({
                'type': 'performance_optimization',
                'description': 'Otimizar funções com tempo de execução variável',
                'priority': 'medium',
                'implementation': 'Identificar e otimizar gargalos de performance'
            })

        # Recomendação geral de monitoramento
        recommendations.append({
            'type': 'monitoring_enhancement',
            'description': 'Melhorar sistema de debug para identificação de seletores múltiplos',
            'priority': 'low',
            'implementation': 'Adicionar logs detalhados quando múltiplos seletores são encontrados'
        })

        return recommendations

    def _generate_p2b_recommendations(self, data_proc: Dict, extraction: Dict, performance: Dict, failures: List) -> List[Dict]:
        """Gera recomendações específicas para p2b.py"""
        recommendations = []

        # Recomendações baseadas em falhas
        for failure in failures:
            if failure['error_type'] == 'low_conversion_rate':
                recommendations.append({
                    'type': 'extraction_optimization',
                    'description': 'Melhorar métodos de extração de dados para aumentar taxa de conversão',
                    'priority': 'high',
                    'implementation': 'Implementar fallback methods e validação de dados'
                })

        # Recomendações baseadas em processamento
        if data_proc.get('processing_efficiency', 1) < 0.7:  # Eficiência baixa
            recommendations.append({
                'type': 'data_processing_optimization',
                'description': 'Otimizar processamento de dados para melhorar eficiência',
                'priority': 'medium',
                'implementation': 'Implementar processamento em lotes e cache de dados'
            })

        # Recomendação de debug aprimorado
        recommendations.append({
            'type': 'debug_enhancement',
            'description': 'Aprimorar debug para casos com múltiplos seletores similares',
            'priority': 'low',
            'implementation': 'Adicionar identificação contextual de seletores durante debug'
        })

        return recommendations

    def _calculate_loop_optimization_score(self, recommendations: List) -> float:
        """Calcula score de otimização para loop.py"""
        base_score = 100

        for rec in recommendations:
            if rec['priority'] == 'high':
                base_score -= 20
            elif rec['priority'] == 'medium':
                base_score -= 10
            else:
                base_score -= 5

        return max(0, base_score)

    def _calculate_p2b_optimization_score(self, recommendations: List) -> float:
        """Calcula score de otimização para p2b.py"""
        base_score = 100

        for rec in recommendations:
            if rec['priority'] == 'high':
                base_score -= 25
            elif rec['priority'] == 'medium':
                base_score -= 15
            else:
                base_score -= 5

        return max(0, base_score)

    def enhanced_debug_selector_identification(self, driver, action_description: str, selectors: List[str], context: str = "") -> Dict:
        """
        Sistema aprimorado de debug para identificação de seletores quando há múltiplos
        Única alteração permitida nos scripts - melhoria do debug
        """
        print(f"\n🔍 [DEBUG APRIMORADO] {action_description}")
        print(f"📍 Contexto: {context}")
        print(f"🎯 Seletores candidatos: {len(selectors)}")

        results = {
            'action': action_description,
            'context': context,
            'total_candidates': len(selectors),
            'found_elements': [],
            'recommended_selector': None,
            'debug_info': {}
        }

        for i, selector in enumerate(selectors):
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                element_count = len(elements)

                element_info = {
                    'selector': selector,
                    'count': element_count,
                    'visible': 0,
                    'clickable': 0,
                    'attributes': []
                }

                # Analisar elementos encontrados
                for j, element in enumerate(elements[:5]):  # Analisar até 5 elementos
                    try:
                        is_visible = element.is_displayed()
                        if is_visible:
                            element_info['visible'] += 1

                        # Verificar se é clicável
                        if element.tag_name in ['button', 'input', 'a'] or element.get_attribute('onclick'):
                            element_info['clickable'] += 1

                        # Coletar atributos relevantes
                        attrs = {}
                        for attr in ['id', 'class', 'name', 'type', 'aria-label', 'title']:
                            value = element.get_attribute(attr)
                            if value:
                                attrs[attr] = value

                        element_info['attributes'].append({
                            'index': j,
                            'visible': is_visible,
                            'clickable': element.tag_name in ['button', 'input', 'a'],
                            'attributes': attrs,
                            'text': element.text[:50] if element.text else ''
                        })

                    except Exception as e:
                        element_info['attributes'].append({
                            'index': j,
                            'error': str(e)
                        })

                results['found_elements'].append(element_info)

                print(f"  {i+1:2d}. '{selector}' → {element_count} elementos")
                if element_count > 0:
                    print(f"      ✅ Visíveis: {element_info['visible']}, Clicáveis: {element_info['clickable']}")

            except Exception as e:
                print(f"  {i+1:2d}. '{selector}' → ERRO: {e}")
                results['found_elements'].append({
                    'selector': selector,
                    'count': 0,
                    'error': str(e)
                })

        # Recomendar melhor seletor
        if results['found_elements']:
            # Priorizar: 1 elemento visível e clicável > 1 elemento visível > menor quantidade
            best_candidate = None
            best_score = -1

            for element_info in results['found_elements']:
                score = 0
                if element_info['count'] == 1:
                    score += 10  # Preferir seletores específicos
                elif element_info['count'] > 1:
                    score += 5   # Ainda útil se específico

                score += element_info['visible'] * 3  # Visibilidade é importante
                score += element_info['clickable'] * 2  # Clicabilidade é crucial

                if score > best_score:
                    best_score = score
                    best_candidate = element_info

            if best_candidate:
                results['recommended_selector'] = best_candidate['selector']
                print(f"\n🎯 RECOMENDAÇÃO: Use '{best_candidate['selector']}'")
                print(f"   Motivo: {best_candidate['visible']} visíveis, {best_candidate['clickable']} clicáveis")

        results['debug_info'] = {
            'timestamp': datetime.now().isoformat(),
            'analysis_duration': 'completed',
            'recommendation_confidence': 'high' if results['recommended_selector'] else 'low'
        }

        return results

    def generate_comprehensive_optimization_report(self, include_loop: bool = True, include_p2b: bool = True) -> str:
        """
        Gera relatório completo de otimização para loop.py e p2b.py
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RELATÓRIO DE OTIMIZAÇÃO - LOOP.PY E P2B.PY")
        report_lines.append("=" * 80)
        report_lines.append("")

        total_issues = 0
        total_recommendations = 0

        # Análise do Loop.py
        if include_loop:
            report_lines.append("🔄 ANÁLISE LOOP.PY")
            report_lines.append("-" * 40)

            loop_analysis = self.analyze_loop_execution()

            patterns = loop_analysis.get('loop_patterns', {})
            risks = loop_analysis.get('infinite_loop_risks', [])
            recommendations = loop_analysis.get('recommendations', [])

            report_lines.append(f"Funções mais executadas: {patterns.get('most_frequent_functions', {})}")
            report_lines.append(f"Tempo médio de execução: {patterns.get('avg_execution_time', 0):.2f}s")
            report_lines.append(f"Riscos de loop infinito: {len(risks)}")

            if risks:
                report_lines.append("\n🚨 RISCOS DETECTADOS:")
                for risk in risks:
                    report_lines.append(f"  • {risk['description']} ({risk['severity']})")

            if recommendations:
                report_lines.append("\n💡 RECOMENDAÇÕES PARA LOOP.PY:")
                for rec in recommendations:
                    report_lines.append(f"  • {rec['description']} ({rec['priority']})")

            total_issues += len(risks)
            total_recommendations += len(recommendations)
            report_lines.append("")

        # Análise do P2B.py
        if include_p2b:
            report_lines.append("📊 ANÁLISE P2B.PY")
            report_lines.append("-" * 40)

            p2b_analysis = self.analyze_p2b_execution()

            data_proc = p2b_analysis.get('data_processing', {})
            failures = p2b_analysis.get('failure_patterns', [])
            recommendations = p2b_analysis.get('recommendations', [])

            report_lines.append(f"Total de dados processados: {data_proc.get('total_data_processed', 0)}")
            report_lines.append(f"Taxa média de conversão: {data_proc.get('avg_conversion_rate', 0):.1%}")
            report_lines.append(f"Padrões de falha: {len(failures)}")

            if failures:
                report_lines.append("\n🚨 FALHAS DETECTADAS:")
                for failure in failures:
                    report_lines.append(f"  • {failure['description']} ({failure['severity']})")

            if recommendations:
                report_lines.append("\n💡 RECOMENDAÇÕES PARA P2B.PY:")
                for rec in recommendations:
                    report_lines.append(f"  • {rec['description']} ({rec['priority']})")

            total_issues += len(failures)
            total_recommendations += len(recommendations)
            report_lines.append("")

        # Resumo Geral
        report_lines.append("📈 RESUMO GERAL")
        report_lines.append("-" * 40)
        report_lines.append(f"Total de problemas identificados: {total_issues}")
        report_lines.append(f"Total de recomendações geradas: {total_recommendations}")

        if total_issues > 0:
            report_lines.append("\n✅ PRÓXIMOS PASSOS RECOMENDADOS:")
            report_lines.append("   1. Implementar timeout em loops do loop.py")
            report_lines.append("   2. Melhorar métodos de extração no p2b.py")
            report_lines.append("   3. Adicionar tracking de progresso")
            report_lines.append("   4. Implementar sistema de debug aprimorado")
            report_lines.append("   5. Configurar alertas para riscos detectados")
        else:
            report_lines.append("\n✅ Sistema otimizado!")

        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append(f"Relatório gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def save_comprehensive_report(self, report_content: str, filename: str = None) -> str:
        """Salva relatório completo em arquivo"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"relatorio_otimizacao_loop_p2b_{timestamp}.txt"

        filepath = os.path.join(self.workspace_path, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)

            print(f"📄 Relatório salvo em: {filepath}")
            return filepath

        except Exception as e:
            print(f"⚠️ Erro ao salvar relatório: {e}")
            return None