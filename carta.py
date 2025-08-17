from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re

def carta(driver, log=True, limite_intimacoes=None):
    """
    Extrai TODAS as intimações do e-carta do dia mais recente e formata como blocos simples.
    Salva o resultado em clipboard.txt para uso posterior.
    
    Parâmetros:
    - driver: WebDriver do Selenium
    - log: Boolean para ativar logs detalhados
    - limite_intimacoes: (Opcional) Número máximo de intimações para verificar. 
                         Se None, busca indefinidamente (comportamento padrão)
    
    Formato de saída:
    Id Pje: (id)
    Rastreamento: (link clicável)
    Destinatário: (destinatário)
    Data do envio: (data)
    Data da entrega: (data)
    Status: (status)
    
    [próximo bloco]...
    """
    try:
        # 1. Primeiro, extrair o número do processo clicando no ícone de copiar
        process_number = None
        if log:
            print("[CARTA] Extraindo número do processo...")
        
        try:
            # Clica no ícone de copiar para obter o número do processo
            copy_icon = driver.find_element(By.CSS_SELECTOR, 'i.far.fa-copy.fa-lg')
            copy_icon.click()
            time.sleep(1)
            
            # Obtém o conteúdo da área de transferência usando JavaScript
            clipboard_content = driver.execute_script("""
                return navigator.clipboard.readText().then(text => text).catch(err => '');
            """)
            
            if clipboard_content:
                # Busca pelo padrão do número do processo
                proc_match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})', clipboard_content)
                if proc_match:
                    process_number = proc_match.group(1)
                    if log:
                        print(f"[CARTA] Número do processo extraído: {process_number}")
                else:
                    if log:
                        print(f"[CARTA] Conteúdo da área de transferência: {clipboard_content}")
            else:
                if log:
                    print("[CARTA][AVISO] Não foi possível acessar a área de transferência")
                    
        except Exception as e:
            if log:
                print(f"[CARTA][ERRO] Falha ao extrair número do processo: {e}")
        
        # 2. Buscar intimações na timeline do PJe e extrair IDs
        intimation_ids = []
        
        if log:
            print("[CARTA] Iniciando busca de intimações na timeline...")
        
        # NOVA LÓGICA: usar mesma abordagem simplificada do p2.py
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        
        if log:
            print(f"[CARTA] Encontrados {len(itens)} itens na timeline")
        
        # Verifica apenas o primeiro item para ver se é intimação
        intimacao_encontrada = False
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
                    # Clica no primeiro item para extrair conteúdo
                    link = primeiro_item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    aria = link.get_attribute('aria-label') or ''
                    
                    if log:
                        print(f"[CARTA] Clicando na intimação: {link.text}")
                    
                    link.click()
                    time.sleep(2)
                    
                    # Extrai conteúdo para verificar se é correio
                    from Fix import extrair_documento
                    resultado_extracao = extrair_documento(driver, timeout=10, log=False)
                    
                    if resultado_extracao and resultado_extracao[0]:
                        texto_completo = resultado_extracao[0]
                        if log:
                            print(f"[CARTA][DEBUG] Texto extraído ({len(texto_completo)} chars): {texto_completo[:200]}...")
                        
                        # Verifica se é intimação de correio
                        correio_detectado = 'NAO APAGAR NENHUM CARACTERE' in texto_completo.upper()
                        if log:
                            print(f"[CARTA][DEBUG] Procurando 'NAO APAGAR NENHUM CARACTERE' - Encontrado: {correio_detectado}")
                        
                        if correio_detectado:
                            # Extrai ID da intimação do texto do link (após o hífen)
                            link_text = link.text.strip()
                            if log:
                                print(f"[CARTA][DEBUG] Texto do link: {link_text}")
                            
                            # Busca padrão: "Intimação(Intimação) - CODIGO"
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
                        else:
                            if log:
                                print("[CARTA][DEBUG] Intimação não é de correio - iniciando fallback")
                    else:
                        if log:
                            print("[CARTA][ERRO] Não foi possível extrair texto da intimação - iniciando fallback")
                        
                except Exception as e:
                    if log:
                        print(f"[CARTA] Erro ao processar intimação - iniciando fallback: {e}")
            else:
                if log:
                    print("[CARTA] Primeiro item não é uma intimação - iniciando fallback")
        else:
            if log:
                print("[CARTA] Nenhum item encontrado na timeline")
        
        # ===== FALLBACK: Buscar sequencialmente por intimações até encontrar uma de correio =====
        if not intimacao_encontrada:
            if log:
                print("[CARTA][FALLBACK] Buscando sequencialmente por intimações de correio...")
            
            # Contador de intimações verificadas
            count_intimacoes = 0
            
            # Determina o limite baseado no parâmetro
            limite = limite_intimacoes if limite_intimacoes is not None else float('inf')
            if log and limite_intimacoes is not None:
                print(f"[CARTA][FALLBACK] Limite de intimações definido: {limite}")
            
            # Percorrer sequencialmente os itens até encontrar intimação de correio ou atingir o limite
            for idx, item in enumerate(itens):
                try:
                    # Procura links de documentos (não target="_blank")
                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    doc_text = link.text.lower()
                    
                    # Verifica se é intimação (busca por "intimação(intimação)" especificamente)
                    if 'intimação' in doc_text:
                        count_intimacoes += 1
                        if log:
                            print(f"[CARTA][FALLBACK] Intimação encontrada no item {idx + 1} (verificando {count_intimacoes}")
                            if limite_intimacoes is not None:
                                print(f"[CARTA][FALLBACK] Limite: {limite_intimacoes} | Verificadas: {count_intimacoes}")
                        
                        # Se já atingiu o limite, interrompe
                        if count_intimacoes > limite:
                            if log:
                                print(f"[CARTA][FALLBACK] Limite de {limite} intimações atingido. Parando busca.")
                            break
                        
                        # Clica no documento para extrair conteúdo
                        link.click()
                        time.sleep(2)
                        
                        # Extrai conteúdo usando Fix.extrair_documento
                        from Fix import extrair_documento
                        
                        try:
                            resultado_extracao = extrair_documento(driver, timeout=10, log=False)
                            
                            if resultado_extracao and resultado_extracao[0]:
                                texto_completo = resultado_extracao[0]
                                
                                # Verifica se é intimação de correio
                                correio_detectado = 'NAO APAGAR NENHUM CARACTERE' in texto_completo.upper()
                                
                                if correio_detectado:
                                    # É de correio! Extrai ID e para a busca
                                    aria = link.get_attribute('aria-label') or ''
                                    link_text = link.text.strip()
                                    
                                    # Busca padrão: "Intimação(Intimação) - CODIGO"
                                    id_match = re.search(r'-\s*([a-f0-9]+)\s*$', link_text)
                                    if id_match:
                                        id_curto = id_match.group(1)
                                    else:
                                        # Fallback para aria-label
                                        id_match = re.search(r'Id: ([a-f0-9]+)', aria)
                                        id_curto = id_match.group(1) if id_match else item.get_attribute('id')
                                    
                                    intimation_ids.append(id_curto)
                                    intimacao_encontrada = True
                                    
                                    if log:
                                        print(f"[CARTA][FALLBACK] ✅ Intimação de correio encontrada: {id_curto}")
                                    
                                    # PARA A BUSCA - encontrou intimação de correio
                                    break
                                else:
                                    # Não é de correio, continua procurando
                                    if log:
                                        print(f"[CARTA][FALLBACK] Item {idx + 1} não é de correio, continuando...")
                                    continue
                            else:
                                # Não conseguiu extrair texto, continua procurando
                                if log:
                                    print(f"[CARTA][FALLBACK] Não foi possível extrair texto do item {idx + 1}, continuando...")
                                continue
                                    
                        except Exception as extract_err:
                            # Erro na extração, continua procurando
                            if log:
                                print(f"[CARTA][FALLBACK] Erro ao extrair item {idx + 1}, continuando...")
                            continue
                            
                except Exception as e:
                    # Item não tem link de documento, continua para o próximo
                    continue
            
            if not intimacao_encontrada:
                if log:
                    if limite_intimacoes is not None:
                        print(f"[CARTA][FALLBACK] ❌ Nenhuma intimação de correio encontrada após verificar {count_intimacoes} intimações.")
                    else:
                        print("[CARTA][FALLBACK] ❌ Nenhuma intimação de correio encontrada na timeline.")
        
        if not intimation_ids or not process_number or not intimacao_encontrada:
            if log:
                print("[CARTA] Nenhuma intimação de correio encontrada.")
            return ""
        
        if log:
            print(f"[CARTA] {len(intimation_ids)} intimações encontradas para processo {process_number}")
        
        # 2. Acessar eCarta em nova aba
        if log:
            print("[CARTA] Abrindo eCarta em nova aba...")
        
        # Salvar a aba atual (processo)
        original_window = driver.current_window_handle
        original_window_count = len(driver.window_handles)
        
        if log:
            print(f"[CARTA] Abas antes de abrir eCarta: {original_window_count}")
        
        # Abrir eCarta em nova aba
        ecarta_url = f"https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo={process_number}"
        driver.execute_script(f"window.open('{ecarta_url}', '_blank');")
        
        # AGUARDAR que a nova aba seja detectada (mais robusto para Fix.py)
        max_tentativas = 10
        for tentativa in range(max_tentativas):
            time.sleep(0.5)
            current_window_count = len(driver.window_handles)
            if current_window_count > original_window_count:
                if log:
                    print(f"[CARTA] Nova aba detectada após {tentativa * 0.5:.1f}s - Total: {current_window_count}")
                break
        else:
            if log:
                print("[CARTA] AVISO: Nova aba não foi detectada no tempo esperado")
        
        # Aguardar mais um pouco para Fix.py processar a mudança
        time.sleep(2)
        
        # Mudar foco para a nova aba (eCarta) - sempre a última aba criada
        all_windows = driver.window_handles
        if len(all_windows) > 1:
            # A nova aba será sempre a última da lista
            nova_aba = all_windows[-1]
            driver.switch_to.window(nova_aba)
            if log:
                print(f"[CARTA] Focando na nova aba (última): {nova_aba}")
        else:
            if log:
                print("[CARTA][ERRO] Nova aba não foi detectada")
        
        if log:
            print(f"[CARTA] Nova aba eCarta aberta: {driver.current_url}")
        
        # VALIDAÇÃO CRÍTICA: Verificar se estamos realmente na aba do eCarta
        if "ecarta" not in driver.current_url.lower():
            if log:
                print(f"[CARTA][ERRO] Não estamos na aba correta do eCarta!")
                print(f"[CARTA][ERRO] URL atual: {driver.current_url}")
                print(f"[CARTA][ERRO] Interrompendo execução - retornando ao fluxo normal")
            return ""  # Retorna vazio para permitir que o fluxo continue
        
        time.sleep(3)  # Aguardar carregamento
        
        # 3. Login se necessário
        try:
            username_field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#input_user"))
            )
            if log:
                print("[CARTA] Fazendo login no eCarta...")
            username_field.send_keys("s164283")
            driver.find_element(By.CSS_SELECTOR, "#input_password").send_keys("59Justdoit!1")
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
        
        # 4. Extrair dados da tabela do eCarta usando JavaScript com logs detalhados
        table_data = []
        try:
            if log:
                print("[CARTA] Iniciando extração de dados da tabela eCarta...")
            
            # Primeiro, tentar na página atual
            correlacao_encontrada = False
            pagina_atual = 1
            max_tentativas_paginas = 10  # Máximo de páginas para tentar
            
            while not correlacao_encontrada and pagina_atual <= max_tentativas_paginas:
                if log:
                    print(f"[CARTA] Tentativa de extração na página {pagina_atual}...")
                
                # JavaScript para extrair dados da tabela eCarta com logs
                js_script = """
                console.log('[CARTA-JS] Iniciando extração de dados na página', arguments[0] || 'desconhecida');
                
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
                    // Primeiro, vamos verificar qual página estamos
                    var paginatorInfo = document.querySelector('.ui-paginator-current');
                    if (paginatorInfo) {
                        console.log('[CARTA-JS] Info do paginador:', paginatorInfo.innerText);
                    }
                    
                    console.log('[CARTA-JS] URL atual:', window.location.href);
                    console.log('[CARTA-JS] Título da página:', document.title);
                    
                    // Tentar múltiplos seletores para encontrar a tabela
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
                        console.log('[CARTA-JS] Tentando seletor:', seletores[i]);
                        var tempRows = Array.from(document.querySelectorAll(seletores[i]));
                        console.log('[CARTA-JS] Rows encontradas com seletor', seletores[i] + ':', tempRows.length);
                        
                        if (tempRows.length > 0) {
                            rows = tempRows;
                            seletorUsado = seletores[i];
                            break;
                        }
                    }
                    
                    if (!rows || rows.length === 0) {
                        console.log('[CARTA-JS] ERRO: Nenhuma linha encontrada em nenhum seletor');
                        
                        // Debug adicional - vamos ver o que existe na página
                        var todasTabelas = document.querySelectorAll('table');
                        console.log('[CARTA-JS] DEBUG: Total de tabelas na página:', todasTabelas.length);
                        
                        for (var j = 0; j < Math.min(todasTabelas.length, 3); j++) {
                            var tabela = todasTabelas[j];
                            console.log('[CARTA-JS] DEBUG: Tabela', j+1, 'ID:', tabela.id, 'Class:', tabela.className);
                            var linhas = tabela.querySelectorAll('tr');
                            console.log('[CARTA-JS] DEBUG: Tabela', j+1, 'tem', linhas.length, 'linhas');
                        }
                        
                        return null;
                    }
                    
                    console.log('[CARTA-JS] Usando seletor:', seletorUsado);
                    console.log('[CARTA-JS] Processando', rows.length, 'linhas...');
                    
                    var data = rows.map(function(tr, index) {
                        console.log('[CARTA-JS] Processando linha', index + 1);
                        var tds = tr.querySelectorAll('td');
                        console.log('[CARTA-JS] TDs encontrados na linha:', tds.length);
                        
                        if (tds.length < 4) {
                            console.log('[CARTA-JS] Linha', index + 1, 'tem poucos TDs, pulando...');
                            return null;
                        }
                        
                        // Extrair dados das colunas (ajustar índices se necessário)
                        var dataEnvio = tds[0] ? tds[0].innerText.trim() : '';
                        var dataEntrega = tds[1] ? tds[1].innerText.trim() : '';
                        var idTd = tds[3];  // Coluna do ID PJe
                        var idPje = idTd ? idTd.innerText.trim() : '';
                        var objetoTd = tds[4];  // Coluna do objeto
                        var objeto = objetoTd ? objetoTd.innerText.trim() : '';
                        
                        console.log('[CARTA-JS] Linha', index + 1, '- ID PJe:', idPje);
                        console.log('[CARTA-JS] Linha', index + 1, '- Objeto:', objeto.substring(0, 100));
                        
                        // Se não temos ID na coluna 3, tentar outras colunas
                        if (!idPje || idPje.length < 5) {
                            for (var k = 0; k < tds.length; k++) {
                                var conteudo = tds[k].innerText.trim();
                                // Procurar por algo que pareça um ID (letras e números)
                                if (/^[a-f0-9]{6,}$/.test(conteudo)) {
                                    idPje = conteudo;
                                    console.log('[CARTA-JS] ID encontrado na coluna', k, ':', idPje);
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
                            console.log('[CARTA-JS] Código rastreamento encontrado:', codigoRastreamento);
                            if (codigoRastreamento && codigoRastreamento.length > 5) {
                                objeto = codigoRastreamento;
                                var linkElement = spanElement.closest('a');
                                if (linkElement && linkElement.href) {
                                    if (linkElement.href.startsWith('/')) {
                                        objetoLink = 'https://aplicacoes1.trt2.jus.br' + linkElement.href;
                                    } else {
                                        objetoLink = linkElement.href;
                                    }
                                    console.log('[CARTA-JS] Link de rastreamento extraído:', objetoLink);
                                } else {
                                    // Se não há link direto, tentar construir a URL baseada no código
                                    if (/^[A-Z]{2}\\d{9}BR$/.test(codigoRastreamento)) {
                                        objetoLink = 'https://aplicacoes1.trt2.jus.br/eCarta-web/consultarObjeto.xhtml?codigo=' + codigoRastreamento;
                                        console.log('[CARTA-JS] Link de rastreamento construído:', objetoLink);
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
                                console.log('[CARTA-JS] Link alternativo encontrado na célula:', objetoLink);
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
                        
                        console.log('[CARTA-JS] Dados da linha', index + 1, ':', JSON.stringify(rowData));
                        return rowData;
                    }).filter(function(item) { return item !== null; });
                    
                    console.log('[CARTA-JS] Total de linhas válidas processadas:', data.length);
                    
                    if (data.length === 0) {
                        console.log('[CARTA-JS] ERRO: Nenhum dado válido encontrado');
                        return null;
                    }
                    
                    console.log('[CARTA-JS] Retornando dados da página');
                    return data;
                }
                
                var resultado = extrairDadosTabela();
                console.log('[CARTA-JS] Resultado final:', resultado);
                return resultado;
                """
                
                # Executa o JavaScript e obtém os dados
                if log:
                    print(f"[CARTA] Executando script JavaScript para extração na página {pagina_atual}...")
                
                ecarta_data = driver.execute_script(js_script, pagina_atual)
                
                if log:
                    print(f"[CARTA] Resultado da extração JavaScript: {ecarta_data}")
                
                if not ecarta_data:
                    if log:
                        print(f"[CARTA] Nenhum dado encontrado na tabela eCarta - página {pagina_atual}")
                else:
                    if log:
                        print(f"[CARTA] Dados extraídos: {len(ecarta_data)} registros na página {pagina_atual}")
                        for i, item in enumerate(ecarta_data):
                            print(f"[CARTA] Registro {i+1}: ID_PJE={item.get('idPje', '')}, STATUS={item.get('status', '')}")
                    
                    # Verificar se há correlação com IDs da intimação do PJE nesta página
                    data_da_intimacao_encontrada = None
                    
                    for item in ecarta_data:
                        id_pje = item.get('idPje', '')
                        destinatario = item.get('destinatario', '')
                        status = item.get('status', '')
                        objeto = item.get('objeto', '')
                        objeto_link = item.get('objetoLink', '')
                        data_envio = item.get('dataEnvio', '')
                        data_entrega = item.get('dataEntrega', '') 
                        
                        if log:
                            print(f"[CARTA] Verificando correlação: ID_PJE={id_pje} vs intimation_ids={intimation_ids}")
                        
                        # Verificar se este ID corresponde a alguma intimação encontrada no processo PJE
                        for intimation_id in intimation_ids:
                            if intimation_id in id_pje or id_pje in intimation_id:
                                if log:
                                    print(f"[CARTA] ✅ CORRELAÇÃO ENCONTRADA! ID_PJE={id_pje} corresponde à intimação={intimation_id}")
                                    print(f"[CARTA] Data da intimação correlacionada: {data_envio}")
                                
                                # Definir a data da intimação encontrada
                                data_da_intimacao_encontrada = data_envio
                                break
                        
                        if data_da_intimacao_encontrada:
                            break
                    
                    # Se encontrou correlação, coletar TODAS as intimações desta data específica
                    if data_da_intimacao_encontrada:
                        if log:
                            print(f"[CARTA] Coletando TODAS as intimações da data: {data_da_intimacao_encontrada}")
                        
                        for item in ecarta_data:
                            item_data_envio = item.get('dataEnvio', '')
                            
                            # Coletar apenas intimações da mesma data da intimação correlacionada
                            if item_data_envio == data_da_intimacao_encontrada:
                                id_pje = item.get('idPje', '')
                                objeto_link = item.get('objetoLink', '')
                                objeto = item.get('objeto', '')
                                
                                table_data.append({
                                    "ID_PJE": id_pje,
                                    "RASTREAMENTO": objeto_link if objeto_link else objeto,
                                    "DESTINATARIO": item.get('destinatario', ''),
                                    "DATA_ENVIO": item_data_envio,
                                    "DATA_ENTREGA": item.get('dataEntrega', ''),
                                    "STATUS": item.get('status', '')
                                })
                                
                                if log:
                                    print(f"[CARTA] ✅ Coletado da mesma data: ID={id_pje}, Data={item_data_envio}")
                        
                        correlacao_encontrada = True
                        if log:
                            print(f"[CARTA] ✅ {len(table_data)} registros coletados da data {data_da_intimacao_encontrada}!")
                        break
                    else:
                        # Não encontrou correlação nesta página
                        if log:
                            print(f"[CARTA] Nenhuma correlação encontrada na página {pagina_atual}")
                
                # Aguardar um pouco antes de tentar navegar
                if log:
                    print(f"[CARTA] Correlação não encontrada na página {pagina_atual}, tentando navegar...")
                time.sleep(1)
                
                # Se não encontrou e é a primeira página, navegar para última página
                if pagina_atual == 1:
                    if log:
                        print("[CARTA] Navegando para última página do eCarta...")
                    
                    try:
                        # Clicar no botão "última página"
                        last_page_btn = driver.find_element(By.CSS_SELECTOR, 'a.ui-paginator-last.ui-state-default.ui-corner-all')
                        last_page_btn.click()
                        time.sleep(3)  # Aumentar tempo de espera
                        if log:
                            print("[CARTA] ✅ Navegou para última página")
                        pagina_atual = 2  # Marcar como segunda tentativa (última página)
                    except Exception as e:
                        if log:
                            print(f"[CARTA] ❌ Erro ao navegar para última página: {e}")
                        break
                        
                # Se não encontrou e não é a primeira página, navegar para página anterior
                elif pagina_atual > 1:
                    if log:
                        print("[CARTA] Navegando para página anterior do eCarta...")
                    
                    try:
                        # Clicar no botão "página anterior"
                        prev_page_btn = driver.find_element(By.CSS_SELECTOR, 'a.ui-paginator-prev.ui-state-default.ui-corner-all')
                        prev_page_btn.click()
                        time.sleep(2)
                        if log:
                            print("[CARTA] ✅ Navegou para página anterior")
                        pagina_atual += 1  # Incrementa contador de tentativas
                    except Exception as e:
                        if log:
                            print(f"[CARTA] ❌ Erro ao navegar para página anterior ou chegou na primeira: {e}")
                        break
                else:
                    # Não há mais páginas para navegar
                    if log:
                        print("[CARTA] Não há mais páginas para navegar")
                    break
            
            # Se não encontrou dados após todas as tentativas
            if not table_data:
                if log:
                    print("[CARTA] Nenhuma correlação encontrada após navegar pelas páginas do eCarta")
                
                # Tentar verificar se a página carregou corretamente
                page_title = driver.title
                current_url = driver.current_url
                if log:
                    print(f"[CARTA] Título da página: {page_title}")
                    print(f"[CARTA] URL atual: {current_url}")
                
                # Fechar aba eCarta e voltar para processo
                driver.close()
                driver.switch_to.window(original_window)
                if log:
                    print("[CARTA] Aba eCarta fechada, voltando para processo")
                
                return ""
        
        except Exception as e:
            if log:
                print(f"[CARTA] Erro ao extrair dados da tabela eCarta via JavaScript: {e}")
            
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
                print(f"[CARTA] Aba atual: {driver.current_window_handle}")
                print(f"[CARTA] Aba original: {original_window}")
            
            driver.close()
            time.sleep(0.5)  # Aguardar Fix.py processar fechamento
            
            driver.switch_to.window(original_window)
            time.sleep(0.5)  # Aguardar Fix.py processar mudança de foco
            
            final_window_count = len(driver.window_handles)
            if log:
                print(f"[CARTA] Aba eCarta fechada - Abas depois: {final_window_count}")
                print(f"[CARTA] Voltando para processo: {driver.current_url}")
        except Exception as e:
            if log:
                print(f"[CARTA] Erro ao fechar aba eCarta: {e}")
        
        # 5. Processar dados coletados - já filtrados pela data da intimação correlacionada
        if not table_data:
            if log:
                print("[CARTA] Nenhum dado encontrado na tabela eCarta com correlação")
            return ""
        
        if log:
            print(f"[CARTA] {len(table_data)} registros coletados da data da intimação correlacionada")
        
        # Os dados já estão filtrados pela data correta, não precisa reagrupar
        dados_mais_recentes = table_data
        
        # Extrair a data para log (pegar do primeiro item)
        data_da_intimacao = dados_mais_recentes[0].get('DATA_ENVIO', '') if dados_mais_recentes else ''
        
        if log:
            print(f"[CARTA] ✅ Data da intimação correlacionada: {data_da_intimacao}")
            print(f"[CARTA] {len(dados_mais_recentes)} intimações da mesma data serão formatadas")
        
        # 6. Formatar como blocos simples com tabulação correta
        blocos_formatados = []
        
        for i, item in enumerate(dados_mais_recentes, 1):
            bloco = []
            bloco.append(f"    Id Pje: {item.get('ID_PJE', '')}")
            
            # Rastreamento (link clicável se disponível)
            rastreamento = item.get('RASTREAMENTO', '')
            if rastreamento:
                # Se é uma URL, criar um link clicável em formato HTML
                if rastreamento.startswith('http'):
                    # Extrair código do rastreamento da URL para exibição
                    codigo_match = re.search(r'codigo=([A-Z]{2}\\d{9}BR)', rastreamento)
                    if codigo_match:
                        codigo = codigo_match.group(1)
                        bloco.append(f'    Rastreamento: <a href="{rastreamento}" target="_blank">{codigo}</a>')
                    else:
                        bloco.append(f'    Rastreamento: <a href="{rastreamento}" target="_blank">{rastreamento}</a>')
                else:
                    # Se não é URL, exibir como texto simples
                    bloco.append(f"    Rastreamento: {rastreamento}")
            else:
                bloco.append("    Rastreamento: Indisponível")
            
            bloco.append(f"    Destinatário: {item.get('DESTINATARIO', '')}")
            bloco.append(f"    Data do envio: {item.get('DATA_ENVIO', '') if item.get('DATA_ENVIO') else 'Indisponível'}")
            bloco.append(f"    Data da entrega: {item.get('DATA_ENTREGA', '') if item.get('DATA_ENTREGA') else 'Indisponível'}")
            bloco.append(f"    Status: {item.get('STATUS', '')}")
            
            # Adiciona linha separadora para cada bloco exceto o último
            bloco_texto = '\\n'.join(bloco)
            if i < len(dados_mais_recentes):
                bloco_texto += '\\n' + '-' * 50  # Linha separadora
            
            blocos_formatados.append(bloco_texto)
        
        # Juntar todos os blocos com dupla quebra
        conteudo_final = '\\n\\n'.join(blocos_formatados)
        
        # 7. Salvar em clipboard.txt usando função centralizada
        try:
            from anexos import salvar_conteudo_clipboard
            
            # Usar função centralizada que adiciona número do processo automaticamente
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
        
        # 8. Salvar versão HTML com links clicáveis
        try:
            if log:
                print("[CARTA] Salvando versão HTML com links clicáveis...")
            
            # Criar conteúdo HTML
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
            
            # Adicionar cada bloco
            for i, item in enumerate(dados_mais_recentes, 1):
                rastreamento = item.get('RASTREAMENTO', '')
                status = item.get('STATUS', '').lower()
                status_class = 'entregue' if 'entregue' in status else ('rejeitado' if 'rejeitado' in status else '')
                
                conteudo_html += f"""
        <div class="bloco">
            <div class="id">Id Pje: {item.get('ID_PJE', '')}</div>
"""
                
                # Rastreamento com link clicável
                if rastreamento:
                    if rastreamento.startswith('http'):
                        codigo_match = re.search(r'codigo=([A-Z]{{2}}\\d{{9}}BR)', rastreamento)
                        if codigo_match:
                            codigo = codigo_match.group(1)
                            conteudo_html += f'            <div>Rastreamento: <a href="{rastreamento}" target="_blank">{codigo}</a></div>\\n'
                        else:
                            conteudo_html += f'            <div>Rastreamento: <a href="{rastreamento}" target="_blank">{rastreamento}</a></div>\\n'
                    else:
                        conteudo_html += f'            <div>Rastreamento: {rastreamento}</div>\\n'
                else:
                    conteudo_html += '            <div>Rastreamento: Indisponível</div>\\n'
                
                conteudo_html += f"""            <div>Destinatário: {item.get('DESTINATARIO', '')}</div>
            <div>Data do envio: {item.get('DATA_ENVIO', '') if item.get('DATA_ENVIO') else 'Indisponível'}</div>
            <div>Data da entrega: {item.get('DATA_ENTREGA', '') if item.get('DATA_ENTREGA') else 'Indisponível'}</div>
            <div class="status {status_class}">Status: {item.get('STATUS', '')}</div>
        </div>
"""
                
                if i < len(dados_mais_recentes):
                    conteudo_html += '        <div class="separador"></div>\\n'
            
            conteudo_html += """    </div>
</body>
</html>"""
            
            # Salvar arquivo HTML
            html_filename = f"ecarta_{process_number.replace('-', '_').replace('.', '_')}.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(conteudo_html)
                
            if log:
                print(f"[CARTA] ✅ Arquivo HTML salvo: {html_filename}")
                print(f"[CARTA] 📂 Abra o arquivo no navegador para ver os links clicáveis")
                
        except Exception as e:
            if log:
                print(f"[CARTA] ❌ Erro ao salvar arquivo HTML: {e}")
        
        # 8. Exibir resultado no console
        if log:
            print("\\n" + "="*80)
            print("DADOS DO E-CARTA EXTRAÍDOS:")
            print("="*80)
            print(conteudo_final)
            print("="*80 + "\\n")
        
        # 9. Chamar wrapper de anexos para juntada automática
        try:
            if log:
                print("[CARTA] Iniciando juntada automática via anexos.py...")
            
            from anexos import carta_wrapper
            
            # Passar o conteúdo formatado para o wrapper
            resultado_juntada = carta_wrapper(driver, debug=log, ecarta_html=conteudo_final)
            
            if resultado_juntada and log:
                print("[CARTA] ✅ Juntada automática concluída com sucesso!")
            elif log:
                print("[CARTA] ⚠️ Juntada automática falhou ou foi pulada")
                
        except Exception as e:
            if log:
                print(f"[CARTA] ⚠️ Erro na juntada automática: {e}")
        
        return conteudo_final
        
    except Exception as e:
        if log:
            print(f"[CARTA] Erro no processamento: {e}")
        return ""

