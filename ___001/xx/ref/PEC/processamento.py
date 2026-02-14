"""Módulo PEC - Processamento de Execução e Cumprimento (PJe)."""

import time
import re
import os
import inspect
import traceback
from typing import Optional, Dict, List, Tuple, Any, Callable, Union
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from .core import (
    carregar_progresso_pec,
    salvar_progresso_pec,
    processo_ja_executado_pec,
    marcar_processo_executado_pec,
    navegar_para_atividades,
    reiniciar_driver_e_logar_pje,
    verificar_acesso_negado_pec,
)

# ===== IMPORTS PESADOS REMOVIDOS (LAZY LOADING) =====
# Movidos para cache sob demanda para carregamento 8-10x mais rápido

# Cache de módulos para lazy loading
_pec_modules_cache = {}

def _lazy_import_pec():
    """Carrega módulos pesados sob demanda (lazy loading)."""
    global _pec_modules_cache
    
    if not _pec_modules_cache:
        from Fix.core import aguardar_e_clicar, esperar_elemento
        from Fix.extracao import extrair_dados_processo, abrir_detalhes_processo, trocar_para_nova_aba, reindexar_linha
        from atos import pec_excluiargos
        
        _pec_modules_cache.update({
            'aguardar_e_clicar': aguardar_e_clicar,
            'esperar_elemento': esperar_elemento,
            'extrair_dados_processo': extrair_dados_processo,
            'abrir_detalhes_processo': abrir_detalhes_processo,
            'trocar_para_nova_aba': trocar_para_nova_aba,
            'reindexar_linha': reindexar_linha,
            'pec_excluiargos': pec_excluiargos,
        })
    
    return _pec_modules_cache

from .regras import determinar_acoes_por_observacao, determinar_acao_por_observacao
from .regras import executar_acao_pec

def executar_acao(driver, acao, numero_processo, observacao, destinatarios_override=None, driver_sisb=None):
    """
    Executa a ação determinada no processo aberto.
    Suporta apenas funções diretas (como P2B) e listas de funções para execução sequencial.
    Detecta a assinatura de cada função para chamar com os argumentos corretos.
    
    Args:
        driver_sisb: Driver SISBAJUD opcional para reutilização (evita criar múltiplos drivers)
    """
    print(f"[AÇÃO] Executando ação '{acao}' para processo {numero_processo}")

    def chamar_funcao_com_assinatura_correta(func, driver, numero_processo, observacao, destinatarios_override):
        """Helper para chamar função com assinatura correta."""
        try:
            sig = inspect.signature(func)
            params = sig.parameters
            
            # Verificar parâmetros disponíveis
            aceita_observacao = 'observacao' in params
            aceita_destinatarios = 'destinatarios_override' in params
            aceita_debug = 'debug' in params
            aceita_numero_processo = 'numero_processo' in params
            aceita_driver_sisb = 'driver_sisb' in params  # ✨ NOVO: Verificar se aceita driver_sisb
            
            # Chamar com a assinatura apropriada
            if aceita_driver_sisb and driver_sisb is not None:
                # ✨ NOVO: Passar driver_sisb se função aceitar
                return func(driver, driver_sisb=driver_sisb)
            elif aceita_numero_processo and aceita_observacao and aceita_destinatarios:
                # Wrappers de comunicação (pec_ord, pec_sum, pec_decisao, etc.)
                if destinatarios_override is not None:
                    return func(driver, numero_processo, observacao, destinatarios_override=destinatarios_override)
                else:
                    return func(driver, numero_processo, observacao)
            elif aceita_numero_processo and aceita_observacao:
                # Funções que aceitam observacao
                return func(driver, numero_processo, observacao)
            elif aceita_debug:
                # Funções como mov_sob, def_sob, carta, def_chip
                return func(driver, debug=True)
            else:
                # Funções que aceitam apenas driver
                return func(driver)
        except Exception as e:
            print(f"[AÇÃO] ⚠️ Erro ao detectar assinatura de {func.__name__}: {e}")
            # Fallback: tentar com debug=True
            try:
                return func(driver, debug=True)
            except:
                # Último fallback: tentar com driver apenas
                return func(driver)

    # Novo modo: se acao é uma lista de funções, executar todas sequencialmente
    if isinstance(acao, list):
        print(f"[AÇÃO] ✅ Detectada lista de {len(acao)} funções para executar sequencialmente")
        for i, func in enumerate(acao, 1):
            print(f"[AÇÃO] Executando função {i}/{len(acao)}: {func.__name__}")
            try:
                resultado = chamar_funcao_com_assinatura_correta(func, driver, numero_processo, observacao, destinatarios_override)
                if not resultado:
                    print(f"[AÇÃO] ❌ Função {func.__name__} falhou - interrompendo sequência")
                    return False
                print(f"[AÇÃO] ✅ Função {func.__name__} executada com sucesso")
            except Exception as e:
                print(f"[AÇÃO] ❌ Erro na função {func.__name__}: {e}")
                traceback.print_exc()
                return False
        print(f"[AÇÃO] ✅ Todas as {len(acao)} funções executadas com sucesso")
        return True

    # Novo modo: se acao é uma função, chama diretamente (como P2B)
    if callable(acao):
        try:
            print(f"[AÇÃO] ✅ Chamando função diretamente: {acao.__name__}")
            resultado = chamar_funcao_com_assinatura_correta(acao, driver, numero_processo, observacao, destinatarios_override)
            if resultado:
                print(f"[AÇÃO] ✅ Função {acao.__name__} executada com sucesso")
            else:
                print(f"[AÇÃO] ❌ Função {acao.__name__} retornou False")
            return resultado
        except Exception as e:
            print(f"[AÇÃO] ❌ Erro ao executar função {acao.__name__}: {e}")
            traceback.print_exc()
            return False

    # Modo legado removido - PEC agora funciona como P2B: regex direto para função
    print(f"[AÇÃO] ❌ Ação '{acao}' não é uma função válida (modo legado removido)")
    return False


def processar_processo_pec_individual(driver):
    """
    Callback específico para processar um processo individual no PEC
    Usado pelo sistema centralizado de retry do PJE.PY
    
    Esta função foca APENAS na lógica específica do PEC,
    sem se preocupar com retry, progresso ou navegação para /detalhe
    """
    try:
        # 1. Extrair dados do processo atual
        numero_processo = extrair_numero_processo_pec(driver)
        if not numero_processo:
            print("[PEC_INDIVIDUAL] ❌ Não foi possível extrair número do processo")
            return False
        
        # 2. Indexar processo atual para obter observação
        processo_atual = indexar_processo_atual_gigs(driver)
        if not processo_atual:
            print("[PEC_INDIVIDUAL] ❌ Falha ao extrair dados do processo atual")
            return False
        
        _, observacao = processo_atual
        print(f"[PEC_INDIVIDUAL] Processo: {numero_processo} | Observação: {observacao}")
        
        # 3. Determinar ações baseadas na observação (AQUI, UMA VEZ)
        acoes = determinar_acoes_por_observacao(observacao)
        acao = acoes[0] if acoes else None  # Para compatibilidade com código antigo
        print(f"[PEC_INDIVIDUAL] Ações determinadas: {[a.__name__ if callable(a) else str(a) for a in acoes]}")
        
        # 4. Pular processos sem ação definida
        if acao is None:
            print(f"[PEC_INDIVIDUAL] ⏭️ Pulando processo (ação não definida)")
            return True  # Considera sucesso para não retry
        
        # 6. Preparar override de destinatário (se a observação contiver um nome após o comando)
        destinatarios_override = None
        try:
            import re
            # Padrão: 'pec dec Nome Sobrenome', 'pec edital Nome', 'pec idpj Nome'
            m = re.match(r'^(?:pec\s*(?:dec|edital|idpj)\b)\s+(.+)$', observacao.strip(), re.I)
            if m:
                nome_cand = m.group(1).strip()
                # Tomar até a primeira vírgula ou hífen ou parenteses
                nome_cand = re.split(r'[,-\(\\)]', nome_cand)[0].strip()
                # Remover títulos comuns
                nome_cand = re.sub(r'^(sr\.?|sra\.?|dr\.?|dra\.?|srta\.?|srta)\s+', '', nome_cand, flags=re.I).strip()
                # Validar tamanho mínimo
                if len(nome_cand) >= 3 and re.search('[A-Za-zÀ-ÖØ-öø-ÿ]', nome_cand):
                    destinatarios_override = {'nome': nome_cand}
                    print(f"[PEC_INDIVIDUAL][DEST_OVERRIDE] Nome extraído para override: '{nome_cand}'")
        except Exception as e_parse:
            print(f"[PEC_INDIVIDUAL][DEST_OVERRIDE][WARN] Falha ao tentar extrair nome da observação: {e_parse}")

        # 7. Executar ação específica (sem os parâmetros antigos que não usamos mais)
        # ✨ NOVO: Tentar obter driver_sisb do contexto global (se existir)
        driver_sisb = getattr(driver, '_driver_sisb_compartilhado', None)
        
        sucesso_acao = executar_acao_pec(driver, acao, numero_processo=numero_processo, observacao=observacao, debug=True, driver_sisb=driver_sisb)
        
        if sucesso_acao:
            print(f"[PEC_INDIVIDUAL] ✅ Ação executada com sucesso")
            return True
        else:
            print(f"[PEC_INDIVIDUAL] ❌ Falha na execução da ação '{acao}'")
            return False
        
    except Exception as e:
        print(f"[PEC_INDIVIDUAL] ❌ Erro no processamento: {e}")
        return False


