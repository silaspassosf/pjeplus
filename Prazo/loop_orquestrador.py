"""Prazo - Orquestrador sequencial de 7 etapas com barreiras Playwright.

Sequência antes do P2B:
1. Navega para Prazos vencidos (painel/global/14)
2. Filtra fases Liquidação + Execução
3. Filtra lista para 100 registros
4. Seleciona livres + cria atividade xs1 (-1//xs1) página a página
5. Navega para Cumprimento de providências (painel/global/6)
6. Filtra lista para 100 registros
7. Seleciona livres + cria atividade xs1 (-1//xs1) página a página
"""
import logging
import math
import re
from typing import Optional, Sequence

from Fix import espera
from Fix.core import (
    _executar_js,
    aplicar_filtro_100,
    filtrofases,
    preencher_campo,
    safe_click,
    safe_click_no_scroll,
)
from Fix.facade_publica import buscar
from core.resultado_execucao import ResultadoExecucao

logger = logging.getLogger(__name__)

URL_PAINEL_PRAZOS_VENCIDOS = "https://pje.trt2.jus.br/pjekz/painel/global/14/lista-processos"
URL_PAINEL_CUMPRIMENTO = "https://pje.trt2.jus.br/pjekz/painel/global/6/lista-processos"
FASES_PRAZOS_VENCIDOS = ("liquidação", "execução")

_SEL_SPINNERS = "div.carregando, mat-progress-spinner, mat-spinner"
_SEL_BACKDROP = ".cdk-overlay-backdrop.cdk-overlay-backdrop-showing"
_XPATH_LISTA_VAZIA = "//span[contains(text(), 'Não há processos neste tema')]"
_XPATH_FILTRO_100_ATIVO = "//span[contains(@class,'mat-select-min-line') and normalize-space(text())='100']"

_SEL_PRAZO_XS = (
    'input[formcontrolname="dias"]',
    'input[formcontrolname="prazo"]',
    'input[aria-label="Prazo em dias úteis"]',
    'mat-form-field input[type="number"]',
    'input[type="number"]',
)
_SEL_OBS_XS = (
    "textarea[formcontrolname='observacao']",
    "textarea[aria-label*='Observa']",
    "textarea",
)

SCRIPT_SELECAO_LIVRES = r'''
try {
    let linhas = document.querySelectorAll('tr.cdk-drag');
    let selecionados = 0;
    linhas.forEach(function(linha){
        let prazo = linha.querySelector('td[data-label*="prazo" i] time, td:nth-child(9) time');
        let prazoVazio = !prazo || !prazo.textContent.trim();
        let hasComment = linha.querySelector('i.fa-comment') !== null;
        let inputField = linha.querySelector('input[matinput]');
        let campoPreenchido = inputField && inputField.value.trim();
        let temLupa = linha.querySelector('td[data-label*="processo" i] i.fa-search, td:nth-child(3) i.fa-search') !== null;
        if (prazoVazio && !hasComment && !campoPreenchido && !temLupa) {
            let checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
            if (checkbox && !checkbox.checked) {
                checkbox.click();
                linha.style.backgroundColor = "#ffccd2";
                selecionados++;
            }
        }
    });
    return selecionados;
} catch(e) { return -1; }
'''


def _aguardar_tela_livre(driver, teto: float = 15.0) -> bool:
    """Barreira: aguarda spinners e backdrops modais desaparecerem."""
    ok_spin = espera.ate_sumir(driver, _SEL_SPINNERS, teto=teto)
    ok_drop = espera.ate_sumir(driver, _SEL_BACKDROP, teto=min(teto, 8.0))
    return bool(ok_spin and ok_drop)


def _ler_texto_paginacao(driver, teto: float = 0.0) -> str:
    """Lê o texto atual do contador de registros (ex.: '1 - 100 de 140')."""
    el = espera.elemento(driver, "span.total-registros", teto=teto)
    if not el:
        return ""
    return (getattr(el, "text", "") or "").strip()


