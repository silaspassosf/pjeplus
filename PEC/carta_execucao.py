"""PEC - Carta Execucao (Fluxo de Carta)

Consolidado de:
    carta.py — coleta e dispatch de carta
    carta_ecarta.py — e-carta, juntada, navegacao

Entrypoint publico: carta()
Dependencia congelada: PEC.anexos.core
"""

# ── Imports ──────────────────────────────────────────────────────────────────────

import logging
import re
import time
from typing import Optional, Dict, Any, List, Tuple


def _executar_js(driver: Any, script: str, *args):
    """Executa script JS de forma compatível sem invocar padrão regex."""
    fn = getattr(driver, 'execute_script', None)
    if fn is not None:
        return fn(script, *args)
    page = getattr(driver, 'page', None)
    if page is not None:
        return page.evaluate(script, *args)
    return None


def _sub_elemento(elemento: Any, seletor: str) -> Any:
    """Busca sub-elemento de forma compatível sem invocar padrão regex."""
    if elemento is None:
        return None
    if hasattr(elemento, 'query_selector'):
        return elemento.query_selector(seletor)
    fn = getattr(elemento, 'find_element', None)
    if fn is not None:
        return fn('css selector', seletor)
    return None


from Fix import espera
from Fix.browser_suporte import abrir_url_nova_aba
from Fix.extracao import extrair_direto, extrair_pdf
from Fix.core import safe_click_no_scroll
from PEC.anexos.core import anex_carta, salvar_conteudo_clipboard
from PEC.carta_formatacao import formatar_dados_ecarta
from PEC.carta_utils import _obter_numero_processo
from PEC.carta_ecarta_api import coletar_tabela_ecarta_api  # API-based (substitui DOM)

logger = logging.getLogger(__name__)

# ════════════════════════════════════════
# 1. carta_ecarta.py — e-carta, juntada, navegacao
# ════════════════════════════════════════


def _texto_e_correio(texto):
    if not texto:
        return False
    upper = texto.upper()
    # Indicadores primários de eCarta/Correio
    if 'VIA ECARTA REG' in upper or 'VIA ECARTA AR' in upper or 'VIA ECARTA' in upper or 'E-CARTA' in upper or 'ECARTA' in upper:
        return True

    # Indicador alternativo: padrão de código de rastreamento dos Correios (ex: XX999999999BR)
    try:
        if re.search(r"[A-Z]{2}\d{9}BR", texto, re.IGNORECASE):
            return True
    except Exception:
        pass

    # Se a frase de instrução rígida estiver presente junto com qualquer menção a eCarta, considerar correio
    if 'NAO APAGAR NENHUM CARACTERE' in upper and ('ECARTA' in upper or 'E-CARTA' in upper or 'VIA ECARTA' in upper):
        return True

    return False


def _extrair_texto_completo(driver, log):
    texto_completo = None
    try:
        res = extrair_direto(driver, timeout=10, debug=False, formatar=True)
        if res and isinstance(res, dict) and res.get('sucesso'):
            texto_completo = res.get('conteudo') or res.get('conteudo_bruto')
            if texto_completo:
                texto_completo = texto_completo.lower()
    except Exception as e:
        if log:
            logger.error(f"[CARTA][DEBUG] Erro ao extrair documento com extrair_direto: {e}")

    if not texto_completo or len(texto_completo.strip()) < 10:
        try:
            texto_pdf = extrair_pdf(driver, log=False)
            if texto_pdf:
                texto_completo = texto_pdf.lower()
        except Exception as e:
            if log:
                logger.error(f"[CARTA][DEBUG] Erro ao extrair documento com extrair_pdf: {e}")

    return texto_completo


def _extrair_texto_via_api(driver, item, log) -> Optional[str]:
    """Leitura DIRETA do documento pela API — sem abrir o viewer e sem o
    export "Texto Extraído" (OCR).

    Usa `Fix.variaveis.obter_texto_documento` (LEGADO.md ~17883), que sempre
    existiu e lê o conteúdo textual/HTML do documento sem tocar na interface.
    """
    try:
        item_id = ''
        if hasattr(item, 'get_attribute'):
            item_id = item.get_attribute('id') or ''
        id_doc = re.sub(r'^doc_', '', item_id).strip()
        if not id_doc.isdigit():
            return None

        from Fix.core import extrair_id_processo
        from Fix.variaveis import cliente_para, obter_texto_documento

        id_proc = extrair_id_processo(driver)
        if not id_proc:
            return None

        texto = obter_texto_documento(cliente_para(driver), id_proc, id_doc)
        if texto and len(texto.strip()) >= 10:
            if log:
                logger.info(f"[CARTA][API] Documento lido direto da API ({len(texto)} chars, doc={id_doc})")
            return texto.lower()
    except Exception as e:
        if log:
            logger.warning(f"[CARTA][API] Falha na leitura direta do documento: {e}")
    return None


