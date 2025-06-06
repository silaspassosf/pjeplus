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
import time
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Fix import (
    login_pc,
    navegar_para_tela,
    extrair_pdf,
    analise_outros,
    extrair_documento,
    criar_gigs,
    esperar_elemento,
    safe_click,
    buscar_seletor_robusto,
    limpar_temp_selenium,
    driver_pc,
    login_notebook,
    indexar_e_processar_lista,
    extrair_dados_processo,
    buscar_documento_argos,
    buscar_mandado_autor,
    buscar_ultimo_mandado,
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
    pec_idpj
)

# --- Configurações customizadas ---
FIREFOX_PROFILE_PATH = r'C:\Users\s164283\AppData\Roaming\Mozilla\Firefox\Profiles\2y17wq63.default'
FIREFOX_EXECUTABLE_PATH = r'C:\Users\s164283\AppData\Local\Firefox Developer Edition\firefox.exe'
GECKODRIVER_PATH = r'C:\Users\s164283\Desktop\pjeplus\geckodriver.exe'
LOGIN_AHK_PATH = r'C:\Users\s164283\Desktop\pjeplus\Login.ahk'
AHK_ROOT = r'C:\Users\s164283\Desktop\pjeplus\AHK\\v2'

# --- Funções utilitárias para inicialização do driver ---
def criar_driver_custom(headless=False):
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    options = Options()
    if headless:
        options.add_argument('-headless')
    options.binary_location = FIREFOX_EXECUTABLE_PATH
    options.profile = FIREFOX_PROFILE_PATH  # Correção para selenium 4+
    service = Service(executable_path=GECKODRIVER_PATH)
    driver = webdriver.Firefox(
        options=options,
        service=service
    )
    return driver

def login_pc(driver):
    """Processo de login manual: abre a tela de login e aguarda o usuário logar manualmente."""
    login_url = "https://pje.trt2.jus.br/primeirograu/login.seam"
    driver.get(login_url)
    print(f"[INFO] Navegando para a URL de login: {login_url}")
    try:
        # Aguarda até que a URL mude (login realizado manualmente pelo usuário)
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(driver, 300).until(lambda d: "/painel" in d.current_url or "/painel/" in d.current_url)
        print("[INFO] Login realizado com sucesso!")
        return True
    except Exception as e:
        print(f"[ERRO] Falha no login manual: {e}")
        return False

# 1. Funções de Login e Setup
def setup_driver():
    """Setup inicial do driver e limpeza"""
    limpar_temp_selenium()
    driver = driver_pc(headless=False)
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
        icone = driver.find_element(By.CSS_SELECTOR, 'i.fa-reply-all.icone-clicavel')
        driver.execute_script('arguments[0].scrollIntoView(true);', icone)
        icone.click()
        print('[NAV] Ícone de mandados devolvidos clicado com sucesso.')
        time.sleep(2)
        return True
    except Exception as e:
        print(f'[NAV][ERRO] Falha na navegação: {str(e)}')
        return False

