"""
selector_learning.py
Sistema de autoaprendizado para seletores CSS - mínimo e não-invasivo
Coleta métricas de sucesso/falha e recomenda melhores seletores
"""
import json
import os
import time
from typing import Dict, List, Optional, Tuple, Callable, Any
from collections import defaultdict
from datetime import datetime


# Configuração
LEARNING_DB_PATH = "aprendizado.json"
MIN_SAMPLES_FOR_SCORE = 5  # Mínimo de tentativas para calcular score
SCORE_DECAY_DAYS = 30  # Dados mais antigos que isso têm peso reduzido


class SelectorLearning:
    """Sistema de aprendizado de seletores - singleton"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "total_time_ms": 0.0,
            "times": [],
            "last_used": None,
            "contexts": set(),
            "score": 0.5,  # Score inicial neutro
        })
        self.recommendations: Dict[str, List[str]] = defaultdict(list)
        self.blacklist: List[Dict[str, str]] = []
        self._load()
        self._initialized = True
    
    def _load(self):
        """Carrega base de conhecimento do disco"""
        if not os.path.exists(LEARNING_DB_PATH):
            return
        
        try:
            with open(LEARNING_DB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruir db
            if 'selectors' in data:
                for key, value in data['selectors'].items():
                    self.db[key] = {
                        **value,
                        'contexts': set(value.get('contexts', [])),
                        'times': value.get('times', [])[-100:],  # Manter últimas 100
                    }
            
            # Reconstruir recomendações
            if 'recommendations' in data:
                self.recommendations = defaultdict(list, data['recommendations'])
            
            # Reconstruir blacklist
            if 'blacklist' in data:
                self.blacklist = data['blacklist']
                
        except Exception as e:
            print(f"[LEARNING] Aviso: Erro ao carregar DB: {e}")
    
    def _save(self):
        """Persiste base de conhecimento no disco"""
        try:
            data = {
                'selectors': {
                    key: {
                        **value,
                        'contexts': list(value['contexts']),
                    }
                    for key, value in self.db.items()
                },
                'recommendations': dict(self.recommendations),
                'blacklist': self.blacklist,
                'last_update': datetime.now().isoformat(),
            }
            
            with open(LEARNING_DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[LEARNING] Aviso: Erro ao salvar DB: {e}")
    
    def _calculate_score(self, selector_data: Dict[str, Any]) -> float:
        """
        Calcula score do seletor baseado em:
        - Taxa de sucesso (peso 70%)
        - Velocidade média (peso 20%)
        - Estabilidade/variância (peso 10%)
        
        Returns:
            float: Score de 0.0 (péssimo) a 1.0 (excelente)
        """
        attempts = selector_data['attempts']
        if attempts < MIN_SAMPLES_FOR_SCORE:
            return 0.5  # Score neutro se poucos dados
        
        successes = selector_data['successes']
        success_rate = successes / attempts
        
        # Componente 1: Taxa de sucesso (70% do peso)
        score = success_rate * 0.7
        
        # Componente 2: Velocidade (20% do peso)
        if selector_data['times']:
            avg_time = sum(selector_data['times']) / len(selector_data['times'])
            # Normalizar: <500ms = 1.0, >2000ms = 0.0
            speed_score = max(0, min(1, (2000 - avg_time) / 1500))
            score += speed_score * 0.2
        else:
            score += 0.1  # Score médio se sem dados de tempo
        
        # Componente 3: Estabilidade (10% do peso)
        if len(selector_data['times']) >= 3:
            variance = sum((t - sum(selector_data['times']) / len(selector_data['times'])) ** 2 
                          for t in selector_data['times']) / len(selector_data['times'])
            std_dev = variance ** 0.5
            # Normalizar: <200ms desvio = 1.0, >1000ms = 0.0
            stability_score = max(0, min(1, (1000 - std_dev) / 800))
            score += stability_score * 0.1
        else:
            score += 0.05
        
        return round(score, 3)
    
    def report_result(self, context: str, operation: str, selector: str, 
                     success: bool, duration_ms: Optional[float] = None):
        """
        Registra resultado de uso de seletor.
        
        Args:
            context: Contexto (ex: "prazo", "mandado", "pec")
            operation: Operação (ex: "botao_filtro", "link_processo")
            selector: Seletor CSS usado
            success: Se operação foi bem-sucedida
            duration_ms: Tempo de execução em milissegundos
        """
        key = f"{context}.{operation}.{selector}"
        
        self.db[key]['attempts'] += 1
        if success:
            self.db[key]['successes'] += 1
        else:
            self.db[key]['failures'] += 1
        
        if duration_ms is not None:
            self.db[key]['times'].append(duration_ms)
            self.db[key]['times'] = self.db[key]['times'][-100:]  # Manter últimas 100
            self.db[key]['total_time_ms'] += duration_ms
        
        self.db[key]['last_used'] = datetime.now().isoformat()
        self.db[key]['contexts'].add(context)
        
        # Recalcular score
        self.db[key]['score'] = self._calculate_score(self.db[key])
        
        # Atualizar blacklist se necessário
        if self.db[key]['attempts'] >= 10 and self.db[key]['score'] < 0.3:
            if not any(b['selector'] == selector for b in self.blacklist):
                self.blacklist.append({
                    'selector': selector,
                    'context': context,
                    'reason': f"Score baixo ({self.db[key]['score']}) após {self.db[key]['attempts']} tentativas",
                    'date': datetime.now().isoformat()
                })
        
        # Salvar periodicamente (a cada 10 registros)
        if sum(d['attempts'] for d in self.db.values()) % 10 == 0:
            self._save()
    
    def get_recommendations(self, context: str, operation: str, fallback: Optional[List[str]] = None) -> List[str]:
        """
        Retorna lista de seletores recomendados ordenados por score.
        
        Args:
            context: Contexto (ex: "prazo")
            operation: Operação (ex: "botao_filtro")
            fallback: Seletores padrão se nenhum aprendido
            
        Returns:
            Lista de seletores ordenados por score (melhor primeiro)
        """
        # Buscar todos seletores para essa operação neste contexto
        prefix = f"{context}.{operation}."
        candidates = [(key.replace(prefix, ''), data) 
                     for key, data in self.db.items() 
                     if key.startswith(prefix) and data['attempts'] >= MIN_SAMPLES_FOR_SCORE]
        
        # Ordenar por score
        candidates.sort(key=lambda x: x[1]['score'], reverse=True)
        
        # Filtrar blacklist
        recommended = [sel for sel, data in candidates 
                      if not any(b['selector'] == sel for b in self.blacklist)]
        
        # Se não há recomendações aprendidas, usar fallback
        if not recommended and fallback:
            return fallback
        
        return recommended or (fallback or [])
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais do sistema de aprendizado"""
        total_selectors = len(self.db)
        total_attempts = sum(d['attempts'] for d in self.db.values())
        total_successes = sum(d['successes'] for d in self.db.values())
        avg_score = sum(d['score'] for d in self.db.values()) / total_selectors if total_selectors > 0 else 0
        
        return {
            'total_selectors': total_selectors,
            'total_attempts': total_attempts,
            'total_successes': total_successes,
            'success_rate': total_successes / total_attempts if total_attempts > 0 else 0,
            'avg_score': round(avg_score, 3),
            'blacklisted': len(self.blacklist),
        }
    
    def force_save(self):
        """Força salvamento imediato da base de conhecimento"""
        self._save()


