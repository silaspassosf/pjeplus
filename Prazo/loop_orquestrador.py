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

_SEL_SPINNERS = (
    "div.carregando, mat-progress-spinner, mat-spinner, "
    "mat-progress-bar, .mat-progress-bar-primary.mat-progress-bar-fill"
)
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


def _aguardar_tela_livre(driver, teto: float = 5.0) -> bool:
    """Barreira de tela livre: aguarda backdrop modal e spinners/progress-bar sumirem."""
    ok_drop = espera.ate_sumir(driver, _SEL_BACKDROP, teto=min(teto, 5.0))
    ok_spin = espera.ate_sumir(driver, _SEL_SPINNERS, teto=teto)
    return bool(ok_spin and ok_drop)


def _ler_texto_paginacao(driver, teto: float = 0.0) -> str:
    """Lê o texto atual do contador de registros (ex.: '1 - 60 de 60')."""
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


def _ler_esperado_na_pagina(driver) -> int:
    """Extrai quantas linhas devem estar na página atual a partir de 'A - B de C'."""
    texto = _ler_texto_paginacao(driver)
    if not texto or "0 de 0" in texto:
        return 0
    match = re.search(r"(\d+)\s*-\s*(\d+)\s+de\s+(\d+)", texto)
    if match:
        inicio, fim = int(match.group(1)), int(match.group(2))
        if fim >= inicio > 0:
            return fim - inicio + 1
    total = _ler_total_registros(driver)
    return min(total, 100) if total > 0 else -1


def _contar_linhas_tabela(driver) -> int:
    """Conta quantas linhas tr.cdk-drag estão efetivamente renderizadas no DOM."""
    try:
        qtd = _executar_js(driver, "return document.querySelectorAll('tr.cdk-drag').length;")
        if isinstance(qtd, int) and qtd >= 0:
            return qtd
    except Exception:
        pass
    els = espera.elementos(driver, "tr.cdk-drag", teto=0.0)
    return len(els) if els else 0


def _aguardar_estabilizacao_tabela(driver, minimo_linhas: int = 1, teto: float = 15.0) -> bool:
    """Aguarda spinners sumirem, tabela renderizar todas as linhas esperadas e assentar GIGS."""
    def _linhas_prontas(drv):
        if espera.elemento(drv, _SEL_SPINNERS, teto=0.0):
            return False
        if _lista_esta_vazia(drv):
            return True
        esperado = _ler_esperado_na_pagina(drv)
        alvo = max(minimo_linhas, esperado if esperado > 0 else minimo_linhas)
        qtd = _contar_linhas_tabela(drv)
        return qtd >= alvo

    ok = bool(espera.ate(driver, _linhas_prontas, teto=teto))
    if not ok:
        logger.warning(
            "[PRAZO] Tabela não atingiu estabilização (linhas=%d, paginacao='%s', minimo=%d)",
            _contar_linhas_tabela(driver),
            _ler_texto_paginacao(driver),
            minimo_linhas,
        )
        return False
    espera.ate_sumir(driver, _SEL_BACKDROP, teto=2.0)
    espera.ate_sumir(driver, _SEL_SPINNERS, teto=5.0)
    # Aguarda a 2ª onda assíncrona do painel (poridsprocessos / etiquetasprocessos) popular as linhas
    espera.assentar(driver, 0.8, motivo="estabilizacao_pos_tabela")
    espera.pausa(driver, 0.5, motivo="hidratacao_gigs_linhas")
    return True


def _lista_esta_vazia(driver) -> bool:
    """True se o painel exibe estado vazio ou 0 registros na paginação."""
    total = _ler_total_registros(driver)
    if total > 0:
        return False
    if total == 0:
        return True
    return bool(espera.elemento(driver, _XPATH_LISTA_VAZIA, teto=0.0))


def _clicar_seguro(driver, elemento) -> bool:
    """Clica sem scroll com fallback para safe_click."""
    if safe_click_no_scroll(driver, elemento):
        return True
    return bool(safe_click(driver, elemento))


