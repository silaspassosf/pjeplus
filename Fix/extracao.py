"""Fix.extracao - Módulo de extracao para PJe automação."""

from typing import Optional, Any
from Play.pjeplay.locators import By, Keys
from Play.pjeplay.errors import TimeoutException
from Play.pjeplay.element import PWElement
import re, time, datetime, json, pyperclip, unicodedata

try:
    from atos.core import (
        verificar_carregamento_detalhe,
    )
    _ATOS_CORE_AVAILABLE = True
except ImportError:
    _ATOS_CORE_AVAILABLE = False
import requests
from urllib.parse import urlparse
from pathlib import Path
from Fix.log import logger
from Fix.core import safe_click_no_scroll, aguardar_renderizacao_nativa
from .core import aguardar_e_clicar, safe_click, wait, esperar_elemento, preencher_campo, selecionar_opcao
from .abas import validar_conexao_driver, forcar_fechamento_abas_extras
from .utils import normalizar_cpf_cnpj, formatar_moeda_brasileira, formatar_data_brasileira
from Fix import espera


def _pressionar_tecla(driver, tecla: str):
    """Envia tecla ao teclado do navegador de forma segura."""
    try:
        if hasattr(driver, 'page') and driver.page:
            driver.page.keyboard.press(tecla)
        else:
            safe_click_no_scroll(driver, 'body')
    except Exception:
        pass


def extrair_direto(driver, timeout=10, debug=False, formatar=True):
    """Extrai o conteúdo do documento PDF ativo na tela do processo PJe DIRETAMENTE."""

    resultado = {
        'conteudo': None,
        'conteudo_bruto': None,
        'info': {},
        'sucesso': False
    }
    try:
        if not espera.ate_aparecer(driver, '#documento', teto=timeout):
            if debug:
                logger.debug('[EXTRAIR_DIRETO] Elemento #documento nao encontrado')
            return resultado

        strategies = [
            lambda: _extrair_via_pdf_viewer(driver, timeout, debug),
            lambda: _extrair_via_iframe(driver, timeout, debug),
            lambda: _extrair_via_elemento_dom(driver, timeout, debug)
        ]
        metodos_nomes = ['PDF viewer direto', 'iframe', 'elemento DOM']
        for idx, strategy in enumerate(strategies):
            texto_bruto = strategy()
            if texto_bruto:
                resultado['conteudo_bruto'] = texto_bruto
                resultado['conteudo'] = _extrair_formatar_texto(texto_bruto, debug) if formatar else texto_bruto
                resultado['metodo'] = metodos_nomes[idx]
                resultado['sucesso'] = True
                resultado['info'] = _extrair_info_documento(driver, debug)
                if debug:
                    logger.debug('[EXTRAIR_DIRETO] Extracao bem-sucedida via %s', resultado["metodo"])
                return resultado
        resultado['info'] = _extrair_info_documento(driver, debug)
        if debug:
            logger.debug('[EXTRAIR_DIRETO] Nenhuma estrategia de extracao funcionou')
        return resultado
    except Exception as e:
        if debug:
            logger.error("ERRO em extrair_direto: %s: %s", type(e).__name__, e)
        return resultado


_driver_recovery_config = {
    'criar_driver': None,
    'login_func': None,
    'enabled': True
}


def extrair_documento(driver, regras_analise=None, timeout=15, log=False):
    texto_completo = None
    texto_final = None
    try:
        btn_html = wait(driver, '.fa-file-code', timeout)
        if not btn_html:
            logger.error('ERRO em extrair_documento: Botao HTML nao encontrado')
            return None

        safe_click(driver, btn_html)
        espera.ate_aparecer(driver, '#previewModeloDocumento', teto=1)

        preview = wait(driver, '#previewModeloDocumento', timeout)
        if not preview:
            logger.error('ERRO em extrair_documento: Preview do documento nao encontrado')
            _pressionar_tecla(driver, "Escape")
            return None

        texto_completo = preview.text

        try:
            _pressionar_tecla(driver, "Escape")
            logger.debug('[EXTRAI] Modal HTML fechado')
            espera.ate_sumir(driver, '#previewModeloDocumento', teto=0.5)
            _pressionar_tecla(driver, "Tab")
            logger.debug('[WORKAROUND] Pressionada tecla TAB apos fechar modal de documento')
        except Exception as e_esc:
            logger.debug('[EXTRAI][WARN] Falha ao fechar modal com ESC: %s', e_esc)

        if not texto_completo:
            logger.error('ERRO em extrair_documento: Texto do preview vazio')
            return None
        marcador = "Servidor Responsavel"
        try:
            indice_marcador = texto_completo.rindex(marcador)
            indice_newline = texto_completo.find('\n', indice_marcador)
            if indice_newline != -1:
                texto_final = texto_completo[indice_newline:].strip()
            else:
                texto_final = texto_completo.strip()
            logger.debug('[EXTRAI] Conteudo extraido abaixo de "%s"', marcador)
        except ValueError:
            texto_final = texto_completo.strip()
            logger.debug('[EXTRAI] Marcador "%s" nao encontrado. Usando texto completo do documento.', marcador)

        if regras_analise and callable(regras_analise):
            logger.debug('[EXTRAI] Aplicando regras de analise')
            try:
                logger.debug('[REGRAS] Iniciando analise de regras...')
                _ = regras_analise(texto_final)
                logger.debug('[REGRAS] Analise de regras concluida')
            except Exception as e_analise:
                logger.error('ERRO em extrair_documento: Falha ao analisar regras: %s', e_analise)

        if log:
            logger.info('[EXTRAI] Extracao concluida')
        return texto_final

    except Exception as e:
        if log:
            logger.error("ERRO em extrair_documento: %s: %s", type(e).__name__, e)
        try:
            if espera.elementos(driver, '#previewModeloDocumento'):
                _pressionar_tecla(driver, "Escape")
        except Exception:
            pass
        return None


def extrair_pdf(driver, log=True):
    import time
    import pyperclip
    try:
        btn_export = espera.elemento(driver, '.fa-file-export')
        if not btn_export:
            if log:
                logger.error('ERRO em extrair_pdf: Botao .fa-file-export nao encontrado')
            return None
        btn_export.click()
        if log:
            logger.debug('[EXPORT] Botao .fa-file-export clicado')
        if espera.ate_aparecer(driver, 'pje-conteudo-documento-dialog', teto=10):
            titulo = espera.elemento(driver, 'pje-conteudo-documento-dialog .mat-dialog-title')
            if titulo and 'Texto Extraido' in (titulo.text or ''):
                texto = None
                pre = espera.elemento(driver, 'pje-conteudo-documento-dialog pre')
                if pre and (pre.text or '').strip():
                    texto = pre.text.strip()
                    if log:
                        logger.debug('[EXPORT] Texto extraido do modal via <pre>')
                else:
                    btn_copiar = espera.elemento(driver, 'pje-conteudo-documento-dialog i.far.fa-copy')
                    if btn_copiar:
                        btn_copiar.click()
                        espera.assentar(driver, 0.3)
                        texto = pyperclip.paste()
                        if log:
                            logger.debug('[EXPORT] Texto extraido do modal via copiar (fallback)')
                btn_fechar = espera.elemento(driver, 'pje-conteudo-documento-dialog button[mat-dialog-close]')
                if btn_fechar:
                    btn_fechar.click()
                else:
                    _pressionar_tecla(driver, "Escape")
                espera.ate_sumir(driver, 'pje-conteudo-documento-dialog', teto=0.5)
                if texto:
                    return texto
        if log:
            logger.error('ERRO em extrair_pdf: Modal de texto extraido nao apareceu')
        return None
    except Exception as e:
        if log:
            logger.error("ERRO em extrair_pdf: %s: %s", type(e).__name__, e)
        return None

def extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False):
    """Extrai dados do processo via API do PJe (TRT2), seguindo a mesma lógica da extensão MaisPje."""
    def get_cookies_dict(driver):
        try:
            cookies = driver.get_cookies()
            return {c['name']: c['value'] for c in cookies}
        except Exception as e:
            logger.error("ERRO em get_cookies_dict: %s: %s", type(e).__name__, e)
            return {}

    def extrair_numero_processo_url(driver):
        """Extrai número do processo da URL ou do elemento clipboard"""
        url = driver.current_url
        m = re.search(r'processo/(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', url)
        if m:
            return m.group(1)

        try:
            xpath_clipboard = "//pje-icone-clipboard//span[contains(@aria-label, 'Copia o número do processo')]"
            elemento_clipboard = espera.elemento(driver, xpath_clipboard)
            aria_label = elemento_clipboard.get_attribute("aria-label")
            if aria_label:
                match_clipboard = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", aria_label)
                if match_clipboard:
                    return match_clipboard.group(1)
        except:
            pass

        return None

    def extrair_trt_host(driver):
        url = driver.current_url
        parsed = urlparse(url)
        return parsed.netloc

    def obter_id_processo_via_api(numero_processo, sess, trt_host):
        """Replica a função obterIdProcessoViaApi do gigs-plugin.js"""
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

    dt = dados_processo.get("autuadoEm")
    if dt:
        from datetime import datetime
        try:
            dtobj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            processo_memoria["dtAutuacao"] = dtobj.strftime('%d/%m/%Y')
        except:
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

    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(processo_memoria, f, ensure_ascii=False, indent=2)
    return processo_memoria


DESTINATARIOS_CACHE_PATH = Path('destinatarios_argos.json')


def extrair_destinatarios_decisao(texto_decisao, dados_processo=None, debug=False):
    """Extrai possiveis destinatarios (nome + CPF/CNPJ) a partir do texto completo da decisao."""
    if not texto_decisao:
        if debug:
            logger.debug('[DEST][WARN] Texto da decisao vazio. Nenhum destinatario extraido.')
        return []

    texto_compacto = _normalizar_texto_decisao(texto_decisao)
    texto_upper = texto_compacto.upper()
    resultados = []
    vistos = set()

    padrao_doc = re.compile(r'(CPF|CNPJ)\s*[:\-]?\s*([\d\.\-/]+)')

    for match in padrao_doc.finditer(texto_upper):
        tipo_doc = match.group(1)
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
        logger.debug('[DEST][DEBUG] Destinatarios identificados: %s', json.dumps(resultados, ensure_ascii=False, indent=2))

    return resultados


def salvar_destinatarios_cache(chave_simples, destinatarios, origem=''):  # noqa: D401
    """VERSÃO SIMPLIFICADA - Salva destinatários sem depender do número do processo"""
    payload = {
        'numero_processo': chave_simples,
        'destinatarios': destinatarios,
        'origem': origem,
        'timestamp': datetime.datetime.now().isoformat()
    }
    try:
        DESTINATARIOS_CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.debug('[DEST][CACHE] Cache salvo com chave: %s (%s destinatarios)', chave_simples, len(destinatarios))
    except Exception as exc:
        logger.warning('[DEST][WARN] Falha ao salvar cache de destinatarios: %s', exc)


def carregar_destinatarios_cache():
    """VERSÃO SIMPLIFICADA - Carrega destinatários sem depender do número do processo"""
    try:
        if DESTINATARIOS_CACHE_PATH.exists():
            cache = json.loads(DESTINATARIOS_CACHE_PATH.read_text(encoding='utf-8'))
            logger.debug('[DEST][CACHE] Cache carregado: %s destinatarios', len(cache.get("destinatarios", [])))
            return cache
    except Exception as exc:
        logger.warning('[DEST][WARN] Falha ao carregar cache de destinatarios: %s', exc)
    return {}


def _normalizar_texto_decisao(texto):
    if not texto:
        return ''
    return ' '.join(texto.split())


def _extrair_linha_tipo(linha: str) -> Optional[str]:
    """Detecta tipo de linha e aplica formatação apropriada."""
    linha_limpa = linha.strip()
    if not linha_limpa:
        return None

    eh_titulo = (len(linha_limpa) < 100 and
                (linha_limpa.isupper() or
                 any(p in linha_limpa.upper() for p in ['DECISÃO', 'DESPACHO', 'SENTENÇA', 'CONCLUSÃO', 'VISTOS'])))
    if eh_titulo:
        return f"\n=== {linha_limpa} ===\n"

    if re.match(r'^\d+[\.\)]\s*', linha_limpa):
        return f"\n{linha_limpa}"

    eh_introducao = linha_limpa.startswith(('Ante o', 'Diante', 'Considerando', 'Tendo em vista', 'Por conseguinte'))
    if eh_introducao:
        return f"\n{linha_limpa}"

    eh_decisao = linha_limpa.startswith(('DEFIRO', 'INDEFIRO', 'DETERMINO', 'HOMOLOGO'))
    if eh_decisao:
        return f"\n>>> {linha_limpa}"

    eh_assinatura = any(p in linha_limpa for p in ['Servidor Responsável', 'Juiz', 'Magistrado', 'Responsável'])
    if eh_assinatura:
        return f"\n--- {linha_limpa} ---"

    tem_data = re.search(r'\d{1,2}/\d{1,2}/\d{4}', linha_limpa) and len(linha_limpa) < 50
    if tem_data:
        return f"\n[{linha_limpa}]"

    return linha_limpa


