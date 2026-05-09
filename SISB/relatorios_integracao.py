"""
SISB Relatorios e Integracao - Extracao, formatacao de relatorios e juntada ao PJe.

Consolida SISB/relatorios/generator.py e SISB/integration/pje_integration.py
em uma unica unidade com secoes: Entrada, Extracao, Formatacao, Juntada, Retorno.

Public contracts:
  - _agrupar_dados_bloqueios(dados_acumulados, dados_novos, log)
  - extrair_dados_bloqueios_processados(driver, log, protocolo_ordem)
  - gerar_relatorio_bloqueios_processados(dados_bloqueios, log)
  - gerar_relatorio_bloqueios_conciso(dados_bloqueios, log)
  - _gerar_relatorio_ordem(tipo_fluxo, series_processadas, ordens_processadas, detalhes, ...)
  - _atualizar_relatorio_com_segundo_protocolo(numero_processo, protocolo_primeira, protocolo_segunda, log)
  - _executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log)
"""

import logging
import os
import re
import time as time_module
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


# =============================================================================
# SECAO: EXTRACAO - extracao de dados de bloqueios da pagina SISBAJUD
# =============================================================================


def _agrupar_dados_bloqueios(dados_acumulados, dados_novos, log=True):
    """
    Agrupa dados de bloqueios novos nos dados acumulados.
    Merge por executado (chave = nome|documento).

    CORRIGIDO: Nao evita duplicatas - apenas adiciona todos os protocolos.
    O legado fazia extend simples sem verificar duplicatas.

    Args:
        dados_acumulados: Dict existente {'executados': {...}, 'total_geral': float}
        dados_novos: Dict com novos dados {'executados': {...}, 'total_geral': float}
        log: Se deve fazer log

    Returns:
        None (modifica dados_acumulados in-place)
    """
    try:
        if not dados_novos or not dados_novos.get('executados'):
            return

        for chave_executado, dados_exec in dados_novos['executados'].items():

            # Se executado ja existe nos acumulados, merge os protocolos
            if chave_executado in dados_acumulados['executados']:
                exec_acum = dados_acumulados['executados'][chave_executado]

                # Adicionar TODOS os protocolos (extend simples como no legado)
                #  CORRIGIDO: Garantir que protocolos_novos e sempre lista
                protocolos_novos = dados_exec.get('protocolos', [])
                if not isinstance(protocolos_novos, list):
                    # Se nao for lista, converter para lista
                    protocolos_novos = [protocolos_novos] if protocolos_novos else []

                # Garantir que exec_acum['protocolos'] e lista
                if not isinstance(exec_acum['protocolos'], list):
                    exec_acum['protocolos'] = [exec_acum['protocolos']] if exec_acum['protocolos'] else []

                exec_acum['protocolos'].extend(protocolos_novos)
                exec_acum['total'] += dados_exec.get('total', 0.0)
            else:
                # Novo executado - adicionar integralmente
                dados_acumulados['executados'][chave_executado] = {
                    'nome': dados_exec.get('nome', 'Executado'),
                    'documento': dados_exec.get('documento', ''),
                    'protocolos': list(dados_exec.get('protocolos', [])),  #  Garantir que e sempre lista
                    'total': float(dados_exec.get('total', 0.0))  #  Garantir que e sempre float
                }

            # Somar ao total geral (soma os totais de cada executado novo)
            dados_acumulados['total_geral'] += dados_exec.get('total', 0.0)

    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao agrupar dados: {e}")


def extrair_dados_bloqueios_processados(driver, log=True, protocolo_ordem=None):
    """
    Extrai dados dos bloqueios processados agrupados por executado.
    Le diretamente dos headers mat-expansion-panel-header na pagina do SISBAJUD.

    Baseado no legado ORIGINAIS/sisb.py

    Args:
        driver: WebDriver do SISBAJUD
        log: Se deve fazer log
        protocolo_ordem: Numero do protocolo da ordem (extraido da lista de ordens)

    Seletores usados (baseado no HTML fornecido):
    - mat-expansion-panel-header.sisbajud-mat-expansion-panel-header
    - .col-reu-dados-nome-pessoa (nome do executado)
    - .col-reu-dados a (documento CPF/CNPJ)
    - .div-description-reu span (valor bloqueado)

    Returns:
        dict: {'executados': {chave: {nome, documento, protocolos, total}}, 'total_geral': float}
    """
    try:
        # ===== AGUARDAR HEADERS DE EXECUTADOS APARECEREM (ate 3s) =====
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    'mat-expansion-panel-header.sisbajud-mat-expansion-panel-header'
                ))
            )
        except Exception as e:
            _ = e

        time_module.sleep(0.5)

        dados_bloqueios = {
            'executados': {},
            'total_geral': 0.0
        }

        numero_protocolo = protocolo_ordem if protocolo_ordem else "N/A"

        try:
            headers_executados = driver.find_elements(
                By.CSS_SELECTOR,
                'mat-expansion-panel-header.sisbajud-mat-expansion-panel-header'
            )

            if not headers_executados:
                return dados_bloqueios

            for idx, header in enumerate(headers_executados, 1):
                try:
                    nome_executado = "Executado nao identificado"
                    try:
                        nome_element = header.find_element(By.CSS_SELECTOR, '.col-reu-dados-nome-pessoa')
                        nome_executado = nome_element.text.strip()
                    except Exception as e:
                        _ = e

                    documento_executado = ""
                    try:
                        documento_element = header.find_element(By.CSS_SELECTOR, '.col-reu-dados a')
                        documento_executado = documento_element.text.strip()
                    except Exception as e:
                        _ = e

                    valor_float = 0.0
                    try:
                        valor_element = header.find_element(By.CSS_SELECTOR, '.div-description-reu span')
                        valor_text = valor_element.text.strip()

                        valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_text)
                        if valor_match:
                            valor_str = valor_match.group(1)
                            valor_float = float(valor_str.replace('.', '').replace(',', '.'))
                    except Exception as e:
                        _ = e

                    if valor_float <= 0:
                        continue

                    chave_executado = f"{nome_executado}|{documento_executado}"

                    if chave_executado not in dados_bloqueios['executados']:
                        dados_bloqueios['executados'][chave_executado] = {
                            'nome': nome_executado,
                            'documento': documento_executado,
                            'protocolos': [],
                            'total': 0.0
                        }

                    valor_formatado = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    dados_bloqueios['executados'][chave_executado]['protocolos'].append({
                        'numero': numero_protocolo,
                        'valor': valor_float,
                        'valor_formatado': valor_formatado,
                        'erro_bloqueio': None
                    })

                    dados_bloqueios['executados'][chave_executado]['total'] += valor_float
                    dados_bloqueios['total_geral'] += valor_float

                except Exception as e:
                    if log:
                        logger.error(f"[SISBAJUD]  Erro ao processar header {idx}: {e}")
                    continue

            return dados_bloqueios

        except Exception as e:
            if log:
                logger.error(f"[SISBAJUD]  Erro ao buscar headers: {e}")
            return dados_bloqueios

    except Exception as e:
        return {'executados': {}, 'total_geral': 0.0}


