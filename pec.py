import os
import json
import time
import re
from datetime import datetime
from selenium.webdriver.common.by import By

# ===== FUNÇÕES DE PROGRESSO PARA PEC =====
def carregar_progresso_pec():
    """Carrega o estado de progresso do arquivo JSON específico para PEC"""
    try:
        if os.path.exists("progresso_pec.json"):
            with open("progresso_pec.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[PROGRESSO_PEC][AVISO] Erro ao carregar progresso: {e}")
    return {"processos_executados": [], "session_active": True, "last_update": None}

def salvar_progresso_pec(progresso):
    """Salva o estado de progresso no arquivo JSON específico para PEC"""
    try:
        progresso["last_update"] = datetime.now().isoformat()
        with open("progresso_pec.json", "w", encoding="utf-8") as f:
            json.dump(progresso, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[PROGRESSO_PEC][ERRO] Falha ao salvar progresso: {e}")

def extrair_numero_processo_pec(driver):
    """Extrai o número do processo da URL ou elemento da página (adaptado para PEC)"""
    try:
        url = driver.current_url
        if "processo/" in url:
            match = re.search(r"processo/(\d+)", url)
            if match:
                return match.group(1)
        try:
            candidatos = driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho')
            for elemento in candidatos:
                texto = elemento.text.strip()
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                if match:
                    return re.sub(r'[^\d]', '', match.group(1))
        except:
            pass
        return None
    except Exception as e:
        print(f"[PROGRESSO_PEC][ERRO] Falha ao extrair número do processo: {e}")
        return None

def verificar_acesso_negado_pec(driver):
    """Verifica se estamos na página de acesso negado no sistema PEC"""
    try:
        url_atual = driver.current_url
        return "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower()
    except Exception as e:
        print(f"[PROGRESSO_PEC][ERRO] Falha ao verificar acesso negado: {e}")
        return False

def processo_ja_executado_pec(numero_processo, progresso):
    """Verifica se o processo já foi executado no fluxo PEC"""
    if not numero_processo:
        return False
    return numero_processo in progresso.get("processos_executados", [])

def marcar_processo_executado_pec(numero_processo, progresso):
    """Marca processo como executado no fluxo PEC"""
    if numero_processo and numero_processo not in progresso.get("processos_executados", []):
        progresso.setdefault("processos_executados", []).append(numero_processo)
        salvar_progresso_pec(progresso)
        print(f"[PROGRESSO_PEC] Processo {numero_processo} marcado como executado")

def recuperar_sessao_pec(driver):
    """Tenta recuperar sessão após acesso negado no sistema PEC"""
    try:
        print("[RECOVERY_PEC][SESSÃO] Detectado acesso negado, tentando recuperar sessão...")
        login_url = "https://alvaraeletronico.trt2.jus.br/portaltrtsp/login.jsp"
        driver.get(login_url)
        time.sleep(3)
        if fazer_login_siscon_manual(driver, debug=True):
            print("[RECOVERY_PEC][SESSÃO] ✅ Login realizado com sucesso")
            url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
            driver.get(url_atividades)
            time.sleep(5)
            try:
                from Fix import aplicar_filtro_100
                if aplicar_filtro_100(driver):
                    print("[RECOVERY_PEC][SESSÃO] ✅ Filtro de 100 itens reaplicado")
                    time.sleep(2)
                coluna_observacao = driver.find_element(By.XPATH, '//div[@role="column" and @class="th-elemento-class ng-star-inserted" and contains(text(), "Observação")]')
                coluna_observacao.click()
                print("[RECOVERY_PEC][SESSÃO] ✅ Lista reorganizada por observação")
                time.sleep(3)
                return True
            except Exception as filter_error:
                print(f"[RECOVERY_PEC][SESSÃO][ERRO] Falha ao reaplicar filtros: {filter_error}")
        else:
            print("[RECOVERY_PEC][SESSÃO] ❌ Falha no login")
        return False
    except Exception as e:
        print(f"[RECOVERY_PEC][SESSÃO][ERRO] Falha na recuperação: {e}")
        return False

def resetar_progresso_pec():
    """Reseta o arquivo de progresso específico para PEC"""
    try:
        if os.path.exists("progresso_pec.json"):
            os.remove("progresso_pec.json")
            print("[PROGRESSO_PEC][RESET] ✅ Arquivo de progresso removido")
        else:
            print("[PROGRESSO_PEC][RESET] ❌ Arquivo de progresso não existe")
    except Exception as e:
        print(f"[PROGRESSO_PEC][RESET][ERRO] Falha ao resetar: {e}")

def listar_processos_executados_pec():
    """Lista processos já executados no fluxo PEC"""
    progresso = carregar_progresso_pec()
    executados = progresso.get("processos_executados", [])
    if executados:
        print(f"[PROGRESSO_PEC][LIST] {len(executados)} processos já executados:")
        for i, proc in enumerate(executados, 1):
            print(f"  {i:3d}. {proc}")
    else:
        print("[PROGRESSO_PEC][LIST] Nenhum processo executado ainda")
    return executados
import time
import re
import unicodedata
from atos import (
    pec_decisao, 
    pec_editalidpj, 
    pec_cpgeral,
    pec_bloqueio)


# Flag para controlar se já foi feito login no Siscon
_siscon_login_feito = False

def fazer_login_siscon_manual(driver, debug=False):
    """
    Função para fazer login manual no Siscon/Alvará Eletrônico.
    Pausa a execução e pede para o usuário fazer login manualmente.
    
    Args:
        driver: WebDriver atual
        debug: Se True, exibe logs detalhados
        
    Returns:
        bool: True se login foi bem-sucedido
    """
    global _siscon_login_feito
    
    def log_msg(msg):
        if debug:
            print(f"[LOGIN_SISCON] {msg}")
        else:
            print(msg)  # Sempre mostra mensagens de login
    
    if _siscon_login_feito:
        log_msg("✅ Login no Siscon já foi realizado anteriormente")
        return True
    
    try:
        log_msg("🔐 NECESSÁRIO LOGIN NO SISCON/ALVARÁ ELETRÔNICO")
        log_msg("=" * 60)
        
        # Navegar para página de login
        url_login = "https://alvaraeletronico.trt2.jus.br/portaltrtsp/login.jsp"
        log_msg(f"🌐 Navegando para: {url_login}")
        
        driver.get(url_login)
        time.sleep(3)
        
        log_msg(f"📍 URL atual: {driver.current_url}")
        
        # Instruções para o usuário
        print("\n" + "🚨" * 20)
        print("INSTRUÇÕES PARA LOGIN:")
        print("1. Faça login no sistema que apareceu no navegador")
        print("2. Complete a autenticação (inclusive token do email se necessário)")
        print("3. Após fazer login com sucesso, volte aqui e pressione ENTER")
        print("4. NÃO feche o navegador!")
        print("🚨" * 20 + "\n")
        
        # Aguardar usuário fazer login
        input("⏳ Pressione ENTER após completar o login no navegador...")
        
        # Verificar se login foi bem-sucedido tentando navegar para busca
        url_busca = "https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar"
        log_msg(f"🎯 Testando acesso à página de busca: {url_busca}")
        
        driver.get(url_busca)
        time.sleep(5)
        
        url_final = driver.current_url
        log_msg(f"📍 URL após teste: {url_final}")
        
        # Verificar se foi redirecionado para login (falha) ou está na busca (sucesso)
        if 'login.jsp' in url_final:
            log_msg("❌ Login não foi realizado corretamente - ainda na página de login")
            print("\n⚠️ ERRO: Login não foi completado corretamente")
            print("Tente novamente ou verifique suas credenciais")
            return False
        
        elif 'buscar' in url_final:
            log_msg("✅ Login realizado com sucesso!")
            _siscon_login_feito = True
            print("\n🎉 LOGIN REALIZADO COM SUCESSO!")
            print("As próximas chamadas do def_Siscon usarão esta sessão")
            return True
        
        else:
            log_msg(f"⚠️ URL inesperada após login: {url_final}")
            print("\n⚠️ Status de login incerto - continuando...")
            _siscon_login_feito = True  # Assume sucesso para não pedir novamente
            return True
        
    except Exception as e:
        log_msg(f"❌ Erro durante login manual: {e}")
        print(f"\n❌ Erro: {e}")
        return False

def determinar_acao_por_observacao(observacao):
    """
    Determina a ação a ser executada baseada na observação extraída.
    
    Regras - retorna diretamente o nome da função do atos.py:
    - Sobrestamento vencido -> def_sob
    - xs pec cp -> pec_cpgeral  
    - xs pec edital -> pec_editaldec
    - pec dec -> pec_decisao
    - pec idpj -> pec_editalidpj
    - pz idpj -> ato_idpj
    - xs carta -> carta
    - xs bloq -> pec_bloqueio
    - xs parcial -> ato_bloq
    - sob {numero} -> mov_sob
    - sob chip -> def_chip
    """
    import re
    observacao_lower = observacao.lower().strip()
    # Regras mínimas para todas ações PEC
    if "pec cp" in observacao_lower:
        return "pec_cpgeral"
    elif "pec edital" in observacao_lower:
        return "pec_editaldec"
    elif "pec dec" in observacao_lower:
        return "pec_decisao"
    elif "pec idpj" in observacao_lower:
        return "pec_editalidpj"
    elif "xs carta" in observacao_lower:
        return "xs_carta"
    elif "pec bloq" in observacao_lower or "pec bloq".replace(" ","") in observacao_lower:
        return "pec_bloqueio"
    elif "xs pz carta" in observacao_lower:
        return "xs_pz_carta"
    elif re.search(r'\bsob\s+\d+', observacao_lower):
        return "mov_sob"
    elif "sob chip" in observacao_lower:
        return "def_chip"
    elif "sobrestamento vencido" in observacao_lower:
        return "def_sob"
    elif "xs pec cp" in observacao_lower:
        return "pec_cpgeral"
    elif "xs pec edital" in observacao_lower:
        return "pec_editaldec"
    elif "xs pec dec" in observacao_lower:
        return "pec_decisao"
    elif "xs pec idpj" in observacao_lower:
        return "pec_editalidpj"
    elif "pz idpj" in observacao_lower:
        return "ato_idpj"
    elif "xs carta" in observacao_lower:
        return "carta"
    elif "xs bloq" in observacao_lower:
        return "pec_bloqueio"
    elif "xs parcial" in observacao_lower:
        return "ato_bloq"
    elif "meios" in observacao_lower:
        return "ato_meios"
    elif "pec aud" in observacao_lower:
        return "pec_editalaud"
    else:
        return "PULAR"

def indexar_processo_atual_gigs(driver):
    """
    Extrai número do processo e observação da página atual de atividades GIGS.
    Assume que já está na página de detalhes do processo.
    
    Returns:
        tuple: (numero_processo, observacao) ou None se falhar
    """
    from selenium.webdriver.common.by import By
    import re
    
    try:
        # Método 1: Tentar extrair da URL atual
        url_atual = driver.current_url
        if "processo" in url_atual:
            # Extrai número da URL se disponível
            match_url = re.search(r'processo/(\d+)', url_atual)
            if match_url:
                numero_processo = match_url.group(1)
                print(f"[INDEXAR_GIGS] Número extraído da URL: {numero_processo}")
        
        # Método 2: Buscar na página por elementos que contenham o número
        try:
            # Procura por elementos que podem conter o número do processo
            candidatos = driver.find_elements(By.CSS_SELECTOR, 
                'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho')
            
            numero_processo = None
            for elemento in candidatos:
                texto = elemento.text.strip()
                # Busca padrão de número de processo: 1234567-12.2024.5.02.1234
                match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                if match:
                    numero_processo = match.group(1)
                    print(f"[INDEXAR_GIGS] Número encontrado na página: {numero_processo}")
                    break
            
            if not numero_processo:
                print("[INDEXAR_GIGS] ⚠️ Número do processo não encontrado na página")
                # Fallback: usar um identificador genérico baseado na URL
                numero_processo = f"PROC_{hash(url_atual) % 1000000}"
        
        except Exception as e:
            print(f"[INDEXAR_GIGS] ⚠️ Erro ao buscar número na página: {e}")
            numero_processo = "UNKNOWN"
        
        # Método 3: Buscar observação na estrutura HTML específica do GIGS
        observacao = ""
        try:
            print("[INDEXAR_GIGS] Procurando observação na estrutura HTML específica...")
            
            # Procura pelo elemento <span class="descricao"> que contém "Prazo: observacao"
            elementos_descricao = driver.find_elements(By.CSS_SELECTOR, 'span.descricao')
            
            for elemento in elementos_descricao:
                try:
                    texto_completo = elemento.text.strip()
                    print(f"[INDEXAR_GIGS] Texto encontrado: {texto_completo}")
                    
                    # Verifica se tem o padrão "Prazo: observacao"
                    if texto_completo.startswith('Prazo:'):
                        # Extrai a observação após "Prazo: "
                        observacao = texto_completo[6:].strip().lower()  # Remove "Prazo: " e converte para minúscula
                        observacao = observacao.rstrip('.')  # Remove ponto final se houver
                        print(f"[INDEXAR_GIGS] ✅ Observação extraída: {observacao}")
                        break
                except Exception as e:
                    print(f"[INDEXAR_GIGS] Erro ao processar elemento descricao: {e}")
                    continue
            
            if not observacao:
                print("[INDEXAR_GIGS] ⚠️ Observação não encontrada na estrutura específica")
                # Fallback: buscar qualquer texto que contenha padrões conhecidos no HTML
                texto_pagina = driver.page_source.lower()
                
                padroes_conhecidos = ['xs carta', 'xs pec cp', 'xs pec edital', 'xs bloq', 'sob chip', 'sobrestamento vencido']
                for padrao in padroes_conhecidos:
                    if padrao in texto_pagina:
                        observacao = padrao
                        print(f"[INDEXAR_GIGS] Observação encontrada no fallback: {observacao}")
                        break
                
                if not observacao:
                    observacao = "observacao nao encontrada"
                    print("[INDEXAR_GIGS] ⚠️ Usando observação padrão")
        
        except Exception as e:
            print(f"[INDEXAR_GIGS] ⚠️ Erro ao buscar observação: {e}")
            observacao = "erro ao extrair observacao"
        
        return (numero_processo, observacao)
        
    except Exception as e:
        print(f"[INDEXAR_GIGS] ❌ Erro geral ao indexar processo atual: {e}")
        return None

def executar_acao(driver, acao, numero_processo, observacao):
    """
    Executa a ação determinada no processo aberto.
    """
    
    print(f"[AÇÃO] Executando ação '{acao}' para processo {numero_processo}")
    
    try:
        if acao == "xs_pz_carta":
            print("[AÇÃO] Detectado 'xs pz carta' - executando fluxo completo")
            
            # 1. Executa função carta do carta.py
            from carta import carta
            resultado_carta = carta(driver, log=True)
            
            if not resultado_carta:
                print("[AÇÃO] ❌ Falha ao executar carta")
                return False
            
            print("[AÇÃO] ✅ Carta executada com sucesso")
            
            # 2. Executa análise de documentos (integrada ao fluxo)
            return analisar_documentos_pos_carta(driver, numero_processo, observacao)
            
        if acao == "xs_carta":
            # Executa função carta do carta.py
            from carta import carta
            resultado = carta(driver, log=True)
            return bool(resultado)
            
        elif acao == "mov_sob":
            # Executa função mov_sob do atos.py
            from atos import mov_sob
            resultado = mov_sob(driver, numero_processo, observacao)
            return bool(resultado)
            
        elif acao == "def_chip":
            # Executa função def_chip do atos.py
            from atos import def_chip
            resultado = def_chip(driver, numero_processo, observacao, debug=True)
            return bool(resultado)
            
        elif acao == "def_sob":
            # Executa função def_sob local (analisa última decisão)
            resultado = def_sob(driver, numero_processo, observacao, debug=True)
            return bool(resultado)
            
        elif acao == "pec_cpgeral":
            # Executa pec_cpgeral do atos.py
            from atos import pec_cpgeral
            resultado = pec_cpgeral(driver, terceiro=True, debug=True)
            return bool(resultado)
            
        elif acao == "pec_editaldec":
            # Executa pec_editaldec do atos.py
            from atos import pec_editaldec
            resultado = pec_editaldec(driver, debug=True)
            return bool(resultado)
            
        elif acao == "pec_decisao":
            # Executa pec_decisao do atos.py
            from atos import pec_decisao
            resultado = pec_decisao(driver, debug=True)
            return bool(resultado)
            
        elif acao == "pec_editalidpj":
            # Executa pec_editalidpj do atos.py
            from atos import pec_editalidpj
            resultado = pec_editalidpj(driver, debug=True)
            return bool(resultado)
            
        elif acao == "ato_idpj":
            # Executa ato_idpj do atos.py
            from atos import ato_idpj
            resultado = ato_idpj(driver, debug=True)
            return bool(resultado)
            
        elif acao == "pec_bloqueio":
            # Executa pec_bloqueio do atos.py  
            from atos import pec_bloqueio
            resultado = pec_bloqueio(driver, debug=True)
            return bool(resultado)
        
        elif acao == "pec_editalaud":
            # Executa pec_editalaud do atos.py  
            from atos import pec_editalaud
            resultado = pec_editalaud(driver, debug=True)
            return bool(resultado)
            
        elif acao == "ato_bloq":
            # Executa ato_bloq do atos.py
            from atos import ato_bloq
            resultado = ato_bloq(driver, debug=True)
            return bool(resultado)
            
        elif acao == "saldo":
            # Executa função saldo local (analisa alvará e consulta sistemas)
            resultado = saldo(driver, numero_processo, observacao, debug=True)
            return bool(resultado)
            
        else:
            print(f"[AÇÃO] ❌ Ação '{acao}' não reconhecida")
            return False
            
    except Exception as e:
        print(f"[AÇÃO] Erro ao executar ação '{acao}': {e}")
        return False
        return False

def analisar_documentos_pos_carta(driver, numero_processo, observacao, debug=False):
    """
    Analisa documentos após execução de carta para observação "xs pz carta".
    Busca até 4 documentos (sentença, decisão ou despacho) e aplica regras específicas.
    """
    from selenium.webdriver.common.by import By
    from Fix import extrair_documento, criar_gigs
    import time
    
    def log_msg(msg):
        if debug:
            print(f"[XS_PZ_CARTA] {msg}")
    
    log_msg(f"Iniciando análise de documentos para processo {numero_processo}")
    
    try:
        # Buscar itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            log_msg("❌ Nenhum item encontrado na timeline")
            return False
        
        log_msg(f"Encontrados {len(itens)} itens na timeline")
        
        # Contador de documentos processados
        documentos_processados = 0
        max_documentos = 4
        
        # Procurar documentos relevantes (sentença, decisão ou despacho)
        for item in itens:
            if documentos_processados >= max_documentos:
                log_msg(f"Limite de {max_documentos} documentos atingido")
                break
                
            try:
                # Verificar se é um documento relevante
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                if not link:
                    continue
                
                doc_text = link.text.lower()
                log_msg(f"Verificando documento: {doc_text}")
                
                # Verificar se é sentença, decisão ou despacho
                if not any(termo in doc_text for termo in ['sentença', 'decisão', 'despacho']):
                    continue
                
                log_msg(f"Documento relevante encontrado: {doc_text}")
                
                # Clicar no documento para abrir
                try:
                    # Rolar até o elemento para garantir visibilidade
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.5)
                    
                    # Clicar no documento
                    link.click()
                    time.sleep(2)
                    
                    log_msg("Documento aberto com sucesso")
                    
                    # Extrair conteúdo do documento
                    resultado_extracao = extrair_documento(driver, timeout=10, log=debug)
                    if not resultado_extracao or not resultado_extracao[0]:
                        log_msg("❌ Falha ao extrair conteúdo do documento")
                        continue
                    
                    texto_documento = resultado_extracao[0].lower()
                    log_msg(f"Conteúdo extraído: {texto_documento[:100]}...")
                    
                    # Aplicar regras conforme conteúdo
                    regra_aplicada = False
                    
                    # Regra a: "defiro a instauração" -> ato_idpj
                    if "defiro a instauração" in texto_documento:
                        log_msg("Regra aplicada: 'defiro a instauração' -> ato_idpj")
                        from atos import ato_idpj
                        resultado_idpj = ato_idpj(driver, debug=debug)
                        
                        if resultado_idpj:
                            log_msg("✅ ato_idpj executado com sucesso")
                            regra_aplicada = True
                        else:
                            log_msg("❌ Falha ao executar ato_idpj")
                    
                    # Regra b: "bloqueio realizado" ou "844" -> criar GIGS 1/Bruna/Liberação
                    elif "bloqueio realizado" in texto_documento or "844" in texto_documento:
                        log_msg("Regra aplicada: 'bloqueio realizado' ou '844' -> criar GIGS")
                        resultado_gigs = criar_gigs(
                            driver=driver,
                            dias_uteis=1,
                            responsavel="Bruna",
                            observacao="Liberação",
                            timeout=10,
                            log=debug
                        )
                        
                        if resultado_gigs:
                            log_msg("✅ GIGS criado com sucesso")
                            regra_aplicada = True
                        else:
                            log_msg("❌ Falha ao criar GIGS")
                    
                    # Regra c: "instaurado em face" -> ato_meios
                    elif "instaurado em face" in texto_documento:
                        log_msg("Regra aplicada: 'instaurado em face' -> ato_meios")
                        from atos import ato_meios
                        resultado_meios = ato_meios(driver, debug=debug)
                        
                        if resultado_meios:
                            log_msg("✅ ato_meios executado com sucesso")
                            regra_aplicada = True
                        else:
                            log_msg("❌ Falha ao executar ato_meios")
                    
                    if regra_aplicada:
                        documentos_processados += 1
                        log_msg(f"Documento processado com sucesso ({documentos_processados}/{max_documentos})")
                    else:
                        log_msg("⚠️ Nenhuma regra aplicável para este documento")
                    
                except Exception as e:
                    log_msg(f"❌ Erro ao processar documento: {e}")
                    continue
                    
            except Exception as e:
                log_msg(f"❌ Erro ao analisar item da timeline: {e}")
                continue
        
        log_msg(f"Análise concluída. {documentos_processados} documentos processados.")
        return documentos_processados > 0
        
    except Exception as e:
        log_msg(f"❌ Erro geral na análise de documentos: {e}")
        return False

