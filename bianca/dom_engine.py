# -*- coding: utf-8 -*-
"""
bianca/dom_engine.py - DOM Eletronico engine.

Adapted from Triagem/dom.py for the bianca standalone project.
Processes processes with electronic domicile (DOM Electronico).

Fluxo:
  1. Navega para URL_LISTA_DOM
  2. Aplica filtro de fase (conhecimento)
  3. Navega para painel de atividades e aplica filtro dom.e
  4. Indexa processos e processa cada um com callback do bucket 2
     (remocao de chips, criacao de lembrete, criacao de PEC)
"""

import time
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bianca.atos_utils import def_chip
from atos.wrappers_pec import pec_arord, pec_arsum
from bianca.extracao import (
    abrir_detalhes_processo,
    criar_comentario,
    criar_gigs,
    criar_lembrete_posit,
    indexar_processos,
    reindexar_linha,
)
from bianca.selenium_utils import (
    aguardar_e_clicar,
    aplicar_filtro_100,
    esperar_elemento,
    filtrofases,
    safe_click,
    trocar_para_nova_aba,
)
from bianca.utils import logger

# =============================================================================
# Constantes
# =============================================================================

LIST_URL = "https://pje.trt2.jus.br/pjekz/painel/global/todos/lista-processos"
URL_ATIVIDADES = "https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades"

# =============================================================================
# Helpers internos
# =============================================================================


def _determinar_bucket(tem_audiencia: bool, tem_ata: bool) -> str:
    """Determina qual bucket de processamento aplicar ao processo.

    Lógica:
      - Bucket 1: Sem audiência OU (tem audiência E tem ata)
      - Bucket 2: Tem audiência E não tem ata

    Args:
        tem_audiencia: True se o processo tem audiência agendada.
        tem_ata: True se a timeline contém ata de audiência.

    Returns:
        String "bucket1" ou "bucket2".

    Exemplos:
        >>> _determinar_bucket(False, False)
        'bucket1'
        >>> _determinar_bucket(True, True)
        'bucket1'
        >>> _determinar_bucket(True, False)
        'bucket2'
    """
    if not tem_audiencia or tem_ata:
        return "bucket1"
    else:
        return "bucket2"


def _verificar_acesso_negado(driver: WebDriver, contexto: str) -> None:
    """Verifica se a URL atual indica acesso negado e lanca excecao em caso positivo.

    Args:
        driver: WebDriver Selenium.
        contexto: String de contexto para identificacao no log.

    Raises:
        Exception: Com prefixo RESTART_DRIVER se acesso negado detectado.
    """
    try:
        url_atual = driver.current_url
        if "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower():
            msg = f"RESTART_DRIVER: acesso negado em {contexto}"
            logger.warning("[DOMICILIO_ELETRONICO] %s", msg)
            raise Exception(msg)
    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            raise
        logger.debug("[DOMICILIO_ELETRONICO] Falha ao verificar acesso negado: %s", e)


def has_dom_eletronico_reminder(driver: WebDriver) -> bool:
    """Verifica se ja existe lembrete Dom Eletronico no processo.

    Busca por elementos mat-panel-title com classe post-it-titulo
    e verifica se o texto contem "Dom Eletronico", "DomicEletr"
    ou "DomElet".

    Args:
        driver: WebDriver Selenium.

    Returns:
        True se um lembrete DOM eletronico ja existe.
    """
    try:
        titles = driver.find_elements(
            By.CSS_SELECTOR, "mat-panel-title.post-it-titulo"
        )
        for title in titles:
            title_text = title.text.strip()
            if (
                "Dom Eletronico" in title_text
                or "DomicEletr" in title_text
                or "DomElet" in title_text
            ):
                return True
        return False
    except Exception:
        return False


def _extrair_conteudo_lembrete_dom(driver: WebDriver) -> Optional[str]:
    """Extrai o conteúdo do lembrete Dom Eletronico se existir.

    Procura pelo elemento mat-panel-title com "Dom Eletronico", "DomicEletr"
    ou "DomElet" e retorna o texto da descrição (mat-panel-description).

    Args:
        driver: WebDriver Selenium.

    Returns:
        String com conteúdo do lembrete, ou None se não encontrado.
    """
    try:
        panels = driver.find_elements(
            By.CSS_SELECTOR, "mat-expansion-panel"
        )
        for panel in panels:
            try:
                title_elem = panel.find_element(
                    By.CSS_SELECTOR, "mat-panel-title.post-it-titulo"
                )
                title_text = title_elem.text.strip()
                if (
                    "Dom Eletronico" in title_text
                    or "DomicEletr" in title_text
                    or "DomElet" in title_text
                ):
                    # Encontrou o painel, agora extrair descrição
                    try:
                        desc_elem = panel.find_element(
                            By.CSS_SELECTOR, "mat-panel-description"
                        )
                        conteudo = desc_elem.text.strip()
                        return conteudo if conteudo else None
                    except Exception:
                        return None
            except Exception:
                continue
        return None
    except Exception:
        return None
        return False


def _checar_empresas_api(id_processo: str, driver: WebDriver) -> str:
    """Busca nomes das empresas com expedientes DOM abertos via API.

    Substitui checar_empresas(driver) para evitar abertura de modal.
    Filtra expedientes nao fechados cujo meio/tipo indique domicilio eletronico
    ou onde dataCiencia seja nula (prazo expirado sem ciencia).

    Args:
        id_processo: ID interno do processo (string numerica).
        driver: WebDriver para extrair sessao.

    Returns:
        String com nomes separados por virgula, ou string vazia em caso de erro.
    """
    try:
        from bianca.api_client import PjeApiClient, session_from_driver as _sfp
        _sess, _base = _sfp(driver)
        _client = PjeApiClient(_sess, _base)
        expedientes = _client.expedientes_processo(id_processo)
        if not expedientes:
            return ''
        nomes: list = []
        for exp in expedientes:
            # só processa Domicílio Eletrônico
            if (exp.get('meioExpedienteEnum') or '').upper() != 'DOMICILIO_ELETRONICO':
                continue
            nome = (exp.get('nomePessoaParte') or '').strip()
            if not nome:
                continue
            # incluir se: ciência automática (sistema) OU sem dataCiencia (prazo expirado)
            ciencia_sistema = exp.get('cienciaViaSistema', False)
            data_ciencia = exp.get('dataCiencia')
            if (ciencia_sistema or data_ciencia is None) and nome not in nomes:
                nomes.append(nome)
        return ', '.join(nomes)
    except Exception as e:
        logger.warning('[DOMICILIO_ELETRONICO] _checar_empresas_api falhou: %s', e)
        return ''


