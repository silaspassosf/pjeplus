"""entrada_campos — interação com inputs e selects Angular/DOM (re-exportado por Fix.core)."""

import json

from Fix import espera
from Play.pjeplay.errors import NoSuchElementException, TimeoutException
from Play.pjeplay.locators import By, Keys, traduzir

from .log import logger
from .navegacao import js_base, safe_click_no_scroll  # noqa: F401

_MAPA_DROPDOWNS = {
    'destino': ['mat-select[aria-placeholder*="destino"]'],
    'fase': [
        'mat-select[formcontrolname="fpglobal_faseProcessual"]',
        'mat-select[placeholder*="Fase processual"]',
        'mat-select[aria-label*="Fase"]',
    ],
    'tipo': [
        'mat-select[formcontrolname="tipoCredito"]',
        'mat-select[formcontrolname="tipo"]',
        'mat-select[aria-label*="Tipo"]',
    ],
    'tarefa': [
        'mat-select[formcontrolname="tarefa"]',
        'mat-select[aria-label*="Tarefa"]',
        'mat-select[placeholder*="Tarefa"]',
    ],
    'situacao': [
        'mat-select[formcontrolname="situacao"]',
        'mat-select[aria-label*="Situação"]',
        'mat-select[placeholder*="Situação"]',
    ],
    'prioridade': [
        'mat-select[formcontrolname="prioridade"]',
        'mat-select[aria-label*="Prioridade"]',
    ],
    'status': [
        'mat-select[formcontrolname="status"]',
        'mat-select[aria-label*="Status"]',
    ],
}

_ESTRATEGIAS_AUTO_DROPDOWN = [
    'mat-select[formcontrolname="destinos"]',
    'mat-select[aria-label*="Tarefa destino"]',
    'mat-select[aria-label*="destino"]',
    'mat-select[placeholder*="destino"]',
    'mat-select[formcontrolname*="destino"]',
    'mat-select',
]


def buscar_seletor_robusto(driver, textos, contexto=None, timeout=5, log=False):
    """Localiza input editável, input associado por rótulo ou ícone pelo texto."""
    try:
        for texto in textos:
            for el in espera.elementos(
                driver,
                f'input[placeholder*="{texto}"], input[aria-label*="{texto}"], input[name*="{texto}"]',
            ):
                if el.is_displayed() and el.is_enabled():
                    return el
        for texto in textos:
            if espera.elementos(driver, f'//*[contains(text(), "{texto}")]'):
                inp = espera.elemento(
                    driver,
                    f'//*[contains(text(), "{texto}")]/following-sibling::input'
                    f' | //*[contains(text(), "{texto}")]/ancestor::*[contains(@class,"form-group")]//input',
                )
                if inp:
                    return inp
        for texto in textos:
            for el in espera.elementos(
                driver,
                f'i[mattooltip*="{texto}"], i[aria-label*="{texto}"], i.fa-reply-all',
            ):
                if el.is_displayed():
                    return el
        return None
    except Exception as e:
        logger.error('[ROBUSTO][ERRO GERAL] %s', e)
        return None


def _abrir_dropdown(driver, dropdown):
    """Tenta abrir mat-select/select por clique, Enter ou ArrowDown."""
    try:
        dropdown.click()
        return True
    except Exception:
        pass
    for tecla in ('Enter', 'ArrowDown'):
        try:
            if hasattr(dropdown, 'press'):
                dropdown.press(tecla)
                return True
            if hasattr(driver, 'page'):
                driver.page.keyboard.press(tecla)
                return True
        except Exception:
            continue
    return False


def _selecionar_por_lista(driver, seletores, texto_opcao, teto, exato, log):
    alvo = texto_opcao.lower()
    for seletor in seletores:
        try:
            if log:
                logger.debug('[SELECIONAR_OPCAO] Tentando seletor: %s', seletor)
            if not espera.ate_habilitar(driver, seletor, teto=teto):
                continue
            dropdown = espera.elemento(driver, seletor)
            if not dropdown or not _abrir_dropdown(driver, dropdown):
                continue
            if not espera.ate_aparecer(driver, 'mat-option[role="option"], option', teto=3):
                continue
            for opcao in espera.elementos(driver, 'mat-option[role="option"] span.mat-option-text, option'):
                try:
                    texto = opcao.text.strip().lower()
                    if (texto == alvo) if exato else (alvo in texto):
                        if log:
                            logger.debug("[SELECIONAR_OPCAO] Opcao '%s' selecionada (%s)", texto_opcao, seletor)
                        opcao.click()
                        espera.assentar(driver, 0.3)
                        return True
                except Exception:
                    continue
        except Exception as e:
            if log:
                logger.warning('[SELECIONAR_OPCAO] Seletor %s falhou: %s', seletor, e)
    return False