def navegar_para_atividades(driver):
    """
    Navega para a tela de atividades do GIGS através da URL direta.
    """
    try:
        url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
        print(f"[NAVEGAR] Navegando para atividades: {url_atividades}")
        driver.get(url_atividades)
        
        # Aguarda a página carregar
        import time
        time.sleep(3)
        
        # Verifica se chegou na página correta
        if 'atividades' in driver.current_url:
            print("[NAVEGAR] ✅ Navegação para atividades bem-sucedida")
            return True
        else:
            print(f"[NAVEGAR] ❌ Erro: URL atual é {driver.current_url}")
            return False
            
    except Exception as e:
        print(f"[NAVEGAR] Erro ao navegar para atividades: {e}")
        return False

def executar_fluxo_novo():
    """
    Executa o novo fluxo conforme especificações:
    1- criar driver e executar login conforme definido em driver_config.py
    2- iniciar fluxo logo após login navegando até atividades
    3- não clicar no ícone "Atividades sem prazo" 
    4- não filtrar com xs
    5- indexar lista com a função definida de fix.py
    6- ao indexar numero do processo - atividade (observação)
    """
    # Importa configurações do driver_config.py
    from driver_config import criar_driver, login_func
    import time
    
    # Importa configurações do driver_config.py
    from driver_config import criar_driver, login_func
    print("[FLUXO_NOVO] Iniciando novo fluxo com controle de progresso...")
    progresso = carregar_progresso_pec()
    try:
        driver = criar_driver(headless=False)
        if not driver:
            print('[FLUXO_NOVO] ❌ Falha ao criar driver')
            return False
        print("[FLUXO_NOVO] ✅ Driver criado com sucesso")
        if not login_func(driver):
            print('[FLUXO_NOVO] ❌ Falha no login')
            driver.quit()
            return False
        print("[FLUXO_NOVO] ✅ Login realizado com sucesso")
    except Exception as e:
        print(f"[FLUXO_NOVO] ❌ Erro ao criar driver/login: {e}")
        return False
    try:
        if not navegar_para_atividades(driver):
            print("[FLUXO_NOVO] ❌ Falha ao navegar para atividades")
            driver.quit()
            return False
        time.sleep(5)
    except Exception as e:
        print(f"[FLUXO_NOVO] ❌ Erro ao navegar para atividades: {e}")
        driver.quit()
        return False
    print("[FLUXO_NOVO] ✅ Pulando filtros conforme solicitado")
    try:
        from Fix import aplicar_filtro_100, indexar_e_processar_lista
        print("[FLUXO_NOVO] Aplicando filtro de 100 itens por página...")
        if aplicar_filtro_100(driver):
            print("[FLUXO_NOVO] ✅ Filtro de 100 itens aplicado")
            time.sleep(2)
        else:
            print("[FLUXO_NOVO] ⚠️ Falha ao aplicar filtro de 100 itens, continuando...")
        print("[FLUXO_NOVO] Clicando na coluna 'Observação' para reorganizar a lista...")
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            coluna_observacao = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@role="column" and @class="th-elemento-class ng-star-inserted" and contains(text(), "Observação")]'))
            )
            coluna_observacao.click()
            print("[FLUXO_NOVO] ✅ Coluna 'Observação' clicada - lista reorganizada")
            time.sleep(3)
        except Exception as e:
            print(f"[FLUXO_NOVO] ⚠️ Erro ao clicar na coluna 'Observação': {e}")
            print("[FLUXO_NOVO] Continuando sem reorganizar...")
        def callback_pec_progresso(driver):
            try:
                if verificar_acesso_negado_pec(driver):
                    print("[CALLBACK_PEC] ⚠️ Acesso negado detectado! Reiniciando driver e login...")
                    # Reinicia driver e login
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    novo_driver = criar_driver(headless=False)
                    if not novo_driver:
                        print('[CALLBACK_PEC] ❌ Falha ao reiniciar driver')
                        return False
                    if not login_func(novo_driver):
                        print('[CALLBACK_PEC] ❌ Falha ao relogar')
                        novo_driver.quit()
                        return False
                    print('[CALLBACK_PEC] ✅ Driver e login reiniciados com sucesso')
                    # Navega para atividades
                    if not navegar_para_atividades(novo_driver):
                        print('[CALLBACK_PEC] ❌ Falha ao navegar para atividades após reinicio')
                        novo_driver.quit()
                        return False
                    time.sleep(5)
                    # Reaplica filtro de 100 itens
                    from Fix import aplicar_filtro_100
                    if aplicar_filtro_100(novo_driver):
                        print('[CALLBACK_PEC] ✅ Filtro de 100 itens reaplicado')
                        time.sleep(2)
                    # Reorganiza lista por observação
                    try:
                        from selenium.webdriver.common.by import By
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        coluna_observacao = WebDriverWait(novo_driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, '//div[@role="column" and @class="th-elemento-class ng-star-inserted" and contains(text(), "Observação")]'))
                        )
                        coluna_observacao.click()
                        print('[CALLBACK_PEC] ✅ Lista reorganizada por observação')
                        time.sleep(3)
                    except Exception as e:
                        print(f'[CALLBACK_PEC] ⚠️ Erro ao reorganizar lista: {e}')
                    # Retorna None para pular o processo atual e continuar a lista
                    return None
                numero_processo = extrair_numero_processo_pec(driver)
                if not numero_processo:
                    print("[CALLBACK_PEC] ❌ Não foi possível extrair número do processo")
                    return False
                if processo_ja_executado_pec(numero_processo, progresso):
                    print(f"[CALLBACK_PEC] ⏭️ Processo {numero_processo} já executado, pulando...")
                    return True
                processo_atual = indexar_processo_atual_gigs(driver)
                if not processo_atual:
                    print("[CALLBACK_PEC] ❌ Falha ao extrair dados do processo atual")
                    return False
                _, observacao = processo_atual
                print(f"[CALLBACK_PEC] Processo: {numero_processo} | Observação: {observacao}")
                acao = determinar_acao_por_observacao(observacao)
                print(f"[CALLBACK_PEC] Ação determinada: {acao}")
                if acao == "PULAR":
                    print(f"[CALLBACK_PEC] ⏭️ Pulando processo (ação não definida)")
                    marcar_processo_executado_pec(numero_processo, progresso)
                    return True
                sucesso_acao = executar_acao(driver, acao, numero_processo, observacao)
                time.sleep(2)
                if sucesso_acao:
                    marcar_processo_executado_pec(numero_processo, progresso)
                    print(f"[CALLBACK_PEC] ✅ Ação '{acao}' executada e processo marcado como concluído")
                else:
                    print(f"[CALLBACK_PEC] ❌ Falha na execução da ação '{acao}'")
                    marcar_processo_executado_pec(numero_processo, progresso)
                print(f"[CALLBACK_PEC] Processamento do callback concluído")
            except Exception as e:
                print(f"[CALLBACK_PEC] ❌ Erro no processamento: {e}")
            time.sleep(1)
        print("[FLUXO_NOVO] Iniciando processamento com indexar_e_processar_lista...")
        sucesso = indexar_e_processar_lista(driver, callback_pec_progresso)
        if sucesso:
            print("[FLUXO_NOVO] ✅ Processamento concluído com sucesso!")
        else:
            print("[FLUXO_NOVO] ⚠️ Processamento concluído com alguns problemas")
    except Exception as e:
        print(f"[FLUXO_NOVO] ❌ Erro durante o processamento: {e}")
        driver.quit()
        return False
    finally:
        input("[FLUXO_NOVO] Pressione Enter para fechar o driver...")
        try:
            driver.quit()
        except:
            pass
    return True
def aplicar_filtro_xs(driver):
    """
    Aplica filtro 'xs' na tela de atividades do GIGS.
    """
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from Fix import esperar_elemento, safe_click
        
        # Clicar no ícone fa-pen para abrir filtros
        btn_fa_pen = esperar_elemento(driver, 'i.fa-pen', timeout=15)
        if not btn_fa_pen:
            print("[FILTRO_XS] ❌ Botão fa-pen não encontrado")
            return False
        
        safe_click(driver, btn_fa_pen)
        time.sleep(2)
        
        # Aplicar filtro "xs" no campo descrição
        campo_descricao = esperar_elemento(driver, 'input[aria-label*="Descrição"]', timeout=15)
        if not campo_descricao:
            print("[FILTRO_XS] ❌ Campo descrição não encontrado")
            return False
        
        campo_descricao.clear()
        campo_descricao.send_keys('xs')
        campo_descricao.send_keys(Keys.ENTER)
        
        print('[FILTRO_XS] ✅ Filtro xs aplicado com sucesso')
        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"[FILTRO_XS] ❌ Erro ao aplicar filtro: {e}")
        return False

# Função principal para manter compatibilidade
def main():
    """
    Função principal - executa o novo fluxo
    """
    return executar_fluxo_novo()

