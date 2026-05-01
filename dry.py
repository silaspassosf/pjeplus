from Fix.core import criar_driver_PC
from PEC.orquestrador import PECOrquestrador

driver = criar_driver_PC()  # abre browser com seu profile PJe
try:
    orq = PECOrquestrador(driver)
    stats = orq.executar(dry_run=True, filtro_d1=True)
    print('Dry-run result:', stats)
finally:
    driver.quit()