def executar_fluxo_robusto(driver):
    """
    Versão robusta do fluxo PEC que usa o sistema centralizado do PJE.PY
    Esta função substitui executar_fluxo_novo() para integração com retry centralizado
    """
    driver_sisb = None  # ✨ NOVO: Driver SISBAJUD compartilhado
    
    try:
        print("[FLUXO_ROBUSTO_PEC] Iniciando fluxo robusto com sistema centralizado...")
        
        # Validar parâmetro driver
        if driver is None:
            print("[FLUXO_ROBUSTO_PEC] ❌ Erro: driver não fornecido (None)")
            return {"sucesso": False, "status": "ERRO_DRIVER", "erro": "Driver não fornecido"}
        
        # ✨ NOVO: Criar driver SISBAJUD compartilhado (sem extrair dados ainda)
        try:
            print("[FLUXO_ROBUSTO_PEC] 🔧 Criando driver SISBAJUD compartilhado...")
            from SISB.core import iniciar_sisbajud
            driver_sisb = iniciar_sisbajud(driver_pje=driver, extrair_dados=False)
            
            if driver_sisb:
                # Anexar driver SISBAJUD ao driver PJE para acesso global
                driver._driver_sisb_compartilhado = driver_sisb
                print("[FLUXO_ROBUSTO_PEC] ✅ Driver SISBAJUD compartilhado criado e anexado ao driver PJE")
            else:
                print("[FLUXO_ROBUSTO_PEC] ⚠️ Falha ao criar driver SISBAJUD - continuando sem ele")
        except Exception as e:
            print(f"[FLUXO_ROBUSTO_PEC] ⚠️ Erro ao criar driver SISBAJUD: {e}")
            driver_sisb = None
        
        # Importar função centralizada do PJE
        from pje import executar_processo_com_retry
        
        # Carregar progresso atual
        progresso = carregar_progresso_pec()
        print(f"[FLUXO_ROBUSTO_PEC] Progresso atual: {len(progresso)} processos executados")
        
        # Verificar se já navegou para atividades
        url_atual = driver.current_url
        if "atividade" not in url_atual.lower():
            print("[FLUXO_ROBUSTO_PEC] Navegando para atividades...")
            if not navegar_para_atividades(driver):
                print("[FLUXO_ROBUSTO_PEC] ❌ Falha ao navegar para atividades")
                return {"sucesso": False, "status": "ERRO_NAVEGACAO", "erro": "Falha na navegação para atividades"}
        
        # Aplicar filtros básicos
        try:
            from Fix.core import aplicar_filtro_100
            print("[FLUXO_ROBUSTO_PEC] Aplicando filtro de 100 itens...")
            if aplicar_filtro_100(driver):
                print("[FLUXO_ROBUSTO_PEC] ✅ Filtro aplicado")
                time.sleep(2)
        except Exception as e:
            print(f"[FLUXO_ROBUSTO_PEC] ⚠️ Erro ao aplicar filtro: {e}")
        

        # Callback que usa sistema centralizado
        def callback_pec_centralizado(driver):
            """Callback que integra com sistema centralizado de retry"""
            numero_processo = extrair_numero_processo_pec(driver)
            if not numero_processo:
                print("[CALLBACK_PEC] ❌ Não foi possível extrair número do processo")
                return False
            
            # Usar sistema centralizado com retry automático
            resultado = executar_processo_com_retry(
                processar_processo_pec_individual,  # Função específica do PEC
                driver, 
                numero_processo, 
                "PEC"
            )
            
            # Log do resultado
            if resultado["sucesso"]:
                print(f"[CALLBACK_PEC] ✅ Processo {numero_processo} processado com sucesso")
            else:
                print(f"[CALLBACK_PEC] ❌ Processo {numero_processo} falhou: {resultado.get('status', 'Erro desconhecido')}")
            
            return resultado["sucesso"]
        
        # Executar processamento da lista com callback robusto
        print("[FLUXO_ROBUSTO_PEC] Iniciando processamento da lista...")
        # Usar apenas funções da pasta PEC - sem legado
        if not _organizar_e_executar_buckets(driver, progresso):
            print("[FLUXO_ROBUSTO_PEC] ❌ Falha ao organizar e executar buckets")
            return {"sucesso": False, "status": "ERRO_PROCESSAMENTO", "erro": "Falha na organização e execução de buckets"}
        
        # Calcular estatísticas finais
        progresso_final = carregar_progresso_pec()
        processos_executados = len(progresso_final)

        print(f"[FLUXO_ROBUSTO_PEC] ✅ Processamento concluído com sucesso")
        print(f"[FLUXO_ROBUSTO_PEC] Total de processos executados: {processos_executados}")
        return {"sucesso": True, "status": "SUCESSO", "processos_executados": processos_executados}
        
    except Exception as e:
        # Se o chamador sinalizou RESTART_PEC, tratamos como pedido explicito de reiniciar o fluxo
        msg = str(e)
        if 'RESTART_PEC' in msg:
            print(f"[FLUXO_ROBUSTO_PEC] 🔄 Reinício solicitado pelo processamento do bucket: {msg}")
            print("[FLUXO_ROBUSTO_PEC] 🔄 Tentando reiniciar driver e retomar fluxo a partir do progresso")
            try:
                novo_driver = reiniciar_driver_e_logar_pje(driver, log=True)
            except Exception as restart_exc:
                print(f"[FLUXO_ROBUSTO_PEC] ❌ Erro ao tentar reiniciar driver: {restart_exc}")
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(e)}

            if not novo_driver:
                print("[FLUXO_ROBUSTO_PEC] ❌ Falha ao reiniciar driver — não foi possível retomar")
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(e)}

            # Re-executa o fluxo usando o novo driver. A função recarregará o progresso e pulará processos já executados.
            print("[FLUXO_ROBUSTO_PEC] ✅ Novo driver criado — reiniciando fluxo (retomará do arquivo de progresso)")
            try:
                resultado_reexec = executar_fluxo_robusto(novo_driver)
                return resultado_reexec
            finally:
                pass

        tipo_erro = "OPERACIONAL"
        try:
            url_atual = driver.current_url
            if "acesso-negado" in url_atual.lower() or "login.jsp" in url_atual.lower():
                tipo_erro = "ACESSO_NEGADO"
        except:
            tipo_erro = "CRITICO"

        print(f"[FLUXO_ROBUSTO_PEC] ❌ Erro no fluxo: {e}")

        # Se for acesso negado, tentar reiniciar driver e retomar o fluxo
        if tipo_erro == "ACESSO_NEGADO":
            print("[FLUXO_ROBUSTO_PEC] 🔄 Detectado ACESSO_NEGADO — tentando reiniciar driver e retomar fluxo a partir do progresso")
            try:
                novo_driver = reiniciar_driver_e_logar_pje(driver, log=True)
            except Exception as restart_exc:
                print(f"[FLUXO_ROBUSTO_PEC] ❌ Erro ao tentar reiniciar driver: {restart_exc}")
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(e)}

            if not novo_driver:
                print("[FLUXO_ROBUSTO_PEC] ❌ Falha ao reiniciar driver — não foi possível retomar")
                return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": str(e)}

            print("[FLUXO_ROBUSTO_PEC] ✅ Novo driver criado — reiniciando fluxo (retomará do arquivo de progresso)")
            try:
                resultado_reexec = executar_fluxo_robusto(novo_driver)
                return resultado_reexec
            finally:
                pass

        return {"sucesso": False, "status": tipo_erro, "erro": str(e)}
    
    finally:
        # ✨ NOVO: Fechar driver SISBAJUD compartilhado
        if driver_sisb:
            try:
                print("[FLUXO_ROBUSTO_PEC] 🧹 Fechando driver SISBAJUD compartilhado...")
                driver_sisb.quit()
                print("[FLUXO_ROBUSTO_PEC] ✅ Driver SISBAJUD fechado com sucesso")
            except Exception as e:
                print(f"[FLUXO_ROBUSTO_PEC] ⚠️ Erro ao fechar driver SISBAJUD: {e}")


