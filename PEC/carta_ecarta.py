import logging
logger = logging.getLogger(__name__)

import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from Fix.extracao import extrair_direto, extrair_pdf


def _texto_e_correio(texto):
    if not texto:
        return False
    upper = texto.upper()
    if 'NAO APAGAR NENHUM CARACTERE' not in upper:
        return False
    return 'VIA ECARTA REG' in upper or 'VIA ECARTA AR' in upper


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


def _processar_item(driver, item, contexto, log):
    try:
        link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
        link_text = link.text.strip()

        # Filtrar apenas documentos do tipo "Intimação("
        if not link_text.startswith('Intimação('):
            return None

        aria = link.get_attribute('aria-label') or ''

        # log link info before opening
        try:
            if log:
                logger.info(f"[CARTA][DEBUG] link_text_before_click='{link.text.strip()[:120]}' | aria='{aria[:120]}' | item_id_attr='{item.get_attribute('id')}'")
        except Exception:
            pass

        link.click()
        time.sleep(2)

        texto_completo = _extrair_texto_completo(driver, log)
        if not texto_completo or len(texto_completo.strip()) < 10:
            return None

        # small excerpt for debug (safe length)
        if log:
            excerpt = (texto_completo[:200] + '...') if len(texto_completo) > 200 else texto_completo
            logger.info(f"[CARTA][DEBUG] documento extraído (excerpt): {excerpt[:400]}")

        texto_upper = texto_completo.upper()
        correio_detectado = _texto_e_correio(texto_upper)
        tem_desconsideracao = False

        if correio_detectado:
            tem_desconsideracao = bool(re.search(r'desconsider[aã][çc][ãa]o', texto_completo, re.IGNORECASE))

        if not correio_detectado:
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

        return id_curto, tem_desconsideracao
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
        # Chamar explicitamente a implementação atual em Fix.extracao_processo (comportamento legado)
        from Fix.extracao_processo import extrair_dados_processo
        res = extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
        if log:
            logger.info('[CARTA] extrair_dados_processo (Fix.extracao_processo) executado; retorno_type=%s', type(res))
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
            logger.error(f'[CARTA] Fix.extracao_processo não disponível ou falhou: {e}')
        # continuar sem bloquear o fluxo
        pass

    intimation_ids = []
    intimacoes_info = []
    limite = limite_intimacoes if limite_intimacoes is not None else float('inf')
    count_intimacoes = 0
    intimacao_encontrada = False

    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    if itens:
        primeiro_item = itens[0]
        try:
            link_primeiro = primeiro_item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            texto_link = link_primeiro.text.strip()
            if texto_link.startswith('Intimação('):
                resultado = _processar_item(driver, primeiro_item, 'primeiro item', log)
                if resultado:
                    id_curto, tem_desconsideracao = resultado
                    intimation_ids.append(id_curto)
                    intimacoes_info.append({
                        'id': id_curto,
                        'tem_desconsideracao': tem_desconsideracao,
                    })
                    intimacao_encontrada = True
        except Exception:
            pass

    if not intimacao_encontrada:
        for idx, item in enumerate(itens):
            if count_intimacoes >= limite:
                break

            resultado = _processar_item(driver, item, f'item {idx + 1}', log)
            if resultado:
                id_curto, tem_desconsideracao = resultado
                intimation_ids.append(id_curto)
                intimacoes_info.append({
                    'id': id_curto,
                    'tem_desconsideracao': tem_desconsideracao,
                })
                count_intimacoes += 1
                intimacao_encontrada = True
                break

    return intimation_ids, intimacoes_info


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

    original_window = driver.current_window_handle
    original_window_count = len(driver.window_handles)

    # Legacy behaviour: always use the `process_number` (CNJ) obtained from dadosatuais.json
    ecarta_url = f"https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo={process_number}"
    driver.execute_script(f"window.open('{ecarta_url}', '_blank');")

    max_tentativas = 10
    for _ in range(max_tentativas):
        time.sleep(0.5)
        current_window_count = len(driver.window_handles)
        if current_window_count > original_window_count:
            break
    else:
        time.sleep(2)

    all_windows = driver.window_handles
    if len(all_windows) > 1:
        nova_aba = all_windows[-1]
        driver.switch_to.window(nova_aba)
    else:
        if log:
            logger.error("[CARTA][ERRO] Nova aba não foi detectada")

    max_aguardar_carregamento = 20
    for tentativa in range(max_aguardar_carregamento):
        current_url = driver.current_url
        if "ecarta" in current_url.lower() and current_url != "about:blank":
            break
        time.sleep(1)
        if tentativa == max_aguardar_carregamento - 1:
            pass

    if "ecarta" not in driver.current_url.lower():
        if log:
            logger.error("[CARTA][ERRO] Não estamos na aba correta do eCarta!")
            logger.error(f"[CARTA][ERRO] URL atual: {driver.current_url}")
        return []

    time.sleep(3)
    if log:
        logger.info(f"[CARTA] Página eCarta carregada: {driver.current_url} (waiting 3s)")
    try:
        username_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#input_user"))
        )
        username_field.send_keys("s164283")
        driver.find_element(By.CSS_SELECTOR, "#input_password").send_keys("SpFintra861!")
        driver.find_element(By.CSS_SELECTOR, "input.btn").click()
        time.sleep(3)

        driver.get(ecarta_url)
        time.sleep(3)
    except TimeoutException:
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
                    if (idPje && /^\d{10,}$/.test(idPje)) {
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
                                if (/^[A-Z]{2}\d{9}BR$/.test(codigoRastreamento)) {
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

            page_t0 = time.time()
            ecarta_data = driver.execute_script(js_script, pagina_atual)
            page_dur = time.time() - page_t0

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

                        rastreamento_final = item.get('objetoLink', '') or item.get('objeto', '')
                        table_data.append({
                            "ID_PJE": item.get('idPje', ''),
                            "RASTREAMENTO": rastreamento_final,
                            "DESTINATARIO": item.get('destinatario', ''),
                            "DATA_ENVIO": item_data_envio,
                            "DATA_ENTREGA": item.get('dataEntrega', ''),
                            "STATUS": item.get('status', ''),
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
                        last_page_btn = driver.find_element(By.CSS_SELECTOR, 'a.ui-paginator-last.ui-state-default.ui-corner-all')
                        last_page_btn.click()
                        time.sleep(2)
                        pagina_atual = pagina_atual + 1
                        continue
                    except Exception:
                        # se falhar, prosseguir para tentativas alternativas (prev / page links)
                        pass

                    # tentativa 2: clicar 'prev' (comportamento do legado: navegamos do último para páginas anteriores)
                    prev_btn = driver.find_element(By.CSS_SELECTOR, 'a.ui-paginator-prev')
                    prev_cls = (prev_btn.get_attribute('class') or '')
                    if 'ui-state-disabled' in prev_cls:
                        # não há mais páginas disponíveis para retroceder
                        if log:
                            logger.info('[CARTA] Paginator: botão "prev" está desabilitado — fim das páginas')
                        break

                    try:
                        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', prev_btn)
                        driver.execute_script('arguments[0].click();', prev_btn)
                        time.sleep(2)
                        pagina_atual += 1
                        continue
                    except Exception as e_prev:
                        if log:
                            logger.error(f"[CARTA] Falha ao clicar 'prev' no paginator: {e_prev}")

                    # tentativa 3: fallback para clicar no último link de página disponível (legacy tenta navegar por páginas também)
                    page_links = driver.find_elements(By.CSS_SELECTOR, 'a.ui-paginator-page')
                    if page_links:
                        last_page_link = page_links[-1]
                        link_cls = (last_page_link.get_attribute('class') or '')
                        if 'ui-state-disabled' not in link_cls:
                            try:
                                driver.execute_script('arguments[0].scrollIntoView({block:"center"});', last_page_link)
                                driver.execute_script('arguments[0].click();', last_page_link)
                                time.sleep(2)
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
        time.sleep(0.5)
        driver.switch_to.window(original_window)
        time.sleep(0.5)
    except Exception as e:
        if log:
            logger.error(f"[CARTA] Erro ao fechar aba eCarta: {e}")

    return table_data

