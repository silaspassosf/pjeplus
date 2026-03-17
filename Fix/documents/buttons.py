import logging
logger = logging.getLogger(__name__)

"""
Fix.documents.buttons - Módulo de criação de botões de detalhes para PJe.

Parte da refatoração do Fix/core.py para melhor granularidade IA.
"""

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def criar_botoes_detalhes(driver: WebDriver) -> None:
    """
    Cria botões com ícones e ações específicas, replicando a funcionalidade do MaisPje, usando o driver já autenticado.
    """
    try:
        base_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pjextension_bt_detalhes_base"))
        )
    except:
        base_element = driver.find_element(By.TAG_NAME, "body")

    # Cria o container se não existir
    if not driver.find_elements(By.ID, "pjextension_bt_detalhes_base"):
        container = driver.execute_script(
            "var div = document.createElement('div');"
            "div.id = 'pjextension_bt_detalhes_base';"
            "div.style = 'float: left';"
            "div.setAttribute('role', 'toolbar');"
            "document.body.appendChild(div);"
            "return div;"
        )
    else:
        container = driver.find_element(By.ID, "pjextension_bt_detalhes_base")

    # Configuração dos botões
    buttons = [
        {"title": "Abrir o Gigs", "icon": "fa fa-tag", "action": "abrir_gigs"},
        {"title": "Expedientes", "icon": "fa fa-envelope", "action": "acao_botao_detalhes('Expedientes')"},
        {"title": "Lembretes", "icon": "fas fa-thumbtack", "action": "acao_botao_detalhes('Lembretes')"},
    ]

    for button in buttons:
        driver.execute_script(
            f"var a = document.createElement('a');"
            f"a.title = '{button['title']}';"
            f"a.style = 'cursor: pointer; position: relative; vertical-align: middle; padding: 5px; top: 5px; z-index: 1; opacity: 1; font-size: 1.5rem; margin: 5px;';"
            f"a.onmouseover = function() {{ a.style.opacity = 0.5; }};"
            f"a.onmouseleave = function() {{ a.style.opacity = 1; }};"
            f"var i = document.createElement('i');"
            f"i.className = '{button['icon']}';"
            f"a.appendChild(i);"
            f"a.onclick = function() {{ {button['action']} }};"
            f"document.getElementById('pjextension_bt_detalhes_base').appendChild(a);"
        )
    driver.execute_script(
        "setTimeout(function() {"
        "  var div = document.getElementById('pjextension_bt_detalhes_base');"
        "  if (div) { div.style.display='none'; div.offsetHeight; div.style.display=''; }"
        "}, 100);"
    )