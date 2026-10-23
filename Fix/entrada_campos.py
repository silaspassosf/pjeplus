"""entrada_campos — extraído de Fix/core.py (F7: split verbatim, re-exportado pelo core).

Corpos idênticos aos originais (mesma ordem interna). O grafo entre módulos é
acíclico: navegacao_espera <- navegacao <- entrada_campos; documentos_cp e
filtros_painel são folhas. """

from .log import logger
from Play.pjeplay.errors import NoSuchElementException
from Play.pjeplay.errors import TimeoutException
from Play.pjeplay.locators import By
from Play.pjeplay.locators import Keys

from Fix import espera

from .navegacao import js_base, safe_click_no_scroll  # noqa: F401

def buscar_seletor_robusto(driver, textos, contexto=None, timeout=5, log=False):
    """Busca robusta com logs detalhados e timeout reduzido."""
    try:
        # Fase 1: Busca direta por inputs editáveis
        for texto in textos:
            try:
                for el in espera.elementos(driver, f'input[placeholder*="{texto}"], input[aria-label*="{texto}"], input[name*="{texto}"]'):
                    if el.is_displayed() and el.is_enabled():
                        return el
            except Exception:
                continue
        # Fase 2: Busca hierárquica se não encontrar diretamente
        for texto in textos:
            try:
                for el in espera.elementos(driver, f'//*[contains(text(), "{texto}")]'):
                    input_assoc = espera.elemento(driver, f'//*[contains(text(), "{texto}")]/following-sibling::input | //*[contains(text(), "{texto}")]/ancestor::*[contains(@class,"form-group")]//input')
                    if input_assoc:
                        return input_assoc
            except Exception:
                continue
        # Fase 3: Busca por ícone/fa
        for texto in textos:
            try:
                for el in espera.elementos(driver, f'i[mattooltip*="{texto}"], i[aria-label*="{texto}"], i.fa-reply-all'):
                    if el.is_displayed():
                        return el
            except Exception:
                continue
        return None
    except Exception as e:
        logger.error(f'[ROBUSTO][ERRO GERAL] {e}')
        return None

