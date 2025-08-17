# ===== FUNÇÕES DE EXTRAÇÃO DE CONTEÚDO PARA ATOS.PY =====

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import re
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Importar função de salvamento do anexos.py
try:
    from anexos import salvar_conteudo_clipboard
except ImportError:
    def salvar_conteudo_clipboard(conteudo, numero_processo, tipo_conteudo, debug=False):
        """Fallback caso anexos.py não esteja disponível"""
        print(f"[FALLBACK] Salvando: {tipo_conteudo} - {conteudo[:50]}...")
        return True

def coletar_link_ato_timeline(driver, numero_processo, debug=False):
    """
    Extrai link de validação de atos da timeline seguindo a ordem:
    1- Sentença, 2- Decisão, 3- Despacho (primeira ocorrência encontrada)
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo
        debug: Boolean para logs detalhados
        
    Returns:
        bool: True se coletou com sucesso, False caso contrário
    """
    def log_msg(msg):
        if debug:
            print(f"[LINK_ATO] {msg}")

    def extrair_numero_processo_cnj_da_pagina():
        """Tenta extrair o número CNJ do processo da página (DOM)."""
        try:
            # 1) Procurar próximo ao ícone de copiar número
            seletor_icon = 'span[aria-label*="Copia o número do processo"]'
            try:
                icon_spans = driver.find_elements(By.CSS_SELECTOR, seletor_icon)
            except Exception:
                icon_spans = []
            cnj_regex = r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
            for sp in icon_spans:
                try:
                    cont = sp.find_element(By.XPATH, './..')
                    for _ in range(3):
                        txt = cont.text.strip()
                        if txt:
                            m = re.search(cnj_regex, txt)
                            if m:
                                return m.group(0)
                        cont = cont.find_element(By.XPATH, './..')
                except Exception:
                    continue
            # 2) Fallback: varrer texto do body
            try:
                body_text = driver.execute_script('return document.body ? document.body.innerText : "";') or ''
                m = re.search(cnj_regex, body_text)
                if m:
                    return m.group(0)
            except Exception:
                pass
        except Exception:
            pass
        return None
    
    log_msg(f"Iniciando coleta de link de ato para processo {numero_processo}")
    
    try:
        # Ordem de prioridade para busca
        tipos_ato = ['Sentença', 'Decisão', 'Despacho']
        
        for tipo_ato in tipos_ato:
            log_msg(f"Buscando primeira ocorrência de: {tipo_ato}")
            
            # Busca mais abrangente por texto que contenha o tipo de ato
            elementos_timeline = []
            
            # Múltiplas estratégias de busca
            estrategias_busca = [
                f"//span[contains(text(), '{tipo_ato}')]",
                f"//*[contains(text(), '{tipo_ato}')]",
                f"//div[contains(@class, 'movimento')]//span[contains(text(), '{tipo_ato}')]",
                f"//div[contains(@class, 'timeline')]//span[contains(text(), '{tipo_ato}')]"
            ]
            
            for estrategia in estrategias_busca:
                try:
                    elementos = driver.find_elements(By.XPATH, estrategia)
                    if elementos:
                        elementos_timeline = elementos
                        log_msg(f"✅ Encontrados {len(elementos)} elementos usando: {estrategia}")
                        break
                except Exception as e:
                    log_msg(f"⚠️ Estratégia falhou: {estrategia} - {e}")
                    continue
            
            if elementos_timeline:
                log_msg(f"✅ Total de {len(elementos_timeline)} elemento(s) do tipo '{tipo_ato}' encontrado(s)")
                
                # Pega o primeiro elemento encontrado
                primeiro_elemento = elementos_timeline[0]
                log_msg(f"✅ Processando primeiro elemento de '{tipo_ato}'")
                
                # Clica no elemento para expandir/selecionar (com scroll para garantir visibilidade)
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", primeiro_elemento)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", primeiro_elemento)
                    log_msg(f"✅ Elemento '{tipo_ato}' clicado e expandido")
                    time.sleep(1)  # Aguarda expansão
                except Exception as click_err:
                    log_msg(f"⚠️ Erro ao clicar no elemento: {click_err}")
                    # Continua mesmo se não conseguir clicar
                
                # PASSO CRÍTICO: Ativar aba para recuperar cabeçalho
                log_msg(f"Ativando aba para recuperar cabeçalho após seleção de '{tipo_ato}'...")
                
                try:
                    # Pressiona TAB para ativar a aba e recuperar o cabeçalho
                    from selenium.webdriver.common.keys import Keys
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.TAB)
                    log_msg("✅ TAB pressionado para ativar aba e recuperar cabeçalho")
                    time.sleep(2)  # Aguarda mais tempo para cabeçalho carregar completamente
                except Exception as tab_err:
                    log_msg(f"⚠️ Erro ao pressionar TAB: {tab_err}")
                    # Continua mesmo se não conseguir pressionar TAB
                
                # NOVA ESTRATÉGIA: Clicar no ícone do número do processo e extrair número do documento
                log_msg(f"Implementando nova estratégia para '{tipo_ato}': número do processo + número do documento")
                
                # Aguarda um momento adicional para garantir que o cabeçalho esteja disponível
                time.sleep(1)
                
                try:
                    # PASSO 1: Clicar no ícone que copia o número do processo
                    log_msg("1. Buscando ícone para copiar número do processo...")
                    
                    # Seletor para o ícone que copia o número do processo
                    seletor_processo = 'span[aria-label*="Copia o número do processo"] i.far.fa-copy.fa-lg'
                    
                    icones_processo = driver.find_elements(By.CSS_SELECTOR, seletor_processo)
                    
                    if icones_processo:
                        icone_processo = None
                        for icone in icones_processo:
                            if icone.is_displayed():
                                icone_processo = icone
                                log_msg("✅ Ícone para copiar número do processo encontrado")
                                break
                        
                        if icone_processo:
                            # Clica no ícone do número do processo
                            driver.execute_script("arguments[0].scrollIntoView(true);", icone_processo)
                            time.sleep(0.3)
                            driver.execute_script("arguments[0].click();", icone_processo)
                            log_msg("✅ Clique no ícone do número do processo executado")
                            time.sleep(1)
                        else:
                            log_msg("⚠️ Ícone do número do processo não visível")
                    else:
                        log_msg("⚠️ Ícone do número do processo não encontrado")
                    
                    # PASSO 2: Extrair o número do documento
                    log_msg("2. Extraindo número do documento...")
                    
                    numero_documento = None
                    metodo_usado = None
                    
                    # ESTRATÉGIA ÚNICA: Seletor específico que funcionou
                    log_msg("Extraindo via seletor específico baseado no HTML...")
                    try:
                        # Seletor que funcionou: span dentro de div com display:block
                        seletor_documento_especifico = 'div[style="display: block;"] span'
                        log_msg(f"Seletor usado: {seletor_documento_especifico}")
                        spans_documento = driver.find_elements(By.CSS_SELECTOR, seletor_documento_especifico)
                        log_msg(f"Elementos encontrados: {len(spans_documento)}")
                        
                        for i, span in enumerate(spans_documento):
                            texto = span.text.strip()
                            log_msg(f"  Span {i}: '{texto}'")
                            if "Número do documento:" in texto:
                                # Extrai o número após os dois pontos
                                partes = texto.split("Número do documento:")
                                if len(partes) > 1:
                                    numero_documento = partes[1].strip()
                                    metodo_usado = f"Seletor: {seletor_documento_especifico}"
                                    log_msg(f"✅ Número do documento extraído: {numero_documento}")
                                    log_msg(f"✅ Método usado: {metodo_usado}")
                                    break
                        
                        if not numero_documento:
                            log_msg("❌ Nenhum span continha 'Número do documento:'")
                            
                    except Exception as e:
                        log_msg(f"❌ Erro na extração: {e}")
                        # DEBUG básico em caso de erro
                        try:
                            todos_spans = driver.find_elements(By.TAG_NAME, 'span')
                            spans_com_documento = []
                            for span in todos_spans:
                                texto = span.text.strip()
                                if texto and "documento" in texto.lower():
                                    spans_com_documento.append(texto)
                            
                            if spans_com_documento:
                                log_msg(f"DEBUG: Spans contendo 'documento': {spans_com_documento}")
                            else:
                                log_msg("DEBUG: Nenhum span contendo 'documento' encontrado")
                        except Exception:
                            pass
                    
                    if numero_documento:
                        # PASSO 3: Montar o link de validação
                        log_msg("3. Montando link de validação...")
                        
                        link_validacao = f"https://pje.trt2.jus.br/pjekz/validacao/{numero_documento}?instancia=1"
                        log_msg(f"✅ Link de validação construído: {link_validacao}")
                        
                        # PASSO 4: Salvar o link
                        log_msg("4. Salvando link no clipboard...")
                        log_msg(f"Parâmetros de salvamento:")
                        log_msg(f"  - conteudo: {link_validacao}")
                        log_msg(f"  - numero_processo: '{numero_processo}' (tipo: {type(numero_processo)})")
                        log_msg(f"  - tipo_conteudo: 'link_ato_{tipo_ato.lower()}_validacao'")
                        
                        # Preferir CNJ (copiado/visível) para registrar no clipboard
                        numero_cnj = extrair_numero_processo_cnj_da_pagina()
                        if numero_cnj:
                            log_msg(f"  - CNJ detectado na página: {numero_cnj}")
                        else:
                            log_msg("  - CNJ não detectado; usando identificador recebido")
                        # Garantir que numero_processo é string válida
                        numero_processo_safe = str(numero_cnj or numero_processo) if (numero_cnj or numero_processo) else "PROCESSO_NAO_INFORMADO"
                        log_msg(f"  - numero_processo_safe: '{numero_processo_safe}'")
                        
                        sucesso = salvar_conteudo_clipboard(
                            conteudo=link_validacao,
                            numero_processo=numero_processo_safe,
                            tipo_conteudo=f"link_ato_{tipo_ato.lower()}_validacao",
                            debug=debug
                        )
                        
                        if sucesso:
                            log_msg(f"✅ Link de validação de '{tipo_ato}' salvo com sucesso!")
                            return True
                        else:
                            log_msg(f"❌ Falha ao salvar link de validação de '{tipo_ato}'")
                    else:
                        log_msg(f"❌ Não foi possível extrair número do documento para '{tipo_ato}'")
                        
                except Exception as nova_estrategia_err:
                    log_msg(f"❌ Erro na nova estratégia de extração: {nova_estrategia_err}")
                
                # Se chegou aqui para este tipo de ato, significa que encontrou o ato mas não conseguiu extrair
                # Como a prioridade é: primeiro que acha, para de procurar
                log_msg(f"❌ Não foi possível coletar link do '{tipo_ato}' - abortando busca nos demais tipos")
                break  # Para de tentar outros tipos (Decisão, Despacho) pois já achou uma Sentença mas falhou
                    
            else:
                log_msg(f"⚠️ Nenhum elemento do tipo '{tipo_ato}' encontrado na timeline")
        
        log_msg("❌ Nenhum link de ato foi coletado (Sentença, Decisão ou Despacho)")
        return False
        
    except Exception as e:
        log_msg(f"❌ Erro geral na coleta de link de ato: {e}")
        import traceback
        if debug:
            log_msg(f"Traceback completo: {traceback.format_exc()}")
        return False


