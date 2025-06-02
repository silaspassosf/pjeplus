# teste.py
"""
Script de teste para análise Argos.
"""
import time
from Fix import driver_pc, login_pc
from infojud import Infojud

def main():
    driver = driver_pc(headless=False)
    if not driver:
        print('[ERRO] Falha ao iniciar o driver.')
        return
    if not login_pc(driver):
        print('[ERRO] Falha no login. Encerrando script.')
        driver.quit()
        return
    print('[TESTE] Login realizado com sucesso.')
    url_teste = 'https://pje.trt2.jus.br/pjekz/processo/3561619/detalhe/peticao/403345675'
    print(f'[TESTE] Navegando para a URL de teste: {url_teste}')
    driver.get(url_teste)
    time.sleep(3)
    print('[TESTE] Chamando infojud...')
    Infojud(driver=driver, usar_perfil_real=True)
    print('[TESTE] Consulta infojud finalizada. Janela permanecerá aberta para conferência manual.')

if __name__ == "__main__":
    main()
