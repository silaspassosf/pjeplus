"""Prazo - Orquestrador sequencial de 8 etapas com barreiras Playwright.

Sequência antes do P2B:
1. Navega para Prazos vencidos (painel/global/14)
2. Filtra fases Liquidação + Execução
3. Filtra lista para 100 registros
4. Seleciona livres + cria atividade xs1 (-1//xs1) página a página
5. Navega para Cumprimento de providências (painel/global/6)
6. Filtra lista para 100 registros
7. Seleciona livres + cria atividade xs1 (-1//xs1) página a página
8. Filtra via API processos livres em Análise (Liquidação/Execução):
   - se "Aguardando prazo" disponível → movimenta via API para "Aguardando prazo"
   - se "Aguardando prazo" indisponível → cria GIGS 1//xs1
"""
import logging
import math
import re
from typing import Any, Dict, List, Optional, Sequence

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


def _criar_gigs_1_xs1_no_processo(driver, id_processo: int, numero_processo: str, tag: str) -> bool:
    """Abre /detalhe em nova aba, cria GIGS 1//xs1 e fecha a aba voltando para a aba base."""
    from Fix.browser_suporte import abrir_url_nova_aba, forcar_fechamento_abas_extras
    from Fix.core import garantir_carregamento_pagina
    from Fix.extracao import criar_gigs
    from Fix.variaveis import url_processo_detalhe

    aba_base = getattr(driver, "current_window_handle", None)
    url = url_processo_detalhe(id_processo, "detalhe")
    try:
        nova_aba = abrir_url_nova_aba(driver, url, timeout=15.0)
        if not nova_aba:
            logger.error("%s %s: falha ao abrir nova aba %s", tag, numero_processo, url)
            return False

        garantir_carregamento_pagina(
            driver,
            seletor_esperado="pje-cabecalho-processo,pje-timeline",
            timeout_refresh=15.0,
            url_alvo=url,
        )
        ok = bool(criar_gigs(driver, "1", "", "xs1"))
        if ok:
            logger.info("%s %s: GIGS 1//xs1 criada com sucesso", tag, numero_processo)
        else:
            logger.error("%s %s: criar_gigs('1', '', 'xs1') retornou False", tag, numero_processo)
        return ok
    except Exception as exc:
        logger.error("%s %s: erro ao criar GIGS 1//xs1: %s", tag, numero_processo, exc)
        return False
    finally:
        if aba_base:
            try:
                forcar_fechamento_abas_extras(driver, aba_base)
            except Exception as exc_close:
                logger.warning("%s %s: falha ao fechar aba extra: %s", tag, numero_processo, exc_close)


