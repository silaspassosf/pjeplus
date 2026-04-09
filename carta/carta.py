
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

# Imports Fix
from Fix.extracao import extrair_direto, extrair_pdf, extrair_dados_processo


CALENDARIO_DIAS_UTEIS_PATH = Path('dias-uteis-trt2-2025.json')
_CALENDARIO_DIAS_UTEIS = None
_CALENDARIO_INTERVALO = None


def _carregar_calendario_dias_uteis():
    global _CALENDARIO_DIAS_UTEIS, _CALENDARIO_INTERVALO
    if _CALENDARIO_DIAS_UTEIS is not None:
        return _CALENDARIO_DIAS_UTEIS, _CALENDARIO_INTERVALO

    dias_calendario = set()
    intervalo = None

    if CALENDARIO_DIAS_UTEIS_PATH.exists():
        try:
            with open(CALENDARIO_DIAS_UTEIS_PATH, 'r', encoding='utf-8') as arquivo:
                conteudo = json.load(arquivo)
            for entrada in conteudo.get('dias_uteis', []):
                try:
                    data_convertida = datetime.fromisoformat(entrada).date()
                    dias_calendario.add(data_convertida)
                except ValueError:
                    continue
            if dias_calendario:
                intervalo = (min(dias_calendario), max(dias_calendario))
        except Exception:
            dias_calendario = set()
            intervalo = None

    _CALENDARIO_DIAS_UTEIS = dias_calendario
    _CALENDARIO_INTERVALO = intervalo
    return _CALENDARIO_DIAS_UTEIS, _CALENDARIO_INTERVALO


def _somar_dias_uteis(data_base, quantidade):
    if not data_base or quantidade <= 0:
        return data_base

    dias_calendario, intervalo = _carregar_calendario_dias_uteis()
    data_atual = data_base
    acumulado = 0
    seguranca = 0

    while acumulado < quantidade and seguranca < 1000:
        data_atual += timedelta(days=1)
        seguranca += 1
        dentro_intervalo = intervalo and intervalo[0] <= data_atual <= intervalo[1]

        if dias_calendario and dentro_intervalo:
            if data_atual in dias_calendario:
                acumulado += 1
        else:
            if data_atual.weekday() < 5:
                acumulado += 1

    if acumulado < quantidade:
        return None

    return data_atual


