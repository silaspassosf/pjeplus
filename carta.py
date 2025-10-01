from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re

def carta(driver, log=True, limite_intimacoes=None):
    """
    Função principal para processar intimações de carta no PJe
    """
    # 1. Extrair dados do processo via API para obter o número do processo
    from Fix import extrair_dados_processo
    dados_processo = extrair_dados_processo(driver, caminho_json=None, debug=log)

    if not dados_processo:
        if log:
            print("[CARTA][ERRO] Não foi possível extrair dados do processo via API")
        return None

    # Extrair número do processo dos dados da API
    process_number = dados_processo.get("numero")
    if not process_number:
        if log:
            print("[CARTA][ERRO] Número do processo não encontrado nos dados da API")
        return None

    if log:
        print(f"[CARTA] Número do processo extraído via API: {process_number}")
    
    # 2. Buscar intimações na timeline do PJe
    intimation_ids = []
    if log:
        print("[CARTA] Iniciando busca de intimações na timeline...")
    
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    if log:
        print(f"[CARTA] Encontrados {len(itens)} itens na timeline")
    
    # Variável para controlar se encontramos intimação de correio
    intimacao_encontrada = False
    continue_busca = False  # Controla se deve continuar buscando outras intimações
    data_referencia = None  # Data da primeira intimação encontrada
    
    # Verificar apenas o primeiro item para ver se é intimação
    if itens:
        primeiro_item = itens[0]
        primeiro_item_text = primeiro_item.text.lower()
        
        if log:
            print(f"[CARTA] Primeiro item da timeline: {primeiro_item_text[:100]}...")
        
        # Se o primeiro item contém "intimação", verifica se é de correio
        if 'intimação' in primeiro_item_text or 'intimacao' in primeiro_item_text:
            if log:
                print("[CARTA] Intimação detectada no primeiro item - verificando se é de correio")
            
            try:
                link = primeiro_item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                aria = link.get_attribute('aria-label') or ''
                
                if log:
                    print(f"[CARTA] Clicando na intimação: {link.text}")
                
                link.click()
                time.sleep(2)
                
                # Extrair conteúdo usando extrair_direto com log de conteúdo
                from Fix import extrair_direto
                resultado_extracao = extrair_direto(driver, timeout=10, debug=log)
                
                if not resultado_extracao.get('sucesso', False):
                    if log:
                        print("[CARTA][DEBUG] Não foi possível extrair conteúdo da intimação")
                    continue_busca = True  # Continua buscando outras
                
                if not continue_busca:
                    texto_completo = resultado_extracao.get('conteudo', '').lower()
                    if log:
                        print(f"[CARTA][DEBUG] Conteúdo extraído com sucesso ({len(texto_completo)} chars)")
                        if log and len(texto_completo) > 0:
                            # Log das primeiras linhas para debug
                            linhas = texto_completo.split('\n')[:5]
                            print("[CARTA][DEBUG] Primeiras linhas do conteúdo:")
                            for i, linha in enumerate(linhas, 1):
                                print(f"[CARTA][DEBUG]   {i}: {linha[:100]}{'...' if len(linha) > 100 else ''}")
                    
                    # Extrair data da intimação para usar como referência
                    linhas = texto_completo.split('\n')
                    for linha in linhas:
                        linha_strip = linha.strip()
                        if 'reg.' in linha_strip.lower():
                            # Tentar extrair data da linha REG (formato: "...reg. sao paulo/sp, 11 de setembro de 2025...")
                            import re
                            data_match = re.search(r'reg\.\s*[^,]+,\s*(\d{1,2})\s+de\s+([a-zçã]+)\s+de\s+(\d{4})', linha_strip.lower())
                            if data_match:
                                dia, mes, ano = data_match.groups()
                                # Converter mês por extenso para número
                                meses = {
                                    'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
                                    'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                                    'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
                                }
                                mes_num = meses.get(mes, '01')
                                data_referencia = f"{dia.zfill(2)}/{mes_num}/{ano}"
                                if log:
                                    print(f"[CARTA][DEBUG] Data de referência extraída: {data_referencia}")
                                break
                    
                    # Verificar se temos texto válido
                    if not texto_completo or len(texto_completo.strip()) < 10:
                        if log:
                            print("[CARTA][DEBUG] Conteúdo extraído muito curto ou vazio")
                        continue_busca = True  # Continua buscando outras
                    
                    if not continue_busca:
                        # FILTRO PARA SABER SE É DE CORREIO:
                        # 1. Ler a linha com "REG."
                        # 2. Ignorar notificações que tenham "ENDEREÇO: Expediente enviado por outro meio"
                        
                        linha_reg = None
                        
                        # Procurar pela linha que contém "REG."
                        for linha in linhas:
                            linha_strip = linha.strip()
                            if 'reg.' in linha_strip.lower():
                                linha_reg = linha_strip
                                if log:
                                    print(f"[CARTA][DEBUG] Linha REG encontrada: {linha_reg}")
                                break
                        
                        # Verificar se encontrou a linha REG
                        if not linha_reg:
                            if log:
                                print("[CARTA][DEBUG] Linha com 'REG.' não encontrada - não é intimação de correio")
                            continue_busca = True  # Continua buscando outras
                        
                        if not continue_busca:
                            # Verificar se contém "ENDEREÇO: Expediente enviado por outro meio"
                            # Se contiver, ignorar pois nunca será de correio
                            endereco_outro_meio = "endereço: expediente enviado por outro meio"
                            if endereco_outro_meio in linha_reg.lower():
                                if log:
                                    print("[CARTA][DEBUG] Intimação tem 'ENDEREÇO: Expediente enviado por outro meio' - continuando busca")
                                continue_busca = True  # Continua buscando outras
                            else:
                                # Se passou pelos filtros, é intimação de correio
                                if log:
                                    print("[CARTA][DEBUG] Intimação de correio confirmada pelos filtros")
                                
                                # Extrair ID da intimação
                                link_text = link.text.strip()
                                if log:
                                    print(f"[CARTA][DEBUG] Texto do link: {link_text}")
                                
                                # Buscar padrão: "Intimação(Intimação) - CODIGO"
                                id_match = re.search(r'-\s*([a-f0-9]+)\s*$', link_text)
                                if id_match:
                                    id_curto = id_match.group(1)
                                else:
                                    # Fallback para aria-label
                                    id_match = re.search(r'Id: ([a-f0-9]+)', aria)
                                    id_curto = id_match.group(1) if id_match else primeiro_item.get_attribute('id')
                                
                                intimation_ids.append(id_curto)
                                intimacao_encontrada = True
                                
                                if log:
                                    print(f"[CARTA] ID da intimação de correio encontrado: {id_curto}")
                                    print(f"[CARTA] Número do processo: {process_number}")
            except Exception as e:
                if log:
                    print(f"[CARTA] Erro ao processar primeira intimação: {e}")
                continue_busca = True  # Continua buscando outras
    
    # Fallback: Buscar sequencialmente por intimações até encontrar uma de correio
    if not intimacao_encontrada:
        if log:
            print("[CARTA][FALLBACK] Buscando sequencialmente por intimações de correio...")
        
        count_intimacoes = 0
        limite = limite_intimacoes if limite_intimacoes is not None else float('inf')
        
        for idx, item in enumerate(itens):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                
                if 'intimação' in doc_text:
                    # Se temos data de referência, verificar se esta intimação é da mesma data
                    if data_referencia:
                        # Extrair data desta intimação para comparar
                        link_fallback = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                        link_fallback.click()
                        time.sleep(2)
                        
                        resultado_fallback = extrair_direto(driver, timeout=10, debug=False)
                        if resultado_fallback.get('sucesso', False):
                            texto_fallback = resultado_fallback.get('conteudo', '').lower()
                            linhas_fallback = texto_fallback.split('\n')
                            
                            data_atual = None
                            for linha in linhas_fallback:
                                linha_strip = linha.strip()
                                if 'reg.' in linha_strip.lower():
                                    data_match = re.search(r'reg\.\s*[^,]+,\s*(\d{1,2})\s+de\s+([a-zçã]+)\s+de\s+(\d{4})', linha_strip.lower())
                                    if data_match:
                                        dia, mes, ano = data_match.groups()
                                        meses = {
                                            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
                                            'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                                            'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
                                        }
                                        mes_num = meses.get(mes, '01')
                                        data_atual = f"{dia.zfill(2)}/{mes_num}/{ano}"
                                        break
                            
                            # Verificar se a data coincide
                            if data_atual != data_referencia:
                                if log:
                                    print(f"[CARTA][FALLBACK] Intimação do item {idx + 1} tem data {data_atual}, diferente da referência {data_referencia} - pulando")
                                continue
                    
                    count_intimacoes += 1
                    if log:
                        print(f"[CARTA][FALLBACK] Intimação encontrada no item {idx + 1}")
                    
                    if count_intimacoes > limite:
                        if log:
                            print(f"[CARTA][FALLBACK] Limite de {limite} intimações atingido")
                        break
                    
                    # Se já clicou para verificar data, não precisa clicar novamente
                    if not data_referencia:
                        link.click()
                        time.sleep(2)
                    
                    # Extrair conteúdo usando extrair_direto com log de conteúdo
                    from Fix import extrair_direto
                    resultado_extracao = extrair_direto(driver, timeout=10, debug=log)
                    
                    if not resultado_extracao.get('sucesso', False):
                        if log:
                            print(f"[CARTA][FALLBACK] Não foi possível extrair conteúdo da intimação")
                        continue
                    
                    texto_completo = resultado_extracao.get('conteudo', '').lower()
                    if log:
                        print(f"[CARTA][FALLBACK] Conteúdo extraído com sucesso ({len(texto_completo)} chars)")
                    
                    # Verificar se temos texto válido
                    if not texto_completo or len(texto_completo.strip()) < 10:
                        if log:
                            print(f"[CARTA][FALLBACK] Conteúdo extraído muito curto ou vazio")
                        continue
                    
                    # FILTRO PARA SABER SE É DE CORREIO:
                    # 1. Ler a linha com "REG."
                    # 2. Ignorar notificações que tenham "ENDEREÇO: Expediente enviado por outro meio"
                    
                    linhas = texto_completo.split('\n')
                    linha_reg = None
                    
                    # Procurar pela linha que contém "REG."
                    for linha in linhas:
                        linha_strip = linha.strip()
                        if 'reg.' in linha_strip.lower():
                            linha_reg = linha_strip
                            if log:
                                print(f"[CARTA][FALLBACK] Linha REG encontrada: {linha_reg}")
                            break
                    
                    # Verificar se encontrou a linha REG
                    if not linha_reg:
                        if log:
                            print(f"[CARTA][FALLBACK] Linha com 'REG.' não encontrada - não é intimação de correio")
                        continue
                    
                    # Verificar se contém "ENDEREÇO: Expediente enviado por outro meio"
                    # Se contiver, ignorar pois nunca será de correio
                    endereco_outro_meio = "endereço: expediente enviado por outro meio"
                    if endereco_outro_meio in linha_reg.lower():
                        if log:
                            print(f"[CARTA][FALLBACK] Intimação tem 'ENDEREÇO: Expediente enviado por outro meio' - ignorando")
                        continue
                    
                    # Se passou pelos filtros, é intimação de correio
                    correio_detectado = True
                    if log:
                        print(f"[CARTA][FALLBACK] Intimação de correio confirmada pelos filtros")
                        # Extrair ID
                        aria = link.get_attribute('aria-label') or ''
                        link_text = link.text.strip()
                        
                        id_match = re.search(r'-\s*([a-f0-9]+)\s*$', link_text)
                        if id_match:
                            id_curto = id_match.group(1)
                        else:
                            id_match = re.search(r'Id: ([a-f0-9]+)', aria)
                            id_curto = id_match.group(1) if id_match else item.get_attribute('id')
                        
                        intimation_ids.append(id_curto)
                        intimacao_encontrada = True
                        
                        if log:
                            print(f"[CARTA][FALLBACK] ✅ Intimação de correio encontrada: {id_curto}")
                        
                        break
                    else:
                        if log:
                            print(f"[CARTA][FALLBACK] Item {idx + 1} não é de correio, continuando...")
            except Exception:
                continue
    
    # Se detectou intimação de correio (intimation_ids preenchido), segue normalmente
    if not intimation_ids:
        if log:
            print("[CARTA] Nenhuma intimação de correio encontrada.")
        return ""
    # Não depende do número do processo para seguir o fluxo de correio
    
    if log:
        print(f"[CARTA] {len(intimation_ids)} intimações encontradas para processo {process_number}")
    
    # 3. Acessar eCarta em nova aba
    if log:
        print("[CARTA] Abrindo eCarta em nova aba...")
    
    original_window = driver.current_window_handle
    original_window_count = len(driver.window_handles)
    
    if log:
        print(f"[CARTA] Abas antes de abrir eCarta: {original_window_count}")
    
    ecarta_url = f"https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo={process_number}"
    driver.execute_script(f"window.open('{ecarta_url}', '_blank');")
    
    # Aguardar nova aba
    max_tentativas = 10
    for tentativa in range(max_tentativas):
        time.sleep(0.5)
        current_window_count = len(driver.window_handles)
        if current_window_count > original_window_count:
            if log:
                print(f"[CARTA] Nova aba detectada após {tentativa * 0.5:.1f}s")
            break
    else:
        if log:
            print("[CARTA] AVISO: Nova aba não foi detectada")
    
    time.sleep(2)
    
    # Mudar para a nova aba
    all_windows = driver.window_handles
    if len(all_windows) > 1:
        nova_aba = all_windows[-1]
        driver.switch_to.window(nova_aba)
        if log:
            print(f"[CARTA] Focando na nova aba: {nova_aba}")
    else:
        if log:
            print("[CARTA][ERRO] Nova aba não foi detectada")
    
    if log:
        print(f"[CARTA] Nova aba eCarta aberta: {driver.current_url}")
    
    # Validar se estamos na aba correta
    if "ecarta" not in driver.current_url.lower():
        if log:
            print(f"[CARTA][ERRO] Não estamos na aba correta do eCarta!")
            print(f"[CARTA][ERRO] URL atual: {driver.current_url}")
        return ""
    
    time.sleep(3)
    
    # 4. Login se necessário
    try:
        username_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#input_user"))
        )
        if log:
            print("[CARTA] Fazendo login no eCarta...")
        username_field.send_keys("s164283")
        driver.find_element(By.CSS_SELECTOR, "#input_password").send_keys("59Justdoit1!")
        driver.find_element(By.CSS_SELECTOR, "input.btn").click()
        time.sleep(3)
        
        # Navegar novamente para a URL após login
        driver.get(ecarta_url)
        time.sleep(3)
        if log:
            print("[CARTA] Login realizado na eCarta")
    except TimeoutException:
        if log:
            print("[CARTA] Já logado na eCarta")
    
    # 5. Extrair dados da tabela do eCarta
    table_data = []
    try:
        if log:
            print("[CARTA] Iniciando extração de dados da tabela eCarta...")
        
        correlacao_encontrada = False
        pagina_atual = 1
        max_tentativas_paginas = 10
        
        while not correlacao_encontrada and pagina_atual <= max_tentativas_paginas:
            if log:
                print(f"[CARTA] Tentativa de extração na página {pagina_atual}...")
            
            # JavaScript para extrair dados
            js_script = """
            function criarUrlDocumento(documentoId) {
                var baseUrl = window.location.origin;
                var currentPath = window.location.pathname;
                var contexto = '';
                if (currentPath.includes('/pjekz/')) {
                    contexto = '/pjekz';
                } else if (currentPath.includes('/pje/')) {
                    contexto = '/pje';
                } else {
                    contexto = '/pjekz';
                }
                if (contexto === '/pjekz') {
                    return baseUrl + '/pjekz/processo/documento/' + documentoId + '/conteudo';
                } else {
                    return baseUrl + '/pje/Processo/ConsultaDocumento/Documento.seam?doc=' + documentoId;
                }
            }
            
            function extrairDadosTabela() {
                var seletores = [
                    '#main\\\\:tabDoc_data tr',
                    '#main\\\\:tabDoc tbody tr',
                    'table[id*="tabDoc"] tr',
                    '.ui-datatable tbody tr',
                    'tbody tr'
                ];
                
                var rows = null;
                var seletorUsado = '';
                
                for (var i = 0; i < seletores.length; i++) {
                    var tempRows = Array.from(document.querySelectorAll(seletores[i]));
                    if (tempRows.length > 0) {
                        rows = tempRows;
                        seletorUsado = seletores[i];
                        break;
                    }
                }
                
                if (!rows || rows.length === 0) {
                    return null;
                }
                
                var data = rows.map(function(tr, index) {
                    var tds = tr.querySelectorAll('td');
                    
                    if (tds.length < 4) {
                        return null;
                    }
                    
                    var dataEnvio = tds[0] ? tds[0].innerText.trim() : '';
                    var dataEntrega = tds[1] ? tds[1].innerText.trim() : '';
                    var idTd = tds[3];
                    var idPje = idTd ? idTd.innerText.trim() : '';
                    var objetoTd = tds[4];
                    var objeto = objetoTd ? objetoTd.innerText.trim() : '';
                    
                    // Se não temos ID na coluna 3, tentar outras colunas
                    if (!idPje || idPje.length < 5) {
                        for (var k = 0; k < tds.length; k++) {
                            var conteudo = tds[k].innerText.trim();
                            if (/^[a-f0-9]{6,}$/.test(conteudo)) {
                                idPje = conteudo;
                                break;
                            }
                        }
                    }
                    
                    var idPjeLink = null;
                    if (idPje && /^\\d{10,}$/.test(idPje)) {
                        idPjeLink = criarUrlDocumento(idPje);
                    }
                    
                    var objetoLink = null;
                    var spanElement = objetoTd ? objetoTd.querySelector('span[id*=":rastreamento"]') : null;
                    if (spanElement) {
                        var codigoRastreamento = spanElement.innerText.trim();
                        if (codigoRastreamento && codigoRastreamento.length > 5) {
                            objeto = codigoRastreamento;
                            var linkElement = spanElement.closest('a');
                            if (linkElement && linkElement.href) {
                                if (linkElement.href.startsWith('/')) {
                                    objetoLink = 'https://aplicacoes1.trt2.jus.br' + linkElement.href;
                                } else {
                                    objetoLink = linkElement.href;
                                }
                            } else {
                                if (/^[A-Z]{2}\\d{9}BR$/.test(codigoRastreamento)) {
                                    objetoLink = 'https://aplicacoes1.trt2.jus.br/eCarta-web/consultarObjeto.xhtml?codigo=' + codigoRastreamento;
                                }
                            }
                        }
                    }
                    
                    // Fallback: tentar encontrar link na célula do objeto
                    if (!objetoLink && objetoTd) {
                        var linkInCell = objetoTd.querySelector('a[href]');
                        if (linkInCell && linkInCell.href) {
                            if (linkInCell.href.startsWith('/')) {
                                objetoLink = 'https://aplicacoes1.trt2.jus.br' + linkInCell.href;
                            } else {
                                objetoLink = linkInCell.href;
                            }
                        }
                    }
                    
                    var rowData = {
                        dataEnvio: dataEnvio,
                        dataEntrega: dataEntrega,
                        idPje: idPje,
                        idPjeLink: idPjeLink,
                        objeto: objeto,
                        objetoLink: objetoLink,
                        status: tds[5] ? tds[5].innerText.trim() : '',
                        destinatario: tds[6] ? tds[6].innerText.trim() : '',
                        orgaoJulgador: tds[7] ? tds[7].innerText.trim() : ''
                    };
                    
                    return rowData;
                }).filter(function(item) { return item !== null; });
                
                return data;
            }
            
            var resultado = extrairDadosTabela();
            return resultado;
            """
            
            if log:
                print(f"[CARTA] Executando script JavaScript para extração na página {pagina_atual}...")
            
            ecarta_data = driver.execute_script(js_script, pagina_atual)
            
            if not ecarta_data:
                if log:
                    print(f"[CARTA] Nenhum dado encontrado na tabela eCarta - página {pagina_atual}")
            else:
                if log:
                    print(f"[CARTA] Dados extraídos: {len(ecarta_data)} registros na página {pagina_atual}")
                
                # Verificar correlação com IDs da intimação
                data_da_intimacao_encontrada = None
                
                for item in ecarta_data:
                    id_pje = item.get('idPje', '')
                    
                    for intimation_id in intimation_ids:
                        if intimation_id in id_pje or id_pje in intimation_id:
                            if log:
                                print(f"[CARTA] ✅ CORRELAÇÃO ENCONTRADA! ID_PJE={id_pje} corresponde à intimação={intimation_id}")
                                print(f"[CARTA] Data da intimação correlacionada: {item.get('dataEnvio', '')}")
                            
                            data_da_intimacao_encontrada = item.get('dataEnvio', '')
                            break
                    
                    if data_da_intimacao_encontrada:
                        break
                
                # Coletar todas as intimações da mesma data
                if data_da_intimacao_encontrada:
                    if log:
                        print(f"[CARTA] Coletando TODAS as intimações da data: {data_da_intimacao_encontrada}")
                    
                    for item in ecarta_data:
                        item_data_envio = item.get('dataEnvio', '')
                        
                        if item_data_envio == data_da_intimacao_encontrada:
                            table_data.append({
                                "ID_PJE": item.get('idPje', ''),
                                "RASTREAMENTO": item.get('objetoLink', '') or item.get('objeto', ''),
                                "DESTINATARIO": item.get('destinatario', ''),
                                "DATA_ENVIO": item_data_envio,
                                "DATA_ENTREGA": item.get('dataEntrega', ''),
                                "STATUS": item.get('status', '')
                            })
                            
                            if log:
                                print(f"[CARTA] ✅ Coletado da mesma data: ID={item.get('idPje', '')}, Data={item_data_envio}")
                    
                    correlacao_encontrada = True
                    if log:
                        print(f"[CARTA] ✅ {len(table_data)} registros coletados da data {data_da_intimacao_encontrada}!")
                    break
            
            # Navegar para próxima página se necessário
            if not correlacao_encontrada:
                if pagina_atual == 1:
                    try:
                        last_page_btn = driver.find_element(By.CSS_SELECTOR, 'a.ui-paginator-last.ui-state-default.ui-corner-all')
                        last_page_btn.click()
                        time.sleep(3)
                        if log:
                            print("[CARTA] ✅ Navegou para última página")
                        pagina_atual = 2
                    except Exception as e:
                        if log:
                            print(f"[CARTA] ❌ Erro ao navegar para última página: {e}")
                        break
                else:
                    try:
                        prev_page_btn = driver.find_element(By.CSS_SELECTOR, 'a.ui-paginator-prev.ui-state-default.ui-corner-all')
                        prev_page_btn.click()
                        time.sleep(2)
                        if log:
                            print("[CARTA] ✅ Navegou para página anterior")
                        pagina_atual += 1
                    except Exception as e:
                        if log:
                            print(f"[CARTA] ❌ Erro ao navegar para página anterior: {e}")
                        break
        
        if not table_data:
            if log:
                print("[CARTA] Nenhuma correlação encontrada após navegar pelas páginas do eCarta")
            
            # Fechar aba eCarta e voltar para processo
            driver.close()
            driver.switch_to.window(original_window)
            if log:
                print("[CARTA] Aba eCarta fechada, voltando para processo")
            
            return ""
            
    except Exception as e:
        if log:
            print(f"[CARTA] Erro ao extrair dados da tabela eCarta: {e}")
        
        # Fechar aba eCarta em caso de erro
        try:
            driver.close()
            driver.switch_to.window(original_window)
            if log:
                print("[CARTA] Aba eCarta fechada após erro, voltando para processo")
        except:
            pass
        
        return ""
    
    # Fechar aba eCarta e voltar para processo
    try:
        current_window_count = len(driver.window_handles)
        if log:
            print(f"[CARTA] Fechando aba eCarta - Abas antes: {current_window_count}")
        
        driver.close()
        time.sleep(0.5)
        
        driver.switch_to.window(original_window)
        time.sleep(0.5)
        
        if log:
            print(f"[CARTA] Aba eCarta fechada - Abas depois: {len(driver.window_handles)}")
            print(f"[CARTA] Voltando para processo: {driver.current_url}")
    except Exception as e:
        if log:
            print(f"[CARTA] Erro ao fechar aba eCarta: {e}")
    
    # 6. Processar dados coletados
    if not table_data:
        if log:
            print("[CARTA] Nenhum dado encontrado na tabela eCarta com correlação")
        return ""
    
    if log:
        print(f"[CARTA] {len(table_data)} registros coletados da data da intimação correlacionada")
    
    dados_mais_recentes = table_data
    data_da_intimacao = dados_mais_recentes[0].get('DATA_ENVIO', '') if dados_mais_recentes else ''
    
    if log:
        print(f"[CARTA] ✅ Data da intimação correlacionada: {data_da_intimacao}")
        print(f"[CARTA] {len(dados_mais_recentes)} intimações da mesma data serão formatadas")
    
    # 7. Formatar como blocos simples E HTML para juntada
    blocos_formatados = []
    
    # NOVA FUNCIONALIDADE: Gerar HTML correto para juntada com método bookmarklet
    def gerar_html_carta_para_juntada(dados):
        """
        Gera HTML correto para juntada no editor PJe usando método bookmarklet
        Retorna HTML formatado que será aceito pelo editor quando colado via Ctrl+V
        """
        blocos_html = []
        
        for i, item in enumerate(dados, 1):
            # Criar parágrafo com classe corpo (estrutura PJe)
            html_bloco = '<p class="corpo" style="font-size: 12pt; line-height: normal; margin-left: 0px !important; text-align: justify !important; text-indent: 4.5cm;">'
            html_bloco += '&nbsp; &nbsp; '  # Indentação padrão PJe
            
            # ID PJE
            id_pje = item.get('ID_PJE', '')
            if id_pje:
                html_bloco += f'IID: {id_pje}<br>'
            
            # Rastreamento (com link clicável se for URL)
            rastreamento = item.get('RASTREAMENTO', '')
            if rastreamento:
                if rastreamento.startswith('http'):
                    rastreamento_limpo = rastreamento.strip()
                    # Extrair código do rastreamento para exibição
                    codigo_match = re.search(r'codigo=([A-Z0-9]+)', rastreamento_limpo)
                    codigo_display = codigo_match.group(1) if codigo_match else rastreamento_limpo
                    html_bloco += f'OBJETO: <a target="_blank" rel="noopener noreferrer" href="{rastreamento_limpo}">{codigo_display}</a><br>'
                else:
                    html_bloco += f'OBJETO: {rastreamento}<br>'
            
            # Destinatário
            destinatario = item.get('DESTINATARIO', '')
            if destinatario:
                html_bloco += f'DESTINATÁRIO: {destinatario}<br>'
            
            # Data do envio
            data_envio = item.get('DATA_ENVIO', '')
            if data_envio:
                html_bloco += f'DATA DO ENVIO: {data_envio}<br>'
            
            # Data da entrega
            data_entrega = item.get('DATA_ENTREGA', '')
            if data_entrega:
                html_bloco += f'DATA DE ENTREGA: {data_entrega}<br>'
            
            # Status/Resultado
            status = item.get('STATUS', '')
            if status:
                html_bloco += f'RESULTADO: {status}<br>'
            
            # Informação sobre devolução (padrão para cartas entregues)
            if 'entregue' in status.lower():
                html_bloco += 'DEVOLVIDA? ( ) - Desmarcado significa ENTREGA CONFIRMADA.'
            
            html_bloco += '</p>'
            blocos_html.append(html_bloco)
        
        # Unir todos os blocos HTML
        return '\n'.join(blocos_html)
    
    # Gerar tanto o texto simples quanto o HTML
    html_para_juntada = gerar_html_carta_para_juntada(dados_mais_recentes)
    
    if log:
        print(f"[CARTA] ✅ HTML para juntada gerado: {len(html_para_juntada)} caracteres")
        print(f"[CARTA] Preview HTML: {html_para_juntada[:100]}...")
    
    # Manter formatação de texto simples para compatibilidade
    for i, item in enumerate(dados_mais_recentes, 1):
        bloco = []
        bloco.append(f"    Id Pje: {item.get('ID_PJE', '')}")
        
        # Rastreamento
        rastreamento = item.get('RASTREAMENTO', '')
        if rastreamento:
            if rastreamento.startswith('http'):
                # Garantir que não há espaços e retornar apenas o link simples
                rastreamento_limpo = rastreamento.strip()
                bloco.append(f'    Rastreamento: {rastreamento_limpo}')
            else:
                bloco.append(f"    Rastreamento: {rastreamento}")
        else:
            bloco.append("    Rastreamento: Indisponível")
        
        bloco.append(f"    Destinatário: {item.get('DESTINATARIO', '')}")
        bloco.append(f"    Data do envio: {item.get('DATA_ENVIO', '') if item.get('DATA_ENVIO') else 'Indisponível'}")
        bloco.append(f"    Data da entrega: {item.get('DATA_ENTREGA', '') if item.get('DATA_ENTREGA') else 'Indisponível'}")
        bloco.append(f"    Status: {item.get('STATUS', '')}")
        
        bloco_texto = '\n'.join(bloco)
        if i < len(dados_mais_recentes):
            bloco_texto += '\n' + '-' * 50
        
        blocos_formatados.append(bloco_texto)
    
    conteudo_final = '\n\n'.join(blocos_formatados)
    
    # 8. Salvar em clipboard.txt
    try:
        from anexos import salvar_conteudo_clipboard
        
        sucesso = salvar_conteudo_clipboard(
            conteudo=conteudo_final,
            numero_processo=process_number,
            tipo_conteudo="ecarta",
            debug=log
        )
        
        if sucesso and log:
            print("[CARTA] ✅ Conteúdo salvo via função centralizada do clipboard")
        elif log:
            print("[CARTA] ⚠️ Falha ao salvar via função centralizada do clipboard")
            
    except Exception as e:
        if log:
            print(f"[CARTA] ❌ Erro ao salvar clipboard: {e}")
    
    # 9. Salvar versão HTML com links clicáveis
    try:
        if log:
            print("[CARTA] Salvando versão HTML com links clicáveis...")
        
        conteudo_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>E-Carta - Processo {process_number}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 20px; }}
        .container {{ background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ background-color: #2c3e50; color: white; padding: 15px; margin: -20px -20px 20px -20px; border-radius: 8px 8px 0 0; }}
        .processo {{ font-size: 18px; font-weight: bold; }}
        .timestamp {{ font-size: 12px; opacity: 0.9; }}
        .bloco {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #3498db; border-radius: 4px; }}
        .id {{ font-weight: bold; color: #2c3e50; }}
        .status {{ font-weight: bold; }}
        .status.entregue {{ color: #27ae60; }}
        .status.rejeitado {{ color: #e74c3c; }}
        a {{ color: #3498db; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .separador {{ border-top: 2px solid #bdc3c7; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="processo">PROCESSO: {process_number}</div>
            <div class="timestamp">TIPO: ecarta | TIMESTAMP: {time.strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
"""
        
        for i, item in enumerate(dados_mais_recentes, 1):
            rastreamento = item.get('RASTREAMENTO', '')
            status = item.get('STATUS', '').lower()
            status_class = 'entregue' if 'entregue' in status else ('rejeitado' if 'rejeitado' in status else '')
            
            conteudo_html += f"""
        <div class="bloco">
            <div class="id">Id Pje: {item.get('ID_PJE', '')}</div>
"""
            
            if rastreamento:
                if rastreamento.startswith('http'):
                    # Garantir que não há espaços e usar apenas o link simples no HTML também
                    rastreamento_limpo = rastreamento.strip()
                    conteudo_html += f'            <div>Rastreamento: <a href="{rastreamento_limpo}" target="_blank">{rastreamento_limpo}</a></div>\n'
                else:
                    conteudo_html += f'            <div>Rastreamento: {rastreamento}</div>\n'
            else:
                conteudo_html += '            <div>Rastreamento: Indisponível</div>\n'
            
            conteudo_html += f"""            <div>Destinatário: {item.get('DESTINATARIO', '')}</div>
            <div>Data do envio: {item.get('DATA_ENVIO', '') if item.get('DATA_ENVIO') else 'Indisponível'}</div>
            <div>Data da entrega: {item.get('DATA_ENTREGA', '') if item.get('DATA_ENTREGA') else 'Indisponível'}</div>
            <div class="status {status_class}">Status: {item.get('STATUS', '')}</div>
        </div>
"""
            
            if i < len(dados_mais_recentes):
                conteudo_html += '        <div class="separador"></div>\n'
        
        conteudo_html += """    </div>
</body>
</html>"""
        
        html_filename = f"ecarta_{process_number.replace('-', '_').replace('.', '_')}.html"
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(conteudo_html)
            
        if log:
            print(f"[CARTA] ✅ Arquivo HTML salvo: {html_filename}")
            print(f"[CARTA] 📂 Abra o arquivo no navegador para ver os links clicáveis")
            
    except Exception as e:
        if log:
            print(f"[CARTA] ❌ Erro ao salvar arquivo HTML: {e}")
    
    # 10. Exibir resultado no console
    if log:
        print("\n" + "="*80)
        print("DADOS DO E-CARTA EXTRAÍDOS:")
        print("="*80)
        print(conteudo_final)
        print("="*80 + "\n")
    
    # 11. Chamar wrapper de anexos para juntada automática
    try:
        if log:
            print("[CARTA] Iniciando juntada automática via anexos.py com HTML formatado...")
        
        from anexos import carta_wrapper
        
        # Usar o HTML gerado para juntada (ao invés do texto simples)
        resultado_juntada = carta_wrapper(driver, debug=log, ecarta_html=html_para_juntada)
        
        if resultado_juntada and log:
            print("[CARTA] ✅ Juntada automática concluída com sucesso!")
        elif log:
            print("[CARTA] ⚠️ Juntada automática falhou ou foi pulada")
            
    except Exception as e:
        if log:
            print(f"[CARTA] ⚠️ Erro na juntada automática: {e}")
    
    return conteudo_final

def teste_juntada_carta_html(driver, log=True):
    """
    Função de teste para juntada de dados e-Carta com link clicável no formato HTML correto.
    Usa dados fixos para teste da funcionalidade de juntada.
    """
    try:
        if log:
            print("[CARTA][TESTE] Iniciando teste de juntada com dados HTML...")
        
        # Dados de teste no formato HTML CORRETO (estrutura real do PJe)
        dados_html_teste = '''<p class="corpo" style="font-size: 12pt; line-height: normal; margin-left: 0px !important; text-align: justify !important; text-indent: 4.5cm;">&nbsp; &nbsp; IID: 62a83b4<br>DESTINATÁRIO: ANGELA APARECIDA FARIA<br>DATA DO ENVIO: 28/08/2025<br>DATA DE ENTREGA: 01/09/2025<br>RESULTADO: Objeto entregue ao destinatário<br>OBJETO: <a target="_blank" rel="noopener noreferrer" href="https://aplicacoes1.trt2.jus.br/eCarta-web/consultarObjeto.xhtml?codigo=YQ829742261BR">YQ829742261BR</a><br>DEVOLVIDA? ( ) - Desmarcado significa ENTREGA CONFIRMADA.</p>'''
        
        if log:
            print(f"[CARTA][TESTE] Dados HTML preparados: {len(dados_html_teste)} caracteres")
            print(f"[CARTA][TESTE] Preview: {dados_html_teste[:100]}...")
        
        # Tentar fazer a juntada usando anexos.py
        from anexos import carta_wrapper
        
        if log:
            print("[CARTA][TESTE] Chamando carta_wrapper com dados HTML...")
        
        # Chamar carta_wrapper com os dados HTML de teste
        resultado_juntada = carta_wrapper(driver, debug=log, ecarta_html=dados_html_teste)
        
        if resultado_juntada:
            if log:
                print("[CARTA][TESTE] ✅ Juntada de teste concluída com sucesso!")
                print("[CARTA][TESTE] ✅ Link clicável deve estar funcionando no editor")
            return True
        else:
            if log:
                print("[CARTA][TESTE] ❌ Juntada de teste falhou")
            return False
            
    except Exception as e:
        if log:
            print(f"[CARTA][TESTE] ❌ Erro durante teste de juntada: {e}")
        return False