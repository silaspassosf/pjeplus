"""
Andrei.extracao - Extracao de documentos e dados do PJe.
Adaptado de Fix.extracao e Peticao.core.extracao.extracao.
"""

import re
import json
import time
import datetime
import logging
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from urllib.parse import urlparse

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import requests

from Andrei.utils_selenium import aguardar_renderizacao_nativa

logger = logging.getLogger(__name__)

# Caminho padrao para salvar dados do processo
_DADOSATUAIS_PATH = str(Path(__file__).parent / "dadosatuais.json")


# =============================================================================
# CONSTANTES JS
# =============================================================================

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
            callback({tipo: "pdf", texto: paginas.join("\n\n--- PAGINA ---\n\n")});
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


# =============================================================================
# FUNCOES INTERNAS DE EXTRACAO DIRETA
# =============================================================================


def _extrair_objeto_pje(driver: WebDriver, timeout: int = 8, debug: bool = False) -> Dict[str, Optional[str]]:
    """Extrai texto do object.conteudo-pdf via JavaScript assincrono (PDF.js ou HTML)."""
    try:
        if not aguardar_renderizacao_nativa(driver, "object.conteudo-pdf", 'aparecer', timeout):
            raise TimeoutError('object.conteudo-pdf nao apareceu')
    except Exception:
        if debug:
            logger.info('[EXTRACAO_OBJ] object.conteudo-pdf nao presente')
        return {'sucesso': False, 'status': 'FALHA', 'detalhes': {'tipo': None, 'texto': None}}

    try:
        resultado = driver.execute_async_script(_JS_EXTRAIR_OBJECT)
        if not resultado:
            return {'sucesso': False, 'status': 'FALHA', 'detalhes': {'tipo': None, 'texto': None}}
        return resultado
    except Exception as e:
        if debug:
            logger.exception('[EXTRACAO_OBJ] erro exec js: %s', e)
        return {'sucesso': False, 'status': 'FALHA', 'erro': str(e), 'detalhes': {'tipo': None, 'texto': None}}


