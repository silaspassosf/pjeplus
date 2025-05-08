import time
from Fix import login_notebook, driver_notebook
from atos import ato_pesquisas

# Parâmetros automatizados para o teste
URL_TESTE = "https://pje.trt2.jus.br/pjekz/processo/6574951/detalhe"

# 1. Login e driver (automatizado)
driver = driver_notebook()
try:
    if not login_notebook(driver):
        raise Exception('Falha no login')
    print('[TESTE] Login realizado com sucesso.')

    # 2. Navegação direta para a URL do teste (automatizada)
    driver.get(URL_TESTE)
    print(f'[TESTE] Navegado para {URL_TESTE}')
    time.sleep(2)

    # 3. Chamada do fluxo/função a ser testado (automatizada)
    print('[TESTE] Executando ato_pesquisas(driver)...')
    resultado = ato_pesquisas(driver)
    print(f'[TESTE] Resultado ato_pesquisas: {resultado}')

    print('[TESTE] Teste finalizado. Fechando navegador...')
    time.sleep(2)

except Exception as e:
    print(f'[TESTE][ERRO] {e}')
finally:
    driver.quit()
    print('[TESTE] Navegador fechado.')
