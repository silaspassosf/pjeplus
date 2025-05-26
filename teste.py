# teste.py
"""
Script de teste para login e consulta Infojud no PJe TRT2.
"""
import time
from Fix import driver_pc, login_pc
from apec import acao_bt_apec_selenium, botoes
from p2 import fluxo_pz

def main():
    # Setup driver e login igual m1.py (agora usando driver_pc e login_pc)
    driver = driver_pc(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return
    if not login_pc(driver):
        print('[ERRO] Falha no login. Encerrando script.')
        driver.quit()
        return
    print('[TESTE] Login realizado com sucesso.')
    url_teste = 'https://pje.trt2.jus.br/pjekz/processo/2108106/detalhe'
    print(f'[TESTE] Navegando para a URL de teste: {url_teste}')
    driver.get(url_teste)
    time.sleep(3)  # Aguarda carregamento da página
    print('[TESTE] Executando fluxo_pz (regra especial bloqueio de valores realizado, ora)...')
    fluxo_pz(driver)
    print('[TESTE] Fluxo finalizado. Janela permanecerá aberta para conferência manual.')
    # driver.quit()  # Removido para permitir conferência manual

if __name__ == "__main__":
    main()
