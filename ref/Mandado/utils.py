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

# 0. Importações Padrão
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from typing import Optional, Dict, List, Union, Tuple, Callable, Any

# Selenium
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchWindowException,
    StaleElementReferenceException,
)

# Módulos Locais
from Fix import (
    navegar_para_tela,
    extrair_pdf,
    analise_outros,
    extrair_documento,
    criar_gigs,
    esperar_elemento,
    aguardar_e_clicar,
    buscar_seletor_robusto,
    limpar_temp_selenium,
    driver_pc,
    indexar_e_processar_lista,
    extrair_dados_processo,
    buscar_documento_argos,
    buscar_mandado_autor,
    buscar_ultimo_mandado,
    extrair_destinatarios_decisao,
    configurar_recovery_driver,
    verificar_e_tratar_acesso_negado_global,
    handle_exception_with_recovery,
    preencher_campo,
    salvar_destinatarios_cache,
    safe_click,
    wait_for_visible,
    sleep,
)
from Fix.abas import validar_conexao_driver
from Fix.extracao import criar_lembrete_posit
from .atos_wrapper import (
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

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

# ====================================================
# CONTROLE DE SESSÃO E PROGRESSO UNIFICADO
# ====================================================

# Use o monitoramento unificado para extração e marcação de progresso
# Isso garante comportamento idêntico ao usado em p2b.py (validação/formato do número)
from PEC.core import (
    carregar_progresso_pec as carregar_progresso,
    salvar_progresso_pec as salvar_progresso,
    extrair_numero_processo_pec as extrair_numero_processo,
    verificar_acesso_negado_pec as verificar_acesso_negado,
    processo_ja_executado_pec as processo_ja_executado,
    marcar_processo_executado_pec as marcar_processo_executado,
)


def lembrete_bloq(driver: WebDriver, debug: bool = False) -> bool:
    """Wrapper compatível - delegado para criar_lembrete_posit genérico."""
    return criar_lembrete_posit(
        driver,
        titulo="Bloqueio pendente",
        conteudo="processar após IDPJ",
        debug=debug
    )


def _selecionar_checkbox_intimacao(driver: WebDriver, linha: WebElement, log: bool = True) -> bool:
    """Marca o checkbox da linha alvo usando poucas tentativas eficientes."""
    try:
        checkbox_element = linha.find_element(By.CSS_SELECTOR, 'td:last-child div:not([hidden]) mat-checkbox')
        input_checkbox = checkbox_element.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
    except Exception:
        if log:
            print('[INTIMACAO] [5] Checkbox não localizado na linha selecionada')
        return False

    tentativas = (
        lambda: safe_click(driver, checkbox_element, timeout=3, log=False),
        lambda: safe_click(driver, input_checkbox, timeout=3, log=False),
        lambda: driver.execute_script("arguments[0].click();", checkbox_element),
        lambda: driver.execute_script("arguments[0].click();", input_checkbox),
    )

    def marcado() -> bool:
        try:
            return input_checkbox.is_selected()
        except StaleElementReferenceException:
            try:
                novo_input = linha.find_element(By.CSS_SELECTOR, 'td:last-child div:not([hidden]) mat-checkbox input[type="checkbox"]')
                return novo_input.is_selected()
            except Exception:
                return False

    for tentativa in tentativas:
        try:
            tentativa()
            time.sleep(0.3)
            if marcado():
                if log:
                    print('[INTIMACAO] [5] Checkbox marcado com sucesso')
                return True
        except Exception:
            continue

    if log:
        print('[INTIMACAO] [5] Não foi possível marcar o checkbox')
    return False

# ===== FUNÇÃO ANTERIOR (REMOVIDA) =====
# def lembrete_bloq_old(driver, debug=False):
#     """Cria lembrete de bloqueio com título "Bloqueio pendente" e conteúdo "processar após IDPJ"."""
#     # Ver Fix.py > criar_lembrete_posit() para implementação completa

def fechar_intimacao(driver: WebDriver, log: bool = True) -> bool:
    """Fecha a intimação do processo."""
    print('[INTIMACAO] === INÍCIO ===')
    try:
        # 1. Abrir menu
        print('[INTIMACAO] [1] Tentando abrir menu #botao-menu...')
        if not aguardar_e_clicar(driver, '#botao-menu', timeout=10):
            print('[INTIMACAO] [1] ❌ FALHOU: Não conseguiu abrir menu')
            return False
        print('[INTIMACAO] [1] ✓ Menu aberto')
        time.sleep(0.5)
        
        # 2. Clicar Expedientes
        print('[INTIMACAO] [2] Tentando clicar Expedientes...')
        if not aguardar_e_clicar(driver, 'button[aria-label="Expedientes"]', timeout=5):
            print('[INTIMACAO] [2] ❌ FALHOU: Não conseguiu clicar Expedientes')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            return False
        print('[INTIMACAO] [2] ✓ Botão Expedientes clicado')
        
        # 3. Aguardar modal
        print('[INTIMACAO] [3] Aguardando modal abrir...')
        time.sleep(2)
        
        # 4. Buscar linha prazo 30
        print('[INTIMACAO] [4] Buscando linhas com prazo 30...')
        rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
        print(f'[INTIMACAO] [4] Total de linhas encontradas: {len(rows)}')
        
        linha_prazo_30 = None
        
        for i, row in enumerate(rows):
            try:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) >= 11:
                    prazo = cells[8].text.strip()
                    fechado = cells[10].text.strip().lower()
                    print(f'[INTIMACAO] [4] Linha {i+1}: prazo={prazo}, fechado={fechado}')
                    
                    if prazo == '30' and fechado != "sim":
                        linha_prazo_30 = row
                        print(f'[INTIMACAO] [4] ✓ Linha {i+1} válida (prazo 30, não fechado)')
                        break
            except Exception as e:
                print(f'[INTIMACAO] [4] Erro na linha {i+1}: {str(e)[:40]}')
                continue
        
        if not linha_prazo_30:
            print('[INTIMACAO] [4] Nenhuma linha prazo 30 aberta encontrada')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            return True
        
        # 5. Clicar checkbox
        print('[INTIMACAO] [5] Tentando marcar checkbox...')
        if not _selecionar_checkbox_intimacao(driver, linha_prazo_30, log=log):
            print('[INTIMACAO] [5] ❌ Checkbox não foi selecionado')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            return False
        
        # 6. Clicar Fechar Expedientes
        print('[INTIMACAO] [6] Tentando clicar Fechar Expedientes...')
        if not aguardar_e_clicar(driver, 'button[aria-label="Fechar Expedientes"]', timeout=5):
            print('[INTIMACAO] [6] ❌ FALHOU')
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            return False
        print('[INTIMACAO] [6] ✓ Botão clicado')
        time.sleep(1)
        
        # 7. Confirmar
        print('[INTIMACAO] [7] Confirmando com SPACE...')
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
        time.sleep(1)
        
        print('[INTIMACAO] === CONCLUÍDO COM SUCESSO ===')
        return True
        
    except Exception as e:
        print(f'[INTIMACAO] === ERRO GERAL: {str(e)[:150]} ===')
        try:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except:
            pass
        return False

