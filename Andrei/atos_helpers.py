"""
Andrei/atos_helpers.py - Funcoes auxiliares para atos judiciais PJe.

Contem funcoes internas de navegacao, modelos, prazos, movimento e
visibilidade de documentos sigilosos, usadas pelo modulo
Andrei.atos_judicial.

Uso:
    from Andrei.atos_helpers import (
        abrir_tarefa_processo, navegar_para_conclusao,
        escolher_tipo_conclusao, preencher_prazos_destinatarios,
        executar_visibilidade_sigilosos_se_necessario, ...
    )
"""

import logging
import time
import re
import unicodedata
from typing import Optional, Tuple, List

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException,
)

from Andrei.utils_selenium import (
    esperar_elemento,
    wait_for_clickable,
    esperar_url_conter,
    aguardar_renderizacao_nativa,
    safe_click,
    aguardar_e_clicar,
    preencher_multiplos_campos,
)

logger = logging.getLogger(__name__)

__all__ = [
    "abrir_tarefa_processo",
    "limpar_overlays",
    "navegar_para_conclusao",
    "preparar_campo_minutar",
    "escolher_tipo_conclusao",
    "aguardar_transicao_minutar",
    "verificar_estado_atual",
    "focar_campo_minutar_se_necessario",
    "preencher_prazos_destinatarios",
    "executar_visibilidade_sigilosos_se_necessario",
    "safe_click_no_scroll",
    "selecionar_movimento_auto",
    "selecionar_movimento_dois_estagios",
    "visibilidade_sigilosos",
]


# ==============================================================================
# CONSTANTES
# ==============================================================================

BTN_TAREFA_PROCESSO = 'button[mattooltip="Abre a tarefa do processo"]'

# ==============================================================================
# UTILITARIOS LOCAIS
# ==============================================================================


def safe_click_no_scroll(
    driver: WebDriver, element: WebElement, log: bool = True
) -> bool:
    """Clica via JavaScript sem scrollIntoView."""
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
        if log:
            logger.debug("safe_click_no_scroll falhou: %s", e)
        return False


