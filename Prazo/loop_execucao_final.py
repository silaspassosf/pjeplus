"""Prazo - Loop Execucao Final (ciclo 2 + ciclo 3)

Consolidado de: loop_ciclo2_processamento.py, loop_ciclo3.py
"""
# ── Imports ──
import logging
import math
import re
import time
import traceback
from typing import Any, List, Tuple, Union

# Selenium imports removed — Playwright native

from Fix import espera
from Fix.core import (
    safe_click_no_scroll,
    aguardar_renderizacao_nativa,
    aplicar_filtro_100,
    preencher_campo,
)
from Fix.facade_publica import buscar
from Fix.variaveis import cliente_para

from .loop_lote import (
    _ciclo1_abrir_suitcase,
    _ciclo1_aguardar_movimentacao_lote,
    _ciclo1_movimentar_destino,
    _ciclo1_retornar_lista,
    _ciclo2_aplicar_filtros,
    _ciclo2_processar_livres,
    _ciclo2_selecionar_nao_livres,
)
from .loop_orquestrador import (
    SCRIPT_SELECAO_LIVRES,
    _selecionar_processos_por_gigs_aj_jt,
    log_seletor_vencedor,
    medir_latencia,
    pausar_confirmacao,
)

logger = logging.getLogger(__name__)


def _executar_js(driver: Any, script: str, *args):
    """Executa script JS via driver de forma compatível."""
    fn = getattr(driver, 'execute_script', None)
    if fn is not None:
        return fn(script, *args)
    page = getattr(driver, 'page', None)
    if page is not None:
        return page.evaluate(script, *args)
    return None


# ═══════════════════════════════════════════════
# ── 1. loop_ciclo2_processamento.py ──
# ═══════════════════════════════════════════════

def _parse_atividade_xs_param(valor: str) -> tuple:
    partes = valor.split('/')
    if len(partes) >= 3:
        prazo = partes[0].strip()
        responsavel = partes[1].strip() if partes[1].strip() else None
        observacao = '/'.join(partes[2:]).strip()
        return prazo, responsavel, observacao
    if len(partes) == 2:
        return partes[0].strip(), None, partes[1].strip()
    return None, None, valor.strip()