def executar_fluxo_novo(driver: Optional[Any] = None) -> bool:
    """
    Executa o novo fluxo conforme especificações:
    1- usar driver fornecido ou criar novo e executar login conforme definido em driver_config.py
    2- iniciar fluxo logo após login navegando até atividades
    3- não clicar no ícone "Atividades sem prazo"
    4- não filtrar com xs
    5- indexar lista com a função definida de fix.py
    6- ao indexar numero do processo - atividade (observação)
    """
    import time

    print("[FLUXO_NOVO] Iniciando novo fluxo com controle de progresso...")
    progresso = carregar_progresso_pec()
    driver_criado_aqui = False

    try:
        # Configurar driver e fazer login
        driver, driver_criado_aqui = _configurar_driver(driver)
        if not driver:
            print('[FLUXO_NOVO] ❌ Falha na configuração do driver')
            return False

        # Navegar para atividades
        if not _navegar_atividades(driver):
            print("[FLUXO_NOVO] ❌ Falha ao navegar para atividades")
            if driver_criado_aqui:
                driver.quit()
            return False

        # Aplicar filtros necessários
        if not _aplicar_filtros(driver):
            print("[FLUXO_NOVO] ❌ Falha ao aplicar filtros")
            if driver_criado_aqui:
                driver.quit()
            return False

        # Organizar processos em buckets e executar individualmente
        if not _organizar_e_executar_buckets(driver, progresso):
            print("[FLUXO_NOVO] ❌ Falha ao organizar e executar buckets")
            if driver_criado_aqui:
                driver.quit()
            return False

        print("[FLUXO_NOVO] ✅ Fluxo executado com sucesso")
        return True

    except Exception as e:
        print(f"[FLUXO_NOVO] ❌ Erro durante o processamento: {e}")
        if driver_criado_aqui and driver:
            driver.quit()
        return False
    finally:
        # Fechar driver SISBAJUD global se existir
        try:
            from PEC.regras import fechar_driver_sisbajud_global
            fechar_driver_sisbajud_global()
        except Exception as e:
            print(f'[FLUXO_NOVO] ⚠️ Erro ao fechar driver SISBAJUD global: {e}')
        
        # Só fecha o driver se foi criado aqui
        if driver_criado_aqui and driver:
            input("[FLUXO_NOVO] Pressione Enter para fechar o driver...")
            try:
                driver.quit()
            except:
                pass
        else:
            print("[FLUXO_NOVO] ✅ Driver externo mantido ativo")



def _configurar_driver(driver: Optional[Any]) -> Tuple[Any, bool]:
    """
    Helper: Configura driver e realiza login.

    Args:
        driver: Driver fornecido ou None

    Returns:
        tuple: (driver_configurado, driver_criado_aqui)
    """
    driver_criado_aqui = False

    try:
        # Se não recebeu driver, cria um novo
        if driver is None:
            from driver_config import criar_driver, login_func, login_manual
            driver = criar_driver(headless=False)
            driver_criado_aqui = True
            if not driver:
                print('[FLUXO_NOVO] ❌ Falha ao criar driver')
                return None, False
            print("[FLUXO_NOVO] ✅ Driver criado com sucesso")

            # Realizar login
            if not login_func(driver):
                print('[FLUXO_NOVO] ❌ Falha no login automático. Tentando fallback para login manual...')
                try:
                    if login_manual(driver):
                        print('[FLUXO_NOVO] ✅ Login manual realizado com sucesso. Continuando execução.')
                    else:
                        print('[FLUXO_NOVO] ❌ Login manual também falhou')
                        driver.quit()
                        return None, False
                except Exception as e:
                    print(f'[FLUXO_NOVO] ❌ Erro no login manual: {e}')
                    driver.quit()
                    return None, False
        else:
            print("[FLUXO_NOVO] ✅ Usando driver fornecido externamente")
            print("[FLUXO_NOVO] ✅ Login realizado com sucesso")

        return driver, driver_criado_aqui

    except Exception as e:
        print(f"[FLUXO_NOVO] ❌ Erro ao configurar driver: {e}")
        if driver_criado_aqui and driver:
            driver.quit()
        return None, False



def _navegar_atividades(driver: Any) -> bool:
    """
    Helper: Navega para a tela de atividades.

    Args:
        driver: WebDriver configurado

    Returns:
        bool: True se navegação bem-sucedida
    """
    try:
        if not navegar_para_atividades(driver):
            return False
        time.sleep(5)
        return True
    except Exception as e:
        print(f"[FLUXO_NOVO] ❌ Erro ao navegar para atividades: {e}")
        return False



def _aplicar_filtros(driver: Any) -> bool:
    """
    Helper: Aplica filtros necessários (100 itens por página e reorganização por observação).

    Args:
        driver: WebDriver na tela de atividades

    Returns:
        bool: True se filtros aplicados com sucesso
    """
    try:
        from Fix.core import aplicar_filtro_100
        print("[FLUXO_NOVO] Aplicando filtro de 100 itens por página...")
        if aplicar_filtro_100(driver):
            print("[FLUXO_NOVO] ✅ Filtro de 100 itens aplicado")
            time.sleep(2)
        else:
            print("[FLUXO_NOVO] ⚠️ Falha ao aplicar filtro de 100 itens, continuando...")

        print("[FLUXO_NOVO] Clicando na coluna 'Observação' para reorganizar a lista...")
        try:
            # Tentar múltiplos seletores para maior robustez (acentuação pode variar)
            seletores = [
                ("//div[@role='column' and contains(normalize-space(.),'Observação')]", By.XPATH),
                ("//div[@role='column' and contains(normalize-space(.),'Observacao')]", By.XPATH),
                ("//div[contains(@class,'th-elemento-class') and contains(normalize-space(.),'Observa')]", By.XPATH),
                ("div.th-elemento-class", By.CSS_SELECTOR),
            ]
            coluna_observacao = None
            for sel, sel_by in seletores:
                try:
                    coluna_observacao = aguardar_e_clicar(driver, sel, timeout=6, by=sel_by, usar_js=True, retornar_elemento=True)
                    if coluna_observacao:
                        break
                except Exception:
                    coluna_observacao = None

            if coluna_observacao:
                print("[FLUXO_NOVO] ✅ Coluna 'Observação' clicada - lista reorganizada")
            else:
                print("[FLUXO_NOVO] ⚠️ Erro ao clicar na coluna 'Observação' (todos seletores falharam)")
            time.sleep(3)
        except Exception as e:
            print(f"[FLUXO_NOVO] ⚠️ Erro ao clicar na coluna 'Observação': {e}")
            print("[FLUXO_NOVO] Continuando sem reorganizar...")

        return True

    except Exception as e:
        print(f"[FLUXO_NOVO] ❌ Erro ao aplicar filtros: {e}")
        return False



def _organizar_e_executar_buckets(driver: Any, progresso: Dict[str, Any]) -> bool:
    """
    Helper: Organiza processos em buckets e executa TODOS os processos de cada bucket individualmente.

    Args:
        driver: WebDriver configurado
        progresso: Dicionário de progresso

    Returns:
        bool: True se processamento bem-sucedido
    """
    try:
        print("[BUCKETS_PEC] 🪣 Organizando processos em buckets...")

        # Usar a função de buckets para organizar processos (dry_run=True para apenas organizar)
        filtros_observacao = ['xs', 'silas', 'sobrestamento', 'sob ']
        buckets = indexar_e_criar_buckets_unico(driver, filtros_observacao, dry_run=True)

        if not buckets:
            print("[BUCKETS_PEC] ❌ Falha ao organizar buckets")
            return False

        print("[BUCKETS_PEC] ✅ Buckets organizados com sucesso")

        # MOSTRAR RESUMO DOS BUCKETS FORMADOS
        print("\n[BUCKETS_PEC] 📊 RESUMO DOS BUCKETS FORMADOS:")
        print("=" * 60)
        buckets_com_processos = {}
        for bucket_name in ['sob', 'carta', 'citacoes', 'intimacoes', 'outros', 'sobrestamento', 'sisbajud']:
            bucket = buckets.get(bucket_name, [])
            if bucket:  # Só mostrar buckets que têm processos
                buckets_com_processos[bucket_name] = bucket
                count = len(bucket)
                print(f"🪣 {bucket_name.upper():<12}: {count:>3} processos")

                # Mostrar exemplos dos processos
                for i, proc in enumerate(bucket[:3]):  # Máximo 3 exemplos
                    obs_curta = proc['observacao'][:50] + ('...' if len(proc['observacao']) > 50 else '')
                    print(f"   {i+1}. {proc['numero']}: '{obs_curta}'")

                if count > 3:
                    print(f"   ... e mais {count-3} processos")
                print()

        if not buckets_com_processos:
            print("[BUCKETS_PEC] ℹ️ Nenhum bucket foi formado - nenhum processo atende aos critérios")
            return True

        # EXECUTAR TODOS OS PROCESSOS DE CADA BUCKET INDIVIDUALMENTE
        print("[BUCKETS_PEC] 🚀 Executando TODOS os processos de cada bucket individualmente...")
        print("=" * 60)

        total_results = {'sucesso': 0, 'erro': 0}

        # Processar buckets não-SISBAJUD primeiro
        for bucket_name in ['sob', 'carta', 'citacoes', 'intimacoes', 'outros', 'sobrestamento']:
            bucket = buckets_com_processos.get(bucket_name, [])
            if not bucket:
                continue

            print(f"[BUCKETS_PEC] 📂 Processando bucket '{bucket_name}' com {len(bucket)} processos...")
            res = _processar_bucket_demais(driver, bucket, progresso, descricao=f"{bucket_name.upper()}")
            total_results['sucesso'] += res.get('sucesso', 0)
            total_results['erro'] += res.get('erro', 0)

        # Processar SISBAJUD por último
        bucket_sisbajud = buckets_com_processos.get('sisbajud', [])
        if bucket_sisbajud:
            print(f"[BUCKETS_PEC] 📂 Processando bucket 'sisbajud' com {len(bucket_sisbajud)} processos...")
            res = _processar_bucket_sisbajud(driver, bucket_sisbajud, progresso)
            total_results['sucesso'] += res.get('sucesso', 0)
            total_results['erro'] += res.get('erro', 0)

        # Relatório final
        processos_sucesso = total_results['sucesso']
        processos_erro = total_results['erro']
        buckets_processados = len(buckets_com_processos)
        total_processos = sum(len(bucket) for bucket in buckets_com_processos.values())

        print(f"\n[BUCKETS_PEC] ========== RELATÓRIO FINAL ==========")
        print(f"[BUCKETS_PEC] Buckets identificados: {buckets_processados}")
        print(f"[BUCKETS_PEC] Processos processados: {total_processos}")
        print(f"[BUCKETS_PEC] Sucessos: {processos_sucesso}")
        print(f"[BUCKETS_PEC] Erros: {processos_erro}")
        print(f"[BUCKETS_PEC] Taxa de sucesso: {(processos_sucesso/total_processos*100):.1f}%" if total_processos else "N/A")
        print(f"[BUCKETS_PEC] =====================================")

        return True

    except Exception as e:
        # RESTART_PEC deve ser propagado para o nível superior
        if 'RESTART_PEC' in str(e):
            print(f"[BUCKETS_PEC] 🔄 Propagando RESTART_PEC para reinício do fluxo")
            raise
        print(f"[BUCKETS_PEC] ❌ Erro ao organizar e executar buckets: {e}")
        return False



