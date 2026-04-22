from typing import Optional, Tuple, Dict, List, Union, Callable, Any

from selenium.webdriver.remote.webdriver import WebDriver

from .judicial_fluxo import fluxo_cls as _fluxo_cls
from .judicial_fluxo import ato_judicial as _ato_judicial, make_ato_wrapper as _make_ato_wrapper
from .judicial_helpers import (
    ato_pesquisas as _ato_pesquisas,
    idpj as _idpj,
    preencher_prazos_destinatarios as _preencher_prazos_destinatarios,
    verificar_bloqueio_recente as _verificar_bloqueio_recente,
)

# Wrappers centralizados em wrappers_ato.py
from .wrappers_ato import (
    ato_meios,
    ato_100,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    ato_sobrestamento,
    ato_prov,
    ato_180,
    ato_x90,
    ato_pesqliq_original,
    ato_pesqliq,
    ato_calc2,
    ato_meiosub,
    ato_presc,
    ato_fal,
    ato_parcela,
)


def fluxo_cls(
    driver: WebDriver,
    conclusao_tipo: str,
    forcar_iniciar_execucao: bool = False
) -> bool:
    """Wrapper para atos.judicial_fluxo.fluxo_cls com navegação inteligente via mov_cls."""
    return _fluxo_cls(driver, conclusao_tipo, forcar_iniciar_execucao=forcar_iniciar_execucao)


def ato_judicial(
    driver: WebDriver,
    conclusao_tipo: Optional[str] = None,
    modelo_nome: Optional[str] = None,
    prazo: Optional[int] = None,
    marcar_pec: Optional[bool] = None,
    movimento: Optional[str] = None,
    gigs: Optional[Any] = None,
    marcar_primeiro_destinatario: Optional[bool] = None,
    debug: bool = False,
    sigilo: Optional[str] = None,
    descricao: Optional[str] = None,
    perito: bool = False,
    Assinar: bool = False,
    coleta_conteudo: Optional[Callable] = None,
    inserir_conteudo: Optional[Callable] = None,
    intimar: Optional[bool] = None,
    **kwargs: Any
) -> bool:
    """Wrapper para atos.judicial_ato.ato_judicial."""
    return _ato_judicial(
        driver,
        conclusao_tipo=conclusao_tipo,
        modelo_nome=modelo_nome,
        prazo=prazo,
        marcar_pec=marcar_pec,
        movimento=movimento,
        gigs=gigs,
        marcar_primeiro_destinatario=marcar_primeiro_destinatario,
        debug=debug,
        sigilo=sigilo,
        descricao=descricao,
        perito=perito,
        Assinar=Assinar,
        coleta_conteudo=coleta_conteudo,
        inserir_conteudo=inserir_conteudo,
        intimar=intimar,
        **kwargs
    )


def make_ato_wrapper(conclusao_tipo: str, modelo_nome: str, prazo: Optional[int] = None, marcar_pec: Optional[bool] = None, movimento: Optional[str] = None, gigs: Optional[Any] = None, marcar_primeiro_destinatario: Optional[bool] = None, descricao: Optional[str] = None, sigilo: Optional[str] = None, perito: bool = False, Assinar: bool = False, coleta_conteudo: Optional[Callable] = None, inserir_conteudo: Optional[Callable] = None, intimar: Optional[bool] = None) -> Callable[[WebDriver, bool, Any], bool]:
    """Wrapper para atos.judicial_ato.make_ato_wrapper."""
    return _make_ato_wrapper(
        conclusao_tipo,
        modelo_nome,
        prazo=prazo,
        marcar_pec=marcar_pec,
        movimento=movimento,
        gigs=gigs,
        marcar_primeiro_destinatario=marcar_primeiro_destinatario,
        descricao=descricao,
        sigilo=sigilo,
        perito=perito,
        Assinar=Assinar,
        coleta_conteudo=coleta_conteudo,
        inserir_conteudo=inserir_conteudo,
        intimar=intimar,
    )


def ato_pesquisas(driver, debug=False, gigs=None, **kwargs):
    """Wrapper para atos.judicial_helpers.ato_pesquisas."""
    return _ato_pesquisas(driver, debug=debug, gigs=gigs, **kwargs)


def idpj(
    driver: WebDriver,
    debug: bool = False
) -> bool:
    """Wrapper para atos.judicial_helpers.idpj."""
    return _idpj(driver, debug=debug)


def preencher_prazos_destinatarios(driver, prazo, apenas_primeiro=False, perito=False, perito_nomes=None):
    """Wrapper para atos.judicial_helpers.preencher_prazos_destinatarios."""
    return _preencher_prazos_destinatarios(
        driver,
        prazo,
        apenas_primeiro=apenas_primeiro,
        perito=perito,
        perito_nomes=perito_nomes,
    )


def verificar_bloqueio_recente(driver, debug=False):
    """Wrapper para atos.judicial_helpers.verificar_bloqueio_recente."""
    return _verificar_bloqueio_recente(driver, debug=debug)
