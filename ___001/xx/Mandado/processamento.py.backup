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

# ===== IMPORTS PESADOS REMOVIDOS (LAZY LOADING) =====
# Movidos para cache sob demanda para carregamento 8-10x mais rápido
# Anteriormente importados do Fix e outros módulos no topo
# Agora cada função importa apenas o que precisa, quando precisa

# Cache de módulos para lazy loading
_mandado_modules_cache = {}

def _lazy_import_mandado():
    """Carrega módulos pesados sob demanda (lazy loading)."""
    global _mandado_modules_cache
    
    if not _mandado_modules_cache:
        from Fix import (
            navegar_para_tela,
            extrair_pdf,
            analise_outros,
            extrair_documento,
            extrair_direto,
            criar_gigs,
            esperar_elemento,
            aguardar_e_clicar,
            buscar_seletor_robusto,
            limpar_temp_selenium,
            indexar_e_processar_lista,
            extrair_dados_processo,
            buscar_mandado_autor,
            buscar_ultimo_mandado,
            extrair_destinatarios_decisao,
            configurar_recovery_driver,
        )
        
        _mandado_modules_cache.update({
            'navegar_para_tela': navegar_para_tela,
            'extrair_pdf': extrair_pdf,
            'analise_outros': analise_outros,
            'extrair_documento': extrair_documento,
            'extrair_direto': extrair_direto,
            'criar_gigs': criar_gigs,
            'esperar_elemento': esperar_elemento,
            'aguardar_e_clicar': aguardar_e_clicar,
            'buscar_seletor_robusto': buscar_seletor_robusto,
            'limpar_temp_selenium': limpar_temp_selenium,
            'indexar_e_processar_lista': indexar_e_processar_lista,
            'extrair_dados_processo': extrair_dados_processo,
            'buscar_mandado_autor': buscar_mandado_autor,
            'buscar_ultimo_mandado': buscar_ultimo_mandado,
            'extrair_destinatarios_decisao': extrair_destinatarios_decisao,
            'configurar_recovery_driver': configurar_recovery_driver,
        })
    
    return _mandado_modules_cache

# Módulos Locais (mantidos leves)
from Fix import (
    verificar_e_tratar_acesso_negado_global,
    handle_exception_with_recovery,
    preencher_campo,
    salvar_destinatarios_cache,
    buscar_documentos_sequenciais,
)
from Fix.core import buscar_documento_argos
from Fix.abas import validar_conexao_driver
from Fix.extracao import criar_lembrete_posit, extrair_pdf
from Fix.log import logger
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
from .utils import (
    fechar_intimacao,
    retirar_sigilo,
    retirar_sigilo_fluxo_argos,
    retirar_sigilo_certidao_devolucao_primeiro,
    retirar_sigilo_demais_documentos_especificos,
)
from .regras import aplicar_regras_argos

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

# ====================================================
# ETAPA 2: TRATAR ANEXOS ARGOS (Refatorado)
# ====================================================

# Constantes
_SIGILO_TYPES = [
    "infojud", "doi", "irpf", "ir2022", "ir2023", "ir2024", "ir2025", "ir2026",
    "ir 2023", "ir 2024", "ir 2025", "ir 2026", "ir23", "ir24", "ir25", "ir26",
    "dimob", "ecac", "efinanceira", "e-financeira", "decred", "DEC9"
]

_SELETORES_ANEXOS = {
    'btn_anexos': 'pje-timeline-anexos > div > div',
    'anexos': '.tl-item-anexo',
    'btn_sigilo': 'i.fa-wpexplorer',
    'icone_plus': 'i.fas.fa-plus.tl-sigiloso',
    'modal_container': '.cdk-overlay-container .mat-dialog-container',
    'checkbox': 'mat-checkbox',
    'btn_salvar': ".//div[@mat-dialog-actions]//button[contains(., 'Salvar')]",
    'selecionar_todos': 'i.fa.fa-check.botao-icone-titulo-coluna'
}

def _identificar_tipo_anexo(texto: str) -> Optional[str]:
    """Identifica tipo de anexo especial."""
    import re
    texto_lower = texto.strip().lower()
    for tipo in _SIGILO_TYPES:
        if tipo == "DEC9":
            if re.search(r"dec\d{9}", texto_lower):
                return tipo
        elif tipo in texto_lower:
            return tipo
    return None



def _aguardar_icone_plus(elemento: WebElement, tentativas: int = 8, log: bool = True) -> Optional[WebElement]:
    """Aguarda ícone + aparecer após aplicar sigilo."""
    for i in range(tentativas):
        try:
            icons = elemento.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['icone_plus'])
            if icons:
                icon_classes = icons[0].get_attribute("class") or ""
                if "fa-plus" in icon_classes and "tl-sigiloso" in icon_classes:
                    btn = icons[0].find_element(By.XPATH, "./ancestor::button[1]")
                    if btn.is_displayed() and btn.is_enabled():
                        if log:
                            print(f"[VISIBILIDADE] ✅ Ícone + validado após {i+1} tentativas")
                        return btn
            time.sleep(0.3)
        except Exception:
            time.sleep(0.3)
    return None

