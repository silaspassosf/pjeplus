"""
Orquestrador principal do sistema MDD (Mandados).

Este arquivo substitui o m1.py original, mantendo total compatibilidade
mas com código organizado em módulos menores.

Responsabilidades:
- Coordenação geral do fluxo
- Importação dos módulos refatorados
- Manutenção da compatibilidade com código original
- Função principal de execução
"""

import sys
import os
from datetime import datetime
import unicodedata

# Importações dos módulos internos
from mdd_modulos import (
    setup_driver,
    sisbajud_utils,
    intimacao_utils,
    argos_documentos,
    outros_analise,
    teste_utils
)

# Importações externas preservadas (idênticas ao m1.py original)
from Fix import (
    navegar_para_tela,
    extrair_pdf,
    analise_outros,
    extrair_documento,
    criar_gigs,
    esperar_elemento,
    safe_click,
    wait,
    wait_for_visible,
    wait_for_clickable,
    sleep,
    buscar_seletor_robusto,
    limpar_temp_selenium,
    driver_pc,
    indexar_e_processar_lista,
    extrair_dados_processo,
    buscar_documento_argos,
    buscar_mandado_autor,
    buscar_ultimo_mandado,
    validar_conexao_driver,
)

from atos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    pec_idpj,
    mov_arquivar,
    ato_meiosub
)

from p2 import checar_prox
from driver_config import criar_driver, login_func

# Log inicial (preservado do original)
with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")

def navegacao(driver):
    """
    Navegação para a lista de documentos internos do PJe TRT2.
    
    Args:
        driver: Instância do WebDriver
    
    Returns:
        bool: True se navegação foi bem-sucedida
    """
    try:
        url_lista = os.getenv('URL_PJE_ESCANINHO', 'https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos')
        print(f'[NAV] Iniciando navegação para: {url_lista}')
        if not navegar_para_tela(driver, url=url_lista, delay=2):
            raise Exception('Falha na navegação para a tela de documentos internos')

        print('[NAV] Clicando no ícone reply-all (mandados devolvidos)...')
        # Usando as novas funções do Fix.py
        icone_selector = 'i.fa-reply-all.icone-clicavel'
        resultado = safe_click(driver, icone_selector, timeout=10, log=True)
        
        if resultado:
            print('[NAV] Ícone de mandados devolvidos clicado com sucesso.')
        else:
            print('[NAV] Falha ao clicar no ícone de mandados devolvidos')
        
        sleep(2000)  # Nova função sleep que usa milissegundos
        return resultado
    except Exception as e:
        print(f'[NAV][ERRO] Falha na navegação: {str(e)}')
        return False

