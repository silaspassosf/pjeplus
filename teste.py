#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de execução do script carta.py
URL: https://pje.trt2.jus.br/pjekz/processo/6283693/detalhe

Este arquivo navega para o processo específico e executa apenas o script carta.py
"""

from driver_config import criar_driver, login_func
from carta import carta
import time

def teste_carta():
    """Testa o script carta.py no processo específico."""
    driver = None
    try:
        print('[TESTE] Iniciando teste do carta.py...')
        
        # 1. Criar driver e fazer login
        driver = criar_driver()
        login_success = login_func(driver)
        if not login_success:
            print('[TESTE][ERRO] Falha no login')
            return False
        
        print('[TESTE] Login realizado com sucesso.')
        
        # 2. Navegar para o processo específico
        url_processo = "https://pje.trt2.jus.br/pjekz/processo/6283693/detalhe"
        print(f'[TESTE] Navegando para: {url_processo}')
        driver.get(url_processo)
        time.sleep(5)
        
        print('[TESTE] Página do processo carregada.')
        
        # 3. Executar carta.py
        print('[TESTE] Executando carta.py...')
        print('[TESTE] =====================================')
        
        resultado = carta(driver, log=True)
        
        if resultado:
            print('[TESTE] ✓ carta.py executado com sucesso!')
            print(f'[TESTE] Resultado obtido ({len(resultado)} caracteres)')
        else:
            print('[TESTE] ⚠ carta.py não retornou dados ou encontrou erro.')
        
        return bool(resultado)
        
    except Exception as e:
        print(f'[TESTE][ERRO] Exceção durante teste: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Mantém o navegador aberto para inspeção manual
        print('[TESTE] Mantendo navegador aberto para inspeção manual...')
        print('[TESTE] Pressione Ctrl+C no terminal para encerrar.')
        try:
            input('[TESTE] Pressione Enter para fechar o navegador...')
        except KeyboardInterrupt:
            pass
        
        if driver:
            try:
                driver.quit()
                print('[TESTE] Driver encerrado.')
            except Exception:
                pass

if __name__ == "__main__":
    teste_carta()
