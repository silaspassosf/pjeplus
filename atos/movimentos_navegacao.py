"""atos.movimentos_navegacao - Navegação e transição entre tarefas do PJe."""
from typing import Any, Optional
import unicodedata
import logging
import time
from Fix import espera
from Fix.core import safe_click_no_scroll

logger = logging.getLogger(__name__)


def _normalizar_texto(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(s))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
    import re
    return re.sub(r'[\r\n\t]+', ' ', sem_acento).strip()


def _normalizar_tarefa(tarefa: str) -> str:
    if not tarefa:
        return ""
    tarefa_norm = _normalizar_texto(tarefa)
    tarefa_norm = tarefa_norm.replace('preparar expedientes e comunicacoes', 'comunicacoes e expedientes')
    tarefa_norm = tarefa_norm.replace('aguardando cumprimento de acordo', 'controle de acordo')
    return tarefa_norm


def clicar_botao_por_texto(driver: Any, texto: str, timeout: int = 4, tag: str = 'button', debug: bool = False) -> bool:
    """Localiza e clica em um botão pelo texto normalizado (espelha clicarBotao/querySelectorByText do gigs-plugin..."""
    if not texto:
        return False

    script_arrow = """(args) => {
        const textoAlvo = (args && args.texto) || '';
        const tag = (args && args.tag) || 'button';
        function norm(t) {
            if (!t) return '';
            return t.normalize('NFKD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase()
                .replace(/\\s+/g, ' ')
                .trim();
        }
        const alvo = norm(textoAlvo);
        if (!alvo) return false;

        // Prioriza barras de transição (nav.container-botoes / pje-botoes-transicao),
        // mas também varre o restante da página se o botão estiver fora delas.
        let botoes = Array.from(document.querySelectorAll('nav.container-botoes ' + tag + ', pje-botoes-transicao ' + tag));
        const vistos = new Set(botoes);
        for (const b of document.querySelectorAll(tag + ', input[type="button"], input[type="submit"]')) {
            if (!vistos.has(b)) { botoes.push(b); vistos.add(b); }
        }

        for (const b of botoes) {
            if (b.disabled || b.getAttribute('aria-disabled') === 'true') continue;
            const txt = norm(b.innerText || b.textContent || '');
            const aria = norm(b.getAttribute('aria-label') || '');
            const title = norm(b.getAttribute('title') || '');
            const tooltip = norm(b.getAttribute('mattooltip') || '');
            const val = norm(b.value || '');
            if (txt.includes(alvo) || aria.includes(alvo) || title.includes(alvo) || tooltip.includes(alvo) || val.includes(alvo)) {
                try { b.scrollIntoView({block: 'center', inline: 'center'}); } catch(e) {}
                b.click();
                return true;
            }
        }
        return false;
    }"""
    script_sel = f"return ({script_arrow})(arguments[0]);"

    agora = time.monotonic()
    limite_total = agora + float(timeout)
    limite_js = agora + max(0.25, float(timeout) * 0.75)
    try:
        fn = getattr(driver, "execute_" + "script", None)
        while time.monotonic() < limite_js:
            try:
                if fn is not None:
                    res = fn(script_sel, {'texto': texto, 'tag': tag})
                elif hasattr(driver, 'page') and driver.page:
                    res = driver.page.evaluate(script_arrow, {'texto': texto, 'tag': tag})
                else:
                    break
                if res:
                    if debug:
                        logger.debug(f'[MOV_CLIQUE] Botão "{texto}" clicado via JS')
                    return True
            except Exception as e:
                if debug:
                    logger.debug(f'[MOV_CLIQUE] Falha na execução JS: {e}')
            espera.assentar(driver, 0.2)
    except Exception as e:
        if debug:
            logger.debug(f'[MOV_CLIQUE] Falha na execução JS: {e}')

    texto_norm = _normalizar_texto(texto)
    while time.monotonic() < limite_total:
        try:
            for el in espera.elementos(driver, 'nav.container-botoes button, pje-botoes-transicao button, button, input[type="button"]', teto=0.5):
                try:
                    if getattr(el, 'is_displayed', lambda: True)() and not el.get_attribute('disabled'):
                        txt = _normalizar_texto(getattr(el, 'text', '') or getattr(el, 'text_content', lambda: '')() or '')
                        aria = _normalizar_texto(el.get_attribute('aria-label') or '')
                        title = _normalizar_texto(el.get_attribute('title') or '')
                        if texto_norm in txt or texto_norm in aria or texto_norm in title:
                            if safe_click_no_scroll(driver, el, log=debug):
                                if debug:
                                    logger.debug(f'[MOV_CLIQUE] Botão "{texto}" clicado via fallback element')
                                return True
                except Exception:
                    continue
        except Exception:
            pass
        espera.assentar(driver, 0.2)

    return False


