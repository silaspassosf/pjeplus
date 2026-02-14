import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario


def alterar_meio_expedicao(driver, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        log('[COMUNICACAO] ⚡ Alterando meio de expedição IMEDIATAMENTE (pós-seleção de destinatários, pré-salvamento)...')
        t0_expediente = time.perf_counter()

        linhas_tabela = driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag')
        total_linhas = len(linhas_tabela)

        if total_linhas == 0:
            log('[COMUNICACAO][WARN] Nenhuma linha de destinatário encontrada na tabela!')
            return False

        log(f'[COMUNICACAO] Verificando {total_linhas} destinatário(s) para alterar meio de expedição')

        alterados = 0
        pulados = 0

        for idx, linha in enumerate(linhas_tabela, 1):
            try:
                try:
                    span_meio = linha.find_element(By.CSS_SELECTOR, 'pje-pec-coluna-meio-expedicao .mat-select-value-text .mat-select-min-line')
                    meio_atual = span_meio.text.strip()
                except Exception:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Não foi possível ler meio de expedição atual')
                    continue

                if 'Domicílio Eletrônico' not in meio_atual:
                    if debug:
                        log(f'[COMUNICACAO] Linha {idx}: "{meio_atual}" - não precisa alterar')
                    pulados += 1
                    continue

                log(f'[COMUNICACAO] Linha {idx}: Domicílio Eletrônico encontrado - alterando para Correio...')

                try:
                    dropdown = linha.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Meios de Expedição"]')
                except Exception:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Dropdown não encontrado')
                    continue

                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown)
                time.sleep(0.1)
                driver.execute_script("arguments[0].click();", dropdown)
                time.sleep(0.4)

                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-option'))
                    )
                except Exception:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Opções do dropdown não carregaram')
                    continue

                opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                correio_clicado = False
                for opcao in opcoes:
                    if 'Correio' in opcao.text:
                        driver.execute_script("arguments[0].click();", opcao)
                        log(f'[COMUNICACAO] ✓ Linha {idx}: Domicílio Eletrônico → Correio')
                        alterados += 1
                        correio_clicado = True
                        time.sleep(0.3)
                        break

                if not correio_clicado:
                    log(f'[COMUNICACAO][WARN] Linha {idx}: Opção "Correio" não encontrada nas opções')
                    try:
                        from selenium.webdriver.common.keys import Keys
                        dropdown.send_keys(Keys.ESCAPE)
                    except Exception:
                        pass

            except Exception as e_linha:
                log(f'[COMUNICACAO][WARN] Linha {idx}: Erro ao processar - {str(e_linha)[:60]}')
                continue

        tempo_total = time.perf_counter() - t0_expediente
        log(f'[COMUNICACAO] ✅ Alterados: {alterados} | Não precisavam: {pulados} | Total: {total_linhas} (tempo: {tempo_total:.3f}s)')
        return True
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Falha ao alterar meio de expedição para Correio: {e}')
        return False


def remover_destinatarios_invalidos(driver, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        log('[COMUNICACAO] Verificando destinatários com ícone vermelho (endereço inválido)')
        try:
            red_icons = driver.find_elements(By.CSS_SELECTOR, '.pec-icone-vermelho-endereco-tabela-destinatarios')
            removidos = 0
            for ic in red_icons:
                try:
                    try:
                        row = ic.find_element(By.XPATH, './ancestor::tr[1]')
                    except Exception:
                        elem = ic
                        row = None
                        for _ in range(6):
                            try:
                                elem = elem.find_element(By.XPATH, './..')
                                if elem.tag_name.lower() == 'tr':
                                    row = elem
                                    break
                            except Exception:
                                break
                        if row is None:
                            continue

                    try:
                        btn_excluir = row.find_element(By.XPATH, ".//button[.//i[contains(@class,'fa-trash-alt')]]")
                        driver.execute_script('arguments[0].scrollIntoView(true);', btn_excluir)
                        time.sleep(0.2)
                        driver.execute_script('arguments[0].click();', btn_excluir)
                        removidos += 1
                        log(f'[COMUNICACAO] ✓ Destinatário com ícone vermelho removido (linha). Total removidos: {removidos}')
                        time.sleep(0.6)
                    except Exception as ebtn:
                        log(f'[COMUNICACAO][WARN] Não encontrou botão de excluir na linha do ícone vermelho: {ebtn}')
                        continue
                except Exception as einner:
                    log(f'[COMUNICACAO][WARN] Erro ao processar ícone vermelho: {einner}')
                    continue
            if removidos == 0:
                log('[COMUNICACAO] Nenhum destinatário com ícone vermelho encontrado')
        except Exception as echeck:
            log(f'[COMUNICACAO][WARN] Falha ao varrer ícones vermelhos: {echeck}')
        return True
    except Exception as e:
        log(f'[COMUNICACAO][WARN] Erro inesperado na verificação de ícones vermelhos: {e}')
        return False


def salvar_minuta_final(driver, sigilo, gigs_extra=None, debug=False, log=None):
    if log is None:
        def log(_msg):
            return None

    try:
        btn_salvar_final = None
        spans = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-button-wrapper') and normalize-space(text())='Salvar']")
        for span in spans:
            btn = span.find_element(By.XPATH, './ancestor::button[1]')
            if btn.is_displayed() and btn.is_enabled():
                btn_salvar_final = btn
                break
        if not btn_salvar_final:
            log('[ERRO] Botão Salvar final não encontrado!')
            return False

        try:
            from Fix.core import safe_click
            clicked = safe_click(driver, btn_salvar_final, log=debug)
        except Exception:
            clicked = False

        if not clicked:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_salvar_final)
                driver.execute_script('arguments[0].click();', btn_salvar_final)
                clicked = True
            except Exception as e_click_final:
                log(f'[ERRO] Não foi possível clicar no botão Salvar final (tentativa direta): {e_click_final}')
                return False

        if clicked:
            log('[DEBUG] Clique no botão Salvar final realizado.')
    except Exception as e:
        log(f'[ERRO] Não foi possível clicar no botão Salvar final: {e}')
        return False

    time.sleep(1)
    time.sleep(2)
    log('[DEBUG] Aguardando processamento do salvamento...')

    if gigs_extra:
        log('[GIGS_EXTRA][WARN] Criação de GIGS via minuta removida. Use criar_gigs na aba /detalhe antes do fluxo.')

    if str(sigilo).lower() in ("sim", "true", "1"):
        try:
            log('[COMUNICACAO] Executando visibilidade_sigilosos após salvamento...')
            executar_visibilidade_sigilosos_se_necessario(driver, True, debug=debug)
            log('[COMUNICACAO] Visibilidade extra aplicada por sigilo positivo.')
        except Exception as e:
            log(f"[COMUNICACAO][ERRO] Falha ao aplicar visibilidade extra: {e}")

    log('Comunicação processual finalizada.')
    return True