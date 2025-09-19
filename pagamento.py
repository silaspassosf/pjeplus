"""
Módulo para processamento de pagamentos e comparação com alvarás.
Extraído de listaexec2.py para modularização.
"""

import re
import json
import os
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from alvara_core import ler_alvaras_arquivo, atualizar_status_alvara, salvar_alvaras_arquivo
from alvara_utils import converter_valor_para_float


def processar_pagamentos(driver, alvaras_processados, log=True):
    """
    Analisa a listagem de pagamentos e compara com os alvarás logados.
    Só deve ser chamada após processar todos os alvarás corretamente.
    
    Args:
        driver: WebDriver do Selenium
        alvaras_processados: Lista de alvarás que foram processados
        log: Se deve exibir logs
    """
    def registro(alvara, log=True):
        """
        Função placeholder para registrar alvarás sem correspondência.
        
        Args:
            alvara: Dados do alvará
            log: Se deve exibir logs
        """
        try:
            if log:
                print(f'[REGISTRO] Processando alvará sem correspondência: {alvara.get("data_expedicao")} - {alvara.get("valor")}')
                print(f'[REGISTRO] Beneficiário: {alvara.get("beneficiario")}')
                print('[REGISTRO] TODO: Implementar lógica específica para registros sem correspondência')
            
            # TODO: Implementar lógica específica aqui
            # Por exemplo: enviar notificação, criar tarefa, etc.
            
        except Exception as e:
            if log:
                print(f'[REGISTRO][ERRO] Erro na função registro: {e}')
    
    def analisar_listagem_pagamentos(driver, log=True):
        """
        Analisa a listagem de pagamentos e extrai dados relevantes.
        
        Args:
            driver: WebDriver do Selenium
            log: Se deve exibir logs
            
        Returns:
            list: Lista de pagamentos encontrados
        """
        try:
            pagamentos = []
            
            # Buscar todos os mat-card-content com classe corpo
            cards_pagamento = driver.find_elements(By.CSS_SELECTOR, 'mat-card-content.mat-card-content.corpo')
            
            if log:
                print(f'[PAGAMENTO] Encontrados {len(cards_pagamento)} cards de pagamento')
            
            for index, card in enumerate(cards_pagamento):
                try:
                    pagamento_data = extrair_dados_pagamento(card, index, log)
                    if pagamento_data:
                        pagamentos.append(pagamento_data)
                        if log:
                            print(f'[PAGAMENTO] Pagamento {index+1}: {pagamento_data["data_pagamento"]} - {pagamento_data["credito_demandante"]}')
                    
                except Exception as e:
                    if log:
                        print(f'[PAGAMENTO][ERRO] Erro ao processar card {index}: {e}')
                    continue
            
            return pagamentos
            
        except Exception as e:
            if log:
                print(f'[PAGAMENTO][ERRO] Erro na análise da listagem: {e}')
            return []
    
    def extrair_dados_pagamento(card, index, log=True):
        """
        Extrai dados específicos de um card de pagamento.
        
        Args:
            card: Elemento do card de pagamento
            index: Índice do card
            log: Se deve exibir logs
            
        Returns:
            dict: Dados do pagamento ou None
        """
        try:
            dados_pagamento = {
                'index': index,
                'data_pagamento': None,
                'credito_demandante': None,
                'valor_total': None
            }
            
            # Buscar todos os dl dentro do card
            dls = card.find_elements(By.CSS_SELECTOR, 'dl.dl-rubrica')
            
            for dl in dls:
                try:
                    dt = dl.find_element(By.CSS_SELECTOR, 'dt.dt-rubrica')
                    dd = dl.find_element(By.CSS_SELECTOR, 'dd.dd-rubrica')
                    
                    campo = dt.text.strip()
                    valor = dd.text.strip()
                    
                    if campo == 'Data do Pagamento':
                        dados_pagamento['data_pagamento'] = valor
                    elif campo == 'Crédito do demandante':
                        dados_pagamento['credito_demandante'] = valor
                        # Extrair valor numérico
                        dados_pagamento['valor_total'] = converter_valor_pagamento_para_float(valor)
                
                except Exception as e:
                    continue
            
            # Verificar se conseguiu extrair dados essenciais
            if dados_pagamento['data_pagamento'] and dados_pagamento['credito_demandante']:
                return dados_pagamento
            else:
                if log:
                    print(f'[PAGAMENTO][AVISO] Dados insuficientes no card {index}')
                return None
                
        except Exception as e:
            if log:
                print(f'[PAGAMENTO][ERRO] Erro ao extrair dados do card {index}: {e}')
            return None
    
    def converter_valor_pagamento_para_float(valor_str):
        """Converte valor de pagamento para float"""
        try:
            # Remove R$, &nbsp;, espaços e converte
            valor_clean = valor_str.replace('R$', '').replace('&nbsp;', '').replace(' ', '')
            valor_clean = valor_clean.replace('.', '').replace(',', '.')
            return float(valor_clean)
        except:
            return 0.0
    
    def comparar_alvaras_com_pagamentos(alvaras_processados, pagamentos, log=True):
        """
        Compara cada alvará com os pagamentos encontrados.
        
        Args:
            alvaras_processados: Lista de alvarás processados
            pagamentos: Lista de pagamentos encontrados
            log: Se deve exibir logs
        """
        try:
            if log:
                print(f'[PAGAMENTO] Comparando {len(alvaras_processados)} alvarás com {len(pagamentos)} pagamentos')
            
            # Ler alvaras existentes do arquivo
            alvaras_arquivo = ler_alvaras_arquivo(log)
            
            for alvara in alvaras_processados:
                encontrou_correspondencia = False
                
                # Dados do alvará para comparação
                alvara_data = alvara.get('data_expedicao', '')
                alvara_valor = alvara.get('valor', '')
                alvara_valor_float = converter_valor_para_float(alvara_valor.replace('R$ ', '').replace('.', '').replace(',', '.')) if alvara_valor else 0.0
                
                if log:
                    print(f'[PAGAMENTO] Analisando alvará: {alvara_data} - {alvara_valor}')
                
                # Comparar com cada pagamento
                for pagamento in pagamentos:
                    pagamento_data = pagamento.get('data_pagamento', '')
                    pagamento_valor = pagamento.get('valor_total', 0.0)
                    
                    # Verificar correspondência
                    if verificar_correspondencia_data_valor(alvara_data, alvara_valor_float, pagamento_data, pagamento_valor, log):
                        encontrou_correspondencia = True
                        if log:
                            print(f'[PAGAMENTO] ✅ Correspondência encontrada: Alvará {alvara_data}/{alvara_valor} <-> Pagamento {pagamento_data}/{pagamento["credito_demandante"]}')
                    
                        # Atualizar alvará no arquivo como REGISTRADO
                        atualizar_status_alvara(alvaras_arquivo, alvara, 'ALVARA REGISTRADO', log)
                        break
                    
                # Se não encontrou correspondência
                if not encontrou_correspondencia:
                    if log:
                        print(f'[PAGAMENTO] ❌ Nenhuma correspondência encontrada para alvará: {alvara_data} - {alvara_valor}')
                    
                    # Atualizar alvará no arquivo como SEM REGISTRO
                    atualizar_status_alvara(alvaras_arquivo, alvara, 'SEM REGISTRO', log)
                    
                    # Função registro será chamada dentro da lógica de pagamento
                    registro(alvara, log)
            
            # Salvar arquivo atualizado
            salvar_alvaras_arquivo(alvaras_arquivo, log)
            
        except Exception as e:
            if log:
                print(f'[PAGAMENTO][ERRO] Erro na comparação: {e}')
    
    def verificar_correspondencia_data_valor(alvara_data, alvara_valor, pagamento_data, pagamento_valor, log=True):
        """
        Verifica se há correspondência entre alvará e pagamento.
        Critérios: data igual ou diferença máxima de 5 dias, valor igual ou diferença máxima de R$ 300.
        
        Args:
            alvara_data: Data do alvará (formato dd/mm/aaaa)
            alvara_valor: Valor do alvará (float)
            pagamento_data: Data do pagamento (formato dd/mm/aaaa)
            pagamento_valor: Valor do pagamento (float)
            log: Se deve exibir logs
            
        Returns:
            bool: True se houver correspondência
        """
        try:
            # Converter datas
            try:
                alvara_date = datetime.strptime(alvara_data, '%d/%m/%Y')
                pagamento_date = datetime.strptime(pagamento_data, '%d/%m/%Y')
                
                # Calcular diferença em dias
                diferenca_dias = abs((alvara_date - pagamento_date).days)
                
            except:
                # Se não conseguir converter, considerar como não correspondente
                if log:
                    print(f'[PAGAMENTO][AVISO] Erro ao converter datas: {alvara_data} / {pagamento_data}')
                return False
            
            # Calcular diferença de valores
            diferenca_valor = abs(alvara_valor - pagamento_valor)
            
            # Verificar critérios
            data_ok = diferenca_dias <= 5
            valor_ok = diferenca_valor <= 300.0
            
            if log and (data_ok or valor_ok):
                print(f'[PAGAMENTO] Comparação: Data {diferenca_dias} dias, Valor R$ {diferenca_valor:.2f}')
            
            return data_ok and valor_ok
            
        except Exception as e:
            if log:
                print(f'[PAGAMENTO][ERRO] Erro na verificação de correspondência: {e}')
            return False

    try:
        if log:
            print('[PAGAMENTO] Iniciando processo de verificação de pagamentos...')

        # A função agora assume que o driver JÁ ESTÁ na página de pagamentos
        
        # 1. Ler todos os alvarás do arquivo
        alvaras_do_arquivo = ler_alvaras_arquivo(log)
        if not alvaras_do_arquivo:
            if log:
                print('[PAGAMENTO] Nenhum alvará encontrado no arquivo alvaras.js para verificar.')
            return

        # 2. Analisar a listagem de pagamentos na página atual
        pagamentos_encontrados = analisar_listagem_pagamentos(driver, log)
        
        if pagamentos_encontrados:
            # 3. Comparar a lista completa de alvarás com os pagamentos
            comparar_alvaras_com_pagamentos(alvaras_do_arquivo, pagamentos_encontrados, log)
        else:
            if log:
                print('[PAGAMENTO] Nenhum pagamento encontrado na listagem. Marcando todos os alvarás como "SEM REGISTRO".')
            # Se não há pagamentos, processa todos os alvarás como "SEM REGISTRO"
            processar_alvaras_sem_registro(alvaras_do_arquivo, log)

    except Exception as e:
        if log:
            print(f'[PAGAMENTO][ERRO] Erro geral no processo de pagamento: {e}')
    
    finally:
        # --- RETORNO À ABA ORIGINAL ---
        try:
            if log:
                print('[PAGAMENTO] 🔄 Iniciando retorno à aba original...')
            
            # Obter todas as abas abertas
            todas_abas = driver.window_handles
            aba_atual = driver.current_window_handle
            
            if log:
                print(f'[PAGAMENTO] Total de abas abertas: {len(todas_abas)}')
                print(f'[PAGAMENTO] Aba atual: {driver.current_url}')
            
            # Procurar pela aba original (/detalhe)
            aba_original = None
            for aba in todas_abas:
                if aba != aba_atual:  # Não é a aba atual (pagamentos)
                    try:
                        driver.switch_to.window(aba)
                        if '/detalhe' in driver.current_url:
                            aba_original = aba
                            if log:
                                print(f'[PAGAMENTO] ✅ Aba original encontrada: {driver.current_url}')
                            break
                    except:
                        continue
            
            # Se encontrou a aba original, fechar a aba de pagamentos
            if aba_original:
                # Voltar para a aba de pagamentos para fechá-la
                driver.switch_to.window(aba_atual)
                if log:
                    print('[PAGAMENTO] 🗑️ Fechando aba de pagamentos...')
                driver.close()
                
                # Mudar para a aba original
                driver.switch_to.window(aba_original)
                if log:
                    print(f'[PAGAMENTO] ✅ Retornado à aba original: {driver.current_url}')
                    print('[PAGAMENTO] 🎯 Pronto para processar alvarás individuais!')
            else:
                if log:
                    print('[PAGAMENTO][AVISO] Aba original não encontrada, permanecendo na aba atual')
                    
        except Exception as e:
            if log:
                print(f'[PAGAMENTO][ERRO] Erro ao retornar à aba original: {e}')
                print('[PAGAMENTO] Continuando na aba atual...')


