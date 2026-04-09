# Extração de Texto de Documentos PJe via API
#
# Leitura de PDFs diretamente do endpoint `conteudo` da API PJe,
# sem navegador visível e sem IA — com fallback automático para OCR
# quando o PDF for escaneado (imagem).
#
# ---
#
# ## Dependências
#
# pip install pdfplumber pytesseract pdf2image requests
# Também necessário: Tesseract-OCR instalado no sistema
# Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-por
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
#
# ---
#
# ## Reutilizar Sessão Autenticada do Driver
#
# O Firefox do PJePlus já está autenticado. Basta exportar os cookies:
#
# import requests
#
# def sessao_do_driver(driver) -> requests.Session:
#     """Cria sessão requests reutilizando cookies ativos do driver."""
#     sessao = requests.Session()
#     sessao.headers.update({
#         'User-Agent': driver.execute_script("return navigator.userAgent;")
#     })
#     for cookie in driver.get_cookies():
#         sessao.cookies.set(cookie['name'], cookie['value'])
#     return sessao
#
# ---
#
# ## Extração com Fallback para OCR
#
# import io
# import pdfplumber
# import pytesseract
# from pdf2image import convert_from_bytes
# from PIL import Image
#
# LIMIAR_CHARS_POR_PAGINA = 30
#
# def _extrair_texto_nativo(pdf_bytes: bytes) -> tuple[str, int]:
#     textos = []
#     total = 0
#     with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
#         total = len(pdf.pages)
#         for pagina in pdf.pages:
#             t = pagina.extract_text()
#             if t:
#                 textos.append(t)
#     return '\n'.join(textos).strip(), total
#
# def _extrair_texto_ocr(pdf_bytes: bytes, lang: str = 'por') -> str:
#     imagens = convert_from_bytes(pdf_bytes, dpi=300)
#     textos = []
#     for i, img in enumerate(imagens):
#         t = pytesseract.image_to_string(img, lang=lang)
#         if t.strip():
#             textos.append(t)
#         print(f"[OCR] Página {i+1}/{len(imagens)} processada | chars={len(t)}")
#     return '\n'.join(textos).strip()
#
# def _e_pdf_escaneado(texto_nativo: str, total_paginas: int) -> bool:
#     if total_paginas == 0:
#         return True
#     media = len(texto_nativo) / total_paginas
#     return media < LIMIAR_CHARS_POR_PAGINA
#
# def extrair_texto_documento_api(
#     sessao: requests.Session,
#     id_processo: str,
#     id_doc: str,
#     forcar_ocr: bool = False,
#     lang_ocr: str = 'por'
# ) -> dict:
#     resultado = {
#         'texto': '',
#         'metodo': 'erro',
#         'paginas': 0,
#         'chars': 0,
#         'id_doc': id_doc,
#         'id_processo': id_processo,
#     }
#     url = (
#         f"https://pje.trt2.jus.br/pjekz/api/processos/{id_processo}"
#         f"/documentos/{id_doc}/conteudo"
#     )
#     try:
#         print(f"[EXTRACAO] Baixando doc={id_doc} processo={id_processo}")
#         resp = sessao.get(url, timeout=60)
#         resp.raise_for_status()
#         content_type = resp.headers.get('Content-Type', '')
#         if 'pdf' not in content_type:
#             print(f"[EXTRACAO] Tipo inesperado: {content_type}")
#             return resultado
#         pdf_bytes = resp.content
#         print(f"[EXTRACAO] PDF recebido | tamanho={len(pdf_bytes):,} bytes")
#         if not forcar_ocr:
#             texto_nativo, total_paginas = _extrair_texto_nativo(pdf_bytes)
#             resultado['paginas'] = total_paginas
#             if not _e_pdf_escaneado(texto_nativo, total_paginas):
#                 print(f"[EXTRACAO] Método: NATIVO | páginas={total_paginas} | chars={len(texto_nativo)}")
#                 resultado.update(texto=texto_nativo, metodo='nativo', chars=len(texto_nativo))
#                 return resultado
#             print(f"[EXTRACAO] PDF-imagem detectado (média chars/pág baixa) → acionando OCR")
#         texto_ocr = _extrair_texto_ocr(pdf_bytes, lang=lang_ocr)
#         resultado.update(texto=texto_ocr, metodo='ocr', chars=len(texto_ocr))
#         print(f"[EXTRACAO] Método: OCR | chars={len(texto_ocr)}")
#         return resultado
#     except Exception as e:
#         print(f"[EXTRACAO] Erro ao extrair doc {id_doc}: {e}")
#         return resultado
#
# ---
#
# ## Iterar Todos os Documentos de um Processo
#
# def extrair_todos_documentos(
#     sessao: requests.Session,
#     id_processo: str,
#     documentos: list[dict],
#     apenas_tipos: list[str] | None = None
# ) -> list[dict]:
#     resultados = []
#     for doc in documentos:
#         if apenas_tipos and doc.get('tipo') not in apenas_tipos:
#             continue
#         print(f"\n[EXTRACAO] → {doc.get('tipo')} | {doc.get('titulo')}")
#         r = extrair_texto_documento_api(sessao, id_processo, str(doc['id']))
#         r['tipo'] = doc.get('tipo', '')
#         r['titulo'] = doc.get('titulo', '')
#         resultados.append(r)
#     return resultados
#
# ---
#
# ## Exemplo de Uso Completo
#
# sessao = sessao_do_driver(driver)
# resultado = extrair_texto_documento_api(sessao, '8463218', '453355283')
# print(f"Método: {resultado['metodo']}")
# print(f"Páginas: {resultado['paginas']}")
# print(f"Chars: {resultado['chars']}")
# print(resultado['texto'][:500])
# todos = extrair_todos_documentos(sessao, '8463218', lista_documentos_api)
# termo = 'horas extras'
# for doc in todos:
#     if termo.lower() in doc['texto'].lower():
#         print(f"✅ '{termo}' encontrado em: {doc['titulo']} ({doc['tipo']})")
#
# ---
#
# ## Notas Operacionais
#
# | Situação | Comportamento |
# |---|---|
# | PDF digital (texto embutido) | `pdfplumber` extrai em < 1s |
# | PDF escaneado (imagem) | OCR com `dpi=300` — ~3-8s por página |
# | PDF protegido / corrompido | Retorna `metodo='erro'` sem lançar exceção |
# | `forcar_ocr=True` | Ignora pdfplumber, vai direto ao Tesseract |
# | Múltiplos idiomas | `lang_ocr='por+eng'` para documentos mistos |
#
# Sessão e cookies: os cookies do PJe expiram junto com a sessão do navegador. Se o driver for reiniciado, chame `sessao_do_driver(driver)` novamente antes de fazer novas requisições.
"""
f.py - Script de Teste Rápido com estrutura fixa
===================================================

ESTRUTURA FIXA (NÃO MODIFICAR):
1. Escolha de Driver PJE (VT ou PC) - sempre visível
2. Login CPF
3. URL de navegação
4. Funções de teste (modificar apenas esta seção)

Uso:
    py f.py
    >> Escolha: [V] VT ou [P] PC
"""

