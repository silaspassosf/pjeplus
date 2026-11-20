"""SISBAJUD Ordens — Seleciona ação por fluxo nos painéis com saldo (desdobrar)."""

import logging
import random

from Fix import espera
from Fix.entrada_campos import _fechar_dropdown_ou_esc

logger = logging.getLogger(__name__)

_JS_FILTER_SELS = """
function _selsComSaldo() {
    return Array.from(document.querySelectorAll('mat-select[name="assessor"]')).filter(function(s) {
        var panel = s.closest('.mat-expansion-panel-content');
        if (panel) {
            var st = window.getComputedStyle(panel);
            if (st.visibility === 'hidden' || panel.style.height === '0px') return false;
        }
        var body = s.closest('.mat-expansion-panel-body');
        if (!body) return false;
        var saldoCell = body.querySelector('td.cdk-column-saldoRemanescente');
        if (saldoCell && saldoCell.textContent.includes('0,01')) return false;
        return !!body.querySelector('.com-acoes') && !body.querySelector('.com-acoes-nao-resposta');
    });
}
"""

_JS_CLICK_OPT = """
var alvo = arguments[0];
var opcoes = Array.from(document.querySelectorAll('mat-option[role="option"]'));
var el = opcoes.find(function(o) { return o.textContent.trim() === alvo; })
      || opcoes.find(function(o) { return o.textContent.trim().indexOf(alvo) >= 0; });
if (el) { el.click(); return el.textContent.trim(); }
return null;
"""


def _aplicar_acao_por_fluxo(driver, tipo_fluxo, log=True, valor_parcial=None):
    """Seleciona a ação em todos os dropdowns com-saldo via JS + Playwright."""
    espera.assentar(driver, 0.5)
    if not espera.ate_aparecer(driver, "mat-select[name='assessor']", teto=5):
        if log:
            logger.error("[_acao] Nenhum mat-select[name='assessor'] encontrado")
        return False

    count = espera._executar_script(driver, _JS_FILTER_SELS + "return _selsComSaldo().length;")
    if not count:
        if log:
            logger.error("[_acao] Nenhum select com-saldo encontrado via JS")
        return False

    if log:
        logger.info("[_acao] %s select(s) com-saldo (JS)", count)

    texto_alvo = 'Transferir valor' if tipo_fluxo == 'POSITIVO' else 'Desbloquear valor'
    js_click_sel = _JS_FILTER_SELS + "var s = _selsComSaldo()[arguments[0]]; if (s) { s.click(); return true; } return false;"
    processados = 0

    for i in range(count):
        if not espera._executar_script(driver, js_click_sel, i):
            if log:
                logger.warning("[_acao] Select com-saldo #%s não encontrado via JS", i)
            continue

        espera.ate_aparecer(driver, 'mat-option[role="option"]', teto=3)
        espera.pausa(driver, random.uniform(0.3, 0.6))
        resultado = espera._executar_script(driver, _JS_CLICK_OPT, texto_alvo)
        if resultado:
            processados += 1
            if log:
                logger.info("[_acao] com-saldo #%s: '%s' selecionado (%s/%s)", i, resultado, processados, count)
        else:
            _fechar_dropdown_ou_esc(driver)
            if log:
                logger.warning("[_acao] com-saldo #%s: opção '%s' não encontrada no overlay", i, texto_alvo)

        espera.pausa(driver, random.uniform(0.25, 0.5))

    return processados > 0