def processar_alvaras_sem_registro(alvaras_processados, log=True):
    """
    Processa alvarás quando não há pagamentos na listagem.
    
    Args:
        alvaras_processados: Lista de alvarás que foram processados
        log: Se deve exibir logs
    """
    def registro(alvara, log=True):
        """
        Função placeholder para registrar alvarás sem correspondência.
        
        Args:
            alvara: Dados do alvará
            log: Se deve exibir logs
        """
        try:
            if log:
                print(f'[REGISTRO] Processando alvará sem correspondência: {alvara.get("data_expedicao")} - {alvara.get("valor")}')
                print(f'[REGISTRO] Beneficiário: {alvara.get("beneficiario")}')
                print('[REGISTRO] TODO: Implementar lógica específica para registros sem correspondência')
            
            # TODO: Implementar lógica específica aqui
            # Por exemplo: enviar notificação, criar tarefa, etc.
            
        except Exception as e:
            if log:
                print(f'[REGISTRO][ERRO] Erro na função registro: {e}')
    
    try:
        if log:
            print('[PAGAMENTO] Processando alvarás sem registro de pagamentos...')
        
        alvaras_arquivo = ler_alvaras_arquivo(log)
        
        for alvara in alvaras_processados:
            # Atualizar como SEM REGISTRO
            atualizar_status_alvara(alvaras_arquivo, alvara, 'SEM REGISTRO', log)
            
            # Chamar a função registro para cada um
            registro(alvara, log)
        
        # Salvar arquivo atualizado
        salvar_alvaras_arquivo(alvaras_arquivo, log)
        
    except Exception as e:
        if log:
            print(f'[PAGAMENTO][ERRO] Erro ao processar alvaras sem registro: {e}')