def _buscar_icone_plus_direto(elemento: WebElement, log: bool = True) -> Optional[WebElement]:
    """Busca ícone + diretamente (quando sigilo já existe)."""
    try:
        icons = elemento.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['icone_plus'])
        if not icons:
            return None
        icon_classes = icons[0].get_attribute("class") or ""
        if "fa-plus" in icon_classes and "tl-sigiloso" in icon_classes:
            btn = icons[0].find_element(By.XPATH, "./ancestor::button[1]")
            if btn.is_displayed() and btn.is_enabled():
                if log:
                    print(f"[VISIBILIDADE] ✅ Ícone + encontrado diretamente")
                return btn
        return None
    except Exception:
        return None

def _localizar_modal_visibilidade(driver: WebDriver, timeout: int = 4) -> Optional[WebElement]:
    """Localiza modal de visibilidade com espera ativa."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException
    try:
        def _buscar_modal(drv):
            candidatos = drv.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['modal_container'])
            for modal in candidatos:
                try:
                    modal_html = modal.get_attribute('innerHTML') or ''
                except Exception:
                    continue
                if 'Visibilidade de Sigilo de Documento' in modal_html and 'Atribuir às partes' in modal_html:
                    return modal
            return False
        return WebDriverWait(driver, timeout, poll_frequency=0.1).until(_buscar_modal)
    except TimeoutException:
        return None

## Mantido comportamento original do p2b: não adicionar wrappers adicionais aqui.

def _processar_modal_visibilidade(driver: WebDriver, modal: WebElement, log: bool = True) -> bool:
    """Processa modal: seleciona checkboxes e salva."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    try:
        time.sleep(0.12)
        # STEP 1: Tentar "Selecionar Todos"
        selecionar_todos_ok = False
        try:
            icone = modal.find_element(By.CSS_SELECTOR, _SELETORES_ANEXOS['selecionar_todos'])
            driver.execute_script("arguments[0].click();", icone)
            time.sleep(0.15)
            selecionar_todos_ok = True
            if log:
                print(f"[MODAL] ✅ Selecionar Todos clicado")
        except Exception:
            if log:
                print(f"[MODAL] Tentando checkboxes individuais")
        # STEP 2: Se falhou, checkboxes individuais
        if not selecionar_todos_ok:
            checkboxes = modal.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['checkbox'])
            for checkbox in checkboxes:
                try:
                    checkbox_input = checkbox.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    if not checkbox_input.is_selected():
                        driver.execute_script("arguments[0].click();", checkbox)
                        time.sleep(0.1)
                except Exception:
                    continue
        # STEP 3: Salvar
        time.sleep(0.08)
        btn_salvar = modal.find_element(By.XPATH, _SELETORES_ANEXOS['btn_salvar'])
        if not (btn_salvar.is_displayed() and btn_salvar.is_enabled()):
            return False
        driver.execute_script("arguments[0].click();", btn_salvar)
        # STEP 4: Verificar fechamento
        try:
            WebDriverWait(driver, 4, poll_frequency=0.1).until(EC.staleness_of(modal))
            time.sleep(0.05)
            if log:
                print(f"[MODAL] ✅ Modal fechado")
            return True
        except TimeoutException:
            return False
    except Exception as e:
        if log:
            print(f"[MODAL][ERRO] {e}")
        return False

def _extrair_resultado_sisbajud(texto_documento: str, log: bool = True) -> tuple:
    """Extrai resultado SISBAJUD do texto do documento."""
    if not texto_documento:
        return (None, 'Documento vazio')
    
    # Procurar por marcador SISBAJUD no texto
    texto_lower = texto_documento.lower()
    sisbajud_idx = texto_lower.find('sisbajud')
    
    if sisbajud_idx == -1:
        return (None, 'Marcador SISBAJUD não encontrado')
    
    # Extrair trecho após SISBAJUD para análise
    trecho_apos_sisbajud = texto_documento[sisbajud_idx:sisbajud_idx + 500]  # 500 chars após SISBAJUD
    lines = trecho_apos_sisbajud.splitlines()
    
    for line in lines[1:]:  # Pular a linha que contém SISBAJUD
        result_line = line.strip().lower()
        if not result_line:
            continue
        if 'negativo' in result_line:
            return ('negativo', 'linha contém "negativo"')
        elif 'positivo' in result_line:
            return ('positivo', 'linha contém "positivo"')
        else:
            # Tentar extrair valor numérico
            valor = result_line.replace('r$', '').replace(' ', '').replace('.', '').replace(',', '.').replace('-', '')
            try:
                value = float(''.join([c for c in valor if c.isdigit() or c == '.']))
                if value == 0:
                    return ('negativo', 'valor numérico == 0')
                else:
                    return ('positivo', 'valor numérico > 0')
            except Exception:
                continue
    
    return (None, 'Nenhuma regra aplicada')

