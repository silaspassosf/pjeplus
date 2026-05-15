# -*- coding: utf-8 -*-
"""
bianca/extracao.py - Funcoes de extracao e interacao com PJe.

Contem implementacoes autocontidas de:
  - criar_gigs: Cria atividade GIGS (anotacao)
  - criar_comentario: Cria comentario no processo
  - criar_lembrete_posit: Cria lembrete/post-it
  - abrir_detalhes_processo: Abre detalhes a partir de uma linha
  - indexar_processos: Indexa processos da lista atual
  - reindexar_linha: Re-indexa uma linha especifica

Nenhuma dependencia externa ao modulo bianca.
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bianca.utils import logger
from bianca.selenium_utils import aguardar_e_clicar, esperar_elemento, preencher_campo


# =============================================================================
# HELPERS
# =============================================================================


def _gigs_responsavel_valido(responsavel: Optional[str]) -> bool:
    """Verifica se responsavel e valido (nao vazio, nao '-').

    Args:
        responsavel: String com nome do responsavel ou None.

    Returns:
        True se responsavel e valido, False caso contrario.
    """
    return responsavel is not None and responsavel.strip() and responsavel.strip() != '-'


def _parse_gigs_string(string: str) -> Dict[str, Any]:
    """Parseia string de teste GIGS automaticamente.

    Regras:
    - sem / = OBSERVACAO
    - uma / ou // juntas = prazo/observacao ou prazo//observacao (sem responsavel)
    - duas / entre parametros = prazo/responsavel/observacao

    Args:
        string: String no formato prazo/responsavel/observacao.

    Returns:
        Dict com chaves 'dias_uteis', 'responsavel', 'observacao'.
    """
    if '/' not in string:
        return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}

    # Verificar se ha duas barras consecutivas
    if '//' in string:
        partes = string.split('//', 1)
        if len(partes) == 2:
            prazo_str, obs = partes
            try:
                dias_uteis = int(prazo_str.strip())
            except ValueError:
                dias_uteis = None
            return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}

    # Split por /
    partes = string.split('/')
    if len(partes) == 2:
        prazo_str, obs = partes
        try:
            dias_uteis = int(prazo_str.strip())
        except ValueError:
            dias_uteis = None
        return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}
    elif len(partes) == 3:
        prazo_str, resp, obs = partes
        try:
            dias_uteis = int(prazo_str.strip())
        except ValueError:
            dias_uteis = None
        return {'dias_uteis': dias_uteis, 'responsavel': resp.strip(), 'observacao': obs.strip()}

    return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}


# =============================================================================
# GIGS
# =============================================================================


def criar_gigs(
    driver: WebDriver,
    dias_uteis: Any = None,
    responsavel: Optional[str] = None,
    observacao: Optional[str] = None,
    timeout: Union[int, float] = 10,
    log: bool = True,
) -> bool:
    """Cria atividade GIGS na aba /detalhe.

    Suporta multiplas assinaturas:
    - criar_gigs(driver, "observacao simples") -> apenas observacao
    - criar_gigs(driver, "7/xs carta") -> prazo/observacao
    - criar_gigs(driver, "7/xs/carta urgente") -> prazo/responsavel/observacao
    - criar_gigs(driver, 7, "xs", "carta") -> parametros separados

    Fluxo:
    1. Clica "Nova Atividade"
    2. Preenche campos (dias, responsavel, observacao)
    3. Salva e confirma

    Args:
        driver: WebDriver Selenium.
        dias_uteis: Dias uteis para prazo, ou string unificada, ou None.
        responsavel: Nome do responsavel (opcional).
        observacao: Texto da observacao.
        timeout: Timeout para operacoes (default 10s).
        log: Habilitar logs (default True).

    Returns:
        True se GIGS criada com sucesso, False caso contrario.
    """
    # Parse string unificada se necessario
    if isinstance(dias_uteis, str) and responsavel is None and observacao is None:
        parsed = _parse_gigs_string(dias_uteis)
        dias_uteis = parsed['dias_uteis']
        responsavel = parsed['responsavel']
        observacao = parsed['observacao']

    # Compatibilidade: 2 params = dias_uteis + observacao
    if observacao is None and responsavel is not None:
        observacao = responsavel
        responsavel = None

    try:
        if log:
            info = f"{dias_uteis or '-'}/{responsavel or '-'}/{observacao or '-'}"
            logger.debug("[GIGS] Criando: %s", info)

        if log:
            logger.debug("[GIGS] Clicando Nova Atividade...")
        btn_nova = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[.//span[contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                "'nova atividade')] "
                "or contains(translate(@aria-label, "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                "'nova atividade')]"
            ))
        )
        btn_nova.click()
        time.sleep(1)

        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')
            )
        )
        if log:
            logger.debug("[GIGS] Formulario aberto")

        if dias_uteis:
            campo_dias = driver.find_element(
                By.CSS_SELECTOR, 'input[formcontrolname="dias"]'
            )
            campo_dias.clear()
            campo_dias.send_keys(str(dias_uteis))
            time.sleep(0.3)
            if log:
                logger.debug("[GIGS] Prazo: %s dias", dias_uteis)

        if responsavel:
            campo_resp = driver.find_element(
                By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]'
            )
            campo_resp.clear()
            campo_resp.send_keys(responsavel)
            time.sleep(0.5)
            campo_resp.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.2)
            campo_resp.send_keys(Keys.ENTER)
            if log:
                logger.debug("[GIGS] Responsavel: %s", responsavel)

        if observacao:
            campo_obs = driver.find_element(
                By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'
            )
            campo_obs.clear()
            campo_obs.send_keys(observacao)
            # Forcar evento para Angular detectar
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                campo_obs,
            )
            time.sleep(0.3)
            if log:
                obs_preview = (
                    observacao[:50] + '...'
                    if len(observacao) > 50
                    else observacao
                )
                logger.debug("[GIGS] Observacao: %s", obs_preview)

        # Salvar
        if log:
            logger.debug("[GIGS] Salvando...")
        btn_salvar = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Salvar')]")
            )
        )
        btn_salvar.click()

        # Aguardar confirmacao
        time.sleep(0.3)
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//snack-bar-container//span[contains(normalize-space(.), "
                    "'Atividade salva com sucesso')]"
                ))
            )
            if log:
                logger.debug("[GIGS] Atividade criada com sucesso")
            return True
        except TimeoutException:
            if log:
                logger.warning("[GIGS] Confirmacao nao detectada, assumindo sucesso")
            return True

    except Exception as e:
        if log:
            logger.error("ERRO em criar_gigs: %s: %s", type(e).__name__, e)
        return False


# =============================================================================
# COMENTARIO
# =============================================================================


def criar_comentario(
    driver: WebDriver,
    observacao: str,
    visibilidade: str = 'LOCAL',
    timeout: Union[int, float] = 10,
    log: bool = True,
) -> bool:
    """Cria comentario GIGS na aba /detalhe.

    Args:
        driver: WebDriver do Selenium.
        observacao: Texto do comentario.
        visibilidade: 'LOCAL' (padrao), 'RESTRITA' ou 'GLOBAL'.
        timeout: Timeout para operacoes (default 10s).
        log: Habilitar logs (default True).

    Returns:
        True se comentario criado com sucesso, False caso contrario.
    """
    try:
        if log:
            com_preview = (
                observacao[:50] + '...'
                if len(observacao) > 50
                else observacao
            )
            logger.debug("[COMENTARIO] Criando: %s", com_preview)

        # 1. Clicar "Novo Comentario"
        if log:
            logger.debug("[COMENTARIO] Clicando Novo Comentario...")
        btn_novo = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(., 'Novo Coment\u00e1rio') "
                "or contains(., 'Novo coment\u00e1rio') "
                "or contains(., 'Novo Comentario') "
                "or contains(., 'Novo comentario')]"
            ))
        )
        btn_novo.click()
        time.sleep(1)

        # 2. Aguardar formulario
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                'textarea[formcontrolname="descricao"], '
                'textarea[name="descricao"]',
            ))
        )
        if log:
            logger.debug("[COMENTARIO] Formulario aberto")

        # 3. Preencher observacao/descricao
        campo_obs = driver.find_element(
            By.CSS_SELECTOR,
            'textarea[formcontrolname="descricao"], '
            'textarea[name="descricao"]',
        )
        campo_obs.clear()
        campo_obs.send_keys(observacao)
        # Forcar evento para Angular
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            campo_obs,
        )
        time.sleep(0.3)
        if log:
            logger.debug("[COMENTARIO] Descricao preenchida")

        # 4. Selecionar visibilidade (radio buttons)
        visibilidade_upper = visibilidade.upper()
        if log:
            logger.debug("[COMENTARIO] Visibilidade: %s", visibilidade_upper)

        try:
            radio_buttons = driver.find_elements(
                By.CSS_SELECTOR,
                'pje-gigs-comentarios-cadastro mat-radio-button, '
                'mat-radio-button',
            )
            if len(radio_buttons) >= 3:
                index_map = {'LOCAL': 0, 'RESTRITA': 1, 'GLOBAL': 2}
                idx = index_map.get(visibilidade_upper, 0)
                radio_input = radio_buttons[idx].find_element(
                    By.CSS_SELECTOR, 'input'
                )
                # Angular Material oculta o input com cdk-visually-hidden;
                # JS click e necessario pois scroll/interacao direta falha.
                driver.execute_script("arguments[0].click();", radio_input)
                time.sleep(0.3)

                if visibilidade_upper == 'RESTRITA':
                    if log:
                        logger.debug(
                            "[COMENTARIO] Visibilidade RESTRITA - "
                            "pode requerer selecao de usuarios"
                        )
                    time.sleep(0.5)
        except Exception as e:
            if log:
                logger.warning(
                    "[COMENTARIO][AVISO] Nao foi possivel "
                    "selecionar visibilidade: %s",
                    e,
                )

        # 5. Salvar
        if log:
            logger.debug("[COMENTARIO] Salvando...")
        btn_salvar = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Salvar')]")
            )
        )
        btn_salvar.click()
        time.sleep(1)

        # 6. Verificar se modal fechou
        time.sleep(1)
        try:
            modals = driver.find_elements(
                By.CSS_SELECTOR, 'mat-dialog-container'
            )
            modal_aberto = any(m.is_displayed() for m in modals)
            if not modal_aberto:
                if log:
                    logger.debug("[COMENTARIO] Comentario criado com sucesso")
                return True
            else:
                driver.find_element(
                    By.TAG_NAME, 'body'
                ).send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                if log:
                    logger.debug(
                        "[COMENTARIO] Comentario criado "
                        "(modal fechado manualmente)"
                    )
                return True
        except Exception as e:
            if log:
                logger.debug("[COMENTARIO] Comentario criado")
            return True

    except Exception as e:
        if log:
            logger.error(
                "ERRO em criar_comentario: %s: %s",
                type(e).__name__,
                e,
            )
        return False


# =============================================================================
# LEMBRETE / POST-IT
# =============================================================================


def criar_lembrete_posit(
    driver: WebDriver,
    titulo: str,
    conteudo: str,
    debug: bool = False,
) -> bool:
    """Cria lembrete/post-it generico com titulo e conteudo customizaveis.

    Args:
        driver: WebDriver Selenium.
        titulo: Texto do titulo.
        conteudo: Texto do conteudo.
        debug: Log detalhado (default: False).

    Returns:
        True se sucesso, False caso contrario.
    """
    try:
        if debug:
            logger.debug(
                '[LEMBRETE][POSIT] Criando: "%s" / "%s"', titulo, conteudo
            )

        menu_clicked = aguardar_e_clicar(driver, '.fa-bars', log=debug)
        time.sleep(0.8)

        seletores_lembrete = [
            'button[aria-label*="Lembrete"]',
            'button[title*="Lembrete"]',
            'pje-icone-post-it button',
            '.lista-itens-menu li:nth-child(16) button',
        ]

        for seletor in seletores_lembrete:
            try:
                lembrete_clicked = aguardar_e_clicar(
                    driver, seletor, timeout=3, log=False
                )
                if lembrete_clicked:
                    if debug:
                        logger.debug(
                            '[LEMBRETE][POSIT] Icone: %s', seletor
                        )
                    break
            except Exception:
                continue

        time.sleep(0.8)

        aguardar_e_clicar(driver, '.mat-dialog-content', log=False)
        time.sleep(0.8)

        titulo_elem = esperar_elemento(
            driver, '#tituloPostit', timeout=5
        )
        if titulo_elem:
            preencher_campo(titulo_elem, titulo)

        conteudo_elem = esperar_elemento(
            driver, '#conteudoPostit', timeout=5
        )
        if conteudo_elem:
            preencher_campo(conteudo_elem, conteudo)

        seletores_salvar = [
            'button[color="primary"]',
            '.mat-raised-button:not([disabled])',
            'button[type="submit"]',
        ]

        for seletor in seletores_salvar:
            try:
                if aguardar_e_clicar(driver, seletor, timeout=3, log=False):
                    break
            except Exception:
                continue

        time.sleep(0.8)
        if debug:
            logger.debug('[LEMBRETE][POSIT] "%s" criado', titulo)
        return True

    except Exception as e:
        if debug:
            logger.error(
                "ERRO em criar_lembrete_posit: %s: %s",
                type(e).__name__,
                e,
            )
        return False


# =============================================================================
# INDEXACAO DE PROCESSOS
# =============================================================================


def indexar_processos(
    driver: WebDriver,
) -> List[Tuple[str, WebElement]]:
    """Indexa processos de forma robusta, evitando stale elements.

    Busca elementos frescos a cada iteracao para evitar problemas de
    StaleElementReferenceException.

    Args:
        driver: WebDriver Selenium.

    Returns:
        Lista de tuplas (proc_id, linha_element).
    """
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos: List[Tuple[str, WebElement]] = []

    def obter_linhas_frescas():
        return driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')

    linhas = obter_linhas_frescas()
    logger.debug('[INDEXAR] Encontradas %s linhas para processar', len(linhas))

    for idx in range(len(linhas)):
        try:
            linhas_atuais = obter_linhas_frescas()

            if idx >= len(linhas_atuais):
                logger.debug(
                    '[INDEXAR][SKIP] Linha %s: DOM mudou, '
                    'menos linhas disponiveis',
                    idx + 1,
                )
                continue

            linha = linhas_atuais[idx]

            links = linha.find_elements(By.CSS_SELECTOR, 'a')
            texto = ''

            if links:
                texto = links[0].text.strip()
            else:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                if tds:
                    texto = tds[0].text.strip()

            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem numero]'

            processos.append((num_proc, linha))

        except Exception as e:
            logger.debug(
                '[INDEXAR][ERRO] Linha %s: %s '
                '(elemento pode ter ficado stale)',
                idx + 1,
                e,
            )
            continue

    logger.debug(
        '[INDEXAR] Processamento concluido: %s processos indexados',
        len(processos),
    )
    return processos


def reindexar_linha(
    driver: WebDriver, proc_id: str
) -> Optional[WebElement]:
    """Reindexar linha quando elemento fica stale.

    Nao navega automaticamente - respeita a pagina atual do modulo.

    Args:
        driver: WebDriver Selenium.
        proc_id: ID do processo a reindexar.

    Returns:
        WebElement da linha encontrada ou None se nao encontrada.
    """
    try:
        # Verificar se ainda estamos em uma pagina valida do PJE
        url_atual = driver.current_url
        if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
            logger.error("ACESSO NEGADO detectado na URL: %s", url_atual)
            return None

        if 'pje.trt2.jus.br' not in url_atual:
            logger.error("URL nao e do PJE: %s", url_atual)
            return None

        logger.debug(
            '[REINDEXAR] Tentando reindexar na pagina atual: %s', url_atual
        )

        # Buscar linhas na pagina atual (diferentes seletores)
        possible_selectors = [
            'tr.cdk-drag',         # Atividades (PEC)
            'tr',                   # Documentos internos (M1)
            'tbody tr',             # Outras tabelas
            '.linha-processo',      # Seletor alternativo
        ]

        linhas_atuais = []
        for selector in possible_selectors:
            try:
                linhas_temp = driver.find_elements(
                    By.CSS_SELECTOR, selector
                )
                if linhas_temp:
                    linhas_atuais = linhas_temp
                    logger.debug(
                        '[REINDEXAR] Usando seletor %s: '
                        '%s linhas encontradas',
                        selector,
                        len(linhas_atuais),
                    )
                    break
            except Exception:
                continue

        if not linhas_atuais:
            logger.error(
                "Nenhuma linha encontrada na pagina "
                "com os seletores testados"
            )
            return None

        logger.debug(
            '[REINDEXAR] Buscando %s entre %s linhas...',
            proc_id,
            len(linhas_atuais),
        )

        for idx, linha_temp in enumerate(linhas_atuais):
            try:
                if not linha_temp.is_displayed():
                    continue
            except Exception:
                continue

            try:
                texto_linha = ""

                # Estrategia 1: Links
                links = linha_temp.find_elements(By.CSS_SELECTOR, 'a')
                if links:
                    texto_linha = links[0].text.strip()
                else:
                    # Estrategia 2: Celulas td
                    tds = linha_temp.find_elements(By.TAG_NAME, 'td')
                    if tds:
                        for td in tds[:3]:
                            td_text = td.text.strip()
                            if proc_id in td_text:
                                texto_linha = td_text
                                break
                        if not texto_linha:
                            texto_linha = tds[0].text.strip()
                    else:
                        # Estrategia 3: Texto geral da linha
                        texto_linha = linha_temp.text.strip()

                if proc_id in texto_linha:
                    logger.info(
                        "Processo %s encontrado na linha %s",
                        proc_id,
                        idx + 1,
                    )
                    return linha_temp

            except Exception:
                continue

        logger.error(
            "Processo %s nao encontrado nas %s linhas da pagina atual",
            proc_id,
            len(linhas_atuais),
        )
        return None

    except Exception as e:
        logger.error("Erro geral na reindexacao: %s", e)
        return None


# =============================================================================
# ABRIR DETALHES DO PROCESSO
# =============================================================================


def abrir_detalhes_processo(
    driver: WebDriver, linha: WebElement
) -> bool:
    """Abre detalhes do processo a partir de uma linha da tabela.

    Tenta encontrar o bota de detalhes via matTooltip, ou clica
    no primeiro bota/link disponivel na linha.

    Args:
        driver: WebDriver Selenium.
        linha: WebElement da linha da tabela.

    Returns:
        True se conseguiu abrir detalhes, False caso contrario.
    """
    try:
        btn = linha.find_element(
            By.CSS_SELECTOR, '[mattooltip*="Detalhes do Processo"]'
        )
    except Exception:
        try:
            btn = linha.find_element(By.CSS_SELECTOR, 'button, a')
        except Exception:
            return False

    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
    driver.execute_script("arguments[0].click();", btn)
    return True
