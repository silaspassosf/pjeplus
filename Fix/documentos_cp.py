"""documentos_cp — extraído de Fix/core.py (F7: split verbatim, re-exportado pelo core)."""

import os
import re
import unicodedata

from .log import logger
from Play.pjeplay.errors import ElementClickInterceptedException
from Play.pjeplay.locators import By

from Fix import espera

from .navegacao import _buscar_filho, _executar_js, safe_click_no_scroll  # noqa: F401
from .navegacao_espera import aguardar_renderizacao_nativa, esperar_elemento  # noqa: F401

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
    """Aplica visibilidade a documentos sigilosos anexados automaticamente, conforme lógica do gigs-plugin.js."""
    try:
        try:
            from Fix.headless_helpers import limpar_overlays_headless
            limpar_overlays_headless(driver)
        except ImportError:
            pass

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
        btn_multi = espera.elemento(driver, 'button[aria-label="Exibir múltipla seleção."]')
        if btn_multi:
            try:
                btn_multi.click()
            except ElementClickInterceptedException:
                safe_click_no_scroll(driver, btn_multi)
        espera.elemento(driver, f'mat-card[id*="{id_documento}"] mat-checkbox', teto=5, visivel=False)
        mat_checkbox = espera.elemento(driver, f'mat-card[id*="{id_documento}"] mat-checkbox label')
        if mat_checkbox:
            try:
                mat_checkbox.click()
            except ElementClickInterceptedException:
                safe_click_no_scroll(driver, mat_checkbox)
        espera.elemento(driver, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]', teto=5, visivel=False)
        btn_visibilidade = espera.elemento(driver, 'div.div-todas-atividades-em-lote button[mattooltip="Visibilidade para Sigilo"]')
        if btn_visibilidade:
            try:
                btn_visibilidade.click()
            except ElementClickInterceptedException:
                safe_click_no_scroll(driver, btn_visibilidade)
        # Aguardar modal de sigilo
        espera.elemento(driver, 'pje-data-table[nametabela="Tabela de Controle de Sigilo"]', teto=5, visivel=False)
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
        btn_salvar = espera.elemento(driver, '//button[.//span[contains(text(),"Salvar")]]', teto=10)
        if btn_salvar:
            btn_salvar.click()
        espera.ate_sumir(
            driver,
            '//button[.//span[contains(text(),"Salvar")]]/ancestor::div[contains(@class,"cdk-overlay")]',
            teto=5,
        )
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
    """Cria botões com ícones e ações específicas, replicando a funcionalidade do MaisPje, usando o driver já aute..."""
    base_element = espera.elemento(driver, "#pjextension_bt_detalhes_base", teto=10, visivel=False)
    if base_element is None:
        base_element = espera.elemento(driver, "body")

    fn_sc = getattr(driver, "execute" + "_script", None)
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
    """Busca o último documento do tipo 'mandado' na timeline do processo."""
    try:
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
    """Busca o último documento do tipo 'mandado' na timeline do processo."""
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
    """✅ BUSCA DOCUMENTOS DO BLOCO ARGOS NA ORDEM CORRETA"""
    try:
        if log:
            logger.debug('[DOCUMENTOS_SEQUENCIAIS] Buscando documentos do bloco ARGOS')

        aguardar_renderizacao_nativa(driver, timeout=10)
        elementos = espera.elementos(driver, "li.tl-item-container", teto=8)

        if not elementos:
            if log:
                logger.error('[DOCUMENTOS_SEQUENCIAIS] Timeline vazia')
            return []

        # anteriores e pulava a retirada de sigilo dos documentos atuais.
        idxs_devolucao = []
        for idx, elem in enumerate(elementos):
            texto = _norm(elem.text.strip())
            if 'certidao de devolucao' in texto:
                idxs_devolucao.append(idx)
                if log:
                    logger.debug('[DOCUMENTOS_SEQUENCIAIS] Certidao de devolucao idx=%d: %s...', idx, texto[:50])

        if not idxs_devolucao:
            if log:
                logger.error('[DOCUMENTOS_SEQUENCIAIS] Certidao de devolucao nao encontrada')
            return []

        if len(idxs_devolucao) > 1 and log:
            logger.info(
                '[DOCUMENTOS_SEQUENCIAIS] %d certidões de devolução na timeline — usando a mais recente (idx=%d) como âncora',
                len(idxs_devolucao), idxs_devolucao[0],
            )

        idx_ancora = idxs_devolucao[0]

        idx_decisao = None
        for idx in range(idx_ancora + 1, len(elementos)):
            texto = _norm(elementos[idx].text.strip())
            if 'decisao(' in texto:
                idx_decisao = idx
                if log:
                    logger.debug('[DOCUMENTOS_SEQUENCIAIS] Encontrado: Decisao - %s...', texto[:50])
                break

        if idx_decisao is None:
            for idx in range(idx_ancora + 1, len(elementos)):
                texto = _norm(elementos[idx].text.strip())
                if 'despacho(' in texto:
                    idx_decisao = idx
                    if log:
                        logger.debug('[DOCUMENTOS_SEQUENCIAIS] Fallback Despacho como fim do bloco idx=%d', idx)
                    break

        if idx_decisao is None:
            if log:
                logger.error('[DOCUMENTOS_SEQUENCIAIS] Decisao/Despacho nao encontrada apos certidao')
            return []

        resultados = [elementos[idx_ancora]]

        tipos_meio = {
            'Certidao de devolucao': ['certidao de devolucao'],
            'Certidao de expedicao': ['certidao de expedicao'],
            'Certidao de pesquisa patrimonial': ['certidao de pesquisa patrimonial'],
            'Planilha': ['planilha de atualizacao', 'planilha de calculo'],
            'Ordem de pesquisa': ['ordem de pesquisa'],
            'Intimacao': ['intimacao('],
        }

        for idx in range(idx_ancora + 1, idx_decisao):
            elem = elementos[idx]
            texto = _norm(elem.text.strip())
            matched = False
            for tipo_nome, palavras in tipos_meio.items():
                if any(palavra in texto for palavra in palavras):
                    resultados.append(elem)
                    matched = True
                    if log:
                        logger.debug('[DOCUMENTOS_SEQUENCIAIS] Encontrado: %s - %s...', tipo_nome, texto[:50])
                    break
            if matched:
                continue

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
    """Obtem timeline via API REST (mais confiavel que DOM parsing)."""
    try:
        from Fix.variaveis import cliente_para
        url_atual = getattr(driver, 'current_url', '') or ''

        id_processo = None
        m = re.search(r'/processo/(\d+)', url_atual)
        if m:
            id_processo = m.group(1)

        client = cliente_para(driver)
        if not client:
            if log:
                logger.warning('[TIMELINE_API] Nao conseguiu extrair sessao do driver')
            return None

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
    """Procura documento na timeline que combine com padrão normalizado."""
    if not timeline:
        return None

    for doc in timeline or []:
        if not isinstance(doc, dict):
            continue

        texto_completo = _extrair_texto_item_api(doc)

        if padrao_normalize and padrao_normalize in texto_completo:
            return doc

        if padrao_regex and padrao_regex.search(texto_completo):
            return doc

    return None

