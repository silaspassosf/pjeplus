from selenium.webdriver.remote.webdriver import WebDriver

from Fix.extracao import criar_lembrete_posit


def lembrete_bloq(driver: WebDriver, debug: bool = False) -> bool:
    """Wrapper compatível - delegado para criar_lembrete_posit genérico."""
    return criar_lembrete_posit(
        driver,
        titulo="Bloqueio pendente",
        conteudo="processar após IDPJ",
        debug=debug
    )