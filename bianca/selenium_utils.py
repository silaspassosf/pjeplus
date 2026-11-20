"""bianca.selenium_utils — delega para os helpers Playwright nativos canônicos de Fix/."""

import logging
from typing import Any

from Fix import espera
from Fix.abas import fechar_abas_extras  # noqa: F401
from Fix.browser_suporte import (  # noqa: F401
    limpar_overlays_headless,
    trocar_para_nova_aba,
)
from Fix.core import (  # noqa: F401
    aguardar_e_clicar,
    aguardar_renderizacao_nativa,
    aplicar_filtro_100,
    buscar_seletor_robusto,
    com_retry,
    esperar_elemento,
    filtrofases,
    preencher_campo,
    safe_click,
    safe_click_no_scroll,
    selecionar_opcao,
)
from Fix.entrada_campos import _fechar_dropdown_ou_esc  # noqa: F401
from Fix.extracao import _pressionar_tecla  # noqa: F401
from Fix.filtros_painel import _aguardar_loader_painel  # noqa: F401
from Fix.navegacao import (  # noqa: F401
    _clicar_botao_movimentar,
    _clicar_botao_tarefa_processo,
    js_base,
)

logger = logging.getLogger(__name__)


def _sub_el(parent: Any, seletor: str) -> Any:
    return espera.elemento(parent, seletor, teto=0.2)


def _sub_els(parent: Any, seletor: str) -> list:
    return espera.elementos(parent, seletor, teto=0.2)


def resetar_driver(driver: Any) -> bool:
    """Reseta estado do driver para pagina inicial do PJe."""
    try:
        fechar_abas_extras(driver)
        espera._executar_script(driver, "document.body.style.zoom='100%'")
        if hasattr(driver, "get"):
            driver.get("https://pje.trt2.jus.br/pjekz/")
        elif hasattr(driver, "page") and hasattr(driver.page, "goto"):
            driver.page.goto("https://pje.trt2.jus.br/pjekz/")
        espera.ate_url(driver, "pjekz", teto=5)
        aguardar_renderizacao_nativa(driver)
        return True
    except Exception as e:
        logger.warning("Falha ao resetar driver: %s", e)
        return False