def _formatar_html(texto: str) -> str:
    """Formata texto extraido de HTML com estrutura organizacional."""
    if not texto:
        return ''
    texto = re.sub(r'\r\n|\r', '\n', texto)
    texto = re.sub(r'[ \t]+', ' ', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    out: List[str] = []
    for l in linhas:
        up = l.upper()
        if len(l) < 100 and (l.isupper() or any(k in up for k in ['DECISAO', 'DESPACHO', 'SENTENCA', 'CONCLUSAO', 'VISTOS'])):
            out.append(f"\n=== {l} ===\n")
            continue
        if re.match(r'^(DEFIRO|INDEFIRO|DETERMINO|HOMOLOGO)\b', up):
            out.append(f"\n>>> {l}")
            continue
        if any(p in l for p in ['Servidor Responsavel', 'Juiz', 'Magistrado', 'Responsavel']):
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
    """Formata texto extraido de PDF, preservando tabelas e totais."""
    if not texto:
        return ''
    paginas = texto.split('\n\n--- PAGINA ---\n\n')
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
                        row = '  '.join(
                            (r[i].ljust(widths[i]) if i < len(r) else ''.ljust(widths[i]))
                            for i in range(max_cols)
                        )
                        out_lines.append(row)
                    table_block = []
                    in_table = False
                if re.search(r'\b(Total|Subtotal|Liquido|Bruto)\b', l, flags=re.IGNORECASE):
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
                row = '  '.join(
                    (r[i].ljust(widths[i]) if i < len(r) else ''.ljust(widths[i]))
                    for i in range(max_cols)
                )
                out_lines.append(row)
    blocos.append('\n'.join(out_lines))
    return '\n\n--- PAGINA ---\n\n'.join(blocos).strip()


def _formatar_texto(texto: str, tipo_doc: Optional[str]) -> str:
    """Seleciona formatador conforme tipo do documento."""
    if not texto:
        return ''
    if tipo_doc == 'html':
        return _formatar_html(texto)
    if tipo_doc == 'pdf':
        return _formatar_pdf(texto)
    return texto.strip()


def _extrair_info_documento(driver: WebDriver, debug: bool = False) -> Dict[str, Any]:
    """Extrai metadados do cabecalho do documento (titulo, subtitulos, id)."""
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


# =============================================================================
# EXTRACAO DIRETA
# =============================================================================


def extrair_direto(driver: WebDriver, timeout: int = 10, debug: bool = False, formatar: bool = True) -> Dict[str, Any]:
    """
    Extrai o conteudo do documento PDF ativo na tela do processo PJe diretamente.
    Sem cliques, sem interacao, apenas leitura direta via object.conteudo-pdf.

    Args:
        driver: WebDriver do Selenium
        timeout: Timeout para operacoes
        debug: Se True, exibe logs detalhados
        formatar: Se True, aplica formatacao organizacional ao texto

    Returns:
        dict com chaves: sucesso, metodo, tipo_doc, conteudo, conteudo_bruto, chars, info
    """
    resultado: Dict[str, Any] = {
        'sucesso': False,
        'metodo': 'objeto_pje',
        'tipo_doc': 'desconhecido',
        'conteudo': None,
        'conteudo_bruto': None,
        'chars': 0,
        'info': {}
    }
    try:
        res = _extrair_objeto_pje(driver, timeout=timeout, debug=debug)
        tipo = res.get('tipo') if isinstance(res, dict) else None
        texto = res.get('texto') if isinstance(res, dict) else None
        if tipo is None or texto is None:
            resultado['sucesso'] = False
            resultado['tipo_doc'] = 'desconhecido'
            resultado['info'] = _extrair_info_documento(driver, debug=debug)
            return resultado

        resultado['tipo_doc'] = tipo
        resultado['conteudo_bruto'] = texto
        if formatar:
            resultado['conteudo'] = _formatar_texto(texto, tipo)
        else:
            resultado['conteudo'] = texto
        resultado['chars'] = len(resultado['conteudo'] or '')
        resultado['sucesso'] = True
        resultado['info'] = _extrair_info_documento(driver, debug=debug)
        return resultado
    except Exception as e:
        if debug:
            logger.exception('[EXTRAIR_DIRETO] erro: %s', e)
        resultado['sucesso'] = False
        resultado['info'] = _extrair_info_documento(driver, debug=debug)
        return resultado


def extrair_documento(driver: WebDriver, regras_analise=None, timeout: int = 15, log: bool = False) -> Optional[str]:
    """
    Extrai o texto do documento aberto.
    Compat shim: retorna texto formatado (str) ou None se falhar.
    """
    res = extrair_direto(driver, timeout=timeout, debug=log, formatar=True)
    if not res or not res.get('sucesso'):
        return None
    return res.get('conteudo')


def _extrair_formatar_texto(texto_bruto: str, debug: bool = False) -> str:
    """Compat shim: manter nome antigo esperado por outros modulos."""
    tipo = 'pdf' if isinstance(texto_bruto, str) and '--- PAGINA ---' in texto_bruto else 'html'
    try:
        return _formatar_texto(texto_bruto, tipo)
    except Exception:
        if debug:
            logger.exception('[_extrair_formatar_texto] erro')
        return texto_bruto or ''


# =============================================================================
# CRIAR GIGS
# =============================================================================


def _parse_gigs_string(string):
    """
    Parseia string de teste GIGS automaticamente.

    Regras:
    - sem / = OBSERVACAO
    - uma / ou // juntas = prazo/observacao ou prazo//observacao (sem responsavel)
    - duas / entre parametros = prazo/responsavel/observacao
    """
    if '/' not in string:
        return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}

    if '//' in string:
        partes = string.split('//', 1)
        if len(partes) == 2:
            prazo_str, obs = partes
            try:
                dias_uteis = int(prazo_str.strip())
            except ValueError:
                dias_uteis = None
            return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}

    partes = string.split('/')
    if len(partes) == 2:
        prazo_str, obs = partes
        try:
            dias_uteis = int(prazo_str.strip())
        except ValueError:
            dias_uteis = None
        return {'dias_uteis': dias_uteis, 'responsavel': None, 'observacao': obs.strip()}
    elif len(partes) == 3:
        prazo_str, resp, obs = partes
        try:
            dias_uteis = int(prazo_str.strip())
        except ValueError:
            dias_uteis = None
        return {'dias_uteis': dias_uteis, 'responsavel': resp.strip(), 'observacao': obs.strip()}

    return {'dias_uteis': None, 'responsavel': None, 'observacao': string.strip()}


