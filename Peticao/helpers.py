"""
Helpers para checagens específicas de regras em Petições Iniciais
Módulo para validações customizadas antes da execução de ações
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from Fix.log import getmodulelogger

logger = getmodulelogger(__name__)

# Import para API calls
from Fix.variaveis_client import PjeApiClient, session_from_driver
from Fix.extracao import extrair_direto, extrair_documento, criar_gigs
from api.variaveis_resolvers import obter_chave_ultimo_despacho_decisao_sentenca


def _buscar_documento_relevante_timeline(driver: WebDriver) -> Tuple[Optional[Any], Optional[Any], str]:
    """
    Busca documento relevante (sentença/decisão/despacho) na timeline via DOM.
    
    Baseado na implementação do p2b_fluxo_documentos.py.
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
            
            # Verificar se o tipo REAL é um dos procurados
            if tipo_real and re.search(r'^(despacho|decisão|sentença)', tipo_real):
                return item, link, tipo_real.title()  # Retorna capitalizado
                
        except Exception:
            continue
    
    return None, None, ""
import re
from typing import Optional, Tuple, Any

def apagar(numero_processo: str, id_processo: str, descricao: str = "", tipo: str = "", id_documento: str = ""):
    """
    Registra processo no arquivo delete.js para não ser processado.
    Formato: {numero_processo: [{id, id_doc, tipo, desc}]}
    id_doc = ID do documento (fingerprint definitivo via href do a[accesskey='v'])
    tipo → span.texto-preto | desc → a[accesskey='v'] span (fallback quando id_doc ausente)
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
                    delete_processes = json.loads(match.group(1))
            except Exception:
                pass

        nova_entrada = {"id": id_processo, "id_doc": str(id_documento) if id_documento else "", "tipo": tipo, "desc": descricao}

        existente = delete_processes.get(numero_processo)
        if existente is None:
            # Nova chave
            delete_processes[numero_processo] = [nova_entrada]
        elif isinstance(existente, list):
            # Já no novo formato — evitar duplicata pelo id
            ids = [e.get("id") for e in existente if isinstance(e, dict)]
            if str(id_processo) not in [str(x) for x in ids]:
                existente.append(nova_entrada)
        else:
            # Formato legado (string/número) — migrar para lista, preservando entrada antiga
            delete_processes[numero_processo] = [
                {"id": existente, "desc": ""},
                nova_entrada,
            ]

        # Escrever de volta (sempre acumulando)
        with open(delete_file, 'w', encoding='utf-8') as f:
            f.write("// Arquivo para registrar processos que devem ser \"apagados\" (não processados)\n")
            f.write("// Formato: {numero_processo: [{id, desc}]} — desc = texto do documento (discriminador)\n\n")
            f.write("const delete_processes = ")
            json.dump(delete_processes, f, indent=2, ensure_ascii=False)
            f.write(";\n\nmodule.exports = delete_processes;\n")

    except Exception as e:
        print(f"Erro ao registrar processo no delete.js: {e}")

def checar_habilitacao(item, driver: WebDriver) -> bool:
    """
    Checagem completa para a regra de direitos-habilitação
    Inclui verificação de advogado + verificações de audiência para ato_ceju

    Args:
        item: Item da petição com atributos do processo
        driver: WebDriver para acesso ao PJe

    Returns:
        bool: True se deve executar ato_ceju, False caso contrário
    """
    try:
        numero_processo = getattr(item, 'numero_processo', '')
        if not numero_processo:
            return False

        # 0. Extrair dados do processo (dadosatuais.json)
        from Fix.extracao import extrair_dados_processo
        try:
            extrair_dados_processo(driver, caminho_json='dadosatuais.json', debug=False)
        except Exception as e:
            print(f"Erro ao extrair dados do processo: {e}")
            return False

        # 1. VERIFICAÇÃO DE ADVOGADO (não afeta resultado final)
        def _extrair_texto_peticao():
            """Helper: extrai texto da petição — mesma func que bucket análise"""
            try:
                # Buscar link da petição (PRIMEIRO documento = mais recente)
                link = None
                itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
                for item in itens:  # Do mais recente para o mais antigo
                    try:
                        link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                        break
                    except Exception:
                        continue
                
                if not link:
                    return None
                
                # Clicar e aguardar renderização (padrão pet.py)
                link.click()
                try:
                    from Fix.core import aguardar_renderizacao_nativa
                    aguardar_renderizacao_nativa(driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2)
                except Exception:
                    pass
                
                # Extrair com extrair_direto
                resultado = extrair_direto(driver, timeout=10, debug=False, formatar=True)
                if resultado and resultado.get('sucesso'):
                    raw = resultado.get('conteudo') or resultado.get('conteudo_bruto')
                    if raw:
                        return raw
                
                # Fallback: extrair_documento
                texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=False)
                if texto_tuple and texto_tuple[0]:
                    return texto_tuple[0]
                
                return None
            except Exception as e:
                print(f"Erro ao extrair texto da petição: {e}")
                return None

        def _extrair_nome_assinante(texto_pdf):
            """Helper: extrai nome do assinante da primeira página"""
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
                print(f"Erro ao extrair nome do assinante: {e}")
                return None

        def _extrair_id_doc_peticao():
            """ID numérico da petição selecionada na timeline.
            Selecionada = li.tl-item-container com style contendo background-color (azul claro).
            id do li: 'doc_453562049' → '453562049'.
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
            """Helper: obtém lista de advogados de dadosatuais.json"""
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
                print(f"Erro ao obter lista de advogados: {e}")
                return []

        # Executar verificação de advogado (SEMPRE OCORRE)
        id_doc_peticao = _extrair_id_doc_peticao()
        texto_pdf = _extrair_texto_peticao()
        if texto_pdf:
            nome_assinante = _extrair_nome_assinante(texto_pdf)
            if nome_assinante:
                advogados = _obter_lista_advogados()
                if advogados:
                    assinante_eh_advogado = any(
                        nome_assinante.lower() in advogado_nome.lower() or
                        advogado_nome.lower() in nome_assinante.lower()
                        for advogado_nome in advogados
                    )
                    if assinante_eh_advogado:
                        apagar(numero_processo, getattr(item, 'id_processo', numero_processo), getattr(item, 'descricao', ''), getattr(item, 'tipo_peticao', ''), id_doc_peticao)
                        print(f"Processo {numero_processo} - Assinante {nome_assinante} é advogado válido - REGISTRADO PARA APAGAR")
                    else:
                        try:
                            criar_gigs(driver, "-1", "", "autuação")
                            print(f"Processo {numero_processo} - Assinante {nome_assinante} NÃO é advogado - Criado GIGS de autuação")
                        except Exception as e:
                            print(f"Erro ao criar GIGS de autuação para {numero_processo}: {e}")

        # 2. VERIFICAÇÕES DE AUDIÊNCIA (FILTRO - definem se executa ato_ceju)
        # Verificar se tem ata de audiência via API — APÓS completar verificação de advogado
        tem_ata_audiencia = False
        try:
            sess, trt = session_from_driver(driver)
            client = PjeApiClient(sess, trt)
            id_processo = client.id_processo_por_numero(numero_processo)
            if not id_processo:
                print(f"Não foi possível obter ID do processo: {numero_processo}")
                id_processo = getattr(item, 'id_processo', numero_processo)
            
            if id_processo:
                timeline = client.timeline(id_processo, buscarDocumentos=True, buscarMovimentos=False)
                if timeline:
                    for doc in timeline:
                        titulo = doc.get('titulo', '').lower()
                        if 'ata' in titulo and 'audiência' in titulo:
                            tem_ata_audiencia = True
                            apagar(numero_processo, id_processo, getattr(item, 'descricao', ''), getattr(item, 'tipo_peticao', ''), id_doc_peticao)
                            print(f"Processo {numero_processo} tem ata de audiência - não processar")
                            break  # Interrompe a busca de documentos
        except Exception as e:
            print(f"Aviso: Erro ao verificar ata de audiência via API: {e}")

        # Se tem ata de audiência, retorna False (não executa ato_ceju) após completar advogado
        if tem_ata_audiencia:
            return False

        # Extração de conteúdo usando Fix.extracao (padrão p2b/analise_pet)
        try:
            resultado = extrair_direto(driver, timeout=10, debug=False, formatar=True)
            if resultado and resultado.get('sucesso'):
                if resultado.get('conteudo'):
                    texto = resultado['conteudo'].lower()
                elif resultado.get('conteudo_bruto'):
                    texto = resultado['conteudo_bruto'].lower()
                else:
                    texto = None
            else:
                texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=False)
                if texto_tuple and texto_tuple[0]:
                    texto = texto_tuple[0].lower()
                else:
                    texto = None
            if not texto:
                print(f"Processo {numero_processo} - falha na extração de texto/documento")
                return False
            # ...restante da lógica original...
        except Exception as e:
            print(f"Erro ao extrair texto/documento na checagem de habilitação: {e}")
            return False

    except Exception as e:
        print(f"Erro na checagem de habilitação: {e}")
        return False


