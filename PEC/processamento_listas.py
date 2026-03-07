import logging
logger = logging.getLogger(__name__)

from selenium.webdriver.common.by import By

from .regras import determinar_acoes_por_observacao


def criar_lista_sisbajud(driver):
    """
    Varre a lista de atividades usando a mesma lógica de indexação posterior
    e identifica todos os processos SISBAJUD para processamento agrupado
    """
    try:
        import re
        
        # Usar a mesma lógica de indexação da lista posterior
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        if not linhas:
            return []
        
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
                    continue
                
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
                except:
                    # Fallback: texto direto da célula
                    observacao = celula_observacao.text.lower().strip()
                    try:
                        raw_cell = celula_observacao.get_attribute('innerText') or celula_observacao.text
                    except Exception:
                        raw_cell = celula_observacao.text
                
                if not observacao:
                    continue
                
                # Determinar ações (UMA VEZ AQUI)
                acoes = determinar_acoes_por_observacao(observacao)
                
                # Adicionar à lista se acoes for definida
                if acoes:
                    # Extrair nomes das funções para logging
                    nomes_acoes = [a.__name__ if callable(a) else str(a) for a in acoes]
                    lista_sisbajud.append({
                        'numero_processo': numero_processo,
                        'observacao': observacao,
                        'acoes': acoes,
                        'linha': linha,
                        'linha_index': idx
                    })
                    
            except Exception as e:
                logger.error(f"[SISBAJUD_LISTA]  Erro ao processar linha {idx + 1}: {e}")
                continue
        
        return lista_sisbajud
        
    except Exception as e:
        logger.error(f"[SISBAJUD_LISTA]  Erro ao criar lista SISBAJUD: {e}")
        return []


def executar_lista_sisbajud_por_abas(driver_pje, lista_sisbajud):
    """
    Executa lista de processos SISBAJUD usando abas e driver compartilhado
    """
    try:
        if not lista_sisbajud:
            return []

        from Fix.extracao import reindexar_linha

        resultados = []
        driver_sisbajud = None
        
        # Armazenar aba original da lista
        aba_lista_original = driver_pje.current_window_handle
        
        for idx, item in enumerate(lista_sisbajud, 1):
            numero_processo = item['numero_processo']
            observacao = item['observacao']
            acoes = item.get('acoes', [])
            linha = item['linha']
            linha_index = item['linha_index']

            acao_principal = acoes[0] if acoes else None
            acao_nome = acao_principal.__name__ if callable(acao_principal) else (str(acao_principal) if acao_principal else None)
            
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
                    # Verificar URL atual para detectar acesso negado
                    url_atual = driver_pje.current_url
                    if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                        # Forçar restart do driver - não retornar, levantar exceção
                        raise Exception(f'RESTART_PEC: Acesso negado detectado - driver quebrado: {url_atual}')
                    
                    # Verificar se página tem indicadores de erro de sessão
                    try:
                        body_text = driver_pje.find_element(By.TAG_NAME, 'body').text.lower()
                        if any(termo in body_text for termo in ['acesso negado', 'sessão expirada', 'não autorizado', 'access denied']):
                            raise Exception('RESTART_PEC: Acesso negado detectado no conteúdo da página - driver quebrado')
                    except Exception as body_ex:
                        if 'RESTART_PEC' in str(body_ex):
                            raise  # Propagar se for restart
                        pass  # Ignorar outros erros
                    
                    # Se não é acesso negado, tentar reindexar
                    linha_atual = reindexar_linha(driver_pje, numero_processo)
                    if not linha_atual:
                        continue
                
                # NAVEGAR PARA O PROCESSO ESPECÍFICO (usando mesma lógica da indexação normal)
                from Fix.extracao import abrir_detalhes_processo, trocar_para_nova_aba
                
                # 1. Abrir detalhes do processo
                if not abrir_detalhes_processo(driver_pje, linha_atual):
                    continue
                
                # 2. Trocar para nova aba
                import time
                time.sleep(1)
                nova_aba = trocar_para_nova_aba(driver_pje, aba_lista_original)
                if not nova_aba:
                    continue
                
                # 3. Aguardar carregamento
                time.sleep(2)
                
                aba_aberta_pela_funcao = True
                
                # 4. Extrair dados do processo
                from Fix.extracao import extrair_dados_processo
                dados_processo = extrair_dados_processo(driver_pje)
                
                if not dados_processo:
                    continue
                
                # 5. Executar ação SISBAJUD apropriada
                
                # Inicializar driver SISBAJUD apenas uma vez
                if driver_sisbajud is None:
                    from SISB.core import iniciar_sisbajud
                    driver_sisbajud = iniciar_sisbajud(driver_pje=driver_pje)
                    
                    if not driver_sisbajud:
                        break
                
                # Executar a ação apropriada baseada no tipo
                if acao_nome == "processar_ordem_sisbajud":
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
                        
                elif acao_nome and "minuta_bloqueio" in acao_nome:
                    # Executar minuta_bloqueio_sisbajud
                    from SISB.core import minuta_bloqueio
                    
                    # Detectar prazo na observação (padrão 30 dias, 60 se especificado)
                    prazo_dias = 30  # Padrão
                    observacao_lower = observacao.lower() if observacao else ""
                    
                    if "60" in observacao_lower:
                        prazo_dias = 60
                    
                    resultado = minuta_bloqueio(
                        driver=driver_sisbajud,
                        dados_processo=dados_processo, 
                        driver_pje=driver_pje,
                        log=True
                    )
                    
                    if resultado and resultado.get('status') == 'sucesso':
                        sucesso = True
                        # Executar juntada do relatório SISBAJUD no PJe
                        from PEC.anexos import consulta_wrapper
                        
                        resultado_wrapper = consulta_wrapper(
                            driver=driver_pje,
                            numero_processo=numero_processo,
                            debug=True
                        )
                        
                else:
                    sucesso = False
            
            except Exception as e:
                logger.error(f"[SISBAJUD_EXEC]  Erro ao processar {numero_processo}: {e}")
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
            try:
                driver_sisbajud.quit()
            except:
                pass

        return resultados
        
    except Exception as e:
        logger.error(f"[SISBAJUD_EXEC]  Erro geral na execução SISBAJUD: {e}")
        import traceback
        traceback.print_exc()
        return []


def criar_lista_resto(driver, filtros_observacao):
    """
    Varre a lista de atividades e identifica todos os processos do resto (não-SISBAJUD)
    usando exatamente a mesma lógica da criar_lista_sisbajud
    """
    try:
        import re
        
        # Usar a mesma lógica de indexação da lista SISBAJUD
        linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
        if not linhas:
            return []
        
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
                    continue
                
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
                
                # Determinar ações (UMA VEZ AQUI)
                acoes = determinar_acoes_por_observacao(observacao)
                
                # Adicionar à lista se acoes for definida
                if acoes:
                    nomes_acoes = [a.__name__ if callable(a) else str(a) for a in acoes]
                    lista_resto.append({
                        'numero_processo': numero_processo,
                        'observacao': observacao,
                        'acoes': acoes,
                        'linha': linha,
                        'linha_index': idx
                    })
                    
            except Exception as e:
                logger.error(f"[RESTO_LISTA]  Erro ao processar linha {idx + 1}: {e}")
                continue
        
        return lista_resto
        
    except Exception as e:
        logger.error(f"[RESTO_LISTA]  Erro ao criar lista do resto: {e}")
        return []
