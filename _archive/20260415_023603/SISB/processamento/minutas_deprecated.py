"""
SISB Minutas - Funções DEPRECATED

ATENÇÃO: Este arquivo contém funções que foram removidas do fluxo
principal de minuta_bloqueio. O fluxo atual é:
    salvar → gerar relatório → juntada PJE

As funções abaixo (protocolar, copiar ordem, minuta agendada) estão
isoladas aqui para referência futura ou reativação pontual.
"""

import logging
import time
import os
import random
import re

from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DEPRECATED: _protocolar_minuta
# ---------------------------------------------------------------------------

def _protocolar_minuta(driver, protocolo_minuta=None, log=True):
    """
    [DEPRECATED] Protocola/assina minuta no SISBAJUD.
    Removida do fluxo principal em 2026-03. Mantida para referência.
    """
    try:
        if log:
            _ = protocolo_minuta

        time.sleep(1)

        try:
            script_encontrar_botao = """
            const buttons = Array.from(document.querySelectorAll('button'));
            const protocoloBtn = buttons.find(btn => {
                const spans = btn.querySelectorAll('span.mat-button-wrapper');
                return Array.from(spans).some(span => {
                    const hasIcon = span.querySelector('mat-icon.fa-gavel');
                    const hasText = span.textContent.includes('Protocolar');
                    return hasIcon || hasText;
                });
            });
            if (protocoloBtn) {
                protocoloBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                return true;
            }
            return false;
            """

            encontrado = driver.execute_script(script_encontrar_botao)
            if not encontrado:
                return False

            time.sleep(0.5)

            script_clicar = """
            const buttons = Array.from(document.querySelectorAll('button'));
            const protocoloBtn = buttons.find(btn => {
                const spans = btn.querySelectorAll('span.mat-button-wrapper');
                return Array.from(spans).some(span => {
                    const hasIcon = span.querySelector('mat-icon.fa-gavel');
                    const hasText = span.textContent.includes('Protocolar');
                    return hasIcon || hasText;
                });
            });
            if (protocoloBtn) {
                protocoloBtn.click();
                return true;
            }
            return false;
            """

            clicado = driver.execute_script(script_clicar)
            if not clicado:
                return False

        except Exception as e:
            if log:
                logger.error(f'[DEPRECATED][PROTOCOLO]  Erro ao clicar em "Protocolar": {e}')
            return False

        time.sleep(1)

        try:
            campo_senha = driver.find_element(By.CSS_SELECTOR, 'input[type="password"][formcontrolname="senha"]')
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", campo_senha)
            time.sleep(0.3)

            campo_senha.click()
            time.sleep(0.3)

            senha = os.environ.get('BP_PASS', '')
            for char in senha:
                if random.random() < 0.05:
                    erro_char = chr(random.randint(33, 126))
                    campo_senha.send_keys(erro_char)
                    time.sleep(random.uniform(0.08, 0.18))
                    campo_senha.send_keys(Keys.BACKSPACE)
                    time.sleep(random.uniform(0.08, 0.18))
                campo_senha.send_keys(char)
                time.sleep(random.uniform(0.09, 0.22))

        except Exception as e:
            if log:
                logger.error(f'[DEPRECATED][PROTOCOLO]  Erro ao digitar senha: {e}')
            return False

        time.sleep(0.6)

        try:
            script_confirmar = """
            const buttons = Array.from(document.querySelectorAll('button[type="submit"][color="primary"]'));
            const confirmBtn = buttons.find(btn => {
                const wrapper = btn.querySelector('span.mat-button-wrapper');
                return wrapper && wrapper.textContent.trim() === 'Confirmar';
            });
            if (confirmBtn) {
                confirmBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                return true;
            }
            return false;
            """

            encontrado = driver.execute_script(script_confirmar)

            if not encontrado:
                script_confirmar_alt = """
                const buttons = Array.from(document.querySelectorAll('button'));
                const confirmBtn = buttons.find(btn => btn.textContent.includes('Confirmar'));
                if (confirmBtn) {
                    confirmBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                    return true;
                }
                return false;
                """
                encontrado = driver.execute_script(script_confirmar_alt)

            if not encontrado:
                return False

            time.sleep(0.3)

            script_clicar = """
            const buttons = Array.from(document.querySelectorAll('button[type="submit"][color="primary"]'));
            let confirmBtn = buttons.find(btn => {
                const wrapper = btn.querySelector('span.mat-button-wrapper');
                return wrapper && wrapper.textContent.trim() === 'Confirmar';
            });

            if (!confirmBtn) {
                const allButtons = Array.from(document.querySelectorAll('button'));
                confirmBtn = allButtons.find(btn => btn.textContent.includes('Confirmar'));
            }

            if (confirmBtn) {
                confirmBtn.click();
                return true;
            }
            return false;
            """

            clicado = driver.execute_script(script_clicar)
            if clicado:
                time.sleep(2)

                script_verificar_sucesso = """
                const buttons = Array.from(document.querySelectorAll('button[title="Copiar Dados para Nova Ordem"]'));
                if (buttons.length > 0) {
                    return true;
                }
                const allButtons = Array.from(document.querySelectorAll('button'));
                const copyBtn = allButtons.find(btn => {
                    const icon = btn.querySelector('mat-icon.fa-copy');
                    const text = btn.textContent;
                    return icon && text.includes('Copiar Dados');
                });
                return copyBtn !== undefined;
                """

                sucesso_verificado = False
                for _ in range(10):
                    try:
                        sucesso_verificado = driver.execute_script(script_verificar_sucesso)
                        if sucesso_verificado:
                            break
                    except Exception:
                        pass
                    time.sleep(0.5)

                return bool(sucesso_verificado)

            return False

        except Exception as e:
            if log:
                logger.error(f'[DEPRECATED][PROTOCOLO]  Erro ao confirmar: {e}')
            return False

    except Exception as e:
        if log:
            logger.error(f'[DEPRECATED][PROTOCOLO]  Erro ao protocolar minuta: {e}')
            import traceback
            logger.exception("Erro detectado")
        return False