def _ciclo2_criar_atividade_xs(driver: Any) -> bool:
    """Cria atividade 'xs' para processos selecionados."""
    try:
        ids_selecionados = _ciclo2_obter_numeros_processos_selecionados(driver)

        # Clique no botão tag verde para abrir o dropdown de atividade
        tag_verde = espera.elemento(driver, 'i.fa.fa-tag.icone.texto-verde', teto=10)
        if not tag_verde:
            logger.error('[CICLO2][XS] Botão tag verde não encontrado')
            return False
        safe_click_no_scroll(driver, tag_verde)

        # Aguardar renderização do menu de atividades
        aguardar_renderizacao_nativa(driver, "button.mat-menu-item", timeout=10)

        # Clique direto no botão "Atividade" via CSS/texto
        sucesso_atividade = False
        btns = espera.elementos(driver, "button.mat-menu-item", teto=2)
        for btn in btns:
            if "Atividade" in getattr(btn, 'text', ''):
                safe_click_no_scroll(driver, btn)
                sucesso_atividade = True
                break

        if not sucesso_atividade:
            # Fallback: buscar via SmartFinder
            btn_atividade = buscar(driver, 'ciclo2_btn_atividade', [
                "//button[contains(normalize-space(.), 'Atividade')]",
                "//button[contains(translate(normalize-space(.), 'ATIVIDADE', 'atividade'), 'atividade')]",
                "button[aria-label*='Atividade']",
                "button[aria-label*='atividade']",
                "button.mat-menu-item"
            ])
            if btn_atividade:
                safe_click_no_scroll(driver, btn_atividade)
                sucesso_atividade = True

        if not sucesso_atividade:
            logger.error('[CICLO2][XS] Botão "Atividade" não encontrado')
            return False

        # Aguardar renderização do formulário de atividade
        try:
            aguardar_renderizacao_nativa(driver, "textarea[formcontrolname='observacao']", timeout=10)
        except Exception:
            pass

        prazo, _, observacao = _parse_atividade_xs_param('-1//xs1')

        # Preencher prazo, se o campo existir
        if prazo is not None:
            for seletor in [
                'input[formcontrolname="dias"]',
                'input[formcontrolname="prazo"]',
                'input[aria-label="Prazo em dias úteis"]',
                'mat-form-field input[type="number"]',
                'input[type="number"]'
            ]:
                if preencher_campo(driver, seletor, prazo):
                    espera.assentar(driver, 0.3)
                    break

        # Preencher observação
        preencheu_obs = False
        for seletor in [
            "textarea[formcontrolname='observacao']",
            "textarea[aria-label*='Observa']",
            "textarea"
        ]:
            if preencher_campo(driver, seletor, observacao):
                espera.assentar(driver, 0.3)
                preencheu_obs = True
                break

        if not preencheu_obs:
            logger.error('[CICLO2][XS] Campo de observação não encontrado')
            return False

        # Encontrar e clicar no botão Salvar
        spans = espera.elementos(driver, "button.mat-raised-button span", teto=2)
        btn_salvar = next((s for s in spans if "Salvar" in getattr(s, 'text', '')), None)
        if not btn_salvar:
            btn_salvar = espera.elemento(driver, "button[aria-label*='Salvar'] span", teto=1)
        if not btn_salvar:
            logger.error('[CICLO2][XS] Botão Salvar não encontrado')
            return False
        btn_pai = espera.elemento(btn_salvar, "..", teto=0.5) or btn_salvar

        # Scroll e clique no botão salvar
        safe_click_no_scroll(driver, btn_pai)

        # Aguardar fechamento do modal via observer
        try:
            aguardar_renderizacao_nativa(driver, 'mat-dialog-container', modo='sumir', timeout=15)
        except Exception:
            modais = espera.elementos(driver, "mat-dialog-container", teto=0.5)
            if modais:
                logger.error('[CICLO2][XS] Modal ainda aberto após Salvar')
                return False

        if ids_selecionados:
            selecionados_restantes = _ciclo2_contar_processos_selecionados(driver)
            if selecionados_restantes == 0:
                reselecionados = _ciclo2_reselecionar_processos(driver, ids_selecionados)
                if reselecionados:
                    logger.info(f'[CICLO2][XS] Re-selecionados {reselecionados}/{len(ids_selecionados)} processo(s) após salvar XS')
                try:
                    aguardar_renderizacao_nativa(driver, 'mat-checkbox input[type="checkbox"]:checked', timeout=3)
                except Exception:
                    pass

        logger.info('[CICLO2][XS] Atividade xs criada')
        return True
    except Exception as e:
        logger.error(f'[LOOP_PRAZO][ERRO] Falha ao criar atividade xs: {e}')
        return False


def _ciclo2_movimentar_lote(driver: Any, opcao_destino: str, ha_mais: bool) -> bool:
    """Abre suitcase, seleciona destino e movimenta processos."""
    if not _ciclo1_abrir_suitcase(driver):
        logger.error('[CICLO2] Falha ao abrir suitcase')
        return False

    if not _ciclo1_aguardar_movimentacao_lote(driver):
        logger.error('[CICLO2] Falha ao aguardar tela movimentação')
        return False

    # Reutilizar a lógica robusta do ciclo1 para selecionar destino (inclui retries)
    if not _ciclo1_movimentar_destino(driver, opcao_destino):
        logger.error(f'[CICLO2] Falha ao selecionar destino "{opcao_destino}"')
        return False

    # Retorno mais curto que o ciclo1: navegar direto para a lista após confirmar a movimentação.
    _t0 = time.perf_counter()
    try:
        driver.get("https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos")
        try:
            aguardar_renderizacao_nativa(driver, 'tr.cdk-drag', timeout=8)
        except Exception:
            try:
                aguardar_renderizacao_nativa(driver, "//span[contains(text(), 'Fase processual')]", timeout=8)
            except Exception:
                pass
    except Exception as e:
        logger.info(f'[CICLO2] Retorno direto para a lista falhou, fallback para history.back: {e}')
        try:
            _ciclo1_retornar_lista(driver)
            aguardar_renderizacao_nativa(driver, 'tr.cdk-drag', timeout=8)
        except Exception:
            pass

    _t1 = time.perf_counter()
    try:
        logger.info(f'[LATENCIA][DETALHE] CICLO2_NAV_PAINEL8: {(_t1-_t0)*1000:.1f}ms')
    except Exception:
        pass

    logger.info(f'[CICLO2] Lote movimentado ({opcao_destino})')
    return True