import sys
import io
import os
import time
import logging
import re
import traceback
from datetime import datetime

from api.variaveis import PjeApiClient, session_from_driver

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# Configurar logging para capturar logs de Fix.* durante execução do f.py
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Apenas INFO e acima globalmente
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')

# Stream handler (stdout) - apenas INFO
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
sh.setLevel(logging.INFO)
logger.addHandler(sh)

# File handler - apenas INFO
try:
    fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), 'f_py_debug.log'), encoding='utf-8')
    fh.setFormatter(formatter)
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)
except Exception:
    pass

# Silenciar logs extremamente verbose de selenium e urllib3
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('selenium.webdriver').setLevel(logging.WARNING)
logging.getLogger('selenium.webdriver.remote').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)


# Flag de controle (idêntico ao x.py)
skip_finalizar = False

# ============================================================================
# SEÇÃO 1: CONFIGURAÇÕES DE NAVEGAÇÃO (MODIFICAR AQUI)
# ============================================================================

# URL para navegar após login (caso de teste solicitado)
URL_NAVEGACAO = "https://pje.trt2.jus.br/pjekz/processo/8481068/detalhe"
URL_NAVEGACAO_PAINEL_GLOBAL_8 = "https://pje.trt2.jus.br/pjekz/painel/global/8/lista-processos"


