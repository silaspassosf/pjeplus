from .core import *
from .wrappers_utils import executar_visibilidade_sigilosos_se_necessario
from Fix.utils import executar_coleta_parametrizavel, inserir_link_ato_validacao
from Fix.extracao import criar_gigs

from typing import Optional, Tuple, Dict, List, Union, Callable
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

# Tentativa segura de importar helpers do pacote PEC.anexos
try:
    from PEC import anexos as pec_anexos
    _PEC_HELPERS_AVAILABLE = True
except Exception:
    pec_anexos = None
    _PEC_HELPERS_AVAILABLE = False


def comunicacao_judicial(
    driver: WebDriver,
    tipo_expediente,
    prazo,
    nome_comunicacao,
    sigilo,
    modelo_nome,
    subtipo=None,
    descricao=None,
    tipo_prazo='dias uteis',
    gigs_extra=None,
    coleta_conteudo=None,  # NOVO: parâmetro para coleta de conteúdo parametrizável
    inserir_conteudo=None,  # NOVO: função opcional para inserção no editor
    cliques_polo_passivo=1,  # NOVO: número de cliques no polo passivo (padrão 1)
    destinatarios=None,  # NOVO: seleção de destinatários: None = não atuar (usar padrão do sistema)
    # NOVOS: controle de ações opcionais no fluxo
    mudar_expediente=None,  # quando True executa a troca/seleção do tipo de expediente
    checar_sp=None,         # quando True executa a checagem/remocao de destinatários com ícone vermelho
    endereco_tipo=None,     # NOVO: tipo de endereço ('correios' para mudar para correios)
    usar_otimizado=False,   # NOVO: Usar função otimizada de preenchimento (baseada em a.py)
    debug=False,
    terceiro=False
):
    """
    Fluxo generalizado para qualquer comunicação processual.
    Ordem de execução:
    0. Coleta de conteúdo parametrizável (PRIMEIRO PASSO - na aba /detalhe)
    1. Abrir tarefa do processo
    2. Comunicações e expedientes
    3. Preenchimento de formulário
    4. Seleção de destinatários
    5. Salvamento
    """
    def log(msg):
        print(f'[COMUNICACAO] {msg}')
        if debug:
            time.sleep(0.5)
            
    # Imports necessários para seleção de destinatários
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    import re
    import unicodedata
    from selenium.webdriver.common.keys import Keys

    def normalizar_string(valor):
        if not valor:
            return ''
        valor_norm = unicodedata.normalize('NFD', str(valor))
        valor_norm = ''.join(ch for ch in valor_norm if unicodedata.category(ch) != 'Mn')
        return valor_norm.lower()

    def selecionar_destinatario_por_documento(destinatario_info):
        if isinstance(destinatario_info, dict):
            documento_alvo = destinatario_info.get('documento')
            doc_normalizado = destinatario_info.get('documento_normalizado')
            nome_alvo = destinatario_info.get('nome_oficial') or destinatario_info.get('nome_identificado')
        else:
            documento_alvo = doc_normalizado = nome_alvo = None

        doc_digits = re.sub(r'\D', '', doc_normalizado or documento_alvo or '')

        # ✅ CORREÇÃO: Buscar partes na estrutura correta do painel expandido
        try:
            # Primeiro tenta na estrutura do painel expandido (para destinatários extraídos)
            linhas = WebDriverWait(driver, 10).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row')
            )
        except Exception:
            # Fallback para estrutura antiga (mat-row)
            linhas = driver.find_elements(By.CSS_SELECTOR, 'mat-row, .pec-partes-polo li, ul.sem-padding li')

        # Primeiro coletar candidatos que contenham o documento
        candidatos = []
        for linha in linhas:
            try:
                texto_linha = linha.text or ''
                texto_normalizado = re.sub(r'\D', '', texto_linha)
                if doc_digits and doc_digits in texto_normalizado:
                    candidatos.append((linha, texto_linha))
            except Exception:
                continue

        # Se houver candidatos, escolhemos o melhor pela presença do nome (campo .nome-parte) e proximidade
        if candidatos:
            nome_alvo_norm = normalizar_string(nome_alvo) if nome_alvo else ''
            best = None
            best_score = -1
            for linha, texto_linha in candidatos:
                try:
                    score = 0
                    # Documento já garante base alta
                    score += 20

                    # Tentar obter o nome visível específico da linha (se existir .nome-parte)
                    nome_span = None
                    try:
                        nome_span = linha.find_element(By.CSS_SELECTOR, '.nome-parte, .nome-tipo-parte, .pec-formatacao-padrao-dados-parte.nome-parte')
                    except Exception:
                        nome_span = None

                    if nome_span:
                        nome_linha = normalizar_string(nome_span.text or '')
                        # Se houver correspondência exata (nome extraído == nome da linha), pontua alto
                        if nome_alvo_norm and nome_linha == nome_alvo_norm:
                            score += 40
                        elif nome_alvo_norm and nome_alvo_norm in nome_linha:
                            score += 15
                    else:
                        # Fallback: verificar presença do nome no texto da linha
                        if nome_alvo_norm and nome_alvo_norm in normalizar_string(texto_linha):
                            score += 10

                    # Proximidade simples: posição do documento no texto e do nome (em texto normalizado)
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

                    # Penalizar se o texto da linha contém indicadores de representante (advogado) quando nome alvo é pessoa física
                    if 'advogado' in texto_linha.lower() and nome_alvo_norm and len(nome_alvo_norm.split()) >= 2:
                        # não penaliza muito, apenas reduz preferência
                        score -= 2

                    if score > best_score:
                        best_score = score
                        best = linha
                except Exception:
                    # não abortar todo o loop por erro numa linha
                    continue

            if best is not None:
                # tentar encontrar o botão na linha escolhida
                seletores_seta = [
                    'button[mattooltip*="acrescentar"]',
                    'button[aria-label*="acrescentar"]',
                    'button .fa-arrow-circle-down',
                    'button[mat-icon-button]',
                    'button mat-icon-button'
                ]
                btn_seta = None
                for seletor in seletores_seta:
                    try:
                        btn_seta = best.find_element(By.CSS_SELECTOR, seletor)
                        break
                    except Exception:
                        continue
                if btn_seta:
                    driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn_seta)
                    time.sleep(0.3)
                    driver.execute_script('arguments[0].click();', btn_seta)
                    log(f"[DESTINATARIOS] ✓ Parte selecionada via documento (melhor candidato): {documento_alvo}")
                    return True

        # Se não achou por documento, tenta por nome (fallback)
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
                            try:
                                btn_seta = linha.find_element(By.CSS_SELECTOR, seletor)
                                break
                            except Exception:
                                continue
                        if btn_seta:
                            driver.execute_script('arguments[0].scrollIntoView({block: "center"});', btn_seta)
                            time.sleep(0.3)
                            driver.execute_script('arguments[0].click();', btn_seta)
                            log(f"[DESTINATARIOS] ✓ Parte selecionada via nome: {nome_alvo}")
                            return True
                except Exception:
                    continue

        log(f"[DESTINATARIOS][WARN] Não foi possível incluir parte: {nome_alvo or documento_alvo}")
        return False
            
    try:
        # 0. PRIMEIRO: Executar coleta de conteúdo parametrizável na aba /detalhe (se especificado)
        if coleta_conteudo:
            log('Executando coleta de conteúdo parametrizável ANTES do fluxo principal...')
            try:
                # Verifica se está na aba /detalhe
                current_url = driver.current_url
                if '/detalhe' not in current_url:
                    log(f'[COLETA][WARN] URL atual não contém /detalhe: {current_url}')
                    log('[COLETA][WARN] Coleta deve ser executada na aba /detalhe')
                    
                # Importa a função do módulo de coleta
                
                # Se coleta_conteudo for string, converte para dict simples
                if isinstance(coleta_conteudo, str):
                    config_coleta = {'tipo': coleta_conteudo}
                else:
                    config_coleta = coleta_conteudo
                
                # Extrai parâmetros
                tipo_coleta = config_coleta.get('tipo', '')
                parametros = config_coleta.get('parametros', None)
                
                # Tenta extrair número do processo da URL atual
                try:
                    from PEC.anexos import extrair_numero_processo_da_url
                    numero_processo = extrair_numero_processo_da_url(driver)  # Passa o driver, não a URL
                    if not numero_processo:
                        log('[COLETA][WARN] Número do processo não encontrado na URL')
                        numero_processo = "PROCESSO_DESCONHECIDO"
                except Exception as e:
                    log(f'[COLETA][ERRO] Erro na extração do número do processo: {e}')
                    numero_processo = "PROCESSO_DESCONHECIDO"
                
                # Executa a coleta
                sucesso_coleta = False
                # Se for coleta de link de ato, usar a lógica otimizada do fluxo P2B
                if tipo_coleta and tipo_coleta.lower() in ('link_ato', 'link_ato_validacao', 'link_ato_timeline'):
                    # Primeiro, tente obter o link de validação via API (Fix.variaveis) - API-first
                    try:
                        from Fix.variaveis import session_from_driver, PjeApiClient, obter_chave_ultimo_despacho_decisao_sentenca
                        sess_tmp, trt_tmp = session_from_driver(driver)
                        client_tmp = PjeApiClient(sess_tmp, trt_tmp)
                        # ✅ NOVO: Passar driver para filtro de "Comunique-se por edital"
                        link_validacao = obter_chave_ultimo_despacho_decisao_sentenca(client_tmp, str(numero_processo), driver=driver)
                        log(f"[COLETA][VARIAVEIS] link do último despacho/decisão/sentença: {link_validacao}")
                    except Exception as e_var:
                        log(f"[COLETA][VARIAVEIS][WARN] falha ao obter link via Fix.variaveis: {e_var}")
                        link_validacao = None

                    # Se obtivemos um link via API, salvamos diretamente no clipboard interno e pulamos o DOM
                    if link_validacao:
                        try:
                            # normalizar para URL completa se a função retornar apenas a chave
                            if not str(link_validacao).lower().startswith('http'):
                                base = trt_tmp
                                if not base.startswith('http'):
                                    base = 'https://' + base
                                link_validacao = f"{base}/pjekz/validacao/{link_validacao}?instancia=1"

                            from PEC.anexos import salvar_conteudo_clipboard
                            sucesso_coleta = salvar_conteudo_clipboard(
                                conteudo=link_validacao,
                                numero_processo=str(numero_processo),
                                tipo_conteudo=f"link_ato_validacao",
                                debug=debug
                            )
                            if sucesso_coleta:
                                log('[COLETA] Link de validação salvo no clipboard interno (via Fix.variaveis)')
                            else:
                                log('[COLETA][WARN] salvar_conteudo_clipboard retornou False (mas prosseguindo)')
                                sucesso_coleta = True
                        except Exception as e_clip:
                            log(f"[COLETA][VARIAVEIS][WARN] Falha ao salvar via PEC.anexos: {e_clip}")
                            # Considerar como sucesso lógico (link obtido) mesmo que persistência falhe
                            sucesso_coleta = True

                    # Se não obtemos link via API, fazer fallback ao método baseado em DOM/timeline
                    if not sucesso_coleta:
                        log('[COLETA] API não retornou link - usando _encontrar_documento_relevante (DOM) como fallback')
                        try:
                            from Prazo.p2b_fluxo_helpers import _encontrar_documento_relevante
                            doc_encontrado, doc_link, doc_idx = _encontrar_documento_relevante(driver)
                            if doc_link:
                                try:
                                    driver.execute_script('arguments[0].scrollIntoView(true);', doc_link)
                                    time.sleep(0.5)
                                    driver.execute_script('arguments[0].click();', doc_link)
                                    time.sleep(1)
                                except Exception:
                                    # clicar pode falhar, mas tentaremos extrair via script mesmo assim
                                    pass

                                # Tentar extrair link de validação diretamente do DOM expandido (mesma técnica que Fix.utils)
                                try:
                                    link_validacao_dom = driver.execute_script("""
                                        var spans = document.querySelectorAll('div[style="display: block;"] span');
                                        for (var i = 0; i < spans.length; i++) {
                                            var text = spans[i].textContent.trim();
                                            if (text.includes('Número do documento:')) {
                                                var numero = text.split('Número do documento:')[1].trim();
                                                if (numero) {
                                                    return 'https://pje.trt2.jus.br/pjekz/validacao/' + numero + '?instancia=1';
                                                }
                                            }
                                        }
                                        var links = document.querySelectorAll('a[href*="validacao"]');
                                        for (var i = 0; i < links.length; i++) {
                                            var href = links[i].getAttribute('href');
                                            if (href && href.includes('/validacao/')) {
                                                return href;
                                            }
                                        }
                                        return null;
                                    """)
                                except Exception as e_js:
                                    link_validacao_dom = None

                                if link_validacao_dom:
                                    try:
                                        from PEC.anexos import salvar_conteudo_clipboard
                                        sucesso_coleta = salvar_conteudo_clipboard(
                                            conteudo=link_validacao_dom,
                                            numero_processo=str(numero_processo),
                                            tipo_conteudo=f"link_ato_validacao",
                                            debug=debug
                                        )
                                        if sucesso_coleta:
                                            log('[COLETA] Link de validação salvo no clipboard interno (via DOM)')
                                    except Exception:
                                        sucesso_coleta = True
                                else:
                                    log('[COLETA] Não foi possível extrair link de validação via DOM expandido')
                                    sucesso_coleta = False
                            else:
                                log('[COLETA] _encontrar_documento_relevante não retornou link')
                                sucesso_coleta = False
                        except Exception as e_encontrar:
                            log(f'[COLETA][WARN] Falha ao usar _encontrar_documento_relevante: {e_encontrar}')
                            sucesso_coleta = False

                # Se não foi tratada pela rotina específica ou falhou, fallback para a coleta parametrizável existente
                if not sucesso_coleta:
                    sucesso_coleta = executar_coleta_parametrizavel(
                        driver, numero_processo, tipo_coleta, parametros, debug
                    )
                
                if sucesso_coleta:
                    log(f'✓ Coleta de "{tipo_coleta}" executada com sucesso ANTES do fluxo!')
                else:
                    log(f'⚠ Falha na coleta de "{tipo_coleta}" (mas continua o fluxo)')
                    
            except Exception as coleta_err:
                log(f'[ERRO] Erro na coleta de conteúdo: {coleta_err}')
                log('Continuando com o fluxo principal mesmo com erro na coleta...')
                # Não falha o fluxo principal por erro na coleta

        log('==========================================')
        log('Iniciando fluxo principal de comunicação processual...')

        # 1. NAVEGAÇÃO DIRETA POR URL - Otimização que elimina cliques de navegação
        log('[OTIMIZADO] Usando navegação direta por URL para maior eficiência...')
        
        try:
            # 1a. Extrair o ID do processo da URL atual (/detalhe)
            current_url = driver.current_url
            log(f'[URL] URL atual: {current_url}')
            
            # Usar regex para extrair o ID do processo da URL /detalhe
            import re
            match = re.search(r'/processo/(\d+)/detalhe', current_url)
            if not match:
                log('[ERRO] Não foi possível extrair ID do processo da URL /detalhe')
                raise Exception('ID do processo não encontrado na URL /detalhe')
            
            processo_id = match.group(1)
            log(f'[URL] ✓ ID do processo extraído: {processo_id}')
            
            # 1b. Construir URL direta para minutas
            url_minutas = f'https://pje.trt2.jus.br/pjekz/processo/{processo_id}/comunicacoesprocessuais/minutas'
            log(f'[URL] ✓ URL de minutas construída: {url_minutas}')
            
            # 1c. Abrir nova aba diretamente na URL de minutas usando JavaScript
            log('[URL] Abrindo nova aba diretamente na URL de minutas...')
            abas_antes = driver.window_handles
            driver.execute_script(f"window.open('{url_minutas}', '_blank');")
            
            # 1d. Aguardar nova aba abrir de forma ativa (mais rápido que sleep fixo)
            nova_aba = None
            for tentativa in range(15):  # 15 x 0.2s = 3s max
                time.sleep(0.2)
                abas_apos_abertura = driver.window_handles
                if len(abas_apos_abertura) > len(abas_antes):
                    nova_aba = abas_apos_abertura[-1]
                    if tentativa > 0:
                        log(f'[URL] Nova aba detectada após {(tentativa+1)*0.2:.1f}s')
                    break
            
            if not nova_aba:
                log('[URL][ERRO] Nova aba não foi aberta em 3s')
                raise Exception('Nova aba de minutas não abriu')
            
            # Trocar para a nova aba
            driver.switch_to.window(nova_aba)
            log('[URL] ✓ Foco trocado para nova aba de minutas')
            
            # VERIFICAÇÃO DE CARREGAMENTO: Detecta spinner e dá F5 se necessário
            if not aguardar_e_verificar_aba(driver, timeout_spinner=0.5, max_tentativas_reload=2, log=True):
                log('[URL][ERRO] Falha ao carregar nova aba (spinner persistente)')
                raise Exception('Página travou no carregamento (spinner)')
            
            # 1e. Verificar se carregou corretamente
            WebDriverWait(driver, 20).until(lambda d: '/minutas' in d.current_url)
            log('[URL] ✓ Página de minutas carregada com sucesso!')
            
            # 1f. Aguardar elementos da interface carregarem
            WebDriverWait(driver, 20).until(lambda d: 'Tipo de Expediente' in d.page_source or len(d.find_elements(By.TAG_NAME, 'button')) > 5)
            log('[URL] ✓ Interface de minutas carregada completamente')
            
        except Exception as url_error:
            log(f'[URL][ERRO] Falha na navegação direta por URL: {url_error}')
            log('[URL] Fazendo fallback para navegação tradicional por cliques...')
            
            # FALLBACK: Navegação tradicional por cliques (código original)
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from Fix.selectors_pje import BTN_TAREFA_PROCESSO
            
            abas_antes = set(driver.window_handles)
            btn_abrir_tarefa = aguardar_e_clicar(driver, BTN_TAREFA_PROCESSO, timeout=15)
            if not btn_abrir_tarefa:
                log('[ERRO CRÍTICO] Botão "Abrir tarefa do processo" não encontrado!')
                raise Exception('Botão tarefa do processo não encontrado')
            
            log('✓ Botão "Abrir tarefa do processo" clicado (fallback)')
            
            # Troca para nova aba
            nova_aba = None
            for _ in range(20):
                abas_depois = set(driver.window_handles)
                novas_abas = abas_depois - abas_antes
                if novas_abas:
                    nova_aba = novas_abas.pop()
                    break
                time.sleep(0.3)
            
            if nova_aba:
                driver.switch_to.window(nova_aba)
                log('[NAVEGAR] Foco trocado para nova aba da tarefa do processo.')
                
                # VERIFICAÇÃO DE CARREGAMENTO: Detecta spinner e dá F5 se necessário
                if not aguardar_e_verificar_aba(driver, timeout_spinner=0.5, max_tentativas_reload=2, log=True):
                    log('[NAVEGAR][ERRO] Falha ao carregar nova aba (spinner persistente)')
                    raise Exception('Página travou no carregamento (spinner)')
            
            # Aguardar tela de minutas carregar no fallback
            WebDriverWait(driver, 20).until(lambda d: '/minutas' in d.current_url or 'Tipo de Expediente' in d.page_source)
            log('[DEBUG] Tela de minutas carregada (fallback).')

        # 2. Interface de minutas carregada - prosseguir com preenchimento OTIMIZADO
        log('[OTIMIZADO] Prosseguindo com preenchimento otimizado do formulário...')
        try:
            # ============================================================================
            # PREENCHIMENTO OTIMIZADO - Baseado em a.py (JavaScript)
            # Funções auxiliares inline para máxima performance
            # ============================================================================
            
            def _preencher_input_js(seletor, valor):
                """Preenche input via JavaScript (otimizado conforme a.py)"""
                max_tentativas = 3
                for tentativa in range(1, max_tentativas + 1):
                    try:
                        # ✅ Aguardar elemento estar clicável (timeout reduzido para 3s)
                        elemento = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, seletor))
                        )
                        
                        # Scroll até o elemento para garantir visibilidade
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
                        time.sleep(0.3)
                        
                        # Garantir clique/foco como em a.py
                        try:
                            driver.execute_script("arguments[0].click();", elemento)
                        except Exception:
                            pass
                        
                        # Preencher usando mesma lógica do a.py (preencherInput)
                        driver.execute_script("""
                            var el = arguments[0];
                            var val = arguments[1];
                            window.focus();
                            el.focus();
                            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, val);
                            
                            // Disparar eventos conforme a.py
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                            el.dispatchEvent(new Event('dateChange', {bubbles: true}));
                            el.dispatchEvent(new Event('keyup', {bubbles: true}));
                            
                            // Simular Enter
                            var enterEvent = new KeyboardEvent('keydown', {
                                key: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true
                            });
                            el.dispatchEvent(enterEvent);
                            
                            el.blur();
                        """, elemento, str(valor))
                        
                        time.sleep(0.2)
                        log(f'[INPUT][OK] Campo {seletor} preenchido com "{valor}"')
                        return True
                        
                    except Exception as e:
                        if tentativa < max_tentativas:
                            log(f'[INPUT][AVISO] Tentativa {tentativa}/{max_tentativas} falhou para {seletor}, aguardando...')
                            time.sleep(0.4)
                        else:
                            # Não logar erro completo, apenas que falhou (para não poluir logs)
                            return False
                
                return False
            
            def _escolher_opcao_select_js(seletor_select, valor_desejado):
                """Escolhe opção em mat-select via JavaScript"""
                try:
                    select_el = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_select))
                    )
                    driver.execute_script("arguments[0].click();", select_el)
                    time.sleep(0.3)
                    
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-option[role="option"]'))
                    )
                    time.sleep(0.3)
                    
                    opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option[role="option"]')
                    valor_norm = normalizar_string(valor_desejado)
                    
                    for opcao in opcoes:
                        texto_opcao = opcao.get_attribute('innerText') or opcao.text or ''
                        texto_norm = normalizar_string(texto_opcao)
                        if valor_norm == texto_norm or valor_norm in texto_norm:
                            driver.execute_script("arguments[0].click();", opcao)
                            return True
                    return False
                except Exception as e:
                    log(f'[SELECT][ERRO] Falha ao selecionar {valor_desejado}: {e}')
                    return False
            
            def _clicar_radio_button_js(texto_label):
                """Clica em mat-radio-button pelo texto do label"""
                try:
                    radios = driver.find_elements(By.CSS_SELECTOR, 'mat-radio-button')
                    texto_norm = normalizar_string(texto_label)
                    
                    for radio in radios:
                        label = radio.get_attribute('innerText') or radio.text or ''
                        label_norm = normalizar_string(label)
                        if texto_norm in label_norm:
                            driver.execute_script("arguments[0].click();", radio)
                            return True
                    return False
                except Exception as e:
                    log(f'[RADIO][ERRO] Falha ao clicar radio {texto_label}: {e}')
                    return False

            # ============================================================================
            # FLUXO OTIMIZADO DE PREENCHIMENTO (equivalente a acao_bt_aaComunicacao do a.py)
            # ============================================================================

            # 1. SELECIONAR TIPO DE EXPEDIENTE (otimizado)
            log(f'1. Selecionando tipo de expediente: {tipo_expediente}')
            if not _escolher_opcao_select_js('mat-select[placeholder="Tipo de Expediente"]', tipo_expediente):
                log('[ERRO] Falha ao selecionar tipo de expediente')
                raise Exception('Falha ao selecionar tipo de expediente')
            
            # 2. SELECIONAR TIPO DE PRAZO (otimizado)
            log(f'2. Selecionando tipo de prazo: {tipo_prazo}')
            if prazo == "0" or prazo == 0:
                tipo_prazo = "sem prazo"
            
            if not _clicar_radio_button_js(tipo_prazo):
                log('[ERRO] Falha ao selecionar tipo de prazo')
                raise Exception(f'Tipo de prazo "{tipo_prazo}" não encontrado')
            
            # 3. PREENCHER PRAZO (otimizado com múltiplos seletores)
            if prazo and tipo_prazo != "sem prazo":
                log(f'3. Preenchendo prazo: {prazo}')
                tipo_prazo_norm = normalizar_string(tipo_prazo)
                
                # Determinar seletores a tentar baseado no tipo de prazo
                seletores_prazo = []
                if tipo_prazo_norm == 'dias uteis':
                    seletores_prazo = [
                        'input[aria-label="Prazo em dias úteis"]',
                        'input[placeholder*="dias úteis"]',
                        'mat-form-field input[type="number"]',
                        'input[formcontrolname="prazo"]'
                    ]
                elif tipo_prazo_norm == 'data certa':
                    seletores_prazo = [
                        'input[aria-label="Prazo em data certa"]',
                        'input[placeholder*="data"]',
                        'input[type="date"]'
                    ]
                elif tipo_prazo_norm == 'dias corridos':
                    seletores_prazo = [
                        'input[aria-label="Prazo em dias úteis"]',
                        'input[placeholder*="dias"]',
                        'mat-form-field input[type="number"]',
                        'input[formcontrolname="prazo"]'
                    ]
                
                # ✅ AGUARDAR o campo de prazo aparecer após seleção do radio
                # (Angular precisa renderizar o campo dinamicamente)
                campo_prazo_apareceu = False
                for tentativa_wait in range(1, 4):
                    try:
                        # Tentar encontrar qualquer um dos seletores possíveis
                        for seletor_test in seletores_prazo:
                            try:
                                WebDriverWait(driver, 2).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, seletor_test))
                                )
                                log(f'[OK] Campo de prazo apareceu: {seletor_test}')
                                campo_prazo_apareceu = True
                                break
                            except:
                                continue
                        
                        if campo_prazo_apareceu:
                            break
                        
                        if tentativa_wait < 3:
                            log(f'[WAIT] Campo de prazo ainda não visível, aguardando... (tentativa {tentativa_wait}/3)')
                            time.sleep(0.8)
                    except Exception as e:
                        log(f'[WAIT][ERRO] Erro ao aguardar campo: {e}')
                        time.sleep(0.5)
                
                if not campo_prazo_apareceu:
                    log('[AVISO] Campo de prazo não apareceu após aguardar, prosseguindo mesmo assim...')
                
                # Aguardar mais um pouco para estabilizar (campo precisa estar totalmente renderizado)
                time.sleep(0.6)
                
                # Tentar cada seletor até encontrar um que funcione
                prazo_preenchido = False
                for seletor in seletores_prazo:
                    if _preencher_input_js(seletor, prazo):
                        prazo_preenchido = True
                        break
                    time.sleep(0.3)
                
                if not prazo_preenchido:
                    log(f'[AVISO] Não foi possível preencher prazo com nenhum seletor, tentando fallback...')
                    # Fallback: tentar send_keys tradicional com wait
                    try:
                        input_prazo = WebDriverWait(driver, 5).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, 'mat-form-field input[type="number"]'))
                        )
                        input_prazo.clear()
                        input_prazo.send_keys(str(prazo))
                        log(f'[FALLBACK][OK] Prazo preenchido via send_keys')
                    except Exception as e:
                        log(f'[FALLBACK][ERRO] Falha no fallback: {e}')
            else:
                log('3. Sem prazo a preencher')
            
            # 4. CLICAR "CONFECCIONAR ATO AGRUPADO" (otimizado)
            log('4. Clicando "Confeccionar ato agrupado"')
            btn_confeccionar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Confeccionar ato agrupado"]'))
            )
            driver.execute_script("arguments[0].click();", btn_confeccionar)
            time.sleep(0.8)
            
            # 5. SELECIONAR SUBTIPO (otimizado)
            if subtipo:
                log(f'5. Selecionando subtipo: {subtipo}')
                tentativas_subtipo = 0
                sucesso_subtipo = False
                
                while tentativas_subtipo < 3 and not sucesso_subtipo:
                    try:
                        tentativas_subtipo += 1
                        log(f'[SUBTIPO] Tentativa {tentativas_subtipo}/3')
                        
                        # Aguardar input estar presente
                        input_subtipo = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-placeholder="Tipo de Documento"]'))
                        )
                        
                        # Focar e simular tecla Enter para abrir dropdown
                        driver.execute_script("""
                            var el = arguments[0];
                            el.focus();
                            el.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 13, which: 13, bubbles: true}));
                        """, input_subtipo)
                        
                        time.sleep(0.5)
                        
                        # Aguardar mat-options aparecerem
                        try:
                            WebDriverWait(driver, 3).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, 'mat-option'))
                            )
                        except:
                            # Se não abriu, tentar seta para baixo
                            driver.execute_script("""
                                var el = arguments[0];
                                el.focus();
                                el.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 40, which: 40, bubbles: true}));
                            """, input_subtipo)
                            time.sleep(0.5)
                            WebDriverWait(driver, 3).until(
                                EC.visibility_of_element_located((By.CSS_SELECTOR, 'mat-option'))
                            )
                        
                        # Buscar e clicar na opção correta
                        opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                        for opcao in opcoes:
                            if subtipo.lower() in (opcao.text or '').lower():
                                driver.execute_script("arguments[0].click();", opcao)
                                log(f'✓ Subtipo selecionado: {subtipo}')
                                sucesso_subtipo = True
                                break
                        
                        if not sucesso_subtipo and tentativas_subtipo < 3:
                            log('[SUBTIPO] Opção não encontrada, tentando novamente...')
                            # Fechar diálogo e reabrir
                            try:
                                btn_fechar = driver.find_element(By.CSS_SELECTOR, 'pje-pec-dialogo-ato a[mattooltip="Fechar"]')
                                driver.execute_script("arguments[0].click();", btn_fechar)
                                time.sleep(0.5)
                                btn_confeccionar = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Confeccionar ato agrupado"]')
                                driver.execute_script("arguments[0].click();", btn_confeccionar)
                                time.sleep(0.8)
                            except:
                                pass
                                
                    except Exception as e:
                        log(f'[SUBTIPO][WARN] Erro na tentativa {tentativas_subtipo}: {e}')
                        if tentativas_subtipo >= 3:
                            log(f'[SUBTIPO][ERRO] Falha ao selecionar subtipo após 3 tentativas')
            else:
                log('5. Sem subtipo para selecionar')
            
            # 6. PREENCHER DESCRIÇÃO (otimizado)
            desc_to_use = descricao if descricao else nome_comunicacao
            log(f'6. Preenchendo descrição: {desc_to_use}')
            if not _preencher_input_js('input[aria-label="Descrição"]', desc_to_use):
                log('[ERRO] Falha ao preencher descrição')
                raise Exception('Falha ao preencher descrição')
            
            # 7. MARCAR SIGILO (otimizado)
            if sigilo:
                log('7. Marcando sigilo')
                try:
                    input_sigilo = driver.find_element(By.CSS_SELECTOR, 'input[name="sigiloso"]')
                    if not input_sigilo.is_selected():
                        driver.execute_script("arguments[0].click();", input_sigilo)
                        log('✓ Sigilo marcado')
                except Exception as e:
                    log(f'[WARN] Falha ao marcar sigilo: {e}')
            else:
                log('7. Sem sigilo')
            
            # 8. SELECIONAR MODELO (otimizado)
            if modelo_nome:
                log(f'8. Selecionando modelo: {modelo_nome}')
                try:
                    # Aguardar campo de filtro estar presente
                    campo_filtro = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'input#inputFiltro'))
                    )
                    
                    # Trigger events no campo vazio primeiro (como no a.py)
                    driver.execute_script("""
                        var el = arguments[0];
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('keyup', {bubbles: true}));
                    """, campo_filtro)
                    
                    time.sleep(0.3)
                    
                    # Preencher filtro de modelo via JS
                    driver.execute_script("""
                        var el = arguments[0];
                        var val = arguments[1];
                        el.value = '';
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                        el.dispatchEvent(new Event('keyup', {bubbles: true}));
                        el.value = val;
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                        el.dispatchEvent(new Event('keyup', {bubbles: true}));
                        el.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 13, which: 13, bubbles: true}));
                    """, campo_filtro, modelo_nome)
                    
                    time.sleep(1.5)
                    
                    # Aguardar e clicar no nodo filtrado
                    try:
                        nodo = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, '.nodo-filtrado'))
                        )
                        driver.execute_script("arguments[0].click();", nodo)
                        time.sleep(0.5)
                        
                        # Clicar no botão inserir modelo
                        btn_inserir = WebDriverWait(driver, 8).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'pje-dialogo-visualizar-modelo button'))
                        )
                        driver.execute_script("arguments[0].click();", btn_inserir)
                        log('✓ Modelo inserido')
                        time.sleep(1.0)
                    except Exception as e_nodo:
                        log(f'[MODELO][ERRO] Modelo "{modelo_nome}" não encontrado ou não foi possível inserir: {e_nodo}')
                        raise Exception(f'Modelo não encontrado: {modelo_nome}')
                    
                except Exception as e:
                    log(f'[ERRO] Falha ao inserir modelo: {e}')
                    raise
                
                # Hook de inserção de conteúdo (se fornecido)
                try:
                    if inserir_conteudo:
                        log('[INSERIR] Executando função de inserção de conteúdo...')
                        inserir_fn = inserir_conteudo
                        if isinstance(inserir_conteudo, str):
                            try:
                                if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                                    inserir_fn = inserir_link_ato_validacao
                                elif inserir_conteudo.lower() in ('conteudo_formatado', 'transcricao'):
                                    from Fix.utils import inserir_conteudo_formatado
                                    inserir_fn = inserir_conteudo_formatado
                            except Exception as _e:
                                log(f"[INSERIR][WARN] Não foi possível resolver função por string: {inserir_conteudo} -> {_e}")
                        
                        try:
                            from PEC.anexos import extrair_numero_processo_da_url
                            numero_processo_atual = extrair_numero_processo_da_url(driver)
                        except Exception:
                            numero_processo_atual = None
                        
                        ok = False
                        try:
                            ok = inserir_fn(driver=driver, numero_processo=numero_processo_atual, debug=debug)
                        except TypeError:
                            try:
                                ok = inserir_fn(driver, numero_processo_atual)
                            except Exception:
                                ok = inserir_fn(driver)
                        log(f"[INSERIR] Resultado da inserção: {'✓' if ok else '✗'}")
                except Exception as e:
                    log(f"[INSERIR][WARN] Erro ao executar inserção: {e}")
            else:
                log('8. Sem modelo para inserir')
            
            # 9. SALVAR E FINALIZAR (otimizado)
            log('9. Salvando e finalizando minuta')
            try:
                # Salvar
                btn_salvar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salvar"]'))
                )
                driver.execute_script("arguments[0].click();", btn_salvar)
                log('✓ Botão Salvar clicado')
                time.sleep(1.0)
                
                # Finalizar
                btn_finalizar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Finalizar minuta"]'))
                )
                driver.execute_script("arguments[0].click();", btn_finalizar)
                log('✓ Botão Finalizar minuta clicado')
                time.sleep(2.0)
                
                log('✅ Comunicação criada com sucesso!')
                
            except Exception as e:
                log(f'[SALVAR][ERRO] Falha ao salvar/finalizar: {e}')
                raise
        
        except Exception as e:
            log(f'[ERRO] Falha no fluxo de preenchimento otimizado: {e}')
            raise
        
        # 3. SELEÇÃO DE DESTINATÁRIOS - SIMPLIFICADO (3 opções apenas)
        if destinatarios is None:
            log('[DESTINATARIOS] Parâmetro None - pulando seleção')
        
        elif destinatarios == 'polo_ativo':
            # OPÇÃO 3: POLO ATIVO - 1 clique
            log('[DESTINATARIOS] OPÇÃO 3: Clicando no polo ativo (1x)')
            try:
                btn_polo_ativo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloAtivo"]'))
                )
                driver.execute_script("arguments[0].click();", btn_polo_ativo)
                log('[DESTINATARIOS] ✅ Polo ativo selecionado')
            except Exception as e:
                log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')
        
        elif destinatarios == 'polo_passivo_2x':
            # OPÇÃO 2: POLO PASSIVO com 2 cliques e intervalo de 2s
            log('[DESTINATARIOS] OPÇÃO 2: Clicando no polo passivo (2x com intervalo 2s)')
            try:
                btn_polo_passivo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]'))
                )
                
                # Primeiro clique
                driver.execute_script("arguments[0].click();", btn_polo_passivo)
                log('[DESTINATARIOS] ✅ Polo passivo - primeiro clique')
                
                # Aguardar 2 segundos
                time.sleep(2)
                
                # Segundo clique
                driver.execute_script("arguments[0].click();", btn_polo_passivo)
                log('[DESTINATARIOS] ✅ Polo passivo - segundo clique')
                
            except Exception as e:
                log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo (2x): {e}')
        
        else:
            # OPÇÃO 1 (PADRÃO): POLO PASSIVO com 1 clique
            log('[DESTINATARIOS] OPÇÃO 1 (PADRÃO): Clicando no polo passivo (1x)')
            try:
                btn_polo_passivo = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomentePoloPassivo"]'))
                )
                driver.execute_script("arguments[0].click();", btn_polo_passivo)
                log('[DESTINATARIOS] ✅ Polo passivo selecionado')
            except Exception as e:
                log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')
        
        # Regra especial: terceiros interessados
        if terceiro:
            log('[DESTINATARIOS] FLAG terceiro=True: Adicionando terceiros interessados')
            try:
                btn_terceiro = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="btnIntimarSomenteTerceirosInteressados"]'))
                )
                driver.execute_script("arguments[0].click();", btn_terceiro)
                log('[DESTINATARIOS] ✅ Terceiros interessados adicionados')
            except Exception as e:
                log(f'[DESTINATARIOS][WARN] Falha ao adicionar terceiros: {e}')
        
        
        # OPÇÃO ESPECIAL: pec_excluiargos - primeiro destinatário
        elif destinatarios == 'primeiro':
            log('[DESTINATARIOS] OPÇÃO ESPECIAL: Primeiro destinatário (pec_excluiargos)')
            try:
                # Expandir painel Polo Passivo
                painel_header_xpath = '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]]'
                painel_header = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, painel_header_xpath)))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", painel_header)
                driver.execute_script("arguments[0].click();", painel_header)
                time.sleep(0.5)
                
                # Clicar na primeira seta do Polo Passivo
                primeira_seta = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//mat-expansion-panel[.//*[contains(text(), "Polo Passivo")]]//button[@aria-label="Clique para acrescentar esta parte à lista de destinatários de expedientes e comunicações."][1]'))
                )
                driver.execute_script("arguments[0].click();", primeira_seta)
                log('[DESTINATARIOS] ✅ Primeira seta (primeiro destinatário) clicada')
                time.sleep(1)
                
                # ✅ NOVO: Buscar e adicionar TRIBUNAL se necessário (pec_excluiargos)
                try:
                    log('[DESTINATARIOS] 3. Buscando tribunal nos endereços disponíveis...')
                    
                    # Verificar se formulário de consulta de endereços apareceu
                    try:
                        consulta_enderecos = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '.pec-consulta-enderecos'))
                        )
                        log('[DESTINATARIOS] 3a. Formulário de consulta de endereços detectado')
                    except Exception:
                        log('[DESTINATARIOS] 3a. Formulário de consulta de endereços não apareceu')
                        raise Exception('Consulta não apareceu')
                    
                    # Verificar se há snack-bar de "Nenhum resultado encontrado"
                    try:
                        snack_nenhum = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Nenhum resultado encontrado')]"))
                        )
                        log('[DESTINATARIOS] 3b. Snack-bar detectado: "Nenhum resultado encontrado" -> incluir tribunal via CEP')
                        
                        # Digitar CEP 01302906 no campo inputCep
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
                        log('[DESTINATARIOS] ✓ Opção do tribunal selecionada')
                        time.sleep(0.5)
                        
                        log('[DESTINATARIOS] 3e. Clicando no botão Salvar das alterações')
                        btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                        )
                        btn_salvar_alteracoes.click()
                        log('[DESTINATARIOS] ✓ Alterações salvas')
                        time.sleep(0.5)
                        
                        log('[DESTINATARIOS] 3f. Clicando no botão fechar para fechar endereços')
                        btn_fechar = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                        )
                        btn_fechar.click()
                        log('[DESTINATARIOS] ✓ Janela de endereços fechada')
                    except Exception:
                        # Se não houver snack-bar, procurar tribunal nas linhas da tabela
                        log('[DESTINATARIOS] 3b. Nenhum snack-bar - buscando tribunal na tabela de endereços')
                        try:
                            tabela_enderecos = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, 'table[name="Endereços do destinatário no sistema"]'))
                            )
                            
                            # Procura por linhas que contenham "TRIBUNAL" (case insensitive)
                            linhas_tribunal = driver.find_elements(By.XPATH, 
                                "//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tribunal')]")
                            
                            if linhas_tribunal:
                                log('[DESTINATARIOS] 3c. Encontrado endereço do tribunal, clicando na seta')
                                linha_tribunal = linhas_tribunal[0].find_element(By.XPATH, './ancestor::tr')
                                seta_tribunal = linha_tribunal.find_element(By.CSS_SELECTOR, 'button[aria-label="Selecionar endereço"]')
                                seta_tribunal.click()
                                log('[DESTINATARIOS] ✓ Endereço do tribunal selecionado')
                                time.sleep(0.5)
                                
                                log('[DESTINATARIOS] 3d. Clicando no botão fechar para fechar endereços')
                                btn_fechar = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                                )
                                btn_fechar.click()
                                log('[DESTINATARIOS] ✓ Janela de endereços fechada')
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
                                log('[DESTINATARIOS] ✓ Tribunal selecionado')
                                time.sleep(0.5)
                                
                                log('[DESTINATARIOS] 3f. Clicando em Salvar alterações')
                                btn_salvar_alteracoes = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Salva as alterações"]'))
                                )
                                btn_salvar_alteracoes.click()
                                log('[DESTINATARIOS] ✓ Alterações salvas')
                                time.sleep(0.5)
                                
                                log('[DESTINATARIOS] 3g. Fechando janela de endereços')
                                btn_fechar = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa.fa-window-close.btn-fechar'))
                                )
                                btn_fechar.click()
                                log('[DESTINATARIOS] ✓ Janela fechada')
                        except Exception as e:
                            log(f'[DESTINATARIOS] Erro ao processar endereços: {e}')
                except Exception as tribunal_err:
                    log(f'[DESTINATARIOS] Aviso: Não foi possível adicionar tribunal: {tribunal_err}')
                    
            except Exception as e:
                log(f'[DESTINATARIOS][ERRO] Falha ao selecionar primeiro destinatário: {e}')
        
        # 4. (CRITICO) Alterar meio de expedição IMEDIATAMENTE após selecionar destinatários, ANTES de salvar
        if mudar_expediente:
            try:
                log('[COMUNICACAO] ⚡ Alterando meio de expedição IMEDIATAMENTE (pós-seleção de destinatários, pré-salvamento)...')
                t0_expediente = time.perf_counter()
                
                # ABORDAGEM OTIMIZADA: Encontrar apenas linhas com "Domicílio Eletrônico" e alterar
                # Busca todas as linhas (tr) da tabela de destinatários
                linhas_tabela = driver.find_elements(By.CSS_SELECTOR, 'tbody.cdk-drop-list tr.cdk-drag')
                total_linhas = len(linhas_tabela)
                
                if total_linhas == 0:
                    log('[COMUNICACAO][WARN] Nenhuma linha de destinatário encontrada na tabela!')
                else:
                    log(f'[COMUNICACAO] Verificando {total_linhas} destinatário(s) para alterar meio de expedição')
                    
                    alterados = 0
                    pulados = 0
                    
                    for idx, linha in enumerate(linhas_tabela, 1):
                        try:
                            # Verificar o valor ATUAL do meio de expedição nesta linha
                            # Procura o span que contém o texto do meio selecionado
                            try:
                                span_meio = linha.find_element(By.CSS_SELECTOR, 'pje-pec-coluna-meio-expedicao .mat-select-value-text .mat-select-min-line')
                                meio_atual = span_meio.text.strip()
                            except:
                                log(f'[COMUNICACAO][WARN] Linha {idx}: Não foi possível ler meio de expedição atual')
                                continue
                            
                            # Se NÃO for "Domicílio Eletrônico", pular (não precisa alterar)
                            if 'Domicílio Eletrônico' not in meio_atual:
                                if debug:
                                    log(f'[COMUNICACAO] Linha {idx}: "{meio_atual}" - não precisa alterar')
                                pulados += 1
                                continue
                            
                            # É "Domicílio Eletrônico" - precisa alterar para "Correio"
                            log(f'[COMUNICACAO] Linha {idx}: Domicílio Eletrônico encontrado - alterando para Correio...')
                            
                            # Encontrar o mat-select DESTA linha específica
                            try:
                                dropdown = linha.find_element(By.CSS_SELECTOR, 'mat-select[placeholder="Meios de Expedição"]')
                            except:
                                log(f'[COMUNICACAO][WARN] Linha {idx}: Dropdown não encontrado')
                                continue
                            
                            # Scroll e clique no dropdown
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown)
                            time.sleep(0.1)
                            driver.execute_script("arguments[0].click();", dropdown)
                            time.sleep(0.4)
                            
                            # Aguardar opções aparecerem
                            try:
                                WebDriverWait(driver, 5).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-option'))
                                )
                            except:
                                log(f'[COMUNICACAO][WARN] Linha {idx}: Opções do dropdown não carregaram')
                                continue
                            
                            # Procurar e clicar na opção "Correio"
                            opcoes = driver.find_elements(By.CSS_SELECTOR, 'mat-option')
                            correio_clicado = False
                            for opcao in opcoes:
                                if 'Correio' in opcao.text:
                                    driver.execute_script("arguments[0].click();", opcao)
                                    log(f'[COMUNICACAO] ✓ Linha {idx}: Domicílio Eletrônico → Correio')
                                    alterados += 1
                                    correio_clicado = True
                                    time.sleep(0.3)
                                    break
                            
                            if not correio_clicado:
                                log(f'[COMUNICACAO][WARN] Linha {idx}: Opção "Correio" não encontrada nas opções')
                                # Fechar dropdown
                                try:
                                    from selenium.webdriver.common.keys import Keys
                                    dropdown.send_keys(Keys.ESCAPE)
                                except:
                                    pass
                                    
                        except Exception as e_linha:
                            log(f'[COMUNICACAO][WARN] Linha {idx}: Erro ao processar - {str(e_linha)[:60]}')
                            continue
                    
                    tempo_total = time.perf_counter() - t0_expediente
                    log(f'[COMUNICACAO] ✅ Alterados: {alterados} | Não precisavam: {pulados} | Total: {total_linhas} (tempo: {tempo_total:.3f}s)')
                        
            except Exception as e:
                log(f'[COMUNICACAO][WARN] Falha ao alterar meio de expedição para Correio: {e}')
                # Não raise, pois é opcional
        else:
            log('[DEBUG] mudar_expediente não ativado - mantendo expediente padrão')
        
        # 5. Aguardar carregamento após seleção de destinatários e troca de expediente
        time.sleep(3)
        
        # 6. Antes de salvar: remover destinatários com ícone vermelho (endereço inválido) - opcional
        if checar_sp:
            try:
                log('[COMUNICACAO] Verificando destinatários com ícone vermelho (endereço inválido)')
                try:
                    # Localiza todos os ícones vermelhos visíveis na tabela
                    red_icons = driver.find_elements(By.CSS_SELECTOR, '.pec-icone-vermelho-endereco-tabela-destinatarios')
                    removidos = 0
                    for ic in red_icons:
                        try:
                            # Subir até a linha correspondente (ancestor tr)
                            try:
                                row = ic.find_element(By.XPATH, './ancestor::tr[1]')
                            except Exception:
                                # fallback: procurar elemento pai até encontrar 'tr'
                                elem = ic
                                row = None
                                for _ in range(6):
                                    try:
                                        elem = elem.find_element(By.XPATH, './..')
                                        if elem.tag_name.lower() == 'tr':
                                            row = elem
                                            break
                                    except Exception:
                                        break
                                if row is None:
                                    continue

                            # Procurar botão de excluir (ícone trash) dentro da mesma linha
                            try:
                                btn_excluir = row.find_element(By.XPATH, ".//button[.//i[contains(@class,'fa-trash-alt')]]")
                                # Usar JS click para evitar interceptações
                                driver.execute_script('arguments[0].scrollIntoView(true);', btn_excluir)
                                time.sleep(0.2)
                                driver.execute_script('arguments[0].click();', btn_excluir)
                                removidos += 1
                                log(f'[COMUNICACAO] ✓ Destinatário com ícone vermelho removido (linha). Total removidos: {removidos}')
                                time.sleep(0.6)  # aguardar remoção da linha na UI
                            except Exception as ebtn:
                                log(f'[COMUNICACAO][WARN] Não encontrou botão de excluir na linha do ícone vermelho: {ebtn}')
                                continue
                        except Exception as einner:
                            log(f'[COMUNICACAO][WARN] Erro ao processar ícone vermelho: {einner}')
                            continue
                    if removidos == 0:
                        log('[COMUNICACAO] Nenhum destinatário com ícone vermelho encontrado')
                except Exception as echeck:
                    log(f'[COMUNICACAO][WARN] Falha ao varrer ícones vermelhos: {echeck}')
            except Exception as e:
                log(f'[COMUNICACAO][WARN] Erro inesperado na verificação de ícones vermelhos: {e}')
        else:
            log('[DEBUG] Pulando checagem/remocao de destinatários com ícone vermelho (parametro checar_sp não ativado)')

        # 7. Clicar em <span class="mat-button-wrapper">Salvar</span>
        try:
            btn_salvar_final = None
            spans = driver.find_elements(By.XPATH, "//span[contains(@class, 'mat-button-wrapper') and normalize-space(text())='Salvar']")
            for span in spans:
                btn = span.find_element(By.XPATH, './ancestor::button[1]')
                if btn.is_displayed() and btn.is_enabled():
                    btn_salvar_final = btn
                    break
            if not btn_salvar_final:
                log('[ERRO] Botão Salvar final não encontrado!')
                return False
            # Tentar clique resiliente usando helpers do Fix
            try:
                clicked = safe_click(driver, btn_salvar_final, log=debug)
            except Exception as _e_sc:
                clicked = False

            if not clicked:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", btn_salvar_final)
                    driver.execute_script('arguments[0].click();', btn_salvar_final)
                    clicked = True
                except Exception as e_click_final:
                    log(f'[ERRO] Não foi possível clicar no botão Salvar final (tentativa direta): {e_click_final}')
                    return False

            if clicked:
                log('[DEBUG] Clique no botão Salvar final realizado.')
        except Exception as e:
            log(f'[ERRO] Não foi possível clicar no botão Salvar final: {e}')
            return False
        time.sleep(1)

        # Aguarda salvamento ser processado
        time.sleep(2)
        log('[DEBUG] Aguardando processamento do salvamento...')

        # A criação de GIGS via minuta foi removida: GIGS deve ser criado ANTES
        # do fluxo, na aba de `detalhe`, usando a função `criar_gigs` (Fix.extracao).
        if gigs_extra:
            log('[GIGS_EXTRA][WARN] Criação de GIGS via minuta removida. Use criar_gigs na aba /detalhe antes do fluxo.')
        
        # Visibilidade sigilosa - MOVIDA para após salvamento completo
        if str(sigilo).lower() in ("sim", "true", "1"):
            try:
                log('[COMUNICACAO] Executando visibilidade_sigilosos após salvamento...')
                # Usa a função importada de wrappers_utils
                executar_visibilidade_sigilosos_se_necessario(driver, True, debug=debug)
                log('[COMUNICACAO] Visibilidade extra aplicada por sigilo positivo.')
            except Exception as e:
                log(f"[COMUNICACAO][ERRO] Falha ao aplicar visibilidade extra: {e}")
        
        log('Comunicação processual finalizada.')
        
        return True
    except Exception as e:
        log(f"[ERRO] Falha no fluxo de comunicação: {e}")
        # Tenta preservar contexto do browser em caso de erro
        try:
            current_handles = driver.window_handles
            if current_handles:
                # Usa primeira aba disponível se contexto ainda válido
                driver.switch_to.window(current_handles[0])
                log('[DEBUG] Contexto preservado usando primeira aba disponível após erro.')
            else:
                log('[ERRO] Contexto do browser completamente perdido.')
        except Exception as recovery_error:
            log(f"[ERRO] Contexto do browser perdido - impossível recuperar: {recovery_error}")
        return False