def ciclo2_processar_livres_apenas_uma_vez(driver: Any, opcao_destino: str = 'Cumprimento de providências') -> Tuple[int, bool]:
    """
    Fase 2.1: Processa APENAS seleção de processos livres (SEM aplicar atividade XS).
    A atividade XS será aplicada na Fase 2.2 para GIGS+LIVRES juntos.

    Returns:
        Tupla (livres_selecionados, ha_nao_livres_para_providencias)
    """
    if not _ciclo2_aplicar_filtros(driver):
        return 0, False

    # 1. Criar client GIGS para busca de atividades
    client = None
    try:
        client = cliente_para(driver)
    except Exception as e:
        logger.warning(f'[LOOP_PRAZO][WARN] Falha ao inicializar client GIGS (continuando sem GIGS): {e}')
        client = None

    # 2. Selecionar LIVRES (SEM aplicar XS ainda)
    livres = _ciclo2_processar_livres(driver, client=client)

    # 3. Contar total de não-livres (para saber se entra no loop de providências)
    # Primeiro, salvar os selecionados atuais (GIGS+LIVRES) antes de testar não-livres
    try:
        resultado = _executar_js(driver, """
            function selecionarProcessos(maxProcessos) {
                const linhas = document.querySelectorAll('tr.cdk-drag');
                let selecionados = 0;
                let totalNaoLivres = 0;
                linhas.forEach(linha => {
                    const prazo = linha.querySelector('td:nth-child(9) time');
                    const prazoPreenchido = prazo && prazo.textContent.trim();
                    const hasComment = linha.querySelector('i.fa-comment') !== null;
                    const inputField = linha.querySelector('input[matinput]');
                    const campoPreenchido = inputField && inputField.value.trim();
                    if (prazoPreenchido || hasComment || campoPreenchido) {
                        totalNaoLivres++;
                    }
                });
                for (const linha of linhas) {
                    if (selecionados >= maxProcessos) break;
                    const prazo = linha.querySelector('td:nth-child(9) time');
                    const prazoPreenchido = prazo && prazo.textContent.trim();
                    const hasComment = linha.querySelector('i.fa-comment') !== null;
                    const inputField = linha.querySelector('input[matinput]');
                    const campoPreenchido = inputField && inputField.value.trim();
                    if (prazoPreenchido || hasComment || campoPreenchido) {
                        const checkbox = linha.querySelector('mat-checkbox input[type="checkbox"]');
                        if (checkbox && !checkbox.checked) {
                            checkbox.click();
                            selecionados++;
                        }
                    }
                }
                return {selecionados, totalNaoLivres};
            }
            return selecionarProcessos(arguments[0]);
        """, 1)  # Seleciona apenas 1 para contar total
        total_nao_livres = resultado['totalNaoLivres'] if resultado else 0
        ha_nao_livres = total_nao_livres > 0

        # Desselecionar aquele 1 não-livre que foi selecionado para teste
        try:
            _executar_js(driver, """
                document.querySelectorAll('mat-checkbox input[type="checkbox"]:checked').forEach(function(c){
                    var linha = c.closest('tr');
                    var temProvidencias = linha.querySelector('a[href*="providencias"]') !== null;
                    if (temProvidencias) {
                        c.click();
                    }
                });
            """)
            try:
                aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
            except Exception:
                pass
        except Exception:
            pass

        return livres, ha_nao_livres
    except Exception as e:
        logger.error(f'[LOOP_PRAZO][ERRO] Erro ao contar não-livres: {e}')
        return livres, False