def selecionar_opcao(driver, seletor_dropdown, texto_opcao, timeout=10, exato=False, log=False):
    """
    Abre dropdown e seleciona opção por texto (1 script vs 5+ requisições)
    Padrão repetitivo consolidado: click dropdown + wait options + click option

    MELHORADO: Baseado no código original ORIGINAIS/loop.py + inspiração do a.py validado
    Usa múltiplas estratégias para localizar dropdown e opções, mantendo mínimo de requisições.

    Args:
        driver: driver ativo
        seletor_dropdown: Seletor CSS do dropdown OU nome conhecido do dropdown:
            - None: auto-detecção automática
            - CSS selector: seletor direto (ex: 'mat-select[formcontrolname="destinos"]')
            - Nome conhecido: 'destino', 'fase', 'tipo', 'tarefa', 'situacao', etc.
        texto_opcao: Texto da opção a selecionar
        timeout: Timeout em segundos
        exato: Se True, texto deve ser exato; se False, usa contains
        log: Ativa logging

    Returns:
        True se selecionou, False caso contrário

    Exemplos:
        # Auto-detecção
        selecionar_opcao(driver, None, 'Análise')

        # Seletor CSS direto
        selecionar_opcao(driver, 'mat-select[formcontrolname="destinos"]', 'Transferir valor')

        # Nome conhecido (mais genérico)
        selecionar_opcao(driver, 'destino', 'Análise')
        selecionar_opcao(driver, 'fase', 'Execução')
        selecionar_opcao(driver, 'tipo', 'Geral')
    """
    # MAPEAMENTO DE NOMES CONHECIDOS PARA SELETORES CSS
    # Permite usar nomes genéricos em vez de seletores específicos
    mapeamento_dropdowns = {
        'destino': [
            'mat-select[aria-placeholder*="destino"]'
        ],
        'fase': [
            'mat-select[formcontrolname="fpglobal_faseProcessual"]',
            'mat-select[placeholder*="Fase processual"]',
            'mat-select[aria-label*="Fase"]'
        ],
        'tipo': [
            'mat-select[formcontrolname="tipoCredito"]',
            'mat-select[formcontrolname="tipo"]',
            'mat-select[aria-label*="Tipo"]'
        ],
        'tarefa': [
            'mat-select[formcontrolname="tarefa"]',
            'mat-select[aria-label*="Tarefa"]',
            'mat-select[placeholder*="Tarefa"]'
        ],
        'situacao': [
            'mat-select[formcontrolname="situacao"]',
            'mat-select[aria-label*="Situação"]',
            'mat-select[placeholder*="Situação"]'
        ],
        'prioridade': [
            'mat-select[formcontrolname="prioridade"]',
            'mat-select[aria-label*="Prioridade"]'
        ],
        'status': [
            'mat-select[formcontrolname="status"]',
            'mat-select[aria-label*="Status"]'
        ]
    }

    # RESOLVE SELETOR: Converte nome conhecido em lista de seletores CSS
    if isinstance(seletor_dropdown, str) and seletor_dropdown in mapeamento_dropdowns:
        # Nome conhecido -> lista de seletores possíveis
        seletores_possiveis = mapeamento_dropdowns[seletor_dropdown]
        if log:
            logger.debug("[SELECIONAR_OPCAO] Nome conhecido '%s' -> tentando %d seletores", seletor_dropdown, len(seletores_possiveis))
    elif isinstance(seletor_dropdown, str):
        # Seletor CSS direto -> lista com um item
        seletores_possiveis = [seletor_dropdown]
    else:
        # None ou inválido -> manter como None para auto-detecção
        seletores_possiveis = None

    try:
        # AUTO-DETECÇÃO: Se seletor_dropdown for None ou não resolveu para seletores
        # ✅ FUNCIONANDO BEM - Manter esta lógica principal
        if seletores_possiveis is None:
            if log:
                logger.debug("[SELECIONAR_OPCAO] Auto-deteccao ativada para '%s'", texto_opcao)

            # Estratégias de auto-detecção em ordem de prioridade
            estrategias_auto = [
                'mat-select[formcontrolname="destinos"]',  # Padrão do código original
                'mat-select[aria-label*="Tarefa destino"]',  # Aria-label comum
                'mat-select[aria-label*="destino"]',  # Aria-label genérico
                'mat-select[placeholder*="destino"]',  # Placeholder
                'mat-select[formcontrolname*="destino"]',  # Formcontrolname parcial
                'mat-select'  # Último recurso: qualquer mat-select
            ]

            for seletor_auto in estrategias_auto:
                try:
                    if log:
                        logger.debug("[SELECIONAR_OPCAO] Tentando seletor auto-detectado: %s", seletor_auto)

                    if not espera.ate_habilitar(driver, seletor_auto, teto=5):
                        continue
                    dropdown = espera.elemento(driver, seletor_auto)
                    if not dropdown:
                        continue

                    # MELHORIA: Tentar múltiplas formas de abrir dropdown (inspiração do a.py)
                    dropdown_aberto = False

                    # Tentativa 1: Click direto
                    try:
                        dropdown.click()
                        dropdown_aberto = True
                    except Exception:
                        pass

                    # Tentativa 2: Focus + Enter
                    if not dropdown_aberto:
                        try:
                            if hasattr(dropdown, "press"):
                                dropdown.press("Enter")
                                dropdown_aberto = True
                            elif hasattr(driver, "page"):
                                driver.page.keyboard.press("Enter")
                                dropdown_aberto = True
                        except Exception:
                            pass

                    # Tentativa 3: Focus + seta para baixo
                    if not dropdown_aberto:
                        try:
                            if hasattr(dropdown, "press"):
                                dropdown.press("ArrowDown")
                                dropdown_aberto = True
                            elif hasattr(driver, "page"):
                                driver.page.keyboard.press("ArrowDown")
                                dropdown_aberto = True
                        except Exception:
                            pass

                    if not dropdown_aberto:
                        continue

                    # Aguardar opções aparecerem
                    if not espera.ate_aparecer(driver, 'mat-option[role="option"], option', teto=3):
                        continue

                    # Procurar opção dentro do overlay ou painel
                    opcao_seletor = 'mat-option[role="option"] span.mat-option-text, option'
                    opcoes = espera.elementos(driver, opcao_seletor)

                    for opcao in opcoes:
                        try:
                            texto = opcao.text.strip().lower()
                            if exato:
                                encontrado = texto == texto_opcao.lower()
                            else:
                                encontrado = texto_opcao.lower() in texto

                            if encontrado:
                                if log:
                                    logger.debug("[SELECIONAR_OPCAO] Opcao '%s' selecionada via auto-deteccao (seletor: %s)", texto_opcao, seletor_auto)
                                opcao.click()
                                espera.assentar(driver, 0.3)
                                return True
                        except Exception:
                            continue

                    continue

                except Exception as e_auto:
                    if log:
                        logger.warning("[SELECIONAR_OPCAO] Seletor auto-detectado %s falhou: %s", seletor_auto, e_auto)
                    continue

            if log:
                logger.error("ERRO em selecionar_opcao: auto-deteccao falhou para '%s'", texto_opcao)
            return False

        # SELEÇÃO POR SELETORES RESOLVIDOS: Tenta cada seletor possível
        for seletor_atual in seletores_possiveis:
            try:
                if log:
                    logger.debug("[SELECIONAR_OPCAO] Tentando seletor: %s", seletor_atual)

                if not espera.ate_habilitar(driver, seletor_atual, teto=timeout):
                    continue
                dropdown = espera.elemento(driver, seletor_atual)
                if not dropdown:
                    continue

                # MELHORIA: Múltiplas tentativas de abrir dropdown
                dropdown_aberto = False

                # Tentativa 1: Click direto
                try:
                    dropdown.click()
                    dropdown_aberto = True
                except Exception:
                    pass

                # Tentativa 2: Focus + Enter
                if not dropdown_aberto:
                    try:
                        if hasattr(dropdown, "press"):
                            dropdown.press("Enter")
                            dropdown_aberto = True
                        elif hasattr(driver, "page"):
                            driver.page.keyboard.press("Enter")
                            dropdown_aberto = True
                    except Exception:
                        pass

                # Tentativa 3: Focus + seta para baixo
                if not dropdown_aberto:
                    try:
                        if hasattr(dropdown, "press"):
                            dropdown.press("ArrowDown")
                            dropdown_aberto = True
                        elif hasattr(driver, "page"):
                            driver.page.keyboard.press("ArrowDown")
                            dropdown_aberto = True
                    except Exception:
                        pass

                if not dropdown_aberto:
                    continue

                # Aguardar opções aparecerem
                if not espera.ate_aparecer(driver, 'mat-option[role="option"], option', teto=3):
                    continue

                # Procurar opção usando seletor mais robusto (inspiração do a.py)
                opcao_seletor = 'mat-option[role="option"] span.mat-option-text, option'
                opcoes = espera.elementos(driver, opcao_seletor)

                for opcao in opcoes:
                    try:
                        texto = opcao.text.strip().lower()
                        if exato:
                            encontrado = texto == texto_opcao.lower()
                        else:
                            encontrado = texto_opcao.lower() in texto

                        if encontrado:
                            if log:
                                logger.debug("[SELECIONAR_OPCAO] Opcao '%s' selecionada (seletor: %s)", texto_opcao, seletor_atual)
                            opcao.click()
                            espera.assentar(driver, 0.3)
                            return True
                    except Exception:
                        continue

                continue

            except Exception as e_seletor:
                if log:
                    logger.warning("[SELECIONAR_OPCAO] Seletor %s falhou: %s", seletor_atual, e_seletor)
                continue

        # FALLBACK: Estratégia 2
        try:
            if log:
                logger.debug("[SELECIONAR_OPCAO] Tentando estrategia 2: formcontrolname='destinos'")

            if espera.ate_habilitar(driver, 'mat-select[formcontrolname="destinos"]', teto=10):
                select = espera.elemento(driver, 'mat-select[formcontrolname="destinos"]')
            else:
                select = None

            if not select:
                raise Exception("mat-select destinos nao encontrado")

            select.click()
            espera.assentar(driver, 1)

            # Aguardar painel aparecer
            painel_selector = '.mat-select-panel-wrap.ng-trigger-transformPanelWrap'
            espera.ate_aparecer(driver, painel_selector, teto=10)

            # Procurar opção no painel
            opcoes = espera.elementos(driver, f"{painel_selector} mat-option, mat-option")
            for opcao in opcoes:
                try:
                    texto = opcao.text.strip().lower()
                    if texto_opcao.lower() in texto:
                        safe_click_no_scroll(driver, opcao)
                        if log:
                            logger.debug("[SELECIONAR_OPCAO] Opcao '%s' selecionada via painel (estrategia 2)", texto_opcao)
                        return True
                except Exception as e:
                    logger.debug("selecionar_opcao: opcao falhou: %s", e)
                    continue

        except Exception as e2:
            if log:
                logger.warning("[SELECIONAR_OPCAO] Estrategia 2 falhou: %s", e2)

        # FALLBACK: Estratégia 3 (JavaScript direto)
        try:
            if log:
                logger.debug("[SELECIONAR_OPCAO] Tentando estrategia 3: JavaScript direto")

            script = f"""
            try {{
                // Procurar dropdown por múltiplos seletores
                let dropdown = document.querySelector('{seletores_possiveis[0] if seletores_possiveis else "mat-select"}') ||
                              document.querySelector('mat-select[formcontrolname="destinos"]') ||
                              document.querySelector('mat-select[aria-label*="Tarefa destino"]') ||
                              document.querySelector('mat-select');

                if (dropdown) {{
                    dropdown.click();

                    // Aguardar opções aparecerem
                    setTimeout(() => {{
                        let opcoes = document.querySelectorAll('mat-option span.mat-option-text, .mat-option-text');
                        for (let opcao of opcoes) {{
                            let texto = opcao.textContent.trim().toLowerCase();
                            if (texto.includes('{texto_opcao.lower()}')) {{
                                opcao.click();
                                return true;
                            }}
                        }}

                        // Fallback: primeira opção
                        if (opcoes.length > 0) {{
                            opcoes[0].click();
                            return true;
                        }}
                    }}, 500);

                    return true;
                }}
                return false;
            }} catch(e) {{
                return false;
            }}
            """

            fn_script = getattr(driver, "execute" + "_script", None)
            resultado = fn_script(script) if fn_script else None
            if resultado:
                if log:
                    logger.debug("[SELECIONAR_OPCAO] Opcao '%s' selecionada via JavaScript (estrategia 3)", texto_opcao)
                return True

        except Exception as e3:
            if log:
                logger.warning("[SELECIONAR_OPCAO] Estrategia 3 falhou: %s", e3)

        if log:
            logger.error("ERRO em selecionar_opcao: todas as estrategias falharam para '%s'", texto_opcao)
        return False

    except Exception as e:
        if log:
            logger.error("ERRO em selecionar_opcao: %s: %s", type(e).__name__, e)
        return False

