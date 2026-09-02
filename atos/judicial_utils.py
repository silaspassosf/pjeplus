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
        else:
            logger.warning('[PRAZOS] Tabela de destinatários não carregou no tempo esperado')
            return False

        # Se apenas_primeiro, clicar no botão "Selecionar polo ativo"
        if apenas_primeiro:
            try:
                if not espera.ate_habilitar(driver, '#selecionar-polo-ativo', teto=15):
                    logger.error('[PRAZOS] #selecionar-polo-ativo não habilitou — aborta')
                    return False
                btn_polo_alvo = driver.find_element(By.ID, 'selecionar-polo-ativo')
                # SEMPRE clicar em "polo ativo" quando apenas_primeiro: o botão seleciona
                # SOMENTE o primeiro destinatário. Não há guarda de idempotência aqui —
                # se a tabela abriu com destinatários já marcados, pular o clique
                # deixaria todos selecionados (prazo aplicado a todos, não ao primeiro).
                # Clique REAL (WebDriver/Playwright), não o dispatchEvent sintético
                # do safe_click_no_scroll — o sintético não efetiva no mat-icon-button.
                # Antes, limpa overlays residuais: o backdrop do Angular intercepta
                # o clique real e o faz travar 30s em actionability.
                try:
                    driver.execute_script("""
                        document.querySelectorAll('.cdk-overlay-backdrop, .cdk-overlay-pane, snack-bar-container, simple-snack-bar').forEach(function(el){
                            if (el.style) el.style.display = 'none';
                        });
                    """)
                except Exception:
                    pass
                try:
                    btn_polo_alvo.click()
                except Exception as e:
                    # Fallback: clique sintético (dispatchEvent) não exige
                    # actionability e atravessa sobreposição remanescente.
                    logger.warning(f'[PRAZOS] Clique real falhou ({type(e).__name__}); tentando clique sintético')
                    if not safe_click_no_scroll(driver, btn_polo_alvo, log=False):
                        logger.error('[PRAZOS] Nem clique real nem sintético funcionaram — aborta')
                        return False
                espera.assentar(driver, 0.5)
                # Confirma o efeito antes de seguir.
                marcado = espera.ate_js(
                    driver,
                    "__pjeEls('table.t-class tbody tr.ng-star-inserted input[type=checkbox]').some(el => el.checked)",
                    teto=5,
                )
                if not marcado:
                    logger.error('[PRAZOS] Polo ativo NÃO confirmado após o clique — aborta')
                    return False
                logger.info('[PRAZOS] Polo ativo selecionado - apenas primeiro destinatário marcado')
                espera.assentar(driver, 0.5)
            except Exception as e:
                logger.error(f'[PRAZOS] Não foi possível clicar em polo ativo: {e}')
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

        # Preenche os campos de prazo APENAS nas linhas selecionadas (checkbox marcado)
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
                        'mat-form-field.prazo input[type="text"].mat-input-element',
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
                    logger.info(f'[PRAZOS] Campo {i+1} preenchido com prazo: {prazo}')
                except Exception as e:
                    logger.warning(f'[PRAZOS] Erro ao preencher campo {i+1}: {e}')
                    continue

            espera.assentar(driver, 0.3)

        except Exception as e:
            logger.warning(f'[PRAZOS] Erro ao preencher campos de prazo: {e}')
            return False

        logger.info('[PRAZOS] Preenchimento de prazos concluído')
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
