# m1.py
# Fluxo automatizado de mandados PJe TRT2
###DIRETRIZES MÁXIMAS INEGOCIÁVEIS
# Priorizar edições apenas no código selecionado ou referenciado  
# Sempre validar se as alterações propostas estão estritamente alinhadas com o prompt do usuário.  
# Evitar modificações em arquivos não explicitamente mencionados.  
# Respeitar convenções de estilo definidas no projeto (ex: indentação com tabs, aspas duplas).  
# Workspace preference: NÃO altere, traduza ou reescreva NENHUMA linha do código, exceto exatamente o trecho solicitado.
# NÃO traduza palavras-chave, nomes de variáveis, comentários, strings, nem nada do código.
# NÃO faça ajustes automáticos, refatorações, nem ‘melhorias’ não solicitadas.
# Se precisar editar, use sempre o padrão # ...existing code... para indicar partes não alteradas. 
# As edições devem ser ESPECIFICAMENTE sobre erros de log ou pedidos EXPLICITOS do usuario, nada alem disso.
# tenha em mente que descumprir essas diretizes estraga o codigo e causa perda de tempo
# nao é neceasário varrer o codigo todo para cada edição pedida 
# use a busca de termos para ir diretamente à região correta e edirtar apenas o necessário, para ser mais eficiente
# ====================================================
# BLOCO 0 - GERAL
# ====================================================

# 0. Importações
import json
import sys
import time
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from Fix import (    navegar_para_tela,
    extrair_pdf,
    analise_outros,
    extrair_documento,
    criar_gigs,
    esperar_elemento,
    safe_click,
    wait,
    wait_for_visible,
    wait_for_clickable,
    sleep,
    buscar_seletor_robusto,
    limpar_temp_selenium,
    driver_pc,
    indexar_e_processar_lista,
    extrair_dados_processo,
    buscar_documento_argos,
    buscar_mandado_autor,
    buscar_ultimo_mandado,
    validar_conexao_driver,
)
from atos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    pec_idpj,
    mov_arquivar,
    ato_meiosub
)
from p2b import checar_prox
from driver_config import criar_driver, login_func, login_manual
from urllib.parse import urlparse
import sys
from datetime import datetime
import unicodedata

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

# ====================================================
# CONTROLE DE SESSÃO E PROGRESSO
# ====================================================

def carregar_progresso():
    """Carrega o estado de progresso do arquivo JSON"""
    try:
        if os.path.exists("progresso_m1.json"):
            with open("progresso_m1.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[PROGRESSO][AVISO] Erro ao carregar progresso: {e}")
    return {"processos_executados": [], "session_active": True, "last_update": None}