# ============================================================================
# SEÇÃO 3: FUNÇÕES DE TESTE (MODIFICAR AQUI CONFORME NECESSÁRIO)
# ============================================================================

def executar_ciclo3_debug(driver_pje):
    """DEBUG PRAZO: testa apenas seleção de não-livres e movimentação para providências."""
    from Prazo.loop_ciclo2_selecao import _ciclo2_aplicar_filtros
    from Prazo.loop_ciclo2_processamento import ciclo2_loop_providencias
    from Fix.core import aguardar_renderizacao_nativa

    print("\n[DEBUG] Navegando para painel global 8 (ciclo2)")
    driver_pje.get(URL_NAVEGACAO_PAINEL_GLOBAL_8)
    try:
        aguardar_renderizacao_nativa(driver_pje, 'span.total-registros', timeout=15)
    except Exception:
        pass

    print("[DEBUG] Aplicando filtros ciclo2")
    if not _ciclo2_aplicar_filtros(driver_pje):
        print("[DEBUG][ERRO] _ciclo2_aplicar_filtros retornou False")
        return False

    print("[DEBUG] Iniciando ciclo 3: seleção de não-livres + movimentação em lote")
    resultado = ciclo2_loop_providencias(driver_pje, 'Cumprimento de providências')
    print(f"[DEBUG] ciclo 3 concluído: {'sucesso' if resultado else 'falha'}")
    return resultado


def _extrair_id_processo_da_url(url):
    if not url:
        return None
    match = re.search(r"/processo/(\d+)(?:/|$)", url)
    return match.group(1) if match else None


def _normalizar_texto_documento(valor):
    return (valor or '').strip().lower()


def _listar_documentos_timeline(timeline):
    documentos = []
    for item in timeline or []:
        if not isinstance(item, dict):
            continue
        documentos.append(item)
        for anexo in item.get('anexos') or []:
            if isinstance(anexo, dict):
                documentos.append(anexo)
    return documentos


def _eh_peticao_inicial(documento):
    tipo = _normalizar_texto_documento(documento.get('tipo'))
    titulo = _normalizar_texto_documento(documento.get('titulo'))
    return 'petição inicial' in tipo or 'peticao inicial' in tipo or 'petição inicial' in titulo or 'peticao inicial' in titulo


def _resumir_documento(documento):
    anexos = documento.get('anexos') or []
    return {
        'tipo': documento.get('tipo'),
        'titulo': documento.get('titulo'),
        'id': documento.get('id'),
        'idUnicoDocumento': documento.get('idUnicoDocumento'),
        'idDocumentoPai': documento.get('idDocumentoPai'),
        'anexos': len(anexos) if isinstance(anexos, list) else 0,
    }


def _sondar_endpoint_documento(client, id_processo, id_documento, sufixo):
    url = client._url(f"/pje-comum-api/api/processos/id/{id_processo}/documentos/id/{id_documento}/{sufixo}")
    resposta = client.sess.get(url, timeout=15)
    content_type = resposta.headers.get('Content-Type', '')
    corpo_json = None
    corpo_texto = ''
    try:
        corpo_json = resposta.json()
    except Exception:
        corpo_texto = resposta.text or ''
    return {
        'url': url,
        'ok': resposta.ok,
        'status': resposta.status_code,
        'content_type': content_type,
        'json': corpo_json,
        'texto_inicio': corpo_texto[:500] if corpo_texto else '',
        'texto_tamanho': len(corpo_texto) if corpo_texto else 0,
    }




