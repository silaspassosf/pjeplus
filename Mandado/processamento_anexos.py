import time
from typing import Optional, Dict, List

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from Fix.log import logger
from Fix.extracao import extrair_pdf

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
                            logger.info(f"[VISIBILIDADE]  Ícone + validado após {i+1} tentativas")
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
        except Exception:
            pass
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
            return True
        except TimeoutException:
            return False
    except Exception as e:
        if log:
            logger.error(f"[MODAL][ERRO] {e}")
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
     ANÁLISE SISBAJUD: Sempre processa usando o texto extraído (texto_pdf).

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
        if 'bloqueio de valores' in result_line:
            bloqueio_idx = det_idx + offset
            break
    if bloqueio_idx == -1:
        return 'negativo', 'Bloqueio de valores não encontrado, sem SISBAJUD', executados
    for offset in range(1, 15):
        if bloqueio_idx + offset >= len(lines):
            break
        sisbajud_line = lines[bloqueio_idx + offset].strip().lower()
        if not sisbajud_line:
            continue
        if 'sisbajud' in sisbajud_line:
            for sib_offset in range(1, 5):
                if bloqueio_idx + offset + sib_offset >= len(lines):
                    break
                resultado_line = lines[bloqueio_idx + offset + sib_offset].strip().lower()
                if not resultado_line:
                    continue
                if 'negativo' in resultado_line:
                    return 'negativo', 'SISBAJUD Negativo na seção Bloqueio de valores', executados
                elif 'positivo' in resultado_line:
                    return 'positivo', 'SISBAJUD Positivo na seção Bloqueio de valores', executados
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
                        break
                    except ValueError:
                        continue
            if valor_encontrado > 0:
                return 'positivo', f'SISBAJUD com valor positivo: R$ {valor_encontrado:.2f}', executados
            else:
                return 'negativo', f'SISBAJUD sem valor ou valor zero encontrado', executados
    return 'negativo', 'SISBAJUD não encontrado na seção Bloqueio de valores', executados


# `buscar_documento_argos` fica no módulo `Fix` (manter implementação no local de origem).
# Use `from Fix import buscar_documento_argos` conforme já declarado nas importações.

def tratar_anexos_argos(driver: WebDriver, documentos_sequenciais: List[WebElement], log: bool = True) -> Optional[Dict]:
    """
     ETAPA 2 DO FLUXO ARGOS - Processar anexos sigilosos e extrair SISBAJUD
    
    Sequência correta conforme m1.py:
    1. Abrir anexos
    2. Processar sigilo + visibilidade da lista infojud, doi, irpf, etc.
    3. Extrair SISBAJUD
    4. Aplicar regras adicionais
    """
    if not documentos_sequenciais:
        if log:
            logger.info('[ARGOS][ANEXOS][ERRO] Nenhum documento sequencial fornecido')
        return None
    
    # ABRIR ANEXOS (JavaScript direto - ignora overlay de DOM) conforme legado
    doc = documentos_sequenciais[0]
    btn_anexos = doc.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['btn_anexos'])
    if btn_anexos:
        try:
            # JavaScript direto conforme legado (evita abertura de aba e ignora overlays)
            driver.execute_script("arguments[0].click();", btn_anexos[0])
            if log:
                logger.info('[ARGOS][ANEXOS]  Anexos abertos (via clique no botão de anexos)')
            time.sleep(2)
        except Exception as e:
            if log:
                logger.info(f'[ARGOS][ANEXOS][ERRO] Falha ao abrir anexos: {e}')
            return None
    else:
        if log:
            logger.info('[ARGOS][ANEXOS]  Botão de anexos não encontrado')
        # Se não há botão, não há o que expandir
        return None
    
    anexos = driver.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['anexos'])
    tem_anexos = len(anexos) > 0
    
    if not anexos:
        if log:
            logger.info('[ARGOS][ANEXOS]  Nenhum anexo encontrado')
    else:
        if log:
            logger.info(f'[ARGOS][ANEXOS]  {len(anexos)} anexos encontrados')
    found_sigilo = {k: False for k in _SIGILO_TYPES}
    sigilo_anexos = {k: "nao" for k in _SIGILO_TYPES}
    any_sigilo = False
    executados = []
    resultado_sisbajud = None
    
