import time
import re
import json
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Fix.log import log_seletor_multiplo, logger
def normalizar_string(valor):
    if not valor:
        return ''
    valor_norm = unicodedata.normalize('NFD', str(valor))
    valor_norm = ''.join(ch for ch in valor_norm if unicodedata.category(ch) != 'Mn')
    return valor_norm.lower()
def _normalizar_nome_para_match(nome):
    nome_norm = normalizar_string(nome)
    return re.sub(r'\s+', ' ', nome_norm).strip()

def _carregar_dadosatuais_local(caminho='dadosatuais.json'):
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}
def _montar_destinatarios_por_observacao(observacao, dados_processo):
    if not observacao or not isinstance(dados_processo, dict):
        return []

    texto_obs = _normalizar_nome_para_match(observacao)
    if not texto_obs:
        return []

    # Ex.: "Prazo: xs pec gabriela david" -> tokens alvo ["gabriela", "david"]
    texto_limpo = re.sub(r'^\s*prazo\s*:\s*', '', texto_obs, flags=re.I).strip()
    texto_limpo = re.sub(r'^\s*xs\s+pec\b', '', texto_limpo, flags=re.I).strip()

    stopwords = {
        'xs', 'pec', 'prazo', 'para', 'sobre', 'com', 'sem', 'de', 'da', 'do',
        'dos', 'das', 'e', 'ou', 'manifestacao', 'manifestação', 'idpj'
    }
    tokens_alvo = [
        t for t in re.findall(r'[a-z0-9]+', texto_limpo)
        if len(t) >= 3 and t not in stopwords
    ]

    if not tokens_alvo:
        return []

    destinatarios = []
    vistos = set()
    for parte in dados_processo.get('reu', []) or []:
        nome = (parte.get('nome') or '').strip()
        doc = (parte.get('cpfcnpj') or '').strip()
        if not nome:
            continue

        nome_norm = _normalizar_nome_para_match(nome)
        if not nome_norm:
            continue

        tokens_nome = set(re.findall(r'[a-z0-9]+', nome_norm))
        if any(token in tokens_nome for token in tokens_alvo):
            chave = (nome_norm, re.sub(r'\D', '', doc or ''))
            if chave in vistos:
                continue
            vistos.add(chave)
            destinatarios.append({
                'nome_oficial': nome,
                'nome_identificado': nome,
                'documento': doc,
                'documento_normalizado': re.sub(r'\D', '', doc or ''),
                'polo': 'reu'
            })
    return destinatarios
def _clicar_polo_passivo(driver, log):
    header = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//mat-expansion-panel-header[.//div[contains(@class,"pec-item-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]]'))
    )
    aria_expanded = (header.get_attribute('aria-expanded') or '').strip().lower()
    if aria_expanded == 'true':
        return

    alvo = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//div[contains(@class,"pec-item-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]'))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", alvo)
    driver.execute_script("arguments[0].click();", alvo)


def _clicar_botao_polo_passivo(driver, log):
    btn_polo_passivo = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]'))
    )
    driver.execute_script("arguments[0].click();", btn_polo_passivo)
