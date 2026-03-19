"""
SISB/batch.py - Processamento em lote de operações SISBAJUD

Este módulo fornece funções para processar múltiplos processos SISBAJUD
usando um único driver compartilhado, otimizando o tempo de execução.
"""

import time
from typing import Any, Dict, List, Optional, Callable

# URL base para navegação entre processos
URL_MINUTA = "https://sisbajud.pdpj.jus.br/minuta"


def processar_lote_sisbajud(
    driver_pje: Any,
    processos: List[Dict[str, Any]],
    progresso: Dict[str, Any],
    fn_reindexar_linha: Callable,
    fn_abrir_detalhes: Callable,
    fn_trocar_aba: Callable,
    fn_ja_executado: Callable,
    fn_marcar_executado: Callable,
    log: bool = True
) -> Dict[str, int]:
    """
    Processa um lote de processos SISBAJUD com driver compartilhado.
    
    Separa processos em 'teimosinha' (minuta) e 'resultado' (processar ordens),
    cria um único driver SISBAJUD e processa todos sequencialmente.
    
    Args:
        driver_pje: WebDriver do PJE
        processos: Lista de processos com {numero, observacao, linha, ...}
        progresso: Dicionário de progresso
        fn_reindexar_linha: Função para reindexar linha na tabela
        fn_abrir_detalhes: Função para abrir detalhes do processo
        fn_trocar_aba: Função para trocar para nova aba
        fn_ja_executado: Função para verificar se já foi executado
        fn_marcar_executado: Função para marcar como executado
        log: Se deve fazer log
        
    Returns:
        dict: {'sucesso': int, 'erro': int}
    """
    from .core import iniciar_sisbajud, minuta_bloqueio, processar_ordem_sisbajud
    from Fix.extracao import extrair_dados_processo
    
    resultados = {'sucesso': 0, 'erro': 0}
    
    if not processos:
        if log:
            print("[SISBAJUD_LOTE] ⚠️ Nenhum processo para processar")
        return resultados
    
    # ===== ETAPA 1: Separar processos por tipo (baseado na PRIMEIRA ação) =====
    processos_teimosinha = []
    processos_resultado = []
    
    for proc in processos:
        # As ações já foram determinadas por PEC/regras.py
        acoes = proc.get('acoes', [])
        
        if not acoes:
            # Fallback: se por algum motivo não veio com ações, ignorar
            continue
        
        # Usar PRIMEIRA ação para separar
        primeira_acao = acoes[0]
        acao_nome = primeira_acao.__name__ if callable(primeira_acao) else str(primeira_acao)
        
        # Classificar baseado na primeira ação
        if 'minuta_bloqueio' in acao_nome:
            # minuta_bloqueio ou minuta_bloqueio_60
            processos_teimosinha.append(proc)
        elif 'processar_ordem' in acao_nome:
            processos_resultado.append(proc)
        else:
            # Default
            processos_teimosinha.append(proc)
    
    if log:
        print(f"[SISBAJUD] Separação: {len(processos_teimosinha)} teimosinha (minuta) | {len(processos_resultado)} resultado (processar)")
    
    # ===== ETAPA 2: Armazenar aba da lista e preparar driver SISBAJUD (será criado no primeiro processo) =====
    driver_sisbajud = None
    aba_lista_pje = driver_pje.current_window_handle
    
    try:
        
        # ===== ETAPA 3: Processar todos TEIMOSINHA =====
        if processos_teimosinha:
            driver_sisbajud, res = _processar_grupo(
                driver_pje=driver_pje,
                driver_sisbajud=driver_sisbajud,
                processos=processos_teimosinha,
                tipo='TEIMOSINHA',
                fn_executar=lambda d_sisb, dados, d_pje: minuta_bloqueio(d_sisb, dados_processo=dados, driver_pje=d_pje, log=log, fechar_driver=False),
                progresso=progresso,
                aba_lista_pje=aba_lista_pje,
                fn_reindexar_linha=fn_reindexar_linha,
                fn_abrir_detalhes=fn_abrir_detalhes,
                fn_trocar_aba=fn_trocar_aba,
                fn_ja_executado=fn_ja_executado,
                fn_marcar_executado=fn_marcar_executado,
                log=log
            )
            resultados['sucesso'] += res['sucesso']
            resultados['erro'] += res['erro']
        
        # ===== ETAPA 4: Processar todos RESULTADO =====
        if processos_resultado:
            driver_sisbajud, res = _processar_grupo(
                driver_pje=driver_pje,
                driver_sisbajud=driver_sisbajud,
                processos=processos_resultado,
                tipo='RESULTADO',
                fn_executar=lambda d_sisb, dados, d_pje: processar_ordem_sisbajud(d_sisb, dados_processo=dados, driver_pje=d_pje, log=log, fechar_driver=False),
                progresso=progresso,
                aba_lista_pje=aba_lista_pje,
                fn_reindexar_linha=fn_reindexar_linha,
                fn_abrir_detalhes=fn_abrir_detalhes,
                fn_trocar_aba=fn_trocar_aba,
                fn_ja_executado=fn_ja_executado,
                fn_marcar_executado=fn_marcar_executado,
                log=log
            )
            resultados['sucesso'] += res['sucesso']
            resultados['erro'] += res['erro']
        
    except Exception as e:
        if log:
            print(f"[SISBAJUD] ❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # ===== ETAPA 5: Fechar driver SISBAJUD =====
        if driver_sisbajud:
            try:
                driver_sisbajud.quit()
                if log:
                    print("\n[SISBAJUD] ✅ Driver fechado")
            except:
                pass
    
    if log:
        print(f"[SISBAJUD]  Total: {resultados['sucesso']} sucesso | {resultados['erro']} erros\n")
    
    return resultados


def _processar_grupo(
    driver_pje: Any,
    driver_sisbajud: Any,
    processos: List[Dict[str, Any]],
    tipo: str,
    fn_executar: Callable,
    progresso: Dict[str, Any],
    aba_lista_pje: str,
    fn_reindexar_linha: Callable,
    fn_abrir_detalhes: Callable,
    fn_trocar_aba: Callable,
    fn_ja_executado: Callable,
    fn_marcar_executado: Callable,
    log: bool = True
) -> Dict[str, int]:
    """
    Processa um grupo de processos do mesmo tipo.
    
    Args:
        driver_pje: WebDriver do PJE
        driver_sisbajud: WebDriver do SISBAJUD (compartilhado)
        processos: Lista de processos
        tipo: 'TEIMOSINHA' ou 'RESULTADO'
        fn_executar: Função a executar para cada processo
        progresso: Dicionário de progresso
        aba_lista_pje: Handle da aba da lista PJE
        fn_*: Funções auxiliares do PEC
        log: Se deve fazer log
        
    Returns:
        dict: {'sucesso': int, 'erro': int}
    """
    from Fix.extracao import extrair_dados_processo
    
    resultados = {'sucesso': 0, 'erro': 0}
    
    if log:
        print(f"\n[SISBAJUD]  {tipo}: processando {len(processos)} processos...")
    
    for idx, proc in enumerate(processos, 1):
        numero_processo = proc.get('numero')
        
        if log:
            print(f"\n[SISBAJUD] [{idx}/{len(processos)}] {numero_processo}")
        
        try:
            # Verificar se já foi executado
            if fn_ja_executado(numero_processo, progresso):
                if log:
                    print(f"  ⏭️ Já executado, pulando")
                continue
            
            # Reindexar linha se necessário
            linha = proc.get('linha')
            try:
                linha.is_displayed()
            except:
                linha = fn_reindexar_linha(driver_pje, numero_processo)
            
            if not linha:
                # Verificar se é acesso negado
                try:
                    url_atual = driver_pje.current_url
                    if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                        if log:
                            print(f"  ⚠️ Acesso negado - pulando")
                        fn_marcar_executado(numero_processo, progresso)
                        resultados['erro'] += 1
                        continue
                except:
                    pass
                
                if log:
                    print(f"  ❌ Linha não encontrada")
                resultados['erro'] += 1
                continue
            
            # Abrir detalhes do processo no PJE
            if not fn_abrir_detalhes(driver_pje, linha):
                # Verificar se é acesso negado
                try:
                    url_atual = driver_pje.current_url
                    if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                        if log:
                            print(f"  ⚠️ Acesso negado ao abrir - pulando")
                        fn_marcar_executado(numero_processo, progresso)
                        resultados['erro'] += 1
                        continue
                except:
                    pass
                
                if log:
                    print(f"  ❌ Não foi possível abrir")
                resultados['erro'] += 1
                continue
            
            time.sleep(1)
            nova_aba = fn_trocar_aba(driver_pje, aba_lista_pje)
            if not nova_aba:
                if log:
                    print(f"  ❌ Nova aba não abriu")
                resultados['erro'] += 1
                continue
            
            time.sleep(2)
            
            # Extrair dados do processo
            dados_processo = extrair_dados_processo(driver_pje)
            if not dados_processo:
                # Verificar se é acesso negado
                try:
                    url_atual = driver_pje.current_url
                    if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                        if log:
                            print(f"[SISBAJUD_LOTE] ⚠️ ACESSO NEGADO detectado para {numero_processo}")
                            print(f"[SISBAJUD_LOTE]  Lançando exceção para reiniciar driver...")
                        
                        # Lançar exceção para forçar reinício do driver
                        raise Exception(f"RESTART_SISB: ACESSO_NEGADO detectado para {numero_processo}")
                except Exception as e:
                    # Se a exceção é de acesso negado, propagar
                    if "RESTART_SISB" in str(e):
                        raise
                    # Outros erros, apenas continuar
                    pass
                
                if log:
                    print(f"[SISBAJUD_LOTE] ❌ Falha ao extrair dados de {numero_processo}")
                
                # FECHAR TODAS AS ABAS DO PJE EXCETO A LISTA
                try:
                    if aba_lista_pje in driver_pje.window_handles:
                        driver_pje.switch_to.window(aba_lista_pje)
                        
                        for handle in list(driver_pje.window_handles):
                            if handle != aba_lista_pje:
                                try:
                                    driver_pje.switch_to.window(handle)
                                    driver_pje.close()
                                except:
                                    pass
                        
                        driver_pje.switch_to.window(aba_lista_pje)
                except:
                    pass
                
                resultados['erro'] += 1
                continue
            
            # ===== VERIFICAR VALOR DE BLOQUEIO ANTES DE CRIAR DRIVER SISBAJUD =====
            divida = dados_processo.get('divida', {})
            valor = divida.get('valor')
            
            if not valor:
                if log:
                    print(f'[SISBAJUD_LOTE] ⚠️ {numero_processo} sem valor de bloqueio - criando GIGS Bruna Atualização')
                
                # Criar GIGS Bruna Atualização (não marca como executado - reprocessar depois)
                try:
                    from Fix.extracao import criar_gigs
                    criar_gigs(driver_pje, 'Bruna Atualização', log=log)
                    if log:
                        print(f'[SISBAJUD_LOTE] ✅ GIGS Bruna Atualização criado para {numero_processo} (não marcado como executado)')
                    
                    # FECHAR TODAS AS ABAS DO PJE EXCETO A LISTA
                    try:
                        if aba_lista_pje in driver_pje.window_handles:
                            driver_pje.switch_to.window(aba_lista_pje)
                            
                            # Fechar todas as outras abas
                            for handle in list(driver_pje.window_handles):
                                if handle != aba_lista_pje:
                                    try:
                                        driver_pje.switch_to.window(handle)
                                        driver_pje.close()
                                    except:
                                        pass
                            
                            # Garantir que estamos na lista
                            driver_pje.switch_to.window(aba_lista_pje)
                    except:
                        pass
                    
                    # Contar como sucesso (GIGS criado)
                    resultados['sucesso'] += 1
                    continue
                    
                except Exception as e:
                    if log:
                        print(f'[SISBAJUD_LOTE] ❌ Erro ao criar GIGS para {numero_processo}: {e}')
                    
                    # FECHAR TODAS AS ABAS DO PJE EXCETO A LISTA
                    try:
                        if aba_lista_pje in driver_pje.window_handles:
                            driver_pje.switch_to.window(aba_lista_pje)
                            
                            for handle in list(driver_pje.window_handles):
                                if handle != aba_lista_pje:
                                    try:
                                        driver_pje.switch_to.window(handle)
                                        driver_pje.close()
                                    except:
                                        pass
                            
                            driver_pje.switch_to.window(aba_lista_pje)
                    except:
                        pass
                    
                    resultados['erro'] += 1
                    continue
            
            if log:
                print(f'[SISBAJUD_LOTE] ✅ {numero_processo} tem valor {valor} - prosseguindo com SISBAJUD')
            
            # ===== CRIAR DRIVER SISBAJUD NO PRIMEIRO PROCESSO (SÓ SE HOUVER VALOR) =====
            if driver_sisbajud is None:
                if log:
                    print("[SISBAJUD_LOTE]  Iniciando driver SISBAJUD compartilhado (primeiro processo)...")
                
                from .core import iniciar_sisbajud
                driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje, extrair_dados=False)
                
                if not driver_sisbajud:
                    if log:
                        print("[SISBAJUD_LOTE] ❌ Falha ao iniciar driver SISBAJUD")
                    
                    # FECHAR TODAS AS ABAS DO PJE EXCETO A LISTA
                    try:
                        if aba_lista_pje in driver_pje.window_handles:
                            driver_pje.switch_to.window(aba_lista_pje)
                            
                            for handle in list(driver_pje.window_handles):
                                if handle != aba_lista_pje:
                                    try:
                                        driver_pje.switch_to.window(handle)
                                        driver_pje.close()
                                    except:
                                        pass
                            
                            driver_pje.switch_to.window(aba_lista_pje)
                    except:
                        pass
                    
                    resultados['erro'] += 1
                    continue
                
                if log:
                    print("[SISBAJUD_LOTE] ✅ Driver SISBAJUD iniciado")
            
            # Navegar para /minuta no SISBAJUD antes de executar ações
            driver_sisbajud.get(URL_MINUTA)
            time.sleep(1)
            
            # Executar TODAS AS AÇÕES determinadas para este processo
            acoes = proc.get('acoes', [])
            
            if acoes:
                for acao in acoes:
                    if callable(acao):
                        acao_nome = acao.__name__ if hasattr(acao, '__name__') else str(acao)
                        if log:
                            print(f"   Executando: {acao_nome}")
                        
                        # Executar ação (minuta_bloqueio, minuta_bloqueio_60, processar_ordem, etc)
                        # Cada função sabe sua assinatura correta
                        resultado = acao(driver=driver_sisbajud, dados_processo=dados_processo, driver_pje=driver_pje, log=log, fechar_driver=False)
                    else:
                        if log:
                            print(f"  ⚠️ Ação não é callable: {acao}")
                        continue
            else:
                # Fallback para fn_executar se não tiver ações (compatibilidade)
                if log:
                    print(f"  ⚠️ Nenhuma ação determinada, usando fn_executar")
                resultado = fn_executar(driver_sisbajud, dados_processo, driver_pje)
            
            # FECHAR TODAS AS ABAS DO PJE EXCETO A LISTA
            # (Evita que abas remanescentes causem confusão entre processos)
            try:
                # Voltar para lista primeiro
                if aba_lista_pje in driver_pje.window_handles:
                    driver_pje.switch_to.window(aba_lista_pje)
                    
                    # Fechar todas as outras abas
                    for handle in list(driver_pje.window_handles):
                        if handle != aba_lista_pje:
                            try:
                                driver_pje.switch_to.window(handle)
                                driver_pje.close()
                            except:
                                pass
                    
                    # Garantir que estamos na lista
                    driver_pje.switch_to.window(aba_lista_pje)
            except Exception as e:
                if log:
                    print(f"  ⚠️ Erro ao fechar abas: {e}")
                try:
                    driver_pje.switch_to.window(aba_lista_pje)
                except:
                    pass
            
            # Avaliar resultado
            sucesso = False
            if isinstance(resultado, dict):
                sucesso = resultado.get('status') == 'concluido'
            elif resultado:
                sucesso = True
            
            if sucesso:
                pass  # Continuar fluxo normal
            
            # FECHAR TODAS AS ABAS DO PJE EXCETO A LISTA (mesmo em caso de erro)
            try:
                if aba_lista_pje in driver_pje.window_handles:
                    driver_pje.switch_to.window(aba_lista_pje)
                    
                    for handle in list(driver_pje.window_handles):
                        if handle != aba_lista_pje:
                            try:
                                driver_pje.switch_to.window(handle)
                                driver_pje.close()
                            except:
                                pass
                    
                fn_marcar_executado(numero_processo, progresso)
            except Exception as e:
                if log:
                    print(f"  ⚠️ Erro ao fechar abas: {e}")
            
            if log:
                print(f"  ✅ Concluído")
            else:
                resultados['erro'] += 1
                if log:
                    print(f"  ❌ Falha")
                    
        except Exception as e:
            if log:
                print(f"  ❌ Erro: {e}")
            resultados['erro'] += 1
            try:
                driver_pje.switch_to.window(aba_lista_pje)
            except:
                pass
    
    return driver_sisbajud, resultados
