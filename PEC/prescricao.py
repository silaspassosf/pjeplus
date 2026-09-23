import logging
logger = logging.getLogger(__name__)

"""Análise de prescrição - função def_presc."""


import re
import time
from datetime import datetime, timedelta
from typing import Optional, Any
from Fix.abas import aguardar_nova_aba
from Fix.extracao import criar_lembrete_posit
from Fix.core import buscar_documentos_polo_ativo, esperar_elemento
from atos.movimentos import mov_fimsob, mov_sob
from atos.judicial import ato_presc
import traceback


def def_presc(driver: Any, numero_processo: str, texto_decisao: str, data_decisao_str: Optional[str] = None, debug: bool = False) -> bool:
    """
    Analisa timeline para determinar prescrição.
    
    Regras (ordem do legado — LEGADO.md 31478-31813):
    1. SEM documento recente do autor (180 dias) e mais de 2 anos + 10 dias desde
       a decisão → mov_fimsob + ato_presc (na nova aba da tarefa);
    2. SEM documento do autor e até 2 anos + 10 dias → mov_sob 1 mês;
    3. Decisão com menos de 2 anos E documento recente do autor
       → lembrete de reinício + mov_sob 23 meses;
    4. Caso padrão (prescrição interrompida) → nada a executar (True).
    
    Args:
        driver: conexao/driver PJe
        numero_processo: Número do processo
        texto_decisao: Texto da decisão analisada
        data_decisao_str: Data da decisão no formato DD/MM/YYYY
        debug: Se True, exibe logs detalhados
    
    Returns:
        bool: True se executado com sucesso
    """
    # Guard clauses
    if not driver:
        if debug:
            logger.info("[DEF_PRESC] ERRO: driver não fornecido")
        return False
    
    if not numero_processo or not isinstance(numero_processo, str):
        if debug:
            logger.info("[DEF_PRESC] ERRO: numero_processo inválido")
        return False
    
    if not texto_decisao or not isinstance(texto_decisao, str):
        if debug:
            logger.info("[DEF_PRESC] ERRO: texto_decisao inválido")
        return False
    
    def log_msg(msg):
        if debug:
            logger.info(f"[DEF_PRESC] {msg}")
    
    log_msg(f"Iniciando análise de prescrição para processo {numero_processo}")
    
    try:
        data_atual = datetime.now()
        limite_autor = data_atual - timedelta(days=180)

        # ── Data da decisão: parâmetro → texto da decisão → data atual ──
        data_decisao_dt = _converter_data(data_decisao_str)
        if not data_decisao_dt:
            data_decisao_dt = _converter_data((texto_decisao or '')[:500])
            if data_decisao_dt:
                log_msg(f"Data da decisão extraída do texto: {data_decisao_dt:%d/%m/%Y}")
        if not data_decisao_dt:
            data_decisao_dt = data_atual
            log_msg(f"Data da decisão indisponível — usando data atual ({data_atual:%d/%m/%Y})")

        # ── Guard: a timeline precisa existir para concluir "sem autor" ──
        if not esperar_elemento(driver, 'li.tl-item-container', timeout=10):
            log_msg("Timeline não encontrada — não é possível avaliar a prescrição")
            return False

        # ── Documentos do polo ativo (autor) nos últimos 6 meses ──
        documentos_autor_recentes = []
        documentos = buscar_documentos_polo_ativo(driver, polo="autor", limite_dias=180, debug=debug) or []
        for doc in documentos:
            data_doc = _converter_data(doc.get('data'))
            if not data_doc:
                continue
            nome_doc = doc.get('titulo', '')
            if data_doc >= limite_autor:
                documentos_autor_recentes.append({'data': data_doc, 'nome': nome_doc})
                log_msg(f"Documento do autor nos últimos 6 meses: {nome_doc} ({data_doc:%d/%m/%Y})")
            else:
                log_msg(f"Documento do autor fora do período: {nome_doc} ({data_doc:%d/%m/%Y})")

        tem_documentos_autor = bool(documentos_autor_recentes)
        dias_desde_decisao = (data_atual - data_decisao_dt).days
        limite_2anos_10dias = 730 + 10
        log_msg(
            f"Data da decisão: {data_decisao_dt:%d/%m/%Y} | dias decorridos: {dias_desde_decisao} | "
            f"autor recente: {tem_documentos_autor}"
        )

        # ── REGRAS 1 e 2: sem documento do autor ──
        if not tem_documentos_autor:
            if dias_desde_decisao > limite_2anos_10dias:
                log_msg("> 2 anos e 10 dias desde a decisão e SEM autor → mov_fimsob + ato_presc")
                aba_processo = driver.current_window_handle
                if not mov_fimsob(driver, debug=debug):
                    log_msg("Falha na execução do mov_fimsob")
                    return False
                # mov_fimsob abre a tarefa em nova aba — o CLS continua nela
                try:
                    driver.switch_to.window(aguardar_nova_aba(driver, aba_processo, timeout=10))
                    log_msg("Trocado para a nova aba da tarefa após mov_fimsob")
                except Exception:
                    log_msg("Nenhuma aba nova detectada após mov_fimsob — seguindo na aba atual")
                if ato_presc(driver, debug=debug):
                    log_msg("ato_presc executado com sucesso")
                    return True
                log_msg("Falha na execução do ato_presc")
                return False

            log_msg("<= 2 anos e 10 dias desde a decisão e SEM autor → mov_sob 1 mês")
            if mov_sob(driver, numero_processo, "sob 1", debug=debug, timeout=30):
                log_msg("mov_sob 1 mês executado com sucesso")
                return True
            log_msg("Falha na execução do mov_sob 1 mês")
            return False

        # ── REGRA 3: decisão com menos de 2 anos + autor recente ──
        if data_decisao_dt > (data_atual - timedelta(days=730)):
            log_msg("Data da decisão < 2 anos + autor recente → lembrete + mov_sob 23 meses")
            conteudo_lembrete = f"Sobrestamento reiniciado em {data_atual:%m/%Y} por manifestação recente"
            try:
                if criar_lembrete_posit(driver, "prescrição", conteudo_lembrete, debug=debug):
                    log_msg("Lembrete criado com sucesso")
                else:
                    log_msg("Falha ao criar lembrete — continuando com mov_sob")
            except Exception as e:
                log_msg(f"Erro ao criar lembrete: {e} — continuando com mov_sob")
            if mov_sob(driver, numero_processo, "sob 23", debug=debug):
                log_msg("mov_sob 23 meses executado com sucesso")
                return True
            log_msg("Falha na execução do mov_sob 23")
            return False

        # ── Caso padrão ──
        log_msg("Prescrição INTERROMPIDA: decisão com 2+ anos e documento recente do autor")
        return True

    except Exception as e:
        logger.error(f"[DEF_PRESC] Erro geral: {e}")
        logger.error(traceback.format_exc())
        return False


_MESES_ABREV = {
    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
    'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12',
}


def _dt(dia: str, mes: str, ano: str) -> Optional[datetime]:
    """Monta datetime a partir de dia/mês/ano já normalizados."""
    try:
        return datetime(int(ano), int(mes), int(dia))
    except (TypeError, ValueError):
        return None


def _converter_data(data_texto: Optional[str]) -> Optional[datetime]:
    """Converte 'DD/MM/AAAA', 'DD-MM-AAAA' ou 'DD mar. AAAA' em datetime.

    Portado do legado (LEGADO.md 31606-31637): a timeline do PJe usa tanto data
    numérica quanto abreviação de mês com ponto.
    """
    if not data_texto:
        return None
    texto = str(data_texto)
    match = re.search(r'(\d{1,2})\s+([A-Za-zÀ-ÿ]{3})\.?\s+(\d{4})', texto)
    if match:
        mes = _MESES_ABREV.get(match.group(2).lower()[:3])
        if mes:
            return _dt(match.group(1), mes, match.group(3))
    match = re.search(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})', texto)
    if match:
        return _dt(match.group(1), match.group(2), match.group(3))
    return None