def _parse_data_ecarta(valor):
    if not valor:
        return None

    valor_limpo = valor.strip()
    if not valor_limpo:
        return None

    parte_data = re.split(r'[\sT]', valor_limpo)[0]
    formatos = ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d')

    for fmt in formatos:
        try:
            return datetime.strptime(parte_data, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(parte_data).date()
    except ValueError:
        return None


def _obter_numero_processo(driver, log):
    process_number = None
    try:
        if log:
            print('[CARTA] Extraindo dados do processo via Fix.extracao (dadosatuais.json)...')
        extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
    except Exception as e:
        if log:
            print(f"[CARTA][DADOSATUAIS] Falha ao executar extrair_dados_processo: {e}")

    try:
        p = Path('dadosatuais.json')
        if p.exists():
            j = json.loads(p.read_text(encoding='utf-8'))
            maybe = j.get('numero') if isinstance(j, dict) else None
            if isinstance(maybe, (list, tuple)) and len(maybe) > 0:
                process_number = maybe[0]
            elif isinstance(maybe, str):
                process_number = maybe
            if process_number and log:
                print(f"[CARTA][DADOSATUAIS] Número obtido de dadosatuais.json: {process_number}")
    except Exception as e:
        if log:
            print(f"[CARTA][DADOSATUAIS] Erro ao ler dadosatuais.json: {e}")

    return process_number

def carta(driver, log=True, limite_intimacoes=None):
    """
    Função principal para processar intimações de carta no PJe
    """
    process_number = _obter_numero_processo(driver, log)
    
    # 2. Buscar intimações na timeline do PJe
    intimation_ids = []
    if log:
        print("[CARTA] Iniciando busca de intimações na timeline...")
    
    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    if log:
        print(f"[CARTA] Encontrados {len(itens)} itens na timeline")
    
    intimacoes_info = []  # Lista de dicts com {id: str, tem_desconsideracao: bool}
    limite = limite_intimacoes if limite_intimacoes is not None else float('inf')
    count_intimacoes = 0
    intimacao_encontrada = False

    def _texto_e_correio(texto):
        if not texto:
            return False
        upper = texto.upper()
        if 'NAO APAGAR NENHUM CARACTERE' not in upper:
            return False
        return 'VIA ECARTA REG' in upper or 'VIA ECARTA AR' in upper

    def _extrair_texto_completo():
        texto_completo = None
        try:
            res = extrair_direto(driver, timeout=10, debug=False, formatar=True)
            if res and isinstance(res, dict) and res.get('sucesso'):
                texto_completo = res.get('conteudo') or res.get('conteudo_bruto')
                if texto_completo:
                    texto_completo = texto_completo.lower()
                    if log:
                        print(f"[CARTA][DEBUG] Texto extraído com sucesso usando extrair_direto ({len(texto_completo)} chars) via {res.get('metodo')}")
            else:
                if log:
                    print("[CARTA][DEBUG] extrair_direto retornou sem sucesso")
        except Exception as e:
            if log:
                print(f"[CARTA][DEBUG] Erro ao extrair documento com extrair_direto: {e}")

        if not texto_completo or len(texto_completo.strip()) < 10:
            try:
                if log:
                    print("[CARTA][DEBUG] Tentando alternativa com extrair_pdf...")
                texto_pdf = extrair_pdf(driver, log=False)
                if texto_pdf:
                    texto_completo = texto_pdf.lower()
                    if log:
                        print(f"[CARTA][DEBUG] Texto extraído com sucesso usando extrair_pdf ({len(texto_pdf)} chars)")
                else:
                    if log:
                        print("[CARTA][DEBUG] extrair_pdf retornou None")
            except Exception as e:
                if log:
                    print(f"[CARTA][DEBUG] Erro ao extrair documento com extrair_pdf: {e}")

        return texto_completo

    def _processar_item(item, contexto):
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            link_text = link.text.strip()
            
            # Filtrar apenas documentos do tipo "Intimação(" - ignorar certidões e outros
            if not link_text.startswith('Intimação('):
                return None
            
            aria = link.get_attribute('aria-label') or ''

            if log:
                print(f"[CARTA] ({contexto}) Clicando na intimação: {link_text}")

            link.click()
            time.sleep(2)

            texto_completo = _extrair_texto_completo()
            if not texto_completo or len(texto_completo.strip()) < 10:
                if log:
                    print("[CARTA][DEBUG] Não foi possível extrair texto da intimação")
                return None

            texto_upper = texto_completo.upper()
            correio_detectado = _texto_e_correio(texto_upper)
            tem_desconsideracao = False
            tem_via_reg = 'VIA ECARTA REG' in texto_upper

            if correio_detectado:
                tem_desconsideracao = bool(re.search(r'desconsider[aã][çc][ãa]o', texto_completo, re.IGNORECASE))
                if log:
                    print(f"[CARTA][DEBUG] Correio confirmado (via eCarta) - Desconsideração: {tem_desconsideracao}")

            if log:
                print(f"[CARTA][DEBUG] Procurando 'NAO APAGAR NENHUM CARACTERE' + frase eCarta - Encontrado: {correio_detectado}")
                if correio_detectado:
                    print(f"[CARTA][DEBUG] VIA ECARTA REG detectado: {tem_via_reg}")

            if log:
                print(f"[CARTA][DEBUG] Procurando 'NAO APAGAR NENHUM CARACTERE' + frase eCarta - Encontrado: {correio_detectado}")

            if not correio_detectado:
                if log:
                    print("[CARTA][DEBUG] Intimação não é de correio - continuando")
                return None

            link_text = link.text.strip()
            id_match = re.search(r'-\s*([a-f0-9]+)\s*$', link_text)
            if id_match:
                id_curto = id_match.group(1)
            else:
                id_match = re.search(r'Id: ([a-f0-9]+)', aria)
                if id_match:
                    id_curto = id_match.group(1)
                else:
                    id_curto = item.get_attribute('id')

            if log:
                print(f"[CARTA] ID da intimação de correio encontrado: {id_curto}")
                print(f"[CARTA] Número do processo: {process_number}")
            return id_curto, tem_desconsideracao
        except Exception as e:
            if log:
                print(f"[CARTA] Erro ao processar intimação ({contexto}): {e}")
            return None

    if itens:
        primeiro_item = itens[0]
        # Verificar se o primeiro item é especificamente uma Intimação(
        try:
            link_primeiro = primeiro_item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            texto_link = link_primeiro.text.strip()
            if texto_link.startswith('Intimação('):
                if log:
                    print(f"[CARTA] Primeiro item é intimação válida: {texto_link[:100]}...")
                resultado = _processar_item(primeiro_item, 'primeiro item')
                if resultado:
                    id_curto, tem_desconsideracao = resultado
                    intimation_ids.append(id_curto)
                    intimacoes_info.append({
                        'id': id_curto,
                        'tem_desconsideracao': tem_desconsideracao,
                    })
                    intimacao_encontrada = True
        except Exception:
            pass  # Se não conseguir encontrar o link, seguir para fallback

    if not intimacao_encontrada:
        if log:
            print("[CARTA][FALLBACK] Buscando sequencialmente por intimações de correio...")
        for idx, item in enumerate(itens):
            if count_intimacoes >= limite:
                if log:
                    print(f"[CARTA][FALLBACK] Limite de {limite} intimações atingido")
                break

            resultado = _processar_item(item, f'item {idx + 1}')
            if resultado:
                id_curto, tem_desconsideracao = resultado
                intimation_ids.append(id_curto)
                intimacoes_info.append({
                    'id': id_curto,
                    'tem_desconsideracao': tem_desconsideracao,
                })
                count_intimacoes += 1
                intimacao_encontrada = True
                break


    if not intimation_ids:
        if log:
            print("[CARTA] Nenhuma intimação de correio encontrada.")
        return ""

    if log:
        print(f"[CARTA] {len(intimation_ids)} intimações encontradas para processo {process_number}")

    if not process_number:
        process_number = _obter_numero_processo(driver, log)
        if not process_number:
            if log:
                print('[CARTA][ERRO] Não foi possível obter o número do processo via dadosatuais.json. Abortando eCarta.')
            return ""
    
    # 3. Acessar eCarta em nova aba
    if log:
        print("[CARTA] Abrindo eCarta em nova aba...")

    original_window = driver.current_window_handle
    original_window_count = len(driver.window_handles)

    if log:
        print(f"[CARTA] Abas antes de abrir eCarta: {original_window_count}")

    # Garantir que temos um número de processo válido antes de montar o link do eCarta.
    # Nova abordagem: executar apenas `extrair_dados_processo` e ler `dadosatuais.json`.
    if not process_number:
        if log:
            print('[CARTA] Extraindo dados do processo via Fix.extracao (somente este método)...')
        try:
            extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
        except Exception as e:
            if log:
                print(f"[CARTA] Falha em extrair_dados_processo: {e}")

        # Ler o arquivo `dadosatuais.json` gerado pela função
        try:
            p = Path('dadosatuais.json')
            if p.exists():
                j = json.loads(p.read_text(encoding='utf-8'))
                maybe = j.get('numero') if isinstance(j, dict) else None
                if isinstance(maybe, (list, tuple)) and len(maybe) > 0:
                    process_number = maybe[0]
                elif isinstance(maybe, str):
                    process_number = maybe
                if process_number and log:
                    print(f"[CARTA][DADOSATUAIS] Número obtido de dadosatuais.json: {process_number}")
        except Exception as e:
            if log:
                print(f"[CARTA][DADOSATUAIS] Erro ao ler dadosatuais.json: {e}")

        if not process_number:
            if log:
                print('[CARTA][ERRO] Não foi possível obter o número do processo via dadosatuais.json. Abortando eCarta.')
            return ""

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
    
    # Aguardar carregamento completo da página eCarta
    max_aguardar_carregamento = 20  # 20 segundos máximo
    for tentativa in range(max_aguardar_carregamento):
        current_url = driver.current_url
        if "ecarta" in current_url.lower() and current_url != "about:blank":
            if log:
                print(f"[CARTA] ✅ Página eCarta carregada após {tentativa + 1}s: {current_url}")
            break
        time.sleep(1)
        if tentativa == max_aguardar_carregamento - 1:
            if log:
                print(f"[CARTA] ⚠️ Timeout aguardando carregamento eCarta após {max_aguardar_carregamento}s")
    
    # Validar se estamos na aba correta
    if "ecarta" not in driver.current_url.lower():
        if log:
            print(f"[CARTA][ERRO] Não estamos na aba correta do eCarta!")
            print(f"[CARTA][ERRO] URL atual: {driver.current_url}")
        return ""
    
    time.sleep(3)
    
    # 4. Login se necessário
    try:
        from Fix.core import aguardar_renderizacao_nativa

        if not aguardar_renderizacao_nativa(driver, '#input_user', 'aparecer', timeout=5):
            raise TimeoutException('Campo de usuário não apareceu')

        username_field = driver.find_element(By.CSS_SELECTOR, '#input_user')
        if log:
            print("[CARTA] Fazendo login no eCarta...")
        username_field.send_keys("s164283")
        driver.find_element(By.CSS_SELECTOR, "#input_password").send_keys("SpFintra861!")
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
                datas_correlacionadas = []
                for item in ecarta_data:
                    id_pje = item.get('idPje', '')

                    if not id_pje:
                        continue

                    for intimation_id in intimation_ids:
                        if not intimation_id:
                            continue

                        if intimation_id in id_pje or id_pje in intimation_id:
                            data_envio = item.get('dataEnvio', '')
                            if data_envio and data_envio not in datas_correlacionadas:
                                datas_correlacionadas.append(data_envio)
                            if log:
                                print(f"[CARTA] ✅ CORRELAÇÃO ENCONTRADA! ID_PJE={id_pje} corresponde à intimação={intimation_id} (data {data_envio})")
                            break
                
                if datas_correlacionadas:
                    if log:
                        print(f"[CARTA] Coletando TODAS as intimações das datas: {datas_correlacionadas}")
                    
                    for item in ecarta_data:
                        item_data_envio = item.get('dataEnvio', '')

                        if item_data_envio not in datas_correlacionadas:
                            continue

                        rastreamento_final = item.get('objetoLink', '') or item.get('objeto', '')
                        table_data.append({
                            "ID_PJE": item.get('idPje', ''),
                            "RASTREAMENTO": rastreamento_final,
                            "DESTINATARIO": item.get('destinatario', ''),
                            "DATA_ENVIO": item_data_envio,
                            "DATA_ENTREGA": item.get('dataEntrega', ''),
                            "STATUS": item.get('status', ''),
                        })
                        
                        if log:
                            print(f"[CARTA] ✅ Coletado da mesma data: ID={item.get('idPje', '')}, Data={item_data_envio}")
                    
                    correlacao_encontrada = True
                    if log:
                        print(f"[CARTA] ✅ {len(table_data)} registros coletados das datas {datas_correlacionadas}!")
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
    
    prazo_texto = ""
    data_base_prazo = None

    # NOVA LÓGICA: Encontrar a data de entrega mais recente entre todas as intimações
    datas_entrega_validas = []
    for item in dados_mais_recentes:
        data_entrega = _parse_data_ecarta(item.get('DATA_ENTREGA', ''))
        if data_entrega:
            datas_entrega_validas.append(data_entrega)
    
    if datas_entrega_validas:
        # Usar a data de entrega mais recente como base para o prazo
        data_base_prazo = max(datas_entrega_validas)
        if log:
            print(f"[CARTA] ✅ Data de entrega mais recente encontrada: {data_base_prazo.strftime('%d/%m/%Y')}")
            if len(datas_entrega_validas) > 1:
                print(f"[CARTA] ℹ️ {len(datas_entrega_validas)} datas de entrega diferentes - usando a mais recente")
    else:
        # Fallback: usar data de envio se não houver data de entrega
        for item in dados_mais_recentes:
            data_base_prazo = _parse_data_ecarta(item.get('DATA_ENVIO', ''))
            if data_base_prazo:
                if log:
                    print(f"[CARTA] ⚠️ Usando data de envio como fallback: {data_base_prazo.strftime('%d/%m/%Y')}")
                break

    if data_base_prazo:
        # NOVA LÓGICA: Verificar se há alguma intimação com status "devolvido"
        tem_devolvido = any(re.search(r'devolvid[oa]', item.get('STATUS', ''), re.IGNORECASE) for item in dados_mais_recentes)
        
        if tem_devolvido:
            # Se há intimação devolvida, não calcular prazo
            prazo_texto = ""
            if log:
                print(f"[CARTA] Intimação devolvida detectada - prazo não será calculado")
        else:
            # NOVA LÓGICA: Determinar prazo baseado na presença de desconsideração
            tem_alguma_desconsideracao = any(info.get('tem_desconsideracao') for info in intimacoes_info)
            
            if tem_alguma_desconsideracao:
                # Se tem desconsideração, prazo é 15 dias
                prazo_principal = _somar_dias_uteis(data_base_prazo, 15)
                prazo_secundario = _somar_dias_uteis(data_base_prazo, 8)
                
                if prazo_principal and prazo_secundario:
                    prazo_texto = f"Prazo: 15 dias ({prazo_principal.strftime('%d/%m/%Y')})"
                    if log:
                        print(f"[CARTA] Prazo de 15 dias aplicado (desconsideração detectada): {prazo_texto}")
            else:
                # Se não tem desconsideração, prazo é 8 dias
                prazo_principal = _somar_dias_uteis(data_base_prazo, 8)
                prazo_secundario = _somar_dias_uteis(data_base_prazo, 15)
                
                if prazo_principal and prazo_secundario:
                    prazo_texto = f"Prazo: 8 dias ({prazo_principal.strftime('%d/%m/%Y')})"
                    if log:
                        print(f"[CARTA] Prazo de 8 dias aplicado (sem desconsideração): {prazo_texto}")
            
            # Fallback para o formato antigo se algo der errado
            if not prazo_texto:
                prazo_8 = _somar_dias_uteis(data_base_prazo, 8)
                prazo_15 = _somar_dias_uteis(data_base_prazo, 15)
                if prazo_8 and prazo_15:
                    prazo_texto = f"Prazos: 15 ({prazo_15.strftime('%d/%m/%Y')}) - 08 ({prazo_8.strftime('%d/%m/%Y')})"
                    if log:
                        print(f"[CARTA] Usando formato de prazo antigo (fallback): {prazo_texto}")
        
        if not prazo_texto and log:
            print(f"[CARTA] Não foi possível calcular prazos úteis")
    elif log:
        print("[CARTA] Data de entrega/envio não encontrada para cálculo dos prazos")

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

    if prazo_texto:
        html_prazo = (
            '<p class="corpo" style="font-size: 12pt; line-height: normal; '
            'margin-left: 0px !important; text-align: justify !important; '
            'text-indent: 4.5cm;">&nbsp; &nbsp; '
            f'{prazo_texto}</p>'
        )
        html_para_juntada = f"{html_para_juntada}\n{html_prazo}" if html_para_juntada else html_prazo
    
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

    if prazo_texto:
        conteudo_final = (conteudo_final + '\n\n' if conteudo_final else '') + prazo_texto
    
    # 8. Salvar em clipboard.txt
    try:
        from PEC.anexos import salvar_conteudo_clipboard
        
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
    
    # 9. Exibir resultado no console (HTML individual removido - tudo vai para clipboard.txt)
    if log:
        print("\n" + "="*80)
        print("DADOS DO E-CARTA EXTRAÍDOS:")
        print("="*80)
        print(conteudo_final)
        print("="*80 + "\n")
    
    # 10. Chamar wrapper de anexos para juntada automática
    try:
        if log:
            print("[CARTA] Iniciando juntada automática via anexos.py com HTML formatado...")
        
        from PEC.anexos import carta_wrapper
        
        # Usar o HTML gerado para juntada (ao invés do texto simples)
        resultado_juntada = carta_wrapper(driver, debug=log, ecarta_html=html_para_juntada)
        
        if resultado_juntada and log:
            print("[CARTA] ✅ Juntada automática concluída com sucesso!")
        elif log:
            print("[CARTA] ⚠️ Juntada automática falhou ou foi pulada")
            
    except Exception as e:
        if log:
            print(f"[CARTA] ⚠️ Erro na juntada automática: {e}")
    
    # 11. Após juntada correta, voltar para /detalhe e chamar mov_prazo
    try:
        if log:
            print("[CARTA] Voltando para aba /detalhe após juntada...")
        
        # URLs que JÁ INDICAM "Aguardando prazo" - não precisa forçar mov_prazo
        URLS_JA_EM_PRAZO = [
            '/minutar',
            '/aguardando-prazo',
            '/assinar'
        ]
        
        # Verificar se há múltiplas abas e trocar para a aba /detalhe
        abas_atuais = driver.window_handles
        aba_detalhe = None
        url_detalhe = None
        
        for aba in abas_atuais:
            driver.switch_to.window(aba)
            url_atual = driver.current_url
            if '/detalhe' in url_atual:
                aba_detalhe = aba
                url_detalhe = url_atual
                break
        
        if aba_detalhe:
            driver.switch_to.window(aba_detalhe)
            if log:
                print("[CARTA] ✅ Foco trocado para aba /detalhe")
            
            # Verificar se URL já indica "Aguardando prazo"
            ja_em_prazo = any(url_pattern in url_detalhe for url_pattern in URLS_JA_EM_PRAZO)
            
            if ja_em_prazo:
                if log:
                    print(f"[CARTA] ✓ URL já indica tarefa em prazo ({url_detalhe}) - pulando mov_prazo")
            else:
                # Chamar mov_prazo apenas se URL não indicar prazo
                if log:
                    print("[CARTA] Executando mov_prazo para definir prazo de cumprimento...")
                
                resultado_prazo = None  # mov_prazo não disponível em atos
                
                if resultado_prazo:
                    if log:
                        print("[CARTA] ✅ mov_prazo executado com sucesso!")
                else:
                    if log:
                        print("[CARTA] ⚠️ mov_prazo falhou ou não foi necessário")
        else:
            if log:
                print("[CARTA] ⚠️ Aba /detalhe não encontrada, permanecendo na aba atual")
            
            # Se não encontrou /detalhe, tentar mov_prazo mesmo assim
            if log:
                print("[CARTA] Executando mov_prazo para definir prazo de cumprimento...")
            
            resultado_prazo = None  # mov_prazo não disponível em atos
                
    except Exception as e:
        if log:
            print(f"[CARTA] ⚠️ Erro ao executar mov_prazo: {e}")
    
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
        from PEC.anexos import carta_wrapper
        
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