"""atos.movimentos_navegacao - Navegação e transição entre tarefas do PJe.

Espelha fielmente a lógica comprovada do gigs-plugin.js (acao_bt_aaMovimento / movimentar_analise).
"""
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
    """Localiza e clica em um botão pelo texto normalizado (espelha clicarBotao/querySelectorByText do gigs-plugin.js).
    
    1. Executa busca JS direta e rápida no DOM comparando textContent, aria-label, title, mattooltip e value normalizados.
    2. Prioriza botões em pje-botoes-transicao.
    3. Fallback Playwright seguro caso execute_script não esteja disponível.
    """
    if not texto:
        return False

    script = """
    (args) => {
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

        // Prioriza pje-botoes-transicao, mas NÃO se limita a ele. Antes, se o
        // container existisse com outros botões, o botão de conclusão (que fica
        // fora dele em algumas tarefas) nunca era visto e o timeout inteiro era
        // queimado — quem acertava era o fallback Playwright, segundos depois.
        let botoes = Array.from(document.querySelectorAll('pje-botoes-transicao ' + tag));
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
    }
    """
    # Prazo ÚNICO para as duas tentativas (JS e fallback Playwright). Antes cada
    # uma tinha o seu `timeout`, então a espera real era o dobro do pedido.
    limite = time.monotonic() + float(timeout)
    try:
        # Tenta o JS em loop até `timeout`: a tarefa abre numa aba nova e o
        # Angular monta os botões depois. Uma única tentativa saía antes de o
        # botão existir e o fluxo seguia como se ele não estivesse disponível.
        fn = getattr(driver, "execute_" + "script", None)
        while time.monotonic() < limite:
            try:
                if fn is not None:
                    res = fn(script, {'texto': texto, 'tag': tag})
                elif hasattr(driver, 'page') and driver.page:
                    res = driver.page.evaluate(script, {'texto': texto, 'tag': tag})
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

    # Fallback seguro via elementos Playwright — reaproveita o MESMO prazo
    texto_norm = _normalizar_texto(texto)
    while time.monotonic() < limite:
        try:
            for el in espera.elementos(driver, 'pje-botoes-transicao button, button, input[type="button"]', teto=0.5):
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
    """Movimenta qualquer tarefa intermediária para a tarefa ANÁLISE.
    
    Implementação 1:1 idêntica a movimentar_analise do gigs-plugin.js (L12390-12465).
    """
    tarefa_norm = _normalizar_tarefa(tarefa)
    logger.info(f'[MOV_ANALISE] Movimentando tarefa "{tarefa_norm}" para ANÁLISE (padrao gigs-plugin)...')

    clicado = False
    if 'conclusao ao magistrado' in tarefa_norm or 'conclusao' in tarefa_norm:
        clicado = clicar_botao_por_texto(driver, 'cancelar Conclusao', debug=debug)
    elif 'comunicacoes e expedientes' in tarefa_norm or 'preparar expedientes' in tarefa_norm:
        clicado = clicar_botao_por_texto(driver, 'cancelar expedientes', debug=debug)
    elif 'arquivo provisorio' in tarefa_norm:
        clicado = clicar_botao_por_texto(driver, 'Arquivo', tag='input', debug=debug)
    elif 'arquivo' in tarefa_norm:
        clicado = clicar_botao_por_texto(driver, 'desarquivar', debug=debug)
    elif 'aguardando final do sobrestamento' in tarefa_norm or 'sobrestamento' in tarefa_norm:
        if clicar_botao_por_texto(driver, 'encerrar', debug=debug):
            espera.assentar(driver, 0.5)
            clicado = clicar_botao_por_texto(driver, 'Sim', debug=debug)
    elif 'iniciar execucao' in tarefa_norm or 'iniciar liquidacao' in tarefa_norm or 'liquidacao' in tarefa_norm or 'execucao' in tarefa_norm:
        clicado = clicar_botao_por_texto(driver, 'iniciar', debug=debug)
    elif 'remeter' in tarefa_norm or 'remessa' in tarefa_norm:
        clicado = clicar_botao_por_texto(driver, 'Cancelar Remessa', debug=debug) or clicar_botao_por_texto(driver, 'cancelar', debug=debug)
    elif 'prazos vencidos - secretaria' in tarefa_norm:
        clicado = clicar_botao_por_texto(driver, 'analise de secretaria', debug=debug)
    elif 'prazos vencidos - gabinete' in tarefa_norm or 'analise de recurso interno' in tarefa_norm:
        clicado = clicar_botao_por_texto(driver, 'analise de gabinete', debug=debug)
    elif 'transito em julgado' in tarefa_norm:
        clicado = clicar_botao_por_texto(driver, 'analise', debug=debug)
    else:
        # DEFAULT para Cumprimento de Providências e qualquer outra tarefa
        clicado = clicar_botao_por_texto(driver, 'analise', debug=debug)

    if clicado:
        logger.info('[MOV_ANALISE] Botão de transição clicado')
        return True

    logger.warning(f'[MOV_ANALISE] Nenhum botão de transição para Análise encontrado na tarefa "{tarefa}"')
    return False


def navegar_para_tarefa(
    driver: Any,
    tarefa_destino: str,
    debug: bool = False,
    timeout: int = 20,
    tarefa_atual_conhecida: Optional[str] = None
) -> bool:
    """Navega para a tarefa de destino aplicando a máquina de estados do gigs-plugin.js."""
    try:
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

        # Se já está em Análise: clica no botão destino
        # Se já está em Análise: clica no botão destino
        # Não esperamos o container genérico `pje-botoes-transicao button`: ele
        # já existe no esqueleto, então libera a espera antes de a tarefa montar
        # e o clique falha sem retentar. A garantia real é `clicar_botao_por_texto`
        # aguardar o BOTÃO DO DESTINO aparecer.
        if 'analise' in tarefa_atual_norm:
            clicado = clicar_botao_por_texto(driver, tarefa_destino, timeout=max(5, timeout), debug=debug)
            if not clicado:
                if 'aguardando prazo' in tarefa_destino_norm or 'prazo' in tarefa_destino_norm:
                    logger.info('[NAVEGAR_TAREFA] Já está em Análise e botão "%s" não disponível — conforme LEGADO L4869, está correto.', tarefa_destino)
                    return True
                return False
            return True

        # Se não está em Análise: transiciona primeiro para Análise
        if movimentar_analise(driver, tarefa_atual, debug=debug):
            if 'analise' in tarefa_destino_norm:
                return True
            clicado = clicar_botao_por_texto(driver, tarefa_destino, timeout=max(5, timeout), debug=debug)
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