def ciclo2_loop_providencias(driver: Any, opcao_destino: str = 'Cumprimento de providências') -> bool:
    """
    Fase 2.3: Loop para processar providências (cumprimento) - processa NÃO-LIVRES.
    Processa até 20 processos não-livres por iteração.
    Se selecionou < 20 → último ciclo, encerra.

    Returns:
        True: processamento bem-sucedido
        False: erro crítico
    """
    iteracao = 0

    while True:
        iteracao += 1

        # Desselecionar todos antes de começar nova iteração
        try:
            _executar_js(driver, "document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').forEach(c=>c.click());")
            # aguardar até que não haja checkboxes marcados (sincronização mínima)
            try:
                aguardar_renderizacao_nativa(driver, "mat-checkbox input[type=\"checkbox\"]:checked", modo='sumir', timeout=6)
            except Exception:
                pass
        except Exception:
            pass

        # REAPLICAR FILTROS a partir da 2ª iteração (1ª já tem filtros do ciclo2)
        # Motivo: ao voltar da movimentação em lote, a lista perde os filtros aplicados
        if iteracao > 1:
            if not _ciclo2_aplicar_filtros(driver):
                logger.error('[CICLO2][PROVIDENCIAS] Falha ao reaplicar filtros')
                return False

        # Selecionar até 20 não-livres
        nao_livres, ha_mais = _ciclo2_selecionar_nao_livres(driver)

        if nao_livres == 0:
            logger.info('[CICLO2][PROVIDENCIAS] Nenhum não-livre')
            return True

        logger.info(f'[CICLO2][PROVIDENCIAS] Ciclo {iteracao}: {nao_livres} processos')

        # Movimentar para providências
        if not _ciclo2_movimentar_lote(driver, opcao_destino, ha_mais):
            logger.error('[CICLO2][PROVIDENCIAS] Falha ao movimentar lote')
            return False

        # Se selecionou < 20 → último ciclo (não há mais processos)
        if nao_livres < 20:
            logger.info(f'[CICLO2][PROVIDENCIAS] Último ciclo concluído ({nao_livres} processos)')
            return True

        # Continuar loop (selecionou exatamente 20, pode haver mais)
        # Pequena espera de estabilização opcional, baseada no indicador de total de registros
        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=3)
        except Exception:
            pass


def _ciclo2_contar_processos_selecionados(driver: Any) -> int:
    """Retorna a quantidade de checkboxes de processo selecionados no painel atual."""
    try:
        return int(_executar_js(driver, "return document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').length;") or 0)
    except Exception as e:
        logger.warning(f'[CICLO2] Não foi possível contar selecionados: {e}')
        return 0


def _ciclo2_obter_numeros_processos_selecionados(driver: Any) -> List[str]:
    """Retorna lista de números de processo atualmente selecionados."""
    script = r"""
        const rows = Array.from(document.querySelectorAll('tr.cdk-drag'));
        const regex = /(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/;
        return rows.reduce((acc, row) => {
            const checkbox = row.querySelector('mat-checkbox input[type="checkbox"]');
            if (!checkbox || !checkbox.checked) return acc;
            let text = '';
            const a = row.querySelector('a');
            if (a && a.textContent) text = a.textContent;
            else text = row.textContent || '';
            const match = text.match(regex);
            if (match) acc.push(match[1]);
            return acc;
        }, []);
    """
    try:
        return _executar_js(driver, script) or []
    except Exception as e:
        logger.warning(f'[CICLO2] Não foi possível obter números de processos selecionados: {e}')
        return []


def _ciclo2_reselecionar_processos(driver: Any, numeros_processos: List[str]) -> int:
    """Resseliona processos pelo número de processo na tabela."""
    if not numeros_processos:
        return 0

    script = r"""
        const numeros = arguments[0];
        const rows = Array.from(document.querySelectorAll('tr.cdk-drag'));
        const regex = /(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/;
        let cont = 0;
        rows.forEach(row => {
            const checkbox = row.querySelector('mat-checkbox input[type="checkbox"]');
            if (!checkbox) return;
            let text = '';
            const a = row.querySelector('a');
            if (a && a.textContent) text = a.textContent;
            else text = row.textContent || '';
            const match = text.match(regex);
            if (!match) return;
            const numero = match[1];
            if (numeros.includes(numero) && !checkbox.checked) {
                checkbox.click();
                cont += 1;
            }
        });
        return cont;
    """
    try:
        return int(_executar_js(driver, script, numeros_processos) or 0)
    except Exception as e:
        logger.warning(f'[CICLO2] Falha ao reselecionar processos: {e}')
        return 0


