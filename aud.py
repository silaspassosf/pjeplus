"""
aud.py

Fluxo para varrer a lista "Novos Processos" e agrupar em buckets A/B/C
conforme regras do usuário, executando ações apropriadas por bucket.

Uso: importar e chamar run_aud() ou executar diretamente como script.

Observações/assunções:
- Este módulo usa funções de `Fix.utils` para criar driver e fazer login.
- Para criar gigs chamamos `criar_gigs` de `Fix.extracao` passando os parâmetros
  indicados pelo usuário ("-1", "xs marcar aud"). Se a assinatura de
  `criar_gigs` for diferente, pode ser necessário ajustar os argumentos.
- Para `ato_100` verificamos se existe `ato_100` em `atos.py`; se não, apenas logamos.
- Para `pec_ord`/`pec_sum` usamos as wrappers em `atos.py` e, quando aplicável,
  também chamamos `mov_aud` após a notificação (compatível com alteração em `pec.py`).
"""

import time
import json
import traceback
from typing import List, Dict, Any, Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Importar do módulo /Fix (novo)
from Fix.utils import configurar_recovery_driver, handle_exception_with_recovery
from Fix.abas import validar_conexao_driver, trocar_para_nova_aba
from Fix.extracao import abrir_detalhes_processo, criar_gigs, extrair_dados_processo
from Fix.core import preencher_multiplos_campos, aguardar_e_clicar, esperar_elemento, safe_click, preencher_campo

# Importa sistema unificado de progresso
from progresso_unificado import ProgressoUnificado

# Instância global do sistema de progresso para AUD
progresso_sistema = ProgressoUnificado("AUD")

def carregar_progresso_aud():
    """Carrega o estado de progresso usando sistema unificado"""
    return progresso_sistema.carregar_progresso()

def salvar_progresso_aud(progresso):
    """Salva o estado de progresso usando sistema unificado"""
    return progresso_sistema.salvar_progresso(progresso)

def processo_ja_executado_aud(numero_processo, progresso=None):
    """Verifica se o processo já foi executado no fluxo AUD usando sistema unificado"""
    if not numero_processo:
        return False
    return progresso_sistema.processo_ja_executado(numero_processo, progresso)

def marcar_processo_executado_aud(numero_processo, progresso=None, status="SUCESSO", detalhes=None):
    """Marca processo como executado no fluxo AUD usando sistema unificado"""
    if not numero_processo:
        return progresso
    return progresso_sistema.marcar_processo_executado(numero_processo, status, detalhes, progresso)


def acao_bucket_a(driver, numero_processo, processo_info):
    """Ação para bucket A: marcar audiência para 100% digital."""
    try:
        tipo = (processo_info.get('tipo') or '').upper().strip()
        tem_100 = bool(processo_info.get('tem_100', False))

        extrair_dados_processo(driver)
        numero_formatado = None
        id_processo = None
        try:
            with open('dadosatuais.json', 'r', encoding='utf-8') as f:
                dados = json.load(f)
            num_list = dados.get('numero') if isinstance(dados, dict) else None
            if isinstance(num_list, list) and num_list:
                numero_formatado = num_list[0]
            elif isinstance(num_list, str):
                numero_formatado = num_list
            id_processo = dados.get('id') if isinstance(dados, dict) else None
        except Exception as e:
            print(f"[AUD][A] ❌ Erro ao ler dadosatuais.json: {e}")
        if not numero_formatado or not id_processo:
            print(f"[AUD][A] ❌ Falha ao extrair número/ID do processo {numero_processo}")
            return False

        rito = 'ATSum' if tipo == 'ATSUM' else 'ATOrd'

        # Se NÃO é 100% digital: marcar audiência + executar ato_unap + GIGS conforme tipo
        if not tem_100:
            print(f"[AUD][A] Processo {numero_processo} sem 100% digital. Marcando audiência, executando ato_unap e GIGS.")
            
            # 1) Marcar audiência na pauta
            marcar_aud(driver, numero_formatado, rito, driver.current_window_handle)
            
            # 2) Criar GIGS conforme tipo
            observacao = "xs sum" if tipo == 'ATSUM' else "xs ord"
            try:
                print(f"[AUD][A] Criando GIGS para {numero_processo} (prazo: 1, observacao: {observacao})")
                criar_gigs(driver, "1", "", observacao)
            except Exception as e:
                print(f"[AUD][A] ⚠️ Erro ao criar GIGS: {e}")

            # 3) Executar ato_unap
            try:
                from atos import ato_unap
                print(f"[AUD][A] Executando ato_unap para {numero_processo}")
                return bool(ato_unap(driver, debug=True))
            except Exception as e:
                print(f"[AUD][A] ⚠️ Erro ao executar ato_unap: {e}")
                return False

        if tipo not in ['ATORD', 'ATSUM', 'ACUM', 'ACCUM']:
            print(f"[AUD][A] Processo {numero_processo} não atende critérios de rito. Pulando.")
            return True

        # 1) Desmarcar 100% (mantém aba /retificar aberta)
        aba_retificar = desmarcar_100(driver, id_processo)
        if not aba_retificar:
            print(f"[AUD][A] ❌ Não foi possível abrir/usar aba retificar")
            return False

        # 2) Marcar audiência na pauta (abre e fecha aba de audiência)
        marcar_aud(driver, numero_formatado, rito, aba_retificar)

        # 3) De volta à aba /retificar: repetir toggle + sim, fechar
        try:
            if aba_retificar in driver.window_handles:
                driver.switch_to.window(aba_retificar)
                remarcar_100_pos_aud(driver)
                driver.close()
        except Exception as e:
            print(f"[AUD][A] ⚠️ Erro ao finalizar retificar: {e}")

        # 4) Retornar à aba detalhe
        try:
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if '/detalhe' in driver.current_url:
                    break
        except Exception:
            pass

        # 5) Pós-audiência: responsável + GIGS + ato_100 (igual bloco 100%)
        try:
            print(f"[AUD][A] Definindo responsável para {numero_processo}")
            input_responsavel = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[aria-label="Sem Responsável"]'))
            )
            input_responsavel.click()
            input_responsavel.clear()
            input_responsavel.send_keys("SILAS")
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span.mat-option-text'))
            )
            opcao_silas = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), 'SILAS PASSOS FERREIRA')]"))
            )
            opcao_silas.click()
            # Garantir que a seleção foi aplicada: desfocar e aguardar atributo preenchido
            try:
                driver.execute_script("document.activeElement.blur();")
            except Exception:
                pass

            try:
                WebDriverWait(driver, 5).until(
                    lambda d: ('SILAS PASSOS FERREIRA' in (input_responsavel.get_attribute('aria-label') or '')
                               or 'SILAS PASSOS FERREIRA' in (input_responsavel.get_attribute('value') or ''))
                )
                print(f"[AUD][A] ✅ Campo responsável confirmado visivelmente preenchido")
            except Exception:
                # Tentar clicar fora como fallback e aguardar mais um pouco
                try:
                    body = driver.find_element(By.TAG_NAME, 'body')
                    body.click()
                except Exception:
                    pass
                time.sleep(1)
        except Exception as e:
            print(f"[AUD][A] ⚠️ Erro ao definir responsável: {e}")

        try:
            observacao = "xs sum" if tipo == 'ATSUM' else "xs ord"
            print(f"[AUD][A] Criando GIGS para {numero_processo} (prazo: 1, observacao: {observacao})")
            criar_gigs(driver, "1", "", observacao)
        except Exception as e:
            print(f"[AUD][A] ⚠️ Erro ao criar GIGS: {e}")

        try:
            from atos import ato_100
            print(f"[AUD][A] Executando ato_100 para {numero_processo}")
            ato_100(driver, debug=True)
        except Exception as e:
            print(f"[AUD][A] ⚠️ Erro ao executar ato_100: {e}")

        return True
    except Exception as e:
        print(f"[AUD][A] Erro ao executar ações: {e}")
        return False

