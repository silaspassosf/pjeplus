"""
judicial_navegacao.py - Funções de navegação para atos judiciais
====================================================================

Funções para abertura de tarefas, navegação entre estados do PJE,
limpeza de overlays e transição entre URLs.
"""

import time
from typing import Optional, Tuple, Any

from Fix.core import (
    aguardar_e_clicar,
    safe_click_no_scroll,
    safe_click,
    wait_for_page_load,
    aguardar_renderizacao_nativa,
    preencher_campo,
)
from Fix.log import logger
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix import espera
from atos.movimentos_navegacao import (
    clicar_botao_por_texto,
    movimentar_analise,
    esperar_transicao_tarefa,
    _normalizar_texto,
)


def _localizar_botao_navegacao(driver: Any, label: str):
    """Localiza botão de navegação de tarefa via estratégias combinadas (case/accent-insensitive)."""
    el = espera.elemento(
        driver,
        f"button[aria-label*='{label}' i], pje-botoes-transicao button[aria-label*='{label}' i]",
        teto=2,
    )
    if el:
        return el
    label_norm = _normalizar_texto(label)
    try:
        for b in espera.elementos(driver, 'pje-botoes-transicao button, button', teto=2):
            txt = _normalizar_texto(getattr(b, 'text', '') or '')
            aria = _normalizar_texto(b.get_attribute('aria-label') or '')
            title = _normalizar_texto(b.get_attribute('title') or '')
            if label_norm in txt or label_norm in aria or label_norm in title:
                return b
    except Exception:
        pass
    return None


def abrir_tarefa_processo(driver: Any) -> Tuple[bool, bool]:
    """
    Abre a tarefa do processo atual e troca para nova aba se necessário.

    Returns:
        Tuple[bool, bool]: (sucesso_abertura, ja_em_estado_final)
        - sucesso_abertura: True se conseguiu abrir a tarefa
        - ja_em_estado_final: True se já estava em /assinar, /minutar ou /conclusao
    """
    try:
        logger.info('[NAVEGAÇÃO] Abrindo tarefa do processo...')
        # zera a marca do item anterior: sem isto um processo assinado deixaria
        # a flag ligada e o seguinte seria encerrado por engano
        try:
            driver.pje_tarefa_pronta = None
        except Exception:
            pass
        handle_original = getattr(driver, 'current_window_handle', None)

        # Obter botão da tarefa
        btn_abrir_tarefa = aguardar_e_clicar(driver, BTN_TAREFA_PROCESSO, timeout=10, retornar_elemento=True)
        if not btn_abrir_tarefa:
            logger.error('[NAVEGAÇÃO] Botão "Abrir tarefa do processo" não encontrado!')
            return False, False

        # Verificar se já está em "Assinar"
        tarefa_do_botao = None
        try:
            span_tarefa = espera.elemento(driver, f"{BTN_TAREFA_PROCESSO} .texto-tarefa-processo", teto=1)
            if span_tarefa:
                tarefa_do_botao = (getattr(span_tarefa, 'text', '') or '').strip()
        except Exception:
            try:
                tarefa_do_botao = (getattr(btn_abrir_tarefa, 'text', '') or '').strip()
            except Exception:
                pass

        if tarefa_do_botao:
            driver.pje_tarefa_atual = tarefa_do_botao
            tarefa_lower = _normalizar_texto(tarefa_do_botao).lower()
            # A tarefa é lida aqui, ainda em /detalhe, e o nome define o caminho
            # (mesma regra do gigs-plugin.js:12030 — movimentar_destino):
            #   "Assinar <ato>"  -> ato já concluído, falta só assinar: nada a fazer;
            #   "Elaborar <ato>" -> minuta em elaboração: NÃO movimentar o processo,
            #                       a URL /minutar é consequência dessa tarefa.
            if 'assinar' in tarefa_lower:
                logger.info(f'[NAVEGAÇÃO] Tarefa "{tarefa_do_botao}" — ato já assinado, nada a fazer')
                driver.pje_tarefa_pronta = 'assinar'
                return True, True

            if 'elaborar' in tarefa_lower:
                # Mesmo tratamento da tarefa "Assinar": nada a fazer aqui.
                # Abrir a tarefa so levaria a /minutar para repetir a minuta;
                # o fluxo segue a partir das acoes da propria URL /minutar.
                logger.info(f'[NAVEGAÇÃO] Tarefa "{tarefa_do_botao}" — minuta em elaboração, seguindo sem abrir')
                driver.pje_tarefa_pronta = 'elaborar'
                return True, True

        # Clicar para abrir tarefa
        if not safe_click(driver, btn_abrir_tarefa):
            logger.error('[NAVEGAÇÃO] Falha ao clicar em "Abrir tarefa do processo"')
            return False, False

        # Aguardar nova aba se tiver aberto
        try:
            from Fix.browser_suporte import aguardar_nova_aba
            if handle_original:
                nova_aba = aguardar_nova_aba(driver, handle_original, timeout=10)
                if nova_aba:
                    driver.switch_to.window(nova_aba)
                    logger.info('[NAVEGAÇÃO] Foco trocado para nova aba')
        except Exception:
            logger.info('[NAVEGAÇÃO] Nenhuma nova aba detectada (continuando na mesma aba)')

        # Aguardar carregamento mínimo
        try:
            aguardar_renderizacao_nativa(driver, timeout=3)
        except Exception:
            pass

        # Verificar estado final após abertura
        current_url = (driver.current_url or '').lower()
        ja_em_estado_final = ('/assinar' in current_url or
                            '/minutar' in current_url or
                            '/conclusao' in current_url)

        if ja_em_estado_final:
            logger.info(f'[NAVEGAÇÃO] Após abertura: já em estado final ({current_url})')

        return True, ja_em_estado_final

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Erro ao abrir tarefa: {e}')
        return False, False


