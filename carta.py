from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re

def carta(driver, log=True):
    """
    Função simplificada para gerar tabela HTML com dados de intimações do eCarta.
    Colunas: ID, DESTINATARIO, RESULTADO, RASTREAMENTO
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
                            
                            if log:
                                print(f"[CARTA] ID da intimação de correio encontrado: {id_curto}")
                                print(f"[CARTA] Número do processo: {process_number}")
                        else:
                            if log:
                                print("[CARTA][DEBUG] Intimação não é de correio")
                    else:
                        if log:
                            print("[CARTA][ERRO] Não foi possível extrair texto da intimação")
                        
                except Exception as e:
                    if log:
                        print(f"[CARTA] Erro ao processar intimação: {e}")
            else:
                if log:
                    print("[CARTA] Primeiro item não é uma intimação")
        else:
            if log:
                print("[CARTA] Nenhum item encontrado na timeline")
        
        if not intimation_ids or not process_number:
            if log:
                print("[CARTA] Nenhuma intimação de correio encontrada.")
            return ""
        
        if log:
            print(f"[CARTA] {len(intimation_ids)} intimações encontradas para processo {process_number}")
        
        # 2. Acessar eCarta
        ecarta_url = f"https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo={process_number}"
        driver.get(ecarta_url)
        time.sleep(2)
        
        # 3. Login se necessário
        try:
            username_field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#input_user"))
            )
            username_field.send_keys("s164283")
            driver.find_element(By.CSS_SELECTOR, "#input_password").send_keys("59Justdoit!1")
            driver.find_element(By.CSS_SELECTOR, "input.btn").click()
            time.sleep(3)
            
            # Navegar novamente para a URL após login
            driver.get(ecarta_url)
            time.sleep(2)
            if log:
                print("[CARTA] Login realizado na eCarta")
        except TimeoutException:
            if log:
                print("[CARTA] Já logado na eCarta")
        
        # 4. Extrair dados da tabela do eCarta usando JavaScript
        table_data = []
        try:
            # JavaScript para extrair dados da tabela eCarta
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
                var rows = Array.from(document.querySelectorAll('#main\\\\:tabDoc_data tr'));
                if (!rows.length) {
                    return null;
                }
                
                var data = rows.map(function(tr) {
                    var tds = tr.querySelectorAll('td');
                    var objetoTd = tds[4];
                    var objeto = objetoTd ? objetoTd.innerText.trim() : '';
                    var objetoLink = null;
                    var idTd = tds[3];
                    var idPje = idTd ? idTd.innerText.trim() : '';
                    var idPjeLink = null;
                    
                    if (idPje && /^\\d{10,}$/.test(idPje)) {
                        idPjeLink = criarUrlDocumento(idPje);
                    }
                    
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
                            }
                        }
                    }
                    
                    return {
                        dataEnvio: tds[0] ? tds[0].innerText.trim() : '',
                        dataEntrega: tds[1] ? tds[1].innerText.trim() : '',
                        idPje: idPje,
                        idPjeLink: idPjeLink,
                        objeto: objeto,
                        objetoLink: objetoLink,
                        status: tds[5] ? tds[5].innerText.trim() : '',
                        destinatario: tds[6] ? tds[6].innerText.trim() : '',
                        orgaoJulgador: tds[7] ? tds[7].innerText.trim() : ''
                    };
                });
                
                function parseDate(d) {
                    var parts = d.split('/');
                    return new Date(parts[2] + '-' + parts[1] + '-' + parts[0]);
                }
                
                var maxDataEnvio = data.map(function(d) { return d.dataEnvio; })
                    .filter(function(d) { return /\\d{2}\\/\\d{2}\\/\\d{4}/.test(d); })
                    .map(parseDate)
                    .sort(function(a, b) { return b - a; })[0];
                
                var recentes = data.filter(function(d) {
                    if (!/\\d{2}\\/\\d{2}\\/\\d{4}/.test(d.dataEnvio)) return false;
                    return parseDate(d.dataEnvio).getTime() === maxDataEnvio.getTime();
                });
                
                return recentes;
            }
            
            return extrairDadosTabela();
            """
            
            # Executa o JavaScript e obtém os dados
            ecarta_data = driver.execute_script(js_script)
            
            if not ecarta_data:
                if log:
                    print("[CARTA] Nenhum dado encontrado na tabela eCarta")
                return ""
            
            # Converte os dados para o formato esperado e filtra por IDs das intimações
            for item in ecarta_data:
                id_pje = item.get('idPje', '')
                destinatario = item.get('destinatario', '')
                status = item.get('status', '')
                objeto = item.get('objeto', '')
                objeto_link = item.get('objetoLink', '')
                
                # Usa o link de rastreamento se disponível, senão usa o status
                rastreamento = objeto_link if objeto_link else (objeto if objeto else status)
                
                # Verifica se o ID está na nossa lista de intimações
                for intimation_id in intimation_ids:
                    if intimation_id in id_pje or id_pje in intimation_id:
                        table_data.append({
                            "ID": intimation_id,
                            "DESTINATARIO": destinatario,
                            "RESULTADO": status,
                            "RASTREAMENTO": rastreamento
                        })
                        break
        
        except Exception as e:
            if log:
                print(f"[CARTA] Erro ao extrair dados da tabela eCarta via JavaScript: {e}")
            return ""
        
        # 5. Gerar tabela HTML
        if not table_data:
            if log:
                print("[CARTA] Nenhum dado correlacionado encontrado na tabela eCarta")
            return ""
        

        html_table = generate_html_table(table_data)

        if log:
            print(f"[CARTA] Tabela HTML gerada com {len(table_data)} registros")
            print("[CARTA] Tabela copiável gerada - use Ctrl+A, Ctrl+C para copiar")

        # Exibir tabela no console para fácil cópia
        print("\n" + "="*80)
        print("TABELA CARTA - COPIE O CONTEÚDO ABAIXO:")
        print("="*80)
        print(html_table)
        print("="*80 + "\n")


        # 4. Voltar para a página anterior (/detalhe) usando driver.back()
        try:
            if log:
                print("[CARTA] Voltando para página anterior (/detalhe)...")
            driver.back()
            time.sleep(3)  # Aguarda carregamento
            if log:
                print("[CARTA] Retornou para página de detalhes do processo")
        except Exception as e:
            if log:
                print(f"[CARTA] Erro ao voltar para página anterior: {e}")

        # 5. Chamar função rastreamento do anexos.py para criar certidão, passando o html_table diretamente
        if log:
            print("[CARTA] Chamando função rastreamento do anexos.py para criar certidão...")

        try:
            from anexos import rastreaamento as anexos_rastreamento
            # Passa o html_table diretamente como argumento extra
            resultado_anexo = anexos_rastreamento(driver, debug=log, ecarta_html=html_table)
            if resultado_anexo:
                if log:
                    print("[CARTA] Certidão eCarta criada e anexada com sucesso!")
            else:
                if log:
                    print("[CARTA] Falha ao criar certidão eCarta")
        except Exception as e:
            if log:
                print(f"[CARTA] Erro ao chamar função carta do anexos.py: {e}")

        return html_table
        
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
                            id_match = re.search(r'Id: ([a-f0-9]+)', aria)
                            id_curto = id_match.group(1) if id_match else item.get_attribute('id')
                            # Extrai número do processo (primeira vez)
                            if not process_number:
                                proc_match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})', texto_completo)
                                if proc_match:
                                    process_number = proc_match.group(1)
                            
                            # Adiciona linha à tabela com campos vazios
                            intimation_rows.append({
                                "ID": id_curto,
                                "DESTINATARIO": "",
                                "RESULTADO": "",
                                "RASTREAMENTO": ""
                            })
                            
                            if log:
                                print(f"[CARTA] ID da intimação de correio encontrado: {id_curto}")
            except Exception as e:
                if log:
                    print(f"[CARTA] Erro ao processar item {idx+1}: {e}")
                continue
        
        # Gera tabela HTML se encontrou intimações
        if intimation_rows:
            html_table = generate_html_table(intimation_rows)
            if log:
                print(f"[CARTA] Tabela HTML gerada com {len(intimation_rows)} intimações de correio")
                print("\n" + "="*80)
                print("TABELA INTIMAÇÕES RECENTES - COPIE O CONTEÚDO ABAIXO:")
                print("="*80)
                print(html_table)
                print("="*80 + "\n")
            return html_table
        else:
            if log:
                print("[CARTA] Nenhuma intimação de correio encontrada nas datas recentes")
            return ""
            
    except Exception as e:
        if log:
            print(f"[CARTA] Erro ao gerar tabela de intimações recentes: {e}")
        return ""