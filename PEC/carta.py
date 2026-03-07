import logging
import time

from PEC.anexos.core import carta_wrapper, salvar_conteudo_clipboard
from PEC.carta_ecarta import coletar_intimacoes, coletar_tabela_ecarta
from PEC.carta_formatacao import formatar_dados_ecarta
from PEC.carta_utils import _obter_numero_processo


logger = logging.getLogger(__name__)


def carta(driver, log=True, limite_intimacoes=None):
    """Orquestra o fluxo de carta eCarta no PJe."""
    process_number = _obter_numero_processo(driver, log)

    t_ci = time.time()
    intimation_ids, intimacoes_info = coletar_intimacoes(
        driver, limite_intimacoes=limite_intimacoes, log=log
    )
    dur_ci = time.time() - t_ci
    if log:
        logger.info(f"[CARTA] coletar_intimacoes retornou {len(intimation_ids)} ids (took {dur_ci:.2f}s): {intimation_ids}")

    if not intimation_ids:
        if log:
            logger.error("[CARTA] Nenhuma intimacao de correio encontrada.")
        return ""

    if not process_number:
        process_number = _obter_numero_processo(driver, log)
        if not process_number:
            if log:
                logger.error(
                    "[CARTA][ERRO] Nao foi possivel obter o numero do processo via dadosatuais.json."
                )
            return ""

    t_ct = time.time()
    table_data = coletar_tabela_ecarta(driver, process_number, intimation_ids, log=log)
    dur_ct = time.time() - t_ct
    if log:
        logger.info(f"[CARTA] coletar_tabela_ecarta retornou {len(table_data) if table_data else 0} registros (took {dur_ct:.2f}s)")

    if not table_data:
        if log:
            logger.error("[CARTA] Nenhuma correlacao encontrada no eCarta.")
        return ""

    conteudo_final, html_para_juntada, _prazo_texto = formatar_dados_ecarta(
        table_data, intimacoes_info, log=log
    )
    if not conteudo_final:
        if log:
            logger.error("[CARTA] Falha ao formatar dados do eCarta.")
        return ""

    try:
        sucesso = salvar_conteudo_clipboard(
            conteudo=conteudo_final,
            numero_processo=process_number,
            tipo_conteudo="ecarta",
            debug=log,
        )
        if log and not sucesso:
            logger.error("[CARTA] Falha ao salvar via funcao centralizada do clipboard.")
    except Exception as e:
        if log:
            logger.error(f"[CARTA] Erro ao salvar clipboard: {e}")

    try:
        resultado_juntada = carta_wrapper(
            driver,
            numero_processo=process_number,
            debug=log,
            ecarta_html=html_para_juntada,
        )
        if log and not resultado_juntada:
            logger.error("[CARTA] Juntada automatica falhou ou foi pulada.")
            return False
            
    except Exception as e:
        if log:
            logger.error(f"[CARTA] Erro na juntada automatica: {e}")
        return False

    return True