def _tem_ata_audiencia(id_processo: str, driver: WebDriver) -> bool:
    """Verifica se ha Ata de Audiencia na timeline do processo via API.

    Args:
        id_processo: ID interno do processo (string numerica).
        driver: WebDriver para extrair sessao.

    Returns:
        True se encontrou item de ata de audiencia na timeline.
    """
    import unicodedata

    def _norm(s: str) -> str:
        return unicodedata.normalize('NFKD', (s or '').lower()).encode('ascii', 'ignore').decode()

    try:
        from bianca.api_client import PjeApiClient, session_from_driver as _sfp
        _sess, _base = _sfp(driver)
        _client = PjeApiClient(_sess, _base)
        _tl = _client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=True)
        if not _tl:
            return False
        for item in _tl:
            texto = _norm(item.get('tipo') or '') + ' ' + _norm(item.get('titulo') or '')
            if 'ata' in texto and 'audienci' in texto:
                logger.info('[DOMICILIO_ELETRONICO] Ata de audiencia encontrada na timeline de %s', id_processo)
                return True
        return False
    except Exception as e:
        logger.warning('[DOMICILIO_ELETRONICO] _tem_ata_audiencia falhou para %s: %s', id_processo, e)
        return False


    """Le o painel de expedientes e retorna nomes de empresas com falha de confirmacao.

    Args:
        driver: WebDriver Selenium.

    Returns:
        String com nomes de empresas separados por virgula, ou string vazia.
    """
    empresas = []
    try:
        if not aguardar_e_clicar(driver, "#botao-menu", timeout=10, log=False):
            logger.warning("[DOMICILIO_ELETRONICO] checar_empresas: menu nao encontrado")
            return ""

        if not aguardar_e_clicar(
            driver, 'button[aria-label="Expedientes"]', timeout=8, log=False
        ):
            logger.warning("[DOMICILIO_ELETRONICO] checar_empresas: Expedientes nao encontrado")
            return ""

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tbody tr"))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 2:
                    continue
                nome_empresa = cols[0].text.strip()
                confirmacao = cols[-1].text.strip().lower()
                if any(
                    token in confirmacao
                    for token in ["expirado", "automatica", "automtica", "erro"]
                ):
                    if nome_empresa:
                        empresas.append(nome_empresa)
            except Exception:
                continue
    except Exception as e:
        logger.warning(
            "[DOMICILIO_ELETRONICO] checar_empresas: erro ao ler painel de expedientes: %s", e
        )
    finally:
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            WebDriverWait(driver, 2).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, ".cdk-overlay-backdrop")
                )
            )
        except Exception:
            pass

    unique_empresas: List[str] = []
    for nome in empresas:
        if nome not in unique_empresas:
            unique_empresas.append(nome)
    return ", ".join(unique_empresas)


def is_processo_100_digital(driver: WebDriver) -> bool:
    """Verifica se o processo e 100% digital baseado na presenca da logo no cabecalho.

    Args:
        driver: WebDriver Selenium.

    Returns:
        True se o processo possui a logo do juizo 100% digital.
    """
    try:
        logo_juizo = driver.find_elements(
            By.CSS_SELECTOR, 'img.logo_juizo[alt="Juizo 100% Digital"]'
        )
        return len(logo_juizo) > 0
    except Exception:
        return False


# =============================================================================
# Callbacks
# =============================================================================


def callback_bucket1(driver: WebDriver, tipo: str = "desconhecido") -> bool:
    """Callback para bucket 1 (sem audiencia): remove chips domicilio eletronico.

    Args:
        driver: WebDriver na aba de detalhes do processo.
        tipo: Tipo do processo (para log).

    Returns:
        True se a operacao foi bem-sucedida.
    """
    numero = getattr(driver, "_numero_processo_lista", "desconhecido")
    logger.info("[DOMICILIO_ELETRONICO][B1][CALLBACK] Executando acoes para %s", numero)

    chips_domicilio = [
        "Domicilio Eletronico - Ciencia Automatica",
        "Domicilio Eletronico - Prazo de Ciencia Expirado",
        "Domicilio Eletronico - Prazo de Resposta Excedido",
        "Domicilio Eletronico - Erro na Transmissao",
    ]
    result = def_chip(
        driver,
        numero_processo=numero,
        observacao="Remover chips domicilio eletronico",
        chips_para_remover=chips_domicilio,
        debug=True,
    )
    logger.info("[DOMICILIO_ELETRONICO][B1][CALLBACK] def_chip result: %s", result)
    return result