def salvar_progresso(progresso):
    """Salva o estado de progresso no arquivo JSON"""
    try:
        progresso["last_update"] = datetime.now().isoformat()
        with open("progresso_m1.json", "w", encoding="utf-8") as f:
            json.dump(progresso, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[PROGRESSO][ERRO] Falha ao salvar progresso: {e}")

def extrair_numero_processo(driver):
    """Extrai o número do processo da URL ou elemento da página"""
    try:
        # Método 1: da URL
        url = driver.current_url
        if "processo/" in url:
            import re
            match = re.search(r"processo/(\d+)", url)
            if match:
                return match.group(1)
        
        # Método 2: de elementos da página
        try:
            numero_elem = driver.find_element(By.CSS_SELECTOR, '[data-testid="numero-processo"], .numero-processo, .processo-numero')
            if numero_elem and numero_elem.text:
                return re.sub(r'[^\d]', '', numero_elem.text)
        except:
            pass
            
        return None
    except Exception as e:
        print(f"[PROGRESSO][ERRO] Falha ao extrair número do processo: {e}")
        return None

def verificar_acesso_negado(driver):
    """Verifica se estamos na página de acesso negado"""
    try:
        url_atual = driver.current_url
        return "acesso-negado" in url_atual.lower()
    except Exception as e:
        print(f"[PROGRESSO][ERRO] Falha ao verificar acesso negado: {e}")
        return False

def processo_ja_executado(numero_processo, progresso):
    """Verifica se o processo já foi executado"""
    if not numero_processo:
        return False
    return numero_processo in progresso.get("processos_executados", [])

def marcar_processo_executado(numero_processo, progresso):
    """Marca processo como executado"""
    # Função desativada para não registrar processos como executados nesta execução
    pass

def recuperar_sessao(driver):
    """Tenta recuperar sessão após acesso negado"""
    try:
        print("[RECOVERY][SESSÃO] Detectado acesso negado, tentando recuperar sessão...")
        
        # Navega para página de login
        login_url = "https://pje.trt2.jus.br/pjekz/login"
        driver.get(login_url)
        time.sleep(3)
        
        # Chama função de login existente
        if login_func(driver):
            print("[RECOVERY][SESSÃO] ✅ Login realizado com sucesso")
            
            # Navega de volta para a lista
            url_lista = os.getenv('URL_PJE_ESCANINHO', 'https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos')
            driver.get(url_lista)
            time.sleep(3)
            
            # Reaplica filtro de mandados devolvidos
            try:
                icone_selector = 'i.fa-reply-all.icone-clicavel'
                resultado = safe_click(driver, icone_selector, timeout=10, log=True)
                if resultado:
                    print("[RECOVERY][SESSÃO] ✅ Filtro de mandados devolvidos reaplicado")
                    time.sleep(2)
                    return True
                else:
                    print("[RECOVERY][SESSÃO] ❌ Falha ao reaplicar filtro")
            except Exception as filter_error:
                print(f"[RECOVERY][SESSÃO][ERRO] Falha no filtro: {filter_error}")
        else:
            print("[RECOVERY][SESSÃO] ❌ Falha no login")
            
        return False
    except Exception as e:
        print(f"[RECOVERY][SESSÃO][ERRO] Falha na recuperação: {e}")
        return False

def resetar_progresso():
    """Reseta o arquivo de progresso - útil para reiniciar do zero"""
    try:
        if os.path.exists("progresso_m1.json"):
            os.remove("progresso_m1.json")
            print("[PROGRESSO][RESET] ✅ Arquivo de progresso removido")
        else:
            print("[PROGRESSO][RESET] ❌ Arquivo de progresso não existe")
    except Exception as e:
        print(f"[PROGRESSO][RESET][ERRO] Falha ao resetar: {e}")

def listar_processos_executados():
    """Lista processos já executados"""
    progresso = carregar_progresso()
    executados = progresso.get("processos_executados", [])
    if executados:
        print(f"[PROGRESSO][LIST] {len(executados)} processos já executados:")
        for i, proc in enumerate(executados, 1):
            print(f"  {i:3d}. {proc}")
    else:
        print("[PROGRESSO][LIST] Nenhum processo executado ainda")
    return executados

# ====================================================

# 1. Funções de Login e Setup
def setup_driver():
    """Setup inicial do driver e limpeza"""
    from Fix import limpar_temp_selenium
    limpar_temp_selenium()
    driver = criar_driver(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return None
    return driver

# 2. Funções de Navegação
def navegacao(driver):
    """Navegação para a lista de documentos internos do PJe TRT2"""
    try:
        url_lista = os.getenv('URL_PJE_ESCANINHO', 'https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos')
        print(f'[NAV] Iniciando navegação para: {url_lista}')
        
        if not navegar_para_tela(driver, url=url_lista, delay=2):
            raise Exception('Falha na navegação para a tela de documentos internos')
        
        print('[NAV] Clicando no ícone reply-all (mandados devolvidos)...')
        # Usando as novas funções do Fix.py
        icone_selector = 'i.fa-reply-all.icone-clicavel'
        resultado = safe_click(driver, icone_selector, timeout=10, log=True)
        
        if resultado:
            print('[NAV] Ícone de mandados devolvidos clicado com sucesso.')
        else:
            print('[NAV] Falha ao clicar no ícone de mandados devolvidos')
        
        sleep(2000)  # Nova função sleep que usa milissegundos
        return resultado
        
    except Exception as e:
        print(f'[NAV][ERRO] Falha na navegação: {e}')
        return False

def iniciar_fluxo(driver):
    """Função que decide qual fluxo será aplicado com controle de sessão"""
    # Carrega progresso
    progresso = carregar_progresso()
    print(f"[PROGRESSO][SESSÃO] Carregado progresso com {len(progresso.get('processos_executados', []))} processos já executados")
    
    def fluxo_callback(driver):
        try:
            # VERIFICAÇÃO DE SESSÃO: Antes de qualquer processamento
            if verificar_acesso_negado(driver):
                print("[PROCESSAR][ALERTA] Não estamos na página da lista! URL:", driver.current_url)
                if recuperar_sessao(driver):
                    print("[RECOVERY][SESSÃO] ✅ Sessão recuperada com sucesso, continuando processamento...")
                else:
                    print("[RECOVERY][SESSÃO] ❌ Falha na recuperação da sessão, abortando processo atual")
                    return
            
            # VERIFICAÇÃO DE PROGRESSO: Extrai número do processo, mas não pula execução
            numero_processo = extrair_numero_processo(driver)
            # Removido o skip para permitir novas ações nos processos
            
            # Busca o cabeçalho do documento ativo
            try:
                # Usando as novas funções do Fix.py
                cabecalho_selector = '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'
                cabecalho = wait_for_visible(driver, cabecalho_selector, timeout=10)
                
                if not cabecalho:
                    print('[ERRO] Cabeçalho do documento não encontrado após espera')
                    return
                    
                texto_doc = cabecalho.text
                if not texto_doc:
                    print('[ERRO] Cabeçalho do documento vazio')
                    return
            except Exception as e:
                print(f'[ERRO] Cabeçalho do documento não encontrado: {e}')
                return
                
            texto_lower = texto_doc.lower()
            # Identificação dos fluxos
            if any(termo in texto_lower for termo in ['pesquisa patrimonial', 'argos', 'devolução de ordem de pesquisa', 'certidão de devolução']):
                print(f'[ARGOS] Processo em análise: {texto_doc}')
                processar_argos(driver, log=True)  # Ativamos o log para depuração
                # VALIDAÇÃO PÓS ARGOS: Verifica se o contexto do driver ainda é válido
                try:
                    _ = driver.window_handles
                except Exception as e:
                    print(f'[FLUXO][PEC_IDPJ] Contexto do driver perdido após processar_argos: {e}')
                    # Força exceção para interromper o fluxo normal e evitar erro na limpeza de abas
                    raise Exception(f"Driver context lost after processar_argos: {e}")
            elif any(termo in texto_lower for termo in ['oficial de justiça', 'certidão de oficial']):
                print(f'[OUTROS] Processo em análise: {texto_doc}')
                fluxo_mandados_outros(driver, log=False)
            else:
                print(f'[AVISO] Documento não identificado: {texto_doc}')
                
        except Exception as e:
            print(f'[ERRO] Falha ao processar mandado: {str(e)}')
        finally:
            # Limpeza de abas com validação robusta de contexto
            try:
                # Primeira validação: verifica se o contexto ainda existe
                try:
                    current_handles = driver.window_handles
                    current_handle = driver.current_window_handle
                except Exception as context_error:
                    print(f"[LIMPEZA][ERRO] Contexto do browser perdido - abortando limpeza: {context_error}")
                    return
                
                # Se há múltiplas abas e não estamos na principal, fecha a atual
                if len(current_handles) > 1:
                    main_window = current_handles[0] if current_handles else None
                    
                    if main_window and current_handle != main_window:
                        try:
                            driver.close()
                            print(f"[LIMPEZA] Aba secundária fechada: {current_handle[:8]}...")
                            
                            # Troca para aba principal com validação
                            remaining_handles = driver.window_handles
                            if main_window in remaining_handles:
                                driver.switch_to.window(main_window)
                                print(f"[LIMPEZA] Retornado para aba principal: {main_window[:8]}...")
                            elif remaining_handles:
                                driver.switch_to.window(remaining_handles[0])
                                print(f"[LIMPEZA] Usando primeira aba disponível: {remaining_handles[0][:8]}...")
                            else:
                                print("[LIMPEZA][ERRO] Nenhuma aba restante após fechamento.")
                                return
                            
                            # Validação final
                            try:
                                test_url = driver.current_url
                                print(f"[LIMPEZA] Contexto validado: {test_url[:50]}...")
                            except Exception as validation_error:
                                print(f"[LIMPEZA][ERRO] Falha na validação final: {validation_error}")
                                
                        except Exception as close_error:
                            print(f"[LIMPEZA][ERRO] Falha ao fechar/trocar aba: {close_error}")
                    else:
                        print("[LIMPEZA] Já na aba principal ou aba única - nenhuma ação necessária.")
                else:
                    print("[LIMPEZA] Aba única detectada - preservando contexto.")
                    
            except Exception as cleanup_error:
                print(f"[LIMPEZA][ERRO CRÍTICO] Falha geral na limpeza: {cleanup_error}")
                print("[LIMPEZA][AVISO] Contexto do browser pode estar comprometido.")
            
            # MARCAÇÃO DE PROGRESSO: Marca processo como executado se chegou até aqui
            if numero_processo:
                marcar_processo_executado(numero_processo, progresso)
            
            print('[FLUXO] Processo concluído, retornando à lista')
    print('[FLUXO] Filtro de mandados devolvidos já garantido na navegação. Iniciando processamento...')
    indexar_e_processar_lista(driver, fluxo_callback)

# 3. Funções de Processamento
def verificar_autor_documento(documento, driver):
    """
    Função para verificar quem assinou/é responsável por um documento.
    Extrai informações de autor/responsável do texto do documento.
    """
    try:
        if not documento:
            print("[MANDADOS][OUTROS][LOG] Documento vazio, não é possível verificar autor")
            return None
            
        # Converte para string se necessário
        texto = str(documento).lower()
        
        # Padrões de assinatura/responsabilidade para buscar
        padroes_autor = [
            r'assinado por\s*[:\-]?\s*([^,\n\.]+)',
            r'assinatura digital\s*[:\-]?\s*de\s*([^,\n\.]+)',
            r'responsável\s*[:\-]?\s*([^,\n\.]+)',
            r'elaborado por\s*[:\-]?\s*([^,\n\.]+)',
            r'autor\s*[:\-]?\s*([^,\n\.]+)',
            r'oficial de justiça\s*[:\-]?\s*([^,\n\.]+)',
        ]
        
        # Buscar padrões no texto
        for padrao in padroes_autor:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                nome_autor = match.group(1).strip()
                # Limpar caracteres extras
                nome_autor = re.sub(r'[^\w\s]', ' ', nome_autor).strip()
                # Capitalizar nome
                nome_autor = nome_autor.title()
                print(f"[MANDADOS][OUTROS][LOG] Autor identificado: {nome_autor}")
                return nome_autor
                
        # Busca específica por "silas passos" no texto
        if 'silas passos' in texto:
            print("[MANDADOS][OUTROS][LOG] Referência a 'Silas Passos' encontrada diretamente no texto")
            return 'Silas Passos'
            
        print("[MANDADOS][OUTROS][LOG] Nenhum autor identificado no documento")
        return None
        
    except Exception as e:
        print(f"[MANDADOS][OUTROS][ERRO] Falha ao verificar autor do documento: {e}")
        return None

def lembrete_bloq(driver, debug=False):
    """
    Cria lembrete de bloqueio com título "Bloqueio pendente" e conteúdo "processar após IDPJ".
    """
    try:
        if debug:
            print('[ARGOS][LEMBRETE] Criando lembrete de bloqueio...')
            
        # 1. Clique no menu (fa-bars)
        menu_clicked = safe_click(driver, '.fa-bars', log=debug)
        if not menu_clicked and debug:
            print('[ARGOS][LEMBRETE] Falha ao clicar no menu')
        sleep(1000)  # Nova função sleep que usa milissegundos
        
        # 2. Clique no ícone de lembrete (fa thumbtack)
        lembrete_selector = '.lista-itens-menu > li:nth-child(16) > pje-icone-post-it:nth-child(1) > li:nth-child(1) > button:nth-child(1)'
        lembrete_clicked = safe_click(driver, lembrete_selector, log=debug)
        if not lembrete_clicked and debug:
            print('[ARGOS][LEMBRETE] Falha ao clicar no ícone de lembrete')
        sleep(1000)
        
        # 3. Foco no conteúdo do diálogo
        dialog_clicked = safe_click(driver, '.mat-dialog-content', log=debug)
        sleep(1000)
        
        # 4. Preenche título
        titulo = wait_for_visible(driver, '#tituloPostit', timeout=5)
        if titulo:
            titulo.clear()
            titulo.send_keys('Bloqueio pendente')
        else:
            print('[ARGOS][LEMBRETE] Campo de título não encontrado')
        
        # 5. Preenche conteúdo
        conteudo = wait_for_visible(driver, '#conteudoPostit', timeout=5)
        if conteudo:
            conteudo.clear()
            conteudo.send_keys('processar após IDPJ')
        else:
            print('[ARGOS][LEMBRETE] Campo de conteúdo não encontrado')
        
        # 6. Clica em salvar
        salvar_clicked = safe_click(driver, 'button.mat-raised-button:nth-child(1)', log=debug)
        if not salvar_clicked and debug:
            print('[ARGOS][LEMBRETE] Falha ao clicar no botão salvar')
        sleep(1000)
        
        if debug:
            print('[ARGOS][LEMBRETE] Lembrete criado com sucesso.')
            
    except Exception as e:
        if debug:
            print(f'[ARGOS][LEMBRETE][ERRO] Falha ao criar lembrete: {e}')
            raise

def extract_sisbajud_result_from_text(text, log=True):
    # Busca a primeira ocorrência de 'determinações normativas e legais' no texto completo
    lines = text.splitlines()
    det_idx = -1
    for idx, line in enumerate(lines):
        if 'determinações normativas e legais' in line.lower():
            det_idx = idx
            break
    if det_idx == -1:
        if log:
            print('[SISBAJUD][DEBUG] determinações normativas e legais marker not found in text.')
        return 'negativo', 'determinações normativas e legais marker not found, default negativo'
    # Busca por "Bloqueio de valores" após "determinações normativas e legais"
    bloqueio_idx = -1
    for offset in range(1, 21):
        if det_idx + offset >= len(lines):
            break
        result_line = lines[det_idx + offset].strip().lower()
        if not result_line:
            continue
        if log:
            print(f'[SISBAJUD][DEBUG] Checking line after determinações normativas e legais: {repr(result_line)}')
        
        # Busca pela seção "Bloqueio de valores"
        if 'bloqueio de valores' in result_line:
            bloqueio_idx = det_idx + offset
            if log:
                print(f'[SISBAJUD][DEBUG] Found "Bloqueio de valores" at line {bloqueio_idx}')
            break
    
    # Se não encontrou "Bloqueio de valores", não há SISBAJUD
    if bloqueio_idx == -1:
        if log:
            print('[SISBAJUD][DEBUG] "Bloqueio de valores" not found after determinações normativas e legais')
        return 'negativo', 'Bloqueio de valores não encontrado, sem SISBAJUD'
    
    # Analisa as linhas após "Bloqueio de valores" procurando por SISBAJUD
    for offset in range(1, 15):
        if bloqueio_idx + offset >= len(lines):
            break
        sisbajud_line = lines[bloqueio_idx + offset].strip().lower()
        if not sisbajud_line:
            continue
        if log:
            print(f'[SISBAJUD][DEBUG] Checking line after Bloqueio de valores: {repr(sisbajud_line)}')
        
        # Busca por SISBAJUD e verifica se é seguido por Negativo ou Positivo
        if 'sisbajud' in sisbajud_line:
            if log:
                print(f'[SISBAJUD][DEBUG] Found SISBAJUD marker at line')
            
            # Verifica as próximas linhas após SISBAJUD
            for sib_offset in range(1, 5):
                if bloqueio_idx + offset + sib_offset >= len(lines):
                    break
                resultado_line = lines[bloqueio_idx + offset + sib_offset].strip().lower()
                if not resultado_line:
                    continue
                if log:
                    print(f'[SISBAJUD][DEBUG] Checking SISBAJUD result line: {repr(resultado_line)}')
                
                if 'negativo' in resultado_line:
                    if log:
                        print('[SISBAJUD][DEBUG] Found "Negativo" in SISBAJUD section')
                    return 'negativo', 'SISBAJUD Negativo na seção Bloqueio de valores'
                elif 'positivo' in resultado_line:
                    if log:
                        print('[SISBAJUD][DEBUG] Found "Positivo" in SISBAJUD section')
                    return 'positivo', 'SISBAJUD Positivo na seção Bloqueio de valores'
            
            # Se encontrou SISBAJUD mas não encontrou resultado, assume negativo
            if log:
                print('[SISBAJUD][DEBUG] Found SISBAJUD but no clear result, assuming negativo')
            return 'negativo', 'SISBAJUD encontrado mas resultado inconclusivo'
    if log:
        print('[SISBAJUD][DEBUG] No rule matched after determinações normativas e legais marker, default negativo.')
    return 'negativo', 'nenhuma regra anterior satisfeita, default negativo'

# ...existing code...

def andamento_argos(driver, resultado_sisbajud, sigilo_anexos, log=True):
    """
    Processa o andamento do Argos com base no resultado do SISBAJUD, sigilo dos anexos e tipo de documento.
    1. Busca documento relevante (decisão ou despacho)
    2. Aplica regras específicas do Argos
    """
    try:
        if log:
            print('[ARGOS][ANDAMENTO] Iniciando processamento do andamento...')
            
        # 1. Busca documento relevante
        max_tentativas = 3
        tentativa = 0
        regra_aplicada = False
        
        while tentativa < max_tentativas and not regra_aplicada:
            tentativa += 1
            if log:
                print(f'[ARGOS][ANDAMENTO] Tentativa {tentativa}/{max_tentativas} para buscar documento relevante...')
                
            try:
                # Corrigindo o erro de desempacotamento
                resultado_documento = buscar_documento_argos(driver, log=log)
                
                # Verifica se o resultado é válido
                if not resultado_documento:
                    if log:
                        print(f'[ARGOS][ANDAMENTO][ERRO] Nenhum documento encontrado na tentativa {tentativa}')
                    continue
                
                # Tenta desempacotar o resultado (flexível para diferentes formatos de retorno)
                try:
                    if isinstance(resultado_documento, tuple):
                        if len(resultado_documento) >= 2:
                            texto_documento, tipo_documento = resultado_documento[0], resultado_documento[1]
                        elif len(resultado_documento) == 1:
                            texto_documento, tipo_documento = resultado_documento[0], 'documento'
                        else:
                            if log:
                                print(f'[ARGOS][ANDAMENTO][ERRO] Tupla vazia retornada')
                            continue
                    elif isinstance(resultado_documento, str):
                        # Se retornou apenas uma string, assume como texto do documento
                        texto_documento, tipo_documento = resultado_documento, 'documento'
                    else:
                        if log:
                            print(f'[ARGOS][ANDAMENTO][ERRO] Tipo de resultado inesperado: {type(resultado_documento)} com valor {resultado_documento}')
                        continue
                except Exception as e_unpack:
                    if log:
                        print(f'[ARGOS][ANDAMENTO][ERRO] Erro ao desempacotar resultado: {e_unpack}')
                    continue
                    
                if log:
                    print(f'[ARGOS][DOCUMENTO] Tipo encontrado: {tipo_documento}')
                    
                # 2. Aplica regras específicas do Argos
                regra_foi_aplicada = aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=log)
                
                if regra_foi_aplicada:
                    regra_aplicada = True
                    if log:
                        print('[ARGOS][ANDAMENTO] Regra aplicada com sucesso, processo concluído.')
                else:
                    if log:
                        print('[ARGOS][ANDAMENTO] Nenhuma regra aplicada, tentando próximo documento...')
                    # Continua no loop para tentar próximo documento
                
            except ValueError as ve:
                if log:
                    print(f'[ARGOS][ANDAMENTO][ERRO] Erro ao processar documento (tentativa {tentativa}): {ve}')
                
                # Se não for a última tentativa, tenta o próximo documento
                if tentativa < max_tentativas:
                    if log:
                        print('[ARGOS][ANDAMENTO] Tentando próximo documento...')
                    
                    try:
                        # Buscando itens da timeline para usar com checar_prox
                        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                        if itens:
                            # Determinando o índice atual do documento
                            doc_idx = 0
                            for idx, item in enumerate(itens):
                                try:
                                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento.ativo')
                                    if link:
                                        doc_idx = idx
                                        break
                                except Exception:
                                    continue
                            
                            # Chamando checar_prox para encontrar o próximo documento
                            doc_encontrado, doc_link, novo_idx = checar_prox(driver, itens, doc_idx, None, "")
                            
                            if doc_encontrado and doc_link:
                                if log:
                                    print(f'[ARGOS][ANDAMENTO] Próximo documento encontrado no índice {novo_idx}, abrindo...')
                                
                                # Clicando no próximo documento
                                driver.execute_script('arguments[0].scrollIntoView({block: "center"});', doc_link)
                                sleep(500)
                                click_resultado = safe_click(driver, doc_link, log=log)
                                
                                if not click_resultado:
                                    if log:
                                        print('[ARGOS][ANDAMENTO] Falha no clique seguro, tentando via JavaScript')
                                    try:
                                        driver.execute_script('arguments[0].click();', doc_link)
                                    except Exception as e:
                                        if log:
                                            print(f'[ARGOS][ANDAMENTO][ERRO] Falha ao clicar no próximo documento: {e}')
                                
                                # Aguardando carregamento
                                sleep(1500)
                            else:
                                if log:
                                    print('[ARGOS][ANDAMENTO] Nenhum próximo documento encontrado, interrompendo tentativas.')
                                break
                        else:
                            if log:
                                print('[ARGOS][ANDAMENTO] Nenhum item encontrado na timeline, interrompendo tentativas.')
                            break
                    except Exception as e_proximo:
                        if log:
                            print(f'[ARGOS][ANDAMENTO][ERRO] Falha ao buscar próximo documento: {e_proximo}')
                        break
                else:
                    if log:
                        print('[ARGOS][ANDAMENTO] Máximo de tentativas atingido, encerrando busca.')
            except Exception as e:
                if log:
                    print(f'[ARGOS][ANDAMENTO][ERRO] Erro não tratado ao processar documento: {e}')
                break
        
        if not regra_aplicada and log:
            print('[ARGOS][ANDAMENTO] Nenhuma regra aplicável após todas as tentativas, prosseguindo.')
            
    except Exception as e:
        if log:
            print(f'[ARGOS][ANDAMENTO][ERRO] Falha no processamento do andamento: {e}')
            raise

# ...existing code...

def aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """
    Aplica as regras específicas do Argos com base no resultado do SISBAJUD, sigilo dos anexos e tipo de documento.
    Retorna True se uma regra foi aplicada, False caso contrário.
    """
    try:
        regra_aplicada = None
        trecho_relevante = texto_documento if texto_documento else ''
        if debug:
            print(f'[ARGOS][REGRAS] Analisando regras para tipo: {tipo_documento}')
            print(f'[ARGOS][REGRAS] Resultado SISBAJUD: {resultado_sisbajud}')
            print(f'[ARGOS][REGRAS] Sigilo anexos: {sigilo_anexos}')
        
        # REGRA: Despacho com "Realize-se a pesquisa INFOJUD"
        if tipo_documento == 'despacho' and texto_documento and 'realize-se a pesquisa infojud' in texto_documento.lower():
            if any(v == 'sim' for v in sigilo_anexos.values()):
                if debug:
                    print('[ARGOS][REGRAS] Despacho com pesquisa INFOJUD e anexo sigiloso - chamando ato_termoS')
                ato_termoS(driver, debug=debug)
            else:
                if debug:
                    print('[ARGOS][REGRAS] Despacho com pesquisa INFOJUD e sem anexo sigiloso - chamando ato_meios')
                ato_meios(driver, debug=debug)
            regra_aplicada = 'despacho+infojud'
            print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {texto_documento}')
            return True
        
        # NOVA REGRA PRIORIDADE MÁXIMA: Despacho com palavra "ARGOS"
        if tipo_documento == 'despacho' and texto_documento and 'argos' in texto_documento.lower():
            regra_aplicada = '[PRIORIDADE MÁXIMA] despacho+argos'
            if debug:
                print('[ARGOS][REGRAS] NOVA REGRA: Despacho com ARGOS detectado - aplicando regras específicas')
            
            if resultado_sisbajud == 'positivo':
                regra_aplicada += ' | sisbajud positivo => ato_bloq'
                if debug:
                    print('[ARGOS][REGRAS] ARGOS: SISBAJUD positivo, executando ato_bloq')
                ato_bloq(driver, debug=debug)
                print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
                return True
            elif resultado_sisbajud == 'negativo':
                tem_sigiloso = any(v == 'sim' for v in sigilo_anexos.values()) if sigilo_anexos else False
                if tem_sigiloso:
                    regra_aplicada += ' | sisbajud negativo, com sigiloso => ato_termoS'
                    if debug:
                        print('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo com anexo sigiloso, executando ato_termoS')
                    ato_termoS(driver, debug=debug)
                else:
                    regra_aplicada += ' | sisbajud negativo, sem sigiloso => ato_meios'
                    if debug:
                        print('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo sem anexo sigiloso, executando ato_meios')
                    ato_meios(driver, debug=debug)
                print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
                return True
        
        # Nova regra para detectar "devendo se manifestar"
        if texto_documento and "devendo se manifestar" in texto_documento.lower():
            if debug:
                print('[ARGOS][REGRAS] Texto "devendo se manifestar" detectado, buscando próximo documento...')
            regra_aplicada = 'devendo se manifestar'
            
            # Buscando itens da timeline para usar com checar_prox
            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
            if not itens:
                if debug:
                    print('[ARGOS][REGRAS] Nenhum item encontrado na timeline para análise de próximo documento')
            else:
                # Determinando o índice atual do documento
                doc_idx = 0
                for idx, item in enumerate(itens):
                    try:
                        link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento.ativo')
                        if link:
                            doc_idx = idx
                            break
                    except Exception:
                        continue
                
                # Chamando checar_prox para encontrar o próximo documento
                if debug:
                    print(f'[ARGOS][REGRAS] Índice do documento atual: {doc_idx}, buscando próximo...')
                doc_encontrado, doc_link, novo_idx = checar_prox(driver, itens, doc_idx, None, texto_documento)
                
                if doc_encontrado and doc_link:
                    if debug:
                        print(f'[ARGOS][REGRAS] Próximo documento encontrado no índice {novo_idx}, abrindo...')
                    
                    # Clicando no próximo documento
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', doc_link)
                    sleep(500)
                    click_resultado = safe_click(driver, doc_link, log=debug)
                    
                    if not click_resultado:
                        if debug:
                            print('[ARGOS][REGRAS] Falha no clique seguro, tentando via JavaScript')
                        try:
                            driver.execute_script('arguments[0].click();', doc_link)
                        except Exception as e:
                            if debug:
                                print(f'[ARGOS][REGRAS][ERRO] Falha ao clicar no próximo documento: {e}')
                    
                    # Aguardando carregamento
                    sleep(1500)
                    
                    # Extraindo texto do novo documento com tratamento de erro
                    try:
                        resultado_extracao = extrair_documento(driver)
                        if len(resultado_extracao) >= 2:
                            novo_texto = resultado_extracao[0]
                            novo_tipo = "decisao" if "decisão" in doc_link.text.lower() else "despacho"
                            
                            if debug:
                                print(f'[ARGOS][REGRAS] Novo documento extraído (tipo {novo_tipo})')
                                print(f'[ARGOS][REGRAS] Repetindo análise de regras para o novo documento')
                            
                            # Chamada recursiva para aplicar regras no novo documento
                            resultado_recursivo = aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, novo_tipo, novo_texto, debug=debug)
                            regra_aplicada += ' | análise repetida em documento seguinte'
                            print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
                            return resultado_recursivo
                        else:
                            if debug:
                                print(f'[ARGOS][REGRAS][ERRO] Resultado inesperado da extrair_documento: {len(resultado_extracao)} valores')
                    except Exception as e_extracao:
                        if debug:
                            print(f'[ARGOS][REGRAS][ERRO] Falha ao extrair texto do próximo documento: {e_extracao}')
                else:
                    if debug:
                        print('[ARGOS][REGRAS] Nenhum próximo documento encontrado, continuando com a análise atual')
        
        # PRIORIDADE ABSOLUTA: Regra "defiro a instauração" com SISBAJUD positivo
        if 'defiro a instauração' in texto_documento.lower() and resultado_sisbajud == 'positivo':
            regra_aplicada = '[PRIORIDADE] decisao+defiro a instauracao+sisbajud positivo'
            if debug:
                print('[ARGOS][REGRAS][PRIORIDADE] ✅ REGRA DE PRECEDÊNCIA: defiro a instauração + SISBAJUD positivo')
                print('[ARGOS][REGRAS][PRIORIDADE] Esta regra prevalece sobre qualquer outra')
            regra_aplicada += ' | lembrete_bloq + gigs 0/xs_assinar + pec_idpj [PRECEDENCIA ABSOLUTA]'
            lembrete_bloq(driver, debug=debug)
            criar_gigs(driver, 7, '', 'xs carta')
            pec_idpj(driver, debug=debug)
            
            # Executa Infojud após pec_idpj
            try:
                from infojud import Infojud
                if debug:
                    print('[ARGOS][REGRAS][INFOJUD] Executando Infojud após pec_idpj...')
                Infojud(driver=driver, log=debug)
                if debug:
                    print('[ARGOS][REGRAS][INFOJUD] Infojud executado com sucesso.')
            except Exception as e:
                if debug:
                    print(f'[ARGOS][REGRAS][INFOJUD][ERRO] Falha ao executar Infojud: {e}')
            
            # VALIDAÇÃO PÓS PEC_IDPJ
            try:
                _ = driver.window_handles
            except Exception as e:
                if debug:
                    print(f'[ARGOS][REGRAS][PEC_IDPJ] Contexto do driver perdido após pec_idpj: {e}')
                raise Exception(f"Driver context lost after pec_idpj: {e}")
            print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
            return True
        
        # Outras regras de "defiro a instauração" (sem SISBAJUD positivo)
        elif 'defiro a instauração' in texto_documento.lower():
            regra_aplicada = 'decisao+defiro a instauracao'
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como decisão de instauração')
            if resultado_sisbajud == 'negativo':
                regra_aplicada += ' | sisbajud negativo => gigs 0/xs_assinar + pec_idpj'
                criar_gigs(driver, 7, '', 'xs carta')
                pec_idpj(driver, debug=debug)
                
                # Executa Infojud após pec_idpj
                try:
                    from infojud import Infojud
                    if debug:
                        print('[ARGOS][REGRAS][INFOJUD] Executando Infojud após pec_idpj...')
                    Infojud(driver=driver, log=debug)
                    if debug:
                        print('[ARGOS][REGRAS][INFOJUD] Infojud executado com sucesso.')
                except Exception as e:
                    if debug:
                        print(f'[ARGOS][REGRAS][INFOJUD][ERRO] Falha ao executar Infojud: {e}')
                
                # VALIDAÇÃO PÓS PEC_IDPJ
                try:
                    _ = driver.window_handles
                except Exception as e:
                    if debug:
                        print(f'[ARGOS][REGRAS][PEC_IDPJ] Contexto do driver perdido após pec_idpj: {e}')
                    raise Exception(f"Driver context lost after pec_idpj: {e}")
                print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
                return True
        
        # 1. Se é despacho com texto específico
        elif tipo_documento == 'despacho' and any(p in texto_documento.lower() for p in ['em que pese a ausência', 'argos']):
            regra_aplicada = 'despacho+argos'
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como despacho com texto específico')
            if resultado_sisbajud == 'negativo' and all(v == 'nao' for v in sigilo_anexos.values()):
                regra_aplicada += ' | sisbajud negativo, nenhum anexo sigiloso => ato_meios'
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo e nenhum anexo sigiloso - chamando ato_meios')
                ato_meios(driver, debug=debug)
            elif resultado_sisbajud == 'negativo' and any(v == 'sim' for v in sigilo_anexos.values()):
                regra_aplicada += ' | sisbajud negativo, anexo sigiloso => ato_termoS'
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo com anexo sigiloso - chamando ato_termoS')
                ato_termoS(driver, debug=debug)
            elif resultado_sisbajud == 'positivo':
                regra_aplicada += ' | sisbajud positivo => ato_bloq'
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD positivo - chamando ato_bloq')
                ato_bloq(driver, debug=debug)
            print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
            return True
        
        elif tipo_documento == 'decisao' and 'tendo em vista que' in texto_documento.lower():
            regra_aplicada = 'decisao+tendo em vista que'
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como decisão com texto sobre reclamada')
            try:
                import sys
                from urllib.parse import urlparse
            except ImportError:
                if debug:
                    print('[ARGOS][REGRAS] Importação direta de urlparse falhou, tentando via urllib.parse')
                from urllib.parse import urlparse
            
            dados_processo = extrair_dados_processo(driver)
            if debug:
                print(f'[ARGOS][REGRAS] Dados do processo extraídos: {dados_processo}')
            
            num_reclamadas = len(dados_processo.get('reu', []))
            if debug:
                print(f'[ARGOS][REGRAS] Número de reclamadas (réus) encontradas: {num_reclamadas}')
            
            if num_reclamadas == 1:
                regra_aplicada += ' | uma reclamada'
                if debug:
                    print('[ARGOS][REGRAS] Uma única reclamada - seguindo regras do despacho')
                if resultado_sisbajud == 'negativo' and all(v == 'nao' for v in sigilo_anexos.values()):
                    regra_aplicada += ' | sisbajud negativo, nenhum anexo sigiloso => ato_meios'
                    ato_meios(driver, debug=debug)
                elif resultado_sisbajud == 'negativo' and any(v == 'sim' for v in sigilo_anexos.values()):
                    regra_aplicada += ' | sisbajud negativo, anexo sigiloso => ato_termoS'
                    ato_termoS(driver, debug=debug)
                else:
                    regra_aplicada += ' | sisbajud positivo => ato_bloq'
                    ato_bloq(driver, debug=debug)
            else:
                regra_aplicada += ' | multiplas reclamadas'
                if debug:
                    print(f'[ARGOS][REGRAS] Múltiplas reclamadas ({num_reclamadas}) - verificando SISBAJUD')
                if resultado_sisbajud == 'negativo':
                    regra_aplicada += ' | sisbajud negativo => ato_meiosub'
                    ato_meiosub(driver, debug=debug)
                    print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
                    return True
                else:
                    regra_aplicada += ' | sisbajud positivo => ato_bloq'
                    ato_bloq(driver, debug=debug)
                    print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
                    return True
        else:
            regra_aplicada = f'nao identificado: {tipo_documento}'
            if debug:
                print(f'[ARGOS][REGRAS] Tipo de documento não identificado: {tipo_documento}')
                    
        # Log sempre que chamado, para rastreabilidade
        print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
        return False  # Nenhuma regra específica foi aplicada
    except Exception as e:
        if debug:
            print(f'[ARGOS][REGRAS][ERRO] Falha ao aplicar regras: {e}')
        return False
