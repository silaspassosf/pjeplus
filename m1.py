# m1.py
# Fluxo automatizado de mandados PJe TRT2

from Fix import (
    login_pc,  # Corrigido: era login_automatico
    navegar_para_tela,
    processar_lista_processos,
    extrair_texto_pdf_por_conteudo,
    tratar_anexos,
    analise_outros,
    extrair_documento,
    criar_gigs,
    esperar_elemento,
    safe_click,
    buscar_seletor_robusto,
    limpar_temp_selenium,
    driver_notebook,
    login_notebook,
    indexar_e_processar_lista
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
    ato_termoS
)
import os
from selenium import webdriver
from selenium.webdriver.common.by import By

def lembrete_bloq(driver, debug=False):
    """
    Cria lembrete de bloqueio com título "Bloqueio pendente" e conteúdo "processar após IDPJ".
    """
    try:
        if debug:
            print('[ARGOS][LEMBRETE] Criando lembrete de bloqueio...')
            
        # 1. Clique no menu (fa-bars)
        menu = safe_click(driver, '.fa-bars', log=debug)
        time.sleep(1)
        
        # 2. Clique no ícone de lembrete (fa thumbtack)
        lembrete = safe_click(driver, '.lista-itens-menu > li:nth-child(16) > pje-icone-post-it:nth-child(1) > li:nth-child(1) > button:nth-child(1)', log=debug)
        time.sleep(1)
        
        # 3. Foco no conteúdo do diálogo
        dialog = safe_click(driver, '.mat-dialog-content', log=debug)
        time.sleep(1)
        
        # 4. Preenche título
        titulo = driver.find_element(By.CSS_SELECTOR, '#tituloPostit')
        titulo.clear()
        titulo.send_keys('Bloqueio pendente')
        
        # 5. Preenche conteúdo
        conteudo = driver.find_element(By.CSS_SELECTOR, '#conteudoPostit')
        conteudo.clear()
        conteudo.send_keys('processar após IDPJ')
        
        # 6. Clica em salvar
        salvar = safe_click(driver, 'button.mat-raised-button:nth-child(1)', log=debug)
        time.sleep(1)
        
        if debug:
            print('[ARGOS][LEMBRETE] Lembrete criado com sucesso.')
            
    except Exception as e:
        if debug:
            print(f'[ARGOS][LEMBRETE][ERRO] Falha ao criar lembrete: {e}')
            raise

def aplicar_regras_argos(driver, resultado_sisbajud, tipo_documento, texto_documento, debug=False):
    """
    Aplica as regras específicas do Argos com base no resultado do SISBAJUD e tipo de documento.
    """
    try:
        if debug:
            print(f'[ARGOS][REGRAS] Analisando regras para tipo: {tipo_documento}')
            
        # 1. Se é despacho com texto específico
        if tipo_documento == 'despacho' and any(p in texto_documento.lower() for p in ['em que pese a ausência', 'argos']):
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como despacho com texto específico')
                
            # a) SISBAJUD negativo, sem doc sigiloso
            if resultado_sisbajud == 'negativo':
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo - chamando ato_meios')
                ato_meios(driver, debug=debug)
                
            # b) SISBAJUD negativo, com doc sigiloso
            elif resultado_sisbajud == 'negativo' and resultado_sisbajud == 'doc_sigiloso':
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo com doc sigiloso - chamando ato_termoS')
                ato_termoS(driver, debug=debug)
                
            # c) SISBAJUD positivo
            elif resultado_sisbajud == 'positivo':
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD positivo - chamando ato_bloq')
                ato_bloq(driver, debug=debug)
                
        # 2. Se é decisão com texto "tendo em vista que a reclamada"
        elif tipo_documento == 'decisao' and 'tendo em vista que a reclamada' in texto_documento.lower():
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como decisão com texto sobre reclamada')
                
            # Extrai dados do processo
            dados_processo = extrair_dados_processo(driver, log=debug)
            if debug:
                print(f'[ARGOS][REGRAS] Dados do processo extraídos: {dados_processo}')
                
            # Se for só uma reclamada, segue regras do despacho
            if len(dados_processo.get('reclamadas', [])) == 1:
                if debug:
                    print('[ARGOS][REGRAS] Uma única reclamada - seguindo regras do despacho')
                if resultado_sisbajud == 'negativo':
                    ato_meios(driver, debug=debug)
                else:
                    ato_bloq(driver, debug=debug)
                    
            # Se for mais de uma reclamada, cria GIGS
            else:
                if debug:
                    print('[ARGOS][REGRAS] Mais de uma reclamada - criando GIGS')
                criar_gigs(driver, dias_uteis=0, observacao='Pz mdd subid', tela='principal', log=debug)
                
        # 3. Se é decisão com texto "defiro a instauração"
        elif tipo_documento == 'decisao' and 'defiro a instauração' in texto_documento.lower():
            if debug:
                print('[ARGOS][REGRAS] Documento identificado como decisão de instauração')
                
            # a) SISBAJUD negativo
            if resultado_sisbajud == 'negativo':
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD negativo - chamando pec_idpj')
                pec_idpj(driver, debug=debug)
                
            # b) SISBAJUD positivo
            elif resultado_sisbajud == 'positivo':
                if debug:
                    print('[ARGOS][REGRAS] SISBAJUD positivo - criando lembrete e chamando pec_idpj')
                lembrete_bloq(driver, debug=debug)
                pec_idpj(driver, debug=debug)
                
        else:
            if debug:
                print(f'[ARGOS][REGRAS] Tipo de documento não identificado: {tipo_documento}')
                
    except Exception as e:
        if debug:
            print(f'[ARGOS][REGRAS][ERRO] Falha ao aplicar regras: {e}')
            raise

