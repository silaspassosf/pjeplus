import logging
logger = logging.getLogger(__name__)

"""
@module: Fix.forms.multiple_fields
@responsibility: Preenchimento de múltiplos campos com otimização JS
@depends_on: Fix.selenium_base.element_interaction, Fix.core (js_base)
@used_by: Módulos que precisam preencher vários campos de uma vez
@entry_points: preencher_multiplos_campos
@tags: #forms #multiple #js #optimization
@created: 2026-02-06
@refactored_from: Fix/core.py lines 1055-1135
"""

from typing import Dict, Union
from selenium.webdriver.remote.webdriver import WebDriver

from ..log import logger
from ..selenium_base.js_helpers import js_base

# Variáveis de compatibilidade
import os
DEBUG = os.getenv('PJEPLUS_DEBUG', '0').lower() in ('1', 'true', 'on')

def _log_info(msg: str) -> None:
    """Compatibilidade com logs antigos"""
    logger.info(msg)

def _log_error(msg: str) -> None:
    """Compatibilidade com logs antigos"""
    logger.error(msg)

def _audit(action: str, target: str, status: str, extra: dict = None) -> None:
    """Compatibilidade com auditoria antiga"""
    if extra:
        logger.debug(f"[AUDIT] {action}:{target}:{status} {extra}")
    else:
        logger.debug(f"[AUDIT] {action}:{target}:{status}")

def preencher_multiplos_campos(driver: WebDriver, campos_dict: Dict[str, Union[str, int]], log: bool = False) -> Dict[str, bool]:
    """
    Preenche múltiplos campos em uma única operação JavaScript
    Otimização extra: N campos = 1 requisição (vs N requisições)

    Args:
        driver: WebDriver Selenium
        campos_dict: Dict {seletor: valor}
        log: Ativa logging

    Returns:
        Dict {seletor: True/False} indicando sucesso de cada campo

    Exemplo:
        resultado = preencher_multiplos_campos(driver, {
            '#nome': 'João Silva',
            '#email': 'joao@email.com',
            '#telefone': '11999999999'
        })
    """
    try:
        # Construir array JavaScript de campos
        campos_js = []
        for seletor, valor in campos_dict.items():
            valor_escapado = str(valor).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
            campos_js.append(f"{{'seletor': '{seletor}', 'valor': '{valor_escapado}'}}")

        campos_array = "[" + ", ".join(campos_js) + "]"

        script = f"""
        {js_base()}

        let campos = {campos_array};
        let resultados = {{}};

        for (let campo of campos) {{
            try {{
                let elemento = document.querySelector(campo.seletor);
                if (elemento) {{
                    elemento.value = campo.valor;
                    triggerEvent(elemento, 'input');
                    triggerEvent(elemento, 'change');
                    resultados[campo.seletor] = true;
                }} else {{
                    resultados[campo.seletor] = false;
                }}
            }} catch(e) {{
                resultados[campo.seletor] = false;
            }}
        }}

        return resultados;
        """

        resultado = driver.execute_script(script)

        if log:
            for seletor, sucesso in resultado.items():
                status = "" if sucesso else ""
                _log_info(f"Campo {seletor}: {status}")

        return resultado
    except Exception as e:
        if log:
            _log_error(f"Erro ao preencher múltiplos campos: {e}")
        return {seletor: False for seletor in campos_dict.keys()}