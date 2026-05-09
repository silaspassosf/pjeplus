"""Mandado - Fluxo Argos (Pesquisa Patrimonial)

Consolidado de:
    processamento_argos.py — fluxo principal Argos (etapas 0-5)
    processamento_anexos.py — tratamento de anexos (sigilo, visibilidade, SISBAJUD)

Entrypoint publico: processar_argos()
Sequencia obrigatoria: ETAPA 0 (fechar intimacao) -> ETAPA 1 (documentos sequenciais)
    -> ETAPA 1.5 (sigilo) -> ETAPA 2 (anexos infojud) -> ETAPA 3 (SISBAJUD)
    -> ETAPA 4 (regras) -> ETAPA 5 (destinatarios)
"""

# ══════════════════════ Imports ══════════════════════
import re
import time
import traceback
from typing import Optional, Dict, List

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.resultado_execucao import ResultadoExecucao

from Fix.core import buscar_documento_argos
from Fix.core import buscar_documentos_sequenciais
from Fix.extracao import extrair_dados_processo, extrair_destinatarios_decisao, extrair_direto, salvar_destinatarios_cache
from Fix.log import logger
from Fix.utils_observer import aguardar_renderizacao_nativa

from PEC.core_progresso import extrair_numero_processo_pec as extrair_numero_processo

from atos import ato_meios

from .regras import aplicar_regras_argos
from .apoio_fluxos import retirar_sigilo_fluxo_argos, buscar_documentos_sequenciais_via_api
from .entrada_api import fechar_intimacao


# ══════════════════════ 1. processamento_anexos.py ══════════════════════
# (anexo processing comes first since argos calls into it)

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


## Mantido comportamento original do p2b: não adicionar wrappers adicionais aqui.

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
    btn_anexos = doc.find_elements(By.CSS_SELECTOR, _SELETORES_ANEXOS['btn_anexos'])
    if btn_anexos:
        try:
            # JavaScript direto conforme legado (evita abertura de aba e ignora overlays)
            driver.execute_script("arguments[0].click();", btn_anexos[0])
            if log:
                logger.info('[ARGOS][ANEXOS]  Anexos abertos (via clique no botão de anexos)')
            aguardar_renderizacao_nativa(driver, _SELETORES_ANEXOS['anexos'], modo='aparecer', timeout=5)
        except Exception as e:
            if log:
                logger.info(f'[ARGOS][ANEXOS][ERRO] Falha ao abrir anexos: {e}')
            return None
    else:
        if log:
            logger.info('[ARGOS][ANEXOS]  Botão de anexos não encontrado')
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

# === FASE 1: PROCESSAR SIGILO + VISIBILIDADE EM LOTE ===
    if log:
        logger.info('[ARGOS][ANEXOS] === FASE SIGILO + VISIBILIDADE EM LOTE ===')

    anexos_para_sigilo = []
    
    # 1. Identificar anexos especiais e se precisam de sigilo
    for anexo in anexos:
        texto_anexo = anexo.text.strip()
        tipo = _identificar_tipo_anexo(texto_anexo)
        if not tipo:
            continue
            
        found_sigilo[tipo] = True
        
        # Detectar estado atual de sigilo
        tem_sigilo = False
        try:
            icons = anexo.find_elements(By.CSS_SELECTOR, 'pje-doc-sigiloso span button i.fa-wpexplorer')
            if icons:
                classes = icons[0].get_attribute("class") or ""
                if "tl-sigiloso" in classes:
                    tem_sigilo = True
        except Exception:
            pass
            
        if not tem_sigilo:
            anexos_para_sigilo.append((anexo, tipo))
            sigilo_anexos[tipo] = "sim"
        else:
            sigilo_anexos[tipo] = "sim"

    if anexos_para_sigilo:
        if log:
            logger.info(f'[ARGOS][ANEXOS] {len(anexos_para_sigilo)} anexo(s) especiais precisam de sigilo. Iniciando processamento em lote...')
        
        try:
            import time
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # 2. Ativar seleção múltipla
            btn_multi = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Exibir múltipla seleção."]'))
            )
            driver.execute_script("arguments[0].click();", btn_multi)
            time.sleep(1)
            
            # 3. Marcar checkboxes dos anexos alvo
            for anexo, tipo in anexos_para_sigilo:
                try:
                    checkbox_label = anexo.find_element(By.CSS_SELECTOR, 'mat-checkbox label')
                    driver.execute_script("arguments[0].click();", checkbox_label)
                    if log:
                        logger.info(f'[ARGOS][ANEXOS]  Selecionado para lote: {tipo.upper()}')
                except Exception as e:
                    if log:
                        logger.warning(f'[ARGOS][ANEXOS] Erro ao selecionar {tipo.upper()}: {e}')
            
            time.sleep(0.5)
            
            # 4. Clicar em "Inserir Sigilo" no div de lote
            btn_inserir_sigilo = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.div-todas-atividades-em-lote button[mattooltip="Inserir Sigilo"]'))
            )
            driver.execute_script("arguments[0].click();", btn_inserir_sigilo)
            time.sleep(1.5)
            if log:
                logger.info('[ARGOS][ANEXOS]  Sigilo em lote aplicado.')
                
            # 5. Clicar em "Visibilidade" no div de lote
            btn_visibilidade_lote = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]'))
            )
            driver.execute_script("arguments[0].click();", btn_visibilidade_lote)
            time.sleep(1.5)
            
            # 6. Usar a mesma lógica de modal de visibilidade já existente
            modal = _localizar_modal_visibilidade(driver, timeout=6)
            if modal:
                time.sleep(0.8)  # Espera para estabilização
                modal_ok = _processar_modal_visibilidade(driver, modal, log=False)
                if modal_ok:
                    any_sigilo = True
                    if log:
                        logger.info('[ARGOS][ANEXOS]  Visibilidade em lote aplicada com sucesso.')
                    time.sleep(0.5)
                else:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(1.5)
            else:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(1.5)
                
            # 7. Ocultar múltipla seleção
            try:
                btn_ocultar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Ocultar múltipla seleção."]')
                driver.execute_script("arguments[0].click();", btn_ocultar)
            except Exception:
                pass
                
        except Exception as e:
            if log:
                logger.error(f'[ARGOS][ANEXOS] Erro crítico no processamento em lote: {e}')
            try:
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            except Exception:
                pass
    else:
        if log:
            logger.info('[ARGOS][ANEXOS] Nenhum anexo precisava de sigilo/visibilidade (já estavam com sigilo ou ausentes).')

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


