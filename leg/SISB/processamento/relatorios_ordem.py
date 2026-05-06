import logging
import os
from datetime import datetime

from .relatorios_formatacao import (
    gerar_relatorio_bloqueios_conciso,
    gerar_relatorio_bloqueios_processados,
)

logger = logging.getLogger(__name__)

"""
SISB Relatorios - Relatorio de ordens
"""


def _gerar_relatorio_ordem(tipo_fluxo, series_processadas, ordens_processadas, detalhes, series_validas=None, driver=None, log=True, numero_processo=None, estrategia=None):
    """
    Helper para gerar relatorio do processamento de ordens (Transferencia/Desbloqueio).
    Sempre inclui primeiro o relatorio das series analisadas.
    """
    try:
        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ""

        # Etapa 1: incluir relatorio das series
        if series_validas and len(series_validas) > 0:
            relatorio_html += f'<p {pStyle}><strong>Relatorio de series executadas:</strong></p>'

            for serie in series_validas:
                numero_serie = serie.get('id_serie', 'N/A')
                data_conclusao = serie.get('data_conclusao')
                total_bloqueado = serie.get('valor_bloqueado', 0)
                total_bloqueado_text = serie.get('valor_bloqueado_text', '')

                if data_conclusao and hasattr(data_conclusao, 'strftime'):
                    data_str = data_conclusao.strftime('%d/%m/%Y')
                elif serie.get('data_conclusao_text'):
                    data_str = serie.get('data_conclusao_text')
                else:
                    data_str = 'Data nao disponivel'

                if total_bloqueado_text and total_bloqueado_text != 'R$ 0,00':
                    valor_str = total_bloqueado_text
                else:
                    valor_str = f"R$ {total_bloqueado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

                linha_serie = f"- (Serie {numero_serie}) - Data da finalizacao: ({data_str}) - Total bloqueado: ({valor_str})"
                relatorio_html += f'<p {pStyle}>{linha_serie}</p>'

        # Etapa 1.5: informar valor da execucao
        if estrategia:
            valor_exec = estrategia.get('valor_execucao', 0.0)
            total_bloq = estrategia.get('total_bloqueado', 0.0)

            valor_exec_fmt = f"R$ {valor_exec:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            total_bloq_fmt = f"R$ {total_bloq:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

            relatorio_html += f'<p {pStyle}><strong>Valor da execucao:</strong> {valor_exec_fmt}</p>'

            if estrategia.get('tipo') == 'TRANSFERIR_PARCIAL':
                relatorio_html += f'<p {pStyle}><strong>Total bloqueado nas series:</strong> {total_bloq_fmt} (excede valor da execucao)</p>'
            else:
                relatorio_html += f'<p {pStyle}><strong>Total bloqueado nas series:</strong> {total_bloq_fmt}</p>'

        # Etapa 2: processar por tipo de fluxo
        if tipo_fluxo == 'POSITIVO':
            dados_bloqueios = detalhes.get('dados_bloqueios', {}) if detalhes else {}

            if dados_bloqueios and dados_bloqueios.get('executados'):
                if log:
                    erros_bloq = dados_bloqueios.get('ordens_com_erro_bloqueio', [])
                    logger.error(f'[SISBAJUD]    - ordens_com_erro_bloqueio: {len(erros_bloq)} erros')
                    if erros_bloq:
                        for idx, erro in enumerate(erros_bloq):
                            logger.error(f'[SISBAJUD]      Erro {idx+1}: {erro}')

                relatorio_html += f'<p {pStyle}><strong>DISCRIMINACAO DE BLOQUEIOS TRANSFERIDOS:</strong></p>'

                relatorio_conciso = gerar_relatorio_bloqueios_conciso(dados_bloqueios, log)

                try:
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    pec_dir = os.path.join(base_dir, "PEC")
                    os.makedirs(pec_dir, exist_ok=True)

                    arquivo_conciso = os.path.join(pec_dir, "sisbajud_conciso_ultimo.txt")
                    with open(arquivo_conciso, 'w', encoding='utf-8') as f:
                        f.write(relatorio_conciso)
                except Exception as e_conciso:
                    if log:
                        logger.error(f'[SISBAJUD]  Erro ao salvar relatorio conciso: {e_conciso}')

                if estrategia and estrategia.get('tipo') == 'TRANSFERIR_PARCIAL':
                    dados_bloqueios['total_geral'] = estrategia.get('valor_execucao', dados_bloqueios['total_geral'])

                relatorio_detalhado = gerar_relatorio_bloqueios_processados(dados_bloqueios, log)
                relatorio_html += relatorio_detalhado

                if estrategia and estrategia.get('tipo') == 'TRANSFERIR_PARCIAL':
                    ordens_desbloq = detalhes.get('ordens_desbloqueadas', [])
                    qtd_desbloq = len(ordens_desbloq)

                    if qtd_desbloq > 0:
                        protocolos = [od.get('protocolo', 'N/A') for od in ordens_desbloq]
                        protocolos_str = ', '.join(protocolos)
                        relatorio_html += f'<p {pStyle}>Os valores excedentes ({qtd_desbloq} ordem(ns) - protocolos {protocolos_str}) foram devidamente <strong>DESBLOQUEADOS</strong>.</p>'
            else:
                relatorio_html += f'<p {pStyle}>Considerando os bloqueios realizados, as quantias localizadas foram <strong>TRANSFERIDAS</strong> a conta judicial do processo, acao que sera efetivada em ate 48h uteis.</p>'

        elif tipo_fluxo == 'NEGATIVO':
            relatorio_html += f'<p {pStyle}>Nao houve bloqueios realizados.</p>'

        elif tipo_fluxo == 'DESBLOQUEIO':
            relatorio_html += f'<p {pStyle}>Considerando as regras sobre bloqueios irrisorios, as quantias localizadas foram <strong>DESBLOQUEADAS</strong>, acao que sera efetivada em ate 48h uteis.</p>'

        else:
            relatorio_html += f'<p {pStyle}>Series processadas: {series_processadas}</p>'
            relatorio_html += f'<p {pStyle}>Ordens processadas: {ordens_processadas}</p>'
            relatorio_html += f'<p {pStyle}>Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>'

        # Salvar no clipboard.txt centralizado
        try:
            from PEC.anexos import salvar_conteudo_clipboard

            sucesso = salvar_conteudo_clipboard(
                conteudo=relatorio_html,
                numero_processo=numero_processo or "SISBAJUD",
                tipo_conteudo=f"sisbajud_{tipo_fluxo.lower()}",
                debug=log
            )

            _ = sucesso
        except ImportError as e:
            _ = e

        return True

    except Exception as e:
        if log:
            logger.error(f'[SISBAJUD]  Erro ao gerar relatorio: {e}')
        return False