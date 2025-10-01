# teste.py - Teste isolado da juntada SISBAJUD wrapper_parcial# teste.py - Teste isolado da juntada SISBAJUD

import timeimport time

from driver_config import criar_driver, login_funcfrom driver_config import criar_driver, login_func, exibir_configuracao_ativa



def main():def testar_juntada_wrapper_parcial(driver, numero_processo):

    # 1. Criar driver e fazer login    """Testa a juntada usando wrapper_parcial"""

    print("[TESTE] Criando driver...")    print("\n[TESTE] ===== INICIANDO TESTE DE JUNTADA =====")

    driver = criar_driver(headless=False)    

        try:

    print("[TESTE] Fazendo login...")        # Importar wrapper_parcial

    login_func(driver)        from anexos import wrapper_parcial

            

    # 2. Navegar para processo        print("[TESTE] Executando wrapper_parcial...")

    numero_processo = "1242007"        print(f"[TESTE] Processo: {numero_processo}")

    url = f"https://pje.trt2.jus.br/pjekz/processo/{numero_processo}/detalhe"        print("[TESTE] Modelo: xsisbp")

    print(f"[TESTE] Navegando para: {url}")        print("[TESTE] Relatório: relatorio_sisbajud.txt")

    driver.get(url)        

    time.sleep(3)        # Executar juntada

            resultado = wrapper_parcial(

    # 3. Executar wrapper_parcial            driver=driver,

    print("\n[TESTE] ===== EXECUTANDO WRAPPER_PARCIAL =====\n")            numero_processo=numero_processo,

    from anexos import wrapper_parcial            debug=True,

                tipo='Certidão',

    resultado = wrapper_parcial(            descricao='Consulta sisbajud POSITIVA',

        driver=driver,            modelo='xsisbp',

        numero_processo=numero_processo,            assinar='nao',

        debug=True,            sigilo='nao'

        tipo='Certidão',        )

        descricao='Consulta sisbajud POSITIVA',        

        modelo='xsisbp',        if resultado:

        assinar='nao',            print("\n[TESTE] ✅ JUNTADA EXECUTADA COM SUCESSO!")

        sigilo='nao'            print("[TESTE] Aguarde 10 segundos para verificar o resultado...")

    )            time.sleep(10)

            else:

    print(f"\n[TESTE] ===== RESULTADO: {'✅ SUCESSO' if resultado else '❌ FALHA'} =====\n")            print("\n[TESTE] ❌ JUNTADA FALHOU!")

            

    # 4. Aguardar para verificar        return resultado

    input("[TESTE] Pressione ENTER para fechar...")        

    driver.quit()    except Exception as e:

        print(f"\n[TESTE] ❌ ERRO NO TESTE: {e}")

if __name__ == "__main__":        import traceback

    main()        traceback.print_exc()

        return False

def main():
    """Função principal do teste"""
    print("=" * 70)
    print("TESTE DE JUNTADA SISBAJUD - wrapper_parcial")
    print("=" * 70)
    
    # 1. Mostrar configuração ativa
    print("[TESTE] Verificando configuração ativa...")
    exibir_configuracao_ativa()

    # 2. Criar driver
    print("[TESTE] Criando driver...")
    driver = criar_driver(headless=False)
    if not driver:
        print('[TESTE] ❌ Falha ao criar driver')
        return False

    # 3. Fazer login
    print("[TESTE] Fazendo login...")
    login_ok = login_func(driver)
    if not login_ok:
        print('[TESTE] ❌ Falha no login')
        try:
            driver.quit()
        except Exception:
            pass
        return False

    print("[TESTE] ✅ Login realizado com sucesso")

    # 4. Navegar para processo 1242007
    numero_processo = "1242007"
    url_processo = f"https://pje.trt2.jus.br/pjekz/processo/{numero_processo}/detalhe"
    print(f"[TESTE] Navegando para: {url_processo}")
    try:
        driver.get(url_processo)
        print("[TESTE] ✅ Navegação realizada")
        time.sleep(3)
    except Exception as e:
        print(f"[TESTE] ❌ Erro na navegação: {e}")
        try:
            driver.quit()
        except Exception:
            pass
        return False

    # 5. Executar teste de juntada
    print("\n[TESTE] Iniciando teste de juntada...")
    resultado = testar_juntada_wrapper_parcial(driver, numero_processo)
    
    if resultado:
        print("\n[TESTE] 🎉 TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("\n[TESTE] ⚠️  TESTE FALHOU - Verifique os logs acima")
    
    print("\n[TESTE] Pressione ENTER para fechar o navegador...")
    input()
    
    # 6. Fechar driver
    try:
        driver.quit()
        print("[TESTE] ✅ Driver fechado")
    except Exception:
        pass
    
    return resultado

if __name__ == "__main__":
    main()
    return resultado
        print("[TESTE] Executando mov_fimsob...")
        resultado_fimsob = mov_fimsob(driver, debug=True, skip_open_task=False)
        
        if not resultado_fimsob:
            print("[TESTE] ❌ mov_fimsob falhou")
            input("[TESTE] Pressione ENTER para fechar...")
            try:
                driver.quit()
            except Exception:
                pass
            return False
        
        print("[TESTE] ✅ mov_fimsob executado com sucesso")
        
        # Aguardar URL /transicao
        print("[TESTE] Aguardando URL /transicao...")
        for tentativa in range(30):
            time.sleep(1)
            current_url = driver.current_url
            print(f"[TESTE] [{tentativa+1}] URL: {current_url}")
            if '/transicao' in current_url:
                print("[TESTE] ✅ /transicao detectada")
                break
        
        if '/transicao' not in driver.current_url:
            print("[TESTE] ❌ /transicao não detectada")
            input("[TESTE] Pressione ENTER para fechar...")
            try:
                driver.quit()
            except Exception:
                pass
            return False
        
        # Executar ato_fal
        print("[TESTE] Executando ato_fal...")
        resultado_fal = ato_fal(driver, debug=True)
        
        if resultado_fal:
            print("[TESTE] ✅ ato_fal executado com sucesso")
            print("[TESTE] ✅ Fluxo juízo universal concluído!")
        else:
            print("[TESTE] ❌ ato_fal falhou")
        
        input("[TESTE] Pressione ENTER para fechar...")
        
    except Exception as e:
        print(f"[TESTE] ❌ Erro na execução: {e}")
        import traceback
        traceback.print_exc()
        input("[TESTE] Pressione ENTER para fechar...")

    # Fechar driver
    try:
        driver.quit()
    except Exception:
        pass

if __name__ == "__main__":
    main()