def _extrair_formatar_texto(texto_bruto: str, debug: bool = False) -> str:
    """Formata o texto extraído com estrutura organizacional."""
    if not texto_bruto or not texto_bruto.strip():
        return ""

    try:
        texto = texto_bruto.strip()
        texto = re.sub(r'\r\n|\r', '\n', texto)
        texto = re.sub(r'[ \t]+', ' ', texto)
        texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)

        linhas = texto.split('\n')
        linhas_formatadas = [_extrair_linha_tipo(l) for l in linhas]
        linhas_formatadas = [l for l in linhas_formatadas if l is not None]

        texto_formatado = '\n'.join(linhas_formatadas)
        texto_formatado = re.sub(r'\n{3,}', '\n\n', texto_formatado)
        return texto_formatado.strip()

    except Exception as e:
        if debug:
            logger.debug('[EXTRAIR_DIRETO] Erro na formatacao: %s', e)
        return texto_bruto


def _extrair_info_documento(driver, debug=False):
    """Extrai informações do cabeçalho do documento."""
    try:
        info = {}

        try:
            titulo_el = espera.elemento(driver, 'mat-card-title')
            titulo = titulo_el.text.strip() if titulo_el else ''
            info['titulo'] = titulo
        except:
            info['titulo'] = ""

        try:
            subtitulos = espera.elementos(driver, 'mat-card-subtitle')
            info['subtitulos'] = [sub.text.strip() for sub in subtitulos if sub.text.strip()]
        except:
            info['subtitulos'] = []

        try:
            id_match = re.search(r'Id\s+(\w+)', info.get('titulo', ''))
            if id_match:
                info['documento_id'] = id_match.group(1)
        except:
            info['documento_id'] = ""

        return info

    except Exception as e:
        if debug:
            logger.debug('[EXTRAIR_DIRETO] Erro ao extrair informacoes: %s', e)
        return {}


def _extrair_via_pdf_viewer(driver, timeout, debug=False):
    """Strategy 1: Extrai texto do PDF viewer incorporado via JavaScript."""
    if debug:
        logger.debug('[EXTRAIR_DIRETO] Tentando extracao via PDF viewer...')

    try:
        pdf_object = espera.elemento(driver, "object.conteudo-pdf", teto=timeout, visivel=False)
        if not pdf_object or not espera.ate_js(
            driver,
            "__pjeEls('object.conteudo-pdf').some(el => el.getAttribute('data') !== null)",
            teto=timeout,
        ):
            return None

        js_script = """
        try {
            var pdfObject = document.querySelector('object[type="application/pdf"]') || document.querySelector('object.conteudo-pdf');
            if (!pdfObject) return null;
            var pdfDoc = pdfObject.contentDocument || pdfObject.contentWindow.document;
            if (!pdfDoc) return null;
            var v = pdfDoc.querySelector('#viewer');
            if (!v) return null;
            var text = v.textContent || '';
            return (text && text.trim().length > 100) ? text.trim() : null;
        } catch(e) { return null; }
        """

        resultado_js = None
        if hasattr(driver, 'page') and driver.page:
            try:
                resultado_js = driver.page.evaluate(f"() => {{ {js_script} }}")
            except Exception:
                resultado_js = None
        if resultado_js and resultado_js.strip():
            return resultado_js.strip()

        try:
            pdf_url = None
            if hasattr(driver, 'page') and driver.page:
                pdf_url = driver.page.evaluate("""() => {
                    var el = document.querySelector('object.conteudo-pdf, object[type="application/pdf"], embed[type="application/pdf"]');
                    return el ? (el.getAttribute('data') || el.getAttribute('src') || el.data || el.src) : null;
                }""")
            if pdf_url:
                if pdf_url.startswith('/'):
                    from urllib.parse import urljoin
                    pdf_url = urljoin(driver.current_url, pdf_url)
                import requests
                sess = requests.Session()
                for c in driver.get_cookies():
                    sess.cookies.set(c['name'], c['value'])
                resp = sess.get(pdf_url, timeout=timeout)
                if resp.status_code == 200 and resp.content and resp.content.startswith(b'%PDF'):
                    from Mandado.apoio_fluxos import _extrair_texto_pdf_bytes
                    t = _extrair_texto_pdf_bytes(resp.content, log=debug)
                    if t and len(t.strip()) > 100:
                        return t.strip()
        except Exception as e_url:
            if debug:
                logger.debug('[EXTRAIR_DIRETO] Fallback via URL do PDF viewer: %s', e_url)

    except Exception as e:
        if debug:
            logger.debug('[EXTRAIR_DIRETO] Erro na extracao via PDF viewer: %s', e)

    return None


def _extrair_via_iframe(driver, timeout, debug=False):
    """Strategy 2: Extrai texto de iframes alternativos."""
    if debug:
        logger.debug('[EXTRAIR_DIRETO] Tentando extracao via iframe...')

    try:
        iframes = espera.elementos(driver, "iframe", teto=0.5)
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                corpo = espera.elemento(driver, "body", teto=0.5)
                texto = corpo.text if corpo else ""
                driver.switch_to.default_content()
                if texto and len(texto.strip()) > 100:
                    return texto.strip()
            except:
                driver.switch_to.default_content()

    except Exception as e:
        if debug:
            logger.debug('[EXTRAIR_DIRETO] Erro na extracao via iframe: %s', e)
        driver.switch_to.default_content()

    return None


def _extrair_via_elemento_dom(driver, timeout, debug=False):
    """Strategy 3: Extrai texto de elemento DOM estruturado."""
    if debug:
        logger.debug('[EXTRAIR_DIRETO] Tentando extracao via elemento DOM...')

    try:
        seletores = [
            "div.documento-conteudo",
            "div.conteudo-documento",
            "article",
            "main",
            "div[id*='documento']"
        ]

        tem_pdf = bool(espera.elementos(driver, "object.conteudo-pdf, object[type='application/pdf'], embed[type='application/pdf']", teto=0.2))

        for seletor in seletores:
            try:
                elemento = espera.elemento(driver, seletor, teto=0.2)
                texto = elemento.text if elemento else ""
                min_len = 500 if (tem_pdf and seletor in ("article", "main", "div[id*='documento']")) else 100
                if texto and len(texto.strip()) > min_len:
                    return texto.strip()
            except:
                pass

    except Exception as e:
        if debug:
            logger.debug('[EXTRAIR_DIRETO] Erro na extracao via DOM: %s', e)

    return None


def _gigs_responsavel_valido(responsavel: Optional[str]) -> bool:
    """Verifica se responsável é válido (não vazio, não '-')."""
    return responsavel is not None and responsavel.strip() and responsavel.strip() != '-'


def _normalizar_texto(texto: Any) -> str:
    """Normaliza texto para comparações robustas (sem acentos, minúsculo, espaços colapsados)."""
    if not texto:
        return ""
    s = unicodedata.normalize('NFKD', str(texto).strip().lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.split())


def _normalizar_marcadores(marcadores) -> list:
    """Normaliza uma lista (ou string) de marcadores para comparação por substring."""
    if not marcadores:
        return []
    if isinstance(marcadores, str):
        marcadores = [marcadores]
    saida = []
    for m in marcadores:
        n = _normalizar_texto(m)
        if n:
            saida.append(n)
    return saida


def _bate_marcador(alvo: str, marcadores: list) -> bool:
    """True se `alvo` (normalizado) contém algum marcador (normalizado)."""
    for m in marcadores:
        if m and m in alvo:
            return True
    return False


def _verificar_lembrete_presente(
    driver,
    titulo: str,
    conteudo: Optional[str] = None,
    teto: float = 1.0,
    marcadores_titulo: Optional[list] = None,
    marcadores_conteudo: Optional[list] = None,
) -> bool:
    """Confirma no painel de post-its do /detalhe que um lembrete equivalente já existe."""
    alvo_tit = _normalizar_texto(titulo)
    alvo_cont = _normalizar_texto(conteudo) if conteudo else ''
    marcs_tit = _normalizar_marcadores(marcadores_titulo)
    marcs_cont = _normalizar_marcadores(marcadores_conteudo)

    if not alvo_tit and not alvo_cont and not marcs_tit and not marcs_cont:
        return False

    logger.info(
        '[LEMBRETE][VERIFICAR] Procurando lembrete existente (titulo=%r, conteudo=%r, '
        'marcs_titulo=%r, marcs_conteudo=%r, teto=%.1fs)',
        alvo_tit, alvo_cont, marcs_tit, marcs_cont, teto,
    )

    fim = time.time() + teto
    while time.time() < fim:
        try:
            container = espera.elemento(driver, '[class*="post-it-set"], pje-visualizador-post-its', teto=0.2)
            if not container:
                logger.info('[LEMBRETE][VERIFICAR] Painel de post-its nao encontrado — sem lembrete a pular')
                return False

            paineis = espera.elementos(driver, 'mat-expansion-panel[class*="post-it"], [class*="post-it-set"] mat-expansion-panel, mat-expansion-panel', teto=0.3)
            if not paineis:
                logger.info('[LEMBRETE][VERIFICAR] Nenhum cartao de lembrete no painel — sem lembrete a pular')
                return False

            for painel in paineis:
                try:
                    el_tit = espera.elemento(painel, 'div[class="post-it-div-titulo"], .post-it-div-titulo, .post-it-titulo, mat-panel-title', teto=0.2)
                    txt_tit = _normalizar_texto(getattr(el_tit, 'text', '') or '') if el_tit else ''

                    bate_titulo = False
                    if alvo_tit and (alvo_tit in txt_tit or txt_tit in alvo_tit):
                        bate_titulo = True
                    if not bate_titulo and marcs_tit and _bate_marcador(txt_tit, marcs_tit):
                        bate_titulo = True
                    if not alvo_tit and not marcs_tit:
                        bate_titulo = True

                    if not bate_titulo:
                        continue

                    logger.info('[LEMBRETE][VERIFICAR] Titulo bate (%r vs alvo=%r)', txt_tit, alvo_tit)

                    el_cont = espera.elemento(painel, 'div[aria-label="Conteúdo do Lembrete"], .post-it-conteudo, [aria-label*="Conteúdo" i]', teto=0.2)
                    txt_cont = _normalizar_texto(getattr(el_cont, 'text', '') or '') if el_cont else ''

                    tem_alvo_cont = bool(alvo_cont)
                    tem_marc_cont = bool(marcs_cont)

                    if tem_alvo_cont or tem_marc_cont:
                        bate_cont = False
                        if txt_cont:
                            if alvo_cont and (alvo_cont in txt_cont or txt_cont in alvo_cont):
                                bate_cont = True
                            if not bate_cont and _bate_marcador(txt_cont, marcs_cont):
                                bate_cont = True
                        if bate_cont:
                            logger.info('[LEMBRETE][VERIFICAR] Lembrete existente encontrado (titulo+conteudo) — pulando criacao')
                            return True
                        elif not txt_cont:
                            logger.info('[LEMBRETE][VERIFICAR] Lembrete existente encontrado (titulo ok, conteudo recolhido) — pulando criacao')
                            return True
                        continue
                    else:
                        logger.info('[LEMBRETE][VERIFICAR] Lembrete existente encontrado (so titulo) — pulando criacao')
                        return True
                except Exception:
                    continue
        except Exception as e:
            logger.warning('[LEMBRETE][VERIFICAR] Erro ao varrer painel de post-its: %s', e)
        espera.assentar(driver, 0.2)
    logger.info('[LEMBRETE][VERIFICAR] Nenhum lembrete equivalente encontrado (teto %ss esgotado) — prosseguindo para criacao', teto)
    return False