# ============================================================================
# EXECUÇÃO PRINCIPAL (NÃO MODIFICAR)
# ============================================================================

def main():
    """Execução principal - PC em modo headless."""
    global skip_finalizar


# ============================================================================
# EXECUÇÃO PRINCIPAL (NÃO MODIFICAR)
# ============================================================================

def main():
    """Execução principal - PC em modo headless."""
    global skip_finalizar

    from Fix.drivers import driver_session





# ============================================================================
# EXECUÇÃO PRINCIPAL (NÃO MODIFICAR)
# ============================================================================

def main():
    """Execução principal - PC em modo headless."""
    global skip_finalizar

    from Fix.drivers import driver_session
    driver = None

    try:
        print("=" * 80)
        print("F.PY - SCRIPT DE TESTE RÁPIDO")
        print("=" * 80)
        print(f" Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f" Ambiente: PC + Headless")
        print("=" * 80)

        driver_type_str = "PC"
        headless = False

        with driver_session(driver_type_str, headless=headless) as driver:
            # Login
            from Fix.utils import login_cpf
            if not login_cpf(driver):
                print(" Falha no login")
                return
            try:
                print(f"\n Navegando para: {URL_NAVEGACAO}")
                driver.get(URL_NAVEGACAO)

                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By

                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    print(" Página carregada")
                except Exception as e:
                    print(f" Aviso: Página pode não ter carregado completamente: {e}")

                # Executar triagem completa após login e navegação (seguir fluxo de aud.py)
                from tr import triagem_peticao
                from Fix.gigs import criar_comentario
                
                processo_info = {}
                
                try:
                    print("\n[TRIAGEM] Executando triagem_peticao(driver)...")
                    processo_info['triagem'] = triagem_peticao(driver)
                except Exception as e:
                    processo_info['triagem'] = f"ERRO: falha ao executar triagem: {e}"
                    print(f"[TRIAGEM] ⚠️ Falha ao executar triagem: {e}")

                try:
                    triagem = processo_info.get('triagem')
                    if triagem:
                        print(f"\n[TRIAGEM] Resultado da triagem:")
                        print(triagem)
                        print(f"\n[TRIAGEM] Registrando comentário da triagem...")
                        criar_comentario(driver, triagem)
                        print(f"[TRIAGEM] ✓ Comentário da triagem registrado com sucesso")
                except Exception as e:
                    print(f"[TRIAGEM] ⚠️ Falha ao registrar comentário da triagem: {e}")
                    print(f"[TRIAGEM] triagem tipo={type(triagem).__name__} tamanho={len(triagem) if isinstance(triagem, str) else 'N/A'}")
                    traceback.print_exc()

                print("\n" + "=" * 80)
                print("TESTE CONCLUÍDO - encerrando em modo headless...")

            except KeyboardInterrupt:
                print("\n Interrompido (Ctrl+C) — finalizando imediatamente")
                try:
                    import logging as _logging
                    _logging.getLogger('urllib3.connectionpool').disabled = True
                    _logging.getLogger('urllib3').setLevel(_logging.CRITICAL)
                    from Fix.core import finalizar_driver_imediato as finalizar_driver_imediato_fix
                    finalizar_driver_imediato_fix(driver)
                except Exception:
                    pass
                os._exit(0)
            except Exception as e:
                print(f" Erro: {e}")
                traceback.print_exc()

    except KeyboardInterrupt:
        print("\n Interrompido pelo usuário — finalizando imediatamente")
        try:
            import logging as _logging
            _logging.getLogger('urllib3.connectionpool').disabled = True
            _logging.getLogger('urllib3').setLevel(_logging.CRITICAL)
            from Fix.core import finalizar_driver_imediato as finalizar_driver_imediato_fix
            finalizar_driver_imediato_fix(driver)
        except Exception:
            pass
        os._exit(0)
    except Exception as e:
        print(f" Erro fatal: {e}")
        traceback.print_exc()
    finally:
        # Driver mantido aberto para inspeção manual
        pass


if __name__ == "__main__":
    main()
