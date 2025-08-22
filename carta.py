from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import pyperclip

def carta(driver, log=True, limite_intimacoes=None):
    """
    Função principal para processar intimações de carta no PJe
    """
    # 1. Tentar clicar no ícone de copiar número do processo antes de extrair do clipboard
    process_number = None
    clipboard_content = None
    try:
        icone_clipboard = driver.find_element(By.CSS_SELECTOR, 'pje-icone-clipboard .mat-tooltip-trigger.pointer')
        icone_clipboard.click()
        if log:
            print("[CARTA][DEBUG] Ícone de copiar número do processo clicado.")
        time.sleep(0.5)
    except Exception as e:
        if log:
            print(f"[CARTA][DEBUG] Falha ao clicar no ícone de copiar número do processo: {e}")
    try:
        clipboard_content = pyperclip.paste()
        if log:
            print(f"[CARTA] Conteúdo do clipboard: {clipboard_content}")
    except Exception:
        if log:
            print("[CARTA][AVISO] Não foi possível acessar a área de transferência")
    # Extrair número do processo do clipboard
    if clipboard_content:
        proc_match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})', clipboard_content)
        if proc_match:
            process_number = proc_match.group(1)
            if log:
                print(f"[CARTA] Número do processo extraído: {process_number}")
    
    # 2. Buscar intimações na timeline do PJe
    intimation_ids = []
    if log:
        print("[CARTA] Iniciando busca de intimações na timeline...")
    
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    if log:
        print(f"[CARTA] Encontrados {len(itens)} itens na timeline")
    
    # Variável para controlar se encontramos intimação de correio
    intimacao_encontrada = False
    
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
                
                # Extrair conteúdo para verificar se é correio
                from Fix import extrair_documento, extrair_pdf
                texto_completo = None
                
                # Tentativa 1: Usar extrair_documento
                try:
                    texto_completo = extrair_documento(driver, regras_analise=None, timeout=10, log=False)
                    if texto_completo:
                        texto_completo = texto_completo.lower()
                        if log:
                            print(f"[CARTA][DEBUG] Texto extraído com sucesso usando extrair_documento ({len(texto_completo)} chars)")
                    else:
                        if log:
                            print("[CARTA][DEBUG] extrair_documento retornou None")
                except Exception as e:
                    if log:
                        print(f"[CARTA][DEBUG] Erro ao extrair documento com extrair_documento: {e}")
                
                # Se extrair_documento falhou, tentar extrair_pdf
                if not texto_completo or len(texto_completo.strip()) < 10:
                    if log:
                        print("[CARTA][DEBUG] Tentando alternativa com extrair_pdf...")
                    try:
                        texto_pdf = extrair_pdf(driver, log=False)
                        if texto_pdf:
                            texto_completo = texto_pdf.lower()
                            if log:
                                print("[CARTA][DEBUG] Texto extraído com sucesso usando extrair_pdf ({len(texto_pdf)} chars)")
                        else:
                            if log:
                                print("[CARTA][DEBUG] extrair_pdf retornou None")
                    except Exception as e:
                        if log:
                            print(f"[CARTA][DEBUG] Erro ao extrair documento com extrair_pdf: {e}")
                
                # Verificar se temos texto válido
                if not texto_completo or len(texto_completo.strip()) < 10:
                    if log:
                        print("[CARTA][DEBUG] Não foi possível extrair texto da intimação")
                    return
                
                # Verificar se é intimação de correio
                correio_detectado = 'NAO APAGAR NENHUM CARACTERE' in texto_completo.upper()
                if log:
                    print(f"[CARTA][DEBUG] Procurando 'NAO APAGAR NENHUM CARACTERE' - Encontrado: {correio_detectado}")
                
                if correio_detectado:
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
                else:
                    if log:
                        print("[CARTA][DEBUG] Intimação não é de correio - iniciando fallback")
            except Exception as e:
                if log:
                    print(f"[CARTA] Erro ao processar intimação: {e}")
    
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
                    count_intimacoes += 1
                    if log:
                        print(f"[CARTA][FALLBACK] Intimação encontrada no item {idx + 1}")
                    
                    if count_intimacoes > limite:
                        if log:
                            print(f"[CARTA][FALLBACK] Limite de {limite} intimações atingido")
                        break
                    
                    link.click()
                    time.sleep(2)
                    
                    # Extrair conteúdo
                    from Fix import extrair_documento, extrair_pdf
                    texto_completo = None
                    
                    # Tentativa 1: Usar extrair_documento
                    try:
                        texto_completo = extrair_documento(driver, regras_analise=None, timeout=10, log=False)
                        if texto_completo:
                            texto_completo = texto_completo.lower()
                            if log:
                                print(f"[CARTA][FALLBACK] Texto extraído com sucesso usando extrair_documento ({len(texto_completo)} chars)")
                        else:
                            if log:
                                print("[CARTA][FALLBACK] extrair_documento retornou None")
                    except Exception as e:
                        if log:
                            print(f"[CARTA][FALLBACK] Erro ao extrair documento com extrair_documento: {e}")
                    
                    # Se extrair_documento falhou, tentar extrair_pdf
                    if not texto_completo or len(texto_completo.strip()) < 10:
                        if log:
                            print("[CARTA][FALLBACK] Tentando alternativa com extrair_pdf...")
                        try:
                            texto_pdf = extrair_pdf(driver, log=False)
                            if texto_pdf:
                                texto_completo = texto_pdf.lower()
                                if log:
                                    print(f"[CARTA][FALLBACK] Texto extraído com sucesso usando extrair_pdf ({len(texto_pdf)} chars)")
                            else:
                                if log:
                                    print("[CARTA][FALLBACK] extrair_pdf retornou None")
                        except Exception as e:
                            if log:
                                print(f"[CARTA][FALLBACK] Erro ao extrair documento com extrair_pdf: {e}")
                    
                    # Verificar se temos texto válido
                    if not texto_completo or len(texto_completo.strip()) < 10:
                        if log:
                            print(f"[CARTA][FALLBACK] Não foi possível extrair texto da intimação")
                        continue
                    
                    # Verificar se é intimação de correio
                    correio_detectado = 'NAO APAGAR NENHUM CARACTERE' in texto_completo.upper()
                    
                    if correio_detectado:
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
    
    # 7. Formatar como blocos simples
    blocos_formatados = []
    
    for i, item in enumerate(dados_mais_recentes, 1):
        bloco = []
        bloco.append(f"    Id Pje: {item.get('ID_PJE', '')}")
        
        # Rastreamento
        rastreamento = item.get('RASTREAMENTO', '')
        if rastreamento:
            if rastreamento.startswith('http'):
                codigo_match = re.search(r'codigo=([A-Z]{2}\\d{9}BR)', rastreamento)
                if codigo_match:
                    codigo = codigo_match.group(1)
                    bloco.append(f'    Rastreamento: <a href="{rastreamento}" target="_blank">{codigo}</a>')
                else:
                    bloco.append(f'    Rastreamento: <a href="{rastreamento}" target="_blank">{rastreamento}</a>')
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
                    codigo_match = re.search(r'codigo=([A-Z]{{2}}\\d{{9}}BR)', rastreamento)
                    if codigo_match:
                        codigo = codigo_match.group(1)
                        conteudo_html += f'            <div>Rastreamento: <a href="{rastreamento}" target="_blank">{codigo}</a></div>\n'
                    else:
                        conteudo_html += f'            <div>Rastreamento: <a href="{rastreamento}" target="_blank">{rastreamento}</a></div>\n'
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
            print("[CARTA] Iniciando juntada automática via anexos.py...")
        
        from anexos import carta_wrapper
        
        resultado_juntada = carta_wrapper(driver, debug=log, ecarta_html=conteudo_final)
        
        if resultado_juntada and log:
            print("[CARTA] ✅ Juntada automática concluída com sucesso!")
        elif log:
            print("[CARTA] ⚠️ Juntada automática falhou ou foi pulada")
            
    except Exception as e:
        if log:
            print(f"[CARTA] ⚠️ Erro na juntada automática: {e}")
    
    return conteudo_final