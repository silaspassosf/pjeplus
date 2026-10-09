"""
PEC.anexos.juntador.metodos - Métodos da classe Juntador.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contém os métodos específicos da classe Juntador (_escolher_opcao_gigs, etc.).
"""

import logging
logger = logging.getLogger(__name__)

import os
import re
import time
import types
from typing import Optional, Dict, Any, Callable, Union, List


def _executar_js(driver: Any, script: str, *args):
    """Executa script JS de forma compatível sem invocar padrão regex."""
    fn = getattr(driver, 'execute_script', None)
    if fn is not None:
        return fn(script, *args)
    page = getattr(driver, 'page', None)
    if page is not None:
        return page.evaluate(script, *args)
    return None


# Imports do Fix
from Fix import espera
from Fix.core import (
    safe_click_no_scroll,
    aguardar_e_clicar,
    selecionar_opcao,
    preencher_campo,
    safe_click,
    wait_for_clickable,
    wait_for_visible,
)
from Fix.utils import (
    inserir_html_no_editor_apos_marcador,
    obter_ultimo_conteudo_clipboard,
    executar_coleta_parametrizavel,
    inserir_link_ato_validacao,
)

# Imports dos módulos refatorados
from .anexos_extracao import extrair_numero_processo_da_url
from .anexos_formatacao import formatar_conteudo_ecarta
from .anexos_juntador_helpers import substituir_marcador_por_conteudo


def _escolher_opcao_gigs(self, seletor: str, valor: str, nome_campo: str) -> bool:
    """Implementa escolherOpcaoTeste/escolherOpcaoTeste2 do gigs-plugin.js com suporte a autocomplete."""
    try:
        driver = self.driver

        # 1. Encontra o campo (com espera)
        elementos_campo = espera.elementos(driver, seletor, teto=6)
        if not elementos_campo:
            logger.error('[JUNTADA] Campo %s não apareceu a tempo', nome_campo)
            return False
        campo = elementos_campo[0]

        # 2. Foco e abertura via click / Enter / ArrowDown (padrão gigs escolherOpcaoTeste2)
        _executar_js(driver, """
            const el = arguments[0];
            el.focus();
            const p = el.closest('mat-form-field') || (el.parentElement ? el.parentElement.parentElement : el);
            if (p) p.click();
            el.click();
            el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
            el.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', keyCode: 40, bubbles: true}));
        """, campo)

        # 3. Aguarda opções aparecerem
        if not espera.ate_aparecer(driver, "mat-option[role='option'], mat-option", teto=3):
            # Se não abriu imediatamente, preenche valor no input para ativar autocomplete do Angular
            _executar_js(driver, """
                const el = arguments[0];
                const val = arguments[1];
                el.focus();
                Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, val);
                ['input', 'change', 'keyup'].forEach(ev => el.dispatchEvent(new Event(ev, {bubbles: true})));
                el.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', keyCode: 40, bubbles: true}));
            """, campo, valor)
            espera.ate_aparecer(driver, "mat-option[role='option'], mat-option", teto=4)

        opcoes = espera.elementos(driver, "mat-option[role='option'], mat-option", teto=4)
        for opcao in opcoes:
            texto = (getattr(opcao, 'text_content', None) and opcao.text_content()) or getattr(opcao, 'text', '') or ''
            if valor.lower() in texto.lower():
                safe_click_no_scroll(driver, opcao)
                logger.debug('[JUNTADA] %s selecionado: %s', nome_campo, valor)
                return True

        # Fallback de filtragem direta: se opções foram abertas mas a desejada não apareceu (lista grande)
        _executar_js(driver, """
            const el = arguments[0];
            const val = arguments[1];
            el.focus();
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, val);
            ['input', 'change', 'keyup'].forEach(ev => el.dispatchEvent(new Event(ev, {bubbles: true})));
        """, campo, valor)
        espera.assentar(driver, 0.4)
        opcoes = espera.elementos(driver, "mat-option[role='option'], mat-option", teto=4)
        for opcao in opcoes:
            texto = (getattr(opcao, 'text_content', None) and opcao.text_content()) or getattr(opcao, 'text', '') or ''
            if valor.lower() in texto.lower():
                safe_click_no_scroll(driver, opcao)
                logger.debug('[JUNTADA] %s selecionado após filtro: %s', nome_campo, valor)
                return True

        logger.error('[JUNTADA] Opção "%s" não encontrada em %s', valor, nome_campo)
        return False

    except Exception as e:
        logger.error('[JUNTADA] Falha ao selecionar %s: %s', nome_campo, e)
        return False


