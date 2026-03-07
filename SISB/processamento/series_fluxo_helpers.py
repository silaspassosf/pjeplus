"""
SISB Series - Helpers de fluxo
"""


def _tratar_ordem_respondida(driver, ordem, tipo_fluxo, log, resultado):
    if tipo_fluxo != 'POSITIVO':
        return

    if log:
        logger.info('[SISBAJUD] Extraindo dados da ordem ja processada...')

    try:
        from .ordens_fluxo import _processar_ordem
        sucesso = _processar_ordem(driver, ordem, tipo_fluxo, log, apenas_extrair=True)

        from .relatorios_dados import _agrupar_dados_bloqueios
        if sucesso and '_relatorio' in ordem and ordem['_relatorio'].get('discriminacao'):
            _agrupar_dados_bloqueios(
                resultado['detalhes']['dados_bloqueios'],
                ordem['_relatorio']['discriminacao'],
                log
            )
            if log:
                logger.info('[SISBAJUD] Dados extraidos e agrupados')
    except Exception as e:
        if log:
            logger.info(f'[SISBAJUD] Erro ao extrair dados: {e}')


def _executar_transferencia(driver, ordem, tipo_fluxo, log, valor_parcial, resultado):
    from .ordens_fluxo import _processar_ordem

    sucesso_processamento = _processar_ordem(
        driver,
        ordem,
        tipo_fluxo,
        log,
        valor_parcial=valor_parcial
    )

    if not sucesso_processamento:
        if '_relatorio' in ordem and ordem['_relatorio'].get('status') == 'erro':
            rel = ordem['_relatorio']
            erro = f"ERRO DE BLOQUEIO: Ordem {ordem.get('sequencial')} - {rel.get('erro_msg', 'erro desconhecido')}"
            if log:
                logger.info(f'[SISBAJUD] {erro}')
            resultado['erros'].append(erro)

            erro_item = {
                'protocolo': rel['protocolo'],
                'valor_esperado': rel['valor_esperado'],
                'erro_msg': rel.get('erro_msg', 'Erro desconhecido')
            }
            resultado['detalhes']['dados_bloqueios']['ordens_com_erro_bloqueio'].append(erro_item)
            if log:
                logger.info(f'[SISBAJUD] Erro adicionado a lista: {erro_item}')
            return False, True

        erro = f"CRITICO: Impossivel processar ordem {ordem.get('sequencial')}"
        if log:
            logger.info(f'[SISBAJUD] {erro}')
        resultado['erros'].append(erro)
        return False, False

    if tipo_fluxo == 'POSITIVO':
        protocolo_ordem = ordem.get('protocolo', 'N/A')
        if log:
            logger.info(f'[SISBAJUD] Extraindo dados dos bloqueios (Protocolo: {protocolo_ordem})')

        try:
            from .relatorios_dados import extrair_dados_bloqueios_processados, _agrupar_dados_bloqueios
            dados_ordem = extrair_dados_bloqueios_processados(driver, log, protocolo_ordem=protocolo_ordem)

            if '_relatorio' in ordem:
                ordem['_relatorio']['status'] = 'processado'
                ordem['_relatorio']['discriminacao'] = dados_ordem

            if dados_ordem and dados_ordem.get('executados'):
                _agrupar_dados_bloqueios(resultado['detalhes']['dados_bloqueios'], dados_ordem, log)
                if log:
                    logger.info(f'[SISBAJUD] Dados extraidos da ordem {ordem.get("sequencial")}')
        except Exception as e:
            if log:
                logger.info(f'[SISBAJUD] Erro ao extrair dados para relatorio: {e}')

    return True, False


def _executar_desbloqueio(driver, ordem, log, resultado):
    from .ordens_fluxo import _processar_ordem

    sucesso_processamento = _processar_ordem(driver, ordem, 'DESBLOQUEIO', log)
    if not sucesso_processamento:
        erro = f"CRITICO: Impossivel desbloquear ordem {ordem.get('sequencial')}"
        if log:
            logger.info(f'[SISBAJUD] {erro}')
        resultado['erros'].append(erro)
        return False

    return True


def _navegar_pos_ordem(driver, idx_ordem, total_ordens_serie, ordens_bloqueadas, log):
    from .navegacao import _voltar_para_lista_ordens_serie, _voltar_para_lista_principal

    if idx_ordem < total_ordens_serie:
        if log:
            logger.info(f'[SISBAJUD] Voltando para lista de ordens (restantes: {total_ordens_serie - idx_ordem})')
        _voltar_para_lista_ordens_serie(driver, log)

        for ordem_restante in ordens_bloqueadas[idx_ordem:]:
            if 'linha_el' in ordem_restante:
                ordem_restante['linha_el'] = None
        if log:
            logger.info('[SISBAJUD] Elementos invalidados apos retorno')
    else:
        if log:
            logger.info('[SISBAJUD] Ultima ordem da serie, voltando para lista de series')
        _voltar_para_lista_principal(driver, log)


def _registrar_erro_processar(driver, idx_ordem, total_ordens_serie, ordens_bloqueadas, log):
    from .navegacao import _voltar_para_lista_ordens_serie, _voltar_para_lista_principal

    try:
        if idx_ordem < total_ordens_serie:
            _voltar_para_lista_ordens_serie(driver, log)
            for ordem_restante in ordens_bloqueadas[idx_ordem:]:
                if 'linha_el' in ordem_restante:
                    ordem_restante['linha_el'] = None
        else:
            _voltar_para_lista_principal(driver, log)
    except Exception:
        pass