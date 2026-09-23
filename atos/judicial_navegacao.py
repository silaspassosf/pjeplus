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


def _localizar_botao_navegacao(driver: Any, label: str):
    """Localiza botão de navegação de tarefa via estratégias combinadas."""
    seletor = (
        f"button[aria-label='{label}'], "
        f"button[aria-label*='{label}'], "
        f"//button[.//span[normalize-space(text())='{label}']]"
    )
    return espera.elemento(driver, seletor, teto=2)


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
            tarefa_lower = tarefa_do_botao.lower()
            if 'assinar' in tarefa_lower or 'minutar' in tarefa_lower:
                logger.info(f'[NAVEGAÇÃO] ⏭ Tarefa "{tarefa_do_botao}" em minutar/assinar — ato pronto, sem ação')
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

    Estratégia:
    1. Tenta clicar diretamente em "Conclusão ao Magistrado"
    2. Se não disponível, clica em "Análise" primeiro, remove overlays, depois clica em "Conclusão ao Magistrado"
    3. Aguarda o elemento da próxima tela (botões de tipo de conclusão) — não a URL,
       que não é um sinal confiável dessa transição (mesmo padrão do gigs-plugin.js)

    Returns:
        bool: True se conseguiu navegar para conclusão
    """
    try:
        logger.info('[NAVEGAÇÃO] Navegando para Conclusão ao Magistrado...')

        # Obter nome da tarefa se disponível (do DOM ou do driver salvo anteriormente)
        nome_tarefa = getattr(driver, 'pje_tarefa_atual', '').lower()
        if not nome_tarefa:
            try:
                h1 = espera.elementos(driver, "pje-cabecalho-tarefa h1.titulo-tarefa, span.texto-tarefa-processo", teto=1)
                if h1:
                    nome_tarefa = (getattr(h1[0], 'text', '') or '').strip().lower()
            except Exception:
                pass

        logger.info(f'[NAVEGAÇÃO] Nome da Tarefa Detectado: "{nome_tarefa}"')

        if not (
            espera.elemento(driver, "button[aria-label='Análise'], button[aria-label*='Análise']", teto=5)
            or espera.elemento(driver, "button[aria-label='Conclusão ao magistrado'], button[aria-label*='Conclusão ao magistrado']", teto=5)
        ):
            logger.error('[NAVEGAÇÃO] Botões de navegação não apareceram no DOM')
            return False

        btn_conclusao_encontrado = False

        # Tentar clique direto em "Conclusão ao magistrado" independente do tipo de tarefa.
        btn_conclusao_direto = _localizar_botao_navegacao(driver, 'Conclusão ao magistrado')
        if btn_conclusao_direto and getattr(btn_conclusao_direto, 'is_displayed', lambda: True)() and safe_click_no_scroll(driver, btn_conclusao_direto):
            btn_conclusao_encontrado = True
            logger.info('[NAVEGAÇÃO] Clique direto em "Conclusão ao magistrado" realizado')
        else:
            logger.info('[NAVEGAÇÃO] Conclusão não disponível diretamente, tentando via "Análise"...')

        # Se não encontrou, usar estratégia via "Análise"
        if not btn_conclusao_encontrado:
            logger.info('[NAVEGAÇÃO] Tentando via "Análise"...')
            btn_analise = _localizar_botao_navegacao(driver, 'Análise')
            if btn_analise and safe_click_no_scroll(driver, btn_analise):
                logger.info('[NAVEGAÇÃO] Clique em "Análise" realizado')
            else:
                logger.error('[NAVEGAÇÃO] Falha ao clicar em "Análise": botão não encontrado no DOM')

        # Remover overlays após Análise se houver
        logger.info('[NAVEGAÇÃO] Verificando overlays...')
        try:
            overlays = espera.elementos(driver, '.cdk-overlay-backdrop-showing', teto=1)
            if overlays:
                if hasattr(driver, 'page'):
                    driver.page.keyboard.press("Escape")
                else:
                    safe_click_no_scroll(driver, 'body')
                aguardar_renderizacao_nativa(driver, '.cdk-overlay-backdrop-showing', modo='sumir', timeout=2)
        except Exception:
            pass

        # Aguardar renderização e clicar na conclusão
        if not btn_conclusao_encontrado:
            seletor_conclusao = "button[aria-label='Conclusão ao magistrado'], button[aria-label*='Conclusão ao magistrado']"
            aguardar_renderizacao_nativa(driver, seletor_conclusao, 'aparecer', timeout=8)
            btn_conclusao = _localizar_botao_navegacao(driver, 'Conclusão ao magistrado')
            if not btn_conclusao or not safe_click_no_scroll(driver, btn_conclusao):
                logger.error('[NAVEGAÇÃO] Falha na navegação via Análise: botão "Conclusão ao magistrado" não encontrado após aguardar renderização')
                return False
            logger.info('[NAVEGAÇÃO] Clique em "Conclusão ao magistrado" realizado após Análise')

        current_after = (driver.current_url or '').lower()
        if '/minutar' in current_after:
            logger.info('[NAVEGAÇÃO] Processo foi direto para /minutar')
            return True

        if not aguardar_renderizacao_nativa(driver, 'pje-concluso-tarefa-botao button', 'aparecer', timeout=10):
            logger.error(f'[NAVEGAÇÃO] Botões de conclusão não apareceram. URL atual: {driver.current_url}')
            return False

        logger.info('[NAVEGAÇÃO] Navegação para conclusão concluída com sucesso')
        return True

    except Exception as e:
        logger.error(f'[NAVEGAÇÃO] Erro na navegação para conclusão: {e}')
        return False


def preparar_campo_minutar(driver: Any) -> bool:
    """
    Prepara o campo de filtro de modelos na tela de minutar.

    Returns:
        bool: True se conseguiu preparar o campo
    """
    try:
        logger.info('[NAVEGAÇÃO] Preparando campo de filtro para minutar...')

        campo_filtro_modelo = espera.elemento(driver, 'input#inputFiltro', teto=10)
        if not campo_filtro_modelo:
            raise Exception('input#inputFiltro não apareceu')

        if hasattr(driver, 'page'):
            driver.page.evaluate("""() => {
                var el = document.querySelector('input#inputFiltro');
                if (el) {
                    el.removeAttribute('disabled');
                    el.removeAttribute('readonly');
                    el.value = '';
                    el.focus();
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('keyup', {bubbles: true}));
                }
            }""")
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


def aguardar_transicao_minutar(driver: Any) -> bool:
    """
    Aguarda a transição da tela de conclusão para a tela de minutar.
    Usando a lógica do gigs-plugin: observa o DOM (pje-arvore-modelo-documento)
    que é muito mais rápido e confiável que o polling de URL no Angular.

    Returns:
        bool: True se conseguiu fazer a transição
    """
    try:
        logger.info('[CONCLUSÃO] Aguardando transição para tela de minutar (DOM Observer)...')
        from Fix.core import esperar_url_conter

        try:
            if aguardar_renderizacao_nativa(driver, 'pje-arvore-modelo-documento', modo='aparecer', timeout=10):
                logger.info('[CONCLUSÃO] Transição detectada via renderização do DOM (pje-arvore-modelo-documento)')
                return True
        except Exception as e:
            logger.warning(f'[CONCLUSÃO] Fallback: Falha no observer do DOM: {e}')

        logger.info('[CONCLUSÃO] Verificando URL /minutar como fallback...')
        if not esperar_url_conter(driver, '/minutar', timeout=10):
            logger.error(f'[CONCLUSÃO] Falha na transição para minutar: DOM não renderizou e URL não mudou: {driver.current_url}')
            return False

        logger.info('[CONCLUSÃO] Transição para minutar concluída via URL fallback')
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
            campo_filtro_modelo = espera.elemento(driver, 'input#inputFiltro', teto=10)
            if not campo_filtro_modelo:
                raise Exception('input#inputFiltro não apareceu')
            if hasattr(driver, 'page'):
                driver.page.evaluate("() => { const el = document.querySelector('input#inputFiltro'); if (el) el.focus(); }")
            else:
                preencher_campo(driver, 'input#inputFiltro', '')
            logger.info('[CONCLUSÃO] Foco no campo #inputFiltro realizado')
        return True
    except Exception as e:
        logger.warning(f'[CONCLUSÃO] Erro ao focar campo minutar: {e}')
        return False