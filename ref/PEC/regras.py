"""Módulo PEC - Regras de Processamento."""

import time
import re
import os
import unicodedata
import inspect
from typing import Optional, Dict, List, Tuple, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from PEC.core import carregar_progresso_pec, salvar_progresso_pec

# ===== IMPORTS PESADOS REMOVIDOS (LAZY LOADING) =====
# Movidos para cache sob demanda para carregamento 8-10x mais rápido

# Cache de módulos para lazy loading
_pec_regras_modules_cache = {}

def _lazy_import_pec_regras():
    """Carrega módulos pesados sob demanda (lazy loading)."""
    global _pec_regras_modules_cache
    
    if not _pec_regras_modules_cache:
        from Fix.core import preencher_campo
        from Fix.extracao import extrair_documento, extrair_pdf, criar_lembrete_posit, extrair_dados_processo, bndt, extrair_direto, criar_gigs
        from atos import pec_excluiargos
        from atos.judicial import ato_prov, ato_presc, ato_fal, ato_idpj, ato_bloq, ato_meios, ato_termoS
        from atos.movimentos import mov, def_chip, mov_aud, mov_sob
        from atos.comunicacao import (
            pec_ord, pec_sum, pec_editalaud, pec_cpgeral, pec_editaldec, 
            pec_decisao, pec_editalidpj, pec_bloqueio, pec_sigilo
        )
        from atos.wrappers_pec import wrapper_pec_ord_com_domicilio, wrapper_pec_sum_com_domicilio
        from Prazo.p2b_core import parse_gigs_param
        
        _pec_regras_modules_cache.update({
            'preencher_campo': preencher_campo,
            'extrair_documento': extrair_documento,
            'extrair_pdf': extrair_pdf,
            'criar_lembrete_posit': criar_lembrete_posit,
            'extrair_dados_processo': extrair_dados_processo,
            'bndt': bndt,
            'extrair_direto': extrair_direto,
            'criar_gigs': criar_gigs,
            'pec_excluiargos': pec_excluiargos,
            'ato_prov': ato_prov,
            'ato_presc': ato_presc,
            'ato_fal': ato_fal,
            'ato_idpj': ato_idpj,
            'ato_bloq': ato_bloq,
            'ato_meios': ato_meios,
            'ato_termoS': ato_termoS,
            'mov': mov,
            'def_chip': def_chip,
            'mov_aud': mov_aud,
            'mov_sob': mov_sob,
            'pec_ord': pec_ord,
            'pec_sum': pec_sum,
            'pec_editalaud': pec_editalaud,
            'pec_cpgeral': pec_cpgeral,
            'pec_editaldec': pec_editaldec,
            'pec_decisao': pec_decisao,
            'pec_editalidpj': pec_editalidpj,
            'pec_bloqueio': pec_bloqueio,
            'pec_sigilo': pec_sigilo,
            'wrapper_pec_ord_com_domicilio': wrapper_pec_ord_com_domicilio,
            'wrapper_pec_sum_com_domicilio': wrapper_pec_sum_com_domicilio,
            'parse_gigs_param': parse_gigs_param,
        })
    
    return _pec_regras_modules_cache

# NOTE: carta functionality lives in PEC.carta (function `carta`). We import dynamically below to avoid module errors.
import traceback

# ===== CACHE GLOBAL PARA REGRAS DE AÇÃO =====
# Inicializado como None - será preenchido na primeira chamada de get_cached_rules()
_ACAO_RULES_CACHE = None

# ===== DRIVER SISBAJUD GLOBAL PERSISTENTE =====
# Mantém um único driver SISBAJUD durante toda a sessão PEC
_DRIVER_SISBAJUD_GLOBAL = None

def _get_or_create_driver_sisbajud(driver_pje):
    """
    Retorna o driver SISBAJUD global existente ou cria um novo se necessário.
    Esta função garante que apenas um driver SISBAJUD seja usado durante toda a sessão.
    """
    global _DRIVER_SISBAJUD_GLOBAL
    
    # Se já existe e ainda está válido, reutilizar
    if _DRIVER_SISBAJUD_GLOBAL:
        try:
            # Verificar se o driver ainda está ativo
            _ = _DRIVER_SISBAJUD_GLOBAL.current_url
            print('[SISBAJUD_GLOBAL] ✅ Reutilizando driver SISBAJUD existente')
            return _DRIVER_SISBAJUD_GLOBAL
        except Exception:
            print('[SISBAJUD_GLOBAL] ⚠️ Driver anterior inválido, criando novo...')
            _DRIVER_SISBAJUD_GLOBAL = None
    
    # Criar novo driver SISBAJUD
    print('[SISBAJUD_GLOBAL]  Criando novo driver SISBAJUD global...')
    try:
        # Importar dinamicamente para evitar erros de módulo
        try:
            from SISB import core as sisb_core
        except:
            import sisb as sisb_core
        
        _DRIVER_SISBAJUD_GLOBAL = sisb_core.iniciar_sisbajud(driver_pje=driver_pje, extrair_dados=False)
        
        if _DRIVER_SISBAJUD_GLOBAL:
            print('[SISBAJUD_GLOBAL] ✅ Driver SISBAJUD global criado com sucesso')
        else:
            print('[SISBAJUD_GLOBAL] ❌ Falha ao criar driver SISBAJUD global')
        
        return _DRIVER_SISBAJUD_GLOBAL
    except Exception as e:
        print(f'[SISBAJUD_GLOBAL] ❌ Erro ao criar driver SISBAJUD: {e}')
        import traceback
        traceback.print_exc()
        return None

def fechar_driver_sisbajud_global():
    """Fecha o driver SISBAJUD global se existir"""
    global _DRIVER_SISBAJUD_GLOBAL
    if _DRIVER_SISBAJUD_GLOBAL:
        try:
            print('[SISBAJUD_GLOBAL]  Fechando driver SISBAJUD global...')
            _DRIVER_SISBAJUD_GLOBAL.quit()
            print('[SISBAJUD_GLOBAL] ✅ Driver SISBAJUD global fechado')
        except Exception as e:
            print(f'[SISBAJUD_GLOBAL] ⚠️ Erro ao fechar driver: {e}')
        finally:
            _DRIVER_SISBAJUD_GLOBAL = None

def _remover_acentos(txt):
    """Remove acentos de texto"""
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')


def _normalizar_texto(txt):
    """Normaliza texto: remove acentos e converte para minúscula"""
    return _remover_acentos(txt.lower())


def _gerar_regex_geral(termo):
    """Gera regex flexível para um termo, permitindo pontuação entre palavras"""
    termo_norm = _normalizar_texto(termo)
    palavras = termo_norm.split()
    partes = [re.escape(p) for p in palavras]
    regex = r''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()]*'
    return re.compile(rf"{regex}", re.IGNORECASE)


