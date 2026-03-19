import logging
logger = logging.getLogger(__name__)

"""
SISB Series Processor - Processamento de séries SISBAJUD
Funções para filtrar, processar e gerenciar séries de ordens
"""

import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _filtrar_series(driver, data_limite):
    """
    Helper para filtrar séries válidas da tabela.
    Implementa lógica corrigida:
    1. Extrair dados das séries via JS
    2. Validar cada série em Python
    3. Enriquecer dados válidos
    4. Retornar apenas séries válidas

    Args:
        driver: Driver SISBAJUD
        data_limite: Data limite para filtro

    Returns:
        list: Lista de séries válidas enriquecidas
    """
    try:
        # Aguardar tabela Angular renderizar antes de executar JS
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.mat-table tbody tr.mat-row'))
            )
            logger.info('[SISBAJUD]  Tabela de séries carregada')
        except Exception:
            logger.info('[SISBAJUD]  Timeout aguardando tabela — tentando JS mesmo assim')

        # ETAPA 1: EXTRAIR DADOS DA TABELA VIA JS (usando lógica do bookmarklet funcional)
        # IMPORTANTE: execute_script precisa de 'return' no nível top-level,
        # senão retorna None mesmo que o IIFE retorne algo internamente.
        script_extrair = """
        return (function() {
            try {
                var series = [];
                var rows = document.querySelectorAll('table.mat-table tbody tr.mat-row');
                var months = {JAN:0, FEV:1, MAR:2, ABR:3, MAI:4, JUN:5,
                              JUL:6, AGO:7, SET:8, OUT:9, NOV:10, DEZ:11};
                var now = new Date();
                var limit = new Date();
                limit.setDate(now.getDate() - 15);

                rows.forEach(function(row) {
                    try {
                        var id       = row.querySelector('td[data-label="sequencial"]');
                        var protocolo = row.querySelector('td[data-label="protocolo"]');
                        var processo  = row.querySelector('td[data-label="processo"]');
                        var situacao  = row.querySelector('td[data-label="dataFim"]');
                        var sched     = row.querySelector('td[data-label="dataProgramada"]');
                        var blocked   = row.querySelector('td[data-label="valorBloqueado"]');
                        var bloquear  = row.querySelector('td[data-label="valorBloquear"]');

                        if (id && sched && blocked) {
                            var dateText = sched.textContent.trim();
                            var parts = dateText.replace(/\\./g, '').toUpperCase().split(' ');

                            if (parts.length >= 5) {
                                var day   = parseInt(parts[0], 10);
                                var month = months[parts[2]];
                                var year  = parseInt(parts[4], 10);

                                if (!isNaN(day) && month !== undefined && !isNaN(year)) {
                                    var parsed = new Date(year, month, day);
                                    if (parsed >= limit) {
                                        series.push({
                                            id_serie:             id.textContent.trim(),
                                            protocolo:            protocolo ? protocolo.textContent.trim() : '',
                                            processo:             processo  ? processo.textContent.trim()  : '',
                                            situacao:             situacao  ? situacao.textContent.trim()  : '',
                                            data_conclusao:       dateText,
                                            valor_bloqueado_text: blocked.textContent.trim(),
                                            valor_bloquear_text:  bloquear ? bloquear.textContent.trim() : 'R$ 0,00',
                                            acao: ''
                                        });
                                    }
                                }
                            }
                        }
                    } catch(e) {}
                });

                return {sucesso: true, series: series};
            } catch(err) {
                return {sucesso: false, erro: err.message};
            }
        })();
        """

        resultado = driver.execute_script(script_extrair)
        
        if not resultado or not resultado.get('sucesso'):
            logger.error(f'[SISBAJUD]  Erro na extração: {resultado.get("erro") if resultado else "Erro desconhecido"}')
            return []

        series_bruto = resultado.get('series', [])

        # ETAPA 2: VALIDAR E ENRIQUECER SÉRIES
        series_validas = []
        meses_map = {
            'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
            'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
        }

        def extrair_valor_monetario(texto):
            """Converte texto monetário para float"""
            texto_limpo = texto.replace('R$', '').replace('\xa0', '').replace('&nbsp;', '').strip()
            texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
            try:
                return float(texto_limpo)
            except:
                return 0.0

        for idx, serie_raw in enumerate(series_bruto, 1):
            try:
                id_serie = serie_raw.get('id_serie', 'DESCONHECIDA')
                logger.info(f'[SISBAJUD]  Analisando série {idx}: {id_serie}')

                # VALIDAÇÃO 1: Verificar se temos dados essenciais
                data_texto = serie_raw.get('data_conclusao', '').strip()
                if not data_texto:
                    logger.info(f'[SISBAJUD]    Rejeitada: data vazia')
                    continue

                # VALIDAÇÃO 2: Validar e parsear data (formato brasileiro)
                # Formatos possíveis: "15 DEZ 2025" ou "1 DE MAR. DE 2026"
                partes = data_texto.replace('.', '').upper().split()

                # Tentar diferentes padrões de parsing
                dia, mes_nome, ano = None, None, None

                if len(partes) == 3:
                    # Formato: "15 DEZ 2025"
                    dia = partes[0]
                    mes_nome = partes[1]
                    ano = partes[2]
                elif len(partes) == 5 and partes[1] == 'DE' and partes[3] == 'DE':
                    # Formato: "1 DE MAR DE 2026"
                    dia = partes[0]
                    mes_nome = partes[2]  # MAR
                    ano = partes[4]
                else:
                    logger.info(f'[SISBAJUD]    Rejeitada: formato de data não reconhecido "{data_texto}" ({len(partes)} partes: {partes})')
                    continue

                try:
                    dia = int(dia)
                    ano = int(ano)
                    mes = meses_map.get(mes_nome)

                    if not mes:
                        logger.info(f'[SISBAJUD]    Rejeitada: mês inválido "{mes_nome}"')
                        continue

                    data_serie = datetime(ano, mes, dia)
                except (ValueError, IndexError) as e:
                    logger.info(f'[SISBAJUD]    Rejeitada: erro ao parsear data - {e}')
                    continue

                # VALIDAÇÃO 3: Verificar data limite (>= limite, como no JS fornecido)
                if data_serie < data_limite:
                    logger.info(f'[SISBAJUD]    Rejeitada: data {data_serie.strftime("%d/%m/%Y")} < limite ({data_limite.strftime("%d/%m/%Y")})')
                    continue

                logger.info(f'[SISBAJUD]    Data válida: {data_serie.strftime("%d/%m/%Y")}')

                # ENRIQUECIMENTO: Converter valores monetários
                valor_bloqueado_text = serie_raw.get('valor_bloqueado_text', 'R$ 0,00')
                valor_bloquear_text = serie_raw.get('valor_bloquear_text', 'R$ 0,00')
                
                valor_bloqueado = extrair_valor_monetario(valor_bloqueado_text)
                valor_bloquear = extrair_valor_monetario(valor_bloquear_text)

                # CRIAR SÉRIE VÁLIDA ENRIQUECIDA
                serie_valida = {
                    'id_serie': id_serie,
                    'protocolo': serie_raw.get('protocolo', ''),
                    'processo': serie_raw.get('processo', ''),
                    'acao': serie_raw.get('acao', ''),
                    'data_conclusao': data_serie,
                    'data_conclusao_text': data_texto,
                    'situacao': serie_raw.get('situacao', ''),
                    'valor_bloqueado': valor_bloqueado,
                    'valor_bloquear': valor_bloquear,
                    'valor_bloqueado_text': valor_bloqueado_text,
                    'valor_bloquear_text': valor_bloquear_text,
                    'linha_index': serie_raw.get('linha_index', idx - 1)
                }

                series_validas.append(serie_valida)
                logger.info(f'[SISBAJUD]    Série válida: R${valor_bloqueado:.2f} bloqueado')

            except Exception as e:
                logger.info(f'[SISBAJUD]   Erro processando série {idx}: {e}')
                continue

        # RESUMO FINAL
        logger.info(f'[SISBAJUD]  Filtradas {len(series_validas)} séries válidas de {len(series_bruto)}')
        if series_validas:
            logger.info('[SISBAJUD]  Séries válidas:')
            for s in series_validas:
                logger.info(f'  - ID: {s["id_serie"]}, Data: {s["data_conclusao_text"]}, Situação: {s["situacao"]}')
            
            total_bloqueado = sum(s['valor_bloqueado'] for s in series_validas)
            logger.info(f'[SISBAJUD]  Total bloqueado das séries válidas: R$ {total_bloqueado:.2f}')

        return series_validas

    except Exception as e:
        logger.info(f'[SISBAJUD]  Erro ao filtrar séries: {e}')
        import traceback
        logger.exception("Erro detectado")
        return []


