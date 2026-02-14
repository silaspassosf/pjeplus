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
    NoSuchWindowException,
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
        from Fix import (
            navegar_para_tela,
            extrair_pdf,
            analise_outros,
            extrair_documento,
            criar_gigs,
            esperar_elemento,
            aguardar_e_clicar,
            buscar_seletor_robusto,
            limpar_temp_selenium,
            indexar_e_processar_lista,
            extrair_dados_processo,
            buscar_documento_argos,
            buscar_mandado_autor,
            buscar_ultimo_mandado,
            extrair_destinatarios_decisao,
            configurar_recovery_driver,
        )
        
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
from Fix import (
    verificar_e_tratar_acesso_negado_global,
    handle_exception_with_recovery,
    preencher_campo,
    salvar_destinatarios_cache,
)
from Fix.abas import validar_conexao_driver
from Fix.extracao import criar_lembrete_posit
from Prazo.p2b_core import checar_prox
from atos import (
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

# ====================================================
# CONTROLE DE SESSÃO E PROGRESSO UNIFICADO
# ====================================================

# Use o monitoramento unificado para extração e marcação de progresso
# Isso garante comportamento idêntico ao usado em p2b.py (validação/formato do número)
from PEC.core import (
    carregar_progresso_pec as carregar_progresso,
    salvar_progresso_pec as salvar_progresso,
    extrair_numero_processo_pec as extrair_numero_processo,
    verificar_acesso_negado_pec as verificar_acesso_negado,
    processo_ja_executado_pec as processo_ja_executado,
    marcar_processo_executado_pec as marcar_processo_executado,
)

# =========================
# ESTRATEGIAS_ARGOS - Strategy Pattern for Argos document relevance
# =========================
def estrategia_defiro_instauracao(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Prioridade: IDPJ (instauração/855-A/desconsideração) + SISBAJUD positivo"""
    txt_lower = texto_documento.lower() if texto_documento else ''
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
        # Caso SISBAJUD positivo tem precedência e fluxo específico
        if resultado_sisbajud == 'positivo':
            if debug:
                print('[ARGOS][REGRAS] Regra IDPJ reconhecida (SISBAJUD positivo)')
            try:
                criar_lembrete_posit(driver, 'Bloqueio', texto_documento, debug=debug)
            except Exception as e:
                if debug:
                    logger.warning(f'[ARGOS][REGRAS][WARN] Falha ao criar lembrete: {e}')
            # GIGS já é criado automaticamente pelo pec_idpj (gigs_extra configurado)
            try:
                pec_idpj(driver, debug=debug)
            except Exception as e:
                if debug:
                    logger.error(f'[ARGOS][REGRAS][ERRO] Falha ao executar pec_idpj: {e}')
            return True
        # Se explicitamente negativo, seguir fluxo alternativo (apenas pec_idpj, sem lembrete)
        elif resultado_sisbajud == 'negativo':
            if debug:
                print('[ARGOS][REGRAS] Regra IDPJ reconhecida (SISBAJUD negativo)')
            try:
                pec_idpj(driver, debug=debug)
            except Exception as e:
                if debug:
                    logger.error(f'[ARGOS][REGRAS][ERRO] Falha ao executar pec_idpj: {e}')
            return True
        # Caso sem informação clara de SISBAJUD, não aplica aqui (deixa para outras regras)
    return False

def estrategia_despacho_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Prioridade: despacho com palavra 'ARGOS'"""
    if tipo_documento == 'despacho' and texto_documento and 'argos' in texto_documento.lower():
        if debug:
            print('[ARGOS][REGRAS] NOVA REGRA: Despacho com ARGOS detectado - aplicando regras específicas')
        if resultado_sisbajud == 'positivo':
            if debug:
                print('[ARGOS][REGRAS] Ação definida pela regra: ato_bloq')
            if debug:
                print('[ARGOS][REGRAS] Regra despacho+argos reconhecida (SISBAJUD positivo)')
            inicio_ato = time.time()
            try:
                ato_bloq(driver, debug=debug)
            except Exception as e:
                if debug:
                    print(f'[ARGOS][REGRAS][ERRO] ato_bloq falhou: {e}')
            if debug:
                print(f'[ARGOS][REGRAS] ato_bloq finalizado em {time.time() - inicio_ato:.2f}s')
        elif resultado_sisbajud == 'negativo':
            # Quando SISBAJUD é negativo, distinguir se há anexos sigilosos
            if any(v == 'sim' for v in (sigilo_anexos or {}).values()):
                if debug:
                    print('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo com anexo sigiloso, executando ato_termoS')
                if debug:
                    print('[ARGOS][REGRAS] Regra despacho+argos reconhecida (SISBAJUD negativo + sigilo)')
                inicio_ato = time.time()
                try:
                    ato_termoS(driver, debug=debug)
                except Exception as e:
                    if debug:
                        print(f'[ARGOS][REGRAS][ERRO] ato_termoS falhou: {e}')
                if debug:
                    print(f'[ARGOS][REGRAS] ato_termoS finalizado em {time.time() - inicio_ato:.2f}s')
            else:
                if debug:
                    print('[ARGOS][REGRAS] ARGOS: SISBAJUD negativo sem anexo sigiloso, executando ato_meios')
                if debug:
                    print('[ARGOS][REGRAS] Regra despacho+argos reconhecida (SISBAJUD negativo sem sigilo)')
                inicio_ato = time.time()
                try:
                    ato_meios(driver, debug=debug)
                except Exception as e:
                    if debug:
                        print(f'[ARGOS][REGRAS][ERRO] ato_meios falhou: {e}')
                if debug:
                    print(f'[ARGOS][REGRAS] ato_meios finalizado em {time.time() - inicio_ato:.2f}s')
        else:
            # Caso de SISBAJUD indefinido ou outro valor — padrão para ato_meios
            if debug:
                print('[ARGOS][REGRAS] Ação padrão (SISBAJUD indefinido): ato_meios')
            if debug:
                print('[ARGOS][REGRAS] Regra despacho+argos reconhecida (SISBAJUD indefinido)')
            inicio_ato = time.time()
            try:
                ato_meios(driver, debug=debug)
            except Exception as e:
                if debug:
                    print(f'[ARGOS][REGRAS][ERRO] ato_meios falhou: {e}')
            if debug:
                print(f'[ARGOS][REGRAS] ato_meios finalizado em {time.time() - inicio_ato:.2f}s')
        return True
    return False

def estrategia_infojud(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Despacho com 'Realize-se a pesquisa INFOJUD'"""
    if tipo_documento == 'despacho' and texto_documento and 'realize-se a pesquisa infojud' in texto_documento.lower():
        if debug:
            print('[ARGOS][REGRAS] Regra despacho+infojud reconhecida')
        if any(v == 'sim' for v in sigilo_anexos.values()):
            inicio_ato = time.time()
            try:
                ato_termoS(driver, debug=debug)
            except Exception as e:
                if debug:
                    logger.error(f'[ARGOS][REGRAS][ERRO] ato_termoS falhou: {e}')
            if debug:
                print(f'[ARGOS][REGRAS] ato_termoS finalizado em {time.time() - inicio_ato:.2f}s')
        else:
            inicio_ato = time.time()
            try:
                ato_meios(driver, debug=debug)
            except Exception as e:
                if debug:
                    logger.error(f'[ARGOS][REGRAS][ERRO] ato_meios falhou: {e}')
            if debug:
                print(f'[ARGOS][REGRAS] ato_meios finalizado em {time.time() - inicio_ato:.2f}s')
        return True
    return False

def estrategia_decisao_manifestar(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Decisão com 'devendo se manifestar'"""
    # Triggers que, segundo m1.py, devem acionar checar_prox para avançar ao próximo documento
    trechos_checar_prox = ['devendo se manifestar', 'nada a deferir']
    for trecho in trechos_checar_prox:
        if texto_documento and trecho in texto_documento.lower():
            if debug:
                print(f'[ARGOS][REGRAS] Texto "{trecho}" detectado, chamando checar_prox...')
            try:
                # Seguir o padrão histórico: passar placeholders compatíveis
                checar_prox(driver, None, None, None, texto_documento)
            except Exception as e:
                if debug:
                    print(f'[ARGOS][REGRAS][ERRO] checar_prox falhou: {e}')
            return True
    return False


def estrategia_tendo_em_vista_que(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Decisão com 'tendo em vista que' — analisa número de reclamadas e escolhe ação."""
    if tipo_documento == 'decisao' and texto_documento:
        # Normalizar texto para detecção robusta (remover acentos)
        txt_lower = texto_documento.lower()
        normalized = unicodedata.normalize('NFD', texto_documento).encode('ascii', 'ignore').decode('ascii').lower()

        # Buscar em ambas as formas (com e sem acento)
        tem_tendo_em_vista = ('tendo em vista que' in txt_lower or
                             'tendo em vista que' in normalized)

        if not tem_tendo_em_vista:
            return False
        if debug:
            print('[ARGOS][REGRAS] Regra decisao+tendo_em_vista reconhecida')
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

        num_reclamadas = len(dados_processo.get('reu', [])) if dados_processo else 0
        if num_reclamadas == 1:
            # Com uma reclamada, segue lógica semelhante a despacho
            if resultado_sisbajud == 'negativo' and all(v == 'nao' for v in (sigilo_anexos or {}).values()):
                if debug:
                    print('[ARGOS][REGRAS] Chamando ato_meios (1 reclamada, SISBAJUD negativo, sem sigilo)')
                inicio_ato = time.time()
                try:
                    ato_meios(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_meios falhou: {e}')
                if debug:
                    print(f'[ARGOS][REGRAS] ato_meios finalizado em {time.time() - inicio_ato:.2f}s')
            elif resultado_sisbajud == 'negativo' and any(v == 'sim' for v in (sigilo_anexos or {}).values()):
                if debug:
                    print('[ARGOS][REGRAS] Chamando ato_termoE (1 reclamada, SISBAJUD negativo, com sigilo)')
                inicio_ato = time.time()
                try:
                    ato_termoE(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_termoE falhou: {e}')
                if debug:
                    print(f'[ARGOS][REGRAS] ato_termoE finalizado em {time.time() - inicio_ato:.2f}s')
            else:
                if debug:
                    print('[ARGOS][REGRAS] Chamando ato_bloq (1 reclamada, SISBAJUD positivo/indefinido)')
                inicio_ato = time.time()
                try:
                    ato_bloq(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_bloq falhou: {e}')
                if debug:
                    print(f'[ARGOS][REGRAS] ato_bloq finalizado em {time.time() - inicio_ato:.2f}s')
        else:
            # Multiplas reclamadas
            if resultado_sisbajud == 'negativo':
                if debug:
                    print('[ARGOS][REGRAS] Chamando ato_meiosub (multiplas reclamadas, SISBAJUD negativo)')
                inicio_ato = time.time()
                try:
                    ato_meiosub(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_meiosub falhou: {e}')
                if debug:
                    print(f'[ARGOS][REGRAS] ato_meiosub finalizado em {time.time() - inicio_ato:.2f}s')
            else:
                if debug:
                    print('[ARGOS][REGRAS] Chamando ato_bloq (multiplas reclamadas, SISBAJUD positivo/indefinido)')
                inicio_ato = time.time()
                try:
                    ato_bloq(driver, debug=debug)
                except Exception as e:
                    if debug:
                        logger.error(f'[ARGOS][REGRAS][ERRO] ato_bloq falhou: {e}')
                if debug:
                    print(f'[ARGOS][REGRAS] ato_bloq finalizado em {time.time() - inicio_ato:.2f}s')
        return True
    return False


# Adicione outras estratégias conforme necessário

ESTRATEGIAS_ARGOS = [
    ("decisao+tendo_em_vista", estrategia_tendo_em_vista_que),  # ✨ PRIMEIRA: Triagem por quantidade de reclamadas
    ("IDPJ (instauração/855-A/desconsideração)", estrategia_defiro_instauracao),
    ("despacho+argos", estrategia_despacho_argos),
    ("despacho+infojud", estrategia_infojud),
    ("decisao+manifestar", estrategia_decisao_manifestar),
    # Adicione outras estratégias aqui
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
    
    if debug:
        # Mostrar trecho extraído para diagnóstico (raw + normalizado sem acentos)
        try:
            raw_snippet = texto_documento[:1200].replace('\n', ' ')
        except Exception:
            raw_snippet = str(texto_documento)[:1200]
        normalized_snippet = unicodedata.normalize('NFD', texto_documento).encode('ascii', 'ignore').decode('ascii')[:1200] if texto_documento else ''
    
    # ===== TENTAR CADA ESTRATÉGIA EM ORDEM =====
    inicio_aplicacao = time.time()
    for nome_estrategia, funcao_estrategia in ESTRATEGIAS_ARGOS:
        try:
            if debug:
                inicio_estrategia = time.time()
            if funcao_estrategia(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug):
                if debug:
                    fim_estrategia = time.time()
                    print(f'[ARGOS][REGRAS] Estratégia "{nome_estrategia}" aplicada em {fim_estrategia - inicio_estrategia:.2f}s')
                    print(f'[ARGOS][REGRAS] Tempo total até aplicar regra: {fim_estrategia - inicio_aplicacao:.2f}s')
                return True
            if debug:
                fim_estrategia = time.time()
                print(f'[ARGOS][REGRAS] Estratégia "{nome_estrategia}" sem aplicação ({fim_estrategia - inicio_estrategia:.2f}s)')
        except Exception as e:
            if debug:
                logger.error(f'[ARGOS][REGRAS][ERRO] Estratégia "{nome_estrategia}" falhou: {str(e)[:60]}')
            # Continua com próxima estratégia
            continue
    
    # ===== NENHUMA REGRA APLICOU =====
    if debug:
        fim_aplicacao = time.time()
        print(f'[ARGOS][REGRAS] Nenhuma regra aplicou ({fim_aplicacao - inicio_aplicacao:.2f}s)')
    return False
# ...existing code...