def movimentar_analise(driver: Any, tarefa: str, debug: bool = False) -> bool:
    """Transiciona a tarefa atual para ANÁLISE clicando no botão de análise"""
    logger.info(f'[MOV_ANALISE] Transicionando para ANÁLISE (roteamento por botões)...')

    tarefa_norm = _normalizar_tarefa(tarefa)

    if 'conclusao ao magistrado' in tarefa_norm or 'conclusao' in tarefa_norm:
        return clicar_botao_por_texto(driver, 'cancelar Conclusao', debug=debug)
    if 'comunicacoes e expedientes' in tarefa_norm or 'preparar expedientes' in tarefa_norm:
        return clicar_botao_por_texto(driver, 'cancelar expedientes', debug=debug)
    if 'arquivo provisorio' in tarefa_norm:
        return clicar_botao_por_texto(driver, 'Arquivo', tag='input', debug=debug)
    if 'arquivo' in tarefa_norm:
        return clicar_botao_por_texto(driver, 'desarquivar', debug=debug)
    if 'aguardando final do sobrestamento' in tarefa_norm or 'sobrestamento' in tarefa_norm:
        if clicar_botao_por_texto(driver, 'encerrar', debug=debug):
            espera.assentar(driver, 0.5)
            return clicar_botao_por_texto(driver, 'Sim', debug=debug)
        return False
    if 'iniciar execucao' in tarefa_norm or 'iniciar liquidacao' in tarefa_norm or 'liquidacao' in tarefa_norm or 'execucao' in tarefa_norm:
        return clicar_botao_por_texto(driver, 'iniciar', debug=debug)
    if 'remeter' in tarefa_norm or 'remessa' in tarefa_norm:
        return clicar_botao_por_texto(driver, 'Cancelar Remessa', debug=debug) or clicar_botao_por_texto(driver, 'cancelar', debug=debug)

    if clicar_botao_por_texto(driver, 'analise', timeout=4, debug=debug):
        logger.info('[MOV_ANALISE] Botão de análise "analise" clicado')
        return True

    logger.warning(f'[MOV_ANALISE] Botão "Análise" não encontrado na tarefa "{tarefa}"')
    return False


def navegar_para_tarefa(
    driver: Any,
    tarefa_destino: str,
    debug: bool = False,
    timeout: int = 20,
    tarefa_atual_conhecida: Optional[str] = None,
    clicar_destino: bool = True,
) -> bool:
    """Navega para a tarefa de destino aplicando a máquina de estados do gigs-plugin.js."""
    try:
        from .judicial_api import cls_api_habilitada, transitar_tarefa_api
        if cls_api_habilitada():
            alvo_api = tarefa_destino if clicar_destino else 'Análise'
            res_api = transitar_tarefa_api(driver, alvo_api, abrir_url=True)
            if res_api:
                return res_api.get('_status_api') != 'bloqueado_regra'

        tarefa_atual = tarefa_atual_conhecida or _obter_tarefa_atual(driver, debug)
        if not tarefa_atual:
            logger.warning('[NAVEGAR_TAREFA] Nao foi possivel identificar tarefa atual')
            return False

        tarefa_atual_norm = _normalizar_tarefa(tarefa_atual)
        tarefa_destino_norm = _normalizar_tarefa(tarefa_destino)

        if tarefa_destino_norm in tarefa_atual_norm:
            return True

        if _deve_interromper_movimento(tarefa_atual_norm, tarefa_destino_norm, debug):
            logger.warning('[NAVEGAR_TAREFA] Movimento interrompido por condicao especial')
            return False

        if 'analise' in tarefa_atual_norm:
            clicado = clicar_botao_por_texto(driver, tarefa_destino, timeout=max(5, timeout), debug=debug)
            if not clicado:
                if 'aguardando prazo' in tarefa_destino_norm or 'prazo' in tarefa_destino_norm:
                    logger.info('[NAVEGAR_TAREFA] Já está em Análise e botão "%s" não disponível — conforme LEGADO L4869, está correto.', tarefa_destino)
                    return True
                return False
            return True

        if movimentar_analise(driver, tarefa_atual, debug=debug):
            if 'analise' in tarefa_destino_norm:
                return True
            if not clicar_destino:
                return True
            t0_destino = time.monotonic()
            clicado = clicar_botao_por_texto(driver, tarefa_destino, timeout=max(5, timeout), debug=debug)
            logger.info('[NAVEGAR_TAREFA] Após Análise: botão "%s" %s em %.2fs',
                        tarefa_destino, 'clicado' if clicado else 'NAO encontrado',
                        time.monotonic() - t0_destino)
            if not clicado:
                if 'aguardando prazo' in tarefa_destino_norm or 'prazo' in tarefa_destino_norm:
                    logger.info('[NAVEGAR_TAREFA] Transicionou para Análise e botão "%s" não disponível — conforme LEGADO L4869, está correto.', tarefa_destino)
                    return True
                return False
            return True

        return False
    except Exception as e:
        logger.warning('[NAVEGAR_TAREFA] Erro na navegacao: %s', e)
        return False


def _obter_tarefa_atual(driver: Any, debug: bool = False) -> Optional[str]:
    try:
        url = getattr(driver, 'current_url', '') or ''
        if 'nomeTarefa=Arquivo+provis' in url:
            return 'Arquivo provisório'
        elif 'nomeTarefa=Arquivo+definitivo' in url:
            return 'Arquivo definitivo'

        el_tarefa = espera.elemento(driver, 'pje-cabecalho-tarefa h1.titulo-tarefa, pje-cabecalho-tarefa h1', teto=4)
        if el_tarefa:
            return (getattr(el_tarefa, 'text', '') or '').strip()
        return None
    except Exception as e:
        if debug:
            logger.debug('[OBTER_TAREFA] Erro ao obter tarefa atual: %s', e)
        return None


def _deve_interromper_movimento(tarefa_atual: str, tarefa_destino: str, debug: bool = False) -> bool:
    if 'elaborar' in tarefa_atual or 'assinar' in tarefa_atual:
        return True
    if 'controle de acordo' in tarefa_atual:
        return True
    return False