# ...existing code...

def fechar_intimacao(driver, log=True):
    """
    Fecha a intimação do processo, otimizado para performance e confiabilidade.
    """
    try:
        if log:
            print('[INTIMACAO] Iniciando processo de fechar intimação...')
        
        # 1. Abrir menu principal
        menu_selector = '#botao-menu'
        menu_clicked = safe_click(driver, menu_selector, timeout=10, log=log)
        if not menu_clicked:
            if log:
                print('[INTIMACAO] Falha ao abrir menu principal')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return True
        
        if log:
            print('[INTIMACAO] Menu principal aberto')
        
        # 2. Clicar no botão Expedientes
        btn_exp_selector = 'button[aria-label="Expedientes"]:not([disabled])'
        btn_exp_clicked = safe_click(driver, btn_exp_selector, timeout=5, log=log)
        if not btn_exp_clicked:
            if log:
                print('[INTIMACAO] Falha ao clicar no botão Expedientes')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return True
        
        if log:
            print('[INTIMACAO] Botão Expedientes clicado')
        
        # 3. Esperar o modal de expedientes aparecer
        modal_selector = 'mat-dialog-container pje-expedientes-dialogo'
        modal = wait_for_visible(driver, modal_selector, timeout=5)
        if not modal:
            if log:
                print('[INTIMACAO] Modal de expedientes não encontrado, continuando mesmo assim')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return True
        
        # 4. Procurar diretamente pela linha com prazo 30 e checkbox disponível
        try:
            # Estratégia otimizada: Encontrar todas as linhas e verificar em uma única passagem
            rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
            if log:
                print(f'[INTIMACAO] Encontradas {len(rows)} linhas de expedientes')
            
            linha_com_prazo_30 = None
            checkbox_disponivel = False
            
            # Percorrer as linhas procurando pela com prazo 30 e checkbox disponível
            for i, row in enumerate(rows):
                try:
                    # Obter todas as células da linha
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    
                    # Verificar se há células suficientes (pelo menos 9 colunas)
                    if len(cells) < 9:
                        continue
                    
                    # Verificar se a 9ª coluna (índice 8) contém "30"
                    prazo_cell = cells[8]  # 9ª coluna (índice 8) - coluna "Prazo"
                    prazo_texto = prazo_cell.text.strip()
                    
                    if log and i < 5:  # Log as primeiras 5 linhas para debug
                        print(f'[INTIMACAO] Linha {i+1}: prazo = "{prazo_texto}"')
                    
                    if prazo_texto == '30':
                        if log:
                            print(f'[INTIMACAO] Linha com prazo 30 encontrada (linha {i+1})')
                        
                        # Verificar se há checkbox disponível na última coluna (índice 10 - coluna "Fechado")
                        if len(cells) >= 11:
                            checkbox_cell = cells[10]  # 11ª coluna (índice 10) - coluna "Fechado"
                            
                            # Primeiro verifica se já está fechado (texto "Sim" visível)
                            texto_fechado_divs = checkbox_cell.find_elements(By.CSS_SELECTOR, 'div:not([hidden])')
                            texto_fechado = ""
                            for div in texto_fechado_divs:
                                texto = div.text.strip()
                                if texto:
                                    texto_fechado = texto
                                    break
                            
                            if texto_fechado.lower() == "sim":
                                if log:
                                    print('[INTIMACAO] Expediente já está fechado (texto "Sim" encontrado)')
                                # Não quebra o loop, continua procurando por linhas não fechadas
                                continue
                            
                            # Procurar pelo checkbox que NÃO está escondido
                            checkbox_divs_visiveis = checkbox_cell.find_elements(By.CSS_SELECTOR, 'div:not([hidden]) mat-checkbox')
                            
                            if checkbox_divs_visiveis:
                                # Checkbox está disponível (não escondido)
                                linha_com_prazo_30 = row
                                checkbox_disponivel = True
                                if log:
                                    print('[INTIMACAO] Checkbox disponível encontrado (não escondido)')
                                    print(f'[INTIMACAO] HTML da célula do checkbox: {checkbox_cell.get_attribute("innerHTML")[:200]}...')
                                break
                            else:
                                # Verificar se existe div escondida (expediente já fechado)
                                checkbox_divs_escondidos = checkbox_cell.find_elements(By.CSS_SELECTOR, 'div[hidden] mat-checkbox')
                                if checkbox_divs_escondidos:
                                    if log:
                                        print('[INTIMACAO] Checkbox escondido (expediente já fechado)')
                                else:
                                    if log:
                                        print('[INTIMACAO] Estrutura de checkbox não encontrada')
                                # Continua procurando outras linhas
                                continue
                        else:
                            if log:
                                print('[INTIMACAO] Linha não tem coluna de checkbox suficiente')
                            break
                except Exception as e:
                    if log:
                        print(f'[INTIMACAO] Erro ao verificar linha {i+1}: {str(e)}')
                    continue
            
            # Se não encontrou linha com prazo 30 ou checkbox não está disponível
            if not linha_com_prazo_30 or not checkbox_disponivel:
                if log:
                    if linha_com_prazo_30 is None:
                        print('[INTIMACAO] Nenhuma linha com prazo 30 encontrada')
                    else:
                        print('[INTIMACAO] Todas as linhas com prazo 30 já estão fechadas')
                    print('[INTIMACAO] Fechando modal e prosseguindo')
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    if log:
                        print('[INTIMACAO] Modal fechado com ESC')
                except Exception:
                    pass
                return True
            
            # 5. Selecionar o checkbox
            checkbox_selecionada = False
            try:
                # Tentar encontrar o checkbox visível na última coluna
                checkbox_element = linha_com_prazo_30.find_element(By.CSS_SELECTOR, 'td:last-child div:not([hidden]) mat-checkbox')
                
                if log:
                    print(f'[INTIMACAO] Checkbox encontrado: {checkbox_element.get_attribute("class")}')
                
                # Verificar se o checkbox está visível e habilitado
                if checkbox_element.is_displayed():
                    if log:
                        print('[INTIMACAO] Checkbox está visível, tentando clicar...')
                    
                    # Primeira tentativa: clique direto no mat-checkbox
                    checkbox_selecionada = safe_click(driver, checkbox_element, timeout=3, log=log)
                    
                    if not checkbox_selecionada:
                        if log:
                            print('[INTIMACAO] Clique direto falhou, tentando no input interno...')
                        
                        # Segunda tentativa: clicar no input interno
                        try:
                            input_checkbox = checkbox_element.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                            checkbox_selecionada = safe_click(driver, input_checkbox, timeout=3, log=log)
                        except Exception as e_input:
                            if log:
                                print(f'[INTIMACAO] Input interno não encontrado: {e_input}')
                    
                    if not checkbox_selecionada:
                        if log:
                            print('[INTIMACAO] Cliques normais falharam, tentando JavaScript...')
                        
                        # Terceira tentativa: JavaScript no mat-checkbox
                        try:
                            driver.execute_script("arguments[0].click();", checkbox_element)
                            sleep(500)
                            
                            # Verificar se foi marcado
                            input_checkbox = checkbox_element.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                            if input_checkbox.is_selected():
                                checkbox_selecionada = True
                                if log:
                                    print('[INTIMACAO] Checkbox selecionado via JavaScript')
                            else:
                                # Tentar JavaScript no input
                                driver.execute_script("arguments[0].click();", input_checkbox)
                                sleep(500)
                                if input_checkbox.is_selected():
                                    checkbox_selecionada = True
                                    if log:
                                        print('[INTIMACAO] Checkbox selecionado via JavaScript no input')
                        except Exception as e_js:
                            if log:
                                print(f'[INTIMACAO] JavaScript também falhou: {e_js}')
                                
                else:
                    if log:
                        print('[INTIMACAO] Checkbox não está visível')
                        
            except Exception as e:
                if log:
                    print(f'[INTIMACAO] Erro ao selecionar checkbox: {str(e)}')
                    print('[INTIMACAO] Tentando seletor alternativo...')
                
                # Tentativa alternativa: qualquer checkbox na linha
                try:
                    checkbox_alt = linha_com_prazo_30.find_element(By.CSS_SELECTOR, 'mat-checkbox')
                    checkbox_selecionada = safe_click(driver, checkbox_alt, timeout=3, log=log)
                    if log:
                        print(f'[INTIMACAO] Tentativa alternativa: {"sucesso" if checkbox_selecionada else "falhou"}')
                except Exception as e_alt:
                    if log:
                        print(f'[INTIMACAO] Seletor alternativo também falhou: {e_alt}')
            
            if not checkbox_selecionada:
                if log:
                    print('[INTIMACAO] Falha ao selecionar checkbox')
                    print('[INTIMACAO] Fechando modal e prosseguindo')
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                except Exception:
                    pass
                return True
            
            if log:
                print('[INTIMACAO] Checkbox selecionado com sucesso')
            
            # 6. Clicar no botão Fechar Expedientes
            try:
                modal_expedientes = driver.find_element(By.CSS_SELECTOR, modal_selector)
                btn_fechar_clicked = False
                botoes = modal_expedientes.find_elements(By.CSS_SELECTOR, 'button[aria-label="Fechar Expedientes"]')
                for btn in botoes:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_fechar_clicked = safe_click(driver, btn, timeout=5, log=log)
                        if btn_fechar_clicked:
                            break
                
                if not btn_fechar_clicked:
                    if log:
                        print('[INTIMACAO] Falha ao clicar no botão Fechar Expedientes')
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    except Exception:
                        pass
                    return True
                
                if log:
                    print('[INTIMACAO] Botão Fechar Expedientes clicado')
                
                sleep(500)
                
                # 7. Modal de confirmação
                modal_confirm_selector = 'mat-dialog-container[role="dialog"]'
                modal_confirm = wait_for_visible(driver, modal_confirm_selector, timeout=5)
                if not modal_confirm:
                    if log:
                        print('[INTIMACAO] Modal de confirmação não encontrado, continuando mesmo assim')
                    return True
                
                sleep(500)
                if log:
                    print('[INTIMACAO] Tentando confirmar com tecla ESPAÇO...')
                
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
                sleep(300)
                
                if log:
                    print('[INTIMACAO] Confirmação via ESPAÇO enviada com sucesso')
                
                return True
                
            except Exception as e:
                if log:
                    print(f'[INTIMACAO] Erro ao fechar expedientes: {str(e)}')
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                except Exception:
                    pass
                return True
                
        except Exception as e:
            if log:
                print(f'[INTIMACAO] Erro ao processar expedientes: {str(e)}')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
            return True
            
    except Exception as e:
        if log:
            print(f'[INTIMACAO] Erro geral: {str(e)}')
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
        return True

