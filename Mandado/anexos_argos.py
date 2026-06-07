"""Mandado - Processamento de Anexos Argos

Lógica consolidada de:
  - Processamento de anexos sigilosos (infojud, doi, irpf, etc.)
  - Análise SISBAJUD a partir do PDF da certidão de devolução
  - Aplicação de visibilidade e sigilo de documentos

Entrypoints públicos:
  - tratar_anexos_argos(): ETAPA 2 do fluxo Argos
  - processar_sisbajud(): ETAPA 3 do fluxo Argos
"""

# ══════════════════════ Imports ══════════════════════
import re
import time
from typing import Optional, Dict, List

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.resultado_execucao import ResultadoExecucao

from Fix.log import logger
from Fix.utils_observer import aguardar_renderizacao_nativa


# ══════════════════════ Constantes ══════════════════════

_SIGILO_TYPES = [
    "infojud", "doi", "irpf", "ir2022", "ir2023", "ir2024", "ir2025", "ir2026",
    "ir 2023", "ir 2024", "ir 2025", "ir 2026", "ir23", "ir24", "ir25", "ir26",
    "dimob", "ecac", "efinanceira", "e-financeira", "decred", "DEC9"
]

_SELETORES_ANEXOS = {
    'btn_anexos': 'button.botao-anexos, pje-timeline-anexos > div > div',
    'anexos': '.tl-item-anexo',
    'btn_sigilo': 'i.fa-wpexplorer',
    'icone_plus': 'i.fas.fa-plus.tl-sigiloso',
    'modal_container': '.cdk-overlay-container .mat-dialog-container',
    'checkbox': 'mat-checkbox',
    'btn_salvar': ".//div[@mat-dialog-actions]//button[contains(., 'Salvar')]",
    'selecionar_todos': 'i.fa.fa-check.botao-icone-titulo-coluna'
}


# ══════════════════════ Funções Privadas ══════════════════════

def _identificar_tipo_anexo(texto: str) -> Optional[str]:
    """Identifica tipo de anexo especial."""
    texto_lower = texto.strip().lower()
    for tipo in _SIGILO_TYPES:
        if tipo == "DEC9":
            if re.search(r"dec\d{9}", texto_lower):
                return tipo
        elif tipo in texto_lower:
            return tipo
    return None


def _localizar_modal_visibilidade(driver: WebDriver, timeout: int = 4) -> Optional[WebElement]:
    """Localiza modal de visibilidade com espera ativa."""
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


