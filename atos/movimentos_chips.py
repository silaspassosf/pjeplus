from typing import Any, List, Optional
import logging
from Fix import espera
from Fix.core import safe_click_no_scroll
from Fix.selectors_pje import BTN_EXPANDIR_CHIPS, CHIPS_LISTA

logger = logging.getLogger(__name__)


def def_chip(driver: Any, numero_processo: str = '', observacao: str = '', chips_para_remover: Optional[List[str]] = None, debug: bool = False, timeout: int = 10) -> bool:
    chips_removidos = 0

    try:
        if chips_para_remover is None:
            chips_para_remover = ["Prazo vencido", "pós sentença"]

        btn_expandir = espera.elemento(driver, BTN_EXPANDIR_CHIPS, teto=2)
        if btn_expandir:
            safe_click_no_scroll(driver, btn_expandir)
            espera.assentar(driver, 1)

        chip_elements = espera.elementos(driver, CHIPS_LISTA, teto=timeout)
        chips_encontrados = []

        for chip_element in chip_elements:
            try:
                chip_text = (getattr(chip_element, 'text', '') or '').strip()
                if any(rem_text in chip_text for rem_text in chips_para_remover):
                    chips_encontrados.append(chip_text)
            except Exception:
                continue

        if not chips_encontrados:
            return True

        for chip_text in chips_encontrados:
            try:
                btn_remover_xpath = f"{CHIPS_LISTA}[contains(., '{chip_text}')]//button[contains(@mattooltip, 'Remover Chip') or contains(@class, 'etq-botao-excluir')]"
                botao_remover = espera.elemento(driver, btn_remover_xpath, teto=3)
                if not botao_remover:
                    continue
                safe_click_no_scroll(driver, botao_remover)
                espera.assentar(driver, 1)

                btn_sim_xpath = "//button[.//span[contains(text(), 'Sim')]]"
                if espera.ate_habilitar(driver, btn_sim_xpath, teto=5):
                    botao_sim = espera.elemento(driver, btn_sim_xpath, teto=2)
                    if botao_sim:
                        safe_click_no_scroll(driver, botao_sim)
                        espera.assentar(driver, 2)
                        chips_removidos += 1
            except Exception as e:
                logger.warning("[CHIPS][REMOVER] #%s: falha ao remover chip '%s': %s", numero_processo, chip_text, e)
                continue

        return chips_removidos > 0
    except Exception as e:
        logger.warning("[CHIPS][ERRO] #%s: erro geral na remocao de chips: %s", numero_processo, e)
        return False