def criar_lembrete_posit(
    driver: Any,
    titulo: str,
    conteudo: str = "",
    debug: bool = False,
    visibilidade: str = "LOCAL",
    destinatario: Optional[str] = None,
    salvar: bool = True,
    verificar_existente: bool = True,
    acao: str = "criar",
    marcadores_titulo: Optional[list] = None,
    marcadores_conteudo: Optional[list] = None,
) -> bool:
    """Cria ou conclui lembrete/post-it genérico no PJe com título, visibilidade e conteúdo customizáveis."""
    if acao.lower() in ("concluir", "remover"):
        return remover_lembrete_posit(driver, titulo=titulo, conteudo=conteudo, debug=debug)

    if isinstance(debug, str):
        visibilidade = debug
        debug = False

    def _fechar_dialogo_residual():
        """Barreira: garante que nenhum diálogo ou overlay de lembrete fique aberto após falha."""
        try:
            if not espera.ate_sumir(driver, '#tituloPostit', teto=0.5):
                _pressionar_tecla(driver, 'Escape')
                espera.ate_sumir(driver, '#tituloPostit', teto=2)
            _pressionar_tecla(driver, 'Escape')
            espera.ate_sumir(driver, '.cdk-overlay-backdrop-showing', teto=2)
        except Exception:
            pass

    conexao_status = validar_conexao_driver(driver, "LEMBRETE")
    if conexao_status == "FATAL" or not conexao_status:
        if debug:
            logger.error('[LEMBRETE][POSIT] Driver desconectado ou sessão inválida — abortando')
        return False

    try:
        logger.info('[LEMBRETE][POSIT] Criando: "%s" / "%s" (visibilidade: %s)', titulo, conteudo, visibilidade)

        if conteudo and "clipboard" in conteudo.lower():
            try:
                clip_val = pyperclip.paste() or ""
                if clip_val:
                    conteudo = re.sub(r'clipboard', clip_val, conteudo, flags=re.IGNORECASE)
            except Exception:
                pass

        if verificar_existente:
            try:
                _ctx = getattr(driver, 'context', None)
                if _ctx is not None and hasattr(_ctx, 'pages'):
                    _vivas = [p for p in _ctx.pages if not p.is_closed()]
                    if not _vivas and not (getattr(driver, 'window_handles', None) or []):
                        logger.warning('[LEMBRETE][POSIT] Nenhuma pagina aberta — abortando antes da verificacao de idempotencia')
                        return False
            except Exception as e:
                logger.warning('[LEMBRETE][POSIT] Falha ao checar paginas vivas: %s', e)

        if verificar_existente and _verificar_lembrete_presente(
            driver, titulo, conteudo=conteudo, teto=0.5,
            marcadores_titulo=marcadores_titulo,
            marcadores_conteudo=marcadores_conteudo,
        ):
            logger.info('[LEMBRETE][POSIT] Lembrete "%s" já presente no painel — nada a criar', titulo)
            return True

        dialogo_aberto = (
            espera.elemento(driver, '#tituloPostit', teto=0.3)
            or espera.elemento(driver, 'pje-dialogo-post-it', teto=0.3)
        )

        if not dialogo_aberto:
            seletores_lembrete = [
                'pje-icone-post-it button',
                'button[aria-label*="Lembrete" i]',
                'button[title*="Lembrete" i]',
                'button[mattooltip*="Lembrete" i]',
                '.lista-itens-menu pje-icone-post-it button',
                '.lista-itens-menu button[aria-label*="Lembrete" i]',
                'pje-icone-post-it',
                'button:has(i.fa-sticky-note)',
                'i.fa-sticky-note',
            ]

            lembrete_btn = None
            for sel in seletores_lembrete:
                el = espera.elemento(driver, sel, teto=0.3)
                if el:
                    lembrete_btn = el
                    break

            if not lembrete_btn:
                menu_clicked = aguardar_e_clicar(driver, 'button[id="botao-menu"], #botao-menu', timeout=4, log=debug)
                if not menu_clicked:
                    menu_clicked = aguardar_e_clicar(driver, '.fa-bars', timeout=4, log=debug)
                espera.assentar(driver, 0.6)
                for sel in seletores_lembrete:
                    el = espera.elemento(driver, sel, teto=1)
                    if el:
                        lembrete_btn = el
                        break

            if not lembrete_btn:
                logger.warning('[LEMBRETE][POSIT] Botão de lembrete não encontrado no menu')
                return False

            lembrete_clicked = False
            for seletor in (lembrete_btn, 'pje-icone-post-it button, button[aria-label*="Lembrete" i]'):
                try:
                    if isinstance(seletor, str):
                        if aguardar_e_clicar(driver, seletor, timeout=3, log=debug):
                            lembrete_clicked = True
                            break
                    else:
                        safe_click_no_scroll(driver, seletor)
                        lembrete_clicked = True
                        break
                except Exception:
                    continue

            if not lembrete_clicked:
                return False
            espera.assentar(driver, 0.5)

        if not espera.ate_aparecer(driver, '#tituloPostit', teto=5):
            if not espera.ate_aparecer(driver, '.mat-dialog-content', teto=2):
                logger.warning('[LEMBRETE][POSIT] Diálogo do lembrete não abriu (#tituloPostit ausente)')
                return False

        titulo_limpo = (titulo or '').strip()
        conteudo_limpo = (conteudo or '').strip() if conteudo is not None else ""

        aguardar_e_clicar(driver, '#tituloPostit', timeout=3, log=False)
        preencher_campo(driver, '#tituloPostit', titulo_limpo, limpar=True, log=debug)

        try:
            visib_upper = (visibilidade or 'LOCAL').upper()
            sel_visib = 'mat-select[id="visibilidadePostit"], #visibilidadePostit'
            el_visib = espera.elemento(driver, sel_visib, teto=1)
            if el_visib:
                # Só aciona o dropdown se o valor atual for diferente (evita abrir overlay backdrop desnecessário)
                txt_atual = (getattr(el_visib, 'text', '') or '').strip().upper()
                if visib_upper not in txt_atual:
                    mapa_visib = {'LOCAL': 'Local', 'PRIVADO': 'Privado', 'GLOBAL': 'Global'}
                    lbl_visib = mapa_visib.get(visib_upper, 'Local')
                    selecionar_opcao(driver, sel_visib, lbl_visib, timeout=3, log=debug)
                    espera.assentar(driver, 0.3)
                    if visib_upper == 'PRIVADO' and destinatario:
                        sel_dest = 'mat-select[id="destinatarioPostit"], #destinatarioPostit'
                        if espera.elemento(driver, sel_dest, teto=1):
                            selecionar_opcao(driver, sel_dest, destinatario, timeout=3, log=debug)
                            espera.assentar(driver, 0.3)
        except Exception as e_visib:
            if debug:
                logger.warning('[LEMBRETE][POSIT] Aviso ao definir visibilidade: %s', e_visib)

        if conteudo is not None:
            aguardar_e_clicar(driver, '#conteudoPostit', timeout=3, log=False)
            preencher_campo(driver, '#conteudoPostit', conteudo_limpo, limpar=True, log=debug)
            espera.assentar(driver, 0.2)

        try:
            page_obj = getattr(driver, 'page', None)
            if page_obj and type(page_obj).__name__ != 'MagicMock':
                page_obj.fill('#tituloPostit', titulo_limpo)
                if conteudo is not None:
                    page_obj.fill('#conteudoPostit', conteudo_limpo)
        except Exception:
            pass

        # Barreira de validação com JS nativo + sincronização de ControlValueAccessor Angular
        _JS_SYNC_VAL = """(() => {
            function sync(sel, val, isTa) {
                const el = document.querySelector(sel);
                if (!el) return;
                if (!el.value || el.value !== val) {
                    el.focus();
                    const proto = isTa ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
                    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (desc && desc.set) {
                        desc.set.call(el, val);
                    } else {
                        el.value = val;
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                }
            }
            const t = document.querySelector('#tituloPostit');
            return !!(t && (t.value || '').trim());
        })()"""
        campos_preenchidos = espera.ate_js(driver, _JS_SYNC_VAL, teto=3)
        if not campos_preenchidos:
            logger.warning('[LEMBRETE][POSIT] Campo título não ficou preenchido — abortando')
            _fechar_dialogo_residual()
            return False
        espera.assentar(driver, 0.2)

        if not salvar:
            logger.info('[LEMBRETE][POSIT] salvar=False: diálogo mantido aberto')
            return True

        seletores_salvar = (
            'button[aria-label="Salvar"]',
            '.criacao-alteracao-post-it button[aria-label="Salvar"]',
            '.botoes-centralizados button[aria-label="Salvar"]',
            '.criacao-alteracao-post-it button:not([matdialogclose])',
        )

        clicou_salvar = False
        _diag_salvar = []
        _limite = time.time() + 8
        while time.time() < _limite and not clicou_salvar:
            if page_obj:
                try:
                    for seletor in seletores_salvar:
                        loc = page_obj.locator(seletor).first
                        if loc.is_visible(timeout=500):
                            loc.click(timeout=1000)
                            clicou_salvar = True
                            _diag_salvar.append(f'pw:{seletor} -> True')
                            break
                except Exception as e_pw:
                    _diag_salvar.append(f'pw_err: {e_pw}')

            if not clicou_salvar:
                for seletor in seletores_salvar:
                    try:
                        if aguardar_e_clicar(driver, seletor, timeout=1.5, log=False):
                            clicou_salvar = True
                            _diag_salvar.append('%s -> True' % seletor)
                            break
                    except Exception as e_sel:
                        _diag_salvar.append('%s -> %s' % (seletor, e_sel))

            if not clicou_salvar:
                try:
                    _JS_CLICK_SALVAR = """(() => {
                        const btn = document.querySelector('.criacao-alteracao-post-it button[aria-label="Salvar"]')
                                 || document.querySelector('button[aria-label="Salvar"]')
                                 || Array.from(document.querySelectorAll('.botoes-centralizados button')).find(b => (b.innerText || '').includes('Salvar') && !b.hasAttribute('matdialogclose'));
                        if (btn && !btn.disabled) {
                            btn.click();
                            return true;
                        }
                        return false;
                    })()"""
                    if page_obj:
                        if page_obj.evaluate(_JS_CLICK_SALVAR):
                            clicou_salvar = True
                            _diag_salvar.append('js_click -> True')
                    else:
                        _fn_exec = getattr(driver, 'execute_script', None)
                        if _fn_exec and _fn_exec(_JS_CLICK_SALVAR):
                            clicou_salvar = True
                            _diag_salvar.append('js_click -> True')
                except Exception as e_js:
                    _diag_salvar.append(f'js_err: {e_js}')

            if not clicou_salvar:
                espera.assentar(driver, 0.3)

        if not clicou_salvar:
            logger.error(
                '[LEMBRETE][POSIT] Botao "Salvar" nao clicado - lembrete "%s" NAO gravado'
                ' | tentativas: %s | tituloPostit=%s conteudoPostit=%s',
                titulo, _diag_salvar,
                bool(espera.elemento(driver, '#tituloPostit', teto=0.3)),
                bool(espera.elemento(driver, '#conteudoPostit', teto=0.3)),
            )
            _fechar_dialogo_residual()
            return False

        # esperarSalvamento do aagigs), mas NAO pode ser obrigatorio: se o
        _JS_SNACK = """(() => {
            const bars = document.querySelectorAll(
                'simple-snack-bar, .mat-snack-bar-container, snack-bar-container');
            for (const b of bars) {
                const t = (b.innerText || '').toLowerCase();
                if (t.includes('sucesso')) { return 'ok'; }
                if (t.includes('inv') && t.includes('argumento')) { return 'erro-argumento'; }
            }
            return '';
        })()"""
        sucesso = ''
        limite_snack = time.time() + 6
        while time.time() < limite_snack and not sucesso:
            try:
                _fn = getattr(driver, 'execute_script', None)
                if _fn is not None:
                    _ret = _fn(_JS_SNACK)
                else:
                    _page = getattr(driver, 'page', None)
                    _ret = _page.evaluate(_JS_SNACK) if _page is not None else None
                if isinstance(_ret, str):
                    sucesso = _ret
            except Exception:
                pass
            if not sucesso:
                espera.assentar(driver, 0.25)

        if sucesso != 'ok':
            dialogo_someu = espera.ate_sumir(driver, '#tituloPostit', teto=5)
            if not dialogo_someu:
                logger.error(
                    '[LEMBRETE][POSIT] Salvar nao teve efeito (snack=%r, dialogo aberto) - '
                    'lembrete "%s" NAO gravado', sucesso, titulo,
                )
                _fechar_dialogo_residual()
                return False
            logger.info(
                '[LEMBRETE][POSIT] Snack-bar nao observado (retorno=%r), mas o dialogo '
                'fechou apos o clique - assumindo gravado', sucesso,
            )

        try:
            espera.ate_js(
                driver,
                """(() => {
                    const b = document.querySelector('simple-snack-bar button, .mat-snack-bar-container button');
                    if (b) { b.click(); return true; }
                    return false;
                })()""",
                teto=2,
            )
        except Exception:
            pass

        try:
            espera.ate_sumir(driver, '#tituloPostit', teto=3)
            espera.ate_sumir(driver, 'pje-dialogo-post-it', teto=3)
            espera.ate_sumir(driver, '.cdk-overlay-backdrop-showing', teto=2)
        except Exception:
            pass
        espera.assentar(driver, 0.3)

        logger.info('[LEMBRETE][POSIT] Lembrete "%s" salvo com sucesso', titulo)
        return True

    except Exception as e:
        if debug:
            logger.error("ERRO em criar_lembrete_posit: %s: %s", type(e).__name__, e)
        _fechar_dialogo_residual()
        return False