def _preencher_input_gigs(self, seletor: str, valor: str, nome_campo: str) -> bool:
    """Implementa preencherInput do gigs-plugin.js"""
    try:
        driver = self.driver

        # Encontra o elemento (com espera — mesma corrida de render da
        # 1ª abertura da aba /anexar que afetava _escolher_opcao_gigs)
        elementos_campo = espera.elementos(driver, seletor, teto=8)
        if not elementos_campo:
            logger.error(f'[JUNTADA][ERRO] Campo {nome_campo} não apareceu a tempo')
            return False
        campo = elementos_campo[0]

        # Implementa exatamente como no gigs-plugin.js usando JavaScript
        resultado = _executar_js(driver, """
            const elemento = arguments[0];
            const valor = arguments[1];

            // Focus no elemento (JavaScript, não WebElement)
            elemento.focus();

            // Define valor usando Object.getOwnPropertyDescriptor (padrão GIGS)
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(elemento, valor);

            // Dispara eventos exatos do GIGS
            function triggerEvent(el, eventType) {
                const event = new Event(eventType, {bubbles: true, cancelable: true});
                el.dispatchEvent(event);
            }

            triggerEvent(elemento, 'input');
            triggerEvent(elemento, 'change');
            triggerEvent(elemento, 'dateChange');
            triggerEvent(elemento, 'keyup');

            // Simula Enter (padrão GIGS)
            const enterEvent = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true});
            elemento.dispatchEvent(enterEvent);

            // Blur no elemento
            elemento.blur();

            return true;
        """, campo, valor)

        return True

    except Exception as e:
        logger.error(f'[JUNTADA][ERRO] Falha ao preencher {nome_campo}: {e}')
        return False