def _ler_total_registros(driver) -> int:
    """Extrai o total numérico de registros; retorna 0 se vazio ou -1 se indisponível."""
    texto = _ler_texto_paginacao(driver)
    if not texto:
        return -1
    if "0 de 0" in texto:
        return 0
    match = re.search(r"de\s+(\d+)", texto)
    return int(match.group(1)) if match else -1


def _lista_esta_vazia(driver) -> bool:
    """True se o painel exibe estado vazio ou 0 registros."""
    if espera.elemento(driver, _XPATH_LISTA_VAZIA, teto=0.0):
        return True
    return _ler_total_registros(driver) == 0


def _clicar_seguro(driver, elemento) -> bool:
    """Clica sem scroll com fallback para safe_click."""
    if safe_click_no_scroll(driver, elemento):
        return True
    return bool(safe_click(driver, elemento))


def _aguardar_estado_lista(driver, teto: float = 15.0) -> str:
    """Barreira: aguarda a tabela renderizar linhas ou estado vazio sem spinners."""
    def _pronto(drv):
        if _lista_esta_vazia(drv):
            return "vazio"
        if espera.elemento(drv, "tr.cdk-drag", teto=0.0):
            return "ok"
        return False

    estado = espera.ate(driver, _pronto, teto=teto)
    _aguardar_tela_livre(driver, teto=min(teto, 10.0))
    if not estado:
        return "vazio" if _lista_esta_vazia(driver) else "erro"
    if _lista_esta_vazia(driver):
        return "vazio"
    return str(estado)


def _aguardar_recarregamento(driver, texto_antes: str = "", teto: float = 20.0) -> str:
    """Barreira pós-ação: captura eventual spinner/mudança e espera lista estabilizar."""
    espera.ate_sumir(driver, _SEL_BACKDROP, teto=5.0)

    def _iniciou_ou_mudou(drv):
        if espera.elemento(drv, _SEL_SPINNERS, teto=0.0):
            return True
        if texto_antes:
            atual = _ler_texto_paginacao(drv)
            if atual and atual != texto_antes:
                return True
        if _lista_esta_vazia(drv):
            return True
        return False

    espera.ate(driver, _iniciou_ou_mudou, teto=0.8)
    _aguardar_tela_livre(driver, teto=teto)
    return _aguardar_estado_lista(driver, teto=min(teto, 15.0))


def _navegar_para_painel(driver, url: str, url_token: str, tag: str) -> str:
    """Navega para o painel alvo e aguarda URL + lista/vazio estabilizarem."""
    logger.info("%s Navegando para %s", tag, url)
    url_ok = False
    for tentativa in range(2):
        driver.get(url)
        if espera.ate_url(driver, url_token, teto=12.0):
            url_ok = True
            break
        logger.warning("%s URL ainda não contém '%s' (tentativa %d/2)", tag, url_token, tentativa + 1)

    if not url_ok:
        logger.error("%s Falha ao navegar para %s (atual: %s)", tag, url, getattr(driver, "current_url", ""))
        return "erro"

    _aguardar_tela_livre(driver, teto=15.0)
    estado = _aguardar_estado_lista(driver, teto=15.0)
    logger.info("%s Painel carregado: estado=%s", tag, estado)
    return estado


