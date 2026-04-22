"""
Fix.extracao_documento - Extração direta de documentos PJe.
Suporta HTML e PDF via object.conteudo-pdf — sem scroll, headless-safe.
"""

import re
import logging
from typing import Optional, Dict, Any, List

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

from Fix.utils_observer import aguardar_renderizacao_nativa

import sys
if 'Fix.log' in sys.modules:
    try:
        from Fix.log import logger
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
    from core.resultado_execucao import ResultadoExecucao
    try:
        if not aguardar_renderizacao_nativa(driver, "object.conteudo-pdf", 'aparecer', timeout):
            raise TimeoutError('object.conteudo-pdf não apareceu')
    except Exception:
        if debug:
            logger.info('[EXTRACAO_OBJ] object.conteudo-pdf não presente')
        return ResultadoExecucao(sucesso=False, status='FALHA', erro='object_not_found', detalhes={'tipo': None, 'texto': None}).to_dict()

    try:
        # execute_async_script espera que o JS invoque o callback
        resultado = driver.execute_async_script(_JS_EXTRAIR_OBJECT)
        if not resultado:
            return ResultadoExecucao(sucesso=False, status='FALHA', detalhes={'tipo': None, 'texto': None}).to_dict()
        return resultado
    except Exception as e:
        if debug:
            logger.exception(f'[EXTRACAO_OBJ] erro exec js: {e}')
        return ResultadoExecucao(sucesso=False, status='FALHA', erro=str(e), detalhes={'tipo': None, 'texto': None}).to_dict()


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


        # removed nested compat shims to avoid duplicates; top-level shims provided below

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
        # trecho legado removido — lógica de export/modal e blocos órfãos eliminados


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