import re
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from Fix import extrair_documento, criar_gigs
import time

def buscar_medidas_executorias(driver, log=True):
    """
    Busca medidas executórias na timeline do PJe, replicando a lógica do userscript Lista_Exec.user.js.
    Retorna uma lista de dicionários com as medidas encontradas.
    """
    seletores_timeline = [
        'li.tl-item-container',
        '.tl-data .tl-item-container',
        '.timeline-item'
    ]
    itens = []
    seletor_usado = ''
    for seletor in seletores_timeline:
        try:
            itens = driver.find_elements(By.CSS_SELECTOR, seletor)
            if itens and len(itens) > 0:
                seletor_usado = seletor
                if log:
                    print(f'[PY-LISTA-EXEC] Encontrados {len(itens)} itens com: {seletor}')
                    print('[PY-LISTA-EXEC] Primeiro item para debug:', itens[0].text[:200])
                break
        except Exception as e:
            if log:
                print(f'[PY-LISTA-EXEC][ERRO] Falha ao buscar seletor {seletor}: {e}')
    if not itens:
        if log:
            print('[PY-LISTA-EXEC] Nenhum item encontrado na timeline')
        return []
    medidas = []
    itens_alvo = [
        {'nome': 'Certidão de pesquisa patrimonial', 'termos': ['certidão de pesquisa patrimonial', 'certidao de pesquisa patrimonial', 'pesquisa patrimonial']},
        {'nome': 'SISBAJUD', 'termos': ['sisbajud']},
        {'nome': 'INFOJUD', 'termos': ['infojud']},
        {'nome': 'IRPF', 'termos': ['irpf', 'imposto de renda']},
        {'nome': 'DOI', 'termos': ['doi']},
        {'nome': 'Mandado de livre penhora', 'termos': ['mandado de livre penhora', 'mandado de penhora', 'livre penhora']},
        {'nome': 'Serasa', 'termos': ['serasa']},
        {'nome': 'CNIB', 'termos': ['cnib']},
        {'nome': 'CAGED', 'termos': ['caged']},
        {'nome': 'PREVJUD', 'termos': ['prevjud']},
        {'nome': 'SNIPER', 'termos': ['sniper']},
        {'nome': 'CCS', 'termos': ['ccs']},
        {'nome': 'CENSEC', 'termos': ['censec']}
    ]
    itens_somente_anexos = ['INFOJUD', 'IRPF', 'DOI']
    for index, item in enumerate(itens):
        try:
            # Buscar link do documento principal
            links = item.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            link = links[0] if links else None
            if link:
                texto_doc = link.text.strip().lower()
                # Data: buscar .tl-data dentro do item ou em irmãos anteriores
                data = None
                try:
                    data_elem = item.find_element(By.CSS_SELECTOR, '.tl-data[name="dataItemTimeline"]')
                except:
                    try:
                        data_elem = item.find_element(By.CSS_SELECTOR, '.tl-data')
                    except:
                        data_elem = None
                if not data_elem:
                    # Buscar em irmãos anteriores
                    try:
                        prev = item
                        for _ in range(5):
                            prev = driver.execute_script('return arguments[0].previousElementSibling', prev)
                            if not prev:
                                break
                            try:
                                data_elem = prev.find_element(By.CSS_SELECTOR, '.tl-data')
                                if data_elem:
                                    break
                            except:
                                continue
                    except:
                        pass
                if data_elem:
                    data_texto = data_elem.text.strip()
                    data = data_texto
                else:
                    data = 'Data não encontrada'
                for item_alvo in itens_alvo:
                    encontrado = any(termo in texto_doc for termo in item_alvo['termos'])
                    if encontrado:
                        if item_alvo['nome'] in itens_somente_anexos:
                            if log:
                                print(f'[PY-LISTA-EXEC] ⚠️ {item_alvo["nome"]} encontrado como documento principal - não será logado (deve ser apenas anexo)')
                            break
                        documento_id = f'doc-{index}'
                        medidas.append({
                            'nome': item_alvo['nome'],
                            'texto': link.text.strip(),
                            'data': data,
                            'id': documento_id,
                            'elemento': item,
                            'index': index,
                            'tipoItem': 'documento'
                        })
                        if log:
                            print(f'[PY-LISTA-EXEC] ✅ {item_alvo["nome"]}: {link.text.strip()} ({data})')
                        break
            # Buscar anexos
            btn_anexos = item.find_elements(By.CSS_SELECTOR, 'pje-timeline-anexos > div > div')
            if btn_anexos and link:
                texto_doc = link.text.strip().lower()
                data = data or 'Data não encontrada'
                if 'pesquisa patrimonial' in texto_doc:
                    anexo_id = f'anexos-{index}'
                    medidas.append({
                        'nome': 'Anexos da Pesquisa Patrimonial',
                        'texto': f'Anexos: {link.text.strip()}',
                        'data': data,
                        'id': anexo_id,
                        'elemento': item,
                        'index': index,
                        'tipoItem': 'anexos',
                        'documentoPai': link.text.strip()
                    })
                    if log:
                        print(f'[PY-LISTA-EXEC] ✅ Anexos de Pesquisa Patrimonial: {data}')
        except Exception as e:
            if log:
                print(f'[PY-LISTA-EXEC][ERRO] Erro ao processar item {index}: {e}')
    if log:
        print(f'[PY-LISTA-EXEC] Total de medidas encontradas: {len(medidas)}')
    return medidas