def callback_bucket2(
    driver: WebDriver, tipo_processo: str = "desconhecido"
) -> bool:
    """Callback para bucket 2 (com audiencia): acoes completas DOM.

    Fluxo:
      1. Remove chips de ciencia expirado e resposta excedido
      2. Cria GIGS dom.e
      3. Verifica lembrete Dom Eletronico
         - Se nao existe: checa empresas, cria lembrete DomicEletr
      4. Executa PEC conforme tipo e se e 100% digital

    Args:
        driver: WebDriver na aba de detalhes do processo.
        tipo_processo: String com tipo do processo (ATOrd, ATSum, ACum).

    Returns:
        True se o PEC foi criado com sucesso.
    """
    numero = getattr(driver, "_numero_processo_lista", "desconhecido")

    logger.info(
        "[DOMICILIO_ELETRONICO][B2][CALLBACK] Executando acoes para %s (%s)", numero, tipo_processo
    )

    # Extrair ID do processo da URL (necessario para _checar_empresas_api)
    import re as _re
    id_processo = None
    try:
        m_id = _re.search(r'/processo/(\d+)/', driver.current_url)
        if m_id:
            id_processo = m_id.group(1)
    except Exception:
        pass

    if not id_processo:
        logger.warning(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Nao foi possivel extrair id_processo da URL para %s", numero
        )

    # 1. Remover chips de ciencia expirado e resposta excedido
    chips_ciencia_resposta = [
        "Domicilio Eletronico - Ciencia Automatica",
        "Domicilio Eletronico - Prazo de Ciencia Expirado",
        "Domicilio Eletronico - Prazo de Resposta Excedido",
    ]

    result_def_chip = def_chip(
        driver,
        numero_processo=numero,
        observacao="Remover ciencia expirado e resposta excedido",
        chips_para_remover=chips_ciencia_resposta,
        debug=True,
    )
    logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] def_chip result: %s", result_def_chip)

    # Verificar acesso negado apos def_chip
    try:
        _verificar_acesso_negado(driver, f"DOM_{numero}_def_chip")
    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            logger.warning(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Acesso negado detectado apos def_chip"
                " - propagando para recuperacao"
            )
            raise
        else:
            logger.error(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro inesperado na verificacao"
                " de acesso negado: %s",
                e,
            )

    # 4. Verificar lembrete Dom Eletronico (nova lógica simplificada)
    lembrete_existe = has_dom_eletronico_reminder(driver)
    executar_pec = False  # Flag para determinar se PEC deve ser executada
    
    if lembrete_existe:
        # Lembrete existe - extrair conteúdo
        conteudo = _extrair_conteudo_lembrete_dom(driver)
        logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Lembrete existente encontrado")
        
        if conteudo and ("via correio" in conteudo.lower() or "correio enviado" in conteudo.lower()):
            # Sub-case 2a: Via correio já registrado
            logger.info(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Lembrete contem 'via correio' ou 'correio enviado'"
                " - criando comentario e apagando chips (SEM PEC)"
            )
            
            # Criar comentário Bianca
            try:
                comentario = "Dom - verificado correio"
                criar_comentario(driver, comentario, debug=True)
                logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Comentario criado: %s", comentario)
            except Exception as e:
                logger.warning(
                    "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro ao criar comentario: %s", e
                )
            
            # Apagar chips de domicilio
            result_chips = def_chip(
                driver,
                numero_processo=numero,
                observacao="Remover chips domicilio - correio registrado",
                chips_para_remover=[
                    "Domicilio Eletronico - Ciencia Automatica",
                    "Domicilio Eletronico - Prazo de Ciencia Expirado",
                    "Domicilio Eletronico - Prazo de Resposta Excedido",
                ],
                debug=True,
            )
            logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] def_chip result: %s", result_chips)
            
            # NÃO executar PEC
            executar_pec = False
        else:
            # Sub-case: Lembrete existe mas não é "via correio" ou "correio enviado"
            logger.warning(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Lembrete existe mas nao contem 'via correio' ou 'correio enviado'"
                " - pulando tudo (sem comentario, sem chips, sem PEC)"
            )
            executar_pec = False
    else:
        # Sub-case 2b: Sem lembrete - executar fluxo completo
        logger.info(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Sem lembrete Dom Eletronico"
            " - executando fluxo completo (empresas+lembrete+comentario+chips+PEC)"
        )
        
        # Chamar _checar_empresas_api
        empresas_falha = _checar_empresas_api(id_processo, driver)
        conteudo_lembrete = "Ciencia negativa Domicilio: Correio enviado"
        if empresas_falha:
            conteudo_lembrete += f" ({empresas_falha})"
        
        # Criar lembrete
        logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Criando lembrete DomicEletr")
        lembrete_result = criar_lembrete_posit(
            driver, titulo="DomicEletr", conteudo=conteudo_lembrete, debug=True
        )
        logger.info(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Lembrete criado: %s", lembrete_result
        )
        
        # Aguardar salvamento completo do lembrete
        if lembrete_result:
            logger.info(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Aguardando salvamento completo do lembrete..."
            )
            try:
                WebDriverWait(driver, 8).until(
                    lambda d: any(
                        "DomicEletr" in el.text
                        for el in d.find_elements(
                            By.CSS_SELECTOR, "mat-panel-title.post-it-titulo"
                        )
                    )
                )
            except Exception:
                pass
        
        # Criar comentário Bianca
        try:
            comentario = "Dom - criado lembrete e enviado correio"
            criar_comentario(driver, comentario, debug=True)
            logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Comentario criado: %s", comentario)
        except Exception as e:
            logger.warning(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro ao criar comentario: %s", e
            )
        
        # Apagar chips de domicilio
        result_chips = def_chip(
            driver,
            numero_processo=numero,
            observacao="Remover chips domicilio - lembrete criado",
            chips_para_remover=[
                "Domicilio Eletronico - Ciencia Automatica",
                "Domicilio Eletronico - Prazo de Ciencia Expirado",
                "Domicilio Eletronico - Prazo de Resposta Excedido",
            ],
            debug=True,
        )
        logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] def_chip result: %s", result_chips)
        
        # Executar PEC
        executar_pec = True
        
        # Verificar acesso negado apos criacao do lembrete
        try:
            _verificar_acesso_negado(driver, f"DOM_{numero}_lembrete")
        except Exception as e:
            if "RESTART_DRIVER" in str(e):
                logger.warning(
                    "[DOMICILIO_ELETRONICO][B2][CALLBACK] Acesso negado detectado apos lembrete"
                    " - propagando para recuperacao"
                )
                raise
            else:
                logger.error(
                    "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro inesperado na verificacao"
                    " de acesso negado: %s",
                    e,
                )

    # 5. Executar PEC AR (apenas se flag executar_pec = True)
    if not executar_pec:
        logger.info(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] Pulando PEC (lembrete com via correio ou nenhuma acao necessaria)"
        )
        return True

    if "ATSum" in tipo_processo:
        logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Criando PEC AR Sumaria (pec_arsum)")
        pec_wrapper = pec_arsum
    else:
        # ATOrd, ACum ou outros
        logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Criando PEC AR Ordinaria (pec_arord)")
        pec_wrapper = pec_arord

    # Verificar abas antes da PEC
    abas_antes = len(driver.window_handles)
    logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Abas antes da PEC: %s", abas_antes)

    result_pec = pec_wrapper(driver, debug=True)
    logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] PEC result: %s", result_pec)

    # Verificar acesso negado apos execucao da PEC
    try:
        _verificar_acesso_negado(driver, f"DOM_{numero}_pec")
    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            logger.warning(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Acesso negado detectado apos PEC"
                " - propagando para recuperacao"
            )
            raise
        else:
            logger.error(
                "[DOMICILIO_ELETRONICO][B2][CALLBACK] Erro inesperado na verificacao"
                " de acesso negado: %s",
                e,
            )

    # Verificar abas depois da PEC
    abas_depois = len(driver.window_handles)
    logger.info("[DOMICILIO_ELETRONICO][B2][CALLBACK] Abas depois da PEC: %s", abas_depois)

    if abas_depois <= abas_antes:
        logger.warning(
            "[DOMICILIO_ELETRONICO][B2][CALLBACK] AVISO: Nenhuma nova aba foi aberta pela PEC!"
        )
        return False

    return result_pec


# =============================================================================
# Filtro de chips DOM (helper)
# =============================================================================