def _aplicar_filtro_fases_com_barreira(
    driver,
    fases_alvo: Sequence[str] = FASES_PRAZOS_VENCIDOS,
    tag: str = "[PRAZO]",
) -> str:
    """Aplica filtro de fases e aguarda recarregamento completo da lista."""
    logger.info("%s Aplicando filtro de fases: %s", tag, list(fases_alvo))
    _aguardar_tela_livre(driver, teto=10.0)
    combo = buscar(driver, "ciclo1_mat_select_combobox", ["mat-select[role='combobox']", "//mat-select"])
    if not combo:
        logger.error("%s Dropdown de fases não encontrado", tag)
        return "erro"

    texto_antes = _ler_texto_paginacao(driver)
    if not filtrofases(driver, fases_alvo=list(fases_alvo)):
        logger.error("%s Falha ao aplicar filtrofases(%s)", tag, list(fases_alvo))
        return "erro"

    estado = _aguardar_recarregamento(driver, texto_antes=texto_antes, teto=20.0)
    logger.info("%s Após filtro de fases: estado=%s (%s)", tag, estado, _ler_texto_paginacao(driver) or "sem contador")
    return estado


def _aplicar_filtro_100_com_barreira(driver, tag: str = "[PRAZO]") -> bool:
    """Aplica exibição de 100 registros por página e aguarda lista estabilizar."""
    _aguardar_tela_livre(driver, teto=10.0)
    if espera.elemento(driver, _XPATH_FILTRO_100_ATIVO, teto=0.2):
        logger.info("%s Filtro lista 100 já ativo", tag)
        return _aguardar_estado_lista(driver, teto=10.0) != "erro"

    texto_antes = _ler_texto_paginacao(driver)
    total_antes = _ler_total_registros(driver)
    logger.info("%s Aplicando filtro lista 100 (atual: %s)", tag, texto_antes or "n/d")
    if not aplicar_filtro_100(driver):
        logger.error("%s Falha ao aplicar filtro lista 100", tag)
        return False

    espera.ate_sumir(driver, _SEL_BACKDROP, teto=5.0)
    espera.ate_aparecer(driver, _XPATH_FILTRO_100_ATIVO, teto=6.0)
    estado = _aguardar_recarregamento(
        driver,
        texto_antes=texto_antes if total_antes > 20 else "",
        teto=15.0,
    )
    if estado == "erro":
        logger.error("%s Lista não estabilizou após filtro 100", tag)
        return False
    logger.info("%s Filtro 100 concluído (%s)", tag, _ler_texto_paginacao(driver) or estado)
    return True


def _clicar_item_atividade(driver, tag: str) -> bool:
    """Localiza e clica na opção 'Atividade' do menu de etiqueta verde."""
    espera.ate_aparecer(driver, "button.mat-menu-item", teto=6.0)
    itens = espera.elementos(driver, "button.mat-menu-item", teto=3.0)
    btn_atividade = next((el for el in itens if "Atividade" in (getattr(el, "text", "") or "")), None)
    if not btn_atividade:
        btn_atividade = buscar(
            driver,
            "ciclo2_btn_atividade",
            [
                "//button[contains(@class, 'mat-menu-item') and contains(., 'Atividade')]",
                "//button[@role='menuitem' and contains(., 'Atividade')]",
            ],
        )
    if not btn_atividade:
        logger.error("%s Item 'Atividade' não encontrado no menu", tag)
        return False
    return _clicar_seguro(driver, btn_atividade)


def _encontrar_botao_salvar(driver):
    """Localiza o botão Salvar dentro do modal de atividade."""
    spans = espera.elementos(driver, "mat-dialog-container button.mat-raised-button span", teto=2.0)
    if not spans:
        spans = espera.elementos(driver, "button.mat-raised-button span", teto=2.0)
    alvo = next((s for s in spans if "Salvar" in (getattr(s, "text", "") or "")), None)
    if not alvo:
        alvo = espera.elemento(driver, "button[aria-label*='Salvar'] span", teto=1.0)
    if alvo:
        return espera.elemento(alvo, "..", teto=0.5) or alvo
    return espera.elemento(driver, "button[aria-label*='Salvar']", teto=1.0)