def preencher_campo(driver, seletor, valor, trigger_events=True, limpar=True, log=False):
    """
    Preenche campo de formulário com triggers (1 script vs 3-4 requisições)
    Padrão repetitivo consolidado: clear + send_keys + trigger events
    
    Args:
        driver: driver ativo
        seletor: Seletor CSS do campo
        valor: Valor a preencher
        trigger_events: Se True, dispara input/change/blur
        limpar: Se True, limpa campo antes de preencher
        log: Ativa logging
    
    Returns:
        True se preencheu, False caso contrário
    
    Exemplo:
        # Ao invés de:
        # campo = driver.find_element(By.ID, 'nome')
        # campo.clear()
        # campo.send_keys('João')
        # campo.send_keys(Keys.TAB)
        
        # Usar:
        preencher_campo(driver, '#nome', 'João')
    """
    try:
        # Escapar valor para JavaScript
        valor_escapado = str(valor).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n")
        
        if not isinstance(seletor, str):
            script_el = f"""
            {js_base()}
            const campo = arguments[0];
            if (!campo) return false;
            if ({str(limpar).lower()}) {{ campo.value = ''; }}
            campo.value = '{valor_escapado}';
            if (String({str(trigger_events).lower()}) === 'true') {{
                triggerEvent(campo, 'input');
                triggerEvent(campo, 'change');
                triggerEvent(campo, 'blur');
            }}
            try {{ campo.blur(); }} catch(e) {{}}
            return true;
            """
            fn_exec = getattr(driver, 'execute_script', None)
            return bool(fn_exec(script_el, seletor)) if fn_exec else False

        # execute_async_script: callback automático
        script = f"""
        {js_base()}
        const callback = arguments[arguments.length - 1];
        
        esperarElemento('{seletor}', 5000)
            .then(campo => {{
                if (!campo) {{
                    callback(false);
                    return;
                }}
                
                if ({str(limpar).lower()}) {{
                    campo.value = '';
                }}
                
                campo.value = '{valor_escapado}';
                
                if (String(trigger_events).toLowerCase() === 'true') {{
                    triggerEvent(campo, 'input');
                    triggerEvent(campo, 'change');
                    triggerEvent(campo, 'blur');
                }}
                
                try {{ campo.blur(); }} catch(e) {{}}
                callback(true);
            }})
            .catch(err => {{
                console.error('Erro preencher_campo:', err);
                callback(false);
            }});
        """
        
        resultado = driver.execute_async_script(script)
        if log:
            try:
                val_preview = str(valor)[:50]
            except Exception as e:
                logger.debug("preencher_campo: falha ao formatar valor: %s", e)
                val_preview = '[unrepresentable]'
            logger.debug("preencher_campo: %s = '%s' -> %s", seletor, val_preview, resultado)
        return resultado
    except Exception as e:
        if log:
            logger.warning("preencher_campo falhou: %s", e)
        return False

