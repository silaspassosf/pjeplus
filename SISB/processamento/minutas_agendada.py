import logging
import time

logger = logging.getLogger(__name__)

"""
SISB Minutas - Criacao de minuta agendada
"""


def _criar_minuta_agendada(driver, dados_processo, reus_ja_processados, prazo_dias=30, log=True):
    """
    Cria segunda minuta identica a primeira, mas com agendamento.
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
                import re
                match = re.search(r'(https://[^/]+/sisbajud/[^/]+/teimosinha)', url_atual)
                if match:
                    url_listagem = match.group(1)
                    driver.get(url_listagem)
                    if log:
                        _ = url_listagem
                    time.sleep(2)
                else:
                    return False
            except Exception as e:
                if log:
                    logger.error(f'[SISBAJUD]  Erro ao navegar para listagem: {e}')
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

        from .. import processamento
        processamento._configurar_valor(driver, dados_processo)

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

        from datetime import datetime, timedelta
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

        if log:
            _ = minuta_salva

        time.sleep(1)
        driver.execute_script(script_voltar)
        time.sleep(1)

        return True

    except Exception as e:
        if log:
            logger.error(f'[SISBAJUD]  Erro ao criar minuta agendada: {e}')
        return False