def _build_action_rules():
    """
    Constrói as regras de mapeamento observação -> ação uma única vez.
    Chamada apenas na primeira utilização, resultado é cacheado globalmente.
    (Todas as importações estão no início do arquivo)
    """
    
    # Import locally to avoid issues with import timing / circular imports.
    from importlib import import_module
    try:
        _com = import_module('atos.comunicacao')
    except Exception:
        _com = None
    try:
        _jud = import_module('atos.judicial')
    except Exception:
        _jud = None
    try:
        _movmod = import_module('atos.movimentos')
    except Exception:
        _movmod = None
    try:
        _fix_carta = import_module('PEC.carta')
    except Exception:
        _fix_carta = None
    try:
        _fix_ext = import_module('Fix.extracao')
    except Exception:
        _fix_ext = None
    
    # Importar SISB.core
    _sisb = None
    try:
        _sisb = import_module('SISB.core')
        print(f'[PEC_REGRAS] ✅ SISB importado')
    except Exception as e:
        print(f'[PEC_REGRAS] ❌ Falha ao importar SISB.core: {e}')
    
    try:
        _wraps = import_module('atos.wrappers_ato')
    except Exception:
        _wraps = None
    
    try:
        _wraps_pec = import_module('atos.wrappers_pec')
    except Exception:
        _wraps_pec = None

    # Helper to resolve attribute safely
    def _attr(mod, name, default=None):
        if not mod:
            return default
        return getattr(mod, name, default)

    return [
        ([_gerar_regex_geral(k) for k in ['exclusão', 'exclusao', 'excluir', 'indeferido']], _attr(_com, 'pec_excluiargos')),
        # SISBAJUD - TEIMOSINHA COM 60 DIAS (60d, 60 dias, sessenta)
        ([_gerar_regex_geral(k) for k in ['teimosinha 60', 't2 60', '60d', '60 dias', 'sessenta']], _attr(_sisb, 'minuta_bloqueio_60')),
        # SISBAJUD - TEIMOSINHA PADRÃO (30 dias)
        ([_gerar_regex_geral(k) for k in ['teimosinha', 't2']], _attr(_sisb, 'minuta_bloqueio')),
        # SISBAJUD - RESULTADO (processar ordens)
        ([_gerar_regex_geral(k) for k in ['xs resultado', 'resultado']], _attr(_sisb, 'processar_ordem_sisbajud')),
        ([_gerar_regex_geral(k) for k in ['xs ord']], _attr(_wraps_pec, 'wrapper_pec_ord_com_domicilio')),
        ([_gerar_regex_geral(k) for k in ['xs sum']], _attr(_wraps_pec, 'wrapper_pec_sum_com_domicilio')),
        ([_gerar_regex_geral(k) for k in ['xs aud', 'audx', 'aud x']], _attr(_jud, 'mov_aud')),
        ([_gerar_regex_geral(k) for k in ['sob chip']], _attr(_movmod, 'def_chip')),
        # Regra para "sobrestamento vencido" - agora ativada
        ([_gerar_regex_geral(k) for k in ['sobrestamento vencido']], def_sob),
        ([_gerar_regex_geral(k) for k in ['pz idpj', 'idpjd']], [lambda driver: criar_gigs(driver, 1, 'Ingrid', 'edital intimação correio'), _attr(_jud, 'ato_idpj')]),
        ([_gerar_regex_geral(k) for k in ['xs parcial']], _attr(_jud, 'ato_bloq')),
        ([_gerar_regex_geral(k) for k in ['meios']], [(_attr(_fix_ext, 'bndt'), {'inclusao': True}), _attr(_jud, 'ato_meios')]),
        ([_gerar_regex_geral(k) for k in ['pec aud']], _attr(_com, 'pec_editalaud')),
        ([_gerar_regex_geral(k) for k in ['pec cp', 'xs pec cp']], _attr(_com, 'pec_cpgeral')),
        ([_gerar_regex_geral(k) for k in ['xs dec reg']], _attr(_com, 'pec_decisao')),
        ([_gerar_regex_geral(k) for k in ['xs edital']], _attr(_com, 'pec_editaldec')),
        ([_gerar_regex_geral(k) for k in ['pec edital', 'xs pec edital']], _attr(_com, 'pec_editaldec')),
        ([_gerar_regex_geral(k) for k in ['pec dec', 'xs pec dec']], _attr(_com, 'pec_decisao')),
        ([_gerar_regex_geral(k) for k in ['pec idpj', 'xs pec idpj']], _attr(_com, 'pec_editalidpj')),
    ([_gerar_regex_geral(k) for k in ['xs carta']], _attr(_fix_carta, 'carta')),
        ([_gerar_regex_geral(k) for k in ['pec bloq', 'xs bloq']], _attr(_com, 'pec_bloqueio')),
        ([_gerar_regex_geral(k) for k in ['xs sigilo']], _attr(_com, 'pec_sigilo')),
        ([_gerar_regex_geral(k) for k in ['xs socio']], [(_attr(_fix_ext, 'bndt'), {'inclusao': True}), _attr(_wraps, 'ato_termoS')]),
    ([_gerar_regex_geral(k) for k in ['xs empresa', 'xs empre', 'xs emprea']], [(_attr(_fix_ext, 'bndt'), {'inclusao': True}), _attr(_wraps, 'ato_termoE')]),
        # xs (numero) sozinho = xs sob (numero) - mesmo bucket/ações
        ([re.compile(r'^xs\s+\d+$', re.IGNORECASE)], [_attr(_movmod, 'def_chip'), _attr(_movmod, 'mov_sob')]),
        ([re.compile(r'\bsob\s+\d+', re.IGNORECASE)], [_attr(_movmod, 'def_chip'), _attr(_movmod, 'mov_sob')]),
        ([_gerar_regex_geral(k) for k in ['sob']], [_attr(_movmod, 'def_chip'), _attr(_movmod, 'mov_sob')]),
    ]


def get_cached_rules():
    """
    Retorna regras cacheadas, construindo apenas na primeira chamada.
    Implementa padrão singleton para evitar repetidas compilações de regex.
    """
    global _ACAO_RULES_CACHE
    if _ACAO_RULES_CACHE is None:
        _ACAO_RULES_CACHE = _build_action_rules()
    return _ACAO_RULES_CACHE


def get_action_rules():
    """
    [DEPRECATED] Mantida para compatibilidade.
    Usa get_cached_rules() internamente.
    """
    return get_cached_rules()


def determinar_acoes_por_observacao(observacao):
    """
    Determina LISTA DE AÇÕES para uma observação.
    Cada regra que match adiciona sua ação à lista.
    
    Retorna lista de funções, ou [] se nenhuma regra corresponder.
    Usa cache global de regras (construído apenas uma vez).
    
    Args:
        observacao: String com a observação do processo
        
    Returns:
        list: [funcao1, funcao2, ...] ou []
    """
    observacao_lower = observacao.lower()
    regras = get_cached_rules()
    acoes = []
    minuta_ja_detectada = False  # Flag para não adicionar minuta padrão após 60
    
    for idx, (regex_list, funcao) in enumerate(regras, 1):
        for regex in regex_list:
            try:
                if regex.search(observacao_lower):
                    # Se já detectou minuta_bloqueio_60, pular minuta_bloqueio padrão
                    acao_nome = funcao.__name__ if callable(funcao) and hasattr(funcao, '__name__') else str(funcao)
                    if minuta_ja_detectada and acao_nome == 'minuta_bloqueio':
                        break  # Pula esta regra
                    
                    # Adiciona ação à lista (não retorna na primeira match!)
                    if funcao and funcao not in acoes:  # Evita duplicatas
                        acoes.append(funcao)
                        if acao_nome == 'minuta_bloqueio_60':
                            minuta_ja_detectada = True
                    break  # Passa para próxima regra (não próxima regex da mesma regra)
            except NameError as ne:
                # Log detailed context to help debug missing names
                import traceback as _tb
                print(f"[PEC_RULE_ERROR] NameError while evaluating regex in rule #{idx}: {ne}")
                print(f"[PEC_RULE_ERROR] regex={regex.pattern if hasattr(regex, 'pattern') else regex} funcao={funcao}")
                _tb.print_exc()
                raise
            except Exception:
                # Other regex errors shouldn't stop processing; log and continue
                import traceback as _tb
                print(f"[PEC_RULE_ERROR] Exception while evaluating regex in rule #{idx}")
                print(f"[PEC_RULE_ERROR] regex={getattr(regex, 'pattern', str(regex))} funcao={funcao}")
                _tb.print_exc()
                continue
    
    return acoes  # ← Retorna LISTA, mesmo que vazia


# Manter compatibilidade: função antiga que retorna primeira ação
def determinar_acao_por_observacao(observacao):
    """
    [COMPATIBILIDADE] Retorna PRIMEIRA ação.
    Use determinar_acoes_por_observacao() para lista completa.
    """
    acoes = determinar_acoes_por_observacao(observacao)
    return acoes[0] if acoes else None


def executar_acao_pec(driver, acao, numero_processo=None, observacao=None, debug=True):
    """
    [SIMPLIFICADA + ROBUSTA] Executa uma ação (função ou lista de funções).
    
    Tenta primeira com assinatura padrão (driver, debug), depois tenta com parâmetros extras
    se disponíveis (numero_processo, observacao).
    
    Args:
        driver: Selenium WebDriver
        acao: Função ou lista de funções para executar, ou None
        numero_processo: Número do processo (opcional, para funções que precisem)
        observacao: Observação do processo (opcional, para funções que precisem)
        debug: Flag de debug
    
    Returns:
        bool: True se sucesso, False se falha ou nenhuma ação
    """
    if acao is None:
        if numero_processo:
            print(f"[PEC_EXEC] Nenhuma ação para {numero_processo}")
        return False
    
    # Normalizar: sempre trabalhar com lista
    acoes = acao if isinstance(acao, list) else [acao]
    
    try:
        for i, raw in enumerate(acoes, 1):
            # Suporta formato: func ou (func, kwargs_dict)
            extra_kwargs = None
            if isinstance(raw, (list, tuple)) and len(raw) == 2 and callable(raw[0]) and isinstance(raw[1], dict):
                func = raw[0]
                extra_kwargs = raw[1].copy()
            else:
                func = raw

            nome = func.__name__ if callable(func) else str(func)
            print(f"[PEC_EXEC] ({i}/{len(acoes)}) Executando: {nome}")

            resultado = False
            try:
                # Construir kwargs iniciais a partir de extra_kwargs (se houver)
                call_kwargs = {}
                if extra_kwargs:
                    call_kwargs.update(extra_kwargs)

                # Garantir que o parâmetro `debug` seja passado a menos que já esteja explicitamente fornecido
                if 'debug' not in call_kwargs:
                    call_kwargs['debug'] = debug

                # 1) Tentar chamada por kwargs (preserva parâmetros como mudar_expediente quando fornecidos como dados)
                try:
                    print(f"[PEC_EXEC_CALL] Chamando {nome} com kwargs={call_kwargs}")
                    resultado = func(driver, **call_kwargs)
                except TypeError:
                    # 2) Fallbacks: várias assinaturas possíveis (compatibilidade retroativa)
                    try:
                        resultado = func(driver, debug=debug)
                    except TypeError:
                        try:
                            resultado = func(driver, numero_processo, observacao, debug=debug)
                        except TypeError:
                            try:
                                resultado = func(driver, numero_processo, observacao)
                            except TypeError:
                                try:
                                    resultado = func(driver, debug=True)
                                except TypeError:
                                    resultado = func(driver)

            except Exception:
                # Re-raise unexpected exceptions to be handled by outer try
                raise

            if not resultado:
                print(f"[PEC_EXEC] ❌ {nome} retornou False")
                return False

            print(f"[PEC_EXEC] ✅ {nome} executada")

        return True

    except Exception as e:
        print(f"[PEC_EXEC] ❌ Erro na execução: {e}")
        traceback.print_exc()
        return False


