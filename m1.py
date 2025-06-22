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
from p2 import checar_prox
from driver_config import criar_driver, login_func
from urllib.parse import urlparse
import sys
from datetime import datetime

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

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
        print(f'[NAV][ERRO] Falha na navegação: {str(e)}')
        return False

def iniciar_fluxo(driver):
    """Função que decide qual fluxo será aplicado"""
    def fluxo_callback(driver):
        try:            # Busca o cabeçalho do documento ativo
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
            elif any(termo in texto_lower for termo in ['oficial de justiça', 'certidão de oficial']):
                print(f'[OUTROS] Processo em análise: {texto_doc}')
                fluxo_mandados_outros(driver, log=False)
            else:
                print(f'[AVISO] Documento não identificado: {texto_doc}')
                
        except Exception as e:
            print(f'[ERRO] Falha ao processar mandado: {str(e)}')
        finally:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                print('[LIMPEZA] Retorno à lista concluído')# Aplica o filtro de mandados devolvidos ANTES de iniciar o processamento
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
        regra_aplicada = None
        trecho_relevante = texto_documento if texto_documento else ''
        if debug:
            print(f'[ARGOS][REGRAS] Analisando regras para tipo: {tipo_documento}')
            print(f'[ARGOS][REGRAS] Resultado SISBAJUD: {resultado_sisbajud}')
            print(f'[ARGOS][REGRAS] Sigilo anexos: {sigilo_anexos}')
        
        # Nova regra para detectar "devendo se manifestar" e repetir a análise no próximo documento
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
                    
                    # Extraindo texto do novo documento
                    try:
                        novo_texto, _ = extrair_documento(driver)
                        novo_tipo = "decisao" if "decisão" in doc_link.text.lower() else "despacho"
                        
                        if debug:
                            print(f'[ARGOS][REGRAS] Novo documento extraído (tipo {novo_tipo})')
                            print(f'[ARGOS][REGRAS] Repetindo análise de regras para o novo documento')
                        
                        # Chamada recursiva para aplicar regras no novo documento
                        aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, novo_tipo, novo_texto, debug)
                        regra_aplicada += ' | análise repetida em documento seguinte'
                        return  # Retornamos após aplicar as regras no próximo documento
                    except Exception as e_extracao:
                        if debug:
                            print(f'[ARGOS][REGRAS][ERRO] Falha ao extrair texto do próximo documento: {e_extracao}')
                else:
                    if debug:
                        print('[ARGOS][REGRAS] Nenhum próximo documento encontrado, continuando com a análise atual')
        
        # 1. Se é despacho com texto específico
        if tipo_documento == 'despacho' and any(p in texto_documento.lower() for p in ['em que pese a ausência', 'argos']):
            regra_aplicada = 'despacho+argos'
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como despacho com texto específico')
            if resultado_sisbajud == 'negativo' and all(v == 'nao' for v in sigilo_anexos.values()):
                regra_aplicada += ' | sisbajud negativo, nenhum anexo sigiloso => ato_meios'
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo e nenhum anexo sigiloso - chamando ato_meios')
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
            if len(dados_processo.get('reclamadas', [])) == 1:
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
                    print('[ARGOS][REGRAS] Mais de uma reclamada - verificando SISBAJUD')
                if resultado_sisbajud == 'negativo':
                    regra_aplicada += ' | sisbajud negativo => ato_meiosub'
                    ato_meiosub(driver, debug=debug)
                else:
                    regra_aplicada += ' | sisbajud positivo => ato_bloq'
                    ato_bloq(driver, debug=debug)
        elif tipo_documento == 'decisao' and 'defiro a instauração' in texto_documento.lower():
            regra_aplicada = 'decisao+defiro a instauracao'
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como decisão de instauração')
            if resultado_sisbajud == 'negativo':
                regra_aplicada += ' | sisbajud negativo => pec_idpj'
                pec_idpj(driver, debug=debug)
            elif resultado_sisbajud == 'positivo':
                regra_aplicada += ' | sisbajud positivo => lembrete_bloq + pec_idpj'
                lembrete_bloq(driver, debug=debug)
                pec_idpj(driver, debug=debug)
        else:
            regra_aplicada = f'nao identificado: {tipo_documento}'
            if debug:
                print(f'[ARGOS][REGRAS] Tipo de documento não identificado: {tipo_documento}')
        # Log sempre que chamado, para rastreabilidade
        print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
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
    """
    Fecha a intimação do processo, otimizado para performance e confiabilidade.
    """
    try:
        # 1. Abrir menu e clicar em Expedientes
        if log:
            print('[INTIMACAO] Iniciando processo de fechar intimação...')
            
        # Usando as novas funções do Fix.py para esperar e clicar
        menu_selector = '#botao-menu'
        menu_clicked = safe_click(driver, menu_selector, timeout=10, log=log)
        
        if menu_clicked:
            if log:
                print('[INTIMACAO] Menu principal aberto')
        else:
            if log:
                print('[INTIMACAO] Falha ao abrir menu principal')
            # Mesmo com falha, continuamos o processo
                
        sleep(300)  # Nova função sleep em milissegundos
          # Clique no botão Expedientes
        btn_exp_selector = 'button[aria-label="Expedientes"]:not([disabled])'
        btn_exp_clicked = safe_click(driver, btn_exp_selector, timeout=5, log=log)
        
        if btn_exp_clicked:
            if log:
                print('[INTIMACAO] Botão Expedientes clicado')
        else:
            if log:
                print('[INTIMACAO] Falha ao clicar no botão Expedientes')
                print('[INTIMACAO][ALERTA] Provavelmente não há checkbox de 30 dias disponível')
            # Tentativa de escape se o botão não foi clicado
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if log:
                    print('[INTIMACAO] Enviado ESC após falha de clique em Expedientes')
                    print('[INTIMACAO] Modal fechado com ESC, prosseguindo com o fluxo normalmente')
            except Exception:
                pass
            return True  # Retornamos True para não interromper o fluxo Argos
                
        sleep(300)
        
        # 2. Espera o modal de expedientes aparecer (timeout reduzido para 5 segundos)
        try:
            modal_selector = 'mat-dialog-container pje-expedientes-dialogo'
            modal = wait_for_visible(driver, modal_selector, timeout=5)
            
            if modal:
                if log:
                    print('[INTIMACAO] Modal de expedientes aberto')
            else:
                if log:
                    print('[INTIMACAO] Modal de expedientes não encontrado, continuando mesmo assim')
                # Enviamos ESC para garantir que tudo está fechado
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    if log:
                        print('[INTIMACAO] Modal fechado com ESC após não encontrar modal')
                except Exception:
                    pass
                return True  # Retornamos True para não interromper o fluxo Argos
        except Exception as e:
            if log:
                print(f'[INTIMACAO][ERRO] Falha ao verificar modal: {e}')
            # Enviamos ESC para garantir que tudo está fechado
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if log:
                    print('[INTIMACAO] Modal fechado com ESC após erro')
            except Exception:
                pass
            return True  # Retornamos True para não interromper o fluxo Argos

        # 3. Busca linha com prazo 30
        try:
            # Aguarda tbody carregar usando as novas funções
            rows_selector = 'tbody tr'
            first_row = wait(driver, rows_selector, timeout=5)
            
            if not first_row:
                if log:
                    print('[INTIMACAO] Falha ao encontrar linhas de expedientes')
                # Enviamos ESC para fechar o modal e continuamos
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    if log:
                        print('[INTIMACAO] Modal fechado com ESC após não encontrar linhas')
                except Exception:
                    pass
                return True  # Retornamos True para não interromper o fluxo
            
            # Busca célula com prazo 30
            rows = driver.find_elements(By.CSS_SELECTOR, rows_selector)
            prazo_30_encontrado = False
            
            for row in rows:
                try:
                    prazo_cell = row.find_element(By.CSS_SELECTOR, 'td:nth-child(9)')
                    if prazo_cell.text.strip() == '30':
                        prazo_30_encontrado = True
                        # Procura checkbox na última coluna da mesma linha
                        try:
                            checkbox_container = row.find_element(By.CSS_SELECTOR, 'td:last-child mat-checkbox')
                            checkbox = checkbox_container.find_element(By.CSS_SELECTOR, '.mat-checkbox-inner-container')
                            driver.execute_script("arguments[0].click();", checkbox)
                            if log:
                                print('[INTIMACAO] ✓ Checkbox da linha com prazo 30 selecionada')
                            break
                        except Exception as e_check:
                            if log:
                                print(f'[INTIMACAO] ✗ Erro ao selecionar checkbox: {e_check}')
                            continue
                except Exception as e_row:
                    if log:
                        print(f'[INTIMACAO] Erro ao processar linha: {e_row}')
                    continue
                    
            if not prazo_30_encontrado:
                if log:
                    print('[INTIMACAO] ❌ Nenhuma linha com prazo 30 encontrada')
                    print('[INTIMACAO][ALERTA] Ausência do checkbox de 30 dias, fechando modal e prosseguindo')
                # Pressiona ESC e retorna True para continuar o fluxo
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    if log:
                        print('[INTIMACAO] Modal fechado com ESC após não encontrar prazo 30')
                        print('[INTIMACAO] Prosseguindo normalmente com o fluxo Argos')
                except Exception:
                    pass
                return True

            # 4. Clica no botão Fechar Expedientes com safe_click
            btn_fechar_selector = 'button[aria-label="Fechar Expedientes"]'
            btn_fechar_clicked = safe_click(driver, btn_fechar_selector, timeout=5, log=log)
            
            if not btn_fechar_clicked:
                if log:
                    print('[INTIMACAO] Falha ao clicar no botão Fechar Expedientes')
                # Pressiona ESC e retorna True para continuar o fluxo
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    if log:
                        print('[INTIMACAO] Modal fechado com ESC após falha no botão Fechar')
                except Exception:
                    pass
                return True

            if log:
                print('[INTIMACAO] Botão Fechar Expedientes clicado')
            sleep(500)  # Aguarda modal de confirmação

            # 5. Aguarda e interage com o modal de confirmação
            try:
                modal_confirm_selector = 'mat-dialog-container[role="dialog"]'
                modal_confirm = wait_for_visible(driver, modal_confirm_selector, timeout=5)
                
                if not modal_confirm:
                    if log:
                        print('[INTIMACAO] Modal de confirmação não encontrado, continuando mesmo assim')
                    return True
                    
                # Lista de seletores para teste, do mais específico ao mais genérico
                seletores_sim = [
                    'button.mat-button.mat-button-base.mat-primary span.mat-button-wrapper',
                    'mat-dialog-container button.mat-button.mat-primary',
                    'button.mat-button.mat-primary',
                    'button[color="primary"]',
                    '.mat-dialog-actions button:first-child',
                ]
                
                # Tentativa com safe_click para cada seletor
                sim_clicked = False
                for seletor in seletores_sim:
                    if safe_click(driver, seletor, timeout=2, log=False):
                        if log:
                            print(f'[INTIMACAO] Botão Sim clicado com seletor: {seletor}')
                        sim_clicked = True
                        break
                
                if not sim_clicked:
                    if log:
                        print('[INTIMACAO] Não foi possível clicar no botão Sim, tentando ESC')
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    
                return True  # Sempre retorna True para continuar o fluxo
                
            except Exception as e:
                if log:
                    print(f'[INTIMACAO][ERRO] Falha no modal de confirmação: {e}')
                # Enviamos ESC para garantir que tudo está fechado
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                except Exception:
                    pass
                return True  # Retornamos True para não interromper o fluxo Argos
                
        except Exception as e:
            if log:
                print(f'[INTIMACAO][ERRO] Falha ao processar expedientes: {e}')
            # Enviamos ESC para garantir que tudo está fechado
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                if log:
                    print('[INTIMACAO] Modal fechado com ESC após erro')
            except Exception:
                pass
            return True  # Retornamos True para não interromper o fluxo Argos
            
    except Exception as e:
        if log:
            print(f'[INTIMACAO][ERRO] Falha geral: {str(e)}')
        # Tentativa final de enviar ESC para limpar qualquer modal aberto
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            if log:
                print('[INTIMACAO] Modal fechado com ESC após erro')
        except Exception:
            pass
        return True  # Retornamos True para não interromper o fluxo Argos

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
    sigilo_types = ["infojud", "doi", "irpf", "dimob", "ecac", "efinanceira", "e-financeira"]
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
                    if "tl-nao-sigiloso" in btn_sigilo[0].get_attribute("class"):
                        safe_click(driver, btn_sigilo[0])
                        time.sleep(1)
                        sigilo_anexos[k] = "sim"
                    else:
                        sigilo_anexos[k] = "sim"
                else:
                    sigilo_anexos[k] = "nao"
                # Clique de visibilidade: buscar diretamente o botão correto e clicar com .click()
                try:
                    btn_visibilidade = anexo.find_element(By.CSS_SELECTOR, "button:has(i.fas.fa-plus.tl-sigiloso)")
                    if log:
                        print(f'[ARGOS][ANEXOS] Clicando no botão de visibilidade correto para: {texto_anexo}')
                    btn_visibilidade.click()
                    time.sleep(0.5)
                    # Aguarda e busca o modal de confirmação
                    modal_visibilidade = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, "mat-dialog-container[role='dialog']"))
                    )
                    # Busca o botão Salvar
                    btn_salvar = modal_visibilidade.find_elements(By.CSS_SELECTOR, "button[color='primary'] .mat-button-wrapper")
                    if not btn_salvar:
                        if log:
                            print(f"[ARGOS][ANEXOS][ERRO] Botão Salvar não encontrado no modal de visibilidade para: {texto_anexo}")
                    if btn_salvar:
                        btn_salvar[0].click()
                        time.sleep(0.5)
                    else:
                        if log:
                            print(f"[ARGOS][ANEXOS][ERRO] Botão Salvar não encontrado no modal de visibilidade para: {texto_anexo}")
                except Exception as e:
                    if log:
                        print(f"[ARGOS][ANEXOS][ERRO] Botão de visibilidade não encontrado ou erro ao clicar para: {texto_anexo} | {e}")
                any_sigilo = True
                break
        # Se não é anexo especial, REMOVER sigilo (se ícone estiver vermelho, clicar para tornar azul)
        if not tipo_anexo_encontrado:
            btn_sigilo = anexo.find_elements(By.CSS_SELECTOR, "i.fa-wpexplorer")
            if btn_sigilo:
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
            
            # Passo 0: Clicar no ícone lupa (fa-search lupa-doc-nao-apreciado)
            try:
                print('[FLUXO] Passo 0: Tentando clicar no ícone lupa (fa-search)')
                lupa_selector = 'i.fa.fa-search.fa-2x.lupa-doc-nao-apreciado'
                resultado = safe_click(driver, lupa_selector, timeout=5, log=True)
                if resultado:
                    print('[FLUXO] Passo 0: Clique na lupa realizado com sucesso')
                    # Aguarda breve momento para carregar detalhes após o clique
                    time.sleep(1)
                else:
                    print('[FLUXO][AVISO] Passo 0: Ícone lupa não encontrado ou não clicável')
            except Exception as e:
                print(f'[FLUXO][AVISO] Passo 0: Erro ao tentar clicar na lupa: {e}')
                # Continua o fluxo mesmo se houver erro neste passo
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
                    # Validar conexão antes de prosseguir com análise
                    if not validar_conexao_driver(driver, contexto="OUTROS"):
                        print("[MANDADOS][OUTROS][ERRO] Falha na validação de conexão")
                        return
                    
                    def analise_padrao(texto):
                        print(f"[MANDADOS][OUTROS] Texto extraído para análise:\n{texto}\n---Fim do documento---")
                        texto_lower = texto.lower()
                        
                        # Nova regra: Verifica se contém "cancelamento TOTAL da inserção"
                        if "cancelamento total da inserção" in texto_lower:
                            print("[MANDADOS][OUTROS][LOG] Padrão 'cancelamento TOTAL da inserção' ENCONTRADO - chamando mov_arquivar")
                            try:
                                mov_arquivar(driver)
                                print("[MANDADOS][OUTROS][LOG] mov_arquivar executado com sucesso")
                                return None
                            except Exception as e:
                                print(f"[MANDADOS][OUTROS][ERRO] Erro ao executar mov_arquivar: {e}")
                        
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
                                # criar_gigs(driver, dias_uteis=0, observacao='xx positivo', tela='principal')
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
                                    # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                            else:
                                print("[MANDADOS][OUTROS][LOG] Mandado sem padrão reconhecido. Criando GIGS fallback.")
                                # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                        else:
                            print("[MANDADOS][OUTROS][LOG] Documento NÃO é certidão de oficial. Criando GIGS fallback.")
                            # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                        return None
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
                    pass
        # 2. Processar anexos
        print('[ARGOS] Tratando anexos...')
        anexos_info = tratar_anexos_argos(driver, documentos_sequenciais, log=log) if documentos_sequenciais else None
        
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
        documento_texto, documento_tipo = buscar_documento_argos(driver, log=True)  # Forçando log=True para depuração
        
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
                        print(f'[ARGOS][DEBUG] Item {idx}: documento relevante encontrado (fallback), clicando para ativar.')                    # Clica para ativar o documento usando safe_click (fallback)
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
                    
                    sleep(1500)  # Esperamos mais tempo para carregar o documento
                    print(f'[ARGOS][DOC][FALLBACK] Extraindo texto do documento...')
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
    
    # Verificação inicial de conexão do driver
    if not validar_conexao_driver(driver, contexto="INICIO_FLUXO"):
        if log:
            print('[MANDADOS][OUTROS][FATAL] Driver em estado inválido no início do fluxo')
        return
        
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
            
            # Verificação de conexão antes do fechamento crítico de aba
            if validar_conexao_driver(driver, contexto="FECHAR_ABA"):
                try:
                    driver.close()
                    if log:
                        print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
                except Exception as e:
                    if log:
                        print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e}')
            else:
                if log:
                    print('[MANDADOS][OUTROS][ALERTA] Não foi possível fechar a aba devido a erro de conexão.')
                    
            if log:
                print('[MANDADOS][OUTROS] Fluxo Mandado (Outros) concluído.')
            return
        
        if log:
            print(f"[MANDADOS][OUTROS][LOG] Documento '{cabecalho.text}' é certidão de oficial. Prosseguindo com análise.")
            
    except Exception as e:
        if log:
            print(f"[MANDADOS][OUTROS][ERRO] Erro ao verificar cabeçalho: {e}. Criando GIGS fallback.")
        criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
        
        # Verificação de conexão antes do fechamento crítico de aba
        if validar_conexao_driver(driver, contexto="FECHAR_ABA"):
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
            
            # Verificação de conexão antes de executar ações importantes
            if validar_conexao_driver(driver, contexto="ANTES_BNDT"):
                from isolar import BNDT_apagar
                BNDT_apagar(driver)
                
                # Verificar novamente após a primeira ação crítica
                if validar_conexao_driver(driver, contexto="ANTES_DEF_ARQ"):
                    from atos import def_arq
                    def_arq(driver)
                    return None
            else:
                if log:
                    print("[MANDADOS][OUTROS][FATAL] Erro de conexão impediu execução de ações BNDT/def_arq")
                return None
        
        if padrao_positivo:
            if log:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado POSITIVO encontrado no texto.")
            # criar_gigs(driver, dias_uteis=0, observacao='xx positivo', tela='principal')
        elif padrao_negativo:
            if log:
                print("[MANDADOS][OUTROS][LOG] Padrão de mandado NEGATIVO encontrado no texto.")
                # NOVA REGRA: localizar mandado anterior na timeline, extrair conteúdo e, se contiver 'penhora', chamar ato_meios
                autor_ant, elemento_ant = ultimo_mdd(driver, log=log)
                if elemento_ant:
                    # Verificação de conexão antes de interagir com elemento e executar JS
                    if validar_conexao_driver(driver, contexto="ANTES_CLICK_MDD_ANT"):
                        try:
                            link_ant = elemento_ant.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                            # Usar safe_click ao invés de JS direto + click normal
                            safe_click(driver, link_ant)
                            time.sleep(1)
                            
                            # Verificar novamente após a navegação
                            if validar_conexao_driver(driver, contexto="ANTES_EXTRAIR_DOC"):
                                texto_mandado_ant, _ = extrair_documento(driver)
                                if texto_mandado_ant and 'penhora' in texto_mandado_ant.lower():
                                    if log:
                                        print("[MANDADOS][OUTROS][LOG] Mandado anterior contém 'penhora' - chamando ato_meios")
                                    
                                    # Última verificação antes de chamar ato_meios
                                    if validar_conexao_driver(driver, contexto="ANTES_ATO_MEIOS"):
                                        ato_meios(driver)
                        except Exception as e:
                            if log:
                                print(f"[MANDADOS][OUTROS][ERRO] Falha ao processar mandado anterior: {e}")
                            
            # Verificação de conexão antes de continuar
            if not validar_conexao_driver(driver, contexto="DURANTE_ANALISE"):
                if log:
                    print("[MANDADOS][OUTROS][FATAL] Erro de conexão durante análise de mandado negativo")
                return None
            
            # Verifica se contém "penhora de bens" no texto
            if "penhora de bens" in texto_lower:
                if log:
                    print("[MANDADOS][OUTROS][LOG] Texto contém 'penhora de bens' - chamando ato_meios")
                # Substitui checar_conexao_critica por validar_conexao_driver
                if validar_conexao_driver(driver, contexto="ANTES_ATO_MEIOS_2"):
                    ato_meios(driver)
            elif "deixei de penhorar" in texto_lower:
                if log:
                    print("[MANDADOS][OUTROS][LOG] Texto contém 'deixei de penhorar' - chamando ato_meios")
                if validar_conexao_driver(driver, contexto="ANTES_ATO_MEIOS_3"):
                    ato_meios(driver)
            else:
                # Busca último mandado na timeline
                autor, elemento = ultimo_mdd(driver, log=log)
                if autor:
                    if 'silas passos' in autor.lower():
                        if log:
                            print("[MANDADOS][OUTROS][LOG] Último mandado assinado por Silas Passos - chamando ato_edital")
                        if validar_conexao_driver(driver, contexto="ANTES_ATO_EDITAL"):
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
            # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
        return None
    
    # Verificação de conexão antes de extrair o documento
    if not validar_conexao_driver(driver, contexto="ANTES_EXTRAIR"):
        if log:
            print("[MANDADOS][OUTROS][FATAL] Driver em estado inválido antes de extrair documento. Abortando.")
        return
        
    texto, resultado = extrair_documento(driver, regras_analise=analise_padrao)
    if not texto:
        if log:
            print("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return
        
    # Verificação de conexão antes do fechamento crítico de aba
    if validar_conexao_driver(driver, contexto="ANTES_FECHAR_FINAL"):
        try:
            driver.close()
            if log:
                print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
        except Exception as e:
            if log:
                print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e}')
    else:
        if log:
            print('[MANDADOS][OUTROS][ALERTA] Estado do driver inválido, pulando fechamento da aba.')
            
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
    Função principal que coordena todo o fluxo do programa.
    1. Setup inicial (driver e limpeza)
    2. Login humanizado
    3. Navegação para a lista de documentos internos
    4. Execução do fluxo automatizado sobre a lista
    """
    # Setup inicial
    driver = setup_driver()
    if not driver:
        return

    # Login process (agora usando login_pc do Fix.py)
    if not login_func(driver):
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