def _filtro_chips_dom(
    driver: WebDriver, chips_alvo: List[str]
) -> bool:
    """Aplica filtro de chips para domicilio eletronico no painel global.

    Args:
        driver: WebDriver Selenium.
        chips_alvo: Lista de strings para filtrar (ex: 'domicilio eletronico expirado').

    Returns:
        True se ao menos um chip foi selecionado com sucesso.
    """
    logger.info("[DOMICILIO_ELETRONICO] Aplicando filtro de chips: %s", chips_alvo)

    chips_mapeamento = {
        "domicilio eletronico expirado": (
            "Domicilio Eletronico - Prazo de Ciencia Expirado"
        ),
        "domicilio eletronico expedido": (
            "Domicilio Eletronico - Prazo de Resposta Excedido"
        ),
        "domicilio eletronico erro na transmissao": (
            "Domicilio Eletronico - Erro na Transmissao"
        ),
    }

    chips_alvo_mapeados = [
        chips_mapeamento.get(chip, chip) for chip in chips_alvo
    ]

    # Encontrar seletor de chips
    chips_element = None
    try:
        chips_element = driver.find_element(
            By.XPATH, "//span[contains(text(), 'Chips')]"
        )
    except Exception:
        try:
            seletor = "span.ng-tns-c82-22.ng-star-inserted"
            for elem in driver.find_elements(By.CSS_SELECTOR, seletor):
                if "Chips" in elem.text:
                    chips_element = elem
                    break
        except Exception:
            logger.error("[DOMICILIO_ELETRONICO] Elemento chips nao encontrado")
            return False

    if not chips_element:
        logger.error("[DOMICILIO_ELETRONICO] Elemento chips nao encontrado")
        return False

    # Clicar para abrir dropdown
    driver.execute_script("arguments[0].click();", chips_element)
    time.sleep(1)

    # Aguardar painel
    painel_selector = (
        ".mat-select-panel-wrap.ng-trigger-transformPanelWrap"
    )
    try:
        painel = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, painel_selector)
            )
        )
    except Exception as e:
        logger.error("[DOMICILIO_ELETRONICO] Painel de chips nao apareceu: %s", e)
        return False

    # Aguardar opcoes carregarem
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "mat-option")
            )
        )
    except Exception:
        pass

    opcoes = painel.find_elements(By.XPATH, ".//mat-option")
    chips_selecionados: List[str] = []

    for chip in chips_alvo_mapeados:
        for opcao in opcoes:
            try:
                texto = opcao.text.strip()
                if chip in texto and opcao.is_displayed():
                    driver.execute_script("arguments[0].click();", opcao)
                    chips_selecionados.append(chip)
                    try:
                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "mat-option.mat-selected")
                            )
                        )
                    except Exception:
                        pass
                    break
            except Exception:
                continue

    # Aplicar filtro
    try:
        botao_filtrar = driver.find_element(
            By.CSS_SELECTOR, 'button[aria-label="Filtrar"]'
        )
        driver.execute_script("arguments[0].click();", botao_filtrar)
        # Aguardar recarregamento da tabela
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "tbody tr.tr-class")
                )
            )
        except Exception:
            pass
    except Exception as e:
        logger.error("[DOMICILIO_ELETRONICO] Erro ao clicar filtrar: %s", e)
        return False

    logger.info("[DOMICILIO_ELETRONICO] Chips aplicados: %s", chips_selecionados)
    return len(chips_selecionados) > 0


# =============================================================================
# Navegacao e filtros no painel de atividades
# =============================================================================


def navigate_to_activities_and_filter(driver: WebDriver) -> bool:
    """Navega para o painel de atividades e aplica filtro dom.e.

    Fluxo:
      1. Navega para URL_ATIVIDADES
      2. Remove chip "Vencidas" se existir
      3. Clica icone fa-pen e preenche descricao com "dom.e"
      4. Aplica filtro 100 itens por pagina

    Args:
        driver: WebDriver Selenium.

    Returns:
        True se a navegacao e filtros foram bem-sucedidos.
    """
    try:
        # 1. Navegar para painel de atividades
        driver.get(URL_ATIVIDADES)
        WebDriverWait(driver, 10).until(EC.url_contains("atividades"))
        logger.info("[DOMICILIO_ELETRONICO] Navegado para painel de atividades")

        # 2. Remover chip "Vencidas" se existir
        try:
            chips = driver.find_elements(By.CSS_SELECTOR, "mat-chip")
            removido = False
            for chip in chips:
                if "Vencidas" in chip.text:
                    btns = chip.find_elements(
                        By.CSS_SELECTOR, "button.chips-icone-fechar"
                    )
                    for btn in btns:
                        try:
                            if safe_click(driver, btn, timeout=5, log=False):
                                logger.info(
                                    "[DOMICILIO_ELETRONICO] Chip Vencidas removido."
                                )
                                removido = True
                                break
                        except Exception as e:
                            logger.warning(
                                "[DOMICILIO_ELETRONICO] Erro ao clicar no botao"
                                " de fechar chip Vencidas: %s",
                                e,
                            )
                    if removido:
                        break
            if not removido:
                logger.info(
                    "[DOMICILIO_ELETRONICO] Chip Vencidas nao encontrado ou ja removido."
                )
        except Exception as e:
            logger.warning(
                "[DOMICILIO_ELETRONICO] Erro ao verificar/remover chip Vencidas: %s", e
            )

        # 3. Aplicar filtro dom.e
        btn_fa_pen = esperar_elemento(driver, "i.fa-pen", timeout=10)
        if btn_fa_pen:
            safe_click(driver, btn_fa_pen)

        campo_descricao = esperar_elemento(
            driver, 'input[aria-label*="Descricao"]', timeout=10
        )
        if campo_descricao:
            campo_descricao.clear()
            campo_descricao.send_keys("dom.e")
            campo_descricao.send_keys(Keys.ENTER)
            logger.info(
                "[DOMICILIO_ELETRONICO] Filtro dom.e aplicado no painel de atividades"
            )
            # Aguardar aplicacao do filtro
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "tr.cdk-drag")
                    )
                )
            except Exception:
                pass

        # 4. Aplicar filtro 100
        aplicar_filtro_100(driver)
        logger.info("[DOMICILIO_ELETRONICO] Filtro 100 aplicado")
        # Aguardar estabilizacao apos filtro 100
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "tr.cdk-drag")
                )
            )
        except Exception:
            pass

    except Exception as e:
        logger.error(
            "[DOMICILIO_ELETRONICO] Erro na navegacao para atividades: %s", e
        )
        return False

    return True


# =============================================================================
# Processamento de processo individual
# =============================================================================


