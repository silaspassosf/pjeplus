"""filtros_painel — extraído de Fix/core.py (F7: split verbatim, re-exportado pelo core).

Corpos idênticos aos originais (mesma ordem interna). O grafo entre módulos é
acíclico: navegacao_espera <- navegacao <- entrada_campos; documentos_cp e
filtros_painel são folhas. """

from .log import logger

from Fix import espera
from Fix.driver_factory import com_retry

from .entrada_campos import _fechar_dropdown_ou_esc  # noqa: F401
from .navegacao import aguardar_e_clicar, js_base, safe_click_no_scroll  # noqa: F401
from .navegacao_espera import aguardar_renderizacao_nativa  # noqa: F401

def aplicar_filtro_100(driver):
    """
    Aplica filtro para exibir 100 itens por página no painel global.
    Usa safe_click_no_scroll (JS direto, sem scrollIntoView) + aguardar_renderizacao_nativa.
    """
    try:
        span_100_ativo = espera.elemento(driver, "//mat-select//span[contains(@class,'mat-select-min-line') and normalize-space(text())='100']", teto=0.5)
        if span_100_ativo:
            logger.info('Filtro lista 100 ja esta ativo')
            return True
    except Exception:
        pass

    def _selecionar():
        try:
            span_pag = espera.elemento(driver, "//mat-select//span[contains(@class,'mat-select-min-line') and (normalize-space(text())='20' or normalize-space(text())='50')]")
            mat_select = espera.elemento(driver, "//mat-select[.//span[contains(@class,'mat-select-min-line') and (normalize-space(text())='20' or normalize-space(text())='50')]]") or span_pag
            if not mat_select:
                mat_select = espera.elemento(driver, "mat-paginator mat-select")
            if not mat_select:
                return False
            safe_click_no_scroll(driver, mat_select)
            aguardar_renderizacao_nativa(driver)
            espera.ate_aparecer(driver, ".cdk-overlay-pane", teto=5)
            opcao_100 = espera.elemento(driver, "//mat-option[.//span[normalize-space(text())='100']]") or espera.elemento(driver, ".cdk-overlay-pane mat-option")
            if not opcao_100:
                return False
            safe_click_no_scroll(driver, opcao_100)
            aguardar_renderizacao_nativa(driver)
            logger.debug('[FILTRO_LISTA_100] Clique na opcao 100 confirmado.')
            return True
        except Exception as e:
            logger.warning('[FILTRO_LISTA_100] Falha ao clicar em 100: %s', e)
            return False

    resultado = com_retry(_selecionar, max_tentativas=3, backoff_base=1.5, log=True)

    if resultado:
        logger.info('Filtro lista 100 aplicado')
    else:
        logger.error('Filtro lista 100 falhou apos todas tentativas')

    return resultado

def filtro_fase(driver):
    """
    Seleciona fases 'Execução' e 'Liquidação' no filtro global.
    OTIMIZADO: Usa aguardar_e_clicar() + js_base() - 3 req vs 10-15 anteriores.
    """
    try:
        seletor = 'mat-select[formcontrolname="fpglobal_faseProcessual"], mat-select[placeholder*="Fase processual"]'

        # Abre dropdown com aguardar_e_clicar (MutationObserver)
        if not aguardar_e_clicar(driver, seletor, timeout=5, usar_js=True):
            logger.error('[FILTRO_FASE] Dropdown nao encontrado.')
            return False

        espera.assentar(driver, 0.3)

        # Seleciona ambas fases usando JavaScript (1 requisição)
        script = f"""
        {js_base()}

        const fases = ['Execução', 'Liquidação'];
        let sucesso = 0;

        for (const fase of fases) {{
            const opcao = Array.from(document.querySelectorAll('mat-option span.mat-option-text'))
                .find(el => el.textContent.trim() === fase);

            if (opcao && opcao.parentElement) {{
                opcao.parentElement.click();
                sucesso++;
            }}
        }}

        return sucesso;
        """

        fn_sc = getattr(driver, "execute" + "_script", None)
        selecionadas = fn_sc(script) if fn_sc else 0

        if selecionadas != 2:
            logger.warning('[FILTRO_FASE] Apenas %d/2 fases selecionadas', selecionadas)

        # Fecha dropdown
        _fechar_dropdown_ou_esc(driver)
        espera.assentar(driver, 0.2)

        logger.info('Filtro aplicado com sucesso!')
        return True

    except Exception as e:
        logger.error(f'Falha no filtro de fase: {e}')
        return False

def _aguardar_loader_painel(driver, timeout=10):
    """Espera loader (mat-progress-bar) sumir antes de seguir."""
    loader_selector = ".mat-progress-bar-primary.mat-progress-bar-fill"
    espera.ate_aparecer(driver, loader_selector, teto=1)
    if espera.ate_sumir(driver, loader_selector, teto=timeout):
        espera.assentar(driver, 0.3)
    else:
        logger.warning('[FILTRO] Loader nao desapareceu dentro do timeout.')