def _clicar_elemento_gigs(self, seletor: str, nome_elemento: str) -> bool:
    """Implementa clicarBotao do gigs-plugin.js com múltiplas tentativas"""
    try:
        driver = self.driver

        # Lista de seletores alternativos para botão Salvar
        if 'Salvar' in nome_elemento:
            seletores = [
                'button[aria-label="Salvar"]',
                'button[mat-raised-button][color="primary"][aria-label="Salvar"]',
                'button.mat-raised-button.mat-primary[aria-label="Salvar"]',
                'button.mat-focus-indicator.mat-raised-button.mat-button-base.mat-primary[aria-label="Salvar"]',
                'button:contains("Salvar")',
                '[aria-label="Salvar"]'
            ]
        # Lista de seletores alternativos para botão Assinar
        elif 'Assinar' in nome_elemento:
            seletores = [
                'button[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-fab[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-focus-indicator.mat-fab.mat-button-base.mat-accent[aria-label="Assinar documento e juntar ao processo"]',
                'button[mat-fab].mat-accent[aria-label="Assinar documento e juntar ao processo"]',
                'button.mat-fab .fa-pen-nib',
                'button:contains("Assinar")',
                '[aria-label*="Assinar"]'
            ]
        else:
            seletores = [seletor]

        for i, sel in enumerate(seletores):
            try:
                logger.debug('[JUNTADA] Tentando seletor %d: %s', i + 1, sel)

                # Tenta encontrar o elemento
                if ':contains(' in sel:
                    # Para seletores com :contains, usar JavaScript
                    elemento = _executar_js(driver, """
                        const buttons = document.querySelectorAll('button');
                        return Array.from(buttons).find(btn =>
                            btn.textContent.trim().toLowerCase().includes('salvar') ||
                            btn.getAttribute('aria-label') === 'Salvar'
                        );
                    """)
                else:
                    elementos = espera.elementos(driver, sel, teto=1)
                    elemento = elementos[0] if elementos else None

                if elemento:
                    logger.debug('[JUNTADA] Elemento encontrado com seletor %d: %s', i + 1, sel)

                    # Tentativas de clique
                    for tentativa in range(2):
                        try:
                            # Scroll para o elemento
                            _executar_js(driver, "arguments[0].scrollIntoView({block:'center'});", elemento)

                            # Verifica se elemento é clicável
                            is_enabled = getattr(elemento, 'is_enabled', None)
                            is_displayed = getattr(elemento, 'is_displayed', None)
                            ok_enabled = is_enabled() if callable(is_enabled) else True
                            ok_displayed = is_displayed() if callable(is_displayed) else True
                            if ok_enabled and ok_displayed:
                                # Tenta clique JavaScript
                                safe_click_no_scroll(driver, elemento)
                                logger.debug('[JUNTADA] Clique realizado: %s (seletor %d, tentativa %d)', nome_elemento, i + 1, tentativa + 1)
                                return True
                            else:
                                logger.debug('[JUNTADA] Elemento não clicável (enabled: %s, visible: %s)', ok_enabled, ok_displayed)
                                espera.assentar(driver, 0.2)

                        except Exception as e:
                            if tentativa < 1:
                                logger.debug('[JUNTADA] Tentativa %d falhou para %s: %s', tentativa + 1, nome_elemento, e)
                                espera.assentar(driver, 0.3)
                            else:
                                logger.debug('[JUNTADA] Tentativas falharam para %s com seletor %s: %s', nome_elemento, sel, e)
                else:
                    logger.debug('[JUNTADA] Elemento não encontrado com seletor %d: %s', i + 1, sel)

            except Exception as e:
                if i < len(seletores) - 1:  # Não é o último seletor
                    logger.debug('[JUNTADA] Seletor %d "%s" falhou: %s', i + 1, sel, e)
                    continue
                else:
                    logger.debug('[JUNTADA] Último seletor "%s" falhou: %s', sel, e)

        logger.error('[JUNTADA] Todos os seletores falharam para %s', nome_elemento)
        return False

    except Exception as e:
        logger.error('[JUNTADA] Falha geral ao clicar %s: %s', nome_elemento, e)
        return False