def limpar_overlays(driver: Any) -> None:
    """
    Remove overlays e elementos flutuantes que podem interferir nos cliques.
    """
    try:
        overlays = espera.elementos(driver, '.cdk-overlay-backdrop, .mat-dialog-container', teto=1)
        if overlays:
            if hasattr(driver, 'page'):
                driver.page.keyboard.press("Escape")
            else:
                safe_click_no_scroll(driver, 'body')
            aguardar_renderizacao_nativa(driver, 'div.cdk-overlay-backdrop.cdk-overlay-dark-backdrop.cdk-overlay-backdrop-showing', 'sumir', timeout=2)
            logger.info('[NAVEGAÇÃO] Overlays removidos')
    except Exception as e:
        logger.debug(f'[NAVEGAÇÃO] Erro ao limpar overlays: {e}')


def navegar_para_conclusao(driver: Any) -> bool:
    """
    Navega da tarefa atual para "Conclusão ao Magistrado".
    Espelha fielmente a lógica comprovada do gigs-plugin.js (aaDespacho / movimentar_destino / movimentar_analise).

    Estratégia:
    1. Verifica se já está em Conclusão (/conclusao na URL ou na tarefa).
    2. Aguarda a renderização dos botões de transição ('pje-botoes-transicao button').
    3. Tenta clique direto em "Conclusão ao Magistrado" usando clicar_botao_por_texto()
       (busca insensível a maiúsculas/minúsculas e acentos em textContent, aria-label, title, mattooltip).
    4. Se não estiver disponível diretamente, utiliza movimentar_analise() (padrão gigs-plugin)
       para transicionar para a tarefa Análise (ou botão correspondente da tarefa atual).
    5. Aguarda transição para Análise e clica em "Conclusão ao Magistrado".
    6. Aguarda o aparecimento dos botões de conclusão (pje-concluso-tarefa-botao button)
       ou transição para /minutar.

    Returns:
        bool: True se conseguiu navegar para conclusão
    """
    try:
        logger.info('[NAVEGAÇÃO] Navegando para Conclusão ao Magistrado...')

        current_url = (getattr(driver, 'current_url', '') or '').lower()
        if '/conclusao' in current_url:
            logger.info('[NAVEGAÇÃO] Já em /conclusao — pulando navegação')
            return True
        if '/minutar' in current_url:
            logger.info('[NAVEGAÇÃO] Já em /minutar — pulando navegação')
            return True

        # Obter nome da tarefa se disponível (do DOM ou do driver salvo anteriormente)
        nome_tarefa = getattr(driver, 'pje_tarefa_atual', '') or ''
        if not nome_tarefa:
            try:
                h1 = espera.elementos(driver, "pje-cabecalho-tarefa h1.titulo-tarefa, span.texto-tarefa-processo, pje-cabecalho-tarefa h1", teto=2)
                if h1:
                    nome_tarefa = (getattr(h1[0], 'text', '') or '').strip()
            except Exception:
                pass

        logger.info(f'[NAVEGAÇÃO] Nome da Tarefa Detectado: "{nome_tarefa}"')

        tarefa_norm = _normalizar_texto(nome_tarefa)
        if 'conclusao ao magistrado' in tarefa_norm or (tarefa_norm.startswith('conclusao') and 'cancelar' not in tarefa_norm):
            logger.info('[NAVEGAÇÃO] Tarefa atual já é Conclusão ao Magistrado')
            return True

        # Aguarda botões de transição renderizarem (padrão esperarColecao('pje-botoes-transicao button', 15) do gigs-plugin)
        # A só existência de um botão de transição não prova que a página da
        # tarefa carregou: o esqueleto da nova aba já traz os botões antes de a
        # tarefa montar, e a busca por "Conclusão" saía antes disso. Esperar o
        # cabeçalho da tarefa (que só aparece com ela carregada) estabiliza a
        # tela antes de procurar o destino.
        aguardar_renderizacao_nativa(driver, 'pje-cabecalho-tarefa', modo='aparecer', timeout=6)
        aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', modo='aparecer', timeout=6)

        btn_conclusao_encontrado = False

        # 1. Tentar clique direto em "Conclusão ao magistrado" (independente da tarefa)
        logger.info('[NAVEGAÇÃO] Tentando clique direto em "Conclusão ao magistrado"...')
        if clicar_botao_por_texto(driver, 'conclusao ao magistrado', timeout=3, debug=True) or clicar_botao_por_texto(driver, 'conclusao', timeout=1, debug=True):
            btn_conclusao_encontrado = True
            logger.info('[NAVEGAÇÃO] ✅ Clique direto em "Conclusão ao magistrado" realizado')
        else:
            # Fallback com _localizar_botao_navegacao + safe_click_no_scroll
            btn_dir = _localizar_botao_navegacao(driver, 'Conclusão ao magistrado')
            if btn_dir and getattr(btn_dir, 'is_displayed', lambda: True)() and safe_click_no_scroll(driver, btn_dir):
                btn_conclusao_encontrado = True
                logger.info('[NAVEGAÇÃO] ✅ Clique direto em "Conclusão ao magistrado" realizado (via elemento)')

        # 2. Se não encontrou direto, usar transição via "Análise" (padrão gigs-plugin aaDespacho)
        if not btn_conclusao_encontrado:
            logger.info('[NAVEGAÇÃO] Conclusão não disponível diretamente na tarefa "%s", movimentando via Análise (padrão gigs-plugin)...', nome_tarefa)
            movimentou = movimentar_analise(driver, nome_tarefa, debug=True)
            if not movimentou:
                movimentou = clicar_botao_por_texto(driver, 'analise', timeout=4, debug=True)

            if movimentou:
                logger.info('[NAVEGAÇÃO] Transição para Análise acionada — aguardando botões...')
                limpar_overlays(driver)
                aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', modo='aparecer', timeout=8)

                if clicar_botao_por_texto(driver, 'conclusao ao magistrado', timeout=6, debug=True) or clicar_botao_por_texto(driver, 'conclusao', timeout=2, debug=True):
                    btn_conclusao_encontrado = True
                    logger.info('[NAVEGAÇÃO] ✅ Clique em "Conclusão ao magistrado" realizado após Análise')
                else:
                    btn_pos = _localizar_botao_navegacao(driver, 'Conclusão ao magistrado')
                    if btn_pos and safe_click_no_scroll(driver, btn_pos):
                        btn_conclusao_encontrado = True
                        logger.info('[NAVEGAÇÃO] ✅ Clique em "Conclusão ao magistrado" realizado após Análise (via elemento)')

        # 3. Remover overlays pós-clique se houver
        limpar_overlays(driver)

        # 4. Validar chegada ao destino
        current_after = (getattr(driver, 'current_url', '') or '').lower()
        if '/minutar' in current_after:
            logger.info('[NAVEGAÇÃO] Processo foi direto para /minutar')
            return True

        if aguardar_renderizacao_nativa(driver, 'pje-concluso-tarefa-botao button', 'aparecer', timeout=10):
            logger.info('[NAVEGAÇÃO] ✅ Navegação para conclusão concluída com sucesso (botões de conclusão ativos)')
            return True

        if '/conclusao' in (getattr(driver, 'current_url', '') or '').lower():
            logger.info('[NAVEGAÇÃO] ✅ Em /conclusao')
            return True

        if btn_conclusao_encontrado:
            espera.assentar(driver, 1.0)
            current_check = (getattr(driver, 'current_url', '') or '').lower()
            if '/conclusao' in current_check or '/minutar' in current_check:
                return True

        logger.error(f'[NAVEGAÇÃO] Falha ao confirmar conclusão. URL atual: {driver.current_url}')
        return False

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Erro na navegação para conclusão: {e}')
        return False


