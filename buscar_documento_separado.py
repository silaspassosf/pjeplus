def buscar_ultimo_mandado(driver, log=True):
    """
    Busca o último documento do tipo 'mandado' na timeline do processo.
    Retorna o texto do documento e seu tipo, ou None se não encontrado.
    """
    try:
        # Espera a timeline carregar
        itens_timeline = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens_timeline:
            if log:
                print('[MANDADO] Nenhum item encontrado na timeline.')
            return None, None

        # Procura pelo último documento do tipo 'mandado'
        for item in itens_timeline:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()

                # Verifica se é do tipo 'mandado'
                if 'mandado' in doc_text:
                    link.click()
                    time.sleep(1)

                    # Extrai o texto do documento
                    texto = item.text
                    if log:
                        print(f'[MANDADO] Documento encontrado: {doc_text}')
                    return texto, 'mandado'

            except Exception as e:
                if log:
                    print(f'[MANDADO][ERRO] Falha ao processar item: {e}')
                continue

        if log:
            print('[MANDADO] Nenhum documento do tipo mandado encontrado.')
        return None, None

    except Exception as e:
        if log:
            print(f'[MANDADO][ERRO] Falha geral: {e}')
        return None, None
