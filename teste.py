# teste.py
"""
Script de teste para login manual no PJe TRT2.
Ao rodar, abre o navegador na URL de login e aguarda o usuário realizar o login manualmente.
"""
import time
import Fix

def main():
    """
    Script de teste para login manual no PJe TRT2.
    1. Abre driver notebook e faz login manual.
    2. Após login, detecta automaticamente a URL do quadro de avisos.
    3. Se detectar a URL https://pje.trt2.jus.br/pjekz/quadro-avisos/visualizar, executa o fluxo de teste automaticamente.
    4. Executa pec_decisao de atos.py.
    5. Aguarda usuário, não fecha após erro.
    """
    import time
    import Fix
    from atos import pec_decisao
    from selenium.webdriver.common.by import By
    driver = Fix.driver_notebook(headless=False)
    url_login = 'https://pje.trt2.jus.br/primeirograu/login.seam'
    url_quadro_avisos = 'https://pje.trt2.jus.br/pjekz/quadro-avisos/visualizar'
    url_teste = 'https://pje.trt2.jus.br/pjekz/processo/304338/detalhe'
    print(f"[TESTE] Acesse manualmente: {url_login}")
    driver.get(url_login)
    print("[TESTE] Aguarde e realize o login manualmente no navegador aberto.")
    # Aguarda até que a URL do quadro de avisos seja detectada
    while True:
        time.sleep(1)
        atual = driver.current_url
        if atual.startswith(url_quadro_avisos):
            print("[TESTE] Login detectado! URL do quadro de avisos identificada.")
            break
    print("[TESTE] Login concluído. Prosseguindo automaticamente com o teste...")
    try:
        print(f"[TESTE] Navegando para a URL de teste: {url_teste}")
        driver.get(url_teste)
        time.sleep(2)
        print("[TESTE] Executando pec_decisao(driver)...")
        resultado = pec_decisao(driver)
        print(f"[TESTE] Resultado pec_decisao: {resultado}")
    except Exception as e:
        print(f"[TESTE][ERRO] {e}")
        try:
            from selenium.webdriver.common.by import By
            fa_times = driver.find_elements(By.CSS_SELECTOR, '.fa-times')
            for btn in fa_times:
                if btn.is_displayed():
                    btn.click()
                    print('[TESTE][ERRO] Botão .fa-times clicado para fechar modal.')
                    break
        except Exception as e2:
            print(f'[TESTE][ERRO] Falha ao tentar clicar em .fa-times: {e2}')
        time.sleep(5)  # Pausa para inspeção após erro
    input("Pressione ENTER para encerrar e fechar o navegador...")
    driver.quit()

if __name__ == "__main__":
    main()
