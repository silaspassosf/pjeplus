# teste.py
"""
Script de teste para análise Argos.
"""
from selenium.webdriver.common.by import By
import time
from extrair import extrair_dados_processo

if __name__ == "__main__":
    from driver_config import criar_driver, login_func
    driver = criar_driver(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        exit(1)
    if not login_func(driver):
        print('[ERRO] Falha no login. Encerrando script.')
        driver.quit()
        exit(1)
    print('[TESTE] Login realizado com sucesso.')
    # Teste da automação de movimentação em lote (loop_prazo)
    from loop_prazo import loop_prazo
    print('[TESTE] Executando loop_prazo...')
    resultado = loop_prazo(driver)
    print('[teste.py] Resultado loop_prazo:', resultado)
    print('[TESTE] Execução concluída. A aba do navegador permanecerá aberta para inspeção manual.')
    input('[TESTE] Pressione ENTER para fechar o navegador e encerrar o teste...')
    driver.quit()
