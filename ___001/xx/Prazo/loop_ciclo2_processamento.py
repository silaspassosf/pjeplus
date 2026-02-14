from .loop_base import *
from .loop_ciclo1 import _ciclo1_abrir_suitcase, _ciclo1_aguardar_movimentacao_lote, _ciclo1_movimentar_destino


def _ciclo2_criar_atividade_xs(driver: WebDriver) -> bool:
    """Cria atividade 'xs' para processos selecionados."""
    try:
        # Clique no botão tag verde para abrir o dropdown de atividade
        seletor_tag = 'i.fa.fa-tag.icone.texto-verde'
        sucesso_tag = aguardar_e_clicar(
            driver,
            seletor_tag,
            timeout=10,
            by=By.CSS_SELECTOR,
            log=True
        )
        if not sucesso_tag:
            logger.error('[LOOP_PRAZO][ERRO] Falha ao clicar no botão tag verde com aguardar_e_clicar.')
            input('[PAUSE] Pressione ENTER para continuar o debug...')
            return False
        time.sleep(0.8)

        # Clique direto no botão "Atividade" via CSS/texto
        sucesso_atividade = False
        btns = driver.find_elements(By.CSS_SELECTOR, "button.mat-menu-item")
        for btn in btns:
            if "Atividade" in btn.text:
                driver.execute_script("arguments[0].click();", btn)
                sucesso_atividade = True
                break
        if not sucesso_atividade:
            logger.error('[LOOP_PRAZO][ERRO] Falha ao clicar no botão "Atividade".')
            return False
        time.sleep(1.2)

        # Preencher observação
        campo_obs = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea[formcontrolname='observacao']"))
        )
        campo_obs.click()
        campo_obs.clear()
        campo_obs.send_keys('xs')
        time.sleep(0.6)
        # Clique enxuto: localizar span "Salvar" e clicar via JS no botão pai
        spans = driver.find_elements(By.CSS_SELECTOR, "button.mat-raised-button span")
        btn_salvar = next((s for s in spans if "Salvar" in s.text), None)
        if not btn_salvar:
            return False
        btn_pai = btn_salvar.find_element(By.XPATH, "..")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_pai)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", btn_pai)
        # Checar fechamento do modal
        time.sleep(1.2)
        modais = driver.find_elements(By.CSS_SELECTOR, "mat-dialog-container")
        if modais:
            logger.error('[LOOP_PRAZO][ERRO] Modal xs ainda aberto após clique em Salvar.')
            input('[PAUSE] Pressione ENTER para continuar o debug...')
            return False
        #  AGUARDAR para garantir que o CICLO COMPLETO (seleção + atividade XS) foi finalizado
        # ANTES de prosseguir para o próximo ciclo (NÃO-LIVRES/CUMPRIMENTO DE PROVIDÊNCIAS)
        time.sleep(2.0)
        return True
    except Exception as e:
        logger.error(f'[LOOP_PRAZO][ERRO] Falha ao criar atividade xs: {e}')
        return False
        # NÃO atualizar/recarregar a página após xs, inicia próximo ciclo direto
        return True
    except Exception as e:
        logger.error(f'[LOOP_PRAZO][ERRO] Falha ao criar atividade xs: {e}')
        return False


def _ciclo2_movimentar_lote(driver: WebDriver, opcao_destino: str, ha_mais: bool) -> Union[bool, str]:
    """Abre suitcase, seleciona destino e movimenta processos."""
    # Abrir suitcase
    if not _ciclo1_abrir_suitcase(driver):
        logger.error('[LOOP_PRAZO][ERRO] Falha ao abrir suitcase no ciclo2.')
        return False

    # Aguardar carregamento da página de movimentação em lote (como no ciclo1)
    if not _ciclo1_aguardar_movimentacao_lote(driver):
        logger.error('[LOOP_PRAZO][ERRO] Falha ao aguardar movimentação em lote no ciclo2.')
        return False

    # Selecionar destino
    if not _ciclo1_movimentar_destino(driver, opcao_destino):
        logger.error(f'[LOOP_PRAZO][ERRO] Falha ao selecionar destino "{opcao_destino}" no ciclo2.')
        return False

    # Retornar à lista
    driver.get("https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos")
    time.sleep(3)

    return ha_mais


