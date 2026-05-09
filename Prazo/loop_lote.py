"""Prazo - Loop Lote (filtros + movimentacao + selecao)

Consolidado de: loop_ciclo1_filtros.py, loop_ciclo1_movimentacao.py, loop_ciclo2_selecao.py
"""
# ── Imports ──
import logging
import re
import time
from typing import List, Optional, Tuple, Union

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from Fix.core import (
    aguardar_renderizacao_nativa,
    aplicar_filtro_100,
    com_retry,
)
from Fix.extracao import filtrofases
from Fix.facade_publica import buscar

from .loop_orquestrador import (
    GIGS_API_MAX_WORKERS,
    SCRIPT_SELECAO_LIVRES,
    SCRIPT_SELECAO_LIVRES_API,
    SCRIPT_SELECAO_NAO_LIVRES,
    _extrair_numero_processo_da_linha,
    _obter_processos_com_gigs_api,
    log_seletor_vencedor,
    pausar_confirmacao,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# ── 1. loop_ciclo1_filtros.py ──
# ═══════════════════════════════════════════════

def _verificar_quantidade_processos_paginacao(driver: WebDriver) -> int:
    """
    Verifica quantidade de processos lendo o elemento de paginação.
    Retorna: quantidade de processos ou -1 se não conseguir detectar
    """
    try:
        # Buscar o elemento span.total-registros que contém "X - Y de Z"
        total_elem = driver.find_element(By.CSS_SELECTOR, 'span.total-registros')
        texto = total_elem.text.strip()

        # Extrair o total (último número após "de")
        # Formato: "1 - 1 de 1" ou "1 - 20 de 150" ou "0 de 0"
        match = re.search(r'de\s+(\d+)', texto)
        if match:
            total = int(match.group(1))
            return total

        # Fallback: tentar detectar "0 de 0" ou formato sem hífen
        if '0 de 0' in texto or '0 - 0 de 0' in texto:
            return 0

        return -1

    except Exception as e:
        logger.error(f'[CICLO1] Erro ao ler paginação: {e}')
        return -1


def _ciclo1_aplicar_filtro_fases(driver: WebDriver) -> Union[bool, str]:
    """Aplica filtro de liquidação/execução no painel 14.

    Returns:
        True: filtro aplicado e processos encontrados
        "no_more_processes": filtro aplicado mas sem processos
        False: erro ao aplicar filtro
    """
    try:
        if not pausar_confirmacao('CICLO1/FILTRO_FASES', 'Aplicar filtro liquidação/execução'):
            return False
        # Aguardar mat-select (componente de filtro Angular) estar presente e interativo
        # ANTES de chamar filtrofases. Sem isso, na 2ª+ iteração o dropdown abre mas os
        # mat-option ainda não foram populados (Angular não hidratou) → 0 matches → falha.
        try:
            el = buscar(driver, 'ciclo1_mat_select_combobox', ["mat-select[role='combobox']", "//mat-select"])
            if not el:
                try:
                    aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=10)
                except Exception:
                    aguardar_renderizacao_nativa(driver, "mat-select[role='combobox']", timeout=10)
            else:
                logger.info('[CICLO1][FILTRO] mat-select pronto')
        except Exception:
            pass
        t0 = time.perf_counter()
        result = filtrofases(driver, fases_alvo=['liquidação', 'execução'])
        t_filtro = time.perf_counter() - t0
        logger.info(f'[LATENCIA][DETALHE] CICLO1 filtrofases: {t_filtro:.3f}s')
        if not result:
            # filtrofases retorna False quando não encontra as opções para selecionar
            # Isso significa que não há processos nessas fases
            return "no_more_processes"

        # Aguardar spinner do filtro (div.carregando) — garante que Angular processou
        # o filtro ANTES de iniciar o polling de células (evita detectar linhas stale)
        try:
            WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.carregando'))
            )
            WebDriverWait(driver, 15).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.carregando'))
            )
            logger.info('[CICLO1][FILTRO] Spinner de filtro sumiu — lista pronta para polling')
        except Exception:
            pass  # sem spinner visível — pode ter sido rápido; polling cobre o restante

        # AGUARDAR LISTA CARREGAR - loop manual com break imediato ao encontrar células
        t1 = time.perf_counter()
        # Dar mais tempo para o Angular povoar a lista após aplicar o filtro.
        # 3s provou ser insuficiente em casos reais; usar 6s para maior robustez.
        timeout_espera = 6.0  # máximo 6 segundos de espera

        # Tentar aguardar renderização nativa/pagination atualizar (quando disponível)
        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=2)
            logger.info('[CICLO1][FILTRO] aguardar_renderizacao_nativa completada')
        except Exception:
            # fallback silencioso; o loop abaixo fará a checagem final
            logger.info('[CICLO1][FILTRO] aguardar_renderizacao_nativa indisponível ou falhou')

        seletor_celula_processo = 'td.td-class span.link.processo'
        xpath_vazio = "//span[contains(text(), 'Não há processos neste tema')]"

        # Loop manual: break assim que encontrar células ou mensagem vazio
        while time.perf_counter() - t1 < timeout_espera:
            try:
                celulas = driver.find_elements(By.CSS_SELECTOR, seletor_celula_processo)
                if len(celulas) > 0:
                    t_lista = time.perf_counter() - t1
                    logger.info(f'[CICLO1][FILTRO] Células encontradas em {t_lista:.3f}s')
                    logger.info(f'[LATENCIA][DETALHE] CICLO1 espera lista: {t_lista:.3f}s')
                    return True
            except Exception:
                pass

            # Verificar se há mensagem de vazio
            try:
                vazios = driver.find_elements(By.XPATH, xpath_vazio)
                if any(el.is_displayed() for el in vazios):
                    t_lista = time.perf_counter() - t1
                    logger.info(f'[CICLO1][FILTRO] Mensagem vazio encontrada em {t_lista:.3f}s')
                    logger.info(f'[LATENCIA][DETALHE] CICLO1 espera lista: {t_lista:.3f}s')
                    return "no_more_processes"
            except Exception:
                pass

            time.sleep(0.15)  # Sleep curto entre tentativas (polling interval)  # TODO: classificar

        # Timeout da espera atingido - fazer avaliação final rápida
        t_lista = time.perf_counter() - t1
        logger.info(f'[CICLO1][FILTRO] Timeout de espera atingido ({timeout_espera}s), avaliando lista...')
        logger.info(f'[LATENCIA][DETALHE] CICLO1 espera lista: {t_lista:.3f}s')

        # Verificação rápida final se há células
        try:
            celulas = driver.find_elements(By.CSS_SELECTOR, seletor_celula_processo)
            if len(celulas) > 0:
                logger.info(f'[CICLO1][FILTRO] {len(celulas)} célula(s) de processo detectada(s) na avaliação final')
                return True
        except Exception:
            pass

        # Última verificação: tentar ler paginação para confirmar quantidade
        try:
            total = _verificar_quantidade_processos_paginacao(driver)
            if total == 0:
                logger.info(f'[CICLO1][FILTRO] Paginação indica 0 processos (final)')
                return "no_more_processes"
            elif total > 0:
                logger.info(f'[CICLO1][FILTRO] Paginação final indica {total} processo(s)')
                return True
        except Exception:
            pass

        time.sleep(0.2)  # TODO: classificar
        return True
    except Exception as e:
        logger.error(f'[CICLO1] Erro ao aplicar filtro de fases: {e}')
        return False


