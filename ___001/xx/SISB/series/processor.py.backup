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

from ..utils import criar_js_otimizado


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
        # ETAPA 1: EXTRAIR DADOS DA TABELA VIA JS
        script_extrair = f"""
        {criar_js_otimizado()}

        async function extrairSeries() {{
            try {{
                let tabela = await esperarElemento('table.mat-table', 10000);
                if (!tabela) return {{sucesso: false, erro: 'Tabela não encontrada'}};

                let linhas = tabela.querySelectorAll('tbody tr.mat-row');
                let series = [];

                for (let i = 0; i < linhas.length; i++) {{
                    let linha = linhas[i];
                    let colunas = linha.querySelectorAll('td');
                    
                    // Extrair cada coluna
                    let serie = {{
                        linha_index: i
                    }};
                    
                    if (colunas.length >= 8) {{
                        serie.id_serie = colunas[0].textContent.trim();
                        serie.protocolo = colunas[1].textContent.trim();
                        serie.acao = colunas[2].textContent.trim();
                        serie.valor_bloquear_text = colunas[3].textContent.trim();
                        serie.valor_bloqueado_text = colunas[4].textContent.trim();
                        serie.data_conclusao = colunas[5].textContent.trim();
                        serie.situacao = colunas[6].textContent.trim();
                    }}
                    
                    series.push(serie);
                }}

                return {{sucesso: true, series: series}};
            }} catch(e) {{
                return {{sucesso: false, erro: e.message}};
            }}
        }}

        return extrairSeries().then(arguments[arguments.length - 1]);
        """

        resultado = driver.execute_async_script(script_extrair)
        if not resultado or not resultado.get('sucesso'):
            logger.error(f'[SISBAJUD]  Erro na extração: {resultado.get("erro")}')
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
                print(f'[SISBAJUD] 🔍 Analisando série {idx}: {id_serie}')

                # VALIDAÇÃO 1: Verificar situação (deve conter "encerrada")
                situacao = serie_raw.get('situacao', '').strip()
                if 'encerrada' not in situacao.lower():
                    print(f'[SISBAJUD]   ❌ Rejeitada: situação="{situacao}" (não é "encerrada")')
                    continue

                print(f'[SISBAJUD]   ✅ Situação válida: {situacao}')

                # VALIDAÇÃO 2: Validar e parsear data
                data_texto = serie_raw.get('data_conclusao', '').strip()
                if not data_texto:
                    print(f'[SISBAJUD]   ❌ Rejeitada: data vazia')
                    continue

                partes = data_texto.upper().split()
                if len(partes) < 5:
                    print(f'[SISBAJUD]   ❌ Rejeitada: formato de data inválido')
                    continue

                try:
                    dia = int(partes[0])
                    mes_nome = partes[2]
                    ano = int(partes[4])
                    mes = meses_map.get(mes_nome)

                    if not mes:
                        print(f'[SISBAJUD]   ❌ Rejeitada: mês inválido "{mes_nome}"')
                        continue

                    data_serie = datetime(ano, mes, dia)
                except (ValueError, IndexError) as e:
                    print(f'[SISBAJUD]   ❌ Rejeitada: erro ao parsear data - {e}')
                    continue

                # VALIDAÇÃO 3: Verificar data limite
                if isinstance(data_limite, datetime) and data_serie < data_limite:
                    print(f'[SISBAJUD]   ❌ Rejeitada: data {data_serie.strftime("%d/%m/%Y")} < limite {data_limite.strftime("%d/%m/%Y")}')
                    continue

                print(f'[SISBAJUD]   ✅ Data válida: {data_serie.strftime("%d/%m/%Y")}')

                # ENRIQUECIMENTO: Converter valores monetários
                valor_bloqueado_text = serie_raw.get('valor_bloqueado_text', 'R$ 0,00')
                valor_bloquear_text = serie_raw.get('valor_bloquear_text', 'R$ 0,00')
                
                valor_bloqueado = extrair_valor_monetario(valor_bloqueado_text)
                valor_bloquear = extrair_valor_monetario(valor_bloquear_text)

                # CRIAR SÉRIE VÁLIDA ENRIQUECIDA
                serie_valida = {
                    'id_serie': id_serie,
                    'protocolo': serie_raw.get('protocolo', ''),
                    'acao': serie_raw.get('acao', ''),
                    'data_conclusao': data_serie,
                    'data_conclusao_text': data_texto,
                    'situacao': situacao,
                    'valor_bloqueado': valor_bloqueado,
                    'valor_bloquear': valor_bloquear,
                    'valor_bloqueado_text': valor_bloqueado_text,
                    'valor_bloquear_text': valor_bloquear_text,
                    'linha_index': serie_raw.get('linha_index', idx - 1)
                }

                series_validas.append(serie_valida)
                print(f'[SISBAJUD]   ✅ Série válida: R${valor_bloqueado:.2f} bloqueado, R${valor_bloquear:.2f} a bloquear')

            except Exception as e:
                print(f'[SISBAJUD] ⚠️  Erro processando série {idx}: {e}')
                continue

        # RESUMO FINAL
        print(f'[SISBAJUD] ✅ Filtradas {len(series_validas)} séries válidas de {len(series_bruto)}')
        if series_validas:
            print('[SISBAJUD] 📋 Séries válidas:')
            for s in series_validas:
                print(f'  - ID: {s["id_serie"]}, Data: {s["data_conclusao_text"]}, Situação: {s["situacao"]}')
            
            total_bloqueado = sum(s['valor_bloqueado'] for s in series_validas)
            print(f'[SISBAJUD] 📊 Total bloqueado das séries válidas: R$ {total_bloqueado:.2f}')

        return series_validas

    except Exception as e:
        print(f'[SISBAJUD] ❌ Erro ao filtrar séries: {e}')
        import traceback
        traceback.print_exc()
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
            print(f"[SISBAJUD] Navegando para detalhes da série {id_serie}")

        # Navegar diretamente para a URL da série
        url_serie = f"https://sisbajud.cnj.jus.br/teimosinha/{id_serie}/detalhes"
        driver.get(url_serie)
        time.sleep(3)  # Aguardar carregamento da página

        # Verificar se chegou na página correta
        if f"/{id_serie}/detalhes" not in driver.current_url:
            if log:
                print(f"[SISBAJUD] ❌ URL atual não corresponde à série: {driver.current_url}")
            return []

        if log:
            print(f"[SISBAJUD] ✅ Navegação direta bem-sucedida para série {id_serie}")

        # Aguardar a tabela de ordens carregar
        time.sleep(2)

        # Extrair ordens da série
        from ..ordens import _extrair_ordens_da_serie
        ordens = _extrair_ordens_da_serie(driver, log)
        if log:
            print(f"[SISBAJUD] ✅ {len(ordens)} ordens extraídas da série {id_serie}")

        return ordens

    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro na navegação para série {serie.get('id_serie', 'unknown')}: {str(e)}")
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
                    print(f"[SISBAJUD] Executado encontrado via expansion-panel: {header.text.strip()}")
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
                            print(f"[SISBAJUD] Executado encontrado via header: {nome}")
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
                        print(f"[SISBAJUD] Executado encontrado via card: {text}")
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
                        print(f"[SISBAJUD] Executado encontrado via label: {text}")
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
                        print(f"[SISBAJUD] Executado encontrado via URL: {nome}")
                    return nome
        except Exception as e:
            _ = e

        if log:
            print("[SISBAJUD] ⚠️ Nome do executado não identificado, usando placeholder")
        return "Executado"
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ⚠️ Erro ao extrair nome do executado: {e}")
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
            print(f'[SISBAJUD] Processando {len(series_validas)} séries...')

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
                print(f'[SISBAJUD] >>> Processando série {idx_serie}/{len(series_validas)}: {serie["id_serie"]}')

            try:
                # 1. Navegar para detalhes da série e extrair ordens
                ordens = _navegar_e_extrair_ordens_serie(driver, serie, log)
                if not ordens:
                    if log:
                        print(f'[SISBAJUD] ⚠️ Nenhuma ordem extraída da série {serie["id_serie"]}')
                    # Série sem ordens - voltar para lista principal
                    from ..navigation import _voltar_para_lista_principal
                    _voltar_para_lista_principal(driver, log)
                    continue

                # 1.5 Extrair nome do executado (após navegar)
                nome_executado = _extrair_nome_executado_serie(driver, log)
                if log:
                    print(f'[SISBAJUD] Executado identificado: {nome_executado}')

                # 2. Identificar ordens com bloqueio
                from ..ordens import _identificar_ordens_com_bloqueio
                valor_bloqueado = float(serie.get('valor_bloqueado', 0))
                ordens_bloqueadas = _identificar_ordens_com_bloqueio(ordens, valor_bloqueado, log)

                if not ordens_bloqueadas:
                    if log:
                        print(f'[SISBAJUD] ⚠️ Nenhuma ordem com bloqueio encontrada na série {serie["id_serie"]}, voltando para lista de séries')
                    # Série sem bloqueio - voltar para lista principal
                    from ..navigation import _voltar_para_lista_principal
                    _voltar_para_lista_principal(driver, log)
                    resultado['series_processadas'] += 1
                    continue
                
                # Ordenar ordens por valor (decrescente) para otimizar transferências
                if usar_estrategia_parcial:
                    ordens_bloqueadas_ordenadas = sorted(ordens_bloqueadas, key=lambda o: float(o.get('valor_bloquear', 0)), reverse=True)
                    if log:
                        print(f'[SISBAJUD] 📊 {len(ordens_bloqueadas)} ordens ordenadas por valor (maior primeiro)')
                    ordens_bloqueadas = ordens_bloqueadas_ordenadas

                # 3. Processar cada ordem com bloqueio COM estratégia
                total_ordens_serie = len(ordens_bloqueadas)
                for idx_ordem, ordem in enumerate(ordens_bloqueadas, 1):
                    sequencial_ordem = ordem.get('sequencial')
                    situacao_ordem = ordem.get('situacao', '')
                    
                    if log:
                        print(f'\n[SISBAJUD] >>> Processando ordem {idx_ordem}/{total_ordens_serie} da série {serie["id_serie"]}')
                        print(f'[SISBAJUD] Ordem: {sequencial_ordem}, Protocolo: {ordem.get("protocolo", "N/A")}')
                    
                    # Verificar se ordem já está "Respondida com minuta"
                    # Abrir apenas para extrair discriminação (nunca terá erro aqui)
                    if "Respondida com minuta" in situacao_ordem:
                        if log:
                            print(f'[SISBAJUD] Ordem {sequencial_ordem} já processada (Respondida com minuta)')
                        
                        # Abrir para extrair dados se for fluxo POSITIVO
                        if tipo_fluxo == 'POSITIVO':
                            if log:
                                print(f'[SISBAJUD]    📊 Extraindo dados da ordem já processada...')
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
                                        print(f'[SISBAJUD]    ✅ Dados extraídos e agrupados')
                                
                            except Exception as e:
                                if log:
                                    print(f'[SISBAJUD]    ⚠️ Erro ao extrair dados: {e}')
                        
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
                                    print(f'[SISBAJUD]    ⚙️  Ordem {sequencial_ordem}: TRANSFERÊNCIA PARCIAL (R$ {valor_restante:.2f} de R$ {valor_ordem:.2f})')
                    
                    try:
                        # Executar ação conforme estratégia
                        if acao in ['TRANSFERIR', 'TRANSFERIR_PARCIAL']:
                            if log and usar_estrategia_parcial and acao == 'TRANSFERIR':
                                print(f'[SISBAJUD]    ▶️  Ordem {sequencial_ordem}: TRANSFERIR (R$ {valor_ordem:.2f})')
                            
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
                                    erro = f'⚠️ ERRO DE BLOQUEIO: Ordem {sequencial_ordem} - {rel.get("erro_msg", "erro desconhecido")}'
                                    if log:
                                        print(f'[SISBAJUD]   {erro}')
                                    resultado['erros'].append(erro)
                                    
                                    # Adicionar à lista de erros de bloqueio
                                    erro_item = {
                                        'protocolo': rel['protocolo'],
                                        'valor_esperado': rel['valor_esperado'],
                                        'erro_msg': rel.get('erro_msg', 'Erro desconhecido')
                                    }
                                    resultado['detalhes']['dados_bloqueios']['ordens_com_erro_bloqueio'].append(erro_item)
                                    if log:
                                        print(f'[SISBAJUD]   📝 Erro adicionado à lista: {erro_item}')
                                    
                                    # CONTINUAR para próxima ordem (não parar tudo)
                                    continue
                                
                                # Se não é erro de bloqueio, é erro real - PARAR TUDO
                                erro = f'❌ CRÍTICO: Impossível processar ordem {sequencial_ordem}'
                                if log:
                                    print(f'[SISBAJUD]   {erro}')
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
                                    print(f'[SISBAJUD]   ✅ Ordem {sequencial_ordem} processada com sucesso')
                                
                                # ===== EXTRAIR DADOS IMEDIATAMENTE APÓS PROCESSAMENTO (ANTES DE VOLTAR) =====
                                if tipo_fluxo == 'POSITIVO':
                                    protocolo_ordem = ordem.get('protocolo', 'N/A')
                                    if log:
                                        print(f'[SISBAJUD] 📊 Extraindo dados dos bloqueios da página (Protocolo: {protocolo_ordem})...')
                                    
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
                                                print(f'[SISBAJUD]   ✅ Dados extraídos da ordem {sequencial_ordem}')
                                        else:
                                            if log:
                                                print(f'[SISBAJUD]   ⚠️ Nenhum dado de bloqueio extraído da ordem {sequencial_ordem}')
                                                
                                    except Exception as e_dados:
                                        if log:
                                            print(f'[SISBAJUD]   ⚠️ Erro ao extrair dados para relatório: {e_dados}')
                            
                            # Se chegou aqui, processamento foi sucesso (não teria retornado antes)
                        
                        elif acao == 'DESBLOQUEAR':
                            if log:
                                print(f'[SISBAJUD]    Ordem {sequencial_ordem}: DESBLOQUEAR (R$ {valor_ordem:.2f})')
                            
                            from ..processamento import _processar_ordem
                            
                            # Processar ordem (sem retry automático - se falhar, para tudo)
                            sucesso_processamento = _processar_ordem(driver, ordem, 'DESBLOQUEIO', log)
                            
                            # CRÍTICO: Se falhou, PARAR TUDO
                            if not sucesso_processamento:
                                erro = f'CRÍTICO: Impossível desbloquear ordem {sequencial_ordem}'
                                if log:
                                    print(f'[SISBAJUD]   {erro}')
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
                                    print(f'[SISBAJUD]   ✅ Ordem {sequencial_ordem} desbloqueada com sucesso')
                            
                            # Se chegou aqui, processamento foi sucesso (não teria retornado antes)
                        
                        # ===== CRUCIAL: NAVEGAÇÃO APÓS PROCESSAR ORDEM COM SUCESSO =====
                        from ..navigation import _voltar_para_lista_ordens_serie, _voltar_para_lista_principal
                        if idx_ordem < total_ordens_serie:
                            # Ainda há mais ordens para processar nesta série
                            if log:
                                print(f'[SISBAJUD] Voltando para lista de ordens (mais {total_ordens_serie - idx_ordem} ordens restantes)...')
                            _voltar_para_lista_ordens_serie(driver, log)
                            
                            # Invalidar TODAS as referências de elementos após voltar da página
                            for ordem_restante in ordens_bloqueadas[idx_ordem:]:
                                if 'linha_el' in ordem_restante:
                                    ordem_restante['linha_el'] = None
                            if log:
                                print(f'[SISBAJUD] 🧹 Elementos invalidados após retorno (ordens restantes)')
                        else:
                            # Última ordem da série, voltar para lista de séries
                            if log:
                                print(f'[SISBAJUD] Última ordem da série {serie["id_serie"]}, voltando para lista de séries')
                            _voltar_para_lista_principal(driver, log)
                        
                    except Exception as e:
                        erro = f'Erro ao processar ordem {ordem["sequencial"]} da série {serie["id_serie"]}: {str(e)}'
                        if log:
                            print(f'[SISBAJUD] ❌ {erro}')
                        resultado['erros'].append(erro)
                        
                        # Tentar voltar para lista de ordens ou séries após erro
                        try:
                            from ..navigation import _voltar_para_lista_ordens_serie, _voltar_para_lista_principal
                            if idx_ordem < total_ordens_serie:
                                _voltar_para_lista_ordens_serie(driver, log)
                                # Invalidar elementos após erro e retorno
                                for ordem_restante in ordens_bloqueadas[idx_ordem:]:
                                    if 'linha_el' in ordem_restante:
                                        ordem_restante['linha_el'] = None
                            else:
                                _voltar_para_lista_principal(driver, log)
                        except Exception as nav_err:
                            _ = nav_err

                resultado['series_processadas'] += 1

            except Exception as e:
                erro = f'Erro na série {serie.get("id_serie", "unknown")}: {str(e)}'
                if log:
                    print(f'[SISBAJUD] ❌ {erro}')
                resultado['erros'].append(erro)
                
                # Tentar voltar para lista de séries após erro
                try:
                    from ..navigation import _voltar_para_lista_principal
                    _voltar_para_lista_principal(driver, log)
                except Exception as nav_err:
                    _ = nav_err
                continue

        if log:
            print(f'[SISBAJUD] ✅ Processamento concluído: {resultado["series_processadas"]} séries, {resultado["ordens_processadas"]} ordens')
            if usar_estrategia_parcial:
                print(f'[SISBAJUD]    💰 Total transferido: R$ {acumulado_transferido:.2f} de R$ {limite_execucao:.2f}')
                print(f'[SISBAJUD]    📊 Ordens transferidas: {len(resultado["detalhes"]["ordens_transferidas"])}')
                print(f'[SISBAJUD]    ⏭️  Ordem pendente: {1 if resultado["detalhes"]["ordem_pendente"] else 0}')
                print(f'[SISBAJUD]    🔓 Ordens desbloqueadas: {len(resultado["detalhes"]["ordens_desbloqueadas"])}')

        return resultado

    except Exception as e:
        if log:
            print(f'[SISBAJUD] ❌ Erro geral no processamento: {e}')
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
            print(f'[SISBAJUD] 🔍 Estratégia de bloqueio:')
            print(f'[SISBAJUD]    Valor da execução: R$ {valor_execucao:.2f}')
            print(f'[SISBAJUD]    Total bloqueado: R$ {total_bloqueado:.2f}')
        
        # 3. Decidir estratégia
        if total_bloqueado <= valor_execucao:
            if log:
                print(f'[SISBAJUD]    ✅ Estratégia: TRANSFERIR TUDO (bloqueado não excede execução)')
            return {
                'tipo': 'TRANSFERIR_TUDO',
                'valor_execucao': valor_execucao,
                'total_bloqueado': total_bloqueado,
                'acumulado_limite': valor_execucao
            }
        
        # 4. Total excede - usar transferência parcial
        if log:
            excesso = total_bloqueado - valor_execucao
            print(f'[SISBAJUD]    ⚠️ Estratégia: TRANSFERIR PARCIAL (bloqueado excede em R$ {excesso:.2f})')
            print(f'[SISBAJUD]    📋 Será: transferir até limite, pular 1 ordem, desbloquear restantes')
        
        return {
            'tipo': 'TRANSFERIR_PARCIAL',
            'valor_execucao': valor_execucao,
            'total_bloqueado': total_bloqueado,
            'acumulado_limite': valor_execucao
        }
        
    except Exception as e:
        if log:
            print(f'[SISBAJUD] ❌ Erro ao calcular estratégia: {e}')
        # Em caso de erro, usar estratégia padrão
        return {
            'tipo': 'TRANSFERIR_TUDO',
            'valor_execucao': 0.0,
            'total_bloqueado': 0.0,
            'acumulado_limite': 0.0
        }
