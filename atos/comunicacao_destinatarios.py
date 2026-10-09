from typing import Optional, Callable, Any, Dict, List
from Fix.core import safe_click_no_scroll, esperar_elemento, wait_for_clickable, preencher_campo
from Fix.core import aguardar_renderizacao_nativa
from Fix.browser_suporte import click_headless_safe
from Fix.utils import normalizar_texto as normalizar_string
import re
import json
from Fix.log import log_seletor_multiplo, logger
from Fix import espera
from Play.pjeplay.locators import By


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


def _extrair_nomes_por_separador(observacao):
    """Extrai lista de nomes após o delimitador '>' na observação do GIGS.

    Formato esperado: '<prefixo> >nome1, nome2, ...'
    Ex.: 'xs mddid >murillo, silas' → ['murillo', 'silas']

    Retorna lista vazia se não houver '>' ou nenhum token válido após ele.
    """
    if not observacao or '>' not in observacao:
        return []
    _, _, parte_nomes = observacao.partition('>')
    nomes = [n.strip() for n in parte_nomes.split(',') if n.strip()]
    return [n for n in nomes if len(n) >= 2]


def _resolver_candidatos_via_api(driver, nomes_alvo, numero_processo=None, debug=False, log=None):
    """Confirma destinatários fazendo GET /pje-comum-api/api/processos/id/{id}/partes.

    Recebe nomes_alvo (lista de strings, ex: ['murillo', 'silas']) e retorna
    apenas as partes cujos nomes dão match com ao menos um token de nomes_alvo.
    Não usa DOM nem JSON local — apenas a API.

    Retorna lista de dicts no formato esperado por selecionar_destinatario_por_documento.
    """
    if log is None:
        def log(_msg): return None

    if not nomes_alvo:
        return []

    tokens_alvo = [
        _normalizar_nome_para_match(n)
        for n in nomes_alvo
        if n and len(n.strip()) >= 2
    ]
    if not tokens_alvo:
        return []

    try:
        from Fix.variaveis import PjeApiClient, session_from_driver
        sess = session_from_driver(driver)
        client = PjeApiClient(sess)

        # Resolver ID do processo a partir do número CNJ se necessário
        id_processo = None
        if numero_processo:
            try:
                id_processo = client.id_processo_por_numero(str(numero_processo))
            except Exception as e:
                log(f'[DESTINATARIOS][WARN] Falha ao resolver id_processo via API: {e}')

        if not id_processo:
            log('[DESTINATARIOS][WARN] id_processo não disponível — match via API ignorado')
            return []

        partes_raw = client.partes(str(id_processo))
        if not partes_raw:
            log('[DESTINATARIOS][WARN] API /partes retornou vazio')
            return []

        if debug:
            log(f'[DESTINATARIOS][DEBUG] API retornou {len(partes_raw)} parte(s); tokens alvo: {tokens_alvo}')

        candidatos = []
        vistos = set()
        for parte in partes_raw:
            nome = (parte.get('nome') or parte.get('nomeParte') or '').strip()
            doc = (
                parte.get('cpfCnpj') or parte.get('cpfcnpj')
                or parte.get('documento') or ''
            ).strip()
            polo = (parte.get('polo') or parte.get('tipoPolo') or '').lower()

            if not nome:
                continue

            nome_norm = _normalizar_nome_para_match(nome)
            tokens_nome = set(re.findall(r'[a-z0-9]+', nome_norm))

            # Match: ao menos um token do nome_alvo presente nos tokens do nome da parte
            matched_alvo = None
            for token_alvo in tokens_alvo:
                tokens_do_alvo = set(re.findall(r'[a-z0-9]+', token_alvo))
                if tokens_do_alvo & tokens_nome:  # interseção não vazia
                    matched_alvo = token_alvo
                    break

            if matched_alvo is None:
                if debug:
                    log(f'[DESTINATARIOS][DEBUG] Sem match: parte="{nome}" tokens={list(tokens_nome)}')
                continue

            chave = (nome_norm, re.sub(r'\D', '', doc))
            if chave in vistos:
                continue
            vistos.add(chave)

            log(f'[DESTINATARIOS] Match confirmado via API: "{nome}" (polo={polo or "?"})')
            candidatos.append({
                'nome_oficial': nome,
                'nome_identificado': matched_alvo,
                'documento': doc,
                'documento_normalizado': re.sub(r'\D', '', doc),
                'polo': polo,
            })

        if not candidatos:
            log(f'[DESTINATARIOS][WARN] Nomes {nomes_alvo} não encontrados nas partes via API — não é destinatário')

        return candidatos

    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha em _resolver_candidatos_via_api: {e}')
        return []


