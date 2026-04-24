import logging
logger = logging.getLogger(__name__)

# m1.py
# Fluxo automatizado de mandados PJe TRT2
###DIRETRIZES MÁXIMAS INEGOCIÁVEIS
# Priorizar edições apenas no código selecionado ou referenciado  
# Sempre validar se as alterações propostas estão estritamente alinhadas com o prompt do usuário.  
# Evitar modificações em arquivos não explicitamente mencionados.  
# Respeitar convenções de estilo definidas no projeto (ex: indentação com tabs, aspas duplas).  
# Workspace preference: NÃO altere, traduza ou reescreva NENHUMA linha do código, exceto exatamente o trecho solicitado.
# NÃO traduza palavras-chave, nomes de variáveis, comentários, strings, nem nada do código.
# NÃO faça ajustes automáticos, refatorações, nem ‘melhorias’ não solicitadas.
# Se precisar editar, use sempre o padrão # ...existing code... para indicar partes não alteradas. 
# As edições devem ser ESPECIFICAMENTE sobre erros de log ou pedidos EXPLICITOS do usuario, nada alem disso.
# tenha em mente que descumprir essas diretizes estraga o codigo e causa perda de tempo
# nao é neceasário varrer o codigo todo para cada edição pedida 
# use a busca de termos para ir diretamente à região correta e edirtar apenas o necessário, para ser mais eficiente
# ====================================================
# BLOCO 0 - GERAL
# ====================================================

# 0. Importações Padrão
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from typing import Optional, Dict, List, Union, Tuple, Callable, Any

# Selenium
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
)

# ===== IMPORTS PESADOS REMOVIDOS (LAZY LOADING) =====
# Movidos para cache sob demanda para carregamento 8-10x mais rápido

# Cache de módulos para lazy loading
_mandado_regras_modules_cache = {}

def _lazy_import_mandado_regras():
    """Carrega módulos pesados sob demanda (lazy loading)."""
    global _mandado_regras_modules_cache
    
    if not _mandado_regras_modules_cache:
        from Fix.utils import navegar_para_tela
        from Fix.core import buscar_seletor_robusto, buscar_documento_argos
        from Fix.extracao import extrair_pdf, analise_outros, extrair_documento, extrair_dados_processo, buscar_mandado_autor, buscar_ultimo_mandado, extrair_destinatarios_decisao, indexar_e_processar_lista
        from Fix.gigs import criar_gigs
        from Fix.selenium_base import esperar_elemento, aguardar_e_clicar
        from Fix.utils import limpar_temp_selenium, configurar_recovery_driver
        
        _mandado_regras_modules_cache.update({
            'navegar_para_tela': navegar_para_tela,
            'extrair_pdf': extrair_pdf,
            'analise_outros': analise_outros,
            'extrair_documento': extrair_documento,
            'criar_gigs': criar_gigs,
            'esperar_elemento': esperar_elemento,
            'aguardar_e_clicar': aguardar_e_clicar,
            'buscar_seletor_robusto': buscar_seletor_robusto,
            'limpar_temp_selenium': limpar_temp_selenium,
            'indexar_e_processar_lista': indexar_e_processar_lista,
            'extrair_dados_processo': extrair_dados_processo,
            'buscar_documento_argos': buscar_documento_argos,
            'buscar_mandado_autor': buscar_mandado_autor,
            'buscar_ultimo_mandado': buscar_ultimo_mandado,
            'extrair_destinatarios_decisao': extrair_destinatarios_decisao,
            'configurar_recovery_driver': configurar_recovery_driver,
        })
    
    return _mandado_regras_modules_cache

# Módulos Locais (mantidos leves)
from Fix.utils import verificar_e_tratar_acesso_negado_global, handle_exception_with_recovery
from Fix.selenium_base import preencher_campo
from Fix.extracao import salvar_destinatarios_cache
from Fix.abas import validar_conexao_driver
from Fix.extracao import criar_lembrete_posit
from Prazo.p2b_core import checar_prox
from .atos_wrapper import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    pec_idpj,
    mov_arquivar,
    ato_meiosub
)

