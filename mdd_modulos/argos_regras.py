"""
Módulo responsável pelas regras de negócio específicas do fluxo Argos.

Responsabilidades:
- Aplicação de regras baseadas em SISBAJUD
- Lógica de prioridades e precedência
- Criação de lembretes
- Execução de atos judiciais

Funções extraídas do m1.py:
- aplicar_regras_argos()
- lembrete_bloq()
"""

import re
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from Fix import safe_click, wait_for_visible, sleep, extrair_documento, extrair_dados_processo
from atos import ato_bloq, ato_meios, ato_termoS, pec_idpj, ato_meiosub
from p2 import checar_prox

def lembrete_bloq(driver, debug=False):
    """
    Cria lembrete de bloqueio com título "Bloqueio pendente" e conteúdo "processar após IDPJ".
    
    Args:
        driver: Instância do WebDriver
        debug (bool): Se True, imprime logs de debug
    """
    try:
        if debug:
            print('[ARGOS][LEMBRETE] Criando lembrete de bloqueio...')
            
        # 1. Clique no menu (fa-bars)
        menu_clicked = safe_click(driver, '.fa-bars', log=debug)
        if not menu_clicked and debug:
            print('[ARGOS][LEMBRETE] Falha ao clicar no menu')
        sleep(1000)  # Nova função sleep que usa milissegundos
        
        # 2. Clique no ícone de lembrete (fa thumbtack)
        lembrete_selector = '.lista-itens-menu > li:nth-child(16) > pje-icone-post-it:nth-child(1) > li:nth-child(1) > button:nth-child(1)'
        lembrete_clicked = safe_click(driver, lembrete_selector, log=debug)
        if not lembrete_clicked and debug:
            print('[ARGOS][LEMBRETE] Falha ao clicar no ícone de lembrete')
        sleep(1000)
        
        # 3. Foco no conteúdo do diálogo
        dialog_clicked = safe_click(driver, '.mat-dialog-content', log=debug)
        sleep(1000)
        
        # 4. Preenche título
        titulo = wait_for_visible(driver, '#tituloPostit', timeout=5)
        if titulo:
            titulo.clear()
            titulo.send_keys('Bloqueio pendente')
        else:
            print('[ARGOS][LEMBRETE] Campo de título não encontrado')
        
        # 5. Preenche conteúdo
        conteudo = wait_for_visible(driver, '#conteudoPostit', timeout=5)
        if conteudo:
            conteudo.clear()
            conteudo.send_keys('processar após IDPJ')
        else:
            print('[ARGOS][LEMBRETE] Campo de conteúdo não encontrado')
        
        # 6. Clica em salvar
        salvar_clicked = safe_click(driver, 'button.mat-raised-button:nth-child(1)', log=debug)
        if not salvar_clicked and debug:
            print('[ARGOS][LEMBRETE] Falha ao clicar no botão salvar')
        sleep(1000)
        
        if debug:
            print('[ARGOS][LEMBRETE] Lembrete criado com sucesso.')
            
    except Exception as e:
        if debug:
            print(f'[ARGOS][LEMBRETE][ERRO] Falha ao criar lembrete: {e}')
        raise

def aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """
    Aplica as regras específicas do Argos com base no resultado do SISBAJUD, sigilo dos anexos e tipo de documento.
    
    Args:
        driver: Instância do WebDriver
        resultado_sisbajud (str): Resultado do SISBAJUD ('positivo' ou 'negativo')
        sigilo_anexos (dict): Dicionário com status de sigilo dos anexos
        tipo_documento (str): Tipo do documento ('despacho' ou 'decisao')
        texto_documento (str): Texto completo do documento
        debug (bool): Se True, imprime logs de debug
    """
    try:
        regra_aplicada = None
        trecho_relevante = texto_documento if texto_documento else ''
        if debug:
            print(f'[ARGOS][REGRAS] Analisando regras para tipo: {tipo_documento}')
            print(f'[ARGOS][REGRAS] Resultado SISBAJUD: {resultado_sisbajud}')
            print(f'[ARGOS][REGRAS] Sigilo anexos: {sigilo_anexos}')
        
        # NOVA REGRA PRIORIDADE MÁXIMA: Despacho com palavra "ARGOS"
        # Se primeiro documento lido for DESPACHO e contém "ARGOS", aplica regras específicas
        if tipo_documento == 'despacho' and texto_documento and 'argos' in texto_documento.lower():
            regra_aplicada = '[PRIORIDADE MÁXIMA] despacho+argos'
            if debug:
                print('[ARGOS][REGRAS] NOVA REGRA: Despacho com ARGOS detectado - aplicando regras específicas')
            
            if resultado_sisbajud == 'positivo':
                regra_aplicada += ' | sisbajud positivo => ato_bloq'
                if debug:
                    print('[ARGOS][REGRAS] ARGOS: SISBAJUD positivo, executando ato_bloq')
                ato_bloq(driver, debug=debug)
                print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
                return  # Sai da função sem verificar outras regras
            elif resultado_sisbajud == 'negativo':
                # Verifica se há anexos sigilosos
                tem_sigiloso = any(v == 'sim' for v in sigilo_anexos.values()) if sigilo_anexos else False
                if tem_sigiloso:
                    regra_aplicada += ' | sisbajud negativo, com sigiloso => ato_termoS'
                    if debug:
                        print('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo com anexo sigiloso, executando ato_termoS')
                    ato_termoS(driver, debug=debug)
                else:
                    regra_aplicada += ' | sisbajud negativo, sem sigiloso => ato_meios'
                    if debug:
                        print('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo sem anexo sigiloso, executando ato_meios')
                    ato_meios(driver, debug=debug)
                print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
                return  # Sai da função sem verificar outras regras
        
        # Nova regra para detectar "devendo se manifestar" e repetir a análise no próximo documento
        if texto_documento and "devendo se manifestar" in texto_documento.lower():
            if debug:
                print('[ARGOS][REGRAS] Texto "devendo se manifestar" detectado, buscando próximo documento...')
            regra_aplicada = 'devendo se manifestar'
            
            # Busca próximo documento e aplica regras recursivamente
            resultado_proximo = _processar_proximo_documento(driver, resultado_sisbajud, sigilo_anexos, texto_documento, debug)
            if resultado_proximo:
                regra_aplicada += ' | análise repetida em documento seguinte'
                return
        
        # PRIORIDADE ABSOLUTA: Regra "defiro a instauração" com SISBAJUD positivo
        # Esta regra tem precedência sobre qualquer outra, mesmo se outros termos estiverem presentes
        if 'defiro a instauração' in texto_documento.lower() and resultado_sisbajud == 'positivo':
            regra_aplicada = '[PRIORIDADE] decisao+defiro a instauracao+sisbajud positivo'
            if debug:
                print('[ARGOS][REGRAS][PRIORIDADE] ✅ REGRA DE PRECEDÊNCIA: defiro a instauração + SISBAJUD positivo')
                print('[ARGOS][REGRAS][PRIORIDADE] Esta regra prevalece sobre qualquer outra')
            regra_aplicada += ' | lembrete_bloq + pec_idpj [PRECEDENCIA ABSOLUTA]'
            lembrete_bloq(driver, debug=debug)
            pec_idpj(driver, debug=debug)
        # Outras regras de "defiro a instauração" (sem SISBAJUD positivo)
        elif 'defiro a instauração' in texto_documento.lower():
            regra_aplicada = 'decisao+defiro a instauracao'
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como decisão de instauração')
            if resultado_sisbajud == 'negativo':
                regra_aplicada += ' | sisbajud negativo => pec_idpj'
                pec_idpj(driver, debug=debug)
        # 1. Se é despacho com texto específico
        elif tipo_documento == 'despacho' and any(p in texto_documento.lower() for p in ['em que pese a ausência', 'argos']):
            regra_aplicada = 'despacho+argos'
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como despacho com texto específico')
            if resultado_sisbajud == 'negativo' and all(v == 'nao' for v in sigilo_anexos.values()):
                regra_aplicada += ' | sisbajud negativo, nenhum anexo sigiloso => ato_meios'
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo e nenhum anexo sigiloso - chamando ato_meios')
                ato_meios(driver, debug=debug)
            elif resultado_sisbajud == 'negativo' and any(v == 'sim' for v in sigilo_anexos.values()):
                regra_aplicada += ' | sisbajud negativo, anexo sigiloso => ato_termoS'
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo com anexo sigiloso - chamando ato_termoS')
                ato_termoS(driver, debug=debug)
            elif resultado_sisbajud == 'positivo':
                regra_aplicada += ' | sisbajud positivo => ato_bloq'
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD positivo - chamando ato_bloq')
                ato_bloq(driver, debug=debug)
        elif tipo_documento == 'decisao' and 'tendo em vista que' in texto_documento.lower():
            regra_aplicada = 'decisao+tendo em vista que'
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como decisão com texto sobre reclamada')
            
            # Aplica regras baseadas no número de reclamadas
            _aplicar_regras_reclamadas(driver, resultado_sisbajud, sigilo_anexos, debug, regra_aplicada)
        else:
            regra_aplicada = f'nao identificado: {tipo_documento}'
            if debug:
                print(f'[ARGOS][REGRAS] Tipo de documento não identificado: {tipo_documento}')
        
        # Log sempre que chamado, para rastreabilidade
        print(f'[ARGOS][REGRAS][LOG] Regra aplicada: {regra_aplicada}\nTrecho considerado: {trecho_relevante}')
    except Exception as e:
        if debug:
            print(f'[ARGOS][REGRAS][ERRO] Falha ao aplicar regras: {e}')
        raise

