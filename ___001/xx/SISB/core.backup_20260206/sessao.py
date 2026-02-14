import json
import os
import time

from .driver import driver_sisbajud
from .login import login_automatico_sisbajud, login_manual_sisbajud

"""
SISB Core - Sessao
"""

processo_dados_extraidos = None


def salvar_dados_processo_temp(params_adicionais=None):
    """Salva dados do processo no arquivo do projeto (dadosatuais.json)."""
    try:
        project_path = os.path.dirname(os.path.abspath(__file__))
        dados_path = os.path.join(project_path, 'dadosatuais.json')

        dados_para_salvar = processo_dados_extraidos.copy()
        if params_adicionais:
            dados_para_salvar['parametros_automacao'] = params_adicionais
            print(f'[SISBAJUD] Parametros de automacao adicionados: {params_adicionais}')

        with open(dados_path, 'w', encoding='utf-8') as f:
            json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
        print(f'[SISBAJUD] Dados do processo salvos em: {dados_path}')
    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha ao salvar dados do processo: {e}')


def iniciar_sisbajud(driver_pje=None, extrair_dados=False):
    """
    Funcao unificada de inicializacao do SISBAJUD.
    """
    global processo_dados_extraidos

    try:
        print('[SISBAJUD] ============================================')
        print('[SISBAJUD] Iniciando sessao SISBAJUD...')
        print(f'[SISBAJUD][DEBUG] extrair_dados={extrair_dados}, driver_pje presente={driver_pje is not None}')
        print('[SISBAJUD] ============================================')

        if extrair_dados and driver_pje:
            print('[SISBAJUD] Extraindo dados do processo PJe...')
            from Fix import extrair_dados_processo
            processo_dados_extraidos = extrair_dados_processo(driver_pje)
            if processo_dados_extraidos:
                numero_lista = processo_dados_extraidos.get("numero", [])
                numero_display = numero_lista[0] if numero_lista else "N/A"
                print(f'[SISBAJUD] Dados extraidos: {numero_display}')
                salvar_dados_processo_temp()
            else:
                print('[SISBAJUD] Nao foi possivel extrair dados do processo')
        elif extrair_dados and not driver_pje:
            print('[SISBAJUD] Driver PJE nao fornecido, nao e possivel extrair dados')

        print('[SISBAJUD] Criando driver Firefox SISBAJUD...')
        driver = driver_sisbajud()

        if not driver:
            print('[SISBAJUD] Falha ao criar driver - driver_sisbajud() retornou None')
            return None

        try:
            from bacen import carregar_cookies_sisbajud
        except Exception:
            carregar_cookies_sisbajud = None

        cookie_restored = False
        if carregar_cookies_sisbajud:
            try:
                if carregar_cookies_sisbajud(driver):
                    print('[SISBAJUD] Cookies SISBAJUD carregados com sucesso; pulando login.')
                    cookie_restored = True
            except Exception:
                cookie_restored = False

        try:
            from driver_config import criar_driver_sisb, criar_driver_sisb_notebook, salvar_cookies_sessao, salvar_cookies_sisbajud, SALVAR_COOKIES_AUTOMATICO
        except Exception:
            criar_driver_sisb = None
            criar_driver_sisb_notebook = None
            salvar_cookies_sessao = None
            SALVAR_COOKIES_AUTOMATICO = False

        login_ok = False
        if cookie_restored:
            login_ok = True

        if not login_ok and carregar_cookies_sisbajud:
            try:
                if carregar_cookies_sisbajud(driver):
                    print('[SISBAJUD] Cookies SISBAJUD (bacen) carregados com sucesso; pulando login.')
                    login_ok = True
            except Exception:
                pass

        if not login_ok:
            try:
                print('[SISBAJUD] Tentando login automatico SISBAJUD...')
                resultado_login = login_automatico_sisbajud(driver)
                print(f'[SISBAJUD][DEBUG] Resultado do login_automatico_sisbajud: {resultado_login}')

                if resultado_login is True:
                    login_ok = True
                    print('[SISBAJUD] Login automatico bem-sucedido')
                    try:
                        if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sisbajud:
                            salvar_cookies_sisbajud(driver, info_extra='login_automatico_sisbajud')
                    except Exception:
                        pass
                elif resultado_login == 'manual_needed':
                    print('[SISBAJUD] Login automatico requer intervencao manual')
                    if login_manual_sisbajud(driver, aguardar_url_final=True):
                        login_ok = True
                        print('[SISBAJUD] Login completado manualmente com sucesso')
                        try:
                            if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sisbajud:
                                salvar_cookies_sisbajud(driver, info_extra='login_manual_pos_automatico')
                        except Exception:
                            pass
                    else:
                        print('[SISBAJUD] Login manual nao foi concluido')
                else:
                    print(f'[SISBAJUD] Login automatico retornou: {resultado_login}')
            except Exception as e:
                print(f'[SISBAJUD] Erro no login automatico SISBAJUD: {e}')
                import traceback
                traceback.print_exc()

        if not login_ok:
            try:
                print('[SISBAJUD] Aguardando login manual SISBAJUD...')
                if login_manual_sisbajud(driver):
                    login_ok = True
                    try:
                        if SALVAR_COOKIES_AUTOMATICO and salvar_cookies_sisbajud:
                            salvar_cookies_sisbajud(driver, info_extra='login_manual_sisbajud')
                    except Exception as e:
                        print(f'[SISBAJUD] Falha ao salvar cookies SISBAJUD: {e}')
                else:
                    print('[SISBAJUD] Login manual SISBAJUD falhou ou expirou')
            except Exception as e:
                print(f'[SISBAJUD] Erro durante login manual SISBAJUD: {e}')

        if not login_ok:
            print('[SISBAJUD] Nao foi possivel autenticar no SISBAJUD')
            try:
                driver.quit()
            except Exception:
                pass
            return None

        minuta_indicator = 'sisbajud.cnj.jus.br/minuta'
        url_timeout = 120
        inicio_url = time.time()
        url_ready = False
        while time.time() - inicio_url < url_timeout:
            try:
                current = driver.current_url.lower()
                if minuta_indicator in current:
                    print('[SISBAJUD] URL /minuta detectada')
                    url_ready = True
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not url_ready:
            print('[SISBAJUD] Timeout aguardando a URL /minuta apos login')
            return None

        print('[SISBAJUD] URL /minuta confirmada, aguardando 2 segundos...')
        time.sleep(2)

        try:
            driver.maximize_window()
            print('[SISBAJUD] Janela maximizada')
        except Exception as e:
            print(f'[SISBAJUD] Nao foi possivel maximizar a janela: {e}')

        print('[SISBAJUD] Sessao SISBAJUD inicializada com sucesso')
        return driver

    except Exception as e:
        print(f'[SISBAJUD][ERRO] Falha ao iniciar sessao SISBAJUD: {e}')
        try:
            import traceback
            traceback.print_exc()
        except Exception:
            pass

    return None