def def_sob(driver, numero_processo, observacao, debug=False, timeout=10):
    """
    Função def_sob: analisa última decisão e executa ação baseada no conteúdo.
    """
    import re
    import time
    import unicodedata
    from selenium.webdriver.common.by import By
    from Fix import extrair_documento, extrair_pdf
    
    def log_msg(msg):
        if debug:
            print(f"[DEF_SOB] {msg}")
    
    log_msg(f"Iniciando análise de sobrestamento para processo {numero_processo}")
    log_msg(f"Observação: {observacao}")
    
    try:
        # ===== ETAPA 1: SELECIONAR ÚLTIMA DECISÃO =====
        log_msg("1. Selecionando última decisão...")
        
        # Procura itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            log_msg("❌ Nenhum item encontrado na timeline")
            return False
        
        doc_encontrado = None
        doc_link = None
        
        # Procura documento relevante (decisão, despacho ou sentença)
        for item in itens:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                
                # Verifica se é documento relevante
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                
                # Verifica se foi assinado por magistrado
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                if mag_icons:  # Se há ícone de magistrado, usa esse documento
                    doc_encontrado = item
                    doc_link = link
                    break
                    
            except Exception as e:
                log_msg(f"⚠️ Erro ao processar item: {e}")
                continue
        
        # Se não encontrou com magistrado, usa o primeiro documento relevante
        if not doc_encontrado:
            for item in itens:
                try:
                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    doc_text = link.text.lower()
                    
                    if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                        doc_encontrado = item
                        doc_link = link
                        break
                        
                except Exception:
                    continue
        
        if not doc_encontrado or not doc_link:
            log_msg("❌ Nenhum documento relevante encontrado na timeline")
            return False
        
        log_msg(f"✅ Documento encontrado: {doc_link.text}")
        
        # ===== EXTRAIR DATA DA DECISÃO =====
        data_decisao_str = None
        try:
            hora_element = doc_encontrado.find_element(By.CSS_SELECTOR, '.tl-item-hora')
            if hora_element:
                title_attr = hora_element.get_attribute('title')
                if title_attr:
                    data_parte = title_attr.split(' ')[0]  # "08/08/2023"
                    data_decisao_str = data_parte
                    log_msg(f"✅ Data da decisão extraída: {data_decisao_str}")
        except Exception as e:
            log_msg(f"⚠️ Erro ao extrair data da decisão: {e}")
        
        # Clica no documento
        doc_link.click()
        time.sleep(3)  # Aguarda carregar mais tempo

        # ===== ETAPA 2: EXTRAIR CONTEÚDO =====
        log_msg("2. Extraindo conteúdo do documento...")

        texto = None

        # Tentativa 1: Usar extrair_documento
        try:
            texto = extrair_documento(driver, regras_analise=None, timeout=timeout, log=debug)
            if texto:
                texto = texto.lower()
                log_msg("✅ Conteúdo extraído com sucesso usando extrair_documento")
            else:
                log_msg("❌ extrair_documento retornou None")
        except Exception as e:
            log_msg(f"❌ Erro ao extrair documento com extrair_documento: {e}")

        # Se extrair_documento falhou, tentar extrair_pdf
        if not texto or len(texto.strip()) < 10:
            log_msg("⚠️ Tentando alternativa com extrair_pdf...")
            try:
                texto_pdf = extrair_pdf(driver, log=debug)
                if texto_pdf:
                    texto = texto_pdf.lower()
                    log_msg("✅ Conteúdo extraído com sucesso usando extrair_pdf")
                else:
                    log_msg("❌ extrair_pdf retornou None")
            except Exception as e:
                log_msg(f"❌ Erro ao extrair documento com extrair_pdf: {e}")

        # Se ainda não temos texto, salvar HTML para diagnóstico e retornar falha
        if not texto or len(texto.strip()) < 10:
            log_msg("❌ Texto extraído muito curto ou vazio. Salvando HTML para diagnóstico.")
            try:
                preview_html = driver.page_source
                with open(f'debug_sob_preview_{numero_processo}.html', 'w', encoding='utf-8') as f:
                    f.write(preview_html)
                log_msg(f"[DIAGNOSTICO] HTML do preview salvo em debug_sob_preview_{numero_processo}.html")
            except Exception as ehtml:
                log_msg(f"[DIAGNOSTICO][ERRO] Falha ao salvar HTML do preview: {ehtml}")
            return False

        # Log do texto extraído (início apenas)
        log_texto = texto[:200] + '...' if len(texto) > 200 else texto
        log_msg(f"Texto extraído: {log_texto}")
        
        # ===== ETAPA 3: APLICAR REGRAS BASEADAS NO CONTEÚDO =====
        log_msg("3. Analisando conteúdo e aplicando regras...")
        
        # Funções auxiliares para normalização (igual ao p2.py)
        def remover_acentos(txt):
            return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
        
        def normalizar_texto(txt):
            return remover_acentos(txt.lower())
        
        def gerar_regex_geral(termo):
            termo_norm = normalizar_texto(termo)
            palavras = termo_norm.split()
            partes = [re.escape(p) for p in palavras]
            regex = r''
            for i, parte in enumerate(partes):
                regex += parte
                if i < len(partes) - 1:
                    regex += r'[\s\.,;:!\-–—]*'
            return re.compile(rf"{regex}", re.IGNORECASE)
        
        texto_normalizado = normalizar_texto(texto)
        
        # ===== ETAPA 3: ESTRUTURA DE REGRAS REFATORADA (baseada no p2.py) =====
        def executar_mov_sob_precatorio():
            """Executa mov_sob com 1 mês para precatório/RPV/pequeno valor"""
            log_msg("✅ Regra: 'precatório/RPV/pequeno valor' - executando mov_sob com 1 mês")
            try:
                from atos import mov_sob
                resultado = mov_sob(driver, numero_processo, "sob 1", debug=True, timeout=timeout)
                if resultado:
                    log_msg("✅ mov_sob com 1 mês executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do mov_sob com 1 mês")
                    return False
            except Exception as e:
                log_msg(f"❌ Erro ao executar mov_sob: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def executar_juizo_universal():
            """Executa sequência mov_fimsob + ato_fal para juízo universal"""
            log_msg("✅ Regra: 'juízo universal' - executando mov_fimsob + ato_fal")
            try:
                # Capturar informações das abas antes de executar mov_fimsob
                abas_antes_fimsob = driver.window_handles
                aba_processo_atual = driver.current_window_handle
                log_msg(f"Abas antes do mov_fimsob: {len(abas_antes_fimsob)}")
                
                # ETAPA 1: Executar mov_fimsob primeiro
                log_msg("1. Executando mov_fimsob...")
                from atos import mov_fimsob
                resultado_fimsob = mov_fimsob(driver, debug=debug)
                
                if not resultado_fimsob:
                    log_msg("❌ Falha na execução do mov_fimsob")
                    return False
                
                log_msg("✅ mov_fimsob executado com sucesso")
                
                # Verificar estado das abas após mov_fimsob
                abas_apos_fimsob = driver.window_handles
                
                # Garantir que está na aba correta para ato_fal
                if aba_processo_atual in abas_apos_fimsob:
                    driver.switch_to.window(aba_processo_atual)
                    log_msg(f"✅ Retornado à aba do processo original")
                
                # ETAPA 2: Executar ato_fal em seguida
                log_msg("2. Executando ato_fal...")
                from atos import ato_fal
                resultado_fal = ato_fal(driver, debug=debug)
                
                if resultado_fal:
                    log_msg("✅ Sequência completa (mov_fimsob + ato_fal) executada com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do ato_fal")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro durante sequência juízo universal: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def executar_def_presc():
            """Executa def_presc para prazo prescricional"""
            log_msg("✅ Regra: 'prazo prescricional' - executando def_presc")
            try:
                resultado = def_presc(driver, numero_processo, texto, data_decisao_str, debug=debug)
                if resultado:
                    log_msg("✅ def_presc executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do def_presc")
                    return False
            except Exception as e:
                log_msg(f"❌ Erro ao executar def_presc: {e}")
                return False
        
        def executar_ato_prov():
            """Executa mov_fimsob + ato_prov para autos principais"""
            log_msg("✅ Regra: 'autos principais' - executando mov_fimsob + ato_prov")
            try:
                # Capturar informações das abas antes de executar mov_fimsob
                abas_antes_fimsob = driver.window_handles
                aba_processo_atual = driver.current_window_handle
                log_msg(f"Abas antes do mov_fimsob: {len(abas_antes_fimsob)}")
                
                # ETAPA 1: Executar mov_fimsob primeiro
                log_msg("1. Executando mov_fimsob...")
                from atos import mov_fimsob
                resultado_fimsob = mov_fimsob(driver, debug=debug)
                
                if not resultado_fimsob:
                    log_msg("❌ Falha na execução do mov_fimsob")
                    return False
                
                log_msg("✅ mov_fimsob executado com sucesso")
                
                # Verificar estado das abas após mov_fimsob
                abas_apos_fimsob = driver.window_handles
                
                # Garantir que está na aba correta para ato_prov
                if aba_processo_atual in abas_apos_fimsob:
                    driver.switch_to.window(aba_processo_atual)
                    log_msg(f"✅ Retornado à aba do processo original")
                
                # ETAPA 2: Executar ato_prov em seguida
                log_msg("2. Executando ato_prov...")
                from atos import ato_prov
                resultado_prov = ato_prov(driver, debug=debug)
                
                if resultado_prov:
                    log_msg("✅ Sequência completa (mov_fimsob + ato_prov) executada com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do ato_prov")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro durante sequência autos principais: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def executar_ato_x90():
            """Executa mov_fimsob + ato_x90 para andamento da penhora no rosto"""
            log_msg("✅ Regra: 'andamento da penhora no rosto' - executando mov_fimsob + ato_x90")
            try:
                # Capturar informações das abas antes de executar mov_fimsob
                abas_antes_fimsob = driver.window_handles
                aba_processo_atual = driver.current_window_handle
                log_msg(f"Abas antes do mov_fimsob: {len(abas_antes_fimsob)}")
                
                # ETAPA 1: Executar mov_fimsob primeiro
                log_msg("1. Executando mov_fimsob...")
                from atos import mov_fimsob
                resultado_fimsob = mov_fimsob(driver, debug=debug)
                
                if not resultado_fimsob:
                    log_msg("❌ Falha na execução do mov_fimsob")
                    return False
                
                log_msg("✅ mov_fimsob executado com sucesso")
                
                # Verificar estado das abas após mov_fimsob
                abas_apos_fimsob = driver.window_handles
                
                # Garantir que está na aba correta para ato_x90
                if aba_processo_atual in abas_apos_fimsob:
                    driver.switch_to.window(aba_processo_atual)
                    log_msg(f"✅ Retornado à aba do processo original")
                
                # ETAPA 2: Executar ato_x90 em seguida
                log_msg("2. Executando ato_x90...")
                from atos import ato_x90
                resultado_x90 = ato_x90(driver, debug=debug)
                
                if resultado_x90:
                    log_msg("✅ Sequência completa (mov_fimsob + ato_x90) executada com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do ato_x90")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro durante sequência andamento da penhora no rosto: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def executar_mov_sob_retorno_feito():
            """Executa mov_sob com 4 meses para retorno do feito principal"""
            log_msg("✅ Regra: 'retorno do feito principal' - executando mov_sob com 4 meses")
            try:
                from atos import mov_sob
                resultado = mov_sob(driver, numero_processo, "sob 4", debug=True, timeout=timeout)
                if resultado:
                    log_msg("✅ mov_sob com 4 meses executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do mov_sob com 4 meses")
                    return False
            except Exception as e:
                log_msg(f"❌ Erro ao executar mov_sob: {e}")
                import traceback
                traceback.print_exc()
                return False

        # Estrutura de regras baseada no p2.py - mais clara e organizadas
        regras_def_sob = [
            # [lista_de_termos, função_de_ação, descrição]
            (['retorno do feito principal'], executar_mov_sob_retorno_feito, 'Retorno do feito principal'),
            (['precatório', 'RPV', 'pequeno valor'], executar_mov_sob_precatorio, 'Precatório/RPV/Pequeno valor'),
            (['juízo universal'], executar_juizo_universal, 'Juízo universal'),
            (['prazo prescricional'], executar_def_presc, 'Prazo prescricional'),
            (['autos principais', 'processo principal'], executar_ato_prov, 'Autos principais'),
            (['andamento da penhora no rosto'], executar_ato_x90, 'Andamento da penhora no rosto'),
        ]
        
        # Aplicar regras de forma limpa (baseado no p2.py)
        log_msg("Analisando conteúdo e aplicando regras...")
        
        for termos, acao_func, descricao in regras_def_sob:
            # Verificar se algum termo da regra está presente
            for termo in termos:
                regex = gerar_regex_geral(termo)
                if regex.search(texto_normalizado):
                    log_msg(f"Regra encontrada: {descricao} (termo: '{termo}')")
                    resultado = acao_func()
                    if resultado:
                        log_msg(f"✅ Regra '{descricao}' executada com sucesso")
                        return True
                    else:
                        log_msg(f"❌ Falha na execução da regra '{descricao}'")
                        return False
        
        # Se nenhuma regra foi aplicada
        regras_nomes = [descricao for _, _, descricao in regras_def_sob]
        log_msg("⚠️ Nenhuma regra aplicável encontrada no conteúdo")
        log_msg(f"Regras verificadas: {', '.join(regras_nomes)}")
        return False
    except Exception as e:
        log_msg(f"❌ Erro geral em def_sob: {e}")
        return False
def def_presc(driver, numero_processo, texto_decisao, data_decisao_str=None, debug=False):
    """
    Função def_presc: analisa timeline para determinar prescrição.
    
    Verifica:
    1. Data da decisão fornecida como parâmetro
    2. Se há documento do autor (ícone verde) datado de menos de 6 meses da data atual
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        texto_decisao: Texto da decisão analisada
        data_decisao_str: Data da decisão no formato DD/MM/YYYY (extraída do elemento HTML)
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    import re
    import time
    from datetime import datetime, timedelta
    from selenium.webdriver.common.by import By
    
    def log_msg(msg):
        if debug:
            print(f"[DEF_PRESC] {msg}")
    
    log_msg(f"Iniciando análise de prescrição para processo {numero_processo}")
    
    try:
        # Data atual para comparação
        data_atual = datetime.now()
        seis_meses_atras = data_atual - timedelta(days=180)  # Aproximadamente 6 meses
        
        log_msg(f"Data atual: {data_atual.strftime('%d/%m/%Y')}")
        log_msg(f"Limite (6 meses atrás): {seis_meses_atras.strftime('%d/%m/%Y')}")
        
        # ===== ETAPA 1: USAR DATA DA DECISÃO FORNECIDA =====
        # Usa a data da decisão extraída do HTML no momento da seleção
        if data_decisao_str:
            log_msg(f"✅ Data da decisão recebida: {data_decisao_str}")
        else:
            log_msg("⚠️ Data da decisão não fornecida, tentando extrair do texto...")
            # Fallback: tenta extrair do texto da decisão
            match_data_decisao = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', texto_decisao[:500])
            if match_data_decisao:
                data_decisao_str = match_data_decisao.group(1).replace('-', '/').replace('.', '/')
                log_msg(f"Data encontrada no texto da decisão: {data_decisao_str}")
            else:
                log_msg("⚠️ Não foi possível extrair data da decisão")
        
        # ===== ETAPA 2: ANALISAR TIMELINE PARA DOCUMENTOS DO AUTOR =====
        log_msg("Analisando timeline para documentos do autor...")
        
        # Procura itens da timeline (baseado no listaexec2.py - método robusto)
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
                    log_msg(f"Encontrados {len(itens)} itens na timeline com seletor: {seletor}")
                    break
            except Exception as e:
                log_msg(f"⚠️ Erro ao tentar seletor {seletor}: {e}")
        
        if not itens:
            log_msg("❌ Nenhum item encontrado na timeline")
            return False
        
        documentos_autor_recentes = []
        
        # Funções auxiliares para extração de data (baseadas no listaexec2.py - método robusto)
        def extrair_data_item(item):
            """Extrai data do item da timeline usando JavaScript (método do listaexec2.py)"""
            try:
                # Usar JavaScript para buscar data de forma robusta (igual ao listaexec2.py)
                data_texto = driver.execute_script("""
                    var item = arguments[0];
                    var dataElement = null;
                    
                    // Buscar .tl-data no próprio item
                    dataElement = item.querySelector('.tl-data[name="dataItemTimeline"]');
                    if (!dataElement) {
                        dataElement = item.querySelector('.tl-data');
                    }
                    
                    // Se não encontrou, buscar em elementos anteriores (método do listaexec2.py)
                    if (!dataElement) {
                        var elementoAnterior = item.previousElementSibling;
                        while (elementoAnterior) {
                            dataElement = elementoAnterior.querySelector('.tl-data[name="dataItemTimeline"]');
                            if (!dataElement) {
                                dataElement = elementoAnterior.querySelector('.tl-data');
                            }
                            if (dataElement) break;
                            elementoAnterior = elementoAnterior.previousElementSibling;
                        }
                    }
                    
                    return dataElement ? dataElement.textContent.trim() : null;
                """, item)
                
                if data_texto:
                    # Converter formato "17 mar. 2017" para "17/03/2017"
                    return converter_data_texto_para_numerico(data_texto)
                    
                return None
            except Exception as e:
                log_msg(f"Erro ao extrair data do item: {e}")
                return None
        
        def converter_data_texto_para_numerico(data_texto):
            try:
                meses = {
                    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                    'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                }
                
                # Regex para "17 mar. 2017"
                match = re.search(r'(\d{1,2})\s+(\w{3})\.?\s+(\d{4})', data_texto)
                if match:
                    dia = match.group(1).zfill(2)
                    mes_texto = match.group(2).lower()
                    ano = match.group(3)
                    
                    mes_numero = meses.get(mes_texto)
                    if mes_numero:
                        return f"{dia}/{mes_numero}/{ano}"
                
                # Regex para formato já numérico
                match_numerico = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', data_texto)
                if match_numerico:
                    return match_numerico.group(1).replace('-', '/').replace('.', '/')
                
                return None
            except Exception:
                return None
        
        def converter_data_para_datetime(data_str):
            try:
                if not data_str:
                    return None
                dia, mes, ano = data_str.split('/')
                return datetime(int(ano), int(mes), int(dia))
            except Exception:
                return None
        
        # ===== ABORDAGEM OTIMIZADA BASEADA NO DOCUMENTOS_EXECUCAO.JS =====
        log_msg("� Usando abordagem JavaScript otimizada para buscar polo ativo...")
        
        # Executa JavaScript diretamente para buscar primeiro documento de polo ativo
        resultado_busca = driver.execute_script("""
            // Buscar itens da timeline
            var seletoresTimeline = [
                'li.tl-item-container',
                '.tl-data .tl-item-container', 
                '.timeline-item'
            ];
            
            var itens = [];
            for (var i = 0; i < seletoresTimeline.length; i++) {
                itens = document.querySelectorAll(seletoresTimeline[i]);
                if (itens.length > 0) break;
            }
            
            console.log('[DEF_PRESC] Encontrados ' + itens.length + ' itens na timeline');
            
            var documentosAutor = [];
            var primeiroEncontrado = false;
            
            // Função para extrair data (baseada no Documentos_execucao.js)
            function extrairDataItem(item) {
                try {
                    var dataElement = item.querySelector('.tl-data[name="dataItemTimeline"]');
                    if (!dataElement) {
                        dataElement = item.querySelector('.tl-data');
                    }
                    
                    if (!dataElement) {
                        var elementoAnterior = item.previousElementSibling;
                        var tentativas = 0;
                        while (elementoAnterior && tentativas < 5) {
                            dataElement = elementoAnterior.querySelector('.tl-data[name="dataItemTimeline"]');
                            if (!dataElement) {
                                dataElement = elementoAnterior.querySelector('.tl-data');
                            }
                            if (dataElement) break;
                            elementoAnterior = elementoAnterior.previousElementSibling;
                            tentativas++;
                        }
                    }
                    
                    if (dataElement) {
                        return dataElement.textContent.trim();
                    }
                    return null;
                } catch (e) {
                    console.log('[DEF_PRESC] Erro ao extrair data:', e);
                    return null;
                }
            }
            
            var dataDecisaoReferencia = arguments[0]; // Recebe data da decisão
            console.log('[DEF_PRESC] Data da decisão de referência:', dataDecisaoReferencia);
            
            // Função para converter data em formato de comparação (YYYYMMDD)  
            function converterDataParaComparacao(dataTexto) {
                try {
                    var meses = {
                        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                        'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                        'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                    };
                    
                    // "08 ago. 2023"
                    var match = dataTexto.match(/(\\d{1,2})\\s+(\\w{3})\\.?\\s+(\\d{4})/);
                    if (match) {
                        var dia = match[1].padStart(2, '0');
                        var mesTexto = match[2].toLowerCase();
                        var ano = match[3];
                        var mesNumero = meses[mesTexto];
                        if (mesNumero) {
                            return ano + mesNumero + dia;
                        }
                    }
                    
                    // "08/08/2023"
                    var matchNumerico = dataTexto.match(/(\\d{1,2})[\/\\-\\.](\\d{1,2})[\/\\-\\.]?(\\d{4})/);
                    if (matchNumerico) {
                        var dia = matchNumerico[1].padStart(2, '0');
                        var mes = matchNumerico[2].padStart(2, '0');
                        var ano = matchNumerico[3];
                        return ano + mes + dia;
                    }
                    
                    return null;
                } catch (e) {
                    return null;
                }
            }
            
            var dataReferenciaComparacao = null;
            if (dataDecisaoReferencia) {
                dataReferenciaComparacao = converterDataParaComparacao(dataDecisaoReferencia);
            }
            
            // Buscar APENAS o primeiro item com polo ativo APÓS a decisão
            var decisaoEncontrada = !dataReferenciaComparacao; // Se sem referência, considera encontrada
            for (var idx = 0; idx < itens.length; idx++) {
                try {
                    var item = itens[idx];
                    var dataTexto = extrairDataItem(item);
                    
                    // Se ainda não encontrou a decisão, procura por ela primeiro
                    if (!decisaoEncontrada && dataReferenciaComparacao && dataTexto) {
                        var dataItemComparacao = converterDataParaComparacao(dataTexto);
                        if (dataItemComparacao === dataReferenciaComparacao) {
                            decisaoEncontrada = true;
                            console.log('[DEF_PRESC] ✓ Decisão de referência encontrada no item:', idx);
                            continue; // Continua buscando APÓS esta decisão
                        }
                    }
                    
                    // Se ainda não encontrou a decisão, continua procurando
                    if (!decisaoEncontrada) {
                        continue;
                    }
                    
                    // Verificar polo ativo APÓS encontrar a decisão
                    var iconePoloAtivo = item.querySelectorAll('i.icone-polo-ativo, i.fa-user.icone-polo-ativo, .tl-icon i.icone-polo-ativo');
                    
                    if (iconePoloAtivo.length === 0) {
                        continue; // Não é documento do autor
                    }
                    
                    console.log('[DEF_PRESC] ✓ Primeira ocorrência de polo ativo APÓS decisão no item:', idx);
                    
                    if (!dataTexto) {
                        continue;
                    }
                    
                    // Extrair documento
                    var linkDoc = item.querySelector('a.tl-documento');
                    if (linkDoc) {
                        var nomeDoc = linkDoc.textContent.trim();
                        
                        documentosAutor.push({
                            data: dataTexto,
                            nome: nomeDoc,
                            index: idx
                        });
                        
                        console.log('[DEF_PRESC] ✓ Documento do autor encontrado:', nomeDoc, '(', dataTexto, ')');
                        primeiroEncontrado = true;
                        break; // PARA na primeira ocorrência APÓS decisão
                    }
                    
                } catch (e) {
                    continue;
                }
            }
            
            return {
                sucesso: primeiroEncontrado,
                documentos: documentosAutor,
                totalItens: itens.length,
                decisaoEncontrada: decisaoEncontrada,
                dataReferencia: dataDecisaoReferencia
            };
        """, data_decisao_str)
        
        log_msg(f"� Resultado da busca JavaScript: {resultado_busca}")
        
        if resultado_busca and resultado_busca.get('sucesso'):
            log_msg("✅ JavaScript encontrou documento de polo ativo com sucesso")
            if resultado_busca.get('decisaoEncontrada'):
                log_msg("✅ Decisão de referência foi encontrada na timeline")
            elif data_decisao_str:
                log_msg("⚠️ Decisão de referência NÃO encontrada, busca geral realizada")
            
            # Processar documentos encontrados
            for doc_info in resultado_busca.get('documentos', []):
                data_texto = doc_info.get('data', '')
                nome_doc = doc_info.get('nome', '')
                
                # Converter data
                data_item_str = converter_data_texto_para_numerico(data_texto)
                if data_item_str:
                    data_item_dt = converter_data_para_datetime(data_item_str)
                    if data_item_dt and data_item_dt >= seis_meses_atras:
                        documentos_autor_recentes.append({
                            'data': data_item_str,
                            'data_dt': data_item_dt,
                            'nome': nome_doc,
                            'index': doc_info.get('index', 0)
                        })
                        log_msg(f"✅ Documento do autor dos últimos 6 meses: {nome_doc} ({data_item_str})")
                    else:
                        log_msg(f"📅 Documento do autor fora do período: {nome_doc} ({data_item_str if data_item_str else data_texto})")
        else:
            log_msg("⚠️ JavaScript não encontrou nenhum documento de polo ativo")
            
        log_msg(f"📊 Busca JavaScript concluída. Total de itens analisados: {resultado_busca.get('totalItens', 0) if resultado_busca else 0}")
        
        # ===== ETAPA 3: DECISÃO BASEADA NA ANÁLISE E DATA DA DECISÃO =====
        log_msg(f"Total de documentos do autor nos últimos 6 meses: {len(documentos_autor_recentes)}")
        
        # Primeiro, precisamos determinar a data da decisão para aplicar as regras
        data_decisao_dt = None
        if data_decisao_str:
            data_decisao_dt = converter_data_para_datetime(data_decisao_str)
        
        if not data_decisao_dt:
            log_msg("⚠️ Não foi possível determinar a data da decisão")
            # Fallback: usar data atual como referência (caso não encontre data na decisão)
            data_decisao_dt = data_atual
            log_msg(f"Usando data atual como fallback: {data_atual.strftime('%d/%m/%Y')}")
        
        # Calcular períodos para as regras
        dois_anos_atras = data_atual - timedelta(days=730)  # 2 anos
        dois_anos_5_dias_atras = data_atual - timedelta(days=735)  # 2 anos e 5 dias
        
        log_msg(f"Data da decisão: {data_decisao_dt.strftime('%d/%m/%Y')}")
        log_msg(f"2 anos atrás: {dois_anos_atras.strftime('%d/%m/%Y')}")
        log_msg(f"2 anos e 5 dias atrás: {dois_anos_5_dias_atras.strftime('%d/%m/%Y')}")
        
        # Aplicar regras específicas baseadas na data da decisão e presença de documentos do autor
        tem_documentos_autor = len(documentos_autor_recentes) > 0
        
        # REGRA 1: Data da decisão entre 2 anos e 2 anos e 5 dias + SEM ícone autor
        if dois_anos_5_dias_atras <= data_decisao_dt <= dois_anos_atras and not tem_documentos_autor:
            log_msg("📋 REGRA 1: Data entre 2 anos e 2 anos e 5 dias + SEM autor → def_ajustegigs")
            try:
                resultado = def_ajustegigs(driver, numero_processo, data_decisao_str, debug=debug)
                if resultado:
                    log_msg("✅ def_ajustegigs executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do def_ajustegigs")
                    return False
            except Exception as e:
                log_msg(f"❌ Erro ao executar def_ajustegigs: {e}")
                return False
        
        # REGRA 2: Data da decisão maior que 2 anos e 5 dias + SEM ícone autor
        elif data_decisao_dt < dois_anos_5_dias_atras and not tem_documentos_autor:
            log_msg("⚖️ REGRA 2: Data maior que 2 anos e 5 dias + SEM autor → mov_fimsob + alternar aba + ato_presc")
            try:
                from atos import mov_fimsob, ato_presc
                resultado_fimsob = mov_fimsob(driver, debug=debug)
                if not resultado_fimsob:
                    log_msg("❌ Falha na execução do mov_fimsob")
                    return False

                # Após mov_fimsob, identificar se uma nova aba foi aberta e trocar para ela para prosseguir o CLS
                abas_apos = driver.window_handles
                novas_abas = [a for a in abas_apos if a not in [driver.current_window_handle]]
                if len(abas_apos) > 1:
                    # Tenta trocar para a última aba aberta (normalmente a tarefa do processo)
                    driver.switch_to.window(abas_apos[-1])
                    log_msg(f"[CORRIGIDO] Troca para a nova aba da tarefa após mov_fimsob. Abas: {abas_apos}")
                else:
                    log_msg(f"[CORRIGIDO] Apenas uma aba detectada após mov_fimsob. Prosseguindo na atual.")

                resultado_presc = ato_presc(driver, debug=debug)
                if resultado_presc:
                    log_msg("✅ ato_presc executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do ato_presc")
                    return False
            except Exception as e:
                log_msg(f"❌ Erro ao executar mov_fimsob/ato_presc: {e}")
                return False
        
        # REGRA 3: Data da decisão menor que 2 anos + ícone autor com 6 meses ou menos
        elif data_decisao_dt > dois_anos_atras and tem_documentos_autor:
            log_msg("🔄 REGRA 3: Data menor que 2 anos + autor recente → lembrete + mov_sob 23")
            
            # Criar lembrete
            try:
                mes_atual = data_atual.strftime("%m")
                ano_atual = data_atual.strftime("%Y")
                conteudo_lembrete = f"Sobrestamento reiniciado em {mes_atual}/{ano_atual} por manifestação recente"
                
                log_msg(f"Criando lembrete: {conteudo_lembrete}")
                resultado_lembrete = criar_lembrete(driver, "prescrição", conteudo_lembrete, debug=debug)
                
                if not resultado_lembrete:
                    log_msg("⚠️ Falha ao criar lembrete, mas continuando com mov_sob")
                else:
                    log_msg("✅ Lembrete criado com sucesso")
                
            except Exception as e:
                log_msg(f"⚠️ Erro ao criar lembrete: {e}, continuando com mov_sob")
            
            # Executar mov_sob com 23 meses
            try:
                from atos import mov_sob
                # Simula observação "sob 23" para acionar mov_sob com 23 meses
                observacao_sob = "sob 23"
                resultado_mov = mov_sob(driver, numero_processo, observacao_sob, debug=debug)
                
                if resultado_mov:
                    log_msg("✅ mov_sob 23 meses executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do mov_sob 23")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro ao executar mov_sob 23: {e}")
                return False
        
        # CASO PADRÃO: Não se encaixa em nenhuma regra específica
        else:
            log_msg("⚠️ Situação não se encaixa nas regras específicas")
            log_msg(f"Data decisão > 2 anos? {data_decisao_dt > dois_anos_atras}")
            log_msg(f"Tem documentos autor? {tem_documentos_autor}")
            
            if tem_documentos_autor:
                log_msg("✅ Há documentos do autor recentes - prescrição INTERROMPIDA")
                for doc in documentos_autor_recentes:
                    log_msg(f"  - {doc['nome']} ({doc['data']})")
            else:
                log_msg("⚠️ NÃO há documentos do autor recentes")
            
            # TODO: Definir ação padrão se necessário
            log_msg("Nenhuma ação específica executada")
            return True
        
        log_msg("✅ Análise de prescrição concluída")
        return True
        
    except Exception as e:
        log_msg(f"❌ Erro geral em def_presc: {e}")
        return False

def def_ajustegigs(driver, numero_processo, data_decisao, debug=False, dias_uteis=4):
    """
    Função para ajustar GIGS - modifica prazo para quantidade de dias úteis especificada.
    
    Fluxo:
    1. Clica no ícone de edição (fa-edit)
    2. Aguarda modal de cadastro de atividades abrir
    3. Preenche campo "Dias Úteis" com valor especificado
    4. Clica em "Salvar"
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        data_decisao: Data da decisão analisada
        debug: Se True, exibe logs detalhados
        dias_uteis: Número de dias úteis a ser configurado (padrão: 4)
    
    Returns:
        bool: True se executado com sucesso
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    def log_msg(msg):
        if debug:
            print(f"[DEF_AJUSTEGIGS] {msg}")
    
    log_msg(f"Iniciando ajuste de GIGS para processo {numero_processo}")
    log_msg(f"Data da decisão: {data_decisao}")
    log_msg(f"Ação: Ajustar prazo para {dias_uteis} dias úteis")
    
    try:
        # ===== ETAPA 1: CLICAR NO ÍCONE DE EDIÇÃO =====
        log_msg("1. Procurando ícone de edição (fa-edit)...")
        
        try:
            # Procura o ícone de edição na tabela
            icone_edicao = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.far.fa-edit.botao-icone-tabela'))
            )
            
            # Clica no ícone
            icone_edicao.click()
            log_msg("✅ Ícone de edição clicado")
            time.sleep(2)  # Aguarda modal abrir
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar no ícone de edição: {e}")
            return False
        
        # ===== ETAPA 2: AGUARDAR MODAL DE CADASTRO ABRIR =====
        log_msg("2. Aguardando modal de cadastro de atividades...")
        
        try:
            # Aguarda o modal aparecer
            modal_cadastro = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-dialog-container pje-gigs-cadastro-atividades'))
            )
            log_msg("✅ Modal de cadastro de atividades encontrado")
            
            # Aguarda formulário estar completamente carregado
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="dias"]'))
            )
            log_msg("✅ Formulário carregado completamente")
            time.sleep(1)  # Estabilização adicional
            
        except Exception as e:
            log_msg(f"❌ Erro ao aguardar modal: {e}")
            return False
        
        # ===== ETAPA 3: PREENCHER CAMPO "DIAS ÚTEIS" COM VALOR ESPECIFICADO =====
        log_msg(f"3. Preenchendo campo 'Dias Úteis' com valor {dias_uteis}...")
        
        try:
            # Procura o campo "Dias Úteis" usando o seletor do HTML fornecido
            campo_dias = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="dias"]'))
            )
            
            # Limpa o campo e insere o valor especificado
            campo_dias.clear()
            campo_dias.send_keys(str(dias_uteis))
            log_msg(f"✅ Campo 'Dias Úteis' preenchido com valor {dias_uteis}")
            
            # Verifica se o valor foi inserido corretamente
            valor_atual = campo_dias.get_attribute('value')
            if valor_atual == str(dias_uteis):
                log_msg(f"✅ Valor confirmado no campo: {dias_uteis}")
            else:
                log_msg(f"⚠️ Valor no campo difere do esperado: {valor_atual}")
            
            time.sleep(0.5)  # Aguarda processamento do valor
            
        except Exception as e:
            log_msg(f"❌ Erro ao preencher campo Dias Úteis: {e}")
            return False
        
        # ===== ETAPA 4: CLICAR EM "SALVAR" =====
        log_msg("4. Clicando em botão 'Salvar'...")
        
        try:
            # Usa a mesma lógica do criar_gigs de Fix.py para encontrar o botão Salvar
            btn_salvar = None
            botoes = driver.find_elements(By.CSS_SELECTOR, 'button.mat-raised-button')
            
            for btn in botoes:
                if btn.is_displayed() and ('Salvar' in btn.text or btn.get_attribute('type') == 'submit'):
                    btn_salvar = btn
                    log_msg(f"✅ Botão Salvar encontrado: texto='{btn.text}', type='{btn.get_attribute('type')}'")
                    break
            
            if not btn_salvar:
                log_msg("❌ Botão Salvar não encontrado!")
                return False
            
            # Clica no botão
            btn_salvar.click()
            log_msg("✅ Botão 'Salvar' clicado")
            
            # Aguarda mensagem de sucesso no snackbar (igual ao criar_gigs)
            try:
                success_snackbar = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'snack-bar-container.success simple-snack-bar span'))
                )
                if 'salva com sucesso' in success_snackbar.text.lower():
                    log_msg("✅ Mensagem de sucesso confirmada no snackbar")
                    time.sleep(1)  # Aguarda 1s após confirmação
                else:
                    log_msg("⚠️ Snackbar encontrado mas sem mensagem de sucesso")
            except Exception as e_snackbar:
                log_msg(f"⚠️ Não foi possível confirmar mensagem de sucesso: {e_snackbar}")
                # Aguarda o modal desaparecer como indicativo de sucesso
                try:
                    WebDriverWait(driver, 10).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, 'mat-dialog-container pje-gigs-cadastro-atividades'))
                    )
                    log_msg("✅ Modal fechado - operação salva com sucesso")
                except:
                    time.sleep(3)
                    log_msg("⚠️ Modal ainda visível, mas prosseguindo")
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar em Salvar: {e}")
            return False
        
        # ===== FINALIZAÇÃO =====
        time.sleep(2)  # Aguarda processamento final
        
        log_msg("✅ Ajuste de GIGS concluído com sucesso!")
        log_msg(f"Prazo ajustado para {dias_uteis} dias úteis")
        
        return True
        
    except Exception as e:
        log_msg(f"❌ Erro geral no ajuste de GIGS: {e}")
        
        # Em caso de erro, tenta fechar modal se estiver aberto
        try:
            botao_cancelar = driver.find_element(By.XPATH, "//button[contains(., 'Cancelar')]")
            if botao_cancelar.is_displayed():
                botao_cancelar.click()
                log_msg("⚠️ Modal cancelado devido ao erro")
        except:
            pass
        
        return False

