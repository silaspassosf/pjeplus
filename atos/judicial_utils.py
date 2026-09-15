"""
judicial_utils.py - Utilit�rios para atos judiciais
===================================================

Fun��es utilit�rias para preenchimento de prazos, verifica��o de bloqueios
e cria��o de wrappers para atos judiciais.
"""

from Fix.core import logger
from selenium.webdriver.common.by import By
from Fix.browser_suporte import safe_click_no_scroll
from Fix.selenium_base import preencher_multiplos_campos
import re
import time
from datetime import datetime, timedelta
from Fix import espera

def _aguardar_painel_destinatarios_assentar(driver, teto_linhas=10):
    """Espera o painel de destinatários terminar de renderizar/hidratar.

    Causa do atropelo (caso 1001827-72.2023.5.02.0703): a tabela aparece no DOM
    ANTES do Angular terminar de hidratar as linhas (que chegam por HTTP) e
    ligar o handler do botão 'Selecionar polo ativo' — o clique cedo não tem
    efeito e a seleção fica com o default (todas marcadas). O ate_habilitar
    só valida DOM, não prontidão Angular. Sinais de prontidão reais:
      1) contagem de linhas estável em 2 leituras consecutivas;
      2) nenhum overlay/spinner de carregamento visível.
    """
    anterior = -1
    atual = 0
    limite = time.monotonic() + float(teto_linhas)
    while time.monotonic() < limite:
        try:
            atual = driver.execute_script(
                "return document.querySelectorAll("
                "'table.t-class tbody tr.ng-star-inserted').length;"
            ) or 0
        except Exception:
            atual = 0
        if atual > 0 and atual == anterior:
            break
        anterior = atual
        espera.assentar(driver, 0.5, motivo='[PRAZOS] aguardando linhas estabilizar')
    try:
        espera.ate_sumir(
            driver,
            '.cdk-overlay-backdrop, .mat-progress-spinner, '
            'circle.mat-progress-spinner-circle, pje-loader, .loading',
            teto=5,
        )
    except Exception:
        pass
    return atual


def preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=False, perito=False, perito_nomes=None):
    """
    Preenche prazos para destinatários em uma tabela específica.
    Se apenas_primeiro=True, seleciona apenas o polo ativo (clicando no ícone verde).
    """
    try:
        logger.info(f'[PRAZOS] Preenchendo prazos: {prazo}')

        # Aguardar tabela de prazos carregar
        if espera.ate_js(driver, "__pjeEls('table.t-class tr.ng-star-inserted').length > 0", teto=20):
            logger.info('[PRAZOS] Tabela de destinatários carregada')
            # FIX fluxo: só interagir com o painel depois dele ASSENTAR (linhas
            # estáveis + sem overlay) — clique em painel ainda hidratando não
            # tem efeito e a seleção fica no default (todas marcadas).
            _aguardar_painel_destinatarios_assentar(driver)
        else:
            logger.warning('[PRAZOS] Tabela de destinatários não carregou no tempo esperado')
            return False

        # Se apenas_primeiro, clicar no botão "Selecionar polo ativo"
        if apenas_primeiro:
            try:
                # Seletores para botão polo ativo (padrão PJe 2.18+ e legado)
                btn_polo_alvo = None
                for sel in ['#selecionar-polo-ativo', 'button[aria-label*="polo ativo" i]', 'button[name="btnIntimarSomentePoloAtivo"]']:
                    if espera.ate_habilitar(driver, sel, teto=10):
                        try:
                            btn_polo_alvo = driver.find_element(By.CSS_SELECTOR, sel)
                            break
                        except Exception:
                            continue

                if not btn_polo_alvo:
                    logger.error('[PRAZOS] Botão #selecionar-polo-ativo não habilitou — aborta')
                    return False

                # Scroll antes do click: garante que o botão está no viewport
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
                        btn_polo_alvo,
                    )
                except Exception:
                    pass

                # Limpa overlays residuais antes do clique
                try:
                    driver.execute_script("""
                        document.querySelectorAll('.cdk-overlay-backdrop, .cdk-overlay-pane, snack-bar-container, simple-snack-bar').forEach(function(el){
                            if (el.style) el.style.display = 'none';
                        });
                    """)
                except Exception:
                    pass

                # Clique real com fallback sintético
                try:
                    btn_polo_alvo.click()
                except Exception as e:
                    logger.warning(f'[PRAZOS] Clique real falhou ({type(e).__name__}); tentando clique sintético')
                    if not safe_click_no_scroll(driver, btn_polo_alvo, log=False):
                        driver.execute_script("arguments[0].click();", btn_polo_alvo)

                espera.assentar(driver, 0.5)

                # Confirmação do efeito nos checkboxes de destinatários:
                # O botão nativo do PJe marca o polo ativo e desmarca os demais polos.
                js_checa_destinatarios = (
                    "var linhas = Array.from(document.querySelectorAll('table.t-class tbody tr.ng-star-inserted'));"
                    "var total = linhas.length;"
                    "var marcados = 0;"
                    "linhas.forEach(function(tr){"
                    "  var cb = tr.querySelector('input[type=checkbox]');"
                    "  if (cb && (cb.checked || cb.getAttribute('aria-checked') === 'true')) marcados++;"
                    "});"
                    "return {total: total, marcados: marcados};"
                )

                confirmado = False
                for tentativa in range(1, 4):
                    try:
                        res = driver.execute_script(js_checa_destinatarios) or {}
                        total_linhas = int(res.get('total', 0))
                        marcados = int(res.get('marcados', 0))
                    except Exception:
                        total_linhas, marcados = 0, 0

                    if total_linhas <= 1 and marcados == 1:
                        confirmado = True
                        break
                    elif total_linhas > 1 and 0 < marcados < total_linhas:
                        confirmado = True
                        break

                    logger.warning(f'[PRAZOS] Polo ativo ainda não confirmado (marcados={marcados}/{total_linhas}) — tentativa {tentativa}/3')
                    espera.assentar(driver, 0.8)
                    try:
                        driver.execute_script("arguments[0].click();", btn_polo_alvo)
                    except Exception:
                        pass
                    espera.assentar(driver, 0.5)

                # Se após 3 tentativas ainda estiver com todas marcadas (caso raro de falha no listener Angular),
                # desmarca manualmente as linhas subsequentes mantendo apenas a primeira (polo ativo).
                if not confirmado and total_linhas > 1 and marcados >= total_linhas:
                    logger.warning(f'[PRAZOS] Botão polo ativo não desmarcou outras partes automaticamente ({marcados}/{total_linhas}); aplicando desmarcação manual')
                    driver.execute_script("""
                        var linhas = Array.from(document.querySelectorAll('table.t-class tbody tr.ng-star-inserted'));
                        linhas.forEach(function(tr, idx){
                            if (idx > 0) {
                                var cb = tr.querySelector('input[type=checkbox]');
                                if (cb && (cb.checked || cb.getAttribute('aria-checked') === 'true')) {
                                    var alvo = tr.querySelector('mat-checkbox label') || cb;
                                    alvo.click();
                                }
                            }
                        });
                    """)
                    espera.assentar(driver, 0.5)
                    confirmado = True

                if not confirmado and marcados == 0:
                    logger.error(f'[PRAZOS] Nenhuma parte marcada após seleção de polo ativo — aborta')
                    return False

                logger.info(f'[PRAZOS] Polo ativo selecionado com sucesso ({marcados if confirmado else 1}/{total_linhas} partes)')
                espera.assentar(driver, 0.5)
            except Exception as e:
                logger.error(f'[PRAZOS] Erro ao selecionar polo ativo: {e}')
                return False
        else:
            # Selecionar todos e filtrar apenas "Diário" (excluir "Domicílio Eletrônico")
            try:
                # Clicar em "Selecionar todas"
                if espera.ate_habilitar(driver, '#selecionar-todas', teto=10):
                    btn_selecionar_todas = driver.find_element(By.ID, 'selecionar-todas')
                    safe_click_no_scroll(driver, btn_selecionar_todas, log=False)
                    logger.info('[PRAZOS] Todas as partes selecionadas')
                    espera.assentar(driver, 0.5)
                    
                    # Desmarcar aqueles com "Domicílio Eletrônico"
                    linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tbody tr.ng-star-inserted')
                    desmarcados = 0
                    
                    for linha in linhas:
                        try:
                            # Verificar se o campo MEIO contém "Domicílio Eletrônico"
                            meio_elementos = linha.find_elements(By.CSS_SELECTOR, 'td.envio mat-select .mat-select-value-text')
                            if meio_elementos:
                                meio_texto = meio_elementos[0].text.strip()
                                if 'Domicílio Eletrônico' in meio_texto or 'Domicilio Eletronico' in meio_texto:
                                    # Desmarcar checkbox desta linha
                                    checkbox = linha.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                                    if checkbox.is_selected():
                                        checkbox.click()
                                        desmarcados += 1
                                        logger.info(f'[PRAZOS] Desmarcado destinatário com Domicílio Eletrônico')
                        except Exception as e:
                            logger.debug(f'[PRAZOS] Erro ao processar linha: {e}')
                            continue
                    
                    if desmarcados > 0:
                        logger.info(f'[PRAZOS] {desmarcados} destinatário(s) com Domicílio Eletrônico desmarcado(s)')
                        espera.assentar(driver, 0.3)
                else:
                    logger.warning('[PRAZOS] Botão selecionar-todas não habilitou')
            except Exception as e:
                logger.warning(f'[PRAZOS] Erro ao filtrar destinatários: {e}')

        # Se prazo foi fornecido, preenche os campos de prazo APENAS nas linhas selecionadas
        if prazo is not None:
            try:
                linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tbody tr.ng-star-inserted')
                inputs_prazo = []
                for tr in linhas:
                    try:
                        checkbox = tr.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Intimar parte"]')
                        marcado_linha = (
                            checkbox.get_attribute('aria-checked') == 'true'
                            or checkbox.is_selected()
                        )
                        if not marcado_linha:
                            continue
                        input_prazo = tr.find_element(
                            By.CSS_SELECTOR,
                            'mat-form-field.prazo input[type="text"].mat-input-element, mat-form-field.prazo input',
                        )
                        inputs_prazo.append(input_prazo)
                    except Exception:
                        # Linha sem checkbox de intimar ou sem campo de prazo — não selecionável
                        continue

                if not inputs_prazo:
                    logger.warning('[PRAZOS] Nenhum campo de prazo na linha selecionada')
                    return False

                logger.info(f'[PRAZOS] Encontrados {len(inputs_prazo)} campos de prazo')

                for i, input_elem in enumerate(inputs_prazo):
                    try:
                        input_elem.clear()
                        input_elem.send_keys(str(prazo))
                        driver.execute_script("""
                            arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                            arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                        """, input_elem)
                        logger.info(f'[PRAZOS] Campo {i+1} preenchido com prazo: {prazo}')
                    except Exception as e:
                        logger.warning(f'[PRAZOS] Erro ao preencher campo {i+1}: {e}')
                        continue

                espera.assentar(driver, 0.3)

            except Exception as e:
                logger.warning(f'[PRAZOS] Erro ao preencher campos de prazo: {e}')
                return False
        else:
            logger.info('[PRAZOS] Sem prazo numérico definido; destinatários mantidos conforme seleção')

        logger.info('[PRAZOS] Preenchimento de destinatários e prazos concluído')
        return True

    except Exception as e:
        logger.error(f'[PRAZOS] Erro geral ao preencher prazos: {e}')
        return False