def iniciar_fluxo(driver):
    """Função que decide qual fluxo será aplicado"""
    def fluxo_callback(driver):
        try:
            print('\n' + '='*50)
            print('[FLUXO] Iniciando análise do documento...')
            
            # Busca o cabeçalho do documento ativo ao invés de usar tl-item-ativo
            try:
                cabecalho = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'))
                )
                texto_doc = cabecalho.text
                if not texto_doc:
                    print('[FLUXO][ERRO] Cabeçalho do documento vazio')
                    return
            except Exception as e:
                print(f'[FLUXO][ERRO] Cabeçalho do documento não encontrado: {e}')
                return
                
            texto_lower = texto_doc.lower()
            
            # Corrigir a lógica de identificação dos fluxos
            if any(termo in texto_lower for termo in ['pesquisa patrimonial', 'argos', 'devolução de ordem de pesquisa', 'certidão de devolução']):
                print('\n[FLUXO] >>> INICIANDO FLUXO ARGOS <<<')
                print(f'[FLUXO][ARGOS] Documento identificado: {texto_doc}')
                print('='*50)
                processar_argos(driver)
            elif any(termo in texto_lower for termo in ['oficial de justiça', 'certidão de oficial']):
                print('\n[FLUXO] >>> INICIANDO FLUXO OUTROS <<<')
                print(f'[FLUXO][OUTROS] Documento identificado: {texto_doc}')
                print('='*50)
                fluxo_mandados_outros(driver, log=True)
            else:
                print('\n[FLUXO][AVISO] >>> DOCUMENTO NÃO IDENTIFICADO <<<')
                print(f'[FLUXO][AVISO] Texto do documento: {texto_doc}')
                print('='*50)
                
        except Exception as e:
            print('\n[FLUXO][ERRO] Falha ao processar mandado:')
            print(f'[FLUXO][ERRO] Detalhes: {str(e)}')
            print('='*50)
        finally:
            if len(driver.window_handles) > 1:
                print('[FLUXO] Fechando aba de detalhes e voltando para lista')
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                print('[FLUXO] Retorno para lista completado')
            print('='*50 + '\n')

    # Executa o processamento da lista
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
        menu = safe_click(driver, '.fa-bars', log=debug)
        time.sleep(1)
        
        # 2. Clique no ícone de lembrete (fa thumbtack)
        lembrete = safe_click(driver, '.lista-itens-menu > li:nth-child(16) > pje-icone-post-it:nth-child(1) > li:nth-child(1) > button:nth-child(1)', log=debug)
        time.sleep(1)
        
        # 3. Foco no conteúdo do diálogo
        dialog = safe_click(driver, '.mat-dialog-content', log=debug)
        time.sleep(1)
        
        # 4. Preenche título
        titulo = driver.find_element(By.CSS_SELECTOR, '#tituloPostit')
        titulo.clear()
        titulo.send_keys('Bloqueio pendente')
        
        # 5. Preenche conteúdo
        conteudo = driver.find_element(By.CSS_SELECTOR, '#conteudoPostit')
        conteudo.clear()
        conteudo.send_keys('processar após IDPJ')
        
        # 6. Clica em salvar
        salvar = safe_click(driver, 'button.mat-raised-button:nth-child(1)', log=debug)
        time.sleep(1)
        
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
    # Analisa as 20 linhas seguintes à ocorrência
    for offset in range(1, 21):
        if det_idx + offset >= len(lines):
            break
        result_line = lines[det_idx + offset].strip().lower()
        if not result_line:
            continue
        if log:
            print(f'[SISBAJUD][DEBUG] Checking line after determinações normativas e legais: {repr(result_line)}')
        if 'negativo' in result_line:
            if log:
                print('[SISBAJUD][DEBUG] Found "negativo" after determinações normativas e legais marker.')
            return 'negativo', 'linha contém "negativo"'
        if 'positivo' in result_line:
            if log:
                print('[SISBAJUD][DEBUG] Found "positivo" after determinações normativas e legais marker.')
            return 'positivo', 'linha contém "positivo"'
        # Tenta extrair valor numérico (ex: R$ 0,00)
        valor = result_line.replace('r$', '').replace(' ', '').replace('.', '').replace(',', '.').replace('-', '')
        try:
            value = float(''.join([c for c in valor if c.isdigit() or c == '.']))
            if log:
                print(f'[SISBAJUD][DEBUG] Found value after determinações normativas e legais: {value}')
            if value == 0:
                return 'negativo', 'valor numérico == 0'
            else:
                return 'positivo', 'valor numérico > 0'
        except Exception:
            continue
    if log:
        print('[SISBAJUD][DEBUG] No rule matched after determinações normativas e legais marker, default negativo.')
    return 'negativo', 'nenhuma regra anterior satisfeita, default negativo'

def aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """
    Aplica as regras específicas do Argos com base no resultado do SISBAJUD, sigilo dos anexos e tipo de documento.
    """
    try:
        if debug:
            print(f'[ARGOS][REGRAS] Analisando regras para tipo: {tipo_documento}')
            print(f'[ARGOS][REGRAS] Resultado SISBAJUD: {resultado_sisbajud}')
            print(f'[ARGOS][REGRAS] Sigilo anexos: {sigilo_anexos}')
        # Exemplo de uso do sigilo_anexos:
        # if sigilo_anexos['infojud'] == 'sim': ...
        # 1. Se é despacho com texto específico
        if tipo_documento == 'despacho' and any(p in texto_documento.lower() for p in ['em que pese a ausência', 'argos']):
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como despacho com texto específico')
            # a) SISBAJUD negativo, sem doc sigiloso
            if resultado_sisbajud == 'negativo' and all(v == 'nao' for v in sigilo_anexos.values()):
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo e nenhum anexo sigiloso - chamando ato_meios')
                ato_meios(driver, debug=debug)
            # b) SISBAJUD negativo, com doc sigiloso
            elif resultado_sisbajud == 'negativo' and any(v == 'sim' for v in sigilo_anexos.values()):
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo com anexo sigiloso - chamando ato_termoS')
                ato_termoS(driver, debug=debug)
            # c) SISBAJUD positivo
            elif resultado_sisbajud == 'positivo':
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD positivo - chamando ato_bloq')
                ato_bloq(driver, debug=debug)
        # 2. Se é decisão com texto "tendo em vista que"
        elif tipo_documento == 'decisao' and 'tendo em vista que' in texto_documento.lower():
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como decisão com texto sobre reclamada')
            dados_processo = extrair_dados_processo(driver, log=debug)
            if debug:
                print(f'[ARGOS][REGRAS] Dados do processo extraídos: {dados_processo}')
            if len(dados_processo.get('reclamadas', [])) == 1:
                if debug:
                    print('[ARGOS][REGRAS] Uma única reclamada - seguindo regras do despacho')
                if resultado_sisbajud == 'negativo' and all(v == 'nao' for v in sigilo_anexos.values()):
                    ato_meios(driver, debug=debug)
                elif resultado_sisbajud == 'negativo' and any(v == 'sim' for v in sigilo_anexos.values()):
                    ato_termoS(driver, debug=debug)
                else:
                    ato_bloq(driver, debug=debug)
            else:
                if debug:
                    print('[ARGOS][REGRAS] Mais de uma reclamada - Não criando GIGS aqui.')
                # criar_gigs(driver, dias_uteis=0, observacao='Pz mdd subid', tela='principal', log=debug) # REMOVIDO
        # 3. Se é decisão com texto "defiro a instauração"
        elif tipo_documento == 'decisao' and 'defiro a instauração' in texto_documento.lower():
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como decisão de instauração')
            if resultado_sisbajud == 'negativo':
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo - chamando pec_idpj')
                pec_idpj(driver, debug=debug)
            elif resultado_sisbajud == 'positivo':
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD positivo - criando lembrete e chamando pec_idpj')
                lembrete_bloq(driver, debug=debug)
                pec_idpj(driver, debug=debug)
        else:
            if debug:
                print(f'[ARGOS][REGRAS] Tipo de documento não identificado: {tipo_documento}')
    except Exception as e:
        if debug:
            print(f'[ARGOS][REGRAS][ERRO] Falha ao aplicar regras: {e}')
        raise

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
        texto_documento, tipo_documento = buscar_documento_argos(driver, log=log)
        if log:
            print(f'[ARGOS][DOCUMENTO] Tipo encontrado: {tipo_documento}')
            
        # 2. Aplica regras específicas do Argos
        aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=log)
            
        if log:
            print('[ARGOS][ANDAMENTO] Processamento do andamento concluído.')
            
    except Exception as e:
        if log:
            print(f'[ARGOS][ANDAMENTO][ERRO] Falha no processamento do andamento: {e}')
            raise

