import logging
logger = logging.getLogger(__name__)

"""
SISB Relatorios Generator - Geração e formatação de relatórios
Funções para extrair, agrupar e formatar relatórios de bloqueios SISBAJUD
"""

import os
import re
import time as time_module
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _agrupar_dados_bloqueios(dados_acumulados, dados_novos, log=True):
    """
    Agrupa dados de bloqueios novos nos dados acumulados.
    Merge por executado (chave = nome|documento).
    
    CORRIGIDO: Não evita duplicatas - apenas adiciona todos os protocolos.
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
            
            # Se executado já existe nos acumulados, merge os protocolos
            if chave_executado in dados_acumulados['executados']:
                exec_acum = dados_acumulados['executados'][chave_executado]
                
                # Adicionar TODOS os protocolos (extend simples como no legado)
                #  CORRIGIDO: Garantir que protocolos_novos é sempre lista
                protocolos_novos = dados_exec.get('protocolos', [])
                if not isinstance(protocolos_novos, list):
                    # Se não for lista, converter para lista
                    protocolos_novos = [protocolos_novos] if protocolos_novos else []
                
                # Garantir que exec_acum['protocolos'] é lista
                if not isinstance(exec_acum['protocolos'], list):
                    exec_acum['protocolos'] = [exec_acum['protocolos']] if exec_acum['protocolos'] else []
                
                exec_acum['protocolos'].extend(protocolos_novos)
                exec_acum['total'] += dados_exec.get('total', 0.0)
            else:
                # Novo executado - adicionar integralmente
                dados_acumulados['executados'][chave_executado] = {
                    'nome': dados_exec.get('nome', 'Executado'),
                    'documento': dados_exec.get('documento', ''),
                    'protocolos': list(dados_exec.get('protocolos', [])),  #  Garantir que é sempre lista
                    'total': float(dados_exec.get('total', 0.0))  #  Garantir que é sempre float
                }
            
            # Somar ao total geral (soma os totais de cada executado novo)
            dados_acumulados['total_geral'] += dados_exec.get('total', 0.0)
    
    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao agrupar dados: {e}")


def extrair_dados_bloqueios_processados(driver, log=True, protocolo_ordem=None):
    """
    Extrai dados dos bloqueios processados agrupados por executado.
    Lê diretamente dos headers mat-expansion-panel-header na página do SISBAJUD.
    
    Baseado no legado ORIGINAIS/sisb.py
    
    Args:
        driver: WebDriver do SISBAJUD
        log: Se deve fazer log
        protocolo_ordem: Número do protocolo da ordem (extraído da lista de ordens)
    
    Seletores usados (baseado no HTML fornecido):
    - mat-expansion-panel-header.sisbajud-mat-expansion-panel-header
    - .col-reu-dados-nome-pessoa (nome do executado)
    - .col-reu-dados a (documento CPF/CNPJ)
    - .div-description-reu span (valor bloqueado)
    
    Returns:
        dict: {'executados': {chave: {nome, documento, protocolos, total}}, 'total_geral': float}
    """
    try:
        # ===== AGUARDAR HEADERS DE EXECUTADOS APARECEREM (até 3s) =====
        # Importante: após clicar Salvar, a página pode demorar para renderizar os dados
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    'mat-expansion-panel-header.sisbajud-mat-expansion-panel-header'
                ))
            )
        except Exception as e:
            _ = e
        
        # Pequeno delay adicional para garantir renderização completa
        time_module.sleep(0.5)
        
        # Estrutura para armazenar dados agrupados por executado
        dados_bloqueios = {
            'executados': {},
            'total_geral': 0.0
        }
        
        # 1. Usar o protocolo da ordem (passado como parâmetro) - é o protocolo correto!
        numero_protocolo = protocolo_ordem if protocolo_ordem else "N/A"
        
        # 2. Buscar todos os cabeçalhos de executados
        try:
            headers_executados = driver.find_elements(
                By.CSS_SELECTOR, 
                'mat-expansion-panel-header.sisbajud-mat-expansion-panel-header'
            )
            
            if not headers_executados:
                return dados_bloqueios
            
            for idx, header in enumerate(headers_executados, 1):
                try:
                    # Extrair nome do executado
                    nome_executado = "Executado não identificado"
                    try:
                        nome_element = header.find_element(By.CSS_SELECTOR, '.col-reu-dados-nome-pessoa')
                        nome_executado = nome_element.text.strip()
                    except Exception as e:
                        _ = e
                    
                    # Extrair documento do executado (CPF/CNPJ)
                    documento_executado = ""
                    try:
                        documento_element = header.find_element(By.CSS_SELECTOR, '.col-reu-dados a')
                        documento_executado = documento_element.text.strip()
                    except Exception as e:
                        _ = e
                    
                    # Extrair valor bloqueado do executado
                    valor_float = 0.0
                    try:
                        valor_element = header.find_element(By.CSS_SELECTOR, '.div-description-reu span')
                        valor_text = valor_element.text.strip()
                        
                        # Processar valor: "Valor bloqueado (bloqueio original e reiterações): R$ 187,94"
                        # Usar regex para extrair o valor monetário (igual ao legado)
                        valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_text)
                        if valor_match:
                            valor_str = valor_match.group(1)
                            # Converter formato brasileiro (1.234,56) para float
                            valor_float = float(valor_str.replace('.', '').replace(',', '.'))
                    except Exception as e:
                        _ = e
                    
                    # Pular se valor for 0 (não houve bloqueio)
                    if valor_float <= 0:
                        continue
                    
                    # Criar chave única para o executado
                    chave_executado = f"{nome_executado}|{documento_executado}"
                    
                    # Inicializar dados do executado se não existir
                    if chave_executado not in dados_bloqueios['executados']:
                        dados_bloqueios['executados'][chave_executado] = {
                            'nome': nome_executado,
                            'documento': documento_executado,
                            'protocolos': [],  #  Sempre inicializar como lista vazia
                            'total': 0.0
                        }
                    
                    # Adicionar protocolo e valor
                    valor_formatado = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    dados_bloqueios['executados'][chave_executado]['protocolos'].append({
                        'numero': numero_protocolo,
                        'valor': valor_float,
                        'valor_formatado': valor_formatado,
                        'erro_bloqueio': None  # Será preenchido se houver erro
                    })
                    
                    # Somar aos totais
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


def gerar_relatorio_bloqueios_processados(dados_bloqueios, log=True):
    """
    Gera o relatório formatado dos bloqueios processados agrupados por executado
    Copiado do legado ORIGINAIS/sisb.py
    """
    try:
        if not dados_bloqueios or not dados_bloqueios.get('executados'):
            return "Nenhum bloqueio processado encontrado."
        
        # Estrutura HTML do relatório
        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ''
        
        # Percorrer cada executado
        for chave_executado, dados_exec in dados_bloqueios['executados'].items():
            nome = dados_exec['nome']
            documento = dados_exec.get('documento', '')
            protocolos = dados_exec['protocolos']
            total_executado = dados_exec['total']
            
            #  VALIDAÇÃO: Garantir que protocolos é sempre lista
            if not isinstance(protocolos, list):
                protocolos = [protocolos] if protocolos else []
            
            # Cabeçalho do executado
            doc_str = f" - {documento}" if documento else ""
            relatorio_html += f'<p {pStyle}><strong>Executado: {nome}{doc_str}</strong></p>'
            
            # Listar protocolos do executado
            for protocolo in protocolos:
                try:
                    # Garantir que protocolo é dict
                    if isinstance(protocolo, dict):
                        numero_prot = protocolo.get('numero', 'N/A')
                        valor_format = protocolo.get('valor_formatado', 'R$ 0,00')
                    else:
                        # Se não for dict, tentar extrair valor
                        numero_prot = str(protocolo)
                        valor_format = 'R$ 0,00'
                    
                    relatorio_html += f'<p {pStyle}>Protocolo {numero_prot} - Valor: {valor_format}</p>'
                except Exception as e_prot:
                    if log:
                        logger.error(f"[SISBAJUD]  Erro ao processar protocolo: {e_prot}")
                    continue
            
            # Total do executado
            total_format = f"R$ {total_executado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            relatorio_html += f'<p {pStyle}><strong>Total do executado: {total_format}</strong></p>'
        
        # Total geral do processo
        total_geral_format = f"R$ {dados_bloqueios['total_geral']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        relatorio_html += f'<p {pStyle}><strong>Total efetivamente transferido à conta judicial do processo: {total_geral_format}</strong></p>'
        
        # Mensagem sobre transferência em 48h (ANTES da seção de erros)
        relatorio_html += f'<p {pStyle}>Considerando os bloqueios realizados, as quantias localizadas foram <strong>TRANSFERIDAS</strong> à conta judicial do processo, ação que será efetivada em até 48h úteis.</p>'
        
        # Adicionar ordens com erro de bloqueio (se houver)
        if dados_bloqueios.get('ordens_com_erro_bloqueio'):
            if log:
                logger.error(f"[SISBAJUD]  Adicionando {len(dados_bloqueios['ordens_com_erro_bloqueio'])} ordens com erro ao relatório DETALHADO")
            relatorio_html += f'<p {pStyle}><strong><u>ORDENS COM ERRO DE BLOQUEIO:</u></strong></p>'
            for ordem_erro in dados_bloqueios['ordens_com_erro_bloqueio']:
                prot = ordem_erro.get('protocolo', 'N/A')
                val_esp = ordem_erro.get('valor_esperado', 0.0)
                val_esp_fmt = f"R$ {val_esp:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                relatorio_html += f'<p {pStyle}>Protocolo {prot}: Bloqueio esperado de {val_esp_fmt} está <strong>INDISPONÍVEL</strong> para transferência.</p>'
            
            # Texto final sobre acompanhamento dos erros
            relatorio_html += f'<p {pStyle}>As ordens acima, com erro de processamento, serão alvo de ofício ao suporte do SISBAJUD para esclarecimentos, caso os valores não estejam disponíves em até 10 dias.</p>'
        
        return relatorio_html
        
    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao gerar relatório de bloqueios: {e}")
        return "Erro ao gerar relatório dos bloqueios processados."


def gerar_relatorio_bloqueios_conciso(dados_bloqueios, log=True):
    """
    Gera versão CONCISA do relatório de bloqueios - apenas 2 linhas por executado:
    - Nome (documento)
    - Ordens transferidas: [protocolos] - Total: valor
    
    Ordens com erro de bloqueio aparecem inline com destaque e observação.
    """
    try:
        if not dados_bloqueios or not dados_bloqueios.get('executados'):
            return ""
        
        # Estrutura HTML do relatório
        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ''
        
        relatorio_html += f'<p {pStyle}><strong>Relatório de bloqueios discriminado por executado:</strong></p>'
        
        # Percorrer cada executado
        for idx, (chave_executado, dados_exec) in enumerate(dados_bloqueios['executados'].items(), 1):
            nome = dados_exec['nome']
            documento = dados_exec.get('documento', '')
            protocolos = dados_exec['protocolos']
            total_executado = dados_exec['total']
            
            #  VALIDAÇÃO: Garantir que protocolos é sempre lista
            if not isinstance(protocolos, list):
                protocolos = [protocolos] if protocolos else []
            
            # Linha 1: Nome do executado (documento)
            doc_str = f" ({documento})" if documento else ""
            relatorio_html += f'<p {pStyle}>- {nome}{doc_str}:</p>'
            
            # Construir lista de protocolos com marcação de erros
            protocolos_formatados = []
            for protocolo in protocolos:
                try:
                    if isinstance(protocolo, dict):
                        num = protocolo.get('numero', 'N/A')
                        erro_info = protocolo.get('erro_bloqueio')
                        if erro_info:
                            # Protocolo com erro - adicionar com destaque
                            protocolos_formatados.append(f"<strong><u>{num} ({erro_info})</u></strong>")
                        else:
                            protocolos_formatados.append(num)
                    else:
                        protocolos_formatados.append(str(protocolo))
                except:
                    continue
            
            protocolos_str = ", ".join(protocolos_formatados) if protocolos_formatados else "N/A"
            total_format = f"R$ {total_executado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            relatorio_html += f'<p {pStyle}>Ordens com bloqueios transferidos desta parte: [{protocolos_str}] - Total transferido do executado: {total_format}</p>'
        
        # Adicionar ordens com erro (se houver)
        if dados_bloqueios.get('ordens_com_erro_bloqueio'):
            if log:
                logger.error(f"[SISBAJUD]  Adicionando {len(dados_bloqueios['ordens_com_erro_bloqueio'])} ordens com erro ao relatório")
            relatorio_html += f'<p {pStyle}><strong><u>ORDENS COM ERRO DE BLOQUEIO:</u></strong></p>'
            for ordem_erro in dados_bloqueios['ordens_com_erro_bloqueio']:
                prot = ordem_erro.get('protocolo', 'N/A')
                val_esp = ordem_erro.get('valor_esperado', 0.0)
                val_esp_fmt = f"R$ {val_esp:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                relatorio_html += f'<p {pStyle}>Protocolo {prot}: Bloqueio esperado de {val_esp_fmt} está <strong>INDISPONÍVEL</strong> para transferência.</p>'
            
            # Texto final sobre acompanhamento dos erros
            relatorio_html += f'<p {pStyle}>As ordens acima, com erro de processamento, serão alvo de ofício ao suporte do SISBAJUD para esclarecimentos, caso os valores não estejam disponíves em até 10 dias.</p>'
        else:
            if log:
                logger.error(f"[SISBAJUD] ℹ Nenhuma ordem com erro de bloqueio encontrada")
        
        return relatorio_html
        
    except Exception as e:
        if log:
            logger.error(f"[SISBAJUD]  Erro ao gerar relatório conciso: {e}")
        return ""


def _gerar_relatorio_ordem(tipo_fluxo, series_processadas, ordens_processadas, detalhes, series_validas=None, driver=None, log=True, numero_processo=None, estrategia=None):
    """
    Helper para gerar relatório do processamento de ordens (Transferência/Desbloqueio).
    SEMPRE inclui primeiro o relatório das séries analisadas.
    Para fluxo POSITIVO: extrai dados dos bloqueios diretamente da página via driver.
    Para outros fluxos: gera relatório com dados das séries + mensagem específica.
    Salva no clipboard.txt centralizado.

    Args:
        tipo_fluxo: Tipo de fluxo (POSITIVO, NEGATIVO, DESBLOQUEIO)
        series_processadas: Número de séries processadas
        ordens_processadas: Número de ordens processadas
        detalhes: Detalhes do processamento
        series_validas: Lista de séries processadas (para gerar relatório detalhado)
        driver: WebDriver SISBAJUD para extrair dados dos bloqueios (usado no fluxo POSITIVO)
        log: Se deve fazer log
        numero_processo: Número do processo para salvar no clipboard

    Returns:
        bool: True se relatório gerado com sucesso
    """
    try:
        # Estrutura HTML do relatório
        pStyle = 'class="corpo" style="font-size:12pt;line-height:1.5;margin-left:0 !important;text-align:justify !important;text-indent:4.5cm;"'
        relatorio_html = ""
        
        # ===== ETAPA 1: SEMPRE incluir relatório das séries primeiro =====
        if series_validas and len(series_validas) > 0:
            relatorio_html += f'<p {pStyle}><strong>Relatório de séries executadas:</strong></p>'
            
            for i, serie in enumerate(series_validas, 1):
                # Extrair dados da série
                numero_serie = serie.get('id_serie', 'N/A')
                data_conclusao = serie.get('data_conclusao')
                total_bloqueado = serie.get('valor_bloqueado', 0)
                total_bloqueado_text = serie.get('valor_bloqueado_text', '')
                
                # Formatar data
                if data_conclusao and hasattr(data_conclusao, 'strftime'):
                    data_str = data_conclusao.strftime('%d/%m/%Y')
                elif serie.get('data_conclusao_text'):
                    data_str = serie.get('data_conclusao_text')
                else:
                    data_str = 'Data não disponível'
                
                # Formatar valor (usar texto original se disponível)
                if total_bloqueado_text and total_bloqueado_text != 'R$ 0,00':
                    valor_str = total_bloqueado_text
                else:
                    valor_str = f"R$ {total_bloqueado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                
                # Adicionar linha da série
                linha_serie = f"- (Série {numero_serie}) - Data da finalização: ({data_str}) - Total bloqueado: ({valor_str})"
                relatorio_html += f'<p {pStyle}>{linha_serie}</p>'
        else:
            _ = series_validas
        
        # ===== ETAPA 1.5: ADICIONAR INFORMAÇÃO DE VALOR DA EXECUÇÃO (se estratégia presente) =====
        if estrategia:
            valor_exec = estrategia.get('valor_execucao', 0.0)
            total_bloq = estrategia.get('total_bloqueado', 0.0)
            
            valor_exec_fmt = f"R$ {valor_exec:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            total_bloq_fmt = f"R$ {total_bloq:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            relatorio_html += f'<p {pStyle}><strong>Valor da execução:</strong> {valor_exec_fmt}</p>'
            
            # Adicionar indicação de excesso no total bloqueado
            if estrategia.get('tipo') == 'TRANSFERIR_PARCIAL':
                relatorio_html += f'<p {pStyle}><strong>Total bloqueado nas séries:</strong> {total_bloq_fmt} (excede valor da execução)</p>'
            else:
                relatorio_html += f'<p {pStyle}><strong>Total bloqueado nas séries:</strong> {total_bloq_fmt}</p>'
        
        # ===== ETAPA 2: Processar baseado no tipo de fluxo =====
        if tipo_fluxo == 'POSITIVO':
            # Fluxo POSITIVO: gerar relatório detalhado dos bloqueios transferidos
            # Usar dados coletados DURANTE o processamento de cada ordem
            # (a extração da página acontece a cada ordem processada em _processar_series)
            dados_bloqueios = detalhes.get('dados_bloqueios', {}) if detalhes else {}
            
            # Gerar relatório se houver dados
            if dados_bloqueios and dados_bloqueios.get('executados'):
                if log:
                    erros_bloq = dados_bloqueios.get('ordens_com_erro_bloqueio', [])
                    logger.error(f'[SISBAJUD]    - ordens_com_erro_bloqueio: {len(erros_bloq)} erros')
                    if erros_bloq:
                        for idx, erro in enumerate(erros_bloq):
                            logger.error(f'[SISBAJUD]      Erro {idx+1}: {erro}')
                
                # Adicionar título de discriminação antes dos detalhes por executado
                relatorio_html += f'<p {pStyle}><strong>DISCRIMINAÇÃO DE BLOQUEIOS TRANSFERIDOS:</strong></p>'
                
                #  GERAR RELATÓRIOS SEPARADOS
                # Relatório CONCISO (para visualização rápida) - salvar em arquivo específico
                relatorio_conciso = gerar_relatorio_bloqueios_conciso(dados_bloqueios, log)
                
                # Salvar relatório CONCISO em arquivo específico (não no clipboard.txt)
                try:
                    # Salvar em PEC/sisbajud_conciso_ultimo.txt
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pasta raiz do projeto
                    pec_dir = os.path.join(base_dir, "PEC")
                    os.makedirs(pec_dir, exist_ok=True)
                    
                    arquivo_conciso = os.path.join(pec_dir, "sisbajud_conciso_ultimo.txt")
                    with open(arquivo_conciso, 'w', encoding='utf-8') as f:
                        f.write(relatorio_conciso)
                except Exception as e_conciso:
                    if log:
                        logger.error(f'[SISBAJUD]  Erro ao salvar relatório conciso: {e_conciso}')
                
                # Ajustar total_geral para valor da execução se TRANSFERIR_PARCIAL
                if estrategia and estrategia.get('tipo') == 'TRANSFERIR_PARCIAL':
                    dados_bloqueios['total_geral'] = estrategia.get('valor_execucao', dados_bloqueios['total_geral'])
                
                # Relatório DETALHADO (para juntada automática) - adicionar ao HTML principal
                relatorio_detalhado = gerar_relatorio_bloqueios_processados(dados_bloqueios, log)
                
                # Adicionar APENAS o detalhado ao relatório principal (usado pela juntada)
                relatorio_html += relatorio_detalhado
                
                # Mensagem final ajustada SOMENTE se for TRANSFERIR_PARCIAL (com desbloqueios)
                if estrategia and estrategia.get('tipo') == 'TRANSFERIR_PARCIAL':
                    ordens_desbloq = detalhes.get('ordens_desbloqueadas', [])
                    qtd_desbloq = len(ordens_desbloq)
                    
                    if qtd_desbloq > 0:
                        # Adicionar informação sobre desbloqueios
                        protocolos = [od.get('protocolo', 'N/A') for od in ordens_desbloq]
                        protocolos_str = ', '.join(protocolos)
                        relatorio_html += f'<p {pStyle}>Os valores excedentes ({qtd_desbloq} ordem(ns) - protocolos {protocolos_str}) foram devidamente <strong>DESBLOQUEADOS</strong>.</p>'
            else:
                # Fallback se não tiver dados detalhados
                relatorio_html += f'<p {pStyle}>Considerando os bloqueios realizados, as quantias localizadas foram <strong>TRANSFERIDAS</strong> à conta judicial do processo, ação que será efetivada em até 48h úteis.</p>'
                    
        elif tipo_fluxo == 'NEGATIVO':
            # Fluxo NEGATIVO: não houve bloqueios
            relatorio_html += f'<p {pStyle}>Não houve bloqueios realizados.</p>'
            
        elif tipo_fluxo == 'DESBLOQUEIO':
            # Fluxo DESBLOQUEIO: valores irrisórios desbloqueados
            relatorio_html += f'<p {pStyle}>Considerando as regras sobre bloqueios irrisórios, as quantias localizadas foram <strong>DESBLOQUEADAS</strong>, ação que será efetivada em até 48h úteis.</p>'
            
        else:
            # Fluxo não reconhecido
            relatorio_html += f'<p {pStyle}>Séries processadas: {series_processadas}</p>'
            relatorio_html += f'<p {pStyle}>Ordens processadas: {ordens_processadas}</p>'
            relatorio_html += f'<p {pStyle}>Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>'

        # Salvar no clipboard.txt centralizado
        try:
            from PEC.anexos import salvar_conteudo_clipboard
            
            # Salvar APENAS relatório DETALHADO - usado pela juntada
            # NÃO salvar o conciso aqui pois sobrescreveria o detalhado
            sucesso = salvar_conteudo_clipboard(
                conteudo=relatorio_html,
                numero_processo=numero_processo or "SISBAJUD",
                tipo_conteudo=f"sisbajud_{tipo_fluxo.lower()}",
                debug=log
            )
            
            if sucesso:
                _ = sucesso
            else:
                _ = sucesso
                    
        except ImportError as e:
            _ = e

        return True

    except Exception as e:
        if log:
            logger.error(f'[SISBAJUD]  Erro ao gerar relatório: {e}')
        return False