def _navegar_e_extrair_ordens_serie(driver, serie, log=True):
    """
    Navega para uma série específica e extrai suas ordens.

    Args:
        driver: WebDriver do Selenium
        serie: Dicionário com dados da série (deve conter 'id_serie')
        log: Se deve fazer log

    Returns:
        list: Lista de ordens da série
    """
    try:
        id_serie = serie.get('id_serie')
        if not id_serie:
            return []

        if log:
            logger.info(f"[SISBAJUD] Navegando para detalhes da série {id_serie}")

        # Navegar diretamente para a URL da série
        url_serie = f"https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes"
        driver.get(url_serie)
        time.sleep(3)  # Aguardar carregamento da página

        # Verificar se chegou na página correta
        if f"/{id_serie}/detalhes" not in driver.current_url:
            if log:
                logger.info(f"[SISBAJUD]  URL atual não corresponde à série: {driver.current_url}")
            return []

        if log:
            logger.info(f"[SISBAJUD]  Navegação direta bem-sucedida para série {id_serie}")

        # Aguardar a tabela de ordens carregar
        time.sleep(2)

        # Extrair ordens da série
        from ..ordens import _extrair_ordens_da_serie
        ordens = _extrair_ordens_da_serie(driver, log)
        if log:
            logger.info(f"[SISBAJUD]  {len(ordens)} ordens extraídas da série {id_serie}")

        return ordens

    except Exception as e:
        if log:
            logger.info(f"[SISBAJUD]  Erro na navegação para série {serie.get('id_serie', 'unknown')}: {str(e)}")
        return []