# =============================================================================
# SECAO: FORMATACAO - geracao de relatorios HTML
# =============================================================================


def gerar_relatorio_bloqueios_processados(dados_bloqueios, log=True):
    """
    Gera o relatorio formatado dos bloqueios processados agrupados por executado
    Copiado do legado ORIGINAIS/sisb.py
    """
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

            #  VALIDACAO: Garantir que protocolos e sempre lista
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
    """
    Gera versao CONCISA do relatorio de bloqueios - apenas 2 linhas por executado:
    - Nome (documento)
    - Ordens transferidas: [protocolos] - Total: valor

    Ordens com erro de bloqueio aparecem inline com destaque e observacao.
    """
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

            #  VALIDACAO: Garantir que protocolos e sempre lista
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


# =============================================================================
# SECAO: ENTRADA - geracao do relatorio completo de processamento de ordens
# =============================================================================


def _gerar_relatorio_ordem(tipo_fluxo, series_processadas, ordens_processadas, detalhes, series_validas=None, driver=None, log=True, numero_processo=None, estrategia=None):
    """
    Helper para gerar relatorio do processamento de ordens (Transferencia/Desbloqueio).
    SEMPRE inclui primeiro o relatorio das series analisadas.
    Para fluxo POSITIVO: extrai dados dos bloqueios diretamente da pagina via driver.
    Para outros fluxos: gera relatorio com dados das series + mensagem especifica.
    Salva no clipboard.txt centralizado.

    Args:
        tipo_fluxo: Tipo de fluxo (POSITIVO, NEGATIVO, DESBLOQUEIO)
        series_processadas: Numero de series processadas
        ordens_processadas: Numero de ordens processadas
        detalhes: Detalhes do processamento
        series_validas: Lista de series processadas (para gerar relatorio detalhado)
        driver: WebDriver SISBAJUD para extrair dados dos bloqueios (usado no fluxo POSITIVO)
        log: Se deve fazer log
        numero_processo: Numero do processo para salvar no clipboard

    Returns:
        bool: True se relatorio gerado com sucesso
    """
    try:
        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ""

        # ===== ETAPA 1: SEMPRE incluir relatorio das series primeiro =====
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

        # ===== ETAPA 1.5: ADICIONAR INFORMACAO DE VALOR DA EXECUCAO (se estrategia presente) =====
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

        # ===== ETAPA 2: Processar baseado no tipo de fluxo =====
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


# =============================================================================
# SECAO: JUNTADA - execucao de juntada automatica no PJe
# =============================================================================


def _executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log=True):
    """Delega para a funcao canonica em PEC.anexos."""
    from PEC.anexos import executar_juntada_pje
    return executar_juntada_pje(driver_pje, tipo_fluxo, numero_processo, log)


# =============================================================================
# SECAO: RETORNO - atualizacao de relatorios com segundos protocolos
# =============================================================================


def _atualizar_relatorio_com_segundo_protocolo(numero_processo, protocolo_primeira, protocolo_segunda, log=True):
    """
    Atualiza o relatorio no clipboard.txt adicionando o protocolo da segunda minuta.

    Modifica a linha de protocolo de:
    "Protocolo: 12345678901234"
    Para:
    "Protocolos: 12345678901234 e 98765432109876"

    Args:
        numero_processo: Numero do processo
        protocolo_primeira: Protocolo da primeira minuta
        protocolo_segunda: Protocolo da segunda minuta
        log: Se True, exibe logs

    Returns:
        bool: True se atualizou com sucesso
    """
    try:
        from PEC.anexos import obter_caminho_clipboard
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