# ══════════════════════ 2. processamento_argos.py ══════════════════════
# (main flow — calls into anexos functions above)


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
    # === TIMING: INÍCIO DO PROCESSAMENTO ===
    timing_inicio = time.time()
    logger.info('[ARGOS][TIMING][PROCESAR_ARGOS][INICIO]')

    try:
        logger.info('[ARGOS][INICIO] Iniciando processamento do fluxo Argos com sequência rigorosa')

        # ════════════════════════════════════════
        # === ETAPA 0: FECHAR INTIMAÇÃO ===
        logger.info('[ARGOS][ETAPA 0] Fechando intimação...')
        if not fechar_intimacao(driver, log=log):
            logger.info('[ARGOS][ETAPA 0][ERRO CRÍTICO] Falha ao fechar intimação - ABORTANDO FLUXO')
            return False
        logger.info('[ARGOS][ETAPA 0]  Intimação fechada com sucesso')

        # ════════════════════════════════════════
        # === ETAPA 1: IDENTIFICAR DOCUMENTOS SEQUENCIAIS ===
        logger.info('[ARGOS][ETAPA 1] Identificando documentos sequenciais (certidão, ordem de pesquisa, cálculos, intimação, decisão)...')
        documentos_sequenciais, uids_sigilosos_hint = buscar_documentos_sequenciais_via_api(driver, log=log)
        if documentos_sequenciais and len(documentos_sequenciais) >= 2:
            logger.info(f'[ARGOS][ETAPA 1]  {len(documentos_sequenciais)} doc(s) identificados via API')
        else:
            if documentos_sequenciais:
                logger.info('[ARGOS][ETAPA 1] API retornou %d doc(s) (mínimo 2) — fallback DOM', len(documentos_sequenciais))
            else:
                logger.info('[ARGOS][ETAPA 1] API sem resultado — fallback DOM')
            documentos_sequenciais = buscar_documentos_sequenciais(driver, log=log)
            uids_sigilosos_hint = None
        if not documentos_sequenciais:
            logger.info('[ARGOS][ETAPA 1][ERRO] Nenhum documento sequencial encontrado - abortando fluxo')
            return False
        logger.info(f'[ARGOS][ETAPA 1]  Encontrados {len(documentos_sequenciais)} documentos sequenciais')

        # ════════════════════════════════════════
        # === ETAPA 1.5: RETIRAR SIGILO DOS DOCUMENTOS SEQUENCIAIS ===
        logger.info('[ARGOS][ETAPA 1.5] Removendo sigilo dos documentos sequenciais (se houver)...')
        resultado_sigilo = retirar_sigilo_fluxo_argos(driver, documentos_sequenciais, log=log, uids_sigilosos_hint=uids_sigilosos_hint)
        if resultado_sigilo.get('total_processados', 0) > 0:
            logger.info(f'[ARGOS][ETAPA 1.5]  {resultado_sigilo["total_processados"]} documento(s) tiveram sigilo removido')
        else:
            logger.info('[ARGOS][ETAPA 1.5]  Todos os documentos sequenciais sem sigilo')

        # ════════════════════════════════════════
        # === ETAPA 2: TRATAR ANEXOS ESPECIAIS INFOJUD (SIGILO + VISIBILIDADE) ===
        logger.info('[ARGOS][ETAPA 2] Tratando anexos especiais infojud (sigilo + visibilidade)...')
        anexos_info = tratar_anexos_argos(driver, documentos_sequenciais, log=log)
        if not anexos_info:
            logger.info('[ARGOS][ETAPA 2][AVISO] Nenhum anexo especial encontrado ou processamento não crítico; prosseguindo sem anexos')
            anexos_info = {
                'tem_anexos': False,
                'sigilo_anexos': {}
            }
        else:
            logger.info('[ARGOS][ETAPA 2]  Anexos especiais processados com sucesso')

        # Extrair dados de anexos para decisão de rota
        if hasattr(anexos_info, 'detalhes') and isinstance(anexos_info.detalhes, dict):
            sigilo_anexos = anexos_info.detalhes.get('sigilo_anexos', {})
            tem_anexos = anexos_info.detalhes.get('tem_anexos', False)
        else:
            sigilo_anexos = anexos_info.get('sigilo_anexos', {})
            tem_anexos = anexos_info.get('tem_anexos', False)

        # Sem anexos = sem SISBAJUD = certidão negativa → ato_meios direto
        if not tem_anexos:
            logger.info('[ARGOS][ETAPA 2.5] Certidao sem anexos — ato_meios direto')
            ato_meios(driver, debug=log)
            return True

        # ════════════════════════════════════════
        # === ETAPA 3: ANÁLISE SISBAJUD VIA CERTIDÃO DE DEVOLUÇÃO ===
        # A certidão de devolução JÁ ESTÁ selecionada na timeline.
        # Após tratamento de anexos (ETAPA 2), ela continua selecionada.
        # Usar extrair_direto para ler o conteúdo da certidão.
        logger.info('[ARGOS][ETAPA 3] Lendo certidão de devolução via extrair_direto para análise SISBAJUD...')

        resultado_sisbajud = None
        executados = []

        try:
            resultado_extracao = extrair_direto(driver, timeout=10, debug=log, formatar=True)
            texto_certidao = resultado_extracao.get('conteudo') if resultado_extracao and resultado_extracao.get('sucesso') else None

            if texto_certidao:
                logger.info('[ARGOS][ETAPA 3] Certidão extraída: %d chars', len(texto_certidao))
                try:
                    resultado_sisbajud, motivo, executados = processar_sisbajud(texto_certidao, log=False)
                    if resultado_sisbajud == 'positivo':
                        logger.info(f'[ARGOS][ETAPA 3] SISBAJUD POSITIVO: {motivo}')
                    elif resultado_sisbajud == 'negativo':
                        logger.info(f'[ARGOS][ETAPA 3] SISBAJUD NEGATIVO: {motivo}')
                except ValueError:
                    logger.info('[ARGOS][ETAPA 3] SISBAJUD INDISPONIVEL: marcador "determinacoes normativas e legais" nao encontrado na certidao')
                    resultado_sisbajud = None
                    executados = []
                except Exception as e:
                    logger.error('[ARGOS][ETAPA 3] Erro na análise SISBAJUD: %s', e)
                    resultado_sisbajud = None
                    executados = []
            else:
                logger.info('[ARGOS][ETAPA 3] Certidão sem conteúdo — SISBAJUD indisponível')
        except Exception as e:
            logger.error('[ARGOS][ETAPA 3] Falha ao extrair certidão: %s', e)

        # ════════════════════════════════════════
        # === ETAPA 4: BUSCAR E APLICAR REGRAS ARGOS (LOOP ITERATIVO) ===
        # Loop: abrir despacho/decisão → extrair → comparar regras → aplicar se tem regra → próximo se não
        # LIMITE: Máximo 3 documentos. Se passar de 3 sem encontrar regra, abortar busca.

        timing_etapa4_inicio = time.time()
        logger.info('[ARGOS][TIMING][ETAPA4][INICIO] Iniciando busca e aplicação de regras ARGOS')

        regra_aplicada = False
        max_documentos_testados = 3  # LIMITE: máximo 3 documentos
        documentos_testados = 0
        documentos_ignorados = []

        while documentos_testados < max_documentos_testados and not regra_aplicada:
            # Buscar próximo documento com regra Argos
            timing_busca_inicio = time.time()
            resultado_documento = buscar_documento_argos(driver, log=True, ignorar_indices=documentos_ignorados)
            timing_busca_fim = time.time()
            logger.info(f'[ARGOS][TIMING][BUSCA_DOC] {timing_busca_fim - timing_busca_inicio:.3f}s')

            if not resultado_documento or not resultado_documento[0]:
                logger.info('[ARGOS][ETAPA 4] Fim da busca: Nenhum documento candidato restou na timeline')
                break

            documento_texto, documento_tipo, documento_idx = resultado_documento

            if not documento_texto:
                if documento_idx is not None:
                    documentos_ignorados.append(documento_idx)
                continue

            documentos_testados += 1
            logger.info('[ARGOS][ETAPA 4] Testando documento %d/%d (índice #%d, tipo: %s)...',
                       documentos_testados, max_documentos_testados, documento_idx, documento_tipo)

            # ════════════════════════════════════════
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
            except Exception as dest_err:
                pass

            # TENTAR APLICAR REGRAS
            timing_regras_inicio = time.time()
            regras_aplicadas = aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, documento_tipo, documento_texto, debug=True)
            timing_regras_fim = time.time()
            logger.info(f'[ARGOS][TIMING][APLICAR_REGRAS] {timing_regras_fim - timing_regras_inicio:.3f}s')

            if regras_aplicadas:
                regra_aplicada = True
                logger.info(f'[ARGOS][ETAPA 4] ✅ SUCESSO: Regra aplicada no documento #{documento_idx} ({documentos_testados}/{max_documentos_testados})')
                break
            else:
                logger.info(f'[ARGOS][ETAPA 4] ❌ Nenhuma regra encontrada no documento #{documento_idx}')
                documentos_ignorados.append(documento_idx)

                # Se atingiu limite de documentos testados, parar busca
                if documentos_testados >= max_documentos_testados:
                    logger.info(f'[ARGOS][ETAPA 4] Limite de documentos ({max_documentos_testados}) atingido. Interrompendo busca por regras.')
                    break
                continue

        # === TIMING: FIM DA ETAPA 4 ===
        timing_etapa4_total = time.time() - timing_etapa4_inicio
        logger.info(f'[ARGOS][TIMING][ETAPA4][TOTAL] {timing_etapa4_total:.3f}s documentos_testados={documentos_testados} regra_aplicada={regra_aplicada}')

        if not regra_aplicada:
            logger.info(f'[ARGOS][ETAPA 4] Nenhuma regra Argos encontrada nos {documentos_testados} documento(s) testado(s) (limite: {max_documentos_testados})')
            timing_total = time.time() - timing_inicio
            logger.info(f'[ARGOS][TIMING][PROCESSAR_ARGOS][FALHA] {timing_total:.3f}s')
            return False

        timing_total = time.time() - timing_inicio
        logger.info(f'[ARGOS][TIMING][PROCESSAR_ARGOS][SUCESSO] {timing_total:.3f}s')
        return True

    except Exception as e:
        timing_erro = time.time() - timing_inicio
        logger.info(f'[ARGOS][TIMING][PROCESSAR_ARGOS][ERRO] {timing_erro:.3f}s')
        logger.info(f'[ARGOS][ERRO] Falha crítica no processamento: {e}')
        logger.exception("Erro detectado")
        return False
    finally:
        # ===== GARANTIR FECHAMENTO DA ABA /DETALHE MESMO EM CASO DE ERRO =====
        try:
            all_windows = driver.window_handles
            current_url = driver.current_url.lower() if driver.current_url else ''

            # Se estamos em uma aba /detalhe e há mais de uma aba aberta
            if '/detalhe' in current_url and len(all_windows) > 1:
                current_window = driver.current_window_handle
                main_window = all_windows[0]

                # Fecha a aba atual
                driver.close()

                # Troca para aba principal
                if main_window in driver.window_handles:
                    driver.switch_to.window(main_window)
                else:
                    # Se a aba principal não existe mais, vai para a última aba disponível
                    driver.switch_to.window(driver.window_handles[-1])
        except Exception as cleanup_err:
            logger.info(f'[ARGOS][CLEANUP][ERRO] Falha ao fechar aba: {cleanup_err}')
            # Não propaga o erro de cleanup para não mascarar erro original