def coletar_conteudo_js_generico(driver, numero_processo, seletor_js, tipo_conteudo, debug=False):
    """
    Função genérica para coletar conteúdo usando JavaScript.
    Pode ser usada para extrair dados de páginas complexas.
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo
        seletor_js: String com código JavaScript para extrair o conteúdo
        tipo_conteudo: String identificando o tipo de conteúdo (ex: "dados_processo", "informacoes_parte")
        debug: Boolean para logs detalhados
        
    Returns:
        bool: True se coletou com sucesso, False caso contrário
    """
    def log_msg(msg):
        if debug:
            print(f"[CONTEUDO_JS] {msg}")
    
    log_msg(f"Iniciando coleta genérica JS para processo {numero_processo}")
    log_msg(f"Tipo de conteúdo: {tipo_conteudo}")
    
    try:
        # Executa o JavaScript personalizado
        resultado = driver.execute_script(seletor_js)
        
        if resultado:
            # Se o resultado for um objeto/dict, converte para string legível
            if isinstance(resultado, dict):
                conteudo = "\n".join([f"{k}: {v}" for k, v in resultado.items()])
            elif isinstance(resultado, list):
                conteudo = "\n".join([str(item) for item in resultado])
            else:
                conteudo = str(resultado)
            
            log_msg(f"✅ Conteúdo extraído via JS: {conteudo[:100]}...")
            
            # Salva no sistema de clipboard parametrizável
            sucesso = salvar_conteudo_clipboard(
                conteudo=conteudo,
                numero_processo=numero_processo,
                tipo_conteudo=tipo_conteudo,
                debug=debug
            )
            
            if sucesso:
                log_msg(f"✅ Conteúdo '{tipo_conteudo}' salvo no clipboard!")
                return True
            else:
                log_msg(f"❌ Falha ao salvar conteúdo '{tipo_conteudo}' no clipboard")
                return False
        else:
            log_msg(f"⚠️ JavaScript retornou resultado vazio ou nulo")
            return False
            
    except Exception as e:
        log_msg(f"❌ Erro na coleta genérica JS: {e}")
        return False


