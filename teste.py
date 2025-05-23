# teste.py
"""
Script de teste para login e consulta Infojud no PJe TRT2.
"""
import time
from Fix import driver_pc, login_pc
from apec import acao_bt_apec_selenium, botoes

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
    # Teste localizado: botão "Decisão" em aaComunicacao
    botao_decisao = None
    for botao in botoes['aaComunicacao']:
        if botao.get('nm_botao', '').lower() == 'decisão':
            botao_decisao = botao
            break
    if not botao_decisao:
        print('Botão "Decisão" não encontrado em aaComunicacao.')
        driver.quit()
        return
    else:
        print('Testando fluxo de comunicação para o botão "Decisão"...')
        acao_bt_apec_selenium(driver, botao_decisao)
        # Não executar carta nem outros fluxos aqui!
    print('[TESTE] Fluxo finalizado. Janela permanecerá aberta para conferência manual.')
    # driver.quit()  # Removido para permitir conferência manual

if __name__ == "__main__":
    main()