def preparar_campo_minutar(driver: Any) -> bool:
    """
    Prepara o campo de filtro de modelos na tela de minutar.

    Returns:
        bool: True se conseguiu preparar o campo ou se a tela de minutar já está ativa
    """
    try:
        logger.info('[NAVEGAÇÃO] Preparando campo de filtro para minutar...')
        seletor_filtro = 'input#inputFiltro, input[id="inputFiltro"], pje-arvore-modelo-documento input, input[placeholder*="Filtro" i]'

        campo_filtro_modelo = espera.elemento(driver, seletor_filtro, teto=12)
        if not campo_filtro_modelo:
            campo_filtro_modelo = espera.ate_aparecer(driver, seletor_filtro, teto=5)

        if not campo_filtro_modelo:
            # Tolerância estrutural: se já estamos em /minutar ou o editor CKEditor já está presente,
            # não abortamos o fluxo_cls! O inserir_modelo_no_editor tem retries e localizadores próprios.
            estado_atual = verificar_estado_atual(driver)
            editor_presente = False
            try:
                if hasattr(driver, 'page'):
                    editor_presente = bool(driver.page.evaluate("""() => {
                        return !!document.querySelector('div.ck-content[contenteditable="true"], div[class*="area-conteudo"]');
                    }"""))
            except Exception:
                pass

            if estado_atual == 'minutar' or editor_presente:
                logger.warning('[NAVEGAÇÃO] Campo #inputFiltro não detectado no teto, mas tela de minuta está ativa (editor=%s). Prosseguindo para inserção de modelo.', editor_presente)
                return True

            raise Exception('input#inputFiltro não apareceu e página não está em minutar')

        if hasattr(driver, 'page'):
            driver.page.evaluate("""(sel) => {
                var el = document.querySelector(sel);
                if (el) {
                    el.removeAttribute('disabled');
                    el.removeAttribute('readonly');
                    el.value = '';
                    el.focus();
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('keyup', {bubbles: true}));
                }
            }""", 'input#inputFiltro, input[id="inputFiltro"]')
        else:
            preencher_campo(driver, 'input#inputFiltro', '')

        logger.info('[NAVEGAÇÃO] Campo de filtro preparado com sucesso')
        aguardar_renderizacao_nativa(driver, 'input#inputFiltro', 'aparecer', timeout=2)
        return True

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Falha ao preparar campo de filtro: {e}')
        return False