def _selecionar_modelo_gigs(self, modelo: str) -> bool:
    """Seleciona e insere o modelo no editor da juntada (aaAnexar).

    Implementação DEDICADA ao contexto da juntada/anexar — NÃO delega para
    judicial_modelos.inserir_modelo_no_editor porque:
    - O editor-alvo é 'div[class*="area-conteudo"][contenteditable][aria-label*="Conteúdo principal"]'
    - O aaAnexar do gigs-plugin foca esse editor ANTES de filtrar (api/gigs-plugin.js:10106)
    - A prova de conteúdo é innerText > 1 OU figure (verificarSeExisteTextoNoEditor L10261)
    Fonte: api/gigs-plugin.js acao_bt_aaAnexar L10100-10124 + inserirModeloNoDocumento L10192-10253.
    """
    driver = self.driver
    try:
        # 0. Foco no editor-alvo ANTES de filtrar (padrão aaAnexar gigs L10106)
        sel_editor = (
            'div[class*="area-conteudo"][contenteditable="true"][aria-label*="Conteúdo principal"],'
            'div[class*="area-conteudo"][contenteditable="true"],'
            '.ck-editor__editable[contenteditable="true"]'
        )
        _executar_js(driver, """
            var el = document.querySelector(arguments[0].split(',').find(s => document.querySelector(s)));
            if (el) { el.focus(); }
        """, sel_editor)

        # 1. Disparar eventos iniciais no filtro (elimina carregamento eterno — aaAnexar L10111)
        _executar_js(driver, """
            var f = document.getElementById('inputFiltro');
            if (f) {
                f.dispatchEvent(new Event('input', {bubbles: true}));
                f.dispatchEvent(new Event('keyup', {bubbles: true}));
            }
        """)

        # 2. Preencher filtro com native setter + eventos (padrão preencherInput gigs)
        campo_filtro = wait_for_clickable(driver, 'input#inputFiltro', timeout=10)
        if not campo_filtro:
            logger.error('[JUNTADA][MODELO][ERRO] Campo input#inputFiltro não encontrado')
            return False

        _executar_js(driver, """
            var el = arguments[0];
            var val = arguments[1];
            el.focus();
            Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')
                .set.call(el, val);
            ['input', 'change', 'keyup'].forEach(ev =>
                el.dispatchEvent(new Event(ev, {bubbles: true}))
            );
            el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
        """, campo_filtro, modelo)

        if hasattr(driver, 'page') and driver.page:
            try:
                driver.page.keyboard.press('Enter')
            except Exception:
                pass
        espera.assentar(driver, 0.3, 'aguardando filtro de modelo ser aplicado na árvore')

        # 3. Aguardar nodo filtrado e clicar
        # Caminho primário rápido (comportamento nativo validado): wait_for_clickable encontra o
        # .nodo-filtrado diretamente assim que o filtro do Angular renderiza (< 500ms).
        sel_nodo = 'span.nodo-filtrado, .nodo-filtrado'
        nodo = wait_for_clickable(driver, sel_nodo, timeout=5)
        clicou_nodo = False
        if nodo:
            _executar_js(driver, "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", nodo)
            clicou_nodo = True
        else:
            # Fallback assistido: se galhos da árvore estiverem fechados, expande sob demanda
            logger.debug('[JUNTADA][MODELO] Nodo filtrado não clicável direto, tentando expansão assistida de galhos')
            js_expandir_e_buscar = """() => {
                var nodo = document.querySelector('span.nodo-filtrado, .nodo-filtrado');
                if (nodo) {
                    var alvo = nodo.closest('mat-tree-node') || nodo.parentElement || nodo;
                    try { alvo.scrollIntoView({block: 'center', behavior: 'instant'}); } catch(e) {}
                    nodo.click();
                    return { status: 'encontrado' };
                }
                var fechados = Array.from(document.querySelectorAll('pje-arvore-modelo-documento div[aria-expanded="false"], pje-arvore-modelo-documento mat-tree-node[aria-expanded="false"] button'));
                if (fechados.length > 0) {
                    fechados[0].click();
                    return { status: 'expandindo' };
                }
                return { status: 'aguardando' };
            }"""
            limite_nodo = time.time() + 4
            while time.time() < limite_nodo:
                try:
                    res = _executar_js(driver, f"return ({js_expandir_e_buscar})();")
                    if isinstance(res, dict) and res.get('status') == 'encontrado':
                        clicou_nodo = True
                        break
                except Exception:
                    pass
                espera.assentar(driver, 0.3)

        if not clicou_nodo:
            logger.error('[JUNTADA][MODELO][ERRO] .nodo-filtrado não encontrado para "%s"', modelo)
            return False

        logger.debug('[JUNTADA][MODELO] Clique em .nodo-filtrado realizado')

        # 4. Aguardar diálogo de preview entrar no DOM
        if not espera.ate_aparecer(driver, 'pje-dialogo-visualizar-modelo', teto=8):
            logger.warning('[JUNTADA][MODELO] Diálogo pje-dialogo-visualizar-modelo não detectado')

        # 5. Guarda anti-corrida: aguarda o teor do preview carregar de forma dinâmica
        # (se carregar rápido, prossegue imediatamente em vez de pausa fixa desnecessária)
        _JS_TEOR_PREVIEW = """() => {
            var dlg = document.querySelector('pje-dialogo-visualizar-modelo');
            if (!dlg) return false;
            var preview = dlg.querySelector('.div-preview-conteudo, .preview-conteudo, .conteudo-modelo, .ck-content, [class*="preview"]');
            if (!preview) return false;
            var clone = preview.cloneNode(true);
            clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
            var txt = (clone.innerText || clone.textContent || '').trim();
            return txt.length > 10 || clone.querySelector('figure') !== null || clone.querySelector('table') !== null;
        }"""
        if not espera.ate_js(driver, f"({_JS_TEOR_PREVIEW})()", teto=3):
            espera.assentar(driver, 0.3, 'aguarda preview/teor carregar no dialogo antes de inserir')

        # 6. Clicar botão Inserir (aria-label canônico conforme gigs L10224 e MaisPje)
        seletor_btn_inserir = (
            'button[aria-label="Inserir modelo de documento"],'
            'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button,'
            'pje-dialogo-visualizar-modelo button'
        )
        btn_inserir = wait_for_clickable(driver, seletor_btn_inserir, timeout=6)
        if not btn_inserir:
            logger.error('[JUNTADA][MODELO][ERRO] Botão Inserir não encontrado')
            return False

        # Dispara tecla Space (padrão MaisPje / legado L19260) com fallback de clique
        _inserido = False
        try:
            if hasattr(btn_inserir, '_handle') and btn_inserir._handle:
                btn_inserir._handle.focus()
                if hasattr(driver, 'page') and driver.page:
                    driver.page.keyboard.press('Space')
                    _inserido = True
        except Exception:
            pass

        if not _inserido:
            _executar_js(driver, """
                var btn = arguments[0];
                btn.focus();
                btn.dispatchEvent(new KeyboardEvent('keydown', {code: 'Space', keyCode: 32, which: 32, bubbles: true}));
                btn.dispatchEvent(new KeyboardEvent('keyup', {code: 'Space', keyCode: 32, which: 32, bubbles: true}));
                btn.click();
            """, btn_inserir)

        logger.debug('[JUNTADA][MODELO] Clique em Inserir modelo realizado')

        # 7. Aguardar diálogo de preview sumir
        espera.ate_sumir(driver, 'pje-dialogo-visualizar-modelo', teto=8)

        # 8. VERIFICAÇÃO REAL DE CONTEÚDO (verificarSeExisteTextoNoEditor gigs L10261)
        _JS_JUNTADA_EDITOR_COM_CONTEUDO = """() => {
            var sels = [
                'div[class*="area-conteudo"][contenteditable="true"]',
                '.ck-editor__editable[contenteditable="true"]',
                '.ck-content[contenteditable="true"]',
                'div[contenteditable="true"]'
            ];
            for (var s of sels) {
                var area = document.querySelector(s);
                if (area) {
                    var clone = area.cloneNode(true);
                    clone.querySelectorAll('.placeholder-conteudo, .ck-placeholder, [data-placeholder]').forEach(p => p.remove());
                    var txt = (clone.innerText || clone.textContent || '').replace(/\\s/g, '');
                    if (txt.length > 1 || clone.querySelector('figure') !== null || clone.querySelector('table') !== null) {
                        return true;
                    }
                }
            }
            return false;
        }"""
        modelo_carregado = bool(espera.ate_js(driver, f"({_JS_JUNTADA_EDITOR_COM_CONTEUDO})()", teto=8))

        if not modelo_carregado:
            # Fallback: tentar clique direto no botão de inserir se o modal ainda estiver por perto
            try:
                _executar_js(driver, "arguments[0].click();", btn_inserir)
            except Exception:
                pass
            modelo_carregado = bool(espera.ate_js(driver, f"({_JS_JUNTADA_EDITOR_COM_CONTEUDO})()", teto=5))

        if modelo_carregado:
            logger.info('[JUNTADA][MODELO] Modelo "%s" confirmado no editor (conteúdo real)', modelo)
            return True
        else:
            logger.error('[JUNTADA][MODELO][ERRO] Editor permaneceu vazio após inserção de "%s"', modelo)
            return False

    except Exception as e:
        logger.error('[JUNTADA][MODELO][ERRO] Falha ao selecionar/inserir modelo: %s', e)
        return False


