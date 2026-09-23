import logging
logger = logging.getLogger(__name__)

from typing import Optional, Any
from Fix.utils import remover_acentos

from .core import *
from Fix.core import (
    aguardar_renderizacao_nativa,
    safe_click,
    safe_click_no_scroll,
    esperar_elemento,
    buscar_seletor_robusto,
)
import Fix.espera as espera


def _obter_abas(driver) -> list:
    """Retorna lista de handles/páginas de forma unificada."""
    context = getattr(driver, 'context', None)
    if context and hasattr(context, 'pages'):
        return list(context.pages)
    handles = getattr(driver, '_handles', None)
    if handles:
        return list(handles.keys())
    return list(getattr(driver, 'window_handles', []))


def _trocar_para_aba(driver, aba) -> None:
    """Troca o foco para a aba especificada (Page do Playwright ou handle)."""
    if hasattr(aba, 'bring_to_front'):
        aba.bring_to_front()
        if hasattr(driver, '_page'):
            driver._page = aba
    elif isinstance(aba, str):
        driver.switch_to.window(aba)


def _trocar_para_aba_detalhe(driver, debug: bool = False) -> bool:
    """Busca e troca para a aba que contém /detalhe na URL."""
    url_atual = getattr(driver, 'current_url', '') or ''
    if '/detalhe' in url_atual:
        return True

    context = getattr(driver, 'context', None)
    if context and hasattr(context, 'pages'):
        for p in context.pages:
            if '/detalhe' in (p.url or ''):
                p.bring_to_front()
                if hasattr(driver, '_page'):
                    driver._page = p
                if debug:
                    logger.debug(f"[MOV] Aba /detalhe encontrada: {p.url}")
                return True

    for h in _obter_abas(driver):
        try:
            _trocar_para_aba(driver, h)
            if '/detalhe' in (getattr(driver, 'current_url', '') or ''):
                if debug:
                    logger.debug(f"[MOV] Aba /detalhe encontrada: {driver.current_url}")
                return True
        except Exception:
            continue

    return False


def _localizar_botao_tarefa(driver: Any, timeout: int = 8):
    """Tentativa robusta de localizar o botão 'Abrir tarefa do processo'.
    Retorna WebElement ou None.
    """
    try:
        # 1) seletor canônico
        btn = esperar_elemento(driver, BTN_TAREFA_PROCESSO, timeout=timeout)
        if btn:
            return btn
    except Exception:
        pass

    try:
        # 2) busca robusta por textos/atributos (maisPje style)
        textos = ['Abre a tarefa do processo', 'Abrir tarefa', 'tarefa do processo', 'tarefa']
        el = buscar_seletor_robusto(driver, textos, timeout=timeout)
        if el:
            return el
    except Exception:
        pass

    try:
        # 3) tentativas por seletores alternativos
        alt = ["button[mattooltip*='tarefa']", "button[aria-label*='tarefa']", "button[title*='tarefa']"]
        for s in alt:
            try:
                el = espera.elemento(driver, s, teto=1)
                if el and getattr(el, 'is_displayed', lambda: True)():
                    return el
            except Exception:
                continue
    except Exception:
        pass

    return None