def criar_lembrete(driver, titulo, conteudo, debug=False):
    """
    Cria lembrete no PJe (baseado em lembrete_bloq do m1.py).
    
    Args:
        driver: WebDriver do Selenium
        titulo: Título do lembrete
        conteudo: Conteúdo do lembrete
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    from Fix import safe_click, wait_for_visible, sleep
    
    try:
        if debug:
            print(f'[LEMBRETE] Criando lembrete: "{titulo}" - "{conteudo}"')
            
        # 1. Clique no menu (fa-bars)
        menu_clicked = safe_click(driver, '.fa-bars', log=debug)
        if not menu_clicked and debug:
            print('[LEMBRETE] Falha ao clicar no menu')
        sleep(1000)  # 1 segundo
        
        # 2. Clique no ícone de lembrete (fa thumbtack)
        lembrete_selector = '.lista-itens-menu > li:nth-child(16) > pje-icone-post-it:nth-child(1) > li:nth-child(1) > button:nth-child(1)'
        lembrete_clicked = safe_click(driver, lembrete_selector, log=debug)
        if not lembrete_clicked and debug:
            print('[LEMBRETE] Falha ao clicar no ícone de lembrete')
        sleep(1000)
        
        # 3. Foco no conteúdo do diálogo
        dialog_clicked = safe_click(driver, '.mat-dialog-content', log=debug)
        sleep(1000)
        
        # 4. Preenche título
        campo_titulo = wait_for_visible(driver, '#tituloPostit', timeout=5)
        if campo_titulo:
            campo_titulo.clear()
            campo_titulo.send_keys(titulo)
        else:
            print('[LEMBRETE] Campo de título não encontrado')
            return False
        
        # 5. Preenche conteúdo
        campo_conteudo = wait_for_visible(driver, '#conteudoPostit', timeout=5)
        if campo_conteudo:
            campo_conteudo.clear()
            campo_conteudo.send_keys(conteudo)
        else:
            print('[LEMBRETE] Campo de conteúdo não encontrado')
            return False
        
        # 6. Clica em salvar
        salvar_clicked = safe_click(driver, 'button.mat-raised-button:nth-child(1)', log=debug)
        if not salvar_clicked and debug:
            print('[LEMBRETE] Falha ao clicar no botão salvar')
            return False
        sleep(1000)
        
        if debug:
            print('[LEMBRETE] Lembrete criado com sucesso.')
            
        return True
            
    except Exception as e:
        if debug:
            print(f'[LEMBRETE][ERRO] Falha ao criar lembrete: {e}')
        return False

def saldo(driver, numero_processo, observacao, debug=False, timeout=10):
    """
    Função def_saldo: analisa timeline para identificar primeira ocorrência de Alvará/Alvará
    e executa ação baseada no responsável (Magistrado ou Servidor).
    
    Fluxo:
    1. Percorre timeline procurando primeira ocorrência de "Alvará" ou "Alvará"
    2. Ao identificar, lê o atributo aria-label do ícone responsável
    3. Se "Magistrado" -> def_SIF
    4. Se "Servidor" -> def_Siscon
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        observacao: Observação que disparou a ação
        debug: Se True, exibe logs detalhados
        timeout: Timeout para aguardar elementos
    
    Returns:
        bool: True se executado com sucesso
    """
    from selenium.webdriver.common.by import By
    import re
    import unicodedata
    
    # FORÇAR DEBUG SEMPRE ATIVO PARA MELHOR DEPURAÇÃO
    debug = True
    
    def log_msg(msg):
        print(f"[SALDO] {msg}")
    
    log_msg("=" * 60)
    log_msg("INICIANDO FUNÇÃO SALDO")
    log_msg("=" * 60)
    log_msg(f"Processo: {numero_processo}")
    log_msg(f"Observação: {observacao}")
    log_msg(f"Debug: {debug}")
    
    try:
        # ===== ETAPA 1: VERIFICAR SE ESTÁ NA ABA CORRETA =====
        log_msg("1. Verificando URL atual e contexto...")
        
        url_atual = driver.current_url
        log_msg(f"URL atual: {url_atual}")
        
        # Verifica se está na página de detalhes do processo
        if '/detalhe' not in url_atual:
            log_msg("❌ ERRO: Não está na página de detalhes do processo")
            log_msg("URL atual não contém '/detalhe'")
            return False
        
        # ===== ETAPA 2: PERCORRER TIMELINE PROCURANDO ALVARÁ =====
        log_msg("2. Percorrendo timeline procurando primeira ocorrência de Alvará...")
        
        # Procura itens da timeline (usando mesmo padrão do def_sob)
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            log_msg("❌ ERRO: Nenhum item encontrado na timeline")
            log_msg("Tentando seletores alternativos...")
            
            # Tenta outros seletores
            itens = driver.find_elements(By.CSS_SELECTOR, '.timeline-item')
            if not itens:
                itens = driver.find_elements(By.CSS_SELECTOR, '[class*="timeline"]')
            
            if not itens:
                log_msg("❌ ERRO CRÍTICO: Timeline não encontrada com nenhum seletor")
                return False
        
        log_msg(f"✅ Encontrados {len(itens)} itens na timeline")
        
        alvara_encontrado = None
        alvara_item = None
        documentos_analisados = []
        
        # Percorre timeline procurando Alvará/Alvará
        for idx, item in enumerate(itens):
            try:
                # Procura link do documento no item
                links = item.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                if not links:
                    # Fallback: procura qualquer link
                    links = item.find_elements(By.CSS_SELECTOR, 'a')
                
                if not links:
                    continue
                
                for link in links:
                    doc_text = link.text.lower().strip()
                    if not doc_text:
                        continue
                    
                    documentos_analisados.append(f"Item {idx + 1}: '{doc_text}'")
                    log_msg(f"Analisando documento {idx + 1}: '{doc_text}'")
                    
                    # Verifica se contém "alvará" ou "alvara" (normalizado)
                    doc_text_normalizado = unicodedata.normalize('NFD', doc_text)
                    doc_text_normalizado = ''.join(c for c in doc_text_normalizado if unicodedata.category(c) != 'Mn')
                    
                    # Busca por diferentes variações
                    if ('alvara' in doc_text_normalizado or 
                        'alvará' in doc_text or 
                        'alvarã' in doc_text or
                        'alvara' in doc_text_normalizado.replace(' ', '')):
                        
                        alvara_encontrado = link
                        alvara_item = item
                        log_msg(f"✅ ALVARÁ ENCONTRADO!")
                        log_msg(f"   Texto: '{link.text}'")
                        log_msg(f"   Posição: Item {idx + 1}")
                        break
                
                if alvara_encontrado:
                    break
                    
            except Exception as e:
                log_msg(f"⚠️ Erro ao processar item {idx + 1}: {e}")
                continue
        
        # Log de todos os documentos analisados
        log_msg("DOCUMENTOS ANALISADOS NA TIMELINE:")
        for doc in documentos_analisados:
            log_msg(f"  {doc}")
        
        if not alvara_encontrado or not alvara_item:
            log_msg("❌ ERRO: Nenhuma ocorrência de Alvará encontrada na timeline")
            log_msg(f"Total de documentos analisados: {len(documentos_analisados)}")
            return False
        
        # ===== ETAPA 3: LER ÍCONE RESPONSÁVEL DO ALVARÁ =====
        log_msg("3. Analisando responsável pelo Alvará...")
        
        try:
            # Múltiplas tentativas para encontrar o ícone responsável
            icone_responsavel = None
            aria_label = None
            
            # Tentativa 1: Seletor específico fornecido
            try:
                icone_responsavel = alvara_item.find_element(By.CSS_SELECTOR, 
                    'div[name="tipoItemTimeline"] .mat-tooltip-trigger.tl-icon')
                aria_label = icone_responsavel.get_attribute('aria-label')
                log_msg(f"✅ Tentativa 1 - Aria-label encontrado: '{aria_label}'")
            except Exception as e1:
                log_msg(f"⚠️ Tentativa 1 falhou: {e1}")
            
            # Tentativa 2: Busca mais ampla por ícones
            if not aria_label:
                try:
                    icones = alvara_item.find_elements(By.CSS_SELECTOR, '[aria-label]')
                    for icone in icones:
                        label = icone.get_attribute('aria-label')
                        if label and ('magistrado' in label.lower() or 'servidor' in label.lower()):
                            icone_responsavel = icone
                            aria_label = label
                            log_msg(f"✅ Tentativa 2 - Aria-label encontrado: '{aria_label}'")
                            break
                except Exception as e2:
                    log_msg(f"⚠️ Tentativa 2 falhou: {e2}")
            
            # Tentativa 3: Busca por classes de ícone
            if not aria_label:
                try:
                    icones = alvara_item.find_elements(By.CSS_SELECTOR, '.tl-icon, .fa, [class*="icon"]')
                    for icone in icones:
                        label = icone.get_attribute('aria-label')
                        title = icone.get_attribute('title')
                        tooltip = icone.get_attribute('mattooltip')
                        
                        for attr in [label, title, tooltip]:
                            if attr and ('magistrado' in attr.lower() or 'servidor' in attr.lower()):
                                icone_responsavel = icone
                                aria_label = attr
                                log_msg(f"✅ Tentativa 3 - Atributo encontrado: '{aria_label}'")
                                break
                        if aria_label:
                            break
                except Exception as e3:
                    log_msg(f"⚠️ Tentativa 3 falhou: {e3}")
            
            if not aria_label:
                log_msg("❌ ERRO: Aria-label do responsável não encontrado")
                log_msg("Tentando extrair HTML do item para análise...")
                
                try:
                    html_item = alvara_item.get_attribute('outerHTML')[:500]
                    log_msg(f"HTML do item (primeiros 500 chars): {html_item}")
                except:
                    pass
                
                return False
            
            aria_label_lower = aria_label.lower()
            log_msg(f"Responsável identificado: '{aria_label}' (normalizado: '{aria_label_lower}')")
            
            # ===== ETAPA 4: EXECUTAR AÇÃO BASEADA NO RESPONSÁVEL =====
            log_msg("4. Executando ação baseada no responsável...")
            
            if 'magistrado' in aria_label_lower:
                log_msg("✅ RESPONSÁVEL: MAGISTRADO")
                log_msg(">>> Executando def_SIF...")
                try:
                    resultado = def_SIF(driver, numero_processo, observacao, debug=True)
                    log_msg(f">>> def_SIF retornou: {resultado}")
                    if resultado:
                        log_msg("✅ def_SIF executado com SUCESSO")
                        return True
                    else:
                        log_msg("❌ def_SIF FALHOU")
                        return False
                except Exception as e:
                    log_msg(f"❌ EXCEÇÃO em def_SIF: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
                    
            elif 'servidor' in aria_label_lower:
                log_msg("✅ RESPONSÁVEL: SERVIDOR")
                log_msg(">>> Executando def_Siscon...")
                try:
                    resultado = def_Siscon(driver, numero_processo, observacao, debug=True)
                    log_msg(f">>> def_Siscon retornou: {resultado}")
                    if resultado:
                        log_msg("✅ def_Siscon executado com SUCESSO")
                        return True
                    else:
                        log_msg("❌ def_Siscon FALHOU")
                        return False
                except Exception as e:
                    log_msg(f"❌ EXCEÇÃO em def_Siscon: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                log_msg(f"❌ ERRO: Responsável não reconhecido: '{aria_label}'")
                log_msg("Esperado: termo que contenha 'Magistrado' ou 'Servidor'")
                return False
                
        except Exception as e:
            log_msg(f"❌ ERRO ao analisar responsável: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        log_msg(f"❌ ERRO GERAL na função saldo: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        log_msg("=" * 60)
        log_msg("FIM DA FUNÇÃO SALDO")
        log_msg("=" * 60)

def def_SIF(driver, numero_processo, observacao, debug=False):
    """
    Função def_SIF: Consulta saldo no sistema SIF e executa ação baseada no resultado.
    
    Fluxo:
    1. Clicar no menu do processo (fa-bars)
    2. Clicar em "Dados Financeiros" (fa-file-invoice-dollar)
    3. Aguardar carregamento da página SIF
    4. Ler saldo disponível da página SIF
    5. Se saldo > 0 → criar_gigs (1/Bruna/Liberação)
    6. Se saldo = 0 → ato_parcela
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        observacao: Observação original
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    import time
    import re
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    def log_msg(msg):
        if debug:
            print(f"[DEF_SIF] {msg}")
    
    log_msg(f"Executando def_SIF para processo {numero_processo}")
    log_msg(f"Observação: {observacao}")
    
    try:
        # Captura aba original
        aba_original = driver.current_window_handle
        log_msg(f"Aba original capturada: {aba_original}")
        
        # ===== ETAPA 1: CLICAR NO MENU DO PROCESSO =====
        log_msg("1. Clicando no menu do processo (fa-bars)...")
        
        try:
            # Procura o botão do menu usando o seletor fornecido
            botao_menu = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button#botao-menu[aria-label="Menu do processo"]'))
            )
            botao_menu.click()
            log_msg("✅ Menu do processo aberto")
            time.sleep(2)  # Aguarda menu abrir
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar no menu do processo: {e}")
            # Tenta seletor alternativo mais genérico
            try:
                log_msg("Tentando seletor alternativo para o menu...")
                botao_menu_alt = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[mat-icon-button] i.fa-bars'))
                )
                botao_menu_alt.click()
                log_msg("✅ Menu do processo aberto (seletor alternativo)")
                time.sleep(2)
            except Exception as e2:
                log_msg(f"❌ Erro também no seletor alternativo: {e2}")
                return False
        
        # ===== ETAPA 2: CLICAR EM "DADOS FINANCEIROS" =====
        log_msg("2. Clicando em 'Dados Financeiros'...")
        
        try:
            # Procura o botão "Dados Financeiros" usando o seletor fornecido
            botao_dados_financeiros = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Abre a tela com os dados financeiros"]'))
            )
            botao_dados_financeiros.click()
            log_msg("✅ Botão 'Dados Financeiros' clicado")
            time.sleep(3)  # Aguarda navegação
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar em 'Dados Financeiros': {e}")
            # Tenta seletor alternativo
            try:
                log_msg("Tentando seletor alternativo para 'Dados Financeiros'...")
                botao_alt = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'dados financeiros') or contains(., 'Dados Financeiros')]//i[contains(@class, 'fa-file-invoice-dollar')]"))
                )
                botao_alt.click()
                log_msg("✅ 'Dados Financeiros' clicado (seletor alternativo)")
                time.sleep(3)
            except Exception as e2:
                log_msg(f"❌ Erro também no seletor alternativo: {e2}")
                return False
        
        # ===== ETAPA 3: VERIFICAR SE CHEGOU NA PÁGINA SIF =====
        log_msg("3. Verificando se chegou na página de dados financeiros...")
        
        try:
            # Aguarda até que a URL contenha indicativos da página SIF
            WebDriverWait(driver, 20).until(
                lambda d: 'sif' in d.current_url.lower() or 'financeiro' in d.current_url.lower() or 'saldo' in d.current_url.lower()
            )
            
            url_atual = driver.current_url
            log_msg(f"✅ Página de dados financeiros carregada: {url_atual}")
            
            # Aguarda elementos da página carregarem
            time.sleep(5)
            
        except Exception as e:
            log_msg(f"⚠️ Timeout ao aguardar página SIF. URL atual: {driver.current_url}")
            # Continua mesmo assim, pode ser que tenha carregado
        
        # Verifica se há nova aba aberta (alguns sistemas abrem em nova aba)
        abas_abertas = driver.window_handles
        if len(abas_abertas) > 1:
            log_msg("Nova aba detectada, mudando para ela...")
            for aba in abas_abertas:
                if aba != aba_original:
                    driver.switch_to.window(aba)
                    url_nova_aba = driver.current_url
                    log_msg(f"URL da nova aba: {url_nova_aba}")
                    if 'sif' in url_nova_aba.lower() or 'financeiro' in url_nova_aba.lower():
                        log_msg("✅ Nova aba SIF confirmada")
                        break
            time.sleep(3)  # Aguarda nova aba carregar
        
        # ===== ETAPA 4: LER SALDO DISPONÍVEL =====
        log_msg("4. Lendo saldo disponível da página de dados financeiros...")
        
        # Aguarda página carregar completamente
        time.sleep(5)
        
        saldo_disponivel = 0.0
        tem_saldo = False
        
        try:
            # Procura pelos elementos de saldo na estrutura fornecida
            # Primeiro tenta o saldo total do processo (último card)
            log_msg("Procurando saldo total do processo...")
            
            # Seletor mais específico para o saldo total do processo
            saldos_processo = driver.find_elements(By.CSS_SELECTOR, 
                'mat-card.total-processo .grid-tile-valor h4.grid-tile-valor')
            
            if saldos_processo and len(saldos_processo) >= 2:
                # Primeiro h4 é saldo total, segundo é saldo disponível
                saldo_disponivel_elemento = saldos_processo[1]  # Saldo Disponível
                saldo_text = saldo_disponivel_elemento.text.strip()
                log_msg(f"Saldo disponível encontrado: {saldo_text}")
                
                # Extrai valor numérico (ex: "R$ 1.234,56" -> 1234.56)
                valor_match = re.search(r'R\$\s*([0-9.,]+)', saldo_text)
                if valor_match:
                    valor_str = valor_match.group(1)
                    # Converte formato brasileiro para float
                    valor_str = valor_str.replace('.', '').replace(',', '.')
                    saldo_disponivel = float(valor_str)
                    log_msg(f"Saldo disponível convertido: {saldo_disponivel}")
            
            # Se não encontrou no processo, tenta na instituição financeira
            if saldo_disponivel == 0:
                log_msg("Procurando saldo na instituição financeira...")
                
                saldos_instituicao = driver.find_elements(By.CSS_SELECTOR, 
                    'pje-listar-saldo mat-card-footer .grid-tile-valor h4.grid-tile-valor')
                
                if saldos_instituicao and len(saldos_instituicao) >= 2:
                    saldo_disponivel_elemento = saldos_instituicao[1]  # Segundo é disponível
                    saldo_text = saldo_disponivel_elemento.text.strip()
                    log_msg(f"Saldo disponível (instituição): {saldo_text}")
                    
                    valor_match = re.search(r'R\$\s*([0-9.,]+)', saldo_text)
                    if valor_match:
                        valor_str = valor_match.group(1)
                        valor_str = valor_str.replace('.', '').replace(',', '.')
                        saldo_disponivel = float(valor_str)
                        log_msg(f"Saldo disponível convertido: {saldo_disponivel}")
            
            # Determina se tem saldo
            tem_saldo = saldo_disponivel > 0
            log_msg(f"Saldo disponível: R$ {saldo_disponivel:.2f}")
            log_msg(f"Tem saldo: {'SIM' if tem_saldo else 'NÃO'}")
            
        except Exception as e:
            log_msg(f"❌ Erro ao ler saldo: {e}")
            log_msg("Assumindo saldo = 0")
            saldo_disponivel = 0.0
            tem_saldo = False
        
        # ===== ETAPA 5: RETORNAR PARA PÁGINA DO PROCESSO =====
        log_msg("5. Retornando para página do processo...")
        
        try:
            # Verifica se há múltiplas abas e fecha a do SIF se necessário
            abas_abertas = driver.window_handles
            if len(abas_abertas) > 1:
                # Se estiver em nova aba, fecha ela e volta para a original
                driver.close()  # Fecha aba atual
                driver.switch_to.window(aba_original)
                log_msg("✅ Aba SIF fechada, retornado para aba original")
            else:
                # Se está na mesma aba, navega de volta para o processo
                driver.back()  # Volta uma página
                log_msg("✅ Navegado de volta para página do processo")
            
            time.sleep(2)  # Aguarda carregar
            
        except Exception as e:
            log_msg(f"⚠️ Erro ao retornar para página do processo: {e}")
            # Força retorno para aba original
            try:
                driver.switch_to.window(aba_original)
            except:
                pass
        
        # ===== ETAPA 6 e 7: EXECUTAR AÇÃO BASEADA NO SALDO =====
        if tem_saldo:
            log_msg("6. SALDO > 0 → Executando criar_gigs (1/Bruna/Liberação)")
            try:
                from Fix import criar_gigs
                
                # Parâmetros: número_processo, origem, destinatario, assunto
                resultado = criar_gigs(driver, numero_processo, "1", "Bruna", "Liberação", debug=debug)
                
                if resultado:
                    log_msg("✅ criar_gigs executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do criar_gigs")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro ao executar criar_gigs: {e}")
                return False
        else:
            log_msg("7. SALDO = 0 → Executando ato_parcela")
            try:
                from atos import ato_parcela
                
                resultado = ato_parcela(driver, debug=debug)
                
                if resultado:
                    log_msg("✅ ato_parcela executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do ato_parcela")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro ao executar ato_parcela: {e}")
                return False
        
    except Exception as e:
        log_msg(f"❌ Erro geral em def_SIF: {e}")
        import traceback
        traceback.print_exc()
        
        # Tenta voltar para aba original em caso de erro
        try:
            driver.switch_to.window(aba_original)
        except:
            pass
            
        return False