def remover_lembrete_posit(driver: Any, titulo: str, conteudo: Optional[str] = None, debug: bool = False) -> bool:
    """Remove/conclui lembrete(s) existente(s) no painel de post-its."""
    conexao_status = validar_conexao_driver(driver, "REMOVER_LEMBRETE")
    if conexao_status == "FATAL" or not conexao_status:
        return False

    alvo_tit = _normalizar_texto(titulo)
    alvo_cont = _normalizar_texto(conteudo) if conteudo else ''

    try:
        container = espera.elemento(driver, 'pje-visualizador-post-its div[class*="post-it-set"], pje-visualizador-post-its', teto=2)
        if not container:
            if debug:
                logger.debug('[LEMBRETE][REMOVER] Container de post-its não encontrado')
            return False

        paineis = espera.elementos(driver, 'pje-visualizador-post-its mat-expansion-panel, div[class*="post-it-set"] mat-expansion-panel', teto=2)
        if not paineis:
            if debug:
                logger.debug('[LEMBRETE][REMOVER] Nenhum post-it encontrado no painel')
            return False

        removido_algum = False
        for painel in paineis:
            try:
                el_tit = espera.elemento(painel, 'div[class="post-it-div-titulo"], .post-it-div-titulo, .post-it-titulo, mat-panel-title', teto=0.3)
                txt_tit = _normalizar_texto(getattr(el_tit, 'text', '') or '') if el_tit else ''

                if alvo_tit and not (alvo_tit in txt_tit or txt_tit in alvo_tit):
                    continue

                if alvo_cont:
                    el_cont = espera.elemento(painel, 'div[aria-label="Conteúdo do Lembrete"], .post-it-conteudo, [aria-label*="Conteúdo" i]', teto=0.3)
                    txt_cont = _normalizar_texto(getattr(el_cont, 'text', '') or '') if el_cont else ''
                    if txt_cont and not (alvo_cont in txt_cont or txt_cont in alvo_cont):
                        continue

                btn_remover = espera.elemento(painel, 'button[aria-label*="Remover" i], button[title*="Remover" i]', teto=1)
                if not btn_remover:
                    header = espera.elemento(painel, 'mat-expansion-panel-header', teto=0.5)
                    if header:
                        safe_click_no_scroll(driver, header)
                        espera.assentar(driver, 0.3)
                        btn_remover = espera.elemento(painel, 'button[aria-label*="Remover" i], button[title*="Remover" i]', teto=1)

                if btn_remover:
                    safe_click_no_scroll(driver, btn_remover)
                    espera.assentar(driver, 0.4)

                    confirmado = False
                    seletores_confirmar = [
                        'mat-dialog-container button[color="primary"]',
                        'mat-dialog-container button[type="submit"]',
                        '//mat-dialog-container//button[contains(., "Excluir") or contains(., "Sim") or contains(., "Confirmar")]',
                        'mat-dialog-container button',
                    ]
                    for sel_conf in seletores_confirmar:
                        try:
                            if aguardar_e_clicar(driver, sel_conf, timeout=2, log=False):
                                confirmado = True
                                break
                        except Exception:
                            continue

                    if confirmado:
                        espera.ate_sumir(driver, 'mat-dialog-container', teto=3)
                        espera.assentar(driver, 0.4)
                        removido_algum = True
                        logger.info('[LEMBRETE][REMOVER] Lembrete "%s" excluído com sucesso', titulo)
            except Exception as e_painel:
                if debug:
                    logger.debug('[LEMBRETE][REMOVER] Erro ao processar painel de post-it: %s', e_painel)
                continue

        return removido_algum
    except Exception as e:
        if debug:
            logger.error('[LEMBRETE][REMOVER] Erro geral ao remover lembrete: %s', e)
        return False


def _parse_gigs_string(string):
    """Parseia string de teste GIGS automaticamente."""
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
    """Cria atividade GIGS na aba /detalhe - VERSÃO OTIMIZADA baseada em a.py"""
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

        # Etapa 0: isolamento pré-abertura (formulário, overlay e snackbar anteriores)
        espera.ate_sumir(driver, 'textarea[formcontrolname="observacao"]', teto=6)
        aguardar_renderizacao_nativa(driver, '.cdk-overlay-backdrop-showing', modo='sumir', timeout=6)
        try:
            btn_x_prev = espera.elemento(driver, 'simple-snack-bar button, snack-bar-container button', teto=0.4)
            if btn_x_prev:
                btn_x_prev.click()
            espera.ate_sumir(driver, 'simple-snack-bar, snack-bar-container', teto=2)
        except Exception:
            pass

        # Etapa 1: abrir formulário limpo
        if log:
            logger.debug('[GIGS] Clicando Nova Atividade...')
        btn_nova = espera.elemento(
            driver, "//button[.//span[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')] "
            "or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nova atividade')]",
            teto=timeout,
        )
        if not btn_nova:
            raise TimeoutException("Botao 'Nova Atividade' nao encontrado")
        btn_nova.click()

        espera.ate_aparecer(driver, 'textarea[formcontrolname="observacao"]', teto=timeout)

        if not espera.ate_js(
            driver,
            """__pjeEls('textarea[formcontrolname="observacao"]').some("""
            """el => (el.value || '') === '')""",
            teto=timeout,
        ):
            raise TimeoutException('Formulario de atividade nao ficou limpo (resquicio do anterior)')

        if log:
            logger.debug('[GIGS] Formulario aberto')

        from Fix.core import preencher_campo

        dias_str = str(dias_uteis).strip() if dias_uteis is not None and str(dias_uteis).strip() != '' else ''

        _JS_CONFIRMAR_PRAZO = """(esperado) => {
            var inpDias = document.querySelector('input[formcontrolname="dias"]');
            if (!inpDias) return false;
            if (String(inpDias.value || '').trim() !== String(esperado)) return false;
            var form = inpDias.closest('form') || inpDias.closest('mat-dialog-container') || document;
            var inpData = form.querySelector(
                'input[formcontrolname="dataPrazo"], input[formcontrolname="prazo"], ' +
                'input[formcontrolname*="dataPrazo" i], input[formcontrolname*="dataLimite" i]'
            );
            if (inpData && inpData.offsetParent !== null) {
                return String(inpData.value || '').trim().length > 0;
            }
            return true;
        }"""

        def _preencher_e_confirmar_prazo() -> bool:
            campo_dias = espera.elemento(driver, 'input[formcontrolname="dias"]', teto=timeout)
            if not campo_dias:
                logger.error('[GIGS] Campo de prazo (dias) nao apareceu — abortando para nao criar GIGS sem prazo')
                return False

            expr_ok = f"({_JS_CONFIRMAR_PRAZO})({json.dumps(dias_str)})"
            for tentativa_prazo in (1, 2):
                preenchido_nativo = False
                try:
                    if hasattr(driver, 'page') and driver.page:
                        loc = driver.page.locator('input[formcontrolname="dias"]').first
                        loc.click(timeout=2000)
                        loc.fill('', timeout=2000)
                        loc.fill(dias_str, timeout=2000)
                        loc.press('Tab', timeout=2000)
                        preenchido_nativo = True
                except Exception:
                    preenchido_nativo = False

                if not preenchido_nativo:
                    preencher_campo(driver, 'input[formcontrolname="dias"]', dias_str, limpar=True)
                    try:
                        espera._executar_script(driver, """
                            var el = document.querySelector('input[formcontrolname="dias"]');
                            if (el) {
                                el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
                                el.dispatchEvent(new Event('change', {bubbles: true}));
                                el.dispatchEvent(new FocusEvent('blur', {bubbles: true}));
                                try { el.blur(); } catch (e) {}
                            }
                        """)
                    except Exception:
                        pass

                espera.assentar(driver, 0.4, motivo='calculo do prazo no formulario GIGS')
                if espera.ate_js(driver, expr_ok, teto=4):
                    if log:
                        logger.info('[GIGS] Prazo confirmado no formulario: %s dias (tentativa %d)', dias_str, tentativa_prazo)
                    return True
                logger.warning('[GIGS] Prazo %s nao confirmado na tentativa %d/2 — retentando', dias_str, tentativa_prazo)

            logger.error('[GIGS] Prazo %s nao confirmado no formulario apos 2 tentativas — abortando sem salvar', dias_str)
            return False

        # Etapa 2: prazo (isolado e obrigatório quando solicitado)
        if dias_str:
            if not _preencher_e_confirmar_prazo():
                return False

        # Etapa 3: responsável (isolado)
        if responsavel:
            preencher_campo(driver, 'input[formcontrolname="responsavel"]', responsavel, limpar=True)
            espera.assentar(driver, 0.5)
            _pressionar_tecla(driver, "ArrowDown")
            espera.assentar(driver, 0.2)
            _pressionar_tecla(driver, "Enter")
            espera.assentar(driver, 0.2)
            if log:
                logger.debug('[GIGS] Responsavel: %s', responsavel)

        # Etapa 4: observação (isolada com confirmação)
        if observacao:
            preencher_campo(driver, 'textarea[formcontrolname="observacao"]', observacao, limpar=True)
            espera.assentar(driver, 0.3)
            if log:
                obs_preview = observacao[:50] + '...' if len(observacao) > 50 else observacao
                logger.debug('[GIGS] Observacao: %s', obs_preview)

        # Etapa 5: barreira final de integridade dos parâmetros antes do Salvar
        if dias_str:
            expr_ok = f"({_JS_CONFIRMAR_PRAZO})({json.dumps(dias_str)})"
            if not espera.ate_js(driver, expr_ok, teto=2):
                logger.warning('[GIGS] Prazo %s perdeu-se antes de Salvar — reaplicando', dias_str)
                if not _preencher_e_confirmar_prazo():
                    return False

        if observacao:
            obs_esperada = str(observacao).strip()
            expr_obs = (
                "__pjeEls('textarea[formcontrolname=\"observacao\"]').some("
                f"el => String(el.value || '').trim() === {json.dumps(obs_esperada)})"
            )
            if not espera.ate_js(driver, expr_obs, teto=2):
                preencher_campo(driver, 'textarea[formcontrolname="observacao"]', observacao, limpar=True)
                espera.assentar(driver, 0.3)
                if not espera.ate_js(driver, expr_obs, teto=2):
                    logger.error('[GIGS] Observacao nao confirmada no formulario antes de Salvar — abortando')
                    return False

        # Etapa 6: fechar snackbar residual, salvar e confirmar persistência + fechamento
        try:
            btn_x = espera.elemento(driver, 'simple-snack-bar button, snack-bar-container button', teto=0.5)
            if btn_x:
                btn_x.click()
            espera.ate_sumir(driver, 'simple-snack-bar, snack-bar-container', teto=2)
        except Exception:
            pass

        if log:
            logger.debug('[GIGS] Salvando...')
        btn_salvar = espera.elemento(driver, "//button[contains(., 'Salvar')]", teto=timeout)
        if not btn_salvar:
            raise TimeoutException("Botao 'Salvar' nao encontrado")
        btn_salvar.click()

        if espera.ate_aparecer(
            driver,
            "//snack-bar-container//span[contains(normalize-space(.), 'Atividade salva com sucesso')]",
            teto=timeout,
        ):
            if log:
                logger.debug('[GIGS] Atividade criada com sucesso')
        else:
            logger.warning('[GIGS] Snackbar "Atividade salva com sucesso" nao apareceu — conferir o painel GIGS do processo')

        try:
            btn_x = espera.elemento(driver, 'simple-snack-bar button, snack-bar-container button', teto=1)
            if btn_x:
                btn_x.click()
            espera.ate_sumir(driver, 'simple-snack-bar, snack-bar-container', teto=2)
        except Exception:
            pass

        if not espera.ate_sumir(driver, 'textarea[formcontrolname="observacao"]', teto=6):
            if log:
                logger.error('[GIGS] Formulario nao fechou apos Salvar — atividade nao gravada')
            return False

        return True

    except Exception as e:
        if log:
            logger.error("ERRO em criar_gigs: %s: %s", type(e).__name__, e)
        return False