def _extrair_nome_executado_serie(driver, log=True):
    """
    Tenta extrair o nome do executado na página de detalhes da série.
    Usa múltiplos seletores para maior robustez.
    """
    try:
        # Tentativa 1: Cabeçalho do expansion panel (mais comum no SISBAJUD)
        try:
            header = driver.find_element(By.CSS_SELECTOR, "mat-expansion-panel-header .col-reu-dados-nome-pessoa")
            if header and header.text.strip():
                if log:
                    logger.info(f"[SISBAJUD] Executado encontrado via expansion-panel: {header.text.strip()}")
                return header.text.strip()
        except Exception as e:
            _ = e
        
        # Tentativa 2: Cabeçalho principal com traço
        try:
            header = driver.find_element(By.CSS_SELECTOR, "div.header-title, .mat-card-title, h1, h2")
            if header:
                text = header.text
                # Se tiver formato "Detalhes da ordem - NOME DO EXECUTADO"
                if "-" in text:
                    nome = text.split("-")[-1].strip()
                    if nome and len(nome) > 3:
                        if log:
                            logger.info(f"[SISBAJUD] Executado encontrado via header: {nome}")
                        return nome
        except Exception as e:
            _ = e
            
        # Tentativa 3: Card de detalhes do réu
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, "mat-card-title, .card-title, .reu-nome")
            for card in cards:
                text = card.text.strip()
                if text and len(text) > 3 and "Executado" not in text and "Ordem" not in text and "Série" not in text:
                    if log:
                        logger.info(f"[SISBAJUD] Executado encontrado via card: {text}")
                    return text
        except Exception as e:
            _ = e
            
        # Tentativa 4: Buscar por label "Réu" ou "Executado"
        try:
            labels = driver.find_elements(By.XPATH, "//*[contains(text(), 'Réu') or contains(text(), 'Executado')]/following-sibling::*[1]")
            for label in labels:
                text = label.text.strip()
                if text and len(text) > 3:
                    if log:
                        logger.info(f"[SISBAJUD] Executado encontrado via label: {text}")
                    return text
        except Exception as e:
            _ = e
            
        # Tentativa 5: Buscar na URL (algumas páginas têm o nome codificado)
        try:
            url = driver.current_url
            # Tentar extrair de parâmetros da URL se existir
            if "nome=" in url.lower():
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                if 'nome' in params:
                    nome = params['nome'][0]
                    if log:
                        logger.info(f"[SISBAJUD] Executado encontrado via URL: {nome}")
                    return nome
        except Exception as e:
            _ = e

        if log:
            logger.info("[SISBAJUD]  Nome do executado não identificado, usando placeholder")
        return "Executado"
    except Exception as e:
        if log:
            logger.info(f"[SISBAJUD]  Erro ao extrair nome do executado: {e}")
        return "Executado"