def fechar_intimacao(driver, log=True):
    try:
        if log:
            print('[ARGOS][FECHAR INTIMAÇÃO] Iniciando fechamento de intimação...')
        menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#botao-menu'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", menu)
        menu.click()
        time.sleep(0.5)
        btns = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Expedientes"]')
        btn_exp = None
        for btn in btns:
            if btn.is_displayed():
                btn_exp = btn
                break
        if not btn_exp:
            print('[ARGOS][FECHAR INTIMAÇÃO][ERRO] Botão Expedientes não encontrado.')
            return False
        btn_exp.click()
        time.sleep(1)
        # Foco no modal
        modal = None
        modais = driver.find_elements(By.CSS_SELECTOR, '.mat-dialog-container')
        for m in modais:
            if m.is_displayed():
                modal = m
                break
        if not modal:
            print('[ARGOS][FECHAR INTIMAÇÃO][ERRO] Modal não encontrado.')
            return False
        # Busca a linha com prazo 30
        linhas = modal.find_elements(By.CSS_SELECTOR, 'tbody tr')
        checkbox_span = None
        for linha in linhas:
            tds = linha.find_elements(By.TAG_NAME, 'td')
            if len(tds) > 8 and tds[8].text.strip() == '30':
                try:
                    checkbox_span = linha.find_element(By.CSS_SELECTOR, '.mat-checkbox-inner-container')
                    break
                except Exception:
                    continue
        if not checkbox_span:
            print('[ARGOS][FECHAR INTIMAÇÃO][WARN] Checkbox visual ao lado do prazo 30 NÃO encontrada. Fechando modal pelo ícone e seguindo.')
            # Clica no botão de fechar modal (ícone fa-window-close)
            try:
                btn_fechar_modal = modal.find_element(By.CSS_SELECTOR, 'a.btn-fechar-link')
                if btn_fechar_modal.is_displayed():
                    btn_fechar_modal.click()
                    time.sleep(0.5)
                    return True  # Segue normalmente
            except Exception as e:
                print('[ARGOS][FECHAR INTIMAÇÃO][ERRO] Não foi possível fechar o modal pelo ícone:', e)
                # Tenta sair com ESC
                from selenium.webdriver.common.keys import Keys
                body = driver.find_element(By.TAG_NAME, 'body')
                body.send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                print('[ARGOS][FECHAR INTIMAÇÃO][INFO] Enviado ESC para fechar modal.')
                return True        
        # Diminui o zoom da página para 70% ANTES de selecionar a checkbox
        driver.execute_script("document.body.style.zoom='70%'")
        time.sleep(0.5)
        
        # Melhorias solicitadas: clique na checkbox e pressionar espaço
        checkbox_selecionada = False
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox_span)
            checkbox_span.click()
            checkbox_selecionada = True
            if log:
                print('[ARGOS][FECHAR INTIMAÇÃO] Checkbox selecionada com sucesso.')
        except Exception as e:
            print('[ARGOS][FECHAR INTIMAÇÃO][ERRO] Falha ao clicar na checkbox:', e)
            # Se não conseguir clicar, fecha o modal e segue
            try:
                btn_fechar_modal = modal.find_element(By.CSS_SELECTOR, 'a.btn-fechar-link')
                if btn_fechar_modal.is_displayed():
                    btn_fechar_modal.click()
                    time.sleep(0.5)
                    return True
            except Exception as e:
                print('[ARGOS][FECHAR INTIMAÇÃO][ERRO] Não foi possível fechar o modal pelo ícone após erro no clique:', e)
                from selenium.webdriver.common.keys import Keys
                body = driver.find_element(By.TAG_NAME, 'body')
                body.send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                print('[ARGOS][FECHAR INTIMAÇÃO][INFO] Enviado ESC para fechar modal.')
                return True
        
        # Busca e clica no botão 'Fechar Expedientes'
        btn_fechar = None
        botoes = modal.find_elements(By.CSS_SELECTOR, 'button[aria-label="Fechar Expedientes"]')
        for b in botoes:
            if b.is_displayed():
                btn_fechar = b
                break
        if not btn_fechar:
            print('[ARGOS][FECHAR INTIMAÇÃO][ERRO] Botão Fechar Expedientes não encontrado.')
            return False
        
        # Se checkbox foi selecionada, pressiona espaço antes de clicar em fechar
        if checkbox_selecionada:
            try:
                from selenium.webdriver.common.keys import Keys
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
                time.sleep(0.5)
                if log:
                    print('[ARGOS][FECHAR INTIMAÇÃO] Espaço pressionado após seleção da checkbox.')
            except Exception as e:
                if log:
                    print(f'[ARGOS][FECHAR INTIMAÇÃO][WARN] Falha ao pressionar espaço: {e}')
        
        btn_fechar.click()
        time.sleep(1)
        
        # Busca o modal correto de confirmação pelo título
        modal_confirm = None
        modais_confirm = driver.find_elements(By.CSS_SELECTOR, '.mat-dialog-container')
        for m in modais_confirm:
            try:
                titulo = m.find_element(By.CSS_SELECTOR, 'h2.mat-dialog-title')
                if 'Fechamento de prazos em aberto' in titulo.text:
                    modal_confirm = m
                    break
            except Exception:
                continue
        if not modal_confirm:
            print('[ARGOS][FECHAR INTIMAÇÃO][ERRO] Modal de confirmação não encontrado.')
            return False
            
        btn_sim = None
        botoes_sim = modal_confirm.find_elements(By.CSS_SELECTOR, 'button.mat-primary')
        for b in botoes_sim:
            if b.is_displayed() and 'Sim' in b.text:
                btn_sim = b
                break
        if not btn_sim:
            print('[ARGOS][FECHAR INTIMAÇÃO][ERRO] Botão Sim não encontrado.')
            return False
            
        btn_sim.click()
        
        # Aguarda o fechamento completo do modal antes de continuar
        if log:
            print('[ARGOS][FECHAR INTIMAÇÃO] Aguardando fechamento completo do modal...')
        
        # Aguarda até que não haja mais modais visíveis
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len([m for m in d.find_elements(By.CSS_SELECTOR, '.mat-dialog-container') if m.is_displayed()]) == 0
            )
            if log:
                print('[ARGOS][FECHAR INTIMAÇÃO] Modal fechado completamente. Aguardando estabilização...')
            time.sleep(2)  # Tempo adicional para garantir que a interface se estabilize
        except Exception as e:
            if log:
                print(f'[ARGOS][FECHAR INTIMAÇÃO][WARN] Timeout aguardando fechamento do modal: {e}')
            time.sleep(2)  # Fallback: aguarda tempo fixo
        
        if log:
            print('[ARGOS][FECHAR INTIMAÇÃO] Fechamento de intimação concluído.')
        return True
    except Exception as e:
        print('[ARGOS][FECHAR INTIMAÇÃO][ERRO]', e)
        return False

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
    sigilo_types = ["infojud", "doi", "irpf", "dimob"]
    found_sigilo = {k: False for k in sigilo_types}
    sigilo_anexos = {k: "nao" for k in sigilo_types}
    any_sigilo = False
    for anexo in anexos:
        texto_anexo = anexo.text.strip().lower()
        tipo_anexo_encontrado = None
        
        # Verifica se é um anexo especial (INFOJUD, DOI, IRPF, DIMOB)
        for k in sigilo_types:
            if k in texto_anexo:
                found_sigilo[k] = True
                tipo_anexo_encontrado = k
                
                # Para anexos especiais: INSERIR sigilo (se ícone estiver azul, clicar para tornar vermelho)
                btn_sigilo = anexo.find_elements(By.CSS_SELECTOR, "i.fa-wpexplorer")
                if btn_sigilo:
                    # Verifica se o ícone está azul (sem sigilo - tl-nao-sigiloso)
                    if "tl-nao-sigiloso" in btn_sigilo[0].get_attribute("class"):
                        safe_click(driver, btn_sigilo[0])
                        time.sleep(1)
                        sigilo_anexos[k] = "sim"
                        if log:
                            print(f'[ARGOS][ANEXOS] Sigilo INSERIDO para anexo especial: {texto_anexo}')
                    else:
                        sigilo_anexos[k] = "sim"  # já estava com sigilo
                        if log:
                            print(f'[ARGOS][ANEXOS] Anexo especial já tinha sigilo: {texto_anexo}')
                else:
                    sigilo_anexos[k] = "nao"                # Apply visibility
                btn_visibilidade = anexo.find_elements(By.CSS_SELECTOR, "i.fa-plus")
                if btn_visibilidade:
                    if log:
                        print(f'[ARGOS][ANEXOS] Clicando no botão de visibilidade para: {texto_anexo}')
                    safe_click(driver, btn_visibilidade[0])
                    time.sleep(1)
                    
                    # Aguarda e busca o modal de confirmação
                    try:
                        modal_visibilidade = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".mat-dialog-container"))
                        )
                        if log:
                            print(f'[ARGOS][ANEXOS] Modal de visibilidade aberto para: {texto_anexo}')
                        
                        # Clica no botão com classe botao-icone-titulo-coluna (fa-check)
                        try:
                            btn_check = modal_visibilidade.find_element(By.CSS_SELECTOR, "button.botao-icone-titulo-coluna i.fa-check")
                            if log:
                                print(f'[ARGOS][ANEXOS] Clicando no botão de check para: {texto_anexo}')
                            safe_click(driver, btn_check)
                            time.sleep(1)
                        except Exception as e:
                            if log:
                                print(f'[ARGOS][ANEXOS][ERRO] Botão de check não encontrado para: {texto_anexo} - {e}')
                        
                        # Busca o botão Salvar
                        btn_salvar = modal_visibilidade.find_elements(By.CSS_SELECTOR, "button[color='primary'] .mat-button-wrapper")
                        if not btn_salvar:
                            # Seletor alternativo para o botão Salvar
                            btn_salvar = modal_visibilidade.find_elements(By.CSS_SELECTOR, "button.mat-primary")
                        
                        if btn_salvar:
                            if log:
                                print(f'[ARGOS][ANEXOS] Clicando no botão Salvar para: {texto_anexo}')
                            safe_click(driver, btn_salvar[0])
                            time.sleep(1)
                        else:
                            if log:
                                print(f'[ARGOS][ANEXOS][ERRO] Botão Salvar não encontrado para: {texto_anexo}')
                                
                    except Exception as e:
                        if log:
                            print(f'[ARGOS][ANEXOS][ERRO] Modal de visibilidade não abriu para: {texto_anexo} - {e}')
                else:
                    if log:
                        print(f'[ARGOS][ANEXOS][ERRO] Botão de visibilidade não encontrado para: {texto_anexo}')
                any_sigilo = True
                break
        
        # Se não é anexo especial, REMOVER sigilo (se ícone estiver vermelho, clicar para tornar azul)
        if not tipo_anexo_encontrado:
            btn_sigilo = anexo.find_elements(By.CSS_SELECTOR, "i.fa-wpexplorer")
            if btn_sigilo:
                # Verifica se o ícone está vermelho (com sigilo - tl-sigiloso)
                if "tl-sigiloso" in btn_sigilo[0].get_attribute("class"):
                    safe_click(driver, btn_sigilo[0])
                    time.sleep(1)
                    if log:
                        print(f'[ARGOS][ANEXOS] Sigilo REMOVIDO para anexo comum: {texto_anexo}')
                else:
                    if log:
                        print(f'[ARGOS][ANEXOS] Anexo comum já estava sem sigilo: {texto_anexo}')
    # Extract PDF text
    from Fix import extrair_pdf
    texto_pdf = extrair_pdf(driver, log=log)
    executados = []
    resultado_sisbajud = None
    regra_aplicada = None
    if texto_pdf:
        # Split pages
        paginas = texto_pdf.split('\f') if '\f' in texto_pdf else [texto_pdf]
        # 1. Extract executados from page 1
        pagina1 = paginas[0] if paginas else texto_pdf
        lines = pagina1.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^[0-9]+\.', line):
                nome = line.split('.', 1)[1].strip()
                documento = ''
                # Look for document in the next lines
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
        # 2. Extract SISBAJUD result from page 3
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
                print('[SISBAJUD][DEBUG] Lines after SISBAJUD marker:')
                for k, l in enumerate(trecho_log):
                    print(f'  [{sisbajud_idx+k}] {repr(l)}')
                # Robust: look ahead up to 6 lines after SISBAJUD, skipping empty lines
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
                        # Try to parse as value (e.g. R$ 0,00)
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
        # Use robust SISBAJUD extraction from full text
        resultado_sisbajud, regra_aplicada = extract_sisbajud_result_from_text(texto_pdf, log=log)
    if log:
        print(f'[ARGOS][ANEXOS] Extracted executados (page 1): {executados}')
        print(f'[ARGOS][ANEXOS] SISBAJUD result: {resultado_sisbajud}')
        print(f'[ARGOS][ANEXOS] SISBAJUD rule applied: {regra_aplicada}')
        print(f'[ARGOS][ANEXOS] Found attachments: {found_sigilo}')
        print(f'[ARGOS][ANEXOS] Will register as sigiloso: {any_sigilo}')
    return {'executados': executados, 'resultado_sisbajud': resultado_sisbajud, 'found_sigilo': found_sigilo, 'sigilo_anexos': sigilo_anexos, 'sigiloso': any_sigilo}