def escolher_tipo_conclusao(driver: Any, conclusao_tipo: str) -> bool:
    """
    Escolhe o tipo de conclusão na tela de conclusão do processo.

    ESTRATÉGIA ROBUSTA (GIGS aadespacho / despacho_engine):
    - Normaliza acentos (Suspensão == Suspensao)
    - Faz polling ativo injetando JS para clicar
    """
    try:
        logger.info(f'[CONCLUSÃO] Escolhendo tipo de conclusão: {conclusao_tipo}')

        script_eval = """tipo_buscado => {
            function normalizar(s) {
                return (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
            }

            var tipo_norm = normalizar(tipo_buscado);
            var candidatos = document.querySelectorAll('pje-concluso-tarefa-botao button, pje-conclusao-dependencia button, button.mat-raised-button');

            for (var i = 0; i < candidatos.length; i++) {
                var btn = candidatos[i];
                var txt = normalizar(btn.textContent);
                var aria = normalizar(btn.getAttribute('aria-label'));

                if (txt.indexOf(tipo_norm) !== -1 || aria.indexOf(tipo_norm) !== -1) {
                    if (aria.indexOf('remover') === -1 && aria.indexOf('fechar') === -1 && aria.indexOf('excluir') === -1) {
                        if (!btn.disabled && btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                            btn.scrollIntoView({block: 'center', behavior: 'instant'});
                            btn.click();
                            return true;
                        }
                    }
                }
            }
            return false;
        }"""

        clicou = False
        limite = time.time() + 15
        while time.time() < limite:
            try:
                if hasattr(driver, 'page'):
                    if driver.page.evaluate(script_eval, conclusao_tipo):
                        clicou = True
                        break
                elif hasattr(driver, '_js'):
                    if driver._js(script_eval, conclusao_tipo):
                        clicou = True
                        break
            except Exception:
                pass
            espera.assentar(driver, 0.5, motivo='esperando botão de conclusão renderizar')

        if not clicou:
            logger.error(f'[CONCLUSÃO] Botão de conclusão "{conclusao_tipo}" não encontrado após 15s de espera')
            return False

        logger.info(f'[CONCLUSÃO] ✅ Botão de conclusão "{conclusao_tipo}" clicado com sucesso')

        try:
            espera.ate_js(driver, "document.readyState === 'complete'", teto=10)
        except Exception:
            pass

        return True

    except Exception as e:
        logger.error(f'[CONCLUSÃO] Erro ao escolher tipo de conclusão: {e}')
        return False