def coletar_elemento_por_seletor(driver, numero_processo, seletor_css, tipo_conteudo, atributo=None, debug=False):
    """
    Função genérica para coletar conteúdo de elementos por seletor CSS.
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo  
        seletor_css: String com seletor CSS do elemento
        tipo_conteudo: String identificando o tipo de conteúdo
        atributo: String com nome do atributo a extrair (None = texto do elemento)
        debug: Boolean para logs detalhados
        
    Returns:
        bool: True se coletou com sucesso, False caso contrário
    """
    def log_msg(msg):
        if debug:
            print(f"[ELEMENTO_CSS] {msg}")
    
    log_msg(f"Iniciando coleta por seletor CSS para processo {numero_processo}")
    log_msg(f"Seletor: {seletor_css}")
    log_msg(f"Tipo de conteúdo: {tipo_conteudo}")
    
    try:
        # Busca o elemento
        elemento = driver.find_element(By.CSS_SELECTOR, seletor_css)
        
        if elemento and elemento.is_displayed():
            # Extrai conteúdo do elemento
            if atributo:
                conteudo = elemento.get_attribute(atributo)
                log_msg(f"✅ Atributo '{atributo}' extraído: {conteudo[:50]}...")
            else:
                conteudo = elemento.text.strip()
                log_msg(f"✅ Texto do elemento extraído: {conteudo[:50]}...")
            
            if conteudo:
                # Salva no sistema de clipboard parametrizável
                sucesso = salvar_conteudo_clipboard(
                    conteudo=conteudo,
                    numero_processo=numero_processo,
                    tipo_conteudo=tipo_conteudo,
                    debug=debug
                )
                
                if sucesso:
                    log_msg(f"✅ Conteúdo '{tipo_conteudo}' salvo no clipboard!")
                    return True
                else:
                    log_msg(f"❌ Falha ao salvar conteúdo '{tipo_conteudo}' no clipboard")
                    return False
            else:
                log_msg(f"⚠️ Elemento encontrado mas conteúdo vazio")
                return False
        else:
            log_msg(f"❌ Elemento não encontrado ou não visível: {seletor_css}")
            return False
            
    except Exception as e:
        log_msg(f"❌ Erro na coleta por seletor CSS: {e}")
        return False


