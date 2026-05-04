"""
Helpers para checagens especificas de regras em Peticoes Iniciais
Modulo para validacoes customizadas antes da execucao de acoes
"""

from Fix.log import logger

import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from Fix.selenium_base.wait_operations import esperar_elemento

# Import para API calls
from ..api.client import PjeApiClient, session_from_driver
from ..core.extracao import extrair_direto, extrair_documento, criar_gigs, extrair_dados_processo
from Fix.variaveis import obter_chave_ultimo_despacho_decisao_sentenca
from ..runtime_pet import extrair_texto_peticao_via_api


def _buscar_documento_relevante_timeline(driver: WebDriver) -> Tuple[Optional[Any], Optional[Any], str]:
    """
    Busca documento relevante (sentenca/decisao/despacho) na timeline via DOM.

    Baseado na implementacao do p2b_fluxo_documentos.py.
    Busca APENAS no tipo real do documento (primeiro <span> dentro do link).

    Returns:
        Tupla (doc_encontrado, doc_link, tipo_documento)
    """
    from selenium.webdriver.common.by import By

    itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')

    # Busca do mais recente para o mais antigo
    for item in itens:
        try:
            link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')

            # Extrair apenas o primeiro <span> (tipo real do documento)
            primeiro_span = link.find_element(By.CSS_SELECTOR, 'span:not(.sr-only)')
            tipo_real = primeiro_span.text.lower().strip() if primeiro_span else ''

            # Verificar se o tipo REAL e um dos procurados
            if tipo_real and re.search(r'^(despacho|decisao|sentenca)', tipo_real):
                return item, link, tipo_real.title()  # Retorna capitalizado

        except Exception:
            continue

    return None, None, ""
import re
from typing import Optional, Tuple, Any


def _normalizar_delete_processes(delete_processes: dict) -> dict:
    normalizado = {}
    for numero_processo, entradas in delete_processes.items():
        ids_documento = []
        if isinstance(entradas, list):
            for entrada in entradas:
                if isinstance(entrada, dict):
                    id_doc = str(entrada.get("id_doc") or entrada.get("id") or "").strip()
                else:
                    id_doc = str(entrada).strip()
                if id_doc and id_doc not in ids_documento:
                    ids_documento.append(id_doc)
        else:
            id_doc = str(entradas).strip()
            if id_doc:
                ids_documento.append(id_doc)
        if ids_documento:
            normalizado[numero_processo] = ids_documento
    return normalizado

def apagar(numero_processo: str, id_documento: str):
    """
    Registra processo no arquivo delete.js para nao ser processado.
    Formato: {numero_processo: [id_doc]}
    """
    try:
        delete_file = Path(__file__).parent / "delete.js"

        # Ler arquivo atual (sempre acumular, nunca sobrescrever)
        delete_processes = {}
        if delete_file.exists():
            try:
                content = delete_file.read_text(encoding='utf-8')
                match = re.search(
                    r'const\s+delete_processes\s*=\s*(\{.*?\})\s*;',
                    content,
                    re.S,
                )
                if match:
                    delete_processes = _normalizar_delete_processes(json.loads(match.group(1)))
            except Exception:
                pass

        novo_id_doc = str(id_documento).strip()
        if not novo_id_doc:
            return

        existente = delete_processes.get(numero_processo)
        if existente is None:
            delete_processes[numero_processo] = [novo_id_doc]
        elif isinstance(existente, list):
            ids = [str(e.get("id_doc") or e).strip() if isinstance(e, dict) else str(e).strip() for e in existente]
            if novo_id_doc not in ids:
                existente.append(novo_id_doc)
        else:
            id_legado = str(existente).strip()
            delete_processes[numero_processo] = [id_legado] if id_legado == novo_id_doc else [
                id_legado,
                novo_id_doc,
            ]

        # Escrever de volta (sempre acumulando)
        with open(delete_file, 'w', encoding='utf-8') as f:
            f.write("// Arquivo para registrar processos que devem ser \"apagados\" (nao processados)\n")
            f.write("// Formato: {numero_processo: [id_doc]}\n\n")
            f.write("const delete_processes = ")
            json.dump(delete_processes, f, indent=2, ensure_ascii=False)
            f.write(";\n\nmodule.exports = delete_processes;\n")

    except Exception as e:
        logger.error("ERRO em apagar: Erro ao registrar processo no delete.js: %s: %s", type(e).__name__, e)