def processar_processo_dom(
    driver: WebDriver,
    proc_id: str,
    linha: WebElement,
    aba_lista_original: str,
) -> bool:
    """Processa um unico processo DOM com recuperacao de acesso negado.

    Args:
        driver: WebDriver Selenium.
        proc_id: ID do processo.
        linha: Elemento da linha na tabela.
        aba_lista_original: Handle da aba da lista.

    Returns:
        True se processado com sucesso.

    Raises:
        Exception: Com prefixo RESTART_DRIVER se o driver precisa ser reiniciado.
    """
    try:
        logger.info("[DOMICILIO_ELETRONICO] Processando processo: %s", proc_id)

        # Reindexar linha se necessario (cuidar de erros de conexao)
        try:
            linha.is_displayed()
            linha_atual = linha
        except Exception:
            try:
                linha_atual = reindexar_linha(driver, proc_id)
            except Exception as re_e:
                msg = str(re_e)
                logger.error("[DOMICILIO_ELETRONICO] Erro geral na reindexacao: %s", msg)
                if (
                    "Tried to run command without establishing a connection"
                    in msg
                    or "disconnected" in msg.lower()
                ):
                    raise Exception(
                        f"RESTART_DRIVER: reindex_failed ({msg})"
                    )
                return False

            if not linha_atual:
                logger.error(
                    "[DOMICILIO_ELETRONICO] Nao foi possivel reindexar linha para %s",
                    proc_id,
                )
                return False

        # Abrir detalhes do processo
        try:
            if not abrir_detalhes_processo(driver, linha_atual):
                logger.error(
                    "[DOMICILIO_ELETRONICO] Falha ao abrir detalhes para %s", proc_id
                )
                return False
        except Exception as e_open:
            msg = str(e_open)
            logger.error(
                "[DOMICILIO_ELETRONICO] Erro ao abrir detalhes para %s: %s", proc_id, msg
            )
            if (
                "Tried to run command without establishing a connection"
                in msg
                or "disconnected" in msg.lower()
            ):
                raise Exception(
                    f"RESTART_DRIVER: abrir_detalhes_failed ({msg})"
                )
            return False

        # Aguardar nova aba e trocar para ela
        try:
            nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
        except Exception as e_tab:
            msg = str(e_tab)
            logger.error(
                "[DOMICILIO_ELETRONICO] Erro ao trocar para nova aba em %s: %s",
                proc_id,
                msg,
            )
            if (
                "Tried to run command without establishing a connection"
                in msg
                or "disconnected" in msg.lower()
            ):
                raise Exception(
                    f"RESTART_DRIVER: trocar_para_nova_aba_failed ({msg})"
                )
            return False

        if not nova_aba:
            logger.error(
                "[DOMICILIO_ELETRONICO] Nova aba nao carregou para %s", proc_id
            )
            return False

        # 0. Remover chips DOM Eletronico antes de qualquer verificacao
        _chips_dom_pre = [
            "Domicilio Eletronico - Ciencia Automatica",
            "Domicilio Eletronico - Prazo de Ciencia Expirado",
            "Domicilio Eletronico - Prazo de Resposta Excedido",
            "Domicilio Eletronico - Erro na Transmissao",
        ]
        try:
            def_chip(
                driver,
                numero_processo=proc_id,
                observacao="Remover chips DOM pre-fluxo",
                chips_para_remover=_chips_dom_pre,
                debug=True,
            )
        except Exception as _e_chip_pre:
            logger.warning("[DOMICILIO_ELETRONICO] Erro ao remover chips pre-fluxo: %s", _e_chip_pre)

        # Verificar ata de audiencia na timeline antes de processar
        import re as _re_dom
        _m_pid = _re_dom.search(r'/processo/(\d+)/', driver.current_url)
        if _m_pid and _tem_ata_audiencia(_m_pid.group(1), driver):
            logger.info(
                "[DOMICILIO_ELETRONICO] Ata de audiencia na timeline de %s — pulando (filtro de lista)",
                proc_id,
            )
            return True

        # Extrair tipo do processo da aba de detalhes (mais confiavel)
        tipo_processo = "ATOrd"  # padrao
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "pje-cabecalho-processo")
                )
            )

            tipo_js = driver.execute_script(
                """
                var cabecalho = document.querySelector('pje-cabecalho-processo');
                if (cabecalho) {
                    var spansTipo = cabecalho.querySelectorAll(
                        'pje-descricao-processo span.align-end.ng-star-inserted'
                    );
                    for (var i = 0; i < spansTipo.length; i++) {
                        var texto = (spansTipo[i].innerText
                            || spansTipo[i].textContent || '').trim();
                        if (texto && (texto.includes('ATOrd')
                            || texto.includes('ATSum')
                            || texto.includes('ACum'))) {
                            return texto;
                        }
                    }
                }
                return '';
            """
            )

            if tipo_js:
                tipo_processo = tipo_js.strip()
                logger.info(
                    "[DOMICILIO_ELETRONICO] Tipo identificado na aba de detalhes: %s",
                    tipo_processo,
                )
            else:
                logger.warning(
                    "[DOMICILIO_ELETRONICO] Tipo nao identificado na aba de detalhes"
                    " para %s, usando padrao ATOrd",
                    proc_id,
                )
                tipo_processo = "ATOrd"
        except Exception as e:
            logger.warning(
                "[DOMICILIO_ELETRONICO] Erro ao extrair tipo da aba de detalhes"
                " para %s: %s, usando padrao ATOrd",
                proc_id,
                e,
            )
            tipo_processo = "ATOrd"

        # Executar callback do bucket 2
        try:
            driver._numero_processo_lista = proc_id
            result = callback_bucket2(driver, tipo_processo)
            if result:
                logger.info("[DOMICILIO_ELETRONICO] Callback OK para %s", proc_id)
                return True
            else:
                logger.error(
                    "[DOMICILIO_ELETRONICO] Callback falhou para %s", proc_id
                )
                return False
        except Exception as e:
            # Se e RESTART_DRIVER, propagar para recuperacao
            if "RESTART_DRIVER" in str(e):
                logger.warning(
                    "[DOMICILIO_ELETRONICO] Acesso negado detectado no callback"
                    " para %s - propagando para recuperacao",
                    proc_id,
                )
                raise
            # Outras excecoes sao erros do callback
            logger.error(
                "[DOMICILIO_ELETRONICO] Erro no callback para %s: %s", proc_id, e
            )
            return False
        finally:
            if hasattr(driver, "_numero_processo_lista"):
                delattr(driver, "_numero_processo_lista")

    except Exception as e:
        msg = str(e)
        logger.error(
            "[DOMICILIO_ELETRONICO] Erro geral no processamento de %s: %s", proc_id, msg
        )
        if (
            "Tried to run command without establishing a connection" in msg
            or "RESTART_DRIVER" in msg
            or "disconnected" in msg.lower()
        ):
            raise Exception(f"RESTART_DRIVER: {msg}")
        return False
    finally:
        # Gerenciar abas apos processamento
        _gerenciar_abas_apos_processo_dom(driver, aba_lista_original)