def indexar_e_processar_lista_aud(driver):
    """
    Indexa e processa lista de processos AUD com controle de progresso.
    
    SEGUINDO O PADRÃO CORRETO DO PEC.PY:
    1. PRIMEIRO indexa todos os processos da lista
    2. DEPOIS filtra quais já foram executados
    3. ENTÃO agrupa em buckets A/B/C
    4. FINALMENTE processa cada bucket individualmente
    
    Returns:
        dict: Resultado do processamento com estatísticas
    """
    try:
        print("[AUD] Iniciando indexação e processamento da lista...")
        
        # Carregar progresso atual
        progresso = carregar_progresso_aud()
        
        # ===== ETAPA 1: INDEXAR TODOS OS PROCESSOS DA LISTA =====
        print("[AUD] 1. Indexando todos os processos da lista...")
        
        lista_processos = coletar_lista_processos(driver)
        if not lista_processos:
            print("[AUD] ❌ Nenhuma linha encontrada na lista")
            return {"sucesso": False, "erro": "Lista vazia"}
        
        print(f"[AUD] ✅ Indexados {len(lista_processos)} processos da lista")
        
        # ===== ETAPA 2: FILTRAR POR PROGRESSO (JÁ EXECUTADOS) =====
        print("[AUD] 2. Filtrando processos já executados...")
        
        processos_pendentes = []
        processos_pulados = 0
        
        for processo in lista_processos:
            numero_processo = processo.get('numero')
            
            if processo_ja_executado_aud(numero_processo, progresso):
                print(f"[AUD] ⏭️ Processo {numero_processo} já executado, pulando...")
                processos_pulados += 1
            else:
                processos_pendentes.append(processo)
                print(f"[AUD] ✅ Processo {numero_processo} será processado")
        
        print(f"[AUD] {processos_pulados} processos pulados (já executados)")
        print(f"[AUD] {len(processos_pendentes)} processos serão processados")
        
        if not processos_pendentes:
            print("[AUD] ⚠️ Todos os processos já foram executados!")
            return {"sucesso": True, "processos_executados": 0, "total_na_lista": len(lista_processos)}
        
        # ===== ETAPA 3: AGRUPAR EM BUCKETS =====
        print("[AUD] 3. Agrupando em buckets A/B/C...")
        
        A, B, C, D = agrupar_em_buckets(processos_pendentes)
        
        # Calcular total de processos que passaram pelo filtro de Triagem Inicial
        total_processos_triagem = len(A) + len(B) + len(C) + len(D)
        
        print(f"[AUD] Buckets: A={len(A)} B={len(B)} C={len(C)}")
        
        # ===== ETAPA 4: PROCESSAR BUCKETS =====
        print("[AUD] 4. Processando buckets...")
        
        resultados = {'A': [], 'B': [], 'C': []}
        aba_lista_original = driver.current_window_handle
        
        def processar_bucket(bucket, bucket_nome, acao_callback):
            """Processa um bucket específico abrindo cada processo e executando ação"""
            resultados_bucket = []
            
            for idx, processo_info in enumerate(bucket):
                numero_processo = processo_info.get('numero')
                print(f"[AUD][{bucket_nome}] Processando {idx+1}/{len(bucket)}: {numero_processo}")
                
                # Reindexar linha se necessário
                linha_atual = processo_info.get('linha')
                try:
                    linha_atual.is_displayed()
                except:
                    linha_atual = reindexar_linha_js(driver, numero_processo)
                    if not linha_atual:
                        print(f"[AUD][{bucket_nome}] ❌ Não foi possível reindexar linha para {numero_processo}")
                        resultados_bucket.append({
                            'numero': numero_processo,
                            'acao': f'bucket_{bucket_nome.lower()}',
                            'ok': False,
                            'msg': 'Falha ao reindexar linha'
                        })
                        continue
                
                # Abrir detalhes do processo
                if not abrir_detalhes_processo(driver, linha_atual):
                    print(f"[AUD][{bucket_nome}] ❌ Botão de detalhes não encontrado para {numero_processo}")
                    resultados_bucket.append({
                        'numero': numero_processo,
                        'acao': f'bucket_{bucket_nome.lower()}',
                        'ok': False,
                        'msg': 'Botão de detalhes não encontrado'
                    })
                    continue
                
                time.sleep(1)
                
                # Trocar para nova aba
                nova_aba = trocar_para_nova_aba(driver, aba_lista_original)
                if not nova_aba:
                    print(f"[AUD][{bucket_nome}] ❌ Nova aba do processo {numero_processo} não foi aberta")
                    resultados_bucket.append({
                        'numero': numero_processo,
                        'acao': f'bucket_{bucket_nome.lower()}',
                        'ok': False,
                        'msg': 'Falha ao abrir nova aba'
                    })
                    continue
                
                time.sleep(2)
                
                # Executar ação específica do bucket
                try:
                    sucesso = acao_callback(driver, numero_processo, processo_info)
                    resultados_bucket.append({
                        'numero': numero_processo,
                        'acao': f'bucket_{bucket_nome.lower()}',
                        'ok': sucesso,
                        'msg': '' if sucesso else 'Ação falhou'
                    })
                except Exception as e:
                    print(f"[AUD][{bucket_nome}] ❌ Erro ao executar ação para {numero_processo}: {e}")
                    resultados_bucket.append({
                        'numero': numero_processo,
                        'acao': f'bucket_{bucket_nome.lower()}',
                        'ok': False,
                        'msg': str(e)
                    })
                
                # Voltar para lista e fechar aba extra
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
                    print(f"[AUD][{bucket_nome}] ⚠️ Erro ao voltar para lista: {eback}")
                
                time.sleep(1)
            
            return resultados_bucket
        
        def acao_bucket_b(driver, numero_processo, processo_info):
            """Ação para bucket B: definir responsável + criar gigs específico + ato_100"""
            try:
                # ===== PRIMEIRA AÇÃO: DEFINIR RESPONSÁVEL =====
                print(f"[AUD][B] Definindo responsável para {numero_processo}")
                
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.keys import Keys
                
                try:
                    # 1. Localizar e clicar no input de responsável
                    input_responsavel = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[aria-label="Sem Responsável"]'))
                    )
                    input_responsavel.click()
                    print(f"[AUD][B] ✅ Input de responsável clicado")
                    
                    # 2. Digitar "SILAS"
                    input_responsavel.clear()
                    input_responsavel.send_keys("SILAS")
                    print(f"[AUD][B] ✅ Digitado 'SILAS'")
                    
                    # 3. Aguardar e selecionar a opção "SILAS PASSOS FERREIRA"
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'span.mat-option-text'))
                    )
                    
                    # Encontrar a opção específica
                    opcao_silas = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), 'SILAS PASSOS FERREIRA')]"))
                    )
                    opcao_silas.click()
                    print(f"[AUD][B] ✅ Opção 'SILAS PASSOS FERREIRA' selecionada")

                    def responsavel_confirmado():
                        label = input_responsavel.get_attribute('aria-label') or ''
                        value = input_responsavel.get_attribute('value') or ''
                        return 'SILAS PASSOS FERREIRA' in label or 'SILAS PASSOS FERREIRA' in value

                    driver.execute_script("document.activeElement.blur();")

                    try:
                        WebDriverWait(driver, 5).until(lambda _driver: responsavel_confirmado())
                        print(f"[AUD][B] ✅ Responsável confirmado visivelmente preenchido")
                    except Exception:
                        try:
                            body = driver.find_element(By.TAG_NAME, 'body')
                            body.click()
                        except Exception:
                            pass
                        time.sleep(0.5)
                        if not responsavel_confirmado():
                            raise
                        print(f"[AUD][B] ✅ Responsável confirmado após clicar fora")
                    print(f"[AUD][B] ✅ Responsável definido: SILAS PASSOS FERREIRA")
                    
                except Exception as e:
                    print(f"[AUD][B] ⚠️ Erro ao definir responsável: {e}")
                    # Continua mesmo se falhar, pois não é crítico
                
                # ===== SEGUNDA AÇÃO: CRIAR GIGS =====
                tipo = (processo_info.get('tipo') or '').upper()
                
                # Determinar observação baseada no tipo do processo
                # ATord e Accum -> xs ord
                # ATsum -> xs sum
                if tipo == 'ATSUM':
                    observacao = "xs sum"
                else:  # ATORD ou ACUM
                    observacao = "xs ord"
                
                print(f"[AUD][B] Criando GIGS para {numero_processo} (prazo: 1, observacao: {observacao})")
                criar_gigs(driver, "1", "", observacao)
                
                # ===== TERCEIRA AÇÃO: EXECUTAR ATO_100 =====
                try:
                    from atos import ato_100
                    print(f"[AUD][B] Executando ato_100 para {numero_processo}")
                    ato_100(driver, debug=True)
                except Exception as e:
                    print(f"[AUD][B] ⚠️ Erro ao executar ato_100: {e}")
                
                print(f"[AUD][B] ✅ GIGS criado com sucesso para {numero_processo}")
                return True
            except Exception as e:
                print(f"[AUD][B] Erro ao criar GIGS: {e}")
                return False
        
        def acao_bucket_c(driver, numero_processo, processo_info):
            """Ação para bucket C: pec_ord ou pec_sum + mov_aud"""
            try:
                tipo = (processo_info.get('tipo') or '').upper()
                
                if tipo == 'ATSUM':
                    # pec_sum (vem de atos.py que ainda não foi refatorado)
                    try:
                        from atos import pec_sum, mov_aud
                        print(f"[AUD][C] Executando pec_sum para {numero_processo}")
                        ok = pec_sum(driver, debug=True)
                        if ok:
                            # mov_aud após pec_sum
                            print(f"[AUD][C] Executando mov_aud após pec_sum")
                            mov_ok = mov_aud(driver, debug=True)
                            return bool(mov_ok)
                        return False
                    except ImportError:
                        print("[AUD][C] pec_sum não disponível")
                        return False
                else:
                    # pec_ord (default para ATORD ou ACUM) (vem de atos.py que ainda não foi refatorado)
                    try:
                        from atos import pec_ord, mov_aud
                        print(f"[AUD][C] Executando pec_ord para {numero_processo}")
                        ok = pec_ord(driver, debug=True)
                        if ok:
                            # mov_aud após pec_ord
                            print(f"[AUD][C] Executando mov_aud após pec_ord")
                            mov_ok = mov_aud(driver, debug=True)
                            return bool(mov_ok)
                        return True
                    except ImportError:
                        print("[AUD][C] pec_ord não disponível")
                        return False
            except Exception as e:
                print(f"[AUD][C] Erro na ação: {e}")
                return False
        
        def acao_bucket_d(driver, numero_processo, processo_info):
            """Ação para bucket D: marcar responsável Silas Passos + executar ato_ratif"""
            try:
                # ===== PRIMEIRA AÇÃO: DEFINIR RESPONSÁVEL =====
                print(f"[AUD][D] Definindo responsável para {numero_processo}")
                
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.keys import Keys
                
                try:
                    # 1. Localizar e clicar no input de responsável
                    input_responsavel = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[aria-label="Sem Responsável"]'))
                    )
                    input_responsavel.click()
                    print(f"[AUD][D] ✅ Input de responsável clicado")
                    
                    # 2. Digitar "SILAS"
                    input_responsavel.clear()
                    input_responsavel.send_keys("SILAS")
                    print(f"[AUD][D] ✅ Digitado 'SILAS'")
                    
                    # 3. Aguardar e selecionar a opção "SILAS PASSOS FERREIRA"
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'span.mat-option-text'))
                    )
                    
                    # Encontrar a opção específica
                    opcao_silas = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), 'SILAS PASSOS FERREIRA')]"))
                    )
                    opcao_silas.click()
                    print(f"[AUD][D] ✅ Opção 'SILAS PASSOS FERREIRA' selecionada")

                    def responsavel_confirmado():
                        label = input_responsavel.get_attribute('aria-label') or ''
                        value = input_responsavel.get_attribute('value') or ''
                        return 'SILAS PASSOS FERREIRA' in label or 'SILAS PASSOS FERREIRA' in value

                    driver.execute_script("document.activeElement.blur();")

                    try:
                        WebDriverWait(driver, 5).until(lambda _driver: responsavel_confirmado())
                        print(f"[AUD][D] ✅ Responsável confirmado visivelmente preenchido")
                    except Exception:
                        try:
                            body = driver.find_element(By.TAG_NAME, 'body')
                            body.click()
                        except Exception:
                            pass
                        time.sleep(0.5)
                        if not responsavel_confirmado():
                            raise
                        print(f"[AUD][D] ✅ Responsável confirmado após clicar fora")
                    print(f"[AUD][D] ✅ Responsável definido: SILAS PASSOS FERREIRA")
                    
                except Exception as e:
                    print(f"[AUD][D] ⚠️ Erro ao definir responsável: {e}")
                    # Continua mesmo se falhar, pois não é crítico
                
                # ===== SEGUNDA AÇÃO: EXECUTAR ATO_RATIF =====
                try:
                    from xx.atos import ato_ratif
                    print(f"[AUD][D] Executando ato_ratif para {numero_processo}")
                    ok = ato_ratif(driver, debug=True)
                    if ok:
                        print(f"[AUD][D] ✅ ato_ratif executado com sucesso")
                        return True
                    else:
                        print(f"[AUD][D] ❌ ato_ratif falhou")
                        return False
                except ImportError:
                    print(f"[AUD][D] ato_ratif não disponível")
                    return False
                except Exception as e:
                    print(f"[AUD][D] Erro ao executar ato_ratif: {e}")
                    return False
            
            except Exception as e:
                print(f"[AUD][D] Erro geral na ação: {e}")
                return False
        
        # Processar cada bucket
        resultados['A'] = processar_bucket(A, 'A', acao_bucket_a)
        resultados['B'] = processar_bucket(B, 'B', acao_bucket_b)
        resultados['C'] = processar_bucket(C, 'C', acao_bucket_c)
        resultados['D'] = processar_bucket(D, 'D', acao_bucket_d)
        
        # ===== ETAPA 5: MARCAR PROCESSOS EXECUTADOS =====
        print("[AUD] 5. Marcando processos executados...")
        
        processos_sucesso = 0
        processos_erro = 0
        
        # Função auxiliar para extrair resultados
        def processar_resultados_bucket(bucket_resultados, bucket_nome):
            nonlocal processos_sucesso, processos_erro
            for res in bucket_resultados:
                numero = res.get('numero')
                ok = res.get('ok', False)
                if ok:
                    marcar_processo_executado_aud(numero, progresso, "SUCESSO", f"Bucket {bucket_nome}")
                    processos_sucesso += 1
                else:
                    marcar_processo_executado_aud(numero, progresso, "ERRO", f"Bucket {bucket_nome}: {res.get('msg', '')}")
                    processos_erro += 1
        
        processar_resultados_bucket(resultados['A'], 'A')
        processar_resultados_bucket(resultados['B'], 'B')
        processar_resultados_bucket(resultados['C'], 'C')
        processar_resultados_bucket(resultados['D'], 'D')
        
        # ===== ETAPA 6: RELATÓRIO FINAL =====
        print("[AUD] ========== RELATÓRIO FINAL ==========")
        print(f"[AUD] Total de processos na lista: {len(lista_processos)}")
        print(f"[AUD] Processos de Triagem Inicial: {total_processos_triagem}")
        print(f"[AUD] Processos executados com sucesso: {processos_sucesso}")
        print(f"[AUD] Processos com erro: {processos_erro}")
        print(f"[AUD] Taxa de sucesso: {(processos_sucesso/total_processos_triagem*100):.1f}%" if total_processos_triagem else "N/A")
        print("[AUD] ====================================")
        
        return {
            "sucesso": True,
            "processos_executados": processos_sucesso,
            "processos_erro": processos_erro,
            "total_na_lista": len(lista_processos),
            "resultados_detalhados": resultados
        }
        
    except Exception as e:
        print(f"[AUD] ❌ Erro geral na indexação: {e}")
        traceback.print_exc()
        return {"sucesso": False, "erro": str(e)}


