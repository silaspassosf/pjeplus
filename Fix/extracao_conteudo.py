"""
Fix.extracao_conteudo - Extração de documentos e dados de processo PJe.

Consolidação de Fix.extracao_documento (298 linhas) + Fix.extracao_processo (388 linhas).
Os módulos originais permanecem como stubs de compatibilidade.
"""

import json
import re
import datetime
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import requests
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Fix.utils_observer import aguardar_renderizacao_nativa
from Fix.log import logger
from .utils import normalizar_cpf_cnpj, formatar_moeda_brasileira, formatar_data_brasileira


DESTINATARIOS_CACHE_PATH = Path('destinatarios_argos.json')


# ===========================================================================
# Extração de documentos (anterior Fix/extracao_documento.py)
# ===========================================================================

_JS_EXTRAIR_OBJECT = r"""
var callback = arguments[arguments.length - 1];
try {
    var obj = document.querySelector("object.conteudo-pdf");
    if (!obj) { callback({tipo: null, texto: null}); return; }

    var inner = obj.contentDocument;
    if (!inner) { callback({tipo: null, texto: null}); return; }

    if (typeof inner.defaultView.pdfjsLib !== 'undefined') {
        var pdfjsLib = inner.defaultView.pdfjsLib;
        var blobUrl  = new inner.defaultView.URLSearchParams(
                           inner.defaultView.location.search
                       ).get("file");

        pdfjsLib.GlobalWorkerOptions.workerSrc = "/pjekz/assets/pdf/build/pdf.worker.js";
        pdfjsLib.getDocument(blobUrl).promise.then(function(pdf) {
            var promises = [];
            for (var i = 1; i <= pdf.numPages; i++) {
                (function(pn){
                    promises.push(
                        pdf.getPage(pn).then(function(p) { return p.getTextContent(); })
                        .then(function(c) {
                            var linhas = {};
                            c.items.filter(function(it) { return it.str.trim(); })
                             .forEach(function(it) {
                                 var y = Math.round(it.transform[5] || it.transform);
                                 var k = Object.keys(linhas).find(function(k) {
                                     return Math.abs(parseInt(k) - y) <= 4;
                                 }) || String(y);
                                 if (!linhas[k]) linhas[k] = [];
                                 var x = Math.round((it.transform[4]||0));
                                 linhas[k].push({str: it.str, x: x});
                             });
                            return Object.keys(linhas).map(Number).sort(function(a,b){ return b - a; })
                                .map(function(y) {
                                    return linhas[y].sort(function(a,b){ return a.x - b.x; })
                                        .map(function(i){ return i.str.trim(); })
                                        .filter(Boolean).join(" | ");
                                }).join("\n");
                        })
                    );
                })(i);
            }
            return Promise.all(promises);
        }).then(function(paginas) {
            callback({tipo: "pdf", texto: paginas.join("\n\n--- PÁGINA ---\n\n")});
        }).catch(function(e) {
            callback({tipo: "pdf_erro", texto: null, erro: e.message});
        });

    } else {
        var viewer = inner.querySelector("#viewer");
        if (!viewer) { callback({tipo: null, texto: null}); return; }
        var texto = (viewer.innerText || viewer.textContent || "").trim();
        callback({tipo: "html", texto: texto.length > 50 ? texto : null});
    }

} catch(e) { callback({tipo: null, texto: null, erro: e.message}); }
"""


def _normalizar_texto_decisao(texto: str) -> str:
    """Normaliza espaços e quebras de linha de um texto de decisão."""
    if not texto:
        return ''
    return ' '.join(texto.split())


def _extrair_objeto_pje(driver: WebDriver, timeout: int = 8, debug: bool = False) -> Dict[str, Optional[str]]:
    from core.resultado_execucao import ResultadoExecucao
    try:
        if not aguardar_renderizacao_nativa(driver, "object.conteudo-pdf", 'aparecer', timeout):
            raise TimeoutError('object.conteudo-pdf não apareceu')
    except Exception:
        if debug:
            logger.info('[EXTRACAO_OBJ] object.conteudo-pdf não presente')
        return {'sucesso': False, 'status': 'FALHA', 'erro': 'object_not_found', 'tipo': None, 'texto': None}

    try:
        resultado = driver.execute_async_script(_JS_EXTRAIR_OBJECT)
        if not resultado:
            return {'sucesso': False, 'status': 'FALHA', 'tipo': None, 'texto': None}
        return resultado
    except Exception as e:
        if debug:
            logger.exception(f'[EXTRACAO_OBJ] erro exec js: {e}')
        return {'sucesso': False, 'status': 'FALHA', 'erro': str(e), 'tipo': None, 'texto': None}


