
import logging
import re
import time
import unicodedata
from typing import Any
from selenium.webdriver.common.by import By
from Fix.extracao import extrair_direto, extrair_documento, extrair_pdf, criar_gigs
from atos.movimentos import def_chip, mov_sob, mov_fimsob
from atos.judicial import ato_fal, ato_prov, ato_termoS
from Fix.selectors_pje import BTN_TAREFA_PROCESSO
from Fix.selenium_base import esperar_elemento, safe_click
from Fix.extracao import bndt
from pathlib import Path
from Fix.scripts import carregar_js

logger = logging.getLogger(__name__)

"""Análise de sobrestamento vencido - função def_sob (extraída de PEC/regras.py)."""


# ===== Funções auxiliares (copiadas da versão anterior) =====

def remover_acentos(texto: str) -> str:
    """Remove acentos de um texto."""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def normalizar_texto(texto: str) -> str:
    """Normaliza texto: remove acentos e converte para minúsculo."""
    return remover_acentos(texto.lower())


def gerar_regex_geral(termo: str) -> re.Pattern:
    """
    Gera regex tolerante para busca de termos em texto.

    Args:
        termo: Termo a ser procurado

    Returns:
        Pattern regex compilado
    """
    termo_norm = normalizar_texto(termo)
    palavras = termo_norm.split()

    # Monta regex permitindo pontuação entre palavras
    partes = [re.escape(p) for p in palavras]
    regex = r''
    for i, parte in enumerate(partes):
        regex += parte
        if i < len(partes) - 1:
            regex += r'[\s\w\.,;:!\-–—()$]*'

    # Permite o trecho em qualquer lugar do texto
    return re.compile(rf"{regex}", re.IGNORECASE)