def _processar_proximo_documento(driver, resultado_sisbajud, sigilo_anexos, texto_documento, debug):
    """
    Processa o próximo documento quando encontrado texto "devendo se manifestar".
    
    Args:
        driver: Instância do WebDriver
        resultado_sisbajud (str): Resultado do SISBAJUD
        sigilo_anexos (dict): Dicionário com status de sigilo dos anexos
        texto_documento (str): Texto do documento atual
        debug (bool): Se True, imprime logs de debug
    
    Returns:
        bool: True se próximo documento foi processado com sucesso
    """
    try:
        # Buscando itens da timeline para usar com checar_prox
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            if debug:
                print('[ARGOS][REGRAS] Nenhum item encontrado na timeline para análise de próximo documento')
            return False
        
        # Determinando o índice atual do documento
        doc_idx = 0
        for idx, item in enumerate(itens):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento.ativo')
                if link:
                    doc_idx = idx
                    break
            except Exception:
                continue
        
        # Chamando checar_prox para encontrar o próximo documento
        if debug:
            print(f'[ARGOS][REGRAS] Índice do documento atual: {doc_idx}, buscando próximo...')
        doc_encontrado, doc_link, novo_idx = checar_prox(driver, itens, doc_idx, None, texto_documento)
        
        if doc_encontrado and doc_link:
            if debug:
                print(f'[ARGOS][REGRAS] Próximo documento encontrado no índice {novo_idx}, abrindo...')
            
            # Clicando no próximo documento
            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', doc_link)
            sleep(500)
            click_resultado = safe_click(driver, doc_link, log=debug)
            
            if not click_resultado:
                if debug:
                    print('[ARGOS][REGRAS] Falha no clique seguro, tentando via JavaScript')
                try:
                    driver.execute_script('arguments[0].click();', doc_link)
                except Exception as e:
                    if debug:
                        print(f'[ARGOS][REGRAS][ERRO] Falha ao clicar no próximo documento: {e}')
                    return False
            
            # Aguardando carregamento
            sleep(1500)
            
            # Extraindo texto do novo documento
            try:
                novo_texto, _ = extrair_documento(driver)
                novo_tipo = "decisao" if "decisão" in doc_link.text.lower() else "despacho"
                
                if debug:
                    print(f'[ARGOS][REGRAS] Novo documento extraído (tipo {novo_tipo})')
                    print(f'[ARGOS][REGRAS] Repetindo análise de regras para o novo documento')
                
                # Chamada recursiva para aplicar regras no novo documento
                aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, novo_tipo, novo_texto, debug)
                return True
                
            except Exception as e_extracao:
                if debug:
                    print(f'[ARGOS][REGRAS][ERRO] Falha ao extrair texto do próximo documento: {e_extracao}')
                return False
        else:
            if debug:
                print('[ARGOS][REGRAS] Nenhum próximo documento encontrado, continuando com a análise atual')
            return False
    except Exception as e:
        if debug:
            print(f'[ARGOS][REGRAS][ERRO] Falha ao processar próximo documento: {e}')
        return False

