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
    navegar_para_tarefa,
    _normalizar_texto,
)


def _localizar_botao_navegacao(driver: Any, label: str):
    """Localiza botão de navegação de tarefa via estratégias combinadas (case/accent-insensitive).

    Mantido como utilidade de diagnóstico: o caminho de navegação usa
    diretamente o seletor por aria-label (ver navegar_para_conclusao).
    """
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

    Premissa do PJe (não é caso a tratar): em "Aguardando prazo" a Conclusão ao
    Magistrado SEMPRE existe. Portanto não há desvio para "Análise" -- o único
    problema possível é a página da tarefa não ter carregado.

    Estratégia:
    1. Se já está em Conclusão/minutar, nada a fazer.
    2. Se a tarefa já é a própria Conclusão ao Magistrado, nada a fazer.
    3. Aguarda o BOTÃO REAL aparecer (seletor por aria-label, teto 15s --
       mesmo padrão de esperarColecao('pje-botoes-transicao button', 15) do
       gigs-plugin). Esta é a estabilização: esperar pelo esqueleto da aba
       (pje-cabecalho-tarefa / pje-botoes-transicao button) não garante nada,
       porque ambos já existem antes de a tarefa montar.
    4. Clica no botão.
    5. Confirma a chegada pelos botões de conclusão. Só retorna True se eles
       existirem de fato -- retorno otimista escondia a falha e fazia o erro
       aparecer só no passo seguinte, como se fosse problema do CLS.

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

        # ===== ESTABILIZAÇÃO DA PÁGINA =====
        # A tarefa abre numa aba nova e o Angular monta o DOM depois do
        # esqueleto. As esperas anteriores observavam `pje-cabecalho-tarefa` e
        # `pje-botoes-transicao button`, ambos presentes JÁ no esqueleto, então
        # retornavam na hora e a busca saía antes de o botão existir.
        # Aqui esperamos o botão real pelo aria-label, como faz o gigs-plugin
        # (esperarColecao('pje-botoes-transicao button', 15)).
        aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', modo='aparecer', timeout=15)

        SELETOR_CONCLUSAO = (
            "button[aria-label*='Conclusão ao magistrado' i], "
            "pje-botoes-transicao button[aria-label*='Conclusão ao magistrado' i]"
        )

        # ===== ROTEAMENTO PELO ESTADO DA TAREFA =====
        # Em "Aguardando prazo" a Conclusão ao Magistrado SEMPRE existe: é regra
        # do próprio PJe. O botão é procurado direto, sem passar por Análise.
        # Os demais fluxos (ex.: Cumprimento de Providências) realmente pedem
        # Análise antes da conclusão -- esse roteamento já existe pronto em
        # navegar_para_tarefa (máquina de estados do gigs-plugin) e é usado em
        # vez de recriá-lo aqui.
        tarefa_direta = 'aguardando prazo' in tarefa_norm

        if tarefa_direta:
            logger.info('[NAVEGAÇÃO] Tarefa "Aguardando prazo": conclusão direta ao magistrado')
            btn_conclusao = espera.elemento(driver, SELETOR_CONCLUSAO, teto=15)
            if not btn_conclusao:
                logger.error(
                    '[NAVEGAÇÃO] Botão "Conclusão ao magistrado" não apareceu em 15s '
                    '(tarefa "%s", URL=%s) -- a página da tarefa não carregou',
                    nome_tarefa, getattr(driver, 'current_url', ''))
                return False
        else:
            logger.info('[NAVEGAÇÃO] Tarefa "%s": roteando via máquina de estados (Análise se necessário)', nome_tarefa)
            if not navegar_para_tarefa(driver, 'conclusão ao magistrado', debug=True, tarefa_atual_conhecida=nome_tarefa):
                # navegar_para_tarefa já moveu para Análise; aqui só falta clicar
                logger.info('[NAVEGAÇÃO] Roteamento não concluiu — tentando o botão na tela atual')
            btn_conclusao = espera.elemento(driver, SELETOR_CONCLUSAO, teto=15)
            if not btn_conclusao:
                logger.error(
                    '[NAVEGAÇÃO] Botão "Conclusão ao magistrado" não apareceu em 15s '
                    '(tarefa "%s", URL=%s)',
                    nome_tarefa, getattr(driver, 'current_url', ''))
                return False

        logger.info('[NAVEGAÇÃO] Botão "Conclusão ao magistrado" presente no DOM')

        # Qualquer overlay pendente sobre os botões de transição impediria o clique
        limpar_overlays(driver)

        logger.info('[NAVEGAÇÃO] Clicando em "Conclusão ao magistrado"...')
        if not safe_click_no_scroll(driver, btn_conclusao):
            logger.error('[NAVEGAÇÃO] Falha ao clicar em "Conclusão ao magistrado"')
            return False
        logger.info('[NAVEGAÇÃO] ✅ Clique em "Conclusão ao magistrado" realizado')

        limpar_overlays(driver)

        # ===== CONFIRMAÇÃO DA CHEGADA =====
        # Sucesso só quando os botões de conclusão existem de fato. Antes, esta
        # função retornava True mesmo sem ter navegado, e o erro aparecia só no
        # Passo 4 ("Botão de conclusão 'Despacho' não encontrado"), escondendo
        # a causa real.
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