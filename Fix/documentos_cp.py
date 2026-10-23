"""documentos_cp — extraído de Fix/core.py (F7: split verbatim, re-exportado pelo core).

Corpos idênticos aos originais (mesma ordem interna). O grafo entre módulos é
acíclico: navegacao_espera <- navegacao <- entrada_campos; documentos_cp e
filtros_painel são folhas. """

import re
import unicodedata

from .log import logger
from Play.pjeplay.errors import ElementClickInterceptedException
from Play.pjeplay.locators import By

from Fix import espera

from .navegacao import _buscar_filho, _executar_js, safe_click_no_scroll  # noqa: F401
from .navegacao_espera import aguardar_renderizacao_nativa, esperar_elemento  # noqa: F401

# Constantes de módulo que acompanham este grupo (usadas por suas funções).
_CP_DESPACHO = re.compile(r'\bdespacho\b')

def verificar_documento_decisao_sentenca(driver):
    """Verifica se existe um documento com 'decisão' ou 'sentença' no nome."""
    try:
        seletor_nomes_docs = 'pje-arvore-documento .node-content-wrapper span'
        nomes_docs = espera.elementos(driver, seletor_nomes_docs)

        for nome_element in nomes_docs:
            doc_text = nome_element.text.lower()
            if 'decisao' in doc_text or 'sentenca' in doc_text:
                logger.debug('[DOC CHECK] Documento encontrado: "%s"', doc_text)
                return True

        logger.debug('[DOC CHECK] Nenhum documento de decisao/sentenca encontrado.')
        return False
    except Exception as e:
        logger.error('[DOC CHECK] Falha ao verificar documentos: %s', e)
        return False