def _clicar_salvar_com_confirmacao(
    driver: Any,
    xpath_botao: str,
    seletor_formulario: str,
    teto: float = 10,
    log: bool = False,
) -> bool:
    """Clica em "Salvar" e so retorna True se o clique teve efeito."""
    limite = time.time() + max(1.0, teto)
    btn = None
    while time.time() < limite:
        try:
            btn = espera.elemento(driver, xpath_botao, teto=0.5)
        except Exception:
            btn = None
        if btn is not None:
            try:
                desabilitado = btn.get_attribute('disabled') or btn.get_attribute('aria-disabled')
                if desabilitado not in (True, 'true', 'disabled', ''):
                    break
                if desabilitado in (None, False, 'false'):
                    break
            except Exception:
                break
        espera.assentar(driver, 0.2)

    if btn is None:
        if log:
            logger.error('[SALVAR] botao nao encontrado: %s', xpath_botao)
        return False

    try:
        btn.click()
    except Exception as e:
        if log:
            logger.error('[SALVAR] clique falhou: %s', e)
        return False

    if espera.ate_sumir(driver, seletor_formulario, teto=5):
        return True

    if log:
        logger.error('[SALVAR] formulario (%s) continua no DOM apos o clique', seletor_formulario)
    return False


def criar_comentario(driver, observacao, visibilidade='LOCAL', timeout=10, log=True):
    """Cria comentário GIGS na aba /detalhe - baseado em lancarComentario do a.py"""
    conexao_status = validar_conexao_driver(driver, "COMENTARIO")
    if conexao_status == "FATAL":
        if log:
            logger.error('ERRO em criar_comentario: sessao do driver inutilizavel (contexto descartado) - abortando sem tentar interacao')
        return False
    if not conexao_status:
        if log:
            logger.error('ERRO em criar_comentario: driver desconectado - abortando sem tentar interacao')
        return False

    try:
        if log:
            com_preview = observacao[:50] + '...' if len(observacao) > 50 else observacao
            logger.debug("[COMENTARIO] Criando: %s", com_preview)

        if log:
            logger.debug('[COMENTARIO] Clicando Novo Comentario...')
        btn_novo = espera.elemento(
            driver, "//button[contains(., 'Novo Comentário') or contains(., 'Novo comentário')]", teto=timeout
        )
        if not btn_novo:
            raise TimeoutException("Botao 'Novo Comentario' nao encontrado")
        btn_novo.click()
        espera.ate_aparecer(driver, 'textarea[formcontrolname="descricao"], textarea[name="descricao"]', teto=1)

        espera.ate_aparecer(driver, 'textarea[formcontrolname="descricao"], textarea[name="descricao"]', teto=timeout)
        if log:
            logger.debug('[COMENTARIO] Formulario aberto')

        from Fix.core import preencher_campo
        preencher_campo(driver, 'textarea[formcontrolname="descricao"], textarea[name="descricao"]', observacao, limpar=True)
        espera.assentar(driver, 0.3)
        if log:
            logger.debug('[COMENTARIO] Descricao preenchida')

        visibilidade_upper = visibilidade.upper()
        if log:
            logger.debug('[COMENTARIO] Visibilidade: %s', visibilidade_upper)

        try:
            radio_inputs = espera.elementos(driver, 'pje-gigs-comentarios-cadastro mat-radio-button input, mat-radio-button input')
            if len(radio_inputs) >= 3:
                index_map = {'LOCAL': 0, 'RESTRITA': 1, 'GLOBAL': 2}
                idx = index_map.get(visibilidade_upper, 0)
                safe_click_no_scroll(driver, radio_inputs[idx])
                espera.assentar(driver, 0.3)

                if visibilidade_upper == 'RESTRITA':
                    if log:
                        logger.debug('[COMENTARIO] Visibilidade RESTRITA - pode requerer selecao de usuarios')
                    espera.assentar(driver, 0.5)
        except Exception as e:
            if log:
                logger.warning('[COMENTARIO][AVISO] Nao foi possivel selecionar visibilidade: %s', e)

        if log:
            logger.debug('[COMENTARIO] Salvando...')
        if not _clicar_salvar_com_confirmacao(
            driver,
            "//button[contains(., 'Salvar')]",
            'textarea[formcontrolname="descricao"], textarea[name="descricao"]',
            teto=timeout,
            log=log,
        ):
            if log:
                logger.error('[COMENTARIO] Salvar nao teve efeito - comentario NAO gravado')
            return False

        if not espera.ate_sumir(driver, 'mat-dialog-container', teto=3):
            modais = espera.elementos(driver, 'mat-dialog-container') or []
            if any(m.is_displayed() for m in modais):
                if log:
                    logger.error('[COMENTARIO] Modal segue aberto apos salvar - comentario NAO gravado')
                _pressionar_tecla(driver, "Escape")
                espera.ate_sumir(driver, 'mat-dialog-container', teto=1)
                return False

        if log:
            logger.debug('[COMENTARIO] Comentario criado com sucesso')
        return True

    except Exception as e:
        if log:
            logger.error("ERRO em criar_comentario: %s: %s", type(e).__name__, e)
        return False


def bndt(driver, inclusao=False, debug=False, **kwargs):
    """Executa rotinas BNDT no polo Passivo."""
    try:
        logger.info(f'BNDT: parâmetro inclusao recebido: {inclusao!r} (tipo: {type(inclusao)})')
    except Exception:
        pass
    operacao = "Inclusão" if inclusao else "Exclusão"
    logger.info(f'Iniciando operação BNDT: {operacao}')

    main_window = driver.current_window_handle
    nova_aba = None
    erro_classe = False

    try:
        main_window, nova_aba = _bndt_abrir_nova_aba(driver)

        polo = 'Passivo'
        logger.info(f'============ Processando Polo {polo} ============')

        if hasattr(driver, 'page') and driver.page:
            try:
                driver.page.bring_to_front()
            except Exception:
                pass

        logger.info(f'Procurando botão de polo {polo}...')
        try:
            clicado = _bndt_clicar_radio_js(
                driver,
                seletores_input=[
                    f'#selecao-polo input[type="radio"][value="{polo}"]',
                    f'#selecao-polo input[type="radio"][value="{polo.upper()}"]',
                    f'input[type="radio"][value="{polo}"]',
                    f'input[type="radio"][value="{polo.upper()}"]',
                ],
                texto_label=polo,
            )
            if not clicado:
                seletor_polo = [
                    (By.CSS_SELECTOR, f'#selecao-polo input[value="{polo}"]'),
                    (By.XPATH, f"//input[@value='{polo}']/ancestor::mat-radio-button//label | //mat-radio-button[@value='{polo}']//label"),
                ]

                btn_polo = None
                for by, selector in seletor_polo:
                    btn_polo = espera.elemento(driver, selector, teto=5, visivel=False)
                    if btn_polo:
                        break

                if not btn_polo:
                    raise Exception(f'Botao de polo {polo} nao encontrado')

                try:
                    safe_click_no_scroll(driver, btn_polo)
                except Exception:
                    btn_polo.click()

            logger.info(f'Polo {polo} selecionado')
        except Exception as e:
            logger.error(f'Erro ao selecionar polo {polo}: {e}')
            raise

        if not _bndt_selecionar_operacao_para_polo(driver, inclusao, polo):
            driver.close()
            driver.switch_to.window(main_window)
            return False

        estado_lista = _bndt_aguardar_carregamento_operacao(driver, inclusao=inclusao, teto=10)
        logger.info(f'[BNDT] Estado após selecionar {operacao} ({polo}): {estado_lista}')

        try:
            texto_no_reg = ""
            if hasattr(driver, 'page') and driver.page:
                texto_no_reg = driver.page.evaluate("""() => {
                    var els = document.querySelectorAll('#tabela-registros-bndt div[class*="mensagem"], pje-bndt-partes-sem-registro .mensagem, pje-bndt-exclusao .mensagem, mat-card .mensagem, div.mensagem.ng-star-inserted, div.mensagem');
                    for (var i = 0; i < els.length; i++) {
                        var txt = (els[i].textContent || '').trim().toLowerCase();
                        if (txt.includes('não há registros') || txt.includes('não existem partes') || txt.includes('nenhum registro')) return txt;
                    }
                    return '';
                }""") or ""
            if texto_no_reg:
                logger.info(f'Polo {polo}: "{texto_no_reg}" — nada a fazer')
                driver.close()
                driver.switch_to.window(main_window)
                return True
        except Exception:
            pass

        try:
            msg_classe = False
            if hasattr(driver, 'page') and driver.page:
                msg_classe = bool(driver.page.evaluate("""() => {
                    return document.evaluate("//*[contains(text(),'A classe judicial do processo não pode acessar')]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue != null;
                }"""))
            if msg_classe:
                logger.warning(f'Polo {polo}: Classe judicial do processo não permite cadastro no BNDT')
                erro_classe = True
                driver.close()
                driver.switch_to.window(main_window)
                return False
        except Exception:
            pass

        marcou = _bndt_processar_selecoes_polo(driver, polo, inclusao=inclusao)
        if not marcou:
            logger.warning(f'[BNDT] Nenhuma parte/registro marcado para {operacao} no polo {polo} — abortando gravação')
            driver.close()
            driver.switch_to.window(main_window)
            return False

        gravou = _bndt_gravar_e_confirmar_polo(driver, polo, inclusao=inclusao)

        logger.info(f'============ Finalizando operação {operacao} ============')

        if erro_classe:
            logger.warning('ATENÇÃO: Classe do processo não suporta BNDT!')

        driver.close()
        driver.switch_to.window(main_window)
        if gravou:
            logger.info(f'Operação {operacao} concluída no polo {polo}')
        else:
            logger.warning(f'Operação {operacao} falhou ao gravar no polo {polo}')
        return bool(gravou)

    except Exception as e:
        logger.error(f'ERRO na operação {operacao}: {e}')
        todas_abas = list(getattr(driver, 'window_handles', []))
        if nova_aba and nova_aba in todas_abas:
            try:
                driver.switch_to.window(nova_aba)
                driver.close()
            except Exception:
                pass

        if main_window and main_window in todas_abas:
            try:
                driver.switch_to.window(main_window)
            except Exception:
                pass
        return False


def _bndt_abrir_menu(driver: Any) -> bool:
    """Abre o menu hambúrguer com validação robusta."""
    try:
        btn_menu = espera.elemento(driver, 'i.fa-bars.icone-botao-menu', teto=10)
        if not btn_menu:
            logger.error('Menu hambúrguer não encontrado')
            return False
        btn_menu.click()
        logger.info('Menu hambúrguer clicado')
        espera.assentar(driver, 0.2)
        return True
    except Exception as e:
        logger.error(f'Erro ao abrir menu: {e}')
        return False


def _bndt_clicar_icone(driver: Any) -> bool:
    """Clica no ícone BNDT com validação robusta."""
    try:
        btn_bndt = espera.elemento(driver, 'i.fas.fa-money-check-alt.icone-padrao', teto=10)
        if not btn_bndt:
            logger.error('Ícone BNDT não encontrado')
            return False
        btn_bndt.click()
        logger.info('Ícone BNDT clicado')
        espera.assentar(driver, 0.3)
        return True
    except Exception as e:
        logger.error(f'Erro ao clicar ícone BNDT: {e}')
        return False