def andamento_argos(driver, resultado_sisbajud, log=True):
    """
    Processa o andamento do Argos com base no resultado do SISBAJUD e tipo de documento.
    1. Busca documento relevante (decisão ou despacho)
    2. Aplica regras específicas do Argos
    """
    try:
        if log:
            print('[ARGOS][ANDAMENTO] Iniciando processamento do andamento...')
            
        # 1. Busca documento relevante
        texto_documento, tipo_documento = buscar_documento_argos(driver, log=log)
        if log:
            print(f'[ARGOS][DOCUMENTO] Tipo encontrado: {tipo_documento}')
            
        # 2. Aplica regras específicas do Argos
        aplicar_regras_argos(driver, resultado_sisbajud, tipo_documento, texto_documento, debug=log)
            
        if log:
            print('[ARGOS][ANDAMENTO] Processamento do andamento concluído.')
            
    except Exception as e:
        if log:
            print(f'[ARGOS][ANDAMENTO][ERRO] Falha no processamento do andamento: {e}')
            raise

def processar_argos(driver, log=True):
    """
    Processa o fluxo completo de Argos (Pesquisa Patrimonial).
    1. Busca documentos sequenciais
    2. Trata sigilos e anexos
    3. Verifica SISBAJUD nos anexos
    4. Se não encontrado, extrai PDF para confirmação
    5. Busca documento relevante (decisão ou despacho)
    6. Processa andamento com base no resultado
    """
    try:
        if log:
            print('[ARGOS] Iniciando processamento...')
            
        # 1. Busca documentos sequenciais
        documentos = buscar_documentos_sequenciais(driver, log=log)
        if not documentos:
            raise Exception('Nenhum documento relevante encontrado na timeline')
            
        # 2. Processa cada documento
        for doc in documentos:
            processar_documento_argos(doc, driver, log=log)
            
        # 3. Verifica SISBAJUD nos anexos
        resultado_sisbajud = tratar_anexos_sisbajud(driver)
        if log:
            print(f'[ARGOS][SISBAJUD] Resultado inicial: {resultado_sisbajud}')
            
        # 4. Se não encontrado, extrai PDF para confirmação
        if resultado_sisbajud == 'nao_encontrado':
            if log:
                print('[ARGOS][SISBAJUD] Não encontrado nos anexos, tentando extração do PDF...')
                
            # Extrai PDF e verifica SISBAJUD
            texto_pdf = extrair_texto_pdf_por_conteudo(driver, termo=r"SISBAJUD\s*\n\s*(Negativo|Positivo)", pagina=2)
            if texto_pdf:
                # Verifica se encontrou o padrão
                if "Positivo" in texto_pdf:
                    resultado_sisbajud = 'positivo'
                elif "Negativo" in texto_pdf:
                    resultado_sisbajud = 'negativo'
                
                if log:
                    print(f'[PDF][ARGOS] Trecho extraído: {texto_pdf}')
                    print(f'[ARGOS][SISBAJUD] Resultado após PDF: {resultado_sisbajud}')
            
        # 5. Busca documento relevante
        texto_documento, tipo_documento = buscar_documento_argos(driver, log=log)
        if log:
            print(f'[ARGOS][DOCUMENTO] Tipo encontrado: {tipo_documento}')
            
        # 6. Processa andamento
        andamento_argos(driver, resultado_sisbajud, log=log)
            
        if log:
            print('[ARGOS] Processamento concluído.')
            
    except Exception as e:
        if log:
            print(f'[ARGOS][ERRO] Falha no processamento: {e}')
            raise