def _processar_item(driver, item, contexto, log):
    try:
        link = _sub_elemento(item, 'a.tl-documento:not([target="_blank"])')
        if not link:
            return None
        link_text = ((getattr(link, 'text_content', None) and link.text_content()) or getattr(link, 'text', '') or '').strip()

        # Filtrar apenas documentos do tipo "Intimação("
        if not link_text.startswith('Intimação('):
            return None

        aria = getattr(link, 'get_attribute', lambda a: '')('aria-label') or ''

        # log link info before opening
        try:
            if log:
                item_id = getattr(item, 'get_attribute', lambda a: '')('id') if hasattr(item, 'get_attribute') else ''
                logger.info(f"[CARTA][DEBUG] link_text_before_click='{link_text[:120]}' | aria='{aria[:120]}' | item_id_attr='{item_id}'")
        except Exception:
            pass

        # Leitura DIRETA pela API (obter_texto_documento — LEGADO.md ~17883):
        # evita abrir o documento e evita o export "Texto Extraído" (OCR).
        texto_completo = _extrair_texto_via_api(driver, item, log)

        if not texto_completo or not _texto_e_correio(texto_completo):
            # Fallback UI (extrair_direto / extrair_pdf) só quando a leitura
            # direta não bastou para provar que a intimação é de correio.
            safe_click_no_scroll(driver, link)
            espera.assentar(driver, 2.0, 'carregamento documento intimacao')
            texto_completo = _extrair_texto_completo(driver, log)

        if not texto_completo or len(texto_completo.strip()) < 10:
            return None

        # small excerpt for debug (safe length)
        if log:
            excerpt = (texto_completo[:200] + '...') if len(texto_completo) > 200 else texto_completo
            logger.info(f"[CARTA][DEBUG] documento extraído (excerpt): {excerpt[:400]}")

        # Data da intimação: mesma fonte de texto que alimenta _texto_e_correio()
        # (nao um seletor DOM separado) -- extrai do rodape padrao do documento,
        # ex: "Sao Paulo/SP, 07 de julho de 2026." Usada como referencia pra
        # correlacao no eCarta em vez do ID do documento: um documento especifico
        # pode nao ter side no eCarta (ex: destinatario sem endereco -> "Expediente
        # enviado por outro meio", eCarta nunca gera carta pra ele), mas a DATA do
        # lote de intimacoes continua valida pra achar as OUTRAS cartas do mesmo
        # dia que foram enviadas normalmente.
        data_intimacao = ''
        try:
            m_data = re.search(
                r'(\d{1,2})\s+de\s+(janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|'
                r'setembro|outubro|novembro|dezembro)\s+de\s+(\d{4})',
                texto_completo, re.IGNORECASE,
            )
            if m_data:
                data_intimacao = m_data.group(0)
                if log:
                    logger.info(f"[CARTA][DEBUG] data_intimacao extraida do texto: '{data_intimacao}'")
        except Exception:
            pass

        texto_upper = texto_completo.upper()
        correio_detectado = _texto_e_correio(texto_upper)
        tem_desconsideracao = False

        if correio_detectado:
            tem_desconsideracao = bool(re.search(r'desconsider[aã][çc][ãa]o', texto_completo, re.IGNORECASE))

        if not correio_detectado:
            if log:
                tem_ecarta = 'ecarta' in texto_completo or 'e-carta' in texto_completo
                tem_via = 'via ecarta' in texto_completo
                tem_rastreio = bool(re.search(r'[a-z]{2}\d{9}br', texto_completo))
                logger.info(
                    f"[CARTA][DEBUG] correio_detectado=False | len_texto={len(texto_completo)} | "
                    f"contem_ecarta={tem_ecarta} | contem_via_ecarta={tem_via} | tem_rastreio={tem_rastreio}"
                )
                # Amostra do meio do texto (onde costuma estar o conteudo postal)
                meio = len(texto_completo) // 2
                amostra = texto_completo[max(0, meio - 100):meio + 100]
                logger.info(f"[CARTA][DEBUG] amostra_meio_texto: {amostra[:300]}")
            return None

        # Extract ID using legacy order: link_text -> aria -> item attribute
        link_text = link.text.strip()
        id_curto = None
        id_source = None

        id_match = re.search(r'-\s*([a-f0-9]+)\s*$', link_text)
        if id_match:
            id_curto = id_match.group(1)
            id_source = 'link_text'
        else:
            id_match = re.search(r'Id: ([a-f0-9]+)', aria)
            if id_match:
                id_curto = id_match.group(1)
                id_source = 'aria'
            else:
                id_curto = item.get_attribute('id')
                id_source = 'item_attr'

        if log:
            logger.info(f"[CARTA][DEBUG] extracted_id={id_curto} (source={id_source})")

        return id_curto, tem_desconsideracao, data_intimacao
    except Exception as e:
        # Se o driver estiver morto, lançar erro para parar o loop superior (evita flood de logs)
        from Fix.utils import verificar_driver_ativo
        if not verificar_driver_ativo(driver):
            if log:
                logger.error(f"[CARTA] Driver desconectado detectado em _processar_item. Interrompendo loop.")
            raise e

        if log:
            logger.error(f"[CARTA] Erro ao processar intimação ({contexto}): {e}")
        return None