def visibilidade_sigilosos(driver, polo='ativo', log=True):
    """
    Aplica visibilidade a documentos sigilosos anexados automaticamente, conforme lógica do gigs-plugin.js.
    polo: 'ambos', 'ativo', 'passivo' ou 'nenhum'
    """
    try:
        # ✨ OTIMIZADO: Limpar overlays antes de buscar documento
        try:
            from Fix.headless_helpers import limpar_overlays_headless
            limpar_overlays_headless(driver)
        except ImportError:
            pass

        # 1. Seleciona o último documento sigiloso na timeline
        sigiloso_link = espera.elemento(driver, 'ul.pje-timeline a.tl-documento.is-sigiloso:last-child')
        if not sigiloso_link:
            if log:
                logger.error('[VISIBILIDADE] Documento sigiloso nao encontrado na timeline.')
            return False
        aria_label = sigiloso_link.get_attribute('aria-label')
        import re
        m = re.search(r'Id[:\.\s]+([A-Za-z0-9]{6,8})', aria_label or '')
        if not m:
            if log:
                logger.error('[VISIBILIDADE] Nao foi possivel extrair o ID do documento.')
            return False
        id_documento = m.group(1)
        if log:
            logger.debug('[VISIBILIDADE] Documento sigiloso encontrado: %s', id_documento)
        # 2. Ativa múltipla seleção
        btn_multi = espera.elemento(driver, 'button[aria-label="Exibir múltipla seleção."]')
        if btn_multi:
            try:
                btn_multi.click()
            except ElementClickInterceptedException:
                safe_click_no_scroll(driver, btn_multi)
        # Aguardar checkbox do documento aparecer
        espera.elemento(driver, f'mat-card[id*="{id_documento}"] mat-checkbox', teto=5, visivel=False)
        # 3. Marca o checkbox do documento
        mat_checkbox = espera.elemento(driver, f'mat-card[id*="{id_documento}"] mat-checkbox label')
        if mat_checkbox:
            try:
                mat_checkbox.click()
            except ElementClickInterceptedException:
                safe_click_no_scroll(driver, mat_checkbox)
        # Aguardar botão de visibilidade
        espera.elemento(driver, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]', teto=5, visivel=False)
        # 4. Clica no botão de visibilidade
        btn_visibilidade = espera.elemento(driver, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]')
        if btn_visibilidade:
            try:
                btn_visibilidade.click()
            except ElementClickInterceptedException:
                safe_click_no_scroll(driver, btn_visibilidade)
        # Aguardar modal de sigilo
        espera.elemento(driver, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"]', teto=5, visivel=False)
        # 5. No modal, seleciona o polo desejado
        if polo == 'ativo':
            labels = espera.elementos(driver, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] tr:has(i.POLO_ATIVO) label')
            for label in labels:
                label.click()
        elif polo == 'passivo':
            labels = espera.elementos(driver, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"] tr:has(i.POLO_PASSIVO) label')
            for label in labels:
                label.click()
        elif polo == 'ambos':
            btn_todos = espera.elemento(driver, 'th button')
            if btn_todos:
                btn_todos.click()
        # 6. Confirma no botão Salvar
        btn_salvar = espera.elemento(driver, '//button[.//span[contains(text(),"Salvar")]]', teto=10)
        if btn_salvar:
            btn_salvar.click()
        # Aguardar modal fechar
        espera.ate_sumir(
            driver,
            '//button[.//span[contains(text(),"Salvar")]]/ancestor::div[contains(@class,"cdk-overlay")]',
            teto=5,
        )
        # 7. Oculta múltipla seleção
        try:
            btn_ocultar = espera.elemento(driver, 'button[aria-label="Ocultar múltipla seleção."]')
            if btn_ocultar:
                btn_ocultar.click()
        except Exception:
            pass
        if log:
            logger.debug('[VISIBILIDADE] Visibilidade aplicada com sucesso.')
        return True
    except Exception as e:
        if log:
            logger.error('[VISIBILIDADE] Falha ao aplicar visibilidade: %s', e)
        return False

def criar_botoes_detalhes(driver):
    """
    Cria botões com ícones e ações específicas, replicando a funcionalidade do MaisPje, usando o driver já autenticado.
    """
    base_element = espera.elemento(driver, "#pjextension_bt_detalhes_base", teto=10, visivel=False)
    if base_element is None:
        base_element = espera.elemento(driver, "body")

    fn_sc = getattr(driver, "execute" + "_script", None)
    # Cria o container se não existir
    if not espera.elementos(driver, "#pjextension_bt_detalhes_base"):
        if fn_sc:
            fn_sc(
                "var div = document.createElement('div');"
                "div.id = 'pjextension_bt_detalhes_base';"
                "div.style = 'float: left';"
                "div.setAttribute('role', 'toolbar');"
                "document.body.appendChild(div);"
                "return div;"
            )
    else:
        container = espera.elemento(driver, "#pjextension_bt_detalhes_base")

    # Configuração dos botões
    buttons = [
        {"title": "Abrir o Gigs", "icon": "fa fa-tag", "action": "abrir_gigs"},
        {"title": "Expedientes", "icon": "fa fa-envelope", "action": "acao_botao_detalhes('Expedientes')"},
        {"title": "Lembretes", "icon": "fas fa-thumbtack", "action": "acao_botao_detalhes('Lembretes')"},
    ]

    for button in buttons:
        if fn_sc:
            fn_sc(
                f"var a = document.createElement('a');"
                f"a.title = '{button['title']}';"
                f"a.style = 'cursor: pointer; position: relative; vertical-align: middle; padding: 5px; top: 5px; z-index: 1; opacity: 1; font-size: 1.5rem; margin: 5px;';"
                f"a.onmouseover = function() {{ a.style.opacity = 0.5; }};"
                f"a.onmouseleave = function() {{ a.style.opacity = 1; }};"
                f"var i = document.createElement('i');"
                f"i.className = '{button['icon']}';"
                f"a.appendChild(i);"
                f"a.onclick = function() {{ {button['action']} }};"
                f"document.getElementById('pjextension_bt_detalhes_base').appendChild(a);"
            )
    if fn_sc:
        fn_sc(
            "setTimeout(function() {"
            "  var div = document.getElementById('pjextension_bt_detalhes_base');"
            "  if (div) { div.style.display='none'; div.offsetHeight; div.style.display=''; }"
            "}, 100);"
        )

def buscar_ultimo_mandado(driver, log=True):
    """
    Busca o último documento do tipo 'mandado' na timeline do processo.
    Retorna o texto do documento e seu tipo, ou None se não encontrado.
    """
    try:
        # Espera a timeline carregar
        itens_timeline = espera.elementos(driver, 'li.tl-item-container')
        if not itens_timeline:
            if log:
                logger.warning('[MANDADO] Nenhum item encontrado na timeline.')
            return None, None

        for item in itens_timeline:
            try:
                link = espera.elemento(driver, 'li.tl-item-container a.tl-documento:not([target="_blank"])')
                if not link:
                    continue
                doc_text = link.text.lower()

                if 'mandado' in doc_text:
                    link.click()
                    espera.assentar(driver, 1)

                    texto = item.text
                    if log:
                        logger.debug('[MANDADO] Documento encontrado: %s', doc_text)
                    return texto, 'mandado'

            except Exception as e:
                if log:
                    logger.warning('[MANDADO] Falha ao processar item: %s', e)
                continue

        if log:
            logger.debug('[MANDADO] Nenhum documento do tipo mandado encontrado.')
        return None, None

    except Exception as e:
        if log:
            logger.error('[MANDADO] Falha geral: %s', e)
        return None, None

def buscar_mandado_autor(driver, log=True):
    """
    Busca o último documento do tipo 'mandado' na timeline do processo.
    Após localizar, busca o ícone de martelo (gavel) e registra o autor: 'SILAS PASSOS' ou outro.
    Retorna um dicionário com texto, tipo e autor, ou None se não encontrado.
    """
    try:
        itens_timeline = espera.elementos(driver, 'li.tl-item-container')
        if not itens_timeline:
            if log:
                logger.warning('[MANDADO] Nenhum item encontrado na timeline.')
            return None

        for item in itens_timeline:
            try:
                link = espera.elemento(driver, 'li.tl-item-container a.tl-documento:not([target="_blank"])')
                if not link:
                    continue
                doc_text = link.text.lower()
                if 'mandado' in doc_text:
                    link.click()
                    espera.assentar(driver, 1)
                    texto = item.text
                    autor = 'DESCONHECIDO'
                    try:
                        gavel_icon = espera.elemento(driver, 'li.tl-item-container i.fa-gavel, li.tl-item-container i.fas.fa-gavel')
                        if gavel_icon:
                            autor_text = gavel_icon.text.strip().upper()
                            if 'SILAS PASSOS' in autor_text:
                                autor = 'SILAS PASSOS'
                            else:
                                autor = autor_text
                            if log:
                                logger.debug('[MANDADO] Autor identificado: %s', autor)
                    except Exception:
                        if log:
                            logger.debug('[MANDADO] Icone gavel ou autor nao localizado.')
                    if log:
                        logger.debug('[MANDADO] Documento encontrado: %s', doc_text)
                    return {'texto': texto, 'tipo': 'mandado', 'autor': autor}
            except Exception as e:
                if log:
                    logger.warning('[MANDADO] Falha ao processar item: %s', e)
                continue
        if log:
            logger.debug('[MANDADO] Nenhum documento do tipo mandado encontrado.')
        return None
    except Exception as e:
        if log:
            logger.error('[MANDADO] Falha geral: %s', e)
        return None

def buscar_documentos_sequenciais(driver, log=True):
    """
    ✅ BUSCA DOCUMENTOS DO BLOCO ARGOS NA ORDEM CORRETA
    
    Bloco ARGOS (ordem cronológica - mais recente para mais antiga):
    0. Certidão de devolução (mais recente)
    1-3. Documentos do meio: certidão expedição, intimação, planilha
    4. Decisão (mais antiga - fim do bloco)
    
    IMPORTANTE: Intimação deve estar ENTRE certidão devolução e decisão
    """
    try:
        if log:
            logger.debug('[DOCUMENTOS_SEQUENCIAIS] Buscando documentos do bloco ARGOS')

        aguardar_renderizacao_nativa(driver, timeout=10)
        elementos = espera.elementos(driver, "li.tl-item-container", teto=8)

        if not elementos:
            if log:
                logger.error('[DOCUMENTOS_SEQUENCIAIS] Timeline vazia')
            return []

        idx_cert_devolucao = None
        for idx, elem in enumerate(elementos):
            texto = _norm(elem.text.strip())
            if "certidao de devolucao" in texto:
                idx_cert_devolucao = idx
                if log:
                    logger.debug('[DOCUMENTOS_SEQUENCIAIS] Encontrado: Certidao de devolucao - %s...', texto[:50])
                break

        if idx_cert_devolucao is None:
            if log:
                logger.error('[DOCUMENTOS_SEQUENCIAIS] Certidao de devolucao nao encontrada')
            return []

        idx_decisao = None
        for idx in range(idx_cert_devolucao + 1, len(elementos)):
            texto = _norm(elementos[idx].text.strip())
            if "decisao(" in texto:
                idx_decisao = idx
                if log:
                    logger.debug('[DOCUMENTOS_SEQUENCIAIS] Encontrado: Decisao - %s...', texto[:50])
                break

        if idx_decisao is None:
            if log:
                logger.error('[DOCUMENTOS_SEQUENCIAIS] Decisao nao encontrada apos certidao')
            return []

        resultados = [elementos[idx_cert_devolucao]]

        tipos_meio = {
            'Certidao de expedicao': ['certidao de expedicao'],
            'Planilha': ['planilha de atualizacao'],
            'Intimacao': ['intimacao(']
        }

        for idx in range(idx_cert_devolucao + 1, idx_decisao):
            elem = elementos[idx]
            texto = _norm(elem.text.strip())

            for tipo_nome, palavras in tipos_meio.items():
                for palavra in palavras:
                    if palavra in texto:
                        resultados.append(elem)
                        if log:
                            logger.debug('[DOCUMENTOS_SEQUENCIAIS] Encontrado: %s - %s...', tipo_nome, texto[:50])
                        break

        resultados.append(elementos[idx_decisao])

        if log:
            logger.info('[DOCUMENTOS_SEQUENCIAIS] encontrados: %d', len(resultados))

        return resultados

    except Exception as e:
        if log:
            logger.error('[DOCUMENTOS_SEQUENCIAIS] %s', str(e))
        return []

def _norm(t):
    """Normaliza texto para comparacao: minusculas, sem acento (NFD -> ascii)."""
    return unicodedata.normalize('NFD', (t or '').lower()).encode('ascii', 'ignore').decode()

def _normalizar_para_cp(texto):
    """Normaliza texto removendo acentos e espaços extras (para matching)."""
    if not texto:
        return ''
    from Fix.utils import normalizar_texto
    return normalizar_texto(texto).strip()

def _extrair_texto_item_api(doc):
    """Extrai texto consolidado (titulo, tipo, descricao, nomeDocumento) de item da API timeline."""
    if not isinstance(doc, dict):
        return ''
    titulo = _normalizar_para_cp(doc.get('titulo') or '')
    tipo = _normalizar_para_cp(doc.get('tipo') or '')
    descricao = _normalizar_para_cp(doc.get('descricao') or '')
    nome_doc = _normalizar_para_cp(doc.get('nomeDocumento') or '')
    return f"{titulo} {tipo} {descricao} {nome_doc}".strip()

def _cp_eh_cdist(texto: str) -> bool:
    """Verifica se texto corresponde a Certidão de Distribuição (âncora primária de CP)."""
    return ('certidao' in texto and 'distribuicao' in texto) or 'certidao de distribuicao' in texto

def _cp_eh_despacho(texto: str) -> bool:
    """Verifica se texto corresponde a Despacho."""
    return bool(_CP_DESPACHO.search(texto))

def _cp_eh_mandado(texto: str) -> bool:
    """Verifica se texto corresponde a Mandado."""
    return 'mandado' in texto and 'mandado de pagamento' not in texto and 'mandado de seguranca' not in texto

def _cp_eh_certidao_oj(texto: str) -> bool:
    """Verifica se texto corresponde a Certidão de Oficial de Justiça."""
    return (
        'certidao de oficial de justica' in texto
        or 'certidao de oficial' in texto
        or ('certidao' in texto and 'oficial de justica' in texto)
    )

def _cp_eh_certidao_geral(texto: str) -> bool:
    """Verifica se texto corresponde a Certidão em geral (ex.: certidão de ciência ao deprecante)."""
    return 'certidao' in texto

def _obter_timeline_via_api(driver, log=True, numero_processo=None):
    """Obtem timeline via API REST (mais confiavel que DOM parsing).
    
    Returns:
        list[dict] ou None se falhar
    """
    try:
        from Fix.variaveis import cliente_para
        url_atual = getattr(driver, 'current_url', '') or ''
        
        # 1. Tentar extrair id_processo da URL (/processo/123456)
        id_processo = None
        m = re.search(r'/processo/(\d+)', url_atual)
        if m:
            id_processo = m.group(1)
            
        client = cliente_para(driver)
        if not client:
            if log:
                logger.warning('[TIMELINE_API] Nao conseguiu extrair sessao do driver')
            return None
            
        # 2. Se não extraiu da URL, tentar obter ID via numero_processo se disponível
        if not id_processo:
            num = numero_processo
            if not num:
                from Fix.extracao import extrair_numero_processo_url
                try:
                    num = extrair_numero_processo_url(driver)
                except Exception:
                    num = None
            if num:
                try:
                    url_agrup = client._url(f"/pje-comum-api/api/agrupamentotarefas/processos?numero={num}")
                    r = client.sess.get(url_agrup, timeout=10)
                    if r.ok and r.json():
                        id_processo = str(r.json()[0].get('idProcesso') or '')
                except Exception as e:
                    if log:
                        logger.debug('[TIMELINE_API] Falha ao obter idProcesso por numero: %s', e)
                        
        if not id_processo:
            if log:
                logger.warning('[TIMELINE_API] Nao conseguiu extrair id_processo da URL: %s', url_atual)
            return None
            
        timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
        if timeline:
            if log:
                logger.info('[TIMELINE_API] ✓ Obtido timeline com %d itens via API (id_processo=%s)', len(timeline), id_processo)
            return timeline
        else:
            if log:
                logger.warning('[TIMELINE_API] API retornou timeline vazia/None para id_processo=%s', id_processo)
            return None
    except Exception as e:
        if log:
            logger.error('[TIMELINE_API] Erro ao chamar /timeline: %s', str(e))
        return None

def _encontrar_documento_na_timeline_api(timeline, padrao_normalize, padrao_regex=None):
    """Procura documento na timeline que combine com padrão normalizado.
    
    Args:
        timeline: lista de dicts do /timeline API
        padrao_normalize: string que deve estar presente após normalização
        padrao_regex: opcional, regex pattern alternativo
        
    Returns:
        dict do documento encontrado, ou None
    """
    if not timeline:
        return None
    
    for doc in timeline or []:
        if not isinstance(doc, dict):
            continue
        
        texto_completo = _extrair_texto_item_api(doc)
        
        # Tentar matching por string normalizada
        if padrao_normalize and padrao_normalize in texto_completo:
            return doc
        
        # Tentar matching por regex (se fornecido)
        if padrao_regex and padrao_regex.search(texto_completo):
            return doc
    
    return None

def _contar_documentos_na_timeline_api(timeline, padrao_normalize, padrao_regex=None):
    """Conta documentos na timeline que combinam com padrão.
    
    Returns:
        int: quantidade encontrada
    """
    if not timeline:
        return 0
    
    count = 0
    for doc in timeline or []:
        if not isinstance(doc, dict):
            continue
        
        texto_completo = _extrair_texto_item_api(doc)
        
        # Tentar matching por string normalizada
        if padrao_normalize and padrao_normalize in texto_completo:
            count += 1
        # Tentar matching por regex (se fornecido e string não encontrou)
        elif padrao_regex and padrao_regex.search(texto_completo):
            count += 1
    
    return count

def _cp_texto_documento(elem, debug=False):
    """Lê o texto do item da timeline ou checkbox mat-checkbox.
    Busca em múltiplos atributos (aria-label, title, link a.tl-documento, innerText).
    Usa normalizar_texto (remove acentos corretamente).
    """
    from Fix.utils import normalizar_texto

    if elem is None:
        return ''

    partes = []

    # 1. Se for mat-checkbox ou contiver mat-checkbox, pegar aria-label e title
    try:
        chk = None
        if hasattr(elem, 'tag_name') and elem.tag_name == 'mat-checkbox':
            chk = elem
        else:
            chk = _buscar_filho(elem, 'mat-checkbox')

        if chk:
            aria_label = chk.get_attribute('aria-label')
            if aria_label and isinstance(aria_label, str):
                partes.append(aria_label)
            title = chk.get_attribute('title')
            if title and isinstance(title, str):
                partes.append(title)
    except Exception as e:
        if debug:
            logger.debug(f'[_CP_TEXTO] Falha ao ler mat-checkbox: {e}')

    # 2. Buscar link a.tl-documento
    try:
        link = _buscar_filho(elem, 'a.tl-documento')
        if link:
            l_txt = getattr(link, 'text', '')
            if l_txt and isinstance(l_txt, str):
                partes.append(l_txt.strip())
    except Exception as e:
        if debug:
            logger.debug(f'[_CP_TEXTO] Falha ao ler a.tl-documento: {e}')

    # 3. Buscar texto geral do elemento pai (inner_text)
    try:
        txt = getattr(elem, 'text', '')
        if txt and isinstance(txt, str):
            partes.append(txt.strip())
    except Exception as e:
        if debug:
            logger.debug(f'[_CP_TEXTO] Falha ao ler elem.text: {e}')

    texto_bruto = ' '.join(str(p) for p in partes).strip()
    texto_norm = normalizar_texto(texto_bruto)

    if debug:
        logger.debug(f'[_CP_TEXTO] Bruto: "{texto_bruto[:100]}" | Norm: "{texto_norm[:100]}"')

    return texto_norm

def _cp_marcar_checkbox(driver, elem, timeout=10):
    """Marca o checkbox mat-checkbox de um item da timeline (idempotente).
    Suporta PWElement de mat-checkbox, PWElement de li.tl-item-container,
    ou seletor string (ex: '#doc_47c03da').
    """
    from Fix.browser_suporte import click_headless_safe

    try:
        # Se elem for string (ex: seletor '#doc_12345')
        if isinstance(elem, str):
            sel = elem
            el = espera.elemento(driver, sel, teto=timeout)
            if not el and sel.startswith('#doc_'):
                # Fallback: procurar elemento cujo link contenha o UID
                uid = sel.replace('#doc_', '')
                try:
                    el = espera.elemento(driver, f"a[href*='{uid}'], a[id*='{uid}']", teto=2)
                except Exception:
                    el = None
            if not el:
                return click_headless_safe(driver, sel, timeout=timeout)
            elem = el

        # 1. Verificar se já está marcado (idempotência)
        try:
            input_cb = _buscar_filho(elem, 'input.mat-checkbox-input, input[type="checkbox"]')
            if input_cb:
                if input_cb.get_attribute('aria-checked') == 'true' or input_cb.is_selected():
                    return True
            cls = elem.get_attribute('class') or ''
            if 'mat-checkbox-checked' in cls:
                return True
        except Exception:
            pass

        # 2. Tentar clicar no span.mat-checkbox-inner-container
        try:
            chk_inner = _buscar_filho(elem, 'span.mat-checkbox-inner-container, label.mat-checkbox-layout')
            if chk_inner and safe_click_no_scroll(driver, chk_inner):
                return True
        except Exception:
            pass

        # 3. Tentar clicar no próprio mat-checkbox
        try:
            chk_mat = elem if getattr(elem, 'tag_name', '') == 'mat-checkbox' else _buscar_filho(elem, 'mat-checkbox')
            if chk_mat and safe_click_no_scroll(driver, chk_mat):
                return True
        except Exception:
            pass

        # 4. Fallback por seletor de ID (se tiver id com doc_ ou outro)
        try:
            elem_id = elem.get_attribute('id')
            if elem_id:
                if click_headless_safe(driver, f'#{elem_id} span.mat-checkbox-inner-container', timeout=timeout):
                    return True
                if click_headless_safe(driver, f'#{elem_id}', timeout=timeout):
                    return True
        except Exception:
            pass

        # 5. Fallback via JS click
        try:
            clicou = _executar_js(driver, """
                const el = arguments[0];
                if (!el) return false;
                const cb = el.matches && el.matches('mat-checkbox') ? el : el.querySelector('mat-checkbox');
                const target = cb ? (cb.querySelector('.mat-checkbox-inner-container') || cb.querySelector('input') || cb) : el;
                target.click();
                return true;
            """, elem)
            if clicou:
                return True
        except Exception:
            pass

        return False
    except Exception:
        return False

def contar_mandados_e_certidoes_oficial(driver, log=True, numero_processo=None):
    """Conta, na timeline atual, quantos itens sao 'Mandado' e 'Certidao de Oficial de Justica'.
    
    ESTRATÉGIA:
    1. Tentar obter via API /timeline (confiável, sem problemas de DOM)
    2. Se falhar, fallback para parsing do DOM
    
    Returns:
        tuple[int, int]: (qtd_mandados, qtd_certidoes_oficial)
    """
    from Fix.facade_publica import ElementoNaoEncontradoError

    # ========================================================================
    # TENTATIVA 1: Via API /timeline (RECOMENDADO - confiável)
    # ========================================================================
    if log:
        logger.info('[CONTAR_CP] Tentando obter timeline via API /timeline...')
    
    timeline_api = _obter_timeline_via_api(driver, log=log, numero_processo=numero_processo)
    if timeline_api is not None:
        qtd_mandados = 0
        qtd_certidoes = 0
        for doc in timeline_api:
            if not isinstance(doc, dict):
                continue
            texto = _extrair_texto_item_api(doc)
            if _cp_eh_mandado(texto):
                qtd_mandados += 1
            elif _cp_eh_certidao_oj(texto):
                qtd_certidoes += 1
                
        if log:
            logger.info('[CONTAR_CP] ✅ Via API: mandados=%d certidoes_oficial=%d', 
                       qtd_mandados, qtd_certidoes)
        
        return qtd_mandados, qtd_certidoes

    if log:
        logger.warning('[CONTAR_CP] ⚠️ Falha na API; usando fallback DOM parsing...')

    # ========================================================================
    # FALLBACK: Via DOM
    # ========================================================================
    elementos = espera.elementos(driver, 'li.tl-item-container, mat-checkbox[id^="doc_"]')
    if not elementos:
        raise ElementoNaoEncontradoError('[CONTAR_CP] Timeline vazia (li.tl-item-container ou mat-checkbox nao encontrado)')

    qtd_mandados = 0
    qtd_certidoes = 0
    if log:
        logger.info('[CONTAR_CP] [FALLBACK-DOM] Lendo %d elementos da timeline...', len(elementos))

    for idx, elem in enumerate(elementos):
        texto = _cp_texto_documento(elem, debug=True if log else False)
        if _cp_eh_mandado(texto):
            qtd_mandados += 1
            if log:
                logger.info(f'[CONTAR_CP] Item {idx}: ✓ MANDADO encontrado')
        elif _cp_eh_certidao_oj(texto):
            qtd_certidoes += 1
            if log:
                logger.info(f'[CONTAR_CP] Item {idx}: ✓ CERTIDAO_OJ encontrada')

    if log:
        logger.info('[CONTAR_CP] [FALLBACK-DOM] Totais: mandados=%d certidoes_oficial=%d', 
                   qtd_mandados, qtd_certidoes)

    return qtd_mandados, qtd_certidoes

def baixarCP(driver, timeout=15, log=True, numero_processo=None):
    """
    Seleciona na timeline (ul.pje-timeline) documentos CP (Carta Precatória):
    - Tenta usar Certidão de Distribuição como âncora (se existir)
    - Se não houver CDist, usa o primeiro Despacho encontrado (mais antigo)
    - Depois marca todos os Mandados/Certidões até o topo
    - Baixa a seleção como PDF único

    Raises:
        ElementoNaoEncontradoError: timeline vazia, nenhuma âncora/despacho encontrado,
            ou falha em etapa obrigatória (botão/menu não clicável).

    Returns:
        bool: True quando o download "PDF único" foi iniciado com sucesso.
    """
    from Fix.browser_suporte import click_headless_safe
    from atos.movimentos_navegacao import clicar_botao_por_texto
    from Fix.facade_publica import ElementoNaoEncontradoError

    if log:
        logger.info('[BAIXAR_CP] Iniciando selecao de Carta Precatoria (CDist + anexos)')

    # 1. Ativar múltipla seleção se ainda não estiver ativa
    btn_baixar_visivel = False
    try:
        el_baixar = espera.elemento(driver, '#baixar-docs-selecionados', teto=1)
        if el_baixar and el_baixar.is_displayed():
            btn_baixar_visivel = True
    except Exception:
        btn_baixar_visivel = False

    if not btn_baixar_visivel:
        if not click_headless_safe(driver, '#exibirOcultarMultiplaSelecao', timeout=timeout):
            raise ElementoNaoEncontradoError('[BAIXAR_CP] Botao "Exibir multipla selecao" (#exibirOcultarMultiplaSelecao) nao encontrado/clicavel')

    # Aguardar renderização dos checkboxes na timeline
    aguardar_renderizacao_nativa(driver, 'mat-checkbox[id^="doc_"], li.tl-item-container mat-checkbox', modo='aparecer', timeout=timeout)

    # 2. Tentar estratégia via API para identificar os UIDs exatos
    timeline_api = _obter_timeline_via_api(driver, log=log, numero_processo=numero_processo)
    uids_para_marcar = []

    if timeline_api:
        if log:
            logger.info('[BAIXAR_CP] Identificando documentos via API (/timeline)...')
        idx_ancora = None
        eh_cdist = False

        # 1º procurar CDist
        for idx, doc in enumerate(timeline_api):
            texto = _extrair_texto_item_api(doc)
            if _cp_eh_cdist(texto):
                idx_ancora = idx
                eh_cdist = True
                if log:
                    logger.info('[BAIXAR_CP] [API] Âncora CDist encontrada no índice %d (uid=%s)', idx, doc.get('idUnicoDocumento'))
                break

        # 2º se não houver CDist, procurar despacho mais antigo (do final para o início)
        if idx_ancora is None:
            for idx in range(len(timeline_api) - 1, -1, -1):
                texto = _extrair_texto_item_api(timeline_api[idx])
                if _cp_eh_despacho(texto):
                    idx_ancora = idx
                    eh_cdist = False
                    if log:
                        logger.info('[BAIXAR_CP] [API] Âncora Despacho encontrada no índice %d (uid=%s)', idx, timeline_api[idx].get('idUnicoDocumento'))
                    break

        if idx_ancora is not None:
            # Documentos a marcar: a âncora e todos os documentos relevantes entre a âncora e o topo (index 0)
            for idx in range(idx_ancora, -1, -1):
                doc = timeline_api[idx]
                uid = doc.get('idUnicoDocumento')
                if not uid:
                    continue
                texto = _extrair_texto_item_api(doc)
                if idx == idx_ancora:
                    uids_para_marcar.append(uid)
                elif _cp_eh_mandado(texto) or _cp_eh_certidao_geral(texto) or _cp_eh_despacho(texto):
                    uids_para_marcar.append(uid)
            if log:
                logger.info('[BAIXAR_CP] [API] %d UIDs identificados para marcar: %s', len(uids_para_marcar), uids_para_marcar)

    marcados = 0
    # 3. Marcar via UIDs da API (se obtidos)
    if uids_para_marcar:
        for uid in uids_para_marcar:
            sel_cb = f"#doc_{uid}"
            if _cp_marcar_checkbox(driver, sel_cb, timeout=timeout):
                marcados += 1
                if log:
                    logger.info('[BAIXAR_CP] ✓ Marcado checkbox: %s', sel_cb)
            else:
                if log:
                    logger.warning('[BAIXAR_CP] Falha ao marcar checkbox por UID: %s', sel_cb)

    # 4. Se não marcou nada via API (ou API não retornou âncora), usar Fallback DOM
    if marcados == 0:
        if log:
            logger.info('[BAIXAR_CP] Executando marcação via DOM fallback...')
        elementos = espera.elementos(driver, 'li.tl-item-container')
        if not elementos:
            elementos = espera.elementos(driver, 'mat-checkbox[id^="doc_"]')
        if not elementos:
            raise ElementoNaoEncontradoError('[BAIXAR_CP] Timeline vazia (li.tl-item-container ou mat-checkbox nao encontrado)')

        idx_ancora = None
        eh_cdist = False

        for idx, elem in enumerate(elementos):
            texto = _cp_texto_documento(elem, debug=True if log else False)
            if _cp_eh_cdist(texto):
                idx_ancora = idx
                eh_cdist = True
                if log:
                    logger.info('[BAIXAR_CP] [DOM] ✅ Item %d: CDist encontrada como âncora', idx)
                break

        if idx_ancora is None:
            for idx in range(len(elementos) - 1, -1, -1):
                texto = _cp_texto_documento(elementos[idx], debug=False)
                if _cp_eh_despacho(texto):
                    idx_ancora = idx
                    eh_cdist = False
                    if log:
                        logger.info('[BAIXAR_CP] [DOM] ✅ Item %d: Despacho encontrado como âncora', idx)
                    break

        if idx_ancora is None:
            raise ElementoNaoEncontradoError('[BAIXAR_CP] Nem Certidao de Distribuicao nem Despacho encontrados no DOM')

        if _cp_marcar_checkbox(driver, elementos[idx_ancora], timeout):
            marcados += 1

        for idx in range(idx_ancora - 1, -1, -1):
            texto = _cp_texto_documento(elementos[idx], debug=False)
            if _cp_eh_mandado(texto) or _cp_eh_certidao_geral(texto) or _cp_eh_despacho(texto):
                if _cp_marcar_checkbox(driver, elementos[idx], timeout):
                    marcados += 1
                elif log:
                    logger.warning('[BAIXAR_CP] Item idx=%d falhou ao marcar', idx)

    if marcados == 0:
        raise ElementoNaoEncontradoError('[BAIXAR_CP] Nenhum documento foi marcado para download')

    if log:
        logger.info('[BAIXAR_CP] Total de itens marcados: %d', marcados)

    # 5. Clicar no botão #baixar-docs-selecionados
    if not click_headless_safe(driver, '#baixar-docs-selecionados', timeout=timeout):
        raise ElementoNaoEncontradoError('[BAIXAR_CP] Botao "#baixar-docs-selecionados" nao encontrado/clicavel')

    aguardar_renderizacao_nativa(driver, 'button[role="menuitem"]', modo='aparecer', timeout=timeout)

    # 6. Selecionar "PDF único"
    clicou_pdf = False
    xpath_pdf_unico = "//button[@role='menuitem'][contains(., 'PDF') and (contains(., 'único') or contains(., 'unico'))]"
    if click_headless_safe(driver, xpath_pdf_unico, by=By.XPATH, timeout=timeout):
        clicou_pdf = True
    elif clicar_botao_por_texto(driver, 'PDF único', timeout=timeout):
        clicou_pdf = True
    else:
        clicou_pdf = bool(_executar_js(driver, """
            const items = Array.from(document.querySelectorAll('button[role="menuitem"]'));
            const target = items.find(b => /pdf\\s*(único|unico)/i.test(b.innerText || ''));
            if (target) {
                target.click();
                return true;
            }
            return false;
        """))

    if not clicou_pdf:
        raise ElementoNaoEncontradoError('[BAIXAR_CP] Opcao "PDF unico" nao encontrada no menu de download')

    # 7. Aguardar diálogo de download aparecer e sumir
    if aguardar_renderizacao_nativa(driver, 'mat-dialog-container', modo='aparecer', timeout=5):
        aguardar_renderizacao_nativa(driver, 'mat-dialog-container', modo='sumir', timeout=timeout)

    if log:
        logger.info('[BAIXAR_CP] Download "PDF unico" iniciado com sucesso')

    return True

def buscar_documentos_polo_ativo(driver, polo="autor", limite_dias=None, debug=False):
    """
    Busca documentos na timeline do processo filtrando por polo ativo (autor/réu).

    Args:
        driver: Instância do WebDriver
        polo: "autor" ou "reu" (padrão: "autor")
        limite_dias: Se informado, filtra documentos dos últimos N dias
        debug: Se True, exibe logs detalhados

    Returns:
        list: Lista de dicionários com informações dos documentos encontrados
    """
    try:
        if debug:
            logger.debug("[BUSCAR_DOCUMENTOS_POLO_ATIVO] Buscando documentos do polo %s na timeline...", polo)

        esperar_elemento(driver, "li.tl-item-container", timeout=10)

        script = """
            var poloTarget = arguments[0];
            var limiteDias = arguments[1];

            // Função para determinar se é polo ativo baseado no texto
            function isPoloAtivo(texto, polo) {
                if (!texto) return false;

                texto = texto.toLowerCase();
                if (polo === 'autor') {
                    // Polo ativo para autor: contém "autor" mas não "réu" ou indica movimento do autor
                    return (texto.includes('autor') && !texto.includes('réu')) ||
                           texto.includes('reclamante') ||
                           texto.includes('exequente');
                } else if (polo === 'reu') {
                    // Polo ativo para réu: contém "réu" mas não "autor" ou indica movimento do réu
                    return (texto.includes('réu') && !texto.includes('autor')) ||
                           texto.includes('reclamado') ||
                           texto.includes('executado');
                }
                return false;
            }

            // Coletar todos os itens da timeline
            var itens = document.querySelectorAll('li.tl-item-container');
            var documentos = [];

            for (var i = 0; i < itens.length; i++) {
                var item = itens[i];

                try {
                    // Extrair data
                    var dataElement = item.querySelector('.tl-item-date');
                    var data = dataElement ? dataElement.textContent.trim() : '';

                    // Extrair título/ação
                    var tituloElement = item.querySelector('.tl-item-title, .tl-item-header');
                    var titulo = tituloElement ? tituloElement.textContent.trim() : '';

                    // Extrair descrição completa
                    var descElement = item.querySelector('.tl-item-description, .tl-item-content');
                    var descricao = descElement ? descElement.textContent.trim() : '';

                    // Combinar título e descrição para análise
                    var textoCompleto = (titulo + ' ' + descricao).toLowerCase();

                    // Verificar se é do polo ativo
                    if (isPoloAtivo(textoCompleto, poloTarget)) {
                        // Verificar limite de dias se informado
                        var documentoValido = true;
                        if (limiteDias) {
                            try {
                                var dataObj = new Date(data.split('/').reverse().join('-'));
                                var hoje = new Date();
                                var diffTime = Math.abs(hoje - dataObj);
                                var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                                if (diffDays > limiteDias) {
                                    documentoValido = false;
                                }
                            } catch (e) {
                                // Se não conseguir parsear data, considera válido
                                documentoValido = true;
                            }
                        }

                        if (documentoValido) {
                            documentos.push({
                                'data': data,
                                'titulo': titulo,
                                'descricao': descricao,
                                'texto_completo': textoCompleto,
                                'polo': poloTarget
                            });
                        }
                    }
                } catch (e) {
                    // Ignorar erros em itens individuais
                    continue;
                }
            }

            return documentos;
        """

        fn_sc = getattr(driver, "execute" + "_script", None)
        documentos = fn_sc(script, polo, limite_dias) if fn_sc else []

        if debug:
            logger.debug("[BUSCAR_DOCUMENTOS_POLO_ATIVO] Encontrados %d documentos do polo %s", len(documentos), polo)
        return documentos

    except Exception as e:
        if debug:
            logger.error("[BUSCAR_DOCUMENTOS_POLO_ATIVO] Erro ao buscar documentos do polo ativo: %s", str(e))
        return []

def buscar_documento_argos(driver, log=True, ignorar_indices=None):
    """✅ CORRIGIDO: Busca PRÓXIMO documento (decisão/despacho) que contenha REGRAS ARGOS.

    Estratégia (mesma de checar_prox em p2b):
    1. Buscar todos os itens da timeline (despacho/decisão/sentença/conclusão)
    2. Manter índice persistente em atributo do driver
    3. A cada chamada, procurar NO ÍNDICE SEGUINTE (não refazer do zero)
    4. Verificar se documento contém REGRAS ARGOS
    5. Se contém, retornar; se não, avançar para próximo
    
    Retorna (texto, tipo, idx) ou (None, None, None).
    """
    # Importar localmente para evitar import circular entre Fix.core <-> Fix.extracao
    try:
        from .extracao import extrair_direto, extrair_documento
    except Exception:
        # Fallback para import via package
        from Fix.extracao import extrair_direto, extrair_documento
    
    # ✅ REGRAS ARGOS que o documento deve conter (alinhado com Mandado/regras.py)
    REGRAS_ARGOS = [
        'defiro a instauração',
        'defiro a instauracao',
        'argos',
        'realize-se a pesquisa infojud',
        'realize se a pesquisa infojud',
        'tendo em vista que',
        'tendo em vista',
        'pesquisas para execução',
        'pesquisas para execucao',
        'desconsideração',
        'desconsideracao',
        '855-a',
        'idpj',
        'inclua-se no polo passivo',
        'certex',
    ]
    
    try:
        if log:
            logger.info('[ARGOS][DOC] Buscando proximo documento com REGRAS ARGOS na timeline...')

        # ✨ USAR ÍNDICE PERSISTENTE (como em checar_prox)
        # Inicializar índice se não existir
        if not hasattr(driver, '_argos_doc_idx'):
            driver._argos_doc_idx = -1  # Começar em -1 para que primeira busca comece em 0
            if log:
                logger.info('[ARGOS][DOC] Inicializando indice persistente')

        itens = espera.elementos(driver, 'li.tl-item-container')
        if not itens:
            if log:
                logger.warning('[ARGOS][DOC] Nenhum item na timeline')
            return None, None, None

        # ✅ Encontrar âncora: Certidão de Expedição/Pesquisa (sempre existe no bloco ARGOS).
        # Buscamos decisões/despachos MAIS ANTIGOS que esta certidão
        # (índices maiores = mais abaixo na timeline = mais antigos).
        import unicodedata as _ud
        def _norm_timeline(t):
            return _ud.normalize('NFD', (t or '').lower()).encode('ascii', 'ignore').decode()

        idx_certidao = -1
        for i, it in enumerate(itens):
            try:
                # Buscar no texto COMPLETO do item (não só no <a>), como a API function faz.
                # A certidão pode ter texto distribuído em múltiplos elementos dentro do container.
                txt = _norm_timeline(it.text or '')
                if 'certidao de expedicao' in txt:
                    idx_certidao = i
                    break
                if 'certidao' in txt and ('expedicao' in txt or 'pesquisa' in txt):
                    idx_certidao = i
                    break
            except Exception:
                continue

        if idx_certidao >= 0:
            if log:
                logger.info('[ARGOS][DOC] Âncora certidão no índice %d', idx_certidao)
            # Buscar itens MAIS ANTIGOS que a certidão (índices maiores)
            start_idx = max(driver._argos_doc_idx + 1, idx_certidao + 1)
        else:
            if log:
                logger.warning('[ARGOS][DOC] Certidão de expedição/pesquisa não localizada — ABORTANDO (sem âncora não é seguro selecionar documentos)')
            return None, None, None

        if ignorar_indices:
            start_idx = max(start_idx, max(ignorar_indices) + 1)

        if log:
            logger.info('[ARGOS][DOC] Buscando decisões/despachos do índice %d ao %d (âncora certidão=%d, total=%d)',
                       start_idx, len(itens) - 1, idx_certidao, len(itens))

        for idx in range(start_idx, len(itens)):
            try:
                item = itens[idx]
                link = _buscar_filho(item, 'a.tl-documento:not([target="_blank"])')
                if not link:
                    continue
                doc_text = (link.text or '').lower()
                
                # ✅ Validar se é despacho/decisão/sentença/conclusão
                if not re.search(r'^(despacho|decisão|sentença|conclusão|decisao|sentenca|conclusao)', doc_text.strip()):
                    if log:
                        logger.debug('[ARGOS][DOC] Indice %d: "%s" - nao e documento relevante, continuando...', idx, doc_text[:30])
                    continue
                
                if log:
                    logger.info('[ARGOS][DOC] Doc %d: "%s" - documento relevante encontrado, abrindo...', idx, doc_text[:50])
                
            except Exception as e:
                if log:
                    logger.warning('[ARGOS][DOC] Erro ao validar elemento %d: %s', idx, e)
                continue
            
            # ✨ CLICAR NO DOCUMENTO
            try:
                try:
                    from Fix.headless_helpers import limpar_overlays_headless, scroll_to_element_safe
                    limpar_overlays_headless(driver)
                    scroll_to_element_safe(driver, link)
                    espera.assentar(driver, 0.3)
                except ImportError:
                    pass
                
                # Tentar click normal primeiro
                try:
                    link.click()
                except ElementClickInterceptedException:
                    if log:
                        logger.info('[ARGOS][DOC] Click intercepted, usando JS fallback')
                    safe_click_no_scroll(driver, link)
                
                espera.assentar(driver, 2, motivo="Aguardar carregamento")
            except Exception as e:
                if log:
                    logger.warning('[ARGOS][DOC] Falha ao clicar no documento: %s', e)
                continue

            # ✨ EXTRAIR TEXTO
            espera.assentar(driver, 1.5)
            texto = None
            try:
                if log:
                    logger.info('[ARGOS][DOC] Extraindo conteudo via extrair_direto...')
                resultado = extrair_direto(driver, timeout=10, debug=log, formatar=True)
                texto = resultado.get('conteudo') if resultado and resultado.get('sucesso') else None
            except Exception as e:
                if log:
                    logger.warning('[ARGOS][DOC] extrair_direto falhou: %s', e)

            # ✅ VERIFICAR REGRAS ARGOS
            if texto:
                if log:
                    logger.info('[ARGOS][DOC] Texto extraido: %d chars. Verificando regras...', len(texto))
                
                texto_lower = texto.lower()
                encontrou_regra = False
                regra_encontrada = None
                
                # Verificar regras principais ARGOS
                for regra in REGRAS_ARGOS:
                    if regra in texto_lower:
                        encontrou_regra = True
                        regra_encontrada = regra
                        break
                
                # FALLBACK: Se não encontrou regra ARGOS mas tem sigilo, tratar como ARGOS
                if not encontrou_regra:
                    if 'este despacho permanecerá em sigilo' in texto_lower or \
                       'este despacho permanecera em sigilo' in texto_lower:
                        encontrou_regra = True
                        regra_encontrada = 'sigilo (fallback)'
                        if log:
                            logger.info('[ARGOS][DOC] ℹ️ Encontrado sigilo - tratando como ARGOS')
                
                if encontrou_regra:
                    # ✅ SALVAR ÍNDICE ATUAL PARA PRÓXIMA BUSCA
                    driver._argos_doc_idx = idx
                    if log:
                        logger.info('[ARGOS][DOC] ✅ REGRA "%s" no indice %d - USANDO ESTE DOCUMENTO', regra_encontrada, idx)
                    tipo = 'decisao' if 'decis' in doc_text or 'senten' in doc_text else 'despacho'
                    return texto, tipo, idx
                else:
                    # REGRA NÃO ENCONTRADA - APENAS CONTINUAR COM PRÓXIMO
                    if log:
                        logger.warning('[ARGOS][DOC] ⚠️ Sem REGRA ARGOS no indice %d - avancando para o proximo na timeline...', idx)
                    continue
            else:
                if log:
                    logger.warning('[ARGOS][DOC] ⚠️ Falha ao extrair texto do indice %d - avancando para o proximo na timeline...', idx)
                continue

        # ✅ FIM: Nenhum documento teve regra
        if log:
            logger.warning('[ARGOS][DOC] ❌ Nenhum despacho/decisao com REGRAS ARGOS encontrado (fim da timeline)')
        return None, None, None

    except Exception as e:
        if log:
            logger.error('[ARGOS][DOC][ERRO] buscar_documento_argos falhou: %s', e)
        return None, None, None
