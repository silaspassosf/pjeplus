from Fix.utils_tempo import medir_tempo
"""
judicial_fluxo.py - Fluxos principais de atos judiciais
======================================================

Módulo principal com os fluxos de alto nível para atos judiciais,
usando os módulos especializados para navegação, conclusão, modelos,
prazos e bloqueios.
"""

from Fix.core import (
    aguardar_e_clicar, safe_click_no_scroll, safe_click,
    esperar_elemento, wait_for_clickable, esperar_url_conter,
    preencher_multiplos_campos, aguardar_renderizacao_nativa,
    preencher_campo,
)
from Fix.log import getmodulelogger, log_start, log_fim
logger = getmodulelogger(__name__)
from Fix.selectors_pje import BTN_TAREFA_PROCESSO, BTN_GRAVAR_MOVIMENTOS, EDITOR_AREA_CONTEUDO
from Play.pjeplay.locators import By
from Fix.utils import executar_coleta_parametrizavel, inserir_link_ato_validacao
from Fix.extracao import bndt, criar_gigs
from Fix.movimento_helpers import selecionar_movimento_auto
import json
import time
import logging

from typing import Optional, Tuple, Dict, List, Union, Callable, Any
from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario
from .core import verificar_carregamento_pagina, aguardar_e_verificar_aba

from .judicial_navegacao import (
    abrir_tarefa_processo,
    limpar_overlays,
    navegar_para_conclusao,
    escolher_tipo_conclusao,
    aguardar_transicao_minutar,
    preparar_campo_minutar,
    verificar_estado_atual,
    focar_campo_minutar_se_necessario,
)
from .judicial_modelos import inserir_modelo_no_editor
from .judicial_utils import (
    preencher_prazos_destinatarios,
    verificar_bloqueio_recente
)
from Fix import espera