# ═══════════════════════════════════════════════
# ── 2. loop_ciclo1_movimentacao.py ──
# ═══════════════════════════════════════════════

def _ciclo1_marcar_todas(driver: WebDriver) -> str:
    """Seleciona todos os processos via botão marcar-todas.

    Correção: clica no <button> pai (não no <i>) e valida checkboxes
    apenas nas linhas da tabela (tr.cdk-drag) com baseline pré-clique.
    Referência: legado atalhos_backup.js + idx.md (P4, P8).
    """
    logger.info("[CICLO1/MARCAR_TODAS] Iniciando busca e clique")

    # Baseline: contar checkboxes já marcados nas linhas da tabela (exclui filtros/menus)
    baseline = driver.execute_script(
        "return document.querySelectorAll('tr.cdk-drag mat-checkbox input[type=\"checkbox\"]:checked').length;"
    ) or 0
    total_linhas = driver.execute_script(
        "return document.querySelectorAll('tr.cdk-drag').length;"
    ) or 0
    logger.info(f"[CICLO1/MARCAR_TODAS] Baseline: {baseline}/{total_linhas} checkbox(es) marcados nas linhas")

    def _tentar_marcar():
        logger.info("[CICLO1/MARCAR_TODAS] Aguardando botão marcar-todas...")
        icone = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//i[contains(@class, 'marcar-todas')]"))
        )
        html = icone.get_attribute('outerHTML')
        logger.info(f"[CICLO1/MARCAR_TODAS] Botão encontrado: {html[:200]}")
        # (legado) clicar no button pai que tem o event handler Angular, não no <i>
        logger.info("[CICLO1/MARCAR_TODAS] Executando clique via JS no button pai...")
        try:
            result = driver.execute_script("""
                var icone = arguments[0];
                var btn = icone.closest('button, div[role="button"]') || icone;
                btn.scrollIntoView({block: 'center'});
                btn.click();
                return true;
            """, icone)
        except Exception:
            result = False
        if result:
            try:
                aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
            except Exception:
                aguardar_renderizacao_nativa(driver, timeout=1)
        return result

    try:
        if com_retry(_tentar_marcar, max_tentativas=5, backoff_base=1.5, log=True):
            # Validar: contar apenas checkboxes nas linhas da tabela, comparado ao baseline
            marcados = driver.execute_script(
                "return document.querySelectorAll('tr.cdk-drag mat-checkbox input[type=\"checkbox\"]:checked').length;"
            ) or 0
            novos = marcados - baseline
            logger.info(f"[CICLO1/MARCAR_TODAS] {novos} novo(s) checkbox(es) marcado(s) (total na tabela: {marcados}/{total_linhas})")
            if novos > 0:
                logger.info("[CICLO1/MARCAR_TODAS] Sucesso")
                return "success"
            else:
                logger.error("[CICLO1/MARCAR_TODAS] Nenhum checkbox novo marcado após clique")
                return "marcar_todas_not_found_but_continue"
        else:
            logger.info("[LOOP_PRAZO] Todas as tentativas de marcar-todas falharam")
            return "marcar_todas_not_found_but_continue"
    except Exception as e:
        logger.error(f"[CICLO1/MARCAR_TODAS] Erro geral: {e}")
        return "error"


