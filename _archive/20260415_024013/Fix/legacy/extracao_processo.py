import logging
logger = logging.getLogger(__name__)

"""
Fix.extracao_processo - Extração de dados do processo e destinatários.

Separado de Fix.extracao para reduzir tamanho do arquivo principal.
"""

import json
import datetime
import re
from urllib.parse import urlparse
from pathlib import Path
import requests
from selenium.webdriver.common.by import By
from typing import Optional, Dict, Any, List, Union
from selenium.webdriver.remote.webdriver import WebDriver
from Fix.log import logger
from Fix.utils import normalizar_cpf_cnpj, formatar_moeda_brasileira, formatar_data_brasileira


DESTINATARIOS_CACHE_PATH = Path('destinatarios_argos.json')


def extrair_dados_processo(driver: WebDriver, caminho_json: str = 'dadosatuais.json', debug: bool = False) -> Dict[str, Any]:
    """
    Extrai dados do processo via API do PJe (TRT2), seguindo a mesma lógica da extensão MaisPje.
    Função completa auto-contida.
    """
    def get_cookies_dict(driver: WebDriver) -> Dict[str, str]:
        try:
            cookies = driver.get_cookies()
            return {c['name']: c['value'] for c in cookies}
        except Exception as e:
            logger.info(f"[ERRO] Falha ao obter cookies: {e}")
            return {}

    def extrair_numero_processo_url(driver: WebDriver) -> Optional[str]:
        url = driver.current_url
        m = re.search(r'processo/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', url)
        if m:
            return m.group(1)

        try:
            xpath_clipboard = "//pje-icone-clipboard//span[contains(@aria-label, 'Copia o número do processo')]"
            elemento_clipboard = driver.find_element(By.XPATH, xpath_clipboard)
            aria_label = elemento_clipboard.get_attribute("aria-label")
            if aria_label:
                match_clipboard = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
                if match_clipboard:
                    return match_clipboard.group(1)
        except:
            pass

        return None

    def extrair_trt_host(driver: WebDriver) -> str:
        url = driver.current_url
        parsed = urlparse(url)
        return parsed.netloc

    def obter_id_processo_via_api(numero_processo: str, sess: requests.Session, trt_host: str) -> Optional[int]:
        url = f'https://{trt_host}/pje-comum-api/api/agrupamentotarefas/processos?numero={numero_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('idProcesso')
        except Exception as e:
            if debug:
                logger.info(f'[extrair.py] Erro ao obter ID via API: {e}')
        return None

    def obter_dados_processo_via_api(id_processo: int, sess: requests.Session, trt_host: str) -> Optional[Dict[str, Any]]:
        url = f'https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                return resp.json()
        except Exception as e:
            if debug:
                logger.info(f'[extrair.py] Erro ao obter dados via API: {e}')
        return None

    cookies = get_cookies_dict(driver)
    numero_processo = extrair_numero_processo_url(driver)
    trt_host = extrair_trt_host(driver)

    sess = requests.Session()
    for k, v in cookies.items():
        sess.cookies.set(k, v)
    sess.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Grau-Instancia": "1"
    })

    if not numero_processo:
        if debug:
            logger.info('[extrair.py] Não foi possível extrair o número do processo.')
        return {}

    id_processo = obter_id_processo_via_api(numero_processo, sess, trt_host)
    if not id_processo:
        if debug:
            logger.info('[extrair.py] Não foi possível obter o ID do processo via API.')
        return {}

    dados_processo = obter_dados_processo_via_api(id_processo, sess, trt_host)
    if not dados_processo:
        if debug:
            logger.info('[extrair.py] Não foi possível obter dados do processo via API.')
        return {}

    processo_memoria = {
        "numero": [dados_processo.get("numero", numero_processo)],
        "id": id_processo,
        "autor": [],
        "reu": [],
        "terceiro": [],
        "divida": {},
        "justicaGratuita": [],
        "transito": "",
        "custas": "",
        "dtAutuacao": "",
        "classeJudicial": dados_processo.get("classeJudicial", {}),
        "labelFaseProcessual": dados_processo.get("labelFaseProcessual", ""),
        "orgaoJuizo": dados_processo.get("orgaoJuizo", {}),
        "dataUltimo": dados_processo.get("dataUltimo", "")
    }

    dt = dados_processo.get("autuadoEm")
    if dt:
        from datetime import datetime
        try:
            dtobj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            processo_memoria["dtAutuacao"] = dtobj.strftime('%d/%m/%Y')
        except:
            processo_memoria["dtAutuacao"] = dt

    def criar_pessoa_limpa(parte: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um dicionário limpo com os dados da parte e seu advogado."""
        nome = parte.get("nome", "").strip()
        doc_original = parte.get("documento", "")
        doc_normalizado = normalizar_cpf_cnpj(doc_original)
        pessoa = {"nome": nome, "cpfcnpj": doc_normalizado}

        reps = parte.get("representantes", [])
        if reps:
            adv = reps[0]
            cpf_advogado = normalizar_cpf_cnpj(adv.get("documento", ""))
            pessoa["advogado"] = {
                "nome": adv.get("nome", "").strip(),
                "cpf": cpf_advogado,
                "oab": adv.get("numeroOab", "")
            }
        return pessoa

    try:
        url_partes = f"https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}/partes"
        resp = sess.get(url_partes, timeout=10)
        if resp.ok:
            j = resp.json()
            for parte in j.get("ATIVO", []):
                processo_memoria["autor"].append(criar_pessoa_limpa(parte))
            for parte in j.get("PASSIVO", []):
                processo_memoria["reu"].append(criar_pessoa_limpa(parte))
            for parte in j.get("TERCEIROS", []):
                processo_memoria["terceiro"].append({"nome": parte.get("nome", "").strip()})
    except Exception as e:
        if debug:
            logger.info('[extrair.py] Erro ao buscar partes:', e)

    try:
        url_divida = f"https://{trt_host}/pje-comum-api/api/calculos/processo?pagina=1&tamanhoPagina=10&ordenacaoCrescente=false&idProcesso={id_processo}"
        resp = sess.get(url_divida, timeout=10)
        if resp.ok:
            j = resp.json()
            if j and j.get("resultado"):
                mais_recente = j["resultado"][0]
                valor_raw = mais_recente.get("total", 0)
                data_raw = mais_recente.get("dataLiquidacao", "")
                processo_memoria["divida"] = {
                    "valor": formatar_moeda_brasileira(valor_raw),
                    "data": formatar_data_brasileira(data_raw)
                }
    except Exception as e:
        if debug:
            logger.info('[extrair.py] Erro ao buscar divida:', e)

    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(processo_memoria, f, ensure_ascii=False, indent=2)

    # Confirmação de gravação (útil para debug e paridade com o legado)
    try:
        logger.info(f"[extrair_dados_processo] dadosatuais.json salvo (numero={processo_memoria.get('numero')})")
    except Exception:
        pass

    return processo_memoria


def extrair_destinatarios_decisao(texto_decisao: Optional[str], dados_processo: Optional[Dict[str, Any]] = None, debug: bool = False) -> List[Dict[str, Any]]:
    """Extrai possíveis destinatários (nome + CPF/CNPJ) a partir do texto completo da decisão."""
    if not texto_decisao:
        if debug:
            logger.info('[DEST][WARN] Texto da decisão vazio. Nenhum destinatário extraído.')
        return []

    from Fix.extracao_documento import _normalizar_texto_decisao

    texto_compacto = _normalizar_texto_decisao(texto_decisao)
    texto_upper = texto_compacto.upper()
    resultados = []
    vistos = set()

    padrao_doc = re.compile(r'(CPF|CNPJ)\s*[:\-]?\s*([\d\.\-/]+)')

    for match in padrao_doc.finditer(texto_upper):
        documento_bruto = match.group(2)
        doc_normalizado = normalizar_cpf_cnpj(documento_bruto)
        if len(doc_normalizado) not in (11, 14):
            continue

        inicio_procura = max(0, match.start() - 160)
        prefixo = texto_upper[inicio_procura:match.start()]
        match_nome = re.search(r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s'\.-]{2,})[,\s]*$", prefixo)
        if not match_nome:
            continue

        nome_inicio = inicio_procura + match_nome.start(1)
        nome_fim = inicio_procura + match_nome.end(1)
        nome_bruto = texto_compacto[nome_inicio:nome_fim].strip()
        nome_upper_ref = nome_bruto.upper()
        marcadores = [
            ' SÓCIO ', ' SOCIO ', ' SÓCIA ', ' SOCIA ', ' EMPRESA ', ' PARTE ',
            ' EXECUTADA ', ' EXECUTADO ', ' INCLUIR ', ' INCLUSÃO ', ' INCLUSAO ',
            ' SECRETARIA ', ' RETIFICAÇÃO ', ' RETIFICACAO ', ' PARA INCLUIR ',
            ' PARA INCLUSAO '
        ]
        for marcador in marcadores:
            idx = nome_upper_ref.rfind(marcador)
            if idx != -1:
                corte = idx + len(marcador)
                nome_bruto = nome_bruto[corte:].strip(' ,.-')
                nome_upper_ref = nome_upper_ref[corte:]
                break

        nome_bruto = nome_bruto.lstrip('.- ').strip()
        if nome_bruto.upper().startswith(('O ', 'A ', 'OS ', 'AS ')):
            partes_nome = nome_bruto.split(' ', 1)
            if len(partes_nome) > 1:
                nome_bruto = partes_nome[1]
        nome_bruto = nome_bruto.strip()
        chave = (doc_normalizado, nome_bruto.strip().upper())
        if chave in vistos:
            continue
        vistos.add(chave)

        registro = {
            'nome_identificado': nome_bruto.strip(),
            'documento': documento_bruto.strip(),
            'documento_normalizado': doc_normalizado,
            'tipo_documento': 'CPF' if len(doc_normalizado) == 11 else 'CNPJ',
            'polo': None,
            'nome_oficial': None
        }

        if dados_processo:
            partes_passivas = dados_processo.get('reu', []) or []
            for parte in partes_passivas:
                doc_cadastrado = normalizar_cpf_cnpj(parte.get('cpfcnpj'))
                if doc_cadastrado and doc_cadastrado == doc_normalizado:
                    registro['polo'] = 'reu'
                    registro['nome_oficial'] = parte.get('nome', '').strip() or registro['nome_identificado']
                    break

        resultados.append(registro)

    if debug:
        logger.info(f'[DEST][DEBUG] Destinatários identificados: {json.dumps(resultados, ensure_ascii=False, indent=2)}')

    return resultados


def salvar_destinatarios_cache(chave_simples: str, destinatarios: List[Dict[str, Any]], origem: str = '') -> None:  # noqa: D401
    """
    Salva destinatários no cache GLOBAL, casado com número do processo ATUAL.
    
    **IMPORTANTE:** Extrai o número do processo de dadosatuais.json (populado por extrair_dados_processo)
    de forma automática, garantindo que o cache sempre tenha o número correto.
    
    Fluxo:
    1. Processo X executa extrair_dados_processo() → popula dadosatuais.json com número de X
    2. Processo X executa extrair_destinatarios_decisao() → extrai nomes
    3. Processo X chama salvar_destinatarios_cache(destinatarios=nomes)
    4. Esta função lê número de X de dadosatuais.json e salva {numero_X, nomes} no cache
    
    Args:
        chave_simples: (ignorado - número é extraído de dadosatuais.json)
        destinatarios: lista de destinatarios extraidos da decisão
        origem: onde vieram (ex: "argos_idpj_decisao")
    """
    # Extrair número do processo ATUAL de dadosatuais.json
    numero_processo = None
    try:
        if Path('dadosatuais.json').exists():
            dados = json.loads(Path('dadosatuais.json').read_text(encoding='utf-8'))
            numero_list = dados.get('numero', [])
            numero_processo = numero_list[0] if isinstance(numero_list, list) and numero_list else None
            if not numero_processo:
                logger.warning('[DEST][CACHE] Número de processo não encontrado em dadosatuais.json')
                return
    except Exception as exc:
        logger.warning(f'[DEST][CACHE][WARN] Erro ao ler dadosatuais.json: {exc}')
        return
    
    # Salvar com número automático (não usar chave_simples)
    payload = {
        'numero_processo': numero_processo,
        'destinatarios': destinatarios,
        'origem': origem,
        'timestamp': datetime.datetime.now().isoformat()
    }
    try:
        DESTINATARIOS_CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.info(
            f'[DEST][CACHE] ✅ Destinatários salvos: '
            f'processo={numero_processo}, origem={origem}, quantidade={len(destinatarios)}'
        )
    except Exception as exc:
        logger.warning(f'[DEST][CACHE][WARN] Falha ao salvar cache: {exc}')


def carregar_destinatarios_cache() -> Dict[str, Any]:
    """
    Carrega destinatários em cache ESPECÍFICO para o processo atual.
    
    Busca o número do processo em dadosatuais.json (populado por extrair_dados_processo)
    e procura no arquivo cache global por destinatarios extraidos daquele processo específico.
    
    Returns:
        Dict com {numero_processo, destinatarios, origem} se encontrado, {} caso contrário
    """
    # Passo 1: Extrair número do processo ATUAL de dadosatuais.json
    numero_processo_atual = None
    try:
        if Path('dadosatuais.json').exists():
            dados = json.loads(Path('dadosatuais.json').read_text(encoding='utf-8'))
            numero_list = dados.get('numero', [])
            numero_processo_atual = numero_list[0] if isinstance(numero_list, list) and numero_list else None
            if numero_processo_atual:
                logger.info(f'[DEST][CACHE] Processo atual: {numero_processo_atual}')
    except Exception as exc:
        logger.warning(f'[DEST][WARN] Erro ao determinar processo atual: {exc}')
    
    if not numero_processo_atual:
        logger.warning('[DEST][CACHE] Não foi possível extrair número do processo de dadosatuais.json')
        return {}
    
    # Passo 2: Buscar no cache global pelo número específico
    try:
        if DESTINATARIOS_CACHE_PATH.exists():
            cache = json.loads(DESTINATARIOS_CACHE_PATH.read_text(encoding='utf-8'))
            cache_numero = cache.get('numero_processo', '')
            
            if cache_numero == numero_processo_atual:
                # Cache está casado com este processo!
                destinatarios = cache.get('destinatarios', [])
                origem = cache.get('origem', '')
                logger.info(
                    f'[DEST][CACHE] ✅ Cache encontrado: processo={numero_processo_atual}, '
                    f'destinatarios={len(destinatarios)}, origem={origem}'
                )
                return cache
            else:
                logger.info(
                    f'[DEST][CACHE] Cache existe mas para outro processo '
                    f'(cache={cache_numero}, atual={numero_processo_atual}) → fallback'
                )
                return {}
    except Exception as exc:
        logger.warning(f'[DEST][WARN] Erro ao carregar cache: {exc}')
    
    logger.info(f'[DEST][CACHE] Nenhum cache para processo {numero_processo_atual} → fallback')
    return {}