# ---------------------------------------------------------------------------
# DEPRECATED: _criar_minuta_agendada_por_copia
# ---------------------------------------------------------------------------

def _criar_minuta_agendada_por_copia(driver, dados_processo, log=True):
    """
    [DEPRECATED] Cria segunda minuta agendada usando "Copiar Dados para Nova Ordem".
    Removida do fluxo principal em 2026-03. Mantida para referência.
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

        # Seleciona radio SIM (ID fixo - frágil)
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
                logger.error(f'[DEPRECATED][COPIA]  Erro ao clicar radio SIM: {resultado_radio}')
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
            return None

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

        # Preenche Juiz
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
                logger.error(f'[DEPRECATED][COPIA]  Erro ao preencher juiz: {e}')

        time.sleep(0.5)

        # Calendário repetição (2º ícone)
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
                logger.error(f'[DEPRECATED][COPIA]  Erro ao preencher calendário repetição: {e}')

        time.sleep(0.3)

        try:
            from ..processamento_campos import _configurar_valor
            _configurar_valor(driver, dados_processo)
        except Exception as e:
            if log:
                logger.error(f'[DEPRECATED][COPIA]  Erro ao configurar valor: {e}')

        time.sleep(0.5)

        from .minutas_salvar import _salvar_minuta
        minuta_salva = _salvar_minuta(driver)
        if not minuta_salva:
            return None

        # Protocola a minuta agendada
        _ = _protocolar_minuta(driver, protocolo_minuta=None, log=log)

        # Extrai protocolo
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
                url = driver.current_url
                match = re.search(r'/(\d{10,})/', url)
                if match:
                    protocolo_agendada = match.group(1)
            except Exception:
                pass

        return protocolo_agendada if protocolo_agendada else None

    except Exception as e:
        if log:
            logger.error(f'[DEPRECATED][COPIA]  Erro ao criar minuta agendada por cópia: {e}')
            import traceback
            logger.exception("Erro detectado")
        return None


# ---------------------------------------------------------------------------
# DEPRECATED: _criar_minuta_agendada
# ---------------------------------------------------------------------------

def _criar_minuta_agendada(driver, dados_processo, reus_ja_processados, prazo_dias=30, log=True):
    """
    [DEPRECATED] Cria segunda minuta idêntica à primeira, mas com agendamento.
    Cria a minuta do zero (fallback, sem usar Copiar Dados).
    Removida do fluxo principal em 2026-03. Mantida para referência.
    """
    try:
        _ = reus_ja_processados

        script_voltar = """
        var btnVoltar = document.querySelector('button mat-icon.fa-arrow-left');
        if (btnVoltar) {
            btnVoltar.closest('button').click();
            return true;
        }
        var buttons = document.querySelectorAll('button');
        for (var btn of buttons) {
            if (btn.textContent.toLowerCase().includes('voltar')) {
                btn.click();
                return true;
            }
        }
        return false;
        """

        voltou = driver.execute_script(script_voltar)
        if not voltou:
            try:
                url_atual = driver.current_url
                match = re.search(r'(https://[^/]+/sisbajud/[^/]+/teimosinha)', url_atual)
                if match:
                    url_listagem = match.group(1)
                    driver.get(url_listagem)
                    time.sleep(2)
                else:
                    return False
            except Exception as e:
                if log:
                    logger.error(f'[DEPRECATED]  Erro ao navegar para listagem: {e}')
                return False
        else:
            time.sleep(1.5)

        script_nova_minuta = """
        var botaoNova = document.querySelector('button.mat-fab.mat-primary .fa-plus');
        if (!botaoNova) {
            botaoNova = document.querySelector('button.mat-fab.mat-primary mat-icon');
        }
        if (botaoNova) {
            if (botaoNova.tagName === 'MAT-ICON') {
                botaoNova = botaoNova.closest('button');
            }
            botaoNova.click();
            return true;
        }
        return false;
        """

        sucesso = driver.execute_script(script_nova_minuta)
        if not sucesso:
            return False

        time.sleep(2)

        from .minutas_campos import _preencher_campos_iniciais
        campos_preenchidos = _preencher_campos_iniciais(driver, dados_processo, prazo_dias)
        if not campos_preenchidos:
            return False

        juiz = dados_processo.get('sisbajud', {}).get('juiz', 'Otavio Augusto')
        script_preencher_juiz = f"""
        async function preencherJuiz() {{
            try {{
                let juizInput = document.querySelector('input[placeholder*="Juiz"]');
                if (juizInput) {{
                    juizInput.focus();
                    juizInput.value = '{juiz}';
                    juizInput.dispatchEvent(new Event('input', {{ bubbles: true }}));

                    await new Promise(resolve => setTimeout(resolve, 500));
                    let opcoes = document.querySelectorAll('mat-option[role="option"]');
                    for (let opcao of opcoes) {{
                        if (opcao.textContent.toLowerCase().includes('{juiz.lower()}')) {{
                            opcao.click();
                            return true;
                        }}
                    }}
                }}
                return false;
            }} catch(e) {{
                return false;
            }}
        }}
        return preencherJuiz();
        """

        juiz_preenchido = driver.execute_async_script(script_preencher_juiz)
        _ = juiz_preenchido

        time.sleep(0.5)

        from .minutas_reus import _processar_reus_otimizado
        _processar_reus_otimizado(driver, dados_processo.get('reu', []))

        from ..processamento_campos import _configurar_valor
        _configurar_valor(driver, dados_processo)

        # Marcar radio "SIM" (Teimosinha agendada)
        script_marcar_sim = """
        var radioInputs = document.querySelectorAll('input[type="radio"][name^="mat-radio-group"]');
        for (var input of radioInputs) {
            if (input.value === '2') {
                var radio = input.closest('mat-radio-button');
                if (radio) {
                    var radioGroup = radio.closest('mat-radio-group');
                    if (radioGroup && radioGroup.classList.contains('sisbajud-radio-group')) {
                        var label = radio.querySelector('label');
                        if (label) {
                            label.click();
                            return true;
                        }
                    }
                }
            }
        }
        return false;
        """

        sim_marcado = driver.execute_script(script_marcar_sim)
        if not sim_marcado:
            return False

        time.sleep(1.5)

        data_atual = datetime.now()
        data_agendamento = data_atual + timedelta(days=1)

        if data_atual.weekday() == 4:
            data_agendamento = data_atual + timedelta(days=3)
        elif data_atual.weekday() == 5:
            data_agendamento = data_atual + timedelta(days=2)

        script_abrir_calendario = """
        var todosIcones = document.querySelectorAll('svg.mat-datepicker-toggle-default-icon');
        var iconeAgendamento = null;

        for (var i = 0; i < todosIcones.length; i++) {
            var icone = todosIcones[i];
            if (icone.offsetParent !== null) {
                var parent = icone.closest('.col-md-3');
                if (parent) {
                    var hasRadioGroupBefore = parent.previousElementSibling;
                    if (hasRadioGroupBefore && hasRadioGroupBefore.querySelector('mat-radio-group')) {
                        iconeAgendamento = icone;
                    }
                }
            }
        }

        if (!iconeAgendamento && todosIcones.length > 0) {
            for (var j = todosIcones.length - 1; j >= 0; j--) {
                if (todosIcones[j].offsetParent !== null) {
                    iconeAgendamento = todosIcones[j];
                    break;
                }
            }
        }

        if (iconeAgendamento) {
            var botao = iconeAgendamento.closest('button');
            if (botao) {
                botao.click();
                return true;
            }
        }
        return false;
        """

        calendario_aberto = driver.execute_script(script_abrir_calendario)
        if not calendario_aberto:
            return False

        time.sleep(0.5)

        script_selecionar_data = f"""
        var calendario = document.querySelector('mat-calendar');
        if (!calendario) return false;

        var dia = {data_agendamento.day};
        var celulas = calendario.querySelectorAll('.mat-calendar-body-cell');

        for (var celula of celulas) {{
            var conteudo = celula.querySelector('.mat-calendar-body-cell-content');
            if (conteudo && parseInt(conteudo.textContent.trim()) === dia) {{
                if (!celula.classList.contains('mat-calendar-body-disabled')) {{
                    conteudo.click();
                    return true;
                }}
            }}
        }}
        return false;
        """

        data_selecionada = driver.execute_script(script_selecionar_data)
        if not data_selecionada:
            return False

        time.sleep(0.5)

        from .minutas_salvar import _salvar_minuta
        minuta_salva = _salvar_minuta(driver)
        if not minuta_salva:
            return False

        time.sleep(1)
        driver.execute_script(script_voltar)
        time.sleep(1)

        return True

    except Exception as e:
        if log:
            logger.error(f'[DEPRECATED]  Erro ao criar minuta agendada: {e}')
        return False