def _processar_series(driver, series_validas, tipo_fluxo, log=True, estrategia=None):
    """
    Helper para processar séries e suas ordens.
    Com estratégia TRANSFERIR_PARCIAL: transfere até limite, pula 1, desbloqueia restantes.
    
    Args:
        driver: Driver SISBAJUD
        series_validas: Lista de séries válidas
        tipo_fluxo: Tipo de fluxo (POSITIVO, NEGATIVO, DESBLOQUEIO)
        log: Se deve fazer log
        estrategia: Dict com estratégia de bloqueio (None = processar tudo normal)
    
    Returns:
        dict: Resultado do processamento com keys: series_processadas, ordens_processadas, erros, detalhes
    """
    try:
        if log:
            logger.info(f'[SISBAJUD] Processando {len(series_validas)} séries...')

        resultado = {
            'series_processadas': 0,
            'ordens_processadas': 0,
            'erros': [],
            'detalhes': {
                'dados_bloqueios': {
                    'executados': {},
                    'total_geral': 0.0,
                    'ordens_com_erro_bloqueio': []  # Lista de ordens com erro de bloqueio
                },
                'ordens_transferidas': [],  # NOVO: rastrear ordens transferidas
                'ordem_pendente': None,      # NOVO: ordem que ficou pendente
                'ordens_desbloqueadas': []   # NOVO: ordens desbloqueadas
            }
        }

        # Controle de acumulado para estratégia parcial
        acumulado_transferido = 0.0
        usar_estrategia_parcial = (estrategia and estrategia.get('tipo') == 'TRANSFERIR_PARCIAL')
        limite_execucao = estrategia.get('acumulado_limite', 0.0) if usar_estrategia_parcial else 0.0
        ordem_pulada = False

        for idx_serie, serie in enumerate(series_validas, 1):
            if log:
                logger.info(f'[SISBAJUD] >>> Processando série {idx_serie}/{len(series_validas)}: {serie["id_serie"]}')

            try:
                # 1. Navegar para detalhes da série e extrair ordens
                ordens = _navegar_e_extrair_ordens_serie(driver, serie, log)
                if not ordens:
                    if log:
                        logger.info(f'[SISBAJUD]  Nenhuma ordem extraída da série {serie["id_serie"]}')
                    # Série sem ordens - voltar para lista principal
                    from ..navigation import _voltar_para_lista_principal
                    _voltar_para_lista_principal(driver, log)
                    continue

                # 1.5 Extrair nome do executado (após navegar)
                nome_executado = _extrair_nome_executado_serie(driver, log)
                if log:
                    logger.info(f'[SISBAJUD] Executado identificado: {nome_executado}')

                # 2. Identificar ordens com bloqueio
                from ..ordens import _identificar_ordens_com_bloqueio
                valor_bloqueado = float(serie.get('valor_bloqueado', 0))
                ordens_bloqueadas = _identificar_ordens_com_bloqueio(ordens, valor_bloqueado, log)

                if not ordens_bloqueadas:
                    if log:
                        logger.info(f'[SISBAJUD]  Nenhuma ordem com bloqueio encontrada na série {serie["id_serie"]}, voltando para lista de séries')
                    # Série sem bloqueio - voltar para lista principal
                    from ..navigation import _voltar_para_lista_principal
                    _voltar_para_lista_principal(driver, log)
                    resultado['series_processadas'] += 1
                    continue
                
                # Ordenar ordens por valor (decrescente) para otimizar transferências
                if usar_estrategia_parcial:
                    ordens_bloqueadas_ordenadas = sorted(ordens_bloqueadas, key=lambda o: float(o.get('valor_bloquear', 0)), reverse=True)
                    if log:
                        logger.info(f'[SISBAJUD]  {len(ordens_bloqueadas)} ordens ordenadas por valor (maior primeiro)')
                    ordens_bloqueadas = ordens_bloqueadas_ordenadas

                # 3. Processar cada ordem com bloqueio COM estratégia
                total_ordens_serie = len(ordens_bloqueadas)
                for idx_ordem, ordem in enumerate(ordens_bloqueadas, 1):
                    sequencial_ordem = ordem.get('sequencial')
                    situacao_ordem = ordem.get('situacao', '')
                    
                    if log:
                        logger.info(f'\n[SISBAJUD] >>> Processando ordem {idx_ordem}/{total_ordens_serie} da série {serie["id_serie"]}')
                        logger.info(f'[SISBAJUD] Ordem: {sequencial_ordem}, Protocolo: {ordem.get("protocolo", "N/A")}')
                    
                    # Verificar se ordem já está "Respondida com minuta"
                    # Abrir apenas para extrair discriminação (nunca terá erro aqui)
                    if "Respondida com minuta" in situacao_ordem:
                        if log:
                            logger.info(f'[SISBAJUD] Ordem {sequencial_ordem} já processada (Respondida com minuta)')
                        
                        # Abrir para extrair dados se for fluxo POSITIVO
                        if tipo_fluxo == 'POSITIVO':
                            if log:
                                logger.info(f'[SISBAJUD]     Extraindo dados da ordem já processada...')
                            try:
                                from ..processamento import _processar_ordem
                                sucesso = _processar_ordem(driver, ordem, tipo_fluxo, log, apenas_extrair=True)
                                
                                # Agrupar dados extraídos (nunca será erro, sempre discriminação)
                                from ..relatorios import _agrupar_dados_bloqueios
                                if sucesso and '_relatorio' in ordem and ordem['_relatorio'].get('discriminacao'):
                                    _agrupar_dados_bloqueios(
                                        resultado['detalhes']['dados_bloqueios'],
                                        ordem['_relatorio']['discriminacao'],
                                        log
                                    )
                                    if log:
                                        logger.info(f'[SISBAJUD]     Dados extraídos e agrupados')
                                
                            except Exception as e:
                                if log:
                                    logger.info(f'[SISBAJUD]     Erro ao extrair dados: {e}')
                        
                        resultado['ordens_processadas'] += 1
                        continue
                    
                    # Limpar referências de elementos obsoletos antes de cada processamento
                    if 'linha_el' in ordem:
                        ordem['linha_el'] = None
                    
                    # Determinar ação para esta ordem baseado na estratégia
                    valor_ordem = float(ordem.get('valor_bloquear', 0))
                    acao = None
                    valor_a_transferir = None  # Para transferência parcial
                    
                    if not usar_estrategia_parcial:
                        # Estratégia normal: transferir tudo
                        acao = 'TRANSFERIR'
                    else:
                        # Estratégia parcial: decidir baseado no acumulado
                        if acumulado_transferido >= limite_execucao:
                            # Já atingiu ou ultrapassou o limite - desbloquear todas restantes
                            acao = 'DESBLOQUEAR'
                        else:
                            projecao = acumulado_transferido + valor_ordem
                            
                            if projecao <= limite_execucao:
                                # Ainda cabe - transferir
                                acao = 'TRANSFERIR'
                            else:
                                # Esta ordem faria ultrapassar - transferir parcialmente
                                valor_restante = limite_execucao - acumulado_transferido
                                acao = 'TRANSFERIR_PARCIAL'
                                valor_a_transferir = valor_restante
                                ordem_pulada = True
                                if log:
                                    logger.info(f'[SISBAJUD]      Ordem {sequencial_ordem}: TRANSFERÊNCIA PARCIAL (R$ {valor_restante:.2f} de R$ {valor_ordem:.2f})')
                    
                    try:
                        # Executar ação conforme estratégia
                        if acao in ['TRANSFERIR', 'TRANSFERIR_PARCIAL']:
                            if log and usar_estrategia_parcial and acao == 'TRANSFERIR':
                                logger.info(f'[SISBAJUD]    ▶  Ordem {sequencial_ordem}: TRANSFERIR (R$ {valor_ordem:.2f})')
                            
                            from ..processamento import _processar_ordem
                            
                            # Processar ordem (sem retry automático - se falhar, para tudo)
                            sucesso_processamento = _processar_ordem(
                                driver, 
                                ordem, 
                                tipo_fluxo, 
                                log,
                                valor_parcial=valor_a_transferir if acao == 'TRANSFERIR_PARCIAL' else None
                            )
                            
                            # CRÍTICO: Se falhou após todas as tentativas, VERIFICAR MOTIVO
                            if not sucesso_processamento:
                                # VERIFICAR SE É ERRO DE BLOQUEIO (valor zerado no sistema)
                                if '_relatorio' in ordem and ordem['_relatorio'].get('status') == 'erro':
                                    rel = ordem['_relatorio']
                                    erro = f' ERRO DE BLOQUEIO: Ordem {sequencial_ordem} - {rel.get("erro_msg", "erro desconhecido")}'
                                    if log:
                                        logger.info(f'[SISBAJUD]   {erro}')
                                    resultado['erros'].append(erro)
                                    
                                    # Adicionar à lista de erros de bloqueio
                                    erro_item = {
                                        'protocolo': rel['protocolo'],
                                        'valor_esperado': rel['valor_esperado'],
                                        'erro_msg': rel.get('erro_msg', 'Erro desconhecido')
                                    }
                                    resultado['detalhes']['dados_bloqueios']['ordens_com_erro_bloqueio'].append(erro_item)
                                    if log:
                                        logger.info(f'[SISBAJUD]    Erro adicionado à lista: {erro_item}')
                                    
                                    # CONTINUAR para próxima ordem (não parar tudo)
                                    continue
                                
                                # Se não é erro de bloqueio, é erro real - PARAR TUDO
                                erro = f' CRÍTICO: Impossível processar ordem {sequencial_ordem}'
                                if log:
                                    logger.info(f'[SISBAJUD]   {erro}')
                                resultado['erros'].append(erro)
                                # NÃO continuar - retornar resultado parcial
                                return resultado
                            
                            if sucesso_processamento:
                                valor_transferido = valor_a_transferir if acao == 'TRANSFERIR_PARCIAL' else valor_ordem
                                acumulado_transferido += valor_transferido
                                resultado['ordens_processadas'] += 1
                                resultado['detalhes']['ordens_transferidas'].append({
                                    'sequencial': sequencial_ordem,
                                    'valor': valor_transferido,
                                    'serie': serie['id_serie'],
                                    'parcial': acao == 'TRANSFERIR_PARCIAL'
                                })
                                
                                if log:
                                    logger.info(f'[SISBAJUD]    Ordem {sequencial_ordem} processada com sucesso')
                                
                                # ===== EXTRAIR DADOS IMEDIATAMENTE APÓS PROCESSAMENTO (ANTES DE VOLTAR) =====
                                if tipo_fluxo == 'POSITIVO':
                                    protocolo_ordem = ordem.get('protocolo', 'N/A')
                                    if log:
                                        logger.info(f'[SISBAJUD]  Extraindo dados dos bloqueios da página (Protocolo: {protocolo_ordem})...')
                                    
                                    try:
                                        from ..relatorios import extrair_dados_bloqueios_processados, _agrupar_dados_bloqueios
                                        dados_ordem = extrair_dados_bloqueios_processados(driver, log, protocolo_ordem=protocolo_ordem)
                                        
                                        # Atualizar entrada do relatório
                                        if '_relatorio' in ordem:
                                            ordem['_relatorio']['status'] = 'processado'
                                            ordem['_relatorio']['discriminacao'] = dados_ordem
                                        
                                        if dados_ordem and dados_ordem.get('executados'):
                                            _agrupar_dados_bloqueios(
                                                resultado['detalhes']['dados_bloqueios'], 
                                                dados_ordem, 
                                                log
                                            )
                                            if log:
                                                logger.info(f'[SISBAJUD]    Dados extraídos da ordem {sequencial_ordem}')
                                        else:
                                            if log:
                                                logger.info(f'[SISBAJUD]    Nenhum dado de bloqueio extraído da ordem {sequencial_ordem}')
                                                
                                    except Exception as e_dados:
                                        if log:
                                            logger.info(f'[SISBAJUD]    Erro ao extrair dados para relatório: {e_dados}')
                            
                            # Se chegou aqui, processamento foi sucesso (não teria retornado antes)
                        
                        elif acao == 'DESBLOQUEAR':
                            if log:
                                logger.info(f'[SISBAJUD]    Ordem {sequencial_ordem}: DESBLOQUEAR (R$ {valor_ordem:.2f})')
                            
                            from ..processamento import _processar_ordem
                            
                            # Processar ordem (sem retry automático - se falhar, para tudo)
                            sucesso_processamento = _processar_ordem(driver, ordem, 'DESBLOQUEIO', log)
                            
                            # CRÍTICO: Se falhou, PARAR TUDO
                            if not sucesso_processamento:
                                erro = f'CRÍTICO: Impossível desbloquear ordem {sequencial_ordem}'
                                if log:
                                    logger.info(f'[SISBAJUD]   {erro}')
                                resultado['erros'].append(erro)
                                # NÃO continuar - retornar resultado parcial
                                return resultado
                            
                            if sucesso_processamento:
                                resultado['ordens_processadas'] += 1
                                resultado['detalhes']['ordens_desbloqueadas'].append({
                                    'sequencial': sequencial_ordem,
                                    'valor': valor_ordem,
                                    'serie': serie['id_serie'],
                                    'protocolo': ordem.get('protocolo', 'N/A')
                                })
                                if log:
                                    logger.info(f'[SISBAJUD]    Ordem {sequencial_ordem} desbloqueada com sucesso')
                            
                            # Se chegou aqui, processamento foi sucesso (não teria retornado antes)
                        
                        # ===== NAVEGAÇÃO APÓS PROCESSAR ORDEM COM SUCESSO =====
                        if idx_ordem < total_ordens_serie:
                            # Ainda há mais ordens para processar nesta série
                            if log:
                                logger.info(f'[SISBAJUD] Voltando para lista de ordens (mais {total_ordens_serie - idx_ordem} ordens restantes)...')
                            from ..navigation import _voltar_para_lista_ordens_serie
                            _voltar_para_lista_ordens_serie(driver, log)
                            
                            # Invalidar referências de elementos após nova página
                            for ordem_restante in ordens_bloqueadas[idx_ordem:]:
                                if 'linha_el' in ordem_restante:
                                    ordem_restante['linha_el'] = None
                            if log:
                                logger.info(f'[SISBAJUD]  Elementos invalidados após retorno (ordens restantes)')
                        else:
                            # Última ordem da série, voltar para lista de séries
                            if log:
                                logger.info(f'[SISBAJUD] Última ordem da série {serie["id_serie"]}, voltando para lista de séries')
                            from ..navigation import _voltar_para_lista_principal
                            _voltar_para_lista_principal(driver, log)
                        
                    except Exception as e:
                        erro = f'Erro ao processar ordem {ordem["sequencial"]} da série {serie["id_serie"]}: {str(e)}'
                        if log:
                            logger.info(f'[SISBAJUD]  {erro}')
                        resultado['erros'].append(erro)
                        
                        # Navegar de volta após erro
                        try:
                            if idx_ordem < total_ordens_serie:
                                from ..navigation import _voltar_para_lista_ordens_serie
                                _voltar_para_lista_ordens_serie(driver, log)
                                # Invalidar elementos após retorno
                                for ordem_restante in ordens_bloqueadas[idx_ordem:]:
                                    if 'linha_el' in ordem_restante:
                                        ordem_restante['linha_el'] = None
                        except Exception as nav_err:
                            _ = nav_err

                resultado['series_processadas'] += 1

            except Exception as e:
                erro = f'Erro na série {serie.get("id_serie", "unknown")}: {str(e)}'
                if log:
                    logger.info(f'[SISBAJUD]  {erro}')
                resultado['erros'].append(erro)
                
                # Tentar voltar para lista de séries após erro
                try:
                    from ..navigation import _voltar_para_lista_principal
                    _voltar_para_lista_principal(driver, log)
                except Exception as nav_err:
                    _ = nav_err
                continue

        if log:
            logger.info(f'[SISBAJUD]  Processamento concluído: {resultado["series_processadas"]} séries, {resultado["ordens_processadas"]} ordens')
            if usar_estrategia_parcial:
                logger.info(f'[SISBAJUD]     Total transferido: R$ {acumulado_transferido:.2f} de R$ {limite_execucao:.2f}')
                logger.info(f'[SISBAJUD]     Ordens transferidas: {len(resultado["detalhes"]["ordens_transferidas"])}')
                logger.info(f'[SISBAJUD]    ⏭  Ordem pendente: {1 if resultado["detalhes"]["ordem_pendente"] else 0}')
                logger.info(f'[SISBAJUD]     Ordens desbloqueadas: {len(resultado["detalhes"]["ordens_desbloqueadas"])}')

        return resultado

    except Exception as e:
        if log:
            logger.info(f'[SISBAJUD]  Erro geral no processamento: {e}')
        return {'series_processadas': 0, 'ordens_processadas': 0, 'erros': [str(e)], 'detalhes': {}}