def def_Siscon(driver, numero_processo, observacao, debug=False, extrair_dados_completos=False):
    """
    Função def_Siscon: Consulta saldo no sistema Alvará Eletrônico e executa ação baseada no resultado.
    
    NOVO COMPORTAMENTO: Na primeira execução, pausa e pede login manual do usuário.
    
    Fluxo:
    0. Verificar se precisa fazer login manual (primeira execução)
    1. Clicar no ícone de cópia para obter número do processo  
    2. Navegar para busca do Alvará Eletrônico (mesma aba)
    3. Inserir número do processo no campo específico
    4. Clicar no botão de buscar
    5. Aguardar carregamento da página
    6. Ler coluna "Valor Disponível" da tabela de contas
    7. (OPCIONAL) Se extrair_dados_completos=True → Executar extração detalhada
    8. Voltar para página original
    9. Se saldo > 0 → criar_gigs (1/Bruna/Liberação)
    10. Se saldo = 0 → ato_parcela
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        observacao: Observação original
        debug: Se True, exibe logs detalhados
        extrair_dados_completos: Se True, executa também extrair_dados_siscon()
    
    Returns:
        bool: True se executado com sucesso
    """
    import time
    import re
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    def log_msg(msg):
        if debug:
            print(f"[DEF_SISCON] {msg}")
    
    log_msg(f"Executando def_Siscon para processo {numero_processo}")
    log_msg(f"Observação: {observacao}")
    
    try:
        # Captura URL original para voltar depois
        url_original = driver.current_url
        log_msg(f"URL original capturada: {url_original}")
        
        # ===== ETAPA 0: VERIFICAR SE PRECISA FAZER LOGIN MANUAL =====
        log_msg("0. Verificando necessidade de login manual...")
        
        if not fazer_login_siscon_manual(driver, debug):
            log_msg("❌ Login manual falhou - abortando def_Siscon")
            return False
        
        # ===== ETAPA 1: CLICAR NO ÍCONE DE CÓPIA PARA OBTER NÚMERO DO PROCESSO =====
        log_msg("1. Voltando para página original e clicando no ícone de cópia...")
        
        # Voltar para página original
        driver.get(url_original)
        time.sleep(2)
        
        try:
            # Procura o ícone de cópia
            icone_copia = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.far.fa-copy.fa-lg'))
            )
            icone_copia.click()
            log_msg("✅ Ícone de cópia clicado")
            time.sleep(1)  # Aguarda copiar
            
            # Tenta obter número da clipboard se possível, senão usa o parâmetro
            numero_para_siscon = numero_processo
            log_msg(f"Número do processo para Siscon: {numero_para_siscon}")
            
        except Exception as e:
            log_msg(f"⚠️ Erro ao clicar no ícone de cópia: {e}")
            log_msg("Usando número do processo do parâmetro")
            numero_para_siscon = numero_processo
        
        # ===== ETAPA 2: NAVEGAR PARA BUSCA DO ALVARÁ ELETRÔNICO =====
        log_msg("2. Navegando para busca do Alvará Eletrônico...")
        
        url_alvara = "https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar"
        log_msg(f"URL Alvará Eletrônico: {url_alvara}")
        
        driver.get(url_alvara)
        time.sleep(5)  # Aguarda carregar
        
        # ===== ETAPA 3: VERIFICAR SE ESTÁ NA PÁGINA CORRETA =====
        url_atual = driver.current_url
        log_msg(f"URL atual após navegação: {url_atual}")
        
        if 'login.jsp' in url_atual:
            log_msg("❌ Redirecionado para login - sessão expirou")
            print("\n⚠️ SESSÃO EXPIROU - faça login novamente")
            global _siscon_login_feito
            _siscon_login_feito = False  # Reset flag para forçar novo login
            return def_Siscon(driver, numero_processo, observacao, debug, extrair_dados_completos)
        
        if 'buscar' not in url_atual:
            log_msg(f"❌ URL inesperada: {url_atual}")
            return False
            time.sleep(1)  # Aguarda copiar
            
        
        # ===== ETAPA 3: INSERIR NÚMERO DO PROCESSO =====
        log_msg("3. Inserindo número do processo no campo de busca...")
        
        try:
            # Procura o campo de número do processo
            campo_processo = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'numeroProcesso'))
            )
            
            # Limpa campo e insere número
            campo_processo.clear()
            campo_processo.send_keys(numero_para_siscon)
            log_msg(f"✅ Número do processo inserido: {numero_para_siscon}")
            time.sleep(1)
            
        except Exception as e:
            log_msg(f"❌ Erro ao inserir número do processo: {e}")
            # Voltar para URL original antes de retornar erro
            try:
                driver.get(url_original)
                time.sleep(2)
            except:
                pass
            return False
        
        # ===== ETAPA 4: CLICAR NO BOTÃO DE BUSCAR =====
        log_msg("4. Clicando no botão de buscar...")
        
        try:
            # Procura o botão de buscar
            botao_buscar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'bt_buscar'))
            )
            
            botao_buscar.click()
            log_msg("✅ Botão de buscar clicado")
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar no botão de buscar: {e}")
            # Voltar para URL original antes de retornar erro
            try:
                driver.get(url_original)
                time.sleep(2)
            except:
                pass
            return False
        
        # ===== ETAPA 5: AGUARDAR CARREGAMENTO DA PÁGINA =====
        log_msg("5. Aguardando carregamento da página de resultados...")
        
        try:
            # Aguarda o elemento de dados pesquisados aparecer
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, 'dados_pesquisados'))
            )
            log_msg("✅ Página de resultados carregada")
            time.sleep(2)  # Aguarda adicional para garantir carregamento completo
            
        except Exception as e:
            log_msg(f"❌ Timeout aguardando carregamento dos resultados: {e}")
            # Voltar para URL original antes de retornar erro
            try:
                driver.get(url_original)
                time.sleep(2)
            except:
                pass
            return False
        
        # ===== ETAPA 6: LER COLUNA "VALOR DISPONÍVEL" =====
        
        saldo_total_disponivel = 0.0
        tem_saldo = False
        
        try:
            # Procura a tabela de contas judiciais
            tabela_contas = driver.find_element(By.ID, 'table_contas')
            log_msg("✅ Tabela de contas encontrada")
            
            # Procura todas as linhas de conta (tr com id que começa com "linhaConta_")
            linhas_conta = driver.find_elements(By.CSS_SELECTOR, 'tr[id^="linhaConta_"]')
            log_msg(f"✅ Encontradas {len(linhas_conta)} contas judiciais")
            
            if not linhas_conta:
                log_msg("⚠️ Nenhuma conta judicial encontrada")
                saldo_total_disponivel = 0.0
            else:
                # Para cada linha de conta, extrai o valor disponível
                for idx, linha in enumerate(linhas_conta):
                    try:
                        # O "Valor Disponível" está na 6ª coluna (index 5)
                        # Procura a célula com id que termina com "saldo_corrigido_conta_"
                        celula_disponivel = linha.find_element(By.CSS_SELECTOR, 'td[id*="saldo_corrigido_conta_"]')
                        
                        valor_text = celula_disponivel.text.strip()
                        log_msg(f"Conta {idx + 1} - Valor disponível: {valor_text}")
                        
                        # Extrai valor numérico (ex: "R$ 2.572,86" -> 2572.86)
                        valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_text)
                        if valor_match:
                            valor_str = valor_match.group(1)
                            # Converte formato brasileiro para float
                            valor_str = valor_str.replace('.', '').replace(',', '.')
                            valor_disponivel = float(valor_str)
                            saldo_total_disponivel += valor_disponivel
                            log_msg(f"Conta {idx + 1} - Valor convertido: {valor_disponivel}")
                        
                    except Exception as e:
                        log_msg(f"⚠️ Erro ao processar conta {idx + 1}: {e}")
                        continue
            
            # Determina se tem saldo
            tem_saldo = saldo_total_disponivel > 0
            log_msg(f"✅ Saldo total disponível: R$ {saldo_total_disponivel:.2f}")
            log_msg(f"Tem saldo: {'SIM' if tem_saldo else 'NÃO'}")
            
        except Exception as e:
            log_msg(f"❌ Erro ao ler valores disponíveis: {e}")
            log_msg("Assumindo saldo = 0")
            saldo_total_disponivel = 0.0
            tem_saldo = False
        
        # ===== ETAPA 7: VOLTAR PARA PÁGINA ORIGINAL =====
        log_msg("7. Voltando para página original...")
        
        try:
            driver.get(url_original)
            time.sleep(2)
            log_msg("✅ Retornado para página original")
        except Exception as e:
            log_msg(f"⚠️ Erro ao voltar para página original: {e}")
        
        # ===== ETAPA 7.5: EXTRAÇÃO COMPLETA DE DADOS (OPCIONAL) =====
        if extrair_dados_completos:
            log_msg("7.5. Executando extração completa de dados SISCON...")
            try:
                dados_extraidos = extrair_dados_siscon(driver, numero_para_siscon, debug=debug)
                if dados_extraidos:
                    log_msg("✅ Extração completa de dados executada com sucesso")
                    log_msg(f"Dados extraídos: {len(dados_extraidos.get('contas', []))} contas com saldo")
                else:
                    log_msg("⚠️ Extração completa não retornou dados")
            except Exception as e:
                log_msg(f"⚠️ Erro na extração completa: {e}")
                # Continua o fluxo normal mesmo se a extração falhar
        
        # ===== ETAPA 8 e 9: EXECUTAR AÇÃO BASEADA NO SALDO =====
        if saldo_total_disponivel > 0:
            log_msg("8. SALDO > 0 → Executando criar_gigs (1/Bruna/Liberação)")
            try:
                from Fix import criar_gigs
                
                # Parâmetros: número_processo, origem, destinatario, assunto
                resultado = criar_gigs(driver, numero_para_siscon, "1", "Bruna", "Liberação", debug=debug)
                
                if resultado:
                    log_msg("✅ criar_gigs executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do criar_gigs")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro ao executar criar_gigs: {e}")
                return False
        else:
            log_msg("9. SALDO = 0 → Executando ato_parcela")
            try:
                from atos import ato_parcela
                
                resultado = ato_parcela(driver, debug=debug)
                
                if resultado:
                    log_msg("✅ ato_parcela executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do ato_parcela")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro ao executar ato_parcela: {e}")
                return False
        
    except Exception as e:
        log_msg(f"❌ Erro geral em def_Siscon: {e}")
        
        # Tenta voltar para URL original em caso de erro
        try:
            driver.get(url_original)
            time.sleep(2)
        except:
            pass
            
        return False