def make_comunicacao_wrapper(
    tipo_expediente, 
    prazo, 
    nome_comunicacao, 
    sigilo, 
    modelo_nome, 
    subtipo=None, 
    descricao=None,
    tipo_prazo='dias uteis',
    gigs_extra=None,
    coleta_conteudo=None,  # NOVO: parâmetro para coleta
    inserir_conteudo=None,  # NOVO: função opcional de inserção no editor
    cliques_polo_passivo=1,  # NOVO: número de cliques no polo passivo
    destinatarios='extraido',  # NOVO: seleção de destinatários
    # NOVOS: controle opcional de ações do fluxo
    mudar_expediente=None,
    checar_sp=None,
    endereco_tipo=None  # NOVO: tipo de endereço ('correios' para mudar para correios)
):
    def wrapper(driver, debug=False, **overrides):
        """
        Wrapper que aceita overrides genéricos e repassa quaisquer parâmetros fornecidos
        diretamente para `comunicacao_judicial`, tratando `mudar_expediente` como um
        parâmetro comum (como `descricao`, `prazo`, etc.).
        """
        # Resolve destinatários override explicitamente se presente
        destinatarios_param = overrides.get('destinatarios') if 'destinatarios' in overrides else destinatarios

        # Se o wrapper foi configurado com gigs_extra, executá-lo ANTES do início do fluxo
        if gigs_extra:
            try:
                if gigs_extra is True:
                    criar_gigs(driver, prazo, '', nome_comunicacao)
                elif isinstance(gigs_extra, (tuple, list)):
                    if len(gigs_extra) >= 3:
                        dias_uteis, responsavel, observacao = gigs_extra[:3]
                        criar_gigs(driver, dias_uteis, responsavel, observacao)
                    elif len(gigs_extra) == 2:
                        dias_uteis, observacao = gigs_extra
                        criar_gigs(driver, dias_uteis, '', observacao)
                    else:
                        criar_gigs(driver, gigs_extra)
                else:
                    criar_gigs(driver, gigs_extra)
            except Exception as e:
                try:
                    print(f'[GIGS_WRAPPER][ERRO] Falha ao executar criar_gigs antes do fluxo: {e}')
                except Exception:
                    pass

        # Construir kwargs a serem repassados para comunicacao_judicial
        call_kwargs = {
            'driver': driver,
            'tipo_expediente': tipo_expediente,
            'prazo': prazo,
            'nome_comunicacao': nome_comunicacao,
            'sigilo': sigilo,
            'modelo_nome': modelo_nome,
            'subtipo': overrides.get('subtipo', subtipo),
            'descricao': overrides.get('descricao', descricao if descricao else nome_comunicacao),
            'tipo_prazo': overrides.get('tipo_prazo', tipo_prazo),
            # Evitar repassar gigs_extra para não duplicar criação
            'gigs_extra': None,
            'coleta_conteudo': overrides.get('coleta_conteudo', overrides.get('coleta_conteudo_', coleta_conteudo)),
            'inserir_conteudo': overrides.get('inserir_conteudo', overrides.get('inserir_conteudo_', inserir_conteudo)),
            'cliques_polo_passivo': overrides.get('cliques_polo_passivo', cliques_polo_passivo),
            'destinatarios': destinatarios_param,
            # Passa adiante quaisquer flags de controle (mudar_expediente, checar_sp) diretamente
            'mudar_expediente': mudar_expediente,
            'checar_sp': overrides.get('checar_sp', overrides.get('checar_sp_', checar_sp)),
            'endereco_tipo': endereco_tipo,
            'debug': debug,
            'terceiro': overrides.get('terceiro', False)
        }

        return comunicacao_judicial(**call_kwargs)
    return wrapper