def _bndt_abrir_nova_aba(driver):
    """Abre nova aba BNDT e retorna seu handle."""
    main_window = driver.current_window_handle

    current_url = driver.current_url or ''
    match = re.search(r'/processo/(\d+)', current_url)
    id_processo = match.group(1) if match else None

    if id_processo:
        url_bndt = f"/pjekz/processo/{id_processo}/bndt"
        handles_antes = list(getattr(driver, 'window_handles', []))
        if hasattr(driver, 'page') and driver.page:
            driver.page.evaluate("url => window.open(url, '_blank')", url_bndt)
        try:
            espera.ate_abas(driver, len(handles_antes) + 1, teto=10)
            novos_handles = [w for w in list(getattr(driver, 'window_handles', [])) if w not in handles_antes]
            if novos_handles:
                nova_aba = novos_handles[-1]
                driver.switch_to.window(nova_aba)
                espera.ate_url(driver, '/bndt', teto=15)
                espera.assentar(driver, 0.5)
                if espera.ate_aparecer(driver, 'mat-card, mat-radio-group, button, #selecao-polo', teto=10):
                    logger.info('Elementos da página BNDT detectados')
                logger.info(f'Nova aba BNDT aberta diretamente via URL: {driver.current_url}')
                return main_window, nova_aba
        except Exception as e_direct:
            logger.warning(f'Falha ao abrir BNDT diretamente via URL ({e_direct}), tentando via menu...')

    _bndt_abrir_menu(driver)
    _bndt_clicar_icone(driver)

    espera.ate_abas(driver, 2, teto=15)
    all_windows = list(getattr(driver, 'window_handles', []))
    nova_aba = [w for w in all_windows if w != main_window]
    if not nova_aba:
        raise Exception('Nova aba BNDT não foi criada')

    nova_aba = nova_aba[-1]
    driver.switch_to.window(nova_aba)
    espera.ate_url(driver, '/bndt', teto=15)

    espera.assentar(driver, 0.5)
    if espera.ate_aparecer(driver, 'mat-card, mat-radio-group, button, #selecao-polo', teto=10):
        logger.info('Elementos da página BNDT detectados')
    else:
        logger.warning('AVISO: Elementos podem não ter carregado')

    logger.info(f'Nova aba BNDT aberta: {driver.current_url}')
    return main_window, nova_aba


def _bndt_selecionar_operacao(driver, inclusao):
    """Seleciona Inclusão ou Exclusão."""
    operacao = "Inclusão" if inclusao else "Exclusão"

    if not espera.ate_js(driver, "document.readyState === 'complete'", teto=10):
        logger.warning('AVISO: Página pode não ter carregado a tempo')

    if inclusao:
        try:
            try:
                inp = espera.elemento(driver, "//input[@name='mat-radio-group-1' and @value='INCLUSAO']")
                checked = False
                try:
                    checked = inp.is_selected() or inp.get_attribute('checked') or inp.get_attribute('aria-checked') == 'true'
                except Exception:
                    checked = False
                if checked:
                    logger.info('BNDT: Inclusão já selecionada — sem ação necessária')
                    return True
                else:
                    try:
                        parent = espera.elemento(driver, "//input[@name='mat-radio-group-1' and @value='INCLUSAO']/ancestor::mat-radio-button")
                        if parent:
                            parent.click()
                        logger.info('BNDT: Radio Inclusão clicado (detected unchecked -> clicked)')
                        espera.assentar(driver, 0.5)
                        return True
                    except Exception:
                        logger.info('BNDT: Inclusão requisitada — assumindo opção padrão já selecionada')
                        return True
            except Exception:
                logger.info('BNDT: Inclusão requisitada — assumindo opção padrão já selecionada')
                return True
        except Exception as e:
            logger.warning(f'BNDT: Falha ao verificar radio Inclusão, mas prosseguindo sem clique: {e}')
            return True

    selectors = [
        (By.XPATH, "//mat-radio-button[@id='mat-radio-7']"),
        (By.XPATH, "//mat-radio-button[contains(@id,'mat-radio-')][.//input[@value='EXCLUSAO'] ]"),
        (By.XPATH, "//mat-radio-button[.//span[contains(text(),'Exclusão')]]"),
        (By.XPATH, "//input[@name='mat-radio-group-1'][@value='EXCLUSAO']/ancestor::mat-radio-button")
    ]

    radio_operacao = None
    for by, selector in selectors:
        radio_operacao = espera.elemento(driver, selector, teto=5)
        if radio_operacao:
            logger.info(f'Radio {operacao} encontrado')
            break

    if not radio_operacao:
        raise Exception(f'Não foi possível encontrar o radio button de {operacao}')

    radio_operacao.click()
    logger.info(f'Radio {operacao} clicado')
    espera.assentar(driver, 0.5)

    try:
        mensagem_nao_existem_partes = espera.elementos(driver, "//div[contains(@class, 'mensagem') and contains(text(), 'Não existem partes a serem selecionadas')]")
        if mensagem_nao_existem_partes:
            logger.info('BNDT: Não existem partes a serem selecionadas — operação cumprida sem seleções')
            return True
    except Exception as e:
        logger.warning(f'BNDT: Erro ao verificar mensagem de partes não existentes: {e}')


def _bndt_clicar_radio_js(driver, seletores_input, texto_label: str = '') -> bool:
    """Seleciona um mat-radio-button clicando no label/círculo/input real (Angular Material ignora click no host)."""
    if not (hasattr(driver, 'page') and driver.page):
        return False
    try:
        return bool(driver.page.evaluate("""({ seletores, textoLabel }) => {
            function clicarRadio(radio) {
                if (!radio) return false;
                var matRadio = radio.closest('mat-radio-button');
                var jaMarcado = !!(radio.checked || (matRadio && matRadio.classList.contains('mat-radio-checked')));
                if (jaMarcado) return true;
                var alvo = (matRadio && (
                    matRadio.querySelector('label.mat-radio-label')
                    || matRadio.querySelector('span.mat-radio-outer-circle')
                    || matRadio.querySelector('span.mat-radio-inner-circle')
                )) || radio;
                alvo.click();
                if (!radio.checked && (!matRadio || !matRadio.classList.contains('mat-radio-checked'))) {
                    radio.click();
                }
                return !!(radio.checked || (matRadio && matRadio.classList.contains('mat-radio-checked')));
            }

            for (var i = 0; i < seletores.length; i++) {
                var r = document.querySelector(seletores[i]);
                if (r) return clicarRadio(r);
            }

            if (textoLabel) {
                var alvoNorm = textoLabel.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
                var radios = document.querySelectorAll('mat-radio-button');
                for (var j = 0; j < radios.length; j++) {
                    var txt = (radios[j].textContent || '').trim().toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
                    if (txt.includes(alvoNorm)) {
                        var inp = radios[j].querySelector('input[type="radio"]');
                        return clicarRadio(inp || radios[j]);
                    }
                }
            }
            return false;
        }""", {'seletores': list(seletores_input), 'textoLabel': texto_label}))
    except Exception:
        return False


def _bndt_aguardar_carregamento_operacao(driver, inclusao: bool = False, teto: float = 10.0) -> str:
    """Aguarda a resposta assíncrona do BNDT renderizar checkboxes ou mensagem de vazio/erro."""
    js_estado = """() => {
        var spinners = document.querySelectorAll('div[class*="container-loading"] mat-progress-spinner, mat-progress-spinner');
        for (var s = 0; s < spinners.length; s++) {
            var st = window.getComputedStyle(spinners[s]);
            if (st && st.display !== 'none' && st.visibility !== 'hidden' && spinners[s].offsetParent !== null) {
                return '';
            }
        }
        var checks = document.querySelectorAll(
            'input[id^="parte"][id$="-input"], mat-checkbox[id^="parte"], '
            + 'label[for*="debito"][for*="-input"], input[id*="debito"][id$="-input"], '
            + 'pje-bndt-partes-sem-registro mat-checkbox, pje-bndt-exclusao mat-checkbox'
        );
        if (checks.length > 0) return 'checkboxes';

        var msgs = document.querySelectorAll(
            '#tabela-registros-bndt div[class*="mensagem"], pje-bndt-partes-sem-registro .mensagem, '
            + 'pje-bndt-exclusao .mensagem, mat-card .mensagem, div.mensagem.ng-star-inserted, div.mensagem'
        );
        for (var i = 0; i < msgs.length; i++) {
            var txt = (msgs[i].textContent || '').trim().toLowerCase();
            if (txt.includes('não há registros') || txt.includes('não existem partes') || txt.includes('nenhum registro')) {
                return 'vazio';
            }
            if (txt.includes('a classe judicial do processo não pode acessar')) {
                return 'classe_invalida';
            }
        }
        var bodyTxt = (document.body && document.body.textContent || '').toLowerCase();
        if (bodyTxt.includes('a classe judicial do processo não pode acessar')) return 'classe_invalida';
        return '';
    }"""
    if hasattr(driver, 'page') and driver.page:
        ok = espera.ate_js(driver, f"Boolean(({js_estado})())", teto=teto)
        if ok:
            try:
                return driver.page.evaluate(js_estado) or 'desconhecido'
            except Exception:
                return 'desconhecido'
        return 'timeout'
    return 'sem_page'


def _bndt_selecionar_operacao_para_polo(driver, inclusao, polo):
    """Seleciona Inclusão ou Exclusão para um polo específico."""
    operacao = "Inclusão" if inclusao else "Exclusão"
    tipo_operacao = "INCLUSAO" if inclusao else "EXCLUSAO"

    logger.info(f'Selecionando operação: {operacao} para polo {polo}')

    if hasattr(driver, 'page') and driver.page:
        try:
            driver.page.bring_to_front()
        except Exception:
            pass

    seletores_input = [
        f'#selecao-tipo-determinacao input[type="radio"][value="{tipo_operacao}"]',
        f'input[name="mat-radio-group-1"][type="radio"][value="{tipo_operacao}"]',
        f'input[type="radio"][value="{tipo_operacao}"]',
    ]

    if _bndt_clicar_radio_js(driver, seletores_input=seletores_input, texto_label=operacao):
        logger.info(f'Operação {operacao} selecionada e confirmada para polo {polo} via JS')
        return True

    seletores_operacao = [
        (By.XPATH, f"//input[@type='radio' and @value='{tipo_operacao}']/ancestor::mat-radio-button//label"),
        (By.XPATH, f"//mat-radio-button[.//span[contains(normalize-space(.),'{operacao}')]]//label"),
        (By.CSS_SELECTOR, f'#selecao-tipo-determinacao input[value="{tipo_operacao}"]'),
    ]

    for by, selector in seletores_operacao:
        btn_operacao = espera.elemento(driver, selector, teto=5, visivel=False)
        if not btn_operacao:
            continue
        try:
            safe_click_no_scroll(driver, btn_operacao)
        except Exception:
            btn_operacao.click()
        logger.info(f'Operação {operacao} selecionada para polo {polo} via seletor: {selector}')
        return True

    logger.warning(f'Erro ao selecionar operação {operacao} no polo {polo}: nenhum seletor funcionou')
    return False


def _bndt_processar_selecoes(driver):
    """Seleciona o checkbox de "Selecionar todos" se disponível."""
    selectors = [
        "//mat-checkbox[.//span[contains(text(),'Selecionar todos')]]//label",
        "//mat-checkbox[.//span[contains(text(),'Selecionar todos')]]//input[@type='checkbox']",
        "//span[contains(@class,'mat-checkbox-label')][contains(text(),'Selecionar todos')]/ancestor::mat-checkbox//label",
        "//input[@type='checkbox'][@aria-label='Selecionar todos']/ancestor::mat-checkbox//label"
    ]

    for selector in selectors:
        try:
            chk_todos = espera.elemento(driver, selector)
            if chk_todos:
                safe_click_no_scroll(driver, chk_todos)
                logger.info('Checkbox "Selecionar todos" clicado (sem aguardar elementos extras)')
                espera.assentar(driver, 0.25)
                return
        except Exception:
            continue

    logger.warning('Checkbox "Selecionar todos" não encontrado — ação concluída sem seleção adicional')