def _aguardar_estado_lista(driver, teto: float = 15.0) -> str:
    """Confirmador direto pelo setor de paginação (span.total-registros) ou mensagem vazia."""
    def _pronto(drv):
        total = _ler_total_registros(drv)
        if total > 0:
            return "ok"
        if total == 0 or espera.elemento(drv, _XPATH_LISTA_VAZIA, teto=0.0):
            return "vazio"
        if espera.elemento(drv, "tr.cdk-drag", teto=0.0):
            return "ok"
        return False

    estado = espera.ate(driver, _pronto, teto=teto)
    if not estado:
        return "vazio" if _lista_esta_vazia(driver) else "erro"
    return str(estado)


def _aguardar_recarregamento(
    driver,
    texto_antes: str = "",
    teto: float = 15.0,
    exigir_mudanca: bool = False,
) -> str:
    """Aguarda a paginação atualizar após filtro/ação e confirma estado via span.total-registros."""
    espera.ate_sumir(driver, _SEL_BACKDROP, teto=3.0)

    if texto_antes:
        def _mudou_ou_vazio(drv):
            atual = _ler_texto_paginacao(drv)
            if atual and atual != texto_antes:
                return True
            if espera.elemento(drv, _XPATH_LISTA_VAZIA, teto=0.0):
                return True
            return False

        mudou = bool(espera.ate(driver, _mudou_ou_vazio, teto=teto))
        if exigir_mudanca and not mudou:
            logger.error(
                "[PRAZO] Paginação não mudou após ação (mantido='%s')",
                texto_antes,
            )
            return "erro"

    espera.ate_sumir(driver, _SEL_SPINNERS, teto=teto)
    return _aguardar_estado_lista(driver, teto=teto)


def _navegar_para_painel(driver, url: str, url_token: str, tag: str) -> str:
    """Navega para o painel alvo e confirma carregamento pelo setor de paginação."""
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

    estado = _aguardar_estado_lista(driver, teto=15.0)
    logger.info("%s Painel carregado: estado=%s (%s)", tag, estado, _ler_texto_paginacao(driver) or "sem contador")
    return estado


def _aplicar_filtro_fases_com_barreira(
    driver,
    fases_alvo: Sequence[str] = FASES_PRAZOS_VENCIDOS,
    tag: str = "[PRAZO]",
) -> str:
    """Aplica filtro de fases e aguarda recarregamento completo da lista."""
    logger.info("%s Aplicando filtro de fases: %s", tag, list(fases_alvo))
    _aguardar_tela_livre(driver, teto=10.0)
    combo = buscar(
        driver,
        "ciclo1_mat_select_combobox",
        [
            'mat-select[aria-label*="Fase processual"]',
            'mat-select[formcontrolname="fpglobal_faseProcessual"]',
            'mat-select[placeholder*="Fase processual"]',
            "mat-select[role='combobox']",
            "//mat-select",
        ],
    )
    if not combo:
        logger.error("%s Dropdown de fases não encontrado", tag)
        return "erro"

    texto_antes = _ler_texto_paginacao(driver)
    if not filtrofases(driver, fases_alvo=list(fases_alvo)):
        logger.error("%s Falha ao aplicar filtrofases(%s)", tag, list(fases_alvo))
        return "erro"

    estado = _aguardar_recarregamento(driver, texto_antes=texto_antes, teto=20.0)
    if estado == "ok":
        _aguardar_estabilizacao_tabela(driver, minimo_linhas=1, teto=10.0)
    logger.info("%s Após filtro de fases: estado=%s (%s)", tag, estado, _ler_texto_paginacao(driver) or "sem contador")
    return estado