def _ciclo1_abrir_suitcase(driver: WebDriver) -> bool:
    """Abre suitcase para movimentação em lote usando JavaScript click (VERSÃO CORRIGIDA)."""
    logger.info("[DEBUG] Aguardando suitcase aparecer...")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'i.fas.fa-suitcase.icone'))
        )
        logger.info("[DEBUG] Suitcase apareceu na página.")
    except Exception as e:
        logger.info(f"[DEBUG] Suitcase não apareceu: {e}")
        return False

    def _tentar_abrir_suitcase():
        if not pausar_confirmacao('CICLO1/SUITCASE_INTERNO', 'Executar clique no suitcase'):
            return False
        logger.info("[DEBUG] Tentando clicar no suitcase...")
        by = By.CSS_SELECTOR
        seletor = "button[aria-label='Movimentar em Lote'] i.fas.fa-suitcase.icone"

        elemento = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((by, seletor))
        )

        clicou = driver.execute_script(
            """
            let element = arguments[0];
            let target = element.closest('button, div[role="button"], mat-icon, span') || element;
            target.scrollIntoView({block: 'center'});
            target.click();
            return true;
            """,
            elemento,
        )

        if clicou:
            log_seletor_vencedor('CICLO1/SUITCASE', by, seletor)
            logger.info("[DEBUG] Suitcase clicado com sucesso.")
            return True

        logger.info("[CICLO1/SUITCASE] Clique falhou com seletor específico")
        return False

    try:
        if com_retry(_tentar_abrir_suitcase, max_tentativas=3, backoff_base=1.5, log=True):
            logger.info("[DEBUG] Suitcase aberto após retry.")
            try:
                aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
            except Exception:
                aguardar_renderizacao_nativa(driver, timeout=1)
            return True
        else:
            logger.info("[LOOP_PRAZO] Todas as tentativas de abrir suitcase falharam")
            return False
    except Exception as e:
        logger.info(f"[LOOP_PRAZO] Erro geral em abrir suitcase: {e}")
        return False