with open("log.py", "w", encoding="utf-8") as f:
    f.write(f"# Última execução: {datetime.now()}\n")
    f.write(f"# Script: {os.path.abspath(sys.argv[0])}\n")
    f.write(f"# Argumentos: {' '.join(sys.argv[1:])}\n")


def _normalizar_texto_match(valor: str) -> str:
    if not valor:
        return ''
    txt = unicodedata.normalize('NFD', str(valor)).encode('ascii', 'ignore').decode('ascii').lower()
    txt = re.sub(r'[^a-z0-9\s]', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt


def _carregar_reus_dadosatuais(debug: bool = False) -> List[Dict[str, str]]:
    """Carrega reclamadas/reclamados de dadosatuais.json para cruzamento de destinatários."""
    try:
        caminho = os.path.join(os.getcwd(), 'dadosatuais.json')
        if not os.path.exists(caminho):
            if debug:
                logger.info('[ARGOS][IDPJ][DEST] dadosatuais.json não encontrado')
            return []

        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        reus = dados.get('reu', []) or []
        resultado = []
        for item in reus:
            nome = (item or {}).get('nome', '')
            cpfcnpj = (item or {}).get('cpfcnpj', '')
            if nome:
                resultado.append({'nome': nome, 'cpfcnpj': cpfcnpj})

        if debug:
            logger.info(f'[ARGOS][IDPJ][DEST] Reús carregados de dadosatuais.json: {len(resultado)}')
        return resultado

    except Exception as e:
        if debug:
            logger.info(f'[ARGOS][IDPJ][DEST] Falha ao carregar dadosatuais.json: {e}')
        return []


def _identificar_destinatarios_idpj(texto_documento: str, debug: bool = False) -> List[Dict[str, str]]:
    """
    Identifica destinatários da decisão IDPJ cruzando nomes no texto com dadosatuais.json.

    Retorna lista no formato esperado por salvar_destinatarios_cache.
    """
    if not texto_documento:
        return []

    texto_norm = _normalizar_texto_match(texto_documento)
    reus = _carregar_reus_dadosatuais(debug=debug)
    if not reus:
        return []

    # 1) Contexto focal da decisão IDPJ: priorizar parágrafo de providências
    # Ex.: "Providencie a Secretaria da Vara retificação da autuação...".
    # Isso evita detectar nomes que aparecem no cabeçalho do documento.
    contexto_focal = ''

    # Prioridade: parágrafo que inicia com "Providencie a Secretaria" (ou variações)
    try:
        m2 = re.search(r'providencie a secretaria.*?(?:\n\s*\n|$)', texto_norm, flags=re.IGNORECASE | re.DOTALL)
        if m2:
            contexto_focal = m2.group(0)
    except Exception:
        contexto_focal = ''

    # Se não encontrou o parágrafo de providências, tenta padrões clássicos de inclusão
    if not contexto_focal:
        padroes_focais = [
            r'incluir os socios .*? no polo passivo',
            r'inclua se .*? no polo passivo',
            r'incluir os socios .*? em obediencia a ordem',
        ]

        for padrao in padroes_focais:
            try:
                m = re.search(padrao, texto_norm, flags=re.IGNORECASE)
                if m:
                    contexto_focal = m.group(0)
                    break
            except Exception:
                continue

    if debug:
        if contexto_focal:
            logger.info('[ARGOS][IDPJ][DEST] Contexto focal de sócios identificado na decisão')
        else:
            logger.info('[ARGOS][IDPJ][DEST] Contexto focal não encontrado, usando texto completo')

    texto_base_busca = contexto_focal if contexto_focal else texto_norm

    destinatarios = []
    nomes_match = []

    for reu in reus:
        nome = reu.get('nome', '')
        cpfcnpj = reu.get('cpfcnpj', '')
        nome_norm = _normalizar_texto_match(nome)

        if not nome_norm or len(nome_norm) < 5:
            continue

        if nome_norm in texto_base_busca:
            destinatarios.append({
                'nome': nome,
                'cpfcnpj': cpfcnpj,
                'tipo': 'reu',
            })
            nomes_match.append(nome)

    # 2) Fallback: se o contexto focal não capturar destinatários, usa texto completo
    if not destinatarios and contexto_focal:
        for reu in reus:
            nome = reu.get('nome', '')
            cpfcnpj = reu.get('cpfcnpj', '')
            nome_norm = _normalizar_texto_match(nome)

            if not nome_norm or len(nome_norm) < 5:
                continue

            if nome_norm in texto_norm:
                destinatarios.append({
                    'nome': nome,
                    'cpfcnpj': cpfcnpj,
                    'tipo': 'reu',
                })
                nomes_match.append(nome)

        if debug and destinatarios:
            logger.info('[ARGOS][IDPJ][DEST] Fallback no texto completo aplicado')

    if debug:
        logger.info(f'[ARGOS][IDPJ][DEST] Destinatários IDPJ reconhecidos: {len(destinatarios)}')
        if nomes_match:
            logger.info(f"[ARGOS][IDPJ][DEST] Nomes: {', '.join(nomes_match[:6])}")

    return destinatarios

# =========================
# ESTRATEGIAS_ARGOS - Strategy Pattern for Argos document relevance
# =========================
def estrategia_defiro_instauracao(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Regra IDPJ por decisão; SISBAJUD afeta apenas lembrete."""
    txt_lower = texto_documento.lower() if texto_documento else ''
    tipo_norm = unicodedata.normalize('NFD', str(tipo_documento or '')).encode('ascii', 'ignore').decode('ascii').lower()
    if 'decisao' not in tipo_norm:
        return False
    # diagnóstico: verificar presença com e sem normalização de acentos
    normalized = unicodedata.normalize('NFD', texto_documento).encode('ascii', 'ignore').decode('ascii').lower() if texto_documento else ''
    
    # Lista expandida de palavras-chave para detectar IDPJ
    palavras_idpj = [
        'defiro a instauração',
        'defiro a instauracao',
        'deferir a instauração',
        'deferir a instauracao',
        'determino que seja incluído',
        'determino que seja incluida',
        'incidente de desconsideração',
        'incidente de desconsideracao',
        'desconsideração da personalidade jurídica',
        'desconsideracao da personalidade juridica',
        'desconsideração inversa',
        'desconsideracao inversa',
        '855-a',
        'idpj',
        'inclua-se no polo passivo',
        'sócio retirante',
        'socio retirante'
    ]
    
    idpj_detectado = False
    palavra_encontrada = None
    for palavra in palavras_idpj:
        if palavra in txt_lower or palavra in normalized:
            idpj_detectado = True
            palavra_encontrada = palavra
            break
    
    if idpj_detectado:
        def _persistir_destinatarios_idpj() -> None:
            """Persiste destinatários apenas quando a regra IDPJ for efetivamente aplicada."""
            try:
                destinatarios_idpj = _identificar_destinatarios_idpj(texto_documento, debug=debug)
                if destinatarios_idpj:
                    salvar_destinatarios_cache('ATUAL', destinatarios_idpj, origem='argos_idpj_decisao')
                    if debug:
                        logger.info(f'[ARGOS][IDPJ][DEST] Cache atualizado com {len(destinatarios_idpj)} destinatário(s)')
                elif debug:
                    logger.info('[ARGOS][IDPJ][DEST] Nenhum destinatário IDPJ reconhecido no texto')
            except Exception as dest_err:
                if debug:
                    logger.info(f'[ARGOS][IDPJ][DEST] Falha ao salvar destinatários IDPJ: {dest_err}')

        if debug:
            logger.info('[ARGOS][REGRAS] Regra IDPJ reconhecida por decisão')

        _persistir_destinatarios_idpj()

        if resultado_sisbajud == 'positivo':
            if debug:
                logger.info('[ARGOS][REGRAS] SISBAJUD positivo: criando lembrete de bloqueio')
            try:
                titulo_lembrete = 'IDPJcomBloq'
                conteudo_lembrete = 'Processar bloqueios após intimar para pagamento depois do transito do IDPJ.'
                criar_lembrete_posit(driver, titulo_lembrete, conteudo_lembrete, debug=debug)
            except Exception as e:
                if debug:
                    logger.warning(f'[ARGOS][REGRAS][WARN] Falha ao criar lembrete: {e}')
        elif debug:
            logger.info('[ARGOS][REGRAS] SISBAJUD não positivo: sem lembrete, seguindo com pec_idpj')

        try:
            if debug:
                logger.info('[ARGOS][IDPJ] Executando pec_idpj (inclui GIGS xs carta via wrapper)')
            pec_idpj(driver, debug=debug)
        except Exception as e:
            if debug:
                logger.error(f'[ARGOS][REGRAS][ERRO] Falha ao executar pec_idpj: {e}')
        return True
    return False

def estrategia_despacho_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Prioridade: documento com palavra 'ARGOS'"""
    tipo_norm = unicodedata.normalize('NFD', str(tipo_documento or '')).encode('ascii', 'ignore').decode('ascii').lower()
    if 'despacho' not in tipo_norm:
        return False

    if texto_documento and 'argos' in texto_documento.lower():
        if debug:
            logger.info('[ARGOS][REGRAS] NOVA REGRA: Despacho com ARGOS detectado - aplicando regras específicas')
        
        if resultado_sisbajud == 'positivo':
            if debug:
                logger.info('[ARGOS][REGRAS] Ação definida pela regra: ato_bloq')
            if debug:
                logger.info('[ARGOS][REGRAS] Regra despacho+argos reconhecida (SISBAJUD positivo)')
            inicio_ato = time.time()
            try:
                ato_bloq(driver, debug=debug)
            except Exception as e:
                if debug:
                    logger.info(f'[ARGOS][REGRAS][ERRO] ato_bloq falhou: {e}')
            if debug:
                logger.info(f'[ARGOS][REGRAS] ato_bloq finalizado em {time.time() - inicio_ato:.2f}s')
        elif resultado_sisbajud == 'negativo':
            # Quando SISBAJUD é negativo, distinguir se há anexos sigilosos
            if any(v == 'sim' for v in (sigilo_anexos or {}).values()):
                if debug:
                    logger.info('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo com anexo sigiloso, executando ato_termoS')
                if debug:
                    logger.info('[ARGOS][REGRAS] Regra despacho+argos reconhecida (SISBAJUD negativo + sigilo)')
                inicio_ato = time.time()
                try:
                    ato_termoS(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.info(f'[ARGOS][REGRAS][ERRO] ato_termoS falhou: {e}')
                if debug:
                    logger.info(f'[ARGOS][REGRAS] ato_termoS finalizado em {time.time() - inicio_ato:.2f}s')
            else:
                if debug:
                    logger.info('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo sem anexo sigiloso, executando ato_meios')
                if debug:
                    logger.info('[ARGOS][REGRAS] Regra despacho+argos reconhecida (SISBAJUD negativo sem sigilo)')
                inicio_ato = time.time()
                try:
                    ato_meios(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.info(f'[ARGOS][REGRAS][ERRO] ato_meios falhou: {e}')
                if debug:
                    logger.info(f'[ARGOS][REGRAS] ato_meios finalizado em {time.time() - inicio_ato:.2f}s')
        else:
            # Caso de SISBAJUD indefinido ou outro valor — padrão para ato_meios
            if debug:
                logger.info('[ARGOS][REGRAS] Ação padrão (SISBAJUD indefinido): ato_meios')
            inicio_ato = time.time()
            try:
                ato_meios(driver, debug=debug)
            except Exception as e:
                if debug:
                    logger.info(f'[ARGOS][REGRAS][ERRO] ato_meios falhou: {e}')
            if debug:
                logger.info(f'[ARGOS][REGRAS] ato finalizado em {time.time() - inicio_ato:.2f}s')
        return True
    return False

def estrategia_infojud(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Despacho com 'Realize-se a pesquisa INFOJUD'"""
    tipo_norm = unicodedata.normalize('NFD', str(tipo_documento or '')).encode('ascii', 'ignore').decode('ascii').lower()
    if 'despacho' not in tipo_norm:
        return False

    if not texto_documento:
        return False
        
    txt_lower = texto_documento.lower()
    # Normalizar para tratar acentos e espaços extras
    normalized = unicodedata.normalize('NFD', texto_documento).encode('ascii', 'ignore').decode('ascii').lower()
    
    # Variantes da regra de pesquisa INFOJUD (expandida para maior cobertura)
    regras_infojud = [
        'realize-se a pesquisa infojud',
        'realize se a pesquisa infojud',
        'realize-se a pesquisa do infojud',
        'realize se a pesquisa do infojud',
        'realização de pesquisa infojud',
        'realizacao de pesquisa infojud',
        'pesquisa infojud',
        'decred, dimob e e-financeira',
        'através do sistema argos',
        'atraves do sistema argos'
    ]
    
    encontrou = False
    for r in regras_infojud:
        if r in txt_lower or r in normalized:
            encontrou = True
            break
            
    if encontrou:
        if debug:
            logger.info('[ARGOS][REGRAS] Regra despacho+infojud reconhecida')
        
        if any(v == 'sim' for v in sigilo_anexos.values()):
            inicio_ato = time.time()
            try:
                ato_termoS(driver, debug=debug)
            except Exception as e:
                if debug:
                    logger.error(f'[ARGOS][REGRAS][ERRO] ato_termoS falhou: {e}')
            if debug:
                logger.info(f'[ARGOS][REGRAS] ato_termoS finalizado em {time.time() - inicio_ato:.2f}s')
        else:
            inicio_ato = time.time()
            try:
                ato_meios(driver, debug=debug)
            except Exception as e:
                if debug:
                    logger.error(f'[ARGOS][REGRAS][ERRO] ato_meios falhou: {e}')
            if debug:
                logger.info(f'[ARGOS][REGRAS] ato finalizado em {time.time() - inicio_ato:.2f}s')
        return True
    return False



def estrategia_decisao_manifestar(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Decisão com 'devendo se manifestar'"""
    tipo_norm = unicodedata.normalize('NFD', str(tipo_documento or '')).encode('ascii', 'ignore').decode('ascii').lower()
    if 'decisao' not in tipo_norm:
        return False

    # Triggers que, segundo m1.py, devem acionar checar_prox para avançar ao próximo documento
    trechos_checar_prox = ['devendo se manifestar', 'nada a deferir']
    for trecho in trechos_checar_prox:
        if texto_documento and trecho in texto_documento.lower():
            if debug:
                logger.info(f'[ARGOS][REGRAS] Texto "{trecho}" detectado, chamando checar_prox...')
            try:
                # Seguir o padrão histórico: passar placeholders compatíveis
                checar_prox(driver, None, None, None, texto_documento)
            except Exception as e:
                if debug:
                    logger.info(f'[ARGOS][REGRAS][ERRO] checar_prox falhou: {e}')
            return True
    return False


def estrategia_tendo_em_vista_que(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Decisão com 'tendo em vista que' — analisa número de reclamadas e escolhe ação."""
    tipo_norm = unicodedata.normalize('NFD', str(tipo_documento or '')).encode('ascii', 'ignore').decode('ascii').lower()
    if 'decisao' in tipo_norm and texto_documento:
        # Normalizar texto para detecção robusta (remover acentos)
        txt_lower = texto_documento.lower()
        normalized = unicodedata.normalize('NFD', texto_documento).encode('ascii', 'ignore').decode('ascii').lower()

        # Buscar em ambas as formas (com e sem acento)
        tem_tendo_em_vista = ('tendo em vista que' in txt_lower or
                             'tendo em vista que' in normalized)

        if not tem_tendo_em_vista:
            return False
        if debug:
            logger.info('[ARGOS][REGRAS] Regra decisao+tendo_em_vista reconhecida')
        try:
            mods = _lazy_import_mandado_regras()
            extrair_dados_processo = mods.get('extrair_dados_processo')
            if not extrair_dados_processo:
                raise Exception('extrair_dados_processo indisponível')
            dados_processo = extrair_dados_processo(driver)
        except Exception as e:
            if debug:
                logger.error(f'[ARGOS][REGRAS][ERRO] Falha ao extrair dados do processo: {e}')
            dados_processo = {}

        if not dados_processo:
            reus_dadosatuais = _carregar_reus_dadosatuais(debug=debug)
            if reus_dadosatuais:
                dados_processo = {'reu': reus_dadosatuais}

        num_reclamadas = len(dados_processo.get('reu', [])) if dados_processo else 0
        if num_reclamadas == 1:
            # Com uma reclamada, segue lógica semelhante a despacho
            if resultado_sisbajud == 'negativo' and all(v == 'nao' for v in (sigilo_anexos or {}).values()):
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_meios (1 reclamada, SISBAJUD negativo, sem sigilo)')
                inicio_ato = time.time()
                try:
                    ato_meios(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_meios falhou: {e}')
                if debug:
                    logger.info(f'[ARGOS][REGRAS] ato_meios finalizado em {time.time() - inicio_ato:.2f}s')
            elif resultado_sisbajud == 'negativo' and any(v == 'sim' for v in (sigilo_anexos or {}).values()):
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_termoE (1 reclamada, SISBAJUD negativo, com sigilo)')
                inicio_ato = time.time()
                try:
                    ato_termoE(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_termoE falhou: {e}')
                if debug:
                    logger.info(f'[ARGOS][REGRAS] ato_termoE finalizado em {time.time() - inicio_ato:.2f}s')
            else:
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_bloq (1 reclamada, SISBAJUD positivo/indefinido)')
                inicio_ato = time.time()
                try:
                    ato_bloq(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_bloq falhou: {e}')
                if debug:
                    logger.info(f'[ARGOS][REGRAS] ato_bloq finalizado em {time.time() - inicio_ato:.2f}s')
        elif num_reclamadas > 1:
            # Multiplas reclamadas
            if resultado_sisbajud == 'negativo':
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_meiosub (multiplas reclamadas, SISBAJUD negativo)')
                inicio_ato = time.time()
                try:
                    ato_meiosub(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_meiosub falhou: {e}')
                if debug:
                    logger.info(f'[ARGOS][REGRAS] ato_meiosub finalizado em {time.time() - inicio_ato:.2f}s')
            else:
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_bloq (multiplas reclamadas, SISBAJUD positivo/indefinido)')
                inicio_ato = time.time()
                try:
                    ato_bloq(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_bloq falhou: {e}')
                if debug:
                    logger.info(f'[ARGOS][REGRAS] ato_bloq finalizado em {time.time() - inicio_ato:.2f}s')
        else:
            if debug:
                logger.info('[ARGOS][REGRAS] Número de reclamadas desconhecido/zero; regra "tendo em vista que" não será aplicada')
            return False
        return True
    return False


# Adicione outras estratégias conforme necessário

ESTRATEGIAS_ARGOS = [
    ("decisao+tendo_em_vista", estrategia_tendo_em_vista_que),  #  PRIMEIRA: Triagem por quantidade de reclamadas
    ("IDPJ (instauração/855-A/desconsideração)", estrategia_defiro_instauracao),
    ("despacho+argos", estrategia_despacho_argos),
    ("despacho+infojud", estrategia_infojud),
    ("decisao+manifestar", estrategia_decisao_manifestar),
    # Adicione outras estratégias aqui
]

ESTRATEGIAS_ARGOS_DECISAO = [
    ("decisao+tendo_em_vista", estrategia_tendo_em_vista_que),
    ("IDPJ (instauração/855-A/desconsideração)", estrategia_defiro_instauracao),
    ("decisao+manifestar", estrategia_decisao_manifestar),
]

ESTRATEGIAS_ARGOS_DESPACHO = [
    ("despacho+argos", estrategia_despacho_argos),
    ("despacho+infojud", estrategia_infojud),
]


def aplicar_regras_argos(
    driver: WebDriver,
    resultado_sisbajud: Dict[str, str],
    sigilo_anexos: Dict[str, str],
    tipo_documento: str,
    texto_documento: str,
    debug: bool = False
) -> bool:
    """Aplica regras de negócio via Strategy Pattern.
    
    Avalia documento usando múltiplas estratégias em ordem de prioridade,
    aplicando atos judiciais conforme padrões identificados.
    
    Args:
        driver: WebDriver Selenium conectado a PJe
        resultado_sisbajud: Dict com resultado da consulta SISBAJUD
        sigilo_anexos: Dict com status de sigilo por tipo de anexo
        tipo_documento: Tipo do documento (despacho, decisão, etc)
        texto_documento: Texto completo do documento
        debug: Se True, imprime logs detalhados
    
    Returns:
        True se alguma regra foi aplicada, False caso contrário
    
    Examples:
        >>> resultado = {'tipo': 'positivo'}
        >>> aplicar_regras_argos(driver, resultado, {}, 'despacho', 'texto', debug=True)
        True
    """
    if not texto_documento:
        return False

    tipo_norm = unicodedata.normalize('NFD', str(tipo_documento or '')).encode('ascii', 'ignore').decode('ascii').lower()
    if 'decisao' in tipo_norm:
        estrategias_em_uso = ESTRATEGIAS_ARGOS_DECISAO
    elif 'despacho' in tipo_norm:
        estrategias_em_uso = ESTRATEGIAS_ARGOS_DESPACHO
    else:
        estrategias_em_uso = ESTRATEGIAS_ARGOS
    
    if debug:
        # Mostrar trecho extraído para diagnóstico (raw + normalizado sem acentos)
        try:
            raw_snippet = texto_documento[:1200].replace('\n', ' ')
        except Exception:
            raw_snippet = str(texto_documento)[:1200]
        normalized_snippet = unicodedata.normalize('NFD', texto_documento).encode('ascii', 'ignore').decode('ascii')[:1200] if texto_documento else ''
    
    # ===== TENTAR CADA ESTRATÉGIA EM ORDEM =====
    inicio_aplicacao = time.time()
    regra_aplicada = False
    for nome_estrategia, funcao_estrategia in estrategias_em_uso:
        try:
            if debug:
                inicio_estrategia = time.time()
            if funcao_estrategia(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug):
                regra_aplicada = True
                if debug:
                    fim_estrategia = time.time()
                    logger.info(f'[ARGOS][REGRAS] Estrategia "{nome_estrategia}" aplicada em {fim_estrategia - inicio_estrategia:.2f}s')
                    logger.info(f'[ARGOS][REGRAS] Tempo total ate aplicar regra: {fim_estrategia - inicio_aplicacao:.2f}s')
                break  # Interrompe após primeira regra aplicada
            if debug:
                fim_estrategia = time.time()
                logger.info(f'[ARGOS][REGRAS] Estrategia "{nome_estrategia}" sem aplicacao ({fim_estrategia - inicio_estrategia:.2f}s)')
        except Exception as e:
            if debug:
                logger.error(f'[ARGOS][REGRAS][ERRO] Estrategia "{nome_estrategia}" falhou: {str(e)[:60]}')
            continue

    if not regra_aplicada and debug:
        fim_aplicacao = time.time()
        logger.info(f'[ARGOS][REGRAS] Nenhuma regra aplicou ({fim_aplicacao - inicio_aplicacao:.2f}s)')
    return regra_aplicada
# ...existing code...