def def_sob(driver: Any, numero_processo: str, observacao: str, debug: bool = False, timeout: int = 10) -> bool:
    """
    Versão simplificada seguindo padrão p2b:
    1. Abre tarefa do processo (se necessário)
    2. Extrai texto da decisão visível (documento ativo)
    3. Aplica regra de sobrestamento
    """
    if not driver or not numero_processo or not observacao:
        return False

    logger.info(f'[DEF_SOB] Iniciando análise sobrestamento: {numero_processo}')

    # ===== Funções de ação (definidas localmente para capturar variáveis do escopo) =====

    def executar_mov_sob_retorno_feito():
        try:
            return mov_sob(driver, numero_processo, "sob 4", debug=True, timeout=timeout)
        except Exception:
            return False

    def executar_penhora_rosto():
        try:
            chips_padrao = ["Prazo vencido", "Prazo vencido pós sentença", "SISBAJUD"]
            try:
                def_chip(driver, numero_processo=numero_processo, observacao=observacao, chips_para_remover=chips_padrao, debug=debug, timeout=timeout)
            except Exception:
                pass
            ok_gigs = False
            try:
                # criar GIGS para 'xs rosto' com 1 dia antes de movimentar
                ok_gigs = criar_gigs(driver, 1, '', 'xs rosto', detalhe=True)
            except Exception:
                ok_gigs = False
            try:
                if mov_sob(driver, numero_processo, "sob 1", debug=debug):
                    return True
                return ok_gigs
            except Exception:
                return ok_gigs
        except Exception:
            return False

    def executar_mov_sob_precatorio():
        try:
            chips_padrao = ["Prazo vencido", "Prazo vencido pós sentença", "SISBAJUD"]
            try:
                def_chip(driver, numero_processo=numero_processo, observacao=observacao, chips_para_remover=chips_padrao, debug=debug, timeout=timeout)
            except Exception:
                pass

            meses_necessarios = 1

            try:
                from datetime import datetime
                hoje = datetime.now()
                if hoje.year == 2026 and hoje.month == 7:
                    if criar_gigs(driver, '-1', 'silas', 'precatorio'):
                        return True
                    return False
            except Exception:
                pass

            return mov_sob(driver, numero_processo, f"sob {meses_necessarios}", debug=True, timeout=timeout)
        except Exception:
            return False

    def executar_juizo_universal():
        # implementação complexa omitida - vamos retornar False temporariamente como stava no stub
        return False

    def executar_def_presc():
        try:
            from PEC.prescricao import def_presc as def_presc_func
            return def_presc_func(driver, numero_processo, texto_extraido, None, debug=debug)
        except Exception:
            return False

    def executar_ato_prov():
        try:
            res_fimsob = mov_fimsob(driver, debug=debug)
            if not res_fimsob:
                return False
            res_prov = ato_prov(driver, debug=debug)
            return True if res_prov else False
        except Exception:
            return False

    try:
        # ===== 1. Abrir tarefa do processo (como no p2b) =====
        from atos.judicial_fluxo import abrir_tarefa_processo
        sucesso, _ = abrir_tarefa_processo(driver)
        if not sucesso:
            logger.error('[DEF_SOB] ❌ Falha ao abrir tarefa')
            return False

        # ===== 2. Extrair texto da decisão ativa =====
        logger.info('[DEF_SOB] Extraindo conteúdo da decisão...')
        texto_extraido = None

        # Tenta extrair com extrair_direto (como no p2b)
        try:
            resultado = extrair_direto(driver, timeout=timeout, debug=debug, formatar=True)
            if resultado.get('sucesso'):
                texto_extraido = resultado['conteudo']
        except Exception:
            pass

        if not texto_extraido or len(texto_extraido.strip()) < 10:
            # Fallback: extrair_documento
            try:
                texto_extraido = extrair_documento(driver, regras_analise=None, timeout=timeout, log=debug)
            except Exception:
                pass

        if not texto_extraido or len(texto_extraido.strip()) < 10:
            logger.warning('[DEF_SOB] ⚠️ Texto extraído muito curto – tentando PDF fallback')
            try:
                texto_pdf = extrair_pdf(driver, log=debug)
                if texto_pdf:
                    texto_extraido = texto_pdf
            except Exception:
                pass

        if not texto_extraido or len(texto_extraido.strip()) < 10:
            logger.error('[DEF_SOB] ❌ Não foi possível extrair texto da decisão')
            return False

        # ===== 3. Aplicar regra de sobrestamento =====
        texto_normalizado = normalizar_texto(texto_extraido)

        regras_def_sob = [
            (['retorno do feito principal'], executar_mov_sob_retorno_feito, 'Retorno do feito principal'),
            (['penhora no rosto'], executar_penhora_rosto, 'Penhora no rosto'),
            (['precatório', 'RPV', 'pequeno valor'], executar_mov_sob_precatorio, 'Precatório/RPV/Pequeno valor'),
            (['juízo universal'], executar_juizo_universal, 'Juízo universal'),
            (['prazo prescricional'], executar_def_presc, 'Prazo prescricional'),
            (['autos principais', 'processo principal'], executar_ato_prov, 'Autos principais'),
        ]

        for termos, acao_func, descricao in regras_def_sob:
            for termo in termos:
                regex = gerar_regex_geral(termo)
                if regex.search(texto_normalizado):
                    logger.info(f'[DEF_SOB] ✅ Regra encontrada: {descricao}')
                    resultado = acao_func()
                    if resultado:
                        logger.info(f'[DEF_SOB] ✅ Regra executada com sucesso: {descricao}')
                        return True
                    else:
                        logger.error(f'[DEF_SOB] ❌ Falha na execução da regra: {descricao}')
                        return False

        # Se nenhuma regra foi aplicada
        logger.warning(f'[DEF_SOB] ⚠️ Nenhuma regra aplicável para {numero_processo}. Encaminhando para verificação manual.')
        return True

    except Exception as e:
        logger.error(f'[DEF_SOB] ❌ Erro geral: {e}', exc_info=True)
        return False
