"""
P2B Fluxo PZ Helpers - Funções auxiliares do fluxo_pz
Refatoração seguindo abordagem ORIGINAL do p2b.py: lista sequencial de regras
Mantém termos exatos e ordem de precedência do código que FUNCIONA
"""

# ===== CONFIGURAÇÕES DE PERFORMANCE =====
# Número de threads paralelas para verificar processos contra API GIGS
# Valores recomendados:
#   - 5-10: Conexão estável, evita sobrecarga
#   - 15-20: Conexão rápida, processa mais rápido
#   - 3-5: Conexão lenta ou instável
GIGS_API_MAX_WORKERS = 20

import logging
import re
import time
from typing import Optional, Tuple, List, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

from .p2b_fluxo_lazy import _lazy_import
from .p2b_fluxo_prescricao import prescreve, analisar_timeline_prescreve_js_puro
from .p2b_fluxo_documentos import (
    _encontrar_documento_relevante,
    _documento_nao_assinado,
    _extrair_texto_documento,
    _extrair_com_extrair_direto,
    _extrair_com_extrair_documento,
    _fechar_aba_processo,
)
from .p2b_fluxo_regras import _definir_regras_processamento, _processar_regras_gerais
# simple helper to obtain process phase from dadosatuais.json


def obter_fase_processual(driver, caminho_json: str = 'dadosatuais.json', debug: bool = False) -> Optional[str]:
    """
    Extrai dados do processo via `extrair_dados_processo` (Fix.extracao) e retorna
    o valor de `labelFaseProcessual` presente em `caminho_json`.

    Retorna `None` em caso de falha ou se o campo não existir.
    """
    from pathlib import Path
    import json
    try:
        try:
            from Fix.extracao import extrair_dados_processo
        except Exception:
            # fallback para módulo separado
            from Fix.extracao_processo import extrair_dados_processo

        # Executa extração que grava/atualiza `dadosatuais.json`
        extrair_dados_processo(driver, caminho_json=caminho_json, debug=debug)
    except Exception as e:
        logger.debug(f'[FLUXO_PZ] extrair_dados_processo falhou: {e}')

    p = Path(caminho_json)
    if not p.exists():
        logger.debug(f'[FLUXO_PZ] obter_fase_processual: {caminho_json} não encontrado')
        return None

    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        fase = data.get('labelFaseProcessual')
        if isinstance(fase, str):
            return fase.strip()
        return None
    except Exception as e:
        logger.debug(f'[FLUXO_PZ] Erro ao ler {caminho_json}: {e}')
        return None


def inicar_exec(driver, texto_normalizado: Optional[str] = None):
    """Helper: cria duas GIGS padrão, tenta Iniciar execução e roteia ato.

    1) cria GIG '1/Ana Lucia/Argos'      (try independente)
    2) cria GIG '1//xs sigilo'            (try independente — não bloqueado por falha do 1)
    3) tenta clicar 'Iniciar execução' via movimentar_inteligente
       - sucesso → ato_pesquisas (processo já está em execução)
       - falha   → roteia por fase:
           'liquid'/'homolog' → ato_pesqliq
           caso contrário     → ato_pesquisas

    Retorna o resultado da ação executada (tupla ou bool).
    """
    m = _lazy_import()
    criar_gigs = m.get('criar_gigs')
    ato_pesquisas = m.get('ato_pesquisas')
    ato_pesqliq = m.get('ato_pesqliq')
    resultado = (False, False)

    if texto_normalizado:
        logger.debug('[FLUXO_PZ] inicar_exec texto_normalizado comprimento=%d', len(texto_normalizado))

    # 1) GIGS Argos — try isolado
    if criar_gigs:
        try:
            from .p2b_core import parse_gigs_param
            d, r, o = parse_gigs_param('1/Ana Lucia/Argos')
            criar_gigs(driver, d, r, o)
        except Exception as e:
            logger.error('[FLUXO_PZ] inicar_exec: falha ao criar GIGS Argos: %s', e)

        # 2) GIGS xs1 (prazo 1) — try isolado (não depende do anterior)
        try:
            from .p2b_core import parse_gigs_param
            d2, r2, o2 = parse_gigs_param('1//xs1')
            criar_gigs(driver, d2, r2, o2)
        except Exception as e:
            logger.error('[FLUXO_PZ] inicar_exec: falha ao criar GIGS xs1: %s', e)

    # 3) Tentar clicar "Iniciar execução" diretamente (movimentar_inteligente)
    # — independente da fase: se o botão está na tela, clicar; senão, rotear por fase
    mov_ok = False
    try:
        from atos.movimentos_fluxo import movimentar_inteligente
        mov_ok = bool(movimentar_inteligente(driver, 'Iniciar execução', timeout=10))
        if mov_ok:
            logger.info('[FLUXO_PZ] inicar_exec: Iniciar execução clicado com sucesso')
        else:
            logger.info('[FLUXO_PZ] inicar_exec: Iniciar execução não disponível, roteando por fase')
    except Exception as e:
        logger.info('[FLUXO_PZ] inicar_exec: movimentar_inteligente falhou (%s), roteando por fase', e)

    try:
        if mov_ok:
            # Processo movido para execução → ato_pesquisas (forçar sigilo)
            if ato_pesquisas:
                resultado = ato_pesquisas(driver, sigilo=True)
        else:
            # Fallback: rotear por fase processual
            fase_lower = ''
            try:
                fase_lower = (driver.find_element(By.CSS_SELECTOR, '[class*="fase"]').text or '').lower()
            except Exception:
                pass

            if ('liquid' in fase_lower or 'homolog' in fase_lower) and ato_pesqliq:
                # Chamadas em fallback também devem forçar sigilo
                resultado = ato_pesqliq(driver, sigilo=True)
            elif ato_pesquisas:
                resultado = ato_pesquisas(driver, sigilo=True)
    except Exception as e:
        logger.error('[FLUXO_PZ] inicar_exec: erro no roteamento: %s', e)

    try:
        sucesso, sigilo_ativado = resultado if isinstance(resultado, tuple) else (bool(resultado), False)
    except Exception:
        sucesso, sigilo_ativado = (False, False)

    if sucesso and sigilo_ativado:
        try:
            from atos.wrappers_utils import executar_visibilidade_sigilosos_se_necessario
            executar_visibilidade_sigilosos_se_necessario(driver, sigilo_ativado, debug=True)
        except Exception as e:
            logger.error('[FLUXO_PZ] inicar_exec: erro aplicando visibilidade: %s', e)

    return resultado

# ===== VALIDAÇÃO =====

if __name__ == "__main__":
    pass

    # Teste importações
    try:
        from Prazo.p2b_core import normalizar_texto, gerar_regex_geral
        pass

        # Teste funções básicas
        teste = "TESTE ÁCÊNTÖS"
        resultado = normalizar_texto(teste)
        pass

    except ImportError as e:
        logger.error(f" Erro de importação: {e}")

    pass