def _aplicar_regras_reclamadas(driver, resultado_sisbajud, sigilo_anexos, debug, regra_aplicada):
    """
    Aplica regras baseadas no número de reclamadas (réus) do processo.
    
    Args:
        driver: Instância do WebDriver
        resultado_sisbajud (str): Resultado do SISBAJUD
        sigilo_anexos (dict): Dicionário com status de sigilo dos anexos
        debug (bool): Se True, imprime logs de debug
        regra_aplicada (str): Regra aplicada até o momento
    """
    try:
        dados_processo = extrair_dados_processo(driver)
        if debug:
            print(f'[ARGOS][REGRAS] Dados do processo extraídos: {dados_processo}')
        
        # No contexto trabalhista, "reclamadas" são os "réus" do processo
        num_reclamadas = len(dados_processo.get('reu', []))
        if debug:
            print(f'[ARGOS][REGRAS] Número de reclamadas (réus) encontradas: {num_reclamadas}')
        
        if num_reclamadas == 1:
            regra_aplicada += ' | uma reclamada'
            if debug:
                print('[ARGOS][REGRAS] Uma única reclamada - seguindo regras do despacho')
            if resultado_sisbajud == 'negativo' and all(v == 'nao' for v in sigilo_anexos.values()):
                regra_aplicada += ' | sisbajud negativo, nenhum anexo sigiloso => ato_meios'
                ato_meios(driver, debug=debug)
            elif resultado_sisbajud == 'negativo' and any(v == 'sim' for v in sigilo_anexos.values()):
                regra_aplicada += ' | sisbajud negativo, anexo sigiloso => ato_termoS'
                ato_termoS(driver, debug=debug)
            else:
                regra_aplicada += ' | sisbajud positivo => ato_bloq'
                ato_bloq(driver, debug=debug)
        else:
            regra_aplicada += ' | multiplas reclamadas'
            if debug:
                print(f'[ARGOS][REGRAS] Múltiplas reclamadas ({num_reclamadas}) - verificando SISBAJUD')
            if resultado_sisbajud == 'negativo':
                regra_aplicada += ' | sisbajud negativo => ato_meiosub'
                ato_meiosub(driver, debug=debug)
            else:
                regra_aplicada += ' | sisbajud positivo => ato_bloq'
                ato_bloq(driver, debug=debug)
    except Exception as e:
        if debug:
            print(f'[ARGOS][REGRAS][ERRO] Falha ao aplicar regras de reclamadas: {e}')
        raise

def andamento_argos(driver, resultado_sisbajud, sigilo_anexos, log=True):
    """
    Processa o andamento do Argos com base no resultado do SISBAJUD, sigilo dos anexos e tipo de documento.
    1. Busca documento relevante (decisão ou despacho)
    2. Aplica regras específicas do Argos
    
    Args:
        driver: Instância do WebDriver
        resultado_sisbajud (str): Resultado do SISBAJUD
        sigilo_anexos (dict): Dicionário com status de sigilo dos anexos
        log (bool): Se True, imprime logs de debug
    """
    try:
        if log:
            print('[ARGOS][ANDAMENTO] Iniciando processamento do andamento...')
        
        # Importação local para evitar dependência circular
        from mdd_modulos.argos_documentos import buscar_documento_argos
        
        # 1. Busca documento relevante
        texto_documento, tipo_documento = buscar_documento_argos(driver, log=log)
        if log:
            print(f'[ARGOS][DOCUMENTO] Tipo encontrado: {tipo_documento}')
            
        # 2. Aplica regras específicas do Argos
        aplicar_regras_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=log)
            
        if log:
            print('[ARGOS][ANDAMENTO] Processamento do andamento concluído.')
            
    except Exception as e:
        if log:
            print(f'[ARGOS][ANDAMENTO][ERRO] Falha no processamento do andamento: {e}')
        raise