def selecionar_destinatario_por_documento(driver, destinatario_info, debug=False, timeout=10, qtd_cliques=1):
    qtd_cliques = 2 if str(qtd_cliques).strip().lower() in ('2', '2x') else 1
    try:
        if isinstance(destinatario_info, dict):
            documento_alvo = destinatario_info.get('documento') or destinatario_info.get('cpfcnpj') or destinatario_info.get('cpfCnpj')
            doc_normalizado = destinatario_info.get('documento_normalizado') or re.sub(r'\D', '', str(documento_alvo or ''))
            nome_alvo = (
                destinatario_info.get('nome_oficial')
                or destinatario_info.get('nome_identificado')
                or destinatario_info.get('nome')
            )
        else:
            documento_alvo = doc_normalizado = nome_alvo = None

        doc_digits = re.sub(r'\D', '', doc_normalizado or documento_alvo or '')

        try:
            linhas = WebDriverWait(driver, timeout).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row')
            )
        except Exception:
            linhas = driver.find_elements(By.CSS_SELECTOR, 'mat-row, .pec-partes-polo li, ul.sem-padding li')

        candidatos = []
        for linha in linhas:
            try:
                texto_linha = linha.text or ''
                texto_normalizado = re.sub(r'\D', '', texto_linha)
                if doc_digits and doc_digits in texto_normalizado:
                    candidatos.append((linha, texto_linha))
            except Exception:
                continue

        if candidatos:
            nome_alvo_norm = normalizar_string(nome_alvo) if nome_alvo else ''
            best = None
            best_score = -1
            for linha, texto_linha in candidatos:
                try:
                    score = 20
                    nome_span = None
                    try:
                        nome_span = linha.find_element(By.CSS_SELECTOR, '.nome-parte, .nome-tipo-parte, .pec-formatacao-padrao-dados-parte.nome-parte')
                    except Exception:
                        nome_span = None

                    if nome_span:
                        nome_linha = normalizar_string(nome_span.text or '')
                        if nome_alvo_norm and nome_linha == nome_alvo_norm:
                            score += 40
                        elif nome_alvo_norm and nome_alvo_norm in nome_linha:
                            score += 15
                    else:
                        if nome_alvo_norm and nome_alvo_norm in normalizar_string(texto_linha):
                            score += 10

                    try:
                        texto_norm = normalizar_string(texto_linha)
                        doc_pos = texto_norm.find(re.sub(r'\D', '', doc_digits)) if doc_digits else -1
                    except Exception:
                        doc_pos = -1
                    try:
                        nome_pos = texto_norm.find(nome_alvo_norm) if nome_alvo_norm else -1
                    except Exception:
                        nome_pos = -1
                    if doc_pos >= 0 and nome_pos >= 0 and abs(doc_pos - nome_pos) < 80:
                        score += 5

                    if 'advogado' in texto_linha.lower() and nome_alvo_norm and len(nome_alvo_norm.split()) >= 2:
                        score -= 2

                    if score > best_score:
                        best_score = score
                        best = linha
                except Exception:
                    continue

            if best is not None:
                seletores_seta = [
                    'button[mattooltip*="acrescentar"]',
                    'button[aria-label*="acrescentar"]',
                    'button .fa-arrow-circle-down',
                    'button[mat-icon-button]',
                    'button mat-icon-button'
                ]
                btn_seta = None
                for seletor in seletores_seta:
                    log_seletor_multiplo('[DESTINATARIOS]', seletor, 'TENTATIVA')
                    try:
                        btn_seta = best.find_element(By.CSS_SELECTOR, seletor)
                        log_seletor_multiplo('[DESTINATARIOS]', seletor, 'SUCESSO')
                        break
                    except Exception as e:
                        log_seletor_multiplo('[DESTINATARIOS]', seletor, 'FALHA', str(e))
                        continue
                if btn_seta:
                    try:
                        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn_seta)
                        for _ in range(qtd_cliques):
                            time.sleep(0.3)
                            driver.execute_script('arguments[0].click();', btn_seta)
                    except Exception:
                        try:
                            for _ in range(qtd_cliques):
                                btn_seta.click()
                                time.sleep(0.2)
                        except Exception:
                            pass
                    if debug:
                        logger.info(f"[DESTINATARIOS]  Parte selecionada via documento (melhor candidato): {documento_alvo}")
                    return True

        if nome_alvo:
            nome_alvo_norm = normalizar_string(nome_alvo)
            for linha in linhas:
                try:
                    texto_linha = linha.text or ''
                    if nome_alvo_norm and nome_alvo_norm in normalizar_string(texto_linha):
                        seletores_seta = [
                            'button[mattooltip*="acrescentar"]',
                            'button[aria-label*="acrescentar"]',
                            'button .fa-arrow-circle-down',
                            'button[mat-icon-button]'
                        ]
                        btn_seta = None
                        for seletor in seletores_seta:
                            log_seletor_multiplo('[DESTINATARIOS]', seletor, 'TENTATIVA')
                            try:
                                btn_seta = linha.find_element(By.CSS_SELECTOR, seletor)
                                log_seletor_multiplo('[DESTINATARIOS]', seletor, 'SUCESSO')
                                break
                            except Exception as e:
                                log_seletor_multiplo('[DESTINATARIOS]', seletor, 'FALHA', str(e))
                                continue
                        if btn_seta:
                            try:
                                driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn_seta)
                                for _ in range(qtd_cliques):
                                    time.sleep(0.3)
                                    driver.execute_script('arguments[0].click();', btn_seta)
                            except Exception:
                                try:
                                    for _ in range(qtd_cliques):
                                        btn_seta.click()
                                        time.sleep(0.2)
                                except Exception:
                                    pass
                            if debug:
                                logger.info(f"[DESTINATARIOS]  Parte selecionada via nome: {nome_alvo}")
                            return True
                except Exception:
                    continue

        if debug:
            logger.info(f"[DESTINATARIOS][WARN] Não foi possível incluir parte: {nome_alvo or documento_alvo}")
        return False
    except Exception as e:
        if debug:
            logger.info(f"[DESTINATARIOS][ERRO] {e}")
        return False
