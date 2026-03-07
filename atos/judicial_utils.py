"""
judicial_utils.py - Utilit�rios para atos judiciais
===================================================

Fun��es utilit�rias para preenchimento de prazos, verifica��o de bloqueios
e cria��o de wrappers para atos judiciais.
"""

from Fix.core import logger
from selenium.webdriver.common.by import By
from Fix.core import preencher_multiplos_campos
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from datetime import datetime, timedelta
from Fix.core import safe_click_no_scroll

def preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=False, perito=False, perito_nomes=None):
    """
    Preenche prazos para destinatários em uma tabela específica.
    Versão baseada no jud.py - mais robusta e compatível.
    """
    # Lista fixa de nomes de peritos
    nomes_peritos_padrao = [
        'ROGERIO APARECIDO ROSA',
        # Adicione outros nomes fixos aqui se necessário
    ]
    if perito_nomes is None:
        perito_nomes = nomes_peritos_padrao

    try:
        logger.info(f'[PRAZOS] Preenchendo prazos: {prazo}')

        # Aguardar tabela de prazos carregar (como no jud.py) - mais tempo
        try:
            WebDriverWait(driver, 20).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')) > 0
            )
            logger.info('[PRAZOS] Tabela de destinatários carregada')
        except Exception:
            logger.warning('[PRAZOS] Tabela de destinatários não carregou no tempo esperado')
            return False

        # Encontra todas as linhas da tabela de destinatários (como no jud.py)
        linhas = driver.find_elements(By.CSS_SELECTOR, 'table.t-class tr.ng-star-inserted')
        if not linhas:
            logger.error('[PRAZOS] Nenhuma linha de destinatário encontrada!')
            return False

        logger.info(f'[PRAZOS] Encontradas {len(linhas)} linhas de destinatários')

        # Filtrar apenas destinatários ativos (checkbox marcado) - abordagem do jud.py
        ativos = []
        for tr in linhas:
            try:
                checkbox = tr.find_element(By.CSS_SELECTOR, 'input[type="checkbox"][aria-label="Intimar parte"]')
                nome_elem = tr.find_element(By.CSS_SELECTOR, '.destinario')
                nome = nome_elem.text.strip().upper()

                # Verifica se já está marcado
                if checkbox.get_attribute('aria-checked') == 'true':
                    ativos.append((tr, checkbox, nome))
                    logger.info(f'[PRAZOS] Destinatário ativo encontrado: {nome}')
                # Se está desmarcado e é perito e perito=True e nome na lista
                elif perito and nome in [n.upper() for n in perito_nomes]:
                    driver.execute_script("arguments[0].click();", checkbox)
                    logger.info(f'[PRAZOS] Perito ativado: {nome}')
                    ativos.append((tr, checkbox, nome))
            except Exception as e:
                logger.warning(f'[PRAZOS] Erro ao processar linha: {e}')
                continue

        if not ativos:
            logger.error('[PRAZOS] Nenhum destinatário ativo!')
            return False

        logger.info(f'[PRAZOS] {len(ativos)} destinatários ativos para preenchimento')

        # Se apenas primeiro, desmarcar os outros
        if apenas_primeiro and len(ativos) > 1:
            logger.info('[PRAZOS] Mantendo apenas o primeiro destinatário...')
            for i, (tr, checkbox, nome) in enumerate(ativos):
                if i == 0:
                    continue
                try:
                    driver.execute_script("arguments[0].click();", checkbox)
                    logger.info(f'[PRAZOS] Destinatário {i+1} desmarcado: {nome}')
                except Exception as e:
                    logger.warning(f'[PRAZOS] Erro ao desmarcar destinatário {i+1}: {e}')
            ativos = [ativos[0]]

        # Preenche prazos usando JavaScript para múltiplos campos (como no jud.py)
        campos_prazo = {}
        for i, (tr, checkbox, nome) in enumerate(ativos):
            try:
                input_prazo = tr.find_element(By.CSS_SELECTOR, 'mat-form-field.prazo input[type="text"].mat-input-element')
                campo_id = f'prazo_destinatario_{i}'
                # Atribui um ID único ao campo se não tiver
                driver.execute_script("arguments[0].id = arguments[1];", input_prazo, campo_id)
                campos_prazo[f'#{campo_id}'] = str(prazo)
                logger.info(f'[PRAZOS] Preparado prazo {prazo} para destinatário: {nome}')
            except Exception as e:
                logger.warning(f'[PRAZOS] Erro ao preparar campo de prazo para {nome}: {e}')
                continue

        # Preenche todos os campos de uma vez usando preencher_multiplos_campos
        if campos_prazo:
            from Fix.core import preencher_multiplos_campos
            resultado = preencher_multiplos_campos(driver, campos_prazo, log=True)
            if all(resultado.values()):
                logger.info(f'[PRAZOS] ✅ Todos os {len(campos_prazo)} campos de prazo preenchidos com sucesso')
            else:
                logger.warning(f'[PRAZOS] ⚠️ Alguns campos de prazo podem não ter sido preenchidos corretamente')
                return False
        else:
            logger.warning('[PRAZOS] Nenhum campo de prazo para preencher')
            return False

        # Após preencher, tentar clicar em "Gravar" se existir (como no jud.py)
        try:
            logger.info('[PRAZOS] Tentando gravar prazos...')

            # Remover overlays que podem interferir
            driver.execute_script("""
                const overlays = document.querySelectorAll('.cdk-overlay-backdrop, .mat-dialog-container, .cdk-overlay-pane');
                overlays.forEach(overlay => {
                    if (overlay.style) overlay.style.display = 'none';
                });

                const snackbars = document.querySelectorAll('snack-bar-container, simple-snack-bar');
                snackbars.forEach(snack => {
                    if (snack.style) snack.style.display = 'none';
                });

                document.body.style.overflow = 'visible';
            """)

            # Procurar botão Gravar (como no jud.py)
            btn_gravar_prazo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space(text())='Gravar'] and contains(@class, 'mat-raised-button') and not(contains(@aria-label, 'movimentos'))]"))
            )

            if btn_gravar_prazo.is_displayed() and btn_gravar_prazo.is_enabled():
                # Usar safe_click_no_scroll em vez de scrollIntoView + click
                if safe_click_no_scroll(driver, btn_gravar_prazo, log=False):
                    logger.info('[PRAZOS] ✅ Prazos gravados via safe_click_no_scroll')
                else:
                    logger.warning('[PRAZOS] Falha em safe_click_no_scroll, tentando .click()')
                    btn_gravar_prazo.click()
                    logger.info('[PRAZOS] ✅ Prazos gravados via Selenium')

                time.sleep(1)
                logger.info('[PRAZOS] ✅ Gravação de prazos concluída')
            else:
                logger.warning('[PRAZOS] Botão Gravar não está disponível')

        except Exception as e:
            logger.warning(f'[PRAZOS] Não foi possível gravar prazos automaticamente: {e}')

        logger.info('[PRAZOS] ✅ Preenchimento de prazos concluído')
        return True

    except Exception as e:
        logger.error(f'[PRAZOS] ❌ Erro geral ao preencher prazos: {e}')
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
