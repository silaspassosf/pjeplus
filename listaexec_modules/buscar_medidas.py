"""
Módulo para busca de medidas executórias na timeline do PJe.
Extraído de listaexec2.py para modularização.
"""

from selenium.webdriver.common.by import By


def buscar_medidas_executorias(driver, log=True):
    """
    Busca medidas executórias na timeline do PJe, replicando a lógica do userscript Lista_Exec.user.js.
    Retorna uma lista de dicionários com as medidas encontradas.
    """
    seletores_timeline = [
        'li.tl-item-container',
        '.tl-data .tl-item-container',
        '.timeline-item'
    ]
    itens = []
    seletor_usado = ''
    for seletor in seletores_timeline:
        try:
            itens = driver.find_elements(By.CSS_SELECTOR, seletor)
            if itens and len(itens) > 0:
                seletor_usado = seletor
                if log:
                    print(f'[PY-LISTA-EXEC] Encontrados {len(itens)} itens com: {seletor}')
                    print('[PY-LISTA-EXEC] Primeiro item para debug:', itens[0].text[:200])
                break
        except Exception as e:
            if log:
                print(f'[PY-LISTA-EXEC][ERRO] Falha ao buscar seletor {seletor}: {e}')
    if not itens:
        if log:
            print('[PY-LISTA-EXEC] Nenhum item encontrado na timeline')
        return []
    medidas = []
    itens_alvo = [
        {'nome': 'Certidão de pesquisa patrimonial', 'termos': ['certidão de pesquisa patrimonial', 'certidao de pesquisa patrimonial', 'pesquisa patrimonial']},
        {'nome': 'SISBAJUD', 'termos': ['sisbajud']},
        {'nome': 'INFOJUD', 'termos': ['infojud']},
        {'nome': 'IRPF', 'termos': ['irpf', 'imposto de renda']},
        {'nome': 'DOI', 'termos': ['doi']},
        {'nome': 'Mandado de livre penhora', 'termos': ['mandado de livre penhora', 'mandado de penhora', 'livre penhora']},
        {'nome': 'Serasa', 'termos': ['serasa']},
        {'nome': 'CNIB', 'termos': ['cnib']},
        {'nome': 'CAGED', 'termos': ['caged']},
        {'nome': 'PREVJUD', 'termos': ['prevjud']},
        {'nome': 'SNIPER', 'termos': ['sniper']},
        {'nome': 'CCS', 'termos': ['ccs']},
        {'nome': 'CENSEC', 'termos': ['censec']}
    ]
    itens_somente_anexos = ['INFOJUD', 'IRPF', 'DOI']
    for index, item in enumerate(itens):
        try:
            # Buscar link do documento principal
            links = item.find_elements(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            link = links[0] if links else None
            if link:
                texto_doc = link.text.strip().lower()
                # Data: buscar .tl-data dentro do item ou em irmãos anteriores
                data = None
                try:
                    data_elem = item.find_element(By.CSS_SELECTOR, '.tl-data[name="dataItemTimeline"]')
                except:
                    try:
                        data_elem = item.find_element(By.CSS_SELECTOR, '.tl-data')
                    except:
                        data_elem = None
                if not data_elem:
                    # Buscar em irmãos anteriores
                    try:
                        prev = item
                        for _ in range(5):
                            prev = driver.execute_script('return arguments[0].previousElementSibling', prev)
                            if not prev:
                                break
                            try:
                                data_elem = prev.find_element(By.CSS_SELECTOR, '.tl-data')
                                if data_elem:
                                    break
                            except:
                                continue
                    except:
                        pass
                if data_elem:
                    data_texto = data_elem.text.strip()
                    data = data_texto
                else:
                    data = 'Data não encontrada'
                for item_alvo in itens_alvo:
                    encontrado = any(termo in texto_doc for termo in item_alvo['termos'])
                    if encontrado:
                        if item_alvo['nome'] in itens_somente_anexos:
                            if log:
                                print(f'[PY-LISTA-EXEC] ⚠️ {item_alvo["nome"]} encontrado como documento principal - não será logado (deve ser apenas anexo)')
                            break
                        documento_id = f'doc-{index}'
                        medidas.append({
                            'nome': item_alvo['nome'],
                            'texto': link.text.strip(),
                            'data': data,
                            'id': documento_id,
                            'elemento': item,
                            'index': index,
                            'tipoItem': 'documento'
                        })
                        if log:
                            print(f'[PY-LISTA-EXEC] ✅ {item_alvo["nome"]}: {link.text.strip()} ({data})')
                        break
            # Buscar anexos
            btn_anexos = item.find_elements(By.CSS_SELECTOR, 'pje-timeline-anexos > div > div')
            if btn_anexos and link:
                texto_doc = link.text.strip().lower()
                data = data or 'Data não encontrada'
                if 'pesquisa patrimonial' in texto_doc:
                    anexo_id = f'anexos-{index}'
                    medidas.append({
                        'nome': 'Anexos da Pesquisa Patrimonial',
                        'texto': f'Anexos: {link.text.strip()}',
                        'data': data,
                        'id': anexo_id,
                        'elemento': item,
                        'index': index,
                        'tipoItem': 'anexos',
                        'documentoPai': link.text.strip()
                    })
                    if log:
                        print(f'[PY-LISTA-EXEC] ✅ Anexos de Pesquisa Patrimonial: {data}')
        except Exception as e:
            if log:
                print(f'[PY-LISTA-EXEC][ERRO] Erro ao processar item {index}: {e}')
    if log:
        print(f'[PY-LISTA-EXEC] Total de medidas encontradas: {len(medidas)}')
    return medidas