def criar_gigs(driver, dias_uteis=None, responsavel=None, observacao=None, timeout=10, log=True):
    """
    Cria atividade GIGS na aba /detalhe - versao portada de Fix/extracao.py

    Suporta multiplas assinaturas:
    - criar_gigs(driver, "observacao simples")
    - criar_gigs(driver, "7/xs carta")
    - criar_gigs(driver, "7/xs/carta urgente")
    - criar_gigs(driver, 7, "xs", "carta")
    """
    if isinstance(dias_uteis, str) and responsavel is None and observacao is None:
        parsed = _parse_gigs_string(dias_uteis)
        dias_uteis = parsed['dias_uteis']
        responsavel = parsed['responsavel']
        observacao = parsed['observacao']

    if observacao is None and responsavel is not None:
        observacao = responsavel
        responsavel = None

    try:
        if log:
            info = f"{dias_uteis or '-'}/{responsavel or '-'}/{observacao or '-'}"
            logger.debug("[GIGS] Criando: %s", info)

        if log:
            logger.debug('[GIGS] Clicando Nova Atividade...')
        btn_nova = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[.//span[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')] "
                "or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')]")
            )
        )
        btn_nova.click()
        time.sleep(1)

        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]'))
        )
        if log:
            logger.debug('[GIGS] Formulario aberto')

        if dias_uteis:
            campo_dias = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="dias"]')
            campo_dias.clear()
            campo_dias.send_keys(str(dias_uteis))
            time.sleep(0.3)
            if log:
                logger.debug('[GIGS] Prazo: %s dias', dias_uteis)

        if responsavel:
            campo_resp = driver.find_element(By.CSS_SELECTOR, 'input[formcontrolname="responsavel"]')
            campo_resp.clear()
            campo_resp.send_keys(responsavel)
            time.sleep(0.5)
            campo_resp.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.2)
            campo_resp.send_keys(Keys.ENTER)
            if log:
                logger.debug('[GIGS] Responsavel: %s', responsavel)

        if observacao:
            campo_obs = driver.find_element(By.CSS_SELECTOR, 'textarea[formcontrolname="observacao"]')
            campo_obs.clear()
            campo_obs.send_keys(observacao)
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                campo_obs
            )
            time.sleep(0.3)
            if log:
                obs_preview = observacao[:50] + '...' if len(observacao) > 50 else observacao
                logger.debug('[GIGS] Observacao: %s', obs_preview)

        if log:
            logger.debug('[GIGS] Salvando...')
        btn_salvar = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Salvar')]"))
        )
        btn_salvar.click()

        time.sleep(0.3)
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//snack-bar-container//span[contains(normalize-space(.), 'Atividade salva com sucesso')]"))
            )
            if log:
                logger.debug('[GIGS] Atividade criada com sucesso')
            return True
        except TimeoutException:
            if log:
                logger.warning('[GIGS] Confirmacao nao detectada, assumindo sucesso')
            return True

    except Exception as e:
        if log:
            logger.error("ERRO em criar_gigs: %s: %s", type(e).__name__, e)
        return False


# =============================================================================
# EXTRACAO DE DADOS DO PROCESSO
# =============================================================================