def retirar_sigilo(elemento: WebElement, driver: Optional[WebDriver] = None, debug: bool = False) -> bool:
    """
    ✅ DIRETO E SIMPLES: Verifica tl-nao-sigiloso (AZUL) antes de qualquer ação.
    
    Lógica clara:
    1. Busca botão de sigilo
    2. Se TEM tl-nao-sigiloso (azul) → retorna True (JÁ SEM SIGILO)
    3. Se TEM tl-sigiloso (vermelho) → clica para remover
    4. Caso contrário → retorna True (sem sigilo)
    
    Args:
        elemento: WebElement do documento na timeline
        driver: WebDriver Selenium
        debug: Exibir logs detalhados
    
    Returns:
        True se sigilo foi removido ou já estava removido, False em erro
    """
    import time
    from selenium.webdriver.common.by import By

    if not elemento:
        return False

    if not driver:
        try:
            if hasattr(elemento, '_parent') and hasattr(elemento._parent, 'execute_script'):
                driver = elemento._parent
            else:
                return False
        except Exception:
            return False

    try:
        # Buscar botão de sigilo
        btn_sigilo = None
        seletores = [
            "pje-doc-sigiloso button",
            "pje-doc-sigiloso span button",
            "button i.fa-wpexplorer",
            "i.fa-wpexplorer"
        ]
        
        for seletor in seletores:
            try:
                btn_sigilo = elemento.find_element(By.CSS_SELECTOR, seletor)
                if btn_sigilo.is_displayed():
                    if debug:
                        print(f"[SIGILO_DEBUG] Botão encontrado com seletor: {seletor}")
                    break
                else:
                    btn_sigilo = None
            except Exception:
                continue
        
        # Sem botão = sem sigilo
        if not btn_sigilo:
            if debug:
                print("[SIGILO_DEBUG] Botão não encontrado → SEM SIGILO")
            return True
        
        # ✅ USAR ARIA-LABEL COMO INDICADOR DEFINITIVO
        aria_label = (btn_sigilo.get_attribute("aria-label") or "").lower()
        
        if debug:
            print(f"[SIGILO_DEBUG] Aria-label: {aria_label}")
        
        # ✅ VERIFICAÇÃO DEFINITIVA: aria-label indica o estado
        if "inserir sigilo" in aria_label:
            # Botão para INSERIR = documento JÁ ESTÁ SEM SIGILO
            if debug:
                print("[SIGILO_DEBUG] ✅ Aria-label='Inserir sigilo' → JÁ SEM SIGILO (não clicar!)")
            return True
        
        # ✅ VERIFICAÇÃO: Se aria-label TEM "retirar sigilo" = PRECISA REMOVER
        if "retirar sigilo" in aria_label:
            # TEM "retirar sigilo" no aria-label = SIGILO ATIVO → REMOVER
            if debug:
                print("[SIGILO_DEBUG] ⚠️ Aria-label='Retirar sigilo' → COM SIGILO → CLICANDO...")
        else:
            # Sem aria-label claro = verificar ícone dentro do botão
            try:
                icone = btn_sigilo.find_element(By.CSS_SELECTOR, "i.fa-wpexplorer")
                classes_icone = (icone.get_attribute("class") or "").lower()
                
                if debug:
                    print(f"[SIGILO_DEBUG] Classes do ícone: {classes_icone}")
                
                if 'tl-nao-sigiloso' in classes_icone:
                    if debug:
                        print("[SIGILO_DEBUG] ✅ Ícone tem tl-nao-sigiloso → JÁ SEM SIGILO")
                    return True
                
                if 'tl-sigiloso' not in classes_icone:
                    if debug:
                        print("[SIGILO_DEBUG] Ícone sem tl-sigiloso → SEM SIGILO")
                    return True
                
                # Se chegou aqui e tem tl-sigiloso, vai clicar
                if debug:
                    print("[SIGILO_DEBUG] ⚠️ Ícone tem tl-sigiloso → COM SIGILO → CLICANDO...")
            except Exception as e_icone:
                if debug:
                    print(f"[SIGILO_DEBUG] Erro ao verificar ícone: {e_icone} → considerando SEM SIGILO")
                return True
        
        try:
            driver.execute_script('arguments[0].click();', btn_sigilo)
            time.sleep(0.3)  # Aguardar processamento
            
            # ✅ VERIFICAR se aria-label mudou para "inserir sigilo"
            tentativas = 0
            while tentativas < 5:
                time.sleep(0.2)
                try:
                    novo_aria = (btn_sigilo.get_attribute("aria-label") or "").lower()
                    if "inserir sigilo" in novo_aria:
                        if debug:
                            print("[SIGILO_DEBUG] ✅ Aria-label mudou para 'Inserir sigilo' → Confirmado!")
                        return True
                    tentativas += 1
                except Exception:
                    break
            
            if debug:
                print("[SIGILO_DEBUG] ✅ Clique executado (sem confirmação de mudança)")
            return True
        except Exception as e1:
            if debug:
                print(f"[SIGILO_DEBUG] Erro no clique JS: {e1}")
            try:
                btn_sigilo.click()
                time.sleep(0.8)
                if debug:
                    print("[SIGILO_DEBUG] ✅ Clique direto executado com sucesso")
                return True
            except Exception as e2:
                if debug:
                    print(f"[SIGILO_DEBUG] ❌ Erro no clique direto: {e2}")
                return False
    
    except Exception as e:
        if debug:
            print(f"[SIGILO_DEBUG] ❌ Erro geral: {e}")
        return False

