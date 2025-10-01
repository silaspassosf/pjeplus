# test.py - Teste isolado da juntada SISBAJUD wrapper_parcial
import time
from driver_config import criar_driver, login_func

if __name__ == '__main__':
    driver = None
    try:
        # 1. Criar driver e fazer login
        print("[TEST] Criando driver...")
        driver = criar_driver(headless=False)
        
        print("[TEST] Fazendo login...")
        login_func(driver)
        
        # 2. Navegar para processo
        numero_processo = "1242007"
        url = f"https://pje.trt2.jus.br/pjekz/processo/{numero_processo}/detalhe"
        print(f"[TEST] Navegando para: {url}")
        driver.get(url)
        time.sleep(3)
        
        # 3. Executar wrapper_parcial
        print("\n[TEST] ===== EXECUTANDO WRAPPER_PARCIAL =====\n")
        from anexos import wrapper_parcial
        
        resultado = wrapper_parcial(
            driver=driver,
            numero_processo=numero_processo,
            debug=True,
            tipo='Certidão',
            descricao='Consulta sisbajud POSITIVA',
            modelo='xsisbp',
            assinar='nao',
            sigilo='nao'
        )
        
        print(f"\n[TEST] ===== RESULTADO: {'✅ SUCESSO' if resultado else '❌ FALHA'} =====\n")
        
        # 4. Aguardar para verificar
        input("[TEST] Pressione ENTER para fechar...")
    
    except Exception as e:
        print(f'[TEST] ❌ Erro durante execução: {e}')
        input('[TEST] Pressione ENTER para fechar...')
    finally:
        if driver:
            print('[TEST] Fechando driver...')
            try:
                driver.quit()
            except Exception:
                pass
    
    print('[TEST] test.py finalizado')