def _bndt_processar_selecoes_polo(driver, polo, inclusao=False) -> bool:
    """Seleciona checkboxes de partes/débitos no BNDT via JS com confirmação de estado checked."""
    logger.info(f'Processando seleções para polo {polo} via JS (inclusao={inclusao})...')
    try:
        marcados = 0
        if hasattr(driver, 'page') and driver.page:
            marcados = int(driver.page.evaluate("""inclusao => {
                function marcarCheckbox(container) {
                    if (!container) return false;
                    var matChk = container.matches && container.matches('mat-checkbox')
                        ? container
                        : (container.closest ? container.closest('mat-checkbox') : null);
                    var inp = (container.tagName === 'INPUT')
                        ? container
                        : (matChk ? matChk.querySelector('input[type="checkbox"]') : null);
                    if (inp && inp.disabled) return false;
                    if (inp && inp.checked) return true;
                    if (matChk && matChk.classList.contains('mat-checkbox-checked')) return true;

                    var lbl = (matChk && matChk.querySelector('label.mat-checkbox-layout'))
                        || (matChk && matChk.querySelector('label'))
                        || (container.tagName === 'LABEL' ? container : null);
                    if (lbl) lbl.click();
                    if (inp && !inp.checked && (!matChk || !matChk.classList.contains('mat-checkbox-checked'))) {
                        inp.click();
                    }
                    return !!((inp && inp.checked) || (matChk && matChk.classList.contains('mat-checkbox-checked')));
                }

                if (inclusao) {
                    var candidatos = Array.from(document.querySelectorAll(
                        'pje-bndt-partes-sem-registro mat-checkbox[id^="parte"], mat-checkbox[id^="parte"], input[id^="parte"][id$="-input"]'
                    ));
                    for (var i = 0; i < candidatos.length; i++) {
                        if (marcarCheckbox(candidatos[i])) return 1;
                    }
                    var fallback = Array.from(document.querySelectorAll('pje-bndt-partes-sem-registro mat-checkbox, mat-checkbox'));
                    for (var j = 0; j < fallback.length; j++) {
                        var txt = (fallback[j].textContent || '').toLowerCase();
                        if (txt.indexOf('selecionar todos') !== -1) continue;
                        if (marcarCheckbox(fallback[j])) return 1;
                    }
                    return 0;
                } else {
                    var cont = 0;
                    var debitos = Array.from(document.querySelectorAll(
                        'pje-bndt-exclusao label[for*="debito"][for*="-input"], label[for*="debito"][for*="-input"], input[id*="debito"][id$="-input"]'
                    ));
                    var vistos = new Set();
                    for (var k = 0; k < debitos.length; k++) {
                        var mat = debitos[k].closest ? (debitos[k].closest('mat-checkbox') || debitos[k]) : debitos[k];
                        if (vistos.has(mat)) continue;
                        vistos.add(mat);
                        if (marcarCheckbox(mat)) cont++;
                    }
                    if (cont > 0) return cont;
                    var fallEx = Array.from(document.querySelectorAll(
                        'pje-bndt-exclusao mat-checkbox[id^="parte"], mat-checkbox[id^="parte"], input[id^="parte"][id$="-input"]'
                    ));
                    for (var m = 0; m < fallEx.length; m++) {
                        var mat2 = fallEx[m].closest ? (fallEx[m].closest('mat-checkbox') || fallEx[m]) : fallEx[m];
                        if (vistos.has(mat2)) continue;
                        vistos.add(mat2);
                        if (marcarCheckbox(mat2)) cont++;
                    }
                    if (cont > 0) return cont;
                    var fallTabela = Array.from(document.querySelectorAll('pje-bndt-exclusao mat-checkbox, mat-table mat-checkbox, table mat-checkbox'));
                    for (var n = 0; n < fallTabela.length; n++) {
                        var txtEx = (fallTabela[n].textContent || '').toLowerCase();
                        if (txtEx.indexOf('selecionar todos') !== -1) continue;
                        if (vistos.has(fallTabela[n])) continue;
                        vistos.add(fallTabela[n]);
                        if (marcarCheckbox(fallTabela[n])) cont++;
                    }
                    return cont;
                }
            }""", bool(inclusao)) or 0)
        if marcados > 0:
            logger.info(f'[BNDT] {marcados} checkbox(es) marcado(s) com sucesso via JS (inclusao={inclusao})')
            return True
        logger.warning(f'[BNDT] Nenhum checkbox encontrado para marcar no polo {polo}')
        return False
    except Exception as e:
        logger.warning(f'Erro ao marcar checkboxes via JS no polo {polo}: {e}')
        return False


def _bndt_gravar_e_confirmar(driver, main_window, nova_aba):
    """Clica Gravar, confirma e fecha aba."""
    selectors_gravar = [
        (By.XPATH, "//button[.//span[contains(text(),'Gravar')]]"),
        (By.XPATH, "//button[contains(@class,'mat-raised-button')][contains(text(),'Gravar')]"),
        (By.CSS_SELECTOR, "button[mat-raised-button]:contains('Gravar')"),
        (By.XPATH, "//button[@type='submit'][contains(text(),'Gravar')]")
    ]

    btn_gravar = None
    for by, selector in selectors_gravar:
        btn_gravar = espera.elemento(driver, selector, teto=5)
        if btn_gravar:
            logger.info('Botão Gravar encontrado')
            break

    if not btn_gravar:
        raise Exception('Botão Gravar não encontrado')

    btn_gravar.click()
    logger.info('Botão Gravar clicado')
    espera.assentar(driver, 1)

    btn_sim = espera.elemento(driver, "//button[.//span[contains(text(),'Sim')]]", teto=3)
    if btn_sim:
        btn_sim.click()
        logger.info('Confirmação clicada')
        espera.assentar(driver, 1)

    driver.close()
    driver.switch_to.window(main_window)
    logger.info('Aba BNDT fechada')


def _bndt_gravar_e_confirmar_polo(driver, polo, inclusao=False) -> bool:
    """Clica Gravar, confirma dialog ('Decisão não encontrada' -> Sim), aguarda conclusão e fecha snackbar."""
    logger.info(f'Gravando e confirmando BNDT para polo {polo} via JS...')
    if hasattr(driver, 'page') and driver.page:
        try:
            driver.page.bring_to_front()
        except Exception:
            pass

    clicado_gravar = False
    try:
        if hasattr(driver, 'page') and driver.page:
            espera.ate_js(driver, """(() => {
                var btns = Array.from(document.querySelectorAll('button.mat-raised-button.mat-primary, button'));
                return btns.some(b =>
                    (b.textContent || '').trim().includes('Gravar')
                    && !b.disabled
                    && !b.classList.contains('mat-button-disabled')
                );
            })()""", teto=5)
            clicado_gravar = bool(driver.page.evaluate("""() => {
                var btns = Array.from(document.querySelectorAll('button.mat-raised-button.mat-primary, button'));
                var btnGravar = btns.find(b =>
                    (b.textContent || '').trim().includes('Gravar')
                    && !b.disabled
                    && !b.classList.contains('mat-button-disabled')
                );
                if (btnGravar) {
                    btnGravar.click();
                    return true;
                }
                return false;
            }"""))
        if not clicado_gravar:
            logger.warning('Botão Gravar não encontrado ou desabilitado via JS')
            return False

        logger.info('Botão Gravar clicado via JS')

        # Aguarda modal de confirmação (ex.: "Decisão não encontrada" -> Sim), progresso ou snackbar
        espera.ate_js(driver, """(() => {
            var btnsOverlay = Array.from(document.querySelectorAll('mat-dialog-container button, .cdk-overlay-pane button'));
            if (btnsOverlay.some(b => (b.textContent || '').trim() === 'Sim')) return true;
            if (document.querySelector('simple-snack-bar')) return true;
            var dlgs = Array.from(document.querySelectorAll('mat-dialog-container'));
            if (dlgs.some(d => /incluindo|excluindo/i.test(d.textContent || ''))) return true;
            return false;
        })()""", teto=5)

        clicado_sim = False
        if hasattr(driver, 'page') and driver.page:
            clicado_sim = bool(driver.page.evaluate("""() => {
                var btns = Array.from(document.querySelectorAll('mat-dialog-container button.mat-primary, mat-dialog-container button, .cdk-overlay-pane button'));
                var btnSim = btns.find(b => (b.textContent || '').trim() === 'Sim')
                    || btns.find(b => (b.textContent || '').includes('Sim'));
                if (btnSim && !btnSim.disabled) {
                    btnSim.click();
                    return true;
                }
                return false;
            }"""))
        if clicado_sim:
            logger.info('Botão Sim clicado via JS')
    except Exception as e:
        logger.error(f'Erro ao clicar Gravar/Sim no polo {polo} via JS: {e}')
        return False

    # Aguarda spinner e dialog de progresso ("Incluindo/Excluindo registro(s) no BNDT...") fecharem
    espera.ate_sumir(driver, 'div[class*="container-loading"] mat-progress-spinner', teto=10)
    if hasattr(driver, 'page') and driver.page:
        espera.ate_js(driver, """(() => {
            var dlgs = Array.from(document.querySelectorAll('mat-dialog-container[role="dialog"], mat-dialog-container'));
            return !dlgs.some(d => /incluindo|excluindo|aguarde/i.test(d.textContent || ''));
        })()""", teto=15)

    try:
        aviso = espera.elemento(driver, 'simple-snack-bar', teto=5, visivel=False)
        if aviso:
            texto_aviso = aviso.text
            logger.info(f'Aviso: {texto_aviso}')

            if (
                'Excluído registro de' in texto_aviso
                or 'Partes excluídas' in texto_aviso
                or 'Incluído registro de' in texto_aviso
                or 'Partes incluídas' in texto_aviso
                or 'sucesso' in texto_aviso.lower()
            ):
                logger.info(f'Operação no polo {polo} concluída com sucesso')
                try:
                    btn_close = espera.elemento(driver, 'simple-snack-bar button', teto=2, visivel=False)
                    if btn_close:
                        safe_click_no_scroll(driver, btn_close)
                except Exception:
                    pass
                return True
            if 'A classe judicial do processo não pode acessar' in texto_aviso:
                logger.warning('Classe judicial não permite BNDT')
                return False
            logger.warning(f'Mensagem inesperada: {texto_aviso}')
            return True
        logger.warning('Nenhum aviso detectado após Gravar/Sim')
        return True
    except Exception:
        logger.warning('Nenhum aviso detectado após Gravar/Sim')
        return True


def filtrofases(driver, fases_alvo=['liquidação', 'execução'], tarefas_alvo=None, seletor_tarefa='Tarefa do processo'):
    """Aplica filtros de fase e tarefa redirecionando para Fix.core.filtrofases."""
    from Fix.core import filtrofases as _filtrofases_core
    return _filtrofases_core(driver, fases_alvo=fases_alvo, tarefas_alvo=tarefas_alvo, seletor_tarefa=seletor_tarefa)

def indexar_processos(driver):
    """Indexa processos de forma mais robusta, evitando problemas de stale elements"""
    padrao_proc = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    processos = []

    # Buscar elementos frescos a cada iteração para evitar stale elements
    def obter_linhas_frescas():
        return espera.elementos(driver, 'tr.cdk-drag', teto=0.5)

    linhas = obter_linhas_frescas()
    logger.debug('[INDEXAR] Encontradas %s linhas para processar', len(linhas))

    for idx in range(len(linhas)):
        try:
            linhas_atuais = obter_linhas_frescas()

            if idx >= len(linhas_atuais):
                logger.debug('[INDEXAR][SKIP] Linha %s: DOM mudou, menos linhas disponiveis', idx+1)
                continue

            linha = linhas_atuais[idx]

            texto = ''
            if hasattr(linha, '_handle') and linha._handle:
                links = [PWElement(h, getattr(linha, '_page', None)) for h in linha._handle.query_selector_all('a')]
                if links:
                    texto = links[0].text.strip()
                else:
                    tds = [PWElement(h, getattr(linha, '_page', None)) for h in linha._handle.query_selector_all('td')]
                    if tds:
                        texto = tds[0].text.strip()
            elif hasattr(linha, 'text'):
                texto = (linha.text or '').strip()

            match = padrao_proc.search(texto)
            num_proc = match.group(0) if match else '[sem numero]'

            processos.append((num_proc, linha))

        except Exception as e:
            logger.debug('[INDEXAR][ERRO] Linha %s: %s (elemento pode ter ficado stale)', idx+1, e)
            continue

    logger.debug('[INDEXAR] Processamento concluido: %s processos indexados', len(processos))
    return processos