def generate_html_table(data):
    """Gera tabela HTML simples com os dados fornecidos"""
    if not data:
        return ""
    
    html = """<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif;">
    <thead style="background-color: #f0f0f0;">
        <tr>
            <th>ID</th>
            <th>DESTINATARIO</th>
            <th>RESULTADO</th>
            <th>RASTREAMENTO</th>
        </tr>
    </thead>
    <tbody>"""
    
    for row in data:
        html += f"""
        <tr>
            <td>{row['ID']}</td>
            <td>{row['DESTINATARIO']}</td>
            <td>{row['RESULTADO']}</td>
            <td>{row['RASTREAMENTO']}</td>
        </tr>"""
    
    html += """
    </tbody>
</table>"""
    
    return html

def gerar_tabela_intimacoes_recentes(driver, log=True):
    """
    Gera uma tabela HTML com todas as intimações de correio das datas mais recentes (primeiro bloco de data da timeline).
    Colunas: ID, DESTINATARIO, RESULTADO, RASTREAMENTO (estes três últimos ficam vazios).
    """
    import re
    from Fix import extrair_documento
    try:
        intimation_rows = []
        process_number = None
        if log:
            print("[CARTA] Iniciando busca de intimações de correio na timeline...")
        
        # NOVA LÓGICA: usar mesma abordagem do p2.py
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        
        if log:
            print(f"[CARTA] Encontrados {len(itens)} itens na timeline")
        
        # Processa apenas o(s) primeiro(s) bloco(s) de data
        first_date_found = False
        for idx, item in enumerate(itens):
            if log:
                print(f"[CARTA] Processando item {idx+1}/{len(itens)}")
            
            # Detecta mudança de data
            try:
                date_div = item.find_element(By.CSS_SELECTOR, 'div.tl-data')
                if first_date_found:
                    if log:
                        print("[CARTA] Segunda data encontrada, parando busca")
                    break  # Para na segunda data
                first_date_found = True
                if log:
                    print(f"[CARTA] Primeira data encontrada: {date_div.text}")
                continue
            except:
                pass
            
            # Busca intimações de correio
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                aria = link.get_attribute('aria-label') or ''
                texto_link = link.text.strip().lower()
                
                if log:
                    print(f"[CARTA] Item {idx+1}: {texto_link[:50]}...")
                
                if 'intimação' in texto_link or 'intimação' in aria.lower():
                    if log:
                        print(f"[CARTA] Intimação encontrada: {texto_link}")
                    
                    link.click()
                    time.sleep(2)
                    resultado_extracao = extrair_documento(driver, timeout=10, log=False)
                    if resultado_extracao and resultado_extracao[0]:
                        texto_completo = resultado_extracao[0]
                        if log:
                            print(f"[CARTA][DEBUG] Texto extraído ({len(texto_completo)} chars): {texto_completo[:200]}...")
                        correio_detectado = 'NAO APAGAR NENHUM CARACTERE' in texto_completo.upper()
                        if log:
                            print(f"[CARTA][DEBUG] Procurando 'NAO APAGAR NENHUM CARACTERE' - Encontrado: {correio_detectado}")
                        
                        if correio_detectado:
                            # Extrai ID da intimação
                            link_text = link.text.strip()
                            id_match = re.search(r'-\s*([a-f0-9]+)\s*$', link_text)
                            if id_match:
                                id_curto = id_match.group(1)
                            else:
                                id_match = re.search(r'Id: ([a-f0-9]+)', aria)
                                id_curto = id_match.group(1) if id_match else item.get_attribute('id')
                            
                            intimation_rows.append({
                                "ID": id_curto,
                                "DESTINATARIO": "",
                                "RESULTADO": "",
                                "RASTREAMENTO": ""
                            })
                            
                            if log:
                                print(f"[CARTA] Intimação de correio adicionada: {id_curto}")
                        else:
                            if log:
                                print("[CARTA] Intimação não é de correio")
                    else:
                        if log:
                            print("[CARTA] Não foi possível extrair texto da intimação")
            except Exception as e:
                if log:
                    print(f"[CARTA] Erro ao processar item {idx+1}: {e}")
        
        if not intimation_rows:
            if log:
                print("[CARTA] Nenhuma intimação de correio encontrada")
            return ""
        
        if log:
            print(f"[CARTA] {len(intimation_rows)} intimações de correio encontradas")
        
        # Gerar tabela HTML
        html_table = generate_html_table(intimation_rows)
        
        # Salvar em arquivo
        filename = "intimacoes_recentes.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Intimações Recentes</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Intimações de Correio Recentes</h1>
    {html_table}
</body>
</html>""")
        
        if log:
            print(f"[CARTA] Tabela HTML salva: {filename}")
        
        return html_table
        
    except Exception as e:
        if log:
            print(f"[CARTA] Erro ao gerar tabela de intimações: {e}")
        return ""