def _processar_modal_visibilidade(driver: WebDriver, modal: WebElement, log: bool = True) -> bool:
    """Processa modal: seleciona checkboxes e salva (modo rápido)."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    import time
    try:
        time.sleep(0.12)
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
        time.sleep(0.08)
        btn_salvar = modal.find_element(By.XPATH, _SELETORES_ANEXOS['btn_salvar'])
        if not (btn_salvar.is_displayed() and btn_salvar.is_enabled()):
            return False
        driver.execute_script("arguments[0].click();", btn_salvar)
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


def _extrair_executados_pdf(texto_documento: str) -> List[Dict[str, str]]:
    """Extrai lista de executados do texto do documento."""
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


# ══════════════════════ Funções Públicas ══════════════════════

def processar_sisbajud(texto_pdf: str, log: bool = True) -> tuple[str, str, list]:
    """
    ANÁLISE SISBAJUD: Sempre processa usando o texto extraído (texto_pdf).

    Não busca SISBAJUD em anexos, apenas analisa o texto recebido.
    """
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
    
    # Testar vários seletores para encontrar o botão de anexos e logar qual funcionou
    seletores_teste = [
        'button.botao-anexos'
    ]
    
    btn_anexos_encontrado = None
    for sel in seletores_teste:
        try:
            elementos = doc.find_elements(By.CSS_SELECTOR, sel)
            if elementos:
                btn_anexos_encontrado = elementos[0]
                if log:
                    logger.info(f'[ARGOS][ANEXOS][SELETOR_BOTAO] ✅ Funcionou com: "{sel}"')
                break
        except Exception:
            continue
            
    if btn_anexos_encontrado:
        try:
            # JavaScript direto conforme legado (evita abertura de aba e ignora overlays)
            driver.execute_script("arguments[0].click();", btn_anexos_encontrado)
            if log:
                logger.info('[ARGOS][ANEXOS]  Anexos abertos (via clique no botão de anexos)')
            aguardar_renderizacao_nativa(driver, _SELETORES_ANEXOS['anexos'], modo='aparecer', timeout=5)
        except Exception as e:
            if log:
                logger.info(f'[ARGOS][ANEXOS][ERRO] Falha ao abrir anexos: {e}')
            return None
    else:
        if log:
            logger.info('[ARGOS][ANEXOS]  Botão de anexos não encontrado com nenhum seletor testado')
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

    # === FASE 1: INSERIR SIGILO INDIVIDUALMENTE ===
    if log:
        logger.info('[ARGOS][ANEXOS] === FASE 1: INSERIR SIGILO INDIVIDUALMENTE ===')

    from atos.anexos_sigilo import inserir_sigilo_individual

    anexos_com_sigilo = []

    # 1. Inserir sigilo individualmente em cada anexo especial
    for anexo in anexos:
        texto_anexo = anexo.text.strip()
        tipo = _identificar_tipo_anexo(texto_anexo)
        if not tipo:
            continue

        found_sigilo[tipo] = True

        # Tentar inserir sigilo
        if inserir_sigilo_individual(anexo, driver, debug=False):
            anexos_com_sigilo.append((anexo, tipo))
            sigilo_anexos[tipo] = "sim"
            if log:
                logger.info(f'[ARGOS][ANEXOS]  ✅ Sigilo inserido: {tipo.upper()}')
        else:
            if log:
                logger.warning(f'[ARGOS][ANEXOS] ❌ Falha ao inserir sigilo em {tipo.upper()}')
            sigilo_anexos[tipo] = "falha"

    # Disparar visibilidade se algum anexo especial foi processado (com sucesso OU falha)
    # Falha pode indicar que sigilo já estava presente mas não foi detectado
    tem_especiais = any(found_sigilo.values())
    if anexos_com_sigilo or tem_especiais:
        any_sigilo = True
        if log:
            if anexos_com_sigilo:
                logger.info(f'[ARGOS][ANEXOS] {len(anexos_com_sigilo)} anexo(s) receberam sigilo')
            else:
                logger.info('[ARGOS][ANEXOS] Anexos especiais encontrados (sigilo já presente) — aplicando visibilidade')

        # Pequena espera antes de passar para visibilidade
        time.sleep(1.0)

        # === FASE 2: APLICAR VISIBILIDADE EM LOTE ===
        if log:
            logger.info('[ARGOS][ANEXOS] === FASE 2: APLICAR VISIBILIDADE EM LOTE ===')

        try:
            from atos.anexos_sigilo import visibilidade_sigilosos_lote_apenas

            vis_ok = visibilidade_sigilosos_lote_apenas(driver, polo='ativo', log=True)

            if vis_ok:
                if log:
                    logger.info('[ARGOS][ANEXOS]  ✅ Visibilidade em lote aplicada com sucesso')
            else:
                if log:
                    logger.warning('[ARGOS][ANEXOS] ❌ Falha ao aplicar visibilidade em lote (não é crítico, continuando)')

        except Exception as e:
            if log:
                logger.error(f'[ARGOS][ANEXOS] Erro ao aplicar visibilidade em lote: {e}')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
    else:
        if log:
            logger.info('[ARGOS][ANEXOS] Nenhum anexo especial encontrado.')

    return ResultadoExecucao(
        sucesso=True,
        status='OK',
        detalhes={
            'found_sigilo': found_sigilo,
            'sigilo_anexos': sigilo_anexos,
            'sigiloso': any_sigilo,
            'tem_anexos': tem_anexos
        }
    )