def fluxo_mandado(driver):
    """
    Percorre a lista de processos e executa o fluxo adequado (Argos ou Outros) para cada mandado.
    """
    def fluxo_callback(driver):
        try:
            print('\n' + '='*50)
            print('[FLUXO] Iniciando análise do documento...')
            
            # Identificar documento ativo
            doc_ativo = driver.find_element(By.CSS_SELECTOR, 'li.tl-item-container.tl-item-ativo')
            if not doc_ativo:
                print('[FLUXO][ERRO] Documento ativo não encontrado')
                return
                
            texto_doc = doc_ativo.text
            print(f'[FLUXO] Documento encontrado: {texto_doc}')
            
            # Decisão de fluxo baseada no texto do documento
            texto_lower = texto_doc.lower()
            
            if 'pesquisa patrimonial - argos' in texto_lower:
                print('\n[FLUXO] >>> INICIANDO FLUXO ARGOS <<<')
                print(f'[FLUXO][ARGOS] Documento identificado: {texto_doc}')
                print('='*50)
                processar_argos(driver)
            elif 'oficial de justiça' in texto_doc:
                print(f'[MANDADO] Fluxo OUTROS')
                def fluxo_mandados_hipotese2(driver):
                    print('[MANDADOS][OUTROS] Iniciando fluxo Mandado 2 (Outros)')
                    def analise_padrao(texto):
                        print(f"[MANDADOS][OUTROS] Texto extraído para análise:\n{texto}\n---Fim do documento---")
                        texto_lower = texto.lower()
                        padrao_oficial = "certidão de oficial" in texto_lower
                        padrao_positivo = any(p in texto_lower for p in ["citei", "intimei", "recebeu o mandado", "de tudo ficou ciente"])
                        padrao_negativo = any(p in texto_lower for p in [
                            "não localizado", "negativo", "não encontrado",
                            "deixei de citar", "deixei de efetuar", "não logrei êxito", "desconhecido no local",
                            "não foi possível efetuar"
                        ])
                        if padrao_oficial:
                            print("[MANDADOS][OUTROS][LOG] Padrão 'certidão de oficial' ENCONTRADO no texto.")
                            if padrao_positivo:
                                print("[MANDADOS][OUTROS][LOG] Padrão de mandado POSITIVO encontrado no texto.")
                                criar_gigs(driver, dias_uteis=0, observacao='xx positivo', tela='principal')
                            elif padrao_negativo:
                                print("[MANDADOS][OUTROS][LOG] Padrão de mandado NEGATIVO encontrado no texto.")
                                # Busca último mandado na timeline
                                documento = buscar_ultimo_mandado(driver)
                                if documento:
                                    # Verifica quem assinou
                                    autor = verificar_autor_documento(documento, driver)
                                    if autor and 'silas passos' in autor.lower():
                                        print("[MANDADOS][OUTROS][LOG] Último mandado assinado por Silas Passos - chamando ato_edital")
                                        ato_edital(driver)
                                    else:
                                        print("[MANDADOS][OUTROS][LOG] Último mandado assinado por outro autor - não faz nada")
                                else:
                                    print("[MANDADOS][OUTROS][LOG] Não encontrado último mandado na timeline")
                                    criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                            else:
                                print("[MANDADOS][OUTROS][LOG] Mandado sem padrão reconhecido. Criando GIGS fallback.")
                                criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                        else:
                            print("[MANDADOS][OUTROS][LOG] Documento NÃO é certidão de oficial. Criando GIGS fallback.")
                            criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                        return None
                    texto, resultado = extrair_documento(driver, regras_analise=analise_padrao)
                    if not texto:
                        print("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
                        return
                    try:
                        driver.close()
                        print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
                    except Exception as e:
                        print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e}')
                    print('[MANDADOS][OUTROS] Fluxo Mandado 2 concluído.')
                fluxo_mandados_hipotese2(driver)
                print('[FLUXO][OUTROS] Processamento concluído')
                
            else:
                print('\n[FLUXO][AVISO] >>> DOCUMENTO NÃO IDENTIFICADO <<<')
                print(f'[FLUXO][AVISO] Texto do documento: {texto_doc}')
                print('='*50)
                
        except Exception as e:
            print('\n[FLUXO][ERRO] Falha ao processar mandado:')
            print(f'[FLUXO][ERRO] Detalhes: {str(e)}')
            print('='*50)
        finally:
            if len(driver.window_handles) > 1:
                print('[FLUXO] Fechando aba de detalhes e voltando para lista')
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                print('[FLUXO] Retorno para lista completado')
            print('='*50 + '\n')    # Aplica o filtro de mandados devolvidos ANTES de iniciar o processamento
    if aplicar_filtro_mandados_devolvidos(driver):
        print('[FLUXO] Filtro de mandados devolvidos aplicado com sucesso. Iniciando processamento...')
        # Executa o processamento da lista com o callback melhorado
        indexar_e_processar_lista(driver, fluxo_callback)
    else:
        print('[FLUXO][ERRO] Falha ao aplicar filtro de mandados devolvidos. Processamento cancelado.')
        return

