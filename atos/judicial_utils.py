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
                logger.info('[PRAZOS] Clicando no botão #selecionar-polo-ativo...')
                espera.ate_aparecer(driver, '#selecionar-polo-ativo, button[aria-label="Selecionar polo ativo"]', teto=10)

                # Clique direto no elemento nativo pelo ID
                clicado = driver.execute_script("""
                    const btn = document.getElementById('selecionar-polo-ativo')
                             || document.querySelector('#selecionar-polo-ativo')
                             || document.querySelector('button[aria-label="Selecionar polo ativo"]');
                    if (btn) {
                        btn.click();
                        return true;
                    }
                    return false;
                """)

                if not clicado:
                    btn_polo_alvo = driver.find_element(By.CSS_SELECTOR, '#selecionar-polo-ativo, button[aria-label="Selecionar polo ativo"]')
                    btn_polo_alvo.click()

                espera.assentar(driver, 0.5)
                logger.info('[PRAZOS] Botão #selecionar-polo-ativo clicado com sucesso')
            except Exception as e:
                logger.warning(f'[PRAZOS] Erro ao clicar no botão selecionar-polo-ativo: {e}')
                try:
                    driver.execute_script("const b = document.getElementById('selecionar-polo-ativo'); if (b) b.click();")
                    espera.assentar(driver, 0.5)
                except Exception:
                    pass
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
                    marcado_linha = False
                    mat_chks = tr.find_elements(By.CSS_SELECTOR, 'mat-checkbox')
                    if mat_chks:
                        cls = mat_chks[0].get_attribute('class') or ''
                        if 'mat-checkbox-checked' in cls:
                            marcado_linha = True

                    if not marcado_linha:
                        chks = tr.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                        if chks and (chks[0].is_selected() or chks[0].get_attribute('aria-checked') == 'true'):
                            marcado_linha = True

                    if not marcado_linha:
                        continue

                    inputs_tr = tr.find_elements(
                        By.CSS_SELECTOR,
                        'mat-form-field.prazo input[type="text"].mat-input-element, input[aria-label="Prazo"]',
                    )
                    if inputs_tr:
                        inputs_prazo.extend(inputs_tr)
                except Exception:
                    continue

            # Fallback se a verificação estrita não encontrar
            if not inputs_prazo:
                if apenas_primeiro and linhas:
                    inputs_primeira = linhas[0].find_elements(
                        By.CSS_SELECTOR,
                        'mat-form-field.prazo input[type="text"].mat-input-element, input[aria-label="Prazo"]',
                    )
                    if inputs_primeira:
                        inputs_prazo = inputs_primeira

                if not inputs_prazo:
                    inputs_prazo = driver.find_elements(
                        By.CSS_SELECTOR,
                        'mat-form-field.prazo input[type="text"].mat-input-element',
                    )

            if not inputs_prazo:
                logger.warning('[PRAZOS] Nenhum campo de prazo encontrado')
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