def ciclo2(driver: Any, opcao_destino: str = 'Cumprimento de providências') -> Union[bool, str]:
    """
    Ciclo 2 completo: GIGS + LIVRES + PROVIDÊNCIAS.
    Ordem: 1) NÃO-LIVRES (providências) → 2) Reaplicar filtros → 3) GIGS+LIVRES+XS
    """
    try:
        with medir_latencia('CICLO2_TOTAL'):
            logger.info('[CICLO2] Iniciando ciclo 2 (ordem: NÃO-LIVRES -> LIVRES+XS)...')

            # Aplicar filtros iniciais
            if not _ciclo2_aplicar_filtros(driver):
                return False

            # Inicializar client GIGS quando possível
            client = None
            try:
                client = cliente_para(driver)
            except Exception as e:
                logger.warning(f'[CICLO2][WARN] Falha ao inicializar client GIGS: {e}')

            # 1) Selecionar e processar NÃO-LIVRES primeiro (movimentação em lote / providências)
            with medir_latencia('CICLO2_LOOP_PROVIDENCIAS'):
                logger.info('[CICLO2] ===== Iniciando processamento de NÃO-LIVRES (providências) =====')
                if not ciclo2_loop_providencias(driver, opcao_destino):
                    logger.error('[CICLO2] Erro ao processar providências (não-livres) — continuando para LIVRES+XS')
                    # Garantir retorno ao painel 8 antes de prosseguir
                    try:
                        driver.get('https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos')
                        aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=6)
                    except Exception as _nav_e:
                        logger.warning(f'[CICLO2] Falha ao retornar ao painel 8 após erro de providências: {_nav_e}')

            # 2) Reaplicar filtros e selecionar GIGS + LIVRES para criar atividade XS
            if not _ciclo2_aplicar_filtros(driver):
                return False

            with medir_latencia('CICLO2_SELECAO_GIGS_AJ_JT'):
                gigs_selecionados = _selecionar_processos_por_gigs_aj_jt(driver, client)

            with medir_latencia('CICLO2_SELECAO_LIVRES'):
                livres_selecionados = _ciclo2_processar_livres(driver, client=client)

            total_selecionados = gigs_selecionados + livres_selecionados
            logger.info(f'[CICLO2] Total selecionado para XS: {total_selecionados} (GIGS: {gigs_selecionados}, Livres: {livres_selecionados})')

            if total_selecionados > 0:
                selected_before = _ciclo2_contar_processos_selecionados(driver)
                selected_ids = _ciclo2_obter_numeros_processos_selecionados(driver)
                logger.info(f'[CICLO2] Selecionados antes de XS: {selected_before} | IDs: {selected_ids}')

                if not _ciclo2_criar_atividade_xs(driver):
                    logger.error('[CICLO2] Falha ao criar atividade XS')
                    return False

                selected_after = _ciclo2_contar_processos_selecionados(driver)
                logger.info(f'[CICLO2] Selecionados depois de XS: {selected_after}')

                if selected_after < selected_before and selected_ids:
                    logger.warning('[CICLO2] Aviso: seleção foi perdida após criação de XS, efetuando reseleção')
                    reselecionados = _ciclo2_reselecionar_processos(driver, selected_ids)
                    logger.info(f'[CICLO2] Re-selecionados: {reselecionados} (esperado: {len(selected_ids)})')

                    selected_after = _ciclo2_contar_processos_selecionados(driver)
                    logger.info(f'[CICLO2] Selecionados após reseleção: {selected_after}')

            logger.info('[CICLO2] Ciclo 2 concluído com sucesso.')
            return True

    except Exception as e:
        logger.error(f'[CICLO2] Erro no ciclo 2: {e}')
        return False


# ═══════════════════════════════════════════════
# ── 2. loop_ciclo3.py ──
# ═══════════════════════════════════════════════

URL_PAINEL_CUMPRIMENTO = 'https://pje.trt2.jus.br/pjekz/painel/global/6/lista-processos'