def checar_habilitacao(item, driver: WebDriver) -> bool:
    """
    Checagem completa para a regra de direitos-habilitacao
    Inclui verificacao de advogado + verificacoes de audiencia para ato_ceju

    Args:
        item: Item da peticao com atributos do processo
        driver: WebDriver para acesso ao PJe

    Returns:
        bool: True se deve executar ato_ceju, False caso contrario
    """
    try:
        numero_processo = getattr(item, 'numero_processo', '')
        if not numero_processo:
            return False

        # 0. Extrair dados do processo (dadosatuais.json)
        from ..core.extracao import extrair_dados_processo
        try:
            extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
        except Exception as e:
            logger.warning('[HABILITACAO] Erro ao extrair dados do processo: %s', e)
            return False

        # 1. VERIFICACAO DE ADVOGADO (nao afeta resultado final)
        def _extrair_nome_assinante(texto_pdf):
            """Helper: extrai nome do assinante da primeira pagina"""
            try:
                linhas = texto_pdf.split('\n')
                for linha in reversed(linhas):
                    linha = linha.strip()
                    if 'Documento assinado eletronicamente por' in linha:
                        match = re.search(r'Documento assinado eletronicamente por (.+)', linha)
                        if match:
                            nome = match.group(1).strip()
                            nome = re.sub(r'[.,;:!?]+$', '', nome)
                            return nome
                return None
            except Exception as e:
                logger.warning('[HABILITACAO] Erro ao extrair nome do assinante: %s', e)
                return None

        def _extrair_id_doc_peticao():
            """ID numerico da peticao selecionada na timeline.
            Selecionada = li.tl-item-container com style contendo background-color (azul claro).
            id do li: 'doc_453562049' -> '453562049'.
            """
            try:
                sel = driver.find_element(
                    By.CSS_SELECTOR,
                    'li.tl-item-container[style*="background-color"]'
                )
                li_id = sel.get_attribute('id') or ''
                m = re.match(r'doc_(\d+)', li_id)
                return m.group(1) if m else ''
            except Exception:
                return ''

        def _obter_lista_advogados():
            """Helper: obtem lista de advogados de dadosatuais.json"""
            try:
                dados_path = Path('dadosatuais.json')
                if not dados_path.exists():
                    return []
                with open(dados_path, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                advogados = []
                for autor in dados.get('autor', []):
                    if 'advogado' in autor and 'nome' in autor['advogado']:
                        advogados.append(autor['advogado']['nome'])
                for reu in dados.get('reu', []):
                    if 'advogado' in reu and 'nome' in reu['advogado']:
                        advogados.append(reu['advogado']['nome'])
                return advogados
            except Exception as e:
                logger.warning('[HABILITACAO] Erro ao obter lista de advogados: %s', e)
                return []

        # 1. VERIFICAR AUDIENCIA -> define ato_ceju (nao depende de advogado)
        tem_ata_audiencia = False
        try:
            sess, trt = session_from_driver(driver)
            client = PjeApiClient(sess, trt)
            id_processo = client.id_processo_por_numero(numero_processo)
            if not id_processo:
                id_processo = getattr(item, 'id_processo', numero_processo)
            if id_processo:
                timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
                if timeline:
                    for doc in timeline:
                        titulo = doc.get('titulo', '').lower()
                        if 'ata' in titulo and 'audiencia' in titulo:
                            tem_ata_audiencia = True
                            logger.debug('[HABILITACAO] Processo %s - tem ata de audiencia (ato_ceju=True)', numero_processo)
                            break
        except Exception as e:
            logger.warning('[HABILITACAO] Aviso: Erro ao verificar ata de audiencia via API: %s', e)

        # ato_ceju depende APENAS da audiencia
        executar_ato_ceju = tem_ata_audiencia

        # 2. VERIFICAR ADVOGADO -- SEMPRE, independente de ato_ceju
        id_doc_peticao = _extrair_id_doc_peticao()
        fez_gigs = False
        texto_pdf = extrair_texto_peticao_via_api(driver, item)
        if texto_pdf:
            texto_lower = texto_pdf.lower()
            contem_exclusao = "excluir" in texto_lower or "exclusao" in texto_lower
            nome_assinante = _extrair_nome_assinante(texto_pdf)
            logger.debug('[HABILITACAO] Processo %s - assinante: %s | contem_exclusao: %s', numero_processo, nome_assinante or '(nao identificado)', contem_exclusao)
            adv_diverso = False
            if nome_assinante:
                advogados = _obter_lista_advogados()
                if advogados:
                    assinante_eh_advogado = any(
                        nome_assinante.lower() in adv.lower() or adv.lower() in nome_assinante.lower()
                        for adv in advogados
                    )
                    if not assinante_eh_advogado:
                        adv_diverso = True
                else:
                    logger.debug('[HABILITACAO] Processo %s - lista de advogados vazia/indisponivel', numero_processo)
            else:
                logger.debug('[HABILITACAO] Processo %s - assinante nao identificado no PDF', numero_processo)

            if adv_diverso and contem_exclusao:
                tipo_gigs = "hab adv diverso + exclusao"
            elif adv_diverso:
                tipo_gigs = "hab adv diverso"
            elif contem_exclusao:
                tipo_gigs = "hab pede exclusao"
            else:
                tipo_gigs = None

            if adv_diverso and contem_exclusao:
                logger.debug('[HABILITACAO] Processo %s - Adv diverso + exclusao', numero_processo)
            elif adv_diverso:
                logger.debug('[HABILITACAO] Processo %s - Adv diverso', numero_processo)
            elif contem_exclusao:
                logger.debug('[HABILITACAO] Processo %s - Pede exclusao', numero_processo)
            elif nome_assinante:
                logger.debug('[HABILITACAO] Processo %s - Advogado ok', numero_processo)

            if tipo_gigs:
                try:
                    criar_gigs(driver, "-1", "", tipo_gigs)
                    fez_gigs = True
                    logger.debug('[HABILITACAO] Processo %s - GIGS: %s', numero_processo, tipo_gigs)
                except Exception as e:
                    logger.warning('[HABILITACAO] Erro ao criar GIGS para %s: %s', numero_processo, e)
        else:
            logger.debug('[HABILITACAO] Processo %s - texto PDF nao extraido, verificacao de advogado ignorada', numero_processo)

        # 3. Decisao final
        if executar_ato_ceju:
            # Tem audiencia -> executa ato_ceju, nada mais
            logger.debug('[HABILITACAO] Processo %s - ato_ceju=True, executa ato_ceju, nada mais', numero_processo)
            return True

        # ato_ceju=False: apagar apenas se nao fez GIGS
        if not fez_gigs:
            apagar(numero_processo, id_doc_peticao)
            logger.debug('[HABILITACAO] Processo %s - ato_ceju=False, registrado para apagar', numero_processo)
        else:
            logger.debug('[HABILITACAO] Processo %s - ato_ceju=False + GIGS feito, nao apagar', numero_processo)
        return False

    except Exception as e:
        logger.error("ERRO em checar_habilitacao: %s: %s", type(e).__name__, e)
        return False


def agravo_peticao(item, driver: WebDriver) -> bool:
    """
    Processa Agravo de Peticao: busca documento relevante na timeline via DOM
    e executa ato apropriado baseado no conteudo.

    Fluxo:
    1. Buscar documento relevante (sentenca/decisao/despacho) na timeline
    2. Se sentenca: extrair conteudo e verificar por "defiro" ou "indefiro" + "desconsideracao"
    3. Executar ato correspondente
    """
    logger.info('[AGPET] Iniciando processamento de agravo de peticao: %s', item.numero_processo)

    # 1. Buscar documento relevante na timeline via DOM
    doc_encontrado, doc_link, tipo_documento = _buscar_documento_relevante_timeline(driver)

    if not doc_encontrado or not doc_link:
        logger.warning('[AGPET] Nenhum documento relevante encontrado na timeline')
        return False

    logger.info('[AGPET] Documento relevante encontrado: %s', tipo_documento)

    # 2. Se for sentenca, extrair conteudo para analise
    if tipo_documento.lower() == 'sentenca':
        # Clicar no documento e aguardar carregamento
        doc_link.click()
        try:
            from ..core.utils.observer import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2)
        except Exception:
            import time
            time.sleep(2)

        # Extrair conteudo usando extrair_direto
        texto = None
        try:
            resultado_direto = extrair_direto(driver, timeout=10, debug=False, formatar=True)

            if resultado_direto and resultado_direto.get('sucesso'):
                if resultado_direto.get('conteudo'):
                    texto = resultado_direto['conteudo'].lower()
                elif resultado_direto.get('conteudo_bruto'):
                    texto = resultado_direto['conteudo_bruto'].lower()
        except Exception as e:
            logger.warning('[AGPET] Erro na extracao DIRETA: %s', e)

        # Fallback para extrair_documento se extrair_direto falhar
        if not texto:
            try:
                texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=False)
                if texto_tuple and texto_tuple[0]:
                    texto = texto_tuple[0].lower()
            except Exception as e:
                logger.warning('[AGPET] Erro na extracao DOCUMENTO: %s', e)

        if not texto:
            logger.error("ERRO em agravo_peticao: Nao foi possivel extrair texto da sentenca")
            return False

        # 3. Verificar conteudo da sentenca
        texto_normalizado = texto.lower()

        # Verificar se contem "defiro" ou "indefiro" + "desconsideracao"
        if 'desconsideracao' in texto_normalizado:
            if 'defiro' in texto_normalizado or 'indefiro' in texto_normalizado:
                logger.info('[AGPET] Sentenca contem decisao sobre desconsideracao - executando ato_agpetidpj')
                try:
                    from ..atos.wrappers import ato_agpetidpj
                    ato_agpetidpj(driver)
                    logger.info('[AGPET] ato_agpetidpj executado com sucesso')
                    return True
                except Exception as e:
                    logger.error("ERRO em agravo_peticao: Erro ao executar ato_agpetidpj: %s: %s", type(e).__name__, e)
                    return False
            else:
                logger.info('[AGPET] Sentenca menciona desconsideracao mas sem decisao clara')

        # Demais casos de sentenca
        logger.info('[AGPET] Sentenca sem decisao especifica sobre desconsideracao - executando ato_agpet')
        try:
            from ..atos.wrappers import ato_agpet
            ato_agpet(driver)
            logger.info('[AGPET] ato_agpet executado com sucesso')
            return True
        except Exception as e:
            logger.error("ERRO em agravo_peticao: Erro ao executar ato_agpet: %s: %s", type(e).__name__, e)
            return False

    # 4. Para decisoes e despachos, executar ato_agpinter
    else:
        logger.info('[AGPET] Documento e %s - executando ato_agpinter', tipo_documento)
        try:
            from ..atos.wrappers import ato_agpinter
            ato_agpinter(driver)
            logger.info('[AGPET] ato_agpinter executado com sucesso')
            return True
        except Exception as e:
            logger.error("ERRO em agravo_peticao: Erro ao executar ato_agpinter: %s: %s", type(e).__name__, e)
            return False