def criar_lista_sisbajud(driver):
    """
    Varre a lista de atividades usando a mesma lógica de indexação posterior
    e identifica todos os processos SISBAJUD para processamento agrupado
    """
    try:
        print("[SISBAJUD_LISTA] 🔍 Lendo lista completa de atividades para criar lista SISBAJUD...")
        
        from selenium.webdriver.common.by import By
        import re
        
        # Usar a mesma lógica de indexação da lista posterior
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        if not linhas:
            print("[SISBAJUD_LISTA] ❌ Nenhuma linha encontrada com seletor tr.tr-class")
            return []
        
        print(f"[SISBAJUD_LISTA] 📋 Encontradas {len(linhas)} linhas na tabela")
        
        lista_sisbajud = []
        padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
        
        for idx, linha in enumerate(linhas):
            try:
                colunas = linha.find_elements(By.TAG_NAME, 'td')
                if len(colunas) < 6:
                    continue
                
                # Extrair número do processo da 2ª coluna
                celula_processo = colunas[1]
                numero_processo = None
                
                # Buscar elemento <b> que contém o número
                try:
                    elemento_b = celula_processo.find_element(By.TAG_NAME, 'b')
                    if elemento_b:
                        texto_b = elemento_b.text.strip()
                        match = padrao_proc.search(texto_b)
                        if match:
                            numero_processo = match.group(0)
                except:
                    pass
                
                if not numero_processo:
                    continue
                
                # Extrair observação da 6ª coluna
                celula_observacao = colunas[5]
                observacao = ""
                
                # Buscar span.texto-descricao
                try:
                    span_observacao = celula_observacao.find_element(By.CSS_SELECTOR, 'span.texto-descricao')
                    observacao = span_observacao.text.lower().strip()
                    # Debug: mostrar conteúdo bruto do span e da célula
                    try:
                        raw_span = span_observacao.get_attribute('innerText') or span_observacao.text
                    except Exception:
                        raw_span = span_observacao.text
                    try:
                        raw_cell = celula_observacao.get_attribute('innerText') or celula_observacao.text
                    except Exception:
                        raw_cell = celula_observacao.text
                    print(f"[INDEXAR][DEBUG] Linha {idx+1} - span_observacao raw: {repr(raw_span)} | celula raw: {repr(raw_cell)} -> processed: {repr(observacao)}")
                except:
                    # Fallback: texto direto da célula
                    observacao = celula_observacao.text.lower().strip()
                    try:
                        raw_cell = celula_observacao.get_attribute('innerText') or celula_observacao.text
                    except Exception:
                        raw_cell = celula_observacao.text
                    print(f"[INDEXAR][DEBUG] Linha {idx+1} - celula raw (fallback): {repr(raw_cell)} -> processed: {repr(observacao)}")
                
                if not observacao:
                    continue
                
                # Determinar ações (UMA VEZ AQUI)
                acoes = determinar_acoes_por_observacao(observacao)
                
                # Adicionar à lista se acoes for definida
                if acoes:
                    # Extrair nomes das funções para logging
                    nomes_acoes = [a.__name__ if callable(a) else str(a) for a in acoes]
                    
                    print(f"[SISBAJUD_LISTA] 📋 Processo: {numero_processo} | Observação: {observacao}")
                    lista_sisbajud.append({
                        'numero_processo': numero_processo,
                        'observacao': observacao,
                        'acoes': acoes,
                        'linha': linha,
                        'linha_index': idx
                    })
                    print(f"[SISBAJUD_LISTA] ✅ Adicionado: {numero_processo} ({', '.join(nomes_acoes)})")
                    
            except Exception as e:
                print(f"[SISBAJUD_LISTA] ⚠️ Erro ao processar linha {idx + 1}: {e}")
                continue
        
        print(f"[SISBAJUD_LISTA] ✅ Varredura concluída. Encontrados {len(lista_sisbajud)} processos SISBAJUD")
        return lista_sisbajud
        
    except Exception as e:
        print(f"[SISBAJUD_LISTA] ❌ Erro ao criar lista SISBAJUD: {e}")
        return []