def coletar_intimacoes(driver, limite_intimacoes=None, log=True):
    # Legacy behaviour: garantir que dadosatuais.json está atualizado para o processo atual
    try:
        # Chamar explicitamente a implementação atual em Fix.extracao (comportamento legado)
        from Fix.extracao import extrair_dados_processo
        res = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
        if log:
            logger.info('[CARTA] extrair_dados_processo (Fix.extracao) executado; retorno_type=%s', type(res))
        # Verificar que dadosatuais.json foi atualizado e logar o número extraído
        try:
            from pathlib import Path
            import json as _json
            p = Path('dadosatuais.json')
            if p.exists():
                j = _json.loads(p.read_text(encoding='utf-8'))
                if log:
                    logger.info(f"[CARTA] dadosatuais.json.numero={j.get('numero')}")
        except Exception as _f:
            if log:
                logger.error(f"[CARTA] Falha ao ler dadosatuais.json pós-extracao: {_f}")
    except Exception as e:
        if log:
            logger.error(f'[CARTA] Fix.extracao não disponível ou falhou: {e}')
        # continuar sem bloquear o fluxo
        pass

    intimation_ids = []
    intimacoes_info = []
    data_referencia = ''
    limite = limite_intimacoes if limite_intimacoes is not None else float('inf')
    max_busca = 3  # limita a busca por correio a 3 documentos de intimação
    count_intimacoes = 0
    tentativas_busca = 0
    primeiro_ja_processado = False
    intimacao_encontrada = False

    itens = espera.elementos(driver, 'li.tl-item-container', teto=2)
    if itens:
        primeiro_item = itens[0]
        try:
            link_primeiro = _sub_elemento(primeiro_item, 'a.tl-documento:not([target="_blank"])')
            if link_primeiro:
                texto_link = ((getattr(link_primeiro, 'text_content', None) and link_primeiro.text_content()) or getattr(link_primeiro, 'text', '') or '').strip()
                if texto_link.startswith('Intimação('):
                    primeiro_ja_processado = True
                    tentativas_busca += 1
                    resultado = _processar_item(driver, primeiro_item, 'primeiro item', log)
                    if resultado:
                        id_curto, tem_desconsideracao, data_intimacao = resultado
                        intimation_ids.append(id_curto)
                        intimacoes_info.append({
                            'id': id_curto,
                            'tem_desconsideracao': tem_desconsideracao,
                            'data_intimacao': data_intimacao,
                        })
                        if data_intimacao and not data_referencia:
                            data_referencia = data_intimacao
                        intimacao_encontrada = True
        except Exception:
            pass

    if not intimacao_encontrada:
        for idx, item in enumerate(itens):
            if count_intimacoes >= limite:
                break
            if tentativas_busca >= max_busca:
                if log:
                    logger.warning(
                        f'[CARTA] Busca por correio limitada a {max_busca} '
                        'documentos de intimação — encerrando a procura.'
                    )
                break
            if idx == 0 and primeiro_ja_processado:
                continue
            # Só conta como tentativa um documento do tipo "Intimação("
            link_item = _sub_elemento(item, 'a.tl-documento:not([target="_blank"])')
            if not link_item:
                continue
            texto_link_item = ((getattr(link_item, 'text_content', None) and link_item.text_content()) or getattr(link_item, 'text', '') or '').strip()
            if not texto_link_item.startswith('Intimação('):
                continue

            tentativas_busca += 1
            resultado = _processar_item(driver, item, f'item {idx + 1}', log)
            if resultado:
                id_curto, tem_desconsideracao, data_intimacao = resultado
                intimation_ids.append(id_curto)
                intimacoes_info.append({
                    'id': id_curto,
                    'tem_desconsideracao': tem_desconsideracao,
                    'data_intimacao': data_intimacao,
                })
                if data_intimacao and not data_referencia:
                    data_referencia = data_intimacao
                count_intimacoes += 1
                intimacao_encontrada = True
                break

    return intimation_ids, intimacoes_info, data_referencia