def ciclo2_processar_livres_apenas_uma_vez(driver: WebDriver, opcao_destino: str = 'Cumprimento de providências') -> Tuple[int, bool]:
    """
    Fase 2.1: Processa APENAS seleção de processos livres (SEM aplicar atividade XS).
    A atividade XS será aplicada na Fase 2.2 para GIGS+LIVRES juntos.

    Returns:
        Tupla (livres_selecionados, ha_nao_livres_para_providencias)
    """
    from .loop_ciclo2_selecao import _ciclo2_aplicar_filtros, _ciclo2_processar_livres

    if not _ciclo2_aplicar_filtros(driver):
        return 0, False

    # 1. Criar client GIGS para busca de atividades
    client = None
    try:
        sess, trt = session_from_driver(driver)
        client = PjeApiClient(sess, trt)
    except Exception as e:
        logger.warning(f'[LOOP_PRAZO][WARN] Falha ao inicializar client GIGS (continuando sem GIGS): {e}')
        client = None

    # 2. Selecionar LIVRES (SEM aplicar XS ainda)
    livres = _ciclo2_processar_livres(driver, client=client)

    # 3. Contar total de não-livres (para saber se entra no loop de providências)
    # Primeiro, salvar os selecionados atuais (GIGS+LIVRES) antes de testar não-livres
    try:
        resultado = driver.execute_script(SCRIPT_SELECAO_NAO_LIVRES, 1)  # Seleciona apenas 1 para contar total
        total_nao_livres = resultado['totalNaoLivres']
        ha_nao_livres = total_nao_livres > 0

        # Desselecionar aquele 1 não-livre que foi selecionado para teste
        try:
            driver.execute_script("""
                document.querySelectorAll('mat-checkbox input[type="checkbox"]:checked').forEach(function(c){
                    var linha = c.closest('tr');
                    var temProvidencias = linha.querySelector('a[href*="providencias"]') !== null;
                    if (temProvidencias) {
                        c.click();
                    }
                });
            """)
            time.sleep(0.6)
        except:
            pass

        return livres, ha_nao_livres
    except Exception as e:
        logger.error(f'[LOOP_PRAZO][ERRO] Erro ao contar não-livres: {e}')
        return livres, False


def ciclo2_loop_providencias(driver: WebDriver, opcao_destino: str = 'Cumprimento de providências') -> bool:
    """
    Fase 2.3: Loop para processar providências (cumprimento) - processa NÃO-LIVRES.
    Processa até 20 processos não-livres por iteração.
    Continua loopando enquanto houver MAIS de 20 processos não-livres.

    Returns:
        True: processamento bem-sucedido
        False: erro crítico
    """
    from .loop_ciclo2_selecao import _ciclo2_selecionar_nao_livres

    iteracao = 0
    while True:
        iteracao += 1

        # Desselecionar todos antes de começar nova iteração
        try:
            driver.execute_script("document.querySelectorAll('mat-checkbox input[type=\"checkbox\"]:checked').forEach(c=>c.click());")
            time.sleep(0.6)
        except:
            pass
        
        # REAPLICAR FILTROS antes de cada iteração (fases liquidação/execução + filtro tarefa análise)
        print(f'[LOOP_PRAZO] Reaplicando filtros para iteração {iteracao}...')
        from .loop_ciclo2_selecao import _ciclo2_aplicar_filtros
        if not _ciclo2_aplicar_filtros(driver):
            print('[LOOP_PRAZO][ERRO] Falha ao reaplicar filtros de atividades.')
            return False

        # Selecionar até 20 não-livres
        nao_livres, ha_mais = _ciclo2_selecionar_nao_livres(driver)

        if nao_livres == 0:
            return True


        # Movimentar para providências
        resultado = _ciclo2_movimentar_lote(driver, opcao_destino, ha_mais)
        if resultado is False:
            logger.error('[LOOP_PRAZO][ERRO] Falha ao movimentar lote em providências.')
            return False

        # Se não há mais processos (ha_mais=False), encerrar o loop
        if not ha_mais:
            return True

        # Se há mais (ha_mais=True), continuar o loop para processar próximos 20
        time.sleep(2)
        time.sleep(2)


def ciclo2(driver: WebDriver, opcao_destino: str = 'Cumprimento de providências') -> Union[bool, str]:
    """
    Ciclo 2 completo: GIGS + LIVRES + PROVIDÊNCIAS.
    """
    from .loop_ciclo2_selecao import _ciclo2_aplicar_filtros, _ciclo2_processar_livres
    from .loop_api import _selecionar_processos_por_gigs_aj_jt

    try:
        print('[CICLO2] Iniciando ciclo 2 completo...')

        # Aplicar filtros
        if not _ciclo2_aplicar_filtros(driver):
            return False

        # Criar client GIGS
        client = None
        try:
            sess, trt = session_from_driver(driver)
            client = PjeApiClient(sess, trt)
        except Exception as e:
            logger.warning(f'[CICLO2][WARN] Falha ao inicializar client GIGS: {e}')

        # 1. Selecionar GIGS AJ-JT
        gigs_selecionados = _selecionar_processos_por_gigs_aj_jt(driver, client)

        # 2. Selecionar LIVRES (filtrando xs duplicados)
        livres_selecionados = _ciclo2_processar_livres(driver, client=client)

        total_selecionados = gigs_selecionados + livres_selecionados
        print(f'[CICLO2] 📊 Total selecionado: {total_selecionados} (GIGS: {gigs_selecionados}, Livres: {livres_selecionados})')

        # 3. Aplicar atividade XS se há processos selecionados
        if total_selecionados > 0:
            if not _ciclo2_criar_atividade_xs(driver):
                return False

        # 4. Processar providências (não-livres)
        if not ciclo2_loop_providencias(driver, opcao_destino):
            return False

        print('[CICLO2] Ciclo 2 concluído com sucesso.')
        return True

    except Exception as e:
        logger.error(f'[CICLO2] Erro no ciclo 2: {e}')
        return False