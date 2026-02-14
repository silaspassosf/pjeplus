"""
SISB Series - Fluxo de processamento
"""

from .series_navegar import _navegar_e_extrair_ordens_serie, _extrair_nome_executado_serie
from .series_estrategia import _calcular_estrategia_bloqueio
from .ordens_dados import _identificar_ordens_com_bloqueio
from .series_fluxo_helpers import (
    _tratar_ordem_respondida,
    _executar_transferencia,
    _executar_desbloqueio,
    _navegar_pos_ordem,
    _registrar_erro_processar,
)


def _processar_series(driver, series_validas, tipo_fluxo, log=True, estrategia=None):
    """
    Helper para processar series e suas ordens.
    """
    try:
        if log:
            print(f'[SISBAJUD] Processando {len(series_validas)} series...')

        resultado = {
            'series_processadas': 0,
            'ordens_processadas': 0,
            'erros': [],
            'detalhes': {
                'dados_bloqueios': {
                    'executados': {},
                    'total_geral': 0.0,
                    'ordens_com_erro_bloqueio': []
                },
                'ordens_transferidas': [],
                'ordem_pendente': None,
                'ordens_desbloqueadas': []
            }
        }

        acumulado_transferido = 0.0
        usar_estrategia_parcial = (estrategia and estrategia.get('tipo') == 'TRANSFERIR_PARCIAL')
        limite_execucao = estrategia.get('acumulado_limite', 0.0) if usar_estrategia_parcial else 0.0

        for idx_serie, serie in enumerate(series_validas, 1):
            if log:
                print(f'[SISBAJUD] Processando serie {idx_serie}/{len(series_validas)}: {serie["id_serie"]}')

            try:
                ordens = _navegar_e_extrair_ordens_serie(driver, serie, log)
                if not ordens:
                    if log:
                        print(f'[SISBAJUD] Nenhuma ordem extraida da serie {serie["id_serie"]}')
                    from .navegacao import _voltar_para_lista_principal
                    _voltar_para_lista_principal(driver, log)
                    continue

                _ = _extrair_nome_executado_serie(driver, log)

                valor_bloqueado = float(serie.get('valor_bloqueado', 0))
                ordens_bloqueadas = _identificar_ordens_com_bloqueio(ordens, valor_bloqueado, log)

                if not ordens_bloqueadas:
                    if log:
                        print(f'[SISBAJUD] Nenhuma ordem com bloqueio na serie {serie["id_serie"]}')
                    from .navegacao import _voltar_para_lista_principal
                    _voltar_para_lista_principal(driver, log)
                    resultado['series_processadas'] += 1
                    continue

                if usar_estrategia_parcial:
                    ordens_bloqueadas = sorted(ordens_bloqueadas, key=lambda o: float(o.get('valor_bloquear', 0)), reverse=True)

                total_ordens_serie = len(ordens_bloqueadas)
                for idx_ordem, ordem in enumerate(ordens_bloqueadas, 1):
                    sequencial_ordem = ordem.get('sequencial')
                    situacao_ordem = ordem.get('situacao', '')

                    if "Respondida com minuta" in situacao_ordem:
                        if log:
                            print(f'[SISBAJUD] Ordem {sequencial_ordem} ja processada')
                        _tratar_ordem_respondida(driver, ordem, tipo_fluxo, log, resultado)
                        resultado['ordens_processadas'] += 1
                        continue

                    if 'linha_el' in ordem:
                        ordem['linha_el'] = None

                    valor_ordem = float(ordem.get('valor_bloquear', 0))
                    acao = None
                    valor_a_transferir = None

                    if not usar_estrategia_parcial:
                        acao = 'TRANSFERIR'
                    else:
                        if acumulado_transferido >= limite_execucao:
                            acao = 'DESBLOQUEAR'
                        else:
                            projecao = acumulado_transferido + valor_ordem
                            if projecao <= limite_execucao:
                                acao = 'TRANSFERIR'
                            else:
                                valor_restante = limite_execucao - acumulado_transferido
                                acao = 'TRANSFERIR_PARCIAL'
                                valor_a_transferir = valor_restante
                                if log:
                                    print(f'[SISBAJUD] Ordem {sequencial_ordem}: TRANSFERENCIA PARCIAL (R$ {valor_restante:.2f} de R$ {valor_ordem:.2f})')

                    try:
                        if acao in ['TRANSFERIR', 'TRANSFERIR_PARCIAL']:
                            sucesso, erro_bloqueio = _executar_transferencia(
                                driver,
                                ordem,
                                tipo_fluxo,
                                log,
                                valor_a_transferir if acao == 'TRANSFERIR_PARCIAL' else None,
                                resultado
                            )

                            if not sucesso:
                                if erro_bloqueio:
                                    continue
                                return resultado

                            valor_transferido = valor_a_transferir if acao == 'TRANSFERIR_PARCIAL' else valor_ordem
                            acumulado_transferido += valor_transferido
                            resultado['ordens_processadas'] += 1
                            resultado['detalhes']['ordens_transferidas'].append({
                                'sequencial': sequencial_ordem,
                                'valor': valor_transferido,
                                'serie': serie['id_serie'],
                                'parcial': acao == 'TRANSFERIR_PARCIAL'
                            })

                        elif acao == 'DESBLOQUEAR':
                            sucesso = _executar_desbloqueio(driver, ordem, log, resultado)
                            if not sucesso:
                                return resultado

                            resultado['ordens_processadas'] += 1
                            resultado['detalhes']['ordens_desbloqueadas'].append({
                                'sequencial': sequencial_ordem,
                                'valor': valor_ordem,
                                'serie': serie['id_serie'],
                                'protocolo': ordem.get('protocolo', 'N/A')
                            })

                        _navegar_pos_ordem(driver, idx_ordem, total_ordens_serie, ordens_bloqueadas, log)

                    except Exception as e:
                        erro = f'Erro ao processar ordem {ordem.get("sequencial")} da serie {serie.get("id_serie")}: {str(e)}'
                        if log:
                            print(f'[SISBAJUD] {erro}')
                        resultado['erros'].append(erro)
                        _registrar_erro_processar(driver, idx_ordem, total_ordens_serie, ordens_bloqueadas, log)

                resultado['series_processadas'] += 1

            except Exception as e:
                erro = f'Erro na serie {serie.get("id_serie", "unknown")}: {str(e)}'
                if log:
                    print(f'[SISBAJUD] {erro}')
                resultado['erros'].append(erro)
                try:
                    from .navegacao import _voltar_para_lista_principal
                    _voltar_para_lista_principal(driver, log)
                except Exception:
                    pass
                continue

        if log:
            print(f'[SISBAJUD] Processamento concluido: {resultado["series_processadas"]} series, {resultado["ordens_processadas"]} ordens')
            if usar_estrategia_parcial:
                print(f'[SISBAJUD] Total transferido: R$ {acumulado_transferido:.2f} de R$ {limite_execucao:.2f}')
                print(f'[SISBAJUD] Ordens transferidas: {len(resultado["detalhes"]["ordens_transferidas"])}')
                print(f'[SISBAJUD] Ordens desbloqueadas: {len(resultado["detalhes"]["ordens_desbloqueadas"])}')

        return resultado

    except Exception as e:
        if log:
            print(f'[SISBAJUD] Erro geral no processamento: {e}')
        return {'series_processadas': 0, 'ordens_processadas': 0, 'erros': [str(e)], 'detalhes': {}}