def _ciclo1_aguardar_movimentacao_lote(driver: WebDriver) -> bool:
    """Aguarda carregamento da página de movimentação em lote.

    Inclui espera pelo spinner 'Recuperando transições possíveis...' (div.carregando)
    desaparecer antes de retornar — garante que o dropdown de destino terá opções.
    """
    logger.info("[DEBUG] Aguardando URL /painel/movimentacao-lote...")
    try:
        WebDriverWait(driver, 15).until(
            EC.url_contains('/painel/movimentacao-lote')
        )
        logger.info(f"[DEBUG] URL atual: {driver.current_url}")
        if '/painel/movimentacao-lote' not in driver.current_url:
            logger.info(f"[LOOP_PRAZO][ERRO] URL inesperada após suitcase: {driver.current_url}")
            return False
        logger.info(f"[LOOP_PRAZO] Na tela de movimentação em lote: {driver.current_url}")

        # ── Aguardar spinner "Recuperando transições possíveis..." desaparecer ──
        # Sem isso, o dropdown de destino não terá opções e o clique nunca funciona
        logger.info("[CICLO1/LOTE] Aguardando transições carregarem (div.carregando sumir)...")
        try:
            WebDriverWait(driver, 25).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.carregando'))
            )
            logger.info("[CICLO1/LOTE] Transições carregadas (spinner sumiu)")
        except TimeoutException:
            logger.error("[CICLO1/LOTE] Timeout: spinner 'Recuperando transições possíveis...' não sumiu em 25s")
            logger.error("[CICLO1/LOTE] Algum processo do lote não possui a transição de destino — abortando")
            return False

        aguardar_renderizacao_nativa(driver, timeout=2)
        return True
    except Exception as e:
        logger.info(f"[LOOP_PRAZO][ERRO] URL de movimentacao-lote não carregou: {e}")
        return False


def _ciclo1_movimentar_destino_providencias(driver: WebDriver) -> bool:
    """Seleciona 'Cumprimento de providências' — mesma lógica do path padrão (Análise)."""
    opcao_destino = 'Cumprimento de providências'
    logger.info(f"[LOOP_PRAZO] Selecionando destino: '{opcao_destino}'")
    try:
        seta_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.mat-select-arrow-wrapper"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", seta_dropdown)
        driver.execute_script("arguments[0].click();", seta_dropdown)

        # Aguardar um mat-option aparecer (garante que as opções foram carregadas)
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane mat-option"))
        )

        opcao_elemento = None
        for xpath in [
            f"//mat-option//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']",
            "//mat-option//span[contains(@class,'mat-option-text') and contains(text(),'Cumprimento')]",
            "//mat-option//span[contains(@class,'mat-option-text') and contains(text(),'provid')]",
        ]:
            try:
                opcao_elemento = driver.find_element(By.XPATH, xpath)
                break
            except Exception:
                pass

        if not opcao_elemento:
            logger.error(f"[LOOP_PRAZO] Opção '{opcao_destino}' não encontrada no dropdown")
            return False

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento)
        driver.execute_script("arguments[0].click();", opcao_elemento)
        logger.info(f"[CICLO1/PROVIDENCIAS_OPCAO] Opção '{opcao_destino}' selecionada")

        seletor_btn = "button.mat-raised-button[color='primary']"
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_btn))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        driver.execute_script("arguments[0].click();", btn)
        logger.info("[LOOP_PRAZO] Botão 'Movimentar processos' clicado")
        return True
    except Exception as e:
        logger.error(f"[LOOP_PRAZO] Falha ao movimentar para '{opcao_destino}': {e}")
        return False