def ciclo_analise_livres(driver, *, tag: str = "[PRAZO][ANALISE_LIVRES]") -> Dict[str, Any]:
    """Etapa 8 (pós-Cumprimento): filtra livres em Análise (Liq/Exec) via API e despacha ações.

    - Livre + "Aguardando prazo" disponível  → movimenta para "Aguardando prazo" via rota API.
    - Livre + "Aguardando prazo" indisponível → cria GIGS 1//xs1.
    """
    from Fix.variaveis import cliente_para
    from api.filtro_analise import (
        NOME_TRANSICAO_AGUARDANDO_PRAZO,
        filtrar_processos_analise_livres,
    )

    resumo: Dict[str, Any] = {
        "ok": True,
        "total_livres": 0,
        "movidos_aguardando_prazo": [],
        "gigs_xs1_criadas": [],
        "falhas_movimento": [],
        "falhas_gigs": [],
        "sem_status_transicao": [],
        "diagnostico": {},
    }

    try:
        client = cliente_para(driver)
        processos, diag = filtrar_processos_analise_livres(
            client,
            confirmar_gigs_individual=True,
            consultar_escaninho=True,
            aguardando_prazo_disponivel=None,
            retornar_diagnostico=True,
        )
    except Exception as exc:
        logger.error("%s Falha na consulta API de Análise livres: %s", tag, exc)
        resumo["ok"] = False
        resumo["erro"] = str(exc)
        return resumo

    resumo["total_livres"] = len(processos)
    resumo["diagnostico"] = diag

    if not processos:
        logger.info("%s Nenhum processo livre em Análise (Liq/Exec)", tag)
        return resumo

    para_aguardando_prazo = [p for p in processos if p.aguardando_prazo_disponivel is True]
    para_gigs_xs1 = [p for p in processos if p.aguardando_prazo_disponivel is False]
    sem_status = [p for p in processos if p.aguardando_prazo_disponivel is None]

    logger.info(
        "%s Livres encontrados=%d | aguardando_prazo(API)=%d | gigs_1_xs1=%d | sem_status=%d",
        tag,
        len(processos),
        len(para_aguardando_prazo),
        len(para_gigs_xs1),
        len(sem_status),
    )

    for proc in sem_status:
        logger.warning(
            "%s %s (id=%s): estado de 'Aguardando prazo' indisponível na consulta — pulando",
            tag,
            proc.numero_processo,
            proc.id_processo,
        )
        resumo["sem_status_transicao"].append(proc.numero_processo)

    for proc in para_aguardando_prazo:
        try:
            res_mov = client.transitar_tarefa_processo(
                proc.id_processo,
                proc.id_tarefa,
                NOME_TRANSICAO_AGUARDANDO_PRAZO,
                verificar_bloqueio=True,
            )
            if res_mov.get("ok"):
                logger.info(
                    "%s %s (id=%s) movido via API: %s → %s (%s)",
                    tag,
                    proc.numero_processo,
                    proc.id_processo,
                    proc.id_tarefa,
                    res_mov.get("id_tarefa_destino"),
                    res_mov.get("nome_tarefa_destino") or NOME_TRANSICAO_AGUARDANDO_PRAZO,
                )
                resumo["movidos_aguardando_prazo"].append(proc.numero_processo)
            else:
                logger.warning(
                    "%s %s (id=%s) falha ao mover para Aguardando prazo via API: %s",
                    tag,
                    proc.numero_processo,
                    proc.id_processo,
                    res_mov.get("motivo") or res_mov.get("error"),
                )
                resumo["falhas_movimento"].append(
                    {"numero": proc.numero_processo, "id": proc.id_processo, "motivo": res_mov.get("motivo")}
                )
        except Exception as exc:
            logger.error("%s %s (id=%s) exceção ao mover via API: %s", tag, proc.numero_processo, proc.id_processo, exc)
            resumo["falhas_movimento"].append(
                {"numero": proc.numero_processo, "id": proc.id_processo, "motivo": str(exc)}
            )

    for proc in para_gigs_xs1:
        ok_gigs = _criar_gigs_1_xs1_no_processo(driver, proc.id_processo, proc.numero_processo, tag)
        if ok_gigs:
            resumo["gigs_xs1_criadas"].append(proc.numero_processo)
        else:
            resumo["falhas_gigs"].append({"numero": proc.numero_processo, "id": proc.id_processo})

    logger.info(
        "%s Concluído | movidos_api=%d | gigs_1_xs1=%d | falhas_mov=%d | falhas_gigs=%d",
        tag,
        len(resumo["movidos_aguardando_prazo"]),
        len(resumo["gigs_xs1_criadas"]),
        len(resumo["falhas_movimento"]),
        len(resumo["falhas_gigs"]),
    )
    return resumo


def _criar_gigs_xs1_em_lote_api(
    client,
    processos: Sequence[Any],
    *,
    dias: int = -1,
    observacao: str = "xs1",
    cache_prazo: Optional[Dict[Any, str]] = None,
    tag: str = "[PRAZO]",
) -> Dict[str, Any]:
    """Cria atividade GIGS (`-1//xs1` por padrão) via API para cada processo informado."""
    criadas: List[str] = []
    falhas: List[Dict[str, Any]] = []
    if cache_prazo is None:
        cache_prazo = {}

    for proc in processos:
        try:
            res = client.criar_atividade_gigs_api(
                proc.id_processo,
                observacao,
                dias=dias,
                id_oj=getattr(proc, "id_orgao_julgador", None),
                data_prazo_cache=cache_prazo,
            )
            if res.get("ok"):
                criadas.append(proc.numero_processo)
                logger.info(
                    "%s %s (id=%s): GIGS %s//%s criada via API (id=%s, prazo=%s)",
                    tag,
                    proc.numero_processo,
                    proc.id_processo,
                    dias,
                    observacao,
                    res.get("id"),
                    res.get("dataPrazo"),
                )
            else:
                motivo = res.get("motivo") or res.get("error") or res.get("status")
                logger.warning(
                    "%s %s (id=%s): falha ao criar GIGS %s//%s via API: %s",
                    tag,
                    proc.numero_processo,
                    proc.id_processo,
                    dias,
                    observacao,
                    motivo,
                )
                falhas.append({"numero": proc.numero_processo, "id": proc.id_processo, "motivo": motivo})
        except PermissionError:
            raise
        except Exception as exc:
            logger.error("%s %s (id=%s): exceção ao criar GIGS via API: %s", tag, proc.numero_processo, proc.id_processo, exc)
            falhas.append({"numero": proc.numero_processo, "id": proc.id_processo, "motivo": str(exc)})

    return {"criadas": criadas, "falhas": falhas}