def retirar_sigilo_fluxo_argos(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True, debug: bool = False) -> dict:
    """
    ✅ FUNÇÃO ÚNICA PARA TODO O FLUXO DE REMOÇÃO DE SIGILO DO ARGOS
    
    Respeita a ORDEM OBRIGATÓRIA do fluxo ARGOS:
    1º - Certidão de devolução (PRIMEIRO)
    2º - Demais documentos: certidão expedição, intimação, decisão, planilha
    
    Args:
        driver: WebDriver Selenium
        documentos_sequenciais: Lista de WebElements dos documentos
        log: Exibir logs detalhados
        debug: Ativar modo debug com detalhes das classes CSS
    
    Returns:
        dict com status de cada etapa e documentos processados
    """
    if not documentos_sequenciais:
        if log:
            print("[SIGILO_ARGOS] Nenhum documento fornecido")
        return {'sucesso': False, 'etapa_erro': 'nenhum_documento'}
    
    resultado = {
        'sucesso': True,
        'certidao_devolucao': None,
        'demais_documentos': [],
        'total_processados': 0
    }
    
    if log:
        print(f"[SIGILO_ARGOS] Iniciando remoção de sigilo de {len(documentos_sequenciais)} documentos")
        print("[SIGILO_ARGOS] Ordem: 1º Certidão Devolução → 2º Demais Documentos")
    
    # =======================================================
    # ETAPA 1: CERTIDÃO DE DEVOLUÇÃO (PRIMEIRO!)
    # =======================================================
    if log:
        print("[SIGILO_ARGOS][1/2] Processando certidão de devolução...")
    
    certidao_encontrada = None
    for doc in reversed(documentos_sequenciais):
        texto = doc.text.strip().lower()
        if "certidão de devolução" in texto or "certidao de devolucao" in texto:
            certidao_encontrada = doc
            if log:
                print(f"[SIGILO_ARGOS][1/2] ✅ Certidão encontrada: {texto[:50]}...")
            break
    
    if not certidao_encontrada:
        if log:
            print("[SIGILO_ARGOS][1/2] ⚠️ Certidão de devolução não encontrada - pulando")
        resultado['certidao_devolucao'] = {'status': 'nao_encontrada'}
    else:
        # Verificar se tem sigilo
        links_doc = certidao_encontrada.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
        tem_sigilo = False
        
        if links_doc:
            link_correto = None
            for link in links_doc:
                target = link.get_attribute('target') or ''
                role = link.get_attribute('role') or ''
                if role == 'button' or target != '_blank':
                    link_correto = link
                    break
            
            if not link_correto and links_doc:
                link_correto = links_doc[-1]
            
            if link_correto:
                classes_link = (link_correto.get_attribute('class') or '')
                tem_sigilo = 'is-sigiloso' in classes_link
        
        if not tem_sigilo:
            if log:
                print("[SIGILO_ARGOS][1/2] ✅ Certidão JÁ SEM SIGILO")
            resultado['certidao_devolucao'] = {'status': 'ja_sem_sigilo'}
        else:
            if log:
                print("[SIGILO_ARGOS][1/2] Removendo sigilo da certidão...")
            if retirar_sigilo(certidao_encontrada, driver, debug=debug):
                if log:
                    print("[SIGILO_ARGOS][1/2] ✅ Sigilo removido com sucesso")
                resultado['certidao_devolucao'] = {'status': 'removido'}
                resultado['total_processados'] += 1
            else:
                if log:
                    print("[SIGILO_ARGOS][1/2] ❌ Falha ao remover sigilo")
                resultado['certidao_devolucao'] = {'status': 'erro'}
                resultado['sucesso'] = False
    
    # =======================================================
    # ETAPA 2: DEMAIS DOCUMENTOS ESPECÍFICOS (DENTRO DO BLOCO)
    # =======================================================
    if log:
        print("[SIGILO_ARGOS][2/2] Processando demais documentos...")
    
    # ✅ BLOCO COMPLETO:
    # Índice 0: Certidão devolução (mais recente)
    # Índices 1, 2, 3: Documentos do meio (certidão expedição, intimação, planilha)
    # Índice 4: Decisão (mais antiga)
    
    tipos_especificos = {
        'certidao_expedicao': {
            'palavras': ['certidão de expedição', 'certidao de expedicao'],
            'limite': 1,
            'encontrados': []
        },
        'intimacao': {
            'palavras': ['intimação(', 'intimacao('],
            'limite': 1,
            'encontrados': []
        },
        'decisao': {
            'palavras': ['decisão(', 'decisao('],
            'limite': 1,
            'encontrados': []
        },
        'planilha': {
            'palavras': ['planilha de atualização', 'planilha de atualizacao'],
            'limite': 1,
            'encontrados': []
        }
    }
    
    # Encontrar onde está a decisão (fim do bloco)
    idx_decisao = None
    for idx in range(len(documentos_sequenciais)):
        texto = documentos_sequenciais[idx].text.strip().lower()
        if "decisão(" in texto or "decisao(" in texto:
            idx_decisao = idx
            if debug:
                print(f"[SIGILO_ARGOS][DEBUG] Decisão no índice {idx} - FIM DO BLOCO")
            break
    
    if idx_decisao is None:
        if log:
            print("[SIGILO_ARGOS][2/2] ⚠️ Decisão não encontrada")
        return resultado
    
    # Processar índices 1, 2, 3... até ANTES da decisão
    if debug:
        print(f"[SIGILO_ARGOS][DEBUG] Processando índices 1 até {idx_decisao - 1}")
    
    for idx in range(1, idx_decisao):
        doc = documentos_sequenciais[idx]
        texto = doc.text.strip().lower()
        
        if debug:
            print(f"[SIGILO_ARGOS][DEBUG] Índice {idx}: {texto[:80]}")
        
        for tipo_nome, tipo_config in tipos_especificos.items():
            if len(tipo_config['encontrados']) >= tipo_config['limite']:
                continue
            
            for palavra in tipo_config['palavras']:
                if palavra in texto:
                    if debug:
                        print(f"[SIGILO_ARGOS][DEBUG] ✅ {tipo_nome.upper()}: {texto[:80]}")
                    tipo_config['encontrados'].append({
                        'elemento': doc,
                        'texto': texto[:50],
                        'palavra': palavra
                    })
                    break
    
    # Adicionar decisão (índice 4 - fim do bloco)
    doc_decisao = documentos_sequenciais[idx_decisao]
    texto_decisao = doc_decisao.text.strip().lower()
    if debug:
        print(f"[SIGILO_ARGOS][DEBUG] Adicionando decisão (índice {idx_decisao}): {texto_decisao[:80]}")
    tipos_especificos['decisao']['encontrados'].append({
        'elemento': doc_decisao,
        'texto': texto_decisao[:50],
        'palavra': 'decisão'
    })
    
    # Remover sigilo dos demais documentos
    for tipo_nome, tipo_config in tipos_especificos.items():
        if not tipo_config['encontrados']:
            continue
        
        for doc_info in tipo_config['encontrados']:
            elemento = doc_info['elemento']
            texto = doc_info['texto']
            
            # Verificar se tem sigilo
            links_doc = elemento.find_elements(By.CSS_SELECTOR, 'a.tl-documento')
            tem_sigilo = False
            
            if links_doc:
                link_correto = None
                for link in links_doc:
                    target = link.get_attribute('target') or ''
                    role = link.get_attribute('role') or ''
                    if role == 'button' or target != '_blank':
                        link_correto = link
                        break
                
                if not link_correto and links_doc:
                    link_correto = links_doc[-1]
                
                if link_correto:
                    classes_link = (link_correto.get_attribute('class') or '')
                    tem_sigilo = 'is-sigiloso' in classes_link
                    
                    if debug:
                        print(f"[SIGILO_ARGOS][DEBUG] {tipo_nome.upper()} - Classes link: {classes_link}")
                        print(f"[SIGILO_ARGOS][DEBUG] {tipo_nome.upper()} - tem_sigilo: {tem_sigilo}")
            
            if not tem_sigilo:
                if log:
                    print(f"[SIGILO_ARGOS][2/2] {tipo_nome.upper()}: JÁ SEM SIGILO - {texto}")
                resultado['demais_documentos'].append({
                    'tipo': tipo_nome,
                    'texto': texto,
                    'status': 'ja_sem_sigilo'
                })
            else:
                if log:
                    print(f"[SIGILO_ARGOS][2/2] {tipo_nome.upper()}: Removendo sigilo...")
                if retirar_sigilo(elemento, driver, debug=debug):
                    if log:
                        print(f"[SIGILO_ARGOS][2/2] {tipo_nome.upper()}: ✅ Removido")
                    resultado['demais_documentos'].append({
                        'tipo': tipo_nome,
                        'texto': texto,
                        'status': 'removido'
                    })
                    resultado['total_processados'] += 1
                else:
                    if log:
                        print(f"[SIGILO_ARGOS][2/2] {tipo_nome.upper()}: ❌ Erro")
                    resultado['demais_documentos'].append({
                        'tipo': tipo_nome,
                        'texto': texto,
                        'status': 'erro'
                    })
                    resultado['sucesso'] = False
    
    if log:
        print(f"[SIGILO_ARGOS] ✅ Concluído: {resultado['total_processados']} documentos processados")
    
    return resultado