def retirar_sigilo(elemento):
    try:
        btn_sigilo = elemento.find_element(By.CSS_SELECTOR, "pje-doc-sigiloso span button i.fa-wpexplorer")
        
        # Verifica se o ícone está vermelho (com sigilo ativo) através da classe tl-sigiloso
        if "tl-sigiloso" in btn_sigilo.get_attribute("class"):
            btn_sigilo.click()
            time.sleep(1)
            print("[SIGILO] Clique para retirar sigilo realizado (ícone estava vermelho).")
        else:
            print("[SIGILO] Ícone está azul (sem sigilo ativo). Não é necessário clicar.")
    except Exception as e:
        print("[SIGILO] Erro ao retirar sigilo (pode já estar sem sigilo):", e)

# Unifica anexos Argos e SISBAJUD

def tratar_anexos_argos(driver, documentos_sequenciais, log=True):
    # Process attachments: set confidentiality and visibility for infojud, doi, irpf, dimob and extract SISBAJUD result
    if log:
        print('[ARGOS][ANEXOS] Processing attachments...')
    if not documentos_sequenciais:
        if log:
            print('[ARGOS][ANEXOS][ERROR] No sequential document to process attachments.')
        return None
    doc = documentos_sequenciais[0]
    btn_anexos = doc.find_elements(By.CSS_SELECTOR, "pje-timeline-anexos > div > div")
    if btn_anexos:
        safe_click(driver, btn_anexos[0])
        time.sleep(2)    
    anexos = driver.find_elements(By.CSS_SELECTOR, ".tl-item-anexo")
   
    tem_anexos = len(anexos) > 0  # Nova variável para indicar se há anexos
    if not anexos:
        if log:
            print('[ARGOS][ANEXOS] ❌ Nenhum anexo encontrado no documento')
    else:
        if log:
            print(f'[ARGOS][ANEXOS] ✅ Encontrados {len(anexos)} anexos para processamento')
    
    import re
    # Lista de tipos que devem receber tratamento de sigilo (inicializa antes para manter variáveis disponíveis)
    sigilo_types = ["infojud", "doi", "irpf", "ir2022", "ir2023", "ir2024", "dimob", "ecac", "efinanceira", "e-financeira", "DEC9"]
    found_sigilo = {k: False for k in sigilo_types}
    sigilo_anexos = {k: "nao" for k in sigilo_types}
    any_sigilo = False

    # === NOVA ORDEM: PRIMEIRO, PROCESSAR SISBAJUD (com a certidão já ativada) ===
    if log:
        print('[ARGOS][ANEXOS] === FASE SISBAJUD (moved earlier) ===')

    # Antes de extrair o PDF, ativar o documento correto para SISBAJUD
    try:
        documento_sisbajud = None
        for anexo in anexos:
            texto_anexo = anexo.text.strip()
            if "Certidão de devolução de ordem de pesquisa patrimonial" in texto_anexo:
                documento_sisbajud = anexo
                break

        if documento_sisbajud:
            if log:
                print('[ARGOS][ANEXOS][SISBAJUD] Ativando documento de certidão de devolução...')
            safe_click(driver, documento_sisbajud)
            sleep(1000)
        else:
            if log:
                print('[ARGOS][ANEXOS][SISBAJUD][AVISO] Documento de certidão de devolução não encontrado')
    except Exception as e:
        if log:
            print(f'[ARGOS][ANEXOS][SISBAJUD][ERRO] Erro ao ativar documento: {e}')

    # Extract PDF text para SISBAJUD
    from Fix import extrair_pdf
    texto_pdf = extrair_pdf(driver, log=log)
    executados = []
    resultado_sisbajud = None
    regra_aplicada = None
    if texto_pdf:
        paginas = texto_pdf.split('\f') if '\f' in texto_pdf else [texto_pdf]
        pagina1 = paginas[0] if paginas else texto_pdf
        lines = pagina1.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^[0-9]+\.', line):
                nome = line.split('.', 1)[1].strip()
                documento = ''
                j = i + 1
                while j < len(lines):
                    doc_line = lines[j].strip()
                    if doc_line.startswith('CPF') or doc_line.startswith('CNPJ'):
                        documento = doc_line.split(':', 1)[-1].strip()
                        break
                    if re.match(r'^[0-9]+\.', doc_line):
                        break
                    j += 1
                executados.append({'nome': nome, 'documento': documento})
            i += 1
        if len(paginas) >= 3:
            pagina3 = paginas[2]
            lines3 = pagina3.splitlines()
            sisbajud_idx = -1
            for idx, line in enumerate(lines3):
                if 'sisbajud' in line.lower():
                    sisbajud_idx = idx
                    break
            if sisbajud_idx != -1:
                trecho_log = lines3[sisbajud_idx:sisbajud_idx+8]
                if log:
                    print('[SISBAJUD][DEBUG] Lines after SISBAJUD marker:')
                    for k, l in enumerate(trecho_log):
                        print(f'  [{sisbajud_idx+k}] {repr(l)}')
                regra_aplicada = None
                for offset in range(1, 7):
                    if sisbajud_idx+offset >= len(lines3):
                        break
                    result_line = lines3[sisbajud_idx+offset].strip().lower()
                    if not result_line:
                        continue
                    if log:
                        print(f'[SISBAJUD][DEBUG] Checking line after determinações normativas e legais: {repr(result_line)}')
                    if 'negativo' in result_line:
                        resultado_sisbajud = 'negativo'
                        regra_aplicada = 'linha contém "negativo"'
                        break
                    elif 'positivo' in result_line:
                        resultado_sisbajud = 'positivo'
                        regra_aplicada = 'linha contém "positivo"'
                        break
                    else:
                        valor = result_line.replace('r$', '').replace(' ', '').replace('.', '').replace(',', '.').replace('-', '')
                        try:
                            value = float(''.join([c for c in valor if c.isdigit() or c == '.']))
                            if value == 0:
                                resultado_sisbajud = 'negativo'
                                regra_aplicada = 'valor numérico == 0'
                            else:
                                resultado_sisbajud = 'positivo'
                                regra_aplicada = 'valor numérico > 0'
                            break
                        except Exception:
                            continue
                if not resultado_sisbajud:
                    resultado_sisbajud = 'positivo'
                    regra_aplicada = 'SISBAJUD marker not found, default positivo'
            else:
                resultado_sisbajud = 'positivo'
                regra_aplicada = 'SISBAJUD marker not found, default positivo'
        else:
            resultado_sisbajud = 'positivo'
            regra_aplicada = 'page 3 not found, default positivo'
        resultado_sisbajud, regra_aplicada = extract_sisbajud_result_from_text(texto_pdf, log=log)

    if log:
        print(f'[ARGOS][ANEXOS] SISBAJUD result: {resultado_sisbajud}')
        print(f'[ARGOS][ANEXOS] SISBAJUD rule applied: {regra_aplicada}')

    # === SEGUINTE: PRIMEIRA FASE ORIGINAL - Processar anexos que devem ter sigilo ===
    if log:
        print('[ARGOS][ANEXOS] === FASE SIGILOSOS (moved after SISBAJUD) ===')

    for anexo in anexos:
        texto_anexo = anexo.text.strip().lower()
        tipo_anexo_encontrado = None

        # Verifica se é um anexo especial (apenas os da lista sigilo_types)
        for k in sigilo_types:
            if k == "DEC9":
                # Detecta padrão DEC seguido de 9 dígitos, sem espaços
                if re.search(r"dec\d{9}", texto_anexo):
                    found_sigilo[k] = True
                    tipo_anexo_encontrado = k
                    break
            elif k in texto_anexo:
                found_sigilo[k] = True
                tipo_anexo_encontrado = k
                break

        # Se encontrou um tipo que deve ter sigilo, processa normalmente
        if tipo_anexo_encontrado:
            if log:
                print(f'[ARGOS][ANEXOS] Processando anexo sigiloso: {texto_anexo}')

            # Para anexos especiais: Lógica inteligente de sigilo
            btn_sigilo = anexo.find_elements(By.CSS_SELECTOR, "i.fa-wpexplorer")
            sigilo_foi_aplicado = False
            ja_tem_sigilo = False

            if btn_sigilo:
                classes_sigilo = btn_sigilo[0].get_attribute("class")
                if "tl-nao-sigiloso" in classes_sigilo:
                    # Ícone azul - não tem sigilo, precisa aplicar
                    if log:
                        print(f'[ARGOS][ANEXOS] Ícone azul detectado, aplicando sigilo para: {texto_anexo}')
                    safe_click(driver, btn_sigilo[0])
                    time.sleep(1)
                    sigilo_anexos[k] = "sim"
                    sigilo_foi_aplicado = True
                    if log:
                        print(f'[ARGOS][ANEXOS] ✅ Sigilo aplicado para: {texto_anexo}')
                elif "tl-sigiloso" in classes_sigilo:
                    # Ícone vermelho - já tem sigilo
                    ja_tem_sigilo = True
                    sigilo_anexos[k] = "sim"
                    if log:
                        print(f'[ARGOS][ANEXOS] ✅ Sigilo já existia (ícone vermelho) para: {texto_anexo}')
                else:
                    # Estado indefinido
                    sigilo_anexos[k] = "indefinido"
                    if log:
                        print(f'[ARGOS][ANEXOS] ⚠️ Estado de sigilo indefinido para: {texto_anexo} (classes: {classes_sigilo})')
            else:
                sigilo_anexos[k] = "nao"
                if log:
                    print(f'[ARGOS][ANEXOS] ❌ Botão de sigilo não encontrado para: {texto_anexo}')

            # Clique de visibilidade: buscar o <button> correto pelo <i> filho
            try:
                if log:
                    print(f'[ARGOS][ANEXOS] Processando visibilidade para: {texto_anexo}')

                # LÓGICA CORRIGIDA: Diferencia entre sigilo recém-aplicado e sigilo já existente
                if sigilo_foi_aplicado:
                    # Sigilo foi aplicado agora - aguardar ícone + aparecer
                    if log:
                        print(f'[ARGOS][ANEXOS] Aguardando ícone + aparecer após aplicação do sigilo...')

                    # Aguarda o ícone + aparecer com timeout
                    btn_visibilidade = None
                    for tentativa_espera in range(15):  # 15 tentativas x 0.8s = 12s timeout
                        try:
                            icons = anexo.find_elements(By.CSS_SELECTOR, "i.fas.fa-plus.tl-sigiloso")
                            if icons:
                                icon_classes = icons[0].get_attribute("class")
                                if "fa-plus" in icon_classes and "tl-sigiloso" in icon_classes:
                                    btn_candidate = icons[0].find_element(By.XPATH, "./ancestor::button[1]")
                                    if btn_candidate.is_displayed() and btn_candidate.is_enabled():
                                        btn_visibilidade = btn_candidate
                                        if log:
                                            print(f'[ARGOS][ANEXOS] ✅ Ícone + validado após {tentativa_espera + 1} tentativas')
                                        break
                            sleep(800)  # Aguarda 0.8s antes da próxima tentativa
                        except Exception as e_espera:
                            if log and tentativa_espera < 3:
                                print(f'[ARGOS][ANEXOS][DEBUG] Tentativa {tentativa_espera + 1} falhou: {e_espera}')
                            sleep(800)

                    if not btn_visibilidade:
                        if log:
                            print(f'[ARGOS][ANEXOS][ERRO] Ícone + não apareceu após aplicação do sigilo para: {texto_anexo}')
                        continue

                elif ja_tem_sigilo:
                    # Sigilo já existia - buscar diretamente pelo ícone +
                    if log:
                        print(f'[ARGOS][ANEXOS] Sigilo já existia, buscando ícone + diretamente...')

                    btn_visibilidade = None
                    icons = anexo.find_elements(By.CSS_SELECTOR, "i.fas.fa-plus.tl-sigiloso")
                    if icons:
                        icon_classes = icons[0].get_attribute("class")
                        if "fa-plus" in icon_classes and "tl-sigiloso" in icon_classes:
                            btn_candidate = icons[0].find_element(By.XPATH, "./ancestor::button[1]")
                            if btn_candidate.is_displayed() and btn_candidate.is_enabled():
                                btn_visibilidade = btn_candidate
                                if log:
                                    print(f'[ARGOS][ANEXOS] ✅ Ícone + encontrado diretamente (sigilo pré-existente)')
                            else:
                                if log:
                                    print(f'[ARGOS][ANEXOS][AVISO] Ícone + encontrado mas botão não clicável')
                        else:
                            if log:
                                print(f'[ARGOS][ANEXOS][AVISO] Ícone encontrado mas classes incorretas: {icon_classes}')
                    else:
                        if log:
                            print(f'[ARGOS][ANEXOS][ERRO] Ícone + não encontrado mesmo com sigilo pré-existente')
                        continue
                else:
                    # Sem sigilo aplicado ou pré-existente - pular processamento de visibilidade
                    if log:
                        print(f'[ARGOS][ANEXOS] Sem sigilo para: {texto_anexo}, pulando processamento de visibilidade')
                    continue

                if btn_visibilidade:
                    if log:
                        print(f'[ARGOS][ANEXOS] Clicando no botão de visibilidade para: {texto_anexo}')

                    # ✅ FLUXO SIMPLIFICADO: Clique direto via JavaScript no seletor específico
                    try:
                        # Scroll para garantir visibilidade
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_visibilidade)
                        sleep(300)

                        # Clique direto via JavaScript no ícone +
                        driver.execute_script("arguments[0].click();", btn_visibilidade)

                        if log:
                            print(f'[ARGOS][ANEXOS][DEBUG] ✅ Clique realizado via JavaScript')

                    except Exception as e_click:
                        if log:
                            print(f'[ARGOS][ANEXOS][ERRO] ❌ Falha no clique: {e_click}')
                            print(f'[ARGOS][ANEXOS][ERRO] Pulando anexo: {texto_anexo}')
                        continue

                    # ✅ VERIFICAÇÃO ÚNICA DO MODAL: Checagem simples da presença
                    modal_apareceu = False
                    modal_visibilidade = None

                    if log:
                        print(f'[ARGOS][ANEXOS][DEBUG] Verificando abertura do modal...')

                    try:
                        # Aguarda um momento para o modal aparecer
                        sleep(1000)

                        # Verifica se o modal está presente e visível
                        modal_visibilidade = driver.find_element(By.CSS_SELECTOR, "pje-doc-visibilidade-sigilo")
                        if modal_visibilidade.is_displayed():
                            modal_apareceu = True
                            if log:
                                print(f'[ARGOS][ANEXOS][DEBUG] ✅ Modal confirmado')
                        else:
                            if log:
                                print(f'[ARGOS][ANEXOS][ERRO] ❌ Modal encontrado mas não visível')

                    except Exception as e_modal:
                        if log:
                            print(f'[ARGOS][ANEXOS][ERRO] ❌ Modal não encontrado: {e_modal}')

                    # ✅ INTERRUPÇÃO IMEDIATA: Se modal não identificado, parar execução
                    if not modal_apareceu:
                        if log:
                            print(f'[ARGOS][ANEXOS][ERRO] ❌ EXECUÇÃO INTERROMPIDA: Modal não identificado após clique')
                            print(f'[ARGOS][ANEXOS][ERRO] Anexo será pulado: {texto_anexo}')
                        continue

                    # ✅ MODAL CONFIRMADO - Prosseguindo com o processamento
                    try:
                        if log:
                            print(f'[ARGOS][ANEXOS][DEBUG] ✅ PROCESSANDO MODAL VALIDADO para: {texto_anexo}')
                            print(f'[ARGOS][ANEXOS][DEBUG] Modal confirmado como correto, iniciando seleção de checkboxes...')

                        # Aguarda modal carregar completamente
                        sleep(800)

                        # DEBUG: Estratégia otimizada para clique no botão "Selecionar Todos"
                        btn_selecionar_todos = None

                        # Busca pelo ícone específico de selecionar todos
                        try:
                            # Busca diretamente pelo ícone fa-check
                            icone_selecionar_todos = modal_visibilidade.find_element(By.CSS_SELECTOR, "i.fa.fa-check")

                            if log:
                                print(f'[ARGOS][ANEXOS] Ícone "Selecionar Todos" encontrado')

                            # Clique no ícone Selecionar Todos
                            driver.execute_script("arguments[0].click();", icone_selecionar_todos)
                            sleep(500)

                            if log:
                                print(f'[ARGOS][ANEXOS] ✅ Ícone "Selecionar Todos" clicado com sucesso')

                        except Exception as e_selecionar:
                            if log:
                                print(f'[ARGOS][ANEXOS][AVISO] Botão "Selecionar Todos" não encontrado, tentando checkboxes individuais: {e_selecionar}')

                            # Fallback: Selecionar checkboxes individualmente
                            checkboxes = modal_visibilidade.find_elements(By.CSS_SELECTOR, "mat-checkbox")
                            if checkboxes:
                                if log:
                                    print(f'[ARGOS][ANEXOS] Encontrados {len(checkboxes)} checkboxes no modal')

                                for i, checkbox in enumerate(checkboxes):
                                    try:
                                        # Verifica se já está selecionado
                                        if checkbox.get_attribute('aria-checked') != 'true':
                                            # Clica no checkbox
                                            driver.execute_script("arguments[0].click();", checkbox)
                                            sleep(200)
                                            if log:
                                                print(f'[ARGOS][ANEXOS] Checkbox {i+1} selecionado')
                                    except Exception as e_check:
                                        if log:
                                            print(f'[ARGOS][ANEXOS] Erro ao selecionar checkbox {i+1}: {e_check}')

                        # Busca e clica no botão Salvar
                        btn_salvar = None
                        try:
                            # Busca pelo botão Salvar específico do modal (baseado no HTML fornecido)
                            btn_salvar = modal_visibilidade.find_element(By.CSS_SELECTOR, "button[color='primary'].mat-focus-indicator.mat-button.mat-button-base.mat-primary")

                            if log:
                                print(f'[ARGOS][ANEXOS] Botão Salvar encontrado')

                            # Clique no botão Salvar
                            driver.execute_script("arguments[0].click();", btn_salvar)
                            sleep(1000)  # Aguarda processamento

                            if log:
                                print(f'[ARGOS][ANEXOS][DEBUG] ✅ SUCESSO COMPLETO: Visibilidade processada para: {texto_anexo}')
                                print(f'[ARGOS][ANEXOS][DEBUG] Anexo foi processado corretamente do início ao fim')

                        except Exception as e_salvar:
                            if log:
                                print(f'[ARGOS][ANEXOS][ERRO] ❌ FALHA: Botão Salvar não encontrado: {e_salvar}')
                                print(f'[ARGOS][ANEXOS][ERRO] Anexo será considerado como não processado: {texto_anexo}')

                            # Fallback: Tenta seletor mais simples
                            try:
                                btn_salvar = modal_visibilidade.find_element(By.CSS_SELECTOR, "button[color='primary']")
                                driver.execute_script("arguments[0].click();", btn_salvar)
                                sleep(1000)
                                if log:
                                    print(f'[ARGOS][ANEXOS][DEBUG] ✅ SUCESSO: Botão Salvar clicado via fallback para: {texto_anexo}')
                            except Exception as e_fallback:
                                if log:
                                    print(f'[ARGOS][ANEXOS][ERRO] ❌ FALHA CRÍTICA: Fallback também falhou: {e_fallback}')
                                    print(f'[ARGOS][ANEXOS][ERRO] Anexo não foi processado: {texto_anexo}')
                                # Fechar modal com ESC
                                try:
                                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                    if log:
                                        print(f'[ARGOS][ANEXOS][DEBUG] Modal fechado com ESC após falha')
                                except Exception:
                                    pass
                                # Continua para próximo anexo sem marcar como processado
                                continue

                    except Exception as e_modal:
                        if log:
                            print(f'[ARGOS][ANEXOS][ERRO] ❌ FALHA CRÍTICA: Erro ao tratar modal de visibilidade: {e_modal}')
                            print(f'[ARGOS][ANEXOS][ERRO] Anexo não será processado: {texto_anexo}')
                        # Fechar modal com ESC em caso de erro
                        try:
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            if log:
                                print(f'[ARGOS][ANEXOS][DEBUG] Modal fechado com ESC após erro')
                        except:
                            pass
                        # Continua para próximo anexo sem marcar como processado
                        continue

                else:
                    if log:
                        print(f'[ARGOS][ANEXOS][ERRO] ❌ FALHA: Botão de visibilidade não encontrado para: {texto_anexo}')
                        print(f'[ARGOS][ANEXOS][ERRO] Anexo será pulado')
                    # Continua para próximo anexo
                    continue

            except Exception as e_geral:
                if log:
                    print(f'[ARGOS][ANEXOS][ERRO] ❌ FALHA GERAL: Erro ao processar visibilidade: {e_geral}')
                    print(f'[ARGOS][ANEXOS][ERRO] Anexo não processado: {texto_anexo}')
                # Fechar qualquer modal aberto
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    if log:
                        print(f'[ARGOS][ANEXOS][DEBUG] Modal fechado com ESC após erro geral')
                except:
                    pass
                # Continua para próximo anexo sem marcar como processado
                continue

            # Marca que encontrou anexo especial processado com sucesso
            any_sigilo = True
            break

    # === TERCEIRA FASE: Processar SERASA e CNIB (mantida após sigilosos) ===

    # Variáveis para armazenar os dados extraídos
    serasa_data = None
    cnib_data = None

    if log:
        print('[ARGOS][ANEXOS] === FASE SERASA/CNIB ===')

    # --- Extração específica para SERASA e CNIB ---
    anexos_serasa = []
    anexos_cnib = []
    for anexo in anexos:
        texto_base = anexo.text.strip().lower()
        if "serasa" in texto_base:
            anexos_serasa.append(anexo)
        if "cnib" in texto_base:
            anexos_cnib.append(anexo)

    # Processa SERASA
    for anexo_serasa in anexos_serasa:
        try:
            if log:
                print(f'[ARGOS][ANEXOS][SERASA] Processando anexo SERASA...')

            # Clica no anexo SERASA para ativá-lo
            safe_click(driver, anexo_serasa)
            sleep(1500)  # Aguarda o documento carregar

            # Usa a função extrair_pdf do Fix.py para obter o conteúdo diretamente
            texto_pdf = extrair_pdf(driver, log=log)

            if texto_pdf:
                if log:
                    print(f'[ARGOS][ANEXOS][SERASA] Texto extraído com extrair_pdf:\n{texto_pdf[:500]}...')

                # Aplica regra de extração para SERASA
                padroes_serasa = [
                    r'APJUR 2025\d{14}',    # Padrão original: APJUR 20250821085112786
                    r'APJUR \d{14}',        # Padrão sem ano: APJUR 12345678901234
                    r'APJUR\d{14}',         # Padrão sem espaço: APJUR12345678901234
                    r'APJUR \d{12}',        # Padrão com 12 dígitos: APJUR 123456789012
                ]

                for padrao in padroes_serasa:
                    match = re.search(padrao, texto_pdf)
                    if match:
                        serasa_data = match.group(0)
                        if log:
                            print(f'[ARGOS][ANEXOS][SERASA] Dados extraídos: {serasa_data}')
                        break

                if not serasa_data and log:
                    print(f'[ARGOS][ANEXOS][SERASA] Nenhum padrão APJUR encontrado')
            else:
                if log:
                    print(f'[ARGOS][ANEXOS][SERASA] Falha ao extrair texto com extrair_pdf')

            # Fecha o documento (se necessário)
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                sleep(500)
            except:
                pass
        except Exception as e:
            if log:
                print(f'[ARGOS][ANEXOS][SERASA][ERRO] Falha ao extrair SERASA: {e}')
            # Tenta fechar com ESC
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                sleep(500)
            except:
                pass

    # Processa CNIB
    for anexo_cnib in anexos_cnib:
        try:
            if log:
                print(f'[ARGOS][ANEXOS][CNIB] Processando anexo CNIB...')

            # Clica no anexo CNIB para ativá-lo
            safe_click(driver, anexo_cnib)
            sleep(1500)  # Aguarda o documento carregar

            # Usa a função extrair_pdf do Fix.py para obter o conteúdo diretamente
            texto_pdf = extrair_pdf(driver, log=log)

            if texto_pdf:
                if log:
                    print(f'[ARGOS][ANEXOS][CNIB] Texto extraído com extrair_pdf:\n{texto_pdf[:500]}...')

                # Aplica regra de extração para CNIB
                linhas = texto_pdf.splitlines()
                protocolo_encontrado = False

                # Tenta vários padrões possíveis para o protocolo
                padroes_protocolo = [
                    r'\d{6}\.\d{4}\.\d{8}-\d+-\d+',  # Padrão original: 202508.2020.04204441-1A-898
                    r'\d{6}\.\d{4}\.\d{8}-\d+',      # Padrão alternativo: 202508.2020.04204441-1
                    r'\d{6}\.\d{4}\.\d{8}',           # Padrão simplificado: 202508.2020.04204441
                    r'[A-Z]{2}\d{14}',                # Padrão tipo CNIB: AB12345678901234
                    r'\d{20}',                        # Padrão numérico: 12345678901234567890
                ]

                for i, linha in enumerate(linhas):
                    if 'protocolo' in linha.lower():
                        if log:
                            print(f'[ARGOS][ANEXOS][CNIB] Linha com "protocolo" encontrada: {linha}')
                        protocolo_encontrado = True
                        continue

                    if protocolo_encontrado:
                        if log:
                            print(f'[ARGOS][ANEXOS][CNIB] Verificando linha após protocolo: {linha}')

                        # Tenta encontrar algum dos padrões na linha atual
                        for padrao in padroes_protocolo:
                            match = re.search(padrao, linha)
                            if match:
                                cnib_data = match.group(0)
                                if log:
                                    print(f'[ARGOS][ANEXOS][CNIB] Dados extraídos: {cnib_data}')
                                break

                        if cnib_data:
                            break
                        else:
                            # Se nenhum padrão foi encontrado na linha atual, tenta a próxima
                            if log:
                                print(f'[ARGOS][ANEXOS][CNIB] Nenhum padrão encontrado na linha atual, verificando próxima...')
                            continue

                if not cnib_data and log:
                    print(f'[ARGOS][ANEXOS][CNIB] Padrão de protocolo não encontrado')
            else:
                if log:
                    print(f'[ARGOS][ANEXOS][CNIB] Falha ao extrair texto com extrair_pdf')

            # Fecha o documento (se necessário)
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                sleep(500)
            except:
                pass
        except Exception as e:
            if log:
                print(f'[ARGOS][ANEXOS][CNIB][ERRO] Falha ao extrair CNIB: {e}')
            # Tenta fechar com ESC
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                sleep(500)
            except:
                pass
    
    # Ação C: Registro em Nova Atividade (se encontrou pelo menos um)
    if serasa_data or cnib_data:
        if log:
            print('[ARGOS][ANEXOS] Criando nova atividade para registrar SERASA e/ou CNIB...')
            if serasa_data:
                print(f'[ARGOS][ANEXOS] Dados SERASA a serem registrados: {serasa_data}')
            if cnib_data:
                print(f'[ARGOS][ANEXOS] Dados CNIB a serem registrados: {cnib_data}')
        
        try:
            # Clicar no botão de nova atividade (usando o mesmo seletor de criar_gigs)
            btn_nova_atividade = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'nova-atividade'))
            )
            btn_nova_atividade.click()
            if log:
                print('[ARGOS][ANEXOS] Botão Nova Atividade clicado.')
            
            # Aguardar o modal abrir
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'form'))
            )
            if log:
                print('[ARGOS][ANEXOS] Modal de atividade aberto.')
            
            # Preencher observação
            campo_obs = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'))
            )
            campo_obs.clear()
            
            # Formato: ARGOS:\n(dados serasa)\n(dados cnib)
            observacao = "ARGOS:\n"
            observacao += serasa_data if serasa_data else ""
            observacao += "\n"
            observacao += cnib_data if cnib_data else ""
            
            campo_obs.send_keys(observacao)
            if log:
                print(f'[ARGOS][ANEXOS] Observação preenchida: {observacao}')
            
            # Clicar em Salvar
            btn_salvar = None
            botoes = driver.find_elements(By.CSS_SELECTOR, 'button.mat-raised-button')
            for btn in botoes:
                if btn.is_displayed() and ('Salvar' in btn.text or btn.get_attribute('type') == 'submit'):
                    btn_salvar = btn
                    break
            
            if btn_salvar:
                btn_salvar.click()
                if log:
                    print('[ARGOS][ANEXOS] Botão Salvar clicado.')
                
                # Aguardar confirmação
                time.sleep(2)
                
                # Verificar se houve mensagem de sucesso
                try:
                    success_snackbar = driver.find_element(By.CSS_SELECTOR, 'snack-bar-container.success simple-snack-bar span')
                    if 'salva com sucesso' in success_snackbar.text.lower():
                        if log:
                            print('[ARGOS][ANEXOS] Atividade salva com sucesso.')
                except:
                    if log:
                        print('[ARGOS][ANEXOS] Não foi possível confirmar a mensagem de sucesso, mas o botão foi clicado.')
            else:
                if log:
                    print('[ARGOS][ANEXOS][ERRO] Botão Salvar não encontrado!')
                    
        except Exception as e:
            if log:
                print(f'[ARGOS][ANEXOS][ERRO] Erro ao criar atividade: {e}')
            # Tentar fechar o modal com ESC
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1)
            except:
                pass
    else:
        if log:
            print('[ARGOS][ANEXOS] Nenhum dado de SERASA ou CNIB encontrado para registrar.')
    
    if log:
        print(f'[ARGOS][ANEXOS] Extracted executados (page 1): {executados}')
        print(f'[ARGOS][ANEXOS] Found attachments: {found_sigilo}')
        print(f'[ARGOS][ANEXOS] Total attachments found: {tem_anexos}')
        print(f'[ARGOS][ANEXOS] Will register as sigiloso: {any_sigilo}')
    return {'executados': executados, 'resultado_sisbajud': resultado_sisbajud, 'found_sigilo': found_sigilo, 'sigilo_anexos': sigilo_anexos, 'sigiloso': any_sigilo, 'tem_anexos': tem_anexos}