def _movimentar_processos_api(
    client,
    processos: Sequence[Any],
    nome_destino: str,
    *,
    usar_endpoint_lote: bool = True,
    tag: str = "[PRAZO]",
) -> Dict[str, Any]:
    """Movimenta uma lista de processos via API para `nome_destino`.

    Usa `POST /tarefas/{tid}/movimentacoes` (endpoint nativo da movimentação em lote do PJe)
    com fallback automático para `transitar_tarefa_processo` caso o cliente não exponha o método.
    """
    movidos: List[str] = []
    bloqueados: List[str] = []
    falhas: List[Dict[str, Any]] = []
    tem_mov_lote = usar_endpoint_lote and hasattr(client, "movimentar_tarefa_lote_api")

    for proc in processos:
        pid = proc.id_processo if hasattr(proc, "id_processo") else int(proc["id"])
        tid = proc.id_tarefa if hasattr(proc, "id_tarefa") else int(proc.get("idTarefa") or 0)
        num = proc.numero_processo if hasattr(proc, "numero_processo") else str(proc.get("numeroProcesso") or pid)
        if not tid:
            falhas.append({"numero": num, "id": pid, "motivo": "id_tarefa_ausente"})
            continue
        try:
            if tem_mov_lote:
                res = client.movimentar_tarefa_lote_api(pid, tid, nome_destino)
            else:
                res = client.transitar_tarefa_processo(
                    pid, tid, nome_destino, verificar_bloqueio=True,
                )
            if res.get("ok"):
                movidos.append(num)
                logger.info(
                    "%s %s (id=%s) movido via API: %s → %s (%s)",
                    tag, num, pid, tid, res.get("id_tarefa_destino"),
                    res.get("nome_tarefa_destino") or nome_destino,
                )
            elif res.get("motivo") == "bloqueado_outro_usuario":
                bloqueados.append(num)
                logger.warning("%s %s (id=%s) bloqueado por outro usuário — pulado", tag, num, pid)
            else:
                motivo = res.get("motivo") or res.get("error") or res.get("status")
                logger.warning("%s %s (id=%s) falha ao mover para '%s': %s", tag, num, pid, nome_destino, motivo)
                falhas.append({"numero": num, "id": pid, "motivo": motivo})
        except PermissionError:
            raise
        except Exception as exc:
            logger.error("%s %s (id=%s) exceção ao mover para '%s': %s", tag, num, pid, nome_destino, exc)
            falhas.append({"numero": num, "id": pid, "motivo": str(exc)})

    return {"movidos": movidos, "bloqueados": bloqueados, "falhas": falhas}


def ciclo1_vencidos_para_analise_api(client, *, tag: str = "[PRAZO][1_VENCIDOS_API]") -> Dict[str, Any]:
    """Etapa 1 (API): Prazos Vencidos (Liq/Exec) → movimenta todos para Análise."""
    from api.filtro_analise import (
        FASES_LIQUIDACAO_EXECUCAO,
        ID_AGRUPAMENTO_PRAZOS_VENCIDOS,
        NOME_TRANSICAO_ANALISE,
    )

    processos = client.listar_agrupamento_processos(
        ID_AGRUPAMENTO_PRAZOS_VENCIDOS,
        fases=list(FASES_LIQUIDACAO_EXECUCAO),
    )
    logger.info("%s Encontrados %d processo(s) em Prazos Vencidos (Liq/Exec)", tag, len(processos))
    if not processos:
        return {"ok": True, "total": 0, "movidos": [], "bloqueados": [], "falhas": []}

    res_mov = _movimentar_processos_api(client, processos, NOME_TRANSICAO_ANALISE, tag=tag)
    logger.info(
        "%s Concluído | total=%d movidos=%d bloqueados=%d falhas=%d",
        tag, len(processos), len(res_mov["movidos"]), len(res_mov["bloqueados"]), len(res_mov["falhas"]),
    )
    return {"ok": True, "total": len(processos), **res_mov}