def criar_driver_e_logar(driver: Optional[WebDriver] = None, log: bool = True) -> Optional[WebDriver]:
    """Cria um driver (se driver for None) e executa login usando Fix.utils.
    Retorna o driver pronto ou None em caso de falha."""
    if driver is not None:
        if log:
            print("[AUD] Usando driver fornecido")
        return driver

    try:
        if log:
            print("[AUD] Criando driver e executando login (Fix.utils)")
        from Fix.utils import driver_pc, login_cpf

        drv = driver_pc()
        if not drv:
            print("[AUD] Falha ao criar driver")
            return None

        ok = False
        try:
            ok = login_cpf(drv)
        except Exception as e:
            print(f"[AUD] Erro ao executar login_cpf: {e}")
            ok = False

        if not ok:
            try:
                drv.quit()
            except Exception:
                pass
            print("[AUD] Login falhou")
            return None

        return drv

    except Exception as e:
        print(f"[AUD] Exceção ao criar/logar driver: {e}")
        traceback.print_exc()
        return None


def coletar_lista_processos(driver: WebDriver) -> List[Dict[str, Any]]:
    """Coleta todos os processos visíveis na lista e extrai campos relevantes.

    Retorna lista de dicionários com chaves: numero (string sem formatação),
    tipo (ATOrd/ATSum/ACum/HTE/ou ''), tem_100 (bool), audiencia (str or ''),
    responsavel (str or ''), row_index (int).
    """
    js = r"""
    var linhas = Array.from(document.querySelectorAll('tbody tr.tr-class'));
    var resultado = [];
    linhas.forEach(function(tr, idx){
        try {
            var numero = '';
            // Extrair número do processo - baseado no HTML real do aud.js
            var linkProcesso = tr.querySelector('pje-descricao-processo a, a[role="link"]');
            if (linkProcesso) {
                numero = (linkProcesso.innerText || linkProcesso.textContent || '').trim();
            }

            // Extrair tipo (ATOrd/ATSum/ACum/HTE) - baseado no HTML real
            var tipo = '';
            // Tentar múltiplas abordagens para encontrar o tipo
            var spansTipo = tr.querySelectorAll('pje-descricao-processo span.align-end.ng-star-inserted');
            for (var i = 0; i < spansTipo.length; i++) {
                var texto = (spansTipo[i].innerText || spansTipo[i].textContent || '').trim();
                if (texto && (texto.includes('ATOrd') || texto.includes('ATSum') || texto.includes('ACum') || texto.includes('Accum') || texto.includes('HTE'))) {
                    tipo = texto;
                    console.log('Tipo encontrado:', tipo);
                    break;
                }
            }

            // Fallback: tentar pegar o primeiro span align-end que não seja vazio
            if (!tipo) {
                var primeiroSpan = tr.querySelector('pje-descricao-processo span.align-end.ng-star-inserted');
                if (primeiroSpan) {
                    tipo = (primeiroSpan.innerText || primeiroSpan.textContent || '').trim();
                    console.log('Tipo via fallback:', tipo);
                }
            }

            // 100% digital - baseado no HTML real
            var tem100 = false;
            var icone100 = tr.querySelector('.texto-icone-juizo-digital');
            if (icone100 && (icone100.innerText || icone100.textContent || '').includes('100')) {
                tem100 = true;
            }

            // Audiência - pegar toda a coluna principal
            var aud = '';
            var tdPrincipal = tr.querySelector('td:nth-child(2)');
            if (tdPrincipal) {
                aud = (tdPrincipal.innerText || tdPrincipal.textContent || '').trim();
            }

            // Responsável - baseado no HTML real
            var resp = '';
            var inputResp = tr.querySelector('pje-gigs-cadastro-responsavel input, input[aria-label*="Respons"]');
            if (inputResp) {
                resp = (inputResp.value || '').trim();
            }

            // Extrair tarefa para debug
            var tarefa = '';
            var tarefaElement = tr.querySelector('a[role="button"] span, span.link, .link span');
            if (tarefaElement) {
                tarefa = (tarefaElement.innerText || tarefaElement.textContent || '').trim();
            }

            // Normalize numero removing non-digits
            var numero_clean = numero.replace(/[^0-9]/g,'');

            resultado.push({
                numero: numero_clean || numero,
                numero_raw: numero,
                tipo: tipo,
                tem_100: tem100,
                audiencia: aud,
                responsavel: resp,
                tarefa: tarefa,
                row_index: idx
            });
        } catch(e) {
            console.log('Erro na linha ' + idx + ': ' + e.message);
            resultado.push({
                numero: null,
                numero_raw: '',
                tipo: '',
                tem_100: false,
                audiencia: '',
                responsavel: '',
                tarefa: '',
                row_index: idx
            });
        }
    });
    return resultado;
    """

    try:
        dados = driver.execute_script(js)
        if not dados:
            print("[AUD] Nenhuma linha retornada pela coleta JS")
            return []
        print(f"[AUD] Coletados {len(dados)} processos da página (raw)")
        return dados
    except Exception as e:
        print(f"[AUD] Erro ao executar JS de coleta: {e}")
        traceback.print_exc()
        return []