pec_bloqueio = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=7,
    nome_comunicacao='ciência bloqueio',
    sigilo=False,
    modelo_nome='xs dec reg',
    subtipo='Intimação',  # Subtipo igual ao tipo_expediente
    gigs_extra=(7, 'xs - carta'),
    destinatarios='extraido'
)
pec_decisao = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=10,
    nome_comunicacao='intimação de decisão',
    sigilo=False,
    modelo_nome='xs dec reg',
    subtipo='Intimação',  # Subtipo igual ao tipo_expediente
    # Criar GIGS na minuta (detalhe=False) -> usar tupla com 3 itens: (dias, responsavel, observacao)
    gigs_extra=(7, 'xs carta'),
    coleta_conteudo="link_ato",  # NOVO: Coleta automática de link da timeline
    inserir_conteudo='link_ato',  # NOVO: Insere link coletado no marcador '--'
    destinatarios='extraido'
)
pec_idpj = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=17,
    nome_comunicacao='defesa IDPJ',
    sigilo=False,
    modelo_nome='xidpj c',
    subtipo="Intimação",  # Adicionando subtipo explícito
    descricao="Intimação para manifestação sobre IDPJ",  # Descrição mais detalhada
    tipo_prazo='dias uteis',
    # Criar GIGS na minuta (detalhe=False)
    gigs_extra=(7, 'xs carta'),
    cliques_polo_passivo=2,  # ESPECIAL: pec_idpj precisa de 2 cliques no polo passivo
    destinatarios='extraido'
)
pec_editalidpj = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=15,
    nome_comunicacao='Defesa IDPJ',
    sigilo=False,
    modelo_nome='IDPJ (edital)',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)
