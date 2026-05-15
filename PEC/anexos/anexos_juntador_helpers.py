"""
PEC.anexos.juntador.helpers - Helpers de decomposicao para juntada.

Parte da refatoracao do PEC/anexos/core.py para melhor granularidade IA.
Contem helpers para executar_juntada_ate_editor e substituir_marcador_por_conteudo.
"""

from Fix.log import logger

import os
import re
import html
import time
import types
from typing import Optional, Dict, Any, Callable, Union, List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Imports do Fix
from Fix.core import (
    aguardar_e_clicar,
    aguardar_renderizacao_nativa,
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


def _abrir_interface_anexacao(self: types.SimpleNamespace) -> bool:
    """Abre a interface de anexacao de documentos."""
    driver = self.driver
    logger.debug('[JUNTADA] Abrindo interface de anexacao...')
    qtd_abas_antes = len(driver.window_handles)

    # 1. Clique no menu (icone hamburguer)
    logger.debug('[JUNTADA] Clicando no menu hamburguer...')
    if not aguardar_e_clicar(driver, 'i[class*="fa-bars"].icone-botao-menu', 'Menu hamburguer'):
        return False
    wait_for_visible(driver, 'button[aria-label="Anexar Documentos"]', timeout=3)

    # 2. Clique em "Anexar Documentos"
    logger.debug('[JUNTADA] Clicando em "Anexar documentos"...')
    if not aguardar_e_clicar(driver, 'button[aria-label="Anexar Documentos"]', 'Anexar documentos'):
        return False
    try:
        WebDriverWait(driver, 5).until(
            lambda d: len(d.window_handles) > qtd_abas_antes or '/anexar' in (d.current_url or '')
        )
    except Exception:
        pass

    # 3. Aguarda nova aba/janela e muda para ela
    logger.debug('[JUNTADA] Mudando para aba de anexacao...')
    all_windows = driver.window_handles
    if len(all_windows) > 1:
        driver.switch_to.window(all_windows[-1])
        # CORRECAO: esperar_url_conter em vez de wait_for_visible(..., 'String') que causava erro de float
        from Fix.core import esperar_url_conter
        if not esperar_url_conter(driver, '/anexar', timeout=10):
            logger.warning('[JUNTADA] URL nao contem /anexar, mas prosseguindo...')
    else:
        logger.debug('[JUNTADA] Nova aba nao detectada, prosseguindo na mesma aba...')

    # Espera orientada a estado para o formulario principal de anexacao.
    aguardar_renderizacao_nativa(
        driver,
        'input[aria-label="Tipo de Documento"], input[data-placeholder="Tipo de Documento"]',
        'aparecer',
        3,
    )
    return True


def _preencher_campos_basicos(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool:
    """Preenche os campos basicos: tipo, descricao e sigilo."""
    driver = self.driver
    # Tipo de Documento
    tipo = configuracao.get('tipo', 'Certidao')
    if not selecionar_opcao(driver, 'input[aria-label="Tipo de Documento"]', tipo, 'Tipo de Documento'):
        return False

    # Descricao
    descricao = configuracao.get('descricao', '')
    if descricao:
        seletores_descricao = [
            'input[aria-label="Descrição"]',
            'input[aria-label="Descricao"]',
        ]
        for seletor in seletores_descricao:
            if driver.find_elements(By.CSS_SELECTOR, seletor):
                if not preencher_campo(driver, seletor, descricao, 'Descricao'):
                    return False
                break
        else:
            logger.error('[JUNTADA] Campo Descricao nao encontrado para preenchimento automatico')
            return False

    # Sigilo
    sigilo = configuracao.get('sigilo', 'nao').lower()
    if 'sim' in sigilo:
        if not aguardar_e_clicar(driver, 'input[name="sigiloso"]', 'Sigilo'):
            return False

    return True


def _inserir_modelo(self: types.SimpleNamespace, configuracao: Dict[str, Any]) -> bool:
    """Insere o modelo no editor e verifica se foi carregado."""
    driver = self.driver
    modelo_original = configuracao.get('modelo', '')
    if modelo_original:
        logger.debug('[JUNTADA] Selecionando e inserindo modelo: %s', modelo_original)
        if not self._selecionar_modelo_gigs(modelo_original):
            return False
        logger.debug('[JUNTADA] Aguardando modelo ser inserido no editor...')
        aguardar_renderizacao_nativa(
            driver,
            'simple-snack-bar, .ck-editor__editable[contenteditable="true"], div[contenteditable="true"]',
            'aparecer',
            5,
        )

    logger.debug('[JUNTADA] Verificando se editor esta disponivel apos insercao do modelo...')

    seletores_editor = [
        'div[aria-label="Conteudo principal. Alt+F10 para acessar a barra de tarefas"].area-conteudo.ck.ck-content.ck-editor__editable',
        '.area-conteudo.ck.ck-content.ck-editor__editable.ck-rounded-corners.ck-editor__editable_inline',
        '.area-conteudo.ck-editor__editable[contenteditable="true"]',
        '.ck-editor__editable[contenteditable="true"]',
        'div.fr-element[contenteditable="true"]',
        '[contenteditable="true"]'
    ]

    editor_encontrado = None
    for i, seletor in enumerate(seletores_editor):
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
            logger.debug('[JUNTADA] Seletor %s "%s": %s elementos', i+1, seletor, len(elementos))
            if elementos:
                editor_encontrado = elementos[0]
                logger.debug('[JUNTADA] Editor encontrado com seletor: %s', seletor)
                logger.debug('[JUNTADA] Editor visivel: %s', editor_encontrado.is_displayed())
                logger.debug('[JUNTADA] Editor habilitado: %s', editor_encontrado.is_enabled())
                conteudo = editor_encontrado.get_attribute('innerHTML')
                logger.debug('[JUNTADA] Conteudo do editor (primeiros 200 chars): %s...', conteudo[:200])
                if 'marker-yellow' in conteudo and 'link' in conteudo:
                    logger.debug('[JUNTADA] Editor contem termo "link" marcado em amarelo')
                elif conteudo.strip() and len(conteudo) > 100:
                    logger.debug('[JUNTADA] Editor contem conteudo do modelo inserido')
                else:
                    logger.warning('[JUNTADA] Editor parece vazio - modelo pode nao ter sido inserido')
                break
        except Exception as e:
            logger.debug('[JUNTADA] Erro com seletor %s: %s', i+1, e)
            continue

    if not editor_encontrado:
        logger.error("ERRO em _inserir_modelo: Nenhum editor encontrado com os seletores disponiveis")
        return False

    logger.debug('[JUNTADA] Editor disponivel para manipulacao')
    return True


def substituir_marcador_por_conteudo(driver, conteudo_customizado: Optional[str] = None, debug: bool = True, marcador: str = "--") -> bool:
    """
    Função melhorada para localizar marcador (ex: "--") e colar conteúdo após ele.
    Usa a mesma lógica robusta do editor_insert.py para maior compatibilidade.
    Simula ação manual: clique no final da linha + Ctrl+V
    Args:
        driver: Selenium WebDriver
        debug: Se deve exibir logs
        conteudo_customizado: Conteúdo específico para usar (se None, usa clipboard/arquivo)
        marcador: Texto a ser localizado (padrão: "--")
    """
    if debug:
        print(f"[SUBST_MARCADOR] Iniciando colagem após marcador '{marcador}'...")

    try:
        # 1) Determina o conteúdo a inserir.
        conteudo_para_usar = None
        fonte_conteudo = ""

        if conteudo_customizado:
            conteudo_para_usar = conteudo_customizado
            fonte_conteudo = "conteudo_customizado"
            if debug:
                print(f"[SUBST_MARCADOR] Usando conteúdo customizado: {len(conteudo_customizado)} chars")
        else:
            # Prioriza leitura estruturada do último bloco salvo no clipboard interno.
            try:
                conteudo_para_usar = obter_ultimo_conteudo_clipboard(debug=debug)
                if conteudo_para_usar:
                    fonte_conteudo = "clipboard_ultimo_bloco"
            except Exception:
                conteudo_para_usar = None

            # Fallback: ler arquivo local da pasta de anexos.
            if not conteudo_para_usar:
                try:
                    clipboard_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clipboard.txt")
                    if os.path.exists(clipboard_file):
                        with open(clipboard_file, 'r', encoding='utf-8') as f:
                            conteudo_para_usar = f.read().strip()
                        if conteudo_para_usar:
                            fonte_conteudo = "clipboard_arquivo_local"
                except Exception:
                    conteudo_para_usar = None

        if not conteudo_para_usar:
            print("[SUBST_MARCADOR] ✗ Nenhum conteúdo disponível para colar")
            return False

        # 2) Normaliza conteúdo para preservar formatação de clipboard.
        html_content_clean = (str(conteudo_para_usar)
                              .replace('\x00', '')
                              .replace('\r', '')
                              .strip())

        # Se o conteúdo vier como texto puro, converte quebras de linha em <br>
        # para manter a estrutura visual no editor.
        if not re.search(r'<[^>]+>', html_content_clean):
            html_content_clean = html.escape(html_content_clean).replace('\n', '<br>')

        # 3) Encontrar editor ativo.
        sels = [
            '.ck-editor__editable[contenteditable="true"]',
            '.ck-content[contenteditable="true"]',
            'div[role="textbox"][contenteditable="true"]',
        ]

        editable = None
        for sel in sels:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el and el.is_displayed() and el.is_enabled():
                    editable = el
                    if debug:
                        print(f"[SUBST_MARCADOR] Editor encontrado por seletor: {sel}")
                    break
            except Exception:
                continue

        if not editable:
            print("[SUBST_MARCADOR] ✗ Editor CKEditor não encontrado na página")
            return False

        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', editable)
        try:
            editable.click()
        except Exception:
            driver.execute_script('arguments[0].focus();', editable)

        # 4) Estratégia principal (legado): usar API do CKEditor quando disponível.
        # Fallback para substituição DOM quando API não estiver acessível.
        script_ckeditor = """
        let editor = arguments[0];
        let htmlContent = arguments[1];
        let marcador = arguments[2];

        try {
            let ckInstance = null;

            if (editor.ckeditorInstance) {
                ckInstance = editor.ckeditorInstance;
            }

            if (!ckInstance && window.CKEDITOR) {
                for (let instanceName in window.CKEDITOR.instances) {
                    let instance = window.CKEDITOR.instances[instanceName];
                    if (instance.element && instance.element.$ === editor) {
                        ckInstance = instance;
                        break;
                    }
                }
            }

            if (!ckInstance) {
                let ckEditor = editor.closest('.ck-editor');
                if (ckEditor && ckEditor.ckeditorInstance) {
                    ckInstance = ckEditor.ckeditorInstance;
                }
            }

            if (ckInstance && ckInstance.getData && ckInstance.setData) {
                let htmlOriginal = ckInstance.getData();
                if (htmlOriginal.includes(marcador)) {
                    let novoHtml = htmlOriginal.replace(marcador, htmlContent);
                    ckInstance.setData(novoHtml);
                    return { sucesso: true, metodo: 'ckeditor_api_setData' };
                }
            }

            editor.focus();
            let htmlOriginal = editor.innerHTML || '';
            if (htmlOriginal.includes(marcador)) {
                editor.innerHTML = htmlOriginal.replace(marcador, htmlContent);
                editor.dispatchEvent(new Event('input', { bubbles: true }));
                editor.dispatchEvent(new Event('change', { bubbles: true }));
                editor.dispatchEvent(new Event('keyup', { bubbles: true }));
                editor.blur();
                setTimeout(() => editor.focus(), 10);
                return { sucesso: true, metodo: 'dom_replace_innerHTML' };
            }

            return { sucesso: false, erro: 'Marcador nao encontrado no HTML do editor' };

        } catch (e) {
            return { sucesso: false, erro: e.message };
        }
        """

        resultado = driver.execute_script(script_ckeditor, editable, html_content_clean, marcador)

        # 5) Fallback final: TreeWalker+Range, para cenários em que o marcador
        # existe apenas como nó de texto fragmentado no DOM.
        if not (resultado and isinstance(resultado, dict) and resultado.get('sucesso')):
            script_treewalker = """
            let editor = arguments[0];
            let htmlContent = arguments[1];
            let marcador = arguments[2];
            try {
                let foundNode = null;
                let foundIdx = -1;
                const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
                let textNode;
                while ((textNode = walker.nextNode())) {
                    const idx = textNode.data.indexOf(marcador);
                    if (idx !== -1) {
                        foundNode = textNode;
                        foundIdx = idx;
                        break;
                    }
                }

                if (!foundNode) {
                    return { sucesso: false, erro: 'Marcador nao encontrado no DOM' };
                }

                editor.focus();
                const sel = window.getSelection();
                const range = document.createRange();
                range.setStart(foundNode, foundIdx);
                range.setEnd(foundNode, foundIdx + marcador.length);
                sel.removeAllRanges();
                sel.addRange(range);
                range.deleteContents();

                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = htmlContent;
                const fragment = document.createDocumentFragment();
                while (tempDiv.firstChild) {
                    fragment.appendChild(tempDiv.firstChild);
                }
                range.insertNode(fragment);

                editor.dispatchEvent(new Event('input', { bubbles: true }));
                editor.dispatchEvent(new Event('change', { bubbles: true }));
                editor.dispatchEvent(new Event('keyup', { bubbles: true }));
                editor.blur();
                setTimeout(() => editor.focus(), 10);

                return { sucesso: true, metodo: 'treewalker_range' };
            } catch (e) {
                return { sucesso: false, erro: e.message };
            }
            """
            resultado = driver.execute_script(script_treewalker, editable, html_content_clean, marcador)

        # 6) Espera confirmação de alteração.
        try:
            def _condicao_html(_drv):
                try:
                    cur = _drv.execute_script("return arguments[0].innerHTML;", editable) or ''
                    if html_content_clean in cur:
                        return True
                    if marcador not in cur:
                        return True
                    return False
                except Exception:
                    return False

            WebDriverWait(driver, 3, poll_frequency=0.2).until(_condicao_html)
        except Exception:
            pass

        if debug:
            metodo = resultado.get('metodo') if isinstance(resultado, dict) else 'desconhecido'
            print(f"[SUBST_MARCADOR] Fonte: {fonte_conteudo} | Método: {metodo} | Resultado: {resultado}")

        return bool(resultado and isinstance(resultado, dict) and resultado.get('sucesso'))

    except Exception as e:
        if debug:
            print(f"[SUBST_MARCADOR] ✗ Erro geral: {e}")
        return False
