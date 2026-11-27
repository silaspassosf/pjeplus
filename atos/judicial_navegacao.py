"""judicial_navegacao.py - Funções de navegação para atos judiciais"""

from typing import Optional, Tuple, Any

from Fix.core import (
    aguardar_e_clicar,
    safe_click_no_scroll,
    safe_click,
    wait_for_page_load,
    aguardar_renderizacao_nativa,
    esperar_elemento,
    esperar_url_conter,
    preencher_campo,
)
from Fix.log import logger
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix import espera
from atos.movimentos_navegacao import (
    navegar_para_tarefa,
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
    """Abre a tarefa do processo atual e troca para nova aba se necessário."""
    try:
        logger.info('[NAVEGAÇÃO] Abrindo tarefa do processo...')
        # zera a marca do item anterior: sem isto um processo assinado deixaria
        try:
            driver.pje_tarefa_pronta = None
        except Exception:
            pass
        handle_original = getattr(driver, 'current_window_handle', None)
        try:
            handles_antes = set(getattr(driver, 'window_handles', []) or [])
        except Exception:
            handles_antes = set()

        btn_abrir_tarefa = aguardar_e_clicar(driver, BTN_TAREFA_PROCESSO, timeout=10, retornar_elemento=True)
        if not btn_abrir_tarefa:
            logger.error('[NAVEGAÇÃO] Botão "Abrir tarefa do processo" não encontrado!')
            return False, False

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
            if 'assinar' in tarefa_lower:
                logger.info(f'[NAVEGAÇÃO] Tarefa "{tarefa_do_botao}" — ato já assinado, nada a fazer')
                driver.pje_tarefa_pronta = 'assinar'
                return True, True

            if 'elaborar' in tarefa_lower:
                logger.info(f'[NAVEGAÇÃO] Tarefa "{tarefa_do_botao}" — minuta em elaboração, seguindo sem abrir')
                driver.pje_tarefa_pronta = 'elaborar'
                return True, True

        if not safe_click(driver, btn_abrir_tarefa):
            logger.error('[NAVEGAÇÃO] Falha ao clicar em "Abrir tarefa do processo"')
            return False, False

        try:
            from Fix.browser_suporte import aguardar_nova_aba
            if handles_antes or handle_original:
                nova_aba = aguardar_nova_aba(driver, handles_antes or handle_original, timeout=10)
                if nova_aba:
                    driver.switch_to.window(nova_aba)
                    logger.info('[NAVEGAÇÃO] Foco trocado para nova aba')
        except Exception:
            logger.info('[NAVEGAÇÃO] Nenhuma nova aba detectada (continuando na mesma aba)')

        try:
            aguardar_renderizacao_nativa(driver, timeout=3)
        except Exception:
            pass

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
    """Remove overlays e elementos flutuantes que podem interferir nos cliques."""
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
    """Navega da tarefa atual para "Conclusão ao Magistrado"."""
    try:
        logger.info('[NAVEGAÇÃO] Navegando para Conclusão ao Magistrado...')

        current_url = (getattr(driver, 'current_url', '') or '').lower()
        if '/conclusao' in current_url:
            logger.info('[NAVEGAÇÃO] Já em /conclusao — pulando navegação')
            return True
        if '/minutar' in current_url:
            logger.info('[NAVEGAÇÃO] Já em /minutar — pulando navegação')
            return True

        if '/tarefa' not in current_url:
            try:
                atual = driver.current_window_handle
                for h in reversed(list(getattr(driver, 'window_handles', []) or [])):
                    driver.switch_to.window(h)
                    if '/tarefa' in (getattr(driver, 'current_url', '') or '').lower():
                        logger.warning('[NAVEGAÇÃO] Foco estava fora da tarefa (%s) — trocado para a aba da tarefa (%s)',
                                       current_url, driver.current_url)
                        break
                else:
                    driver.switch_to.window(atual)
            except Exception as e_aba:
                logger.debug('[NAVEGAÇÃO] Guarda de aba falhou: %s', e_aba)
        logger.info('[NAVEGAÇÃO] Procurando botões na URL: %s', getattr(driver, 'current_url', ''))

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

        # A tarefa abre numa aba nova e o Angular monta o DOM depois do
        aguardar_renderizacao_nativa(
            driver, 'nav.container-botoes button, pje-botoes-transicao button',
            modo='aparecer', timeout=15)

        tarefa_direta = 'aguardando prazo' in tarefa_norm
        # obrigatória é Análise antes da conclusão. Procurar o botão direto aqui só
        exige_analise = 'cumprimento de providencias' in tarefa_norm

        # ORDEM DE BUSCA — a PRIMEIRA tentativa tem de ser a que acerta.
        SELETOR_CONCLUSAO = (
            "button[aria-label*='Conclusão ao magistrado' i], "
            "pje-botoes-transicao button[aria-label*='Conclusão ao magistrado' i]"
        )

        logger.info('[NAVEGAÇÃO] Tarefa "%s": procurando conclusão direta antes de rotear', nome_tarefa)
        botao = None
        if not exige_analise:
            botao = esperar_elemento(
                driver, 'nav.container-botoes button',
                texto='Conclusão ao magistrado',
                timeout=15 if tarefa_direta else 6)
            if botao is None:
                botao = espera.elemento(driver, SELETOR_CONCLUSAO, teto=2)
            if botao is None:
                botao = esperar_elemento(
                    driver, 'button', texto='Conclusão ao magistrado', timeout=2)

        if botao is None and not tarefa_direta:
            logger.info('[NAVEGAÇÃO] Conclusão indisponível — roteando via máquina de estados (Análise)')
            if not navegar_para_tarefa(driver, 'conclusão ao magistrado', debug=True, tarefa_atual_conhecida=nome_tarefa):
                logger.info('[NAVEGAÇÃO] Roteamento não concluiu — tentando o botão na tela atual')
            botao = esperar_elemento(
                driver, 'nav.container-botoes button',
                texto='Conclusão ao magistrado', timeout=15)
            if botao is None:
                botao = espera.elemento(driver, SELETOR_CONCLUSAO, teto=2)
            if botao is None:
                botao = esperar_elemento(
                    driver, 'button', texto='Conclusão ao magistrado', timeout=2)

        if botao is None:
            _dump_botoes_conclusao(
                driver,
                'nav.container-botoes button, pje-botoes-transicao button, '
                'button[aria-label]')
            logger.error(
                '[NAVEGAÇÃO] Botão "Conclusão ao magistrado" não apareceu '
                '(tarefa "%s", URL=%s)',
                nome_tarefa, getattr(driver, 'current_url', ''))
            return False

        logger.info('[NAVEGAÇÃO] Botão "Conclusão ao magistrado" presente no DOM')

        # Angular é justamente o que causava o "refresh" visível.
        limpar_overlays(driver)

        if not safe_click_no_scroll(driver, botao):
            logger.error('[NAVEGAÇÃO] Falha ao clicar em "Conclusão ao magistrado"')
            return False

        logger.info('[NAVEGAÇÃO] ✅ Clique em "Conclusão ao magistrado" realizado')

        # componentes que o Angular estava abrindo (era o "refresh" visível

        if '/minutar' in (getattr(driver, 'current_url', '') or '').lower():
            logger.info('[NAVEGAÇÃO] Processo foi direto para /minutar')
            return True

        if espera.ate_aparecer(driver, 'pje-concluso-tarefa-botao button', teto=15):
            logger.info('[NAVEGAÇÃO] ✅ Na tela de conclusão (botões de conclusão ativos)')
            return True

        logger.error(
            '[NAVEGAÇÃO] Clique realizado, mas a tela de conclusão não apareceu. URL: %s',
            getattr(driver, 'current_url', ''))
        return False

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Erro na navegação para conclusão: {e}')
        return False


def preparar_campo_minutar(driver: Any) -> bool:
    """Prepara o campo de filtro de modelos na tela de minutar."""
    try:
        logger.info('[NAVEGAÇÃO] Preparando campo de filtro para minutar...')
        seletor_filtro = 'input#inputFiltro, input[id="inputFiltro"], pje-arvore-modelo-documento input, input[placeholder*="Filtro" i]'

        campo_filtro_modelo = espera.elemento(driver, seletor_filtro, teto=12)
        if not campo_filtro_modelo:
            campo_filtro_modelo = espera.ate_aparecer(driver, seletor_filtro, teto=5)

        if not campo_filtro_modelo:
            # Tolerância estrutural: se já estamos em /minutar ou o editor CKEditor já está presente,
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


def _dump_botoes_conclusao(driver: Any, seletor: str = (
        'pje-concluso-tarefa-botao button, '
        'pje-conclusao-dependencia button, '
        'button.mat-raised-button')) -> None:
    """Lista os botões da tela no log (só diagnóstico)."""
    try:
        if not hasattr(driver, 'page'):
            return
        dump = driver.page.evaluate("""(sel) => {
            function norm(s) { return (s || '').replace(/\\s+/g, ' ').trim(); }
            var out = [];
            var els = document.querySelectorAll(sel);
            for (var i = 0; i < els.length && out.length < 15; i++) {
                var b = els[i];
                out.push({
                    txt: norm(b.textContent).slice(0, 40),
                    aria: norm(b.getAttribute('aria-label')).slice(0, 40),
                    vis: (b.offsetWidth > 0 && b.offsetHeight > 0),
                    dis: !!b.disabled,
                    host: b.closest('pje-concluso-tarefa-botao') ? 'concluso' : (b.closest('pje-conclusao-dependencia') ? 'dependencia' : 'outro')
                });
            }
            return out;
        }""", seletor)
        logger.error('[CONCLUSÃO] Botões na tela no momento da falha: %s', dump)
    except Exception as e:
        logger.error('[CONCLUSÃO] Não foi possível listar os botões da tela: %s', e)


def escolher_tipo_conclusao(driver: Any, conclusao_tipo: str) -> bool:
    """Escolhe o tipo de conclusão na tela de conclusão do processo."""
    try:
        logger.info(f'[CONCLUSÃO] Escolhendo tipo de conclusão: {conclusao_tipo}')

        # Escopar ali é o que evita a isca: `pje-conclusao-dependencia` (lista
        botao = esperar_elemento(
            driver, 'pje-concluso-tarefa-botao button',
            texto=conclusao_tipo, timeout=15,
        )
        if botao is None:
            botao = esperar_elemento(driver, 'button', texto=conclusao_tipo, timeout=2)

        if botao is None and hasattr(driver, 'page'):
            script_find = """(tipo) => {
                function normalizar(s){ return (s||'').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().trim(); }
                var tipo_norm = normalizar(tipo);
                var candidatos = Array.prototype.slice.call(document.querySelectorAll(
                    'pje-concluso-tarefa-botao button, pje-conclusao-dependencia button, button.mat-raised-button'));
                function casa(btn) {
                    var txt = normalizar(btn.textContent);
                    if (txt === tipo_norm || txt.indexOf(tipo_norm) !== -1) return true;
                    var aria = normalizar(btn.getAttribute('aria-label'));
                    return aria.indexOf(tipo_norm) !== -1;
                }
                for (var i = 0; i < candidatos.length; i++) {
                    var btn = candidatos[i];
                    var txt = normalizar(btn.textContent);
                    var aria = normalizar(btn.getAttribute('aria-label'));
                    if (aria.indexOf('remover') !== -1 || aria.indexOf('fechar') !== -1 || aria.indexOf('excluir') !== -1) continue;
                    if (btn.disabled || !(btn.offsetWidth > 0 && btn.offsetHeight > 0)) continue;
                    if (!casa(btn)) continue;
                    btn.scrollIntoView({block:'center', behavior:'instant'});
                    btn.click();
                    return true;
                }
                return false;
            }"""
            fallback_ok = espera.ate(
                driver, lambda d: bool(d.page.evaluate(script_find, conclusao_tipo)), teto=10)
            if fallback_ok:
                logger.info(f'[CONCLUSÃO] ✅ Botão de conclusão "{conclusao_tipo}" clicado via busca ativa (despacho_engine / pre-refac)')
                return True

        if botao is None:
            logger.error(f'[CONCLUSÃO] Botão de conclusão "{conclusao_tipo}" não encontrado após 15s de espera '
                         f'(incluindo busca ativa do despacho_engine / pre-refac)')
            _dump_botoes_conclusao(driver)
            return False

        safe_click_no_scroll(driver, botao)
        logger.info(f'[CONCLUSÃO] ✅ Botão de conclusão "{conclusao_tipo}" clicado com sucesso')

        return True

    except Exception as e:
        logger.error(f'[CONCLUSÃO] Erro ao escolher tipo de conclusão: {e}')
        return False


def aguardar_transicao_minutar(driver: Any, timeout: float = 20.0) -> bool:
    """Aguarda a transição da tela de conclusão para a tela de minutar."""
    try:
        logger.info(f'[CONCLUSÃO] Aguardando transição para tela de minutar (teto={timeout}s)...')

        seletor_exclusivo_minutar = (
            'input#inputFiltro, input[id="inputFiltro"], '
            'pje-arvore-modelo-documento, div.ck-content[contenteditable="true"], '
            'div[class*="area-conteudo"]'
        )

        if '/minutar' in (getattr(driver, 'current_url', '') or '').lower():
            logger.info('[CONCLUSÃO] URL já em /minutar — transição imediata')
            return True

        transicionou = bool(aguardar_renderizacao_nativa(
            driver, seletor_exclusivo_minutar, modo='aparecer',
            timeout=max(6.0, float(timeout) * 0.6)))

        # 2. FALLBACK (URL): sinal lento do Angular, só se o DOM não veio.
        if not transicionou:
            logger.info('[CONCLUSÃO] DOM de minutar não renderizou — verificando URL /minutar como fallback...')
            transicionou = bool(esperar_url_conter(
                driver, '/minutar', timeout=max(5.0, float(timeout) * 0.4)))

        if not transicionou:
            logger.error(f'[CONCLUSÃO] Falha na transição para minutar após {timeout}s: URL={getattr(driver, "current_url", "")}')
            _dump_botoes_conclusao(driver)
            return False

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


_JS_MINUTA_PRONTA = """(() => {
    if (!location.href.toLowerCase().includes('/minutar')) return false;
    const vis = el => !!(el && el.getClientRects().length > 0);
    const filtro = document.querySelector('input#inputFiltro, pje-arvore-modelo-documento input');
    const abaModelos = Array.from(document.querySelectorAll('pje-editor-lateral div[role="tab"], pje-editor-lateral .mat-tab-label'))
        .find(t => (t.textContent || '').toLowerCase().includes('modelo'));
    const painelLateralPronto = (vis(filtro) && !filtro.disabled) || vis(abaModelos);
    if (!painelLateralPronto) return false;
    const eds = Array.from(document.querySelectorAll(
        'div[class*="area-conteudo"][contenteditable="true"], ' +
        'div[class*="area-conteudo"] div[contenteditable="true"], ' +
        'div.ck-content[contenteditable="true"]'
    )).filter(e => !e.closest('pje-dialogo-visualizar-modelo'));
    if (!eds.length) return false;
    const edPronto = eds.some(e => {
        if (!vis(e)) return false;
        const ck = e.ckeditorInstance;
        if (ck) return ck.state === 'ready' && !ck.isReadOnly;
        const salvar = document.querySelector('button[aria-label="Salvar"]');
        return vis(salvar);
    });
    if (!edPronto) return false;
    const spinEditor = document.querySelectorAll(
        'pje-editor-minuta mat-progress-spinner, pje-editor-minuta mat-progress-bar'
    );
    for (const s of spinEditor) {
        if (vis(s)) return false;
    }
    return true;
})()"""


def aguardar_minuta_pronta(driver: Any, timeout: float = 15.0) -> bool:
    """Aguarda a prontidão observável de `/minutar` após navegação direta (CLS-API).

    Confirma, em um único predicado JS (sem sleep cego e sem travar em spinners
    de fundo como a aba Documentos/timeline):
      1. URL em `/minutar`;
      2. `input#inputFiltro` visível e habilitado;
      3. CKEditor montado com `ckeditorInstance.state === 'ready'` e `!isReadOnly`
         (ou editor + botão Salvar visíveis);
      4. Sem spinner ativo dentro de `pje-editor-minuta`.
    """
    try:
        if espera.ate_js(driver, _JS_MINUTA_PRONTA, teto=timeout):
            logger.info('[CLS-API] ✅ Minuta pronta (editor ready + filtro ativo)')
            return True
        logger.warning('[CLS-API] Timeout (%.1fs) aguardando editor/filtro prontos em /minutar', timeout)
        return False
    except Exception as e:
        logger.warning('[CLS-API] Erro ao aguardar minuta pronta: %s', e)
        return False


def verificar_estado_atual(driver: Any) -> str:
    """Verifica o estado atual do processo baseado na URL."""
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
    """Foca no campo de filtro de modelos se estiver na tela de minutar."""
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