def tratar_anexos_argos(doc, driver, log=True):
    """
    Trata os anexos de um documento Argos:
    1. Abre a seção de anexos
    2. Processa cada anexo
    3. Trata intimação se encontrada
    """
    try:
        if log:
            print('[ARGOS][ANEXOS] Tratando anexos...')
            
        # 1. Abre a seção de anexos
        btn_anexos = doc.find_elements(By.CSS_SELECTOR, "pje-timeline-anexos > div > div")
        if btn_anexos:
            safe_click(driver, btn_anexos[0])
            time.sleep(2)
            
            # 2. Processa cada anexo
            anexos = driver.find_elements(By.CSS_SELECTOR, ".tl-item-anexo")
            for anexo in anexos:
                texto_anexo = anexo.text.strip().lower()
                
                # Trata intimação
                if "intimação" in texto_anexo:
                    fechar_prazo(driver, log=log)
                    continue
                    
                # Trata documentos sigilosos (INFOJUD, DOI, IRPF)
                if any(p in texto_anexo for p in ["infojud", "doi", "irpf"]):
                    # Trata documentos sigilosos
                    btn_sigilo = anexo.find_elements(By.CSS_SELECTOR, "i.fa-wpexplorer")
                    if btn_sigilo:
                        safe_click(driver, btn_sigilo[0])
                        time.sleep(1)
                        
                    # Trata visibilidade
                    btn_visibilidade = anexo.find_elements(By.CSS_SELECTOR, "i.fa-plus")
                    if btn_visibilidade:
                        safe_click(driver, btn_visibilidade[0])
                        time.sleep(1)
                        
                    # Confirma alterações
                    btn_confirmar = anexo.find_elements(By.CSS_SELECTOR, ".mat-dialog-actions > button:nth-child(1) > span")
                    if btn_confirmar:
                        safe_click(driver, btn_confirmar[0])
                        time.sleep(1)
                        
                    # Registra que encontrou documento sigiloso
                    return 'doc_sigiloso'
                    
                # Trata SISBAJUD
                if "sisbajud" in texto_anexo:
                    tratar_anexos_sisbajud(driver)
                    
        if log:
            print('[ARGOS][ANEXOS] Anexos tratados com sucesso.')
            
    except Exception as e:
        if log:
            print(f'[ARGOS][ANEXOS][ERRO] Falha ao tratar anexos: {e}')
            raise

