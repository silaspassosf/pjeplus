from Fix.core import safe_click
from Fix.log import logger
from Fix.extracao import bndt
from Fix import espera
from typing import Any
import re
from datetime import datetime, timedelta

from .judicial_fluxo import ato_judicial
from .wrappers_ato import ato_bloq, ato_meios


def ato_pesquisas(driver: Any, debug: bool = False, gigs: Any = None, **kwargs: Any):
    """Ato de pesquisas (BACEN): sigilo + VISIBILIDADE da decisão após o ato.

    IMPORTANTE: devolve (sucesso, sigilo_ativado) — é o sinal que dispara a
    atribuição de visibilidade em `ato_judicial` quando
    `atribuir_visibilidade_autor=True` (recuperado do pre-refac).
    """
    try:
        try:
            btn_iniciar = espera.elemento(driver, "button[aria-label*='Iniciar a execução'], button[mattooltip*='Iniciar a execução']", teto=1)
            if btn_iniciar and getattr(btn_iniciar, 'is_displayed', lambda: True)() and getattr(btn_iniciar, 'is_enabled', lambda: True)():
                safe_click(driver, btn_iniciar)
                espera.assentar(driver, 1)
        except Exception:
            pass
        
        # Recuperado do pre-refac: este ato sempre aplica sigilo, ATRIBUI
        # VISIBILIDADE À DECISÃO após o ato judicial e DESLIGA o toggle
        # INTIMAR (intimar=False). `setdefault` preserva overrides explícitos
        # do chamador (ex.: p2b_gateway passa sigilo=True).
        params = dict(kwargs)
        params.setdefault('sigilo', True)
        params.setdefault('atribuir_visibilidade_autor', True)
        params.setdefault('descricao', 'Pesquisas para execução')
        params.setdefault('intimar', False)

        sucesso, sigilo_ativado = ato_judicial(
            driver,
            conclusao_tipo='BACEN',
            modelo_nome='xsbacen',
            prazo=30,
            marcar_pec=False,
            movimento='bloqueio',
            gigs=gigs,
            marcar_primeiro_destinatario=True,
            debug=debug,
            **params
        )
        return sucesso, sigilo_ativado
    except Exception as e:
        logger.error(f"[JUDICIAL][PESQUISAS] Erro: {e}")
        try:
            driver.save_screenshot('erro_ato_pesquisas.png')
        except Exception:
            pass
        return False, False


def idpj(
    driver: Any,
    debug: bool = False
) -> bool:
    try:
        tem_bloqueio_recente = verificar_bloqueio_recente(driver, debug=debug)
        
        try:
            bndt(driver, operacao="inclusao", polo="passivo", debug=debug)
        except Exception as e:
            logger.error(f"[IDPJ] Erro no BNDT inclusão: {e}")
        
        if tem_bloqueio_recente:
            resultado = ato_bloq(driver, debug=debug)
        else:
            resultado = ato_meios(driver, debug=debug)
        
        return resultado
    except Exception as e:
        logger.error(f"[IDPJ] Erro no fluxo IDPJ: {e}")
        return False
