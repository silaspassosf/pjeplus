"""
Andrei/atos_judicial.py - Atos judiciais PJe.

Fornece make_ato_wrapper (factory) e ato_judicial (fluxo principal)
para a execucao de atos judiciais no PJe.

Uso:
    from Andrei.atos_judicial import make_ato_wrapper
    wrapper = make_ato_wrapper(conclusao_tipo='Despacho', modelo_nome='Geral')
    sucesso, sigilo = wrapper(driver)
"""

import logging
import time
from typing import Optional, Tuple, Dict, List, Union, Callable, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
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
from Andrei.atos_helpers import (
    abrir_tarefa_processo,
    limpar_overlays,
    navegar_para_conclusao,
    preparar_campo_minutar,
    escolher_tipo_conclusao,
    aguardar_transicao_minutar,
    verificar_estado_atual,
    focar_campo_minutar_se_necessario,
    preencher_prazos_destinatarios,
    executar_visibilidade_sigilosos_se_necessario,
    safe_click_no_scroll,
    selecionar_movimento_auto,
)

logger = logging.getLogger(__name__)

__all__ = [
    "fluxo_cls",
    "ato_judicial",
    "make_ato_wrapper",
]


# ==============================================================================
# LOGGING HELPERS
# ==============================================================================


def log_start(modulo: str) -> None:
    """Registra inicio de processamento em modulo."""
    logger.info("[%s] START", modulo)


def log_fim(modulo: str, resumo) -> None:
    """Registra conclusao do processamento com resumo (dict ou str)."""
    logger.info("[%s] FIM %s", modulo, resumo)


# ==============================================================================
# FLUXO CLS - Conclusao ao Magistrado / Minutar
# ==============================================================================