def verificar_alvaras_na_timeline(driver, itens_alvo, log=True):
    """
    Função prévia para identificar se há alvarás na timeline.
    Retorna lista de alvarás encontrados sem processá-los.
    
    Args:
        driver: WebDriver do Selenium
        itens_alvo: Lista de itens a serem buscados na timeline
        log: Se deve exibir logs
        
    Returns:
        list: Lista de alvarás identificados na timeline
    """
    try:
        if log:
            print('[LISTA-EXEC] Verificando presença de alvarás na timeline...')
        
        # BUSCA EFICIENTE: Pegar TODOS os itens da timeline de uma vez
        seletores_timeline = [
            'li.tl-item-container',
            '.tl-data .tl-item-container', 
            '.timeline-item'
        ]
        
        itens = []
        for seletor in seletores_timeline:
            try:
                itens = driver.find_elements(By.CSS_SELECTOR, seletor)
                if itens and len(itens) > 0:
                    break
            except Exception as e:
                continue
        
        if not itens:
            if log:
                print('[LISTA-EXEC] ❌ Nenhum item encontrado na timeline')
            return []
        
        # Buscar especificamente por alvarás
        alvaras_detectados = []
        item_alvara = next((item for item in itens_alvo if item['nome'] == 'Alvará'), None)
        
        if not item_alvara:
            return []
        
        for index, item in enumerate(itens):
            try:
                # Buscar link do documento principal 
                links = item.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                if not links:
                    continue
                    
                link = links[0]
                texto_doc = link.text.strip().lower()
                
                # Verificar se é alvará
                encontrado = any(termo in texto_doc for termo in item_alvara['termos'])
                if encontrado:
                    # EXCEÇÃO ESPECÍFICA: Se contém "expedição", não é alvará válido
                    if 'expedição' in texto_doc:
                        if log:
                            print(f'[LISTA-EXEC] ⚠️ Alvará com "expedição" detectado - não será processado: {link.text.strip()}')
                        continue
                    
                    # Adicionar à lista de alvarás detectados
                    from alvara_utils import extrair_data_item
                    data = extrair_data_item(item)
                    alvara_detectado = {
                        'index': index,
                        'item': item,
                        'link': link,
                        'texto_doc': texto_doc,
                        'data': data,
                        'uid': f"alvara-{index}"
                    }
                    alvaras_detectados.append(alvara_detectado)
                    
                    if log:
                        print(f'[LISTA-EXEC] 🎯 Alvará detectado: {link.text.strip()} ({data})')
                    
            except Exception as e:
                if log:
                    print(f'[LISTA-EXEC][ERRO] Erro ao verificar item {index}: {e}')
                continue
        
        if log:
            print(f'[LISTA-EXEC] ✅ Verificação concluída. {len(alvaras_detectados)} alvarás detectados.')
        
        return alvaras_detectados
        
    except Exception as e:
        if log:
            print(f'[LISTA-EXEC][ERRO] Erro na verificação de alvarás: {e}')
        return []