def def_Siscon_sob(driver, numero_processo, observacao, debug=False):
    """
    Função def_Siscon específica para def_sob: Consulta saldo no Alvará Eletrônico 
    com regra específica para saldo = 0 (ajustegigs 20 dias).
    
    SIMPLIFICADO: Reutiliza toda a lógica da def_Siscon normal, só muda a ação final.
    
    Diferenças da def_Siscon normal:
    - Quando saldo = 0: executa def_ajustegigs com 20 dias (ao invés de ato_parcela)
    - Mantém: saldo > 0 → criar_gigs (1/Bruna/Liberação)
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        observacao: Observação original
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    def log_msg(msg):
        if debug:
            print(f"[DEF_SISCON_SOB] {msg}")
    
    log_msg(f"Executando def_Siscon_sob para processo {numero_processo}")
    log_msg("REGRA ESPECÍFICA: saldo = 0 → def_ajustegigs 20 dias")
    
    # ===== REUTILIZAR TODA A LÓGICA DA def_Siscon =====
    # Mas interceptar o resultado para aplicar regra específica
    
    try:
        # Captura URL original
        url_original = driver.current_url
        
        # Verificar login manual
        if not fazer_login_siscon_manual(driver, debug):
            log_msg("❌ Login manual falhou - abortando def_Siscon_sob")
            return False
        
        # Voltar para página original e clicar cópia
        driver.get(url_original)
        time.sleep(2)
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import re
            
            # Clicar no ícone de cópia
            icone_copia = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.far.fa-copy.fa-lg'))
            )
            icone_copia.click()
            numero_para_siscon = numero_processo
            
        except Exception as e:
            log_msg(f"⚠️ Erro ao clicar no ícone de cópia: {e}")
            numero_para_siscon = numero_processo
        
        # Navegar para Alvará
        url_alvara = "https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar"
        driver.get(url_alvara)
        time.sleep(5)
        
        # Verificar se precisa fazer login novamente
        if 'login.jsp' in driver.current_url:
            log_msg("❌ Sessão expirou - fazendo novo login")
            global _siscon_login_feito
            _siscon_login_feito = False
            return def_Siscon_sob(driver, numero_processo, observacao, debug)
        
        # Inserir número do processo
        campo_processo = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'numeroProcesso'))
        )
        campo_processo.clear()
        campo_processo.send_keys(numero_para_siscon)
        time.sleep(1)
        
        # Buscar
        botao_buscar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'bt_buscar'))
        )
        botao_buscar.click()
        
        # Aguardar resultados
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'dados_pesquisados'))
        )
        time.sleep(2)
        
        # Ler saldo
        saldo_total = 0.0
        try:
            linhas_conta = driver.find_elements(By.CSS_SELECTOR, 'tr[id^="linhaConta_"]')
            for linha in linhas_conta:
                try:
                    celula_disponivel = linha.find_element(By.CSS_SELECTOR, 'td[id*="saldo_corrigido_conta_"]')
                    valor_text = celula_disponivel.text.strip()
                    
                    valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_text)
                    if valor_match:
                        valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
                        saldo_total += float(valor_str)
                except:
                    continue
            
            log_msg(f"✅ Saldo total: R$ {saldo_total:.2f}")
            
        except Exception as e:
            log_msg(f"❌ Erro ao ler saldo: {e}")
            saldo_total = 0.0
        
        # Voltar para página original
        driver.get(url_original)
        time.sleep(2)
        
        # ===== APLICAR REGRA ESPECÍFICA =====
        if saldo_total > 0:
            log_msg("SALDO > 0 → Executando criar_gigs (1/Bruna/Liberação)")
            try:
                from Fix import criar_gigs
                resultado = criar_gigs(driver, numero_para_siscon, "1", "Bruna", "Liberação", debug=debug)
                return resultado
            except Exception as e:
                log_msg(f"❌ Erro em criar_gigs: {e}")
                return False
        else:
            log_msg("SALDO = 0 → Executando def_ajustegigs com 20 dias (REGRA ESPECÍFICA SOB)")
            try:
                resultado = def_ajustegigs(driver, dias_uteis=20, debug=debug)
                return resultado
            except Exception as e:
                log_msg(f"❌ Erro em def_ajustegigs: {e}")
                return False
        
    except Exception as e:
        log_msg(f"❌ Erro geral em def_Siscon_sob: {e}")
        try:
            driver.get(url_original)
        except:
            pass
        return False
        log_msg("✅ Driver Firefox básico criado com sucesso")
        
        # Extrai e aplica cookies da sessão ativa
        log_msg("0.1. Extraindo cookies da sessão Firefox ativa...")
        cookies = extrair_cookies_firefox_alvara()
        
        if cookies:
            log_msg(f"✅ {len(cookies)} cookies extraídos da sessão ativa")
            sucesso_cookies = aplicar_cookies_no_driver(driver_alvara, cookies)
            if sucesso_cookies:
                log_msg("✅ Cookies aplicados com sucesso - Sessão reutilizada!")
            else:
                log_msg("⚠️ Falha ao aplicar cookies - Tentando sem cookies")
        else:
            log_msg("⚠️ Nenhum cookie extraído - Tentando sem cookies")
        
    except Exception as e:
        log_msg(f"❌ Erro ao criar driver Firefox específico: {e}")
        return False
    
    try:
        # ===== ETAPA 1: OBTER NÚMERO DO PROCESSO =====
        log_msg("1. Obtendo número do processo...")
        numero_para_siscon = numero_processo
        log_msg(f"Número do processo para SISCON: {numero_para_siscon}")
        
        # ===== ETAPA 2: NAVEGAR DIRETAMENTE PARA ALVARÁ ELETRÔNICO =====
        log_msg("2. Navegando diretamente para Alvará Eletrônico...")
        
        url_alvara = "https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar"
        log_msg(f"URL Alvará Eletrônico: {url_alvara}")
        
        # Navega diretamente (sem nova aba, pois é driver independente)
        driver_alvara.get(url_alvara)
        time.sleep(5)  # Aguarda carregar completamente
        log_msg("✅ Página Alvará Eletrônico carregada")
        
        # ===== ETAPA 3: INSERIR NÚMERO DO PROCESSO =====
        log_msg("3. Inserindo número do processo no campo de busca...")
        
        # Aguarda página carregar completamente
        time.sleep(3)
        
        try:
            # Procura o campo de número do processo
            campo_processo = WebDriverWait(driver_alvara, 10).until(
                EC.presence_of_element_located((By.ID, 'numeroProcesso'))
            )
            
            # Limpa campo e insere número
            campo_processo.clear()
            campo_processo.send_keys(numero_para_siscon)
            log_msg(f"✅ Número do processo inserido: {numero_para_siscon}")
            time.sleep(1)
            
        except Exception as e:
            log_msg(f"❌ Erro ao inserir número do processo: {e}")
            return False
        
        # ===== ETAPA 4: CLICAR NO BOTÃO DE BUSCAR =====
        log_msg("4. Clicando no botão de buscar...")
        
        try:
            # Procura o botão de buscar
            botao_buscar = WebDriverWait(driver_alvara, 10).until(
                EC.element_to_be_clickable((By.ID, 'bt_buscar'))
            )
            
            botao_buscar.click()
            log_msg("✅ Botão de buscar clicado")
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar no botão de buscar: {e}")
            return False
        
        # ===== ETAPA 5: AGUARDAR CARREGAMENTO DA PÁGINA =====
        log_msg("5. Aguardando carregamento da página de resultados...")
        
        try:
            # Aguarda o elemento de dados pesquisados aparecer
            WebDriverWait(driver_alvara, 15).until(
                EC.presence_of_element_located((By.ID, 'dados_pesquisados'))
            )
            log_msg("✅ Página de resultados carregada")
            time.sleep(2)  # Aguarda adicional para garantir carregamento completo
            
        except Exception as e:
            log_msg(f"❌ Timeout aguardando carregamento dos resultados: {e}")
            return False
        
        # ===== ETAPA 6: LER COLUNA "VALOR DISPONÍVEL" =====
        log_msg("6. Lendo valores disponíveis das contas judiciais...")
        
        saldo_total_disponivel = 0.0
        tem_saldo = False
        
        try:
            # Procura a tabela de contas judiciais
            tabela_contas = driver.find_element(By.ID, 'table_contas')
            log_msg("✅ Tabela de contas encontrada")
            
            # Procura todas as linhas de conta (tr com id que começa com "linhaConta_")
            linhas_conta = driver.find_elements(By.CSS_SELECTOR, 'tr[id^="linhaConta_"]')
            log_msg(f"✅ Encontradas {len(linhas_conta)} contas judiciais")
            
            if not linhas_conta:
                log_msg("⚠️ Nenhuma conta judicial encontrada")
                saldo_total_disponivel = 0.0
            else:
                # Para cada linha de conta, extrai o valor disponível
                for idx, linha in enumerate(linhas_conta):
                    try:
                        # O "Valor Disponível" está na 6ª coluna (index 5)
                        # Procura a célula com id que termina com "saldo_corrigido_conta_"
                        celula_disponivel = linha.find_element(By.CSS_SELECTOR, 'td[id*="saldo_corrigido_conta_"]')
                        
                        valor_text = celula_disponivel.text.strip()
                        log_msg(f"Conta {idx + 1} - Valor disponível: {valor_text}")
                        
                        # Extrai valor numérico (ex: "R$ 2.572,86" -> 2572.86)
                        valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_text)
                        if valor_match:
                            valor_str = valor_match.group(1)
                            # Converte formato brasileiro para float
                            valor_str = valor_str.replace('.', '').replace(',', '.')
                            valor_disponivel = float(valor_str)
                            saldo_total_disponivel += valor_disponivel
                            log_msg(f"Conta {idx + 1} - Valor convertido: {valor_disponivel}")
                        
                    except Exception as e:
                        log_msg(f"⚠️ Erro ao processar conta {idx + 1}: {e}")
                        continue
            
            # Determina se tem saldo
            tem_saldo = saldo_total_disponivel > 0
            log_msg(f"✅ Saldo total disponível: R$ {saldo_total_disponivel:.2f}")
            log_msg(f"Tem saldo: {'SIM' if tem_saldo else 'NÃO'}")
            
        except Exception as e:
            log_msg(f"❌ Erro ao ler valores disponíveis: {e}")
            log_msg("Assumindo saldo = 0")
            saldo_total_disponivel = 0.0
            tem_saldo = False
        
        # ===== ETAPA 7: FECHAR ABA ALVARÁ ELETRÔNICO =====
        log_msg("7. Fechando aba Alvará Eletrônico...")
        
        try:
            driver.close()  # Fecha aba atual (Alvará Eletrônico)
            driver.switch_to.window(aba_original)  # Volta para aba original
            log_msg("✅ Aba Alvará Eletrônico fechada, retornado para aba original")
            time.sleep(1)
        except Exception as e:
            log_msg(f"⚠️ Erro ao fechar aba Alvará Eletrônico: {e}")
            # Força retorno para aba original
            try:
                driver.switch_to.window(aba_original)
            except:
                pass
        
        # ===== ETAPA 8 e 9: EXECUTAR AÇÃO BASEADA NO SALDO (REGRA ESPECÍFICA) =====
        if saldo_total_disponivel > 0:
            log_msg("8. SALDO > 0 → Executando criar_gigs (1/Bruna/Liberação)")
            try:
                from Fix import criar_gigs
                
                # Parâmetros: número_processo, origem, destinatario, assunto
                resultado = criar_gigs(driver, numero_para_siscon, "1", "Bruna", "Liberação", debug=debug)
                
                if resultado:
                    log_msg("✅ criar_gigs executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do criar_gigs")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro ao executar criar_gigs: {e}")
                return False
        else:
            # REGRA ESPECÍFICA: saldo = 0 → def_ajustegigs com 20 dias
            log_msg("9. SALDO = 0 → Executando def_ajustegigs com 20 dias (REGRA ESPECÍFICA def_sob)")
            try:
                resultado = def_ajustegigs(driver, numero_processo, None, debug=debug, dias_uteis=20)
                
                if resultado:
                    log_msg("✅ def_ajustegigs (20 dias) executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do def_ajustegigs")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro ao executar def_ajustegigs: {e}")
                return False
        
    except Exception as e:
        log_msg(f"❌ Erro geral em def_Siscon_sob: {e}")
        
        # Tenta fechar driver específico em caso de erro
        try:
            if 'driver_alvara' in locals():
                driver_alvara.quit()
                log_msg("⚠️ Driver Firefox específico fechado após erro")
        except:
            pass
            
        return False


def extrair_dados_siscon(driver, numero_processo, debug=False):
    """
    Função para extrair dados completos do SISCON (Sistema de Controle de Contas Judiciais).
    
    Baseado no HTML fornecido, esta função:
    1. Extrai o número do processo da página
    2. Localiza contas judiciais com valor disponível
    3. Para cada conta com saldo > 0:
       a) Clica no ícone de expansão (soma-ico.png) para mostrar parcelas
       b) Registra: número da conta judicial, total disponível
       c) Para cada linha de depósito com valor disponível: data, depositante e valor
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo para buscar
        debug: Se True, exibe logs detalhados
    
    Returns:
        dict: Dados extraídos estruturados ou None se houver erro
        {
            'numero_processo': str,
            'contas': [
                {
                    'numero_conta': str,
                    'total_disponivel': float,
                    'depositos': [
                        {
                            'data': str,
                            'depositante': str,
                            'valor_disponivel': float
                        }
                    ]
                }
            ]
        }
    """
    import time
    import re
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    
    def log_msg(msg):
        if debug:
            print(f"[EXTRAIR_SISCON] {msg}")
    
    log_msg(f"Iniciando extração de dados SISCON para processo {numero_processo}")
    
    try:
        # Captura aba original
        aba_original = driver.current_window_handle
        log_msg(f"Aba original capturada: {aba_original}")
        
        # ===== ETAPA 1: ABRIR URL DO SISCON EM NOVA ABA =====
        log_msg("1. Abrindo URL do SISCON em nova aba...")
        
        url_siscon = "https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/new"
        log_msg(f"URL SISCON: {url_siscon}")
        
        # Abre nova aba
        driver.execute_script(f"window.open('{url_siscon}', '_blank');")
        time.sleep(3)
        
        # ===== ETAPA 2: MUDAR PARA ABA NOVA =====
        log_msg("2. Mudando para aba SISCON...")
        
        abas_abertas = driver.window_handles
        aba_siscon = None
        
        for aba in abas_abertas:
            if aba != aba_original:
                driver.switch_to.window(aba)
                url_atual = driver.current_url
                log_msg(f"Verificando aba: {url_atual}")
                
                if 'alvaraeletronico.trt2.jus.br' in url_atual:
                    aba_siscon = aba
                    log_msg(f"✅ Aba SISCON confirmada: {url_atual}")
                    break
        
        if not aba_siscon:
            log_msg("❌ Aba SISCON não encontrada")
            return None
        
        # ===== ETAPA 3: PREENCHER E BUSCAR PROCESSO =====
        log_msg("3. Preenchendo número do processo e buscando...")
        
        # Aguarda página carregar
        time.sleep(3)
        
        try:
            # Preenche número do processo
            campo_processo = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'numeroProcesso'))
            )
            campo_processo.clear()
            campo_processo.send_keys(numero_processo)
            log_msg(f"✅ Número inserido: {numero_processo}")
            
            # Clica no botão buscar
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
            
        except Exception as e:
            log_msg(f"❌ Erro na busca: {e}")
            return None
        
        # ===== ETAPA 4: EXTRAIR NÚMERO DO PROCESSO DA PÁGINA =====
        log_msg("4. Extraindo número do processo da página...")
        
        numero_extraido = None
        try:
            # Busca o campo que contém o número do processo
            campo_numero = driver.find_element(By.ID, 'numeroProcesso')
            numero_extraido = campo_numero.get_attribute('value')
            log_msg(f"✅ Número extraído: {numero_extraido}")
        except:
            numero_extraido = numero_processo
            log_msg(f"⚠️ Usando número do parâmetro: {numero_extraido}")
        
        # ===== ETAPA 5: PROCESSAR CONTAS JUDICIAIS =====
        log_msg("5. Processando contas judiciais...")
        
        dados_extraidos = {
            'numero_processo': numero_extraido,
            'contas': []
        }
        
        try:
            # Procura a tabela de contas
            tabela_contas = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'table_contas'))
            )
            log_msg("✅ Tabela de contas encontrada")
            
            # Procura linhas de conta com valor disponível > 0
            linhas_conta = driver.find_elements(By.CSS_SELECTOR, 'tr[id^="linhaConta_"]')
            log_msg(f"✅ Encontradas {len(linhas_conta)} linhas de conta")
            
            for idx, linha in enumerate(linhas_conta):
                log_msg(f"Processando conta {idx + 1}...")
                
                try:
                    # Extrai número da conta judicial
                    celula_conta = linha.find_element(By.CSS_SELECTOR, 'td:nth-child(2)')  # 2ª coluna
                    numero_conta = celula_conta.text.strip()
                    
                    # Extrai valor disponível total
                    celula_disponivel = linha.find_element(By.CSS_SELECTOR, 'td[id*="saldo_corrigido_conta_"]')
                    valor_disponivel_texto = celula_disponivel.text.strip()
                    
                    # Converte valor para float
                    valor_match = re.search(r'R\$\s*([0-9.,]+)', valor_disponivel_texto)
                    if valor_match:
                        valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
                        total_disponivel = float(valor_str)
                    else:
                        total_disponivel = 0.0
                    
                    log_msg(f"Conta: {numero_conta}, Total: R$ {total_disponivel:.2f}")
                    
                    # Só processa contas com saldo > 0
                    if total_disponivel > 0:
                        log_msg(f"✅ Conta {numero_conta} tem saldo disponível")
                        
                        conta_dados = {
                            'numero_conta': numero_conta,
                            'total_disponivel': total_disponivel,
                            'depositos': []
                        }
                        
                        # ===== ETAPA 6: EXPANDIR PARCELAS =====
                        log_msg(f"6. Expandindo parcelas da conta {numero_conta}...")
                        
                        try:
                            # Procura o ícone de expansão (soma-ico.png)
                            icone_expansao = linha.find_element(By.CSS_SELECTOR, 'img[src*="soma-ico.png"]')
                            
                            # Clica no ícone para expandir
                            ActionChains(driver).move_to_element(icone_expansao).click().perform()
                            log_msg("✅ Ícone de expansão clicado")
                            time.sleep(2)  # Aguarda expansão
                            
                            # ===== ETAPA 7: EXTRAIR DADOS DOS DEPÓSITOS =====
                            log_msg("7. Extraindo dados dos depósitos...")
                            
                            # Procura as linhas de depósito expandidas
                            # Normalmente ficam logo após a linha principal da conta
                            try:
                                # Busca próximas linhas que contenham dados de depósito
                                # Elas geralmente têm um padrão específico de ID ou classe
                                linhas_deposito = driver.find_elements(By.CSS_SELECTOR, f'tr[id*="parcela_{idx}"], tr.linha-parcela, tr[style*="display: table-row"]')
                                
                                for linha_dep in linhas_deposito:
                                    try:
                                        # Verifica se a linha está visível e contém dados de depósito
                                        if not linha_dep.is_displayed():
                                            continue
                                        
                                        colunas = linha_dep.find_elements(By.TAG_NAME, 'td')
                                        if len(colunas) < 5:  # Precisa ter pelo menos 5 colunas
                                            continue
                                        
                                        # Extrai dados das colunas (ajustar conforme layout real)
                                        data_deposito = colunas[0].text.strip()  # 1ª coluna: Data
                                        depositante = colunas[1].text.strip()    # 2ª coluna: Depositante
                                        
                                        # Valor disponível geralmente na última coluna
                                        valor_dep_texto = colunas[-1].text.strip()
                                        
                                        # Converte valor
                                        valor_dep_match = re.search(r'R\$\s*([0-9.,]+)', valor_dep_texto)
                                        if valor_dep_match:
                                            valor_dep_str = valor_dep_match.group(1).replace('.', '').replace(',', '.')
                                            valor_deposito = float(valor_dep_str)
                                        else:
                                            valor_deposito = 0.0
                                        
                                        # Só registra se tem valor disponível > 0
                                        if valor_deposito > 0 and data_deposito and depositante:
                                            deposito_dados = {
                                                'data': data_deposito,
                                                'depositante': depositante,
                                                'valor_disponivel': valor_deposito
                                            }
                                            conta_dados['depositos'].append(deposito_dados)
                                            log_msg(f"✅ Depósito: {data_deposito} | {depositante} | R$ {valor_deposito:.2f}")
                                    
                                    except Exception as e:
                                        log_msg(f"⚠️ Erro ao processar linha de depósito: {e}")
                                        continue
                            
                            except Exception as e:
                                log_msg(f"⚠️ Erro ao extrair depósitos: {e}")
                        
                        except Exception as e:
                            log_msg(f"⚠️ Erro ao expandir parcelas: {e}")
                        
                        # Adiciona conta aos dados (mesmo sem depósitos detalhados)
                        dados_extraidos['contas'].append(conta_dados)
                        log_msg(f"✅ Conta {numero_conta} adicionada com {len(conta_dados['depositos'])} depósitos")
                    
                    else:
                        log_msg(f"⏭️ Conta {numero_conta} sem saldo disponível, ignorando")
                
                except Exception as e:
                    log_msg(f"⚠️ Erro ao processar linha {idx + 1}: {e}")
                    continue
        
        except Exception as e:
            log_msg(f"❌ Erro ao processar tabela de contas: {e}")
            return None
        
        # ===== ETAPA 8: SALVAR DADOS NO CLIPBOARD.TXT =====
        log_msg("8. Salvando dados extraídos no clipboard.txt...")
        
        try:
            # Importa a função de clipboard do anexos.py
            from anexos import salvar_conteudo_clipboard
            
            # Formata dados para clipboard
            clipboard_texto = f"=== DADOS SISCON - Processo: {dados_extraidos['numero_processo']} ===\n\n"
            
            if dados_extraidos['contas']:
                for conta in dados_extraidos['contas']:
                    clipboard_texto += f"🏛️ CONTA JUDICIAL: {conta['numero_conta']}\n"
                    clipboard_texto += f"💰 TOTAL DISPONÍVEL: R$ {conta['total_disponivel']:.2f}\n"
                    
                    if conta['depositos']:
                        clipboard_texto += "📋 DEPÓSITOS:\n"
                        for dep in conta['depositos']:
                            clipboard_texto += f"  • {dep['data']} | {dep['depositante']} | R$ {dep['valor_disponivel']:.2f}\n"
                    else:
                        clipboard_texto += "📋 DEPÓSITOS: Não expandidos ou não encontrados\n"
                    
                    clipboard_texto += "\n" + "="*60 + "\n\n"
            else:
                clipboard_texto += "⚠️ NENHUMA CONTA COM SALDO DISPONÍVEL ENCONTRADA\n"
            
            # Salva no clipboard.txt usando a função padronizada do anexos.py
            sucesso_clipboard = salvar_conteudo_clipboard(
                conteudo=clipboard_texto,
                numero_processo=numero_extraido,
                tipo_conteudo="siscon_dados",
                debug=debug
            )
            
            if sucesso_clipboard:
                log_msg("✅ Dados salvos no clipboard.txt via anexos.py")
            else:
                log_msg("⚠️ Falha ao salvar no clipboard.txt")
        
        except Exception as e:
            log_msg(f"⚠️ Erro ao salvar no clipboard.txt: {e}")
            # Fallback: tenta salvar usando pyperclip como antes
            try:
                import pyperclip
                pyperclip.copy(clipboard_texto)
                log_msg("✅ Dados salvos via pyperclip (fallback)")
            except:
                log_msg("⚠️ Falha completa ao salvar dados")
        
        # ===== ETAPA 9: FECHAR ABA E RETORNAR =====
        log_msg("9. Fechando aba SISCON...")
        
        try:
            driver.close()
            driver.switch_to.window(aba_original)
            log_msg("✅ Retornado para aba original")
        except Exception as e:
            log_msg(f"⚠️ Erro ao fechar aba: {e}")
            try:
                driver.switch_to.window(aba_original)
            except:
                pass
        
        log_msg(f"✅ Extração concluída! Encontradas {len(dados_extraidos['contas'])} contas com saldo")
        return dados_extraidos
    
    except Exception as e:
        log_msg(f"❌ Erro geral na extração: {e}")
        
        # Tenta voltar para aba original
        try:
            driver.switch_to.window(aba_original)
        except:
            pass
        
        return None


if __name__ == "__main__":
    main()

"""
=== EXEMPLOS DE USO DA EXTRAÇÃO DE DADOS SISCON ===