def def_quesitos(item, driver: WebDriver) -> bool:
    """
    Processa peticoes com quesitos: analisa se deve admitir assistente tecnico ou apagar.

    Logica:
    1. Seleciona primeira peticao com quesitos na timeline.
    2. Extrai texto direto de Fix.extracao.
    3. Se texto contem "indicar assistente/assistentes" ou "assistente/assistentes tecnicos":
       - Chama _desp_assist para analisar despachos subsequentes.
    4. Caso contrario: flag apagar.

    Returns:
        bool: True se deve executar ato_assistente, False se deve apagar.
    """
    try:
        numero_processo = getattr(item, 'numero_processo', '')
        if not numero_processo:
            return False

        # 1. Selecionar primeira peticao com quesitos na timeline
        link_peticao = None
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        for item_timeline in itens:
            try:
                link = item_timeline.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                span_texto = link.find_element(By.CSS_SELECTOR, 'span:not(.sr-only)')
                texto_link = span_texto.text.lower()
                if 'quesitos' in texto_link or 'apresentacao de quesitos' in texto_link:
                    link_peticao = link
                    break
            except Exception:
                continue

        if not link_peticao:
            logger.warning('[QUESITOS] Nenhuma peticao com quesitos encontrada na timeline para %s', numero_processo)
            return False

        # 2. Extrair texto direto
        link_peticao.click()
        try:
            from ..core.utils.observer import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2)
        except Exception:
            pass

        texto_peticao = None
        try:
            resultado = extrair_direto(driver, timeout=10, debug=False, formatar=True)
            if resultado and resultado.get('sucesso'):
                texto_peticao = resultado.get('conteudo') or resultado.get('conteudo_bruto')
        except Exception as e:
            logger.warning('[QUESITOS] Erro ao extrair texto da peticao: %s', e)

        if not texto_peticao:
            logger.warning('[QUESITOS] Nao foi possivel extrair texto da peticao para %s', numero_processo)
            return False

        texto_lower = texto_peticao.lower()

        # 3. Verificar se contem "indicar assistente/assistentes" ou "assistente/assistentes tecnicos"
        if ('indicar assistente' in texto_lower or 'indicar assistentes' in texto_lower or
            'assistente tecnico' in texto_lower or 'assistentes tecnicos' in texto_lower):
            # Chamar _desp_assist
            return _desp_assist(driver, numero_processo)
        else:
            # Nao contem: flag apagar
            logger.info('[QUESITOS] Peticao nao contem indicacao de assistente - apagando %s', numero_processo)
            apagar(numero_processo, getattr(item, 'id_item', ''))
            return False

    except Exception as e:
        logger.error("ERRO em def_quesitos: %s: %s", type(e).__name__, e)
        return False