def ciclo3(driver: Any) -> bool:
    """
    Ciclo 3: Processar painel de cumprimento de providências (painel 6)

    Fluxo:
    1. Navega para painel global 6 (cumprimento de providências)
    2. Aplica filtro 100
    3. Seleciona processos LIVRES (sem GIGS)
    4. Aplica atividade XS se houver processos livres

    Args:
        driver: conexao/driver PJe já logado

    Returns:
        True se sucesso, False se falha crítica
    """
    try:
        logger.info("[CICLO3] Iniciando processamento painel cumprimento providências")

        # 1. Navegação
        logger.info(f"[CICLO3] Navegando para painel 6: {URL_PAINEL_CUMPRIMENTO}")
        driver.get(URL_PAINEL_CUMPRIMENTO)
        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=3)
        except Exception:
            espera.ate_js(driver, "document.readyState === 'complete'", teto=3)

        # 2. Aplicar filtro 100
        logger.info("[CICLO3] Aplicando filtro 100...")
        try:
            aplicar_filtro_100(driver)
            logger.info("[CICLO3] Filtro 100 aplicado")
        except Exception as e:
            logger.error(f"[CICLO3] Erro ao aplicar filtro 100: {e}")
            return False

        try:
            aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=2)
        except Exception:
            espera.ate_js(driver, "document.readyState === 'complete'", teto=2)

        # 3. Selecionar livres: percorrer todas as páginas após aplicar filtro 100
        logger.info("[CICLO3] Selecionando processos livres (sem GIGS) em todas as páginas...")

        # Tentar obter total de processos para calcular número de páginas
        try:
            total_elem = espera.elemento(driver, 'span.total-registros', teto=2)
            total_text = getattr(total_elem, 'text', '') if total_elem else ''
            m = re.search(r'de\s+(\d+)', total_text)
            total = int(m.group(1)) if m else -1
        except Exception:
            total = -1

        if total > 0:
            paginas = math.ceil(total / 100)
        else:
            paginas = 1

        total_selecionados = 0
        for pagina in range(paginas):
            try:
                selecionados = _executar_js(driver, SCRIPT_SELECAO_LIVRES)
                if selecionados == -1:
                    logger.error(f"[CICLO3] ERRO no script de seleção de livres na página {pagina+1}")
                    return False
                elif isinstance(selecionados, int) and selecionados > 0:
                    total_selecionados += selecionados
                    logger.info(f"[CICLO3] Página {pagina+1}: {selecionados} livres selecionados")
                else:
                    logger.info(f"[CICLO3] Página {pagina+1}: 0 livres selecionados")
            except Exception as e:
                logger.error(f"[CICLO3] Erro ao selecionar livres na página {pagina+1}: {e}")

            # Ir para próxima página, se houver
            if pagina < paginas - 1:
                try:
                    btn_next = espera.elemento(driver, 'mat-paginator button[aria-label="Próxima página"]', teto=2)
                    if btn_next:
                        safe_click_no_scroll(driver, btn_next)
                    try:
                        aguardar_renderizacao_nativa(driver, 'span.total-registros', timeout=1)
                    except Exception:
                        espera.ate_js(driver, "document.readyState === 'complete'", teto=1)
                except Exception:
                    logger.info("[CICLO3] Não foi possível navegar para próxima página (ou última página atingida)")

        logger.info(f"[CICLO3] Total de processos livres selecionados: {total_selecionados}")

        # Usar a mesma execução de atividade XS do ciclo 2
        if total_selecionados > 0:
            logger.info("[CICLO3] Aplicando atividade XS para os processos livres selecionados...")
            if not _ciclo2_criar_atividade_xs(driver):
                logger.error("[CICLO3] Falha ao aplicar XS após seleção de livres")
                return False
            logger.info("[CICLO3] Atividade XS aplicada")
        else:
            logger.info("[CICLO3] Nenhum processo livre encontrado")

        logger.info("[CICLO3] Ciclo 3 concluído com sucesso")
        return True

    except Exception as e:
        logger.error(f"[CICLO3] Erro no ciclo 3: {e}")
        logger.error(traceback.format_exc())
        return False
