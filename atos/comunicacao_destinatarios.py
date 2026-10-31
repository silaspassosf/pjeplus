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


STOPWORDS_NOMES = {
    'de', 'da', 'do', 'dos', 'das', 'e', 'em', 'para', 'com', 'sem',
    'ltda', 'me', 'epp', 'sa', 's/a', 'eireli', 'cia'
}


def extrair_primeiro_nome_e_sobrenome(nome: str):
    """Extrai (primeiro_nome, proximo_sobrenome) do nome normalizado."""
    if not nome:
        return None, None
    nome_norm = _normalizar_nome_para_match(nome).lower()
    tokens = [t for t in re.findall(r'[a-z]+', nome_norm) if len(t) >= 2]
    if not tokens:
        return None, None
    primeiro = tokens[0]
    sobrenome = None
    for t in tokens[1:]:
        if t not in STOPWORDS_NOMES and len(t) >= 2:
            sobrenome = t
            break
    return primeiro, sobrenome


def casar_nome_destinatario(nome_alvo: str, texto_linha: str) -> bool:
    """Verifica se o nome da linha corresponde estritamente ao destinatário alvo.
    
    Regras:
    1. Match exato (nome_alvo == texto_linha ou contido como substring completa).
    2. Se não exato, o primeiro nome DEVE ser igual (se é Bruno, tem que ser Bruno).
    3. Se houver próximo sobrenome no alvo, ele deve casar contiguamente com o primeiro nome
       (ex.: 'BRUNO DOS SANTOS' ou 'BRUNO SANTOS').
    4. Rejeita tokens isolados dispersos (ex.: 'GOMES' e 'MIRANDA' espalhados entre réu e advogado).
    """
    if not nome_alvo or not texto_linha:
        return False

    alvo_norm = _normalizar_nome_para_match(nome_alvo).lower()
    linha_norm = _normalizar_nome_para_match(texto_linha).lower()

    if not alvo_norm or not linha_norm:
        return False

    # 1. Match exato ou substring completa direta
    if alvo_norm == linha_norm or alvo_norm in linha_norm or linha_norm in alvo_norm:
        return True

    p_alvo, s_alvo = extrair_primeiro_nome_e_sobrenome(nome_alvo)
    if not p_alvo:
        return False

    p_linha, s_linha = extrair_primeiro_nome_e_sobrenome(texto_linha)
    if p_linha and p_linha != p_alvo:
        prefixos_tipo = {
            'reclamado', 'reclamada', 'reu', 're', 'autor', 'autora',
            'reclamante', 'executado', 'executada', 'exequente', 'terceiro',
            'suscitado', 'suscitada'
        }
        if p_linha not in prefixos_tipo:
            return False

    padrao_primeiro = rf'\b{re.escape(p_alvo)}\b'
    if not re.search(padrao_primeiro, linha_norm):
        return False

    if s_alvo:
        padrao_primeiro_e_sobrenome = (
            rf'\b{re.escape(p_alvo)}\b(?:\s+(?:de|da|do|dos|das|e)\b)*\s+\b{re.escape(s_alvo)}\b'
        )
        return bool(re.search(padrao_primeiro_e_sobrenome, linha_norm))

    return True


def _partial_name_match(nome_norm, texto_norm, min_tokens=2):
    """Compat shim que delega para casar_nome_destinatario."""
    return casar_nome_destinatario(nome_norm, texto_norm)


def _extrair_nome_linha_pje(linha):
    """Extrai o nome da parte na linha do PJe, isolando advogados/representantes."""
    try:
        if hasattr(linha, '_js'):
            res = linha._js("""el => {
                const sel = '.nome-parte, .pec-formatacao-padrao-dados-parte.nome-parte, .nome-tipo-parte, pje-nome-parte';
                const elNome = el.querySelector(sel);
                if (elNome && elNome.textContent && elNome.textContent.trim()) {
                    return elNome.textContent.trim();
                }
                const clone = el.cloneNode(true);
                const reps = clone.querySelectorAll('.partes-representante, .pec-representante, [mattooltip*="advogado" i]');
                reps.forEach(r => r.remove());
                return clone.textContent.trim();
            }""")
            if res:
                return res
    except Exception:
        pass
    return getattr(linha, 'text', '') or ''