def fluxo_cls(
    driver: WebDriver,
    conclusao_tipo: str,
    forcar_iniciar_execucao: bool = False,
) -> bool:
    """Fluxo principal para CLS (Conclusao ao Magistrado / Minutar).

    Logica sequencial:
    1. Verificar estados especiais (/assinar, /minutar, /conclusao)
    2. Abrir tarefa do processo se necessario
    3. Navegar para 'Conclusao ao Magistrado'
    4. Escolher tipo de conclusao
    5. Aguardar transicao para minutar e preparar campo

    Returns:
        bool: True se sucesso, False se falha.
    """
    log_start("CLS")
    timing_inicio = time.time()
    logger.info("[CLS][TIMING][INICIO]")

    try:
        logger.info("=" * 60)
        logger.info("FLUXO CLS - INICIANDO")
        logger.info("=" * 60)

        # ===== VERIFICACAO INICIAL: Estados especiais =====
        timing_check_estado = time.time()
        estado_atual = verificar_estado_atual(driver)
        timing_check_estado = time.time() - timing_check_estado
        logger.info(
            "[CLS][TIMING][CHECK_ESTADO] %.3fs estado=%s",
            timing_check_estado,
            estado_atual,
        )

        if estado_atual == "assinar":
            logger.info("[CLS] Processo ja esta em /assinar - ato cumprido")
            timing_total = time.time() - timing_inicio
            logger.info(
                "[CLS][TIMING][SUCESSO] %.3fs (estado pre-assinar)",
                timing_total,
            )
            return True
        elif estado_atual == "minutar":
            logger.info(
                "[CLS] Processo ja em /minutar - marcando como concluido"
            )
            timing_total = time.time() - timing_inicio
            logger.info(
                "[CLS][TIMING][SUCESSO] %.3fs (ja em /minutar)",
                timing_total,
            )
            return True
        elif estado_atual == "conclusao":
            logger.info(
                "[CLS] Ja estamos em /conclusao - pulando navegacao"
            )
            ja_em_conclusao = True
        else:
            ja_em_conclusao = False

        # ===== PASSO 1: ABRIR TAREFA DO PROCESSO =====
        ja_em_minutar = False
        if not ja_em_conclusao:
            current = (driver.current_url or "").lower()
            if "/detalhe" in current:
                logger.info(
                    "[CLS] Passo 1: Estamos em /detalhe"
                    " - abrindo tarefa do processo..."
                )
                timing_tarefa_inicio = time.time()
                sucesso, ja_em_minutar = abrir_tarefa_processo(driver)
                timing_tarefa = time.time() - timing_tarefa_inicio
                logger.info(
                    "[CLS][TIMING][ABRIR_TAREFA] %.3fs sucesso=%s",
                    timing_tarefa,
                    sucesso,
                )

                if not sucesso:
                    logger.error(
                        "[CLS] Falha ao abrir tarefa do processo"
                    )
                    timing_total = time.time() - timing_inicio
                    logger.info(
                        "[CLS][TIMING][ERRO] %.3fs falha ao abrir tarefa",
                        timing_total,
                    )
                    return False

                if ja_em_minutar:
                    current_after = (driver.current_url or "").lower()
                    if "/assinar" in current_after:
                        logger.info(
                            "[CLS] Ja em /assinar apos abrir tarefa"
                            " - ato cumprido"
                        )
                        timing_total = time.time() - timing_inicio
                        logger.info(
                            "[CLS][TIMING][SUCESSO] %.3fs"
                            " (estado pre-assinar)",
                            timing_total,
                        )
                        return True
                    elif "/minutar" in current_after:
                        logger.info(
                            "[CLS] Ja em /minutar apos abrir tarefa"
                            " - marcando como concluido"
                        )
                        timing_total = time.time() - timing_inicio
                        logger.info(
                            "[CLS][TIMING][SUCESSO] %.3fs"
                            " (ja em /minutar apos abrir tarefa)",
                            timing_total,
                        )
                        return True
                    elif "/conclusao" in current_after:
                        logger.info(
                            "[CLS] Detectado /conclusao apos abrir tarefa"
                            " - executando tipo de conclusao"
                            " para transicionar a /minutar"
                        )
                        try:
                            if not escolher_tipo_conclusao(
                                driver, conclusao_tipo
                            ):
                                logger.error(
                                    "[CLS] Falha ao escolher tipo"
                                    " de conclusao apos abrir tarefa: %s",
                                    conclusao_tipo,
                                )
                                timing_total = time.time() - timing_inicio
                                logger.info(
                                    "[CLS][TIMING][ERRO] %.3fs"
                                    " falha ao escolher tipo conclusao",
                                    timing_total,
                                )
                                return False
                            if not aguardar_transicao_minutar(driver):
                                logger.error(
                                    "[CLS] Falha na transicao para minutar"
                                    " apos escolher tipo de conclusao"
                                )
                                timing_total = time.time() - timing_inicio
                                logger.info(
                                    "[CLS][TIMING][ERRO] %.3fs"
                                    " falha na transicao minutar",
                                    timing_total,
                                )
                                return False
                            focar_campo_minutar_se_necessario(driver)
                            timing_total = time.time() - timing_inicio
                            logger.info(
                                "[CLS][TIMING][SUCESSO] %.3fs"
                                " (transicionado para /minutar)",
                                timing_total,
                            )
                            return True
                        except Exception as e:
                            logger.error(
                                "[CLS][ERRO CRITICO]"
                                " Excecao ao processar /conclusao"
                                " apos abrir tarefa: %s",
                                e,
                            )
                            import traceback

                            logger.error(traceback.format_exc())
                            return False
                    else:
                        logger.info(
                            "[CLS] Estado inesperado apos abrir tarefa: %s"
                            " - continuando fluxo",
                            current_after,
                        )
            else:
                logger.info(
                    "[CLS] Nao estamos em /detalhe"
                    " - assumindo que ja estamos na aba da tarefa"
                    " do processo (nao clicar em Abrir tarefa)"
                )
                sucesso = True
                ja_em_minutar = "/minutar" in current

        # ===== PASSO 2: LIMPAR OVERLAYS =====
        logger.info("[CLS] Passo 2: Limpando overlays...")
        timing_overlays_inicio = time.time()
        limpar_overlays(driver)
        timing_overlays = time.time() - timing_overlays_inicio
        logger.info(
            "[CLS][TIMING][LIMPAR_OVERLAYS] %.3fs", timing_overlays
        )

        # ===== PASSO 3: NAVEGAR PARA CONCLUSAO =====
        if not ja_em_conclusao:
            logger.info("[CLS] Passo 3: Navegando para conclusao...")
            timing_nav_inicio = time.time()
            try:
                if not navegar_para_conclusao(driver):
                    logger.error(
                        "[CLS] Falha ao navegar para conclusao"
                    )
                    timing_total = time.time() - timing_inicio
                    logger.info(
                        "[CLS][TIMING][ERRO] %.3fs"
                        " falha ao navegar conclusao",
                        timing_total,
                    )
                    return False
            except Exception as e:
                logger.error(
                    "[CLS][ERRO CRITICO]"
                    " Excecao em navegar_para_conclusao: %s",
                    e,
                )
                import traceback

                logger.error(traceback.format_exc())
                return False
            timing_nav = time.time() - timing_nav_inicio
            logger.info(
                "[CLS][TIMING][NAVEGAR_CONCLUSAO] %.3fs", timing_nav
            )

        # ===== PASSO 4: ESCOLHER TIPO DE CONCLUSAO =====
        logger.info(
            "[CLS] Passo 4: Escolhendo tipo de conclusao: %s",
            conclusao_tipo,
        )
        timing_tipo_inicio = time.time()
        try:
            if not escolher_tipo_conclusao(driver, conclusao_tipo):
                logger.error(
                    "[CLS] Falha ao escolher tipo de conclusao: %s",
                    conclusao_tipo,
                )
                timing_total = time.time() - timing_inicio
                logger.info(
                    "[CLS][TIMING][ERRO] %.3fs"
                    " falha ao escolher tipo conclusao",
                    timing_total,
                )
                return False
        except Exception as e:
            logger.error(
                "[CLS][ERRO CRITICO]"
                " Excecao em escolher_tipo_conclusao: %s",
                e,
            )
            import traceback

            logger.error(traceback.format_exc())
            return False
        timing_tipo = time.time() - timing_tipo_inicio
        logger.info(
            "[CLS][TIMING][ESCOLHER_TIPO] %.3fs tipo=%s",
            timing_tipo,
            conclusao_tipo,
        )

        # ===== PASSO 5: AGUARDAR TRANSICAO PARA MINUTAR =====
        logger.info("[CLS] Passo 5: Aguardando transicao para minutar...")
        timing_transicao_inicio = time.time()
        try:
            if not aguardar_transicao_minutar(driver):
                logger.error(
                    "[CLS] Falha na transicao para minutar"
                )
                timing_total = time.time() - timing_inicio
                logger.info(
                    "[CLS][TIMING][ERRO] %.3fs"
                    " falha na transicao minutar",
                    timing_total,
                )
                return False
        except Exception as e:
            logger.error(
                "[CLS][ERRO CRITICO]"
                " Excecao em aguardar_transicao_minutar: %s",
                e,
            )
            import traceback

            logger.error(traceback.format_exc())
            return False
        timing_transicao = time.time() - timing_transicao_inicio
        logger.info(
            "[CLS][TIMING][TRANSICAO_MINUTAR] %.3fs", timing_transicao
        )

        # ===== PASSO 6: PREPARAR CAMPO DE MINUTAR =====
        logger.info("[CLS] Passo 6: Preparando campo de minutar...")
        timing_campo_inicio = time.time()
        try:
            if not preparar_campo_minutar(driver):
                logger.error(
                    "[CLS] Falha ao preparar campo de minutar"
                )
                timing_total = time.time() - timing_inicio
                logger.info(
                    "[CLS][TIMING][ERRO] %.3fs"
                    " falha ao preparar campo minutar",
                    timing_total,
                )
                return False
        except Exception as e:
            logger.error(
                "[CLS][ERRO CRITICO]"
                " Excecao em preparar_campo_minutar: %s",
                e,
            )
            import traceback

            logger.error(traceback.format_exc())
            return False
        timing_campo = time.time() - timing_campo_inicio
        logger.info(
            "[CLS][TIMING][PREPARAR_CAMPO] %.3fs", timing_campo
        )

        logger.info("=" * 60)
        logger.info("FLUXO CLS - CONCLUIDO COM SUCESSO")
        logger.info("=" * 60)

        timing_total = time.time() - timing_inicio
        log_fim("CLS", {"status": "sucesso", "tempo": "%.3fs" % timing_total})
        logger.info(
            "[CLS][TIMING][SUCESSO] %.3fs (fluxo completo)", timing_total
        )
        return True

    except Exception as e:
        timing_total = time.time() - timing_inicio
        log_fim("CLS", {"status": "erro", "motivo": str(e)[:80]})
        logger.error(
            "[CLS][TIMING][ERRO] %.3fs erro inesperado: %s", timing_total, e
        )
        logger.error("[CLS] Erro inesperado no fluxo CLS: %s", e)
        return False