def _gerenciar_abas_apos_processo_dom(
    driver: WebDriver, aba_lista_original: str
) -> None:
    """Gerencia abas apos processamento de um processo no DOM.

    Fecha todas as abas exceto a da lista original.

    Args:
        driver: WebDriver Selenium.
        aba_lista_original: Handle da aba da lista.

    Raises:
        Exception: Com prefixo RESTART_DRIVER se o driver estiver desconectado.
    """
    try:
        # Verificar handles validos
        try:
            handles = list(driver.window_handles)
        except Exception as e:
            logger.error(
                "[DOMICILIO_ELETRONICO] Driver desconectado ao ler window_handles: %s", e
            )
            raise Exception(f"RESTART_DRIVER: driver_disconnect ({e})")

        if aba_lista_original not in handles:
            logger.error("[DOMICILIO_ELETRONICO] Aba da lista nao esta mais disponivel")
            raise Exception("RESTART_DRIVER: aba_lista_original_missing")

        # Fechar outras abas com cuidado
        for handle in handles:
            if handle == aba_lista_original:
                continue
            try:
                driver.switch_to.window(handle)
                try:
                    WebDriverWait(driver, 3).until(
                        lambda d: d.execute_script(
                            "return document.readyState"
                        )
                        == "complete"
                    )
                except Exception:
                    pass
                driver.close()
                logger.info("[DOMICILIO_ELETRONICO] Aba fechada: %s...", handle[:20])
            except Exception as e:
                msg = str(e)
                logger.warning(
                    "[DOMICILIO_ELETRONICO] Erro ao fechar aba %s...: %s",
                    handle[:20],
                    msg,
                )
                if (
                    "Tried to run command without establishing a connection"
                    in msg
                    or "disconnected" in msg.lower()
                ):
                    raise Exception(f"RESTART_DRIVER: {msg}")
                continue

        # Retornar a aba da lista e aguardar estabilizacao do DOM
        try:
            driver.switch_to.window(aba_lista_original)
        except Exception as e:
            logger.error(
                "[DOMICILIO_ELETRONICO] Falha ao retornar para aba da lista: %s", e
            )
            raise Exception(f"RESTART_DRIVER: switch_to_failed ({e})")

        # Pequena espera para evitar rate-limit
        time.sleep(2.0)
        try:
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "tr.cdk-drag")
                )
            )
        except Exception:
            logger.debug(
                "[DOMICILIO_ELETRONICO] Timeout: tabela de processos"
                " pode nao estar visivel imediatamente (seguindo)"
            )

        logger.info("[DOMICILIO_ELETRONICO] Retornado a aba da lista")

    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            raise
        logger.error("[DOMICILIO_ELETRONICO] Falha ao gerenciar abas: %s", e)
        raise


# =============================================================================
# Execucao da lista com callback do bucket 2
# =============================================================================


def execute_list_with_bucket2_callback(driver: WebDriver) -> bool:
    """Indexa processos e executa callback do bucket 2 em cada um.

    Fluxo:
      1. Verifica se esta no painel de atividades; se nao, navega
      2. Indexa todos os processos da lista
      3. Para cada processo: abre detalhes, executa callback bucket 2,
         fecha abas extras
      4. Aplica delay anti-rate entre itens

    Args:
        driver: WebDriver Selenium.

    Returns:
        True se todos os processos foram processados sem erros.
    """
    try:
        # Verificar se estamos no painel de atividades
        try:
            cur = (driver.current_url or "").lower()
            if "atividades" in cur:
                logger.info(
                    "[DOMICILIO_ELETRONICO] Executando fluxo no painel de atividades (dom.e)"
                )
            elif "lista-processos" in cur:
                logger.info(
                    "[DOMICILIO_ELETRONICO] Pagina e a lista de processos"
                    " -- prosseguindo com indexacao (compativel)"
                )
            else:
                logger.info(
                    "[DOMICILIO_ELETRONICO] Pagina atual nao e painel de atividades"
                    " nem lista; navegando para painel de atividades"
                    " e aplicando filtro dom.e"
                )
                if not navigate_to_activities_and_filter(driver):
                    logger.error(
                        "[DOMICILIO_ELETRONICO] Falha ao navegar para painel de atividades"
                    )
                    return False
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "tr.cdk-drag")
                        )
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.debug(
                "[DOMICILIO_ELETRONICO] Erro no pre-check de pagina: %s", e
            )

        # 1. Indexar processos
        processos = indexar_processos(driver)
        if not processos:
            logger.warning(
                "[DOMICILIO_ELETRONICO] Nenhum processo encontrado na lista"
            )
            return False

        logger.info(
            "[DOMICILIO_ELETRONICO] %s processos encontrados para processamento",
            len(processos),
        )

        # 2. Processar cada processo individualmente
        aba_lista_original = driver.current_window_handle
        erros = 0
        total = len(processos)

        for idx, (proc_id, linha) in enumerate(processos, 1):
            logger.info(
                "[DOMICILIO_ELETRONICO] Processando %d/%d: %s", idx, total, proc_id
            )

            try:
                ok = processar_processo_dom(
                    driver, proc_id, linha, aba_lista_original
                )
                if not ok:
                    erros += 1
                    logger.error(
                        "[DOMICILIO_ELETRONICO] Falha no processamento de %s", proc_id
                    )
            except Exception as e:
                if "RESTART_DRIVER" in str(e):
                    logger.warning(
                        "[DOMICILIO_ELETRONICO] Erro critico em %s"
                        " - propagando RESTART_DRIVER",
                        proc_id,
                    )
                    raise
                erros += 1
                logger.error(
                    "[DOMICILIO_ELETRONICO] Erro processando %s: %s", proc_id, e
                )

            # Delay anti-rate entre itens
            try:
                time.sleep(1.25)
            except Exception:
                pass

        sucesso = total - erros
        logger.info(
            "[DOMICILIO_ELETRONICO] Processamento concluido: %s sucesso, %s erros"
            " (total %s)",
            sucesso,
            erros,
            total,
        )
        return erros == 0

    except Exception as e:
        if "RESTART_DRIVER" in str(e):
            raise
        logger.error("[DOMICILIO_ELETRONICO] Erro na execucao da lista: %s", e)
        return False


# =============================================================================
# Entrypoint principal
# =============================================================================

_PROGRESSO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "progresso.json")