def _extrair_executados_pdf(texto_documento: str) -> List[Dict[str, str]]:
    """Extrai lista de executados do texto do documento."""
    import re
    if not texto_documento:
        return []
    
    lines = texto_documento.splitlines()
    executados = []
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
    return executados

def processar_sisbajud(texto_pdf: str, log: bool = True) -> tuple[str, str, list]:
    """
    ✅ ANÁLISE SISBAJUD: Sempre processa usando o texto extraído (texto_pdf).

    Não busca SISBAJUD em anexos, apenas analisa o texto recebido.
    """
    # ...existing code for análise do texto_pdf...
    lines = texto_pdf.splitlines()
    det_idx = -1
    for idx, line in enumerate(lines):
        if 'determinações normativas e legais' in line.lower():
            det_idx = idx
            break
    if det_idx == -1:
        raise ValueError('[SISBAJUD][ERRO] Marcador "determinações normativas e legais" não encontrado no texto')
    executados = _extrair_executados_pdf(texto_pdf)
    bloqueio_idx = -1
    for offset in range(1, 21):
        if det_idx + offset >= len(lines):
            break
        result_line = lines[det_idx + offset].strip().lower()
        if not result_line:
            continue
        if log:
            logger.debug(f'[SISBAJUD][DEBUG] Checking line after determinações normativas e legais: {repr(result_line)}')
        if 'bloqueio de valores' in result_line:
            bloqueio_idx = det_idx + offset
            if log:
                logger.debug(f'[SISBAJUD][DEBUG] Found "Bloqueio de valores" at line {bloqueio_idx}')
            break
    if bloqueio_idx == -1:
        if log:
            logger.debug('[SISBAJUD][DEBUG] "Bloqueio de valores" not found after determinações normativas e legais')
        return 'negativo', 'Bloqueio de valores não encontrado, sem SISBAJUD', executados
    for offset in range(1, 15):
        if bloqueio_idx + offset >= len(lines):
            break
        sisbajud_line = lines[bloqueio_idx + offset].strip().lower()
        if not sisbajud_line:
            continue
        if log:
            logger.debug(f'[SISBAJUD][DEBUG] Checking line after Bloqueio de valores: {repr(sisbajud_line)}')
        if 'sisbajud' in sisbajud_line:
            if log:
                logger.debug(f'[SISBAJUD][DEBUG] Found SISBAJUD marker at line')
            for sib_offset in range(1, 5):
                if bloqueio_idx + offset + sib_offset >= len(lines):
                    break
                resultado_line = lines[bloqueio_idx + offset + sib_offset].strip().lower()
                if not resultado_line:
                    continue
                if log:
                    logger.debug(f'[SISBAJUD][DEBUG] Checking SISBAJUD result line: {repr(resultado_line)}')
                if 'negativo' in resultado_line:
                    if log:
                        logger.debug('[SISBAJUD][DEBUG] Found "Negativo" in SISBAJUD section')
                    return 'negativo', 'SISBAJUD Negativo na seção Bloqueio de valores', executados
                elif 'positivo' in resultado_line:
                    if log:
                        logger.debug('[SISBAJUD][DEBUG] Found "Positivo" in SISBAJUD section')
                    return 'positivo', 'SISBAJUD Positivo na seção Bloqueio de valores', executados
            if log:
                logger.debug('[SISBAJUD][DEBUG] Found SISBAJUD but no explicit result, analyzing context and value')
            valor_encontrado = 0
            for check_offset in range(1, 10):
                if bloqueio_idx + offset + check_offset >= len(lines):
                    break
                check_line = lines[bloqueio_idx + offset + check_offset].strip().lower()
                if not check_line:
                    continue
                import re
                valor_match = re.search(r'r\$\s*([\d.,]+)', check_line)
                if valor_match:
                    valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
                    try:
                        valor_encontrado = float(valor_str)
                        if log:
                            logger.debug(f'[SISBAJUD][DEBUG] Found value: R$ {valor_str} = {valor_encontrado}')
                        break
                    except ValueError:
                        continue
            if valor_encontrado > 0:
                return 'positivo', f'SISBAJUD com valor positivo: R$ {valor_encontrado:.2f}', executados
            else:
                return 'negativo', f'SISBAJUD sem valor ou valor zero encontrado', executados
    if log:
        logger.debug('[SISBAJUD][DEBUG] SISBAJUD marker not found after determinações normativas e legais, default negativo.')
    return 'negativo', 'SISBAJUD não encontrado na seção Bloqueio de valores', executados