def _formatar_html(texto: str) -> str:
    if not texto:
        return ''
    texto = re.sub(r'\r\n|\r', '\n', texto)
    texto = re.sub(r'[ \t]+', ' ', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    out: List[str] = []
    for l in linhas:
        up = l.upper()
        if len(l) < 100 and (l.isupper() or any(k in up for k in ['DECISÃO', 'DESPACHO', 'SENTENÇA', 'CONCLUSÃO', 'VISTOS'])):
            out.append(f"\n=== {l} ===\n")
            continue
        if re.match(r'^(DEFIRO|INDEFIRO|DETERMINO|HOMOLOGO)\b', up):
            out.append(f"\n>>> {l}")
            continue
        if any(p in l for p in ['Servidor Responsável', 'Juiz', 'Magistrado', 'Responsável']):
            out.append(f"\n--- {l} ---")
            continue
        if re.search(r'\b\d{1,2}/\d{1,2}/\d{4}\b', l) and len(l) < 50:
            out.append(f"\n[{l}]")
            continue
        out.append(l)
    res = '\n'.join(out)
    res = re.sub(r'\n{3,}', '\n\n', res)
    return res.strip()


def _formatar_pdf(texto: str) -> str:
    if not texto:
        return ''
    paginas = texto.split('\n\n--- PÁGINA ---\n\n')
    blocos: List[str] = []
    for p in paginas:
        linhas = [l.rstrip() for l in p.split('\n') if l.strip()]
        out_lines: List[str] = []
        in_table = False
        table_block: List[List[str]] = []
        for l in linhas:
            if '|' in l and len(l.split('|')) >= 3:
                cols = [c.strip() for c in l.split('|')]
                table_block.append(cols)
                in_table = True
                continue
            else:
                if in_table and table_block:
                    max_cols = max(len(r) for r in table_block)
                    widths = [0] * max_cols
                    for r in table_block:
                        for i, cell in enumerate(r):
                            widths[i] = max(widths[i], len(cell))
                    out_lines.append('\n=== TABELA ===\n')
                    for r in table_block:
                        row = '  '.join((r[i].ljust(widths[i]) if i < len(r) else ''.ljust(widths[i])) for i in range(max_cols))
                        out_lines.append(row)
                    table_block = []
                    in_table = False
                if re.search(r'\b(Total|Subtotal|Líquido|Bruto)\b', l, flags=re.IGNORECASE):
                    out_lines.append(f"** {l} **")
                else:
                    out_lines.append(l)
        if in_table and table_block:
            max_cols = max(len(r) for r in table_block)
            widths = [0] * max_cols
            for r in table_block:
                for i, cell in enumerate(r):
                    widths[i] = max(widths[i], len(cell))
            out_lines.append('\n=== TABELA ===\n')
            for r in table_block:
                row = '  '.join((r[i].ljust(widths[i]) if i < len(r) else ''.ljust(widths[i])) for i in range(max_cols))
                out_lines.append(row)
        blocos.append('\n'.join(out_lines))
    return '\n\n--- PÁGINA ---\n\n'.join(blocos).strip()


def _formatar_texto(texto: str, tipo_doc: Optional[str]) -> str:
    if not texto:
        return ''
    if tipo_doc == 'html':
        return _formatar_html(texto)
    if tipo_doc == 'pdf':
        return _formatar_pdf(texto)
    return texto.strip()


def _extrair_info_documento(driver: WebDriver, debug: bool = False) -> Dict[str, Any]:
    info: Dict[str, Any] = {'titulo': '', 'subtitulos': [], 'documento_id': ''}
    try:
        try:
            titulo = driver.find_element(By.CSS_SELECTOR, 'mat-card-title').text.strip()
            info['titulo'] = titulo
        except Exception:
            info['titulo'] = ''
        try:
            subs = driver.find_elements(By.CSS_SELECTOR, 'mat-card-subtitle')
            info['subtitulos'] = [s.text.strip() for s in subs if s.text.strip()]
        except Exception:
            info['subtitulos'] = []
        try:
            m = re.search(r'Id\s+(\w+)', info.get('titulo', ''))
            if m:
                info['documento_id'] = m.group(1)
        except Exception:
            info['documento_id'] = ''
    except Exception:
        if debug:
            logger.exception('[EXTRACAO_INFO] erro')
    return info


def extrair_direto(driver: WebDriver, timeout: int = 10, debug: bool = False, formatar: bool = True) -> Dict[str, Any]:
    resultado: Dict[str, Any] = {
        'sucesso': False, 'metodo': 'objeto_pje', 'tipo_doc': 'desconhecido',
        'conteudo': None, 'conteudo_bruto': None, 'chars': 0, 'info': {}
    }
    try:
        res = _extrair_objeto_pje(driver, timeout=timeout, debug=debug)
        tipo = res.get('tipo') if isinstance(res, dict) else None
        texto = res.get('texto') if isinstance(res, dict) else None
        if tipo is None or texto is None:
            resultado['info'] = _extrair_info_documento(driver, debug=debug)
            return resultado
        resultado['tipo_doc'] = tipo
        resultado['conteudo_bruto'] = texto
        resultado['conteudo'] = _formatar_texto(texto, tipo) if formatar else texto
        resultado['chars'] = len(resultado['conteudo'] or '')
        resultado['sucesso'] = True
        resultado['info'] = _extrair_info_documento(driver, debug=debug)
        return resultado
    except Exception as e:
        if debug:
            logger.exception(f'[EXTRAIR_DIRETO] erro: {e}')
        resultado['info'] = _extrair_info_documento(driver, debug=debug)
        return resultado


def extrair_documento(driver: WebDriver, regras_analise=None, timeout: int = 15, log: bool = False) -> Optional[str]:
    """Compat shim: retorna texto formatado (str) ou None se falhar."""
    res = extrair_direto(driver, timeout=timeout, debug=log, formatar=True)
    if not res or not res.get('sucesso'):
        return None
    return res.get('conteudo')


def _extrair_formatar_texto(texto_bruto: str, debug: bool = False) -> str:
    """Compat shim: formata texto bruto detectando tipo automaticamente."""
    tipo = 'pdf' if isinstance(texto_bruto, str) and '--- PÁGINA ---' in texto_bruto else 'html'
    try:
        return _formatar_texto(texto_bruto, tipo)
    except Exception:
        if debug:
            logger.exception('[_extrair_formatar_texto] erro')
        return texto_bruto or ''


def extrair_pdf(driver: WebDriver, timeout: int = 15, debug: bool = False, log: bool = False) -> Optional[str]:
    """Compat shim: extrai especificamente PDF."""
    debug = debug or log
    res = extrair_direto(driver, timeout=timeout, debug=debug, formatar=True)
    if not res or not res.get('sucesso'):
        return None
    if res.get('tipo_doc') != 'pdf':
        return None
    return res.get('conteudo')


# ===========================================================================
# Extração de dados do processo e destinatários (anterior Fix/extracao_processo.py)
# ===========================================================================

def extrair_dados_processo(driver: WebDriver, caminho_json: str = 'dadosatuais.json', debug: bool = False) -> Dict[str, Any]:
    """Extrai dados do processo via API do PJe (TRT2)."""

    def get_cookies_dict(driver: WebDriver) -> Dict[str, str]:
        try:
            return {c['name']: c['value'] for c in driver.get_cookies()}
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
            elemento = driver.find_element(By.XPATH, xpath_clipboard)
            aria_label = elemento.get_attribute("aria-label")
            if aria_label:
                match_cb = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
                if match_cb:
                    return match_cb.group(1)
        except Exception:
            pass
        return None

    def extrair_trt_host(driver: WebDriver) -> str:
        return urlparse(driver.current_url).netloc

    def obter_id_processo_via_api(numero: str, sess: requests.Session, host: str) -> Optional[int]:
        url = f'https://{host}/pje-comum-api/api/agrupamentotarefas/processos?numero={numero}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                if data:
                    return data[0].get('idProcesso')
        except Exception as e:
            if debug:
                logger.info(f'[extrair.py] Erro ao obter ID via API: {e}')
        return None

    def obter_dados_processo_via_api(id_proc: int, sess: requests.Session, host: str) -> Optional[Dict[str, Any]]:
        url = f'https://{host}/pje-comum-api/api/processos/id/{id_proc}'
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

    processo_memoria: Dict[str, Any] = {
        "numero": [dados_processo.get("numero", numero_processo)],
        "id": id_processo,
        "autor": [], "reu": [], "terceiro": [], "divida": {},
        "justicaGratuita": [], "transito": "", "custas": "", "dtAutuacao": "",
        "classeJudicial": dados_processo.get("classeJudicial", {}),
        "labelFaseProcessual": dados_processo.get("labelFaseProcessual", ""),
        "orgaoJuizo": dados_processo.get("orgaoJuizo", {}),
        "dataUltimo": dados_processo.get("dataUltimo", "")
    }

    dt = dados_processo.get("autuadoEm")
    if dt:
        try:
            from datetime import datetime as _dt
            dtobj = _dt.fromisoformat(dt.replace('Z', '+00:00'))
            processo_memoria["dtAutuacao"] = dtobj.strftime('%d/%m/%Y')
        except Exception:
            processo_memoria["dtAutuacao"] = dt

    def criar_pessoa_limpa(parte: Dict[str, Any]) -> Dict[str, Any]:
        nome = parte.get("nome", "").strip()
        pessoa: Dict[str, Any] = {"nome": nome, "cpfcnpj": normalizar_cpf_cnpj(parte.get("documento", ""))}
        reps = parte.get("representantes", [])
        if reps:
            adv = reps[0]
            pessoa["advogado"] = {
                "nome": adv.get("nome", "").strip(),
                "cpf": normalizar_cpf_cnpj(adv.get("documento", "")),
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
                processo_memoria["divida"] = {
                    "valor": formatar_moeda_brasileira(mais_recente.get("total", 0)),
                    "data": formatar_data_brasileira(mais_recente.get("dataLiquidacao", ""))
                }
    except Exception as e:
        if debug:
            logger.info('[extrair.py] Erro ao buscar divida:', e)

    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(processo_memoria, f, ensure_ascii=False, indent=2)

    logger.info(f"[extrair_dados_processo] dadosatuais.json salvo (numero={processo_memoria.get('numero')})")
    return processo_memoria


def extrair_destinatarios_decisao(texto_decisao: Optional[str], dados_processo: Optional[Dict[str, Any]] = None, debug: bool = False) -> List[Dict[str, Any]]:
    """Extrai possíveis destinatários (nome + CPF/CNPJ) a partir do texto da decisão."""
    if not texto_decisao:
        if debug:
            logger.info('[DEST][WARN] Texto vazio.')
        return []

    texto_compacto = _normalizar_texto_decisao(texto_decisao)
    texto_upper = texto_compacto.upper()
    resultados = []
    vistos: set = set()
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
            ' SECRETARIA ', ' RETIFICAÇÃO ', ' RETIFICACAO ', ' PARA INCLUIR ', ' PARA INCLUSAO '
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

        registro: Dict[str, Any] = {
            'nome_identificado': nome_bruto.strip(),
            'documento': documento_bruto.strip(),
            'documento_normalizado': doc_normalizado,
            'tipo_documento': 'CPF' if len(doc_normalizado) == 11 else 'CNPJ',
            'polo': None,
            'nome_oficial': None
        }

        if dados_processo:
            for parte in (dados_processo.get('reu') or []):
                if normalizar_cpf_cnpj(parte.get('cpfcnpj')) == doc_normalizado:
                    registro['polo'] = 'reu'
                    registro['nome_oficial'] = parte.get('nome', '').strip() or registro['nome_identificado']
                    break

        resultados.append(registro)

    if debug:
        logger.info(f'[DEST][DEBUG] Destinatários: {json.dumps(resultados, ensure_ascii=False, indent=2)}')

    return resultados


def salvar_destinatarios_cache(chave_simples: str, destinatarios: List[Dict[str, Any]], origem: str = '') -> None:
    """Salva destinatários no cache associado ao processo atual (lido de dadosatuais.json)."""
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

    payload = {
        'numero_processo': numero_processo,
        'destinatarios': destinatarios,
        'origem': origem,
        'timestamp': datetime.datetime.now().isoformat()
    }
    try:
        DESTINATARIOS_CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.info(f'[DEST][CACHE] Destinatários salvos: processo={numero_processo}, origem={origem}, qtd={len(destinatarios)}')
    except Exception as exc:
        logger.warning(f'[DEST][CACHE][WARN] Falha ao salvar cache: {exc}')


def carregar_destinatarios_cache() -> Dict[str, Any]:
    """Carrega destinatários do cache para o processo atual."""
    numero_processo_atual = None
    try:
        if Path('dadosatuais.json').exists():
            dados = json.loads(Path('dadosatuais.json').read_text(encoding='utf-8'))
            numero_list = dados.get('numero', [])
            numero_processo_atual = numero_list[0] if isinstance(numero_list, list) and numero_list else None
    except Exception as exc:
        logger.warning(f'[DEST][WARN] Erro ao determinar processo atual: {exc}')

    if not numero_processo_atual:
        logger.warning('[DEST][CACHE] Não foi possível extrair número do processo de dadosatuais.json')
        return {}

    try:
        if DESTINATARIOS_CACHE_PATH.exists():
            cache = json.loads(DESTINATARIOS_CACHE_PATH.read_text(encoding='utf-8'))
            if cache.get('numero_processo') == numero_processo_atual:
                logger.info(f'[DEST][CACHE] Cache encontrado: processo={numero_processo_atual}, qtd={len(cache.get("destinatarios", []))}')
                return cache
            logger.info(f'[DEST][CACHE] Cache para outro processo ({cache.get("numero_processo")} vs {numero_processo_atual})')
    except Exception as exc:
        logger.warning(f'[DEST][WARN] Erro ao carregar cache: {exc}')

    return {}
