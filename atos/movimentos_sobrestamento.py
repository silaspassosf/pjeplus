import logging
from Fix.core import safe_click_no_scroll
logger = logging.getLogger(__name__)

from .core import *
import time

from selenium.webdriver.remote.webdriver import WebDriver
from Fix import espera


def mov_sob(driver, numero_processo, observacao, debug=False, timeout=15):
    """
    Movimento de sobrestamento com prazo específico.
    
    Fluxo:
    1. Abre tarefa do processo (igual ao mov padrão)    
    2. Clica no ícone de calendário NA NOVA ABA DA TAREFA ABERTA
    3. Preenche prazo em meses (extrai número da observação)
    4. Confirma com "Prosseguir"

    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        observacao: Observação que contém o número do prazo (ex: "sob 6")
        debug: Se True, exibe logs detalhados
        timeout: Timeout para aguardar elementos
    
    Returns:
        bool: True se executado com sucesso
    """
    import re
    from Fix.core import safe_click_no_scroll
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from Fix.core import esperar_elemento, safe_click, preencher_campo
    
    def log_msg(msg):
        if debug:
            try:
                print(msg)
            except Exception:
                pass

    log_msg(f"Iniciando movimento de sobrestamento para processo {numero_processo}")
    log_msg(f"Observação: {observacao}")
    
    try:
        # Extrai o número da observação. Padrão: "xs sob N" (meses); pode aparecer
        # por engano sem o "xs" ("sob N"). A mesma regex cobre os dois casos.
        obs_lower = observacao.lower()
        numero_match = re.search(r'\bsob\s+(\d+)', obs_lower)
        if not numero_match:
            # Fallback: "xs N" sem "sob" explícito
            numero_match = re.search(r'\bxs\s+(\d+)', obs_lower)
        if not numero_match:
            log_msg(f" Número não encontrado na observação: {observacao}")
            return False

        prazo_meses = numero_match.group(1)
        log_msg(f" Prazo extraído: {prazo_meses} meses (formato: {'sob' if 'sob' in obs_lower else 'xs'})")

        # ===== ETAPA 1: ABRIR A TAREFA DO PROCESSO (sempre abrir primeiro) =====
        # Nota: comportamento intencionalmente alinhado ao fluxo genérico `mov()`:
        #  - Garantir /detalhe (se existir)
        #  - Tentar localizar o botão rapidamente
        #  - Se não achar, tentar buscas rápidas por variações e um fallback robusto
        #  - Clicar imediatamente com safe_click (fallback para JS click)
        log_msg("1. Abrindo tarefa do processo (sempre primeiro)...")

        def garantir_aba_detalhe():
            # Se houver mais de uma aba, preferimos a que contém '/detalhe'
            try:
                for handle in driver.window_handles:
                    try:
                        driver.switch_to.window(handle)
                        if '/detalhe' in driver.current_url:
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        # tentamos garantir aba /detalhe (não é fatal se não encontrar)
        try:
            garantir_aba_detalhe()
        except Exception:
            pass

        # tentativa rápida pelo seletor canônico (curto timeout para não travar)
        from Fix.selectors_pje import BTN_TAREFA_PROCESSO
        btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=max(2, timeout//3))

        # se não achou, tentar variações rápidas (busca direta sem esperar muito)
        if not btn_abrir_tarefa:
            log_msg(" Botão 'Abrir tarefa do processo' não encontrado via seletor padrão em tentativa rápida; tentando variações...")
            try:
                # procura por atributos alternativos ou texto aproximado
                candidates = []
                try:
                    candidates = driver.find_elements(By.CSS_SELECTOR, 'button[mattooltip*="tarefa"], button[aria-label*="tarefa"], button[title*="tarefa"]')
                except Exception:
                    candidates = []

                for c in candidates:
                    try:
                        if c.is_displayed() and c.is_enabled():
                            btn_abrir_tarefa = c
                            break
                    except Exception:
                        continue
            except Exception:
                btn_abrir_tarefa = None

        # último fallback: usar função robusta do selectors_pje (curto timeout)
        if not btn_abrir_tarefa:
            try:
                from Fix.selectors_pje import buscar_seletor_robusto as buscar_robusto
                btn_abrir_tarefa = buscar_robusto(driver, [
                    "Abre a tarefa do processo",
                    "Abrir tarefa do processo",
                    "Abrir tarefa",
                    "Abrir a tarefa do processo"
                ], timeout=3, log=debug)
            except Exception:
                btn_abrir_tarefa = None

        if not btn_abrir_tarefa:
            log_msg(" Botão 'Abrir tarefa do processo' não encontrado! Não foi possível prosseguir")
            return False

        # Captura o texto da tarefa (quando possível)
        tarefa_do_botao = None
        try:
            span_tarefa = btn_abrir_tarefa.find_element(By.CSS_SELECTOR, '.texto-tarefa-processo')
            if span_tarefa:
                tarefa_do_botao = span_tarefa.text.strip()
                log_msg(f" Tarefa identificada: '{tarefa_do_botao}'")
        except Exception:
            try:
                tarefa_do_botao = btn_abrir_tarefa.text.strip()
            except Exception:
                tarefa_do_botao = None

        # Se a tarefa é "Aguardando prazo", não fazer nada (já está em andamento)
        if tarefa_do_botao and 'aguardando prazo' in tarefa_do_botao.lower():
            log_msg(f"ℹ Tarefa já em estado 'Aguardando prazo' - nenhuma ação necessária")
            return True

        # Clicar na tarefa imediatamente (mesmo que já esteja na aba /detalhe)
        abas_antes = set(driver.window_handles)
        click_ok = safe_click(driver, btn_abrir_tarefa)
        if not click_ok:
            # fallback para clique via JS se safe_click falhar
            try:
                safe_click_no_scroll(driver, btn_abrir_tarefa)
                click_ok = True
            except Exception:
                click_ok = False

        if not click_ok:
            log_msg(" Falha no clique do botão da tarefa")
            return False
        log_msg(f'[MOV_SOB] Botão "Abrir tarefa do processo" clicado')

        # Aguarda nova aba e troca para ela (polling loop, padrão legado)
        nova_aba = None
        for _ in range(20):
            abas_depois = set(driver.window_handles)
            novas_abas = abas_depois - abas_antes
            if novas_abas:
                nova_aba = novas_abas.pop()
                break
            espera.assentar(driver, 0.3)

        if nova_aba:
            # Ao abrir a tarefa, a nova aba é a que devemos usar (não procurar por '/detalhe').
            driver.switch_to.window(nova_aba)
            log_msg(f" Foco trocado para nova aba da tarefa: {driver.current_url}")
        else:
            log_msg(" Nenhuma nova aba detectada, prosseguindo na aba atual")

        # Espera carregamento da aba de detalhes
        try:
            wait_for_page_load(driver, 8)
        except Exception:
            time.sleep(0.8)

        # Guard: só executar este movimento se a aba da tarefa indicar a página
        # de sobrestamento em estado 'aguardandofinal'. Caso contrário, tornar
        # o movimento um no-op e retornar True para não bloquear fluxos que
        # dependem de mov_sob quando este não é aplicável.
        # O Angular roteia a nova aba para /sobrestamento/aguardandofinal de forma
        # ASSÍNCRONA: checar a URL uma única vez (comportamento anterior) fazia o
        # mov_sob virar no-op intermitente quando a checagem corria antes do roteamento
        # — causa principal da execução inconsistente. Agora fazemos polling curto.
        try:
            url_ok = False
            current = ''
            for _ in range(24):  # ~7s no máximo (24 x 0.3s)
                try:
                    current = (driver.current_url or '')
                except Exception:
                    current = ''
                if '/sobrestamento/aguardandofinal' in current:
                    url_ok = True
                    break
                espera.assentar(driver, 0.3)
            if not url_ok:
                log_msg(f" URL atual '{current}' não é sobrestamento/aguardandofinal; pulando mov_sob (no-op)")
                return True
        except Exception:
            # Se não for possível verificar a URL, continuar com o fluxo normal
            log_msg(' Não foi possível verificar a URL atual; prosseguindo com mov_sob')

        # ===== ETAPA 2: LOCALIZAR O BOTÃO DE CALENDÁRIO NA ABA DA TAREFA =====
        log_msg("2. Localizando botão de calendário na aba da tarefa...")
        btn_calendario = None
        try:
            btn_calendario = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[mattooltip="Definir prazo para este motivo de sobrestamento"]'))
            )
            log_msg(" Botão de calendário encontrado")
        except Exception:
            btn_calendario = None

        if not btn_calendario:
            log_msg(" Botão de calendário não encontrado via seletor principal - tentando ícone/alternativos...")
            try:
                icone_cal = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-calendar-alt'))
                )
                safe_click_no_scroll(driver, icone_cal, log=False)
                log_msg(' Fallback: clique no ícone calendário realizado')
            except Exception:
                log_msg(' Botão de calendário não encontrado (principal nem fallback)')
                return False

        # ===== ETAPA 3: CLICAR NO CALENDÁRIO (se achamos o botão) =====
        try:
            if btn_calendario:
                try:
                    btn_calendario.click()
                    log_msg(' Clique direto no botão calendário executado')
                except Exception:
                    try:
                        safe_click_no_scroll(driver, btn_calendario)
                        log_msg(' Clique via JavaScript no botão calendário executado')
                    except Exception:
                        # última tentativa: clicar no ícone interno
                        try:
                            ic = btn_calendario.find_element(By.CSS_SELECTOR, 'i.fas.fa-calendar-alt')
                            ic.click()
                            log_msg(' Clique no ícone interno executado')
                        except Exception as e:
                            log_msg(f' Falha ao clicar no calendário: {e}')
                            return False

            # Aguardar o modal aparecer
            log_msg("Aguardando modal 'Prazo do sobrestamento' aparecer...")
            modal_prazo = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'pje-dialog-prazo-sobrestamento'))
            )
            log_msg(' Modal "Prazo do sobrestamento" encontrado')
        except Exception as e:
            log_msg(f' Erro ao abrir modal de prazo: {e}')
            return False

        # ===== ETAPA 4: PREENCHER PRAZO EM MESES =====
        # Escrita canônica: Fix.core.preencher_campo (em Playwright resolve para
        # fill + blur em Play/pjeplay/nativo.py, que commita o FormControl do
        # Angular). clear() + send_keys() e a escrita direta de el.value NÃO
        # commitavam o `mesesPrazoControl`: o PJe regravava o prazo anterior
        # ("prazo fica idêntico") e o erro passava invisível.
        try:
            campo_prazo = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[formcontrolname='mesesPrazoControl']"))
            )
            if not preencher_campo(
                driver, "input[formcontrolname='mesesPrazoControl']", prazo_meses, log=debug
            ):
                log_msg(' Falha ao gravar o prazo em meses no FormControl do modal')
                return False
            try:
                valor_no_campo = (campo_prazo.get_attribute('value') or '').strip()
            except Exception:
                valor_no_campo = ''
            if valor_no_campo and str(prazo_meses) not in valor_no_campo:
                log_msg(f' Campo de prazo ficou com {valor_no_campo!r}; esperado {prazo_meses}')
                return False
            log_msg(f" Prazo {prazo_meses} meses preenchido no campo")
            espera.pausa(driver, 0.5, 'prazo do sobrestamento preenchido')
        except Exception as e:
            log_msg(f' Erro ao preencher prazo no modal: {e}')
            return False

        # ===== ETAPA 5: CONFIRMAR COM 'PROSSEGUIR' =====
        try:
            btn_prosseguir = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, "//pje-dialog-prazo-sobrestamento//button[.//span[contains(text(), 'Prosseguir')] or contains(., 'Prosseguir')]"))
            )
            try:
                btn_prosseguir.click()
            except Exception:
                try:
                    safe_click_no_scroll(driver, btn_prosseguir)
                except Exception:
                    driver.execute_script('arguments[0].click();', btn_prosseguir)
            log_msg(' Botão "Prosseguir" clicado')

            # Snapshot dos avisos já na tela: só snackbar NOVA conta como resposta
            # deste clique (mesmo critério de clicarBotao(monitorar=true) do
            # gigs-plugin — api/gigs-plugin.js ~37020-37045).
            avisos_antes = set()
            try:
                for barra in driver.find_elements(By.CSS_SELECTOR, 'simple-snack-bar'):
                    try:
                        avisos_antes.add((barra.text or '').strip().lower())
                    except Exception:
                        continue
            except Exception:
                pass

            aviso_sucesso = False
            aviso_falha = ''
            for _ in range(40):  # ~12s, mesmo teto do clicarBotao(monitorar=true)
                texto_novo = ''
                try:
                    for barra in driver.find_elements(By.CSS_SELECTOR, 'simple-snack-bar'):
                        try:
                            texto = (barra.text or '').strip().lower()
                        except Exception:
                            continue
                        if texto and texto not in avisos_antes:
                            texto_novo = texto
                            break
                except Exception:
                    texto_novo = ''
                if texto_novo:
                    if 'falha ao tentar registrar o prazo' in texto_novo or 'erro ao persistir' in texto_novo:
                        aviso_falha = texto_novo
                        break
                    if 'sobrestamento' in texto_novo and 'sucesso' in texto_novo:
                        aviso_sucesso = True
                        break
                espera.pausa(driver, 0.3, 'aguardando aviso do sobrestamento')

            # Fecha o aviso (libera a tela para o próximo processo)
            try:
                for botao_aviso in driver.find_elements(By.CSS_SELECTOR, 'simple-snack-bar button'):
                    try:
                        botao_aviso.click()
                    except Exception:
                        continue
            except Exception:
                pass

            if aviso_falha:
                log_msg(f' PJe recusou o registro do prazo do sobrestamento: {aviso_falha}')
                return False
            if aviso_sucesso:
                log_msg(' Snackbar "Sobrestamento(s) registrado(s) com sucesso" detectada')
                log_msg(' Movimento de sobrestamento finalizado com sucesso!')
                return True
            log_msg(' Sem confirmacao do PJe no prazo do monitor — tratando como falha')
            return False

        except Exception as e:
            log_msg(f' Erro ao confirmar com "Prosseguir": {e}')
            return False

    except Exception as e:
        log_msg(f' Erro geral no movimento de sobrestamento: {e}')
        return False