def agrupar_em_buckets(lista: List[Dict[str, Any]]):
    """Agrupa em quatro buckets A, B, C, D conforme regra do usuário.

    Primeiro filtra apenas processos da tarefa "Triagem Inicial".
    Depois filtra apenas processos Atord, Atsum, Accum ou HTE.
    A: sem audiência
    B: tem audiência + tem 100%
    C: tem audiência + nao tem 100%
    D: HTE
    """
    # Primeiro filtrar apenas processos da Triagem Inicial
    processos_triagem = []
    for item in lista:
        tarefa = (item.get('tarefa') or '').strip()
        if 'Triagem Inicial' in tarefa:
            processos_triagem.append(item)
        else:
            print(f"[AUD] Pulando processo {item.get('numero')} - tarefa: '{tarefa}'")

    print(f"[AUD] Filtrados {len(processos_triagem)} processos da Triagem Inicial de {len(lista)} total")

    # Segundo filtro: apenas Atord, Atsum, Accum ou HTE
    processos_validos = []
    tipos_validos = ['ATORD', 'ATSUM', 'ACUM', 'HTE']
    
    for item in processos_triagem:
        tipo = (item.get('tipo') or '').upper().strip()
        if tipo in tipos_validos:
            processos_validos.append(item)
        else:
            print(f"[AUD] Pulando processo {item.get('numero')} - tipo '{tipo}' não é Atord/Atsum/Accum/HTE")

    print(f"[AUD] Filtrados {len(processos_validos)} processos válidos (Atord/Atsum/Accum/HTE) de {len(processos_triagem)} da triagem")

    A = []
    B = []
    C = []
    D = []

    for item in processos_validos:
        tipo = (item.get('tipo') or '').upper().strip()
        if tipo == 'HTE':
            D.append(item)
            continue
            
        audiencia = (item.get('audiencia') or '').strip()
        tem_aud = False

        # Verificar se tem audiência: presença de "Audiência em:" na string
        if isinstance(audiencia, str) and 'Audiência em:' in audiencia:
            tem_aud = True

        if not tem_aud:
            A.append(item)
        else:
            if item.get('tem_100', False):
                B.append(item)
            else:
                C.append(item)

    print(f"[AUD] Buckets: A={len(A)} (sem audiência) B={len(B)} (com audiência + 100%) C={len(C)} (com audiência + sem 100%) D={len(D)} (HTE)")
    return A, B, C, D