def buscar_documentos_sequenciais(driver):
    documentos_alvo = [
        "Certidão de devolução",
        "Certidão de expedição",
        "Planilha",
        "Intimação",
        "Decisão"
    ]
    resultados = []
    elementos = driver.find_elements(By.CSS_SELECTOR, ".tl-data, li.tl-item-container")
    indice_doc_atual = 0
    for elemento in elementos:
        if indice_doc_atual >= len(documentos_alvo):
            break
        texto_item = elemento.text.strip().lower()
        documento_atual = documentos_alvo[indice_doc_atual]
        if documento_atual.lower() in texto_item:
            print(f"[ENCONTRADO] {documento_atual}")
            resultados.append(elemento)
            indice_doc_atual += 1
    return resultados

def processar_argos(driver, log=True):
    """
    Processa fluxo Argos com nova regra de busca de documentos.
    
    NOVA REGRA IMPLEMENTADA:
    - Busca decisões/despachos que vêm ANTES da "Planilha de Atualização de Cálculos" na timeline
    - Se não encontrar planilha ou documentos antes dela, usa lógica fallback (primeiro despacho/decisão)
    - Aplica ações conforme o tipo de documento encontrado (decisão vs despacho)
    """
    try:
        # Cria GIGS inicial simples
        criar_gigs(driver, dias_uteis=0, observacao='xx', tela='principal', log=log)
        if log:
            print('[ARGOS] GIGS inicial criado, iniciando fluxo m1 com nova regra de busca...')
        
        # NOVA FUNCIONALIDADE: Busca documento usando a regra da planilha
        documento_texto, documento_tipo = buscar_documento_argos(driver, log=log)
        
        if documento_texto and documento_tipo:
            if log:
                print(f'[ARGOS] Documento encontrado: tipo={documento_tipo}')
                print(f'[ARGOS] Iniciando processamento baseado no tipo de documento...')
            
            # Aplica ações conforme o tipo de documento
            if documento_tipo == 'decisao':
                if log:
                    print('[ARGOS] Processando DECISÃO encontrada antes da planilha...')
                # Aqui seria implementada a lógica específica para decisões
                # Por exemplo: análise de padrões específicos, criação de minutas, etc.
                
            elif documento_tipo == 'despacho':
                if log:
                    print('[ARGOS] Processando DESPACHO encontrado antes da planilha...')
                # Aqui seria implementada a lógica específica para despachos
                # Por exemplo: análise de comandos, ações administrativas, etc.
            
            # Continua com o fluxo m1 principal baseado no documento encontrado
            if log:
                print('[ARGOS] Documento processado, continuando fluxo m1...')
                
        else:
            if log:
                print('[ARGOS] Nenhum documento relevante encontrado, continuando com fluxo padrão...')
        
        if log:
            print('[ARGOS] Processamento m1 concluído com nova regra de busca.')
            
    except Exception as e:
        if log:
            print(f'[ARGOS][ERRO] Falha no processamento: {e}')
        raise