def coletar_tabela_ecarta(driver, process_number, intimation_ids, log=True):
    # Se não houver intimações, nada a fazer
    if not intimation_ids:
        return []

    # Garantir que usamos o jNúmero (número do processo) atual do PJe — obter antes de abrir o eCarta
    try:
        from PEC.carta_utils import _obter_numero_processo as _obter_numero_processo
        numero_atual = _obter_numero_processo(driver, log)
        if numero_atual:
            if process_number != numero_atual:
                if log:
                    logger.info(f"[CARTA] process_number sobrescrito: {process_number} -> {numero_atual}")
            process_number = numero_atual
    except Exception:
        # falha ao re-obter não é fatal aqui — usaremos o valor recebido se existir
        pass

    if not process_number:
        if log:
            logger.error('[CARTA][ERRO] Número do processo não disponível para abrir eCarta')
        return []

    t_start = time.time()
    if log:
        logger.info(f"[CARTA] coletar_tabela_ecarta START — process={process_number} | intimation_ids={intimation_ids}")

    original_window = getattr(driver, 'current_window_handle', None)

    # Legacy behaviour: always use the `process_number` (CNJ) obtained from dadosatuais.json
    ecarta_url = f"https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo={process_number}"
    abrir_url_nova_aba(driver, ecarta_url)

    espera.ate_url(driver, "ecarta", teto=20)

    if "ecarta" not in (driver.current_url or '').lower():
        if log:
            logger.error("[CARTA][ERRO] Não estamos na aba correta do eCarta!")
            logger.error(f"[CARTA][ERRO] URL atual: {driver.current_url}")
        return []

    if log:
        logger.info(f"[CARTA] Página eCarta carregada: {driver.current_url}")
    try:
        user_field = espera.elemento(driver, "#input_user", teto=8)
        if user_field:
            _executar_js(driver, "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", user_field, "s164283")
            pwd_field = espera.elemento(driver, "#input_password", teto=5)
            if pwd_field:
                _executar_js(driver, "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", pwd_field, "SpFintra861!")
            btn_login = espera.elemento(driver, "input.btn", teto=5)
            if btn_login:
                safe_click_no_scroll(driver, btn_login)
            espera.ate_js(driver, "document.readyState === 'complete'", teto=5)

            driver.get(ecarta_url)
            espera.ate_aparecer(driver, "#main\\:tabDoc_data tr, table[id*='tabDoc'] tr, .ui-datatable tbody tr", teto=10)
    except Exception:
        pass

    table_data = []
    try:
        correlacao_encontrada = False
        pagina_atual = 1
        max_tentativas_paginas = 10

        while not correlacao_encontrada and pagina_atual <= max_tentativas_paginas:
            js_script = """
            function criarUrlDocumento(documentoId) {
                var baseUrl = window.location.origin;
                var currentPath = window.location.pathname;
                var contexto = '';
                if (currentPath.includes('/pjekz/')) {
                    contexto = '/pjekz';
                } else if (currentPath.includes('/pje/')) {
                    contexto = '/pje';
                } else {
                    contexto = '/pjekz';
                }
                if (contexto === '/pjekz') {
                    return baseUrl + '/pjekz/processo/documento/' + documentoId + '/conteudo';
                } else {
                    return baseUrl + '/pje/Processo/ConsultaDocumento/Documento.seam?doc=' + documentoId;
                }
            }

            function extrairDadosTabela() {
                var seletores = [
                    '#main\\\\:tabDoc_data tr',
                    '#main\\\\:tabDoc tbody tr',
                    'table[id*="tabDoc"] tr',
                    '.ui-datatable tbody tr',
                    'tbody tr'
                ];

                var rows = null;
                var seletorUsado = '';

                for (var i = 0; i < seletores.length; i++) {
                    var tempRows = Array.from(document.querySelectorAll(seletores[i]));
                    if (tempRows.length > 0) {
                        rows = tempRows;
                        seletorUsado = seletores[i];
                        break;
                    }
                }

                if (!rows || rows.length === 0) {
                    return null;
                }

                var data = rows.map(function(tr, index) {
                    var tds = tr.querySelectorAll('td');

                    if (tds.length < 4) {
                        return null;
                    }

                    var dataEnvio = tds[0] ? tds[0].innerText.trim() : '';
                    var dataEntrega = tds[1] ? tds[1].innerText.trim() : '';
                    var idTd = tds[3];
                    var idPje = idTd ? idTd.innerText.trim() : '';
                    var objetoTd = tds[4];
                    var objeto = objetoTd ? objetoTd.innerText.trim() : '';

                    if (!idPje || idPje.length < 5) {
                        for (var k = 0; k < tds.length; k++) {
                            var conteudo = tds[k].innerText.trim();
                            if (/^[a-f0-9]{6,}$/.test(conteudo)) {
                                idPje = conteudo;
                                break;
                            }
                        }
                    }

                    var idPjeLink = null;
                    if (idPje && /^\\d{10,}$/.test(idPje)) {
                        idPjeLink = criarUrlDocumento(idPje);
                    }

                    var objetoLink = null;
                    var spanElement = objetoTd ? objetoTd.querySelector('span[id*=":rastreamento"]') : null;
                    if (spanElement) {
                        var codigoRastreamento = spanElement.innerText.trim();
                        if (codigoRastreamento && codigoRastreamento.length > 5) {
                            objeto = codigoRastreamento;
                            var linkElement = spanElement.closest('a');
                            if (linkElement && linkElement.href) {
                                if (linkElement.href.startsWith('/')) {
                                    objetoLink = 'https://aplicacoes1.trt2.jus.br' + linkElement.href;
                                } else {
                                    objetoLink = linkElement.href;
                                }
                            } else {
                                if (/^[A-Z]{2}\\d{9}BR$/.test(codigoRastreamento)) {
                                    objetoLink = 'https://aplicacoes1.trt2.jus.br/eCarta-web/consultarObjeto.xhtml?codigo=' + codigoRastreamento;
                                }
                            }
                        }
                    }

                    if (!objetoLink && objetoTd) {
                        var linkInCell = objetoTd.querySelector('a[href]');
                        if (linkInCell && linkInCell.href) {
                            if (linkInCell.href.startsWith('/')) {
                                objetoLink = 'https://aplicacoes1.trt2.jus.br' + linkInCell.href;
                            } else {
                                objetoLink = linkInCell.href;
                            }
                        }
                    }

                    var rowData = {
                        dataEnvio: dataEnvio,
                        dataEntrega: dataEntrega,
                        idPje: idPje,
                        idPjeLink: idPjeLink,
                        objeto: objeto,
                        objetoLink: objetoLink,
                        status: tds[5] ? tds[5].innerText.trim() : '',
                        destinatario: tds[6] ? tds[6].innerText.trim() : '',
                        orgaoJulgador: tds[7] ? tds[7].innerText.trim() : ''
                    };

                    return rowData;
                }).filter(function(item) { return item !== null; });

                return data;
            }

            var resultado = extrairDadosTabela();
            return resultado;
            """

            page_t0 = espera.assentar(driver, 0, '')
            ecarta_data = _executar_js(driver, js_script, pagina_atual)

            if not ecarta_data:
                if log:
                    logger.info(f"[CARTA] Nenhum dado encontrado na tabela eCarta - página {pagina_atual} (page_time={page_dur:.2f}s)")
            else:
                if log:
                    sample_ids = [it.get('idPje','') for it in (ecarta_data[:12] if isinstance(ecarta_data, list) else [])]
                    logger.info(f"[CARTA] Dados extraídos: {len(ecarta_data)} registros na página {pagina_atual} (page_time={page_dur:.2f}s) | ids_sample={sample_ids}")

                # Verificar correlação com IDs da intimação (legacy strict matching)
                datas_correlacionadas = []
                for item in ecarta_data:
                    id_pje = item.get('idPje', '')

                    if not id_pje:
                        continue

                    for intimation_id in intimation_ids:
                        if not intimation_id:
                            continue

                        if intimation_id in id_pje or id_pje in intimation_id:
                            data_envio = item.get('dataEnvio', '')
                            if data_envio and data_envio not in datas_correlacionadas:
                                datas_correlacionadas.append(data_envio)
                            if log:
                                logger.info(f"[CARTA]  CORRELAÇÃO ENCONTRADA! ID_PJE={id_pje} corresponde à intimação={intimation_id} (data {data_envio})")
                            break

                if datas_correlacionadas:
                    if log:
                        logger.info(f"[CARTA] Coletando TODAS as intimações das datas: {datas_correlacionadas}")

                    for item in ecarta_data:
                        item_data_envio = item.get('dataEnvio', '')

                        if item_data_envio not in datas_correlacionadas:
                            continue

                        status_item = item.get('status', '')
                        eh_devolvido = bool(re.search(r'devolvid[oa]', status_item, re.IGNORECASE))
                        rastreamento_final = item.get('objetoLink', '') or item.get('objeto', '')
                        table_data.append({
                            "ID_PJE": item.get('idPje', ''),
                            "ID_PJE_LINK": item.get('idPjeLink', ''),
                            "RASTREAMENTO": rastreamento_final,
                            "DESTINATARIO": item.get('destinatario', ''),
                            "DATA_ENVIO": item_data_envio,
                            "DATA_ENTREGA": '' if eh_devolvido else item.get('dataEntrega', ''),
                            "STATUS": status_item,
                        })

                    correlacao_encontrada = True
                    break

            if not correlacao_encontrada:
                # Tentar navegar entre páginas de forma mais robusta (comportamento legado):
                # - Preferir 'last' se estiver habilitado
                # - Caso contrário, avançar via 'prev' repetidamente
                # - Fallback: clicar no último link de página visível
                try:
                    # tentativa 1: clicar 'last' (comportamento do legado)
                    try:
                        last_page_btn = espera.elemento(driver, 'a.ui-paginator-last.ui-state-default.ui-corner-all', teto=2)
                        if last_page_btn:
                            safe_click_no_scroll(driver, last_page_btn)
                            espera.ate_aparecer(driver, '#main\\:tabDoc_data tr, table[id*="tabDoc"] tr', teto=5)
                            pagina_atual = pagina_atual + 1
                            continue
                    except Exception:
                        pass

                    # tentativa 2: clicar 'prev' (comportamento do legado: navegamos do último para páginas anteriores)
                    prev_btn = espera.elemento(driver, 'a.ui-paginator-prev', teto=2)
                    if prev_btn:
                        prev_cls = (getattr(prev_btn, 'get_attribute', lambda a: '')('class') or '')
                        if 'ui-state-disabled' in prev_cls:
                            # não há mais páginas disponíveis para retroceder
                            if log:
                                logger.info('[CARTA] Paginator: botão "prev" está desabilitado — fim das páginas')
                            break

                        try:
                            _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", prev_btn)
                            safe_click_no_scroll(driver, prev_btn)
                            espera.ate_aparecer(driver, '#main\\:tabDoc_data tr, table[id*="tabDoc"] tr', teto=5)
                            pagina_atual += 1
                            continue
                        except Exception as e_prev:
                            if log:
                                logger.error(f"[CARTA] Falha ao clicar 'prev' no paginator: {e_prev}")

                    # tentativa 3: fallback para clicar no último link de página disponível (legacy tenta navegar por páginas também)
                    page_links = espera.elementos(driver, 'a.ui-paginator-page', teto=2)
                    if page_links:
                        last_page_link = page_links[-1]
                        link_cls = (getattr(last_page_link, 'get_attribute', lambda a: '')('class') or '')
                        if 'ui-state-disabled' not in link_cls:
                            try:
                                _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", last_page_link)
                                safe_click_no_scroll(driver, last_page_link)
                                espera.ate_aparecer(driver, '#main\\:tabDoc_data tr, table[id*="tabDoc"] tr', teto=5)
                                pagina_atual += 1
                                continue
                            except Exception as e_link:
                                if log:
                                    logger.error(f"[CARTA] Falha ao clicar link de página (fallback): {e_link}")

                    # Se todas as tentativas falharem, registrar e abortar paginação
                    if log:
                        logger.error('[CARTA]  Não foi possível navegar entre páginas do eCarta (paginator bloqueado ou sobreposto)')
                    break
                except Exception as e:
                    if log:
                        logger.error(f"[CARTA]  Erro ao tentar navegar pelas páginas do eCarta: {e}")
                    break

        if not table_data:
            driver.close()
            driver.switch_to.window(original_window)
            return []

    except Exception as e:
        from Fix.utils import verificar_driver_ativo
        if not verificar_driver_ativo(driver):
            raise e

        if log:
            logger.error(f"[CARTA] Erro ao extrair dados da tabela eCarta: {e}")

        try:
            driver.close()
            driver.switch_to.window(original_window)
            if log:
                logger.error("[CARTA] Aba eCarta fechada após erro, voltando para processo")
        except Exception:
            pass

        return []

    try:
        driver.close()
        for _ in range(15):
            if original_window in getattr(driver, 'window_handles', []):
                break
            espera.pausa(driver, 0.2)
        if original_window:
            driver.switch_to.window(original_window)
        espera.ate_js(driver, "document.readyState === 'complete'", teto=3)
    except Exception as e:
        if log:
            logger.error(f"[CARTA] Erro ao fechar aba eCarta: {e}")

    return table_data