def ciclo2_3_analise_api(
    client,
    *,
    ids_escaninho_cache: Optional[set] = None,
    cache_prazo: Optional[Dict[Any, str]] = None,
    tag_mov: str = "[PRAZO][2_ANALISE_MOV_API]",
    tag_liv: str = "[PRAZO][3_ANALISE_LIVRES_API]",
) -> Dict[str, Any]:
    """Etapas 2 e 3 (API) em Análise (Liq/Exec, tarefa 500):
    - Etapa 2: não-livres (com GIGS/comentário/responsável) → Cumprimento de providências.
    - Etapa 3: livres com 'Aguardando prazo' disponível → Aguardando prazo;
               livres com 'Aguardando prazo' indisponível → GIGS `-1//xs1` via API.
    """
    from api.filtro_analise import (
        FASES_LIQUIDACAO_EXECUCAO,
        ID_AGRUPAMENTO_ANALISE,
        ID_TAREFA_ANALISE,
        NOME_TAREFA_ANALISE,
        NOME_TRANSICAO_AGUARDANDO_PRAZO,
        NOME_TRANSICAO_CUMPRIMENTO,
        classificar_processos_agrupamento,
    )

    classif = classificar_processos_agrupamento(
        client,
        ID_AGRUPAMENTO_ANALISE,
        fases=FASES_LIQUIDACAO_EXECUCAO,
        id_tarefa=ID_TAREFA_ANALISE,
        nome_tarefa=NOME_TAREFA_ANALISE,
        confirmar_gigs_individual=True,
        consultar_escaninho=True,
        ids_escaninho_cache=ids_escaninho_cache,
        verificar_aguardando_prazo_nos_livres=True,
        excetuar_apenas_xs1=True,
    )
    nao_livres = classif["nao_livres"]
    apenas_xs1 = classif.get("apenas_xs1") or []
    livres = classif["livres"]
    ids_escaninho = classif["ids_escaninho"]

    logger.info(
        "%s Não-livres para Cumprimento de providências: %d (apenas_xs1 excetuados=%d | doc_nao_apreciado preservados=%d)",
        tag_mov, len(nao_livres), len(apenas_xs1), len(classif["com_doc_nao_apreciado"]),
    )
    res_nao_livres = (
        _movimentar_processos_api(client, nao_livres, NOME_TRANSICAO_CUMPRIMENTO, tag=tag_mov)
        if nao_livres
        else {"movidos": [], "bloqueados": [], "falhas": []}
    )

    para_ag_prazo = [p for p in livres if p.aguardando_prazo_disponivel is True]
    para_xs1 = [p for p in livres if p.aguardando_prazo_disponivel is False]
    sem_status = [p for p in livres if p.aguardando_prazo_disponivel is None]

    logger.info(
        "%s Livres=%d | aguardando_prazo=%d | xs1_api=%d | sem_status=%d",
        tag_liv, len(livres), len(para_ag_prazo), len(para_xs1), len(sem_status),
    )
    res_ag_prazo = (
        _movimentar_processos_api(client, para_ag_prazo, NOME_TRANSICAO_AGUARDANDO_PRAZO, tag=tag_liv)
        if para_ag_prazo
        else {"movidos": [], "bloqueados": [], "falhas": []}
    )
    res_xs1 = (
        _criar_gigs_xs1_em_lote_api(client, para_xs1, dias=-1, observacao="xs1", cache_prazo=cache_prazo, tag=tag_liv)
        if para_xs1
        else {"criadas": [], "falhas": []}
    )

    return {
        "ok": True,
        "ids_escaninho": ids_escaninho,
        "diagnostico": classif["diagnostico"],
        "nao_livres": {"total": len(nao_livres), **res_nao_livres},
        "livres": {
            "total": len(livres),
            "movidos_aguardando_prazo": res_ag_prazo["movidos"],
            "falhas_movimento": res_ag_prazo["falhas"],
            "gigs_xs1_criadas": res_xs1["criadas"],
            "falhas_gigs": res_xs1["falhas"],
            "sem_status": [p.numero_processo for p in sem_status],
        },
    }