def coletar_dados_siscon(driver, numero_processo, parametros=None, debug=False):
    """
    Extrai dados completos do SISCON (Sistema de Controle de Contas Judiciais).
    Integrado com o sistema de clipboard.txt via anexos.py.
    
    Esta função:
    1. Abre nova aba para SISCON
    2. Busca pelo número do processo
    3. Para cada conta judicial com saldo > 0:
       - Clica no ícone de expansão para mostrar depósitos
       - Extrai: número da conta, total disponível, detalhes dos depósitos
    4. Salva dados estruturados no clipboard.txt via anexos.salvar_conteudo_clipboard
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo
        parametros: Dict com configurações opcionais:
            - url_siscon: URL customizada (padrão: TRT2)
            - expandir_depositos: Se deve expandir detalhes (padrão: True)
        debug: Boolean para logs detalhados
        
    Returns:
        bool: True se coletou com sucesso, False caso contrário
    """
    def log_msg(msg):
        if debug:
            print(f"[COLETA_SISCON] {msg}")
    
    log_msg(f"Iniciando coleta SISCON para processo {numero_processo}")
    
    try:
        # Configurações padrão
        config = parametros or {}
        url_siscon = config.get('url_siscon', 'https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/new')
        expandir_depositos = config.get('expandir_depositos', True)
        
        # Captura aba original
        aba_original = driver.current_window_handle
        log_msg(f"Aba original: {aba_original}")
        
        # ===== ETAPA 1: ABRIR SISCON EM NOVA ABA =====
        log_msg("Abrindo SISCON em nova aba...")
        driver.execute_script(f"window.open('{url_siscon}', '_blank');")
        time.sleep(3)
        
        # Muda para aba SISCON
        abas_abertas = driver.window_handles
        aba_siscon = None
        
        for aba in abas_abertas:
            if aba != aba_original:
                driver.switch_to.window(aba)
                if 'alvaraeletronico' in driver.current_url:
                    aba_siscon = aba
                    log_msg(f"✅ Aba SISCON: {driver.current_url}")
                    break
        
        if not aba_siscon:
            log_msg("❌ Aba SISCON não encontrada")
            return False
        
        # ===== ETAPA 2: BUSCAR PROCESSO =====
        log_msg("Preenchendo e buscando processo...")
        time.sleep(3)
        
        # Preenche número do processo
        campo_processo = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'numeroProcesso'))
        )
        campo_processo.clear()
        campo_processo.send_keys(numero_processo)
        log_msg(f"✅ Número inserido: {numero_processo}")
        
        # Clica buscar
        botao_buscar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'bt_buscar'))
        )
        botao_buscar.click()
        log_msg("✅ Busca executada")
        
        # Aguarda resultados
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'dados_pesquisados'))
        )
        log_msg("✅ Resultados carregados")
        time.sleep(2)
        
        # ===== ETAPA 3: EXTRAIR DADOS =====
        log_msg("Extraindo dados das contas judiciais...")
        
        dados_siscon = {
            'numero_processo': numero_processo,
            'contas': [],
            'total_geral': 0.0
        }
        
        # Procura tabela de contas
        try:
            tabela_contas = driver.find_element(By.ID, 'table_contas')
            linhas_conta = driver.find_elements(By.CSS_SELECTOR, 'tr[id^="linhaConta_"]')
            log_msg(f"✅ Encontradas {len(linhas_conta)} contas")
            
            for idx, linha in enumerate(linhas_conta):
                try:
                    # Número da conta (2ª coluna)
                    celula_conta = linha.find_element(By.CSS_SELECTOR, 'td:nth-child(2)')
                    numero_conta = celula_conta.text.strip()
                    
                    # Valor disponível
                    celula_disponivel = linha.find_element(By.CSS_SELECTOR, 'td[id*="saldo_corrigido_conta_"]')
                    valor_texto = celula_disponivel.text.strip()
                    
                    # Converte valor
                    valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_texto)
                    if valor_match:
                        valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
                        total_disponivel = float(valor_str)
                    else:
                        total_disponivel = 0.0
                    
                    log_msg(f"Conta {numero_conta}: R$ {total_disponivel:.2f}")
                    
                    # Só processa contas com saldo > 0
                    if total_disponivel > 0:
                        conta_dados = {
                            'numero_conta': numero_conta,
                            'total_disponivel': total_disponivel,
                            'depositos': []
                        }
                        dados_siscon['total_geral'] += total_disponivel
                        
                        # ===== EXPANDIR DEPÓSITOS (OPCIONAL) =====
                        if expandir_depositos:
                            try:
                                # Clica no ícone de expansão
                                icone_expansao = linha.find_element(By.CSS_SELECTOR, 'img[src*="soma-ico.png"]')
                                from selenium.webdriver.common.action_chains import ActionChains
                                ActionChains(driver).move_to_element(icone_expansao).click().perform()
                                log_msg(f"✅ Expandido depósitos da conta {numero_conta}")
                                time.sleep(2)
                                
                                # Busca linhas de depósito (implementação simplificada)
                                # Nota: O HTML real pode variar, ajustar conforme necessário
                                linhas_deposito = driver.find_elements(By.CSS_SELECTOR, f'tr[id*="parcela"], tr.linha-parcela')
                                
                                for linha_dep in linhas_deposito:
                                    if linha_dep.is_displayed():
                                        colunas = linha_dep.find_elements(By.TAG_NAME, 'td')
                                        if len(colunas) >= 3:
                                            try:
                                                data_deposito = colunas[0].text.strip()
                                                depositante = colunas[1].text.strip()
                                                valor_dep_texto = colunas[-1].text.strip()
                                                
                                                # Converte valor do depósito
                                                valor_dep_match = re.search(r'R\$\s*([0-9.,]+)', valor_dep_texto)
                                                if valor_dep_match and data_deposito and depositante:
                                                    valor_dep_str = valor_dep_match.group(1).replace('.', '').replace(',', '.')
                                                    valor_deposito = float(valor_dep_str)
                                                    
                                                    if valor_deposito > 0:
                                                        conta_dados['depositos'].append({
                                                            'data': data_deposito,
                                                            'depositante': depositante,
                                                            'valor_disponivel': valor_deposito
                                                        })
                                            except:
                                                continue
                                
                                log_msg(f"✅ Extraídos {len(conta_dados['depositos'])} depósitos")
                                
                            except Exception as e:
                                log_msg(f"⚠️ Erro ao expandir depósitos: {e}")
                        
                        dados_siscon['contas'].append(conta_dados)
                
                except Exception as e:
                    log_msg(f"⚠️ Erro na conta {idx}: {e}")
                    continue
        
        except Exception as e:
            log_msg(f"❌ Erro ao processar tabela: {e}")
            return False
        
        # ===== ETAPA 4: FORMATAR E SALVAR NO CLIPBOARD.TXT =====
        log_msg("Formatando e salvando dados...")
        
        # Formata conteúdo
        conteudo_formatado = f"=== DADOS SISCON ===\n"
        conteudo_formatado += f"Processo: {dados_siscon['numero_processo']}\n"
        conteudo_formatado += f"Total Geral: R$ {dados_siscon['total_geral']:.2f}\n"
        conteudo_formatado += f"Contas com Saldo: {len(dados_siscon['contas'])}\n\n"
        
        if dados_siscon['contas']:
            for conta in dados_siscon['contas']:
                conteudo_formatado += f"🏛️ CONTA: {conta['numero_conta']}\n"
                conteudo_formatado += f"💰 TOTAL: R$ {conta['total_disponivel']:.2f}\n"
                
                if conta['depositos']:
                    conteudo_formatado += "📋 DEPÓSITOS:\n"
                    for dep in conta['depositos']:
                        conteudo_formatado += f"  • {dep['data']} | {dep['depositante']} | R$ {dep['valor_disponivel']:.2f}\n"
                else:
                    conteudo_formatado += "📋 DEPÓSITOS: Não expandidos\n"
                
                conteudo_formatado += "\n" + "="*50 + "\n\n"
        else:
            conteudo_formatado += "⚠️ NENHUMA CONTA COM SALDO DISPONÍVEL\n"
        
        # Salva usando função do anexos.py
        sucesso = salvar_conteudo_clipboard(
            conteudo=conteudo_formatado,
            numero_processo=numero_processo,
            tipo_conteudo="siscon_dados",
            debug=debug
        )
        
        if sucesso:
            log_msg("✅ Dados salvos no clipboard.txt")
        
        # ===== ETAPA 5: FECHAR ABA =====
        try:
            driver.close()
            driver.switch_to.window(aba_original)
            log_msg("✅ Retornado à aba original")
        except:
            pass
        
        log_msg(f"✅ Coleta concluída: {len(dados_siscon['contas'])} contas")
        return True
        
    except Exception as e:
        log_msg(f"❌ Erro na coleta SISCON: {e}")
        
        # Tenta voltar à aba original
        try:
            driver.switch_to.window(aba_original)
        except:
            pass
        
        return False


