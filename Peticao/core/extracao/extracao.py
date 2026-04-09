"""
Peticao.extracao - Extração direta de documentos PJe.
Suporta HTML e PDF via object.conteudo-pdf — sem scroll, headless-safe.
"""

import re
import logging
from typing import Optional, Dict, Any, List, Union

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from ..utils.observer import aguardar_renderizacao_nativa

import sys
if 'Peticao.core.log' in sys.modules:
    try:
        from ..log import getmodulelogger
        logger = getmodulelogger(__name__)
    except Exception:
        import logging
        logger = logging.getLogger(__name__)
else:
    import logging
    logger = logging.getLogger(__name__)


# JavaScript que detecta se o object.conteudo-pdf contém viewer PDF.js ou HTML
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


def _extrair_objeto_pje(driver: WebDriver, timeout: int = 8, debug: bool = False) -> Dict[str, Optional[str]]:
    try:
        if not aguardar_renderizacao_nativa(driver, "object.conteudo-pdf", 'aparecer', timeout):
            raise TimeoutError('object.conteudo-pdf não apareceu')
    except Exception:
        if debug:
            logger.info('[EXTRACAO_OBJ] object.conteudo-pdf não presente')
        return {'sucesso': False, 'status': 'FALHA', 'detalhes': {'tipo': None, 'texto': None}}

    try:
        # execute_async_script espera que o JS invoque o callback
        resultado = driver.execute_async_script(_JS_EXTRAIR_OBJECT)
        if not resultado:
            return {'sucesso': False, 'status': 'FALHA', 'detalhes': {'tipo': None, 'texto': None}}
        return resultado
    except Exception as e:
        if debug:
            logger.exception(f'[EXTRACAO_OBJ] erro exec js: {e}')
        return {'sucesso': False, 'status': 'FALHA', 'erro': str(e), 'detalhes': {'tipo': None, 'texto': None}}


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
        if len(l) < 100 and (l.isupper() or any(k in up for k in ['DECISÃO','DESPACHO','SENTENÇA','CONCLUSÃO','VISTOS'])):
            out.append(f"\n=== {l} ===\n")
            continue
        if re.match(r'^(DEFIRO|INDEFIRO|DETERMINO|HOMOLOGO)\b', up):
            out.append(f"\n>>> {l}")
            continue
        if any(p in l for p in ['Servidor Responsável','Juiz','Magistrado','Responsável']):
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
                    # flush table
                    max_cols = max(len(r) for r in table_block)
                    widths = [0]*max_cols
                    for r in table_block:
                        for i,cell in enumerate(r):
                            widths[i] = max(widths[i], len(cell))
                    out_lines.append('\n=== TABELA ===\n')
                    for r in table_block:
                        row = '  '.join((r[i].ljust(widths[i]) if i < len(r) else ''.ljust(widths[i]) ) for i in range(max_cols))
                        out_lines.append(row)
                    table_block = []
                    in_table = False
                # detect totals
                if re.search(r'\b(Total|Subtotal|Líquido|Bruto)\b', l, flags=re.IGNORECASE):
                    out_lines.append(f"** {l} **")
                else:
                    out_lines.append(l)
        if in_table and table_block:
            max_cols = max(len(r) for r in table_block)
            widths = [0]*max_cols
            for r in table_block:
                for i,cell in enumerate(r):
                    widths[i] = max(widths[i], len(cell))
            out_lines.append('\n=== TABELA ===\n')
            for r in table_block:
                row = '  '.join((r[i].ljust(widths[i]) if i < len(r) else ''.ljust(widths[i]) ) for i in range(max_cols))
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
            m = re.search(r'Id\s+(\w+)', info.get('titulo',''))
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
            logger.exception(f'[EXTRAIR_DIRETO] erro: {e}')
        resultado['sucesso'] = False
        resultado['info'] = _extrair_info_documento(driver, debug=debug)
        return resultado


def extrair_documento(driver: WebDriver, regras_analise=None, timeout: int = 15, log: bool = False) -> Optional[str]:
    """Compat shim: manter assinatura antiga `extrair_documento`.
    Retorna o texto formatado (str) ou None se falhar.
    """
    res = extrair_direto(driver, timeout=timeout, debug=log, formatar=True)
    if not res or not res.get('sucesso'):
        return None
    return res.get('conteudo')


def _extrair_formatar_texto(texto_bruto: str, debug: bool = False) -> str:
    """Compat shim: manter nome antigo esperado por outros módulos."""
    tipo = 'pdf' if isinstance(texto_bruto, str) and '--- PÁGINA ---' in texto_bruto else 'html'
    try:
        return _formatar_texto(texto_bruto, tipo)
    except Exception:
        if debug:
            logger.exception('[_extrair_formatar_texto] erro')
        return texto_bruto or ''


