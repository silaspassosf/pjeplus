from typing import Any
import logging
from Fix import espera
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.core import safe_click, aguardar_renderizacao_nativa
from Fix.browser_suporte import abrir_em_nova_aba

logger = logging.getLogger(__name__)

XPATH_CONCLUSAO = (
    "//button[contains(translate(normalize-space(text()), 'ÇÃOA', 'çãoa'), 'conclusão ao magistrado') "
    "or contains(normalize-space(text()), 'Conclusão ao magistrado')]"
)
XPATH_ANALISE = (
    "//button[contains(translate(normalize-space(text()), 'ANÁLISE', 'análise'), 'análise')]"
)
XPATH_DESPACHO = (
    "//button[contains(translate(normalize-space(text()), 'DESPACHO', 'despacho'), 'despacho')]"
)


def despacho_generico(driver: Any, peticao: Any) -> bool:
    try:
        if '/detalhe' not in (getattr(driver, 'current_url', '') or ''):
            if not espera.ate_url(driver, '/detalhe', teto=3):
                return False

        btn_abrir_tarefa = espera.elemento(driver, BTN_TAREFA_PROCESSO, teto=10)
        if not btn_abrir_tarefa:
            return False

        nova_aba = abrir_em_nova_aba(driver, lambda: safe_click(driver, btn_abrir_tarefa), timeout=10)
        if nova_aba:
            driver.switch_to.window(nova_aba)

        btn_conclusao = espera.elemento(driver, XPATH_CONCLUSAO, teto=5)
        if not btn_conclusao:
            btn_analise = espera.elemento(driver, XPATH_ANALISE, teto=5)
            if not btn_analise:
                return False
            safe_click(driver, btn_analise)
            aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', 'aparecer', timeout=8)
            btn_conclusao = espera.elemento(driver, XPATH_CONCLUSAO, teto=5)

        if not btn_conclusao:
            return False

        safe_click(driver, btn_conclusao)
        aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', 'aparecer', timeout=8)

        btn_despacho = espera.elemento(driver, XPATH_DESPACHO, teto=5)
        if not btn_despacho:
            return False

        safe_click(driver, btn_despacho)
        aguardar_renderizacao_nativa(driver, timeout=5)
        return True
    except Exception as e:
        proc = getattr(peticao, 'numero_processo', str(peticao))
        logger.warning("[DESPACHO_GENERICO][FALHA] #%s: %s", proc, e)
        return False
