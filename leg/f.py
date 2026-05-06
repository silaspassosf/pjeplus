# ============================================================
# f.py -- Harness de teste isolado: Triagem completa
# Uso: py f.py
# Processo alvo: 8501188
# ============================================================

PROCESS_URL = 'https://pje.trt2.jus.br/pjekz/processo/4409298/detalhe'

# Criar driver PC (opção A do x.py) e fazer login via `login_cpf`
from x import criar_driver_pc
from Fix.utils import login_cpf, navegar_para_tela
from Fix.gigs import criar_comentario
from PEC.regras_pec import determinar_regra
from types import SimpleNamespace
import re


def main():
    driver = criar_driver_pc(headless=False)
    if not driver:
        print('[TESTE][ERRO] Falha ao criar driver')
        return

    # Fazer login via CPF (opção manual/automática configurada em Fix.utils)
    if not login_cpf(driver):
        print('[TESTE][ERRO] Falha no login via login_cpf()')
        try:
            driver.quit()
        except Exception:
            pass
        return

    try:
        print(f'[TESTE] Navegando para processo de teste: {PROCESS_URL}')
        navegar_para_tela(driver, url=PROCESS_URL)

        print('[TESTE] Extraindo dados do processo para SISBAJUD...')
        try:
            from Fix.extracao import extrair_dados_processo
            dados_processo = extrair_dados_processo(driver)
        except Exception as e:
            print('[TESTE] Erro ao extrair dados do processo:', e)
            dados_processo = None

        # Salvar snapshot em dadosatuais.json para inspeção/correções
        try:
            import json
            with open('dadosatuais.json', 'w', encoding='utf-8') as fh:
                json.dump(dados_processo or {}, fh, ensure_ascii=False, indent=2)
            print('[TESTE] dadosatuais.json salvo')
        except Exception as e:
            print('[TESTE] Falha ao salvar dadosatuais.json:', e)

        # Iniciar driver SISBAJUD e realizar login
        try:
            from SISB.core import iniciar_sisbajud, minuta_bloqueio, minuta_bloqueio_60
        except Exception as e:
            print('[TESTE] Erro ao importar SISB.core:', e)
            raise

        print('[TESTE] Iniciando driver SISBAJUD...')
        try:
            driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
        except Exception as e:
            print('[TESTE] Erro ao iniciar SISBAJUD:', e)
            driver_sisb = None

        if not driver_sisb:
            print('[TESTE] Não foi possível iniciar o driver SISBAJUD; abortando ação de minuta')
        else:
            # Executar minuta de bloqueio usando os dados extraídos
            try:
                # Determinar variante 60 dias pela observação (padrão: 30)
                observacao = 'teimosinha'
                if re.search(r'\b60\b|60d|60\s+dias|t2\s*60', observacao, re.IGNORECASE):
                    print('[TESTE] Chamando minuta_bloqueio_60')
                    resultado_sisb = minuta_bloqueio_60(driver_sisb, dados_processo=dados_processo, driver_pje=driver, log=True, fechar_driver=True)
                else:
                    print('[TESTE] Chamando minuta_bloqueio (30 dias padrão)')
                    resultado_sisb = minuta_bloqueio(driver_sisb, dados_processo=dados_processo, driver_pje=driver, log=True, fechar_driver=True)

                print('[TESTE] Resultado SISB:', resultado_sisb)
            except Exception as e:
                print('[TESTE] Erro ao executar minuta SISB:', e)

    finally:
        print('[TESTE] Encerrando driver PJE...')
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    main()