def _carregar_progresso() -> Dict[str, Any]:
    try:
        with open(_PROGRESSO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_progresso(dados: Dict[str, Any]) -> None:
    try:
        with open(_PROGRESSO_PATH, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("[DOMICILIO_ELETRONICO][CACHE] Falha ao salvar progresso: %s", e)


def _cache_dom_salvar_lista(processos: List[Dict[str, Any]]) -> None:
    """Persiste a lista completa de processos DOM no progresso.json."""
    prog = _carregar_progresso()
    prog["dom"] = {
        "data": datetime.now().strftime("%Y-%m-%d"),
        "processos_pendentes": [
            {"id": str(p.get("id", "")), "numero": p.get("numeroProcesso") or p.get("numero") or ""}
            for p in processos
        ],
        "processos_ok": [],
        "processos_erro": [],
        "last_update": datetime.now().isoformat(),
    }
    _salvar_progresso(prog)
    logger.info("[DOMICILIO_ELETRONICO][CACHE] Lista de %d processos salva em progresso.json", len(processos))


def _cache_dom_carregar_pendentes() -> Optional[List[Dict[str, Any]]]:
    """Retorna lista pendente do dia se existir, None caso contrário."""
    prog = _carregar_progresso()
    dom = prog.get("dom", {})
    if not dom:
        return None
    data_cache = dom.get("data", "")
    hoje = datetime.now().strftime("%Y-%m-%d")
    if data_cache != hoje:
        return None
    pendentes = dom.get("processos_pendentes", [])
    if not pendentes:
        return None
    ok = set(dom.get("processos_ok", []))
    erro = set(dom.get("processos_erro", []))
    ja_processados = ok | erro
    restantes = [p for p in pendentes if p["numero"] not in ja_processados and p["id"] not in ja_processados]
    total_orig = len(pendentes)
    logger.info("[DOMICILIO_ELETRONICO][CACHE] Cache do dia encontrado: %d/%d processos pendentes", len(restantes), total_orig)
    return restantes if restantes else None


def _cache_dom_marcar(numero: str, sucesso: bool) -> None:
    """Marca processo como ok ou erro no cache."""
    prog = _carregar_progresso()
    dom = prog.get("dom", {})
    if not dom:
        return
    chave = "processos_ok" if sucesso else "processos_erro"
    lista = dom.setdefault(chave, [])
    if numero not in lista:
        lista.append(numero)
    dom["last_update"] = datetime.now().isoformat()
    prog["dom"] = dom
    _salvar_progresso(prog)



def run_dom(driver: WebDriver) -> Dict[str, Any]:
    """Entrypoint principal para processamento do fluxo Dom Eletronico.

    Fluxo completo:
      1. Navega para URL_LISTA_DOM
      2. Aplica filtro de fase processual (conhecimento)
      3. Navega para painel de atividades e aplica filtro dom.e
      4. Indexa processos e processa cada um com callback do bucket 2

    Args:
        driver: WebDriver Selenium (ja autenticado no PJe).

    Returns:
        Dict com chave ``"sucesso"`` (bool) e opcionalmente ``"erro"`` (str).

    Example:
        >>> resultado = run_dom(driver)
        >>> resultado["sucesso"]
        True
    """
    logger.info("[DOMICILIO_ELETRONICO] === INICIANDO DOM ENGINE ===")

    try:
        # 1. Navegar para lista de processos DOM
        logger.info("[DOMICILIO_ELETRONICO] Navegando para lista de processos...")
        driver.get(LIST_URL)
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "tbody tr.tr-class")
                )
            )
        except Exception:
            logger.warning(
                "[DOMICILIO_ELETRONICO] Timeout ao aguardar tabela na lista de processos"
            )
        logger.info("[DOMICILIO_ELETRONICO] Navegacao concluida")

        # 2. Aplicar filtro de fase: conhecimento
        logger.info("[DOMICILIO_ELETRONICO] Aplicando filtro de fase: conhecimento")
        try:
            filtrofases(driver, fases_alvo=["conhecimento"])
        except Exception as e:
            logger.error(
                "[DOMICILIO_ELETRONICO] Erro ao aplicar filtro de fase: %s", e
            )
            return {"sucesso": False, "erro": str(e)}

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "tbody tr.tr-class")
                )
            )
        except Exception:
            pass

        # 3. Navegar para painel de atividades e aplicar filtro dom.e
        logger.info(
            "[DOMICILIO_ELETRONICO] Navegando para painel de atividades"
            " e aplicando filtro dom.e..."
        )
        if not navigate_to_activities_and_filter(driver):
            logger.error(
                "[DOMICILIO_ELETRONICO] Falha ao navegar para painel de atividades"
            )
            return {
                "sucesso": False,
                "erro": "Falha ao navegar para painel de atividades",
            }

        # 4. Executar lista com callback do bucket 2
        logger.info("[DOMICILIO_ELETRONICO] Executando lista com callback bucket 2...")
        sucesso = execute_list_with_bucket2_callback(driver)

        if sucesso:
            logger.info("[DOMICILIO_ELETRONICO] === EXECUCAO CONCLUIDA COM SUCESSO ===")
            return {"sucesso": True}
        else:
            logger.warning(
                "[DOMICILIO_ELETRONICO] Execucao concluida com falhas em alguns processos"
            )
            return {
                "sucesso": False,
                "erro": "Falha no processamento de um ou mais processos",
            }

    except Exception as e:
        msg = str(e)
        logger.error("[DOMICILIO_ELETRONICO] Erro geral: %s", msg)
        return {"sucesso": False, "erro": msg}