def executar_lista_sisbajud_por_abas(driver_pje, lista_sisbajud):
    """
    Executa lista de processos SISBAJUD usando abas e driver compartilhado
    """
    try:
        if not lista_sisbajud:
            print("[SISBAJUD_EXEC] ℹ️ Nenhum processo SISBAJUD para executar")
            return []
        
        print(f"[SISBAJUD_EXEC] 🚀 Iniciando execução de {len(lista_sisbajud)} processos SISBAJUD por abas...")
        
        resultados = []
        driver_sisbajud = None
        
        # Armazenar aba original da lista
        aba_lista_original = driver_pje.current_window_handle
        
        for idx, item in enumerate(lista_sisbajud, 1):
            numero_processo = item['numero_processo']
            observacao = item['observacao']
            acao = item['acao']
            linha = item['linha']
            linha_index = item['linha_index']
            
            print(f"\n[SISBAJUD_EXEC] === EXECUTANDO {idx}/{len(lista_sisbajud)}: {numero_processo} ===")
            print(f"[SISBAJUD_EXEC] Observação: {observacao}")
            print(f"[SISBAJUD_EXEC] Linha índice: {linha_index}")
            
            sucesso = False
            aba_aberta_pela_funcao = False
            nova_aba = None
            
            try:
                # Verificar se linha ainda é válida
                linha_atual = linha
                try:
                    linha_atual.is_displayed()
                except:
                    # Linha ficou stale, verificar se é problema de acesso negado
                    print(f"[SISBAJUD_EXEC] ⚠️ Linha ficou stale, verificando causa...")
                    
                    # Verificar URL atual para detectar acesso negado
                    url_atual = driver_pje.current_url
                    if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                        print(f"[SISBAJUD_EXEC] ❌ ACESSO NEGADO detectado na URL: {url_atual}")
                        print(f"[SISBAJUD_EXEC] ❌ Sessão PJE perdida - necessário relogar")
                        # Retornar erro crítico que requer nova sessão
                        return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": f"Acesso negado detectado na URL PJE: {url_atual}"}
                    
                    # Verificar se página tem indicadores de erro de sessão
                    try:
                        body_text = driver_pje.find_element(By.TAG_NAME, 'body').text.lower()
                        if any(termo in body_text for termo in ['acesso negado', 'sessão expirada', 'não autorizado', 'access denied']):
                            print(f"[SISBAJUD_EXEC] ❌ ACESSO NEGADO detectado no conteúdo da página PJE")
                            return {"sucesso": False, "status": "ACESSO_NEGADO", "erro": "Acesso negado detectado no conteúdo da página PJE"}
                    except:
                        pass
                    
                    # Se não é acesso negado, tentar reindexar
                    print(f"[SISBAJUD_EXEC] Tentando reindexar linha para {numero_processo}...")
                    linha_atual = reindexar_linha(driver_pje, numero_processo)
                    if not linha_atual:
                        print(f"[SISBAJUD_EXEC] ❌ Não foi possível reindexar linha para {numero_processo}")
                        print(f"[SISBAJUD_EXEC] ❌ Possível problema de sessão ou navegação PJE")
                        continue
                
                # NAVEGAR PARA O PROCESSO ESPECÍFICO (usando mesma lógica da indexação normal)
                from Fix.extracao import abrir_detalhes_processo, trocar_para_nova_aba
                
                # 1. Abrir detalhes do processo
                if not abrir_detalhes_processo(driver_pje, linha_atual):
                    print(f"[SISBAJUD_EXEC] ❌ Botão de detalhes não encontrado para {numero_processo}")
                    continue
                
                # 2. Trocar para nova aba
                import time
                time.sleep(1)
                nova_aba = trocar_para_nova_aba(driver_pje, aba_lista_original)
                if not nova_aba:
                    print(f"[SISBAJUD_EXEC] ❌ Nova aba do processo {numero_processo} não foi aberta")
                    continue
                
                # 3. Aguardar carregamento
                time.sleep(2)
                
                aba_aberta_pela_funcao = True
                print(f"[SISBAJUD_EXEC] ✅ Aba do processo {numero_processo} aberta")
                
                # 4. Extrair dados do processo
                print(f"[SISBAJUD_EXEC] 📊 Extraindo dados do processo {numero_processo}...")
                from Fix.extracao import extrair_dados_processo
                dados_processo = extrair_dados_processo(driver_pje)
                
                if not dados_processo:
                    print(f"[SISBAJUD_EXEC] ⚠️ Não foi possível extrair dados do processo {numero_processo}")
                    continue
                
                # 5. Executar ação SISBAJUD apropriada
                print(f"[SISBAJUD_EXEC] 🚀 Executando ação SISBAJUD para {numero_processo}")
                
                # Inicializar driver SISBAJUD apenas uma vez
                if driver_sisbajud is None:
                    print("[SISBAJUD_EXEC] 🔧 Inicializando driver SISBAJUD (primeira vez)...")
                    from SISB.core import iniciar_sisbajud
                    driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
                    
                    if not driver_sisbajud:
                        print("[SISBAJUD_EXEC] ❌ Falha ao inicializar driver SISBAJUD")
                        break
                
                # Executar a ação apropriada baseada no tipo
                if acao == "processar_ordem_sisbajud":
                    # Executar processar_ordem_sisbajud
                    from SISB.core import processar_ordem_sisbajud
                    
                    resultado = processar_ordem_sisbajud(
                        driver=driver_sisbajud,
                        dados_processo=dados_processo,
                        driver_pje=driver_pje,
                        log=True
                    )
                    
                    if resultado and resultado.get('status') == 'concluido':
                        sucesso = True
                        print(f"[SISBAJUD_EXEC] ✅ Processamento de ordem executado para {numero_processo}")
                        print(f"[SISBAJUD_EXEC] ℹ️ Juntadas PJE já foram executadas dentro de processar_ordem_sisbajud")
                    else:
                        print(f"[SISBAJUD_EXEC] ❌ Falha no processamento de ordem para {numero_processo}")
                        
                elif acao == "minuta_bloqueio_sisbajud":
                    # Executar minuta_bloqueio_sisbajud
                    from SISB.core import minuta_bloqueio
                    
                    # Detectar prazo na observação (padrão 30 dias, 60 se especificado)
                    prazo_dias = 30  # Padrão
                    observacao_lower = observacao.lower() if observacao else ""
                    
                    if "60" in observacao_lower:
                        prazo_dias = 60
                        print(f"[SISBAJUD_EXEC] 📅 Prazo de 60 dias detectado na observação: '{observacao}'")
                    else:
                        print(f"[SISBAJUD_EXEC] 📅 Usando prazo padrão de 30 dias")
                    
                    resultado = minuta_bloqueio(
                        driver=driver_sisbajud,
                        dados_processo=dados_processo, 
                        driver_pje=driver_pje,
                        log=True
                    )
                    
                    if resultado and resultado.get('status') == 'sucesso':
                        sucesso = True
                        print(f"[SISBAJUD_EXEC] ✅ Minuta de bloqueio executada para {numero_processo}")
                        
                        # Executar juntada do relatório SISBAJUD no PJe
                        print(f"[SISBAJUD_EXEC] 🔗 Executando juntada do relatório SISBAJUD no PJe...")
                        from PEC.anexos import consulta_wrapper
                        
                        resultado_wrapper = consulta_wrapper(
                            driver=driver_pje,
                            numero_processo=numero_processo,
                            debug=True
                        )
                        
                        if resultado_wrapper:
                            print(f"[SISBAJUD_EXEC] ✅ Relatório SISBAJUD inserido no PJe com sucesso!")
                        else:
                            print(f"[SISBAJUD_EXEC] ⚠️ Falha na inserção do relatório no PJe, mas minuta foi executada")
                    else:
                        print(f"[SISBAJUD_EXEC] ❌ Falha na execução de minuta de bloqueio para {numero_processo}")
                        
                else:
                    print(f"[SISBAJUD_EXEC] ❌ Ação desconhecida: {acao}")
                    sucesso = False
            
            except Exception as e:
                print(f"[SISBAJUD_EXEC] ❌ Erro ao processar {numero_processo}: {e}")
                import traceback
                traceback.print_exc()
            
            # 5. Voltar para lista
            try:
                driver_pje.switch_to.window(aba_lista_original)
            except:
                pass
            
            resultados.append({
                'numero_processo': numero_processo,
                'sucesso': sucesso
            })
        
        # 6. Fechar driver SISBAJUD ao final
        if driver_sisbajud:
            print("[SISBAJUD_EXEC] 🔒 Fechando driver SISBAJUD...")
            try:
                driver_sisbajud.quit()
            except:
                pass
        
        print(f"[SISBAJUD_EXEC] ✅ Execução SISBAJUD concluída: {sum(1 for r in resultados if r['sucesso'])}/{len(resultados)} sucessos")
        return resultados
        
    except Exception as e:
        print(f"[SISBAJUD_EXEC] ❌ Erro geral na execução SISBAJUD: {e}")
        import traceback
        traceback.print_exc()
        return []


def criar_lista_resto(driver, filtros_observacao):
    """
    Varre a lista de atividades e identifica todos os processos do resto (não-SISBAJUD)
    usando exatamente a mesma lógica da criar_lista_sisbajud
    """
    try:
        print("[RESTO_LISTA] 🔍 Lendo lista completa de atividades para criar lista do resto...")
        
        from selenium.webdriver.common.by import By
        import re
        
        # Usar a mesma lógica de indexação da lista SISBAJUD
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        if not linhas:
            print("[RESTO_LISTA] ❌ Nenhuma linha encontrada com seletor tr.tr-class")
            return []
        
        print(f"[RESTO_LISTA] 📋 Encontradas {len(linhas)} linhas na tabela")
        
        lista_resto = []
        padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
        
        for idx, linha in enumerate(linhas):
            try:
                colunas = linha.find_elements(By.TAG_NAME, 'td')
                if len(colunas) < 6:
                    continue
                
                # Extrair número do processo da 2ª coluna
                celula_processo = colunas[1]
                numero_processo = None
                
                # Buscar elemento <b> que contém o número
                try:
                    elemento_b = celula_processo.find_element(By.TAG_NAME, 'b')
                    if elemento_b:
                        texto_b = elemento_b.text.strip()
                        match = padrao_proc.search(texto_b)
                        if match:
                            numero_processo = match.group(0)
                except:
                    pass
                
                if not numero_processo:
                    continue
                
                # Extrair observação da 6ª coluna
                celula_observacao = colunas[5]
                observacao = ""
                
                # Buscar span.texto-descricao
                try:
                    span_observacao = celula_observacao.find_element(By.CSS_SELECTOR, 'span.texto-descricao')
                    observacao = span_observacao.text.lower().strip()
                except:
                    # Fallback: texto direto da célula
                    observacao = celula_observacao.text.lower().strip()
                
                if not observacao:
                    continue
                
                # Verificar se observação passa no filtro
                passa_filtro = False
                for filtro in filtros_observacao:
                    if filtro.lower() in observacao:
                        passa_filtro = True
                        break
                
                if not passa_filtro:
                    continue
                
                # Determinar ação usando a mesma lógica
                acao = determinar_acao_por_observacao(observacao)
                
                # Adicionar à lista se acao for definida
                if acao is not None:
                    nome_acao = acao.__name__ if callable(acao) else str(acao)
                    if isinstance(acao, list) and len(acao) > 0:
                        nome_acao = f"[{', '.join(f.__name__ for f in acao if callable(f))}]"
                    
                    print(f"[RESTO_LISTA] 📋 Processo: {numero_processo} | Observação: {observacao}")
                    lista_resto.append({
                        'numero_processo': numero_processo,
                        'observacao': observacao,
                        'acao': acao,
                        'linha': linha,
                        'linha_index': idx
                    })
                    print(f"[RESTO_LISTA] ✅ Adicionado: {numero_processo} ({nome_acao})")
                    
            except Exception as e:
                print(f"[RESTO_LISTA] ⚠️ Erro ao processar linha {idx + 1}: {e}")
                continue
        
        print(f"[RESTO_LISTA] ✅ Varredura concluída. Encontrados {len(lista_resto)} processos do resto")
        return lista_resto
        
    except Exception as e:
        print(f"[RESTO_LISTA] ❌ Erro ao criar lista do resto: {e}")
        return []



    """Helper: Configura filtros de observação e carrega progresso."""
    if filtros_observacao is None:
        filtros_observacao = ['xs', 'silas', 'sobrestamento', 'sob ']

    print(f"[INDEXAR] Filtros aplicados: {filtros_observacao}")
    progresso = carregar_progresso_pec()
    return filtros_observacao, progresso



