"""SISB.processamento_campos_reus — configuração de valor/opções (re-exporta _processar_reus_otimizado)."""

import logging

from Fix import espera
from .processamento.minutas_reus import _processar_reus_otimizado  # noqa: F401
from .utils import criar_js_otimizado, log_sisbajud  # noqa: F401

logger = logging.getLogger(__name__)


def _configurar_valor(driver, dados_processo):
    """Configura valor da dívida se disponível."""
    try:
        divida = dados_processo.get('divida', {})
        valor = divida.get('valor')
        data_divida = divida.get('data', '')

        if valor:
            log_sisbajud(f"Configurando valor: {valor}")

            script_valor = f"""
            var ancora = document.querySelector('div[class="label-valor-extenso"]');
            if (ancora && !document.getElementById('maisPJe_valor_execucao')) {{
                var span = document.createElement('span');
                span.id = 'maisPJe_valor_execucao';
                span.innerText = "Última atualização do processo: {valor} em {data_divida}";
                span.style = "color: white; background-color: slategray; padding: 10px; border-radius: 10px; cursor: pointer; font-weight: bold; margin: 5px 0;";
                span.onclick = function() {{
                    var input = document.querySelector('input[placeholder*="Valor aplicado a todos"]');
                    if (input) {{
                        input.value = "{valor}";
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }};
                ancora.appendChild(document.createElement('br'));
                ancora.appendChild(document.createElement('br'));
                ancora.appendChild(span);
            }}
            return true;
            """

            espera._executar_script(driver, script_valor)
            espera.ate_aparecer(driver, '#maisPJe_valor_execucao', teto=1)

            espera._executar_script(driver, """
            var overlay = document.getElementById('maisPJe_valor_execucao');
            if (overlay) {
                overlay.click();
                return true;
            }
            return false;
            """)

            espera.assentar(driver, 1)

            espera._executar_script(driver, """
            var botaoConfirmar = document.querySelector('button.btn-adicionar.mat-mini-fab.mat-primary mat-icon.fa-check-square');
            if (botaoConfirmar) {
                botaoConfirmar.closest('button').click();
                return true;
            }
            return false;
            """)

            log_sisbajud("Valor configurado")

    except Exception as e:
        log_sisbajud(f"Erro ao configurar valor: {e}")

def _configurar_opcoes_adicionais(driver, dados_processo):
    """Configura opções adicionais como conta-salário."""
    try:
        if dados_processo.get('sisbajud', {}).get('contasalario', '').lower() == 'sim':
            espera._executar_script(driver, """
            var toggles = document.querySelectorAll('mat-slide-toggle label');
            for (var i = 0; i < toggles.length; i++) {
                toggles[i].click();
            }
            """)
            log_sisbajud("Conta-salário ativada")

    except Exception as e:
        log_sisbajud(f"Erro ao configurar opções adicionais: {e}")