def verificar_bloqueio_recente(driver, debug=False):
    '''
    Verifica se existe lembrete de bloqueio com data n�o superior a 100 dias.
    Vers�o simplificada baseada na fun��o original.
    
    Returns:
        bool: True se encontrou bloqueio recente, False caso contr�rio
    '''
    try:
        if debug:
            logger.info('[BLOQUEIOS] Verificando bloqueios recentes...')

        # Procurar por elementos de bloqueio
        elementos_bloqueio = driver.find_elements(By.CSS_SELECTOR, '[class*="bloqueio"], [class*="block"]')

        for elemento in elementos_bloqueio:
            try:
                texto = elemento.text.strip()
                if not texto:
                    continue

                # Procurar por datas no texto
                # Padr�es comuns: DD/MM/YYYY, DD-MM-YYYY, etc.
                padroes_data = [
                    r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',
                    r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b'
                ]

                for padrao in padroes_data:
                    matches = re.findall(padrao, texto)
                    for match in matches:
                        try:
                            if len(match[0]) == 4:  # Formato YYYY-MM-DD
                                ano, mes, dia = int(match[0]), int(match[1]), int(match[2])
                            else:  # Formato DD-MM-YYYY
                                dia, mes, ano = int(match[0]), int(match[1]), int(match[2])

                            data_bloqueio = datetime(ano, mes, dia)
                            dias_diferenca = (datetime.now() - data_bloqueio).days

                            if debug:
                                logger.info(f'[BLOQUEIOS] Data encontrada: {data_bloqueio.date()}, {dias_diferenca} dias atr�s')

                            # Verificar se est� dentro de 100 dias
                            if 0 <= dias_diferenca <= 100:
                                logger.info(f'[BLOQUEIOS] Bloqueio recente encontrado: {data_bloqueio.date()} ({dias_diferenca} dias)')
                                return True

                        except ValueError:
                            continue  # Data inv�lida, continuar procurando

            except Exception as e:
                if debug:
                    logger.warning(f'[BLOQUEIOS] Erro ao processar elemento: {e}')
                continue

        if debug:
            logger.info('[BLOQUEIOS] Nenhum bloqueio recente encontrado')
        return False

    except Exception as e:
        logger.error(f'[BLOQUEIOS] Erro ao verificar bloqueios: {e}')
        return False