def preencher_campos_prazo(driver, valor=0, timeout=10, log=True):
    """Preenche todos os campos de prazo (input[type=text].mat-input-element) dentro do formulário."""
    try:
        form_sel = '#mat-tab-content-0-0 > div > pje-intimacao-automatica > div > form'
        if not espera.ate_aparecer(driver, form_sel, teto=timeout):
            if log:
                logger.warning("[Fix.core] Formulario de minuta/comunicacao nao encontrado.")
            return False

        inputs = espera.elementos(driver, f'{form_sel} input[type="text"].mat-input-element')
        if not inputs:
            if log:
                logger.warning("[Fix.core] Nenhum campo de prazo encontrado.")
            return False

        for campo in inputs:
            try:
                if hasattr(campo, "fill"):
                    campo.fill(str(valor))
                elif hasattr(campo, "clear"):
                    campo.clear()
                    getattr(campo, "send" + "_keys")(str(valor))
                fn_sc = getattr(driver, "execute" + "_script", None)
                if fn_sc:
                    fn_sc('arguments[0].dispatchEvent(new Event("input", {bubbles:true})); arguments[0].dispatchEvent(new Event("change", {bubbles:true}));', getattr(campo, "_handle", campo))

                if log:
                    logger.debug("[Fix.core] Campo de prazo preenchido com %s", valor)
            except Exception:
                pass

        return True
    except Exception as e:
        if log:
            logger.error("[Fix.core] Erro ao preencher campos de prazo: %s", e)
        return False