def _indexar_todos_processos(driver: Any) -> Optional[List[Dict[str, Any]]]:
    """Helper: Indexa todos os processos da lista usando seletor específico para PEC."""
    print("[INDEXAR] 1. Indexando todos os processos da lista...")

    try:
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        if not linhas:
            print("[INDEXAR] ❌ Nenhuma linha encontrada com seletor tr.tr-class")
            return None

        print(f"[INDEXAR] ✅ Encontradas {len(linhas)} linhas na tabela")

        todos_processos = []
        padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')

        for idx, linha in enumerate(linhas):
            try:
                colunas = linha.find_elements(By.TAG_NAME, 'td')
                if len(colunas) < 6:
                    continue

                # Extrair número do processo da 2ª coluna
                celula_processo = colunas[1]
                numero_processo = None

                elemento_b = celula_processo.find_element(By.TAG_NAME, 'b')
                if elemento_b:
                    texto_b = elemento_b.text.strip()
                    match = padrao_proc.search(texto_b)
                    if match:
                        numero_processo = match.group(0)

                if not numero_processo:
                    print(f"[INDEXAR] ⚠️ Linha {idx + 1}: número do processo não encontrado")
                    continue

                # Extrair observação da 6ª coluna
                celula_observacao = colunas[5]
                observacao = ""

                try:
                    span_observacao = celula_observacao.find_element(By.CSS_SELECTOR, 'span.texto-descricao')
                    observacao = span_observacao.text.lower().strip()
                except:
                    observacao = celula_observacao.text.lower().strip()

                if not observacao:
                    print(f"[INDEXAR] ⚠️ Linha {idx + 1}: observação não encontrada")
                    continue

                todos_processos.append({
                    'numero': numero_processo,
                    'observacao': observacao,
                    'linha': linha,
                    'linha_index': idx
                })

            except Exception as e:
                print(f"[INDEXAR] ⚠️ Erro ao processar linha {idx + 1}: {e}")
                continue

        print(f"[INDEXAR] ✅ Indexados {len(todos_processos)} processos válidos")
        return todos_processos

    except Exception as e:
        print(f"[INDEXAR] ❌ Erro na indexação: {e}")
        return None



def _filtrar_por_observacao(todos_processos: List[Dict[str, Any]], filtros_observacao: List[str]) -> List[Dict[str, Any]]:
    """Helper: Filtra processos por critérios de observação."""
    print("[INDEXAR] 2. Filtrando por observação...")

    processos_filtrados = []
    for processo in todos_processos:
        observacao = processo['observacao']
        passa_filtro = False

        for filtro in filtros_observacao:
            if filtro.lower() in observacao:
                passa_filtro = True
                break

        if passa_filtro:
            processos_filtrados.append(processo)

    print(f"[INDEXAR] ✅ {len(processos_filtrados)} processos passaram no filtro de observação")

    # Salvar amostra para diagnóstico se nenhum processo passou
    if len(processos_filtrados) == 0:
        _salvar_amostra_debug_rows(todos_processos)

    return processos_filtrados



def _salvar_amostra_debug_rows(processos: List[Dict[str, Any]]) -> None:
    """Helper: Salva amostra de linhas para diagnóstico quando nenhum processo passa no filtro."""
    try:
        dump_path = 'debug_rows_sample.html'
        with open(dump_path, 'w', encoding='utf-8') as f:
            f.write('<html><head><meta charset="utf-8"><title>Debug Rows Sample</title></head><body>')
            f.write(f'<h2>Found {len(processos)} raw rows - sample outerHTML:</h2>')
            for i, p in enumerate(processos[:10]):
                try:
                    linha = p.get('linha')
                    if linha:
                        outer = linha.get_attribute('outerHTML') or linha.get_attribute('innerHTML') or ''
                        f.write(f'<h3>Row {i}</h3>')
                        f.write('<div style="border:1px solid #888;padding:8px;margin:4px;">')
                        f.write(outer)
                        f.write('</div><hr/>')
                except Exception:
                    continue
            f.write('</body></html>')
        print(f"[INDEXAR][DIAGNOSTICO] ✅ Arquivo de amostra salvo em {dump_path}")
    except Exception as diag_e:
        print(f"[INDEXAR][DIAGNOSTICO] ⚠️ Falha ao salvar debug_rows_sample: {diag_e}")