def extrair_dados_processo(driver, caminho_json=None, debug=False):
    """
    Extrai dados do processo via API do PJe (TRT2), seguindo a mesma logica da extensao MaisPje.
    Salva os dados em Andrei/dadosatuais.json por padrao.
    Retorna dict com dados do processo ou {} em caso de erro.
    """
    if caminho_json is None:
        caminho_json = _DADOSATUAIS_PATH

    # --- funcoes auxiliares internas ---

    def get_cookies_dict(drv):
        try:
            cookies = drv.get_cookies()
            return {c['name']: c['value'] for c in cookies}
        except Exception as e:
            logger.error("ERRO em get_cookies_dict: %s: %s", type(e).__name__, e)
            return {}

    def extrair_numero_processo_url(drv):
        """Extrai numero do processo da URL ou do elemento clipboard"""
        url = drv.current_url
        m = re.search(r'processo/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', url)
        if m:
            return m.group(1)

        try:
            xpath_clipboard = "//pje-icone-clipboard//span[contains(@aria-label, 'Copia o numero do processo')]"
            elemento_clipboard = drv.find_element(By.XPATH, xpath_clipboard)
            aria_label = elemento_clipboard.get_attribute("aria-label")
            if aria_label:
                match_clipboard = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
                if match_clipboard:
                    return match_clipboard.group(1)
        except Exception:
            pass

        return None

    def extrair_trt_host(drv):
        url = drv.current_url
        parsed = urlparse(url)
        return parsed.netloc

    def obter_id_processo_via_api(numero_processo, sess, trt_host):
        """Replica a funcao obterIdProcessoViaApi do gigs-plugin.js"""
        url = f'https://{trt_host}/pje-comum-api/api/agrupamentotarefas/processos?numero={numero_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0].get('idProcesso')
        except Exception as e:
            if debug:
                logger.debug('[extrair.py] Erro ao obter ID via API: %s', e)
        return None

    def obter_dados_processo_via_api(id_processo, sess, trt_host):
        """Replica a funcao obterDadosProcessoViaApi do gigs-plugin.js"""
        url = f'https://{trt_host}/pje-comum-api/api/processos/id/{id_processo}'
        try:
            resp = sess.get(url, timeout=10)
            if resp.ok:
                return resp.json()
        except Exception as e:
            if debug:
                logger.debug('[extrair.py] Erro ao obter dados via API: %s', e)
        return None

    # --- fluxo principal ---

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
            logger.debug('[extrair.py] Nao foi possivel extrair o numero do processo')
        return {}

    id_processo = obter_id_processo_via_api(numero_processo, sess, trt_host)
    if not id_processo:
        if debug:
            logger.debug('[extrair.py] Nao foi possivel obter o ID do processo via API')
        return {}

    dados_processo = obter_dados_processo_via_api(id_processo, sess, trt_host)
    if not dados_processo:
        if debug:
            logger.debug('[extrair.py] Nao foi possivel obter dados do processo via API')
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

    # Extrai data de autuacao
    dt = dados_processo.get("autuadoEm")
    if dt:
        try:
            dtobj = datetime.datetime.fromisoformat(dt.replace('Z', '+00:00'))
            processo_memoria["dtAutuacao"] = dtobj.strftime('%d/%m/%Y')
        except Exception:
            processo_memoria["dtAutuacao"] = dt

    def criar_pessoa_limpa(parte):
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

    # Busca partes via API
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
            logger.debug('[extrair.py] Erro ao buscar partes: %s', e)

    # Busca divida via API
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
            logger.debug('[extrair.py] Erro ao buscar divida: %s', e)

    # Salva JSON
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(processo_memoria, f, ensure_ascii=False, indent=2)

    logger.debug("[extrair_dados_processo] dadosatuais.json salvo (numero=%s)", processo_memoria.get('numero'))
    return processo_memoria


# =============================================================================
# BNDT (Banco Nacional de Devedores Trabalhistas)
# =============================================================================


