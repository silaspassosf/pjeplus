def fluxo_mandado(driver):
    """
    Percorre a lista de processos e executa o fluxo adequado (Argos ou Outros) para cada mandado.
    """
    def fluxo_callback(driver):
        try:
            print('\n' + '='*50)
            print('[FLUXO] Iniciando análise do documento...')
            
            # Passo 0: Clicar no ícone lupa (fa-search lupa-doc-nao-apreciado)
            try:
                print('[FLUXO] Passo 0: Tentando clicar no ícone lupa (fa-search)')
                lupa_selector = 'i.fa.fa-search.fa-2x.lupa-doc-nao-apreciado'
                resultado = safe_click(driver, lupa_selector, timeout=5, log=True)
                if resultado:
                    print('[FLUXO] Passo 0: Clique na lupa realizado com sucesso')
                    # Aguarda breve momento para carregar detalhes após o clique
                    time.sleep(1)
                else:
                    print('[FLUXO][AVISO] Passo 0: Ícone lupa não encontrado ou não clicável')
            except Exception as e:
                print(f'[FLUXO][AVISO] Passo 0: Erro ao tentar clicar na lupa: {e}')
                # Continua o fluxo mesmo se houver erro neste passo
            
            # Identificar documento ativo
            doc_ativo = driver.find_element(By.CSS_SELECTOR, 'li.tl-item-container.tl-item-ativo')
            if not doc_ativo:
                print('[FLUXO][ERRO] Documento ativo não encontrado')
                return
                
            texto_doc = doc_ativo.text
            print(f'[FLUXO] Documento encontrado: {texto_doc}')
            
            # Decisão de fluxo baseada no texto do documento
            texto_lower = texto_doc.lower()
            
            if 'pesquisa patrimonial - argos' in texto_lower:
                print('\n[FLUXO] >>> INICIANDO FLUXO ARGOS <<<')
                print(f'[FLUXO][ARGOS] Documento identificado: {texto_doc}')
                print('='*50)
                processar_argos(driver)
            elif 'oficial de justiça' in texto_doc:
                print(f'[MANDADO] Fluxo OUTROS')
                def fluxo_mandados_hipotese2(driver):
                    print('[MANDADOS][OUTROS] Iniciando fluxo Mandado 2 (Outros)')
                    def analise_padrao(texto):
                        print(f"[MANDADOS][OUTROS] Texto extraído para análise:\n{texto}\n---Fim do documento---")
                        texto_lower = texto.lower()
                        
                        # Nova regra: Verifica se contém "cancelamento TOTAL da inserção"
                        if "cancelamento total da inserção" in texto_lower:
                            print("[MANDADOS][OUTROS][LOG] Padrão 'cancelamento TOTAL da inserção' ENCONTRADO - chamando mov_arquivar")
                            try:
                                mov_arquivar(driver)
                                print("[MANDADOS][OUTROS][LOG] mov_arquivar executado com sucesso")
                                return None
                            except Exception as e:
                                print(f"[MANDADOS][OUTROS][ERRO] Erro ao executar mov_arquivar: {e}")
                        
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
                                # criar_gigs(driver, dias_uteis=0, observacao='xx positivo', tela='principal')
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
                                    # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                            else:
                                print("[MANDADOS][OUTROS][LOG] Mandado sem padrão reconhecido. Criando GIGS fallback.")
                                # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                        else:
                            print("[MANDADOS][OUTROS][LOG] Documento NÃO é certidão de oficial. Criando GIGS fallback.")
                            # criar_gigs(driver, dias_uteis=0, observacao='pz mdd', tela='principal')
                        return None
                    
                    try:
                        driver.close()
                        print('[MANDADOS][OUTROS] Aba fechada após análise e ação.')
                    except Exception as e:
                        print(f'[MANDADOS][OUTROS][ERRO] Falha ao fechar aba: {e}')
                    print('[MANDADOS][OUTROS] Fluxo Mandado 2 concluído.')
                
                fluxo_mandados_hipotese2(driver)
                print('[FLUXO][OUTROS] Processamento concluído')
                
            else:
                print('\n[FLUXO][AVISO] >>> DOCUMENTO NÃO IDENTIFICADO <<<')
                print(f'[FLUXO][AVISO] Texto do documento: {texto_doc}')
                print('='*50)
