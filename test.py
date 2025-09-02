import time
import json
import traceback

# Follow teste.py flow: create driver via sisb.driver_sisbajud(), login, wait ready, then call minuta_bloqueio
from driver_config import exibir_configuracao_ativa
from sisb import driver_sisbajud, login_automatico_sisbajud, aguardar_sisbajud_ready, minuta_bloqueio

DATA_FILE = r"c:\Users\s164283\Desktop\Pjeplus\dadosatuais.json"

if __name__ == '__main__':
    driver = None
    dados = None
    try:
        exibir_configuracao_ativa()

        print('[TEST] Carregando dados de dadosatuais.json...')
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            print('[TEST] ✅ dadosatuais.json carregado')
        except Exception as e:
            print(f'[TEST] ❌ Falha ao carregar dadosatuais.json: {e}')
            raise

        print('[TEST] Criando driver SISBAJUD via sisb.driver_sisbajud()...')
        driver = driver_sisbajud()
        if not driver:
            print('[TEST] ❌ Falha ao criar driver SISBAJUD')
            raise SystemExit(1)

        print('[TEST] Tentando login automático SISBAJUD (login_automatico_sisbajud)...')
        try:
            ok = login_automatico_sisbajud(driver)
            print(f'[TEST] login_automatico_sisbajud returned: {ok}')
        except Exception as e:
            print(f'[TEST] ⚠️ login_automatico_sisbajud raised: {e}')

        print('[TEST] Aguardando SISBAJUD ficar pronto (aguardar_sisbajud_ready)...')
        ready = aguardar_sisbajud_ready(driver, timeout=30)
        print(f'[TEST] SISBAJUD ready: {ready}')

        print('[TEST] Executando minuta_bloqueio usando apenas os dados de dadosatuais.json...')
        resultado = minuta_bloqueio(driver_pje=None, dados_processo=dados, driver_sisbajud=driver)
        print(f'[TEST] Resultado minuta_bloqueio: {resultado}')

        # manter driver aberto para inspeção manual
        time.sleep(5)

    except Exception:
        print('[TEST] ❌ Erro durante execução:')
        traceback.print_exc()
    finally:
        try:
            if driver:
                print('[TEST] Fechando driver SISBAJUD...')
                try:
                    driver.quit()
                except Exception:
                    pass
        except Exception:
            pass

    print('[TEST] test.py finalizado')
