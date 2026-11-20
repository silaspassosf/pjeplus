"""SISB Relatorios e Integracao - Extracao, formatacao de relatorios e juntada ao PJe."""

import logging
import os
import re
from datetime import datetime

from .processamento.relatorios_dados import _agrupar_dados_bloqueios, extrair_dados_bloqueios_processados  # noqa: F401

logger = logging.getLogger(__name__)


def gerar_relatorio_bloqueios_processados(dados_bloqueios, log=True):
    """Gera o relatorio formatado dos bloqueios processados agrupados por executado"""
    try:
        if not dados_bloqueios or not dados_bloqueios.get('executados'):
            return "Nenhum bloqueio processado encontrado."

        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ''

        for chave_executado, dados_exec in dados_bloqueios['executados'].items():
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

            bancos_001 = dados_exec.get('bancos_001', [])
            if bancos_001:
                bancos_str = ", ".join(bancos_001)
                relatorio_html += f'<p {pStyle}>Foram registrados bloqueios de 0,01 no banco ({bancos_str}) que podem indicar investimentos localizados nesta instituição.</p>'

        total_geral_format = f"R$ {dados_bloqueios['total_geral']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        relatorio_html += f'<p {pStyle}><strong>Total efetivamente transferido a conta judicial do processo: {total_geral_format}</strong></p>'
        relatorio_html += f'<p {pStyle}>Considerando os bloqueios realizados, as quantias localizadas foram <strong>TRANSFERIDAS</strong> a conta judicial do processo, acao que sera efetivada em ate 48h uteis.</p>'

        if dados_bloqueios.get('ordens_com_erro_bloqueio'):
            if log:
                logger.error(f"[SISBAJUD]  Adicionando {len(dados_bloqueios['ordens_com_erro_bloqueio'])} ordens com erro ao relatorio DETALHADO")
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
    """Gera versao CONCISA do relatorio de bloqueios - apenas 2 linhas por executado:"""
    try:
        if not dados_bloqueios or not dados_bloqueios.get('executados'):
            return ""

        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ''

        relatorio_html += f'<p {pStyle}><strong>Relatorio de bloqueios discriminado por executado:</strong></p>'

        for idx, (chave_executado, dados_exec) in enumerate(dados_bloqueios['executados'].items(), 1):
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

            bancos_001 = dados_exec.get('bancos_001', [])
            if bancos_001:
                bancos_str = ", ".join(bancos_001)
                relatorio_html += f'<p {pStyle}>Foram registrados bloqueios de 0,01 no banco ({bancos_str}) que podem indicar investimentos localizados nesta instituição.</p>'

        if dados_bloqueios.get('ordens_com_erro_bloqueio'):
            if log:
                logger.error(f"[SISBAJUD]  Adicionando {len(dados_bloqueios['ordens_com_erro_bloqueio'])} ordens com erro ao relatorio")
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


def _gerar_relatorio_ordem(tipo_fluxo, series_processadas, ordens_processadas, detalhes, series_validas=None, driver=None, log=True, numero_processo=None, estrategia=None):
    """Helper para gerar relatorio do processamento de ordens (Transferencia/Desbloqueio)."""
    try:
        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ""

        if series_validas and len(series_validas) > 0:
            relatorio_html += f'<p {pStyle}><strong>Relatorio de series executadas:</strong></p>'

            for i, serie in enumerate(series_validas, 1):
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
        else:
            _ = series_validas

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

        try:
            from atos.anexos import salvar_conteudo_clipboard

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


def _executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log=True):
    """Delega para a funcao canonica em atos.anexos."""
    from atos.anexos import executar_juntada_pje
    return executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log)


def _atualizar_relatorio_com_segundo_protocolo(numero_processo, protocolo_primeira, protocolo_segunda, log=True):
    """Atualiza o relatorio no clipboard.txt adicionando o protocolo da segunda minuta."""
    try:
        from atos.anexos import obter_caminho_clipboard
        clipboard_path = obter_caminho_clipboard(numero_processo or "SISBAJUD")

        if not os.path.exists(clipboard_path):
            return False

        with open(clipboard_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        padrao = r'Protocolo:\s*(\d+)'
        substituicao = f'Protocolos: {protocolo_primeira} e {protocolo_segunda}'

        conteudo_atualizado = re.sub(padrao, substituicao, conteudo)

        with open(clipboard_path, 'w', encoding='utf-8') as f:
            f.write(conteudo_atualizado)

        return True

    except Exception as e:
        if log:
            logger.error(f'[SISBAJUD][RELATORIO]  Erro ao atualizar relatorio: {e}')
            import traceback
            logger.exception("Erro detectado")
        return False
