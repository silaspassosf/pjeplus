#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de execução de listaexec.py
URL: https://pje.trt2.jus.br/pjekz/processo/5968134/detalhe
"""

from driver_config import criar_driver, login_func
from listaexec import listaexec
import time

def teste_listaexec():
    """Executa listaexec em um processo específico, sem logs próprios."""
    driver = None
    try:
        driver = criar_driver()
        login_success = login_func(driver)
        if not login_success:
            return False
        url_processo = "https://pje.trt2.jus.br/pjekz/processo/5968134/detalhe"
        driver.get(url_processo)
        time.sleep(5)
        listaexec(driver)
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == "__main__":
    teste_listaexec()