def fluxo_mandado(driver):
    """
    Percorre a lista de processos e executa o fluxo adequado (Argos ou Outros) para cada mandado.
    """
    def remover_acentos(txt):
        return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    def fluxo_callback(driver):
        try:
            print('\n' + '='*50)
            print('[FLUXO] Iniciando análise do documento...')
            # REMOVIDO: Passo 0 de clique na lupa (fa-search lupa-doc-nao-apreciado)
            # Busca o cabeçalho do documento após o carregamento da página
            try:
                # Aguarda um pouco para a interface se estabilizar
                sleep(2000)
                # Busca o cabeçalho usando as funções do Fix.py
                cabecalho_selector = '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'
                cabecalho = wait_for_visible(driver, cabecalho_selector, timeout=10)
                if not cabecalho:
                    print('[FLUXO][ERRO] Cabeçalho do documento não encontrado após carregamento')
                    return
                texto_doc = cabecalho.text
                if not texto_doc:
                    print('[FLUXO][ERRO] Cabeçalho do documento vazio')
                    return
                print(f'[FLUXO] Documento encontrado: {texto_doc}')
            except Exception as e:
                print(f'[FLUXO][ERRO] Erro ao buscar cabeçalho após carregamento: {e}')
                return
            texto_lower = remover_acentos(texto_doc.lower().strip())
            # Identificação dos fluxos
            if any(remover_acentos(termo) in texto_lower for termo in ['pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa', 'certidao de devolucao']):
                print(f'[ARGOS] Processo em análise: {texto_doc}')
                processar_argos(driver, log=True)  # Ativamos o log para depuração
            elif any(remover_acentos(termo) in texto_lower for termo in ['oficial de justica', 'certidao de oficial', 'certidao de oficial de justica']):
                print(f'[OUTROS] Processo em análise: {texto_doc}')
                fluxo_mandados_outros(driver, log=False)
            else:
                print(f'[AVISO] Documento não identificado: {texto_doc}')
                
        except Exception as e:
            print(f'[ERRO] Falha ao processar mandado: {str(e)}')
        finally:
            # Fechar a aba após o processamento do fluxo (reproduzindo padrão de p2.py)
            all_windows = driver.window_handles
            main_window = all_windows[0]
            current_window = driver.current_window_handle

            if current_window != main_window and len(all_windows) > 1:
                driver.close()
                # Troca para uma aba válida após fechar
                try:
                    if main_window in driver.window_handles:
                        driver.switch_to.window(main_window)
                    elif driver.window_handles:
                        driver.switch_to.window(driver.window_handles[0])
                    else:
                        print("[LIMPEZA][ERRO] Nenhuma aba restante para alternar.")
                except Exception as e:
                    print(f"[LIMPEZA][ERRO] Falha ao alternar para aba válida após fechar: {e}")
                # Testa se a aba está realmente acessível
                from selenium.common.exceptions import NoSuchWindowException
                try:
                    _ = driver.current_url
                except NoSuchWindowException:
                    print("[LIMPEZA][ERRO] Tentou acessar uma aba já fechada.")
            
            print('[FLUXO] Processo concluído, retornando à lista')
    print('[FLUXO] Filtro de mandados devolvidos já garantido na navegação. Iniciando processamento...')
    indexar_e_processar_lista(driver, fluxo_callback)