def _carregar_dadosatuais_local(caminho='dadosatuais.json'):
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _extrair_nomes_por_separador(observacao):
    """Extrai lista de nomes após o delimitador '>' na observação do GIGS.

    Formato esperado: '<prefixo> >nome1, nome2, ...'
    Ex.: 'xs pec id >murillo, silas' → ['murillo', 'silas']

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


def _extrair_reus_mencionados_no_texto(
    texto: str,
    reus: List[Dict[str, Any]],
    padrao_proximidade: Optional[str] = None,
    debug: bool = False,
    log: Any = None
) -> List[Dict[str, Any]]:
    """Compara o texto do documento com a lista de réus (dados_processo['reu']).
    
    Se `padrao_proximidade` for fornecido (ou se for detectado padrão de 'suscitado(s)/suscitada(s)'),
    restringe a busca ao trecho de proximidade logo após o padrão (ex: até 500 caracteres ou fim de período),
    evitando que réus fora desse contexto específico (ex: a empresa ré principal) sejam indevidamente incluídos.

    Para cada réu, extrai tokens significativos do nome (tamanho >= 3, ignorando stopwords).
    Se ao menos 2 tokens significativos (ou todos se o nome for curto) estiverem no texto,
    ou se houver match exato do nome normalizado, o réu é considerado destinatário.
    """
    if not texto or not reus:
        return []

    texto_alvo = texto

    # Se houver padrão de proximidade especificado explicitamente (ex.: via 'informado sentenca suscitados')
    regex_prox = padrao_proximidade

    if regex_prox:
        trechos_encontrados = []
        # Localiza todas as ocorrências do padrão e extrai a janela seguinte (até 600 chars ou ponto final de parágrafo)
        for m in re.finditer(regex_prox, texto, re.I):
            inicio = m.end()
            janela = texto[inicio:inicio + 600]
            # Cortar no final de sentença/parágrafo duplo se houver
            m_fim = re.search(r'(\n\s*\n|\.\s+[A-Z])', janela)
            if m_fim:
                janela = janela[:m_fim.start() + 1]
            trechos_encontrados.append(janela)

        if trechos_encontrados:
            texto_alvo = " ... ".join(trechos_encontrados)
            if log:
                log(f'[DESTINATARIOS] Contexto de proximidade ativado ({regex_prox}): avaliando {len(trechos_encontrados)} trecho(s)')
        else:
            if padrao_proximidade:
                if log:
                    log(f'[DESTINATARIOS][WARN] Padrão de proximidade "{padrao_proximidade}" não localizado no documento')
                return []

    # 1. Match prioritário por CPF / CNPJ mencionado no documento
    # Se algum réu tiver seu CPF ou CNPJ mencionado explicitamente no texto,
    # ele é identificado com certeza absoluta e prevalece sobre matches nominais gerais (ex.: empresa no cabeçalho).
    texto_digitos = re.sub(r'\D', '', texto_alvo)
    candidatos_documento = []
    vistos = set()

    for parte in reus:
        nome = (parte.get('nome') or parte.get('nomeParte') or '').strip()
        doc = (parte.get('cpfcnpj') or parte.get('cpfCnpj') or parte.get('documento') or '').strip()
        doc_digits = re.sub(r'\D', '', str(doc))
        if not doc_digits or len(doc_digits) not in (11, 14):
            continue

        doc_no_texto = (doc and doc in texto_alvo) or (doc_digits in texto_digitos)
        if doc_no_texto:
            chave = (_normalizar_nome_para_match(nome), doc_digits)
            if chave not in vistos:
                vistos.add(chave)
                candidatos_documento.append({
                    'nome_oficial': nome,
                    'nome_identificado': nome,
                    'documento': doc,
                    'documento_normalizado': doc_digits,
                    'polo': 'reu',
                    'tipo_doc': 'cpf' if len(doc_digits) == 11 else 'cnpj'
                })
                if log:
                    tipo_doc_str = 'CPF' if len(doc_digits) == 11 else 'CNPJ'
                    log(f'[DESTINATARIOS] Match exato de {tipo_doc_str} ({doc}) do réu "{nome}" no texto do documento')

    candidatos_cpf = [c for c in candidatos_documento if c.get('tipo_doc') == 'cpf']
    if candidatos_cpf:
        return candidatos_cpf
    if candidatos_documento:
        return candidatos_documento

    texto_norm = _normalizar_nome_para_match(texto_alvo)
    stopwords = {
        'de', 'da', 'do', 'dos', 'das', 'e', 'ou', 'em', 'para', 'com', 'sem',
        'ltda', 'me', 'epp', 'sa', 's/a', 'eireli', 'cia', 'advogado', 'advogados'
    }

    destinatarios = []

    for parte in reus:
        nome = (parte.get('nome') or parte.get('nomeParte') or '').strip()
        doc = (parte.get('cpfcnpj') or parte.get('cpfCnpj') or parte.get('documento') or '').strip()
        if not nome:
            continue

        nome_norm = _normalizar_nome_para_match(nome)
        if not nome_norm:
            continue

        chave = (nome_norm, re.sub(r'\D', '', doc))
        if chave in vistos:
            continue

        # 1. Match direto como substring exata
        if len(nome_norm) >= 5 and nome_norm in texto_norm:
            vistos.add(chave)
            destinatarios.append({
                'nome_oficial': nome,
                'nome_identificado': nome,
                'documento': doc,
                'documento_normalizado': re.sub(r'\D', '', doc),
                'polo': 'reu'
            })
            if log:
                log(f'[DESTINATARIOS] Match direto do réu "{nome}" no trecho do documento')
            continue

        # 2. Match por primeiro nome e próximo sobrenome contíguos (se é Bruno, tem que ser Bruno + sobrenome)
        if casar_nome_destinatario(nome, texto_norm):
            vistos.add(chave)
            destinatarios.append({
                'nome_oficial': nome,
                'nome_identificado': nome,
                'documento': doc,
                'documento_normalizado': re.sub(r'\D', '', doc),
                'polo': 'reu'
            })
            if log:
                log(f'[DESTINATARIOS] Match por primeiro nome + sobrenome do réu "{nome}" no trecho do documento')

    return destinatarios


def _resolver_destinatarios_por_documento_api(
    driver: Any,
    tipo_alvo: str,
    dados_processo: Optional[Dict[str, Any]] = None,
    numero_processo: Optional[str] = None,
    padrao_proximidade: Optional[str] = None,
    debug: bool = False,
    log: Any = None
) -> List[Dict[str, Any]]:
    """Busca o documento respectivo mais recente (e o anterior como fallback) via API
    e cruza seu conteúdo com dados_processo['reu'] para definir os destinatários.

    Args:
        driver: driver PJe / Playwright
        tipo_alvo: 'despacho', 'decisao' ou 'sentenca' (ou lista correspondente)
        dados_processo: dict com dados do processo contendo 'reu'
        numero_processo: número do processo (opcional)
        padrao_proximidade: regex ou termo de proximidade (ex: r'suscitad[oas]{1,2}')
        debug: flag de depuração
        log: logger callback
    """
    if log is None:
        def log(_msg): return None

    # Normalizar tipos procurados para a timeline
    mapa_tipos = {
        'despacho': ['Despacho'],
        'decisao': ['Decisão', 'Decisao'],
        'sentenca': ['Sentença', 'Sentenca'],
    }
    tipos_busca = mapa_tipos.get(tipo_alvo.lower(), [tipo_alvo.capitalize()])

    try:
        from Fix.variaveis import cliente_para, obter_texto_documento
        from Fix.core import extrair_id_processo
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Erro ao importar Fix.variaveis/core: {e}')
        return []

    client = None
    try:
        client = cliente_para(driver)
    except Exception as e:
        log(f'[DESTINATARIOS][WARN] Falha ao instanciar cliente_para: {e}')
        return []

    id_processo = extrair_id_processo(driver)
    if not id_processo and numero_processo:
        try:
            id_processo = client.id_processo_por_numero(str(numero_processo))
        except Exception as e:
            log(f'[DESTINATARIOS][WARN] Falha ao resolver id_processo pelo número {numero_processo}: {e}')

    if not id_processo:
        log('[DESTINATARIOS][WARN] id_processo não disponível para leitura de documento via API')
        return []

    # Obter réus a partir de dados_processo ou via API /partes
    reus = []
    if isinstance(dados_processo, dict) and dados_processo.get('reu'):
        reus = dados_processo['reu']
    else:
        try:
            partes_raw = client.partes(str(id_processo))
            if isinstance(partes_raw, dict):
                # Formato padrão PJe /partes: {'PASSIVO': [...]}
                passivos = partes_raw.get('PASSIVO') or partes_raw.get('passivo') or partes_raw.get('reu') or []
                for p in passivos:
                    if isinstance(p, dict):
                        reus.append(p)
            elif isinstance(partes_raw, list):
                # Formato lista plana: filtrar estritamente polo passivo/reu
                for p in partes_raw:
                    if isinstance(p, dict):
                        polo = (p.get('polo') or p.get('tipoPolo') or '').lower()
                        if polo in ('passivo', 'reu', 'r'):
                            reus.append(p)
        except Exception as e:
            log(f'[DESTINATARIOS][WARN] Falha ao obter partes via API: {e}')

    if not reus:
        log('[DESTINATARIOS][WARN] Nenhum réu encontrado para match com documento')
        return []

    # Buscar itens da timeline via API
    try:
        timeline_dados = client.timeline(str(id_processo), buscarDocumentos=True, buscarMovimentos=False) or []
    except Exception as e:
        log(f'[DESTINATARIOS][ERRO] Falha ao obter timeline via API: {e}')
        return []

    # Flatten documentos + anexos
    documentos_candidatos = []
    for item in timeline_dados:
        documentos_candidatos.append(item)
        for anexo in item.get('anexos') or []:
            documentos_candidatos.append(anexo)

    # Filtrar documentos que correspondam ao tipo solicitado (ordem decrescente da timeline = mais recente primeiro)
    docs_alvo = []
    tipos_busca_lower = [t.lower() for t in tipos_busca]
    for d in documentos_candidatos:
        tipo_doc = (d.get('tipo') or '').strip().lower()
        if not tipo_doc:
            continue
        if any(t in tipo_doc for t in tipos_busca_lower):
            doc_id = d.get('id') or d.get('idDocumento') or d.get('idUnicoDocumento')
            if doc_id:
                docs_alvo.append({
                    'id': str(doc_id),
                    'tipo': d.get('tipo'),
                    'titulo': d.get('titulo') or d.get('tipo')
                })

    if not docs_alvo:
        log(f'[DESTINATARIOS][WARN] Nenhum documento do tipo "{tipo_alvo}" ({tipos_busca}) encontrado na timeline')
        return []

    # Ler no máximo o último (mais recente) e o anterior se não encontrar no mais recente
    limite_docs = docs_alvo[:2]
    log(f'[DESTINATARIOS] Encontrados {len(docs_alvo)} documento(s) de tipo {tipos_busca}; avaliando até {len(limite_docs)} mais recente(s)')

    for idx, doc_info in enumerate(limite_docs):
        doc_id = doc_info['id']
        rotulo = 'mais recente' if idx == 0 else 'anterior'
        log(f'[DESTINATARIOS] Lendo documento ({rotulo}): ID={doc_id} tipo="{doc_info["tipo"]}"')

        texto_doc = None
        try:
            texto_doc = obter_texto_documento(client, str(id_processo), str(doc_id))
        except Exception as e_ler:
            log(f'[DESTINATARIOS][WARN] Falha ao extrair texto do doc {doc_id}: {e_ler}')

        if not texto_doc:
            log(f'[DESTINATARIOS] Documento {doc_id} sem conteúdo textual legível via API')
            continue

        candidatos = _extrair_reus_mencionados_no_texto(
            texto_doc,
            reus,
            padrao_proximidade=padrao_proximidade,
            debug=debug,
            log=log
        )
        if candidatos:
            log(f'[DESTINATARIOS] Encontrado(s) {len(candidatos)} destinatário(s) no documento {rotulo} (ID={doc_id})')
            return candidatos
        else:
            log(f'[DESTINATARIOS] Nenhum réu encontrado no texto do documento {rotulo}')

    log('[DESTINATARIOS][WARN] Nenhum réu deu match nos documentos avaliados via API')
    return []



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

        # --- tentativa por nome (Two-pass: exato primeiro, depois primeiro nome + próximo sobrenome) ---
        if nome_alvo:
            nome_alvo_norm = _normalizar_nome_para_match(nome_alvo).lower()

            # Passada 1: Procura match exato do nome alvo entre todas as linhas
            for linha in linhas:
                try:
                    nome_linha = _extrair_nome_linha_pje(linha)
                    nome_linha_norm = _normalizar_nome_para_match(nome_linha).lower()
                    texto_linha_norm = _normalizar_nome_para_match(linha.text or '').lower()

                    if nome_alvo_norm and (nome_alvo_norm == nome_linha_norm or nome_alvo_norm in nome_linha_norm or nome_alvo_norm in texto_linha_norm):
                        if _clicar_btn_acrescentar(driver, linha, qtd_cliques, debug=debug):
                            if debug:
                                logger.info(f"[DESTINATARIOS] Parte selecionada via nome (match exato): {nome_alvo}")
                            return {'status': 'ok', 'count': 1}
                except Exception:
                    continue

            # Passada 2: Procura match estrito (primeiro nome + próximo sobrenome, nunca tokens isolados)
            for linha in linhas:
                try:
                    nome_linha = _extrair_nome_linha_pje(linha)
                    if casar_nome_destinatario(nome_alvo, nome_linha):
                        if _clicar_btn_acrescentar(driver, linha, qtd_cliques, debug=debug):
                            if debug:
                                logger.info(f"[DESTINATARIOS] Parte selecionada via nome (primeiro nome + sobrenome): {nome_alvo}")
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

    # Normalização de 'informado [tipo]' (ex: 'informado despacho', 'informado_decisao', 'informado sentenca', 'informado decisao suscitados')
    tipo_informado_doc = None
    padrao_proximidade_informado = None
    if isinstance(destinatarios, str):
        dest_str = destinatarios.strip().lower()
        # Verificar se especifica cliques no final (ex: informado despacho 2, informado_2)
        m_cliques = re.search(r'[\s_]([12])x?$', dest_str)
        if m_cliques and not re.search(r'(despacho|decis|senten)', m_cliques.group(0)):
            qtd_informado = int(m_cliques.group(1))

        # Identificar padrão de proximidade se especificado (ex: após/depois de X ou suscitad...)
        m_apos = re.search(r'(?:ap[oó]s|depois\s+de)\s+([a-z0-9_]+)', dest_str)
        if m_apos:
            termo = m_apos.group(1).strip()
            padrao_proximidade_informado = rf'\b{termo}[a-z]*\b'
        elif re.search(r'\b(suscitad[oas]{1,2})\b', dest_str):
            padrao_proximidade_informado = r'\b(?:suscitad[oas]{1,2})\b'

        # Identificar tipo de documento informado
        if re.search(r'\b(despacho)\b', dest_str):
            tipo_informado_doc = 'despacho'
            destinatarios = 'informado'
        elif re.search(r'\b(decis[aã]o|decisao)\b', dest_str):
            tipo_informado_doc = 'decisao'
            destinatarios = 'informado'
        elif re.search(r'\b(senten[cç]a|sentenca)\b', dest_str):
            tipo_informado_doc = 'sentenca'
            destinatarios = 'informado'
        elif re.match(r'^informado', dest_str):
            destinatarios = 'informado'
            tipo_informado_doc = 'decisao'  # padrão quando vem 'informado'

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
        tipo_alvo = tipo_informado_doc or 'decisao'
        msg_prox = f' (proximidade: {padrao_proximidade_informado})' if padrao_proximidade_informado else ''
        log(f'[DESTINATARIOS] OPÇÃO INFORMADO ({tipo_alvo}{msg_prox}): lendo documento respectivo mais recente via API e cruzando com réus')
        try:
            candidatos = _resolver_destinatarios_por_documento_api(
                driver,
                tipo_alvo=tipo_alvo,
                dados_processo=dados_processo,
                numero_processo=numero_processo,
                padrao_proximidade=padrao_proximidade_informado,
                debug=debug,
                log=log,
            )

            return _selecionar_por_lista(
                driver, candidatos, f'informado/{tipo_alvo}', log,
                fallback_polo_passivo=True,
                qtd_seta_override=qtd_informado,
                debug=debug,
                qtd_cliques_fallback=qtd_cliques_fallback,
            )
        except Exception as e:
            log(f'[DESTINATARIOS][ERRO] Falha no modo informado ({tipo_alvo}): {e}')
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

        var icones = Array.from(document.querySelectorAll(selIcone));
        if (!icones.length) return { encontrado: false };

        for (var icone of icones) {
            var tr = icone.closest('tr');
            if (!tr) continue;

            // Extrair o meio de comunicação/expedição da linha
            var meioEl = tr.querySelector('.mat-select-min-line, mat-select [class*="select-value"], pje-pec-coluna-meio-expedicao, .pec-coluna-meio-expedicao');
            var meioTxt = (meioEl ? (meioEl.innerText || meioEl.textContent || '') : '').trim().toLowerCase();
            
            // Também verificar texto da coluna de endereço como fallback
            var endAria = (icone.getAttribute('aria-label') || '').toLowerCase();
            var endTxt = (icone.parentElement ? (icone.parentElement.innerText || icone.parentElement.textContent || '') : '').toLowerCase();

            // Meios eletrônicos onde endereço postal não existe e não é obrigatório
            var isEletronico = meioTxt.includes('sistema') || 
                               meioTxt.includes('domicilio') || 
                               meioTxt.includes('domicílio') || 
                               meioTxt.includes('eletron') ||
                               meioTxt.includes('dje') ||
                               endAria.includes('matéria do dje') ||
                               endAria.includes('materia do dje') ||
                               endTxt.includes('matéria do dje') ||
                               endTxt.includes('materia do dje');

            // Só é elegível para exclusão por endereço inválido se o envio for postal/Correios
            var isCorreios = meioTxt.includes('correio');

            // Se for meio eletrônico (Sistema/Domicílio/DJE) ou não for comprovadamente Correios, NÃO exclui!
            if (isEletronico || !isCorreios) {
                continue;
            }

            var nomeEl = tr.querySelector('.pec-nome-parte-tabela-destinatarios, .pec-formatacao-padrao-dados-parte');
            var nome = nomeEl ? (nomeEl.innerText || nomeEl.textContent || '').trim().replace(/\\s+/g, ' ') : '';

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
        }

        return { encontrado: false };
    }"""

    removidos = 0
    limite = 20
    for _ in range(limite):
        res = None
        try:
            if hasattr(driver, 'page') and driver.page:
                res = driver.page.evaluate(_JS_EXCLUIR_PRIMEIRO_INVALIDO)
            elif hasattr(driver, 'evaluate'):
                res = driver.evaluate(_JS_EXCLUIR_PRIMEIRO_INVALIDO)
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