def _calcular_estrategia_bloqueio(series_validas, dados_processo, log=True):
    """
    Calcula estratégia de bloqueio comparando valor total bloqueado com valor da execução.
    
    Lógica:
    - Se total_bloqueado <= valor_execucao: transferir TUDO (estratégia padrão)
    - Se total_bloqueado > valor_execucao:
      * Transferir ordens até a que NÃO ultrapassaria o limite
      * Pular a ordem que ultrapassaria (sem tratamento)
      * Desbloquear todas as ordens seguintes (desta e outras séries)
    
    Args:
        series_validas: Lista de séries válidas
        dados_processo: Dados do processo (inclui divida.valor)
        log: Se deve fazer log
    
    Returns:
        dict: {
            'tipo': 'TRANSFERIR_TUDO' | 'TRANSFERIR_PARCIAL',
            'valor_execucao': float,
            'total_bloqueado': float,
            'acumulado_limite': float
        }
    """
    try:
        # 1. Extrair valor da execução
        valor_execucao_str = dados_processo.get('divida', {}).get('valor', 'R$ 0,00')
        # Converter para float
        texto_limpo = valor_execucao_str.replace('R$', '').replace('\xa0', '').replace('&nbsp;', '').strip()
        texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
        try:
            valor_execucao = float(texto_limpo)
        except:
            valor_execucao = 0.0
        
        # 2. Calcular total bloqueado
        total_bloqueado = sum(float(s.get('valor_bloqueado', 0)) for s in series_validas)
        
        if log:
            logger.info(f'[SISBAJUD]  Estratégia de bloqueio:')
            logger.info(f'[SISBAJUD]    Valor da execução: R$ {valor_execucao:.2f}')
            logger.info(f'[SISBAJUD]    Total bloqueado: R$ {total_bloqueado:.2f}')
        
        # 3. Decidir estratégia
        if total_bloqueado <= valor_execucao:
            if log:
                logger.info(f'[SISBAJUD]     Estratégia: TRANSFERIR TUDO (bloqueado não excede execução)')
            return {
                'tipo': 'TRANSFERIR_TUDO',
                'valor_execucao': valor_execucao,
                'total_bloqueado': total_bloqueado,
                'acumulado_limite': valor_execucao
            }
        
        # 4. Total excede - usar transferência parcial
        if log:
            excesso = total_bloqueado - valor_execucao
            logger.info(f'[SISBAJUD]     Estratégia: TRANSFERIR PARCIAL (bloqueado excede em R$ {excesso:.2f})')
            logger.info(f'[SISBAJUD]     Será: transferir até limite, pular 1 ordem, desbloquear restantes')
        
        return {
            'tipo': 'TRANSFERIR_PARCIAL',
            'valor_execucao': valor_execucao,
            'total_bloqueado': total_bloqueado,
            'acumulado_limite': valor_execucao
        }
        
    except Exception as e:
        if log:
            logger.info(f'[SISBAJUD]  Erro ao calcular estratégia: {e}')
        # Em caso de erro, usar estratégia padrão
        return {
            'tipo': 'TRANSFERIR_TUDO',
            'valor_execucao': 0.0,
            'total_bloqueado': 0.0,
            'acumulado_limite': 0.0
        }