# ════════════════════════════════════════
# 2. carta.py — coleta e dispatch
# ════════════════════════════════════════


def carta(driver: Any, log: bool = True, limite_intimacoes: Optional[int] = None) -> Any:
    """Orquestra o fluxo de carta eCarta no PJe."""
    process_number = _obter_numero_processo(driver, log)

    t_ci = time.time()
    intimation_ids, intimacoes_info, data_referencia = coletar_intimacoes(
        driver, limite_intimacoes=limite_intimacoes, log=log
    )
    dur_ci = time.time() - t_ci
    if log:
        logger.info(
            f"[CARTA] coletar_intimacoes retornou {len(intimation_ids)} ids (took {dur_ci:.2f}s): "
            f"{intimation_ids} | data_referencia={data_referencia!r}"
        )

    if not intimation_ids:
        if log:
            logger.error("[CARTA] Nenhuma intimacao de correio encontrada.")
        return ""

    if not process_number:
        process_number = _obter_numero_processo(driver, log)
        if not process_number:
            if log:
                logger.error(
                    "[CARTA][ERRO] Nao foi possivel obter o numero do processo via dadosatuais.json."
                )
            return ""

    t_ct = time.time()
    table_data = coletar_tabela_ecarta_api(
        driver, process_number, intimation_ids, log=log, data_referencia=data_referencia
    )
    dur_ct = time.time() - t_ct
    if log:
        logger.info(f"[CARTA] coletar_tabela_ecarta_api retornou {len(table_data) if table_data else 0} registros (took {dur_ct:.2f}s)")

    if not table_data:
        if log:
            logger.error("[CARTA] Nenhuma correlacao encontrada no eCarta.")
        return ""

    conteudo_final, html_para_juntada, _prazo_texto = formatar_dados_ecarta(
        table_data, intimacoes_info, log=log
    )
    if not conteudo_final:
        if log:
            logger.error("[CARTA] Falha ao formatar dados do eCarta.")
        return ""

    try:
        sucesso = salvar_conteudo_clipboard(
            conteudo=conteudo_final,
            numero_processo=process_number,
            tipo_conteudo="ecarta",
            debug=log,
        )
        if log and not sucesso:
            logger.error("[CARTA] Falha ao salvar via funcao centralizada do clipboard.")
    except Exception as e:
        if log:
            logger.error(f"[CARTA] Erro ao salvar clipboard: {e}")

    try:
        resultado_juntada = anex_carta(
            driver,
            numero_processo=process_number,
            debug=log,
            ecarta_html=html_para_juntada,
        )
        if log and not resultado_juntada:
            logger.error("[CARTA] Juntada automatica falhou ou foi pulada.")
            return False

    except Exception as e:
        if log:
            logger.error(f"[CARTA] Erro na juntada automatica: {e}")
        return False

    return True