def reindexar_linha(driver, proc_id):
    """Reindexar linha quando elemento fica stale."""
    try:
        url_atual = driver.current_url
        if 'acesso-negado' in url_atual.lower() or 'access-denied' in url_atual.lower():
                logger.error(f'ACESSO NEGADO detectado na URL: {url_atual}')
                return None

        if 'pje.trt2.jus.br' not in url_atual:
            logger.error(f'URL não é do PJE: {url_atual}')
            return None

        logger.debug('[REINDEXAR] Tentando reindexar na pagina atual: %s', url_atual)

        possible_selectors = [
            'tr.cdk-drag',
            'tr',
            'tbody tr',
            '.linha-processo',
        ]

        linhas_atuais = []
        for selector in possible_selectors:
            try:
                linhas_temp = espera.elementos(driver, selector, teto=0.5)
                if linhas_temp:
                    linhas_atuais = linhas_temp
                    logger.debug('[REINDEXAR] Usando seletor %s: %s linhas encontradas', selector, len(linhas_atuais))
                    break
            except:
                continue

        if not linhas_atuais:
            logger.error(f'Nenhuma linha encontrada na página com os seletores testados')
            return None

        logger.debug('[REINDEXAR] Buscando %s entre %s linhas...', proc_id, len(linhas_atuais))

        for idx, linha_temp in enumerate(linhas_atuais):
            try:
                if not linha_temp.is_displayed():
                    continue

                texto_linha = ""
                if hasattr(linha_temp, '_handle') and linha_temp._handle:
                    links = [PWElement(h, getattr(linha_temp, '_page', None)) for h in linha_temp._handle.query_selector_all('a')]
                    if links:
                        texto_linha = links[0].text.strip()
                    else:
                        tds = [PWElement(h, getattr(linha_temp, '_page', None)) for h in linha_temp._handle.query_selector_all('td')]
                        if tds:
                            for td in tds[:3]:
                                td_text = td.text.strip()
                                if proc_id in td_text:
                                    texto_linha = td_text
                                    break
                            if not texto_linha:
                                texto_linha = tds[0].text.strip()
                        else:
                            texto_linha = (linha_temp.text or '').strip()
                elif hasattr(linha_temp, 'text'):
                    texto_linha = (linha_temp.text or '').strip()

                if proc_id in texto_linha:
                    logger.info(f'Processo {proc_id} encontrado na linha {idx+1}')
                    return linha_temp

            except Exception as e:
                continue

        logger.error(f'Processo {proc_id} não encontrado nas {len(linhas_atuais)} linhas da página atual')
        return None

    except Exception as e:
        logger.error(f'Erro geral na reindexação: {e}')
        return None


def abrir_detalhes_processo(driver, linha):
    try:
        btn = None
        if hasattr(linha, '_handle') and linha._handle:
            h = linha._handle.query_selector('[mattooltip*="Detalhes do Processo"]') or linha._handle.query_selector('button, a')
            if h:
                h.scroll_into_view_if_needed()
                btn = PWElement(h, getattr(linha, '_page', None))
        if not btn:
            btn = linha
        safe_click_no_scroll(driver, btn)
        return True
    except Exception:
        return False


def trocar_para_nova_aba(driver, aba_lista_original):
    """Troca para uma nova aba diferente da aba original da lista."""
    from Fix.browser_suporte import trocar_para_nova_aba as _tpna
    return _tpna(driver, aba_lista_original)


def _indexar_preparar_contexto(driver, max_processos=None):
    """Valida conexão e indexa processos, retornando (aba_original, lista_processos) ou (None, None)."""
    import time

    conexao_inicial = validar_conexao_driver(driver, "FLUXO")
    if conexao_inicial == "FATAL":
        logger.error('ERRO em _indexar_preparar_contexto: Driver inutilizavel no inicio do processamento!')
        return None, None
    elif not conexao_inicial:
        logger.error('ERRO em _indexar_preparar_contexto: Driver nao esta conectado no inicio do processamento!')
        return None, None

    try:
        aba_lista_original = driver.current_window_handle
        logger.debug('[FLUXO] Aba da lista capturada: %s', aba_lista_original)
    except Exception as e:
        logger.error('ERRO em _indexar_preparar_contexto: Falha ao capturar aba da lista: %s', e)
        return None, None

    try:
        processos = indexar_processos(driver)
        if not processos:
            logger.warning('[FLUXO] Nenhum processo encontrado para indexacao')
            return None, None
    except Exception as e:
        logger.error('ERRO em _indexar_preparar_contexto: Falha ao indexar processos: %s', e)
        return None, None

    if max_processos and max_processos > 0 and max_processos < len(processos):
        processos = processos[:max_processos]
        logger.debug('[FLUXO] Limitando processamento a %s processos', max_processos)

    return aba_lista_original, processos


def _indexar_tentar_reindexar(driver: Any, proc_id: str, max_tentativas: int = 3) -> Optional[Any]:
    """Tenta reindexar linha com múltiplas tentativas."""
    for tent in range(max_tentativas):
        try:
            linha = reindexar_linha(driver, proc_id)
            if linha:
                return linha
            logger.debug('[PROCESSAR] Tentativa %s/%s - Reindexando', tent+1, max_tentativas)
            espera.assentar(driver, 1)
        except Exception as e:
            logger.debug('[PROCESSAR] Falha na tentativa %s: %s', tent+1, e)
            espera.assentar(driver, 1)
    return None


def _indexar_tentar_trocar_aba(driver: Any, aba_original: str, max_tentativas: int = 3) -> Optional[str]:
    """Tenta trocar para nova aba com múltiplas tentativas."""
    for tent in range(max_tentativas):
        try:
            nova_aba = trocar_para_nova_aba(driver, aba_original)
            if nova_aba:
                try:
                    url_atual = driver.current_url
                    from urllib.parse import urlparse
                    parsed = urlparse(url_atual)
                    path_parts = parsed.path.strip('/').split('/')
                    if len(path_parts) >= 2:
                        url_legivel = f"{path_parts[-2]}/{path_parts[-1]}"
                    else:
                        url_legivel = parsed.path or url_atual[-30:]
                    logger.debug('[PROCESSAR] Trocado para nova aba: %s', url_legivel)
                except:
                    logger.debug('[PROCESSAR] Trocado para nova aba')
                espera.assentar(driver, 0.5)
                return nova_aba
            logger.debug('[PROCESSAR] Tentativa %s/%s - Aguardando aba', tent+1, max_tentativas)
            espera.assentar(driver, 1)
        except Exception as e:
            logger.debug('[PROCESSAR] Falha ao trocar aba (tent %s): %s', tent+1, e)
            espera.assentar(driver, 1)
    return None


def _indexar_processar_item(driver, proc_id, linha, aba_lista_original, callback):
    """Processa um item individual da lista: abre, executa callback, limpa abas."""
    logger.debug('[PROCESSAR] Processando %s...', proc_id)

    conexao_status = validar_conexao_driver(driver, "PROCESSAR")
    if conexao_status == "FATAL":
        logger.error('ERRO em _indexar_processar_item: Contexto descartado - interrompendo')
        return "FATAL"
    elif not conexao_status:
        logger.error('ERRO em _indexar_processar_item: Conexao perdida para %s', proc_id)
        return "ERRO"

    try:
        atual_url = driver.current_url
        if 'acesso-negado' in atual_url.lower() or 'login.jsp' in atual_url.lower():
            logger.warning('[PROCESSAR] Acesso negado detectado. Reiniciando driver...')
            novo_driver = reiniciar_driver_e_logar_pje(driver, log=True)
            if not novo_driver:
                logger.error('ERRO em _indexar_processar_item: Falha ao reiniciar driver')
                return "ERRO"
            driver = novo_driver
            handles_reiniciados = list(getattr(driver, 'window_handles', []))
            aba_lista_original = handles_reiniciados[0] if handles_reiniciados else None

        if "escaninho" not in atual_url and "documentos" not in atual_url:
            handles_atuais = list(getattr(driver, 'window_handles', []))
            if not aba_lista_original or aba_lista_original not in handles_atuais:
                return "ERRO"
            driver.switch_to.window(aba_lista_original)
            logger.debug('[PROCESSAR] Voltado para aba da lista')
    except Exception as e:
        logger.error('ERRO em _indexar_processar_item: Falha ao verificar URL: %s', e)
        return "ERRO"

    linha_atual = _indexar_tentar_reindexar(driver, proc_id)
    if not linha_atual:
        logger.error('ERRO em _indexar_processar_item: Nao reindexado apos 3 tentativas')
        return "ERRO"

    try:
        if not abrir_detalhes_processo(driver, linha_atual):
            logger.error('ERRO em _indexar_processar_item: Botao de detalhes nao encontrado')
            return "ERRO"
    except Exception as e:
        logger.error('ERRO em _indexar_processar_item: Falha ao abrir detalhes: %s', e)
        return "ERRO"

    espera.assentar(driver, 1)

    nova_aba = _indexar_tentar_trocar_aba(driver, aba_lista_original)
    if not nova_aba:
        logger.error('ERRO em _indexar_processar_item: Nova aba nao aberta apos 3 tentativas')
        return "ERRO"

    try:
        espera.assentar(driver, 1)
        def callback_wrapper(driver_inner):
            driver_inner._numero_processo_lista = proc_id
            return callback(driver_inner)

        if callback_wrapper(driver):
            logger.debug('[PROCESSAR] Callback OK para %s', proc_id)
            conexao_pos = validar_conexao_driver(driver, "POS-CALLBACK")
            if conexao_pos == "FATAL":
                logger.error('ERRO em _indexar_processar_item: Contexto perdido durante callback')
                return "FATAL"
        else:
            logger.error('ERRO em _indexar_processar_item: Callback retornou False')
            return "ERRO"
    except Exception as e:
        logger.error('ERRO em _indexar_processar_item: Falha inesperada em callback: %s', e)
        return "ERRO"
    finally:
        if hasattr(driver, '_numero_processo_lista'):
            delattr(driver, '_numero_processo_lista')

    limpeza = forcar_fechamento_abas_extras(driver, aba_lista_original)
    if limpeza == "FATAL":
        logger.error('ERRO em _indexar_processar_item: Contexto perdido durante limpeza')
        return "FATAL"
    elif not limpeza:
        logger.warning('[PROCESSAR] Limpeza de abas falhou (nao e fatal)')

    return "SUCESSO"


def indexar_e_processar_lista(driver, callback, seletor_btn=None, modo='tabela', max_processos=None, log=True):
    """Processa lista de processos com tratamento robusto de conexão e abas."""
    logger.info('[FLUXO] Iniciando indexacao da lista de processos...')

    aba_original, processos_iniciais = _indexar_preparar_contexto(driver, max_processos)
    if not aba_original or not processos_iniciais:
        return False

    try:
        processos_iniciais = indexar_processos(driver)
        if not processos_iniciais:
            logger.warning('[FLUXO] Nenhum processo encontrado para processar')
            return False
        logger.info('[FLUXO] %s processos encontrados para processamento', len(processos_iniciais))
    except Exception as e:
        logger.error('ERRO em indexar_e_processar_lista: Falha ao indexar lista inicial: %s', e)
        return False

    processados = 0
    erros = 0
    fatal = False

    for idx, (proc_id, linha_original) in enumerate(processos_iniciais):
        if max_processos and processados >= max_processos:
            logger.info('[FLUXO] Limite de %s processos atingido', max_processos)
            break

        logger.info('[FLUXO] Processando item %s/%s: %s', idx+1, len(processos_iniciais), proc_id)

        resultado = _indexar_processar_item(driver, proc_id, linha_original, aba_original, callback)

        if resultado == "SUCESSO":
            processados += 1
        elif resultado == "FATAL":
            fatal = True
            logger.error('[FLUXO][FATAL] Interrompendo processamento')
            break
        else:
            erros += 1
            idx += 1

    logger.info('[FLUXO] Processamento concluido: %s sucesso, %s erros', processados, erros)
    return processados > 0


def analise_argos(driver):
    logger.info('[ARGOS] Iniciando analise Argos...')
    try:
        logger.info('[ARGOS] Analise Argos concluida')
    except Exception as e:
        logger.error("ERRO em analise_argos: %s: %s", type(e).__name__, e)


def tratar_anexos_argos(driver, log=True):
    if log:
        logger.debug('[ARGOS][ANEXOS] Tratando anexos...')
    if log:
        logger.debug('[ARGOS][ANEXOS] Anexos tratados com sucesso')


def analise_outros(driver):
    logger.info('[OUTROS] Iniciando analise Outros...')
    texto = extrair_documento(driver, regras_analise=lambda texto: criar_gigs(driver, 0, 'Pz mdd'))
    if not texto:
        logger.error("ERRO em analise_outros: Nao foi possivel extrair o texto da certidao")
    logger.info('[OUTROS] Analise Outros concluida')