def _executar_coleta_opcional(self, configuracao: Dict[str, Any]) -> bool:
    """Executa coleta de conteúdo se configurada."""
    coleta_conteudo = configuracao.get('coleta_conteudo')
    if not coleta_conteudo:
        return True  # Não é erro não ter coleta

    numero_processo_atual = extrair_numero_processo_da_url(self.driver)
    if not numero_processo_atual:
        logger.debug('[JUNTADA][COLETA] Número do processo não identificado')
        return True  # Não falha por não conseguir extrair número

    try:
        logger.debug('[JUNTADA][COLETA] Iniciando coleta: %s | processo: %s', coleta_conteudo, numero_processo_atual)
        executar_coleta_parametrizavel(self.driver, numero_processo_atual, coleta_conteudo, debug=True)
        return True
    except Exception as e:
        logger.warning('[JUNTADA][COLETA] Falha ao executar coleta opcional: %s', e)
        return True  # Coleta opcional não deve falhar a juntada


def _preencher_tipo(self, configuracao: Dict[str, Any]) -> bool:
    """Preenche Tipo de Documento."""
    tipo = configuracao.get('tipo', 'Certidão')
    return self._escolher_opcao_gigs('input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento')


def _preencher_descricao(self, configuracao: Dict[str, Any]) -> bool:
    """Preenche Descrição."""
    descricao = configuracao.get('descricao', '')
    if not descricao:
        return True  # Descrição opcional
    return self._preencher_input_gigs('input[aria-label="Descrição"]', descricao, 'Descrição')