# `buscar_documento_argos` fica no módulo `Fix` (manter implementação no local de origem).
# Use `from Fix import buscar_documento_argos` conforme já declarado nas importações.

def tratar_anexos_argos(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True) -> Optional[Dict]:
    """
    ✅ ETAPA 2 DO FLUXO ARGOS - Processar anexos sigilosos e extrair SISBAJUD
    
    Sequência correta conforme m1.py:
    1. Abrir anexos
    2. Processar sigilo + visibilidade da lista infojud, doi, irpf, etc.
    3. Extrair SISBAJUD
    4. Aplicar regras adicionais
    """
    if log:
        print('[ARGOS][ANEXOS] Processando anexos...')
    if not documentos_sequenciais:
        if log:
            print('[ARGOS][ANEXOS][ERRO] Nenhum documento sequencial fornecido')
        return None
    
    # ABRIR ANEXOS (JavaScript direto - ignora overlay de DOM)
    doc = documentos_sequenciais[0]
    btn_anexos = doc.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['btn_anexos'])
    if btn_anexos:
        try:
            # JavaScript direto (ignora bloqueios de z-index/overlay)
            driver.execute_script("arguments[0].click();", btn_anexos[0])
            if log:
                print('[ARGOS][ANEXOS] ✅ Anexos abertos')
            time.sleep(2)
        except Exception as e:
            if log:
                print(f'[ARGOS][ANEXOS][ERRO] Falha ao abrir anexos: {e}')
            return None
    
    anexos = driver.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['anexos'])
    tem_anexos = len(anexos) > 0
    
    if not anexos:
        if log:
            print('[ARGOS][ANEXOS] ❌ Nenhum anexo encontrado')
    else:
        if log:
            print(f'[ARGOS][ANEXOS] ✅ {len(anexos)} anexos encontrados')
    
    # INICIALIZAR TRACKING
    found_sigilo = {k: False for k in _SIGILO_TYPES}
    sigilo_anexos = {k: "nao" for k in _SIGILO_TYPES}
    any_sigilo = False
    executados = []
    resultado_sisbajud = None
    
    # === FASE 1: PROCESSAR SIGILO + VISIBILIDADE SEQUENCIALMENTE ===
    if log:
        print('[ARGOS][ANEXOS] === FASE SIGILO + VISIBILIDADE ===')
    
    anexos_processados = 0
    
    # Processar cada anexo sequencialmente: apenas ícones de sigilo e visibilidade
    for anexo in anexos:
        texto_anexo = anexo.text.strip()
        tipo = _identificar_tipo_anexo(texto_anexo)
        if not tipo:
            continue
        
        found_sigilo[tipo] = True
        
        # 1. Detectar estado de sigilo pelo ícone de sigilo (robusto)
        btn_sigilo = anexo.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['btn_sigilo'])
        tem_sigilo = False
        try:
            # Checar ícone específico usado por retirar_sigilo(): pje-doc-sigiloso span button i.fa-wpexplorer
            icons = anexo.find_elements(By.CSS_SELECTOR, 'pje-doc-sigiloso span button i.fa-wpexplorer')
            if icons:
                classes = icons[0].get_attribute("class") or ""
                if "tl-sigiloso" in classes:
                    tem_sigilo = True
        except Exception:
            tem_sigilo = False

        sigilo_foi_aplicado = False
        # Se o documento já estiver sigiloso, NÃO aplicar sigilo (ação seria retirar)
        if not tem_sigilo:
            # Clicar apenas no ícone de sigilo, não no anexo (somente se o ícone existir)
            try:
                if btn_sigilo and len(btn_sigilo) > 0:
                    driver.execute_script("arguments[0].click();", btn_sigilo[0])
                    time.sleep(0.5)
                    sigilo_foi_aplicado = True
                    sigilo_anexos[tipo] = "sim"
                    if log:
                        print(f'[ARGOS][ANEXOS] ✅ Sigilo aplicado em {tipo.upper()}')
                else:
                    if log:
                        print(f'[ARGOS][ANEXOS] ⚠️ Ícone de sigilo não encontrado para {tipo.upper()} - pulando')
                    continue
            except Exception as e:
                if log:
                    print(f'[ARGOS][ANEXOS] ❌ Erro ao aplicar sigilo em {tipo.upper()}: {e}')
                continue
        else:
            sigilo_anexos[tipo] = "sim"
        
        # 2. Aplicar visibilidade apenas clicando no ícone + (sem clicar no anexo)
        if sigilo_foi_aplicado or tem_sigilo:
            try:
                # Buscar e clicar apenas no ícone + do anexo atual
                icone_plus = anexo.find_element(By.CSS_SELECTOR, _SELETORES_ANEXOS['icone_plus'])
                driver.execute_script("arguments[0].click();", icone_plus)
                time.sleep(1.5)  # AUMENTADO: Espera adequada para modal abrir completamente
                
                # Processar modal de visibilidade com verificação robusta
                modal = _localizar_modal_visibilidade(driver, timeout=6)  # AUMENTADO timeout
                if modal:
                    # Verificação adicional: aguardar modal estar totalmente carregado
                    time.sleep(0.8)  # Espera extra para estabilização
                    
                    modal_ok = _processar_modal_visibilidade(driver, modal, log=False)
                    if modal_ok:
                        any_sigilo = True
                        anexos_processados += 1
                        if log:
                            print(f'[ARGOS][ANEXOS] ✅ {tipo.upper()} processado (visibilidade aplicada)')
                        
                        # Espera adicional após processamento bem-sucedido
                        time.sleep(0.5)
                    else:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(1.5)  # AUMENTADO espera após ESCAPE
                else:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(1.5)  # AUMENTADO espera após ESCAPE
                    
            except Exception as e:
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                except Exception:
                    pass
                continue
    
    # LOG: Quantos anexos foram tratados
    if log:
        print(f'[ARGOS][ANEXOS] ✅ {anexos_processados} anexos processados (sigilo + visibilidade)')
        print(f'[ARGOS][ANEXOS] === FASE SISBAJUD ===')
    
    # === FASE 2: PROCESSAR SISBAJUD ===
    try:
        if log:
            print('[ARGOS][ANEXOS][SISBAJUD] Procurando documento SISBAJUD...')
        
        documento_sisbajud = None
        for anexo in anexos:
            texto = anexo.text.strip()
            if "Certidão de devolução de ordem de pesquisa patrimonial" in texto:
                documento_sisbajud = anexo
                if log:
                    print(f'[ARGOS][ANEXOS][SISBAJUD] ✅ Documento SISBAJUD encontrado: {texto[:50]}...')
                break
        
        if not documento_sisbajud:
            if log:
                print('[ARGOS][ANEXOS][SISBAJUD] ❌ Nenhum documento SISBAJUD encontrado nos anexos')
        else:
            if log:
                print('[ARGOS][ANEXOS][SISBAJUD] Clicando no documento SISBAJUD...')
            documento_sisbajud.click()
            time.sleep(1)
            if log:
                print('[ARGOS][ANEXOS][SISBAJUD] ✅ Documento SISBAJUD clicado, aguardando carregamento...')
    except Exception as e:
        if log:
            print(f'[ARGOS][ANEXOS][SISBAJUD][ERRO] Falha ao localizar/clicar documento SISBAJUD: {e}')
        pass
    
    if log:
        print('[ARGOS][ANEXOS][SISBAJUD] Extraindo texto do documento...')
    
    texto_pdf = extrair_pdf(driver, log=False)
    if texto_pdf:
        if log:
            print(f'[ARGOS][ANEXOS][SISBAJUD] ✅ Texto extraído com sucesso ({len(texto_pdf)} caracteres)')
            # Mostrar preview do texto
            preview = texto_pdf[:200].replace('\n', ' ').strip()
            print(f'[ARGOS][ANEXOS][SISBAJUD] Preview: {preview}...')
    else:
        texto_pdf = None
        if log:
            print(f'[ARGOS][ANEXOS][SISBAJUD] ❌ Falha na extração do texto')
    
    if texto_pdf:
        if log:
            print('[ARGOS][ANEXOS][SISBAJUD] Extraindo lista de executados...')
        executados = _extrair_executados_pdf(texto_pdf)
        if log:
            print(f'[ARGOS][ANEXOS][SISBAJUD] ✅ {len(executados)} executados encontrados')
            if executados:
                for i, exec_data in enumerate(executados[:3]):  # Mostrar até 3 primeiros
                    print(f'[ARGOS][ANEXOS][SISBAJUD]   {i+1}. {exec_data.get("nome", "N/A")} - {exec_data.get("documento", "N/A")}')
                if len(executados) > 3:
                    print(f'[ARGOS][ANEXOS][SISBAJUD]   ... e mais {len(executados)-3} executados')
        
        if log:
            print('[ARGOS][ANEXOS][SISBAJUD] Analisando resultado SISBAJUD...')
        try:
            resultado_sisbajud, motivo, executados = processar_sisbajud(texto_pdf, log=False)
            # Log limpo: apenas SISBAJUD POSITIVO/NEGATIVO com valor detectado
            if resultado_sisbajud == 'positivo':
                valor_detectado = motivo.split('R$ ')[-1] if 'R$ ' in motivo else ''
                print(f'SISBAJUD POSITIVO {valor_detectado}')
            elif resultado_sisbajud == 'negativo':
                print(f'SISBAJUD NEGATIVO')
            # Log de executados: apenas quantidade
            if len(executados) == 1:
                print('executadas: UMA')
            elif len(executados) > 1:
                print('executadas: MAIS DE UMA')
        except ValueError as ve:
            # Erro da função SISBAJUD - reportar no log
            print(f'[SISBAJUD][ERRO] {ve}')
            resultado_sisbajud = None
            executados = []
        except Exception as e:
            # Qualquer outro erro - reportar como erro da função
            print(f'[SISBAJUD][ERRO] Erro na análise SISBAJUD: {e}')
            resultado_sisbajud = None
            executados = []
    else:
        executados = []
        resultado_sisbajud = None
        if log:
            print('[ARGOS][ANEXOS][SISBAJUD] ❌ Sem texto para análise, pulando extração')
    
    # === RETORNO ===
    if log:
        status_sisbajud = resultado_sisbajud if resultado_sisbajud else f"SEM SISBAJUD ({motivo})"
        print(f'[ARGOS][ANEXOS] SISBAJUD: {status_sisbajud}')
        print(f'[ARGOS][ANEXOS] Executados: {len(executados)}')
        print(f'[ARGOS][ANEXOS] Sigiloso: {any_sigilo}')
    
    return {
        'executados': executados,
        'resultado_sisbajud': resultado_sisbajud,
        'found_sigilo': found_sigilo,
        'sigilo_anexos': sigilo_anexos,
        'sigiloso': any_sigilo,
        'tem_anexos': tem_anexos
    }

