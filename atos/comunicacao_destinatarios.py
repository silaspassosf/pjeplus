from Fix.core import safe_click_no_scroll
import re
import json
import unicodedata
import time
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

def _partial_name_match(nome_norm, texto_norm, min_tokens=2):
    try:
        tokens = [t for t in re.findall(r'[a-z0-9]+', nome_norm) if len(t) >= 3]
        if len(tokens) < min_tokens:
            return False
        found = sum(1 for t in tokens if t in texto_norm)
        return found >= min_tokens
    except Exception:
        return False

def _carregar_dadosatuais_local(caminho='dadosatuais.json'):
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}
def _montar_destinatarios_por_observacao(observacao, dados_processo, debug=False):
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

    if debug:
        try:
            logger.info(f"[DESTINATARIOS][DEBUG] Tokens alvo extraídos da observação: {tokens_alvo}")
        except Exception:
            pass

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
        match_found = any(token in tokens_nome for token in tokens_alvo)
        if debug:
            try:
                logger.info(f"[DESTINATARIOS][DEBUG] Comparando parte='{nome}' tokens_nome={list(tokens_nome)} match={match_found}")
            except Exception:
                pass

        if match_found:
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
    safe_click_no_scroll(driver, alvo, log=False)


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
                        # Prefer to click the closest ancestor button if the selector
                        # returned an inner element (e.g., an <i> icon). This ensures
                        # the click targets the actual interactive control.
                        clickable = driver.execute_script("return (arguments[0].closest && arguments[0].closest('button')) || arguments[0];", btn_seta)
                        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', clickable)
                        try:
                            tname = getattr(clickable, 'tag_name', None)
                        except Exception:
                            tname = None
                        if debug:
                            try:
                                logger.info(f"[DESTINATARIOS][DEBUG] Usando elemento clicavel: {tname}")
                            except Exception:
                                pass
                        for _ in range(qtd_cliques):
                            time.sleep(0.3)
                            driver.execute_script('arguments[0].click();', clickable)
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
                    texto_norm = normalizar_string(texto_linha)
                    if nome_alvo_norm and (nome_alvo_norm in texto_norm or _partial_name_match(nome_alvo_norm, texto_norm)):
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
                                clickable = driver.execute_script(
                                    "return (arguments[0].closest && arguments[0].closest('button')) || arguments[0];",
                                    btn_seta
                                )
                                driver.execute_script('arguments[0].scrollIntoView({block: "center"});', clickable)
                                try:
                                    tname = getattr(clickable, 'tag_name', None)
                                except Exception:
                                    tname = None
                                if debug:
                                    try:
                                        logger.info(f"[DESTINATARIOS][DEBUG] Usando elemento clicavel: {tname}")
                                    except Exception:
                                        pass
                                for _ in range(qtd_cliques):
                                    time.sleep(0.3)
                                    driver.execute_script('arguments[0].click();', clickable)
                            except Exception:
                                try:
                                    for _ in range(qtd_cliques):
                                        btn_seta.click()
                                        time.sleep(0.2)
                                except Exception:
                                    pass
                        else:
                            if debug:
                                try:
                                    logger.info(f"[DESTINATARIOS][DEBUG] Nome correspondeu mas nenhuma seta encontrada para: {nome_alvo}")
                                except Exception:
                                    pass
                        if debug:
                            try:
                                logger.info(f"[DESTINATARIOS]  Parte selecionada via nome: {nome_alvo}")
                            except Exception:
                                pass
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
def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, cliques_informado=2, observacao=None, numero_processo=None, dados_processo=None):
    if log is None:
        def log(_msg): return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1
    qtd_informado = 2 if str(cliques_informado).strip().lower() in ('2', '2x') else 1

    def _selecionar_por_lista(lista_destinatarios, origem_log, fallback_polo_passivo=False, qtd_seta_override=None):
        selecionados = 0
        
        # 1. GARANTE ABERTURA DO PAINEL E AGUARDA O RENDER DO PJE (CRÍTICO)
        try:
            _clicar_polo_passivo(driver, log)
            time.sleep(1) # Aguarda animação e lazy loading das linhas do painel
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao expandir Polo Passivo: {e}')

        qtd_cliques = qtd_seta_override if qtd_seta_override is not None else qtd_seta

        if not lista_destinatarios:
            log(f'[DESTINATARIOS][WARN] Lista de destinatários vazia ({origem_log})')
            if fallback_polo_passivo:
                _clicar_botao_polo_passivo(driver, log)
                log('[DESTINATARIOS] Fallback polo passivo aplicado')
            return 0

        for dest in lista_destinatarios:
            # 2. PADRONIZA AS CHAVES DO DICIONÁRIO (Cache vs Informado)
            info_padrao = dest
            if isinstance(dest, dict):
                nome = dest.get('nome') or dest.get('nome_oficial') or dest.get('nome_identificado')
                doc = dest.get('cpfcnpj') or dest.get('cpfCnpj') or dest.get('documento')
                
                info_padrao = {
                    'nome_alvo': nome,
                    'nome_oficial': nome,
                    'documento': doc,
                    'documento_normalizado': re.sub(r'\D', '', str(doc)) if doc else ''
                }

            try:
                if selecionar_destinatario_por_documento(driver, info_padrao, debug=debug, qtd_cliques=qtd_cliques):
                    selecionados += 1
                    time.sleep(0.3)
            except Exception as e:
                log(f'[DESTINATARIOS][ERRO] Exceção ao tentar selecionar {info_padrao.get("nome_alvo")} : {e}')

        # 3. VERIFICAÇÃO FINAL E FALLBACK
        if selecionados == 0:
            log(f'[DESTINATARIOS][WARN] Nenhum destinatário selecionado ({origem_log})')
            if fallback_polo_passivo:
                _clicar_botao_polo_passivo(driver, log)
                log('[DESTINATARIOS] Fallback polo passivo aplicado (botão geral)')
        else:
            log(f'[DESTINATARIOS] {selecionados} destinatário(s) selecionado(s) via {origem_log}')
            
        return selecionados

    # ================= ROTEAMENTO PRINCIPAL =================

    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')

    elif isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        # Agora a lista explícita também garante a expansão do painel antes da busca
        _selecionar_por_lista(destinatarios, 'lista explícita', fallback_polo_passivo=True)

    elif destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            _selecionar_por_lista(lista_destinatarios, 'cache', fallback_polo_passivo=True, qtd_seta_override=2)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')

    elif destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: cruzando observação com dados do processo')
        try:
            if not dados_processo:
                try:
                    from Fix.extracao_processo import extrair_dados_processo
                    dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                except Exception:
                    dados_processo = _carregar_dadosatuais_local('dadosatuais.json')

            candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo)
            _selecionar_por_lista(candidatos, 'observação', fallback_polo_passivo=False, qtd_seta_override=qtd_informado)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')

    elif destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO: Clicando no polo ativo')
        try:
            btn_polo_ativo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloAtivo"]'))
            )
            driver.execute_script("arguments[0].click();", btn_polo_ativo)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')

    elif destinatarios in ('polo_passivo', 'polo_passivo_2x'):
        cliques = cliques_polo_passivo if destinatarios == 'polo_passivo' else 2
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques}x)')
        try:
            btn_polo_passivo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]'))
            )
            for i in range(cliques):
                driver.execute_script("arguments[0].click();", btn_polo_passivo)
                if i < cliques - 1: time.sleep(2)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')

    elif destinatarios == 'terceiros':
        log('[DESTINATARIOS] OPÇÃO TERCEIROS: Clicando em terceiros interessados')
        try:
            try:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]'))
                )
            except Exception:
                btn_terceiro = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-user.pec-polo-outros-partes-processo'))
                )
            driver.execute_script("arguments[0].click();", btn_terceiro)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar terceiros: {e}')
    else:
        log('[DESTINATARIOS] OPÇÃO PADRÃO: Clicando no polo passivo (1x)')
        try:
            btn_polo_passivo = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]'))
            )
            driver.execute_script("arguments[0].click();", btn_polo_passivo)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo padrão: {e}')

    if terceiro:
        log('[DESTINATARIOS] FLAG terceiro=True: Adicionando terceiros interessados')
        try:
            btn_terceiro = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]'))
            )
            driver.execute_script("arguments[0].click();", btn_terceiro)
        except Exception as e:
            log(f'[DESTINATARIOS][WARN] Falha ao adicionar terceiros: {e}')

    return True