def normalize_text(txt: str) -> str:
    """Remove acentos e converte para minusculas."""
    if not txt:
        return ""
    return (
        unicodedata.normalize("NFD", txt.lower())
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _normalize_text(s: str) -> str:
    """Remove acentos e normaliza espacos."""
    if not s:
        return ""
    s = normalize_text(s.strip())
    s = re.sub(r"\s+", " ", s)
    return s


def _aguardar_nova_aba(
    driver: WebDriver, handle_atual: str, timeout: int = 10
) -> Optional[str]:
    """Aguarda e retorna o handle de uma nova aba."""
    try:
        return WebDriverWait(driver, timeout).until(
            lambda d: next(
                (h for h in d.window_handles if h != handle_atual), None
            )
        )
    except TimeoutException:
        return None


def _wait_for_page_load(driver: WebDriver, timeout: int = 10) -> bool:
    """Aguarda document.readyState == complete."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        return True
    except Exception:
        return False


# ==============================================================================
# NAVEGACAO
# ==============================================================================


def verificar_estado_atual(driver: WebDriver) -> str:
    """Verifica o estado atual do processo baseado na URL.

    Returns:
        str: Estado atual ('assinar', 'minutar', 'conclusao', 'outro')
    """
    current_url = (driver.current_url or "").lower()

    if "/assinar" in current_url:
        return "assinar"
    elif "/minutar" in current_url:
        return "minutar"
    elif "/conclusao" in current_url:
        return "conclusao"
    else:
        return "outro"


def abrir_tarefa_processo(driver: WebDriver) -> Tuple[bool, bool]:
    """Abre a tarefa do processo atual. Usa API REST como caminho primario
    (padrao gigs-plugin L4491-4516), com fallback para clique UI.

    Returns:
        Tuple[bool, bool]: (sucesso_abertura, ja_em_estado_final)
    """
    try:
        logger.info("[NAVEGACAO] Abrindo tarefa do processo...")

        # Caminho 1: API REST (gigs-plugin L4491-4516)
        try:
            url_atual = driver.current_url or ''
            if '/tarefa' not in url_atual and '/processo/' in url_atual:
                m = re.search(r'/processo/(\d+)', url_atual)
                if m:
                    id_processo = m.group(1)
                    base = url_atual.split('/pjekz/')[0]
                    dados = driver.execute_async_script(
                        """
                        const url = arguments[0];
                        const done = arguments[arguments.length - 1];
                        fetch(url, {method: 'GET', credentials: 'include',
                                    headers: {'Content-Type':'application/json'}})
                            .then(resp => resp.json())
                            .then(json => done(json))
                            .catch(err => done({__erro: err && err.message
                                                   ? err.message : String(err)}));
                        """,
                        f"{base}/pje-comum-api/api/processos/id/{id_processo}/tarefas"
                        f"?maisRecente=true"
                    )
                    id_tarefa = None
                    if isinstance(dados, dict) and dados.get('__erro'):
                        logger.warning("[API_TAREFA] fetch error: %s", dados['__erro'])
                        dados = []
                    if isinstance(dados, list) and dados:
                        id_tarefa = dados[0].get('id') or dados[0].get('idTarefa')
                    elif isinstance(dados, dict):
                        id_tarefa = dados.get('id') or dados.get('idTarefa')
                    if id_tarefa:
                        url_tarefa = (
                            f"{base}/pjekz/processo/{id_processo}/tarefa/{id_tarefa}"
                        )
                        abas_antes_api = set(driver.window_handles)
                        driver.execute_script(
                            f"window.open('{url_tarefa}', '_blank');"
                        )
                        nova = _aguardar_nova_aba(
                            driver, next(iter(abas_antes_api)), timeout=5
                        )
                        if nova:
                            driver.switch_to.window(nova)
                        aguardar_renderizacao_nativa(
                            driver, 'pje-cabecalho-tarefa',
                            modo='aparecer', timeout=8
                        )
                        aguardar_renderizacao_nativa(
                            driver, 'pje-botoes-transicao button',
                            modo='aparecer', timeout=8
                        )
                        logger.info(
                            "[API_TAREFA] Tarefa aberta via API: processo=%s tarefa=%s",
                            id_processo, id_tarefa
                        )
                        current_url = (driver.current_url or "").lower()
                        ja_em_estado_final = (
                            "/assinar" in current_url
                            or "/minutar" in current_url
                            or "/conclusao" in current_url
                        )
                        if ja_em_estado_final:
                            logger.info(
                                "[NAVEGACAO] Apos API: ja em estado final (%s)",
                                current_url
                            )
                        return True, ja_em_estado_final
        except Exception as e:
            logger.info("[NAVEGACAO] API indisponivel, usando fallback UI: %s", e)

        # Caminho 2: fallback — clique UI no botao
        logger.info("[NAVEGACAO] Fallback: abrindo via clique UI...")
        abas_antes = set(driver.window_handles)

        btn_abrir_tarefa = esperar_elemento(
            driver, BTN_TAREFA_PROCESSO, timeout=10
        )
        if not btn_abrir_tarefa:
            logger.error(
                '[NAVEGACAO] Botao "Abrir tarefa do processo" nao encontrado!'
            )
            return False, False

        tarefa_do_botao = None
        try:
            span_tarefa = btn_abrir_tarefa.find_element(
                By.CSS_SELECTOR, ".texto-tarefa-processo"
            )
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
        except Exception:
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
            except Exception:
                pass

        if tarefa_do_botao and "assinar" in tarefa_do_botao.lower():
            logger.info(
                '[NAVEGACAO] Tarefa "%s" contem "assinar" - ato pronto',
                tarefa_do_botao,
            )
            return True, True

        if not safe_click(driver, btn_abrir_tarefa):
            logger.error(
                '[NAVEGACAO] Falha ao clicar em "Abrir tarefa do processo"'
            )
            return False, False

        nova_aba = None
        try:
            nova_aba = _aguardar_nova_aba(
                driver, next(iter(abas_antes)), timeout=10
            )
        except TimeoutException:
            logger.info(
                "[NAVEGACAO] Nenhuma nova aba detectada (continuando na mesma aba)"
            )

        if nova_aba:
            driver.switch_to.window(nova_aba)
            logger.info("[NAVEGACAO] Foco trocado para nova aba")
            try:
                _wait_for_page_load(driver, 8)
            except Exception:
                pass

        current_url = (driver.current_url or "").lower()
        ja_em_estado_final = (
            "/assinar" in current_url
            or "/minutar" in current_url
            or "/conclusao" in current_url
        )

        if ja_em_estado_final:
            logger.info(
                "[NAVEGACAO] Apos abertura: ja em estado final (%s)", current_url
            )

        return True, ja_em_estado_final

    except Exception as e:
        logger.error("[NAVEGACAO] Erro ao abrir tarefa: %s", e)
        return False, False


def limpar_overlays(driver: WebDriver) -> None:
    """Remove overlays e elementos flutuantes que podem interferir."""
    try:
        driver.implicitly_wait(0)
        overlays = driver.find_elements(
            By.CSS_SELECTOR,
            ".cdk-overlay-backdrop, .mat-dialog-container",
        )
        driver.implicitly_wait(10)
        if overlays:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            aguardar_renderizacao_nativa(
                driver,
                "div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop"
                ".cdk-overlay-backdrop-showing",
                modo="sumir",
                timeout=2,
            )
            logger.info("[NAVEGACAO] Overlays removidos")
    except Exception as e:
        driver.implicitly_wait(10)
        logger.debug("[NAVEGACAO] Erro ao limpar overlays: %s", e)


def navegar_para_conclusao(driver: WebDriver) -> bool:
    """Navega da tarefa atual para 'Conclusao ao Magistrado'.
    Padrao gigs-plugin L11576-11656: JS click nativo + observer, sem retry loops.

    Returns:
        bool: True se conseguiu navegar para conclusao.
    """
    try:
        logger.info("[NAVEGACAO] Navegando para Conclusao ao Magistrado (padrao gigs)...")

        # Aguardar botoes de transicao via observer (gigs: esperarElemento)
        botoes_ok = aguardar_renderizacao_nativa(
            driver, 'pje-botoes-transicao button', modo='aparecer', timeout=8
        )
        if not botoes_ok:
            logger.warning("[NAVEGACAO] Botoes de transicao nao carregaram — tentando refresh")
            try:
                driver.refresh()
                aguardar_renderizacao_nativa(
                    driver, 'pje-botoes-transicao button', modo='aparecer', timeout=6
                )
            except Exception:
                pass

        # Localizar e clicar 'Conclusao ao magistrado' via JS (gigs: clicarBotao por texto)
        clicou = driver.execute_script("""
            function normalizar(s) {
                return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
            }
            var botoes = document.querySelectorAll('pje-botoes-transicao button');
            for (var i = 0; i < botoes.length; i++) {
                var txt = normalizar(botoes[i].textContent || '');
                if (txt.indexOf('conclusao ao magistrado') !== -1 && !botoes[i].disabled) {
                    botoes[i].click();
                    return true;
                }
            }
            return false;
        """)

        if not clicou:
            logger.info("[NAVEGACAO] Conclusao nao disponivel — passando por Analise...")
            analise_ok = driver.execute_script("""
                function normalizar(s) {
                    return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                }
                var botoes = document.querySelectorAll('pje-botoes-transicao button');
                for (var i = 0; i < botoes.length; i++) {
                    var txt = normalizar(botoes[i].textContent || '');
                    if (txt.indexOf('analise') !== -1 && !botoes[i].disabled) {
                        botoes[i].click();
                        return true;
                    }
                }
                return false;
            """)
            if not analise_ok:
                logger.error("[NAVEGACAO] Botao Analise nao encontrado")
                return False

            aguardar_renderizacao_nativa(
                driver, 'pje-botoes-transicao button', modo='aparecer', timeout=8
            )

            clicou = driver.execute_script("""
                function normalizar(s) {
                    return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                }
                var botoes = document.querySelectorAll('pje-botoes-transicao button');
                for (var i = 0; i < botoes.length; i++) {
                    var txt = normalizar(botoes[i].textContent || '');
                    if (txt.indexOf('conclusao ao magistrado') !== -1 && !botoes[i].disabled) {
                        botoes[i].click();
                        return true;
                    }
                }
                return false;
            """)
            if not clicou:
                logger.error("[NAVEGACAO] Conclusao ao magistrado nao encontrada apos Analise")
                return False

        # Aguardar sinal de transicao (gigs L11655)
        transicao_ok = aguardar_renderizacao_nativa(
            driver,
            'pje-concluso-tarefa-botao button, pje-arvore-modelo-documento',
            modo='aparecer',
            timeout=10
        )
        if transicao_ok:
            logger.info("[NAVEGACAO] Transicao para conclusao detectada (observer)")
            return True

        # Fallback: verificar URL
        current_url = (driver.current_url or "").lower()
        if '/minutar' in current_url or '/conclusao' in current_url:
            logger.info("[NAVEGACAO] URL confirma transicao para conclusao/minutar")
            return True

        try:
            botoes = driver.find_elements(By.CSS_SELECTOR, 'pje-concluso-tarefa-botao button')
            if botoes:
                logger.info("[NAVEGACAO] Botoes de conclusao disponiveis (fallback)")
                return True
        except Exception:
            pass

        logger.error("[NAVEGACAO] URL nao mudou para conclusao: %s", driver.current_url[:120])
        return False

    except Exception as e:
        logger.error("[NAVEGACAO] Erro na navegacao para conclusao: %s", e)
        return False


def preparar_campo_minutar(driver: WebDriver) -> bool:
    """Prepara o campo de filtro de modelos na tela de minutar.

    Returns:
        bool: True se conseguiu preparar o campo.
    """
    try:
        logger.info("[NAVEGACAO] Preparando campo de filtro para minutar...")

        campo_filtro_modelo = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "input#inputFiltro")
            )
        )

        driver.execute_script(
            'arguments[0].removeAttribute("disabled");'
            ' arguments[0].removeAttribute("readonly");',
            campo_filtro_modelo,
        )
        driver.execute_script(
            "arguments[0].value = arguments[1];", campo_filtro_modelo, ""
        )
        driver.execute_script(
            "arguments[0].focus();", campo_filtro_modelo
        )

        driver.execute_script(
            "var el=arguments[0];"
            " el.dispatchEvent(new Event('input', {bubbles:true}));"
            " el.dispatchEvent(new Event('keyup', {bubbles:true}));",
            campo_filtro_modelo,
        )

        logger.info("[NAVEGACAO] Campo de filtro preparado com sucesso")
        aguardar_renderizacao_nativa(
            driver, "input#inputFiltro", modo="aparecer", timeout=2
        )
        return True

    except Exception as e:
        logger.error("[NAVEGACAO] Falha ao preparar campo de filtro: %s", e)
        return False


# ==============================================================================
# MODELOS
# ==============================================================================


def escolher_tipo_conclusao(
    driver: WebDriver, conclusao_tipo: str
) -> bool:
    """Escolhe o tipo de conclusao na tela de conclusao do processo.
    Padrao gigs-plugin L11626-11653: busca normalizada unica, JS click
    no firstElementChild, aguarda PJE-ARVORE-MODELO-DOCUMENTO.

    Returns:
        bool: True se conseguiu escolher o tipo.
    """
    try:
        logger.info("[CONCLUSO] Escolhendo tipo: %s (padrao gigs)", conclusao_tipo)

        aguardar_renderizacao_nativa(
            driver, 'pje-concluso-tarefa-botao', modo='aparecer', timeout=8
        )

        clicou = driver.execute_script("""
            var tipo = arguments[0].toLowerCase();
            function normalizar(s) {
                return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
            }
            var containers = document.querySelectorAll('pje-concluso-tarefa-botao');
            for (var i = 0; i < containers.length; i++) {
                var txt = normalizar(containers[i].textContent || '');
                if (txt.indexOf(normalizar(tipo)) !== -1) {
                    var btn = containers[i].querySelector('button');
                    if (btn && !btn.disabled) {
                        btn.click();
                        return true;
                    }
                }
            }
            return false;
        """, conclusao_tipo)

        if not clicou:
            logger.error("[CONCLUSO] Botao de conclusao '%s' nao encontrado", conclusao_tipo)
            return False

        logger.info("[CONCLUSO] Tipo '%s' clicado (JS nativo)", conclusao_tipo)
        aguardar_renderizacao_nativa(
            driver, 'pje-arvore-modelo-documento', modo='aparecer', timeout=10
        )
        return True

    except Exception as e:
        logger.error("[CONCLUSO] Erro ao escolher tipo: %s", e)
        import traceback
        logger.error(traceback.format_exc())
        return False


def aguardar_transicao_minutar(driver: WebDriver) -> bool:
    """Aguarda a transicao da tela de conclusao para minutar.
    Padrao gigs-plugin L11655: observer em PJE-ARVORE-MODELO-DOCUMENTO
    em vez de polling de URL.

    Returns:
        bool: True se conseguiu fazer a transicao.
    """
    try:
        logger.info("[CONCLUSO] Aguardando transicao para minutar (observer)...")

        # Caminho 1: observer no elemento DOM (gigs L11655)
        if aguardar_renderizacao_nativa(
            driver, 'pje-arvore-modelo-documento', modo='aparecer', timeout=10
        ):
            logger.info("[CONCLUSO] Transicao para minutar detectada (observer)")
            return True

        # Caminho 2: fallback — verificar URL
        current_url = (driver.current_url or "").lower()
        if "/minutar" in current_url:
            logger.info("[CONCLUSO] URL /minutar detectada (fallback)")
            return True

        # Caminho 3: esperar URL como ultima alternativa
        if esperar_url_conter(driver, "/minutar", timeout=8):
            logger.info("[CONCLUSO] Transicao para minutar concluida (URL)")
            return True

        logger.error(
            "[CONCLUSO] URL nao mudou para /minutar: %s", driver.current_url[:120]
        )
        return False

    except Exception as e:
        logger.error("[CONCLUSO] Erro na transicao para minutar: %s", e)
        return False


def focar_campo_minutar_se_necessario(driver: WebDriver) -> bool:
    """Foca no campo de filtro de modelos se estiver na tela de minutar.

    Returns:
        bool: True se conseguiu focar ou se nao era necessario.
    """
    try:
        if verificar_estado_atual(driver) == "minutar":
            logger.info("[CONCLUSO] Ja em minutar - focando no campo de filtro")
            campo_filtro_modelo = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "input#inputFiltro")
                )
            )
            driver.execute_script(
                "arguments[0].focus();", campo_filtro_modelo
            )
            logger.info("[CONCLUSO] Foco no campo #inputFiltro realizado")
        return True
    except Exception as e:
        logger.warning("[CONCLUSO] Erro ao focar campo minutar: %s", e)
        return False


# ==============================================================================
# PRAZOS E DESTINATARIOS
# ==============================================================================


def preencher_prazos_destinatarios(
    driver,
    prazo,
    apenas_primeiro=False,
    perito=False,
    perito_nomes=None,
):
    """Preenche prazos para destinatarios em uma tabela especifica.

    Ignora automaticamente destinatarios configurados como
    'Domicilio Eletronico'.
    """
    nomes_peritos_padrao = [
        "ROGERIO APARECIDO ROSA",
    ]
    if perito_nomes is None:
        perito_nomes = nomes_peritos_padrao

    try:
        logger.info("[PRAZOS] Preenchendo prazos: %s", prazo)

        try:
            WebDriverWait(driver, 20).until(
                lambda d: len(
                    d.find_elements(
                        By.CSS_SELECTOR,
                        "table.t-class tr.ng-star-inserted",
                    )
                )
                > 0
            )
            logger.info("[PRAZOS] Tabela de destinatarios carregada")
        except Exception:
            logger.warning(
                "[PRAZOS] Tabela de destinatarios nao carregou no tempo esperado"
            )
            return False

        linhas = driver.find_elements(
            By.CSS_SELECTOR, "table.t-class tr.ng-star-inserted"
        )
        if not linhas:
            logger.error("[PRAZOS] Nenhuma linha de destinatario encontrada!")
            return False

        logger.info("[PRAZOS] Encontradas %d linhas de destinatarios", len(linhas))

        ativos = []
        for tr in linhas:
            try:
                texto_linha = (tr.text or "").strip().upper()
                is_domicilio_eletronico = (
                    "domicilio eletronico"
                    in normalize_text(texto_linha)
                )

                checkbox = tr.find_element(
                    By.CSS_SELECTOR,
                    'input[type="checkbox"][aria-label="Intimar parte"]',
                )
                nome_elem = tr.find_element(
                    By.CSS_SELECTOR, ".destinario"
                )
                nome = nome_elem.text.strip().upper()

                if is_domicilio_eletronico:
                    if checkbox.get_attribute("aria-checked") == "true":
                        driver.execute_script(
                            "arguments[0].click();", checkbox
                        )
                        logger.info(
                            "[PRAZOS] Destinatario ignorado e desmarcado"
                            " (Domicilio Eletronico): %s",
                            nome,
                        )
                    else:
                        logger.info(
                            "[PRAZOS] Destinatario ignorado"
                            " (Domicilio Eletronico): %s",
                            nome,
                        )
                    continue

                if checkbox.get_attribute("aria-checked") == "true":
                    ativos.append((tr, checkbox, nome))
                    logger.info(
                        "[PRAZOS] Destinatario ativo encontrado: %s", nome
                    )
                elif perito and nome in [n.upper() for n in perito_nomes]:
                    driver.execute_script(
                        "arguments[0].click();", checkbox
                    )
                    logger.info("[PRAZOS] Perito ativado: %s", nome)
                    ativos.append((tr, checkbox, nome))

            except Exception as e:
                logger.warning("[PRAZOS] Erro ao processar linha: %s", e)
                continue

        if not ativos:
            logger.error(
                "[PRAZOS] Nenhum destinatario ativo"
                " (ou todos eram Domicilio Eletronico)!"
            )
            return False

        logger.info(
            "[PRAZOS] %d destinatarios ativos para preenchimento", len(ativos)
        )

        if apenas_primeiro and len(ativos) > 1:
            logger.info("[PRAZOS] Mantendo apenas o primeiro destinatario...")
            for i, (tr, checkbox, nome) in enumerate(ativos):
                if i == 0:
                    continue
                try:
                    driver.execute_script(
                        "arguments[0].click();", checkbox
                    )
                    logger.info(
                        "[PRAZOS] Destinatario %d desmarcado: %s",
                        i + 1,
                        nome,
                    )
                except Exception as e:
                    logger.warning(
                        "[PRAZOS] Erro ao desmarcar destinatario %d: %s",
                        i + 1,
                        e,
                    )
            ativos = [ativos[0]]

        campos_prazo = {}
        for i, (tr, checkbox, nome) in enumerate(ativos):
            try:
                input_prazo = tr.find_element(
                    By.CSS_SELECTOR,
                    'mat-form-field.prazo input[type="text"].mat-input-element',
                )
                campo_id = "prazo_destinatario_%d" % i
                driver.execute_script(
                    "arguments[0].id = arguments[1];",
                    input_prazo,
                    campo_id,
                )
                campos_prazo["#" + campo_id] = str(prazo)
                logger.info(
                    "[PRAZOS] Preparado prazo %s para destinatario: %s",
                    prazo,
                    nome,
                )
            except Exception as e:
                logger.warning(
                    "[PRAZOS] Erro ao preparar campo de prazo para %s: %s",
                    nome,
                    e,
                )
                continue

        if campos_prazo:
            resultado = preencher_multiplos_campos(driver, campos_prazo)
            if all(resultado.values()):
                logger.info(
                    "[PRAZOS] Todos os %d campos de prazo preenchidos com sucesso",
                    len(campos_prazo),
                )
            else:
                logger.warning(
                    "[PRAZOS] Alguns campos de prazo"
                    " podem nao ter sido preenchidos corretamente"
                )
                return False
        else:
            logger.warning("[PRAZOS] Nenhum campo de prazo para preencher")
            return False

        try:
            logger.info("[PRAZOS] Tentando gravar prazos...")

            driver.execute_script(
                """
                const overlays = document.querySelectorAll(
                    '.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-pane'
                );
                overlays.forEach(function(overlay) {
                    if (overlay.style) overlay.style.display = 'none';
                });
                const snackbars = document.querySelectorAll(
                    'snack-bar-container, simple-snack-bar'
                );
                snackbars.forEach(function(snack) {
                    if (snack.style) snack.style.display = 'none';
                });
                document.body.style.overflow = 'visible';
            """
            )

            btn_gravar_prazo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[.//span[normalize-space(text())='Gravar']"
                        " and contains(@class, 'mat-raised-button')"
                        " and not(contains(@aria-label, 'movimentos'))]",
                    )
                )
            )

            if btn_gravar_prazo.is_displayed() and btn_gravar_prazo.is_enabled():
                if safe_click_no_scroll(driver, btn_gravar_prazo, log=False):
                    logger.info(
                        "[PRAZOS] Prazos gravados via safe_click_no_scroll"
                    )
                else:
                    logger.warning(
                        "[PRAZOS] Falha em safe_click_no_scroll,"
                        " tentando .click()"
                    )
                    btn_gravar_prazo.click()
                    logger.info("[PRAZOS] Prazos gravados via Selenium")

                time.sleep(1)
                logger.info("[PRAZOS] Gravacao de prazos concluida")
            else:
                logger.warning("[PRAZOS] Botao Gravar nao esta disponivel")

        except Exception as e:
            logger.warning(
                "[PRAZOS] Nao foi possivel gravar prazos automaticamente: %s", e
            )

        logger.info("[PRAZOS] Preenchimento de prazos concluido")
        return True

    except Exception as e:
        logger.error("[PRAZOS] Erro geral ao preencher prazos: %s", e)
        return False


# ==============================================================================
# MOVIMENTO HELPERS
# ==============================================================================


def selecionar_movimento_dois_estagios(
    driver: WebDriver, movimento: str, timeout_select: int = 2
) -> bool:
    """Seleciona movimentos em multiplos estagios (comboboxes/complementos).

    Tenta, em ordem:
      1) localizar mat-select dentro de pje-complemento
      2) preencher input/textarea dentro do complemento
      3) fallback: mat-select visivel na pagina
    """
    termos = [t.strip() for t in re.split(r"[/\\-]", movimento) if t.strip()]
    if not termos:
        return False

    complementos = driver.find_elements(By.CSS_SELECTOR, "pje-complemento")
    usados = set()

    for termo in termos:
        termo_norm = _normalize_text(termo)
        encontrado = False

        # 1) mat-select dentro dos complementos
        for idx, comp in enumerate(complementos):
            if idx in usados:
                continue
            try:
                sel = comp.find_element(By.CSS_SELECTOR, "mat-select")
                try:
                    driver.execute_script(
                        "arguments[0].parentElement.parentElement.click();",
                        sel,
                    )
                except Exception:
                    driver.execute_script("arguments[0].click();", sel)

                opts = WebDriverWait(driver, timeout_select).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "mat-option[role='option']")
                    )
                )
                for op in opts:
                    try:
                        if termo_norm in _normalize_text(op.text or ""):
                            driver.execute_script(
                                "arguments[0].click();", op
                            )
                            usados.add(idx)
                            encontrado = True
                            break
                    except Exception:
                        continue
                if encontrado:
                    break
            except Exception:
                continue

        # 2) input/textarea no complemento
        if not encontrado:
            for idx, comp in enumerate(complementos):
                if idx in usados:
                    continue
                try:
                    inp = comp.find_element(By.CSS_SELECTOR, "input")
                    driver.execute_script(
                        "arguments[0].value = arguments[1];"
                        " arguments[0].dispatchEvent("
                        "   new Event('input',{bubbles:true})"
                        ");",
                        inp,
                        termo,
                    )
                    usados.add(idx)
                    encontrado = True
                    break
                except Exception:
                    try:
                        ta = comp.find_element(
                            By.CSS_SELECTOR, "textarea"
                        )
                        driver.execute_script(
                            "arguments[0].value = arguments[1];"
                            " arguments[0].dispatchEvent("
                            "   new Event('input',{bubbles:true})"
                            ");",
                            ta,
                            termo,
                        )
                        usados.add(idx)
                        encontrado = True
                        break
                    except Exception:
                        continue

        # 3) fallback: mat-select visivel na pagina
        if not encontrado:
            all_selects = driver.find_elements(
                By.CSS_SELECTOR, "mat-select"
            )
            for sel in all_selects:
                try:
                    try:
                        driver.execute_script(
                            "arguments[0].parentElement.parentElement.click();",
                            sel,
                        )
                    except Exception:
                        driver.execute_script(
                            "arguments[0].click();", sel
                        )
                    opts = WebDriverWait(driver, 1).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "mat-option[role='option']")
                        )
                    )
                    for op in opts:
                        if termo_norm in _normalize_text(op.text or ""):
                            driver.execute_script(
                                "arguments[0].click();", op
                            )
                            encontrado = True
                            break
                    if encontrado:
                        break
                except Exception:
                    continue

        if not encontrado:
            return False

        time.sleep(0.2)

    return True


def selecionar_movimento_auto(
    driver: WebDriver, movimento: str
) -> bool:
    """Chamada auxiliar: decide a estrategia e executa selecao.

    - se movimento contem '/' ou '-' -> usa selecionar_movimento_dois_estagios
    - caso contrario retorna False para que o chamador use fluxo por checkbox

    Retorna True se a selecao foi feita aqui, False se o chamador deve usar
    fluxo por checkbox.
    """
    if not movimento:
        return False
    if "/" in movimento or "-" in movimento:
        return selecionar_movimento_dois_estagios(driver, movimento)
    return False


# ==============================================================================
# VISIBILIDADE DE SIGILOSOS
# ==============================================================================


def _trocar_para_aba_detalhe(driver, log):
    """Tenta trocar para a aba /detalhe, retorna URL atual."""
    current_url = driver.current_url
    if len(driver.window_handles) > 1:
        detalhe_handle = None
        for handle in driver.window_handles:
            try:
                driver.switch_to.window(handle)
                url = driver.current_url
                if "/detalhe" in url:
                    detalhe_handle = handle
                    break
            except Exception:
                continue
        if detalhe_handle:
            driver.switch_to.window(detalhe_handle)
            return driver.current_url
        else:
            try:
                segundo = driver.window_handles[1]
                driver.switch_to.window(segundo)
                waited = 0
                while "/detalhe" not in driver.current_url and waited < 10:
                    time.sleep(1)
                    waited += 1
                return driver.current_url
            except Exception as e:
                if log:
                    logger.error(
                        "[VISIBILIDADE][ERRO]"
                        " Falha ao trocar para aba detalhe: %s",
                        e,
                    )
                return current_url
    return current_url


def _refresh_e_aguardar(driver, log):
    try:
        driver.refresh()
        _wait_for_page_load(driver, timeout=10)
    except Exception as refresh_err:
        if log:
            logger.error(
                "[VISIBILIDADE][F5][ERRO] Falha no refresh: %s", refresh_err
            )
        return False
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        if log:
            logger.warning(
                "[VISIBILIDADE] WebDriverWait readyState timeout"
                " apos refresh, prosseguindo"
            )
    return True


def _ativar_multipla_selecao(driver, log):
    try:
        btn_multi = driver.find_element(
            By.CSS_SELECTOR,
            'button[aria-label="Exibir multipla selecao."]',
        )
        btn_multi.click()
        time.sleep(0.5)
        return True
    except Exception as e:
        if log:
            logger.error(
                "[VISIBILIDADE][ERRO]"
                " Falha ao ativar multipla selecao: %s",
                e,
            )
        return False


def _clicar_primeira_checkbox(driver, log):
    try:
        primeira_checkbox = driver.find_element(
            By.CSS_SELECTOR,
            "ul.pje-timeline mat-card mat-checkbox label",
        )
        primeira_checkbox.click()
        time.sleep(0.5)
        return True
    except Exception as e:
        if log:
            logger.error(
                "[VISIBILIDADE][ERRO]"
                " Falha ao marcar primeira checkbox: %s",
                e,
            )
        return False


def _clicar_botao_visibilidade(driver, log):
    try:
        btn_visibilidade = driver.find_element(
            By.CSS_SELECTOR,
            "div.div-todas-atividades-em-lote"
            ' button[mattooltip="Visibilidade para Sigilo"]',
        )
        btn_visibilidade.click()
        time.sleep(1)
        return True
    except Exception as e:
        if log:
            logger.error(
                "[VISIBILIDADE][ERRO]"
                " Falha ao clicar no botao de visibilidade: %s",
                e,
            )
        return False


def _selecionar_polo(driver, polo, log):
    try:
        if polo == "ativo":
            icones = driver.find_elements(
                By.CSS_SELECTOR,
                'pje-data-table[nametabela="Tabela de Controle de Sigilo"]'
                " i.icone-polo-ativo",
            )
            for icone in icones:
                linha = icone.find_element(By.XPATH, "./../../..")
                label = linha.find_element(By.CSS_SELECTOR, "label")
                label.click()
        elif polo == "passivo":
            icones = driver.find_elements(
                By.CSS_SELECTOR,
                'pje-data-table[nametabela="Tabela de Controle de Sigilo"]'
                " i.icone-polo-passivo",
            )
            for icone in icones:
                linha = icone.find_element(By.XPATH, "./../../..")
                label = linha.find_element(By.CSS_SELECTOR, "label")
                label.click()
        elif polo == "ambos":
            btn_todos = driver.find_element(By.CSS_SELECTOR, "th button")
            btn_todos.click()
        return True
    except Exception as e:
        if log:
            logger.error(
                "[VISIBILIDADE][ERRO] Falha ao selecionar polo: %s", e
            )
        return False


def _clicar_salvar(driver, log):
    try:
        btn_salvar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//button[.//span[contains(text(),"Salvar")]]',
                )
            )
        )
        btn_salvar.click()
        time.sleep(1)
        return True
    except Exception as e:
        if log:
            logger.error(
                "[VISIBILIDADE][ERRO] Falha ao salvar configuracao: %s", e
            )
        return False


def _ocultar_multipla_selecao(driver):
    try:
        btn_ocultar = driver.find_element(
            By.CSS_SELECTOR,
            'button[aria-label="Ocultar multipla selecao."]',
        )
        btn_ocultar.click()
    except Exception:
        logger.debug(
            "[VISIBILIDADE] Botao ocultar multipla selecao"
            " nao encontrado (normal se ja oculto)"
        )


def visibilidade_sigilosos(driver, polo="ativo", log=False):
    """Aplica visibilidade a documentos sigilosos anexados automaticamente.

    Sequencia: Tab switch -> refresh -> Multipla selecao
               -> Primeira checkbox -> Visibilidade -> Salvar

    Args:
        driver: WebDriver.
        polo: 'ativo', 'passivo', 'ambos'.
        log: Ativa logs detalhados.

    Returns:
        True se executou com sucesso, False caso contrario.
    """
    try:
        _trocar_para_aba_detalhe(driver, log)
        if not _refresh_e_aguardar(driver, log):
            return False
        if not _ativar_multipla_selecao(driver, log):
            return False
        if not _clicar_primeira_checkbox(driver, log):
            return False
        if not _clicar_botao_visibilidade(driver, log):
            return False
        if not _selecionar_polo(driver, polo, log):
            return False
        if not _clicar_salvar(driver, log):
            return False
        _ocultar_multipla_selecao(driver)
        return True
    except Exception as e:
        if log:
            logger.error(
                "[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade: %s", e
            )
        return False


def executar_visibilidade_sigilosos_se_necessario(
    driver, sigilo_ativado, debug=False
):
    """Executa visibilidade_sigilosos se sigilo foi ativado.

    Deve ser chamada na aba /detalhe.

    Args:
        driver: WebDriver.
        sigilo_ativado: Boolean indicando se sigilo foi ativado.
        debug: Boolean para logs detalhados.

    Returns:
        True se executou com sucesso ou nao era necessario, False se falhou.
    """
    if not sigilo_ativado:
        return True

    try:
        current_url = driver.current_url
        if "/detalhe" not in current_url:
            logger.warning(
                "[VISIBILIDADE][WARN] URL atual nao contem /detalhe: %s",
                current_url,
            )
            logger.warning(
                "[VISIBILIDADE][WARN]"
                " A funcao visibilidade_sigilosos"
                " deve ser executada na URL /detalhe"
            )

        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.F5)

        try:
            aguardar_renderizacao_nativa(
                driver, "ul.pje-timeline", modo="aparecer", timeout=10
            )
        except Exception:
            logger.info(
                "[VISIBILIDADE] Observer timeout no F5,"
                " prosseguindo mesmo assim"
            )

        resultado = visibilidade_sigilosos(driver, log=debug)

        if resultado:
            return True
        else:
            logger.error(
                "[VISIBILIDADE][ERRO]"
                " Funcao visibilidade_sigilosos falhou."
            )
            return False

    except Exception as e:
        logger.error(
            "[VISIBILIDADE][ERRO]"
            " Excecao ao executar visibilidade_sigilosos: %s",
            e,
        )
        import traceback

        logger.exception("Erro detectado")
        return False
