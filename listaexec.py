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
            if log:
                print(f'[ALVARA] Processando alvará: {link.text.strip()}')
            
            # a) Selecionar o documento
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
            driver.execute_script("arguments[0].click();", link)
            
            if log:
                print('[ALVARA] Documento selecionado, aguardando carregamento...')
            
            time.sleep(2)  # Aguarda carregamento do documento
            
            # b) Chamar extrair documento de fix.py
            try:
                texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
                if texto_tuple and texto_tuple[0]:
                    texto = texto_tuple[0]
                    if log:
                        print(f'[ALVARA] Texto extraído: {len(texto)} caracteres')
                else:
                    if log:
                        print('[ALVARA][ERRO] extrair_documento retornou None ou texto vazio')
                    return None
            except Exception as e_extrair:
                if log:
                    print(f'[ALVARA][ERRO] Erro ao extrair documento: {e_extrair}')
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
            
            # NOVA REGRA: Verificar se contém "3011" no texto
            contem_3011 = '3011' in texto
            
            if contem_3011:
                # Modelo com data de atualização (contém 3011)
                # Buscar data de atualização no texto
                padroes_data_atualizacao = [
                    r'atualiza[çc]ão[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                    r'atualizado em[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                    r'data[:\s]*de[:\s]*atualiza[çc]ão[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                    r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'  # Qualquer data no formato como fallback
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
                
                # Se não encontrou data de atualização específica, usar a primeira data encontrada
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
            
            # 2. Extrair valor (formato monetário)
            padroes_valor = [
                r'valor[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'quantia[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'import[aâ]ncia[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                r'(\d{1,3}(?:\.\d{3})*,\d{2})'  # Formato brasileiro
            ]
            
            for padrao in padroes_valor:
                matches = re.findall(padrao, texto, re.IGNORECASE)
                if matches:
                    # Pegar o maior valor encontrado (assumindo que é o principal)
                    valores = [converter_valor_para_float(v) for v in matches]
                    valor_maximo = max(valores)
                    dados['valor'] = formatar_valor_brasileiro(valor_maximo)
                    if log:
                        print(f'[ALVARA] Valor encontrado: {dados["valor"]}')
                    break
            
            # 3. Extrair beneficiário
            padroes_beneficiario = [
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
                            print(f'[ALVARA] Beneficiário encontrado: {beneficiario}')
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
            # Padrões para encontrar o autor do processo
            padroes_autor = [
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
                            print(f'[ALVARA] Autor do processo encontrado: {autor}')
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
    
    def extrair_data_item(item):
        """Extrai data do item da timeline"""
        try:
            # Buscar elemento .tl-data
            data_element = item.querySelector('.tl-data[name="dataItemTimeline"]')
            if not data_element:
                data_element = item.querySelector('.tl-data')
            
            # Se não encontrou, buscar em elementos anteriores
            if not data_element:
                elemento_anterior = item.previousElementSibling
                while elemento_anterior:
                    data_element = elemento_anterior.querySelector('.tl-data')
                    if data_element:
                        break
                    elemento_anterior = elemento_anterior.previousElementSibling
            
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
            
            # Usar o seletor correto da função tratar_anexos_argos
            btn_anexos = item.find_elements(By.CSS_SELECTOR, "pje-timeline-anexos > div > div")
            
            if btn_anexos:
                if log:
                    print(f'[LISTA-EXEC][ANEXOS] Encontrado botão de anexos, clicando...')
                
                # Clicar no botão de anexos
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_anexos[0])
                driver.execute_script("arguments[0].click();", btn_anexos[0])
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
    
    def tratar_timeline(driver, itens_alvo, log=True):
        """
        Trata a timeline principal, buscando e processando itens de interesse.
        
        Args:
            driver: WebDriver do Selenium
            itens_alvo: Lista de itens a serem buscados na timeline
            log: Se deve exibir logs
        """
        nonlocal serasa_gigs_gerado  # Acessar a flag da função externa
        
        try:
            # Obter todos os itens da timeline
            itens = driver.find_elements(By.CSS_SELECTOR, 'pje-timeline-item')
            
            for index, item in enumerate(itens):
                try:
                    texto_item = item.text.strip().lower()
                    links = item.find_elements(By.CSS_SELECTOR, 'a[name="juntadaDocumento"]')
                    
                    if not links:
                        continue

                    link = links[0]
                    data = extrair_data_item(item)

                    for item_alvo in itens_alvo:
                        encontrado = any(termo in texto_item for termo in item_alvo['termos'])
                        
                        if encontrado:
                            medida = {
                                'nome': item_alvo['nome'],
                                'texto': link.text.strip(),
                                'data': data,
                                'id': link.get_attribute('id'),
                                'elemento': link,
                                'index': index,
                                'tipo_item': 'documento'
                            }
                            medidas.append(medida)
                            
                            if log:
                                print(f'[LISTA-EXEC] ✅ {item_alvo["nome"]} encontrado: {link.text.strip()} em {data}')
                            
                            # Lógica específica para cada tipo de item
                            if item_alvo['nome'] == 'Alvará':
                                dados_alvara = alvara(driver, item, link, data, log)
                                if dados_alvara:
                                    alvaras_encontrados.append(dados_alvara)
                            
                            elif item_alvo['nome'] == 'Serasa':
                                if not serasa_gigs_gerado:
                                    gerar_gigs_serasa(driver, item, link, data, log)
                                    serasa_gigs_gerado = True
                                    if log:
                                        print('[LISTA-EXEC] GIGS para Serasa solicitado (primeira ocorrência).')
                                else:
                                    if log:
                                        print('[LISTA-EXEC] Item "Serasa" subsequente encontrado. GIGS já foi gerado.')

                            elif item_alvo['nome'] == 'Certidão de pesquisa patrimonial':
                                medidas_anexos = buscar_termos_em_anexos(driver, item, index, itens_alvo, log)
                                if medidas_anexos:
                                    medidas.extend(medidas_anexos)
                        
                        item_encontrado = True
                        break
                    
                    if not item_encontrado and log:
                        print(f'[LISTA-EXEC] Nenhum termo de interesse no item {index}: {texto_item[:100]}...')

                except Exception as e:
                    if log:
                        print(f'[LISTA-EXEC][ERRO] Erro ao processar item {index}: {e}')
                    continue
        
        except Exception as e:
            if log:
                print(f'[LISTA-EXEC][ERRO] Erro geral na função tratar_timeline: {e}')
    
    try:
        medidas = []
        alvaras_encontrados = []
        serasa_gigs_gerado = False

        # Definição dos itens a serem buscados
        itens_alvo = [
            {'nome': 'Alvará', 'termos': ['alvará', 'alvara']},
            {'nome': 'Serasa', 'termos': ['serasa']},
            {'nome': 'Sisbajud', 'termos': ['sisbajud', 'bacenjud']},
            {'nome': 'Infojud', 'termos': ['infojud']},
            {'nome': 'Renajud', 'termos': ['renajud']},
            {'nome': 'Penhora', 'termos': ['penhora', 'constrição']},
            {'nome': 'Certidão de pesquisa patrimonial', 'termos': ['pesquisa patrimonial', 'certidão de oficial de justiça']}
        ]
        
        # --- FASE 1: Análise da Timeline ---
        if log:
            print('[LISTA-EXEC] Iniciando Fase 1: Análise da Timeline...')
        tratar_timeline(driver, itens_alvo, log)
        
        # --- FASE 2: Processamento de Pagamentos (Após varrer a timeline) ---
        if alvaras_encontrados:
            if log:
                print('[LISTA-EXEC] Iniciando Fase 2: Processamento de Pagamentos...')
            try:
                # Navegar para a página de pagamentos
                url_pagamentos = "https://pje.trt4.jus.br/pje-comprovante-pagamento/pagamento/list"
                driver.get(url_pagamentos)
                import time
                time.sleep(3) # Aguardar carregamento

                # Chamar a função de pagamento (que agora opera sobre o arquivo)
                pagamento(driver, log)

            except Exception as e:
                if log:
                    print(f'[LISTA-EXEC][ERRO] Falha na fase de processamento de pagamentos: {e}')

        if log:
            print(f'[LISTA-EXEC] Análise da timeline concluída. {len(medidas)} medidas encontradas.')
            
        return medidas
        
    except Exception as e:
        if log:
            print(f'[LISTA-EXEC][ERRO] Erro geral na função: {e}')
        return []