def def_sob(driver: Any, numero_processo: str, observacao: str, debug: bool = False, timeout: int = 10) -> bool:
    """
    Função def_sob: analisa última decisão e executa ação baseada no conteúdo.
    """
    import re
    import time
    import unicodedata
    from selenium.webdriver.common.by import By
    # from Fix import extrair_documento, extrair_pdf  # Commented out - using extrair_direto from top-level import
    
    # ===== FUNÇÕES AUXILIARES PARA DECOMPOSIÇÃO BOOLEANA =====
    
    def _eh_documento_relevante(doc_text):
        """
        Verifica se o documento é relevante para análise de sobrestamento.
        
        Args:
            doc_text (str): Texto do documento
            
        Returns:
            bool: True se for documento relevante
        """
        return bool(re.search(r'despacho|decisão|sentença|conclusão', doc_text))
    
    def _tem_assinatura_magistrado(item):
        """
        Verifica se o item da timeline tem assinatura de magistrado.
        
        Args:
            item: Elemento da timeline
            
        Returns:
            bool: True se tem ícone de magistrado
        """
        try:
            mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
            return len(mag_icons) > 0
        except Exception:
            return False
    
    # ===== ESTRATEGIAS DE SOBRESTAMENTO - CONFIGURÁVEIS =====
    ESTRATEGIAS_SOBRESTAMENTO = {
        'retorno_feito_principal': {
            'termos': ['retorno do feito principal'],
            'acao': 'mov_sob_4_meses',
            'descricao': 'Retorno do feito principal'
        },
        'precatorio_rpv_pequeno_valor': {
            'termos': ['precatório', 'RPV', 'pequeno valor'],
            'acao': 'mov_sob_1_mes',
            'descricao': 'Precatório/RPV/Pequeno valor'
        },
        'juizo_universal': {
            'termos': ['juízo universal'],
            'acao': 'sequencia_juizo_universal',
            'descricao': 'Juízo universal'
        },
        'prazo_prescricional': {
            'termos': ['prazo prescricional'],
            'acao': 'def_presc',
            'descricao': 'Prazo prescricional'
        },
        'autos_principais': {
            'termos': ['autos principais', 'processo principal'],
            'acao': 'mov_fimsob_ato_prov',
            'descricao': 'Autos principais'
        }
    }
    
    # Guard clauses - validação de parâmetros obrigatórios
    if not driver:
        if debug:
            print("[DEF_SOB] ERRO: driver não fornecido")
        return False
    
    if not numero_processo or not isinstance(numero_processo, str):
        if debug:
            print("[DEF_SOB] ERRO: numero_processo inválido ou não fornecido")
        return False
    
    if not observacao or not isinstance(observacao, str):
        if debug:
            print("[DEF_SOB] ERRO: observacao inválida ou não fornecida")
        return False
    
    if timeout <= 0:
        if debug:
            print("[DEF_SOB] ERRO: timeout deve ser positivo")
        return False
    
    def log_msg(msg):
        if debug:
            print(f"[DEF_SOB] {msg}")
    
    log_msg(f"Iniciando análise de sobrestamento para processo {numero_processo}")
    log_msg(f"Observação: {observacao}")
    
    try:
        # ===== ETAPA 1: SELECIONAR ÚLTIMA DECISÃO =====
        log_msg("1. Selecionando última decisão...")
        
        # Procura itens da timeline
        itens = driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
        if not itens:
            log_msg("❌ Nenhum item encontrado na timeline")
            return False
        
        doc_encontrado = None
        doc_link = None
        
        # Procura documento relevante (decisão, despacho ou sentença)
        for item in itens:
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                doc_text = link.text.lower()
                
                # Verifica se é documento relevante
                if not re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                    continue
                
                # Verifica se foi assinado por magistrado
                mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                if mag_icons:  # Se há ícone de magistrado, usa esse documento
                    doc_encontrado = item
                    doc_link = link
                    break
                    
            except Exception as e:
                log_msg(f"⚠️ Erro ao processar item: {e}")
                continue
        
        # Se não encontrou com magistrado, usa o primeiro documento relevante
        if not doc_encontrado:
            for item in itens:
                try:
                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    doc_text = link.text.lower()
                    
                    if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                        doc_encontrado = item
                        doc_link = link
                        break
                        
                except Exception:
                    continue
        
        if not doc_encontrado or not doc_link:
            log_msg("❌ Nenhum documento relevante encontrado na timeline")
            return False
        
        log_msg(f"✅ Documento encontrado: {doc_link.text}")
        
        # ===== EXTRAIR DATA DA DECISÃO =====
        data_decisao_str = None
        try:
            hora_element = doc_encontrado.find_element(By.CSS_SELECTOR, '.tl-item-hora')
            if hora_element:
                title_attr = hora_element.get_attribute('title')
                if title_attr:
                    data_parte = title_attr.split(' ')[0]  # "08/08/2023"
                    data_decisao_str = data_parte
                    log_msg(f"✅ Data da decisão extraída: {data_decisao_str}")
        except Exception as e:
            log_msg(f"⚠️ Erro ao extrair data da decisão: {e}")
        
        # Clica no documento
        doc_link.click()
        time.sleep(3)  # Aguarda carregar mais tempo

        # ===== ETAPA 2: EXTRAIR CONTEÚDO =====
        log_msg("2. Extraindo conteúdo do documento...")

        texto = None

        # Usar extrair_direto (método direto sem cliques)
        try:
            resultado_extracao = extrair_direto(driver, timeout=timeout, debug=debug, formatar=True)
            if resultado_extracao['sucesso']:
                texto = resultado_extracao['conteudo']
                log_msg("✅ Conteúdo extraído com sucesso usando extrair_direto")
            else:
                log_msg("❌ extrair_direto falhou")
        except Exception as e:
            log_msg(f"❌ Erro ao extrair documento com extrair_direto: {e}")

        # Se extrair_direto falhou, tentar fallback com extrair_documento
        if not texto or len(texto.strip()) < 10:
            log_msg("⚠️ Tentando fallback com extrair_documento...")
            try:
                texto = extrair_documento(driver, regras_analise=None, timeout=timeout, log=debug)
                if texto:
                    texto = texto.lower()
                    log_msg("✅ Conteúdo extraído com sucesso usando extrair_documento (fallback)")
                else:
                    log_msg("❌ extrair_documento retornou None")
            except Exception as e:
                log_msg(f"❌ Erro ao extrair documento com extrair_documento: {e}")

        # Se ainda não temos texto, tentar extrair_pdf como último fallback
        if not texto or len(texto.strip()) < 10:
            log_msg("⚠️ Tentando último fallback com extrair_pdf...")
            try:
                texto_pdf = extrair_pdf(driver, log=debug)
                if texto_pdf:
                    texto = texto_pdf.lower()
                    log_msg("✅ Conteúdo extraído com sucesso usando extrair_pdf (último fallback)")
                else:
                    log_msg("❌ extrair_pdf retornou None")
            except Exception as e:
                log_msg(f"❌ Erro ao extrair documento com extrair_pdf: {e}")

        # Se ainda não temos texto, salvar HTML para diagnóstico e retornar falha
        if not texto or len(texto.strip()) < 10:
            log_msg("❌ Texto extraído muito curto ou vazio. Salvando HTML para diagnóstico.")
            try:
                preview_html = driver.page_source
                with open(f'debug_sob_preview_{numero_processo}.html', 'w', encoding='utf-8') as f:
                    f.write(preview_html)
                log_msg(f"[DIAGNOSTICO] HTML do preview salvo em debug_sob_preview_{numero_processo}.html")
            except Exception as ehtml:
                log_msg(f"[DIAGNOSTICO][ERRO] Falha ao salvar HTML do preview: {ehtml}")
            return False

        # Log do texto extraído (início apenas)
        log_texto = texto[:200] + '...' if len(texto) > 200 else texto
        log_msg(f"Texto extraído: {log_texto}")
        
        # ===== ETAPA 3: APLICAR REGRAS BASEADAS NO CONTEÚDO =====
        log_msg("3. Analisando conteúdo e aplicando regras...")
        
        # Funções auxiliares para normalização (igual ao p2.py)
        def remover_acentos(txt):
            return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
        
        def normalizar_texto(txt):
            return remover_acentos(txt.lower())
        
        def gerar_regex_geral(termo):
            termo_norm = normalizar_texto(termo)
            palavras = termo_norm.split()
            partes = [re.escape(p) for p in palavras]
            regex = r''  
            for i, parte in enumerate(partes):
                regex += parte
                if i < len(partes) - 1:
                    regex += r'[\s\.,;:!\-–—]*'
            return re.compile(rf"{regex}", re.IGNORECASE)
        
        texto_normalizado = normalizar_texto(texto)
        
        # ===== ETAPA 3: ESTRUTURA DE REGRAS REFATORADA (baseada no p2.py) =====
        def executar_mov_sob_precatorio():
            """Executa mov_sob com 1 mês para precatório/RPV/pequeno valor"""
            log_msg("✅ Regra: 'precatório/RPV/pequeno valor' - executando mov_sob com 1 mês")
            try:
                # 1) Remover chips relevantes antes de tentar ajustar sobrestamento
                try:
                    from atos.movimentos import def_chip
                    chip_ok = def_chip(driver, numero_processo, observacao, debug=debug, timeout=timeout)
                    if chip_ok:
                        log_msg("✅ def_chip executado: chips removidos/confirmados")
                    else:
                        log_msg("⚠️ def_chip executado: nenhum chip removido (ou já removido)")
                except Exception as e_chip:
                    log_msg(f"⚠️ Não foi possível executar def_chip: {e_chip}")

                # 2) Calcular meses necessários para que o sobrestamento VENÇA em JULHO/2026
                meses_necessarios = 1
                try:
                    from datetime import datetime
                    if data_decisao_str:
                        try:
                            dt = datetime.strptime(data_decisao_str, "%d/%m/%Y")
                            target = datetime(2026, 7, 1)
                            meses_necessarios = (target.year - dt.year) * 12 + (target.month - dt.month)
                            # Garantir pelo menos 1 mês
                            if meses_necessarios < 1:
                                meses_necessarios = 1
                            log_msg(f"✅ Data da decisão: {data_decisao_str} -> meses necessários: {meses_necessarios}")
                        except Exception as e_dt:
                            log_msg(f"⚠️ Falha ao parsear data_decisao_str ('{data_decisao_str}'): {e_dt}")
                            meses_necessarios = 1
                    else:
                        log_msg("⚠️ data_decisao_str não disponível; usando 1 mês como fallback")
                        meses_necessarios = 1
                except Exception as e_calc:
                    log_msg(f"⚠️ Erro ao calcular meses necessários: {e_calc}")
                    meses_necessarios = 1

                # 3) Se o mês atual já for JULHO/2026, criar GIGS em vez de mover sobrestamento
                try:
                    from datetime import datetime
                    hoje = datetime.now()
                    if hoje.year == 2026 and hoje.month == 7:
                        log_msg("⚠️ Mês atual é JULHO/2026 — criando GIGS em vez de mov_sob")
                        try:
                            # Formato solicitado: '-1/silas/precatorio'
                            resultado_gigs = criar_gigs(driver, '-1', 'silas', 'precatorio')
                            if resultado_gigs:
                                log_msg("✅ GIGS '-1/silas/precatorio' criada com sucesso")
                                return True
                            else:
                                log_msg("❌ Falha na criação do GIGS '-1/silas/precatorio'")
                                return False
                        except Exception as eg:
                            log_msg(f"❌ Erro ao executar criar_gigs: {eg}")
                            import traceback
                            traceback.print_exc()
                            return False

                except Exception:
                    # Se houver qualquer problema ao checar a data, seguir para mov_sob padrão
                    pass

                # 4) Executar mov_sob com a quantidade de meses calculada
                from atos import mov_sob
                resultado = mov_sob(driver, numero_processo, f"sob {meses_necessarios}", debug=True, timeout=timeout)
                if resultado:
                    log_msg(f"✅ mov_sob com {meses_necessarios} meses executado com sucesso")
                    return True
                else:
                    log_msg(f"❌ Falha na execução do mov_sob com {meses_necessarios} meses")
                    return False
            except Exception as e:
                log_msg(f"❌ Erro ao executar mov_sob: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def executar_juizo_universal():
            """Executa sequência baseada na análise do prazo do sobrestamento usando a data da decisão"""
            log_msg("✅ Regra: 'juízo universal' - analisando prazo do sobrestamento usando data da decisão")
            try:
                from datetime import datetime, timedelta
                import re
                
                # Usar a data da decisão já extraída (disponível em data_decisao_str)
                if not data_decisao_str:
                    log_msg("❌ Data da decisão não disponível para análise de juízo universal")
                    return False
                
                # Converter data da decisão para datetime
                try:
                    data_decisao_dt = datetime.strptime(data_decisao_str, "%d/%m/%Y")
                    log_msg(f"✅ Usando data da decisão: {data_decisao_str}")
                except ValueError as e:
                    log_msg(f"❌ Erro ao converter data da decisão '{data_decisao_str}': {e}")
                    return False
                
                # ===== ETAPA 1: ABRIR TAREFA DO PROCESSO =====
                log_msg("1. Abrindo tarefa do processo para verificar sobrestamento atual...")
                
                try:
                    from Fix.selectors_pje import BTN_TAREFA_PROCESSO
                    from Fix import esperar_elemento, safe_click
                    
                    # Encontrar e clicar no botão "Abrir tarefa do processo"
                    btn_abrir_tarefa = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=15)
                    if not btn_abrir_tarefa:
                        log_msg("❌ Botão 'Abrir tarefa do processo' não encontrado")
                        return False
                    
                    # Registrar abas antes do clique
                    abas_antes = set(driver.window_handles)
                    
                    # Clicar no botão
                    click_resultado = safe_click(driver, btn_abrir_tarefa)
                    if not click_resultado:
                        log_msg("❌ Falha ao clicar no botão da tarefa")
                        return False
                    
                    # Aguardar nova aba
                    nova_aba = None
                    for _ in range(20):
                        abas_depois = set(driver.window_handles)
                        novas_abas = abas_depois - abas_antes
                        if novas_abas:
                            nova_aba = novas_abas.pop()
                            break
                        time.sleep(0.3)
                    
                    if nova_aba:
                        driver.switch_to.window(nova_aba)
                        log_msg("✅ Nova aba da tarefa aberta")
                        
                        # Aguardar carregamento
                        time.sleep(3)
                        
                        # Verificar se carregou corretamente
                        try:
                            driver.find_element(By.TAG_NAME, 'body')
                            log_msg("✅ Página da tarefa carregada")
                        except Exception as e:
                            log_msg(f"⚠️ Problema ao verificar carregamento: {e}")
                    else:
                        log_msg("⚠️ Nenhuma nova aba detectada, continuando na aba atual")
                        
                except Exception as e:
                    log_msg(f"❌ Erro ao abrir tarefa do processo: {e}")
                    return False
                
                # ===== ETAPA 2: LER DATA ATUAL DO SOBRESTAMENTO =====
                log_msg("2. Verificando data atual do sobrestamento...")
                
                data_sobrestamento = None
                try:
                    # Buscar célula com classe centralizado que contém data
                    celulas_data = driver.find_elements(By.CSS_SELECTOR, 'td.centralizado.td-class.ng-star-inserted')
                    log_msg(f"Encontradas {len(celulas_data)} células para análise")
                    
                    for i, celula in enumerate(celulas_data):
                        texto = celula.text.strip()
                        log_msg(f"Célula {i+1}: '{texto}'")
                        
                        # Buscar padrão de data DD/MM/AAAA
                        match_data = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
                        if match_data:
                            data_str = match_data.group(1)
                            try:
                                data_sobrestamento = datetime.strptime(data_str, "%d/%m/%Y")
                                log_msg(f"✅ Data do sobrestamento encontrada na célula {i+1}: {data_str}")
                                break
                            except ValueError as ve:
                                log_msg(f"⚠️ Erro ao converter '{data_str}': {ve}")
                                continue
                    
                    if not data_sobrestamento:
                        log_msg("⚠️ Data do sobrestamento não encontrada em nenhuma célula")
                        log_msg("Tentando seletores alternativos...")
                        
                        # Fallback: buscar em outros seletores possíveis
                        seletores_alternativos = [
                            'td:contains("/")',  # Qualquer célula com barra
                            'td[class*="data"]',  # Célula com classe contendo "data"
                            'td[class*="prazo"]', # Célula com classe contendo "prazo"
                            '.data-sobrestamento', # Classe específica se existir
                        ]
                        
                        for seletor in seletores_alternativos:
                            try:
                                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                                log_msg(f"Seletor '{seletor}': {len(elementos)} elementos")
                                
                                for elem in elementos:
                                    texto_alt = elem.text.strip()
                                    if texto_alt:
                                        match_alt = re.search(r'(\d{2}/\d{2}/\d{4})', texto_alt)
                                        if match_alt:
                                            data_str_alt = match_alt.group(1)
                                            try:
                                                data_sobrestamento = datetime.strptime(data_str_alt, "%d/%m/%Y")
                                                log_msg(f"✅ Data encontrada via seletor alternativo: {data_str_alt}")
                                                break
                                            except ValueError:
                                                continue
                                if data_sobrestamento:
                                    break
                            except Exception as e:
                                log_msg(f"Erro em seletor '{seletor}': {e}")
                        
                        if not data_sobrestamento:
                            log_msg("❌ Data não encontrada em nenhum seletor, executando fluxo completo como fallback")
                        
                except Exception as e:
                    log_msg(f"❌ Erro crítico ao buscar data do sobrestamento: {e}")
                    log_msg("Executando fluxo completo como fallback")
                
                # ===== ETAPA 2: CALCULAR DIFERENÇA DE MESES USANDO DATA DA DECISÃO =====
                executar_fimsob_e_ato_fal = True  # Padrão: executar fluxo completo
                
                hoje = datetime.now()
                
                if data_sobrestamento:
                    # Calcular diferença entre hoje e a data da decisão (não do sobrestamento)
                    diferenca = hoje - data_decisao_dt
                    meses_diferenca = diferenca.days / 30.44  # Aproximação de meses
                    
                    log_msg(f" ANÁLISE DE PRAZO (usando data da decisão):")
                    log_msg(f"   Data da decisão: {data_decisao_dt.strftime('%d/%m/%Y')}")
                    log_msg(f"   Data atual: {hoje.strftime('%d/%m/%Y')}")
                    log_msg(f"   Diferença em dias: {diferenca.days}")
                    log_msg(f"   Diferença estimada: {meses_diferenca:.1f} meses")
                    log_msg(f"   Data do sobrestamento atual: {data_sobrestamento.strftime('%d/%m/%Y')}")
                    
                    if meses_diferenca < 8:
                        # Menos de 8 meses desde a decisão: calcular meses necessários para 9 meses totais
                        meses_necessarios = 9 - meses_diferenca
                        
                        # Garantir que seja pelo menos 1 mês
                        if meses_necessarios < 1:
                            meses_necessarios = 1
                        
                        # Arredondar para cima para garantir que passe de 9 meses
                        import math
                        meses_necessarios = math.ceil(meses_necessarios)
                        
                        log_msg(f"✅ DECISÃO: Prazo < 8 meses desde decisão ({meses_diferenca:.1f})")
                        log_msg(f"   Cálculo: 9 meses desejados - {meses_diferenca:.1f} meses decorridos = {meses_necessarios} meses")
                        log_msg(f"   Ação: Ajustar sobrestamento para {meses_necessarios} meses")
                        executar_fimsob_e_ato_fal = False
                        
                        # Calcular data final esperada: data da decisão + 9 meses
                        data_final_esperada = data_decisao_dt + timedelta(days=9*30)
                        log_msg(f"   Data final esperada (9 meses da decisão): {data_final_esperada.strftime('%d/%m/%Y')}")
                        
                        # Executar mov_sob com número calculado de meses
                        try:
                            log_msg(f"2. Executando mov_sob com {meses_necessarios} meses...")
                            from atos import mov_sob
                            resultado_sob = mov_sob(driver, numero_processo, f"sob {meses_necessarios}", debug=debug, timeout=timeout)
                            
                            if resultado_sob:
                                log_msg(f"✅ Sobrestamento ajustado para {meses_necessarios} meses com sucesso")
                                log_msg(f"✅ Processo {numero_processo}: Prazo ajustado para {meses_necessarios} meses (total 9 meses da decisão)")
                                return True
                            else:
                                log_msg("❌ Falha no ajuste do sobrestamento")
                                log_msg("   Fallback: Executando fluxo completo (mov_fimsob + ato_fal)")
                                executar_fimsob_e_ato_fal = True
                                
                        except Exception as e:
                            log_msg(f"❌ Erro no ajuste do sobrestamento: {e}")
                            log_msg("   Fallback: Executando fluxo completo (mov_fimsob + ato_fal)")
                            import traceback
                            traceback.print_exc()
                            executar_fimsob_e_ato_fal = True
                    else:
                        log_msg(f"✅ DECISÃO: Prazo >= 8 meses desde decisão ({meses_diferenca:.1f})")
                        log_msg("   Ação: Executar fluxo completo (mov_fimsob + ato_fal)")
                else:
                    log_msg("⚠️ DECISÃO: Data do sobrestamento não encontrada")
                    log_msg("   Ação: Executar fluxo completo como fallback")
                
                # ===== ETAPA 3: EXECUTAR FLUXO COMPLETO SE NECESSÁRIO =====
                if executar_fimsob_e_ato_fal:
                    log_msg("3. Executando fluxo completo (mov_fimsob + ato_fal)...")
                    
                    # Capturar informações das abas antes de executar mov_fimsob
                    abas_antes_fimsob = driver.window_handles
                    aba_processo_atual = driver.current_window_handle
                    log_msg(f"   Abas disponíveis: {len(abas_antes_fimsob)}")
                    
                    # ETAPA 3A: Executar mov_fimsob primeiro
                    log_msg("3A. Executando mov_fimsob...")
                    from atos import mov_fimsob
                    resultado_fimsob = mov_fimsob(driver, debug=debug)
                    
                    if not resultado_fimsob:
                        log_msg("❌ Falha na execução do mov_fimsob")
                        return False
                    
                    log_msg("✅ mov_fimsob executado com sucesso")
                    
                    # Verificar estado das abas após mov_fimsob
                    abas_apos_fimsob = driver.window_handles
                    log_msg(f"   Abas após fimsob: {len(abas_apos_fimsob)}")
                    
                    # Garantir que está na aba correta para ato_fal
                    if aba_processo_atual in abas_apos_fimsob:
                        driver.switch_to.window(aba_processo_atual)
                        log_msg("✅ Retornado à aba do processo original")
                    else:
                        log_msg("⚠️ Aba original não encontrada, permanecendo na aba atual")
                    
                    # ETAPA 3B: Executar ato_fal em seguida
                    log_msg("3B. Executando ato_fal...")
                    from atos import ato_fal
                    resultado_fal = ato_fal(driver, debug=debug)
                    
                    if resultado_fal:
                        log_msg("✅ ato_fal executado com sucesso")
                        log_msg(f"✅ Processo {numero_processo}: Sequência completa executada")
                        return True
                    else:
                        log_msg("❌ Falha na execução do ato_fal")
                        return False
                
                return True
                    
            except Exception as e:
                log_msg(f"❌ Erro crítico durante sequência juízo universal: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def executar_def_presc():
            """Executa def_presc para prazo prescricional"""
            log_msg("✅ Regra: 'prazo prescricional' - executando def_presc")
            try:
                resultado = def_presc(driver, numero_processo, texto, data_decisao_str, debug=debug)
                if resultado:
                    log_msg("✅ def_presc executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do def_presc")
                    return False
            except Exception as e:
                log_msg(f"❌ Erro ao executar def_presc: {e}")
                return False
        
        def executar_ato_prov():
            """Executa mov_fimsob + ato_prov para autos principais"""
            log_msg("✅ Regra: 'autos principais' - executando mov_fimsob + ato_prov")
            try:
                # Capturar informações das abas antes de executar mov_fimsob
                abas_antes_fimsob = driver.window_handles
                aba_processo_atual = driver.current_window_handle
                log_msg(f"Abas antes do mov_fimsob: {len(abas_antes_fimsob)}")
                
                # ETAPA 1: Executar mov_fimsob primeiro
                log_msg("1. Executando mov_fimsob...")
                from atos import mov_fimsob
                resultado_fimsob = mov_fimsob(driver, debug=debug)
                
                if not resultado_fimsob:
                    log_msg("❌ Falha na execução do mov_fimsob")
                    return False
                
                log_msg("✅ mov_fimsob executado com sucesso")
                
                # Verificar estado das abas após mov_fimsob
                abas_apos_fimsob = driver.window_handles
                
                # Garantir que está na aba correta para ato_prov
                if aba_processo_atual in abas_apos_fimsob:
                    driver.switch_to.window(aba_processo_atual)
                    log_msg(f"✅ Retornado à aba do processo original")
                
                # ETAPA 2: Executar ato_prov em seguida
                log_msg("2. Executando ato_prov...")
                from atos import ato_prov
                resultado_prov = ato_prov(driver, debug=debug)
                
                if resultado_prov:
                    log_msg("✅ Sequência completa (mov_fimsob + ato_prov) executada com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do ato_prov")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro durante sequência autos principais: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def executar_socio():
            """Executa BNDT inclusão + ato_termoS para casos de sócio"""
            log_msg("✅ Regra: 'socio' - executando BNDT inclusão + ato_termoS")
            try:
                # ETAPA 1: Executar BNDT inclusão
                log_msg("1. Executando BNDT inclusão...")
                from Fix import bndt
                resultado_bndt = bndt(driver, inclusao=True)
                
                if not resultado_bndt:
                    log_msg("⚠️ Falha na execução do BNDT inclusão — aba BNDT fechada, prosseguindo com ato_termoS")
                else:
                    log_msg("✅ BNDT inclusão executado com sucesso")
                
                # ETAPA 2: Executar ato_termoS
                log_msg("2. Executando ato_termoS...")
                from atos import ato_termoS
                resultado_termos = ato_termoS(driver, debug=debug)
                
                if resultado_termos:
                    log_msg("✅ Sequência completa (BNDT inclusão + ato_termoS) executada com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do ato_termoS")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro durante sequência socio: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def executar_mov_sob_retorno_feito():
            """Executa mov_sob com 4 meses para retorno do feito principal"""
            log_msg("✅ Regra: 'retorno do feito principal' - executando mov_sob com 4 meses")
            try:
                from atos import mov_sob
                resultado = mov_sob(driver, numero_processo, "sob 4", debug=True, timeout=timeout)
                if resultado:
                    log_msg("✅ mov_sob com 4 meses executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do mov_sob com 4 meses")
                    return False
            except Exception as e:
                log_msg(f"❌ Erro ao executar mov_sob: {e}")
                import traceback
                traceback.print_exc()
                return False

        def executar_penhora_rosto():
            """Regra específica para 'penhora no rosto': executa sequência definida.

            Sequência:
                1) def_chip (tentar)
                2) criar_gigs(driver, 1, '', 'xs rosto', detalhe=True)
                3) mov_sob(driver, numero_processo, 'sob 1')
            """
            log_msg("✅ Regra: 'penhora no rosto' - executando sequência automatizada")
            try:
                # 1) Tentar remover chips via def_chip
                try:
                    chip_ok = def_chip(driver, numero_processo, observacao, debug=debug, timeout=timeout)
                    log_msg(f"def_chip resultado: {chip_ok}")
                except Exception as e_chip:
                    log_msg(f"⚠️ def_chip falhou: {e_chip}")

                # 2) Criar GIGS -1/xs rosto
                ok_gigs = False
                try:
                    ok_gigs = criar_gigs(driver, -1, '', 'xs rosto', detalhe=True)
                    if ok_gigs:
                        log_msg("✅ GIGS '-1/xs rosto' criada com sucesso")
                    else:
                        log_msg("⚠️ Falha ao criar GIGS '-1/xs rosto'")
                except Exception as e_gigs:
                    log_msg(f"⚠️ Erro ao criar GIGS: {e_gigs}")
                    ok_gigs = False

                # 3) Executar mov_sob 1
                try:
                    resultado_mov = mov_sob(driver, numero_processo, "sob 1", debug=debug)
                    if resultado_mov:
                        log_msg("✅ mov_sob com 1 mês executado com sucesso")
                        return True
                    else:
                        log_msg("❌ mov_sob 1 falhou")
                        if ok_gigs:
                            log_msg("✅ GIGS criada apesar da falha no mov_sob - retornando True")
                            return True
                        return False
                except Exception as e_mov:
                    log_msg(f"❌ Erro ao executar mov_sob: {e_mov}")
                    if ok_gigs:
                        log_msg("✅ GIGS criada apesar do erro no mov_sob - retornando True")
                        return True
                    return False

            except Exception as e:
                log_msg(f"❌ Erro na execução da regra penhora no rosto: {e}")
                return False

        # Estrutura de regras baseada no p2.py - mais clara e organizadas
        regras_def_sob = [
            # [lista_de_termos, função_de_ação, descrição]
            (['retorno do feito principal'], executar_mov_sob_retorno_feito, 'Retorno do feito principal'),
            (['penhora no rosto'], executar_penhora_rosto, 'Penhora no rosto'),
            (['precatório', 'RPV', 'pequeno valor'], executar_mov_sob_precatorio, 'Precatório/RPV/Pequeno valor'),
            (['juízo universal'], executar_juizo_universal, 'Juízo universal'),
            (['prazo prescricional'], executar_def_presc, 'Prazo prescricional'),
            (['autos principais', 'processo principal'], executar_ato_prov, 'Autos principais'),
        ]
        
        # Aplicar regras de forma limpa (baseado no p2.py)
        log_msg("Analisando conteúdo e aplicando regras...")
        
        for termos, acao_func, descricao in regras_def_sob:
            # Verificar se algum termo da regra está presente
            for termo in termos:
                regex = gerar_regex_geral(termo)
                if regex.search(texto_normalizado):
                    log_msg(f"Regra encontrada: {descricao} (termo: '{termo}')")
                    resultado = acao_func()
                    if resultado:
                        log_msg(f"✅ Regra '{descricao}' executada com sucesso")
                        return True
                    else:
                        log_msg(f"❌ Falha na execução da regra '{descricao}'")
                        return False
        
        # Se nenhuma regra foi aplicada
        regras_nomes = [descricao for _, _, descricao in regras_def_sob]
        log_msg("⚠️ Nenhuma regra aplicável encontrada no conteúdo")

        log_msg(f"Regras verificadas: {', '.join(regras_nomes)}")
        return False
    except Exception as e:
        log_msg(f"❌ Erro geral em def_sob: {e}")
        return False

def def_presc(driver: Any, numero_processo: str, texto_decisao: str, data_decisao_str: Optional[str] = None, debug: bool = False) -> bool:
    """
    Função def_presc: analisa timeline para determinar prescrição.
    
    Verifica:
    1. Data da decisão fornecida como parâmetro
    2. Se há documento do autor (ícone verde) datado de menos de 6 meses da data atual
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        texto_decisao: Texto da decisão analisada
        data_decisao_str: Data da decisão no formato DD/MM/YYYY (extraída do elemento HTML)
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    import re
    import time
    from datetime import datetime, timedelta
    from selenium.webdriver.common.by import By
    
    # Guard clauses - validação de parâmetros obrigatórios
    if not driver:
        if debug:
            print("[DEF_PRESC] ERRO: driver não fornecido")
        return False
    
    if not numero_processo or not isinstance(numero_processo, str):
        if debug:
            print("[DEF_PRESC] ERRO: numero_processo inválido ou não fornecido")
        return False
    
    if not texto_decisao or not isinstance(texto_decisao, str):
        if debug:
            print("[DEF_PRESC] ERRO: texto_decisao inválido ou não fornecido")
        return False
    
    def log_msg(msg):
        if debug:
            print(f"[DEF_PRESC] {msg}")
    
    log_msg(f"Iniciando análise de prescrição para processo {numero_processo}")
    
    try:
        # Data atual para comparação
        data_atual = datetime.now()
        seis_meses_atras = data_atual - timedelta(days=180)  # Aproximadamente 6 meses
        
        log_msg(f"Data atual: {data_atual.strftime('%d/%m/%Y')}")
        log_msg(f"Limite (6 meses atrás): {seis_meses_atras.strftime('%d/%m/%Y')}")
        
        # ===== ETAPA 1: USAR DATA DA DECISÃO FORNECIDA =====
        # Usa a data da decisão extraída do HTML no momento da seleção
        if data_decisao_str:
            log_msg(f"✅ Data da decisão recebida: {data_decisao_str}")
        else:
            log_msg("⚠️ Data da decisão não fornecida, tentando extrair do texto...")
            # Fallback: tenta extrair do texto da decisão
            match_data_decisao = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', texto_decisao[:500])
            if match_data_decisao:
                data_decisao_str = match_data_decisao.group(1).replace('-', '/').replace('.', '/')
                log_msg(f"Data encontrada no texto da decisão: {data_decisao_str}")
            else:
                log_msg("⚠️ Não foi possível extrair data da decisão")
        
        # ===== ETAPA 2: ANALISAR TIMELINE PARA DOCUMENTOS DO AUTOR =====
        log_msg("Analisando timeline para documentos do autor...")
        
        # Procura itens da timeline (baseado no listaexec2.py - método robusto)
        seletores_timeline = [
            'li.tl-item-container',
            '.tl-data .tl-item-container', 
            '.timeline-item'
        ]
        
        itens = []
        for seletor in seletores_timeline:
            try:
                itens = driver.find_elements(By.CSS_SELECTOR, seletor)
                if itens and len(itens) > 0:
                    log_msg(f"Encontrados {len(itens)} itens na timeline com seletor: {seletor}")
                    break
            except Exception as e:
                log_msg(f"⚠️ Erro ao tentar seletor {seletor}: {e}")
        
        if not itens:
            log_msg("❌ Nenhum item encontrado na timeline")
            return False
        
        documentos_autor_recentes = []
        
        # Funções auxiliares para extração de data (baseadas no listaexec2.py - método robusto)
        def extrair_data_item(item):
            """Extrai data do item da timeline usando JavaScript (método do listaexec2.py)"""
            try:
                # Usar JavaScript para buscar data de forma robusta (igual ao listaexec2.py)
                data_texto = driver.execute_script("""
                    var item = arguments[0];
                    var dataElement = null;
                    
                    // Buscar .tl-data no próprio item
                    dataElement = item.querySelector('.tl-data[name="dataItemTimeline"]');
                    if (!dataElement) {
                        dataElement = item.querySelector('.tl-data');
                    }
                    
                    // Se não encontrou, buscar em elementos anteriores (método do listaexec2.py)
                    if (!dataElement) {
                        var elementoAnterior = item.previousElementSibling;
                        while (elementoAnterior) {
                            dataElement = elementoAnterior.querySelector('.tl-data[name="dataItemTimeline"]');
                            if (!dataElement) {
                                dataElement = elementoAnterior.querySelector('.tl-data');
                            }
                            if (dataElement) break;
                            elementoAnterior = elementoAnterior.previousElementSibling;
                        }
                    }
                    
                    return dataElement ? dataElement.textContent.trim() : null;
                """, item)
                
                if data_texto:
                    # Converter formato "17 mar. 2017" para "17/03/2017"
                    return converter_data_texto_para_numerico(data_texto)
                    
                return None
            except Exception as e:
                log_msg(f"Erro ao extrair data do item: {e}")
                return None
        
        def converter_data_texto_para_numerico(data_texto):
            try:
                meses = {
                    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                    'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                }
                
                # Regex para "17 mar. 2017"
                match = re.search(r'(\d{1,2})\s+(\w{3})\.?\s+(\d{4})', data_texto)
                if match:
                    dia = match.group(1).zfill(2)
                    mes_texto = match.group(2).lower()
                    ano = match.group(3)
                    
                    mes_numero = meses.get(mes_texto)
                    if mes_numero:
                        return f"{dia}/{mes_numero}/{ano}"
                
                # Regex para formato já numérico
                match_numerico = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', data_texto)
                if match_numerico:
                    return match_numerico.group(1).replace('-', '/').replace('.', '/')
                
                return None
            except Exception:
                return None
        
        def converter_data_para_datetime(data_str):
            try:
                if not data_str:
                    return None
                dia, mes, ano = data_str.split('/')
                return datetime(int(ano), int(mes), int(dia))
            except Exception:
                return None
        
        # ===== ABORDAGEM OTIMIZADA BASEADA NO DOCUMENTOS_EXECUCAO.JS =====
        log_msg("� Usando abordagem JavaScript otimizada para buscar polo ativo...")
        
        # Executa JavaScript diretamente para buscar primeiro documento de polo ativo
        # Usar função centralizada de Fix.py
        from Fix import buscar_documentos_polo_ativo
        documentos_encontrados = buscar_documentos_polo_ativo(driver, polo="autor", limite_dias=180, debug=debug)
        
        log_msg(f" Busca JavaScript concluída. Total de documentos encontrados: {len(documentos_encontrados)}")
        
        # Processar documentos encontrados
        for doc_info in documentos_encontrados:
            data_texto = doc_info.get('data', '')
            nome_doc = doc_info.get('titulo', '')  # Atualizado para usar 'titulo' ao invés de 'nome'
            
            # Converter data
            data_item_str = converter_data_texto_para_numerico(data_texto)
            if data_item_str:
                data_item_dt = converter_data_para_datetime(data_item_str)
                if data_item_dt and data_item_dt >= seis_meses_atras:
                    documentos_autor_recentes.append({
                        'data': data_item_str,
                        'data_dt': data_item_dt,
                        'nome': nome_doc,
                        'index': doc_info.get('index', 0)
                    })
                    log_msg(f"✅ Documento do autor dos últimos 6 meses: {nome_doc} ({data_item_str})")
                else:
                    log_msg(f" Documento do autor fora do período: {nome_doc} ({data_item_str if data_item_str else data_texto})")
        
        # ===== ETAPA 3: DECISÃO BASEADA NA ANÁLISE E DATA DA DECISÃO =====
        log_msg(f"Total de documentos do autor nos últimos 6 meses: {len(documentos_autor_recentes)}")
        
        # Primeiro, precisamos determinar a data da decisão para aplicar as regras
        data_decisao_dt = None
        if data_decisao_str:
            data_decisao_dt = converter_data_para_datetime(data_decisao_str)
        
        if not data_decisao_dt:
            log_msg("⚠️ Não foi possível determinar a data da decisão")
            # Fallback: usar data atual como referência (caso não encontre data na decisão)
            data_decisao_dt = data_atual
            log_msg(f"Usando data atual como fallback: {data_atual.strftime('%d/%m/%Y')}")
        
        # Calcular novos períodos para as regras usando referência à data da decisão
        tem_documentos_autor = len(documentos_autor_recentes) > 0

        # Usar um limite de 2 anos + 10 dias a partir da data da decisão (quando não há documentos do autor)
        limite_2anos_10dias = timedelta(days=730 + 10)  # aprox. 2 anos + 10 dias
        dias_desde_decisao = (data_atual - data_decisao_dt).days

        log_msg(f"Data da decisão: {data_decisao_dt.strftime('%d/%m/%Y')}")
        log_msg(f"Data atual: {data_atual.strftime('%d/%m/%Y')}")
        log_msg(f"Dias desde a decisão: {dias_desde_decisao}")
        log_msg(f"Limite (2 anos + 10 dias desde decisão): {(data_decisao_dt + limite_2anos_10dias).strftime('%d/%m/%Y')}")

        # NOVA LÓGICA: quando NÃO há documentos do autor, usar um único limite de 2 anos + 10 dias
        if not tem_documentos_autor:
            # Se passaram mais de 2 anos + 10 dias desde a decisão -> executar fluxo completo (mov_fimsob + ato_presc)
            if (data_atual - data_decisao_dt) > limite_2anos_10dias:
                log_msg("⚖️ REGRA (novo): > 2 anos e 10 dias desde decisão + SEM autor → mov_fimsob + alternar aba + ato_presc")
                try:
                    from atos import mov_fimsob, ato_presc
                    resultado_fimsob = mov_fimsob(driver, debug=debug)
                    if not resultado_fimsob:
                        log_msg("❌ Falha na execução do mov_fimsob")
                        return False

                    # Após mov_fimsob, identificar se uma nova aba foi aberta e trocar para ela para prosseguir o CLS
                    abas_apos = driver.window_handles
                    if len(abas_apos) > 1:
                        # Tenta trocar para a última aba aberta (normalmente a tarefa do processo)
                        driver.switch_to.window(abas_apos[-1])
                        log_msg(f"[CORRIGIDO] Troca para a nova aba da tarefa após mov_fimsob. Abas: {abas_apos}")
                    else:
                        log_msg(f"[CORRIGIDO] Apenas uma aba detectada após mov_fimsob. Prosseguindo na atual.")

                    resultado_presc = ato_presc(driver, debug=debug)
                    if resultado_presc:
                        log_msg("✅ ato_presc executado com sucesso")
                        return True
                    else:
                        log_msg("❌ Falha na execução do ato_presc")
                        return False
                except Exception as e:
                    log_msg(f"❌ Erro ao executar mov_fimsob/ato_presc: {e}")
                    return False
            else:
                # Se faltam menos de 2 anos + 10 dias -> apenas mover sobrestamento 1 mês
                log_msg(" REGRA (novo): <= 2 anos e 10 dias desde decisão + SEM autor → mov_sob com 1 mês")
                try:
                    from atos import mov_sob
                    resultado = mov_sob(driver, numero_processo, "sob 1", debug=debug, timeout=30)
                    if resultado:
                        log_msg("✅ mov_sob com 1 mês executado com sucesso")
                        return True
                    else:
                        log_msg("❌ Falha na execução do mov_sob com 1 mês")
                        return False
                except Exception as e:
                    log_msg(f"❌ Erro ao executar mov_sob 1 mês: {e}")
                    return False

        # REGRA: Data da decisão menor que 2 anos + ícone autor com manifestações recentes
        elif data_decisao_dt > (data_atual - timedelta(days=730)) and tem_documentos_autor:
            log_msg(" REGRA 3: Data menor que 2 anos + autor recente → lembrete + mov_sob 23")
            
            # Criar lembrete
            try:
                mes_atual = data_atual.strftime("%m")
                ano_atual = data_atual.strftime("%Y")
                conteudo_lembrete = f"Sobrestamento reiniciado em {mes_atual}/{ano_atual} por manifestação recente"
                
                log_msg(f"Criando lembrete: {conteudo_lembrete}")
                resultado_lembrete = criar_lembrete_posit(driver, "prescrição", conteudo_lembrete, debug=debug)
                
                if not resultado_lembrete:
                    log_msg("⚠️ Falha ao criar lembrete, mas continuando com mov_sob")
                else:
                    log_msg("✅ Lembrete criado com sucesso")
                
            except Exception as e:
                log_msg(f"⚠️ Erro ao criar lembrete: {e}, continuando com mov_sob")
            
            # Executar mov_sob com 23 meses
            try:
                from atos import mov_sob
                # Simula observação "sob 23" para acionar mov_sob com 23 meses
                observacao_sob = "sob 23"
                resultado_mov = mov_sob(driver, numero_processo, observacao_sob, debug=debug)
                
                if resultado_mov:
                    log_msg("✅ mov_sob 23 meses executado com sucesso")
                    return True
                else:
                    log_msg("❌ Falha na execução do mov_sob 23")
                    return False
                    
            except Exception as e:
                log_msg(f"❌ Erro ao executar mov_sob 23: {e}")
                return False
        
        # CASO PADRÃO: Não se encaixa em nenhuma regra específica
        else:
            log_msg("⚠️ Situação não se encaixa nas regras específicas")
            # Indica se a decisão é mais recente que 2 anos atrás (True = decisão dentro dos últimos 2 anos)
            log_msg(f"Data decisão > 2 anos? {data_decisao_dt > (data_atual - timedelta(days=730))}")
            log_msg(f"Tem documentos autor? {tem_documentos_autor}")
            
            if tem_documentos_autor:
                log_msg("✅ Há documentos do autor recentes - prescrição INTERROMPIDA")
                for doc in documentos_autor_recentes:
                    log_msg(f"  - {doc['nome']} ({doc['data']})")
            else:
                log_msg("⚠️ NÃO há documentos do autor recentes")
            
            # TODO: Definir ação padrão se necessário
            log_msg("Nenhuma ação específica executada")
            return True
        
        log_msg("✅ Análise de prescrição concluída")
        return True
        
    except Exception as e:
        log_msg(f"❌ Erro geral em def_presc: {e}")
        return False


def def_ajustegigs(driver: Any, numero_processo: str, data_decisao: str, debug: bool = False, dias_uteis: int = 4) -> bool:
    """
    Função para ajustar GIGS - modifica prazo para quantidade de dias úteis especificada.
    
    Fluxo:
    1. Clica no ícone de edição (fa-edit)
    2. Aguarda modal de cadastro de atividades abrir
    3. Preenche campo "Dias Úteis" com valor especificado
    4. Clica em "Salvar"
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo
        data_decisao: Data da decisão analisada
        debug: Se True, exibe logs detalhados
        dias_uteis: Número de dias úteis a ser configurado (padrão: 4)
    
    Returns:
        bool: True se executado com sucesso
    """
    import time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    def log_msg(msg):
        if debug:
            print(f"[DEF_AJUSTEGIGS] {msg}")
    
    log_msg(f"Iniciando ajuste de GIGS para processo {numero_processo}")
    log_msg(f"Data da decisão: {data_decisao}")
    log_msg(f"Ação: Ajustar prazo para {dias_uteis} dias úteis")
    
    try:
        # ===== ETAPA 1: CLICAR NO ÍCONE DE EDIÇÃO =====
        log_msg("1. Procurando ícone de edição (fa-edit)...")
        
        try:
            # Procura o ícone de edição na tabela
            icone_edicao = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.far.fa-edit.botao-icone-tabela'))
            )
            
            # Clica no ícone
            icone_edicao.click()
            log_msg("✅ Ícone de edição clicado")
            time.sleep(2)  # Aguarda modal abrir
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar no ícone de edição: {e}")
            return False
        
        # ===== ETAPA 2: AGUARDAR MODAL DE CADASTRO ABRIR =====
        log_msg("2. Aguardando modal de cadastro de atividades...")
        
        try:
            # Aguarda o modal aparecer
            modal_cadastro = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'mat-dialog-container pje-gigs-cadastro-atividades'))
            )
            log_msg("✅ Modal de cadastro de atividades encontrado")
            
            # Aguarda formulário estar completamente carregado
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[formcontrolname="dias"]'))
            )
            log_msg("✅ Formulário carregado completamente")
            time.sleep(1)  # Estabilização adicional
            
        except Exception as e:
            log_msg(f"❌ Erro ao aguardar modal: {e}")
            return False
        
        # ===== ETAPA 3: PREENCHER CAMPO "DIAS ÚTEIS" COM VALOR ESPECIFICADO =====
        log_msg(f"3. Preenchendo campo 'Dias Úteis' com valor {dias_uteis}...")
        
        try:
            # Procura o campo "Dias Úteis" usando o seletor do HTML fornecido
            campo_dias = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[formcontrolname="dias"]'))
            )
            
            # Aplicar preencher_campo para o valor de dias úteis
            resultado_preenchimento = preencher_campo(driver, campo_dias, str(dias_uteis))
            if not resultado_preenchimento:
                log_msg("❌ Falha ao preencher campo Dias Úteis")
                return False
            
            log_msg(f"✅ Campo 'Dias Úteis' preenchido com valor {dias_uteis}")
            
            # Verifica se o valor foi inserido corretamente
            valor_atual = campo_dias.get_attribute('value')
            if valor_atual == str(dias_uteis):
                log_msg(f"✅ Valor confirmado no campo: {dias_uteis}")
            else:
                log_msg(f"⚠️ Valor no campo difere do esperado: {valor_atual}")
            
            time.sleep(0.5)  # Aguarda processamento do valor
            
        except Exception as e:
            log_msg(f"❌ Erro ao preencher campo Dias Úteis: {e}")
            return False
        
        # ===== ETAPA 4: CLICAR EM "SALVAR" =====
        log_msg("4. Clicando em botão 'Salvar'...")
        
        try:
            # Usa a mesma lógica do criar_gigs de Fix.py para encontrar o botão Salvar
            btn_salvar = None
            botoes = driver.find_elements(By.CSS_SELECTOR, 'button.mat-raised-button')
            
            for btn in botoes:
                if btn.is_displayed() and ('Salvar' in btn.text or btn.get_attribute('type') == 'submit'):
                    btn_salvar = btn
                    log_msg(f"✅ Botão Salvar encontrado: texto='{btn.text}', type='{btn.get_attribute('type')}'")
                    break
            
            if not btn_salvar:
                log_msg("❌ Botão Salvar não encontrado!")
                return False
            
            # Clica no botão
            btn_salvar.click()
            log_msg("✅ Botão 'Salvar' clicado")
            
            # Aguarda mensagem de sucesso no snackbar (igual ao criar_gigs)
            try:
                success_snackbar = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'snack-bar-container.success simple-snack-bar span'))
                )
                if 'salva com sucesso' in success_snackbar.text.lower():
                    log_msg("✅ Mensagem de sucesso confirmada no snackbar")
                    time.sleep(1)  # Aguarda 1s após confirmação
                else:
                    log_msg("⚠️ Snackbar encontrado mas sem mensagem de sucesso")
            except Exception as e_snackbar:
                log_msg(f"⚠️ Não foi possível confirmar mensagem de sucesso: {e_snackbar}")
                # Aguarda o modal desaparecer como indicativo de sucesso
                try:
                    WebDriverWait(driver, 10).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, 'mat-dialog-container pje-gigs-cadastro-atividades'))
                    )
                    log_msg("✅ Modal fechado - operação salva com sucesso")
                except:
                    time.sleep(3)
                    log_msg("⚠️ Modal ainda visível, mas prosseguindo")
            
        except Exception as e:
            log_msg(f"❌ Erro ao clicar em Salvar: {e}")
            return False
        
        # ===== FINALIZAÇÃO =====
        time.sleep(2)  # Aguarda processamento final
        
        log_msg("✅ Ajuste de GIGS concluído com sucesso!")
        log_msg(f"Prazo ajustado para {dias_uteis} dias úteis")
        
        return True
        
    except Exception as e:
        log_msg(f"❌ Erro geral no ajuste de GIGS: {e}")
        
        # Em caso de erro, tenta fechar modal se estiver aberto
        try:
            botao_cancelar = driver.find_element(By.XPATH, "//button[contains(., 'Cancelar')]")
            if botao_cancelar.is_displayed():
                botao_cancelar.click()
                log_msg("⚠️ Modal cancelado devido ao erro")
        except:
            pass
        
        return False




# Placeholder functions for rules - REMOVED: Now imported from actual implementations
# def def_chip, mov_sob, carta, criar_lembrete_posit, preencher_campo are now imported from their respective modules


def determinar_acoes_por_observacao(observacao: str) -> List[Any]:
    """
    Determina ações baseadas na observação do processo.
    
    Args:
        observacao: Texto da observação (ex: 'xs sigilo', 'pec ord', etc.)
        
    Returns:
        Lista de funções de ação a executar
    """
    if not observacao:
        return []
    
    observacao_str = str(observacao).lower().strip()
    m = _lazy_import_pec_regras()
    
    # Regras em ordem de especificidade
    if 'xs' in observacao_str and 'sigilo' in observacao_str:
        return [m['pec_sigilo']]
    elif 'minuta' in observacao_str and 'bloqueio' in observacao_str:
        # SISBAJUD minuta de bloqueio
        try:
            from SISB.core import minuta_bloqueio
            return [minuta_bloqueio]
        except (ImportError, AttributeError):
            return []
    elif 'pec' in observacao_str and 'ord' in observacao_str:
        return [m['pec_ord']]
    elif 'pec' in observacao_str and 'sum' in observacao_str:
        return [m['pec_sum']]
    elif 'mov' in observacao_str and 'sob' in observacao_str:
        return [m['mov_sob']]
    elif 'def' in observacao_str and 'chip' in observacao_str:
        return [m['def_chip']]
    elif 'mov' in observacao_str and 'aud' in observacao_str:
        return [m['mov_aud']]
    elif 'pec' in observacao_str and 'sigilo' in observacao_str:
        return [m['pec_sigilo']]
    
    # Se não encontrou, retornar vazio
    return []


def determinar_acao_por_observacao(observacao: str) -> Any:
    """
    Versão compatibilidade que retorna apenas a primeira ação.
    """
    acoes = determinar_acoes_por_observacao(observacao)
    return acoes[0] if acoes else None