def reindexar_linha_js(driver, numero_processo):
    """
    Reindexa linha usando JavaScript para encontrar o processo pelo número.
    Similar à lógica de coletar_lista_processos, mas retorna o elemento da linha.
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo a procurar (com ou sem formatação)
    
    Returns:
        WebElement da linha ou None se não encontrado
    """
    try:
        # JavaScript para encontrar a linha que contém o processo
        js = r"""
        var numero_procurado = arguments[0];
        var linhas = Array.from(document.querySelectorAll('tbody tr.tr-class'));
        
        for (var i = 0; i < linhas.length; i++) {
            try {
                var tr = linhas[i];
                
                // Extrair número do processo da mesma forma que coletar_lista_processos
                var numero = '';
                var linkProcesso = tr.querySelector('pje-descricao-processo a, a[role="link"]');
                if (linkProcesso) {
                    numero = (linkProcesso.innerText || linkProcesso.textContent || '').trim();
                }
                
                // Normalizar número removendo não-dígitos
                var numero_clean = numero.replace(/[^0-9]/g,'');
                
                // Verificar se corresponde (comparar números limpos)
                if (numero_clean === numero_procurado || numero === numero_procurado) {
                    // Retornar índice da linha encontrada
                    return i;
                }
            } catch(e) {
                console.log('Erro ao verificar linha ' + i + ': ' + e.message);
                continue;
            }
        }
        
        // Não encontrou
        return -1;
        """
        
        # Executar JavaScript para encontrar o índice da linha
        linha_index = driver.execute_script(js, numero_processo)
        
        if linha_index >= 0:
            print(f"[AUD] ✅ Processo {numero_processo} encontrado na linha {linha_index}")
            
            # Agora obter o elemento da linha usando Selenium
            from selenium.webdriver.common.by import By
            linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
            
            if linha_index < len(linhas):
                return linhas[linha_index]
            else:
                print(f"[AUD] ❌ Índice {linha_index} fora do range (total: {len(linhas)})")
                return None
        else:
            print(f"[AUD] ❌ Processo {numero_processo} não encontrado na lista atual")
            return None
            
    except Exception as e:
        print(f"[AUD] ❌ Erro ao reindexar linha para {numero_processo}: {e}")
        return None