def selecionar_opcao(driver, seletor_dropdown, texto_opcao, timeout=10, exato=False, log=False):
    """Abre dropdown (CSS, alias conhecido ou auto-detecção) e seleciona `texto_opcao`."""
    if isinstance(seletor_dropdown, str):
        seletores = _MAPA_DROPDOWNS.get(seletor_dropdown, [seletor_dropdown])
    else:
        seletores = None

    try:
        if seletores is None:
            if _selecionar_por_lista(driver, _ESTRATEGIAS_AUTO_DROPDOWN, texto_opcao, 5, exato, log):
                return True
            if log:
                logger.error("ERRO em selecionar_opcao: auto-deteccao falhou para '%s'", texto_opcao)
            return False

        if _selecionar_por_lista(driver, seletores, texto_opcao, timeout, exato, log):
            return True

        try:
            sel_dest = 'mat-select[formcontrolname="destinos"]'
            select = espera.elemento(driver, sel_dest) if espera.ate_habilitar(driver, sel_dest, teto=10) else None
            if select:
                select.click()
                espera.assentar(driver, 1)
                painel = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
                espera.ate_aparecer(driver, painel, teto=10)
                alvo = texto_opcao.lower()
                for opcao in espera.elementos(driver, f'{painel} mat-option, mat-option'):
                    try:
                        if alvo in opcao.text.strip().lower():
                            safe_click_no_scroll(driver, opcao)
                            return True
                    except Exception:
                        continue
        except Exception as e2:
            if log:
                logger.warning('[SELECIONAR_OPCAO] Estrategia 2 falhou: %s', e2)

        try:
            sel_js = json.dumps(seletores[0] if seletores else 'mat-select')
            alvo_js = json.dumps(texto_opcao.lower())
            script = f"""
            try {{
                let dropdown = document.querySelector({sel_js}) ||
                    document.querySelector('mat-select[formcontrolname="destinos"]') ||
                    document.querySelector('mat-select[aria-label*="Tarefa destino"]') ||
                    document.querySelector('mat-select');
                if (!dropdown) return false;
                dropdown.click();
                setTimeout(() => {{
                    let opcoes = document.querySelectorAll('mat-option span.mat-option-text, .mat-option-text');
                    for (let o of opcoes) {{
                        if (o.textContent.trim().toLowerCase().includes({alvo_js})) {{ o.click(); return; }}
                    }}
                    if (opcoes.length > 0) opcoes[0].click();
                }}, 500);
                return true;
            }} catch (e) {{ return false; }}
            """
            if espera._executar_script(driver, script):
                return True
        except Exception as e3:
            if log:
                logger.warning('[SELECIONAR_OPCAO] Estrategia 3 falhou: %s', e3)

        if log:
            logger.error("ERRO em selecionar_opcao: todas as estrategias falharam para '%s'", texto_opcao)
        return False
    except Exception as e:
        if log:
            logger.error('ERRO em selecionar_opcao: %s: %s', type(e).__name__, e)
        return False


def preencher_campo(driver, seletor, valor, trigger_events=True, limpar=True, log=False):
    """Preenche campo (seletor CSS ou elemento) e dispara input/change/blur."""
    try:
        val_js = json.dumps(str(valor))
        limpar_js = 'true' if limpar else 'false'
        trig_js = 'true' if trigger_events else 'false'

        if not isinstance(seletor, str):
            script_el = f"""
            {js_base()}
            const campo = arguments[0];
            if (!campo) return false;
            if ({limpar_js}) campo.value = '';
            campo.value = {val_js};
            if ({trig_js}) {{
                triggerEvent(campo, 'input');
                triggerEvent(campo, 'change');
                triggerEvent(campo, 'blur');
            }}
            try {{ campo.blur(); }} catch (e) {{}}
            return true;
            """
            return bool(espera._executar_script(driver, script_el, seletor))

        script = f"""
        {js_base()}
        const callback = arguments[arguments.length - 1];
        esperarElemento({json.dumps(seletor)}, 5000)
            .then(campo => {{
                if (!campo) {{ callback(false); return; }}
                if ({limpar_js}) campo.value = '';
                campo.value = {val_js};
                if ({trig_js}) {{
                    triggerEvent(campo, 'input');
                    triggerEvent(campo, 'change');
                    triggerEvent(campo, 'blur');
                }}
                try {{ campo.blur(); }} catch (e) {{}}
                callback(true);
            }})
            .catch(() => callback(false));
        """
        resultado = driver.execute_async_script(script)
        if log:
            logger.debug("preencher_campo: %s = '%s' -> %s", seletor, str(valor)[:50], resultado)
        return resultado
    except Exception as e:
        if log:
            logger.warning('preencher_campo falhou: %s', e)
        return False