# ===== WRAPPER PARA USAR COM AS FUNÇÕES EXISTENTES =====

def executar_coleta_parametrizavel(driver, numero_processo, tipo_coleta, parametros=None, debug=False):
    """
    Wrapper principal para executar diferentes tipos de coleta de conteúdo.
    Usado pelas funções ato_judicial e comunicacao_judicial.
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: String com número do processo
        tipo_coleta: String identificando o tipo de coleta:
            - "ecarta": Coleta e-carta (já implementado em anexos.py)
            - "link_ato": Coleta link de ato da timeline
            - "js_generico": Executa JavaScript customizado
            - "elemento_css": Extrai conteúdo por seletor CSS
        parametros: Dict com parâmetros específicos para cada tipo de coleta
        debug: Boolean para logs detalhados
        
    Returns:
        bool: True se executou com sucesso, False caso contrário
    """
    def log_msg(msg):
        if debug:
            print(f"[COLETA_PARAM] {msg}")
    
    log_msg(f"Executando coleta parametrizável: {tipo_coleta}")
    
    try:
        if tipo_coleta == "ecarta":
            from anexos import coletar_ecarta
            return coletar_ecarta(driver, numero_processo, debug=debug)
            
        elif tipo_coleta == "link_ato":
            return coletar_link_ato_timeline(driver, numero_processo, debug=debug)
            
        elif tipo_coleta == "js_generico":
            if not parametros or 'codigo_js' not in parametros:
                log_msg("❌ Parâmetro 'codigo_js' obrigatório para tipo 'js_generico'")
                return False
            
            tipo_conteudo = parametros.get('tipo_conteudo', 'conteudo_js')
            return coletar_conteudo_js_generico(
                driver, numero_processo, 
                parametros['codigo_js'], tipo_conteudo, debug
            )
            
        elif tipo_coleta == "elemento_css":
            if not parametros or 'seletor_css' not in parametros:
                log_msg("❌ Parâmetro 'seletor_css' obrigatório para tipo 'elemento_css'")
                return False
            
            tipo_conteudo = parametros.get('tipo_conteudo', 'conteudo_elemento')
            atributo = parametros.get('atributo', None)
            return coletar_elemento_por_seletor(
                driver, numero_processo, 
                parametros['seletor_css'], tipo_conteudo, atributo, debug
            )
            
        elif tipo_coleta == "siscon":
            # Nova coleta: dados do SISCON
            return coletar_dados_siscon(driver, numero_processo, parametros, debug)
            
        else:
            log_msg(f"❌ Tipo de coleta não reconhecido: {tipo_coleta}")
            return False
            
    except Exception as e:
        log_msg(f"❌ Erro geral na coleta parametrizável: {e}")
        return False