def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, observacao=None, numero_processo=None):
    if log is None:
        def log(_msg):
            return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1

    def _selecionar_por_lista(lista_destinatarios, origem_log, fallback_polo_passivo=False):
        selecionados = 0
        _clicar_polo_passivo(driver, log)

        if not lista_destinatarios:
            log(f'[DESTINATARIOS][WARN] Lista de destinatários vazia ({origem_log})')
            if fallback_polo_passivo:
                _clicar_botao_polo_passivo(driver, log)
                log('[DESTINATARIOS] Fallback polo passivo aplicado')
            return 0

        for destinatario_info in lista_destinatarios:
            if selecionar_destinatario_por_documento(driver, destinatario_info, debug=debug, qtd_cliques=qtd_seta):
                selecionados += 1
                time.sleep(0.3)

        if selecionados == 0:
            log(f'[DESTINATARIOS][WARN] Nenhum destinatário selecionado ({origem_log})')
            if fallback_polo_passivo:
                _clicar_botao_polo_passivo(driver, log)
                log('[DESTINATARIOS] Fallback polo passivo aplicado')
        else:
            log(f'[DESTINATARIOS] {selecionados} destinatário(s) selecionado(s) via {origem_log}')
        return selecionados

    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')

    elif isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        selecionados = 0
        for destinatario_info in destinatarios:
            if selecionar_destinatario_por_documento(driver, destinatario_info, debug=debug):
                selecionados += 1
                time.sleep(0.3)
        if selecionados == 0:
            log('[DESTINATARIOS][WARN] Lista explícita sem seleção - fallback polo passivo (1x)')
            try:
                _clicar_polo_passivo(driver, log)
            except Exception as e:
                log(f'[DESTINATARIOS][ERRO] Falha no fallback polo passivo: {e}')

    elif destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO 3: Clicando no polo ativo (1x)')
        try:
            btn_polo_ativo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloAtivo"]'))
            )
            driver.execute_script("arguments[0].click();", btn_polo_ativo)
            log('[DESTINATARIOS]  Polo ativo selecionado')
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')

    elif destinatarios == 'polo_passivo':
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques_polo_passivo}x com intervalo 2s)')
        try:
            btn_polo_passivo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]'))
            )

            for i in range(cliques_polo_passivo):
                driver.execute_script("arguments[0].click();", btn_polo_passivo)
                log(f'[DESTINATARIOS]  Polo passivo - clique {i+1}')
                if i < cliques_polo_passivo - 1:  # Não espera após o último clique
                    time.sleep(2)

        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo ({cliques_polo_passivo}x): {e}')

    elif destinatarios == 'terceiros':
        log('[DESTINATARIOS] OPÇÃO TERCEIROS: Clicando em terceiros interessados / outros participantes')
        try:
            # Tentar o seletor padrão (btnIntimarSomenteTerceirosInteressados)
            try:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]'))
                )
                driver.execute_script("arguments[0].click();", btn_terceiro)
            except Exception:
                # Fallback: tentar o ícone de terceiros especificado pelo usuário
                log('[DESTINATARIOS] Botão padrão não encontrado. Tentando ícone fa-user pec-polo-outros-partes-processo...')
                btn_icone = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-user.pec-polo-outros-partes-processo'))
                )
                driver.execute_script("arguments[0].click();", btn_icone)
            
            log('[DESTINATARIOS]  Terceiros selecionados')
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar terceiros: {e}')

    elif destinatarios == 'polo_passivo_2x':  # Mantém compatibilidade
        log('[DESTINATARIOS] OPÇÃO 2: Clicando no polo passivo (2x com intervalo 2s)')
        try:
            btn_polo_passivo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]'))
            )

            driver.execute_script("arguments[0].click();", btn_polo_passivo)
            log('[DESTINATARIOS]  Polo passivo - primeiro clique')

            time.sleep(2)

            driver.execute_script("arguments[0].click();", btn_polo_passivo)
            log('[DESTINATARIOS]  Polo passivo - segundo clique')

        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo (2x): {e}')

    elif destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários extraídos em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            _selecionar_por_lista(lista_destinatarios, 'cache')
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')

    elif destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: extraindo dados e cruzando nomes da observação')
        try:
            from Fix.extracao_processo import extrair_dados_processo

            dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
            if not dados_processo:
                dados_processo = _carregar_dadosatuais_local('dadosatuais.json')

            candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo)
            _selecionar_por_lista(candidatos, 'observação', fallback_polo_passivo=True)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')

    elif destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPÇÃO ESPECIAL: Primeiro destinatário (pec_excluiargos)')
    else:
        log('[DESTINATARIOS] OPÇÃO 1 (PADRÃO): Clicando no polo passivo (1x)')
        try:
            btn_polo_passivo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]'))
            )
            driver.execute_script("arguments[0].click();", btn_polo_passivo)
            log('[DESTINATARIOS]  Polo passivo selecionado')
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')

    if terceiro:
        log('[DESTINATARIOS] FLAG terceiro=True: Adicionando terceiros interessados')
        try:
            btn_terceiro = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]'))
            )
            driver.execute_script("arguments[0].click();", btn_terceiro)
            log('[DESTINATARIOS]  Terceiros interessados adicionados')
        except Exception as e:
            log(f'[DESTINATARIOS][WARN] Falha ao adicionar terceiros: {e}')

    elif destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPÇÃO ESPECIAL: Primeiro destinatário (pec_excluiargos)')
        try:
            _clicar_polo_passivo(driver, log)
            time.sleep(0.5)

            primeira_seta = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//mat-expansion-panel[.//*[contains(text(), "Polo Passivo")]]//button[@aria-label="Clique para acrescentar esta parte à lista de destinatários de expedientes e comunicações."][1]'))
            )
            driver.execute_script("arguments[0].click();", primeira_seta)
            log('[DESTINATARIOS]  Primeira seta (primeiro destinatário) clicada')
            time.sleep(1)

            btn_alterar_endereco = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Alterar endereço"]'))
            )
            driver.execute_script("arguments[0].click();", btn_alterar_endereco)
            log('[DESTINATARIOS]  Botão Alterar endereço clicado')
            time.sleep(0.5)

            try:
                log('[DESTINATARIOS] 3. Buscando tribunal nos endereços disponíveis...')
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.pec-consulta-enderecos'))
                    )
                    log('[DESTINATARIOS] 3a. Formulário de consulta de endereços detectado')
                except Exception:
                    log('[DESTINATARIOS] 3a. Formulário de consulta de endereços não apareceu')
                    raise Exception('Consulta não apareceu')

                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Nenhum resultado encontrado')]"))
                    )
                    log('[DESTINATARIOS] 3b. Snack-bar detectado: "Nenhum resultado encontrado" -> incluir tribunal via CEP')

                    log('[DESTINATARIOS] 3c. Digitando CEP 01302906 no campo inputCep')
                    campo_cep = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#inputCep'))
                    )
                    campo_cep.clear()
                    for char in '01302906':
                        campo_cep.send_keys(char)
                        time.sleep(0.1)
                    time.sleep(1)

                    log('[DESTINATARIOS] 3d. Clicando na opção do tribunal TRT2 São Paulo')
                    opcao_tribunal = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), '01302-906')]"))
                    )
                    opcao_tribunal.click()
                    log('[DESTINATARIOS]  Opção do tribunal selecionada')
                    time.sleep(0.5)

                    log('[DESTINATARIOS] 3e. Clicando no botão Salvar das alterações')
                    btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                    )
                    btn_salvar_alteracoes.click()
                    log('[DESTINATARIOS]  Alterações salvas')
                    time.sleep(0.5)

                    log('[DESTINATARIOS] 3f. Clicando no botão fechar para fechar endereços')
                    btn_fechar = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                    )
                    btn_fechar.click()
                    log('[DESTINATARIOS]  Janela de endereços fechada')
                except Exception:
                    log('[DESTINATARIOS] 3b. Nenhum snack-bar - buscando tribunal na tabela de endereços')
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'table[name="Endereços do destinatário no sistema"]'))
                        )

                        linhas_tribunal = driver.find_elements(By.XPATH,
                            "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tribunal')]"
                        )
                        if linhas_tribunal:
                            log('[DESTINATARIOS] 3c. Encontrado endereço do tribunal, clicando na seta')
                            linha_tribunal = linhas_tribunal[0].find_element(By.XPATH, './ancestor::tr')
                            seta_tribunal = linha_tribunal.find_element(By.CSS_SELECTOR, 'button[aria-label="Selecionar endereço"]')
                            seta_tribunal.click()
                            log('[DESTINATARIOS]  Endereço do tribunal selecionado')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3d. Clicando no botão fechar para fechar endereços')
                            btn_fechar = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                            )
                            btn_fechar.click()
                            log('[DESTINATARIOS]  Janela de endereços fechada')
                        else:
                            log('[DESTINATARIOS] 3c. Nenhum endereço do tribunal encontrado na tabela - incluindo tribunal via CEP')

                            log('[DESTINATARIOS] 3d. Digitando CEP 01302906 no campo inputCep')
                            campo_cep = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input#inputCep'))
                            )
                            campo_cep.clear()
                            for char in '01302906':
                                campo_cep.send_keys(char)
                                time.sleep(0.1)
                            time.sleep(1)

                            log('[DESTINATARIOS] 3e. Clicando na opção do tribunal TRT2')
                            opcao_tribunal = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//span[@class='mat-option-text' and contains(text(), '01302-906')]"))
                            )
                            opcao_tribunal.click()
                            log('[DESTINATARIOS]  Tribunal selecionado')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3f. Clicando em Salvar alterações')
                            btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                            )
                            btn_salvar_alteracoes.click()
                            log('[DESTINATARIOS]  Alterações salvas')
                            time.sleep(0.5)

                            log('[DESTINATARIOS] 3g. Fechando janela de endereços')
                            btn_fechar = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                            )
                            btn_fechar.click()
                            log('[DESTINATARIOS]  Janela fechada')
                    except Exception as e:
                        log(f'[DESTINATARIOS] Erro ao processar endereços: {e}')
            except Exception as tribunal_err:
                log(f'[DESTINATARIOS] Aviso: Não foi possível adicionar tribunal: {tribunal_err}')
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar primeiro destinatário: {e}')

    return True
