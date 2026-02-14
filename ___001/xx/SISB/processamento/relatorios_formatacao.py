import logging

logger = logging.getLogger(__name__)

"""
SISB Relatorios - Formatacao e conteudo
"""


def gerar_relatorio_bloqueios_processados(dados_bloqueios, log=True):
    """
    Gera o relatorio formatado dos bloqueios processados agrupados por executado.
    """
    try:
        if not dados_bloqueios or not dados_bloqueios.get('executados'):
            return "Nenhum bloqueio processado encontrado."

        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ''

        for _, dados_exec in dados_bloqueios['executados'].items():
            nome = dados_exec['nome']
            documento = dados_exec.get('documento', '')
            protocolos = dados_exec['protocolos']
            total_executado = dados_exec['total']

            if not isinstance(protocolos, list):
                protocolos = [protocolos] if protocolos else []

            doc_str = f" - {documento}" if documento else ""
            relatorio_html += f'<p {pStyle}><strong>Executado: {nome}{doc_str}</strong></p>'

            for protocolo in protocolos:
                try:
                    if isinstance(protocolo, dict):
                        numero_prot = protocolo.get('numero', 'N/A')
                        valor_format = protocolo.get('valor_formatado', 'R$ 0,00')
                    else:
                        numero_prot = str(protocolo)
                        valor_format = 'R$ 0,00'

                    relatorio_html += f'<p {pStyle}>Protocolo {numero_prot} - Valor: {valor_format}</p>'
                except Exception as e_prot:
                    if log:
                        logger.error(f"[SISBAJUD]  Erro ao processar protocolo: {e_prot}")
                    continue

            total_format = f"R$ {total_executado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            relatorio_html += f'<p {pStyle}><strong>Total do executado: {total_format}</strong></p>'

        total_geral_format = f"R$ {dados_bloqueios['total_geral']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        relatorio_html += f'<p {pStyle}><strong>Total efetivamente transferido a conta judicial do processo: {total_geral_format}</strong></p>'
        relatorio_html += f'<p {pStyle}>Considerando os bloqueios realizados, as quantias localizadas foram <strong>TRANSFERIDAS</strong> a conta judicial do processo, acao que sera efetivada em ate 48h uteis.</p>'

        if dados_bloqueios.get('ordens_com_erro_bloqueio'):
            if log:
                logger.error(f"[SISBAJUD] Adicionando {len(dados_bloqueios['ordens_com_erro_bloqueio'])} ordens com erro ao relatorio DETALHADO")
            relatorio_html += f'<p {pStyle}><strong><u>ORDENS COM ERRO DE BLOQUEIO:</u></strong></p>'
            for ordem_erro in dados_bloqueios['ordens_com_erro_bloqueio']:
                prot = ordem_erro.get('protocolo', 'N/A')
                val_esp = ordem_erro.get('valor_esperado', 0.0)
                val_esp_fmt = f"R$ {val_esp:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                relatorio_html += f'<p {pStyle}>Protocolo {prot}: Bloqueio esperado de {val_esp_fmt} esta <strong>INDISPONIVEL</strong> para transferencia.</p>'

            relatorio_html += f'<p {pStyle}>As ordens acima, com erro de processamento, serao alvo de oficio ao suporte do SISBAJUD para esclarecimentos, caso os valores nao estejam disponiveis em ate 10 dias.</p>'

        return relatorio_html

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao gerar relatorio de bloqueios: {e}")
        return "Erro ao gerar relatorio dos bloqueios processados."


def gerar_relatorio_bloqueios_conciso(dados_bloqueios, log=True):
    """
    Gera versao concisa do relatorio de bloqueios.
    """
    try:
        if not dados_bloqueios or not dados_bloqueios.get('executados'):
            return ""

        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ''

        relatorio_html += f'<p {pStyle}><strong>Relatorio de bloqueios discriminado por executado:</strong></p>'

        for _, dados_exec in dados_bloqueios['executados'].items():
            nome = dados_exec['nome']
            documento = dados_exec.get('documento', '')
            protocolos = dados_exec['protocolos']
            total_executado = dados_exec['total']

            if not isinstance(protocolos, list):
                protocolos = [protocolos] if protocolos else []

            doc_str = f" ({documento})" if documento else ""
            relatorio_html += f'<p {pStyle}>- {nome}{doc_str}:</p>'

            protocolos_formatados = []
            for protocolo in protocolos:
                try:
                    if isinstance(protocolo, dict):
                        num = protocolo.get('numero', 'N/A')
                        erro_info = protocolo.get('erro_bloqueio')
                        if erro_info:
                            protocolos_formatados.append(f"<strong><u>{num} ({erro_info})</u></strong>")
                        else:
                            protocolos_formatados.append(num)
                    else:
                        protocolos_formatados.append(str(protocolo))
                except Exception:
                    continue

            protocolos_str = ", ".join(protocolos_formatados) if protocolos_formatados else "N/A"
            total_format = f"R$ {total_executado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

            relatorio_html += f'<p {pStyle}>Ordens com bloqueios transferidos desta parte: [{protocolos_str}] - Total transferido do executado: {total_format}</p>'

        if dados_bloqueios.get('ordens_com_erro_bloqueio'):
            if log:
                logger.error(f"[SISBAJUD] Adicionando {len(dados_bloqueios['ordens_com_erro_bloqueio'])} ordens com erro ao relatorio")
            relatorio_html += f'<p {pStyle}><strong><u>ORDENS COM ERRO DE BLOQUEIO:</u></strong></p>'
            for ordem_erro in dados_bloqueios['ordens_com_erro_bloqueio']:
                prot = ordem_erro.get('protocolo', 'N/A')
                val_esp = ordem_erro.get('valor_esperado', 0.0)
                val_esp_fmt = f"R$ {val_esp:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                relatorio_html += f'<p {pStyle}>Protocolo {prot}: Bloqueio esperado de {val_esp_fmt} esta <strong>INDISPONIVEL</strong> para transferencia.</p>'

            relatorio_html += f'<p {pStyle}>As ordens acima, com erro de processamento, serao alvo de oficio ao suporte do SISBAJUD para esclarecimentos, caso os valores nao estejam disponiveis em ate 10 dias.</p>'
        else:
            if log:
                logger.error("[SISBAJUD] Nenhuma ordem com erro de bloqueio encontrada")

        return relatorio_html

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao gerar relatorio conciso: {e}")
        return ""