# ===== EXEMPLOS DE USO =====

def exemplo_uso_coleta_atos():
    """
    Exemplos de como usar o sistema de coleta parametrizável
    """
    
    # Exemplo 1: Coletar e-carta
    # executar_coleta_parametrizavel(driver, "1234567890", "ecarta", debug=True)
    
    # Exemplo 2: Coletar link de ato da timeline  
    # executar_coleta_parametrizavel(driver, "1234567890", "link_ato", debug=True)
    
    # Exemplo 3: JavaScript genérico para extrair dados específicos
    parametros_js = {
        'codigo_js': '''
            // Exemplo: extrair número de processos relacionados
            var elementos = document.querySelectorAll('.numero-processo');
            return Array.from(elementos).map(el => el.textContent.trim());
        ''',
        'tipo_conteudo': 'processos_relacionados'
    }
    # executar_coleta_parametrizavel(driver, "1234567890", "js_generico", parametros_js, debug=True)
    
    # Exemplo 4: Elemento CSS específico
    parametros_css = {
        'seletor_css': '.valor-causa',
        'tipo_conteudo': 'valor_da_causa',
        'atributo': 'data-valor'  # ou None para texto
    }
    # executar_coleta_parametrizavel(driver, "1234567890", "elemento_css", parametros_css, debug=True)
    
    # Exemplo 5: Dados do SISCON (Sistema de Controle de Contas Judiciais)
    parametros_siscon = {
        'url_siscon': 'https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/new',
        'expandir_depositos': True  # Se deve expandir e extrair detalhes dos depósitos
    }
    # executar_coleta_parametrizavel(driver, "1001320-19.2020.5.02.0703", "siscon", parametros_siscon, debug=True)
    
    pass