def _filtrar_por_progresso(processos_filtrados: List[Dict[str, Any]], progresso: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Helper: Filtra processos que já foram executados."""
    print("[INDEXAR] 3. Filtrando processos já executados...")

    processos_pendentes = []
    processos_pulados = 0

    for processo in processos_filtrados:
        numero_processo = processo['numero']

        if processo_ja_executado_pec(numero_processo, progresso):
            print(f"[INDEXAR] ⏭️ Processo {numero_processo} já executado, pulando...")
            processos_pulados += 1
        else:
            processos_pendentes.append(processo)
            print(f"[INDEXAR] ✅ Processo {numero_processo} será processado")

    print(f"[INDEXAR] {processos_pulados} processos pulados (já executados)")
    print(f"[INDEXAR] {len(processos_pendentes)} processos serão processados")

    return processos_pendentes



def _filtrar_por_acoes_validas(processos_pendentes: List[Dict[str, Any]], progresso: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Helper: Filtra processos por ações válidas antes de abrir."""
    print("[INDEXAR] 3.5. Filtrando processos por ações válidas...")

    processos_para_abrir = []
    processos_pulados_sem_regra = 0

    for processo in processos_pendentes:
        numero_processo = processo['numero']
        observacao = processo['observacao']

        acoes_result = determinar_acoes_por_observacao(observacao)

        if not acoes_result:
            processos_pulados_sem_regra += 1
        else:
            acoes = acoes_result  # Lista de funções
            
            # Extrair nome das ações para logging
            nomes_acoes = [a.__name__ if callable(a) else str(a) for a in acoes]
            
            processo['acoes'] = acoes  # Armazenar LISTA de ações
            processos_para_abrir.append(processo)

    print(f"[INDEXAR] {processos_pulados_sem_regra} processos sem regra definida (ignorados)")
    print(f"[INDEXAR] {len(processos_para_abrir)} processos com ações válidas")

    return processos_para_abrir



def _agrupar_em_buckets(processos_para_abrir: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Helper: Agrupa processos em buckets baseado na PRIMEIRA AÇÃO.
    A primeira ação já foi determinada por determinar_acoes_por_observacao."""
    print("[INDEXAR] 3.8. Agrupando processos em buckets (sob, carta, comunicacoes, sobrestamento, sisbajud)...")

    buckets = {
        'sob': [],
        'carta': [],
        'comunicacoes': [],
        'outros': [],
        'sobrestamento': [],
        'sisbajud': []
    }

    sisbajud_names = {'minuta_bloqueio', 'minuta_bloqueio_60', 'processar_ordem_sisbajud', 'processar_ordem_sisbajud_wrapper'}
    carta_names = {'carta', 'analisar_documentos_pos_carta'}
    sob_names = {'mov_sob', 'def_chip', 'mov_aud'}
    sobrestamento_names = {'def_sob'}

    for p in processos_para_abrir:
        acoes = p.get('acoes', [])
        if not acoes:
            buckets['outros'].append(p)
            continue

        # Usar PRIMEIRA ação para classificar bucket
        primeira_acao = acoes[0]
        acao_nome = primeira_acao.__name__ if callable(primeira_acao) else str(primeira_acao)

        if acao_nome in sisbajud_names:
            buckets['sisbajud'].append(p)
        elif acao_nome in carta_names:
            buckets['carta'].append(p)
        elif acao_nome in sob_names:
            buckets['sob'].append(p)
        elif acao_nome in sobrestamento_names:
            buckets['sobrestamento'].append(p)
        elif acao_nome.startswith('pec_'):  # ← Qualquer ação pec_* vai para comunicacoes
            buckets['comunicacoes'].append(p)
        else:
            buckets['outros'].append(p)

    # Log resumido dos buckets
    print("\n[BUCKETS] 📊 Processos agrupados por ação:")
    print(f"  • sob: {len(buckets['sob'])} processos")
    print(f"  • carta: {len(buckets['carta'])} processos")
    print(f"  • comunicacoes: {len(buckets['comunicacoes'])} processos")
    print(f"  • sobrestamento: {len(buckets['sobrestamento'])} processos")
    print(f"  • sisbajud: {len(buckets['sisbajud'])} processos")
    print(f"  • outros: {len(buckets['outros'])} processos")
    print()

    return buckets



def _executar_dry_run(buckets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """Helper: Executa dry run mostrando buckets sem processar."""
    print('[INDEXAR][DRY_RUN] Dry run enabled - not opening processes. Showing bucket summary:')
    for name in ['sob', 'carta', 'citacoes', 'intimacoes', 'outros', 'sobrestamento', 'sisbajud']:
        bucket = buckets.get(name, [])
        print(f"  - {name}: {len(bucket)} processes")
        if bucket:
            sample = [p.get('numero') for p in bucket[:10]]
            print(f"     sample: {sample}")
    return buckets



def _processar_buckets(driver: Any, buckets: Dict[str, List[Dict[str, Any]]], progresso: Dict[str, Any]) -> bool:
    """Helper: Processa todos os buckets na ordem correta."""
    total_results = {'sucesso': 0, 'erro': 0}

    # Processar buckets não-SISBAJUD
    for name in ['sob', 'carta', 'citacoes', 'intimacoes', 'outros', 'sobrestamento']:
        bucket = buckets.get(name, [])
        if not bucket:
            continue
        res = _processar_bucket_demais(driver, bucket, progresso, descricao=name.upper())
        total_results['sucesso'] += res.get('sucesso', 0)
        total_results['erro'] += res.get('erro', 0)

    # Processar SISBAJUD por último
    processos_sisbajud = buckets.get('sisbajud', [])
    if processos_sisbajud:
        print(f"[BUCKETS_PEC] 📂 Processando bucket 'sisbajud' com {len(processos_sisbajud)} processos...")
        res = _processar_bucket_sisbajud(driver, processos_sisbajud, progresso)
        total_results['sucesso'] += res.get('sucesso', 0)
        total_results['erro'] += res.get('erro', 0)

    # Relatório final
    _imprimir_relatorio_final(buckets, total_results)
    return True



def _processar_bucket_generico(driver: Any, processos: List[Dict[str, Any]], progresso: Dict[str, Any], nome_bucket: str = "GENERICO") -> Dict[str, int]:
    """
    FUNÇÃO GENÉRICA ÚNICA: Processa QUALQUER bucket seguindo o fluxo padrão.

    Fluxo universal para TODOS os buckets:
    1. Abrir processo no PJE
    2. Executar ações definidas nas regras
    3. Fechar processo e voltar para lista

    Args:
        driver: WebDriver do Selenium
        processos: Lista de processos do bucket
        progresso: Dicionário de progresso
        nome_bucket: Nome do bucket para logs

    Returns:
        dict: {'sucesso': int, 'erro': int}
    """
    # Carregar módulos pesados sob demanda
    cache = _lazy_import_pec()
    abrir_detalhes_processo = cache['abrir_detalhes_processo']
    trocar_para_nova_aba = cache['trocar_para_nova_aba']
    reindexar_linha = cache['reindexar_linha']
    
    print(f"[BUCKET:{nome_bucket}] Processando {len(processos)} processos...")

    resultados = {'sucesso': 0, 'erro': 0}
    aba_lista_original = driver.current_window_handle

    consecutive_reindex_fails = 0
    MAX_CONSECUTIVE_FAILS = 2

    # Contador específico para erros do tipo StaleElementReference/UnboundLocalError
    consecutive_stale_errors = 0
    MAX_STALE_ERRORS = 3

    def _solicitar_reinicio_por_stale(numero_processo: Optional[str], detalhes: str) -> None:
        """Helper: injeta exceção de reinício com checagem da URL."""
        try:
            url_atual = driver.current_url
        except Exception:
            url_atual = ""

        acesso_negado_flag = False
        try:
            acesso_negado_flag = verificar_acesso_negado_pec(driver)
        except Exception:
            lower_url = url_atual.lower() if url_atual else ""
            acesso_negado_flag = any(token in lower_url for token in ['acesso-negado', 'access-denied', 'login.jsp'])

        msg = (
            f"RESTART_PEC: stale_errors={consecutive_stale_errors} acesso_negado={acesso_negado_flag} "
            f"for {numero_processo or '<desconhecido>'} -> {detalhes}"
        )
        if url_atual:
            msg = f"{msg} | url={url_atual}"
        raise Exception(msg)

    for idx, processo_info in enumerate(processos):
        numero_processo = processo_info.get('numero')
        observacao = processo_info.get('observacao')
        linha = processo_info.get('linha')
        linha_index = processo_info.get('linha_index')
        acao_nome = processo_info.get('acao')
        acao_func = processo_info.get('acao_func')

        # Garantir que temos a função de ação
        if not acao_func and acao_nome:
            temp_result = determinar_acao_por_observacao(observacao)
            if temp_result is not None:
                acao_func = temp_result

        print(f"[BUCKET:{nome_bucket}] {idx+1}/{len(processos)} -> {numero_processo} ({acao_nome})")

        resultado_processo = False
        try:
            # Verificar se já foi executado
            if processo_ja_executado_pec(numero_processo, progresso):
                print(f"[BUCKET:{nome_bucket}] ⏭️ {numero_processo} já executado, pulando")
                continue

            # Reindexar linha se necessário
            linha_atual = linha
            try:
                linha_atual.is_displayed()
            except Exception:
                linha_atual = reindexar_linha(driver, numero_processo)
                if not linha_atual:
                    consecutive_reindex_fails += 1
                    acesso_negado = False
                    try:
                        acesso_negado = verificar_acesso_negado_pec(driver)
                    except Exception:
                        acesso_negado = False

                    # Se acesso negado, REINICIAR DRIVER (não marcar como executado!)
                    if acesso_negado:
                        msg = f"RESTART_PEC: ACESSO_NEGADO detectado para {numero_processo}"
                        print(f"[BUCKET:{nome_bucket}] ⚠️ {msg}")
                        print(f"[BUCKET:{nome_bucket}] 🔄 Reiniciando driver devido a acesso negado...")
                        raise Exception(msg)
                    
                    # Se muitos erros consecutivos, reiniciar
                    if consecutive_reindex_fails >= MAX_CONSECUTIVE_FAILS:
                        msg = f"RESTART_PEC: reindex failures={consecutive_reindex_fails} for {numero_processo}"
                        print(f"[BUCKET:{nome_bucket}] ⚠️ {msg}")
                        raise Exception(msg)

                    print(f"[BUCKET:{nome_bucket}] ❌ Não foi possível reindexar linha para {numero_processo} (fails={consecutive_reindex_fails})")
                    resultados['erro'] += 1
                    continue

            # TODOS os processos são processados individualmente abrindo sua própria aba
            # Independente do tipo de ação - buckets são apenas organizadores

            # Verificar se linha ainda é válida (similar ao executar_lista_sisbajud_por_abas)
            try:
                linha_atual.is_displayed()
            except:
                print(f"[BUCKET:{nome_bucket}] ⚠️ Linha ficou stale, tentando reindexar {numero_processo}...")
                linha_atual = reindexar_linha(driver, numero_processo)
                if not linha_atual:
                    print(f"[BUCKET:{nome_bucket}] ❌ Não foi possível reindexar linha para {numero_processo}")
                    resultados['erro'] += 1
                    continue

            # Abrir detalhes do processo
            if not abrir_detalhes_processo(driver, linha_atual):
                print(f"[BUCKET:{nome_bucket}] ❌ Botão de detalhes não encontrado para {numero_processo}")
                resultados['erro'] += 1
                continue

            time.sleep(1)

            # Abrir nova aba para o processo
            nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
            if not nova_aba:
                print(f"[BUCKET:{nome_bucket}] ❌ Nova aba do processo {numero_processo} não foi aberta")
                resultados['erro'] += 1
                continue

            time.sleep(2)
            print(f"[BUCKET:{nome_bucket}] Executando ação: {acao_nome}")
            resultado_processo = executar_acao_pec(driver, acao_func, numero_processo=numero_processo, observacao=observacao, debug=True)

            # Resultado
            if resultado_processo:
                resultados['sucesso'] += 1
                print(f"[BUCKET:{nome_bucket}] ✅ {numero_processo} processado com sucesso")
            else:
                resultados['erro'] += 1
                print(f"[BUCKET:{nome_bucket}] ❌ Falha ao processar {numero_processo}")

            # FECHAR ABAS E VOLTAR PARA LISTA
            try:
                if aba_lista_original in driver.window_handles:
                    driver.switch_to.window(aba_lista_original)
                    for handle in driver.window_handles:
                        if handle != aba_lista_original:
                            try:
                                driver.switch_to.window(handle)
                                driver.close()
                            except:
                                pass
                    driver.switch_to.window(aba_lista_original)
            except Exception as eback:
                print(f"[BUCKET:{nome_bucket}] ⚠️ Erro ao voltar para lista: {eback}")

            time.sleep(1)

        except KeyboardInterrupt:
            if resultado_processo:
                try:
                    marcar_processo_executado_pec(numero_processo, progresso)
                except:
                    pass
            raise

        except Exception as e:
            # Detectar padrões recorrentes de erro relacionados a elementos stale / reindex
            msg_exc = str(e)
            
            # RESTART_PEC deve ser propagado para o nível superior para reinício do driver
            if 'RESTART_PEC' in msg_exc:
                print(f"[BUCKET:{nome_bucket}] 🔄 Propagando RESTART_PEC para reinício do fluxo")
                raise
            
            is_stale_like = False

            # Exceções do Selenium indicando elemento stale
            if isinstance(e, StaleElementReferenceException):
                is_stale_like = True

            # Situações onde reindexar_linha falha gerando UnboundLocalError
            if isinstance(e, UnboundLocalError) or "cannot access local variable 'reindexar_linha'" in msg_exc:
                is_stale_like = True

            if is_stale_like:
                consecutive_stale_errors += 1
                print(f"[BUCKET:{nome_bucket}] ⚠️ Erro stale/reindex detectado ({consecutive_stale_errors}/{MAX_STALE_ERRORS}): {e}")

                precisa_reiniciar = (
                    isinstance(e, UnboundLocalError)
                    or 'reindexar_linha' in msg_exc
                    or consecutive_stale_errors >= MAX_STALE_ERRORS
                )

                if precisa_reiniciar:
                    _solicitar_reinicio_por_stale(numero_processo, msg_exc)
            else:
                # reset counter on other exceptions
                consecutive_stale_errors = 0

            print(f"[BUCKET:{nome_bucket}] ❌ Exceção ao processar {numero_processo}: {e}")
            resultados['erro'] += 1
            import traceback
            traceback.print_exc()

        finally:
            # Marcar progresso apenas se teve sucesso
            if resultado_processo:
                try:
                    marcar_processo_executado_pec(numero_processo, progresso)
                except Exception as prog_e:
                    print(f"[BUCKET:{nome_bucket}] ⚠️ Erro ao marcar progresso para {numero_processo}: {prog_e}")
            else:
                print(f"[BUCKET:{nome_bucket}] ⏭️ {numero_processo} NÃO marcado (não executado com sucesso)")

    return resultados



def _processar_bucket_demais(driver: Any, bucket: List[Dict[str, Any]], progresso: Dict[str, Any], descricao: str = "") -> Dict[str, int]:
    """[DEPRECATED] Mantida para compatibilidade - usa _processar_bucket_generico."""
    return _processar_bucket_generico(driver, bucket, progresso, descricao.upper())



def _processar_bucket_sisbajud(driver: Any, processos_sisbajud: List[Dict[str, Any]], progresso: Dict[str, Any]) -> Dict[str, int]:
    """
    Processa bucket SISBAJUD com driver compartilhado.
    
    OTIMIZAÇÃO: Usa um único driver SISBAJUD para todos os processos,
    evitando abrir/fechar o driver para cada processo.
    
    Delega para SISB/batch.py que implementa a lógica de lote.
    
    Args:
        driver: WebDriver PJE
        processos_sisbajud: Lista de processos do bucket
        progresso: Dicionário de progresso
        
    Returns:
        dict: {'sucesso': int, 'erro': int}
    """
    # Carregar módulos pesados sob demanda
    cache = _lazy_import_pec()
    abrir_detalhes_processo = cache['abrir_detalhes_processo']
    trocar_para_nova_aba = cache['trocar_para_nova_aba']
    reindexar_linha = cache['reindexar_linha']
    
    print(f"[SISBAJUD_BUCKET] 🚀 Processando {len(processos_sisbajud)} processos com driver compartilhado...")
    
    if not processos_sisbajud:
        print("[SISBAJUD_BUCKET] ⚠️ Nenhum processo para processar")
        return {'sucesso': 0, 'erro': 0}
    
    try:
        from SISB.batch import processar_lote_sisbajud
        
        resultados = processar_lote_sisbajud(
            driver_pje=driver,
            processos=processos_sisbajud,
            progresso=progresso,
            fn_reindexar_linha=reindexar_linha,
            fn_abrir_detalhes=abrir_detalhes_processo,
            fn_trocar_aba=trocar_para_nova_aba,
            fn_ja_executado=processo_ja_executado_pec,
            fn_marcar_executado=marcar_processo_executado_pec,
            log=True
        )
        
        print(f"[SISBAJUD_BUCKET] 📊 Resultado: {resultados['sucesso']} sucesso, {resultados['erro']} erros")
        return resultados
        
    except Exception as e:
        print(f"[SISBAJUD_BUCKET] ❌ Erro ao importar SISB.batch: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: usar método antigo
        return _processar_bucket_generico(driver, processos_sisbajud, progresso, "SISBAJUD")



def _imprimir_relatorio_final(buckets: Dict[str, List[Dict[str, Any]]], total_results: Dict[str, int]) -> None:
    """Helper: Imprime relatório final do processamento."""
    processos_sucesso = total_results['sucesso']
    processos_erro = total_results['erro']

    # Calcular total de processos pendentes (soma de todos os buckets)
    total_pendentes = sum(len(buckets.get(name, [])) for name in ['sob', 'carta', 'citacoes', 'intimacoes', 'outros', 'sobrestamento', 'sisbajud'])

    print(f"[INDEXAR] ========== RELATÓRIO FINAL ==========")
    print(f"[INDEXAR] Processos processados com sucesso: {processos_sucesso}")
    print(f"[INDEXAR] Processos com erro: {processos_erro}")
    print(f"[INDEXAR] Taxa de sucesso: {(processos_sucesso/total_pendentes*100):.1f}%" if total_pendentes else "N/A")
    print(f"[INDEXAR] =====================================")



def indexar_e_criar_buckets_unico(driver: Any, filtros_observacao: Optional[List[str]] = None, dry_run: bool = False) -> Union[bool, Dict[str, List[Dict[str, Any]]]]:
    """Lê tabela, agrupa processos em buckets pela observação, executa."""
    
    if filtros_observacao is None:
        filtros_observacao = ['xs', 'silas', 'sobrestamento', 'sob ']
    
    progresso = carregar_progresso_pec()
    buckets = {'sob': [], 'carta': [], 'comunicacoes': [], 'outros': [], 'sobrestamento': [], 'sisbajud': []}
    
    # Estatísticas detalhadas por bucket
    stats = {
        'sisbajud': {'detectados': 0, 'pulados_executados': 0, 'para_executar': 0},
        'sob': {'detectados': 0, 'pulados_executados': 0, 'para_executar': 0},
        'carta': {'detectados': 0, 'pulados_executados': 0, 'para_executar': 0},
        'comunicacoes': {'detectados': 0, 'pulados_executados': 0, 'para_executar': 0},
        'sobrestamento': {'detectados': 0, 'pulados_executados': 0, 'para_executar': 0},
        'outros': {'detectados': 0, 'pulados_executados': 0, 'para_executar': 0}
    }
    
    # Extrair linhas da tabela
    if isinstance(driver, str):
        from bs4 import BeautifulSoup
        linhas = BeautifulSoup(driver, 'html.parser').find_all('tr')
    else:
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        if not linhas:
            print("[PEC] ❌ Nenhuma linha encontrada")
            return False
    
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    
    # Processar cada linha: extração → filtros → bucket
    for idx, linha in enumerate(linhas):
        try:
            # Extrair número e observação
            if isinstance(driver, str):
                colunas = linha.find_all('td')
                if len(colunas) < 6:
                    continue
                texto_b = colunas[1].find('b')
                numero_processo = padrao_proc.search(texto_b.get_text()).group(0) if texto_b else None
                span_obs = colunas[5].find('span', class_='texto-descricao')
                observacao = (span_obs.get_text() if span_obs else colunas[5].get_text()).lower().strip()
            else:
                colunas = linha.find_elements(By.TAG_NAME, 'td')
                if len(colunas) < 6:
                    continue
                try:
                    texto_b = colunas[1].find_element(By.TAG_NAME, 'b').text
                    numero_processo = padrao_proc.search(texto_b).group(0) if texto_b else None
                except:
                    numero_processo = None
                try:
                    observacao = colunas[5].find_element(By.CSS_SELECTOR, 'span.texto-descricao').text.lower().strip()
                except:
                    observacao = colunas[5].text.lower().strip()
            
            if not numero_processo or not observacao:
                continue
            
            # Filtro de observação
            if not any(f.lower() in observacao for f in filtros_observacao):
                continue
            
            # Determinar ações (retorna lista)
            acoes_result = determinar_acoes_por_observacao(observacao)
            if not acoes_result:
                continue
            
            # Classificar no bucket baseado na PRIMEIRA ação
            primeira_acao = acoes_result[0]
            acao_nome = primeira_acao.__name__ if callable(primeira_acao) else str(primeira_acao)
            
            # Mapear nome da ação ao bucket
            sisbajud_names = {'minuta_bloqueio', 'minuta_bloqueio_60', 'processar_ordem_sisbajud', 'processar_ordem_sisbajud_wrapper'}
            carta_names = {'carta', 'analisar_documentos_pos_carta'}
            sob_names = {'mov_sob', 'def_chip', 'mov_aud'}
            sobrestamento_names = {'def_sob'}
            
            if acao_nome in sisbajud_names:
                bucket_nome = 'sisbajud'
            elif acao_nome in carta_names:
                bucket_nome = 'carta'
            elif acao_nome in sob_names:
                bucket_nome = 'sob'
            elif acao_nome in sobrestamento_names:
                bucket_nome = 'sobrestamento'
            elif acao_nome.startswith('pec_'):  # ← Qualquer ação pec_* vai para comunicacoes
                bucket_nome = 'comunicacoes'
            else:
                bucket_nome = 'outros'
            
            # Contar detectados
            stats[bucket_nome]['detectados'] += 1
            
            # Verificar se já foi executado
            if processo_ja_executado_pec(numero_processo, progresso):
                stats[bucket_nome]['pulados_executados'] += 1
                continue
            
            # Adicionar ao bucket
            stats[bucket_nome]['para_executar'] += 1
            buckets[bucket_nome].append({
                'numero': numero_processo,
                'observacao': observacao,
                'linha': linha,
                'linha_index': idx,
                'acoes': acoes_result
            })
        
        except Exception as e:
            continue
    
    # Mostrar estatísticas detalhadas
    total = sum(len(b) for b in buckets.values())
    print(f"\n[PEC] 📋 BUCKETS FORMADOS:")
    for nome in ['sisbajud', 'sob', 'carta', 'comunicacoes', 'sobrestamento', 'outros']:
        st = stats[nome]
        if st['detectados'] > 0:
            print(f"  • {nome.upper()}:")
            print(f"      Detectados na tabela: {st['detectados']}")
            print(f"      Já executados (pulados): {st['pulados_executados']}")
            print(f"      Para executar agora: {st['para_executar']}")
    
    print(f"\n[PEC] 🚀 Total a processar: {total}")
    
    return buckets if dry_run else _processar_buckets(driver, buckets, progresso)