def _criar_atividade_xs1_com_barreira(
    driver,
    tag: str = "[PRAZO]",
    prazo: str = "-1",
    observacao: str = "xs1",
) -> bool:
    """Cria atividade em lote (-1//xs1) e aguarda fechamento do modal e spinners."""
    tag_verde = espera.elemento(driver, "i.fa.fa-tag.icone.texto-verde", teto=10.0)
    if not tag_verde or not _clicar_seguro(driver, tag_verde):
        logger.error("%s Etiqueta verde não encontrada/clicável", tag)
        return False

    if not _clicar_item_atividade(driver, tag):
        return False

    if not espera.ate_aparecer(driver, "mat-dialog-container", teto=10.0):
        logger.error("%s Modal de atividade não abriu", tag)
        return False
    espera.ate_aparecer(driver, "textarea[formcontrolname='observacao']", teto=6.0)

    if prazo:
        for seletor in _SEL_PRAZO_XS:
            if preencher_campo(driver, seletor, prazo):
                break

    obs_ok = any(preencher_campo(driver, seletor, observacao) for seletor in _SEL_OBS_XS)
    if not obs_ok:
        logger.error("%s Campo de observação não preenchido", tag)
        return False

    btn_salvar = _encontrar_botao_salvar(driver)
    if not btn_salvar or not _clicar_seguro(driver, btn_salvar):
        logger.error("%s Botão Salvar não encontrado/clicável", tag)
        return False

    if not espera.ate_sumir(driver, "mat-dialog-container", teto=20.0):
        logger.error("%s Modal de atividade permaneceu aberto após Salvar", tag)
        return False

    espera.ate(driver, lambda d: espera.elemento(d, _SEL_SPINNERS, teto=0.0), teto=0.5)
    _aguardar_tela_livre(driver, teto=20.0)
    logger.info("%s Atividade '%s//%s' criada e tela liberada", tag, prazo, observacao)
    return True


def _avancar_pagina_com_barreira(driver, texto_antes: str, tag: str) -> bool:
    """Avança para a próxima página e aguarda o texto da paginação mudar + tabela estabilizar."""
    btn_next = espera.elemento(driver, 'mat-paginator button[aria-label="Próxima página"]', teto=5.0)
    if not btn_next:
        logger.info("%s Botão próxima página ausente", tag)
        return False

    desabilitado = (
        btn_next.get_attribute("disabled") is not None
        or btn_next.get_attribute("aria-disabled") == "true"
    )
    if desabilitado:
        logger.info("%s Última página atingida (botão desabilitado)", tag)
        return False

    if not _clicar_seguro(driver, btn_next):
        logger.warning("%s Falha ao clicar em Próxima página", tag)
        return False

    if texto_antes:
        mudou = espera.ate(
            driver,
            lambda d: (_ler_texto_paginacao(d) not in ("", texto_antes)),
            teto=15.0,
        )
        if not mudou:
            logger.warning("%s Paginação não mudou após clique (mantido: '%s')", tag, texto_antes)
            return False

    _aguardar_tela_livre(driver, teto=15.0)
    return _aguardar_estado_lista(driver, teto=10.0) == "ok"