def salvar_alvaras_processados_no_arquivo(alvaras_processados, log=True):
    """
    Salva alvarás processados no arquivo alvaras.js para uso pela função pagamento.
    
    Args:
        alvaras_processados: Lista de alvarás processados com dados completos
        log: Se deve exibir logs
    """
    try:
        if not alvaras_processados:
            return
            
        # Converter alvarás processados para o formato do arquivo
        alvaras_para_arquivo = []
        
        for alvara in alvaras_processados:
            # Extrair dados essenciais do alvará processado
            alvara_data = {
                'data_expedicao': alvara.get('data_expedicao', ''),
                'valor': alvara.get('valor', ''),
                'beneficiario': alvara.get('beneficiario', ''),
                'tipo': alvara.get('tipo', 'Alvará'),
                'status': 'PENDENTE'  # Status inicial
            }
            alvaras_para_arquivo.append(alvara_data)
        
        # Salvar no arquivo alvaras.js
        try:
            with open('alvaras.js', 'w', encoding='utf-8') as f:
                f.write('var alvaras = ')
                f.write(str(alvaras_para_arquivo).replace("'", '"'))
                f.write(';')
                
            if log:
                print(f'[ARQUIVO] ✅ Salvos {len(alvaras_para_arquivo)} alvarás processados no arquivo alvaras.js')
                
        except Exception as e_arquivo:
            if log:
                print(f'[ARQUIVO][ERRO] Erro ao salvar arquivo alvaras.js: {e_arquivo}')
            
    except Exception as e:
        if log:
            print(f'[SALVAR-ALVARAS][ERRO] Erro geral: {e}')

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
    
    def alvara(driver, item, link, data, log=True):
        """
        Processa um alvará encontrado na timeline.
        Seleciona, extrai documento e salva dados em alvaras.js
        Ao final, se houver alvarás válidos, chama a função pagamento para análise.
        
        Args:
            driver: WebDriver do Selenium
            item: Elemento da timeline
            link: Link do documento
            data: Data do alvará
            log: Se deve exibir logs
        """
        def pagamento(driver, alvaras_processados, log=True):
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
                    from datetime import datetime
                    
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

            def registro(alvara, status, log=True):
                """
                Registra o status do alvará (com ou sem correspondência de pagamento).
                
                Args:
                    alvara: Dados do alvará
                    status: Status a ser registrado
                    log: Se deve exibir logs
                """
                try:
                    if log:
                        print(f'[REGISTRO] Registrando alvará: {alvara.get("data_expedicao")} - {status}')
                    
                    # Ler alvaras existentes do arquivo
                    alvaras_arquivo = ler_alvaras_arquivo(log)
                    
                    # Atualizar status do alvará no arquivo
                    atualizar_status_alvara(alvaras_arquivo, alvara, status, log)
                    
                    # Salvar arquivo atualizado
                    salvar_alvaras_arquivo(alvaras_arquivo, log)
                
                except Exception as e:
                    if log:
                        print(f'[REGISTRO][ERRO] Erro na função registro: {e}')
        
        try:
            # Importações necessárias
            import time
            import os
            import unicodedata
            
            if log:
                print(f'[ALVARA] Processando alvará: {link.text.strip()}')
            
            # a) Selecionar o documento
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
            driver.execute_script("arguments[0].click();", link)
            
            if log:
                print('[ALVARA] Documento selecionado, aguardando carregamento...')
            time.sleep(2)  # 2s é o bastante para clicar no botão de extração
            
            # b) Clicar no ícone de exportação para abrir modal
            try:
                # Primeiro verificar se já há modal aberto
                modais_existentes = driver.find_elements(By.CSS_SELECTOR, 'main#main-content.mat-dialog-content')
                if modais_existentes:
                    if log:
                        print('[ALVARA] ⚠️ Modal já existe, tentando fechar primeiro...')
                    
                    # Fechar modais existentes
                    for _ in range(3):  # Tentar até 3 vezes
                        try:
                            from selenium.webdriver.common.keys import Keys
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(0.5)
                        except:
                            pass
                    
                    # Verificar se ainda há modais
                    modais_ainda_existem = driver.find_elements(By.CSS_SELECTOR, 'main#main-content.mat-dialog-content')
                    if modais_ainda_existem:
                        if log:
                            print('[ALVARA] ⚠️ Ainda há modais abertos, aguardando...')
                        time.sleep(2)
                
                # Buscar o ícone de exportação (fas fa-file-export)
                icone_exportar = driver.find_element(By.CSS_SELECTOR, 'i.fas.fa-file-export.fa-lg')
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", icone_exportar)
                driver.execute_script("arguments[0].click();", icone_exportar)
                
                if log:
                    print('[ALVARA] Ícone de exportação clicado, aguardando modal aparecer...')
                
                # AGUARDAR ESPECIFICAMENTE O MODAL APARECER
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Aguardar o modal container aparecer
                modal_container = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-dialog-container.mat-dialog-container'))
                )
                
                if log:
                    print('[ALVARA] ✅ Modal container detectado, aguardando conteúdo...')
                
                # Aguardar o conteúdo específico aparecer
                modal_content = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'main#main-content.mat-dialog-content pre'))
                )
                
                if log:
                    print('[ALVARA] ✅ Conteúdo do modal carregado, extraindo texto...')
                
                # Aguardar um pouco mais para garantir que o texto foi carregado
                time.sleep(1)
                
                # Buscar conteúdo do modal
                texto = modal_content.text.strip()
                
                if texto:
                    if log:
                        print(f'[ALVARA] ✅ Texto extraído do modal: {len(texto)} caracteres')
                else:
                    if log:
                        print('[ALVARA][ERRO] Modal carregou mas não contém texto')
                    # Tentar fechar modal mesmo se vazio
                    try:
                        from selenium.webdriver.common.keys import Keys
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(1)
                    except:
                        pass
                    return None
                
                # Fechar o modal antes de prosseguir
                try:
                    from selenium.webdriver.common.keys import Keys
                    
                    if log:
                        print('[ALVARA] Fechando modal...')
                    
                    # Tentar várias formas de fechar o modal
                    modal_fechado = False
                    
                    # Método 1: Clicar no botão "Fechar" específico do modal (baseado no HTML fornecido)
                    try:
                        # Seletor específico para o botão Fechar no modal de texto extraído
                        btn_fechar = driver.find_element(By.CSS_SELECTOR, 'button[mat-dialog-close][mat-raised-button]')
                        driver.execute_script("arguments[0].click();", btn_fechar)
                        time.sleep(0.5)
                        
                        # Verificar se o modal foi fechado
                        modais_restantes = driver.find_elements(By.CSS_SELECTOR, 'mat-dialog-container.mat-dialog-container')
                        if not modais_restantes:
                            modal_fechado = True
                            if log:
                                print('[ALVARA] ✅ Modal fechado com botão Fechar')
                    except Exception as e_btn:
                        if log:
                            print(f'[ALVARA] Botão Fechar não encontrado: {e_btn}')
                    
                    # Método 2: Se botão não funcionou, tentar ESC
                    if not modal_fechado:
                        try:
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(0.5)
                            
                            # Verificar se o modal foi fechado
                            modais_restantes = driver.find_elements(By.CSS_SELECTOR, 'mat-dialog-container.mat-dialog-container')
                            if not modais_restantes:
                                modal_fechado = True
                                if log:
                                    print('[ALVARA] ✅ Modal fechado com ESC')
                        except Exception as e_esc:
                            if log:
                                print(f'[ALVARA] ESC falhou: {e_esc}')
                    
                    # Método 3: Se ainda não fechou, tentar clicar no X
                    if not modal_fechado:
                        try:
                            # Botão X no cabeçalho do modal
                            btn_x = driver.find_element(By.CSS_SELECTOR, 'button[mat-icon-button][mat-dialog-close] i.fas.fa-times')
                            driver.execute_script("arguments[0].parentElement.click();", btn_x)
                            time.sleep(0.5)
                            
                            modais_restantes = driver.find_elements(By.CSS_SELECTOR, 'mat-dialog-container.mat-dialog-container')
                            if not modais_restantes:
                                modal_fechado = True
                                if log:
                                    print('[ALVARA] ✅ Modal fechado com botão X')
                        except Exception as e_x:
                            if log:
                                print(f'[ALVARA] Botão X falhou: {e_x}')
                    
                    # Aguardar confirmação do fechamento do modal
                    if modal_fechado:
                        if log:
                            print('[ALVARA] ✅ Modal fechado com sucesso')
                        time.sleep(0.5)  # Espera breve para garantir
                    else:
                        if log:
                            print('[ALVARA] ⚠️ Não foi possível fechar o modal pelos métodos convencionais')
                        # Forçar fechamento com múltiplos ESCs
                        for _ in range(3):
                            try:
                                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                time.sleep(0.3)
                            except:
                                pass
                        time.sleep(1)
                
                except Exception as e_fechar:
                    if log:
                        print(f'[ALVARA][ERRO] Erro ao fechar modal: {e_fechar}')
                    # Fallback: forçar fechamento
                    try:
                        for _ in range(3):
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(0.3)
                    except:
                        pass
                
                except Exception as e_fechar:
                    if log:
                        print(f'[ALVARA][ERRO] Erro ao fechar modal: {e_fechar}')
                    time.sleep(2)  # Espera de segurança
                    
            except Exception as e_extrair:
                if log:
                    print(f'[ALVARA][ERRO] Erro ao extrair conteúdo do modal: {e_extrair}')
                return None
            
            # c) Extrair dados do alvará
            dados_alvara = extrair_dados_alvara(texto, data, log)
            
            if dados_alvara:
                # Verificar se beneficiário é igual ao autor do processo
                autor_processo = extrair_autor_processo(texto, log)
                
                if autor_processo and dados_alvara.get('beneficiario'):
                    # Normalizar nomes para comparação (remover acentos, converter para minúsculo)
                    beneficiario_norm = normalizar_nome(dados_alvara['beneficiario'])
                    autor_norm = normalizar_nome(autor_processo)
                    
                    if beneficiario_norm == autor_norm:
                        # Beneficiário = Autor: Salvar no arquivo
                        if log:
                            print(f'[ALVARA] ✅ Beneficiário ({dados_alvara["beneficiario"]}) = Autor ({autor_processo}) - Salvando no arquivo')
                        salvar_dados_alvara(dados_alvara, log)
                        
                    else:
                        # Beneficiário ≠ Autor: Não salvar
                        if log:
                            print(f'[ALVARA] ❌ Beneficiário ({dados_alvara["beneficiario"]}) ≠ Autor ({autor_processo}) - NÃO salvando no arquivo')
                else:
                    # Se não conseguiu extrair autor ou beneficiário, salvar mesmo assim com aviso
                    if log:
                        print(f'[ALVARA] ⚠️ Não foi possível comparar beneficiário com autor - Salvando por segurança')
                    salvar_dados_alvara(dados_alvara, log)
                
                return dados_alvara
            else:
                if log:
                    print('[ALVARA][AVISO] Não foi possível extrair dados do alvará')
                return None
                
        except Exception as e:
            if log:
                print(f'[ALVARA][ERRO] Falha ao processar alvará: {e}')
            return None
        finally:
            # LIMPEZA FINAL: Garantir que não há modais abertos ao sair da função
            try:
                modais_restantes = driver.find_elements(By.CSS_SELECTOR, 'main#main-content.mat-dialog-content')
                if modais_restantes:
                    if log:
                        print(f'[ALVARA] 🧹 Limpeza final: {len(modais_restantes)} modal(s) ainda aberto(s)')
                    
                    # Tentar fechar qualquer modal restante
                    for _ in range(3):
                        try:
                            from selenium.webdriver.common.keys import Keys
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(0.5)
                        except:
                            pass
                    
                    # Verificação final
                    modais_finais = driver.find_elements(By.CSS_SELECTOR, 'main#main-content.mat-dialog-content')
                    if modais_finais:
                        if log:
                            print(f'[ALVARA] ⚠️ Ainda restam {len(modais_finais)} modal(s) após limpeza')
                    else:
                        if log:
                            print('[ALVARA] ✅ Limpeza concluída, nenhum modal restante')
                    
                    time.sleep(1)  # Pequena pausa final
            except Exception as e_limpeza:
                if log:
                    print(f'[ALVARA][ERRO] Erro na limpeza final: {e_limpeza}')
    
    def extrair_dados_alvara(texto, data_timeline, log=True):
        """
        Extrai dados específicos do alvará: data de expedição, valor e beneficiário
        
        Args:
            texto: Texto do documento extraído
            data_timeline: Data da timeline como fallback
            log: Se deve exibir logs
            
        Returns:
            dict: Dados do alvará ou None se não conseguir extrair
        """
        try:
            dados = {
                'data_expedicao': data_timeline,  # Fallback
                'valor': None,
                'beneficiario': None
            }
            
            if log:
                print(f'[ALVARA][DEBUG] Texto para extração ({len(texto)} chars):')
                print(f'[ALVARA][DEBUG] Primeiros 500 chars: {texto[:500]}...')
            
            # NOVA REGRA: Verificar se contém "3011" no texto
            contem_3011 = '3011' in texto
            
            if contem_3011:
                # Modelo com data de atualização (contém 3011)
                # Buscar "Data de Atualização............: DD/MM/AAAA"
                padroes_data_atualizacao = [
                    r'Data de Atualiza[çc]ão[.\s]*:?\s*(\d{1,2}/\d{1,2}/\d{4})',
                    r'Data de Atualiza[çc]ão[.\s]*(\d{1,2}/\d{1,2}/\d{4})',
                    r'atualiza[çc]ão[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                    r'atualizado em[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'
                ]
                
                for padrao in padroes_data_atualizacao:
                    match = re.search(padrao, texto, re.IGNORECASE)
                    if match:
                        data_encontrada = match.group(1)
                        # Normalizar formato para dd/mm/aaaa
                        data_normalizada = normalizar_data(data_encontrada)
                        if data_normalizada:
                            dados['data_expedicao'] = data_normalizada
                            if log:
                                print(f'[ALVARA] ⚠️ 3011 detectado - Data de atualização encontrada: {data_normalizada}')
                            break
                
                # Se não encontrou data de atualização específica, usar fallback
                if dados['data_expedicao'] == data_timeline:
                    if log:
                        print(f'[ALVARA] ⚠️ 3011 detectado - Data de atualização não encontrada, usando fallback: {data_timeline}')
            else:
                # Modelo com data de expedição (não contém 3011)
                # Padrões de busca para data de expedição
                padroes_data_expedicao = [
                    r'expedi[çc]ão[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                    r'expedido em[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                    r'data[:\s]*de[:\s]*expedi[çc]ão[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                    r'data[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                    r'em[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                    r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'  # Qualquer data no formato
                ]
                
                for padrao in padroes_data_expedicao:
                    match = re.search(padrao, texto, re.IGNORECASE)
                    if match:
                        data_encontrada = match.group(1)
                        # Normalizar formato para dd/mm/aaaa
                        data_normalizada = normalizar_data(data_encontrada)
                        if data_normalizada:
                            dados['data_expedicao'] = data_normalizada
                            if log:
                                print(f'[ALVARA] Data de expedição encontrada: {data_normalizada}')
                            break
            
            # 2. Extrair valor - PADRÕES PARA AMBOS OS FORMATOS
            padroes_valor = [
                # Padrão específico do 1º screenshot (3011): "Valor do Alvará............: R$ 1339,50"
                r'Valor do Alvar[áa][.\s]*:?\s*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                # Padrões para o 2º screenshot (formato comum): "R$ 14.977,84"
                r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                # Padrões mais específicos para alvará comum
                r'valor[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'quantia[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'import[aâ]ncia[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                # Padrão genérico para qualquer valor monetário brasileiro
                r'(\d{1,3}(?:\.\d{3})*,\d{2})'
            ]
            
            for padrao in padroes_valor:
                matches = re.findall(padrao, texto, re.IGNORECASE)
                if matches:
                    # Pegar o maior valor encontrado (assumindo que é o principal)
                    valores = [converter_valor_para_float(v) for v in matches]
                    valor_maximo = max(valores)
                    dados['valor'] = formatar_valor_brasileiro(valor_maximo)
                    if log:
                        print(f'[ALVARA] Valor encontrado: {dados["valor"]} (padrão: {padrao})')
                    break
            
            # 3. Extrair beneficiário - PADRÕES PARA AMBOS OS FORMATOS
            padroes_beneficiario = [
                # Padrão específico do 1º screenshot (3011): "Beneficiário................: LUIS JOSE CARDOSO"
                r'Benefici[aá]rio[.\s]*:?\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                # Padrões para o 2º screenshot (formato comum): buscar "Beneficiário.........: NOME"
                r'Benefici[aá]rio[.\s:]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                # Padrões genéricos de backup
                r'benefici[aá]rio[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                r'favor de[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                r'em favor de[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                r'para[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                r'autorizado[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)'
            ]
            
            for padrao in padroes_beneficiario:
                match = re.search(padrao, texto, re.IGNORECASE)
                if match:
                    beneficiario = match.group(1).strip()
                    # Limpar texto (remover quebras de linha, espaços extras)
                    beneficiario = re.sub(r'\s+', ' ', beneficiario)
                    # Pegar apenas até a primeira vírgula ou ponto (se houver)
                    beneficiario = re.split(r'[,\.]', beneficiario)[0].strip()
                    if len(beneficiario) > 3:  # Nome válido
                        dados['beneficiario'] = beneficiario
                        if log:
                            print(f'[ALVARA] Beneficiário encontrado: "{beneficiario}" (padrão: {padrao})')
                        break
            
            # Verificar se conseguiu extrair pelo menos alguns dados
            if dados['valor'] or dados['beneficiario']:
                return dados
            else:
                if log:
                    print('[ALVARA][AVISO] Não foi possível extrair dados específicos do alvará')
                return None
                
        except Exception as e:
            if log:
                print(f'[ALVARA][ERRO] Erro ao extrair dados do alvará: {e}')
            return None
    
    def normalizar_data(data_str):
        """Normaliza data para formato dd/mm/aaaa"""
        try:
            # Remove espaços e substitui - por /
            data_clean = data_str.strip().replace('-', '/')
            
            # Verifica se já está no formato correto
            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', data_clean):
                partes = data_clean.split('/')
                dia = partes[0].zfill(2)
                mes = partes[1].zfill(2)
                ano = partes[2]
                return f"{dia}/{mes}/{ano}"
            
            return None
        except:
            return None
    
    def extrair_autor_processo(texto, log=True):
        """Extrai o nome do autor do processo do texto do alvará"""
        try:
            # Padrões específicos para ambos os formatos de alvará
            padroes_autor = [
                # Padrão específico do 1º screenshot (3011): "Autor (reclamante) ......: LUIS JOSE CARDOSO"
                r'Autor \(reclamante\)[.\s]*:?\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                # Padrões para o 2º screenshot (formato comum): "Requerente...........: NOME"
                r'Requerente[.\s]*:?\s*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                # Padrões genéricos de backup
                r'autor[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                r'requerente[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                r'exequente[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                r'processo[:\s]*\d+-\d+\.\d+\.\d+\.\d+[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)',
                r'nos autos[:\s]*.*?[:\s]*([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇa-záàâãéêíóôõúç\s]+)'
            ]
            
            for padrao in padroes_autor:
                match = re.search(padrao, texto, re.IGNORECASE)
                if match:
                    autor = match.group(1).strip()
                    # Limpar texto (remover quebras de linha, espaços extras)
                    autor = re.sub(r'\s+', ' ', autor)
                    # Pegar apenas até a primeira vírgula, "X" ou "versus" (se houver)
                    autor = re.split(r'[,]|(?:\s+[xX]\s+)|(?:\s+versus\s+)|(?:\s+vs?\s+)', autor)[0].strip()
                    if len(autor) > 3:  # Nome válido
                        if log:
                            print(f'[ALVARA] Autor do processo encontrado: "{autor}" (padrão: {padrao})')
                        return autor
            
            if log:
                print('[ALVARA] ⚠️ Autor do processo não encontrado no texto')
            return None
            
        except Exception as e:
            if log:
                print(f'[ALVARA][ERRO] Erro ao extrair autor do processo: {e}')
            return None
    
    def normalizar_nome(nome):
        """Normaliza nome para comparação (remove acentos, espaços extras, converte para minúsculo)"""
        try:
            if not nome:
                return ""
            
            import unicodedata
            
            # Converter para string se não for
            nome_str = str(nome)
            
            # Remover acentos
            nome_sem_acento = unicodedata.normalize('NFD', nome_str)
            nome_sem_acento = ''.join(c for c in nome_sem_acento if unicodedata.category(c) != 'Mn')
            
            # Converter para minúsculo e remover espaços extras
            nome_normalizado = re.sub(r'\s+', ' ', nome_sem_acento.lower().strip())
            
            return nome_normalizado
            
        except Exception as e:
            # Em caso de erro, retornar o nome original em minúsculo
            return str(nome).lower().strip() if nome else ""
    
    def converter_valor_para_float(valor_str):
        """Converte string de valor brasileiro para float"""
        try:
            # Remove pontos (separadores de milhares) e substitui vírgula por ponto
            valor_clean = valor_str.replace('.', '').replace(',', '.')
            return float(valor_clean)
        except:
            return 0.0
    
    def formatar_valor_brasileiro(valor_float):
        """Formata float para string no formato brasileiro"""
        try:
            return f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except:
            return "R$ 0,00"
    
    def salvar_dados_alvara(dados, log=True):
        """Salva dados do alvará em alvaras.js"""
        try:
            import os
            
            arquivo_path = os.path.join(os.getcwd(), 'alvaras.js')
            
            # Criar entrada de log
            entrada = {
                'timestamp': datetime.now().isoformat(),
                'data_expedicao': dados['data_expedicao'],
                'valor': dados['valor'],
                'beneficiario': dados['beneficiario']
            }
            
            # Ler arquivo existente ou criar novo
            dados_existentes = []
            if os.path.exists(arquivo_path):
                try:
                    with open(arquivo_path, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                        if conteudo.strip():
                            # Tentar extrair dados JSON do arquivo JS
                            match = re.search(r'const alvaras = (\[.*?\]);', conteudo, re.DOTALL)
                            if match:
                                dados_existentes = json.loads(match.group(1))
                except:
                    pass
            
            # Adicionar nova entrada
            dados_existentes.append(entrada)
            
            # Salvar arquivo JS
            conteudo_js = f"""// Dados de alvarás extraídos automaticamente
// Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

const alvaras = {json.dumps(dados_existentes, indent=2, ensure_ascii=False)};

// Função para buscar alvarás por período
function buscarAlvarasPorPeriodo(dataInicio, dataFim) {{
    return alvaras.filter(alvara => {{
        const data = new Date(alvara.data_expedicao.split('/').reverse().join('-'));
        const inicio = new Date(dataInicio);
        const fim = new Date(dataFim);
        return data >= inicio && data <= fim;
    }});
}}

// Função para calcular total de valores
function calcularTotalAlvaras(lista = alvaras) {{
    return lista.reduce((total, alvara) => {{
        const valor = parseFloat(alvara.valor.replace(/[R$\s.]/g, '').replace(',', '.'));
        return total + (isNaN(valor) ? 0 : valor);
    }}, 0);
}}

console.log(`Total de alvarás registrados: ${{alvaras.length}}`);
"""
            
            with open(arquivo_path, 'w', encoding='utf-8') as f:
                f.write(conteudo_js)
            
            if log:
                print(f'[ALVARA] Dados salvos em: {arquivo_path}')
                print(f'[ALVARA] Data: {dados["data_expedicao"]}, Valor: {dados["valor"]}, Beneficiario: {dados["beneficiario"]}')
        
        except Exception as e:
            if log:
                print(f'[ALVARA][ERRO] Erro ao salvar dados: {e}')
    
    def extrair_id_timeline(item, log=True):
        """
        Extrai o ID único do item da timeline (como em lista.js)
        
        Args:
            item: Elemento da timeline
            log: Se deve exibir logs
            
        Returns:
            str: ID do item ou ID gerado baseado no texto
        """
        try:
            # Tentar extrair ID do atributo data-id ou similar
            try:
                item_id = item.get_attribute('data-id')
                if item_id:
                    return item_id
            except:
                pass
            
            # Tentar extrair de atributos comuns
            for attr in ['id', 'data-item-id', 'data-timeline-id']:
                try:
                    item_id = item.get_attribute(attr)
                    if item_id:
                        return item_id
                except:
                    continue
            
            # Fallback: gerar ID baseado no texto do link principal
            try:
                links = item.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                if links:
                    texto_link = links[0].text.strip()
                    # Criar hash simples do texto para ID único
                    import hashlib
                    id_gerado = hashlib.md5(texto_link.encode()).hexdigest()[:8]
                    return f"tl-{id_gerado}"
            except:
                pass
            
            # Último fallback: ID baseado na posição
            return f"item-{hash(str(item)) % 10000}"
            
        except Exception as e:
            if log:
                print(f'[TIMELINE-ID][ERRO] Erro ao extrair ID: {e}')
            return f"erro-{hash(str(item)) % 10000}"

    def extrair_data_item(item):
        """Extrai data do item da timeline usando Selenium"""
        try:
            # Buscar elemento .tl-data
            data_element = None
            try:
                data_element = item.find_element(By.CSS_SELECTOR, '.tl-data[name="dataItemTimeline"]')
            except:
                try:
                    data_element = item.find_element(By.CSS_SELECTOR, '.tl-data')
                except:
                    pass
            
            # Se não encontrou, buscar em elementos anteriores usando JavaScript
            if not data_element:
                try:
                    data_texto = driver.execute_script("""
                        var item = arguments[0];
                        var dataElement = null;
                        var elementoAnterior = item.previousElementSibling;
                        while (elementoAnterior) {
                            dataElement = elementoAnterior.querySelector('.tl-data[name="dataItemTimeline"]');
                            if (!dataElement) {
                                dataElement = elementoAnterior.querySelector('.tl-data');
                            }
                            if (dataElement) break;
                            elementoAnterior = elementoAnterior.previousElementSibling;
                        }
                        return dataElement ? dataElement.textContent.trim() : null;
                    """, item)
                    
                    if data_texto:
                        # Converter formato "01 mar. 2019" para "01/03/2019"
                        data_convertida = converter_data_texto_para_numerico(data_texto)
                        if data_convertida:
                            return data_convertida
                except Exception as e:
                    pass
            
            if data_element:
                data_texto = data_element.text.strip()
                # Converter formato "01 mar. 2019" para "01/03/2019"
                data_convertida = converter_data_texto_para_numerico(data_texto)
                if data_convertida:
                    return data_convertida
            
            # Fallback: buscar data no texto do item
            texto_completo = item.text
            match_data = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', texto_completo)
            if match_data:
                return match_data.group(1)
            
            return 'Data não encontrada'
        except:
            return 'Erro na data'
    
    def converter_data_texto_para_numerico(data_texto):
        """Converte texto de data para formato numérico"""
        try:
            meses = {
                'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
            }
            
            match = re.search(r'(\d{1,2})\s+(\w{3})\.?\s+(\d{4})', data_texto)
            if match:
                dia = match.group(1).zfill(2)
                mes_texto = match.group(2).lower()
                ano = match.group(3)
                
                mes_numero = meses.get(mes_texto)
                if mes_numero:
                    return f"{dia}/{mes_numero}/{ano}"
            
            return None
        except:
            return None

    def salvar_alvaras_arquivo(dados_alvaras, log=True):
        """
        Salva a lista completa de alvarás no arquivo alvaras.js
        
        Args:
            dados_alvaras: Lista completa de alvarás
            log: Se deve exibir logs
        """
        try:
            from datetime import datetime
            import json
            import os
            
            arquivo_path = os.path.join(os.getcwd(), 'alvaras.js')
            
            # Salvar arquivo JS atualizado
            conteudo_js = f"""// Dados de alvarás extraídos automaticamente
// Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

const alvaras = {json.dumps(dados_alvaras, indent=2, ensure_ascii=False)};

// Função para buscar alvarás por período
function buscarAlvarasPorPeriodo(dataInicio, dataFim) {{
    return alvaras.filter(alvara => {{
        const data = new Date(alvara.data_expedicao.split('/').reverse().join('-'));
        const inicio = new Date(dataInicio);
        const fim = new Date(dataFim);
        return data >= inicio && data <= fim;
    }});
}}

// Função para calcular total de valores
function calcularTotalAlvaras(lista = alvaras) {{
    return lista.reduce((total, alvara) => {{
        const valor = parseFloat(alvara.valor.replace(/[R$\s.]/g, '').replace(',', '.'));
        return total + (isNaN(valor) ? 0 : valor);
    }}, 0);
}}

// Função para buscar alvarás registrados
function buscarAlvarasRegistrados() {{
    return alvaras.filter(alvara => alvara.status === 'ALVARA_REGISTRADO');
}}

console.log(`Total de alvarás registrados: ${{alvaras.length}}`);
"""
            
            with open(arquivo_path, 'w', encoding='utf-8') as f:
                f.write(conteudo_js)
            
            if log:
                print(f'[ALVARA] Arquivo atualizado: {arquivo_path}')
                print(f'[ALVARA] Total de {len(dados_alvaras)} alvarás salvos')
        
        except Exception as e:
            if log:
                print(f'[ALVARA][ERRO] Erro ao salvar arquivo: {e}')

    def gerar_gigs_final(driver, dados_gigs_final, log=True):
        """
        Gera GIGS final consolidado com todas as medidas encontradas.
        Formato: 0/{medidas} - sem responsável
        
        Args:
            driver: WebDriver do Selenium
            dados_gigs_final: Estrutura com todas as medidas coletadas
            log: Se deve exibir logs
            
        Returns:
            dict: Resultado da criação do GIGS final
        """
        try:
            if log:
                print('[GIGS-FINAL] Gerando GIGS consolidado final...')
            
            # Construir texto das medidas
            medidas_texto = []
            
            # 1. ALVARÁS SEM REGISTRO
            if dados_gigs_final['alvaras_sem_registro']:
                medidas_texto.append("Alvará:")
                for alvara in dados_gigs_final['alvaras_sem_registro']:
                    linha_alvara = f"{alvara['id_timeline']} - {alvara['data']} - {alvara['valor']}"
                    medidas_texto.append(linha_alvara)
                medidas_texto.append("")  # Linha em branco
            
            # 2. PESQUISAS (CNIB e SERASA)
            if dados_gigs_final['cnib_anexos'] or dados_gigs_final['serasa_anexos']:
                medidas_texto.append("_______________")
                medidas_texto.append("PESQUISAS:")
                
                # CNIB
                if dados_gigs_final['cnib_anexos']:
                    cnib_ids = ", ".join(dados_gigs_final['cnib_anexos'])
                    medidas_texto.append(f"CNIB - {cnib_ids}")
                
                # SERASA
                if dados_gigs_final['serasa_anexos']:
                    serasa_ids = ", ".join(dados_gigs_final['serasa_anexos'])
                    medidas_texto.append(f"SERASA - {serasa_ids}")
                
                medidas_texto.append("")  # Linha em branco
            
            # 3. SOBRESTAMENTOS
            if dados_gigs_final['sobrestamentos']:
                if medidas_texto:  # Se já tem conteúdo, adicionar separador
                    medidas_texto.append("____________")
                medidas_texto.append("Sobrestamento:")
                for sobrestamento in dados_gigs_final['sobrestamentos']:
                    linha_sobrestamento = f"{sobrestamento['id_timeline']} - {sobrestamento['data']}"
                    medidas_texto.append(linha_sobrestamento)
            
            # Verificar se há medidas para processar
            if not medidas_texto:
                if log:
                    print('[GIGS-FINAL] ⚠️ Nenhuma medida encontrada para GIGS final')
                return None
            
            # Juntar todo o texto
            observacao_completa = "\n".join(medidas_texto)
            
            if log:
                print('[GIGS-FINAL] Texto das medidas gerado:')
                print('=' * 50)
                print(observacao_completa)
                print('=' * 50)
            
            # Chamar criar_gigs do Fix.py
            try:
                # Importar função necessária
                from Fix import criar_gigs
                
                gigs_resultado = criar_gigs(
                    driver=driver,
                    dias_uteis=0,
                    responsavel="",  # Sem responsável
                    observacao=observacao_completa,
                    timeout=15,
                    log=log
                )
                
                if gigs_resultado:
                    if log:
                        print('[GIGS-FINAL] ✅ GIGS final criado com sucesso!')
                    return {
                        'status': 'sucesso',
                        'gigs': f'0/{observacao_completa[:50]}...',
                        'total_alvaras': len(dados_gigs_final['alvaras_sem_registro']),
                        'total_cnib': len(dados_gigs_final['cnib_anexos']),
                        'total_serasa': len(dados_gigs_final['serasa_anexos']),
                        'total_sobrestamentos': len(dados_gigs_final['sobrestamentos'])
                    }
                else:
                    if log:
                        print('[GIGS-FINAL] ❌ Falha ao criar GIGS final')
                    return {
                        'status': 'falha',
                        'erro': 'Falha na criação do GIGS'
                    }
                
            except ImportError:
                if log:
                    print('[GIGS-FINAL][ERRO] Não foi possível importar criar_gigs do Fix.py')
                return {
                    'status': 'erro',
                    'erro': 'Função criar_gigs não disponível'
                }
            except Exception as e_gigs:
                if log:
                    print(f'[GIGS-FINAL][ERRO] Erro ao criar GIGS: {e_gigs}')
                return {
                    'status': 'erro',
                    'erro': str(e_gigs)
                }
                
        except Exception as e:
            if log:
                print(f'[GIGS-FINAL][ERRO] Erro geral na geração do GIGS final: {e}')
            return {
                'status': 'erro',
                'erro': str(e)
            }

    def processar_anexos_certidoes(driver, doc, dados_gigs_final, log=True):
        """
        Processa anexos de certidões (oficial de justiça ou pesquisa patrimonial)
        buscando por CNIB e SERASA.
        
        Args:
            driver: WebDriver do Selenium
            doc: Documento da certidão
            dados_gigs_final: Estrutura para coletar dados do GIGS final
            log: Se deve exibir logs
            
        Returns:
            list: Lista de medidas encontradas em anexos
        """
        try:
            from selenium.webdriver.common.by import By
            import time
            
            medidas_anexos = []
            
            # Verificar se tem botão de anexos
            btn_anexos = doc['item'].find_elements(By.CSS_SELECTOR, 'pje-timeline-anexos > div > div')
            
            if btn_anexos:
                if log:
                    print(f'[LISTA-EXEC][ANEXOS] Processando anexos de: {doc["link"].text.strip()}')
                
                # Clicar no botão de anexos
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_anexos[0])
                driver.execute_script("arguments[0].click();", btn_anexos[0])
                time.sleep(2)
                
                # Buscar anexos
                anexos = driver.find_elements(By.CSS_SELECTOR, ".tl-item-anexo")
                
                if anexos:
                    if log:
                        print(f'[LISTA-EXEC][ANEXOS] ✅ Encontrados {len(anexos)} anexos')
                    
                    for anexo_index, anexo in enumerate(anexos):
                        try:
                            texto_anexo = anexo.text.strip().lower()
                            
                            # Buscar CNIB em anexos
                            if 'cnib' in texto_anexo:
                                # Extrair ID do anexo para GIGS final
                                id_anexo = extrair_id_timeline(anexo)
                                dados_gigs_final['cnib_anexos'].append(id_anexo)
                                
                                uid_anexo = f"anexo-cnib-{doc['index']}-{anexo_index}"
                                medida_anexo = {
                                    'nome': 'CNIB',
                                    'texto': f'CNIB (anexo): {anexo.text.strip()}',
                                    'data': doc['data'],
                                    'id': uid_anexo,
                                    'id_timeline': id_anexo,  # ID para GIGS final
                                    'elemento': anexo,
                                    'link': anexo,
                                    'index': doc['index'],
                                    'tipo_item': 'anexo',
                                    'documento_pai': doc['link'].text.strip()
                                }
                                medidas_anexos.append(medida_anexo)
                                if log:
                                    print(f'[LISTA-EXEC][ANEXOS] ✅ CNIB encontrado: {anexo.text.strip()} (ID: {id_anexo})')
                            
                            # Buscar SERASA em anexos
                            if 'serasa' in texto_anexo:
                                # Extrair ID do anexo para GIGS final
                                id_anexo = extrair_id_timeline(anexo)
                                dados_gigs_final['serasa_anexos'].append(id_anexo)
                                
                                uid_anexo = f"anexo-serasa-{doc['index']}-{anexo_index}"
                                medida_anexo = {
                                    'nome': 'Serasa',
                                    'texto': f'Serasa (anexo): {anexo.text.strip()}',
                                    'data': doc['data'],
                                    'id': uid_anexo,
                                    'id_timeline': id_anexo,  # ID para GIGS final
                                    'elemento': anexo,
                                    'link': anexo,
                                    'index': doc['index'],
                                    'tipo_item': 'anexo',
                                    'documento_pai': doc['link'].text.strip()
                                }
                                medidas_anexos.append(medida_anexo)
                                if log:
                                    print(f'[LISTA-EXEC][ANEXOS] ✅ SERASA encontrado: {anexo.text.strip()} (ID: {id_anexo})')
                        
                        except Exception as e:
                            if log:
                                print(f'[LISTA-EXEC][ANEXOS][ERRO] Erro ao processar anexo {anexo_index}: {e}')
                            continue
                else:
                    if log:
                        print(f'[LISTA-EXEC][ANEXOS] ❌ Nenhum anexo encontrado')
            else:
                if log:
                    print(f'[LISTA-EXEC][ANEXOS] ❌ Botão de anexos não encontrado')
            
            return medidas_anexos
            
        except Exception as e:
            if log:
                print(f'[LISTA-EXEC][ANEXOS][ERRO] Erro geral ao processar anexos: {e}')
            return []

    def verificar_serasa_em_anexos(driver, documentos_relevantes, log=True):
        """
        Verifica se há SERASA em anexos de certidões de oficial de justiça ou pesquisa patrimonial.
        
        Args:
            driver: WebDriver do Selenium
            documentos_relevantes: Lista de documentos relevantes encontrados
            log: Se deve exibir logs
            
        Returns:
            bool: True se encontrou SERASA em anexos, False caso contrário
        """
        try:
            serasa_encontrado_em_anexos = False
            
            # Buscar documentos que podem ter anexos com SERASA
            documentos_com_anexos = [
                doc for doc in documentos_relevantes 
                if doc['item_alvo']['tipo'] == 'documento_com_anexos'
            ]
            
            if not documentos_com_anexos:
                if log:
                    print('[LISTA-EXEC] Nenhum documento com possíveis anexos SERASA encontrado')
                return False
            
            for doc in documentos_com_anexos:
                try:
                    # Verificar se tem botão de anexos
                    btn_anexos = doc['item'].find_elements(By.CSS_SELECTOR, 'pje-timeline-anexos > div > div')
                    
                    if btn_anexos:
                        if log:
                            print(f'[LISTA-EXEC] Verificando anexos de: {doc["link"].text.strip()}')
                        
                        # Clicar no botão de anexos
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_anexos[0])
                        driver.execute_script("arguments[0].click();", btn_anexos[0])
                        time.sleep(2)
                        
                        # Buscar anexos
                        anexos = driver.find_elements(By.CSS_SELECTOR, ".tl-item-anexo")
                        
                        if anexos:
                            for anexo in anexos:
                                texto_anexo = anexo.text.strip().lower()
                                if 'serasa' in texto_anexo:
                                    serasa_encontrado_em_anexos = True
                                    if log:
                                        print(f'[LISTA-EXEC] ✅ SERASA encontrado em anexo: {texto_anexo}')
                                    break
                        
                        if serasa_encontrado_em_anexos:
                            break
                            
                except Exception as e:
                    if log:
                        print(f'[LISTA-EXEC][ERRO] Erro ao verificar anexos: {e}')
                    continue
            
            return serasa_encontrado_em_anexos
            
        except Exception as e:
            if log:
                print(f'[LISTA-EXEC][ERRO] Erro na verificação de SERASA em anexos: {e}')
            return False

    def buscar_termos_em_anexos(driver, item, index, itens_alvo, log=True):
        """
        Busca termos relevantes em anexos de documentos (certidão de oficial de justiça ou pesquisa patrimonial).
        Usa o seletor da função tratar_anexos_argos de m1.py.
        
        Args:
            driver: WebDriver do Selenium
            item: Elemento do documento principal
            index: Índice do item na timeline
            itens_alvo: Lista de termos a serem buscados
            log: Se deve exibir logs
            
        Returns:
            list: Lista de medidas encontradas em anexos
        """
        try:
            import time
            from selenium.webdriver.common.by import By
            
            medidas_anexos = []
            
            if log:
                print(f'[LISTA-EXEC][ANEXOS] Buscando anexos no item {index}...')
            
            # Usar o seletor correto do JavaScript para anexos
            btn_anexos = item.find_elements(By.CSS_SELECTOR, "pje-timeline-anexos > div > div")
            
            if btn_anexos:
                if log:
                    print(f'[LISTA-EXEC][ANEXOS] Encontrado botão de anexos, clicando...')
                
                # Clicar no botão de anexos
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_anexos[0])
                driver.execute_script("arguments[0].click();", btn_anexos[0])
                import time
                time.sleep(2)
                
                # Buscar anexos
                anexos = driver.find_elements(By.CSS_SELECTOR, ".tl-item-anexo")
                
                if anexos:
                    if log:
                        print(f'[LISTA-EXEC][ANEXOS] ✅ Encontrados {len(anexos)} anexos para análise')
                    
                    for anexo_index, anexo in enumerate(anexos):
                        try:
                            texto_anexo = anexo.text.strip().lower()
                            
                            # Aplicar o mesmo filtro de termos
                            for item_alvo in itens_alvo:
                                encontrado = any(termo in texto_anexo for termo in item_alvo['termos'])
                                if encontrado:
                                    data = f"{index+1:02d}/01/2024"  # Placeholder
                                    uid = f"anexo-{index}-{anexo_index}"
                                    
                                    medida = {
                                        'nome': f"{item_alvo['nome']} (anexo)",
                                        'texto': anexo.text.strip(),
                                        'data': data,
                                        'id': uid,
                                        'elemento': anexo,
                                        'index': index,
                                        'anexo_index': anexo_index,
                                        'tipo_item': 'anexo'
                                    }
                                    
                                    medidas_anexos.append(medida)
                                    
                                    if log:
                                        print(f'[LISTA-EXEC][ANEXOS] ✅ {item_alvo["nome"]} em anexo: {anexo.text.strip()[:100]}...')
                                    
                                    break  # Sair do loop após encontrar a primeira correspondência
                        
                        except Exception as e:
                            if log:
                                print(f'[LISTA-EXEC][ANEXOS][ERRO] Erro ao processar anexo {anexo_index}: {e}')
                            continue
                else:
                    if log:
                        print(f'[LISTA-EXEC][ANEXOS] ❌ Nenhum anexo encontrado')
            else:
                if log:
                    print(f'[LISTA-EXEC][ANEXOS] ❌ Botão de anexos não encontrado')
            
            return medidas_anexos
            
        except Exception as e:
            if log:
                print(f'[LISTA-EXEC][ANEXOS][ERRO] Erro geral ao buscar anexos: {e}')
            return []

    def gerar_gigs_serasa(driver, item, link, data, log=True):
        """
        Gera GIGS específico para Serasa encontrado na timeline principal.
        Cria: 1/Bianca/Serasa Arq
        
        Args:
            driver: WebDriver do Selenium
            item: Elemento da timeline
            link: Link do documento
            data: Data do Serasa
            log: Se deve exibir logs
        """
        try:
            if log:
                print(f'[SERASA-GIGS] Processando Serasa para GIGS: {link.text.strip()}')
            
            # Importar função necessária (assumindo que está disponível)
            import time
            
            # Selecionar o documento
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
            driver.execute_script("arguments[0].click();", link)
            
            if log:
                print('[SERASA-GIGS] Documento selecionado, aguardando carregamento...')
            
            import time
            time.sleep(2)  # Aguarda carregamento do documento
            
            # Gerar GIGS 1/Bianca/Serasa Arq
            try:
                # Usar a função criar_gigs do Fix.py
                # Padrão: dias_uteis=1, responsavel="Bianca", observacao="Serasa Arq"
                gigs_resultado = criar_gigs(
                    driver=driver,
                    dias_uteis=1,
                    responsavel="Bianca",
                    observacao="Serasa Arq",
                    timeout=10,
                    log=log
                )
                
                if gigs_resultado:
                    gigs_texto = "1/Bianca/Serasa Arq"
                    if log:
                        print(f'[SERASA-GIGS] ✅ GIGS criado com sucesso: {gigs_texto}')
                        print(f'[SERASA-GIGS] Data: {data}')
                    
                    # Retornar informações do GIGS gerado
                    return {
                        'gigs': gigs_texto,
                        'data': data,
                        'documento': link.text.strip(),
                        'status': 'criado_com_sucesso'
                    }
                else:
                    if log:
                        print('[SERASA-GIGS][ERRO] Falha ao criar GIGS')
                    return {
                        'gigs': "1/Bianca/Serasa Arq",
                        'data': data,
                        'documento': link.text.strip(),
                        'status': 'falha_na_criacao'
                    }
                
            except Exception as e_gigs:
                if log:
                    print(f'[SERASA-GIGS][ERRO] Erro ao gerar GIGS: {e_gigs}')
                return None
                
        except Exception as e:
            if log:
                print(f'[SERASA-GIGS][ERRO] Falha ao processar Serasa para GIGS: {e}')
            return None
    
    def pagamento(driver, log=True):
        """
        Processa a lógica de pagamentos, comparando alvarás com a listagem de pagamentos.
        A função agora lê a lista de alvarás do arquivo `alvaras.js` e a atualiza.
        
        Args:
            driver: WebDriver do Selenium
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
                        
                        # TODO: Implementar lógica específica para registros sem correspondência
                        if log:
                            print(f'[REGISTRO] Processando alvará sem correspondência: {alvara.get("data_expedicao")} - {alvara.get("valor")}')
                            print(f'[REGISTRO] Beneficiário: {alvara.get("beneficiario")}')
                            print('[REGISTRO] TODO: Implementar lógica específica para registros sem correspondência')
                
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
                from datetime import datetime
                
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
                import time
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

def processar_alvaras_completo(driver, alvaras_encontrados=None, log=True):
    """
    Função única que processa completamente alvarás encontrados na timeline.
    
    Fluxo completo:
    1. Se alvaras_encontrados não fornecido, busca alvarás na timeline
    2. Extrai conteúdo e dados detalhados de todos os alvarás
    3. Abre aba de pagamentos para comparação
    4. Registra alvarás não registrados
    
    Args:
        driver: WebDriver do Selenium
        alvaras_encontrados: Lista opcional de alvarás já localizados na timeline
                           Formato: [{'elemento': element, 'link': link, 'data': data, 'texto': texto}, ...]
        log: Se deve exibir logs
        
    Returns:
        dict: {
            'alvaras_processados': [...],
            'alvaras_registrados': [...],
            'alvaras_sem_registro': [...],
            'sucesso': bool
        }
    """
    try:
        from datetime import datetime
        import time
        from selenium.webdriver.common.by import By
        
        if log:
            print('[PROCESSAR-ALVARAS] 🚀 Iniciando processamento completo de alvarás...')
        
        resultado = {
            'alvaras_processados': [],
            'alvaras_registrados': [],
            'alvaras_sem_registro': [],
            'sucesso': False
        }
        
        # ===== ETAPA 1: LOCALIZAR ALVARÁS NA TIMELINE (se não fornecidos) =====
        if alvaras_encontrados is None:
            if log:
                print('[PROCESSAR-ALVARAS] 1. Buscando alvarás na timeline...')
            
            alvaras_encontrados = []
            
            # Buscar itens da timeline
            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
            if not itens:
                itens = driver.find_elements(By.CSS_SELECTOR, '.timeline-item')
            
            for item in itens:
                try:
                    links = item.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    for link in links:
                        texto = link.text.lower().strip()
                        if 'alvará' in texto or 'alvara' in texto:
                            # Extrair data do item
                            data = ''
                            try:
                                data_el = item.find_element(By.CSS_SELECTOR, '.tl-data[name="dataItemTimeline"], .tl-data')
                                data_texto = data_el.text.strip()
                                import re
                                data_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', data_texto)
                                data = data_match.group(1) if data_match else ''
                            except:
                                pass
                            
                            alvaras_encontrados.append({
                                'elemento': item,
                                'link': link,
                                'data': data,
                                'texto': link.text.strip()
                            })
                            if log:
                                print(f'[PROCESSAR-ALVARAS] ✅ Alvará encontrado: {link.text.strip()} ({data})')
                except:
                    continue
        
        if not alvaras_encontrados:
            if log:
                print('[PROCESSAR-ALVARAS] ⚠️ Nenhum alvará encontrado na timeline')
            return resultado
        
        if log:
            print(f'[PROCESSAR-ALVARAS] 📋 {len(alvaras_encontrados)} alvará(s) para processar')
        
        # ===== ETAPA 2: EXTRAIR CONTEÚDO E DADOS DETALHADOS DOS ALVARÁS =====
        if log:
            print('[PROCESSAR-ALVARAS] 2. Extraindo dados detalhados dos alvarás...')
        
        alvaras_processados = []
        
        for idx, alvara_info in enumerate(alvaras_encontrados):
            try:
                if log:
                    print(f'[PROCESSAR-ALVARAS] 2.{idx+1}. Processando alvará: {alvara_info["texto"]}')
                
                # Clicar no link do alvará para abrir
                alvara_info['link'].click()
                time.sleep(2)
                
                # Aguardar modal de documento abrir
                try:
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    
                    # Aguardar modal aparecer
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-doc-visualizar, .modal-content, [role="dialog"]'))
                    )
                    time.sleep(1)
                    
                    # Extrair dados do alvará usando função existente
                    dados_alvara = extrair_dados_alvara(alvara_info['texto'], alvara_info['data'], log)
                    
                    if dados_alvara:
                        dados_alvara.update({
                            'elemento_timeline': alvara_info['elemento'],
                            'link_timeline': alvara_info['link'],
                            'data_timeline': alvara_info['data'],
                            'texto_timeline': alvara_info['texto'],
                            'timestamp': datetime.now().isoformat(),
                            'status': 'PROCESSADO'
                        })
                        alvaras_processados.append(dados_alvara)
                        
                        if log:
                            print(f'[PROCESSAR-ALVARAS] ✅ Dados extraídos: {dados_alvara.get("beneficiario", "N/A")} - {dados_alvara.get("valor", "N/A")}')
                    
                    # Fechar modal
                    try:
                        # Buscar botão de fechar
                        botoes_fechar = driver.find_elements(By.CSS_SELECTOR, 
                            'button[aria-label="Fechar"], button.close, .modal-header button, button[mat-dialog-close]')
                        if botoes_fechar:
                            botoes_fechar[0].click()
                            time.sleep(1)
                        else:
                            # Pressionar ESC como fallback
                            from selenium.webdriver.common.keys import Keys
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(1)
                    except:
                        pass
                        
                except Exception as e:
                    if log:
                        print(f'[PROCESSAR-ALVARAS] ⚠️ Erro ao extrair dados do alvará: {e}')
                    continue
                    
            except Exception as e:
                if log:
                    print(f'[PROCESSAR-ALVARAS] ❌ Erro ao processar alvará {idx+1}: {e}')
                continue
        
        resultado['alvaras_processados'] = alvaras_processados
        
        if not alvaras_processados:
            if log:
                print('[PROCESSAR-ALVARAS] ⚠️ Nenhum alvará foi processado com sucesso')
            return resultado
        
        # ===== ETAPA 3: ABRIR ABA DE PAGAMENTOS PARA COMPARAÇÃO =====
        if log:
            print('[PROCESSAR-ALVARAS] 3. Navegando para aba de pagamentos...')
        
        # Usar função existente para navegar para pagamentos
        if navegar_para_pagamentos(driver, log):
            if log:
                print('[PROCESSAR-ALVARAS] ✅ Navegação para pagamentos bem-sucedida')
            
            # Analisar listagem de pagamentos
            pagamentos_encontrados = analisar_listagem_pagamentos(driver, log)
            
            if log:
                print(f'[PROCESSAR-ALVARAS] 📋 {len(pagamentos_encontrados)} pagamento(s) encontrado(s)')
            
            # Comparar alvarás com pagamentos
            if pagamentos_encontrados:
                comparacao = comparar_alvaras_com_pagamentos(alvaras_processados, pagamentos_encontrados, log)
                resultado['alvaras_registrados'] = comparacao.get('correspondencias', [])
                resultado['alvaras_sem_registro'] = comparacao.get('sem_correspondencia', [])
            else:
                resultado['alvaras_sem_registro'] = alvaras_processados.copy()
                
        else:
            if log:
                print('[PROCESSAR-ALVARAS] ⚠️ Falha na navegação para pagamentos, marcando todos como sem registro')
            resultado['alvaras_sem_registro'] = alvaras_processados.copy()
        
        # ===== ETAPA 4: REGISTRAR ALVARÁS NÃO REGISTRADOS =====
        if resultado['alvaras_sem_registro']:
            if log:
                print(f'[PROCESSAR-ALVARAS] 4. Registrando {len(resultado["alvaras_sem_registro"])} alvará(s) não registrado(s)...')
            
            for alvara in resultado['alvaras_sem_registro']:
                try:
                    if log:
                        print(f'[PROCESSAR-ALVARAS] 📝 Registrando: {alvara.get("beneficiario", "N/A")} - {alvara.get("valor", "N/A")}')
                    
                    # Usar lógica de registro existente
                    # TODO: Implementar registro real quando necessário
                    alvara['status'] = 'AGUARDANDO_REGISTRO'
                    
                except Exception as e:
                    if log:
                        print(f'[PROCESSAR-ALVARAS] ❌ Erro ao registrar alvará: {e}')
        
        # ===== SALVAR DADOS PROCESSADOS =====
        if alvaras_processados:
            try:
                salvar_dados_alvara(alvaras_processados, log)
                if log:
                    print('[PROCESSAR-ALVARAS] ✅ Dados dos alvarás salvos em arquivo')
            except Exception as e:
                if log:
                    print(f'[PROCESSAR-ALVARAS] ⚠️ Erro ao salvar dados: {e}')
        
        # ===== FINALIZAÇÃO =====
        resultado['sucesso'] = True
        
        if log:
            print('[PROCESSAR-ALVARAS] 📊 RESUMO FINAL:')
            print(f'[PROCESSAR-ALVARAS]   - Alvarás processados: {len(resultado["alvaras_processados"])}')
            print(f'[PROCESSAR-ALVARAS]   - Alvarás já registrados: {len(resultado["alvaras_registrados"])}')
            print(f'[PROCESSAR-ALVARAS]   - Alvarás sem registro: {len(resultado["alvaras_sem_registro"])}')
            print('[PROCESSAR-ALVARAS] ✅ Processamento completo finalizado!')
        
        return resultado
        
    except Exception as e:
        if log:
            print(f'[PROCESSAR-ALVARAS] ❌ Erro geral no processamento: {e}')
        
        resultado['sucesso'] = False
        return resultado

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

    def ler_alvaras_arquivo(log=True):
        """Lê o arquivo alvaras.js e retorna os dados"""
        try:
            import os
            import json
            
            arquivo_path = os.path.join(os.getcwd(), 'alvaras.js')
            
            # Ler arquivo existente
            if os.path.exists(arquivo_path):
                try:
                    with open(arquivo_path, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                        if conteudo.strip():
                            # Tentar extrair dados JSON do arquivo JS
                            match = re.search(r'const alvaras = (\[.*?\]);', conteudo, re.DOTALL)
                            if match:
                                dados_existentes = json.loads(match.group(1))
                                if log:
                                    print(f'[ALVARA] {len(dados_existentes)} alvarás encontrados no arquivo')
                                return dados_existentes
                except Exception as e:
                    if log:
                        print(f'[ALVARA][ERRO] Erro ao ler arquivo alvaras.js: {e}')
            
            return []
        
        except Exception as e:
            if log:
                print(f'[ALVARA][ERRO] Erro geral na leitura do arquivo alvaras.js: {e}')
            return []
    
    def atualizar_status_alvara(alvaras, alvara_alvo, novo_status, log=True):
        """
        Atualiza o status de um alvará na lista de alvarás.
        
        Args:
            alvaras: Lista de alvarás
            alvara_alvo: Alvará alvo para atualização
            novo_status: Novo status a ser atribuído
            log: Se deve exibir logs
        """
        try:
            for alvara in alvaras:
                if alvara.get('data_expedicao') == alvara_alvo.get('data_expedicao') and alvara.get('valor') == alvara_alvo.get('valor'):
                    if log:
                        print(f'[ALVARA] Atualizando alvará: {alvara.get("data_expedicao")} - {novo_status}')
                    alvara['status'] = novo_status
                    break
        
        except Exception as e:
            if log:
                print(f'[ALVARA][ERRO] Erro ao atualizar status do alvará: {e}')
    
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

    def navegar_para_pagamentos(driver, log=True):
        """
        Navega para a tela de pagamentos usando o fluxo correto da interface:
        menu hambúrguer > botão Pagamento > aguarda nova aba com URL /cadastro
        
        Args:
            driver: WebDriver do Selenium
            log: Se deve exibir logs
            
        Returns:
            bool: True se navegação foi bem-sucedida
        """
        try:
            import time
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            if log:
                print('[PAGAMENTO] Navegando para tela de pagamentos via interface...')
            
            # Aguardar e clicar no menu hambúrguer
            try:
                hamburger_selectors = [
                    'button#botao-menu[aria-label="Menu do processo"]',
                    'button[id="botao-menu"]',
                    'button[aria-label="Menu do processo"]',
                    'button[mattooltip="Menu do processo"]',
                    'button.botao-menu[mat-icon-button]',
                    'button[aria-label="Toggle sidenav"]',
                    'button.mat-button.mat-icon-button.sidenav-toggle',
                    'button[mattooltip="Menu lateral"]',
                    'button[mat-icon-button]',
                    '.sidenav-toggle'
                ]
                
                hamburger_button = None
                for selector in hamburger_selectors:
                    try:
                        hamburger_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        break
                    except:
                        continue
                
                if not hamburger_button:
                    if log:
                        print('[PAGAMENTO][ERRO] Menu hambúrguer não encontrado')
                    return False
                
                hamburger_button.click()
                time.sleep(1)  # Aguardar menu abrir
                
                if log:
                    print('[PAGAMENTO] ✅ Menu hambúrguer clicado')
                    print('[PAGAMENTO] 🔍 Aguardando menu abrir e procurando botão Pagamento...')
                
            except Exception as e:
                if log:
                    print(f'[PAGAMENTO][ERRO] Erro ao clicar no menu hambúrguer: {e}')
                return False
            
            # Aguardar e clicar no botão Pagamento
            try:
                if log:
                    print('[PAGAMENTO] 🔍 Procurando botão Pagamento...')
                
                # Usar apenas o seletor que funcionou
                pagamento_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Pagamento"]'))
                )
                
                if log:
                    print('[PAGAMENTO] ✅ Botão Pagamento encontrado')
                
                # Armazenar abas atuais antes do clique
                abas_iniciais = driver.window_handles
                
                pagamento_button.click()
                time.sleep(2)  # Aguardar navegação
                
                if log:
                    print('[PAGAMENTO] ✅ Botão Pagamento clicado')
                
            except Exception as e:
                if log:
                    print(f'[PAGAMENTO][ERRO] Erro ao clicar no botão Pagamento: {e}')
                return False
            
            # Verificar se nova aba foi aberta ou se navegou na mesma aba
            try:
                if log:
                    print('[PAGAMENTO] 🔍 Verificando navegação (nova aba ou mesma aba)...')
                
                # Aguardar um pouco para permitir que a nova aba abra
                time.sleep(3)
                
                # Verificar se há novas abas
                abas_atuais = driver.window_handles
                if len(abas_atuais) > len(abas_iniciais):
                    # Nova aba foi aberta - mudar para ela
                    nova_aba = abas_atuais[-1]  # Última aba (nova)
                    driver.switch_to.window(nova_aba)
                    if log:
                        print('[PAGAMENTO] ✅ Nova aba detectada, mudando para ela...')
                else:
                    if log:
                        print('[PAGAMENTO] 🔍 Permanecendo na aba atual...')
                
                # Aguardar até que a URL contenha 'cadastro' ou 'pagamento'
                WebDriverWait(driver, 15).until(
                    lambda d: '/cadastro' in d.current_url or 'pagamento' in d.current_url
                )
                
                if log:
                    print(f'[PAGAMENTO] ✅ Navegação concluída. URL atual: {driver.current_url}')
                return True
                
            except Exception as e:
                if log:
                    print(f'[PAGAMENTO][ERRO] Timeout aguardando navegação para tela de pagamentos: {e}')
                    print(f'[PAGAMENTO] URL atual: {driver.current_url}')
                    print(f'[PAGAMENTO] Total de abas: {len(driver.window_handles)}')
                    
                    # Tentar verificar todas as abas abertas
                    try:
                        for i, aba in enumerate(driver.window_handles):
                            driver.switch_to.window(aba)
                            if log:
                                print(f'[PAGAMENTO] Aba {i+1}: {driver.current_url}')
                            if '/cadastro' in driver.current_url or 'pagamento' in driver.current_url:
                                if log:
                                    print(f'[PAGAMENTO] ✅ Encontrada aba de pagamentos!')
                                return True
                    except:
                        pass
                        
                return False
                
        except Exception as e:
            if log:
                print(f'[PAGAMENTO][ERRO] Erro geral na navegação para pagamentos: {e}')
            return False

    def pagamento_previa(driver, log=True):
        """
        Executa análise prévia de pagamentos para identificar alvarás já registrados.
        Esta função é chamada ANTES do processamento individual dos alvarás.
        
        Args:
            driver: WebDriver do Selenium
            log: Se deve exibir logs
            
        Returns:
            list: Lista de alvarás já registrados nos pagamentos
        """
        try:
            import time
            from datetime import datetime
            
            if log:
                print('[PAGAMENTO-PREVIA] Iniciando análise prévia de pagamentos...')

            # Navegar para a página de pagamentos via interface
            if not navegar_para_pagamentos(driver, log):
                if log:
                    print('[PAGAMENTO-PREVIA][ERRO] Falha na navegação para pagamentos')
                return []

            # Analisar a listagem de pagamentos
            pagamentos_encontrados = analisar_listagem_pagamentos(driver, log)
            
            # Criar lista de "alvarás registrados" baseada nos pagamentos
            alvaras_registrados = []
            
            for pagamento in pagamentos_encontrados:
                alvara_registrado = {
                    'data_expedicao': pagamento.get('data_pagamento'),
                    'valor': formatar_valor_brasileiro(pagamento.get('valor_total', 0.0)),
                    'beneficiario': 'Identificado via pagamento',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'ALVARA_REGISTRADO',
                    'origem': 'pagamento_previo',
                    'credito_demandante': pagamento.get('credito_demandante')
                }
                alvaras_registrados.append(alvara_registrado)
                
                if log:
                    print(f'[PAGAMENTO-PREVIA] ✅ Alvará registrado identificado: {pagamento.get("data_pagamento")} - {pagamento.get("credito_demandante")}')
            
            # Salvar os alvarás registrados no arquivo
            if alvaras_registrados:
                salvar_alvaras_registrados(alvaras_registrados, log)
            
            if log:
                print(f'[PAGAMENTO-PREVIA] ✅ Análise concluída. {len(alvaras_registrados)} alvarás já registrados identificados.')
            
            return alvaras_registrados
            
        except Exception as e:
            if log:
                print(f'[PAGAMENTO-PREVIA][ERRO] Erro na análise prévia: {e}')
            return []

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

    def salvar_alvaras_registrados(alvaras_registrados, log=True):
        """
        Salva a lista de alvarás já registrados no arquivo alvaras.js
        
        Args:
            alvaras_registrados: Lista de alvarás identificados nos pagamentos
            log: Se deve exibir logs
        """
        try:
            from datetime import datetime
            import json
            import os
            
            arquivo_path = os.path.join(os.getcwd(), 'alvaras.js')
            
            # Ler arquivo existente ou começar com lista vazia
            dados_existentes = ler_alvaras_arquivo(log) or []
            
            # Adicionar os novos alvarás registrados
            dados_existentes.extend(alvaras_registrados)
            
            # Salvar arquivo JS atualizado
            conteudo_js = f"""// Dados de alvarás extraídos automaticamente
// Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

const alvaras = {json.dumps(dados_existentes, indent=2, ensure_ascii=False)};

// Função para buscar alvarás por período
function buscarAlvarasPorPeriodo(dataInicio, dataFim) {{
    return alvaras.filter(alvara => {{
        const data = new Date(alvara.data_expedicao.split('/').reverse().join('-'));
        const inicio = new Date(dataInicio);
        const fim = new Date(dataFim);
        return data >= inicio && data <= fim;
    }});
}}

// Função para calcular total de valores
function calcularTotalAlvaras(lista = alvaras) {{
    return lista.reduce((total, alvara) => {{
        const valor = parseFloat(alvara.valor.replace(/[R$\s.]/g, '').replace(',', '.'));
        return total + (isNaN(valor) ? 0 : valor);
    }}, 0);
}}

// Função para buscar alvarás registrados
function buscarAlvarasRegistrados() {{
    return alvaras.filter(alvara => alvara.status === 'ALVARA_REGISTRADO');
}}

console.log(`Total de alvarás registrados: ${{alvaras.length}}`);
"""
            
            with open(arquivo_path, 'w', encoding='utf-8') as f:
                f.write(conteudo_js)
            
            if log:
                print(f'[PAGAMENTO-PREVIA] Alvarás registrados salvos em: {arquivo_path}')
                print(f'[PAGAMENTO-PREVIA] Total de {len(alvaras_registrados)} alvarás registrados adicionados')
        
        except Exception as e:
            if log:
                print(f'[PAGAMENTO-PREVIA][ERRO] Erro ao salvar alvarás registrados: {e}')

    def formatar_valor_brasileiro(valor_float):
        """
        Formata um valor float para o padrão brasileiro (R$ X.XXX,XX)
        
        Args:
            valor_float: Valor em float
            
        Returns:
            str: Valor formatado
        """
        try:
            valor_str = f"{valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"R$ {valor_str}"
        except:
            return "R$ 0,00"

    def verificar_se_alvara_ja_registrado(doc_alvara, alvaras_ja_registrados, log=True):
        """
        Verifica se um alvará da timeline já foi registrado nos pagamentos.
        
        Args:
            doc_alvara: Documento de alvará da timeline
            alvaras_ja_registrados: Lista de alvarás já registrados nos pagamentos
            log: Se deve exibir logs
            
        Returns:
            bool: True se já foi registrado, False caso contrário
        """
        try:
            if not alvaras_ja_registrados or len(alvaras_ja_registrados) == 0:
                return False
            
            # Extrair data do alvará da timeline para comparação
            data_alvara = doc_alvara.get('data', '')
            
            # Verificar se existe correspondência com os alvarás registrados
            for alvara_registrado in alvaras_ja_registrados:
                data_registrado = alvara_registrado.get('data_expedicao', '')
                
                # Comparar datas (formato DD/MM/YYYY)
                if data_alvara and data_registrado and data_alvara == data_registrado:
                    if log:
                        print(f'[LISTA-EXEC] 🎯 Correspondência encontrada: {data_alvara} = {data_registrado}')
                    return True
            
            return False
            
        except Exception as e:
            if log:
                print(f'[LISTA-EXEC][ERRO] Erro ao verificar registro de alvará: {e}')
            return False

    def ler_alvaras_arquivo(log=True):
        """
        Lê os dados existentes do arquivo alvaras.js
        
        Args:
            log: Se deve exibir logs
            
        Returns:
            list: Lista de alvarás do arquivo ou lista vazia
        """
        try:
            import os
            import json
            import re
            
            arquivo_path = os.path.join(os.getcwd(), 'alvaras.js')
            
            if not os.path.exists(arquivo_path):
                if log:
                    print('[ALVARAS] Arquivo alvaras.js não encontrado - criando novo')
                return []
            
            with open(arquivo_path, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            # Extrair o array JSON do arquivo JS
            match = re.search(r'const alvaras = (\[.*?\]);', conteudo, re.DOTALL)
            if match:
                json_str = match.group(1)
                dados = json.loads(json_str)
                if log:
                    print(f'[ALVARAS] {len(dados)} alvarás carregados do arquivo')
                return dados
            else:
                if log:
                    print('[ALVARAS] Formato inválido no arquivo - iniciando lista vazia')
                return []
                
        except Exception as e:
            if log:
                print(f'[ALVARAS][ERRO] Erro ao ler arquivo: {e}')
            return []

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
            from datetime import datetime
            
            # Converter datas
            try:
                alvara_date = datetime.strptime(alvara_data, '%d/%m/%Y')
                pagamento_date = datetime.strptime(pagamento_data, '%d/%m/%Y')
                
                # Calcular diferença em dias
                diferenca_dias = abs((alvara_date - pagamento_date).days)
                
            except:
                # Se não conseguir converter, considerar como não correspondente
                if log:
                    print(f'[CORRESPONDENCIA][AVISO] Erro ao converter datas: {alvara_data} / {pagamento_data}')
                return False
            
            # Calcular diferença de valores
            diferenca_valor = abs(alvara_valor - pagamento_valor)
            
            # Verificar critérios
            data_ok = diferenca_dias <= 5
            valor_ok = diferenca_valor <= 300.0
            
            if log and (data_ok and valor_ok):
                print(f'[CORRESPONDENCIA] ✅ Correspondência encontrada: Data {diferenca_dias} dias, Valor R$ {diferenca_valor:.2f}')
            
            return data_ok and valor_ok
            
        except Exception as e:
            if log:
                print(f'[CORRESPONDENCIA][ERRO] Erro na verificação de correspondência: {e}')
            return False

    def verificar_serasa_em_anexos_rapido(driver, documentos_com_anexos, log=True):
        """
        Verificação rápida de SERASA em anexos - apenas verifica sem processar.
        
        Args:
            driver: WebDriver do Selenium
            documentos_com_anexos: Lista de documentos com anexos
            log: Se deve exibir logs
            
        Returns:
            bool: True se encontrou SERASA em anexos
        """
        try:
            import time
            for doc in documentos_com_anexos:
                # Verificação rápida sem clicar
                btn_anexos = doc['item'].find_elements(By.CSS_SELECTOR, 'pje-timeline-anexos > div > div')
                if btn_anexos:
                    # Clicar rapidamente para verificar
                    driver.execute_script("arguments[0].click();", btn_anexos[0])
                    time.sleep(1)
                    
                    # Buscar anexos
                    anexos = driver.find_elements(By.CSS_SELECTOR, ".tl-item-anexo")
                    for anexo in anexos:
                        if 'serasa' in anexo.text.lower():
                            if log:
                                print('[LISTA-EXEC] 🔍 SERASA encontrado em anexos - não processará timeline')
                            return True
            
            return False
        except Exception as e:
            if log:
                print(f'[LISTA-EXEC][ERRO] Erro na verificação rápida de SERASA: {e}')
            return False

    def criar_medida_basica(doc):
        """
        Cria uma medida básica para o retorno da função.
        
        Args:
            doc: Documento catalogado
            
        Returns:
            dict: Medida básica formatada
        """
        return {
            'nome': doc['item_alvo']['nome'],
            'texto': doc['texto_original'], 
            'data': doc['data'],
            'id': doc['id_timeline'],
            'elemento': doc['item'],
            'link': doc['link'],
            'index': doc['index'],
            'tipo_item': 'documento'
        }

    def tratar_timeline(driver, itens_alvo, log=True):
        """
        Versão HÍBRIDA: Injeta JavaScript para ler a timeline rapidamente e retorna os dados para o Python processar.
        """
        try:
            if log:
                print('[LISTA-EXEC] 🚀 Injetando script JS para leitura INSTANTÂNEA da timeline...')

            # Script JavaScript para extrair dados da timeline
            script_js = """
            const itens_alvo = arguments[0];
            const resultados = [];
            const itens_timeline = document.querySelectorAll('li.tl-item-container');

            itens_timeline.forEach((item, index) => {
                try {
                    const link = item.querySelector('a.tl-documento:not([target="_blank"])');
                    if (!link) return;

                    const textoCompleto = link.innerText.trim();
                    const textoLower = textoCompleto.toLowerCase();
                    
                    // Extrair data
                    let data = '';
                    const dataEl = item.querySelector('.data-producao-documento');
                    if (dataEl) {
                        data = dataEl.innerText.trim();
                    }

                    // Extrair ID
                    let id = null;
                    if (textoCompleto.includes(' - ')) {
                        id = textoCompleto.split(' - ').pop().trim();
                    }

                    for (const alvo of itens_alvo) {
                        for (const termo of alvo.termos) {
                            if (textoLower.includes(termo)) {
                                // Encontrou uma correspondência
                                resultados.push({
                                    'nome': alvo.nome,
                                    'tipo': alvo.tipo,
                                    'texto_original': textoCompleto,
                                    'data': data,
                                    'id_timeline': id,
                                    'index': index,
                                    'tem_anexos': item.querySelector('pje-timeline-anexos') !== null
                                });
                                // Pula para o próximo item da timeline para não duplicar
                                return; 
                            }
                        }
                    }
                } catch (e) {
                    // Ignora erros em itens individuais
                }
            });

            return JSON.stringify(resultados);
            """

            # Executar o script e obter o resultado como uma string JSON
            json_resultados = driver.execute_script(script_js, itens_alvo)

            if not json_resultados:
                if log:
                    print('[LISTA-EXEC] ❌ Script JS não retornou dados.')
                return []

            # Converter a string JSON de volta para uma lista de dicionários Python
            import json
            documentos_encontrados = json.loads(json_resultados)

            if log:
                print(f'[LISTA-EXEC] ✅ Leitura via JS concluída INSTANTANEAMENTE. {len(documentos_encontrados)} itens relevantes encontrados.')

            return documentos_encontrados

        except Exception as e:
            if log:
                print(f'[LISTA-EXEC][ERRO-JS] Falha ao executar script de injeção: {e}')
            return []
    
    def extrair_id_timeline(item):
        """Extrai o ID da timeline de um item a partir do texto do link"""
        try:
            # Buscar o link do documento dentro do item
            links = item.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            if links:
                texto_completo = links[0].text.strip()
                
                # Extrair ID do padrão "texto - CÓDIGO_ID"
                if ' - ' in texto_completo:
                    partes = texto_completo.split(' - ')
                    if len(partes) >= 2:
                        id_extraido = partes[-1].strip()  # Pegar a última parte após o último ' - '
                        if id_extraido:
                            return id_extraido
            
            # Fallback: buscar em outros elementos
            texto_item = item.text.strip()
            if ' - ' in texto_item:
                partes = texto_item.split(' - ')
                if len(partes) >= 2:
                    id_extraido = partes[-1].strip().split()[0]  # Primeira palavra da última parte
                    if id_extraido:
                        return id_extraido
            
            # Fallback final: gerar ID baseado no hash do texto
            return f"timeline-{hash(item.text[:50]) % 1000000}"
        except:
            return f"timeline-{int(time.time()) % 1000000}"

    def gerar_gigs_final(driver, dados_gigs_final, log=True):
        """
        Gera o GIGS final consolidado com todas as medidas relevantes.
        
        Args:
            driver: WebDriver do Selenium
            dados_gigs_final: Estrutura com todos os dados coletados
            log: Se deve exibir logs
        """
        try:
            if log:
                print('[GIGS-FINAL] Gerando GIGS consolidado...')
            
            # Importar função criar_gigs
            from Fix import criar_gigs
            
            # Construir texto do GIGS
            texto_gigs = []
            
            # SEÇÃO 1: Alvarás sem registro
            if dados_gigs_final['alvaras_sem_registro']:
                texto_gigs.append("ALVARÁS:")
                for alvara in dados_gigs_final['alvaras_sem_registro']:
                    linha_alvara = f"{alvara['id']}, {alvara['data']}, {alvara['valor']}"
                    texto_gigs.append(linha_alvara)
                texto_gigs.append("")  # Linha em branco
            
            # SEÇÃO 2: Pesquisas (CNIB e SERASA agrupados)
            pesquisas = []
            pesquisas.extend(dados_gigs_final['cnib_anexos'])
            pesquisas.extend(dados_gigs_final['serasa_anexos'])
            
            if pesquisas:
                texto_gigs.append("PESQUISAS:")
                for pesquisa in pesquisas:
                    texto_gigs.append(f"ID {pesquisa}")
                texto_gigs.append("")  # Linha em branco
            
            # SEÇÃO 3: Sobrestamentos
            if dados_gigs_final['sobrestamentos']:
                for sobrestamento in dados_gigs_final['sobrestamentos']:
                    linha_sobrestamento = f"Sobrestamento ID {sobrestamento['id']} de {sobrestamento['data']}"
                    texto_gigs.append(linha_sobrestamento)
                texto_gigs.append("")  # Linha em branco
            
            # Juntar tudo em um texto único
            observacao_final = "\n".join(texto_gigs).strip()
            
            if not observacao_final:
                if log:
                    print('[GIGS-FINAL] Nenhuma medida relevante encontrada para o GIGS.')
                return None
            
            if log:
                print(f'[GIGS-FINAL] Texto do GIGS:\n{observacao_final}')
            
            # Criar GIGS com dias_uteis=0 e responsavel vazio
            resultado = criar_gigs(
                driver=driver,
                dias_uteis=0,
                responsavel="",
                observacao=observacao_final,
                timeout=10,
                log=log
            )
            
            if log:
                if resultado:
                    print('[GIGS-FINAL] ✅ GIGS final criado com sucesso!')
                else:
                    print('[GIGS-FINAL] ❌ Falha ao criar GIGS final.')
            
            return resultado
            
        except Exception as e:
            if log:
                print(f'[GIGS-FINAL][ERRO] Erro ao gerar GIGS final: {e}')
            return None

    try:
        from selenium.webdriver.common.by import By
        import time
        
        medidas = []
        alvaras_encontrados = []
        serasa_gigs_gerado = False
        
        # ESTRUTURAS PARA GIGS FINAL
        dados_gigs_final = {
            'alvaras_sem_registro': [],  # {'id_timeline': 'xxx', 'data': 'dd/mm/yyyy', 'valor': 'R$ xxx,xx'}
            'cnib_anexos': [],           # ['id1', 'id2', 'id3']
            'serasa_anexos': [],         # ['id1', 'id2', 'id3']
            'sobrestamentos': []         # {'id_timeline': 'xxx', 'data': 'dd/mm/yyyy'}
        }

        # Definição dos itens a serem buscados - FILTRO ESPECÍFICO CORRIGIDO
        itens_alvo = [
            {
                'nome': 'Alvará', 
                'termos': ['alvará', 'alvara'],
                'tipo': 'documento_individual'
            },
            {
                'nome': 'Certidão de oficial de justiça', 
                'termos': ['certidão de oficial de justiça', 'certidao de oficial de justica', 'oficial de justiça', 'oficial de justica'],
                'tipo': 'documento_com_anexos',
                'anexos_interesse': ['cnib', 'serasa']
            },
            {
                'nome': 'Certidão de pesquisa patrimonial', 
                'termos': ['certidão de pesquisa patrimonial', 'certidao de pesquisa patrimonial', 'pesquisa patrimonial'],
                'tipo': 'documento_com_anexos',
                'anexos_interesse': ['cnib', 'serasa']
            },
            {
                'nome': 'Serasa', 
                'termos': ['serasa'],
                'tipo': 'documento_condicional_gigs'  # Só gera GIGS se não houver SERASA em anexos
            },
            {
                'nome': 'Sobrestamento', 
                'termos': ['sobrestamento'],
                'tipo': 'documento_deteccao'  # Apenas detectar
            }
        ]
        
        # --- FASE 1: Análise da Timeline ---
        if log:
            print('[LISTA-EXEC] Iniciando Fase 1: Análise da Timeline...')
        
        # A função tratar_timeline agora usa JS e retorna uma lista de documentos brutos
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
                alvaras_encontrados.append(doc)  # Para a fase de pagamentos
            elif doc['nome'] == 'Sobrestamento':
                sobrestamentos_detectados.append(doc)
            elif 'Certidão' in doc['nome'] and doc['tem_anexos']:
                certidoes_com_anexos.append(doc)
            elif doc['nome'] == 'Serasa':
                serasa_timeline.append(doc)

        # --- NOVO FLUXO CORRETO ---
        # 1. Se há alvarás, primeiro ir aos pagamentos e armazenar resultado
        pagamentos_encontrados = []
        alvaras_processados_individuais = []  # Lista para armazenar alvarás processados
        
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
                            # Fechar aba atual (pagamentos)
                            driver.close()
                            # Voltar para primeira aba
                            driver.switch_to.window(todas_abas[0])
                        else:
                            # Se não há múltiplas abas, navegar de volta
                            driver.get(url_original)
                        
                        time.sleep(2)
                        if log:
                            print(f'[LISTA-EXEC] ✅ Retornado à aba original: {driver.current_url}')
                    except Exception as e:
                        if log:
                            print(f'[LISTA-EXEC][ERRO] Erro ao retornar à aba original: {e}')
                        # Fallback: navegar pela URL
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
                seletores_timeline = [
                    'li.tl-item-container',
                    '.tl-data .tl-item-container', 
                    '.timeline-item'
                ]
                
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
                        
                        # PROCESSAR O ALVARÁ INDIVIDUALMENTE (chamar função alvara correta)
                        resultado_alvara = alvara(driver, item_alvara, link_alvara, data_alvara, log)
                        
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
        # A implementação de processar_anexos_certidoes seria chamada aqui
        # Por enquanto, vamos apenas simular a extração de IDs
        for certidao in certidoes_com_anexos:
             # Simulação: se encontrasse CNIB ou SERASA, adicionaria o ID
            dados_gigs_final['cnib_anexos'].append(certidao['id_timeline'] or f"certidao-{certidao['index']}") 

        # Prioridade 4: SERASA da timeline (se não houver SERASA de anexos)
        if not dados_gigs_final['serasa_anexos']:
            for serasa in serasa_timeline:
                # Aqui iria a lógica de gerar o GIGS individual de SERASA
                # Por enquanto, vamos apenas registrar
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