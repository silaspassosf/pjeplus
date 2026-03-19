from .loop_base import *
from .loop_ciclo1 import _ciclo1_abrir_suitcase, _ciclo1_aguardar_movimentacao_lote, _ciclo1_movimentar_destino
from Fix.smart_finder import SmartFinder

# Instantiate once for reuse
_SF = SmartFinder()


def _ciclo2_criar_atividade_xs(driver: WebDriver) -> bool:
    """Cria atividade 'xs' para processos selecionados."""
    try:
        # Clique tag verde
        tag_verde = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-tag.icone.texto-verde'))
        )
        driver.execute_script("arguments[0].click();", tag_verde)

        # Clique botão "Atividade" — usar SmartFinder para localizar opção de menu mais rápido
        btn_atividade = _SF.find(driver, 'ciclo2_btn_atividade', [
            "//button[contains(normalize-space(.), 'Atividade')]",
            "button.mat-menu-item"
        ])
        if btn_atividade:
            driver.execute_script("arguments[0].click();", btn_atividade)
        else:
            # fallback: buscar via text scan (mais custoso)
            btns = driver.find_elements(By.CSS_SELECTOR, "button.mat-menu-item")
            for btn in btns:
                if "Atividade" in (btn.text or ''):
                    driver.execute_script("arguments[0].click();", btn)
                    break

        # Preencher observação
        campo_obs = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea[formcontrolname='observacao']"))
        )
        campo_obs.click()
        campo_obs.clear()
        campo_obs.send_keys('xs')
        # esperar até que o textarea contenha o texto (sincronização mínima)
        WebDriverWait(driver, 6).until(lambda d: 'xs' in campo_obs.get_attribute('value'))

        # Salvar
        spans = driver.find_elements(By.CSS_SELECTOR, "button.mat-raised-button span")
        btn_salvar = next((s for s in spans if "Salvar" in s.text), None)
        if not btn_salvar:
            return False
        btn_pai = btn_salvar.find_element(By.XPATH, "..")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_pai)
        driver.execute_script("arguments[0].click();", btn_pai)

        # Verificar fechamento do modal via espera explícita
        try:
            WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, 'mat-dialog-container')))
        except Exception:
            modais = driver.find_elements(By.CSS_SELECTOR, "mat-dialog-container")
            if modais:
                logger.error('[CICLO2][XS] Modal ainda aberto após Salvar')
                return False
        logger.info('[CICLO2][XS] ✅ Atividade xs criada')
        return True
    except Exception as e:
        logger.error(f'[LOOP_PRAZO][ERRO] Falha ao criar atividade xs: {e}')
        return False


