import time
from driver_config import criar_driver_PC, login_automatico
from bloq import bloqsisb
driver = criar_driver_PC()
login_automatico(driver)


# 1. Navegar para a URL do processo (navegação direta)
url_processo = "https://pje.trt2.jus.br/pjekz/processo/4565141/detalhe"
driver.get(url_processo)
time.sleep(3)  # Aguarda carregamento

# 2 . Executar função principal de bloq.py
bloqsisb(driver, log=True)

driver.quit()