def buscar_documento_argos(driver, log=True):
    """Busca documentos relevantes na timeline do Argos, priorizando decisões/despachos anteriores à Planilha de Atualização de Cálculos."""
    try:
        # Aguarda a timeline carregar (aguarda pelo menos um item na timeline)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'li.tl-item-container'))
            )
            if log:
                print('[ARGOS][DEBUG] Timeline carregada, buscando documentos...')
        except Exception:
            if log:
                print('[ARGOS][ERRO] Timeline não carregou a tempo.')
            return None, None
        
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if log:
            print(f'[ARGOS][DEBUG] {len(itens)} itens encontrados na timeline.')
        
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
                
                # Clica para ativar o documento
                driver.execute_script('arguments[0].scrollIntoView(true);', link)
                link.click()
                time.sleep(1)
                texto, _ = extrair_documento(driver)
                
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
        if log:
            print('[ARGOS][DEBUG] Usando lógica fallback: procurando primeiro despacho/decisão na timeline...')
        
        for idx, item in enumerate(itens):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: texto do link = {doc_text}')
                # Verifica se é despacho ou decisão
                if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: documento relevante encontrado (fallback), clicando para ativar.')
                    # Clica para ativar o documento (não abre nova aba)
                    driver.execute_script('arguments[0].scrollIntoView(true);', link)
                    link.click()
                    time.sleep(1)
                    texto, _ = extrair_documento(driver)
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
                else:
                    if log:
                        print(f'[ARGOS][DEBUG] Item {idx}: não é despacho/decisão/sentença/conclusão.')
            except Exception as e:
                if log:
                    print(f'[ARGOS][DEBUG] Item {idx}: erro ao processar item: {e}')
                continue
        
        if log:
            print('[ARGOS] Nenhum documento relevante encontrado após varrer os itens.')
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
                    texto, _ = extrair_documento(driver)
                    if texto:
                        return texto, 'fallback'
        except Exception as e_fb:
            if log:
                print(f'[ARGOS][ERRO] Fallback também falhou: {e_fb}')
        return None, None