@medir_tempo('fluxo_cls')
def fluxo_cls(
    driver: Any,
    conclusao_tipo: str,
    forcar_iniciar_execucao: bool = False
) -> bool:
    """Fluxo principal para CLS (Conclusão ao Magistrado → Minutar)."""
    log_start('CLS')
    timing_inicio = time.time()
    logger.info('[CLS][TIMING][INICIO]')

    try:
        logger.info('FLUXO CLS - INICIANDO')
        logger.info('=' * 60)

        timing_check_estado = time.time()
        estado_atual = verificar_estado_atual(driver)

        timing_check_estado = time.time() - timing_check_estado
        logger.info(f'[CLS][TIMING][CHECK_ESTADO] {timing_check_estado:.3f}s estado={estado_atual}')

        if estado_atual == 'assinar':
            logger.info('[CLS]  Processo já está em /assinar - ato cumprido')
            timing_total = time.time() - timing_inicio
            logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (estado pré-assinar)')
            return True, True
        elif estado_atual == 'minutar':
            logger.info('[CLS] Processo já em /minutar — seguindo para as ações de minuta')
            timing_total = time.time() - timing_inicio
            logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (já em /minutar)')
            return True, False
        elif estado_atual == 'conclusao':
            logger.info('[CLS] Já estamos em /conclusao - pulando navegação')
            ja_em_conclusao = True
        else:
            ja_em_conclusao = False

        if not ja_em_conclusao:
            nome_cls = (getattr(driver, 'pje_tarefa_atual', '') or '').strip()
            if not nome_cls:
                try:
                    h1 = espera.elementos(
                        driver,
                        "pje-cabecalho-tarefa h1.titulo-tarefa, pje-cabecalho-tarefa h1",
                        teto=2,
                    )
                    if h1:
                        nome_cls = (getattr(h1[0], 'text', '') or '').strip()
                except Exception:
                    pass
            if getattr(driver, 'pje_tarefa_pronta', None) == 'elaborar' or 'elaborar' in nome_cls.lower():
                logger.info('[CLS] Tarefa de elaboração — processo encerrado, seguindo para o próximo')
                timing_total = time.time() - timing_inicio
                logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (tarefa de elaboração)')
                return True, True

        ja_em_minutar = False
        if not ja_em_conclusao:
            # Usa estado_atual para evitar dupla leitura de URL
            if estado_atual == 'detalhe':
                logger.info('[CLS] Passo 1: Estamos em /detalhe — abrindo tarefa do processo...')
                timing_tarefa_inicio = time.time()
                sucesso, ja_em_minutar = abrir_tarefa_processo(driver)
                timing_tarefa = time.time() - timing_tarefa_inicio
                logger.info(f'[CLS][TIMING][ABRIR_TAREFA] {timing_tarefa:.3f}s sucesso={sucesso}')

                if not sucesso:
                    logger.error('[CLS] Falha ao abrir tarefa do processo')
                    timing_total = time.time() - timing_inicio
                    logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha ao abrir tarefa')
                    return False, False

                if getattr(driver, 'pje_tarefa_pronta', None) == 'assinar':
                    logger.info('[CLS] Tarefa de assinatura — ato já cumprido, encerrando CLS')
                    timing_total = time.time() - timing_inicio
                    logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (ato já assinado)')
                    return True, True

                if getattr(driver, 'pje_tarefa_pronta', None) == 'elaborar':
                    logger.info('[CLS] Tarefa de elaboração — seguindo sem abrir a minuta')
                    timing_total = time.time() - timing_inicio
                    logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (tarefa de elaboração)')
                    return True, True

                if ja_em_minutar:
                    current_after = (driver.current_url or '').lower()
                    if '/assinar' in current_after:
                        logger.info('[CLS] Já em /assinar após abrir tarefa - ato cumprido')
                        timing_total = time.time() - timing_inicio
                        logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (estado pré-assinar)')
                        return True, True
                    elif '/minutar' in current_after:
                        logger.info('[CLS] Já em /minutar após abrir tarefa — seguindo para as ações de minuta')
                        timing_total = time.time() - timing_inicio
                        logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (já em /minutar após abrir tarefa)')
                        return True, False
                    else:
                        logger.warning(
                            '[CLS] Tarefa "%s" não abriu tela de ato (URL=%s) — abortando CLS',
                            getattr(driver, 'pje_tarefa_atual', ''), current_after)
                        timing_total = time.time() - timing_inicio
                        logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s tarefa não abriu')
                        return False, False

                current_after = (driver.current_url or '').lower()
                if '/conclusao' in current_after:
                    logger.info('[CLS] Nova aba já em /conclusao — pulando navegação inicial')
                    ja_em_conclusao = True
            else:
                logger.info('[CLS] Não estamos em /detalhe — assumindo que já estamos na aba da tarefa do processo')
                current_url = (driver.current_url or '').lower()
                if '/conclusao' in current_url:
                    ja_em_conclusao = True

        logger.info('[CLS] Passo 2: Limpando overlays...')
        timing_overlays_inicio = time.time()
        limpar_overlays(driver)
        timing_overlays = time.time() - timing_overlays_inicio
        logger.info(f'[CLS][TIMING][LIMPAR_OVERLAYS] {timing_overlays:.3f}s')

        if not ja_em_conclusao:
            logger.info('[CLS] Passo 3: Navegando para conclusão...')
            timing_nav_inicio = time.time()
            try:
                nav_ok = navegar_para_conclusao(driver)
                if not nav_ok:
                    logger.error('[CLS] Falha ao navegar para conclusão')
                    timing_total = time.time() - timing_inicio
                    logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha ao navegar conclusão')
                    return False, False
            except Exception as e:
                logger.error(f'[CLS][ERRO CRÍTICO] Exceção em navegar_para_conclusao: {e}')
                import traceback
                logger.error(traceback.format_exc())
                return False, False
            timing_nav = time.time() - timing_nav_inicio
            logger.info(f'[CLS][TIMING][NAVEGAR_CONCLUSAO] {timing_nav:.3f}s')

        logger.info(f'[CLS] Passo 4: Escolhendo tipo de conclusão: {conclusao_tipo}')
        timing_tipo_inicio = time.time()
        try:
            if not escolher_tipo_conclusao(driver, conclusao_tipo):
                logger.error(f'[CLS] Falha ao escolher tipo de conclusão: {conclusao_tipo}')
                timing_total = time.time() - timing_inicio
                logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha ao escolher tipo conclusão')
                return False, False
        except Exception as e:
            logger.error(f'[CLS][ERRO CRÍTICO] Exceção em escolher_tipo_conclusao: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return False, False
        timing_tipo = time.time() - timing_tipo_inicio
        logger.info(f'[CLS][TIMING][ESCOLHER_TIPO] {timing_tipo:.3f}s tipo={conclusao_tipo}')

        logger.info('[CLS] Passo 5: Aguardando transição para minutar...')
        timing_transicao_inicio = time.time()
        try:
            if not aguardar_transicao_minutar(driver):
                logger.error('[CLS] Falha na transição para minutar')
                timing_total = time.time() - timing_inicio
                logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha na transição minutar')
                return False, False
        except Exception as e:
            logger.error(f'[CLS][ERRO CRÍTICO] Exceção em aguardar_transicao_minutar: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return False, False
        timing_transicao = time.time() - timing_transicao_inicio
        logger.info(f'[CLS][TIMING][TRANSICAO_MINUTAR] {timing_transicao:.3f}s')

        logger.info('[CLS] Passo 6: Preparando campo de minutar...')
        timing_campo_inicio = time.time()
        try:
            if not preparar_campo_minutar(driver):
                logger.error('[CLS] Falha ao preparar campo de minutar')
                timing_total = time.time() - timing_inicio
                logger.info(f'[CLS][TIMING][ERRO] {timing_total:.3f}s falha ao preparar campo minutar')
                return False, False
        except Exception as e:
            logger.error(f'[CLS][ERRO CRÍTICO] Exceção em preparar_campo_minutar: {e}')
            import traceback
            logger.error(traceback.format_exc())
            return False
        timing_campo = time.time() - timing_campo_inicio
        logger.info(f'[CLS][TIMING][PREPARAR_CAMPO] {timing_campo:.3f}s')

        logger.info('=' * 60)
        logger.info('FLUXO CLS - CONCLUÍDO COM SUCESSO')
        logger.info('=' * 60)

        timing_total = time.time() - timing_inicio
        log_fim('CLS', {'status': 'sucesso', 'tempo': f'{timing_total:.3f}s'})
        logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (fluxo completo)')
        return True, False

    except Exception as e:
        timing_total = time.time() - timing_inicio
        log_fim('CLS', {'status': 'erro', 'motivo': str(e)[:80]})
        logger.error(f'[CLS][TIMING][ERRO] {timing_total:.3f}s erro inesperado: {e}')
        logger.error(f'[CLS] Erro inesperado no fluxo CLS: {e}')
        return False, False


# Candidatos em ordem de confiança. Todos foram provados localizando
# muda a ordem ou o conjunto de abas. Como os índices `mat-tab-*` são gerados
# pelo Angular, NENHUM candidato é usado sem confirmar o TEXTO do label — é
SELETORES_ABA_INTIMACOES = (
    'pje-editor-lateral div[role="tab"][aria-posinset="1"]',
    'pje-editor-lateral div[role="tab"][aria-controls="mat-tab-content-0-0"]',
    # 3-5: fallbacks estruturais do Angular Material.
    'pje-editor-lateral .mat-tab-label[aria-posinset="1"]',
    'pje-editor-lateral mat-tab-header div[role="tab"]:first-child',
    '#mat-tab-label-0-0',
    '//pje-editor-lateral//div[@role="tab"][contains(., "Intima")]',
)
TENTATIVAS_ABA_INTIMACOES = 3

# intimações precisa estar montado no MESMO `mat-tab-group`. O Angular mantém
_JS_ABA_INTIMACOES_ATIVA = """(() => {
    var l = document.querySelector(%s);
    if (!l) return false;
    if (!(l.classList.contains('mat-tab-label-active')
          || l.getAttribute('aria-selected') === 'true')) return false;
    var g = l.closest('mat-tab-group') || document;
    return !!g.querySelector(
        'pje-intimacao-automatica .controle-intimacao-pai');
}"""

_JS_TEXTO_ABA = """(() => {
    var l = document.querySelector(%s);
    return l ? (l.textContent || '') : '';
})()"""

_JS_ESTADO_ABA = """(() => {
    var sel = %s;
    var l = (sel.startsWith('//') || sel.startsWith('('))
        ? document.evaluate(sel, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
        : document.querySelector(sel);
    var g = l && (l.closest('mat-tab-group') || document);
    var ativa = g && g.querySelector(
        'div[role="tab"].mat-tab-label-active, div[role="tab"][aria-selected="true"]');
    return {
        existe: !!l,
        ativa: !!(l && (l.classList.contains('mat-tab-label-active')
                        || l.getAttribute('aria-selected') === 'true')),
        painel: !!(g && g.querySelector(
            'pje-intimacao-automatica .controle-intimacao-pai, pje-intimacao-automatica label.mat-slide-toggle-label')),
        ativa_texto: ativa
            ? (ativa.textContent || '').trim().replace(/\\s+/g, ' ').toLowerCase() : ''
    };
})()"""


def _is_xpath(seletor: str) -> bool:
    return seletor.startswith('//') or seletor.startswith('(')


def _texto_aba(driver: Any, seletor: str, elemento: Any = None) -> str:
    """Texto normalizado do label apontado por `seletor` ('' se não existir)."""
    bruto = ''
    if elemento is not None:
        try:
            bruto = getattr(elemento, 'text', '') or ''
        except Exception:
            bruto = ''
    if not bruto:
        try:
            if _is_xpath(seletor):
                if hasattr(driver, 'page'):
                    try:
                        xpath_js = (
                            "x => {" +
                            "var r = document.evaluate(x, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);"
                            "var n = r.singleNodeValue;"
                            "return n ? (n.textContent || '') : '';"
                            "}"
                        )
                        bruto = driver.page.evaluate(xpath_js, seletor) or ''
                    except Exception:
                        return ''
                return ''
            bruto = driver.page.evaluate(_JS_TEXTO_ABA % json.dumps(seletor)) or ''
        except Exception:
            return ''
    return ' '.join(str(bruto).split()).lower()


def _estado_aba(driver: Any, seletor: str, elemento: Any = None) -> dict:
    """Estado observável da aba: existe / ativa / painel montado / label ativo."""
    if hasattr(driver, 'page'):
        try:
            estado = driver.page.evaluate(_JS_ESTADO_ABA % json.dumps(seletor))
            if isinstance(estado, dict):
                return estado
        except Exception:
            pass
    ativa = False
    if elemento is not None:
        try:
            classe = elemento.get_attribute('class') or ''
            ativa = (elemento.get_attribute('aria-selected') == 'true'
                     or 'mat-tab-label-active' in classe)
        except Exception:
            ativa = False
    painel = False
    try:
        painel = bool(esperar_elemento(
            driver, 'pje-intimacao-automatica .controle-intimacao-pai', timeout=1))
    except Exception:
        painel = False
    return {'existe': elemento is not None, 'ativa': ativa,
            'painel': painel, 'ativa_texto': ''}


def _aba_intimacoes_ativa(driver: Any, seletor: str, teto: float = 2.0) -> bool:
    """True só com AQUELE label ativo E o painel montado no mesmo tab-group."""
    def _ok(_driver):
        estado = _estado_aba(_driver, seletor)
        return bool(estado.get('ativa') and estado.get('painel'))
    return bool(espera.ate(driver, _ok, teto=teto))


_JS_ARMAR_CLIQUE_ABA = """(sel) => {
    var l = (sel.startsWith('//') || sel.startsWith('('))
        ? document.evaluate(sel, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
        : document.querySelector(sel);
    if (!l) return false;
    window.__pjeCliqueAba = 0;
    l.addEventListener('click', function () { window.__pjeCliqueAba += 1; }, { once: true });
    return true;
}"""

_JS_LER_CLIQUE_ABA = """() => (window.__pjeCliqueAba || 0)"""


def _armar_clique_aba(driver: Any, seletor: str) -> bool:
    """Arma um contador de eventos de `click` no label antes do clique."""
    if not hasattr(driver, 'page'):
        return False
    try:
        return bool(driver.page.evaluate(_JS_ARMAR_CLIQUE_ABA, seletor))
    except Exception:
        return False


def _ler_clique_aba(driver: Any) -> int:
    """Eventos de clique vistos no label desde o armamento (-1 = sem medição)."""
    try:
        return int(driver.page.evaluate(_JS_LER_CLIQUE_ABA))
    except Exception:
        return -1


def _resolver_aba_intimacoes(driver: Any, tentativa: int):
    """Acha o 1º candidato cujo label seja realmente "Intimações"."""
    for idx, seletor in enumerate(SELETORES_ABA_INTIMACOES, 1):
        teto = 4 if idx == 1 else 2
        by = By.XPATH if seletor.startswith('//') else By.CSS_SELECTOR
        elemento = esperar_elemento(driver, seletor, timeout=teto, by=by)
        if elemento is None:
            logger.debug('[ATO][ABA] candidato %d/%d ausente: %s',
                         idx, len(SELETORES_ABA_INTIMACOES), seletor)
            continue
        texto = _texto_aba(driver, seletor, elemento)
        if 'intima' not in texto:
            logger.warning('[ATO][ABA] candidato %d/%d (%s) aponta para %r — ignorado',
                           idx, len(SELETORES_ABA_INTIMACOES), seletor, texto)
            continue
        logger.info('[ATO][ABA] candidato %d/%d (%s) resolvido para %r',
                    idx, len(SELETORES_ABA_INTIMACOES), seletor, texto)
        return seletor, elemento
    return None, None


def _dump_abas_intimacoes(driver: Any) -> None:
    """Diagnóstico: estado de cada candidato e de todas as abas da tela."""
    for idx, seletor in enumerate(SELETORES_ABA_INTIMACOES, 1):
        estado = _estado_aba(driver, seletor)
        logger.error('[ATO][ABA] candidato %d/%d %s -> texto=%r ativa=%s painel=%s',
                     idx, len(SELETORES_ABA_INTIMACOES), seletor,
                     _texto_aba(driver, seletor) or '<ausente>',
                     estado.get('ativa'), estado.get('painel'))
    try:
        if not hasattr(driver, 'page'):
            return
        abas = driver.page.evaluate("""() => Array.from(
            document.querySelectorAll('pje-editor-lateral div[role="tab"], pje-editor-lateral .mat-tab-label')
        ).map(t => ({
            texto: (t.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 30),
            id: t.id || null,
            pos: t.getAttribute('aria-posinset'),
            sel: t.getAttribute('aria-selected'),
            ativa: t.classList.contains('mat-tab-label-active')
        }))""")
        logger.error('[ATO][ABA] abas na tela: %s', abas)
    except Exception as e:
        logger.error('[ATO][ABA] não foi possível listar as abas: %s', e)


def _ativar_aba_intimacoes(driver: Any) -> bool:
    """Ativa a aba "Intimações" pelo clique, com retry, e confirma o painel."""
    for tentativa in range(1, TENTATIVAS_ABA_INTIMACOES + 1):
        seletor, aba = _resolver_aba_intimacoes(driver, tentativa)
        if aba is None:
            logger.warning('[ATO][ABA] tentativa %d/%d nenhum candidato apontou para '
                           '"Intimações"', tentativa, TENTATIVAS_ABA_INTIMACOES)
            espera.assentar(driver, 0.6, motivo='re-tentativa de localização da aba Intimações')
            continue

        antes = _estado_aba(driver, seletor, aba)
        if antes.get('ativa') and antes.get('painel'):
            logger.info('[ATO][ABA] tentativa %d/%d: aba JÁ estava ativa e com painel '
                        'ANTES do clique (ativo=%r) — atribuição não comprovável',
                        tentativa, TENTATIVAS_ABA_INTIMACOES,
                        antes.get('ativa_texto'))
        armado = _armar_clique_aba(driver, seletor)
        clicou = None
        try:
            clicou = safe_click_no_scroll(driver, aba)
            logger.info('[ATO][ABA] tentativa %d/%d — clique na aba "Intimações" via %s '
                        '(ativo antes=%r)', tentativa, TENTATIVAS_ABA_INTIMACOES,
                        seletor, antes.get('ativa_texto'))
        except Exception as e:
            logger.warning('[ATO][ABA] tentativa %d/%d falha ao clicar via %s: %s',
                           tentativa, TENTATIVAS_ABA_INTIMACOES, seletor, e)

        if armado:
            recebidos = _ler_clique_aba(driver)
            if recebidos == 0:
                logger.warning('[ATO][ABA] tentativa %d/%d: clique NÃO alcançou a aba '
                               '(0 eventos no label) — painel alheio não conta',
                               tentativa, TENTATIVAS_ABA_INTIMACOES)
                if tentativa < TENTATIVAS_ABA_INTIMACOES:
                    espera.assentar(driver, 0.6, motivo='re-tentativa: clique não alcançou a aba')
                    continue
            elif recebidos > 1:
                logger.info('[ATO][ABA] tentativa %d/%d: %d cliques no label no intervalo '
                            '(houve clique externo)', tentativa,
                            TENTATIVAS_ABA_INTIMACOES, recebidos)
        elif clicou is False:
            logger.warning('[ATO][ABA] tentativa %d/%d: safe_click falhou para %s',
                           tentativa, TENTATIVAS_ABA_INTIMACOES, seletor)

        # Dá tempo do Angular montar o painel de intimações após o clique.
        espera.assentar(driver, 0.8, motivo='pós-clique da aba Intimações')
        if _aba_intimacoes_ativa(driver, seletor, teto=3.0):
            depois = _estado_aba(driver, seletor, aba)
            if not (antes.get('ativa') and antes.get('painel')):
                logger.info('[ATO][ABA] ✅ transição observada pelo clique → aba '
                            '"Intimações" ativa e painel montado '
                            '(tentativa %d, seletor %s)', tentativa, seletor)
            else:
                logger.info('[ATO][ABA] ✅ aba "Intimações" ativa e painel montado '
                            '(sem transição: já estava antes; ativo depois=%r)',
                            depois.get('ativa_texto'))
            return True
        depois = _estado_aba(driver, seletor, aba)
        logger.warning('[ATO][ABA] tentativa %d/%d sem confirmação — antes(ativa=%s, '
                       'painel=%s) depois(ativa=%s, painel=%s)',
                       tentativa, TENTATIVAS_ABA_INTIMACOES,
                       antes.get('ativa'), antes.get('painel'),
                       depois.get('ativa'), depois.get('painel'))
    return False


def ato_judicial(
    driver: Any,
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
    **kwargs: Any
) -> Tuple[bool, bool]:
    """Fluxo generalizado para qualquer ato judicial, seguindo a ordem:"""
    import time
    atribuir_visibilidade_autor = False
    try:
        atribuir_visibilidade_autor = bool(kwargs.pop('atribuir_visibilidade_autor', False))
    except Exception:
        atribuir_visibilidade_autor = False

    log_start('ATO')
    timing_inicio = time.time()
    logger.info('[ATO][TIMING][INICIO] conclusao_tipo={} modelo_nome={}'.format(conclusao_tipo, modelo_nome))

    try:
        # página viva do PJe. Sem isso, um driver em branco (ex.: aba fechada depois da
        try:
            _url_ato = (getattr(driver, 'current_url', '') or '')
        except Exception:
            _url_ato = ''
        if not ('pje' in _url_ato and 'jus.br' in _url_ato):
            logger.error('[ATO][ERRO] Página atual não é do PJe (%r) — ato não executado',
                         _url_ato or 'sem URL')
            return False, False

        if coleta_conteudo:
            logger.info('[ATO][COLETA] Executando coleta de conteúdo parametrizável ANTES do fluxo principal...')
            try:
                sucesso_coleta = coleta_conteudo(driver)
                if not sucesso_coleta:
                    logger.warning('[ATO][COLETA] Coleta retornou False — prosseguindo mesmo assim')
                else:
                    logger.info('[ATO][COLETA] Coleta executada com sucesso!')
            except Exception as e:
                logger.error(f'[ATO][COLETA] Erro na coleta de conteúdo: {e} — prosseguindo')

        if modelo_nome:
            logger.info(f'[ATO] Executando fluxo CLS com modelo: {modelo_nome}')

            if not conclusao_tipo:
                logger.error('[ATO] conclusao_tipo é obrigatório quando modelo_nome é fornecido!')
                return False, False

            res_cls = fluxo_cls(driver, conclusao_tipo, forcar_iniciar_execucao=True)
            if isinstance(res_cls, tuple):
                sucesso_cls, ja_estava_final = res_cls
            else:
                sucesso_cls = bool(res_cls)
                ja_estava_final = False

            if not sucesso_cls:
                logger.error('[ATO] Falha no fluxo CLS')
                return False, False

            if ja_estava_final:
                logger.info('[ATO] Processo já estava em estado final — ato cumprido sem nova minuta')
                return True, False

            # esperar a estrutura existir evita descricao e modelo perdidos por pagina
            from Fix.seletores_catalogo import SEL_EDITOR_FALLBACKS
            espera.ate_aparecer(
                driver,
                f'input#inputFiltro, pje-arvore-modelo-documento, {SEL_EDITOR_FALLBACKS}',
                teto=20,
            )

            if descricao:
                logger.info(f'[ATO][DESCRICAO] Preenchendo descrição: {descricao}')
                try:
                    campo_descricao = esperar_elemento(driver, 'input[aria-label="Descrição"]', timeout=10)
                    if campo_descricao:
                        preencher_campo(driver, 'input[aria-label="Descrição"]', descricao)
                        logger.info('[ATO][DESCRICAO]  Descrição preenchida')
                    else:
                        raise Exception('Campo descrição não encontrado')
                except Exception as e:
                    logger.error(f'[ATO][DESCRICAO]  Erro ao preencher descrição: {e}')

            espera.ate_aparecer(driver, SEL_EDITOR_FALLBACKS, teto=10)
            logger.info(f'[ATO][MODELO] Inserindo modelo "{modelo_nome}"...')
            if not inserir_modelo_no_editor(driver, modelo_nome, log=logger.info):
                logger.error('[ATO][MODELO] Modelo não confirmado no editor-alvo — abortando antes do Salvar')
                return False, False
            espera.assentar(driver, 1.0, motivo='paciência pós-inserção do modelo')

        if inserir_conteudo:
            logger.info('[ATO][INSERIR] Executando inserção de conteúdo...')
            try:
                inserir_conteudo(driver)
                logger.info('[ATO][INSERIR]  Conteúdo inserido')
            except Exception as e:
                logger.error(f'[ATO][INSERIR]  Erro ao inserir conteúdo: {e}')
                return False, False

        logger.info('[ATO][SALVAR] Salvando minuta após inserção...')
        try:
            seletor_btn_salvar = 'button[aria-label="Salvar"]'
            btn_salvar = wait_for_clickable(driver, seletor_btn_salvar, timeout=15)
            if not btn_salvar:
                btn_salvar = wait_for_clickable(
                    driver,
                    '//button[contains(@class, "mat-raised-button") and contains(., "Salvar")]',
                    timeout=5,
                    by=By.XPATH
                )
            if not btn_salvar:
                raise Exception('Botão Salvar não disponível')

            safe_click(driver, btn_salvar)
            logger.info('[ATO][SALVAR] Clique no botão Salvar realizado')

            espera.ate_sumir(driver, 'mat-progress-bar, mat-progress-spinner, .mat-progress-spinner, .mat-progress-bar', teto=15)

            js_snack_salvo = """() => {
                var snacks = Array.from(document.querySelectorAll('simple-snack-bar, snack-bar-container'));
                for (var s of snacks) {
                    var txt = (s.innerText || '').toLowerCase();
                    if (txt.includes('minuta salva') || txt.includes('minuta foi salva')) {
                        var btn = s.querySelector('button');
                        if (btn) btn.click();
                        return true;
                    }
                }
                return false;
            }"""
            salvou = bool(espera.ate_js(driver, f"({js_snack_salvo})()", teto=4))

            # Salvar; sem isso o painel de destinatários/prazo não renderiza e
            aba_ok = _ativar_aba_intimacoes(driver)

            if not aba_ok:
                logger.warning('[ATO][ABA] Painel de intimações NÃO confirmado pelo clique — '
                               'verificando controles de destinatários')

            if not salvou:
                salvou = bool(espera.ate_js(driver, f"({js_snack_salvo})()", teto=2))
            if not salvou:
                salvou = bool(aguardar_renderizacao_nativa(
                    driver,
                    'pje-intimacao-automatica label.mat-slide-toggle-label, '
                    'button[aria-label="Gravar a intimação/notificação"], '
                    'mat-checkbox[aria-label="Enviar para PEC"], '
                    'button#selecionar-polo-ativo',
                    modo='aparecer',
                    timeout=15,
                ))

            if not salvou and not aba_ok:
                logger.error('[ATO][SALVAR] Sem confirmação positiva de salvamento (nem snackbar nem aba de destinatários) — abortando')
                return False, False

            aguardar_renderizacao_nativa(
                driver,
                'button[aria-label="Gravar a intimação/notificação"], '
                'pje-intimacao-automatica label.mat-slide-toggle-label, '
                'mat-checkbox[aria-label="Enviar para PEC"], '
                'div.checkbox-pec mat-checkbox, '
                'table.t-class tr.ng-star-inserted, '
                'button#selecionar-polo-ativo',
                modo='aparecer',
                timeout=15,
            )

            espera.assentar(driver, 1.0, motivo='estabilização pós-salvamento da minuta')
            logger.info('[ATO][SALVAR] Minuta salva e aba destinatários pronta')

        except Exception as e:
            logger.error(f'[ATO][SALVAR] Erro ao salvar minuta: {e}')
            return False, False

        sigilo_ativado = False

        intimar_ativado = True if intimar is None else str(intimar).lower() in ("sim", "true", "1")

        # ----- 1. SIGILO (primeiro de tudo, logo após a aba renderizar) -----
        if sigilo:
            logger.info('[ATO][SIGILO] Aplicando sigilo...')
            sigilo_ativado = True
            try:
                slide = esperar_elemento(
                    driver,
                    'mat-slide-toggle[name="sigiloso"], mat-slide-toggle#sigilo, mat-slide-toggle:has-text("Sigiloso"), label.mat-slide-toggle-label',
                    timeout=5
                )
                if slide:
                    input_sig = espera.elemento(driver, 'mat-slide-toggle[name="sigiloso"] input[type="checkbox"], mat-slide-toggle#sigilo input[type="checkbox"], input[name="sigiloso"]', teto=1)

                    is_checked = False
                    try:
                        if input_sig:
                            is_checked = (
                                input_sig.get_attribute('aria-checked') == 'true'
                                or getattr(input_sig, 'is_selected', lambda: False)()
                            )
                        else:
                            cls = slide.get_attribute('class') or ''
                            is_checked = 'mat-checked' in cls
                    except Exception:
                        is_checked = False

                    if not is_checked:
                        label = espera.elemento(driver, 'mat-slide-toggle[name="sigiloso"] label.mat-slide-toggle-label, mat-slide-toggle#sigilo label.mat-slide-toggle-label', teto=1)
                        if label:
                            safe_click_no_scroll(driver, label, log=False)
                        elif input_sig:
                            safe_click_no_scroll(driver, input_sig)
                        else:
                            safe_click_no_scroll(driver, slide)

                    logger.info('[ATO][SIGILO] Sigilo ativado')
                else:
                    logger.debug('[ATO][SIGILO] Toggle de sigilo não encontrado (mantendo flag ativa)')
            except Exception as e:
                logger.debug(f'[ATO][SIGILO] Erro ao aplicar sigilo: {e}')

        if intimar_ativado:
            try:
                toggle_intimar = esperar_elemento(driver, 'pje-intimacao-automatica label.mat-slide-toggle-label', timeout=2)
                if not toggle_intimar:
                    _ativar_aba_intimacoes(driver)
                    toggle_intimar = esperar_elemento(driver, 'pje-intimacao-automatica label.mat-slide-toggle-label', timeout=5)
                if toggle_intimar:
                    is_mat_checked = False
                    if hasattr(toggle_intimar, '_js'):
                        is_mat_checked = bool(toggle_intimar._js("el => el.parentElement && el.parentElement.classList.contains('mat-checked')"))
                    elif hasattr(driver, 'page'):
                        is_mat_checked = bool(driver.page.evaluate("""() => {
                            var el = document.querySelector('pje-intimacao-automatica label.mat-slide-toggle-label');
                            return el && el.parentElement && el.parentElement.classList.contains('mat-checked');
                        }"""))
                    if not is_mat_checked:
                        safe_click_no_scroll(driver, toggle_intimar)
                        espera.assentar(driver, 0.5)
                        logger.info('[ATO][INTIMAR] Toggle "Intimar?" ativado')
            except Exception as e:
                logger.debug(f'[ATO][INTIMAR] Erro ao assegurar guia/toggle de intimações: {e}')
        else:
            logger.info('[ATO][INTIMAR] Desativando intimações automáticas...')
            try:
                toggle_intimar = esperar_elemento(driver, 'pje-intimacao-automatica label.mat-slide-toggle-label', timeout=2)
                if not toggle_intimar:
                    _ativar_aba_intimacoes(driver)
                    toggle_intimar = esperar_elemento(driver, 'pje-intimacao-automatica label.mat-slide-toggle-label', timeout=8)
                if toggle_intimar:
                    is_mat_checked = False
                    if hasattr(toggle_intimar, '_js'):
                        is_mat_checked = bool(toggle_intimar._js("el => el.parentElement && el.parentElement.classList.contains('mat-checked')"))
                    elif hasattr(driver, 'page'):
                        is_mat_checked = bool(driver.page.evaluate("""() => {
                            var el = document.querySelector('pje-intimacao-automatica label.mat-slide-toggle-label');
                            return el && el.parentElement && el.parentElement.classList.contains('mat-checked');
                        }"""))
                    if is_mat_checked:
                        safe_click_no_scroll(driver, toggle_intimar)
                        espera.assentar(driver, 0.5)
                    logger.info('[ATO][INTIMAR] Toggle "Intimar?" desativado.')
                else:
                    logger.info('[ATO][INTIMAR] Toggle "Intimar?" já estava desativado.')
            except Exception as e:
                logger.error(f'[ATO][INTIMAR] Erro ao desativar intimações: {e}')

        # antes de prosseguir para Gravar/Movimento. Sem isso, o spinner fica
        # travado na tela porque o Angular ainda está processando a transição.
        if not intimar_ativado:
            logger.info('[ATO][INTIMAR] Aguardando estabilização da aba após desativar intimações...')
            try:
                espera.ate_sumir(driver, 'mat-progress-spinner, .mat-progress-spinner, mat-progress-bar, .mat-progress-bar', teto=8)
                # Pequena pausa extra para o Angular finalizar a renderização
                espera.assentar(driver, 1.5, motivo='estabilização pós-desativação de intimações')
            except Exception as e:
                logger.debug(f'[ATO][INTIMAR] Erro ao aguardar estabilização: {e}')

        if intimar_ativado and (prazo is not None or marcar_primeiro_destinatario):
            logger.info(f'[ATO][PRAZO] Configurando destinatários/prazos: prazo={prazo} (apenas_primeiro={marcar_primeiro_destinatario})')
            try:
                if not preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=marcar_primeiro_destinatario, perito=perito):
                    logger.error('[ATO][PRAZO] Falha ao preencher destinatários/prazos')
                    return False, False
                logger.info('[ATO][PRAZO] Destinatários e prazos concluídos com sucesso')
            except Exception as e:
                logger.error(f'[ATO][PRAZO] Erro ao preencher prazos: {e}')
                return False, False

        if marcar_pec is not None:
            marcar_pec_bool = str(marcar_pec).lower() in ("sim", "true", "1", "yes")
            logger.info(f'[ATO][PEC] Parâmetro marcar_pec={marcar_pec!r} (desejado: {"marcar" if marcar_pec_bool else "desmarcar"})')
            try:
                js_tratar_pec = """marcar => {
                    var el = document.querySelector(
                        'pje-intimacao-automatica mat-checkbox[aria-label="Enviar para PEC"], ' +
                        'mat-checkbox[aria-label="Enviar para PEC"], ' +
                        'pje-intimacao-automatica .checkbox-pec mat-checkbox, ' +
                        '.checkbox-pec mat-checkbox, ' +
                        'pje-intimacao-automatica label[class*="enviarPec"], ' +
                        'label.enviarPec'
                    );
                    if (!el) {
                        var inp = document.querySelector('input[aria-label="Enviar para PEC"], input[name="enviarPec"]');
                        if (inp) el = inp.closest('mat-checkbox') || inp.closest('label') || inp;
                    }
                    if (!el) return { sucesso: false, erro: 'Elemento PEC não encontrado' };

                    var matCheckbox = el.matches('mat-checkbox') ? el : el.closest('mat-checkbox');
                    var input = el.matches('input') ? el : (el.querySelector('input[type="checkbox"]') || (matCheckbox ? matCheckbox.querySelector('input[type="checkbox"]') : null));
                    
                    var isChecked = false;
                    if (matCheckbox) {
                        var cls = matCheckbox.getAttribute('class') || '';
                        isChecked = cls.indexOf('mat-checkbox-checked') !== -1 || cls.indexOf('mat-mdc-checkbox-checked') !== -1;
                    }
                    if (!isChecked && input) {
                        isChecked = !!(input.checked || input.getAttribute('aria-checked') === 'true');
                    }

                    var estadoInicial = isChecked;
                    if (isChecked !== marcar) {
                        var clickTarget = (matCheckbox && (matCheckbox.querySelector('label') || matCheckbox.querySelector('.mat-checkbox-inner-container'))) || el;
                        clickTarget.click();
                        return { sucesso: true, alterado: true, estadoInicial: estadoInicial };
                    }
                    return { sucesso: true, alterado: false, estadoInicial: estadoInicial };
                }"""

                res_pec = {}
                if hasattr(driver, 'page'):
                    res_pec = driver.page.evaluate(js_tratar_pec, marcar_pec_bool) or {}
                else:
                    res_pec = {'sucesso': True}

                if not res_pec.get('sucesso'):
                    logger.warning(f'[ATO][PEC] {res_pec.get("erro", "Elemento PEC não encontrado")}')
                else:
                    estado_ini = "marcado" if res_pec.get('estadoInicial') else "desmarcado"
                    alterado = res_pec.get('alterado')
                    if alterado:
                        espera.assentar(driver, 0.5)
                        js_recheca_pec = """() => {
                            var el = document.querySelector(
                                'pje-intimacao-automatica mat-checkbox[aria-label="Enviar para PEC"], ' +
                                'mat-checkbox[aria-label="Enviar para PEC"], ' +
                                'pje-intimacao-automatica .checkbox-pec mat-checkbox, ' +
                                '.checkbox-pec mat-checkbox'
                            );
                            if (el) {
                                var cls = el.getAttribute('class') || '';
                                if (cls.indexOf('mat-checkbox-checked') !== -1 || cls.indexOf('mat-mdc-checkbox-checked') !== -1) return true;
                            }
                            var inp = (el && el.querySelector('input[type="checkbox"]'))
                                || document.querySelector('input[aria-label="Enviar para PEC"], input[name="enviarPec"]');
                            return inp ? !!(inp.checked || inp.getAttribute('aria-checked') === 'true') : null;
                        }"""
                        novo_estado = None
                        if hasattr(driver, 'page'):
                            novo_estado = driver.page.evaluate(js_recheca_pec)
                        if novo_estado is not None and bool(novo_estado) != marcar_pec_bool:
                            # Fallback Playwright: em alguns formulários Angular o
                            el_pec = esperar_elemento(
                                driver,
                                'pje-intimacao-automatica mat-checkbox[aria-label="Enviar para PEC"], '
                                'mat-checkbox[aria-label="Enviar para PEC"], '
                                'pje-intimacao-automatica .checkbox-pec mat-checkbox, '
                                'input[name="enviarPec"]',
                                timeout=2,
                            )
                            if el_pec:
                                safe_click_no_scroll(driver, el_pec, log=False)
                                espera.assentar(driver, 0.4)
                                if hasattr(driver, 'page'):
                                    novo_estado = driver.page.evaluate(js_recheca_pec)
                        novo_estado_str = "marcado" if novo_estado else "desmarcado"
                        logger.info(f'[ATO][PEC] Estado inicial: {estado_ini} → alterado para: {novo_estado_str}')
                    else:
                        logger.info(f'[ATO][PEC] Já está conforme esperado: {estado_ini}')
            except Exception as e:
                logger.error(f'[ATO][PEC] Erro ao tratar PEC: {e}')

        logger.info('[ATO][GRAVAR] Gravando intimações...')
        try:
            if hasattr(driver, 'page'):
                try:
                    driver.page.evaluate("""() => {
                        document.querySelectorAll('.cdk-overlay-backdrop, snack-bar-container, simple-snack-bar').forEach(function(el){
                            if (el.style) el.style.display = 'none';
                        });
                    }""")
                except Exception:
                    pass

            btn_gravar_intim = None
            for sel in [
                'pje-intimacao-automatica button[aria-label*="Gravar"]',
                'button[aria-label="Gravar a intimação/notificação"]',
                'button[aria-label*="Gravar a intima"]',
                'pje-intimacao-automatica button.mat-raised-button.mat-primary'
            ]:
                btn_gravar_intim = wait_for_clickable(driver, sel, timeout=6)
                if btn_gravar_intim:
                    break

            if btn_gravar_intim:
                safe_click_no_scroll(driver, btn_gravar_intim, log=False)
                logger.info('[ATO][GRAVAR] Intimações gravadas')
                try:
                    aguardar_renderizacao_nativa(driver, 'simple-snack-bar', modo='aparecer', timeout=5)
                except Exception:
                    pass
                espera.assentar(driver, 0.8)
            else:
                logger.debug('[ATO][GRAVAR] Botão Gravar não encontrado (sem alterações ou já gravado)')
        except Exception as e:
            logger.debug(f'[ATO][GRAVAR] {e}')

        if movimento:
            logger.info(f'[ATO][MOVIMENTO] Selecionando movimento: {movimento}')
            try:
                if hasattr(driver, 'page'):
                    try:
                        driver.page.evaluate("""() => {
                            document.querySelectorAll('.cdk-overlay-backdrop, snack-bar-container, simple-snack-bar').forEach(function(el){
                                if (el.style) el.style.display = 'none';
                            });
                        }""")
                    except Exception:
                        pass
                espera.assentar(driver, 0.8, motivo='paciência pós-intimações antes de abrir aba Movimentos')

                from Fix.movimento_helpers import executar_movimento_judicial
                ok_mov = executar_movimento_judicial(driver, movimento)
                if not ok_mov:
                    logger.error(f'[ATO][MOVIMENTO]  Falha ao executar movimento: {movimento}')
                    return False, False
                logger.info(f'[ATO][MOVIMENTO]  Movimento "{movimento}" lançado e gravado com sucesso')
                espera.assentar(driver, 0.8)

            except Exception as e:
                logger.error(f'[ATO][MOVIMENTO]  Erro ao selecionar movimento: {e}')
                return False, False

        logger.info('[ATO][SALVAR_FINAL] Salvando ato...')
        try:
            salvou_final = False
            btn_salvar_final = wait_for_clickable(driver, "button[aria-label='Salvar'][color='primary']", timeout=(10 if not movimento else 4))
            if btn_salvar_final:
                safe_click_no_scroll(driver, btn_salvar_final)
                salvou_final = True
            elif hasattr(driver, 'page'):
                js_salvar_se_ativo = """() => {
                    var btns = Array.from(document.querySelectorAll('button[aria-label="Salvar"]'));
                    var btnSalvar = btns.find(function(b) {
                        return !b.disabled && !b.hasAttribute('disabled') && b.offsetWidth > 0 && b.offsetHeight > 0;
                    });
                    if (btnSalvar) { btnSalvar.click(); return true; }
                    return false;
                }"""
                salvou_final = bool(driver.page.evaluate(js_salvar_se_ativo))
            if salvou_final:
                logger.info('[ATO][SALVAR_FINAL] Ato salvo')
                espera.assentar(driver, 1.5)
            elif movimento:
                logger.debug('[ATO][SALVAR_FINAL] Nenhum botão Salvar ativo (movimento já gravou)')
            else:
                logger.warning('[ATO][SALVAR_FINAL] Botão Salvar não encontrado e não há movimento — ato pode não ter sido persistido')
        except Exception as e:
            logger.warning(f'[ATO][SALVAR_FINAL] {e}')

        if Assinar:
            logger.info('[ATO][ASSINAR] Clicando em assinar...')
            try:
                btn_assinar = wait_for_clickable(driver, 'button#assinar', timeout=5)
                if btn_assinar:
                    safe_click_no_scroll(driver, btn_assinar)
                    logger.info('[ATO][ASSINAR] Assinar clicado')
                else:
                    raise Exception('Botão assinar não disponível')
            except Exception as e:
                logger.error(f'[ATO][ASSINAR]  Erro ao clicar em assinar: {e}')
                return False, False

        logger.info('=' * 60)
        logger.info('ATO JUDICIAL - CONCLUÍDO COM SUCESSO')
        logger.info('=' * 60)
        try:
            if sigilo_ativado and atribuir_visibilidade_autor:
                logger.info('[ATO][VISIBILIDADE] Sigilo ativado e wrapper solicitou visibilidade — executando visibilidade canônica')
                try:
                    executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=debug)
                    logger.info('[ATO][VISIBILIDADE] Execução da visibilidade concluída')
                except Exception as e:
                    logger.error(f'[ATO][VISIBILIDADE] Falha ao executar visibilidade: {e}')
            elif sigilo_ativado and not atribuir_visibilidade_autor:
                logger.debug('[ATO][VISIBILIDADE] Sigilo ativado, mas wrapper não solicitou atribuição automática de visibilidade; pulando execução')
        except Exception:
            logger.warning('[ATO][VISIBILIDADE] Exceção inesperada no bloco de visibilidade (não crítico)')

        timing_total = time.time() - timing_inicio
        log_fim('ATO', {'status': 'sucesso', 'sigilo': sigilo_ativado, 'tempo': f'{timing_total:.3f}s'})
        logger.info(f'[ATO][TIMING][SUCESSO] {timing_total:.3f}s (fluxo completo)')
        return True, sigilo_ativado

    except Exception as e:
        timing_total = time.time() - timing_inicio
        log_fim('ATO', {'status': 'erro', 'motivo': str(e)[:80]})
        logger.error(f'[ATO][TIMING][ERRO] {timing_total:.3f}s erro inesperado: {e}')
        logger.error(f'[ATO]  Erro inesperado no ato judicial: {e}')
        return False, False


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
    atribuir_visibilidade_autor: Optional[bool] = False
) -> Callable[[Any, Any], Tuple[bool, bool]]:
    """Factory function que cria um wrapper para ato_judicial com parâmetros pré-definidos."""
    def wrapper(driver, **kwargs):
        params = {
            'conclusao_tipo': conclusao_tipo,
            'modelo_nome': modelo_nome,
            'prazo': prazo,
            'marcar_pec': marcar_pec,
            'movimento': movimento,
            'gigs': gigs,
            'marcar_primeiro_destinatario': marcar_primeiro_destinatario,
            'descricao': descricao,
            'sigilo': sigilo,
            'perito': perito,
            'Assinar': Assinar,
            'coleta_conteudo': coleta_conteudo,
            'inserir_conteudo': inserir_conteudo,
            'intimar': intimar,
            'atribuir_visibilidade_autor': atribuir_visibilidade_autor
        }
        params.update(kwargs)
        return ato_judicial(driver, **params)

    modelo_part = modelo_nome.lower().replace(" ", "_") if modelo_nome else "sem_modelo"
    wrapper.__name__ = f'ato_{conclusao_tipo.lower()}_{modelo_part}'
    return wrapper