def _montar_destinatarios_por_observacao(observacao, dados_processo, debug=False):
    if not observacao or not isinstance(dados_processo, dict):
        return []

    texto_obs = _normalizar_nome_para_match(observacao)
    if not texto_obs:
        return []

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
        doc = (parte.get('cpfcnpj') or parte.get('cpfCnpj') or '').strip()
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
    try:
        # 1. Tentar via JS primeiro (mais rápido e checa aria-expanded/classe mat-expanded)
        if hasattr(driver, 'page') and driver.page:
            try:
                res = driver.page.evaluate("""() => {
                    const headers = Array.from(document.querySelectorAll('mat-expansion-panel-header'));
                    const headerPP = headers.find(h => (h.textContent || '').trim().toLowerCase().includes('polo passivo'));
                    if (!headerPP) return { ok: false, motivo: 'header_nao_encontrado' };
                    const panel = headerPP.closest('mat-expansion-panel');
                    const isExpanded = (headerPP.getAttribute('aria-expanded') === 'true') || 
                                       (panel && panel.classList.contains('mat-expanded'));
                    if (!isExpanded) {
                        headerPP.click();
                        return { ok: true, clicou: true };
                    }
                    return { ok: true, clicou: false };
                }""")
                if res and res.get('ok'):
                    if res.get('clicou'):
                        log('[DESTINATARIOS] Painel Polo Passivo expandido via clique no header')
                        espera.assentar(driver, 0.5)
                    else:
                        log('[DESTINATARIOS] Painel Polo Passivo já estava expandido')
                    return True
            except Exception as e_js:
                log(f'[DESTINATARIOS][DEBUG] Tentativa JS expandir Polo Passivo falhou: {e_js}')

        # 2. Fallback via XPath amplo
        xpath_header = '//mat-expansion-panel-header[contains(., "Polo Passivo")]'
        header = espera.elemento(driver, xpath_header, teto=3)
        if not header:
            header = espera.elemento(
                driver,
                '//mat-expansion-panel-header[.//div[contains(@class,"pec-titulo-painel-expansivel-partes-processo") and contains(normalize-space(.), "Polo Passivo")]]',
                teto=2
            )
        if not header:
            log('[DESTINATARIOS][ERRO] Header Polo Passivo não encontrado')
            return False

        aria_expanded = (header.get_attribute('aria-expanded') or '').strip().lower()
        if aria_expanded != 'true':
            safe_click_no_scroll(driver, header)
            espera.assentar(driver, 0.5)

        # aguardar conteúdo do painel (preferir observer nativo)
        try:
            aguardar_renderizacao_nativa(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', modo='aparecer', timeout=5)
        except Exception:
            esperar_elemento(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', timeout=5, by=By.CSS_SELECTOR)
        return True
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao expandir Polo Passivo: {e}')
        return False


def _clicar_e_aguardar_spinner(driver, btn, timeout_s=15):
    """Clica e aguarda loading do servidor (equivalente a clicarBotao(monitorar=true) do gigs-plugin).
    
    Fluxo puro (SEM sleeps fixos):
    1. Execute script click
    2. Aguarde spinner/dialog/modal sumir (observer nativo)
    3. Retorna quando DOM estiver pronto
    """
    import time
    safe_click_no_scroll(driver, btn)
    
    # Aguardar APENAS até spinner sumir — nenhum sleep fixo
    seletores_loading = (
        'mat-dialog-container, mat-progress-spinner, mat-progress-bar, '
        '.loading-spinner, .cdk-overlay-backdrop, .modal-backdrop'
    )
    aguardar_renderizacao_nativa(
        driver,
        seletores_loading,
        modo='sumir',
        timeout=timeout_s
    )


def _clicar_botao_polo_passivo(driver, log, qtd_cliques=1):
    try:
        for _ in range(qtd_cliques):
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                log('[DESTINATARIOS][ERRO] Botão polo passivo não clicável')
                return
            _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar no botão polo passivo (fallback): {e}')



# Seletores do botão "acrescentar parte" — ordenados por especificidade (Probe: button.icone-clicavel)
# O Probe confirmou: class="...icone-clicavel mat-icon-button mat-button-base..."
# button[mat-icon-button] fica por último: pega edit/delete também se mal-escoped
_SELETORES_BTN_ACRESCENTAR = [
    'button.icone-clicavel[mattooltip*="acrescentar"]',          # mais específico: classe + tooltip
    'button.icone-clicavel[aria-label*="acrescentar"]',          # classe + aria-label
    'button[mattooltip*="acrescentar"]',                          # só tooltip
    'button[aria-label*="acrescentar"]',                          # só aria-label
    'button[mattooltip*="Acrescentar"]',
    'button[aria-label*="Acrescentar"]',
    'button.mat-tooltip-trigger.mat-icon-button',                 # Probe PJe
    'button[aria-label="Clique para acrescentar esta parte à lista de destinatários de expedientes e comunicações."]',
    'button.icone-clicavel',                                      # fallback por classe
]


def _clicar_btn_acrescentar(driver, linha, qtd_cliques, debug=False):
    for _ in range(qtd_cliques):
        try:
            if hasattr(linha, '_js'):
                clicou = linha._js("""el => {
                    const seletores = [
                        'button[mattooltip="Clique para acrescentar esta parte à lista de destinatários de expedientes e comunicações."]',
                        'button.icone-clicavel[aria-label*="acrescentar"]',
                        'button[mattooltip*="acrescentar"]',
                        'button[aria-label*="acrescentar"]',
                        'button[aria-label="Clique para acrescentar esta parte à lista de destinatários de expedientes e comunicações."]',
                        'button.icone-clicavel'
                    ];
                    for (const sel of seletores) {
                        const btn = el.querySelector(sel);
                        if (btn) {
                            const clickable = btn.closest('button') || btn;
                            clickable.scrollIntoView({block: 'center'});
                            clickable.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                if not clicou:
                    return False
            else:
                return False
        except Exception:
            return False
    return True


def selecionar_destinatario_por_documento(driver, destinatario_info, debug=False, timeout=10, qtd_cliques=1):
    qtd_cliques = 2 if str(qtd_cliques).strip().lower() in ('2', '2x') else 1
    try:
        documento_alvo = None
        nome_alvo = None
        doc_normalizado = None
        if isinstance(destinatario_info, dict):
            documento_alvo = destinatario_info.get('documento') or destinatario_info.get('cpfcnpj') or destinatario_info.get('cpfCnpj')
            doc_normalizado = destinatario_info.get('documento_normalizado') or re.sub(r'\D', '', str(documento_alvo or ''))
            nome_alvo = (
                destinatario_info.get('nome_oficial')
                or destinatario_info.get('nome_identificado')
                or destinatario_info.get('nome')
            )

        doc_digits = re.sub(r'\D', '', doc_normalizado or documento_alvo or '')

        try:
            try:
                ok = aguardar_renderizacao_nativa(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', modo='aparecer', timeout=timeout)
            except Exception:
                ok = False
            linhas = espera.elementos(driver, '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row', teto=timeout)
        except Exception:
            linhas = espera.elementos(driver, 'mat-row, .pec-partes-polo li, ul.sem-padding li', teto=2)

        if doc_digits:
            candidatos = []
            for linha in linhas:
                try:
                    texto_linha = linha.text or ''
                    if doc_digits in re.sub(r'\D', '', texto_linha):
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
                        try:
                            texto_span = linha._js("el => (el.querySelector('.nome-parte, .nome-tipo-parte, .pec-formatacao-padrao-dados-parte.nome-parte') || {}).textContent || ''") if hasattr(linha, '_js') else ''
                            nome_linha = normalizar_string(texto_span)
                            if nome_alvo_norm and nome_linha == nome_alvo_norm:
                                score += 40
                            elif nome_alvo_norm and nome_alvo_norm in nome_linha:
                                score += 15
                        except Exception:
                            if nome_alvo_norm and nome_alvo_norm in normalizar_string(texto_linha):
                                score += 10

                        if 'advogado' in texto_linha.lower() and nome_alvo_norm and len(nome_alvo_norm.split()) >= 2:
                            score -= 2

                        if score > best_score:
                            best_score = score
                            best = linha
                    except Exception:
                        continue

                if best is not None:
                    if _clicar_btn_acrescentar(driver, best, qtd_cliques, debug=debug):
                        if debug:
                            logger.info(f"[DESTINATARIOS] Parte selecionada via documento: {documento_alvo}")
                        return {'status': 'ok', 'count': 1}

        # --- tentativa por nome ---
        if nome_alvo:
            nome_alvo_norm = normalizar_string(nome_alvo)
            for linha in linhas:
                try:
                    texto_norm = normalizar_string(linha.text or '')
                    if nome_alvo_norm and (nome_alvo_norm in texto_norm or _partial_name_match(nome_alvo_norm, texto_norm)):
                        if _clicar_btn_acrescentar(driver, linha, qtd_cliques, debug=debug):
                            if debug:
                                logger.info(f"[DESTINATARIOS] Parte selecionada via nome: {nome_alvo}")
                            return {'status': 'ok', 'count': 1}
                except Exception:
                    continue

        if debug:
            logger.info(f"[DESTINATARIOS][WARN] Não foi possível incluir parte: {nome_alvo or documento_alvo}")
        return {'status': 'empty', 'count': 0}
    except Exception as e:
        if debug:
            logger.info(f"[DESTINATARIOS][ERRO] {e}")
        return {'status': 'error', 'count': 0, 'details': str(e)}


def _selecionar_por_lista(driver, lista_destinatarios, origem_log, log, fallback_polo_passivo=False, qtd_seta_override=None, debug=False, qtd_cliques_fallback=1):
    selecionados = 0

    qtd_cliques = qtd_seta_override if qtd_seta_override is not None else 1

    if not lista_destinatarios:
        log(f'[DESTINATARIOS][WARN] Lista de destinatários vazia ({origem_log})')
        if fallback_polo_passivo:
            log(f'[DESTINATARIOS] Acionando fallback polo passivo ({qtd_cliques_fallback}x)')
            _clicar_botao_polo_passivo(driver, log, qtd_cliques_fallback)
            log(f'[DESTINATARIOS] Fallback polo passivo aplicado ({qtd_cliques_fallback}x)')
            return {'status': 'fallback', 'count': 0}
        return {'status': 'empty', 'count': 0}

    # APENAS abrir painel se houver items para selecionar
    try:
        _clicar_polo_passivo(driver, log)
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao expandir Polo Passivo: {e}')

    for dest in lista_destinatarios:
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
            res = selecionar_destinatario_por_documento(driver, info_padrao, debug=debug, qtd_cliques=qtd_cliques)
            if isinstance(res, dict) and res.get('status') == 'ok':
                selecionados += int(res.get('count', 1) or 1)
            elif res is True:
                selecionados += 1
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Exceção ao tentar selecionar {info_padrao.get("nome_alvo")} : {e}')

    if selecionados == 0:
        log(f'[DESTINATARIOS][WARN] Nenhum destinatário selecionado ({origem_log})')
        if fallback_polo_passivo:
            _clicar_botao_polo_passivo(driver, log, qtd_cliques_fallback)
            log(f'[DESTINATARIOS] Fallback polo passivo aplicado ({qtd_cliques_fallback}x) (botão geral)')
            return {'status': 'fallback', 'count': 0}
        return {'status': 'empty', 'count': 0}
    else:
        log(f'[DESTINATARIOS] {selecionados} destinatário(s) selecionado(s) via {origem_log}')
        return {'status': 'ok', 'count': selecionados}


def _incluir_tribunal_por_cep(driver, log, debug=False):
    try:
        campo_cep = wait_for_clickable(driver, 'input#inputCep', timeout=10)
        if not campo_cep:
            raise RuntimeError('Campo CEP não encontrado')
        preencher_campo(driver, 'input#inputCep', '01302906', limpar=True)
        espera.assentar(driver, 1)

        opcao_tribunal = wait_for_clickable(
            driver,
            "//span[@class='mat-option-text' and contains(text(), '01302-906')]",
            timeout=10
        )
        if not opcao_tribunal:
            raise RuntimeError('Opção tribunal não encontrada')
        safe_click_no_scroll(driver, opcao_tribunal, log=False)

        btn_salvar_alteracoes = wait_for_clickable(driver, 'button[aria-label="Salva as alterações"]', timeout=10)
        if btn_salvar_alteracoes:
            safe_click_no_scroll(driver, btn_salvar_alteracoes, log=False)

        btn_fechar = wait_for_clickable(driver, 'i.fa.fa-window-close.btn-fechar', timeout=10)
        if btn_fechar:
            safe_click_no_scroll(driver, btn_fechar, log=False)
        espera.assentar(driver, 0.5)
        return True
    except Exception as e:
        if debug:
            log(f'[DESTINATARIOS][WARN] Falha ao incluir tribunal via CEP: {e}')
        return False


def _selecionar_endereco_tribunal(driver, log, debug=False):
    try:
        if not esperar_elemento(driver, '.pec-consulta-enderecos', timeout=5):
            if debug:
                log('[DESTINATARIOS] Endereço do tribunal não solicitado após seleção do destinatário')
            return False
    except Exception as e:
        if debug:
            log(f'[DESTINATARIOS][WARN] Falha ao detectar painel de endereços: {e}')
        return False

    try:
        if esperar_elemento(driver, "//*[contains(text(), 'Nenhum resultado encontrado')]", timeout=3):
            log('[DESTINATARIOS] 3b. Nenhum resultado encontrado -> incluir tribunal via CEP')
            return _incluir_tribunal_por_cep(driver, log, debug=debug)
    except Exception:
        pass

    try:
        setas = espera.elementos(
            driver,
            "//tr[.//td[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tribunal')]]//button[@aria-label='Selecionar endereço']",
            teto=5
        )
        for seta in setas:
            try:
                safe_click_no_scroll(driver, seta, log=False)
                log('[DESTINATARIOS] ✓ Endereço do tribunal selecionado')
                btn_fechar = wait_for_clickable(driver, 'i.fa.fa-window-close.btn-fechar', timeout=10)
                if btn_fechar:
                    safe_click_no_scroll(driver, btn_fechar, log=False)
                espera.assentar(driver, 0.5)
                return True
            except Exception:
                continue
    except Exception:
        pass

    log('[DESTINATARIOS] 3c. Nenhum endereço do tribunal encontrado na tabela - incluindo tribunal via CEP')
    return _incluir_tribunal_por_cep(driver, log, debug=debug)


def selecionar_destinatarios(driver, destinatarios, terceiro=False, debug=False, log=None, cliques_polo_passivo=1, cliques_informado=2, observacao=None, numero_processo=None, dados_processo=None):
    from core.resultado_execucao import ResultadoExecucao
    if log is None:
        def log(_msg):
            return None

    qtd_seta = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1
    qtd_informado = 2 if str(cliques_informado).strip().lower() in ('2', '2x') else 1
    qtd_cliques_fallback = 2 if str(cliques_polo_passivo).strip().lower() in ('2', '2x') else 1

    # Variante 'informado_2' ou 'informado 2' → 2 cliques; normaliza para 'informado'
    if isinstance(destinatarios, str) and re.match(r'^informado[\s_]2$', destinatarios.strip(), re.I):
        destinatarios = 'informado'
        qtd_informado = 2

    # Roteamento principal
    if destinatarios is None:
        log('[DESTINATARIOS] Parâmetro None - pulando seleção')
        return ResultadoExecucao(sucesso=False, status='skip', detalhes={'count': 0})

    if isinstance(destinatarios, list):
        log('[DESTINATARIOS] Lista explícita recebida via override')
        return _selecionar_por_lista(driver, destinatarios, 'lista explícita', log, fallback_polo_passivo=True, qtd_seta_override=None, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)

    if destinatarios == 'extraido':
        log('[DESTINATARIOS] OPÇÃO EXTRAIDO: carregando destinatários em cache')
        try:
            from Fix.extracao_processo import carregar_destinatarios_cache
            cache = carregar_destinatarios_cache() or {}
            lista_destinatarios = cache.get('destinatarios', []) or []
            return _selecionar_por_lista(driver, lista_destinatarios, 'cache', log, fallback_polo_passivo=True, qtd_seta_override=2, debug=debug, qtd_cliques_fallback=qtd_cliques_fallback)
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo extraido: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'informado':
        log('[DESTINATARIOS] OPÇÃO INFORMADO: extraindo nomes via separador ">" e confirmando via API')
        try:
            # 1. Tentar extração precisa pelo separador '>'
            nomes_separador = _extrair_nomes_por_separador(observacao or '')

            if nomes_separador:
                log(f'[DESTINATARIOS] Nomes extraídos via ">": {nomes_separador}')
                candidatos = _resolver_candidatos_via_api(
                    driver,
                    nomes_separador,
                    numero_processo=numero_processo,
                    debug=debug,
                    log=log,
                )
            else:
                # 2. Fallback: modo tokens livres (comportamento legado) sobre dados_processo
                log('[DESTINATARIOS] Sem separador ">" — modo tokens livres (legado)')
                if not dados_processo:
                    try:
                        from Fix.extracao_processo import extrair_dados_processo
                        dados_processo = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=debug)
                    except Exception:
                        dados_processo = _carregar_dadosatuais_local('dadosatuais.json')
                candidatos = _montar_destinatarios_por_observacao(observacao, dados_processo, debug=debug)

            return _selecionar_por_lista(
                driver, candidatos, 'informado/api', log,
                fallback_polo_passivo=True,
                qtd_seta_override=qtd_informado,
                debug=debug,
                qtd_cliques_fallback=qtd_cliques_fallback,
            )
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios == 'polo_ativo':
        log('[DESTINATARIOS] OPÇÃO: Clicando no polo ativo')
        try:
            btn = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloAtivo"]', timeout=10, by=By.CSS_SELECTOR)
            if not btn:
                raise RuntimeError('Botão polo ativo não clicável')
            _clicar_e_aguardar_spinner(driver, btn)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo ativo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios in ('polo_passivo', 'polo_passivo_2x'):
        cliques = cliques_polo_passivo if destinatarios == 'polo_passivo' else 2
        log(f'[DESTINATARIOS] Clicando no polo passivo ({cliques}x)')
        try:
            btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=5, by=By.CSS_SELECTOR)
            if not btn_polo_passivo:
                raise RuntimeError('Botão polo passivo não clicável')
            for i in range(cliques):
                _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
                if i < cliques - 1:
                    btn_polo_passivo = espera.elemento(driver, 'button[name="btnIntimarSomentePoloPassivo"]', teto=2)
            return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    if destinatarios in ('terceiros', 'polo_passivo_e_terceiros', 'polo_passivo_terceiros'):
        log('[DESTINATARIOS] Modo Polo Passivo (1x) + Terceiros Interessados (pec_cpgeral)')
        polo_passivo_ok = False
        try:
            # 1. Clicar sempre no Polo Passivo (1x)
            btn_polo_passivo = wait_for_clickable(
                driver,
                'button[name="btnIntimarSomentePoloPassivo"]',
                timeout=10,
                by=By.CSS_SELECTOR
            )
            if btn_polo_passivo:
                _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
                polo_passivo_ok = True
                log('[DESTINATARIOS] Polo passivo (1x) adicionado com sucesso')
            else:
                log('[DESTINATARIOS][WARN] Botão polo passivo não clicável')
        except Exception as e_pp:
            log(f'[DESTINATARIOS][WARN] Erro ao intimar polo passivo: {e_pp}')

        # 2. Tentar intimar terceiros interessados (se houver; se não houver terceiros, não falha)
        terceiros_adicionados = False
        try:
            btn_terceiro = espera.elemento(
                driver,
                'button[name="btnIntimarSomenteTerceirosInteressados"]',
                teto=2
            )
            if not btn_terceiro:
                btn_terceiro = espera.elemento(
                    driver,
                    'i.fa.fa-user.pec-polo-outros-partes-processo',
                    teto=2
                )

            if btn_terceiro:
                is_disabled = False
                if hasattr(btn_terceiro, '_js'):
                    is_disabled = bool(btn_terceiro._js("""el => {
                        return el.disabled || 
                               el.getAttribute('aria-disabled') === 'true' || 
                               el.classList.contains('mat-button-disabled');
                    }"""))
                else:
                    aria_dis = btn_terceiro.get_attribute('aria-disabled') or ''
                    dis_attr = btn_terceiro.get_attribute('disabled')
                    is_disabled = bool(dis_attr or aria_dis == 'true')

                if not is_disabled:
                    log('[DESTINATARIOS] Botão terceiros interessados habilitado — clicando...')
                    _clicar_e_aguardar_spinner(driver, btn_terceiro)
                    terceiros_adicionados = True
                    log('[DESTINATARIOS] Terceiros interessados adicionados com sucesso')
                else:
                    log('[DESTINATARIOS] Botão terceiros interessados desabilitado (sem terceiros no processo) — prosseguindo com polo passivo')
            else:
                log('[DESTINATARIOS] Botão de terceiros interessados não encontrado — prosseguindo com polo passivo')
        except Exception as e_terc:
            log(f'[DESTINATARIOS][WARN] Falha ao tentar intimar terceiros (não fatal): {e_terc}')

        if polo_passivo_ok or terceiros_adicionados:
            return ResultadoExecucao(
                sucesso=True,
                status='geral',
                detalhes={
                    'count': 0,
                    'polo_passivo': polo_passivo_ok,
                    'terceiros': terceiros_adicionados
                }
            )
        else:
            log('[DESTINATARIOS][ERRO] Nem polo passivo nem terceiros puderam ser selecionados')
            return ResultadoExecucao(sucesso=False, status='error', erro='nenhum_destinatario_selecionado', detalhes={'count': 0})

    if destinatarios == 'primeiro':
        log('[DESTINATARIOS] OPCAO PRIMEIRO: expande Polo Passivo + seleciona primeiro destinatário (pec_excluiargos)')
        try:
            # 1. Expandir Polo Passivo de forma robusta
            _clicar_polo_passivo(driver, log)

            # Aguardar renderização das partes no painel
            aguardar_renderizacao_nativa(
                driver,
                '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row, mat-expansion-panel.mat-expanded button',
                modo='aparecer',
                timeout=5
            )

            # 2. Localizar e clicar no botão de acrescentar do primeiro destinatário do Polo Passivo
            clicado = False
            if hasattr(driver, 'page') and driver.page:
                try:
                    res_click = driver.page.evaluate("""() => {
                        const headers = Array.from(document.querySelectorAll('mat-expansion-panel-header'));
                        const headerPP = headers.find(h => (h.textContent || '').trim().toLowerCase().includes('polo passivo'));
                        if (!headerPP) return { ok: false, motivo: 'header_nao_encontrado' };
                        const panel = headerPP.closest('mat-expansion-panel');
                        if (!panel) return { ok: false, motivo: 'panel_nao_encontrado' };

                        const seletores = [
                            'button[mattooltip*="acrescentar"]',
                            'button[aria-label*="acrescentar"]',
                            'button[mattooltip*="Acrescentar"]',
                            'button[aria-label*="Acrescentar"]',
                            'button.mat-tooltip-trigger.mat-icon-button',
                            'button.icone-clicavel',
                            'button[mat-icon-button]'
                        ];

                        for (const sel of seletores) {
                            const botoes = Array.from(panel.querySelectorAll(sel));
                            const botoesCorpo = botoes.filter(b => !headerPP.contains(b));
                            if (botoesCorpo.length > 0) {
                                const primeiroBtn = botoesCorpo[0];
                                primeiroBtn.scrollIntoView({ block: 'center' });
                                primeiroBtn.click();
                                return { ok: true, seletor: sel };
                            }
                        }
                        return { ok: false, motivo: 'nenhum_botao_acrescentar_encontrado' };
                    }""")
                    if res_click and res_click.get('ok'):
                        clicado = True
                        log(f"[DESTINATARIOS] Primeira seta (primeiro destinatário) clicada via JS ({res_click.get('seletor')})")
                except Exception as e_click_js:
                    log(f'[DESTINATARIOS][DEBUG] Falha ao clicar primeiro destinatário via JS: {e_click_js}')

            if not clicado:
                # Fallback via seletores e click_headless_safe
                for sel_btn in _SELETORES_BTN_ACRESCENTAR:
                    xpath_seta = (
                        f'(//mat-expansion-panel[.//mat-expansion-panel-header[contains(., "Polo Passivo")]]'
                        f'//{sel_btn})[1]'
                    )
                    if click_headless_safe(driver, xpath_seta, by=By.XPATH):
                        clicado = True
                        log(f'[DESTINATARIOS] Primeira seta (primeiro destinatário) clicada via fallback {sel_btn}')
                        break

            if not clicado:
                raise RuntimeError('Falha ao clicar primeira seta do Polo Passivo (botão de acrescentar não encontrado)')

            # Aguardar spinner pós-clique
            seletores_loading = (
                'mat-dialog-container, mat-progress-spinner, mat-progress-bar, '
                '.loading-spinner, .cdk-overlay-backdrop, .modal-backdrop'
            )
            try:
                aguardar_renderizacao_nativa(driver, seletores_loading, modo='sumir', timeout=5)
            except Exception:
                pass

            # Aguardar destinatário aparecer na tabela de expedientes
            try:
                aguardar_renderizacao_nativa(driver, 'tbody.cdk-drop-list tr.cdk-drag, table[name="Expedientes"] tbody tr', modo='aparecer', timeout=5)
            except Exception:
                pass

            # Se abrir modal de endereços (ex.: tribunal), tenta selecionar
            try:
                if espera.elemento(driver, '.pec-consulta-enderecos', teto=2):
                    _selecionar_endereco_tribunal(driver, log, debug=debug)
            except Exception:
                pass

            return ResultadoExecucao(
                sucesso=True,
                status='ok',
                detalhes={'count': 1}
            )
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha ao selecionar primeiro destinatário: {e}')
            return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})

    # opção padrão: clicar polo passivo 1x
    log('[DESTINATARIOS] OPÇÃO PADRÃO: Clicando no polo passivo (1x)')
    try:
        btn_polo_passivo = wait_for_clickable(driver, 'button[name="btnIntimarSomentePoloPassivo"]', timeout=10, by=By.CSS_SELECTOR)
        if not btn_polo_passivo:
            raise RuntimeError('Botão polo passivo não clicável')
        _clicar_e_aguardar_spinner(driver, btn_polo_passivo)
        return ResultadoExecucao(sucesso=True, status='geral', detalhes={'count': 0})
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao clicar polo passivo padrão: {e}')
        return ResultadoExecucao(sucesso=False, status='error', erro=str(e), detalhes={'count': 0})


def contar_linhas_destinatarios(driver: Any) -> int:
    """Retorna quantidade de linhas de expedientes presentes na tabela de destinatários."""
    js_contar = """() => {
        var trs = document.querySelectorAll(
            'table[name="Expedientes"] tbody tr, tbody.cdk-drop-list tr.cdk-drag, .pec-tabela-destinatarios table tbody tr'
        );
        return trs ? trs.length : 0;
    }"""
    try:
        if hasattr(driver, 'page') and driver.page:
            return int(driver.page.evaluate(js_contar) or 0)
        fn_exec = getattr(driver, 'execute_script', None)
        if fn_exec:
            return int(fn_exec(f"return ({js_contar})();") or 0)
    except Exception:
        pass
    return 0


def remover_destinatarios_endereco_invalido(
    driver: Any,
    log: Optional[Callable] = None,
    debug: bool = False,
) -> int:
    """Verifica a tabela de expedientes e exclui destinatários com endereço inválido.

    Identifica linhas com o ícone '.pec-icone-vermelho-endereco-tabela-destinatarios'
    (fas fa-times-circle) e clica no botão 'Excluir expediente.' da respectiva linha.
    Opera independentemente da função de destinatário e mesmo que seja o único da tabela.

    Retorna a quantidade de destinatários removidos.
    """
    if log is None:
        def log(_msg):
            pass

    _JS_EXCLUIR_PRIMEIRO_INVALIDO = """() => {
        var selIcone = [
            '.pec-icone-vermelho-endereco-tabela-destinatarios',
            'pje-pec-coluna-endereco i.fa-times-circle',
            'i[class*="pec-icone-vermelho-endereco"]',
            'i.fa-times-circle[class*="pec-icone-vermelho"]'
        ].join(', ');

        var icone = document.querySelector(selIcone);
        if (!icone) return { encontrado: false };

        var tr = icone.closest('tr');
        if (!tr) return { encontrado: true, erro: 'tr_nao_encontrado' };

        var nomeEl = tr.querySelector('.pec-nome-parte-tabela-destinatarios, .pec-formatacao-padrao-dados-parte');
        var nome = nomeEl ? (nomeEl.innerText || nomeEl.textContent || '').trim().replace(/\\s+/g, ' ') : '';
        var endAria = icone.getAttribute('aria-label') || '';

        var btn = tr.querySelector('button[aria-label="Excluir expediente."], button[mattooltip="Excluir expediente."]');
        if (!btn) {
            var iconTrash = tr.querySelector('i.fa-trash-alt, .fa-trash-alt');
            if (iconTrash) btn = iconTrash.closest('button');
        }
        if (!btn) {
            btn = tr.querySelector('.pec-coluna-acoes-usuario-tabela-destinatarios button');
        }

        if (!btn) {
            return { encontrado: true, erro: 'btn_excluir_nao_encontrado', nome: nome, endereco: endAria };
        }

        try { btn.scrollIntoView({ block: 'center', behavior: 'instant' }); } catch(e) {}
        btn.click();
        return { encontrado: true, excluido: true, nome: nome, endereco: endAria };
    }"""

    removidos = 0
    limite = 20
    for _ in range(limite):
        res = None
        try:
            if hasattr(driver, 'page') and driver.page:
                res = driver.page.evaluate(_JS_EXCLUIR_PRIMEIRO_INVALIDO)
            elif hasattr(driver, 'execute_script'):
                res = driver.execute_script(f"return ({_JS_EXCLUIR_PRIMEIRO_INVALIDO})();")
        except Exception as e:
            if debug:
                log(f"[COMUNICACAO][DESTINATARIOS][DEBUG] Erro ao executar exclusão de destinatário inválido: {e}")
            break

        if not isinstance(res, dict) or not res.get('encontrado'):
            break

        if res.get('excluido'):
            removidos += 1
            nome_info = res.get('nome', '')
            end_info = res.get('endereco', '')
            log(f"[COMUNICACAO][DESTINATARIOS] Destinatário com endereço inválido excluído: '{nome_info}' ({end_info})")
            espera.assentar(driver, 0.4, motivo='estabilizacao pos-exclusao destinatario invalido')
        else:
            erro_msg = res.get('erro', 'desconhecido')
            log(f"[COMUNICACAO][DESTINATARIOS][WARN] Falha ao excluir destinatário com endereço inválido: {erro_msg}")
            break

    if removidos > 0:
        log(f"[COMUNICACAO][DESTINATARIOS] Total de destinatários com endereço inválido removidos: {removidos}")
    elif debug:
        log("[COMUNICACAO][DESTINATARIOS][DEBUG] Nenhum destinatário com endereço inválido detectado na tabela.")

    return removidos