# === FASE 1: PROCESSAR SIGILO + VISIBILIDADE SEQUENCIALMENTE ===
    if log:
        logger.info('[ARGOS][ANEXOS] === FASE SIGILO + VISIBILIDADE ===')
    
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
                        logger.info(f'[ARGOS][ANEXOS]  Sigilo aplicado em {tipo.upper()}')
                else:
                    if log:
                        logger.info(f'[ARGOS][ANEXOS]  Ícone de sigilo não encontrado para {tipo.upper()} - pulando')
                    continue
            except Exception as e:
                if log:
                    logger.info(f'[ARGOS][ANEXOS]  Erro ao aplicar sigilo em {tipo.upper()}: {e}')
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
                            logger.info(f'[ARGOS][ANEXOS]  {tipo.upper()} processado (visibilidade aplicada)')
                        
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
        pass
    
    # === FASE 2: PROCESSAR SISBAJUD ===
    try:
        if log:
            logger.info('[ARGOS][ANEXOS][SISBAJUD] Procurando documento SISBAJUD...')
        
        documento_sisbajud = None
        for anexo in anexos:
            texto = anexo.text.strip()
            if "Certidão de devolução de ordem de pesquisa patrimonial" in texto:
                documento_sisbajud = anexo
                if log:
                    logger.info(f'[ARGOS][ANEXOS][SISBAJUD]  Documento SISBAJUD encontrado: {texto[:50]}...')
                break
        
        if not documento_sisbajud:
            if log:
                logger.info('[ARGOS][ANEXOS][SISBAJUD]  Nenhum documento SISBAJUD encontrado nos anexos')
        else:
            if log:
                logger.info('[ARGOS][ANEXOS][SISBAJUD] Clicando no documento SISBAJUD...')
            documento_sisbajud.click()
            time.sleep(1)
            if log:
                logger.info('[ARGOS][ANEXOS][SISBAJUD]  Documento SISBAJUD clicado, aguardando carregamento...')
    except Exception as e:
        if log:
            logger.info(f'[ARGOS][ANEXOS][SISBAJUD][ERRO] Falha ao localizar/clicar documento SISBAJUD: {e}')
        pass
    
    texto_pdf = extrair_pdf(driver, log=False)
    if texto_pdf:
        if log:
            # Mostrar preview do texto
            preview = texto_pdf[:200].replace('\n', ' ').strip()
    else:
        texto_pdf = None
    if texto_pdf:
        executados = _extrair_executados_pdf(texto_pdf)
        if log:
            if executados:
                for i, exec_data in enumerate(executados[:3]):  # Mostrar até 3 primeiros
                    pass
        try:
            resultado_sisbajud, motivo, executados = processar_sisbajud(texto_pdf, log=False)
            # Log limpo: apenas SISBAJUD POSITIVO/NEGATIVO com valor detectado
            if resultado_sisbajud == 'positivo':
                valor_detectado = motivo.split('R$ ')[-1] if 'R$ ' in motivo else ''
            elif resultado_sisbajud == 'negativo':
                pass
            # Log de executados: apenas quantidade
            if len(executados) == 1:
                pass
            elif len(executados) > 1:
                pass
        except ValueError as ve:
            # Erro da função SISBAJUD - reportar no log
            logger.error(f'[SISBAJUD][ERRO] {ve}')
            resultado_sisbajud = None
            executados = []
        except Exception as e:
            # Qualquer outro erro - reportar como erro da função
            logger.error(f'[SISBAJUD][ERRO] Erro na análise SISBAJUD: {e}')
            resultado_sisbajud = None
            executados = []
    else:
        executados = []
        resultado_sisbajud = None
    if log:
        status_sisbajud = resultado_sisbajud if resultado_sisbajud else f"SEM SISBAJUD ({motivo})"
    
    return {
        'executados': executados,
        'resultado_sisbajud': resultado_sisbajud,
        'found_sigilo': found_sigilo,
        'sigilo_anexos': sigilo_anexos,
        'sigiloso': any_sigilo,
        'tem_anexos': tem_anexos
    }