def ciclo4_cumprimento_livres_api(
    client,
    *,
    ids_escaninho_cache: Optional[set] = None,
    cache_prazo: Optional[Dict[Any, str]] = None,
    tag: str = "[PRAZO][4_CUMPRIMENTO_API]",
) -> Dict[str, Any]:
    """Etapa 4 (API): Cumprimento de Providências (agrupamento 6, todas as fases) livres → GIGS `-1//xs1`."""
    from api.filtro_analise import (
        ID_AGRUPAMENTO_CUMPRIMENTO,
        classificar_processos_agrupamento,
    )

    classif = classificar_processos_agrupamento(
        client,
        ID_AGRUPAMENTO_CUMPRIMENTO,
        fases=None,
        id_tarefa=None,
        confirmar_gigs_individual=True,
        consultar_escaninho=True,
        ids_escaninho_cache=ids_escaninho_cache,
        verificar_aguardando_prazo_nos_livres=False,
    )
    livres = classif["livres"]
    logger.info(
        "%s Total=%d | livres=%d | nao_livres=%d | doc_nao_apreciado=%d",
        tag,
        classif["diagnostico"]["total"],
        len(livres),
        len(classif["nao_livres"]),
        len(classif["com_doc_nao_apreciado"]),
    )
    res_xs1 = (
        _criar_gigs_xs1_em_lote_api(client, livres, dias=-1, observacao="xs1", cache_prazo=cache_prazo, tag=tag)
        if livres
        else {"criadas": [], "falhas": []}
    )
    return {
        "ok": True,
        "diagnostico": classif["diagnostico"],
        "total_livres": len(livres),
        "gigs_xs1_criadas": res_xs1["criadas"],
        "falhas_gigs": res_xs1["falhas"],
    }


def loop_prazo(driver) -> ResultadoExecucao:
    """Executa o fluxo Prazo completo em 4 etapas 100% via API REST antes do P2B:
    1. Prazos Vencidos (Liq/Exec) → Análise
    2. Análise (Liq/Exec) não-livres → Cumprimento de providências
    3. Análise (Liq/Exec) livres → Aguardando prazo (se disponível) ou GIGS `-1//xs1`
    4. Cumprimento de providências livres → GIGS `-1//xs1`
    """
    from Fix.variaveis import cliente_para

    logger.info(
        "[PRAZO] Iniciando fluxo 100%% API (1:Vencidos→Análise | 2:Análise não-livres→Cumprimento | "
        "3:Análise livres→Ag.Prazo/xs1 | 4:Cumprimento livres→xs1)"
    )
    try:
        client = cliente_para(driver)
        cache_prazo: Dict[Any, str] = {}

        res1 = ciclo1_vencidos_para_analise_api(client)
        res23 = ciclo2_3_analise_api(client, cache_prazo=cache_prazo)
        res4 = ciclo4_cumprimento_livres_api(
            client,
            ids_escaninho_cache=res23.get("ids_escaninho"),
            cache_prazo=cache_prazo,
        )

        logger.info(
            "[PRAZO] Concluído (API) | vencidos→analise=%d | analise→cumprimento=%d | "
            "analise→ag_prazo=%d | analise_xs1=%d | cumprimento_xs1=%d",
            len(res1["movidos"]),
            len(res23["nao_livres"]["movidos"]),
            len(res23["livres"]["movidos_aguardando_prazo"]),
            len(res23["livres"]["gigs_xs1_criadas"]),
            len(res4["gigs_xs1_criadas"]),
        )
        return ResultadoExecucao(
            sucesso=True,
            status="OK",
            detalhes={
                "prazos_vencidos": res1,
                "analise_nao_livres": res23["nao_livres"],
                "analise_livres": res23["livres"],
                "cumprimento_providencias": res4,
                "ciclo0": True,
                "ciclo3": True,
            },
        )
    except Exception as exc:
        logger.error("[PRAZO] Erro crítico no fluxo Prazo (API): %s", exc)
        return ResultadoExecucao(
            sucesso=False,
            status="ERRO",
            erro=str(exc),
            detalhes={"erro": str(exc)},
        )
