import logging

logger = logging.getLogger(__name__)

"""
SISB Series - Estrategia de bloqueio
"""


def _calcular_estrategia_bloqueio(series_validas, dados_processo, log=True):
    """
    Calcula estrategia de bloqueio comparando valor total bloqueado com valor da execucao.
    """
    try:
        valor_execucao_str = dados_processo.get('divida', {}).get('valor', 'R$ 0,00')
        texto_limpo = valor_execucao_str.replace('R$', '').replace('\xa0', '').replace('&nbsp;', '').strip()
        texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
        try:
            valor_execucao = float(texto_limpo)
        except Exception:
            valor_execucao = 0.0

        total_bloqueado = sum(float(s.get('valor_bloqueado', 0)) for s in series_validas)

        if log:
            print('[SISBAJUD] Estrategia de bloqueio:')
            print(f'[SISBAJUD] Valor da execucao: R$ {valor_execucao:.2f}')
            print(f'[SISBAJUD] Total bloqueado: R$ {total_bloqueado:.2f}')

        if total_bloqueado <= valor_execucao:
            if log:
                print('[SISBAJUD] Estrategia: TRANSFERIR TUDO (bloqueado nao excede execucao)')
            return {
                'tipo': 'TRANSFERIR_TUDO',
                'valor_execucao': valor_execucao,
                'total_bloqueado': total_bloqueado,
                'acumulado_limite': valor_execucao
            }

        if log:
            excesso = total_bloqueado - valor_execucao
            print(f'[SISBAJUD] Estrategia: TRANSFERIR PARCIAL (bloqueado excede em R$ {excesso:.2f})')
            print('[SISBAJUD] Sera: transferir ate limite, pular 1 ordem, desbloquear restantes')

        return {
            'tipo': 'TRANSFERIR_PARCIAL',
            'valor_execucao': valor_execucao,
            'total_bloqueado': total_bloqueado,
            'acumulado_limite': valor_execucao
        }

    except Exception as e:
        if log:
            print(f'[SISBAJUD] Erro ao calcular estrategia: {e}')
        return {
            'tipo': 'TRANSFERIR_TUDO',
            'valor_execucao': 0.0,
            'total_bloqueado': 0.0,
            'acumulado_limite': 0.0
        }