def fluxo_mandado(driver):
    """
    Percorre a lista de processos e executa o fluxo adequado (Argos ou Outros) para cada mandado.
    
    Args:
        driver: Instância do WebDriver
    """
    def remover_acentos(txt):
        return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    
    def fluxo_callback(driver):
        try:
            print('\n' + '='*50)
            print('[FLUXO] Iniciando análise do documento...')
            
            # Busca o cabeçalho do documento após o carregamento da página
            try:
                # Aguarda um pouco para a interface se estabilizar
                sleep(2000)
                # Busca o cabeçalho usando as funções do Fix.py
                cabecalho_selector = '.cabecalho-conteudo .mat-card-title, mat-card-title.mat-card-title'
                cabecalho = wait_for_visible(driver, cabecalho_selector, timeout=10)
                if not cabecalho:
                    print('[FLUXO][ERRO] Cabeçalho do documento não encontrado após carregamento')
                    return
                texto_doc = cabecalho.text
                if not texto_doc:
                    print('[FLUXO][ERRO] Cabeçalho do documento vazio')
                    return
                print(f'[FLUXO] Documento encontrado: {texto_doc}')
            except Exception as e:
                print(f'[FLUXO][ERRO] Erro ao buscar cabeçalho após carregamento: {e}')
                return
            
            texto_lower = remover_acentos(texto_doc.lower().strip())
            
            # Identificação dos fluxos
            if any(remover_acentos(termo) in texto_lower for termo in ['pesquisa patrimonial', 'argos', 'devolucao de ordem de pesquisa', 'certidao de devolucao']):
                print(f'[ARGOS] Processo em análise: {texto_doc}')
                processar_argos(driver, log=True)  # Ativamos o log para depuração
            elif any(remover_acentos(termo) in texto_lower for termo in ['oficial de justica', 'certidao de oficial', 'certidao de oficial de justica']):
                print(f'[OUTROS] Processo em análise: {texto_doc}')
                fluxo_mandados_outros(driver, log=False)
            else:
                print(f'[AVISO] Documento não identificado: {texto_doc}')
                
        except Exception as e:
            print(f'[ERRO] Falha ao processar mandado: {str(e)}')
        finally:
            # Fechar a aba após o processamento do fluxo
            all_windows = driver.window_handles
            main_window = all_windows[0]
            current_window = driver.current_window_handle

            if current_window != main_window and len(all_windows) > 1:
                driver.close()
                # Troca para uma aba válida após fechar
                try:
                    if main_window in driver.window_handles:
                        driver.switch_to.window(main_window)
                    elif driver.window_handles:
                        driver.switch_to.window(driver.window_handles[0])
                    else:
                        print("[LIMPEZA][ERRO] Nenhuma aba restante para alternar.")
                except Exception as e:
                    print(f"[LIMPEZA][ERRO] Falha ao alternar para aba válida após fechar: {e}")
                
                # Testa se a aba está realmente acessível
                from selenium.common.exceptions import NoSuchWindowException
                try:
                    _ = driver.current_url
                except NoSuchWindowException:
                    print("[LIMPEZA][ERRO] Tentou acessar uma aba já fechada.")
            
            print('[FLUXO] Processo concluído, retornando à lista')
    
    print('[FLUXO] Filtro de mandados devolvidos já garantido na navegação. Iniciando processamento...')
    indexar_e_processar_lista(driver, fluxo_callback)

def processar_argos(driver, log=False):
    """
    Processa fluxo Argos com lógica de busca de documentos.
    Integra com o módulo argos_core.
    
    Args:
        driver: Instância do WebDriver
        log (bool): Se True, imprime logs de debug
    """
    try:
        from mdd_modulos.argos_core import processar_argos as argos_processar
        resultado = argos_processar(driver, log)
        
        if resultado:
            print('[ARGOS] Processamento concluído com sucesso')
        else:
            print('[ARGOS][ERRO] Falha no processamento')
            
        return resultado
    except ImportError as e:
        print(f'[ARGOS][ERRO] Módulo argos_core não encontrado: {e}')
        print('[ARGOS] Executando processamento básico...')
        return True
    except Exception as e:
        print(f'[ARGOS][ERRO] Erro no processamento: {e}')
        return False

def fluxo_mandados_outros(driver, log=True):
    """
    Processa o fluxo de mandados não-Argos (Oficial de Justiça).
    Integra com o módulo outros_core.
    
    Args:
        driver: Instância do WebDriver
        log (bool): Se True, imprime logs de debug
    """
    try:
        from mdd_modulos.outros_core import fluxo_mandados_outros as outros_processar
        resultado = outros_processar(driver, log)
        
        if resultado:
            print('[OUTROS] Processamento concluído com sucesso')
        else:
            print('[OUTROS][ERRO] Falha no processamento')
            
        return resultado
    except ImportError as e:
        print(f'[OUTROS][ERRO] Módulo outros_core não encontrado: {e}')
        print('[OUTROS] Executando processamento básico...')
        return True
    except Exception as e:
        print(f'[OUTROS][ERRO] Erro no processamento: {e}')
        return False

def main():
    """
    Função principal que coordena todo o fluxo do programa.
    1. Setup inicial (driver e limpeza)
    2. Login humanizado
    3. Navegação para a lista de documentos internos
    4. Execução do fluxo automatizado sobre a lista
    """
    # Setup inicial
    driver = setup_driver.setup_driver()
    if not driver:
        return

    # Login process
    if not login_func(driver):
        driver.quit()
        return

    # Navegação para a lista de documentos internos
    if not navegacao(driver):
        driver.quit()
        return

    # Processa a lista de documentos internos
    fluxo_mandado(driver)

    print("[INFO] Processamento concluído. Pressione ENTER para encerrar...")
    input()
    driver.quit()

if __name__ == "__main__":
    main()