def _aplicar_filtro_100_com_barreira(driver, tag: str = "[PRAZO]") -> bool:
    """Aplica exibição de 100 registros por página e aguarda lista estabilizar por completo."""
    _aguardar_tela_livre(driver, teto=5.0)
    if espera.elemento(driver, _XPATH_FILTRO_100_ATIVO, teto=0.2):
        logger.info("%s Filtro lista 100 já ativo", tag)
        estado = _aguardar_estado_lista(driver, teto=10.0)
        if estado == "erro":
            return False
        if estado == "vazio":
            return True
        esperado = _ler_esperado_na_pagina(driver)
        minimo = max(1, esperado) if esperado > 0 else 1
        if not _aguardar_estabilizacao_tabela(driver, minimo_linhas=minimo, teto=20.0):
            logger.error("%s Tabela não estabilizou com filtro 100 já ativo", tag)
            return False
        return True

    texto_antes = _ler_texto_paginacao(driver)
    total_antes = _ler_total_registros(driver)
    logger.info("%s Aplicando filtro lista 100 (atual: %s)", tag, texto_antes or "n/d")
    if not aplicar_filtro_100(driver):
        logger.error("%s Falha ao aplicar filtro lista 100", tag)
        return False

    espera.ate_sumir(driver, _SEL_BACKDROP, teto=5.0)
    if not espera.ate_aparecer(driver, _XPATH_FILTRO_100_ATIVO, teto=6.0):
        logger.error("%s Seletor de paginação não confirmou '100'", tag)
        return False

    # Janela curta para o loader/progress-bar aparecer após selecionar 100
    espera.ate_aparecer(driver, _SEL_SPINNERS, teto=0.6)

    exigir_mudanca = bool(texto_antes and total_antes > 20)
    estado = _aguardar_recarregamento(
        driver,
        texto_antes=texto_antes if exigir_mudanca else "",
        teto=25.0,
        exigir_mudanca=exigir_mudanca,
    )
    if estado == "erro":
        logger.error("%s Lista não estabilizou após filtro 100", tag)
        return False
    if estado == "vazio":
        logger.info("%s Lista ficou vazia após filtro 100", tag)
        return True

    total_atual = _ler_total_registros(driver)
    referencia = total_atual if total_atual > 0 else total_antes
    esperado_pagina = _ler_esperado_na_pagina(driver)
    minimo_esperado = max(
        1,
        esperado_pagina if esperado_pagina > 0 else (min(referencia, 100) if referencia > 0 else 1),
    )
    if not _aguardar_estabilizacao_tabela(driver, minimo_linhas=minimo_esperado, teto=25.0):
        logger.error(
            "%s Filtro 100 não concluiu renderização antes do xs1 (esperado>=%d, linhas=%d, paginacao='%s')",
            tag,
            minimo_esperado,
            _contar_linhas_tabela(driver),
            _ler_texto_paginacao(driver),
        )
        return False

    logger.info("%s Filtro 100 concluído e tabela estabilizada (%s)", tag, _ler_texto_paginacao(driver) or estado)
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
    botoes = espera.elementos(driver, "mat-dialog-container button.mat-raised-button", teto=2.0)
    if not botoes:
        botoes = espera.elementos(driver, "button.mat-raised-button", teto=2.0)
    alvo = next((b for b in botoes if "Salvar" in (getattr(b, "text", "") or "")), None)
    if alvo:
        return alvo
    spans = espera.elementos(driver, "mat-dialog-container button.mat-raised-button span", teto=1.0)
    if not spans:
        spans = espera.elementos(driver, "button.mat-raised-button span", teto=1.0)
    span_alvo = next((s for s in spans if "Salvar" in (getattr(s, "text", "") or "")), None)
    if span_alvo:
        return span_alvo
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
    btn_next = (
        espera.elemento(driver, 'button[aria-label="Próximo"]', teto=2.0)
        or espera.elemento(driver, 'mat-paginator button[aria-label="Próxima página"]', teto=2.0)
    )
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
    if _aguardar_estado_lista(driver, teto=10.0) != "ok":
        return False
    esperado = _ler_esperado_na_pagina(driver)
    return _aguardar_estabilizacao_tabela(driver, minimo_linhas=max(1, esperado), teto=20.0)


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