def preencher_campos_prazo(driver, valor=0, timeout=10, log=True):
    """Preenche todos os campos de prazo (input[type=text].mat-input-element) do formulário."""
    try:
        form_sel = '#mat-tab-content-0-0 > div > pje-intimacao-automatica > div > form'
        if not espera.ate_aparecer(driver, form_sel, teto=timeout):
            if log:
                logger.warning('[Fix.core] Formulario de minuta/comunicacao nao encontrado.')
            return False

        inputs = espera.elementos(driver, f'{form_sel} input[type="text"].mat-input-element')
        if not inputs:
            if log:
                logger.warning('[Fix.core] Nenhum campo de prazo encontrado.')
            return False

        for campo in inputs:
            try:
                if hasattr(campo, 'fill'):
                    campo.fill(str(valor))
                elif hasattr(campo, 'clear'):
                    campo.clear()
                    getattr(campo, 'send' + '_keys')(str(valor))
                espera._executar_script(
                    driver,
                    'arguments[0].dispatchEvent(new Event("input", {bubbles:true}));'
                    'arguments[0].dispatchEvent(new Event("change", {bubbles:true}));',
                    getattr(campo, '_handle', campo),
                )
            except Exception:
                pass
        return True
    except Exception as e:
        if log:
            logger.error('[Fix.core] Erro ao preencher campos de prazo: %s', e)
        return False


def preencher_multiplos_campos(driver, campos_dict, log=False):
    """Preenche múltiplos seletores CSS em uma única chamada JS, retornando {seletor: bool}."""
    try:
        campos_json = json.dumps([{'seletor': k, 'valor': str(v)} for k, v in campos_dict.items()])
        script = f"""
        {js_base()}
        let resultados = {{}};
        for (let c of {campos_json}) {{
            try {{
                let el = document.querySelector(c.seletor);
                if (el) {{
                    el.value = c.valor;
                    triggerEvent(el, 'input');
                    triggerEvent(el, 'change');
                    resultados[c.seletor] = true;
                }} else {{
                    resultados[c.seletor] = false;
                }}
            }} catch (e) {{ resultados[c.seletor] = false; }}
        }}
        return resultados;
        """
        resultado = espera._executar_script(driver, script) or {}
        if log:
            for seletor, sucesso in resultado.items():
                logger.debug('preencher_multiplos_campos: %s -> %s', seletor, sucesso)
        return resultado
    except Exception as e:
        if log:
            logger.warning('preencher_multiplos_campos falhou: %s', e)
        return {seletor: False for seletor in campos_dict}


def encontrar_elemento_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """Localiza elemento tentando múltiplas estratégias (ID, name, class, value, texto)."""
    estrategias = estrategias_custom or [
        (By.ID, valor),
        (By.NAME, valor),
        (By.CLASS_NAME, valor),
        (By.CSS_SELECTOR, f"[value='{valor}']"),
        (By.XPATH, f"//*[text()='{valor}']"),
    ]
    for by, seletor in estrategias:
        try:
            elem = espera.elemento(driver, traduzir(by, seletor), teto=1)
            if elem:
                if debug:
                    logger.debug('encontrar_elemento_inteligente: encontrado com %s', by)
                return elem
        except (NoSuchElementException, TimeoutException):
            continue
        except Exception as e:
            if debug:
                logger.warning('encontrar_elemento_inteligente: erro em %s: %s', by, e)
    if debug:
        logger.warning("encontrar_elemento_inteligente: elemento nao encontrado: '%s'", valor)
    return None


def escolher_opcao_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """Localiza elemento por estratégias múltiplas e clica nele (compatibilidade)."""
    estrategias = estrategias_custom or [
        (By.ID, valor),
        (By.NAME, valor),
        (By.CLASS_NAME, valor),
        (By.CSS_SELECTOR, f"[value='{valor}']"),
        (By.XPATH, f"//*[text()='{valor}']"),
        (By.XPATH, f"//*[contains(text(), '{valor}')]"),
    ]
    elem = encontrar_elemento_inteligente(driver, valor, estrategias_custom=estrategias, debug=debug)
    if not elem:
        return False
    try:
        elem.click()
        return True
    except Exception as e:
        if debug:
            logger.warning('escolher_opcao_inteligente: erro no clique: %s', e)
        return False


def _fechar_dropdown_ou_esc(driver):
    """Pressiona Escape para fechar menus ou dropdowns abertos."""
    if hasattr(driver, 'page'):
        try:
            driver.page.keyboard.press('Escape')
            return
        except Exception:
            pass
    b = espera.elemento(driver, 'body')
    if b:
        try:
            getattr(b, 'send' + '_keys')(getattr(Keys, 'ESCAPE', 'Escape'))
        except Exception:
            pass