# ====================================================
# PROCESSAMENTO PRINCIPAL
# ====================================================

def processar_argos(driver: WebDriver, log: bool = False) -> bool:
    """
    Processa fluxo Argos com sequência rigorosa e validações entre etapas.

    SEQUÊNCIA OBRIGATÓRIA (não pode ser alterada):
    0. Documentos sequenciais (identificar certidão, ordem de pesquisa, cálculos, intimação, decisão)
    1. Tirar sigilo da certidão
    2. Tratar anexos especiais infojud (sigilo+visibilidade)
    3. SISBAJUD - extrair documento PDF + regras
    4. Retirar sigilo dos demais documentos sequenciais que forem ainda sigilosos

    Cada etapa deve ser executada completamente antes de passar para a próxima.
    """
    try:
        print('[ARGOS][INICIO] Iniciando processamento do fluxo Argos com sequência rigorosa')

        # === ETAPA 0: FECHAR INTIMAÇÃO ===
        print('[ARGOS][ETAPA 0] Fechando intimação...')
        if not fechar_intimacao(driver, log=log):
            print('[ARGOS][ETAPA 0][ERRO CRÍTICO] Falha ao fechar intimação - ABORTANDO FLUXO')
            return False
        print('[ARGOS][ETAPA 0] ✅ Intimação fechada com sucesso')

        # === ETAPA 1: IDENTIFICAR DOCUMENTOS SEQUENCIAIS ===
        print('[ARGOS][ETAPA 1] Identificando documentos sequenciais (certidão, ordem de pesquisa, cálculos, intimação, decisão)...')
        documentos_sequenciais = buscar_documentos_sequenciais(driver, log=log)
        if not documentos_sequenciais:
            print('[ARGOS][ETAPA 1][ERRO] Nenhum documento sequencial encontrado - abortando fluxo')
            return False
        print(f'[ARGOS][ETAPA 1] ✅ Encontrados {len(documentos_sequenciais)} documentos sequenciais')

        # === ETAPA 1.5: RETIRAR SIGILO DOS DOCUMENTOS SEQUENCIAIS ===
        print('[ARGOS][ETAPA 1.5] Removendo sigilo dos documentos sequenciais (se houver)...')
        resultado_sigilo = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log=log)
        if resultado_sigilo.get('total_processados', 0) > 0:
            print(f'[ARGOS][ETAPA 1.5] ✅ {resultado_sigilo["total_processados"]} documento(s) tiveram sigilo removido')
        else:
            print('[ARGOS][ETAPA 1.5] ✅ Todos os documentos sequenciais sem sigilo')

        # === ETAPA 2: TRATAR ANEXOS ESPECIAIS INFOJUD (SIGILO + VISIBILIDADE) ===
        print('[ARGOS][ETAPA 2] Tratando anexos especiais infojud (sigilo + visibilidade)...')
        anexos_info = tratar_anexos_argos(driver, documentos_sequenciais, log=log)
        if not anexos_info:
            print('[ARGOS][ETAPA 2][ERRO] Falha no processamento de anexos - abortando fluxo')
            return False
        print('[ARGOS][ETAPA 2] ✅ Anexos especiais processados com sucesso')

        # === ETAPA 3: SISBAJUD - EXTRAIR DOCUMENTO PDF + REGRAS ===
        print('[ARGOS][ETAPA 3] SISBAJUD - Extraindo documento PDF e aplicando regras...')
        resultado_sisbajud = anexos_info.get('resultado_sisbajud', None)
        sigilo_anexos = anexos_info.get('sigilo_anexos', {})
        executados = anexos_info.get('executados', [])

        if resultado_sisbajud:
            print(f'[ARGOS][ETAPA 3] ✅ SISBAJUD processado: {resultado_sisbajud}')
        else:
            print('[ARGOS][ETAPA 3][AVISO] SISBAJUD não encontrado nos anexos')

        # === VALIDAÇÃO FINAL: VERIFICAR SE ANEXOS FORAM PROCESSADOS ===
        tem_anexos = anexos_info.get('tem_anexos', False)
        if not tem_anexos:
            print('[ARGOS][VALIDAÇÃO] Nenhum anexo encontrado - executando ato_meios diretamente')
            ato_meios(driver, debug=log)
            return True

        # === ETAPA 4: BUSCAR E APLICAR REGRAS ARGOS (LOOP ITERATIVO SIMPLES) ===
        # Loop: abrir despacho/decisão → extrair → comparar regras → aplicar se tem regra → próximo se não
        print('[ARGOS][ETAPA 4] Iniciando busca iterativa por despacho/decisão com regra aplicável...')
        
        regra_aplicada = False
        max_tentativas = 10  # Limite para evitar loop infinito
        tentativa = 0
        
        while tentativa < max_tentativas and not regra_aplicada:
            tentativa += 1
            print(f'\n[ARGOS][ETAPA 4] Tentativa {tentativa}/{max_tentativas}...')
            
            # Buscar próximo documento com regra Argos
            resultado_documento = buscar_documento_argos(driver, log=True)
            
            if not resultado_documento or not resultado_documento[0]:
                print(f'[ARGOS][ETAPA 4][INFO] Nenhum documento encontrado nesta tentativa')
                break
            
            documento_texto, documento_tipo = resultado_documento[0], resultado_documento[1]
            
            if not documento_texto or not documento_tipo:
                print(f'[ARGOS][ETAPA 4] ⚠️ Documento inválido - próximo')
                continue
            
            print(f'[ARGOS][ETAPA 4] Documento: tipo={documento_tipo}, chars={len(documento_texto)}')

            # === ETAPA 5: EXTRAIR DESTINATÁRIOS ===
            try:
                dados_processo_cache = extrair_dados_processo(driver, debug=log)
            except Exception as dados_err:
                dados_processo_cache = {}

            try:
                numero_proc_atual = extrair_numero_processo(driver)
            except Exception:
                numero_proc_atual = ''

            try:
                destinatarios_extraidos = extrair_destinatarios_decisao(
                    documento_texto,
                    dados_processo=dados_processo_cache,
                    debug=log
                )
                if destinatarios_extraidos:
                    salvar_destinatarios_cache(
                        "ATUAL",
                        destinatarios_extraidos,
                        origem=f'argos_{documento_tipo}'
                    )
                    print(f'[ARGOS][ETAPA 5] ✅ {len(destinatarios_extraidos)} destinatários salvos')
                else:
                    print('[ARGOS][ETAPA 5] ⚠️ Nenhum destinatário identificado')
            except Exception as dest_err:
                if log:
                    print(f'[ARGOS][ETAPA 5] Falha: {dest_err}')

            # === ETAPA 6: APLICAR REGRAS ARGOS ===
            print('[ARGOS][ETAPA 6] Tentando aplicar regras...')
            regras_aplicadas = aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, documento_tipo, documento_texto, debug=True)
            
            if regras_aplicadas:
                print(f'[ARGOS][ETAPA 6] ✅ Regra aplicada com sucesso!')
                regra_aplicada = True
                break
            else:
                print(f'[ARGOS][ETAPA 6] ⚠️ Nenhuma estratégia aplicou - próximo documento')
                continue
        
        if not regra_aplicada:
            print('[ARGOS][ETAPA 4-6][ERRO] Nenhum documento teve regra Argos aplicada com sucesso após {tentativa} tentativas')
            return False

        print('[ARGOS][SUCESSO] Todas as etapas do fluxo Argos executadas!')
        return True

    except Exception as e:
        print(f'[ARGOS][ERRO] Falha crítica no processamento: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        # ===== GARANTIR FECHAMENTO DA ABA /DETALHE MESMO EM CASO DE ERRO =====
        print('[ARGOS][CLEANUP] Verificando abas abertas...')
        try:
            all_windows = driver.window_handles
            current_url = driver.current_url.lower() if driver.current_url else ''
            
            # Se estamos em uma aba /detalhe e há mais de uma aba aberta
            if '/detalhe' in current_url and len(all_windows) > 1:
                print(f'[ARGOS][CLEANUP] Fechando aba /detalhe (total de abas: {len(all_windows)})')
                current_window = driver.current_window_handle
                main_window = all_windows[0]
                
                # Fecha a aba atual
                driver.close()
                print('[ARGOS][CLEANUP] ✅ Aba /detalhe fechada')
                
                # Troca para aba principal
                if main_window in driver.window_handles:
                    driver.switch_to.window(main_window)
                    print('[ARGOS][CLEANUP] ✅ Retornou para aba principal')
                else:
                    # Se a aba principal não existe mais, vai para a última aba disponível
                    driver.switch_to.window(driver.window_handles[-1])
                    print('[ARGOS][CLEANUP] ✅ Retornou para última aba disponível')
            else:
                print(f'[ARGOS][CLEANUP] Nenhuma ação necessária (URL: {current_url}, Abas: {len(all_windows)})')
                
        except Exception as cleanup_err:
            print(f'[ARGOS][CLEANUP][ERRO] Falha ao fechar aba: {cleanup_err}')
            # Não propaga o erro de cleanup para não mascarar erro original

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
            
        # Usando aguardar_e_clicar ao invés de find_elements direto para maior robustez
        timeline = aguardar_e_clicar(driver, 'ul.timeline-container', timeout=5)
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
                link = aguardar_e_clicar(driver, item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])'), timeout=1)
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
                time.sleep(2.0)
                # Busca o cabeçalho usando as funções do Fix.py
                cabecalho_selector = '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'
                cabecalho = esperar_elemento(driver, cabecalho_selector, timeout=15)  # Aumentado de 10 para 15
                if not cabecalho:
                    print('[ERRO] Cabeçalho do documento não encontrado após espera')
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
                print(f'[ARGOS] {texto_doc}')
                resultado = processar_argos(driver, log=True)
                if not resultado:
                    print('[ARGOS] ❌ FALHA CRÍTICA - Abortando este processo')
                    return  # Não continua para próximo processo
            elif any(remover_acentos(termo) in texto_lower for termo in ['oficial de justica', 'certidao de oficial', 'certidao de oficial de justica']):
                print(f'[OUTROS] Processo em análise: {texto_doc}')
                fluxo_mandados_outros(driver, log=False)
            else:
                print(f'[AVISO] Documento não identificado: {texto_doc}')
                
        except Exception as e:
            print(f'[ERRO] Falha ao processar mandado: {str(e)}')
        # NOTA: Fechamento de abas é gerenciado por forcar_fechamento_abas_extras
        # chamado pela função indexar_e_processar_lista após o callback
        
    print('[FLUXO] Filtro de mandados devolvidos já garantido na navegação. Iniciando processamento...')
    indexar_e_processar_lista(driver, fluxo_callback)

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
        # Usa aguardar_e_clicar mais robusto ao invés de find_element direto
        cabecalho = aguardar_e_clicar(driver, ".cabecalho-conteudo .mat-card-title", timeout=5, retornar_elemento=True)
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
        # REMOVIDO: GIGS 0/PZ MDD considerado inútil
        
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
                print("[MANDADOS][OUTROS][LOG] Ordem de cancelamento total detectada")
            
            # TODO: Implementar BNDT_apagar e def_arq quando funções forem disponibilizadas
            # BNDT_apagar(driver)
            # def_arq(driver)
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
                        # Comportamento idêntico ao p2b: abrir link, aguardar estabilização e chamar extrair_direto
                        try:
                            aguardar_e_clicar(driver, link_ant)
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", link_ant)
                            except Exception:
                                pass
                        time.sleep(2)
                        try:
                            texto_mandado_ant_result = extrair_direto(driver, timeout=10, debug=True, formatar=True)
                        except Exception:
                            texto_mandado_ant_result = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
                        texto_mandado_ant = texto_mandado_ant_result.get('conteudo', '') if texto_mandado_ant_result and texto_mandado_ant_result.get('sucesso') else None
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
    
    # Comportamento idêntico ao p2b: tentar extrair direto (timeout=10, debug=formatar)
    try:
        texto_result = extrair_direto(driver, timeout=10, debug=log, formatar=True)
    except Exception:
        texto_result = None

    if not texto_result or not texto_result.get('sucesso'):
        if log:
            print('[MANDADOS][OUTROS] Fallback: chamando extrair_documento()')
        texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=log)
        texto = texto_tuple[0] if texto_tuple and texto_tuple[0] else None
    else:
        texto = texto_result.get('conteudo', '')
    if not texto:
        if log:
            print("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
        return
            
    if log:
        print('[MANDADOS][OUTROS] Fluxo Mandado (Outros) concluído.')

# ====================================================
# BLOCO 3 - MÓDULO DE TESTE
# ====================================================