def buscar_documentos_sequenciais(driver, log=True):
    """
    Busca documentos sequenciais na timeline do processo.
    """
    try:
        documentos_alvo = [
            "Certidão de devolução",
            "Certidão de expedição", 
            "Planilha",
            "Intimação",
            "Decisão"
        ]
        
        if log:
            print(f'[DOCS_SEQUENCIAIS] Buscando documentos alvos: {documentos_alvo}')
            
        resultados = []
        
        # Espera documentos carregarem na timeline
        selector = ".tl-data, li.tl-item-container"
        sleep(2000)  # Pausa para garantir carregamento da página
        
        # Tenta primeiro usar wait para garantir que algum elemento existe
        primeiro_elemento = wait(driver, selector, timeout=10)
        
        if not primeiro_elemento:
            if log:
                print('[DOCS_SEQUENCIAIS][ERRO] Nenhum documento encontrado na timeline')
            return []
            
        elementos = driver.find_elements(By.CSS_SELECTOR, selector)
        
        if log:
            print(f'[DOCS_SEQUENCIAIS] Total de elementos encontrados na timeline: {len(elementos)}')
        
        indice_doc_atual = 0
        for elemento in elementos:
            if indice_doc_atual >= len(documentos_alvo):
                break
                
            texto_item = elemento.text.strip().lower()
            documento_atual = documentos_alvo[indice_doc_atual]
            
            if documento_atual.lower() in texto_item:
                resultados.append(elemento)
                if log:
                    print(f'[DOCS_SEQUENCIAIS] Encontrado documento: "{documento_atual}" - {texto_item[:50]}...')
                indice_doc_atual += 1
                
        if log:
            print(f'[DOCS_SEQUENCIAIS] Total de documentos alvos encontrados: {len(resultados)}')
            
        return resultados
    except Exception as e:
        if log:
            print(f'[DOCS_SEQUENCIAIS][ERRO] Falha ao buscar documentos: {str(e)}')
        return []