def aguardar_transicao_minutar(driver: Any, timeout: float = 20.0) -> bool:
    """
    Aguarda a transição da tela de conclusão para a tela de minutar.
    Observa a mudança da URL para /minutar e a renderização dos componentes
    exclusivos de minutar (árvore de modelos, input de filtro, editor).

    Returns:
        bool: True se conseguiu fazer a transição
    """
    try:
        logger.info(f'[CONCLUSÃO] Aguardando transição para tela de minutar (teto={timeout}s)...')

        seletor_exclusivo_minutar = (
            'input#inputFiltro, input[id="inputFiltro"], '
            'pje-arvore-modelo-documento, div.ck-content[contenteditable="true"], '
            'div[class*="area-conteudo"]'
        )

        limite = time.monotonic() + float(timeout)
        transicionou = False
        while time.monotonic() < limite:
            url = (getattr(driver, 'current_url', '') or '').lower()
            if '/minutar' in url:
                transicionou = True
                break
            try:
                if hasattr(driver, 'page'):
                    if driver.page.evaluate(f"""() => {{
                        var els = document.querySelectorAll('{seletor_exclusivo_minutar}');
                        for (var i = 0; i < els.length; i++) {{
                            var el = els[i];
                            if (el && (el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0)) {{
                                return true;
                            }}
                        }}
                        return false;
                    }}"""):
                        transicionou = True
                        break
            except Exception:
                pass
            espera.assentar(driver, 0.15)

        if not transicionou:
            transicionou = bool(espera.elemento(driver, seletor_exclusivo_minutar, teto=3))

        if not transicionou:
            logger.error(f'[CONCLUSÃO] Falha na transição para minutar após {timeout}s: URL={getattr(driver, "current_url", "")}')
            return False

        # Aguardar spinners de carregamento inicial assentarem
        try:
            espera.ate_sumir(driver, '.loading-spinner, .mat-progress-spinner, .fa-spin', teto=5)
        except Exception:
            pass
        espera.assentar(driver, 0.5, motivo='estabilização pós-transição para minutar')

        logger.info('[CONCLUSÃO] ✅ Transição para minutar detectada com sucesso')
        return True

    except Exception as e:
        logger.error(f'[CONCLUSÃO] Erro inesperado na transição para minutar: {e}')
        return False


def verificar_estado_atual(driver: Any) -> str:
    """
    Verifica o estado atual do processo baseado na URL.

    Returns:
        str: Estado atual ('assinar', 'minutar', 'conclusao', 'detalhe', 'outro')
    """
    current_url = (driver.current_url or '').lower()

    if '/assinar' in current_url:
        return 'assinar'
    elif '/minutar' in current_url:
        return 'minutar'
    elif '/conclusao' in current_url:
        return 'conclusao'
    elif '/detalhe' in current_url:
        return 'detalhe'
    else:
        return 'outro'


def focar_campo_minutar_se_necessario(driver: Any) -> bool:
    """
    Foca no campo de filtro de modelos se estiver na tela de minutar.

    Returns:
        bool: True se conseguiu focar ou se não era necessário
    """
    try:
        if verificar_estado_atual(driver) == 'minutar':
            logger.info('[CONCLUSÃO] Já em minutar - focando no campo de filtro')
            seletor_filtro = 'input#inputFiltro, input[id="inputFiltro"], pje-arvore-modelo-documento input'
            campo_filtro_modelo = espera.elemento(driver, seletor_filtro, teto=10)
            if campo_filtro_modelo:
                if hasattr(driver, 'page'):
                    driver.page.evaluate("() => { const el = document.querySelector('input#inputFiltro'); if (el) el.focus(); }")
                else:
                    preencher_campo(driver, 'input#inputFiltro', '')
                logger.info('[CONCLUSÃO] Foco no campo #inputFiltro realizado')
            else:
                logger.warning('[CONCLUSÃO] Campo de filtro não visível de imediato ao focar')
        return True
    except Exception as e:
        logger.warning(f'[CONCLUSÃO] Erro ao focar campo minutar: {e}')
        return False