def bndt(driver, inclusao=False, debug=False, **kwargs):
    """
    Executa rotinas BNDT - versao refatorada processando ambos os polos.
    Orquestrador principal que coordena as etapas.

    Args:
        driver: WebDriver do Selenium
        inclusao: True para inclusao, False para exclusao
        debug: Log detalhado
        **kwargs: Compatibilidade com chamadas que possam passar parametros extras
    """
    try:
        logger.info('BNDT: parametro inclusao recebido: %r (tipo: %s)', inclusao, type(inclusao))
    except Exception:
        pass
    operacao = "Inclusao" if inclusao else "Exclusao"
    logger.info('Iniciando operacao BNDT: %s', operacao)

    main_window = driver.current_window_handle
    nova_aba = None
    erro_classe = False

    try:
        # Etapa 1: Validar localizacao
        _bndt_validar_localizacao(driver)

        # Etapa 2: Abrir menu e icone
        _bndt_abrir_menu(driver)
        _bndt_clicar_icone(driver)

        # Etapa 3: Abrir nova aba
        main_window, nova_aba = _bndt_abrir_nova_aba(driver)

        # Processar apenas polo passivo
        polo = 'Passivo'
        logger.info('============ Processando Polo %s ============', polo)

        logger.info('Procurando botao de polo %s...', polo)
        try:
            btn_polo = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f"//input[@value='{polo}']/ancestor::mat-radio-button | "
                    f"//mat-radio-button[@value='{polo}']"
                ))
            )
            btn_polo.click()
            logger.info('Polo %s selecionado', polo)
            time.sleep(0.5)
        except Exception as e:
            logger.error('Erro ao selecionar polo %s: %s', polo, e)
            raise

        # Selecionar operacao (Inclusao ou Exclusao)
        if not _bndt_selecionar_operacao_para_polo(driver, inclusao, polo):
            driver.close()
            driver.switch_to.window(main_window)
            return False

        # Verificar se ha mensagem "Nao existem partes a serem selecionadas"
        try:
            no_reg_elems = driver.find_elements(
                By.CSS_SELECTOR,
                '#tabela-registros-bndt div[class*="mensagem"], '
                'pje-bndt-partes-sem-registro .mensagem, '
                'mat-card .mensagem, div.mensagem.ng-star-inserted'
            )
            for elem in no_reg_elems:
                texto_no_reg = (elem.text or '').strip().lower()
                if ('nao ha registros' in texto_no_reg or
                        'nao ha registros disponiveis' in texto_no_reg or
                        'nao existem partes a serem selecionadas' in texto_no_reg):
                    logger.info('Polo %s: "%s" -- nada a fazer', polo, elem.text)
                    driver.close()
                    driver.switch_to.window(main_window)
                    return True
        except Exception:
            pass

        # Verificar se ha mensagem de classe nao permitida
        try:
            msg_classe_elems = driver.find_elements(
                By.XPATH,
                "//*[contains(text(),'A classe judicial do processo nao pode acessar')]"
            )
            if msg_classe_elems:
                logger.warning(
                    'Polo %s: Classe judicial do processo nao permite cadastro no BNDT', polo
                )
                erro_classe = True
                driver.close()
                driver.switch_to.window(main_window)
                return False
        except Exception:
            pass

        # Processar selecoes (marcar checkboxes)
        _bndt_processar_selecoes_polo(driver, polo)

        # Gravar e confirmar
        _bndt_gravar_e_confirmar_polo(driver, polo)

        logger.info('============ Finalizando operacao %s ============', operacao)

        if erro_classe:
            logger.warning('ATENCAO: Classe do processo nao suporta BNDT!')

        # Fechar aba BNDT
        driver.close()
        driver.switch_to.window(main_window)
        logger.info('Operacao %s concluida no polo %s', operacao, polo)
        return True

    except Exception as e:
        logger.error('ERRO na operacao %s: %s', operacao, e)
        # Fechar apenas a aba BNDT (se aberta) para nao encerrar o driver principal
        if nova_aba and nova_aba in driver.window_handles:
            try:
                driver.switch_to.window(nova_aba)
                driver.close()
            except Exception:
                pass

        # Garantir retorno para a aba principal original
        if main_window and main_window in driver.window_handles:
            try:
                driver.switch_to.window(main_window)
            except Exception:
                pass
        return False


# =============================================================================
# FUNCOES AUXILIARES BNDT
# =============================================================================


def _bndt_validar_localizacao(driver):
    """Valida se esta em /detalhe."""
    current_url = driver.current_url
    if '/detalhe' not in current_url:
        raise Exception(
            f'bndt deve ser executado a partir de /detalhe. URL atual: {current_url}'
        )
    logger.info('Confirmado: Estamos na pagina /detalhe')
    return True