def agravo_peticao(item, driver: WebDriver) -> bool:
    """
    Processa Agravo de Petição: busca documento relevante na timeline via DOM
    e executa ato apropriado baseado no conteúdo.
    
    Fluxo:
    1. Buscar documento relevante (sentença/decisão/despacho) na timeline
    2. Se sentença: extrair conteúdo e verificar por "defiro" ou "indefiro" + "desconsideração"
    3. Executar ato correspondente
    """
    logger.info(f'[AGPET] Iniciando processamento de agravo de petição: {item.numero_processo}')
    
    # 1. Buscar documento relevante na timeline via DOM
    doc_encontrado, doc_link, tipo_documento = _buscar_documento_relevante_timeline(driver)
    
    if not doc_encontrado or not doc_link:
        logger.warning(f'[AGPET] Nenhum documento relevante encontrado na timeline')
        return False
    
    logger.info(f'[AGPET] Documento relevante encontrado: {tipo_documento}')
    
    # 2. Se for sentença, extrair conteúdo para análise
    if tipo_documento.lower() == 'sentença':
        # Clicar no documento e aguardar carregamento
        doc_link.click()
        try:
            from Fix.core import aguardar_renderizacao_nativa
            aguardar_renderizacao_nativa(driver, '.timeline, .document-viewer, div.tl-item-container', timeout=2)
        except Exception:
            import time
            time.sleep(2)
        
        # Extrair conteúdo usando extrair_direto
        texto = None
        try:
            resultado_direto = extrair_direto(driver, timeout=10, debug=False, formatar=True)
            
            if resultado_direto and resultado_direto.get('sucesso'):
                if resultado_direto.get('conteudo'):
                    texto = resultado_direto['conteudo'].lower()
                elif resultado_direto.get('conteudo_bruto'):
                    texto = resultado_direto['conteudo_bruto'].lower()
        except Exception as e:
            logger.warning(f'[AGPET] Erro na extração DIRETA: {e}')
        
        # Fallback para extrair_documento se extrair_direto falhar
        if not texto:
            try:
                texto_tuple = extrair_documento(driver, regras_analise=None, timeout=10, log=False)
                if texto_tuple and texto_tuple[0]:
                    texto = texto_tuple[0].lower()
            except Exception as e:
                logger.warning(f'[AGPET] Erro na extração DOCUMENTO: {e}')
        
        if not texto:
            logger.error(f'[AGPET] Não foi possível extrair texto da sentença')
            return False
        
        # 3. Verificar conteúdo da sentença
        texto_normalizado = texto.lower()
        
        # Verificar se contém "defiro" ou "indefiro" + "desconsideração"
        if 'desconsideração' in texto_normalizado:
            if 'defiro' in texto_normalizado or 'indefiro' in texto_normalizado:
                logger.info(f'[AGPET] Sentença contém decisão sobre desconsideração - executando ato_agpetidpj')
                try:
                    from atos.wrappers_ato import ato_agpetidpj
                    ato_agpetidpj(driver)
                    logger.info(f'[AGPET] ato_agpetidpj executado com sucesso')
                    return True
                except Exception as e:
                    logger.error(f'[AGPET] Erro ao executar ato_agpetidpj: {e}')
                    return False
            else:
                logger.info(f'[AGPET] Sentença menciona desconsideração mas sem decisão clara')
        
        # Demais casos de sentença
        logger.info(f'[AGPET] Sentença sem decisão específica sobre desconsideração - executando ato_agpet')
        try:
            from atos.wrappers_ato import ato_agpet
            ato_agpet(driver)
            logger.info(f'[AGPET] ato_agpet executado com sucesso')
            return True
        except Exception as e:
            logger.error(f'[AGPET] Erro ao executar ato_agpet: {e}')
            return False
    
    # 4. Para decisões e despachos, executar ato_agpinter
    else:
        logger.info(f'[AGPET] Documento é {tipo_documento} - executando ato_agpinter')
        try:
            from atos.wrappers_ato import ato_agpinter
            ato_agpinter(driver)
            logger.info(f'[AGPET] ato_agpinter executado com sucesso')
            return True
        except Exception as e:
            logger.error(f'[AGPET] Erro ao executar ato_agpinter: {e}')
            return False