# Singleton global
_learning = SelectorLearning()


# API pública simplificada
def report_selector_result(context: str, operation: str, selector: str, 
                           success: bool, duration_ms: Optional[float] = None):
    """Registra resultado de seletor (wrapper do singleton)"""
    _learning.report_result(context, operation, selector, success, duration_ms)


def get_recommended_selectors(context: str, operation: str, fallback: Optional[List[str]] = None) -> List[str]:
    """Obtém seletores recomendados (wrapper do singleton)"""
    return _learning.get_recommendations(context, operation, fallback)


def get_learning_stats() -> Dict[str, Any]:
    """Obtém estatísticas do aprendizado (wrapper do singleton)"""
    return _learning.get_stats()


def save_learning_db():
    """Força salvamento da base de conhecimento"""
    _learning.force_save()


def use_best_selector(driver, context: str, operation: str, 
                     click_func: Callable, default_selector: str, 
                     timeout: int = 10) -> bool:
    """
    Wrapper inteligente que tenta seletores na ordem de score.
    Compatível com funções Fix existentes.
    
    Args:
        driver: WebDriver instance
        context: Contexto (ex: "prazo")
        operation: Operação (ex: "botao_processar")
        click_func: Função de click (ex: aguardar_e_clicar)
        default_selector: Seletor padrão se nenhum aprendido
        timeout: Timeout em segundos
        
    Returns:
        bool: True se sucesso
    """
    selectors = get_recommended_selectors(context, operation, [default_selector])
    
    for selector in selectors:
        start = time.time()
        try:
            result = click_func(driver, selector, timeout=timeout)
            duration_ms = (time.time() - start) * 1000
            
            if result or result is None:  # None = sem retorno explícito, assumir sucesso
                report_selector_result(context, operation, selector, True, duration_ms)
                return True
            else:
                report_selector_result(context, operation, selector, False, duration_ms)
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            report_selector_result(context, operation, selector, False, duration_ms)
            continue
    
    return False