def processar_argos(driver, log=False):
    """
    Processa fluxo Argos com lógica de busca de documentos.
    """
    try:
        print('[ARGOS][INICIO] Iniciando processamento do fluxo Argos')
        # 0. Fechar intimação
        print('[ARGOS] Chamando função fechar_intimacao...')
        fechar_intimacao(driver, log=log)
        print('[ARGOS] Fechamento de intimação concluído')
        # 1. Buscar documentos sequenciais
        print('[ARGOS] Buscando documentos sequenciais...')
        documentos_sequenciais = buscar_documentos_sequenciais(driver)
        if documentos_sequenciais:
            print(f'[ARGOS] Encontrados {len(documentos_sequenciais)} documentos sequenciais')
        else:
            print('[ARGOS][ALERTA] Nenhum documento sequencial encontrado')
        # 1. Retirar sigilo de certidão, ordem de pesquisa, planilha, intimação, decisão
        tipos_sigilo = ['certidão', 'certidao', 'ordem de pesquisa', 'planilha', 'intimação', 'intimacao', 'decisão', 'decisao']
        for doc in documentos_sequenciais or []:
            texto = doc.text.strip().lower()
            if any(tp in texto for tp in tipos_sigilo):
                try:
                    retirar_sigilo(doc)
                except Exception:
                    pass          # 2. Processar anexos
        print('[ARGOS] Tratando anexos...')
        anexos_info = tratar_anexos_argos(driver, documentos_sequenciais, log=log) if documentos_sequenciais else None
        
        # Nova regra: se nenhum anexo for localizado, executar diretamente ato_meios
        # Verificamos se anexos_info é None OU se não há anexos de fato (verificando se encontrou anexos gerais)
        tem_anexos = False
        if anexos_info:
            # Verifica se há informação sobre anexos encontrados
            tem_anexos = anexos_info.get('tem_anexos', False)
        
        if anexos_info is None or not tem_anexos:
            print('[ARGOS][NOVA_REGRA] Nenhum anexo encontrado - executando ato_meios diretamente')
            if log:
                print(f'[ARGOS][DEBUG] anexos_info: {anexos_info}')
                print(f'[ARGOS][DEBUG] tem_anexos: {tem_anexos}')
            ato_meios(driver, debug=log)
            return True  # Retorna após executar ato_meios
        
        if anexos_info:
            resultado_sisbajud = anexos_info.get('resultado_sisbajud', None)
            sigilo_anexos = anexos_info.get('sigilo_anexos', {})
            print(f'[ARGOS] Anexos analisados com sucesso: SISBAJUD={resultado_sisbajud}')
        else:
            resultado_sisbajud = None
            sigilo_anexos = {}
            print('[ARGOS][ALERTA] Nenhuma informação de anexo obtida')

        print(f'[ARGOS] Resultado SISBAJUD: {resultado_sisbajud}')
        print(f'[ARGOS] Sigilo anexos: {sigilo_anexos}')

        # 4. Buscar documento relevante (nova lógica antes da planilha)
        print('[ARGOS] Buscando documento relevante...')
        resultado_documento = buscar_documento_argos(driver, log=True)  # Forçando log=True para depuração
        
        # Verifica se o resultado é válido antes de desempacotar (flexível)
        if not resultado_documento:
            print(f'[ARGOS][ERRO] Nenhum resultado retornado de buscar_documento_argos')
            return False
            
        try:
            if isinstance(resultado_documento, tuple):
                if len(resultado_documento) >= 2:
                    documento_texto, documento_tipo = resultado_documento[0], resultado_documento[1]
                elif len(resultado_documento) == 1:
                    documento_texto, documento_tipo = resultado_documento[0], 'documento'
                else:
                    print(f'[ARGOS][ERRO] Tupla vazia retornada')
                    return False
            elif isinstance(resultado_documento, str):
                documento_texto, documento_tipo = resultado_documento, 'documento'
            else:
                print(f'[ARGOS][ERRO] Tipo de resultado inesperado: {type(resultado_documento)}')
                return False
        except Exception as e_unpack:
            print(f'[ARGOS][ERRO] Erro ao processar resultado: {e_unpack}')
            return False
        
        if documento_texto and documento_tipo:
            print(f'[ARGOS] Documento encontrado: tipo={documento_tipo}')
            print(f'[ARGOS] Trechos do documento: {documento_texto[:100]}...')
            
            # 5. Aplicar regras Argos conforme documento e anexos
            print('[ARGOS] Aplicando regras Argos...')
            aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, documento_tipo, documento_texto, debug=True)  # Forçando debug=True para depuração
            
            print('[ARGOS] Documento processado e regras aplicadas.')
            return True  # Indicando sucesso
        else:
            print('[ARGOS][ERRO] Nenhum documento relevante encontrado, fluxo Argos não foi aplicado.')
            return False

        if log:
            print('[ARGOS] Processamento m1 concluído com nova regra de busca.')

    except Exception as e:
        if log:
            print(f'[ARGOS][ERRO] Falha no processamento: {e}')
        raise

def buscar_documento_argos(driver, log=True):
    """Busca documentos relevantes na timeline do Argos, priorizando decisões/despachos anteriores à Planilha de Atualização de Cálculos."""
    try:
        print('[ARGOS][DOC] Iniciando busca de documento relevante...')
        
        # Aguarda a timeline carregar (aguarda pelo menos um item na timeline)
        timeline_selector = 'li.tl-item-container'
        print('[ARGOS][DOC] Aguardando carregamento da timeline...')
        
        # Usando as novas funções do Fix.py
        timeline_item = wait(driver, timeline_selector, timeout=15)
        
        if not timeline_item:
            print('[ARGOS][DOC][ERRO] Timeline não carregou após 15 segundos de espera')
            return None, None
            
        print('[ARGOS][DOC] Timeline carregada com sucesso')
        
        # Garantimos um tempo extra para carregar completamente a timeline
        sleep(1000)
        
        # Buscamos todos os itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, timeline_selector)
        print(f'[ARGOS][DOC] Encontrados {len(itens)} itens na timeline')
        
        # NOVA REGRA: Busca por decisões/despachos anteriores à Planilha de Atualização de Cálculos
        planilha_index = None
        documentos_antes_planilha = []
        
        # Primeiro, encontra a primeira "Planilha de Atualização de Cálculos" na timeline
        for idx, item in enumerate(itens):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento')
                doc_text = link.text.lower()
                if 'planilha de atualização' in doc_text or 'planilha de atuali' in doc_text:
                    planilha_index = idx
                    if log:
                        print(f'[ARGOS][DEBUG] Planilha de Atualização encontrada no item {idx}: {doc_text}')
                    break
            except Exception:
                continue
        
        # Se encontrou uma planilha, procura por decisões/despachos anteriores a ela
        if planilha_index is not None:
            if log:
                print(f'[ARGOS][DEBUG] Procurando decisões/despachos antes da planilha (itens 0 a {planilha_index-1})...')
            
            for idx in range(planilha_index):
                try:
                    item = itens[idx]
                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    doc_text = link.text.lower()
                    
                    # Verifica se é despacho ou decisão
                    if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                        documentos_antes_planilha.append((idx, item, link, doc_text))
                        if log:
                            print(f'[ARGOS][DEBUG] Item {idx}: documento relevante encontrado antes da planilha: {doc_text}')
                except Exception:
                    continue
            
            # Se encontrou documentos antes da planilha, processa o primeiro
            if documentos_antes_planilha:
                idx, item, link, doc_text = documentos_antes_planilha[0]
                if log:
                    print(f'[ARGOS][DEBUG] Processando primeiro documento antes da planilha: item {idx}')
                  # Clica para ativar o documento usando safe_click
                print(f'[ARGOS][DOC] Tentando abrir documento: {doc_text}')
                # Primeiro rolamos para o elemento para garantir visibilidade
                driver.execute_script('arguments[0].scrollIntoView({block: "center"});', link)
                sleep(500)  # Breve pausa após scroll
                
                # Tentamos o clique seguro
                click_resultado = safe_click(driver, link, log=True)
                
                if not click_resultado:
                    print(f'[ARGOS][DOC][ERRO] Falha ao clicar no documento usando safe_click. Tentando método alternativo.')
                    try:
                        driver.execute_script('arguments[0].click();', link)
                        print(f'[ARGOS][DOC] Clique via JavaScript executado com sucesso')
                    except Exception as e:
                        print(f'[ARGOS][DOC][ERRO] Falha no clique alternativo: {e}')
                
                sleep(1500)  # Esperamos mais tempo para carregar o documento
                print(f'[ARGOS][DOC] Extraindo texto do documento...')
                texto = extrair_documento(driver)
                
                if log:
                    print(f'[ARGOS][DEBUG] TEXTO EXTRAÍDO DO DOCUMENTO (antes da planilha):\n---\n{texto}\n---')
                
                # Determina o tipo do documento
                if 'decisão' in doc_text or 'sentença' in doc_text:
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: documento é decisão/sentença anterior à planilha.')
                    return texto, 'decisao'
                else:
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: documento é despacho anterior à planilha.')
                    return texto, 'despacho'
        
        # FALLBACK: Se não encontrou planilha ou documentos antes dela, usa a lógica original
        # LIMITADO A 4 DESPACHOS/DECISÕES MÁXIMO (não conta outros tipos de documento)
        if log:
            print('[ARGOS][DEBUG] Usando lógica fallback: procurando primeiro despacho/decisão na timeline...')
        
        despachos_decisoes_processados = 0
        max_despachos_decisoes = 4
        
        for idx, item in enumerate(itens):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: texto do link = {doc_text}')
                
                # Verifica se é despacho ou decisão PRIMEIRO
                if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    despachos_decisoes_processados += 1
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: é despacho/decisão ({despachos_decisoes_processados}/{max_despachos_decisoes}), clicando para ativar.')
                    
                    # Clica para ativar o documento usando safe_click (fallback)
                    print(f'[ARGOS][DOC][FALLBACK] Tentando abrir documento: {doc_text}')
                    # Primeiro rolamos para o elemento
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', link)
                    sleep(500)
                    
                    # Tentamos o clique seguro
                    click_resultado = safe_click(driver, link, log=True)
                    
                    if not click_resultado:
                        print(f'[ARGOS][DOC][FALLBACK][ERRO] Falha ao clicar no documento. Tentando método alternativo.')
                        try:
                            driver.execute_script('arguments[0].click();', link)
                            print(f'[ARGOS][DOC][FALLBACK] Clique via JavaScript executado com sucesso')
                        except Exception as e:
                            print(f'[ARGOS][DOC][FALLBACK][ERRO] Falha no clique alternativo: {e}')
                            # Não incrementa o contador se falhou no clique
                            despachos_decisoes_processados -= 1
                            continue  # Tenta próximo documento se falha no clique
                    
                    sleep(1500)  # Esperamos mais tempo para carregar o documento
                    print(f'[ARGOS][DOC][FALLBACK] Extraindo texto do documento...')
                    
                    try:
                        texto = extrair_documento(driver)
                        if log:
                            print(f'[ARGOS][DEBUG] TEXTO EXTRAÍDO DO DOCUMENTO (fallback):\n---\n{texto}\n---')
                        
                        if 'decisão' in doc_text or 'sentença' in doc_text:
                            if log:
                                print(f'[ARGOS][DEBUG] Item {idx}: documento é decisão/sentença (fallback).')
                            return texto, 'decisao'
                        else:
                            if log:
                                print(f'[ARGOS][DEBUG] Item {idx}: documento é despacho (fallback).')
                            return texto, 'despacho'
                    except Exception as e:
                        if log:
                            print(f'[ARGOS][DEBUG] Item {idx}: erro ao extrair texto do documento: {e}')
                        # Não incrementa o contador se falhou na extração
                        despachos_decisoes_processados -= 1
                        continue  # Tenta próximo documento se falha na extração
                        
                    # Limite de 4 despachos/decisões APÓS encontrar um válido
                    if despachos_decisoes_processados >= max_despachos_decisoes:
                        if log:
                            print(f'[ARGOS][DEBUG] Limite de {max_despachos_decisoes} despachos/decisões atingido no fallback, encerrando busca.')
                        break
                else:
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: não é despacho/decisão/sentença/conclusão.')
            except Exception as e:
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: erro ao processar item: {e}')
                continue
        
        if log:
            print(f'[ARGOS] Nenhum documento relevante encontrado após varrer {despachos_decisoes_processados} despachos/decisões (máximo {max_despachos_decisoes}).')
        return None, None
    except Exception as e:
        if log:
            print(f'[ARGOS][ERRO] Falha ao buscar documento: {e}')
            print('[ARGOS][INFO] Tentando fallback...')
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
            for elem in elementos:
                if elem.is_displayed() and not elem.get_attribute('target'):
                    if log:
                        print('[ARGOS][DEBUG] Fallback: clicando em documento visível.')
                    safe_click(driver, elem)
                    time.sleep(1)
                    texto = extrair_documento(driver)
                    if texto:
                        return texto, 'fallback'
        except Exception as e_fb:
            if log:
                print(f'[ARGOS][ERRO] Fallback também falhou: {e_fb}')
        return None, None