def _executar_painel_livres_xs1(
    driver,
    *,
    tag: str,
    url: str,
    url_token: str,
    fases_alvo: Optional[Sequence[str]] = None,
) -> bool:
    """Executa um painel completo: navegar -> [filtrar fases] -> filtro 100 -> livres + xs1."""
    estado = _navegar_para_painel(driver, url, url_token, tag)
    if estado == "vazio":
        logger.info("%s Painel sem processos — etapa concluída", tag)
        return True
    if estado != "ok":
        return False

    if fases_alvo:
        estado = _aplicar_filtro_fases_com_barreira(driver, fases_alvo=fases_alvo, tag=tag)
        if estado == "vazio":
            logger.info("%s Sem processos após filtro de fases — etapa concluída", tag)
            return True
        if estado != "ok":
            return False

    if not _aplicar_filtro_100_com_barreira(driver, tag=tag):
        return False

    if _lista_esta_vazia(driver):
        logger.info("%s Lista vazia após filtro 100 — etapa concluída", tag)
        return True

    total = _ler_total_registros(driver)
    paginas = math.ceil(total / 100) if total > 0 else 1
    logger.info("%s Iniciando seleção de livres: total=%d paginas=%d", tag, total, paginas)

    for pagina in range(paginas):
        _aguardar_tela_livre(driver, teto=15.0)
        if not espera.ate_aparecer(driver, "tr.cdk-drag", teto=10.0):
            logger.warning("%s Sem linhas visíveis na página %d/%d", tag, pagina + 1, paginas)
            break

        texto_pagina = _ler_texto_paginacao(driver)
        selecionados = _executar_js(driver, SCRIPT_SELECAO_LIVRES)
        if selecionados is None or selecionados < 0:
            logger.error("%s Erro JS ao selecionar livres na página %d/%d", tag, pagina + 1, paginas)
            return False

        logger.info("%s Página %d/%d: %d livre(s) selecionado(s)", tag, pagina + 1, paginas, selecionados)
        if selecionados > 0:
            espera.ate_js(
                driver,
                "document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').length > 0",
                teto=5.0,
            )
            if not _criar_atividade_xs1_com_barreira(driver, tag=tag):
                return False

        if pagina < paginas - 1:
            if not _avancar_pagina_com_barreira(driver, texto_pagina, tag):
                break

    _aguardar_tela_livre(driver, teto=10.0)
    logger.info("%s Painel concluído com sucesso", tag)
    return True


def ciclo0(driver) -> bool:
    """Etapas 1-4: Prazos vencidos -> fases Liquidação+Execução -> lista 100 -> livres + xs1."""
    return _executar_painel_livres_xs1(
        driver,
        tag="[PRAZO][VENCIDOS]",
        url=URL_PAINEL_PRAZOS_VENCIDOS,
        url_token="painel/global/14",
        fases_alvo=FASES_PRAZOS_VENCIDOS,
    )


def ciclo3(driver) -> bool:
    """Etapas 5-7: Cumprimento de providências -> lista 100 -> livres + xs1."""
    return _executar_painel_livres_xs1(
        driver,
        tag="[PRAZO][CUMPRIMENTO]",
        url=URL_PAINEL_CUMPRIMENTO,
        url_token="painel/global/6",
        fases_alvo=None,
    )


def loop_prazo(driver) -> ResultadoExecucao:
    """Executa o fluxo Prazo completo (etapas 1-7) antes do P2B."""
    logger.info("[PRAZO] Iniciando fluxo sequencial de 7 etapas (Vencidos -> Cumprimento)")
    try:
        ok_vencidos = ciclo0(driver)
        if not ok_vencidos:
            return ResultadoExecucao(
                sucesso=False,
                status="FALHA",
                erro="Falha no painel Prazos vencidos (etapas 1-4)",
                detalhes={
                    "prazos_vencidos": False,
                    "cumprimento_providencias": False,
                    "ciclo0": False,
                    "ciclo3": False,
                },
            )

        _aguardar_tela_livre(driver, teto=15.0)
        ok_cumprimento = ciclo3(driver)
        _aguardar_tela_livre(driver, teto=10.0)
        return ResultadoExecucao(
            sucesso=ok_cumprimento,
            status="OK" if ok_cumprimento else "FALHA",
            erro=None if ok_cumprimento else "Falha no painel Cumprimento de providências (etapas 5-7)",
            detalhes={
                "prazos_vencidos": True,
                "cumprimento_providencias": ok_cumprimento,
                "ciclo0": True,
                "ciclo3": ok_cumprimento,
            },
        )
    except Exception as exc:
        logger.error("[PRAZO] Erro crítico no fluxo Prazo: %s", exc)
        return ResultadoExecucao(
            sucesso=False,
            status="ERRO",
            erro=str(exc),
            detalhes={"erro": str(exc)},
        )
