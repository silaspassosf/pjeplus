import re
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from Fix import extrair_documento, criar_gigs

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
        
        Args:
            driver: WebDriver do Selenium
            item: Elemento da timeline
            link: Link do documento
            data: Data do alvará
            log: Se deve exibir logs
        """
        try:
            if log:
                print(f'[ALVARA] Processando alvará: {link.text.strip()}')
            
            # a) Selecionar o documento
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
            driver.execute_script("arguments[0].click();", link)
            
            if log:
                print('[ALVARA] Documento selecionado, aguardando carregamento...')
            
            import time
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
                # Salvar em alvaras.js
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
            
            # 1. Extrair data de expedição (formato dd/mm/aaaa)
            # Padrões de busca para data de expedição
            padroes_data = [
                r'expedi[çc]ão[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'expedido em[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'data[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'em[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'  # Qualquer data no formato
            ]
            
            for padrao in padroes_data:
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
                print(f'[ALVARA] Data: {dados["data_expedicao"]}, Valor: {dados["valor"]}, Beneficiário: {dados["beneficiario"]}')
        
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
    
    try:
        if log:
            print('[LISTA-EXEC] Iniciando análise da timeline...')
        
        # Verificar se estamos na URL correta
        if '/detalhe' not in driver.current_url:
            if log:
                print('[LISTA-EXEC][ERRO] URL não contém /detalhe')
            return []
        
        # Buscar itens da timeline
        seletores_timeline = [
            'li.tl-item-container',
            '.tl-data .tl-item-container',
            '.timeline-item'
        ]
        
        itens = []
        for seletor in seletores_timeline:
            itens = driver.find_elements(By.CSS_SELECTOR, seletor)
            if itens:
                if log:
                    print(f'[LISTA-EXEC] Encontrados {len(itens)} itens com seletor: {seletor}')
                break
        
        if not itens:
            if log:
                print('[LISTA-EXEC][ERRO] Nenhum item encontrado na timeline')
            return []
        
        medidas = []
        
        # Itens a serem filtrados
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
            {'nome': 'CENSEC', 'termos': ['censec']},
            {'nome': 'Alvará', 'termos': ['alvará', 'alvara']}  # Adicionado alvará
        ]
        
        for index, item in enumerate(itens):
            try:
                # Verificar documento principal
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                
                if link:
                    texto_doc = link.text.strip().lower()
                    
                    for item_alvo in itens_alvo:
                        encontrado = any(termo in texto_doc for termo in item_alvo['termos'])
                        if encontrado:
                            # Extrair data usando JavaScript (simulação)
                            data = f"{index+1:02d}/01/2024"  # Placeholder - em implementação real usaria JavaScript
                            
                            uid = f"doc-{index}"
                            
                            medida = {
                                'nome': item_alvo['nome'],
                                'texto': link.text.strip(),
                                'data': data,
                                'id': uid,
                                'elemento': item,
                                'link': link,
                                'index': index,
                                'tipo_item': 'documento'
                            }
                            
                            medidas.append(medida)
                            
                            if log:
                                print(f'[LISTA-EXEC] ✅ {item_alvo["nome"]}: {link.text.strip()} ({data})')
                            
                            # Se for alvará, chamar função específica
                            if item_alvo['nome'] == 'Alvará':
                                if log:
                                    print('[LISTA-EXEC] 📋 Alvará encontrado, processando...')
                                alvara(driver, item, link, data, log)
                            
                            # Se for Serasa na timeline principal, gerar GIGS
                            elif item_alvo['nome'] == 'Serasa':
                                if log:
                                    print('[LISTA-EXEC] 🎯 Serasa encontrado na timeline, gerando GIGS...')
                                gigs_resultado = gerar_gigs_serasa(driver, item, link, data, log)
                                if gigs_resultado:
                                    # Adicionar informação do GIGS à medida
                                    medida['gigs_gerado'] = gigs_resultado
                            
                            break  # Sair do loop após encontrar a primeira correspondência
                
                # Verificar se precisa buscar em anexos (apenas para certidão de oficial de justiça ou pesquisa patrimonial)
                if link:
                    texto_doc = link.text.strip().lower()
                    deve_buscar_anexos = any(termo in texto_doc for termo in ['certidão de oficial de justiça', 'certidao de oficial de justica', 'pesquisa patrimonial'])
                    
                    if deve_buscar_anexos:
                        medidas_anexos = buscar_termos_em_anexos(driver, item, index, itens_alvo, log)
                        if medidas_anexos:
                            medidas.extend(medidas_anexos)
                
            except Exception as e:
                if log:
                    print(f'[LISTA-EXEC][ERRO] Erro ao processar item {index}: {e}')
                continue
        
        if log:
            print(f'[LISTA-EXEC] Total de medidas encontradas: {len(medidas)}')
        
        return medidas
        
    except Exception as e:
        if log:
            print(f'[LISTA-EXEC][ERRO] Erro geral na função: {e}')
        return []

# Exemplo de uso:
# medidas = listaexec(driver, log=True)
