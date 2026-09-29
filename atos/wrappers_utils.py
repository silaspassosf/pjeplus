from typing import Any, Optional
import re
import logging
from Fix import espera
from Fix.core import aguardar_renderizacao_nativa, safe_click_no_scroll, preencher_campo

logger = logging.getLogger(__name__)


def esperar_insercao_modelo(driver: Any, timeout: int = 8000) -> bool:
    try:
        teto_s = max(float(timeout) / 1000.0, 1.0)
        return bool(
            espera.ate_texto(driver, 'simple-snack-bar', 'Modelo', teto=teto_s)
            or espera.ate_aparecer(driver, 'simple-snack-bar', teto=teto_s)
            or espera.ate_aparecer(driver, 'pje-dialogo-visualizar-modelo', teto=teto_s)
        )
    except Exception as e:
        logger.warning('[MODELO] Excecao em esperar_insercao_modelo: %s', e)
        return False


def _trocar_para_aba_detalhe(driver: Any, log: bool = False) -> str:
    try:
        if hasattr(driver, 'context') and hasattr(driver.context, 'pages'):
            for p in driver.context.pages:
                if '/detalhe' in (p.url or ''):
                    p.bring_to_front()
                    if hasattr(driver, '_pagina'):
                        driver._pagina = p
                    return p.url

        url_atual = getattr(driver, 'current_url', '') or ''
        if '/detalhe' in url_atual:
            return url_atual

        if '/processo/' in url_atual:
            match = re.search(r'/processo/(\d+)', url_atual)
            if match:
                id_proc = match.group(1)
                base_match = re.search(r'^(https?://[^/]+/pjekz)', url_atual)
                if base_match:
                    base_url = base_match.group(1)
                    nova_url = f"{base_url}/processo/{id_proc}/detalhe"
                    driver.get(nova_url)
                    return getattr(driver, 'current_url', '') or nova_url
    except Exception as e:
        logger.warning('[VISIBILIDADE][ERRO] Falha ao tentar restaurar URL de detalhe: %s', e)

    return getattr(driver, 'current_url', '') or ''


def _refresh_e_aguardar(driver: Any, log: bool = False) -> bool:
    try:
        driver.refresh()
        try:
            aguardar_renderizacao_nativa(driver, 'ul.pje-timeline', modo='aparecer', timeout=15)
        except Exception:
            pass
        return True
    except Exception as refresh_err:
        logger.warning('[VISIBILIDADE][F5][ERRO] Falha no refresh: %s', refresh_err)
        return False


def _ativar_multipla_selecao(driver: Any, log: bool = False) -> bool:
    try:
        btn_multi = espera.elemento(driver, 'button[aria-label="Exibir múltipla seleção."]', teto=10)
        if btn_multi:
            safe_click_no_scroll(driver, btn_multi)
            aguardar_renderizacao_nativa(driver, 'ul.pje-timeline mat-card mat-checkbox', 'aparecer', 3)
            return True
        return False
    except Exception as e:
        logger.warning('[VISIBILIDADE][ERRO] Falha ao ativar multipla selecao: %s', e)
        return False


def _clicar_primeira_checkbox(driver: Any, log: bool = False) -> bool:
    try:
        primeira_checkbox = espera.elemento(driver, 'ul.pje-timeline mat-card mat-checkbox label', teto=5)
        if primeira_checkbox:
            safe_click_no_scroll(driver, primeira_checkbox)
            aguardar_renderizacao_nativa(driver, 'ul.pje-timeline mat-card mat-checkbox.mat-checkbox-checked', 'aparecer', 3)
            return True
        return False
    except Exception as e:
        logger.warning('[VISIBILIDADE][ERRO] Falha ao marcar primeira checkbox: %s', e)
        return False


def _clicar_botao_visibilidade(driver: Any, log: bool = False) -> bool:
    try:
        btn_visibilidade = espera.elemento(driver, 'button[aria-label*="visibilidade para Sigilo"]', teto=3)
        if not btn_visibilidade:
            btn_visibilidade = espera.elemento(
                driver, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]', teto=3
            )
        if not btn_visibilidade:
            logger.warning('[VISIBILIDADE][ERRO] Botao de visibilidade nao encontrado')
            return False

        safe_click_no_scroll(driver, btn_visibilidade)
        aguardar_renderizacao_nativa(driver, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"]', 'aparecer', 5)
        return True
    except Exception as e:
        logger.warning('[VISIBILIDADE][ERRO] Falha ao clicar no botao de visibilidade: %s', e)
        return False


def _selecionar_polo(driver: Any, polo: str, log: bool = False) -> bool:
    try:
        if polo == 'ativo':
            xpath = '//pje-data-table[@nametabela="Tabela de Controle de Sigilo"]//tr[.//i[contains(@class, "POLO_ATIVO")]]//label'
            labels = espera.elementos(driver, xpath, teto=5)
            for label in labels:
                safe_click_no_scroll(driver, label)
        elif polo == 'passivo':
            xpath = '//pje-data-table[@nametabela="Tabela de Controle de Sigilo"]//tr[.//i[contains(@class, "POLO_PASSIVO")]]//label'
            labels = espera.elementos(driver, xpath, teto=5)
            for label in labels:
                safe_click_no_scroll(driver, label)
        elif polo == 'ambos':
            btn_todos = espera.elemento(driver, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] th button, th button', teto=5)
            if btn_todos:
                safe_click_no_scroll(driver, btn_todos)
        return True
    except Exception as e:
        logger.warning('[VISIBILIDADE][ERRO] Falha ao selecionar polo: %s', e)
        return False


def _clicar_salvar(driver: Any, log: bool = False) -> bool:
    try:
        btn_salvar = espera.elemento(driver, '//button[.//span[contains(text(),"Salvar")]]', teto=10)
        if btn_salvar:
            safe_click_no_scroll(driver, btn_salvar)
            aguardar_renderizacao_nativa(driver, 'simple-snack-bar', 'aparecer', 5)
            return True
        return False
    except Exception as e:
        logger.warning('[VISIBILIDADE][ERRO] Falha ao salvar configuracao: %s', e)
        return False


def _ocultar_multipla_selecao(driver: Any) -> None:
    try:
        btn_ocultar = espera.elemento(driver, 'button[aria-label="Ocultar múltipla seleção."]', teto=2)
        if btn_ocultar:
            safe_click_no_scroll(driver, btn_ocultar)
    except Exception:
        pass


def visibilidade_sigilosos(driver: Any, polo: str = 'ativo', log: bool = False) -> bool:
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
        logger.warning('[VISIBILIDADE][ERRO] Falha ao aplicar visibilidade: %s', e)
        return False


def executar_visibilidade_sigilosos_se_necessario(driver: Any, sigilo_ativado: bool, debug: bool = False) -> bool:
    if not sigilo_ativado:
        return True
    try:
        return visibilidade_sigilosos(driver, log=True)
    except Exception as e:
        logger.warning('[VISIBILIDADE][ERRO] Excecao ao executar visibilidade_sigilosos: %s', e)
        return False


def preparar_campo_filtro_modelo(driver: Any, log: bool = False) -> bool:
    try:
        campo = espera.elemento(driver, 'input#inputFiltro', teto=10)
        if not campo:
            return False
        preencher_campo(driver, 'input#inputFiltro', '', trigger_events=True, limpar=True)
        aguardar_renderizacao_nativa(driver, 'input#inputFiltro', 'aparecer', 2)
        return True
    except Exception as e:
        logger.warning('[CLS][MODELO][ERRO] Falha ao preparar campo de filtro de modelos: %s', e)
        return False
