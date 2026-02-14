import logging
logger = logging.getLogger(__name__)

"""Módulo PEC - Processamento de Execução e Cumprimento (PJe)."""

from typing import Any

from .regras import determinar_acoes_por_observacao
from .regras import executar_acao_pec, chamar_funcao_com_assinatura_correta
from .executor import executar_acao as executar_acao_base


# ===== IMPORTS PESADOS REMOVIDOS (LAZY LOADING) =====
# Movidos para cache sob demanda para carregamento 8-10x mais rápido

# Cache de módulos para lazy loading
_pec_modules_cache = {}


def _lazy_import_pec():
    """Carrega módulos pesados sob demanda (lazy loading)."""
    global _pec_modules_cache
    
    if not _pec_modules_cache:
        from Fix.core import aguardar_e_clicar, esperar_elemento
        from Fix.extracao import extrair_dados_processo, abrir_detalhes_processo, trocar_para_nova_aba, reindexar_linha
        from atos import pec_excluiargos
        
        _pec_modules_cache.update({
            'aguardar_e_clicar': aguardar_e_clicar,
            'esperar_elemento': esperar_elemento,
            'extrair_dados_processo': extrair_dados_processo,
            'abrir_detalhes_processo': abrir_detalhes_processo,
            'trocar_para_nova_aba': trocar_para_nova_aba,
            'reindexar_linha': reindexar_linha,
            'pec_excluiargos': pec_excluiargos,
        })
    
    return _pec_modules_cache


def executar_acao(driver, acao, numero_processo, observacao, destinatarios_override=None, driver_sisb=None):
    """
    Executa a ação determinada no processo aberto.
    Suporta apenas funções diretas (como P2B) e listas de funções para execução sequencial.
    Detecta a assinatura de cada função para chamar com os argumentos corretos.
    
    Args:
        driver_sisb: Driver SISBAJUD opcional para reutilização (evita criar múltiplos drivers)
    """
    return executar_acao_base(
        driver,
        acao,
        numero_processo,
        observacao,
        destinatarios_override,
        driver_sisb
    )


def processar_processo_pec_individual(driver):
    """
    Callback específico para processar um processo individual no PEC
    Usado pelo sistema centralizado de retry do PJE.PY
    
    Esta função foca APENAS na lógica específica do PEC,
    sem se preocupar com retry, progresso ou navegação para /detalhe
    """
    try:
        # 1. Extrair dados do processo atual
        numero_processo = extrair_numero_processo_pec(driver)
        if not numero_processo:
            print("[PEC_INDIVIDUAL] ❌ Não foi possível extrair número do processo")
            return False
        
        # 2. Indexar processo atual para obter observação
        processo_atual = indexar_processo_atual_gigs(driver)
        if not processo_atual:
            print("[PEC_INDIVIDUAL] ❌ Falha ao extrair dados do processo atual")
            return False
        
        _, observacao = processo_atual
        print(f"[PEC_INDIVIDUAL] Processo: {numero_processo} | Observação: {observacao}")
        
        # 3. Determinar ações baseadas na observação (AQUI, UMA VEZ)
        acoes = determinar_acoes_por_observacao(observacao)
        acao = acoes[0] if acoes else None  # Para compatibilidade com código antigo
        print(f"[PEC_INDIVIDUAL] Ações determinadas: {[a.__name__ if callable(a) else str(a) for a in acoes]}")
        
        # 4. Pular processos sem ação definida
        if acao is None:
            print(f"[PEC_INDIVIDUAL] ⏭️ Pulando processo (ação não definida)")
            return True  # Considera sucesso para não retry
        
        # 6. Preparar override de destinatário (se a observação contiver um nome após o comando)
        destinatarios_override = None
        try:
            import re
            # Padrão: 'pec dec Nome Sobrenome', 'pec edital Nome', 'pec idpj Nome'
            m = re.match(r'^(?:pec\s*(?:dec|edital|idpj)\b)\s+(.+)$', observacao.strip(), re.I)
            if m:
                nome_cand = m.group(1).strip()
                # Tomar até a primeira vírgula ou hífen ou parenteses
                nome_cand = re.split(r'[,-\(\\)]', nome_cand)[0].strip()
                # Remover títulos comuns
                nome_cand = re.sub(r'^(sr\.?|sra\.?|dr\.?|dra\.?|srta\.?|srta)\s+', '', nome_cand, flags=re.I).strip()
                # Validar tamanho mínimo
                if len(nome_cand) >= 3 and re.search('[A-Za-zÀ-ÖØ-öø-ÿ]', nome_cand):
                    destinatarios_override = {'nome': nome_cand}
                    print(f"[PEC_INDIVIDUAL][DEST_OVERRIDE] Nome extraído para override: '{nome_cand}'")
        except Exception as e_parse:
            print(f"[PEC_INDIVIDUAL][DEST_OVERRIDE][WARN] Falha ao tentar extrair nome da observação: {e_parse}")

        # 7. Executar ação específica (sem os parâmetros antigos que não usamos mais)
        # ✨ NOVO: Tentar obter driver_sisb do contexto global (se existir)
        driver_sisb = getattr(driver, '_driver_sisb_compartilhado', None)
        
        sucesso_acao = executar_acao_pec(
            driver,
            acao,
            numero_processo=numero_processo,
            observacao=observacao,
            debug=True,
            driver_sisb=driver_sisb
        )
        
        if sucesso_acao:
            print(f"[PEC_INDIVIDUAL] ✅ Ação executada com sucesso")
            return True
        else:
            print(f"[PEC_INDIVIDUAL] ❌ Falha na execução da ação '{acao}'")
            return False
        
    except Exception as e:
        print(f"[PEC_INDIVIDUAL] ❌ Erro no processamento: {e}")
        return False