pec_editaldec = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=8,
    nome_comunicacao='Decisão/Sentença',
    sigilo=False,
    modelo_nome='3Decisão (Edital)',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    coleta_conteudo="link_ato",  # NOVO: Coleta automática de link da timeline
    inserir_conteudo='link_ato',  # NOVO: Insere link coletado no marcador '--'
    destinatarios='extraido'  # CORRIGIDO: 'extraido' para selecionar destinatários do polo passivo
)
pec_cpgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado CP',
    sigilo=False,
    modelo_nome='mdd cp geral',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)

# ⚠️ pec_excluiargos centralizado em atos/wrappers_pec.py
# Importar de lá em vez de redefinir

pec_mddgeral = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=8,
    nome_comunicacao='Mandado',
    sigilo=False,
    modelo_nome='02 - gené',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)
pec_mddaud = make_comunicacao_wrapper(
    tipo_expediente='Mandado',
    prazo=1,
    nome_comunicacao='Mandado citação',
    sigilo=False,
    modelo_nome='xmdd aud',
    subtipo='Mandado',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)
pec_editalaud = make_comunicacao_wrapper(
    tipo_expediente='Edital',
    prazo=1,
    nome_comunicacao='Citação',
    sigilo=False,
    modelo_nome='1cit',
    subtipo='Edital',  # Subtipo igual ao tipo_expediente
    gigs_extra=None,
    destinatarios='extraido'
)
pec_sigilo = make_comunicacao_wrapper(
    tipo_expediente='Intimação',
    prazo=30,
    nome_comunicacao='ciência decisão',
    sigilo=True,
    modelo_nome='xdecsig',
    subtipo="Intimação",  # Adicionando subtipo explícito
    descricao="decisão sigilosa",
    destinatarios='polo_ativo'  # MODIFICADO: Define destinatário como polo ativo
)

# Novos wrappers solicitados: pec_ord e pec_sum
pec_ord = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zordd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None
)

pec_sum = make_comunicacao_wrapper(
    tipo_expediente='Notificação Inicial',
    prazo=5,
    nome_comunicacao='Notificação',
    sigilo=False,
    modelo_nome='zsumd',
    subtipo="Notificação",
    gigs_extra=None,
    destinatarios=None
)

# ====================================================
# BLOCO 3 - MOVIMENTOS (importado de mov.py)
# ====================================================