def _desp_assist(driver: WebDriver, numero_processo: str) -> bool:
    """
    Analisa despachos subsequentes a peticao de quesitos para decidir admissao de assistente.

    Logica:
    - Checa primeiro Despacho abaixo da peticao.
    - Se contem "venham a ser nomeados futuramente": flag apagar.
    - Senao, itera proximos despachos.
    - Se no segundo contem: flag apagar.
    - Senao: ato_assistente.

    Returns:
        bool: True se deve executar ato_assistente, False se deve apagar.
    """
    try:
        # Buscar despachos na timeline apos a peticao
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        despachos = []

        for item_timeline in itens:
            try:
                link = item_timeline.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                span_texto = link.find_element(By.CSS_SELECTOR, 'span:not(.sr-only)')
                tipo_doc = span_texto.text.lower().strip()
                if tipo_doc == 'despacho':
                    despachos.append(link)
            except Exception:
                continue

        if len(despachos) < 1:
            logger.warning('[DESP_ASSIST] Nenhum despacho encontrado para %s', numero_processo)
            return False

        # Checar primeiro despacho
        texto_primeiro = _extrair_texto_despacho(driver, despachos[0])
        if texto_primeiro and 'venham a ser nomeados futuramente' in texto_primeiro.lower():
            logger.info('[DESP_ASSIST] Primeiro despacho contem "venham a ser nomeados futuramente" - apagando %s', numero_processo)
            return False

        # Se nao, checar segundo despacho se existir
        if len(despachos) > 1:
            texto_segundo = _extrair_texto_despacho(driver, despachos[1])
            if texto_segundo and 'venham a ser nomeados futuramente' in texto_segundo.lower():
                logger.info('[DESP_ASSIST] Segundo despacho contem "venham a ser nomeados futuramente" - apagando %s', numero_processo)
                return False

        # Se nenhum contem: ato_assistente
        logger.info('[DESP_ASSIST] Nenhum despacho contem "venham a ser nomeados futuramente" - executando ato_assistente para %s', numero_processo)
        try:
            from ..atos.wrappers import ato_assistente
            if ato_assistente:
                ato_assistente(driver)
                logger.info('[DESP_ASSIST] ato_assistente executado com sucesso para %s', numero_processo)
                return True
            else:
                logger.warning('[DESP_ASSIST] ato_assistente nao disponivel')
                return False
        except Exception as e:
            logger.error("ERRO em _desp_assist: Erro ao executar ato_assistente: %s: %s", type(e).__name__, e)
            return False

    except Exception as e:
        logger.error("ERRO em _desp_assist: %s: %s", type(e).__name__, e)
        return False