def run_dom_api(driver: WebDriver) -> Dict[str, Any]:
    """Entrypoint DOM via API — usa buscar_processos_conhecimento_dom() como filtro.

    Vantagem sobre run_dom: nao depende de scroll/DOM para indexar processos.
    A lista ja chega filtrada por chips 274/275/302 + audiencia.

    Fluxo:
      1. Extrai sessao do driver para PjeApiClient
      2. buscar_processos_conhecimento_dom() -> lista com id + numeroProcesso
      3. Para cada processo: navega /processo/{id}/detalhe, extrai tipo, callback_bucket2

    Args:
        driver: WebDriver Selenium (ja autenticado no PJe).

    Returns:
        Dict com sucesso, processados, total.
    """
    from bianca.api_client import PjeApiClient, session_from_driver
    from bianca.config import URL_PJE_BASE

    logger.info("[DOMICILIO_ELETRONICO] === INICIANDO DOM ENGINE (API) ===")

    try:
        sess, base_url = session_from_driver(driver)
    except Exception as e:
        return {"sucesso": False, "erro": f"session_from_driver: {e}"}

    client = PjeApiClient(sess, base_url)

    # Tentar reutilizar lista do dia (evita re-fetch lento da API)
    pendentes = _cache_dom_carregar_pendentes()
    if pendentes is not None:
        logger.info("[DOMICILIO_ELETRONICO][API] Reutilizando cache do dia (%d processos pendentes)", len(pendentes))
        processos = [{"id": p["id"], "numeroProcesso": p["numero"]} for p in pendentes]
    else:
        logger.info(
            "[DOMICILIO_ELETRONICO][API] Buscando processos (conhecimento + chips DOM + audiencia)..."
        )
        processos = client.buscar_processos_conhecimento_dom()
        if processos:
            _cache_dom_salvar_lista(processos)

    if not processos:
        logger.info("[DOMICILIO_ELETRONICO][API] Nenhum processo encontrado pela API")
        return {"sucesso": True, "processados": 0, "total": 0}

    # Filtrar processos com ata de audiencia na timeline (nao entram na lista)
    logger.info("[DOMICILIO_ELETRONICO][API] Filtrando processos com ata de audiencia...")
    sem_ata = []
    for _p in processos:
        _pid = str(_p.get("id", ""))
        _num = _p.get("numeroProcesso") or _p.get("numero") or _pid
        tem_ata = _pid and _tem_ata_audiencia(_pid, driver)
        _p["temAta"] = tem_ata  # Guardar para uso posterior
        if tem_ata:
            logger.info("[DOMICILIO_ELETRONICO][API] Excluido da lista (ata de audiencia): %s", _num)
        else:
            sem_ata.append(_p)
    logger.info(
        "[DOMICILIO_ELETRONICO][API] %d processos apos filtro de ata (%d removidos)",
        len(sem_ata), len(processos) - len(sem_ata),
    )
    processos = sem_ata

    # Enriquecer cada processo com campo temAudiencia (necessário para determinar bucket)
    for proc in processos:
        proc_id = str(proc.get("id", ""))
        proc["temAudiencia"] = True  # Por padrão True (API retorna processos com chips 274/275/302)

    # Separar processos por bucket e exibir pré-execução
    bucket1_procs = []
    bucket2_procs = []
    for proc in processos:
        bucket = _determinar_bucket(proc.get("temAudiencia", True), proc.get("temAta", False))
        if bucket == "bucket1":
            bucket1_procs.append(proc)
        else:
            bucket2_procs.append(proc)

    logger.info("[DOMICILIO_ELETRONICO] === PRÉ-PROCESSAMENTO ===")
    logger.info("[DOMICILIO_ELETRONICO] Bucket1 (sem aud. OU aud+ata):   %d processos", len(bucket1_procs))
    for proc in bucket1_procs:
        num = proc.get("numeroProcesso") or proc.get("numero") or proc.get("id")
        logger.info("[DOMICILIO_ELETRONICO]   - %s", num)
    logger.info("[DOMICILIO_ELETRONICO] Bucket2 (aud sem ata):         %d processos", len(bucket2_procs))
    for proc in bucket2_procs:
        num = proc.get("numeroProcesso") or proc.get("numero") or proc.get("id")
        logger.info("[DOMICILIO_ELETRONICO]   - %s", num)
    logger.info("[DOMICILIO_ELETRONICO] Total: %d processos", len(processos))

    if not processos:
        logger.info("[DOMICILIO_ELETRONICO][API] Nenhum processo restante apos filtro de ata")
        return {"sucesso": True, "processados": 0, "total": 0}

    logger.info("[DOMICILIO_ELETRONICO][API] %d processos a processar", len(processos))

    handle_principal = driver.current_window_handle
    erros = 0
    total = len(processos)
    
    # Contadores por bucket
    bucket1_processados = 0
    bucket2_processados = 0
    bucket1_erros = 0
    bucket2_erros = 0

    for idx, proc in enumerate(processos, 1):
        proc_id = str(proc.get("id", ""))
        numero = proc.get("numeroProcesso") or proc.get("numero") or proc_id

        if not proc_id:
            logger.warning("[DOMICILIO_ELETRONICO][API] Processo sem id, pulando")
            erros += 1
            continue

        logger.info("[DOMICILIO_ELETRONICO][API] %d/%d: %s (id=%s)", idx, total, numero, proc_id)

        try:
            # Fechar abas extras
            for h in list(driver.window_handles):
                if h != handle_principal:
                    try:
                        driver.switch_to.window(h)
                        driver.close()
                    except Exception:
                        pass
            driver.switch_to.window(handle_principal)

            # Navegar direto para detalhe via id interno
            url = f"{URL_PJE_BASE}/processo/{proc_id}/detalhe"
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "pje-cabecalho-processo,pje-timeline")
                )
            )

            _verificar_acesso_negado(driver, f"dom_api_{numero}")

            # Extrair tipo do processo a partir do cabecalho renderizado
            tipo_processo = "ATOrd"
            try:
                tipo_js = driver.execute_script(
                    """
                    var cab = document.querySelector('pje-cabecalho-processo');
                    if (cab) {
                        var spans = cab.querySelectorAll(
                            'pje-descricao-processo span.align-end.ng-star-inserted'
                        );
                        for (var i = 0; i < spans.length; i++) {
                            var t = (spans[i].innerText || spans[i].textContent || '').trim();
                            if (t && (t.includes('ATOrd') || t.includes('ATSum') || t.includes('ACum'))) {
                                return t;
                            }
                        }
                    }
                    return '';
                    """
                )
                if tipo_js:
                    tipo_processo = tipo_js.strip()
                    logger.info(
                        "[DOMICILIO_ELETRONICO][API] Tipo identificado: %s para %s",
                        tipo_processo, numero,
                    )
            except Exception as e_tipo:
                logger.warning(
                    "[DOMICILIO_ELETRONICO][API] Erro extraindo tipo para %s: %s, usando ATOrd",
                    numero, e_tipo,
                )

            # Executar callback apropriado baseado em bucket
            tem_audiencia = proc.get("temAudiencia", True)
            tem_ata = proc.get("temAta", False)
            bucket = _determinar_bucket(tem_audiencia, tem_ata)
            driver._numero_processo_lista = numero
            
            if bucket == "bucket1":
                logger.info("[DOMICILIO_ELETRONICO][API] Roteando para bucket1: %s", numero)
                ok = callback_bucket1(driver, tipo_processo)
                if ok:
                    bucket1_processados += 1
                else:
                    bucket1_erros += 1
            else:
                logger.info("[DOMICILIO_ELETRONICO][API] Roteando para bucket2: %s", numero)
                ok = callback_bucket2(driver, tipo_processo)
                if ok:
                    bucket2_processados += 1
                else:
                    bucket2_erros += 1

            if ok:
                logger.info("[DOMICILIO_ELETRONICO][API] OK: %s (%s)", numero, tipo_processo)
                _cache_dom_marcar(numero, sucesso=True)
            else:
                erros += 1
                logger.error("[DOMICILIO_ELETRONICO][API] Falha callback: %s", numero)
                _cache_dom_marcar(numero, sucesso=False)

        except Exception as e:
            if "RESTART_DRIVER" in str(e):
                raise
            erros += 1
            logger.error("[DOMICILIO_ELETRONICO][API] Erro em %s: %s", numero, e)

        try:
            time.sleep(1.25)
        except Exception:
            pass

    logger.info(
        "[DOMICILIO_ELETRONICO][API] Concluido: %d OK, %d erros (total %d)",
        total - erros, erros, total,
    )
    
    # Logging detalhado por bucket
    logger.info("[DOMICILIO_ELETRONICO] === RESUMO POR BUCKET ===")
    logger.info("[DOMICILIO_ELETRONICO] Bucket1: %d processados, %d erros", bucket1_processados, bucket1_erros)
    logger.info("[DOMICILIO_ELETRONICO] Bucket2: %d processados, %d erros", bucket2_processados, bucket2_erros)
    logger.info("[DOMICILIO_ELETRONICO] TOTAL: %d processados, %d erros (total %d)", 
                total - erros, erros, total)
    
    return {
        "sucesso": erros == 0,
        "processados": total - erros,
        "total": total,
        "bucket1_processados": bucket1_processados,
        "bucket1_erros": bucket1_erros,
        "bucket2_processados": bucket2_processados,
        "bucket2_erros": bucket2_erros,
    }