def _ciclo2_movimentar_lote(driver: WebDriver, opcao_destino: str, ha_mais: bool) -> bool:
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

    # Em vez de forçar um reload completo, voltar graciosamente para a lista
    # usando o mesmo método do ciclo1, que demonstrou ser mais rápido/estável.
    import time as _time
    _t0 = _time.perf_counter()
    try:
        # _ciclo1_retornar_lista faz history.back() e limpa overlays
        from .loop_ciclo1_movimentacao import _ciclo1_retornar_lista
        _ciclo1_retornar_lista(driver)
        # aguardar a tabela da lista reaparecer
        try:
            WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.cdk-drag')))
        except Exception:
            try:
                WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Fase processual')]")))
            except Exception:
                pass
    except Exception as e:
        logger.info(f'[CICLO2] Retorno para a lista via history.back() falhou, fallback para driver.get: {e}')
        try:
            driver.get("https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos")
            WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.cdk-drag')))
        except Exception:
            pass

    _t1 = _time.perf_counter()
    try:
        logger.info(f'[LATENCIA][DETALHE] CICLO2_NAV_PAINEL8: {(_t1-_t0)*1000:.1f}ms')
    except Exception:
        pass

    logger.info(f'[CICLO2] ✅ Lote movimentado ({opcao_destino})')
    return True


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
    Se selecionou < 20 → último ciclo, encerra.

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
            # aguardar até que não haja checkboxes marcados (sincronização mínima)
            try:
                WebDriverWait(driver, 6).until(lambda d: len(d.execute_script("return document.querySelectorAll('mat-checkbox input[type=\\\"checkbox\\\"]:checked').length")) == 0)
            except Exception:
                pass
        except:
            pass

        # REAPLICAR FILTROS a partir da 2ª iteração (1ª já tem filtros do ciclo2)
        # Motivo: ao voltar da movimentação em lote, a lista perde os filtros aplicados
        if iteracao > 1:
            from .loop_ciclo2_selecao import _ciclo2_aplicar_filtros
            if not _ciclo2_aplicar_filtros(driver):
                logger.error('[CICLO2][PROVIDENCIAS] Falha ao reaplicar filtros')
                return False

        # Selecionar até 20 não-livres
        nao_livres, ha_mais = _ciclo2_selecionar_nao_livres(driver)

        if nao_livres == 0:
            logger.info('[CICLO2][PROVIDENCIAS] ✅ Nenhum não-livre')
            return True

        logger.info(f'[CICLO2][PROVIDENCIAS] Ciclo {iteracao}: {nao_livres} processos')

        # Movimentar para providências
        if not _ciclo2_movimentar_lote(driver, opcao_destino, ha_mais):
            logger.error('[CICLO2][PROVIDENCIAS] Falha ao movimentar lote')
            return False

        # Se selecionou < 20 → último ciclo (não há mais processos)
        if nao_livres < 20:
            logger.info(f'[CICLO2][PROVIDENCIAS] ✅ Último ciclo concluído ({nao_livres} processos)')
            return True

        # Continuar loop (selecionou exatamente 20, pode haver mais)
        # Pequena espera de estabilização opcional, mas muito menor que sleep(2)
        try:
            WebDriverWait(driver, 3).until(lambda d: True)
        except Exception:
            pass


def ciclo2(driver: WebDriver, opcao_destino: str = 'Cumprimento de providências') -> Union[bool, str]:
    """
    Ciclo 2 completo: GIGS + LIVRES + PROVIDÊNCIAS.
    """
    from .loop_ciclo2_selecao import _ciclo2_aplicar_filtros, _ciclo2_processar_livres
    from .loop_api import _selecionar_processos_por_gigs_aj_jt

    try:
        with medir_latencia('CICLO2_TOTAL'):
            logger.info('[CICLO2] Iniciando ciclo 2 completo...')

            if not _ciclo2_aplicar_filtros(driver):
                return False

            client = None
            try:
                sess, trt = session_from_driver(driver)
                client = PjeApiClient(sess, trt)
            except Exception as e:
                logger.warning(f'[CICLO2][WARN] Falha ao inicializar client GIGS: {e}')

            with medir_latencia('CICLO2_SELECAO_GIGS_AJ_JT'):
                gigs_selecionados = _selecionar_processos_por_gigs_aj_jt(driver, client)

            with medir_latencia('CICLO2_SELECAO_LIVRES'):
                livres_selecionados = _ciclo2_processar_livres(driver, client=client)

            total_selecionados = gigs_selecionados + livres_selecionados
            logger.info(f'[CICLO2]  Total selecionado: {total_selecionados} (GIGS: {gigs_selecionados}, Livres: {livres_selecionados})')

            if total_selecionados > 0:
                if not _ciclo2_criar_atividade_xs(driver):
                    return False

            with medir_latencia('CICLO2_LOOP_PROVIDENCIAS'):
                if not ciclo2_loop_providencias(driver, opcao_destino):
                    return False

            logger.info('[CICLO2] Ciclo 2 concluído com sucesso.')
            return True

    except Exception as e:
        logger.error(f'[CICLO2] Erro no ciclo 2: {e}')
        return False