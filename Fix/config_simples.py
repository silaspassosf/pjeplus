"""config_simples — extraído de Fix/core.py (F7: split verbatim, re-exportado pelo core).

Corpos idênticos aos originais (mesma ordem interna). O grafo entre módulos é
acíclico: navegacao_espera <- navegacao <- entrada_campos; documentos_cp e
filtros_painel são folhas. """

class SimpleConfig:
    def __init__(self):
        self.stats = {'consecutive_errors': 0, 'total_actions': 0, 'rate_limit_detected': False}
        self.delays = {
            'default': 0.3,
            'click': 0.3,
            'navigation': 0.6,
            'form_fill': 0.8,
            'api_call': 1.0,
            'page_load': 2.0,
            'retry_base': 1.5,
        }
    
    def get_delay(self, t='default'):
        base = self.delays.get(t, 0.6)
        if self.stats['rate_limit_detected']:
            return base * 5.0
        elif self.stats['consecutive_errors'] > 5:
            return base * 3.0
        elif self.stats['consecutive_errors'] > 2:
            return base * 2.0
        return base