def _abrir_nova_aba(driver: WebDriver, url: str, aba_origem: str, url_fragmento: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    """Abre URL em nova aba e retorna handle da nova aba (opcionalmente filtrando por fragmento)."""
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                abas = driver.window_handles
                for h in abas:
                    if h == aba_origem:
                        continue
                    driver.switch_to.window(h)
                    if not url_fragmento:
                        return h
                    try:
                        if url_fragmento in (driver.current_url or ""):
                            return h
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(0.2)
        return trocar_para_nova_aba(driver, aba_origem)
    except Exception as e:
        print(f"[AUD] ❌ Erro ao abrir nova aba: {e}")
        return None


def desmarcar_100(driver: WebDriver, id_processo: str) -> Optional[str]:
    """Desmarca 100% digital na aba /retificar e mantém a aba aberta."""
    aba_detalhe = driver.current_window_handle
    url_retificar = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/retificar"

    nova_aba = _abrir_nova_aba(driver, url_retificar, aba_detalhe, url_fragmento="/retificar")
    if not nova_aba:
        return None

    try:
        step_carac = esperar_elemento(
            driver,
            "mat-step-header[aria-posinset='4']",
            by=By.CSS_SELECTOR,
            timeout=15
        )
        if not step_carac:
            raise Exception("Step 'Características' não encontrado")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", step_carac)
        safe_click(driver, step_carac)
        time.sleep(1)

        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10
        )
        if not toggle:
            raise Exception("Toggle Juízo 100% digital não encontrado")

        if "mat-checked" in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            esperar_elemento(
                driver,
                "pje-modal-juizo-digital",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            modal = driver.find_element(By.CSS_SELECTOR, "pje-modal-juizo-digital")
            if "Juízo 100% digital" in (modal.text or ""):
                botoes = modal.find_elements(By.CSS_SELECTOR, "button")
                if len(botoes) >= 4:
                    safe_click(driver, botoes[3])
                elif botoes:
                    safe_click(driver, botoes[0])
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital']:not(.mat-checked)",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            time.sleep(1)
        return nova_aba
    except Exception as e:
        print(f"[AUD] ❌ Erro ao desmarcar 100%: {e}")
        return nova_aba


def remarcar_100_pos_aud(driver: WebDriver):
    """Remarcar 100% após marcar audiência (apenas toggle + Sim)."""
    try:
        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10
        )
        if not toggle:
            raise Exception("Toggle Juízo 100% digital não encontrado")

        if "mat-checked" not in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            esperar_elemento(
                driver,
                "pje-modal-juizo-digital",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            modal = driver.find_element(By.CSS_SELECTOR, "pje-modal-juizo-digital")
            if "Juízo 100% digital" in (modal.text or ""):
                botoes = modal.find_elements(By.CSS_SELECTOR, "button")
                if botoes:
                    safe_click(driver, botoes[0])
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital'].mat-checked",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            time.sleep(1)
    except Exception as e:
        print(f"[AUD] ❌ Erro ao remarcar 100%: {e}")


def marcar_aud(driver: WebDriver, numero_processo: str, rito: str, aba_retorno: str):
    """Marca audiência na pauta e fecha a aba de audiência ao final."""
    aba_origem = driver.current_window_handle
    url_pauta = f"https://pje.trt2.jus.br/pjekz/pauta-audiencias?maisPje=true&numero={numero_processo}&rito={rito}&fase=Conhecimento"
    aba_aud = _abrir_nova_aba(driver, url_pauta, aba_origem, url_fragmento="/pauta-audiencias")
    if not aba_aud:
        return

    sucesso = False
    try:
        esperar_elemento(driver, "mat-card.card-pauta", by=By.CSS_SELECTOR, timeout=15)

        if rito.upper() == 'ATSUM':
            linha = esperar_elemento(
                driver,
                "//tr[.//span[contains(normalize-space(.), 'Una (rito sumaríssimo)')]]",
                by=By.XPATH,
                timeout=10
            )
        else:
            linha = esperar_elemento(
                driver,
                "//tr[.//span[normalize-space(.)='Una'] and not(.//span[contains(normalize-space(.), 'sumar')]) ]",
                by=By.XPATH,
                timeout=10
            )

        if not linha:
            raise Exception("Linha de pauta não encontrada")

        btn_plus = linha.find_element(By.XPATH, ".//button[@aria-label='Designar Audiência'] | .//i[contains(@class,'fa-plus-circle')]/ancestor::button")
        safe_click(driver, btn_plus)

        modal = esperar_elemento(driver, "mat-dialog-container", by=By.CSS_SELECTOR, timeout=10)
        if not modal:
            raise Exception("Modal de audiência não encontrado")

        input_num = modal.find_element(By.CSS_SELECTOR, "input#inputNumeroProcesso")
        valor_atual = (input_num.get_attribute('value') or '').strip()
        if not valor_atual:
            try:
                safe_click(driver, input_num)
                input_num.clear()
                input_num.send_keys(numero_processo)
                driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                    input_num
                )
            except Exception:
                preencher_campo(driver, "#inputNumeroProcesso", numero_processo)
        time.sleep(0.8)
        btn_confirmar = esperar_elemento(
            driver,
            "//mat-dialog-container//button[.//span[normalize-space(.)='Confirmar']]",
            by=By.XPATH,
            timeout=10
        )
        if not btn_confirmar:
            raise Exception("Botão Confirmar não encontrado")
        safe_click(driver, btn_confirmar)
        time.sleep(1)
        modal_confirmado = esperar_elemento(
            driver,
            "//mat-dialog-container//*[self::h4 or self::h3][contains(normalize-space(.), 'Designação Confirmada')]",
            by=By.XPATH,
            timeout=10
        )
        if modal_confirmado:
            btn_fechar = esperar_elemento(
                driver,
                "//mat-dialog-container//button[.//span[normalize-space(.)='Fechar']]",
                by=By.XPATH,
                timeout=10
            )
            if btn_fechar:
                safe_click(driver, btn_fechar)
                time.sleep(0.5)
        sucesso = True
    except Exception as e:
        print(f"[AUD] ❌ Erro ao marcar audiência: {e}")
    finally:
        if sucesso:
            try:
                driver.close()
            except Exception:
                pass
            try:
                if aba_retorno in driver.window_handles:
                    driver.switch_to.window(aba_retorno)
            except Exception:
                pass