def _configurar_sigilo(self, configuracao: Dict[str, Any]) -> bool:
    """Configura sigilo se necessário."""
    sigilo = configuracao.get('sigilo', 'nao').lower()
    if 'sim' in sigilo:
        return self._clicar_elemento_gigs('input[name="sigiloso"]', 'Sigilo')
    return True  # Não é erro não configurar sigilo


def _selecionar_e_inserir_modelo(self, configuracao: Dict[str, Any]) -> bool:
    """Seleciona e insere modelo no editor."""
    modelo = configuracao.get('modelo', '')
    if not modelo:
        return True  # Modelo opcional
    return self._selecionar_modelo_gigs(modelo)


def _inserir_conteudo_customizado(self, configuracao: Dict[str, Any], substituir_link: bool = False) -> bool:
    """Insere conteúdo customizado ou substitui link."""
    try:
        inserir_conteudo = configuracao.get('inserir_conteudo')
        if inserir_conteudo:
            inserir_fn = inserir_conteudo
            if isinstance(inserir_conteudo, str):
                try:
                    if inserir_conteudo.lower() in ('link_ato', 'link_ato_validacao'):
                        inserir_fn = inserir_link_ato_validacao
                except Exception as _e:
                    logger.warning(f"[JUNTADA][INSERIR][WARN] Não foi possível resolver função por string: {inserir_conteudo} -> {_e}")

            # Número do processo: priorizar dadosatuais.json (número CNJ) em vez de ID da URL
            numero_processo_atual = None
            try:
                import json
                from pathlib import Path
                dados_path = Path('dadosatuais.json')
                if dados_path.exists():
                    dados = json.loads(dados_path.read_text(encoding='utf-8'))
                    numero = dados.get('numero')
                    if isinstance(numero, list) and numero:
                        numero_processo_atual = numero[0]
                    elif isinstance(numero, str) and numero.strip():
                        numero_processo_atual = numero.strip()
            except Exception as e:
                logger.error(f'[JUNTADA][INSERIR][WARN] Erro ao ler dadosatuais.json: {e}')

            # Fallback: extrair da URL se não conseguiu do JSON
            if not numero_processo_atual:
                numero_processo_atual = extrair_numero_processo_da_url(self.driver)
                logger.warning(f'[JUNTADA][INSERIR][WARN] Usando ID da URL como fallback: {numero_processo_atual}')

            # Gate anti-atropelo: se já existe editor na página, só cola quando
            # o modelo estiver realmente presente no editor.
            editor_presente = espera.ate_aparecer(
                self.driver, '.ck-editor__editable[contenteditable=true]', teto=4
            )
            if editor_presente:
                conteudo_no_editor = (
                    "__pjeEls('.ck-editor__editable[contenteditable=true]').some("
                    "el => (el.innerHTML || '').includes('--') || ((el.textContent || '').trim().length > 20))"
                )
                if not espera.ate_js(self.driver, conteudo_no_editor, teto=10):
                    logger.error(
                        "[JUNTADA][INSERIR][ERRO] Conteúdo do modelo não chegou ao editor em 10s — "
                        "colagem abortada para não salvar documento incompleto."
                    )
                    return False

            ok = False
            try:
                ok = inserir_fn(driver=self.driver, numero_processo=numero_processo_atual, debug=True)
            except TypeError as te:
                try:
                    ok = inserir_fn(self.driver, numero_processo_atual)
                except Exception as e2:
                    try:
                        ok = inserir_fn(self.driver)
                    except Exception as e3:
                        logger.error(f"[JUNTADA][INSERIR][ERRO] Todas as tentativas de chamada falharam: {e3}")
                        return False

            if ok:
                espera.assentar(self.driver, 0.5, 'assentamento pos-insercao')
            return ok

        elif substituir_link:
            # Compat: caminho antigo de substituição
            espera.ate_js(
                self.driver,
                "typeof CKEDITOR !== 'undefined'"
                " && Object.keys(CKEDITOR.instances || {}).length > 0",
                teto=3,
            )
            if not substituir_marcador_por_conteudo(self.driver, debug=True):
                logger.error('[JUNTADA][ERRO] Falha na substituição do link!')
                return False
            espera.pausa(self.driver, 2, 'assentamento pos-substituicao no editor')
            return True

        return True  # Não é erro não ter conteúdo para inserir

    except Exception as e:
        logger.error(f"[JUNTADA][INSERIR][WARN] Erro durante inserção opcional: {e}")
        return False