def _bndt_abrir_menu(driver: WebDriver) -> bool:
    """Abre o menu hamburguer com validacao robusta."""
    try:
        btn_menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fa-bars.icone-botao-menu'))
        )
        btn_menu.click()
        logger.info('Menu hamburguer clicado')
        time.sleep(0.2)
        return True
    except TimeoutException:
        logger.error('Menu hamburguer nao encontrado')
        return False
    except Exception as e:
        logger.error('Erro ao abrir menu: %s', e)
        return False


def _bndt_clicar_icone(driver: WebDriver) -> bool:
    """Clica no icone BNDT com validacao robusta."""
    try:
        btn_bndt = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.fas.fa-money-check-alt.icone-padrao'))
        )
        btn_bndt.click()
        logger.info('Icone BNDT clicado')
        time.sleep(0.3)
        return True
    except TimeoutException:
        logger.error('Icone BNDT nao encontrado')
        return False
    except Exception as e:
        logger.error('Erro ao clicar icone BNDT: %s', e)
        return False


def _bndt_abrir_nova_aba(driver):
    """Abre nova aba BNDT e retorna seu handle."""
    main_window = driver.current_window_handle
    WebDriverWait(driver, 15).until(lambda d: len(d.window_handles) > 1)

    all_windows = driver.window_handles
    nova_aba = [w for w in all_windows if w != main_window]
    if not nova_aba:
        raise Exception('Nova aba BNDT nao foi criada')

    nova_aba = nova_aba[-1]
    driver.switch_to.window(nova_aba)
    WebDriverWait(driver, 15).until(lambda d: '/bndt' in d.current_url)

    time.sleep(0.5)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-card, mat-radio-group, button'))
        )
        logger.info('Elementos da pagina BNDT detectados')
    except Exception as e:
        logger.warning('AVISO: Elementos podem nao ter carregado: %s', e)

    logger.info('Nova aba BNDT aberta: %s', driver.current_url)
    return main_window, nova_aba


def _bndt_selecionar_operacao_para_polo(driver, inclusao, polo):
    """Seleciona Inclusao ou Exclusao para um polo especifico."""
    operacao = "Inclusao" if inclusao else "Exclusao"
    tipo_operacao = "INCLUSAO" if inclusao else "EXCLUSAO"

    logger.info('Selecionando operacao: %s para polo %s', operacao, polo)

    try:
        btn_operacao = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((
                By.XPATH,
                f"//input[@value='{tipo_operacao}']/ancestor::mat-radio-button | "
                f"//mat-radio-button[@value='{tipo_operacao}']"
            ))
        )
        btn_operacao.click()
        logger.info('Operacao %s selecionada para polo %s', operacao, polo)
        time.sleep(0.5)
        return True
    except Exception as e:
        logger.warning('Erro ao selecionar operacao %s no polo %s: %s', operacao, polo, e)
        return False


def _bndt_processar_selecoes_polo(driver, polo):
    """Procurar e clicar em todos os checkboxes de debito/credito para um polo especifico."""
    logger.info('Procurando checkboxes para marcar no polo %s...', polo)
    try:
        labels = driver.find_elements(
            By.CSS_SELECTOR,
            'pje-bndt-exclusao label[for*="debito"][for*="-input"], '
            'pje-bndt-inclusao label[for*="debito"][for*="-input"]'
        )
        if not labels:
            logger.warning('Nenhum checkbox encontrado no polo %s', polo)
            return

        for label in labels:
            try:
                label.click()
                time.sleep(0.1)
            except Exception as e:
                logger.warning('Erro ao clicar checkbox: %s', e)

        logger.info('%s checkbox(es) marcados no polo %s', len(labels), polo)
        time.sleep(0.5)
    except Exception as e:
        logger.warning('Erro ao marcar checkboxes no polo %s: %s', polo, e)