1. EXTRAÇÃO BÁSICA (função def_Siscon original):
   resultado = def_Siscon(driver, "1001320-19.2020.5.02.0703", "servidor", debug=True)

2. EXTRAÇÃO COM DADOS COMPLETOS (função def_Siscon + extração detalhada):
   resultado = def_Siscon(driver, "1001320-19.2020.5.02.0703", "servidor", debug=True, extrair_dados_completos=True)

3. EXTRAÇÃO SOMENTE DOS DADOS (função independente):
   dados = extrair_dados_siscon(driver, "1001320-19.2020.5.02.0703", debug=True)
   
   # Estrutura dos dados retornados:
   {
       'numero_processo': '1001320-19.2020.5.02.0703',
       'contas': [
           {
               'numero_conta': '123456789-0',
               'total_disponivel': 2572.86,
               'depositos': [
                   {
                       'data': '15/03/2024',
                       'depositante': 'EMPRESA XYZ LTDA',
                       'valor_disponivel': 1286.43
                   },
                   {
                       'data': '20/03/2024', 
                       'depositante': 'INSS',
                       'valor_disponivel': 1286.43
                   }
               ]
           }
       ]
   }

4. PROCESSAMENTO DOS DADOS EXTRAÍDOS:
   dados = extrair_dados_siscon(driver, numero_processo, debug=True)
   if dados and dados['contas']:
       for conta in dados['contas']:
           print(f"Conta: {conta['numero_conta']}")
           print(f"Total: R$ {conta['total_disponivel']:.2f}")
           for deposito in conta['depositos']:
               print(f"  {deposito['data']} - {deposito['depositante']} - R$ {deposito['valor_disponivel']:.2f}")

NOTAS TÉCNICAS:
- A extração funciona clicando nos ícones de expansão (soma-ico.png) para mostrar os depósitos
- Os dados são salvos automaticamente no clipboard em formato texto
- Somente contas e depósitos com valor disponível > 0 são processados
- A função é robusta e continua funcionando mesmo se alguns elementos não forem encontrados
"""