def ultimo_mdd(driver, log=True):
    """
    Busca o último mandado na timeline (item com texto começando por 'Mandado' e ícone de gavel) e retorna (nome_autor, elemento_mandado).
    Versão robusta com verificações de conectividade.
    """
    try:
        # Verificação inicial de conexão 
        if not validar_conexao_driver(driver, contexto="MDD_INICIO"):
            if log:
                print('[MDD][ERRO_FATAL] Driver em estado inválido ao buscar mandado')
            return None, None
            
        # Usando wait_for_visible ao invés de find_elements direto para maior robustez
        timeline = wait_for_visible(driver, 'ul.timeline-container', timeout=5)
        if not timeline:
            if log:
                print('[MDD][ERRO] Timeline não encontrada, tentando método direto')
            itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        else:
            itens = timeline.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        
        if not itens:
            if log:
                print('[MDD][ALERTA] Nenhum item encontrado na timeline')
            return None, None
            
        for idx, item in enumerate(itens):
            try:
                # Verificação periódica de conexão durante loop
                if idx % 10 == 0 and idx > 0:  # Verificar a cada 10 itens para não impactar performance
                    if not validar_conexao_driver(driver, contexto=f"MDD_LOOP_{idx}"):
                        if log:
                            print(f'[MDD][ERRO_FATAL] Driver em estado inválido durante loop (item {idx})')
                        return None, None
                        
                # Usa wait com timeout curto para não prejudicar performance
                link = wait(driver, item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])'), timeout=1)
                if not link:
                    continue
                    
                doc_text = link.text.strip().lower()
                if doc_text.startswith('mandado'):
                    # Procura ícone de gavel (fa-gavel)
                   
                    icones = item.find_elements(By.CSS_SELECTOR, 'i.fa-gavel')
                    if not icones:
                        continue  # Não é mandado assinado por oficial
                    # Procura nome do autor próximo ao link ou assinatura
                    nome_autor = None
                    # Tenta encontrar assinatura padrão
                    try:
                        assinatura = item.find_element(By.CSS_SELECTOR, '.assinatura, .autor, .assinante, .nome-assinatura')
                        nome_autor = assinatura.text.strip()
                    except Exception:
                        # Fallback: procura texto logo após o link
                        try:
                            spans = item.find_elements(By.CSS_SELECTOR, 'span')
                            for s in spans:
                                s_text = s.text.strip()
                                if s_text and s_text.lower() != doc_text:
                                    nome_autor = s_text
                                    break
                        except Exception:
                            pass
                    if log:
                        print(f'[MDD][DEBUG] Mandado encontrado: {doc_text} | Autor: {nome_autor}')
                    return nome_autor, item
            except Exception as e:
                if log:
                    print(f'[MDD][DEBUG] Erro ao processar item {idx}: {e}')
                continue
                
        # Verificação final de conexão
        if not validar_conexao_driver(driver, contexto="MDD_FIM"):
            if log:
                print('[MDD][ERRO_FATAL] Driver em estado inválido ao finalizar busca de mandado')
            return None, None
            
        if log:
            print('[MDD][DEBUG] Nenhum mandado encontrado na timeline.')
        return None, None
    except Exception as e:
        if log:
            print(f'[MDD][ERRO] Falha ao buscar último mandado: {e}')
        return None, None

# ====================================================
# BLOCO 2 - FLUXO OUTROS
# ====================================================

def fluxo_mandados_outros(driver, log=True):
    """
    Processa o fluxo de mandados não-Argos (Oficial de Justiça).
    1. Verifica se é certidão de oficial através do cabeçalho
    2. Extrai e analisa o texto da certidão
    3. Verifica padrões de mandado positivo/negativo
    4. Cria GIGS ou executa atos conforme resultado
    """
    if log:
        print('[MANDADOS][OUTROS] Iniciando fluxo Mandado (Outros)')        
    # Primeiro verifica se é certidão de oficial através do cabeçalho
    try:
        # Usa wait_for_visible mais robusto ao invés de find_element direto
        cabecalho = wait_for_visible(driver, ".cabecalho-conteudo .mat-card-title", timeout=5)
        if not cabecalho:
            if log:
                print('[MANDADOS][OUTROS][ALERTA] Cabeçalho não encontrado. Tentando fallback.')
            cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")
            
        titulo_documento = cabecalho.text.lower()
        
        eh_certidao_oficial = any(p in titulo_documento for p in [
            "certidão de oficial",
            "certidão de oficial de justiça"
        ])
        
        if not eh_certidao_oficial:
            if log:
                print(f"[MANDADOS][OUTROS][LOG] Documento '{cabecalho.text}' NÃO é certidão de oficial. Criando GIGS fallback.")
            # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
            
            # Fechamento simples sem verificações excessivas (igual ao ARGOS)
            if log:
                print('[MANDADOS][OUTROS] Fluxo Mandado (Outros) concluído.')
            return
        
        if log:
            print(f"[MANDADOS][OUTROS][LOG] Documento '{cabecalho.text}' é certidão de oficial. Prosseguindo com análise.")            
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro ao verificar cabeçalho: {e}. Criando GIGS fallback.")
        criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
        
        # Fechamento simples sem verificações excessivas (igual ao ARGOS)
        return
    
    def analise_padrao(texto):
        if log:
            print(f"[MANDADOS][OUTROS] Texto extraído para análise:\n{texto}\n---Fim do documento---")
        texto_lower = texto.lower()        
        
        padrao_positivo = any(p in texto_lower for p in [
            "citei", 
            "intimei", 
            "recebeu o mandado", 
            "de tudo ficou ciente"
            "procedi à intimação",
            "procedi à citação",
            "procedi à entrega do mandado",
            "procedi à penhora",
            "penhorei"

        ])
        padrao_negativo = any(p in texto_lower for p in [
            "não localizado",
            "resultado negativo",
            "diligencias negativas",
            "diligência negativa",
            "não encontrado",
            "deixei de citar",
            "deixei de efetuar",
            "deixei de comparacer",
            "deixei de intimar",
            "deixei de penhorar",
            "não logrei êxito",
            "desconhecido no local",
            "não foi possível efetuar"
            "parou de responder",
            "não foi possível localizar",
        ])
        
        padrao_cancelamento_total = any(p in texto_lower for p in [
            "ordem de cancelamento total",
        ])        
        if padrao_cancelamento_total:
            if log:
                print("[MANDADOS][OUTROS][LOG] Ordem de cancelamento total detectada - executando BNDT_apagar e def_arq (atos.py)")
            
            from isolar import BNDT_apagar
            BNDT_apagar(driver)
            
            from atos import def_arq
            def_arq(driver)
            return None
        
        if padrao_positivo:
            if log:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado POSITIVO encontrado no texto.")
            # criar_gigs(driver, dias_uteis=0, observacao='xx positivo', tela='principal')
        elif padrao_negativo:
            if log:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado NEGATIVO encontrado no texto.")                # NOVA REGRA: localizar mandado anterior na timeline, extrair conteúdo e, se contiver 'penhora', chamar ato_meios
                autor_ant, elemento_ant = ultimo_mdd(driver, log=log)
                if elemento_ant:
                    try:
                        link_ant = elemento_ant.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                        # Usar safe_click ao invés de JS direto + click normal
                        safe_click(driver, link_ant)
                        time.sleep(1)
                        
                        texto_mandado_ant = extrair_documento(driver)
                        if texto_mandado_ant and 'penhora' in texto_mandado_ant.lower():
                            if log:
                                print("[MANDADOS][OUTROS][LOG] Mandado anterior contém 'penhora' - chamando ato_meios")
                            ato_meios(driver)
                    except Exception as e:
                        if log:
                            print(f"[MANDADOS][OUTROS][ERRO] Falha ao processar mandado anterior: {e}")                            
            # Verifica se contém "penhora de bens" no texto
            if "penhora de bens" in texto_lower:
                if log:
                    print("[MANDADOS][OUTROS][LOG] Texto contém 'penhora de bens' - chamando ato_meios")
                ato_meios(driver)
            elif "deixei de penhorar" in texto_lower:
                if log:
                    print("[MANDADOS][OUTROS][LOG] Texto contém 'deixei de penhorar' - chamando ato_meios")
                ato_meios(driver)
            else:
                # Busca último mandado na timeline
                autor, elemento = ultimo_mdd(driver, log=log)
                if autor:
                    if 'silas passos' in autor.lower():
                        if log:
                            print("[MANDADOS][OUTROS][LOG] Último mandado assinado por Silas Passos - chamando ato_edital")
                        ato_edital(driver)
                    else:
                        if log:
                            print("[MANDADOS][OUTROS][LOG] Último mandado assinado por outro autor - não faz nada")
                else:
                    if log:
                        print("[MANDADOS][OUTROS][LOG] Não encontrado último mandado na timeline")
                    # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
        else:
            if log:
                print("[MANDADOS][OUTROS][LOG] Mandado sem padrão reconhecido. Criando GIGS fallback.")
            # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')        return None
    
    texto = extrair_documento(driver, regras_analise=analise_padrao)
    if not texto:
        if log:
            print("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return
            
    if log:
        print('[MANDADOS][OUTROS] Fluxo Mandado (Outros) concluído.')

# ====================================================
# BLOCO 3 - MÓDULO DE TESTE
# ====================================================

def fluxo_teste(driver):
    """
    Fluxo de teste isolado que começa pelo cabeçalho do documento ativo.
    """
    try:
        # Espera o cabeçalho do documento ativo
        cabecalho = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-card-title.mat-card-title'))
        )
        texto_cabecalho = cabecalho.text.lower()
        print(f"[INFO] Cabeçalho do documento: {texto_cabecalho}")

        if "pesquisa patrimonial" in texto_cabecalho or "argos" in texto_cabecalho:
            print("[FLUXO] Iniciando fluxo Argos")
            processar_argos(driver)
        elif "oficial de justiça" in texto_cabecalho or "certidão de oficial" in texto_cabecalho:
            print("[FLUXO] Iniciando fluxo Outros")
            fluxo_mandados_outros(driver)
        else:
            print(f"[FLUXO] Tipo de documento não identificado: {texto_cabecalho}")

    except Exception as e:
        print(f"[ERRO] Falha ao identificar o cabeçalho do documento: {e}")

# Função de teste para demonstrar a nova regra de busca de documentos
def testar_regra_argos_planilha():
    """
    Função de teste que demonstra como a nova regra funciona.
    
    NOVA REGRA IMPLEMENTADA:
    1. Procura pela primeira "Planilha de Atualização de Cálculos" na timeline
    2. Busca por decisões/despachos que vêm ANTES dessa planilha
    3. Prioriza o primeiro documento relevante encontrado antes da planilha
    4. Se não encontrar planilha, usa lógica fallback (primeiro despacho/decisão)
    
    BENEFÍCIOS:
    - Melhora a precisão na seleção de documentos relevantes
    - Evita processar documentos que podem ser posteriores aos cálculos
    - Mantém compatibilidade com casos onde não há planilha
    """
    exemplo_timeline = [
        "Item 0: Petição inicial",
        "Item 1: Despacho ordenando perícia",  # <- Este seria selecionado (primeiro antes da planilha)
        "Item 2: Decisão deferindo pedido",    # <- Este seria ignorado (após item  1)
        "Item 3: Planilha de Atualização de Cálculos",  # <- Referência para busca
        "Item 4: Despacho posterior",          # <- Este seria ignorado (após planilha)
        "Item 5: Decisão final"                # <- Este seria ignorado (após planilha)
    ]
    
    print("="*60)
    print("TESTE DA NOVA REGRA ARGOS - BUSCA ANTES DA PLANILHA")
    print("="*60)
    print("Timeline de exemplo:")
    for item in exemplo_timeline:
        print(f"  {item}")
    
    print("\nLógica da nova regra:")
    print("1. Encontra 'Planilha de Atualização de Cálculos' no item 3")
    print("2. Busca decisões/despachos nos itens 0, 1, 2 (antes da planilha)")
    print("3. Seleciona 'Despacho ordenando perícia' (item 1) - primeiro relevante")
    print("4. Ignora itens 4 e 5 por estarem após a planilha")
    
    print("\nFallback (se não houvesse planilha):")
    print("- Selecionaria 'Despacho ordenando perícia' (item 1) - primeiro relevante geral")
    
    print("\nVantagens da nova regra:")
    print("- Foca em documentos anteriores aos cálculos")
    print("- Evita documentos potencialmente desatualizados")
    print("- Mantém compatibilidade com timelines sem planilha")
    print("="*60)

# ====================================================
# MAIN
# ====================================================

def main():
    """
    Função principal que coordena todo o fluxo do programa com controle de sessão.
    1. Setup inicial (driver e limpeza)
    2. Login humanizado
    3. Navegação para a lista de documentos internos
    4. Execução do fluxo automatizado sobre a lista com recuperação de sessão
    """
    # Verifica argumentos da linha de comando para funções utilitárias
    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset":
            resetar_progresso()
            return
        elif sys.argv[1] == "--list":
            listar_processos_executados()
            return
        elif sys.argv[1] == "--status":
            progresso = carregar_progresso()
            print(f"[PROGRESSO][STATUS] {len(progresso.get('processos_executados', []))} processos executados")
            print(f"[PROGRESSO][STATUS] Última atualização: {progresso.get('last_update', 'N/A')}")
            return
    
    # Setup inicial
    driver = setup_driver()
    if not driver:
        return

    # Login process (agora usando login_pc do Fix.py)
    if not login_func(driver):
        # Não fechar o driver imediatamente em caso de falha no login automático.
        # Tentamos um fallback para login manual antes de abortar a execução.
        print('[LOGIN] Login automático falhou. Tentando fallback para login manual...')
        try:
            if login_manual(driver):
                print('[LOGIN] Login manual realizado com sucesso. Continuando execução.')
            else:
                print('[LOGIN] Login manual não realizado. Mantendo driver aberto para inspeção.')
                return
        except Exception as e:
            print(f'[LOGIN][ERRO] Falha ao tentar login manual de fallback: {e}')
            print('[LOGIN] Mantendo driver aberto para inspeção.')
            return

    # Navegação para a lista de documentos internos
    if not navegacao(driver):
        driver.quit()
        return

    # Processa a lista de documentos internos com controle de sessão
    iniciar_fluxo(driver)

    print("[INFO] Processamento concluído. Pressione ENTER para encerrar...")
    input()
    driver.quit()

if __name__ == "__main__":
    main()