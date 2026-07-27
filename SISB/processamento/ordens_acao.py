import logging
import time
import random

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from Fix import espera

logger = logging.getLogger(__name__)

"""
SISBAJUD Ordens - Selecionar acao por fluxo

Estrutura real do HTML /desdobrar (confirmada em doc.txt):
  Cada instituicao tem painel expansion com div:
    class="com-acoes"              -> banco COM saldo -> recebe acao do fluxo
    class="com-acoes-nao-resposta" -> sem resposta (98) -> Cancelar/Reiterar/blank
  Paineis sem resposta de saldo (codigo 02) ficam COLLAPSED (visibility:hidden).
"""


def _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=True, valor_parcial=None):
    """
    Seleciona a ação em todos os dropdowns com-saldo via JS puro.
    Não usa referências Python (evita StaleElementReferenceException).
    Cada interação faz query fresh no DOM — idêntico ao que funciona no console.
    """
    espera.assentar(driver, 0.5)

    if not espera.ate_aparecer(driver, "mat-select[name='assessor']", teto=5):
        if log:
            logger.error("[_acao] Nenhum mat-select[name='assessor'] encontrado")
        return False

    # JS: conta selects visíveis em painéis com-saldo (sem nao-resposta)
    JS_SELS = """
        return Array.from(document.querySelectorAll('mat-select[name="assessor"]')).filter(function(s) {
            var panel = s.closest('.mat-expansion-panel-content');
            if (panel) {
                var st = window.getComputedStyle(panel);
                if (st.visibility === 'hidden' || panel.style.height === '0px') return false;
            }
            var body = s.closest('.mat-expansion-panel-body');
            if (!body) return false;
            
            var saldoCell = body.querySelector('td.cdk-column-saldoRemanescente');
            if (saldoCell && saldoCell.textContent.includes('0,01')) {
                return false;
            }
            
            return !!body.querySelector('.com-acoes') && !body.querySelector('.com-acoes-nao-resposta');
        }).length;
    """
    count = driver.execute_script(JS_SELS)

    if not count:
        if log:
            logger.error("[_acao] Nenhum select com-saldo encontrado via JS")
        return False

    if log:
        logger.info(f"[_acao] {count} select(s) com-saldo (JS)")

    texto_alvo = 'Transferir valor' if tipo_fluxo == 'POSITIVO' else 'Desbloquear valor'
    processados = 0

    # JS: clica o i-ésimo select com-saldo (query fresh)
    JS_CLICK_SEL = """
        var sels = Array.from(document.querySelectorAll('mat-select[name="assessor"]')).filter(function(s) {
            var panel = s.closest('.mat-expansion-panel-content');
            if (panel) {
                var st = window.getComputedStyle(panel);
                if (st.visibility === 'hidden' || panel.style.height === '0px') return false;
            }
            var body = s.closest('.mat-expansion-panel-body');
            if (!body) return false;
            
            var saldoCell = body.querySelector('td.cdk-column-saldoRemanescente');
            if (saldoCell && saldoCell.textContent.includes('0,01')) {
                return false;
            }
            
            return !!body.querySelector('.com-acoes') && !body.querySelector('.com-acoes-nao-resposta');
        });
        if (sels[arguments[0]]) { sels[arguments[0]].click(); return true; }
        return false;
    """

    # JS: clica a opção correta no overlay (query fresh)
    JS_CLICK_OPT = """
        var alvo = arguments[0];
        var opcoes = Array.from(document.querySelectorAll('mat-option[role="option"]'));
        var el = opcoes.find(function(o) { return o.textContent.trim() === alvo; });
        if (!el) el = opcoes.find(function(o) { return o.textContent.trim().indexOf(alvo) >= 0; });
        if (el) { el.click(); return el.textContent.trim(); }
        return null;
    """

    for i in range(count):
        clicou = driver.execute_script(JS_CLICK_SEL, i)
        if not clicou:
            if log:
                logger.warning(f"[_acao] Select com-saldo #{i} não encontrado via JS")
            continue

        time.sleep(random.uniform(0.7, 1.2))  # aguarda overlay do Angular Material abrir (jitter anti-deteccao)

        resultado = driver.execute_script(JS_CLICK_OPT, texto_alvo)

        if resultado:
            processados += 1
            if log:
                logger.info(f"[_acao] com-saldo #{i}: '{resultado}' selecionado ({processados}/{count})")
        else:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            if log:
                logger.warning(f"[_acao] com-saldo #{i}: opção '{texto_alvo}' não encontrada no overlay")

        time.sleep(random.uniform(0.25, 0.5))

    return processados > 0