def fluxo_mandado(driver):
    """
    Percorre a lista de processos e executa o fluxo adequado (Argos ou Outros) para cada mandado.
    """
    def fluxo_callback(driver):
        try:
            # Identificar documento ativo
            doc_ativo = driver.find_element_by_css_selector('li.tl-item-container.tl-item-ativo').text.lower()
            if 'pesquisa patrimonial - argos' in doc_ativo:
                print(f'[MANDADO] Fluxo ARGOS')
                processar_argos(driver)
            elif 'oficial de justiça' in doc_ativo:
                print(f'[MANDADO] Fluxo OUTROS')
                def fluxo_mandados_hipotese2(driver):
                    print('[MANDADOS][OUTROS] Iniciando fluxo Mandado 2 (Outros)')
                    def analise_padrao(texto):
                        print(f"[MANDADOS][OUTROS] Texto extraído para análise:\n{texto}\n---Fim do documento---")
                        texto_lower = texto.lower()
                        padrao_oficial = "certidão de oficial" in texto_lower
                        padrao_positivo = any(p in texto_lower for p in ["citei", "intimei", "recebeu o mandado", "de tudo ficou ciente"])
                        padrao_negativo = any(p in texto_lower for p in [
                            "não localizado", "negativo", "não encontrado",
                            "deixei de citar", "deixei de efetuar", "não logrei êxito", "desconhecido no local",
                            "não foi possível efetuar"
                        ])
                        if padrao_oficial:
                            print("[MANDADOS][OUTROS][LOG] Padrão 'certidão de oficial' ENCONTRADO no texto.")
                            if padrao_positivo:
                                print("[MANDADOS][OUTROS][LOG] Padrão de mandado POSITIVO encontrado no texto.")
                                criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                            elif padrao_negativo:
                                print("[MANDADOS][OUTROS][LOG] Padrão de mandado NEGATIVO encontrado no texto.")
                                # Busca último mandado na timeline
                                documento = buscar_ultimo_mandado(driver)
                                if documento:
                                    # Verifica quem assinou
                                    autor = verificar_autor_documento(documento, driver)
                                    if autor and 'silas passos' in autor.lower():
                                        print("[MANDADOS][OUTROS][LOG] Último mandado assinado por Silas Passos - chamando ato_edital")
                                        ato_edital(driver)
                                    else:
                                        print("[MANDADOS][OUTROS][LOG] Último mandado assinado por outro autor - não faz nada")
                                else:
                                    print("[MANDADOS][OUTROS][LOG] Não encontrado último mandado na timeline")
                                    criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                            else:
                                print("[MANDADOS][OUTROS][LOG] Mandado sem padrão reconhecido. Criando GIGS fallback.")
                                criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                        else:
                            print("[MANDADOS][OUTROS][LOG] Documento NÃO é certidão de oficial. Criando GIGS fallback.")
                            criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                        return None
                    texto, resultado = extrair_documento(driver, regras_analise=analise_padrao)
                    if not texto:
                        print("[MANDADOS][OUTROS][ERRO] Não foi possível extrair o texto da certidão.")
                        return
                    try:
                        driver.close()
                        print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
                    except Exception as e:
                        print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e}')
                    print('[MANDADOS][OUTROS] Fluxo Mandado 2 concluído.')
                fluxo_mandados_hipotese2(driver)
            else:
                print(f'[MANDADO] Documento não identificado para decisão de fluxo.')
        except Exception as e:
            print(f'[MANDADO][ERRO] Falha ao processar mandado: {e}')
        finally:
            # Fechar aba e voltar para lista
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

    # processar_lista do Fix.py aceita: driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True
    indexar_e_processar_lista(driver, fluxo_callback)


def navegacao(driver):
    """
    Navegação para a lista de documentos internos do PJe TRT2
    """
    try:
        url_lista = os.getenv('URL_PJE_ESCANINHO', 'https://pje.trt2.jus.br/pjekz/escaninho/documentos-internos')
        print(f'[NAV] Iniciando navegação para: {url_lista}')
        if not navegar_para_tela(driver, url=url_lista, delay=2):
            raise Exception('Falha na navegação para a tela de documentos internos')

        print('[NAV] Clicando no ícone reply-all (mandados devolvidos)...')
        icone = driver.find_element(By.CSS_SELECTOR, 'i.fa-reply-all.icone-clicavel')
        driver.execute_script('arguments[0].scrollIntoView(true);', icone)
        icone.click()
        print('[NAV] Ícone de mandados devolvidos clicado com sucesso.')
        time.sleep(2)
        return True
    except Exception as e:
        print(f'[NAV][ERRO] Falha na navegação: {str(e)}')
        return False


def main():
    # Limpeza inicial
    from Fix import limpar_temp_selenium
    limpar_temp_selenium()

    # Login humanizado Chrome
    from Fix import login_notebook_humano
    driver = login_notebook_humano()
    if not driver:
        print('[ERRO] Falha no login humanizado.')
        return

    # --- TESTE: Executar fluxo_callback em uma URL específica ---
    url_teste = "https://pje.trt2.jus.br/pjekz/processo/6018878/detalhe"
    driver.get(url_teste)
    import time; time.sleep(2)
    def fluxo_callback_teste(driver):
        try:
            doc_ativo = driver.find_element(By.CSS_SELECTOR, 'li.tl-item-container.tl-item-ativo').text.lower()
            if 'pesquisa patrimonial - argos' in doc_ativo:
                print(f'[MANDADO] Fluxo ARGOS')
                processar_argos(driver)
            elif 'oficial de justiça' in doc_ativo:
                print(f'[MANDADO] Fluxo OUTROS')
                analise_outros(driver)
            else:
                print(f'[MANDADO] Documento não identificado para decisão de fluxo.')
        except Exception as e:
            print(f'[MANDADO][ERRO] Falha ao processar mandado: {e}')
        finally:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
    fluxo_callback_teste(driver)
    input("Pressione ENTER para encerrar o teste...")
    driver.quit()

if __name__ == "__main__":
    main()