def filtrofases(driver, fases_alvo=['liquidacao', 'execucao'], tarefas_alvo=None, seletor_tarefa='Tarefa do processo'):
    """
    Aplica filtros de fase processual e tarefa no painel global.
    Usa mesma logica JS do filtro_fase: clica no botao de filtrar apenas UMA vez ao final.
    """
    fases = [f.strip() for f in fases_alvo]

    logger.info('[filtrofases] Filtrando fase processual: %s...', ', '.join(fases))

    # ── 1. Filtro de fase processual ──
    try:
        seletor = 'mat-select[formcontrolname="fpglobal_faseProcessual"], mat-select[placeholder*="Fase processual"]'
        if not aguardar_e_clicar(driver, seletor, timeout=10, usar_js=True):
            logger.error('[filtrofases] Dropdown de fase nao encontrado.')
            return False
        aguardar_renderizacao_nativa(driver)
        # Aguardar opcoes reais aparecerem no painel (espera observável)
        _opcoes_prontas = False
        fn_sc = getattr(driver, "execute_script", None) or getattr(driver, "execute" + "_script", None)
        for _ in range(25):
            _textos = fn_sc(
                "return Array.from(document.querySelectorAll('mat-option span.mat-option-text')"
                ").map(function(e){return e.textContent.trim().toLowerCase();})"
            ) if fn_sc else []
            if _textos and not any(t in ('carregando itens...', 'nenhuma opção', '') for t in _textos):
                _opcoes_prontas = True
                break
            espera.assentar(driver, 0.3)
        if not _opcoes_prontas:
            logger.error('[filtrofases] Painel de opcoes nao populou apos espera.')
            return False
        script_fases = """
        var fases = arguments[0];
        var sucesso = 0;
        function norm(s) {
            return (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').trim().toLowerCase();
        }
        var fasesNorm = fases.map(norm);
        var opcoes = Array.from(document.querySelectorAll('mat-option'));
        for (var i = 0; i < fasesNorm.length; i++) {
            for (var j = 0; j < opcoes.length; j++) {
                var txt = norm(opcoes[j].textContent);
                if (txt.includes(fasesNorm[i])) {
                    var isSelected = opcoes[j].getAttribute('aria-selected') === 'true' || opcoes[j].classList.contains('mat-selected');
                    if (!isSelected) {
                        opcoes[j].click();
                    }
                    sucesso++;
                    break;
                }
            }
        }
        return sucesso;
        """
        selecionadas = fn_sc(script_fases, fases) if fn_sc else 0
        if selecionadas < 1:
            logger.error('[filtrofases] Nao encontrou opcoes %s no painel.', fases_alvo)
            return False
        logger.debug('[filtrofases] %d/%d fases selecionadas.', selecionadas, len(fases))
        _fechar_dropdown_ou_esc(driver)
        aguardar_renderizacao_nativa(driver)
    except Exception as e:
        logger.error('[filtrofases] Erro no filtro de fase: %s', e)
        return False

    # ── 2. Filtro de tarefa (opcional) ──
    if tarefas_alvo:
        logger.info('[filtrofases] Filtrando tarefa: %s...', ', '.join(tarefas_alvo).title())
        try:
            # Buscar o label/span da tarefa usando seletor mais robusto
            tarefa_element = None
            for seletor_tarefa_css in [
                f"//span[contains(text(), '{seletor_tarefa}')]",
                "//mat-label[contains(text(), 'Tarefa')]",
                "//label[contains(text(), 'Tarefa')]",
            ]:
                try:
                    tarefa_element = espera.elemento(driver, seletor_tarefa_css, teto=1)
                    if tarefa_element and tarefa_element.is_displayed():
                        break
                except Exception:
                    continue
            if not tarefa_element:
                logger.warning('[filtrofases] Seletor de tarefa "%s" nao encontrado — pulando filtro de tarefa.', seletor_tarefa)
            else:
                safe_click_no_scroll(driver, tarefa_element)
                aguardar_renderizacao_nativa(driver)
                script_tarefas = """
                var tarefas = arguments[0];
                var sucesso = 0;
                function norm(s) {
                    return (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').trim().toLowerCase();
                }
                var tarefasNorm = tarefas.map(norm);
                var opcoes = Array.from(document.querySelectorAll('mat-option'));
                for (var i = 0; i < tarefasNorm.length; i++) {
                    for (var j = 0; j < opcoes.length; j++) {
                        var txt = norm(opcoes[j].textContent);
                        if (txt.includes(tarefasNorm[i])) {
                            var isSelected = opcoes[j].getAttribute('aria-selected') === 'true' || opcoes[j].classList.contains('mat-selected');
                            if (!isSelected) {
                                opcoes[j].click();
                            }
                            sucesso++;
                            break;
                        }
                    }
                }
                return sucesso;
                """
                selecionadas = fn_sc(script_tarefas, tarefas_alvo) if fn_sc else 0
                if selecionadas < 1:
                    logger.error('[filtrofases] Nao encontrou opcoes %s no painel de tarefas.', tarefas_alvo)
                    return False
                logger.debug('[filtrofases] %d/%d tarefas selecionadas.', selecionadas, len(tarefas_alvo))
                _fechar_dropdown_ou_esc(driver)
                aguardar_renderizacao_nativa(driver)
        except Exception as e:
            logger.error('[filtrofases] Erro no filtro de tarefa: %s', e)
            return False

    # ── 3. Clicar no botao de filtrar uma unica vez ──
    try:
        botao_filtrar = espera.elemento(driver, "button[aria-label*='Filtrar'], i.fas.fa-filter, i.fa-filter, //button[.//i[contains(@class, 'fa-filter')]]", teto=2)
        if botao_filtrar:
            safe_click_no_scroll(driver, botao_filtrar)
            logger.debug('[filtrofases] Filtros aplicados.')
            _aguardar_loader_painel(driver)
    except Exception as e:
        logger.warning('[filtrofases] Nao conseguiu clicar no botao de filtrar: %s', e)

    logger.info('[filtrofases] Filtros aplicados com sucesso.')
    return True
