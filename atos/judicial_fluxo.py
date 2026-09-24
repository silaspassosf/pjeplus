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
from Fix.utils import executar_coleta_parametrizavel, inserir_link_ato_validacao
from Fix.extracao import bndt, criar_gigs
from Fix.movimento_helpers import selecionar_movimento_auto
import time
import logging

from typing import Optional, Tuple, Dict, List, Union, Callable, Any
from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario
from .core import verificar_carregamento_pagina, aguardar_e_verificar_aba

# Importações dos módulos especializados
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
from .judicial_modelos import (
    esperar_insercao_modelo,
)
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
    '''
    Fluxo principal para CLS (Conclusão ao Magistrado → Minutar).

    Garantia: sempre chega em Conclusão ao Magistrado, independente da tarefa
    de origem, usando a matriz de transição do aaDespacho.

    LÓGICA SEQUENCIAL:
    1. Verificar estados especiais (/assinar, /minutar, /conclusao)
    2. Abrir tarefa do processo se necessário (de /detalhe)
    3. Navegar para 'Conclusão ao Magistrado' via navegacao unificada
       (com retry + refresh entre tentativas)
    4. Escolher tipo de conclusão
    5. Aguardar transição para minutar e preparar campo

    Returns:
        bool: True se sucesso, False se falha
    '''
    log_start('CLS')
    # === TIMING: INICIO ===
    timing_inicio = time.time()
    logger.info('[CLS][TIMING][INICIO]')

    try:
        logger.info('FLUXO CLS - INICIANDO')
        logger.info('=' * 60)

        # ===== VERIFICAÇÃO INICIAL: Estados especiais =====
        timing_check_estado = time.time()
        estado_atual = verificar_estado_atual(driver)

        timing_check_estado = time.time() - timing_check_estado
        logger.info(f'[CLS][TIMING][CHECK_ESTADO] {timing_check_estado:.3f}s estado={estado_atual}')
        
        if estado_atual == 'assinar':
            logger.info('[CLS]  Processo já está em /assinar - ato cumprido')
            timing_total = time.time() - timing_inicio
            logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (estado pré-assinar)')
            return True, True  # (sucesso, ja_estava_estado_final=True)
        elif estado_atual == 'minutar':
            logger.info('[CLS]  Processo ja em /minutar — marcando como concluido')
            timing_total = time.time() - timing_inicio
            logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (já em /minutar)')
            return True, True  # (sucesso, ja_estava_estado_final=True)
        elif estado_atual == 'conclusao':
            logger.info('[CLS] Já estamos em /conclusao - pulando navegação')
            ja_em_conclusao = True
        else:
            ja_em_conclusao = False

        # ===== PASSO 1: ABRIR TAREFA DO PROCESSO (apenas se estivermos em /detalhe) =====
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

                # Se já está em estado final após abrir tarefa (/assinar ou /minutar)
                if ja_em_minutar:
                    current_after = (driver.current_url or '').lower()
                    if '/assinar' in current_after:
                        logger.info('[CLS] Já em /assinar após abrir tarefa - ato cumprido')
                        timing_total = time.time() - timing_inicio
                        logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (estado pré-assinar)')
                        return True, True
                    elif '/minutar' in current_after:
                        logger.info('[CLS] Já em /minutar após abrir tarefa — marcando como concluído')
                        timing_total = time.time() - timing_inicio
                        logger.info(f'[CLS][TIMING][SUCESSO] {timing_total:.3f}s (já em /minutar após abrir tarefa)')
                        return True, True

                # Se abriu direto em /conclusao, marca para pular a navegação (mas segue para escolher o tipo)
                current_after = (driver.current_url or '').lower()
                if '/conclusao' in current_after:
                    logger.info('[CLS] Nova aba já em /conclusao — pulando navegação inicial')
                    ja_em_conclusao = True
            else:
                # Se não estamos em /detalhe, presumimos que já estamos na aba da tarefa do processo
                logger.info('[CLS] Não estamos em /detalhe — assumindo que já estamos na aba da tarefa do processo')
                current_url = (driver.current_url or '').lower()
                if '/conclusao' in current_url:
                    ja_em_conclusao = True

        # ===== PASSO 2: LIMPAR OVERLAYS =====
        logger.info('[CLS] Passo 2: Limpando overlays...')
        timing_overlays_inicio = time.time()
        limpar_overlays(driver)
        timing_overlays = time.time() - timing_overlays_inicio
        logger.info(f'[CLS][TIMING][LIMPAR_OVERLAYS] {timing_overlays:.3f}s')

        # ===== PASSO 3: NAVEGAR PARA CONCLUSÃO (se necessário) =====
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

        # ===== PASSO 4: ESCOLHER TIPO DE CONCLUSÃO =====
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

        # ===== PASSO 5: AGUARDAR TRANSIÇÃO PARA MINUTAR =====
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

        # ===== PASSO 6: PREPARAR CAMPO DE MINUTAR =====
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
        return True, False  # (sucesso, ja_estava_estado_final)

    except Exception as e:
        timing_total = time.time() - timing_inicio
        log_fim('CLS', {'status': 'erro', 'motivo': str(e)[:80]})
        logger.error(f'[CLS][TIMING][ERRO] {timing_total:.3f}s erro inesperado: {e}')
        logger.error(f'[CLS] Erro inesperado no fluxo CLS: {e}')
        return False, False  # (sucesso=False, ja_estava_estado_final=False)


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
    '''
    Fluxo generalizado para qualquer ato judicial, seguindo a ordem:
    0. Coleta de conteúdo parametrizável (PRIMEIRO PASSO - na aba /detalhe)
    1. Modelo (fluxo_cls)
    2. Descrição
    3. Sigilo
    4. Intimar
    5. PEC
    6. Prazo
    7. Movimento
    8. Assinar
    9. Função extra de sigilo (NOTA: não executada aqui, deve ser feita externamente)

    NOVO COMPORTAMENTO DE SIGILO:
    - A função visibilidade_sigilosos não é mais executada automaticamente
    - Deve ser executada externamente após fechar a aba e estar na URL /detalhe
    - Use executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado)

    :return: (sucesso: bool, sigilo_ativado: bool)
    '''
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
        # 0. PRIMEIRO: Executar coleta de conteúdo parametrizável na aba /detalhe (se especificado)
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

        # 1. MODELO: Executar fluxo CLS se modelo_nome especificado
        if modelo_nome:
            logger.info(f'[ATO] Executando fluxo CLS com modelo: {modelo_nome}')

            if not conclusao_tipo:
                logger.error('[ATO] conclusao_tipo é obrigatório quando modelo_nome é fornecido!')
                return False, False

            # Executar fluxo_cls (retorna (sucesso, ja_estava_estado_final))
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

            # Preencher descrição se fornecida
            if descricao:
                logger.info(f'[ATO][DESCRICAO] Preenchendo descrição: {descricao}')
                try:
                    campo_descricao = esperar_elemento(driver, 'input[aria-label="Descrição"]', timeout=5)
                    if campo_descricao:
                        preencher_campo(driver, 'input[aria-label="Descrição"]', descricao)
                        logger.info('[ATO][DESCRICAO]  Descrição preenchida')
                    else:
                        raise Exception('Campo descrição não encontrado')
                except Exception as e:
                    logger.error(f'[ATO][DESCRICAO]  Erro ao preencher descrição: {e}')

            # Preencher filtro do modelo
            try:
                logger.info(f'[ATO][MODELO] Preenchendo filtro com modelo: {modelo_nome}')
                campo_filtro_modelo = esperar_elemento(driver, 'input#inputFiltro', timeout=5)
                if not campo_filtro_modelo:
                    raise Exception('Campo filtro modelo não encontrado')

                if hasattr(driver, 'page'):
                    driver.page.evaluate("""modeloNome => {
                        var input = document.querySelector('input#inputFiltro');
                        if (input) {
                            input.focus();
                            input.value = modeloNome;
                            ['input', 'change', 'keyup'].forEach(ev => input.dispatchEvent(new Event(ev, {bubbles: true})));
                        }
                    }""", modelo_nome)
                    driver.page.keyboard.press("Enter")
                else:
                    preencher_campo(driver, 'input#inputFiltro', modelo_nome)

                logger.info(f'[ATO][MODELO] Modelo "{modelo_nome}" preenchido e ENTER pressionado no filtro.')

                try:
                    aguardar_renderizacao_nativa(driver, '.nodo-filtrado', modo='aparecer', timeout=10)
                except Exception:
                    logger.warning('[ATO][MODELO] Timeout aguardando nodo-filtrado, prosseguindo...')

            except Exception as e:
                logger.error(f'[ATO][MODELO] Erro ao preencher filtro do modelo: {e}')
                return False, False

            try:
                seletor_item_filtrado = '.nodo-filtrado'
                seletor_btn_inserir_aria = 'button[aria-label="Inserir modelo de documento"]'
                seletor_btn_inserir_css = (
                    'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes'
                    ' > div.div-botao-inserir > button')

                nodo = aguardar_e_clicar(driver, seletor_item_filtrado, timeout=15)
                if not nodo:
                    logger.error('[ATO][MODELO] Nodo do modelo não encontrado!')
                    return False, False
                logger.info('[ATO][MODELO] Clique em nodo-filtrado realizado!')

                aguardar_renderizacao_nativa(
                    driver, 'pje-dialogo-visualizar-modelo', modo='aparecer', timeout=8)

                espera.assentar(driver, 0.5, motivo='espera de estabilização do dialog de inserção')

                btn_inserir = wait_for_clickable(driver, seletor_btn_inserir_aria, timeout=8)
                if not btn_inserir:
                    btn_inserir = wait_for_clickable(driver, seletor_btn_inserir_css, timeout=3)
                if not btn_inserir:
                    logger.error('[ATO][MODELO] Botão inserir não encontrado!')
                    return False, False

                safe_click_no_scroll(driver, btn_inserir)
                logger.info('[ATO][MODELO] Clique em inserir realizado')

                try:
                    if espera.ate_texto(driver, 'simple-snack-bar',
                                        'Modelo de documento inserido com sucesso', teto=4):
                        logger.info('[ATO][MODELO] Snackbar de inserção detectada '
                                    '— sinal para prosseguir')
                    else:
                        logger.warning('[ATO][MODELO] Snackbar não detectada '
                                       '(foco pode ter saído da tela); seguindo '
                                       'para verificação de conteúdo')
                except Exception:
                    pass
                aguardar_renderizacao_nativa(
                    driver, 'pje-dialogo-visualizar-modelo', modo='sumir', timeout=4)

                modelo_no_editor = False
                try:
                    modelo_no_editor = bool(espera.ate_js(driver, f"""(() => {{
                        var area = document.querySelector('{EDITOR_AREA_CONTEUDO}');
                        if (!area) return false;
                        var texto = (area.innerText || '').replace(/\\s/g, '');
                        return texto.length > 1 || area.querySelector('figure') !== null;
                    }})()""", teto=10))
                except Exception:
                    modelo_no_editor = False

                if not modelo_no_editor:
                    logger.error('[ATO][MODELO] Conteúdo do modelo NÃO presente no '
                                 'editor após inserção — abortando antes do Salvar')
                    return False, False
                logger.info('[ATO][MODELO] Modelo inserido (conteúdo confirmado no editor)')

            except Exception as e:
                logger.error(f'[ATO][MODELO] Erro ao inserir modelo: {e}')
                return False, False

        # ===== INSERIR CONTEÚDO (antes do salvar, como no jud.py) =====
        if inserir_conteudo:
            logger.info('[ATO][INSERIR] Executando inserção de conteúdo...')
            try:
                inserir_conteudo(driver)
                logger.info('[ATO][INSERIR]  Conteúdo inserido')
            except Exception as e:
                logger.error(f'[ATO][INSERIR]  Erro ao inserir conteúdo: {e}')
                return False, False

        # ===== SALVAR IMEDIATAMENTE APÓS INSERÇÃO (como no jud.py) =====
        logger.info('[ATO][SALVAR] Salvando modelo após inserção...')
        try:
            btn_salvar = wait_for_clickable(driver, '//button[contains(@class, "mat-raised-button") and contains(@class, "mat-primary") and contains(., "Salvar") and @aria-label="Salvar"]', timeout=15, by=By.XPATH)
            if not btn_salvar:
                raise Exception('Botão Salvar não disponível')
            safe_click(driver, btn_salvar)
            logger.info('[ATO][SALVAR] Clique no botao Salvar realizado')

            # Aguarda controles da aba destinatários (OR de seletores como no leg)
            # Toggle OU botão gravar OU PEC OU tabela de partes — qualquer um indica que a aba renderizou
            if not aguardar_renderizacao_nativa(
                driver,
                'button[aria-label="Gravar a intimação/notificação"], '
                'pje-intimacao-automatica label.mat-slide-toggle-label, '
                'mat-checkbox[aria-label="Enviar para PEC"], '
                'div.checkbox-pec mat-checkbox, '
                'table.t-class tr.ng-star-inserted, '
                'button#selecionar-polo-ativo',
                modo='aparecer',
                timeout=15,
            ):
                logger.warning('[ATO][SALVAR] Timeout aguardando controles de destinatários, prosseguindo...')


            # Compatibilidade com transição Angular (como no leg)
            espera.assentar(driver, 1.5)
            logger.info('[ATO][SALVAR] Aguardando ativação da aba destinatários...')

        except Exception as e:
            logger.error(f'[ATO][SALVAR] Botão Salvar não encontrado ou não clicável: {e}')
            return False, False

        # ===== ABA DESTINATÁRIOS =====
        # sigilo_ativado referenciado no retorno mesmo sem movimento
        sigilo_ativado = False

        # Verificar intimar_ativado
        intimar_ativado = True if intimar is None else str(intimar).lower() in ("sim", "true", "1")

        # ----- 1. SIGILO (primeiro de tudo, logo após a aba renderizar) -----
        if sigilo:
            logger.info('[ATO][SIGILO] Aplicando sigilo...')
            try:
                slide = esperar_elemento(
                    driver,
                    'mat-slide-toggle[name="sigiloso"], mat-slide-toggle#sigilo',
                    timeout=5
                )
                if slide:
                    input_sig = espera.elemento(driver, 'mat-slide-toggle[name="sigiloso"] input[type="checkbox"], mat-slide-toggle#sigilo input[type="checkbox"]', teto=1)

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

                    sigilo_ativado = True
                    logger.info('[ATO][SIGILO] Sigilo ativado')
                else:
                    logger.debug('[ATO][SIGILO] Toggle de sigilo não encontrado')
            except Exception as e:
                logger.debug(f'[ATO][SIGILO] Erro ao aplicar sigilo: {e}')

        # ----- 2. TOGGLE INTIMAR (ativar ou desativar conforme intimar_ativado) -----
        if intimar_ativado:
            try:
                guia_intimacoes = esperar_elemento(driver, 'pje-editor-lateral div[aria-posinset="1"]', timeout=5)
                if guia_intimacoes and guia_intimacoes.get_attribute('aria-selected') == "false":
                    safe_click_no_scroll(driver, guia_intimacoes)
                    espera.assentar(driver, 0.5)

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
                guia_intimacoes = esperar_elemento(driver, 'pje-editor-lateral div[aria-posinset="1"]', timeout=10)
                if guia_intimacoes and guia_intimacoes.get_attribute('aria-selected') == "false":
                    safe_click_no_scroll(driver, guia_intimacoes)
                    espera.assentar(driver, 0.5)

                toggle_intimar = esperar_elemento(driver, 'pje-intimacao-automatica label.mat-slide-toggle-label', timeout=10)
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

        # ----- 3. DESTINATÁRIOS E PRAZO (quando intimar=True) -----
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

        # ----- 4. PEC (conforme padrão aadespacho de gigs-plugin.js) -----
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
                            var el = document.querySelector('pje-intimacao-automatica mat-checkbox[aria-label="Enviar para PEC"], mat-checkbox[aria-label="Enviar para PEC"]');
                            if (!el) return null;
                            var cls = el.getAttribute('class') || '';
                            return cls.indexOf('mat-checkbox-checked') !== -1 || cls.indexOf('mat-mdc-checkbox-checked') !== -1;
                        }"""
                        novo_estado = None
                        if hasattr(driver, 'page'):
                            novo_estado = driver.page.evaluate(js_recheca_pec)
                        novo_estado_str = "marcado" if novo_estado else "desmarcado"
                        logger.info(f'[ATO][PEC] Estado inicial: {estado_ini} → alterado para: {novo_estado_str}')
                    else:
                        logger.info(f'[ATO][PEC] Já está conforme esperado: {estado_ini}')
            except Exception as e:
                logger.error(f'[ATO][PEC] Erro ao tratar PEC: {e}')

        # ----- 5. GRAVAR INTIMAÇÕES (padrão gigs-plugin.js e leg) -----
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

        # ----- 6. MOVIMENTO -----
        if movimento:
            logger.info(f'[ATO][MOVIMENTO] Selecionando movimento: {movimento}')
            try:
                aba_mov_clicada = False
                if hasattr(driver, 'page'):
                    try:
                        aba_mov_clicada = bool(driver.page.evaluate("""() => {
                            var abas = Array.from(document.querySelectorAll('.mat-tab-label'));
                            var abaMov = abas.find(function(a) {
                                return a.textContent && a.textContent.normalize('NFD').replace(/[\\W_]/g, '').toLowerCase().includes('movimentos');
                            });
                            if (abaMov && abaMov.getAttribute('aria-selected') !== 'true') {
                                abaMov.click();
                                return true;
                            }
                            return false;
                        }"""))
                    except Exception:
                        aba_mov_clicada = False

                if aba_mov_clicada:
                    logger.debug('[ATO][MOVIMENTO] Aba Movimentos clicada')
                    aguardar_renderizacao_nativa(driver, 'mat-checkbox.mat-checkbox.movimento', modo='aparecer', timeout=3)

                raiz_movimento = movimento.split('/')[0].split('-')[0].strip() if ('/' in movimento or '-' in movimento) else movimento

                js_mov = """raiz => {
                    var textoMov = raiz.trim().toLowerCase().replace(/\\s+/g, ' ');
                    var checkboxes = Array.from(document.querySelectorAll('mat-checkbox.mat-checkbox.movimento'));

                    function normalizarTexto(texto) {
                        return texto.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().trim();
                    }

                    var termoPesquisa = normalizarTexto(textoMov);

                    for (var cb of checkboxes) {
                        try {
                            var label = cb.querySelector('label.mat-checkbox-layout .mat-checkbox-label');
                            var labelText = label && label.textContent ? label.textContent : '';
                            var labelNorm = labelText.trim().toLowerCase().replace(/\\s+/g, ' ');
                            var labelSemAcento = normalizarTexto(labelText);

                            var encontrado = labelNorm.includes(textoMov) ||
                                            labelSemAcento.includes(termoPesquisa) ||
                                            (textoMov === 'frustrada' && (labelSemAcento.includes('execucao frustrada') || labelSemAcento.includes('276'))) ||
                                            (textoMov.match(/^\\d+$/) && labelText.includes('(' + textoMov + ')'));

                            if (encontrado) {
                                var input = cb.querySelector('input[type="checkbox"]');
                                if (input && !input.checked) {
                                    var inner = cb.querySelector('.mat-checkbox-inner-container');
                                    if(inner) {
                                        inner.click();
                                    } else {
                                        input.click();
                                    }
                                }
                                return {selecionado: true, label: labelText};
                            }
                        } catch (e) {
                            console.warn('[ATO][MOVIMENTO] Erro ao processar checkbox:', e);
                        }
                    }
                    return {selecionado: false, label: ''};
                }"""

                res_mov = {'selecionado': False, 'label': ''}
                if hasattr(driver, 'page'):
                    res_mov = driver.page.evaluate(js_mov, raiz_movimento) or {}

                if not res_mov.get('selecionado'):
                    logger.error(f'[ATO][MOVIMENTO]  Movimento raiz não encontrado: {raiz_movimento}')
                    return False, False
                logger.info(f'[ATO][MOVIMENTO]  Checkbox marcado: {res_mov.get("label")}')

                # Movimento multi-estágio (combobox)
                if '/' in movimento or '-' in movimento:
                    if not selecionar_movimento_auto(driver, movimento):
                        logger.error(f'[ATO][MOVIMENTO]  Complementos do movimento não encontrados: {movimento}')
                        return False, False
                    logger.info('[ATO][MOVIMENTO]  Complementos selecionados via combobox')

                # Gravar movimento
                logger.info('[ATO][MOVIMENTO] Gravando movimento...')
                aguardar_renderizacao_nativa(driver, '.cdk-overlay-backdrop-showing', modo='sumir', timeout=3)
                btn_gravar_mov = wait_for_clickable(driver, BTN_GRAVAR_MOVIMENTOS, timeout=10)
                if btn_gravar_mov:
                    safe_click_no_scroll(driver, btn_gravar_mov)

                logger.info('[ATO][MOVIMENTO] Confirmando gravação...')
                snack = wait_for_clickable(driver, 'snack-bar-container simple-snack-bar', timeout=4)
                if snack and 'movimentos gravados' in (getattr(snack, 'text', '') or '').lower():
                    try:
                        btn_x = espera.elemento(driver, 'simple-snack-bar button', teto=1)
                        if btn_x:
                            safe_click_no_scroll(driver, btn_x)
                    except Exception:
                        pass
                    logger.info('[ATO][MOVIMENTO] Movimento gravado (snackbar de sucesso)')
                else:
                    logger.warning('[ATO][MOVIMENTO] Sem confirmação de gravação do movimento (snackbar ausente), assumindo sucesso')

            except Exception as e:
                logger.error(f'[ATO][MOVIMENTO]  Erro ao selecionar movimento: {e}')
                return False, False

        # ----- 7. SALVAR FINAL (único, sempre — com ou sem movimento) -----
        logger.info('[ATO][SALVAR_FINAL] Salvando ato...')
        try:
            btn_salvar_final = wait_for_clickable(driver, "button[aria-label='Salvar'][color='primary']", timeout=10)
            if not btn_salvar_final:
                raise Exception('Botão Salvar não disponível')
            safe_click_no_scroll(driver, btn_salvar_final)
            logger.info('[ATO][SALVAR_FINAL] Ato salvo')
            espera.assentar(driver, 1.5)
        except Exception as e:
            logger.error(f'[ATO][SALVAR_FINAL] {e}')
            return False, False

        # 8. ASSINAR: Clicar em assinar se especificado
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
    '''
    Factory function que cria um wrapper para ato_judicial com parâmetros pré-definidos.
    '''
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