# ==============================================================================
# ATO JUDICIAL - Fluxo generalizado
# ==============================================================================


def ato_judicial(
    driver: WebDriver,
    conclusao_tipo: Optional[str] = None,
    modelo_nome: Optional[str] = None,
    prazo: Optional[Union[str, int]] = None,
    marcar_pec: Optional[bool] = None,
    movimento: Optional[str] = None,
    gigs: Optional[Any] = None,
    marcar_primeiro_destinatario: Optional[bool] = None,
    debug: bool = False,
    sigilo: Optional[str] = None,
    descricao: Optional[str] = None,
    perito: bool = False,
    Assinar: bool = False,
    coleta_conteudo: Optional[Callable] = None,
    inserir_conteudo: Optional[Callable] = None,
    intimar: Optional[bool] = None,
    **kwargs: Any,
) -> Tuple[bool, bool]:
    """Fluxo generalizado para qualquer ato judicial, seguindo a ordem:

    0. Coleta de conteudo parametrizavel (PRIMEIRO PASSO - na aba /detalhe)
    1. Modelo (fluxo_cls)
    2. Descricao
    3. Sigilo
    4. Intimar
    5. PEC
    6. Prazo
    7. Movimento
    8. Assinar

    Returns:
        (sucesso: bool, sigilo_ativado: bool)
    """
    atribuir_visibilidade_autor = False
    try:
        atribuir_visibilidade_autor = bool(
            kwargs.pop("atribuir_visibilidade_autor", False)
        )
    except Exception:
        atribuir_visibilidade_autor = False

    log_start("ATO")
    timing_inicio = time.time()
    logger.info(
        "[ATO][TIMING][INICIO] conclusao_tipo=%s modelo_nome=%s",
        conclusao_tipo,
        modelo_nome,
    )

    try:
        # 0. COLETA DE CONTEUDO PARAMETRIZAVEL
        if coleta_conteudo:
            logger.info(
                "[ATO][COLETA]"
                " Executando coleta de conteudo parametrizavel"
                " ANTES do fluxo principal..."
            )
            try:
                current_url = driver.current_url
                if "/detalhe" not in current_url:
                    logger.warning(
                        "[ATO][COLETA][WARN]"
                        " URL atual nao contem /detalhe: %s",
                        current_url,
                    )
                    logger.warning(
                        "[ATO][COLETA][WARN]"
                        " Coleta deve ser executada na aba /detalhe"
                    )

                coleta_conteudo(driver)
                logger.info("[ATO][COLETA] Coleta de conteudo concluida")
            except Exception as e:
                logger.error(
                    "[ATO][COLETA] Erro na coleta de conteudo: %s", e
                )
                return False, False

        # 1. MODELO: fluxo_cls
        logger.info(
            "[ATO][CLS] Iniciando fluxo CLS: conclusao_tipo=%s",
            conclusao_tipo,
        )
        timing_fluxo_cls_inicio = time.time()
        if not fluxo_cls(driver, conclusao_tipo or "decisao"):
            logger.error("[ATO][CLS] Falha no fluxo CLS")
            timing_total = time.time() - timing_inicio
            logger.info(
                "[ATO][TIMING][ERRO] %.3fs falha fluxo CLS", timing_total
            )
            return False, False
        timing_fluxo_cls = time.time() - timing_fluxo_cls_inicio
        logger.info(
            "[ATO][TIMING][FLUXO_CLS] %.3fs", timing_fluxo_cls
        )

        if modelo_nome:

            # ===== DESCRICAO (antes de inserir modelo) =====
            if descricao:
                logger.info(
                    "[ATO][DESCRICAO] Preenchendo descricao: %s", descricao
                )
                try:
                    campo_descricao = esperar_elemento(
                        driver,
                        'input[aria-label="Descricao"]',
                        timeout=10,
                        by=By.CSS_SELECTOR,
                    )
                    if campo_descricao:
                        campo_descricao.clear()
                        driver.execute_script(
                            """
                            var input = arguments[0];
                            var valor = arguments[1];
                            input.focus();
                            input.value = valor;
                            ['input', 'change', 'keyup'].forEach(function(ev) {
                                input.dispatchEvent(
                                    new Event(ev, {bubbles: true})
                                );
                            });
                            input.blur();
                        """,
                            campo_descricao,
                            descricao,
                        )
                        logger.info(
                            "[ATO][DESCRICAO] Descricao preenchida"
                        )
                    else:
                        raise Exception("Campo descricao nao encontrado")
                except Exception as e:
                    logger.error(
                        "[ATO][DESCRICAO] Erro ao preencher descricao: %s",
                        e,
                    )

            # Preencher filtro do modelo
            try:
                logger.info(
                    "[ATO][MODELO] Preenchendo filtro com modelo: %s",
                    modelo_nome,
                )
                campo_filtro_modelo = esperar_elemento(
                    driver,
                    "input#inputFiltro",
                    timeout=10,
                    by=By.CSS_SELECTOR,
                )
                if not campo_filtro_modelo:
                    raise Exception("Campo filtro modelo nao encontrado")

                driver.execute_script(
                    "arguments[0].focus();", campo_filtro_modelo
                )
                driver.execute_script(
                    "arguments[0].value = arguments[1];",
                    campo_filtro_modelo,
                    modelo_nome,
                )

                for ev in ["input", "change", "keyup"]:
                    driver.execute_script(
                        "var evt = new Event(arguments[1],"
                        " {bubbles:true});"
                        " arguments[0].dispatchEvent(evt);",
                        campo_filtro_modelo,
                        ev,
                    )

                campo_filtro_modelo.send_keys(Keys.ENTER)
                logger.info(
                    "[ATO][MODELO] Modelo \"%s\" preenchido via JS"
                    " e ENTER pressionado no filtro.",
                    modelo_nome,
                )

                try:
                    aguardar_renderizacao_nativa(
                        driver,
                        ".nodo-filtrado",
                        modo="aparecer",
                        timeout=10,
                    )
                except Exception:
                    logger.warning(
                        "[ATO][MODELO]"
                        " Timeout aguardando nodo-filtrado,"
                        " prosseguindo..."
                    )

            except Exception as e:
                logger.error(
                    "[ATO][MODELO]"
                    " Erro ao preencher filtro do modelo: %s",
                    e,
                )
                return False, False

            # Inserir modelo especifico (gigs L15111-15115: querySelector direto)
            try:
                clicou = driver.execute_script("""
                    var el = document.querySelector('.nodo-filtrado');
                    if (el) { el.click(); return true; }
                    return false;
                """)
                if not clicou:
                    logger.error(
                        "[ATO][MODELO] Nodo do modelo nao encontrado!"
                    )
                    return False, False
                logger.info(
                    "[ATO][MODELO] Clique em nodo-filtrado realizado!"
                )

                try:
                    modal_aberto = aguardar_renderizacao_nativa(
                        driver,
                        "pje-dialogo-visualizar-modelo",
                        modo="aparecer",
                        timeout=5,
                    )
                except Exception:
                    modal_aberto = False
                if not modal_aberto:
                    logger.warning(
                        "[ATO][MODELO]"
                        " Modal nao abriu,"
                        " tentando inserir mesmo assim..."
                    )

                seletor_btn_inserir = (
                    "pje-dialogo-visualizar-modelo"
                    " > div > div.div-preview-botoes"
                    " > div.div-botao-inserir > button"
                )

                inseriu = driver.execute_script("""
                    var btn = document.querySelector(arguments[0]);
                    if (btn && !btn.disabled) { btn.click(); return true; }
                    return false;
                """, seletor_btn_inserir)
                if not inseriu:
                    logger.error(
                        "[ATO][MODELO] Botao inserir nao encontrado ou desabilitado"
                    )
                    return False, False
                logger.info("[ATO][MODELO] Modelo inserido")

                try:
                    aguardar_renderizacao_nativa(
                        driver,
                        "simple-snack-bar",
                        modo="aparecer",
                        timeout=5,
                    )
                except Exception:
                    pass

            except Exception as e:
                logger.error(
                    "[ATO][MODELO] Erro ao inserir modelo: %s", e
                )
                return False, False

        # ===== INSERIR CONTEUDO =====
        if inserir_conteudo:
            logger.info("[ATO][INSERIR] Executando insercao de conteudo...")
            try:
                inserir_conteudo(driver)
                logger.info("[ATO][INSERIR] Conteudo inserido")
            except Exception as e:
                logger.error(
                    "[ATO][INSERIR] Erro ao inserir conteudo: %s", e
                )
                return False, False

        # ===== SALVAR APOS INSERCAO (gigs: clicarBotao) =====
        logger.info("[ATO][SALVAR] Salvando modelo apos insercao...")
        try:
            btn_salvar = esperar_elemento(
                driver,
                "button[aria-label='Salvar']",
                timeout=10,
                by=By.CSS_SELECTOR,
            )
            if not btn_salvar:
                raise Exception("Botao Salvar nao disponivel")
            driver.execute_script("arguments[0].click();", btn_salvar)
            logger.info("[ATO][SALVAR] Clique no botao Salvar realizado")

            try:
                aguardar_renderizacao_nativa(
                    driver,
                    "pje-editor-lateral",
                    modo="aparecer",
                    timeout=10,
                )
            except Exception:
                logger.warning(
                    "[ATO][SALVAR]"
                    " Timeout aguardando aba destinatarios,"
                    " prosseguindo..."
                )
            logger.info(
                "[ATO][SALVAR]"
                " Aguardando ativacao da aba destinatarios..."
            )

        except Exception as e:
            logger.error(
                "[ATO][SALVAR]"
                " Botao Salvar nao encontrado"
                " ou nao clicavel: %s",
                e,
            )
            return False, False

        # ===== ABA DESTINATARIOS - PRAZOS =====
        intimar_ativado = (
            True
            if intimar is None
            else str(intimar).lower() in ("sim", "true", "1")
        )

        if not intimar_ativado:
            logger.info(
                "[ATO][INTIMAR] Desativando intimacoes automaticas..."
            )
            try:
                guia_intimacoes = esperar_elemento(
                    driver,
                    'pje-editor-lateral div[aria-posinset="1"]',
                    timeout=10,
                    by=By.CSS_SELECTOR,
                )
                if (
                    guia_intimacoes
                    and guia_intimacoes.get_attribute("aria-selected")
                    == "false"
                ):
                    guia_intimacoes.click()

                toggle_intimar = esperar_elemento(
                    driver,
                    "pje-intimacao-automatica label.mat-slide-toggle-label",
                    timeout=10,
                    by=By.CSS_SELECTOR,
                )
                if toggle_intimar:
                    parent_toggle = toggle_intimar.find_element(
                        By.XPATH, ".."
                    )
                    if "mat-checked" in parent_toggle.get_attribute(
                        "class"
                    ):
                        toggle_intimar.click()
                    logger.info(
                        '[ATO][INTIMAR] Toggle "Intimar?" desativado.'
                    )
                else:
                    logger.info(
                        "[ATO][INTIMAR]"
                        ' Toggle "Intimar?" ja estava desativado.'
                    )
            except Exception as e:
                logger.error(
                    "[ATO][INTIMAR] Erro ao desativar intimacoes: %s", e
                )

        if prazo is not None and intimar_ativado:
            logger.info(
                "[ATO][PRAZO] Preenchendo prazos: %s"
                " (apenas_primeiro=%s)",
                prazo,
                marcar_primeiro_destinatario,
            )
            try:
                if not preencher_prazos_destinatarios(
                    driver,
                    prazo,
                    apenas_primeiro=marcar_primeiro_destinatario,
                    perito=perito,
                ):
                    logger.error("[ATO][PRAZO] Falha ao preencher prazos")
                    return False, False

                driver.execute_script(
                    """
                    const overlays = document.querySelectorAll(
                        '.cdk-overlay-backdrop, .mat-dialog-container,'
                        + ' .cdk-overlay-pane'
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
                try:
                    aguardar_renderizacao_nativa(
                        driver,
                        ".cdk-overlay-backdrop, .mat-dialog-container,"
                        " .cdk-overlay-pane",
                        modo="sumir",
                        timeout=3,
                    )
                except Exception:
                    logger.debug(
                        "[ATO][PRAZO]"
                        " Observer overlays indisponivel"
                        " (nao critico)"
                    )

                logger.info("[ATO][PRAZO] Prazos concluidos")
            except Exception as e:
                logger.error(
                    "[ATO][PRAZO] Erro ao preencher prazos: %s", e
                )
                return False, False

        # ===== ABA DESTINATARIOS - PEC =====
        if marcar_pec is not None:
            marcar_pec_bool = str(marcar_pec).lower() in (
                "sim",
                "true",
                "1",
                "yes",
            )
            logger.info(
                "[ATO][PEC] Parametro: marcar_pec=%r", marcar_pec
            )
            try:
                pec_checkbox = None
                pec_input = None

                pec_checkbox = esperar_elemento(
                    driver,
                    'mat-checkbox[aria-label="Enviar para PEC"]',
                    timeout=10,
                    by=By.CSS_SELECTOR,
                )
                if pec_checkbox:
                    pec_input = pec_checkbox.find_element(
                        By.CSS_SELECTOR, 'input[type="checkbox"]'
                    )
                else:
                    pec_checkbox = esperar_elemento(
                        driver,
                        "div.checkbox-pec mat-checkbox",
                        timeout=5,
                        by=By.CSS_SELECTOR,
                    )
                    if pec_checkbox:
                        pec_input = pec_checkbox.find_element(
                            By.CSS_SELECTOR, 'input[type="checkbox"]'
                        )
                    else:
                        pec_input = esperar_elemento(
                            driver,
                            'input[type="checkbox"]'
                            '[aria-label="Enviar para PEC"]',
                            timeout=5,
                            by=By.CSS_SELECTOR,
                        )
                        if pec_input:
                            pec_checkbox = pec_input.find_element(
                                By.XPATH,
                                "./ancestor::mat-checkbox[1]",
                            )
                        else:
                            pec_checkbox = None
                            pec_input = None

                if not pec_checkbox or not pec_input:
                    raise Exception("Checkbox PEC nao encontrado")

                is_checked = False
                try:
                    if (
                        pec_input.get_attribute("aria-checked") == "true"
                        or pec_input.get_attribute("checked") == "true"
                        or pec_input.is_selected()
                        or "mat-checkbox-checked"
                        in pec_checkbox.get_attribute("class")
                    ):
                        is_checked = True
                except Exception:
                    is_checked = False

                logger.info(
                    "[ATO][PEC] Estado: %s -> esperado: %s",
                    "marcado" if is_checked else "desmarcado",
                    "marcar" if marcar_pec_bool else "desmarcar",
                )

                if marcar_pec_bool != is_checked:
                    try:
                        label = pec_checkbox.find_element(
                            By.CSS_SELECTOR,
                            "label.mat-checkbox-layout",
                        )
                        safe_click_no_scroll(driver, label, log=False)
                    except Exception:
                        safe_click_no_scroll(
                            driver, pec_checkbox, log=False
                        )
                        driver.execute_script(
                            "arguments[0].click();", pec_checkbox
                        )

                    logger.info(
                        "[ATO][PEC] %s",
                        "Marcado" if marcar_pec_bool else "Desmarcado",
                    )
                else:
                    logger.info("[ATO][PEC] Ja esta conforme esperado")

            except Exception as e:
                logger.error("[ATO][PEC] %s", e)

        # ===== GRAVAR INTIMACOES =====
        logger.info("[ATO][GRAVAR] Gravando intimacoes...")
        try:
            btn_gravar_intim = wait_for_clickable(
                driver,
                'button[aria-label="Gravar a intimacao/notificacao"]',
                timeout=10,
                by=By.CSS_SELECTOR,
            )
            if btn_gravar_intim:
                safe_click_no_scroll(driver, btn_gravar_intim, log=False)
                logger.info("[ATO][GRAVAR] Intimacoes gravadas")
                try:
                    aguardar_renderizacao_nativa(
                        driver,
                        "simple-snack-bar",
                        modo="aparecer",
                        timeout=5,
                    )
                except Exception:
                    pass
            else:
                logger.debug(
                    "[ATO][GRAVAR]"
                    " Botao Gravar nao encontrado"
                    " (sem alteracoes?)"
                )
        except Exception as e:
            logger.debug("[ATO][GRAVAR] %s", e)

        # ===== ABA DESTINATARIOS - MOVIMENTO =====
        sigilo_ativado = False
        if movimento:
            logger.info(
                "[ATO][MOVIMENTO] Selecionando movimento: %s", movimento
            )
            try:
                try:
                    aba_mov = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                "//div[contains(@class,'mat-tab-label')"
                                " and .//span[contains("
                                "  translate(text(),"
                                "  'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                                "  'abcdefghijklmnopqrstuvwxyz'"
                                "  ),'movimentos')]]",
                            )
                        )
                    )
                    if aba_mov.get_attribute("aria-selected") != "true":
                        safe_click_no_scroll(driver, aba_mov, log=False)
                        logger.debug(
                            "[ATO][MOVIMENTO] Aba Movimentos clicada"
                        )
                        aguardar_renderizacao_nativa(driver)
                except Exception as e:
                    logger.debug(
                        "[ATO][MOVIMENTO]"
                        " Nao foi possivel clicar na aba"
                        " Movimentos: %s",
                        e,
                    )

                if "/" in movimento or "-" in movimento:
                    if not selecionar_movimento_auto(driver, movimento):
                        logger.error(
                            "[ATO][MOVIMENTO]"
                            " Movimento nao encontrado: %s",
                            movimento,
                        )
                        return False, False
                    logger.info(
                        "[ATO][MOVIMENTO]"
                        " Movimento selecionado via combobox"
                    )
                else:
                    js_mov = (
                        "(function() {"
                        "    setTimeout(function() {"
                        "        var textoMov = '%s'"
                        "            .trim().toLowerCase()"
                        "            .replace(/\\s+/g, ' ');"
                        "        var checkboxes = Array.from("
                        "            document.querySelectorAll("
                        "                'mat-checkbox.mat-checkbox"
                        "                .movimento'"
                        "            )"
                        "        );"
                        "        var selecionado = false;"
                        "        function normalizarTexto(texto) {"
                        "            return texto.normalize('NFD')"
                        "                .replace(/[\\u0300-\\u036f]/g, '')"
                        "                .toLowerCase().trim();"
                        "        }"
                        "        var termoPesquisa ="
                        "            normalizarTexto(textoMov);"
                        "        for (var cb of checkboxes) {"
                        "            try {"
                        "                var label = cb.querySelector("
                        "                    'label.mat-checkbox-layout"
                        "                     .mat-checkbox-label'"
                        "                );"
                        "                var labelText = label"
                        "                    && label.textContent"
                        "                    ? label.textContent : '';"
                        "                var labelNorm = labelText"
                        "                    .trim().toLowerCase()"
                        "                    .replace(/\\s+/g, ' ');"
                        "                var labelSemAcento ="
                        "                    normalizarTexto(labelText);"
                        "                var encontrado ="
                        "                    labelNorm.includes("
                        "                        textoMov"
                        "                    )"
                        "                    || labelSemAcento.includes("
                        "                        termoPesquisa"
                        "                    )"
                        "                    || (textoMov === 'frustrada'"
                        "                        && (labelSemAcento"
                        "                            .includes("
                        "                               'execucao"
                        "                                frustrada'"
                        "                            )"
                        "                            || labelSemAcento"
                        "                               .includes('276')"
                        "                        )"
                        "                    )"
                        "                    || (textoMov.match(/^\\d+$/)"
                        "                        && labelText.includes("
                        "                            '(' + textoMov"
                        "                            + ')'"
                        "                        )"
                        "                    );"
                        "                if (encontrado) {"
                        "                    var input = cb.querySelector("
                        "                        'input[type=\"checkbox\"]'"
                        "                    );"
                        "                    if (input && !input.checked)"
                        "                    {"
                        "                        var inner = cb"
                        "                            .querySelector("
                        "                                '.mat-checkbox"
                        "                                -inner-container'"
                        "                            );"
                        "                        if(inner) {"
                        "                            inner.click();"
                        "                        } else {"
                        "                            input.click();"
                        "                        }"
                        "                    }"
                        "                    window.selecionadoMovimento"
                        "                        = true;"
                        "                    window.labelSelecionadoMovimento"
                        "                        = labelText;"
                        "                    selecionado = true;"
                        "                    break;"
                        "                }"
                        "            } catch (e) {"
                        "                console.warn("
                        "                    '[ATO][MOVIMENTO]"
                        "                     Erro ao processar"
                        "                     checkbox:', e"
                        "                );"
                        "            }"
                        "        }"
                        "        if (!selecionado) {"
                        "            console.warn("
                        "                '[ATO][MOVIMENTO]"
                        "                 Movimento nao encontrado'"
                        "            );"
                        "            window.selecionadoMovimento = false;"
                        "        }"
                        "    }, 800);"
                        "})();"
                    ) % _escape_js_string(movimento)

                    driver.execute_script(js_mov)
                    try:
                        aguardar_renderizacao_nativa(
                            driver,
                            ".mat-checkbox-checked",
                            modo="aparecer",
                            timeout=5,
                        )
                    except Exception:
                        pass

                    selecionado = driver.execute_script(
                        "return window.selecionadoMovimento;"
                    )
                    if not selecionado:
                        logger.error(
                            "[ATO][MOVIMENTO]"
                            " Movimento nao encontrado: %s",
                            movimento,
                        )
                        return False, False
                    label_mov = driver.execute_script(
                        "return window.labelSelecionadoMovimento;"
                    )
                    logger.info(
                        "[ATO][MOVIMENTO] Checkbox marcado: %s",
                        label_mov,
                    )

                logger.info("[ATO][MOVIMENTO] Gravando movimento...")
                btn_gravar_mov = wait_for_clickable(
                    driver,
                    "button[aria-label="
                    "'Gravar os movimentos a serem lancados']",
                    timeout=10,
                    by=By.CSS_SELECTOR,
                )
                if btn_gravar_mov:
                    btn_gravar_mov.click()
                try:
                    aguardar_renderizacao_nativa(
                        driver,
                        "//button[contains(@class, 'mat-button')"
                        " and contains(@class, 'mat-primary')"
                        " and .//span[text()='Sim']]",
                        modo="aparecer",
                        timeout=8,
                    )
                except Exception:
                    pass

                logger.info("[ATO][MOVIMENTO] Confirmando...")
                btn_sim = wait_for_clickable(
                    driver,
                    "//button[contains(@class, 'mat-button')"
                    " and contains(@class, 'mat-primary')"
                    " and .//span[text()='Sim']]",
                    timeout=10,
                    by=By.XPATH,
                )
                if btn_sim:
                    btn_sim.click()
                    try:
                        aguardar_renderizacao_nativa(
                            driver,
                            "simple-snack-bar",
                            modo="aparecer",
                            timeout=5,
                        )
                    except Exception:
                        pass
                    logger.info(
                        "[ATO][MOVIMENTO] Movimento gravado e confirmado"
                    )
                else:
                    logger.warning(
                        "[ATO][MOVIMENTO] Botao Sim nao encontrado"
                    )

                try:
                    if sigilo:
                        logger.info(
                            "[ATO][SIGILO]"
                            " Aplicando sigilo"
                            " apos gravacao do movimento..."
                        )
                        try:
                            slide = esperar_elemento(
                                driver,
                                'mat-slide-toggle[name="sigiloso"],'
                                ' mat-slide-toggle#sigilo',
                                timeout=5,
                                by=By.CSS_SELECTOR,
                            )

                            try:
                                input_sig = slide.find_element(
                                    By.CSS_SELECTOR,
                                    'input[type="checkbox"]',
                                )
                            except Exception:
                                input_sig = None

                            is_checked = False
                            try:
                                if input_sig:
                                    is_checked = (
                                        input_sig.get_attribute(
                                            "aria-checked"
                                        )
                                        == "true"
                                        or input_sig.is_selected()
                                    )
                                else:
                                    cls = slide.get_attribute("class") or ""
                                    is_checked = "mat-checked" in cls
                            except Exception:
                                is_checked = False

                            if not is_checked:
                                try:
                                    label = slide.find_element(
                                        By.CSS_SELECTOR,
                                        "label.mat-slide-toggle-label",
                                    )
                                    safe_click_no_scroll(
                                        driver, label, log=False
                                    )
                                except Exception:
                                    try:
                                        if input_sig:
                                            driver.execute_script(
                                                "arguments[0].click();",
                                                input_sig,
                                            )
                                        else:
                                            driver.execute_script(
                                                "arguments[0].click();",
                                                slide,
                                            )
                                    except Exception:
                                        try:
                                            driver.execute_script(
                                                """
                                                var el = arguments[0]
                                                    .querySelector(
                                                        'input[type="checkbox"]'
                                                    )
                                                    || arguments[0];
                                                el.checked = true;
                                                el.dispatchEvent(
                                                    new Event(
                                                        'change',
                                                        {bubbles:true}
                                                    )
                                                );
                                            """,
                                                slide,
                                            )
                                        except Exception:
                                            logger.debug(
                                                "[ATO][SIGILO]"
                                                " Fallback de JS"
                                                " para marcar sigilo falhou"
                                            )
                            sigilo_ativado = True
                            logger.info(
                                "[ATO][SIGILO]"
                                " Sigilo aplicado (apos movimento)"
                            )
                        except Exception as e:
                            logger.debug(
                                "[ATO][SIGILO]"
                                " Falha ao aplicar sigilo"
                                " apos movimento: %s",
                                e,
                            )
                except Exception:
                    logger.debug(
                        "[ATO][SIGILO]"
                        " Excecao no bloco sigilo"
                        " (nao critico, continuando)"
                    )

            except Exception as e:
                logger.error(
                    "[ATO][MOVIMENTO] Erro ao selecionar movimento: %s", e
                )
                return False, False

        # Intimacao permanece marcada por padrao
        if intimar_ativado:
            logger.debug(
                "[ATO][INTIMAR]"
                " Intimacao permanece marcada por padrao"
                " (nenhuma acao realizada)"
            )

        # ===== GRAVAR / SALVAR FINAL =====
        if movimento:
            logger.info("[ATO][SALVAR] Salvando ato apos movimento...")
            try:
                btn_salvar = esperar_elemento(
                    driver,
                    "button[aria-label='Salvar'][color='primary']",
                    timeout=10,
                    by=By.CSS_SELECTOR,
                )
                if not btn_salvar:
                    raise Exception("Botao Salvar nao disponivel")

                driver.execute_script("arguments[0].click();", btn_salvar)
                logger.info("[ATO][SALVAR] Ato salvo")
                try:
                    aguardar_renderizacao_nativa(
                        driver, "button#assinar", modo="aparecer", timeout=8
                    )
                except Exception:
                    pass

            except Exception as e:
                logger.error(
                    "[ATO][SALVAR] Erro ao salvar apos movimento: %s", e
                )
                return False, False
        else:
            logger.info("[ATO][SALVAR] Salvando ato (sem movimento)...")
            try:
                btn_salvar_final = esperar_elemento(
                    driver,
                    "button[aria-label='Salvar'][color='primary']",
                    timeout=10,
                    by=By.CSS_SELECTOR,
                )
                if not btn_salvar_final:
                    raise Exception("Botao Salvar nao disponivel")
                driver.execute_script("arguments[0].click();", btn_salvar_final)
                logger.info("[ATO][SALVAR] Ato salvo")
                try:
                    aguardar_renderizacao_nativa(
                        driver, "button#assinar", modo="aparecer", timeout=8
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.error("[ATO][SALVAR] %s", e)
                return False, False

        # ===== ASSINAR =====
        if Assinar:
            logger.info("[ATO][ASSINAR] Clicando em assinar...")
            try:
                btn_assinar = esperar_elemento(
                    driver, "button#assinar", timeout=10, by=By.CSS_SELECTOR
                )
                if btn_assinar:
                    driver.execute_script("arguments[0].click();", btn_assinar)
                    logger.info("[ATO][ASSINAR] Assinar clicado")
                else:
                    raise Exception("Botao assinar nao disponivel")
            except Exception as e:
                logger.error(
                    "[ATO][ASSINAR] Erro ao clicar em assinar: %s", e
                )
                return False, False

        logger.info("=" * 60)
        logger.info("ATO JUDICIAL - CONCLUIDO COM SUCESSO")
        logger.info("=" * 60)

        try:
            if sigilo_ativado and atribuir_visibilidade_autor:
                logger.info(
                    "[ATO][VISIBILIDADE]"
                    " Sigilo ativado e wrapper solicitou visibilidade"
                    " - executando visibilidade canonica"
                )
                try:
                    executar_visibilidade_sigilosos_se_necessario(
                        driver, sigilo_ativado, debug=debug
                    )
                    logger.info(
                        "[ATO][VISIBILIDADE]"
                        " Execucao da visibilidade concluida"
                    )
                except Exception as e:
                    logger.error(
                        "[ATO][VISIBILIDADE]"
                        " Falha ao executar visibilidade: %s",
                        e,
                    )
            elif sigilo_ativado and not atribuir_visibilidade_autor:
                logger.debug(
                    "[ATO][VISIBILIDADE]"
                    " Sigilo ativado, mas wrapper"
                    " nao solicitou atribuicao automatica"
                    " de visibilidade; pulando execucao"
                )
        except Exception:
            logger.warning(
                "[ATO][VISIBILIDADE]"
                " Excecao inesperada no bloco de visibilidade"
                " (nao critico)"
            )

        timing_total = time.time() - timing_inicio
        log_fim(
            "ATO",
            {
                "status": "sucesso",
                "sigilo": sigilo_ativado,
                "tempo": "%.3fs" % timing_total,
            },
        )
        logger.info(
            "[ATO][TIMING][SUCESSO] %.3fs (fluxo completo)", timing_total
        )
        return True, sigilo_ativado

    except Exception as e:
        timing_total = time.time() - timing_inicio
        log_fim("ATO", {"status": "erro", "motivo": str(e)[:80]})
        logger.error(
            "[ATO][TIMING][ERRO] %.3fs erro inesperado: %s",
            timing_total,
            e,
        )
        logger.error("[ATO] Erro inesperado no ato judicial: %s", e)
        return False, False


# ==============================================================================
# FACTORY: make_ato_wrapper
# ==============================================================================


def make_ato_wrapper(
    conclusao_tipo: str,
    modelo_nome: str,
    prazo: Optional[Union[str, int]] = None,
    marcar_pec: Optional[bool] = None,
    movimento: Optional[str] = None,
    gigs: Optional[Any] = None,
    marcar_primeiro_destinatario: Optional[bool] = None,
    descricao: Optional[str] = None,
    sigilo: Optional[str] = None,
    perito: bool = False,
    Assinar: bool = False,
    coleta_conteudo: Optional[Callable] = None,
    inserir_conteudo: Optional[Callable] = None,
    intimar: Optional[bool] = None,
    atribuir_visibilidade_autor: Optional[bool] = False,
) -> Callable[[WebDriver, Any], Tuple[bool, bool]]:
    """Factory function que cria um wrapper para ato_judicial
    com parametros pre-definidos.

    Returns:
        function: Wrapper para ato_judicial com parametros fixos.
    """
    def wrapper(driver, **kwargs):
        """Wrapper para ato_judicial com parametros pre-configurados."""
        params = {
            "conclusao_tipo": conclusao_tipo,
            "modelo_nome": modelo_nome,
            "prazo": prazo,
            "marcar_pec": marcar_pec,
            "movimento": movimento,
            "gigs": gigs,
            "marcar_primeiro_destinatario": marcar_primeiro_destinatario,
            "descricao": descricao,
            "sigilo": sigilo,
            "perito": perito,
            "Assinar": Assinar,
            "coleta_conteudo": coleta_conteudo,
            "inserir_conteudo": inserir_conteudo,
            "intimar": intimar,
            "atribuir_visibilidade_autor": atribuir_visibilidade_autor,
        }
        params.update(kwargs)
        return ato_judicial(driver, **params)

    modelo_part = (
        modelo_nome.lower().replace(" ", "_") if modelo_nome else "sem_modelo"
    )
    wrapper.__name__ = "ato_%s_%s" % (
        conclusao_tipo.lower(),
        modelo_part,
    )
    return wrapper


# ==============================================================================
# HELPER: JS string escaping
# ==============================================================================


def _escape_js_string(s: str) -> str:
    """Escapa uma string para uso seguro dentro de JavaScript."""
    if not s:
        return ""
    result = (
        s.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return result