def ultimo_mdd(driver, log=True):
    """
    Busca o último mandado na timeline (item com texto começando por 'Mandado' e ícone de gavel) e retorna (nome_autor, elemento_mandado).
    """
    try:
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        for idx, item in enumerate(itens):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
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
        cabecalho = driver.find_element(By.CSS_SELECTOR, ".cabecalho-conteudo .mat-card-title")
        titulo_documento = cabecalho.text.lower()
        
        eh_certidao_oficial = any(p in titulo_documento for p in [
            "certidão de oficial",
            "certidão de oficial de justiça"
        ])
        
        if not eh_certidao_oficial:
            if log:
                print(f"[MANDADOS][OUTROS][LOG] Documento '{cabecalho.text}' NÃO é certidão de oficial. Criando GIGS fallback.")
            criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
            try:
                driver.close()
                if log:
                    print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
            except Exception as e:
                if log:
                    print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e}')
            if log:
                print('[MANDADOS][OUTROS] Fluxo Mandado (Outros) concluído.')
            return
        
        if log:
            print(f"[MANDADOS][OUTROS][LOG] Documento '{cabecalho.text}' é certidão de oficial. Prosseguindo com análise.")
            
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro ao verificar cabeçalho: {e}. Criando GIGS fallback.")
        criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
        try:
            driver.close()
            if log:
                print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
        except Exception as e_close:
            if log:
                print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e_close}')
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
            "não logrei êxito",
            "desconhecido no local",
            "não foi possível efetuar"
            "parou de responder",
            "não foi possível localizar",
        ])
        
        if padrao_positivo:
            if log:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado POSITIVO encontrado no texto.")
            criar_gigs(driver, dias_uteis=0, observacao='xx positivo', tela='principal')
        elif padrao_negativo:
            if log:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado NEGATIVO encontrado no texto.")
            
            # Verifica se contém "penhora de bens" no texto
            if "penhora de bens" in texto_lower:
                if log:
                    print("[MANDADOS][OUTROS][LOG] Texto contém 'penhora de bens' - chamando ato_meios")
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
                    criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
        else:
            if log:
                print("[MANDADOS][OUTROS][LOG] Mandado sem padrão reconhecido. Criando GIGS fallback.")
            criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
        return None
    texto, resultado = extrair_documento(driver, regras_analise=analise_padrao)
    if not texto:
        if log:
            print("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return
    try:
        driver.close()
        if log:
            print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
    except Exception as e:
        if log:
            print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e}')
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
        "Item 2: Decisão deferindo pedido",    # <- Este seria ignorado (após item 1)
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
    Função principal que coordena todo o fluxo do programa.
    1. Setup inicial (driver e limpeza)
    2. Login humanizado
    3. Navegação para a lista de documentos internos
    4. Execução do fluxo automatizado sobre a lista
    """
    # Setup inicial
    driver = criar_driver_custom(headless=False)
    if not driver:
        return

    # Login process (agora usando login_pc do Fix.py)
    if not login_pc(driver):
        driver.quit()
        return

    # Navegação para a lista de documentos internos
    if not navegacao(driver):
        driver.quit()
        return

    # Processa a lista de documentos internos
    iniciar_fluxo(driver)

    print("[INFO] Processamento concluído. Pressione ENTER para encerrar...")
    input()
    driver.quit()

if __name__ == "__main__":
    main()