# =============================================================================
# Inserção e Detecção de PJDP (Órgãos Públicos / Fazenda Pública)
# =============================================================================

PJDP_NOME_KEYWORDS = [
    'municipio', 'prefeitura', 'estado de', 'estado do', 'governo do estado',
    'governo do municipio', 'uniao federal', 'ministerio', 'autarquia',
    'fazenda publica', 'inss', 'tribunal', 'correios', 'empresa brasileira de correios',
    'fundacao publica', 'fundacao casa', 'procuradoria', 'defensoria publica',
    'hospital das clinicas', 'universidade federal', 'universidade estadual',
    'orgao publico', 'ente publico'
]


def detectar_pjdp_processo(driver: Any) -> bool:
    """Detecta se há PJDP (Pessoa Jurídica de Direito Público / Órgão Público)
    no polo passivo do processo via API PJe chamando diretamente `_detectar_pjdp_api`
    de `bianca.triagem.regras` (critério principal: campo `procuradoria` da API).
    """
    try:
        from Fix.variaveis import cliente_para
        from Fix.core import extrair_id_processo
        from bianca.triagem.regras import _detectar_pjdp_api

        id_proc = extrair_id_processo(driver)
        if not id_proc:
            return False

        client = cliente_para(driver)
        partes_raw = client.partes(str(id_proc))
        if not partes_raw:
            return False

        passivos = []
        if isinstance(partes_raw, dict):
            passivos = partes_raw.get('PASSIVO') or partes_raw.get('passivo') or []
        elif isinstance(partes_raw, list):
            for p in partes_raw:
                polo = (p.get('polo') or p.get('tipoPolo') or p.get('poloProcessual') or '').lower()
                if not polo or polo in ('passivo', 'reclamada', 'reclamado', 'reu'):
                    passivos.append(p)

        if not passivos:
            return False

        reclamados_lista = []
        for p in passivos:
            nome_p = (p.get('nome') or p.get('nomeParte') or '').strip()
            item = {'nome': nome_p}
            # Critério procuradoria (API PJe): entes públicos possuem o campo 'procuradoria' preenchido
            if 'procuradoria' in p:
                item['pjdp'] = bool(p.get('procuradoria'))
            elif 'pjdp' in p:
                item['pjdp'] = bool(p.get('pjdp'))
            reclamados_lista.append(item)

        pjdp_detectado, pjdp_nome = _detectar_pjdp_api({'reclamados': reclamados_lista})
        if pjdp_detectado:
            logger.info(f'[PJDP] PJDP detectada no polo passivo via _detectar_pjdp_api (procuradoria): "{pjdp_nome}"')
            return True

        return False
    except Exception as e:
        logger.warning(f'[PJDP] Erro ao detectar PJDP via API: {e}')
        return False


