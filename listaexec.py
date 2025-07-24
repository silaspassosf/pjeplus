"""
Script principal para listar medidas executórias no PJe.
Versão refatorada de listaexec2.py dividida em módulos.

Uso: from listaexec import listaexec
     resultado = listaexec(driver, log=True)
"""

import time
from selenium.webdriver.common.by import By

# Importar funções dos módulos
from listaexec_modules.buscar_medidas import buscar_medidas_executorias
from listaexec_modules.alvara_core import processar_alvara
from listaexec_modules.alvara_utils import converter_valor_para_float
from listaexec_modules.gigs_utils import (
    navegar_para_pagamentos, analisar_listagem_pagamentos, 
    verificar_correspondencia_data_valor, tratar_timeline, gerar_gigs_final
)


def listaexec(driver, log=True):
    """
    Lista medidas executórias realizadas nos autos do PJe.
    Ao encontrar alvarás, extrai dados detalhados e salva em alvaras.js
    
    Args:
        driver: WebDriver do Selenium
        log: Se deve exibir logs (default: True)
    
    Returns:
        list: Lista de medidas executórias encontradas
    """

    try:
        medidas = []
        alvaras_encontrados = []
        
        # ESTRUTURAS PARA GIGS FINAL
        dados_gigs_final = {
            'alvaras_sem_registro': [],  # {'id_timeline': 'xxx', 'data': 'dd/mm/yyyy', 'valor': 'R$ xxx,xx'}
            'cnib_anexos': [],           # ['id1', 'id2', 'id3']
            'serasa_anexos': [],         # ['id1', 'id2', 'id3']
            'sobrestamentos': []         # {'id_timeline': 'xxx', 'data': 'dd/mm/yyyy'}
        }

        # Definição dos itens a serem buscados
        itens_alvo = [
            {'nome': 'Alvará', 'termos': ['alvará', 'alvara'], 'tipo': 'documento_individual'},
            {'nome': 'Certidão de oficial de justiça', 'termos': ['certidão de oficial de justiça', 'certidao de oficial de justica', 'oficial de justiça', 'oficial de justica'], 'tipo': 'documento_com_anexos', 'anexos_interesse': ['cnib', 'serasa']},
            {'nome': 'Certidão de pesquisa patrimonial', 'termos': ['certidão de pesquisa patrimonial', 'certidao de pesquisa patrimonial', 'pesquisa patrimonial'], 'tipo': 'documento_com_anexos', 'anexos_interesse': ['cnib', 'serasa']},
            {'nome': 'Serasa', 'termos': ['serasa'], 'tipo': 'documento_condicional_gigs'},
            {'nome': 'Sobrestamento', 'termos': ['sobrestamento'], 'tipo': 'documento_deteccao'}
        ]
        
        # --- FASE 1: Análise da Timeline ---
        if log:
            print('[LISTA-EXEC] Iniciando Fase 1: Análise da Timeline...')
        
        documentos_encontrados = tratar_timeline(driver, itens_alvo, log)
        
        # --- FASE 1.5: Processamento dos dados coletados em Python ---
        if log:
            print('[LISTA-EXEC] Iniciando Fase 1.5: Processamento dos dados em Python...')

        # Listas para priorização
        alvaras_para_processar = []
        certidoes_com_anexos = []
        serasa_timeline = []
        sobrestamentos_detectados = []

        # 1. Catalogar todos os itens encontrados
        for doc in documentos_encontrados:
            if doc['nome'] == 'Alvará':
                alvaras_para_processar.append(doc)
                alvaras_encontrados.append(doc)
            elif doc['nome'] == 'Sobrestamento':
                sobrestamentos_detectados.append(doc)
            elif 'Certidão' in doc['nome'] and doc['tem_anexos']:
                certidoes_com_anexos.append(doc)
            elif doc['nome'] == 'Serasa':
                serasa_timeline.append(doc)

        # --- FLUXO CORRIGIDO: Análise de pagamentos primeiro ---
        pagamentos_encontrados = []
        alvaras_processados_individuais = []
        
        if alvaras_para_processar:
            if log:
                print(f'[LISTA-EXEC] 📋 {len(alvaras_para_processar)} alvarás encontrados. Iniciando análise de pagamentos primeiro...')
            
            # Armazenar URL original
            url_original = driver.current_url
            
            try:
                # Navegar para pagamentos e coletar dados
                if navegar_para_pagamentos(driver, log):
                    pagamentos_encontrados = analisar_listagem_pagamentos(driver, log)
                    if log:
                        print(f'[LISTA-EXEC] ✅ {len(pagamentos_encontrados)} pagamentos coletados')
                    
                    # Fechar aba de pagamentos e voltar à aba original
                    try:
                        todas_abas = driver.window_handles
                        if len(todas_abas) > 1:
                            driver.close()
                            driver.switch_to.window(todas_abas[0])
                        else:
                            driver.get(url_original)
                        
                        time.sleep(2)
                        if log:
                            print(f'[LISTA-EXEC] ✅ Retornado à aba original: {driver.current_url}')
                    except Exception as e:
                        if log:
                            print(f'[LISTA-EXEC][ERRO] Erro ao retornar à aba original: {e}')
                        driver.get(url_original)
                        time.sleep(2)
                
            except Exception as e:
                if log:
                    print(f'[LISTA-EXEC][ERRO] Erro na análise de pagamentos: {e}')
        
        # 2. Processar alvarás individualmente, fazendo comparação com pagamentos
        for alvara_doc in alvaras_para_processar:
            try:
                if log:
                    print(f'[LISTA-EXEC] 📋 Processando alvará: {alvara_doc["texto_original"][:100]}...')
                
                # Buscar elementos DOM reais do alvará na timeline
                seletores_timeline = ['li.tl-item-container', '.tl-data .tl-item-container', '.timeline-item']
                
                itens_timeline = []
                for seletor in seletores_timeline:
                    try:
                        itens_timeline = driver.find_elements(By.CSS_SELECTOR, seletor)
                        if itens_timeline and len(itens_timeline) > 0:
                            break
                    except:
                        continue
                
                # Encontrar o item correto na timeline pelo índice
                if alvara_doc['index'] < len(itens_timeline):
                    item_alvara = itens_timeline[alvara_doc['index']]
                    
                    # Buscar link do documento
                    links = item_alvara.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    if links:
                        link_alvara = links[0]
                        data_alvara = alvara_doc['data']
                        
                        # PROCESSAR O ALVARÁ INDIVIDUALMENTE
                        resultado_alvara = processar_alvara(driver, item_alvara, link_alvara, data_alvara, log)
                        
                        if resultado_alvara:
                            # Extrair dados para comparação
                            alvara_data = resultado_alvara.get('data_expedicao', '')
                            alvara_valor_str = resultado_alvara.get('valor', '')
                            alvara_valor = converter_valor_para_float(alvara_valor_str.replace('R$ ', '').replace('.', '').replace(',', '.')) if alvara_valor_str else 0.0
                            
                            # Comparar com pagamentos coletados
                            encontrou_correspondencia = False
                            for pagamento in pagamentos_encontrados:
                                pagamento_data = pagamento.get('data_pagamento', '')
                                pagamento_valor = pagamento.get('valor_total', 0.0)
                                
                                if verificar_correspondencia_data_valor(alvara_data, alvara_valor, pagamento_data, pagamento_valor, log):
                                    encontrou_correspondencia = True
                                    if log:
                                        print(f'[LISTA-EXEC] ✅ Alvará JÁ REGISTRADO: {alvara_data} - {alvara_valor_str}')
                                    break
                            
                            # Definir status e adicionar ao GIGS se necessário
                            if not encontrou_correspondencia:
                                if log:
                                    print(f'[LISTA-EXEC] ❌ Alvará SEM REGISTRO: {alvara_data} - {alvara_valor_str}')
                                
                                # Adicionar ao GIGS final
                                alvara_gigs = {
                                    'id': alvara_doc.get('id_timeline', ''),
                                    'data': alvara_data,
                                    'valor': alvara_valor_str
                                }
                                dados_gigs_final['alvaras_sem_registro'].append(alvara_gigs)
                            
                            # Armazenar alvará processado
                            alvaras_processados_individuais.append(resultado_alvara)
                            
                        else:
                            if log:
                                print(f'[LISTA-EXEC] ❌ Falha ao processar alvará: {alvara_doc["texto_original"][:50]}...')
                    else:
                        if log:
                            print(f'[LISTA-EXEC] ❌ Link não encontrado para alvará: {alvara_doc["texto_original"][:50]}...')
                else:
                    if log:
                        print(f'[LISTA-EXEC] ❌ Índice inválido para alvará: {alvara_doc["index"]} (total: {len(itens_timeline)})')
                
            except Exception as e:
                if log:
                    print(f'[LISTA-EXEC][ERRO] Erro ao processar alvará: {e}')
                continue

        # Prioridade 2: Sobrestamentos
        for sobrestamento in sobrestamentos_detectados:
            dados_gigs_final['sobrestamentos'].append({
                'id': sobrestamento['id_timeline'] or f"sobrestamento-{sobrestamento['index']}",
                'data': sobrestamento['data']
            })

        # Prioridade 3: Certidões com Anexos (CNIB/SERASA)
        for certidao in certidoes_com_anexos:
            dados_gigs_final['cnib_anexos'].append(certidao['id_timeline'] or f"certidao-{certidao['index']}") 

        # Prioridade 4: SERASA da timeline (se não houver SERASA de anexos)
        if not dados_gigs_final['serasa_anexos']:
            for serasa in serasa_timeline:
                if log:
                    print(f"[LISTA-EXEC] SERASA da timeline (ID: {serasa['id_timeline']}) seria processado aqui.")

        # --- FASE 3: Geração do GIGS Final ---
        if log:
            print('[LISTA-EXEC] Iniciando Fase 3: Geração do GIGS Final...')
        
        # Verificar se há dados relevantes para o GIGS
        tem_dados_gigs = (
            dados_gigs_final['alvaras_sem_registro'] or 
            dados_gigs_final['cnib_anexos'] or 
            dados_gigs_final['serasa_anexos'] or 
            dados_gigs_final['sobrestamentos']
        )
        
        if tem_dados_gigs:
            gerar_gigs_final(driver, dados_gigs_final, log)
        else:
            if log:
                print('[LISTA-EXEC] Nenhum dado relevante encontrado para o GIGS final.')

        if log:
            print(f'[LISTA-EXEC] Análise da timeline concluída. {len(medidas)} medidas encontradas.')
            
        return medidas
        
    except Exception as e:
        if log:
            print(f'[LISTA-EXEC][ERRO] Erro geral na função: {e}')
        return []