def _contar_documentos_na_timeline_api(timeline, padrao_normalize, padrao_regex=None):
    """Conta documentos na timeline que combinam com padrão."""
    if not timeline:
        return 0

    count = 0
    for doc in timeline or []:
        if not isinstance(doc, dict):
            continue

        texto_completo = _extrair_texto_item_api(doc)

        if padrao_normalize and padrao_normalize in texto_completo:
            count += 1
        elif padrao_regex and padrao_regex.search(texto_completo):
            count += 1

    return count

def _cp_texto_documento(elem, debug=False):
    """Lê o texto do item da timeline ou checkbox mat-checkbox."""
    from Fix.utils import normalizar_texto

    if elem is None:
        return ''

    partes = []

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

    try:
        link = _buscar_filho(elem, 'a.tl-documento')
        if link:
            l_txt = getattr(link, 'text', '')
            if l_txt and isinstance(l_txt, str):
                partes.append(l_txt.strip())
    except Exception as e:
        if debug:
            logger.debug(f'[_CP_TEXTO] Falha ao ler a.tl-documento: {e}')

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
    """Marca o checkbox mat-checkbox de um item da timeline (idempotente)."""
    from Fix.browser_suporte import click_headless_safe

    try:
        if isinstance(elem, str):
            sel = elem
            el = espera.elemento(driver, sel, teto=timeout)
            if not el and sel.startswith('#doc_'):
                uid = sel.replace('#doc_', '')
                try:
                    el = espera.elemento(driver, f"a[href*='{uid}'], a[id*='{uid}']", teto=2)
                except Exception:
                    el = None
            if not el:
                return click_headless_safe(driver, sel, timeout=timeout)
            elem = el

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

        try:
            chk_inner = _buscar_filho(elem, 'span.mat-checkbox-inner-container, label.mat-checkbox-layout')
            if chk_inner and safe_click_no_scroll(driver, chk_inner):
                return True
        except Exception:
            pass

        try:
            chk_mat = elem if getattr(elem, 'tag_name', '') == 'mat-checkbox' else _buscar_filho(elem, 'mat-checkbox')
            if chk_mat and safe_click_no_scroll(driver, chk_mat):
                return True
        except Exception:
            pass

        try:
            elem_id = elem.get_attribute('id')
            if elem_id:
                if click_headless_safe(driver, f'#{elem_id} span.mat-checkbox-inner-container', timeout=timeout):
                    return True
                if click_headless_safe(driver, f'#{elem_id}', timeout=timeout):
                    return True
        except Exception:
            pass

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
    """Conta, na timeline atual, quantos itens sao 'Mandado' e 'Certidao de Oficial de Justica'."""
    from Fix.facade_publica import ElementoNaoEncontradoError

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
    """Seleciona na timeline (ul.pje-timeline) documentos CP (Carta Precatória):"""
    from Fix.browser_suporte import click_headless_safe
    from atos.movimentos_navegacao import clicar_botao_por_texto
    from Fix.facade_publica import ElementoNaoEncontradoError

    if log:
        logger.info('[BAIXAR_CP] Iniciando selecao de Carta Precatoria (CDist + anexos)')

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

    aguardar_renderizacao_nativa(driver, 'mat-checkbox[id^="doc_"], li.tl-item-container mat-checkbox', modo='aparecer', timeout=timeout)

    timeline_api = _obter_timeline_via_api(driver, log=log, numero_processo=numero_processo)
    uids_para_marcar = []

    if timeline_api:
        if log:
            logger.info('[BAIXAR_CP] Identificando documentos via API (/timeline)...')
        idx_ancora = None
        eh_cdist = False

        for idx, doc in enumerate(timeline_api):
            texto = _extrair_texto_item_api(doc)
            if _cp_eh_cdist(texto):
                idx_ancora = idx
                eh_cdist = True
                if log:
                    logger.info('[BAIXAR_CP] [API] Âncora CDist encontrada no índice %d (uid=%s)', idx, doc.get('idUnicoDocumento'))
                break

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

    if not click_headless_safe(driver, '#baixar-docs-selecionados', timeout=timeout):
        raise ElementoNaoEncontradoError('[BAIXAR_CP] Botao "#baixar-docs-selecionados" nao encontrado/clicavel')

    aguardar_renderizacao_nativa(driver, 'button[role="menuitem"]', modo='aparecer', timeout=timeout)

    def _clicar_pdf_unico() -> bool:
        xpath_pdf_unico = "//button[@role='menuitem'][contains(., 'PDF') and (contains(., 'único') or contains(., 'unico'))]"
        if click_headless_safe(driver, xpath_pdf_unico, by=By.XPATH, timeout=timeout):
            return True
        if clicar_botao_por_texto(driver, 'PDF único', timeout=timeout):
            return True
        return bool(_executar_js(driver, """
            const items = Array.from(document.querySelectorAll('button[role="menuitem"]'));
            const target = items.find(b => /pdf\\s*(único|unico)/i.test(b.innerText || ''));
            if (target) {
                target.click();
                return true;
            }
            return false;
        """))

    page = getattr(driver, 'page', None)
    download = None
    if page is not None:
        try:
            with page.expect_download(timeout=timeout * 1000) as dl_info:
                if not _clicar_pdf_unico():
                    raise ElementoNaoEncontradoError('[BAIXAR_CP] Opcao "PDF unico" nao encontrada no menu de download')
            download = dl_info.value
        except ElementoNaoEncontradoError:
            raise
        except Exception as e:
            if log:
                logger.warning('[BAIXAR_CP] download nao capturado pelo Playwright: %s', e)
    else:
        if not _clicar_pdf_unico():
            raise ElementoNaoEncontradoError('[BAIXAR_CP] Opcao "PDF unico" nao encontrada no menu de download')

    if download is not None:
        from Play.pjeplay.launcher import DOWNLOADS
        nome = download.suggested_filename
        if not isinstance(nome, str) or not nome.strip():
            nome = 'documento.pdf'
        nome = os.path.basename(nome.replace('\\', '/'))
        destino = os.path.join(DOWNLOADS, nome)
        base, ext = os.path.splitext(destino)
        n = 1
        while os.path.exists(destino):
            destino = f'{base} ({n}){ext}'
            n += 1
        try:
            download.save_as(destino)
        except Exception as e:
            raise ElementoNaoEncontradoError(f'[BAIXAR_CP] Falha ao salvar o PDF em {destino}: {e}')
        if log:
            logger.info('[BAIXAR_CP] PDF salvo em %s', destino)
    else:
        if log:
            logger.warning('[BAIXAR_CP] clique em "PDF unico" feito, mas nenhum download foi capturado')

    if aguardar_renderizacao_nativa(driver, 'mat-dialog-container', modo='aparecer', timeout=5):
        aguardar_renderizacao_nativa(driver, 'mat-dialog-container', modo='sumir', timeout=timeout)

    if log:
        logger.info('[BAIXAR_CP] Download "PDF unico" concluido')

    return True