def executar_acoes_por_bucket(driver: WebDriver, A: List[Dict[str, Any]], B: List[Dict[str, Any]], C: List[Dict[str, Any]]):
    """Esta função foi substituída pela nova abordagem de indexação e processamento individual.
    Mantida apenas para compatibilidade, mas não deve ser usada."""
    print("[AUD] AVISO: executar_acoes_por_bucket está deprecated. Use indexar_e_processar_lista_aud.")
    return {'A': [], 'B': [], 'C': []}


def run_aud(driver: Optional[WebDriver] = None):
    """Fluxo principal: cria/usa driver, navega para a lista e processa com indexação e buckets.
    Retorna sumário de resultados.
    """
    # ===== CONFIGURAR RECOVERY GLOBAL =====
    from Fix.utils import driver_pc, login_cpf
    configurar_recovery_driver(driver_pc, login_cpf)
    print("[AUD] ✅ Sistema de recuperação automática configurado")
    
    drv = criar_driver_e_logar(driver)
    if not drv:
        print('[AUD] Falha ao obter driver (aborting)')
        return None

    try:
        url = 'https://pje.trt2.jus.br/pjekz/painel/global/10/lista-processos'
        print(f"[AUD] Navegando para {url}")
        drv.get(url)
        time.sleep(3)

        # Usar nova abordagem de indexação e processamento
        resultado = indexar_e_processar_lista_aud(drv)
        
        if resultado.get("sucesso"):
            print('[AUD] Execução finalizada com sucesso!')
            return resultado
        else:
            print(f'[AUD] Execução finalizada com problemas: {resultado.get("erro", "Erro desconhecido")}')
            return resultado

    except Exception as e:
        novo_driver = handle_exception_with_recovery(e, drv, "AUD_RUN")
        if novo_driver:
            drv = novo_driver
            # Tentar continuar ou retornar resultado parcial
        else:
            print(f"[AUD] Erro geral no run_aud: {e}")
            traceback.print_exc()
        return None


if __name__ == '__main__':
    # Execução direta para testes rápidos (requere login automático configurado em driver_config)
    print('[AUD] executando como script')
    resultado = run_aud(None)
    print('[AUD] Resultado do run:', resultado)
