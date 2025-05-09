import time
from Fix import login_notebook, driver_notebook
from atos import ato_pesquisas

# Parâmetros automatizados para o teste
URL_TESTE = "https://pje.trt2.jus.br/pjekz/processo/5638333/detalhe"

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
    try:
        # Tenta fechar modal de erro se existir
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        fa_times = driver.find_elements(By.CSS_SELECTOR, '.fa-times')
        for btn in fa_times:
            if btn.is_displayed():
                btn.click()
                print('[TESTE][ERRO] Botão .fa-times clicado para fechar modal.')
                time.sleep(1)  # Aguarda 1s após o clique
                # Pressiona e solta espaço para confirmar
                driver.switch_to.active_element.send_keys(Keys.SPACE)
                print('[TESTE][ERRO] Tecla espaço pressionada para confirmar.')
                # Aguarda mudança de URL
                url_anterior = driver.current_url
                for _ in range(20):  # Aguarda até 10s
                    time.sleep(0.5)
                    if driver.current_url != url_anterior:
                        print(f'[TESTE][ERRO] URL mudou para {driver.current_url}')
                        break
                else:
                    print('[TESTE][ERRO] URL não mudou após fechar modal.')
                break
    except Exception as e2:
        print(f'[TESTE][ERRO] Falha ao tentar clicar em .fa-times: {e2}')
    time.sleep(5)  # Pausa para inspeção após erro
finally:
    driver.quit()
    print('[TESTE] Navegador fechado.')