def _obter_tarefa_atual_robusta(driver: Any, timeout: int = 6, debug: bool = False) -> Optional[str]:
    """Obtém a tarefa atual sem depender do cabeçalho da tarefa estar renderizado."""
    seletores_tarefa = [
        'pje-cabecalho-tarefa h1.titulo-tarefa, pje-cabecalho-tarefa h1, pje-cabecalho-tarefa',
        'span.texto-tarefa-processo',
        'mat-card-title',
        'h1',
    ]

    for seletor in seletores_tarefa:
        try:
            for el in espera.elementos(driver, seletor, teto=1):
                texto = (getattr(el, 'text', '') or '').strip()
                if texto:
                    return texto
        except Exception:
            continue

    url_atual = getattr(driver, 'current_url', '') or ''
    if '/tarefa/' in url_atual:
        try:
            titulo = (getattr(driver, 'title', '') or '').strip()
            if titulo:
                return titulo
        except Exception:
            pass
        return 'Tarefa'

    if '/detalhe' in url_atual:
        try:
            tarefa_btn = _localizar_botao_tarefa(driver, timeout=max(2, timeout // 2))
            if tarefa_btn:
                tarefa_texto = ''
                try:
                    span_tarefa = espera.elemento(driver, '.texto-tarefa-processo', teto=1)
                    if span_tarefa and (getattr(span_tarefa, 'text', '') or '').strip():
                        tarefa_texto = span_tarefa.text.strip()
                except Exception:
                    pass

                if not tarefa_texto:
                    tarefa_texto = (getattr(tarefa_btn, 'text', '') or '').strip()

                if tarefa_texto:
                    if debug:
                        logger.info(f'[MOV_INT] Tarefa identificada pelo botão: {tarefa_texto}')

                    try:
                        handle_orig = getattr(driver, 'current_window_handle', None)
                        if safe_click_no_scroll(driver, tarefa_btn, log=debug):
                            try:
                                from Fix.browser_suporte import aguardar_nova_aba
                                if handle_orig:
                                    nova_aba = aguardar_nova_aba(driver, handle_orig, timeout=4)
                                    if nova_aba:
                                        driver.switch_to.window(nova_aba)
                            except Exception:
                                pass

                            for seletor_fallback in ['pje-cabecalho-tarefa h1.titulo-tarefa', 'span.texto-tarefa-processo', 'mat-card-title', 'h1']:
                                try:
                                    for el in espera.elementos(driver, seletor_fallback, teto=1):
                                        texto = (getattr(el, 'text', '') or '').strip()
                                        if texto:
                                            return texto
                                except Exception:
                                    continue
                    except Exception:
                        pass

                    return tarefa_texto
        except Exception:
            pass

    return None


def mov_simples(
    driver: Any,
    seletor_alvo: str,
    texto_confirmacao: Optional[str] = None,
    debug: bool = False,
    timeout: int = 15
) -> bool:
    """
    Versão SIMPLIFICADA do movimento - apenas uma tentativa:
    1. Busca aba /detalhe
    2. Clica uma vez no botão "Abrir tarefa do processo" 
    3. Troca para nova aba
    4. Procura o botão alvo diretamente (sem clicar em "Análise" novamente)
    5. Clica no botão alvo
    6. (Opcional) Confirma ação
    """
    def log_debug(msg):
        if debug:
            try:
                logger.debug(msg)
            except Exception:
                pass

    try:
        # ===== ETAPA 1: GARANTIR QUE ESTÁ EM /DETALHE =====
        log_debug("Buscando aba /detalhe...")
        if not _trocar_para_aba_detalhe(driver, debug=debug):
            logger.error('[MOV_SIMPLES][ERRO] Aba /detalhe não encontrada!')
            return False

        # ===== ETAPA 2: ABRIR TAREFA DO PROCESSO =====
        log_debug("Procurando botão 'Abrir tarefa do processo'...")
        btn_abrir_tarefa = _localizar_botao_tarefa(driver, timeout=max(2, timeout//2))
        if not btn_abrir_tarefa:
            logger.error(f'[MOV_SIMPLES][ERRO] Botão "Abrir tarefa do processo" não encontrado!')
            return False

        # Captura o texto da tarefa
        tarefa_do_botao = None
        try:
            span_tarefa = espera.elemento(driver, '.texto-tarefa-processo', teto=1)
            if span_tarefa and (getattr(span_tarefa, 'text', '') or '').strip():
                tarefa_do_botao = span_tarefa.text.strip()
                log_debug(f"Tarefa identificada: '{tarefa_do_botao}'")
        except Exception:
            pass

        if not tarefa_do_botao:
            try:
                tarefa_do_botao = (getattr(btn_abrir_tarefa, 'text', '') or '').strip()
                log_debug(f"Tarefa identificada (texto completo): '{tarefa_do_botao}'")
            except Exception:
                log_debug("Não foi possível capturar nome da tarefa")

        # Clica na tarefa (usar estratégia sem scroll/dispatchEvent)
        handle_orig = getattr(driver, 'current_window_handle', None)
        click_resultado = safe_click_no_scroll(driver, btn_abrir_tarefa, log=debug)

        if not click_resultado:
            logger.error(f'[MOV_SIMPLES][ERRO] Falha no clique do botão da tarefa')
            return False

        nova_aba = None
        try:
            from Fix.browser_suporte import aguardar_nova_aba
            if handle_orig:
                nova_aba = aguardar_nova_aba(driver, handle_orig, timeout=6)
        except Exception:
            pass

        if nova_aba:
            driver.switch_to.window(nova_aba)
            log_debug("Foco trocado para nova aba da tarefa")
        else:
            log_debug("Nenhuma nova aba detectada, prosseguindo na aba atual")

        # ===== ETAPA 4: PROCURAR E CLICAR NO BOTÃO ALVO =====
        log_debug(f"Procurando botão alvo: {seletor_alvo}")
        btn_alvo = espera.elemento(driver, seletor_alvo, teto=timeout//2)
        if btn_alvo:
            safe_click(driver, btn_alvo)
        else:
            logger.error(f'[MOV_SIMPLES][ERRO] Botão alvo não encontrado: {seletor_alvo}')
            return False

        # ===== ETAPA 5: CONFIRMAÇÃO (OPCIONAL) =====
        if texto_confirmacao:
            try:
                xpath_confirma = f"//button[contains(., '{texto_confirmacao}') or .//span[contains(., '{texto_confirmacao}')]]"
                btn_confirma = espera.elemento(driver, xpath_confirma, teto=timeout//2)
                if btn_confirma:
                    safe_click(driver, btn_confirma)
                else:
                    logger.error(f'[MOV_SIMPLES][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}"')
                    return False
            except Exception as e:
                logger.error(f'[MOV_SIMPLES][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}": {e}')
                return False

        return True

    except Exception as e:
        logger.error(f'[MOV_SIMPLES][ERRO] Falha geral no movimento simples: {e}')
        return False


def mov(
    driver: Any,
    seletor_alvo: str,
    texto_confirmacao: Optional[str] = None,
    debug: bool = False,
    timeout: int = 15
) -> bool:
    """
    Fluxo geral MELHORADO para movimentos:
    1. Verifica se está em /detalhe, se não estiver busca a aba /detalhe
    2. Clica no botão "Abrir tarefa do processo" (BTN_TAREFA_PROCESSO)
    3. Troca para nova aba, se aberta
    4. Procura o botão alvo (seletor_alvo)
       - Se não encontrar, SEMPRE clica em "Análise" e tenta novamente
       - Se ainda não der certo, recomeça do passo 1 (volta para /detalhe)
    5. Clica no botão alvo
    6. (Opcional) Confirma ação se texto_confirmacao for fornecido
    """
    logger.info(f'[MOV] Iniciando movimento geral - Seletor: {seletor_alvo}')

    def log_debug(msg):
        if debug:
            try:
                logger.debug(msg)
            except Exception:
                pass

    def tentar_encontrar_alvo():
        """Tenta encontrar o botão alvo, com fallback para Análise"""
        try:
            # Primeira tentativa: buscar o alvo diretamente
            btn_alvo = espera.elemento(driver, seletor_alvo, teto=timeout//3)
            if btn_alvo:
                safe_click(driver, btn_alvo)
                return True
        except Exception:
            pass

        # Verificar se já está em "Análise" - se sim, e botão não encontrado, está correto
        if seletor_alvo == "button[aria-label='Aguardando prazo']":
            try:
                # Verificar se estamos em uma tarefa de análise
                elementos_analise = espera.elementos(driver, "//*[contains(translate(text(), 'ANÁLISE', 'análise'), 'análise')]", teto=1)
                em_analise = any('análise' in (getattr(el, 'text', '') or '').lower() for el in elementos_analise if getattr(el, 'is_displayed', lambda: True)())
                if em_analise:
                    log_debug("Já está em 'Análise' e botão 'Aguardando prazo' não disponível - está correto")
                    return True
            except Exception:
                pass

        # SEMPRE tenta clicar em "Análise" se não encontrar o alvo
        log_debug("Botão alvo não encontrado. Tentando clicar em 'Análise'...")
        btn_analise = None
        
        # Busca por texto "Análise"
        btns_analise = espera.elementos(driver, "//button[contains(translate(normalize-space(text()), 'ANÁLISE', 'análise'), 'análise')]", teto=2)
        for btn in btns_analise:
            if getattr(btn, 'is_displayed', lambda: True)() and getattr(btn, 'is_enabled', lambda: True)():
                btn_analise = btn
                break
        
        # Fallback: busca por aria-label
        if not btn_analise:
            btns_analise = espera.elementos(driver, "button[aria-label*='Análise']", teto=2)
            for btn in btns_analise:
                if getattr(btn, 'is_displayed', lambda: True)() and getattr(btn, 'is_enabled', lambda: True)():
                    btn_analise = btn
                    break
        
        if btn_analise:
            safe_click(driver, btn_analise)
            try:
                aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao', modo='aparecer', timeout=8)
            except Exception:
                pass
            
            # Segunda tentativa: buscar o alvo após Análise
            try:
                btn_alvo = espera.elemento(driver, seletor_alvo, teto=timeout//3)
                if btn_alvo:
                    safe_click(driver, btn_alvo)
                    return True
            except Exception:
                pass
            log_debug("Botão alvo não encontrado mesmo após 'Análise'")
            return False
        else:
            log_debug("Botão 'Análise' não encontrado")
            return False
    
    # Máximo de 2 tentativas completas
    for tentativa in range(1, 3):
        try:
            # ===== ETAPA 1: GARANTIR QUE ESTÁ EM /DETALHE =====
            if not _trocar_para_aba_detalhe(driver, debug=debug):
                logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Não foi possível encontrar aba /detalhe')
                if tentativa == 2:  # Última tentativa
                    return False
                continue
            
            # ===== ETAPA 2: ABRIR TAREFA DO PROCESSO =====
            log_debug("Procurando botão 'Abrir tarefa do processo'...")
            btn_abrir_tarefa = _localizar_botao_tarefa(driver, timeout=max(2, timeout//2))
            if not btn_abrir_tarefa:
                logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Botão "Abrir tarefa do processo" não encontrado!')
                if tentativa == 2:
                    return False
                continue
            
            # Captura o texto da tarefa antes do clique
            tarefa_do_botao = None
            try:
                span_tarefa = espera.elemento(driver, '.texto-tarefa-processo', teto=1)
                if span_tarefa and (getattr(span_tarefa, 'text', '') or '').strip():
                    tarefa_do_botao = span_tarefa.text.strip()
                    log_debug(f"Tarefa identificada: '{tarefa_do_botao}'")
            except Exception:
                pass

            if not tarefa_do_botao:
                try:
                    tarefa_do_botao = (getattr(btn_abrir_tarefa, 'text', '') or '').strip()
                    log_debug(f"Tarefa identificada (texto completo): '{tarefa_do_botao}'")
                except Exception:
                    log_debug("Não foi possível capturar nome da tarefa")
            
            # Clica na tarefa (usar dispatchEvent/sem scroll)
            handle_orig = getattr(driver, 'current_window_handle', None)
            click_resultado = safe_click_no_scroll(driver, btn_abrir_tarefa, log=debug)
            
            if not click_resultado:
                logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Falha no clique do botão da tarefa')
                if tentativa == 2:
                    return False
                continue

            nova_aba = None
            try:
                from Fix.browser_suporte import aguardar_nova_aba
                if handle_orig:
                    nova_aba = aguardar_nova_aba(driver, handle_orig, timeout=6)
            except Exception:
                pass
            
            if nova_aba:
                driver.switch_to.window(nova_aba)
                log_debug("Foco trocado para nova aba da tarefa")
            else:
                log_debug("Nenhuma nova aba detectada, prosseguindo na aba atual")
            
            # ===== ETAPA 4: ENCONTRAR E CLICAR NO ALVO =====
            if tentar_encontrar_alvo():
                # ===== ETAPA 5: CONFIRMAÇÃO (OPCIONAL) =====
                if texto_confirmacao:
                    try:
                        xpath_confirma = f"//button[contains(., '{texto_confirmacao}') or .//span[contains(., '{texto_confirmacao}')]]"
                        btn_confirma = espera.elemento(driver, xpath_confirma, teto=timeout//2)
                        if btn_confirma:
                            safe_click(driver, btn_confirma)
                        else:
                            logger.error(f'[MOV][ERRO] Botão de confirmação "{texto_confirmacao}" não encontrado')
                            return False
                    except Exception as e:
                        logger.error(f'[MOV][ERRO] Não foi possível clicar no botão de confirmação "{texto_confirmacao}": {e}')
                        return False
                
                return True
            else:
                logger.warning(f'[MOV][WARN] Tentativa {tentativa}: Não foi possível encontrar o alvo, tentando novamente...')
                if tentativa == 2:
                    logger.error('[MOV][ERRO] Esgotadas todas as tentativas')
                    return False
                # Fechar aba da tarefa antes de tentar novamente
                try:
                    abas = _obter_abas(driver)
                    if nova_aba and nova_aba in abas:
                        try:
                            driver.close()
                        except Exception:
                            pass
                        abas_restantes = _obter_abas(driver)
                        if abas_restantes:
                            _trocar_para_aba(driver, abas_restantes[0])
                except Exception:
                    pass
                continue
                
        except Exception as e:
            logger.error(f'[MOV][ERRO] Tentativa {tentativa}: Falha no fluxo de movimento: {e}')
            if tentativa == 2:
                return False
            continue
    
    return False


def _remover_acentos(texto: str) -> str:
    if not texto:
        return ''
    return remover_acentos(texto)


def _localizar_botao_destino_movimento(driver: Any, destino: str, timeout: int = 8):
    """Localiza o botão de destino alinhado ao gigs-plugin/mini-selenium:
    1. Aguarda pje-botoes-transicao ter pelo menos 5 botões (esperarColecao)
    2. Busca por textContent normalizado (removeAcento + includes) — tal como querySelectorByText
    3. Fallback para busca global de botões na página
    4. Fallback para aria-label / title
    """
    destino_lower = (destino or '').strip().lower()
    if not destino_lower:
        return None

    destino_normalizado = _remover_acentos(destino_lower)

    def _texto_normalizado(texto: str) -> str:
        # espelha removeAcento + removeQuebraDeLinha do mini-selenium.js
        import re as _re
        texto = _remover_acentos((texto or '').strip().lower())
        return _re.sub(r'[\r\n]+', ' ', texto)

    def _match(el) -> bool:
        try:
            texto = _texto_normalizado((getattr(el, 'text_content', None) and el.text_content()) or getattr(el, 'text', '') or '')
            return destino_normalizado in texto and getattr(el, 'is_displayed', lambda: True)() and not el.get_attribute('disabled')
        except Exception:
            return False

    # 1. Aguardar pje-botoes-transicao renderizar via MutationObserver (padrão esperarElemento do mini-selenium.js)
    aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao button', modo='aparecer', timeout=timeout)

    # 2. Dentro de pje-botoes-transicao (alvo primário)
    try:
        for el in espera.elementos(driver, 'pje-botoes-transicao button', teto=2):
            if _match(el):
                return el
    except Exception:
        pass

    # 3. Qualquer botão visível na página (fallback global)
    try:
        for el in espera.elementos(driver, 'button', teto=2):
            if _match(el):
                return el
    except Exception:
        pass

    # 4. aria-label / title
    try:
        for el in espera.elementos(driver, 'button[aria-label], button[title]', teto=2):
            attr = (el.get_attribute('aria-label') or el.get_attribute('title') or '')
            if destino_normalizado in _texto_normalizado(attr) and getattr(el, 'is_displayed', lambda: True)() and not el.get_attribute('disabled'):
                return el
    except Exception:
        pass

    return None


def abrir_tarefa_por_api(driver: Any, timeout: int = 10) -> bool:
    """Abre a tarefa mais recente do processo via API REST (padrão gigs-plugin).
    
    Estratégia:
    1. GET /pje-comum-api/api/processos/id/{idProcesso}/tarefas?maisRecente=true
    2. Extrai idTarefa de payload[0].idTarefa
    3. Navega direto (driver.get) para /pjekz/processo/{idProcesso}/tarefa/{idTarefa}
    
    Este fluxo não depende do cabeçalho da tarefa estar renderizado para prosseguir.
    """
    import re as _re
    from Fix.variaveis import session_from_driver

    try:
        url_atual = driver.current_url or ''
        if '/tarefa' in url_atual:
            return True
        if '/processo/' not in url_atual:
            return False

        m = _re.search(r'/processo/(\d+)', url_atual)
        if not m:
            return False
        id_processo = m.group(1)
        base = url_atual.split('/pjekz/')[0]

        # Etapa 1: Obter session autenticada via cookies do driver (padrão apis.js)
        try:
            sess, host = session_from_driver(driver)
        except Exception as e:
            logger.warning(f'[API_TAREFA] session_from_driver falhou: {e}')
            return False

        # Etapa 2: GET /tarefas?maisRecente=true (padrão gigs-plugin L4511-4512)
        endpoint = f"https://{host}/pje-comum-api/api/processos/id/{id_processo}/tarefas?maisRecente=true"
        try:
            r = sess.get(endpoint, timeout=10)
            r.raise_for_status()
            dados = r.json()
        except Exception as e:
            logger.warning(f'[API_TAREFA] GET {endpoint} falhou: {e}')
            return False

        # Etapa 3: Extrair idTarefa (resposta é array [0].idTarefa conforme gigs-plugin)
        id_tarefa = None
        if isinstance(dados, list) and dados:
            id_tarefa = dados[0].get('idTarefa') or dados[0].get('id')
        elif isinstance(dados, dict):
            # Fallback: resposta envelopada {idTarefa: ...}
            id_tarefa = dados.get('idTarefa') or dados.get('id')

        if not id_tarefa:
            logger.warning(f'[API_TAREFA] idTarefa não encontrado na resposta: {dados}')
            return False

        # Etapa 4: Navegar direto para a tarefa (padrão gigs-plugin apis.abrirTarefa.abrir(..., 'self'))
        url_tarefa = f"{base}/pjekz/processo/{id_processo}/tarefa/{id_tarefa}"
        try:
            driver.get(url_tarefa)
        except Exception as e:
            logger.error(f'[API_TAREFA] Erro ao navegar para tarefa: {e}')
            return False

        # Etapa 5: Aguardar renderização
        try:
            aguardar_renderizacao_nativa(driver, 'body', modo='aparecer', timeout=min(6, timeout))
        except Exception:
            pass  # Fallback: continuar mesmo se renderização falhar

        logger.info(f'[API_TAREFA] Tarefa aberta via API com sucesso: processo={id_processo} tarefa={id_tarefa}')
        return True

    except Exception as e:
        logger.error(f'[API_TAREFA] Falha ao abrir tarefa via API: {e}', exc_info=True)
        return False


def _tarefa_atual_via_api(driver: Any) -> Optional[str]:
    """Nome da tarefa mais recente do processo via API, SEM navegar o browser.

    Consulta o mesmo endpoint de abrir_tarefa_por_api
    (/tarefas?maisRecente=true) e extrai o nome da tarefa do payload.
    Usado para evitar abrir a tarefa no browser quando ela já está no
    estado de destino (fluxo p2b: 'Aguardando Prazo' — abria e fechava
    em sequência, sem ação visível).
    Retorna None se não conseguir determinar (chamador segue o fluxo normal).
    """
    import re as _re
    from Fix.variaveis import session_from_driver

    try:
        url_atual = driver.current_url or ''
        if '/tarefa' in url_atual or '/processo/' not in url_atual:
            return None
        m = _re.search(r'/processo/(\d+)', url_atual)
        if not m:
            return None
        id_processo = m.group(1)

        sess, host = session_from_driver(driver)
        endpoint = f"https://{host}/pje-comum-api/api/processos/id/{id_processo}/tarefas?maisRecente=true"
        r = sess.get(endpoint, timeout=10)
        r.raise_for_status()
        dados = r.json()

        registro = None
        if isinstance(dados, list) and dados:
            registro = dados[0]
        elif isinstance(dados, dict):
            registro = dados
        if not isinstance(registro, dict):
            return None

        for campo in ('nomeTarefa', 'nome', 'tarefa', 'descricao', 'titulo'):
            valor = registro.get(campo)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
        return None
    except Exception:
        return None


def movimentar_inteligente(driver: Any, destino: str, ultimo_lance: str = '', chip: Optional[str] = None, responsavel: Optional[str] = None, timeout: int = 15, profundidade: int = 0, pular_abertura_api: bool = False) -> bool:

    def log(msg):
        try:
            logger.info(msg)
        except Exception:
            pass

    if profundidade >= 3:
        logger.error(f'[MOV_INT] Limite de {profundidade} navegacoes atingido sem conseguir "{destino}" — abortando (tarefa possivelmente sem o botao de destino)')
        return False

    try:
        # ===== ETAPA -1: JÁ ESTÁ NO DESTINO? (verificação via API, sem abrir a tarefa) =====
        # Antes de navegar, consulta via API se a tarefa já está no estado de
        # destino — evita o padrão "abre a tarefa e fecha em seguida" sem ação
        # visível (comum no p2b, onde a tarefa já está em 'Aguardando Prazo').
        if '?' not in (destino or ''):
            tarefa_api = _tarefa_atual_via_api(driver)
            if tarefa_api:
                destino_pre = _remover_acentos((destino or '').lower())
                if destino_pre and destino_pre in _remover_acentos(tarefa_api.lower()):
                    log(f"[MOV_INT] tarefa já está em '{tarefa_api}' (via API) — nada a fazer")
                    return True

        # ===== ETAPA 0: NAVEGAR PARA ABA TAREFA VIA API (padrao gigs-plugin L4491-4516) =====
        # Em chamadas recursivas (apos navegar para 'análise') NAO reabrir a
        # tarefa via API — isso desfaz a navegacao e causa loop infinito.
        api_ok = False
        if not pular_abertura_api:
            api_ok = abrir_tarefa_por_api(driver, timeout=timeout)

        tarefa_text = None
        if api_ok:
            tarefa_text = _obter_tarefa_atual_robusta(driver, timeout=max(3, timeout // 2), debug=True)
        if not tarefa_text:
            try:
                from .movimentos_navegacao import navegar_para_tarefa
                if navegar_para_tarefa(driver, 'análise', debug=True, timeout=timeout):
                    tarefa_text = _obter_tarefa_atual_robusta(driver, timeout=max(3, timeout // 2), debug=True)
            except Exception:
                pass

        if not tarefa_text:
            logger.warning('[MOV_INT] Não foi possível determinar tarefa atual — abortando')
            return False

        tarefa_norm = _remover_acentos((tarefa_text or '').lower())
        destino_norm = _remover_acentos((destino or '').lower())
        if '?' in destino:
            destino_norm = destino_norm.replace('?', '') + ' ' + tarefa_norm

        log(f"[MOV_INT] tarefa='{tarefa_text}' destino='{destino}'")

        if destino_norm and destino_norm in tarefa_norm:
            if ultimo_lance:
                try:
                    btn = esperar_elemento(driver, 'button', texto=ultimo_lance, timeout=3)
                    if btn:
                        safe_click_no_scroll(driver, btn)
                except Exception:
                    pass
            if chip:
                try:
                    safe_click_no_scroll(driver, esperar_elemento(driver, 'button[aria-label="Incluir Chip Amarelo"]', timeout=2))
                except Exception:
                    pass
            if responsavel:
                try:
                    buscar_seletor_robusto(driver, ['Abrir o GIGS', 'GIGS'], timeout=2)
                except Exception:
                    pass
            return True

        if 'elaborar' in tarefa_norm or 'assinar' in tarefa_norm:
            log('[MOV_INT] tarefa de elaborar/assinar - abortando')
            return False

        # Tentativa genérica de clicar no botão de destino direto na tarefa atual
        try:
            bt = _localizar_botao_destino_movimento(driver, destino, timeout=timeout)
            if bt and bt.is_enabled():
                log(f"[MOV_INT] clicando botão destino direto: {destino}")
                if safe_click_no_scroll(driver, bt, log=True):
                    if ultimo_lance:
                        try:
                            clicar_ultimo_lance(driver, ultimo_lance)
                        except Exception:
                            pass
                    try:
                        chip_responsavel(driver, chip=chip, responsavel=responsavel)
                    except Exception:
                        pass
                    return True
        except Exception as e:
            log(f"[MOV_INT] falha ao clicar destino direto: {e}")

        if 'elaborar' in tarefa_norm or 'assinar' in tarefa_norm:
            log('[MOV_INT] tarefa de elaborar/assinar - abortando')
            return False

        if 'analise' in tarefa_norm:
            try:
                bt = _localizar_botao_destino_movimento(driver, destino, timeout=timeout)
                if bt and bt.is_enabled():
                    safe_click_no_scroll(driver, bt)
                    # último lance, chip e responsavel manejados por helpers
                    if ultimo_lance:
                        try:
                            clicar_ultimo_lance(driver, ultimo_lance)
                        except Exception:
                            pass
                    try:
                        chip_responsavel(driver, chip=chip, responsavel=responsavel)
                    except Exception:
                        pass
                    return True
                return False
            except Exception:
                return False

        try:
            from .movimentos_navegacao import navegar_para_tarefa
            if navegar_para_tarefa(driver, 'análise', debug=True, timeout=timeout, tarefa_atual_conhecida=tarefa_text):
                tarefa_text = _obter_tarefa_atual_robusta(driver, timeout=max(3, timeout // 2), debug=True) or tarefa_text
                tarefa_norm = _remover_acentos((tarefa_text or '').lower())
                if 'analise' in tarefa_norm:
                    return movimentar_inteligente(driver, destino, ultimo_lance=ultimo_lance, chip=chip, responsavel=responsavel, timeout=timeout, profundidade=profundidade + 1, pular_abertura_api=True)
        except Exception:
            pass

        try:
            btn_analise = _localizar_botao_destino_movimento(driver, 'Análise', timeout=4)
            if btn_analise:
                safe_click_no_scroll(driver, btn_analise)
                aguardar_renderizacao_nativa(driver, 'pje-botoes-transicao', modo='aparecer', timeout=6)
                return movimentar_inteligente(driver, destino, ultimo_lance=ultimo_lance, chip=chip, responsavel=responsavel, timeout=timeout, profundidade=profundidade + 1, pular_abertura_api=True)
        except Exception:
            pass

        return False
    except Exception as e:
        try:
            logger.error(f'[MOV_INT][ERRO] {e}')
        except Exception:
            pass
        return False


def clicar_ultimo_lance(driver: Any, texto_ultimo_lance: str, timeout: int = 5) -> bool:
    """Tenta clicar no último lance indicado pelo texto.

    Retorna True se clicou, False caso contrário.
    """
    try:
        if not texto_ultimo_lance:
            return False
        btn = None
        try:
            btn = esperar_elemento(driver, 'button', texto=texto_ultimo_lance, timeout=max(2, timeout//2))
        except Exception:
            btn = None

        if not btn:
            # tentar buscar por parcial do texto
            try:
                btns = espera.elementos(driver, f"//button[contains(., '{texto_ultimo_lance}')]", teto=max(2, timeout//2))
                for b in btns:
                    try:
                        if getattr(b, 'is_displayed', lambda: True)() and getattr(b, 'is_enabled', lambda: True)():
                            btn = b
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if btn:
            try:
                safe_click_no_scroll(driver, btn)
                return True
            except Exception:
                return False
        return False
    except Exception:
        return False


def chip_responsavel(driver, chip: Optional[str] = None, responsavel: Optional[str] = None, timeout: int = 5) -> None:
    """Clica no chip (se solicitado) e tenta abrir seleção de responsável (GIGS) se solicitado.

    Não lança exceções em falhas, apenas tenta realizar as ações.
    """
    try:
        # Chip amarelo padrão
        if chip:
            try:
                el = esperar_elemento(driver, 'button[aria-label="Incluir Chip Amarelo"]', timeout=max(1, timeout//2))
                if el:
                    safe_click_no_scroll(driver, el)
            except Exception:
                pass

        # Responsável: abrir o GIGS para escolher, se aplicável
        if responsavel:
            try:
                gg = buscar_seletor_robusto(driver, ['Abrir o GIGS', 'GIGS'], timeout=max(1, timeout//2))
                if gg:
                    safe_click_no_scroll(driver, gg)
            except Exception:
                pass
    except Exception:
        pass