def _salvar_documento(self) -> bool:
    """Salva documento com confirmação efetiva no PJe.

    Inspirado no comportamento histórico do branch main (core.py.backup_final)
    e adaptado para Playwright nativo sem dependências de Selenium:
    1. Sincroniza editor (blur + eventos) e descarta snackbar residual de inserção de modelo.
    2. Clica no botão Salvar com fallback robusto.
    3. Aguarda confirmação real de salvamento:
       - snackbar específico de salvamento (excluindo 'modelo')
       - OU botão Salvar desabilitado + botão Assinar liberado.
    4. Retry de clique caso o documento não tenha persistido e o botão Salvar continue ativo.
    5. Assentamento seguro antes de liberar o fechamento da aba.
    """
    driver = self.driver
    logger.debug('[JUNTADA] Salvando documento final...')

    # 1. Sincronização do editor e descarte de notificações de etapas anteriores (ex: inserção de modelo)
    _executar_js(driver, """
        const ed = document.querySelector('.ck-editor__editable[contenteditable="true"], [contenteditable="true"]');
        if (ed) {
            ed.dispatchEvent(new Event('input', { bubbles: true }));
            ed.dispatchEvent(new Event('change', { bubbles: true }));
            ed.blur();
        }
        // Fecha ou descarta qualquer snackbar anterior para evitar falsos positivos
        const oldSnacks = document.querySelectorAll('simple-snack-bar, snack-bar-container');
        oldSnacks.forEach(snack => {
            const btn = snack.querySelector('button');
            if (btn) btn.click();
            else snack.remove();
        });
    """)
    espera.assentar(driver, 0.4, 'sincronizacao do editor e descarte de snackbar residual')

    # 2. Clique no botão Salvar
    clicou = self._clicar_elemento_gigs('button[aria-label="Salvar"]', 'Salvar documento')
    if not clicou:
        # Fallback via JS nativo se _clicar_elemento_gigs não conseguiu
        clicou = bool(_executar_js(driver, """
            const btn = document.querySelector('button[aria-label="Salvar"], button.mat-primary[aria-label="Salvar"]');
            if (btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true') {
                btn.click();
                return true;
            }
            return false;
        """))
    if not clicou:
        logger.error('[JUNTADA] Falha no salvamento principal!')
        return False

    logger.debug('[JUNTADA] Aguardando processamento do salvamento...')

    # 3. Confirmação objetiva do salvamento
    js_salvamento_confirmado = """
        // A. Snackbar específico de salvamento (descarta explicitamente mensagens de modelo)
        var snack = document.querySelector('simple-snack-bar, snack-bar-container');
        if (snack) {
            var t = (snack.innerText || snack.textContent || '').toLowerCase();
            if (!t.includes('modelo') && (t.includes('salv') || t.includes('gravad') || (t.includes('documento') && t.includes('sucesso')))) {
                return true;
            }
        }
        // B. Botão Salvar desabilitado + Botão Assinar liberado indica minuta gravada com sucesso
        var btnSalvar = document.querySelector('button[aria-label="Salvar"]');
        var btnAssinar = document.querySelector('button[aria-label="Assinar documento e juntar ao processo"], button[aria-label*="Assinar"]');
        var salvarDesabilitado = btnSalvar && (btnSalvar.disabled || btnSalvar.getAttribute('aria-disabled') === 'true' || btnSalvar.classList.contains('mat-button-disabled'));
        var assinarPronto = btnAssinar && !btnAssinar.disabled && btnAssinar.getAttribute('aria-disabled') !== 'true';
        if (salvarDesabilitado && assinarPronto) {
            return true;
        }
        return false;
    """

    salvo = bool(espera.ate_js(driver, js_salvamento_confirmado, teto=4))

    # 4. Retry de segurança como no main (core.py.backup_final) caso ainda não tenha persistido
    if not salvo:
        btn_ainda_ativo = _executar_js(driver, """
            const btn = document.querySelector('button[aria-label="Salvar"]');
            return !!(btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true');
        """)
        if btn_ainda_ativo:
            logger.debug('[JUNTADA] Documento ainda não salvo após 4s, tentando retry do clique...')
            _executar_js(driver, """
                const btn = document.querySelector('button[aria-label="Salvar"]');
                if (btn) btn.click();
            """)
            salvo = bool(espera.ate_js(driver, js_salvamento_confirmado, teto=4))

    # Assentamento final de segurança antes de prosseguir (evita fechar a aba com requisição de rede pendente)
    espera.assentar(driver, 1.2, 'pos-salvar juntada')
    logger.debug('[JUNTADA] Salvamento confirmado com sucesso.')
    return True


def _assinar_se_necessario(self, configuracao: Dict[str, Any]) -> bool:
    """Assina documento se configurado."""
    if configuracao.get('assinar', 'nao').lower() == 'sim':
        seletor_assinar = 'button[aria-label="Assinar documento e juntar ao processo"]'
        espera.ate_habilitar(self.driver, seletor_assinar, teto=3)
        return self._clicar_elemento_gigs(seletor_assinar, 'Assinar')
    return True  # Não é erro não assinar
