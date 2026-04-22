import logging
import time

from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

"""
SISB Minutas - Copia e agendamento
"""


def _criar_minuta_agendada_por_copia(driver, dados_processo, log=True):
    """
    Cria segunda minuta agendada usando o botao "Copiar Dados para Nova Ordem".
    """
    try:
        script_copiar = """
        const buttons = Array.from(document.querySelectorAll('button[title="Copiar Dados para Nova Ordem"]'));
        if (buttons.length > 0) {
            buttons[0].scrollIntoView({behavior: 'smooth', block: 'center'});
            return 'found';
        }
        const allButtons = Array.from(document.querySelectorAll('button'));
        const copyBtn = allButtons.find(btn => {
            const icon = btn.querySelector('mat-icon.fa-copy');
            const text = btn.textContent;
            return icon && text.includes('Copiar Dados');
        });
        if (copyBtn) {
            copyBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
            return 'found';
        }
        return 'not_found';
        """

        encontrado = driver.execute_script(script_copiar)
        if encontrado == 'not_found':
            return None

        time.sleep(0.5)

        script_clicar_copiar = """
        const buttons = Array.from(document.querySelectorAll('button[title="Copiar Dados para Nova Ordem"]'));
        if (buttons.length > 0) {
            buttons[0].click();
            return true;
        }
        const allButtons = Array.from(document.querySelectorAll('button'));
        const copyBtn = allButtons.find(btn => {
            const icon = btn.querySelector('mat-icon.fa-copy');
            const text = btn.textContent;
            return icon && text.includes('Copiar Dados');
        });
        if (copyBtn) {
            copyBtn.click();
            return true;
        }
        return false;
        """

        clicado = driver.execute_script(script_clicar_copiar)
        if not clicado:
            return None

        time.sleep(0.8)

        script_confirmar = """
        const buttons = Array.from(document.querySelectorAll('button'));
        const confirmBtn = buttons.find(btn => {
            const wrapper = btn.querySelector('span.mat-button-wrapper');
            return wrapper && wrapper.textContent.trim() === 'Confirmar';
        });
        if (confirmBtn) {
            confirmBtn.click();
            return true;
        }
        return false;
        """

        confirmado = driver.execute_script(script_confirmar)
        if not confirmado:
            return None

        time.sleep(1)

        url_atual = driver.current_url
        if '/copiar-ordem' not in url_atual:
            _ = url_atual

        js_radio_sim = """
        try {
            var cards = Array.from(document.querySelectorAll('mat-card'));
            var cardDados = cards.find(card => {
                var title = card.querySelector('mat-card-title');
                return title && title.textContent.includes('Dados basicos da ordem');
            });

            if (!cardDados) {
                return 'card_not_found';
            }

            var radioSim = cardDados.querySelector('mat-radio-button[id="mat-radio-46"]');
            if (!radioSim) {
                return 'radio_not_found';
            }

            var label = radioSim.querySelector('label');
            if (label) {
                label.click();
                return 'clicked';
            } else {
                return 'label_not_found';
            }
        } catch (e) {
            return 'error: ' + e.message;
        }
        """

        resultado_radio = driver.execute_script(js_radio_sim)
        if resultado_radio != 'clicked':
            if log:
                logger.error(f'[SISBAJUD][COPIA]  Erro ao clicar radio SIM: {resultado_radio}')
            return None

        try:
            radio_input = driver.find_element(By.CSS_SELECTOR, 'input[type="radio"][value="2"]')
            is_checked = radio_input.is_selected()
        except Exception:
            is_checked = True

        if not is_checked:
            return None

        time.sleep(0.5)

        campo_visivel = False
        for tentativa in range(5):
            script_confirmar_campo_data = """
            const inputs = Array.from(document.querySelectorAll('input[placeholder="Data do protocolo:"]'));
            if (inputs.length > 0) {
                return true;
            }
            return false;
            """

            campo_visivel = driver.execute_script(script_confirmar_campo_data)
            if campo_visivel:
                break

            time.sleep(0.5)

        if not campo_visivel:
            if log:
                debug = driver.execute_script("""
                const inputs = Array.from(document.querySelectorAll('input.mat-radio-input[type="radio"]'));
                const estados = inputs.map(i => ({id: i.id, value: i.value, checked: i.checked}));
                return JSON.stringify(estados);
                """)
                _ = debug
            return None

        from datetime import datetime, timedelta
        data_atual = datetime.now()
        weekday = data_atual.weekday()

        if weekday == 4:
            dias_adicionar = 3
        elif weekday == 5:
            dias_adicionar = 2
        else:
            dias_adicionar = 1

        data_agendamento = data_atual + timedelta(days=dias_adicionar)
        dia_agendar = data_agendamento.day

        script_abrir_calendario = """
        const svgs = Array.from(document.querySelectorAll('svg.mat-datepicker-toggle-default-icon'));
        if (svgs.length > 0) {
            const button = svgs[0].closest('button');
            if (button) {
                button.click();
                return true;
            }
        }
        return false;
        """

        calendario_aberto = driver.execute_script(script_abrir_calendario)
        if not calendario_aberto:
            return None

        time.sleep(0.5)

        script_selecionar_dia = f"""
        const cells = Array.from(document.querySelectorAll('.mat-calendar-body-cell'));
        for (const cell of cells) {{
            const content = cell.querySelector('.mat-calendar-body-cell-content');
            if (content && content.textContent.trim() === '{dia_agendar}') {{
                if (!cell.classList.contains('mat-calendar-body-disabled')) {{
                    content.click();
                    return true;
                }}
            }}
        }}
        return false;
        """

        dia_selecionado = driver.execute_script(script_selecionar_dia)
        if not dia_selecionado:
            return None

        time.sleep(0.5)

        try:
            juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')

            script_preencher_juiz = f"""
            const input = document.querySelector('input[placeholder*="Juiz"]');
            if (input) {{
                input.focus();
                input.value = '{juiz}';
                input.dispatchEvent(new Event('input', {{bubbles: true}}));

                return new Promise((resolve) => {{
                    setTimeout(() => {{
                        const opcoes = document.querySelectorAll('span.mat-option-text');
                        for (let opcao of opcoes) {{
                            if (opcao.textContent && opcao.textContent.toUpperCase().includes('{juiz}'.toUpperCase())) {{
                                opcao.click();
                                resolve(true);
                                return;
                            }}
                        }}
                        resolve(false);
                    }}, 800);
                }});
            }}
            return false;
            """

            juiz_preenchido = driver.execute_async_script(script_preencher_juiz)
            _ = juiz_preenchido
        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][COPIA]  Erro ao preencher juiz: {e}')

        time.sleep(0.5)

        try:
            prazo_dias = 30
            data_limite = data_atual + timedelta(days=prazo_dias + 1)
            dia_limite = data_limite.day

            script_abrir_calendario_rep = """
            const svgs = Array.from(document.querySelectorAll('svg.mat-datepicker-toggle-default-icon'));
            if (svgs.length > 1) {
                const button = svgs[1].closest('button');
                if (button) {
                    button.click();
                    return true;
                }
            }
            return false;
            """

            cal_rep_aberto = driver.execute_script(script_abrir_calendario_rep)
            if cal_rep_aberto:
                time.sleep(0.5)

                script_sel_dia_rep = f"""
                const cells = Array.from(document.querySelectorAll('.mat-calendar-body-cell'));
                for (const cell of cells) {{
                    const content = cell.querySelector('.mat-calendar-body-cell-content');
                    if (content && content.textContent.trim() === '{dia_limite}') {{
                        if (!cell.classList.contains('mat-calendar-body-disabled')) {{
                            content.click();
                            return true;
                        }}
                    }}
                }}
                return false;
                """

                dia_rep_selecionado = driver.execute_script(script_sel_dia_rep)
                _ = dia_rep_selecionado
        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][COPIA]  Erro ao preencher calendario repeticao: {e}')

        time.sleep(0.3)

        try:
            from ..processamento_campos import _configurar_valor
            _configurar_valor(driver, dados_processo)
        except Exception as e:
            if log:
                logger.error(f'[SISBAJUD][COPIA]  Erro ao configurar valor: {e}')

        time.sleep(0.5)

        from .minutas_salvar import _salvar_minuta
        minuta_salva = _salvar_minuta(driver)
        if not minuta_salva:
            return None

        from .minutas_protocolo import _protocolar_minuta
        _ = _protocolar_minuta(driver, protocolo_minuta=None, log=log)

        script_extrair_protocolo = """
        const divs = Array.from(document.querySelectorAll('div.col-md-3'));
        for (const div of divs) {
            const label = div.querySelector('div.sisbajud-label');
            if (label && label.textContent.includes('Numero do Protocolo')) {
                const valor = div.querySelector('span.sisbajud-label-valor');
                if (valor) {
                    return valor.textContent.trim();
                }
            }
        }
        return null;
        """

        protocolo_agendada = driver.execute_script(script_extrair_protocolo)

        if not protocolo_agendada:
            try:
                import re
                url = driver.current_url
                match = re.search(r'/(\d{10,})/', url)
                if match:
                    protocolo_agendada = match.group(1)
            except Exception:
                pass

        if protocolo_agendada:
            return protocolo_agendada
        return None

    except Exception as e:
        if log:
            logger.error(f'[SISBAJUD][COPIA]  Erro ao criar minuta agendada por copia: {e}')
            import traceback
            logger.exception("Erro detectado")
        return None