def _ciclo1_movimentar_destino(driver: WebDriver, opcao_destino: str) -> bool:
    """Seleciona destino usando abordagem direta (Gabarito)."""
    if opcao_destino == 'Cumprimento de providências':
        return _ciclo1_movimentar_destino_providencias(driver)
    logger.info(f"[CICLO1/DESTINO] Selecionando destino: '{opcao_destino}' (overlay-only)")
    try:
        if not pausar_confirmacao('CICLO1/DESTINO_ABRIR_DROPDOWN', f'Abrir dropdown para destino={opcao_destino}'):
            return False

        seletor_dropdown = "div.mat-select-arrow-wrapper"
        logger.info(f"[CICLO1/DESTINO_DROPDOWN] Abrindo dropdown com seletor: {seletor_dropdown}")
        try:
            seta_dropdown = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_dropdown))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", seta_dropdown)
            driver.execute_script("arguments[0].click();", seta_dropdown)
            log_seletor_vencedor('CICLO1/DESTINO_DROPDOWN', By.CSS_SELECTOR, seletor_dropdown)
        except Exception as e:
            logger.error(f"[LOOP_PRAZO] Erro ao abrir dropdown de destino com seletor {seletor_dropdown}: {e}")
            return False

        # Aguardar um mat-option aparecer (garante que as opções foram carregadas)
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cdk-overlay-pane mat-option"))
        )

        opcao_xpath = f"//mat-option//span[contains(@class,'mat-option-text') and normalize-space(text())='{opcao_destino}']"
        logger.info(f"[CICLO1/DESTINO_OPCAO] Selecionando opção com xpath: {opcao_xpath}")
        try:
            opcao_elemento = driver.find_element(By.XPATH, opcao_xpath)
            log_seletor_vencedor('CICLO1/DESTINO_OPCAO', By.XPATH, opcao_xpath)
        except Exception as e:
            logger.error(f"[LOOP_PRAZO] Opção '{opcao_destino}' não encontrada com xpath {opcao_xpath}: {e}")
            return False

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", opcao_elemento)
        driver.execute_script("arguments[0].click();", opcao_elemento)

        if not pausar_confirmacao('CICLO1/DESTINO_MOVIMENTAR', 'Clique no botão Movimentar'):
            return False

        seletor_movimentar = "button.mat-raised-button[color='primary']"
        logger.info(f"[CICLO1/DESTINO_BOTAO_MOVIMENTAR] Clicando botão movimentar com seletor: {seletor_movimentar}")
        try:
            btn_movimentar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_movimentar))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_movimentar)
            driver.execute_script("arguments[0].click();", btn_movimentar)
            log_seletor_vencedor('CICLO1/DESTINO_BOTAO_MOVIMENTAR', By.CSS_SELECTOR, seletor_movimentar)
        except Exception as e:
            logger.error(f"[LOOP_PRAZO] Erro ao clicar botão Movimentar com seletor {seletor_movimentar}: {e}")
            return False

        logger.info(f"[LOOP_PRAZO] Destino '{opcao_destino}' processado (legacy overlay flow).")
        return True
    except Exception as e:
        logger.info(f"[LOOP_PRAZO][ERRO] Falha ao movimentar para {opcao_destino}: {e}")
        return False


def _ciclo1_retornar_lista(driver: WebDriver) -> None:
    """Retorna graciosamente para a lista de processos."""
    try:
        if not pausar_confirmacao('CICLO1/RETORNO_INTERNO', 'Executar retorno com history.back'):
            return
        logger.info("[DEBUG] Retornando para a lista de processos...")
        driver.execute_script("window.history.back();")
        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=2)
        except Exception:
            aguardar_renderizacao_nativa(driver, timeout=2)  # fallback: DOM ready
        # Garantir fechamento de modais se sobrarem
        driver.execute_script("document.querySelectorAll('.cdk-overlay-backdrop').forEach(e => e.click())")
    except Exception as e:
        logger.info(f"[DEBUG] Erro ao retornar: {e}")


# ═══════════════════════════════════════════════
# ── 3. loop_ciclo2_selecao.py ──
# ═══════════════════════════════════════════════

def _ciclo2_aplicar_filtros(driver: WebDriver) -> bool:
    """Aplica filtros necessários para ciclo 2."""
    try:
        # Aguardar lista carregar
        try:
            # Usar buscar() para detectar o mat-select mais rapidamente
            el = buscar(driver, 'ciclo2_mat_select_combobox', ["mat-select[role='combobox']", "//mat-select"])
            if not el:
                # Prefer waiting for the stable total-registros indicator (shows "X - Y de Z")
                try:
                    aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=10)
                except Exception:
                    # Fallback: esperar mat-select quando total-registros não estiver presente
                    aguardar_renderizacao_nativa(driver, "mat-select[role='combobox']", timeout=10)
        except Exception:
            # fallback leve
            WebDriverWait(driver, 5)

        if not aplicar_filtro_100(driver):
            return False
        # aguardar aplicação do filtro — checar presença de linhas
        try:
            aguardar_renderizacao_nativa(driver, 'tr.cdk-drag', timeout=6)
        except Exception:
            pass

        if not filtrofases(
            driver,
            fases_alvo=['liquidação', 'execução'],
            tarefas_alvo=['análise'],
            seletor_tarefa='Tarefa do processo'
        ):
            return False
        # Aguardar spinner do filtro de fases (div.carregando) ANTES de selecionar processos.
        # Garante que a lista reflete o filtro antes de selecionar_todos / suitcase.
        try:
            WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.carregando'))
            )
            WebDriverWait(driver, 15).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div.carregando'))
            )
            logger.info('[CICLO2][FILTRO] Spinner de filtro sumiu — lista pronta')
        except Exception:
            try:
                aguardar_renderizacao_nativa(driver, 'tr.cdk-drag', timeout=6)
            except Exception:
                pass

        return True
    except Exception as e:
        logger.error(f'[CICLO2] Erro ao aplicar filtros: {e}')
        return False