def extrair_pdf(driver: WebDriver, timeout: int = 15, debug: bool = False, log: bool = False) -> Optional[str]:
    """Compat shim: extrai especificamente PDF (retorna texto formatado).
    Aceita o parâmetro legado `log` para compatibilidade (mapeado para `debug`)."""
    # aceitar ambos: `debug` ou legado `log` (priorizar `debug` se True)
    debug = debug or log
    res = extrair_direto(driver, timeout=timeout, debug=debug, formatar=True)
    if not res or not res.get('sucesso'):
        return None
    if res.get('tipo_doc') != 'pdf':
        return None
    return res.get('conteudo')


def criar_gigs(driver: WebDriver, dias: str, resposta: str, observacao: str) -> bool:
    """
    Função para criar GIGS - Guia de Informações Gerenciais Simplificada.
    Esta é uma implementação simplificada que pode ser expandida conforme necessário.
    """
    try:
        # Esta função seria implementada com base nas necessidades específicas do módulo Peticao
        logger.info(f"[GIGS] Criando GIGS: Dias={dias}, Resposta='{resposta}', Obs='{observacao}'")

        # Aqui iria a implementação específica para criar GIGS no contexto do módulo Peticao
        # Por enquanto, apenas simulando o comportamento

        return True  # Indicando sucesso
    except Exception as e:
        logger.error(f"[GIGS] Erro ao criar GIGS: {e}")
        return False


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
        import re
        from urllib.parse import urlparse

        url = driver.current_url
        m = re.search(r'processo/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', url)
        if m:
            return m.group(1)

        try:
            from selenium.webdriver.common.by import By
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
        from urllib.parse import urlparse
        url = driver.current_url
        parsed = urlparse(url)
        return parsed.netloc

    def obter_id_processo_via_api(numero_processo: str, sess, trt_host: str) -> Optional[int]:
        import requests
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

    def obter_dados_processo_via_api(id_processo: int, sess, trt_host: str) -> Optional[Dict[str, Any]]:
        import requests
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

    import requests
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

    import json
    from pathlib import Path
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(processo_memoria, f, ensure_ascii=False, indent=2)

    # Confirmação de gravação (útil para debug e paridade com o legado)
    try:
        logger.info(f"[extrair_dados_processo] dadosatuais.json salvo (numero={processo_memoria.get('numero')})")
    except Exception:
        pass

    return processo_memoria


def normalizar_cpf_cnpj(documento: Union[str, int, None]) -> str:
    """
    Remove pontuação de CPF/CNPJ, mantendo apenas números
    """
    if not documento:
        return ""

    # Remove todos os caracteres não numéricos
    import re
    documento_limpo = re.sub(r'\D', '', str(documento))
    return documento_limpo


def formatar_moeda_brasileira(valor: Union[float, int, str]) -> str:
    """
    Formata valor numérico para moeda brasileira (R$ xxxxx,yy)
    """
    try:
        if isinstance(valor, str):
            # Remove caracteres não numéricos, exceto vírgulas e pontos
            valor_limpo = re.sub(r'[^\d,.]', '', valor)

            # Converte para float
            if ',' in valor_limpo and '.' in valor_limpo:
                # Formato 1.234.567,89 ou 1,234,567.89
                if valor_limpo.rfind(',') > valor_limpo.rfind('.'):
                    # Último separador é vírgula (formato brasileiro)
                    valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
                else:
                    # Último separador é ponto (formato internacional)
                    valor_limpo = valor_limpo.replace(',', '')
            elif ',' in valor_limpo:
                # Apenas vírgula como separador decimal
                valor_limpo = valor_limpo.replace(',', '.')

            valor = float(valor_limpo)

        if valor == 0:
            return "R$ 0,00"

        # Formata com separador de milhares e duas casas decimais
        valor_formatado = f"{valor:,.2f}"

        # Substitui separadores para formato brasileiro
        valor_formatado = valor_formatado.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')

        return f"R$ {valor_formatado}"

    except (ValueError, TypeError):
        return "R$ 0,00"


def formatar_data_brasileira(data_str: Optional[str]) -> str:
    """
    Formata data para padrão brasileiro (dd/mm/yyyy)
    """
    try:
        if not data_str:
            return ""

        # Se já está no formato brasileiro, retorna como está
        if re.match(r'\d{2}/\d{2}/\d{4}', data_str):
            return data_str

        # Remove horário se presente
        data_limpa = data_str.split('T')[0].split(' ')[0]

        # Tenta diferentes formatos de entrada
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
                from datetime import datetime
                data_obj = datetime.strptime(data_limpa, formato)
                return data_obj.strftime('%d/%m/%Y')
            except ValueError:
                continue

        # Se não conseguiu formatar, retorna string original
        return data_str

    except Exception:
        return data_str