# Manter aliases para compatibilidade com código existente
def retirar_sigilo_certidao_devolucao_primeiro(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True) -> bool:
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna apenas status da certidão."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    cert_status = resultado.get('certidao_devolucao', {}).get('status', 'erro')
    return cert_status in ['removido', 'ja_sem_sigilo', 'nao_encontrada']

def retirar_sigilo_demais_documentos_especificos(driver, documentos_sequenciais, log=True):
    """COMPATIBILIDADE: Chama retirar_sigilo_fluxo_argos e retorna lista de demais documentos."""
    resultado = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log)
    return resultado.get('demais_documentos', [])

def retirar_sigilo_documentos_especificos(driver, documentos_sequenciais, log=True):
    """
    ✅ FUNÇÃO EFICIENTE - Remove sigilo APENAS dos documentos específicos fornecidos:
    Os documentos_sequenciais já vêm filtrados da buscar_documentos_sequenciais()
    MÁXIMO 5 documentos: 1 certidão devolução, 1 certidão expedição, 1 intimação, 1 decisão, 1 planilha
    
    NADA MAIS que isso - SEM VARRER TIMELINE INTEIRA!
    """
    if not documentos_sequenciais:
        if log:
            print("[SIGILO_ESPECÍFICO] Nenhum documento sequencial fornecido")
        return []
    
    # ✅ EFICIÊNCIA: Os documentos já vêm filtrados, apenas remover sigilo diretamente
    if log:
        print(f"[SIGILO_ESPECÍFICO] Processando {len(documentos_sequenciais)} documentos específicos (PRÉ-FILTRADOS)")
    
    documentos_processados = []
    total_processados = 0
    
    # ✅ PROCESSAMENTO DIRETO: Remove sigilo apenas dos documentos fornecidos
    for i, elemento in enumerate(documentos_sequenciais):
        try:
            texto = elemento.text.strip()[:50] if elemento.text else f"DOCUMENTO_{i+1}"
            
            if log:
                print(f"[SIGILO_ESPECÍFICO] [{i+1}/{len(documentos_sequenciais)}] Removendo sigilo: {texto}...")
            
            resultado_sigilo = retirar_sigilo(elemento, driver)
            
            if resultado_sigilo:
                if log:
                    print(f"[SIGILO_ESPECÍFICO] ✅ Sigilo removido: {texto}")
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'sucesso'
                })
                total_processados += 1
            else:
                if log:
                    print(f"[SIGILO_ESPECÍFICO] ⚠️ Falha ao remover sigilo: {texto}")
                documentos_processados.append({
                    'indice': i+1,
                    'texto': texto,
                    'status': 'falha'
                })
                
        except Exception as e:
            if log:
                print(f"[SIGILO_ESPECÍFICO] ❌ Erro ao processar documento {i+1}: {e}")
            documentos_processados.append({
                'indice': i+1,
                'texto': texto if 'texto' in locals() else f"DOCUMENTO_{i+1}",
                'status': 'erro',
                'erro': str(e)
            })
    
    # ✅ RELATÓRIO FINAL
    if log:
        print(f"\n[SIGILO_ESPECÍFICO] ===== RELATÓRIO FINAL =====")
        print(f"[SIGILO_ESPECÍFICO] Total processados: {total_processados}/{len(documentos_sequenciais)}")
        print(f"[SIGILO_ESPECÍFICO] Documentos processados:")
        
        for doc in documentos_processados:
            status_icon = "✅" if doc['status'] == 'sucesso' else "❌" if doc['status'] == 'erro' else "⚠️"
            print(f"[SIGILO_ESPECÍFICO]   {status_icon} DOC {doc['indice']}: {doc['texto']}")
        
        print(f"[SIGILO_ESPECÍFICO] =============================\n")
    
    return documentos_processados