def inserir_destinatarios_pjdp(driver: Any, log: Callable = logger.info, debug: bool = False) -> int:
    """Insere manualmente destinatários PJDP (órgãos públicos) do polo passivo.

    No PJe, entes públicos (PJDP) não são adicionados automaticamente aos
    destinatários da Notificação Inicial. Esta função abre o Polo Passivo,
    identifica as partes marcadas como órgão público (ícone fas fa-building /
    tooltip 'órgão público') e clica na seta para acrescentá-las aos destinatários.
    """
    log('[COMUNICACAO][PJDP] Verificando inserção manual de PJDP nos destinatários...')

    # 1. Expandir painel do Polo Passivo
    if not _clicar_polo_passivo(driver, log):
        log('[COMUNICACAO][PJDP][WARN] Falha ao expandir o painel Polo Passivo')
        return 0

    espera.assentar(driver, 0.8, motivo='renderizacao polo passivo')

    # 2. Localizar linhas do Polo Passivo
    linhas = espera.elementos(
        driver,
        '.pec-partes-polo li.partes-corpo, ul.sem-padding li.partes-corpo, mat-row',
        teto=5
    )
    if not linhas:
        log('[COMUNICACAO][PJDP][WARN] Nenhuma linha de parte encontrada no Polo Passivo')
        return 0

    # Coletar texto dos destinatários já na tabela para evitar duplicatas
    linhas_tabela = espera.elementos(driver, 'tbody.cdk-drop-list tr.cdk-drag', teto=2) or []
    nomes_tabela = [normalizar_string(getattr(r, 'text', '') or '').lower() for r in linhas_tabela]

    adicionados = 0
    for linha in linhas:
        try:
            eh_pjdp = False
            nome_parte = ''

            if hasattr(linha, '_js'):
                info = linha._js("""el => {
                    const selPjdp = [
                        'i.fas.fa-building',
                        'i.fa-building',
                        'i[mattooltip*="órgão público"]',
                        'i[aria-label*="órgão público"]',
                        'i[mattooltip*="orgao publico"]',
                        'i[aria-label*="orgao publico"]',
                        'i.procuradoria-direito-publico'
                    ];
                    let temIcone = false;
                    for (const sel of selPjdp) {
                        if (el.querySelector(sel)) {
                            temIcone = true;
                            break;
                        }
                    }
                    if (!temIcone) {
                        const txt = (el.textContent || '').toLowerCase();
                        if (txt.includes('órgão público') || txt.includes('orgao publico')) {
                            temIcone = true;
                        }
                    }
                    const elNome = el.querySelector('.nome-parte, .pec-formatacao-padrao-dados-parte.nome-parte, .pec-formatacao-padrao-dados-parte');
                    const nome = (elNome ? elNome.textContent : el.textContent || '').trim();
                    return { eh_pjdp: temIcone, nome: nome };
                }""")
                if info:
                    eh_pjdp = bool(info.get('eh_pjdp'))
                    nome_parte = info.get('nome') or ''

            if not eh_pjdp:
                texto_linha = (getattr(linha, 'text', '') or '').lower()
                if 'órgão público' in texto_linha or 'orgao publico' in texto_linha:
                    eh_pjdp = True

            if eh_pjdp:
                nome_norm = normalizar_string(nome_parte).lower()
                # Verificar se já consta na tabela de destinatários
                ja_adicionado = any(nome_norm[:20] in nt for nt in nomes_tabela if len(nome_norm) >= 5) if nomes_tabela else False
                if ja_adicionado:
                    log(f'[COMUNICACAO][PJDP] PJDP "{nome_parte}" já presente na tabela de destinatários — pulando')
                    continue

                log(f'[COMUNICACAO][PJDP] Parte PJDP identificada no Polo Passivo: "{nome_parte}"')
                clicou = _clicar_btn_acrescentar(driver, linha, qtd_cliques=1, debug=debug)
                if clicou:
                    adicionados += 1
                    log(f'[COMUNICACAO][PJDP] Botão acrescentar clicado para PJDP "{nome_parte}"')
                    espera.assentar(driver, 1.2, motivo='adicao de pjdp')
                else:
                    log(f'[COMUNICACAO][PJDP][WARN] Falha ao clicar botão acrescentar para PJDP "{nome_parte}"')
        except Exception as e_linha:
            log(f'[COMUNICACAO][PJDP][ERRO] Erro ao processar linha de parte: {e_linha}')

    if adicionados > 0:
        log(f'[COMUNICACAO][PJDP] Sucesso: {adicionados} parte(s) PJDP acrescentada(s) aos destinatários.')
        espera.pausa(driver, 2.0, motivo='estabilizacao tabela pos-adicao pjdp')
        try:
            aguardar_renderizacao_nativa(
                driver,
                'tbody.cdk-drop-list tr.cdk-drag',
                modo='aparecer',
                timeout=10
            )
        except Exception:
            pass
    else:
        log('[COMUNICACAO][PJDP] Nenhuma parte PJDP com indicador fas fa-building pendente de inclusão.')

    return adicionados