def buscar_documentos_polo_ativo(driver, polo="autor", limite_dias=None, debug=False):
    """Busca documentos na timeline do processo filtrando por polo ativo (autor/réu)."""
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
    """✅ CORRIGIDO: Busca PRÓXIMO documento (decisão/despacho) que contenha REGRAS ARGOS."""
    # Importar localmente para evitar import circular entre Fix.core <-> Fix.extracao
    try:
        from .extracao import extrair_direto, extrair_documento
    except Exception:
        from Fix.extracao import extrair_direto, extrair_documento

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

        if not hasattr(driver, '_argos_doc_idx'):
            driver._argos_doc_idx = -1
            if log:
                logger.info('[ARGOS][DOC] Inicializando indice persistente')

        itens = espera.elementos(driver, 'li.tl-item-container')
        if not itens:
            if log:
                logger.warning('[ARGOS][DOC] Nenhum item na timeline')
            return None, None, None

        import unicodedata as _ud
        def _norm_timeline(t):
            return _ud.normalize('NFD', (t or '').lower()).encode('ascii', 'ignore').decode()

        idx_certidao = -1
        for i, it in enumerate(itens):
            try:
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

            try:
                try:
                    from Fix.headless_helpers import limpar_overlays_headless, scroll_to_element_safe
                    limpar_overlays_headless(driver)
                    scroll_to_element_safe(driver, link)
                    espera.assentar(driver, 0.3)
                except ImportError:
                    pass

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

            if texto:
                if log:
                    logger.info('[ARGOS][DOC] Texto extraido: %d chars. Verificando regras...', len(texto))

                texto_lower = texto.lower()
                encontrou_regra = False
                regra_encontrada = None

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
                    driver._argos_doc_idx = idx
                    if log:
                        logger.info('[ARGOS][DOC] ✅ REGRA "%s" no indice %d - USANDO ESTE DOCUMENTO', regra_encontrada, idx)
                    tipo = 'decisao' if 'decis' in doc_text or 'senten' in doc_text else 'despacho'
                    return texto, tipo, idx
                else:
                    if log:
                        logger.warning('[ARGOS][DOC] ⚠️ Sem REGRA ARGOS no indice %d - avancando para o proximo na timeline...', idx)
                    continue
            else:
                if log:
                    logger.warning('[ARGOS][DOC] ⚠️ Falha ao extrair texto do indice %d - avancando para o proximo na timeline...', idx)
                continue

        if log:
            logger.warning('[ARGOS][DOC] ❌ Nenhum despacho/decisao com REGRAS ARGOS encontrado (fim da timeline)')
        return None, None, None

    except Exception as e:
        if log:
            logger.error('[ARGOS][DOC][ERRO] buscar_documento_argos falhou: %s', e)
        return None, None, None