def _ciclo2_processar_livres(driver: WebDriver, client: Optional['PjeApiClient'] = None) -> int:
    """Seleciona todos os processos livres (sem gigs DOM nem gigs via API).

    Args:
        driver: WebDriver Selenium
        client: PjeApiClient — quando fornecido, faz checagem extra via API para
                detectar gigs sem prazo que não aparecem no DOM.

    Returns:
        Total de processos livres selecionados
    """
    try:
        processos_com_gigs_api: List[str] = []
        if client is not None:
            # Extrai números de todos os processos visíveis na tabela
            linhas = driver.find_elements(By.CSS_SELECTOR, 'tr.cdk-drag')
            numeros = [n for linha in linhas
                       if (n := _extrair_numero_processo_da_linha(linha))]
            if numeros:
                logger.info(f'[CICLO2][LIVRES] Verificando {len(numeros)} processos via API GIGS...')
                processos_com_gigs_api = _obter_processos_com_gigs_api(
                    client, numeros, max_workers=GIGS_API_MAX_WORKERS
                )
                logger.info(f'[CICLO2][LIVRES] {len(processos_com_gigs_api)} processo(s) com gigs via API')

        _t0 = time.perf_counter()
        if processos_com_gigs_api:
            selecionados_livres = driver.execute_script(SCRIPT_SELECAO_LIVRES_API, processos_com_gigs_api)
            _label = 'SCRIPT_SELECAO_LIVRES_API'
        else:
            selecionados_livres = driver.execute_script(SCRIPT_SELECAO_LIVRES)
            _label = 'SCRIPT_SELECAO_LIVRES'
        _t1 = time.perf_counter()
        try:
            logger.info(f'[LATENCIA][DETALHE] {_label}: {(_t1-_t0)*1000:.1f}ms')
        except Exception:
            pass

        if selecionados_livres > 0:
            logger.info(f'[CICLO2][LIVRES] {selecionados_livres} livre(s) selecionado(s)')
        else:
            logger.info('[CICLO2][LIVRES] Nenhum livre encontrado')

        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=4)
        except Exception:
            pass
        return selecionados_livres

    except Exception as e:
        logger.error('[LOOP_PRAZO][ERRO] Erro em _ciclo2_processar_livres: %s: %s', type(e).__name__, e)
        return 0


def _ciclo2_selecionar_nao_livres(driver: WebDriver, max_processos: int = 20) -> Tuple[int, bool]:
    """Seleciona processos não-livres via JavaScript."""
    try:
        # Desselecionar todos primeiro — time.sleep(0.6) idêntico ao legado para Angular estabilizar
        # NOTA: WebDriverWait+len() era bugado (execute_script retorna int, len(int) → TypeError silenciado)
        driver.execute_script("document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').forEach(c=>c.click());")
        aguardar_renderizacao_nativa(driver, timeout=0.6)  # DOM-settle: Angular stabilize after uncheck

        _t0 = time.perf_counter()
        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, max_processos)
        _t1 = time.perf_counter()
        try:
            logger.info(f'[LATENCIA][DETALHE] SCRIPT_SELECAO_NAO_LIVRES: {(_t1-_t0)*1000:.1f}ms')
        except Exception:
            pass
        selecionados = resultado['selecionados']
        total_nao_livres = resultado['totalNaoLivres']

        logger.info(f'[CICLO2][NAO_LIVRES] {selecionados}/{total_nao_livres} selecionados')

        ha_mais = total_nao_livres > selecionados
        return selecionados, ha_mais
    except Exception as e:
        logger.error('[LOOP_PRAZO][ERRO] Falha ao selecionar nao-livres: %s: %s', type(e).__name__, e)
        return 0, False