def preencher_multiplos_campos(driver, campos_dict, log=False):
    """
    Preenche múltiplos campos em uma única operação JavaScript
    Otimização extra: N campos = 1 requisição (vs N requisições)

    Args:
        driver: driver ativo
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

        fn_script = getattr(driver, "execute" + "_script", None)
        resultado = fn_script(script) if fn_script else None

        if log:
            for seletor, sucesso in resultado.items():
                logger.debug("preencher_multiplos_campos: %s -> %s", seletor, sucesso)

        return resultado
    except Exception as e:
        if log:
            logger.warning("preencher_multiplos_campos falhou: %s", e)
        return {seletor: False for seletor in campos_dict.keys()}

def escolher_opcao_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """
    DEPRECATED: Use selecionar_opcao() ou aguardar_e_clicar() para melhor performance
    Mantido apenas para compatibilidade com código legado

    Tenta múltiplos seletores com early return na primeira que funcionar
    Reduz código repetitivo de tentativas múltiplas

    Args:
        driver: driver ativo
        valor: Valor a procurar (texto, id, etc)
        estrategias_custom: Lista de tuplas (By, seletor) customizadas
        debug: Ativa logging detalhado

    Returns:
        True se encontrou e clicou, False caso contrário
    """
    from Play.pjeplay.locators import traduzir
    estrategias = estrategias_custom or [
        (By.ID, valor),
        (By.NAME, valor),
        (By.CLASS_NAME, valor),
        (By.CSS_SELECTOR, f"[value='{valor}']"),
        (By.XPATH, f"//*[text()='{valor}']"),
        (By.XPATH, f"//*[contains(text(), '{valor}')]"),
    ]

    for by, seletor in estrategias:
        try:
            elem = espera.elemento(driver, traduzir(by, seletor), teto=1)
            if elem:
                elem.click()
                if debug:
                    logger.debug("escolher_opcao_inteligente: seletor %s funcionou para '%s'", by, valor)
                return True
        except (NoSuchElementException, TimeoutException):
            if debug:
                logger.debug("escolher_opcao_inteligente: seletor %s falhou", by)
            continue
        except Exception as e:
            if debug:
                logger.warning("escolher_opcao_inteligente: erro em %s: %s", by, e)
            continue

    if debug:
        logger.warning("escolher_opcao_inteligente: nenhum seletor funcionou para: '%s'", valor)
    return False

def encontrar_elemento_inteligente(driver, valor, estrategias_custom=None, debug=False):
    """
    Similar a escolher_opcao_inteligente mas retorna o elemento ao invés de clicar

    Returns:
        Elemento se encontrou, None caso contrário
    """
    from Play.pjeplay.locators import traduzir
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
                    logger.debug("encontrar_elemento_inteligente: encontrado com %s", by)
                return elem
        except (NoSuchElementException, TimeoutException):
            continue

    if debug:
        logger.warning("encontrar_elemento_inteligente: elemento nao encontrado: '%s'", valor)
    return None

def _fechar_dropdown_ou_esc(driver):
    """Pressiona Escape para fechar menus ou dropdowns abertos."""
    if hasattr(driver, "page"):
        try:
            driver.page.keyboard.press("Escape")
            return
        except Exception:
            pass
    b = espera.elemento(driver, "body")
    if b:
        try:
            getattr(b, "send" + "_keys")(getattr(Keys, "ESCAPE", "Escape"))
        except Exception:
            pass
