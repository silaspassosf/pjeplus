"""Módulo PEC - Processamento de Execução e Cumprimento (PJe)."""

from .core_progresso import (
    carregar_progresso_pec,
    salvar_progresso_pec,
    extrair_numero_processo_pec,
    verificar_acesso_negado_pec,
    processo_ja_executado_pec,
    marcar_processo_executado_pec,
)
from .core_recovery import verificar_e_recuperar_acesso_negado, reiniciar_driver_e_logar_pje
from .core_navegacao import navegar_para_atividades, aplicar_filtro_xs, indexar_processo_atual_gigs
from .core_pos_carta import analisar_documentos_pos_carta
from .core_main import main




import os
import requests
from typing import List, Dict, Any

# buckets config
from .buckets import BUCKETS_PEC


# ---------------------------------------------------------------------------
# CHAMADA DE API — GIGS VENCIDO + OBSERVAÇÃO POR BUCKET
# ---------------------------------------------------------------------------
def _buscar_processos_bucket_api(trt: str, bucket_config: Dict[str, Any]) -> List[str]:
    tipo_atividade = bucket_config.get("tipo_atividade", "")
    observacao = bucket_config.get("observacao", "")
    try:
        url = f"https://pje.trt{trt}.jus.br/pje-comum-api/api/gigs/atividades"
        params = {
            "tipoAtividade": tipo_atividade,
            "observacao": observacao,
            "prazoVencido": "true",
            "pagina": 1,
            "tamanhoPagina": 500,
        }
        resp = requests.get(url, params=params, timeout=30)
        if not resp.ok:
            logger.warning(f"PEC/API WARN bucket '{tipo_atividade}' HTTP {resp.status_code}")
            return []

        dados = resp.json()
        processos = [
            item.get("numeroProcesso") or item.get("numero", "")
            for item in dados.get("resultado", [])
            if item.get("numeroProcesso") or item.get("numero")
        ]
        logger.info(f"PEC/API bucket '{tipo_atividade}'/'{observacao}' → {len(processos)} processo(s)")
        return processos

    except Exception as e:
        logger.warning(f"PEC/API ERRO bucket '{tipo_atividade}': {e}")
        return []


def _construir_grupos_execucao(trt: str, buckets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grupos = []
    for bucket in buckets:
        processos = _buscar_processos_bucket_api(trt, bucket)
        if processos:
            grupos.append({"bucket": bucket, "processos": processos})
    return grupos


# ---------------------------------------------------------------------------
# PONTO DE ENTRADA — iniciar fluxo robusto usando API para montar listas
# ---------------------------------------------------------------------------
def iniciarfluxorobusto(driver) -> Dict[str, Any]:
    progresso = carregar_progresso_pec()
    logger.info(
        f"PROGRESSO/SESSAO Carregado progresso com {len(progresso.get('processos_executados', []))} processos já executados"
    )

    trt = os.getenv("TRT_NUM", "2")
    from core.resultado_execucao import ResultadoExecucao
    grupos_execucao = _construir_grupos_execucao(trt, BUCKETS_PEC)
    if not grupos_execucao:
        logger.warning("PEC Nenhum processo encontrado via API para os buckets configurados.")
        return ResultadoExecucao(sucesso=False, processos=0)
    logger.info(
        f"PEC {sum(len(g['processos']) for g in grupos_execucao)} processo(s) distribuído(s) em {len(grupos_execucao)} bucket(s) ativos."
    )
    total_processados = 0
    for grupo in grupos_execucao:
        bucket = grupo["bucket"]
        lista = grupo["processos"]
        logger.info(f"PEC Iniciando bucket '{bucket.get('tipo_atividade')}' — {len(lista)} processo(s)")
        for numero_cnj in lista:
            progresso = carregar_progresso_pec()
            if processo_ja_executado_pec(numero_cnj, progresso):
                logger.info(f"PEC SKIP {numero_cnj} já executado")
                continue
            sucesso = _abrir_executar_fechar(driver, numero_cnj, bucket)
            if sucesso:
                marcar_processo_executado_pec(numero_cnj, progresso)
                total_processados += 1
    return ResultadoExecucao(sucesso=True, processos=total_processados)


def _abrir_executar_fechar(driver, numero_cnj: str, bucket: Dict[str, Any]) -> bool:
    try:
        url_processo = _montar_url_processo(numero_cnj)
        driver.get(url_processo)
        aguardarenderizacao_nativa(driver)

        resultado = fluxo_pec_bucket(driver, bucket)
        return bool(resultado)

    except Exception as e:
        logger.error(f"PEC ERRO {numero_cnj}: {e}")
        return False
    finally:
        try:
            _fechar_abas_extras(driver)
        except Exception:
            pass