def _extrair_texto_despacho(driver: WebDriver, link_despacho) -> Optional[str]:
    """
    Extrai texto de um despacho clicando no link.
    """
    try:
        link_despacho.click()
        try:
            from ..core.utils.observer import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2)
        except Exception:
            pass

        resultado = extrair_direto(driver, timeout=10, debug=False, formatar=True)
        if resultado and resultado.get('sucesso'):
            return resultado.get('conteudo') or resultado.get('conteudo_bruto')
        return None
    except Exception as e:
        logger.warning('[EXTRACAO_DESPACHO] Erro ao extrair texto do despacho: %s', e)
        return None


def contesta_calc(item, driver: WebDriver) -> bool:
    """
    Processa peticao de calculos de liquidacao:
    1. Busca despacho na timeline (ignora decisao/sentenca)
    2. Extrai texto do despacho
    3. Verifica se contem frase de intimacao para calculos de liquidacao
    4. Se sim: verifica advogado da reclamada em dadosatuais.json
       - com advogado -> ato_contestar
       - sem advogado  -> ato_revel
    """
    numero_processo = item.numero_processo
    logger.info('[CONTESTA_CALC] Iniciando para %s', numero_processo)

    # 1. Buscar despacho na timeline
    itens_tl = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
    link_despacho = None
    for item_tl in itens_tl:
        try:
            link = item_tl.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
            span = link.find_element(By.CSS_SELECTOR, 'span:not(.sr-only)')
            tipo_doc = span.text.lower().strip()
            if tipo_doc == 'despacho':
                link_despacho = link
                break
        except Exception:
            continue

    if not link_despacho:
        logger.info('[CONTESTA_CALC] Nenhum despacho encontrado -- sem acao')
        return False

    # 2. Extrair dados do processo
    try:
        extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
    except Exception as e:
        logger.warning('[CONTESTA_CALC] Falha ao extrair dados do processo: %s', e)

    # 3. Extrair texto do despacho e verificar frase
    texto = _extrair_texto_despacho(driver, link_despacho)
    if not texto:
        logger.warning('[CONTESTA_CALC] Nao foi possivel extrair texto do despacho')
        return False

    FRASE = 'para apresentar calculos de liquidacao'
    texto_norm = texto.lower()
    # normalizar acentos basicos
    import unicodedata
    texto_norm = unicodedata.normalize('NFD', texto_norm)
    texto_norm = ''.join(c for c in texto_norm if unicodedata.category(c) != 'Mn')

    if FRASE not in texto_norm:
        logger.info('[CONTESTA_CALC] Despacho nao contem frase de calculos -- sem acao')
        return False

    logger.info('[CONTESTA_CALC] Frase encontrada -- verificando advogado da reclamada')

    # 4. Verificar advogado da reclamada em dadosatuais.json
    tem_advogado_reclamada = False
    try:
        dados_path = Path('dadosatuais.json')
        if dados_path.exists():
            with open(dados_path, encoding='utf-8') as f:
                dados = json.load(f)
            partes = dados.get('partes', [])
            for parte in partes:
                polo = str(parte.get('polo') or '').lower()
                if 'passiv' in polo or 'reclama' in polo:
                    advogados = parte.get('advogados', [])
                    if advogados:
                        tem_advogado_reclamada = True
                        break
    except Exception as e:
        logger.warning('[CONTESTA_CALC] Erro ao ler dadosatuais.json: %s', e)

    try:
        from ..atos.wrappers import ato_contestar, ato_revel
        if tem_advogado_reclamada:
            logger.info('[CONTESTA_CALC] Reclamada tem advogado -- executando ato_contestar')
            return bool(ato_contestar(driver))
        else:
            logger.info('[CONTESTA_CALC] Reclamada sem advogado (revel) -- executando ato_revel')
            return bool(ato_revel(driver))
    except Exception as e:
        logger.error("ERRO em contesta_calc: Erro ao executar ato: %s: %s", type(e).__name__, e)
        return False