def _bndt_gravar_e_confirmar_polo(driver, polo):
    """Clica Gravar e confirma para um polo especifico."""
    logger.info('Procurando botao Gravar para polo %s...', polo)
    btn_gravar = None
    selectors_gravar = [
        (By.XPATH, "//button[.//span[contains(text(),'Gravar')]]"),
        (By.XPATH, "//button[contains(@class,'mat-raised-button')][contains(text(),'Gravar')]"),
        (By.XPATH, "//pje-bndt-exclusao//button[contains(text(),'Gravar')] | //pje-bndt-inclusao//button[contains(text(),'Gravar')]")
    ]
    for by, selector in selectors_gravar:
        try:
            btn_gravar = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, selector)))
            logger.info('Botao Gravar encontrado')
            break
        except Exception:
            continue

    if not btn_gravar:
        logger.warning('Botao Gravar nao encontrado no polo %s', polo)
        return

    try:
        btn_gravar.click()
        logger.info('Botao Gravar clicado')
        time.sleep(0.5)
    except Exception as e:
        logger.warning('Erro ao clicar no botao Gravar: %s', e)
        return

    # Confirmar acao (botao Sim)
    try:
        btn_sim = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//div[contains(@class,'cdk-overlay-pane')]//button[contains(.,'Sim')]"
            ))
        )
        btn_sim.click()
        logger.info('Confirmacao "Sim" clicada')
        time.sleep(0.5)
    except Exception:
        logger.warning('Botao "Sim" nao encontrado (pode nao ser necessario)')

    # Aguardar desaparecer loading
    try:
        WebDriverWait(driver, 10).until_not(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                'div[class*="container-loading"] mat-progress-spinner'
            ))
        )
        time.sleep(0.5)
    except Exception:
        pass

    # Verificar mensagem de sucesso ou erro
    try:
        aviso = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'simple-snack-bar'))
        )
        if aviso:
            texto_aviso = aviso.text
            logger.info('Aviso: %s', texto_aviso)

            if ('Excluido registro de' in texto_aviso or
                    'Partes excluidas' in texto_aviso or
                    'Incluido registro de' in texto_aviso or
                    'Partes incluídas' in texto_aviso):
                logger.info('Operacao no polo %s concluida com sucesso', polo)
                try:
                    btn_close = aviso.find_element(By.CSS_SELECTOR, 'button')
                    btn_close.click()
                except Exception:
                    pass
            elif 'A classe judicial do processo nao pode acessar' in texto_aviso:
                logger.warning('Classe judicial nao permite BNDT')
            else:
                logger.warning('Mensagem inesperada: %s', texto_aviso)
    except Exception:
        logger.warning('Nenhum aviso detectado')


# =============================================================================
# FUNCOES UTILITARIAS
# =============================================================================


def normalizar_cpf_cnpj(documento: Union[str, int, None]) -> str:
    """
    Remove pontuacao de CPF/CNPJ, mantendo apenas numeros.
    """
    if not documento:
        return ""
    documento_limpo = re.sub(r'\D', '', str(documento))
    return documento_limpo


def formatar_moeda_brasileira(valor: Union[float, int, str]) -> str:
    """
    Formata valor numerico para moeda brasileira (R$ xxxxx,yy).
    """
    try:
        if isinstance(valor, str):
            valor_limpo = re.sub(r'[^\d,.]', '', valor)
            if ',' in valor_limpo and '.' in valor_limpo:
                if valor_limpo.rfind(',') > valor_limpo.rfind('.'):
                    valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
                else:
                    valor_limpo = valor_limpo.replace(',', '')
            elif ',' in valor_limpo:
                valor_limpo = valor_limpo.replace(',', '.')
            valor = float(valor_limpo)

        if valor == 0:
            return "R$ 0,00"

        valor_formatado = f"{valor:,.2f}"
        valor_formatado = valor_formatado.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
        return f"R$ {valor_formatado}"

    except (ValueError, TypeError):
        return "R$ 0,00"


def formatar_data_brasileira(data_str: Optional[str]) -> str:
    """
    Formata data para padrao brasileiro (dd/mm/yyyy).
    """
    try:
        if not data_str:
            return ""
        if re.match(r'\d{2}/\d{2}/\d{4}', data_str):
            return data_str
        data_limpa = data_str.split('T')[0].split(' ')[0]
        formatos = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%Y.%m.%d',
            '%d.%m.%Y'
        ]
        for formato in formatos:
            try:
                data_obj = datetime.datetime.strptime(data_limpa, formato)
                return data_obj.strftime('%d/%m/%Y')
            except ValueError:
                continue
        return data_str
    except Exception:
        return data_str
